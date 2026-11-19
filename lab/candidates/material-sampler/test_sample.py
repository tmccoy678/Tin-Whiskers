#!/usr/bin/env python3

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("material_sampler", BASE / "sample.py")
SAMPLER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SAMPLER)


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class MaterialSamplerTests(unittest.TestCase):
    def test_same_seed_is_byte_stable(self):
        first = SAMPLER.generate_draw("earth", "exploratory", 319)
        second = SAMPLER.generate_draw("earth", "exploratory", 319)
        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(second, sort_keys=True, separators=(",", ":")),
        )

    def test_different_seed_changes_exploratory_draw(self):
        first = SAMPLER.generate_draw("earth", "exploratory", 319)
        second = SAMPLER.generate_draw("earth", "exploratory", 320)
        sampled_first = {
            path: record["selected_value"]
            for path, record in first["parameters"].items()
            if record["disposition"] == "sampled-proposed"
        }
        sampled_second = {
            path: record["selected_value"]
            for path, record in second["parameters"].items()
            if record["disposition"] == "sampled-proposed"
        }
        self.assertNotEqual(sampled_first, sampled_second)

    def test_only_proposed_ranges_are_sampled(self):
        draw = SAMPLER.generate_draw("earth", "exploratory", 319)
        for record in draw["parameters"].values():
            if record["disposition"] == "sampled-proposed":
                self.assertEqual(record["status"], "proposed")
                self.assertGreaterEqual(record["selected_value"], record["allowable_range"]["minimum"])
                self.assertLessEqual(record["selected_value"], record["allowable_range"]["maximum"])
            if record["status"] == "established":
                self.assertEqual(record["disposition"], "fixed-established")
                self.assertEqual(record["selected_value"], record["source_point_value"])

    def test_policy_cannot_promote_established_point_to_axis(self):
        policy = load_json(BASE / "policy.json")
        altered = copy.deepcopy(policy)
        altered["regimes"]["earth"]["sample_axes"].append(
            {
                "path": "numeric_parameters.geometry.gold_wire_diameter",
                "strategy": "uniform",
            }
        )
        with self.assertRaisesRegex(SAMPLER.SamplingError, "established points stay fixed"):
            SAMPLER.generate_draw("earth", "exploratory", 319, policy_document=altered)

    def test_space_screening_keeps_blockers_visible(self):
        draw = SAMPLER.generate_draw("space", "screening", 319)
        self.assertTrue(draw["accepted"])
        self.assertFalse(draw["promotion_eligible"])
        self.assertEqual(len(draw["required_unset_blockers"]), 8)
        self.assertTrue(any("Promotion is excluded" in item["reason"] for item in draw["rejected_combinations"]))

    def test_space_promotion_returns_complete_rejection(self):
        draw = SAMPLER.generate_draw("space", "promotion", 319)
        self.assertFalse(draw["accepted"])
        self.assertFalse(draw["promotion_eligible"])
        self.assertEqual(draw["selected_options"], {})
        self.assertTrue(draw["parameters"])
        self.assertTrue(all(record["disposition"] != "sampled-proposed" for record in draw["parameters"].values()))

    def test_options_are_admitted_and_constraints_hold(self):
        policy = load_json(BASE / "policy.json")["regimes"]["space"]
        for seed in range(32):
            draw = SAMPLER.generate_draw("space", "screening", seed)
            options = draw["selected_options"]
            for name, value in options.items():
                self.assertIn(value, policy["admitted_options"][name])
            if options["radiation_cohort"] == "unbiased-retention":
                self.assertEqual(options["operational_address"], "none-unbiased")
            else:
                self.assertNotEqual(options["operational_address"], "none-unbiased")

    def test_manifest_hash_matches_exact_source_bytes(self):
        draw = SAMPLER.generate_draw("earth", "exploratory", 319)
        source = SAMPLER.MANIFEST_BASE / "earth-pedot.json"
        self.assertEqual(draw["source_manifest_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())

    def test_regime_mode_separation_is_enforced(self):
        with self.assertRaisesRegex(SAMPLER.SamplingError, "not admitted"):
            SAMPLER.generate_draw("earth", "screening", 319)
        with self.assertRaisesRegex(SAMPLER.SamplingError, "not admitted"):
            SAMPLER.generate_draw("space", "exploratory", 319)

    def test_cli_requires_explicit_seed(self):
        result = subprocess.run(
            [sys.executable, str(BASE / "sample.py"), "--regime", "earth", "--mode", "exploratory"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--seed", result.stderr)


if __name__ == "__main__":
    unittest.main()
