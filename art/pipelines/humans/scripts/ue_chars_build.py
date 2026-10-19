"""Import the baked character GLBs (Interchange, Nanite off) and retarget the UE5 Manny clips onto each of them.
env: CHARS_SRC (dir with <name>.glb), CHARS (comma list, default all *.glb), CHARS_DEST (default /Game/Twilight/Humans)
Creates per char: DEST/<Name>/Mesh/... SkeletalMesh, DEST/<Name>/Rig/IK_<Name>, RTG_Manny_to_<Name>, DEST/<Name>/Anims/<clip>
Shared: DEST/Rig/IK_Manny."""
import unreal, os, glob
SRC=os.environ.get('CHARS_SRC','/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto2/humans/src')
DEST=os.environ.get('CHARS_DEST','/Game/Twilight/Humans')
names=[n for n in os.environ.get('CHARS','').split(',') if n] or [os.path.basename(f)[:-4] for f in sorted(glob.glob(SRC+'/*.glb'))]
MANNY='/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
A='/Game/Characters/Mannequins/Anims/'
CLIPS=os.environ.get('CHARS_CLIPS', 'Unarmed/MM_Idle,Unarmed/Walk/MF_Unarmed_Walk_Fwd,Unarmed/Jog/MF_Unarmed_Jog_Fwd,Rifle/MF_Rifle_Idle_ADS,Rifle/MM_Rifle_Fire,'
  'Rifle/AIM/MM_Rifle_Idle_ADS_AO_CU,Rifle/Walk/MF_Rifle_Walk_Fwd,Unarmed/Attack/MM_Attack_01,Unarmed/Attack/MM_Attack_02,Unarmed/Attack/MM_ChargedAttack,'
  'Rifle/HitReact/MM_HitReact_Front_Hvy_01,Death/MM_Death_Front_01,Death/MM_Death_Back_01,Death/MM_Death_Left_01,Unarmed/Jump/MM_Land').split(',')
def log(m): unreal.log_warning('HUM '+str(m))
AT=unreal.AssetToolsHelpers.get_asset_tools(); EAL=unreal.EditorAssetLibrary
reg=unreal.AssetRegistryHelpers.get_asset_registry()

def pipeline():
    pp=DEST+'/Pipelines/GLTF_Chars'
    p=unreal.load_asset(pp) if EAL.does_asset_exist(pp) else EAL.duplicate_loaded_asset(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFAssetsPipeline'),pp)
    mp=p.get_editor_property('mesh_pipeline')
    mp.set_editor_property('build_nanite',False); mp.set_editor_property('import_static_meshes',False)
    p.get_editor_property('animation_pipeline').set_editor_property('import_animations',False)
    EAL.save_loaded_asset(p); return p
def import_glb(path, dest, p):
    if EAL.does_directory_exist(dest): EAL.delete_directory(dest)
    ov=unreal.InterchangePipelineStackOverride(); ov.add_pipeline(p); ov.add_pipeline(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFPipeline'))
    t=unreal.AssetImportTask(); t.filename=path; t.destination_path=dest
    t.automated=True; t.replace_existing=True; t.save=True; t.options=ov
    AT.import_asset_tasks([t])
    for a in reg.get_assets_by_path(dest,recursive=True):
        if str(a.asset_class_path.asset_name)=='SkeletalMesh': return a.get_asset()
def make_rig(name, pkg, mesh):
    if EAL.does_asset_exist(pkg+'/'+name): EAL.delete_asset(pkg+'/'+name)
    rig=AT.create_asset(name, pkg, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c=unreal.IKRigController.get_controller(rig); c.set_skeletal_mesh(mesh)
    ok1=c.apply_auto_generated_retarget_definition(); ok2=c.apply_auto_fbik()
    log('rig %s chains=%s fbik=%s n=%d'%(name,ok1,ok2,len(c.get_retarget_chains())))
    EAL.save_loaded_asset(rig); return rig

p=pipeline(); manny=unreal.load_asset(MANNY)
rig_src=unreal.load_asset(DEST+'/Rig/IK_Manny') if (EAL.does_asset_exist(DEST+'/Rig/IK_Manny') and not os.environ.get('CHARS_REBUILD_MANNY')) else make_rig('IK_Manny', DEST+'/Rig', manny)
ads=[reg.get_asset_by_object_path(A+c+'.'+c.split('/')[-1]) for c in CLIPS]
miss=[c for c,a in zip(CLIPS,ads) if not a.is_valid()]; log('missing clips %s'%miss)
ads=[a for a in ads if a.is_valid()]
for n in names:
    N=n[0].upper()+n[1:]; base=DEST+'/'+N
    for d in (base+'/Anims', base+'/Rig'):
        if EAL.does_directory_exist(d): EAL.delete_directory(d)
    sk=import_glb(SRC+'/'+n+'.glb', base+'/Mesh', p)
    if not sk: log('IMPORT FAILED %s'%n); continue
    log('mesh %s mats=%s'%(sk.get_path_name(),[str(m.material_slot_name) for m in sk.materials]))
    tgt=make_rig('IK_'+N, base+'/Rig', sk)
    rn='RTG_Manny_to_'+N
    rtg=AT.create_asset(rn, base+'/Rig', unreal.IKRetargeter, unreal.IKRetargetFactory())
    rc=unreal.IKRetargeterController.get_controller(rtg)
    S,T=unreal.RetargetSourceOrTarget.SOURCE, unreal.RetargetSourceOrTarget.TARGET
    rc.set_ik_rig(S, rig_src); rc.set_ik_rig(T, tgt); rc.set_preview_mesh(S, manny); rc.set_preview_mesh(T, sk)
    rc.remove_all_ops(); rc.add_default_ops(); rc.assign_ik_rig_to_all_ops(S, rig_src); rc.assign_ik_rig_to_all_ops(T, tgt)
    rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True); rc.auto_align_all_bones(T)
    EAL.save_loaded_asset(rtg)
    out=unreal.IKRetargetBatchOperation.duplicate_and_retarget(ads, manny, sk, rtg, target_path=base+'/Anims', include_referenced_assets=False, overwrite_existing_files=True)
    log('%s anims=%d'%(N,len(out)))
    EAL.save_directory(base)
log('DONE')
