#!/bin/zsh
set -euo pipefail

moose=/Users/tmccoy678/.local/share/tin-dendrite-moose-env/bin/moose-opt
output=ablation/moose-flux.tsv
printf "topology\tlesion\tmetal_fraction\tjoule_integral\tpeak_current_density\tpeak_joule_density\tterminal_flux\n" > "$output"

for image in ablation/{straight,grid,developed}-*.png; do
  stem=${image:t:r}
  topology=${stem%-*}
  lesion=${stem##*-}
  "$moose" -i voltage_conduction.i Mesh/file="$image" Outputs/file_base="ablation/$stem" > "ablation/$stem.log" 2>&1
  final=$(tail -n 1 "ablation/$stem.csv")
  joule=$(printf "%s" "$final" | cut -d, -f2)
  metal=$(printf "%s" "$final" | cut -d, -f3)
  peak_current=$(printf "%s" "$final" | cut -d, -f4)
  peak_joule=$(printf "%s" "$final" | cut -d, -f5)
  flux=$(printf "%s" "$final" | cut -d, -f6)
  printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$topology" "$lesion" "$metal" "$joule" "$peak_current" "$peak_joule" "$flux" >> "$output"
done

print -r -- "$output"
