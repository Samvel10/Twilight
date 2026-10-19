# dem_build.py - real-DEM terrain for the Armenian-highlands test level (Geghama ridge / Azhdahak -> Lake Sevan,
# Masis/Ararat on the horizon).  Pure numpy/scipy, no engine.  Run with: python3 -P dem_build.py <gen_dir> [stage...]
#
# World frame (UE, cm):  X = east, Y = south (north = -Y), Z = up;  Z = 0 at LAKE_LEVEL (Sevan surface, 1898 m in the DEM).
# Three nested square regions share one centre (C_LON, C_LAT):
#   core  30 km, 10x10 tiles of 3 km,  160 quads/tile -> 18.75 m grid (LOD0), DEM z12 (29 m) + detail noise
#   mid  120 km,  8x8 tiles of 15 km (centre 2x2 = core removed), 150 quads -> 100 m grid, DEM z11
#   far  360 km,  6x6 tiles of 60 km (centre 2x2 = mid removed),  150 quads -> 400 m grid, DEM z9
# Earth curvature (with standard refraction, R_eff = 7/6 R) is applied, so Masis (93 km) sinks ~580 m like in reality.
# Elevation data: Mapzen/AWS "terrarium" terrain tiles (SRTM/GMTED/ETOPO; attribution in README).
import sys, os, math, json, io, struct, urllib.request
import numpy as np
from PIL import Image
from scipy import ndimage

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
STAGES = sys.argv[2:] if (len(sys.argv) > 2 and __name__ == '__main__') else ['heights', 'meshes', 'water', 'maps']
C_LON, C_LAT = float(os.environ.get('HL_CLON', 45.10)), float(os.environ.get('HL_CLAT', 40.27))   # site centre (env override)
LAKE_LEVEL = float(os.environ.get('HL_LAKE', 1898.0))   # Sevan surface in the SRTM-based tiles (flat at 1898.0 m); Z = 0 here
R_EARTH = 6371000.0
R_EFF = R_EARTH * 7.0 / 6.0
M_PER_DEG_LAT = 111132.954 - 559.822 * math.cos(2 * math.radians(C_LAT))
M_PER_DEG_LON = 111412.84 * math.cos(math.radians(C_LAT)) - 93.5 * math.cos(3 * math.radians(C_LAT))

REGIONS = {  # name: (size_m, tiles_per_side, quads_per_tile, dem_zoom, hole_tiles, lods)
    'core': (30000.0, 10, 160, 12, 0, 4),
    'mid': (120000.0, 8, 150, 11, 2, 3),
    'far': (360000.0, 6, 150, 9, 2, 3),
}
TILE_CACHE = os.environ.get('HL_TILES', os.path.join(OUT, 'dem', 'tiles'))


def log(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------------------------------- DEM sampling
def merc_px(lon, lat, z):
    n = 2 ** z * 256
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2.0 * n
    return x, y


def fetch_tile(z, tx, ty):
    p = os.path.join(TILE_CACHE, '%d_%d_%d.png' % (z, tx, ty))
    if not os.path.exists(p):
        u = 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/%d/%d/%d.png' % (z, tx, ty)
        b = urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'TwilightResearch/1.0'}), timeout=60).read()
        open(p, 'wb').write(b)
    a = np.asarray(Image.open(p).convert('RGB')).astype(np.float64)
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768


def sample_dem(lon, lat, z):
    """bicubic sample of terrarium zoom z at arrays lon/lat (degrees) -> metres"""
    os.makedirs(TILE_CACHE, exist_ok=True)
    px, py = merc_px(lon, lat, z)
    tx0, ty0 = int(px.min() // 256) - 1, int(py.min() // 256) - 1
    tx1, ty1 = int(px.max() // 256) + 1, int(py.max() // 256) + 1
    M = np.zeros(((ty1 - ty0 + 1) * 256, (tx1 - tx0 + 1) * 256))
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            M[(ty - ty0) * 256:(ty - ty0 + 1) * 256, (tx - tx0) * 256:(tx - tx0 + 1) * 256] = fetch_tile(z, tx, ty)
    log('  dem z%d tiles %dx%d' % (z, tx1 - tx0 + 1, ty1 - ty0 + 1))
    return ndimage.map_coordinates(M, [py - ty0 * 256 - 0.5, px - tx0 * 256 - 0.5], order=3, mode='nearest')


def fix_seams(H, lon, lat, sp):
    """SRTM 1-degree tile edges (45E, 40N here) carry 5-10 m steps; blur across them in a narrow band."""
    for k in range(math.ceil(lon.min()), math.floor(lon.max()) + 1):
        w = np.exp(-((lon - k) * M_PER_DEG_LON / 250.0) ** 2)
        H = H * (1 - w) + ndimage.gaussian_filter1d(H, 220.0 / sp, axis=1) * w
    for k in range(math.ceil(lat.min()), math.floor(lat.max()) + 1):
        w = np.exp(-((lat - k) * M_PER_DEG_LAT / 250.0) ** 2)
        H = H * (1 - w) + ndimage.gaussian_filter1d(H, 220.0 / sp, axis=0) * w
    return H


def grid_lonlat(size, n):
    """n x n sample grid (vertex centres) covering a square of `size` metres; returns x(east), y(south) metres + lon/lat"""
    s = (np.arange(n) / (n - 1) - 0.5) * size
    X, Y = np.meshgrid(s, s)  # rows = Y (south), cols = X (east)
    lat = C_LAT - Y / M_PER_DEG_LAT
    lon = C_LON + X / M_PER_DEG_LON
    return X, Y, lon, lat


# ------------------------------------------------------------------------------------------- detail noise
def value_noise(x, y, seed):
    xi, yi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = x - xi, y - yi

    def h(a, b):
        n = (a * 374761393 + b * 668265263 + seed * 1442695041) & 0xffffffff
        n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
        return ((n & 0xffff) / 65535.0) * 2 - 1
    u, v = fx * fx * fx * (fx * (fx * 6 - 15) + 10), fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    return (h(xi, yi) * (1 - u) + h(xi + 1, yi) * u) * (1 - v) + (h(xi, yi + 1) * (1 - u) + h(xi + 1, yi + 1) * u) * v


def fbm(X, Y, base_wl, octaves, gain=0.5, seed=1, ridged=False):
    acc = np.zeros_like(X); amp = 1.0; wl = base_wl; tot = 0
    for o in range(octaves):
        # rotate each octave to kill grid alignment
        a = 0.6 * o + seed
        xr = (X * math.cos(a) - Y * math.sin(a)) / wl
        yr = (X * math.sin(a) + Y * math.cos(a)) / wl
        n = value_noise(xr, yr, seed * 31 + o)
        if ridged:
            n = 1.0 - 2.0 * np.abs(n)
        acc += n * amp; tot += amp; amp *= gain; wl *= 0.5
    return acc / tot


def slope_deg(H, sp):
    gy, gx = np.gradient(H, sp)
    return np.degrees(np.arctan(np.hypot(gx, gy))), gx, gy


def detail(H, X, Y, sp):
    """sub-DEM relief (metres): gentle meadow hummocks + erosion rills elongated DOWNSLOPE on steeper ground.
    (v1 used isotropic ridged fBm: it rendered as smeared streaks and evenly spaced 'moguls'; rejected after render t1)"""
    Hs = ndimage.gaussian_filter(H, 3.0)
    gy, gx = np.gradient(Hs, sp)
    sl = np.degrees(np.arctan(np.hypot(gx, gy)))
    steep = np.clip((sl - 6.0) / 20.0, 0, 1)
    g = np.hypot(gx, gy) + 1e-6
    dx, dy = ndimage.gaussian_filter(gx / g, 4.0), ndimage.gaussian_filter(gy / g, 4.0)
    nrm = np.hypot(dx, dy) + 1e-6; dx /= nrm; dy /= nrm
    u = X * dx + Y * dy                       # along the fall line
    v = -X * dy + Y * dx                      # across it
    rills = D_fbm_aniso(u, v)
    hum = fbm(X, Y, 160.0, 3, 0.5, seed=3) * 0.9
    return hum + rills * 2.4 * steep


def D_fbm_aniso(u, v):
    """value-noise fBm stretched 6:1 along the fall line -> parallel gullies/rills, ridged so they read as incisions"""
    acc = np.zeros_like(u); amp = 1.0; tot = 0.0
    for o, (lu, lv) in enumerate(((420.0, 70.0), (210.0, 35.0), (105.0, 18.0))):
        n = value_noise(u / lu, v / lv, 50 + o)
        acc += (np.abs(n) * 2.0 - 0.6) * amp; tot += amp; amp *= 0.5
    return acc / tot


# ------------------------------------------------------------------------------------------- lake
def lake_carve(H, sp, level=LAKE_LEVEL, depth=45.0, shelf=700.0):
    """DEM lake surfaces are flat at ~level; push the bed down with distance from shore so the water has a shore
    gradient + depth colour, and lift tiny land specks inside the lake."""
    rng = ndimage.maximum_filter(H, 3) - ndimage.minimum_filter(H, 3)
    water = (np.abs(H - level) < 1.0) & (rng < 1.5)
    water = ndimage.binary_closing(water, iterations=2) & (H < level + 1.5)
    water |= ndimage.binary_fill_holes(water) & (H < level + 1.5)   # dry specks inside the lake (not real islands)
    lab, n = ndimage.label(water)
    if n == 0:
        return H, water
    sizes = ndimage.sum(water, lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.nonzero(sizes * sp * sp > 2.0e6)[0])   # only big water bodies (> 2 km^2)
    d = ndimage.distance_transform_edt(keep) * sp
    bed = level - 1.5 - depth * (1 - np.exp(-d / shelf))
    H2 = np.where(keep, np.minimum(H, bed), H)
    return H2, keep


# ------------------------------------------------------------------------------------------- heights per region
def build_heights(name):
    size, nt, q, z, hole, lods = REGIONS[name]
    n = nt * q + 1
    sp = size / (n - 1)
    X, Y, lon, lat = grid_lonlat(size, n)
    log('[%s] %d^2 samples, %.2f m grid' % (name, n, sp))
    H = np.maximum(sample_dem(lon, lat, z), -30.0)
    if sp < 150:
        H = fix_seams(H, lon, lat, sp)
    if name == 'core':
        # SRTM radar speckle (1-3 m, 50-150 m blobs) renders as 'moguls' under a low sun: smooth it on gentle ground only
        Hs = ndimage.gaussian_filter(H, 43.0 / sp)
        sl = np.degrees(np.arctan(np.hypot(*np.gradient(Hs, sp))))
        k = np.clip((sl - 12.0) / 10.0, 0, 1)
        H = Hs * (1 - k) + H * k
    H, lake = lake_carve(H, sp)
    if name == 'core':                       # detail after the lake test, faded out under/near the water
        wet = ndimage.gaussian_filter(ndimage.binary_dilation(lake, iterations=3).astype(np.float64), 2.0)
        H = H + detail(H, X, Y, sp) * (1.0 - wet)
    drop = (X ** 2 + Y ** 2) / (2 * R_EFF)
    np.save(os.path.join(OUT, '%s_H.npy' % name), H.astype(np.float32))       # true elevation (m)
    np.save(os.path.join(OUT, '%s_lake.npy' % name), lake)
    np.save(os.path.join(OUT, '%s_drop.npy' % name), drop.astype(np.float32))
    log('  elev %.0f..%.0f  lake %.1f%%  max curvature drop %.0f m' % (H.min(), H.max(), lake.mean() * 100, drop.max()))


# ------------------------------------------------------------------------------------------- meshes
def write_gltf(path, meshes):
    """meshes: list of (name, pos_ue_cm Nx3, uv Nx2, nrm_ue Nx3, tri Mx3). One node per mesh. UE->glTF: gx=x, gy=z, gz=y"""
    blob = b''; views = []; accs = []; gmeshes = []; nodes = []
    for name, pos, uv, nrm, tri in meshes:
        p = np.stack([pos[:, 0], pos[:, 2], pos[:, 1]], 1).astype(np.float32) / 100.0
        nn = np.stack([nrm[:, 0], nrm[:, 2], nrm[:, 1]], 1).astype(np.float32)
        t = tri.astype(np.uint32)
        base = len(accs)
        for arr, typ, comp in ((p, 'VEC3', 5126), (nn, 'VEC3', 5126), (uv.astype(np.float32), 'VEC2', 5126), (t.reshape(-1), 'SCALAR', 5125)):
            b = arr.tobytes()
            views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': len(b)})
            a = {'bufferView': len(views) - 1, 'componentType': comp, 'count': int(arr.shape[0]), 'type': typ}
            if arr is p:
                a['min'] = p.min(0).tolist(); a['max'] = p.max(0).tolist()
            accs.append(a)
            blob += b + b'\0' * ((4 - len(b) % 4) % 4)
        gmeshes.append({'name': name, 'primitives': [{'attributes': {'POSITION': base, 'NORMAL': base + 1, 'TEXCOORD_0': base + 2}, 'indices': base + 3}]})
        nodes.append({'mesh': len(gmeshes) - 1, 'name': name})
    binname = os.path.basename(path)[:-5] + '.bin'
    open(os.path.join(os.path.dirname(path), binname), 'wb').write(blob)
    j = {'asset': {'version': '2.0', 'generator': 'twilight dem_build.py'}, 'scene': 0, 'scenes': [{'nodes': list(range(len(nodes)))}],
         'nodes': nodes, 'meshes': gmeshes, 'buffers': [{'uri': binname, 'byteLength': len(blob)}], 'bufferViews': views, 'accessors': accs}
    json.dump(j, open(path, 'w'))


def tile_mesh(Hw, U, V, sp, skirt):
    """Hw: (k+1)^2 world Z (cm) for a tile at one LOD, relative XY grid built here. Returns pos (cm, tile-local), uv, nrm, tri
    with a skirt (border ring duplicated `skirt` cm lower) to hide LOD cracks between neighbouring tiles."""
    k = Hw.shape[0] - 1
    s = (np.arange(k + 1) - k / 2.0) * sp * 100.0
    X, Y = np.meshgrid(s, s)
    gy, gx = np.gradient(Hw, sp * 100.0)
    nrm = np.stack([-gx, -gy, np.ones_like(gx)], -1); nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    pos = np.stack([X, Y, Hw], -1).reshape(-1, 3)
    uv = np.stack([U, V], -1).reshape(-1, 2)
    nr = nrm.reshape(-1, 3)
    R = k + 1
    a = (np.arange(k)[None, :] + np.arange(k)[:, None] * R).ravel()
    # UE left-handed with Y=south: CCW seen from +Z in (east,south) == this order faces up after the glTF swap (checked)
    tri = np.stack([a, a + 1, a + R, a + 1, a + R + 1, a + R], 1).reshape(-1, 3)
    # skirt: walk the border ring
    ring = ([(0, i) for i in range(k)] + [(i, k) for i in range(k)] + [(k, k - i) for i in range(k)] + [(k - i, 0) for i in range(k)])
    ridx = np.array([r * R + c for r, c in ring])
    base = len(pos)
    sk = pos[ridx].copy(); sk[:, 2] -= skirt
    pos = np.concatenate([pos, sk]); uv = np.concatenate([uv, uv[ridx]]); nr = np.concatenate([nr, nr[ridx]])
    m = len(ridx); i0 = ridx; i1 = np.roll(ridx, -1); j0 = base + np.arange(m); j1 = base + np.roll(np.arange(m), -1)
    sk_tri = np.concatenate([np.stack([i0, j0, i1], 1), np.stack([i1, j0, j1], 1)])
    # orientation fix in glTF space (gx=x, gy=z, gz=y, right-handed, CCW front): surface faces +gy, skirt faces outwards
    G = np.stack([pos[:, 0], pos[:, 2], pos[:, 1]], 1)
    def fix(t, want):
        c = np.cross(G[t[:, 1]] - G[t[:, 0]], G[t[:, 2]] - G[t[:, 0]])
        bad = np.einsum('ij,ij->i', c, want(t)) < 0
        t[bad] = t[bad][:, ::-1]
        return t
    tri = fix(tri, lambda t: np.tile([0.0, 1.0, 0.0], (len(t), 1)))
    sk_tri = fix(sk_tri, lambda t: np.stack([G[t].mean(1)[:, 0], np.zeros(len(t)), G[t].mean(1)[:, 2]], 1))
    tri = np.concatenate([tri, sk_tri])
    return pos, uv, nr, tri


def build_meshes(name):
    size, nt, q, z, hole, lods = REGIONS[name]
    H = np.load(os.path.join(OUT, '%s_H.npy' % name)).astype(np.float64)
    drop = np.load(os.path.join(OUT, '%s_drop.npy' % name)).astype(np.float64)
    Zw = (H - LAKE_LEVEL - drop) * 100.0                           # world Z, cm
    n = H.shape[0]; sp = size / (n - 1)
    uvs = np.arange(n) / (n - 1)
    U, V = np.meshgrid(uvs, uvs)
    tsize = size / nt
    d = os.path.join(OUT, 'mesh', name); os.makedirs(d, exist_ok=True)
    lay = []
    lo, hi = (nt - hole) // 2, (nt + hole) // 2
    for ty in range(nt):
        for tx in range(nt):
            if hole and lo <= tx < hi and lo <= ty < hi:
                continue
            r0, c0 = ty * q, tx * q
            meshes = []
            for L in range(lods):
                st = 2 ** L
                sl = (slice(r0, r0 + q + 1, st), slice(c0, c0 + q + 1, st))
                Hw = Zw[sl]
                skirt = max(3000.0, sp * st * 100.0 * 1.5)
                pos, uv, nr, tri = tile_mesh(Hw, U[sl], V[sl], sp * st, skirt)
                meshes.append(('%s_%d_%d_L%d' % (name, tx, ty, L), pos, uv, nr, tri))
            tname = 'T_%s_%d_%d' % (name, tx, ty)
            write_gltf(os.path.join(d, tname + '.gltf'), meshes)
            cx = (tx + 0.5) * tsize - size / 2; cy = (ty + 0.5) * tsize - size / 2
            lay.append({'name': tname, 'loc': [cx * 100.0, cy * 100.0, 0.0], 'radius_m': tsize * 0.7071,
                        'zmin': float(Zw[r0:r0 + q + 1, c0:c0 + q + 1].min()), 'zmax': float(Zw[r0:r0 + q + 1, c0:c0 + q + 1].max())})
    json.dump({'region': name, 'size_m': size, 'tiles': lay, 'grid_m': sp, 'lods': lods}, open(os.path.join(OUT, 'mesh', name + '_layout.json'), 'w'), indent=0)
    log('[%s] %d tiles written (LOD0 %d verts/tile)' % (name, len(lay), (q + 1) ** 2))


def build_water(cell=200.0, chunks=4):
    """Lake surface: quads where the (dilated) mid-region lake mask is set, following the curvature drop (Z = -drop).
    Written as chunks W_<i>_<j>.gltf with vertices relative to the chunk centre (layout in mesh/water_layout.json)."""
    size = REGIONS['mid'][0]
    lake = np.load(os.path.join(OUT, 'mid_lake.npy'))
    n = lake.shape[0]
    m = int(round(size / cell))
    idx = (np.arange(m) + 0.5) * (n - 1) / m
    L = lake[np.ix_(idx.astype(int), idx.astype(int))]
    L = ndimage.binary_dilation(L, iterations=3)
    d = os.path.join(OUT, 'mesh', 'water'); os.makedirs(d, exist_ok=True)
    lay = []
    cs = m // chunks
    for cj in range(chunks):
        for ci in range(chunks):
            sub = L[cj * cs:(cj + 1) * cs, ci * cs:(ci + 1) * cs]
            if not sub.any():
                continue
            ys, xs = np.nonzero(sub)
            cx = ((ci + 0.5) * cs) * cell - size / 2; cy = ((cj + 0.5) * cs) * cell - size / 2
            verts = {}; pos = []; tri = []

            def v(ix, iy):
                k = (ix, iy)
                if k not in verts:
                    X = (ci * cs + ix) * cell - size / 2; Y = (cj * cs + iy) * cell - size / 2
                    verts[k] = len(pos); pos.append((X - cx, Y - cy, -(X * X + Y * Y) / (2 * R_EFF)))
                return verts[k]
            for y, x in zip(ys, xs):
                a, b, c, e = v(x, y), v(x + 1, y), v(x, y + 1), v(x + 1, y + 1)
                tri += [(a, c, b), (b, c, e)]
            P = np.array(pos) * 100.0
            T = np.array(tri)
            G = np.stack([P[:, 0], P[:, 2], P[:, 1]], 1)
            cr = np.cross(G[T[:, 1]] - G[T[:, 0]], G[T[:, 2]] - G[T[:, 0]])
            bad = cr[:, 1] < 0; T[bad] = T[bad][:, ::-1]
            uv = (P[:, :2] / 100.0 + [cx, cy]) / 1000.0          # km world UV (material uses world position anyway)
            nm = 'W_%d_%d' % (ci, cj)
            write_gltf(os.path.join(d, nm + '.gltf'), [(nm, P, uv, np.tile([0.0, 0.0, 1.0], (len(P), 1)), T)])
            lay.append({'name': nm, 'loc': [cx * 100.0, cy * 100.0, 0.0], 'quads': int(len(ys))})
    json.dump({'tiles': lay, 'cell_m': cell}, open(os.path.join(OUT, 'mesh', 'water_layout.json'), 'w'), indent=0)
    log('[water] %d chunks, %d quads' % (len(lay), sum(t['quads'] for t in lay)))


# ------------------------------------------------------------------------------------------- maps
def main():
    os.makedirs(OUT, exist_ok=True)
    for name in REGIONS:
        if 'heights' in STAGES:
            build_heights(name)
        if 'meshes' in STAGES:
            build_meshes(name)
    if 'water' in STAGES:
        build_water()
    if 'maps' in STAGES:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import dem_maps
        dem_maps.run(OUT, REGIONS)


if __name__ == '__main__':
    main()
