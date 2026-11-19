#!/bin/zsh
set -euo pipefail

seeds=${1:-64}
workers=${2:-8}
result_output=${3:-"simulation/results/repair-seed-1-${seeds}.tsv"}
cycle_output=${4:-"simulation/results/repair-seed-1-${seeds}-cycles.tsv"}
transect=${5:-false}
repair_limit=${6:-1000}
cycles=${7:?provide the observation horizon as argument 7}
repo=${0:A:h:h}
binary="$repo/simulation/reduced-rust/target/release/field_guided_growth"
temporary=$(mktemp -d "${TMPDIR%/}/tin-repair-bootstrap.XXXXXX")

cleanup() {
  if [[ -d "$temporary" && "$temporary" == "${TMPDIR%/}"/tin-repair-bootstrap.* ]]; then
    rm -rf -- "$temporary"
  fi
}
trap cleanup EXIT

mkdir -p "${result_output:h}"
export TIN_REPAIR_BINARY="$binary"
export TIN_REPAIR_TEMPORARY="$temporary"
export TIN_REPAIR_TRANSECT="$transect"
export TIN_REPAIR_LIMIT="$repair_limit"
export TIN_REPAIR_CYCLES="$cycles"

seq 1 "$seeds" | xargs -P "$workers" -n 1 sh -c '
  set -eu
  seed=$1
  prefix="$TIN_REPAIR_TEMPORARY/repair-$seed"
  result=$("$TIN_REPAIR_BINARY" \
    --steps 650 --seed "$seed" --drive 0.7 \
    --light-mode cherenkov --refractive-index 1.33 --beta 0.99 \
    --source-x 0.05 --light-gain 2.2 --light-center 0.5 \
    --repair-cut-radius 3 --repair-transect "$TIN_REPAIR_TRANSECT" \
    --repair-steps "$TIN_REPAIR_LIMIT" --repair-cycles "$TIN_REPAIR_CYCLES" \
    --output "$prefix")
  printf "%s\t%s\n" "$seed" "$result"
' sh > "$temporary/raw.tsv"

{
  printf "seed\tresult\n"
  sort -t $'\t' -k1,1n "$temporary/raw.tsv"
} > "$result_output"

{
  printf "seed\tcycle\tremoved\tsteps\tadded\trepaired\tmetal_cells\n"
  for file in "$temporary"/repair-*.repair.csv; do
    [[ -f "$file" ]] || continue
    stem=${file:t}
    stem=${stem%.repair.csv}
    seed=${stem#repair-}
    tail -n +2 "$file" | while IFS= read -r line; do
      line_with_tabs=${line//,/$'\t'}
      printf "%s\t%s\n" "$seed" "$line_with_tabs"
    done
  done | sort -t $'\t' -k1,1n -k2,2n
} > "$cycle_output"

print -r -- "$result_output"
print -r -- "$cycle_output"
