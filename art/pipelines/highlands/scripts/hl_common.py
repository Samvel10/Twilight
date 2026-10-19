# Shared helpers for the highlands scratch project (editor Python).
import unreal, os, glob, json, traceback
P = '/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/highlands/'
SITE = os.environ.get('HL_SITE', '')                  # '' = Geghama/Sevan (default), 'van' = Lake Van east shore (Hayk)
GEN = P + ('gen_%s/' % SITE if SITE else 'gen/')
TROOT = '/Game/Terrain' + ('_' + SITE if SITE else '')  # content root for tiles/maps/water of this site
SFX = ('_' + SITE) if SITE else ''                      # suffix for site-specific MIs / level
LEVEL = '/Game/Test/L_' + ({'van': 'Van', 'ararat': 'Ararat'}.get(SITE, 'Highlands'))
VEGGEN = P + 'gen/'                                      # vegetation glTFs are shared by all sites
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
SMS = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)


def log(m):
    unreal.log_warning('HL ' + str(m))


def import_textures(files, dest, kind=None):
    """kind: None = auto by name; 'normal' / 'mask' / 'color' / 'hdr'"""
    tasks = []
    for f in files:
        t = unreal.AssetImportTask(); t.filename = f; t.destination_path = dest
        t.automated = True; t.replace_existing = True; t.save = True; tasks.append(t)
    AT.import_asset_tasks(tasks)
    out = []
    for t in tasks:
        for path in t.get_editor_property('imported_object_paths'):
            a = EAL.load_asset(path)
            out.append(a)
            if not isinstance(a, unreal.Texture2D):
                continue
            n = a.get_name().lower()
            k = kind
            if k is None:
                k = 'normal' if ('_nor' in n or n.endswith('_n')) else ('mask' if ('arm' in n or 'mask' in n or 'light' in n or 'noise' in n or 'alpha' in n or 'canopy' in n or 'black' in n) else 'color')
            if k == 'normal':
                a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
                a.set_editor_property('srgb', False)
                a.set_editor_property('flip_green_channel', 'nor_gl' in n)
            elif k == 'mask':
                a.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
                a.set_editor_property('srgb', False)
            if n.startswith('t_core') or n.startswith('t_mid') or n.startswith('t_far'):
                a.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
                a.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
                a.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD)
                a.set_editor_property('never_stream', True)
            EAL.save_asset(path.split('.')[0], only_if_is_dirty=False)
            log('tex %s %s' % (path, k))
    return out


def gltf_pipeline(name='/Game/Pipelines/GLTF_NoNanite', materials=False):
    src = unreal.load_asset('/Interchange/Pipelines/DefaultGLTFAssetsPipeline')
    p = EAL.load_asset(name) if EAL.does_asset_exist(name) else EAL.duplicate_loaded_asset(src, name)
    mp = p.get_editor_property('mesh_pipeline')
    mp.set_editor_property('build_nanite', False)
    try:
        mp.set_editor_property('combine_static_meshes', False)
    except Exception as e:
        log('combine: %s' % e)
    try:
        p.get_editor_property('material_pipeline').set_editor_property('import_materials', materials)
    except Exception as e:
        log('material_pipeline: %s' % e)
    EAL.save_loaded_asset(p, False)
    ov = unreal.InterchangePipelineStackOverride()
    ov.add_pipeline(p)
    ov.add_pipeline(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFPipeline'))
    return ov


def import_gltf(ov, f, dest):
    t = unreal.AssetImportTask(); t.filename = f; t.destination_path = dest
    t.automated = True; t.replace_existing = True; t.save = True; t.options = ov
    AT.import_asset_tasks([t])
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    out = []
    for a in reg.get_assets_by_path(dest, recursive=True):
        if str(a.asset_class_path.asset_name) == 'StaticMesh':
            out.append(a.get_asset())
    return out


def report(sm):
    b = sm.get_bounding_box()
    tris = [sm.get_num_triangles(i) for i in range(sm.get_num_lods())]
    log('MESH %s lods=%d tris=%s bbox_min=%s bbox_max=%s' % (sm.get_path_name(), sm.get_num_lods(), tris, b.min, b.max))
