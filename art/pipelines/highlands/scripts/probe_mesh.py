import unreal
SMS = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
sm = unreal.load_asset('/Game/Env/Veg/SM_Pine/SM_Pine/StaticMeshes/SM_Pine')
for l in range(sm.get_num_lods()):
    n = sm.get_num_sections(l)
    unreal.log_warning('PROBE lod %d sections %d slots %s' % (l, n, [SMS.get_lod_material_slot(sm, l, s) for s in range(n)]))
unreal.log_warning('PROBE mats %s' % [(str(m.material_slot_name), m.material_interface.get_name() if m.material_interface else None) for m in sm.static_materials])
unreal.SystemLibrary.quit_editor()
