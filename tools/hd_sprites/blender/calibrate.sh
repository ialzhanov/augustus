#!/bin/bash
# Calibrates c3.py to the current LIGHT: GAIN (flat white ground) then GRASS_CAL (grass render vs tile 306).
cd "$(dirname "$0")"; B=/Applications/Blender.app/Contents/MacOS/Blender; P=~/.local/share/uv/tools/mflux/bin/python
T=$(mktemp -d)
cat > $T/white.py <<PY
import sys; sys.path.insert(0, '$PWD'); import c3
c3.setup(); c3.M['white'] = c3.material('white', lambda: ((0.5, 0.5, 0.5), None, 1.0))
c3.box('g', (0, 0, -0.001), (1, 1, 0.002), 'white'); c3.render(58, 30)
PY
$B -b -P $T/white.py -- $T/white.png 2 >/dev/null 2>&1
GAIN=$($P -c "
from PIL import Image; import numpy as np
a=np.asarray(Image.open('$T/white.png').convert('RGBA'),float); v=a[a[...,3]>250][:,:3].mean(0)/255
lin=np.where(v>0.04045,((v+0.055)/1.055)**2.4,v/12.92); print(','.join(f'{0.5/x:.3f}' for x in lin))")
sed -i '' "s/^GAIN = (.*)  *# 1 \/ light/GAIN = ($GAIN)       # 1 \/ light/" c3.py
cat > $T/g.py <<PY
import sys; sys.path.insert(0, '$PWD'); import c3
c3.setup()
with c3.ground(): c3.box('ground', (0, 0, -0.001), (1, 1, 0.002), 'grass')
c3.grass(1800, lambda x, y: True); c3.render(58, 30)
PY
CAL=1,1,1
for k in 1 2; do
  C3_GRASS_CAL=$CAL $B -b -P $T/g.py -- $T/g.png 4 >/dev/null 2>&1; $P post.py $T/g.png
  R=$($P calibrate_grass.py $T/g.png)
  CAL=$($P -c "print(','.join(f'{float(x)*float(y):.3f}' for x,y in zip('$CAL'.split(','),'$R'.split(','))))")
done
sed -i '' "s/os.environ.get('C3_GRASS_CAL', '[0-9.,]*')/os.environ.get('C3_GRASS_CAL', '$CAL')/" c3.py
C3_GRASS_CAL=$CAL $B -b -P $T/g.py -- $T/g.png 4 >/dev/null 2>&1; $P post.py $T/g.png
echo "GAIN $GAIN  GRASS_CAL $CAL"; $P check.py ../originals/306.png $T/g.png 0
