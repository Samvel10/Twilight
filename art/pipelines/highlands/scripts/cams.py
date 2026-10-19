# cams.py - test camera views placed on the real terrain (python3 -P cams.py <gen>) -> gen/cams.json (UE cm)
import sys, os, math, json
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dem_build as D

G = sys.argv[1]
H = {r: np.load(os.path.join(G, r + '_H.npy')).astype(np.float64) - np.load(os.path.join(G, r + '_drop.npy')) for r in D.REGIONS}


def h(x, y):
    """terrain world height (m above lake level, curvature applied) at x east, y south (m)"""
    for r in ('core', 'mid', 'far'):
        size = D.REGIONS[r][0]
        if abs(x) <= size / 2 and abs(y) <= size / 2:
            A = H[r]; n = A.shape[0]
            v = ndimage.map_coordinates(A, [[(y / size + 0.5) * (n - 1)], [(x / size + 0.5) * (n - 1)]], order=1)[0]
            return max(v, D.LAKE_LEVEL) - D.LAKE_LEVEL if r != 'far' else v - D.LAKE_LEVEL
    return 0.0


def ll(lon, lat):
    return (lon - D.C_LON) * D.M_PER_DEG_LON, -(lat - D.C_LAT) * D.M_PER_DEG_LAT


def cam(name, x, y, agl, yaw_deg=None, pitch=-5.0, target=None, fov=75.0, tgt_agl=0.0):
    z = h(x, y) + agl
    if target is not None:
        tx, ty = target
        tz = h(tx, ty) + tgt_agl
    else:
        a = math.radians(yaw_deg)
        d = 5000.0
        tx, ty = x + math.cos(a) * d, y + math.sin(a) * d
        tz = z + math.tan(math.radians(pitch)) * d
    return name, {'pos': [x * 100, y * 100, z * 100], 'tgt': [tx * 100, ty * 100, tz * 100], 'fov': fov}


az = lambda deg_from_north: deg_from_north - 90.0     # compass azimuth -> UE yaw (X east, Y south)
masis = ll(44.2983, 39.7019)
azhd = ll(44.9500, 40.2236)
if os.environ.get('HL_SITE') == 'ararat':
  V = dict([   # Aralez: Ara's field on the Ararat plain, Masis to the south
    cam('field2', 0, 0, 2.0, az(180), -1, fov=70),
    cam('field60', 0, 0, 60, target=masis, fov=60, tgt_agl=-1500),
  ])
elif os.environ.get('HL_SITE') == 'van':
  V = dict([   # Hayk: valley on the east shore of Lake Van, a hill for Bel
    cam('van300', 8000, 0, 300, az(268), -6, fov=75),
    cam('hayk_plain', 9000, 3000, 1.8, az(110), -1, fov=70),
    cam('bel_hill', 7000, -8000, 40, target=(11906, -13331), fov=55, tgt_agl=-40),
    cam('van_over', 14000, 5000, 1500, az(265), -12, fov=75),
  ])
else:
 V = dict([
    cam('lake300', 9000, -2000, 300, az(60), -7, fov=75),
    cam('masis', *ll(44.952, 40.214), 250, target=masis, fov=35, tgt_agl=-1500),
    cam('valley100', *ll(45.035, 40.215), 100, az(265), -4, fov=75),
    cam('meadow', 3000, -3000, 1.7, az(80), -2, fov=70),
    cam('shore', 10200, -4500, 2.0, az(35), -1, fov=70),
    cam('over1500', -4000, 9000, 1500, az(40), -14, fov=75),
    cam('sunward', 6000, 2000, 250, az(255), -3, fov=75),
    cam('azhdahak', 0, 6000, 400, target=azhd, fov=60, tgt_agl=-200),
 ])
# grove views: densest pine plantation cell from the scatter output (if present)
pf = os.path.join(G, 'scatter', 'Pine.f32')
if os.path.exists(pf) and os.path.getsize(pf) > 0 and not os.environ.get('HL_SITE'):
    a = np.fromfile(pf, np.float32).reshape(-1, 6); px, py = a[:, 0] / 100, a[:, 1] / 100
    hh, xe, ye = np.histogram2d(px, py, bins=60, range=[[-15000, 15000], [-15000, 15000]])
    i, j = np.unravel_index(hh.argmax(), hh.shape); gx, gy = (xe[i] + xe[i + 1]) / 2, (ye[j] + ye[j + 1]) / 2
    V['grove'] = cam('grove', gx + 700, gy + 150, 120, target=(gx, gy), fov=60, tgt_agl=5)[1]
    V['grove_lit'] = cam('grove_lit', gx - 650, gy - 200, 90, target=(gx, gy), fov=60, tgt_agl=5)[1]
for k, v in V.items():
    print(k, [round(c / 100) for c in v['pos']], 'ground %.0f m' % h(v['pos'][0] / 100, v['pos'][1] / 100))
json.dump(V, open(os.path.join(G, 'cams.json'), 'w'), indent=1)
