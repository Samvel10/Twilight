"""Flatten a static glTF (many nodes/meshes) into ONE mesh in world space, one primitive per material, so Interchange
imports a single StaticMesh.  usage: python3 -P glb_flatten.py in.glb out.glb [scale]"""
import sys, os, json, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from gltf_io import rd, flatten_static
j, B = rd(sys.argv[1]); sc = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
prims = flatten_static(j, B)
out = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'name': 'Prop', 'mesh': 0}], 'meshes': [{'name': 'Prop', 'primitives': []}],
       'accessors': [], 'bufferViews': [], 'buffers': [], 'materials': j.get('materials', []), 'textures': j.get('textures', []), 'samplers': j.get('samplers', []), 'images': []}
BIN = bytearray()
def view(d, t=None):
    while len(BIN) % 4: BIN.append(0)
    o = len(BIN); BIN.extend(d); v = {'buffer': 0, 'byteOffset': o, 'byteLength': len(d)}
    if t: v['target'] = t
    out['bufferViews'].append(v); return len(out['bufferViews']) - 1
def accw(arr, ct, typ, t=None, mm=False):
    arr = np.ascontiguousarray(arr); A = {'bufferView': view(arr.tobytes(), t), 'componentType': ct, 'count': int(arr.shape[0]), 'type': typ}
    if mm: A['min'] = [float(x) for x in arr.min(0)]; A['max'] = [float(x) for x in arr.max(0)]
    out['accessors'].append(A); return len(out['accessors']) - 1
for im in j.get('images', []):
    v = j['bufferViews'][im['bufferView']]; o = v.get('byteOffset', 0)
    out['images'].append({'bufferView': view(bytes(B[o:o + v['byteLength']])), 'mimeType': im.get('mimeType', 'image/png')})
byM = {}
for q in prims: byM.setdefault(q['mat'], []).append(q)
for m, qs in byM.items():
    X = np.concatenate([q['X'] for q in qs]) * sc; Nn = np.concatenate([q['N'] for q in qs]); Nn /= np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-9)
    UV = np.concatenate([q['UV'] for q in qs]); I = []; b = 0
    for q in qs: I.append(q['I'] + b); b += len(q['X'])
    out['meshes'][0]['primitives'].append({'attributes': {'POSITION': accw(X.astype(np.float32), 5126, 'VEC3', 34962, True), 'NORMAL': accw(Nn.astype(np.float32), 5126, 'VEC3', 34962),
        'TEXCOORD_0': accw(UV.astype(np.float32), 5126, 'VEC2', 34962)}, 'indices': accw(np.concatenate(I).astype(np.uint32).reshape(-1, 1), 5125, 'SCALAR', 34963), 'material': m})
while len(BIN) % 4: BIN.append(0)
out['buffers'] = [{'byteLength': len(BIN)}]
for k in ('images', 'textures', 'samplers', 'materials'):
    if not out[k]: out.pop(k)
js = json.dumps(out, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
open(sys.argv[2], 'wb').write(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(BIN)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(BIN)) + b'BIN\0' + bytes(BIN))
X = np.concatenate([q['X'] for q in prims]) * sc; print('wrote', sys.argv[2], 'prims', len(byM), 'extent', np.round(X.max(0) - X.min(0), 3))
