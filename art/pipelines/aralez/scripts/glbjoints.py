"""print glTF world-space positions of named nodes: glbjoints.py file.glb name..."""
import json, struct, sys
import numpy as np
b = open(sys.argv[1], 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + n])
nodes = j['nodes']; par = {}
for i, nd in enumerate(nodes):
    for c in nd.get('children', []): par[c] = i
def q2m(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
def local(i):
    nd = nodes[i]; M = np.eye(4)
    if 'matrix' in nd: return np.array(nd['matrix']).reshape(4, 4).T
    M[:3, :3] = q2m(nd.get('rotation', [0, 0, 0, 1])) * np.array(nd.get('scale', [1, 1, 1]))
    M[:3, 3] = nd.get('translation', [0, 0, 0]); return M
def world(i):
    M = local(i)
    while i in par: i = par[i]; M = local(i) @ M
    return M
names = {nd.get('name'): i for i, nd in enumerate(nodes)}
for nm in sys.argv[2:] or [nodes[k].get('name') for k in range(min(5, len(nodes)))]:
    if nm in names: print(nm, np.round(world(names[nm])[:3, 3], 4), 'parent', nodes[par[names[nm]]]['name'] if names[nm] in par else None)
