"""Vahagn hero: import the cleaned Spartan GLB (CC-BY Andywoodhead) and retarget the Manny animations onto it.
Run: UnrealEditor-Cmd <proj>.uproject -run=pythonscript -script=ue_hero_build.py
Creates (DEST=/Game/Twilight/Hero by default, overridable by env HERO_DEST):
  DEST/Mesh/SK_Vahagn (+ Skeleton, PhysicsAsset, textures, material instances)
  DEST/Rig/IK_Manny, DEST/Rig/IK_Vahagn, DEST/Rig/RTG_Manny_to_Vahagn
  DEST/Anims/<MM_* same names>  (AnimSequences on the SK_Vahagn skeleton)"""
import unreal, os
GLB=os.environ.get('HERO_GLB','/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto/hero/src/spartan_vahagn.glb')
DEST=os.environ.get('HERO_DEST','/Game/Twilight/Hero')
MANNY='/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
A='/Game/Characters/Mannequins/Anims/'
ANIMS=[A+'Unarmed/MM_Idle', A+'Unarmed/Jump/MM_Fall_Loop', A+'Unarmed/Attack/MM_Attack_01', A+'Unarmed/Attack/MM_Attack_02',
       A+'Unarmed/Attack/MM_ChargedAttack', A+'Rifle/HitReact/MM_HitReact_Front_Lgt_01', A+'Death/MM_Death_Front_01']
def log(m): unreal.log_warning('HERO '+str(m))
AT=unreal.AssetToolsHelpers.get_asset_tools(); EAL=unreal.EditorAssetLibrary
reg=unreal.AssetRegistryHelpers.get_asset_registry()
for d in (DEST+'/Anims', DEST+'/Rig'):          # rebuild from scratch (rigs/retargeter reference each other)
    if EAL.does_directory_exist(d): EAL.delete_directory(d)

# ---------------------------------------------------------------- 1. import (Interchange, no Nanite, no anims)
def import_glb(path, dest):
    if EAL.does_directory_exist(dest): EAL.delete_directory(dest)
    pp=DEST+'/Pipelines/GLTF_Hero'
    p=unreal.load_asset(pp) if EAL.does_asset_exist(pp) else EAL.duplicate_loaded_asset(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFAssetsPipeline'),pp)
    mp=p.get_editor_property('mesh_pipeline')
    mp.set_editor_property('build_nanite',False)
    mp.set_editor_property('import_static_meshes',False)
    ap=p.get_editor_property('animation_pipeline'); ap.set_editor_property('import_animations',False)
    ov=unreal.InterchangePipelineStackOverride(); ov.add_pipeline(p); ov.add_pipeline(unreal.load_asset('/Interchange/Pipelines/DefaultGLTFPipeline'))
    t=unreal.AssetImportTask(); t.filename=path; t.destination_path=dest
    t.automated=True; t.replace_existing=True; t.save=True; t.options=ov
    AT.import_asset_tasks([t])
    sk=None
    for a in reg.get_assets_by_path(dest,recursive=True):
        c=str(a.asset_class_path.asset_name)
        if c=='SkeletalMesh': sk=a.get_asset()
        if c=='MaterialInstanceConstant' and str(a.asset_name) in ('Shield','Sword'): EAL.delete_asset(str(a.package_name)); continue
        if c not in ('Texture2D',): log('asset %s %s'%(c,a.package_name))
    return sk
sk=import_glb(GLB, DEST+'/Mesh')
log('mesh %s bones=%d mats=%s'%(sk.get_path_name(), len(sk.get_editor_property('skeleton').get_editor_property('bone_tree')) if sk else -1, [m.material_slot_name for m in sk.materials] if sk else None))

# ---------------------------------------------------------------- 2. IK rigs (auto retarget chains + auto FBIK)
def make_rig(name, mesh):
    pkg=DEST+'/Rig'
    if EAL.does_asset_exist(pkg+'/'+name): EAL.delete_asset(pkg+'/'+name)
    rig=AT.create_asset(name, pkg, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c=unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    ok1=c.apply_auto_generated_retarget_definition(); ok2=c.apply_auto_fbik()
    log('rig %s auto_chains=%s fbik=%s root=%s chains=%s'%(name,ok1,ok2,c.get_retarget_root(),[(str(ch.chain_name),str(c.get_retarget_chain_start_bone(ch.chain_name)),str(c.get_retarget_chain_end_bone(ch.chain_name))) for ch in c.get_retarget_chains()]))
    EAL.save_loaded_asset(rig); return rig
manny=unreal.load_asset(MANNY)
rig_src=make_rig('IK_Manny', manny)
rig_tgt=make_rig('IK_Vahagn', sk)

# ---------------------------------------------------------------- 3. retargeter
name='RTG_Manny_to_Vahagn'; pkg=DEST+'/Rig'
if EAL.does_asset_exist(pkg+'/'+name): EAL.delete_asset(pkg+'/'+name)
rtg=AT.create_asset(name, pkg, unreal.IKRetargeter, unreal.IKRetargetFactory())
rc=unreal.IKRetargeterController.get_controller(rtg)
S,T=unreal.RetargetSourceOrTarget.SOURCE, unreal.RetargetSourceOrTarget.TARGET
rc.set_ik_rig(S, rig_src); rc.set_ik_rig(T, rig_tgt)
rc.set_preview_mesh(S, manny); rc.set_preview_mesh(T, sk)
rc.remove_all_ops(); rc.add_default_ops(); rc.assign_ik_rig_to_all_ops(S, rig_src); rc.assign_ik_rig_to_all_ops(T, rig_tgt)
rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
rc.auto_align_all_bones(T)   # match the target's arms/legs to Manny's ref pose (A-pose vs A-pose; fixes residual differences)
log('ops=%s'%[rc.get_op_name(i) for i in range(rc.get_num_retarget_ops())])
EAL.save_loaded_asset(rtg)

# ---------------------------------------------------------------- 4. batch retarget
ads=[reg.get_asset_by_object_path(p+'.'+p.split('/')[-1]) for p in ANIMS]
ads=[a for a in ads if a.is_valid()]
out=unreal.IKRetargetBatchOperation.duplicate_and_retarget(ads, manny, sk, rtg, target_path=DEST+'/Anims', include_referenced_assets=False, overwrite_existing_files=True)
for a in out: log('anim %s'%a.package_name)
EAL.save_directory(DEST)
log('DONE')
