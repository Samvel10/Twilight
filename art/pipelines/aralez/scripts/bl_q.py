import bpy,sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=sys.argv[sys.argv.index('--')+1])
arm=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'][0]
for a in bpy.data.actions:
    paths=set(f.data_path.split('"')[1] if '"' in f.data_path else f.data_path for f in a.fcurves)
    kinds={}
    for f in a.fcurves: kinds[f.data_path.rsplit('.',1)[-1]]=kinds.get(f.data_path.rsplit('.',1)[-1],0)+1
    print('ACT',a.name,a.frame_range[:],len(a.fcurves),kinds)
print('FPS',bpy.context.scene.render.fps)
pb=arm.pose.bones
print([ (b.name,b.rotation_mode) for b in list(pb)[:3]])
m=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name!='Icosphere'][0]
print('MESH',m.name,len(m.data.vertices),len(m.data.polygons),[mod.type for mod in m.modifiers],m.data.shape_keys, len(m.vertex_groups), [u.name for u in m.data.uv_layers], m.data.attributes.keys()[:10])
