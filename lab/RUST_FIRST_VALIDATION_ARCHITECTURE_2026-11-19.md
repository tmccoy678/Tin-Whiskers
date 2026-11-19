# Rust-first field, growth, and conduction validation architecture

## Objective

Build one reproducible Rust mechanism in which a bounded frequency/slit field
guides local conductive growth, finite material and energy constrain every
choice, the changed body carries current, and every causal transition remains
exactly auditable and renderable. MOOSE independently solves conduction on
selected frozen Rust states and supplies the cross-solver verdict.

The smallest implementation is one Rust library crate, one runner binary, and
the existing tested `adaptive-controller-candidate` path dependency:

```text
lab/candidates/rust-field-growth/
├── Cargo.toml
├── Cargo.lock
├── src/
│   ├── lib.rs
│   ├── config.rs
│   ├── grid.rs
│   ├── field.rs
│   ├── budget.rs
│   ├── conduction.rs
│   ├── growth.rs
│   ├── step.rs
│   ├── audit.rs
│   ├── exact_state.rs
│   ├── moose_bridge.rs
│   └── bin/run.rs
├── tests/
│   ├── invariants.rs
│   ├── restart_identity.rs
│   └── moose_contract.rs
└── moose/voltage_conduction.i
```

## Module boundaries

| Module | Owns | Contract |
|---|---|---|
| `config` | Dimensions, apertures, frequencies/wavelengths, phase relation, material mapping, seeds, limits, solver tolerances | Strict serde schema with unknown-field rejection; canonical hash freezes every scientific choice |
| `grid` | Typed row-major `Grid<T>`, barrier/slit masks, source/sink masks, four- or six-neighbour indexing | Bounds-safe indexing and one declared coordinate convention shared by every module |
| `field` | Scalar Huygens/Fresnel slit field, coherent cross term, path-tagged intensity sum, bounded actuator mixtures | Actions select predeclared amplitudes, frequency, phase, or tagging state; integrated incident energy is matched across comparison arms |
| `budget` | Mobile material, deposited material, dissolved/removed material, optical energy, electrical energy, reinforcement credits | Integer or fixed-point ledgers conserve material and charge every physical action exactly once |
| `conduction` | Harmonic-face finite-volume solve of `div(sigma grad(V)) = 0`, terminal flux, current vector/magnitude, Joule density | Residual, source/sink balance, and nonnegative dissipation accompany every solved state |
| `growth` | Local frontier recruitment, widening, dissolution, lesion response, seeded stochastic selection | Topology changes only through eligible local neighbours; probability uses present field/current/material state and never a target route |
| `step` | Causal epoch ordering and adaptive-controller call | Frozen state → solve → observe → choose bounded action → spend budgets → grow → solve outcome → update controller |
| `audit` | Canonical per-choice record, hash chain, action propensity, controller renewal, ledgers, solver metrics | One consecutive index and one before/after state hash per accepted choice; atomic checkpoint records the safe append boundary |
| `exact_state` | Versioned binary snapshot plus literal PGM/VTK translation | Header fixes schema, dimensions, endian order, units, arrays, and SHA-256; decoding reproduces every cell value exactly |
| `moose_bridge` | Frozen topology/conductivity export, pinned MOOSE input, result import, comparison receipt | Rust and MOOSE share boundary values and conductivity mapping through files, while executables and numerical implementations remain independent |

## One causal epoch

1. Hash exact state `S_t` and solve its conduction fields.
2. Form observation `O_t` from declared present-field summaries.
3. Let the controller choose bounded slit/frequency action `A_t` with a logged
   propensity.
4. Debit optical and electrical energy for `A_t`.
5. Construct the energy-matched optical field and apply one local growth,
   widening, dissolution, or maintenance transition.
6. Debit or return material through the conserved reservoir ledger and produce
   exact state `S_(t+1)`.
7. Solve conduction on `S_(t+1)`, calculate delivery, concentration, Joule,
   stress proxy, and useful-service consequences, then update the controller.
8. Append the canonical record and atomically advance the checkpoint.

This order gives every action a clear temporal parent and every learned update
a measured consequence.

## Invariant tests

| Invariant | Cheapest decisive test |
|---|---|
| Seed identity | Two fresh runs with one config and seed produce identical state hashes, action sequence, metrics, and audit hash |
| Field fairness | Coherent and path-tagged maps integrate to the same declared incident energy; coherent symmetry and tagged cross-term removal pass analytic fixtures |
| Local anatomy | Every newly occupied cell has an occupied declared neighbour and lies outside the barrier mask or inside a slit |
| Material conservation | `initial + injected = mobile + deposited + removed`; equality holds at every choice and after damage/repair |
| Energy conservation | Cumulative optical/electrical charges equal the exact sum of accepted actions; reinforcement changes selection opportunity while preserving physical charges |
| Bounded state | Conductivity, concentration, temperature/heat, and reservoir arrays remain finite and inside declared ranges |
| Conduction solution | Homogeneous-grid analytic voltage passes; residual reaches tolerance; source and sink current balance; Joule density is nonnegative |
| Causal separation | Observation hash names `S_t`; action record names that observation; outcome hash names `S_(t+1)`; controller input contains no route coordinate or future lesion |
| Audit chain | Choice indices are unique and consecutive; each prior-state hash equals the preceding after-state hash |
| Restart identity | SIGTERM at a completed epoch plus `--resume` yields the same final snapshot and audit hash as uninterrupted execution |
| Exact-state round trip | Encode → decode reproduces every array byte and state hash; PGM/VTK occupancy equals the canonical threshold cell-for-cell |
| Matched comparison | Fixed, adaptive, and reciprocal-yoke arms share seeds, fields, budgets, material limits, damage, boundaries, and stopping rules |

## Independent MOOSE verification

Rust freezes a predeclared verification set: initial state, first connection,
pre-change state, first post-change state, lesion state, first repair, final
state, and a seeded hidden sample. For each snapshot the bridge writes:

- literal occupancy and conductivity arrays;
- source/sink masks and boundary values;
- material and cell dimensions;
- Rust residual, terminal flux, current/Joule integrals, and state hash;
- pinned MOOSE commit and binary SHA-256.

MOOSE solves the same steady conduction problem from those files. The verifier
compares terminal flux, source/sink balance, current and Joule integrals, and
peak-field locations using tolerances frozen by analytic-grid and resolution
convergence tests before the developmental run. Agreement promotes the
electrical measurement; a resolved discrepancy becomes a focused numerical
experiment with both original outputs preserved.

## Compact Git evidence boundary

Commit:

- Rust source, tests, `Cargo.lock`, and pinned MOOSE input;
- reviewed material/config manifests;
- `run-manifest.json` with seed, versions, executable/config hashes, and CLI;
- compact `metrics.tsv`, `state-hashes.tsv`, and arm summary;
- a small predeclared set of exact binary/PGM snapshots;
- `moose-verification.tsv` plus one concise verdict memo;
- SHA-256, byte size, line count, and final status for each ignored large
  artifact.

Keep in ignored work/output paths:

- complete per-choice JSONL audit;
- every-epoch state sequence and presentation frames;
- MOOSE Exodus fields and solver logs;
- restart checkpoints, compiled targets, vendored backends, and movies.

This boundary keeps Git reviewable while retaining byte-level proof that every
large local artifact belongs to the committed source, configuration, and
result.
