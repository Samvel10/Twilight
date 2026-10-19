# blender -b -P bl_extract.py -- <hero.glb> <outdir>
# Extracts from the CC-BY Spartan hero GLB: Body base-colour texture, head-weighted Body polygons (uv + position + normal per corner)
# -> <outdir>/headpolys.npz  (used by gen_masks.py and gen_firehair.py). Coordinates = glTF-in-Blender (m, Z up, face looks to -Y).
import bpy, sys, os, numpy as np
a=sys.argv[sys.argv.index('--')+1:]; glb,out=a[0],a[1]; os.makedirs(out,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.gltf(filepath=glb)
o=[o for o in bpy.data.objects if o.type=='MESH' and len(o.data.vertices)>1000][0]; me=o.data
for n in me.materials[0].node_tree.nodes:
    if n.type=='TEX_IMAGE' and any(l.to_socket.name=='Base Color' for l in n.outputs[0].links):
        n.image.filepath_raw=os.path.join(out,'body_base.png'); n.image.file_format='PNG'; n.image.save(); print('BASE saved')
gi=o.vertex_groups['head'].index; uv=me.uv_layers[0].data
hw=np.zeros(len(me.vertices),np.float32)
for v in me.vertices:
    for g in v.groups:
        if g.group==gi: hw[v.index]=g.weight
UV=[];CO=[];NO=[]
for p in me.polygons:
    if p.material_index!=0 or len(p.vertices)>4: continue
    if min(hw[v] for v in p.vertices)<0.5: continue
    vs=list(p.vertices); ls=list(p.loop_indices)
    if len(vs)==3: vs.append(vs[2]); ls.append(ls[2])
    UV.append([tuple(uv[l].uv) for l in ls]); CO.append([tuple(me.vertices[v].co) for v in vs]); NO.append([tuple(me.vertices[v].normal) for v in vs])
np.savez(os.path.join(out,'headpolys.npz'),uv=np.array(UV,np.float32),co=np.array(CO,np.float32),no=np.array(NO,np.float32))
print('POLYS',len(UV))
