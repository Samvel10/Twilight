import json,struct,sys
for f in sys.argv[1:]:
    b=open(f,'rb').read(); n=struct.unpack('<I',b[12:16])[0]; j=json.loads(b[20:20+n])
    print('=====',f.split('/')[-1])
    print(' meshes',[(m.get('name'),len(m['primitives']),[bool(p.get('targets')) for p in m['primitives']]) for m in j.get('meshes',[])])
    print(' skins',[len(s['joints']) for s in j.get('skins',[])])
    if j.get('skins'): print(' joints',[j['nodes'][k].get('name') for k in j['skins'][0]['joints']][:200])
    for a in j.get('animations',[]):
        mx=0
        for s in a['samplers']:
            acc=j['accessors'][s['input']]; mx=max(mx,acc.get('max',[0])[0])
        print(' anim',a.get('name'),'channels',len(a['channels']),'dur %.2f'%mx)
    print(' materials',[(m.get('name'),list(m.get('pbrMetallicRoughness',{}).keys()),'N' if 'normalTexture' in m else '', m.get('alphaMode','')) for m in j.get('materials',[])])
    print(' images',[(i.get('name'),i.get('mimeType'),j['bufferViews'][i['bufferView']]['byteLength'] if 'bufferView' in i else i.get('uri')) for i in j.get('images',[])])
    for i in j.get('accessors',[])[:0]: pass
