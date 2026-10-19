"""UE 5.8 editor python (run_ue.sh ue_build.py): imports the procedural textures + fire-hair mesh and builds
   M_FH_FireStrand (+MI_FH_FireStrand, MI_FH_FireStrand_Flight), M_FH_HeroSkinFire (+MI_FH_VahagnBodyFire), M_FH_Invisible
   under /Game/Twilight/FireHair."""
import sys, os
sys.path.insert(0,'/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto3/firehair_strands/deliver/scripts')
from fh_common import *
import traceback
TEXD=FH+'/Textures'; MATD=FH+'/Materials'; MESHD=FH+'/Meshes'
STEPS=os.environ.get('FH_STEPS','tex,mesh,mat').split(',')
SRC=os.environ.get('FH_SRC','/tmp/claude-1000/-var-www-html-Twilight/698dac2a-e3f5-4f70-948c-b54f3c9be169/scratchpad/proto3/firehair_strands/deliver/assets')   # T_FH_*.png + SM_VahagnFireHair.glb

def imp_tex(fn, srgb, comp, clamp=False, nomip=False):
    name=os.path.splitext(os.path.basename(fn))[0]; path=TEXD+'/'+name
    t=unreal.AssetImportTask(); t.filename=fn; t.destination_path=TEXD; t.destination_name=name; t.automated=True; t.save=True; t.replace_existing=True
    AT.import_asset_tasks([t]); tex=unreal.load_asset(path)
    tex.set_editor_property('srgb',srgb); tex.set_editor_property('compression_settings',comp)
    if clamp:
        tex.set_editor_property('address_x',unreal.TextureAddress.TA_CLAMP); tex.set_editor_property('address_y',unreal.TextureAddress.TA_CLAMP)
    if nomip: tex.set_editor_property('mip_gen_settings',unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    EAL.save_loaded_asset(tex); log('tex %s'%path); return tex

def T(n): return unreal.load_asset(TEXD+'/'+n)

if 'tex' in STEPS:
    D=SRC+'/'
    imp_tex(D+'T_FH_Noise.png', False, unreal.TextureCompressionSettings.TC_DEFAULT)
    imp_tex(D+'T_FH_FireLUT.png', False, unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP, clamp=True, nomip=True)
    imp_tex(D+'T_FH_BodyMask.png', False, unreal.TextureCompressionSettings.TC_DEFAULT)

if 'mesh' in STEPS:
    path=MESHD+'/SM_VahagnFireHair'
    if EAL.does_asset_exist(path): EAL.delete_asset(path)
    if EAL.does_directory_exist(MESHD+'/Import'): EAL.delete_directory(MESHD+'/Import')
    t=unreal.AssetImportTask(); t.filename=SRC+'/SM_VahagnFireHair.glb'; t.destination_path=MESHD+'/Import'; t.automated=True; t.save=True; t.replace_existing=True
    AT.import_asset_tasks([t]); log('imported %s'%list(t.get_editor_property('imported_object_paths')))
    sm=None
    for p in t.get_editor_property('imported_object_paths'):
        o=unreal.load_asset(p)
        if isinstance(o,unreal.StaticMesh): sm=o
    EAL.rename_asset(sm.get_path_name().split('.')[0], path); sm=unreal.load_asset(path)
    EAL.delete_directory(MESHD+'/Import')
    SMS=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.EditorStaticMeshLibrary
    bs=SMS.get_lod_build_settings(sm,0); bs.set_editor_property('generate_lightmap_u_vs',False); bs.set_editor_property('recompute_normals',False)
    bs.set_editor_property('recompute_tangents',False); bs.set_editor_property('use_full_precision_u_vs',True)
    SMS.set_lod_build_settings(sm,0,bs)
    try: sm.set_editor_property('nanite_settings', unreal.MeshNaniteSettings())
    except Exception as e: log('nanite %s'%e)
    SMS.remove_collisions(sm)
    log('mesh %s uvch=%d verts=%d tris=%d bounds=%s'%(path, SMS.get_num_uv_channels(sm,0), SMS.get_number_verts(sm,0), sm.get_num_triangles(0) if hasattr(sm,'get_num_triangles') else -1, sm.get_bounds()))
    EAL.save_loaded_asset(sm)
    # drop the placeholder material assets the importer created
    log('assets %s'%EAL.list_assets(MESHD, recursive=True))

def fire_strand(mat):
    setup_material(mat, shading='MSM_UNLIT', blend='BLEND_TRANSLUCENT', two_sided=True, usages=('MATUSAGE_STATIC_LIGHTING',))
    mat.set_editor_property('translucency_pass', unreal.MaterialTranslucencyPass.MTP_AFTER_DOF) if hasattr(unreal,'MaterialTranslucencyPass') else None
    g=G(mat)
    uv0=g.texcoord()
    U=g.mask(uv0,r=True); Vv=g.mask(uv0,g=True)
    fl=lambda x: g._unary(unreal.MaterialExpressionFloor, x)
    fr=lambda x: g._unary(unreal.MaterialExpressionFrac, x)
    a=fl(g.mul(U,0.5)); b=fl(g.mul(Vv,0.5))
    u=g.sub(U, g.mul(a,2.0)); v=g.sat(g.sub(Vv, g.mul(b,2.0)))
    ph=g.mul(g.add(g.mul(a,8.0), b), 1.0/64.0)                       # per-lock id 0..1
    heat=g.add(g.scalar('HeatMin',0.55,'Fire'), g.mul(fr(g.mul(ph,7.13)), 0.22))
    t=g.mul(g.time(), g.scalar('FlowSpeed',1.1,'Fire'))
    nobj=g.tex_param_obj('NoiseTex', T('T_FH_Noise'))
    uvA=g.append(g.add(g.mul(u,0.32), g.mul(ph,7.31)), g.add(g.sub(g.mul(v,g.scalar('NoiseLength',0.75,'Fire')), t), g.mul(ph,3.17)))
    uvB=g.append(g.add(g.mul(u,0.55), g.mul(ph,3.71)), g.add(g.sub(g.mul(v,1.6), g.mul(t,1.73)), g.mul(ph,5.3)))
    nA=g.sample(nobj, T('T_FH_Noise'), uvA, 'R'); nB=g.sample(nobj, T('T_FH_Noise'), uvB, 'G')
    n=g.add(g.mul(nA,0.6), g.mul(nB,0.4))
    # wavy flame edge: shift u by noise more towards the tip
    uu=g.add(u, g.mul(g.sub(nB,0.5), g.mul(v, g.scalar('EdgeWobble',0.3,'Fire'))))
    edge=g.sat(g.one_minus(g.absx(g.sub(g.mul(uu,2.0),1.0))))
    body=g.mul(g.power(g.maxx(edge,0.0001), g.scalar('EdgeSoft',1.1,'Fire')), g.power(g.maxx(g.one_minus(v),0.0001), 0.6))
    root=g.sat(g.mul(v, g.scalar('RootFade',14.0,'Fire')))
    erode=g.mul(n, g.add(g.scalar('Erode0',0.3,'Fire'), g.mul(v, g.scalar('ErodeTip',0.75,'Fire'))))
    T_=g.mul(g.sat(g.mul(g.sub(g.mul(body,1.3), erode), g.scalar('Sharp',1.7,'Fire'))), root)
    temp=g.sat(g.add(g.mul(g.mul(T_, heat), g.sub(1.05, g.mul(v, g.scalar('TipCool',0.9,'Fire')))), g.scalar('HeatBias',0.0,'Fire')))
    lobj=g.tex_param_obj('FireLUT', T('T_FH_FireLUT'))
    col=g.sample(lobj, T('T_FH_FireLUT'), g.append(g.mul(temp,0.98), g.c1(0.5)), 'RGB')
    tt=g.time()
    flick=g.add(0.85, g.mul(g.mul(g.sine(g.add(g.mul(tt,2.3), g.mul(ph,5.0))), g.sine(g.add(g.mul(tt,3.7), g.mul(ph,11.0)))), g.scalar('Flicker',0.15,'Fire')))
    g.out('MP_EMISSIVE_COLOR', g.mul(g.mul(col, g.scalar('Intensity',12.0,'Fire')), flick))
    # dim parts of a flame are transparent, not black: opacity follows temperature
    dfade=g.new(unreal.MaterialExpressionDepthFade, fade_distance_default=4.0)   # soft where the cards cut into the scalp/jaw
    op=g.mul(g.sat(g.mul(g.power(g.maxx(temp,0.0001),1.4), g.scalar('OpacityGain',1.7,'Fire'))), g.scalar('Opacity',0.72,'Fire'))
    g.link(op, dfade, 'Opacity')
    g.out('MP_OPACITY', dfade)
    # world position offset: sway (cm) + wind/flight stream (vector param, cm at the tip) on v^2
    v2=g.mul(v,v)
    sw=g.scalar('Sway',2.2,'Motion')
    sx=g.sine(g.add(g.add(g.mul(tt,0.9), ph), g.mul(v,0.6)))
    sy=g.sine(g.add(g.add(g.mul(tt,1.13), g.mul(ph,1.7)), g.add(g.mul(v,0.5),0.25)))
    sz=g.mul(g.sine(g.add(g.mul(tt,1.7), g.mul(ph,2.3))),0.6)
    sway=g.mul(g.append(g.append(sx,sy),sz), g.mul(v2,sw))
    wind=g.mul(g.vec('Wind',(0,0,0),'Motion'), v2)
    g.out('MP_WORLD_POSITION_OFFSET', g.add(sway, wind))
    finish_material(mat)

def hero_skin_fire(mat, noise, detail):
    """M_HeroSkin (Game/Tools/hero/hero_materials.py, default-lit skin) + fire: FireMaskTex R=ember glow (facial hair+scalp),
       G=iris (eyes like suns), B=charcoal recolour. Keeps the game params (EmissiveIntensity, RimIntensity, HitFlash/FlashColor, CrestGlow)."""
    setup_material(mat, shading='MSM_DEFAULT_LIT', usages=('MATUSAGE_SKELETAL_MESH',))
    g=G(mat); uv=g.texcoord()
    base=g.tex_param('BaseTex', unreal.load_asset('/Engine/EngineResources/DefaultTexture'), uv)
    nrm=g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name='NormalTex', texture=unreal.load_asset('/Engine/EngineMaterials/DefaultNormal'), group='Textures'); g.link(uv,nrm,'UVs')
    dn=g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name='DetailNormalTex', texture=detail, group='Textures')
    g.link(g.mul(uv, g.scalar('DetailTiling',22.0,'Detail')), dn, 'UVs')
    fm=g.new(unreal.MaterialExpressionTextureSampleParameter2D, parameter_name='FireMaskTex', texture=T('T_FH_BodyMask'), group='Fire'); g.link(uv,fm,'UVs')
    fR=g.mask((fm,'RGBA'),r=True); fG=g.mask((fm,'RGBA'),g=True); fB=g.mask((fm,'RGBA'),b=True)
    nxy=g.add(g.mask((nrm,'RGB'),r=True,g=True), g.mul(g.mask((dn,'RGB'),r=True,g=True), g.mul(g.scalar('DetailStrength',0.0,'Detail'), g.one_minus(fB))))
    g.out('MP_NORMAL', g.normalize(g.append(nxy, g.mask((nrm,'RGB'),b=True))))
    lum=g.dot(base, g.c3(0.3,0.59,0.11))
    col=g.lerp(lum, base, g.scalar('Saturation',1.0,'Surface')); col=g.mul(col, g.vec('Tint',(1,1,1)))
    mn=g.tex_param('MottleTex', noise, g.mul(uv, g.scalar('MottleTiling',3.0,'Detail')), 'R')
    col=g.mul(col, g.add(g.mul(g.sub(mn,0.5), g.mul(g.scalar('Mottle',0.0,'Detail'),2.0)),1.0))
    # facial hair / scalp -> soot-dark char, eyes -> pale hot
    col=g.lerp(col, g.vec('CharColor',(0.03,0.018,0.012),'Fire'), g.mul(fB, g.scalar('CharAmount',1.0,'Fire')))
    g.out('MP_BASE_COLOR', col)
    g.out('MP_METALLIC', g.c1(0.0))
    g.out('MP_ROUGHNESS', g.lerp(g.scalar('Roughness',0.6,'Surface'), 0.9, fB))
    g.out('MP_SPECULAR', g.scalar('Specular',0.5,'Surface'))
    t=g.time()
    nobj=g.tex_param_obj('FireNoiseTex', T('T_FH_Noise'))
    e1=g.sample(nobj, T('T_FH_Noise'), g.panner(g.mul(uv, g.scalar('EmberTiling',36.0,'Fire')), 0.0, -0.35, g.mul(t, g.scalar('EmberSpeed',0.25,'Fire'))), 'R')
    e2=g.sample(nobj, T('T_FH_Noise'), g.panner(g.mul(uv, 83.0), 0.05, -0.6, g.mul(t, g.scalar('EmberSpeed',0.25,'Fire'))), 'B')
    pat=g.sat(g.mul(g.sub(g.add(g.mul(e1,0.6), g.mul(e2,0.4)), g.scalar('EmberThreshold',0.3,'Fire')), 2.2))
    flick=g.add(0.85, g.mul(g.sine(g.mul(t,1.9)), 0.15))
    ember=g.mul(g.mul(fR, g.add(0.25, g.mul(pat,0.75))), flick)
    em=g.mul(g.mul(g.vec('EmberColor',(1.0,0.3,0.05),'Fire'), g.power(g.maxx(ember,0.0001),1.5)), g.scalar('EmberIntensity',6.0,'Fire'))
    eye=g.mul(g.mul(g.vec('EyeColor',(1.0,0.66,0.26),'Fire'), fG), g.scalar('EyeIntensity',90.0,'Fire'))
    em=g.add(em, eye)
    # game params (kept so AVahagnCharacter's MIDs keep working)
    red=g.sat(g.mul(g.sub(g.mask(base,r=True), g.maxx(g.mask(base,g=True), g.mask(base,b=True))),3.0))
    em=g.add(em, g.mul(g.mul(red, g.vec('GlowColor',(1.0,0.35,0.06),'Emissive')), g.scalar('CrestGlow',0.0,'Emissive')))
    em=g.add(em, g.mul(g.mul(g.vec('RimColor',(1.0,0.42,0.08),'Emissive'), g.fresnel(4.0)), g.scalar('RimIntensity',0.0,'Emissive')))
    em=g.add(em, g.mul(g.vec('FlashColor',(1.0,0.22,0.04),'Emissive'), g.scalar('HitFlash',0.0,'Emissive')))
    em=g.add(em, g.mul(g.c3(1,0.45,0.08), g.mul(g.scalar('EmissiveIntensity',0.0,'Emissive'), g.c1(0.0))))
    g.out('MP_EMISSIVE_COLOR', em)
    finish_material(mat)

if 'mat' in STEPS:
    noise=unreal.load_asset('/Game/StarterContent/Textures/T_Perlin_Noise_M'); detail=unreal.load_asset('/Game/Twilight/Hero/Textures/T_SkinDetail_N')
    for name,fn in (('M_FH_FireStrand',fire_strand),('M_FH_HeroSkinFire',lambda m: hero_skin_fire(m,noise,detail))):
        try:
            p=MATD+'/'+name
            m=unreal.load_asset(p) if EAL.does_asset_exist(p) else AT.create_asset(name,MATD,unreal.Material,unreal.MaterialFactoryNew())
            if EAL.does_asset_exist(p): clear_graph(m)
            fn(m); log('built %s'%p)
        except Exception: log('FAILED %s\n%s'%(name,traceback.format_exc()))
    # invisible (hides the helmet section in look-dev scenes; the game uses ShowMaterialSection instead)
    p=MATD+'/M_FH_Invisible'
    m=unreal.load_asset(p) if EAL.does_asset_exist(p) else AT.create_asset('M_FH_Invisible',MATD,unreal.Material,unreal.MaterialFactoryNew())
    clear_graph(m); setup_material(m, shading='MSM_UNLIT', blend='BLEND_MASKED', usages=('MATUSAGE_SKELETAL_MESH',)); g=G(m); g.out('MP_OPACITY_MASK', g.c1(0.0)); finish_material(m)
    mi=mic(MATD+'/MI_FH_FireStrand', MATD+'/M_FH_FireStrand', {})
    mic(MATD+'/MI_FH_FireStrand_Flight', MATD+'/M_FH_FireStrand', {}, {'Wind':(-25,0,60)})   # look-dev value for MaxFlySpeed 2700 along +X; the game sets it per tick from C++
    src=unreal.load_asset('/Game/Twilight/Hero/Materials/MI_Vahagn_Body')
    sc={str(p.parameter_info.name):p.parameter_value for p in src.get_editor_property('scalar_parameter_values')}
    vc={str(p.parameter_info.name):(p.parameter_value.r,p.parameter_value.g,p.parameter_value.b) for p in src.get_editor_property('vector_parameter_values')}
    tx={str(p.parameter_info.name):p.parameter_value for p in src.get_editor_property('texture_parameter_values')}
    sc.pop('MetalMask',None)
    mic(MATD+'/MI_FH_VahagnBodyFire', MATD+'/M_FH_HeroSkinFire', sc, vc, tx)
    sm=unreal.load_asset(MESHD+'/SM_VahagnFireHair')
    if sm: sm.set_material(0, unreal.load_asset(MATD+'/MI_FH_FireStrand')); EAL.save_loaded_asset(sm)
    log('materials done errors=%s'%ERRORS)
