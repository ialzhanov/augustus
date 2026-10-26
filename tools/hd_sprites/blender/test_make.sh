#!/bin/bash
# A failed Blender render must not save an attempt (make.sh and terrain_make.sh once checked the previous image again).
cd "$(dirname "$0")"
count() { ls out/attempts/$1 2>/dev/null | wc -l; }
for t in "make.sh tent.py 2779" "terrain_make.sh 306"; do
  id=${t##* }; before=$(count $id)
  BLENDER=false ./$t >/dev/null 2>&1
  [ "$(count $id)" = "$before" ] || { echo "FAIL: $t saved an attempt after a failed render"; exit 1; }
done
echo "ok: no attempt after a failed render"
