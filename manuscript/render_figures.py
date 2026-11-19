#!/usr/bin/env python3
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/figures"
OUT.mkdir(parents=True, exist_ok=True)
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
label_font = ImageFont.truetype(FONT, 24)


def panel(source, size, label, *, background="white", nearest=False):
    image = Image.open(source).convert("RGB")
    method = Image.Resampling.NEAREST if nearest else Image.Resampling.LANCZOS
    fitted = ImageOps.contain(image, size, method=method)
    canvas = Image.new("RGB", (size[0], size[1] + 54), background)
    x = (size[0] - fitted.width) // 2
    y = 54 + (size[1] - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, size[0], 54), fill="#0b1420")
    draw.text((size[0] // 2, 27), label, font=label_font, fill="white", anchor="mm")
    return canvas


fig1_sources = [
    (
        ROOT / "figures/biological-human-H01-neuron-2024.jpg",
        "A  HUMAN H01 CORTEX",
        "black",
        False,
    ),
    (
        ROOT / "figures/biological-purkinje-cajal-1899.jpg",
        "B  PIGEON PURKINJE — CAJAL",
        "white",
        False,
    ),
    (
        ROOT / "lab/candidates/interactive-3d/data/topology-0120.png",
        "C  ADAPTIVE LATTICE — STATE 120",
        "black",
        True,
    ),
    (
        ROOT / "figures/simulated-3d-physics-light.png",
        "D  SIMULATED 3D — 7,019 VOXELS",
        "white",
        False,
    ),
]
fig1_panels = [panel(path, (480, 270), label, background=bg, nearest=nearest) for path, label, bg, nearest in fig1_sources]
figure1 = Image.new("RGB", (1920, 324), "white")
for index, image in enumerate(fig1_panels):
    figure1.paste(image, (index * 480, 0))
draw = ImageDraw.Draw(figure1)
for x in (480, 960, 1440):
    draw.line((x, 0, x, 324), fill="#72808e", width=3)
figure1.save(OUT / "figure1-branching-comparators.png")


work = ROOT / "simulation/work/live_moose"
fig2_sources = [
    (work / "current_fiber_remodel/epoch-000.png", "A  REMODEL 0"),
    (work / "current_fiber_remodel/epoch-036.png", "B  REMODEL 36"),
    (work / "current_fiber_cut_repair/epoch-017.png", "C  CUT 17 — DEVELOPING"),
    (work / "current_fiber_cut_repair/epoch-018.png", "D  CUT 18 — RECONNECTED"),
    (work / "current_fiber_cut_repair/epoch-036.png", "E  CUT 36 — STRENGTHENED"),
]
fig2_panels = [panel(path, (384, 256), label, background="black", nearest=True) for path, label in fig2_sources]
figure2 = Image.new("RGB", (1920, 310), "black")
for index, image in enumerate(fig2_panels):
    figure2.paste(image, (index * 384, 0))
draw = ImageDraw.Draw(figure2)
for x in (384, 768, 1152, 1536):
    draw.line((x, 0, x, 310), fill="#72808e", width=3)
figure2.save(OUT / "figure2-remodel-and-repair.png")

for path in sorted(OUT.glob("figure*.png")):
    print(path)
