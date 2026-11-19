# Long-run adaptive screen

This isolated candidate is a fast, deterministic, single-process reduced
mechanism for the exact full screen:

```text
120 actions × 120 substrate seeds × 120 admitted environment draws
= 1,728,000 adaptive choices
```

Every output is labeled **screening-only**. The program does not control
hardware, prepare chemistry, execute radiation or vacuum work, modify a
canonical simulation, or support a material-performance, reliability,
mission-qualification, intelligence, or autopoiesis claim.

## Mechanism and controller

The substrate is an explicit `16 × 8` field with continuous local state for
conductance, electric-field proxy, mobile concentration, finite local material
reservoir, and heat. Each action performs local field-weighted growth or
remodeling, deducts the deposited amount from both local and global material
inventories, diffuses concentration, and updates delivery, current
concentration, heat, and mechanical-gradient proxies. Nothing grows after the
finite reservoir is exhausted.

Each deterministic environment contains one concealed change at epoch 48–72:
channel-consequence swap, upper-channel degradation, upper-channel heat
coupling, or a mass-conserving reservoir shift. The controller sees only the
resulting observations. The program depends directly on the tested
`../adaptive-controller` crate and retains its strict observation/hash chain,
action propensity, safety checks, prediction residual, and balanced renewal
audit in every choice record.

The 120 environment draws alternate Earth PEDOT `exploratory` and space CBRAM
`screening` regimes. They are sampled only from the source manifests and
allow-listed policy axes. Each draw records its seed, source SHA-256 hashes,
proposed range, admitted option selections, static rejections, and all
`required-unset` blockers. Earth and space parameters are never imported into
one another. Exact source bytes are frozen into each output directory.

## Finite reinforcement pulse

The “nutrient credit” is a conserved, dimensionless reinforcement/scheduling
credit. It is not sugar, chemistry, energy, or matter.

- A positive change in safe useful service may earn one credit from a fixed
  run-global reservoir.
- The reservoir is preallocated equally: 60 credits per 120-action trajectory,
  or 864,000 credits in the full 14,400-trajectory run. This prevents earlier
  trajectories from consuming later trajectories' share.
- A spent credit lets the next action consider a second local candidate and
  select the stronger of the two. It still performs at most one deposition.
- Every action is charged exactly one optical-energy proxy unit and `0.5`
  electrical-energy proxy unit whether or not a credit is spent. Every actual
  material increment is deducted once from the finite material reservoir.
- Every record contains earned, spent, account, global earned/spent/
  outstanding/remaining, and both conservation checks.

The exact integer invariants are:

```text
initial = remaining + spent + outstanding
earned  = spent + outstanding
```

The 60-credit quota is the smallest round quota supported by the smoke data
that remained available after the concealed epoch-62 change without rewarding
every beneficial action. In the final 120×3 smoke, each trajectory reached its
quota at epoch 89–93 and still earned 21–27 post-change credits.

## Durable outputs

The candidate keeps source under version control and ignores `output/`,
`runtime/`, and Cargo `target/` artifacts.

- `output/full/choices.jsonl` — one complete observation/action/controller/
  renewal/physics/pulse audit per choice.
- `output/full/environment-draws.jsonl` — 120 frozen seeded draws.
- `output/full/frozen-manifests/` — byte-exact source manifests and policy.
- `output/full/run-manifest.json` — configuration, source hashes, and blockers.
- `output/full/summary.json` — progress/final quantiles and pulse proof.
- `output/full/status.json` — atomic machine-readable progress overwrite.
- `output/full/intel-status.txt` — atomic, glanceable Intel display overwrite.
- `runtime/full/checkpoint.json` — atomic resume state and safe audit byte
  boundary.

Checkpoints occur every 120 completed trajectories by default and immediately
after the current short trajectory when `SIGTERM` is observed. Resume truncates
the append-only audit to the last checkpoint byte boundary before continuing,
so an interrupted uncheckpointed suffix cannot create duplicate choices.

## Verification and measured estimate

Focused unit tests:

```sh
cd /Users/tmccoy678/Blu-Workbench/tin-whiskers-dendrites-ai-si/lab/candidates/long-run-adaptive-screen
cargo test
```

Result: **5 passed, 0 failed**. The tests cover the exact full choice count,
both pulse equalities, deterministic draws and all eight space blockers,
deterministic substrate state, and controller/hash/pulse integration.

Final smoke command:

```sh
./target/release/long-run-adaptive-screen run \
  --output output/smoke-120x3-scarce \
  --runtime runtime/smoke-120x3-scarce \
  --actions 120 --substrates 3 --environments 1 \
  --seed 319 --checkpoint-every 1 \
  --pulse-credits-per-trajectory 60 --nice 15
```

The Studio smoke completed 360/360 choices in `0.23 s` wall time
(`0.167132 s` recorded engine time), wrote 360 audit records totaling exactly
`885,255 bytes`, produced 9 renewal triggers and 32 renewal actions, and used no
dark/fail-closed action. It earned and spent exactly 180 credits: 50.0% earn
frequency and 50.0% spend frequency. The fixed reservoir was exhausted, so it
was meaningfully finite rather than a nonbinding ceiling. Optical charge was
exactly 120 units per trajectory; maximum finite-reservoir material use was
`0.3037855194224055` proxy units.

Linear projection from that exact smoke measurement gives:

- audit log: `885,255 × 4,800 = 4,249,224,000 bytes`
  (`4.249224 GB`, `3.9574 GiB`);
- checkpoint, frozen inputs, draws, summaries, and status: approximately
  `9 MB` additional;
- total disk: approximately **4.26 GB**;
- conservative wall runtime: `0.23 × 4,800 = 1,104 s`, or **18 min 24 s**;
- engine-time projection: `0.167132 × 4,800 = 802.2336 s`, or **13 min 22 s**.

Those runtime estimates are Studio-arm64 measurements at nice level 15. The
default full run checkpoints 120 times rather than once per trajectory, so the
wall estimate is intentionally conservative. Re-benchmark the same smoke on a
different CPU before using the estimate there.

A separate disposable 4,800-choice interruption check stopped after a real
`SIGTERM` at 480 choices, wrote a resumable atomic checkpoint, then completed
after one `--resume`. Its final audit contained exactly 4,800 unique consecutive
choice indices (`0..4799`) with no missing or duplicate record, and pulse
conservation remained true.

The complete 120 × 120 × 120 result and audit hashes are recorded in
[`FULL_RUN_2026-11-19.md`](FULL_RUN_2026-11-19.md). The full run completed
1,728,000 choices in `177.069158 s`; its 4.29 GB choice audit remains in the
ignored local output directory.

## Exact conductance-map replay

The optional `--visual-samples N` path retains the native `16 × 8`
conductance state after every choice for substrate zero in the first `N`
environments. It changes observation only: the controller, actions, substrate
mechanics, energy, material, and audit remain the same. A seed-571 replay of all
120 environments produced 121 exact states per lineage; all 120 replayed final
metrics and action totals matched the corresponding full-run trajectories.

`render-lineages.swift` selects one Earth and one space lineage for each of the
four concealed-change types and writes an eight-panel H.264 movie. Each movie
frame is one recorded state, each colored rectangle is one native conductance
cell, and geometry uses nearest-neighbor rendering without interpolation.
Seed-571 visual-state SHA-256:
`86c5ea7aaf66a1afb2cb99fe3658538ec0ba39a231281042e0be4cc95490955e`.
Rendered MP4 SHA-256:
`52b38424fa7ae329a2286d072b1bddbc8a4fa1dc1cc94e6b7c0ef5cf1f03d944`.

## Exact full-run commands

Build once:

```sh
cd /Users/tmccoy678/Blu-Workbench/tin-whiskers-dendrites-ai-si/lab/candidates/long-run-adaptive-screen
cargo build --release
```

Low-priority detached launch through a transient user `launchctl` job. Its
wrapper removes the job after completion or failure so launchd never
reschedules the finished command:

```sh
./launch-full.zsh new
```

Resume after a graceful stop or interruption, using the identical scientific
configuration:

```sh
./launch-full.zsh resume
```

Machine-readable status and Intel glance surface:

```sh
./target/release/long-run-adaptive-screen status --runtime runtime/full
cat output/full/intel-status.txt
```

Graceful stop at the next completed trajectory:

```sh
label="$(cat runtime/full/launchd-label)"
kill -TERM "$(launchctl print "gui/$UID/$label" | awk '/pid =/{print $3; exit}')"
```
