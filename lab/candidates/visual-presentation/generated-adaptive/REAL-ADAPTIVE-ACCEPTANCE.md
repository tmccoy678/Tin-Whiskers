# Real adaptive presentation acceptance

## Verdict

**GO.** The frozen `adaptive-seed-319` 120-action run is now a literal,
zero-based `0…120` adaptive evidence movie with an exact action-to-result
mapping. State 0 is visibly `INITIAL` with `N/A` stimuli. State `n` from 1
through 120 shows the recorded source action `n-1` that produced topology `n`.

The source contains four `WARMUP` actions and 116 `EXPLOIT` actions. It contains
zero `EXPLORE` actions, so no explore label was invented.

## Master and checks

- Master: `dark/presentation-lossless-rgb.mov`
- Rendered states: `dark/states/topology-0000.png` through
  `topology-0120.png`
- Acceptance: `dark/acceptance.json`
- Render metadata and source hashes: `dark/render-metadata.json` and
  `input/source-evidence.json`

Results:

- 121 rendered states, 1440 x 960;
- 127 decoded frames, uncompressed 24-bit RGB;
- 4 fps, 31.75 seconds;
- exact one-second first/final holds;
- zero rendered anatomy pixel and RGB channel-byte mismatches;
- zero decoded anatomy pixel and RGB channel-byte mismatches across all 127
  movie frames;
- exact left source `1 V` and right sink `0 V` labels;
- SHA-256 coverage for all 121 topology PNGs, actions, audit, metrics, pilot
  summary, and solver boundary input.

## Light anatomy option

`light-anatomy/states/` contains the same 121 occupancy states on an off-white
background with dark occupied cells. The title states `LIGHT ANATOMY · NO
CURRENT/HEAT`; no current or heat field is mixed into it. The checker reports
zero expected transformed-pixel mismatches across the complete sequence.

Human-eye verdict: **GO and materially clearer for fine tendrils.** The light
surface makes retained one-cell branches easier to see while the dark master
remains the literal binary evidence movie. No light movie was emitted, keeping
anatomy mode separate from any current/heat presentation.

## Intel result

`intel/current.ansi` is the atomic COMPLETE view for real state 120. It shows
`ADAPTIVE CONTROLLER`, exact source/sink values, `UPPER ACTIVE`, `LOWER
INACTIVE`, `EXPLOIT`, and the literal 192 x 128 lattice encoded as 96 x 32
Braille cells. `intel/reversal-running-template.json` is intentionally a
template: its placeholder frame must be replaced from the successor's current
frozen manifest before deployment.
