"""UE editor python: look-dev maps /Game/Proto/L_FH_* (hero rigged exactly like AVahagnCharacter: pivot pitch, mesh offset/scale,
   Glow light) under a low warm sunset. FH_MAPS=Menu,Chase,Front,Close,Orig selects maps."""
import sys; sys.path.insert(0,'/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto3/firehair_strands/deliver/scripts')
from fh_common import *
import math
MAPS=os.environ.get('FH_MAPS','Menu,Chase,Front,Close,Orig').split(',')
SUNYAW=float(os.environ.get('FH_SUNYAW','215'))
C=V(0,0,0)
def boom_cam(ctrl_pitch, yaw, arm, off):
    r=unreal.Rotator(roll=0,pitch=ctrl_pitch,yaw=yaw)
    loc=C+r.transform_vector(V(-arm,0,0)) if hasattr(r,'transform_vector') else None
    return r
def rotv(r, v): return unreal.MathLibrary.greater_greater_vector_rotator(v, r)   # rotate vector by rotator
def cam_from_boom(pitch, yaw, arm, off):
    r=unreal.Rotator(roll=0,pitch=pitch,yaw=yaw)
    return C+rotv(r,V(-arm,0,0))+rotv(r,off), r
def head_pos(pitch):   # approximate head world pos for framing (head bone at 186.5 cm * .86 above mesh origin, mesh origin at -92)
    piv=unreal.Rotator(roll=0,pitch=pitch,yaw=0); return C+rotv(piv,V(0,0,-92+186.5*0.86+8))
def head_world(a):
    tmp=EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, V(0,0,0)); tmp.skeletal_mesh_component.set_skinned_asset_and_update(unreal.load_asset(HERO))
    hc=tmp.skeletal_mesh_component.get_socket_transform('head', unreal.RelativeTransformSpace.RTS_COMPONENT); EAS.destroy_actor(tmp)
    h=unreal.MathLibrary.transform_location(a.get_actor_transform(), hc.translation); log('head %s'%h); return h
for m in MAPS:
    new_map('L_FH_'+m)
    if m in ('Menu','Orig','MenuNoHair','MenuNoLight','OrigFx'):   # *No*/OrigFx: perf isolation variants
        a=spawn_hero(C, pitch=-20, anim='MM_Idle', t=0.3, fire=(m not in ('Orig','OrigFx')), hair=(m!='MenuNoHair'), light=(m=='Menu'))
        if m=='OrigFx':   # stand-in for the game's always-on hand flames (translucent particles): a small translucent sphere at the right hand
            fx=EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(0,0,0)); fx.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
            fx.static_mesh_component.set_material(0, unreal.load_asset(FH+'/Materials/MI_FH_FireStrand')); fx.set_actor_scale3d(V(0.1,0.1,0.1))
            fx.static_mesh_component.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
            fx.attach_to_actor(a,'hand_r',unreal.AttachmentRule.SNAP_TO_TARGET,unreal.AttachmentRule.SNAP_TO_TARGET,unreal.AttachmentRule.KEEP_WORLD,False); h=head_world(a)
        cl=h+V(300,0,-20); env(cl, look(cl,h+V(0,0,-22)), fov=40., sun_yaw=SUNYAW)
    elif m in ('Chase','ChaseOrig'):
        cl,r=cam_from_boom(-12., 0., 560., V(0,85,110)); env(cl, r, fov=88., sun_yaw=SUNYAW)
        spawn_hero(C, pitch=-62, anim='MM_Fall_Loop', t=0.3, flight_wind=True, fire=(m=='Chase'))
    elif m=='ChaseSide':   # diagnostic: the flying pose from the side
        a=spawn_hero(C, pitch=-62, anim='MM_Fall_Loop', t=0.3, flight_wind=True); h=head_world(a)
        cl=h+V(-40,-260,40); env(cl, look(cl,h+V(-30,0,0)), fov=50., sun_yaw=SUNYAW)
    elif m=='Front':
        cl,r=cam_from_boom(-18., 180., 560., V(0,0,70)); env(cl, r, fov=88., sun_yaw=SUNYAW)
        spawn_hero(C, pitch=-20, anim='MM_Idle', t=0.3)
    elif m=='Close':
        a=spawn_hero(C, pitch=-20, anim='MM_Idle', t=0.3); h=head_world(a)
        f=float(os.environ.get('FH_CLOSE','150')); cl=h+V(0.75*f,-0.66*f,-2); env(cl, look(cl,h+V(8,0,3)), fov=40., sun_yaw=SUNYAW)
    save_map(); log('map %s cam %s'%(m,cl))
sm=unreal.load_asset(FH+'/Meshes/SM_VahagnFireHair')
for fn in ('get_num_uv_channels','get_num_vertices','get_num_triangles'):
    try: log('%s %s'%(fn,getattr(sm,fn)(0)))
    except Exception as e: log('%s %s'%(fn,e))
