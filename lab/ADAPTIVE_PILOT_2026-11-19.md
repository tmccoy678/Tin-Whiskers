# Adaptive reciprocal-yoke pilot — 2026-11-19

Status: private pending-unit mechanism test. Physical calibration and ensemble
inference are the next promotion gates.

## Design

Two `192 x 128` material seeds each received:

- a 12-action adaptive Rust controller trajectory;
- the frozen sinusoidal fixed controller; and
- the other seed's exact adaptive action sequence as reciprocal yoked replay.

MOOSE remained the voltage/current/Joule-field authority. The Rust controller
received fixed-footprint field summaries without coordinates, chose only
`upper-heavy` or `lower-heavy`, and emitted an explicit propensity and audit
record. Material-growth randomness was common within seed and separate from
policy randomness.

## Implementation discoveries retained

1. The first attempt rejected a weighted-footprint record because an extreme
   top 5% made the weighted mean exceed the weighted p95. The adapter now
   reports `max(mean, weighted-p95)` as the conservative summary.
2. The second attempt found that raw controller features spanned roughly
   `1e-3` to `1e5`; uncertainty leverage rejected every action before warmup.
   This exposed a required scale-aware controller fix. The completed mechanism
   pilot used permissive abstract caps; safety evaluation begins with the
   calibrated material manifests.

## Descriptive outcome

| Seed | Adaptive vs fixed final flux | Adaptive vs reciprocal yoke final flux |
|---|---:|---:|
| 319 | +0.463% | +3.750% |
| 571 | +0.032% | +1.497% |

Both controllers completed balanced warmup and then selected `upper-heavy` for
every remaining epoch. The run produced 24 Rust audit records with nonzero
selection propensities and clean policy execution.

These two seeds establish a running causal controller/yoke pipeline and a
four-for-four directional adaptive edge. The next calibrated ensemble measures
its uncertainty, safe-use service, and response under concealed damage.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `pilot-summary.tsv` | `a900e6a540d69925b3784d619474464c7aadaa23b1f90e7457a1efc1d322377e` |
| seed 319 actions | `d17226ddf229d1cb78eda99b353d558a956dc3c8907cd97e6cfbfce0bedb306c` |
| seed 571 actions | `2eff6d7ddac14cd23af5b008c40d104d64b76c14c50c9e262c6085b6ee1eca4b` |
| seed 319 audit | `200b445d4fe7db344886a9c5d8f2685b6b5f0a7917a3e5ffbb90f747e2bd7055` |
| seed 571 audit | `94252cd676c88fc196688f553b2af10ce5fd730fa7ca0795d03596e3805689e5` |

Raw artifacts remain in ignored
`simulation/work/live_moose/adaptive-reciprocal-pilot/`.

## Next gate

Repeat only after scale-aware controller tests pass. Then apply the frozen
evaluation harness with calibrated material limits, concealed load/damage
schedules, and enough independent blocks to estimate uncertainty.
