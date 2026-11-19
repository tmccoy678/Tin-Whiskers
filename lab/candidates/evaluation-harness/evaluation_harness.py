#!/usr/bin/env python3
"""Validate candidate evaluation records and compute descriptive contrasts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable


SCHEMAS: dict[str, tuple[str, ...]] = {
    "design.tsv": (
        "run_id", "block_id", "batch_id", "condition", "position_code",
        "microstate_seed", "policy_rng_id", "growth_rng_id", "damage_rng_id",
        "schedule_hash", "controller_hash", "fixed_rule_hash",
        "lesion_algorithm_hash", "material_hash", "M0_kg", "E0_J", "P0_W",
        "T0_K", "yoke_donor",
    ),
    "events.tsv": (
        "run_id", "time_s", "episode", "load_id", "source_pad", "sink_pad",
        "I_req_A", "damage_id", "damage_type", "mask_hash",
        "removed_volume_m3", "event_blind_code",
    ),
    "samples.tsv": (
        "run_id", "time_s", "dt_s", "episode", "I_req_A", "I_del_A", "V_V",
        "Jmax_A_m2", "Tmax_K", "Smax_Pa", "M_used_kg", "E_load_J",
        "E_actuator_J", "E_sensor_J", "E_compute_J", "P_cool_W",
        "command_hash", "containment_state", "containment_code",
    ),
    "unit-summary.tsv": (
        "run_id", "block_id", "batch_id", "condition", "U",
        "delivered_charge_C", "recovery_s", "Jstar_m2_inv", "Hstar_J_C",
        "control_energy_J", "irreversible_failure", "valid", "exclusion_code",
    ),
}

ZERO = Decimal("0")
ONE = Decimal("1")


class ValidationError(ValueError):
    """The record cannot support the declared evaluation."""


@dataclass(frozen=True)
class Dataset:
    config: dict[str, Any]
    design: list[dict[str, str]]
    events: list[dict[str, str]]
    samples: list[dict[str, str]]
    summaries: list[dict[str, str]]


def number(value: Any, label: str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{label}: expected decimal, got {value!r}") from exc
    if not parsed.is_finite():
        raise ValidationError(f"{label}: non-finite value")
    return parsed


def truth(value: str, label: str) -> bool:
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    raise ValidationError(f"{label}: expected true or false, got {value!r}")


def read_tsv(directory: Path, filename: str) -> list[dict[str, str]]:
    path = directory / filename
    if not path.is_file():
        raise ValidationError(f"missing required table: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        actual = tuple(reader.fieldnames or ())
        if actual != SCHEMAS[filename]:
            raise ValidationError(
                f"{filename}: schema mismatch; expected {SCHEMAS[filename]}, got {actual}"
            )
        rows: list[dict[str, str]] = []
        for line, row in enumerate(reader, 2):
            if any(value is None or value.strip() == "" for value in row.values()):
                raise ValidationError(
                    f"{filename}:{line}: every field must be explicit; use NONE when applicable"
                )
            rows.append({key: value.strip() for key, value in row.items()})
    if not rows:
        raise ValidationError(f"{filename}: table is empty")
    return rows


def load_config(path: Path) -> dict[str, Any]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot load configuration {path}: {exc}") from exc
    required = {
        "schema_version", "conditions", "fixed_conditions",
        "fixed_rule_provenance", "safety_limits", "containment_codes",
        "terminal_containment_states", "exclusion_codes", "u_tolerance",
        "inference",
    }
    if set(config) != required:
        raise ValidationError("configuration keys are incomplete or unexpected")
    if config["conditions"] != ["W", "G", "F24", "F36", "A", "Y"]:
        raise ValidationError("configuration must preserve the six declared conditions")
    if config["fixed_conditions"] != ["W", "G", "F24", "F36"]:
        raise ValidationError("fixed_conditions must keep F24 and F36 separate")
    provenance = config["fixed_rule_provenance"]
    if set(provenance) != {"F24", "F36"} or provenance["F24"] == provenance["F36"]:
        raise ValidationError("F24/F36 provenance pooling is forbidden")
    for key in ("J_lim_A_m2", "T_lim_K", "S_lim_Pa"):
        if key not in config["safety_limits"] or number(
            config["safety_limits"].get(key), f"safety_limits.{key}"
        ) <= 0:
            raise ValidationError(f"safety_limits.{key} must be positive")
    inference_keys = {
        "bootstrap_resamples", "alpha_one_sided", "target_power", "delta_star",
        "maximum_blocks", "information_fractions", "obrien_fleming_z",
    }
    if set(config["inference"]) != inference_keys:
        raise ValidationError("inference configuration keys are incomplete or unexpected")
    return config


def unique(rows: Iterable[dict[str, str]], key: str, label: str) -> None:
    seen: set[str] = set()
    for row in rows:
        if row[key] in seen:
            raise ValidationError(f"{label}: duplicate {key} {row[key]!r}")
        seen.add(row[key])


def validate_design(rows: list[dict[str, str]], config: dict[str, Any]):
    unique(rows, "run_id", "design.tsv")
    by_run = {row["run_id"]: row for row in rows}
    by_block: dict[str, list[dict[str, str]]] = defaultdict(list)
    expected = set(config["conditions"])
    seeds: set[str] = set()
    rng_ids: set[str] = set()
    for row in rows:
        if row["condition"] not in expected:
            raise ValidationError(f"design.tsv: unknown condition {row['condition']!r}")
        by_block[row["block_id"]].append(row)
        for field in ("M0_kg", "E0_J", "P0_W", "T0_K"):
            if number(row[field], f"design {row['run_id']} {field}") <= 0:
                raise ValidationError(f"design {row['run_id']}: {field} must be positive")
        if row["microstate_seed"] in seeds:
            raise ValidationError(f"design.tsv: duplicate microstate_seed {row['microstate_seed']!r}")
        seeds.add(row["microstate_seed"])
        for field in ("policy_rng_id", "growth_rng_id", "damage_rng_id"):
            stream = row[field]
            if stream == "NONE" or stream in rng_ids:
                raise ValidationError(f"design.tsv: missing or duplicate RNG stream identifier {stream!r}")
            rng_ids.add(stream)

    for block_id, block_rows in by_block.items():
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in block_rows:
            grouped[row["condition"]].append(row)
        if set(grouped) != expected or any(len(grouped[c]) != 1 for c in expected):
            observed = sorted(row["condition"] for row in block_rows)
            raise ValidationError(
                f"block {block_id}: expected one row per six conditions; observed {observed}"
            )
        for field in (
            "M0_kg", "E0_J", "P0_W", "T0_K", "schedule_hash", "batch_id",
            "material_hash", "lesion_algorithm_hash",
        ):
            values = {row[field] for row in block_rows}
            if len(values) != 1:
                raise ValidationError(f"block {block_id}: within-block identity failed for {field}")
        f24, f36 = grouped["F24"][0], grouped["F36"][0]
        if f24["fixed_rule_hash"] == f36["fixed_rule_hash"]:
            raise ValidationError(f"block {block_id}: F24/F36 provenance pooling is forbidden")
        for condition, expected_hash in config["fixed_rule_provenance"].items():
            if grouped[condition][0]["fixed_rule_hash"] != expected_hash:
                raise ValidationError(f"block {block_id}: {condition} provenance mismatch")
        for condition in ("W", "G", "A", "Y"):
            if grouped[condition][0]["fixed_rule_hash"] != "NONE":
                raise ValidationError(f"block {block_id}: {condition} has fixed-rule provenance")
        adaptive, yoke = grouped["A"][0], grouped["Y"][0]
        if yoke["yoke_donor"] != adaptive["run_id"]:
            raise ValidationError(f"block {block_id}: Y must name A as yoke_donor")
        for condition in ("W", "G", "F24", "F36", "A"):
            if grouped[condition][0]["yoke_donor"] != "NONE":
                raise ValidationError(f"block {block_id}: only Y may name a yoke donor")
    return by_run, by_block


def validate_events(rows: list[dict[str, str]], design_by_run):
    by_run: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        run_id = row["run_id"]
        if run_id not in design_by_run:
            raise ValidationError(f"events.tsv: unknown run_id {run_id!r}")
        key = (run_id, row["time_s"], row["event_blind_code"])
        if key in seen:
            raise ValidationError(f"events.tsv: duplicate event key {key}")
        seen.add(key)
        if number(row["time_s"], f"event {key} time_s") < 0:
            raise ValidationError(f"event {key}: negative time")
        if number(row["I_req_A"], f"event {key} I_req_A") <= 0:
            raise ValidationError(f"event {key}: nonpositive demand")
        if number(row["removed_volume_m3"], f"event {key} volume") < 0:
            raise ValidationError(f"event {key}: negative removed volume")
        by_run[run_id].append(row)
    missing = sorted(set(design_by_run) - set(by_run))
    if missing:
        raise ValidationError(f"events.tsv: runs without events: {missing}")
    for run_rows in by_run.values():
        run_rows.sort(key=lambda row: number(row["time_s"], "event time"))
    return by_run


def active_event(events, time_s: Decimal):
    active = None
    for event in events:
        if number(event["time_s"], "event time") <= time_s:
            active = event
        else:
            break
    return active


def validate_samples(rows, design_by_run, events_by_run, config):
    by_run: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    nonnegative = (
        "time_s", "I_del_A", "Jmax_A_m2", "Tmax_K", "Smax_Pa", "M_used_kg",
        "E_load_J", "E_actuator_J", "E_sensor_J", "E_compute_J", "P_cool_W",
    )
    for row in rows:
        run_id = row["run_id"]
        if run_id not in design_by_run:
            raise ValidationError(f"samples.tsv: unknown run_id {run_id!r}")
        key = (run_id, row["time_s"])
        if key in seen:
            raise ValidationError(f"samples.tsv: duplicate sample key {key}")
        seen.add(key)
        for field in nonnegative:
            if number(row[field], f"sample {key} {field}") < 0:
                raise ValidationError(f"sample {key}: negative {field}")
        number(row["V_V"], f"sample {key} V_V")
        if number(row["dt_s"], f"sample {key} dt_s") <= 0 or number(
            row["I_req_A"], f"sample {key} I_req_A"
        ) <= 0:
            raise ValidationError(f"sample {key}: dt and demand must be positive")
        state = row["containment_state"]
        codes = config["containment_codes"]
        if state not in codes or row["containment_code"] != codes.get(state):
            raise ValidationError(f"sample {key}: containment state/code mismatch")
        event = active_event(events_by_run[run_id], number(row["time_s"], "sample time"))
        if event is None or row["episode"] != event["episode"]:
            raise ValidationError(f"sample {key}: no matching active event episode")
        if number(row["I_req_A"], "sample demand") != number(event["I_req_A"], "event demand"):
            raise ValidationError(f"sample {key}: demand differs from active event")
        by_run[run_id].append(row)
    missing = sorted(set(design_by_run) - set(by_run))
    if missing:
        raise ValidationError(f"samples.tsv: runs without samples: {missing}")
    energy_fields = ("E_load_J", "E_actuator_J", "E_sensor_J", "E_compute_J")
    for run_id, run_rows in by_run.items():
        run_rows.sort(key=lambda row: number(row["time_s"], "sample time"))
        previous = {field: ZERO for field in energy_fields}
        for row in run_rows:
            for field in energy_fields:
                value = number(row[field], f"sample {run_id} {field}")
                if value < previous[field]:
                    raise ValidationError(f"sample {run_id}: cumulative {field} decreased")
                previous[field] = value
    return by_run


def validate_yoke(samples_by_run, design_by_block) -> None:
    for block_id, design_rows in design_by_block.items():
        conditions = {row["condition"]: row for row in design_rows}
        def sequence(condition: str):
            return [
                (row["time_s"], row["command_hash"], row["E_actuator_J"])
                for row in samples_by_run[conditions[condition]["run_id"]]
            ]
        if sequence("A") != sequence("Y"):
            raise ValidationError(
                f"block {block_id}: A/Y yoke command hashes or actuator energy differ"
            )


def compute_u(dataset: Dataset, samples_by_run) -> dict[str, Decimal]:
    design = {row["run_id"]: row for row in dataset.design}
    limits = dataset.config["safety_limits"]
    j_lim = number(limits["J_lim_A_m2"], "J limit")
    t_lim = number(limits["T_lim_K"], "T limit")
    s_lim = number(limits["S_lim_Pa"], "stress limit")
    terminal = set(dataset.config["terminal_containment_states"])
    result: dict[str, Decimal] = {}
    for run_id, rows in samples_by_run.items():
        m0 = number(design[run_id]["M0_kg"], "M0")
        e0 = number(design[run_id]["E0_J"], "E0")
        p0 = number(design[run_id]["P0_W"], "P0")
        numerator = denominator = ZERO
        terminated: set[str] = set()
        for row in rows:
            dt = number(row["dt_s"], "dt")
            denominator += dt
            if row["containment_state"] in terminal:
                terminated.add(row["episode"])
            energy = sum(
                (number(row[field], field) for field in (
                    "E_load_J", "E_actuator_J", "E_sensor_J", "E_compute_J"
                )), ZERO
            )
            safe = (
                row["containment_state"] == "OK" and row["episode"] not in terminated
                and number(row["Jmax_A_m2"], "Jmax") <= j_lim
                and number(row["Tmax_K"], "Tmax") <= t_lim
                and number(row["Smax_Pa"], "Smax") <= s_lim
                and number(row["M_used_kg"], "mass") <= m0 and energy <= e0
                and number(row["P_cool_W"], "cooling") <= p0
            )
            if safe:
                ratio = number(row["I_del_A"], "delivered") / number(row["I_req_A"], "demand")
                numerator += dt * min(ONE, ratio)
        if denominator <= 0:
            raise ValidationError(f"run {run_id}: zero observation duration")
        result[run_id] = numerator / denominator
    return result


def validate_summaries(rows, design_by_run, samples_by_run, computed_u, config):
    unique(rows, "run_id", "unit-summary.tsv")
    by_run = {row["run_id"]: row for row in rows}
    if set(by_run) != set(design_by_run):
        raise ValidationError("unit-summary.tsv: run set differs from design.tsv")
    exclusions = set(config["exclusion_codes"])
    tolerance = number(config["u_tolerance"], "u_tolerance")
    terminal = set(config["terminal_containment_states"])
    for run_id, row in by_run.items():
        for field in ("block_id", "batch_id", "condition"):
            if row[field] != design_by_run[run_id][field]:
                raise ValidationError(f"summary {run_id}: {field} differs from design")
        declared = number(row["U"], f"summary {run_id} U")
        if not ZERO <= declared <= ONE or abs(declared - computed_u[run_id]) > tolerance:
            raise ValidationError(f"summary {run_id}: U differs from computed value")
        for field in ("delivered_charge_C", "recovery_s", "Jstar_m2_inv", "Hstar_J_C", "control_energy_J"):
            if number(row[field], f"summary {run_id} {field}") < 0:
                raise ValidationError(f"summary {run_id}: negative {field}")
        valid = truth(row["valid"], f"summary {run_id} valid")
        if row["exclusion_code"] not in exclusions or valid != (row["exclusion_code"] == "NONE"):
            raise ValidationError(f"summary {run_id}: validity/exclusion code mismatch")
        observed_failure = any(sample["containment_state"] in terminal for sample in samples_by_run[run_id])
        if truth(row["irreversible_failure"], f"summary {run_id} failure") != observed_failure:
            raise ValidationError(f"summary {run_id}: irreversible_failure differs from samples")
    return by_run


def load_and_validate(directory: Path, config_path: Path) -> Dataset:
    config = load_config(config_path)
    design = read_tsv(directory, "design.tsv")
    events = read_tsv(directory, "events.tsv")
    samples = read_tsv(directory, "samples.tsv")
    summaries = read_tsv(directory, "unit-summary.tsv")
    design_by_run, design_by_block = validate_design(design, config)
    events_by_run = validate_events(events, design_by_run)
    samples_by_run = validate_samples(samples, design_by_run, events_by_run, config)
    validate_yoke(samples_by_run, design_by_block)
    dataset = Dataset(config, design, events, samples, summaries)
    computed = compute_u(dataset, samples_by_run)
    validate_summaries(summaries, design_by_run, samples_by_run, computed, config)
    return dataset


def compute_contrasts(dataset: Dataset) -> dict[str, Any]:
    samples: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in dataset.samples:
        samples[row["run_id"]].append(row)
    for run_rows in samples.values():
        run_rows.sort(key=lambda row: number(row["time_s"], "sample time"))
    unit_u = compute_u(dataset, samples)
    summaries = {row["run_id"]: row for row in dataset.summaries}
    blocks: dict[str, dict[str, str]] = defaultdict(dict)
    for row in dataset.design:
        blocks[row["block_id"]][row["condition"]] = row["run_id"]
    contrasts, excluded = [], []
    fixed = dataset.config["fixed_conditions"]
    for block_id in sorted(blocks):
        runs = blocks[block_id]
        invalid = sorted(c for c, run in runs.items() if not truth(summaries[run]["valid"], "valid"))
        if invalid:
            excluded.append({"block_id": block_id, "invalid_conditions": invalid})
            continue
        best = max(fixed, key=lambda condition: (unit_u[runs[condition]], -fixed.index(condition)))
        contrasts.append({
            "block_id": block_id,
            "U_A": unit_u[runs["A"]],
            "U_Y": unit_u[runs["Y"]],
            "best_fixed_condition": best,
            "U_best_fixed": unit_u[runs[best]],
            "A_minus_Y": unit_u[runs["A"]] - unit_u[runs["Y"]],
            "A_minus_best_fixed": unit_u[runs["A"]] - unit_u[runs[best]],
        })
    if not contrasts:
        raise ValidationError("no complete valid block remains for descriptive contrasts")
    return {
        "schema_version": dataset.config["schema_version"],
        "inference": "not_run",
        "unit_U": unit_u,
        "block_contrasts": contrasts,
        "excluded_blocks": excluded,
        "descriptive_mean_A_minus_Y": sum((x["A_minus_Y"] for x in contrasts), ZERO) / len(contrasts),
        "descriptive_mean_A_minus_best_fixed": sum((x["A_minus_best_fixed"] for x in contrasts), ZERO) / len(contrasts),
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=root / "config.json")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "summarize"):
        commands.add_parser(command).add_argument("data_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        dataset = load_and_validate(args.data_directory, args.config)
        if args.command == "validate":
            payload = {
                "status": "valid", "runs": len(dataset.design),
                "blocks": len({row["block_id"] for row in dataset.design}),
                "conditions": dataset.config["conditions"], "inference": "not_run",
            }
        else:
            payload = compute_contrasts(dataset)
        print(json.dumps(json_safe(payload), indent=2, sort_keys=True))
        return 0
    except ValidationError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
