"""Build -game test maps for the Aralez (one camera per map). Commandlet:
UnrealEditor-Cmd AralezTest.uproject -run=pythonscript -script=ue_build_maps.py   env ARZ_SHOTS=comma list (default all), ARZ_CFG=json overrides"""
import unreal, os, math, json, random
def log(m): unreal.log_warning('ARZ ' + str(m))
EAL = unreal.EditorAssetLibrary; AT = unreal.AssetToolsHelpers.get_asset_tools(); ML = unreal.MaterialEditingLibrary
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
V = unreal.Vector; Rt = lambda p=0, y=0, r=0: unreal.Rotator(roll=r, pitch=p, yaw=y)
CFG = {'sun_yaw': 128.0, 'sun_pitch': -5.0, 'sun_lux': 9.0, 'sun_k': 3600.0, 'sky_int': 1.0, 'ev': -0.7, 'fog': 0.02, 'fog_falloff': 0.35,
       'halo': 0.0, 'rim': 0.18, 'feather_rim': 0.2, 'trans': 0.2, 'glow_light': 12.0, 'dome_exp': 1.0, 'probe': 0}
CFG.update(json.loads(os.environ.get('ARZ_CFG', '{}') or '{}'))
D = '/Game/Aralez'
DOG = D + '/Dog/SK_Aralez/SkeletalMeshes/SK_Aralez'; WING = D + '/Wings/SK_AralezWings/SkeletalMeshes/SK_AralezWings'
DA = D + '/Dog/SK_Aralez/SkeletalMeshes/SK_AralezAralez_'; WA = D + '/Wings/SK_AralezWings/SkeletalMeshes/SK_AralezWingsWing_'
HERO = '/Game/Twilight/Hero/Mesh/spartan_vahagn/SkeletalMeshes/spartan_vahagn'; HA = '/Game/Twilight/Hero/Anims/'
WING_OFFSET = V(0, 4.6, 5.5)   # wing root relative to chest_jnt (from SK_Aralez.glb.socket.txt, Blender->UE: (x,-y,z)*100)

def mic(path, parent, scalars={}, vectors={}, textures={}):
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    d, n = path.rsplit('/', 1)
    m = AT.create_asset(n, d, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    m.set_editor_property('parent', unreal.load_asset(parent))
    for k, v in scalars.items(): ML.set_material_instance_scalar_parameter_value(m, k, v)
    for k, v in vectors.items(): ML.set_material_instance_vector_parameter_value(m, k, unreal.LinearColor(*v))
    for k, v in textures.items(): ML.set_material_instance_texture_parameter_value(m, k, unreal.load_asset(v))
    ML.update_material_instance(m); EAL.save_loaded_asset(m); return m

def mats():
    M = {}
    M['sky'] = mic(D + '/Mat/MI_Sky', '/Game/Twilight/Materials/M_SkyHDRI', {'Exposure': CFG['dome_exp'], 'Yaw': 0.0, 'HorizonPower': 6.0},
                   {'ZenithTint': (1, 1, 1, 1), 'HorizonTint': (1, 1, 1, 1)}, {'SkyCube': D + '/HDRI/kloppenheim_06_puresky_4k'})
    M['fur'] = mic(D + '/Mat/MI_AralezFur', D + '/Mat/M_AralezFur', {'RimIntensity': CFG['rim'], 'DivineGlow': CFG.get('fur_glow', 0.03), 'Roughness': 0.78, 'Specular': 0.3,
                   'Desat': CFG.get('desat', 0.15), 'Brightness': CFG.get('fur_bright', 1.0)}, {'Tint': CFG.get('fur_tint', (1.0, 0.96, 0.9, 1)), 'RimColor': (1.0, 0.74, 0.42, 1)})
    M['feather'] = mic(D + '/Mat/MI_AralezFeather', D + '/Mat/M_AralezFeather', {'RimIntensity': CFG['feather_rim'], 'TransIntensity': CFG['trans']},
                       {'Tint': CFG.get('feather_tint', (1, 0.97, 0.92, 1)), 'RimColor': (1.0, 0.76, 0.45, 1)})
    M['shells'] = [mic(D + '/Mat/MI_AralezFurShell_%d' % i, D + '/Mat/M_AralezFurShell', {'ShellFrac': i / float(max(1, CFG.get('shells', 2))), 'FurLength': CFG.get('fur_len', 1.4), 'RimIntensity': CFG['rim']},
                       {'Tint': CFG.get('fur_tint', (1.0, 0.96, 0.9, 1))}) for i in range(1, int(CFG.get('shells', 2)) + 1)]
    M['halo'] = mic(D + '/Mat/MI_AralezHalo', D + '/Mat/M_AralezHalo', {'Intensity': CFG['halo'], 'Falloff': 2.5, 'FadeDistance': 60.0}, {'Color': (1.0, 0.70, 0.34, 1)})
    M['ground'] = unreal.load_asset(D + '/Mat/M_Ground')
    return M

def env(M):
    dome = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(0, 0, 0)); dome.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
    ds = CFG.get('dome_scale', 8000.0)   # 4 km radius encloses the 3.7 km terrain (domes >~20 km across get culled)
    dome.set_actor_scale3d(V(ds, ds, ds)); dome.static_mesh_component.set_material(0, M['sky']); dome.static_mesh_component.set_editor_property('cast_shadow', False)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, V(0, 0, 1000), Rt(CFG['sun_pitch'], CFG['sun_yaw']))
    lc = sun.light_component; lc.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
    lc.set_intensity(CFG['sun_lux']); lc.set_editor_property('use_temperature', True); lc.set_editor_property('temperature', CFG['sun_k'])
    lc.set_editor_property('dynamic_shadow_distance_movable_light', CFG.get('shadow_dist', 6000.0))
    lc.set_editor_property('enable_light_shaft_bloom', True); lc.set_editor_property('bloom_scale', 0.12); lc.set_editor_property('bloom_threshold', 2.0)
    lc.set_editor_property('bloom_tint', unreal.Color(255, 205, 150, 255))
    try: lc.set_editor_property('atmosphere_sun_light', False)
    except Exception: pass
    sl = EAS.spawn_actor_from_class(unreal.SkyLight, V(0, 0, 300)); s = sl.light_component
    s.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
    s.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    s.set_editor_property('cubemap', unreal.load_asset(D + '/HDRI/kloppenheim_06_puresky_4k'))
    s.set_intensity(CFG['sky_int'])
    fog = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, V(0, 0, -200)); f = fog.component
    f.set_editor_property('fog_density', CFG['fog']); f.set_editor_property('fog_height_falloff', CFG['fog_falloff'])
    f.set_editor_property('fog_inscattering_luminance', unreal.LinearColor(0.42, 0.40, 0.46, 1))
    f.set_editor_property('directional_inscattering_luminance', unreal.LinearColor(1.0, 0.55, 0.28, 1))
    f.set_editor_property('directional_inscattering_exponent', 8.0)
    f.set_editor_property('start_distance', CFG.get('fog_start', 1500.0))
    ppv = EAS.spawn_actor_from_class(unreal.PostProcessVolume, V(0, 0, 0)); ppv.set_editor_property('unbound', True)
    ps = ppv.get_editor_property('settings')
    for k, v in (('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL), ('auto_exposure_bias', CFG['ev']), ('auto_exposure_apply_physical_camera_exposure', False),
                 ('bloom_intensity', CFG.get('bloom', 0.45)), ('vignette_intensity', 0.35), ('ambient_occlusion_intensity', 0.6),
                 ('film_slope', 0.88), ('film_toe', 0.55), ('color_saturation', unreal.Vector4(1.05, 1.03, 1.0, 1.0))):
        try:
            ps.set_editor_property('override_' + k, True); ps.set_editor_property(k, v)
        except Exception as e: log('pp %s %s' % (k, e))
    ppv.set_editor_property('settings', ps)
    terr = [a.get_asset() for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(D + '/Env', recursive=True) if str(a.asset_class_path.asset_name) == 'StaticMesh'][0]
    g = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(0, 0, 0)); g.static_mesh_component.set_static_mesh(terr); g.static_mesh_component.set_material(0, M['ground']); g.static_mesh_component.set_editor_property('cast_shadow', CFG.get('terrain_shadow', False))
    EAS.spawn_actor_from_class(unreal.PlayerStart, V(0, 0, -30000))   # far above the terrain: the DefaultPawn sphere must not appear in shots

def add_ism(actor, mesh, transforms):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    h = sds.k2_gather_subobject_data_for_instance(actor)
    nh, fail = sds.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=h[0], new_class=unreal.InstancedStaticMeshComponent, blueprint_context=None))
    BFL = unreal.SubobjectDataBlueprintFunctionLibrary
    c = BFL.get_object(BFL.get_data(nh)); c.set_static_mesh(mesh)
    c.set_editor_property('cast_shadow', False)
    for t in transforms: c.add_instance(t, True)
    return c

def props_battlefield(center, radius=2500, seed=3):
    rnd = random.Random(seed)
    P = D + '/Props/'
    def sm(name):
        r = unreal.AssetRegistryHelpers.get_asset_registry()
        return [a.get_asset() for a in r.get_assets_by_path(P + name, recursive=True) if str(a.asset_class_path.asset_name) == 'StaticMesh']
    # grass clumps (instanced)
    grass = sm('grass_medium_01')
    holder = EAS.spawn_actor_from_class(unreal.Actor, center)
    for k, g in enumerate(grass[:8]):
        T = []
        for i in range(CFG.get('grass_n', 260)):
            a = rnd.uniform(0, 6.283); r = radius * rnd.random() ** 0.8
            p = V(center.x + math.cos(a) * r, center.y + math.sin(a) * r, 0)
            if abs(p.x) < 160 and abs(p.y) < 160: continue
            s = rnd.uniform(1.4, 2.6)
            T.append(unreal.Transform(p, Rt(0, rnd.uniform(0, 360)), V(s, s, s * rnd.uniform(0.8, 1.2))))
        add_ism(holder, g, T)
    # rocks
    for i, m in enumerate(sm('rock_moss_set_02')[:4] + sm('boulder_01')):
        for j in range(1):
            a = rnd.uniform(0, 6.283); r = rnd.uniform(500, radius)
            act = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(math.cos(a) * r, math.sin(a) * r, -5), Rt(0, rnd.uniform(0, 360)))
            act.static_mesh_component.set_static_mesh(m); s = rnd.uniform(0.7, 1.6) * (1.0 if 'boulder' not in m.get_name() else 0.5); act.set_actor_location(V(act.get_actor_location().x, act.get_actor_location().y, -25 * s), False, False); act.set_actor_scale3d(V(s, s, s))

def place_mesh(path, loc, rot, scale=1.0):
    m = path if not isinstance(path, str) else unreal.load_asset(path)
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, loc, rot); a.static_mesh_component.set_static_mesh(m); a.set_actor_scale3d(V(scale, scale, scale)); return a

def fallen(loc, yaw, anim='MM_Fall_Loop', frac=0.3, mats=None, lying=True):
    # the retargeted death clips end bent over (root motion lost) -> lay the fall pose on its back instead
    a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, V(loc.x, loc.y, loc.z + (18 if lying else 0)), Rt(0, yaw, -90 if lying else 0))
    c = a.skeletal_mesh_component; c.set_skinned_asset_and_update(unreal.load_asset(HERO))
    an = unreal.load_asset(HA + anim)
    c.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    pd = unreal.SingleAnimationPlayData(); pd.set_editor_property('anim_to_play', an); pd.set_editor_property('saved_looping', False)
    pd.set_editor_property('saved_playing', False); pd.set_editor_property('saved_position', an.get_play_length() * frac)
    c.set_editor_property('animation_data', pd); a.set_actor_scale3d(V(0.86, 0.86, 0.86))
    return a

def anim_comp(c, anim, t, playing=False, rate=1.0):
    an = unreal.load_asset(anim)
    c.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    pd = unreal.SingleAnimationPlayData(); pd.set_editor_property('anim_to_play', an); pd.set_editor_property('saved_looping', True)
    pd.set_editor_property('saved_playing', playing); pd.set_editor_property('saved_position', (t % 1.0) * an.get_play_length() if t >= 0 else -t)
    pd.set_editor_property('saved_play_rate', rate)
    c.set_editor_property('animation_data', pd)

def aralez(M, loc, rot, dog_anim, dog_t, wing_anim, wing_t, playing=False, halo=True):
    """dog faces +Y in its mesh space -> mesh yaw -90 so the ACTOR faces +X"""
    a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, loc, rot)
    c = a.skeletal_mesh_component; c.set_skinned_asset_and_update(unreal.load_asset(DOG)); c.set_material(0, M['fur'])
    c.set_editor_property('relative_rotation', Rt(0, -90))
    anim_comp(c, DA + dog_anim, dog_t, playing)
    c.set_editor_property('bounds_scale', 2.0)
    for sm in M['shells']:
        sh = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, loc, rot)
        shc = sh.skeletal_mesh_component; shc.set_skinned_asset_and_update(unreal.load_asset(DOG)); shc.set_material(0, sm)
        shc.set_editor_property('cast_shadow', False); shc.set_editor_property('bounds_scale', 2.0)
        anim_comp(shc, DA + dog_anim, dog_t, playing)
        sh.attach_to_component(c, '', unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.KEEP_WORLD, False)
    w = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, loc, rot)
    wc = w.skeletal_mesh_component; wc.set_skinned_asset_and_update(unreal.load_asset(WING)); wc.set_material(0, M['feather'])
    anim_comp(wc, WA + wing_anim, wing_t, playing)
    wc.set_editor_property('bounds_scale', 2.0)
    w.attach_to_component(c, 'chest_jnt', unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.KEEP_WORLD, False)
    w.root_component.set_editor_property('relative_location', WING_OFFSET); w.root_component.set_editor_property('relative_rotation', Rt(0, 0, 0))
    if halo and CFG['halo'] > 0:
        h = EAS.spawn_actor_from_class(unreal.StaticMeshActor, loc); h.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
        h.static_mesh_component.set_material(0, M['halo']); h.static_mesh_component.set_editor_property('cast_shadow', False)
        h.static_mesh_component.set_mobility(unreal.ComponentMobility.MOVABLE)
        h.attach_to_component(c, 'spine_2_jnt', unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.KEEP_WORLD, False)
        h.root_component.set_editor_property('relative_location', V(0, 8, 10)); h.root_component.set_editor_property('relative_rotation', Rt(0, 0, 0))
        h.set_actor_relative_scale3d(V(2.0, 2.8, 1.8)) if hasattr(h, 'set_actor_relative_scale3d') else h.root_component.set_editor_property('relative_scale3d', V(2.0, 2.8, 1.8))
    if CFG['glow_light'] > 0:
        pl = EAS.spawn_actor_from_class(unreal.PointLight, loc); l = pl.point_light_component
        l.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE); l.set_intensity(CFG['glow_light']); l.set_light_color(unreal.LinearColor(1.0, 0.72, 0.4, 1))
        l.set_editor_property('attenuation_radius', 450.0); l.set_editor_property('cast_shadows', False)
        pl.attach_to_component(c, 'spine_2_jnt', unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.KEEP_WORLD, False)
        pl.root_component.set_editor_property('relative_location', V(0, 0, 60))
    return a

def camera(loc, tgt, fov):
    rot = unreal.MathLibrary.find_look_at_rotation(loc, tgt)
    cam = EAS.spawn_actor_from_class(unreal.CameraActor, loc, rot)
    cam.camera_component.set_editor_property('field_of_view', fov)
    cam.camera_component.set_editor_property('constrain_aspect_ratio', False)
    cam.set_editor_property('auto_activate_for_player', unreal.AutoReceiveInput.PLAYER0)
    return cam

# -------------------------------------------------------------- shots
# battlefield centre at origin; the fallen hero lies at (0,0); sun towards -X (yaw 150 = light travels to +X-ish... set in CFG)
HERO_POS = V(60, -40, 2); HERO_YAW = 20.0
def stage(M):
    env(M); props_battlefield(V(0, 0, 0))
    fallen(HERO_POS, HERO_YAW)
    fallen(V(900, 700, 2), 140); fallen(V(-700, 1100, 2), 260); fallen(V(1500, -900, 2), 70)
    P = D + '/Props/'
    r = unreal.AssetRegistryHelpers.get_asset_registry()
    def first(n): return [a.get_asset() for a in r.get_assets_by_path(P + n, recursive=True) if str(a.asset_class_path.asset_name) == 'StaticMesh']
    sh = first('kite_shield'); sw = first('antique_estoc'); ax = first('wooden_axe')
    for i, (m, l, ro) in enumerate([(sh, V(-60, 90, 8), Rt(80, 30, 0)), (sw, V(130, 70, 3), Rt(0, 70, 90)), (ax, V(-150, -120, 4), Rt(0, 200, 90)),
                                    (sh, V(1000, 820, 8), Rt(80, 120, 0)), (sw, V(-650, 980, 3), Rt(0, 10, 90)), (sh, V(-300, 1500, 8), Rt(60, 220, 0))]):
        for mm in m: place_mesh(mm, l, ro, 1.0)
    if CFG['probe']:
        s = place_mesh('/Engine/BasicShapes/Sphere', V(0, 300, 120), Rt(), 1.0)
        pm = unreal.load_asset('/Engine/EngineDebugMaterials/M_SimpleUnlitTranslucent') if False else None

SHOTS = {
 # name: (dog anim, dog t, wing anim, wing t, aralez loc, aralez rot, cam loc, cam target, fov)
 'Fly5':    ('Glide', 0.30, 'Glide', 0.30, V(0, 0, 900), Rt(-8, 200, 6), None, None, 50),
 'Fly20':   ('Flap', 0.28, 'Flap', 0.28, V(0, 0, 1400), Rt(-14, 200, -8), None, None, 45),
 'FlapSeq': ('Flap', 0.0, 'Flap', 0.0, V(0, 0, 1000), Rt(-6, 200, 0), None, None, 45),
 'Desc60':  ('Glide', 0.6, 'Glide', 0.6, V(600, 300, 2600), Rt(-24, 210, 10), None, None, 45),
 'Land20':  ('Land', -0.55, 'Mantle', 0.5, V(-140, 120, 105), Rt(-4, 300, 0), None, None, 45),
 'Lick5':   ('Lick', 0.30, 'Fold', 0.40, V(-55, 110, 0), Rt(0, 300, 0), None, None, 45),
 'LickFace5': ('Lick', 0.30, 'Fold', 0.40, V(0, 0, 0), Rt(0, 0, 0), None, None, 45),
 'Field60': ('Lick', 0.30, 'Fold', 0.40, V(-55, 110, 0), Rt(0, 300, 0), None, None, 40),
}
SUN_AZ = CFG['sun_yaw'] - 180.0   # direction from the scene towards the sun
def polar(tgt, az, el, dist):
    a, e = math.radians(az), math.radians(el)
    return V(tgt.x + math.cos(a) * math.cos(e) * dist, tgt.y + math.sin(a) * math.cos(e) * dist, tgt.z + math.sin(e) * dist)
CAMS = {  # name: (cam az relative to the sun, elevation, distance, target offset z, fov)
    'Fly5': (125, 4, 520, 10, 50), 'FlapSeq': (70, 6, 900, 0, 45), 'Fly20': (55, -10, 2000, 0, 45), 'Desc60': (155, -18, 6000, 0, 40),
    'Land20': (75, 6, 2000, 60, 40), 'Lick5': (100, 16, 420, 30, 45), 'LickFace5': (35, 12, 380, 25, 42), 'Field60': (150, 7, 6000, 80, 40)}
def cam_for(name, aloc):
    az, el, dist, dz, fov = CAMS[name]
    t = V(aloc.x, aloc.y, aloc.z + dz); return polar(t, SUN_AZ + az, el, dist), t
def cam_for_old(name, aloc):
    if name == 'Fly5':    return V(aloc.x - 330, aloc.y + 380, aloc.z + 60), V(aloc.x, aloc.y, aloc.z + 20)
    if name == 'Fly20':   return V(aloc.x - 1500, aloc.y + 1300, aloc.z - 250), V(aloc.x, aloc.y, aloc.z)
    if name == 'Desc60':  return V(-4800, 2600, 170), V(aloc.x, aloc.y, aloc.z - 600)
    if name == 'Land20':  return V(1500, 1100, 260), V(-80, 60, 90)
    if name == 'Lick5':   return V(260, 360, 140), V(-20, 40, 50)
    if name == 'Field60': return V(4500, 3600, 900), V(-50, 50, 80)

if os.environ.get('ARZ_SKYPROBE'):
    M = mats(); LES.new_level(D + '/Maps/L_SkyProbe') if not EAL.does_asset_exist(D + '/Maps/L_SkyProbe') else None
    if EAL.does_asset_exist(D + '/Maps/L_SkyProbe'):
        LES.new_level(D + '/Maps/L_Scratch_sp'); EAL.delete_asset(D + '/Maps/L_SkyProbe'); LES.new_level(D + '/Maps/L_SkyProbe')
    env(M)
    cam = EAS.spawn_actor_from_class(unreal.CameraActor, V(0, 0, 300), Rt(89.9, 0, 0))
    cam.camera_component.set_editor_property('field_of_view', 170.0); cam.camera_component.set_editor_property('constrain_aspect_ratio', False)
    cam.set_editor_property('auto_activate_for_player', unreal.AutoReceiveInput.PLAYER0)
    LES.save_current_level(); log('skyprobe'); raise SystemExit
want = [s for s in (os.environ.get('ARZ_SHOTS') or ','.join(SHOTS)).split(',') if s]
M = mats()
for name in want:
    da, dt, wa, wt, aloc, arot, _, _, fov = SHOTS[name]
    path = D + '/Maps/L_' + name + CFG.get('suffix', '')
    if EAL.does_asset_exist(path):
        LES.new_level(D + '/Maps/L_Scratch_' + name); EAL.delete_asset(path)
    LES.new_level(path)
    stage(M)
    if name in ('Land20', 'Lick5', 'LickFace5', 'Field60'):
        # the lying warrior's head is at actor-local (0,-170) (measured top-down, MM_Fall_Loop laid on its back, scale .86)
        hy = math.radians(HERO_YAW); head = V(HERO_POS.x + 170 * math.sin(hy), HERO_POS.y - 170 * math.cos(hy), 20)
        side = V(math.cos(hy), math.sin(hy), 0)               # perpendicular to the body
        back = 72 if name != 'Land20' else 170
        aloc = V(head.x + side.x * back, head.y + side.y * back, 0 if name != 'Land20' else 45)
        dyaw = math.degrees(math.atan2(-side.y, -side.x))
        camera(*cam_for(name, V((aloc.x + head.x) / 2, (aloc.y + head.y) / 2, 0)), CAMS[name][4])
        if not CFG.get('no_aralez'): aralez(M, aloc, Rt(0, dyaw, 0), da, dt, wa, wt, playing=bool(CFG.get('playing', 0)))
        LES.save_current_level(); log('map %s' % path); continue
    cam_az = SUN_AZ + CAMS[name][0]
    yaw = {'FlapSeq': cam_az + 95, 'Fly5': cam_az + 100, 'Fly20': cam_az + 130, 'Desc60': cam_az + 120, 'Land20': cam_az + 110, 'Lick5': cam_az + 120, 'Field60': cam_az + 120}[name]
    arot = Rt(arot.pitch, yaw, arot.roll)
    if not CFG.get('no_aralez'): aralez(M, aloc, arot, da, dt, wa, wt, playing=bool(CFG.get('playing', 0)))
    cl, ct = cam_for(name, aloc)
    camera(cl, ct, CAMS[name][4])
    LES.save_current_level(); log('map %s' % path)
if not EAL.does_asset_exist(D + '/Maps/L_Empty'):
    LES.new_level(D + '/Maps/L_Empty'); LES.save_current_level()
for s in [p for p in EAL.list_assets(D + '/Maps', recursive=False) if 'L_Scratch_' in p]:
    try: EAL.delete_asset(s)
    except Exception: pass
log('DONE')
