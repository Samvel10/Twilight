"""shared helpers for the FireHair scratch project: logging, material graph helpers (exec'd from the game's materials_build.py),
sunset scene env, character spawn."""
import unreal, os, math
MB='/var/www/html/Twilight/Game/Tools/materials_build.py'
exec(compile(open(MB).read().rsplit("\nmain()",1)[0], MB, 'exec'))   # G, setup_material, finish_material, save, asset_on_disk ... (read only)
EAL=unreal.EditorAssetLibrary; AT=unreal.AssetToolsHelpers.get_asset_tools(); ML=unreal.MaterialEditingLibrary
LES=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
HERO='/Game/Twilight/Hero/Mesh/spartan_vahagn/SkeletalMeshes/spartan_vahagn'
ANIMS='/Game/Twilight/Hero/Anims/'
FH='/Game/Twilight/FireHair'
def log(m): unreal.log_warning('FH '+str(m))
W_DIR='/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto3/firehair_strands/work'

def mic(path, parent, scalars={}, vectors={}, textures={}):
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    d,n=path.rsplit('/',1)
    m=AT.create_asset(n,d,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    ML.set_material_instance_parent(m, unreal.load_asset(parent) if isinstance(parent,str) else parent)
    for k,v in scalars.items(): ML.set_material_instance_scalar_parameter_value(m,k,float(v))
    for k,v in vectors.items(): ML.set_material_instance_vector_parameter_value(m,k,unreal.LinearColor(*(list(v)+[1.0])[:4]))
    for k,v in textures.items(): ML.set_material_instance_texture_parameter_value(m,k,unreal.load_asset(v) if isinstance(v,str) else v)
    ML.update_material_instance(m); EAL.save_loaded_asset(m); return m

# ------------------------------------------------------------------ scene
SUN_COLOR=(1.0,0.56,0.32)
def env(cam_loc, cam_rot, fov=50., sun_pitch=-8., sun_yaw=200., exposure=-0.5, ground=True, sun=9.0, sky=1.0):
    """low warm sunset: HDRI dome + sky light, sun 8 deg colour (1,.56,.32), height fog, manual exposure, ground plane."""
    sky_m=unreal.load_asset('/Game/Twilight/Env/MI_SkyHDRI_Natural')
    dome=EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,0)); dome.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
    dome.set_actor_scale3d(unreal.Vector(4000,4000,4000)); dome.static_mesh_component.set_material(0,sky_m); dome.static_mesh_component.set_editor_property('cast_shadow',False)
    s=EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,500), unreal.Rotator(roll=0,pitch=sun_pitch,yaw=sun_yaw))
    lc=s.light_component; lc.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    lc.set_intensity(sun); lc.set_light_color(unreal.LinearColor(*SUN_COLOR,1))
    lc.set_editor_property('dynamic_shadow_distance_movable_light',6000.); lc.set_editor_property('dynamic_shadow_cascades',3)
    sl=EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0,0,300)); c=sl.light_component
    c.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE); c.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    c.set_editor_property('cubemap',unreal.load_asset('/Game/Twilight/Env/HDRI/belfast_sunset_puresky_2k')); c.set_intensity(sky)
    fog=EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0,0,-200)); f=fog.component
    f.set_editor_property('fog_density',0.02); f.set_editor_property('fog_height_falloff',0.2)
    f.set_editor_property('fog_inscattering_luminance',unreal.LinearColor(0.45,0.36,0.36,1))
    f.set_editor_property('directional_inscattering_luminance',unreal.LinearColor(1.0,0.5,0.25,1))
    ppv=EAS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0,0,0)); ppv.set_editor_property('unbound',True)
    ps=ppv.get_editor_property('settings')
    for k,v in (('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),('auto_exposure_bias',exposure),('auto_exposure_apply_physical_camera_exposure',False),
                ('bloom_intensity',0.8),('vignette_intensity',0.4),('ambient_occlusion_intensity',0.6)):
        ps.set_editor_property('override_'+k,True); ps.set_editor_property(k,v)
    ppv.set_editor_property('settings',ps)
    if ground:
        g=EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,-400)); g.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
        g.set_actor_scale3d(unreal.Vector(800,800,1)); g.static_mesh_component.set_material(0,unreal.load_asset('/Game/Twilight/Env/M_GroundPH'))
    cam=EAS.spawn_actor_from_class(unreal.CameraActor, cam_loc, cam_rot)
    cam.camera_component.set_editor_property('field_of_view',fov); cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
    cam.set_editor_property('auto_activate_for_player',unreal.AutoReceiveInput.PLAYER0)
    EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-20000,0,100))
    return cam

def look(frm, to): return unreal.MathLibrary.find_look_at_rotation(frm,to)
def V(x,y,z): return unreal.Vector(x,y,z)

def hero_xf(center, yaw=0., pitch=0., roll=0.):
    """world transform of the hero mesh exactly as AVahagnCharacter builds it: capsule centre -> BodyPivot(pitch,roll)
    -> mesh at (0,0,-92) yaw -90, scale 0.86. Returns (location, rotator, scale)."""
    piv=unreal.Transform(center, unreal.Rotator(roll=roll,pitch=pitch,yaw=yaw), V(1,1,1))
    rel=unreal.Transform(V(0,0,-92), unreal.Rotator(roll=0,pitch=0,yaw=-90), V(0.86,0.86,0.86))
    t=unreal.MathLibrary.compose_transforms(rel,piv)
    return t

def spawn_hero(center, yaw=0., pitch=0., roll=0., anim='MM_Idle', t=0.3, playing=True, fire=True, helmet=False, flight_wind=None, hair=True, light=True):
    xf=hero_xf(center,yaw,pitch,roll)
    a=EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, xf.translation, xf.rotation.rotator())
    a.set_actor_scale3d(xf.scale3d)
    c=a.skeletal_mesh_component; c.set_skinned_asset_and_update(unreal.load_asset(HERO))
    if anim:
        an=unreal.load_asset(ANIMS+anim)
        c.set_editor_property('animation_mode',unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        pd=unreal.SingleAnimationPlayData(); pd.set_editor_property('anim_to_play',an); pd.set_editor_property('saved_looping',True)
        pd.set_editor_property('saved_playing',playing); pd.set_editor_property('saved_position',t*an.get_play_length()); pd.set_editor_property('saved_play_rate',1.0)
        c.set_editor_property('animation_data',pd)
    # the game's hero point light (AVahagnCharacter::Glow) on the pivot
    gl=EAS.spawn_actor_from_class(unreal.PointLight, center+V(0,0,20)); l=gl.point_light_component
    l.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE); l.set_editor_property('intensity_units',unreal.LightUnits.UNITLESS)
    l.set_intensity(9000.); l.set_light_color(unreal.LinearColor(1,0.42,0.12,1)); l.set_attenuation_radius(1500.); l.set_cast_shadows(False)
    if not fire: return a
    if not helmet: c.set_material(5, unreal.load_asset(FH+'/Materials/M_FH_Invisible'))
    c.set_material(0, unreal.load_asset(FH+'/Materials/MI_FH_VahagnBodyFire'))
    if not hair: return a
    # fire hair: static mesh authored in mesh component space, attached to 'head' with the inverse ref-pose head transform
    ref=unreal.load_asset(HERO); tmp=EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, V(0,0,0)); tmp.skeletal_mesh_component.set_skinned_asset_and_update(ref)
    head=tmp.skeletal_mesh_component.get_socket_transform('head', unreal.RelativeTransformSpace.RTS_COMPONENT); EAS.destroy_actor(tmp)
    inv=head.inverse()
    fh=EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(0,0,0)); sm=fh.static_mesh_component
    sm.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    sm.set_static_mesh(unreal.load_asset(FH+'/Meshes/SM_VahagnFireHair'))
    sm.set_editor_property('cast_shadow',False); sm.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    if flight_wind: sm.set_material(0, unreal.load_asset(FH+'/Materials/MI_FH_FireStrand_Flight'))
    sm.attach_to_component(c, 'head', unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, unreal.AttachmentRule.KEEP_RELATIVE, False)
    sm.set_relative_transform(inv, False, False)
    if not light: return a
    # fire light: the burning hair lights face/shoulders (no shadows, small radius)
    fl=EAS.spawn_actor_from_class(unreal.PointLight, V(0,0,0)); p=fl.point_light_component
    p.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE); p.set_editor_property('intensity_units',unreal.LightUnits.UNITLESS)
    p.set_intensity(float(os.environ.get('FH_LIGHT','700'))); p.set_light_color(unreal.LinearColor(1,0.45,0.15,1)); p.set_attenuation_radius(130.); p.set_cast_shadows(False)
    p.set_editor_property('source_radius',12.); p.set_editor_property('affect_translucent_lighting',False)
    p.attach_to_component(c,'head',unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,unreal.AttachmentRule.KEEP_RELATIVE,False)
    p.set_relative_transform(unreal.MathLibrary.compose_transforms(unreal.Transform(V(0,24,214),unreal.Rotator(),V(1,1,1)),inv),False,False)   # above the brow, in the flames
    return a

def new_map(name):
    path='/Game/Proto/'+name
    if EAL.does_asset_exist(path):
        LES.load_level(path); acts=EAS.get_all_level_actors()
        if acts: EAS.destroy_actors(acts)
    else: LES.new_level(path)
    return path
def save_map(): LES.save_current_level()
