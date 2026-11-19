# Material and condition search space

The search begins with all conductive matter rather than a favored metal:
metallic elements, alloys, intermetallics, hydrides, liquid metals, conducting
polymers, carbon phases, semiconductors, and mixed ionic-electronic conductors.

## Governing coordinates

Candidate names are mapped into physical coordinates before simulation:

- reduced temperature `T / T_m` and pressure-dependent phase;
- pressure, gravity, host composition, redox potential, and ion activity;
- electric field, current density, magnetic field, and mechanical stress;
- photon frequency, phase, polarization, flux, absorption depth, and branch
  scale relative to wavelength;
- electron mean free path and optical skin depth relative to branch width;
- diffusion, advection, reaction, deposition, dissolution, and thermal time
  scales;
- radiation dose, defect production, oxide growth, and present morphology.

These variables form dimensionless groups such as Péclet and Damköhler numbers,
`beta * n`, skin-depth-to-branch ratio, reduced stress energy, and thermal- to
growth-time ratio. Sampling those groups covers Earth laboratories, vacuum,
microgravity, cryogenic surfaces, molten salts, planetary atmospheres, and
conductive giant-planet interiors within one phase map.

## Selection rule

Every candidate faces the same task curriculum:

1. terminal flux and conductance per unit material;
2. peak local field, temperature, and current density;
3. response across frequency and polarization;
4. survival after local damage and full transection;
5. repair time, material cost, and retention across repeated damage;
6. performance across multiple terminal arrangements;
7. information retained in morphology per unit energy and time.

No single score selects the winner. Pareto fronts retain architectures that
trade current capacity, sensory gain, energy, material, and repair differently.
Fixed wire and parallel grid remain reference organisms throughout.

## Computational route

1. Use Sobol or Latin-hypercube sampling across the dimensionless phase space.
2. Run the reduced Rust model for broad topology screening.
3. Send only Pareto candidates and falsifying edge cases to MOOSE for coupled
   voltage, heat, mechanics, phase, electromagnetic, and damage solves.
4. Calibrate surviving regimes with published measurements and a small physical
   pilot.
5. Replace simulated variance with measured material variance before final
   power analysis.

Material labels enter a result only when phase and kinetic data support the
mapping. Uncalibrated runs remain topology probes.
