# Current-driven remodeling

The six-transection topology underwent 24 alternating epochs:

1. MOOSE solved voltage, current-density proxy, and Joule density.
2. The reduced morphology widened locally beside persistently high-current
   cells.
3. The changed topology returned to MOOSE.

No target graph, branch count, or final thickness was supplied.

| Measure | Epoch 0 | Epoch 24 | Change |
|---|---:|---:|---:|
| Metal fraction | 0.088569 | 0.126953 | 1.43× |
| Terminal flux at ΔV = 1 | 0.004335 | 0.035823 | 8.26× |
| Peak current density at ΔV = 1 | 1.177017 | 2.722353 | 2.31× |
| Peak current density / terminal flux | 271.488 | 75.995 | −72.01% |

The absolute peak rises at fixed voltage because the remodeled network carries
8.26 times more current. At the original network's delivered current, the
remodeled topology requires 12.1% of the original applied voltage and its
predicted integrated Joule density falls from 0.003632 to 0.000514, an 85.85%
reduction.

The morphology separates into a widened current-bearing backbone and retained
fine branches. Current-dependent widening therefore improves transport faster
than it consumes material and reduces bottleneck stress per delivered current.
It remains below the parallel grid in absolute one-volt flux.

The raw epoch table is [`remodel-metrics.tsv`](remodel-metrics.tsv). The loop is
implemented by [`remodel_flow.py`](remodel_flow.py).
