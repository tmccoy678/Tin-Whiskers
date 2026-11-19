#!/usr/bin/env python3
"""Transparent NumPy DQN comparison for the isolated NASim candidate."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import html
import json
import os
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import gymnasium as gym
import nasim
import numpy as np

from benchmark import (
    NASIM_COMMIT,
    QBelief,
    SAFE_SERVICE_FRACTION,
    SERVICE_DISRUPTION_EVENTS,
    FixedRulePolicy,
    TabularQPolicy,
    action_descriptor,
    gym_action_indices,
    jsonable,
    make_env,
    observation_hash,
    seed_episode,
    sha256_bytes,
)


ROOT = Path(__file__).resolve().parent
REVERSAL_SPEC = ROOT / "scenarios" / "reversal-deception.json"
REWARD_SCALE = 50.0


class ReversalDeceptionEnv(gym.Wrapper):
    """Swap two target-action meanings after an observable synthetic event.

    The wrapper activates after a successful intended privilege escalation on
    toy host (2, 0). Thereafter, intended Exploit and ProcessScan actions on
    toy host (3, 0) are swapped before the discrete action reaches NASim. The
    policy receives only NASim's ordinary observation, reward, and info. The
    audit is retained separately by the runner and is never passed into a
    policy feature or belief state.
    """

    def __init__(self, env: Any):
        super().__init__(env)
        spec = json.loads(REVERSAL_SPEC.read_text(encoding="utf-8"))
        self.trigger_target = tuple(spec["trigger_target"])
        self.reversal_target = tuple(spec["reversal_target"])
        self.left_kind = spec["swap_action_kinds"][0]
        self.right_kind = spec["swap_action_kinds"][1]
        self.reversal_active = False
        self.last_reversal_audit: dict[str, Any] | None = None

    @property
    def scenario(self) -> Any:
        return self.env.scenario

    def _find_index(self, kind: str, target: tuple[int, int]) -> int:
        matches = []
        for index in range(self.action_space.n):
            descriptor = action_descriptor(self.env, index)
            if descriptor["kind"] == kind and tuple(descriptor["target"]) == target:
                matches.append(index)
        if len(matches) != 1:
            raise ValueError(f"expected one {kind} action for {target}, got {matches}")
        return matches[0]

    def reset(self, **kwargs: Any) -> tuple[np.ndarray, dict[str, Any]]:
        self.reversal_active = False
        self.last_reversal_audit = None
        return self.env.reset(**kwargs)

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        intended_index = int(action)
        intended = action_descriptor(self.env, intended_index)
        active_before = self.reversal_active
        effective_index = intended_index

        if active_before and tuple(intended["target"]) == self.reversal_target:
            if intended["kind"] == self.left_kind:
                effective_index = self._find_index(self.right_kind, self.reversal_target)
            elif intended["kind"] == self.right_kind:
                effective_index = self._find_index(self.left_kind, self.reversal_target)

        observation, reward, terminated, truncated, info = self.env.step(effective_index)
        triggered = (
            not self.reversal_active
            and intended["kind"] == "PrivilegeEscalation"
            and tuple(intended["target"]) == self.trigger_target
            and bool(info.get("success", False))
        )
        if triggered:
            self.reversal_active = True

        effective = action_descriptor(self.env, effective_index)
        self.last_reversal_audit = {
            "active_before": active_before,
            "active_after": self.reversal_active,
            "triggered_this_step": triggered,
            "mapping_applied": effective_index != intended_index,
            "intended_action": intended,
            "effective_action": effective,
        }
        return observation, reward, terminated, truncated, info


def make_reversal_env() -> ReversalDeceptionEnv:
    return ReversalDeceptionEnv(make_env("heldout-branch"))


class LoggedTabularAgent:
    """Tabular Q learner that returns every inspected value for the record."""

    def __init__(self, num_actions: int, alpha: float = 0.25, gamma: float = 0.95):
        self.q = TabularQPolicy(num_actions, alpha=alpha, gamma=gamma)

    @property
    def table(self) -> dict[str, np.ndarray]:
        return self.q.table

    def select(
        self,
        state_key: str,
        epsilon: float,
        rng: np.random.Generator,
    ) -> tuple[int, np.ndarray, int]:
        values = self.q.values(state_key).copy()
        valid = gym_action_indices_from_count(values.size)
        if rng.random() < epsilon:
            action = int(rng.choice(valid))
        else:
            best = valid[values[valid] == values[valid].max()]
            action = int(best.min())
        return action, values, int(values.size)

    def update(
        self,
        state_key: str,
        action: int,
        reward: float,
        next_state_key: str,
        done: bool,
    ) -> int:
        valid = gym_action_indices_from_count(self.q.num_actions)
        return self.q.update(
            state_key, action, reward, next_state_key, valid, done
        )


def gym_action_indices_from_count(count: int) -> np.ndarray:
    return np.arange(count, dtype=np.int64)


class ObservableNeuralState:
    """Episode memory containing only successful intended Gym actions."""

    def __init__(self, num_actions: int):
        self.successes = np.zeros(num_actions, dtype=np.float64)

    def observe(self, action: int, info: dict[str, Any]) -> None:
        if bool(info.get("success", False)):
            self.successes[action] = 1.0


class TinyMLP:
    """One-hidden-layer ReLU Q network with explicit NumPy Adam updates."""

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        rng: np.random.Generator,
        learning_rate: float,
    ):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.learning_rate = learning_rate
        self.params = {
            "w1": rng.normal(0.0, np.sqrt(2.0 / input_dim), (input_dim, hidden_dim)),
            "b1": np.zeros(hidden_dim, dtype=np.float64),
            "w2": rng.normal(0.0, np.sqrt(2.0 / hidden_dim), (hidden_dim, output_dim)),
            "b2": np.zeros(output_dim, dtype=np.float64),
        }
        self.moments = {name: np.zeros_like(value) for name, value in self.params.items()}
        self.velocities = {name: np.zeros_like(value) for name, value in self.params.items()}
        self.adam_step = 0

    def predict(self, features: np.ndarray) -> np.ndarray:
        matrix = np.atleast_2d(np.asarray(features, dtype=np.float64))
        hidden = np.maximum(0.0, matrix @ self.params["w1"] + self.params["b1"])
        output = hidden @ self.params["w2"] + self.params["b2"]
        return output[0] if np.asarray(features).ndim == 1 else output

    def train(self, features: np.ndarray, actions: np.ndarray, targets: np.ndarray) -> float:
        x = np.asarray(features, dtype=np.float64)
        actions = np.asarray(actions, dtype=np.int64)
        targets = np.asarray(targets, dtype=np.float64)
        z1 = x @ self.params["w1"] + self.params["b1"]
        hidden = np.maximum(0.0, z1)
        q_values = hidden @ self.params["w2"] + self.params["b2"]
        chosen = q_values[np.arange(x.shape[0]), actions]
        errors = chosen - targets
        abs_errors = np.abs(errors)
        losses = np.where(abs_errors <= 1.0, 0.5 * errors**2, abs_errors - 0.5)

        chosen_grad = np.where(abs_errors <= 1.0, errors, np.sign(errors))
        output_grad = np.zeros_like(q_values)
        output_grad[np.arange(x.shape[0]), actions] = chosen_grad / x.shape[0]
        grads = {
            "w2": hidden.T @ output_grad,
            "b2": output_grad.sum(axis=0),
        }
        hidden_grad = output_grad @ self.params["w2"].T
        hidden_grad[z1 <= 0.0] = 0.0
        grads["w1"] = x.T @ hidden_grad
        grads["b1"] = hidden_grad.sum(axis=0)

        global_norm = np.sqrt(sum(float(np.sum(grad**2)) for grad in grads.values()))
        if global_norm > 10.0:
            scale = 10.0 / global_norm
            grads = {name: grad * scale for name, grad in grads.items()}

        self.adam_step += 1
        beta1, beta2, epsilon = 0.9, 0.999, 1e-8
        for name, grad in grads.items():
            self.moments[name] = beta1 * self.moments[name] + (1.0 - beta1) * grad
            self.velocities[name] = beta2 * self.velocities[name] + (1.0 - beta2) * grad**2
            m_hat = self.moments[name] / (1.0 - beta1**self.adam_step)
            v_hat = self.velocities[name] / (1.0 - beta2**self.adam_step)
            self.params[name] -= self.learning_rate * m_hat / (np.sqrt(v_hat) + epsilon)
        return float(losses.mean())

    def copy_parameters_from(self, other: "TinyMLP") -> None:
        for name in self.params:
            self.params[name][...] = other.params[name]


@dataclass
class Transition:
    features: np.ndarray
    action: int
    scaled_reward: float
    next_features: np.ndarray
    done: bool


class ReplayBuffer:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.items: list[Transition] = []
        self.position = 0

    def add(self, transition: Transition) -> None:
        if len(self.items) < self.capacity:
            self.items.append(transition)
        else:
            self.items[self.position] = transition
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int, rng: np.random.Generator) -> list[Transition]:
        indices = rng.choice(len(self.items), size=batch_size, replace=False)
        return [self.items[int(index)] for index in indices]

    def __len__(self) -> int:
        return len(self.items)


class NeuralQAgent:
    """Small DQN with replay and a hard-synchronized target network."""

    def __init__(
        self,
        input_dim: int,
        num_actions: int,
        seed: int,
        hidden_dim: int = 32,
        learning_rate: float = 0.001,
        gamma: float = 0.95,
        replay_capacity: int = 4096,
        batch_size: int = 32,
        warmup: int = 256,
        target_sync_interval: int = 120,
    ):
        self.input_dim = input_dim
        self.num_actions = num_actions
        self.hidden_dim = hidden_dim
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.batch_size = batch_size
        self.warmup = warmup
        self.target_sync_interval = target_sync_interval
        self.rng = np.random.default_rng(seed)
        self.online = TinyMLP(input_dim, hidden_dim, num_actions, self.rng, learning_rate)
        self.target = TinyMLP(input_dim, hidden_dim, num_actions, self.rng, learning_rate)
        self.target.copy_parameters_from(self.online)
        self.replay = ReplayBuffer(replay_capacity)
        self.optimizer_updates = 0
        self.target_syncs = 1
        self.replay_samples = 0

    @property
    def parameter_count(self) -> int:
        return sum(value.size for value in self.online.params.values())

    def select(
        self,
        features: np.ndarray,
        epsilon: float,
    ) -> tuple[int, np.ndarray, int]:
        q_values = self.online.predict(features)
        if self.rng.random() < epsilon:
            action = int(self.rng.integers(0, self.num_actions))
        else:
            action = int(np.flatnonzero(q_values == q_values.max()).min())
        return action, q_values.copy(), self.num_actions

    def learn(self, transition: Transition) -> dict[str, Any]:
        self.replay.add(transition)
        metrics = {
            "loss": None,
            "optimizer_updates_step": 0,
            "replay_samples_step": 0,
            "target_syncs_step": 0,
            "q_value_queries_update": 0,
        }
        if len(self.replay) < max(self.warmup, self.batch_size):
            return metrics

        batch = self.replay.sample(self.batch_size, self.rng)
        features = np.stack([item.features for item in batch])
        actions = np.asarray([item.action for item in batch], dtype=np.int64)
        rewards = np.asarray([item.scaled_reward for item in batch], dtype=np.float64)
        next_features = np.stack([item.next_features for item in batch])
        done = np.asarray([item.done for item in batch], dtype=np.float64)

        next_q = self.target.predict(next_features)
        targets = rewards + self.gamma * (1.0 - done) * next_q.max(axis=1)
        loss = self.online.train(features, actions, targets)
        self.optimizer_updates += 1
        self.replay_samples += self.batch_size
        metrics.update({
            "loss": loss,
            "optimizer_updates_step": 1,
            "replay_samples_step": self.batch_size,
            "q_value_queries_update": self.batch_size * self.num_actions * 2,
        })
        if self.optimizer_updates % self.target_sync_interval == 0:
            self.target.copy_parameters_from(self.online)
            self.target_syncs += 1
            metrics["target_syncs_step"] = 1
        return metrics

    def adaptive_clone(self, seed: int) -> "NeuralQAgent":
        clone = NeuralQAgent(
            self.input_dim,
            self.num_actions,
            seed,
            hidden_dim=self.hidden_dim,
            learning_rate=self.learning_rate,
            gamma=self.gamma,
            replay_capacity=512,
            batch_size=8,
            warmup=8,
            target_sync_interval=16,
        )
        clone.online.copy_parameters_from(self.online)
        clone.target.copy_parameters_from(self.online)
        return clone


def neural_features(
    observation: np.ndarray,
    belief: ObservableNeuralState,
    step_index: int,
    step_limit: int,
) -> np.ndarray:
    normalized_observation = np.asarray(observation, dtype=np.float64) / REWARD_SCALE
    step_fraction = np.asarray([step_index / step_limit], dtype=np.float64)
    return np.concatenate((normalized_observation, belief.successes, step_fraction))


def epsilon_for_episode(episode: int, episode_count: int) -> float:
    if episode_count <= 1:
        return 1.0
    return 1.0 - (0.95 * episode / (episode_count - 1))


def run_episode(
    *,
    env: Any,
    scenario: str,
    policy_name: str,
    policy: Any,
    phase: str,
    episode: int,
    episode_seed: int,
    epsilon: float,
    learning: bool,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observation = seed_episode(env, episode_seed)
    step_limit = int(env.scenario.step_limit)
    tabular_belief = QBelief()
    neural_belief = ObservableNeuralState(env.action_space.n)
    policy_rng = np.random.default_rng(episode_seed ^ 0x51A7E)
    episode_start_wall = time.perf_counter_ns()
    episode_start_cpu = time.process_time_ns()
    steps: list[dict[str, Any]] = []
    cumulative_reward = 0.0
    q_queries_total = 0
    optimizer_updates_start = getattr(policy, "optimizer_updates", 0)
    replay_samples_start = getattr(policy, "replay_samples", 0)
    target_syncs_start = getattr(policy, "target_syncs", 0)
    losses: list[float] = []
    terminated = False
    truncated = False

    for step_index in range(1, step_limit + 1):
        select_start_wall = time.perf_counter_ns()
        select_start_cpu = time.process_time_ns()
        q_values: np.ndarray | None = None
        feature_hash: str | None = None
        tabular_state_before: str | None = None
        features_before: np.ndarray | None = None

        if policy_name == "fixed-rule":
            action, q_select_queries = policy.select(env, observation)
        elif policy_name == "tabular-q":
            tabular_state_before = tabular_belief.key()
            action, q_values, q_select_queries = policy.select(
                tabular_state_before, epsilon, policy_rng
            )
        elif policy_name == "neural-q":
            features_before = neural_features(
                observation, neural_belief, step_index - 1, step_limit
            )
            feature_hash = sha256_bytes(np.asarray(features_before, dtype="<f8").tobytes())
            action, q_values, q_select_queries = policy.select(features_before, epsilon)
        else:
            raise ValueError(f"unknown policy: {policy_name}")

        selection_process_ns = time.process_time_ns() - select_start_cpu
        selection_wall_ns = time.perf_counter_ns() - select_start_wall
        descriptor = action_descriptor(env, action)
        step_start_wall = time.perf_counter_ns()
        step_start_cpu = time.process_time_ns()
        next_observation, reward, terminated, truncated, info = env.step(action)
        environment_process_ns = time.process_time_ns() - step_start_cpu
        environment_wall_ns = time.perf_counter_ns() - step_start_wall

        update = {
            "loss": None,
            "optimizer_updates_step": 0,
            "replay_samples_step": 0,
            "target_syncs_step": 0,
            "q_value_queries_update": 0,
        }
        tabular_state_after: str | None = None
        if policy_name == "fixed-rule":
            policy.observe(descriptor, info)
        elif policy_name == "tabular-q":
            tabular_belief.observe(descriptor, info)
            tabular_state_after = tabular_belief.key()
            if learning:
                update["q_value_queries_update"] = policy.update(
                    tabular_state_before,
                    action,
                    float(reward),
                    tabular_state_after,
                    bool(terminated or truncated),
                )
        else:
            assert features_before is not None
            neural_belief.observe(action, info)
            next_features = neural_features(
                next_observation, neural_belief, step_index, step_limit
            )
            if learning:
                update = policy.learn(Transition(
                    features=features_before.copy(),
                    action=action,
                    scaled_reward=float(reward) / REWARD_SCALE,
                    next_features=next_features.copy(),
                    done=bool(terminated or truncated),
                ))

        if update["loss"] is not None:
            losses.append(float(update["loss"]))
        q_queries_step = int(q_select_queries + update["q_value_queries_update"])
        q_queries_total += q_queries_step
        cumulative_reward += float(reward)
        reversal_audit = copy.deepcopy(
            getattr(env, "last_reversal_audit", None)
        )
        record = {
            "phase": phase,
            "scenario": scenario,
            "policy": policy_name,
            "episode": episode,
            "episode_seed": episode_seed,
            "step": step_index,
            "epsilon": epsilon,
            "environment_queries_step": 1,
            "environment_queries_total": step_index,
            "q_value_queries_step": q_queries_step,
            "q_value_queries_total": q_queries_total,
            "q_values_before": None if q_values is None else q_values.tolist(),
            "chosen_q_value": None if q_values is None else float(q_values[action]),
            "tabular_belief_before": tabular_state_before,
            "tabular_belief_after": tabular_state_after,
            "neural_feature_sha256": feature_hash,
            "observation_before_sha256": observation_hash(observation),
            "observation_after_sha256": observation_hash(next_observation),
            "action": descriptor,
            "action_success": bool(info.get("success", False)),
            "connection_error": bool(info.get("connection_error", False)),
            "permission_error": bool(info.get("permission_error", False)),
            "undefined_error": bool(info.get("undefined_error", False)),
            "reward": float(reward),
            "cumulative_reward": cumulative_reward,
            "terminated": bool(terminated),
            "truncated": bool(truncated),
            "safe_service_fraction": SAFE_SERVICE_FRACTION,
            "service_disruption_events": SERVICE_DISRUPTION_EVENTS,
            "selection_process_time_ns": selection_process_ns,
            "selection_wall_time_ns": selection_wall_ns,
            "environment_step_process_time_ns": environment_process_ns,
            "environment_step_wall_time_ns": environment_wall_ns,
            "loss": update["loss"],
            "optimizer_updates_step": update["optimizer_updates_step"],
            "optimizer_updates_total": getattr(policy, "optimizer_updates", 0),
            "replay_size": len(getattr(policy, "replay", [])),
            "replay_samples_step": update["replay_samples_step"],
            "replay_samples_total": getattr(policy, "replay_samples", 0),
            "target_syncs_step": update["target_syncs_step"],
            "target_syncs_total": getattr(policy, "target_syncs", 0),
            "reversal_audit": reversal_audit,
        }
        steps.append(record)
        observation = next_observation
        if terminated or truncated:
            break

    episode_record = {
        "phase": phase,
        "scenario": scenario,
        "policy": policy_name,
        "episode": episode,
        "episode_seed": episode_seed,
        "epsilon": epsilon,
        "steps": len(steps),
        "environment_queries": len(steps),
        "q_value_queries": q_queries_total,
        "reward": cumulative_reward,
        "success": bool(terminated),
        "truncated": bool(truncated),
        "safe_service_fraction": SAFE_SERVICE_FRACTION,
        "service_disruption_events": SERVICE_DISRUPTION_EVENTS,
        "optimizer_updates": getattr(policy, "optimizer_updates", 0)
        - optimizer_updates_start,
        "replay_samples": getattr(policy, "replay_samples", 0)
        - replay_samples_start,
        "target_syncs": getattr(policy, "target_syncs", 0) - target_syncs_start,
        "mean_loss": None if not losses else statistics.fmean(losses),
        "process_time_ns": time.process_time_ns() - episode_start_cpu,
        "wall_time_ns": time.perf_counter_ns() - episode_start_wall,
    }
    return episode_record, steps


def summarize(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = (record["phase"], record["scenario"], record["policy"])
        groups.setdefault(key, []).append(record)
    summary = []
    for key in sorted(groups):
        rows = groups[key]
        rewards = [float(row["reward"]) for row in rows]
        step_counts = [int(row["steps"]) for row in rows]
        losses = [row["mean_loss"] for row in rows if row["mean_loss"] is not None]
        successes = sum(bool(row["success"]) for row in rows)
        summary.append({
            "phase": key[0],
            "scenario": key[1],
            "policy": key[2],
            "episodes": len(rows),
            "successes": successes,
            "success_rate": successes / len(rows),
            "mean_reward": statistics.fmean(rewards),
            "median_reward": statistics.median(rewards),
            "mean_steps": statistics.fmean(step_counts),
            "median_steps": statistics.median(step_counts),
            "environment_queries": sum(row["environment_queries"] for row in rows),
            "q_value_queries": sum(row["q_value_queries"] for row in rows),
            "optimizer_updates": sum(row["optimizer_updates"] for row in rows),
            "replay_samples": sum(row["replay_samples"] for row in rows),
            "target_syncs": sum(row["target_syncs"] for row in rows),
            "mean_loss": None if not losses else statistics.fmean(losses),
            "process_time_ns": sum(row["process_time_ns"] for row in rows),
            "wall_time_ns": sum(row["wall_time_ns"] for row in rows),
            "safe_service_fraction": statistics.fmean(
                row["safe_service_fraction"] for row in rows
            ),
            "service_disruption_events": sum(
                row["service_disruption_events"] for row in rows
            ),
        })
    return summary


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(jsonable(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl_gz(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as handle:
        for row in rows:
            handle.write(json.dumps(jsonable(row), sort_keys=True) + "\n")


def write_surface(
    directory: Path,
    steps: list[dict[str, Any]],
    action_map: list[dict[str, Any]],
) -> None:
    directory.mkdir(exist_ok=True)
    rows = [
        row for row in steps
        if row["q_values_before"] is not None and row["phase"].startswith("eval")
    ]
    headers = [
        "phase", "scenario", "policy", "episode", "step", "epsilon",
        "chosen_action", "reward", "success", "reversal_active_before",
    ] + [f"q_{index:02d}" for index in range(len(action_map))]
    with (directory / "q_lattice.tsv").open("w", encoding="utf-8") as handle:
        handle.write("\t".join(headers) + "\n")
        for row in rows:
            audit = row["reversal_audit"] or {}
            values = [
                row["phase"], row["scenario"], row["policy"], row["episode"],
                row["step"], row["epsilon"], row["action"]["index"],
                row["reward"], int(row["terminated"]), audit.get("active_before", ""),
            ] + [f"{value:.9g}" for value in row["q_values_before"]]
            handle.write("\t".join(str(value) for value in values) + "\n")

    write_json(directory / "action_map.json", action_map)
    display_rows = [row for row in rows if row["episode"] == 0]
    policy_bounds = {
        policy: max(
            (
                abs(value)
                for row in display_rows if row["policy"] == policy
                for value in row["q_values_before"]
            ),
            default=1.0,
        ) or 1.0
        for policy in {row["policy"] for row in display_rows}
    }

    def cell(value: float, chosen: bool, bound: float) -> str:
        intensity = min(1.0, abs(value) / bound)
        if value >= 0:
            color = f"rgba(16, 145, 84, {0.12 + 0.78 * intensity:.3f})"
        else:
            color = f"rgba(190, 45, 45, {0.12 + 0.78 * intensity:.3f})"
        css = f"background:{color};" + ("outline:2px solid #ffd166;" if chosen else "")
        return f'<td style="{css}">{value:.4f}</td>'

    action_headers = "".join(
        f"<th title='{html.escape(item['kind'])} {item['target']}'>a{item['index']}</th>"
        for item in action_map
    )
    table_rows = []
    for row in display_rows:
        prefix = (
            f"<td>{html.escape(row['phase'])}</td>"
            f"<td>{html.escape(row['scenario'])}</td>"
            f"<td>{html.escape(row['policy'])}</td>"
            f"<td>{row['step']}</td><td>{row['reward']:.1f}</td>"
        )
        q_cells = "".join(
            cell(
                value,
                index == row["action"]["index"],
                policy_bounds[row["policy"]],
            )
            for index, value in enumerate(row["q_values_before"])
        )
        table_rows.append(f"<tr>{prefix}{q_cells}</tr>")
    document = f"""<!doctype html>
<meta charset="utf-8">
<title>Cyber-gym rolling Q lattice</title>
<style>
body {{ font: 13px -apple-system, BlinkMacSystemFont, sans-serif; margin: 20px; background: #f7f5ef; color: #171717; }}
h1 {{ margin-bottom: 4px; }} p {{ max-width: 1000px; }}
.wrap {{ overflow: auto; max-height: 85vh; border: 1px solid #aaa; background: white; }}
table {{ border-collapse: collapse; white-space: nowrap; }}
th {{ position: sticky; top: 0; background: #222; color: white; z-index: 2; }}
td, th {{ border: 1px solid #bbb; padding: 3px 6px; text-align: right; font-variant-numeric: tabular-nums; }}
td:nth-child(-n+3), th:nth-child(-n+3) {{ text-align: left; }}
</style>
<h1>Rolling classical Q-value lattice</h1>
<p>Episode 0 from every evaluation surface. Green is positive, red is negative, and the yellow outline is the chosen action. Tabular values use raw reward units; neural values use reward divided by 50. Compare rank within a policy, not magnitude across policies. These are classical software values, not quantum amplitudes.</p>
<div class="wrap"><table><thead><tr><th>phase</th><th>scenario</th><th>policy</th><th>step</th><th>reward</th>{action_headers}</tr></thead>
<tbody>{''.join(table_rows)}</tbody></table></div>
"""
    (directory / "q_lattice.html").write_text(document, encoding="utf-8")


def save_neural_model(path: Path, agent: NeuralQAgent) -> None:
    arrays = {f"online_{key}": value for key, value in agent.online.params.items()}
    arrays.update({f"target_{key}": value for key, value in agent.target.params.items()})
    np.savez_compressed(path, **arrays)


def run_benchmark(
    output: Path,
    seed: int,
    train_episodes: int,
    eval_episodes: int,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)

    train_env = make_env("train-chain")
    num_actions = train_env.action_space.n
    input_dim = train_env.observation_space.shape[0] + num_actions + 1
    tabular = LoggedTabularAgent(num_actions)
    neural = NeuralQAgent(input_dim, num_actions, seed + 73)
    episodes: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []

    for policy_name, policy in (("tabular-q", tabular), ("neural-q", neural)):
        env = make_env("train-chain")
        for episode in range(train_episodes):
            episode_record, step_records = run_episode(
                env=env,
                scenario="train-chain",
                policy_name=policy_name,
                policy=policy,
                phase="train",
                episode=episode,
                episode_seed=seed + episode,
                epsilon=epsilon_for_episode(episode, train_episodes),
                learning=True,
            )
            episodes.append(episode_record)
            steps.extend(step_records)

    eval_seed_base = seed + 200_000
    eval_scenarios = (
        ("train-chain", make_env),
        ("heldout-branch", make_env),
        ("reversal-deception", lambda _name: make_reversal_env()),
    )
    for scenario_index, (scenario, factory) in enumerate(eval_scenarios):
        for policy_name, learned_policy in (
            ("fixed-rule", None), ("tabular-q", tabular), ("neural-q", neural)
        ):
            env = factory(scenario if scenario != "reversal-deception" else "heldout-branch")
            for episode in range(eval_episodes):
                policy = FixedRulePolicy() if policy_name == "fixed-rule" else learned_policy
                episode_record, step_records = run_episode(
                    env=env,
                    scenario=scenario,
                    policy_name=policy_name,
                    policy=policy,
                    phase="eval-zero-shot",
                    episode=episode,
                    episode_seed=eval_seed_base + scenario_index * 10_000 + episode,
                    epsilon=0.0,
                    learning=False,
                )
                episodes.append(episode_record)
                steps.extend(step_records)

    adaptive_tabular = copy.deepcopy(tabular)
    adaptive_neural = neural.adaptive_clone(seed + 991)
    for policy_name, policy in (
        ("fixed-rule", None),
        ("tabular-q", adaptive_tabular),
        ("neural-q", adaptive_neural),
    ):
        env = make_reversal_env()
        for episode in range(eval_episodes):
            episode_policy = FixedRulePolicy() if policy_name == "fixed-rule" else policy
            episode_record, step_records = run_episode(
                env=env,
                scenario="reversal-deception",
                policy_name=policy_name,
                policy=episode_policy,
                phase="eval-adapt",
                episode=episode,
                episode_seed=eval_seed_base + 30_000 + episode,
                epsilon=0.15 if policy_name != "fixed-rule" else 0.0,
                learning=policy_name != "fixed-rule",
            )
            episodes.append(episode_record)
            steps.extend(step_records)

    scenario_hashes = {
        "train-chain": sha256_bytes((ROOT / "scenarios/train-chain.yaml").read_bytes()),
        "heldout-branch": sha256_bytes((ROOT / "scenarios/heldout-branch.yaml").read_bytes()),
        "reversal-deception": sha256_bytes(REVERSAL_SPEC.read_bytes()),
    }
    manifest = {
        "benchmark": "offline-nasim-neural-q-v1",
        "base_seed": seed,
        "nasim_version": nasim.__version__,
        "nasim_commit": NASIM_COMMIT,
        "python": os.sys.version.split()[0],
        "numpy": np.__version__,
        "train_episodes_per_learned_policy": train_episodes,
        "eval_episodes_per_condition": eval_episodes,
        "scenario_sha256": scenario_hashes,
        "partial_observation": True,
        "all_actions_through_gym_step": True,
        "neural_architecture": {
            "input": input_dim,
            "hidden": neural.hidden_dim,
            "activation": "ReLU",
            "output": num_actions,
            "parameters": neural.parameter_count,
            "optimizer": "NumPy Adam",
            "learning_rate": neural.learning_rate,
            "reward_scale": REWARD_SCALE,
        },
        "stability": {
            "replay_capacity": neural.replay.capacity,
            "batch_size": neural.batch_size,
            "warmup": neural.warmup,
            "target_sync_interval_updates": neural.target_sync_interval,
            "gradient_global_norm_cap": 10.0,
        },
        "adaptive_reversal": {
            "epsilon": 0.15,
            "tabular_updates_online": True,
            "neural_replay_capacity": adaptive_neural.replay.capacity,
            "neural_batch_size": adaptive_neural.batch_size,
            "neural_warmup": adaptive_neural.warmup,
            "neural_target_sync_interval": adaptive_neural.target_sync_interval,
            "carry_learning_across_eval_episodes": True,
        },
        "q_value_query_definition": (
            "one recorded tabular cell read or one computed neural output cell; "
            "a neural replay update counts online and target output cells"
        ),
        "reversal_hidden_state_boundary": (
            "activation and effective mapping are audit-only; policies receive "
            "ordinary NASim observations, rewards, and action-result info"
        ),
        "safe_service_definition": (
            "fraction of immutable configured synthetic services not disabled; "
            "exactly 1.0 because NASim has no service-disable transition"
        ),
    }
    aggregates = summarize(episodes)
    summary = {
        "manifest": manifest,
        "aggregates": aggregates,
        "unfavorable_outcomes_retained": True,
    }
    action_map = [action_descriptor(train_env, index) for index in range(num_actions)]
    write_json(output / "manifest.json", manifest)
    write_json(output / "summary.json", summary)
    write_jsonl_gz(output / "episodes.jsonl.gz", episodes)
    write_jsonl_gz(output / "steps.jsonl.gz", steps)
    write_json(
        output / "tabular_q_table.json",
        {key: values.tolist() for key, values in sorted(tabular.table.items())},
    )
    save_neural_model(output / "neural_q_model.npz", neural)
    write_surface(output / "surface", steps, action_map)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=319)
    parser.add_argument("--train-episodes", type=int, default=600)
    parser.add_argument("--eval-episodes", type=int, default=16)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.train_episodes <= 0 or args.eval_episodes <= 0:
        raise ValueError("episode counts must be positive")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    summary = run_benchmark(output, args.seed, args.train_episodes, args.eval_episodes)
    print(json.dumps(summary["aggregates"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
