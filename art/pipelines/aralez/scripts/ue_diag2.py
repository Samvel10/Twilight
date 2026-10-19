import unreal
exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/ue_build_maps.py').read().split("SHOTS = {")[0])
M = mats()
path = D + '/Maps/L_Diag2'
if EAL.does_asset_exist(path): LES.new_level(D + '/Maps/L_Scratch_d2'); EAL.delete_asset(path)
LES.new_level(path); env(M)
fallen(V(0, 0, 2), 0)
red = unreal.load_asset('/Engine/BasicShapes/BasicShapeMaterial')
for i in range(-4, 5):
    for ax in (0, 1):
        p = V(i * 50, 0, 1) if ax == 0 else V(0, i * 50, 1)
        s = place_mesh('/Engine/BasicShapes/Sphere', p, Rt(), 0.08 if i else 0.2)
cam = EAS.spawn_actor_from_class(unreal.CameraActor, V(0, 0, 600), Rt(-89.9, 0, 0))
cam.camera_component.set_editor_property('field_of_view', 60.0); cam.camera_component.set_editor_property('constrain_aspect_ratio', False)
cam.set_editor_property('auto_activate_for_player', unreal.AutoReceiveInput.PLAYER0)
LES.save_current_level(); log('diag2')
