#!/usr/bin/env python3
"""Convert an exact non-interlaced 8-bit RGB/RGBA PNG into occupied x/y cells."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def paeth(a: int, b: int, c: int) -> int:
    estimate = a + b - c
    pa = abs(estimate - a)
    pb = abs(estimate - b)
    pc = abs(estimate - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path: Path):
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("not a PNG")
    position = len(PNG_SIGNATURE)
    compressed = bytearray()
    width = height = depth = color_type = interlace = None
    while position < len(data):
        length = struct.unpack(">I", data[position : position + 4])[0]
        kind = data[position + 4 : position + 8]
        payload = data[position + 8 : position + 8 + length]
        position += 12 + length
        if kind == b"IHDR":
            width, height, depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    if depth != 8 or color_type not in (2, 6) or interlace != 0:
        raise ValueError(
            f"expected non-interlaced 8-bit RGB/RGBA, got depth={depth} "
            f"color_type={color_type} interlace={interlace}"
        )
    channels = 3 if color_type == 2 else 4
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    expected = height * (stride + 1)
    if len(raw) != expected:
        raise ValueError(f"decoded {len(raw)} bytes, expected {expected}")
    rows = []
    prior = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        encoded = raw[offset + 1 : offset + 1 + stride]
        offset += stride + 1
        row = bytearray(stride)
        for i, value in enumerate(encoded):
            left = row[i - channels] if i >= channels else 0
            above = prior[i]
            upper_left = prior[i - channels] if i >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = above
            elif filter_type == 3:
                predictor = (left + above) // 2
            elif filter_type == 4:
                predictor = paeth(left, above, upper_left)
            else:
                raise ValueError(f"unsupported PNG filter {filter_type}")
            row[i] = (value + predictor) & 0xFF
        rows.append(row)
        prior = row
    return width, height, channels, rows, hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("cells", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    width, height, channels, rows, source_sha = read_png(args.source)
    cells = []
    for image_row, row in enumerate(rows):
        physical_y = height - 1 - image_row
        for x in range(width):
            if row[x * channels] > 128:
                cells.append((x, physical_y))
    args.cells.parent.mkdir(parents=True, exist_ok=True)
    with args.cells.open("w", newline="") as handle:
        handle.write(f"# source_sha256={source_sha}\n")
        handle.write(f"# width={width} height={height} y_mapping=height-1-image_row\n")
        handle.write("x\ty\n")
        for x, y in cells:
            handle.write(f"{x}\t{y}\n")
    cells_sha = hashlib.sha256(args.cells.read_bytes()).hexdigest()
    manifest = {
        "schema": "volumetric-seed/v1",
        "source_path": str(args.source),
        "source_sha256": source_sha,
        "width": width,
        "height": height,
        "occupied_cells": len(cells),
        "mapping": "Exact occupied PNG cells; x unchanged; physical y = height - 1 - image row; all cells enter at z=nz//2.",
        "cells_path": str(args.cells),
        "cells_sha256": cells_sha,
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        f"seed width={width} height={height} occupied={len(cells)} "
        f"source_sha256={source_sha} cells_sha256={cells_sha}"
    )


if __name__ == "__main__":
    main()
