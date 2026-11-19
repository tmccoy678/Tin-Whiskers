# Dynamic load and damage topology screen

Question: can one growing conductor preserve minimum service when demand moves
among three sinks and the strongest active route is cut, while using the same
finite material budget as fixed and current-only developmental controls?

The Rust screen uses a `192 × 128` conduction field, one source, three sink
pads, three sparse optical actuators, demand changes every 15 epochs, and a
current-ranked lesion at epoch 90. Adaptive, fixed-cycle, and current-only arms
receive 100 new cells per epoch. The adaptive controller receives delivery and
current-concentration consequences and learns actuator values without route or
sink coordinates. Its dimensionless reward combines log delivery gain with
`0.75 ×` log concentration relief. A matched `3.0 ×` screen exposed a
short-horizon objective failure: stronger immediate relief weighting produced
higher long-horizon concentration, motivating contextual multi-step stress
prediction rather than coefficient escalation.

Run:

```sh
cargo run --release -- output
```

Endpoints include worst-case delivered current, peak current per delivery,
material, connection state, cut severity, and recovery epoch across eight
matched seeds.

## Matched result

All arms received identical sink schedules, `100` cells per growth epoch, a
`140`-cell current-ranked lesion at epoch 90, and exactly `17,896` final cells.
Policy and material-growth random streams were separated before the admitted
run.

| Endpoint | Adaptive | Fixed cycle | Current only |
|---|---:|---:|---:|
| Mean delivery | **0.07046** | 0.01771 | 0.007581 |
| Post-damage mean delivery | **0.13973** | 0.03483 | 0.01469 |
| Final delivery | **0.36220** | 0.24238 | 0.12155 |
| Connected-service fraction | **14.43%** | 5.80% | 2.56% |
| Post-damage connected fraction | **28.71%** | 11.54% | 5.08% |

Adaptive mean delivery reached **3.98×** fixed and **9.29×** current-only;
post-damage delivery reached **4.01×** and **9.51×**. All eight paired-seed
delivery contrasts were positive. Sink 2 supplied the strongest specialization:
adaptive delivered `65.6×` fixed and `68.6×` current-only and formed occupied
connections in three of eight seeds while both controls remained at zero.

Adaptive mean peak current per delivered current was 22.5% above fixed, while
its mean worst-seed maximum was slightly lower than both controls. A matched
`3.0×` immediate concentration-weight screen increased long-horizon
concentration, establishing that contextual multi-step stress prediction is
the next useful mechanism.

Full paired bootstrap analysis:
[`../../DYNAMIC_LOAD_REPAIR_ENSEMBLE_ANALYSIS_2026-11-19.md`](../../DYNAMIC_LOAD_REPAIR_ENSEMBLE_ANALYSIS_2026-11-19.md).

## Next causal screen

The smallest next experiment solves all three sinks on every present body and
optimizes the minimum normalized sink service. At epoch 90 each body is cloned
into damaged and undamaged twins, sink-0 demand remains fixed through epoch
120, and both twins receive identical actions and material. This separates
repair from demand switching while preserving the demonstrated adaptive
service advantage.

Metrics SHA-256:
`03c6d509e9db4388b9543dcf6ef2207e0402b9c1a53feb2dd0cf30f6a4cc9914`.
