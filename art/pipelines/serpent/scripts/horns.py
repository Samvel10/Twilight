# Procedural keratin horns (own work, CC0) in the serpent's head-bone frame (glTF: +X snout, +Y up, Z lateral, metres).
# Ridged growth rings, oval section, swept back/up/out like a horned viper's supraocular horns grown large.
import sys,os; sys.path.insert(0,os.path.dirname(__file__)); import glbio,numpy as np
out=sys.argv[1]; HK=float(os.environ.get('HK','1.188'))   # head size factor vs the 0.426 m reference head
L=float(os.environ.get('HORN_LEN','0.24'))*HK; R0=0.030*HK
NA,NL=28,90
def centre(t):
    return np.stack([-0.80*t-0.25*t*t, 0.55*t-0.30*t*t, 0.22*t+0.05*t*t],-1)*L
t=np.linspace(0,1,NL); C=centre(t)
T=np.gradient(C,axis=0); T/=np.linalg.norm(T,axis=1,keepdims=True)
N=np.zeros_like(T); up=np.array([0,1.,0]); n=np.cross(T[0],np.array([0,0,1.])); N[0]=n/np.linalg.norm(n)
for i in range(1,NL):
    v=N[i-1]-T[i]*T[i].dot(N[i-1]); N[i]=v/np.linalg.norm(v)
B=np.cross(T,N)
r=R0*(1-t)**0.85+0.0015
ring=1+0.07*np.clip(np.sin(2*np.pi*16*t),0,1)**3*(1-t)
a=np.linspace(0,2*np.pi,NA+1)
P=[];UV=[];NR=[]
for i in range(NL):
    rr=r[i]*ring[i]
    for j,aa in enumerate(a):
        off=N[i]*np.cos(aa)*rr*1.0+B[i]*np.sin(aa)*rr*0.78
        P.append(C[i]+off); UV.append([j/NA,t[i]]); NR.append(off/ (np.linalg.norm(off)+1e-9))
P=np.array(P);UV=np.array(UV);NR=np.array(NR)
I=[]
for i in range(NL-1):
    for j in range(NA):
        a0=i*(NA+1)+j; a1=a0+1; b0=a0+NA+1; b1=b0+1
        I+= [[a0,b0,a1],[a1,b0,b1]]
I=np.array(I)
base=np.array([0.15,0.118,0.075])*HK
PL=P+base; PR=P*np.array([1,1,-1])+base*np.array([1,1,-1]); NRR=NR*np.array([1,1,-1])
IR=I[:,[0,2,1]]+len(P)
Pa=np.r_[PL,PR].astype(np.float32); Na=np.r_[NR,NRR].astype(np.float32); Ua=np.r_[UV,UV].astype(np.float32); Ia=np.r_[I[:,[0,2,1]],IR[:,[0,2,1]]].astype(np.uint32)   # CCW = outward
# orientation sanity: outward normals vs. winding
fn=np.cross(Pa[Ia[:,1]]-Pa[Ia[:,0]],Pa[Ia[:,2]]-Pa[Ia[:,0]]); print('winding agrees with normals:', float((np.einsum('ij,ij->i',fn,Na[Ia[:,0]])>0).mean()))
def extra(j,av,aa): j['materials']=[{'name':'M_VishapHorn'}]; j['meshes'][0]['primitives'][0]['material']=0; j['nodes'][0]['name']='VishapHorns'
glbio.write(out,[dict(POSITION=Pa,NORMAL=Na,TEXCOORD_0=Ua,indices=Ia)],extra=extra)
print('horns tris',len(Ia),'len m',L)
