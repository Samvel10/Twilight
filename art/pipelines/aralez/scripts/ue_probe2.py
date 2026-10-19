import unreal
def log(m): unreal.log_warning('ARZ ' + str(m))
for p in ('/Game/Aralez/Dog/SK_Aralez/Materials/Material_0', '/Game/Aralez/Props/grass_medium_01/grass_medium_01_1k/Materials/grass_medium_01'):
    m = unreal.load_asset(p)
    log('%s parent=%s' % (p, m.get_editor_property('parent').get_path_name()))
    for tp in m.get_editor_property('texture_parameter_values'):
        log('  tex %s = %s' % (tp.parameter_info.name, tp.parameter_value.get_path_name() if tp.parameter_value else None))
    for sp in m.get_editor_property('scalar_parameter_values'): log('  scalar %s = %s' % (sp.parameter_info.name, sp.parameter_value))
for t in ('/Game/Aralez/Dog/SK_Aralez/Textures/Image_0', '/Game/Aralez/Dog/SK_Aralez/Textures/Image_1'):
    x = unreal.load_asset(t); log('%s srgb=%s comp=%s' % (t, x.get_editor_property('srgb'), x.get_editor_property('compression_settings')))
