#!/usr/bin/env pvpython
"""Smallest evidence/geometry check for the interactive scene."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from paraview import servermanager  # type: ignore
from paraview.simple import CellCenters, OpenDataFile, Threshold, UpdatePipeline  # type: ignore
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkIOImage import vtkPNGReader


HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / "provenance.json").read_text())

for record in manifest["files"]:
    path = HERE / record["bundle_path"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual == record["sha256"], f"hash mismatch: {path.name}"

reader = OpenDataFile(str(HERE / "data/moose-0120.e"))
assert reader.TimestepValues == [0.0, 1.0], reader.TimestepValues
UpdatePipeline(time=reader.TimestepValues[-1], proxy=reader)
info = reader.GetDataInformation()
assert info.GetNumberOfCells() == 24576, info.GetNumberOfCells()
required = {"metal", "current_density", "joule_density", "conductivity"}
cell_info = info.GetCellDataInformation()
present = {cell_info.GetArrayInformation(i).GetName() for i in range(cell_info.GetNumberOfArrays())}
assert required <= present, sorted(present)
point_info = info.GetPointDataInformation()
point_present = {point_info.GetArrayInformation(i).GetName() for i in range(point_info.GetNumberOfArrays())}
assert "voltage" in point_present, sorted(point_present)
assert cell_info.GetArrayInformation("current_density").GetComponentRange(0)[1] > 0.0

fetched = servermanager.Fetch(reader)
iterator = fetched.NewIterator()
iterator.InitTraversal()
occupied_from_exodus = 0
while not iterator.IsDoneWithTraversal():
    block = iterator.GetCurrentDataObject()
    if block is not None:
        array = block.GetCellData().GetArray("metal")
        if array is not None:
            occupied_from_exodus += int(np.count_nonzero(vtk_to_numpy(array) > 0.5))
    iterator.GoToNextItem()

png = vtkPNGReader()
png.SetFileName(str(HERE / "data/topology-0120.png"))
png.Update()
image = png.GetOutput()
assert image.GetDimensions() == (192, 128, 1), image.GetDimensions()
pixels = vtk_to_numpy(image.GetPointData().GetScalars())
occupied_from_png = int(np.count_nonzero(pixels[:, 0] > 128))

threshold = Threshold(Input=reader)
threshold.Scalars = ["CELLS", "metal"]
threshold.LowerThreshold = 0.5
threshold.UpperThreshold = 1.5
threshold.ThresholdMethod = "Between"
UpdatePipeline(time=reader.TimestepValues[-1], proxy=threshold)
occupied_from_threshold = threshold.GetDataInformation().GetNumberOfCells()
centers = CellCenters(Input=threshold)
centers.VertexCells = 1
UpdatePipeline(time=reader.TimestepValues[-1], proxy=centers)
occupied_centers = centers.GetDataInformation().GetNumberOfPoints()

expected = manifest["dataset"]["occupied_cells"]
assert occupied_from_exodus == expected
assert occupied_from_png == expected
assert occupied_from_threshold == expected
assert occupied_centers == expected

print(
    "OK: ParaView read 24,576 exact cells; "
    f"PNG = Exodus = threshold = {expected} occupied cells; fields are nonzero."
)
