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
SPEC = importlib.util.spec_from_file_location("space_cbram_calculator", BASE / "calculate.py")
CALCULATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CALCULATOR)


class SpaceCbramCalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = CALCULATOR.calculate()
        cls.draw = json.loads((BASE / "seed-319-draw.json").read_text(encoding="utf-8"))

    def test_seed_and_manifest_provenance_survive(self):
        self.assertEqual(self.result["seed"], 319)
        self.assertEqual(self.result["source_manifest_sha256"], self.draw["source_manifest_sha256"])

    def test_all_mission_blockers_are_preserved_null(self):
        gates = self.result["mission_gates"]
        self.assertEqual(len(gates), 8)
        self.assertEqual(sorted(gates), sorted(self.draw["required_unset_blockers"]))
        for gate in gates.values():
            self.assertIsNone(gate["value"])
            self.assertEqual(gate["status"], "required-unset")
            self.assertIsNotNone(gate["hard_stop"])

    def test_terminal_conductance_remains_primary(self):
        observable = self.result["reversible_filament_observable"]
        self.assertIsNotNone(observable["terminal_on_conductance"]["selected"])
        self.assertEqual(observable["bulk_silver_conductivity_reference"]["admission"], "reference-only")
        self.assertIsNone(observable["filament_conductivity"]["value"])
        self.assertEqual(observable["filament_conductivity"]["status"], "blocked")

    def test_reservoir_mass_propagates_sampled_geometry(self):
        mass = self.result["derived_si"]["silver_reservoir_mass_from_sampled_geometry"]
        self.assertLess(mass["range"]["minimum"], mass["selected"])
        self.assertGreater(mass["range"]["maximum"], mass["selected"])
        consistency = self.result["dimensionless_groups"]["reservoir_mass_consistency"]
        self.assertLess(consistency["range"]["minimum"], consistency["selected"])
        self.assertGreater(consistency["range"]["maximum"], consistency["selected"])

    def test_nominal_fields_are_descriptors_with_ranges(self):
        for name in ("nominal_set_field", "nominal_reset_field_magnitude"):
            field = self.result["derived_si"][name]
            self.assertEqual(field["unit"], "V m^-1")
            self.assertIn("descriptor", field["interpretation"])
            self.assertLessEqual(field["range"]["minimum"], field["selected"])
            self.assertGreaterEqual(field["range"]["maximum"], field["selected"])

    def test_openmc_doses_are_targets_not_sources(self):
        targets = self.result["openmc_screening_targets"]["absorbed_dose_targets"]
        self.assertEqual(len(targets), 4)
        self.assertTrue(all(target["not_a_source"] for target in targets))
        self.assertTrue(all(target["material_basis"] == "silicon" for target in targets))
        self.assertIn("blocked", self.result["openmc_screening_targets"]["normalization_status"])

    def test_solver_admission_names_each_coupling_domain(self):
        admission = self.result["solver_admission"]
        self.assertTrue(admission["moose_conduction"])
        self.assertTrue(admission["moose_thermal"])
        self.assertTrue(admission["moose_mechanics"])
        self.assertTrue(admission["openmc_geometry_material"])
        self.assertTrue(admission["openmc_tally_targets"])
        self.assertEqual(len(admission["mission_gated"]), 8)

    def test_dimensionless_groups_have_ranges_or_explicit_blocker(self):
        for group in self.result["dimensionless_groups"].values():
            bounds = group["range"]
            finite = all(
                isinstance(bounds[key], (int, float)) and math.isfinite(bounds[key])
                for key in ("minimum", "maximum")
            )
            self.assertTrue(finite or "range_blocker" in group)

    def test_constitutive_categories_remain_blocked(self):
        ids = {item["blocker_id"] for item in self.result["constitutive_blockers"]}
        required = {
            "filament-geometry",
            "solid-electrolyte-ion-transport",
            "layer-thermal-properties",
            "layer-mechanical-properties",
            "openmc-material-definitions",
            "mission-radiation-source",
            "dose-material-conversion",
            "displacement-and-see-response",
        }
        self.assertTrue(required.issubset(ids))
        for blocker in self.result["constitutive_blockers"]:
            self.assertNotIn("value", blocker)

    def test_source_manifest_hash_mismatch_is_rejected(self):
        draw = copy.deepcopy(self.draw)
        draw["source_manifest_sha256"] = "0" * 64
        deck = json.loads((BASE / "parameter-deck.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(CALCULATOR.TranslationError, "no longer matches"):
            CALCULATOR.translate(draw, deck, "draw-hash", "deck-hash", "draw.json")

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
            self.assertEqual(len(document["mission_gates"]), 8)


if __name__ == "__main__":
    unittest.main()
