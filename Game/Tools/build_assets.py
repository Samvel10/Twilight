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

def build_maps():
    for name in ["L_Vahagn", "L_Hayk", "L_Aralez", "L_Menu"]:
        path = "/Game/Twilight/Maps/" + name
        if EAL.does_asset_exist(path):
            log("map exists: " + path)
            continue
        world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
        ok = unreal.EditorLoadingAndSavingUtils.save_map(world, path)
        log("map %s saved=%s" % (path, ok))

steps = [("materials", build_materials), ("audio", import_audio), ("maps", build_maps)]
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
