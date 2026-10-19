# glbimg.py <glb> <outdir> : extract embedded images + print material->texture mapping
import sys,json,struct,os
f,out=sys.argv[1],sys.argv[2]; os.makedirs(out,exist_ok=True)
b=open(f,'rb').read(); n=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+n]); off=20+n+8
for i,im in enumerate(j.get('images',[])):
    bv=j['bufferViews'][im['bufferView']]; data=b[off+bv.get('byteOffset',0):off+bv.get('byteOffset',0)+bv['byteLength']]
    ext='png' if 'png' in im.get('mimeType','') else 'jpg'
    open(os.path.join(out,'img%d.%s'%(i,ext)),'wb').write(data)
texsrc=[t['source'] for t in j.get('textures',[])]
for m in j.get('materials',[]):
    d={}
    pb=m.get('pbrMetallicRoughness',{})
    for k in ('baseColorTexture','metallicRoughnessTexture'):
        if k in pb: d[k]=texsrc[pb[k]['index']]
    for k in ('normalTexture','occlusionTexture','emissiveTexture'):
        if k in m: d[k]=texsrc[m[k]['index']]
    for e,v in m.get('extensions',{}).items():
        for k,vv in v.items():
            if isinstance(vv,dict) and 'index' in vv: d[e+'.'+k]=texsrc[vv['index']]
            else: d[e+'.'+k]=vv
    print(m.get('name'),m.get('alphaMode'),m.get('alphaCutoff'),d)
