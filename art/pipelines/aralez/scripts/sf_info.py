import json,urllib.request,sys
for u in sys.argv[1:]:
    d=json.load(urllib.request.urlopen('https://api.sketchfab.com/v3/models/'+u,timeout=30))
    print('=====',u,d['name'],'| by',d['user']['username'],'|',(d.get('license') or {}).get('label'),'| pub',d['publishedAt'][:10],'| faces',d['faceCount'],'verts',d['vertexCount'],'anims',d.get('animationCount'),'| tex',d.get('textureCount'),'mats',d.get('materialCount'))
    print('  tags:',[t['name'] for t in d.get('tags',[])])
    print('  desc:',(d.get('description') or '').replace('\n',' ')[:700])
    try:
        a=json.load(urllib.request.urlopen('https://api.sketchfab.com/v3/models/%s/animations'%u,timeout=30))
        print('  anims:',[(x.get('name'),round(x.get('duration',0),2)) for x in a.get('results',[])][:120])
    except Exception as e: print('  anims err',e)
