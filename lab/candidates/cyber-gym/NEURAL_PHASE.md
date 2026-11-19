# Compact neural-Q phase

This bounded extension compares the fixed rule, tabular Q-values, and a small
transparent NumPy DQN on the same frozen NASim train and held-out scenarios. It
adds one synthetic contingency reversal without changing the vendor package or
touching any network.

## Architecture

The neural approximator has 3,026 trainable parameters:

- input: 75 values — 56 partially observed NASim values, 18 cumulative
  successful intended-action bits, and one observable episode-step fraction;
- hidden layer: 32 ReLU units;
- output: 18 classical action Q-values;
- optimizer: NumPy Adam, learning rate 0.001, global gradient-norm cap 10;
- reward scale: raw NASim reward divided by 50 for neural updates;
- replay: capacity 4,096, batch 32, warmup 256 transitions;
- stability: hard target-network synchronization every 120 optimizer updates;
- seed: base 319, with an isolated neural generator seeded at 392.

No PyTorch, TensorFlow, account, accelerator service, or new dependency was
needed. All weights and optimizer operations are visible in
`neural_benchmark.py`.

Training used 600 episodes per learned policy. The neural learner performed
12,238 optimizer updates, sampled 391,616 replay transitions, and synchronized
the target network 101 times. Its exact training compute was 1,435,953,000
process nanoseconds and 1,437,111,204 wall nanoseconds in this run.

## Frozen reversal

[`scenarios/reversal-deception.json`](scenarios/reversal-deception.json) wraps
the unchanged held-out branch. After the policy observes a successful
privilege escalation on toy host `(2, 0)`, intended `Exploit` and `ProcessScan`
actions on toy host `(3, 0)` swap meanings. The reversal flag and effective
mapping never enter policy observations, beliefs, or neural features. Policies
receive only the ordinary NASim observation, reward, and action-result fields.

The audit separately records intended and effective actions for falsification.
Every effective action remains one discrete `env.step()` call against NASim;
there are no sockets, hosts, credentials, scans, or payloads outside the gym.

Two reversal conditions are retained:

- zero-shot: frozen policies, epsilon 0, no updates;
- adaptive: epsilon 0.15 and online updates carried across 16 reversal
  episodes. The adaptive neural copy starts from the trained weights with a
  fresh 512-transition replay buffer, batch 8, warmup 8, and target sync every
  16 updates.

## Result

Each evaluation condition contains 16 matched-seed episodes.

| Phase | Scenario | Policy | Success | Mean steps | Mean reward | Env queries | Q-value queries |
|---|---|---:|---:|---:|---:|---:|---:|
| zero-shot | train chain | fixed rule | 16/16 | 15.8125 | 49.1875 | 253 | 0 |
| zero-shot | train chain | tabular Q | 16/16 | 13.5625 | 51.4375 | 217 | 3,906 |
| zero-shot | train chain | neural Q | 16/16 | 10.9375 | 53.7500 | 175 | 3,150 |
| zero-shot | held-out branch | fixed rule | 16/16 | 16.8125 | 48.1875 | 269 | 0 |
| zero-shot | held-out branch | tabular Q | 16/16 | 14.3750 | 50.6250 | 230 | 4,140 |
| zero-shot | held-out branch | neural Q | 16/16 | 12.3125 | 52.6875 | 197 | 3,546 |
| zero-shot | reversal | fixed rule | 0/16 | 24.0000 | -9.0000 | 384 | 0 |
| zero-shot | reversal | tabular Q | 0/16 | 24.0000 | -9.0000 | 384 | 6,912 |
| zero-shot | reversal | neural Q | 0/16 | 24.0000 | -9.3125 | 384 | 6,912 |
| adaptive | reversal | fixed rule | 0/16 | 24.0000 | -9.0000 | 384 | 0 |
| adaptive | reversal | tabular Q | 0/16 | 24.0000 | -10.8750 | 384 | 13,536 |
| adaptive | reversal | neural Q | 5/16 | 22.6250 | -0.7500 | 362 | 108,756 |

The neural policy produced the strongest base and held-out result: 16/16 on
both, with fewer steps and higher reward than the fixed and tabular policies.
The reversal establishes a sharper boundary. Every frozen policy failed all 16
zero-shot episodes. With bounded online renewal, neural Q succeeded in episodes
6, 7, 8, 12, and 13; episodes 14 and 15 failed, so this is partial, intermittent
adaptation rather than stable reversal mastery. Fixed and tabular policies
remained at 0/16.

Training outcomes remain equally visible. Neural Q succeeded in 228/600
exploratory episodes with mean reward 8.145; tabular Q succeeded in 55/600 with
mean reward -7.755. All 917 unsuccessful training episodes remain in the exact
record.

Safe service is 1.0 throughout because this NASim version has immutable service
availability. The result demonstrates software policy performance inside these
frozen toy dynamics only.

## Exact records and visual surface

- [`results/neural-pilot/manifest.json`](results/neural-pilot/manifest.json):
  architecture, seeds, scenario hashes, query definitions, replay, and target
  sync settings.
- [`results/neural-pilot/summary.json`](results/neural-pilot/summary.json): all
  aggregate reward, success, step, query, update, replay, target-sync, and
  process/wall compute metrics.
- `results/neural-pilot/episodes.jsonl.gz`: 1,392 exact episode records.
- `results/neural-pilot/steps.jsonl.gz`: 30,079 exact per-step records,
  including all 18 pre-action Q-values, chosen value, replay/update counts,
  losses, observation/feature hashes, intended/effective reversal actions,
  rewards, and compute nanoseconds.
- `results/neural-pilot/neural_q_model.npz`: frozen online and target weights.
- `results/neural-pilot/tabular_q_table.json`: matched tabular learner.
- [`results/neural-pilot/surface/q_lattice.tsv`](results/neural-pilot/surface/q_lattice.tsv):
  full evaluation surface for the visual bench.
- [`results/neural-pilot/surface/q_lattice.html`](results/neural-pilot/surface/q_lattice.html):
  self-contained episode-0 heat lattice; no app was opened.

The surface labels classical Q-values explicitly. Tabular values use raw reward
units, while neural values use reward divided by 50; their ranks are meaningful
within a policy, while their magnitudes are not directly comparable across the
two value scales.

## Exact commands

```sh
cd /Users/tmccoy678/Blu-Workbench/tin-whiskers-dendrites-ai-si/lab/candidates/cyber-gym
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python neural_benchmark.py --seed 319 --train-episodes 600 --eval-episodes 16 --output results/neural-pilot
```

`neural_benchmark.py` refuses to overwrite an existing result directory. Use a
new path for a reproduction.
