#!/bin/bash
# usage: [C3_SEED=n] terrain_make.sh [install] ID...
# Renders terrain tiles (terrain.py, coloured by their own original) at 8x, scales to 2x, checks them and saves
# each as an attempt (out/attempts/ID/<time>/). With "install" a passing attempt is copied to ~/caesar3/hd/c3/
# (central climate only: other climates have other grass); a failing one leaves the game as it is.
# Tiles whose original has a part above the diamond (trees on shores) are skipped: terrain.py renders flat ground.
cd "$(dirname "$0")"; mkdir -p out
B=/Applications/Blender.app/Contents/MacOS/Blender; P=~/.local/share/uv/tools/mflux/bin/python
$P test_check.py >/dev/null || { echo "check.py regression tests failed: fix check.py first"; exit 1; }
INSTALL=0; [ "$1" = install ] && { INSTALL=1; shift; }
pass=0; fail=0; skip=0; SEED0=$C3_SEED
for ID in "$@"; do
  H=$($P -c "from PIL import Image; print(Image.open('../originals/$ID.png').height)")
  if [ "$H" != 30 ]; then echo "skip $ID (height $H: has a part above the tile)"; skip=$((skip+1)); continue; fi
  export C3_SEED=${SEED0:-$ID}
  $B -b -P terrain.py -- $PWD/out/${ID}_8.png 8 -- $ID $PWD/../originals/$ID.png 2>&1 | grep -E "rror:" || true
  $P -c "from PIL import Image; im=Image.open('out/${ID}_8.png'); im.resize((im.width//4, im.height//4), Image.LANCZOS).save('out/${ID}.png')"
  $P post.py out/${ID}.png
  $P cmp.py out/${ID}_8.png ../originals/$ID.png out/${ID}_cmp.png
  if CHECK_JSON=out/${ID}_check.json $P check.py ../originals/$ID.png out/${ID}.png 0 > out/${ID}_check.txt; then
    pass=$((pass+1)); $P attempt.py save $ID $C3_SEED terrain >/dev/null
    if [ $INSTALL = 1 ]; then $P attempt.py install $ID latest >/dev/null; fi
  else
    fail=$((fail+1)); $P attempt.py save $ID $C3_SEED terrain >/dev/null; echo "FAIL $ID: $(tail -1 out/${ID}_check.txt)"
  fi
done
echo "pass $pass, fail $fail, skipped $skip"
$P ../viewer/build_viewer.py
