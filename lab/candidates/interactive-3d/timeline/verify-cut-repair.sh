#!/bin/zsh
set -eu
here=${0:A:h}
app=${PARAVIEW_APP:-}
if [[ -z "$app" ]]; then
  for candidate in \
    "$HOME/Applications/ParaView-6.2.1-Kitware-arm64.app" \
    "/Applications/ParaView-6.2.1-Kitware-arm64.app"; do
    if [[ -x "$candidate/Contents/bin/pvpython" ]]; then
      app=$candidate
      break
    fi
  done
fi
if [[ -z "$app" || ! -x "$app/Contents/bin/pvpython" ]]; then
  print -u2 "Pristine ParaView 6.2.1 pvpython was not found."
  exit 1
fi
exec "$app/Contents/bin/pvpython" "$here/verify_timeline.py"
