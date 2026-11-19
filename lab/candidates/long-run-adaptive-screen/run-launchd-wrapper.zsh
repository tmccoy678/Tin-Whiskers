#!/bin/zsh
set +e

label="$1"
shift
"$@"
run_status=$?

# `launchctl submit` otherwise reschedules the exited command. Removing the
# transient job here leaves completed or failed runs quiescent.
launchctl remove "$label" >/dev/null 2>&1 || true
exit "$run_status"
