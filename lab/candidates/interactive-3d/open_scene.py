#!/usr/bin/env pvpython
"""Open the exact adaptive state-120 lattice as an interactive ParaView scene."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

from paraview.simple import (  # type: ignore
    Box,
    AssignViewToLayout,
    CellCenters,
    Clip,
    ColorBy,
    CreateLayout,
    CreateView,
    ExtractSurface,
    GetActiveViewOrCreate,
    GetAnimationScene,
    GetColorTransferFunction,
    GetLayout,
    GetOpacityTransferFunction,
    GetScalarBar,
    Glyph,
    Hide,
    OpenDataFile,
    RenameSource,
    Render,
    RenameLayout,
    SaveScreenshot,
    SetActiveSource,
    SetActiveView,
    Show,
    Sphere,
    Text,
    Threshold,
    UpdatePipeline,
)


script_name = globals().get("__file__")
root_from_launcher = os.environ.get("TIN_VIZ_ROOT")
if script_name is not None:
    HERE = Path(script_name).resolve().parent
elif root_from_launcher is not None:
    HERE = Path(root_from_launcher).resolve()
else:
    raise RuntimeError("cannot locate scene bundle; launch with launch-local.sh")
DATA = HERE / "data"
MANIFEST_PATH = HERE / "provenance.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_verify_manifest() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text())
    for record in manifest["files"]:
        path = HERE / record["bundle_path"]
        actual = sha256(path)
        if actual != record["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch for {path.name}: {actual}")
    return manifest


def final_metrics() -> dict[str, str]:
    with (DATA / "metrics.tsv").open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    row = rows[-1]
    if int(row["epoch"]) != 120:
        raise RuntimeError("metrics.tsv does not end at state 120")
    return row


def add_overlay(view, name: str, text: str, position, size: int, color, bold=False, shadow=True):
    source = Text(registrationName=name)
    source.Text = text
    display = Show(source, view, "TextSourceRepresentation")
    display.WindowLocation = "Any Location"
    display.Position = position
    display.FontFamily = "Arial"
    display.FontSize = size
    display.Color = color
    display.Bold = int(bold)
    display.Shadow = int(shadow)
    display.Justification = "Left"
    display.VerticalJustification = "Bottom"
    return source, display


def cube_glyph(input_proxy, name: str, dx: float, dy: float, dz: float):
    centers = CellCenters(registrationName=f"_{name} cell centers", Input=input_proxy)
    centers.VertexCells = 1
    glyph = Glyph(registrationName=name, Input=centers, GlyphType="Box")
    glyph.OrientationArray = ["POINTS", "No orientation array"]
    glyph.ScaleArray = ["POINTS", "No scale array"]
    glyph.ScaleFactor = 1.0
    glyph.GlyphMode = "All Points"
    glyph.GlyphType.XLength = dx
    glyph.GlyphType.YLength = dy
    glyph.GlyphType.ZLength = dz
    return centers, glyph


manifest = load_and_verify_manifest()
dataset = manifest["dataset"]
metrics = final_metrics()
actions = json.loads((DATA / "actions.json").read_text())
last_action = actions[-1]
if len(actions) != 120 or last_action["observation_sha256"] != "135491a0288829a74c8fc387c1b0f34d795ffd3f9bba40b355899d12e1dabb54":
    raise RuntimeError("controller action record is not the admitted state-120 sequence")

reader = OpenDataFile(str(DATA / "moose-0120.e"))
RenameSource("00 EXACT EXODUS — adaptive seed 319 state 120", reader)
if not reader.TimestepValues:
    raise RuntimeError("Exodus file has no recorded time values")
final_time = reader.TimestepValues[-1]
UpdatePipeline(time=final_time, proxy=reader)

bounds = reader.GetDataInformation().GetBounds()
xmin, xmax, ymin, ymax, _, _ = bounds
nx = int(dataset["grid_width_cells"])
ny = int(dataset["grid_height_cells"])
dx = (xmax - xmin) / nx
dy = (ymax - ymin) / ny
dz = 2.4 * min(dx, dy)

occupied = Threshold(registrationName="_occupied metal == 1", Input=reader)
occupied.Scalars = ["CELLS", "metal"]
occupied.LowerThreshold = 0.5
occupied.UpperThreshold = 1.5
occupied.ThresholdMethod = "Between"

occupied_centers, occupied_cubes = cube_glyph(
    occupied,
    "01 OCCUPIED CELLS — FULL (toggle eye)",
    dx,
    dy,
    dz,
)

clip = Clip(registrationName="02 CLIP VIEW — ACTIVE; select and drag plane", Input=occupied_cubes)
clip.ClipType = "Plane"
clip.ClipType.Origin = [xmax - 0.12 * (xmax - xmin), 0.5 * (ymin + ymax), 0.0]
clip.ClipType.Normal = [-1.0, 0.0, 0.0]
clip.Invert = 0
clip.Crinkleclip = 0

all_centers, all_cubes = cube_glyph(
    reader,
    "03 CURRENT FIELD — ALL CELLS (toggle eye)",
    dx,
    dy,
    0.36 * dz,
)

voltage_surface = ExtractSurface(
    registrationName="04 VOLTAGE FIELD — CONTINUOUS FEM DIAGNOSTIC (toggle eye)",
    Input=reader,
)

source_rail = Box(registrationName="05 SOURCE BC x=0 value=1 (marker)")
source_rail.Center = [xmin - 0.25 * dx, 0.5 * (ymin + ymax), 0.0]
source_rail.XLength = 0.5 * dx
source_rail.YLength = ymax - ymin
source_rail.ZLength = 1.45 * dz

sink_rail = Box(registrationName="06 SINK BC x=1 value=0 (marker)")
sink_rail.Center = [xmax + 0.25 * dx, 0.5 * (ymin + ymax), 0.0]
sink_rail.XLength = 0.5 * dx
sink_rail.YLength = ymax - ymin
sink_rail.ZLength = 1.45 * dz

upper_y = ymin + (1.0 - 0.34) * (ymax - ymin)
lower_y = ymin + (1.0 - 0.66) * (ymax - ymin)
upper_marker = Sphere(registrationName="07 UPPER STIMULUS — 0.75 (action 119)")
upper_marker.Center = [xmin - 6.5 * dx, upper_y, 0.72 * dz]
upper_marker.Radius = 2.25 * dx
upper_marker.ThetaResolution = 32
upper_marker.PhiResolution = 20
lower_marker = Sphere(registrationName="08 LOWER STIMULUS — 0.25 (action 119)")
lower_marker.Center = [xmin - 6.5 * dx, lower_y, 0.72 * dz]
lower_marker.Radius = 2.25 * dx
lower_marker.ThetaResolution = 32
lower_marker.PhiResolution = 20

animation = GetAnimationScene()
animation.UpdateAnimationUsingDataTimeSteps()
animation.AnimationTime = final_time


def configure_view(view, light: bool):
    view.ViewSize = [1600, 1000]
    view.UseColorPaletteForBackground = 0
    view.BackgroundColorMode = "Gradient"
    if light:
        view.Background = [0.965, 0.975, 0.985]
        view.Background2 = [0.79, 0.86, 0.91]
    else:
        view.Background = [0.012, 0.016, 0.027]
        view.Background2 = [0.045, 0.065, 0.105]
    view.OrientationAxesVisibility = 1
    view.CenterOfRotation = [0.5 * (xmin + xmax), 0.5 * (ymin + ymax), 0.0]
    view.InteractionMode = "3D"
    view.ViewTime = final_time
    view.CameraPosition = [1.24, -0.86, 0.78]
    view.CameraFocalPoint = [0.50, 0.333, 0.0]
    view.CameraViewUp = [-0.30, 0.33, 0.90]
    view.CameraParallelProjection = 0
    view.CameraViewAngle = 30.0


light_view = GetActiveViewOrCreate("RenderView")
light_layout = GetLayout(light_view)
RenameLayout("LIGHT ANATOMY", light_layout)
configure_view(light_view, light=True)

heat_view = CreateView("RenderView")
heat_layout = CreateLayout(name="CURRENT HEAT")
AssignViewToLayout(view=heat_view, layout=heat_layout, hint=0)
configure_view(heat_view, light=False)

# LIGHT ANATOMY: categorical occupied-cell color; no field-dependent color map.
light_full_display = Show(occupied_cubes, light_view, "GeometryRepresentation")
light_full_display.Representation = "Surface With Edges"
light_full_display.DiffuseColor = [0.055, 0.25, 0.34]
light_full_display.AmbientColor = [0.055, 0.25, 0.34]
light_full_display.EdgeColor = [0.005, 0.015, 0.02]
light_full_display.LineWidth = 0.72

light_clip_display = Show(clip, light_view, "GeometryRepresentation")
light_clip_display.Representation = "Surface With Edges"
light_clip_display.DiffuseColor = [0.055, 0.25, 0.34]
light_clip_display.AmbientColor = [0.055, 0.25, 0.34]
light_clip_display.EdgeColor = [0.005, 0.015, 0.02]
light_clip_display.LineWidth = 0.72
Hide(clip, light_view)

light_all_display = Show(all_cubes, light_view, "GeometryRepresentation")
light_all_display.Representation = "Surface"
light_all_display.Opacity = 0.20
ColorBy(light_all_display, ("POINTS", "current_density"))
Hide(all_cubes, light_view)

light_voltage_display = Show(voltage_surface, light_view, "GeometryRepresentation")
light_voltage_display.Representation = "Surface With Edges"
light_voltage_display.Translation = [0.0, 0.0, -1.6 * dz]
light_voltage_display.Opacity = 0.90
light_voltage_display.EdgeColor = [0.10, 0.10, 0.12]
ColorBy(light_voltage_display, ("POINTS", "voltage"))
Hide(voltage_surface, light_view)

# CURRENT HEAT: exact current_density color, preserving the original dark view.
heat_full_display = Show(occupied_cubes, heat_view, "GeometryRepresentation")
heat_full_display.Representation = "Surface With Edges"
heat_full_display.EdgeColor = [0.035, 0.04, 0.05]
heat_full_display.LineWidth = 0.55
ColorBy(heat_full_display, ("POINTS", "current_density"))
Hide(occupied_cubes, heat_view)

heat_clip_display = Show(clip, heat_view, "GeometryRepresentation")
heat_clip_display.Representation = "Surface With Edges"
heat_clip_display.EdgeColor = [0.025, 0.03, 0.04]
heat_clip_display.LineWidth = 0.65
ColorBy(heat_clip_display, ("POINTS", "current_density"))

current_lut = GetColorTransferFunction("current_density")
current_max = float(metrics["peak_current_density"])
current_lut.RGBPoints = [
    0.0, 0.035, 0.075, 0.16,
    0.12 * current_max, 0.08, 0.54, 0.74,
    0.40 * current_max, 0.95, 0.78, 0.20,
    current_max, 0.95, 0.16, 0.06,
]
current_lut.ColorSpace = "RGB"
current_lut.ScalarRangeInitialized = 1.0
current_opacity = GetOpacityTransferFunction("current_density")
current_opacity.Points = [0.0, 0.18, 0.5, 0.0, current_max, 1.0, 0.5, 0.0]

heat_all_display = Show(all_cubes, heat_view, "GeometryRepresentation")
heat_all_display.Representation = "Surface"
heat_all_display.Opacity = 0.24
ColorBy(heat_all_display, ("POINTS", "current_density"))
heat_all_display.LookupTable = current_lut
Hide(all_cubes, heat_view)

heat_voltage_display = Show(voltage_surface, heat_view, "GeometryRepresentation")
heat_voltage_display.Representation = "Surface With Edges"
heat_voltage_display.Translation = [0.0, 0.0, -1.6 * dz]
heat_voltage_display.Opacity = 0.92
heat_voltage_display.EdgeColor = [0.08, 0.08, 0.09]
ColorBy(heat_voltage_display, ("POINTS", "voltage"))
Hide(voltage_surface, heat_view)


def show_markers(view, light: bool):
    source_display = Show(source_rail, view, "GeometryRepresentation")
    sink_display = Show(sink_rail, view, "GeometryRepresentation")
    upper_display = Show(upper_marker, view, "GeometryRepresentation")
    lower_display = Show(lower_marker, view, "GeometryRepresentation")
    if light:
        source_display.DiffuseColor = [0.00, 0.46, 0.38]
        source_display.AmbientColor = [0.00, 0.46, 0.38]
        sink_display.DiffuseColor = [0.72, 0.08, 0.14]
        sink_display.AmbientColor = [0.72, 0.08, 0.14]
        upper_display.DiffuseColor = [0.00, 0.56, 0.30]
        upper_display.AmbientColor = [0.00, 0.56, 0.30]
        lower_display.DiffuseColor = [0.58, 0.12, 0.76]
        lower_display.AmbientColor = [0.58, 0.12, 0.76]
    else:
        source_display.DiffuseColor = [0.12, 0.95, 0.82]
        source_display.AmbientColor = [0.12, 0.95, 0.82]
        sink_display.DiffuseColor = [0.95, 0.27, 0.35]
        sink_display.AmbientColor = [0.95, 0.27, 0.35]
        upper_display.DiffuseColor = [0.15, 0.95, 0.68]
        upper_display.AmbientColor = [0.15, 0.95, 0.68]
        lower_display.DiffuseColor = [0.84, 0.30, 0.98]
        lower_display.AmbientColor = [0.84, 0.30, 0.98]


show_markers(light_view, light=True)
show_markers(heat_view, light=False)

scalar_bar = GetScalarBar(current_lut, heat_view)
scalar_bar.Title = "current_density"
scalar_bar.ComponentTitle = "model field — SI calibration pending"
scalar_bar.TitleColor = [0.93, 0.95, 1.0]
scalar_bar.LabelColor = [0.88, 0.91, 0.97]
scalar_bar.WindowLocation = "Any Location"
scalar_bar.Position = [0.80, 0.13]
scalar_bar.Orientation = "Vertical"
scalar_bar.ScalarBarLength = 0.52
scalar_bar.ScalarBarThickness = 18
scalar_bar.TitleFontSize = 15
scalar_bar.LabelFontSize = 12
heat_clip_display.SetScalarBarVisibility(heat_view, True)
current_lut.RescaleTransferFunction(0.0, current_max)
current_opacity.RescaleTransferFunction(0.0, current_max)

hash_short = manifest["files"][0]["sha256"][:16]
status_text = (
    "ADAPTIVE CONTROLLER  •  seed 319  •  state 120\n"
    "Last applied input: action 119 UPPER-HEAVY\n"
    "upper 0.75  •  lower 0.25  •  exploit"
)

add_overlay(
    light_view,
    "LIGHT LABEL — evidence boundary",
    "EXTRUDED 2D EVIDENCE — NOT 3D PHYSICS",
    [0.30, 0.955],
    20,
    [0.55, 0.30, 0.00],
    bold=True,
    shadow=False,
)
add_overlay(
    light_view,
    "LIGHT LABEL — run status",
    status_text,
    [0.018, 0.865],
    17,
    [0.03, 0.10, 0.15],
    bold=True,
    shadow=False,
)
add_overlay(
    light_view,
    "LIGHT LABEL — anatomy and provenance",
    "LIGHT ANATOMY  •  categorical occupied-cell color independent of current\n"
    "Exact 192 × 128 occupancy  •  SOURCE x=0 value 1  →  SINK x=1 value 0\n"
    f"Exodus SHA-256 {hash_short}…  •  full hashes in provenance.json",
    [0.018, 0.018],
    13,
    [0.05, 0.12, 0.17],
    shadow=False,
)

add_overlay(
    heat_view,
    "HEAT LABEL — evidence boundary",
    "EXTRUDED 2D EVIDENCE — NOT 3D PHYSICS",
    [0.30, 0.955],
    20,
    [1.0, 0.80, 0.22],
    bold=True,
)
add_overlay(
    heat_view,
    "HEAT LABEL — run status",
    status_text,
    [0.018, 0.865],
    17,
    [0.94, 0.97, 1.0],
    bold=True,
)
add_overlay(
    heat_view,
    "HEAT LABEL — field and provenance",
    "CURRENT HEAT  •  color = exact cell current_density\n"
    "SOURCE x=0 value 1  →  SINK x=1 value 0  •  model units; SI calibration pending\n"
    f"Exodus SHA-256 {hash_short}…  •  full hashes in provenance.json",
    [0.018, 0.018],
    13,
    [0.78, 0.84, 0.92],
)

Render(heat_view)
SetActiveView(light_view)
SetActiveSource(occupied_cubes)
Render(light_view)

if "--screenshot" in sys.argv:
    index = sys.argv.index("--screenshot")
    target = Path(sys.argv[index + 1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    SaveScreenshot(str(target), light_view, ImageResolution=[1600, 1000], TransparentBackground=0)
    print(target)
if "--heat-screenshot" in sys.argv:
    index = sys.argv.index("--heat-screenshot")
    target = Path(sys.argv[index + 1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    SaveScreenshot(str(target), heat_view, ImageResolution=[1600, 1000], TransparentBackground=0)
    print(target)
if "--screenshot" not in sys.argv and "--heat-screenshot" not in sys.argv:
    print(
        "Interactive scene ready on LIGHT ANATOMY; switch to the CURRENT HEAT "
        "layout for exact field coloring and its legend."
    )
