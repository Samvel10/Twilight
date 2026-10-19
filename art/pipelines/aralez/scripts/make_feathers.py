"""Procedural feather atlas (original work, CC0). 4 vertical cells of 512x1024 (u: 0-.25 primary, .25-.5 secondary,
.5-.75 covert, .75-1 small contour feather). Rachis along v (base v=0 at the BOTTOM row of the image = glTF v=1? we
write the base at the image bottom, tip at the top). Outputs T_Feather_BC.png (sRGB colour + alpha), T_Feather_N.png
(tangent-space normal, +Y = towards the tip), T_Feather_RT.png (R = roughness, G = translucency/thickness, B = barbs AO).
usage: python3 -I make_feathers.py outdir [seed]"""
import numpy as np, sys, os
from PIL import Image
out = sys.argv[1]; rng = np.random.default_rng(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
W, H = 512, 1024
def noise1(n, octaves=4, scale=8):
    x = np.linspace(0, 1, n); r = np.zeros(n)
    for o in range(octaves):
        f = scale * 2 ** o; p = rng.random(int(f) + 2)
        r += np.interp(x * f, np.arange(len(p)), p) / 2 ** o
    return r / r.max()
def noise2(h, w, sc=8, octaves=4):
    r = np.zeros((h, w))
    for o in range(octaves):
        f = sc * 2 ** o; g = rng.random((int(f * h / w) + 3, int(f) + 3))
        yy = np.linspace(0, g.shape[0] - 2.001, h); xx = np.linspace(0, g.shape[1] - 2.001, w)
        y0 = yy.astype(int); x0 = xx.astype(int); fy = (yy - y0)[:, None]; fx = (xx - x0)[None, :]
        a = g[y0][:, x0]; b = g[y0][:, x0 + 1]; c = g[y0 + 1][:, x0]; d = g[y0 + 1][:, x0 + 1]
        r += (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy) / 2 ** o
    return (r - r.min()) / (r.max() - r.min())

def feather(kind):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    t = 1.0 - yy / (H - 1)                  # 0 at base (bottom) .. 1 tip (top)
    s = (xx - W / 2) / (W / 2)              # -1..1 across the cell, rachis at 0
    P = dict(primary=dict(L0=.03, L1=.985, wmax=.62, lead=.32, c=.74, pointed=1, curve=.05, bar=1, ang=36, base=.10),
             secondary=dict(L0=.03, L1=.975, wmax=.86, lead=.55, c=.80, pointed=0, curve=.025, bar=1, ang=40, base=.10),
             covert=dict(L0=.03, L1=.96, wmax=.90, lead=.80, c=.58, pointed=0, curve=.015, bar=0, ang=48, base=.14),
             contour=dict(L0=.02, L1=.94, wmax=.90, lead=1.0, c=.45, pointed=0, curve=0, bar=0, ang=55, base=.22))[kind]
    tc = np.clip((t - P['L0']) / (P['L1'] - P['L0']), 0, 1)
    ramp = np.clip(tc / P['base'], 0, 1); ramp = ramp * ramp * (3 - 2 * ramp)
    u = np.clip((tc - P['c']) / (1 - P['c']), 0, 1)
    tip = np.clip(1 - u ** 1.6, 0, 1) ** 0.7 if P['pointed'] else np.sqrt(np.clip(1 - u * u, 0, 1))
    prof = ramp * tip * (0.35 + 0.65 * ramp)
    sx = s - P['curve'] * np.sin(np.pi * tc)
    hw = P['wmax'] * prof * np.where(sx < 0, P['lead'], 1.0)
    vane = np.abs(sx) / np.maximum(hw, 1e-4)
    inside_len = (t > P['L0']) & (t < P['L1'])
    lam = 6.5
    phase = (t * H - np.abs(sx) * (W / 2) / np.tan(np.radians(P['ang']))) / lam
    fr = np.mod(phase, 1.0); barb = 0.5 + 0.5 * np.cos(fr * 2 * np.pi)
    rnd = rng.random(20000); bid = (np.floor(phase).astype(int) + (sx < 0) * 7919) % 20000
    split = ((rnd[bid] > 0.94) & (fr < 0.45)) * np.clip((vane - .45) / .25, 0, 1)
    shade = 0.88 + 0.24 * rng.random(20000)[bid]       # per-barb brightness jitter
    edge_noise = (noise2(H, W, 12, 3) - .5) * 0.10
    alpha = np.clip((1.0 - vane + edge_noise) / 0.05, 0, 1) * inside_len
    if kind == 'contour':
        fluff = np.clip((0.4 - tc) / 0.4, 0, 1)
        alpha *= np.clip(1 - fluff * (1 - barb) * 1.4, 0, 1)
    alpha *= (1 - split)
    rach_w = 0.014 * (1 - tc * .75) + 0.003
    rach = np.clip(1 - np.abs(sx) / rach_w, 0, 1) * (t < P['L1'] - .01)
    alpha = np.maximum(alpha, (rach > 0.05) * 1.0)
    base = np.array([0.94, 0.90, 0.82]); gold = np.array([0.82, 0.63, 0.36]); dark = np.array([0.45, 0.33, 0.22])
    tipw = np.clip((tc - 0.35) / 0.65, 0, 1) ** 1.3 * (0.95 if P['bar'] else 0.45)
    col = base[None, None, :] * (1 - tipw[..., None]) + gold[None, None, :] * tipw[..., None]
    if P['bar']:
        bars = 0.5 + 0.5 * np.sin(tc * 2 * np.pi * 6 + np.abs(sx) * 2.5 + noise2(H, W, 6, 3) * 2.0)
        bars = np.clip((bars - 0.58) / 0.22, 0, 1) * np.clip((tc - .15) / .3, 0, 1) * 0.42
        col = col * (1 - bars[..., None]) + dark[None, None, :] * bars[..., None]
    mott = noise2(H, W, 16, 4)
    col *= (0.9 + 0.14 * mott[..., None]) * (shade * (0.74 + 0.26 * barb))[..., None]
    col *= (1 - 0.10 * np.clip(1 - vane, 0, 1) - 0.16 * np.clip((vane - 0.75) / 0.25, 0, 1))[..., None]
    col = col * (1 - rach[..., None] * 0.7) + np.array([0.98, 0.96, 0.92])[None, None, :] * rach[..., None] * 0.7
    hgt = barb * 0.5 * (1 - rach) + rach * 1.5 - split * .3
    hgt = hgt * (alpha > 0)
    gy, gx = np.gradient(hgt)
    k = 2.6; nx = -gx * k; ny = gy * k; nz = np.ones_like(nx)
    n = np.stack([nx, ny, nz], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rough = 0.6 + 0.15 * (1 - barb) - 0.25 * rach
    thick = np.clip(0.3 + 0.7 * vane, 0, 1) * (1 - rach) * 0.85 + rach * 0.05
    ao = 0.82 + 0.18 * barb
    return col, alpha, n, rough, thick, ao

cells = ['primary', 'secondary', 'covert', 'contour']
BC = np.zeros((H, W * 4, 4)); N = np.zeros((H, W * 4, 3)); RT = np.zeros((H, W * 4, 3))
for i, k in enumerate(cells):
    col, a, n, r, th, ao = feather(k)
    BC[:, i * W:(i + 1) * W, :3] = col; BC[:, i * W:(i + 1) * W, 3] = a
    N[:, i * W:(i + 1) * W] = n; RT[:, i * W:(i + 1) * W] = np.stack([r, th, ao], -1)
# dilate colour under transparent texels (avoid dark fringes with mips)
m = BC[..., 3] > 0.5
avg = BC[..., :3][m].mean(0); BC[..., :3][~m] = avg
os.makedirs(out, exist_ok=True)
srgb = lambda x: np.clip(x, 0, 1) ** (1 / 2.2)
Image.fromarray((np.dstack([srgb(BC[..., :3]), BC[..., 3]]) * 255).astype(np.uint8), 'RGBA').save(out + '/T_Feather_BC.png')
Image.fromarray(((N * 0.5 + 0.5) * 255).astype(np.uint8)).save(out + '/T_Feather_N.png')
Image.fromarray((np.clip(RT, 0, 1) * 255).astype(np.uint8)).save(out + '/T_Feather_RT.png')
prev = Image.new('RGB', (W * 4, H), (40, 60, 90)); im = Image.open(out + '/T_Feather_BC.png'); prev.paste(im, (0, 0), im); prev.save(out + '/preview.jpg')
print('ok')
