#!/usr/bin/env python3
"""Deterministic bounded-serendipity sampler for material candidate manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path
from typing import Any


SAMPLER_VERSION = "1.0.0"
BASE = Path(__file__).resolve().parent
MANIFEST_BASE = BASE.parent / "material-manifests"
POLICY_PATH = BASE / "policy.json"


class SamplingError(ValueError):
    pass


def _load_json_bytes(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SamplingError(f"cannot load JSON from {path}: {error}") from error
    if not isinstance(document, dict):
        raise SamplingError(f"{path} must contain a JSON object")
    return document, hashlib.sha256(raw).hexdigest()


def _quantity_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    quantities: dict[str, dict[str, Any]] = {}
    groups = manifest.get("numeric_parameters")
    if not isinstance(groups, dict):
        raise SamplingError("manifest numeric_parameters must be an object")
    for group_name, group in groups.items():
        if not isinstance(group, dict):
            raise SamplingError(f"numeric_parameters.{group_name} must be an object")
        for name, quantity in group.items():
            path = f"numeric_parameters.{group_name}.{name}"
            if not isinstance(quantity, dict):
                raise SamplingError(f"{path} must be a quantity object")
            quantities[path] = quantity

    required_unset = manifest.get("required_unset_gates")
    if not isinstance(required_unset, dict):
        raise SamplingError("manifest required_unset_gates must be an object")
    for name, quantity in required_unset.items():
        path = f"required_unset_gates.{name}"
        if not isinstance(quantity, dict):
            raise SamplingError(f"{path} must be a quantity object")
        quantities[path] = quantity
    return quantities


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _normalized_float(value: float) -> float:
    return float(f"{value:.12g}")


def _sample_quantity(rng: random.Random, quantity: dict[str, Any], strategy: str, path: str) -> float:
    if quantity.get("status") != "proposed":
        raise SamplingError(
            f"{path} has status {quantity.get('status')!r}; only proposed ranges may be sampled"
        )
    allowed = quantity.get("allowable_range")
    if not isinstance(allowed, dict):
        raise SamplingError(f"{path} lacks an allowable range")
    minimum = allowed.get("minimum")
    maximum = allowed.get("maximum")
    if not _finite_number(minimum) or not _finite_number(maximum) or minimum > maximum:
        raise SamplingError(f"{path} has no finite ordered proposed range")
    if strategy == "uniform":
        return _normalized_float(rng.uniform(minimum, maximum))
    raise SamplingError(f"{path} uses unsupported sampling strategy {strategy!r}")


def _constraint_failure(options: dict[str, str], constraints: list[dict[str, Any]]) -> str | None:
    for constraint in constraints:
        condition = constraint.get("if", {})
        if not all(options.get(key) == value for key, value in condition.items()):
            continue
        required = constraint.get("requires", {})
        if any(options.get(key) != value for key, value in required.items()):
            return str(constraint.get("reason", "option requirement failed"))
        forbidden = constraint.get("forbids", {})
        if any(options.get(key) == value for key, value in forbidden.items()):
            return str(constraint.get("reason", "forbidden option combination"))
    return None


def _sample_options(
    rng: random.Random,
    policy: dict[str, Any],
    rejected: list[dict[str, Any]],
) -> dict[str, str]:
    admitted = policy.get("admitted_options")
    constraints = policy.get("constraints")
    if not isinstance(admitted, dict) or not isinstance(constraints, list):
        raise SamplingError("policy admitted_options and constraints are malformed")
    for _ in range(128):
        options: dict[str, str] = {}
        for name in sorted(admitted):
            values = admitted[name]
            if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
                raise SamplingError(f"option {name} must have a non-empty string enumeration")
            options[name] = rng.choice(values)
        reason = _constraint_failure(options, constraints)
        if reason is None:
            return options
        rejected.append({"candidate": options, "reason": reason})
    raise SamplingError("no admitted option combination found within bounded rejection attempts")


def _parameter_record(
    quantity: dict[str, Any],
    selected_value: Any,
    disposition: str,
) -> dict[str, Any]:
    return {
        "selected_value": selected_value,
        "source_point_value": quantity.get("value"),
        "unit": quantity.get("unit"),
        "status": quantity.get("status"),
        "disposition": disposition,
        "allowable_range": quantity.get("allowable_range"),
        "provenance": quantity.get("provenance"),
        "hard_stop": quantity.get("hard_stop"),
    }


def generate_draw(
    regime: str,
    mode: str,
    seed: int,
    policy_document: dict[str, Any] | None = None,
    manifest_document: dict[str, Any] | None = None,
    manifest_hash: str | None = None,
) -> dict[str, Any]:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise SamplingError("seed must be an explicit integer")

    if policy_document is None:
        policy_document, policy_hash = _load_json_bytes(POLICY_PATH)
    else:
        policy_hash = hashlib.sha256(
            json.dumps(policy_document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    regimes = policy_document.get("regimes")
    if not isinstance(regimes, dict) or regime not in regimes:
        raise SamplingError(f"unknown regime {regime!r}")
    policy = regimes[regime]
    admitted_modes = policy.get("admitted_modes")
    if mode not in admitted_modes:
        raise SamplingError(f"mode {mode!r} is not admitted for regime {regime!r}")

    manifest_name = policy.get("manifest")
    if not isinstance(manifest_name, str):
        raise SamplingError("policy manifest name is missing")
    manifest_path = MANIFEST_BASE / manifest_name
    if manifest_document is None:
        manifest_document, loaded_hash = _load_json_bytes(manifest_path)
        manifest_hash = loaded_hash
    elif manifest_hash is None:
        manifest_hash = hashlib.sha256(
            json.dumps(manifest_document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    if manifest_document.get("regime") != regime:
        raise SamplingError("source manifest regime does not match policy regime")
    if manifest_document.get("candidate_id") != policy.get("candidate_id"):
        raise SamplingError("source manifest candidate_id does not match policy candidate_id")
    contract = manifest_document.get("separation_contract", {})
    if contract.get("prohibits_cross_regime_parameter_import") is not True:
        raise SamplingError("source manifest does not enforce cross-regime separation")

    quantities = _quantity_map(manifest_document)
    sample_axes = policy.get("sample_axes")
    if not isinstance(sample_axes, list):
        raise SamplingError("policy sample_axes must be a list")
    axes: dict[str, str] = {}
    for axis in sample_axes:
        if not isinstance(axis, dict) or set(axis) != {"path", "strategy"}:
            raise SamplingError("each sample axis must contain exactly path and strategy")
        path = axis["path"]
        if path in axes:
            raise SamplingError(f"duplicate sample axis {path}")
        if path not in quantities:
            raise SamplingError(f"sample axis {path} is absent from source manifest")
        if quantities[path].get("status") != "proposed":
            raise SamplingError(
                f"sample axis {path} has status {quantities[path].get('status')!r}; established points stay fixed"
            )
        axes[path] = axis["strategy"]

    blockers = sorted(
        path
        for path, quantity in quantities.items()
        if quantity.get("status") == "required-unset" and quantity.get("value") is None
    )
    rejected: list[dict[str, Any]] = [dict(item) for item in policy.get("static_rejections", [])]
    promotion_blocked = mode == "promotion" and bool(blockers)
    if blockers:
        rejected.append(
            {
                "candidate": {"mode": "promotion", "regime": regime},
                "reason": "Promotion is excluded while required-unset source-manifest gates remain: "
                + ", ".join(blockers),
            }
        )

    rng = random.Random(seed)
    selected_options: dict[str, str] = {}
    parameter_records: dict[str, dict[str, Any]] = {}

    if not promotion_blocked:
        selected_options = _sample_options(rng, policy, rejected)

    for path in sorted(quantities):
        quantity = quantities[path]
        status = quantity.get("status")
        if promotion_blocked:
            disposition = "required-unset" if status == "required-unset" else "fixed-blocked-promotion"
            selected = quantity.get("value")
        elif path in axes:
            selected = _sample_quantity(rng, quantity, axes[path], path)
            disposition = "sampled-proposed"
        elif status == "established":
            selected = quantity.get("value")
            disposition = "fixed-established"
        elif status == "proposed":
            selected = quantity.get("value")
            disposition = "fixed-proposed-control"
        elif status == "required-unset":
            selected = None
            disposition = "required-unset"
        else:
            raise SamplingError(f"{path} has unknown status {status!r}")
        parameter_records[path] = _parameter_record(quantity, selected, disposition)

    promotion_eligible = not blockers and not promotion_blocked
    return {
        "sampler_version": SAMPLER_VERSION,
        "seed": seed,
        "regime": regime,
        "candidate_id": manifest_document.get("candidate_id"),
        "mode": mode,
        "accepted": not promotion_blocked,
        "promotion_eligible": promotion_eligible,
        "source_manifest": str(manifest_path.relative_to(BASE.parents[2])),
        "source_manifest_sha256": manifest_hash,
        "sampling_policy": str(POLICY_PATH.relative_to(BASE.parents[2])),
        "sampling_policy_sha256": policy_hash,
        "selected_options": selected_options,
        "parameters": parameter_records,
        "required_unset_blockers": blockers,
        "rejected_combinations": rejected,
        "interpretation_boundary": "This is a deterministic candidate draw only. It executes no wet-lab or hardware work and adds no physical claim."
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--regime", choices=("earth", "space"), required=True)
    parser.add_argument("--mode", choices=("exploratory", "screening", "promotion"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)

    try:
        draw = generate_draw(args.regime, args.mode, args.seed)
    except (OSError, SamplingError) as error:
        parser.error(str(error))

    indent = None if args.compact else 2
    payload = json.dumps(draw, indent=indent, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0 if draw["accepted"] else 2


if __name__ == "__main__":
    sys.exit(main())
