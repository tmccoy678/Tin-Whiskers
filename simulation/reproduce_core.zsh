#!/bin/zsh
set -euo pipefail

repo=${0:A:h:h}
moose=${MOOSE_BIN:-/Users/tmccoy678/.local/share/tin-dendrite-moose-env/bin/moose-opt}
output="$repo/simulation/output/reproduce"
mkdir -p "$output"

[[ -x "$moose" ]] || { print -u2 "MOOSE binary not executable: $moose"; exit 1; }

cargo build --release --manifest-path "$repo/simulation/reduced-rust/Cargo.toml"

cargo run --release --manifest-path "$repo/simulation/reduced-rust/Cargo.toml" -- \
  --steps 650 --seed 319 --drive 0.7 --light-gain 0 \
  --output "$output/baseline"

cargo run --release --manifest-path "$repo/simulation/reduced-rust/Cargo.toml" -- \
  --steps 650 --seed 319 --drive 0.7 \
  --light-mode cherenkov --refractive-index 1.33 --beta 0.99 \
  --source-x 0.05 --light-gain 2.2 --light-center 0.5 \
  --output "$output/cherenkov"

baseline_hash=$(shasum -a 256 "$output/baseline.metal.pgm" | awk '{print $1}')
cherenkov_hash=$(shasum -a 256 "$output/cherenkov.metal.pgm" | awk '{print $1}')
[[ "$baseline_hash" == c08c25ab3f6d4ed71f7908e6b27472d490782b2663c04021ae4f33058ad98d49 ]]
[[ "$cherenkov_hash" == 25f14e8667197b0f266e365ef25ff0e142c1e9131bd4d5cfd5fb2cfea16dc6fa ]]

cp "$output/cherenkov.metal.pgm" "$repo/simulation/output/cherenkov.metal.pgm"
(
  cd "$repo/simulation/voltage-routing"
  Rscript generate_fixed_topologies.R
  for topology in straight-wire parallel-grid grown-cherenkov; do
    "$moose" -i voltage_conduction.i \
      Mesh/file="topologies/${topology}.png" \
      Outputs/file_base="reproduce-${topology}" \
      > "reproduce-${topology}.log" 2>&1
  done
)

straight=$(tail -n 1 "$repo/simulation/voltage-routing/reproduce-straight-wire.csv" | cut -d, -f6)
grid=$(tail -n 1 "$repo/simulation/voltage-routing/reproduce-parallel-grid.csv" | cut -d, -f6)
grown=$(tail -n 1 "$repo/simulation/voltage-routing/reproduce-grown-cherenkov.csv" | cut -d, -f6)

Rscript -e "stopifnot(abs($straight - 0.015861522654378) < 1e-9,
                      abs($grid - 0.079304851383882) < 1e-9,
                      abs($grown - 0.0041372392954523) < 1e-9)"

if [[ ${FULL:-0} == 1 ]]; then
  "$repo/simulation/bootstrap_paired.zsh" 128 8 "$output/paired-seeds.tsv"
  "$repo/simulation/bootstrap_repair.zsh" \
    64 8 "$output/transect-seeds.tsv" "$output/transect-cycles.tsv" true 1500 6
fi

print -r -- "Reproduced commit: $(git -C "$repo" rev-parse HEAD)"
print -r -- "baseline_sha256=$baseline_hash"
print -r -- "cherenkov_sha256=$cherenkov_hash"
print -r -- "flux_straight=$straight"
print -r -- "flux_grid=$grid"
print -r -- "flux_grown=$grown"
