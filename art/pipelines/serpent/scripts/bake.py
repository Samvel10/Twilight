# Step 3: xatlas unwrap of the low mesh + bake albedo / tangent-space normal / mouth mask from the straightened scan.
import sys,os,numpy as np,xatlas
from scipy.spatial import cKDTree
from PIL import Image
hi=np.load(sys.argv[1]); lo=np.load(sys.argv[2]); alb=np.asarray(Image.open(sys.argv[3]).convert('RGB')).astype(np.float32)/255
out=sys.argv[4]; R=int(os.environ.get('RES','2048')); NS=int(os.environ.get('NSAMP','7000000'))
Ph,Nh,UVh,Ih=hi['P'].astype(np.float64),hi['N'].astype(np.float64),hi['UV'].astype(np.float64),hi['I']
Pl,Il=lo['P'].astype(np.float64),lo['I']
# ---- unwrap
atlas=xatlas.Atlas(); atlas.add_mesh(Pl.astype(np.float32),Il.astype(np.uint32))
co=xatlas.ChartOptions(); co.max_iterations=4
po=xatlas.PackOptions(); po.resolution=R; po.padding=4; po.bilinear=True; po.bruteForce=False
atlas.generate(co,po); vmap,I2,UV2=atlas[0]
print('atlas charts',atlas.chart_count,'util',atlas.utilization,'v',len(vmap))
P2=Pl[vmap]
# smooth vertex normals on the welded low mesh
fn=np.cross(Pl[Il[:,1]]-Pl[Il[:,0]],Pl[Il[:,2]]-Pl[Il[:,0]]); vn=np.zeros_like(Pl)
for k in range(3): np.add.at(vn,Il[:,k],fn)
vn/=np.linalg.norm(vn,axis=1,keepdims=True)+1e-12; N2=vn[vmap]
# tangents (Lengyel) on split mesh
def tangents(P,N,UV,I):
    t=np.zeros_like(P); bt=np.zeros_like(P)
    p0,p1,p2=P[I[:,0]],P[I[:,1]],P[I[:,2]]; w0,w1,w2=UV[I[:,0]],UV[I[:,1]],UV[I[:,2]]
    e1=p1-p0;e2=p2-p0; d1=w1-w0; d2=w2-w0; r=d1[:,0]*d2[:,1]-d2[:,0]*d1[:,1]; r=np.where(np.abs(r)<1e-12,1e-12,r)
    sd=(e1*d2[:,1:2]-e2*d1[:,1:2])/r[:,None]; td=(e2*d1[:,0:1]-e1*d2[:,0:1])/r[:,None]
    for k in range(3): np.add.at(t,I[:,k],sd); np.add.at(bt,I[:,k],td)
    t=t-N*np.einsum('ij,ij->i',N,t)[:,None]; t/=np.linalg.norm(t,axis=1,keepdims=True)+1e-12
    w=np.sign(np.einsum('ij,ij->i',np.cross(N,t),bt)); w[w==0]=1
    return t,w
T2,W2=tangents(P2,N2,UV2,I2)
# ---- high samples
p0,p1,p2=Ph[Ih[:,0]],Ph[Ih[:,1]],Ph[Ih[:,2]]; area=0.5*np.linalg.norm(np.cross(p1-p0,p2-p0),axis=1)
rng=np.random.default_rng(1); tri=rng.choice(len(Ih),NS,p=area/area.sum())
a=rng.random(NS);b=rng.random(NS); fl=a+b>1; a[fl]=1-a[fl]; b[fl]=1-b[fl]; c=1-a-b
def interp(A): return A[Ih[tri,0]]*c[:,None]+A[Ih[tri,1]]*a[:,None]+A[Ih[tri,2]]*b[:,None]
S_P=interp(Ph); S_N=interp(Nh); S_N/=np.linalg.norm(S_N,axis=1,keepdims=True)+1e-12; S_UV=interp(UVh)
# sample albedo bilinear
def samp(img,uv):
    h,w,_=img.shape; x=np.mod(uv[:,0],1)*w-0.5; y=np.mod(uv[:,1],1)*h-0.5
    x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); fx=(x-x0)[:,None]; fy=(y-y0)[:,None]
    x0%=w;y0%=h;x1=(x0+1)%w;y1=(y0+1)%h
    return img[y0,x0]*(1-fx)*(1-fy)+img[y0,x1]*fx*(1-fy)+img[y1,x0]*(1-fx)*fy+img[y1,x1]*fx*fy
S_C=samp(alb,S_UV)
tree=cKDTree(S_P); print('tree ok')
# ---- rasterise low triangles in UV space
uvp=UV2*R  # xatlas returns normalised UVs
pos=np.zeros((R,R,3)); nrm=np.zeros((R,R,3)); tan=np.zeros((R,R,3)); wsg=np.zeros((R,R)); cov=np.zeros((R,R),bool)
for f in I2:
    q=uvp[f]; x0=int(np.floor(q[:,0].min())); x1=int(np.ceil(q[:,0].max())); y0=int(np.floor(q[:,1].min())); y1=int(np.ceil(q[:,1].max()))
    xs,ys=np.meshgrid(np.arange(max(x0,0),min(x1+1,R)),np.arange(max(y0,0),min(y1+1,R)))
    px=xs.ravel()+0.5; py=ys.ravel()+0.5
    d=(q[1,1]-q[2,1])*(q[0,0]-q[2,0])+(q[2,0]-q[1,0])*(q[0,1]-q[2,1])
    if abs(d)<1e-12: continue
    l0=((q[1,1]-q[2,1])*(px-q[2,0])+(q[2,0]-q[1,0])*(py-q[2,1]))/d
    l1=((q[2,1]-q[0,1])*(px-q[2,0])+(q[0,0]-q[2,0])*(py-q[2,1]))/d
    l2=1-l0-l1; e=-0.02/ max(1.0,np.sqrt(abs(d)))
    m=(l0>=e)&(l1>=e)&(l2>=e)
    if not m.any(): continue
    X=xs.ravel()[m]; Y=ys.ravel()[m]; L=np.stack([l0[m],l1[m],l2[m]],1)
    pos[Y,X]=L@P2[f]; nrm[Y,X]=L@N2[f]; tan[Y,X]=L@T2[f]; wsg[Y,X]=W2[f].sum()/3; cov[Y,X]=True
print('covered texels',cov.sum())
yy,xx=np.nonzero(cov); qp=pos[yy,xx]; qn=nrm[yy,xx]; qn/=np.linalg.norm(qn,axis=1,keepdims=True)+1e-12
qt=tan[yy,xx]; qt=qt-qn*np.einsum('ij,ij->i',qn,qt)[:,None]; qt/=np.linalg.norm(qt,axis=1,keepdims=True)+1e-12
qb=np.cross(qn,qt)*np.sign(wsg[yy,xx])[:,None]
# nearest high sample (k=4 averaged for smoother result)
KN=int(os.environ.get('KNN','6')); dist,idx=tree.query(qp,k=KN,workers=-1); wgt=1/(dist+1e-5); wgt/=wgt.sum(1,keepdims=True)
col=np.einsum('ij,ijk->ik',wgt,S_C[idx]); hn=np.einsum('ij,ijk->ik',wgt,S_N[idx]); hn/=np.linalg.norm(hn,axis=1,keepdims=True)+1e-12
tn=np.stack([np.einsum('ij,ij->i',hn,qt),np.einsum('ij,ij->i',hn,qb),np.einsum('ij,ij->i',hn,qn)],1)
tn[:,2]=np.maximum(tn[:,2],0.05); tn/=np.linalg.norm(tn,axis=1,keepdims=True)
# mouth mask (geometric): palate = faces looking down above the mouth line, mouth floor/tongue = faces looking up
# below it, both in front of the jaw hinge and inside the lips' width. Soft edges.
HK=float(hi['headlen'])/0.426   # constants below were measured on the 0.426 m head
X,Y,Z=qp[:,0]/HK,qp[:,1]/HK,np.abs(qp[:,2])/HK; line=-0.03-0.06*(X-0.12)
ny=hn[:,1]*0.5+qn[:,1]*0.5
sm=lambda a,b,v: np.clip((v-a)/(b-a),0,1)
front=sm(0.06,0.10,X)
width=1-sm(0.045,0.07,Z)
pal=(Y>line-0.005)*sm(0.15,0.45,-ny)*(1-sm(0.035,0.06,Y-line))
flo=(Y<line+0.005)*sm(0.15,0.45,ny)*(1-sm(0.03,0.055,line-Y))
mouth=np.clip(np.maximum(pal,flo)*front*width,0,1)
A=np.zeros((R,R,3)); A[yy,xx]=col
NM=np.zeros((R,R,3)); NM[...,2]=1; NM[yy,xx]=tn
MK=np.zeros((R,R)); MK[yy,xx]=mouth
# dilate (fill empty texels from neighbours) 
def dilate(img,cov,n=24):
    img=img.copy(); c=cov.copy()
    for it in range(n):
        acc=np.zeros_like(img); cnt=np.zeros(c.shape)
        for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
            sh=np.roll(np.roll(img,dy,0),dx,1); sc=np.roll(np.roll(c,dy,0),dx,1)
            acc[sc]+=sh[sc] if img.ndim==2 else sh[sc]; cnt+=sc
        new=(~c)&(cnt>0)
        if img.ndim==3: img[new]=acc[new]/cnt[new][:,None]
        else: img[new]=acc[new]/cnt[new]
        c=c|new
    return img
A=dilate(A,cov); NM=dilate(NM,cov); MK=dilate(MK,cov)
Image.fromarray((np.clip(A,0,1)**1*255).astype(np.uint8)).save(out+'_D.png')
NMo=NM/ (np.linalg.norm(NM,axis=2,keepdims=True)+1e-12)
Image.fromarray(((NMo*0.5+0.5)*255).clip(0,255).astype(np.uint8)).save(out+'_N.png')
Image.fromarray((MK*255).astype(np.uint8)).save(out+'_M.png')
np.savez(out+'_mesh.npz',P=P2.astype(np.float32),N=N2.astype(np.float32),UV=UV2.astype(np.float32),I=I2.astype(np.int64),T=np.c_[T2,W2].astype(np.float32),headlen=float(hi['headlen']))
print('done mouth texels',int((mouth>0.5).sum()))
