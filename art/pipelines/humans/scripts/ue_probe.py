import unreal
def log(m): unreal.log_warning('HUM '+str(m))
sk=unreal.load_asset('/Game/Twilight/Humans/Shamiram/Mesh/shamiram/SkeletalMeshes/shamiram')
for m in sk.materials:
    mi=m.material_interface; log('slot %s -> %s'%(m.material_slot_name, mi.get_path_name() if mi else None))
mi=unreal.load_asset('/Game/Twilight/Humans/Shamiram/Materials/MI_Shamiram_Vay1')
log('Vay1 scalars %s'%[(str(p.parameter_info.name),round(p.parameter_value,3)) for p in mi.get_editor_property('scalar_parameter_values')])
log('Vay1 vectors %s'%[(str(p.parameter_info.name),p.parameter_value) for p in mi.get_editor_property('vector_parameter_values')])
for n in ('armsoldc','babsoldc','ara'):
    N=n[0].upper()+n[1:]; s=unreal.load_asset('/Game/Twilight/Humans/%s/Mesh/%s/SkeletalMeshes/%s'%(N,n,n)); pa=s.get_editor_property('physics_asset')
    log('%s physics_asset=%s bodies=%s'%(n, pa.get_path_name() if pa else None, len(pa.get_editor_property('skeletal_body_setups')) if pa else 0))
