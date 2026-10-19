import unreal, os
def log(m): unreal.log_warning('ARZ ' + str(m))
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES.load_level(os.environ['ARZ_MAP'])
for a in EAS.get_all_level_actors():
    s = ''
    if isinstance(a, unreal.StaticMeshActor):
        c = a.static_mesh_component; s = '%s mat=%s' % (c.static_mesh.get_name() if c.static_mesh else None, c.get_material(0).get_name() if c.get_material(0) else None)
    par = a.get_attach_parent_actor()
    log('%s %s loc=%s scale=%s parent=%s %s' % (a.get_class().get_name(), a.get_name(), a.get_actor_location(), a.get_actor_scale3d(), par.get_name() if par else None, s))
