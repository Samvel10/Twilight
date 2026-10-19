"""Crowd variant of a baked character GLB: ONE section, ONE material, decimated, skin weights kept.
 - each slot's base colour is pre-graded with the same maths as M_Human (recolours, saturation, tint, brightness, metal tint;
   parameters from mat_spec.SPEC[Char]) and packed into a colour atlas; normals and an MR atlas (G=roughness, B=metal) likewise
 - all primitives merged, UVs remapped into the atlas cells, then quadric-decimated (fast_simplification) to --tris
usage: python3 -P glb_crowd.py in.glb out.glb Char [--tris 14000] [--atlas 2048] [--drop New_eye,Full_figure]"""
import sys, os, io, json, struct, argparse, math
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, '..', 'pylib'))
import numpy as np
from PIL import Image
from gltf_io import rd, acc
import mat_spec
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('char')
ap.add_argument('--tris', type=int, default=14000); ap.add_argument('--atlas', type=int, default=2048); ap.add_argument('--drop', default='')
a = ap.parse_args()
j, B = rd(a.src); spec = mat_spec.SPEC.get(a.char, {})
drop = [d for d in a.drop.split(',') if d]
def img(ti):
    if ti is None: return None
    im = j['images'][j['textures'][ti]['source']]; v = j['bufferViews'][im['bufferView']]; o = v.get('byteOffset', 0)
    return Image.open(io.BytesIO(bytes(B[o:o + v['byteLength']]))).convert('RGB')
def s2l(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def l2s(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
W = np.array([0.3, 0.59, 0.11])
def grade(rgb, mr, sp, mf):
    s = dict(sp.get('s', {})); v = dict(sp.get('v', {})); col = s2l(rgb)
    for k in ('1', '2'):
        amt = s.get('Recolor%sAmount' % k, 0.0)
        if amt <= 0: continue
        lum = (col @ W)[..., None]; ch = col - lum; src = np.array(v.get('Recolor%sSrc' % k, (0, 0, 1))); srcc = src - src @ W + 1e-4; srcc /= np.linalg.norm(srcc)
        cosang = ((ch + 1e-4) / np.linalg.norm(ch + 1e-4, axis=-1, keepdims=True)) @ srcc
        wd = s.get('Recolor%sWidth' % k, 0.8); w = np.clip((cosang - wd) / (1.0001 - wd), 0, 1)
        w = w * np.clip((ch * ch).sum(-1) * s.get('Recolor%sSens' % k, 300.0), 0, 1) * amt
        dst = np.array(v.get('Recolor%sDst' % k, (0.5, 0.5, 0.5))); kl = s.get('Recolor%sKeepLum' % k, 1.0)
        newc = dst * (1 - kl) + dst * (lum / max(dst @ W, 0.02)) * kl
        col = col * (1 - w[..., None]) + newc * w[..., None]
    lum = (col @ W)[..., None]; sat = s.get('Saturation', 1.0); col = lum + (col - lum) * sat
    col = col * np.array(v.get('Tint', (1, 1, 1))) * s.get('Brightness', 1.0)
    metal = np.clip(np.maximum(mr[..., 2] * s.get('MetalMask', mf), s.get('ForceMetal', 0.0)), 0, 1)
    mt = np.clip((col @ W) * 1.6, 0, 1)[..., None] * np.array(v.get('MetalTint', (0.83, 0.52, 0.26)))
    col = col + (mt - col) * (metal * s.get('MetalTintAmount', 0.0))[..., None]
    rough = np.clip(mr[..., 1] * s.get('Roughness', 0.6), 0, 1); rough = rough + (s.get('MetalRoughness', 0.35) - rough) * metal
    return l2s(col), rough, metal
prims = [p for p in j['meshes'][0]['primitives'] if not any(d in j['materials'][p['material']].get('name', '') for d in drop)]
n = len(prims); g = math.ceil(math.sqrt(n)); cell = a.atlas // g; pad = 6
AC = np.zeros((a.atlas, a.atlas, 3), np.float32); AN = np.tile(np.array([0.5, 0.5, 1.0], np.float32), (a.atlas, a.atlas, 1)); AM = np.zeros((a.atlas, a.atlas, 3), np.float32); AM[..., 0] = 1
Xs, Ns, UVs, Js, Ws, Is = [], [], [], [], [], []; base = 0
for i, p in enumerate(prims):
    m = j['materials'][p['material']]; name = m.get('name', ''); pb = m.get('pbrMetallicRoughness', {})
    sz = cell - 2 * pad
    bc = img(pb.get('baseColorTexture', {}).get('index')); bcf = np.array(pb.get('baseColorFactor', [1, 1, 1, 1])[:3])
    rgb = (np.asarray(bc.resize((sz, sz), Image.LANCZOS), np.float32) / 255 if bc else np.ones((sz, sz, 3), np.float32)) * bcf
    mrt = img(pb.get('metallicRoughnessTexture', {}).get('index'))
    mr = np.asarray(mrt.resize((sz, sz), Image.BILINEAR), np.float32) / 255 if mrt else np.ones((sz, sz, 3), np.float32)
    mf = pb.get('metallicFactor', 1.0)
    sp = spec.get(name, {}); col, rough, metal = grade(rgb, mr, sp, mf)
    nt = img(m.get('normalTexture', {}).get('index'))
    nrm = np.asarray(nt.resize((sz, sz), Image.BILINEAR), np.float32) / 255 if nt else np.tile(np.array([0.5, 0.5, 1.0], np.float32), (sz, sz, 1))
    cx, cy = (i % g) * cell, (i // g) * cell
    for A_, data in ((AC, col), (AN, nrm), (AM, np.stack([np.ones_like(rough), rough, metal], -1))):
        A_[cy:cy + cell, cx:cx + cell] = np.pad(data, ((pad, pad), (pad, pad), (0, 0)), mode='edge')
    at = p['attributes']; uv = acc(j, B, at['TEXCOORD_0']).astype(np.float64)
    uv = np.clip(uv, 0, 1); uv = np.stack([(cx + pad + uv[:, 0] * sz) / a.atlas, (cy + pad + uv[:, 1] * sz) / a.atlas], 1)
    X = acc(j, B, at['POSITION']); Xs.append(X); Ns.append(acc(j, B, at['NORMAL']) if 'NORMAL' in at else np.tile([0, 1, 0], (len(X), 1)))
    UVs.append(uv); Js.append(acc(j, B, at['JOINTS_0']).astype(np.uint16)); Ws.append(acc(j, B, at['WEIGHTS_0']).astype(np.float32))
    Is.append(acc(j, B, p['indices']).reshape(-1).astype(np.int64) + base); base += len(X)
    print('cell %d %-26s grade=%s' % (i, name, 'yes' if sp else 'none'))
X = np.concatenate(Xs).astype(np.float32); Nn = np.concatenate(Ns); UV = np.concatenate(UVs); J = np.concatenate(Js); Wt = np.concatenate(Ws); F = np.concatenate(Is).reshape(-1, 3)
import fast_simplification as fs
red = max(0.0, 1.0 - a.tris / len(F))
if red > 0:
    _, _, col_ = fs.simplify(X, F, target_reduction=red, return_collapses=True)
    X2, F2, imap = fs.replay_simplification(X, F, col_)
    rep = np.zeros(len(X2), np.int64); rep[imap[::-1]] = np.arange(len(imap))[::-1]
    X, F = X2.astype(np.float32), F2; Nn, UV, J, Wt = Nn[rep], UV[rep], J[rep], Wt[rep]
print('tris %d -> %d, verts %d' % (base and len(np.concatenate(Is)) // 3, len(F), len(X)))
# ---- write: keep nodes/skins, replace mesh/materials/textures/images
out = dict(j); BIN = bytearray(); out['bufferViews'] = []; out['accessors'] = []
def view(d, t=None):
    while len(BIN) % 4: BIN.append(0)
    o = len(BIN); BIN.extend(d); v = {'buffer': 0, 'byteOffset': o, 'byteLength': len(d)}
    if t: v['target'] = t
    out['bufferViews'].append(v); return len(out['bufferViews']) - 1
def accw(arr, ct, typ, t=None, mm=False):
    arr = np.ascontiguousarray(arr); A = {'bufferView': view(arr.tobytes(), t), 'componentType': ct, 'count': int(arr.shape[0]), 'type': typ}
    if mm: A['min'] = [float(x) for x in arr.min(0)]; A['max'] = [float(x) for x in arr.max(0)]
    out['accessors'].append(A); return len(out['accessors']) - 1
# skins: re-emit inverse bind matrices
for s in out['skins']:
    ibm = acc(j, B, s['inverseBindMatrices']).astype(np.float32); s['inverseBindMatrices'] = accw(ibm, 5126, 'MAT4')
def png(arr):
    bio = io.BytesIO(); Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8)).save(bio, 'PNG', optimize=True); return bio.getvalue()
out['images'] = [{'bufferView': view(png(AC)), 'mimeType': 'image/png', 'name': 'T_%s_Crowd_D' % a.char},
                 {'bufferView': view(png(AN)), 'mimeType': 'image/png', 'name': 'T_%s_Crowd_N' % a.char},
                 {'bufferView': view(png(AM)), 'mimeType': 'image/png', 'name': 'T_%s_Crowd_MR' % a.char}]
out['samplers'] = [{}]; out['textures'] = [{'source': i, 'sampler': 0} for i in range(3)]
out['materials'] = [{'name': 'Crowd', 'pbrMetallicRoughness': {'baseColorTexture': {'index': 0}, 'metallicRoughnessTexture': {'index': 2}}, 'normalTexture': {'index': 1}}]
Nn = (Nn / np.maximum(np.linalg.norm(Nn, axis=1, keepdims=True), 1e-9)).astype(np.float32)
Wt = Wt / np.maximum(Wt.sum(1, keepdims=True), 1e-9)
out['meshes'] = [{'name': j['meshes'][0].get('name', 'SK'), 'primitives': [{'attributes': {
    'POSITION': accw(X, 5126, 'VEC3', 34962, True), 'NORMAL': accw(Nn, 5126, 'VEC3', 34962), 'TEXCOORD_0': accw(UV.astype(np.float32), 5126, 'VEC2', 34962),
    'JOINTS_0': accw(J, 5123, 'VEC4', 34962), 'WEIGHTS_0': accw(Wt.astype(np.float32), 5126, 'VEC4', 34962)},
    'indices': accw(F.reshape(-1, 1).astype(np.uint32), 5125, 'SCALAR', 34963), 'material': 0}]}]
while len(BIN) % 4: BIN.append(0)
out['buffers'] = [{'byteLength': len(BIN)}]
js = json.dumps(out, separators=(',', ':')).encode(); js += b' ' * ((4 - len(js) % 4) % 4)
open(a.dst, 'wb').write(b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(BIN)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(BIN)) + b'BIN\0' + bytes(BIN))
Image.fromarray((np.clip(AC, 0, 1) * 255).astype(np.uint8)).resize((512, 512)).save(a.dst.replace('.glb', '_atlas_preview.png'))
print('wrote', a.dst, os.path.getsize(a.dst))
