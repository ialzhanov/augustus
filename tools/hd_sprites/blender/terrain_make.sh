#!/bin/bash
# usage: terrain_make.sh [install] ID...
# Renders terrain tiles (terrain.py, coloured by their own original) at 8x, scales to 2x, checks them, and with
# "install" copies passing tiles to ~/caesar3/hd/c3/ (central climate only: other climates have other grass).
# Tiles whose original has a part above the diamond (trees on shores) are skipped: terrain.py renders flat ground.
cd "$(dirname "$0")"; mkdir -p out
B=/Applications/Blender.app/Contents/MacOS/Blender; P=~/.local/share/uv/tools/mflux/bin/python
$P test_check.py >/dev/null || { echo "check.py regression tests failed: fix check.py first"; exit 1; }
INSTALL=0; [ "$1" = install ] && { INSTALL=1; shift; }
pass=0; fail=0; skip=0
for ID in "$@"; do
  H=$($P -c "from PIL import Image; print(Image.open('../originals/$ID.png').height)")
  if [ "$H" != 30 ]; then echo "skip $ID (height $H: has a part above the tile)"; skip=$((skip+1)); continue; fi
  $B -b -P terrain.py -- $PWD/out/${ID}_8.png 8 -- $ID $PWD/../originals/$ID.png 2>&1 | grep -E "rror:" || true
  $P -c "from PIL import Image; im=Image.open('out/${ID}_8.png'); im.resize((im.width//4, im.height//4), Image.LANCZOS).save('out/${ID}.png')"
  $P post.py out/${ID}.png
  if $P check.py ../originals/$ID.png out/${ID}.png 0 > out/${ID}_check.txt; then
    pass=$((pass+1))
    if [ $INSTALL = 1 ]; then mkdir -p ~/caesar3/hd/c3; cp out/${ID}.png ~/caesar3/hd/c3/$ID.png; fi
  else
    fail=$((fail+1)); echo "FAIL $ID: $(tail -1 out/${ID}_check.txt)"
    rm -f ~/caesar3/hd/c3/$ID.png
  fi
done
echo "pass $pass, fail $fail, skipped $skip"
$P ../viewer/build_viewer.py
