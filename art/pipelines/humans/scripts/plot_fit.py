import sys; sys.path.insert(0, sys.argv[1]); import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from gltf_io import *
dj, dB = rd(sys.argv[2]); tj, tB = rd(sys.argv[3]); out = sys.argv[4]; ts = float(sys.argv[5]); drop = sys.argv[6].split(',')
sk = dj['skins'][0]; par = parents(dj)
D = np.concatenate([acc(dj, dB, p['attributes']['POSITION']) for p in dj['meshes'][0]['primitives']])
Jw = {dj['nodes'][k]['name']: world(dj, k, par)[:3, 3] for k in sk['joints']}
T = np.concatenate([q['X'] for q in flatten_static(tj, tB, drop)]) * ts
print('donor extent', D.min(0), D.max(0)); print('target extent', T.min(0), T.max(0))
fig, ax = plt.subplots(1, 4, figsize=(24, 9))
for a, (P_, i, k, t) in zip(ax, ((D, 0, 1, 'donor front XY'), (D, 2, 1, 'donor side ZY'), (T, 0, 1, 'target front XY'), (T, 2, 1, 'target side ZY'))):
    s = P_[::max(1, len(P_)//40000)]; a.scatter(s[:, i], s[:, k], s=0.2, c='k'); a.set_aspect('equal'); a.set_title(t); a.grid(True)
    for nm in ('pelvis', 'thigh_l', 'calf_l', 'foot_l', 'spine_05', 'neck_01', 'head', 'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_r', 'hand_r'):
        if nm in Jw: p = Jw[nm]; ax[0 if i == 0 else 1].plot(p[i], p[k], 'ro', ms=4); ax[0 if i == 0 else 1].annotate(nm, (p[i], p[k]), fontsize=7, color='r')
    a.set_ylim(-0.05, 1.95)
plt.tight_layout(); plt.savefig(out, dpi=60); print({k: np.round(v, 3).tolist() for k, v in Jw.items() if k in ('pelvis', 'upperarm_l', 'lowerarm_l', 'hand_l', 'head', 'foot_l')})
