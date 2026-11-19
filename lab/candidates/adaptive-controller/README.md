# Adaptive controller candidate

This crate is an isolated lab candidate. It does not run MOOSE, modify a
topology, control hardware, or replace the fixed deterministic and yoked-replay
controls. Canonical simulation code and results do not depend on it.

The library implements the policy boundary proposed in
`../../adaptive-controller.md`:

- strict observations and actions with unknown-field rejection;
- a two-action safety-constrained contextual bandit;
- a balanced, seeded four-step warmup and explicit action propensity;
- required frozen positive scales for every measured policy feature;
- consequence-change detection with short balanced action renewal;
- fail-closed schema, epoch-chain, hash, energy-counter, safety, and budget
  checks;
- deterministic fixed-order JSON audit records; and
- separate policy state from the physical or simulated morphology.

The unit labels are deliberate placeholders such as
`<SI:delivered-current-pending-calibration>`. Numerical test fixtures are
abstract candidate values and make no physical calibration claim.

## Feature-scale failure and fix

The first live software pilot exposed a real scale pathology before warmup. The
raw context combined values spanning roughly `1e-3` to `1e5`; the largest
components dominated ridge leverage, so the conservative uncertainty bound
rejected both actions. The controller failed closed as designed, but the policy
could not begin its balanced causal probes.

`ControllerConfig.feature_scales` now requires one finite positive divisor for
each nonconstant feature:

```text
delivery
current_per_delivery
heat_per_delivery_squared
mean_current_density
p95_current_density
mean_joule_density
interface_contrast
```

The intercept remains exactly `1`. Each other feature is divided by its frozen
configured scale before fitting, uncertainty calculation, or prediction. The
scales are strict serialized configuration and are copied into the hashed
policy state, so changing a scale changes provenance. There is no implicit
unit-scale fallback.

The values for a physical experiment must come from its reviewed calibration
manifest and be frozen before evaluation. The realistic-magnitude unit fixture
only demonstrates the mechanism; it does not supply physical calibration.

## Reversal failure and consequence renewal

The completed software reversal pilot exposed a second bounded controller
pathology. `lower-heavy` left the model-safe eligible set near epoch 10. When
the upper optical consequence changed at epoch 60, the selected arm could
update from its new outcome, but the policy had no route for re-sampling the
excluded alternative. Commitment therefore persisted through the reversal.

`ControllerConfig.renewal` now freezes:

- an objective-unit residual scale and dimensionless error threshold for every
  objective component;
- the number of consecutive changed outcomes required to trigger;
- an even renewal length;
- fixed upper-first, fixed lower-first, or separately seeded balanced order;
- the balanced upper/lower marginal propensity; and
- a renewal-only RNG seed, separate from ordinary policy exploration.

For the realized action, the controller computes
`abs(observed_delta - predicted_delta) / residual_scale` before updating that
arm. Persistent threshold exceedance opens a short renewal schedule containing
equal numbers of the two existing energy-matched hardware actions. Renewal
does not admit a new action or bypass the current observed-state, schema, hash,
or per-step budget checks. Outcomes caused by renewal actions do not recursively
trigger another renewal.

Every audit step records the predicted delta, observed delta, residual,
normalized residual, component thresholds crossed, change streak, renewal
trigger/mode/generation, exact action propensity, and before/after state hashes.
These are software-policy mechanics only; they make no claim about physical
reversal sensitivity.

Run the focused test suite:

```sh
cd /Users/tmccoy678/Blu-Workbench/tin-whiskers-dendrites-ai-si/lab/candidates/adaptive-controller
cargo test
```

Optional formatting check:

```sh
cargo fmt --check
```
