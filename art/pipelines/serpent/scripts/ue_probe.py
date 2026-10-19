import unreal
sk=unreal.load_asset('/Game/Twilight/Vishap/Mesh/vishap_serpent/SkeletalMeshes/vishap_serpent')
unreal.log_warning('SERPP dir %s' % [d for d in dir(sk) if 'lod' in d.lower()])
ss=unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
unreal.log_warning('SERPP sub %s' % [d for d in dir(ss) if 'lod' in d.lower() or 'screen' in d.lower()])
unreal.log_warning('SERPP lodset %s' % [d for d in dir(unreal) if 'SkeletalMeshLOD' in d])
try: unreal.log_warning('SERPP num lods %s' % ss.get_lod_count(sk))
except Exception as e: unreal.log_warning('SERPP e %s'%e)
