#!/usr/bin/env python3
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[2]
before = Image.open(root / "figures/current-remodel-epoch-000.png").convert("RGB")
after = Image.open(root / "figures/current-remodel-epoch-024.png").convert("RGB")
before = before.resize((768, 512), Image.Resampling.NEAREST)
after = after.resize((768, 512), Image.Resampling.NEAREST)

canvas = Image.new("RGB", (1680, 760), "#05070b")
canvas.paste(before, (48, 110))
canvas.paste(after, (864, 110))
draw = ImageDraw.Draw(canvas)
font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
title = ImageFont.truetype(font_path, 38)
label = ImageFont.truetype(font_path, 27)
small = ImageFont.truetype(font_path, 21)
draw.text((840, 28), "CURRENT-DRIVEN REMODELING", font=title, fill="white", anchor="ma")
draw.text((432, 645), "EPOCH 0", font=label, fill="#c8d8e5", anchor="ma")
draw.text((1248, 645), "EPOCH 24", font=label, fill="#c8d8e5", anchor="ma")
draw.text((840, 700), "8.26× flux · 1.43× material · 72.01% lower peak stress per delivered current", font=small, fill="#9de7c1", anchor="ma")
canvas.save(root / "figures/current-driven-remodeling.png")
