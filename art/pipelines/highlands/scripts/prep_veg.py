# prep_veg.py - clean the CC-BY Sketchfab/Objaverse vegetation GLBs into one glTF per plant (pivot at the base, metres,
# Y-up glTF, UE material slots named after the source material) + extract their textures as PNG.
# usage: python3 -I prep_veg.py <dl_dir> <out_dir>
import sys, os, json, struct
import numpy as np
from PIL import Image

DL, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


class GLB:
    def __init__(self, f):
        b = open(f, 'rb').read()
        n = struct.unpack('<I', b[12:16])[0]
        self.j = json.loads(b[20:20 + n])
        self.bin = b[20 + n + 8:]

    def acc(self, i):
        a = self.j['accessors'][i]; bv = self.j['bufferViews'][a['bufferView']]
        dt = np.dtype(CT[a['componentType']]); nc = NC[a['type']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = bv.get('byteStride', 0) or dt.itemsize * nc
        raw = np.frombuffer(self.bin, np.uint8, count=stride * (a['count'] - 1) + dt.itemsize * nc, offset=off)
        out = np.lib.stride_tricks.as_strided(raw, (a['count'], dt.itemsize * nc), (stride, 1)).copy().view(dt).reshape(a['count'], nc)
        if a.get('normalized'):
            out = out.astype(np.float32) / np.iinfo(dt).max
        return out.astype(np.float64) if dt == np.float32 or a.get('normalized') else out

    def image(self, idx, path):
        im = self.j['images'][idx]; bv = self.j['bufferViews'][im['bufferView']]
        o = bv.get('byteOffset', 0)
        open(path, 'wb').write(self.bin[o:o + bv['byteLength']])

    def world_mats(self):
        """mesh index -> list of world matrices (node instances)"""
        def local(nd):
            if 'matrix' in nd:
                return np.array(nd['matrix']).reshape(4, 4).T
            T = np.eye(4)
            if 'scale' in nd:
                T = np.diag(list(nd['scale']) + [1.0]) @ T
            if 'rotation' in nd:
                x, y, z, w = nd['rotation']
                R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                              [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                              [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
                M = np.eye(4); M[:3, :3] = R; T = M @ T
            if 'translation' in nd:
                M = np.eye(4); M[:3, 3] = nd['translation']; T = M @ T
            return T
        out = {}
        def walk(i, P):
            nd = self.j['nodes'][i]; W = P @ local(nd)
            if 'mesh' in nd:
                out.setdefault(nd['mesh'], []).append(W)
            for c in nd.get('children', []):
                walk(c, W)
        for s in self.j['scenes'][self.j.get('scene', 0)]['nodes']:
            walk(s, np.eye(4))
        return out


def gather(g, mesh_ids):
    """-> list of (matname, pos Nx3, nrm Nx3, uv Nx2, tri Mx3) in glTF world space (Y up)"""
    W = g.world_mats(); prims = []
    for mi in mesh_ids:
        for M in W.get(mi, []):
            for p in g.j['meshes'][mi]['primitives']:
                pos = g.acc(p['attributes']['POSITION'])
                nrm = g.acc(p['attributes']['NORMAL']) if 'NORMAL' in p['attributes'] else np.tile([0, 1.0, 0], (len(pos), 1))
                uv = g.acc(p['attributes']['TEXCOORD_0']) if 'TEXCOORD_0' in p['attributes'] else np.zeros((len(pos), 2))
                tri = g.acc(p['indices']).reshape(-1, 3) if 'indices' in p else np.arange(len(pos)).reshape(-1, 3)
                pos = (np.c_[pos, np.ones(len(pos))] @ M.T)[:, :3]
                nrm = nrm @ np.linalg.inv(M[:3, :3]).T
                nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
                if np.linalg.det(M[:3, :3]) < 0:
                    tri = tri[:, ::-1]
                mname = g.j['materials'][p['material']].get('name', 'mat%d' % p['material']) if 'material' in p else 'default'
                prims.append([mname, pos, nrm, uv, tri.astype(np.int64)])
    return prims


def components(tri, n):
    par = np.arange(n)
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    for t in tri:
        r = [find(int(v)) for v in t]
        for x in r[1:]:
            par[x] = r[0]
    return np.array([find(i) for i in range(n)])


def split_clumps(prim, gap=0.15):
    """split one primitive into separate plants: connected components merged when their XZ boxes overlap (expanded by gap*height)"""
    mname, pos, nrm, uv, tri = prim
    comp = components(tri, len(pos))
    ids = np.unique(comp)
    boxes = []
    for c in ids:
        v = pos[comp == c]
        boxes.append([v[:, 0].min(), v[:, 0].max(), v[:, 2].min(), v[:, 2].max(), v[:, 1].max() - v[:, 1].min()])
    boxes = np.array(boxes); grp = list(range(len(ids)))
    def f(a):
        while grp[a] != a:
            a = grp[a]
        return a
    hmax = boxes[:, 4].max()
    for i in range(len(ids)):
        for k in range(i + 1, len(ids)):
            e = gap * hmax
            if boxes[i, 0] - e < boxes[k, 1] and boxes[k, 0] - e < boxes[i, 1] and boxes[i, 2] - e < boxes[k, 3] and boxes[k, 2] - e < boxes[i, 3]:
                grp[f(k)] = f(i)
    out = {}
    for i, c in enumerate(ids):
        out.setdefault(f(i), []).append(c)
    res = []
    for cs in out.values():
        vm = np.isin(comp, cs)
        remap = -np.ones(len(pos), np.int64); remap[vm] = np.arange(vm.sum())
        tm = vm[tri[:, 0]]
        res.append([mname, pos[vm], nrm[vm], uv[vm], remap[tri[tm]]])
    res.sort(key=lambda r: r[1][:, 0].mean())
    return res


def write(path, prims, height=None, scale=None):
    allp = np.concatenate([p[1] for p in prims])
    base = np.array([(allp[:, 0].min() + allp[:, 0].max()) / 2, allp[:, 1].min(), (allp[:, 2].min() + allp[:, 2].max()) / 2])
    h = allp[:, 1].max() - allp[:, 1].min()
    s = scale if scale else (height / h if height else 1.0)
    blob = b''; views = []; accs = []; gprims = []; mats = []
    for mname, pos, nrm, uv, tri in prims:
        P = ((pos - base) * s).astype(np.float32); Nn = nrm.astype(np.float32); U = uv.astype(np.float32); T = tri.astype(np.uint32).reshape(-1)
        b0 = len(accs)
        for arr, typ, comp in ((P, 'VEC3', 5126), (Nn, 'VEC3', 5126), (U, 'VEC2', 5126), (T, 'SCALAR', 5125)):
            bb = arr.tobytes()
            views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(bb)})
            a = {'bufferView': len(views) - 1, 'componentType': comp, 'count': int(arr.shape[0]), 'type': typ}
            if arr is P:
                a['min'] = P.min(0).tolist(); a['max'] = P.max(0).tolist()
            accs.append(a); blob += bb + b'\0' * ((4 - len(bb) % 4) % 4)
        if mname not in mats:
            mats.append(mname)
        gprims.append({'attributes': {'POSITION': b0, 'NORMAL': b0 + 1, 'TEXCOORD_0': b0 + 2}, 'indices': b0 + 3, 'material': mats.index(mname)})
    nm = os.path.basename(path)[:-5]
    open(path[:-5] + '.bin', 'wb').write(blob)
    j = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0, 'name': nm}],
         'meshes': [{'name': nm, 'primitives': gprims}], 'materials': [{'name': m} for m in mats],
         'buffers': [{'uri': nm + '.bin', 'byteLength': len(blob)}], 'bufferViews': views, 'accessors': accs}
    json.dump(j, open(path, 'w'))
    ntri = sum(len(p[4]) for p in prims)
    print('%-22s h=%.2f m (src %.2f, s=%.4f) tris=%d mats=%s' % (nm, h * s, h, s, ntri, mats))
    return {'name': nm, 'height_m': float(h * s), 'tris': int(ntri), 'mats': mats}


def run():
    info = {}
    G = lambda u: GLB(os.path.join(DL, 'glb', u + '.glb'))
    # evolveduk Pine (Tree It), 5.6k tris
    g = G('d45218a3fab3'); info['SM_Pine'] = write(os.path.join(OUT, 'SM_Pine.gltf'), gather(g, [0, 1]), height=1.0, scale=None) if False else None
    p = gather(g, [0, 1]); info['SM_Pine'] = write(os.path.join(OUT, 'SM_Pine.gltf'), p, height=15.0)
    g.image(0, OUT + '/T_Pine_Bark_D.png'); g.image(2, OUT + '/T_Pine_Bark_N.png'); g.image(3, OUT + '/T_Pine_Leaf_D.png'); g.image(5, OUT + '/T_Pine_Leaf_N.png')
    g = G('e74c71569845'); p = gather(g, [0, 1]); info['SM_Juniper'] = write(os.path.join(OUT, 'SM_Juniper.gltf'), p, height=3.2)
    g.image(0, OUT + '/T_Juniper_Bark_D.png'); g.image(2, OUT + '/T_Juniper_Bark_N.png'); g.image(3, OUT + '/T_Juniper_Leaf_D.png'); g.image(5, OUT + '/T_Juniper_Leaf_N.png')
    # 3dhdscan grass chunks (photoscanned cards)
    g = G('eb4f6dc9d4e3')
    for k, mi in (('a', 5), ('b', 4), ('c', 6)):
        info['SM_GrassScan_' + k] = write(os.path.join(OUT, 'SM_GrassScan_%s.gltf' % k), gather(g, [mi]), height=0.55)
    p = gather(g, [0])
    info['SM_GrassScan_d'] = write(os.path.join(OUT, 'SM_GrassScan_d.gltf'), p, height=0.45)
    g.image(9, OUT + '/T_GrassScan12_D.png'); g.image(10, OUT + '/T_GrassScan12_N.png'); g.image(0, OUT + '/T_GrassScan07_D.png'); g.image(1, OUT + '/T_GrassScan07_N.png')
    # emarshall temperate set: dry grass (mesh 3), green grass (mesh 9), poppies (mesh 6), white flowers (mesh 7)
    g = G('2edf52774f4d')
    for mesh, nm, hgt, img in ((3, 'GrassDry', 0.55, (0, 1)), (9, 'GrassGreen', 0.6, (15, 1)), (6, 'Poppy', 0.5, (7, 8)), (7, 'Daisy', 0.4, (9, 10))):
        prim = gather(g, [mesh])
        parts = split_clumps(prim[0]) if len(prim) == 1 else prim
        src_h = max(pp[1][:, 1].max() - pp[1][:, 1].min() for pp in parts)
        for i, pp in enumerate(parts):
            h = pp[1][:, 1].max() - pp[1][:, 1].min()
            info['SM_%s_%d' % (nm, i)] = write(os.path.join(OUT, 'SM_%s_%d.gltf' % (nm, i)), [pp], scale=hgt / src_h)
        g.image(img[0], OUT + '/T_%s_D.png' % nm); g.image(img[1], OUT + '/T_%s_N.png' % nm)
    json.dump(info, open(os.path.join(OUT, 'veg_info.json'), 'w'), indent=1)


if not os.environ.get("VEG_LODS"):
    run()


# ------------------------------------------------------------------------------- tree LODs that keep the foliage
# UE's auto reduction deletes leaf cards (distant pines became bare sticks in render t3). Here: simplify only the trunk
# (pyfqmr quadric decimation, UVs/normals re-projected from the nearest source vertex) and thin the cards instead.
def tree_lods(glb_uid, name, height, plan, meshes=(0, 1), trunk=lambda m: m.endswith('0Mat')):
    import pyfqmr
    from scipy.spatial import cKDTree
    g = GLB(os.path.join(DL, 'glb', glb_uid + '.glb'))
    prims = gather(g, list(meshes))
    allp = np.concatenate([p[1] for p in prims])
    base = np.array([(allp[:, 0].min() + allp[:, 0].max()) / 2, allp[:, 1].min(), (allp[:, 2].min() + allp[:, 2].max()) / 2])
    s = height / (allp[:, 1].max() - allp[:, 1].min())
    for li, (trunk_frac, keep_cards, grow) in enumerate(plan, start=1):
        out = []
        for mname, pos, nrm, uv, tri in prims:
            if trunk(mname):                 # trunk / branches
                simp = pyfqmr.Simplify(); simp.setMesh(pos, tri)
                simp.simplify_mesh(target_count=max(40, int(len(tri) * trunk_frac)), aggressiveness=5, preserve_border=False, verbose=0)
                v, f, n = simp.getMesh()
                _, idx = cKDTree(pos).query(v)
                out.append([mname, v, n if len(n) == len(v) else nrm[idx], uv[idx], f.astype(np.int64)])
            else:                            # leaf cards: keep a subset (largest first), enlarge to keep the crown volume
                comp = components(tri, len(pos)); ids = np.unique(comp)
                area = {c: 0.0 for c in ids}
                ta = np.linalg.norm(np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]]), axis=1)
                for t, a in zip(comp[tri[:, 0]], ta):
                    area[t] += a
                order = sorted(ids, key=lambda c: -area[c])
                keep = set(order[:max(1, int(len(order) * keep_cards))])
                vm = np.isin(comp, list(keep))
                P = pos.copy()
                for c in keep:
                    sel = comp == c; ctr = P[sel].mean(0); P[sel] = ctr + (P[sel] - ctr) * grow
                remap = -np.ones(len(pos), np.int64); remap[vm] = np.arange(vm.sum())
                tm = vm[tri[:, 0]]
                out.append([mname, P[vm], nrm[vm], uv[vm], remap[tri[tm]]])
        # same pivot/scale as LOD0
        for o in out:
            o[1] = o[1]
        nm = os.path.join(OUT, '%s_L%d.gltf' % (name, li))
        allq = np.concatenate([o[1] for o in out])
        # write() recentres on its own bbox: shift so its base/centre equals LOD0's
        info = write(nm, out, scale=s) if False else None
        blob_fix(nm, out, base, s)


def blob_fix(path, prims, base, s):
    """write() variant with an explicit pivot (LODs must share LOD0's pivot and scale)"""
    shifted = [[m, (p - base) * s + 0.0, n, u, t] for m, p, n, u, t in prims]
    # write() would recentre; neutralise by adding two invisible-degenerate guard points? simpler: inline writer
    blob = b''; views = []; accs = []; gprims = []; mats = []
    for mname, P, Nn, U, T in shifted:
        P = P.astype(np.float32); Nn = Nn.astype(np.float32); U = U.astype(np.float32); T = T.astype(np.uint32).reshape(-1)
        b0 = len(accs)
        for arr, typ, comp in ((P, 'VEC3', 5126), (Nn, 'VEC3', 5126), (U, 'VEC2', 5126), (T, 'SCALAR', 5125)):
            bb = arr.tobytes()
            views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(bb)})
            a = {'bufferView': len(views) - 1, 'componentType': comp, 'count': int(arr.shape[0]), 'type': typ}
            if arr is P:
                a['min'] = P.min(0).tolist(); a['max'] = P.max(0).tolist()
            accs.append(a); blob += bb + b'\0' * ((4 - len(bb) % 4) % 4)
        if mname not in mats:
            mats.append(mname)
        gprims.append({'attributes': {'POSITION': b0, 'NORMAL': b0 + 1, 'TEXCOORD_0': b0 + 2}, 'indices': b0 + 3, 'material': mats.index(mname)})
    nm = os.path.basename(path)[:-5]
    open(path[:-5] + '.bin', 'wb').write(blob)
    j = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0, 'name': nm}],
         'meshes': [{'name': nm, 'primitives': gprims}], 'materials': [{'name': m} for m in mats],
         'buffers': [{'uri': nm + '.bin', 'byteLength': len(blob)}], 'bufferViews': views, 'accessors': accs}
    json.dump(j, open(path, 'w'))
    print('%-22s tris=%d' % (nm, sum(len(p[4]) for p in prims)))


if os.environ.get('VEG_LODS'):
    os.makedirs(os.path.join(OUT, 'lods'), exist_ok=True)
    OUT = os.path.join(OUT, 'lods')
    tree_lods('d45218a3fab3', 'SM_Pine', 15.0, [(0.22, 1.0, 1.0), (0.05, 0.55, 1.3), (0.012, 0.3, 1.6)])
    tree_lods('e74c71569845', 'SM_Juniper', 3.2, [(0.25, 1.0, 1.0), (0.06, 0.5, 1.3)])


# ------------------------------------------------------------------------------- opaque far LOD (crown silhouette)
# ProfileGPU t5: thousands of distant pines with masked leaf cards cost ~4.6 ms (prepass + basepass).
# Far LOD = lathe of the real crown profile (90th-percentile radius per height bin of the leaf cards, 7 sides, jittered)
# + a hexagonal trunk; opaque material slot 'Far' (no alpha test, early-Z friendly). ~70-90 tris.
def tree_far(glb_uid, name, height, lod_index, sides=7, bins=10, seed=3, meshes=(0, 1), trunk=lambda m: m.endswith('0Mat'), rscale=0.92, trunk_mat='Tree_0Mat'):
    g = GLB(os.path.join(DL, 'glb', glb_uid + '.glb'))
    prims = gather(g, list(meshes))
    allp = np.concatenate([p[1] for p in prims])
    base = np.array([(allp[:, 0].min() + allp[:, 0].max()) / 2, allp[:, 1].min(), (allp[:, 2].min() + allp[:, 2].max()) / 2])
    s = height / (allp[:, 1].max() - allp[:, 1].min())
    leaf = np.concatenate([(p[1] - base) * s for p in prims if not trunk(p[0])])
    trunk = np.concatenate([(p[1] - base) * s for p in prims if trunk(p[0])])
    y0, y1 = np.percentile(leaf[:, 1], 2), leaf[:, 1].max()
    rng = np.random.default_rng(seed)
    rings = []
    hs = np.linspace(y0, y1, bins + 1)
    for i in range(bins + 1):
        lo, hi = hs[max(0, i - 1)], hs[min(bins, i + 1)]
        sel = leaf[(leaf[:, 1] >= lo) & (leaf[:, 1] <= hi)]
        r = np.percentile(np.hypot(sel[:, 0], sel[:, 2]), 80) if len(sel) > 5 else 0.05
        if i == bins: r = 0.05
        tier = 1.0 if i % 2 == 0 else 0.62                     # conifer whorls: alternate full / pulled-in rings
        rings.append((hs[i], r * rscale * tier))
    P = []; T = []
    for k, (y, r) in enumerate(rings):
        for j in range(sides):
            a = 2 * np.pi * (j + 0.5 * (k % 2)) / sides
            rr = r * rng.uniform(0.7, 1.3)
            P.append((np.cos(a) * rr, y + rng.uniform(-0.15, 0.15) * (y1 - y0) / bins, np.sin(a) * rr))
    for k in range(bins):
        for j in range(sides):
            a, b = k * sides + j, k * sides + (j + 1) % sides
            c, d = a + sides, b + sides
            T += [(a, c, b), (b, c, d)]
    # bottom cap
    cb = len(P); P.append((0, y0 - 0.2, 0))
    for j in range(sides):
        T.append((cb, j, (j + 1) % sides))
    P = np.array(P); T = np.array(T)
    # outward normals (radial + slope)
    Nn = P.copy(); Nn[:, 1] = 0.35; Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    # orientation: make every triangle face away from the axis
    ctr = P[T].mean(1); cr = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    out = ctr.copy(); out[:, 1] = 0; out[np.linalg.norm(out, axis=1) < 1e-6] = [0, -1, 0]
    bad = np.einsum('ij,ij->i', cr, out) < 0; T[bad] = T[bad][:, ::-1]
    crown = ['Far', P / s + base, Nn, np.zeros((len(P), 2)), T]
    # trunk prism
    tr = max(0.08, np.percentile(np.hypot(trunk[trunk[:, 1] < 1.0][:, 0], trunk[trunk[:, 1] < 1.0][:, 2]), 70))
    TP = []; TT = []
    for k, y in enumerate((0.0, y0 + 0.3)):
        for j in range(6):
            a = 2 * np.pi * j / 6; TP.append((np.cos(a) * tr * (1 - 0.4 * k), y, np.sin(a) * tr * (1 - 0.4 * k)))
    for j in range(6):
        a, b = j, (j + 1) % 6; TT += [(a, a + 6, b), (b, a + 6, b + 6)]
    TP = np.array(TP); TT = np.array(TT)
    ctr = TP[TT].mean(1); cr = np.cross(TP[TT[:, 1]] - TP[TT[:, 0]], TP[TT[:, 2]] - TP[TT[:, 0]]); out = ctr.copy(); out[:, 1] = 0
    bad = np.einsum('ij,ij->i', cr, out) < 0; TT[bad] = TT[bad][:, ::-1]
    TN = TP.copy(); TN[:, 1] = 0; TN /= np.linalg.norm(TN, axis=1, keepdims=True)
    tprim = [trunk_mat, TP / s + base, TN, np.zeros((len(TP), 2)), TT]
    # glTF is right-handed with CCW front faces; the outward test above is in glTF space already
    blob_fix(os.path.join(OUT, '%s_L%d.gltf' % (name, lod_index)), [tprim, crown], base, s)


if os.environ.get('VEG_LODS'):
    tree_far('d45218a3fab3', 'SM_Pine', 15.0, 4)
    tree_far('e74c71569845', 'SM_Juniper', 3.2, 3)


if os.environ.get('VEG_PINEC'):
    # emarshall "Pine Tree" (Corsican pine, CC-BY): 2.4k-tri trunk + 44k tris of needle-tuft cards -> denser, darker crown
    OUT0 = OUT
    g = GLB(os.path.join(DL, 'glb', '9dfbe65769c8.glb'))
    write(os.path.join(OUT0, 'SM_PineC.gltf'), gather(g, [0, 1, 2, 3, 4]), height=16.0)
    g.image(0, OUT0 + '/T_PineC_Bark_D.png'); g.image(1, OUT0 + '/T_PineC_Leaf_D.png')
    OUT = os.path.join(OUT0, 'lods'); os.makedirs(OUT, exist_ok=True)
    tk = lambda m: m == 'initialShadingGroup'
    tree_lods('9dfbe65769c8', 'SM_PineC', 16.0, [(0.35, 0.5, 1.2), (0.12, 0.3, 1.4)], meshes=(0, 1, 2, 3, 4), trunk=tk)
    tree_far('9dfbe65769c8', 'SM_PineC', 16.0, 3, sides=9, bins=16, meshes=(0, 1, 2, 3, 4), trunk=tk, rscale=0.95, trunk_mat='initialShadingGroup')
