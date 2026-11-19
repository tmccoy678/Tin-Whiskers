#!/bin/zsh
set -euo pipefail

mode="${1:-new}"
script_dir="${0:A:h}"
repo_root="$(cd "$script_dir/../../.." && pwd)"
binary="$script_dir/target/release/long-run-adaptive-screen"
wrapper="$script_dir/run-launchd-wrapper.zsh"
output="$script_dir/output/full"
runtime="$script_dir/runtime/full"
label="com.dobeworks.tinwhiskers.long-run"
domain="gui/$UID/$label"
resume_args=()

case "$mode" in
  new)
    if [[ -e "$runtime/checkpoint.json" || -e "$output/choices.jsonl" ]]; then
      print -u2 "existing full-run state found; use: $0 resume"
      exit 1
    fi
    ;;
  resume)
    [[ -e "$runtime/checkpoint.json" ]] || {
      print -u2 "no checkpoint available to resume"
      exit 1
    }
    resume_args=(--resume)
    ;;
  *)
    print -u2 "usage: $0 [new|resume]"
    exit 1
    ;;
esac

[[ -x "$binary" ]] || {
  print -u2 "release binary missing; run: cargo build --release"
  exit 1
}

if launchctl print "$domain" >/dev/null 2>&1; then
  if launchctl print "$domain" | grep -q 'state = running'; then
    print -u2 "full run is already active"
    exit 1
  fi
  launchctl remove "$label"
fi

mkdir -p "$output" "$runtime"
launchctl submit -l "$label" \
  -o "$runtime/stdout.log" \
  -e "$runtime/stderr.log" -- \
  "$wrapper" "$label" "$binary" run \
  --output "$output" \
  --runtime "$runtime" \
  --actions 120 --substrates 120 --environments 120 \
  --seed 319 --checkpoint-every 120 \
  --pulse-credits-per-trajectory 60 --nice 15 \
  --earth-manifest "$repo_root/lab/candidates/material-manifests/earth-pedot.json" \
  --space-manifest "$repo_root/lab/candidates/material-manifests/space-cbram.json" \
  --sampling-policy "$repo_root/lab/candidates/material-sampler/policy.json" \
  "${resume_args[@]}"

print -r -- "$label" > "$runtime/launchd-label"
launchctl print "$domain" | grep -E 'state =|pid =|last exit code' | head -12
