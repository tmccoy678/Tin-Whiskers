#!/bin/zsh
set -eu
here=${0:A:h}
cd "$here"
python3 prepare_seed.py \
  ../interactive-3d/data/topology-0120.png \
  seed/seed_cells.tsv \
  seed/manifest.json
cargo run --release -- --simulate seed/seed_cells.tsv output
