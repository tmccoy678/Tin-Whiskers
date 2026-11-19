# Adaptive engine speedtest — same Studio

## Configuration

- Host: Apple M5 Max Mac Studio, 18 CPU cores, 36 GB unified memory.
- Engine: release-build `long-run-adaptive-screen`, one process, one busy core,
  nice level 15.
- Workload: 120 actions × 120 substrate seeds × 120 Earth/space environment
  draws = 1,728,000 audited adaptive choices.
- Native body: `16 × 8` cells with five persistent fields—conductance,
  electrical-field proxy, mobile concentration, local material reservoir, and
  heat.

## Two complete independent seeds

| Master seed | Choices | Engine time | Choices/s | Audit bytes | Audit MB/s |
|---:|---:|---:|---:|---:|---:|
| 319 | 1,728,000 | 177.069158 s | 9,758.899 | 4,291,511,684 | 24.236 |
| 571 | 1,728,000 | 177.459749 s | 9,737.419 | 4,291,539,148 | 24.183 |

Mean throughput was **9,748.159 choices/s**. The two-seed range was 21.479
choices/s, or **0.220% of the mean**; sample coefficient of variation was
**0.156%**. That repeatability is the first strong speed result.

## Work carried by one choice

Each counted choice completes one controller–substrate–audit cycle:

1. solve/update the 128-cell local electrical-field proxy;
2. evaluate one or two field-weighted growth candidate scans;
3. choose one bounded upper/lower action with propensity and renewal state;
4. update concentration and heat across all 128 cells;
5. deduct any deposition from finite local and global material reservoirs;
6. calculate delivery, concentration, heat, stress, material, and safe-service
   consequences;
7. update the adaptive controller and conserved reinforcement ledger; and
8. append one canonical JSON audit record with hashes and causal metadata.

The direct field-update core writes 384 persistent scalar field values per
choice: 128 electrical-field values, 128 concentration values, and 128 heat
values. Selected-site conductance and reservoir changes add further local
writes. The finite reinforcement path produced an average of 176.13 and 176.05
candidate-cell evaluations per choice in seeds 319 and 571.

## Derived same-core throughput

| Measure | Seed 319 | Seed 571 |
|---|---:|---:|
| Native 128-cell sweeps/s | 1,249,139 | 1,246,390 |
| Persistent scalar field writes/s | 3,747,417 | 3,739,169 |
| Candidate-cell evaluations/s | 1,718,798 | 1,714,260 |
| Canonical audit bytes/choice | 2,483.514 | 2,483.530 |
| Canonical JSON audit throughput | 24.236 MB/s | 24.183 MB/s |

Each full run therefore carried **221,184,000 native cell positions** through
each whole-grid pass, performed **663,552,000 primary persistent field
writes**, evaluated about **304 million growth candidates**, and preserved 1.728
million complete choice records in approximately three minutes.

## Positive study ladder

The same-host Stockfish speedtest supplies a raw nodes/s reference. The
adaptive engine adds an orthogonal work-density result: every event advances a
five-field body, a consequence-sensitive policy, a finite material account, a
renewal mechanism, and a 2.48 KB causal record. Both rates can be presented
side by side with their counted units intact.

The next focused speed studies are:

1. matched full-audit and compact-audit runs to measure how much of the current
   24.2 MB/s path belongs to durable evidence;
2. `16 × 8`, `32 × 16`, and `64 × 32` grids to measure scaling in choices/s,
   cell-field updates/s, and useful-service improvement per second; and
3. one-core and all-core independent-body batches to test whether the observed
   0.22% two-seed stability persists as parallel throughput rises.

Every positive increment in throughput, scaling efficiency, work density,
repeatability, or adaptive outcome becomes the next measured branch.
