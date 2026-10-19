# merge all big primitives of the scan into one primitive (world space), drop the tiny label box
import sys; sys.path.insert(0,sys.argv[1]); import glbio,numpy as np
j,b=glbio.load(sys.argv[2]); W=glbio.node_world(j)
Ps=[];Ns=[];Us=[];Is=[];off=0;img=None
for ni,n in enumerate(j['nodes']):
    if 'mesh' not in n: continue
    for p in j['meshes'][n['mesh']]['primitives']:
        pos=glbio.acc(j,b,p['attributes']['POSITION'])
        if len(pos)<1000: continue
        M=W[ni]; pw=(np.c_[pos,np.ones(len(pos))]@M.T)[:,:3]
        nr=glbio.acc(j,b,p['attributes']['NORMAL'])@np.linalg.inv(M[:3,:3])  # normal matrix (inverse transpose) applied as row vectors
        nr/=np.linalg.norm(nr,axis=1,keepdims=True)+1e-12
        uv=glbio.acc(j,b,p['attributes']['TEXCOORD_0'])
        idx=glbio.acc(j,b,p['indices']).ravel()
        Ps.append(pw);Ns.append(nr);Us.append(uv);Is.append(idx+off);off+=len(pos)
        ti=j['materials'][p['material']]['pbrMetallicRoughness']['baseColorTexture']['index']; img=glbio.image(j,b,j['textures'][ti]['source'])
P=np.concatenate(Ps).astype(np.float32);N=np.concatenate(Ns).astype(np.float32);U=np.concatenate(Us).astype(np.float32);I=np.concatenate(Is).astype(np.uint32)
print('merged v',len(P),'t',len(I)//3)
open(sys.argv[3]+'.albedo.jpg','wb').write(img[0])
glbio.write(sys.argv[3],[dict(POSITION=P,NORMAL=N,TEXCOORD_0=U,indices=I)])
