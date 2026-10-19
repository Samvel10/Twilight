# scatter.py - vegetation / rock placement rules on the core region (python3 -P scatter.py <gen>)
# Output gen/scatter/<Type>.f32 : float32 rows (x_cm, y_cm, z_cm, yaw_deg, scale, mesh_variant) + scatter_info.json.
# Rules use the same DEM products as the terrain material, so plants sit where the material paints meadow/rock/shore:
#   Pine     Sevan-shore plantations: elev < 2250 m, slope < 22 deg, groves from low-frequency noise, not on the beach
#   Juniper  dry rocky slopes 2000-2900 m, south-ish aspect, rock mask 0.15-0.7
#   Boulder  rock mask + scree + crest boulder fields (Geghama basalt "stone rivers"), size by mask strength
#   Grass/flowers  only within GRASS_RADIUS of the ground test views (the game must stream these around the player,
#            see README "runtime grass"): density by lush mask, flowers in lush patches, none on rock/snow/shore
import sys, os, json, math
import numpy as np
from PIL import Image
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dem_build as D

G = sys.argv[1]
OUTD = os.path.join(G, 'scatter'); os.makedirs(OUTD, exist_ok=True)
SIZE = D.REGIONS['core'][0]
Hc = np.load(os.path.join(G, 'core_H.npy')).astype(np.float64)
Zc = Hc - D.LAKE_LEVEL - np.load(os.path.join(G, 'core_drop.npy'))     # world Z in m
lake = np.load(os.path.join(G, 'core_lake.npy'))
mask = np.asarray(Image.open(os.path.join(G, 'tex', 'T_core_Mask.png'))).astype(np.float32) / 255.0
light = np.asarray(Image.open(os.path.join(G, 'tex', 'T_core_Light.png'))).astype(np.float32) / 255.0
cams = json.load(open(os.path.join(G, 'cams.json')))
rng = np.random.default_rng(1234)
n = Hc.shape[0]; sp = SIZE / (n - 1)
gy, gx = np.gradient(Hc, sp)
slope = np.degrees(np.arctan(np.hypot(gx, gy)))


def samp(A, x, y, order=1):
    m = A.shape[0]
    return ndimage.map_coordinates(A, [(y / SIZE + 0.5) * (m - 1), (x / SIZE + 0.5) * (m - 1)], order=order, mode='nearest')


def terrain_z(x, y):
    """height of the LOD0 triangle mesh (same diagonal split as dem_build.tile_mesh) at x,y metres"""
    u = (x / SIZE + 0.5) * (n - 1); v = (y / SIZE + 0.5) * (n - 1)
    i = np.clip(np.floor(u).astype(int), 0, n - 2); j = np.clip(np.floor(v).astype(int), 0, n - 2)
    fu, fv = u - i, v - j
    z00, z10, z01, z11 = Zc[j, i], Zc[j, i + 1], Zc[j + 1, i], Zc[j + 1, i + 1]
    # quad split a-(a+1)-(a+R) / (a+1)-(a+R+1)-(a+R): diagonal from (1,0) to (0,1)
    lower = fu + fv <= 1
    zl = z00 + (z10 - z00) * fu + (z01 - z00) * fv
    zu = z11 + (z01 - z11) * (1 - fu) + (z10 - z11) * (1 - fv)
    return np.where(lower, zl, zu)


def poisson_like(count, weight_fn, box=None, batch=400000):
    """rejection sampling of `count` points with acceptance = weight_fn(x, y) in [0,1]"""
    if count <= 0:
        return np.zeros(0), np.zeros(0)
    out_x, out_y = [], []
    got = 0; tries = 0
    while got < count and tries < 200:
        if box is None:
            x = rng.uniform(-SIZE / 2 + 10, SIZE / 2 - 10, batch); y = rng.uniform(-SIZE / 2 + 10, SIZE / 2 - 10, batch)
        else:
            cx, cy, r = box
            a = rng.uniform(0, 2 * math.pi, batch); rr = r * np.sqrt(rng.uniform(0, 1, batch))
            x = cx + np.cos(a) * rr; y = cy + np.sin(a) * rr
        w = weight_fn(x, y)
        k = rng.uniform(0, 1, batch) < w
        out_x.append(x[k]); out_y.append(y[k]); got += k.sum(); tries += 1
    if not out_x:
        return np.zeros(0), np.zeros(0)
    x = np.concatenate(out_x)[:count]; y = np.concatenate(out_y)[:count]
    return x, y


def save(name, x, y, z, yaw, scale, var):
    a = np.stack([x * 100, y * 100, z * 100, yaw, scale, var], 1).astype(np.float32)
    a.tofile(os.path.join(OUTD, name + '.f32'))
    print('%-10s %7d instances' % (name, len(a)))
    return len(a)


def noise(x, y, wl, seed, octaves=3):
    return D.fbm(x, y, wl, octaves, 0.5, seed=seed) * 0.5 + 0.5


info = {}
elev = lambda x, y: samp(Hc, x, y)
slp = lambda x, y: samp(slope, x, y)
M = lambda c: (lambda x, y: samp(mask[..., c], x, y))
Lt = lambda c: (lambda x, y: samp(light[..., c], x, y))
wet = lambda x, y: samp(lake.astype(np.float32), x, y)

# ---------------------------------------------------------------- pines
def w_pine(x, y):
    e = elev(x, y); s = slp(x, y)
    grove = np.clip((noise(x, y, 700.0, 31) - 0.66) * 25.0, 0, 1) * np.clip((noise(x, y, 90.0, 33, 2) - 0.25) * 4, 0, 1)   # dense plantations with glades
    ok = (e < 2250) & (s < 22) & (wet(x, y) < 0.01) & (Lt(3)(x, y) < 0.25) & (M(0)(x, y) < 0.3)
    return ok * grove * np.clip((2250 - e) / 120.0, 0, 1)
x, y = poisson_like(int(os.environ.get('N_PINE', 45000)), w_pine)
info['Pine'] = save('Pine', x, y, terrain_z(x, y) - 0.3, rng.uniform(0, 360, len(x)), rng.uniform(0.75, 1.25, len(x)), np.zeros(len(x)))

# ---------------------------------------------------------------- junipers
def w_jun(x, y):
    e = elev(x, y); r = M(0)(x, y)
    return ((e > 2000) & (e < 2900) & (wet(x, y) < 0.01)) * np.clip(1 - np.abs(r - 0.4) * 3, 0, 1) * np.clip((noise(x, y, 700.0, 41) - 0.45) * 4, 0, 1)
x, y = poisson_like(int(os.environ.get('N_JUN', 12000)), w_jun)
info['Juniper'] = save('Juniper', x, y, terrain_z(x, y) - 0.15, rng.uniform(0, 360, len(x)), rng.uniform(0.5, 1.1, len(x)), np.zeros(len(x)))

# ---------------------------------------------------------------- boulders (6 scan meshes, sizes by mask)
def w_rock(x, y):
    r = M(0)(x, y); sc = M(1)(x, y)
    m = np.maximum(r, sc * 0.8)
    field = np.clip((noise(x, y, 220.0, 61, 2) - 0.45) * 3.0, 0, 1)        # clustered boulder fields, not uniform dust
    return np.clip(m * m * 1.5 + m * field + 0.004, 0, 1) * (wet(x, y) < 0.01) * (1 - M(2)(x, y) * 0.7)
x, y = poisson_like(int(os.environ.get('N_ROCK', 260000)), w_rock)
strength = np.maximum(M(0)(x, y), M(1)(x, y))
scale = np.exp(rng.normal(0, 0.45, len(x))) * (0.6 + strength * 1.4)
var = rng.integers(0, 6, len(x)).astype(np.float32)
info['Rock'] = save('Rock', x, y, terrain_z(x, y), rng.uniform(0, 360, len(x)), scale, var)
# beach pebbles/stones on the Sevan shore band
def w_shore(x, y):
    s = Lt(3)(x, y)
    return np.clip((s - 0.35) * 3, 0, 1) * (wet(x, y) < 0.01)
x, y = poisson_like(int(os.environ.get('N_SHORE', 25000)), w_shore)
info['ShoreRock'] = save('ShoreRock', x, y, terrain_z(x, y), rng.uniform(0, 360, len(x)), np.exp(rng.normal(-1.2, 0.4, len(x))), rng.integers(0, 6, len(x)).astype(np.float32))

# ---------------------------------------------------------------- grass + flowers near the ground views
GR = float(os.environ.get('GRASS_RADIUS', 140.0))
gx_all, gy_all = [], []
for nm, c in cams.items():
    px, py, pz = [v / 100 for v in c['pos']]
    if pz - terrain_z(np.array([px]), np.array([py]))[0] > 30:
        continue
    tx, ty = c['tgt'][0] / 100, c['tgt'][1] / 100
    d = math.hypot(tx - px, ty - py)
    cx, cy = px + (tx - px) / d * GR * 0.6, py + (ty - py) / d * GR * 0.6   # centre the patch in front of the camera
    gx_all.append((cx, cy))
def w_grass(x, y):
    l = M(3)(x, y); r = M(0)(x, y); s = M(2)(x, y); sh = Lt(3)(x, y)
    return np.clip(0.35 + l * 0.65, 0, 1) * np.clip(1 - r * 1.6, 0, 1) * (1 - s) * np.clip(1 - sh * 2.2, 0, 1) * (wet(x, y) < 0.01)
area = math.pi * GR * GR
dens = float(os.environ.get('GRASS_DENSITY', 5.0))      # clumps per m^2 (before mask rejection)
xs, ys, vs, ss = [], [], [], []
for cx, cy in gx_all:
    x, y = poisson_like(int(area * dens * 0.6), w_grass, (cx, cy, GR))
    lush = M(3)(x, y)
    # variants: 0-3 dry emarshall, 4-7 green emarshall, 8-11 scan cards; mix by lushness
    green = rng.uniform(0, 1, len(x)) < lush * 0.55          # late-summer highlands: mostly dry grass even where lush
    v = np.where(green, 4 + rng.integers(0, 4, len(x)), rng.integers(0, 4, len(x)))
    v = np.where(rng.uniform(0, 1, len(x)) < 0.12, 11, v)   # scanned tuft (rostlinka_07c) for variety
    xs.append(x); ys.append(y); vs.append(v); ss.append(rng.uniform(0.7, 1.3, len(x)))
x = np.concatenate(xs); y = np.concatenate(ys)
info['Grass'] = save('Grass', x, y, terrain_z(x, y) - 0.03, rng.uniform(0, 360, len(x)), np.concatenate(ss), np.concatenate(vs).astype(np.float32))
fx, fy = [], []
for cx, cy in gx_all:
    def w_fl(x, y):
        return w_grass(x, y) * np.clip((noise(x, y, 60.0, 77, 2) - 0.55) * 5, 0, 1) * M(3)(x, y)
    x, y = poisson_like(int(area * 0.08), w_fl, (cx, cy, GR))
    fx.append(x); fy.append(y)
x = np.concatenate(fx); y = np.concatenate(fy)
kind = (noise(x, y, 400.0, 79, 2) > 0.5).astype(np.float32)             # poppy fields vs daisy patches
info['Flower'] = save('Flower', x, y, terrain_z(x, y) - 0.02, rng.uniform(0, 360, len(x)), rng.uniform(0.8, 1.2, len(x)), kind * 6 + rng.integers(0, 6, len(x)))
json.dump(info, open(os.path.join(OUTD, 'scatter_info.json'), 'w'), indent=1)

# ---------------------------------------------------------------- canopy map for the terrain (forest beyond the tree cull distance)
# R = pine canopy cover, G = juniper/shrub cover (0..1), 2048^2 over the core; terrain material fades it in with distance.
from PIL import Image as _I
def canopy(name, radius_m, res=2048):
    a = np.fromfile(os.path.join(OUTD, name + '.f32'), np.float32).reshape(-1, 6)
    px = (a[:, 0] / 100 / SIZE + 0.5) * (res - 1); py = (a[:, 1] / 100 / SIZE + 0.5) * (res - 1)
    h, _, _ = np.histogram2d(py, px, bins=res, range=[[0, res], [0, res]])
    cell = SIZE / res
    cover = h * math.pi * radius_m ** 2 / (cell * cell)            # crown area per cell area
    return np.clip(ndimage.gaussian_filter(cover, 1.0) * 5.0, 0, 1)   # seen from afar a stand reads as closed canopy (height + shadow)
cR = canopy('Pine', 2.6); cG = canopy('Juniper', 0.8)
_I.fromarray((np.stack([cR, cG, np.zeros_like(cR)], -1) * 255).astype(np.uint8)).save(os.path.join(G, 'tex', 'T_core_Canopy.png'))
print('canopy cover mean pine %.3f max %.2f' % (cR.mean(), cR.max()))
