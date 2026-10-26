"""Regression test for the dark grid between HD terrain tiles at zoom levels that are not whole numbers.

The engine (src/core/image_hd.c) masks each HD footprint to the original tile outline and the renderer draws it
with linear filtering. This test repeats both in numpy: a 5 x 5 grid of an HD grass tile, drawn at 106% over black
with straight-alpha bilinear sampling (like the GPU). The old mask (exact outline, black transparent pixels, no
atlas padding) shows dark seams; the new mask (outline + 1 original pixel, colour kept, edge-padded atlas) must not.

usage: python test_seams.py [HD tile png, default ~/caesar3/hd/c3/306.png]
"""
import os
import sys
import numpy as np
from PIL import Image

X_START = [28, 26, 24, 22, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2, 0, 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28]


def engine_mask(hd, density, grow, keep_colour):
    """the footprint mask of image_hd.c for a 1 x 1 tile"""
    m = np.zeros((30, 58), bool)
    for y, xs in enumerate(X_START):
        m[y, xs:58 - xs] = True
    if grow:
        g = m.copy()
        g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]; g[1:, :] |= m[:-1, :]; g[:-1, :] |= m[1:, :]
        m = g
    big = np.repeat(np.repeat(m, density, 0), density, 1)
    out = hd.copy()
    out[~big, 3] = 0
    if not keep_colour:
        out[~big, :3] = 0
    return out


def sample(tex, u, v, clamp):
    """straight-alpha bilinear sampling at texel coordinates (u, v); outside the texture: edge copy or black"""
    h, w = tex.shape[:2]
    u0, v0 = np.floor(u - 0.5).astype(int), np.floor(v - 0.5).astype(int)
    fu, fv = (u - 0.5 - u0)[..., None], (v - 0.5 - v0)[..., None]
    def at(x, y):
        inside = (x >= 0) & (x < w) & (y >= 0) & (y < h)
        t = tex[np.clip(y, 0, h - 1), np.clip(x, 0, w - 1)]
        return t if clamp else np.where(inside[..., None], t, 0.0)
    return ((at(u0, v0) * (1 - fu) + at(u0 + 1, v0) * fu) * (1 - fv) +
            (at(u0, v0 + 1) * (1 - fu) + at(u0 + 1, v0 + 1) * fu) * fv)


def draw_grid(tile, density, zoom=1.06, n=5):
    """n x n isometric grid of the tile, drawn like SDL_RenderCopyF with linear filtering, over black"""
    cw, ch = int(60 * n * zoom) + 80, int(30 * n * zoom) + 80
    canvas = np.zeros((ch, cw, 3))
    yy, xx = np.mgrid[0:ch, 0:cw] + 0.5
    for i in range(n):
        for j in range(n):                                   # back to front, like the city drawing order
            x0 = (30 * (i - j) + 30 * n) * zoom + 10
            y0 = (15 * (i + j)) * zoom + 10
            u = (xx - x0) / zoom * density
            v = (yy - y0) / zoom * density
            inside = (u >= 0) & (u < 58 * density) & (v >= 0) & (v < 30 * density)
            s = sample(tile, u, v, clamp=tile.clamp)
            a = (s[..., 3:4] / 255.0) * inside[..., None]
            canvas = canvas * (1 - a) + s[..., :3] / 255.0 * a
    return canvas, n


def seam_darkness(canvas, n, zoom=1.06):
    """mean brightness on the seams between inner tiles, divided by the mean inside the tiles"""
    lum = canvas.mean(-1)
    seam, body = [], []
    for i in range(1, n - 1):
        for j in range(1, n - 1):
            x0 = (30 * (i - j) + 30 * n) * zoom + 10; y0 = (15 * (i + j)) * zoom + 10
            cx, cy = x0 + 29 * zoom, y0 + 15 * zoom
            body.append(lum[int(cy) - 3:int(cy) + 3, int(cx) - 6:int(cx) + 6].mean())
            for t in np.linspace(0.15, 0.85, 12):            # along the lower-right edge of the tile
                sx, sy = cx + 29 * zoom * t, cy + 15 * zoom * (1 - t)
                seam.append(lum[int(sy) - 1:int(sy) + 2, int(sx)].min())   # darkest pixel across the seam
    return np.mean(seam) / np.mean(body)


class Tex(np.ndarray):
    pass


def tile_tex(hd, density, new):
    t = engine_mask(hd, density, grow=new, keep_colour=new).astype(float).view(Tex)
    t.clamp = new                                            # new: edge-padded atlas; old: the next atlas image (black)
    return t


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser('~/caesar3/hd/c3/306.png')
    hd = np.asarray(Image.open(path).convert('RGBA')).copy()
    density = hd.shape[1] // 58
    hd[..., :3] = 128      # plain grey with the tile's alpha: any darker seam comes from the drawing, not the grass
    for zoom in (0.8, 1.06, 1.33, 1.5):
        old = seam_darkness(*draw_grid(tile_tex(hd, density, False), density, zoom), zoom)
        new = seam_darkness(*draw_grid(tile_tex(hd, density, True), density, zoom), zoom)
        print(f'zoom {zoom:.0%}: seam brightness / tile brightness: old mask {old:.2f}, new mask {new:.2f}')
        assert new > 0.97, f'dark seams between HD tiles at {zoom:.0%} zoom'
    print('ok: no dark seams with the new mask')
