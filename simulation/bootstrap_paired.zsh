#!/bin/zsh
set -euo pipefail

pairs=${1:-128}
workers=${2:-8}
output=${3:-"simulation/results/paired-seed-1-${pairs}.tsv"}
repo=${0:A:h:h}
binary="$repo/simulation/reduced-rust/target/release/field_guided_growth"
temporary=$(mktemp -d "${TMPDIR%/}/tin-bootstrap.XXXXXX")

cleanup() {
  if [[ -d "$temporary" && "$temporary" == "${TMPDIR%/}"/tin-bootstrap.* ]]; then
    rm -rf -- "$temporary"
  fi
}
trap cleanup EXIT

mkdir -p "${output:h}"
jobs="$temporary/jobs.tsv"
raw="$temporary/raw.tsv"

for seed in $(seq 1 "$pairs"); do
  printf "baseline\t%s\n" "$seed"
  printf "cherenkov\t%s\n" "$seed"
done > "$jobs"

export TIN_SWEEP_BINARY="$binary"
export TIN_SWEEP_TEMPORARY="$temporary"

xargs -P "$workers" -n 2 sh -c '
  set -eu
  condition=$1
  seed=$2
  prefix="$TIN_SWEEP_TEMPORARY/$condition-$seed"
  if [ "$condition" = baseline ]; then
    result=$("$TIN_SWEEP_BINARY" \
      --steps 650 --seed "$seed" --drive 0.7 \
      --light-gain 0.0 --output "$prefix")
  else
    result=$("$TIN_SWEEP_BINARY" \
      --steps 650 --seed "$seed" --drive 0.7 \
      --light-mode cherenkov --refractive-index 1.33 --beta 0.99 \
      --source-x 0.05 --light-gain 2.2 --light-center 0.5 \
      --output "$prefix")
  fi
  printf "%s\t%s\t%s\n" "$condition" "$seed" "$result"
' sh < "$jobs" > "$raw"

{
  printf "condition\tseed\tresult\n"
  sort -t $'\t' -k2,2n -k1,1 "$raw"
} > "$output"

print -r -- "$output"
