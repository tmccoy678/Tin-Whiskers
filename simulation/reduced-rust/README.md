# Reduced field-guided growth model

This is a fast, inspectable candidate—not a substitute for MOOSE, COMSOL, or
physical calibration. It asks whether stochastic local deposition under a
continuous electric field can produce path-dependent branching whose geometry
changes the field guiding later growth.

The model couples:

- Laplace relaxation for electrical potential;
- diffusion and local depletion of mobile material;
- stochastic interface deposition weighted by field and concentration;
- an optional photon field that changes growth probability without naming a
  target graph.

Outputs are portable PGM fields plus a CSV trajectory. The model contains no
metal-specific constants yet. Those enter only after high-fidelity and physical
calibration.

```sh
cargo run --release -- \
  --steps 600 --seed 319 --drive 0.7 --light-gain 0.0 \
  --output ../output/baseline
```

## First paired run

The first comparison held the seed (`319`), drive (`0.7`), grid, starting
electrode, and number of steps constant. The baseline used no photon bias; the
paired condition added one sloping light field (`light_gain = 1.8`,
`light_slope = -0.45`). Both conditions bridged the modeled gap. The baseline
used 1,162 occupied cells and the photon-biased condition used 1,144, while the
resulting branch locations and inherited topology visibly diverged.

This establishes the software control needed for the later experiment: a
continuous light field can be the only changed input. The morphology is a
model prediction to test against high-fidelity and physical results.

