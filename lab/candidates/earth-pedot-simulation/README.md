# Earth PEDOT SI-to-simulation candidate

This directory translates one validated seed-319 Earth exploratory draw into
SI-valued ranges and dimensionless descriptors for a later MOOSE candidate. It
does not edit or run the canonical simulation.

Files:

- `seed-319-draw.json` — exact output of the bounded sampler.
- `parameter-deck.json` — source-cited input roles, exact SI constants,
  dimensionless-group definitions, and constitutive blockers.
- `calculate.py` — dependency-free interval calculator and admission report.
- `seed-319-translation.json` — deterministic calculator output.
- `test_calculate.py` — conversion, range-propagation, provenance, and blocker
  tests.

Run:

```sh
python3 lab/candidates/earth-pedot-simulation/calculate.py
python3 -m unittest lab/candidates/earth-pedot-simulation/test_calculate.py
```

## What may enter a later MOOSE input

The deck admits, with their full ranges, the electrode geometry; terminal
waveform; current-compliance and time ceilings; initial concentrations and
finite EDOT inventory; temperature; low-voltage read boundary; and incident
optical wavelength, irradiance, and corridor geometry. Conductivity is admitted
only as a sensitivity-screen range. Pressure remains metadata unless an
evaporation or gas constitutive model is supplied.

The calculator derives waveform timing, a uniform-gap field descriptor,
terminal power and energy ceilings, reservoir consistency, incident photon
energy/flux/fluence, geometry ratios, a conditional voltage-to-threshold ratio,
and other explicitly named dimensionless groups. Every derived value carries
an interval. The one ratio whose denominator range includes zero is returned
with null bounds and an explicit range blocker rather than a fabricated finite
interval.

## What cannot enter yet

No transport coefficient, electrochemical rate, phase-field free-energy term,
growth yield, state-dependent conductivity law, thermal property, absorbed
optical source, mechanochemical coefficient, or stochastic nucleation law is
invented. `parameter-deck.json` lists the missing properties by model role and
the calculator copies them into the translation as promotion blockers.

The optical outputs are **incident** quantities. They do not imply absorption,
photoelectrochemical action, light-guided growth, or a measured physical effect.
Likewise, the uniform-gap field is a terminal geometry descriptor, not the
unknown local overpotential in the electrolyte.

Primary sources:

- [Janzakova et al., PEDOT dendrite growth](https://doi.org/10.1038/s41467-021-27274-9)
- [Janzakova et al., dendritic OECT electrical characterization](https://doi.org/10.1002/advs.202102973)
- [Hwang et al., separate light-guided PEDOT system](https://doi.org/10.1016/j.cej.2025.168284)
- [NIST fundamental constants](https://physics.nist.gov/cuu/Constants/)

This is a simulation-translation candidate, not wet-lab guidance beyond the
existing materials safety boundary and not a new physical claim.
