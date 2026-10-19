"""AralezProto step 2: build preview maps (dog + wings attached at the back socket, env)."""
import unreal, os, sys, math, traceback
sys.path.insert(0, '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts')
from ue_common import *
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
V = unreal.Vector; R = lambda p, y, r=0: unreal.Rotator(roll=r, pitch=p, yaw=y)
DOG = '/Game/Aralez/Dog/'; WING = '/Game/Aralez/Wings/'
GLTF = {'chest_jnt': (0, 0.8301, 0.2711), 'nose_jnt': (0, 0.8835, 0.8221), 'L_shoulder_jnt': (0.1446, 0.5929, 0.3578)}
SOCKET = (0, 0.8896, 0.3170)   # Blender armature (0,-.317,.89) -> glTF (x, z, -y)
FOLD = float(os.environ.get('ARZ_WSCALE', '1.0'))

def solve3(cols, rhs):
    (a, b, c), (d, e, f), (g, h, i) = [[cols[r][k] for k in range(3)] for r in range(3)]
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    inv = [[(e * i - f * h) / det, (c * h - b * i) / det, (b * f - c * e) / det], [(f * g - d * i) / det, (a * i - c * g) / det, (c * d - a * f) / det],
           [(d * h - e * g) / det, (b * g - a * h) / det, (a * e - b * d) / det]]
    return [sum(inv[r][k] * rhs[k] for k in range(3)) for r in range(3)]

def socket_cs(c):
    """fit glTF->component linear map from 3 bones (ref pose), apply to the wing socket."""
    names = list(GLTF); P = [GLTF[n] for n in names]
    U = [c.get_socket_transform(n, unreal.RelativeTransformSpace.RTS_COMPONENT).translation for n in names]
    out = []
    for ax in ('x', 'y', 'z'):
        row = solve3(P, [getattr(u, ax) for u in U]); out.append(sum(row[k] * SOCKET[k] for k in range(3)))
        log('map %s <- %s' % (ax, [round(r, 2) for r in row]))
    return V(*out)

def play(c, path, pos=0.0, rate=1.0):
    an = unreal.load_asset(path)
    c.set_editor_property('animation_mode', unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    pd = unreal.SingleAnimationPlayData(); pd.set_editor_property('anim_to_play', an); pd.set_editor_property('saved_looping', True)
    pd.set_editor_property('saved_playing', True); pd.set_editor_property('saved_position', pos); pd.set_editor_property('saved_play_rate', rate)
    c.set_editor_property('animation_data', pd)

def aralez(loc, yaw, dog_clip, wing_clip, pos=0.0, rate=1.0, dog_mat=None):
    d = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, loc, R(0, yaw))
    dc = d.skeletal_mesh_component; dc.set_skinned_asset_and_update(unreal.load_asset(DOG + 'SK_Aralez'))
    if dog_mat: dc.set_material(0, unreal.load_asset(dog_mat))
    s = socket_cs(dc); log('socket CS %s' % s)
    w = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, loc, R(0, yaw))
    wc = w.skeletal_mesh_component; wc.set_skinned_asset_and_update(unreal.load_asset(WING + 'SK_AralezWings'))
    w.set_actor_transform(unreal.Transform(s, unreal.Rotator(), V(FOLD, FOLD, FOLD)) * d.get_actor_transform(), False, False)
    w.attach_to_component(dc, 'chest_jnt', unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, unreal.AttachmentRule.KEEP_WORLD, False)
    play(dc, DOG + 'SK_AralezAralez_' + dog_clip, pos, rate); play(wc, WING + 'SK_AralezWingsWing_' + wing_clip, pos, rate)
    for c in (dc, wc): c.set_editor_property('bounds_scale', 2.0)
    return d, w

def env(cam_loc, cam_at, fov=40., sun=(-12., 250.), exposure=0.0, ground=True, sky_yaw=0.0):
    sky = mic('/Game/Aralez/Env/MI_Sky', '/Game/Aralez/Env/M_SkyCube', {'Exposure': 1.0, 'Yaw': sky_yaw})
    dome = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(0, 0, 0)); dc = dome.static_mesh_component
    dc.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere')); dome.set_actor_scale3d(V(3000, 3000, 3000)); dc.set_material(0, sky); dc.set_editor_property('cast_shadow', False)
    s = EAS.spawn_actor_from_class(unreal.DirectionalLight, V(0, 0, 500), R(sun[0], sun[1])); lc = s.light_component
    lc.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE); lc.set_intensity(float(os.environ.get('ARZ_SUN', '7')))
    lc.set_light_color(unreal.LinearColor(1.0, 0.72, 0.5, 1)); lc.set_editor_property('dynamic_shadow_distance_movable_light', 4000.)
    sl = EAS.spawn_actor_from_class(unreal.SkyLight, V(0, 0, 300)); k = sl.light_component
    k.set_editor_property('mobility', unreal.ComponentMobility.MOVABLE); k.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    k.set_editor_property('cubemap', unreal.load_asset('/Game/Aralez/Env/kiara_1_dawn')); k.set_intensity(float(os.environ.get('ARZ_SKY', '1.0')))
    f = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, V(0, 0, -100)).component
    f.set_editor_property('fog_density', 0.01); f.set_editor_property('fog_height_falloff', 0.2)
    f.set_editor_property('fog_inscattering_luminance', unreal.LinearColor(0.5, 0.42, 0.38, 1))
    ppv = EAS.spawn_actor_from_class(unreal.PostProcessVolume, V(0, 0, 0)); ppv.set_editor_property('unbound', True); ps = ppv.get_editor_property('settings')
    for kk, v in (('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL), ('auto_exposure_bias', float(os.environ.get('ARZ_EXP', exposure))),
                  ('auto_exposure_apply_physical_camera_exposure', False), ('bloom_intensity', 0.5), ('vignette_intensity', 0.35)):
        ps.set_editor_property('override_' + kk, True); ps.set_editor_property(kk, v)
    ppv.set_editor_property('settings', ps)
    if ground:
        g = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(0, 0, 0)); g.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
        g.set_actor_scale3d(V(600, 600, 1)); g.static_mesh_component.set_material(0, unreal.load_asset('/Game/Aralez/Env/M_Ground'))
    cam = EAS.spawn_actor_from_class(unreal.CameraActor, cam_loc, unreal.MathLibrary.find_look_at_rotation(cam_loc, cam_at))
    cam.camera_component.set_editor_property('field_of_view', fov); cam.camera_component.set_editor_property('constrain_aspect_ratio', False)
    cam.set_editor_property('auto_activate_for_player', unreal.AutoReceiveInput.PLAYER0)

def new_map(name):
    path = '/Game/Proto/' + name
    if EAL.does_asset_exist(path):
        LES.load_level(path); acts = EAS.get_all_level_actors()
        if acts: EAS.destroy_actors(acts)
    else: LES.new_level(path)
    return path

SCENES = {
    # standing guard, wings arched (Fold clip), 3/4 front
    'L_Stand': lambda: (env(V(260, -260, 110), V(0, 0, 70)), aralez(V(0, 0, 0), -90, 'Idle', 'Fold')),
    'L_Side': lambda: (env(V(0, -420, 90), V(0, 0, 80), fov=45), aralez(V(0, 0, 0), -90, 'Idle', 'Fold')),
    'L_Glide': lambda: (env(V(330, -250, 300), V(0, 0, 330), fov=45, ground=True), aralez(V(0, 0, 300), -90, 'Glide', 'Glide')),
    'L_Flap': lambda: (env(V(420, 0, 260), V(0, 0, 330), fov=50), aralez(V(0, 0, 300), -90, 'Flap', 'Flap', 0.25)),
    'L_Land': lambda: (env(V(300, -300, 150), V(0, 0, 120), fov=45), aralez(V(0, 0, 0), -90, 'Land', 'Mantle')),
}
try:
    for name in os.environ.get('ARZ_MAPS', ','.join(SCENES)).split(','):
        p = new_map(name); SCENES[name](); LES.save_current_level(); log('map %s saved' % p)
    log('DONE')
except Exception:
    log('FAILED\n' + traceback.format_exc())
