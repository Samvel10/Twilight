"""helpers for AralezProto (scratch)."""
import unreal, os
def log(m): unreal.log_warning('ARZ ' + str(m))
A = '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez'
EAL = unreal.EditorAssetLibrary; AT = unreal.AssetToolsHelpers.get_asset_tools(); ML = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty
def new_material(path, **props):
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    d, n = path.rsplit('/', 1)
    m = AT.create_asset(n, d, unreal.Material, unreal.MaterialFactoryNew())
    for k, v in props.items(): m.set_editor_property(k, v)
    return m
class G:
    """tiny material graph builder"""
    def __init__(s, m): s.m = m; s.y = 0
    def e(s, cls, **kw):
        s.y += 120; x = ML.create_material_expression(s.m, cls, -600, s.y)
        for k, v in kw.items(): x.set_editor_property(k, v)
        return x
    def ln(s, a, b, inp='', out=''):
        if isinstance(a, tuple): a, out = a
        ML.connect_material_expressions(a, out, b, inp); return b
    def c(s, v): return s.e(unreal.MaterialExpressionConstant, r=v)
    def c3(s, r, g, b): return s.e(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(r, g, b, 1))
    def sp(s, name, v): return s.e(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=v)
    def vp(s, name, v): return s.e(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=unreal.LinearColor(*v))
    def bin(s, cls, a, b):
        x = s.e(cls)
        for inp, v in (('A', a), ('B', b)):
            if isinstance(v, (int, float)): v = s.c(v)
            s.ln(v, x, inp)
        return x
    def mul(s, a, b): return s.bin(unreal.MaterialExpressionMultiply, a, b)
    def add(s, a, b): return s.bin(unreal.MaterialExpressionAdd, a, b)
    def lerp(s, a, b, t):
        x = s.e(unreal.MaterialExpressionLinearInterpolate)
        for inp, v in (('A', a), ('B', b), ('Alpha', t)):
            if isinstance(v, (int, float)): v = s.c(v)
            s.ln(v, x, inp)
        return x
    def tex(s, t, uv=None, st=None, param=None):
        cls = unreal.MaterialExpressionTextureSampleParameter2D if param else unreal.MaterialExpressionTextureSample
        x = s.e(cls, texture=t)
        if param: x.set_editor_property('parameter_name', param)
        if st is not None: x.set_editor_property('sampler_type', st)
        if uv is not None: s.ln(uv, x, 'UVs')
        return x
    def out(s, prop, v, o=''):
        if isinstance(v, tuple): v, o = v
        if isinstance(v, (int, float)): v = s.c(v)
        ML.connect_material_property(v, o, prop)
    def done(s): ML.recompile_material(s.m); EAL.save_loaded_asset(s.m); return s.m
def mic(path, parent, scalars={}, vectors={}, textures={}):
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    d, n = path.rsplit('/', 1)
    m = AT.create_asset(n, d, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    m.set_editor_property('parent', unreal.load_asset(parent) if isinstance(parent, str) else parent)
    for k, v in scalars.items(): ML.set_material_instance_scalar_parameter_value(m, k, v)
    for k, v in vectors.items(): ML.set_material_instance_vector_parameter_value(m, k, unreal.LinearColor(*v))
    for k, v in textures.items(): ML.set_material_instance_texture_parameter_value(m, k, unreal.load_asset(v) if isinstance(v, str) else v)
    ML.update_material_instance(m); EAL.save_loaded_asset(m); return m
