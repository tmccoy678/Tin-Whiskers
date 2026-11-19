# Figure plan for the two-page extended abstract

## Page architecture

- Target: exactly two US-letter pages, 12-point Times New Roman, single-spaced, anonymous.
- Reuse the prior AgentVerify architecture: compact full-width title and anonymous line, followed by a continuous two-column body. Use 0.75-inch top/bottom and 0.625-inch left/right margins with a 0.25-inch column gap.
- Use two full-width figures, each no more than 1.55 inches high including panel labels; Figure 1 follows the opening section on page 1 and Figure 2 follows the results on page 2.
- Keep body headings compact and centered or run-in. Captions remain 12 point to honor the stated font requirement.
- Preserve literal pixels/voxels. Use nearest-neighbor scaling for lattice panels, no smoothing or branch interpolation, and no decorative neural-network imagery.

## Figure 1 — Biological arbors and the controlled computational probe

**Purpose.** Permit direct visual comparison of branching geometry while identifying biological observation, historical biological drawing, adaptive simulated lattice, and volumetric simulated physics as four distinct evidence classes.

**Panel A — Human H01 dendritic reconstruction.** Render one of the 104 proofread human temporal-cortex neurons locally from the official H01 SWC release. No H01 raster is presently stored in this repository, so this panel must be generated before composition; do not substitute a publisher screenshot. Record the selected segment/cell identifier, exact H01 object path or Neuroglancer state, export command, camera, scale bar, source URL, download/export date, and SHA-256 beside the figure source. The H01 release labels all released datasets CC BY 4.0. Attribution: Lichtman Laboratory at Harvard University and Connectomics at Google; scientific citation: Shapson-Coe et al. (2024), https://doi.org/10.1126/science.adk4858; data/license: https://h01-release.storage.googleapis.com/data.html.

**Panel B — Established second-species comparator.** Use [`figures/biological-purkinje-cajal-1899.jpg`](../figures/biological-purkinje-cajal-1899.jpg), SHA-256 `d726b26445d47aea435ed930e0e77670199236389a519ce002d2ef1f8055da11`. Label it **PIGEON CEREBELLUM — PURKINJE AND GRANULE CELLS — CAJAL, 1899**. The local provenance record identifies the Wikimedia Commons source as public domain: https://commons.wikimedia.org/wiki/File:PurkinjeCell.jpg. Crop only empty margins; retain the biological labels and do not trace or stylize the arbor.

**Panel C — AI-controlled literal lattice.** Use [`lab/candidates/interactive-3d/data/topology-0120.png`](../lab/candidates/interactive-3d/data/topology-0120.png), SHA-256 `b71b8fe617fb9e4ef7cce76aae7fc34a63a5546a08a7df840c09878db727e846`. Label it **SIMULATED 2D LATTICE — ADAPTIVE CONTROLLER — SEED 319 — STATE 120**. This is the admitted final state after 120 consequence-sensitive actions; it contains 6,539 exact occupied cells. Show source and sink rails and the two fixed actuator footprints. Do not call the extruded display 3D physics.

**Panel D — Literal volumetric probe.** Render [`lab/candidates/volumetric-physics/output/final-volume.vtk`](../lab/candidates/volumetric-physics/output/final-volume.vtk) locally with occupancy threshold `>= 0.5`, orthographic camera, visible voxel edges, source/sink planes, a small *z*-axis, and one clipped inset showing occupied layers. Record the ParaView state and exported PNG hash. Label it **SIMULATED 3D PHYSICS — 192 × 128 × 9 — SIX-NEIGHBOR GROWTH — 214 ±z CHOICES**. The admitted VTK SHA-256 is `753a22b99bdc9c1a938ef043e7a653b4a22ac03366a82eb48820be2fd76bcfca`; the final body has 7,019 occupied voxels across *z* = 2–6.

**Composition.** Arrange A–D in one horizontal strip with equal visual boxes and independent scale bars. Use neutral grayscale for biological panels, dark occupied anatomy on a pale field for C/D, and one thin rule separating biological from simulated panels. Put the evidence label above each panel so the comparison is legible before the caption.

**Caption.** *Figure 1. Branching geometry across distinct systems. (A) Proofread human temporal-cortex neuron from H01; (B) pigeon-cerebellum Purkinje and granule cells; (C) literal occupied lattice after 120 adaptive-controller actions; and (D) the dimensionless finite-volume body seeded from C and grown through six face-neighbors, including 214 out-of-plane choices. Panels are independently scaled; the comparison concerns branch geometry and field-shaped topology.*

## Figure 2 — Current-driven remodeling and literal cut reconnection

**Purpose.** Show the strongest utility measurements as visible before/after and disconnected/reconnected anatomy under the fixed two-fiber control.

**Panels A–B — Remodeling.** Use the local literal states `simulation/work/live_moose/current_fiber_remodel/epoch-000.png` and `epoch-036.png`, with SHA-256 values `3e84e21faef3cbc6b910b4ccc35da19c6df6b4895de9611b47d70fccfd1f23d8` and `5acf139c60c73a80f3231de8582e17dc9e7595443172fb2b1e36260be85c4201`. Before final composition, copy these exact bytes into a committed figure-source directory and retain the original metrics-table hash `a89f78fae2fb1ffc65cee5d0c3e7eb229b229035eff26be1c2c8180f9496474a`. Labels: **EPOCH 0** and **EPOCH 36 — 8.43× FLUX — 75.29% LOWER PEAK CURRENT DENSITY PER DELIVERED CURRENT**.

**Panels C–E — Cut repair.** Use the literal local states `simulation/work/live_moose/current_fiber_cut_repair/epoch-017.png`, `epoch-018.png`, and `epoch-036.png`, SHA-256 `2fdddba3b7ad9a1c18e0e3cb4879b799557afe2ef7c54f36b557c07fb2d87025`, `a774c81558c7f22d857f9e2da92caeabd6de158f40d65b706d5c22df9134b46e`, and `426ad347933cc6e302ae6ae3974ed37348617cd75f09266ddc654a57c020c736`. Before final composition, copy the exact bytes into the same committed source directory and retain metrics hash `aec47241921e391fac6937b751862203f89920ca4494b5dbe1f0bc5ac4b2b85a`. Labels: **DISCONNECTED — EPOCH 17**, **FIRST RECONNECTED — EPOCH 18**, and **CONNECTED — EPOCH 36 — 8.339× FLUX — 74.978% LOWER CONCENTRATION**.

**Composition.** Use a two-row plate: A–B on the first row and C–E on the second. Apply one fixed nearest-neighbor enlargement, identical crops within each sequence, white occupied cells on black, labeled left source/right sink rails, current arrow, upper/lower stimulus markers, and **FIXED-RULE CONTROL** on every row. A thin colored outline may mark the cut location and the first returned bridge, but it must not cover or add an occupied pixel.

**Caption.** *Figure 2. Simulated transport remodeling and repair under fixed-rule controls. (A–B) Thirty-six current/two-fiber epochs increased terminal flux 8.43-fold and reduced peak current density per delivered current by 75.29%. (C–E) A separately cut lattice remained disconnected through epoch 17, first reconnected at epoch 18, and finished at 8.339-fold flux with 74.978% lower concentration.*

## Citation and acceptance checks

1. Verify the H01 panel against the official released object and CC BY 4.0 terms; include the scale bar and full attribution in the composed source record.
2. Keep the Cajal panel’s public-domain source URL and local hash with the composition record.
3. Recompute every generated-panel SHA-256 after copying; pixel dimensions and hashes must match the sources above before labels are added.
4. Recalculate both current-concentration reductions directly from the frozen metrics tables and confirm epoch-17/18 four-neighbor connectivity labels from the cut record.
5. Confirm panel C is labeled adaptive and every Figure 2 panel is labeled fixed-rule. Do not let the fixed 8.43× result appear as an AI outcome.
6. Confirm Figure 1D says dimensionless simulated 3D physics and carries no calibrated PEDOT, CBRAM, biological, consciousness, or quantum-equivalence label.
7. At final layout, render once at publication size and require all evidence labels, axes, scale bars, rails, and figure captions to be readable without zoom. The final page-count check is exactly two pages.
