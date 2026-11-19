# Recorded-state ParaView timelines

This route converts one completed Exodus solve per recorded state into a local
ParaView PVD timeline. ParaView plays in `Snap To TimeSteps` mode: one source
state maps to one displayed state, with no interpolated anatomy.

## Cut → repair, epochs 0–36

Build from the ignored source evidence:

```zsh
PV="$HOME/Applications/ParaView-6.2.1-Kitware-arm64.app/Contents/bin/pvpython"
"$PV" build_timeline.py \
  --source-dir ../../../../simulation/work/live_moose/current_fiber_cut_repair \
  --output-dir cut-repair/data \
  --metadata ../../../../simulation/work/live_moose/current_fiber_cut_repair/metrics.tsv \
  --epochs 36 \
  --title "Cut to repair recorded states" \
  --first-connection 18
```

Open locally:

```zsh
./launch-cut-repair-local.sh
```

The timeline opens at disconnected epoch 17. Scrub once to epoch 18 to inspect
the first recorded connected state. The toolbar provides native play, pause,
step, time entry, and scrub controls. Layout tabs retain categorical light
anatomy, exact MOOSE current heat, and exact MOOSE Joule heat. Every layout
carries source/sink, fixed-rule status, stimulus fractions, and the affirmative
label `2D EVIDENCE EXTRUDED FOR 3D INSPECTION`.

## Same route for adaptive 0–120

First prepare state metadata so state `n` records the adaptive action that
actually produced it (`n-1`; state 0 has no prior action):

```zsh
python3 prepare_adaptive_metadata.py \
  --metrics ../../../../simulation/work/live_moose/adaptive-reciprocal-pilot-120/adaptive-seed-319/metrics.tsv \
  --actions ../../../../simulation/work/live_moose/adaptive-reciprocal-pilot-120/adaptive-seed-319/actions.json \
  --output adaptive-seed-319-metadata.tsv
```

Then use the same converter without changing its code:

```zsh
"$PV" build_timeline.py \
  --source-dir ../../../../simulation/work/live_moose/adaptive-reciprocal-pilot-120/adaptive-seed-319 \
  --output-dir adaptive-seed-319/data \
  --metadata adaptive-seed-319-metadata.tsv \
  --epochs 120 \
  --exodus-template 'moose-{epoch:04d}.e' \
  --topology-template 'topology-{epoch:04d}.png' \
  --title "Adaptive seed 319 recorded states"
```

The PVD, converted VTU states, and generated manifest are data products. The
scripts and manifest hashes remain the reproducible route; MP4 is optional
export, never the primary instrument.
