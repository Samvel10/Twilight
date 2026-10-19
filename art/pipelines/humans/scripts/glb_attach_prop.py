"""Rigidly attach a static glTF prop (helmet, crown...) to one bone of a baked character GLB (output of bake_gltf_root.py).
The prop is fitted to the bbox of the vertices skinned mostly to that bone (e.g. the head), skinned 100% to the bone and
merged as a new primitive (+ its material/textures) into the character's single mesh -> one SkeletalMesh in Unreal.
usage: python3 -I glb_attach_prop.py char.glb prop.glb out.glb --bone head --name Helmet --fitw 1.15 --top 0.03 [--dz 0 --dy 0 --yaw 0 --pitch 0 --scale 0]
  --fitw  prop width (X) = fitw * bone-geometry width;  --scale overrides with an absolute scale
  --top   prop top = geometry top + top (m);  --dy extra vertical shift;  --dz forward shift (+Z = character front)
  --yaw/--pitch degrees applied to the prop before fitting (prop front assumed +Z, up +Y)"""
import json, struct, sys, argparse, math
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument('char'); ap.add_argument('prop'); ap.add_argument('out')
for k, d in (('--bone', 'head'), ('--name', 'Prop')): ap.add_argument(k, default=d)
for k, d in (('--fitw', 1.15), ('--top', 0.03), ('--dz', 0.0), ('--dy', 0.0), ('--yaw', 0.0), ('--pitch', 0.0), ('--scale', 0.0), ('--minw', 0.5)): ap.add_argument(k, type=float, default=d)
a = ap.parse_args()

def rd(fn):
    b = open(fn, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + n])
    bl = struct.unpack('<I', b[20 + n:24 + n])[0]; return j, bytearray(b[28 + n:28 + n + bl])
C, CB = rd(a.char); Pj, PB = rd(a.prop)
CT = {5120: 'i1', 5121: 'u1', 5122: 'i2', 5123: 'u2', 5125: 'u4', 5126: 'f4'}; NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
def acc(j, B, i):
    A = j['accessors'][i]; v = j['bufferViews'][A['bufferView']]; dt = np.dtype('<' + CT[A['componentType']]); nc = NC[A['type']]
    o = v.get('byteOffset', 0) + A.get('byteOffset', 0); st = v.get('byteStride', dt.itemsize * nc)
    raw = np.frombuffer(bytes(B[o:o + st * (A['count'] - 1) + dt.itemsize * nc]), dtype=np.uint8)
    out = np.lib.stride_tricks.as_strided(raw, shape=(A['count'], dt.itemsize * nc), strides=(st, 1)).copy().view(dt).reshape(A['count'], nc)
    if A.get('normalized') and dt.kind in 'ui': out = out.astype(np.float32) / np.iinfo(dt).max
    return out
def node_m(nd):
    if 'matrix' in nd: return np.array(nd['matrix'], dtype=np.float64).reshape(4, 4).T
    M = np.eye(4)
    if 'scale' in nd: M = np.diag(list(nd['scale']) + [1.0]) @ M
    if 'rotation' in nd:
        x, y, z, w = nd['rotation']
        R = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
        T = np.eye(4); T[:3, :3] = R; M = T @ M
    if 'translation' in nd: T = np.eye(4); T[:3, 3] = nd['translation']; M = T @ M
    return M
# ---- character: bone index + bbox of the geometry skinned to that bone
skin = C['skins'][0]; names = [C['nodes'][k]['name'] for k in skin['joints']]; jb = names.index(a.bone)
pts = []
for p in C['meshes'][0]['primitives']:
    at = p['attributes']; X = acc(C, CB, at['POSITION']); J = acc(C, CB, at['JOINTS_0']); W = acc(C, CB, at['WEIGHTS_0'])
    w = (W * (J == jb)).sum(1); pts.append(X[w >= a.minw])
pts = np.concatenate(pts); lo, hi = pts.min(0), pts.max(0); ctr = (lo + hi) / 2
print('bone %s idx %d verts %d bbox lo %s hi %s' % (a.bone, jb, len(pts), np.round(lo, 3), np.round(hi, 3)))
# ---- prop: flatten all mesh nodes into world space
par = {c: i for i, nd in enumerate(Pj['nodes']) for c in nd.get('children', [])}
def glob(i):
    M = node_m(Pj['nodes'][i])
    while i in par: i = par[i]; M = node_m(Pj['nodes'][i]) @ M
    return M
prims = []
for i, nd in enumerate(Pj['nodes']):
    if 'mesh' not in nd: continue
    M = glob(i); Nm = np.linalg.inv(M[:3, :3]).T
    for p in Pj['meshes'][nd['mesh']]['primitives']:
        at = p['attributes']; X = acc(Pj, PB, at['POSITION']).astype(np.float64)
        X = X @ M[:3, :3].T + M[:3, 3]
        N = acc(Pj, PB, at['NORMAL']).astype(np.float64) @ Nm.T if 'NORMAL' in at else None
        UV = acc(Pj, PB, at['TEXCOORD_0']) if 'TEXCOORD_0' in at else np.zeros((len(X), 2), np.float32)
        I = acc(Pj, PB, p['indices']).reshape(-1) if 'indices' in p else np.arange(len(X))
        prims.append(dict(X=X, N=N, UV=UV, I=I.astype(np.uint32), mat=p.get('material', 0)))
# merge primitives that share a material (fewer sections = fewer draw calls)
byM = {}
for q in prims: byM.setdefault(q['mat'], []).append(q)
merged = []
for m, qs in byM.items():
    base = 0; I = []
    for q in qs: I.append(q['I'] + base); base += len(q['X'])
    Ns = [q['N'] if q['N'] is not None else np.tile([0., 1., 0.], (len(q['X']), 1)) for q in qs]
    merged.append(dict(X=np.concatenate([q['X'] for q in qs]), N=np.concatenate(Ns), UV=np.concatenate([q['UV'] for q in qs]), I=np.concatenate(I).astype(np.uint32), mat=m))
prims = merged
allX = np.concatenate([q['X'] for q in prims])
cy, sy = math.cos(math.radians(a.yaw)), math.sin(math.radians(a.yaw)); cp, sp = math.cos(math.radians(a.pitch)), math.sin(math.radians(a.pitch))
R = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
allX = allX @ R.T; plo, phi = allX.min(0), allX.max(0)
s = a.scale if a.scale > 0 else a.fitw * (hi[0] - lo[0]) / (phi[0] - plo[0])
off = np.array([ctr[0] - s * (plo[0] + phi[0]) / 2, hi[1] + a.top - s * phi[1] + a.dy, ctr[2] - s * (plo[2] + phi[2]) / 2 + a.dz])
print('prop bbox', np.round(plo, 3), np.round(phi, 3), 'scale %.4f offset %s' % (s, np.round(off, 4)))
# ---- append buffers
def align():
    while len(CB) % 4: CB.append(0)
def add_view(data, target=None):
    align(); o = len(CB); CB.extend(data); v = {'buffer': 0, 'byteOffset': o, 'byteLength': len(data)}
    if target: v['target'] = target
    C['bufferViews'].append(v); return len(C['bufferViews']) - 1
def add_acc(arr, ctype, typ, target=None, mm=False):
    arr = np.ascontiguousarray(arr); bv = add_view(arr.tobytes(), target)
    A = {'bufferView': bv, 'componentType': ctype, 'count': int(arr.shape[0]), 'type': typ}
    if mm: A['min'] = [float(x) for x in arr.min(0)]; A['max'] = [float(x) for x in arr.max(0)]
    C['accessors'].append(A); return len(C['accessors']) - 1
# materials / textures / images / samplers
for k in ('images', 'textures', 'samplers', 'materials'): C.setdefault(k, [])
imap = {}
for ii, im in enumerate(Pj.get('images', [])):
    if 'bufferView' in im:
        v = Pj['bufferViews'][im['bufferView']]; o = v.get('byteOffset', 0)
        bv = add_view(bytes(PB[o:o + v['byteLength']])); C['images'].append({'bufferView': bv, 'mimeType': im.get('mimeType', 'image/png'), 'name': '%s_%d' % (a.name, ii)})
        imap[ii] = len(C['images']) - 1
smap = {}
for si, sm in enumerate(Pj.get('samplers', [])): C['samplers'].append(sm); smap[si] = len(C['samplers']) - 1
tmap = {}
for ti, t in enumerate(Pj.get('textures', [])):
    nt = {}
    if 'source' in t and t['source'] in imap: nt['source'] = imap[t['source']]
    if 'sampler' in t: nt['sampler'] = smap[t['sampler']]
    C['textures'].append(nt); tmap[ti] = len(C['textures']) - 1
def remap(o):
    if isinstance(o, dict):
        return {k: (tmap[v] if k == 'index' and isinstance(v, int) else remap(v)) for k, v in o.items()}
    if isinstance(o, list): return [remap(x) for x in o]
    return o
mmap = {}
for mi, m in enumerate(Pj.get('materials', [{}])):
    nm = remap(m); nm['name'] = a.name if len(Pj.get('materials', [])) <= 1 else '%s_%d' % (a.name, mi)
    C['materials'].append(nm); mmap[mi] = len(C['materials']) - 1
for q in prims:
    X = ((q['X'] @ R.T) * s + off).astype(np.float32)
    N = q['N'] @ R.T if q['N'] is not None else np.tile([0, 1, 0], (len(X), 1))
    N = (N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)).astype(np.float32)
    J = np.zeros((len(X), 4), np.uint16); J[:, 0] = jb; W = np.zeros((len(X), 4), np.float32); W[:, 0] = 1
    prim = {'attributes': {'POSITION': add_acc(X, 5126, 'VEC3', 34962, True), 'NORMAL': add_acc(N, 5126, 'VEC3', 34962),
                           'TEXCOORD_0': add_acc(q['UV'].astype(np.float32), 5126, 'VEC2', 34962),
                           'JOINTS_0': add_acc(J, 5123, 'VEC4', 34962), 'WEIGHTS_0': add_acc(W, 5126, 'VEC4', 34962)},
            'indices': add_acc(q['I'].reshape(-1, 1), 5125, 'SCALAR', 34963), 'material': mmap.get(q['mat'], mmap[0])}
    C['meshes'][0]['primitives'].append(prim)
align(); C['buffers'] = [{'byteLength': len(CB)}]
js = json.dumps(C, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
out = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(CB)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(CB)) + b'BIN\0' + bytes(CB)
open(a.out, 'wb').write(out); print('wrote', a.out, len(out), 'prims', len(C['meshes'][0]['primitives']))
