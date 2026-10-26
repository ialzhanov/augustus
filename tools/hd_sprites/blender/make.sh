#!/bin/bash
# usage: [C3_SEED=n] [C3_CLIMATE=c3|c3_north|c3_south] make.sh SCRIPT ID [install] [force]
# Renders SCRIPT for sprite ID at 8x (+ top part when the original has one), scales it to 2x (the game's
# closest zoom is 200%, so 2x is the most it can show; 2:1 bilinear at 100% is a clean box filter),
# sharpens lightly, runs check.py and saves the result as an attempt (out/attempts/[climate/]ID/<time>/).
# With "install" the attempt is copied to ~/caesar3/hd/*/ only when every check passes (or with "force").
# C3_SEED gives a new variation; the default seed is the sprite id. C3_CLIMATE selects the original to remake
# (default c3, the central climate); the sprite script can read it from the environment.
cd "$(dirname "$0")"
B=/Applications/Blender.app/Contents/MacOS/Blender; P=~/.local/share/uv/tools/mflux/bin/python
$P test_check.py >/dev/null || { echo "check.py regression tests failed: fix check.py first"; exit 1; }
S=$1; ID=$2; DENSITY=${DENSITY:-2}; export C3_SEED=${C3_SEED:-$ID}; export C3_CLIMATE=${C3_CLIMATE:-c3}
read -r TOP ORIG SUB <<< "$($P -c "import sys; sys.path.insert(0, '..'); from sg import *
print(SG(GAME, CLIMATES['$C3_CLIMATE']).img[$ID]['top'], orig_path('$C3_CLIMATE', $ID), sub('$C3_CLIMATE') or '.')")"
O=out/$SUB; mkdir -p $O
[ -f "$ORIG" ] || { echo "no original $ORIG (run export_originals.py)"; exit 1; }
$B -b -P $S -- $PWD/$O/${ID}_8.png 8 -- $ID 2>&1 | grep -E "rror:" || true
rm -f $O/${ID}_8top.png $O/${ID}_top.png
if [ "$TOP" != 0 ]; then $B -b -P $S -- $PWD/$O/${ID}_8top.png 8 top -- $ID 2>&1 | grep -E "rror:" || true; fi
$P -c "
from PIL import Image; import os
for src, dst in (('$O/${ID}_8.png', '$O/${ID}.png'), ('$O/${ID}_8top.png', '$O/${ID}_top.png')):
    if os.path.exists(src):
        im = Image.open(src); im.resize((im.width * $DENSITY // 8, im.height * $DENSITY // 8), Image.LANCZOS).save(dst)"
$P post.py $O/${ID}.png $([ -f $O/${ID}_top.png ] && echo $O/${ID}_top.png)
$P cmp.py $O/${ID}_8.png $ORIG $O/${ID}_cmp.png
echo "== $C3_CLIMATE $ID (seed $C3_SEED)"
CHECK_JSON=$O/${ID}_check.json $P check.py $ORIG $O/${ID}.png $([ "$TOP" != 0 ] && echo 1 || echo 0) $([ -f $O/${ID}_top.png ] && echo $O/${ID}_top.png)
$P attempt.py save $ID $C3_SEED $S $C3_CLIMATE
if [ "$3" = install ]; then $P attempt.py install $ID latest $4 $C3_CLIMATE; fi
$P ../viewer/build_viewer.py
