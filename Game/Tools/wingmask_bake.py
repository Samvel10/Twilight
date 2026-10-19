# Bake a UV-space wing-membrane mask from glTF skin weights (or whole primitives).
# usage: wingmask.py file.glb out.png "joint_regex" [mesh_idx_list_whole]  size
import json,struct,sys,re
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
f,out,rx=sys.argv[1],sys.argv[2],sys.argv[3]
whole=[int(x) for x in sys.argv[4].split(',')] if len(sys.argv)>4 and sys.argv[4] else []
S=int(sys.argv[5]) if len(sys.argv)>5 else 1024
b=open(f,'rb').read(); n=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+n]); BIN=20+n+8
CT={5120:np.int8,5121:np.uint8,5122:np.int16,5123:np.uint16,5125:np.uint32,5126:np.float32}
NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}
def acc(i):
    a=j['accessors'][i]; bv=j['bufferViews'][a['bufferView']]
    dt=np.dtype(CT[a['componentType']]); nc=NC[a['type']]
    off=BIN+bv.get('byteOffset',0)+a.get('byteOffset',0); stride=bv.get('byteStride',dt.itemsize*nc)
    raw=np.frombuffer(b,dtype=np.uint8,count=stride*(a['count']-1)+dt.itemsize*nc,offset=off)
    out=np.lib.stride_tricks.as_strided(raw,shape=(a['count'],dt.itemsize*nc),strides=(stride,1)).copy().view(dt).reshape(a['count'],nc)
    if a.get('normalized'): out=out.astype(np.float32)/np.iinfo(dt).max
    return out
names=[j['nodes'][k]['name'] for k in j['skins'][0]['joints']]
sel=np.array([bool(re.search(rx,nm)) for nm in names]+[False])
print('selected joints',[nm for nm,s in zip(names,sel) if s][:40])
img=Image.new('L',(S,S),0); dr=ImageDraw.Draw(img)
mat_target=None
for mi,m in enumerate(j['meshes']):
    for p in m['primitives']:
        at=p['attributes']; uv=acc(at['TEXCOORD_0'])
        idx=acc(p['indices']).reshape(-1,3) if 'indices' in p else np.arange(len(uv)).reshape(-1,3)
        if mi in whole: w=np.ones(len(uv))
        elif 'JOINTS_0' in at and rx:
            J=acc(at['JOINTS_0']).astype(int); W=acc(at['WEIGHTS_0']).astype(float)
            w=(sel[np.clip(J,0,len(names))]*W).sum(1)
        else: continue
        print('mesh',mi,m['name'][-30:],'mat',p.get('material'),'verts',len(uv),'wing verts',(w>0.5).sum())
        for t in idx:
            v=w[t].mean()
            if v<0.05: continue
            pts=[(float(u*S),float(vv*S)) for u,vv in uv[t]]
            dr.polygon(pts,fill=int(255*min(1,v)))
img=img.filter(ImageFilter.MaxFilter(3))
img.save(out); print('saved',out, np.asarray(img).mean()/255)
