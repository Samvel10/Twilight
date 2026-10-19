import unreal, json
MEL=unreal.MaterialEditingLibrary; reg=unreal.AssetRegistryHelpers.get_asset_registry()
out={}
for a in reg.get_assets_by_path('/Game/Twilight/Humans',recursive=True):
    if str(a.asset_class_path.asset_name)!='MaterialInstanceConstant' or '/Mesh/' not in str(a.package_name): continue
    m=a.get_asset(); par=m.get_editor_property('parent')
    d={'parent':par.get_path_name() if par else None,'tex':{},'s':{},'v':{}}
    for pv in m.get_editor_property('texture_parameter_values'): d['tex'][str(pv.parameter_info.name)]=pv.parameter_value.get_name() if pv.parameter_value else None
    for pv in m.get_editor_property('scalar_parameter_values'): d['s'][str(pv.parameter_info.name)]=pv.parameter_value
    for pv in m.get_editor_property('vector_parameter_values'): c=pv.parameter_value; d['v'][str(pv.parameter_info.name)]=[c.r,c.g,c.b,c.a]
    out[str(a.package_name)]=d
open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/logs/mats_dump.json','w').write(json.dumps(out,indent=1))
unreal.log_warning('HUM dumped %d'%len(out))
