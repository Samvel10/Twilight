"""Battle scene for look + perf: Hayk's clan (armsold: Saxon base + conical helmet, madder red, spear) vs Bel's army
(babsold: Roman base, bronze, lapis shields), Hayk (bow) in front, Bel (gold) on a mound.
env: HUM_N per side (30), HUM_URO (1), HUM_PLAY (1), HUM_SPEAR (1), HUM_SSHADOW (1 = soldiers cast shadows),
     HUM_MAP (L_Army), HUM_CAM (game|wide|low|hero), HUM_SUNP/HUM_SUNY"""
import sys,os,random; sys.path.append('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts')
import importlib, ue_common as U, ue_props as PR; importlib.reload(U); importlib.reload(PR)
import unreal
V=unreal.Vector; E=os.environ.get
N=int(E('HUM_N','30')); URO=E('HUM_URO','1')=='1'; PLAY=E('HUM_PLAY','1')=='1'; SPEAR=E('HUM_SPEAR','1')=='1'; SSH=E('HUM_SSHADOW','1')=='1'
MAP=E('HUM_MAP','L_Army'); CAM=E('HUM_CAM','game'); CROWD=E('HUM_CROWD','0')=='1'
random.seed(7)
U.new_map(MAP)
cams={'game':(V(-750,160,280),V(1200,0,90),60.),'wide':(V(-1100,-1300,700),V(900,0,0),50.),'low':(V(-300,330,95),V(1400,-60,160),45.),
      'hero':(V(420,330,175),V(150,40,150),40.),'bel':(V(1250,-250,170),V(2050,0,230),40.)}
cl,ct,fov=cams[CAM]
U.env(cl, U.look(cl,ct), fov, sun_pitch=float(E('HUM_SUNP','-8')), sun_yaw=float(E('HUM_SUNY','200')))
def setup(a, var, shadow=True):
    c=a.skeletal_mesh_component
    for i,v in enumerate(var): c.set_default_custom_primitive_data_float(i, v)
    if URO:
        c.set_editor_property('enable_update_rate_optimizations', True)
        c.set_editor_property('visibility_based_anim_tick_option', unreal.VisibilityBasedAnimTickOption.ONLY_TICK_POSE_WHEN_RENDERED)
    c.set_editor_property('cast_shadow', shadow)
spear_rel={}
def army(name, x0, facing, dx, clips, n, spear_clip=None):
    cols=10; k=0
    for r in range((n+cols-1)//cols):
        for ci in range(cols):
            if k>=n: return
            y=(ci-(cols-1)/2)*95+random.uniform(-18,18)+(r%2)*40; x=x0+dx*r*120+random.uniform(-20,20)
            clip=random.choice(clips)
            a=U.spawn(U.skm(name), U.anim(name,clip), -random.random(), V(x,y,0), facing+random.uniform(-8,8), playing=PLAY, rate=random.uniform(0.85,1.15))
            setup(a,[random.random(), random.random(), random.random()], SSH)
            if SPEAR and clip==spear_clip:
                an=unreal.load_asset(U.anim(name,clip))
                s,_=PR.attach(a, PR.SPEAR, an, 0.0, 'hand_r', 230.0, V(0,0.05,1), V(1,0,0), grip_frac=0.42)
                s.static_mesh_component.set_editor_property('cast_shadow', SSH)
            k+=1
army('armsoldc' if CROWD else 'armsold', 0, 0, -1, ['MM_Idle','MM_Idle','MM_Idle','MF_Unarmed_Walk_Fwd'], N, 'MM_Idle')
army('babsoldc' if CROWD else 'babsold', 1500, 180, 1, ['MM_Idle','MM_Idle','MF_Unarmed_Walk_Fwd'], N, 'MM_Idle')
if E('HUM_HEROES','1')=='1':
    clip='MF_Rifle_Idle_ADS'; h=U.spawn(U.skm('hayk'), U.anim('hayk',clip), 0.0, V(170,40,0), 0, playing=PLAY); setup(h,[0,0.5,0])
    PR.attach(h, PR.BOW, unreal.load_asset(U.anim('hayk',clip)), 0.0, 'hand_l', 165.0, V(0,0.17,0.985), V(0,1,0), depth_sign=1)
    m=U.EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(2050,0,-150)); m.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
    m.set_actor_scale3d(V(7,7,3.2)); m.static_mesh_component.set_material(0,U.ground_material())
    b=U.spawn(U.skm('bel'), U.anim('bel','MM_Idle'), 0.3, V(2050,0,158), 180, playing=PLAY); setup(b,[0,0.5,0])
U.save_map(); U.log('army map %s N=%d uro=%s spear=%s sshadow=%s crowd=%s'%(MAP,N,URO,SPEAR,SSH,CROWD))
