#!/usr/bin/env python3
"""Translate a space CBRAM screening draw into SI ranges and solver gates."""

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
    "um": ("m", 1.0e-6),
    "nm": ("m", 1.0e-9),
    "kg m^-3": ("kg m^-3", 1.0),
    "kg": ("kg", 1.0),
    "S m^-1": ("S m^-1", 1.0),
    "V": ("V", 1.0),
    "A": ("A", 1.0),
    "S": ("S", 1.0),
    "ratio": ("1", 1.0),
    "fraction": ("1", 1.0),
    "s": ("s", 1.0),
    "Pa": ("Pa", 1.0),
    "K": ("K", 1.0),
    "count": ("1", 1.0),
    "K s^-1": ("K s^-1", 1.0),
    "event cell^-1 h^-1": ("event cell^-1 s^-1", 1.0 / 3600.0),
    "Gy(Si)": ("J kg^-1(Si)", 1.0),
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
        raise TranslationError(f"{path}: translated inputs require a finite selected value and range")
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


def _result(quantity: dict[str, Any], **extra: Any) -> dict[str, Any]:
    result = {
        "selected": quantity["selected"],
        "range": {"minimum": quantity["minimum"], "maximum": quantity["maximum"]},
        "unit": quantity["unit"],
        "formula": quantity["formula"],
    }
    result.update(extra)
    return result


def _derived(selected: float, minimum: float | None, maximum: float | None, unit: str, formula: str, **extra: Any) -> dict[str, Any]:
    result = {
        "selected": selected,
        "range": {"minimum": minimum, "maximum": maximum},
        "unit": unit,
        "formula": formula,
    }
    result.update(extra)
    return result


def _constant(value: float, unit: str, formula: str) -> dict[str, Any]:
    return {"selected": value, "minimum": value, "maximum": value, "unit": unit, "formula": formula}


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


def _difference(upper: dict[str, Any], lower: dict[str, Any], unit: str, formula: str) -> dict[str, Any]:
    return {
        "selected": upper["selected"] - lower["selected"],
        "minimum": upper["minimum"] - lower["maximum"],
        "maximum": upper["maximum"] - lower["minimum"],
        "unit": unit,
        "formula": formula,
    }


def _absolute(quantity: dict[str, Any], unit: str, formula: str) -> dict[str, Any]:
    candidates = (abs(quantity["minimum"]), abs(quantity["maximum"]))
    minimum = 0.0 if quantity["minimum"] <= 0.0 <= quantity["maximum"] else min(candidates)
    return {
        "selected": abs(quantity["selected"]),
        "minimum": minimum,
        "maximum": max(candidates),
        "unit": unit,
        "formula": formula,
    }


def _sqrt(quantity: dict[str, Any], unit: str, formula: str) -> dict[str, Any]:
    if quantity["minimum"] < 0.0:
        raise TranslationError(f"cannot take square root of negative range for {formula}")
    return {
        "selected": math.sqrt(quantity["selected"]),
        "minimum": math.sqrt(quantity["minimum"]),
        "maximum": math.sqrt(quantity["maximum"]),
        "unit": unit,
        "formula": formula,
    }


def translate(
    draw: dict[str, Any],
    deck: dict[str, Any],
    draw_hash: str,
    deck_hash: str,
    draw_label: str,
) -> dict[str, Any]:
    if draw.get("regime") != "space" or draw.get("candidate_id") != "space-cbram":
        raise TranslationError("draw must be a space CBRAM candidate")
    if draw.get("mode") != "screening" or draw.get("accepted") is not True:
        raise TranslationError("draw must be an accepted space screening draw")
    if deck.get("regime") != "space":
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
    mission_map = deck.get("mission_gate_map")
    if not isinstance(records, dict) or not isinstance(input_map, dict) or not isinstance(mission_map, dict):
        raise TranslationError("draw parameters or deck maps are malformed")

    translated: dict[str, dict[str, Any]] = {}
    for path, mapping in input_map.items():
        if path not in records:
            raise TranslationError(f"deck input {path} is absent from draw")
        si = _record_to_si(path, records[path])
        si["solver_targets"] = mapping["solver_targets"]
        si["admission"] = mapping["admission"]
        if "reason" in mapping:
            si["admission_reason"] = mapping["reason"]
        translated[path] = si

    mission_gates: dict[str, dict[str, Any]] = {}
    for path, mapping in mission_map.items():
        if path not in records:
            raise TranslationError(f"mission gate {path} is absent from draw")
        record = records[path]
        if record.get("status") != "required-unset" or record.get("selected_value") is not None:
            raise TranslationError(f"mission gate {path} must remain required-unset and null")
        mission_gates[path] = {
            "value": None,
            "unit": record.get("unit"),
            "status": record.get("status"),
            "disposition": record.get("disposition"),
            "solver_targets": mapping["solver_targets"],
            "hard_stop": record.get("hard_stop"),
            "provenance": record.get("provenance"),
        }

    if sorted(mission_gates) != sorted(draw.get("required_unset_blockers", [])):
        raise TranslationError("mission-gate map does not exactly preserve sampler blockers")

    def q(path: str) -> dict[str, Any]:
        return translated[path]

    width = q("numeric_parameters.geometry.cell_width")
    height = q("numeric_parameters.geometry.cell_height")
    silver_thickness = q("numeric_parameters.geometry.silver_electrode_thickness")
    electrolyte_thickness = q("numeric_parameters.geometry.solid_electrolyte_thickness")
    inert_thickness = q("numeric_parameters.geometry.inert_electrode_thickness")
    cap_thickness = q("numeric_parameters.geometry.passivation_thickness")
    area = _multiply(width, height, "m^2", "L_width L_height")
    lateral_scale = _sqrt(area, "m", "sqrt(L_width L_height)")
    silver_volume = _multiply(area, silver_thickness, "m^3", "L_width L_height t_Ag")
    electrolyte_volume = _multiply(area, electrolyte_thickness, "m^3", "L_width L_height t_electrolyte")
    inert_volume = _multiply(area, inert_thickness, "m^3", "L_width L_height t_inert")
    cap_volume = _multiply(area, cap_thickness, "m^3", "L_width L_height t_cap")

    silver_density = q("numeric_parameters.reservoir.bulk_silver_density")
    calculated_reservoir_mass = _multiply(silver_density, silver_volume, "kg", "rho_Ag L_width L_height t_Ag")
    manifest_reservoir_mass = q("numeric_parameters.reservoir.silver_reservoir_mass_per_cell")

    constants = deck["reference_quantities"]
    molar_mass_ag = _constant(constants["silver_molar_mass"]["value"], "kg mol^-1", "M_Ag")
    avogadro = _constant(constants["avogadro_constant"]["value"], "mol^-1", "N_A")
    reservoir_moles = _divide(calculated_reservoir_mass, molar_mass_ag, "mol", "m_Ag / M_Ag")
    reservoir_atoms = _multiply(reservoir_moles, avogadro, "atom", "m_Ag N_A / M_Ag")

    conductance = q("numeric_parameters.electrical_admission.nominal_on_conductance")
    on_resistance = _inverse(conductance, "ohm", "1 / G_on")
    read_voltage = q("numeric_parameters.electrical_drive.read_voltage")
    nominal_read_current = _multiply(read_voltage, conductance, "A", "V_read G_on")
    nominal_read_power = _multiply(read_voltage, nominal_read_current, "W", "V_read^2 G_on")

    set_limit = q("numeric_parameters.electrical_drive.set_sweep_limit")
    reset_magnitude = _absolute(q("numeric_parameters.electrical_drive.reset_sweep_limit"), "V", "abs(V_reset_limit)")
    nominal_set_field = _divide(set_limit, electrolyte_thickness, "V m^-1", "V_set_limit / t_electrolyte")
    nominal_reset_field = _divide(reset_magnitude, electrolyte_thickness, "V m^-1", "abs(V_reset_limit) / t_electrolyte")

    cold = q("numeric_parameters.vacuum_environment.screen_temperature_minimum")
    hot = q("numeric_parameters.vacuum_environment.screen_temperature_maximum")
    compare_temperature = q("numeric_parameters.vacuum_environment.comparison_temperature")
    temperature_span = _difference(hot, cold, "K", "T_hot - T_cold")
    cycles = q("numeric_parameters.vacuum_environment.thermal_cycle_count")
    two_cycles = _scale(cycles, 2.0, "1", "2 N_cycle")
    dwell = q("numeric_parameters.vacuum_environment.plateau_dwell")
    plateau_time = _multiply(two_cycles, dwell, "s", "2 N_cycle t_dwell")
    array_cells = _multiply(
        q("numeric_parameters.geometry.array_rows"),
        q("numeric_parameters.geometry.array_columns"),
        "cell",
        "N_row N_column",
    )

    h = constants["planck_constant"]["value"]
    c = constants["speed_of_light"]["value"]
    hc = _constant(h * c, "J m", "h c")
    fabrication_photon_energy = _divide(
        hc,
        q("numeric_parameters.optical_interface.fabrication_photodoping_wavelength"),
        "J photon^-1",
        "h c / lambda_fabrication",
    )
    operational_photon_energy = _divide(
        hc,
        q("numeric_parameters.optical_interface.operational_address_wavelength"),
        "J photon^-1",
        "h c / lambda_address",
    )

    dose_paths = [
        "numeric_parameters.radiation_materials_screen.cobalt60_dose_step_1",
        "numeric_parameters.radiation_materials_screen.cobalt60_dose_step_2",
        "numeric_parameters.radiation_materials_screen.cobalt60_dose_step_3",
        "numeric_parameters.radiation_materials_screen.cobalt60_dose_step_4",
    ]
    dose_targets = [
        {
            "selected": q(path)["selected"],
            "range": {"minimum": q(path)["minimum"], "maximum": q(path)["maximum"]},
            "unit": q(path)["unit"],
            "material_basis": "silicon",
            "openmc_role": "absorbed-dose tally target after a source and mass normalization exist",
            "not_a_source": True,
        }
        for path in dose_paths
    ]

    direct_derived = {
        "cell_active_area": _result(area),
        "silver_electrode_volume": _result(silver_volume),
        "solid_electrolyte_volume": _result(electrolyte_volume),
        "inert_electrode_volume": _result(inert_volume),
        "passivation_volume": _result(cap_volume),
        "silver_reservoir_mass_from_sampled_geometry": _result(
            calculated_reservoir_mass,
            interpretation="Bulk-density inventory estimate; not a filament mass or thin-film density measurement."
        ),
        "silver_reservoir_moles": _result(reservoir_moles),
        "silver_reservoir_atom_count": _result(reservoir_atoms),
        "terminal_on_resistance": _result(on_resistance),
        "nominal_read_current": _result(nominal_read_current),
        "nominal_read_power": _result(nominal_read_power),
        "nominal_set_field": _result(
            nominal_set_field,
            interpretation="Terminal-voltage-over-film-thickness descriptor, not local ionic field or electrochemical overpotential."
        ),
        "nominal_reset_field_magnitude": _result(
            nominal_reset_field,
            interpretation="Terminal-voltage-over-film-thickness descriptor, not local dissolution field."
        ),
        "temperature_screen_span": _result(temperature_span),
        "minimum_plateau_exposure_time": _result(
            plateau_time,
            interpretation="Counts two stabilized plateaus per cycle and excludes ramps."
        ),
        "array_cell_count": _result(array_cells),
        "fabrication_photon_energy": _result(
            fabrication_photon_energy,
            interpretation="Photon energy only; photodoping dose and Ag-profile response are blocked."
        ),
        "operational_address_photon_energy": _result(
            operational_photon_energy,
            interpretation="Photon energy at the external address interface, not direct filament actuation."
        ),
    }

    cell_aspect = _divide(width, height, "1", "L_width / L_height")
    electrolyte_lateral = _divide(electrolyte_thickness, lateral_scale, "1", "t_electrolyte / sqrt(A_cell)")
    silver_electrolyte = _divide(silver_thickness, electrolyte_thickness, "1", "t_Ag / t_electrolyte")
    cap_electrolyte = _divide(cap_thickness, electrolyte_thickness, "1", "t_cap / t_electrolyte")
    selected_read_set = read_voltage["selected"] / set_limit["selected"]
    reservoir_consistency = _divide(calculated_reservoir_mass, manifest_reservoir_mass, "1", "rho_Ag A_cell t_Ag / m_Ag_manifest")
    temperature_span_fraction = _divide(temperature_span, compare_temperature, "1", "(T_hot - T_cold) / T_compare")
    standard_pressure = _constant(constants["standard_atmosphere"]["value"], "Pa", "p_standard")
    pressure_ratio = _divide(q("numeric_parameters.vacuum_environment.vacuum_pressure_maximum"), standard_pressure, "1", "p_vacuum_max / p_standard")
    dose_span = _divide(q(dose_paths[-1]), q(dose_paths[0]), "1", "D_screen_max / D_screen_min")

    e_times_voltage = _scale(set_limit, constants["elementary_charge"]["value"], "J", "e V_set_limit")
    kbt = _scale(compare_temperature, constants["boltzmann_constant"]["value"], "J", "k_B T_compare")
    set_thermal = _divide(e_times_voltage, kbt, "1", "e V_set_limit / (k_B T_compare)")

    high_compliance = q("numeric_parameters.electrical_drive.compliance_high")
    selected_read_compliance = nominal_read_current["selected"] / high_compliance["selected"]
    drift = q("numeric_parameters.radiation_materials_screen.maximum_programming_efficacy_fractional_drift")

    dimensionless = {
        "cell_lateral_aspect": _result(cell_aspect),
        "electrolyte_to_lateral_scale": _result(electrolyte_lateral),
        "silver_to_electrolyte_thickness": _result(silver_electrolyte),
        "passivation_to_electrolyte_thickness": _result(cap_electrolyte),
        "read_to_set_voltage": _derived(
            selected_read_set,
            None,
            None,
            "1",
            "V_read / V_set_limit",
            range_blocker="The set-voltage allowable range includes zero, so a finite ratio interval cannot be propagated without inventing a positive lower bound."
        ),
        "set_voltage_to_thermal_potential": _result(
            set_thermal,
            interpretation="Uses one elementary charge as a scale; it is not a local Ag-ion overpotential."
        ),
        "reservoir_mass_consistency": _result(reservoir_consistency),
        "nominal_read_current_to_high_compliance": _derived(
            selected_read_compliance,
            None,
            None,
            "1",
            "V_read G_on / I_compliance_high",
            range_blocker="The compliance allowable range includes zero, so no finite ratio interval exists without inventing a positive lower bound."
        ),
        "temperature_screen_span_fraction": _result(temperature_span_fraction),
        "vacuum_to_standard_atmosphere": _result(pressure_ratio),
        "radiation_screen_dose_span": _result(dose_span),
        "programming_drift_tolerance": _derived(
            drift["selected"], drift["minimum"], drift["maximum"], "1", "delta_G_program_max / G_program_reference"
        ),
    }

    filament_observable = {
        "terminal_on_conductance": {
            "selected": conductance["selected"],
            "range": {"minimum": conductance["minimum"], "maximum": conductance["maximum"]},
            "unit": "S",
        },
        "terminal_on_resistance": direct_derived["terminal_on_resistance"],
        "bulk_silver_conductivity_reference": {
            "value": q("numeric_parameters.reservoir.bulk_silver_conductivity_reference")["selected"],
            "unit": "S m^-1",
            "admission": "reference-only",
        },
        "filament_conductivity": {
            "value": None,
            "unit": "S m^-1",
            "status": "blocked",
            "required_measurements": ["filament length", "filament cross-sectional area", "terminal and contact resistance separation"],
            "reason": "Do not substitute bulk silver conductivity for the reversible filament observable."
        }
    }

    buckets: dict[str, list[str]] = {
        "moose_conduction": [],
        "moose_thermal": [],
        "moose_mechanics": [],
        "openmc_geometry_material": [],
        "openmc_tally_targets": [],
        "reference_or_metadata": [],
        "mission_gated": sorted(mission_gates),
    }
    for path, record in translated.items():
        targets = record["solver_targets"]
        if "moose-conduction" in targets:
            buckets["moose_conduction"].append(path)
        if "moose-thermal" in targets:
            buckets["moose_thermal"].append(path)
        if "moose-mechanics" in targets:
            buckets["moose_mechanics"].append(path)
        if any(target.startswith("openmc-geometry") or target.startswith("openmc-material") for target in targets):
            buckets["openmc_geometry_material"].append(path)
        if "openmc-tally-target" in targets:
            buckets["openmc_tally_targets"].append(path)
        if record["admission"] in {"reference-only", "metadata-only"}:
            buckets["reference_or_metadata"].append(path)
    for name in buckets:
        buckets[name] = sorted(buckets[name])

    blockers = deck.get("constitutive_blockers")
    if not isinstance(blockers, list) or not blockers:
        raise TranslationError("parameter deck must declare constitutive blockers")
    buckets["blocked_constitutive"] = sorted(item["blocker_id"] for item in blockers)

    return {
        "translator_version": TRANSLATOR_VERSION,
        "candidate_id": "space-cbram-si-translation",
        "seed": draw.get("seed"),
        "source_draw": draw_label,
        "source_draw_sha256": draw_hash,
        "source_manifest": source_manifest,
        "source_manifest_sha256": source_hash,
        "parameter_deck": str(DEFAULT_DECK.relative_to(REPO)),
        "parameter_deck_sha256": deck_hash,
        "selected_enumerated_options": draw.get("selected_options"),
        "translated_inputs_si": translated,
        "derived_si": direct_derived,
        "dimensionless_groups": dimensionless,
        "reversible_filament_observable": filament_observable,
        "openmc_screening_targets": {
            "absorbed_dose_targets": dose_targets,
            "normalization_status": "blocked until a particle source, material densities, scoring volume, and mass normalization exist",
            "coupling_direction": "OpenMC heating or dose tally to MOOSE volumetric source; MOOSE temperature and density feedback to OpenMC only after both models are independently calibrated"
        },
        "mission_gates": mission_gates,
        "solver_admission": buckets,
        "constitutive_blockers": blockers,
        "claim_boundary": "This translation supplies SI ranges, conductance observables, screening tally targets, and coupling gates only. It is not a filament constitutive model, mission environment, radiation qualification, or new physical claim."
    }


def calculate(draw_path: Path = DEFAULT_DRAW, deck_path: Path = DEFAULT_DECK) -> dict[str, Any]:
    draw, draw_hash = _load(draw_path)
    deck, deck_hash = _load(deck_path)
    try:
        draw_label = str(draw_path.resolve().relative_to(REPO))
    except ValueError:
        draw_label = str(draw_path.resolve())
    return translate(draw, deck, draw_hash, deck_hash, draw_label)


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
