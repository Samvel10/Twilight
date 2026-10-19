"""per-slot look-dev parameters for M_Human (shared by ue_materials.py and glb_crowd.py; no unreal import)"""
SKIN = {"s": {"Saturation": 0.72, "Roughness": 0.62, "Specular": 0.38, "MetalMask": 0.0, "DetailStrength": 0.5, "DetailTiling": 24.0,
              "Mottle": 0.10, "MottleTiling": 3.0, "ToneVar": 0.35}, "v": {"Tint": (0.86, 0.76, 0.68)}}
def S(base, **kw):   # merge helper
    d = {"s": dict(base.get("s", {})), "v": dict(base.get("v", {}))}
    for k, v in kw.items(): (d["v"] if isinstance(v, (tuple, list)) else d["s"])[k] = v
    return d
CLOTH = {"s": {"MetalMask": 0.0, "Roughness": 0.9, "Specular": 0.3, "Saturation": 0.8, "DirtAmount": 0.25, "DustAmount": 0.55, "DustHeight": 50.0}}
LEATHER = {"s": {"MetalMask": 0.0, "Roughness": 0.7, "Specular": 0.35, "Saturation": 0.7, "DirtAmount": 0.25, "DustAmount": 0.5}}
IRON = {"s": {"ForceMetal": 1.0, "MetalRoughness": 0.42, "MetalTintAmount": 0.6, "Saturation": 0.6, "DirtAmount": 0.35, "Brightness": 0.85},
        "v": {"MetalTint": (0.62, 0.6, 0.58)}}
BRONZE = {"s": {"ForceMetal": 1.0, "MetalRoughness": 0.38, "MetalTintAmount": 1.0, "DirtAmount": 0.2, "Brightness": 0.8}, "v": {"MetalTint": (0.78, 0.48, 0.22)}}
GOLD = {"s": {"ForceMetal": 1.0, "MetalRoughness": 0.28, "MetalTintAmount": 1.0, "DirtAmount": 0.1, "Brightness": 1.1}, "v": {"MetalTint": (1.0, 0.75, 0.38)}}
WOAD_OFF = {"Recolor1Src": (0.25, 0.4, 0.9), "Recolor1Dst": (0.265, 0.14, 0.09), "Recolor1Amount": 1.0, "Recolor1Width": 0.25, "Recolor1KeepLum": 0.25, "Recolor1Sens": 6000.0}
MADDER = (0.55, 0.09, 0.06)          # Armenian red ("vordan karmir") dye
LAPIS = (0.09, 0.17, 0.48)           # Babylon: glazed-brick blue

SPEC = {
 "Ara": {   # Celt base: woad removed, madder-red trousers, gold torc + circlet crown
   "Body":  S(SKIN, **WOAD_OFF, Tint=(0.86, 0.72, 0.62)),
   "Head":  S(SKIN, **WOAD_OFF, Tint=(0.86, 0.72, 0.62)),
   "Hands": S(SKIN, **WOAD_OFF, Tint=(0.86, 0.72, 0.62)),
   "Belt":  S(LEATHER, MetalMask=1.0, MetalRoughness=0.3, MetalTintAmount=1.0, MetalTint=(0.95, 0.7, 0.35)),
   "Legs":  S(CLOTH, Recolor1Src=(0.3, 0.9, 0.1), Recolor1Dst=(0.75, 0.6, 0.38), Recolor1Amount=1.0, Recolor1Width=0.5,
              Recolor2Src=(0.6, 0.1, 0.8), Recolor2Dst=MADDER, Recolor2Amount=1.0, Recolor2Width=0.5, Saturation=0.85, Brightness=0.85, DustAmount=0.3),
   "Crown": S(GOLD),
 },
 "Bel": {
   "Full_figure_42_T_pose_02": S(SKIN, MetalMask=0.0, ForceMetal=0.0),
   "Ties": S(LEATHER), "Dangles": S(LEATHER, MetalMask=0.0, Brightness=0.9),
   "Armour_top": S(GOLD, DirtAmount=0.15), "Helmet3": S(GOLD),
   "Tunic_1": S(CLOTH, Recolor1Src=(0.8, 0.1, 0.1), Recolor1Dst=(0.22, 0.05, 0.16), Recolor1Amount=1.0, Saturation=0.9, DustAmount=0.3),
   "New_eye": {"s": {"MetalMask": 0.0, "Roughness": 0.2, "Specular": 0.6}}, "New_eye_2": {"s": {"MetalMask": 0.0, "Roughness": 0.2, "Specular": 0.6}},
   "New_arms": S(SKIN), "New_legs": S(SKIN, DustAmount=0.5, DustHeight=40.0), "New_head": S(SKIN),
   "Boots": S(LEATHER), "Wrist_guard1": S(LEATHER, Tint=(0.8, 0.6, 0.4)),
 },
 "Babsold": {
   "Full_figure_42_T_pose_02": S(SKIN, MetalMask=0.0, ForceMetal=0.0),
   "Ties": S(LEATHER), "Dangles": S(LEATHER, MetalMask=0.0),
   "Armour_top": S(BRONZE, DirtAmount=0.45, MetalRoughness=0.5, Brightness=0.8), "Helmet3": S(BRONZE, DirtAmount=0.35, MetalRoughness=0.45),
   "Tunic_1": S(CLOTH, Recolor1Src=(0.8, 0.1, 0.1), Recolor1Dst=LAPIS, Recolor1Amount=1.0, TintVar=1.0, TintAlt=(0.8, 0.75, 0.6)),
   "New_eye": {"s": {"MetalMask": 0.0, "Roughness": 0.2, "Specular": 0.6}}, "New_eye_2": {"s": {"MetalMask": 0.0, "Roughness": 0.2, "Specular": 0.6}},
   "New_arms": S(SKIN), "New_legs": S(SKIN, DustAmount=0.6, DustHeight=40.0), "New_head": S(SKIN),
   "Boots": S(LEATHER), "Wrist_guard1": S(LEATHER),
   "Scutum_04_01": S(LEATHER, Recolor1Src=(0.9, 0.1, 0.05), Recolor1Dst=LAPIS, Recolor1Amount=1.0, Recolor2Src=(0.9, 0.8, 0.1), Recolor2Dst=(0.85, 0.6, 0.25),
                     Recolor2Amount=1.0, MetalMask=1.0, MetalTintAmount=1.0, MetalTint=(0.9, 0.62, 0.32), Roughness=0.75, DirtAmount=0.45),
 },
 "Hayk": {   # Spartan base without helmet: bearded giant, dark leather, madder cloak
   "Body": S(SKIN, Tint=(0.84, 0.72, 0.62)),
   "Pants": S(CLOTH, Recolor1Src=(0.8, 0.1, 0.1), Recolor1Dst=(0.30, 0.20, 0.12), Recolor1Amount=1.0, Saturation=0.8, MetalMask=1.0, MetalTintAmount=1.0, MetalTint=(0.78, 0.48, 0.22), MetalRoughness=0.4, DustAmount=0.35),
   "Cross_strap": S(LEATHER, Tint=(0.55, 0.4, 0.28), MetalMask=1.0, MetalTintAmount=1.0, MetalTint=(1.0, 0.75, 0.38)),
   "Leg_guard": S(BRONZE, DirtAmount=0.3),
   "Blanket": S(CLOTH, Recolor1Src=(0.8, 0.1, 0.1), Recolor1Dst=MADDER, Recolor1Amount=1.0, Saturation=1.0, DustAmount=0.0, DirtAmount=0.1),
 },
 "Shamiram": {   # Alethea (Mu.Mu1) skinned onto the UE5 mannequin: Assyrian crimson + gold
   "Armor1": S(GOLD, DirtAmount=0.05, MetalRoughness=0.3),
   "Vay1": S(CLOTH, Recolor1Src=(0.1, 0.7, 0.8), Recolor1Dst=(0.10, 0.006, 0.012), Recolor1Amount=1.0, Recolor1Width=0.3, Recolor1KeepLum=0.0, Recolor1Sens=2000.0, Saturation=1.0, Brightness=1.0,
             Roughness=0.55, Specular=0.45, DirtAmount=0.0, DustAmount=0.0),
   "Hair": {"s": {"MetalMask": 0.0, "Roughness": 0.45, "Specular": 0.4, "Brightness": 0.8}},
   "Day_chuyen": S(GOLD),
   "Body": S(SKIN, Tint=(0.88, 0.76, 0.66), MetalMask=0.0, DetailStrength=0.3),
   "Head": S(SKIN, Tint=(0.88, 0.76, 0.66), MetalMask=0.0, DetailStrength=0.25),
   "Eyes": {"s": {"MetalMask": 0.0, "Roughness": 0.15, "Specular": 0.6}},
   "lambert2": {"s": {"MetalMask": 0.0, "Roughness": 0.45, "Specular": 0.4, "Brightness": 0.8}},
 },
 "Armsold": {
   "Saxon_54": S(SKIN, MetalMask=0.0),
   "Shield_13": S(LEATHER, Recolor1Src=(0.9, 0.1, 0.05), Recolor1Dst=MADDER, Recolor1Amount=1.0, Recolor2Src=(0.9, 0.8, 0.1), Recolor2Dst=(0.75, 0.55, 0.3),
                  Recolor2Amount=1.0, MetalMask=1.0, MetalTintAmount=0.8, MetalTint=(0.9, 0.62, 0.32), DirtAmount=0.45),
   "Tunic_4": S(CLOTH, Recolor1Src=(0.2, 0.6, 0.1), Recolor1Dst=MADDER, Recolor1Amount=1.0, Recolor1Width=0.4, Brightness=0.75, TintVar=1.0, TintAlt=(0.75, 0.55, 0.45)),
   "Belt_2": S(LEATHER), "Sleeves_3": S(CLOTH, Tint=(0.85, 0.78, 0.66)),
   "Helmet_Norman": S(BRONZE, ForceMetal=1.0, MetalRoughness=0.45, DirtAmount=0.4, Saturation=0.7, TintVar=0.0),
 },
}


# crowd variants (glb_crowd.py): look-dev already baked into the atlas -> neutral grading, only dirt/dust/variation live
CROWD = {"s": {"MetalMask": 1.0, "Roughness": 1.0, "MetalRoughness": 0.42, "Specular": 0.4, "DirtAmount": 0.12, "DustAmount": 0.45,
               "DustHeight": 45.0, "ToneVar": 0.25, "Saturation": 1.0}}
SPEC["Armsoldc"] = {"Crowd": CROWD}
SPEC["Babsoldc"] = {"Crowd": CROWD}
