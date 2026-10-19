"""Aralez import: UnrealEditor-Cmd AralezTest.uproject -run=pythonscript -script=ue_import.py
env ARZ_STEPS = comma list of: dog,wings,tex,ph,hdri,mats  (default all)
ARZ_ROOT = source root (proto2/aralez)."""
import unreal, os, glob
R = os.environ.get('ARZ_ROOT', '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/aralez')
STEPS = set((os.environ.get('ARZ_STEPS') or 'dog,wings,tex,mats,mis').split(','))   # test-scene extras: ph,hdri,terrain,scene
D = os.environ.get('ARZ_DEST', '/Game/Aralez')   # the game: ARZ_DEST=/Game/Twilight/Aralez (UAralezBodyComponent::AssetRoot)
def log(m): unreal.log_warning('ARZ ' + str(m))
AT = unreal.AssetToolsHelpers.get_asset_tools(); EAL = unreal.EditorAssetLibrary
reg = unreal.AssetRegistryHelpers.get_asset_registry()
ML = unreal.MaterialEditingLibrary

def pipeline(skel, anims):
    pp = D + '/Pipelines/GLTF_%s' % ('Skel' if skel else 'Static')
    p = unreal.load_asset(pp) if EAL.does_asset_exist(pp) else EAL.duplicate_loaded_asset(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFAssetsPipeline'), pp)
    mp = p.get_editor_property('mesh_pipeline')
    mp.set_editor_property('build_nanite', False)
    mp.set_editor_property('import_static_meshes', not skel)
    mp.set_editor_property('import_skeletal_meshes', skel)
    try: mp.set_editor_property('combine_static_meshes', True)
    except Exception: pass
    ap = p.get_editor_property('animation_pipeline'); ap.set_editor_property('import_animations', anims)
    EAL.save_loaded_asset(p)
    ov = unreal.InterchangePipelineStackOverride(); ov.add_pipeline(p); ov.add_pipeline(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFPipeline'))
    return ov

def import_file(path, dest, options=None, wipe=True):
    if wipe and EAL.does_directory_exist(dest): EAL.delete_directory(dest)
    t = unreal.AssetImportTask(); t.filename = path; t.destination_path = dest
    t.automated = True; t.replace_existing = True; t.save = True
    if options: t.options = options
    AT.import_asset_tasks([t])
    out = {}
    for a in reg.get_assets_by_path(dest, recursive=True):
        out.setdefault(str(a.asset_class_path.asset_name), []).append(str(a.package_name))
    log('imported %s -> %s' % (os.path.basename(path), {k: len(v) for k, v in out.items()}))
    return out

if 'dog' in STEPS:
    o = import_file(R + '/src/glb/SK_Aralez.glb', D + '/Dog', pipeline(True, True))
    log('dog %s' % o)
if 'wings' in STEPS:
    o = import_file(R + '/src/glb/SK_AralezWings.glb', D + '/Wings', pipeline(True, True))
    log('wings %s' % o)
if 'tex' in STEPS:
    for f in ('T_Feather_BC', 'T_Feather_N', 'T_Feather_RT', 'T_FurStrands'):
        import_file(R + '/src/tex/%s.png' % f, D + '/Tex', wipe=False)
        t = unreal.load_asset(D + '/Tex/' + f)
        if f.endswith('_N'):
            t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP); t.set_editor_property('srgb', False)
        if f.endswith('_RT') or f.endswith('Strands'):
            t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS); t.set_editor_property('srgb', False)
        EAL.save_loaded_asset(t)
    gd = glob.glob(R + '/dl/ph/aerial_grass_rock/*')
    for f in gd:
        import_file(f, D + '/Tex/Ground', wipe=False)
    for a in reg.get_assets_by_path(D + '/Tex/Ground'):
        t = a.get_asset(); n = str(a.asset_name)
        if 'nor' in n: t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP); t.set_editor_property('srgb', False)
        if 'arm' in n or 'rough' in n.lower(): t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS); t.set_editor_property('srgb', False)
        EAL.save_loaded_asset(t)
if 'ph' in STEPS:
    for m in ('kite_shield', 'antique_estoc', 'grass_medium_01', 'boulder_01', 'rock_moss_set_02', 'wooden_axe'):
        g = glob.glob(R + '/dl/ph/%s/*.gltf' % m)
        if g: import_file(g[0], D + '/Props/' + m, pipeline(False, False))
if 'terrain' in STEPS:
    o = import_file(R + '/src/glb/SM_Highlands.glb', D + '/Env', pipeline(False, False))
    for p in o.get('StaticMesh', []):
        sm = unreal.load_asset(p); sm.set_material(0, unreal.load_asset(D + '/Mat/M_Ground')); EAL.save_loaded_asset(sm); log('terrain %s' % p)
if 'hdri' in STEPS:
    for h in glob.glob(R + '/dl/ph/kloppenheim_06_puresky/*.hdr'):
        o = import_file(h, D + '/HDRI', wipe=False); log('hdri %s' % o)
    sky = unreal.load_asset('/Game/Twilight/Materials/M_SkyHDRI')
    if sky:
        log('M_SkyHDRI tex params %s scal %s vec %s' % (ML.get_texture_parameter_names(sky), ML.get_scalar_parameter_names(sky), ML.get_vector_parameter_names(sky)))

# ------------------------------------------------------------------ materials
def new_mat(path):
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    d, n = path.rsplit('/', 1)
    return AT.create_asset(n, d, unreal.Material, unreal.MaterialFactoryNew())
X = unreal.MaterialExpressionScalarParameter; V = unreal.MaterialExpressionVectorParameter
def E(m, cls, x, y, **props):
    e = ML.create_material_expression(m, cls, x, y)
    for k, v in props.items(): e.set_editor_property(k, v)
    return e
def sp(m, name, val, x, y): return E(m, X, x, y, parameter_name=name, default_value=val)
def vp(m, name, val, x, y): return E(m, V, x, y, parameter_name=name, default_value=unreal.LinearColor(*val))
def tp(m, name, tex, x, y, normal=False, masks=False):
    e = E(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y, parameter_name=name, texture=unreal.load_asset(tex))
    if normal: e.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    elif masks: e.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    return e
def mul(m, a, b, x, y, ao='', bo=''):
    e = E(m, unreal.MaterialExpressionMultiply, x, y); ML.connect_material_expressions(a, ao, e, 'A'); ML.connect_material_expressions(b, bo, e, 'B'); return e
def addn(m, a, b, x, y, ao='', bo=''):
    e = E(m, unreal.MaterialExpressionAdd, x, y); ML.connect_material_expressions(a, ao, e, 'A'); ML.connect_material_expressions(b, bo, e, 'B'); return e
def lerp(m, a, b, al, x, y, ao='', bo='', alo=''):
    e = E(m, unreal.MaterialExpressionLinearInterpolate, x, y)
    ML.connect_material_expressions(a, ao, e, 'A'); ML.connect_material_expressions(b, bo, e, 'B'); ML.connect_material_expressions(al, alo, e, 'Alpha'); return e
MP = unreal.MaterialProperty
def rim(m, x, y, exp=3.5, inten=0.6, col=(1.0, 0.72, 0.38, 1)):
    fr = E(m, unreal.MaterialExpressionFresnel, x, y)
    ML.connect_material_expressions(sp(m, 'RimExp', exp, x - 250, y), '', fr, 'ExponentIn')
    c = mul(m, fr, vp(m, 'RimColor', col, x, y + 120), x + 220, y)
    return mul(m, c, sp(m, 'RimIntensity', inten, x + 220, y + 120), x + 440, y)

def dog_base_tex():
    for a in reg.get_assets_by_path(D + '/Dog', recursive=True):
        if str(a.asset_class_path.asset_name) == 'Texture2D': log('dog tex %s' % a.package_name)
    texs = [str(a.package_name) for a in reg.get_assets_by_path(D + '/Dog', recursive=True) if str(a.asset_class_path.asset_name) == 'Texture2D']
    texs.sort(key=lambda p: EAL.find_asset_data(p).get_asset().blueprint_get_size_x() if False else 0)
    bc = [t for t in texs if 'Base' in t or 'base' in t or t.endswith('_0') or 'Color' in t]
    return texs

if 'mats' in STEPS:
    # skinned-mesh textures: Interchange skeletal meshes carry no UV-density data, so the streamer keeps them at the
    # smallest mip in -game -> never stream them (they are small: 2x1k dog + 2k feather atlas)
    for path in (D + '/Dog', D + '/Tex', D + '/Wings'):
        for a in reg.get_assets_by_path(path, recursive=True):
            if str(a.asset_class_path.asset_name) == 'Texture2D' and 'Ground' not in str(a.package_name):
                t = a.get_asset(); t.set_editor_property('never_stream', True); EAL.save_loaded_asset(t); log('never_stream %s' % a.package_name)
    texs = [str(a.package_name) for a in reg.get_assets_by_path(D + '/Dog', recursive=True) if str(a.asset_class_path.asset_name) == 'Texture2D']
    log('dog textures %s' % texs)
    # read the roles from the Interchange glTF material instance (asset registry order is not stable)
    BC, MR = [], []
    for a in reg.get_assets_by_path(D + '/Dog', recursive=True):
        if str(a.asset_class_path.asset_name) == 'MaterialInstanceConstant':
            for tpv in a.get_asset().get_editor_property('texture_parameter_values'):
                n = str(tpv.parameter_info.name); p = tpv.parameter_value.get_path_name().split('.')[0]
                if n == 'BaseColorTexture': BC.append(p)
                if n == 'MetallicRoughnessTexture': MR.append(p)
    log('BC %s MR %s' % (BC, MR))
    # ---- fur
    m = new_mat(D + '/Mat/M_AralezFur')
    m.set_editor_property('two_sided', True); m.set_editor_property('used_with_skeletal_mesh', True)
    bc = tp(m, 'BaseTex', BC[0], -1400, -300)
    lum = E(m, unreal.MaterialExpressionDotProduct, -1150, -420); ML.connect_material_expressions(bc, 'RGB', lum, 'A')
    ML.connect_material_expressions(E(m, unreal.MaterialExpressionConstant3Vector, -1350, -500, constant=unreal.LinearColor(0.3, 0.59, 0.11, 1)), '', lum, 'B')
    de = lerp(m, bc, lum, sp(m, 'Desat', 0.0, -1300, -150), -1000, -300, ao='RGB')
    col = mul(m, de, vp(m, 'Tint', (1, 1, 1, 1), -1100, -120), -880, -300)
    col2 = mul(m, col, sp(m, 'Brightness', 1.0, -880, -120), -680, -300)
    ML.connect_material_property(col2, '', MP.MP_BASE_COLOR)
    if MR:
        mr = tp(m, 'MRTex', MR[0], -1400, 50); mr.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        r = mul(m, mr, sp(m, 'RoughScale', 0.85, -1150, 200), -900, 60, ao='G')
        ML.connect_material_property(r, '', MP.MP_ROUGHNESS)
    else:
        ML.connect_material_property(sp(m, 'Roughness', 0.8, -900, 60), '', MP.MP_ROUGHNESS)
    ML.connect_material_property(sp(m, 'Specular', 0.32, -900, 250), '', MP.MP_SPECULAR)
    rm = rim(m, -1400, 450, 3.2, 0.5)
    glow = mul(m, col2, sp(m, 'DivineGlow', 0.04, -700, 650), -500, 600)
    em = addn(m, rm, glow, -300, 450)
    ML.connect_material_property(em, '', MP.MP_EMISSIVE_COLOR)
    ML.recompile_material(m); EAL.save_loaded_asset(m); log('built M_AralezFur')
    # ---- fur shells: N extra skinned copies pushed out along the normal (WPO), alpha-tested strand dots
    m = new_mat(D + '/Mat/M_AralezFurShell')
    m.set_editor_property('used_with_skeletal_mesh', True); m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property('opacity_mask_clip_value', 0.2)
    bc = tp(m, 'BaseTex', BC[0], -1600, -300)
    frac = sp(m, 'ShellFrac', 0.5, -1600, 0)
    dark = lerp(m, sp(m, 'RootDark', 0.75, -1400, 80), sp(m, 'TipBright', 1.05, -1400, 160), frac, -1200, 60)
    col = mul(m, mul(m, bc, vp(m, 'Tint', (1, 1, 1, 1), -1400, -150), -1200, -300, ao='RGB'), dark, -1000, -300)
    ML.connect_material_property(col, '', MP.MP_BASE_COLOR)
    ML.connect_material_property(sp(m, 'Roughness', 0.85, -1000, -100), '', MP.MP_ROUGHNESS)
    ML.connect_material_property(sp(m, 'Specular', 0.25, -1000, 0), '', MP.MP_SPECULAR)
    tc = E(m, unreal.MaterialExpressionTextureCoordinate, -1800, 400, u_tiling=1.0, v_tiling=1.0)
    uvs = mul(m, tc, sp(m, 'StrandTiling', 70.0, -1800, 520), -1600, 400)
    st = tp(m, 'StrandTex', D + '/Tex/T_FurStrands', -1400, 400, masks=True); ML.connect_material_expressions(uvs, '', st, 'UVs')
    thr = mul(m, frac, sp(m, 'Taper', 0.75, -1400, 650), -1200, 600)
    sub = E(m, unreal.MaterialExpressionSubtract, -1000, 450); ML.connect_material_expressions(st, 'R', sub, 'A'); ML.connect_material_expressions(thr, '', sub, 'B')
    lum = E(m, unreal.MaterialExpressionDotProduct, -1400, 800); ML.connect_material_expressions(bc, 'RGB', lum, 'A')
    ML.connect_material_expressions(E(m, unreal.MaterialExpressionConstant3Vector, -1600, 850, constant=unreal.LinearColor(0.3, 0.59, 0.11, 1)), '', lum, 'B')
    lm = E(m, unreal.MaterialExpressionSubtract, -1200, 800); ML.connect_material_expressions(lum, '', lm, 'A'); ML.connect_material_expressions(sp(m, 'DarkCut', 0.12, -1400, 950), '', lm, 'B')
    body = E(m, unreal.MaterialExpressionSaturate, -900, 800); ML.connect_material_expressions(mul(m, lm, sp(m, 'Ten', 12.0, -1200, 950), -1050, 800), '', body, '')
    ML.connect_material_property(mul(m, sub, body, -700, 500), '', MP.MP_OPACITY_MASK)
    nrm = E(m, unreal.MaterialExpressionVertexNormalWS, -1400, 1100)
    fl = mul(m, frac, sp(m, 'FurLength', 1.4, -1400, 1250), -1200, 1150)
    off = mul(m, nrm, fl, -1000, 1100)
    droop = mul(m, mul(m, fl, frac, -1200, 1300), E(m, unreal.MaterialExpressionConstant3Vector, -1200, 1400, constant=unreal.LinearColor(0, 0, -0.35, 1)), -1000, 1300)
    ML.connect_material_property(addn(m, off, droop, -800, 1150), '', MP.MP_WORLD_POSITION_OFFSET)
    rm = rim(m, -1600, 1500, 3.0, 0.25); ML.connect_material_property(rm, '', MP.MP_EMISSIVE_COLOR)
    ML.recompile_material(m); EAL.save_loaded_asset(m); log('built M_AralezFurShell')
    # ---- feathers
    m = new_mat(D + '/Mat/M_AralezFeather')
    m.set_editor_property('two_sided', True); m.set_editor_property('used_with_skeletal_mesh', True)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED); m.set_editor_property('opacity_mask_clip_value', 0.4)
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    bc = tp(m, 'FeatherTex', D + '/Tex/T_Feather_BC', -1400, -300)
    vcol = E(m, unreal.MaterialExpressionVertexColor, -1600, -500)
    jit = lerp(m, sp(m, 'JitterLo', 0.8, -1400, -620), sp(m, 'JitterHi', 1.12, -1400, -560), vcol, -1200, -560, alo='G')   # per-feather brightness (vertex colour G = random)
    side = E(m, unreal.MaterialExpressionTwoSidedSign, -1400, -700)
    sat = E(m, unreal.MaterialExpressionSaturate, -1100, -700); ML.connect_material_expressions(side, '', sat, '')
    under = lerp(m, sp(m, 'UnderDark', 0.78, -1250, -760), sp(m, 'One3', 1.0, -1250, -700), sat, -1000, -720)   # backfaces (underside) a bit darker
    col0 = mul(m, bc, vp(m, 'Tint', (1, 0.97, 0.92, 1), -1150, -150), -900, -300, ao='RGB')
    col = mul(m, mul(m, col0, jit, -750, -400), under, -600, -400)
    ML.connect_material_property(col, '', MP.MP_BASE_COLOR)
    ML.connect_material_property(bc, 'A', MP.MP_OPACITY_MASK)
    nn = tp(m, 'FeatherN', D + '/Tex/T_Feather_N', -1400, 0, normal=True)
    ML.connect_material_property(nn, 'RGB', MP.MP_NORMAL)
    rt = tp(m, 'FeatherRT', D + '/Tex/T_Feather_RT', -1400, 300, masks=True)
    r = mul(m, rt, sp(m, 'RoughScale', 1.2, -1150, 420), -900, 300, ao='R')
    ML.connect_material_property(r, '', MP.MP_ROUGHNESS)
    ML.connect_material_property(sp(m, 'Specular', 0.22, -900, 450), '', MP.MP_SPECULAR)
    om = E(m, unreal.MaterialExpressionOneMinus, -1150, 560); ML.connect_material_expressions(rt, 'G', om, '')
    tr = mul(m, om, vp(m, 'TransColor', (1.0, 0.70, 0.40, 1), -1150, 680), -900, 600)
    tr2 = mul(m, tr, sp(m, 'TransIntensity', 0.7, -900, 760), -700, 600)
    ML.connect_material_property(tr2, '', MP.MP_SUBSURFACE_COLOR)
    vc = E(m, unreal.MaterialExpressionVertexColor, -1400, 900)
    tipw = addn(m, mul(m, vc, sp(m, 'TipGlowBias', 0.65, -1200, 1050), -1050, 900, ao='R'), sp(m, 'RimBase', 0.35, -1050, 1050), -850, 900)
    rm = rim(m, -1400, 1200, 3.0, 0.55)
    em = mul(m, rm, tipw, -500, 1000)
    ML.connect_material_property(em, '', MP.MP_EMISSIVE_COLOR)
    ML.recompile_material(m); EAL.save_loaded_asset(m); log('built M_AralezFeather')
    # ---- divine halo shell (additive, unlit): bright at the centre of the shell, invisible at its silhouette
    m = new_mat(D + '/Mat/M_AralezHalo')
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE); m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property('used_with_skeletal_mesh', True); m.set_editor_property('two_sided', False)
    fr = E(m, unreal.MaterialExpressionFresnel, -1200, 0); ML.connect_material_expressions(sp(m, 'One', 1.0, -1400, 0), '', fr, 'ExponentIn')
    nv = E(m, unreal.MaterialExpressionOneMinus, -1000, 0); ML.connect_material_expressions(fr, '', nv, '')
    ring = mul(m, nv, fr, -900, -100)                       # NdotV * (1 - NdotV): 0 at the centre and at the silhouette
    ring4 = mul(m, ring, sp(m, 'Four', 4.0, -1000, -200), -800, -100)
    pw = E(m, unreal.MaterialExpressionPower, -700, 0); ML.connect_material_expressions(ring4, '', pw, 'Base'); ML.connect_material_expressions(sp(m, 'Falloff', 3.0, -1000, 150), '', pw, 'Exp')
    df = E(m, unreal.MaterialExpressionDepthFade, -800, 300); ML.connect_material_expressions(sp(m, 'One2', 1.0, -1000, 300), '', df, 'Opacity'); ML.connect_material_expressions(sp(m, 'FadeDistance', 80.0, -1000, 420), '', df, 'FadeDistance')
    c = mul(m, pw, df, -600, 100)
    c2 = mul(m, c, vp(m, 'Color', (1.0, 0.72, 0.36, 1), -600, 300), -400, 100)
    c3 = mul(m, c2, sp(m, 'Intensity', 0.35, -400, 300), -200, 100)
    ML.connect_material_property(c3, '', MP.MP_EMISSIVE_COLOR)
    ML.recompile_material(m); EAL.save_loaded_asset(m); log('built M_AralezHalo')
    if 'scene' in STEPS:   # test-scene only: ground, Poly Haven grass, fog-free sky
        # ---- ground (world-aligned UVs, two scales to hide tiling)
        gt = {str(a.asset_name): str(a.package_name) for a in reg.get_assets_by_path(D + '/Tex/Ground')}
        log('ground tex %s' % gt)
        def find(k): return [v for n, v in gt.items() if k in n][0]
        m = new_mat(D + '/Mat/M_Ground')
        wp = E(m, unreal.MaterialExpressionWorldPosition, -2000, 0)
        msk = E(m, unreal.MaterialExpressionComponentMask, -1800, 0, r=True, g=True, b=False, a=False); ML.connect_material_expressions(wp, '', msk, '')
        uv1 = E(m, unreal.MaterialExpressionDivide, -1600, 0); ML.connect_material_expressions(msk, '', uv1, 'A'); ML.connect_material_expressions(sp(m, 'TileSize', 800.0, -1800, 150), '', uv1, 'B')
        rot = E(m, unreal.MaterialExpressionRotator, -1700, 300, speed=1.0, center_x=0.0, center_y=0.0)
        ML.connect_material_expressions(uv1, '', rot, 'Coordinate'); ML.connect_material_expressions(sp(m, 'RotAngle', 0.65, -1900, 420), '', rot, 'Time')
        uv2 = E(m, unreal.MaterialExpressionMultiply, -1500, 300); ML.connect_material_expressions(rot, '', uv2, 'A'); ML.connect_material_expressions(sp(m, 'Scale2', 0.73, -1700, 450), '', uv2, 'B')
        uv3 = E(m, unreal.MaterialExpressionDivide, -1600, 600); ML.connect_material_expressions(msk, '', uv3, 'A'); ML.connect_material_expressions(sp(m, 'TileSize3', 9700.0, -1800, 650), '', uv3, 'B')
        def samp(tex, uv, x, y, **kw):
            e = tp(m, kw.pop('name'), tex, x, y, **kw); ML.connect_material_expressions(uv, '', e, 'UVs'); return e
        d1 = samp(find('diff'), uv1, -1300, -200, name='Diff'); d2 = samp(find('diff'), uv2, -1300, 0, name='Diff2')
        n1 = samp(find('nor'), uv1, -1300, 250, name='Nor', normal=True)
        a1 = samp(find('arm'), uv1, -1300, 500, name='Arm', masks=True)
        d3 = samp(find('diff'), uv3, -1300, 750, name='Diff3')
        bl = lerp(m, d1, d2, d3, -1000, -100, ao='RGB', bo='RGB', alo='G')                 # large-scale sample drives the mix
        mac = E(m, unreal.MaterialExpressionPower, -1000, 700); ML.connect_material_expressions(d3, 'G', mac, 'Base'); ML.connect_material_expressions(sp(m, 'MacroPow', 0.6, -1150, 800), '', mac, 'Exp')
        bl2 = mul(m, bl, addn(m, mac, sp(m, 'MacroBias', 0.55, -900, 800), -800, 700), -800, -100)
        col = mul(m, bl2, vp(m, 'Tint', (0.85, 0.82, 0.78, 1), -1000, 50), -600, -100)
        ML.connect_material_property(col, '', MP.MP_BASE_COLOR)
        n2 = samp(find('nor'), uv2, -1300, 1000, name='Nor2', normal=True)
        nb = lerp(m, n1, n2, d3, -1000, 250, ao='RGB', bo='RGB', alo='G')
        pd = E(m, unreal.MaterialExpressionPixelDepth, -1300, 1250)
        fd = E(m, unreal.MaterialExpressionDivide, -1150, 1250); ML.connect_material_expressions(pd, '', fd, 'A'); ML.connect_material_expressions(sp(m, 'NormalFadeDist', 2500.0, -1300, 1350), '', fd, 'B')
        fs = E(m, unreal.MaterialExpressionSaturate, -1000, 1250); ML.connect_material_expressions(fd, '', fs, '')
        flat = E(m, unreal.MaterialExpressionConstant3Vector, -1000, 1400, constant=unreal.LinearColor(0, 0, 1, 1))
        nf = lerp(m, nb, flat, fs, -800, 250)       # grazing sun turns tiled normal detail into stripes far away -> fade to flat
        ML.connect_material_property(nf, '', MP.MP_NORMAL)
        ML.connect_material_property(a1, 'G', MP.MP_ROUGHNESS)
        ML.connect_material_property(a1, 'R', MP.MP_AMBIENT_OCCLUSION)
        ML.recompile_material(m); EAL.save_loaded_asset(m); log('built M_Ground')
        m = new_mat(D + '/Mat/M_Foliage')
        m.set_editor_property('two_sided', True); m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED); m.set_editor_property('opacity_mask_clip_value', 0.35)
        m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        m.set_editor_property('used_with_instanced_static_meshes', True)
        G = '/Game/Aralez/Props/grass_medium_01/grass_medium_01_1k/Textures/'
        bc = tp(m, 'BaseTex', G + 'grass_medium_01_diff-grass_medium_01_alpha', -1200, -200)
        col = mul(m, bc, vp(m, 'Tint', (0.95, 0.85, 0.62, 1), -1000, -50), -800, -200, ao='RGB')
        ML.connect_material_property(col, '', MP.MP_BASE_COLOR); ML.connect_material_property(bc, 'A', MP.MP_OPACITY_MASK)
        nn = tp(m, 'NormalTex', G + 'grass_medium_01_nor_gl', -1200, 100, normal=True); ML.connect_material_property(nn, 'RGB', MP.MP_NORMAL)
        ML.connect_material_property(sp(m, 'Roughness', 0.85, -800, 200), '', MP.MP_ROUGHNESS)
        ML.connect_material_property(mul(m, col, sp(m, 'Trans', 0.6, -800, 400), -600, 300), '', MP.MP_SUBSURFACE_COLOR)
        ML.recompile_material(m); EAL.save_loaded_asset(m); log('built M_Foliage')
        for a in reg.get_assets_by_path(D + '/Props/grass_medium_01', recursive=True):
            if str(a.asset_class_path.asset_name) == 'StaticMesh':
                sm = a.get_asset(); sm.set_material(0, m); EAL.save_loaded_asset(sm)
        # sky dome that ignores height fog: translucent (opacity 1) with fogging disabled; same cube lookup as M_SkyHDRI
        m = new_mat(D + '/Mat/M_AralezSky')
        m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT); m.set_editor_property('two_sided', True)
        m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        for k, v in (('use_translucency_vertex_fog', False), ('compute_fog_per_pixel', False), ('is_sky', True), ('disable_depth_test', False)):
            try: m.set_editor_property(k, v)
            except Exception as e: log('sky prop %s %s' % (k, e))
        cv = E(m, unreal.MaterialExpressionCameraVectorWS, -1200, 0)
        neg = mul(m, cv, sp(m, 'MinusOne', -1.0, -1200, 150), -1000, 0)
        cube = E(m, unreal.MaterialExpressionTextureSampleParameterCube, -800, 0, parameter_name='SkyCube', texture=unreal.load_asset(D + '/HDRI/kloppenheim_06_puresky_4k'))
        ML.connect_material_expressions(neg, '', cube, 'UVs')
        em = mul(m, cube, sp(m, 'Exposure', 1.0, -800, 250), -500, 0, ao='RGB')
        ML.connect_material_property(em, '', MP.MP_EMISSIVE_COLOR)
        ML.connect_material_property(sp(m, 'Opacity', 1.0, -500, 250), '', MP.MP_OPACITY)
        ML.recompile_material(m); EAL.save_loaded_asset(m); log('built M_AralezSky')
    # assign
    def first(path, cls):
        for a in reg.get_assets_by_path(path, recursive=True):
            if str(a.asset_class_path.asset_name) == cls: return a.get_asset()
    dog = first(D + '/Dog', 'SkeletalMesh'); wings = first(D + '/Wings', 'SkeletalMesh')
    for sk, mat in ((dog, D + '/Mat/M_AralezFur'), (wings, D + '/Mat/M_AralezFeather')):
        mats = sk.get_editor_property('materials')
        for sm in mats: sm.set_editor_property('material_interface', unreal.load_asset(mat))
        sk.set_editor_property('materials', mats); EAL.save_loaded_asset(sk)
        log('assigned %s -> %s (%d slots) bones=%d' % (mat, sk.get_path_name(), len(mats), len(sk.get_editor_property('skeleton').get_editor_property('bone_tree'))))
if 'mis' in STEPS:
    # final tuned material instances (the values the screenshots were taken with)
    def mic(path, parent, scalars={}, vectors={}):
        if EAL.does_asset_exist(path): EAL.delete_asset(path)
        d, n = path.rsplit('/', 1)
        m = AT.create_asset(n, d, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        m.set_editor_property('parent', unreal.load_asset(parent))
        for k, v in scalars.items(): ML.set_material_instance_scalar_parameter_value(m, k, v)
        for k, v in vectors.items(): ML.set_material_instance_vector_parameter_value(m, k, unreal.LinearColor(*v))
        ML.update_material_instance(m); EAL.save_loaded_asset(m); log('MI %s' % path); return m
    fur = mic(D + '/Mat/MI_AralezFur', D + '/Mat/M_AralezFur', {'RimIntensity': 0.18, 'DivineGlow': 0.03, 'Roughness': 0.78, 'Specular': 0.3, 'Desat': 0.15, 'Brightness': 1.0, 'RoughScale': 0.85, 'RimExp': 3.2},
              {'Tint': (1.0, 0.96, 0.9, 1), 'RimColor': (1.0, 0.74, 0.42, 1)})
    fea = mic(D + '/Mat/MI_AralezFeather', D + '/Mat/M_AralezFeather', {'RimIntensity': 0.2, 'TransIntensity': 0.2, 'Specular': 0.22, 'RoughScale': 1.2, 'UnderDark': 0.78, 'JitterLo': 0.8, 'JitterHi': 1.12},
              {'Tint': (1.0, 0.97, 0.92, 1), 'RimColor': (1.0, 0.76, 0.45, 1), 'TransColor': (1.0, 0.70, 0.40, 1)})
    for i in (1, 2):
        mic(D + '/Mat/MI_AralezFurShell_%d' % i, D + '/Mat/M_AralezFurShell', {'ShellFrac': i / 2.0, 'FurLength': 1.4, 'RimIntensity': 0.18, 'StrandTiling': 70.0, 'Taper': 0.75},
            {'Tint': (1.0, 0.96, 0.9, 1)})
    for a in reg.get_assets_by_path(D, recursive=True):
        if str(a.asset_class_path.asset_name) == 'SkeletalMesh':
            sk = a.get_asset(); mats = sk.get_editor_property('materials')
            for sm in mats: sm.set_editor_property('material_interface', fur if 'Wings' not in str(a.package_name) else fea)
            sk.set_editor_property('materials', mats); EAL.save_loaded_asset(sk); log('slot MI -> %s' % a.package_name)
EAL.save_directory(D)
log('DONE')
