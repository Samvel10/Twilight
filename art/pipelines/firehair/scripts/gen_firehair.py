# blender -b -P gen_firehair.py -- <workdir> <out.glb> [preview.png]
# Procedural "hair of fire / beard of flame" for the Spartan hero head (CC-BY base mesh, our own geometry):
#  tapered, curling flame-tongue ribbons (2 crossed cards per lock) rooted on the scalp, sideburns and jaw.
#  UV0 = (across + 2a, root->tip + 2b) with a,b in 0..7 = per-lock random id (decoded in the material: id=(a*8+b)/64 -> phase/heat).
#  (one UV channel only: UE's lightmap-UV generation writes channel 1)  Coordinates = hero component space
#  in glTF/Blender convention (m, Z up, face to -Y) so the static mesh lines up with the skeletal mesh after import;
#  in UE it is attached to the 'head' bone with the inverse ref-pose head transform (see README).
import bpy, bmesh, sys, os, math, numpy as np
from mathutils import Vector
a = sys.argv[sys.argv.index('--')+1:]; W, OUT = a[0], a[1]; PREV = a[2] if len(a) > 2 else None
rng = np.random.default_rng(int(os.environ.get('FH_SEED', '11')))
P = np.load(W+'/headpolys.npz'); uv, co, no = P['uv'], P['co'], P['no']
cen = co.mean(1); nrm = no.mean(1); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
cuv = uv.mean(1)*[1024, -1024]+[0, 1024]
strip = (cuv[:, 0] > 600) & (cuv[:, 0] < 800) & (cuv[:, 1] > 120) & (cuv[:, 1] < 240)
eyes = cuv[:, 1] > 700
x, y, z = cen.T
def hairline(y): return np.interp(y, [-0.15, -0.07, 0.0, 0.06, 0.15], [2.045, 2.04, 2.0, 1.93, 1.875])
scalp = (z > hairline(y)+0.004) & ~strip & ~eyes & ~((np.abs(x) > 0.08) & (z < 2.0) & (y > -0.04) & (y < 0.07))
# facial hair: beard (jaw/chin, below the mouth corners), sideburns (|x| > .075, above jaw), no moustache/brows (keep the face readable)
beard = strip & (z < 1.885) & ~((np.abs(x) < 0.03) & (y < -0.105) & (z > 1.86))
side = strip & (np.abs(x) > 0.078) & (z >= 1.885) & (z < 1.965) & (y > -0.07)
def poisson(idx, r, maxn):
    idx = rng.permutation(idx); pts = []
    for i in idx:
        if all(np.linalg.norm(cen[i]-cen[j]) > r for j in pts): pts.append(i)
        if len(pts) >= maxn: break
    return pts
SC = float(os.environ.get('FH_SCALE', '1'))
locks = []   # (root, normal, kind)
for i in poisson(np.where(scalp)[0], 0.03, 90): locks.append((cen[i], nrm[i], 'cap'))
for i in poisson(np.where(scalp)[0], 0.027, 90): locks.append((cen[i], nrm[i], 'hair'))
for i in poisson(np.where(beard)[0], 0.019, 70): locks.append((cen[i], nrm[i], 'beard'))
for i in poisson(np.where(side)[0], 0.018, 20): locks.append((cen[i], nrm[i], 'side'))
UP = np.array([0, 0, 1.]); BACK = np.array([0, 1., 0])
def nz(v): return v/np.linalg.norm(v)
verts, faces, uv0, uv1 = [], [], [], []
SEG = 16
def ribbon(spine, side_dirs, widths, lid):
    base = len(verts); A, Bb = lid//8, lid % 8
    for k, (p, sd, w) in enumerate(zip(spine, side_dirs, widths)):
        v = k/(len(spine)-1)
        for s in (0, 1):
            verts.append(p + sd*w*(s-0.5)); uv0.append((s + 2*A, 1 - (v + 2*Bb)))   # Blender V is flipped on glTF export; UE keeps glTF V
    for k in range(len(spine)-1):
        i = base+2*k; faces.append((i, i+1, i+3, i+2))
counts = {'hair': 0, 'beard': 0, 'side': 0, 'cap': 0}
for root, n, kind in locks:
    counts[kind] += 1
    lid = int(rng.integers(64)); ph = lid/64.
    if kind == 'cap':     # broad short tongues: the continuous burning mass on the scalp
        front = np.clip(-root[1]/0.13, 0, 1)
        L = rng.uniform(0.055, 0.1)*SC*(1-0.3*front); W0 = rng.uniform(0.055, 0.08)
        target = nz(UP + BACK*0.5); d0 = nz(n*0.8 + target*0.7)
    elif kind == 'hair':
        top = np.clip((root[2]-1.97)/0.12, 0, 1); front = np.clip(-root[1]/0.13, 0, 1)
        L = (0.08 + 0.14*top**1.5 + rng.uniform(-0.02, 0.05)) * SC
        if rng.random() < 0.1 and top > 0.5: L *= 1.4           # a few tall tongues
        L *= 1 - 0.3*front*(1-top)                                # short at the hairline
        W0 = rng.uniform(0.035, 0.055)
        target = nz(UP + BACK*0.45)                               # licking up and back (mane / flight wind)
        d0 = nz(n*1.0 + target*0.5)
    elif kind == 'side':
        L = rng.uniform(0.06, 0.1)*SC; W0 = rng.uniform(0.03, 0.045)
        target = nz(UP + BACK*0.6 + np.array([np.sign(root[0])*0.25, 0, 0])); d0 = nz(n + target*0.6)
    else:   # beard: tongues hang down/forward along the jaw (reads as a beard), tips flick forward/up
        chin = math.exp(-(root[0]/0.045)**2)
        L = (0.05 + 0.08*chin + rng.uniform(-0.01, 0.025))*SC; W0 = rng.uniform(0.03, 0.045)
        target = nz(np.array([root[0]*1.5, -0.55, -1.0])); d0 = nz(n*1.0 + target*0.4)
    side0 = np.cross(d0, n if kind != 'hair' else UP); side0 = nz(side0 if np.linalg.norm(side0) > 1e-3 else np.array([1., 0, 0]))
    amp = rng.uniform(0.2, 0.4)*W0*2.0; freq = rng.uniform(0.8, 1.6); tw = rng.uniform(-1.2, 1.2)
    spine = [root - n*0.004]; d = d0.copy(); dirs = []
    for k in range(SEG):
        s = (k+0.5)/SEG
        tgt = target
        if kind == 'beard' and s > 0.65: tgt = nz(target*0.3 + UP*0.5 + np.array([0, -0.8, 0]))   # tip curls forward/up
        d = nz(d*(1-0.32) + tgt*0.32)
        lat = np.cross(d, side0); lat = nz(lat) if np.linalg.norm(lat) > 1e-4 else side0
        wig = side0*amp*math.cos(2*math.pi*(freq*s+ph))*2*math.pi*freq/SEG
        spine.append(spine[-1] + d*L/SEG + wig*(0.3+s))
    spine = np.array(spine)
    t = np.linspace(0, 1, SEG+1)
    widths = W0*(1-t)**1.25*(0.8+1.6*t*(1-t)) + 0.0015
    # two crossed cards whose width axis twists along the lock
    for card in range(2):
        sds = []
        for k in range(SEG+1):
            tan = nz(spine[min(k+1, SEG)] - spine[max(k-1, 0)])
            ang = card*math.pi/2 + tw*t[k]
            b1 = nz(np.cross(tan, side0)) if np.linalg.norm(np.cross(tan, side0)) > 1e-4 else n
            b0 = nz(np.cross(b1, tan))
            sds.append(b0*math.cos(ang) + b1*math.sin(ang))
        ribbon(spine, sds, widths*(1.0 if card == 0 else 0.85), lid)
print('LOCKS', counts, 'verts', len(verts), 'tris', 2*len(faces))
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('SM_VahagnFireHair'); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
for name, data in (('UVMap', uv0),):
    l = me.uv_layers.new(name=name)
    for poly in me.polygons:
        for li in poly.loop_indices: l.data[li].uv = data[me.loops[li].vertex_index]
ob = bpy.data.objects.new('SM_VahagnFireHair', me); bpy.context.scene.collection.objects.link(ob)
mat = bpy.data.materials.new('FireStrand'); me.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
bpy.ops.export_scene.gltf(filepath=OUT, use_selection=True, export_format='GLB', export_normals=True, export_materials='PLACEHOLDER', export_yup=True)
print('EXPORTED', OUT)
if PREV:   # quick silhouette preview with the head (EEVEE, emission)
    bpy.ops.import_scene.gltf(filepath='/var/www/html/Twilight/art/models/hero/spartan_vahagn.glb')
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name != 'SM_VahagnFireHair':
            for i, m in enumerate(o.data.materials):
                if m and m.name.startswith('Helmet'): 
                    for p in o.data.polygons:
                        if p.material_index == i: p.select = True
            bm = bmesh.new(); bm.from_mesh(o.data)
            hel = [i for i, m in enumerate(o.data.materials) if m and m.name.startswith('Helmet')]
            bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index in hel], context='FACES'); bm.to_mesh(o.data); bm.free()
    mat.use_nodes = True; nt = mat.node_tree; nt.nodes.clear()
    o_ = nt.nodes.new('ShaderNodeOutputMaterial'); mix = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); em = nt.nodes.new('ShaderNodeEmission')
    uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'; sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uvn.outputs[0], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB'); mth = nt.nodes.new('ShaderNodeMath'); mth.operation = 'SUBTRACT'; mth.inputs[0].default_value = 1
    nt.links.new(sep.outputs[1], mth.inputs[1]); nt.links.new(mth.outputs[0], ramp.inputs[0])
    ramp.color_ramp.elements[0].color = (0.6, 0.05, 0, 1); ramp.color_ramp.elements[1].color = (1, 0.8, 0.3, 1)
    nt.links.new(ramp.outputs[0], em.inputs[0]); em.inputs[1].default_value = 6
    nt.links.new(mth.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], o_.inputs[0])
    mat.blend_method = 'BLEND'
    sc = bpy.context.scene; sc.render.engine = 'BLENDER_EEVEE_NEXT'; sc.render.resolution_x = 1200; sc.render.resolution_y = 600
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (0.25, 0.2, 0.2, 1)
    L_ = bpy.data.objects.new('L', bpy.data.lights.new('L', 'SUN')); sc.collection.objects.link(L_); L_.rotation_euler = (1.2, 0, -0.8); L_.data.color = (1, .6, .35); L_.data.energy = 3
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam; cam.data.lens = 50
    hp = Vector((0, 0, 2.0)); import tempfile
    outs = []
    for nm, off in (('front', Vector((0, -1.1, 0.0))), ('side', Vector((1.1, 0, 0.0))), ('q', Vector((0.7, -0.8, 0.25)))):
        cam.location = hp+off; cam.rotation_euler = (hp-cam.location).to_track_quat('-Z', 'Y').to_euler()
        f = PREV[:-4]+'_'+nm+'.png'; sc.render.resolution_x = 600; sc.render.filepath = f; bpy.ops.render.render(write_still=True); outs.append(f)
    print('PREVIEW', outs)
