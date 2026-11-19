#!/usr/bin/env pvpython
"""Convert exact per-state Exodus/PNG evidence into a discrete ParaView PVD timeline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from paraview import servermanager  # type: ignore
from paraview.simple import (  # type: ignore
    Calculator,
    Delete,
    MergeBlocks,
    OpenDataFile,
    SaveData,
    UpdatePipeline,
)
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkIOImage import vtkPNGReader


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_metadata(path: Path):
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    return {int(row["epoch"]): row for row in rows}


def png_occupied(path: Path) -> int:
    reader = vtkPNGReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    pixels = vtk_to_numpy(image.GetPointData().GetScalars())
    return int(np.count_nonzero(pixels[:, 0] > 128))


def add_constant(input_proxy, name: str, value: float, proxies):
    calculator = Calculator(Input=input_proxy)
    calculator.AttributeType = "Cell Data"
    calculator.ResultArrayName = name
    calculator.Function = repr(float(value))
    proxies.append(calculator)
    return calculator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--epochs", required=True, type=int)
    parser.add_argument("--exodus-template", default="epoch-{epoch:03d}.e")
    parser.add_argument("--topology-template", default="epoch-{epoch:03d}.png")
    parser.add_argument("--title", required=True)
    parser.add_argument("--first-connection", type=int, default=-1)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata = read_metadata(args.metadata)
    if set(metadata) != set(range(args.epochs + 1)):
        raise RuntimeError("metadata epochs do not exactly match requested timeline")

    states = []
    global_current_max = 0.0
    global_joule_max = 0.0
    for epoch in range(args.epochs + 1):
        row = metadata[epoch]
        exodus = args.source_dir / args.exodus_template.format(epoch=epoch)
        topology = args.source_dir / args.topology_template.format(epoch=epoch)
        if not exodus.is_file() or not topology.is_file():
            raise FileNotFoundError(f"missing state {epoch}: {exodus} or {topology}")

        proxies = []
        reader = OpenDataFile(str(exodus))
        proxies.append(reader)
        final_time = reader.TimestepValues[-1]
        UpdatePipeline(time=final_time, proxy=reader)
        merged = MergeBlocks(Input=reader)
        proxies.append(merged)
        pipeline = merged
        connected = float(row.get("connected", -1) or -1)
        upper = float(row.get("upper_probe", 0) or 0)
        lower = float(row.get("lower_probe", 0) or 0)
        values = {
            "epoch": epoch,
            "connected": connected,
            "upper_probe": upper,
            "lower_probe": lower,
            "first_connection": 1 if epoch == args.first_connection else 0,
        }
        for name, value in values.items():
            pipeline = add_constant(pipeline, name, value, proxies)
        UpdatePipeline(time=final_time, proxy=pipeline)

        fetched = servermanager.Fetch(pipeline)
        metal = vtk_to_numpy(fetched.GetCellData().GetArray("metal"))
        exodus_occupied = int(np.count_nonzero(metal > 0.5))
        image_occupied = png_occupied(topology)
        if exodus_occupied != image_occupied:
            raise RuntimeError(
                f"state {epoch} occupancy mismatch: Exodus={exodus_occupied} PNG={image_occupied}"
            )
        current = vtk_to_numpy(fetched.GetCellData().GetArray("current_density"))
        joule = vtk_to_numpy(fetched.GetCellData().GetArray("joule_density"))
        global_current_max = max(global_current_max, float(current.max()))
        global_joule_max = max(global_joule_max, float(joule.max()))

        output_name = f"state-{epoch:03d}.vtu"
        output_path = args.output_dir / output_name
        SaveData(
            str(output_path),
            proxy=pipeline,
            ChooseArraysToWrite=1,
            PointDataArrays=["voltage"],
            CellDataArrays=[
                "metal",
                "current_density",
                "joule_density",
                "epoch",
                "connected",
                "upper_probe",
                "lower_probe",
                "first_connection",
            ],
        )
        states.append(
            {
                "epoch": epoch,
                "connected": int(connected),
                "upper_probe": upper,
                "lower_probe": lower,
                "occupied_cells": exodus_occupied,
                "source_exodus": str(exodus),
                "source_exodus_sha256": sha256(exodus),
                "source_topology": str(topology),
                "source_topology_sha256": sha256(topology),
                "converted_file": output_name,
                "converted_sha256": sha256(output_path),
            }
        )
        for proxy in reversed(proxies):
            Delete(proxy)
        print(
            f"state={epoch:03d}/{args.epochs:03d} occupied={exodus_occupied} "
            f"connected={int(connected)} upper={upper:.3f} lower={lower:.3f}",
            flush=True,
        )

    pvd = args.output_dir / "timeline.pvd"
    with pvd.open("w") as handle:
        handle.write('<?xml version="1.0"?>\n')
        handle.write(
            '<VTKFile type="Collection" version="0.1" byte_order="LittleEndian">\n'
        )
        handle.write("  <Collection>\n")
        for state in states:
            handle.write(
                f'    <DataSet timestep="{state["epoch"]}" group="" part="0" '
                f'file="{state["converted_file"]}"/>\n'
            )
        handle.write("  </Collection>\n</VTKFile>\n")

    manifest = {
        "schema": "recorded-paraview-timeline/v1",
        "title": args.title,
        "epochs": args.epochs,
        "state_count": args.epochs + 1,
        "play_mode": "Snap To TimeSteps",
        "interpolation": "none; one recorded state per timestep",
        "first_connection_epoch": (
            args.first_connection if args.first_connection >= 0 else None
        ),
        "metadata_path": str(args.metadata),
        "metadata_sha256": sha256(args.metadata),
        "pvd_sha256": sha256(pvd),
        "global_current_max": global_current_max,
        "global_joule_max": global_joule_max,
        "states": states,
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        f"PASS timeline states={len(states)} pvd={pvd} manifest={manifest_path} "
        f"current_max={global_current_max:.6g} joule_max={global_joule_max:.6g}"
    )


if __name__ == "__main__":
    main()
