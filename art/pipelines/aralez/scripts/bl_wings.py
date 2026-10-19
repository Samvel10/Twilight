"""Build SK_AralezWings: feather-card wings (original work, CC0) with a 7-bone rig, baked Wing_* actions, export GLB.
blender -b -P bl_wings.py -- out.glb atlas_dir [preview_prefix]"""
import bpy, bmesh, math, random, sys
from mathutils import Vector, Matrix, Quaternion, Euler
argv = sys.argv[sys.argv.index('--') + 1:]
OUT, TEX = argv[0], argv[1]; PREV = argv[2] if len(argv) > 2 else None
exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/wingflap.py').read())
S = float(__import__('os').environ.get('WING_SCALE', '1.0'))
random.seed(11)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.fps = 30

# ---------------- armature
J = [Vector((0.07, 0, 0)), Vector((0.07 + 0.40 * S, 0.07 * S, 0.02 * S)), Vector((0.07 + 0.88 * S, -0.02 * S, 0.02 * S)), Vector((0.07 + 1.22 * S, 0.03 * S, 0.02 * S))]
ad = bpy.data.armatures.new('AralezWingsSkel'); arm = bpy.data.objects.new('AralezWings', ad); sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode='EDIT')
eb = ad.edit_bones; r = eb.new('wings_root'); r.head = (0, 0, 0); r.tail = (0, 0, 0.1)
for side, sg in (('L', 1), ('R', -1)):
    m = lambda v: Vector((v.x * sg, v.y, v.z))
    prev = r
    for i, n in enumerate(('humerus', 'forearm', 'hand')):
        b = eb.new('%s_%s' % (side, n)); b.head = m(J[i]); b.tail = m(J[i + 1]); b.parent = prev; b.use_connect = i > 0
        b.roll = 0; prev = b
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------- feather cards
CELL = {'primary': 0, 'secondary': 1, 'covert': 2, 'contour': 3}
verts, faces, uvs, cols, groups = [], [], [], [], []   # groups: per-vertex [(bone, w)]
def seg_point(p):  # p in [0,3]: along J0..J3
    i = min(2, int(p)); f = p - i
    return J[i].lerp(J[i + 1], f), i
def card(side, base, ang, L, Wd, kind, z, bonew, bend=0.0, camber=0.02, under=False, nseg=6):
    sg = 1 if side == 'L' else -1
    d = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0))      # along the rachis (X out, Y back)
    lat = Vector((-d.y, d.x, 0))                                                       # across
    c0 = CELL[kind]; rnd = random.random()
    idx0 = len(verts)
    for a in range(nseg + 1):
        u = a / nseg
        for k, v in enumerate((-1, 0, 1)):
            p = base + d * (L * u) + lat * (v * Wd * 0.5)
            zz = z + bend * L * u * u - camber * Wd * (1 - v * v) * (1 if not under else -1)
            p = Vector((p.x * sg, p.y, p.z + zz))
            verts.append(p)
            uu = (c0 + 0.5 + 0.5 * v * (1 if side == 'L' else -1)) / 4.0             # mirror so the narrow vane stays leading
            uvs.append((uu, u))                                                      # base at v=0 (image bottom), tip v=1
            cols.append((u, rnd, c0 / 3.0, 1.0))
            groups.append(bonew)
    for a in range(nseg):
        for k in range(2):
            i0 = idx0 + a * 3 + k; q = (i0, i0 + 1, i0 + 4, i0 + 3)
            faces.append(q if (sg > 0) != under else q[::-1])
def bw(side, p):
    """rigid-ish weights from the chain parameter p (0..3)"""
    names = ['humerus', 'forearm', 'hand']; i = min(2, int(p)); f = p - i
    w = [(side + '_' + names[i], 1.0)]
    if f < 0.12 and i > 0: w = [(side + '_' + names[i], 0.5 + f / 0.24), (side + '_' + names[i - 1], 0.5 - f / 0.24)]
    return w
for side in ('L', 'R'):
    # primaries (hand)
    PL = [0.56, 0.60, 0.64, 0.68, 0.72, 0.75, 0.77, 0.78, 0.74, 0.64]
    for i in range(10):
        f = i / 9; p = 2.0 + 0.12 + 0.88 * f
        base, _ = seg_point(p); base = base + Vector((0, 0.02, 0))
        card(side, base, 88 - 60 * f ** 1.1 + random.uniform(-2, 2), PL[i] * S * random.uniform(0.97, 1.03), (0.25 - 0.05 * f) * S, 'primary', 0.002 * i, [(side + '_hand', 1.0)], bend=0.05)
    # secondaries (forearm)
    for j in range(13):
        f = j / 12; p = 1.0 + 0.05 + 0.95 * f
        base, _ = seg_point(p); base = base + Vector((0, 0.025, 0))
        card(side, base, 97 - 12 * f, (0.50 + 0.03 * math.sin(f * 3)) * S, 0.19 * S, 'secondary', 0.006 + 0.0012 * (12 - j), bw(side, p), bend=-0.02)
    # tertials (inner arm)
    for k in range(4):
        f = k / 3; p = 0.45 + 0.6 * f
        base, _ = seg_point(p); base = base + Vector((0, 0.03, 0))
        card(side, base, 112 - 10 * f, (0.42 + 0.06 * f) * S, 0.18 * S, 'secondary', 0.016 + 0.002 * k, bw(side, p), bend=-0.03)
    # greater coverts (upper + under)
    for j in range(26):
        f = j / 25; p = 0.5 + 2.4 * f
        base, _ = seg_point(p); base = base + Vector((0, -0.01, 0))
        ang = 100 - 30 * max(0, (p - 2.0)) + random.uniform(-4, 4); L = (0.32 if p < 2 else 0.28 - 0.08 * (p - 2)) * S * random.uniform(0.9, 1.1)
        base = base + Vector((random.uniform(-.01, .01), random.uniform(-.015, .015), 0))
        card(side, base, ang, L, 0.14 * S, 'covert', 0.026 + 0.0008 * (25 - j), bw(side, p), bend=-0.02, nseg=4)
        card(side, base, ang, L * 0.9, 0.13 * S, 'covert', -0.010, bw(side, p), bend=0.0, under=True, nseg=3)
    # median coverts
    for j in range(24):
        f = j / 23; p = 0.15 + 2.7 * f
        base, _ = seg_point(p); base = base + Vector((random.uniform(-.015, .015), -0.05 + random.uniform(-.02, .02), 0))
        card(side, base, 98 - 25 * max(0, p - 2) + random.uniform(-8, 8), 0.17 * S * random.uniform(0.8, 1.15), 0.11 * S, 'covert', 0.036 + random.uniform(0, .004), bw(side, p), nseg=3)
        card(side, base, 98 - 25 * max(0, p - 2), 0.15 * S, 0.10 * S, 'contour', -0.018, bw(side, p), under=True, nseg=2)
    # lesser / marginal coverts: two rows over the leading edge
    for row in range(2):
        for j in range(30):
            f = (j + 0.5 * row) / 30; p = 0.05 + 2.85 * f
            base, _ = seg_point(p); base = base + Vector((random.uniform(-.01, .01), -0.075 + 0.03 * row + random.uniform(-.012, .012), 0))
            card(side, base, 92 + random.uniform(-10, 10), (0.10 - 0.025 * (p / 3)) * S * random.uniform(0.8, 1.2), 0.075 * S, 'contour', 0.045 - 0.004 * row, bw(side, p), camber=0.03, nseg=2)
            card(side, base, 92 + random.uniform(-6, 6), (0.08 - 0.02 * (p / 3)) * S, 0.075 * S, 'contour', -0.022 + 0.004 * row, bw(side, p), camber=0.03, under=True, nseg=2)
    # scapulars over the root (blend the wing into the back fur)
    for k in range(6):
        f = k / 5
        base = Vector((0.02 + 0.10 * f, -0.06 + 0.02 * f, 0))
        card(side, base, 100 + 18 * (1 - f), (0.26 + 0.12 * f) * S, 0.14 * S, 'covert', 0.05 - 0.003 * k, [('wings_root', 0.6), (side + '_humerus', 0.4)] if k < 3 else [(side + '_humerus', 1.0)], camber=0.03, nseg=4)

# ---------------- leading-edge arm (tapered flattened tube) so the wing has thickness
def tube(side):
    sg = 1 if side == 'L' else -1; N = 8; idx0 = len(verts); steps = 24
    for a in range(steps + 1):
        p = 3.0 * a / steps; c, _ = seg_point(p)
        rad = (0.055 - 0.03 * p / 3) * S
        for k in range(N):
            ang = 2 * math.pi * k / N
            v = Vector((c.x, c.y + math.cos(ang) * rad * 1.4 - 0.02, c.z + math.sin(ang) * rad * 0.55 + 0.01))
            verts.append(Vector((v.x * sg, v.y, v.z))); uvs.append((0.875 + 0.02 * math.cos(ang), 0.55 + 0.02 * math.sin(ang)))
            cols.append((0.5, 0.5, 1.0, 1.0)); groups.append(bw(side, min(2.999, p)))
    for a in range(steps):
        for k in range(N):
            i0 = idx0 + a * N + k; i1 = idx0 + a * N + (k + 1) % N
            q = (i0, i1, i1 + N, i0 + N); faces.append(q if sg > 0 else q[::-1])
tube('L'); tube('R')

me = bpy.data.meshes.new('SK_AralezWings'); me.from_pydata([tuple(v) for v in verts], [], faces)
ob = bpy.data.objects.new('SK_AralezWings', me); sc.collection.objects.link(ob)
uvl = me.uv_layers.new(name='UVMap')
for poly in me.polygons:
    for li in poly.loop_indices:
        vi = me.loops[li].vertex_index; uvl.data[li].uv = uvs[vi]
ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
for i, c in enumerate(cols): ca.data[i].color = c
for bname in ['wings_root'] + ['%s_%s' % (s, n) for s in 'LR' for n in ('humerus', 'forearm', 'hand')]:
    ob.vertex_groups.new(name=bname)
for i, g in enumerate(groups):
    for bname, w in g: ob.vertex_groups[bname].add([i], w, 'REPLACE')
me.shade_smooth() if hasattr(me, 'shade_smooth') else None
ob.parent = arm; mod = ob.modifiers.new('arm', 'ARMATURE'); mod.object = arm
# material (for preview + glTF)
mat = bpy.data.materials.new('M_AralezFeather'); mat.use_nodes = True; nt = mat.node_tree
bsdf = nt.nodes['Principled BSDF']; img = bpy.data.images.load(TEX + '/T_Feather_BC.png')
tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = img
nt.links.new(tx.outputs['Color'], bsdf.inputs['Base Color']); nt.links.new(tx.outputs['Alpha'], bsdf.inputs['Alpha'])
nimg = bpy.data.images.load(TEX + '/T_Feather_N.png'); nimg.colorspace_settings.name = 'Non-Color'
tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = nimg; nm = nt.nodes.new('ShaderNodeNormalMap')
nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
bsdf.inputs['Roughness'].default_value = 0.65
mat.blend_method = 'CLIP' if hasattr(mat, 'blend_method') else None
try: mat.surface_render_method = 'DITHERED'
except Exception: pass
mat.use_backface_culling = False
ob.data.materials.append(mat)
print('WINGS verts', len(verts), 'tris', sum(len(f) - 2 for f in faces))

# ---------------- baked actions (same maths as the C++ component)
arm.animation_data_create()
def pose(ph, wts, t):
    P = wing_pose(ph, *wts, t=t)
    for side, sg in (('L', 1), ('R', -1)):
        for n in ('humerus', 'forearm', 'hand'):
            pb = arm.pose.bones['%s_%s' % (side, n)]; x, y, z = P[n]
            q = Euler((math.radians(x), math.radians(y * sg), math.radians(z * sg)), 'XYZ').to_quaternion()
            R = pb.bone.matrix_local.to_3x3()
            pb.rotation_mode = 'QUATERNION'; pb.rotation_quaternion = (R.inverted() @ q.to_matrix() @ R).to_quaternion()
def bake(name, dur, wts_fn, cycles=1.0):
    act = bpy.data.actions.new(name); arm.animation_data.action = act
    n = int(round(dur * 30))
    for f in range(n + 1):
        t = f / 30.0; ph = (t / dur * cycles) % 1.0
        pose(ph, wts_fn(t / dur), t)
        for pb in arm.pose.bones: pb.keyframe_insert('rotation_quaternion', frame=f)
    act.use_fake_user = True
    return act
bake('Wing_Flap', 1.0, lambda a: (1, 0, 0, 0))
bake('Wing_Glide', 2.857, lambda a: (0, 1, 0, 0))    # loops: breathing at 0.35 Hz
bake('Wing_Mantle', 1.0, lambda a: (0, 0, 1, 0), cycles=2.0)
bake('Wing_Fold', 2.0, lambda a: (0, 0, 0, 1))
arm.animation_data.action = None
for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()

if PREV:
    exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/bl_common.py').read(), globals())
    cam = setup_render((900, 560))
    for nm, wts, ph in (('rest', None, 0), ('flapUp', (1, 0, 0, 0), 0.25), ('flapDown', (1, 0, 0, 0), 0.75), ('glide', (0, 1, 0, 0), 0), ('mantle', (0, 0, 1, 0), 0), ('fold', (0, 0, 0, 1), 0)):
        if wts: pose(ph, wts, 0)
        else:
            for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()
        bpy.context.view_layer.update()
        shoot(cam, (0, 0.3, 0.1), 90 + 25, 50, 5.2, '%s_%s_top.png' % (PREV, nm))
        shoot(cam, (0, 0.3, 0.1), 180 + 90, 8, 5.2, '%s_%s_back.png' % (PREV, nm))
for pb in arm.pose.bones: pb.rotation_quaternion = Quaternion()
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', use_selection=True, export_animations=True, export_animation_mode='ACTIONS',
                          export_skins=True, export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_yup=True, export_apply=False)
print('EXPORTED', OUT)
