"""Bake the Sketchfab FBX->glTF wrapper transform (0.01 scale + axis rotations on ancestor nodes) into the skinned data so
the result is a canonical glTF: identity scene nodes, Y-up metres, root joint = identity, no bone scale.
Unreal Interchange then produces a SkeletalMesh whose root bone is identity and whose ref pose stands up (+Z) like the
UE mannequin.  Works on the output of prep_spartan.py (single merged mesh, one skin, no morph targets).
usage: python3 -I bake_gltf_root.py in.glb out.glb [extra_yaw_deg about up]"""
import json,struct,sys,math
import numpy as np
src,dst=sys.argv[1],sys.argv[2]; yaw=float(sys.argv[3]) if len(sys.argv)>3 else 0.0
b=open(src,'rb').read()
n=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+n])
binlen=struct.unpack('<I',b[20+n:24+n])[0]; bin_=bytearray(b[28+n:28+n+binlen])
N=j['nodes']; skin=j['skins'][0]; joints=skin['joints']; root=joints[0]
par={c:i for i,nd in enumerate(N) for c in nd.get('children',[])}
def m_of(nd):
    if 'matrix' in nd: return np.array(nd['matrix'],dtype=np.float64).reshape(4,4).T
    M=np.eye(4)
    if 'scale' in nd: M=np.diag(list(nd['scale'])+[1.0])@M
    if 'rotation' in nd:
        x,y,z,w=nd['rotation']
        R=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
        T=np.eye(4); T[:3,:3]=R; M=T@M
    if 'translation' in nd: T=np.eye(4); T[:3,3]=nd['translation']; M=T@M
    return M
def glob(i):
    M=m_of(N[i])
    while i in par: i=par[i]; M=m_of(N[i])@M
    return M
def quat(m):
    t=np.trace(m)
    if t>0: S=math.sqrt(t+1)*2; w=0.25*S; x=(m[2,1]-m[1,2])/S; y=(m[0,2]-m[2,0])/S; z=(m[1,0]-m[0,1])/S
    elif m[0,0]>m[1,1] and m[0,0]>m[2,2]: S=math.sqrt(1+m[0,0]-m[1,1]-m[2,2])*2; w=(m[2,1]-m[1,2])/S; x=0.25*S; y=(m[0,1]+m[1,0])/S; z=(m[0,2]+m[2,0])/S
    elif m[1,1]>m[2,2]: S=math.sqrt(1+m[1,1]-m[0,0]-m[2,2])*2; w=(m[0,2]-m[2,0])/S; x=(m[0,1]+m[1,0])/S; y=0.25*S; z=(m[1,2]+m[2,1])/S
    else: S=math.sqrt(1+m[2,2]-m[0,0]-m[1,1])*2; w=(m[1,0]-m[0,1])/S; x=(m[0,2]+m[2,0])/S; y=(m[1,2]+m[2,1])/S; z=0.25*S
    q=np.array([x,y,z,w]); return [float(v) for v in q/np.linalg.norm(q)]
cy,sy=math.cos(math.radians(yaw)),math.sin(math.radians(yaw)); Ry=np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
# current world (rendered) transforms of the joints = old wrapper * joint chain
W={k:glob(k) for k in joints}
# IBMs and the vertex->world matrix (A*G_j*IBM_j, identical for every joint when the scene pose is the bind pose)
acc=j['accessors'][skin['inverseBindMatrices']]; bv=j['bufferViews'][acc['bufferView']]
off=bv.get('byteOffset',0)+acc.get('byteOffset',0)
ibm=np.frombuffer(bytes(bin_[off:off+64*len(joints)]),dtype='<f4').reshape(-1,4,4).astype(np.float64).transpose(0,2,1)
# root / ik_* bones are non-deforming and carry junk IBMs on Sketchfab exports -> use the deforming bones only
Ms=[W[k]@ibm[i] for i,k in enumerate(joints) if not (k==root or N[k]['name'].startswith('ik_'))]
Mv=[W[k]@ibm[i] for i,k in enumerate(joints) if N[k]['name']=='pelvis'][0]
print('vertex->world\n',np.round(Mv,5),'\nmax deviation across deforming joints',max(np.abs(M-Mv).max() for M in Ms))
Mv3=Ry@Mv[:3,:3]; Mvt=Ry@Mv[:3,3]
# new joint world transforms: rotation of W (scale removed) and translation of W, both yawed; root = identity
Gnew={}
for k in joints:
    rot=W[k][:3,:3]; rot=rot/np.linalg.norm(rot,axis=0)
    M=np.eye(4); M[:3,:3]=Ry@rot; M[:3,3]=Ry@W[k][:3,3]; Gnew[k]=M
Gnew[root]=np.eye(4)
for k in joints:
    L=Gnew[k] if k==root else np.linalg.inv(Gnew[par[k]])@Gnew[k]
    nd=N[k]
    for f in ('matrix','scale','translation','rotation'): nd.pop(f,None)
    if np.abs(L[:3,3]).max()>1e-9: nd['translation']=[float(v) for v in L[:3,3]]
    nd['rotation']=quat(L[:3,:3])
i=par[root]
while True:
    for f in ('matrix','translation','rotation','scale'): N[i].pop(f,None)
    if i not in par: break
    i=par[i]
for i in N[par[root]].get('children',[]):   # helper nodes beside the root joint (Object_6...) -> identity
    if i not in joints:
        for f in ('matrix','translation','rotation','scale'): N[i].pop(f,None)
newibm=np.stack([np.linalg.inv(Gnew[k]).T for k in joints]).astype('<f4')
bin_[off:off+64*len(joints)]=newibm.tobytes(); acc.pop('min',None); acc.pop('max',None)
done=set()
def xform(ai,kind):
    if ai in done: return
    done.add(ai); a=j['accessors'][ai]; v=j['bufferViews'][a['bufferView']]
    comps=3 if a['type']=='VEC3' else 4; stride=v.get('byteStride',comps*4); o=v.get('byteOffset',0)+a.get('byteOffset',0)
    raw=np.frombuffer(bytes(bin_[o:o+stride*a['count']]),dtype='<f4').reshape(a['count'],stride//4).copy()
    xyz=raw[:,:3].astype(np.float64)
    if kind=='P': xyz=xyz@Mv3.T+Mvt
    else:
        Rn=Mv3/np.cbrt(abs(np.linalg.det(Mv3))); xyz=xyz@Rn.T; xyz/=np.maximum(np.linalg.norm(xyz,axis=1,keepdims=True),1e-12)
    raw[:,:3]=xyz.astype('<f4'); bin_[o:o+stride*a['count']]=raw.tobytes()
    if kind=='P': a['min']=[float(x) for x in xyz.min(0)]; a['max']=[float(x) for x in xyz.max(0)]
for m in j['meshes']:
    for p in m['primitives']:
        at=p['attributes']; xform(at['POSITION'],'P')
        if 'NORMAL' in at: xform(at['NORMAL'],'N')
        if 'TANGENT' in at: xform(at['TANGENT'],'T')
        if p.get('targets'): print('WARNING morph targets not baked')
js=json.dumps(j,separators=(',',':')).encode(); js+=b' '*((4-len(js)%4)%4)
binb=bytes(bin_); binb+=b'\0'*((4-len(binb)%4)%4)
out=b'glTF'+struct.pack('<II',2,12+8+len(js)+8+len(binb))+struct.pack('<I',len(js))+b'JSON'+js+struct.pack('<I',len(binb))+b'BIN\0'+binb
open(dst,'wb').write(out)
pos=j['accessors'][j['meshes'][0]['primitives'][0]['attributes']['POSITION']]
pel=[k for k in joints if N[k]['name']=='pelvis'][0]
print('wrote',dst,'body bbox',np.round(pos['min'],3),np.round(pos['max'],3),'pelvis world',np.round(Gnew[pel][:3,3],3))
