# Reduced field-guided growth model

This fast, inspectable reduced model occupies the parameter-exploration stage
between high-fidelity simulation and physical calibration. It asks whether
stochastic local deposition under a continuous electric field can produce
path-dependent branching whose geometry changes the field guiding later
growth.

The model couples:

- Laplace relaxation for electrical potential;
- diffusion and local depletion of mobile material;
- stochastic interface deposition weighted by field and concentration;
- an optional photon field that changes growth probability without naming a
  target graph.

Outputs are portable PGM fields plus a CSV trajectory. Its present parameters
are dimensionless; high-fidelity simulation and physical calibration will
assign metal-specific constants.

```sh
cargo run --release -- \
  --steps 600 --seed 319 --drive 0.7 --light-gain 0.0 \
  --output ../output/baseline
```

## First paired run

The first comparison held the seed (`319`), drive (`0.7`), grid, starting
electrode, maximum step budget, and bridge stopping rule constant. The baseline
used no photon bias; the paired condition added one sloping light field
(`light_gain = 1.8`, `light_slope = -0.45`). Both conditions bridged the modeled
gap. The baseline bridged at step 570 with 1,162 occupied cells; the
photon-biased condition bridged at step 561 with 1,144. Their branch locations
and inherited topology visibly diverged.

This establishes the software control needed for the later experiment: a
continuous light field can be isolated as the changed input. The resulting
morphology supplies a prediction for comparison with high-fidelity and
physical results.

