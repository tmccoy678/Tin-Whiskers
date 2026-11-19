# Adaptive reciprocal-yoke pilot — 120 actions

Status: completed pending-unit developmental pilot. Physical calibration,
concealed damage, and ensemble inference are the next promotion gates.

## Developmental outcome

| Arm | Flux ratio | Material ratio | Peak current per delivery reduction |
|---|---:|---:|---:|
| Adaptive seed 319 | 21.141× | 2.003× | 91.089% |
| Adaptive seed 571 | 20.744× | 2.002× | 89.838% |
| Fixed seed 319 | 21.858× | 2.041× | 91.064% |
| Fixed seed 571 | 21.487× | 2.036× | 89.848% |
| Yoked seed 319, actions from 571 | 20.926× | 1.994× | 91.089% |
| Yoked seed 571, actions from 319 | 20.641× | 1.993× | 89.838% |

Adaptive delivery finished 1.028% and 0.498% above reciprocal yoke. The fixed
sinusoidal controls delivered 3.39% and 3.58% more than adaptive while using
1.90% and 1.68% more material. The six arms therefore expose an interpretable
Pareto structure among delivery, material recruitment, and current
concentration.

Each adaptive policy completed a balanced four-action warmup, then selected
`upper-heavy` for the remaining 116 actions. That stable preference creates a
clear next experiment: reverse or degrade the upper consequence at a concealed
time and measure adaptation, transfer, recovery, and reciprocal yoke behavior.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `pilot-summary.tsv` | `79616e2704c8b3cc38526cf2e674a66bbc6871b141b74813e1c8bd85320519c3` |
| seed 319 actions | `00053f968ae52d5223ca5b8b7914b1012a56428ad75b55e31ee80209457e54a2` |
| seed 571 actions | `8fbc9fc01fc4a22f1049f5969627418826b01cbfa785613a35936874a0521d18` |
| seed 319 audit | `355155319518a2ab7c0aa492cd9523e5477a1a9e1567472de97c961cb2e085d3` |
| seed 571 audit | `83324b16dbe60a511df9a905062449c2cdf80ca4f7fbb71b52410136d47b5852` |

Raw artifacts remain in ignored
`simulation/work/live_moose/adaptive-reciprocal-pilot-120/`.
