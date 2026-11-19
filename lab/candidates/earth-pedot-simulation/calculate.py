#!/usr/bin/env python3
"""Translate an Earth PEDOT sampler draw into SI ranges and MOOSE candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
REPO = BASE.parents[2]
DEFAULT_DRAW = BASE / "seed-319-draw.json"
DEFAULT_DECK = BASE / "parameter-deck.json"
TRANSLATOR_VERSION = "1.0.0"


UNIT_MAP = {
    "uL": ("m^3", 1.0e-9),
    "um": ("m", 1.0e-6),
    "nm": ("m", 1.0e-9),
    "ug": ("kg", 1.0e-9),
    "mol m^-3": ("mol m^-3", 1.0),
    "mol": ("mol", 1.0),
    "V": ("V", 1.0),
    "A": ("A", 1.0),
    "Hz": ("s^-1", 1.0),
    "s": ("s", 1.0),
    "K": ("K", 1.0),
    "Pa": ("Pa", 1.0),
    "W m^-2": ("W m^-2", 1.0),
    "S": ("S", 1.0),
    "S m^-1": ("S m^-1", 1.0),
    "fraction": ("1", 1.0),
    "ratio": ("1", 1.0),
    "count": ("1", 1.0),
}


class TranslationError(ValueError):
    pass


def _load(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TranslationError(f"cannot load {path}: {error}") from error
    if not isinstance(document, dict):
        raise TranslationError(f"{path} must contain a JSON object")
    return document, hashlib.sha256(raw).hexdigest()


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _record_to_si(path: str, record: dict[str, Any]) -> dict[str, Any]:
    unit = record.get("unit")
    if unit not in UNIT_MAP:
        raise TranslationError(f"{path}: unsupported unit {unit!r}")
    si_unit, factor = UNIT_MAP[unit]
    value = record.get("selected_value")
    allowed = record.get("allowable_range")
    if not _finite(value) or not isinstance(allowed, dict):
        raise TranslationError(f"{path}: translated inputs require a selected finite value and range")
    minimum = allowed.get("minimum")
    maximum = allowed.get("maximum")
    if not _finite(minimum) or not _finite(maximum):
        raise TranslationError(f"{path}: translated inputs require finite range bounds")
    return {
        "selected": value * factor,
        "minimum": minimum * factor,
        "maximum": maximum * factor,
        "unit": si_unit,
        "source_unit": unit,
        "status": record.get("status"),
        "disposition": record.get("disposition"),
    }


def _derived(selected: float, minimum: float | None, maximum: float | None, unit: str, formula: str, **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "selected": selected,
        "range": {"minimum": minimum, "maximum": maximum},
        "unit": unit,
        "formula": formula,
    }
    result.update(extra)
    return result


def _scale(quantity: dict[str, Any], factor: float, unit: str, formula: str) -> dict[str, Any]:
    endpoints = (quantity["minimum"] * factor, quantity["maximum"] * factor)
    return {
        "selected": quantity["selected"] * factor,
        "minimum": min(endpoints),
        "maximum": max(endpoints),
        "unit": unit,
        "formula": formula,
    }


def _multiply(left: dict[str, Any], right: dict[str, Any], unit: str, formula: str) -> dict[str, Any]:
    products = (
        left["minimum"] * right["minimum"],
        left["minimum"] * right["maximum"],
        left["maximum"] * right["minimum"],
        left["maximum"] * right["maximum"],
    )
    return {
        "selected": left["selected"] * right["selected"],
        "minimum": min(products),
        "maximum": max(products),
        "unit": unit,
        "formula": formula,
    }


def _divide(numerator: dict[str, Any], denominator: dict[str, Any], unit: str, formula: str) -> dict[str, Any]:
    if denominator["minimum"] <= 0.0 <= denominator["maximum"]:
        raise TranslationError(f"cannot propagate {formula}: denominator range crosses zero")
    ratios = (
        numerator["minimum"] / denominator["minimum"],
        numerator["minimum"] / denominator["maximum"],
        numerator["maximum"] / denominator["minimum"],
        numerator["maximum"] / denominator["maximum"],
    )
    return {
        "selected": numerator["selected"] / denominator["selected"],
        "minimum": min(ratios),
        "maximum": max(ratios),
        "unit": unit,
        "formula": formula,
    }


def _inverse(quantity: dict[str, Any], unit: str, formula: str) -> dict[str, Any]:
    if quantity["minimum"] <= 0.0:
        raise TranslationError(f"cannot invert nonpositive range for {formula}")
    return {
        "selected": 1.0 / quantity["selected"],
        "minimum": 1.0 / quantity["maximum"],
        "maximum": 1.0 / quantity["minimum"],
        "unit": unit,
        "formula": formula,
    }


def _one_minus(quantity: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected": 1.0 - quantity["selected"],
        "minimum": 1.0 - quantity["maximum"],
        "maximum": 1.0 - quantity["minimum"],
        "unit": "1",
        "formula": "1 - D",
    }


def _as_derived(quantity: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return _derived(
        quantity["selected"],
        quantity["minimum"],
        quantity["maximum"],
        quantity["unit"],
        quantity["formula"],
        **extra,
    )


def translate(draw: dict[str, Any], deck: dict[str, Any], draw_hash: str, deck_hash: str) -> dict[str, Any]:
    if draw.get("regime") != "earth" or draw.get("candidate_id") != "earth-pedot":
        raise TranslationError("draw must be an Earth PEDOT candidate")
    if draw.get("accepted") is not True:
        raise TranslationError("draw must be accepted by the bounded sampler")
    if deck.get("regime") != "earth":
        raise TranslationError("parameter deck regime mismatch")

    source_manifest = draw.get("source_manifest")
    if not isinstance(source_manifest, str):
        raise TranslationError("draw lacks source manifest path")
    source_path = REPO / source_manifest
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if source_hash != draw.get("source_manifest_sha256"):
        raise TranslationError("draw source-manifest hash no longer matches exact source bytes")

    records = draw.get("parameters")
    input_map = deck.get("input_map")
    if not isinstance(records, dict) or not isinstance(input_map, dict):
        raise TranslationError("draw parameters or deck input map is malformed")

    translated: dict[str, dict[str, Any]] = {}
    for path, mapping in input_map.items():
        if path not in records:
            raise TranslationError(f"deck input {path} is absent from draw")
        si = _record_to_si(path, records[path])
        si["moose_role"] = mapping["moose_role"]
        si["admission"] = mapping["admission"]
        if "reason" in mapping:
            si["admission_reason"] = mapping["reason"]
        translated[path] = si

    def q(path: str) -> dict[str, Any]:
        return translated[path]

    voltage_pp = q("numeric_parameters.growth_drive.growth_voltage_peak_to_peak")
    voltage_peak = _scale(voltage_pp, 0.5, "V", "Vpp / 2")
    frequency = q("numeric_parameters.growth_drive.growth_frequency")
    period = _inverse(frequency, "s", "1 / f")
    duty = q("numeric_parameters.growth_drive.growth_duty_fraction")
    positive_duration = _divide(duty, frequency, "s", "D / f")
    negative_duration = _divide(_one_minus(duty), frequency, "s", "(1 - D) / f")
    gap = q("numeric_parameters.geometry.electrode_gap")
    diameter = q("numeric_parameters.geometry.gold_wire_diameter")
    active_length = q("numeric_parameters.geometry.active_wire_length")
    nominal_gap_field = _divide(voltage_peak, gap, "V m^-1", "V_peak / L_gap")

    current_compliance = q("numeric_parameters.growth_drive.growth_current_compliance")
    timeout = q("numeric_parameters.growth_drive.growth_timeout")
    power_ceiling = _multiply(voltage_peak, current_compliance, "W", "V_peak I_compliance")
    electrical_energy_ceiling = _multiply(power_ceiling, timeout, "J", "V_peak I_compliance t_max")

    read_voltage = q("numeric_parameters.readout.read_voltage")
    conductance_floor = q("numeric_parameters.admission_metrics.minimum_bridge_conductance")
    threshold_read_current = _multiply(read_voltage, conductance_floor, "A", "V_read G_bridge_min")

    volume = q("numeric_parameters.chemistry.electrolyte_volume")
    edot_concentration = q("numeric_parameters.chemistry.edot_concentration")
    amount_calculated = _multiply(edot_concentration, volume, "mol", "c_EDOT V_drop")
    amount_manifest = q("numeric_parameters.chemistry.edot_reservoir_amount")

    wavelength = q("numeric_parameters.optical_interface.projection_wavelength")
    corridor_width = q("numeric_parameters.optical_interface.projected_corridor_width")
    irradiance = q("numeric_parameters.optical_interface.projected_irradiance")
    corridor_area = _multiply(corridor_width, gap, "m^2", "w_opt L_gap")
    incident_optical_power = _multiply(irradiance, corridor_area, "W", "I_opt w_opt L_gap")
    incident_optical_energy = _multiply(incident_optical_power, timeout, "J", "I_opt w_opt L_gap t_max")

    constants = deck.get("reference_quantities", {})
    h = constants["planck_constant"]["value"]
    c = constants["speed_of_light"]["value"]
    elementary_charge = constants["elementary_charge"]["value"]
    boltzmann = constants["boltzmann_constant"]["value"]
    threshold_voltage = constants["electropolymerization_threshold_nominal"]["value"]

    hc = {
        "selected": h * c,
        "minimum": h * c,
        "maximum": h * c,
        "unit": "J m",
        "formula": "h c",
    }
    photon_energy = _divide(hc, wavelength, "J photon^-1", "h c / lambda")
    photon_flux = _divide(irradiance, photon_energy, "photon m^-2 s^-1", "I_opt / E_photon")
    photon_fluence = _multiply(photon_flux, timeout, "photon m^-2", "I_opt t_max / E_photon")

    direct_derived = {
        "voltage_peak": _as_derived(voltage_peak),
        "waveform_period": _as_derived(period),
        "positive_phase_duration": _as_derived(positive_duration),
        "negative_phase_duration": _as_derived(negative_duration),
        "nominal_uniform_gap_field": _as_derived(
            nominal_gap_field,
            interpretation="Terminal-voltage geometry descriptor only; local overpotential is blocked by electrolyte and interface constitutive data."
        ),
        "electrical_power_ceiling": _as_derived(
            power_ceiling,
            interpretation="Compliance ceiling, not predicted dissipation."
        ),
        "electrical_energy_ceiling": _as_derived(
            electrical_energy_ceiling,
            interpretation="Conservative terminal-energy ceiling, not heat deposited in the dendrite."
        ),
        "threshold_read_current": _as_derived(threshold_read_current),
        "edot_amount_from_concentration_and_volume": _as_derived(amount_calculated),
        "projected_gap_corridor_area": _as_derived(
            corridor_area,
            interpretation="Rectangular incident footprint assumption across the electrode gap; absorption is not inferred."
        ),
        "incident_optical_power": _as_derived(
            incident_optical_power,
            interpretation="Incident power only."
        ),
        "incident_optical_energy_to_timeout": _as_derived(
            incident_optical_energy,
            interpretation="Incident energy only; absorbed and photochemical doses are blocked."
        ),
        "photon_energy": _as_derived(photon_energy),
        "incident_photon_flux": _as_derived(photon_flux),
        "incident_photon_fluence_to_timeout": _as_derived(photon_fluence),
    }

    gap_diameter = _divide(gap, diameter, "1", "L_gap / d_wire")
    active_gap = _divide(active_length, gap, "1", "L_active / L_gap")
    optical_gap = _divide(corridor_width, gap, "1", "w_opt / L_gap")
    threshold_reference = {
        "selected": threshold_voltage,
        "minimum": threshold_voltage,
        "maximum": threshold_voltage,
        "unit": "V",
        "formula": "published nominal threshold",
    }
    voltage_threshold = _divide(voltage_peak, threshold_reference, "1", "V_peak / V_threshold_nominal")

    e_voltage = _scale(voltage_peak, elementary_charge, "J", "e V_peak")
    kbt = _scale(q("numeric_parameters.environment.temperature"), boltzmann, "J", "k_B T")
    voltage_thermal = _divide(e_voltage, kbt, "1", "e V_peak / (k_B T)")
    selected_read_to_compliance = threshold_read_current["selected"] / current_compliance["selected"]
    reservoir_consistency = _divide(amount_calculated, amount_manifest, "1", "c_EDOT V_drop / n_EDOT_manifest")

    selected_energy_ratio = incident_optical_energy["selected"] / electrical_energy_ceiling["selected"]
    dimensionless = {
        "waveform_duty_fraction": _derived(duty["selected"], duty["minimum"], duty["maximum"], "1", "D"),
        "gap_to_wire_diameter": _as_derived(gap_diameter),
        "active_length_to_gap": _as_derived(active_gap),
        "optical_corridor_to_gap": _as_derived(optical_gap),
        "conditional_voltage_to_polymerization_threshold": _as_derived(
            voltage_threshold,
            range_basis="Numerator range divided by the published nominal threshold.",
            uncertainty_blocker="The threshold source does not report a calibrated interval; this group is conditional, not predictive."
        ),
        "voltage_to_thermal_potential": _as_derived(
            voltage_thermal,
            interpretation="Uses one elementary charge as a scale; it is not a local electrochemical overpotential."
        ),
        "threshold_read_current_to_growth_compliance": _derived(
            selected_read_to_compliance,
            None,
            None,
            "1",
            "V_read G_min / I_compliance",
            range_blocker="The current-compliance allowable range includes zero, so a finite ratio interval cannot be propagated without inventing a positive lower bound."
        ),
        "reservoir_amount_consistency": _as_derived(reservoir_consistency),
        "incident_optical_to_electrical_energy_ceiling": _derived(
            selected_energy_ratio,
            None,
            None,
            "1",
            "E_opt_incident / E_electrical_ceiling",
            range_blocker="The compliance and timeout allowable ranges include zero, so a finite ratio interval cannot be propagated without inventing a positive lower bound.",
            interpretation="Selected-setting bookkeeping ratio only; neither numerator absorption nor denominator heat deposition is known."
        ),
    }

    ready_paths = sorted(path for path, item in translated.items() if item["admission"] == "ready")
    conditional_paths = sorted(path for path, item in translated.items() if item["admission"] != "ready")
    blockers = deck.get("constitutive_blockers")
    if not isinstance(blockers, list) or not blockers:
        raise TranslationError("parameter deck must declare constitutive blockers")

    return {
        "translator_version": TRANSLATOR_VERSION,
        "candidate_id": "earth-pedot-si-translation",
        "seed": draw.get("seed"),
        "source_draw": str(DEFAULT_DRAW.relative_to(REPO)),
        "source_draw_sha256": draw_hash,
        "source_manifest": source_manifest,
        "source_manifest_sha256": source_hash,
        "parameter_deck": str(DEFAULT_DECK.relative_to(REPO)),
        "parameter_deck_sha256": deck_hash,
        "translated_inputs_si": translated,
        "derived_si": direct_derived,
        "dimensionless_groups": dimensionless,
        "moose_admission": {
            "can_enter_now": ready_paths,
            "conditional_screening_or_metadata": conditional_paths,
            "cannot_enter_without_constitutive_data": [item["blocker_id"] for item in blockers]
        },
        "constitutive_blockers": blockers,
        "claim_boundary": "This translation supplies SI ranges and algebraic descriptors only. It is not a kinetic model, wet-lab instruction, or physical validation."
    }


def calculate(draw_path: Path = DEFAULT_DRAW, deck_path: Path = DEFAULT_DECK) -> dict[str, Any]:
    draw, draw_hash = _load(draw_path)
    deck, deck_hash = _load(deck_path)
    return translate(draw, deck, draw_hash, deck_hash)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draw", type=Path, default=DEFAULT_DRAW)
    parser.add_argument("--deck", type=Path, default=DEFAULT_DECK)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = calculate(args.draw, args.deck)
    except (OSError, TranslationError) as error:
        parser.error(str(error))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
