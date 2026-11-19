# Rust presentation-buffer hierarchy

## Objective

Keep Studio and Pro available for scientific computation while exact ordered
states move through bounded human-facing buffers: Pro as the many-state
scientific relay, TV as a 24-page AS/400-style review surface, and Intel as an
eight-state delayed end terminal. Every receiver verifies sequence and hash,
memory remains fixed, delivery is atomic, and persistence occurs only when an
explicit post-run artifact is requested.

The existing `intel-ceremony-terminal` candidate already validates the final
stage: fixed `80 × 24` screens, a declared one-second delay, eight in-memory
pending states, atomic wired SSH delivery, source fingerprinting, and an Intel
viewer footprint of `944 KB` RSS and `0.1%` CPU beside Rill.

## Smallest Rust hierarchy

Extend that crate into one library and three binaries:

```text
intel-ceremony-terminal/
├── src/lib.rs                 # envelope, fixed ring, ACK, hash/order checks
├── src/bin/studio-publisher.rs
├── src/bin/pro-buffer.rs      # 256-state scientific ring and fan-out
└── src/bin/intel-viewer.rs    # 8-state delayed 80×24 terminal
```

The TV receives a tiny presentation client built from the same library as
Rust/WASM when Tizen admits it; the Pro retains the identical 24-page ring and
pushes the current page when the TV surface is display-only. This preserves one
ordering implementation and keeps the television client minimal.

## Canonical envelope

Every scientific or presentation state travels inside one strict envelope:

```text
schema_version
run_id
stream_id                 # scientific, tv-presentation, intel-terminal
source_sequence           # canonical Studio state number
stream_sequence           # consecutive within this selected stream
previous_envelope_sha256
payload_sha256
payload_kind              # exact-state, page-80x24, terminal-80x24
payload_length
created_monotonic_ns
display_after_monotonic_ns
evidence_class
payload
```

Studio assigns `source_sequence` exactly once. Pro preserves it and assigns a
separate consecutive sequence to each presentation stream. TV and Intel accept
the next expected `stream_sequence`, verify both hashes and the declared byte
length, insert atomically, then acknowledge that sequence. Duplicate delivery
returns the existing acknowledgement; a gap holds the new page until the
missing sequence arrives.

## Roles and bounds

| Surface | Default ring | Payload | Function | Persistence |
|---|---:|---:|---|---|
| Studio | current state plus sender window | exact scientific envelope | Compute and publish one canonical sequence | Canonical run output only |
| Pro | `256` states | max `512 KiB` each (`128 MiB` total) | Many-state exact buffer, verification, TV/Intel selection, replay | RAM; clears at run end |
| TV | `24` pages | max `8 KiB` each (`192 KiB` total) | AS/400-style current page plus previous/next review | RAM; clears on session close |
| Intel | `8` pages | max `8 KiB` each (`64 KiB` total) | Delayed end-terminal ceremony | RAM plus one atomically replaced current page |

All capacities and payload ceilings live in one hashed session manifest. A
full downstream ring applies acknowledgement backpressure to its dedicated Pro
sender. Scientific computation continues into the Pro ring; if the Pro ring
reaches capacity before a consumer advances, that presentation stream enters a
visible `BUFFER PAUSED` state and preserves its ordered pages for review.

## Ordered delivery path

```text
Studio compute
  └─ verified Thunderbolt route → Pro 256-state ring
       ├─ selected presentation pages → TV 24-page ring
       └─ selected terminal pages → verified Ethernet → Intel 8-state delay ring
```

At session start, each sender runs the existing route preflight and records the
selected interface and negotiated/class link rate in the session manifest.
Studio–Pro uses the verified Thunderbolt route; Intel uses its verified wired
alias. TV earns the `wired` label after its live endpoint verifies a wired
path; atomic sequencing and hash checks apply on every admitted transport.

Delivery writes `page.tmp`, synchronizes it, verifies SHA-256, renames it into
the fixed queue slot, then updates `current` by atomic rename. The receiver
acknowledges only after ring insertion. Consumed Intel queue slots and expired
TV/Pro slots are released immediately. One `current` page remains as the
recoverable display surface.

## Human-rate selection

The Pro router derives two declared subsets from the canonical Studio stream:

- **TV stream:** milestones, consequence changes, first connection/repair,
  periodic exact states, and final result, capped at the TV cadence.
- **Intel stream:** current choice/action, throughput, conservation, and one
  focused exact map, capped at `2–4 Hz` with the declared human delay.

Selection is deterministic from the session manifest and retains the original
`source_sequence`. Every delivered page therefore has a precise canonical
parent while human-rate streams remain bounded.

## Optional post-run MP4

MP4 generation is a separate post-run command. It consumes a finite,
hash-verified presentation bundle from the Pro ring snapshot or a deterministic
replay of selected scientific states. The renderer records input hashes,
cadence, frame mapping, codec, dimensions, and output SHA-256. The movie enters
`Results/` only after an explicit request; ordinary live sessions retain no
movie or rolling frame archive.

## Acceptance tests

1. **Exact order:** shuffled delivery produces the original consecutive display
   order after acknowledgements resolve the gap.
2. **Duplicate identity:** replaying one envelope changes neither ring depth nor
   display count and returns the same ACK.
3. **Hash integrity:** one changed byte is rejected before insertion.
4. **Atomicity:** interruption before rename leaves the prior current page fully
   readable; restart admits the complete temporary successor once.
5. **Memory bound:** sustained input holds Pro at 256, TV at 24, and Intel at 8
   slots within their declared byte ceilings.
6. **Backpressure:** a paused consumer preserves ordered states and leaves the
   compute loop responsive.
7. **Delay:** Intel displays each page after the declared delay within one
   viewer poll interval.
8. **Reconnect:** sender resumes from the last acknowledged sequence and
   reproduces the uninterrupted page hashes.
9. **Selection trace:** every TV/Intel page names an existing canonical Studio
   source sequence and payload hash.
10. **Ephemeral completion:** after the viewing horizon, rings contain zero
    consumed pages, one current page, and no routine history log.

## Smallest refinement to the current candidate

The current viewer already bounds its in-memory queue at eight. The matching
publisher refinement adds an eight-slot acknowledged remote window, checks
capacity before atomic insertion, and waits on the Pro ring when Intel is full.
This closes the complete path with fixed disk and memory use while preserving
every selected terminal state in order.
