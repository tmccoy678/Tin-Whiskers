#!/usr/bin/env python3
from pathlib import Path

import pyvista as pv

root = Path(__file__).resolve().parent
reader = pv.get_reader(str(root / "native_voltage_growth_out.e"))
reader.set_active_time_value(reader.time_values[-1])
mesh = reader.read()[0][0]

plotter = pv.Plotter(shape=(1, 2), off_screen=True, window_size=(1800, 720))
plotter.set_background("#05070b")
plotter.subplot(0, 0)
plotter.add_mesh(
    mesh,
    scalars="eta",
    cmap="bone",
    clim=(0, 1),
    show_edges=False,
    scalar_bar_args={"title": "eta", "color": "white"},
)
plotter.add_text("conductive phase eta · t = 0.02", color="white", font_size=18)
plotter.view_xy()
plotter.camera.tight(padding=0.05)

plotter.subplot(0, 1)
plotter.add_mesh(
    mesh,
    scalars="voltage",
    cmap="plasma",
    clim=(0, 1),
    show_edges=False,
    scalar_bar_args={"title": "voltage", "color": "white"},
)
plotter.add_text("live electric potential", color="white", font_size=18)
plotter.view_xy()
plotter.camera.tight(padding=0.05)

plotter.screenshot(root / "native_voltage_growth.png")
plotter.close()
