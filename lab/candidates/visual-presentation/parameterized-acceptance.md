# Parameterized presenter acceptance

## Verdict

**GO on synthetic fixtures for both `FIXED-RULE CONTROL` and `ADAPTIVE
CONTROLLER`.** The same renderer now carries an explicit mode label, exact state
count, exact source/sink values, deterministic upper/lower stimulus status, and
`FIXED`/`WARMUP`/`EXPLORE`/`EXPLOIT` action labels while copying the lattice ROI
byte-for-byte.

No live or completed 120-action pilot artifact was read for this phase. The
candidate remains proven against isolated synthetic fixtures only.

## Evidence presenter results

Both synthetic fixtures produced:

- three state PNGs at 864 x 480;
- nine uncompressed 24-bit RGB movie frames at 4 fps;
- 2.25-second movies with exact one-second first/final holds;
- zero rendered lattice pixel or RGB channel-byte mismatches;
- zero decoded movie lattice pixel or RGB channel-byte mismatches across all
  nine frames;
- fixed title/mode and source/sink regions on every state;
- source PNG, action-manifest, and presentation-manifest SHA-256 hashes in each
  `render-metadata.json`.

The fixed fixture records `FIXED`, `FIXED`, `FIXED`. The adaptive fixture
records `WARMUP`, `EXPLORE`, `EXPLOIT`, with explicit upper/lower
`ACTIVE`/`INACTIVE`/`OFF` values.

Automated negative fixtures also passed: the presenter rejected mismatched
state counts, adaptive actions under a fixed-control label, and a lattice ROI
that was not an exact multiple of its logical-cell scale.

## Intel atomic surface results

The Intel candidate is a single overwrite-only ANSI surface:

- `current-status.json` is validated and atomically replaced, never appended;
- `current.ansi` begins with clear/home and contains one current status/frame;
- every uniform 6 x 6 logical lattice cell maps to one distinct Braille dot;
- no interpolation, averaging, or smoothing is used;
- `RUNNING` and `COMPLETE` each rendered one 576-cell Braille snapshot;
- `ERROR` rendered four concise lines and zero stale Braille cells;
- the RUNNING → COMPLETE → ERROR test found no retained prior status or frame;
- the final disposable surface was restored to `COMPLETE`.

The terminal view is an ephemeral, human-readable overview. The lossless PNG
states and RGB MOV remain the evidence surface.

## Primary paths

- Presenter: `evidence_presenter.swift`
- Presenter checker: `check_presenter.swift`
- Fixed fixture output: `generated/parameterized/fixed/`
- Adaptive fixture output: `generated/parameterized/adaptive/`
- Manifest rejection results:
  `generated/validation/manifest-rejection-results.json`
- Atomic status writer: `update_intel_status.swift`
- Intel renderer: `intel_atomic_surface.swift`
- Current Intel surface: `generated/intel/current.ansi`
- Intel test results: `generated/intel/test-results.json`

## Frozen adaptive handoff contract

A real adaptive candidate may be generated only from a completed, immutable
frame set plus a completed actions manifest. The manifest must state the exact
state count, boundary values, cadence, lattice ROI, and one contiguous action
per state. `render-metadata.json` then binds those inputs by SHA-256. A missing,
duplicate, still-changing, or mode-inconsistent action fails before output.
