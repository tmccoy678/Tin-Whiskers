#!/usr/bin/env python3
"""Iterate MOOSE voltage solves with local current-driven widening."""

import csv
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
import pyvista as pv

W, H = 192, 128
EPOCHS = 24
ROOT = Path(__file__).resolve().parent
MOOSE = Path("/Users/tmccoy678/.local/share/tin-dendrite-moose-env/bin/moose-opt")
WORK = ROOT / "remodel"
WORK.mkdir(exist_ok=True)

source = np.asarray(Image.open(ROOT / "topologies/grown-transect-60.png").convert("RGB"))
metal = source[..., 0] > 128
metrics = []

for epoch in range(EPOCHS + 1):
    image_path = WORK / f"epoch-{epoch:03d}.png"
    Image.fromarray(np.where(metal[..., None], 255, 0).astype(np.uint8).repeat(3, axis=2)).save(image_path)
    base = WORK / f"epoch-{epoch:03d}"
    with (WORK / f"epoch-{epoch:03d}.log").open("w") as log:
        subprocess.run(
            [
                str(MOOSE),
                "-i", str(ROOT / "voltage_conduction.i"),
                f"Mesh/file={image_path}",
                f"Outputs/file_base={base}",
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )

    with (base.with_suffix(".csv")).open() as handle:
        row = list(csv.DictReader(handle))[-1]
    metrics.append(
        {
            "epoch": epoch,
            "metal_fraction": float(row["metal_fraction"]),
            "terminal_flux": float(row["terminal_flux"]),
            "joule_integral": float(row["joule_integral"]),
            "peak_current_density": float(row["peak_current_density"]),
            "peak_joule_density": float(row["peak_joule_density"]),
        }
    )
    if epoch == EPOCHS:
        break

    reader = pv.get_reader(str(base.with_suffix(".e")))
    reader.set_active_time_value(reader.time_values[-1])
    mesh = reader.read()[0][0]
    centers = mesh.cell_centers().points
    current = np.asarray(mesh["current_density"])
    ymax = mesh.bounds[3]
    cols = np.clip((centers[:, 0] * W).astype(int), 0, W - 1)
    rows = np.clip(H - 1 - (centers[:, 1] / ymax * H).astype(int), 0, H - 1)
    current_grid = np.zeros((H, W), dtype=float)
    np.maximum.at(current_grid, (rows, cols), current)

    used = current_grid[metal]
    positive = used[used > 0]
    if positive.size == 0:
        continue
    target = np.quantile(positive, 0.80)
    normalized = np.clip(current_grid / max(target, 1e-12), 0, 2)

    neighbor_signal = np.zeros_like(normalized)
    neighbor_signal[1:, :] = np.maximum(neighbor_signal[1:, :], normalized[:-1, :])
    neighbor_signal[:-1, :] = np.maximum(neighbor_signal[:-1, :], normalized[1:, :])
    neighbor_signal[:, 1:] = np.maximum(neighbor_signal[:, 1:], normalized[:, :-1])
    neighbor_signal[:, :-1] = np.maximum(neighbor_signal[:, :-1], normalized[:, 1:])
    candidates = (~metal) & (neighbor_signal > 0)
    rng = np.random.default_rng(319 + epoch)
    grow = candidates & (rng.random((H, W)) < 0.12 * np.clip(neighbor_signal, 0, 1))
    metal |= grow

with (WORK / "metrics.tsv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=metrics[0].keys(), delimiter="\t")
    writer.writeheader()
    writer.writerows(metrics)

print(WORK / "metrics.tsv")
