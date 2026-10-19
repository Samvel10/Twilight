# Step 4: build the skinned GLB: Head (root, at the neck pivot, origin) -> Spine_01..Spine_NN along -X; Jaw under Head.
# glTF frame: +X towards the snout, +Y up. Units metres.
import sys,os; sys.path.insert(0,os.path.dirname(__file__)); import glbio,numpy as np
m=np.load(sys.argv[1]); out=sys.argv[2]; NB=int(os.environ.get('NBONES','48'))
P,N,UV,I,T=m['P'],m['N'],m['UV'],m['I'],m['T']
L=-P[:,0].min(); sp=L/NB
print('tail length behind neck %.3f m, spacing %.3f'%(L,sp))
names=['Head','Jaw']+['Spine_%02d'%k for k in range(1,NB+1)]
HK=float(m['headlen'])/0.426 if 'headlen' in m else 1.0   # jaw constants measured on the 0.426 m head
JAW=np.array([0.10,-0.012,0.0])*HK
pos=[np.zeros(3),JAW]+[np.array([-k*sp,0,0]) for k in range(1,NB+1)]
parent=[-1,0,0]+[k+1 for k in range(1,NB)]   # Spine_01 parent Head(0); Spine_k parent Spine_{k-1} (index k+1)
J=np.zeros((len(P),4),np.uint16); Wt=np.zeros((len(P),4),np.float32)
x,y=P[:,0],P[:,1]
t=np.clip(-x/sp,0,NB)               # chain parameter: 0 = Head, k = Spine_k
k0=np.floor(t).astype(int); f=t-k0; k1=np.minimum(k0+1,NB)
f=f*f*(3-2*f)                       # smoothstep between neighbouring bones
idx=lambda k: np.where(k==0,0,k+1)  # chain index -> joint index
J[:,0]=idx(k0); J[:,1]=idx(k1); Wt[:,0]=1-f; Wt[:,1]=f
# jaw: below the mouth line, in front of the hinge
xh,yh=x/HK,y/HK
line=-0.03-0.06*(xh-0.12)
jx=np.clip((xh-0.07)/0.06,0,1); jy=np.clip((line-yh)/0.012,0,1); jw=(jx*jx*(3-2*jx))*(jy*jy*(3-2*jy))
head=x>0
J[head,0]=0; J[head,1]=1; Wt[head,0]=1-jw[head]; Wt[head,1]=jw[head]
print('jaw verts',int((jw>0.5).sum()))
Wt/=Wt.sum(1,keepdims=True)
# ---- UV1: body-aligned scale coordinates (U along the body in scale lengths, V around: ROWS rows over the girth)
ROWS=int(os.environ.get('ROWS','24')); PER_TILE=8; ELONG=float(os.environ.get('SCALE_ELONG','1.35'))
sb=-x                                  # distance behind the neck pivot (head < 0)
r=np.sqrt(P[:,1]**2+P[:,2]**2)
bs=0.02; e0=sb.min(); nb=int((sb.max()-e0)/bs)+2; bi=((sb-e0)/bs).astype(int)
rs=np.array([np.percentile(r[bi==b_],80) if (bi==b_).sum()>3 else np.nan for b_ in range(nb)])
ok=~np.isnan(rs); rs=np.interp(np.arange(nb),np.nonzero(ok)[0],rs[ok])
k_=np.exp(-0.5*(np.arange(-15,16)/5.0)**2); k_/=k_.sum(); rs=np.convolve(np.r_[np.full(15,rs[0]),rs,np.full(15,rs[-1])],k_,'valid')
rs=np.maximum(rs,0.004)
scale_len=2*np.pi*rs/ROWS*ELONG        # one scale along the body
ucum=np.r_[0,np.cumsum(bs/scale_len[:-1])]; ucum-=np.interp(0.0,e0+np.arange(nb)*bs,ucum)   # U=0 at the neck pivot
U1=np.interp(sb,e0+np.arange(nb)*bs,ucum)/PER_TILE
th=np.arctan2(P[:,2],P[:,1])            # 0 on the back, +-pi on the belly
V1=(th/(2*np.pi)+0.5)*ROWS/PER_TILE
# vertex colour: R = body detail mask (0 on the head, fades in over the neck), G = belly mask
bodym=np.clip((sb-0.02)/0.10,0,1)
# UV1 tangent frame expressed in the UV0 tangent frame (the mesh only carries UV0 tangents):
# G,B = cos/sin of the rotation from UV0 tangent to UV1 tangent, A = 1 if the UV1 frame is mirrored.
Nn=N/np.linalg.norm(N,axis=1,keepdims=True); T0=T[:,:3]; B0=np.cross(Nn,T0)*T[:,3:4]
def proj(a): a=a-Nn*np.einsum('ij,ij->i',a,Nn)[:,None]; return a/(np.linalg.norm(a,axis=1,keepdims=True)+1e-9)
rr=np.maximum(r,1e-6)
T1=proj(np.tile(np.array([-1.0,0,0]),(len(P),1)))
B1=proj(np.stack([np.zeros_like(rr),-P[:,2]/rr,P[:,1]/rr],1))
c_=np.einsum('ij,ij->i',T1,T0); s_=np.einsum('ij,ij->i',T1,B0)
b1x=np.einsum('ij,ij->i',B1,T0); b1y=np.einsum('ij,ij->i',B1,B0)
mir=(c_*b1y-s_*b1x)<0
COL=np.stack([bodym,c_*0.5+0.5,s_*0.5+0.5,mir.astype(np.float64)],1)
# UE stores vertex colours as sRGB bytes (FLinearColor::ToFColor(true)) and the material reads the raw bytes:
# pre-linearise RGB so the material sees exactly the encoded values (alpha is stored linearly)
lin=lambda v: np.where(v<=0.04045, v/12.92, ((v+0.055)/1.055)**2.4)
COL[:,:3]=lin(np.clip(COL[:,:3],0,1)); COL=COL.astype(np.float32)
# split vertices for triangles that straddle the belly seam (V wraps at 0 / ROWS/PER_TILE)
VT=ROWS/PER_TILE
tri=I.copy(); vv=V1[tri]; bad=(vv.max(1)-vv.min(1))>VT/2
extra_src=[]; remap={}
for t_ in np.nonzero(bad)[0]:
    for c_ in range(3):
        vi=tri[t_,c_]
        if V1[vi]<VT/2:
            if vi not in remap: remap[vi]=len(P)+len(extra_src); extra_src.append(vi)
            tri[t_,c_]=remap[vi]
es=np.array(extra_src,dtype=np.int64)
if len(es):
    P=np.r_[P,P[es]]; N=np.r_[N,N[es]]; T=np.r_[T,T[es]]; UV=np.r_[UV,UV[es]]; J=np.r_[J,J[es]]; Wt=np.r_[Wt,Wt[es]]
    U1=np.r_[U1,U1[es]]; V1=np.r_[V1,V1[es]+VT]; COL=np.r_[COL,COL[es]]
I=tri
UV1=np.stack([U1,V1],1).astype(np.float32)
print('uv1: U tiles %.1f, seam split %d verts, rows %d'%(U1.max()-U1.min(),len(es),ROWS))
def extra(j,add_view,add_acc):
    base=len(j['nodes'])
    for i,(n,p,pa) in enumerate(zip(names,pos,parent)):
        lp=p-(pos[pa] if pa>=0 else 0)
        j['nodes'].append({'name':n,'translation':[float(v) for v in lp]})
    for i,pa in enumerate(parent):
        if pa>=0: j['nodes'][base+pa].setdefault('children',[]).append(base+i)
    ibm=np.zeros((len(names),16),np.float32)
    for i,p in enumerate(pos):
        M=np.eye(4); M[:3,3]=-p; ibm[i]=M.T.ravel()   # column-major
    j['skins']=[{'joints':list(range(base,base+len(names))),'skeleton':base,'inverseBindMatrices':add_acc(ibm)}]
    j['nodes'][0]['skin']=0
    j['scenes'][0]['nodes']=[0,base]
    j['materials']=[{'name':'M_Vishap','pbrMetallicRoughness':{'metallicFactor':0.0,'roughnessFactor':0.5}}]
    j['meshes'][0]['primitives'][0]['material']=0
glbio.write(out,[dict(POSITION=P.astype(np.float32),NORMAL=N.astype(np.float32),TANGENT=T.astype(np.float32),TEXCOORD_0=UV.astype(np.float32),TEXCOORD_1=UV1,COLOR_0=COL,JOINTS_0=J,WEIGHTS_0=Wt.astype(np.float32),indices=I)],extra=extra)
open(out+'.bones.txt','w').write('\n'.join('%s parent=%s pos_m=%s'%(n,names[pa] if pa>=0 else '-',np.round(p,4).tolist()) for n,p,pa in zip(names,pos,parent)))
print('wrote',out)
