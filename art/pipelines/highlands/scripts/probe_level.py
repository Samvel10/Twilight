import unreal
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Test/L_Highlands')
acts = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for a in acts:
    if a.get_actor_label().startswith(('Veg_', 'Rocks_')):
        comps = a.get_components_by_class(unreal.InstancedStaticMeshComponent)
        unreal.log_warning('PROBE %s comps=%d %s' % (a.get_actor_label(), len(comps), [(c.get_name(), c.get_instance_count(), c.static_mesh.get_name() if c.static_mesh else None) for c in comps][:4]))
        if comps:
            c = comps[0]; t = c.get_instance_transform(0, True)
            unreal.log_warning('PROBE first %s vis=%s cull=%s/%s' % (t.translation, c.is_visible(), c.get_editor_property('instance_start_cull_distance'), c.get_editor_property('instance_end_cull_distance')))
unreal.SystemLibrary.quit_editor()
