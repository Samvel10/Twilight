import bpy,sys
a=sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=a[0])
for o in bpy.context.scene.objects:
    print('OBJ',o.name,o.type,o.parent.name if o.parent else None,tuple(round(x,3) for x in o.location),tuple(round(x,3) for x in o.rotation_euler),tuple(round(x,4) for x in o.scale), len(o.data.vertices) if o.type=='MESH' else '')
arm=[o for o in bpy.context.scene.objects if o.type=='ARMATURE'][0]
M=arm.matrix_world
for b in arm.data.bones:
    if any(k in b.name for k in ['lip','brow','squint','whisker','lid','nostril','_end','ring','pinkie','mid_','index','corrective']): continue
    h=M@b.head_local; t=M@b.tail_local
    print('BONE %-28s par=%-24s h=(%.3f %.3f %.3f) t=(%.3f %.3f %.3f) len=%.3f'%(b.name,b.parent.name if b.parent else '-',h.x,h.y,h.z,t.x,t.y,t.z,(t-h).length))
