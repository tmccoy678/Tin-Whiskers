# Human-eye visual acceptance

## Decision

None of the reviewed surfaces is ready as a standalone, friend-facing presentation.

- `figures/current-driven-remodeling.png` is a **go for internal side-by-side morphology review** and a **no-go as a self-explanatory result**. The before/after change is immediate, but the current path, rails, fixed-rule control status, and meaning of the white cells are not identified.
- `CURRENT_FIBER_REMODEL_LATTICE.mp4` is a **no-go as the foreground evidence movie**. Its source PNGs show the remodeling clearly, but the encoded movie drops fine lattice and title detail and carries stale overlays between frames. The stimulus markers also have no legend.
- `DUAL_FIBER_CHOICE_GROWTH.mp4` is a **go only as a secondary continuous-field diagnostic**. It is a no-go as literal lattice evidence or as an explanation of a two-fiber choice: a viewer sees one bright phase region expand from the left, but no two fibers, two stimuli, choice, or state counter.

The strongest visible result is real and simple: a thin white network develops a broad lower transport corridor while fine branches remain. The current presentation lets a viewer see that change, but not identify the experiment or its causal inputs without narration.

## Surfaces inspected

The review used actual full-resolution image viewing and representative frames decoded from both MP4 files.

| Surface | Local evidence inspected | Metadata |
|---|---|---|
| Static remodeling figure | Full PNG | 1680 x 760 |
| Current-remodel source | Epochs 0, 9, 18, 27, and 36, including the requested 0/18/36 set | 37 PNG states, 1280 x 860 |
| Current-remodel movie | Decoded frames at 0.000, 2.250, 4.500, 6.750, 8.750, and 9.000 s | H.264/AVC, 1280 x 860, 4 fps, 9.25 s, about 65 kb/s |
| Two-fiber field movie | Decoded frames at 0.000, 3.083, 6.250, 9.417, 12.167, and 12.500 s | H.264/AVC, 1200 x 720, 12 fps, 12.584 s, about 37 kb/s |

The 37 current-remodel PNGs at 4 fps and the 151 two-fiber PNGs at 12 fps account for the respective movie durations, consistent with one recorded state per displayed frame. This is a cadence inference from the source counts and asset metadata; it does not establish the simulation time represented by a state.

## What a person sees at laptop distance

### `current-driven-remodeling.png`

**Immediate subject.** The large title and matched epoch panels make this read immediately as a before/after remodeling comparison. White anatomy on black is high-contrast and the broad lower corridor in epoch 24 is unmistakable.

**Causal change.** A viewer can see widening, but cannot see the current field or which boundaries source and receive current. The edge rails appear as unexplained white bars. The picture therefore shows morphological change, while “current-driven” remains a label rather than something visually traceable.

**Legibility.** The title and epoch labels survive laptop scaling. The single long metric line is readable only when the figure is near full-window and is too dense for a glance. Its wording also says “peak stress,” while the lab charter names “peak current density per delivered current.” That may be intended shorthand, but the visual bench cannot determine it; the integrator should resolve the displayed terminology without changing the recorded value.

**Honest detail.** The lattice is sharp and block-literal. The source renderer uses nearest-neighbor resizing, and no smoothing is visible. The fixed deterministic control status is not visible on the figure, which matters because the lab explicitly separates control results from adaptive-AI results.

**Friend test.** A friend can say “the network got much thicker and the listed performance improved.” The figure alone does not let them say what white means, where current enters and exits, or whether this is a fixed control or adaptive AI.

### Current-remodel source frames and movie

**Immediate subject and change.** The lattice occupies nearly the whole frame, the epoch counter is clear, and the lower path visibly thickens from epoch 0 through 36. Four states per second gives the discrete epochs enough separation to be perceived without implying continuous motion.

**Stimulus indicators.** Two small green circles sit left of the lattice. Their active/inactive colors can be seen, but there is no label or legend, so a new viewer cannot know that they are stimuli, which one is active, or whether a dark dot is deliberately off. In the requested source samples, epoch 18 omits the title and both dots; epoch 36 restores them. If “no stimulus” is intentional, it must be written explicitly rather than represented by a missing overlay.

**Encoded-detail failure.** The MP4 does not faithfully preserve its own sharp source frames:

- Source epoch 9 has the complete title; the decoded movie at epoch 9 shows only fragmented title letters and loses thin white detail.
- Source epoch 18 has no title or dots; the decoded movie at epoch 18 carries a complete stale title and both dots forward.
- Source epoch 27 has no title; the decoded movie at epoch 27 carries a short stale title fragment.
- The decoded first and final frames are clean, which makes spot-checking only the endpoints insufficient.

The pattern is consistent with extreme low-bitrate inter-frame compression on high-contrast, rapidly changing pixels. A higher-quality intra-frame re-encode of the exact PNGs is the cheapest check of that diagnosis.

**Friend test.** The main anatomical change is understandable. The alternating cause, control status, and meaning of the stimulus dots are not. The damaged intermediate frames also make the movie look like a rendering fault rather than literal evidence.

### `DUAL_FIBER_CHOICE_GROWTH.mp4`

**Immediate subject.** A viewer sees a black rectangle, a small hot-colored seed at its left edge, and an `eta` field that expands into a broad rounded wedge. The technical title and color bar identify a conductive phase field for an expert, but the title's “two-fiber optical choice” is not embodied in the picture.

**Causal change.** Growth from left to right is obvious at 12 fps. No two candidate fibers, optical stimuli, active choice, source/sink direction, or state number are visible, so the causal comparison is not readable without narration. The first frame is mostly black and can be mistaken for a blank or failed render at normal viewing distance.

**Honest detail.** The soft interface is visibly a continuous scalar field and is labeled with an `eta` color bar. It can remain as a diagnostic, but it cannot replace the literal lattice surface. The existing `dual_lattice_frames` sequence already provides a sharp `eta >= 0.5` threshold view with a state counter; it is the smaller honest foreground surface, though it still needs true stimulus markers and a control-status label to explain the “choice.”

**Friend test.** Without narration, a friend is likely to describe “a hot blob growing from the left.” They cannot identify two fibers or tell what decision the experiment made.

## Reusable go/no-go rubric

Every item below is a gate. A failure makes the surface no-go for foreground presentation even when the solver result is valid.

1. **Immediate subject:** Within three seconds, the title states the material/view, the action, and `FIXED-RULE CONTROL` or `ADAPTIVE CONTROLLER`. A continuous field is labeled `FIELD DIAGNOSTIC — NOT LATTICE`.
2. **Visible cause or honest absence:** Source, sink, and each stimulus have fixed labeled markers. Active, inactive, and off states remain present and visually distinct. If the cause is not shown, the frame says `CAUSE NOT SHOWN` rather than inviting an inference.
3. **Literal evidence:** Occupied cells remain hard-edged cells. Resizing is nearest-neighbor only. No antialiasing, spatial smoothing, cross-fade, optical flow, or interpolated motion may be used to make the anatomy look continuous.
4. **State and cadence:** Every frame carries a monotonically changing epoch/state counter. One recorded state maps to one displayed frame. Exact first and final frames may be repeated for a one-second reading hold; no synthetic in-between states are added.
5. **Legibility:** At the actual presentation size, all essential labels are readable from a normal seated laptop distance without zoom. Long metrics are split into short lines. No key label may depend on a thin low-contrast glyph or color alone.
6. **Decoded integrity:** Compare decoded beginning, middle, stimulus-transition, and final frames with their source PNGs. Missing lattice pixels, stale overlays, fragmented text, or changed state markers are no-go.
7. **Stale/blank/error handling:** A legitimate sparse initial frame still shows title, state, status, and legend. A stopped run shows `COMPLETE` and its final valid frame. A blank player, bare prompt, disconnected page, stack trace, or stale error is never left as the result surface.
8. **Five-second friend test:** Without narration, a fresh viewer can answer: what is this, what changed, what input was active, and is this a fixed control or adaptive AI? Unanswered questions identify the missing label; they are not repaired with a more decorative render.

### Pro immediate-eye presentation

- The evidence figure or movie is the frontmost task window and occupies most of the usable display. Solver terminals, logs, browser errors, and file pickers remain behind it.
- The whole title, lattice/field, legend, and state counter are visible at once. Player controls may not cover the state or stimulus indicators.
- During startup, take temporary screenshots immediately after the surface reaches the foreground, at **+5 minutes**, and at **+10 minutes**. Stop periodic screenshots after two consecutive clean views. Restart the 0/+5/+10 sequence after a new run, a presentation-window replacement, or a display move. Take one final screenshot before handoff.
- If a check is blank, stale, obscured, or errored, refresh/reopen the disposable surface once and then move to the known working surface. Do not leave the failure in front while computation continues.

### Intel ephemeral-terminal presentation

- Use one dedicated foreground terminal screen with an atomic redraw: short title, `RUNNING`/`COMPLETE`/`ERROR`, fixed-control/adaptive status, state counter, literal lattice or one-line result, and stimulus state. Clear the previous screen before publishing the replacement.
- A shell prompt, SSH banner, partial repaint, scrolling log, or traceback is not a presentation. If the process exits normally, the final screen remains `COMPLETE` with the final valid state; if it fails, show a short explicit error state rather than a blank screen.
- Apply the same startup screenshot schedule: foreground at **0 minutes**, then **+5** and **+10 minutes**. Reset the schedule after each new published run or terminal replacement. Keep captures temporary and discard them after acceptance; the Intel surface remains a rolling view, not an archive.
- The terminal is foreground only while it is the intended presentation. Background computation and old result windows must not be allowed to cover or visually compete with it.

## Smallest visual changes

1. **Re-encode the current-remodel movie from the exact PNGs at the same 1280 x 860 and 4 fps using a high-quality intra-frame or lossless master.** Add no filters, resampling, tweening, or interpolated frames. Decode epochs 9, 18, and 27 as the acceptance check; they must match their source overlays and preserve thin lattice cells.
2. **Make overlays deterministic on every source frame.** Keep the full title, `FIXED-RULE CONTROL`, epoch/state, both labeled stimulus markers, and a tiny active/inactive/off legend in fixed positions. A deliberate off interval should say `OFF`; it should not make the title or markers disappear.
3. **Add only orientation labels to the static figure.** Identify white occupied cells and the current source/sink rails, and add `FIXED-RULE CONTROL`. Break the metrics into two short lines. Resolve the visible “stress”/“current density” terminology at integration time without changing the recorded number or scientific claim.
4. **Use the existing literal `dual_lattice_frames` sequence as the two-fiber foreground and retain the smooth `eta` movie as a separately labeled field diagnostic.** Add exact stimulus locations, active-state indication, and fixed-control/adaptive status only when those values are available from the recorded run; never invent them from appearance.
5. **Repeat exact endpoints for reading time.** Hold the first and final recorded frames for one second by frame repetition. This improves comprehension without smoothing, interpolation, or a physics change.
