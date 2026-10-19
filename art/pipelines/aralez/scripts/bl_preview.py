# blender -b -P bl_preview.py -- in.glb out_prefix [engine]
import bpy,sys,math,mathutils
a=sys.argv[sys.argv.index('--')+1:]; src,out=a[0],a[1]; eng=a[2] if len(a)>2 else 'BLENDER_EEVEE_NEXT'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc=bpy.context.scene
objs=[o for o in sc.objects if o.type=='MESH']
arm=[o for o in sc.objects if o.type=='ARMATURE']
acts=list(bpy.data.actions)
print('ACTIONS',[(x.name,x.frame_range[:]) for x in acts])
def bbox():
    P=[]
    dg=bpy.context.evaluated_depsgraph_get()
    for o in objs:
        oe=o.evaluated_get(dg); m=oe.to_mesh()
        P+=[oe.matrix_world@v.co for v in m.vertices]
        oe.to_mesh_clear()
    xs=sorted(p.x for p in P); ys=sorted(p.y for p in P); zs=sorted(p.z for p in P); n=len(P)
    q=lambda L,f: L[min(n-1,int(f*n))]
    return mathutils.Vector((q(xs,.01),q(ys,.01),q(zs,.01))),mathutils.Vector((q(xs,.99),q(ys,.99),q(zs,.99)))
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.55,0.6,0.7,1); w.node_tree.nodes['Background'].inputs[1].default_value=0.6
sun=bpy.data.objects.new('sun',bpy.data.lights.new('sun','SUN')); sc.collection.objects.link(sun); sun.data.energy=4; sun.rotation_euler=(math.radians(50),0,math.radians(40))
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=50
sc.render.engine=eng; sc.render.resolution_x=640; sc.render.resolution_y=420
if eng=='CYCLES': sc.cycles.samples=24; sc.cycles.device='CPU'
sc.view_settings.view_transform='Standard'
frames=[sc.frame_start]
if acts:
    a0=acts[0] if len(a)<4 else [x for x in acts if x.name.startswith(a[3])][0]
    if arm: 
        arm[0].animation_data_create(); arm[0].animation_data.action=a0
    f0,f1=a0.frame_range; frames=[int(f0+(f1-f0)*k/3) for k in range(4)]
for i,f in enumerate(frames):
    sc.frame_set(f)
    mn,mx=bbox(); c=(mn+mx)/2; r=(mx-mn).length
    for j,(az,el) in enumerate([(35,12),(90,5)] if i==0 else [(35,12)]):
        cam.data.clip_start=r*0.01; cam.data.clip_end=r*20; d=r*1.5; cam.location=c+mathutils.Vector((math.cos(math.radians(az))*math.cos(math.radians(el)),-math.sin(math.radians(az))*math.cos(math.radians(el)),math.sin(math.radians(el))))*d*1.3
        cam.rotation_euler=(c-cam.location).to_track_quat('-Z','Y').to_euler()
        sc.render.filepath='%s_f%d_%d.png'%(out,i,j); bpy.ops.render.render(write_still=True)
print('BBOX',mn,mx)
