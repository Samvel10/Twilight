import sys,numpy as np,io
from PIL import Image
z=np.load(sys.argv[1]); P=z['P']; UV=z['UV']; T=np.asarray(Image.open(sys.argv[2]).convert('RGB')); h,w,_=T.shape
C=T[(np.mod(UV[:,1],1)*(h-1)).astype(int),(np.mod(UV[:,0],1)*(w-1)).astype(int)]
x0=float(sys.argv[4]) if len(sys.argv)>4 else -1e9; x1=float(sys.argv[5]) if len(sys.argv)>5 else 1e9
m=(P[:,0]>=x0)&(P[:,0]<=x1); P=P[m]; C=C[m]
lo=P.min(0);hi=P.max(0);rows=[]
for a,bx,dd,sg in ((0,1,2,-1),(0,2,1,1)):
    sc=1580/(hi[0]-lo[0]); H=int((hi[bx]-lo[bx])*sc)+20; img=np.zeros((H,1600,3),np.uint8)+30
    x=((hi[0]-P[:,a])*sc+10).astype(int); y=(H-1-((P[:,bx]-lo[bx])*sc+10)).astype(int)
    o=np.argsort(sg*P[:,dd])
    for k in (0,1): img[np.clip(y[o]+k,0,H-1),np.clip(x[o],0,1599)]=C[o]
    rows.append(img)
Image.fromarray(np.concatenate(rows,0)).save(sys.argv[3],quality=88)
