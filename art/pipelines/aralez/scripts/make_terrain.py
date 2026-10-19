"""Procedural highland terrain (original, CC0): flat battlefield in the centre, rolling hills, far mountain ring.
Writes a glTF (Y-up metres) polar grid.  usage: python3 -I make_terrain.py out.glb"""
import numpy as np, json, struct, sys, math
rng = np.random.default_rng(5)
# square grid, sinh-warped: ~2 m cells at the battlefield, ~300 m at the 14 km edge (well-shaped quads everywhere)
NR = NA = 401
k = 5.0; u = np.linspace(-1, 1, NR); w = 3700.0 * np.sinh(k * u) / np.sinh(k)
X, Y = np.meshgrid(w, w, indexing='ij'); R = np.hypot(X, Y)
def vnoise(x, y, cell, seed):
    r = np.random.default_rng(seed); G = r.random((257, 257)); G[256, :] = G[0, :]; G[:, 256] = G[:, 0]   # periodic: no seam
    u = x / cell + 1000.0; v = y / cell + 1000.0; i = np.floor(u).astype(int); j = np.floor(v).astype(int); fu = u - i; fv = v - j
    fu = fu * fu * (3 - 2 * fu); fv = fv * fv * (3 - 2 * fv); i %= 256; j %= 256
    a = G[i, j]; b = G[i + 1, j]; c = G[i, j + 1]; d = G[i + 1, j + 1]
    return a * (1 - fu) * (1 - fv) + b * fu * (1 - fv) + c * (1 - fu) * fv + d * fu * fv
def fbm(x, y, cell, oct, seed):
    h = 0; amp = 1; tot = 0
    for o in range(oct):
        h = h + amp * vnoise(x, y, cell / 2 ** o, seed + o); tot += amp; amp *= 0.5
    return h / tot   # 0..1
hills = (fbm(X, Y, 900.0, 5, 10) - 0.45) * 40.0 * np.clip((R - 150) / 600, 0, 1) ** 1.5
ridge = 1 - np.abs(fbm(X, Y, 1800.0, 5, 20) * 2 - 1)
mount = ridge ** 2.2 * 230.0 * np.clip((R - 1300) / 1600, 0, 1) ** 1.3
cx, cy = 3300.0 * math.cos(math.radians(105)), 3300.0 * math.sin(math.radians(105))
d = np.hypot(X - cx, Y - cy); volc = 480.0 * np.clip(1 - d / 1900.0, 0, 1) ** 1.6 * (0.9 + 0.1 * fbm(X, Y, 400.0, 3, 40))
micro = (fbm(X, Y, 9.0, 3, 30) - 0.5) * 0.25 * np.clip(1 - R / 400, 0, 1)
H = (hills + mount + volc) * np.clip((5000 - R) / 1200, 0, 1) + micro
H[R < 80] *= 0.3
P = np.stack([X, H, -Y], -1).reshape(-1, 3).astype(np.float32)   # glTF Y-up: (x, up, -y)
# normals via finite differences on the grid
Pg = P.reshape(NR, NA, 3)
dx = np.gradient(Pg, axis=0); dy = np.gradient(Pg, axis=1)
N = np.cross(dx, dy); N /= np.linalg.norm(N, axis=-1, keepdims=True); N[N[..., 1] < 0] *= -1
N = N.reshape(-1, 3).astype(np.float32)
UV = (np.stack([X, Y], -1).reshape(-1, 2) / 10.0).astype(np.float32)
idx = []
for i in range(NR - 1):
    for j in range(NA - 1):
        v0 = i * NA + j; v1 = v0 + 1; v2 = v0 + NA; v3 = v2 + 1
        idx += [v0, v2, v1, v1, v2, v3]
I = np.array(idx, np.uint32)
bins = [P.tobytes(), N.tobytes(), UV.tobytes(), I.tobytes()]
offs = np.cumsum([0] + [len(b) for b in bins])
buf = b''.join(bins)
j = {'asset': {'version': '2.0', 'generator': 'aralez make_terrain'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0, 'name': 'SM_Highlands'}],
     'meshes': [{'name': 'SM_Highlands', 'primitives': [{'attributes': {'POSITION': 0, 'NORMAL': 1, 'TEXCOORD_0': 2}, 'indices': 3, 'material': 0}]}],
     'materials': [{'name': 'M_Ground'}],
     'buffers': [{'byteLength': len(buf)}],
     'bufferViews': [{'buffer': 0, 'byteOffset': int(offs[k]), 'byteLength': len(bins[k])} for k in range(4)],
     'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': len(P), 'type': 'VEC3', 'min': P.min(0).tolist(), 'max': P.max(0).tolist()},
                   {'bufferView': 1, 'componentType': 5126, 'count': len(N), 'type': 'VEC3'},
                   {'bufferView': 2, 'componentType': 5126, 'count': len(UV), 'type': 'VEC2'},
                   {'bufferView': 3, 'componentType': 5125, 'count': len(I), 'type': 'SCALAR'}]}
js = json.dumps(j).encode(); js += b' ' * ((4 - len(js) % 4) % 4); buf += b'\0' * ((4 - len(buf) % 4) % 4)
out = b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(buf)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(buf)) + b'BIN\0' + buf
open(sys.argv[1], 'wb').write(out); print('verts', len(P), 'tris', len(I) // 3, 'hmax', H.max())
