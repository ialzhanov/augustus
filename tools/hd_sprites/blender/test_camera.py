"""Regression test for the camera of c3.render: a half-tile ground and a pole land at the right pixels in every sprite
shape. A sprite higher than wide (trees, H 67 > W 58) rendered 15% too large: Blender fits ortho_scale to the larger
side. (A full-tile ground did not show it: the frame cut the larger diamond to the expected width.)

usage: Blender -b -P test_camera.py -- OUT_DIR/x.png 2
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
import c3

for W, H in ((58, 30), (58, 67), (118, 60)):
    c3.setup()
    n = round((W + 2) / 60)
    c3.box('ground', (0, 0, -0.001), (n / 2, n / 2, 0.002), 'grass')   # half the tile: not cut by the frame
    hp = min(1.0, (H - 15 * n - 2) / 35.5)
    c3.box('pole', (0, 0, hp / 2), (0.04, 0.04, hp), 'grass')          # top at row c - 35.5 hp (inside the frame)
    c3.OUT = c3.OUT.replace('.png', '') + f'_{W}x{H}.png'
    c3.render(W, H, tiles=n, samples=1)
    im = bpy.data.images.load(c3.OUT); w, h = im.size
    a = np.array(im.pixels[:]).reshape(h, w, 4)[::-1, :, 3] > 0.5
    ys, xs = np.nonzero(a)
    k = c3.SCALE; c = H - 15 * n
    got = (xs.min() / k, (xs.max() + 1) / k, ys.min() / k, (ys.max() + 1) / k)
    want = (W / 2 - 14.5 * n, W / 2 + 14.5 * n, c - 35.5 * hp, c + 7.5 * n)
    assert all(abs(g - e) <= 1.5 for g, e in zip(got, want)), (W, H, got, want)
    c3.OUT = c3.OUT.rsplit('_', 1)[0] + '.png'
print('camera ok')
