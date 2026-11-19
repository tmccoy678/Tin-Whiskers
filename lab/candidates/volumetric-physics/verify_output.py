#!/usr/bin/env pvpython
"""Verify the saved volume through ParaView's real VTK reader."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from paraview import servermanager  # type: ignore
from paraview.simple import OpenDataFile, UpdatePipeline  # type: ignore
from vtkmodules.util.numpy_support import vtk_to_numpy


HERE = Path(__file__).resolve().parent
summary = json.loads((HERE / "output/summary.json").read_text())
reader = OpenDataFile(str(HERE / "output/final-volume.vtk"))
UpdatePipeline(proxy=reader)
info = reader.GetDataInformation()
assert info.GetNumberOfPoints() == 192 * 128 * 9
assert info.GetBounds()[5] > info.GetBounds()[4]

point_info = info.GetPointDataInformation()
present = {
    point_info.GetArrayInformation(i).GetName()
    for i in range(point_info.GetNumberOfArrays())
}
required = {
    "occupancy",
    "conductivity",
    "voltage",
    "current_magnitude",
    "joule_density",
    "growth_epoch",
    "current",
    "growth_direction",
}
assert required <= present, sorted(present)

data = servermanager.Fetch(reader)
occupancy = vtk_to_numpy(data.GetPointData().GetArray("occupancy")).reshape(
    (9, 128, 192)
)
growth_epoch = vtk_to_numpy(data.GetPointData().GetArray("growth_epoch"))
growth_direction = vtk_to_numpy(
    data.GetPointData().GetArray("growth_direction")
).reshape((9, 128, 192, 3))
current = vtk_to_numpy(data.GetPointData().GetArray("current"))
joule = vtk_to_numpy(data.GetPointData().GetArray("joule_density"))

occupied = int(np.count_nonzero(occupancy))
occupied_by_z = [int(np.count_nonzero(occupancy[z])) for z in range(9)]
out_of_plane = int(np.count_nonzero(growth_direction[..., 2]))
assert occupied == summary["final_occupied_voxels"] == 7019
assert sum(value > 0 for value in occupied_by_z) >= 3
assert out_of_plane == summary["out_of_plane_growth_choices"] == 214
assert set(np.unique(growth_epoch[growth_epoch >= 0]).tolist()) == {0, 1, 2, 3}
assert float(np.linalg.norm(current, axis=1).max()) > 0.0
assert float(joule.max()) > 0.0
assert summary["source_sink_relative_error"] < 2.0e-3
assert summary["source_joule_relative_error"] < 2.0e-3

print(
    "PASS ParaView volume: 192x128x9, "
    f"occupied_by_z={occupied_by_z}, occupied={occupied}, "
    f"out_of_plane_growth_vectors={out_of_plane}, current/Joule nonzero"
)
