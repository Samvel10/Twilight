# s2_level.py - build materials + the test level /Game/Test/L_Highlands (terrain tiles, lake, sunset lighting, cameras, vegetation)
# env: HL_ONLY=mat,level  HL_LIGHT=fog|atmo  HL_SKYYAW=<turns>  HL_EXPOSURE=<ev bias>
import sys, os, json, math, traceback
sys.path.insert(0, '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands/scripts')
import unreal
from hl_common import *
import twmat
import hl_materials as HM

ONLY = os.environ.get('HL_ONLY', 'mat,level')
ENV = json.load(open(P + 'scripts/env_params.json'))
for k, v in os.environ.items():                     # HLP_<key>=value overrides env_params.json for quick tests
    if k.startswith('HLP_'):
        ENV[k[4:]] = json.loads(v)
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def spawn_mesh(mesh, loc, mat=None, label=None, shadow=True, folder=None, rot=(0, 0, 0), scale=(1, 1, 1)):
    a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator(pitch=rot[0], yaw=rot[1], roll=rot[2]))
    c = a.static_mesh_component
    c.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(*scale))
    if mat is not None:
        for i in range(max(1, c.get_num_materials())):
            c.set_material(i, mat)
    c.set_editor_property('cast_shadow', shadow)
    if label:
        a.set_actor_label(label)
    if folder:
        a.set_folder_path(folder)
    return a


def lighting():
    E = ENV
    sky = unreal.load_asset('/Engine/BasicShapes/Sphere')
    d = spawn_mesh(sky, (0, 0, 0), unreal.load_asset('/Game/Env/Materials/MI_HLSky'), 'SkyDome', False, 'Env', scale=(1.2e6, 1.2e6, 1.2e6))
    d.static_mesh_component.set_editor_property('bounds_scale', 1.0)
    mi = unreal.load_asset('/Game/Env/Materials/MI_HLSky')
    twmat.MEL.set_material_instance_scalar_parameter_value(mi, 'Yaw', float(E['sky_yaw']))
    twmat.MEL.set_material_instance_scalar_parameter_value(mi, 'Exposure', float(E['sky_exposure']))
    twmat.MEL.set_material_instance_texture_parameter_value(mi, 'SkyCube', unreal.load_asset('/Game/Env/HDRI/' + E.get('hdri', 'kloppenheim_06_puresky_4k')))
    twmat.MEL.update_material_instance(mi); twmat.save(mi)
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 500000), unreal.Rotator(pitch=-E['sun_el'], yaw=E['sun_yaw'], roll=0))
    sun.set_actor_label('Sun'); sun.set_folder_path('Env')
    lc = sun.get_component_by_class(unreal.DirectionalLightComponent)
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    lc.set_intensity(E['sun_lux']); lc.set_light_color(unreal.LinearColor(*E['sun_color'], 1.0))
    lc.set_editor_property('dynamic_shadow_distance_movable_light', E['csm_distance'])
    lc.set_editor_property('dynamic_shadow_cascades', 2)
    lc.set_editor_property('far_shadow_cascade_count', 0)
    lc.set_editor_property('light_source_angle', 1.0)
    lc.set_editor_property('atmosphere_sun_light', E['mode'] == 'atmo')
    sl = EAS.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000), unreal.Rotator())
    sl.set_actor_label('SkyLight'); sl.set_folder_path('Env')
    sc = sl.get_component_by_class(unreal.SkyLightComponent)
    sc.set_mobility(unreal.ComponentMobility.MOVABLE)
    sc.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sc.set_cubemap(unreal.load_asset('/Game/Env/HDRI/' + E.get('hdri', 'kloppenheim_06_puresky_4k')))
    sc.set_editor_property('source_cubemap_angle', float(E['sky_yaw']) * 360.0)
    sc.set_intensity(E['sky_intensity'])
    sc.set_editor_property('lower_hemisphere_is_black', False)
    sc.set_editor_property('lower_hemisphere_color', unreal.LinearColor(*E['lower_hemi'], 1.0))
    if E['mode'] == 'atmo':
        at = EAS.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, -E['lake_level_m'] * 100), unreal.Rotator())
        at.set_actor_label('SkyAtmosphere'); at.set_folder_path('Env')
        ac = at.get_component_by_class(unreal.SkyAtmosphereComponent)
        ac.set_editor_property('aerial_pespective_view_distance_scale', E['ap_distance_scale'])
        ac.set_editor_property('height_fog_contribution', 1.0)
        ac.set_editor_property('mie_scattering_scale', E['mie_scale'])
        ac.set_editor_property('rayleigh_exponential_distribution', 8.0)
    fog = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, E['fog_z']), unreal.Rotator())
    fog.set_actor_label('HeightFog'); fog.set_folder_path('Env')
    fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
    fc.set_fog_density(E['fog_density']); fc.set_fog_height_falloff(E['fog_falloff']); fc.set_fog_max_opacity(E['fog_max_opacity'])
    fc.set_start_distance(E['fog_start'])
    fc.set_fog_inscattering_color(unreal.LinearColor(*E['fog_color'], 1.0))
    fc.set_directional_inscattering_color(unreal.LinearColor(*E['fog_sun_color'], 1.0))
    fc.set_editor_property('directional_inscattering_exponent', E['fog_sun_exponent'])
    fc.set_editor_property('directional_inscattering_start_distance', E['fog_sun_start'])
    fc.set_editor_property('fog_cutoff_distance', 0.0)
    try:
        fd = fc.get_editor_property('second_fog_data')
        fd.set_editor_property('fog_density', E['fog2_density']); fd.set_editor_property('fog_height_falloff', E['fog2_falloff'])
        fd.set_editor_property('fog_height_offset', E['fog2_offset'])
        fc.set_editor_property('second_fog_data', fd)
    except Exception as e:
        log('fog2: %s' % e)
    ppv = EAS.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), unreal.Rotator())
    ppv.set_actor_label('PostProcess'); ppv.set_folder_path('Env')
    ppv.set_editor_property('unbound', True)
    s = ppv.get_editor_property('settings')
    for k, v in [('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL), ('auto_exposure_bias', float(E['exposure'])),
                 ('auto_exposure_apply_physical_camera_exposure', False), ('bloom_intensity', E['bloom']),
                 ('vignette_intensity', 0.25), ('white_temp', E['white_temp']), ('color_saturation', unreal.Vector4(1, 1, 1, E['saturation'])),
                 ('color_contrast', unreal.Vector4(1, 1, 1, E['contrast']))]:
        try:
            s.set_editor_property('override_' + k, True); s.set_editor_property(k, v)
        except Exception as e:
            log('pp %s: %s' % (k, e))
    ppv.set_editor_property('settings', s)


def terrain(m):
    for r in ('core', 'mid', 'far'):
        lay = json.load(open(GEN + 'mesh/%s_layout.json' % r))
        mi = m['mi_' + r]
        for t in lay['tiles']:
            sm = unreal.load_asset(TROOT + '/%s/%s/SM_%s' % (r, t['name'], t['name']))
            if sm is None:
                log('missing tile %s' % t['name']); continue
            a = spawn_mesh(sm, t['loc'], mi, t['name'], r == 'core', 'Terrain/' + r)
            a.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
    wl = json.load(open(GEN + 'mesh/water_layout.json'))
    for t in wl['tiles']:
        reg = unreal.AssetRegistryHelpers.get_asset_registry()
        sm = next((a.get_asset() for a in reg.get_assets_by_path(TROOT + '/Water/' + t['name'], recursive=True)
                   if str(a.asset_class_path.asset_name) == 'StaticMesh'), None)
        if sm is None:
            log('missing water %s' % t['name']); continue
        spawn_mesh(sm, t['loc'], m['mi_lake'], t['name'], False, 'Terrain/water')


def cameras():
    cams = json.load(open(GEN + 'cams.json'))
    for n, c in cams.items():
        rot = unreal.MathLibrary.find_look_at_rotation(unreal.Vector(*c['pos']), unreal.Vector(*c['tgt']))
        a = EAS.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(*c['pos']), rot)
        a.set_actor_label('CAM_' + n); a.set_folder_path('Cams')
        cc = a.camera_component
        cc.set_editor_property('field_of_view', c['fov'])
        cc.set_editor_property('constrain_aspect_ratio', False)
    pc = EAS.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(*list(cams.values())[0]['pos']), unreal.Rotator())
    pc.set_actor_label('PerfCam'); pc.set_folder_path('Cams')
    pc.set_editor_property('auto_activate_for_player', unreal.AutoReceiveInput.PLAYER0)
    for i, yaw in enumerate((165, 345)):   # sky probes: 165 = toward the sun (HDRI/sun alignment)
        a = EAS.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(0, 0, 500000), unreal.Rotator(pitch=8, yaw=yaw, roll=0))
        a.set_actor_label('CAM_skyprobe%d' % yaw); a.set_folder_path('Cams')
        a.camera_component.set_editor_property('field_of_view', 90.0)


try:
    m = HM.build_all() if 'mat' in ONLY else None
    if m is None:
        m = {k: unreal.load_asset('/Game/Env/Materials/' + v) for k, v in [('mi_core', 'MI_HLTerrain_core' + SFX), ('mi_mid', 'MI_HLTerrain_mid' + SFX), ('mi_far', 'MI_HLTerrain_far' + SFX), ('mi_lake', 'MI_HLLake'), ('mi_sky', 'MI_HLSky')]}
    if 'level' in ONLY:
        unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
        lighting()
        terrain(m)
        cameras()
        if 'veg' in ONLY or os.environ.get('HL_VEG'):
            import s3_veg
            s3_veg.scatter()
        unreal.EditorLoadingAndSavingUtils.save_map(unreal.EditorLevelLibrary.get_editor_world(), LEVEL)
        log('level saved')
    log('errors=%s' % twmat.ERRORS)
except Exception:
    unreal.log_error('HL s2 failed\n' + traceback.format_exc())
log('S2 DONE')
unreal.SystemLibrary.quit_editor()
