# s3_veg.py - vegetation + rocks: import (as script: HL_ONLY=import), materials, and scatter() into the current level (HISM).
import sys, os, json, glob, array, math, traceback
sys.path.insert(0, '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands/scripts')
import unreal
from hl_common import *
import twmat
from twmat import setup_material, finish_material, get_or_create_material, make_mi, _load
import hl_materials as HM

VEG = VEGGEN + 'veg/'
ROCKS = {  # name: (gltf, LOD0 keep fraction, native size note)
    'rock_07': ('rock_07/rock_07_2k.gltf', 0.25), 'rock_09': ('rock_09/rock_09_2k.gltf', 0.25),
    'namaqualand_boulder_02': ('namaqualand_boulder_02/namaqualand_boulder_02_2k.gltf', 0.04),
    'namaqualand_boulder_05': ('namaqualand_boulder_05/namaqualand_boulder_05_2k.gltf', 0.05),
    'boulder_01': ('boulder_01/boulder_01_2k.gltf', 0.04), 'stone_01': ('stone_01/stone_01_2k.gltf', 0.08)}
ROCK_ORDER = ['boulder_01', 'namaqualand_boulder_02', 'namaqualand_boulder_05', 'rock_07', 'rock_09', 'stone_01']
GRASS = ['GrassDry_0', 'GrassDry_1', 'GrassDry_2', 'GrassDry_3', 'GrassGreen_0', 'GrassGreen_1', 'GrassGreen_2', 'GrassGreen_3',
         'GrassScan_a', 'GrassScan_b', 'GrassScan_c', 'GrassScan_d']
FLOWERS = ['Daisy_%d' % i for i in range(6)] + ['Poppy_%d' % i for i in range(6)]


def set_lods(sm, fracs, sizes):
    o = unreal.StaticMeshReductionOptions(); o.auto_compute_lod_screen_size = False
    rs = []
    for f, s in zip(fracs, sizes):
        r = unreal.StaticMeshReductionSettings(); r.percent_triangles = f; r.screen_size = s; rs.append(r)
    o.reduction_settings = rs
    SMS.set_lods_with_notification(sm, o, True)


def import_all():
    import_textures(sorted(glob.glob(VEG + 'T_*_D.png')), '/Game/Env/Veg/Tex', 'color')
    import_textures(sorted(glob.glob(VEG + 'T_*_N.png')), '/Game/Env/Veg/Tex', 'normal')
    for d in ROCKS:
        import_textures(sorted(glob.glob(P + 'dl/rocks/%s/textures/*.jpg' % d)), '/Game/Env/Rocks/Tex')
    ov = gltf_pipeline('/Game/Pipelines/GLTF_NoNanite_Veg')
    for f in sorted(glob.glob(VEG + 'SM_*.gltf')):
        n = os.path.basename(f)[:-5]
        for sm in import_gltf(ov, f, '/Game/Env/Veg/' + n):
            if n in ('SM_Pine', 'SM_Juniper'):
                set_lods(sm, (1.0, 0.45, 0.18), (1.0, 0.25, 0.08))
            EAL.save_loaded_asset(sm, False); report(sm)
    for name, (rel, frac) in ROCKS.items():
        for sm in import_gltf(ov, P + 'dl/rocks/' + rel, '/Game/Env/Rocks/' + name):
            set_lods(sm, (frac, 0.3, 0.08, 0.025), (1.0, 0.3, 0.1, 0.03))   # LOD1+ fractions are relative to LOD0
            EAL.save_loaded_asset(sm, False); report(sm)


# ------------------------------------------------------------------------------------------- materials
def build_foliage():
    mat = get_or_create_material('M_HLFoliage')
    setup_material(mat, shading='MSM_TWO_SIDED_FOLIAGE', blend='BLEND_MASKED', two_sided=True, usages=('MATUSAGE_INSTANCED_STATIC_MESHES',))
    mat.set_editor_property('opacity_mask_clip_value', 0.33)
    g = HM.H(mat)
    tx = _load('/Game/Env/Veg/Tex/T_GrassDry_D')
    d = g.sample(g.tex_param_obj('Diffuse', tx), tx, g.texcoord(), 'RGBA')
    rgb = g.mask(d, r=True, g=True, b=True)
    rgb = g.lerp(rgb, g.lum(rgb), g.scalar('Desaturate', 0.0, 'Color'))
    pr = g.new(unreal.MaterialExpressionPerInstanceRandom)
    var = g.lerp(g.vec('TintA', (1.0, 1.0, 1.0), 'Color'), g.vec('TintB', (1.12, 1.0, 0.8), 'Color'), pr)
    base = g.mul(g.mul(rgb, var), g.scalar('Brightness', 1.0, 'Color'))
    lp = g.new(unreal.MaterialExpressionLocalPosition)
    hgt = g.sat(g.div(g.mask(lp, b=True), g.scalar('PlantHeight', 50.0, 'Wind')))
    # darker at the base (self-shadowed clump interior) -> reads as dense grass
    base = g.mul(base, g.lerp(g.scalar('BaseDarken', 0.45, 'Color'), g.c1(1.0), g.power(hgt, 0.6)))
    g.out('MP_BASE_COLOR', base)
    g.out('MP_SUBSURFACE_COLOR', g.mul(base, g.scalar('Transmission', 0.8, 'Color')))
    # (1) mip-averaged alpha falls under the clip value far away -> boost alpha with distance (t5: far pines lost their leaves)
    # (2) per-instance progressive thinning toward FadeEnd (no hard edge where the grass patch ends)
    cd = g.cam_dist()
    boost = g.lerp(g.c1(1.0), g.scalar('AlphaBoostMax', 2.2, 'Fade'), g.smooth(cd, 1500.0, g.scalar('AlphaBoostDist', 15000.0, 'Fade')))
    fade = g.smooth(cd, g.scalar('FadeStart', 3000.0, 'Fade'), g.scalar('FadeEnd', 4500.0, 'Fade'))
    keep = g.sat(g.mul(g.sub(g.add(pr, 0.15), g.mul(fade, 1.15)), 8.0))
    g.out('MP_OPACITY_MASK', g.mul(g.sat(g.mul(g.mask(d, a=True), boost)), keep))
    nt = _load('/Game/Env/Veg/Tex/T_GrassDry_N')
    g.out('MP_NORMAL', g.lerp(g.c3(0, 0, 1), g.sample(g.tex_param_obj('Normal', nt), nt, g.texcoord()), g.scalar('NormalStrength', 0.7, 'Surface')))
    g.out('MP_ROUGHNESS', g.scalar('Roughness', 0.75, 'Surface'))
    g.out('MP_SPECULAR', g.scalar('Specular', 0.3, 'Surface'))
    g.out('MP_AMBIENT_OCCLUSION', g.lerp(g.c1(0.5), g.c1(1.0), hgt))
    # wind sway (bends with height^2). Static switch 'Wind': trees/far plants compile WITHOUT WPO, so they skip the
    # velocity pass (perf t4: RenderVelocities 3.9 ms with WPO on all foliage). Distance fade = alpha erosion (no WPO).
    wp = g.world_pos('XYZ')
    t = g.time()
    ph = g.add(g.mul(t, g.scalar('WindSpeed', 0.6, 'Wind')), g.div(g.dot(g.mask(wp, r=True, g=True), g.c2(0.7, 0.4)), g.scalar('WindWave', 900.0, 'Wind')))
    sway = g.mul(g.add(g.sine(ph), g.mul(g.sine(g.mul(ph, 2.7)), 0.35)), g.mul(g.mul(hgt, hgt), g.scalar('WindAmount', 6.0, 'Wind')))
    wpo = g.append(g.mul(g.c2(0.8, 0.5), sway), g.c1(0.0))
    sw = g.new(unreal.MaterialExpressionStaticSwitchParameter, parameter_name='Wind', default_value=False, group='Wind')
    g.link(wpo, sw, 'True'); g.link(g.c3(0.0, 0.0, 0.0), sw, 'False')
    g.out('MP_WORLD_POSITION_OFFSET', sw)
    finish_material(mat)
    return mat


def build_bark():
    mat = get_or_create_material('M_HLBark')
    setup_material(mat, usages=('MATUSAGE_INSTANCED_STATIC_MESHES',))
    g = HM.H(mat)
    tx = _load('/Game/Env/Veg/Tex/T_Pine_Bark_D'); nt = _load('/Game/Env/Veg/Tex/T_Pine_Bark_N')
    d = g.sample(g.tex_param_obj('Diffuse', tx), tx, g.texcoord())
    g.out('MP_BASE_COLOR', g.mul(g.lerp(d, g.lum(d), 0.55), g.vec('Tint', (0.32, 0.26, 0.22), 'Color')))
    g.out('MP_NORMAL', g.sample(g.tex_param_obj('Normal', nt), nt, g.texcoord()))
    g.out('MP_ROUGHNESS', g.scalar('Roughness', 0.85, 'Surface'))
    finish_material(mat)
    return mat


def build_rock():
    """scan boulders graded to Geghama basalt: desaturate, darken, lichen/oxide macro, dusty tops"""
    mat = get_or_create_material('M_HLRock')
    setup_material(mat, usages=('MATUSAGE_INSTANCED_STATIC_MESHES',))
    g = HM.H(mat)
    tx = _load('/Game/Env/Rocks/Tex/boulder_01_diff_2k'); nt = _load('/Game/Env/Rocks/Tex/boulder_01_nor_gl_2k'); at = _load('/Game/Env/Rocks/Tex/boulder_01_arm_2k')
    uv = g.texcoord()
    d = g.sample(g.tex_param_obj('Diffuse', tx), tx, uv)
    a = g.sample(g.tex_param_obj('ARM', at), at, uv)
    lum = g.lum(d)
    base = g.lerp(d, lum, g.scalar('Desaturate', 0.75, 'Grade'))
    base = g.mul(base, g.vec('Tint', (0.36, 0.35, 0.34), 'Grade'))   # Geghama basalt is dark
    pr = g.new(unreal.MaterialExpressionPerInstanceRandom)
    base = g.mul(base, g.lerp(0.75, 1.2, pr))
    nws = g.mask(g.new(unreal.MaterialExpressionVertexNormalWS), b=True)
    up = g.sat(g.mul(g.sub(nws, 0.55), 3.0))
    base = g.lerp(base, g.mul(g.vec('LichenColor', (0.42, 0.40, 0.30), 'Grade'), g.add(g.mul(lum, 0.8), 0.4)), g.mul(up, g.scalar('LichenAmount', 0.45, 'Grade')))
    g.out('MP_BASE_COLOR', base)
    g.out('MP_ROUGHNESS', g.mask(a, g=True))
    g.out('MP_AMBIENT_OCCLUSION', g.mask(a, r=True))
    g.out('MP_NORMAL', g.sample(g.tex_param_obj('Normal', nt), nt, uv))
    finish_material(mat)
    return mat


def build_tree_far():
    """opaque far-LOD crown: flat colour graded like the leaf cards, per-instance variation, darker toward the base/inside"""
    mat = get_or_create_material('M_HLTreeFar')
    setup_material(mat, usages=('MATUSAGE_INSTANCED_STATIC_MESHES',))
    g = HM.H(mat)
    pr = g.new(unreal.MaterialExpressionPerInstanceRandom)
    lp = g.new(unreal.MaterialExpressionLocalPosition)
    h = g.sat(g.div(g.mask(lp, b=True), g.scalar('PlantHeight', 1500.0, 'Color')))
    c = g.lerp(g.vec('ColorA', (0.035, 0.045, 0.025), 'Color'), g.vec('ColorB', (0.055, 0.06, 0.03), 'Color'), pr)
    c = g.mul(c, g.lerp(0.6, 1.15, h))
    # clumpy needle-mass shading: macro noise on local position -> perturbed normal + dark gaps
    mn = _load('/Game/Env/Layers/T_MacroNoise')
    nuv = g.div(g.append(g.add(g.mask(lp, r=True), g.mask(lp, b=True)), g.add(g.mask(lp, g=True), g.mul(g.mask(lp, b=True), 0.7))), g.scalar('ClumpScale', 260.0, 'Color'))
    nz = g.sample(g.tex_param_obj('Noise', mn), mn, nuv, 'RGB')
    gap = g.sat(g.mul(g.sub(g.mask(nz, r=True), 0.35), 3.0))
    c = g.mul(c, g.lerp(0.45, 1.15, gap))
    g.out('MP_NORMAL', g.normalize(g.append(g.mul(g.sub(g.mask(nz, g=True, b=True), 0.5), g.scalar('ClumpNormal', 2.2, 'Color')), g.c1(1.0))))
    g.out('MP_BASE_COLOR', c)
    g.out('MP_ROUGHNESS', g.scalar('Roughness', 0.9, 'Surface'))
    g.out('MP_SPECULAR', g.scalar('Specular', 0.2, 'Surface'))
    finish_material(mat)
    return mat


def materials():
    twmat.ROOT = '/Game/Env/Materials'
    m = {'fol': build_foliage(), 'bark': build_bark(), 'rock': build_rock(), 'far': build_tree_far()}
    make_mi('MI_TreeFar_Pine', m['far'])
    make_mi('MI_TreeFar_Juniper', m['far'], scalars={'PlantHeight': 320.0}, vectors={'ColorA': (0.05, 0.06, 0.035), 'ColorB': (0.07, 0.075, 0.04)})
    T = lambda n: _load('/Game/Env/Veg/Tex/' + n)
    mi = {}
    mi['PineLeaf'] = make_mi('MI_PineLeaf', m['fol'], vectors={'TintA': (0.55, 0.62, 0.45), 'TintB': (0.62, 0.66, 0.45)}, scalars={'PlantHeight': 1500.0, 'WindAmount': 25.0, 'WindWave': 3000.0, 'WindSpeed': 0.4, 'FadeStart': 1e9, 'FadeEnd': 2e9, 'BaseDarken': 0.6, 'Transmission': 0.5},
                             textures={'Diffuse': T('T_Pine_Leaf_D'), 'Normal': T('T_Pine_Leaf_N')})
    mi['JunLeaf'] = make_mi('MI_JuniperLeaf', m['fol'], scalars={'PlantHeight': 320.0, 'WindAmount': 6.0, 'FadeStart': 1e9, 'FadeEnd': 2e9, 'BaseDarken': 0.6, 'Transmission': 0.5},
                            vectors={'TintA': (0.75, 0.8, 0.7), 'TintB': (0.85, 0.85, 0.7)}, textures={'Diffuse': T('T_Juniper_Leaf_D'), 'Normal': T('T_Juniper_Leaf_N')})
    mi['PineBark'] = make_mi('MI_PineBark', m['bark'], textures={'Diffuse': T('T_Pine_Bark_D'), 'Normal': T('T_Pine_Bark_N')})
    mi['JunBark'] = make_mi('MI_JuniperBark', m['bark'], textures={'Diffuse': T('T_Juniper_Bark_D'), 'Normal': T('T_Juniper_Bark_N')})
    make_mi('MI_TreeFar_PineC', m['far'], scalars={'PlantHeight': 1600.0}, vectors={'ColorA': (0.04, 0.05, 0.028), 'ColorB': (0.058, 0.064, 0.034)})
    mi['PineCLeaf'] = make_mi('MI_PineCLeaf', m['fol'], scalars={'PlantHeight': 1600.0, 'FadeStart': 1e9, 'FadeEnd': 2e9, 'BaseDarken': 0.55, 'Transmission': 0.45, 'NormalStrength': 0.0},
                              vectors={'TintA': (0.5, 0.56, 0.45), 'TintB': (0.6, 0.62, 0.48)}, textures={'Diffuse': T('T_PineC_Leaf_D'), 'Normal': T('T_Pine_Leaf_N')})
    mi['PineCBark'] = make_mi('MI_PineCBark', m['bark'], textures={'Diffuse': T('T_PineC_Bark_D'), 'Normal': T('T_Pine_Bark_N')})
    gsc = {'PlantHeight': 50.0, 'WindAmount': 5.0, 'FadeStart': 2200.0, 'FadeEnd': 4000.0}
    for nm, tex in (('GrassDry', 'GrassDry'), ('GrassGreen', 'GrassGreen'), ('GrassScan12', 'GrassScan12'), ('GrassScan07', 'GrassScan07'), ('Poppy', 'Poppy'), ('Daisy', 'Daisy')):
        mi[nm] = make_mi('MI_' + nm, m['fol'], scalars=dict(gsc, Desaturate=0.4 if 'Green' in nm else (0.25 if 'Grass' in nm else 0.0)), textures={'Diffuse': T('T_%s_D' % tex), 'Normal': T('T_%s_N' % tex)},
                         vectors={'TintA': (1.05, 0.88, 0.45), 'TintB': (1.2, 0.95, 0.45)} if 'Green' in nm else ({'TintA': (0.85, 0.78, 0.55), 'TintB': (1.0, 0.85, 0.55)} if 'Grass' in nm else {}))
    for r in ROCKS:
        R = '/Game/Env/Rocks/Tex/%s_' % r
        mi['rock_' + r] = make_mi('MI_Rock_' + r, m['rock'], textures={'Diffuse': _load(R + 'diff_2k'), 'Normal': _load(R + 'nor_gl_2k'), 'ARM': _load(R + 'arm_2k')})
    return mi


# ------------------------------------------------------------------------------------------- scatter
def mesh(n):
    return unreal.load_asset('/Game/Env/Veg/SM_%s/SM_%s/StaticMeshes/SM_%s' % (n, n, n))


def rock_mesh(r):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for a in reg.get_assets_by_path('/Game/Env/Rocks/' + r, recursive=True):
        if str(a.asset_class_path.asset_name) == 'StaticMesh':
            return a.get_asset()


def load_rows(name):
    f = GEN + 'scatter/%s.f32' % name
    if not os.path.exists(f):
        return []
    a = array.array('f'); a.frombytes(open(f, 'rb').read())
    return [a[i:i + 6] for i in range(0, len(a), 6)]


def hism_actor(label, folder='Veg'):
    act = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0), unreal.Rotator())
    act.set_actor_label(label); act.set_folder_path(folder)
    return act


def add_hism(act, sm, mats, rows, cull, shadow, scale_mul=1.0, rand_tilt=0.0, xy_mul=1.0):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = sds.k2_gather_subobject_data_for_instance(act)
    params = unreal.AddNewSubobjectParams(parent_handle=handles[0], new_class=unreal.HierarchicalInstancedStaticMeshComponent)
    h, fail = sds.add_new_subobject(params)
    comp = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))
    comp.set_static_mesh(sm)
    for i, m in enumerate(mats):
        if m is not None:
            comp.set_material(i, m)
    comp.set_editor_property('cast_shadow', shadow)
    comp.set_cull_distances(cull[0], cull[1])
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    xs = []
    import random
    rr = random.Random(len(rows))
    for x, y, z, yaw, s, v in rows:
        s *= scale_mul
        rot = unreal.Rotator(pitch=rr.uniform(-rand_tilt, rand_tilt), yaw=yaw, roll=rr.uniform(-rand_tilt, rand_tilt))
        xs.append(unreal.Transform(unreal.Vector(x, y, z), rot, unreal.Vector(s * xy_mul, s * xy_mul, s)))
    for k in range(0, len(xs), 20000):
        comp.add_instances(xs[k:k + 20000], False, True)
    return comp


def scatter():
    mi = {k: _load('/Game/Env/Materials/' + v) for k, v in [('PineLeaf', 'MI_PineLeaf'), ('JunLeaf', 'MI_JuniperLeaf'), ('PineBark', 'MI_PineBark'), ('JunBark', 'MI_JuniperBark'),
                                                           ('GrassDry', 'MI_GrassDry'), ('GrassGreen', 'MI_GrassGreen'), ('GrassScan12', 'MI_GrassScan12'), ('GrassScan07', 'MI_GrassScan07'),
                                                           ('Poppy', 'MI_Poppy'), ('Daisy', 'MI_Daisy')]}
    C = json.load(open(P + 'scripts/veg_params.json'))
    tot = {}
    rows = load_rows('Pine')
    if rows:
        a = hism_actor('Veg_Pine')
        if C.get('pine_model', 'PineC') == 'PineC':
            add_hism(a, mesh('PineC'), [_load('/Game/Env/Materials/MI_PineCBark'), _load('/Game/Env/Materials/MI_PineCLeaf'), _load('/Game/Env/Materials/MI_TreeFar_PineC')], rows, C['pine_cull'], True, 1.0, 2.0)
        else:
            add_hism(a, mesh('Pine'), [mi['PineBark'], mi['PineLeaf'], _load('/Game/Env/Materials/MI_TreeFar_Pine')], rows, C['pine_cull'], True, 1.0, 2.0)
        tot['Pine'] = len(rows)
    rows = load_rows('Juniper')
    if rows:
        a = hism_actor('Veg_Juniper')
        add_hism(a, mesh('Juniper'), [mi['JunBark'], mi['JunLeaf'], _load('/Game/Env/Materials/MI_TreeFar_Juniper')], rows, C['juniper_cull'], True, 1.0, 4.0); tot['Juniper'] = len(rows)
    for nm, key, cull, smul in (('Rock', 'rock', C['rock_cull'], 1.0), ('ShoreRock', 'shore', C['shore_cull'], 1.0)):
        rows = load_rows(nm)
        if not rows:
            continue
        a = hism_actor('Rocks_' + nm, 'Rocks')
        for vi, r in enumerate(ROCK_ORDER):
            sub = [x for x in rows if int(x[5]) == vi]
            if sub:
                add_hism(a, rock_mesh(r), [_load('/Game/Env/Materials/MI_Rock_' + r)], sub, cull, nm == 'Rock', C['rock_scale'][r] * smul, 25.0)
        tot[nm] = len(rows)
    rows = load_rows('Grass')
    if rows:
        a = hism_actor('Veg_Grass')
        for vi, n in enumerate(GRASS):
            sub = [x for x in rows if int(x[5]) == vi]
            m = mi['GrassDry'] if 'Dry' in n else mi['GrassGreen'] if 'Green' in n else (mi['GrassScan07'] if n.endswith('_d') else mi['GrassScan12'])
            if sub:
                add_hism(a, mesh(n), [m], sub, C['grass_cull'], C['grass_shadow'], 1.0, 8.0, C['grass_xy'])
        tot['Grass'] = len(rows)
    rows = load_rows('Flower')
    if rows:
        a = hism_actor('Veg_Flowers')
        for vi, n in enumerate(FLOWERS):
            sub = [x for x in rows if int(x[5]) == vi]
            if sub:
                add_hism(a, mesh(n), [mi['Poppy'] if 'Poppy' in n else mi['Daisy']], sub, C['grass_cull'], False, 1.0, 6.0)
        tot['Flower'] = len(rows)
    log('scatter %s' % tot)


if __name__ == '__main__' or os.environ.get('HL_VEGSCRIPT'):
    try:
        ONLY = os.environ.get('HL_ONLY', 'import,mat')
        if 'import' in ONLY:
            import_all()
        if 'treelod' in ONLY:
            ov = gltf_pipeline('/Game/Pipelines/GLTF_NoNanite_Veg')
            far_mi = _load('/Game/Env/Materials/MI_TreeFar_Pine')
            for n, sizes, fmi in (('Pine', (1.0, 0.24, 0.12, 0.075, 0.05), 'MI_TreeFar_Pine'), ('Juniper', (1.0, 0.12, 0.05, 0.03), 'MI_TreeFar_Juniper'),
                                  ('PineC', (1.0, 0.5, 0.25, 0.08), 'MI_TreeFar_PineC')):
                if mesh(n) is None:
                    continue
                sm = mesh(n)
                SMS.remove_lods(sm)
                k = 1
                while os.path.exists(VEG + 'lods/SM_%s_L%d.gltf' % (n, k)):
                    lm = import_gltf(ov, VEG + 'lods/SM_%s_L%d.gltf' % (n, k), '/Game/Env/Veg/LODs/%s_L%d' % (n, k))[0]
                    SMS.set_lod_from_static_mesh(sm, k, lm, 0, True)
                    k += 1
                SMS.set_lod_screen_sizes(sm, list(sizes[:k]))
                # far LOD (last) section 1 = lathe crown -> its own opaque material slot 'Far'
                mats = list(sm.get_editor_property('static_materials'))
                names = [str(m.get_editor_property('material_slot_name')) for m in mats]
                if 'Far' not in names:
                    mats.append(unreal.StaticMaterial(material_interface=_load('/Game/Env/Materials/' + fmi), material_slot_name='Far'))
                    sm.set_editor_property('static_materials', mats); names.append('Far')
                else:
                    mats[names.index('Far')].set_editor_property('material_interface', _load('/Game/Env/Materials/' + fmi))
                    sm.set_editor_property('static_materials', mats)
                for lod in range(1, k - 1):            # set_lod_from_static_mesh mapped the leaf section to slot 0 (bark)
                    SMS.set_lod_material_slot(sm, 1, lod, 1)
                SMS.set_lod_material_slot(sm, names.index('Far'), k - 1, 1)
                EAL.save_loaded_asset(sm, False); report(sm)
                log('slots %s' % names)
        if 'rocklod' in ONLY:
            for name, (rel, frac) in ROCKS.items():
                sm = rock_mesh(name); set_lods(sm, (frac, 0.3, 0.08, 0.025), (1.0, 0.3, 0.1, 0.03)); EAL.save_loaded_asset(sm, False); report(sm)
        if 'mat' in ONLY:
            materials()
    except Exception:
        unreal.log_error('HL s3 failed\n' + traceback.format_exc())
    log('S3 DONE')
    unreal.SystemLibrary.quit_editor()
