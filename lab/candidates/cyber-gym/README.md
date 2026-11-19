# Offline cyber-gym benchmark candidate

This candidate uses **NASim 0.12.0** at official repository commit
`4f26de37cfdc3e4553ed8b7484c4db8e2924bdea`. It is a fully synthetic,
local Gymnasium environment. The benchmark never opens a socket, scans a
host, reads a credential, executes a payload, or names an external target.
Every policy action is a discrete integer passed to `env.step()`.

The completed compact neural-Q extension, contingency reversal, exact update
accounting, and rolling Q-value surface are documented in
[`NEURAL_PHASE.md`](NEURAL_PHASE.md). Its retained artifacts are under
`results/neural-pilot/`.

## Why NASim

NASim is the smallest maintained purpose-built option that runs natively on
this Apple-silicon Studio. Its official repository supplies pure-Python
Gymnasium code, YAML scenarios, partial observation, probabilistic transitions,
and tabular-Q examples. A candidate-local arm64 smoke test succeeded under
Python 3.12.14.

The alternatives remain useful at larger scale:

- CybORG/CAGE 4 models blue, red, and green agents and service impact more
  directly, but its official requirements pull Ray/RLlib, PyTorch,
  PyTorch-Geometric, PettingZoo, pygame, and other components. That is a much
  larger installation than this first falsifiable benchmark needs.
- CyberBattleSim is actively maintained, but its official setup recommends
  Linux or WSL. It is therefore a poorer native-Studio fit for this bounded
  first run.

The official-source comparison and exact source snapshots are in
[`SOURCES.md`](SOURCES.md).

## Frozen experiment

- `scenarios/train-chain.yaml`: Internet -> public -> transit -> target,
  exploit probability 0.8.
- `scenarios/heldout-branch.yaml`: the public subnet branches to transit and
  target, exploit probability 0.6.
- Both scenarios have the same 18-action and 56-element observation spaces,
  a 24-step cap, immutable toy services, and no real addresses.
- Policies: deterministic fixed rule, independently seeded uniform random,
  and classical tabular Q-learning.
- The Q state is cumulative successful action-kind/target tuples observed in
  prior Gym step results. It does not read hidden simulator state.
- Base seed: 319. The benchmark seeds Python, NumPy's module RNG, the Gym action
  space, and each policy RNG because NASim 0.12.0 uses NumPy's module RNG for
  probabilistic actions.

The final pilot trained Q-values for 600 episodes and evaluated each policy for
16 matched-seed episodes on each topology. It retained all 13,963 training
steps and 1,774 evaluation steps.

## Install location and exact commands

The source checkout and virtual environment are deliberately ignored and live
only inside this candidate:

- `.vendor/NetworkAttackSimulator`
- `.venv`

Commands used:

```sh
cd /Users/tmccoy678/Blu-Workbench/tin-whiskers-dendrites-ai-si/lab/candidates/cyber-gym
git clone --filter=blob:none --no-checkout https://github.com/Jjschwartz/NetworkAttackSimulator.git .vendor/NetworkAttackSimulator
git -C .vendor/NetworkAttackSimulator checkout --detach 4f26de37cfdc3e4553ed8b7484c4db8e2924bdea
/opt/homebrew/bin/uv venv --python /Users/tmccoy678/.local/bin/python3.12 .venv
/opt/homebrew/bin/uv pip install --python .venv/bin/python ./.vendor/NetworkAttackSimulator
```

`requirements.lock` records the resolved package versions and the pinned
official Git source. The environment was not installed globally.

## Test and reproduce

The bounded tests perform no network activity:

```sh
cd /Users/tmccoy678/Blu-Workbench/tin-whiskers-dendrites-ai-si/lab/candidates/cyber-gym
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v
```

The exact pilot command was:

```sh
.venv/bin/python benchmark.py --seed 319 --train-episodes 600 --eval-episodes 16 --output results/pilot
gzip -9 results/pilot/steps.jsonl
```

`benchmark.py` refuses to overwrite an existing output directory. Use a new
path such as `results/pilot-rerun` for a reproduction.

## Pilot result

| Scenario | Policy | Success | Mean steps | Mean reward | Env queries | Q-value queries | Safe service |
|---|---:|---:|---:|---:|---:|---:|---:|
| train chain | fixed rule | 16/16 | 15.7500 | 49.2500 | 252 | 0 | 1.0000 |
| train chain | seeded random | 0/16 | 24.0000 | -22.4375 | 384 | 0 | 1.0000 |
| train chain | tabular Q | 16/16 | 13.6250 | 51.3750 | 218 | 3,924 | 1.0000 |
| held-out branch | fixed rule | 16/16 | 17.7500 | 47.2500 | 284 | 0 | 1.0000 |
| held-out branch | seeded random | 1/16 | 23.6875 | -19.9375 | 379 | 0 | 1.0000 |
| held-out branch | tabular Q | 16/16 | 16.0625 | 48.9375 | 257 | 4,626 | 1.0000 |

The learned policy finished above both baselines on mean steps and mean reward
in the training topology. It also finished above both on the held-out branch.
The Q training history itself was mixed: 55 of 600 exploratory episodes reached
the goal, its mean training reward was -7.755, and 545 failures remain in the
record. The result establishes this small seeded policy comparison; it does not
establish security capability outside the frozen simulator.

All service-safety values are exactly 1.0 by construction. NASim 0.12.0 has no
service-disable transition or availability state, so this benchmark can prove
that its configured toy services were never mutated; it cannot measure
defensive uptime under a service-impacting adversary. CybORG is the stronger
next environment if that becomes the primary question.

## Accounting and artifacts

Definitions are frozen in `results/pilot/manifest.json`:

- one environment query = one `env.step(action_index)` call;
- one Q-value query = one table cell inspected during greedy selection or
  bootstrap maximization; random exploration inspects zero Q-values;
- compute = integer `process_time_ns` and `perf_counter_ns`, recorded per step
  and per episode;
- reward = the exact float returned by NASim plus cumulative episode reward;
- safe service = fraction of configured services not disabled, exactly 1.0 in
  this immutable-service environment.

Artifacts:

- `results/pilot/manifest.json`: versions, seeds, hashes, definitions.
- `results/pilot/summary.json`: aggregate metrics including CPU/wall nanoseconds.
- `results/pilot/episodes.jsonl`: exact episode totals.
- `results/pilot/steps.jsonl.gz`: all 15,737 exact step records.
- `results/pilot/q_table.json`: final classical Q table.
- `results/pilot-*/`: preserved earlier unfavorable runs; see
  [`results/FAILURES.md`](results/FAILURES.md).

Scenario SHA-256 values in the final pilot are:

- train chain: `3d06ca0514e3a315049298411e8463e1f96843d54414fdc9b4fff0b7c61eabd6`
- held-out branch: `930b2745b64312f77781d682795bec073f7853217da1971f52aec5580e11ef44`

## Known environment defect

At the pinned NASim commit, the optional `get_action_mask()` helper calls a
removed `Network.host_discovered` method. The core Gym reset/step/action-space
API works on arm64. This benchmark leaves the vendor source untouched and uses
the complete discrete action space, which also prevents a hidden-discovery
mask from leaking information into the partially observed learner.

## Quantum comparator decision

No Grover comparator was added. The frozen NASim problem has structured,
labeled actions, stochastic transitions, and potentially several useful
actions. It does not expose a unique marked item behind an opaque Boolean
oracle. Wrapping simulator lookahead in a phase oracle would manufacture the
assumption that creates Grover's query advantage. The full decision and the
requirements for a future valid comparator are in
[`GROVER_DECISION.md`](GROVER_DECISION.md).
