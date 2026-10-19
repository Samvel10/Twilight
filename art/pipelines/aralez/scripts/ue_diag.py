import unreal
exec(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/ue_build_maps.py').read().split("SHOTS = {")[0])
M = mats()
path = D + '/Maps/L_Diag'
if EAL.does_asset_exist(path): LES.new_level(D + '/Maps/L_Scratch_d'); EAL.delete_asset(path)
LES.new_level(path); env(M)
mi_b = mic(D + '/Mat/MI_DiagB', D + '/Mat/M_AralezFur', {'RimIntensity': 0.0, 'DivineGlow': 0.0}, {}, {'BaseTex': D + '/Dog/SK_Aralez/Textures/Image_1'})
for i, mat in enumerate([unreal.load_asset(D + '/Dog/SK_Aralez/Materials/Material_0'), M['fur'], mi_b, unreal.load_asset('/Engine/EngineMaterials/DefaultMaterial')]):
    a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, V(0, -300 + 200 * i, 100), Rt(0, 0, 0))
    c = a.skeletal_mesh_component; c.set_skinned_asset_and_update(unreal.load_asset(DOG)); c.set_material(0, mat)
camera(V(700, 0, 250), V(0, 0, 160), 60)
LES.save_current_level(); log('diag')
