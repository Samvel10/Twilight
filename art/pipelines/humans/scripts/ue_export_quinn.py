import unreal
OUT='/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/src/donor/'
for n in ('SKM_Quinn_Simple','SKM_Manny_Simple'):
    sk=unreal.load_asset('/Game/Characters/Mannequins/Meshes/'+n)
    o=unreal.GLTFExportOptions()
    for k,v in (('export_vertex_skin_weights',True),('export_unlit_materials',False),('bake_material_inputs',unreal.GLTFMaterialBakeMode.DISABLED)):
        try: o.set_editor_property(k,v)
        except Exception as e: unreal.log_warning('HUM opt %s %s'%(k,e))
    ok=unreal.GLTFExporter.export_to_gltf(sk, OUT+n+'.glb', o, set())
    unreal.log_warning('HUM export %s %s'%(n,ok))
