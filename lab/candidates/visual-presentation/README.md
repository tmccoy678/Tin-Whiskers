# Visual presentation candidate

This candidate changes presentation only. It copies the literal 1152 x 768
anatomy rectangle from each existing `current_fiber_remodel_frames` PNG without
resizing, filtering, antialiasing, interpolation, or physics changes. All text
and indicators remain outside that rectangle.

The movie uses uncompressed 24-bit RGB in a MOV container; every frame is
lossless and independent. The state PNG sequence is the second pixel-exact
lossless master. Both run at the source cadence of 4 fps, with the movie holding
the exact first and final states for four frames (one second) each.

Run from the repository root:

```sh
candidate=lab/candidates/visual-presentation
source_frames="$HOME/Desktop/Tin Whisker Dendrite Work/Results/current_fiber_remodel_frames"
swift "$candidate/render_candidate.swift" --source "$source_frames" --output "$candidate/generated"
swift "$candidate/check_candidate.swift" --source "$source_frames" --output "$candidate/generated"
```

The checker verifies:

- 37 rendered state PNGs at 1440 x 960;
- 43 lossless movie frames at 4 fps and 10.75 seconds;
- fixed title, control, source/sink, and legend regions on every state;
- exact anatomy-pixel identity in every rendered state;
- exact decoded anatomy identity for states 9, 18, and 27;
- exact anatomy during all first/final hold frames.

Stimulus status is derived only from the existing indicator center pixel:
black is `OFF`, green-channel intensity 180 or higher is `ACTIVE`, and any
other nonzero indicator is `INACTIVE`. This classification changes no input or
result; it makes the source indicator readable as a discrete presentation
legend.

## Parameterized presenter

`evidence_presenter.swift` is the reusable path for both
`FIXED-RULE CONTROL` and `ADAPTIVE CONTROLLER`. It accepts one presentation
manifest that names the exact state count, frame directory, action manifest,
source/sink values, cadence, and lattice ROI. The action manifest supplies one
contiguous entry per state with explicit upper/lower stimulus status and one of
`FIXED`, `WARMUP`, `EXPLORE`, or `EXPLOIT`.

The presenter rejects a state-count mismatch, a fixed/adaptive action mismatch,
an incomplete frame set, or a nonintegral lattice ROI before writing output.
Each output includes source-frame, presentation-manifest, and action-manifest
SHA-256 hashes in `render-metadata.json`.

The included synthetic fixtures exercise both modes without reading a live
experiment:

```sh
candidate=lab/candidates/visual-presentation

swift "$candidate/make_synthetic_fixtures.swift" "$candidate/fixtures/source-states"

swift "$candidate/evidence_presenter.swift" \
  --manifest "$candidate/fixtures/fixed-presentation.json" \
  --output "$candidate/generated/parameterized/fixed"
swift "$candidate/check_presenter.swift" \
  --manifest "$candidate/fixtures/fixed-presentation.json" \
  --output "$candidate/generated/parameterized/fixed"

swift "$candidate/evidence_presenter.swift" \
  --manifest "$candidate/fixtures/adaptive-presentation.json" \
  --output "$candidate/generated/parameterized/adaptive"
swift "$candidate/check_presenter.swift" \
  --manifest "$candidate/fixtures/adaptive-presentation.json" \
  --output "$candidate/generated/parameterized/adaptive"

swift "$candidate/test_manifest_validation.swift" "$candidate"
```

## Intel atomic terminal surface

`update_intel_status.swift` validates one status JSON and atomically replaces
`current-status.json`; it never appends. `intel_atomic_surface.swift` validates
that each lattice cell is a uniform literal block, maps each logical cell to a
distinct Unicode Braille dot, and atomically replaces one `current.ansi` file.
The output begins with terminal clear/home, contains one current frame, and ends
with `NO HISTORY`.

`RUNNING` and `COMPLETE` require an exact frame and action. `ERROR` accepts one
concise message and renders no stale lattice.

```sh
candidate=lab/candidates/visual-presentation

swift "$candidate/update_intel_status.swift" \
  "$candidate/fixtures/intel/complete.json" \
  "$candidate/generated/intel/current-status.json"
swift "$candidate/intel_atomic_surface.swift" \
  --input "$candidate/generated/intel/current-status.json" \
  --candidate-root "$candidate" \
  --output "$candidate/generated/intel/current.ansi"

swift "$candidate/test_intel_surface.swift" "$candidate"
```

The Intel surface is an ephemeral overview. The lossless PNG/MOV presenter
remains the evidence master.

## Real accepted evidence

- `generated-adaptive/REAL-ADAPTIVE-ACCEPTANCE.md` documents the frozen
  adaptive-seed-319 states 0–120, source hashes, lossless master, and light
  anatomy option.
- `generated-adaptive/INTEL-DEPLOYMENT.md` gives the exact wired atomic Studio
  → Intel command and its 120-second delayed form.
- `generated-cut-repair/CUT-REPAIR-ACCEPTANCE.md` documents the separate fixed
  cut-and-repair control: disconnected at states 0–17, first connected at 18,
  and connected through 36.
- `cyber-gym-visual-review.md` reviews the existing classical Q lattice without
  changing the benchmark. `cyber_q_intel_snapshot.swift` produces its compact,
  overwrite-only delayed Intel view.

Generated state sequences and lossless movies are ignored by the candidate's
`.gitignore`; manifests, hashes, acceptance JSON, and reports remain inspectable.
