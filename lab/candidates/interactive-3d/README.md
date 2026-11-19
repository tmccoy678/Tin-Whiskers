# Interactive 3D adaptive lattice

## Chosen path

Use the parallel pristine Kitware ParaView 6.2.1 desktop app on the Pro at
`~/Applications/ParaView-6.2.1-Kitware-arm64.app`. The Exodus evidence is
copied to the Pro and read by a local ParaView process. This uses no QuickTime,
browser, account, upload, `pvserver`, or remote rendering. The launcher prefers
the pristine versioned app and retains the earlier path only as a fallback.

The admitted snapshot is `adaptive-seed-319`, state 120 of the 120-action
reciprocal pilot. Its final topology was produced after action 119, an
`upper-heavy` adaptive action with upper fraction 0.75 and lower fraction 0.25.
The source boundary is the model's left boundary at value 1; the sink is its
right boundary at value 0. The recorded controller units remain pending SI
calibration, so the scene labels them as model fields.

## Evidence treatment

Each occupied lattice cell becomes one axis-aligned box at its exact cell
center. Box width and height equal the original 192 by 128 mesh cell dimensions;
only depth is added. No smoothing, interpolation, subdivision, skeletonization,
or branch generation occurs. The viewport permanently says:

`EXTRUDED 2D EVIDENCE — NOT 3D PHYSICS`

The default `LIGHT ANATOMY` layout gives every occupied box one categorical
dark-teal color, independent of current, on a pale background with dark exact
voxel edges. It carries no current legend. This makes low-current tendrils as
visible as the main corridor without altering the data or geometry.

The adjacent `CURRENT HEAT` layout retains the exact cell `current_density`
color and its legend on the original dark background. The pipeline also
contains eye-toggle layers for all-cell current, clipping, and the continuous
MOOSE voltage diagnostic. Source and sink rails are boundary markers, and the
two spheres are labeled stimulus markers. `provenance.json` retains the
complete SHA-256 for every bundled source. The pristine application receipt is
`receipts/paraview-6.2.1-provenance.json`.

## Open locally

```zsh
./launch-local.sh
```

ParaView controls:

- `LIGHT ANATOMY` opens first. Select the `CURRENT HEAT` layout tab for exact
  current color and its legend; return to `LIGHT ANATOMY` for anatomy-first
  contrast.
- Left-drag orbits, the scroll wheel or right-drag zooms, and middle-drag pans.
- Select `02 CLIP VIEW — ACTIVE; select and drag plane`, toggle its eye, then
  enable its **Show Plane** control to drag the clipping plane.
- `01 OCCUPIED CELLS — FULL` is the exact full lattice and is active in the
  light layout.
- Toggle the eye beside `03 CURRENT FIELD — ALL CELLS` to inspect current in
  occupied and medium cells.
- Toggle the eye beside
  `04 VOLTAGE FIELD — CONTINUOUS FEM DIAGNOSTIC` for the unextruded voltage
  field. Its continuity is a finite-element field diagnostic, not lattice
  anatomy.

## Smallest verification

```zsh
./verify.sh
```

That one command verifies all source hashes, reads the final Exodus timestep,
checks the required field arrays, and proves that the literal PNG, Exodus
`metal` array, ParaView threshold, and generated cell centers all contain the
same 6,539 occupied cells.

## Frozen reversal candidate

The completed reversal-60 pilot is banked separately at
`scenes/reversal-adaptive-seed-319-state-120.json`, with exact final Exodus,
topology, metrics, actions, audits, summary, and implementation hashes copied
under `data/reversal-seed-319/`. It remains a candidate and did not replace the
foreground state-120 scene. Its summary explicitly keeps inference at
`not_run`; the manifest does not claim that the learned preference reversed.
