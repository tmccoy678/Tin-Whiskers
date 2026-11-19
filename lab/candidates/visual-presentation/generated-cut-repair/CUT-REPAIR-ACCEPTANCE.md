# Cut-and-repair fixed-control acceptance

## Verdict

**GO as a separate evidence candidate.** This movie is titled `CUT AND REPAIR`
and never shares a title, manifest, output directory, or source record with the
earlier widening movie.

The metrics and frame set establish:

- source states 0–17: `DISCONNECTED`;
- source state 18: first `CONNECTED` state;
- source states 18–36: continuously `CONNECTED`.

The status appears directly beside `PROBE · FIXED` on every frame. State labels
remain zero-based, so the first connected frame visibly reads `STATE 018 OF
036`.

## Master and checks

- Master: `evidence/presentation-lossless-rgb.mov`
- States: `evidence/states/frame.0000.png` through `frame.0036.png`
- Acceptance: `evidence/acceptance.json`
- Source hashes and connection record: `input/source-evidence.json`

Results:

- 37 rendered states and 43 decoded frames;
- 1440 x 960, 4 fps, 10.75 seconds;
- zero rendered or decoded anatomy pixel/channel-byte mismatches;
- exact one-second endpoint holds;
- visible fixed-control, source/sink, probe, and connection labels.
