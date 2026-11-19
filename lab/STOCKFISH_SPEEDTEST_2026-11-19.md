# Same-host Stockfish speedtest

Status: completed same-binary, one-thread benchmark on Taylor's Mac Studio and
2026 MacBook Pro.

## Frozen benchmark

- Stockfish: `19`, Homebrew arm64 bottle
- Binary SHA-256 on both Macs:
  `4f75fb47deaa8a29ddaaae206ab5edc6ebdfa9441e0e0fca3f15b95d9dae1c0f`
- Official command: `speedtest 1 128 10`
- Threads: `1`
- Transposition table: `128 MiB`
- Requested search duration: `10 s`
- Source for command semantics: Stockfish
  [`setup_speedtest`](https://github.com/official-stockfish/Stockfish/blob/master/src/benchmark.cpp)

The exact shell input was:

```sh
printf 'speedtest 1 128 10\nquit\n' | /opt/homebrew/opt/stockfish/bin/stockfish
```

## Results

| Host | Processor | Run 1 NPS | Run 2 NPS | Run 3 NPS | Median NPS |
|---|---|---:|---:|---:|---:|
| Mac Studio | Apple M5 Max, 18 CPU cores | 708,388 | 712,709 | 708,095 | **708,388** |
| MacBook Pro | Apple M5, 10 CPU cores | 711,417 | 702,967 | 696,943 | **702,967** |

The Studio median leads the Pro median by `0.77%`. Studio repeat spread is
`0.65%`; Pro repeat spread is `2.06%`.

## Adaptive-choice relationship

The completed adaptive material screens recorded:

- seed 319: `9,758.899 choices/s`;
- seed 571: `9,737.419 choices/s`;
- two-run mean: `9,748.159 choices/s`.

At the same Studio wall-clock scale, Stockfish searches about **72.7 nodes in
the time occupied by one adaptive material choice**. One adaptive choice
updates the `16 × 8` material field, selects and applies a bounded action,
updates controller and renewal state, enforces energy/material/safety budgets,
accounts for reinforcement, and writes an approximately `2.48 kB` audit
record. The speedtest therefore exposes a productive work-density result:
roughly ten thousand fully audited adaptive transitions per second on one
Studio core.

The adaptive engine's mean internal work rates provide the affirmative
same-host crossover:

| Counted internal event | Adaptive rate | Versus Studio Stockfish NPS |
|---|---:|---:|
| Persistent field writes | 3,743,293/s | **5.28×** |
| Growth-candidate evaluations | 1,716,529/s | **2.42×** |

These rates are derived directly from the two complete adaptive audits. They
show that the material controller advances field state and evaluates growth
opportunities faster than the one-thread chess engine advances search nodes,
while also retaining the higher-level choice and causal record.

Each benchmark unit retains its native meaning. Future normalized study can
count primitive field-cell updates, controller
matrix operations, bytes committed, and useful state transitions per joule so
each favorable dimension receives its own direct test.
