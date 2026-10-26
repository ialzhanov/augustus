"""Crowns of tree and shrub sprites from the original (numpy only; terrain.py builds them in Blender).

The canopy mask is every pixel above the tile diamond, and inside the diamond the pixels whose colour differs from the
grass at the tile edge (Lab distance > T) in blobs joined to the part above, or blobs of 6 px or more.
The mask is split into circles (greedy, largest inscribed circle first). An orthographic camera shows a sphere of
radius R as a circle of 41 R px, so each circle is a crown sphere. Its height: the lowest canopy or trunk pixel below
the circle is the ground point (the base of the tree). Small circles in the column under a larger crown are its trunk.

usage (self-check): python foliage.py
"""
import numpy as np

T = 14.0          # Lab distance from the edge grass that counts as foliage
PX_PER_UNIT = 41.0   # 29 * sqrt(2): screen px per world unit (orthographic camera)


def to_lab(rgb):
    """sRGB 0..1 -> Lab"""
    c = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]).T / [0.95047, 1.0, 1.08883]
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def components(m):
    """4-connected components of a boolean mask: list of (ys, xs)"""
    seen, out = np.zeros_like(m), []
    for y0, x0 in zip(*np.nonzero(m)):
        if seen[y0, x0]:
            continue
        st, ys, xs = [(y0, x0)], [], []; seen[y0, x0] = True
        while st:
            y, x = st.pop(); ys.append(y); xs.append(x)
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < m.shape[0] and 0 <= xx < m.shape[1] and m[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True; st.append((yy, xx))
        out.append((np.array(ys), np.array(xs)))
    return out


def diamond(H, W, tiles=None, grow=1.12):
    """the footprint diamond of n x n tiles (n from the width), with the 2 px steps of the outline at grow 1.12"""
    tiles = tiles or max(1, round((W + 2) / 60))
    yy, xx = np.mgrid[0:H, 0:W]
    dd = np.abs(xx + 0.5 - W / 2) / (W / 2) + np.abs(yy + 0.5 - (H - 15 * tiles)) / (15 * tiles)
    return dd <= grow, dd


def water(rgb):
    """blue water pixels (as terrain.py)"""
    return rgb[..., 2] > np.maximum(rgb[..., 0], rgb[..., 1]) + 0.06


def foliage_diff(rgb, alpha):
    """Lab distance of each pixel from the median grass colour at the tile edge (water at the edge left out)"""
    H, W = alpha.shape
    dia, dd = diamond(H, W)
    lab = to_lab(rgb)
    ring = (alpha > 0) & dia & (dd > 0.75)
    ref = np.median(lab[ring & ~water(rgb)] if (ring & ~water(rgb)).sum() > 10 else lab[ring], 0)
    return np.linalg.norm(lab - ref, axis=-1)


def canopy(rgb, alpha):
    """rgb: H x W x 3 sRGB 0..1, alpha: H x W -> canopy mask"""
    H, W = alpha.shape
    dia, _ = diamond(H, W)
    a = alpha > 0
    m = a & (~dia | (foliage_diff(rgb, alpha) > T)) & ~water(rgb)   # shore trees: water is never foliage
    er = m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1)   # opening: no single pixels
    m = m & (er | np.roll(er, 1, 0) | np.roll(er, -1, 0) | np.roll(er, 1, 1) | np.roll(er, -1, 1))
    keep = np.zeros_like(m)
    for ys, xs in components(m):
        if (~dia[ys, xs]).any() or len(ys) >= 6:
            keep[ys, xs] = True
    return keep


def distance_inside(m):
    """distance (px) from each pixel of m to the nearest pixel outside m or the image edge"""
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    d = np.minimum.reduce([yy + 1, xx + 1, m.shape[0] - yy, m.shape[1] - xx]).astype(float)
    for y, x in zip(*np.nonzero(~m)):
        d = np.minimum(d, np.hypot(yy - y, xx - x))
    return np.where(m, d, 0)


def circles(m, rmin=2.0, stop=1.5):
    """greedy circle cover of m: (x, y, r) in px, largest first"""
    d = distance_inside(m)
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    left, out = m.copy(), []
    while left.sum() > 4:
        score = np.where(left, d, 0)
        y, x = np.unravel_index(score.argmax(), score.shape)
        if d[y, x] < stop:
            break
        r = max(d[y, x], rmin)
        out.append((x + 0.5, y + 0.5, r))
        left &= np.hypot(yy - y, xx - x) > r * 0.9
    return out


def crowns(rgb, alpha, keep_low=False):
    """crown spheres: (x px, y px, r px, z units, ground row px). The ground point is the lowest non-grass pixel
    (canopy or trunk, Lab distance > T, no opening) in the columns under the circle; the crown centre is z above it."""
    m = canopy(rgb, alpha)
    trunk = (alpha > 0) & (rgb[..., 0] > rgb[..., 1] + 0.02) & (rgb[..., 0] > rgb[..., 2] + 0.06)   # brown bark
    H, W = alpha.shape
    out = []
    cs = circles(m)
    big = [(x, y, r) for x, y, r in cs if r >= 3.5]
    dia, _ = diamond(H, W, grow=1.0)
    for x, y, r in cs:
        if r <= 2.5 and any(abs(x - xb) < max(2.0, rb / 3) and y > yb + 0.5 * rb for xb, yb, rb in big):
            continue                                            # a trunk under a crown, not a crown
        if r < 3.5 and dia[int(y), int(x)] and not keep_low:
            continue                                            # a low bush: the undergrowth shows it (rocks keep them)
        cols = slice(max(int(x - r / 2), 0), min(int(x + r / 2) + 1, W))
        below = (m | trunk)[int(y):, cols].any(1)               # the rows joined to the circle (a gap of 2 rows ends it)
        gaps = np.nonzero(~below[:-1] & ~below[1:])[0]
        yb = int(y) + (gaps[0] if len(gaps) else len(below) - 1)
        R = r / PX_PER_UNIT
        z = max((yb + 0.5 - y - 0.5 * r) / 35.5, 0.8 * R)     # base 0.5 r in front of the centre (the crown's depth)
        out.append((x, y, r, z, y + 35.5 * z))                   # ground row under the centre: the centre shows at (x, y)
    return m, out


if __name__ == '__main__':
    import os
    from PIL import Image
    here = os.path.dirname(os.path.abspath(__file__))
    for i, least in ((303, 0.85), (254, 0.85), (280, 0.75)):   # 280: its trunks (about 20% of the mask) are cylinders
        o = np.asarray(Image.open(os.path.join(here, '..', 'originals', f'{i}.png')).convert('RGBA'), float) / 255
        m, cs = crowns(o[..., :3], o[..., 3])
        yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
        cover = np.zeros_like(m)
        for x, y, r, z, g in cs:
            cover |= np.hypot(xx + 0.5 - x, yy + 0.5 - y) <= r
        up = m & ~diamond(*m.shape)[0]                          # above the diamond (low bushes are undergrowth)
        frac = (cover & up).sum() / up.sum()
        assert frac >= least, (i, frac)                         # the circles show the whole canopy
        assert (cover & ~m).sum() / m.sum() < 0.2, i            # and not much more
        assert all(z > 0 for *_, z, g in cs), i
    # a tall cypress (254): its top crown is high above the ground
    o = np.asarray(Image.open(os.path.join(here, '..', 'originals', '254.png')).convert('RGBA'), float) / 255
    _, cs = crowns(o[..., :3], o[..., 3])
    assert max(z for *_, z, g in cs) > 0.5, max(z for *_, z, g in cs)
    print('foliage ok')
