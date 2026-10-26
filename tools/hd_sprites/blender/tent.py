"""Re-model Caesar III small tents (group 26, images 2779-2782; 58 x 30-34 px, 1 tile).

usage: Blender -b -P tent.py -- OUT.png SCALE [top] -- ID
Ridge tents of patched canvas on lashed poles, with amphorae, sacks, baskets, blankets, a fire pit and straw.
Layout follows the original sprites: x_s = 29 + 29 (x + y), y_s = (H - 15) + 15 (x - y) - 35.5 z.
"""
import math, os, random, sys
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
    2779: dict(rot=0, L=0.42, W=0.32, H=0.22, fabric=(100, 89, 69), patch=(159, 107, 68),
               pots=[(40, 12), (46, 14)], sacks=[(12, 16), (16, 20), (24, 22), (30, 23)],
               blankets=[(18, 14, 0.3)], baskets=[(36, 22)], fire=None, stools=[]),
    2780: dict(rot=-90, L=0.30, W=0.28, H=0.26, fabric=FAB2780,
               patch=None, pots=[(18, 13), (48, 13)], sacks=[(9, 15), (13, 17)],
               blankets=[(20, 19, 1.2)], baskets=[(26, 24)], fire=(40, 22), stools=[]),
    2781: dict(rot=-90, L=0.40, W=0.36, H=0.31, fabric=(121, 111, 63), front=(60, 40, 26),
               pots=[(12, 17), (38, 17), (39, 23)], post_pot=(12, 17), sacks=[(49, 18), (22, 25)],
               blankets=[(28, 26, 0.2)], baskets=[(17, 22)], fire=None, stools=[]),
    2782: dict(rot=0, L=0.42, W=0.36, H=0.37, fabric=(112, 112, 66), patch=(141, 96, 66), patch_size=(0.7, 0.6),
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


def canvas(srgb):
    """photo canvas (Fabric061, neutral grey ~0.25 linear) tinted so it renders as the original's sRGB colour"""
    lin = [((c / 255 + 0.055) / 1.055) ** 2.4 if c / 255 > 0.04045 else c / 255 / 12.92 for c in srgb]
    # x 0.7: tent slopes face the sun more than flat ground (GAIN is calibrated on flat ground)
    return c3.m_photo('Fabric061', scale=7.0, tint=tuple(0.7 * lin[i] * c3.GAIN[i] / 0.25 for i in range(3)), normal=0.8,
                      extra=canvas_layers)


M['canvas'] = c3.material('canvas', canvas(V['fabric']))
if V.get('patch'):
    M['patch'] = c3.material('patch', canvas(V['patch']))
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
    bpy.ops.mesh.primitive_circle_add(vertices=48, radius=0.38, fill_type='NGON', location=(0, 0, 0.001))
    d = bpy.context.object; d.scale = (1.0, 0.82, 1); d.rotation_euler.z = math.radians(V['rot'])
    d.data.materials.append(M['dirt'])
    c3.box('path', tuple(world((0.33, 0, 0.0012))), (0.26, 0.12, 0.002), 'dirt', rot=math.radians(V['rot']))
    for _ in range(14):
        a, r = random.uniform(0, 6.3), random.uniform(0.25, 0.40)
        c3.rock((r * math.cos(a), r * math.sin(a), 0.004), random.uniform(0.007, 0.015))
    c3.straw(0, 0, 0.36, n=90)

# ---------- tent ----------
L, W, H = V['L'], V['W'], V['H']
sheet = c3.link_obj('canvas', canvas_mesh(L, W, H), 'canvas'); sheet.matrix_world = ROT
sheet.modifiers.new('sol', 'SOLIDIFY').thickness = 0.004
if V.get('patch'):                                       # patched panel on the back slope
    ps = V.get('patch_size', (0.45, 0.5))
    p = c3.link_obj('patch', canvas_mesh(L * ps[0], W * ps[1], H * ps[1], sag=0.0, nu=10, nv=8), 'patch')
    p.matrix_world = ROT @ Matrix.Translation((-L * 0.1, W * 0.22, H * 0.4)) @ Matrix.Rotation(0.65, 4, 'X')
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
    return x * x + (y * 1.22) ** 2 > 0.38 ** 2


c3.grass(1800, open_ground)
c3.render(58, H_PX)
