#!/bin/bash
# usage: [C3_SEED=n] make.sh SCRIPT ID [install] [force]
# Renders SCRIPT for sprite ID at 8x (+ top part when the original has one), scales it to 2x (the game's
# closest zoom is 200%, so 2x is the most it can show; 2:1 bilinear at 100% is a clean box filter),
# sharpens lightly, runs check.py and saves the result as an attempt (out/attempts/ID/<time>/).
# With "install" the attempt is copied to ~/caesar3/hd/*/ only when every check passes (or with "force").
# C3_SEED gives a new variation; the default seed is the sprite id.
cd "$(dirname "$0")"; mkdir -p out
B=/Applications/Blender.app/Contents/MacOS/Blender; P=~/.local/share/uv/tools/mflux/bin/python
$P test_check.py >/dev/null || { echo "check.py regression tests failed: fix check.py first"; exit 1; }
S=$1; ID=$2; DENSITY=${DENSITY:-2}; export C3_SEED=${C3_SEED:-$ID}
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
echo "== $ID (seed $C3_SEED)"
CHECK_JSON=out/${ID}_check.json $P check.py ../originals/$ID.png out/${ID}.png $([ "$TOP" != 0 ] && echo 1 || echo 0) $([ -f out/${ID}_top.png ] && echo out/${ID}_top.png)
$P attempt.py save $ID $C3_SEED $S
if [ "$3" = install ]; then $P attempt.py install $ID latest $4; fi
$P ../viewer/build_viewer.py
