# usage: preview.py <npy> <mpp> <lon0> <lat0> <lon1> <lat1> <out.png> [lake_level]
import sys, numpy as np
from PIL import Image, ImageDraw
C=np.load(sys.argv[1]); mpp=float(sys.argv[2]); lo0,la0,lo1,la1=map(float,sys.argv[3:7]); out=sys.argv[7]
lake=float(sys.argv[8]) if len(sys.argv)>8 else -1e9
gy,gx=np.gradient(C,mpp); sh=np.clip((-gx-gy)/np.sqrt(gx*gx+gy*gy+1)/1.4+0.5,0,1)
h=np.clip((C-1800)/2000,0,1)
rgb=np.stack([0.35+0.65*h,0.45+0.5*h,0.3+0.6*h],-1)*sh[...,None]*1.3
rgb[C<=lake]=[0.1,0.2,0.6]
img=Image.fromarray((np.clip(rgb,0,1)*255).astype(np.uint8)); d=ImageDraw.Draw(img); W,Hh=img.size
import math
for i in range(int(lo0*20)+1,int(lo1*20)+1):
  lon=i/20; x=(lon-lo0)/(lo1-lo0)*W; d.line([(x,0),(x,Hh)],fill=(255,255,0,80)); d.text((x+2,2),'%.2f'%lon,fill=(255,255,0))
for j in range(int(la0*20)+1,int(la1*20)+1):
  lat=j/20; y=(la1-lat)/(la1-la0)*Hh; d.line([(0,y),(W,y)],fill=(255,255,0)); d.text((2,y+2),'%.2f'%lat,fill=(255,255,0))
img.save(out); print(img.size, C.min(), C.max())
