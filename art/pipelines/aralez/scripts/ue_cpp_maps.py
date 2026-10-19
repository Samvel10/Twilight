"""Runtime test maps for the C++ components (cpp_test project): AAralezShowcase in fixed modes / cycling."""
import unreal
src = open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez/scripts/ue_build_maps.py').read().split("SHOTS = {")[0]
exec(src)
M = mats()
for name, mode, aloc, camoff, fov in (('L_CppFlap', 2, V(0, 0, 900), (70, 6, 900), 45), ('L_CppGlide', 1, V(0, 0, 900), (125, 4, 600), 50),
                                      ('L_CppLand', 3, V(0, 0, 0), (75, 8, 900), 45), ('L_CppLick', 4, V(0, 0, 0), (100, 14, 500), 45), ('L_CppCycle', -1, V(0, 0, 300), (90, 6, 1100), 45)):
    path = '/Game/Test/' + name
    if EAL.does_asset_exist(path): LES.new_level('/Game/Test/L_Scratch_' + name); EAL.delete_asset(path)
    LES.new_level(path); env(M)
    az = CFG['sun_yaw'] - 180.0 + camoff[0]
    a = EAS.spawn_actor_from_class(unreal.AralezShowcase, aloc, Rt(0, az + 100, 0))
    a.set_editor_property('fixed_mode', mode); a.set_editor_property('asset_root', '/Game/Aralez')
    t = V(aloc.x, aloc.y, aloc.z + 40)
    import math
    ca, ce = math.radians(az), math.radians(camoff[1])
    cl = V(t.x + math.cos(ca) * math.cos(ce) * camoff[2], t.y + math.sin(ca) * math.cos(ce) * camoff[2], t.z + math.sin(ce) * camoff[2])
    camera(cl, t, fov)
    LES.save_current_level(); log('map ' + path)
if not EAL.does_asset_exist('/Game/Test/L_Empty'): LES.new_level('/Game/Test/L_Empty'); LES.save_current_level()
