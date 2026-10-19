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

    # --- Normal: 8 analytic directional ripples (exact cosine slopes) with a smooth analytic
    # domain warp, no textures at all. The engine T_Water_N cells read as a polka-dot grid
    # (and as dotted sun glints) when seen from altitude.
    base_l = g.scalar("NormalTile", 900.0, "Surface")          # longest ripple wavelength (cm)
    xyb = g.div(xy, base_l)
    rspd = g.scalar("RippleSpeed", 0.16, "Surface")
    # smooth analytic domain warp (three long, non-commensurate sines). The StarterContent Perlin
    # texture is blobby: its spots shifted the ripple phase into a visible dot lattice from altitude.
    wa = g.scalar("WarpAmount", 1.0, "Surface")
    warp = None
    for (wx, wy), ph0, amp_w, spd_w in [((0.31, 0.17), 0.0, 0.5, 0.010), ((-0.13, 0.29), 1.3, 0.5, -0.008),
                                        ((0.39, -0.46), 2.1, 0.35, 0.013)]:
        sw = g.mul(g.sine(g.add(g.dot(xyb, g.c2(wx, wy)), g.add(g.mul(t, spd_w), ph0))), amp_w)
        warp = sw if warp is None else g.add(warp, sw)
    warp = g.mul(warp, wa)
    # long ripples get the strongest warp and no single pair dominates: two strong crossing
    # sines read as a regular dot lattice from altitude
    ripples = [  # (angle deg, wavelength factor, slope weight, phase offset, warp gain)
        (12, 1.00, 0.15, 0.13, 2.6), (77, 0.71, 0.14, 0.61, 2.3), (141, 0.53, 0.14, 0.27, 2.0),
        (203, 0.39, 0.13, 0.88, 1.7), (251, 0.29, 0.12, 0.44, 1.4), (318, 0.21, 0.12, 0.07, 1.1),
        (33, 0.155, 0.10, 0.73, 0.9), (169, 0.11, 0.10, 0.35, 0.7)]
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
    fade = g.lerp(g.c1(1.0), g.c1(0.0), g.sat(g.div(dist, g.scalar("NormalFadeDistance", 2500.0, "Surface"))))
    slope = g.mul(grad, g.mul(g.scalar("NormalStrength", 0.6, "Surface"), g.mul(fade, -1.0)))
    nrm_analytic = g.normalize(g.append(slope, g.c1(1.0)))
    ocean = None
    try:
        ocean = unreal.load_asset("/Game/Twilight/Env/Textures/T_OceanWaves_N_1k")
    except Exception:
        ocean = None
    if ocean is not None:
        # Phillips-spectrum wave normals (generated, tileable) at two scales and directions: carry the far field
        # where the analytic ripples fade (they read as a dot lattice from altitude)
        oobj = g.tex_param_obj("OceanNormal", ocean)
        ouv = g.div(xy, g.scalar("OceanTile", 4200.0, "Surface"))
        o1 = g.sample(oobj, ocean, g.panner(ouv, 0.006, 0.004))
        o2 = g.sample(oobj, ocean, g.panner(g.mul(ouv, 2.7), -0.005, 0.007))
        o = g.add(o1, o2)
        ok = g.scalar("OceanStrength", 0.6, "Surface")
        o_flat = g.lerp(g.c3(0.0, 0.0, 1.0), o, ok)
        g.out("MP_NORMAL", g.normalize(g.add(nrm_analytic, g.mul(o_flat, g.c1(1.0)))))
    else:
        g.out("MP_NORMAL", nrm_analytic)

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



def _load(path):
    try:
        return unreal.load_asset(path)
    except Exception:
        return None


def build_dragon():
    """CC-BY 'European Dragon' (Regina Cachoa) - REALISTIC skin: own albedo (lifted to a plausible
    reptile albedo), wet sheen on scale tops, TwoSidedFoliage transmission through the wing
    membranes (low sun behind the wing = glowing red membrane), no fake rim / lava by default."""
    D = "/Game/Twilight/Vishap/Dragon/european_dragon_texture_"
    albedo, rough, normal = _load(D + "0"), _load(D + "1"), _load(D + "2")
    wingtex = _load("/Game/Twilight/Vishap/Dragon/T_DragonWingMask")
    if albedo is None or normal is None:
        warn("dragon textures missing - M_Dragon skipped")
        return None
    mat = get_or_create_material("M_Dragon")
    setup_material(mat, shading="MSM_TWO_SIDED_FOLIAGE", two_sided=True, usages=("MATUSAGE_SKELETAL_MESH",))
    g = G(mat)
    t = g.time()
    uv = g.texcoord()
    a = g.tex_param("BaseTex", albedo, uv)                                   # sRGB albedo
    lum = g.dot(a, g.c3(0.3, 0.59, 0.11))
    w = g.tex_param("WingMask", wingtex, uv, "R") if wingtex is not None else g.c1(0.0)
    # base colour: desaturate 30 %, tint body / membrane separately, lift x2.4 (texture is ~sRGB 0.09 avg = near black)
    desat = g.lerp(a, lum, g.scalar("Desaturate", 0.3, "Surface"))
    tint = g.lerp(g.vec("Tint", (1.0, 0.95, 0.92)), g.vec("WingTint", (0.55, 0.36, 0.30)), w)
    g.out("MP_BASE_COLOR", g.mul(g.mul(desat, tint), g.scalar("Brightness", 2.4, "Surface")))
    # normal x1.2
    n = g.tex_param("NormalTex", normal, uv)
    g.out("MP_NORMAL", g.lerp(g.c3(0.0, 0.0, 1.0), n, g.scalar("NormalStrength", 1.2, "Surface")))
    # roughness: MR.G * 0.75 (~0.70), 'wet' 0.32 on flat scale tops (normal.z^6), membrane 0.55
    r0 = g.mul(g.tex_param("RoughTex", rough, uv, "G"), g.scalar("RoughnessScale", 0.75, "Surface")) if rough is not None \
        else g.scalar("Roughness", 0.7, "Surface")
    tops = g.sat(g.mul(g.power(g.sat(g.mask(n, b=True)), g.scalar("WetTightness", 6.0, "Surface")), g.scalar("Wetness", 1.0, "Surface")))
    r1 = g.lerp(r0, g.scalar("WetRough", 0.32, "Surface"), tops)
    g.out("MP_ROUGHNESS", g.sat(g.lerp(r1, g.scalar("MembraneRough", 0.55, "Surface"), w)))
    g.out("MP_SPECULAR", g.scalar("Specular", 0.5, "Surface"))
    g.out("MP_METALLIC", g.scalar("Metallic", 0.0, "Surface"))
    # wing membrane transmission (TwoSidedFoliage 'Subsurface Color'); dark struts/veins transmit less
    thin = g.sat(g.power(g.sat(g.mul(lum, 4.0)), 1.5))
    sss = g.mul(g.mul(g.mul(g.vec("MembraneColor", (1.0, 0.22, 0.06)), g.scalar("Transmission", 0.8, "Wings")), w), thin)
    g.out("MP_SUBSURFACE_COLOR", sss)
    # gameplay emissive kept (HitFlash / Burn); veins + rim kept as params but OFF by default
    crev = g.sat(g.mul(g.sat(g.sub(g.scalar("VeinThreshold", 0.0045, "Veins"), lum)), g.scalar("VeinGain", 260.0, "Veins")))
    pulse = g.add(g.mul(g.sine(g.add(g.mul(t, g.scalar("PulseSpeed", 0.6, "Veins")), g.mul(g.mask(uv, r=True), 3.0))), 0.3), 1.0)
    vein_e = g.mul(g.mul(g.vec("VeinColor", (1.0, 0.25, 0.04)), crev), g.mul(g.scalar("VeinIntensity", 0.0, "Veins"), pulse))
    rim = g.mul(g.mul(g.vec("RimColor", (1.0, 0.55, 0.3)), g.fresnel(g.scalar("RimExponent", 5.0, "Rim"))), g.scalar("RimIntensity", 0.0, "Rim"))
    flash = g.mul(g.vec("FlashColor", (1.0, 0.25, 0.05)), g.scalar("HitFlash", 0.0, "Veins"))
    burn = g.mul(g.vec("BurnColor", (1.0, 0.35, 0.05)), g.scalar("Burn", 0.0, "Veins"))
    g.out("MP_EMISSIVE_COLOR", g.add(g.add(vein_e, rim), g.add(g.mul(flash, g.add(crev, 0.15)), g.mul(burn, g.add(crev, 0.04)))))
    finish_material(mat)
    return mat


def build_dragon_teeth():
    tex = _load("/Game/Twilight/Vishap/Dragon/european_dragon_texture_3")
    if tex is None:
        return None
    mat = get_or_create_material("M_DragonTeeth")
    setup_material(mat, two_sided=True, usages=("MATUSAGE_SKELETAL_MESH",))
    g = G(mat)
    a = g.tex_param("BaseTex", tex, g.texcoord())
    g.out("MP_BASE_COLOR", g.mul(a, g.vec("Tint", (0.80, 0.74, 0.66))))
    g.out("MP_ROUGHNESS", g.scalar("Roughness", 0.4, "Surface"))
    finish_material(mat)
    return mat


def build_sky_hdri():
    """Visible sky dome from a lat-long HDRI (TextureCube): tint + exposure + yaw."""
    cube = _load("/Game/Twilight/Env/HDRI/belfast_sunset_puresky_2k")
    if cube is None:
        warn("HDRI missing - M_SkyHDRI skipped")
        return None
    mat = get_or_create_material("M_SkyHDRI")
    setup_material(mat, shading="MSM_UNLIT", two_sided=True, is_sky=True)
    g = G(mat)
    cam = g.new(unreal.MaterialExpressionCameraVectorWS)
    d = g.mul(cam, -1.0)
    rot = g.new(unreal.MaterialExpressionRotateAboutAxis)
    g.link(g.c3(0.0, 0.0, 1.0), rot, "NormalizedRotationAxis")
    g.link(g.scalar("Yaw", 0.0, "Sky"), rot, "RotationAngle")
    g.link(g.c3(0.0, 0.0, 0.0), rot, "PivotPoint")
    g.link(d, rot, "Position")
    dd = g.add(d, rot)
    n = g.new(unreal.MaterialExpressionTextureSampleParameterCube, parameter_name="SkyCube", texture=cube, group="Sky")
    g.link(dd, n, "UVs")
    col = (n, "RGB")
    z = g.mask(d, b=True)
    band = g.power(g.one_minus(g.sat(g.absx(z))), g.scalar("HorizonPower", 6.0, "Sky"))
    tinted = g.mul(col, g.lerp(g.vec("ZenithTint", (0.75, 0.62, 1.0)), g.vec("HorizonTint", (1.0, 0.62, 0.78)), band))
    g.out("MP_EMISSIVE_COLOR", g.mul(tinted, g.scalar("Exposure", 1.0, "Sky")))
    finish_material(mat)
    return mat


def build_rock_pbr():
    """Volcanic rock (Poly Haven dark_rock, CC0), world-space triplanar for procedural terrain."""
    T = "/Game/Twilight/Env/Textures/dark_rock_"
    diff, nor, arm = _load(T + "diff_2k"), _load(T + "nor_gl_2k"), _load(T + "arm_2k")
    if diff is None or nor is None:
        warn("dark_rock textures missing - M_RockPBR skipped")
        return None
    mat = get_or_create_material("M_RockPBR")
    setup_material(mat, usages=("MATUSAGE_INSTANCED_STATIC_MESHES",))
    g = G(mat)
    wp = g.world_pos("XYZ")
    p = g.div(wp, g.scalar("Tiling", 1200.0, "Surface"))
    nrm = g.new(unreal.MaterialExpressionVertexNormalWS)
    w = g.power(g.absx(nrm), 4.0)
    w = g.div(w, g.dot(w, g.c3(1.0, 1.0, 1.0)))
    wx, wy, wz = g.mask(w, r=True), g.mask(w, g=True), g.mask(w, b=True)
    uv_x = g.append(g.mask(p, g=True), g.mask(p, b=True))
    uv_y = g.append(g.mask(p, r=True), g.mask(p, b=True))
    uv_z = g.append(g.mask(p, r=True), g.mask(p, g=True))
    dobj = g.tex_param_obj("RockDiff", diff)
    def tri(obj, tex, out="RGB"):
        a = g.sample(obj, tex, uv_x, out); b = g.sample(obj, tex, uv_y, out); c = g.sample(obj, tex, uv_z, out)
        return g.add(g.add(g.mul(a, wx), g.mul(b, wy)), g.mul(c, wz))
    base = tri(dobj, diff)
    macro = g.sample(dobj, diff, g.mul(uv_z, 0.11))
    base = g.mul(base, g.lerp(g.c1(0.75), g.c1(1.25), g.dot(macro, g.c3(0.33, 0.33, 0.33))))
    up = g.sat(g.mul(g.sub(g.mask(nrm, b=True), 0.6), 3.0))
    base = g.lerp(base, g.mul(base, g.vec("TopTint", (1.6, 1.3, 1.25))), g.mul(up, g.scalar("TopAmount", 0.4, "Surface")))
    haze = g.scalar("HazeAmount", 0.0, "Haze")   # fake aerial perspective for far landmarks (Masis)
    g.out("MP_BASE_COLOR", g.mul(g.mul(base, g.vec("Tint", (1.0, 0.92, 0.95))), g.one_minus(haze)))
    g.out("MP_EMISSIVE_COLOR", g.mul(g.vec("HazeColor", (0.55, 0.42, 0.62), "Haze"), haze))
    nobj = g.tex_param_obj("RockNormal", nor)
    nz = g.sample(nobj, nor, uv_z)
    g.out("MP_NORMAL", g.lerp(g.c3(0.0, 0.0, 1.0), nz, g.scalar("NormalStrength", 0.8, "Surface")))
    if arm is not None:
        aobj = g.tex_param_obj("RockARM", arm)
        g.out("MP_ROUGHNESS", g.sat(g.mul(tri(aobj, arm, "G"), g.scalar("RoughnessScale", 1.0, "Surface"))))
        g.out("MP_AMBIENT_OCCLUSION", tri(aobj, arm, "R"))
    else:
        g.out("MP_ROUGHNESS", g.c1(0.85))
    finish_material(mat)
    return mat



def build_hero(noise_tex):
    """Vahagn: molten bronze god. Lit metallic bronze using the mannequin's own normal/MRA maps (real anatomy
    detail), thin flowing lava veins, fire rim. Same parameter names as M_FireBody (EmissiveIntensity, RimIntensity,
    HitFlash, FlashColor) so the character code drives either."""
    M = "/Game/Characters/Mannequins/Textures/Manny/"
    bn, mra, dif = _load(M + "T_Manny_01_BN"), _load(M + "T_Manny_01_MRA"), _load(M + "T_Manny_01_D")
    if bn is None or noise_tex is None:
        warn("Manny textures missing - M_Hero skipped")
        return None
    mat = get_or_create_material("M_Hero")
    setup_material(mat, usages=("MATUSAGE_SKELETAL_MESH",))
    g = G(mat)
    t = g.time()
    uv = g.texcoord()
    g.out("MP_NORMAL", g.tex_param("NormalTex", bn, uv))
    shade = g.c1(1.0)
    if dif is not None:
        d = g.tex_param("DiffTex", dif, uv)
        shade = g.lerp(g.c1(0.7), g.c1(1.25), g.dot(d, g.c3(0.33, 0.33, 0.33)))
    if mra is not None:
        r = g.tex_param("MRATex", mra, uv, "G")
        g.out("MP_ROUGHNESS", g.sat(g.add(g.mul(r, 0.5), g.scalar("RoughnessBias", 0.18, "Surface"))))
    else:
        g.out("MP_ROUGHNESS", g.c1(0.35))
    g.out("MP_METALLIC", g.scalar("Metallic", 0.85, "Surface"))
    # lava veins: sharp ridges of flowing noise
    nobj = g.tex_param_obj("NoiseTex", noise_tex)
    tflow = g.mul(t, g.scalar("FlowSpeed", 0.6, "Cracks"))
    uv1 = g.mul(uv, g.scalar("NoiseTiling", 3.0, "Cracks"))
    n1 = g.sample(nobj, noise_tex, g.panner(uv1, 0.02, 0.05, tflow), "R")
    n2 = g.sample(nobj, noise_tex, g.panner(g.mul(uv1, 2.3), -0.04, 0.03, tflow), "R")
    n = g.mul(g.add(n1, n2), 0.5)
    ridge = g.one_minus(g.absx(g.sub(g.mul(n, 2.0), 1.0)))
    veins = g.sat(g.mul(g.power(ridge, g.scalar("CrackSharpness", 90.0, "Cracks")), 1.5))
    g.out("MP_BASE_COLOR", g.mul(g.mul(g.vec("SkinColor", (0.55, 0.3, 0.12)), shade), g.one_minus(veins)))
    pulse = g.add(g.mul(g.sine(g.mul(t, 0.7)), 0.15), 1.0)
    e_veins = g.mul(g.mul(g.vec("CrackColorHot", (1.0, 0.45, 0.08)), veins), g.mul(g.scalar("EmissiveIntensity", 3.0, "Emissive"), pulse))
    fr = g.fresnel(g.scalar("RimExponent", 3.0, "Rim"))
    rim = g.mul(g.mul(g.vec("RimColor", (1.0, 0.42, 0.08)), fr), g.scalar("RimIntensity", 1.2, "Rim"))
    flash = g.mul(g.vec("FlashColor", (1.0, 0.22, 0.04)), g.scalar("HitFlash", 0.0, "Emissive"))
    g.out("MP_EMISSIVE_COLOR", g.add(g.add(e_veins, rim), flash))
    finish_material(mat)
    return mat



# ---------------------------------------------------------------- islands (photogrammetry, proto-verified)
def grade(g, diff, arm_r, arm_g, nrm_ws_z, macro_obj, macro_tex):
    """Scan albedo -> basalt: desaturate, darken, world macro variation, oxidised patches, ledge dust,
    wet band above the sea by world Z. Returns (base_color, roughness)."""
    wp = g.world_pos("XYZ")
    lum = g.dot(diff, g.c3(0.3, 0.59, 0.11))
    base = g.lerp(diff, lum, g.scalar('Desaturate', 0.65, 'Grade'))
    base = g.mul(base, g.vec('BasaltTint', (0.62, 0.6, 0.6), 'Grade'))
    # contrast around mid grey keeps the scan's crevice detail while darkening
    base = g.power(g.maxx(base, 0.0001), g.scalar('AlbedoGamma', 1.15, 'Grade'))
    # world-space macro variation (breaks scan repetition across pieces): R = brightness, G = oxidised tint
    m = g.sample(macro_obj, macro_tex, g.div(g.mask(wp, r=True, g=True), g.scalar('MacroScale', 9000.0, 'Macro')))
    m2 = g.sample(macro_obj, macro_tex, g.div(g.mask(wp, r=True, g=True), g.scalar('MacroScale2', 2300.0, 'Macro')))
    mr = g.mul(g.add(g.mask(m, r=True), g.mask(m2, r=True)), 0.5)
    base = g.mul(base, g.lerp(g.scalar('MacroMin', 0.7, 'Macro'), g.scalar('MacroMax', 1.25, 'Macro'), mr))
    rust = g.sat(g.mul(g.sub(g.mask(m, g=True), 0.5), 3.0))
    base = g.lerp(base, g.mul(base, g.vec('OxideTint', (1.35, 0.85, 0.62), 'Macro')), g.mul(rust, g.scalar('OxideAmount', 0.5, 'Macro')))
    # ledges facing up collect pale ash/salt
    up = g.sat(g.mul(g.sub(nrm_ws_z, g.scalar('TopThreshold', 0.65, 'Top')), 4.0))
    base = g.lerp(base, g.mul(g.vec('TopColor', (0.16, 0.15, 0.14), 'Top'), g.add(g.mul(mr, 0.6), 0.7)), g.mul(up, g.scalar('TopAmount', 0.35, 'Top')))
    # wet band: dark + glossy below SeaZ + WetHeight (edge jittered by the macro noise)
    z = g.mask(wp, b=True)
    wet_top = g.add(g.scalar('SeaZ', 0.0, 'Wet'), g.mul(g.scalar('WetHeight', 450.0, 'Wet'), g.add(g.mul(g.mask(m2, b=True), 0.9), 0.55)))
    wet = g.sat(g.div(g.sub(wet_top, z), g.scalar('WetFade', 120.0, 'Wet')))
    base = g.mul(base, g.lerp(g.c1(1.0), g.scalar('WetDarken', 0.45, 'Wet'), wet))
    # tide-line algae: very dark green-black just above the water
    algae = g.sat(g.div(g.sub(g.add(g.scalar('SeaZ', 0.0, 'Wet'), g.scalar('AlgaeHeight', 120.0, 'Wet')), z), 60.0))
    base = g.lerp(base, g.vec('AlgaeColor', (0.012, 0.016, 0.012), 'Wet'), g.mul(algae, g.scalar('AlgaeAmount', 0.7, 'Wet')))
    rough = g.sat(g.mul(arm_g, g.scalar('RoughnessScale', 1.0, 'Surface')))
    rough = g.lerp(rough, g.scalar('WetRoughness', 0.7, 'Wet'), wet)
    base = g.mul(base, g.scalar('Brightness', 1.0, 'Grade'))
    return base, rough


def build_scan_rock(diff, nor, arm, macro):
    mat = get_or_create_material('M_ScanRock')
    setup_material(mat, two_sided=True, usages=('MATUSAGE_INSTANCED_STATIC_MESHES',))
    g = G(mat)
    uv = g.texcoord()
    d = g.sample(g.tex_param_obj('Diff', diff), diff, uv)
    aobj = g.tex_param_obj('ARM', arm)
    a = g.sample(aobj, arm, uv, 'RGB')
    n = g.sample(g.tex_param_obj('Normal', nor), nor, uv)
    nws = g.mask(g.new(unreal.MaterialExpressionVertexNormalWS), b=True)
    mobj = g.tex_param_obj('MacroNoise', macro)
    base, rough = grade(g, d, g.mask(a, r=True), g.mask(a, g=True), nws, mobj, macro)
    g.out('MP_BASE_COLOR', base)
    g.out('MP_ROUGHNESS', rough)
    g.out('MP_SPECULAR', g.scalar('Specular', 0.3, 'Surface'))
    g.out('MP_AMBIENT_OCCLUSION', g.lerp(g.c1(1.0), g.mask(a, r=True), g.scalar('AOAmount', 1.0, 'Surface')))
    g.out('MP_NORMAL', g.lerp(g.c3(0.0, 0.0, 1.0), n, g.scalar('NormalStrength', 1.0, 'Surface')))
    finish_material(mat)
    return mat


def build_island_terrain(sdiff, snor, sarm, tdiff, tnor, tarm, macro):
    """Heightfield core: steep faces = triplanar dark basalt (dark_rock), flats = top-down aerial photogrammetry
    (aerial_rocks_02, 50 m tile) partially desaturated; then the same grade() as the scan facades."""
    mat = get_or_create_material('M_IslandTerrain')
    setup_material(mat, usages=('MATUSAGE_INSTANCED_STATIC_MESHES',))
    g = G(mat)
    wp = g.world_pos("XYZ")
    p = g.div(wp, g.scalar('SteepTiling', 1800.0, 'Surface'))
    nrm = g.new(unreal.MaterialExpressionVertexNormalWS)
    w = g.power(g.absx(nrm), 4.0)
    w = g.div(w, g.dot(w, g.c3(1.0, 1.0, 1.0)))
    wx, wy, wz = g.mask(w, r=True), g.mask(w, g=True), g.mask(w, b=True)
    uvx = g.append(g.mask(p, g=True), g.mask(p, b=True))
    uvy = g.append(g.mask(p, r=True), g.mask(p, b=True))
    uvz = g.append(g.mask(p, r=True), g.mask(p, g=True))
    sobj = g.tex_param_obj('SteepDiff', sdiff); saobj = g.tex_param_obj('SteepARM', sarm)
    def tri(obj, tex, out='RGB'):
        a = g.sample(obj, tex, uvx, out); b = g.sample(obj, tex, uvy, out); c = g.sample(obj, tex, uvz, out)
        return g.add(g.add(g.mul(a, wx), g.mul(b, wy)), g.mul(c, wz))
    sd = g.mul(tri(sobj, sdiff), g.scalar('SteepBright', 1.6, 'Surface'))
    sa = tri(saobj, sarm)
    tuv = g.div(g.mask(wp, r=True, g=True), g.scalar('TopTiling', 5000.0, 'Surface'))
    td = g.sample(g.tex_param_obj('TopDiff', tdiff), tdiff, tuv)
    tlum = g.dot(td, g.c3(0.3, 0.59, 0.11))
    td = g.mul(g.lerp(td, tlum, g.scalar('TopDesaturate', 0.55, 'Surface')), g.scalar('TopBright', 0.45, 'Surface'))
    ta = g.sample(g.tex_param_obj('TopARM', tarm), tarm, tuv, 'RGB')
    mobj = g.tex_param_obj('MacroNoise', macro)
    mn = g.mask(g.sample(mobj, macro, g.div(g.mask(wp, r=True, g=True), 3100.0)), b=True)
    nz = g.mask(nrm, b=True)
    topm = g.sat(g.div(g.sub(g.add(nz, g.mul(g.sub(mn, 0.5), 0.3)), g.scalar('TopStart', 0.72, 'Surface')), g.scalar('TopFade', 0.12, 'Surface')))
    d = g.lerp(sd, td, topm)
    a = g.lerp(sa, ta, topm)
    base, rough = grade(g, d, g.mask(a, r=True), g.mask(a, g=True), nz, mobj, macro)
    g.out('MP_BASE_COLOR', base)
    g.out('MP_ROUGHNESS', rough)
    g.out('MP_SPECULAR', g.scalar('Specular', 0.3, 'Surface'))
    g.out('MP_AMBIENT_OCCLUSION', g.mask(a, r=True))
    sn = g.sample(g.tex_param_obj('SteepNormal', snor), snor, uvz)
    tn = g.sample(g.tex_param_obj('TopNormal', tnor), tnor, tuv)
    g.out('MP_NORMAL', g.lerp(g.c3(0.0, 0.0, 1.0), g.lerp(sn, tn, topm), g.scalar('NormalStrength', 0.8, 'Surface')))
    finish_material(mat)
    return mat




def build_islands_set():
    """M_IslandTerrain (heightfield core) + M_ScanRock (Poly Haven boulder_01) and their instances."""
    macro = _load("/Game/Twilight/Env/Textures/T_MacroNoise")
    D = "/Game/Twilight/Env/Textures/dark_rock_"
    A = "/Game/Twilight/Env/Textures/aerial_rocks_02_"
    if macro is None or _load(A + "diff_2k") is None:
        warn("island textures missing - island materials skipped")
        return None
    isl = build_island_terrain(_load(D + "diff_2k"), _load(D + "nor_gl_2k"), _load(D + "arm_2k"),
                               _load(A + "diff_2k"), _load(A + "nor_gl_2k"), _load(A + "arm_2k"), macro)
    make_mi("MI_IslandTerrain", isl, scalars={"TopAmount": 0.0, "OxideAmount": 0.15, "Desaturate": 0.5, "TopStart": 0.62},
            vectors={"BasaltTint": (0.52, 0.52, 0.55)})
    B = "/Game/Twilight/Env/Scan/boulder_01/"
    bd, bn, ba = _load(B + "boulder_01_diff_2k"), _load(B + "boulder_01_nor_gl_2k"), _load(B + "boulder_01_arm_2k")
    if bd is not None:
        sc = build_scan_rock(bd, bn, ba, macro)
        make_mi("MI_Scan_boulder_01", sc, scalars={"TopAmount": 0.1, "Desaturate": 0.85, "AlbedoGamma": 1.3, "OxideAmount": 0.15},
                vectors={"BasaltTint": (0.45, 0.45, 0.47)})
    return isl

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
        ("M_Dragon", build_dragon),
        ("M_DragonTeeth", build_dragon_teeth),
        ("M_SkyHDRI", build_sky_hdri),
        ("M_RockPBR", build_rock_pbr),
        ("M_Hero", lambda: build_hero(noise)),
        ("M_IslandTerrain", build_islands_set),
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
