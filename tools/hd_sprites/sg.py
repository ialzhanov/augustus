"""Read Caesar III .sg2/.555 sprites (format per Augustus src/core/image.c).

usage: python sg.py C3 GROUP [INDEX_IN_GROUP] -> out/<name>_<group>_<i>.png
"""
import json, struct, sys, os
from PIL import Image

FOOT_W, FOOT_H = 58, 30
X_START = [28, 26, 24, 22, 20, 18, 16, 14, 12, 10, 8, 6, 4, 2, 0,
           0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
TRANSPARENT = 0xf81f  # magenta in the uncompressed 555 data
HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.expanduser('~/caesar3')
# HD folder name (what the engine loads, src/core/image_hd.c) -> sg2/555 name. Each climate has its own sprites.
CLIMATES = {'c3': 'C3', 'c3_north': 'C3_North', 'c3_south': 'C3_south'}
VARIANTS = os.path.join(HERE, 'originals', 'climates.json')


def rgb(c):
    r, g, b = (c >> 10) & 31, (c >> 5) & 31, c & 31
    return (r << 3 | r >> 2, g << 3 | g >> 2, b << 3 | b >> 2, 255)


class SG:
    def __init__(self, game, name):
        self.sg2 = open(os.path.join(game, name + '.sg2'), 'rb').read()
        # + padding: the last image of C3.555 (8952) ends 2 bytes after the end of the file
        self.data = open(os.path.join(game, name + '.555'), 'rb').read() + bytes(64)
        self.groups = struct.unpack_from('<300H', self.sg2, 80)
        n = struct.unpack_from('<I', self.sg2, 16)[0]  # num_image_records
        self.img = []
        off = 4  # Augustus re-derives offsets: contiguous from byte 4, external images skipped
        for i in range(n + 1):
            e = self.sg2[20680 + 64 * i: 20744 + 64 * i]
            _, length, ulen = struct.unpack_from('<iii', e, 0)
            w, h = struct.unpack_from('<HH', e, 20)
            typ, comp, ext, top = struct.unpack_from('<BbbB', e, 50)
            rec = dict(i=i, len=length, ulen=ulen, w=w, h=h, iso=typ == 30, comp=comp, ext=ext, top=top, off=None)
            if not ext and i > 0:
                rec['off'] = off
                off += length
            self.img.append(rec)

    def raw(self, i):
        """what makes image i: its size, top flag and bytes (None when external or empty)"""
        r = self.img[i]
        if r['off'] is None or not r['w'] or not r['h']:
            return None
        return r['w'], r['h'], r['top'], self.data[r['off']:r['off'] + r['len']]

    def decode(self, i):
        r = self.img[i]
        if r['off'] is None:
            raise ValueError(f'image {i} is external')
        w, h, o = r['w'], r['h'], r['off']
        im = Image.new('RGBA', (w, h))
        px = im.load()
        if r['iso']:
            tiles = (w + 2) // (FOOT_W + 2)
            fh = FOOT_H * tiles
            p = o
            y0 = h - fh
            def tile(x0, ty):
                nonlocal p
                for y in range(FOOT_H):
                    for x in range(X_START[y], FOOT_W - X_START[y]):
                        px[x0 + x, y0 + ty + y] = rgb(struct.unpack_from('<H', self.data, p)[0]); p += 2
            xs = (tiles - 1) * 30
            for k in range(tiles):
                for j in range(k + 1):
                    tile(-30 * k + xs + 60 * j, 15 * k)
            for k in range(tiles - 2, -1, -1):
                for j in range(k + 1):
                    tile(-30 * k + xs + 60 * j, 15 * (tiles * 2 - k - 2))
            if r['top']:
                self._rle(px, o + r['ulen'], r['len'] - r['ulen'], w, h - fh // 2)
        elif r['comp']:
            self._rle(px, o, r['len'], w, h)
        else:
            p = o
            for y in range(h):
                for x in range(w):
                    c = struct.unpack_from('<H', self.data, p)[0]; p += 2
                    if c != TRANSPARENT:
                        px[x, y] = rgb(c)
        return im

    def _rle(self, px, p, n, w, h):
        x = y = 0
        end = p + n
        while p < end:
            c = self.data[p]; p += 1
            if c == 255:
                s = self.data[p]; p += 1
                y += s // w; x += s % w
                if x >= w: y += 1; x -= w
                if y >= h: return
            else:
                for _ in range(c):
                    px[x, y] = rgb(struct.unpack_from('<H', self.data, p)[0]); p += 2
                    x += 1
                    if x >= w:
                        y += 1; x = 0
                        if y >= h: return


def sub(climate):
    """folder part of a climate: the central climate keeps the old flat paths"""
    return '' if climate == 'c3' else climate + '/'


def orig_path(climate, i):
    return os.path.join(HERE, 'originals', f'{sub(climate)}{i}.png')


def variants(game=GAME):
    """{climate: sorted ids whose image differs from the central climate} (cached in originals/climates.json)"""
    if os.path.exists(VARIANTS):
        return json.load(open(VARIANTS))
    return write_variants(game)


def write_variants(game=GAME):
    c3 = SG(game, 'C3')
    out = {}
    for c, name in CLIMATES.items():
        if c != 'c3':
            sg = SG(game, name)
            out[c] = [i for i in range(1, len(c3.img)) if sg.raw(i) and sg.raw(i) != c3.raw(i)]
    os.makedirs(os.path.dirname(VARIANTS), exist_ok=True)
    json.dump(out, open(VARIANTS, 'w'))
    return out


def climates_of(i, var):
    """climates that show sprite i of the central climate (the others have their own image)"""
    return ['c3'] + [c for c in CLIMATES if c != 'c3' and i not in var.get(c, ())]


if __name__ == '__main__':
    sg = SG(os.path.expanduser('~/caesar3'), sys.argv[1])
    g = int(sys.argv[2]); k = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    i = sg.groups[g] + k
    os.makedirs('out', exist_ok=True)
    sg.decode(i).save(f'out/{sys.argv[1]}_{g}_{k}.png')
    print(i, sg.img[i])
