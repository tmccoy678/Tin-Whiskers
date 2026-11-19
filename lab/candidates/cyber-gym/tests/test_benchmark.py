from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

import benchmark


class CyberGymBenchmarkTests(unittest.TestCase):
    def test_scenarios_are_shape_compatible(self) -> None:
        train = benchmark.make_env("train-chain")
        heldout = benchmark.make_env("heldout-branch")
        self.assertEqual(train.action_space.n, heldout.action_space.n)
        self.assertEqual(train.observation_space.shape, heldout.observation_space.shape)
        self.assertEqual(train.scenario.step_limit, 24)
        self.assertEqual(heldout.scenario.step_limit, 24)

    def test_fixed_rule_is_seed_reproducible(self) -> None:
        comparable = []
        for _ in range(2):
            env = benchmark.make_env("train-chain")
            episode, steps = benchmark.run_episode(
                env=env,
                scenario="train-chain",
                policy_name="fixed-rule",
                policy=benchmark.FixedRulePolicy(),
                phase="test",
                episode=0,
                episode_seed=319,
                q_policy=None,
            )
            comparable.append({
                "success": episode["success"],
                "reward": episode["reward"],
                "actions": [row["action"]["index"] for row in steps],
                "rewards": [row["reward"] for row in steps],
            })
        self.assertEqual(comparable[0], comparable[1])

    def test_bounded_run_writes_exact_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pilot"
            summary = benchmark.run_benchmark(output, 319, 3, 2)
            self.assertTrue(summary["unfavorable_outcomes_retained"])
            episode_rows = [
                json.loads(line)
                for line in (output / "episodes.jsonl").read_text().splitlines()
            ]
            step_rows = [
                json.loads(line)
                for line in (output / "steps.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(episode_rows), 3 + (2 * 3 * 2))
            self.assertTrue(step_rows)
            self.assertTrue(all(row["environment_queries_step"] == 1 for row in step_rows))
            self.assertTrue(all(row["safe_service_fraction"] == 1.0 for row in step_rows))
            self.assertTrue(all(row["service_disruption_events"] == 0 for row in step_rows))
            self.assertTrue(all(row["q_value_queries_step"] >= 0 for row in step_rows))


if __name__ == "__main__":
    unittest.main()
