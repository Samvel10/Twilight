"""import a GLB as static mesh (look-dev only). env HUM_STATIC_GLB, HUM_STATIC_DEST"""
import unreal, os
AT=unreal.AssetToolsHelpers.get_asset_tools(); EAL=unreal.EditorAssetLibrary
pp='/Game/Twilight/Humans/Pipelines/GLTF_Static'
p=unreal.load_asset(pp) if EAL.does_asset_exist(pp) else EAL.duplicate_loaded_asset(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFAssetsPipeline'),pp)
mp=p.get_editor_property('mesh_pipeline'); mp.set_editor_property('build_nanite',False); mp.set_editor_property('import_skeletal_meshes',False)
try: mp.set_editor_property('combine_static_meshes_behavior', unreal.InterchangeCombineStaticMeshesBehavior.COMBINE_ALL) 
except Exception as e: unreal.log_warning('HUM combine %s'%e)
EAL.save_loaded_asset(p)
dest=os.environ['HUM_STATIC_DEST']
if EAL.does_directory_exist(dest): EAL.delete_directory(dest)
ov=unreal.InterchangePipelineStackOverride(); ov.add_pipeline(p); ov.add_pipeline(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFPipeline'))
t=unreal.AssetImportTask(); t.filename=os.environ['HUM_STATIC_GLB']; t.destination_path=dest; t.automated=True; t.replace_existing=True; t.save=True; t.options=ov
AT.import_asset_tasks([t])
for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path(dest,recursive=True):
    if str(a.asset_class_path.asset_name)=='StaticMesh': unreal.log_warning('HUM static %s'%a.package_name)
