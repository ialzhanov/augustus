"""Regression tests for check.py: each case is a fault we already had. Run: python test_check.py"""
import os
import tempfile
import numpy as np
from PIL import Image, ImageOps
from check import checks

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp()


def orig(i):
    return os.path.join(HERE, '..', 'originals', f'{i}.png')


def save(im, name):
    path = os.path.join(TMP, name); im.save(path); return path


def upscaled(i, d=2):
    o = Image.open(orig(i)).convert('RGBA')
    return o.resize((o.width * d, o.height * d), Image.NEAREST)


def failed(res):
    return {k for k, (ok, _) in res.items() if not ok}


# the original itself (nearest 2x) passes everything
assert failed(checks(orig(2780), save(upscaled(2780), 'same.png'))) == set(), checks(orig(2780), save(upscaled(2780), 'same.png'))

# wrong orientation: a mirrored sprite fails 'mirror' (tents faced the wrong way)
assert 'mirror' in failed(checks(orig(2780), save(ImageOps.mirror(upscaled(2780)), 'mirror.png')))

# colour drift: 30% brighter fails 'colour' (pale tents)
arr = np.asarray(upscaled(2780), float); arr[..., :3] = np.clip(arr[..., :3] * 1.3, 0, 255)
assert 'colour' in failed(checks(orig(2780), save(Image.fromarray(arr.astype(np.uint8)), 'bright.png')))

# flat, bland look: a blurred sprite fails 'contrast'
from PIL import ImageFilter
blurred = upscaled(2780); a = blurred.getchannel('A'); blurred = blurred.filter(ImageFilter.GaussianBlur(3)); blurred.putalpha(a)
assert 'contrast' in failed(checks(orig(2780), save(blurred, 'blur.png')))

# wrong size: the engine refuses non-integer scales
assert 'size' in failed(checks(orig(2780), save(upscaled(2780).resize((117, 61)), 'size.png')))

# a sprite with a top part must come with its _top.png (walkers behind buildings)
assert 'top' in failed(checks(orig(2779), save(upscaled(2779), 'notop.png'), has_top=True))

# nothing may be cut off at the top edge (casa roof above the frame)
# (only sprites with a top part can show it: the engine cuts footprint-only sprites to the tile shape)
full = upscaled(2797); top = full.crop((0, 0, full.width, (36 - 15) * 2))
clip = np.asarray(top, float).copy(); clip[:2, :, :] = [200, 100, 50, 255]
assert 'clip' in failed(checks(orig(2797), save(full, 'casa.png'), True, save(Image.fromarray(clip.astype(np.uint8)), 'clip_top.png')))
assert 'clip' not in failed(checks(orig(2797), save(full, 'casa.png'), True, save(top, 'casa_top.png')))

# grass colour must match the terrain: a blue-tinted grass tile fails 'edge'
g = np.asarray(upscaled(306), float).copy(); g[..., 2] = np.clip(g[..., 2] + 60, 0, 255)
assert 'edge' in failed(checks(orig(306), save(Image.fromarray(g.astype(np.uint8)), 'edge.png')))

# seams: a terrain tile with semi-transparent edges (ground plane exactly 1x1) fails 'seam'
t = np.asarray(upscaled(306), float).copy(); a = t[..., 3]
edge = (a > 0) & ((np.roll(a, 1, 1) == 0) | (np.roll(a, -1, 1) == 0)); t[..., 3][edge] = 128
assert 'seam' in failed(checks(orig(306), save(Image.fromarray(t.astype(np.uint8)), 'seam.png')))

# seams: a crack tile whose sunken floor left a transparent gap along the back edges (mesh only 1.12 wide) fails 'seam'
t = np.asarray(upscaled(452), float).copy(); a = t[..., 3]; hh = a.shape[0]
back = (a > 0) & (np.roll(a, 2, 0) == 0) & (np.mgrid[0:hh, 0:1][0] < hh // 2)
t[..., 3][back] = 0
assert back.sum() > 20 and 'seam' in failed(checks(orig(452), save(Image.fromarray(t.astype(np.uint8)), 'crack_gap.png')))
assert 'seam' not in failed(checks(orig(452), save(upscaled(452), 'crack_same.png')))

# rim: the original itself with its top part measures 1.0 (the band was measured at other pixels in the two images:
# the top part stays opaque at the tile edge, the footprint does not; 837 measured 1.09, tree 276 0.94)
for i in (837, 828, 276):
    up = upscaled(i); top = up.crop((0, 0, up.width, up.height - 30))
    rim = checks(orig(i), save(up, f'rim_same_{i}.png'), True, save(top, f'rim_same_top_{i}.png'))['rim'][1]
    assert 0.98 <= float(rim.split()[3]) <= 1.02, (i, rim)

# rim: a grass tile with a light band along its edge fails 'rim'
t = np.asarray(upscaled(306), float).copy(); hh, ww = t.shape[:2]
yy, xx = np.mgrid[0:hh, 0:ww]; dd = np.abs(xx + 0.5 - ww / 2) / (ww / 2) + np.abs(yy + 0.5 - hh / 2) / (hh / 2)
t[..., :3][dd > 0.85] = np.clip(t[..., :3][dd > 0.85] * 1.35, 0, 255)
assert 'rim' in failed(checks(orig(306), save(Image.fromarray(t.astype(np.uint8)), 'rim.png')))


# a road verge that lost its green fails 'edge' (it was skipped when the new ring had <= 10 green pixels)
o600 = np.asarray(Image.open(orig(600)).convert('RGBA'), float)
gr600 = (o600[..., 1] > o600[..., 0] + 5) & (o600[..., 1] > o600[..., 2] + 15)
v = o600.copy(); v[gr600, :3] = [150, 145, 135]                                 # grey stone where the verge was
lost = Image.fromarray(v.astype(np.uint8)).resize((116, 60), Image.NEAREST)
assert 'edge' in failed(checks(orig(600), save(lost, 'verge_lost.png'))), checks(orig(600), save(lost, 'verge_lost.png'))['edge']
assert 'edge' not in failed(checks(orig(600), save(upscaled(600), 'verge_same.png')))

print('all check.py tests passed')
