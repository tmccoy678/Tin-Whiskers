# Recurrent-transection horizon

One deterministic seed was observed at successively longer horizons under the
same rules and a guaranteed full transection at every epoch.

| Observation horizon | Median repair steps, first 10% | Median repair steps, final 10% | Final metal cells | Repair failures |
|---:|---:|---:|---:|---:|
| 60 | 15.5 | 18 | 2,531 | 0 |
| 600 | 18 | 13 | 2,667 | 0 |
| 6,000 | 14 | 14 | 2,956 | 0 |

Across the extended horizon, the median repair cost is 14 steps in every
600-epoch block. Median material rises early and approaches approximately 2,945
cells; the final block ranges from 2,929 to 2,974. The system reaches a bounded
maintained regime under these conditions rather than unlimited accumulation or
eventual disconnection.

The block-level raw summary is
[`recurrent-extended-blocks.tsv`](recurrent-extended-blocks.tsv). The complete
per-epoch trajectory remains an ignored working output because it can be
reproduced exactly from the committed seed and parameters.
