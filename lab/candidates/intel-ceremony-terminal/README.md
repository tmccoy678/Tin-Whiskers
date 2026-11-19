# Intel ceremony terminal

One Rust publisher on Studio and one Rust viewer on Intel form a wired,
unattended terminal surface. Studio and Pro remain compute/sensing bodies; the
Intel displays one delayed atomic state.

Properties:

- fixed `80 × 24` AS/400-style screen;
- explicit millisecond human delay;
- one current state and up to eight pending states in Intel memory, sized for a
  one-second human delay at a 2–4 Hz display cadence;
- atomic remote replacement over the verified wired SSH route;
- source fingerprint and delay printed on every screen;
- no rolling history or activity log.

`blu-studio-publisher SOURCE blu-intel-lan 250` watches one source file and
publishes every changed state into the Intel queue at the declared polling
interval.

`blu-intel-viewer /Users/agar/.blu-ephemeral/current.ansi 1000` applies the
declared human delay, displays queued states in arrival order through a
fixed-size terminal surface, and forgets each consumed state.

## Working hierarchy

- **Studio:** scientific computation and source state.
- **Pro:** future many-state scientific buffer and sensing surface.
- **TV:** future 24-page human presentation buffer.
- **Intel:** eight-page end queue and current AS/400-style terminal.

The terminal path retains text states only. Optional MP4s are rendered after a
run from scientific states and remain separate, disposable presentation files.

## Live acceptance

The Studio arm64 publisher and Intel x86_64 viewer were built from the same
crate and deployed over Intel's verified wired route. A changed source crossed
the link with matching SHA-256, appeared after the declared one-second delay,
and left queue depth zero after consumption. The Intel viewer used `944 KB`
RSS and `0.1%` CPU beside active Rill computation.
