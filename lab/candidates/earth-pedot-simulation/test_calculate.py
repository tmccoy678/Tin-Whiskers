#!/usr/bin/env python3

import copy
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("earth_pedot_calculator", BASE / "calculate.py")
CALCULATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CALCULATOR)


class EarthPedotCalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = CALCULATOR.calculate()
        cls.draw = json.loads((BASE / "seed-319-draw.json").read_text(encoding="utf-8"))

    def test_seed_and_manifest_provenance_survive(self):
        self.assertEqual(self.result["seed"], 319)
        self.assertEqual(
            self.result["source_manifest_sha256"],
            self.draw["source_manifest_sha256"],
        )

    def test_micrometres_convert_to_metres_with_range(self):
        path = "numeric_parameters.geometry.electrode_gap"
        source = self.draw["parameters"][path]
        translated = self.result["translated_inputs_si"][path]
        self.assertAlmostEqual(translated["selected"], source["selected_value"] * 1.0e-6)
        self.assertAlmostEqual(translated["minimum"], source["allowable_range"]["minimum"] * 1.0e-6)
        self.assertAlmostEqual(translated["maximum"], source["allowable_range"]["maximum"] * 1.0e-6)
        self.assertEqual(translated["unit"], "m")

    def test_peak_voltage_and_period_propagate_ranges(self):
        peak = self.result["derived_si"]["voltage_peak"]
        period = self.result["derived_si"]["waveform_period"]
        self.assertEqual(peak["range"], {"minimum": 3.5, "maximum": 5.0})
        self.assertAlmostEqual(period["range"]["minimum"], 1.0 / 320.0)
        self.assertAlmostEqual(period["range"]["maximum"], 1.0 / 10.0)

    def test_reservoir_interval_is_not_replaced_by_point(self):
        amount = self.result["derived_si"]["edot_amount_from_concentration_and_volume"]
        self.assertLess(amount["range"]["minimum"], amount["selected"])
        self.assertGreater(amount["range"]["maximum"], amount["selected"])
        consistency = self.result["dimensionless_groups"]["reservoir_amount_consistency"]
        self.assertLess(consistency["range"]["minimum"], consistency["selected"])
        self.assertGreater(consistency["range"]["maximum"], consistency["selected"])

    def test_optical_outputs_remain_incident_not_absorbed(self):
        optical = self.result["derived_si"]["incident_optical_energy_to_timeout"]
        self.assertIn("Incident energy only", optical["interpretation"])
        blocker_ids = {item["blocker_id"] for item in self.result["constitutive_blockers"]}
        self.assertIn("optical-constitutive", blocker_ids)

    def test_dimensionless_groups_have_ranges_or_explicit_blocker(self):
        for group in self.result["dimensionless_groups"].values():
            bounds = group["range"]
            finite_bounds = all(
                isinstance(bounds[key], (int, float)) and math.isfinite(bounds[key])
                for key in ("minimum", "maximum")
            )
            self.assertTrue(finite_bounds or "range_blocker" in group)

    def test_constitutive_categories_are_blocked_not_filled(self):
        blocker_ids = {item["blocker_id"] for item in self.result["constitutive_blockers"]}
        required = {
            "species-transport",
            "redox-kinetics",
            "phase-field-free-energy",
            "thermal-properties",
            "optical-constitutive",
            "stochastic-law",
        }
        self.assertTrue(required.issubset(blocker_ids))
        for blocker in self.result["constitutive_blockers"]:
            self.assertNotIn("value", blocker)

    def test_moose_admission_separates_ready_and_screening(self):
        admission = self.result["moose_admission"]
        self.assertIn(
            "numeric_parameters.geometry.electrode_gap",
            admission["can_enter_now"],
        )
        self.assertIn(
            "numeric_parameters.admission_metrics.minimum_effective_conductivity",
            admission["conditional_screening_or_metadata"],
        )
        self.assertIn("redox-kinetics", admission["cannot_enter_without_constitutive_data"])

    def test_threshold_group_carries_uncertainty_boundary(self):
        group = self.result["dimensionless_groups"]["conditional_voltage_to_polymerization_threshold"]
        self.assertIn("uncertainty_blocker", group)
        self.assertIn("published nominal", group["range_basis"])

    def test_source_manifest_hash_mismatch_is_rejected(self):
        draw = copy.deepcopy(self.draw)
        draw["source_manifest_sha256"] = "0" * 64
        deck = json.loads((BASE / "parameter-deck.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(CALCULATOR.TranslationError, "no longer matches"):
            CALCULATOR.translate(draw, deck, "draw-hash", "deck-hash")

    def test_cli_emits_valid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "translation.json"
            result = subprocess.run(
                [sys.executable, str(BASE / "calculate.py"), "--output", str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(document["seed"], 319)


if __name__ == "__main__":
    unittest.main()
