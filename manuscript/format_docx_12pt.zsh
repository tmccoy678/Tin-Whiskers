#!/bin/zsh
set -euo pipefail

if (( $# != 2 )); then
  print -u2 "usage: $0 input.docx output.docx"
  exit 2
fi

input=${1:A}
output=${2:A}
work=$(/usr/bin/mktemp -d /tmp/adaptive-abstract-docx.XXXXXX)
trap '/bin/rm -rf "$work"' EXIT

cd "$work"
/usr/bin/unzip -q "$input"

/usr/bin/perl -0pi -e '
  s{<w:sz w:val="[0-9]+"\s*/>}{<w:sz w:val="24"/>}g;
  s{<w:szCs w:val="[0-9]+"\s*/>}{<w:szCs w:val="24"/>}g;
  s{<w:rFonts\b[^>]*/>}{<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="Times New Roman" w:cs="Times New Roman"/>}g;
' word/styles.xml word/document.xml

/usr/bin/perl -0pi -e '
  s{<dc:creator>.*?</dc:creator>}{<dc:creator>Anonymous</dc:creator>}s;
  s{<cp:lastModifiedBy>.*?</cp:lastModifiedBy>}{<cp:lastModifiedBy>Anonymous</cp:lastModifiedBy>}s;
  s{<dc:title>.*?</dc:title>}{<dc:title>Adaptive Control of Developing Conductive Topology</dc:title>}s;
  s{<cp:revision>.*?</cp:revision>}{<cp:revision>1</cp:revision>}s;
' docProps/core.xml

/bin/rm -f "$output"
/usr/bin/zip -X -qr "$output" .
/usr/bin/unzip -t "$output" >/dev/null
print "$output"
