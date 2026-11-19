# Falsification and statistics bench

## Decision target

The smallest defensible claim is:

> Under equal material, energy, sensing, computation, and cooling budgets, a
> controller using present substrate consequences provides more safe useful
> service on held-out load and damage schedules than its identical yoked action
> replay.

The primary causal contrast is adaptive versus yoked replay. Straight wire,
parallel grid, and two developed fixed-rule arms answer the separate practical
question of whether adaptivity beats conventional or deterministic allocation.
No morphology, movie, or within-arm before/after change substitutes for either
contrast.

## Evidence boundary before a new trial

| ID | Frozen record | Observation | Evidential limit |
|---|---|---|---|
| `F24` | `simulation/voltage-routing/remodel-metrics.tsv`, SHA-256 `d90551339a7de346d7b5bb58b84ae8a23d00e6be3d1cd3042d1b1d426538b0b3` | The canonical 24-epoch current-only fixed rule produced 8.26x initial terminal flux with 1.43x material and 72.01% lower peak current density per delivered current. | One deterministic fixed-rule trajectory. |
| `F36` | `simulation/work/live_moose/current_fiber_remodel/metrics.tsv`, SHA-256 `a89f78fae2fb1ffc65cee5d0c3e7eb229b229035eff26be1c2c8180f9496474a` | The separate 36-epoch alternating two-fiber fixed rule produced **8.43x** initial terminal flux with **1.44x** material and **75.29%** lower peak current density per delivered current. | One deterministic fixed-rule trajectory in an ignored work directory. |
| `B128` | 128 paired reduced-model seeds | Illumination improved bridge time by 53.95 steps, 95% paired-bootstrap CI `[41.06, 66.60]`; the old power estimate was 18 pairs for 80% and 22 for 90%. | A variance pattern for that fixed contrast only. |
| `T64` | Guaranteed transections, 64 seeds | First-to-final repair improved 176.40 steps, CI `[141.40, 209.79]`. | A fixed-rule, practiced damage result. |
| `R64` | Alternate repair schedule, 64 seeds | First-to-final change was -9.16 steps, CI `[-45.43, 26.83]`. | The repair conclusion changes with lesion definition. |
| `ABL` | Unseen shortest-path ablation | The developed topology disconnected at lesion 1; the grid survived four lesions. | Location-specific development is not general fault tolerance. |

`F24` and `F36` are different controls and must never be pooled. Freeze each raw
table, rule, initial image, solver input, and hash before using it as an
ensemble comparator. No adaptive AI result has yet been observed. In
particular, the `F36` 8.43x flux and 75.29% reduction are fixed deterministic
control measurements, not evidence for AI.

The divergent damage results make a concealed, held-out schedule the cheapest
test likely to reverse the apparent advantage.

## One matched block

Every block uses one material/parameter batch, one independent base seed, and
one concealed schedule seed. It contains all six arms. Physical units are
randomly assigned to coded positions. Simulations use counter-based common
random numbers keyed by block, process, and time, so an action cannot shift the
later random-number stream merely by consuming a different number of draws.

| ID | Comparator | Construction and allowed response |
|---|---|---|
| `W` | Fixed wire | Prescribed mass-matched direct conductor; no remodeling. |
| `G` | Fixed grid | Prescribed mass-matched redundant rails; no remodeling. |
| `F24` | Developed current-only fixed rule | Frozen 24-epoch local current-driven mapping; then hold. |
| `F36` | Developed alternating two-fiber fixed rule | Frozen 36-epoch alternating upper/lower probe schedule; then hold. |
| `A` | Adaptive | Frozen controller code may update bounded actions from allowed present observations only. |
| `Y` | Yoked replay | Receives `A`'s timestamped commands in real time; none of its observations affect those commands. |

Give every arm the same 36-epoch development window; `F24` holds its epoch-24
state for the last 12 epochs. `A`, `Y`, and both fixed-rule arms start from the
same seed geometry. `A` and `Y` run simultaneously where possible. The yoke is
valid only if their canonical command streams hash identically and delivered
actuator energy agrees within the preregistered calibration tolerance.

### Budget invariants

For every arm `c` in every block:

\[
M_{built,c}(0)+M_{reservoir,c}(0)=M_0,
\qquad M_{used,c}(t)\leq M_0.
\]

`W` and `G` may allocate all of `M0` at time zero; dynamic arms may reserve
some. There is no refill. All arms have identical pads, chamber volume,
material lot, source compliance, duration, sensor schema, and sampling rate.
They also obey

\[
E_{load}+E_{actuator}+E_{sensor}+E_{compute}\leq E_0,
\quad P_{cool}\leq P_0,
\quad T_{bath}=T_0\pm\epsilon_T.
\]

Unused budget is not reassigned. Log actual component energies; control or
optical energy is never free. Match chamber thermal conductance, coolant flow,
and ambient set point. `A` and `Y` additionally receive identical actuator
energy by construction.

## Concealed evaluation schedule

Freeze controller artifacts and calibration limits first. An independent
runner then generates and locally commits the schedule hash. The controller,
device operator, image scorer, and analyst receive only coded identifiers and
the information their roles require.

The shortest useful evaluation contains these held-out episodes, with order
balanced among blocks:

| Episode | Intervention | Matching rule |
|---:|---|---|
| 0 | Undamaged service | Same terminal/load history in every arm. |
| 1 | Unseen load magnitude or terminal pair | Same demand and compliance envelope; future transition hidden. |
| 2 | Exogenous lesion | Same preregistered physical mask and removed volume. |
| 3 | Source/sink reversal | Same reversal time and demand; no controller reset. |
| 4 | Bottleneck lesion | A frozen algorithm selects the highest-current connected patch separately in each arm; lesion volume is equal and the algorithm hash is shared. |

No evaluation lesion location appears during controller development. Reveal an
event only when it occurs. A schedule is invalid if an arm label, future load,
lesion mask, schedule seed, port identity, global route coordinate, or
simulator-only state reaches `A`, `F24`, `F36`, or `Y` through an allowed
observation.

Use at least four independently prepared material/parameter batches and at
least three complete blocks per batch (`n0 = 12` blocks). A time series is not
an independent replicate. Give every simulation block a unique microstate
seed; physical dishes from one preparation remain one material batch.

## Primary endpoint

Materials calibration must set absolute limits `J_lim`, `T_lim`, `S_lim`,
`M0`, and `E0` before labels are unblinded. At sample `k`, define safe useful
service

\[
q_{ik}=\min\!\left(1,{I_{del,ik}\over I_{req,ik}}\right)
\mathbf 1[J_{max,ik}\leq J_{lim}]
\mathbf 1[T_{max,ik}\leq T_{lim}]
\mathbf 1[S_{max,ik}\leq S_{lim}]
\mathbf 1[M_{used,ik}\leq M_0]
\mathbf 1[E_{used,ik}\leq E_0].
\]

The unit-level primary endpoint is the held-out safe useful-service fraction

\[
U_i={\sum_k \Delta t_k q_{ik}\over\sum_k \Delta t_k},
\qquad 0\leq U_i\leq1.
\]

An irreversible short, containment trip, or destructive open circuit scores
zero for the remaining episode. A transient trip uses the same frozen restart
and cool-down rule in every arm. This endpoint rewards delivered demand but
cannot trade a dangerous local peak for more current.

The primary paired difference is

\[
D_i^{AY}=U_{i,A}-U_{i,Y}.
\]

The practical fixed-comparator gate is deliberately conservative:

\[
D_i^{AF}=U_{i,A}-
\max(U_{i,W},U_{i,G},U_{i,F24},U_{i,F36}).
\]

Report, but do not replace the primary endpoint with, terminal flux, delivered
charge, recovery time, conductor mass, control energy, irreversible failures,
and

\[
J^*=\max_k {J_{max,k}\over\max(I_{del,k},\epsilon)},
\qquad
H^*={\int\!\!\int \mathbf J\!\cdot\!\mathbf E\,dVdt
\over\int I_{del}\,dt}.
\]

## Uncertainty and decision rule

Resample material batches, then complete matched blocks within each sampled
batch, 10,000 times. Never resample time points as independent units. Report
the mean paired effect, its two-sided 95% hierarchical-bootstrap interval, all
batch-specific effects, and a batch-fixed paired-model sensitivity analysis.

Set the minimum worthwhile service improvement before the pilot to
`delta_star = 0.10` (ten percentage points of the evaluation horizon).

| Result | Decision |
|---|---|
| Lower 97.5% bound for `mean(D_AY) > 0`, point estimate at least `delta_star`, and lower 97.5% bound for `mean(D_AF) > 0` | Adaptive causal and practical benefit survives, subject to safety and leakage gates. |
| Upper 97.5% bound for `mean(D_AY) < delta_star` | A worthwhile adaptive benefit is ruled out at the planned resolution. |
| Upper 97.5% bound for `mean(D_AY) < 0` | Directional reversal: yoked replay is better. |
| Upper 97.5% bound for `mean(D_AF) < 0` | Practical reversal: at least one fixed design is better within matched blocks. |
| Interval crosses the relevant boundary | Inconclusive; do not describe it as equivalence or success. |

Gate tests in the order `A versus Y`, then `A versus best fixed`; this avoids a
post-hoc winner selection. Any safety-limit breach, unexplained
batch-by-condition reversal, or advantage present only at practiced lesions
narrows or defeats the general claim even if the pooled contrast is positive.

## Minimal power and sequential stopping

The previous `n = 18/22` calculation cannot be reused because its endpoint and
contrast differ. After the first 12 concealed complete blocks, an independent
analyst estimates the standard deviation `s_D` of `D_AY` from randomly
sign-scrambled pairs, without condition direction or secondary outcomes. For
one-sided `alpha = 0.025`, 90% power, and a true difference of `delta_star`, the
fixed-design starting value is

\[
n_{fixed}=\left\lceil
\left({(z_{0.975}+z_{0.90})s_D\over\delta_{star}}\right)^2
\right\rceil.
\]

Use `n_max = max(24, n_fixed)`, capped at 48 complete blocks. If the formula
exceeds 48, stop: the system is too variable to resolve a ten-point benefit
with this design. Do not replace that finding with more selected seeds.

Use the frozen batch-adjusted paired model to compute `Z = mean(D_AY) / SE` at
two looks with information fractions `t = 0.5` and `1.0`. The one-sided
O'Brien-Fleming efficacy boundaries are `Z = 2.797` and `1.977`. Secondary
gates are tested only after the primary boundary is crossed. At the first look,
nonbinding futility requires both:

1. the upper 97.5% interval bound is below `delta_star`; and
2. conditional power under `delta_star` is below 0.20, where

\[
CP=1-\Phi\!\left(
{1.977-[\sqrt t\,Z_1+(\delta_{star}\sqrt{n_{max}}/s_D)(1-t)]
\over\sqrt{1-t}}
\right).
\]

Each unit still stops immediately at its calibrated containment limits. Pause
the whole experiment after any failure outside that envelope; that is a safety
event, not a statistical success or failure.

## Leakage and reversal tests

| Check | Falsifying result |
|---|---|
| Artifact lock | Controller, observation schema, both fixed rules, lesion algorithm, or analysis hashes differ after schedule commitment. |
| Yoke identity | `A` and `Y` command hashes or actuator energy differ beyond calibration tolerance. |
| Future-event canary | A cross-validated predictor recovers the next hidden event from controller-visible fields above the 95th percentile of label permutations. |
| Observation ablation | Masked or time-permuted observations retain the `A-Y` advantage. |
| Schedule reversal | The effect changes sign under held-out terminal reversal, load shift, or bottleneck lesion. |
| Budget reversal | The effect disappears after equal-current, equal-mass, or total-energy accounting. |
| Batch reversal | The pooled advantage is driven by one batch and reverses in the others. |
| Literal surface | Scores change when only image rendering or smoothing changes. |

A leakage failure invalidates the run; it does not support either arm. Survival
of observation ablation or a consistent yoke tie rejects the claim that present
consequences caused the benefit.

## Executable record structure

`design.tsv`

| Required columns |
|---|
| `run_id block_id batch_id condition position_code microstate_seed schedule_hash controller_hash fixed_rule_hash lesion_algorithm_hash material_hash M0_kg E0_J P0_W T0_K yoke_donor` |

`events.tsv`

| Required columns |
|---|
| `run_id time_s episode load_id source_pad sink_pad I_req_A damage_id damage_type mask_hash removed_volume_m3 event_blind_code` |

`samples.tsv`

| Required columns |
|---|
| `run_id time_s I_req_A I_del_A V_V Jmax_A_m2 Tmax_K Smax_Pa M_used_kg E_load_J E_actuator_J E_sensor_J E_compute_J P_cool_W command_hash containment_state` |

`unit-summary.tsv`

| Required columns |
|---|
| `run_id block_id batch_id condition U delivered_charge_C recovery_s Jstar_m2_inv Hstar_J_C control_energy_J irreversible_failure valid exclusion_code` |

Before analysis, assert: exactly one row per six conditions in every block;
identical budget fields within block; unique seed streams; shared schedule hash;
exact `A/Y` command hash; no missing primary samples except a logged
containment failure; and no exclusions created after decoding. The analysis
consumes these tables directly and emits every contrast, interval, boundary
crossing, and falsification status from the frozen manifest.
