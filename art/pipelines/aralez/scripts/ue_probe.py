import unreal
def log(m): unreal.log_warning('ARZ ' + str(m))
reg = unreal.AssetRegistryHelpers.get_asset_registry(); EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
for path in ('/Game/Aralez/Dog', '/Game/Aralez/Wings', '/Game/Twilight/Hero/Mesh'):
    for a in reg.get_assets_by_path(path, recursive=True):
        c = str(a.asset_class_path.asset_name)
        if c in ('AnimSequence', 'SkeletalMesh'):
            o = a.get_asset(); log('%s %s %s' % (c, a.package_name, ('len=%.2f' % o.get_play_length()) if c == 'AnimSequence' else ''))
LES.new_level('/Game/Aralez/Maps/L_Probe')
for mesh, bones in (('/Game/Aralez/Dog/SK_Aralez/SkeletalMeshes/SK_Aralez', ['root', 'chest_jnt', 'head_jnt', 'L_hand_jnt', 'tail_7_jnt', 'COG_jnt']),
                    ('/Game/Aralez/Wings/SK_AralezWings/SkeletalMeshes/SK_AralezWings', ['wings_root', 'L_humerus', 'L_forearm', 'L_hand', 'R_hand'])):
    a = EAS.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0))
    c = a.skeletal_mesh_component; c.set_skinned_asset_and_update(unreal.load_asset(mesh))
    b = c.get_editor_property('skeletal_mesh_asset') if hasattr(c, 'skeletal_mesh_asset') else None
    log('bounds %s' % (a.get_actor_bounds(False),))
    for n in bones:
        t = c.get_socket_transform(n, unreal.RelativeTransformSpace.RTS_COMPONENT)
        log('%s %s loc=%s rot=%s' % (mesh.split('/')[-1], n, t.translation, t.rotation.rotator()))
log('DONE')
