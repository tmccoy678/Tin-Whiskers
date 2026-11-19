# Adaptive controller bench

## Purpose and claim boundary

This memo specifies the smallest controller that can close the causal loop

```text
present local fields -> bounded action -> changed material -> new local fields
```

without receiving a route, target coordinates, terminal identity, or desired
anatomy. The controller is a safety-constrained contextual bandit over physical
actuator channels. It is intentionally smaller and more inspectable than a
neural policy: a successful result must come from consequence-sensitive action,
not from hidden geometric supervision or model capacity.

Everything under **Implemented now** is present in the repository or the
private ignored work directory. The controller specification below became the
locked boundary for the reciprocal 12- and 120-action pilots. Their results
live in the dated pilot records; the scale-aware Rust controller and renewal
tests live under `candidates/adaptive-controller/`.

## Implemented now

### Reduced Rust model

`simulation/reduced-rust/src/main.rs` implements a `192 x 128` dimensionless
growth lattice. It couples Laplace relaxation, mobile-material diffusion,
stochastic interface deposition, and an optional photon field. Its photon
choices are fixed fields or a hand-written frontier-following rule. The latter
does respond to the present frontier, but it is not the controller proposed
here: it observes a geometric frontier and moves a band center toward it.

The Rust program emits a metal PGM, a potential PGM, and CSV trajectories. It
does not currently ingest MOOSE field output or choose actions from MOOSE
consequences.

### MOOSE conduction solve

`simulation/voltage-routing/voltage_conduction.i` reads an image topology and
solves steady normalized conduction with source voltage `1`, sink voltage `0`,
metal conductivity `1`, and medium conductivity `1e-6`. Its CSV and Exodus
outputs include:

- metal fraction and terminal flux;
- conductivity and voltage-gradient components;
- current-density magnitude and its maximum;
- Joule-density proxy, its integral, and its maximum.

This model presently has no mechanical-stress field, finite material reservoir,
temperature evolution, or optical absorption. Joule density is an electrical
heating proxy; it is not a solved temperature field. Mechanical stress is
therefore unavailable, not zero.

`simulation/moose-native-growth/` separately couples a phase field, voltage,
conductivity, mobility, and a latent thermal field inside MOOSE. It does not
import the Rust topology and does not implement an adaptive controller.

### Fixed current-driven controls

The committed `simulation/voltage-routing/remodel_flow.py` alternates MOOSE
solves with a fixed local widening law. It maps the current-density field back
to the lattice, scales it by the occupied-cell 80th percentile, and permits new
metal only beside existing metal. Its stochastic law and seed schedule are
fixed; it does not choose an action from measured improvement.

The newer private work script
`simulation/work/live_moose/current_fiber_remodel.py` adds two fixed optical
probe footprints. Their upper/lower intensities follow a sinusoid of epoch, not
the measured response. The present current signal and the fixed probe multiply
the probability of local adjacent growth, with probability capped at `0.30`.
After 36 epochs, its recorded metrics give:

| Measure | Recorded change |
|---|---:|
| Terminal flux | `8.427859 x` |
| Metal fraction | `1.444717 x` |
| Peak current density / terminal flux | `75.292797%` lower |

This is the current fixed deterministic control reported in `lab/README.md` as
`8.43 x`, `1.44 x`, and `75.29%`. It is not an adaptive-AI result. The earlier
committed 24-epoch control reports `8.26 x`, `1.43 x`, and `72.01%`; the two
records describe different fixed runs and must not be merged.

## Controller specification

### Causal unit and timing

One decision epoch is strictly ordered:

1. MOOSE solves state `S_t` without access to the next action.
2. A read-only adapter produces observation `O_t` from that solved state.
3. Rust verifies `O_t`, updates no physics, and samples one bounded action
   `A_t` with a logged probability.
4. The unchanged local remodeling law applies `A_t` for one epoch and writes
   topology `S_(t+1)`.
5. MOOSE solves `S_(t+1)` and returns outcome vector `Y_(t+1)`.
6. Rust updates the response model from `(O_t, A_t, Y_(t+1) - Y_t)`.

The action is randomized conditional on the observed state, and its propensity
is recorded. That sequential randomization is the causal identification
mechanism. A correlation between an unrandomized controller choice and a later
field is not sufficient evidence of an action effect.

### Observation space

The controller receives one global consequence block plus one block for each
physical actuator footprint. The two optical footprints are calibrated before
the run and remain fixed. Their names, `upper` and `lower`, identify hardware
channels; they are not route coordinates.

Global fields at epoch `t`:

```text
abs_terminal_flux
metal_fraction
joule_integral
peak_current_density
peak_joule_density
material_budget_remaining
optical_energy_remaining
electrical_energy_remaining
```

For each actuator footprint `k`, the adapter reports fixed-footprint weighted
summaries of present local fields:

```text
mean and p95 current-density magnitude
mean and p95 Joule-density proxy
conductive fraction
conductive-interface fraction
mean available reservoir, when modeled
mean and p95 temperature, when modeled
mean and p95 mechanical stress, when modeled
```

No cell address, `x/y` coordinate, voltage potential, source/sink label,
distance transform, shortest path, terminal mask, target mask, or future event
enters the controller. Voltage potential is excluded because its absolute
value can act as a distance-to-terminal surrogate. Magnitudes of present local
current, heating, and stress remain admissible consequences.

Each run manifest declares which channels are physically available. A missing
declared channel stops the controller. A channel absent from the physics, such
as mechanical stress in the current conduction model, is masked and excluded
from the corresponding claim; it is never imputed as zero.

### Action space

The general bounded action is

```text
A_t = (p_upper, p_lower, optical_pulse_energy,
       source_voltage, electrical_duty, polarity)
```

with hard manifest limits on every component, total and cumulative energy,
voltage slew, current compliance, and pulse duration. The controller cannot
write a metal cell, emit an arbitrary image, choose a point, or modify solver
or material parameters.

The minimal optical action set is:

```text
upper-heavy = (0.75, 0.25)
lower-heavy = (0.25, 0.75)
```

Both spend the same fixed optical pulse energy. A dark action `(0, 0)` exists
only as a fail-closed state and is not scored as an ordinary candidate.

The electrical action space may later select a bounded source-voltage level,
duty cycle, or polarity. The first adaptive experiment holds source voltage at
the present normalized value `1` and current compliance fixed. This isolates
optical adaptation before adding a second causal degree of freedom.

### Invariants

The following conditions hold in the adaptive, fixed, and yoked arms:

1. Terminal geometry, initial topology, conductivity law, MOOSE input, local
   remodeling law, timestep, and stopping rules are identical.
2. New material may appear only through the same local adjacent-growth kernel;
   the controller never deposits or deletes a cell directly.
3. Optical pulse energy per active epoch and cumulative optical budget are
   identical. Electrical compliance and cumulative electrical budget are
   identical.
4. Every arm has the same maximum material reservoir, horizon, cooling
   assumption, and damage schedule.
5. Controller decisions cannot alter objective definitions, safety limits,
   solver tolerances, observation channels, or actuator footprints after the
   run begins.
6. Policy randomness, material-growth randomness, and any damage randomness
   use separate recorded streams.
7. The fixed deterministic controller remains the present sinusoidal
   upper/lower schedule. It is not re-fit after observing adaptive results.
8. The yoked replay receives the adaptive arm's exact action sequence and
   energy, in order, while its own field observations are ignored.
9. Literal lattice occupancy and raw scalar fields remain the evidence
   surface; rendering cannot create or erase branches.

### Objective vector

Let `I_t` be the magnitude of terminal flux and let `I_ref` be a fixed current
declared before the run. The controller predicts the one-step change in the
full vector

```text
G_t = [
  + I_t,                              delivery
  - peak_J_t / max(I_t, epsilon),     current concentration per delivered current
  - peak_q_t / max(I_t^2, epsilon),   peak Joule heating at equal delivered current
  - peak_stress_t at I_ref,           mechanical stress at equal delivered current
  - material_used_t,
  - cumulative_optical_energy_t,
  - cumulative_electrical_energy_t
]
```

`peak_q / I^2` is used because Joule heating scales quadratically with applied
voltage in the present linear conduction solve. Mechanical stress receives no
assumed scaling exponent: once mechanics is coupled, it is evaluated at
`I_ref` by a common-current solve or by a validated constitutive rescaling.

The vector is never replaced in the record by one favorable scalar. Selection
is lexicographic and predeclared:

1. reject actions whose one-sided uncertainty bound can violate a hard safety
   or resource limit;
2. among feasible actions, maximize the lower confidence bound on delivery;
3. within a fixed delivery tolerance, minimize the worst normalized current,
   heat, and stress component;
4. break remaining ties by material and energy, then by the policy RNG.

This preserves delivery as the task while preventing a high-current action
from hiding a worsening bottleneck, heat concentration, or material cost.

### Controller state and update

For each ordinary action `a` and objective component `d`, maintain a small
ridge-regression response model:

```text
A_a = lambda I + sum(phi_t phi_t^T for realized action a)
b_a,d = sum(phi_t * delta_G_t,d for realized action a)
theta_a,d = inverse(A_a) b_a,d
```

`phi_t` contains the global consequence block, the chosen footprint's local
summaries, its contrast with the other footprint, and a constant. It contains
no coordinate or epoch-dependent route feature. The controller state is only:

- `A_a`, `b_a,d`, and residual uncertainty for the two actions;
- remaining material and energy budgets;
- previous observation, action, and state hashes;
- step count and the policy RNG state.

The first four actions are a seeded, balanced random permutation containing
each action twice. Later choices use the safety/lexicographic rule with a
predeclared exploration probability, proposed as `0.10`, divided uniformly
over feasible actions. Every realized action therefore has a logged nonzero
propensity. The response model updates only after the next MOOSE outcome
arrives and passes validation.

This is the minimal AI controller in the experiment: it learns which bounded
actuator choice has better consequences in the present measured context. It
does not learn or emit anatomy.

### Anti-leakage rules

- Freeze observation channels, action set, objective order, limits, and model
  hyperparameters before evaluating a seed.
- Reset adaptive state at the start of every evaluation network. Cross-run
  training, if later studied, uses disjoint training and evaluation seeds.
- Never supply coordinates, target images, route masks, graph distances,
  terminal identities, lesion locations, future loads, or future task order.
- Do not normalize with a future maximum, final topology, ensemble outcome, or
  statistic computed from evaluation arms. Use only pre-run calibration or
  present/past values from the same arm.
- The fixed arm and yoked arm never send outcomes to the adaptive controller.
- Yoked replay uses the recorded action sequence verbatim; it does not call the
  controller and does not substitute actions after seeing its own state.
- Counterfactual MOOSE branches from the same state may be used in a later
  simulator-development set, but never during selection or evaluation.
- Keep policy, growth, and damage RNG streams independent. Reusing one random
  draw for action selection and deposition would leak the action into the
  material noise.
- Hash every input and output so a stale observation or mismatched topology
  cannot be silently paired with an action.

### Fail-closed limits

The run manifest supplies numerical limits appropriate to the calibrated
material. The controller takes the dark action in simulation, and a physical
system removes stimulation and returns the source to its hardware-safe state,
when any of the following occurs:

- missing, stale, duplicate, non-finite, out-of-range, or hash-mismatched data;
- wrong schema, grid size, epoch, topology, field mask, or actuator calibration;
- disagreement between MOOSE terminal power and integrated Joule density beyond
  a declared tolerance;
- exhausted material, optical-energy, or electrical-energy budget;
- measured or conservative predicted violation of peak current, heating,
  temperature, stress, voltage, current-compliance, slew, or growth-rate limit;
- no candidate action certified feasible;
- controller-state load failure or an update based on an unvalidated outcome.

A failed epoch does not update the response model and cannot be retried with a
different action under the same audit step. The run stops after the single
fail-closed transition unless the manifest explicitly defines a safe read-only
measurement step.

## Minimal Rust-to-MOOSE interface

The first implementation should keep MOOSE as the physics authority and Rust
as the policy authority. A narrow adapter may translate Exodus cell data, but
it must not choose or modify an action.

### Files per epoch

1. `topology-####.pgm` -- Rust/local remodeling output consumed by MOOSE's
   existing `ImageMesh` route.
2. `moose-####.csv` and `moose-####.e` -- unchanged MOOSE scalar and cell-field
   outputs.
3. `observation-####.json` -- adapter output containing only the approved global
   and fixed-footprint summaries, channel-availability mask, units, dimensions,
   and hashes of the topology and MOOSE outputs.
4. `action-####.json` -- Rust output containing actuator fractions, pulse
   energy, electrical settings, selection propensity, policy-state hash, and
   the observation hash it authorizes.
5. `step-####.jsonl` -- append-only one-step audit record after the next MOOSE
   state is validated.

The adapter computes current and Joule summaries from the existing Exodus
fields and reads terminal flux and extrema from CSV. It exports no coordinates.
Rust rejects unknown fields rather than accepting an expanded observation by
default.

The morphology executor verifies the action hash, applies only the existing
local current-plus-probe probability law, preserves its probability cap and
independent growth RNG, and emits the next PGM. An electrical action reaches
MOOSE only through an allowlisted boundary override such as
`BCs/source/value=<bounded value>`; no arbitrary MOOSE parameter string is
accepted from the controller.

### One-step audit record

This schema example is not an experimental result:

```json
{"schema":"adaptive-step/v1","run_id":"<run-id>","epoch":7,"pre":{"topology_sha256":"<sha256>","moose_sha256":"<sha256>","observation_sha256":"<sha256>","objective":["<I>","<Jpk_per_I>","<qpk_per_I2>",null,"<material>","<Eopt>","<Eelec>"]},"policy":{"state_before_sha256":"<sha256>","eligible":["upper-heavy","lower-heavy"],"selected":"upper-heavy","selection_mode":"explore","propensity":0.05,"rng_stream":"policy","rng_counter":11},"limits":{"manifest_sha256":"<sha256>","passed":true},"action":{"upper_fraction":0.75,"lower_fraction":0.25,"optical_pulse_energy":"<fixed-energy>","source_voltage":1.0,"electrical_duty":"<fixed-duty>","polarity":1},"post":{"topology_sha256":"<sha256>","moose_sha256":"<sha256>","objective":["<I>","<Jpk_per_I>","<qpk_per_I2>",null,"<material>","<Eopt>","<Eelec>"],"delta_objective":["<dI>","<dJ>","<dq>",null,"<dM>","<dEopt>","<dEelec>"]},"policy_update":{"accepted":true,"state_after_sha256":"<sha256>"}}
```

The `null` stress entry means the run manifest declared mechanical stress
unavailable. It cannot be rendered as zero or included in a stress claim.

## Cheapest first adaptive experiment

Run a private two-seed reciprocal-yoke pilot for 12 remodeling epochs. Reuse
the present `192 x 128` initial topology, MOOSE conduction input, local
current-driven growth law, two optical footprints, probability cap, and
normalized source voltage. Change only who chooses the upper/lower allocation.

For material seeds `A` and `B`, run six short trajectories:

| Seed | Trajectory |
|---|---|
| `A` | adaptive feedback |
| `A` | exact fixed sinusoidal control |
| `A` | open-loop replay of adaptive sequence generated on `B` |
| `B` | adaptive feedback |
| `B` | exact fixed sinusoidal control |
| `B` | open-loop replay of adaptive sequence generated on `A` |

Use common random numbers for material deposition within each seed while
keeping policy randomness separate. Give all six trajectories the same 12
optical pulse energies, electrical limits, maximum material reservoir, and
stopping rules. Hold the electrical action fixed so the first pilot tests one
causal degree of freedom.

The pilot passes the implementation gate only if:

1. the adaptive action sequence changes with present measured consequences and
   is not merely the fixed schedule under another name;
2. every invariant, hash, propensity, limit, and budget check passes;
3. adaptive feedback is directionally better than its reciprocal replay in
   delivery without worsening the normalized current/Joule objectives or using
   more material/energy; and
4. the conclusion is unchanged when outcomes are evaluated at common delivered
   current.

Two seeds cannot establish population performance. This pilot is the cheapest
test that can expose a broken causal loop, coordinate leakage, an ineffective
action basis, unsafe selection, or an advantage that disappears under yoking.
Only after it passes should a predeclared multi-seed ensemble estimate an
adaptive effect and uncertainty.
