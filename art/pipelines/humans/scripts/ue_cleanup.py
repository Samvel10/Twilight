import unreal
for d in ('/Game/Twilight/Humans/Ara2','/Game/Twilight/Humans/Ara3','/Game/Twilight/Humans/Ara','/Game/Twilight/Humans/Hayk','/Game/Proto/L_Por_ara2','/Game/Proto/L_Por_ara3'):
    if unreal.EditorAssetLibrary.does_directory_exist(d): unreal.EditorAssetLibrary.delete_directory(d); unreal.log_warning('HUM deleted '+d)
    elif unreal.EditorAssetLibrary.does_asset_exist(d): unreal.EditorAssetLibrary.delete_asset(d); unreal.log_warning('HUM deleted '+d)
