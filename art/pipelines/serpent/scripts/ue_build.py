"""Serpent vishap: import the skinned GLB + baked textures, build M_VishapSerpent (+MI), and the test level.
Run: UnrealEditor-Cmd SerpentProto.uproject -ExecutePythonScript=ue_build.py -unattended -nullrhi
Env: SERP_SRC (folder with vishap_serpent.glb + textures/), SERP_DEST (/Game/Twilight/Vishap by default),
     SERP_LEVEL=1 to (re)build /Game/Proto/Maps/L_Sky (proto only)."""
import unreal, os, math
if not hasattr(unreal, "MaterialEditingLibrary"):
    unreal.load_module("MaterialEditor")
SRC = os.environ.get('SERP_SRC', '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/serpent/deliver')
DEST = os.environ.get('SERP_DEST', '/Game/Twilight/Vishap')
MEL = unreal.MaterialEditingLibrary; AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary
reg = unreal.AssetRegistryHelpers.get_asset_registry()
P = unreal.MaterialProperty
def log(m): unreal.log_warning('SERPB ' + str(m))

# ------------------------------------------------------------------ 1. skeletal mesh (Interchange, no Nanite, no materials)
def import_mesh():
    dest = DEST + '/Mesh'
    if EAL.does_directory_exist(dest): EAL.delete_directory(dest)
    pp = DEST + '/Pipelines/GLTF_Serpent'
    p = unreal.load_asset(pp) if EAL.does_asset_exist(pp) else EAL.duplicate_loaded_asset(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFAssetsPipeline'), pp)
    mp = p.get_editor_property('mesh_pipeline')
    mp.set_editor_property('build_nanite', False)
    mp.set_editor_property('import_static_meshes', False)
    try: mp.set_editor_property('create_physics_asset', False)
    except Exception as e: log('physics opt %s' % e)
    ap = p.get_editor_property('animation_pipeline'); ap.set_editor_property('import_animations', False)
    try:
        matp = p.get_editor_property('material_pipeline'); matp.set_editor_property('import_materials', False)
    except Exception as e: log('matpipe %s' % e)
    ov = unreal.InterchangePipelineStackOverride(); ov.add_pipeline(p); ov.add_pipeline(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFPipeline'))
    t = unreal.AssetImportTask(); t.filename = SRC + '/SK_VishapSerpent.glb'; t.destination_path = dest
    t.automated = True; t.replace_existing = True; t.save = True; t.options = ov
    AT.import_asset_tasks([t])
    sk = None
    for a in reg.get_assets_by_path(dest, recursive=True):
        c = str(a.asset_class_path.asset_name); log('asset %s %s' % (c, a.package_name))
        if c == 'SkeletalMesh': sk = a.get_asset()
    # asset path: DEST/Mesh/SK_VishapSerpent/SkeletalMeshes/SK_VishapSerpent (named after the GLB, no rename -> no redirectors)
    return sk

# ------------------------------------------------------------------ 2. textures
def import_tex(name, kind):
    dest = DEST + '/Textures'
    t = unreal.AssetImportTask(); t.filename = '%s/textures/%s.png' % (SRC, name); t.destination_path = dest
    t.automated = True; t.replace_existing = True; t.save = False
    AT.import_asset_tasks([t])
    tex = unreal.load_asset(dest + '/' + name)
    if kind == 'normal':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('srgb', False)
        tex.set_editor_property('flip_green_channel', os.environ.get('SERP_FLIPG', '0') == '1')
    elif kind == 'mask':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_GRAYSCALE)
        tex.set_editor_property('srgb', False)
    EAL.save_loaded_asset(tex)
    return tex

class G:
    def __init__(s, m): s.m = m; s.x = -1800; s.y = 0
    def new(s, cls, **props):
        e = MEL.create_material_expression(s.m, cls, s.x, s.y); s.y += 140
        if s.y > 2600: s.y = 0; s.x += 320
        for k, v in props.items(): e.set_editor_property(k, v)
        return e
    def link(s, a, b, inp='', out=''): MEL.connect_material_expressions(a, out, b, inp)
    def scalar(s, name, v, grp='Serpent'): return s.new(unreal.MaterialExpressionScalarParameter, parameter_name=name, default_value=v, group=grp)
    def vec(s, name, c, grp='Serpent'): return s.new(unreal.MaterialExpressionVectorParameter, parameter_name=name, default_value=unreal.LinearColor(c[0], c[1], c[2], 1), group=grp)
    def c(s, v):
        if isinstance(v, (int, float)): return s.new(unreal.MaterialExpressionConstant, r=float(v))
        return s.new(unreal.MaterialExpressionConstant3Vector, constant=unreal.LinearColor(v[0], v[1], v[2], 1))
    def _w(s, a): return s.c(a) if isinstance(a, (int, float, tuple)) else a
    def _bin(s, cls, a, b):
        e = s.new(cls); s.link(s._w(a), e, 'A'); s.link(s._w(b), e, 'B'); return e
    def mul(s, a, b): return s._bin(unreal.MaterialExpressionMultiply, a, b)
    def add(s, a, b): return s._bin(unreal.MaterialExpressionAdd, a, b)
    def sub(s, a, b): return s._bin(unreal.MaterialExpressionSubtract, a, b)
    def div(s, a, b): return s._bin(unreal.MaterialExpressionDivide, a, b)
    def dot(s, a, b): return s._bin(unreal.MaterialExpressionDotProduct, a, b)
    def pow(s, a, b):
        e = s.new(unreal.MaterialExpressionPower); s.link(a, e, 'Base'); s.link(s._w(b), e, 'Exponent'); return e
    def sat(s, a):
        e = s.new(unreal.MaterialExpressionSaturate); s.link(a, e); return e
    def lerp(s, a, b, t):
        e = s.new(unreal.MaterialExpressionLinearInterpolate); s.link(s._w(a), e, 'A'); s.link(s._w(b), e, 'B'); s.link(s._w(t), e, 'Alpha'); return e
    def mask(s, a, r=False, g=False, b=False, al=False):
        e = s.new(unreal.MaterialExpressionComponentMask, r=r, g=g, b=b, a=al); s.link(a, e); return e
    def tex(s, name, t, sampler, grp='Textures'):
        return s.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=name, texture=t, sampler_type=sampler, group=grp)
    NAMES = {'MP_BASE_COLOR': 'BaseColor', 'MP_NORMAL': 'Normal', 'MP_ROUGHNESS': 'Roughness', 'MP_SPECULAR': 'Specular',
             'MP_METALLIC': 'Metallic', 'MP_AMBIENT_OCCLUSION': 'AmbientOcclusion', 'MP_EMISSIVE_COLOR': 'EmissiveColor'}
    def out(s, prop, e):
        if not hasattr(s, 'outs'): s.outs = {}
        s.outs[s.NAMES[str(prop).split('.')[-1].split(':')[0].strip('<> ')] if str(prop).split('.')[-1].split(':')[0].strip('<> ') in s.NAMES else prop.name] = e

def build_material(td, tn, tm, sn, sh):
    path = DEST + '/Materials/M_VishapSerpent'
    if EAL.does_asset_exist(path):
        m = unreal.load_asset(path); MEL.delete_all_material_expressions(m)
    else:
        m = AT.create_asset('M_VishapSerpent', DEST + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    MEL.set_material_usage(m, unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    CLEARCOAT = os.environ.get('SERP_CLEARCOAT', '1') == '1'
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_CLEAR_COAT if CLEARCOAT else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    g = G(m); ST = unreal.MaterialSamplerType
    base = g.tex('BaseTex', td, ST.SAMPLERTYPE_COLOR)
    nrm = g.tex('NormalTex', tn, ST.SAMPLERTYPE_NORMAL)
    msk = g.tex('MouthMask', tm, ST.SAMPLERTYPE_LINEAR_GRAYSCALE)
    rgb = g.mask(base, r=True, g=True, b=True)
    lum = g.dot(rgb, g.c((0.3, 0.59, 0.11)))
    # recolour: keep the scan's pattern (luminance, contrast-boosted) but move the hue to the vishap palette
    pat = g.pow(g.sat(g.mul(lum, g.scalar('PatternGain', 2.2, 'Colour'))), g.scalar('PatternContrast', 1.6, 'Colour'))
    dark = g.vec('DarkColor', (0.010, 0.017, 0.008), 'Colour')     # blotches / back: green-black
    light = g.vec('LightColor', (0.22, 0.15, 0.05), 'Colour')    # ground scales / belly: dull bronze
    recol = g.lerp(dark, light, pat)
    bc = g.mul(g.lerp(rgb, recol, g.scalar('Recolor', 0.85, 'Colour')), g.scalar('Brightness', 1.0, 'Colour'))
    mouth = g.mask(msk, r=True)
    bc = g.lerp(bc, g.mul(rgb, g.vec('MouthTint', (0.40, 0.07, 0.035), 'Mouth')), mouth)
    g.out(P.MP_BASE_COLOR, bc)
    nrgb = g.mask(nrm, r=True, g=True, b=True)
    macro = g.lerp((0.0, 0.0, 1.0), nrgb, g.scalar('NormalStrength', 0.7, 'Surface'))
    # crisp keeled scales from a tiling detail map in body-aligned UV1 (dorsal rows; wide ventral plates on the belly)
    vc = g.new(unreal.MaterialExpressionVertexColor)
    bodym = g.mask(vc, r=True)
    uv1 = g.new(unreal.MaterialExpressionTextureCoordinate, coordinate_index=1)
    uvb = g.mul(uv1, g.new(unreal.MaterialExpressionConstant2Vector, r=1.0, g=0.125))
    sdn = g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name='ScaleNormal', texture=sn, sampler_type=ST.SAMPLERTYPE_NORMAL, group='Textures'); g.link(uv1, sdn, 'UVs')
    sbn = g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name='ScaleNormalBelly', texture=sn, sampler_type=ST.SAMPLERTYPE_NORMAL, group='Textures'); g.link(uvb, sbn, 'UVs')
    sdh = g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name='ScaleHeight', texture=sh, sampler_type=ST.SAMPLERTYPE_LINEAR_GRAYSCALE, group='Textures'); g.link(uv1, sdh, 'UVs')
    # belly = around V1 = 0 / 3 (seam on the belly): wide ventral plates there
    fv = g.new(unreal.MaterialExpressionFrac); g.link(g.mul(g.mask(uv1, g=True), 1.0 / 3.0), fv)
    bd = g.new(unreal.MaterialExpressionAbs); g.link(g.sub(fv, 0.5), bd)
    bellym = g.sat(g.mul(g.sub(bd, 0.40), 12.0))
    dn = g.lerp(g.mask(sdn, r=True, g=True, b=True), g.mask(sbn, r=True, g=True, b=True), bellym)
    dstr = g.mul(bodym, g.scalar('ScaleDetail', 0.85, 'Surface'))
    # rotate the detail normal from the UV1 frame into the mesh's UV0 tangent frame (cos/sin/mirror in vertex colour)
    cs = g.sub(g.mul(g.mask(vc, g=True), 2.0), 1.0); sn_ = g.sub(g.mul(g.mask(vc, b=True), 2.0), 1.0)
    va = g.new(unreal.MaterialExpressionMultiply); MEL.connect_material_expressions(vc, 'A', va, 'A'); g.link(g.c(1.0), va, 'B')
    mi = g.sub(1.0, g.mul(va, 2.0))          # +1 normal, -1 mirrored (vertex alpha)
    dx = g.mask(dn, r=True); dy = g.mul(g.mask(dn, g=True), mi)
    rx = g.sub(g.mul(dx, cs), g.mul(dy, sn_)); ry = g.add(g.mul(dx, sn_), g.mul(dy, cs))
    a2 = g.new(unreal.MaterialExpressionAppendVector); g.link(rx, a2, 'A'); g.link(ry, a2, 'B')
    a3 = g.new(unreal.MaterialExpressionAppendVector); g.link(a2, a3, 'A'); g.link(g.mask(dn, b=True), a3, 'B')
    dn = g.lerp((0.0, 0.0, 1.0), a3, dstr)
    # whiteout blend: (m.xy + d.xy, m.z * d.z)
    xy = g.add(g.mask(macro, r=True, g=True), g.mask(dn, r=True, g=True))
    zz = g.mul(g.mask(macro, b=True), g.mask(dn, b=True))
    ap = g.new(unreal.MaterialExpressionAppendVector); g.link(xy, ap, 'A'); g.link(zz, ap, 'B')
    nn = g.new(unreal.MaterialExpressionNormalize); g.link(ap, nn)
    g.out(P.MP_NORMAL, nn)
    cav = g.lerp(1.0, g.mask(sdh, r=True), g.mul(dstr, g.scalar('CavityStrength', 0.45, 'Surface')))
    g.outs['BaseColor'] = g.mul(g.outs['BaseColor'], cav)
    nrgb = nn
    # wet scales: glossier on the flat scale tops, rougher in the grooves and on light (dry, dusty) scales
    nz = g.sat(g.mask(nrgb, b=True))
    tops = g.pow(nz, g.scalar('WetTightness', 6.0, 'Surface'))
    r0 = g.lerp(g.scalar('GrooveRough', 0.62, 'Surface'), g.scalar('WetRough', 0.26, 'Surface'), g.mul(tops, g.scalar('Wetness', 1.0, 'Surface')))
    r1 = g.add(g.add(r0, g.mul(pat, g.scalar('LightRoughAdd', 0.08, 'Surface'))), g.mul(g.sub(1.0, cav), 0.5))
    g.out(P.MP_ROUGHNESS, g.sat(g.lerp(r1, 0.35, mouth)))
    g.out(P.MP_SPECULAR, g.scalar('Specular', 0.45, 'Surface'))
    g.out(P.MP_AMBIENT_OCCLUSION, g.lerp(1.0, g.pow(nz, 2.0), g.scalar('GrooveAO', 0.6, 'Surface')))
    # ember glow in the mouth only (pulse driven from C++ via MouthGlow)
    em = g.mul(g.mul(g.vec('EmberColor', (1.0, 0.12, 0.02), 'Mouth'), g.scalar('MouthGlow', 3.0, 'Mouth')), g.pow(mouth, 1.5))
    em = g.mul(em, g.sat(g.mul(lum, g.scalar('EmberDetail', 3.0, 'Mouth'))))   # keep the palate/tongue structure in the glow
    flash = g.mul(g.vec('FlashColor', (1.0, 0.85, 0.7), 'Game'), g.scalar('HitFlash', 0.0, 'Game'))   # driven by the game on hits
    g.out(P.MP_EMISSIVE_COLOR, g.add(em, flash))
    if CLEARCOAT:   # thin wet film over the scales: sharp sunset glints on top of the rougher scale surface
        g.outs['ClearCoat'] = g.mul(g.scalar('ClearCoat', 0.45, 'Surface'), g.lerp(0.35, 1.0, tops))
        g.outs['ClearCoatRoughness'] = g.scalar('ClearCoatRoughness', 0.12, 'Surface')
    # everything goes through MakeMaterialAttributes (clear-coat pins are hidden from the Python enum)
    m.set_editor_property('use_material_attributes', True)
    mma = g.new(unreal.MaterialExpressionMakeMaterialAttributes)
    for k, e in g.outs.items(): g.link(e, mma, k)
    MEL.connect_material_property(mma, '', P.MP_MATERIAL_ATTRIBUTES)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    return m

def mic(path, parent, scalars={}, vectors={}):
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    d, n = path.rsplit('/', 1)
    mi = AT.create_asset(n, d, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', parent)
    for k, v in scalars.items(): MEL.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in vectors.items(): MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(*v))
    MEL.update_material_instance(mi); EAL.save_loaded_asset(mi); return mi

def import_horns():
    # optional procedural horns (own CC0 geometry) as a static mesh in head-bone space + keratin material
    fn = SRC + '/SM_VishapHorns.glb'
    if not os.path.exists(fn): return None
    dest = DEST + '/Mesh/Horns'
    if EAL.does_directory_exist(dest): EAL.delete_directory(dest)
    pp = DEST + '/Pipelines/GLTF_Static'
    p = unreal.load_asset(pp) if EAL.does_asset_exist(pp) else EAL.duplicate_loaded_asset(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFAssetsPipeline'), pp)
    mp = p.get_editor_property('mesh_pipeline'); mp.set_editor_property('build_nanite', False)
    mp.set_editor_property('import_skeletal_meshes', False); mp.set_editor_property('import_static_meshes', True)
    try: p.get_editor_property('material_pipeline').set_editor_property('import_materials', False)
    except Exception as e: log('horn matpipe %s' % e)
    ov = unreal.InterchangePipelineStackOverride(); ov.add_pipeline(p); ov.add_pipeline(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFPipeline'))
    t = unreal.AssetImportTask(); t.filename = fn; t.destination_path = dest; t.automated = True; t.replace_existing = True; t.save = True; t.options = ov
    AT.import_asset_tasks([t])
    sm = None
    for a in reg.get_assets_by_path(dest, recursive=True):
        if str(a.asset_class_path.asset_name) == 'StaticMesh': sm = a.get_asset()
    if not sm: log('no horn mesh'); return None
    # keratin: dark root, paler worn tip, growth-ring roughness
    path = DEST + '/Materials/M_VishapHorn'
    if EAL.does_asset_exist(path):
        m = unreal.load_asset(path); MEL.delete_all_material_expressions(m)
    else:
        m = AT.create_asset('M_VishapHorn', DEST + '/Materials', unreal.Material, unreal.MaterialFactoryNew())
    g = G(m)
    uv = g.new(unreal.MaterialExpressionTextureCoordinate)
    v = g.mask(uv, g=True)
    tipf = g.pow(v, g.scalar('TipFalloff', 2.2, 'Horn'))
    rings = g.new(unreal.MaterialExpressionSine); g.link(g.mul(v, g.scalar('RingFreq', 100.0, 'Horn')), rings)
    bc = g.lerp(g.vec('RootColor', (0.028, 0.022, 0.016), 'Horn'), g.vec('TipColor', (0.30, 0.25, 0.17), 'Horn'), tipf)
    bc = g.mul(bc, g.add(0.85, g.mul(rings, 0.15)))
    MEL.connect_material_property(bc, '', P.MP_BASE_COLOR)
    MEL.connect_material_property(g.add(g.scalar('Roughness', 0.42, 'Horn'), g.mul(rings, 0.08)), '', P.MP_ROUGHNESS)
    MEL.connect_material_property(g.scalar('Specular', 0.5, 'Horn'), '', P.MP_SPECULAR)
    MEL.recompile_material(m); EAL.save_loaded_asset(m)
    sm.set_material(0, m)
    EAL.save_loaded_asset(sm)
    log('horns %s' % sm.get_path_name())
    return sm

def variants(m):
    out = {}
    out['MI_Vishap_Default'] = mic(DEST + '/Materials/MI_Vishap_Default', m)
    out['MI_Vishap_Scan'] = mic(DEST + '/Materials/MI_Vishap_Scan', m, {'Recolor': 0.0})                       # original scan colours
    out['MI_Vishap_Bronze'] = mic(DEST + '/Materials/MI_Vishap_Bronze', m, {'Recolor': 0.9},
                                  {'DarkColor': (0.03, 0.022, 0.012, 1), 'LightColor': (0.30, 0.19, 0.075, 1)})
    out['MI_Vishap_Olive'] = mic(DEST + '/Materials/MI_Vishap_Olive', m, {'Recolor': 0.9},
                                 {'DarkColor': (0.008, 0.014, 0.006, 1), 'LightColor': (0.12, 0.13, 0.05, 1)})
    out['MI_Vishap_Storm'] = mic(DEST + '/Materials/MI_Vishap_Storm', m, {'Recolor': 0.9, 'Wetness': 1.0, 'WetRough': 0.2},
                                 {'DarkColor': (0.012, 0.016, 0.020, 1), 'LightColor': (0.11, 0.12, 0.11, 1)})
    for k, v in (('variants', list(out)),): log('%s %s' % (k, v))
    return out

def backdrop(EAS, lake):
    # proto-only mountain-lake backdrop from Poly Haven scans copied from the islands proto (CC0)
    import random
    random.seed(7)
    V = unreal.Vector
    try: lake.static_mesh_component.set_material(0, unreal.load_asset('/Game/Twilight/Materials/MI_SeaNatural'))
    except Exception as e: log('water %s' % e)
    kinds = [('/Game/Scan/mountainside/Mesh/mountainside_1k/StaticMeshes/mountainside_1k', '/Game/Twilight/Materials/MI_Scan_mountainside'),
             ('/Game/Scan/namaqualand_cliff_02/Mesh/namaqualand_cliff_02_2k/StaticMeshes/namaqualand_cliff_02_2k', '/Game/Twilight/Materials/MI_Scan_namaqualand_cliff_02'),
             ('/Game/Scan/coastal_cliff_01/Mesh/coastal_cliff_01_2k/StaticMeshes/coastal_cliff_01_2k', '/Game/Twilight/Materials/MI_Scan_coastal_cliff_01')]
    loaded = [(unreal.load_asset(a), unreal.load_asset(b)) for a, b in kinds]
    for msh, mi in loaded:
        b = msh.get_bounds(); log('backdrop mesh %s ext=%s' % (msh.get_name(), b.box_extent))
    n = 16
    for i in range(n):
        ang = 360.0 * i / n + random.uniform(-8, 8)
        r = random.uniform(900000, 1600000)
        msh, mi = loaded[i % len(loaded)]
        ext = msh.get_bounds().box_extent
        h = random.uniform(100000, 260000)                    # 1 - 2.6 km above the lake
        sc = h / max(ext.z * 2, 1.0)
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang)), -h * 0.25),
                                       unreal.Rotator(roll=0, pitch=0, yaw=ang + 90 + random.uniform(-25, 25)))
        a.static_mesh_component.set_static_mesh(msh); a.static_mesh_component.set_material(0, mi)
        a.set_actor_scale3d(V(sc * random.uniform(1.6, 2.6), sc * random.uniform(1.6, 2.6), sc))
        a.static_mesh_component.set_editor_property('cast_shadow', False)

def build_level(mesh, mat):
    LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem); EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    path = '/Game/Proto/Maps/L_Sky'
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    LES.new_level(path)
    for a in EAS.get_all_level_actors(): EAS.destroy_actor(a)
    V = unreal.Vector
    sun = EAS.spawn_actor_from_class(unreal.DirectionalLight, V(0, 0, 10000), unreal.Rotator(roll=0, pitch=float(os.environ.get('SERP_SUN_PITCH', '-7')), yaw=float(os.environ.get('SERP_SUN_YAW', '200'))))
    lc = sun.light_component; lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    lc.set_intensity(float(os.environ.get('SERP_SUN_LUX', '10')))
    lc.set_editor_property('use_temperature', True); lc.set_editor_property('temperature', 3100.0)
    lc.set_editor_property('dynamic_shadow_distance_movable_light', 20000.0)
    lc.set_editor_property('dynamic_shadow_cascades', 3)
    lc.set_editor_property('contact_shadow_length', 0.03)
    sl = EAS.spawn_actor_from_class(unreal.SkyLight, V(0, 0, 500)); s = sl.light_component
    s.set_mobility(unreal.ComponentMobility.MOVABLE)
    s.set_editor_property('source_type', unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    s.set_editor_property('cubemap', unreal.load_asset('/Game/Proto/HDRI/belfast_sunset_puresky_2k'))
    s.set_editor_property('intensity', float(os.environ.get('SERP_SKY', '1.0')))
    dome = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(0, 0, 0))
    dome.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Sphere'))
    dome.set_actor_scale3d(V(90000, 90000, 90000)); dome.static_mesh_component.set_material(0, unreal.load_asset('/Game/Proto/Mat/M_SkyHDRI'))
    dome.static_mesh_component.set_editor_property('cast_shadow', False)
    lake = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(0, 0, 0))
    lake.static_mesh_component.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
    lake.set_actor_scale3d(V(40000, 40000, 1)); lake.static_mesh_component.set_material(0, unreal.load_asset('/Game/Proto/Mat/M_SeaSimple'))
    lake.static_mesh_component.set_editor_property('cast_shadow', False)
    fog = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, V(0, 0, 0)); fc = fog.component
    fc.set_editor_property('fog_density', float(os.environ.get('SERP_FOG', '0.005'))); fc.set_editor_property('fog_height_falloff', 0.12)
    fc.set_editor_property('fog_inscattering_luminance', unreal.LinearColor(0.55, 0.45, 0.45, 1))
    fc.set_editor_property('directional_inscattering_luminance', unreal.LinearColor(1.0, 0.55, 0.25, 1))
    fc.set_editor_property('directional_inscattering_exponent', 6.0)
    ppv = EAS.spawn_actor_from_class(unreal.PostProcessVolume, V(0, 0, 0)); ppv.set_editor_property('unbound', True)
    ps = ppv.get_editor_property('settings')
    for k, v in (('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL), ('auto_exposure_bias', float(os.environ.get('SERP_EV', '0.0'))),
                 ('auto_exposure_apply_physical_camera_exposure', False), ('bloom_intensity', 0.6), ('vignette_intensity', 0.4),
                 ('motion_blur_amount', 0.0), ('ambient_occlusion_intensity', 0.5)):
        ps.set_editor_property('override_' + k, True); ps.set_editor_property(k, v)
    ppv.set_editor_property('settings', ps)
    if os.environ.get('SERP_BACKDROP', '1') == '1': backdrop(EAS, lake)
    demo = EAS.spawn_actor_from_class(unreal.SerpentDemo, V(0, 0, 0))
    body = demo.get_editor_property('body')
    body.set_skinned_asset_and_update(mesh)
    body.set_material(0, mat)
    LES.save_current_level(); log('level %s' % path)

sk = import_mesh()
td = import_tex('T_VishapSerpent_D', 'color'); tn = import_tex('T_VishapSerpent_N', 'normal'); tm = import_tex('T_VishapSerpent_M', 'mask')
sn = import_tex('T_VishapScales_N', 'normal'); sh = import_tex('T_VishapScales_H', 'mask')
m = build_material(td, tn, tm, sn, sh)
mis = variants(m)
import_horns()
if sk:
    sk.set_material(0, mis['MI_Vishap_Default']) if hasattr(sk, 'set_material') else None
    mats = sk.get_editor_property('materials')
    if len(mats):
        mats[0].set_editor_property('material_interface', mis['MI_Vishap_Default']); sk.set_editor_property('materials', mats)
    # LODs (same skeleton + UV atlas, built offline by lod.py): LOD1 12k tris, LOD2 4k tris
    for li, fn in ((1, 'SK_VishapSerpent_LOD1.glb'), (2, 'SK_VishapSerpent_LOD2.glb')):
        if not os.path.exists(SRC + '/' + fn): continue
        r = -1
        try: r = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).import_lod(sk, li, SRC + '/' + fn)
        except Exception as e:
            log('subsystem import_lod %s' % e)
            try: r = unreal.EditorSkeletalMeshLibrary.import_lod(sk, li, SRC + '/' + fn)
            except Exception as e2: log('library import_lod %s' % e2)
        log('import LOD%d -> %s' % (li, r))
    try:   # screen sizes through a LOD-settings asset (FSkeletalMeshLODInfo is not exposed to Python)
        lp = DEST + '/Mesh/LODS_VishapSerpent'
        if EAL.does_asset_exist(lp): EAL.delete_asset(lp)
        ls = AT.create_asset('LODS_VishapSerpent', DEST + '/Mesh', unreal.SkeletalMeshLODSettings, unreal.DataAssetFactory())
        groups = []
        for ss in (1.0, float(os.environ.get('SERP_LOD1', '0.35')), float(os.environ.get('SERP_LOD2', '0.12'))):
            g_ = unreal.SkeletalMeshLODGroupSettings(); p = unreal.PerPlatformFloat(); p.set_editor_property('default', ss)
            g_.set_editor_property('screen_size', p); groups.append(g_)
        ls.set_editor_property('lod_groups', groups); EAL.save_loaded_asset(ls)
        sk.set_editor_property('lod_settings', ls)
        log('LOD settings applied, lods=%d' % unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem).get_lod_count(sk))
    except Exception as e: log('lod screen size %s' % e)
    EAL.save_loaded_asset(sk)
    ref = sk.get_editor_property('skeleton')
    log('MESH %s bounds=%s bones=%d' % (sk.get_path_name(), sk.get_bounds().box_extent, len(ref.get_editor_property('bone_tree')) if ref else -1))
    # bone sanity: component-space positions of a few bones
    try:
        names = [str(sk.get_editor_property('skeleton').get_reference_pose().get_bone_names()[i]) for i in range(3)]
    except Exception: names = []
    log('bones %s' % names)
if os.environ.get('SERP_LEVEL', '1') == '1':
    build_level(sk, unreal.load_asset(os.environ.get('SERP_MI', DEST + '/Materials/MI_Vishap_Default')))
log('DONE')
