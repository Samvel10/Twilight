"""Generate skeletal LODs with the SkeletalReduction plugin (engine-built, enabled in the .uproject).
env HUM_LOD_CHARS (comma list of Char names), HUM_LOD_PCT (e.g. '0.5,0.2,0.07'), HUM_LOD_SS (screen sizes, e.g. '0.6,0.3,0.12')"""
import unreal, os
def log(m): unreal.log_warning('HUM '+str(m))
EAL=unreal.EditorAssetLibrary; AT=unreal.AssetToolsHelpers.get_asset_tools()
chars=[c for c in os.environ.get('HUM_LOD_CHARS','Armsold,Babsold').split(',') if c]
pct=[float(x) for x in os.environ.get('HUM_LOD_PCT','0.5,0.2,0.07').split(',')]
ss=[float(x) for x in os.environ.get('HUM_LOD_SS','0.5,0.25,0.1').split(',')]
SMS=unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
for C in chars:
    n=C.lower(); path='/Game/Twilight/Humans/%s/Mesh/%s/SkeletalMeshes/%s'%(C,n,n)
    sk=unreal.load_asset(path)
    lsp='/Game/Twilight/Humans/%s/Mesh/LODS_%s'%(C,C)
    fac=unreal.DataAssetFactory(); fac.set_editor_property('data_asset_class',unreal.SkeletalMeshLODSettings)
    ls=unreal.load_asset(lsp) if EAL.does_asset_exist(lsp) else AT.create_asset('LODS_'+C, '/Game/Twilight/Humans/%s/Mesh'%C, unreal.SkeletalMeshLODSettings, fac)
    groups=[]
    for i,(p,s) in enumerate([(1.0,1.0)]+list(zip(pct,ss))):
        g=unreal.SkeletalMeshLODGroupSettings()
        g.set_editor_property('screen_size',unreal.PerPlatformFloat(default=s))
        r=g.get_editor_property('reduction_settings')
        r.set_editor_property('num_of_triangles_percentage',p)
        try: r.set_editor_property('termination_criterion',unreal.SkeletalMeshTerminationCriterion.SMTC_NUM_OF_TRIANGLES)
        except Exception as e: log('tc %s'%e)
        try: r.set_editor_property('max_bones_per_vertex', 4 if i<2 else 2)
        except Exception as e: pass
        g.set_editor_property('reduction_settings',r)
        groups.append(g)
    ls.set_editor_property('lod_groups',groups); EAL.save_loaded_asset(ls)
    sk.set_editor_property('lod_settings',ls)
    ok=SMS.regenerate_lod(sk, len(groups), True, False) if hasattr(SMS,'regenerate_lod') else unreal.SkeletalMeshEditorSubsystem.regenerate_lod(sk,len(groups),True,False)
    n_lod=sk.get_lod_num() if hasattr(sk,'get_lod_num') else SMS.get_lod_count(sk)
    tris=[]
    for l in range(n_lod):
        try: tris.append(SMS.get_num_verts(sk,l))
        except Exception: pass
    EAL.save_loaded_asset(sk)
    log('%s regen=%s lods=%s verts=%s'%(C,ok,n_lod,tris))
