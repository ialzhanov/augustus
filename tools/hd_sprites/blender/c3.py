"""Shared Blender scene for re-modelling Caesar III sprites.

World: 1 tile = 1 x 1 units, tile centre at origin, +z up.
Camera: orthographic 2:1 isometric (elevation 30 deg, azimuth 45 deg); view from (+x, -y).
Screen-left faces = -y, screen-right faces = +x.
Sprite pixel <-> world for an n x n building in a W x H sprite (tile centre row c = H - 15 n):
  x_s = W / 2 + 29 (x + y),  y_s = c + 15 (x - y) - 35.5 z.

A sprite script does:  import c3; c3.setup(); ...build...; c3.render(W, H)
Command line: Blender -b -P SCRIPT.py -- OUT.png SCALE [top]
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['out.png', '4']
OUT, SCALE = argv[0], int(argv[1])
TOP = len(argv) > 2 and argv[2] == 'top'   # building-only pass for <id>_top.png
N = None  # node tree of the material being built
M = {}
GROUND = set()   # names of ground objects (cut out in the top pass)
sc = None


def setup(seed=29, orig=None):
    global sc
    random.seed(int(os.environ.get('C3_SEED', seed)))   # C3_SEED: a new variation (viewer 'Generate')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    global ROCK_MESH
    ROCK_MESH = None
    M.update({k: material(k, f) for k, f in MATERIALS.items()})
    global CLOUDS, CRACKLE
    CLOUDS = bpy.data.textures.new('clouds', 'CLOUDS'); CLOUDS.noise_scale = 0.35
    CRACKLE = bpy.data.textures.new('crackle', 'VORONOI'); CRACKLE.noise_scale = 0.25; CRACKLE.distance_metric = 'DISTANCE'


class ground:
    """with c3.ground(): ... -> objects created inside are ground (cut out in the top pass)"""
    def __enter__(self):
        self.before = set(bpy.data.objects.keys())

    def __exit__(self, *a):
        GROUND.update(set(bpy.data.objects.keys()) - self.before)


# ---------- node helpers ----------
def node(kind, **inputs):
    n = N.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def link(a, b):
    N.links.new(a, b)


def ramp(fac, *stops):
    r = N.nodes.new('ShaderNodeValToRGB'); els = r.color_ramp.elements
    for i, (p, c) in enumerate(stops):
        e = els[i] if i < 2 else els.new(p); e.position = p; e.color = (*c, 1)
    link(fac, r.inputs['Fac']); return r.outputs['Color']


def mix(a, b, f, mode='MIX'):
    m = N.nodes.new('ShaderNodeMix'); m.data_type = 'RGBA'; m.blend_type = mode
    for sock, val in (('A', a), ('B', b), ('Factor', f)):
        if isinstance(val, (tuple, float)):
            m.inputs[sock].default_value = (*val, 1) if isinstance(val, tuple) else val
        else:
            link(val, m.inputs[sock])
    return m.outputs['Result']


def bump(h, strength, dist=0.02):
    b = node('ShaderNodeBump', Strength=strength, Distance=dist); link(h, b.inputs['Height']); return b.outputs['Normal']


def material(name, fn):
    global N
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree
    bsdf = N.nodes['Principled BSDF']
    col, nrm, rough = fn()
    if isinstance(col, tuple):
        bsdf.inputs['Base Color'].default_value = (*col, 1)
    else:
        link(col, bsdf.inputs['Base Color'])
    if nrm: link(nrm, bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = rough
    return m


def coord():
    return node('ShaderNodeTexCoord').outputs['Object']


# ---------- materials ----------
def m_roof():
    # tile courses: wave bands along the slope; per-tile colour from voronoi cells
    v = coord()
    w = node('ShaderNodeTexWave', Scale=34.0, Distortion=0.3); w.wave_type = 'BANDS'; w.bands_direction = 'Z'
    link(v, w.inputs['Vector'])
    cols = node('ShaderNodeTexWave', Scale=30.0, Distortion=0.5); cols.wave_type = 'BANDS'; cols.bands_direction = 'DIAGONAL'
    link(v, cols.inputs['Vector'])
    vor = node('ShaderNodeTexVoronoi', Scale=38.0); link(v, vor.inputs['Vector'])
    tile = ramp(vor.outputs['Color'], (0.0, (0.62, 0.14, 0.02)), (0.5, (0.95, 0.38, 0.08)), (1.0, (1.0, 0.58, 0.22)))
    dirt = node('ShaderNodeTexNoise', Scale=9.0, Detail=6.0); link(v, dirt.inputs['Vector'])
    col = mix(tile, ramp(dirt.outputs['Fac'], (0.35, (0.55, 0.45, 0.40)), (0.65, (1, 1, 1))), 1.0, 'MULTIPLY')
    col = mix(col, ramp(w.outputs['Fac'], (0.0, (0.62, 0.55, 0.52)), (0.4, (1, 1, 1))), 1.0, 'MULTIPLY')
    h = node('ShaderNodeMath'); h.operation = 'ADD'; link(w.outputs['Fac'], h.inputs[0]); link(cols.outputs['Fac'], h.inputs[1])
    return col, bump(h.outputs['Value'], 0.8, 0.01), 0.7


def m_plaster():
    v = coord()
    n = node('ShaderNodeTexNoise', Scale=7.0, Detail=10.0, Roughness=0.65); link(v, n.inputs['Vector'])
    base = ramp(n.outputs['Fac'], (0.35, (0.42, 0.40, 0.24)), (0.65, (0.66, 0.62, 0.38)))
    # patches where the plaster fell off and the stone shows
    p = node('ShaderNodeTexNoise', Scale=4.0, Detail=4.0); link(v, p.inputs['Vector'])
    patch = ramp(p.outputs['Fac'], (0.58, (0, 0, 0)), (0.64, (1, 1, 1)))
    stone = N.nodes.new('ShaderNodeTexVoronoi'); stone.feature = 'DISTANCE_TO_EDGE'
    stone.inputs['Scale'].default_value = 38.0; link(v, stone.inputs['Vector'])
    cell = node('ShaderNodeTexVoronoi', Scale=38.0); link(v, cell.inputs['Vector'])
    stone_c = mix(ramp(cell.outputs['Color'], (0.0, (0.55, 0.50, 0.38)), (1.0, (0.76, 0.70, 0.55))),
                  ramp(stone.outputs['Distance'], (0.0, (0.30, 0.27, 0.22)), (0.08, (1, 1, 1))), 1.0, 'MULTIPLY')
    col = mix(base, stone_c, patch)
    # grime toward the ground
    sep = N.nodes.new('ShaderNodeSeparateXYZ'); link(v, sep.inputs['Vector'])
    g = node('ShaderNodeMapRange', **{'From Min': 0.0, 'From Max': 0.14, 'To Min': 0.75, 'To Max': 0.0})
    link(sep.outputs['Z'], g.inputs['Value'])
    col = mix(col, (0.40, 0.36, 0.26), g.outputs['Result'], 'MULTIPLY')
    return col, bump(n.outputs['Fac'], 0.3), 0.95


GRASS_REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grass_ref.png')   # game grass tile 306
GAIN = (1.224,1.350,1.624)       # 1 / light on flat ground: base colour * GAIN renders as the image colour
DETAIL_SCALE, DLO, DHI = [float(v) for v in os.environ.get('C3_GRASS', '24,0.6,1.4').split(',')]
TLO, THI = [float(v) for v in os.environ.get('C3_TUFT', '0.5,1.5').split(',')]


def grass_ref_colour(position):
    """Colour of the game's grass tile at a world position (x, y): tile 306 repeated on every tile."""
    sep = N.nodes.new('ShaderNodeSeparateXYZ'); link(position, sep.inputs['Vector'])
    def frac(sock):                                    # position inside its own tile, -0.5 .. 0.5
        a = node('ShaderNodeMath'); a.operation = 'ADD'; a.inputs[1].default_value = 0.5; link(sock, a.inputs[0])
        f = node('ShaderNodeMath'); f.operation = 'FRACT'; link(a.outputs['Value'], f.inputs[0])
        return f.outputs['Value']
    fx, fy = frac(sep.outputs['X']), frac(sep.outputs['Y'])
    def lin(a_sock, b_sock, sa, sb, c):               # sa * a + sb * b + c
        m1 = node('ShaderNodeMath'); m1.operation = 'MULTIPLY_ADD'; link(a_sock, m1.inputs[0]); m1.inputs[1].default_value = sa
        m1.inputs[2].default_value = c
        m2 = node('ShaderNodeMath'); m2.operation = 'MULTIPLY_ADD'; link(b_sock, m2.inputs[0]); m2.inputs[1].default_value = sb
        link(m1.outputs['Value'], m2.inputs[2]); return m2.outputs['Value']
    u = lin(fx, fy, 0.5, 0.5, -0.5 + 0.5)             # fx, fy are offset by +0.5: u = 0.5 + 0.5 (x + y)
    v = lin(fx, fy, -0.5, 0.5, 0.5)                   # v = 0.5 - 0.5 (x - y)
    comb = N.nodes.new('ShaderNodeCombineXYZ'); link(u, comb.inputs['X']); link(v, comb.inputs['Y'])
    t = N.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(GRASS_REF, check_existing=True)
    t.interpolation = 'Cubic'; t.extension = 'EXTEND'; link(comb.outputs['Vector'], t.inputs['Vector'])
    g = N.nodes.new('ShaderNodeMix'); g.data_type = 'RGBA'; g.blend_type = 'MULTIPLY'; g.inputs['Factor'].default_value = 1.0
    g.inputs['B'].default_value = tuple(GAIN[i] * GRASS_CAL[i] for i in range(3)) + (1,); link(t.outputs['Color'], g.inputs['A'])
    return g.outputs['Result']


GRASS_CAL = [float(v) for v in os.environ.get('C3_GRASS_CAL', '1.165,1.168,0.851').split(',')]   # grass render vs tile 306, see calibrate_grass.sh


def match_ground(orig_png):
    """Tint the grass so its colour at the front tile edges matches the original sprite (call before materials)."""
    def edge_mean(path, tile_h):
        im = bpy.data.images.load(path, check_existing=True); w, h = im.size
        import numpy as np
        px = np.array(im.pixels[:]).reshape(h, w, 4)[::-1]
        n = (w + 2) // 60; cy = (h - 15 * n) if tile_h else h / 2
        yy, xx = np.mgrid[0:h, 0:w]
        d = np.abs(xx + 0.5 - w / 2) / (w / 2) + np.abs(yy + 0.5 - cy) / (15 * n)
        g = px[..., 1]; m = (px[..., 3] > 0) & (d > 0.78) & (d < 0.97) & (yy > cy) & (g > px[..., 0] + 0.02) & (g > px[..., 2] + 0.06)
        c = px[m][:, :3]; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)   # linear
        return c.mean(0)
    o, r = edge_mean(orig_png, True), edge_mean(GRASS_REF, False)
    GROUND_TINT[:] = [float(o[i] / max(r[i], 1e-4)) for i in range(3)]


def m_grass():
    """ground: the game's grass tile colours x fine detail"""
    v = coord()
    # detail about one game pixel in size (1/41 unit) with mean 1.0, plus finer detail for the zoomed view
    n = node('ShaderNodeTexNoise', Scale=DETAIL_SCALE, Detail=4.0, Roughness=0.6); link(v, n.inputs['Vector'])
    fine = node('ShaderNodeTexNoise', Scale=140.0, Detail=8.0); link(v, fine.inputs['Vector'])
    detail = mix(ramp(n.outputs['Fac'], (0.4, (DLO,) * 3), (0.6, (DHI,) * 3)),   # noise Fac is mostly 0.4 .. 0.6
                 ramp(fine.outputs['Fac'], (0.3, (0.85,) * 3), (0.7, (1.15,) * 3)), 1.0, 'MULTIPLY')
    return mix(grass_ref_colour(v), detail, 1.0, 'MULTIPLY'), bump(fine.outputs['Fac'], 0.4, 0.005), 1.0


def m_stone():
    # per-object random tint so each block differs
    info = N.nodes.new('ShaderNodeObjectInfo')
    tint = ramp(info.outputs['Random'], (0.0, (0.66, 0.54, 0.30)), (0.5, (0.88, 0.76, 0.50)), (1.0, (1.0, 0.92, 0.70)))
    v = coord(); n = node('ShaderNodeTexNoise', Scale=30.0, Detail=8.0); link(v, n.inputs['Vector'])
    col = mix(tint, ramp(n.outputs['Fac'], (0.3, (0.80, 0.78, 0.74)), (0.7, (1, 1, 1))), 1.0, 'MULTIPLY')
    return col, bump(n.outputs['Fac'], 0.6, 0.01), 0.9


def m_flags():
    v = coord()
    vor = node('ShaderNodeTexVoronoi', Scale=22.0); link(v, vor.inputs['Vector'])
    c = ramp(vor.outputs['Color'], (0.0, (0.80, 0.58, 0.44)), (0.5, (0.92, 0.74, 0.56)), (1.0, (1.0, 0.88, 0.66)))
    edge = N.nodes.new('ShaderNodeTexVoronoi'); edge.feature = 'DISTANCE_TO_EDGE'; edge.inputs['Scale'].default_value = 22.0
    link(v, edge.inputs['Vector'])
    joint = ramp(edge.outputs['Distance'], (0.0, (0.25, 0.20, 0.15)), (0.06, (1, 1, 1)))
    return mix(c, joint, 1.0, 'MULTIPLY'), bump(edge.outputs['Distance'], 0.5, 0.01), 0.9


def m_tile():
    # one colour per tile (object random) plus fine grime
    info = N.nodes.new('ShaderNodeObjectInfo')
    tint = ramp(info.outputs['Random'], (0.0, (0.50, 0.11, 0.02)), (0.45, (0.85, 0.27, 0.06)), (1.0, (1.0, 0.45, 0.15)))
    v = coord(); n = node('ShaderNodeTexNoise', Scale=60.0, Detail=8.0); link(v, n.inputs['Vector'])
    col = mix(tint, ramp(n.outputs['Fac'], (0.3, (0.62, 0.55, 0.5)), (0.7, (1, 1, 1))), 1.0, 'MULTIPLY')
    return col, bump(n.outputs['Fac'], 0.3, 0.005), 0.92


def m_blade():
    """grass blades: the grass tile colour at the tuft root, dark at the base, light at the tip"""
    info = N.nodes.new('ShaderNodeObjectInfo')
    sep = N.nodes.new('ShaderNodeSeparateXYZ'); link(coord(), sep.inputs['Vector'])
    tip = ramp(sep.outputs['Z'], (0.0, (0.55, 0.58, 0.5)), (1.0, (1.45, 1.45, 1.3)))
    pn = node('ShaderNodeTexNoise', Scale=DETAIL_SCALE, Detail=4.0, Roughness=0.6); link(info.outputs['Location'], pn.inputs['Vector'])
    rnd = ramp(pn.outputs['Fac'], (0.4, (TLO, TLO, TLO * 0.9)), (0.6, (THI, THI, THI * 0.95)))   # light/dark patches ~1 game px
    col = mix(mix(grass_ref_colour(info.outputs['Location']), tip, 1.0, 'MULTIPLY'), rnd, 1.0, 'MULTIPLY')
    return col, None, 0.8


def m_wood():
    v = coord()
    planks = node('ShaderNodeTexWave', Scale=55.0, Distortion=1.5, Detail=6.0); planks.wave_type = 'BANDS'
    planks.bands_direction = 'X'; link(v, planks.inputs['Vector'])
    col = ramp(planks.outputs['Fac'], (0.0, (0.10, 0.05, 0.02)), (0.5, (0.30, 0.17, 0.08)), (1.0, (0.40, 0.25, 0.12)))
    return col, bump(planks.outputs['Fac'], 0.5, 0.004), 0.8


def m_plinth():
    v = coord(); n = node('ShaderNodeTexNoise', Scale=25.0, Detail=10.0); link(v, n.inputs['Vector'])
    edge = N.nodes.new('ShaderNodeTexVoronoi'); edge.feature = 'DISTANCE_TO_EDGE'; edge.inputs['Scale'].default_value = 20.0
    link(v, edge.inputs['Vector'])
    col = mix(ramp(n.outputs['Fac'], (0.3, (0.40, 0.36, 0.28)), (0.7, (0.62, 0.57, 0.45))),
              ramp(edge.outputs['Distance'], (0.0, (0.35, 0.3, 0.25)), (0.06, (1, 1, 1))), 1.0, 'MULTIPLY')
    return col, bump(n.outputs['Fac'], 0.6, 0.01), 0.95


def m_fabric(c1, c2):
    """canvas: weave bump, stains, colour between c1 and c2"""
    def f():
        v = coord()
        n = node('ShaderNodeTexNoise', Scale=9.0, Detail=8.0); link(v, n.inputs['Vector'])
        col = ramp(n.outputs['Fac'], (0.3, c1), (0.7, c2))
        st = node('ShaderNodeTexNoise', Scale=3.0, Detail=3.0); link(v, st.inputs['Vector'])
        col = mix(col, ramp(st.outputs['Fac'], (0.5, (0.55, 0.5, 0.42)), (0.62, (1, 1, 1))), 1.0, 'MULTIPLY')
        weave = node('ShaderNodeTexWave', Scale=160.0); weave.wave_type = 'BANDS'; weave.bands_direction = 'DIAGONAL'
        link(v, weave.inputs['Vector'])
        return col, bump(weave.outputs['Fac'], 0.15, 0.002), 0.95
    return f


def m_pot():
    info = N.nodes.new('ShaderNodeObjectInfo')
    tint = ramp(info.outputs['Random'], (0.0, (0.45, 0.10, 0.04)), (1.0, (0.75, 0.22, 0.08)))
    v = coord(); n = node('ShaderNodeTexNoise', Scale=40.0, Detail=6.0); link(v, n.inputs['Vector'])
    return mix(tint, ramp(n.outputs['Fac'], (0.3, (0.7, 0.65, 0.6)), (0.7, (1, 1, 1))), 1.0, 'MULTIPLY'), bump(n.outputs['Fac'], 0.2, 0.004), 0.7


def m_pole():
    v = coord(); n = node('ShaderNodeTexNoise', Scale=50.0, Detail=4.0); link(v, n.inputs['Vector'])
    return ramp(n.outputs['Fac'], (0.3, (0.80, 0.74, 0.60)), (0.7, (0.95, 0.91, 0.82))), None, 0.8


def m_dirt():
    v = coord(); n = node('ShaderNodeTexNoise', Scale=22.0, Detail=10.0); link(v, n.inputs['Vector'])
    d = node('ShaderNodeTexNoise', Scale=6.0, Detail=3.0); link(v, d.inputs['Vector'])
    col = mix(ramp(n.outputs['Fac'], (0.42, (0.30, 0.24, 0.15)), (0.58, (0.82, 0.72, 0.52))), (0.30, 0.38, 0.12),
              ramp(d.outputs['Fac'], (0.55, (0, 0, 0)), (0.7, (1, 1, 1))))
    return col, bump(n.outputs['Fac'], 0.6, 0.01), 1.0


MATERIALS = dict(
    wood=m_wood, plinth=m_plinth, tile=m_tile, blade=m_blade, roof=m_roof, plaster=m_plaster, grass=m_grass,
    stone=m_stone, flags=m_flags, pot=m_pot, pole=m_pole, dirt=m_dirt,
    dark=lambda: ((0.025, 0.02, 0.015), None, 0.9))


# ---------- geometry helpers ----------
def box(name, loc, size, m, bevel=0.0, rot=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=(0, 0, rot))
    o = bpy.context.object; o.name = name; o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new('bv', 'BEVEL'); mod.width = bevel; mod.segments = 2
    o.data.materials.append(M[m] if isinstance(m, str) else m); return o


ROCK_MESH = None   # the icosphere of every rock, made once per scene (setup() clears it)


def rock(loc, s, flat=0.65):
    """a rough stone; no bpy.ops: each op updates the whole scene (6000 pebbles of a 3x3 rock tile took > 30 min)"""
    global ROCK_MESH
    if ROCK_MESH is None:
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
        ROCK_MESH = bpy.data.meshes.new('rock'); bm.to_mesh(ROCK_MESH); bm.free()
    o = bpy.data.objects.new('rock', ROCK_MESH.copy()); sc.collection.objects.link(o); o.location = loc
    o.scale = (s * random.uniform(0.8, 1.6), s * random.uniform(0.7, 1.2), s * flat * random.uniform(0.8, 1.2))
    o.rotation_euler = (random.uniform(-.2, .2), random.uniform(-.2, .2), random.uniform(0, math.pi))
    d = o.modifiers.new('d', 'DISPLACE'); d.texture = CLOUDS; d.strength = 0.35
    d2 = o.modifiers.new('d2', 'DISPLACE'); d2.texture = CRACKLE; d2.strength = 0.18
    o.data.materials.append(M['stone']); return o


def block(loc, s):
    """squarish cut stone, slightly tilted"""
    o = box('blk', loc, (s * random.uniform(1, 1.8), s * random.uniform(0.8, 1.2), s * random.uniform(0.6, 1)),
            M['stone'], bevel=s * 0.15, rot=random.uniform(0, math.pi))
    o.rotation_euler.x = random.uniform(-.15, .15); return o


def rubble(p0, p1, n, gaps=(), h=1.0):
    p0, p1 = Vector(p0), Vector(p1)
    for k in range(n):
        t = (k + random.uniform(0.15, 0.85)) / n
        if any(g0 < t < g1 for g0, g1 in gaps):
            continue
        p = p0.lerp(p1, t) + Vector((random.uniform(-.02, .02), random.uniform(-.02, .02)))
        s = random.uniform(0.022, 0.045) * h
        (block if random.random() < 0.4 else rock)((p.x, p.y, s * 0.3), s)
        if random.random() < 0.3:              # second course
            rock((p.x, p.y, s * 0.9), s * 0.7)


def tuft_mesh():
    bm = bmesh.new()
    for k in range(5):
        a = k * 2 * math.pi / 5 + random.uniform(-.3, .3)
        lean = random.uniform(0.15, 0.4)
        h = random.uniform(0.6, 1.0)
        base = Vector((math.cos(a), math.sin(a), 0)) * 0.15
        side = Vector((-math.sin(a), math.cos(a), 0)) * 0.12
        tip = Vector((math.cos(a) * lean, math.sin(a) * lean, h))
        bm.faces.new([bm.verts.new(base - side), bm.verts.new(base + side), bm.verts.new(tip)])
    me = bpy.data.meshes.new('tuft'); bm.to_mesh(me); me.materials.append(M['blade'])
    return me



def grass(count, open_ground, size=(0.010, 0.022), half=0.49):
    """scatter grass tufts on the tile where open_ground(x, y) is true"""
    tufts = [tuft_mesh() for _ in range(4)]
    for _ in range(count):                             # count = tufts per full tile: same density on every sprite
        x, y = random.uniform(-half, half), random.uniform(-half, half)
        if not open_ground(x, y):
            continue
        o = bpy.data.objects.new('grass', random.choice(tufts)); sc.collection.objects.link(o)
        sz = random.uniform(*size)
        o.location = (x, y, 0); o.scale = (sz, sz, sz * random.uniform(0.8, 1.4)); o.rotation_euler.z = random.uniform(0, 6.3)
        GROUND.add(o.name)


def link_obj(name, me, mat=None):
    o = bpy.data.objects.new(name, me); sc.collection.objects.link(o)
    if mat:
        me.materials.append(M[mat] if isinstance(mat, str) else mat)
    return o


LIGHT = dict(el=35, az=-50, sun=4.2, fill=0.5, amb=0.02)   # hard light: original-like contrast (check.py contrast)
LIGHT.update({k: float(v) for k, v in (kv.split('=') for kv in os.environ.get('C3_LIGHT', '').split(',') if kv)})


def render(W, H, tiles=1, samples=128, edge_fade=False):
    """W x H sprite of an n x n building; writes OUT (or the top part when TOP).
    edge_fade: shadows of the building fade out toward the front tile edges (a second render without them is blended
    in), so a long shadow does not stop at the tile edge where the engine cuts the sprite (the next tile is lit)."""
    if TOP:
        for name in GROUND:
            bpy.data.objects[name].is_holdout = True
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = LIGHT['sun']; sun.color = (1.0, 0.90, 0.74); sun.angle = math.radians(3)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(90 - LIGHT['el']), 0, math.radians(LIGHT['az']))   # from the front-left
    fill = bpy.data.lights.new('fill', 'SUN'); fill.energy = LIGHT['fill']; fill.color = (0.85, 0.9, 1.0); fill.use_shadow = False
    fo = bpy.data.objects.new('fill', fill); sc.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(80), 0, math.radians(60))     # low, from the front-right: lifts shaded +x walls
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.52, 0.45, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = LIGHT['amb']

    cam = bpy.data.cameras.new('cam'); cam.type = 'ORTHO'
    co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
    co.rotation_euler = (math.radians(60), 0, math.radians(45))
    co.location = Vector((7.07, -7.07, 5.77))
    foot_h = 15 * tiles                                   # half the footprint height: tile centre above the bottom
    cam.ortho_scale = math.sqrt(2) * tiles * W / (60 * tiles - 2)   # footprint (n tiles) fills 60 n - 2 px
    if H > W:   # Blender fits ortho_scale to the larger side: a tree sprite (58 x 67) rendered 15% too large
        cam.ortho_scale *= H / W
    if W >= H:
        px = cam.ortho_scale / W
    else:
        px = cam.ortho_scale / H
    cam.shift_y = (H / 2 - foot_h) * px / cam.ortho_scale
    sc.render.resolution_x, sc.render.resolution_y = W * SCALE, H * SCALE
    sc.render.film_transparent = True
    sc.render.engine = 'CYCLES'; sc.cycles.samples = samples; sc.cycles.device = 'GPU'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'; prefs.get_devices()
    for d in prefs.devices: d.use = True
    sc.view_settings.view_transform = 'Standard'
    if TOP:
        sc.render.use_border = sc.render.use_crop_to_border = True
        sc.render.border_min_x, sc.render.border_max_x = 0.0, 1.0
        sc.render.border_min_y, sc.render.border_max_y = foot_h / H, 1.0   # rows 0 .. H - foot_h (top part)
    sc.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
    if edge_fade and not TOP:
        import numpy as np
        for o in sc.objects:
            if o.name not in GROUND and o.type == 'MESH':
                o.visible_shadow = False
        sc.render.filepath = OUT.replace('.png', '_noshadow.png')
        bpy.ops.render.render(write_still=True)
        a, b = (bpy.data.images.load(f) for f in (OUT, sc.render.filepath))
        w, h = a.size
        pa = np.array(a.pixels[:]).reshape(h, w, 4); pb = np.array(b.pixels[:]).reshape(h, w, 4)   # bottom row first
        yy, xx = np.mgrid[0:h, 0:w] / SCALE
        cy = foot_h                                      # tile centre, rows from the bottom
        dist = np.abs(xx - W / 2) / (W / 2) + np.abs(yy - cy) / (15 * tiles)
        f = np.clip((dist - 0.6) / 0.25, 0, 1) * np.clip((cy + 3 - yy) / 6, 0, 1)    # front half: no building there
        f = (f * f * (3 - 2 * f))[..., None]
        out = pa + (np.maximum(pb, pa) - pa) * f         # only lighten: remove shadow, keep everything else
        a.pixels.foreach_set(out.astype(np.float32).ravel()); a.filepath_raw = OUT; a.file_format = 'PNG'; a.save()
        os.remove(sc.render.filepath)


# ---------- props (shared by all sprites) ----------
def _mat(name, fn):
    if name not in M:
        M[name] = material(name, fn)
    return M[name]


def lathe(name, profile, loc, seg=16, mat=None, s=1.0):
    """Surface of revolution from (radius, height) pairs."""
    x, y, z = loc
    bm = bmesh.new(); rings = []
    for r, h in profile:
        rings.append([bm.verts.new((x + r * s * math.cos(2 * math.pi * k / seg), y + r * s * math.sin(2 * math.pi * k / seg), z + h * s))
                      for k in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for k in range(seg):
            bm.faces.new([a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]])
    me = bpy.data.meshes.new(name); bm.to_mesh(me)
    for f in me.polygons: f.use_smooth = True
    return link_obj(name, me, mat)


def m_clay(c1, c2):
    def f():
        info = N.nodes.new('ShaderNodeObjectInfo')
        tint = ramp(info.outputs['Random'], (0.0, c1), (1.0, c2))
        v = coord(); n = node('ShaderNodeTexNoise', Scale=60.0, Detail=8.0); link(v, n.inputs['Vector'])
        sep = N.nodes.new('ShaderNodeSeparateXYZ'); link(v, sep.inputs['Vector'])
        dirt = ramp(n.outputs['Fac'], (0.35, (0.55, 0.5, 0.45)), (0.65, (1.1, 1.05, 1.0)))
        return mix(tint, dirt, 1.0, 'MULTIPLY'), bump(n.outputs['Fac'], 0.3, 0.003), 0.55
    return f


def amphora(x, y, s=1.0, rot=0.0):
    _mat('clay', m_clay((0.42, 0.09, 0.03), (0.78, 0.25, 0.08)))
    prof = [(0.0, 0.0), (0.006, 0.0), (0.016, 0.01), (0.024, 0.03), (0.025, 0.045), (0.02, 0.06), (0.011, 0.07),
            (0.008, 0.08), (0.008, 0.09), (0.012, 0.094), (0.009, 0.097)]
    o = lathe('amphora', prof, (x, y, 0), mat=M['clay'], s=s * 1.3)
    o.rotation_euler = (random.uniform(-.05, .05), random.uniform(-.05, .05), rot)
    return o


def bowl_pot(x, y, s=1.0):
    _mat('clay', m_clay((0.42, 0.09, 0.03), (0.78, 0.25, 0.08)))
    return lathe('pot', [(0, 0), (0.014, 0), (0.026, 0.014), (0.027, 0.03), (0.02, 0.04), (0.022, 0.044)], (x, y, 0), mat=M['clay'], s=s * 1.3)


def sack(x, y, s=1.0):
    _mat('burlap', m_photo('Fabric061', scale=9.0, tint=(2.5, 2.15, 1.55), normal=1.0))   # cream-tan sacking
    # a filled sack lying on its side: elongated, flattened, lumpy, with a gathered end
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(x, y, 0.016 * s), segments=20, ring_count=12)
    o = bpy.context.object; o.scale = (0.042 * s, 0.026 * s, 0.018 * s); o.rotation_euler.z = random.uniform(0, 3)
    d = o.modifiers.new('d', 'DISPLACE'); d.texture = CLOUDS; d.strength = 0.25
    o.data.materials.append(M['burlap']); return o


def basket(x, y, s=1.0, produce=((0.70, 0.08, 0.04), (0.85, 0.55, 0.08), (0.25, 0.45, 0.08))):
    _mat('wicker', m_wicker)
    o = lathe('basket', [(0, 0), (0.024, 0), (0.03, 0.025), (0.031, 0.03), (0.027, 0.03), (0.022, 0.006), (0, 0.006)],
              (x, y, 0), mat=M['wicker'], s=s)
    c = random.choice(produce)
    fm = _mat(f'fruit{c}', lambda: (c, None, 0.35))
    for k in range(7):                                 # heaped fruit
        a, r = random.uniform(0, 6.3), random.uniform(0, 0.018 * s)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.007 * s, location=(x + r * math.cos(a), y + r * math.sin(a), 0.03 * s + 0.004 * (k % 3)),
                                             segments=8, ring_count=6)
        bpy.context.object.data.materials.append(fm)
    return o


def m_wicker():
    v = coord()
    w1 = node('ShaderNodeTexWave', Scale=120.0); w1.wave_type = 'BANDS'; w1.bands_direction = 'Z'; link(v, w1.inputs['Vector'])
    w2 = node('ShaderNodeTexWave', Scale=120.0); w2.wave_type = 'RINGS'; link(v, w2.inputs['Vector'])
    h = node('ShaderNodeMath'); h.operation = 'MULTIPLY'; link(w1.outputs['Fac'], h.inputs[0]); link(w2.outputs['Fac'], h.inputs[1])
    col = ramp(h.outputs['Value'], (0.0, (0.25, 0.15, 0.06)), (1.0, (0.70, 0.52, 0.28)))
    return col, bump(h.outputs['Value'], 0.6, 0.003), 0.8


def m_stripes(c1, c2):
    def f():
        v = coord(); w = node('ShaderNodeTexWave', Scale=40.0, Distortion=0.4); w.wave_type = 'BANDS'; w.bands_direction = 'X'
        link(v, w.inputs['Vector'])
        return ramp(w.outputs['Fac'], (0.45, c1), (0.55, c2)), bump(w.outputs['Fac'], 0.1, 0.002), 0.95
    return f


def blanket_roll(x, y, rot, colours=((0.55, 0.12, 0.08), (0.85, 0.78, 0.60)), s=1.7):
    key = f'blanket{colours}'
    _mat(key, m_stripes(*colours))
    bpy.ops.mesh.primitive_cylinder_add(radius=0.016 * s, depth=0.08 * s, location=(x, y, 0.016 * s), rotation=(math.pi / 2, 0, rot), vertices=16)
    o = bpy.context.object; o.data.materials.append(M[key]); return o


def stool(x, y):
    box('seat', (x, y, 0.03), (0.04, 0.04, 0.008), 'wood', bevel=0.002, rot=random.uniform(0, 1))
    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        box('leg', (x + dx * 0.013, y + dy * 0.013, 0.013), (0.005, 0.005, 0.026), 'wood')


def firepit(x, y, s=1.5):
    """ring of stones, charred logs, glowing embers, cooking pot on a tripod (scaled by s)"""
    _firepit(x, y, s)


def _firepit(x, y, s):
    for k in range(9):
        a = 2 * math.pi * k / 9
        rock((x + 0.04 * s * math.cos(a), y + 0.04 * s * math.sin(a), 0.006 * s), 0.011 * s, flat=0.7)
    _mat('char', lambda: ((0.03, 0.025, 0.02), None, 0.9))
    def ember():
        e = N.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = (1.0, 0.35, 0.05, 1); e.inputs['Strength'].default_value = 6.0
        link(e.outputs['Emission'], N.nodes['Material Output'].inputs['Surface'])
        return (0.1, 0.02, 0.0), None, 1.0
    _mat('ember', ember)
    for k in range(4):
        a = random.uniform(0, 3.14)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.005 * s, depth=0.05 * s, location=(x, y, 0.008 * s), rotation=(math.pi / 2, 0, a), vertices=8)
        bpy.context.object.data.materials.append(M['char'])
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.016 * s, location=(x, y, 0.002 * s), segments=10, ring_count=6)
    e = bpy.context.object; e.scale.z = 0.35; e.data.materials.append(M['ember'])
    for k in range(3):                                 # tripod
        a = 2 * math.pi * k / 3
        p0 = Vector((x + 0.045 * s * math.cos(a), y + 0.045 * s * math.sin(a), 0)); p1 = Vector((x, y, 0.09 * s))
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0025 * s, depth=(p1 - p0).length, location=(p0 + p1) / 2, vertices=6)
        o = bpy.context.object; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = (p1 - p0).to_track_quat('Z', 'Y')
        o.data.materials.append(M['wood'])
    _mat('iron', lambda: ((0.06, 0.055, 0.05), None, 0.45))
    lathe('cauldron', [(0, 0), (0.012, 0.002), (0.018, 0.012), (0.017, 0.022), (0.016, 0.024)], (x, y, 0.035 * s), mat=M['iron'], s=s)


def straw(x, y, r, n=60):
    _mat('straw', lambda: ((0.85, 0.70, 0.35), None, 0.8))
    for _ in range(n):
        a, d = random.uniform(0, 6.3), r * math.sqrt(random.random())
        px, py = x + d * math.cos(a), y + d * math.sin(a)
        b = random.uniform(0, 3.14); l = random.uniform(0.008, 0.02)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0007, depth=l, location=(px, py, 0.001), rotation=(math.pi / 2, 0, b), vertices=4)
        o = bpy.context.object; o.data.materials.append(M['straw']); GROUND.add(o.name)


# ---------- CC0 photo materials (ambientCG, tex/<id>/) ----------
TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tex')   # fetch_textures.sh


def m_photo(tex_id, scale=4.0, tint=(1.0, 1.0, 1.0), normal=1.0, extra=None):
    """Box-projected photo texture (colour x tint, normal, roughness) in object space.
    extra(col) -> col may add multipliers (seams, dirt, bleaching) on top of the photo colour."""
    def f():
        v = coord()
        mp = N.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (scale, scale, scale); link(v, mp.inputs['Vector'])
        def img(kind, colour):
            t = N.nodes.new('ShaderNodeTexImage'); t.projection = 'BOX'; t.projection_blend = 0.3
            t.image = bpy.data.images.load(os.path.join(TEX, tex_id, f'{tex_id}_1K-JPG_{kind}.jpg'), check_existing=True)
            if not colour:
                t.image.colorspace_settings.name = 'Non-Color'
            link(mp.outputs['Vector'], t.inputs['Vector']); return t.outputs['Color']
        col = mix(img('Color', True), tint, 1.0, 'MULTIPLY')
        if extra:
            col = extra(col, v)
        nm = N.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = normal; link(img('NormalGL', False), nm.inputs['Color'])
        bsdf = N.nodes['Principled BSDF']; link(img('Roughness', False), bsdf.inputs['Roughness'])
        return col, nm.outputs['Normal'], 0.9
    return f
