# Progressive targeted ablation

At each epoch, the shortest surviving source-to-sink path was identified and a seven-by-seven-pixel lesion was centered on that path. MOOSE then recomputed terminal flux.

| Topology | First disconnecting lesion | Initial flux | Flux after first lesion |
|---|---:|---:|---:|
| Straight wire | 1 | 0.015862 | 2.94167e-06 |
| Parallel grid | 5 | 0.079305 | 0.0634463 |
| Recurrently developed topology | 1 | 0.004095 | 1.66394e-05 |

The developed topology retained 99.975% of flux under the recurrent local lesion, yet disconnected under the first lesion aimed at its current shortest path. Its adaptation was location-specific. The parallel grid generalized across four targeted rail failures and disconnected on the fifth.
