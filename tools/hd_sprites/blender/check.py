"""Checks an HD sprite against the original before it is installed. Exit code 1 when a check fails.

usage: python check.py ORIGINAL.png HD.png HAS_TOP(0|1) [HD_TOP.png]

Each check covers a fault we already had:
  size       HD = original x 2..8 (the engine refuses other sizes)
  top        the _top file exists when the original has a top part, with the right size
  spill      no HD pixels where the original has none (stones outside the tile edge)
  coverage   the HD sprite covers the original shape (nothing missing)
  seam       the footprint is fully opaque (semi-transparent tile edges = dark lines between tiles)
  rim        no light or dark band along the tile edge (grass tiles had a light rim)
  structure  blurred brightness follows the original (layout, what is light/dark where)
  mirror     orientation: the HD sprite matches the original better than its mirror image (tent fronts)
  edge       grass (green pixels) at the front tile edges matches the terrain grass tiles (same grass across the map)
  colour     overall colour matches the original
  contrast   local contrast at game size is near the original: not flat/bland, not noisy
  clip       nothing cut off at the top edge (roof peak above the frame)
"""
import sys
import numpy as np
from PIL import Image, ImageFilter


def lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T
    xyz = xyz / [0.95047, 1.0, 1.08883]
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lum(a):
    return a[..., :3] @ [0.299, 0.587, 0.114]


def blur(a, s):
    r = int(3 * s + 0.5); k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    p = np.pad(a, r, mode='edge')
    p = np.apply_along_axis(lambda v: np.convolve(v, k, 'valid'), 0, p)
    return np.apply_along_axis(lambda v: np.convolve(v, k, 'valid'), 1, p)


# mean Lab of the green pixels of the 58 central grass tiles 306-363 (tile means vary by about 1.5)
TERRAIN_GRASS_LAB = np.array([45.9, -19.3, 39.4])
X_START = [28, 26, 24, 22, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2, 0, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28]


def footprint_mask(w, n):
    """original footprint shape (same tile layout as image_hd.c / the .555 data), w x 30n"""
    m = np.zeros((30 * n, w), bool)
    xs = (n - 1) * 30
    def tile(x0, y0):
        for y in range(30):
            m[y0 + y, x0 + X_START[y]:x0 + 58 - X_START[y]] = True
    for i in range(n):
        for j in range(i + 1):
            tile(-30 * i + xs + 60 * j, 15 * i)
    for i in range(n - 2, -1, -1):
        for j in range(i + 1):
            tile(-30 * i + xs + 60 * j, 15 * (2 * n - i - 2))
    return m


def engine_view(full, top_path, w, h, d, n):
    """HD sprite as the engine draws it: footprint rows masked to the tile shape, top part from _top.png"""
    a = np.asarray(full, float).copy()
    fh = 30 * n
    m = np.repeat(np.repeat(footprint_mask(w, n), d, 0), d, 1)
    foot = a[(h - fh) * d:].copy(); foot[~m] = 0
    out = np.zeros_like(a); out[(h - fh) * d:] = foot
    top_h = h - 15 * n
    if top_path:
        t = np.asarray(Image.open(top_path).convert('RGBA'), float)
    else:
        t = a[:top_h * d].copy() if h > fh else None
    if t is not None:                                   # top drawn over the footprint
        region = out[:top_h * d]; al = t[..., 3:4] / 255
        region[..., :3] = t[..., :3] * al + region[..., :3] * (1 - al)
        region[..., 3] = np.maximum(region[..., 3], t[..., 3])
    return Image.fromarray(out.astype(np.uint8))


def checks(orig_path, hd_path, has_top=False, top_path=None):
    o = np.asarray(Image.open(orig_path).convert('RGBA'), float)
    hd_img = Image.open(hd_path).convert('RGBA')
    h, w = o.shape[:2]
    res = {}
    d = hd_img.width // w
    res['size'] = (2 <= d <= 8 and hd_img.size == (w * d, h * d), f'{hd_img.size} vs {w}x{h}')
    if not res['size'][0]:
        return res
    n = (w + 2) // 60                                      # footprint tiles
    top_h = h - 15 * n
    if has_top:
        ok = bool(top_path)
        if ok:
            t = Image.open(top_path); ok = t.size == (w * d, top_h * d)
        res['top'] = (ok, f'{Image.open(top_path).size if top_path else "missing"} vs {(w * d, top_h * d)}')
    else:
        res['top'] = (True, 'not needed')

    hd_img = engine_view(hd_img, top_path, w, h, d, n)                 # what the game draws
    g = np.asarray(hd_img.resize((w, h), Image.LANCZOS), float)          # game size
    a_hd = np.asarray(hd_img.getchannel('A').resize((w, h), Image.BOX), float) / 255
    oa = o[..., 3] > 0
    grown = np.asarray(Image.fromarray(oa.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) > 0
    spill = ((a_hd > 0.5) & ~grown).sum() / max(oa.sum(), 1)
    res['spill'] = (spill <= 0.01, f'{spill:.1%} outside the original shape (max 1%)')
    cover = ((a_hd > 0.5) & oa).sum() / max(oa.sum(), 1)
    res['coverage'] = (cover >= 0.92, f'{cover:.1%} of the original shape (min 92%)')
    # no seams: every pixel of the footprint shape is fully opaque in what the engine draws
    fm = np.repeat(np.repeat(footprint_mask(w, n), d, 0), d, 1)
    fa = np.asarray(hd_img.getchannel('A'))[(h - 30 * n) * d:][fm]
    thin = (fa < 250).mean()
    res['seam'] = (thin == 0, f'{thin:.1%} of the footprint not fully opaque (max 0%: dark lines between tiles)')
    # no rim: the outer band of the tile is as bright (relative to the inside) as in the original
    yy, xx = np.mgrid[0:h, 0:w]
    dd = np.abs(xx + 0.5 - w / 2) / (w / 2) + np.abs(yy + 0.5 - (h - 15 * n)) / (15 * n)
    def band_ratio(img, m):
        l = lum(img); band, inner = m & (dd > 0.88) & (yy > h - 30 * n), m & (dd > 0.55) & (dd < 0.82) & (yy > h - 30 * n)
        return l[band].mean() / max(l[inner].mean(), 1e-6) if band.sum() > 10 and inner.sum() > 10 else 1.0
    g_full = np.asarray(hd_img.resize((w, h), Image.LANCZOS), float)
    rim = band_ratio(g_full, g_full[..., 3] > 250) / band_ratio(o, oa)
    res['rim'] = (0.9 <= rim <= 1.1, f'tile edge brightness {rim:.2f} x the original ratio (0.9 .. 1.1: no light/dark rim)')

    both = oa & (a_hd > 0.5)
    lo, lg = blur(lum(o) * oa, 1.5), blur(lum(g) * (a_hd > 0.5), 1.5)
    lf = blur(lum(g[:, ::-1]) * (a_hd[:, ::-1] > 0.5), 1.5)
    corr = np.corrcoef(lo[both], lg[both])[0, 1]
    corr_m = np.corrcoef(lo[both], lf[both])[0, 1]
    self_m = np.corrcoef(lo[both], blur(lum(o[:, ::-1]) * oa[:, ::-1], 1.5)[both])[0, 1]
    res['structure'] = (corr >= 0.55, f'brightness correlation {corr:.2f} (min 0.55)')
    symmetric = self_m > 0.85
    res['mirror'] = (symmetric or corr >= corr_m + 0.05,
                     f'{corr:.2f} vs mirrored {corr_m:.2f}' + (' (original is symmetric)' if symmetric else ''))

    yy, xx = np.mgrid[0:h, 0:w]
    cy = h - 15 * n
    dist = np.abs(xx + 0.5 - w / 2) / (w / 2) + np.abs(yy + 0.5 - cy) / (15 * n)
    def green(a):
        return (a[..., 1] > a[..., 0] + 5) & (a[..., 1] > a[..., 2] + 15)
    ring = oa & (a_hd > 0.5) & (dist > 0.78) & (dist < 0.97) & (yy > cy)        # front edges: never under a building
    ring_o, ring_g = ring & green(o), ring & green(g)                            # grass pixels only (no clutter)
    if ring_g.sum() > 10:
        new = lab(g[ring_g][:, :3]).mean(0)
        de_ring = np.linalg.norm(TERRAIN_GRASS_LAB - new)
        de_own = np.linalg.norm(lab(o[ring_o][:, :3]).mean(0) - new) if ring_o.sum() > 10 else 99
    else:
        de_ring = de_own = 0
    res['edge'] = (min(de_ring, de_own) <= 6, f'edge grass dE {de_ring:.1f} vs terrain grass, {de_own:.1f} vs own original (max 6)')
    de_all = np.linalg.norm(lab(o[both][:, :3]).mean(0) - lab(g[both][:, :3]).mean(0))
    res['colour'] = (de_all <= 10, f'mean colour dE {de_all:.1f} (max 10)')

    def local_contrast(img, m):
        l = lum(img)
        return np.abs(l - blur(l, 2.0))[m].mean()
    m_in = np.asarray(Image.fromarray(both.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(3))) > 0
    cr = local_contrast(g, m_in) / max(local_contrast(o, m_in), 1e-6)
    res['contrast'] = (0.6 <= cr <= 1.5, f'local contrast {cr:.2f} x original (0.6 .. 1.5)')

    row_hd = (np.asarray(hd_img.getchannel('A'))[:d] > 0).sum() / d
    row_o = (o[0, :, 3] > 0).sum()
    res['clip'] = (row_hd <= max(row_o, 1) * d * 1.5 + 2 * d, f'top row {row_hd / d:.0f} px vs original {row_o}')
    return res


if __name__ == '__main__':
    r = checks(sys.argv[1], sys.argv[2], sys.argv[3] == '1', sys.argv[4] if len(sys.argv) > 4 else None)
    bad = [k for k, (ok, _) in r.items() if not ok]
    for k, (ok, msg) in r.items():
        print(f"  {'ok  ' if ok else 'FAIL'} {k:9} {msg}")
    print('PASS' if not bad else 'FAIL: ' + ', '.join(bad))
    sys.exit(1 if bad else 0)
