# Volumetric physics candidate

This candidate earns the phrase **SIMULATED 3D PHYSICS** only after the
executable produces all four required facts:

1. a `192 × 128 × 9` volumetric mesh;
2. a three-dimensional finite-volume solve of
   `div(sigma grad(V)) = 0`;
3. material evolution restricted to the six face-neighbors;
4. recorded growth choices with nonzero `+z` or `-z` direction.

It is not an extrusion renderer. The exact 192 by 128 state-120 occupied-cell
skeleton enters only on the middle layer `z=4`. Every later off-plane voxel is
chosen by the simulated six-neighbor growth rule. The source PNG hash, exact
cell coordinates, y-axis mapping, and occupied count live in
`seed/manifest.json`.

## Physics and boundaries

- Cell-centered scalar conductivity is `1.0` in material and `0.01` in medium.
  These are dimensionless mechanism-test values, not a calibrated material.
- Harmonic face conductivity enforces flux continuity at material interfaces.
- `V=1` on the full `x=0` plane and `V=0` on the full `x=191` plane.
- Missing neighbors on the four exterior y/z faces impose zero normal flux.
- Red-black SOR solves the six-face finite-volume equation. The stopping
  criterion is the maximum normalized local flux imbalance.
- Cell current is reconstructed from harmonic face fluxes. Joule power is the
  exact discrete face dissipation `k_face * (delta V)^2 * area / distance`,
  divided equally between its two cells to form the written Joule-density
  field. Integrated Joule power and source/sink current are recorded.
- Material accounting is exact occupied-voxel count times voxel volume.

Growth candidates are empty voxels with at least one occupied face-neighbor.
Their weight is the strongest local face flux from an occupied parent. A
seed-319 exponential race selects 160 candidates per epoch without replacement.
The parent-to-child direction is stored as `growth_direction`, so out-of-plane
choices are directly inspectable.

## Tiny convergence test

```zsh
./verify.sh
```

This runs unit checks and solves a homogeneous `18 × 12 × 7` volume from a
nonlinear initial voltage field. It requires the residual to fall below
`1e-9`, the numerical field to match the analytic linear solution, and source
and sink current to balance.

## Run the volumetric mechanism test

```zsh
./run.sh
```

The output directory contains:

- `final-volume.vtk` — binary VTK structured volume with occupancy,
  conductivity, voltage, current vector/magnitude, Joule density, growth epoch,
  and growth direction;
- `metrics.tsv` — residual, current, Joule, mass, and directional-growth
  accounting for every epoch;
- `summary.json` — the compact admission boundary and final result.

Open `final-volume.vtk` in the pristine local ParaView installation. Threshold
`occupancy` at 0.5 to inspect literal material voxels; slice or clip the full
volume to inspect true internal z layers.

Verify the saved binary through ParaView's real VTK reader with:

```zsh
./verify-output.sh
```

`result-manifest.json` retains the exact source, executable, seed, metrics,
summary, and VTK hashes for the admitted run.

## Dedicated interactive scene

```zsh
./launch-volume-local.sh
```

The pristine local ParaView process opens two layouts:

- `LIGHT ANATOMY — TRUE VOLUME`: categorical dark occupied voxels, exact voxel
  edges, gold `+z` growth, violet `-z` growth, nine-layer z axis, and explicit
  source/sink planes.
- `CURRENT / JOULE — TRUE VOLUME`: clipped occupied voxels colored by current
  magnitude, a draggable Joule z slice, separate legends, and a hidden
  full-field clip toggle.

Both layouts permanently say `SIMULATED 3D PHYSICS` and
`DIMENSIONLESS MECHANISM — MATERIAL CALIBRATION PENDING`. No spatial smoothing
or geometry interpolation is used.
