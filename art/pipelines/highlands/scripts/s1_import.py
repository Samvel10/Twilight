# s1_import.py - import terrain tiles (own LOD chain merged into one StaticMesh per tile), region maps, layer textures, HDRI.
# Run (editor, no UI):  UnrealEditor-Cmd Highlands.uproject -ExecutePythonScript=<this> -unattended -nop4 -nosplash -nosound -nullrhi
# env HL_ONLY=tex,hdri,terrain,water (default all)
import sys, os, glob, json, traceback
sys.path.insert(0, '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands/scripts')
import unreal
from hl_common import *

ONLY = os.environ.get('HL_ONLY', 'tex,hdri,terrain,water')
# LOD switch screen sizes (UE: 2*0.89*R/D at 90 deg FOV 16:9). Per LOD k spacing s_k must stay under ~12 px per quad:
# switch distance D_k = 85 * s_k. core: 3.2/6.4/12.8 km, mid 17/34 km, far 68/136 km -> the same ratios for every region.
LOD_SS = {'core': [8.0, 1.15, 0.58, 0.29], 'mid': [8.0, 1.1, 0.55], 'far': [8.0, 1.1, 0.55]}


def build_settings(sm, nlod):
    for i in range(nlod):
        bs = SMS.get_lod_build_settings(sm, i)
        bs.set_editor_property('recompute_normals', False)
        bs.set_editor_property('recompute_tangents', True)
        bs.set_editor_property('generate_lightmap_u_vs', False)
        bs.set_editor_property('use_full_precision_u_vs', True)
        try:
            bs.set_editor_property('generate_distance_field_as_if_two_sided', False)
        except Exception:
            pass
        SMS.set_lod_build_settings(sm, i, bs)


def import_terrain(ov, region):
    lay = json.load(open(GEN + 'mesh/%s_layout.json' % region))
    for t in lay['tiles']:
        name = t['name']
        dest = TROOT + '/%s/%s' % (region, name)
        f = GEN + 'mesh/%s/%s.gltf' % (region, name)
        meshes = import_gltf(ov, f, dest + '/tmp')
        by = {m.get_name().split('_L')[-1]: m for m in meshes}
        base = by.get('0')
        if base is None:
            log('ERR no L0 for %s: %s' % (name, [m.get_name() for m in meshes]))
            continue
        # move L0 to the final asset name, then append the coarser LODs from the other imported meshes
        final = dest + '/SM_' + name
        if EAL.does_asset_exist(final):
            EAL.delete_asset(final)
        EAL.rename_asset(base.get_path_name().split('.')[0], final)
        base = unreal.load_asset(final)
        k = 1
        while str(k) in by:
            SMS.set_lod_from_static_mesh(base, k, by[str(k)], 0, True)
            k += 1
        build_settings(base, k)
        SMS.set_lod_screen_sizes(base, LOD_SS[region][:k])
        base.set_editor_property('light_map_resolution', 4)
        try:
            base.get_editor_property('body_setup').set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        except Exception as e:
            pass
        EAL.save_loaded_asset(base, False)
        EAL.delete_directory(dest + '/tmp')
        report(base)


try:
    if 'tex' in ONLY:
        import_textures(sorted(glob.glob(GEN + 'tex/T_*.png')), TROOT + '/Maps')
        if not SITE:
            import_textures(sorted(glob.glob(P + 'dl/tex/*.jpg')), '/Game/Env/Layers')
            import_textures([P + 'dl/T_MacroNoise.png'], '/Game/Env/Layers', 'mask')
    if 'hdri' in ONLY:
        import_textures([P + 'dl/hdri/kloppenheim_06_puresky_4k.hdr'], '/Game/Env/HDRI')
    if 'terrain' in ONLY or 'water' in ONLY:
        ov = gltf_pipeline()
        for r in os.environ.get('HL_REGIONS', 'core,mid,far').split(','):
            if 'terrain' in ONLY:
                import_terrain(ov, r)
        if 'water' in ONLY:
            for f in sorted(glob.glob(GEN + 'mesh/water/*.gltf')):
                n = os.path.basename(f)[:-5]
                for sm in import_gltf(ov, f, TROOT + '/Water/' + n):
                    build_settings(sm, 1); EAL.save_loaded_asset(sm, False); report(sm)
except Exception:
    unreal.log_error('HL s1 failed\n' + traceback.format_exc())
log('S1 DONE')
unreal.SystemLibrary.quit_editor()
