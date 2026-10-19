# dem_maps.py - per-region textures baked from the DEM (called by dem_build.py 'maps' stage, or: python3 -P dem_maps.py <gen>)
#   T_<r>_N     world-space normal map (R = +X east, G = +Y south, Z reconstructed), UE: TC_Normalmap, no green flip,
#               material uses TangentSpaceNormal = false.  core 4096 (7.3 m/texel, DEM + micro relief), mid 4096 (z12 DEM, 29 m),
#               far 2048 (z10 DEM).
#   T_<r>_Mask  RGBA8 (linear): R rock (slope/ridge), G scree/talus, B snow, A lush (flow accumulation, north aspect, low slope)
#   T_<r>_Light RGBA8 (linear): R baked sun visibility for the sunset sun (SUN_AZ, SUN_EL; soft), G sky visibility (AO),
#               B stream channels (wet lines), A shore band (1 at the waterline -> 0 at ~120 m inland, lake bed = 1)
import os, sys, math, json
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dem_build as D

SUN_AZ, SUN_EL = 255.0, 8.0   # degrees; azimuth from north clockwise. UE light rotation: yaw = -15, pitch = -8 (see README)
SNOWLINE = 3150.0             # patches above this (north faces/gullies), full cover ~600 m higher
RES = {'core': (4096, 2048), 'mid': (4096, 2048), 'far': (2048, 1024)}   # (normal res, mask res)
NZ = {'core': None, 'mid': 12, 'far': 10}                              # DEM zoom for the normal map (None = from heights)


def log(*a):
    print(*a, flush=True)


def resample(A, n):
    m = A.shape[0]
    c = np.linspace(0, m - 1, n)
    return ndimage.map_coordinates(A, np.meshgrid(c, c)[::-1], order=3, mode='nearest')


def save_rgba(path, ch):
    a = np.stack([np.clip(c, 0, 1) for c in ch], -1)
    Image.fromarray((a * 255 + 0.5).astype(np.uint8), 'RGBA' if len(ch) == 4 else 'RGB').save(path)


def world_height_fn(gen):
    """sampler over all regions (true elevation minus curvature drop, metres) for shadow marching beyond a region"""
    regs = []
    for name in ('core', 'mid', 'far'):
        size = D.REGIONS[name][0]
        H = np.load(os.path.join(gen, name + '_H.npy')).astype(np.float64) - np.load(os.path.join(gen, name + '_drop.npy'))
        regs.append((size, H))

    def f(x, y):
        out = np.full(x.shape, -1e4)
        done = np.zeros(x.shape, bool)
        for size, H in regs:
            n = H.shape[0]
            inside = (~done) & (np.abs(x) <= size / 2) & (np.abs(y) <= size / 2)
            if inside.any():
                cx = (x[inside] / size + 0.5) * (n - 1); cy = (y[inside] / size + 0.5) * (n - 1)
                out[inside] = ndimage.map_coordinates(H, [cy, cx], order=1, mode='nearest')
                done |= inside
        return out
    return f


def horizon_tan(Hs, X, Y, fh, dx, dy, max_d, first, growth=1.06):
    """max over t of (h(p + t*d) - h(p)) / t  marching outward with geometric steps"""
    best = np.full(Hs.shape, -10.0)
    t = first
    while t < max_d:
        h = fh(X + dx * t, Y + dy * t)
        best = np.maximum(best, (h - Hs) / t)
        t *= growth
    return best


def flow_accumulation(H):
    n = H.shape[0]
    Hp = np.pad(H, 1, mode='edge')
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    drops = np.stack([(H - Hp[1 + a:1 + a + n, 1 + b:1 + b + n]) / math.hypot(a, b) for a, b in nb], 0)
    k = np.argmax(drops, 0)
    ok = drops.max(0) > 0
    rr, cc = np.indices(H.shape)
    tr = np.clip(rr + np.array([a for a, b in nb])[k], 0, n - 1)
    tc = np.clip(cc + np.array([b for a, b in nb])[k], 0, n - 1)
    recv = np.where(ok, tr * n + tc, -1).ravel()
    order = np.argsort(-H.ravel(), kind='stable')
    acc = np.ones(n * n)
    recv_l = recv.tolist(); accl = acc.tolist()
    for i in order.tolist():
        r = recv_l[i]
        if r >= 0:
            accl[r] += accl[i]
    return np.array(accl).reshape(n, n)


def smooth01(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def run(gen, regions=None):
    out = os.path.join(gen, 'tex'); os.makedirs(out, exist_ok=True)
    fh = world_height_fn(gen)
    az = math.radians(SUN_AZ)
    sdx, sdy = math.sin(az), -math.cos(az)          # toward the sun in (east, south)
    tan_el = math.tan(math.radians(SUN_EL))
    for name in (regions or D.REGIONS):
        size = D.REGIONS[name][0]
        H = np.load(os.path.join(gen, name + '_H.npy')).astype(np.float64)
        lake = np.load(os.path.join(gen, name + '_lake.npy'))
        nres, mres = RES[name]
        # ---------------------------------------------------------------- normal map
        sp_n = size / (nres - 1)
        if NZ[name] is None:
            Hn = resample(H, nres)
            s = (np.arange(nres) / (nres - 1) - 0.5) * size
            X, Y = np.meshgrid(s, s)
            sl = np.degrees(np.arctan(np.hypot(*np.gradient(Hn, sp_n))))
            micro = D.fbm(X, Y, 48.0, 3, 0.55, seed=11) * 0.35 * (1.0 - resample(lake.astype(np.float64), nres))
            Hn = Hn + micro
            del X, Y
        else:
            X, Y, lon, lat = D.grid_lonlat(size, nres)
            Hn = np.maximum(D.sample_dem(lon, lat, NZ[name]), -30.0)
            Hn = D.fix_seams(Hn, lon, lat, sp_n)
            ln = resample(lake.astype(np.float64), nres) > 0.5
            Hn = np.where(ln, np.minimum(Hn, D.LAKE_LEVEL - 2.0), Hn)   # flat bed under the water plane
            del X, Y, lon, lat
        gy, gx = np.gradient(Hn, sp_n)
        nz = 1.0 / np.sqrt(gx * gx + gy * gy + 1)
        nx, ny = -gx * nz, -gy * nz                  # world-space normal, X east, Y south
        Image.fromarray((np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5], -1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(out, 'T_%s_N.png' % name))
        log('[%s] normal %d done' % (name, nres)); del Hn, gx, gy, nx, ny, nz
        # ---------------------------------------------------------------- masks at mres
        Hm = resample(H, mres)
        sp = size / (mres - 1)
        lk = resample(lake.astype(np.float64), mres) > 0.5
        gy, gx = np.gradient(ndimage.gaussian_filter(Hm, 0.7), sp)
        slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        north = -(-gy) / np.maximum(np.hypot(gx, gy), 1e-6)          # +1 facing north (downhill toward -Y)
        north = np.where(np.hypot(gx, gy) < 0.03, 0.0, north)
        # curvature (positive = convex ridge) at ~3 texel scale
        lap = ndimage.gaussian_laplace(Hm, 2.0 if name == 'core' else 1.2) / (sp * sp)
        conv = np.clip(-lap * (40.0 if name == 'core' else 400.0) * sp / 15.0, -1, 1)
        s = (np.arange(mres) / (mres - 1) - 0.5) * size
        X, Y = np.meshgrid(s, s)
        nA = D.fbm(X, Y, 900.0, 4, 0.55, seed=21); nB = D.fbm(X, Y, 3000.0, 3, 0.5, seed=23)
        rock = smooth01(slope + conv * 12 + nA * 6, 19.0, 31.0)
        rock = np.maximum(rock, smooth01(Hm + nB * 150 + conv * 220, 2950.0, 3350.0) * 0.65 * smooth01(slope, 5, 16))  # crest boulder fields
        scree = ndimage.gaussian_filter(rock, 60.0 / sp + 1.0) * 1.6 * (1 - rock) * smooth01(slope, 14.0, 26.0)
        scree = np.clip(scree + smooth01(nA, 0.35, 0.6) * smooth01(slope, 18, 30) * 0.5, 0, 1)
        sline = SNOWLINE - north * 260.0 - conv * -180.0 + nB * 160.0 + nA * 60.0
        snow = smooth01(Hm, sline, sline + 600.0) * (1 - smooth01(slope, 38.0, 50.0) * 0.8)
        acc = flow_accumulation(ndimage.gaussian_filter(Hm, 1.0))
        cell = sp * sp
        wet = smooth01(np.log10(acc * cell), 4.3, 6.0)               # >2 ha catchment -> gully/stream
        lush = np.clip(0.45 + north * 0.25 + wet * 0.5 - smooth01(slope, 15, 35) * 0.4 - smooth01(Hm, 2700, 3300) * 0.35 + nA * 0.25, 0, 1)
        stream = smooth01(np.log10(acc * cell), 5.5, 7.0) * (1 - lk)
        # ---------------------------------------------------------------- sun shadow + sky visibility (true world heights incl. curvature)
        Hw = Hm - resample(np.load(os.path.join(gen, name + '_drop.npy')).astype(np.float64), mres)
        Hw = np.where(lk, D.LAKE_LEVEL, Hw)
        ht = horizon_tan(Hw + 2.0, X, Y, fh, sdx, sdy, 60000.0 if name != 'far' else 150000.0, sp * 0.7)
        soft = math.tan(math.radians(SUN_EL + 1.2)) - tan_el
        sunvis = smooth01(tan_el - ht, -soft, soft)
        ao = np.zeros_like(Hm)
        for k in range(8):
            a = k * math.pi / 4 + 0.3
            th = horizon_tan(Hw + 1.0, X, Y, fh, math.cos(a), math.sin(a), 3000.0 if name == 'core' else 12000.0, sp * 0.7, 1.15)
            ao += 1 - np.sin(np.arctan(np.maximum(th, 0)))
        ao /= 8
        dshore = ndimage.distance_transform_edt(~lk) * sp
        shore = np.where(lk, 1.0, np.exp(-dshore / 60.0))
        save_rgba(os.path.join(out, 'T_%s_Mask.png' % name), [rock, scree, snow, lush])
        save_rgba(os.path.join(out, 'T_%s_Light.png' % name), [sunvis, ao, stream, shore])
        log('[%s] masks %d: rock %.2f scree %.2f snow %.3f lush %.2f sunvis %.2f ao %.2f' % (name, mres, rock.mean(), scree.mean(), snow.mean(), lush.mean(), sunvis.mean(), ao.mean()))


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2:] or None)
