"""Clean the Sketchfab/Objaverse Spartan GLB (CC-BY Andywoodhead) for Unreal Interchange:
 - joint names 'spine_01_014' -> 'spine_01' (Sketchfab appends _<n>); '_rootJoint' -> 'root'  => exact UE4 mannequin bone names
 - armature node 'root' -> 'Armature' (avoid a clash with the root bone)
 - drop the meshes whose name contains any of DROP (default Shield,Sword) -- the hero's hands stay free for fire
 - merge all remaining skinned meshes into ONE glTF mesh (one primitive per material) so Interchange makes one SkeletalMesh
usage: python3 -I prep_spartan.py in.glb out.glb [Shield,Sword] [MeshName]"""
import json,struct,sys,re
src,dst=sys.argv[1],sys.argv[2]
drop=[d for d in (sys.argv[3] if len(sys.argv)>3 else 'Shield,Sword').split(',') if d]
mname=sys.argv[4] if len(sys.argv)>4 else 'SK_Vahagn'
b=open(src,'rb').read()
n=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+n]); rest=b[20+n:]
skin=j['skins'][0]; joints=set(skin['joints'])
for i,nd in enumerate(j['nodes']):
    nm=nd.get('name','')
    if i in joints: nd['name']='root' if nm=='_rootJoint' else re.sub(r'_\d+$','',nm)
    elif nm=='root': nd['name']='Armature'
prims=[]; first=None
for i,nd in enumerate(j['nodes']):
    if 'mesh' not in nd: continue
    m=j['meshes'][nd['mesh']]
    if any(d in m.get('name','') for d in drop): print('drop',m['name'])
    else:
        print('keep',m['name'],len(m['primitives'])); prims+=m['primitives']
        if first is None: first=i
    if i!=first: del nd['mesh']; nd.pop('skin',None)
j['meshes']=[{'name':mname,'primitives':prims}]
j['nodes'][first]['mesh']=0; j['nodes'][first]['name']=mname
names=[j['nodes'][k]['name'] for k in skin['joints']]
assert len(set(names))==len(names), 'duplicate bone names'
js=json.dumps(j,separators=(',',':')).encode(); js+=b' '*((4-len(js)%4)%4)
out=b'glTF'+struct.pack('<II',2,12+8+len(js)+len(rest))+struct.pack('<I',len(js))+b'JSON'+js+rest
open(dst,'wb').write(out); print('wrote',dst,len(out),'prims',len(prims),'bones',len(names))
