"""shared helpers for the humans scratch project (scene env, ground, character spawn)."""
import unreal, os, math
def log(m): unreal.log_warning('HUM '+str(m))
EAL=unreal.EditorAssetLibrary; AT=unreal.AssetToolsHelpers.get_asset_tools(); ML=unreal.MaterialEditingLibrary
LES=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
HUM='/Game/Twilight/Humans'
MANNY='/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
MA='/Game/Characters/Mannequins/Anims/'
def skm(n): N=n[0].upper()+n[1:]; return '%s/%s/Mesh/%s/SkeletalMeshes/%s'%(HUM,N,n,n)
def anim(n,clip): N=n[0].upper()+n[1:]; return '%s/%s/Anims/%s'%(HUM,N,clip)

def mic(path, parent, scalars={}, vectors={}, textures={}):
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    d,n=path.rsplit('/',1)
    m=AT.create_asset(n,d,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
    m.set_editor_property('parent',unreal.load_asset(parent))
    for k,v in scalars.items(): ML.set_material_instance_scalar_parameter_value(m,k,v)
    for k,v in vectors.items(): ML.set_material_instance_vector_parameter_value(m,k,unreal.LinearColor(*v))
    for k,v in textures.items(): ML.set_material_instance_texture_parameter_value(m,k,unreal.load_asset(v) if isinstance(v,str) else v)
    ML.update_material_instance(m); EAL.save_loaded_asset(m); return m

def import_tex(fn, dest, srgb=True, normal=False):
    name='T_'+os.path.splitext(os.path.basename(fn))[0]
    if EAL.does_asset_exist(dest+'/'+name): return unreal.load_asset(dest+'/'+name)
    t=unreal.AssetImportTask(); t.filename=fn; t.destination_path=dest; t.destination_name=name; t.automated=True; t.save=True; t.replace_existing=True
    AT.import_asset_tasks([t]); tex=unreal.load_asset(dest+'/'+name)
    if normal: tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_NORMALMAP); tex.set_editor_property('srgb',False)
    elif not srgb: tex.set_editor_property('srgb',False); tex.set_editor_property('compression_settings',unreal.TextureCompressionSettings.TC_MASKS)
    EAL.save_loaded_asset(tex); return tex

def ground_material():
    path='/Game/Twilight/Env/M_GroundPH'
    if EAL.does_asset_exist(path): return unreal.load_asset(path)
    D='/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/dl/ph/'
    td=import_tex(D+'aerial_grass_rock_diff_2k.jpg','/Game/Twilight/Env/Tex')
    tn=import_tex(D+'aerial_grass_rock_nor_gl_2k.jpg','/Game/Twilight/Env/Tex',normal=True)
    tr=import_tex(D+'aerial_grass_rock_rough_2k.jpg','/Game/Twilight/Env/Tex',srgb=False)
    m=AT.create_asset('M_GroundPH','/Game/Twilight/Env',unreal.Material,unreal.MaterialFactoryNew())
    E=lambda cls,x,y: ML.create_material_expression(m,cls,x,y)
    wp=E(unreal.MaterialExpressionWorldPosition,-1400,0)
    msk=E(unreal.MaterialExpressionComponentMask,-1250,0); msk.set_editor_property('r',True); msk.set_editor_property('g',True); ML.connect_material_expressions(wp,'',msk,'')
    sc=E(unreal.MaterialExpressionScalarParameter,-1250,150); sc.set_editor_property('parameter_name','Tile'); sc.set_editor_property('default_value',1/600.)
    uv=E(unreal.MaterialExpressionMultiply,-1100,0); ML.connect_material_expressions(msk,'',uv,'A'); ML.connect_material_expressions(sc,'',uv,'B')
    sc2=E(unreal.MaterialExpressionConstant,-1250,250); sc2.set_editor_property('r',0.23)
    uv2=E(unreal.MaterialExpressionMultiply,-1100,200); ML.connect_material_expressions(uv,'',uv2,'A'); ML.connect_material_expressions(sc2,'',uv2,'B')
    def samp(tex,y,uvn,st=None):
        s=E(unreal.MaterialExpressionTextureSample,-850,y); s.set_editor_property('texture',tex)
        if st: s.set_editor_property('sampler_type',st)
        ML.connect_material_expressions(uvn,'',s,'UVs'); return s
    d1=samp(td,-300,uv); d2=samp(td,-50,uv2)
    lp=E(unreal.MaterialExpressionMultiply,-600,-200); ML.connect_material_expressions(d1,'RGB',lp,'A'); ML.connect_material_expressions(d2,'RGB',lp,'B')
    k=E(unreal.MaterialExpressionConstant,-700,-100); k.set_editor_property('r',2.2)
    lp2=E(unreal.MaterialExpressionMultiply,-450,-200); ML.connect_material_expressions(lp,'',lp2,'A'); ML.connect_material_expressions(k,'',lp2,'B')
    tint=E(unreal.MaterialExpressionVectorParameter,-450,-350); tint.set_editor_property('parameter_name','Tint'); tint.set_editor_property('default_value',unreal.LinearColor(1,0.95,0.85,1))
    bc=E(unreal.MaterialExpressionMultiply,-250,-200); ML.connect_material_expressions(lp2,'',bc,'A'); ML.connect_material_expressions(tint,'',bc,'B')
    n=samp(tn,200,uv,unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    r=samp(tr,450,uv,unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    ML.connect_material_property(bc,'',unreal.MaterialProperty.MP_BASE_COLOR)
    ML.connect_material_property(n,'RGB',unreal.MaterialProperty.MP_NORMAL)
    ML.connect_material_property(r,'R',unreal.MaterialProperty.MP_ROUGHNESS)
    sp=E(unreal.MaterialExpressionConstant,-250,500); sp.set_editor_property('r',0.3); ML.connect_material_property(sp,'',unreal.MaterialProperty.MP_SPECULAR)
    ML.recompile_material(m); EAL.save_loaded_asset(m); return m

def env(cam_loc, cam_rot, fov=50., sun_pitch=-7., sun_yaw=265., ground=True, exposure=None):
    sky_m=mic('/Game/Twilight/Env/MI_SkyHDRI_Natural','/Game/Twilight/Materials/M_SkyHDRI',{'Exposure':1.0,'Yaw':0.0},{'ZenithTint':(1,1,1,1),'HorizonTint':(1,1,1,1)})
    dome=EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,0)); dome.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
    dome.set_actor_scale3d(unreal.Vector(4000,4000,4000)); dome.static_mesh_component.set_material(0,sky_m); dome.static_mesh_component.set_editor_property('cast_shadow',False)
    sun=EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,500), unreal.Rotator(roll=0,pitch=sun_pitch,yaw=sun_yaw))
    lc=sun.light_component; lc.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    lc.set_intensity(float(os.environ.get('HUM_SUN','9'))); lc.set_light_color(unreal.LinearColor(1.0,0.62,0.38,1))
    lc.set_editor_property('dynamic_shadow_distance_movable_light',float(os.environ.get('HUM_SHADOWDIST','6000')))
    lc.set_editor_property('dynamic_shadow_cascades',int(os.environ.get('HUM_CASCADES','3')))
    sl=EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0,0,300)); s=sl.light_component
    s.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    s.set_editor_property('source_type',unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    s.set_editor_property('cubemap',unreal.load_asset('/Game/Twilight/Env/HDRI/belfast_sunset_puresky_2k'))
    s.set_intensity(float(os.environ.get('HUM_SKY','1.0')))
    fog=EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0,0,-200)); f=fog.component
    f.set_editor_property('fog_density',float(os.environ.get('HUM_FOG','0.02'))); f.set_editor_property('fog_height_falloff',0.2)
    f.set_editor_property('fog_inscattering_luminance',unreal.LinearColor(0.45,0.36,0.36,1))
    f.set_editor_property('directional_inscattering_luminance',unreal.LinearColor(1.0,0.5,0.25,1))
    ppv=EAS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0,0,0)); ppv.set_editor_property('unbound',True)
    ps=ppv.get_editor_property('settings')
    ex=exposure if exposure is not None else float(os.environ.get('HUM_EXPOSURE','-0.5'))
    for k,v in (('auto_exposure_method',unreal.AutoExposureMethod.AEM_MANUAL),('auto_exposure_bias',ex),('auto_exposure_apply_physical_camera_exposure',False),
                ('bloom_intensity',0.8),('vignette_intensity',0.4),('ambient_occlusion_intensity',0.6)):
        ps.set_editor_property('override_'+k,True); ps.set_editor_property(k,v)
    ppv.set_editor_property('settings',ps)
    if ground:
        g=EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0,0,0)); g.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
        g.set_actor_scale3d(unreal.Vector(800,800,1)); g.static_mesh_component.set_material(0,ground_material())
    cam=EAS.spawn_actor_from_class(unreal.CameraActor, cam_loc, cam_rot)
    cam.camera_component.set_editor_property('field_of_view',fov); cam.camera_component.set_editor_property('constrain_aspect_ratio',False)
    cam.set_editor_property('auto_activate_for_player',unreal.AutoReceiveInput.PLAYER0)
    EAS.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-20000,0,100))

def look(frm, to): return unreal.MathLibrary.find_look_at_rotation(frm,to)

def spawn(mesh, anim_path, t, loc, yaw=0., mats=None, scale=1.0, playing=False, rate=1.0):
    """character standing with feet at loc.z, facing 'yaw' (mesh forward is +Y -> rotate -90)."""
    a=EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, loc, unreal.Rotator(roll=0,pitch=0,yaw=yaw-90))
    a.set_actor_scale3d(unreal.Vector(scale,scale,scale))
    c=a.skeletal_mesh_component
    c.set_skinned_asset_and_update(unreal.load_asset(mesh))
    for i,m in enumerate(mats or []):
        if m is not None: c.set_material(i,m)
    if anim_path:
        an=unreal.load_asset(anim_path)
        if t<0: t=-t*an.get_play_length()
        c.set_editor_property('animation_mode',unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        pd=unreal.SingleAnimationPlayData(); pd.set_editor_property('anim_to_play',an); pd.set_editor_property('saved_looping',True)
        pd.set_editor_property('saved_playing',playing); pd.set_editor_property('saved_position',t); pd.set_editor_property('saved_play_rate',rate)
        c.set_editor_property('animation_data',pd)
    return a

def new_map(name):
    """(re)create /Game/Proto/<name>: an existing map is loaded and emptied (new_level refuses to overwrite)."""
    path='/Game/Proto/'+name
    if EAL.does_asset_exist(path):
        LES.load_level(path)
        acts=EAS.get_all_level_actors()
        if acts: EAS.destroy_actors(acts)
        log('reuse %s (cleared %d actors)'%(path,len(acts)))
    else:
        ok=LES.new_level(path); log('new_level %s %s'%(path,ok))
    return path
def save_map(): LES.save_current_level()
