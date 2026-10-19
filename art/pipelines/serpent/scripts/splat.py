# quick point-splat preview of a glb: top (XZ? we pick axes) and side views, colored by texture
import sys; sys.path.insert(0,sys.argv[1]); import glbio,numpy as np,io
from PIL import Image
f=sys.argv[2]; out=sys.argv[3]
j,b=glbio.load(f); W=glbio.node_world(j)
imgs={}
P=[];C=[]
for ni,n in enumerate(j['nodes']):
    if 'mesh' not in n: continue
    for p in j['meshes'][n['mesh']]['primitives']:
        pos=glbio.acc(j,b,p['attributes']['POSITION'])
        if len(pos)<100: continue
        pw=(np.c_[pos,np.ones(len(pos))]@W[ni].T)[:,:3]
        uv=glbio.acc(j,b,p['attributes']['TEXCOORD_0'])
        ti=j['materials'][p['material']]['pbrMetallicRoughness']['baseColorTexture']['index']
        ii=j['textures'][ti]['source']
        if ii not in imgs: imgs[ii]=np.asarray(Image.open(io.BytesIO(glbio.image(j,b,ii)[0])).convert('RGB'))
        T=imgs[ii]; h,w,_=T.shape
        u=(np.mod(uv[:,0],1)*(w-1)).astype(int); v=(np.mod(uv[:,1],1)*(h-1)).astype(int)
        P.append(pw); C.append(T[v,u])
P=np.concatenate(P); C=np.concatenate(C)
lo=P.min(0); hi=P.max(0); print('bounds',lo,hi,'n',len(P))
views=[(0,1,2,'top(XY,depth Z)'),(0,2,1,'side(XZ,depth Y)'),(0,2,-1,'side2')]
W_=1600
rows=[]
for a,bx,d,name in views:
    dd=abs(d) if d!=-1 else 1
    sgn=1 if d!=-1 else -1
    sc=(W_-20)/(hi[0]-lo[0]); H=int((hi[bx]-lo[bx])*sc)+20
    img=np.zeros((H,W_,3),np.uint8)+30
    x=((P[:,a]-lo[a])*sc+10).astype(int); y=(H-1-((P[:,bx]-lo[bx])*sc+10)).astype(int)
    order=np.argsort(sgn*P[:,dd])  # draw far first -> near last
    for k in (0,1):
        img[np.clip(y[order]+k,0,H-1),np.clip(x[order],0,W_-1)]=C[order]
        img[np.clip(y[order],0,H-1),np.clip(x[order]+k,0,W_-1)]=C[order]
    rows.append(img)
H=sum(r.shape[0] for r in rows); S=np.zeros((H,W_,3),np.uint8); o=0
for r in rows: S[o:o+r.shape[0]]=r; o+=r.shape[0]
Image.fromarray(S).save(out,quality=88)
