"""small glTF-binary reader helpers shared by the skin tools"""
import json, struct, math
import numpy as np
CT = {5120: 'i1', 5121: 'u1', 5122: 'i2', 5123: 'u2', 5125: 'u4', 5126: 'f4'}; NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
def rd(fn):
    b = open(fn, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + n])
    bl = struct.unpack('<I', b[20 + n:24 + n])[0]; return j, bytearray(b[28 + n:28 + n + bl])
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
def parents(j): return {c: i for i, nd in enumerate(j['nodes']) for c in nd.get('children', [])}
def world(j, i, par=None):
    par = par or parents(j); M = node_m(j['nodes'][i])
    while i in par: i = par[i]; M = node_m(j['nodes'][i]) @ M
    return M
def quat(m):
    t = np.trace(m)
    if t > 0: S = math.sqrt(t+1)*2; w = 0.25*S; x = (m[2,1]-m[1,2])/S; y = (m[0,2]-m[2,0])/S; z = (m[1,0]-m[0,1])/S
    elif m[0,0] > m[1,1] and m[0,0] > m[2,2]: S = math.sqrt(1+m[0,0]-m[1,1]-m[2,2])*2; w = (m[2,1]-m[1,2])/S; x = 0.25*S; y = (m[0,1]+m[1,0])/S; z = (m[0,2]+m[2,0])/S
    elif m[1,1] > m[2,2]: S = math.sqrt(1+m[1,1]-m[0,0]-m[2,2])*2; w = (m[0,2]-m[2,0])/S; x = (m[0,1]+m[1,0])/S; y = 0.25*S; z = (m[1,2]+m[2,1])/S
    else: S = math.sqrt(1+m[2,2]-m[0,0]-m[1,1])*2; w = (m[1,0]-m[0,1])/S; x = (m[0,2]+m[2,0])/S; y = (m[1,2]+m[2,1])/S; z = 0.25*S
    q = np.array([x, y, z, w]); return [float(c) for c in q / np.linalg.norm(q)]
def flatten_static(j, B, drop=()):
    """all mesh primitives in world space: list of dict(name, X, N, UV, I, mat)"""
    par = parents(j); out = []
    for i, nd in enumerate(j['nodes']):
        if 'mesh' not in nd: continue
        m = j['meshes'][nd['mesh']]
        if any(d in m.get('name', '') for d in drop): continue
        M = world(j, i, par); Nm = np.linalg.inv(M[:3, :3]).T
        for p in m['primitives']:
            at = p['attributes']; X = acc(j, B, at['POSITION']).astype(np.float64) @ M[:3, :3].T + M[:3, 3]
            Nn = acc(j, B, at['NORMAL']).astype(np.float64) @ Nm.T if 'NORMAL' in at else np.tile([0., 1., 0.], (len(X), 1))
            UV = acc(j, B, at['TEXCOORD_0']).astype(np.float32) if 'TEXCOORD_0' in at else np.zeros((len(X), 2), np.float32)
            I = acc(j, B, p['indices']).reshape(-1).astype(np.uint32) if 'indices' in p else np.arange(len(X), dtype=np.uint32)
            out.append(dict(name=m.get('name', ''), X=X, N=Nn, UV=UV, I=I, mat=p.get('material', 0)))
    return out
