#!/bin/zsh
set -eu
here=${0:A:h}
app=${PARAVIEW_APP:-}
if [[ -z "$app" ]]; then
  for candidate in \
    "$HOME/Applications/ParaView-6.2.1-Kitware-arm64.app" \
    "/Applications/ParaView-6.2.1-Kitware-arm64.app"; do
    if [[ -x "$candidate/Contents/MacOS/paraview" ]]; then
      app=$candidate
      break
    fi
  done
fi
if [[ -z "$app" || ! -x "$app/Contents/MacOS/paraview" ]]; then
  print -u2 "Pristine ParaView 6.2.1 was not found."
  exit 1
fi
exec open -na "$app" --env "TIMELINE_VIZ_ROOT=$here" --args --script="$here/open_timeline_scene.py"
