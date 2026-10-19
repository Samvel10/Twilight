import sys,json,struct
for f in sys.argv[1:]:
    b=open(f,'rb').read(); n=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+n])
    print('=====',f, 'meshes',len(j.get('meshes',[])),'nodes',len(j.get('nodes',[])),'mats',len(j.get('materials',[])),'imgs',len(j.get('images',[])),'anims',len(j.get('animations',[])))
    for m in j.get('materials',[]): 
        pb=m.get('pbrMetallicRoughness',{}); print('  mat',m.get('name'),m.get('alphaMode'),'base' if 'baseColorTexture' in pb else '-', 'nrm' if 'normalTexture' in m else '-', pb.get('baseColorFactor'), m.get('doubleSided'))
    for im in j.get('images',[]): print('  img',im.get('name'),im.get('mimeType'), j['bufferViews'][im['bufferView']]['byteLength']//1024 if 'bufferView' in im else im.get('uri'))
    for k,me in enumerate(j.get('meshes',[])[:40]):
        tris=0
        for p in me['primitives']:
            if 'indices' in p: tris+=j['accessors'][p['indices']]['count']//3
        a=j['accessors'][me['primitives'][0]['attributes']['POSITION']]
        print('  mesh',k,me.get('name'),'tris',tris,'prims',len(me['primitives']),'mats',[p.get('material') for p in me['primitives']],'min',[round(v,2) for v in a.get('min',[])],'max',[round(v,2) for v in a.get('max',[])])
    sc=[nd for nd in j.get('nodes',[]) if 'scale' in nd or 'matrix' in nd][:3]
    print('  xform nodes', [ (nd.get('name'), nd.get('scale'), 'matrix' in nd) for nd in sc])
