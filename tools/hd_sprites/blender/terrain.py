"""HD terrain tiles (grass, water, shores): new detail, colour layout from the original.

usage: Blender -b -P terrain.py -- OUT.png SCALE -- ID ORIGINAL.png
The original tile gives only the broad colour layout (blurred) and the masks (grass / dirt-sand / water).
All visible detail is new: CC0 photo grass and ground, 3D grass tufts, flowers, pebbles; water with depth,
waves, sun glints, shore foam and a wet band on the sand.
Photo colours are normalised: photo / photo mean x blurred original, so the tiles keep matching their neighbours.
Waves are sums of sines with whole periods per tile (seamless across tiles). Plain water tiles 364-371 are the
8 frames of the water animation: the wave phase steps once per frame.
"""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import numpy as np
import c3

ID, SRC = int(sys.argv[-2]), sys.argv[-1]
HERE = os.path.dirname(os.path.abspath(__file__))
TERRAIN_CAL = [float(v) for v in os.environ.get('C3_TERRAIN_CAL', '2.756,2.575,2.208').split(',')]   # terrain render vs its original (edge grass, with the tuft density compensation)
WATER_CAL = [float(v) for v in os.environ.get('C3_WATER_CAL', '0.519,0.540,0.590').split(',')]   # x TERRAIN_CAL: water colour unchanged by the terrain recalibration
GAIN = tuple(c3.GAIN[i] * TERRAIN_CAL[i] for i in range(3))
FRAME = (ID - 364) % 8 if 364 <= ID <= 371 else 0
PAVED = 591 <= ID <= 639   # cobbled roads: 3D cobbles where the original is not grass
MOSAIC = 3140 <= ID <= 3147   # plaza: a mosaic of small square stones over the whole tile
COBBLE_CAL = float(os.environ.get('C3_COBBLE_CAL', '1.0'))
PHOTO = {'grass': ('Grass004', (0.119, 0.152, 0.030)), 'meadow': ('Ground037', (0.317, 0.292, 0.099)),
         'sand': ('Ground054', (0.331, 0.257, 0.155))}       # id, linear mean colour

c3.setup(seed=ID)
img = bpy.data.images.load(SRC); img.colorspace_settings.name = 'sRGB'
W, H = img.size
NT = max(1, round((W + 2) / 60))   # footprint tiles: 58 px wide = 1, 118 px = 2 x 2
pix = np.array(img.pixels[:]).reshape(H, W, 4)[::-1]          # top row first, sRGB values
rgb, alpha = pix[..., :3], pix[..., 3]


def box_blur(m, n=1):
    """3x3 cross blur, edges replicated (np.roll would wrap the opposite edge in)"""
    for _ in range(n):
        p = np.pad(m, 1, mode='edge')
        m = (p[1:-1, 1:-1] + p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 5
    return m


def save_image(name, arr, colour):
    """H x W x 3 array (0..1) -> PNG in out/ -> loaded image (Cycles does not see pixels edited in memory)"""
    im = bpy.data.images.new(name, W, H, alpha=False)
    px = np.ones((H, W, 4)); px[..., :3] = arr
    im.pixels.foreach_set(px[::-1].astype(np.float32).ravel())
    path = os.path.join(HERE, 'out', f'{name}_{ID}.png')
    im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    loaded = bpy.data.images.load(path); loaded.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
    return loaded


# fill transparent corners with nearby colour, then blur: broad colour layout without the original's pixel detail
fill = rgb * (alpha[..., None] > 0); known = alpha > 0
while not known.all():                                    # grow colours into the transparent corners until all are set
    w = box_blur(known.astype(float))
    grown = np.stack([box_blur(fill[..., k] * known) for k in range(3)], -1) / np.maximum(w, 1e-6)[..., None]
    new = ~known & (w > 0)
    fill[new] = grown[new]; known = known | new
# masks from the extended colours: they continue past the tile edge (no rim where a mask meets the transparent corners)
r, g, b = fill[..., 0], fill[..., 1], fill[..., 2]
water = b > np.maximum(r, g) + 0.06
grassy = (g > r + 0.02) & (g > b + 0.08) & ~water
dirt = ~water & ~grassy
if MOSAIC:   # the blue and green mosaic stones are not water or grass
    water, grassy, dirt = np.zeros_like(water), np.zeros_like(grassy), np.ones_like(dirt)
inside = alpha > 0
# paved roads: the sharp layout (a blur mixes the light stones into the 1 px green verges)
LAYOUT = save_image('layout', np.stack([box_blur(fill[..., k], 0 if PAVED else 2) for k in range(3)], -1), True)
# distance from the shore (sprite pixels, up to 4) for depth, foam and the wet band
def grow(m):
    return m | np.roll(m, 1, 0) | np.roll(m, -1, 0) | np.roll(m, 1, 1) | np.roll(m, -1, 1)
land = ~water
dist_w = np.zeros((H, W)); cur = land.copy()
for k in range(1, 5):
    nxt = grow(cur); dist_w[(nxt & ~cur) & water] = k; cur = nxt
dist_w[water & (dist_w == 0)] = 5
dist_l = np.zeros((H, W)); cur = water.copy()
for k in range(1, 4):
    nxt = grow(cur); dist_l[(nxt & ~cur) & land] = k; cur = nxt
MASKS = save_image('masks', np.stack([box_blur(water.astype(float)), box_blur(dirt.astype(float), 2),
                                      np.clip(dist_w / 5, 0, 1)], -1), False)
# blue: local density of the 3D grass tufts (they grow on 'grassy' pixels only, so the density changes across a tile)
SHORE = save_image('shore', np.stack([((dist_l > 0) & (dist_l <= 2)).astype(float), ((dist_w > 0) & (dist_w <= 1.5)).astype(float),
                                      box_blur(grassy.astype(float), 2)], -1), False)
# tufts and their shadows make the ground darker by this fraction at full density (tile 306: edge -3.8 L with tufts, +16 L
# without). The ground is lightened where there are fewer tufts, so a tile is not lighter in its centre (fewer tufts on
# meadow pixels) and darker at its edge (edge check). TERRAIN_CAL stays calibrated for full density.
TUFT_DENSITY = 6.0   # tufts per grassy pixel (the same on every tile: a road verge continues the next grass tile)
TUFT_SHADE = float(os.environ.get('C3_TUFT_SHADE', '0.5'))   # at 6 tufts per grassy pixel (TERRAIN_CAL is calibrated there)


def window_tex(image, interp='Cubic'):
    t = c3.N.nodes.new('ShaderNodeTexImage'); t.image = image; t.interpolation = interp; t.extension = 'EXTEND'
    tc = c3.N.nodes.new('ShaderNodeTexCoord'); c3.link(tc.outputs['Window'], t.inputs['Vector'])
    return t


def channel(tex, k):
    sep = c3.N.nodes.new('ShaderNodeSeparateColor'); c3.link(tex.outputs['Color'], sep.inputs['Color'])
    return sep.outputs[k]


def photo(kind, v, scale):
    tex_id, mean = PHOTO[kind]
    mp = c3.N.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale); c3.link(v, mp.inputs['Vector'])
    out = {}
    for k, colour in (('Color', True), ('NormalGL', False)):
        t = c3.N.nodes.new('ShaderNodeTexImage'); t.projection = 'BOX'
        t.image = bpy.data.images.load(os.path.join(c3.TEX, tex_id, f'{tex_id}_1K-JPG_{k}.jpg'), check_existing=True)
        if not colour:
            t.image.colorspace_settings.name = 'Non-Color'
        c3.link(mp.outputs['Vector'], t.inputs['Vector']); out[k] = t.outputs['Color']
    norm = c3.mix(out['Color'], tuple(1 / m for m in mean), 1.0, 'MULTIPLY')      # photo / its mean: detail around 1.0
    return norm, out['NormalGL']


def waves(v):
    total = None
    for kx, ky, amp, ph in [(3, 1, 1.0, 0.0), (-2, 4, 0.7, 1.3), (5, -3, 0.5, 2.1), (7, 6, 0.3, 0.7), (-9, 5, 0.25, 4.0),
                            (11, -8, 0.15, 1.1), (-13, 12, 0.12, 2.6)]:
        dot = c3.node('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
        dot.inputs[1].default_value = (2 * math.pi * kx, 2 * math.pi * ky, 0); c3.link(v, dot.inputs[0])
        add = c3.node('ShaderNodeMath'); add.operation = 'ADD'
        add.inputs[1].default_value = ph + 2 * math.pi * FRAME / 8 * (1 + (abs(kx) + abs(ky)) % 2)
        c3.link(dot.outputs['Value'], add.inputs[0])
        s = c3.node('ShaderNodeMath'); s.operation = 'SINE'; c3.link(add.outputs['Value'], s.inputs[0])
        m = c3.node('ShaderNodeMath'); m.operation = 'MULTIPLY'; m.inputs[1].default_value = amp; c3.link(s.outputs['Value'], m.inputs[0])
        if total is None:
            total = m.outputs['Value']
        else:
            t = c3.node('ShaderNodeMath'); t.operation = 'ADD'; c3.link(total, t.inputs[0]); c3.link(m.outputs['Value'], t.inputs[1])
            total = t.outputs['Value']
    return total


def m_terrain():
    N = c3.N
    v = c3.coord()
    lay = window_tex(LAYOUT)
    base = c3.mix(lay.outputs['Color'], GAIN, 1.0, 'MULTIPLY')                    # broad colour of the original
    masks, shore = window_tex(MASKS, 'Linear'), window_tex(SHORE, 'Linear')
    # land: grass photo varied with the meadow photo, sand/dirt photo where the original is not green
    gcol, gnrm = photo('grass', v, 2.5)
    mcol, mnrm = photo('meadow', v, 1.6)
    vary = c3.node('ShaderNodeTexNoise', Scale=4.0, Detail=3.0); c3.link(v, vary.inputs['Vector'])
    vmask = c3.ramp(vary.outputs['Fac'], (0.45, (0, 0, 0)), (0.6, (1, 1, 1)))
    green = c3.mix(gcol, mcol, vmask)
    scol, snrm = photo('sand', v, 3.0)
    detail = c3.mix(green, scol, channel(masks, 'Green'))
    wet = c3.ramp(channel(shore, 'Red'), (0.0, (1, 1, 1)), (1.0, (0.62, 0.58, 0.55)))   # wet band on the shore
    land_col = c3.mix(c3.mix(base, detail, 1.0, 'MULTIPLY'), wet, 1.0, 'MULTIPLY')
    shade = c3.node('ShaderNodeMath'); shade.operation = 'MULTIPLY_ADD'                   # 1 - TUFT_SHADE * density
    c3.link(channel(shore, 'Blue'), shade.inputs[0]); shade.inputs[1].default_value = -TUFT_SHADE * TUFT_DENSITY / 6.0; shade.inputs[2].default_value = 1.0
    comp = c3.node('ShaderNodeMath'); comp.operation = 'DIVIDE'; comp.inputs[0].default_value = 1.0 - TUFT_SHADE
    c3.link(shade.outputs['Value'], comp.inputs[1])
    land_col = c3.mix(land_col, comp.outputs['Value'], 1.0, 'MULTIPLY')
    if PAVED:   # soil between the cobbles: darker than the stones
        land_col = c3.mix(land_col, c3.ramp(channel(masks, 'Green'), (0.0, (1, 1, 1)), (1.0, (0.5, 0.47, 0.42))), 1.0, 'MULTIPLY')
    nm = N.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 1.2
    nmix = N.nodes.new('ShaderNodeMix'); nmix.data_type = 'RGBA'; c3.link(channel(masks, 'Green'), nmix.inputs['Factor'])
    c3.link(gnrm, nmix.inputs['A']); c3.link(snrm, nmix.inputs['B']); c3.link(nmix.outputs['Result'], nm.inputs['Color'])
    land = N.nodes.new('ShaderNodeBsdfPrincipled'); land.inputs['Roughness'].default_value = 0.95
    c3.link(land_col, land.inputs['Base Color']); c3.link(nm.outputs['Normal'], land.inputs['Normal'])
    # water: deeper = darker, waves with glints, foam along the shore
    depth = c3.ramp(channel(masks, 'Blue'), (0.0, (1.25, 1.2, 1.1)), (1.0, (0.75, 0.78, 0.85)))
    wcol = c3.mix(c3.mix(c3.mix(lay.outputs['Color'], tuple(GAIN[i] * WATER_CAL[i] for i in range(3)), 1.0, 'MULTIPLY'),
                         depth, 1.0, 'MULTIPLY'), (1, 1, 1), 0.0)
    fn = c3.node('ShaderNodeTexNoise', Scale=60.0, Detail=6.0); c3.link(v, fn.inputs['Vector'])
    foam = c3.node('ShaderNodeMath'); foam.operation = 'MULTIPLY'
    c3.link(channel(shore, 'Green'), foam.inputs[0])
    c3.link(c3.ramp(fn.outputs['Fac'], (0.45, (0, 0, 0)), (0.6, (1, 1, 1))), foam.inputs[1])
    wcol = c3.mix(wcol, (0.85, 0.88, 0.86), foam.outputs['Value'])
    wat = N.nodes.new('ShaderNodeBsdfPrincipled'); wat.inputs['Roughness'].default_value = 0.06
    wat.inputs['Specular IOR Level'].default_value = 0.9
    ripple = c3.node('ShaderNodeTexNoise', Scale=45.0, Detail=6.0); c3.link(v, ripple.inputs['Vector'])
    h = c3.node('ShaderNodeMath'); h.operation = 'MULTIPLY_ADD'; c3.link(ripple.outputs['Fac'], h.inputs[0])
    h.inputs[1].default_value = 1.6; c3.link(waves(v), h.inputs[2])
    crest = c3.node('ShaderNodeMapRange', **{'From Min': -1.0, 'From Max': 2.6, 'To Min': 0.0, 'To Max': 1.0})
    c3.link(h.outputs['Value'], crest.inputs['Value'])
    wcol = c3.mix(wcol, c3.ramp(crest.outputs['Result'], (0.0, (0.72, 0.76, 0.85)), (0.55, (1, 1, 1)), (1.0, (1.35, 1.35, 1.3))),
                  1.0, 'MULTIPLY')                                                  # darker troughs, lighter crests
    c3.link(wcol, wat.inputs['Base Color'])
    c3.link(c3.bump(h.outputs['Value'], 0.6, 0.004), wat.inputs['Normal'])
    mixs = N.nodes.new('ShaderNodeMixShader'); c3.link(channel(masks, 'Red'), mixs.inputs['Fac'])
    c3.link(land.outputs['BSDF'], mixs.inputs[1]); c3.link(wat.outputs['BSDF'], mixs.inputs[2])
    c3.link(mixs.outputs['Shader'], N.nodes['Material Output'].inputs['Surface'])
    N.nodes.remove(N.nodes['Principled BSDF'])


def m_mapped(tip=1.25):
    """tufts, flowers' stems and pebbles: the broad original colour at their position"""
    def f():
        lay = window_tex(LAYOUT)
        sep = c3.N.nodes.new('ShaderNodeSeparateXYZ'); c3.link(c3.coord(), sep.inputs['Vector'])
        root = c3.ramp(sep.outputs['Z'], (0.0, (0.45, 0.48, 0.42)), (1.0, (tip, tip, tip * 0.9)))
        info = c3.N.nodes.new('ShaderNodeObjectInfo')
        rnd = c3.ramp(info.outputs['Random'], (0.0, (0.7, 0.72, 0.6)), (1.0, (1.25, 1.2, 1.0)))
        col = c3.mix(c3.mix(c3.mix(lay.outputs['Color'], GAIN, 1.0, 'MULTIPLY'), root, 1.0, 'MULTIPLY'), rnd, 1.0, 'MULTIPLY')
        return col, None, 0.85
    return f


def material(name, fn):
    m = bpy.data.materials.new(name); m.use_nodes = True; c3.N = m.node_tree
    if fn is m_terrain:
        fn(); return m
    col, nrm, rough = fn()
    bsdf = c3.N.nodes['Principled BSDF']
    c3.link(col, bsdf.inputs['Base Color']); bsdf.inputs['Roughness'].default_value = rough
    if nrm:
        c3.link(nrm, bsdf.inputs['Normal'])
    return m


TERRAIN, MAPPED = material('terrain', m_terrain), material('mapped', m_mapped())
c3.box('ground', (0, 0, -0.001), (NT + 0.12, NT + 0.12, 0.002), TERRAIN)   # larger than the tile (the 2 px steps of the tile shape stick out ~2 px)

c = H - 15 * NT                 # tile centre row


def world_of(px, py):
    s, d = (px + 0.5 - W / 2) / 29.0, (py + 0.5 - c) / 15.0
    return (s + d) / 2, (s - d) / 2


LIMIT = NT / 2 + 0.06   # a little past the tile edge, like the neighbouring tiles' grass (the engine cuts the exact shape)


def scatter(mask, per_pixel, place):
    ys, xs = np.nonzero(mask)
    for _ in range(int(len(xs) * per_pixel)):
        k = random.randrange(len(xs))
        x, y = world_of(xs[k] + random.random() - 0.5, ys[k] + random.random() - 0.5)
        if abs(x) < LIMIT and abs(y) < LIMIT:
            place(x, y)


# 3D grass: tufts about 1-2 game pixels tall, so they show at 200% zoom
tufts = [c3.tuft_mesh() for _ in range(6)]
for me in tufts:
    me.materials[0] = MAPPED


def tuft(x, y):
    o = bpy.data.objects.new('grass', random.choice(tufts)); c3.sc.collection.objects.link(o)
    sz = random.uniform(0.014, 0.03)
    o.location = (x, y, 0); o.scale = (sz, sz, sz * random.uniform(0.9, 1.5)); o.rotation_euler.z = random.uniform(0, 6.3)


scatter(grassy, TUFT_DENSITY, tuft)
# small flowers and clover on grass
FLOWERS = [c3.material(f'flower{k}', (lambda col: lambda: (col, None, 0.5))(col))
           for k, col in enumerate([(0.9, 0.8, 0.15), (0.95, 0.95, 0.9), (0.55, 0.3, 0.75), (0.9, 0.45, 0.1)])]


def flower(x, y):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.0035, 0.006), location=(x, y, random.uniform(0.01, 0.02)),
                                         segments=6, ring_count=4)
    bpy.context.object.data.materials.append(random.choice(FLOWERS))


scatter(grassy & inside, 0.08, flower)
# pebbles on sand and dirt
def pebble(x, y):
    """stone on sand and dirt: the original's colour at its position, varied size, some sunk into the ground"""
    sz = random.uniform(0.003, 0.012)
    o = c3.rock((x, y, sz * random.uniform(-0.1, 0.3)), sz, flat=random.uniform(0.35, 0.6))
    o.data.materials[0] = PEBBLE
    px, py = min(max(int(W / 2 + 29 * (x + y)), 0), W - 1), min(max(int(c + 15 * (x - y)), 0), H - 1)
    o.color = (*(lin(fill[py, px]) * np.array(c3.GAIN) * random.uniform(0.75, 1.25)), 1)




def m_cobble(per_object=False):
    """laid stones: the original's colour per stone (colour attribute, linear), detail = brightness of a rock photo,
    dark soil in the joints (attribute 'joint'). per_object: loose pebbles, the colour is the object colour."""
    N = c3.N
    col_a = N.nodes.new('ShaderNodeObjectInfo') if per_object else N.nodes.new('ShaderNodeAttribute')
    if not per_object: col_a.attribute_name = 'stone'
    joint = N.nodes.new('ShaderNodeAttribute'); joint.attribute_name = 'joint'
    mp = N.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (24, 24, 24); c3.link(c3.coord(), mp.inputs['Vector'])
    def photo(kind, colour):
        t = N.nodes.new('ShaderNodeTexImage'); t.projection = 'BOX'; t.projection_blend = 0.3
        t.image = bpy.data.images.load(os.path.join(c3.TEX, 'Rock064', f'Rock064_1K-JPG_{kind}.jpg'), check_existing=True)
        if not colour: t.image.colorspace_settings.name = 'Non-Color'
        c3.link(mp.outputs['Vector'], t.inputs['Vector']); return t.outputs['Color']
    bw = N.nodes.new('ShaderNodeRGBToBW'); c3.link(photo('Color', True), bw.inputs['Color'])
    norm = c3.node('ShaderNodeMath'); norm.operation = 'DIVIDE'; c3.link(bw.outputs['Val'], norm.inputs[0]); norm.inputs[1].default_value = 0.162
    col = c3.mix(col_a.outputs['Color'], norm.outputs['Value'], 1.0, 'MULTIPLY')
    if not per_object:
        col = c3.mix(col, c3.ramp(joint.outputs['Fac'], (0.0, (1, 1, 1)), (1.0, (0.30, 0.27, 0.22))), 1.0, 'MULTIPLY')   # soil in the joints
    nm = N.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.7; c3.link(photo('NormalGL', False), nm.inputs['Color'])
    return col, nm.outputs['Normal'], 0.85


def lin(c):
    return np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)


def paving(step=0.042, res=0.004, height=0.010, square=False, jitter=0.38, wear=0.16, joint_w=0.10, tilt_sd=0.12):
    """One mesh of laid stones: Voronoi cells of a jittered grid (one cell = one stone), raised inside the cell
    with worn edges, a small tilt per stone, sunk joints at the cell borders. Cells on grass pixels are left out."""
    row = 1.0 if square else 0.9                               # hex-like rows are 0.9 step apart
    nx, ny = int(2 * LIMIT / step) + 4, int(2 * LIMIT / (step * row)) + 4
    rng = np.random.default_rng(int(os.environ.get('C3_SEED', ID)))
    gx, gy = np.meshgrid(np.arange(nx), np.arange(ny))
    cx = -LIMIT - step + (gx + (0 if square else 0.5) * (gy % 2) + rng.uniform(-jitter, jitter, gx.shape)) * step
    cy = -LIMIT - step + (gy + rng.uniform(-jitter, jitter, gy.shape)) * step * row
    px = np.clip((W / 2 + 29 * (cx + cy)).astype(int), 0, W - 1); py = np.clip((c + 15 * (cx - cy)).astype(int), 0, H - 1)
    paved = dirt[py, px]
    colour = lin(fill[py, px]) * np.array(c3.GAIN) * COBBLE_CAL * rng.uniform(0.82, 1.18, gx.shape)[..., None]
    tilt = rng.normal(0, tilt_sd, gx.shape + (2,)); lift = rng.uniform(0.6, 1.2, gx.shape)
    m = int(2 * LIMIT / res) + 1
    vx, vy = np.meshgrid(np.linspace(-LIMIT, LIMIT, m), np.linspace(-LIMIT, LIMIT, m))
    # nearest and second nearest stone centre among the 5 x 5 grid cells around each vertex
    bi = np.floor((vy + LIMIT + step) / (step * row)).astype(int); bj = np.floor((vx + LIMIT + step) / step).astype(int)
    d1 = np.full(vx.shape, 9.0); d2 = np.full(vx.shape, 9.0); k1 = np.zeros(vx.shape + (2,), int)
    for di in range(-2, 3):
        for dj in range(-2, 3):
            i, j = np.clip(bi + di, 0, ny - 1), np.clip(bj + dj, 0, nx - 1)
            d = np.hypot(vx - cx[i, j], vy - cy[i, j])
            closer = d < d1
            d2 = np.where(closer, d1, np.minimum(d2, d)); d1 = np.where(closer, d, d1)
            k1 = np.where(closer[..., None], np.stack([i, j], -1), k1)
    ki, kj = k1[..., 0], k1[..., 1]
    edge = (d2 - d1) / step                                  # 0 on a cell border, about 0.5+ in the middle
    prof = np.clip(edge / wear, 0, 1) ** 0.6                 # worn, rounded stone edge
    rel_x, rel_y = vx - cx[ki, kj], vy - cy[ki, kj]
    z = height * prof * (lift[ki, kj] + (rel_x * tilt[ki, kj, 0] + rel_y * tilt[ki, kj, 1]) / step)
    joint = 1 - np.clip(edge / joint_w, 0, 1)
    verts = np.stack([vx, vy, np.maximum(z, 0)], -1).reshape(-1, 3)
    idx = np.arange(m * m).reshape(m, m)
    quads = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
    qx, qy = vx[:-1, :-1] + res / 2, vy[:-1, :-1] + res / 2
    qpx = np.clip((W / 2 + 29 * (qx + qy)).astype(int), 0, W - 1); qpy = np.clip((c + 15 * (qx - qy)).astype(int), 0, H - 1)
    # a quad belongs to the stone of its first corner; no stone on grass pixels (thin verges stay green)
    keep = (paved[ki[:-1, :-1], kj[:-1, :-1]] & ~grassy[qpy, qpx]).reshape(-1)
    quads = quads[keep]
    me = bpy.data.meshes.new('paving')
    me.vertices.add(len(verts)); me.vertices.foreach_set('co', verts.astype(np.float32).ravel())
    me.loops.add(quads.size); me.loops.foreach_set('vertex_index', quads.ravel().astype(np.int32))
    me.polygons.add(len(quads)); me.polygons.foreach_set('loop_start', np.arange(0, quads.size, 4, dtype=np.int32))
    me.polygons.foreach_set('loop_total', np.full(len(quads), 4, np.int32))
    me.update(calc_edges=True)
    stone = colour[ki, kj].reshape(-1, 3)[quads.ravel()]       # per face corner: the stone of the quad's first corner
    stone = np.repeat(stone.reshape(-1, 4, 3)[:, :1], 4, 1).reshape(-1, 3)
    a = me.color_attributes.new('stone', 'FLOAT_COLOR', 'CORNER')
    a.data.foreach_set('color', np.concatenate([stone, np.ones((len(stone), 1))], 1).astype(np.float32).ravel())
    j = me.attributes.new('joint', 'FLOAT', 'POINT'); j.data.foreach_set('value', joint.reshape(-1).astype(np.float32))
    for f in me.polygons: f.use_smooth = True
    me.materials.append(material('cobble', m_cobble))
    o = bpy.data.objects.new('paving', me); c3.sc.collection.objects.link(o); o.location.z = 0.0005


if PAVED:
    paving()
elif MOSAIC:   # tesserae about 1 game px, set in straight rows, smooth tops, thin grout
    paving(step=0.026, res=0.0025, height=0.004, square=True, jitter=0.06, wear=0.08, joint_w=0.05, tilt_sd=0.03)
else:
    PEBBLE = material('pebble', lambda: m_cobble(per_object=True))
    scatter(dirt & inside, 0.9, pebble)

c3.render(W, H, tiles=NT, samples=64)


def verge_lock():
    """Paved roads: their grass verges are 1-2 px strips. A thin strip renders ~10% lighter and more yellow than the
    calibration (made on full grass tiles: part of the tuft shadows falls outside the strip). Each verge pixel's 8x8
    block is scaled so its mean is the original pixel's colour; the detail inside the block stays (factor 0.6-1.5)."""
    im = bpy.data.images.load(c3.OUT); w, h = im.size; k = c3.SCALE
    px = np.array(im.pixels[:]).reshape(h, w, 4)[::-1]           # top row first, sRGB
    blocks = px[..., :3].reshape(H, k, W, k, 3)
    mean = blocks.mean((1, 3))
    target = rgb
    f = np.clip(target / np.maximum(mean, 1e-3), 0.6, 1.5)
    f = np.where((grassy & inside)[..., None], f, 1.0)
    px[..., :3] = np.clip((blocks * f[:, None, :, None, :]).reshape(h, w, 3), 0, 1)
    im.pixels.foreach_set(px[::-1].astype(np.float32).ravel()); im.filepath_raw = c3.OUT; im.file_format = 'PNG'; im.save()


if PAVED and not c3.TOP:
    verge_lock()
