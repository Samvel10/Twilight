"""Procedural, tileable skin micro-detail normal map (pores + fine wrinkles), 1024^2, original work (CC0).
usage: python3 -I make_skin_detail.py out.png"""
import sys, numpy as np
from PIL import Image
N=1024; rng=np.random.default_rng(7)
def band(lo,hi,amp):  # periodic band-limited noise via FFT
    w=rng.standard_normal((N,N)); F=np.fft.fft2(w)
    fy=np.fft.fftfreq(N)[:,None]*N; fx=np.fft.fftfreq(N)[None,:]*N; r=np.sqrt(fx*fx+fy*fy)
    m=np.exp(-((np.log(np.maximum(r,1e-6))-np.log((lo+hi)/2))**2)/(2*(np.log(hi/lo)/2)**2))
    h=np.real(np.fft.ifft2(F*m)); return amp*h/np.abs(h).max()
h=np.zeros((N,N))
# pores: many small round dips, wrapped
k=np.arange(-4,5); g=np.exp(-(k[:,None]**2+k[None,:]**2)/(2*1.3**2))
pts=rng.integers(0,N,(9000,2)); depth=rng.uniform(0.4,1.0,9000)
for (y,x),d in zip(pts,depth):
    ys=(y+k)%N; xs=(x+k)%N; h[np.ix_(ys,xs)]-=d*g
h=h/np.abs(h).max()*0.8
# fine cross-hatched wrinkles (anisotropic noise in two directions) + general bumpiness
for ang in (0.6, 2.2):
    w=rng.standard_normal((N,N)); F=np.fft.fft2(w)
    fy=np.fft.fftfreq(N)[:,None]*N; fx=np.fft.fftfreq(N)[None,:]*N
    u=fx*np.cos(ang)+fy*np.sin(ang); v=-fx*np.sin(ang)+fy*np.cos(ang)
    m=np.exp(-(u/25.0)**2-((np.abs(v)-70)/45.0)**2)
    hh=np.real(np.fft.ifft2(F*m)); h+=0.07*hh/np.abs(hh).max()
h+=band(150,350,0.12)+band(15,45,0.12)
s=6.0
dx=(np.roll(h,-1,1)-np.roll(h,1,1))*0.5*s; dy=(np.roll(h,-1,0)-np.roll(h,1,0))*0.5*s
n=np.stack([-dx,-dy,np.ones_like(h)],-1); n/=np.linalg.norm(n,axis=-1,keepdims=True)
img=((n*0.5+0.5)*255).round().clip(0,255).astype(np.uint8)
Image.fromarray(img,'RGB').save(sys.argv[1]); print('wrote',sys.argv[1],'z mean',n[...,2].mean())
