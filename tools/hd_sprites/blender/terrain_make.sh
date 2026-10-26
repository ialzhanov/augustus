#!/bin/bash
# usage: [C3_SEED=n] [C3_CLIMATE=c3|c3_north|c3_south] terrain_make.sh [install] ID...
# Renders terrain tiles (terrain.py, coloured by their own original) at 8x, scales to 2x, checks them and saves
# each as an attempt (out/attempts/[climate/]ID/<time>/). With "install" a passing attempt is copied to
# ~/caesar3/hd/<climate>/ (each climate has its own terrain originals); a failing one leaves the game as it is.
# Tiles whose original has a part above the diamond (trees on shores) are skipped: terrain.py renders flat ground.
cd "$(dirname "$0")"
B=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}; P=~/.local/share/uv/tools/mflux/bin/python
$P test_check.py >/dev/null || { echo "check.py regression tests failed: fix check.py first"; exit 1; }
INSTALL=0; [ "$1" = install ] && { INSTALL=1; shift; }
export C3_CLIMATE=${C3_CLIMATE:-c3}
SUB=$($P -c "import sys; sys.path.insert(0, '..'); from sg import sub; print(sub('$C3_CLIMATE') or '.')"); O=out/$SUB; mkdir -p $O
pass=0; fail=0; skip=0; SEED0=$C3_SEED
for ID in "$@"; do
  ORIG=$($P -c "import sys; sys.path.insert(0, '..'); from sg import orig_path; print(orig_path('$C3_CLIMATE', $ID))")
  read -r Wd H <<< "$($P -c "from PIL import Image; im=Image.open('$ORIG'); print(im.width, im.height)")"
  if [ "$H" != $(( 30 * ((Wd + 2) / 60) )) ]; then echo "skip $ID (height $H: has a part above the tile)"; skip=$((skip+1)); continue; fi
  export C3_SEED=${SEED0:-$ID}
  rm -f $O/${ID}_8.png $O/${ID}.png   # a failed render must not leave an old image to check
  $B -b -P terrain.py -- $PWD/$O/${ID}_8.png 8 -- $ID $ORIG 2>&1 | grep -E "rror:" || true
  if [ ! -f $O/${ID}_8.png ]; then echo "FAIL $C3_CLIMATE $ID: render failed, no attempt saved"; fail=$((fail+1)); continue; fi
  $P -c "from PIL import Image; im=Image.open('$O/${ID}_8.png'); im.resize((im.width//4, im.height//4), Image.LANCZOS).save('$O/${ID}.png')"
  $P post.py $O/${ID}.png
  $P cmp.py $O/${ID}_8.png $ORIG $O/${ID}_cmp.png
  if CHECK_JSON=$O/${ID}_check.json $P check.py $ORIG $O/${ID}.png 0 > $O/${ID}_check.txt; then
    pass=$((pass+1)); $P attempt.py save $ID $C3_SEED terrain $C3_CLIMATE >/dev/null
    if [ $INSTALL = 1 ]; then $P attempt.py install $ID latest $C3_CLIMATE >/dev/null; fi
  else
    fail=$((fail+1)); $P attempt.py save $ID $C3_SEED terrain $C3_CLIMATE >/dev/null; echo "FAIL $C3_CLIMATE $ID: $(tail -1 $O/${ID}_check.txt)"
  fi
done
echo "pass $pass, fail $fail, skipped $skip"
$P ../viewer/build_viewer.py
