# Step 1: straighten the scanned snake along a smoothed spine and save as npz (high-poly, straight space, metres).
# Output frame (glTF, Y up): +X = towards the head, Y = dorsal up, Z = lateral. Origin = neck pivot (root bone).
import sys,os; sys.path.insert(0,os.path.dirname(__file__)); import glbio,numpy as np
from scipy.spatial import cKDTree
src,out=sys.argv[1],sys.argv[2]
STRETCH=float(os.environ.get('STRETCH','1.5'))   # body elongation factor (head unchanged)
LTARGET=float(os.environ.get('LTARGET','10.0'))  # final length in metres
j,b=glbio.load(src); pr=j['meshes'][0]['primitives'][0]
Pv=glbio.acc(j,b,pr['attributes']['POSITION']).astype(np.float64); Nv=glbio.acc(j,b,pr['attributes']['NORMAL']).astype(np.float64)
UV=glbio.acc(j,b,pr['attributes']['TEXCOORD_0']); I=glbio.acc(j,b,pr['indices']).reshape(-1,3)
x=Pv[:,0]; xlo,xhi=x.min(),x.max()
# --- spine centre per bin (bbox centre) ---
step=0.1; e=np.arange(xlo,xhi+step,step); cx=[];cy=[];cz=[]
for i in range(len(e)-1):
    m=(x>=e[i])&(x<e[i+1])
    if m.sum()<20: continue
    q=Pv[m]; cx.append((e[i]+e[i+1])/2); cy.append((q[:,1].min()+q[:,1].max())/2); cz.append((q[:,2].min()+q[:,2].max())/2)
cx=np.array(cx);cy=np.array(cy);cz=np.array(cz)
XNECK=-6.5
# head: continue the neck line (fit on -6.5..-4.5) so the open jaw does not bend the spine
m=(cx>XNECK)&(cx<-4.5); ay=np.polyfit(cx[m],cy[m],1); az=np.polyfit(cx[m],cz[m],1)
h=cx<=XNECK; cy[h]=np.polyval(ay,cx[h]); cz[h]=np.polyval(az,cx[h])
# head centre height: use upper-skull/eye line rather than jaw; keep line.
def smooth(a,s):
    k=np.exp(-0.5*(np.arange(-3*s,3*s+1)/s)**2); k/=k.sum(); pad=np.r_[np.full(3*s,a[0]),a,np.full(3*s,a[-1])]
    return np.convolve(pad,k,'valid')
cy=smooth(cy,4); cz=smooth(cz,4)
# extend both ends linearly by 1 unit, resample densely
def ext(c):
    d0=(c[1]-c[0]); d1=(c[-1]-c[-2]); n=10
    return np.r_[c[0]-d0*np.arange(n,0,-1), c, c[-1]+d1*np.arange(1,n+1)]
C=np.stack([ext(cx),ext(cy),ext(cz)],1)
seg=np.linalg.norm(np.diff(C,axis=0),axis=1); sc=np.r_[0,np.cumsum(seg)]
sd=np.arange(0,sc[-1],0.004); D=np.stack([np.interp(sd,sc,C[:,k]) for k in range(3)],1)
T=np.gradient(D,axis=0); T/=np.linalg.norm(T,axis=1,keepdims=True)
# rotation minimising frames starting with up=+Y
N=np.zeros_like(T); up=np.array([0,1.,0]); n0=up-T[0]*T[0].dot(up); N[0]=n0/np.linalg.norm(n0)
for i in range(1,len(T)):
    n=N[i-1]-T[i]*T[i].dot(N[i-1]); N[i]=n/np.linalg.norm(n)
B=np.cross(T,N)
tree=cKDTree(D); _,k=tree.query(Pv,workers=-1)
d=Pv-D[k]; s=sd[k]+np.einsum('ij,ij->i',d,T[k])
u=np.einsum('ij,ij->i',d,N[k]); v=np.einsum('ij,ij->i',d,B[k])
nt=np.einsum('ij,ij->i',Nv,T[k]); nn=np.einsum('ij,ij->i',Nv,N[k]); nb=np.einsum('ij,ij->i',Nv,B[k])
# even out the specimen's girth (food bulges / preservation dents) along the body, keep head, neck and tail taper
EVEN=float(os.environ.get('EVEN','1.0'))
if EVEN>0:
    r=np.sqrt(u*u+v*v); bs=0.05; nbin=int((s.max()-s.min())/bs)+1; bi=((s-s.min())/bs).astype(int)
    rs=np.zeros(nbin)
    for b_ in range(nbin):
        m_=bi==b_
        rs[b_]=np.percentile(r[m_],80) if m_.sum()>10 else np.nan
    ok=~np.isnan(rs); rs=np.interp(np.arange(nbin),np.nonzero(ok)[0],rs[ok])
    def gs(a,sig):
        k_=np.exp(-0.5*(np.arange(-4*sig,4*sig+1)/sig)**2); k_/=k_.sum(); pad=np.r_[np.full(4*sig,a[0]),a,np.full(4*sig,a[-1])]
        return np.convolve(pad,k_,'valid')
    rloc=gs(rs,int(0.25/bs)); rtgt=gs(rs,int(1.8/bs))
    fac=np.clip(rtgt/np.maximum(rloc,1e-4),0.85,1.2)
    sneck0=np.interp(XNECK, D[:,0], sd); sc_=s.min()+np.arange(nbin)*bs
    w_=np.clip((sc_-(sneck0+0.4))/0.8,0,1)*EVEN
    fac=1+(fac-1)*w_
    fv=np.interp(s,sc_,fac); u=u*fv; v=v*fv
    print('girth evened: factor range %.3f..%.3f'%(fac.min(),fac.max()))
# arc length of neck and tail tip
sneck=np.interp(XNECK, D[:,0], sd); stip=s.min(); send=s.max()
print('s tip %.3f neck %.3f end %.3f'%(stip,sneck,send))
# stretch body
s2=np.where(s<sneck, s, sneck+(s-sneck)*STRETCH)
Ltot=(sneck-stip)+(send-sneck)*STRETCH; k_m=LTARGET/Ltot
X=(sneck-s2)*k_m; Y=u*k_m; Z=v*k_m
# normals: along-body component scales by 1/STRETCH in the stretched part (inverse transpose)
ntx=np.where(s<sneck, nt, nt/STRETCH)
Nout=np.stack([-ntx,nn,nb],1); Nout/=np.linalg.norm(Nout,axis=1,keepdims=True)
Pout=np.stack([X,Y,Z],1)
# handedness: (T,N,B) right-handed; X=-T flips one axis -> flip Z too to keep orientation (mirror otherwise)
Pout[:,2]*=-1; Nout[:,2]*=-1
print('length m %.3f  scale %.4f  head len m %.3f  maxR m %.3f'%(np.ptp(Pout[:,0]),k_m,(sneck-stip)*k_m,np.abs(Pout[:,1:]).max()))
np.savez(out,P=Pout.astype(np.float32),N=Nout.astype(np.float32),UV=UV,I=I.astype(np.int64),scale=k_m,stretch=STRETCH,headlen=(sneck-stip)*k_m)
