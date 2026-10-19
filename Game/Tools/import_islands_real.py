# Import for the REAL project (run with the editor binary, NOT the -run=pythonscript commandlet: StaticMeshEditorSubsystem
# is None inside commandlets, so LOD reduction silently fails there):
#   ~/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd /var/www/html/Twilight/Game/TwilightAssets.uproject \
#       -ExecutePythonScript=/ABS/import_islands_real.py -unattended -nop4 -nosplash -nosound -nullrhi -stdout
#   (it segfaults on exit AFTER saving: harmless, assets are on disk)
# Copy first (CC0, Poly Haven):  art/models/boulder_01/{boulder_01_2k.gltf,boulder_01.bin,textures/*}
#                                art/textures/aerial_rocks_02/aerial_rocks_02_{diff,nor_gl,arm}_2k.jpg
import unreal, os, glob
ROOT = '/var/www/html/Twilight/art/'
AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary

def tex_import(files, dest):
    tasks = []
    for f in files:
        t = unreal.AssetImportTask(); t.filename = f; t.destination_path = dest
        t.automated = True; t.replace_existing = True; t.save = True; tasks.append(t)
    AT.import_asset_tasks(tasks)
    for t in tasks:
        for path in t.get_editor_property('imported_object_paths'):
            a = EAL.load_asset(path); n = a.get_name().lower()
            if 'nor' in n:
                a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
                a.set_editor_property('srgb', False); a.set_editor_property('flip_green_channel', 'nor_gl' in n)
            elif 'arm' in n:
                a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS); a.set_editor_property('srgb', False)
            EAL.save_asset(path.split('.')[0], only_if_is_dirty=False)

# glTF via Interchange with Nanite OFF and no Interchange materials (we use MI_Scan_*)
src = unreal.load_asset('/Interchange/Pipelines/DefaultGLTFAssetsPipeline')
pth = '/Game/Twilight/Env/Pipelines/GLTF_NoNanite'
pipe = EAL.load_asset(pth) if EAL.does_asset_exist(pth) else EAL.duplicate_loaded_asset(src, pth)
pipe.get_editor_property('mesh_pipeline').set_editor_property('build_nanite', False)
pipe.get_editor_property('material_pipeline').set_editor_property('import_materials', False)
EAL.save_loaded_asset(pipe, False)
ov = unreal.InterchangePipelineStackOverride(); ov.add_pipeline(pipe); ov.add_pipeline(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFPipeline'))

tex_import(sorted(glob.glob(ROOT + 'models/boulder_01/textures/*.jpg')), '/Game/Twilight/Env/Scan/boulder_01')
tex_import(sorted(glob.glob(ROOT + 'textures/aerial_rocks_02/*.jpg')), '/Game/Twilight/Env/Textures')
t = unreal.AssetImportTask(); t.filename = ROOT + 'models/boulder_01/boulder_01_2k.gltf'; t.destination_path = '/Game/Twilight/Env/Scan/boulder_01'
t.automated = True; t.replace_existing = True; t.save = True; t.options = ov
AT.import_asset_tasks([t])
sm = unreal.load_asset('/Game/Twilight/Env/Scan/boulder_01/boulder_01_2k/StaticMeshes/boulder_01_2k')
# LOD0 = 30% of the 66k scan (19.8k), LOD1-3 are fractions of LOD0: 9.9k / 4.4k / 1.6k
o = unreal.StaticMeshReductionOptions(); o.auto_compute_lod_screen_size = False; rs = []
for frac, scr in ((0.3, 1.0), (0.5, 0.35), (0.22, 0.15), (0.08, 0.05)):
    s = unreal.StaticMeshReductionSettings(); s.percent_triangles = frac; s.screen_size = scr; rs.append(s)
o.reduction_settings = rs
unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).set_lods_with_notification(sm, o, True)
EAL.save_loaded_asset(sm, False)
unreal.log_warning('boulder_01 tris per LOD: %s' % [sm.get_num_triangles(i) for i in range(sm.get_num_lods())])
unreal.SystemLibrary.quit_editor()
