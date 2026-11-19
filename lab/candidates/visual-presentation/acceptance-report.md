# Fixed-control presentation acceptance

## Verdict

**GO as a human-facing fixed-control candidate.** The decoded movie gives a
friend the subject, control status, source/sink direction, upper/lower stimulus
state, literal occupied lattice, and epoch without narration. The broad lower
transport corridor is visible as it forms, while retained fine branches remain
sharp.

The candidate is presentation-only. It copies the existing lattice anatomy
verbatim and changes no topology, physics, metric, action, or canonical result.

## Accepted outputs

- Renderer: `render_candidate.swift`
- Automated acceptance: `check_candidate.swift`
- Pixel-exact state master: `generated/states/frame.0000.png` through
  `generated/states/frame.0036.png`
- Lossless movie master:
  `generated/current-fiber-remodel-presentation-lossless-rgb.mov`
- Decoded representatives: `generated/decoded/state.0009.png`,
  `state.0018.png`, and `state.0027.png`
- Machine-readable result: `generated/check-results.json`

## Encode result

| Property | Result |
|---|---:|
| Movie codec | Uncompressed 24-bit RGB in MOV |
| Resolution | 1440 x 960 |
| Cadence | 4 fps |
| Source states | 37 |
| Movie frames | 43 |
| Duration | 10.75 s |
| First-state hold | 4 exact frames / 1.00 s |
| Final-state hold | 4 exact frames / 1.00 s |
| File size | 182,293,431 bytes |
| Interpolation, tweening, smoothing | None |

The movie is intentionally large because the tested compressed alternatives
did not preserve literal hard-edge anatomy. A ProRes 4444 trial changed roughly
5,700–6,100 anatomy pixels in representative frames; a maximum-quality,
all-keyframe H.264 trial changed substantially more. Both rejected trial movies
were removed. The uncompressed master is the smallest tested route that passes
the literal-pixel requirement.

## Automated acceptance result

The checker passed all gates:

- 37 rendered PNGs at 1440 x 960;
- 43 decoded movie frames at 4 fps and 10.75 seconds;
- fixed title/control, source/sink, and legend regions on every state;
- nonempty stimulus and epoch text regions on every state;
- zero anatomy-pixel and channel-byte mismatches across all 37 rendered PNGs;
- zero decoded anatomy-pixel and channel-byte mismatches for states 9, 18,
  and 27;
- zero anatomy mismatches in all four opening and four closing hold frames;
- uncompressed 24-bit RGB track subtype.

Representative decoded comparisons:

| State | Movie frame | Pixel mismatches | RGB channel-byte mismatches |
|---:|---:|---:|---:|
| 9 | 12 | 0 | 0 |
| 18 | 21 | 0 | 0 |
| 27 | 30 | 0 | 0 |

## Human-eye result

At laptop distance, the title and `FIXED-RULE CONTROL · LITERAL LATTICE`
classification are immediate. Source and sink labels sit directly above their
rails. Upper and lower indicators remain visible on every frame, including
states whose original title and dots were absent. `ACTIVE`, `INACTIVE`, and
`OFF` are both spelled out beside the indicator and shown in the legend. The
state counter and white-cell key are legible without competing with a metric
line.

The 4 fps motion remains intentionally stepped. The one-second exact endpoint
holds give time to read the initial and final states without generating any
intermediate anatomy.

The discrete stimulus labels are derived from the existing source indicator
pixel: black is `OFF`, green intensity 180 or higher is `ACTIVE`, and other
nonzero green is `INACTIVE`. This is a presentation classification of the
recorded indicator, not a new stimulus or physics claim.

## Smallest adaptive-controller reuse

Do not modify or wait for the running reciprocal pilot. Once its final topology
frames and recorded actions exist, the literal renderer needs only these narrow
changes:

1. Parameterize the subtitle as `FIXED-RULE CONTROL` or `ADAPTIVE CONTROLLER`;
   keep the anatomy copy and lossless encode path unchanged.
2. Read upper/lower/off status from the completed action record rather than
   sampling legacy indicator colors. Require one recorded action entry for each
   displayed state and fail closed on a missing or duplicate state.
3. Set the state counter denominator from the completed frame/action manifest;
   do not assume that a planned 120 actions all completed.
4. Point the renderer at the completed adaptive PNGs only after verifying their
   anatomy rectangle. If its bounds differ, pass explicit source bounds; never
   resize or infer them from appearance.
5. Retain `SOURCE · 1 V` and `SINK · 0 V` only if the completed run manifest
   records those values. Otherwise render the recorded boundary values.
6. Reuse the same decoded frame-count, fixed-text, endpoint-hold, and zero-pixel
   anatomy checks, sampling the beginning, middle, action transition, and final
   adaptive states.

No adaptive wording should appear until the final action/topology provenance is
present. The current candidate remains strictly the fixed-rule control.
