# Consequence-reversal pilot — 120 actions

Status: completed first-order conditioning probe. At concealed epoch 60, the
material effect of the upper optical channel changed from full strength to 15%
while the lower channel retained full strength.

## Outcome

| Arm | Flux ratio | Material ratio | Peak current per delivery reduction |
|---|---:|---:|---:|
| Adaptive seed 319 | 21.127× | 2.001× | 91.089% |
| Adaptive seed 571 | 20.672× | 1.997× | 89.838% |
| Fixed seed 319 | 21.855× | 2.040× | 91.064% |
| Fixed seed 571 | 21.439× | 2.032× | 89.848% |
| Yoked seed 319, actions from 571 | 20.911× | 1.992× | 91.089% |
| Yoked seed 571, actions from 319 | 20.570× | 1.987× | 89.838% |

Adaptive delivery finished 1.033% and 0.495% above reciprocal yoke. Both
policies retained `upper-heavy` through every post-reversal action.

## Mechanism discovered

The controller admitted both actions through early warmup, then its confidence
gate retained only `upper-heavy` from approximately epoch 10 onward. Later
consequences continued updating the chosen arm while the alternative remained
outside the eligible set. The first reversal experiment therefore identifies
the next controller capability precisely:

1. detect persistent prediction error or an environmental change;
2. reopen bounded previously-safe alternatives for a short balanced renewal;
3. retain explicit renewal propensity and a separate RNG stream; and
4. compare recovery with fixed and reciprocal-yoked schedules.

The next material intervention also increases causal contrast through a full
channel swap or a concealed upper-path lesion, allowing the controller's
renewal behavior to become visibly and quantitatively consequential.

## Frozen artifacts

| Artifact | SHA-256 |
|---|---|
| `pilot-summary.tsv` | `d5e3ad6e6a0e746ff1a2361387e9b791ed80f8b4e9afe7caed9a6f82b3c48adf` |
| seed 319 actions | `b681d6601625377deef020779a965905c431ce0e6c588ff170e9cabdb48914db` |
| seed 571 actions | `a7ea4ce63d71c5c2c87b8f205e2012f5372dadafecf0ea0297efd5eede0c944f` |
| seed 319 audit | `41c993d5e67ee676c221ffcb0785e552684fc465ec85c36859a069b502e1e483` |
| seed 571 audit | `ef0620f97d4849c5f8b03dd8be2b60c918e9879841ea010aedfbd94c3a61c366` |

Raw artifacts remain in ignored
`simulation/work/live_moose/adaptive-reciprocal-pilot-120-reversal-60/`.
