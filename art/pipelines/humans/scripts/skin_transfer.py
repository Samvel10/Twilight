"""Skin a STATIC character (glTF) onto the UE5 mannequin skeleton by weight transfer from a skinned donor (Quinn exported
from UE with the GLTFExporter).  numpy/scipy only (no Blender).
 1. target: flatten meshes (world space), drop parts, uniform scale, optional per-part decimation (fast_simplification)
 2. donor: bind pose from IBMs, uniform scale to the target height, both arms rotated about the forward axis (--arm deg,
    + = lower) so the donor matches the target's stance; donor mesh LBS-deformed into that pose
 3. weights: inverse-distance blend of the k nearest donor vertices; vertices far from the donor body below the hips
    (dress, train) blend towards a pelvis/thigh mix so cloth does not tear between the legs
 4. writes a glb: target geometry + materials/textures, donor joint hierarchy with the posed bind (UE5 mannequin names)
usage: python3 -P skin_transfer.py donor.glb target.glb out.glb --scale 0.75 --drop eyelash,Kiem --arm 22 --decim lambert2:0.85,Hair:0.5"""
import sys, os, argparse, json, struct, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pylib'))
import numpy as np
from scipy.spatial import cKDTree
from gltf_io import rd, acc, parents, world, quat, flatten_static
ap = argparse.ArgumentParser(); ap.add_argument('donor'); ap.add_argument('target'); ap.add_argument('out')
ap.add_argument('--scale', type=float, default=1.0); ap.add_argument('--drop', default=''); ap.add_argument('--arm', type=float, default=0.0)
ap.add_argument('--decim', default=''); ap.add_argument('--k', type=int, default=8); ap.add_argument('--skirt_y', type=float, default=0.95)
ap.add_argument('--skirt_d0', type=float, default=0.04); ap.add_argument('--skirt_d1', type=float, default=0.20); ap.add_argument('--yaw', type=float, default=0.0)
a = ap.parse_args()
dj, dB = rd(a.donor); tj, tB = rd(a.target)
# ---------------- target geometry
prims = flatten_static(tj, tB, [d for d in a.drop.split(',') if d])
cy, sy = math.cos(math.radians(a.yaw)), math.sin(math.radians(a.yaw)); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
for q in prims: q['X'] = (q['X'] @ Ry.T) * a.scale; q['N'] = q['N'] @ Ry.T
dec = dict(x.split(':') for x in a.decim.split(',') if x)
if dec:
    import fast_simplification as fs
    for q in prims:
        r = [float(v) for k, v in dec.items() if k in q['name']]
        if not r: continue
        F = q['I'].reshape(-1, 3).astype(np.int64)
        p2, f2, col = fs.simplify(q['X'].astype(np.float32), F, target_reduction=r[0], return_collapses=True)
        p3, f3, imap = fs.replay_simplification(q['X'].astype(np.float32), F, col)
        rep = np.zeros(len(p3), np.int64); rep[imap[::-1]] = np.arange(len(imap))[::-1]   # one original vertex per new vertex
        print('decimate %s %d -> %d verts' % (q['name'], len(q['X']), len(p3)))
        q['X'] = p3.astype(np.float64); q['N'] = q['N'][rep]; q['UV'] = q['UV'][rep]; q['I'] = f3.reshape(-1).astype(np.uint32)
T = np.concatenate([q['X'] for q in prims]); lo = T.min(0); print('target extent', np.round(lo, 3), np.round(T.max(0), 3))
H = T.max(0)[1] - lo[1]
# ---------------- donor bind pose + posing
sk = dj['skins'][0]; joints = sk['joints']; names = [dj['nodes'][k]['name'] for k in joints]; par = parents(dj)
A_ = dj['accessors'][sk['inverseBindMatrices']]; ibm = acc(dj, dB, sk['inverseBindMatrices']).reshape(-1, 4, 4).astype(np.float64).transpose(0, 2, 1)
G = np.stack([np.linalg.inv(m) for m in ibm])
DX, DJ, DW = [], [], []
for p in dj['meshes'][0]['primitives']:
    at = p['attributes']; DX.append(acc(dj, dB, at['POSITION']).astype(np.float64)); DJ.append(acc(dj, dB, at['JOINTS_0']).astype(np.int64)); DW.append(acc(dj, dB, at['WEIGHTS_0']).astype(np.float64))
DX, DJ, DW = np.concatenate(DX), np.concatenate(DJ), np.concatenate(DW); DW /= DW.sum(1, keepdims=True)
s = H / (DX.max(0)[1] - DX.min(0)[1]); print('donor scale %.4f' % s)
S = np.eye(4); S[:3, :3] *= s
Gs = np.stack([S @ g for g in G]); Gs[:, :3, :3] /= s          # scaled positions, rigid rotations
jidx = {n: i for i, n in enumerate(names)}
jpar = {}
for i, k in enumerate(joints):
    p = par.get(k)
    while p is not None and p not in joints: p = par.get(p)
    jpar[i] = joints.index(p) if p is not None else -1
def subtree(i):
    out = [i]
    for c in range(len(joints)):
        if jpar[c] == i: out += subtree(c)
    return out
Gp = Gs.copy()
for side, sgn in (('l', -1), ('r', 1)):
    ua = jidx['upperarm_' + side]; piv = Gp[ua][:3, 3].copy(); th = math.radians(a.arm * sgn)
    Rz = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1]])
    M = np.eye(4); M[:3, :3] = Rz; M[:3, 3] = piv - Rz @ piv
    for c in subtree(ua): Gp[c] = M @ Gp[c]
# LBS donor mesh into the posed skeleton (donor verts were bound at G; scale first)
Xs = DX * s; skinM = np.stack([Gp[i] @ np.linalg.inv(Gs[i]) for i in range(len(joints))])
Xh = np.c_[Xs, np.ones(len(Xs))]; Xp = np.zeros_like(Xs)
for c in range(4):
    Xp += DW[:, c:c+1] * np.einsum('nij,nj->ni', skinM[DJ[:, c]], Xh)[:, :3]
# align the donor feet/centre to the target (x,z centre of the lower body, feet on the same floor)
off = np.array([0.0, lo[1] - Xp.min(0)[1], 0.0]); Xp += off; Gp[:, :3, 3] += off
print('posed donor extent', np.round(Xp.min(0), 3), np.round(Xp.max(0), 3), 'hand_l', np.round(Gp[jidx['hand_l']][:3, 3], 3))
# ---------------- weight transfer
tree = cKDTree(Xp); dist, nn = tree.query(T, k=a.k)
wv = 1.0 / np.maximum(dist, 1e-4) ** 2; wv /= wv.sum(1, keepdims=True)
NJ = len(joints); Wt = np.zeros((len(T), NJ))
for c in range(4):
    np.add.at(Wt, (np.repeat(np.arange(len(T)), a.k), DJ[nn.reshape(-1), c]), (wv * DW[nn, c]).reshape(-1))
skirt = np.zeros(NJ); skirt[jidx['pelvis']] = 0.7; skirt[jidx['thigh_l']] = 0.15; skirt[jidx['thigh_r']] = 0.15
t = np.clip((dist[:, 0] - a.skirt_d0) / (a.skirt_d1 - a.skirt_d0), 0, 1) * (T[:, 1] < a.skirt_y)
Wt = Wt * (1 - t[:, None]) + skirt[None, :] * t[:, None]
top = np.argsort(-Wt, axis=1)[:, :4]; tw = np.take_along_axis(Wt, top, 1); tw /= np.maximum(tw.sum(1, keepdims=True), 1e-9)
print('skirt-blended verts %d / %d, mean nn dist %.3f' % ((t > 0).sum(), len(T), dist[:, 0].mean()))
# ---------------- write
out = {'asset': {'version': '2.0', 'generator': 'skin_transfer.py'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [], 'meshes': [], 'skins': [],
       'accessors': [], 'bufferViews': [], 'buffers': [], 'materials': [], 'textures': [], 'images': [], 'samplers': []}
BIN = bytearray()
def view(data, target=None):
    while len(BIN) % 4: BIN.append(0)
    o = len(BIN); BIN.extend(data); v = {'buffer': 0, 'byteOffset': o, 'byteLength': len(data)}
    if target: v['target'] = target
    out['bufferViews'].append(v); return len(out['bufferViews']) - 1
def accw(arr, ct, typ, target=None, mm=False):
    arr = np.ascontiguousarray(arr); A = {'bufferView': view(arr.tobytes(), target), 'componentType': ct, 'count': int(arr.shape[0]), 'type': typ}
    if mm: A['min'] = [float(x) for x in arr.min(0)]; A['max'] = [float(x) for x in arr.max(0)]
    out['accessors'].append(A); return len(out['accessors']) - 1
# nodes: 0 = Armature, then joints in donor order with local TRS of the posed bind
out['nodes'].append({'name': 'Armature', 'children': []})
for i, k in enumerate(joints):
    L = Gp[i] if jpar[i] < 0 else np.linalg.inv(Gp[jpar[i]]) @ Gp[i]
    nd = {'name': names[i], 'rotation': quat(L[:3, :3])}
    if np.abs(L[:3, 3]).max() > 1e-9: nd['translation'] = [float(x) for x in L[:3, 3]]
    out['nodes'].append(nd)
for i in range(len(joints)):
    p = jpar[i]
    if p < 0: out['nodes'][0]['children'].append(i + 1)
    else: out['nodes'][p + 1].setdefault('children', []).append(i + 1)
ibm_new = np.stack([np.linalg.inv(g).T for g in Gp]).astype('<f4')
out['skins'].append({'joints': list(range(1, len(joints) + 1)), 'inverseBindMatrices': accw(ibm_new.reshape(-1, 16), 5126, 'MAT4'), 'skeleton': 1})
# materials / textures / images copied from target
for im in tj.get('images', []):
    v = tj['bufferViews'][im['bufferView']]; o = v.get('byteOffset', 0)
    out['images'].append({'bufferView': view(bytes(tB[o:o + v['byteLength']])), 'mimeType': im.get('mimeType', 'image/png')})
out['samplers'] = tj.get('samplers', []); out['textures'] = tj.get('textures', []); out['materials'] = tj.get('materials', [])
# primitives merged by material
byM = {}; base = 0
for q in prims:
    n = len(q['X']); byM.setdefault(q['mat'], []).append((q, base)); base += n
mesh = {'name': 'SK_shamiram', 'primitives': []}
for m, lst in byM.items():
    X = np.concatenate([q['X'] for q, b in lst]).astype(np.float32); Nn = np.concatenate([q['N'] for q, b in lst])
    Nn = (Nn / np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-9)).astype(np.float32)
    UV = np.concatenate([q['UV'] for q, b in lst]).astype(np.float32)
    idx = np.concatenate([np.arange(b, b + len(q['X'])) for q, b in lst])
    I = []; off_ = 0
    for q, b in lst: I.append(q['I'] + off_); off_ += len(q['X'])
    mesh['primitives'].append({'attributes': {'POSITION': accw(X, 5126, 'VEC3', 34962, True), 'NORMAL': accw(Nn, 5126, 'VEC3', 34962),
        'TEXCOORD_0': accw(UV, 5126, 'VEC2', 34962), 'JOINTS_0': accw(top[idx].astype(np.uint16), 5123, 'VEC4', 34962),
        'WEIGHTS_0': accw(tw[idx].astype(np.float32), 5126, 'VEC4', 34962)}, 'indices': accw(np.concatenate(I).astype(np.uint32).reshape(-1, 1), 5125, 'SCALAR', 34963), 'material': m})
out['meshes'].append(mesh); out['nodes'].append({'name': 'SK_shamiram', 'mesh': 0, 'skin': 0}); out['scenes'][0]['nodes'].append(len(out['nodes']) - 1)
while len(BIN) % 4: BIN.append(0)
out['buffers'] = [{'byteLength': len(BIN)}]
for k in ('samplers', 'textures', 'images'):
    if not out[k]: out.pop(k)
js = json.dumps(out, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
open(a.out, 'wb').write(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(BIN)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(BIN)) + b'BIN\0' + bytes(BIN))
print('wrote', a.out, 'verts', len(T), 'tris', sum(len(q['I']) for q in prims) // 3, 'prims', len(mesh['primitives']))
