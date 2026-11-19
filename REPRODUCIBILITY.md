# Reproducibility

The repository separates three evidence levels:

1. **Dimensionless topology probes** — the Rust model tests local rules, fields,
   damage, and present-state adaptation.
2. **Normalized multiphysics evaluation** — MOOSE solves voltage, current,
   Joule density, and topology-dependent conduction with `ΔV = 1`, metal
   conductivity `1`, and medium conductivity `1e-6`.
3. **Physical calibration** — the whisker ramp uses SI geometry, NIST tin
   resistivity, and measured NASA fusing-current data. Material names enter the
   developmental model only after this type of calibration.

## Reference environment

| Component | Reference version |
|---|---|
| MOOSE | snapshot commit `08315af82e` (2026-11-13) |
| MOOSE binary SHA-256 | `6f11e867e9952507791c26a653df598e17dcca4284c57b4546badc14f9981601` |
| Rust | `rustc 1.99.1 (58cf8f9c3 2026-10-13)` |
| Cargo | `1.99.1 (5f94df478 2026-08-27)` |
| R | `4.6.2` |
| Python | `3.13.18` |
| PyVista | `0.49.2` |
| NumPy | `2.5.5` |
| Pillow | `13.0.0` |
| ParaView | `6.2.1` Kitware arm64, DMG SHA-256 `14ab14fb68adab31677c21c008a2d987145093b001ac2424c7a025dc6d765b57` |

Cardinal, NekRS, OpenMC, Pronghorn, and SAM were explored in the ignored local
backend work area after the core runs. No admitted result in this repository
uses or implies one of those applications. They remain optional MOOSE-family
backends for later volumetric CFD, radiation, porous transport, and system-scale
transient studies.

MOOSE installation follows the official [prebuilt binary
instructions](https://mooseframework.inl.gov/getting_started/installation/moose_conda_binary.html).

## Core reproduction

```sh
MOOSE_BIN=/path/to/moose-opt simulation/reproduce_core.zsh
```

The script:

1. builds and runs the exact Rust baseline and Cherenkov conditions;
2. checks byte-level morphology hashes;
3. regenerates the fixed and developed topology images;
4. runs the same MOOSE voltage/Joule problem on the straight wire, parallel
   grid, and grown topology;
5. checks terminal flux against the committed reference values.

Expected morphology hashes:

| Condition | SHA-256 |
|---|---|
| Unlit baseline, seed 319 | `c08c25ab3f6d4ed71f7908e6b27472d490782b2663c04021ae4f33058ad98d49` |
| Cherenkov topology probe, seed 319 | `25f14e8667197b0f266e365ef25ff0e142c1e9131bd4d5cfd5fb2cfea16dc6fa` |

Expected normalized terminal flux:

| Topology | Flux |
|---|---:|
| Straight wire | `0.015861522654378` |
| Parallel grid | `0.079304851383882` |
| Grown topology | `0.0041372392954523` |

Set `FULL=1` to repeat the paired-seed and transection bootstraps. Heavy Exodus,
frame, and solver-log outputs are ignored and regenerate under
`simulation/output/`; committed TSV and Markdown files contain the compact raw
results and decision rules.

## Admitted candidate checks

These focused commands reproduce the newer evidence boundaries without running
the full bootstrap suite:

```sh
(cd lab/candidates/adaptive-controller && cargo test)
(cd lab/candidates/long-run-adaptive-screen && cargo test)
lab/candidates/interactive-3d/verify.sh
lab/candidates/interactive-3d/timeline/verify-cut-repair.sh
lab/candidates/volumetric-physics/verify-output.sh
```

The interactive cut–repair timeline is regenerated from ignored MOOSE states
with `timeline/build_timeline.py`; its verifier requires 37 exact hashes,
disconnection at epoch 17, first connection at epoch 18, and snap-to-state
playback. The volumetric verifier reads the committed VTK through ParaView's
VTK stack and requires the `192 × 128 × 9` volume, 7,019 occupied voxels, 214
out-of-plane growth choices, and nonzero current and Joule fields.

## Inputs that define each result

- Rust state and CLI: [`simulation/reduced-rust/`](simulation/reduced-rust/)
- MOOSE PDE and boundary conditions:
  [`simulation/voltage-routing/voltage_conduction.i`](simulation/voltage-routing/voltage_conduction.i)
- Paired and repair analyses: [`simulation/`](simulation/)
- Documented physical whisker boundary:
  [`simulation/whisker-ramp/`](simulation/whisker-ramp/)
- Material and condition search coordinates: [`materials/`](materials/)

Every report should record the repository commit, seed or seed range, complete
CLI, MOOSE version, material mapping, and whether a result is dimensionless,
normalized, or physically calibrated.
