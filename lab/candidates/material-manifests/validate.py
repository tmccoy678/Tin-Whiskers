#!/usr/bin/env python3
"""Dependency-free structural and semantic validator for candidate manifests."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0.0"
ROOT_KEYS = {
    "schema_version",
    "candidate_id",
    "regime",
    "state",
    "derived_from",
    "separation_contract",
    "materials",
    "interfaces",
    "numeric_parameters",
    "required_unset_gates",
    "gates",
    "sources",
}
QUANTITY_KEYS = {
    "value",
    "unit",
    "status",
    "provenance",
    "allowable_range",
    "hard_stop",
}
SPACE_REQUIRED_UNSET = {
    "mission_total_ionizing_dose",
    "mission_single_event_let_threshold",
    "mission_heavy_ion_fluence",
    "mission_displacement_damage_fluence",
    "mission_lifetime",
    "mission_shielding_areal_density",
    "mission_operational_temperature_minimum",
    "mission_operational_temperature_maximum",
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_quantity(value: Any) -> bool:
    return isinstance(value, dict) and QUANTITY_KEYS.issubset(value)


def _hard_stop_valid(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"condition", "action"}
        and all(isinstance(value[key], str) and value[key].strip() for key in value)
    )


def _validate_quantity(quantity: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    extra = set(quantity) - QUANTITY_KEYS
    missing = QUANTITY_KEYS - set(quantity)
    if extra:
        errors.append(f"{path}: unexpected quantity fields {sorted(extra)}")
    if missing:
        errors.append(f"{path}: missing quantity fields {sorted(missing)}")
        return errors

    unit = quantity["unit"]
    status = quantity["status"]
    value = quantity["value"]
    provenance = quantity["provenance"]
    allowed = quantity["allowable_range"]
    hard_stop = quantity["hard_stop"]

    if not isinstance(unit, str) or not unit.strip():
        errors.append(f"{path}.unit: must be a non-empty SI or declared engineering unit")
    if status not in {"established", "proposed", "required-unset"}:
        errors.append(f"{path}.status: invalid status {status!r}")

    if not isinstance(provenance, dict) or set(provenance) != {"kind", "text", "url"}:
        errors.append(f"{path}.provenance: must contain exactly kind, text, and url")
    else:
        kind = provenance["kind"]
        text = provenance["text"]
        url = provenance["url"]
        if kind not in {"source", "rationale"}:
            errors.append(f"{path}.provenance.kind: must be source or rationale")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{path}.provenance.text: must be non-empty")
        if kind == "source" and (not isinstance(url, str) or not url.startswith("https://")):
            errors.append(f"{path}.provenance.url: sourced values require a direct https URL")
        if kind == "rationale" and url is not None and not isinstance(url, str):
            errors.append(f"{path}.provenance.url: rationale URL must be a string or null")

    if not isinstance(allowed, dict) or set(allowed) != {"minimum", "maximum", "inclusive"}:
        errors.append(f"{path}.allowable_range: must contain exactly minimum, maximum, and inclusive")
        return errors
    minimum = allowed["minimum"]
    maximum = allowed["maximum"]
    if not isinstance(allowed["inclusive"], bool):
        errors.append(f"{path}.allowable_range.inclusive: must be boolean")

    if status == "required-unset":
        if value is not None:
            errors.append(f"{path}.value: required-unset gates must remain null")
        if minimum is not None or maximum is not None:
            errors.append(f"{path}.allowable_range: required-unset gates must have null bounds")
        if not _hard_stop_valid(hard_stop):
            errors.append(f"{path}.hard_stop: required-unset gates must block promotion")
    else:
        if not _is_number(value) or not math.isfinite(value):
            errors.append(f"{path}.value: established/proposed quantities require a finite number")
        if not _is_number(minimum) or not _is_number(maximum):
            errors.append(f"{path}.allowable_range: numeric quantities require numeric bounds")
        elif minimum > maximum:
            errors.append(f"{path}.allowable_range: minimum exceeds maximum")
        elif _is_number(value) and not minimum <= value <= maximum:
            errors.append(f"{path}.value: value lies outside allowable range")
        if hard_stop is not None and not _hard_stop_valid(hard_stop):
            errors.append(f"{path}.hard_stop: must be null or contain condition and action")

    return errors


def _walk_no_raw_numbers(node: Any, path: str) -> tuple[list[str], int]:
    if _is_quantity(node):
        return _validate_quantity(node, path), 1
    if _is_number(node):
        return [f"{path}: raw numeric leaf is forbidden; use a quantity object"], 0
    if isinstance(node, dict):
        errors: list[str] = []
        count = 0
        for key, value in node.items():
            child_errors, child_count = _walk_no_raw_numbers(value, f"{path}.{key}")
            errors.extend(child_errors)
            count += child_count
        return errors, count
    if isinstance(node, list):
        errors = []
        count = 0
        for index, value in enumerate(node):
            child_errors, child_count = _walk_no_raw_numbers(value, f"{path}[{index}]")
            errors.extend(child_errors)
            count += child_count
        return errors, count
    return [], 0


def validate_document(document: Any, schema_document: Any) -> tuple[list[str], int]:
    errors: list[str] = []
    if not isinstance(schema_document, dict) or "$defs" not in schema_document:
        return ["schema.json: missing JSON Schema definitions"], 0
    if not isinstance(document, dict):
        return ["$: manifest root must be an object"], 0

    missing = ROOT_KEYS - set(document)
    extra = set(document) - ROOT_KEYS
    if missing:
        errors.append(f"$: missing root fields {sorted(missing)}")
    if extra:
        errors.append(f"$: unexpected root fields {sorted(extra)}")
    if missing:
        return errors, 0

    if document["schema_version"] != SCHEMA_VERSION:
        errors.append(f"$.schema_version: expected {SCHEMA_VERSION}")

    candidate_id = document["candidate_id"]
    regime = document["regime"]
    expected = {"earth": "earth-pedot", "space": "space-cbram"}
    if regime not in expected:
        errors.append("$.regime: must be earth or space")
    elif candidate_id != expected[regime]:
        errors.append(f"$.candidate_id: {regime} regime requires {expected[regime]}")

    contract = document["separation_contract"]
    if not isinstance(contract, dict):
        errors.append("$.separation_contract: must be an object")
    else:
        if contract.get("regime_id") != regime:
            errors.append("$.separation_contract.regime_id: must match root regime")
        if contract.get("forbidden_regime_id") == regime:
            errors.append("$.separation_contract.forbidden_regime_id: must name the other regime")
        if contract.get("prohibits_cross_regime_parameter_import") is not True:
            errors.append("$.separation_contract: cross-regime numeric import must be prohibited")

    unset = document["required_unset_gates"]
    if not isinstance(unset, dict):
        errors.append("$.required_unset_gates: must be an object")
    elif regime == "space":
        missing_unset = SPACE_REQUIRED_UNSET - set(unset)
        if missing_unset:
            errors.append(f"$.required_unset_gates: missing mission gates {sorted(missing_unset)}")
        for key, value in unset.items():
            if not _is_quantity(value) or value.get("status") != "required-unset":
                errors.append(f"$.required_unset_gates.{key}: must be a required-unset quantity")
    elif unset:
        errors.append("$.required_unset_gates: Earth manifest must not inherit space mission gates")

    source_ids: set[str] = set()
    sources = document["sources"]
    if not isinstance(sources, list):
        errors.append("$.sources: must be a list")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                errors.append(f"$.sources[{index}]: must be an object")
                continue
            source_id = source.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                errors.append(f"$.sources[{index}].source_id: must be non-empty")
            elif source_id in source_ids:
                errors.append(f"$.sources[{index}].source_id: duplicate {source_id}")
            else:
                source_ids.add(source_id)

    numeric_errors, quantity_count = _walk_no_raw_numbers(document, "$")
    errors.extend(numeric_errors)
    return errors, quantity_count


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_path(path: Path, schema_path: Path) -> tuple[list[str], int]:
    try:
        schema_document = load_json(schema_path)
    except (OSError, json.JSONDecodeError) as error:
        return [f"{schema_path}: cannot load schema: {error}"], 0
    try:
        document = load_json(path)
    except (OSError, json.JSONDecodeError) as error:
        return [f"{path}: cannot load manifest: {error}"], 0
    return validate_document(document, schema_document)


def main(argv: list[str] | None = None) -> int:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="*", type=Path)
    parser.add_argument("--schema", type=Path, default=base / "schema.json")
    args = parser.parse_args(argv)
    manifests = args.manifests or [base / "earth-pedot.json", base / "space-cbram.json"]

    failed = False
    for manifest in manifests:
        errors, count = validate_path(manifest, args.schema)
        if errors:
            failed = True
            print(f"INVALID {manifest}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"VALID {manifest} ({count} quantities)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
