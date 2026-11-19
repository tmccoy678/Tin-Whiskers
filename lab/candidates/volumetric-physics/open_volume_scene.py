#!/usr/bin/env pvpython
"""Open the genuine 192x128x9 volume in two local ParaView layouts."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from paraview.simple import (  # type: ignore
    AssignViewToLayout,
    Box,
    Clip,
    ColorBy,
    CreateLayout,
    CreateView,
    GetActiveViewOrCreate,
    GetColorTransferFunction,
    GetLayout,
    GetOpacityTransferFunction,
    GetScalarBar,
    Glyph,
    Hide,
    OpenDataFile,
    ProgrammableFilter,
    Render,
    RenameLayout,
    RenameSource,
    SaveScreenshot,
    SetActiveSource,
    SetActiveView,
    Show,
    Slice,
    Text,
    UpdatePipeline,
)


script_name = globals().get("__file__")
root_from_launcher = os.environ.get("VOLUME_VIZ_ROOT")
if script_name is not None:
    HERE = Path(script_name).resolve().parent
elif root_from_launcher is not None:
    HERE = Path(root_from_launcher).resolve()
else:
    raise RuntimeError("cannot locate volume bundle; use launch-volume-local.sh")

RESULT = HERE / "result-manifest.json"
VTK = HERE / "output/final-volume.vtk"
SUMMARY = HERE / "output/summary.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


manifest = json.loads(RESULT.read_text())
summary = json.loads(SUMMARY.read_text())
for record in manifest["files"]:
    path = HERE / record["path"]
    if sha256(path) != record["sha256"]:
        raise RuntimeError(f"result hash mismatch: {record['path']}")


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


def point_subset(input_proxy, name: str, predicate: str):
    proxy = ProgrammableFilter(registrationName=name, Input=input_proxy)
    proxy.OutputDataSetType = "vtkPolyData"
    proxy.CopyArrays = 0
    proxy.Script = f'''from vtkmodules.vtkCommonCore import vtkIntArray, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray
source = self.GetInputDataObject(0, 0)
output = self.GetOutputDataObject(0)
source_pd = source.GetPointData()
occupancy = source_pd.GetArray("occupancy")
growth_direction = source_pd.GetArray("growth_direction")
selected = []
for point_id in range(source.GetNumberOfPoints()):
    if {predicate}:
        selected.append(point_id)
points = vtkPoints()
vertices = vtkCellArray()
for point_id in selected:
    new_id = points.InsertNextPoint(source.GetPoint(point_id))
    vertices.InsertNextCell(1)
    vertices.InsertCellPoint(new_id)
output.SetPoints(points)
output.SetVerts(vertices)
for array_index in range(source_pd.GetNumberOfArrays()):
    original = source_pd.GetArray(array_index)
    if original is None:
        continue
    copied = original.NewInstance()
    copied.SetName(original.GetName())
    copied.SetNumberOfComponents(original.GetNumberOfComponents())
    for point_id in selected:
        copied.InsertNextTuple(original.GetTuple(point_id))
    output.GetPointData().AddArray(copied)
layer = vtkIntArray()
layer.SetName("z_layer")
for point_id in selected:
    layer.InsertNextValue(point_id // (192 * 128))
output.GetPointData().AddArray(layer)
'''
    return proxy


def box_glyph(input_proxy, name: str, spacing: float):
    glyph = Glyph(registrationName=name, Input=input_proxy, GlyphType="Box")
    glyph.OrientationArray = ["POINTS", "No orientation array"]
    glyph.ScaleArray = ["POINTS", "No scale array"]
    glyph.ScaleFactor = 1.0
    glyph.GlyphMode = "All Points"
    glyph.GlyphType.XLength = spacing
    glyph.GlyphType.YLength = spacing
    glyph.GlyphType.ZLength = spacing
    return glyph


reader = OpenDataFile(str(VTK))
RenameSource("00 TRUE VOLUME — 192x128x9 finite-volume fields", reader)
UpdatePipeline(proxy=reader)
info = reader.GetDataInformation()
bounds = info.GetBounds()
spacing = bounds[1] / 191.0
z_mid = 4.0 * spacing

occupied_points = point_subset(
    reader,
    "01 OCCUPIED VOXEL CENTERS — exact occupancy == 1",
    "occupancy.GetTuple1(point_id) > 0.5",
)
occupied_voxels = box_glyph(
    occupied_points,
    "02 OCCUPIED VOXELS — LIGHT / CURRENT toggle",
    spacing,
)
plus_z_points = point_subset(
    reader,
    "03 +Z GROWTH CENTERS — exact direction",
    "occupancy.GetTuple1(point_id) > 0.5 and growth_direction.GetComponent(point_id, 2) > 0.5",
)
plus_z_voxels = box_glyph(plus_z_points, "04 +Z GROWTH VOXELS — gold", spacing)
minus_z_points = point_subset(
    reader,
    "05 -Z GROWTH CENTERS — exact direction",
    "occupancy.GetTuple1(point_id) > 0.5 and growth_direction.GetComponent(point_id, 2) < -0.5",
)
minus_z_voxels = box_glyph(minus_z_points, "06 -Z GROWTH VOXELS — violet", spacing)

z_clip = Clip(registrationName="07 DRAGGABLE Z CLIP — toggle eye, then Show Plane", Input=occupied_voxels)
z_clip.ClipType = "Plane"
z_clip.ClipType.Origin = [0.5, 0.5 * (bounds[2] + bounds[3]), z_mid]
z_clip.ClipType.Normal = [0.0, 0.0, -1.0]
z_clip.Invert = 0

joule_slice = Slice(registrationName="08 DRAGGABLE JOULE Z SLICE — select and Show Plane", Input=reader)
joule_slice.SliceType = "Plane"
joule_slice.SliceType.Origin = [0.5, 0.5 * (bounds[2] + bounds[3]), z_mid]
joule_slice.SliceType.Normal = [0.0, 0.0, 1.0]

volume_clip = Clip(registrationName="09 FULL-FIELD Z CLIP — current/Joule diagnostic", Input=reader)
volume_clip.ClipType = "Plane"
volume_clip.ClipType.Origin = [0.5, 0.5 * (bounds[2] + bounds[3]), z_mid]
volume_clip.ClipType.Normal = [0.0, 0.0, -1.0]
volume_clip.Invert = 0

y_center = 0.5 * (bounds[2] + bounds[3])
z_center = 0.5 * (bounds[4] + bounds[5])
source_plane = Box(registrationName="10 SOURCE PLANE — x=0, V=1")
source_plane.Center = [bounds[0], y_center, z_center]
source_plane.XLength = 0.50 * spacing
source_plane.YLength = (bounds[3] - bounds[2]) + spacing
source_plane.ZLength = (bounds[5] - bounds[4]) + spacing
sink_plane = Box(registrationName="11 SINK PLANE — x=1, V=0")
sink_plane.Center = [bounds[1], y_center, z_center]
sink_plane.XLength = 0.50 * spacing
sink_plane.YLength = (bounds[3] - bounds[2]) + spacing
sink_plane.ZLength = (bounds[5] - bounds[4]) + spacing


def configure_view(view, light: bool):
    view.ViewSize = [1600, 1000]
    view.UseColorPaletteForBackground = 0
    view.BackgroundColorMode = "Gradient"
    if light:
        view.Background = [0.975, 0.982, 0.990]
        view.Background2 = [0.80, 0.88, 0.93]
    else:
        view.Background = [0.010, 0.014, 0.024]
        view.Background2 = [0.040, 0.060, 0.10]
    view.OrientationAxesVisibility = 1
    view.CenterOfRotation = [0.5, y_center, z_center]
    view.InteractionMode = "3D"
    view.CameraPosition = [1.27, -0.88, 0.63]
    view.CameraFocalPoint = [0.50, y_center, z_center]
    view.CameraViewUp = [-0.28, 0.31, 0.91]
    view.CameraParallelProjection = 0
    view.CameraViewAngle = 29.0
    grid = view.AxesGrid
    grid.Visibility = 1
    grid.UseCustomBounds = 1
    grid.CustomBounds = [
        bounds[0] - 0.5 * spacing,
        bounds[1] + 0.5 * spacing,
        bounds[2] - 0.5 * spacing,
        bounds[3] + 0.5 * spacing,
        bounds[4] - 0.5 * spacing,
        bounds[5] + 0.5 * spacing,
    ]
    grid.XTitle = "x: source 0 → sink 1"
    grid.YTitle = "y: 128 layers"
    grid.ZTitle = "z layers: 0 / 4 / 8"
    grid.ZAxisUseCustomLabels = 1
    grid.ZAxisLabels = [0.0, 4.0 * spacing, 8.0 * spacing]
    grid.ShowGrid = 1
    grid.ShowEdges = 1
    label_color = [0.06, 0.10, 0.14] if light else [0.90, 0.94, 1.0]
    grid.GridColor = [0.32, 0.38, 0.43] if light else [0.35, 0.42, 0.55]
    for axis in "XYZ":
        setattr(grid, f"{axis}LabelColor", label_color)
        setattr(grid, f"{axis}TitleColor", label_color)
        setattr(grid, f"{axis}LabelFontSize", 12)
        setattr(grid, f"{axis}TitleFontSize", 13)


light_view = GetActiveViewOrCreate("RenderView")
RenameLayout("LIGHT ANATOMY — TRUE VOLUME", GetLayout(light_view))
configure_view(light_view, light=True)

field_view = CreateView("RenderView")
field_layout = CreateLayout(name="CURRENT / JOULE — TRUE VOLUME")
AssignViewToLayout(view=field_view, layout=field_layout, hint=0)
configure_view(field_view, light=False)

# Light anatomy: all occupied voxels remain categorical and current-independent.
light_body = Show(occupied_voxels, light_view, "GeometryRepresentation")
light_body.Representation = "Surface With Edges"
light_body.DiffuseColor = [0.045, 0.22, 0.31]
light_body.AmbientColor = [0.045, 0.22, 0.31]
light_body.EdgeColor = [0.005, 0.012, 0.018]
light_body.LineWidth = 0.70

light_plus = Show(plus_z_voxels, light_view, "GeometryRepresentation")
light_plus.Representation = "Surface With Edges"
light_plus.DiffuseColor = [0.95, 0.52, 0.02]
light_plus.AmbientColor = [0.95, 0.52, 0.02]
light_plus.EdgeColor = [0.22, 0.08, 0.00]
light_minus = Show(minus_z_voxels, light_view, "GeometryRepresentation")
light_minus.Representation = "Surface With Edges"
light_minus.DiffuseColor = [0.61, 0.20, 0.78]
light_minus.AmbientColor = [0.61, 0.20, 0.78]
light_minus.EdgeColor = [0.14, 0.02, 0.20]

light_clip = Show(z_clip, light_view, "GeometryRepresentation")
light_clip.Representation = "Surface With Edges"
light_clip.DiffuseColor = [0.08, 0.34, 0.43]
light_clip.AmbientColor = [0.08, 0.34, 0.43]
light_clip.EdgeColor = [0.005, 0.012, 0.018]
Hide(z_clip, light_view)

# Field view: clipped occupied voxels show current; full-volume z slice shows Joule.
field_body = Show(z_clip, field_view, "GeometryRepresentation")
field_body.Representation = "Surface With Edges"
field_body.EdgeColor = [0.02, 0.025, 0.035]
field_body.LineWidth = 0.55
ColorBy(field_body, ("POINTS", "current_magnitude"))

current_max = float(summary["final_max_current"])
current_lut = GetColorTransferFunction("current_magnitude")
current_lut.RGBPoints = [
    0.0, 0.02, 0.06, 0.18,
    0.12 * current_max, 0.02, 0.62, 0.78,
    0.45 * current_max, 0.98, 0.78, 0.16,
    current_max, 0.94, 0.12, 0.04,
]
current_lut.ColorSpace = "RGB"
current_lut.RescaleTransferFunction(0.0, current_max)
GetOpacityTransferFunction("current_magnitude").RescaleTransferFunction(0.0, current_max)

joule_display = Show(joule_slice, field_view, "GeometryRepresentation")
joule_display.Representation = "Surface With Edges"
joule_display.Opacity = 0.62
joule_display.EdgeColor = [0.16, 0.16, 0.19]
ColorBy(joule_display, ("POINTS", "joule_density"))
joule_lut = GetColorTransferFunction("joule_density")
joule_range = reader.GetDataInformation().GetPointDataInformation().GetArrayInformation("joule_density").GetComponentRange(0)
joule_lut.RGBPoints = [
    joule_range[0], 0.06, 0.00, 0.12,
    0.20 * joule_range[1], 0.37, 0.02, 0.55,
    0.55 * joule_range[1], 0.95, 0.26, 0.21,
    joule_range[1], 1.00, 0.92, 0.36,
]
joule_lut.ColorSpace = "RGB"
joule_lut.RescaleTransferFunction(joule_range[0], joule_range[1])
GetOpacityTransferFunction("joule_density").RescaleTransferFunction(joule_range[0], joule_range[1])

full_field_display = Show(volume_clip, field_view, "GeometryRepresentation")
full_field_display.Representation = "Surface"
full_field_display.Opacity = 0.10
ColorBy(full_field_display, ("POINTS", "current_magnitude"))
Hide(volume_clip, field_view)


def show_boundaries(view, light: bool):
    source_display = Show(source_plane, view, "GeometryRepresentation")
    source_display.Opacity = 0.52
    source_display.DiffuseColor = [0.00, 0.56, 0.38] if light else [0.10, 0.95, 0.72]
    source_display.AmbientColor = source_display.DiffuseColor
    sink_display = Show(sink_plane, view, "GeometryRepresentation")
    sink_display.Opacity = 0.52
    sink_display.DiffuseColor = [0.78, 0.08, 0.13] if light else [0.98, 0.20, 0.30]
    sink_display.AmbientColor = sink_display.DiffuseColor


show_boundaries(light_view, light=True)
show_boundaries(field_view, light=False)

current_bar = GetScalarBar(current_lut, field_view)
current_bar.Title = "current magnitude"
current_bar.ComponentTitle = "dimensionless model field"
current_bar.TitleColor = [0.93, 0.95, 1.0]
current_bar.LabelColor = [0.88, 0.91, 0.97]
current_bar.WindowLocation = "Any Location"
current_bar.Position = [0.82, 0.18]
current_bar.Orientation = "Vertical"
current_bar.ScalarBarLength = 0.48
current_bar.ScalarBarThickness = 16
field_body.SetScalarBarVisibility(field_view, True)

joule_bar = GetScalarBar(joule_lut, field_view)
joule_bar.Title = "Joule density"
joule_bar.ComponentTitle = "discrete face dissipation / voxel volume"
joule_bar.TitleColor = [0.93, 0.95, 1.0]
joule_bar.LabelColor = [0.88, 0.91, 0.97]
joule_bar.WindowLocation = "Any Location"
joule_bar.Position = [0.32, 0.075]
joule_bar.Orientation = "Horizontal"
joule_bar.ScalarBarLength = 0.40
joule_bar.ScalarBarThickness = 14
joule_display.SetScalarBarVisibility(field_view, True)

title = "SIMULATED 3D PHYSICS"
boundary = "DIMENSIONLESS MECHANISM — MATERIAL CALIBRATION PENDING"
status = (
    "192 × 128 × 9 FINITE-VOLUME CONDUCTION  •  SIX FACE-NEIGHBORS\n"
    "7,019 occupied voxels  •  seed layer z=4  •  occupied layers z=2–6\n"
    "214 exact out-of-plane growth choices  •  +z GOLD  •  -z VIOLET"
)
conditions = (
    "σmaterial=1.0  •  σmedium=0.01  •  Vsource=1  •  Vsink=0  •  y/z exterior no-flux\n"
    f"residual={summary['solver_residual_linf']:.3e}  •  source/sink error={summary['source_sink_relative_error']:.3e}  •  source/Joule error={summary['source_joule_relative_error']:.3e}"
)

add_overlay(light_view, "LIGHT LABEL — title", title, [0.37, 0.955], 22, [0.02, 0.20, 0.28], True, False)
add_overlay(light_view, "LIGHT LABEL — boundary", boundary, [0.245, 0.915], 16, [0.62, 0.28, 0.00], True, False)
add_overlay(light_view, "LIGHT LABEL — status", status, [0.018, 0.805], 15, [0.025, 0.08, 0.12], True, False)
add_overlay(light_view, "LIGHT LABEL — conditions", conditions, [0.018, 0.020], 12, [0.04, 0.10, 0.14], False, False)

add_overlay(field_view, "FIELD LABEL — title", title, [0.37, 0.955], 22, [1.0, 0.82, 0.20], True)
add_overlay(field_view, "FIELD LABEL — boundary", boundary, [0.245, 0.915], 16, [1.0, 0.55, 0.22], True)
add_overlay(field_view, "FIELD LABEL — status", status, [0.018, 0.805], 15, [0.94, 0.97, 1.0], True)
add_overlay(field_view, "FIELD LABEL — conditions", conditions, [0.018, 0.020], 12, [0.76, 0.83, 0.92])

Render(field_view)
SetActiveView(light_view)
SetActiveSource(occupied_voxels)
Render(light_view)

if "--screenshot" in sys.argv:
    index = sys.argv.index("--screenshot")
    target = Path(sys.argv[index + 1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    SaveScreenshot(str(target), light_view, ImageResolution=[1600, 1000])
    print(target)
if "--field-screenshot" in sys.argv:
    index = sys.argv.index("--field-screenshot")
    target = Path(sys.argv[index + 1]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    SaveScreenshot(str(target), field_view, ImageResolution=[1600, 1000])
    print(target)
if "--screenshot" not in sys.argv and "--field-screenshot" not in sys.argv:
    print(
        "Genuine volume ready: LIGHT ANATOMY foreground; CURRENT / JOULE tab retained; "
        "select the z clip or Joule slice and enable Show Plane to drag."
    )
