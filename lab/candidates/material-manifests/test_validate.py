#!/usr/bin/env python3

import copy
import importlib.util
import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("material_manifest_validator", BASE / "validate.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)
validate_document = VALIDATOR.validate_document


def load(name):
    with (BASE / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


class ManifestValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = load("schema.json")
        cls.earth = load("earth-pedot.json")
        cls.space = load("space-cbram.json")

    def test_repository_manifests_validate(self):
        for document in (self.earth, self.space):
            errors, count = validate_document(document, self.schema)
            self.assertEqual(errors, [])
            self.assertGreater(count, 0)

    def test_raw_numeric_leaf_is_rejected(self):
        document = copy.deepcopy(self.earth)
        document["unwrapped_number"] = 319
        errors, _ = validate_document(document, self.schema)
        self.assertTrue(any("raw numeric leaf" in error for error in errors))

    def test_value_outside_range_is_rejected(self):
        document = copy.deepcopy(self.earth)
        quantity = document["numeric_parameters"]["environment"]["temperature"]
        quantity["value"] = quantity["allowable_range"]["maximum"] + 1
        errors, _ = validate_document(document, self.schema)
        self.assertTrue(any("outside allowable range" in error for error in errors))

    def test_required_unset_cannot_hide_a_value(self):
        document = copy.deepcopy(self.space)
        gate = document["required_unset_gates"]["mission_total_ionizing_dose"]
        gate["value"] = 1
        errors, _ = validate_document(document, self.schema)
        self.assertTrue(any("must remain null" in error for error in errors))

    def test_regimes_cannot_be_relabeled(self):
        document = copy.deepcopy(self.earth)
        document["regime"] = "space"
        errors, _ = validate_document(document, self.schema)
        self.assertTrue(any("requires space-cbram" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
