# hl_materials.py - materials for the Armenian-highlands environment (G-helper style of Game/Tools/materials_build.py).
#   M_HLTerrain   one master for all DEM tiles (core/mid/far MIs swap the region maps)
#   M_HLLake      opaque lake surface (SSR + sky cubemap reflections, analytic ripples)
#   M_HLSky       unlit IsSky dome from the HDRI cube, yaw-aligned with the sun
#   M_HLFoliage   two-sided masked foliage (cards) with wind WPO, translucency-like backlight, distance fade
#   M_HLBark / M_HLRock  simple PBR for trunks and scanned boulders (world macro variation, basalt grading)
import unreal, math
import twmat
from twmat import G, setup_material, finish_material, get_or_create_material, make_mi, _load, enum_val

twmat.ROOT = '/Game/Env/Materials'
WRAP = unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS
CLAMP = unreal.SamplerSourceMode.SSM_CLAMP_WORLD_GROUP_SETTINGS
L = '/Game/Env/Layers/'
import os as _os
_S = _os.environ.get('HL_SITE', '')
M = '/Game/Terrain' + ('_' + _S if _S else '') + '/Maps/'
MSFX = ('_' + _S) if _S else ''


class H(G):
    """G + shared samplers (more than 16 textures in the terrain) + small helpers"""
    def sample(self, obj, tex, uv, out='RGB', src=WRAP):
        n, o = G.sample(self, obj, tex, uv, out)
        n.set_editor_property('sampler_source', src)
        return (n, o)

    def tex(self, name, path, uv, out='RGB', src=WRAP):
        t = _load(path)
        if t is None:
            raise RuntimeError('missing texture ' + path)
        return self.sample(self.tex_param_obj(name, t), t, uv, out, src)

    def smooth(self, x, a, b):          # linear ramp 0..1 between a and b (cheap smoothstep stand-in)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return self.sat(self.div(self.sub(x, a), float(b - a)))
        return self.sat(self.div(self.sub(x, a), self.maxx(self.sub(b, a), 1e-4)))

    def cam_dist(self):
        d = self.new(unreal.MaterialExpressionDistance)
        self.link(self.new(unreal.MaterialExpressionCameraPositionWS), d, 'A')
        self.link(self.world_pos('XYZ'), d, 'B')
        return d

    def lum(self, c):
        return self.dot(c, self.c3(0.3, 0.59, 0.11))


def build_terrain():
    mat = get_or_create_material('M_HLTerrain')
    setup_material(mat)
    mat.set_editor_property('tangent_space_normal', False)
    g = H(mat)
    uv = g.texcoord()
    wp = g.world_pos('XYZ')
    wxy = g.mask(wp, r=True, g=True)
    dist = g.cam_dist()
    # ---- region maps (clamped, shared sampler)
    nw = g.normalize(g.tex('RegionNormal', M + 'T_core_N', uv, 'RGB', CLAMP))
    mk = g.tex('RegionMask', M + 'T_core_Mask', uv, 'RGBA', CLAMP)
    lt = g.tex('RegionLight', M + 'T_core_Light', uv, 'RGBA', CLAMP)
    rockM, screeM, snowM, lushM = g.mask(mk, r=True), g.mask(mk, g=True), g.mask(mk, b=True), g.mask(mk, a=True)
    sunv, ao, stream, shoreM = g.mask(lt, r=True), g.mask(lt, g=True), g.mask(lt, b=True), g.mask(lt, a=True)
    # ---- macro noise (two scales) breaks every repetition and adds patchy colour like real pasture
    mn = _load(L + 'T_MacroNoise')
    mobj = g.tex_param_obj('MacroNoise', mn)
    m1 = g.sample(mobj, mn, g.div(wxy, g.scalar('MacroScale1', 52000.0, 'Macro')), 'RGB')
    m2 = g.sample(mobj, mn, g.div(wxy, g.scalar('MacroScale2', 6100.0, 'Macro')), 'RGB')
    m1r, m1g, m1b = g.mask(m1, r=True), g.mask(m1, g=True), g.mask(m1, b=True)
    m2r, m2b = g.mask(m2, r=True), g.mask(m2, b=True)
    # ---- meadow: aerial_grass_rock (15 m scan) at two scales
    mt = g.scalar('MeadowTile', 1500.0, 'Meadow')
    mdo = g.tex_param_obj('MeadowDiff', _load(L + 'aerial_grass_rock_diff_2k'))
    def rot(v, deg):                    # rotate world XY so the tiles of different scales never line up (t12/van: rows visible)
        a = math.radians(deg)
        return g.append(g.dot(v, g.c2(math.cos(a), -math.sin(a))), g.dot(v, g.c2(math.sin(a), math.cos(a))))
    mtex = _load(L + 'aerial_grass_rock_diff_2k')
    mda = g.sample(mdo, mtex, g.div(rot(wxy, 11.0), mt))
    mdb = g.sample(mdo, mtex, g.div(rot(wxy, 47.0), g.mul(mt, 3.37)))
    mdc = g.sample(mdo, mtex, g.div(rot(wxy, -29.0), g.mul(mt, 0.43)))
    meadow = g.lerp(g.lerp(mda, mdb, g.add(g.mul(m2r, 0.5), 0.25)), mdc, g.mul(m1b, 0.6))
    lushA = g.sat(g.add(lushM, g.mul(g.sub(m1g, 0.5), g.scalar('LushNoise', 0.8, 'Meadow'))))
    tint = g.lerp(g.vec('DryTint', (1.18, 0.98, 0.62), 'Meadow'), g.vec('LushTint', (0.88, 0.95, 0.5), 'Meadow'), lushA)
    meadow = g.mul(g.mul(meadow, tint), g.lerp(g.scalar('MacroMin', 0.72, 'Macro'), g.scalar('MacroMax', 1.22, 'Macro'), g.mul(g.add(m1r, m2r), 0.5)))
    meadow = g.mul(meadow, g.scalar('MeadowBright', 1.0, 'Meadow'))
    # real aerial photo (rocky_terrain_02, 90 m scan) as a luminance overlay: 1-50 m scale patchiness, paths, stones
    ovt = _load(L + 'rocky_terrain_02_diff_2k')
    ovl = g.div(g.lum(g.sample(g.tex_param_obj('OverlayDiff', ovt), ovt, g.div(wxy, g.scalar('OverlayTile', 9000.0, 'Meadow')))), 0.069)
    meadow = g.mul(meadow, g.lerp(g.c1(1.0), g.power(g.maxx(ovl, 0.05), 0.7), g.scalar('OverlayAmount', 0.55, 'Meadow')))
    mnrm = g.tex('MeadowNormal', L + 'aerial_grass_rock_nor_gl_2k', g.div(wxy, mt))
    # ---- rock: lichen_rock, triplanar from the region normal (basalt grading)
    rt = g.scalar('RockTile', 1100.0, 'Rock')
    p = g.div(wp, rt)
    w = g.power(g.absx(nw), 4.0)
    w = g.div(w, g.dot(w, g.c3(1.0, 1.0, 1.0)))
    rdt = _load(L + 'lichen_rock_diff_2k')
    rdo = g.tex_param_obj('RockDiff', rdt)
    rx = g.sample(rdo, rdt, g.append(g.mask(p, g=True), g.mask(p, b=True)))
    ry = g.sample(rdo, rdt, g.append(g.mask(p, r=True), g.mask(p, b=True)))
    rz = g.lerp(g.sample(rdo, rdt, g.append(g.mask(p, r=True), g.mask(p, g=True))),
                g.sample(rdo, rdt, g.mul(g.append(g.mask(p, g=True), g.mask(p, r=True)), 0.37)), m2r)   # 2 scales, rotated: no grid
    rock = g.add(g.add(g.mul(rx, g.mask(w, r=True)), g.mul(ry, g.mask(w, g=True))), g.mul(rz, g.mask(w, b=True)))
    rock = g.lerp(rock, g.lum(rock), g.scalar('RockDesat', 0.45, 'Rock'))
    rock = g.mul(g.mul(rock, g.vec('RockTint', (1.9, 1.85, 1.8), 'Rock')), g.lerp(0.75, 1.25, m2b))
    # far away the 11 m texture's own low-frequency shading tiles into a grid: fade to its mean colour (macro + overlay remain)
    rmean = g.mul(g.mul(g.vec('RockMean', (0.062, 0.046, 0.031), 'Rock'), g.vec('RockTint', (1.9, 1.85, 1.8), 'Rock')), g.lerp(0.75, 1.25, m2b))
    rock = g.lerp(rock, g.lerp(rmean, g.mul(rmean, g.power(g.maxx(ovl, 0.05), 0.8)), 0.6), g.smooth(dist, 25000.0, 90000.0))
    rnrm = g.tex('RockNormal', L + 'lichen_rock_nor_gl_2k', g.append(g.mask(p, r=True), g.mask(p, g=True)))
    # ---- scree / boulder fields: aerial_rocks_01
    st = g.scalar('ScreeTile', 2400.0, 'Scree')
    scree = g.mul(g.tex('ScreeDiff', L + 'aerial_rocks_01_diff_2k', g.div(wxy, st)), g.vec('ScreeTint', (0.62, 0.6, 0.6), 'Scree'))
    snrm = g.tex('ScreeNormal', L + 'aerial_rocks_01_nor_gl_2k', g.div(wxy, st))
    # ---- snow
    sn = g.mul(g.tex('SnowDiff', L + 'snow_02_diff_2k', g.div(wxy, g.scalar('SnowTile', 500.0, 'Snow'))), g.scalar('SnowBright', 2.0, 'Snow'))
    # ---- shore pebbles (Sevan beach)
    shore = g.mul(g.tex('ShoreDiff', L + 'river_small_rocks_diff_2k', g.div(wxy, g.scalar('ShoreTile', 350.0, 'Shore'))), g.vec('ShoreTint', (0.85, 0.82, 0.78), 'Shore'))
    # ---- blend (masks sharpened with macro noise so edges look natural, not blurry)
    def sharpen(mval, noise, k, bias=0.5):
        return g.sat(g.add(g.mul(g.add(g.sub(mval, bias), g.mul(g.sub(noise, 0.5), 0.35)), k), 0.5))
    sA = g.mul(sharpen(screeM, m2b, 3.0, 0.4), g.scalar('ScreeAmount', 1.0, 'Scree'))
    rA = g.mul(sharpen(rockM, m2r, 3.5, 0.45), g.scalar('RockAmount', 1.0, 'Rock'))
    shA = g.mul(g.smooth(shoreM, g.scalar('ShoreStart', 0.45, 'Shore'), 0.85), g.scalar('ShoreAmount', 1.0, 'Shore'))
    snA = sharpen(snowM, m1b, 4.0, 0.45)
    base = g.lerp(meadow, scree, sA)
    base = g.lerp(base, rock, rA)
    base = g.lerp(base, shore, shA)
    wet = g.smooth(shoreM, 0.8, 0.97)                   # last few metres above the water: wet, dark
    base = g.mul(base, g.lerp(g.c1(1.0), g.scalar('WetDarken', 0.55, 'Shore'), wet))
    base = g.mul(base, g.lerp(g.c3(1, 1, 1), g.vec('StreamTint', (0.7, 0.8, 0.6), 'Meadow'), g.mul(stream, 0.8)))
    base = g.lerp(base, sn, snA)
    # forest canopy beyond the tree cull distance (T_core_Canopy from scatter.py; mid/far MIs use a black texture)
    can = g.tex('RegionCanopy', M + 'T_core_Canopy', uv, 'RGB', CLAMP)
    cfade = g.smooth(dist, g.scalar('CanopyStart', 250000.0, 'Canopy'), g.scalar('CanopyFull', 380000.0, 'Canopy'))
    cov = g.mul(g.sat(g.add(g.mask(can, r=True), g.mul(g.mask(can, g=True), 0.6))), cfade)
    canopy_col = g.mul(g.vec('CanopyColor', (0.03, 0.038, 0.022), 'Canopy'), g.lerp(0.7, 1.2, m2r))
    base = g.lerp(base, canopy_col, cov)
    # ---- baked sunset terrain shadow (beyond the CSM range), plus a slight warm/cool grade
    fade = g.smooth(dist, g.scalar('BakedShadowStart', 20000.0, 'Light'), 45000.0)
    shadowK = g.lerp(g.c1(1.0), g.scalar('ShadowDarken', 0.5, 'Light'), g.mul(g.one_minus(sunv), fade))
    base = g.mul(base, shadowK)
    g.out('MP_BASE_COLOR', g.mul(base, g.scalar('Brightness', 1.0, 'Grade')))
    rough = g.lerp(g.scalar('MeadowRough', 0.92, 'Surface'), g.scalar('RockRough', 0.78, 'Surface'), g.maxx(rA, sA))
    rough = g.lerp(rough, g.scalar('SnowRough', 0.55, 'Surface'), snA)
    rough = g.lerp(rough, 0.35, wet)
    g.out('MP_ROUGHNESS', rough)
    g.out('MP_SPECULAR', g.mul(g.lerp(g.scalar('Specular', 0.15, 'Surface'), 0.4, g.maxx(wet, snA)), shadowK))
    g.out('MP_AMBIENT_OCCLUSION', g.lerp(g.c1(1.0), g.power(ao, 1.5), g.scalar('AOAmount', 1.0, 'Light')))
    # ---- world-space normal: region normal + detail (meadow/scree/rock), detail fades with distance
    dfade = g.one_minus(g.smooth(dist, 3000.0, g.scalar('DetailFadeDist', 60000.0, 'Surface')))
    det = g.lerp(mnrm, snrm, sA)
    det = g.lerp(det, rnrm, rA)
    det = g.lerp(det, g.c3(0, 0, 1), snA)
    dxy = g.mul(g.mask(det, r=True, g=True), g.mul(dfade, g.scalar('DetailNormal', 0.8, 'Surface')))
    g.out('MP_NORMAL', g.normalize(g.add(nw, g.append(dxy, g.c1(0.0)))))
    finish_material(mat)
    return mat


def build_lake():
    mat = get_or_create_material('M_HLLake')
    setup_material(mat)
    g = H(mat)
    t = g.time()
    xy = g.world_pos('XY')
    dist = g.cam_dist()
    base_l = g.scalar('RippleTile', 700.0, 'Surface')
    xyb = g.div(xy, base_l)
    spd = g.scalar('RippleSpeed', 0.25, 'Surface')
    grad = None
    for ang, m, w, off in [(12, 1.0, 0.16, 0.13), (77, 0.71, 0.14, 0.61), (141, 0.53, 0.13, 0.27), (203, 0.39, 0.12, 0.88),
                           (251, 0.29, 0.11, 0.44), (318, 0.21, 0.1, 0.07), (33, 0.155, 0.09, 0.73), (169, 0.11, 0.08, 0.35)]:
        a = math.radians(ang)
        dx, dy = math.cos(a), math.sin(a)
        warp = g.mul(g.sine(g.dot(g.div(xyb, 7.3), g.c2(dy, -dx))), 0.6 + m)
        ph = g.add(g.add(g.dot(xyb, g.c2(dx / m, dy / m)), g.mul(t, g.mul(spd, 1.0 / math.sqrt(m)))), g.add(warp, off + 0.25))
        term = g.mul(g.sine(ph), g.c2(dx * w, dy * w))
        grad = term if grad is None else g.add(grad, term)
    fade = g.one_minus(g.smooth(dist, 2000.0, g.scalar('RippleFadeDist', 150000.0, 'Surface')))
    slope = g.mul(grad, g.mul(g.scalar('RippleStrength', 0.35, 'Surface'), g.add(g.mul(fade, 0.85), 0.15)))
    g.out('MP_NORMAL', g.normalize(g.append(g.mul(slope, -1.0), g.c1(1.0))))
    fr = g.fresnel(5.0, 0.0)
    g.out('MP_BASE_COLOR', g.lerp(g.vec('DeepColor', (0.006, 0.02, 0.024), 'Water'), g.vec('GrazeColor', (0.02, 0.035, 0.04), 'Water'), fr))
    g.out('MP_ROUGHNESS', g.lerp(g.scalar('NearRough', 0.03, 'Water'), g.scalar('FarRough', 0.09, 'Water'), g.one_minus(fade)))
    g.out('MP_SPECULAR', g.scalar('Specular', 0.35, 'Water'))
    finish_material(mat)
    return mat


def build_sky():
    mat = get_or_create_material('M_HLSky')
    setup_material(mat, shading='MSM_UNLIT', two_sided=True, is_sky=True)
    g = H(mat)
    d = g.mul(g.new(unreal.MaterialExpressionCameraVectorWS), -1.0)
    rot = g.new(unreal.MaterialExpressionRotateAboutAxis)
    g.link(g.c3(0.0, 0.0, 1.0), rot, 'NormalizedRotationAxis')
    g.link(g.scalar('Yaw', 0.0, 'Sky'), rot, 'RotationAngle')
    g.link(g.c3(0.0, 0.0, 0.0), rot, 'PivotPoint')
    g.link(d, rot, 'Position')
    dd = g.add(d, rot)
    import json as _j
    cube = _load('/Game/Env/HDRI/' + _j.load(open('/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands/scripts/env_params.json')).get('hdri', 'kloppenheim_06_puresky_4k'))
    n = g.new(unreal.MaterialExpressionTextureSampleParameterCube, parameter_name='SkyCube', texture=cube, group='Sky')
    g.link(dd, n, 'UVs')
    col = g.mul((n, 'RGB'), g.scalar('Exposure', 1.0, 'Sky'))
    below = g.smooth(g.mul(g.mask(d, b=True), -1.0), -0.02, 0.15)
    col = g.lerp(col, g.mul(g.vec('BelowColor', (0.32, 0.36, 0.42), 'Sky'), g.scalar('Exposure', 1.0, 'Sky')), below)
    g.out('MP_EMISSIVE_COLOR', col)
    finish_material(mat)
    return mat


def build_all():
    m = {'terrain': build_terrain(), 'lake': build_lake(), 'sky': build_sky()}
    for r, scal in (('core', {}), ('mid', {'DetailFadeDist': 20000.0, 'BakedShadowStart': 0.0}), ('far', {'DetailFadeDist': 10000.0, 'BakedShadowStart': 0.0})):
        m['mi_' + r] = make_mi('MI_HLTerrain_' + r + MSFX, m['terrain'], scalars=scal,
                               textures={'RegionNormal': _load(M + 'T_%s_N' % r), 'RegionMask': _load(M + 'T_%s_Mask' % r), 'RegionLight': _load(M + 'T_%s_Light' % r),
                                         'RegionCanopy': _load(M + ('T_core_Canopy' if r == 'core' else 'T_Black')) or _load('/Game/Terrain/Maps/T_Black')})
    m['mi_lake'] = make_mi('MI_HLLake', m['lake'])
    m['mi_sky'] = make_mi('MI_HLSky', m['sky'])
    return m
