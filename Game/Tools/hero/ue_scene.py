"""Build comparison maps in the scratch project: sunset key light (5 deg elevation), HDRI skylight + dome, height fog,
manual exposure. Characters are listed in SHOTS below; each entry = (label, skeletal mesh, materials, anim, time, pitch).
env HERO_SHOTS=comma list of shot names to (re)build (default all)."""
import unreal, os, math
def log(m): unreal.log_warning('HERO '+str(m))
EAL=unreal.EditorAssetLibrary; AT=unreal.AssetToolsHelpers.get_asset_tools()
LES=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
H='/Game/Twilight/Hero'
MANNY='/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
SPARTAN=H+'/Mesh/spartan_vahagn/SkeletalMeshes/spartan_vahagn'
MA='/Game/Characters/Mannequins/Anims/'
EXPOSURE=float(os.environ.get('HERO_EXPOSURE','-0.5'))

def mic(path, parent, scalars={}, vectors={}, textures={}):
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    d,n=path.rsplit('/',1)
    m=AT.create_asset(n,d,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    ML=unreal.MaterialEditingLibrary
    m.set_editor_property('parent',unreal.load_asset(parent))
    for k,v in scalars.items(): ML.set_material_instance_scalar_parameter_value(m,k,v)
    for k,v in vectors.items(): ML.set_material_instance_vector_parameter_value(m,k,unreal.LinearColor(*v))
    for k,v in textures.items(): ML.set_material_instance_texture_parameter_value(m,k,unreal.load_asset(v))
    ML.update_material_instance(m); EAL.save_loaded_asset(m); return m

def bronze_mats():
    T='/Game/Characters/Mannequins/Textures/Manny/'
    a=mic(H+'/Cmp/MI_Hero_Bronze',  '/Game/Twilight/Materials/M_Hero',{'EmissiveIntensity':1.2,'RimIntensity':1.0})
    b=mic(H+'/Cmp/MI_Hero_Bronze2', '/Game/Twilight/Materials/M_Hero',{'EmissiveIntensity':1.2,'RimIntensity':1.0},
          textures={'NormalTex':T+'T_Manny_02_BN','MRATex':T+'T_Manny_02_MRA','DiffTex':T+'T_Manny_02_D'})
    return [a,b]

def spawn_char(mesh, mats, anim, t, loc, yaw=0., pitch=0., roll=0.):
    # emulate the game: capsule centre at loc, Pivot rotated (pitch,0,roll) * actor yaw, mesh at (0,0,-92) yaw -90
    pivot=unreal.Transform(loc, unreal.Rotator(roll=roll,pitch=pitch,yaw=yaw), unreal.Vector(1,1,1))
    rel=unreal.Transform(unreal.Vector(0,0,-92), unreal.Rotator(roll=0,pitch=0,yaw=-90), unreal.Vector(1,1,1))
    w=unreal.MathLibrary.compose_transforms(rel,pivot)
    a=EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, w.translation, w.rotation.rotator())
    c=a.skeletal_mesh_component
    c.set_skinned_asset_and_update(unreal.load_asset(mesh)) if hasattr(c,'set_skinned_asset_and_update') else c.set_editor_property('skeletal_mesh_asset',unreal.load_asset(mesh))
    for i,m in enumerate(mats or []):
        if m is not None: c.set_material(i,m)
    an=unreal.load_asset(anim)
    if t<0: t=-t*an.get_play_length()     # negative t = fraction of the clip
    c.set_editor_property('animation_mode',unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    pd=unreal.SingleAnimationPlayData(); pd.set_editor_property('anim_to_play',an); pd.set_editor_property('saved_looping',True)
    pd.set_editor_property('saved_playing',False); pd.set_editor_property('saved_position',t)
    c.set_editor_property('animation_data',pd)
    c.set_editor_property('cast_shadow',True)
    return a

def env(cam_loc, cam_rot, fov=50.):
    sky_m=mic(H+'/Cmp/MI_SkyHDRI_Natural','/Game/Twilight/Materials/M_SkyHDRI',{'Exposure':1.0,'Yaw':0.0},{'ZenithTint':(1,1,1,1),'HorizonTint':(1,1,1,1)})
    dome=EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,0)); dome.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
    dome.set_actor_scale3d(unreal.Vector(4000,4000,4000)); dome.static_mesh_component.set_material(0,sky_m); dome.static_mesh_component.set_editor_property('cast_shadow',False)
    sun=EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,500), unreal.Rotator(roll=0,pitch=-5,yaw=265))
    lc=sun.light_component; lc.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    lc.set_intensity(float(os.environ.get('HERO_SUN','9'))); lc.set_light_color(unreal.LinearColor(1.0,0.62,0.38,1))
    lc.set_editor_property('dynamic_shadow_distance_movable_light',5000.0)
    sl=EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0,0,300)); s=sl.light_component
    s.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    s.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    s.set_editor_property('cubemap',unreal.load_asset('/Game/Twilight/Env/HDRI/belfast_sunset_puresky_2k'))
    s.set_intensity(float(os.environ.get('HERO_SKY','1.0')))
    fog=EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0,0,-2000)); f=fog.component
    f.set_editor_property('fog_density',0.01); f.set_editor_property('fog_height_falloff',0.2)
    f.set_editor_property('fog_inscattering_luminance',unreal.LinearColor(0.45,0.36,0.36,1))
    f.set_editor_property('directional_inscattering_luminance',unreal.LinearColor(1.0,0.5,0.25,1))
    ppv=EAS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0,0,0)); ppv.set_editor_property('unbound',True)
    ps=ppv.get_editor_property('settings')
    for k,v in (('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),('auto_exposure_bias',EXPOSURE),('auto_exposure_apply_physical_camera_exposure',False),
                ('bloom_intensity',1.0),('vignette_intensity',0.4),('ambient_occlusion_intensity',0.5)):
        ps.set_editor_property('override_'+k,True); ps.set_editor_property(k,v)
    ppv.set_editor_property('settings',ps)
    cam=EAS.spawn_actor_from_class(unreal.CameraActor, cam_loc, cam_rot)
    cam.camera_component.set_editor_property('field_of_view',fov)
    cam.set_editor_property('auto_activate_for_player',unreal.AutoReceiveInput.PLAYER0)
    EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-20000,0,0))

def look(frm, to):
    return unreal.MathLibrary.find_look_at_rotation(frm,to)

def build(name, chars, cam_loc, cam_tgt, fov=40.):
    path='/Game/Proto/'+name
    LES.new_level('/Game/Proto/L_Tmp_'+name) if False else None
    if EAL.does_asset_exist(path):
        LES.new_level('/Game/Proto/L_Scratch') if not EAL.does_asset_exist('/Game/Proto/L_Scratch') else LES.load_level('/Game/Proto/L_Scratch')
        EAL.delete_asset(path)
    ok=LES.new_level(path); log('new_level %s %s'%(path,ok))
    env(cam_loc, look(cam_loc,cam_tgt), fov)
    for c in chars: spawn_char(*c)
    LES.save_current_level(); log('map %s'%path)

bz=bronze_mats()
FALL=MA+'Unarmed/Jump/MM_Fall_Loop'; ATK=MA+'Unarmed/Attack/MM_Attack_01'
HA=H+'/Anims/'
want=os.environ.get('HERO_SHOTS','')
def mats_for(kind):
    if kind=='bronze': return bz
    if kind=='raw': return None
    return [unreal.load_asset(H+'/Cmp/MI_%s_%s'%(kind,s)) if EAL.does_asset_exist(H+'/Cmp/MI_%s_%s'%(kind,s)) else None for s in ('Body','Pants','Cross_strap','Leg_guard','Blanket','Helmet')]
KINDS=os.environ.get('HERO_KINDS','raw').split(',')
# lineup along Y; facing +X (towards the front camera)
def lineup(anim_m, anim_s, t, pitch, yaw):
    L=[(MANNY,bz,anim_m,t,unreal.Vector(0,-110*len(KINDS),0),yaw,pitch)]
    for i,k in enumerate(KINDS):
        L.append((SPARTAN,mats_for(k),anim_s,t,unreal.Vector(0,-110*len(KINDS)+220*(i+1),0),yaw,pitch))
    return L
W=110*(len(KINDS)+1)
if not want or 'front' in want:
    build('L_Front', lineup(ATK, HA+'MM_Attack_01', 0.45, 0, 0), unreal.Vector(380+W*1.2,-160,40), unreal.Vector(0,0,0), 40)
if not want or 'chase' in want:
    build('L_Chase', lineup(FALL, HA+'MM_Fall_Loop', 0.3, -50, 0), unreal.Vector(-420-W*1.1,120,260), unreal.Vector(0,0,0), 45)
if not want or 'side' in want:
    build('L_Side', lineup(FALL, HA+'MM_Fall_Loop', 0.3, -50, 90), unreal.Vector(380+W*1.2,0,60), unreal.Vector(0,0,0), 40)
if not want or 'portrait' in want:
    build('L_Portrait', [(SPARTAN,None,HA+'MM_Attack_01',0.45,unreal.Vector(0,0,0),90,0)], unreal.Vector(260,330,90), unreal.Vector(0,0,40), 35)
if not want or 'portfly' in want:
    build('L_PortFly', [(SPARTAN,None,HA+'MM_Fall_Loop',0.3,unreal.Vector(0,0,0),90,-50)], unreal.Vector(330,230,40), unreal.Vector(0,0,-10), 40)
if not want or 'cast' in want:   # casting pose, both lit from the sun side (+Y), facing the sun
    CH=MA+'Unarmed/Attack/MM_ChargedAttack'
    build('L_Cast', [(MANNY,bz,CH,-0.55,unreal.Vector(0,-130,0),70,0),(SPARTAN,None,HA+'MM_ChargedAttack',-0.55,unreal.Vector(0,130,0),70,0)],
          unreal.Vector(520,620,120), unreal.Vector(0,0,40), 42)
if 'perf' in want:   # one character, game chase distance (perf A/B with stat unit)
    build('L_PerfM', [(MANNY,bz,FALL,0.3,unreal.Vector(0,0,0),0,-50)], unreal.Vector(-560,85,110), unreal.Vector(0,0,0), 90)
    build('L_PerfS', [(SPARTAN,None,HA+'MM_Fall_Loop',0.3,unreal.Vector(0,0,0),0,-50)], unreal.Vector(-560,85,110), unreal.Vector(0,0,0), 90)
NAMES=['MM_Idle','MM_Fall_Loop','MM_Attack_01','MM_Attack_02','MM_ChargedAttack','MM_HitReact_Front_Lgt_01','MM_Death_Front_01']
SRC={'MM_Idle':'Unarmed/','MM_Fall_Loop':'Unarmed/Jump/','MM_Attack_01':'Unarmed/Attack/','MM_Attack_02':'Unarmed/Attack/','MM_ChargedAttack':'Unarmed/Attack/','MM_HitReact_Front_Lgt_01':'Rifle/HitReact/','MM_Death_Front_01':'Death/'}
FR=float(os.environ.get('HERO_FRAC','0.45'))
if not want or 'animrow' in want:
    L=[(SPARTAN,None,HA+n,-FR,unreal.Vector(0,-600+200*i,0),0,0) for i,n in enumerate(NAMES)]
    build('L_AnimRow', L, unreal.Vector(1500,0,60), unreal.Vector(0,0,20), 50)
if not want or 'animrowm' in want:
    L=[(MANNY,bz,MA+SRC[n]+n,-FR,unreal.Vector(0,-600+200*i,0),0,0) for i,n in enumerate(NAMES)]
    build('L_AnimRowM', L, unreal.Vector(1500,0,60), unreal.Vector(0,0,20), 50)
log('DONE')
