import sys; sys.path.insert(0,sys.argv[1]); import glbio,numpy as np,io
from PIL import Image
f=sys.argv[2]; out=sys.argv[3]; x0=float(sys.argv[4]); x1=float(sys.argv[5])
j,b=glbio.load(f); W=glbio.node_world(j)
imgs={};P=[];C=[]
for ni,n in enumerate(j['nodes']):
    if 'mesh' not in n: continue
    for p in j['meshes'][n['mesh']]['primitives']:
        pos=glbio.acc(j,b,p['attributes']['POSITION'])
        if len(pos)<100: continue
        pw=(np.c_[pos,np.ones(len(pos))]@W[ni].T)[:,:3]
        uv=glbio.acc(j,b,p['attributes']['TEXCOORD_0'])
        ti=j['materials'][p['material']]['pbrMetallicRoughness']['baseColorTexture']['index']; ii=j['textures'][ti]['source']
        if ii not in imgs: imgs[ii]=np.asarray(Image.open(io.BytesIO(glbio.image(j,b,ii)[0])).convert('RGB'))
        T=imgs[ii]; h,w,_=T.shape
        u=(np.mod(uv[:,0],1)*(w-1)).astype(int); v=(np.mod(uv[:,1],1)*(h-1)).astype(int)
        m=(pw[:,0]>=x0)&(pw[:,0]<=x1); P.append(pw[m]); C.append(T[v,u][m])
P=np.concatenate(P); C=np.concatenate(C); lo=P.min(0); hi=P.max(0)
rows=[]
for a,bx,dd,sg in ((0,1,2,1),(0,2,1,-1),(2,1,0,1)):
    sc=780/(hi[0]-lo[0]); Wd=int((hi[a]-lo[a])*sc)+20; H=int((hi[bx]-lo[bx])*sc)+20
    img=np.zeros((H,800,3),np.uint8)+30
    x=((P[:,a]-lo[a])*sc+10).astype(int); y=(H-1-((P[:,bx]-lo[bx])*sc+10)).astype(int)
    o=np.argsort(sg*P[:,dd]); img[np.clip(y[o],0,H-1),np.clip(x[o],0,799)]=C[o]
    rows.append(img)
S=np.concatenate(rows,0); Image.fromarray(S).save(out,quality=90)
