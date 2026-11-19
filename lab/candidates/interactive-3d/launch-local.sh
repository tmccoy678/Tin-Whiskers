#!/bin/zsh
set -eu

here=${0:A:h}
app=${PARAVIEW_APP:-}
if [[ -z "$app" ]]; then
  for candidate in \
    "$HOME/Applications/ParaView-6.2.1-Kitware-arm64.app" \
    "/Applications/ParaView-6.2.1-Kitware-arm64.app" \
    "$HOME/Applications/ParaView-6.2.1.app" \
    "/Applications/ParaView-6.2.1.app"; do
    if [[ -x "$candidate/Contents/MacOS/paraview" ]]; then
      app=$candidate
      break
    fi
  done
fi
if [[ -z "$app" || ! -x "$app/Contents/MacOS/paraview" ]]; then
  print -u2 "ParaView 6.2.1 was not found. Set PARAVIEW_APP to its app bundle."
  exit 1
fi

exec open -na "$app" --env "TIN_VIZ_ROOT=$here" --args --script="$here/open_scene.py"
