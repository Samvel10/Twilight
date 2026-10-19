"""Headless asset build for Twilight: materials, audio import, maps.
Run: UnrealEditor-Cmd TwilightAssets.uproject -run=pythonscript -script=Tools/build_assets.py
"""
import os, sys, glob, traceback
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))  # repo root (/var/www/html/Twilight)
sys.path.insert(0, HERE)
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ONLY = set(a for a in os.environ.get("TW_ONLY", "materials,audio,maps").split(",") if a)

def log(m): unreal.log("[TwilightBuild] " + m)

def build_materials():
    import materials_build  # runs main() on import

def import_audio():
    files = sorted(glob.glob(os.path.join(ROOT, "art", "audio", "sfx", "*.wav")) + glob.glob(os.path.join(ROOT, "art", "audio", "music", "*.wav")))
    tasks = []
    for f in files:
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", f)
        t.set_editor_property("destination_path", "/Game/Twilight/Audio")
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("save", True)
        tasks.append(t)
    TOOLS.import_asset_tasks(tasks)
    n = 0
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        path = "/Game/Twilight/Audio/" + name
        a = EAL.load_asset(path)
        if not a:
            unreal.log_error("[TwilightBuild] audio import failed: " + name)
            continue
        loop = name.endswith("_loop") or name.startswith("music_")
        a.set_editor_property("looping", loop)
        if name.startswith("music_"):
            try: a.set_editor_property("sound_group", unreal.SoundGroup.SOUNDGROUP_MUSIC)
            except Exception: pass
        EAL.save_asset(path, only_if_is_dirty=False)
        n += 1
    log("audio imported: %d / %d" % (n, len(files)))

def import_env():
    """External CC0/CC-BY assets: vishap model (glTF via Interchange), HDRI skies, PBR rock textures."""
    # --- dragon (skeletal mesh + Fly/Idle anims). One combined skeletal mesh, no Nanite.
    glb = os.path.join(ROOT, "art", "models", "vishap", "european_dragon.glb")
    dest = "/Game/Twilight/Vishap/Dragon"
    if os.path.exists(glb) and (os.environ.get("TW_DRAGON") or not EAL.does_asset_exist(dest + "/european_dragon")):
        mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
        src = unreal.InterchangeManager.create_source_data(glb)
        prm = unreal.ImportAssetParameters(); prm.is_automated = True
        pipe = unreal.InterchangeGenericAssetsPipeline()
        try: pipe.get_editor_property("mesh_pipeline").set_editor_property("build_nanite", False)
        except Exception as e: unreal.log_warning("[TwilightBuild] build_nanite: %s" % e)
        prm.override_pipelines.append(unreal.SoftObjectPath(pipe.get_path_name()))
        mgr.import_asset(dest, src, prm)
        reg = unreal.AssetRegistryHelpers.get_asset_registry()
        for a in reg.get_assets_by_path(dest, recursive=True):
            log("dragon asset %s %s" % (a.asset_class_path.asset_name, a.package_name))
            EAL.save_asset(str(a.package_name), only_if_is_dirty=False)
    # --- HDRI skies -> TextureCube
    tasks = []
    for f in sorted(glob.glob(os.path.join(ROOT, "art", "hdri", "*.hdr"))):
        t = unreal.AssetImportTask(); t.filename = f; t.destination_path = "/Game/Twilight/Env/HDRI"
        t.automated = True; t.replace_existing = True; t.save = True; tasks.append(t)
    # --- PBR rock (Poly Haven dark_rock, CC0): diff sRGB, GL normal (flip green), ARM masks
    for f in sorted(glob.glob(os.path.join(ROOT, "art", "textures", "*", "*.jpg")) + glob.glob(os.path.join(ROOT, "art", "textures", "*", "*.png"))):
        t = unreal.AssetImportTask(); t.filename = f; t.destination_path = "/Game/Twilight/Env/Textures"
        t.automated = True; t.replace_existing = True; t.save = True; tasks.append(t)
    # wing-membrane mask of the dragon (baked from its skin weights by Tools/wingmask_bake.py), next to the dragon
    wm = os.path.join(ROOT, "art", "models", "vishap", "T_DragonWingMask.png")
    if os.path.exists(wm):
        t = unreal.AssetImportTask(); t.filename = wm; t.destination_path = "/Game/Twilight/Vishap/Dragon"
        t.automated = True; t.replace_existing = True; t.save = True; tasks.append(t)
    TOOLS.import_asset_tasks(tasks)
    for t in tasks:
        for path in t.get_editor_property("imported_object_paths"):
            a = EAL.load_asset(path)
            if not a: continue
            n = a.get_name().lower()
            if isinstance(a, unreal.Texture2D):
                if "macronoise" in n:
                    a.set_editor_property("srgb", False)
                    a.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
                elif "wingmask" in n:
                    a.set_editor_property("srgb", False)
                    a.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
                elif "nor" in n or n.endswith("_n_1k"):
                    a.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
                    a.set_editor_property("srgb", False)
                    a.set_editor_property("flip_green_channel", "nor_gl" in n)  # T_OceanWaves_N is already DirectX
                elif "arm" in n:
                    a.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
                    a.set_editor_property("srgb", False)
            EAL.save_asset(path.split(".")[0], only_if_is_dirty=False)
            log("env import %s (%s)" % (path, a.get_class().get_name()))

def build_maps():
    for name in ["L_Vahagn", "L_Hayk", "L_Aralez", "L_Menu"]:
        path = "/Game/Twilight/Maps/" + name
        if EAL.does_asset_exist(path):
            log("map exists: " + path)
            continue
        world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
        ok = unreal.EditorLoadingAndSavingUtils.save_map(world, path)
        log("map %s saved=%s" % (path, ok))

steps = [("env", import_env), ("materials", build_materials), ("audio", import_audio), ("maps", build_maps)]
errors = 0
for key, fn in steps:
    if key not in ONLY: continue
    try:
        log("== " + key)
        fn()
    except Exception:
        errors += 1
        unreal.log_error("[TwilightBuild] step %s failed:\n%s" % (key, traceback.format_exc()))
log("=== done, errors=%d ===" % errors)
