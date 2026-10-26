"""Re-model Caesar III small tents (group 26, images 2779-2782; 58 x 30-34 px, 1 tile).

usage: Blender -b -P tent.py -- OUT.png SCALE [top] -- ID
Ridge tents of patched canvas on lashed poles, with amphorae, sacks, baskets, blankets, a fire pit and straw.
Layout follows the original sprites: x_s = 29 + 29 (x + y), y_s = (H - 15) + 15 (x - y) - 35.5 z.
"""
import math, os, random, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh, bpy
from mathutils import Matrix, Vector
import c3

ID = int(sys.argv[-1])
H_PX = {2779: 30, 2780: 30, 2781: 33, 2782: 34}[ID]

# fabric/patch/front: sRGB colours sampled from the original sprite (converted with the light gain in canvas())
# rot = direction of the open front (deg from +x): 0 = screen lower-right, -90 = screen lower-left
# L, W, H = tent length, base width, ridge height. Props are given as PIXEL positions (x_s, y_s) of the object's
# base in the original sprite (measured at 12x zoom), converted with the camera formula by px().
FAB2780 = (72, 42, 30)   # dark maroon-brown slope (the sampled boxes mix in poles and grass)
VARIANTS = {
    2779: dict(rot=0, L=0.42, W=0.32, H=0.22, fabric=(74, 74, 62), patch=(159, 107, 68), patch_area=(-0.06, 0.12, 0.12),
               pots=[(40, 12), (46, 14)], sacks=[(12, 16), (16, 20), (24, 22), (30, 23)],
               blankets=[(18, 14, 0.3)], baskets=[(36, 22)], fire=None, stools=[]),
    2780: dict(rot=-90, L=0.30, W=0.28, H=0.26, fabric=FAB2780,
               patch=None, pots=[(18, 13), (48, 13)], sacks=[(9, 15), (13, 17)],
               blankets=[(20, 19, 1.2)], baskets=[(26, 24)], fire=(40, 22), stools=[]),
    2781: dict(rot=-90, L=0.40, W=0.36, H=0.31, fabric=(140, 128, 72), front=(78, 54, 34),
               pots=[(12, 17), (38, 17), (39, 23)], post_pot=(12, 17), sacks=[(49, 18), (22, 25)],
               blankets=[(28, 26, 0.2)], baskets=[(17, 22)], fire=None, stools=[]),
    2782: dict(rot=0, L=0.42, W=0.36, H=0.37, fabric=(112, 112, 66), patch=(141, 96, 66), patch_area=(0.0, 0.2, 0.17),
               pots=[(15, 22), (18, 21), (47, 17)], sacks=[(26, 27), (33, 28)],
               blankets=[(38, 25, 0.6)], baskets=[(22, 25)], fire=None, stools=[]),
}
V = VARIANTS[ID]


def px(x_s, y_s):
    """original sprite pixel (base of an object) -> world (x, y) on the ground"""
    sd, dd = (x_s + 0.5 - 29) / 29.0, (y_s + 0.5 - (H_PX - 15)) / 15.0
    return (sd + dd) / 2, (sd - dd) / 2


c3.setup(seed=ID)
M = c3.M
HERE = os.path.dirname(os.path.abspath(__file__))


# ---------- yard from the original: where it is not green, a sand/straw yard; its light colours give the yard colour ----------
def box_blur(m, n=1):
    for _ in range(n):
        p = np.pad(m, 1, mode='edge')
        m = (p[1:-1, 1:-1] + p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 5
    return m


def save_image(name, arr, colour):
    """H x W x 3 array (0..1) -> PNG in out/ -> loaded image (Cycles does not see pixels edited in memory)"""
    h, w = arr.shape[:2]
    im = bpy.data.images.new(name, w, h, alpha=False)
    p = np.ones((h, w, 4)); p[..., :3] = arr
    im.pixels.foreach_set(p[::-1].astype(np.float32).ravel())
    path = os.path.join(HERE, 'out', f'{name}_{ID}.png')
    im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    loaded = bpy.data.images.load(path); loaded.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
    return loaded


_o = bpy.data.images.load(os.path.join(HERE, '..', 'originals', f'{ID}.png'))
_px = np.array(_o.pixels[:]).reshape(_o.size[1], _o.size[0], 4)[::-1]      # top row first, sRGB
_rgb, _a = _px[..., :3], _px[..., 3]
_r, _g, _b = _rgb[..., 0], _rgb[..., 1], _rgb[..., 2]
YARD_PX = (_a > 0) & ~((_g > _r + 0.02) & (_g > _b + 0.08))                # not grass
# yard colour: light yard pixels grown into the rest (no dark tent/prop colour bleeds onto the ground), then blurred
fill = _rgb * 1.0; known = YARD_PX & (_rgb.mean(-1) >= 0.4)
if not known.any():
    known = YARD_PX.copy()
for _ in range(60):
    if known.all(): break
    w = box_blur(known.astype(float))
    grown = np.stack([box_blur(fill[..., k] * known) for k in range(3)], -1) / np.maximum(w, 1e-6)[..., None]
    new = ~known & (w > 0); fill[new] = grown[new]; known = known | new
YARD_COL = save_image('yardcol', np.stack([box_blur(fill[..., k], 2) for k in range(3)], -1), True)
_yy, _xx = np.mgrid[0:_a.shape[0], 0:_a.shape[1]]
_dist = np.abs((_xx + 0.5 - 29) / 29.0) + np.abs((_yy + 0.5 - (H_PX - 15)) / 15.0)    # 0 = tile centre, 1 = tile edge
_mask = np.clip(box_blur(YARD_PX.astype(float), 1) * 2.0 - 0.6, 0, 1) * np.clip((0.8 - _dist) / 0.1, 0, 1)   # grass at the tile edge
YARD_MASK = save_image('yardmask', np.repeat(_mask[..., None], 3, -1), False)
SAND_MEAN = (0.331, 0.257, 0.155)                                          # Ground054, linear mean colour


def m_yard():
    """sand photo (Ground054) coloured by the original's yard colour, faded out where the original is grass"""
    N = c3.N
    def window(image):
        t = N.nodes.new('ShaderNodeTexImage'); t.image = image; t.interpolation = 'Cubic'; t.extension = 'EXTEND'
        tc = N.nodes.new('ShaderNodeTexCoord'); c3.link(tc.outputs['Window'], t.inputs['Vector']); return t
    col, nrm, rough = c3.m_photo('Ground054', scale=3.0, tint=tuple(c3.GAIN[i] / SAND_MEAN[i] for i in range(3)), normal=1.0)()
    col = c3.mix(col, window(YARD_COL).outputs['Color'], 1.0, 'MULTIPLY')
    bsdf = N.nodes['Principled BSDF']
    c3.link(window(YARD_MASK).outputs['Color'], bsdf.inputs['Alpha'])
    return col, nrm, rough


def yard_at(x, y):
    """world (x, y) on the ground -> is the original a yard there"""
    xs, ys = int(29 + 29 * (x + y)), int((H_PX - 15) + 15 * (x - y))
    return 0 <= ys < _mask.shape[0] and 0 <= xs < _mask.shape[1] and _mask[ys, xs] > 0.5   # the drawn yard, not single brown pixels


def m_canvas(c1, c2):
    """canvas: sewn panels with dark seams, sun-bleached top, dirty hem, stains, weave"""
    def f():
        v = c3.coord()
        n = c3.node('ShaderNodeTexNoise', Scale=24.0, Detail=10.0, Roughness=0.65); c3.link(v, n.inputs['Vector'])
        col = c3.ramp(n.outputs['Fac'], (0.44, tuple(x * 0.6 for x in c1)), (0.56, tuple(min(1, x * 1.3) for x in c2)))
        panels = c3.node('ShaderNodeTexWave', Scale=18.0, Distortion=0.3); panels.wave_type = 'BANDS'; panels.bands_direction = 'X'
        c3.link(v, panels.inputs['Vector'])
        seam = c3.ramp(panels.outputs['Fac'], (0.0, (0.35, 0.32, 0.28)), (0.06, (1, 1, 1)), (0.94, (1, 1, 1)), (1.0, (0.45, 0.42, 0.38)))
        col = c3.mix(col, seam, 1.0, 'MULTIPLY')
        sep = c3.N.nodes.new('ShaderNodeSeparateXYZ'); c3.link(v, sep.inputs['Vector'])
        hz = c3.ramp(sep.outputs['Z'], (0.0, (0.45, 0.40, 0.33)), (0.06, (1, 1, 1)), (0.22, (1.08, 1.06, 1.04)))  # dirt hem, bleached top
        col = c3.mix(col, hz, 1.0, 'MULTIPLY')
        st = c3.node('ShaderNodeTexNoise', Scale=16.0, Detail=4.0); c3.link(v, st.inputs['Vector'])
        col = c3.mix(col, c3.ramp(st.outputs['Fac'], (0.58, (1, 1, 1)), (0.66, (0.6, 0.55, 0.45))), 1.0, 'MULTIPLY')
        weave = c3.node('ShaderNodeTexWave', Scale=220.0); weave.wave_type = 'BANDS'; weave.bands_direction = 'DIAGONAL'
        c3.link(v, weave.inputs['Vector'])
        return col, c3.bump(weave.outputs['Fac'], 0.2, 0.001), 0.95
    return f


def canvas_layers(col, v):
    """seams between sewn panels, dirty hem, sun-bleached top, on top of the photo canvas"""
    panels = c3.node('ShaderNodeTexWave', Scale=18.0, Distortion=0.3); panels.wave_type = 'BANDS'; panels.bands_direction = 'X'
    c3.link(v, panels.inputs['Vector'])
    seam = c3.ramp(panels.outputs['Fac'], (0.0, (0.45, 0.42, 0.38)), (0.05, (1, 1, 1)), (0.95, (1, 1, 1)), (1.0, (0.55, 0.52, 0.48)))
    sep = c3.N.nodes.new('ShaderNodeSeparateXYZ'); c3.link(v, sep.inputs['Vector'])
    hz = c3.ramp(sep.outputs['Z'], (0.0, (0.5, 0.45, 0.38)), (0.05, (1, 1, 1)), (0.25, (1.1, 1.08, 1.05)))
    st = c3.node('ShaderNodeTexNoise', Scale=9.0, Detail=4.0); c3.link(v, st.inputs['Vector'])
    stain = c3.ramp(st.outputs['Fac'], (0.56, (1, 1, 1)), (0.66, (0.7, 0.65, 0.55)))
    return c3.mix(c3.mix(c3.mix(col, seam, 1.0, 'MULTIPLY'), hz, 1.0, 'MULTIPLY'), stain, 1.0, 'MULTIPLY')


def to_lin(srgb):
    return [((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92 for c in srgb]


def canvas(srgb, lower=None):
    """photo canvas (Fabric061, neutral grey ~0.25 linear) tinted so it renders as the original's sRGB colour;
    lower: sRGB colour of the lower part of the walls (2781: dark brown walls under an olive roof)"""
    lin = to_lin(srgb)

    def extra(col, v):
        col = canvas_layers(col, v)
        sep = c3.N.nodes.new('ShaderNodeSeparateXYZ'); c3.link(v, sep.inputs['Vector'])
        if lower:
            ratio = tuple(a / b for a, b in zip(to_lin(lower), lin))
            band = c3.ramp(sep.outputs['Z'], (0.0, ratio), (V['H'] * 0.45, ratio), (V['H'] * 0.55, (1, 1, 1)))
            col = c3.mix(col, band, 1.0, 'MULTIPLY')
        if V.get('patch'):           # sewn-on patch: a canvas area of another colour, x0 +- xh along the tent, above z0
            x0, xh, z0 = V['patch_area']
            ratio = tuple(a / b for a, b in zip(to_lin(V['patch']), lin))
            dx = c3.node('ShaderNodeMath'); dx.operation = 'SUBTRACT'; c3.link(sep.outputs['X'], dx.inputs[0]); dx.inputs[1].default_value = x0
            ax = c3.node('ShaderNodeMath'); ax.operation = 'ABSOLUTE'; c3.link(dx.outputs['Value'], ax.inputs[0])
            inx = c3.ramp(ax.outputs['Value'], (xh - 0.01, (1, 1, 1)), (xh, (0, 0, 0)))
            inz = c3.ramp(sep.outputs['Z'], (z0, (0, 0, 0)), (z0 + 0.01, (1, 1, 1)))
            fac = c3.mix(inx, inz, 1.0, 'MULTIPLY')
            col = c3.mix(col, c3.mix(col, ratio, 1.0, 'MULTIPLY'), fac)
        return col
    # x 0.7: tent slopes face the sun more than flat ground (GAIN is calibrated on flat ground)
    return c3.m_photo('Fabric061', scale=7.0, tint=tuple(0.7 * lin[i] * c3.GAIN[i] / 0.25 for i in range(3)), normal=0.8,
                      extra=extra)


M['canvas'] = c3.material('canvas', canvas(V['fabric'], V.get('lower')))
if V.get('front'):
    M['front'] = c3.material('front', canvas(V['front']))
M['dirt'] = c3.material('dirt_photo', c3.m_photo('Ground108', scale=3.0, tint=(1.15, 1.1, 1.05), normal=1.0))
M['rope'] = c3.material('rope', lambda: ((0.55, 0.45, 0.30), None, 0.9))
ROT = Matrix.Rotation(math.radians(V['rot']), 4, 'Z')


def world(p):
    return ROT @ Vector(p)


def canvas_mesh(L, W, H, sag=0.12, nu=40, nv=30):
    """Sagging ridge-tent sheet along local x, ridge at y = 0, with folds toward the hem."""
    bm = bmesh.new(); rows = []
    for i in range(nu + 1):
        u = i / nu; x = -L / 2 + L * u
        droop = 1 - sag * math.sin(math.pi * u)
        row = []
        for j in range(nv + 1):
            s = 2 * j / nv - 1
            k = 1 - abs(s)
            z = H * droop * k ** 1.15
            wrinkle = 0.006 * (1 - k) * math.sin(u * 23 + s * 3) * math.sin(s * 11)
            row.append(bm.verts.new((x, s * W / 2 * (1 + 0.04 * math.sin(math.pi * u)) + wrinkle, z + wrinkle * 0.5)))
        rows.append(row)
    for i in range(nu):
        for j in range(nv):
            bm.faces.new([rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j]])
    me = bpy.data.meshes.new('canvas'); bm.to_mesh(me)
    for f in me.polygons: f.use_smooth = True
    return me


def tri(name, pts, mat):
    bm = bmesh.new(); bm.faces.new([bm.verts.new(p) for p in pts])
    me = bpy.data.meshes.new(name); bm.to_mesh(me)
    return c3.link_obj(name, me, mat)


def rod(a, b, r, mat, verts=8):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=(b - a).length, location=(a + b) / 2, vertices=verts)
    o = bpy.context.object; o.rotation_mode = 'QUATERNION'
    o.rotation_quaternion = (b - a).to_track_quat('Z', 'Y'); o.data.materials.append(M[mat]); return o


# ---------- ground: trodden dirt around the tent and a path to the entrance ----------
with c3.ground():
    c3.box('ground', (0, 0, -0.001), (1.12, 1.12, 0.002), 'grass')   # larger than the tile: the engine cuts the exact shape
    M['yard'] = c3.material('yard', m_yard)
    if not os.environ.get('C3_NOYARD'):
        c3.box('yard', (0, 0, 0.0005), (0.8, 0.8, 0.001), 'yard')   # mask is 0 past 0.4: no transparent plane over the edge grass
    for _ in range(14):
        a, r = random.uniform(0, 6.3), random.uniform(0.25, 0.40)
        c3.rock((r * math.cos(a), r * math.sin(a), 0.004), random.uniform(0.007, 0.015))
    c3.straw(0, 0, 0.36, n=90)

# ---------- tent ----------
L, W, H = V['L'], V['W'], V['H']
sheet = c3.link_obj('canvas', canvas_mesh(L, W, H), 'canvas'); sheet.matrix_world = ROT
sheet.modifiers.new('sol', 'SOLIDIFY').thickness = 0.004
end_mat = 'front' if V.get('front') else 'canvas'
tri('back', [world((-L / 2, -W / 2, 0)), world((-L / 2, W / 2, 0)), world((-L / 2, 0, H))], end_mat)
tri('inside', [world((L / 2 - 0.03, -W / 2 * 0.8, 0)), world((L / 2 - 0.03, W / 2 * 0.8, 0)), world((L / 2 - 0.03, 0, H * 0.85))], 'dark')
for sgn in (-1, 1):                                      # entrance flaps, tied back
    tri('flap', [world((L / 2, sgn * W / 2, 0)), world((L / 2, sgn * W * 0.06, H * 0.92)),
                 world((L / 2 + 0.03, sgn * W * 0.32, 0.0))], end_mat)
for e in (-L / 2 - 0.004, L / 2 + 0.004):               # crossed poles with rope lashing at the crossing
    for sgn in (-1, 1):
        rod(world((e, sgn * W / 2 * 0.95, 0)), world((e, -sgn * 0.04, H + 0.07)), 0.011, 'pole')   # bright poles: the original's white A
    rod(world((e, 0, H + 0.002)), world((e, 0, H + 0.016)), 0.0095, 'rope')   # rope lashing at the crossing
rod(world((-L / 2 - 0.02, 0, H - 0.002)), world((L / 2 + 0.02, 0, H - 0.002)), 0.0055, 'pole')   # ridge pole
for ex in (-1, 1):                                       # guy ropes to stakes
    for sy in (-1, 1):
        a = world((ex * L * 0.3, sy * W / 2 * 0.6, H * 0.45)); b = world((ex * (L / 2 + 0.05), sy * (W / 2 + 0.07), 0.0))
        rod(a, b, 0.0012, 'rope', 6)
        rod(b, b + Vector((0, 0, 0.022)), 0.003, 'wood', 6)

# ---------- belongings ----------
for p in V['pots']:
    x, y = px(*p)
    if V.get('post_pot') == p:
        rod((x, y, 0), (x, y, 0.06), 0.006, 'wood')
        c3.amphora(x, y, 1.3).location.z = 0.06
    elif random.random() < 0.6:
        c3.amphora(x, y, random.uniform(1.6, 1.9), random.uniform(0, 6))
    else:
        c3.bowl_pot(x, y, random.uniform(1.7, 2.0))
M['bedding'] = c3.material('bedding', c3.m_photo('Fabric061', scale=10.0, tint=(3.6, 3.4, 2.9), normal=0.8))
for x, y in map(lambda p: px(*p), V['sacks']):
    c3.sack(x, y, random.uniform(1.7, 2.1))
    c3.box('mat', (x + random.uniform(-.03, .03), y + random.uniform(-.03, .03), 0.003), (0.10, 0.07, 0.006), 'bedding',
           bevel=0.003, rot=random.uniform(0, 3))   # bedding under the sacks: the original's cream areas
for bx, by, r in V['blankets']:
    x, y = px(bx, by)
    c3.blanket_roll(x, y, r, random.choice([((0.55, 0.12, 0.08), (0.85, 0.78, 0.60)), ((0.20, 0.25, 0.45), (0.85, 0.80, 0.65))]))
for x, y in map(lambda p: px(*p), V['baskets']):
    c3.basket(x, y, 1.7)
for x, y in map(lambda p: px(*p), V['stools']):
    c3.stool(x, y)
if V['fire']:
    c3.firepit(*px(*V['fire']))


def open_ground(x, y):
    return not yard_at(x, y)


c3.grass(1800, open_ground)
c3.render(58, H_PX, edge_fade=True)
