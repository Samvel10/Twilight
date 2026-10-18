# -*- coding: utf-8 -*-
"""
materials_build.py  -  Twilight / "Vahagn: Vishapakagh"
Headless material builder for Unreal Engine 5.8 (editor Python).

Creates under /Game/Twilight/Materials:
    M_FireBody      lit (or unlit) molten-lava skin for the hero: panning ridged-noise cracks,
                    fresnel rim, pulse, HitFlash.  Opaque.
    M_FireSprite    additive unlit radial sprite for Niagara/Cascade (ParticleColor, DepthFade).
    M_Additive      additive unlit glow for meshes/billboards (radial-UV or view-facing core).
    M_Water_Purple  opaque lit purple sea: 3 sine WPO waves, 8 analytic noise-warped ripple normals,
                    fresnel colour blend, fake sky reflection, sun glint path (no SSR / no translucency).
    M_Rock          world-aligned triplanar rock (3 samples) + macro variation + top tint.
    M_VishapSkin    dark scaly skin (hex-tile normal), glowing pulsing veins, fresnel rim, HitFlash.
    M_Sky           unlit IsSky gradient + sun disc/glow + horizon band (SkyAtmosphere fallback).
    MI_*            material instances with parameters set.

Run (editor must NOT be open on the same project):
    /home/samo/UnrealEngine-5.8/Engine/Binaries/Linux/UnrealEditor-Cmd \
        /var/www/html/Twilight/Game/Twilight.uproject \
        -run=pythonscript -script=/ABS/PATH/materials_build.py \
        -unattended -nop4 -nosplash -nosound -stdout -FullStdOutLogOutput

Requires PythonScriptPlugin (+ EditorScriptingUtilities recommended) enabled in the .uproject.
Re-runnable: existing materials are cleared and rebuilt in place (references from levels/MIs stay valid).
"""

import os
import traceback
import math
import unreal

# ----------------------------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------------------------
ROOT = "/Game/Twilight/Materials"

# Hero: True = MSM_Unlit (cheapest, always glows, no shading); False = DefaultLit + emissive (reads 3D shape).
FIREBODY_UNLIT = False

# Texture candidates, first one that exists on disk wins. StarterContent is already in
# /var/www/html/Twilight/Game/Content/StarterContent (checked 2026-10-18).
TEX_NOISE = [
    "/Game/StarterContent/Textures/T_Perlin_Noise_M",          # TC_Masks
    "/Engine/MaterialTemplates/Textures/T_Noise01",            # TC_Default
    "/Engine/MapTemplates/TilingNoise05",                      # TC_Default
    "/Engine/EngineMaterials/Good64x64TilingNoiseHighFreq",    # TC_Grayscale
]
TEX_WATER_N = [
    "/Game/StarterContent/Textures/T_Water_N",                 # TC_Normalmap
]
TEX_ROCK = [
    "/Game/StarterContent/Textures/T_Rock_Slate_D",
    "/Game/StarterContent/Textures/T_Rock_Basalt_D",
    "/Game/StarterContent/Textures/T_Rock_Sandstone_D",
] + TEX_NOISE                                                  # last resort: tinted noise
TEX_SCALES_N = [
    "/Game/StarterContent/Textures/T_Tech_Hex_Tile_N",         # hex tiles read as scales
    "/Game/StarterContent/Textures/T_CobbleStone_Pebble_N",
]

# ----------------------------------------------------------------------------------------------
# Engine handles
# ----------------------------------------------------------------------------------------------
if not hasattr(unreal, "MaterialEditingLibrary"):
    unreal.load_module("MaterialEditor")          # PyCore.cpp: load_module(module: str)

MEL = unreal.MaterialEditingLibrary
ASSET_TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EAL = getattr(unreal, "EditorAssetLibrary", None)   # needs EditorScriptingUtilities plugin


def _eas():
    try:
        return unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
    except Exception:
        return None


ERRORS = []


def log(msg):
    unreal.log("[TwilightMat] " + str(msg))


def warn(msg):
    unreal.log_warning("[TwilightMat] " + str(msg))


def err(msg):
    ERRORS.append(str(msg))
    unreal.log_error("[TwilightMat] " + str(msg))


def enum_val(enum_name, *members):
    """getattr(unreal.<enum_name>, member) trying several spellings; None if not found."""
    enum_cls = getattr(unreal, enum_name, None)
    if enum_cls is None:
        warn("enum unreal.%s not found" % enum_name)
        return None
    for m in members:
        v = getattr(enum_cls, m, None)
        if v is not None:
            return v
    warn("unreal.%s has none of %s" % (enum_name, members))
    return None


# ----------------------------------------------------------------------------------------------
# Asset helpers (disk-based existence check: does not depend on the asset registry scan state)
# ----------------------------------------------------------------------------------------------
def package_file(path):
    """'/Game/A/B' or '/Engine/A/B' (optionally '.B' object suffix) -> absolute .uasset path or None."""
    pkg = path.split(".")[0]
    if pkg.startswith("/Game/"):
        base = unreal.Paths.project_content_dir()
        rel = pkg[len("/Game/"):]
    elif pkg.startswith("/Engine/"):
        base = unreal.Paths.engine_content_dir()
        rel = pkg[len("/Engine/"):]
    else:
        return None
    full = unreal.Paths.convert_relative_path_to_full(os.path.join(base, rel + ".uasset"))
    return full


def asset_on_disk(path):
    f = package_file(path)
    return bool(f) and os.path.isfile(f)


def load_first(candidates, what):
    for p in candidates:
        if asset_on_disk(p):
            a = unreal.load_asset(p)
            if a:
                log("%s -> %s" % (what, p))
                return a
    warn("%s: none of %s found" % (what, candidates))
    return None


def save(obj):
    if obj is None:
        return False
    ok = False
    try:
        if EAL is not None:
            ok = EAL.save_loaded_asset(obj, False)
        else:
            s = _eas()
            if s is not None:
                ok = s.save_loaded_asset(obj, False)
    except Exception as e:  # noqa
        warn("save_loaded_asset raised %s" % e)
    if not ok:
        err("FAILED to save %s" % obj.get_path_name())
    return ok


def clear_graph(mat):
    # NOTE: MEL.delete_all_material_expressions iterates a live TConstArrayView while removing
    # (MaterialEditingLibrary.cpp:563-565 + :609) -> delete one by one from a Python copy instead.
    for _ in range(4):
        exprs = list(MEL.get_material_expressions(mat))
        if not exprs:
            break
        for e in exprs:
            MEL.delete_material_expression(mat, e)
    # also disconnect root pins (safe if already empty)
    for p in ("MP_BASE_COLOR", "MP_EMISSIVE_COLOR", "MP_NORMAL", "MP_ROUGHNESS", "MP_METALLIC",
              "MP_SPECULAR", "MP_OPACITY", "MP_OPACITY_MASK", "MP_WORLD_POSITION_OFFSET",
              "MP_AMBIENT_OCCLUSION"):
        v = enum_val("MaterialProperty", p)
        if v is not None:
            MEL.disconnect_material_property(mat, v)


def get_or_create_material(name):
    path = "%s/%s" % (ROOT, name)
    mat = None
    if asset_on_disk(path):
        mat = unreal.load_asset(path)
        if mat is not None and not isinstance(mat, unreal.Material):
            raise RuntimeError("%s exists but is %s, not Material" % (path, mat.get_class().get_name()))
    if mat is None:
        mat = ASSET_TOOLS.create_asset(name, ROOT, unreal.Material, unreal.MaterialFactoryNew())
        if mat is None:
            raise RuntimeError("create_asset failed for " + path)
        log("created " + path)
    else:
        log("rebuilding " + path)
        clear_graph(mat)
    return mat


def get_or_create_mi(name, parent):
    path = "%s/%s" % (ROOT, name)
    mi = None
    if asset_on_disk(path):
        mi = unreal.load_asset(path)
    if mi is None:
        # InitialParent is UPROPERTY() without Edit/BlueprintVisible flags -> not settable from Python
        # (PyGenUtil.cpp:1609-1615, 1811-1815). Create parentless, then set the parent via MEL.
        mi = ASSET_TOOLS.create_asset(name, ROOT, unreal.MaterialInstanceConstant,
                                      unreal.MaterialInstanceConstantFactoryNew())
        if mi is None:
            raise RuntimeError("create_asset failed for " + path)
    MEL.set_material_instance_parent(mi, parent)
    MEL.clear_all_material_instance_parameters(mi)
    return mi


# ----------------------------------------------------------------------------------------------
# Graph builder
# ----------------------------------------------------------------------------------------------
_PIN_ALIASES = {
    "Exp": ["Exponent"], "Exponent": ["Exp"],
    "UVs": ["Coordinates"], "Coordinates": ["UVs"],
    "Tex": ["TextureObject"], "TextureObject": ["Tex"],
    "Input": [""],
}


def _src(s):
    """expression or (expression, 'OutputName')"""
    if isinstance(s, tuple):
        return s[0], s[1]
    return s, ""


class G(object):
    def __init__(self, mat):
        self.m = mat

    # --- creation -----------------------------------------------------------------------------
    def new(self, cls, **props):
        e = MEL.create_material_expression(self.m, cls, 0, 0)
        if e is None:
            raise RuntimeError("create_material_expression(%s) returned None" % cls)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def link(self, src, dst, pin):
        e, out = _src(src)
        if MEL.connect_material_expressions(e, out, dst, pin):
            return
        for alt in _PIN_ALIASES.get(pin, []):
            if MEL.connect_material_expressions(e, out, dst, alt):
                return
        ins = list(MEL.get_material_expression_input_names(dst))
        outs = list(MEL.get_material_expression_output_names(e))
        # names printed as "None" mean: pass "" (GetShortenPinName maps "Input" -> NAME_None)
        raise RuntimeError("connect %s.%r -> %s.%r failed; dst inputs=%s src outputs=%s" % (
            e.get_class().get_name(), out, dst.get_class().get_name(), pin, ins, outs))

    def _in(self, node, pin, val, const_prop):
        if isinstance(val, (int, float)):
            node.set_editor_property(const_prop, float(val))
        else:
            self.link(val, node, pin)

    def out(self, prop_name, src):
        prop = enum_val("MaterialProperty", prop_name)
        e, o = _src(src)
        if not MEL.connect_material_property(e, o, prop):
            raise RuntimeError("connect_material_property %s failed" % prop_name)

    # --- parameters / constants ---------------------------------------------------------------
    def scalar(self, name, default, group="Params"):
        return self.new(unreal.MaterialExpressionScalarParameter, parameter_name=name,
                        default_value=float(default), group=group)

    def vec(self, name, rgba, group="Colors"):
        r, g, b = rgba[0], rgba[1], rgba[2]
        a = rgba[3] if len(rgba) > 3 else 1.0
        e = self.new(unreal.MaterialExpressionVectorParameter, parameter_name=name,
                     default_value=unreal.LinearColor(r, g, b, a), group=group)
        return (e, "RGB")

    def c1(self, v):
        return self.new(unreal.MaterialExpressionConstant, r=float(v))

    def c2(self, x, y):
        return self.new(unreal.MaterialExpressionConstant2Vector, r=float(x), g=float(y))

    def c3(self, r, g, b):
        return self.new(unreal.MaterialExpressionConstant3Vector,
                        constant=unreal.LinearColor(float(r), float(g), float(b), 1.0))

    def texcoord(self):
        return self.new(unreal.MaterialExpressionTextureCoordinate)

    def time(self):
        return self.new(unreal.MaterialExpressionTime)

    def world_pos(self, out="XYZ"):
        return (self.new(unreal.MaterialExpressionWorldPosition), out)   # outputs XYZ / XY / Z

    # --- math ---------------------------------------------------------------------------------
    def _bin(self, cls, a, b):
        n = self.new(cls)
        self._in(n, "A", a, "const_a")
        self._in(n, "B", b, "const_b")
        return n

    def mul(self, a, b):
        return self._bin(unreal.MaterialExpressionMultiply, a, b)

    def add(self, a, b):
        return self._bin(unreal.MaterialExpressionAdd, a, b)

    def sub(self, a, b):
        return self._bin(unreal.MaterialExpressionSubtract, a, b)

    def div(self, a, b):
        return self._bin(unreal.MaterialExpressionDivide, a, b)

    def maxx(self, a, b):
        return self._bin(unreal.MaterialExpressionMax, a, b)

    def lerp(self, a, b, alpha):
        n = self.new(unreal.MaterialExpressionLinearInterpolate)
        self._in(n, "A", a, "const_a")
        self._in(n, "B", b, "const_b")
        self._in(n, "Alpha", alpha, "const_alpha")
        return n

    def power(self, base, exp):
        n = self.new(unreal.MaterialExpressionPower)
        self.link(base, n, "Base")
        self._in(n, "Exp", exp, "const_exponent")      # pin "Exponent" is shortened to "Exp"
        return n

    def _unary(self, cls, x, **props):
        n = self.new(cls, **props)
        self.link(x, n, "")                            # "" = first input
        return n

    def sat(self, x):
        return self._unary(unreal.MaterialExpressionSaturate, x)

    def one_minus(self, x):
        return self._unary(unreal.MaterialExpressionOneMinus, x)

    def absx(self, x):
        return self._unary(unreal.MaterialExpressionAbs, x)

    def sine(self, x):          # period 1.0 -> sin(2*pi*x): x is in "cycles"
        return self._unary(unreal.MaterialExpressionSine, x)

    def normalize(self, x):
        return self._unary(unreal.MaterialExpressionNormalize, x)

    def mask(self, x, r=False, g=False, b=False, a=False):
        n = self.new(unreal.MaterialExpressionComponentMask)
        n.set_editor_property("r", r)
        n.set_editor_property("g", g)
        n.set_editor_property("b", b)
        n.set_editor_property("a", a)
        self.link(x, n, "")
        return n

    def append(self, a, b):
        n = self.new(unreal.MaterialExpressionAppendVector)
        self.link(a, n, "A")
        self.link(b, n, "B")
        return n

    def dot(self, a, b):
        n = self.new(unreal.MaterialExpressionDotProduct)
        self.link(a, n, "A")
        self.link(b, n, "B")
        return n

    def panner(self, uv, sx, sy, time=None):
        n = self.new(unreal.MaterialExpressionPanner, speed_x=float(sx), speed_y=float(sy))
        self.link(uv, n, "Coordinate")
        if time is not None:
            self.link(time, n, "Time")
        return n

    def fresnel(self, exponent=None, base_reflect=0.04):
        n = self.new(unreal.MaterialExpressionFresnel, base_reflect_fraction=float(base_reflect))
        if isinstance(exponent, (int, float)):
            n.set_editor_property("exponent", float(exponent))
        elif exponent is not None:
            self.link(exponent, n, "ExponentIn")
        return n

    # --- textures -----------------------------------------------------------------------------
    def tex_param_obj(self, name, texture):
        """TextureObjectParameter (MI-overridable). Setting .texture auto-sets sampler type
        (UMaterialExpressionTextureSample::PostEditChangeProperty -> AutoSetSampleType)."""
        return self.new(unreal.MaterialExpressionTextureObjectParameter, parameter_name=name,
                        texture=texture, group="Textures")

    def sample(self, tex_obj_param, texture, uv, out="RGB"):
        """TextureSample fed by a TextureObject(Parameter). Its own .texture is set to the same
        texture so that its SamplerType matches (sampler/compression mismatch = compile error)."""
        n = self.new(unreal.MaterialExpressionTextureSample, texture=texture)
        self.link(tex_obj_param, n, "Tex")
        if uv is not None:
            self.link(uv, n, "UVs")
        return (n, out)

    def tex_param(self, name, texture, uv, out="RGB"):
        n = self.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name=name,
                     texture=texture, group="Textures")
        if uv is not None:
            self.link(uv, n, "UVs")
        return (n, out)


def setup_material(mat, shading="MSM_DEFAULT_LIT", blend="BLEND_OPAQUE", two_sided=False,
                   is_sky=False, usages=()):
    mat.set_editor_property("shading_model", enum_val("MaterialShadingModel", shading))
    mat.set_editor_property("blend_mode", enum_val("BlendMode", blend))
    mat.set_editor_property("two_sided", bool(two_sided))
    mat.set_editor_property("is_sky", bool(is_sky))
    # Explicit usage flags (do NOT rely on bAutomaticallySetUsageInEditor: in a cooked/-game run a
    # missing flag silently renders the default material on skeletal/niagara/spline meshes).
    for u in usages:
        v = enum_val("MaterialUsage", u)
        if v is not None:
            MEL.set_base_material_usage(mat, v, True)    # MaterialEditingLibrary.h:205


def finish_material(mat):
    MEL.layout_material_expressions(mat)
    errs = MEL.recompile_material(mat)                    # MaterialEditingLibrary.h:267
    if errs:
        # NOTE: compile is asynchronous; an empty list here does NOT prove the shader compiles.
        for e in errs:
            err("%s compile: %s" % (mat.get_name(), e))
    save(mat)
    log("built %s (%d expressions)" % (mat.get_name(), MEL.get_num_material_expressions(mat)))


# ----------------------------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------------------------
def build_fire_body(noise_tex):
    mat = get_or_create_material("M_FireBody")
    setup_material(mat, shading="MSM_UNLIT" if FIREBODY_UNLIT else "MSM_DEFAULT_LIT",
                   usages=("MATUSAGE_SKELETAL_MESH", "MATUSAGE_NIAGARA_MESH_PARTICLES",
                           "MATUSAGE_SPLINE_MESH", "MATUSAGE_INSTANCED_STATIC_MESHES"))
    g = G(mat)
    t = g.time()
    uv = g.texcoord()
    tiling = g.scalar("NoiseTiling", 2.0, "Cracks")
    flow = g.scalar("FlowSpeed", 1.0, "Cracks")
    tflow = g.mul(t, flow)
    noise = g.tex_param_obj("NoiseTex", noise_tex)
    uv1 = g.mul(uv, tiling)
    uv2 = g.mul(uv, g.mul(tiling, 2.3))
    n1 = g.sample(noise, noise_tex, g.panner(uv1, 0.03, 0.06, tflow), "R")
    n2 = g.sample(noise, noise_tex, g.panner(uv2, -0.05, 0.035, tflow), "R")
    n = g.mul(g.add(n1, n2), 0.5)
    ridge = g.one_minus(g.absx(g.sub(g.mul(n, 2.0), 1.0)))         # 1 at noise mid-level -> vein lines
    cracks = g.power(ridge, g.scalar("CrackSharpness", 40.0, "Cracks"))
    cracks_i = g.sat(g.mul(cracks, g.scalar("CrackAmount", 1.3, "Cracks")))

    deep = g.vec("CrackColorDeep", (1.0, 0.18, 0.02))
    hot = g.vec("CrackColorHot", (1.0, 0.75, 0.25))
    heat_col = g.lerp(deep, hot, cracks_i)
    pulse = g.add(g.mul(g.sine(g.mul(t, g.scalar("PulseSpeed", 0.7, "Cracks"))),
                        g.scalar("PulseAmount", 0.15, "Cracks")), 1.0)
    e_cracks = g.mul(g.mul(heat_col, cracks_i),
                     g.mul(g.scalar("EmissiveIntensity", 8.0, "Emissive"), pulse))

    fr = g.fresnel(g.scalar("RimExponent", 2.5, "Rim"))
    rim = g.mul(g.mul(g.vec("RimColor", (1.0, 0.45, 0.08)), fr), g.scalar("RimIntensity", 4.0, "Rim"))
    flash = g.mul(g.vec("FlashColor", (1.0, 0.9, 0.7)), g.scalar("HitFlash", 0.0, "Emissive"))
    skin = g.vec("SkinColor", (0.035, 0.012, 0.008))
    base = g.mul(skin, g.one_minus(cracks_i))
    emissive = g.add(g.add(e_cracks, rim), flash)
    if FIREBODY_UNLIT:
        emissive = g.add(emissive, g.mul(base, g.scalar("AmbientFill", 2.0, "Emissive")))
    else:
        g.out("MP_BASE_COLOR", base)
        g.out("MP_ROUGHNESS", g.scalar("Roughness", 0.55, "Surface"))
    g.out("MP_EMISSIVE_COLOR", emissive)
    finish_material(mat)
    return mat


def build_fire_sprite():
    mat = get_or_create_material("M_FireSprite")
    setup_material(mat, shading="MSM_UNLIT", blend="BLEND_ADDITIVE", two_sided=True,
                   usages=("MATUSAGE_NIAGARA_SPRITES", "MATUSAGE_NIAGARA_RIBBONS",
                           "MATUSAGE_NIAGARA_MESH_PARTICLES", "MATUSAGE_PARTICLE_SPRITES",
                           "MATUSAGE_MESH_PARTICLES"))
    g = G(mat)
    sm = g.new(unreal.MaterialExpressionSphereMask, attenuation_radius=0.5, hardness_percent=0.0)
    g.link(g.texcoord(), sm, "A")
    g.link(g.c2(0.5, 0.5), sm, "B")
    soft = g.power(sm, g.scalar("Falloff", 1.5))
    core = g.power(sm, g.scalar("CoreSharpness", 6.0))
    col = g.add(g.mul(g.vec("Color", (1.0, 0.35, 0.05)), g.mul(soft, g.scalar("Intensity", 4.0))),
                g.mul(g.vec("CoreColor", (1.0, 0.85, 0.5)), g.mul(core, g.scalar("CoreIntensity", 6.0))))
    pc = g.new(unreal.MaterialExpressionParticleColor)
    tinted = g.mul(col, (pc, "RGB"))
    df = g.new(unreal.MaterialExpressionDepthFade)
    g.link((pc, "A"), df, "")                                  # first input = InOpacity
    g.link(g.scalar("FadeDistance", 60.0), df, "FadeDistance")
    g.out("MP_EMISSIVE_COLOR", g.mul(tinted, df))
    finish_material(mat)
    return mat


def build_additive():
    mat = get_or_create_material("M_Additive")
    setup_material(mat, shading="MSM_UNLIT", blend="BLEND_ADDITIVE", two_sided=False,
                   usages=("MATUSAGE_NIAGARA_SPRITES", "MATUSAGE_NIAGARA_MESH_PARTICLES",
                           "MATUSAGE_NIAGARA_RIBBONS", "MATUSAGE_PARTICLE_SPRITES",
                           "MATUSAGE_MESH_PARTICLES", "MATUSAGE_SKELETAL_MESH",
                           "MATUSAGE_INSTANCED_STATIC_MESHES"))
    g = G(mat)
    falloff = g.scalar("Falloff", 2.0)
    sm = g.new(unreal.MaterialExpressionSphereMask, attenuation_radius=0.5, hardness_percent=0.0)
    g.link(g.texcoord(), sm, "A")
    g.link(g.c2(0.5, 0.5), sm, "B")
    radial = g.power(sm, falloff)
    facing = g.power(g.one_minus(g.fresnel(1.0, 0.0)), falloff)  # 1 where surface faces camera
    m = g.lerp(radial, facing, g.scalar("GlowMode", 0.0))         # 0 = UV radial (cards), 1 = mesh core
    col = g.mul(g.vec("Color", (1.0, 0.45, 0.1)), g.mul(m, g.scalar("Intensity", 5.0)))
    df = g.new(unreal.MaterialExpressionDepthFade)
    g.link(g.c1(1.0), df, "")
    g.link(g.scalar("FadeDistance", 40.0), df, "FadeDistance")
    g.out("MP_EMISSIVE_COLOR", g.mul(col, df))
    finish_material(mat)
    return mat


def build_water(water_n, noise_tex=None):
    mat = get_or_create_material("M_Water_Purple")
    setup_material(mat, usages=("MATUSAGE_INSTANCED_STATIC_MESHES",))
    g = G(mat)
    t = g.time()
    xy = g.world_pos("XY")

    # --- World Position Offset: 3 directional sine waves (cycles = dot(xy,dir)/wavelength + t*speed)
    wl = g.scalar("WaveLength", 2400.0, "Waves")
    amp = g.scalar("WaveHeight", 40.0, "Waves")
    spd = g.scalar("WaveSpeed", 0.12, "Waves")
    waves = [((0.94, 0.33), 1.0, 1.0), ((-0.37, 0.93), 0.62, 1.3), ((0.70, -0.71), 0.38, 1.7)]
    hsum = None
    for (dx, dy), weight, k in waves:
        phase = g.add(g.div(g.dot(xy, g.c2(dx * k, dy * k)), wl), g.mul(t, g.mul(spd, k ** 0.5)))
        s = g.sine(phase)
        s = s if weight == 1.0 else g.mul(s, weight)
        hsum = s if hsum is None else g.add(hsum, s)
    g.out("MP_WORLD_POSITION_OFFSET", g.append(g.c2(0.0, 0.0), g.mul(hsum, amp)))

    # --- Normal: 8 analytic directional ripples (exact cosine slopes), phases domain-warped by
    # low-frequency Perlin noise so no texture cell / tile pattern can repeat. The engine
    # T_Water_N cells read as a polka-dot grid (and as dotted sun glints) when seen from altitude.
    base_l = g.scalar("NormalTile", 900.0, "Surface")          # longest ripple wavelength (cm)
    xyb = g.div(xy, base_l)
    rspd = g.scalar("RippleSpeed", 0.16, "Surface")
    warp = None
    if noise_tex is not None:
        wobj = g.tex_param_obj("WarpNoise", noise_tex)
        warp = g.sample(wobj, noise_tex, g.panner(g.mul(xyb, 0.37), 0.004, -0.003), out="R")
        warp = g.mul(warp, g.scalar("WarpAmount", 1.6, "Surface"))
    ripples = [  # (angle deg, wavelength factor, slope weight, phase offset, warp gain)
        (12, 1.00, 0.22, 0.13, 0.6), (77, 0.71, 0.18, 0.61, 0.9), (141, 0.53, 0.15, 0.27, 1.2),
        (203, 0.39, 0.13, 0.88, 1.5), (251, 0.29, 0.11, 0.44, 1.8), (318, 0.21, 0.09, 0.07, 2.1),
        (33, 0.155, 0.07, 0.73, 2.4), (169, 0.11, 0.05, 0.35, 2.7)]
    grad = None
    for ang, m, w, off, wk in ripples:
        a = math.radians(ang)
        dx, dy = math.cos(a), math.sin(a)
        ph = g.dot(xyb, g.c2(dx / m, dy / m))
        ph = g.add(ph, g.add(g.mul(t, g.mul(rspd, 1.0 / math.sqrt(m))), off + 0.25))  # +0.25 -> cosine
        if warp is not None:
            ph = g.add(ph, g.mul(warp, wk))
        term = g.mul(g.sine(ph), g.c2(dx * w, dy * w))
        grad = term if grad is None else g.add(grad, term)
    dist = g.new(unreal.MaterialExpressionDistance)
    g.link(g.new(unreal.MaterialExpressionCameraPositionWS), dist, "A")
    g.link(g.world_pos("XYZ"), dist, "B")
    fade = g.lerp(g.c1(1.0), g.c1(0.3), g.sat(g.div(dist, g.scalar("NormalFadeDistance", 60000.0, "Surface"))))
    slope = g.mul(grad, g.mul(g.scalar("NormalStrength", 0.6, "Surface"), g.mul(fade, -1.0)))
    g.out("MP_NORMAL", g.normalize(g.append(slope, g.c1(1.0))))

    # --- Colour: fresnel blend deep->horizon, crest tint
    fr = g.fresnel(g.scalar("FresnelExponent", 4.0, "Surface"), 0.02)
    crest = g.mul(g.power(g.sat(g.mul(hsum, 0.5)), 2.0), g.scalar("CrestAmount", 0.35, "Waves"))
    base = g.add(g.lerp(g.vec("DeepColor", (0.035, 0.006, 0.09)), g.vec("HorizonColor", (0.42, 0.16, 0.55)), fr),
                 g.mul(g.vec("CrestColor", (0.75, 0.45, 0.85)), crest))
    g.out("MP_BASE_COLOR", base)
    g.out("MP_ROUGHNESS", g.scalar("Roughness", 0.08, "Surface"))
    g.out("MP_SPECULAR", g.scalar("Specular", 0.6, "Surface"))

    # --- Emissive: fake sky reflection + sun glint path (works without SSR/Lumen)
    refl = g.mul(g.mul(g.vec("SkyReflectColor", (0.9, 0.38, 0.55)), fr),
                 g.scalar("ReflectIntensity", 0.6, "Sun"))
    rv = g.new(unreal.MaterialExpressionReflectionVectorWS)
    sundir = g.normalize(g.vec("SunDir", (-0.8, 0.0, 0.18), "Sun"))   # direction TOWARDS the sun
    glint = g.power(g.sat(g.dot(rv, sundir)), g.scalar("SunGlintSharpness", 300.0, "Sun"))
    glint_c = g.mul(g.mul(g.vec("SunColor", (1.0, 0.55, 0.25), "Sun"), glint),
                    g.scalar("SunGlintIntensity", 25.0, "Sun"))
    g.out("MP_EMISSIVE_COLOR", g.add(refl, glint_c))
    finish_material(mat)
    return mat


def build_rock(rock_tex, noise_tex):
    mat = get_or_create_material("M_Rock")
    setup_material(mat, usages=("MATUSAGE_INSTANCED_STATIC_MESHES",))
    g = G(mat)
    wp = g.world_pos("XYZ")
    p = g.div(wp, g.scalar("TexScale", 400.0, "Triplanar"))
    robj = g.tex_param_obj("RockTex", rock_tex)
    t_xy = g.sample(robj, rock_tex, g.mask(p, r=True, g=True))
    t_yz = g.sample(robj, rock_tex, g.mask(p, g=True, b=True))
    t_xz = g.sample(robj, rock_tex, g.mask(p, r=True, b=True))
    n = g.new(unreal.MaterialExpressionVertexNormalWS)
    w = g.power(g.absx(n), g.scalar("BlendSharpness", 4.0, "Triplanar"))
    wn = g.div(w, g.dot(w, g.c3(1.0, 1.0, 1.0)))
    tri = g.add(g.add(g.mul(t_xy, g.mask(wn, b=True)), g.mul(t_yz, g.mask(wn, r=True))),
                g.mul(t_xz, g.mask(wn, g=True)))
    mv = None
    if noise_tex is not None:
        nobj = g.tex_param_obj("MacroNoise", noise_tex)
        macro_uv = g.div(g.mask(wp, r=True, g=True), g.scalar("MacroScale", 6000.0, "Triplanar"))
        mv = g.lerp(0.65, 1.25, g.sample(nobj, noise_tex, macro_uv, "R"))
    col = g.mul(tri, g.vec("Tint", (0.42, 0.34, 0.40)))
    if mv is not None:
        col = g.mul(col, mv)
    top = g.mul(g.power(g.sat(g.mask(n, b=True)), g.scalar("TopSharpness", 3.0, "Top")),
                g.scalar("TopAmount", 0.55, "Top"))
    g.out("MP_BASE_COLOR", g.lerp(col, g.vec("TopColor", (0.38, 0.22, 0.42)), top))
    g.out("MP_ROUGHNESS", g.scalar("Roughness", 0.85, "Surface"))
    g.out("MP_SPECULAR", g.scalar("Specular", 0.3, "Surface"))
    finish_material(mat)
    return mat


def build_vishap(noise_tex, scales_n):
    mat = get_or_create_material("M_VishapSkin")
    setup_material(mat, usages=("MATUSAGE_SKELETAL_MESH", "MATUSAGE_SPLINE_MESH",
                                "MATUSAGE_INSTANCED_STATIC_MESHES", "MATUSAGE_NIAGARA_MESH_PARTICLES"))
    g = G(mat)
    t = g.time()
    uv = g.texcoord()
    if scales_n is not None:
        sn = g.tex_param("ScaleNormal", scales_n, g.mul(uv, g.scalar("ScaleTiling", 8.0, "Scales")))
        g.out("MP_NORMAL", g.lerp(g.c3(0.0, 0.0, 1.0), sn, g.scalar("ScaleNormalStrength", 0.8, "Scales")))
    nobj = g.tex_param_obj("NoiseTex", noise_tex)
    nuv = g.mul(uv, g.scalar("VeinTiling", 5.0, "Veins"))
    tflow = g.mul(t, g.scalar("VeinFlow", 1.0, "Veins"))
    n1 = g.sample(nobj, noise_tex, g.panner(nuv, 0.01, 0.02, tflow), "R")
    n2 = g.sample(nobj, noise_tex, g.panner(g.mul(nuv, 2.1), -0.015, 0.01, tflow), "R")
    n = g.mul(g.add(n1, n2), 0.5)
    ridge = g.one_minus(g.absx(g.sub(g.mul(n, 2.0), 1.0)))
    veins = g.power(ridge, g.scalar("VeinSharpness", 70.0, "Veins"))
    pulse = g.add(g.mul(g.sine(g.mul(t, g.scalar("PulseSpeed", 0.8, "Veins"))), 0.35), 1.0)
    vein_e = g.mul(g.mul(g.vec("VeinColor", (0.25, 1.0, 0.35)), veins),
                   g.mul(g.scalar("VeinIntensity", 6.0, "Veins"), pulse))
    rim = g.mul(g.mul(g.vec("RimColor", (0.35, 0.9, 0.5)), g.fresnel(g.scalar("RimExponent", 3.0, "Rim"))),
                g.scalar("RimIntensity", 2.0, "Rim"))
    flash = g.mul(g.vec("FlashColor", (1.0, 0.6, 0.25)), g.scalar("HitFlash", 0.0, "Veins"))
    g.out("MP_EMISSIVE_COLOR", g.add(g.add(vein_e, rim), flash))
    base = g.lerp(g.vec("SkinColor", (0.02, 0.03, 0.025)), g.vec("SkinColor2", (0.06, 0.05, 0.04)), n)
    g.out("MP_BASE_COLOR", g.mul(base, g.one_minus(veins)))
    g.out("MP_ROUGHNESS", g.scalar("Roughness", 0.4, "Surface"))
    g.out("MP_METALLIC", g.scalar("Metallic", 0.15, "Surface"))
    finish_material(mat)
    return mat


def build_sky():
    mat = get_or_create_material("M_Sky")
    setup_material(mat, shading="MSM_UNLIT", two_sided=True, is_sky=True)
    g = G(mat)
    cam = g.new(unreal.MaterialExpressionCameraVectorWS)   # pixel -> camera, normalized
    d = g.mul(cam, -1.0)                                      # camera -> pixel = view direction
    z = g.mask(d, b=True)
    t = g.power(g.sat(z), g.scalar("GradientExponent", 0.45, "Gradient"))
    sky = g.lerp(g.vec("HorizonColor", (1.0, 0.36, 0.22)), g.vec("ZenithColor", (0.05, 0.025, 0.18)), t)
    down = g.sat(g.mul(z, -6.0))
    sky = g.lerp(sky, g.vec("BelowColor", (0.12, 0.04, 0.18)), down)
    sd = g.normalize(g.vec("SunDir", (-0.8, 0.0, 0.18), "Sun"))
    s = g.sat(g.dot(d, sd))
    disc = g.mul(g.power(s, g.scalar("SunDiscExponent", 1500.0, "Sun")), g.scalar("SunDiscIntensity", 40.0, "Sun"))
    glow = g.mul(g.power(s, g.scalar("SunGlowExponent", 6.0, "Sun")), g.scalar("SunGlowIntensity", 1.5, "Sun"))
    band = g.mul(g.power(g.one_minus(g.absx(z)), g.scalar("HorizonBandExponent", 10.0, "Gradient")),
                 g.scalar("HorizonBandIntensity", 0.6, "Gradient"))
    sun = g.mul(g.vec("SunColor", (1.0, 0.55, 0.28), "Sun"), g.add(g.add(disc, glow), band))
    g.out("MP_EMISSIVE_COLOR", g.add(g.mul(sky, g.scalar("SkyIntensity", 1.0, "Gradient")), sun))
    finish_material(mat)
    return mat


# ----------------------------------------------------------------------------------------------
# Material instances
# ----------------------------------------------------------------------------------------------
def make_mi(name, parent, scalars=None, vectors=None, textures=None):
    if parent is None:
        warn("skip %s: parent missing" % name)
        return None
    mi = get_or_create_mi(name, parent)
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
        # Setter always returns False (MaterialEditingLibrary.cpp:1487-1493) -> verify by reading back.
        got = MEL.get_material_instance_scalar_parameter_value(mi, k)
        if abs(got - float(v)) > 1e-4:
            warn("%s: scalar %s reads back %s (wanted %s) - parameter missing in parent?" % (name, k, got, v))
    for k, c in (vectors or {}).items():
        a = c[3] if len(c) > 3 else 1.0
        MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(c[0], c[1], c[2], a))
    for k, tex in (textures or {}).items():
        if tex is not None:
            MEL.set_material_instance_texture_parameter_value(mi, k, tex)
    MEL.update_material_instance(mi)
    save(mi)
    log("built %s -> %s" % (name, parent.get_name()))
    return mi


def build_instances(m):
    make_mi("MI_FireBody_Vahagn", m.get("M_FireBody"),
            scalars={"EmissiveIntensity": 9.0, "CrackAmount": 1.8, "RimIntensity": 5.0, "NoiseTiling": 2.5})
    make_mi("MI_FireBody_Ember", m.get("M_FireBody"),
            scalars={"EmissiveIntensity": 3.0, "CrackAmount": 1.2, "RimIntensity": 1.5},
            vectors={"CrackColorDeep": (0.8, 0.08, 0.01), "CrackColorHot": (1.0, 0.4, 0.05)})
    make_mi("MI_FireSprite_Flame", m.get("M_FireSprite"),
            scalars={"Intensity": 4.0, "CoreIntensity": 4.0, "Falloff": 1.6})
    make_mi("MI_FireSprite_Core", m.get("M_FireSprite"),
            scalars={"Intensity": 6.0, "CoreIntensity": 10.0, "Falloff": 2.5},
            vectors={"Color": (1.0, 0.7, 0.3), "CoreColor": (1.0, 0.95, 0.85)})
    make_mi("MI_FireSprite_VishapGreen", m.get("M_FireSprite"),
            scalars={"Intensity": 4.0, "CoreIntensity": 5.0},
            vectors={"Color": (0.15, 1.0, 0.3), "CoreColor": (0.7, 1.0, 0.6)})
    make_mi("MI_Additive_Glow", m.get("M_Additive"), scalars={"Intensity": 5.0, "GlowMode": 0.0})
    make_mi("MI_Additive_FireballCore", m.get("M_Additive"),
            scalars={"Intensity": 12.0, "GlowMode": 1.0, "Falloff": 1.5},
            vectors={"Color": (1.0, 0.55, 0.15)})
    make_mi("MI_Water_Purple", m.get("M_Water_Purple"),
            scalars={"WaveHeight": 45.0, "WaveLength": 2600.0, "NormalStrength": 0.65})
    make_mi("MI_Rock_Mountain", m.get("M_Rock"),
            scalars={"TexScale": 900.0, "TopAmount": 0.6},
            vectors={"Tint": (0.36, 0.28, 0.36), "TopColor": (0.40, 0.24, 0.45)})
    make_mi("MI_Rock_Basalt", m.get("M_Rock"),
            scalars={"TexScale": 300.0, "TopAmount": 0.25},
            vectors={"Tint": (0.30, 0.27, 0.27)})
    make_mi("MI_VishapSkin_Serpent", m.get("M_VishapSkin"), scalars={"VeinIntensity": 6.0})
    make_mi("MI_VishapSkin_Boss", m.get("M_VishapSkin"),
            scalars={"VeinIntensity": 10.0, "VeinTiling": 2.0, "RimIntensity": 3.5, "ScaleTiling": 5.0},
            vectors={"VeinColor": (1.0, 0.18, 0.05), "RimColor": (1.0, 0.3, 0.1),
                     "SkinColor": (0.03, 0.01, 0.01), "SkinColor2": (0.08, 0.03, 0.02)})
    make_mi("MI_Sky_Sunset", m.get("M_Sky"), scalars={"SkyIntensity": 1.0})


# ----------------------------------------------------------------------------------------------
def main():
    log("=== materials_build.py start (ROOT=%s) ===" % ROOT)
    noise = load_first(TEX_NOISE, "noise")
    water_n = load_first(TEX_WATER_N, "water normal")
    rock = load_first(TEX_ROCK, "rock")
    scales_n = load_first(TEX_SCALES_N, "scales normal")
    if noise is None:
        err("no noise texture found at all - fire/vishap/rock materials cannot be built")

    built = {}
    steps = [
        ("M_FireBody", lambda: build_fire_body(noise)),
        ("M_FireSprite", build_fire_sprite),
        ("M_Additive", build_additive),
        ("M_Water_Purple", lambda: build_water(water_n, noise)),
        ("M_Rock", lambda: build_rock(rock, noise)),
        ("M_VishapSkin", lambda: build_vishap(noise, scales_n)),
        ("M_Sky", build_sky),
    ]
    for name, fn in steps:
        try:
            built[name] = fn()
        except Exception:
            err("building %s failed:\n%s" % (name, traceback.format_exc()))

    try:
        build_instances(built)
    except Exception:
        err("building instances failed:\n%s" % traceback.format_exc())

    # final safety net: save anything still dirty
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(False, True)
    except Exception as e:  # noqa
        warn("save_dirty_packages: %s" % e)

    log("=== done: %d materials, %d errors ===" % (len(built), len(ERRORS)))
    if ERRORS:
        # raising makes the commandlet return non-zero ("Python script executed with errors")
        raise RuntimeError("materials_build.py finished with %d error(s):\n%s" % (len(ERRORS), "\n".join(ERRORS)))


main()
