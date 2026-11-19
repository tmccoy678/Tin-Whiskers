# Dynamic-load and repair ensemble analysis

## Integrity of the matched screen

The frozen TSV contains 4,344 observations: three arms × eight matched seeds
(`319–326`) × 181 epochs (`0–180`). Every seed/epoch shares the same active
sink, pre/post-damage state, occupied-cell count, and lesion size across arms.
Each arm receives 100 cells per growth epoch, loses exactly 140 cells at epoch
90, and finishes with 17,896 occupied cells. Policy and material-growth random
streams are separate in the adaptive arm.

The following contrasts use seed as the paired unit. Intervals are percentile
95% bootstrap intervals from 50,000 paired-seed resamples with seed 319.

## Ensemble service

| Endpoint | Adaptive | Fixed cycle | Current only | Adaptive / fixed | Adaptive / current |
|---|---:|---:|---:|---:|---:|
| Worst delivery, all epochs | 0.0001291 | 0.0001291 | 0.0001291 | 1.00× | 1.00× |
| Mean delivery | 0.07046 | 0.01771 | 0.007581 | **3.98×** | **9.29×** |
| Mean post-damage delivery | 0.13973 | 0.03483 | 0.01469 | **4.01×** | **9.51×** |
| Mean final delivery | 0.36220 | 0.24238 | 0.12155 | **1.49×** | **2.98×** |
| Mean post-damage minimum | 0.0007421 | 0.0006829 | 0.0006514 | 1.09× | **1.14×** |
| Connected-service fraction | **14.43%** | 5.80% | 2.56% | **2.49×** | **5.65×** |
| Post-damage connected fraction | **28.71%** | 11.54% | 5.08% | **2.49×** | **5.65×** |

Adaptive mean delivery exceeded fixed cycle by `0.05275` (95% interval
`[0.03985, 0.06520]`) and current only by `0.06288`
(`[0.04841, 0.07736]`); all eight paired seeds were positive in both
comparisons. Post-damage mean delivery was also positive in all eight seeds:
adaptive minus fixed `0.10490` (`[0.07924, 0.12966]`) and adaptive minus
current `0.12504` (`[0.09628, 0.15382]`).

The common worst value occurs at the shared initial condition. It confirms a
matched starting service floor and motivates a post-warmup or block-level
minimum for the next developmental objective.

## Sink-specific service

| Active sink | Arm | Mean delivery | Connected fraction | Mean peak current / delivery |
|---:|---|---:|---:|---:|
| 0 | Adaptive | 0.003339 | 2.29% | 11.393 |
| 0 | Fixed cycle | **0.007211** | **2.50%** | 9.092 |
| 0 | Current only | 0.000793 | 0% | **8.657** |
| 1 | Adaptive | **0.151553** | **29.10%** | 7.213 |
| 1 | Fixed cycle | 0.044628 | 14.75% | 6.391 |
| 1 | Current only | 0.020923 | 7.58% | **5.419** |
| 2 | Adaptive | **0.055133** | **11.67%** | 8.439 |
| 2 | Fixed cycle | 0.000841 | 0% | 6.580 |
| 2 | Current only | 0.000803 | 0% | **5.878** |

Adaptive achieved `3.40×` fixed and `7.24×` current-only delivery at sink 1.
At sink 2 it achieved `65.6×` fixed and `68.6×` current-only delivery, with
occupied-cell connection in three of eight seed trajectories while both
controls remained at zero connected fraction. Fixed cycling retained the
strongest sink-0 delivery. The three-sink profile therefore reveals productive
specialization rather than a uniform shift.

## Concentration tradeoff

Mean peak current per delivered current was 9.005 adaptive, 7.349 fixed, and
6.645 current-only. Adaptive's delivery gain carried a mean concentration
increase of 22.5% versus fixed and 35.5% versus current-only. At the ensemble
maximum, adaptive averaged 35.235 versus 35.436 fixed and 38.108 current-only,
so its much larger delivery coexisted with the lowest mean worst-case maximum
of the three arms. Sink 0 supplied the clearest concentration cost; sink 1 and
2 supplied the clearest service gains.

This is a measurable Pareto result: adaptive recruitment increases service and
connection across moving demand while concentration remains an active objective
rather than an incidental metric.

## Damage and recovery

The lesion is exactly matched: 140 current-ranked cells removed at epoch 90 in
every arm and seed. During the damaged sink-0 block (`90–104`):

| Measure | Adaptive | Fixed cycle | Current only |
|---|---:|---:|---:|
| Mean delivery | **0.0007807** | 0.0007124 | 0.0006782 |
| Delivery at epoch 104 | **0.0008286** | 0.0007354 | 0.0006916 |
| Epoch-104 / epoch-90 delivery | **0.9478** | 0.8965 | 0.8753 |
| Occupied-cell connected fraction | 0% | 0% | 0% |

Adaptive improved its within-block delivery ratio over fixed by `0.05136`
(`[0.01436, 0.08843]`) and over current-only by `0.07255`
(`[0.03880, 0.10826]`). The adaptive-current contrast was positive in all
eight seeds. Medium conduction continued to provide measurable service while
occupied-cell source-to-sink reconnection remained the next developmental
target.

Every arm records recovery at epoch 105, exactly when demand changes from the
damaged sink 0 to sink 2. That shared threshold crossing identifies the
recovery endpoint's sensitivity to demand state and gives the next control a
precise purpose.

## Smallest next objective and control

Use a **demand-conditioned minimax service objective** and a single matched
damage twin:

1. At each epoch, solve all three sinks on the present body and define
   `service_s = delivery_s / predeclared_reference_s` with the existing
   concentration term retained.
2. Optimize the minimum of the three sink services after a short warmup. This
   directly rewards sink-0 preservation while retaining the demonstrated sink-1
   and sink-2 gains.
3. At epoch 90, clone each body and growth RNG into damaged and undamaged twins,
   hold sink-0 demand through epoch 120, and apply identical subsequent actions
   and material additions.
4. Score recovery as damaged/undamaged sink-0 delivery, occupied-cell
   reconnection, concentration, and area under service through epoch 120.
5. Retain fixed cycle and current only, and add the smallest informative policy
   control: a demand-matched fixed action that selects the actuator associated
   with the active sink under the same energy and material budget.

This next screen preserves the present adaptive advantage, studies its sink
specialization, and turns repair into a matched causal contrast with a stable
demand target.
