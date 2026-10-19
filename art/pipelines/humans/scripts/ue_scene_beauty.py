"""Presentation shots (sunset, HDRI sky, fog, manual exposure) -> maps /Game/Proto/L_B_<shot>. env HUM_SHOTS=comma list"""
import sys,os,random; sys.path.append('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts')
import importlib, ue_common as U, ue_props as PR; importlib.reload(U); importlib.reload(PR)
import unreal
V=unreal.Vector; EAS=U.EAS
want=[s for s in os.environ.get('HUM_SHOTS','hayk,bel,ara,shamiram,fallen,wide').split(',') if s]
def cam_dof(focus_cm, fstop=2.8):
    if os.environ.get('HUM_DOF','0')!='1': return   # cinematic DOF renders stripes/magenta garbage on Iris Xe (Vulkan)
    for a in EAS.get_all_level_actors():
        if isinstance(a, unreal.CameraActor):
            c=a.camera_component; ps=c.get_editor_property('post_process_settings')
            for k,v in (('depth_of_field_focal_distance',focus_cm),('depth_of_field_fstop',fstop),('depth_of_field_sensor_width',36.0)):
                ps.set_editor_property('override_'+k,True); ps.set_editor_property(k,v)
            c.set_editor_property('post_process_settings',ps); c.set_editor_property('post_process_blend_weight',1.0)
def soldier(name, clip, loc, yaw, play=True, spear=True, t=None):
    a=U.spawn(U.skm(name), U.anim(name,clip), -random.random() if t is None else t, loc, yaw+random.uniform(-6,6), playing=play, rate=random.uniform(0.9,1.1))
    c=a.skeletal_mesh_component
    for i in range(3): c.set_default_custom_primitive_data_float(i, random.random())
    if spear and clip=='MM_Idle':
        PR.attach(a, PR.SPEAR, unreal.load_asset(U.anim(name,clip)), 0.0, 'hand_r', 230.0, V(0,0.05,1), V(1,0,0), grip_frac=0.42)
    return a
def mound(loc, sx=7, sz=3.2):
    m=EAS.spawn_actor_from_class(unreal.StaticMeshActor, loc); m.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
    m.set_actor_scale3d(V(sx,sx,sz)); m.static_mesh_component.set_material(0,U.ground_material())
random.seed(3)
if 'hayk' in want:   # Hayk draws the bow, his clan behind him, low sun from the side-front
    U.new_map('L_B_hayk'); cl=V(360,250,165); U.env(cl, U.look(cl,V(0,30,140)), 40, sun_pitch=-7, sun_yaw=230); cam_dof(300, 2.0)
    clip='MF_Rifle_Idle_ADS'; h=U.spawn(U.skm('hayk'), U.anim('hayk',clip), 0.0, V(0,0,0), 0, playing=True)
    PR.attach(h, PR.BOW, unreal.load_asset(U.anim('hayk',clip)), 0.0, 'hand_l', 165.0, V(0,0.17,0.985), V(0,1,0), depth_sign=1)
    for i in range(14): soldier('armsoldc', 'MM_Idle', V(-260-(i//7)*130+random.uniform(-25,25), -330+(i%7)*110+random.uniform(-20,20), 0), 0)
    U.save_map()
if 'bel' in want:    # Bel on his hill above the Babylonian ranks
    U.new_map('L_B_bel'); cl=V(-1000,-380,150); U.env(cl, U.look(cl,V(0,0,230)), 38, sun_pitch=-7, sun_yaw=60); cam_dof(700, 4.0)
    mound(V(0,0,-150)); U.spawn(U.skm('bel'), U.anim('bel','MM_Idle'), 0.3, V(0,0,158), 180, playing=True)
    for i in range(16): soldier('babsoldc', 'MM_Idle', V(-330-(i//8)*120+random.uniform(-20,20), -420+(i%8)*115+random.uniform(-15,15), 0), 180)
    U.save_map()
if 'ara' in want:    # Ara the Beautiful with his guard
    U.new_map('L_B_ara'); cl=V(330,-170,185); U.env(cl, U.look(cl,V(0,0,165)), 36, sun_pitch=-7, sun_yaw=150); cam_dof(300, 2.0)
    U.spawn(U.skm('ara'), U.anim('ara','MM_Idle'), 0.4, V(0,0,0), 10, playing=True)
    for i in range(8): soldier('armsoldc', 'MM_Idle', V(-250-(i//4)*130, -260+(i%4)*170+random.uniform(-20,20), 0), 0)
    U.save_map()
if 'shamiram' in want:   # Queen Shamiram with Assyrian guards
    U.new_map('L_B_shamiram'); cl=V(330,150,140); U.env(cl, U.look(cl,V(0,0,125)), 38, sun_pitch=-7, sun_yaw=220); cam_dof(330, 2.0)
    U.spawn(U.skm('shamiram'), U.anim('shamiram','MM_Idle'), 0.4, V(0,0,0), 20, playing=True)
    for y in (-180,180): soldier('babsoldc', 'MM_Idle', V(-160, y, 0), 0)
    U.save_map()
if 'fallen' in want:   # Ara's battlefield: fallen heroes laid on the ground (posed mesh rolled +-90 deg about its lateral axis).
    # NOTE: the 5.8 template "MM_Death_*" clips never reach the ground (pelvis stays 82-93 cm) and editor-placed ragdolls fell
    # through in this test, so bodies are posed lying instead.
    U.new_map('L_B_fallen'); cl=V(-560,-420,300); U.env(cl, U.look(cl,V(150,0,20)), 45, sun_pitch=-6, sun_yaw=40)
    def lying(name, clip, t, loc, yaw, face_up=True):
        a=U.spawn(U.skm(name), U.anim(name,clip), t, loc, 0, playing=False)
        a.set_actor_rotation(unreal.Rotator(roll=(90 if face_up else -90), pitch=0, yaw=yaw), False)
        a.set_actor_location(loc+V(0,0,14), False, False)
        c=a.skeletal_mesh_component
        for i in range(3): c.set_default_custom_primitive_data_float(i, random.random())
        return a
    lying('ara', 'MM_HitReact_Front_Hvy_01', -0.1, V(80,0,0), 30, False)
    for i in range(18):
        n=random.choice(['armsoldc','armsoldc','babsoldc'])
        lying(n, random.choice(['MM_Idle','MM_HitReact_Front_Hvy_01','MF_Unarmed_Walk_Fwd']), -random.random(), V(random.uniform(-150,750), random.uniform(-520,520), 0), random.uniform(0,360), random.random()<0.5)
    for i in range(6): soldier('babsoldc', 'MM_Idle', V(950+random.uniform(-50,50), -300+i*120, 0), 180)
    U.save_map()
if 'wide' in want:   # wide battle overview
    U.new_map('L_B_wide'); cl=V(-1500,-1600,650); U.env(cl, U.look(cl,V(800,0,0)), 45, sun_pitch=-7, sun_yaw=200)
    for side,(name,x0,yaw,dx) in enumerate((('armsoldc',0,0,-1),('babsoldc',1500,180,1))):
        for k in range(60):
            r,c=k//12,k%12; soldier(name, random.choice(['MM_Idle','MM_Idle','MF_Unarmed_Walk_Fwd']), V(x0+dx*r*120+random.uniform(-20,20),(c-5.5)*95+random.uniform(-15,15),0), yaw)
    h=U.spawn(U.skm('hayk'), U.anim('hayk','MF_Rifle_Idle_ADS'), 0.0, V(170,40,0), 0, playing=True)
    PR.attach(h, PR.BOW, unreal.load_asset(U.anim('hayk','MF_Rifle_Idle_ADS')), 0.0, 'hand_l', 165.0, V(0,0.17,0.985), V(0,1,0), depth_sign=1)
    mound(V(2350,0,-150)); U.spawn(U.skm('bel'), U.anim('bel','MM_Idle'), 0.3, V(2350,0,158), 180, playing=True)
    U.save_map()
U.log('beauty %s'%want)
