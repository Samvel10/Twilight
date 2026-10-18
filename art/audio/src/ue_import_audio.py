"""
ue_import_audio.py - headless import of the generated WAVs into the Twilight UE 5.8 project.
It is NOT run by the generators. The main agent runs it when the editor is free:

  UnrealEditor-Cmd /var/www/html/Twilight/Game/Twilight.uproject \
      -run=pythonscript -script=/var/www/html/Twilight/art/audio/src/ue_import_audio.py

Result: /Game/Audio/SFX/<name> and /Game/Audio/Music/<name> SoundWave assets.
Loops (music_*, *_loop, sfx_fire_breath) get bLooping=True and ADPCM compression
(time-domain codec, no encoder priming gap, so loops stay seamless; music and loops stay small).

APIs checked against the UE 5.8 source on disk:
  UAssetImportTask props Filename/DestinationPath/DestinationName/bReplaceExisting/bAutomated/bSave
      Engine/Source/Editor/UnrealEd/Public/AssetImportTask.h:35-64, GetObjects() :81-82
  UAssetToolsHelpers::GetAssetTools()       Engine/Source/Developer/AssetTools/Public/IAssetTools.h:896-898
  IAssetTools::ImportAssetTasks (BlueprintCallable) IAssetTools.h:541-542
  USoundWave::bLooping (EditAnywhere)       Engine/Source/Runtime/Engine/Classes/Sound/SoundWave.h:449-451
  USoundWave::SetSoundAssetCompressionType  SoundWave.h:489-491 ; enum ESoundAssetCompressionType (BlueprintType) :347-349
  UEditorAssetLibrary::SaveAsset            Plugins/Editor/EditorScriptingUtilities/.../EditorAssetLibrary.h:281
Python names follow the PythonScriptPlugin rules: snake_case, and the leading 'b' is dropped from bools
(bLooping -> "looping", bReplaceExisting -> replace_existing). UNVERIFIED by execution: no editor was launched.
"""
import os
import unreal

ROOT = "/var/www/html/Twilight/art/audio"
LOOP_KEYS = ("music_", "_loop", "sfx_fire_breath")


def import_dir(sub, dest):
    folder = os.path.join(ROOT, sub)
    tasks = []
    for fn in sorted(os.listdir(folder)):
        if not fn.lower().endswith(".wav"):
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", os.path.join(folder, fn))
        t.set_editor_property("destination_path", dest)
        t.set_editor_property("destination_name", os.path.splitext(fn)[0])
        t.set_editor_property("replace_existing", True)
        t.set_editor_property("automated", True)
        t.set_editor_property("save", False)
        tasks.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for t in tasks:
        for obj in t.get_objects():
            if not isinstance(obj, unreal.SoundWave):
                continue
            name = obj.get_name()
            if any(k in name for k in LOOP_KEYS):
                obj.set_editor_property("looping", True)
                obj.set_sound_asset_compression_type(unreal.SoundAssetCompressionType.ADPCM)
            path = obj.get_path_name().split(".")[0]
            unreal.EditorAssetLibrary.save_asset(path, False)
            unreal.log(f"[audio import] {path} looping={obj.get_editor_property('looping')}")


import_dir("sfx", "/Game/Audio/SFX")
import_dir("music", "/Game/Audio/Music")
