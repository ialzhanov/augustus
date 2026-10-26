"""Re-model Caesar III 'casa' (house level 4, group 29, image 0) in Blender.

usage: Blender -b -P casa.py -- OUT.png SCALE
World: 1 tile = 1 x 1 units, tile centre at origin, +z up.
Camera: orthographic 2:1 isometric (elevation 30 deg, azimuth 45 deg); view from (+x, -y).
Screen-left wall = -y face (door), screen-right wall = +x face (windows).
Sprite pixel <-> world (58 x 36 sprite): x_s = 29 + 29 (x + y), y_s = 21 + 15 (x - y) - 35.5 z.
Sizes below were measured from the original sprite with these formulas.
"""
import bpy, bmesh, math, random, sys
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index('--') + 1:]
OUT, SCALE = argv[0], int(argv[1])
TOP = len(argv) > 2 and argv[2] == 'top'   # building-only pass for <id>_top.png
random.seed(29)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
N = None  # node tree of the material being built


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


def m_grass():
    v = coord()
    n = node('ShaderNodeTexNoise', Scale=70.0, Detail=12.0, Roughness=0.7); link(v, n.inputs['Vector'])
    g = ramp(n.outputs['Fac'], (0.3, (0.08, 0.22, 0.01)), (0.55, (0.26, 0.46, 0.04)), (0.75, (0.50, 0.62, 0.10)))
    d = node('ShaderNodeTexNoise', Scale=5.0, Detail=4.0); link(v, d.inputs['Vector'])
    dirt = ramp(d.outputs['Fac'], (0.55, (0, 0, 0)), (0.68, (1, 1, 1)))
    return mix(g, (0.36, 0.30, 0.18), dirt), bump(n.outputs['Fac'], 0.8, 0.01), 1.0


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
    info = N.nodes.new('ShaderNodeObjectInfo')
    sep = N.nodes.new('ShaderNodeSeparateXYZ'); link(coord(), sep.inputs['Vector'])
    tip = ramp(sep.outputs['Z'], (0.0, (0.06, 0.14, 0.01)), (1.0, (0.42, 0.55, 0.10)))
    rnd = ramp(info.outputs['Random'], (0.0, (0.45, 0.45, 0.35)), (0.6, (0.9, 0.9, 0.7)), (1.0, (1.25, 1.1, 0.7)))
    return mix(tip, rnd, 1.0, 'MULTIPLY'), None, 0.8


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


M = {k: material(k, f) for k, f in dict(
    wood=m_wood, plinth=m_plinth,
    tile=m_tile, blade=m_blade,
    roof=m_roof, plaster=m_plaster, grass=m_grass, stone=m_stone, flags=m_flags,
    dark=lambda: ((0.025, 0.02, 0.015), None, 0.9)).items()}


# ---------- geometry helpers ----------
def box(name, loc, size, m, bevel=0.0, rot=0.0):
    bpy.ops.mesh.primitive_cube_add(location=loc, rotation=(0, 0, rot))
    o = bpy.context.object; o.name = name; o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        mod = o.modifiers.new('bv', 'BEVEL'); mod.width = bevel; mod.segments = 2
    o.data.materials.append(m); return o


CLOUDS = bpy.data.textures.new('clouds', 'CLOUDS'); CLOUDS.noise_scale = 0.35
CRACKLE = bpy.data.textures.new('crackle', 'VORONOI'); CRACKLE.noise_scale = 0.25; CRACKLE.distance_metric = 'DISTANCE'


def rock(loc, s, flat=0.65):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=loc)
    o = bpy.context.object
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


BEFORE_GROUND = set(bpy.data.objects.keys())
# ---------- ground ----------
box('ground', (0, 0, -0.001), (1, 1, 0.002), M['grass'])   # thin: no visible side strip
# flagstone yard from the door to the front-left edge
box('yard', (-0.12, -0.36, 0.003), (0.62, 0.26, 0.006), M['flags'])
box('yard2', (-0.36, -0.12, 0.003), (0.22, 0.30, 0.006), M['flags'])

GROUND = set(bpy.data.objects.keys()) - BEFORE_GROUND
# ---------- house ----------
A, HH, OV, RH = 0.23, 0.36, 0.09, 0.16        # half side, wall height, eave overhang, roof rise
box('walls', (0, 0, HH / 2), (2 * A, 2 * A, HH), M['plaster'], bevel=0.006)
box('plinth', (0, 0, 0.02), (2 * A + 0.03, 2 * A + 0.03, 0.04), M['plinth'], bevel=0.006)
for k in range(int((HH - 0.03) / 0.053)):      # quoins at the left (-x,-y) corner, all below the eave
    s = 0.05 if k % 2 else 0.035
    box('quoin', (-A + s / 2 - 0.004, -A - 0.004, 0.03 + k * 0.053), (s, 0.03, 0.05), M['stone'], bevel=0.004)
box('door', (-0.05, -A - 0.002, 0.11), (0.10, 0.01, 0.20), M['dark'])
box('leaf', (-0.085, -A - 0.03, 0.105), (0.008, 0.06, 0.19), M['wood'], bevel=0.002, rot=0.35)
for dx in (-0.105, 0.005):
    box('jamb', (dx, -A - 0.006, 0.11), (0.014, 0.014, 0.21), M['plinth'], bevel=0.003)
box('lintel', (-0.05, -A - 0.008, 0.215), (0.14, 0.02, 0.025), M['stone'], bevel=0.004)
box('step', (-0.05, -A - 0.03, 0.012), (0.14, 0.05, 0.024), M['stone'], bevel=0.004)
for y in (-0.13, 0.05):                        # small windows low on the +x face, toward the front
    box('win', (A + 0.003, y, 0.14), (0.01, 0.05, 0.06), M['dark'])
    box('shutter', (A + 0.012, y - 0.04, 0.14), (0.006, 0.026, 0.062), M['wood'], bevel=0.002)
    box('sill', (A + 0.01, y, 0.105), (0.02, 0.07, 0.012), M['stone'])

# hipped roof with overhang
bm = bmesh.new()
x0, x1, z0 = -A - OV, A + OV, HH - 0.01
v = [bm.verts.new(p) for p in [(x0, x0, z0), (x1, x0, z0), (x1, x1, z0), (x0, x1, z0), (0, 0, z0 + RH)]]
for f in [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)]:
    bm.faces.new([v[i] for i in f])
me = bpy.data.meshes.new('roof'); bm.to_mesh(me)
roof = bpy.data.objects.new('roof', me); sc.collection.objects.link(roof)
roof.data.materials.append(M['dark'])
roof.modifiers.new('sol', 'SOLIDIFY').thickness = 0.02


def tile_mesh(name, convex, width, length):
    """Curved roof tile along +y: convex = imbrex (cover tile), else tegula (channel tile)."""
    bm = bmesh.new(); seg = 6; ring = []
    for i in range(seg + 1):
        a = math.pi * i / seg
        x, z = -math.cos(a) * width / 2, math.sin(a) * width * (0.28 if convex else -0.08)
        ring.append((x, z))
    for y in (-length / 2, length / 2):
        for x, z in ring:
            bm.verts.new((x, y, z))
    bm.verts.ensure_lookup_table(); n = seg + 1
    for i in range(seg):
        bm.faces.new([bm.verts[i], bm.verts[i + 1], bm.verts[n + i + 1], bm.verts[n + i]])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); me.materials.append(M['tile'])
    for f in me.polygons: f.use_smooth = True
    return me


CS, CW = 0.026, 0.026                          # course spacing along the slope, column spacing
IMBREX, TEGULA = tile_mesh('imbrex', True, 0.016, CS * 1.25), tile_mesh('tegula', False, 0.026, CS * 1.2)
H0 = A + OV
L = math.hypot(H0, RH)
U = Vector((0, H0, RH)) / L                    # up the -y slope
NRM = Vector((1, 0, 0)).cross(U)               # outward normal of the -y slope
BASIS = Matrix((Vector((1, 0, 0)), U, NRM)).transposed().to_4x4()


def place(me, local, rot_z, jitter=0.0):
    o = bpy.data.objects.new('t', me); sc.collection.objects.link(o)
    m = Matrix.Rotation(rot_z, 4, 'Z') @ Matrix.Translation(local) @ BASIS
    if jitter:
        m = m @ Matrix.Rotation(random.uniform(-jitter, jitter), 4, 'Y') @ Matrix.Rotation(random.uniform(-jitter, jitter), 4, 'X')
    o.matrix_world = m
    return o


for side in range(4):
    rz = side * math.pi / 2
    for r in range(int(L / CS)):
        t = (r + 0.5) * CS / L
        half = H0 * (1 - t) - 0.006
        base = Vector((0, -H0, z0)) + U * (L * t) + NRM * 0.012
        k_max = int(half / (CW / 2))
        for k in range(-k_max, k_max + 1):
            p = base + Vector((k * CW / 2, 0, 0))
            if k % 2:
                place(IMBREX, p + NRM * 0.004, rz, 0.04)
            else:
                place(TEGULA, p, rz, 0.03)
    # hip caps from the eave corner to the apex
    corner, apex = Vector((H0, -H0, z0 + 0.02)), Vector((0, 0, z0 + RH + 0.02))
    d = (apex - corner); n = int(d.length / (CS * 0.9))
    hip_basis = d.normalized().to_track_quat('Y', 'Z').to_matrix().to_4x4()
    for i in range(n + 1):
        o = bpy.data.objects.new('hip', IMBREX); sc.collection.objects.link(o)
        o.matrix_world = Matrix.Rotation(rz, 4, 'Z') @ Matrix.Translation(corner + d * (i / max(n, 1))) @ hip_basis \
            @ Matrix.Scale(1.3, 4)

BEFORE_YARD = set(bpy.data.objects.keys())
# ---------- yard: posts, rubble walls, loose stones ----------
for p in [(-0.46, -0.36), (0.36, 0.46)]:       # cream posts near the left and right corners
    box('post', (p[0], p[1], 0.06), (0.055, 0.055, 0.12), M['stone'], bevel=0.008, rot=random.uniform(-.2, .2))
    block((p[0], p[1], 0.13), 0.045)


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


E = 0.43
rubble((-E, -E), (E, -E), 26, gaps=[(0.3, 0.62)])   # front-left edge, gap at the yard
rubble((E, -E), (E, E), 24)                         # front-right edge
rubble((-E, E), (E, E), 14, h=0.7)                  # back edges (mostly hidden)
rubble((-E, -E), (-E, E), 14, h=0.7)
for _ in range(14):                                 # loose stones in front
    rock((random.uniform(-0.41, 0.41), random.uniform(-0.41, -0.25), 0.01), random.uniform(0.012, 0.025))
for _ in range(8):
    rock((random.uniform(0.25, 0.41), random.uniform(-0.41, 0.2), 0.01), random.uniform(0.012, 0.025))

GROUND |= set(bpy.data.objects.keys()) - BEFORE_YARD

# grass: small tufts of blades scattered on the open ground (not on the yard or under the house)
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


TUFTS = [tuft_mesh() for _ in range(4)]


def open_ground(x, y):
    in_yard = (-0.43 < x < 0.19 and -0.49 < y < -0.23) or (-0.47 < x < -0.25 and -0.27 < y < 0.03)
    in_house = abs(x) < A + 0.03 and abs(y) < A + 0.03
    return not (in_yard or in_house)


n = 0
while n < 2600:
    x, y = random.uniform(-0.49, 0.49), random.uniform(-0.49, 0.49)
    if not open_ground(x, y):
        continue
    o = bpy.data.objects.new('grass', random.choice(TUFTS)); sc.collection.objects.link(o)
    sz = random.uniform(0.010, 0.022)
    o.location = (x, y, 0); o.scale = (sz, sz, sz * random.uniform(0.8, 1.4)); o.rotation_euler.z = random.uniform(0, 6.3)
    GROUND.add(o.name); n += 1

if TOP:  # building only: ground objects cut out, image cropped to the top part (above the footprint middle)
    for name in GROUND:
        bpy.data.objects[name].is_holdout = True

# ---------- light, camera, render ----------
import os
LIGHT = dict(el=35, az=-50, sun=3.4, fill=1.0, amb=0.045)  # sun elevation/azimuth (deg), fill sun from the right, sky
LIGHT.update({k: float(v) for k, v in (kv.split('=') for kv in os.environ.get('CASA_LIGHT', '').split(',') if kv)})
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = LIGHT['sun']; sun.color = (1.0, 0.90, 0.74); sun.angle = math.radians(3)
so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
so.rotation_euler = (math.radians(90 - LIGHT['el']), 0, math.radians(LIGHT['az']))   # from the front-left: lights the -y (door) wall
fill = bpy.data.lights.new('fill', 'SUN'); fill.energy = LIGHT['fill']; fill.color = (0.85, 0.9, 1.0); fill.use_shadow = False
fo = bpy.data.objects.new('fill', fill); sc.collection.objects.link(fo)
fo.rotation_euler = (math.radians(80), 0, math.radians(60))     # low, from the front-right: lifts the shaded (+x) wall, not the roof
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.52, 0.45, 1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = LIGHT['amb']

cam = bpy.data.cameras.new('cam'); cam.type = 'ORTHO'
co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co); sc.camera = co
co.rotation_euler = (math.radians(60), 0, math.radians(45))
co.location = Vector((7.07, -7.07, 5.77))
W, H = 58, 36
cam.ortho_scale = math.sqrt(2) * 60 / 58            # tile diagonal = 58 px (+2 px game gap)
px = cam.ortho_scale / W
cam.shift_y = (H / 2 - 15) * px / cam.ortho_scale   # tile centre 15 px above the bottom edge
sc.render.resolution_x, sc.render.resolution_y = W * SCALE, H * SCALE
sc.render.film_transparent = True
sc.render.engine = 'CYCLES'; sc.cycles.samples = 128; sc.cycles.device = 'GPU'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'METAL'; prefs.get_devices()
for d in prefs.devices: d.use = True
sc.view_settings.view_transform = 'Standard'
if TOP:
    sc.render.use_border = sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_max_x = 0.0, 1.0
    sc.render.border_min_y, sc.render.border_max_y = 15 / H, 1.0   # keep rows 0 .. H - 15 (top part height)
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
