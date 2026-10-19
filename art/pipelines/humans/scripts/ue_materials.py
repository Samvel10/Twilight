# -*- coding: utf-8 -*-
"""Look-dev for the realistic human characters (UE 5.8 editor python).
Builds ONE master /Game/Twilight/Materials/M_Human (default lit, skeletal-mesh usage) and per-slot instances
/Game/Twilight/Humans/<Char>/Materials/MI_<Char>_<slot>, then assigns them to each skeletal mesh.
Uses the G helpers of Game/Tools/materials_build.py (exec'd without its main()), so build_human_master() can be pasted there.

M_Human parameters (all MI-overridable):
  Textures  BaseTex, NormalTex, MRTex (glTF: G=roughness, B=metal), DetailNormalTex (skin pores), NoiseTex
  Surface   Saturation, Brightness, Tint, Roughness, Specular, MetalMask (x MR.B), ForceMetal, MetalTint, MetalTintAmount,
            MetalRoughness, NormalStrength
  Recolor1/2  Recolor{n}Src (a colour whose hue is matched), Recolor{n}Dst (new colour, luminance kept), Recolor{n}Amount,
            Recolor{n}Width (0.5..0.98 cosine threshold) -> repaint garish/off-period dyes, remove woad tattoos
  Detail    DetailStrength, DetailTiling, Mottle, MottleTiling
  Dirt      DirtAmount, DirtColor, DirtTiling, DustHeight (cm, ref pose: dust rises from the feet), DustAmount
  Variation (per component, CustomPrimitiveData 0..2):  CPD0 -> lerp(Tint, TintAlt, CPD0*TintVar)  [cloth dye variation]
            CPD1 -> brightness (1+(CPD1-0.5)*ToneVar) [skin tone / fading],  CPD2 -> extra dirt
  Game      RimIntensity/RimColor, HitFlash/FlashColor (same names as M_Hero)"""
import os, json, unreal

def build_human_master(noise_tex, detail_tex):
    mat = get_or_create_material("M_Human")
    setup_material(mat, shading="MSM_DEFAULT_LIT", usages=("MATUSAGE_SKELETAL_MESH", "MATUSAGE_STATIC_LIGHTING", "MATUSAGE_INSTANCED_STATIC_MESHES"))
    g = G(mat)
    uv = g.texcoord()
    base = g.tex_param("BaseTex", unreal.load_asset("/Engine/EngineResources/DefaultTexture"), uv)
    nrm = g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="NormalTex",
                texture=unreal.load_asset("/Engine/EngineMaterials/DefaultNormal"), group="Textures")
    g.link(uv, nrm, "UVs")
    mr = g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="MRTex",
               texture=unreal.load_asset("/Interchange/gltf/Textures/T_White_Linear"), group="Textures")
    g.link(uv, mr, "UVs")
    dn = g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="DetailNormalTex",
               texture=detail_tex or unreal.load_asset("/Engine/EngineMaterials/DefaultNormal"), group="Textures")
    g.link(g.mul(uv, g.scalar("DetailTiling", 22.0, "Detail")), dn, "UVs")
    nxy = g.mul(g.mask((nrm, "RGB"), r=True, g=True), g.scalar("NormalStrength", 1.0, "Surface"))
    nxy = g.add(nxy, g.mul(g.mask((dn, "RGB"), r=True, g=True), g.scalar("DetailStrength", 0.0, "Detail")))
    g.out("MP_NORMAL", g.normalize(g.append(nxy, g.mask((nrm, "RGB"), b=True))))
    # custom primitive data (per soldier variation)
    cpd = [g.new(unreal.MaterialExpressionScalarParameter, parameter_name="CPD%d" % i, default_value=(0.5 if i == 1 else 0.0), group="Variation",
                 use_custom_primitive_data=True, primitive_data_index=i) for i in range(3)]
    W = g.c3(0.3, 0.59, 0.11)
    col = base
    # ---- hue recolours (luminance preserving)
    for k in ("1", "2"):
        lum = g.dot(col, W)
        chroma = g.sub(col, lum)
        src = g.vec("Recolor%sSrc" % k, (0, 0, 1))
        srcc = g.normalize(g.add(g.sub(src, g.dot(src, W)), g.c3(1e-4, 1e-4, 1e-4)))
        cosang = g.dot(g.normalize(g.add(chroma, g.c3(1e-4, 1e-4, 1e-4))), srcc)
        wdt = g.scalar("Recolor%sWidth" % k, 0.8, "Recolor")
        w = g.sat(g.div(g.sub(cosang, wdt), g.sub(1.0001, wdt)))
        strength = g.sat(g.mul(g.dot(chroma, chroma), g.scalar("Recolor%sSens" % k, 300.0, "Recolor")))     # ignore near-grey texels
        w = g.mul(g.mul(w, strength), g.scalar("Recolor%sAmount" % k, 0.0, "Recolor"))
        dst = g.vec("Recolor%sDst" % k, (0.5, 0.5, 0.5))
        newc = g.lerp(dst, g.mul(dst, g.div(lum, g.maxx(g.dot(dst, W), 0.02))), g.scalar("Recolor%sKeepLum" % k, 1.0, "Recolor"))
        col = g.lerp(col, newc, w)
    lum = g.dot(col, W)
    col = g.lerp(lum, col, g.scalar("Saturation", 1.0, "Surface"))
    tint = g.lerp(g.vec("Tint", (1, 1, 1)), g.vec("TintAlt", (1, 1, 1)), g.sat(g.mul(cpd[0], g.scalar("TintVar", 0.0, "Variation"))))
    col = g.mul(col, tint)
    tone = g.add(1.0, g.mul(g.sub(cpd[1], 0.5), g.scalar("ToneVar", 0.0, "Variation")))
    col = g.mul(col, g.mul(tone, g.scalar("Brightness", 1.0, "Surface")))
    # ---- mottling
    nobj = g.tex_param_obj("NoiseTex", noise_tex)
    mn = g.sample(nobj, noise_tex, g.mul(uv, g.scalar("MottleTiling", 3.0, "Detail")), "R")
    col = g.mul(col, g.add(g.mul(g.sub(mn, 0.5), g.mul(g.scalar("Mottle", 0.0, "Detail"), 2.0)), 1.0))
    # ---- metal
    metal = g.sat(g.maxx(g.mul((mr, "B"), g.scalar("MetalMask", 1.0, "Surface")), g.scalar("ForceMetal", 0.0, "Surface")))
    lum2 = g.dot(col, W)
    mt = g.mul(g.sat(g.mul(lum2, 1.6)), g.vec("MetalTint", (0.83, 0.52, 0.26)))
    col = g.lerp(col, mt, g.mul(metal, g.scalar("MetalTintAmount", 0.0, "Surface")))
    # ---- dirt: noise grime everywhere + dust rising from the feet (pre-skinned local Z, cm)
    dirt_n = g.sample(nobj, noise_tex, g.mul(uv, g.scalar("DirtTiling", 5.0, "Dirt")), "R")
    vi = g.new(unreal.MaterialExpressionVertexInterpolator)   # PreSkinnedPosition is vertex-shader only
    g.link(g.mask(g.new(unreal.MaterialExpressionPreSkinnedPosition), b=True), vi, "")
    psz = vi
    dust = g.sat(g.div(g.sub(g.scalar("DustHeight", 45.0, "Dirt"), psz), g.scalar("DustHeight", 45.0, "Dirt")))
    dirt = g.add(g.mul(g.sat(g.mul(g.sub(dirt_n, 0.35), 2.0)), g.add(g.scalar("DirtAmount", 0.0, "Dirt"), g.mul(cpd[2], 0.3))),
                 g.mul(dust, g.scalar("DustAmount", 0.0, "Dirt")))
    dirt = g.sat(dirt)
    col = g.lerp(col, g.mul(g.vec("DirtColor", (0.25, 0.19, 0.13)), g.add(g.mul(lum2, 0.6), 0.4)), dirt)
    g.out("MP_BASE_COLOR", col)
    g.out("MP_METALLIC", g.mul(metal, g.one_minus(g.mul(dirt, 0.8))))
    rough = g.mul((mr, "G"), g.scalar("Roughness", 0.6, "Surface"))
    rough = g.lerp(rough, g.scalar("MetalRoughness", 0.35, "Surface"), metal)
    g.out("MP_ROUGHNESS", g.lerp(rough, 0.95, dirt))
    g.out("MP_SPECULAR", g.scalar("Specular", 0.5, "Surface"))
    fr = g.fresnel(g.scalar("RimExponent", 4.0, "Emissive"))
    em = g.mul(g.mul(g.vec("RimColor", (1.0, 0.42, 0.08)), fr), g.scalar("RimIntensity", 0.0, "Emissive"))
    em = g.add(em, g.mul(g.vec("FlashColor", (1.0, 0.22, 0.04)), g.scalar("HitFlash", 0.0, "Emissive")))
    g.out("MP_EMISSIVE_COLOR", em)
    finish_material(mat)
    return mat

import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/scripts")
from mat_spec import *

def tex_of(src, key):
    for pv in src.get_editor_property("texture_parameter_values"):
        if key.lower() in str(pv.parameter_info.name).lower() and pv.parameter_value: return pv.parameter_value
def scal_of(src, key):
    for pv in src.get_editor_property("scalar_parameter_values"):
        if str(pv.parameter_info.name) == key: return pv.parameter_value

def build_human_instances(master, char, n, spec, noise):
    mesh_path = "/Game/Twilight/Humans/%s/Mesh/%s/SkeletalMeshes/%s" % (char, n, n)
    sk = unreal.load_asset(mesh_path)
    if sk is None: warn("no mesh %s" % mesh_path); return
    dest = "/Game/Twilight/Humans/%s/Materials" % char
    new = []
    for m in sk.get_editor_property("materials"):
        slot = str(m.material_slot_name)
        src = unreal.load_asset("/Game/Twilight/Humans/%s/Mesh/%s/Materials/%s" % (char, n, slot)) or m.material_interface
        mi = get_or_create_mi("MI_%s_%s" % (char, slot), master) if False else None
        path = "%s/MI_%s_%s" % (dest, char, slot)
        mi = unreal.load_asset(path) if asset_on_disk(path) else ASSET_TOOLS.create_asset("MI_%s_%s" % (char, slot), dest, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, master); MEL.clear_all_material_instance_parameters(mi)
        for pn, key in (("BaseTex", "BaseColor"), ("NormalTex", "Normal"), ("MRTex", "MetallicRoughness")):
            t = tex_of(src, key) if src else None
            if t is not None: MEL.set_material_instance_texture_parameter_value(mi, pn, t)
        MEL.set_material_instance_texture_parameter_value(mi, "NoiseTex", noise)
        sp = spec.get(slot, {})
        sc = dict(sp.get("s", {}))
        mf, rf = (scal_of(src, "MetallicFactor") if src else None), (scal_of(src, "RoughnessFactor") if src else None)
        if "MetalMask" not in sc and mf is not None: sc["MetalMask"] = mf
        if "Roughness" not in sc and rf is not None and rf > 0.05: sc["Roughness"] = rf
        for k, v in sc.items(): MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
        for k, v in sp.get("v", {}).items(): MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
        MEL.update_material_instance(mi); save(mi)
        c = unreal.SkeletalMaterial(); c.set_editor_property("material_interface", mi); c.set_editor_property("material_slot_name", m.material_slot_name)
        new.append(c)
    sk.modify(); sk.set_editor_property("materials", new); save(sk)
    log("assigned %s %d slots" % (char, len(new)))

if __name__ == "__main__":
    MB = os.environ.get("TW_MATERIALS_BUILD", "/var/www/html/Twilight/Game/Tools/materials_build.py")
    _src_code = open(MB).read().rsplit("\nmain()", 1)[0]
    exec(compile(_src_code, MB, "exec"))
    ROOT = "/Game/Twilight/Materials"
    noise = load_first(TEX_NOISE, "noise")
    detail = unreal.load_asset("/Game/Twilight/Hero/Textures/T_SkinDetail_N")
    master = build_human_master(noise, detail)
    only = [c for c in os.environ.get("HUM_ONLY", "").split(",") if c]
    for char, spec in SPEC.items():
        if only and char not in only: continue
        build_human_instances(master, char, char.lower(), spec, noise)
    unreal.log_warning("HUM materials done errors=%d %s" % (len(ERRORS), ERRORS))
