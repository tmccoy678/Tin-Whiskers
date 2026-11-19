from __future__ import annotations

import csv
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "valid"
sys.path.insert(0, str(ROOT))

from evaluation_harness import (  # noqa: E402
    ValidationError,
    compute_contrasts,
    load_and_validate,
)


class HarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name) / "fixture"
        shutil.copytree(FIXTURE, self.data)
        self.config = ROOT / "config.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def rows(self, filename: str):
        path = self.data / filename
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            return list(reader.fieldnames or ()), list(reader)

    def write_rows(self, filename: str, fields, rows) -> None:
        path = self.data / filename
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def mutate(self, filename: str, run_id: str, **changes: str) -> None:
        fields, rows = self.rows(filename)
        matched = False
        for row in rows:
            if row["run_id"] == run_id:
                row.update(changes)
                matched = True
                break
        self.assertTrue(matched)
        self.write_rows(filename, fields, rows)

    def validate(self):
        return load_and_validate(self.data, self.config)

    def test_valid_fixture_computes_u_and_contrasts(self) -> None:
        result = compute_contrasts(self.validate())
        self.assertEqual(result["inference"], "not_run")
        self.assertEqual(result["unit_U"]["A001"], Decimal("0.95"))
        self.assertEqual(result["unit_U"]["Y001"], Decimal("0.75"))
        block = result["block_contrasts"][0]
        self.assertEqual(block["best_fixed_condition"], "F36")
        self.assertEqual(block["A_minus_Y"], Decimal("0.20"))
        self.assertEqual(block["A_minus_best_fixed"], Decimal("0.175"))

    def test_rejects_schema_change(self) -> None:
        fields, rows = self.rows("samples.tsv")
        fields.remove("dt_s")
        for row in rows:
            row.pop("dt_s")
        self.write_rows("samples.tsv", fields, rows)
        with self.assertRaisesRegex(ValidationError, "schema mismatch"):
            self.validate()

    def test_rejects_missing_condition(self) -> None:
        fields, rows = self.rows("design.tsv")
        rows = [row for row in rows if row["condition"] != "Y"]
        self.write_rows("design.tsv", fields, rows)
        with self.assertRaisesRegex(ValidationError, "one row per six conditions"):
            self.validate()

    def test_rejects_budget_mismatch(self) -> None:
        self.mutate("design.tsv", "Y001", E0_J="101")
        with self.assertRaisesRegex(ValidationError, "within-block identity failed for E0_J"):
            self.validate()

    def test_rejects_duplicate_rng_stream(self) -> None:
        self.mutate("design.tsv", "Y001", damage_rng_id="growth-a001")
        with self.assertRaisesRegex(ValidationError, "duplicate RNG stream"):
            self.validate()

    def test_rejects_schedule_hash_mismatch(self) -> None:
        self.mutate("design.tsv", "Y001", schedule_hash="schedule-other")
        with self.assertRaisesRegex(ValidationError, "schedule_hash"):
            self.validate()

    def test_rejects_yoke_command_mismatch(self) -> None:
        fields, rows = self.rows("samples.tsv")
        for row in rows:
            if row["run_id"] == "Y001" and row["time_s"] == "1":
                row["command_hash"] = "wrong-action"
        self.write_rows("samples.tsv", fields, rows)
        with self.assertRaisesRegex(ValidationError, "A/Y yoke command hashes"):
            self.validate()

    def test_rejects_containment_code_mismatch(self) -> None:
        self.mutate("samples.tsv", "W001", containment_code="LIMIT_CONTAINMENT")
        with self.assertRaisesRegex(ValidationError, "containment state/code mismatch"):
            self.validate()

    def test_rejects_exclusion_code_mismatch(self) -> None:
        self.mutate("unit-summary.tsv", "A001", exclusion_code="PROTOCOL_DEVIATION")
        with self.assertRaisesRegex(ValidationError, "validity/exclusion code mismatch"):
            self.validate()

    def test_rejects_f24_f36_provenance_pooling(self) -> None:
        fields, rows = self.rows("design.tsv")
        f24_hash = next(row["fixed_rule_hash"] for row in rows if row["condition"] == "F24")
        for row in rows:
            if row["condition"] == "F36":
                row["fixed_rule_hash"] = f24_hash
        self.write_rows("design.tsv", fields, rows)
        with self.assertRaisesRegex(ValidationError, "provenance pooling"):
            self.validate()


if __name__ == "__main__":
    unittest.main()
