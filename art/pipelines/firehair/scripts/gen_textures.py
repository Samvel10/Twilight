"""python3 -P gen_textures.py <workdir with headpolys.npz + body_base.png> <outdir (deliver/assets)>
Procedural textures (no third-party content):
  T_FH_Noise.png      256x256 tileable fBm, R = low-frequency billows, G = finer turbulence, B = ridged (flame tongue erosion)
  T_FH_FireLUT.png    256x4 black-body-like ramp (deep red -> orange -> yellow -> white), linear values
  T_FH_BodyMask.png   1024 RGBA in the Spartan Body UV: R = ember glow (facial hair + scalp), G = iris (eyes like suns),
                      B = charcoal recolour (facial hair / scalp), A = scalp only
"""
import numpy as np, sys, os
from PIL import Image, ImageDraw, ImageFilter
W, O = sys.argv[1], sys.argv[2]; os.makedirs(O, exist_ok=True)
rng = np.random.default_rng(7)
def fbm(n, beta, seed):
    r = np.random.default_rng(seed); f = np.fft.fft2(r.standard_normal((n, n)))
    k = np.fft.fftfreq(n)[:, None]**2 + np.fft.fftfreq(n)[None, :]**2; k[0, 0] = 1
    x = np.real(np.fft.ifft2(f / k**(beta/2))); x -= x.min(); return x / x.max()
N = 256
a = fbm(N, 2.2, 1); b = fbm(N, 1.6, 2); c = 1 - np.abs(2*fbm(N, 2.0, 3) - 1)
def eq(x):  # histogram equalise -> uniform 0..1 (predictable thresholds in the material)
    o = np.argsort(x.ravel()); y = np.empty(x.size); y[o] = np.linspace(0, 1, x.size); return y.reshape(x.shape)
Image.fromarray((np.dstack([eq(a), eq(b), eq(c)])*255).astype(np.uint8)).save(O+'/T_FH_Noise.png')
# fire ramp (linear radiance-ish, normalised): t=0 black, .25 deep red, .5 orange, .75 yellow, 1 white-yellow
t = np.linspace(0, 1, 256)
keys = [(0, (0, 0, 0)), (.18, (.35, .02, 0)), (.38, (1, .16, .01)), (.6, (1, .45, .06)), (.8, (1, .78, .3)), (1, (1, .97, .85))]
lut = np.zeros((256, 3))
for i in range(3): lut[:, i] = np.interp(t, [k[0] for k in keys], [k[1][i] for k in keys])
Image.fromarray((np.repeat(lut[None], 4, 0)*255).astype(np.uint8)).save(O+'/T_FH_FireLUT.png')
# body mask
P = np.load(W+'/headpolys.npz'); uv, co = P['uv'], P['co']; S = 1024
def px(u): return [(x*S, (1-y)*S) for x, y in u]
cen = co.mean(1); cuv = uv.mean(1)*[S, -S]+[0, S]
strip = (cuv[:, 0] > 600) & (cuv[:, 0] < 800) & (cuv[:, 1] > 120) & (cuv[:, 1] < 240)
eyes = cuv[:, 1] > 700
def hairline(y): return np.interp(y, [-0.15, -0.07, 0.0, 0.06, 0.15], [2.045, 2.04, 2.0, 1.93, 1.875])
x, y, z = cen.T
scalp = np.clip((z - hairline(y) + 0.008)/0.03, 0, 1)
scalp[(np.abs(x) > 0.08) & (z < 2.0) & (y > -0.04) & (y < 0.07)] = 0   # ears
scalp[strip | eyes] = 0
def rast(vals, sel):
    I = Image.new('L', (S, S), 0); D = ImageDraw.Draw(I)
    for p, v in zip(uv[sel], vals[sel]): D.polygon(px(p), fill=int(255*v))
    return I
Istrip = rast(np.ones(len(uv)), strip).filter(ImageFilter.MaxFilter(3))
Iscalp = rast(scalp, scalp > 0).filter(ImageFilter.GaussianBlur(1.5))
base = np.array(Image.open(W+'/body_base.png').convert('RGB')).astype(float)
eyereg = np.array(rast(np.ones(len(uv)), eyes)) > 0
iris = eyereg & (base[..., 2] > base[..., 0] + 6) | eyereg & (base.sum(-1) < 150)
Iiris = Image.fromarray((iris*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(2))
st = np.array(Istrip)/255.; sc = np.array(Iscalp)/255.; ir = np.array(Iiris)/255.
# ember: facial hair strands glow where the painted hair is darker (strand detail survives), scalp glows evenly
lum = base.mean(-1)/255.
R = np.clip(st*(0.55 + 0.45*np.clip(1 - lum*1.6, 0, 1)) + sc, 0, 1)
B = np.clip(st + 0.75*sc, 0, 1)
G = np.clip(ir*1.3, 0, 1)
Image.fromarray((np.dstack([R, G, B, sc])*255).astype(np.uint8), 'RGBA').save(O+'/T_FH_BodyMask.png')
vis = base.copy(); vis[..., 0] = np.maximum(vis[..., 0], R*255); vis[..., 1] = np.maximum(vis[..., 1], G*255)
Image.fromarray(vis.astype(np.uint8)).save(W+'/mask_vis.png')
print('masks: strip px', int(st.sum()), 'scalp px', int((sc > .5).sum()), 'iris px', int((ir > .5).sum()))
