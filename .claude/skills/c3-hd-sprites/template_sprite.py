"""Re-model Caesar III <GROUP NAME> (group <g>, images <ids>; W x H px, n tile(s)).

usage: Blender -b -P <name>.py -- OUT.png SCALE [top] -- ID
Copy to tools/hd_sprites/blender/<name>.py. Positions are measured PIXELS of the original
(base of each object), converted with px(); colours are sampled sRGB from the original, converted with lin_gain().
"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import c3

ID = int(sys.argv[-1])
SIZE = {0000: (58, 30)}[ID]              # W, H of each variant's original sprite
TILES = 1                                # footprint n x n

VARIANTS = {
    0000: dict(rot=0,                    # front direction (deg from +x): 0 = screen lower-right, -90 = lower-left
               wall=(150, 140, 105),     # sRGB sampled from the original
               pots=[(40, 12)]),         # pixel positions (x_s, y_s) of object bases in the original
}
V = VARIANTS[ID]
W, H = SIZE


def px(x_s, y_s):
    """original sprite pixel (base of an object) -> world (x, y) on the ground"""
    s, d = (x_s + 0.5 - W / 2) / 29.0, (y_s + 0.5 - (H - 15 * TILES)) / 15.0
    return (s + d) / 2, (s - d) / 2


def lin_gain(srgb, facing=0.7):
    """base colour that renders as the original's sRGB colour (facing < 1 for surfaces lit more than flat ground)"""
    lin = [((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92 for c in srgb]
    return tuple(facing * lin[i] * c3.GAIN[i] for i in range(3))


c3.setup(seed=ID)
M = c3.M
M['wall'] = c3.material('wall', c3.m_photo('Plaster007', scale=6.0,
                                           tint=tuple(v / 0.5 for v in lin_gain(V['wall'])), normal=0.8))

with c3.ground():                        # everything here is cut out in the top pass
    c3.box('ground', (0, 0, -0.001), (1.12 * TILES, 1.12 * TILES, 0.002), 'grass')   # 1.12: no gaps at the stepped outline

# ---------- model ----------
# c3.box(name, loc, size, material, bevel=..., rot=...), c3.lathe(...), bmesh for custom shapes

# ---------- props ----------
for p in V['pots']:
    c3.amphora(*px(*p), s=1.7)

c3.grass(1800, lambda x, y: True)        # tufts per full tile; return False where the model or a yard covers the ground
c3.render(W, H, tiles=TILES)
