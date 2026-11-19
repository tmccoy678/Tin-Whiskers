# Space CBRAM SI-to-simulation candidate

This directory translates one validated seed-319 space screening draw into
SI-valued ranges, conductance observables, solver roles, and coupling blockers.
It does not edit or run canonical MOOSE/OpenMC models.

Files:

- `seed-319-draw.json` — exact accepted space-screening sampler output.
- `parameter-deck.json` — source-cited solver map, reference constants,
  dimensionless definitions, mission gates, and constitutive blockers.
- `calculate.py` — dependency-free interval translator.
- `seed-319-translation.json` — deterministic translation output.
- `test_calculate.py` — conversion, range, provenance, solver-boundary, and
  blocker tests.

Run:

```sh
python3 lab/candidates/space-cbram-simulation/calculate.py
python3 -m unittest lab/candidates/space-cbram-simulation/test_calculate.py
```

## Solver boundary

MOOSE conduction may receive the layer geometry, terminal read/set/reset
boundaries, current-compliance ceilings, and reversible terminal conductance.
MOOSE thermal and mechanics may receive geometry and the generic screening
temperature schedule. Predictive temperature and stress remain blocked until
layer thermal, mechanical, interface, and package properties exist.

OpenMC may receive candidate geometry and silicon absorbed-dose tally targets.
Those dose values are not particle sources. Material atom densities, device and
shield compositions, particle spectra, source normalization, scoring mass, and
mission duration remain required before an energy-deposition result can be
transferred to MOOSE. The intended later coupling direction is an OpenMC
heating/dose field into a MOOSE volumetric source, with calibrated MOOSE
temperature/density feedback returned through a coupling layer.

The eight mission quantities from the source manifest remain null,
`required-unset`, and promotion-blocking in the output: TID, SEE LET threshold,
heavy-ion fluence, displacement-damage fluence, lifetime, shielding areal
density, and operational temperature extrema.

## Conductance boundary

The electrical observable is terminal conductance and its reciprocal terminal
resistance. The calculator carries the bulk Ag conductivity only as a named
reference and returns filament conductivity as null. Computing
`sigma = G L / A` requires measured filament length, cross-sectional area, and
separated contact resistance.

Primary and authoritative sources include:

- [Ag-Ge-Se incremental programming](https://doi.org/10.1016/j.sse.2014.07.002)
- [Related low-voltage PMC cycling](https://doi.org/10.1088/0957-4484/22/25/254017)
- [CBRAM programming under cobalt-60 exposure](https://doi.org/10.1109/TNS.2017.2779860)
- [NASA thermal-vacuum verification standard](https://standards.nasa.gov/node/791)
- [OpenMC tally and dose normalization](https://docs.openmc.org/en/stable/usersguide/tallies.html)
- [OpenMC heating and energy deposition](https://docs.openmc.org/en/stable/methods/energy_deposition.html)
- [MOOSE heat-transfer module](https://mooseframework.inl.gov/modules/heat_transfer/index.html)
- [Cardinal OpenMC-to-MOOSE heat-source coupling](https://mooseframework.inl.gov/cardinal/tutorials/lwr_solid)

This is a screening translation, not a mission environment, hardware procedure,
radiation qualification, or new physical claim.
