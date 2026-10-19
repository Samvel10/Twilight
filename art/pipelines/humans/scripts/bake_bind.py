"""Canonicalise a skinned glTF from its INVERSE BIND MATRICES (works when the scene pose is not the bind pose, e.g.
Sketchfab exports that carry an animation, and when non-joint nodes sit between joints).
Result: Y-up metres, root joint identity, every joint's local TRS = bind pose (no scale), new IBMs, vertices unchanged
except the unit/axis normalisation A (auto: cm->m if the body is >10 units tall; Z-up -> Y-up if Z is the tallest axis).
usage: python3 -I bake_bind.py in.glb out.glb [--scale s] [--zup 0|1] [--yaw deg]"""
import json, struct, sys, math, argparse
import numpy as np
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('dst')
ap.add_argument('--scale', type=float, default=0); ap.add_argument('--zup', type=int, default=-1); ap.add_argument('--yaw', type=float, default=0)
a = ap.parse_args()
b = open(a.src, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20+n])
bl = struct.unpack('<I', b[20+n:24+n])[0]; B = bytearray(b[28+n:28+n+bl])
N = j['nodes']; skin = j['skins'][0]; joints = skin['joints']; jset = set(joints); root = joints[0]
par = {c: i for i, nd in enumerate(N) for c in nd.get('children', [])}
def acc_rng(ai):
    A = j['accessors'][ai]; v = j['bufferViews'][A['bufferView']]; return A, v, v.get('byteOffset', 0) + A.get('byteOffset', 0)
A, v, o = acc_rng(skin['inverseBindMatrices'])
ibm = np.frombuffer(bytes(B[o:o+64*len(joints)]), dtype='<f4').reshape(-1, 4, 4).astype(np.float64).transpose(0, 2, 1)
bind = {k: np.linalg.inv(ibm[i]) for i, k in enumerate(joints)}
# vertex bbox (all skinned prims)
def pos_arr(ai):
    A, v, o = acc_rng(ai); st = v.get('byteStride', 12)
    return np.lib.stride_tricks.as_strided(np.frombuffer(bytes(B[o:o+st*(A['count']-1)+12]), dtype=np.uint8), shape=(A['count'], 12), strides=(st, 1)).copy().view('<f4').reshape(-1, 3).astype(np.float64)
P = np.concatenate([pos_arr(p['attributes']['POSITION']) for m in j['meshes'] for p in m['primitives']])
ext = P.max(0) - P.min(0); print('vertex extent', np.round(ext, 3))
zup = a.zup if a.zup >= 0 else int(ext[2] > ext[1] * 1.2)
s = a.scale or (0.01 if max(ext) > 10 else 1.0)
R = np.eye(3)
if zup: R = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float64)      # Z-up -> Y-up
cy, sy = math.cos(math.radians(a.yaw)), math.sin(math.radians(a.yaw)); R = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]) @ R
Am = np.eye(4); Am[:3, :3] = R * s
print('normalise: scale', s, 'zup', zup)
G = {}
for k in joints:
    M = Am @ bind[k]; r = M[:3, :3]; r = r / np.linalg.norm(r, axis=0)
    # re-orthonormalise (IBMs carry float noise)
    u, _, vt = np.linalg.svd(r); r = u @ vt
    X = np.eye(4); X[:3, :3] = r; X[:3, 3] = M[:3, 3]; G[k] = X
G[root] = np.eye(4)
def quat(m):
    t = np.trace(m)
    if t > 0: S = math.sqrt(t+1)*2; w = 0.25*S; x = (m[2,1]-m[1,2])/S; y = (m[0,2]-m[2,0])/S; z = (m[1,0]-m[0,1])/S
    elif m[0,0] > m[1,1] and m[0,0] > m[2,2]: S = math.sqrt(1+m[0,0]-m[1,1]-m[2,2])*2; w = (m[2,1]-m[1,2])/S; x = 0.25*S; y = (m[0,1]+m[1,0])/S; z = (m[0,2]+m[2,0])/S
    elif m[1,1] > m[2,2]: S = math.sqrt(1+m[1,1]-m[0,0]-m[2,2])*2; w = (m[0,2]-m[2,0])/S; x = (m[0,1]+m[1,0])/S; y = 0.25*S; z = (m[1,2]+m[2,1])/S
    else: S = math.sqrt(1+m[2,2]-m[0,0]-m[1,1])*2; w = (m[1,0]-m[0,1])/S; x = (m[0,2]+m[2,0])/S; y = (m[1,2]+m[2,1])/S; z = 0.25*S
    q = np.array([x, y, z, w]); return [float(c) for c in q / np.linalg.norm(q)]
def clear(nd):
    for f in ('matrix', 'translation', 'rotation', 'scale'): nd.pop(f, None)
for i, nd in enumerate(N):           # every non-joint node -> identity (wrappers, intermediates)
    if i not in jset: clear(nd)
for k in joints:
    p = par.get(k)
    while p is not None and p not in jset: p = par.get(p)
    L = G[k] if (k == root or p is None) else np.linalg.inv(G[p]) @ G[k]
    clear(N[k])
    if np.abs(L[:3, 3]).max() > 1e-9: N[k]['translation'] = [float(c) for c in L[:3, 3]]
    N[k]['rotation'] = quat(L[:3, :3])
newibm = np.stack([np.linalg.inv(G[k]).T for k in joints]).astype('<f4')
B[o:o+64*len(joints)] = newibm.tobytes(); A.pop('min', None); A.pop('max', None)
done = set()
def xform(ai, kind):
    if ai in done: return
    done.add(ai); A, v, o = acc_rng(ai); comps = 3 if A['type'] == 'VEC3' else 4; st = v.get('byteStride', comps*4)
    raw = np.lib.stride_tricks.as_strided(np.frombuffer(bytes(B[o:o+st*(A['count']-1)+comps*4]), dtype=np.uint8), shape=(A['count'], comps*4), strides=(st, 1)).copy().view('<f4').reshape(-1, comps)
    xyz = raw[:, :3].astype(np.float64)
    if kind == 'P': xyz = xyz @ (R*s).T
    else: xyz = xyz @ R.T
    raw[:, :3] = xyz.astype('<f4')
    for i in range(A['count']): B[o+i*st:o+i*st+comps*4] = raw[i].tobytes()
    if kind == 'P': A['min'] = [float(c) for c in xyz.min(0)]; A['max'] = [float(c) for c in xyz.max(0)]
for m in j['meshes']:
    for p in m['primitives']:
        at = p['attributes']; xform(at['POSITION'], 'P')
        if 'NORMAL' in at: xform(at['NORMAL'], 'N')
        if 'TANGENT' in at: xform(at['TANGENT'], 'T')
js = json.dumps(j, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
bb = bytes(B); bb += b'\0' * ((4 - len(bb) % 4) % 4)
open(a.dst, 'wb').write(b'glTF' + struct.pack('<II', 2, 12+8+len(js)+8+len(bb)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(bb)) + b'BIN\0' + bb)
pel = [k for k in joints if N[k]['name'] == 'pelvis']
print('wrote', a.dst, 'pelvis', np.round(G[pel[0]][:3, 3], 3) if pel else '-', 'feet y min', round(float((P @ (R*s).T)[:, 1].min()), 3))
