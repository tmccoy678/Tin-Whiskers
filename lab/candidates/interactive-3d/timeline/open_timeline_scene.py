#!/usr/bin/env pvpython
"""Open a recorded-state ParaView timeline with no interpolated anatomy."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from paraview.simple import (  # type: ignore
    AssignViewToLayout,
    Box,
    CellCenters,
    ColorBy,
    CreateLayout,
    CreateView,
    GetActiveViewOrCreate,
    GetAnimationScene,
    GetColorTransferFunction,
    GetLayout,
    GetOpacityTransferFunction,
    GetScalarBar,
    Glyph,
    Hide,
    OpenDataFile,
    PythonAnnotation,
    Render,
    RenameLayout,
    RenameSource,
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
root_from_launcher = os.environ.get("TIMELINE_VIZ_ROOT")
if script_name is not None:
    HERE = Path(script_name).resolve().parent
elif root_from_launcher is not None:
    HERE = Path(root_from_launcher).resolve()
else:
    raise RuntimeError("cannot locate timeline bundle; use launch-cut-repair-local.sh")

DATA = HERE / "cut-repair/data"
MANIFEST = DATA / "manifest.json"
PVD = DATA / "timeline.pvd"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


manifest = json.loads(MANIFEST.read_text())
if sha256(PVD) != manifest["pvd_sha256"]:
    raise RuntimeError("timeline PVD hash mismatch")
for state in manifest["states"]:
    path = DATA / state["converted_file"]
    if sha256(path) != state["converted_sha256"]:
        raise RuntimeError(f"timeline state hash mismatch: {path.name}")


def add_overlay(view, name, text, position, size, color, bold=False, shadow=True):
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


def box_glyph(input_proxy, name, dx, dy, dz):
    glyph = Glyph(registrationName=name, Input=input_proxy, GlyphType="Box")
    glyph.OrientationArray = ["POINTS", "No orientation array"]
    glyph.ScaleArray = ["POINTS", "No scale array"]
    glyph.ScaleFactor = 1.0
    glyph.GlyphMode = "All Points"
    glyph.GlyphType.XLength = dx
    glyph.GlyphType.YLength = dy
    glyph.GlyphType.ZLength = dz
    return glyph


reader = OpenDataFile(str(PVD))
RenameSource("00 RECORDED STATES 0–36 — exact cut-repair evidence", reader)
animation = GetAnimationScene()
animation.UpdateAnimationUsingDataTimeSteps()
animation.PlayMode = "Snap To TimeSteps"
animation.AnimationTime = 17.0

UpdatePipeline(time=17.0, proxy=reader)
bounds = reader.GetDataInformation().GetBounds()
dx = (bounds[1] - bounds[0]) / 192.0
dy = (bounds[3] - bounds[2]) / 128.0
dz = 2.4 * min(dx, dy)

occupied = Threshold(registrationName="01 EXACT OCCUPANCY — metal >= 0.5", Input=reader)
occupied.Scalars = ["CELLS", "metal"]
occupied.LowerThreshold = 0.5
occupied.UpperThreshold = 1.5
occupied.ThresholdMethod = "Between"
centers = CellCenters(registrationName="_INTERNAL occupied cell centers", Input=occupied)
centers.VertexCells = 1
light_voxels = box_glyph(centers, "02 LIGHT ANATOMY — literal occupied cells", dx, dy, dz)
current_voxels = box_glyph(centers, "03 CURRENT HEAT — exact cell field", dx, dy, dz)
joule_voxels = box_glyph(centers, "04 JOULE HEAT — exact cell field", dx, dy, dz)

source = Box(registrationName="05 SOURCE BC — x=0 value=1")
source.Center = [bounds[0] - 0.25 * dx, 0.5 * (bounds[2] + bounds[3]), 0.0]
source.XLength = 0.5 * dx
source.YLength = bounds[3] - bounds[2]
source.ZLength = 1.45 * dz
sink = Box(registrationName="06 SINK BC — x=1 value=0")
sink.Center = [bounds[1] + 0.25 * dx, 0.5 * (bounds[2] + bounds[3]), 0.0]
sink.XLength = 0.5 * dx
sink.YLength = bounds[3] - bounds[2]
sink.ZLength = 1.45 * dz

upper_marker = Sphere(registrationName="07 UPPER STIMULUS — value in state label")
upper_marker.Center = [bounds[0] - 6.5 * dx, bounds[2] + 0.66 * (bounds[3] - bounds[2]), 0.72 * dz]
upper_marker.Radius = 2.25 * dx
lower_marker = Sphere(registrationName="08 LOWER STIMULUS — value in state label")
lower_marker.Center = [bounds[0] - 6.5 * dx, bounds[2] + 0.34 * (bounds[3] - bounds[2]), 0.72 * dz]
lower_marker.Radius = 2.25 * dx

state_annotation = PythonAnnotation(registrationName="09 LIVE STATE / CONNECTION / STIMULUS", Input=reader)
state_annotation.ArrayAssociation = "Cell Data"
state_annotation.Expression = (
    '"EPOCH %02d / 36\\n%s\\nSTIMULUS  upper %.3f  •  lower %.3f" % '
    '(inputs[0].CellData["epoch"][0], '
    '"FIRST CONNECTION — EPOCH 18" if inputs[0].CellData["first_connection"][0] > 0.5 '
    'else ("CONNECTED — first connection was epoch 18" if inputs[0].CellData["connected"][0] > 0.5 '
    'else "DEVELOPING CONNECTION"), '
    'inputs[0].CellData["upper_probe"][0], inputs[0].CellData["lower_probe"][0])'
)


def configure_view(view, light):
    view.ViewSize = [1600, 1000]
    view.UseColorPaletteForBackground = 0
    view.BackgroundColorMode = "Gradient"
    if light:
        view.Background = [0.975, 0.983, 0.992]
        view.Background2 = [0.81, 0.88, 0.93]
    else:
        view.Background = [0.010, 0.014, 0.024]
        view.Background2 = [0.04, 0.06, 0.10]
    view.OrientationAxesVisibility = 1
    view.CenterOfRotation = [0.5 * (bounds[0] + bounds[1]), 0.5 * (bounds[2] + bounds[3]), 0.0]
    view.InteractionMode = "3D"
    view.ViewTime = 17.0
    view.CameraPosition = [1.24, -0.86, 0.78]
    view.CameraFocalPoint = [0.50, 0.333, 0.0]
    view.CameraViewUp = [-0.30, 0.33, 0.90]
    view.CameraParallelProjection = 0
    view.CameraViewAngle = 30.0


light_view = GetActiveViewOrCreate("RenderView")
RenameLayout("LIGHT ANATOMY — CUT / REPAIR TIMELINE", GetLayout(light_view))
configure_view(light_view, True)
current_view = CreateView("RenderView")
current_layout = CreateLayout(name="CURRENT HEAT — CUT / REPAIR TIMELINE")
AssignViewToLayout(view=current_view, layout=current_layout, hint=0)
configure_view(current_view, False)
joule_view = CreateView("RenderView")
joule_layout = CreateLayout(name="JOULE HEAT — CUT / REPAIR TIMELINE")
AssignViewToLayout(view=joule_view, layout=joule_layout, hint=0)
configure_view(joule_view, False)

light_display = Show(light_voxels, light_view, "GeometryRepresentation")
light_display.Representation = "Surface With Edges"
light_display.ColorArrayName = [None, ""]
light_display.DiffuseColor = [0.045, 0.22, 0.31]
light_display.AmbientColor = [0.045, 0.22, 0.31]
light_display.EdgeColor = [0.005, 0.012, 0.018]
light_display.LineWidth = 0.70

current_display = Show(current_voxels, current_view, "GeometryRepresentation")
current_display.Representation = "Surface With Edges"
current_display.EdgeColor = [0.02, 0.025, 0.035]
ColorBy(current_display, ("POINTS", "current_density"))
current_lut = GetColorTransferFunction("current_density")
current_lut.RGBPoints = [
    0.0, 0.02, 0.06, 0.18,
    0.12 * manifest["global_current_max"], 0.02, 0.62, 0.78,
    0.45 * manifest["global_current_max"], 0.98, 0.78, 0.16,
    manifest["global_current_max"], 0.94, 0.12, 0.04,
]
current_lut.ColorSpace = "RGB"
current_lut.RescaleTransferFunction(0.0, manifest["global_current_max"])
GetOpacityTransferFunction("current_density").RescaleTransferFunction(0.0, manifest["global_current_max"])

joule_display = Show(joule_voxels, joule_view, "GeometryRepresentation")
joule_display.Representation = "Surface With Edges"
joule_display.EdgeColor = [0.02, 0.025, 0.035]
ColorBy(joule_display, ("POINTS", "joule_density"))
joule_lut = GetColorTransferFunction("joule_density")
joule_lut.RGBPoints = [
    0.0, 0.06, 0.00, 0.12,
    0.20 * manifest["global_joule_max"], 0.37, 0.02, 0.55,
    0.55 * manifest["global_joule_max"], 0.95, 0.26, 0.21,
    manifest["global_joule_max"], 1.00, 0.92, 0.36,
]
joule_lut.ColorSpace = "RGB"
joule_lut.RescaleTransferFunction(0.0, manifest["global_joule_max"])
GetOpacityTransferFunction("joule_density").RescaleTransferFunction(0.0, manifest["global_joule_max"])


def show_markers(view, light):
    source_display = Show(source, view, "GeometryRepresentation")
    sink_display = Show(sink, view, "GeometryRepresentation")
    upper_display = Show(upper_marker, view, "GeometryRepresentation")
    lower_display = Show(lower_marker, view, "GeometryRepresentation")
    source_display.DiffuseColor = [0.00, 0.56, 0.38] if light else [0.10, 0.95, 0.72]
    source_display.AmbientColor = source_display.DiffuseColor
    sink_display.DiffuseColor = [0.78, 0.08, 0.13] if light else [0.98, 0.20, 0.30]
    sink_display.AmbientColor = sink_display.DiffuseColor
    upper_display.DiffuseColor = [0.00, 0.56, 0.30] if light else [0.15, 0.95, 0.68]
    upper_display.AmbientColor = upper_display.DiffuseColor
    lower_display.DiffuseColor = [0.58, 0.12, 0.76] if light else [0.84, 0.30, 0.98]
    lower_display.AmbientColor = lower_display.DiffuseColor


for view, light in [(light_view, True), (current_view, False), (joule_view, False)]:
    show_markers(view, light)
    annotation_display = Show(state_annotation, view, "TextSourceRepresentation")
    annotation_display.WindowLocation = "Any Location"
    annotation_display.Position = [0.018, 0.700]
    annotation_display.FontFamily = "Arial"
    annotation_display.FontSize = 18
    annotation_display.Bold = 1
    annotation_display.Color = [0.025, 0.08, 0.12] if light else [0.94, 0.97, 1.0]
    annotation_display.Shadow = 0 if light else 1
    annotation_display.Justification = "Left"
    annotation_display.VerticalJustification = "Bottom"

current_bar = GetScalarBar(current_lut, current_view)
current_bar.Title = "current_density"
current_bar.ComponentTitle = "exact MOOSE cell field"
current_bar.TitleColor = [0.93, 0.95, 1.0]
current_bar.LabelColor = [0.88, 0.91, 0.97]
current_bar.WindowLocation = "Any Location"
current_bar.Position = [0.81, 0.15]
current_bar.Orientation = "Vertical"
current_bar.ScalarBarLength = 0.52
current_display.SetScalarBarVisibility(current_view, True)

joule_bar = GetScalarBar(joule_lut, joule_view)
joule_bar.Title = "joule_density"
joule_bar.ComponentTitle = "exact MOOSE cell field"
joule_bar.TitleColor = [0.93, 0.95, 1.0]
joule_bar.LabelColor = [0.88, 0.91, 0.97]
joule_bar.WindowLocation = "Any Location"
joule_bar.Position = [0.81, 0.15]
joule_bar.Orientation = "Vertical"
joule_bar.ScalarBarLength = 0.52
joule_display.SetScalarBarVisibility(joule_view, True)

static_title = "CUT → REPAIR • 37 RECORDED STATES • PLAY / PAUSE / SCRUB"
evidence_label = "2D EVIDENCE EXTRUDED FOR 3D INSPECTION"
method_label = "FIXED-RULE REPAIR TRIAL • SNAP TO TIMESTEPS • NO INTERPOLATION"
conditions = "σmaterial=1.0 • σmedium=1e-6 • SOURCE x=0 value 1 → SINK x=1 value 0"
for view, light in [(light_view, True), (current_view, False), (joule_view, False)]:
    title_color = [0.02, 0.20, 0.28] if light else [1.0, 0.82, 0.20]
    boundary_color = [0.58, 0.27, 0.00] if light else [1.0, 0.55, 0.22]
    text_color = [0.04, 0.10, 0.14] if light else [0.76, 0.83, 0.92]
    add_overlay(view, f"{view.SMProxy.GetLogName()} title", static_title, [0.19, 0.955], 19, title_color, True, not light)
    add_overlay(view, f"{view.SMProxy.GetLogName()} evidence", evidence_label, [0.28, 0.915], 16, boundary_color, True, not light)
    add_overlay(view, f"{view.SMProxy.GetLogName()} method", method_label, [0.018, 0.865], 13, text_color, True, not light)
    add_overlay(view, f"{view.SMProxy.GetLogName()} conditions", conditions, [0.018, 0.020], 12, text_color, False, not light)


def set_time(value):
    animation.AnimationTime = float(value)
    for view in (light_view, current_view, joule_view):
        view.ViewTime = float(value)
        Render(view)


set_time(17)
SetActiveView(light_view)
SetActiveSource(light_voxels)
Render(light_view)

if "--screenshot" in sys.argv:
    index = sys.argv.index("--screenshot")
    target = Path(sys.argv[index + 1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    SaveScreenshot(str(target), light_view, ImageResolution=[1600, 1000])
    print(target)
if "--screenshot-18" in sys.argv:
    set_time(18)
    index = sys.argv.index("--screenshot-18")
    target = Path(sys.argv[index + 1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    SaveScreenshot(str(target), light_view, ImageResolution=[1600, 1000])
    print(target)
if "--screenshot" not in sys.argv and "--screenshot-18" not in sys.argv:
    print("Timeline ready at epoch 17; use ParaView play/pause or scrub to epoch 18.")
