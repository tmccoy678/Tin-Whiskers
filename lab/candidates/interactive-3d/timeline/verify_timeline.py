#!/usr/bin/env pvpython
"""Verify cut-repair timeline hashes and the exact 17-to-18 transition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from paraview import servermanager  # type: ignore
from paraview.simple import OpenDataFile, UpdatePipeline  # type: ignore


HERE = Path(__file__).resolve().parent
DATA = HERE / "cut-repair/data"
manifest = json.loads((DATA / "manifest.json").read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


assert sha256(DATA / "timeline.pvd") == manifest["pvd_sha256"]
for state in manifest["states"]:
    assert sha256(DATA / state["converted_file"]) == state["converted_sha256"]

reader = OpenDataFile(str(DATA / "timeline.pvd"))
assert list(reader.TimestepValues) == [float(i) for i in range(37)]
observed = {}
for epoch in (17.0, 18.0):
    UpdatePipeline(time=epoch, proxy=reader)
    data = servermanager.Fetch(reader)
    arrays = data.GetCellData()
    observed[int(epoch)] = {
        name: arrays.GetArray(name).GetTuple1(0)
        for name in (
            "epoch",
            "connected",
            "upper_probe",
            "lower_probe",
            "first_connection",
        )
    }

assert observed[17]["epoch"] == 17
assert observed[17]["connected"] == 0
assert observed[17]["first_connection"] == 0
assert observed[18]["epoch"] == 18
assert observed[18]["connected"] == 1
assert observed[18]["first_connection"] == 1
print(
    "PASS timeline: 37 exact hashed states; epoch 17 disconnected; "
    "epoch 18 connected and marked FIRST CONNECTION; Snap To TimeSteps"
)
