# Procedural tileable snake-scale detail (own work, CC0): 8 rows (around the body, V) x 8 scales (along, U),
# staggered keeled plates overlapping like shingles (the head-ward scale lies on top). Writes normal (DirectX/UE
# green) + height/cavity maps. U runs head -> tail.
import sys,numpy as np
from PIL import Image
out=sys.argv[1]; R=int(sys.argv[2]) if len(sys.argv)>2 else 1024
NU,NV=8,8
y,x=np.mgrid[0:R,0:R].astype(np.float64)+0.5
U=x/R*NU; V=y/R*NV          # in scale units
H=np.full((R,R),-1e9)
rng=np.random.default_rng(3)
jit=rng.uniform(-0.06,0.06,(NV+2,NU+2,2)); hv=rng.uniform(0.9,1.1,(NV+2,NU+2))
for j in range(-1,NV+1):
    for i in range(-1,NU+2):
        cu=i+0.5*(j%2); cv=j+0.5
        ju,jv=jit[j%NV,i%NU]; hh=hv[j%NV,i%NU]
        a=(U-cu-ju)          # along body (+ = toward tail)
        b=(V-cv-jv)
        # wrap distances for tileability
        a=(a+NU/2)%NU-NU/2; b=(b+NV/2)%NV-NV/2
        an=a/0.92; bn=b/0.56
        d=np.abs(an)**1.35+np.abs(bn)**1.5     # lanceolate, keeled (viper dorsal)
        inside=d<1.0
        h=(0.45+0.35*an)*hh                     # rises toward the free (tail-ward) edge
        h+=0.16*np.exp(-(b/0.06)**2)*np.clip(1-np.abs(an),0,1)   # keel
        h-=0.35*np.clip(d-0.75,0,1)**1.5        # rounded rim
        h=np.where(inside,h,-1e9)                 # the rising rear edge of the head-ward scale ends up on top
        H=np.maximum(H,h)
H[H<-1e8]=0.0
H=H-H.min(); H/=H.max()
# small grain
g=rng.normal(0,1,(R//4,R//4)); g=np.kron(g,np.ones((4,4)))
H=H+0.006*g
# normal from height (tileable gradients); strength k
k=float(sys.argv[3]) if len(sys.argv)>3 else 6.0
dx=(np.roll(H,-1,1)-np.roll(H,1,1))*0.5*k; dy=(np.roll(H,-1,0)-np.roll(H,1,0))*0.5*k
n=np.stack([-dx,-dy,np.ones_like(H)],-1); n/=np.linalg.norm(n,axis=-1,keepdims=True)
# DirectX convention: green = +down the image (+V); n_y above is d/dy with y down -> already DX
Image.fromarray(((n*0.5+0.5)*255).clip(0,255).astype(np.uint8)).save(out+'_N.png')
# cavity: low = grooves between scales
cav=np.clip((H-0.05)/0.5,0,1)**0.6
Image.fromarray((cav*255).astype(np.uint8)).save(out+'_H.png')
print('scales written',R)
