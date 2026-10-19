# usage: terrain.py <outdir> <zoom> <lon_min> <lat_min> <lon_max> <lat_max> <name>
import sys,os,math,io,urllib.request,numpy as np
from PIL import Image
out,z,lo0,la0,lo1,la1,name=sys.argv[1],int(sys.argv[2]),*map(float,sys.argv[3:7]),sys.argv[7]
def tile(lon,lat,z):
  n=2**z; x=(lon+180)/360*n; r=math.radians(lat); y=(1-math.asinh(math.tan(r))/math.pi)/2*n; return x,y
x0,y0=tile(lo0,la1,z); x1,y1=tile(lo1,la0,z)
tx0,ty0,tx1,ty1=int(x0),int(y0),int(x1),int(y1)
os.makedirs(os.path.join(out,'tiles'),exist_ok=True)
W=(tx1-tx0+1)*256; H=(ty1-ty0+1)*256; M=np.zeros((H,W),np.float32); tot=0
for ty in range(ty0,ty1+1):
  for tx in range(tx0,tx1+1):
    u=f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{tx}/{ty}.png'
    p=os.path.join(out,'tiles',f'{z}_{tx}_{ty}.png')
    if not os.path.exists(p):
      b=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'TwilightResearch/1.0'})).read(); open(p,'wb').write(b)
    tot+=os.path.getsize(p)
    a=np.asarray(Image.open(p).convert('RGB')).astype(np.float32)
    h=a[...,0]*256+a[...,1]+a[...,2]/256-32768   # Mapzen terrarium decode (metres)
    M[(ty-ty0)*256:(ty-ty0+1)*256,(tx-tx0)*256:(tx-tx0+1)*256]=h
print('zoom',z,'tiles x',tx0,'-',tx1,'y',ty0,'-',ty1,'count',(tx1-tx0+1)*(ty1-ty0+1),'bytes',tot)
# crop to exact bbox
cx0=int((x0-tx0)*256); cy0=int((y0-ty0)*256); cx1=int((x1-tx0)*256); cy1=int((y1-ty0)*256)
C=M[cy0:cy1,cx0:cx1]
lat=(la0+la1)/2; mpp=156543.03392*math.cos(math.radians(lat))/2**z
print(name,'mosaic',M.shape,'crop',C.shape,'m/px %.1f'%mpp,'extent km %.1f x %.1f'%(C.shape[1]*mpp/1000,C.shape[0]*mpp/1000))
print('height min %.1f max %.1f mean %.1f'%(C.min(),C.max(),C.mean()))
iy,ix=np.unravel_index(C.argmax(),C.shape); print('peak at px',ix,iy)
mn,mx=float(C.min()),float(C.max())
h16=((C-mn)/(mx-mn)*65535).round().astype(np.uint16)
Image.fromarray(h16).save(os.path.join(out,name+'_16bit.png'))   # PIL writes mode I;16 PNG
np.save(os.path.join(out,name+'_metres.npy'),C)
# also raw r16 for UE Landscape import
h16.astype('<u2').tofile(os.path.join(out,name+'.r16'))
# hillshade preview
gy,gx=np.gradient(C,mpp); sh=np.clip((-gx*0.7-gy*0.7+1)/np.sqrt(gx*gx+gy*gy+1),0,1)
v=(0.35*sh+0.65*(C-mn)/(mx-mn)); Image.fromarray((v*255).astype(np.uint8)).save(os.path.join(out,name+'_preview.png'))
open(os.path.join(out,name+'_meta.txt'),'w').write(f'bbox {lo0},{la0},{lo1},{la1} zoom {z} size {C.shape[1]}x{C.shape[0]} mpp {mpp:.2f} min {mn:.1f} max {mx:.1f}\n')
