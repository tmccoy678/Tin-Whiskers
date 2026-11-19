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
EPOCHS=60
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

## Frontier-following photon loop

The first closed-loop controller reads the mean vertical position of occupied
cells in the leading three columns and moves the photon-band center toward that
frontier after each growth interval. `follow-gain` is the fraction of the
observed displacement applied at each update.

```sh
cargo run --release -- \
  --steps 650 --seed 319 --drive 0.7 \
  --light-gain 2.2 --light-center 0.35 --follow-gain 0.22 \
  --frame-every 2 --live-frame ../output/frontier-follow-live.ppm \
  --output ../output/frontier-follow
```

At seed `319`, this loop bridged at step 489 with 1,000 occupied cells. The
fixed photon field bridged at step 561 with 1,144 cells; the unlit baseline
bridged at step 570 with 1,162. The CSV records the evolving photon-band center
alongside frontier position and occupied-cell count.

## Cherenkov-cone field

The Cherenkov mode generates a two-dimensional cone slice from
`cos(theta) = 1 / (beta * n)`. The first test uses a water-like refractive index
of `1.33`, `beta = 0.99`, and a resulting half-angle of `40.582°`.

```sh
cargo run --release -- \
  --steps 650 --seed 319 --drive 0.7 \
  --light-mode cherenkov --refractive-index 1.33 --beta 0.99 \
  --source-x 0.05 --light-gain 2.2 --light-center 0.5 \
  --output ../output/cherenkov
```

The symmetric cone produced a lower-arm symmetry break and bridged at step 470
with 962 occupied cells. This reduced stage models the cone's optical geometry;
material-specific radiation yield, absorption, and deposition kinetics enter
through high-fidelity calibration.

## Development through repeated damage

`repair-cut-radius`, `repair-steps`, and `repair-cycles` continue growth after
damage. `repair-transect true` removes a full vertical band, guaranteeing loss
of every source-to-sink path before each repair epoch.

```sh
cargo run --release -- \
  --steps 650 --seed 319 --drive 0.7 \
  --light-mode cherenkov --refractive-index 1.33 --beta 0.99 \
  --source-x 0.05 --light-gain 2.2 \
  --repair-cut-radius 3 --repair-transect true \
  --repair-steps 1500 --repair-cycles "$EPOCHS" \
  --output ../output/transect-development
```

Across the first powered observation horizon, 63 of 64 independent seeds formed
an initial bridge and every bridged seed completed the observed
transection-and-repair epochs. Median repair time fell from 251 steps at the
first transection to 24 at the final observed epoch. The paired improvement was
176.40 steps with a 95% bootstrap interval of 141.40 to 209.79. The current
topology therefore changes later repair without an explicit history variable.

A local-lesion precursor produced no population-level improvement because most
lesions did not sever all routes. That null result is retained separately from
the guaranteed-transection test.

## Frames and dual lineages

`frame-dir` preserves numbered PPM frames for animation. `dual-seed true`
starts two source-connected lineages; gold and cyan identify their ancestry
while sharing the same uncalibrated kinetics. `mobility` controls the
probability that a growth opportunity deposits material during an interval.

