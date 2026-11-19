#!/usr/bin/env python3
"""Private reciprocal-yoke pilot for the isolated Rust controller candidate."""

import csv
import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
import pyvista as pv

W, H = 192, 128
EPOCHS = int(os.environ.get("PILOT_EPOCHS", "12"))
REVERSAL_EPOCH = int(os.environ.get("PILOT_REVERSAL_EPOCH", "-1"))
ROOT = Path("/Users/tmccoy678/Blu-Workbench/tin-whiskers-dendrites-ai-si")
MODEL = ROOT / "simulation/voltage-routing/voltage_conduction.i"
SOURCE = ROOT / "simulation/voltage-routing/topologies/grown-transect-60.png"
MOOSE = Path("/Users/tmccoy678/.local/share/tin-dendrite-moose-env/bin/moose-opt")
POLICY = ROOT / "lab/candidates/adaptive-controller/target/debug/policy_server"
suffix = f"-reversal-{REVERSAL_EPOCH}" if REVERSAL_EPOCH >= 0 else ""
WORK = ROOT / f"simulation/work/live_moose/adaptive-reciprocal-pilot-{EPOCHS}{suffix}"
WORK.mkdir(parents=True, exist_ok=True)

UNIT_CURRENT = "<SI:delivered-current-pending-calibration>"
UNIT_CURRENT_DENSITY = "<SI:current-density-pending-calibration>"
UNIT_POWER_DENSITY = "<SI:power-density-pending-calibration>"
UNIT_STRESS = "<SI:stress-pending-calibration>"
UNIT_TEMPERATURE = "<SI:temperature-pending-calibration>"
UNIT_MATERIAL = "<SI:material-pending-calibration>"
UNIT_ENERGY = "<SI:energy-pending-calibration>"
UNIT_VOLTAGE = "<SI:voltage-pending-calibration>"

env = os.environ.copy()
env["PATH"] = f"{MOOSE.parent}:{env.get('PATH', '')}"
env["FI_PROVIDER"] = "tcp"
yy, xx = np.mgrid[0:H, 0:W]
width = 0.060 * H
decay = np.exp(-xx / (0.65 * W))
UPPER = decay * np.exp(-0.5 * ((yy - 0.34 * H) / width) ** 2)
LOWER = decay * np.exp(-0.5 * ((yy - 0.66 * H) / width) ** 2)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def weighted_mean(values, weights):
    total = float(weights.sum())
    return float(np.sum(values * weights) / total) if total > 0 else 0.0


def weighted_p95(values, weights):
    order = np.argsort(values, axis=None)
    flat_values = values.ravel()[order]
    flat_weights = weights.ravel()[order]
    cumulative = np.cumsum(flat_weights)
    if cumulative.size == 0 or cumulative[-1] <= 0:
        return 0.0
    index = int(np.searchsorted(cumulative, 0.95 * cumulative[-1], side="left"))
    return float(flat_values[min(index, flat_values.size - 1)])


def interface_mask(metal):
    adjacent_empty = np.zeros_like(metal, dtype=bool)
    adjacent_empty[1:, :] |= ~metal[:-1, :]
    adjacent_empty[:-1, :] |= ~metal[1:, :]
    adjacent_empty[:, 1:] |= ~metal[:, :-1]
    adjacent_empty[:, :-1] |= ~metal[:, 1:]
    return metal & adjacent_empty


def fixed_fractions(epoch):
    phase = np.sin(2 * np.pi * epoch / 12.0)
    return 0.5 + 0.5 * phase, 0.5 - 0.5 * phase


def policy_config(run_id, seed):
    return {
        "run_id": run_id,
        "seed": seed,
        "exploration_probability": 0.10,
        "ridge_lambda": 1.0,
        "confidence_multiplier": 2.0,
        "initial_objective_uncertainty": [0.05, 20.0, 5000.0, 0.0, 0.01, 1.0, 1.0],
        "feature_scales": {
            "delivery": 0.005,
            "current_per_delivery": 300.0,
            "heat_per_delivery_squared": 100000.0,
            "mean_current_density": 0.02,
            "p95_current_density": 0.02,
            "mean_joule_density": 0.01,
            "interface_contrast": 0.10,
        },
        "delivery_tolerance": 0.0005,
        "delivery_epsilon": 1.0e-12,
        "source_voltage": 1.0,
        "electrical_duty": 1.0,
        "polarity": 1,
        "safety": {
            "max_current_per_delivery": 400.0,
            "max_heat_per_delivery_squared": 200000.0,
            "max_mechanical_stress": None,
            "max_material_used": 1.0,
            "require_mechanical_stress": False,
        },
        "budget": {
            "max_optical_energy": float(EPOCHS),
            "max_electrical_energy": float(EPOCHS),
            "optical_cost_per_action": 1.0,
            "electrical_cost_per_action": 1.0,
        },
    }


def solve_field(arm_dir, epoch, metal):
    image_path = arm_dir / f"topology-{epoch:04d}.png"
    image = np.where(metal[..., None], 255, 0).astype(np.uint8).repeat(3, axis=2)
    Image.fromarray(image).save(image_path)
    base = arm_dir / f"moose-{epoch:04d}"
    with (arm_dir / f"moose-{epoch:04d}.log").open("w") as log:
        subprocess.run(
            [
                str(MOOSE),
                "-i", str(MODEL),
                f"Mesh/file={image_path}",
                f"Outputs/file_base={base}",
            ],
            cwd=MODEL.parent,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
            env=env,
        )
    with base.with_suffix(".csv").open() as handle:
        row = list(csv.DictReader(handle))[-1]
    reader = pv.get_reader(str(base.with_suffix(".e")))
    reader.set_active_time_value(reader.time_values[-1])
    mesh = reader.read()[0][0]
    centers = mesh.cell_centers().points
    ymax = mesh.bounds[3]
    cols = np.clip((centers[:, 0] * W).astype(int), 0, W - 1)
    rows = np.clip(H - 1 - (centers[:, 1] / ymax * H).astype(int), 0, H - 1)
    current = np.zeros((H, W), dtype=float)
    joule = np.zeros((H, W), dtype=float)
    np.maximum.at(current, (rows, cols), np.asarray(mesh["current_density"]))
    np.maximum.at(joule, (rows, cols), np.asarray(mesh["joule_density"]))
    metrics = {
        "metal_fraction": float(row["metal_fraction"]),
        "terminal_flux": float(row["terminal_flux"]),
        "joule_integral": float(row["joule_integral"]),
        "peak_current_density": float(row["peak_current_density"]),
        "peak_joule_density": float(row["peak_joule_density"]),
    }
    return image_path, base.with_suffix(".e"), metrics, current, joule


def footprint_observation(weights, current, joule, metal):
    interface = interface_mask(metal).astype(float)
    mean_current = weighted_mean(current, weights)
    mean_joule = weighted_mean(joule, weights)
    return {
        "mean_current_density": mean_current,
        "p95_current_density": max(mean_current, weighted_p95(current, weights)),
        "mean_joule_density": mean_joule,
        "p95_joule_density": max(mean_joule, weighted_p95(joule, weights)),
        "conductive_fraction": weighted_mean(metal.astype(float), weights),
        "interface_fraction": weighted_mean(interface, weights),
        "mean_available_reservoir": None,
        "mean_temperature": None,
        "p95_temperature": None,
        "mean_mechanical_stress": None,
        "p95_mechanical_stress": None,
    }


def observation(run_id, epoch, previous_hash, image_path, exodus_path, metrics, current, joule, metal):
    return {
        "schema": "adaptive-observation/v1",
        "run_id": run_id,
        "epoch": epoch,
        "previous_observation_sha256": previous_hash,
        "topology_sha256": sha256(image_path),
        "moose_sha256": sha256(exodus_path),
        "units": {
            "delivered_current": UNIT_CURRENT,
            "current_density": UNIT_CURRENT_DENSITY,
            "joule_density": UNIT_POWER_DENSITY,
            "mechanical_stress": UNIT_STRESS,
            "temperature": UNIT_TEMPERATURE,
            "material": UNIT_MATERIAL,
            "optical_energy": UNIT_ENERGY,
            "electrical_energy": UNIT_ENERGY,
            "voltage": UNIT_VOLTAGE,
        },
        "channels": {
            "material_reservoir": False,
            "temperature": False,
            "mechanical_stress": False,
        },
        "footprints": [
            footprint_observation(UPPER, current, joule, metal),
            footprint_observation(LOWER, current, joule, metal),
        ],
        "global": {
            "terminal_flux": metrics["terminal_flux"],
            "metal_fraction": metrics["metal_fraction"],
            "joule_integral": metrics["joule_integral"],
            "peak_current_density": metrics["peak_current_density"],
            "peak_joule_density": metrics["peak_joule_density"],
            "peak_mechanical_stress": None,
            "material_used": metrics["metal_fraction"],
            "cumulative_optical_energy": float(epoch),
            "cumulative_electrical_energy": float(epoch),
        },
    }


def apply_growth(metal, current, upper_fraction, lower_fraction, seed, epoch):
    carried = current[metal]
    active = carried[carried > 0]
    if active.size == 0:
        return metal.copy()
    response_scale = np.quantile(active, 0.80)
    relative_current = np.clip(current / max(response_scale, 1.0e-12), 0, 2)
    neighbor = np.zeros_like(relative_current)
    neighbor[1:, :] = np.maximum(neighbor[1:, :], relative_current[:-1, :])
    neighbor[:-1, :] = np.maximum(neighbor[:-1, :], relative_current[1:, :])
    neighbor[:, 1:] = np.maximum(neighbor[:, 1:], relative_current[:, :-1])
    neighbor[:, :-1] = np.maximum(neighbor[:, :-1], relative_current[:, 1:])
    upper_efficacy = 0.15 if REVERSAL_EPOCH >= 0 and epoch >= REVERSAL_EPOCH else 1.0
    probe = np.clip(
        upper_fraction * upper_efficacy * UPPER + lower_fraction * LOWER,
        0,
        1,
    )
    candidates = (~metal) & (neighbor > 0)
    probability = np.clip(0.07 * np.clip(neighbor, 0, 1) * (1 + 1.8 * probe), 0, 0.30)
    rng = np.random.default_rng(seed + epoch)
    return metal | (candidates & (rng.random((H, W)) < probability))


def run_arm(name, seed, mode, schedule=None):
    arm_dir = WORK / name
    arm_dir.mkdir(parents=True, exist_ok=True)
    metal = np.asarray(Image.open(SOURCE).convert("RGB"))[..., 0] > 128
    policy = None
    previous_hash = None
    actions = []
    audits = []
    metrics_rows = []
    if mode == "adaptive":
        policy = subprocess.Popen(
            [str(POLICY)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=(arm_dir / "policy.stderr.log").open("w"),
            text=True,
            bufsize=1,
        )
        policy.stdin.write(json.dumps(policy_config(name, seed), separators=(",", ":")) + "\n")
        policy.stdin.flush()

    for epoch in range(EPOCHS + 1):
        image_path, exodus_path, metrics, current, joule = solve_field(arm_dir, epoch, metal)
        metrics_rows.append({"epoch": epoch, **metrics})
        print(f"arm={name} epoch={epoch:02d}/{EPOCHS:02d} flux={metrics['terminal_flux']:.6f}", flush=True)
        if epoch == EPOCHS:
            break
        if mode == "adaptive":
            obs = observation(name, epoch, previous_hash, image_path, exodus_path, metrics, current, joule, metal)
            policy.stdin.write(json.dumps(obs, separators=(",", ":")) + "\n")
            policy.stdin.flush()
            line = policy.stdout.readline()
            if not line:
                raise RuntimeError(f"policy server ended for {name}")
            audit = json.loads(line)
            if audit.get("fail_reason") is not None:
                raise RuntimeError(f"policy failed closed for {name}: {audit['fail_reason']}")
            previous_hash = audit["observation_sha256"]
            action = audit["action"]
            upper_fraction = float(action["upper_fraction"])
            lower_fraction = float(action["lower_fraction"])
            audits.append(audit)
        elif mode == "fixed":
            upper_fraction, lower_fraction = fixed_fractions(epoch)
            action = {"id": "fixed-sinusoid", "upper_fraction": upper_fraction, "lower_fraction": lower_fraction}
        elif mode == "yoked":
            action = schedule[epoch]
            upper_fraction = float(action["upper_fraction"])
            lower_fraction = float(action["lower_fraction"])
        else:
            raise ValueError(mode)
        actions.append(action)
        metal = apply_growth(metal, current, upper_fraction, lower_fraction, seed, epoch)

    if policy is not None:
        policy.stdin.close()
        if policy.wait(timeout=10) != 0:
            raise RuntimeError(f"policy server exit {policy.returncode} for {name}")
    with (arm_dir / "actions.json").open("w") as handle:
        json.dump(actions, handle, indent=2, sort_keys=True)
    if audits:
        with (arm_dir / "audit.jsonl").open("w") as handle:
            for audit in audits:
                handle.write(json.dumps(audit, sort_keys=True, separators=(",", ":")) + "\n")
    with (arm_dir / "metrics.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=metrics_rows[0].keys(), delimiter="\t")
        writer.writeheader()
        writer.writerows(metrics_rows)
    return actions, metrics_rows


def summarize(name, rows):
    first, last = rows[0], rows[-1]
    first_concentration = first["peak_current_density"] / first["terminal_flux"]
    last_concentration = last["peak_current_density"] / last["terminal_flux"]
    return {
        "arm": name,
        "terminal_flux_ratio": last["terminal_flux"] / first["terminal_flux"],
        "material_ratio": last["metal_fraction"] / first["metal_fraction"],
        "peak_current_per_delivery_reduction_pct": 100 * (1 - last_concentration / first_concentration),
        "final_terminal_flux": last["terminal_flux"],
        "final_metal_fraction": last["metal_fraction"],
    }


adaptive_a_actions, adaptive_a = run_arm("adaptive-seed-319", 319, "adaptive")
adaptive_b_actions, adaptive_b = run_arm("adaptive-seed-571", 571, "adaptive")
_, fixed_a = run_arm("fixed-seed-319", 319, "fixed")
_, fixed_b = run_arm("fixed-seed-571", 571, "fixed")
_, yoked_a = run_arm("yoked-seed-319-from-571", 319, "yoked", adaptive_b_actions)
_, yoked_b = run_arm("yoked-seed-571-from-319", 571, "yoked", adaptive_a_actions)

summaries = [
    summarize("adaptive-seed-319", adaptive_a),
    summarize("adaptive-seed-571", adaptive_b),
    summarize("fixed-seed-319", fixed_a),
    summarize("fixed-seed-571", fixed_b),
    summarize("yoked-seed-319-from-571", yoked_a),
    summarize("yoked-seed-571-from-319", yoked_b),
]
with (WORK / "pilot-summary.json").open("w") as handle:
    json.dump(
        {"inference": "not_run", "reversal_epoch": REVERSAL_EPOCH, "summaries": summaries},
        handle,
        indent=2,
        sort_keys=True,
    )
with (WORK / "pilot-summary.tsv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=summaries[0].keys(), delimiter="\t")
    writer.writeheader()
    writer.writerows(summaries)
print(WORK / "pilot-summary.tsv")
