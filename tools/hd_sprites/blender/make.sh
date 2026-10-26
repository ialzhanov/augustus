#!/bin/bash
# usage: make.sh SCRIPT ID [install] [force]
# Renders SCRIPT for sprite ID at 8x (+ top part when the original has one), scales it to 2x (the game's
# closest zoom is 200%, so 2x is the most it can show; 2:1 bilinear at 100% is a clean box filter),
# sharpens lightly, runs check.py, and with "install" copies the 2x files to ~/caesar3/hd/*/ only when
# every check passes.
cd "$(dirname "$0")"; mkdir -p out
B=/Applications/Blender.app/Contents/MacOS/Blender; P=~/.local/share/uv/tools/mflux/bin/python
$P test_check.py >/dev/null || { echo "check.py regression tests failed: fix check.py first"; exit 1; }
S=$1; ID=$2; DENSITY=${DENSITY:-2}
TOP=$($P -c "import sys, os; sys.path.insert(0, '..'); from sg import SG; print(SG(os.path.expanduser('~/caesar3'), 'C3').img[$ID]['top'])")
$B -b -P $S -- $PWD/out/${ID}_8.png 8 -- $ID 2>&1 | grep -E "rror:" || true
rm -f out/${ID}_8top.png out/${ID}_top.png
if [ "$TOP" != 0 ]; then $B -b -P $S -- $PWD/out/${ID}_8top.png 8 top -- $ID 2>&1 | grep -E "rror:" || true; fi
$P -c "
from PIL import Image; import os
for src, dst in (('out/${ID}_8.png', 'out/${ID}.png'), ('out/${ID}_8top.png', 'out/${ID}_top.png')):
    if os.path.exists(src):
        im = Image.open(src); im.resize((im.width * $DENSITY // 8, im.height * $DENSITY // 8), Image.LANCZOS).save(dst)"
$P post.py out/${ID}.png $([ -f out/${ID}_top.png ] && echo out/${ID}_top.png)
$P cmp.py out/${ID}_8.png ../originals/$ID.png out/${ID}_cmp.png
echo "== $ID"
if $P check.py ../originals/$ID.png out/${ID}.png $([ "$TOP" != 0 ] && echo 1 || echo 0) $([ -f out/${ID}_top.png ] && echo out/${ID}_top.png); then OK=1; else OK=0; fi
if [ "$3" = install ]; then
  if [ $OK = 1 ] || [ "$4" = force ]; then
    for c in c3 c3_north c3_south; do
      mkdir -p ~/caesar3/hd/$c; cp out/${ID}.png ~/caesar3/hd/$c/$ID.png
      rm -f ~/caesar3/hd/$c/${ID}_top.png
      if [ -f out/${ID}_top.png ]; then cp out/${ID}_top.png ~/caesar3/hd/$c/${ID}_top.png; fi
    done
    echo "installed $ID"
  else
    echo "NOT installed $ID (checks failed)"
  fi
fi
$P ../viewer/build_viewer.py
