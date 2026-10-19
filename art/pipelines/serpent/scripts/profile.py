# radius / centre profile along X of the welded scan, to locate head, neck, tail
import sys; sys.path.insert(0,sys.argv[1]); import glbio,numpy as np
j,b=glbio.load(sys.argv[2]); p=glbio.acc(j,b,j['meshes'][0]['primitives'][0]['attributes']['POSITION'])
x=p[:,0]; lo,hi=x.min(),x.max(); nb=int(sys.argv[3]) if len(sys.argv)>3 else 60
e=np.linspace(lo,hi,nb+1)
for i in range(nb):
    m=(x>=e[i])&(x<e[i+1]); q=p[m]
    if len(q)==0: continue
    print('%6.2f  n=%6d  ymin=%6.3f ymax=%6.3f zmin=%6.3f zmax=%6.3f  h=%5.3f w=%5.3f'%(e[i],len(q),q[:,1].min(),q[:,1].max(),q[:,2].min(),q[:,2].max(),np.ptp(q[:,1]),np.ptp(q[:,2])))
