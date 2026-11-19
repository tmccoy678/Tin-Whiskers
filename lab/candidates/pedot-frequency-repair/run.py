#!/usr/bin/env python3
"""PEDOT-frequency-informed current-driven repair screen.

The frequency translation is a screening law derived from Janzakova et al.
(2021): projected area scales approximately with waveform period across the
reported 10--950 Hz morphology transition.  It is held separate from the
canonical fixed-rule result.
"""

import csv
import os
import subprocess
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pyvista as pv

W, H = 192, 128
EPOCHS = int(os.environ.get("REMODEL_EPOCHS", "36"))
SEED = 319
FREQUENCY_HZ = float(os.environ.get("PEDOT_FREQUENCY_HZ", "80"))
REFERENCE_FREQUENCY_HZ = 80.0
if not 10.0 <= FREQUENCY_HZ <= 950.0:
    raise ValueError("PEDOT_FREQUENCY_HZ must be in the literature screen 10--950 Hz")
AREA_SCALE = REFERENCE_FREQUENCY_HZ / FREQUENCY_HZ
LINEARITY = np.clip(
    np.log(FREQUENCY_HZ / 10.0) / np.log(950.0 / 10.0), 0.0, 1.0
)
ROOT = Path("/Users/tmccoy678/Blu-Workbench/tin-whiskers-dendrites-ai-si")
MODEL = ROOT / "simulation/voltage-routing/voltage_conduction.i"
SOURCE = Path(os.environ.get(
    "REMODEL_SOURCE",
    ROOT / "simulation/voltage-routing/topologies/grown-transect-60.png",
))
RUN_NAME = os.environ.get("REMODEL_NAME", "current_fiber_remodel")
DISPLAY_TITLE = os.environ.get(
    "REMODEL_TITLE",
    f"CURRENT-DRIVEN CUT/REPAIR: PEDOT {FREQUENCY_HZ:g} Hz",
)
MOOSE = Path("/Users/tmccoy678/.local/share/tin-dendrite-moose-env/bin/moose-opt")
WORK = ROOT / "simulation/work/live_moose" / RUN_NAME
FRAMES = Path.home() / "Desktop/Tin Whisker Dendrite Work/Results" / f"{RUN_NAME}_frames"
LIVE = ROOT / "simulation/work/live_moose/live_view" / RUN_NAME
WORK.mkdir(parents=True, exist_ok=True)
FRAMES.mkdir(parents=True, exist_ok=True)
LIVE.mkdir(parents=True, exist_ok=True)

font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
title_font = ImageFont.truetype(font_path, 29)
state_font = ImageFont.truetype(font_path, 19)

source = np.asarray(Image.open(SOURCE).convert("RGB"))
metal = source[..., 0] > 128
metrics = []
yy, xx = np.mgrid[0:H, 0:W]


def connected_left_right(field):
    queue = deque((row, 0) for row in range(H) if field[row, 0])
    seen = set(queue)
    while queue:
        row, column = queue.popleft()
        if column == W - 1:
            return True
        for next_row, next_column in (
            (row - 1, column),
            (row + 1, column),
            (row, column - 1),
            (row, column + 1),
        ):
            if (
                0 <= next_row < H
                and 0 <= next_column < W
                and field[next_row, next_column]
                and (next_row, next_column) not in seen
            ):
                seen.add((next_row, next_column))
                queue.append((next_row, next_column))
    return False


def optical_probe(epoch):
    phase = np.sin(2 * np.pi * epoch / 12.0)
    upper = 0.5 + 0.5 * phase
    lower = 0.5 - 0.5 * phase
    width = 0.060 * H
    decay = np.exp(-xx / (0.65 * W))
    upper_field = upper * np.exp(-0.5 * ((yy - 0.34 * H) / width) ** 2)
    lower_field = lower * np.exp(-0.5 * ((yy - 0.66 * H) / width) ** 2)
    return np.clip(decay * (upper_field + lower_field), 0, 1), upper, lower


def save_display(epoch, upper, lower, connected):
    lattice = Image.fromarray(np.where(metal, 255, 0).astype(np.uint8), mode="L")
    lattice = lattice.resize((W * 6, H * 6), Image.Resampling.NEAREST).convert("RGB")
    canvas = Image.new("RGB", (1280, 860), "#05070b")
    canvas.paste(lattice, ((canvas.width - lattice.width) // 2, 54))
    draw = ImageDraw.Draw(canvas)
    draw.text((640, 17), DISPLAY_TITLE, font=title_font, fill="white", anchor="ma")
    draw.ellipse((36, 386, 56, 406), fill=(int(157 * upper), int(231 * upper), int(193 * upper)))
    draw.ellipse((36, 506, 56, 526), fill=(int(157 * lower), int(231 * lower), int(193 * lower)))
    status = "CONNECTED" if connected else "DEVELOPING CONNECTION"
    draw.text(
        (640, 846),
        f"{FREQUENCY_HZ:g} Hz  |  EPOCH {epoch:02d} / {EPOCHS:02d}  |  {status}",
        font=state_font,
        fill="#9de7c1",
        anchor="ms",
    )
    canvas.save(FRAMES / f"frame.{epoch:04d}.png")
    live_tmp = LIVE / "latest.tmp.png"
    canvas.save(live_tmp)
    os.replace(live_tmp, LIVE / "latest.png")


env = os.environ.copy()
env["PATH"] = f"{MOOSE.parent}:{env.get('PATH', '')}"
env["FI_PROVIDER"] = "tcp"

for epoch in range(EPOCHS + 1):
    probe, upper, lower = optical_probe(epoch)
    connected = connected_left_right(metal)
    image_path = WORK / f"epoch-{epoch:03d}.png"
    Image.fromarray(np.where(metal[..., None], 255, 0).astype(np.uint8).repeat(3, axis=2)).save(image_path)
    save_display(epoch, upper, lower, connected)

    base = WORK / f"epoch-{epoch:03d}"
    with (WORK / f"epoch-{epoch:03d}.log").open("w") as log:
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
    metrics.append(
        {
            "epoch": epoch,
            "frequency_hz": FREQUENCY_HZ,
            "period_area_scale": AREA_SCALE,
            "linearity": float(LINEARITY),
            "connected": int(connected),
            "upper_probe": upper,
            "lower_probe": lower,
            "metal_fraction": float(row["metal_fraction"]),
            "terminal_flux": float(row["terminal_flux"]),
            "joule_integral": float(row["joule_integral"]),
            "peak_current_density": float(row["peak_current_density"]),
            "peak_joule_density": float(row["peak_joule_density"]),
        }
    )
    print(
        f"epoch={epoch:02d}/{EPOCHS:02d} connected={int(connected)} flux={metrics[-1]['terminal_flux']:.6f} "
        f"peak_j={metrics[-1]['peak_current_density']:.6f} upper={upper:.3f} lower={lower:.3f}",
        flush=True,
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

    carried = current_grid[metal]
    active = carried[carried > 0]
    if active.size == 0:
        continue
    response_scale = np.quantile(active, 0.80)
    relative_current = np.clip(current_grid / max(response_scale, 1e-12), 0, 2)

    vertical_signal = np.zeros_like(relative_current)
    vertical_signal[1:, :] = np.maximum(vertical_signal[1:, :], relative_current[:-1, :])
    vertical_signal[:-1, :] = np.maximum(vertical_signal[:-1, :], relative_current[1:, :])
    horizontal_signal = np.zeros_like(relative_current)
    horizontal_signal[:, 1:] = np.maximum(horizontal_signal[:, 1:], relative_current[:, :-1])
    horizontal_signal[:, :-1] = np.maximum(horizontal_signal[:, :-1], relative_current[:, 1:])
    diffuse_signal = np.maximum(horizontal_signal, vertical_signal)
    oriented_signal = 0.90 * horizontal_signal + 0.10 * vertical_signal
    neighbor_signal = (1.0 - LINEARITY) * diffuse_signal + LINEARITY * oriented_signal
    candidates = (~metal) & (neighbor_signal > 0)
    probability = (
        0.07
        * AREA_SCALE
        * np.clip(neighbor_signal, 0, 1)
        * (1 + 1.8 * probe)
    )
    probability = np.clip(probability, 0, 0.30)
    rng = np.random.default_rng(SEED + epoch)
    metal |= candidates & (rng.random((H, W)) < probability)

with (WORK / "metrics.tsv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=metrics[0].keys(), delimiter="\t")
    writer.writeheader()
    writer.writerows(metrics)

print(f"complete metrics={WORK / 'metrics.tsv'} frames={FRAMES}")
