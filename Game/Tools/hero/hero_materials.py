# -*- coding: utf-8 -*-
"""Vahagn realistic hero materials (UE 5.8 editor python).
build_hero_pbr() is written against the helpers of Game/Tools/materials_build.py (G, setup_material, finish_material,
get_or_create_material, make_mi-like code) so it can be pasted into that file as one more step.
Standalone (scratch) use: exec's the helpers from materials_build.py (without running its main()).

Masters (ROOT=/Game/Twilight/Materials):
  M_HeroSkin  skin: default-lit by default (env HERO_SKIN_MODEL=MSM_SUBSURFACE_PROFILE for SSS with SP_HeroSkin)
  M_HeroPBR   default-lit gear: leather / cloth / bronze
Both: BaseTex, NormalTex, MRTex (glTF: G=roughness, B=metal), Tint, Saturation, Roughness, Specular, Metallic,
      ForceMetal, BronzeAmount/BronzeColor/MetalRoughness (re-colours metal parts as polished bronze),
      game params kept from M_Hero: EmissiveIntensity (ember veins), RimIntensity/RimColor, HitFlash/FlashColor,
      plus CrestGlow/GlowColor (emissive for saturated-red texels: the helmet crest as a flame).
Instances (HERO_MAT_DIR, default /Game/Twilight/Hero/Materials):  MI_Vahagn_<slot>  for slots
  Body, Pants, Cross_strap, Leg_guard, Blanket, Helmet  (textures taken from the Interchange-imported MICs)."""
import os, unreal

def import_detail_normal(png, dest_dir):
    """the procedural pore normal (make_skin_detail.py) as a TC_Normalmap texture"""
    path = dest_dir + "/T_SkinDetail_N"
    if not asset_on_disk(path):
        t = unreal.AssetImportTask(); t.filename = png; t.destination_path = dest_dir; t.destination_name = "T_SkinDetail_N"
        t.automated = True; t.replace_existing = True; t.save = True
        ASSET_TOOLS.import_asset_tasks([t])
    tex = unreal.load_asset(path)
    if tex is not None:
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("srgb", False)
        save(tex)
    return tex

def build_hero_masters(noise_tex, detail_tex=None):
    out = {}
    sp_path = ROOT + "/SP_HeroSkin"
    if asset_on_disk(sp_path):
        sp = unreal.load_asset(sp_path)
    else:
        sp = ASSET_TOOLS.create_asset("SP_HeroSkin", ROOT, unreal.SubsurfaceProfile, unreal.SubsurfaceProfileFactory())
    try:
        s = sp.get_editor_property("settings")
        s.set_editor_property("surface_albedo", unreal.LinearColor(0.91, 0.34, 0.22, 1))   # warm, tanned skin
        s.set_editor_property("mean_free_path_color", unreal.LinearColor(1.0, 0.33, 0.1, 1))
        s.set_editor_property("mean_free_path_distance", 0.6)
        s.set_editor_property("world_unit_scale", 0.1)
        sp.set_editor_property("settings", s)
    except Exception as e:  # noqa - property names differ between versions; defaults are a usable skin
        warn("SP_HeroSkin settings: %s" % e)
    save(sp)
    for name, skin in (("M_HeroSkin", True), ("M_HeroPBR", False)):
        mat = get_or_create_material(name)
        skin_model = os.environ.get("HERO_SKIN_MODEL", "MSM_DEFAULT_LIT")   # MSM_SUBSURFACE_PROFILE = softer, ~+1 ms GPU on Iris Xe; MSM_PREINTEGRATED_SKIN washed out
        setup_material(mat, shading=skin_model if skin else "MSM_DEFAULT_LIT", usages=("MATUSAGE_SKELETAL_MESH",))
        if skin and skin_model == "MSM_PREINTEGRATED_SKIN":
            g0 = G(mat)
            g0.out("MP_SUBSURFACE_COLOR", g0.vec("SubsurfaceColor", (0.75, 0.22, 0.12)))
            g0.out("MP_OPACITY", g0.scalar("SubsurfaceAmount", 0.6, "Surface"))
        if skin and skin_model == "MSM_SUBSURFACE_PROFILE":
            mat.set_editor_property("subsurface_profile", sp)
        g = G(mat)
        uv = g.texcoord()
        base = g.tex_param("BaseTex", unreal.load_asset("/Engine/EngineResources/DefaultTexture"), uv)
        nrm = g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="NormalTex",
                    texture=unreal.load_asset("/Engine/EngineMaterials/DefaultNormal"), group="Textures")
        g.link(uv, nrm, "UVs")
        mr_node = g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="MRTex",
                        texture=unreal.load_asset("/Interchange/gltf/Textures/T_White_Linear"), group="Textures")  # linear (MR maps are not sRGB)
        g.link(uv, mr_node, "UVs")
        # tiling micro detail normal (pores) blended onto the baked normal: n = normalize(n1.xy + d.xy*k, n1.z)
        dn = g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name="DetailNormalTex",
                   texture=detail_tex or unreal.load_asset("/Engine/EngineMaterials/DefaultNormal"), group="Textures")
        g.link(g.mul(uv, g.scalar("DetailTiling", 22.0, "Detail")), dn, "UVs")
        nxy = g.add(g.mask((nrm, "RGB"), r=True, g=True), g.mul(g.mask((dn, "RGB"), r=True, g=True), g.scalar("DetailStrength", 0.0, "Detail")))
        g.out("MP_NORMAL", g.normalize(g.append(nxy, g.mask((nrm, "RGB"), b=True))))
        lum = g.dot(base, g.c3(0.3, 0.59, 0.11))
        col = g.lerp(lum, base, g.scalar("Saturation", 1.0, "Surface"))
        col = g.mul(col, g.vec("Tint", (1, 1, 1)))
        if noise_tex is not None:   # low-frequency mottling (blood flow / tan variation)
            mn = g.tex_param("MottleTex", noise_tex, g.mul(uv, g.scalar("MottleTiling", 3.0, "Detail")), "R")
            col = g.mul(col, g.add(g.mul(g.sub(mn, 0.5), g.mul(g.scalar("Mottle", 0.0, "Detail"), 2.0)), 1.0))
        # metal mask (texture B) or forced; bronze recolour of metal parts
        metal = g.sat(g.maxx(g.mul((mr_node, "B"), g.scalar("MetalMask", 1.0, "Surface")), g.scalar("ForceMetal", 0.0, "Surface")))
        bronze = g.mul(g.mul(g.sat(g.mul(lum, 1.6)), g.vec("BronzeColor", (0.83, 0.52, 0.26))), 1.0)
        col = g.lerp(col, bronze, g.mul(metal, g.scalar("BronzeAmount", 0.0, "Surface")))
        g.out("MP_BASE_COLOR", col)
        g.out("MP_METALLIC", g.mul(metal, g.scalar("Metallic", 1.0, "Surface")))
        rough = g.mul((mr_node, "G"), g.scalar("Roughness", 0.6, "Surface"))  # MR.G is 1.0 on these textures -> this is the roughness
        g.out("MP_ROUGHNESS", g.lerp(rough, g.scalar("MetalRoughness", 0.35, "Surface"), metal))
        g.out("MP_SPECULAR", g.scalar("Specular", 0.5, "Surface"))
        # emissive: crest flame + (optional) ember veins + rim + hit flash
        red = g.sat(g.mul(g.sub(g.mask(base, r=True), g.maxx(g.mask(base, g=True), g.mask(base, b=True))), 3.0))
        crest = g.mul(g.mul(red, g.vec("GlowColor", (1.0, 0.35, 0.06))), g.scalar("CrestGlow", 0.0, "Emissive"))
        em = crest
        if noise_tex is not None:
            t = g.time()
            nobj = g.tex_param_obj("NoiseTex", noise_tex)
            tflow = g.mul(t, g.scalar("FlowSpeed", 0.5, "Emissive"))
            uv1 = g.mul(uv, g.scalar("NoiseTiling", 3.0, "Emissive"))
            n1 = g.sample(nobj, noise_tex, g.panner(uv1, 0.02, 0.05, tflow), "R")
            n2 = g.sample(nobj, noise_tex, g.panner(g.mul(uv1, 2.3), -0.04, 0.03, tflow), "R")
            n = g.mul(g.add(n1, n2), 0.5)
            ridge = g.one_minus(g.absx(g.sub(g.mul(n, 2.0), 1.0)))
            veins = g.sat(g.mul(g.power(ridge, g.scalar("CrackSharpness", 90.0, "Emissive")), 1.5))
            em = g.add(em, g.mul(g.mul(g.vec("CrackColorHot", (1.0, 0.45, 0.08)), veins), g.scalar("EmissiveIntensity", 0.0, "Emissive")))
        fr = g.fresnel(g.scalar("RimExponent", 4.0, "Emissive"))
        em = g.add(em, g.mul(g.mul(g.vec("RimColor", (1.0, 0.42, 0.08)), fr), g.scalar("RimIntensity", 0.0, "Emissive")))
        em = g.add(em, g.mul(g.vec("FlashColor", (1.0, 0.22, 0.04)), g.scalar("HitFlash", 0.0, "Emissive")))
        g.out("MP_EMISSIVE_COLOR", em)
        finish_material(mat)
        out[name] = mat
    return out

# per-slot look (the tuned values from the scratch renders)
HERO_SLOTS = {
    #  slot:        (master, scalars, vectors)
    "Body":        ("M_HeroSkin", {"Saturation": 0.85, "Roughness": 0.55, "Specular": 0.45, "MetalMask": 0.0,
                                   "DetailStrength": 0.55, "DetailTiling": 24.0, "Mottle": 0.10, "MottleTiling": 3.0},
                    {"Tint": (0.8, 0.66, 0.57)}),
    "Pants":       ("M_HeroPBR",  {"Saturation": 0.75, "Roughness": 0.8, "Specular": 0.35, "BronzeAmount": 1.0, "MetalRoughness": 0.35},
                    {"Tint": (0.78, 0.7, 0.68)}),
    "Cross_strap": ("M_HeroPBR",  {"Saturation": 0.55, "Roughness": 0.75, "Specular": 0.35, "BronzeAmount": 1.0, "MetalRoughness": 0.35},
                    {"Tint": (0.52, 0.38, 0.27)}),
    "Leg_guard":   ("M_HeroPBR",  {"Roughness": 0.6, "BronzeAmount": 1.0, "ForceMetal": 1.0, "MetalRoughness": 0.45},
                    {"BronzeColor": (0.9, 0.6, 0.34)}),
    "Blanket":     ("M_HeroPBR",  {"Roughness": 0.92, "Specular": 0.3, "Saturation": 0.9, "MetalMask": 0.0}, {"Tint": (0.85, 0.72, 0.72)}),
    "Helmet":      ("M_HeroPBR",  {"Roughness": 0.7, "BronzeAmount": 1.0, "MetalRoughness": 0.32, "CrestGlow": 1.5},
                    {"BronzeColor": (0.9, 0.6, 0.34)}),
}

def build_hero_instances(masters, imported_dir, dest_dir, overrides=None):
    """MI_Vahagn_<slot> under dest_dir with the textures of the Interchange MICs in imported_dir/<slot>."""
    made = {}
    for slot, (master, scal, vecs) in HERO_SLOTS.items():
        src = unreal.load_asset("%s/%s" % (imported_dir, slot))
        if src is None:
            warn("imported MIC %s/%s missing" % (imported_dir, slot)); continue
        tex = {}
        for pn in MEL.get_texture_parameter_names(src.get_editor_property("parent") or src) if hasattr(MEL, "get_texture_parameter_names") else []:
            v = MEL.get_material_instance_texture_parameter_value(src, pn)
            if v is not None: tex[str(pn)] = v
        def pick(*keys):
            for k, v in tex.items():
                if any(s.lower() in k.lower() for s in keys): return v
            return None
        name = "MI_Vahagn_" + slot
        path = "%s/%s" % (dest_dir, name)
        mi = unreal.load_asset(path) if asset_on_disk(path) else ASSET_TOOLS.create_asset(name, dest_dir, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, masters[master])
        MEL.clear_all_material_instance_parameters(mi)
        for pn, keys in (("BaseTex", ("basecolor", "base_color", "diffuse")), ("NormalTex", ("normal",)), ("MRTex", ("metallicrough", "metallic_rough", "occlusionroughnessmetal", "roughness"))):
            t = pick(*keys)
            if t is not None and not t.get_name().startswith("T_White"): MEL.set_material_instance_texture_parameter_value(mi, pn, t)
        o = (overrides or {}).get(slot, {})
        for k, v in dict(scal, **o.get("s", {})).items(): MEL.set_material_instance_scalar_parameter_value(mi, k, float(v))
        for k, v in dict(vecs, **o.get("v", {})).items(): MEL.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
        MEL.update_material_instance(mi); save(mi); made[slot] = mi
        log("MI %s textures=%s" % (name, {k: v.get_name() for k, v in tex.items()}))
    return made

if __name__ == "__main__":
    MB = os.environ.get("TW_MATERIALS_BUILD", "/var/www/html/Twilight/Game/Tools/materials_build.py")
    _src_code = open(MB).read().rsplit("\nmain()", 1)[0]
    exec(compile(_src_code, MB, "exec"))                      # helpers only (G, setup_material, ...)
    ROOT = os.environ.get("HERO_MAT_ROOT", "/Game/Twilight/Materials")
    noise = load_first(TEX_NOISE, "noise")
    detail = import_detail_normal(os.environ.get("HERO_DETAIL_PNG", "/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto/hero/src/T_SkinDetail_N.png"), "/Game/Twilight/Hero/Textures")
    masters = build_hero_masters(noise, detail)
    imported = os.environ.get("HERO_IMPORTED", "/Game/Twilight/Hero/Mesh/spartan_vahagn/Materials")
    dest = os.environ.get("HERO_MAT_DIR", "/Game/Twilight/Hero/Materials")
    import json
    ov = json.loads(os.environ.get("HERO_MAT_OVERRIDES", "{}"))
    made = build_hero_instances(masters, imported, dest, ov)
    sk = unreal.load_asset(os.environ.get("HERO_MESH", "/Game/Twilight/Hero/Mesh/spartan_vahagn/SkeletalMeshes/spartan_vahagn"))
    if sk is not None and os.environ.get("HERO_ASSIGN", "1") == "1":
        new = []   # editing the returned structs in place does not stick: rebuild them
        for m in sk.get_editor_property("materials"):
            c = unreal.SkeletalMaterial()
            c.set_editor_property("material_interface", made.get(str(m.material_slot_name)) or m.material_interface)
            c.set_editor_property("material_slot_name", m.material_slot_name)
            new.append(c)
        sk.modify(); sk.set_editor_property("materials", new); save(sk)
        log("assigned %s" % [(str(m.material_slot_name), m.material_interface.get_name()) for m in sk.get_editor_property("materials")])
    unreal.log_warning("HERO materials done errors=%d %s" % (len(ERRORS), ERRORS))
