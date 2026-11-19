from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import benchmark
import neural_benchmark as neural


class NeuralBenchmarkTests(unittest.TestCase):
    def test_reversal_swaps_only_after_observable_trigger(self) -> None:
        env = neural.make_reversal_env()
        observation = benchmark.seed_episode(env, 319)
        policy = benchmark.FixedRulePolicy()
        saw_trigger = False
        saw_mapping = False
        for _ in range(env.scenario.step_limit):
            action, _ = policy.select(env, observation)
            intended = benchmark.action_descriptor(env, action)
            observation, _, terminated, truncated, info = env.step(action)
            policy.observe(intended, info)
            audit = env.last_reversal_audit
            self.assertIsNotNone(audit)
            saw_trigger = saw_trigger or bool(audit["triggered_this_step"])
            saw_mapping = saw_mapping or bool(audit["mapping_applied"])
            if saw_mapping or terminated or truncated:
                break
        self.assertTrue(saw_trigger)
        self.assertTrue(saw_mapping)
        self.assertEqual(audit["intended_action"]["kind"], "Exploit")
        self.assertEqual(audit["effective_action"]["kind"], "ProcessScan")

    def test_numpy_network_update_is_seed_deterministic(self) -> None:
        agents = [neural.NeuralQAgent(8, 3, 319, warmup=2, batch_size=2) for _ in range(2)]
        transition = neural.Transition(
            features=np.arange(8, dtype=np.float64) / 8,
            action=1,
            scaled_reward=0.5,
            next_features=np.arange(8, dtype=np.float64)[::-1] / 8,
            done=False,
        )
        for agent in agents:
            agent.learn(transition)
            metrics = agent.learn(transition)
            self.assertIsNotNone(metrics["loss"])
        for name in agents[0].online.params:
            np.testing.assert_array_equal(
                agents[0].online.params[name], agents[1].online.params[name]
            )

    def test_bounded_pilot_writes_q_surface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pilot"
            summary = neural.run_benchmark(output, 319, 3, 1)
            self.assertTrue(summary["unfavorable_outcomes_retained"])
            self.assertTrue((output / "steps.jsonl.gz").is_file())
            self.assertTrue((output / "surface/q_lattice.tsv").is_file())
            self.assertTrue((output / "surface/q_lattice.html").is_file())
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(manifest["neural_architecture"]["hidden"], 32)
            self.assertTrue(manifest["all_actions_through_gym_step"])


if __name__ == "__main__":
    unittest.main()
