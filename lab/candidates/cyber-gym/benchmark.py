#!/usr/bin/env python3
"""Seeded, offline NASim benchmark with exact per-step accounting.

This program never opens sockets, scans hosts, loads credentials, or executes
payloads. Every policy action is an integer passed to a local NASim Gym API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import nasim
import numpy as np


ROOT = Path(__file__).resolve().parent
SCENARIOS = {
    "train-chain": ROOT / "scenarios" / "train-chain.yaml",
    "heldout-branch": ROOT / "scenarios" / "heldout-branch.yaml",
}
NASIM_COMMIT = "4f26de37cfdc3e4553ed8b7484c4db8e2924bdea"
SAFE_SERVICE_FRACTION = 1.0
SERVICE_DISRUPTION_EVENTS = 0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def observation_hash(observation: np.ndarray) -> str:
    canonical = np.asarray(observation, dtype="<f4", order="C")
    return sha256_bytes(canonical.tobytes())


def jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, list):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value


def action_descriptor(env: Any, action_index: int) -> dict[str, Any]:
    action = env.action_space.get_action(int(action_index))
    return {
        "index": int(action_index),
        "kind": action.__class__.__name__,
        "name": str(action.name),
        "target": list(action.target),
        "cost": float(action.cost),
        "success_probability": float(action.prob),
    }


def action_indices(env: Any, predicate: Any, target: tuple[int, int]) -> list[int]:
    matches = []
    for index in range(env.action_space.n):
        action = env.action_space.get_action(index)
        if action.target == target and predicate(action):
            matches.append(index)
    return matches


def gym_action_indices(env: Any) -> np.ndarray:
    """Return the complete discrete Gym action space.

    NASim 0.12.0's optional ``get_action_mask`` helper calls a removed
    ``Network.host_discovered`` method at the pinned commit. The core Gym API
    remains valid. Using the complete discrete space also avoids leaking hidden
    discovery state into a partially observed policy.
    """
    return np.arange(env.action_space.n, dtype=np.int64)


@dataclass
class FixedRulePolicy:
    """A deterministic scan -> enter -> discover -> elevate rule."""

    service_scanned: set[tuple[int, int]] = field(default_factory=set)
    exploited: set[tuple[int, int]] = field(default_factory=set)
    subnet_scanned: set[tuple[int, int]] = field(default_factory=set)
    process_scanned: set[tuple[int, int]] = field(default_factory=set)
    elevated: set[tuple[int, int]] = field(default_factory=set)

    def select(self, env: Any, _observation: np.ndarray) -> tuple[int, int]:
        valid = [int(index) for index in gym_action_indices(env)]
        targets = sorted(
            {env.action_space.get_action(index).target for index in valid}
        )
        phases = (
            (self.service_scanned, lambda action: action.is_service_scan()),
            (self.exploited, lambda action: action.is_exploit()),
            (self.subnet_scanned, lambda action: action.is_subnet_scan()),
            (self.process_scanned, lambda action: action.is_process_scan()),
            (self.elevated, lambda action: action.is_privilege_escalation()),
        )
        for target in targets:
            for completed, predicate in phases:
                if target in completed:
                    continue
                matches = action_indices(env, predicate, target)
                if matches:
                    return min(matches), 0
        return min(valid), 0

    def observe(self, descriptor: dict[str, Any], info: dict[str, Any]) -> None:
        if not bool(info.get("success", False)):
            return
        target = tuple(descriptor["target"])
        completed_by_kind = {
            "ServiceScan": self.service_scanned,
            "Exploit": self.exploited,
            "SubnetScan": self.subnet_scanned,
            "ProcessScan": self.process_scanned,
            "PrivilegeEscalation": self.elevated,
        }
        completed = completed_by_kind.get(descriptor["kind"])
        if completed is not None:
            completed.add(target)


@dataclass
class SeededRandomPolicy:
    rng: np.random.Generator

    def select(self, env: Any, _observation: np.ndarray) -> tuple[int, int]:
        valid = gym_action_indices(env)
        return int(self.rng.choice(valid)), 0

    def observe(self, _descriptor: dict[str, Any], _info: dict[str, Any]) -> None:
        return


@dataclass
class QBelief:
    """Cumulative state built only from action results exposed by the Gym API."""

    completed: set[tuple[str, int, int]] = field(default_factory=set)

    def key(self) -> str:
        return json.dumps(sorted(self.completed), separators=(",", ":"))

    def observe(self, descriptor: dict[str, Any], info: dict[str, Any]) -> None:
        if not bool(info.get("success", False)):
            return
        target = descriptor["target"]
        self.completed.add((descriptor["kind"], int(target[0]), int(target[1])))


class TabularQPolicy:
    """Classical Q-values over observable action history and Gym actions."""

    def __init__(self, num_actions: int, alpha: float = 0.25, gamma: float = 0.95):
        self.num_actions = num_actions
        self.alpha = alpha
        self.gamma = gamma
        self.table: dict[str, np.ndarray] = {}

    def values(self, state_key: str) -> np.ndarray:
        if state_key not in self.table:
            self.table[state_key] = np.zeros(self.num_actions, dtype=np.float64)
        return self.table[state_key]

    def select(
        self,
        env: Any,
        state_key: str,
        epsilon: float,
        rng: np.random.Generator,
    ) -> tuple[int, int]:
        valid = gym_action_indices(env)
        if rng.random() < epsilon:
            return int(rng.choice(valid)), 0
        values = self.values(state_key)
        valid_values = values[valid]
        best_value = valid_values.max()
        best = valid[valid_values == best_value]
        return int(best.min()), int(valid.size)

    def update(
        self,
        state_key: str,
        action: int,
        reward: float,
        next_state_key: str,
        next_valid: np.ndarray,
        done: bool,
    ) -> int:
        values = self.values(state_key)
        if done:
            target = reward
            query_count = 0
        else:
            next_values = self.values(next_state_key)
            target = reward + self.gamma * float(next_values[next_valid].max())
            query_count = int(next_valid.size)
        values[action] += self.alpha * (target - values[action])
        return query_count


def make_env(scenario_name: str) -> Any:
    return nasim.load(
        SCENARIOS[scenario_name],
        fully_obs=False,
        flat_actions=True,
        flat_obs=True,
        name=scenario_name,
    )


def seed_episode(env: Any, seed: int) -> np.ndarray:
    # NASim 0.12.0 uses NumPy's module RNG for probabilistic actions, while
    # Gymnasium reset seeds its own RNG. Seed both to make the episode exact.
    random.seed(seed)
    np.random.seed(seed)
    env.action_space.seed(seed)
    observation, _ = env.reset(seed=seed)
    return observation


def run_episode(
    *,
    env: Any,
    scenario: str,
    policy_name: str,
    policy: Any,
    phase: str,
    episode: int,
    episode_seed: int,
    q_policy: TabularQPolicy | None,
    epsilon: float = 0.0,
    learning: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observation = seed_episode(env, episode_seed)
    policy_rng = np.random.default_rng(episode_seed ^ 0x51A7E)
    start_wall = time.perf_counter_ns()
    start_cpu = time.process_time_ns()
    steps: list[dict[str, Any]] = []
    cumulative_reward = 0.0
    q_queries_total = 0
    terminated = False
    truncated = False
    q_belief = QBelief()

    for step_index in range(1, int(env.scenario.step_limit) + 1):
        before_hash = observation_hash(observation)
        q_state_before = q_belief.key() if policy_name == "tabular-q" else None
        select_wall_start = time.perf_counter_ns()
        select_cpu_start = time.process_time_ns()
        if policy_name == "tabular-q":
            assert q_policy is not None
            action_index, q_select_queries = q_policy.select(
                env, q_state_before, epsilon, policy_rng
            )
        else:
            action_index, q_select_queries = policy.select(env, observation)
        select_cpu_ns = time.process_time_ns() - select_cpu_start
        select_wall_ns = time.perf_counter_ns() - select_wall_start

        descriptor = action_descriptor(env, action_index)
        step_wall_start = time.perf_counter_ns()
        step_cpu_start = time.process_time_ns()
        next_observation, reward, terminated, truncated, info = env.step(action_index)
        step_cpu_ns = time.process_time_ns() - step_cpu_start
        step_wall_ns = time.perf_counter_ns() - step_wall_start

        q_update_queries = 0
        q_state_after = None
        if policy_name == "tabular-q":
            q_belief.observe(descriptor, info)
            q_state_after = q_belief.key()
        if learning:
            assert q_policy is not None
            next_valid = gym_action_indices(env)
            q_update_queries = q_policy.update(
                q_state_before,
                action_index,
                float(reward),
                q_state_after,
                next_valid,
                bool(terminated or truncated),
            )
        elif policy_name != "tabular-q":
            policy.observe(descriptor, info)

        q_queries_step = int(q_select_queries + q_update_queries)
        q_queries_total += q_queries_step
        cumulative_reward += float(reward)
        record = {
            "phase": phase,
            "scenario": scenario,
            "policy": policy_name,
            "episode": episode,
            "episode_seed": episode_seed,
            "step": step_index,
            "environment_queries_step": 1,
            "environment_queries_total": step_index,
            "q_value_queries_step": q_queries_step,
            "q_value_queries_total": q_queries_total,
            "observation_before_sha256": before_hash,
            "observation_after_sha256": observation_hash(next_observation),
            "q_belief_before": q_state_before,
            "q_belief_after": q_state_after,
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
            "selection_process_time_ns": select_cpu_ns,
            "selection_wall_time_ns": select_wall_ns,
            "environment_step_process_time_ns": step_cpu_ns,
            "environment_step_wall_time_ns": step_wall_ns,
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
        "steps": len(steps),
        "environment_queries": len(steps),
        "q_value_queries": q_queries_total,
        "reward": cumulative_reward,
        "success": bool(terminated),
        "truncated": bool(truncated),
        "safe_service_fraction": SAFE_SERVICE_FRACTION,
        "service_disruption_events": SERVICE_DISRUPTION_EVENTS,
        "q_table_states": 0 if q_policy is None else len(q_policy.table),
        "process_time_ns": time.process_time_ns() - start_cpu,
        "wall_time_ns": time.perf_counter_ns() - start_wall,
    }
    return episode_record, steps


def summarize(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = (record["phase"], record["scenario"], record["policy"])
        groups.setdefault(key, []).append(record)
    output = []
    for key in sorted(groups):
        rows = groups[key]
        rewards = [float(row["reward"]) for row in rows]
        step_counts = [int(row["steps"]) for row in rows]
        successes = sum(bool(row["success"]) for row in rows)
        output.append({
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
            "process_time_ns": sum(row["process_time_ns"] for row in rows),
            "wall_time_ns": sum(row["wall_time_ns"] for row in rows),
            "safe_service_fraction": statistics.fmean(
                row["safe_service_fraction"] for row in rows
            ),
            "service_disruption_events": sum(
                row["service_disruption_events"] for row in rows
            ),
        })
    return output


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(jsonable(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(jsonable(row), sort_keys=True) + "\n")


def run_benchmark(
    output: Path,
    seed: int,
    train_episodes: int,
    eval_episodes: int,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(
            f"output already exists: {output}; choose a new --output path"
        )
    output.mkdir(parents=True)

    train_env = make_env("train-chain")
    heldout_env = make_env("heldout-branch")
    if train_env.action_space.n != heldout_env.action_space.n:
        raise ValueError("held-out action space does not match training")
    if train_env.observation_space.shape != heldout_env.observation_space.shape:
        raise ValueError("held-out observation space does not match training")

    q_policy = TabularQPolicy(train_env.action_space.n)
    episodes: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []

    for episode in range(train_episodes):
        epsilon = 1.0 if train_episodes == 1 else (
            1.0 - (0.95 * episode / (train_episodes - 1))
        )
        episode_record, step_records = run_episode(
            env=train_env,
            scenario="train-chain",
            policy_name="tabular-q",
            policy=q_policy,
            phase="train",
            episode=episode,
            episode_seed=seed + episode,
            q_policy=q_policy,
            epsilon=epsilon,
            learning=True,
        )
        episode_record["epsilon"] = epsilon
        episodes.append(episode_record)
        steps.extend(step_records)

    eval_seed_base = seed + 100_000
    for scenario_index, (scenario, env) in enumerate(
        (("train-chain", train_env), ("heldout-branch", heldout_env))
    ):
        for policy_index, policy_name in enumerate(
            ("fixed-rule", "seeded-random", "tabular-q")
        ):
            for episode in range(eval_episodes):
                episode_seed = eval_seed_base + scenario_index * 10_000 + episode
                if policy_name == "fixed-rule":
                    policy: Any = FixedRulePolicy()
                elif policy_name == "seeded-random":
                    policy = SeededRandomPolicy(
                        np.random.default_rng(episode_seed ^ 0xA11CE)
                    )
                else:
                    policy = q_policy
                episode_record, step_records = run_episode(
                    env=env,
                    scenario=scenario,
                    policy_name=policy_name,
                    policy=policy,
                    phase="eval",
                    episode=episode,
                    episode_seed=episode_seed,
                    q_policy=q_policy if policy_name == "tabular-q" else None,
                    epsilon=0.0,
                    learning=False,
                )
                episodes.append(episode_record)
                steps.extend(step_records)

    scenario_hashes = {
        name: sha256_bytes(path.read_bytes()) for name, path in SCENARIOS.items()
    }
    manifest = {
        "benchmark": "offline-nasim-cyber-gym-v1",
        "base_seed": seed,
        "nasim_version": nasim.__version__,
        "nasim_commit": NASIM_COMMIT,
        "python": os.sys.version.split()[0],
        "numpy": np.__version__,
        "train_episodes": train_episodes,
        "eval_episodes_per_policy_scenario": eval_episodes,
        "partial_observation": True,
        "flat_actions": True,
        "flat_observation": True,
        "scenario_sha256": scenario_hashes,
        "safe_service_definition": (
            "Fraction of configured synthetic services not disabled. NASim "
            "0.12.0 has no service-disable transition or availability state, "
            "so this is exactly 1.0 by environment construction."
        ),
        "environment_query_definition": "one call to env.step(action_index)",
        "q_value_query_definition": (
            "one inspected tabular action value during greedy selection or "
            "bootstrap maximization; random exploration inspects zero values"
        ),
        "q_state_definition": (
            "cumulative successful action-kind and target tuples observed "
            "through prior Gym step results; no hidden simulator state"
        ),
        "compute_definition": (
            "integer process_time_ns and perf_counter_ns measured per step and episode"
        ),
    }
    summary = {
        "manifest": manifest,
        "aggregates": summarize(episodes),
        "unfavorable_outcomes_retained": True,
    }
    q_table = {
        key: [float(value) for value in values]
        for key, values in sorted(q_policy.table.items())
    }
    write_json(output / "manifest.json", manifest)
    write_json(output / "summary.json", summary)
    write_json(output / "q_table.json", q_table)
    write_jsonl(output / "episodes.jsonl", episodes)
    write_jsonl(output / "steps.jsonl", steps)
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
    summary = run_benchmark(
        output=output,
        seed=args.seed,
        train_episodes=args.train_episodes,
        eval_episodes=args.eval_episodes,
    )
    print(json.dumps(summary["aggregates"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
