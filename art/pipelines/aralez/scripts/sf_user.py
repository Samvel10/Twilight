import json,urllib.request,urllib.parse,sys
for un in sys.argv[1:]:
    try:
        u=json.load(urllib.request.urlopen('https://api.sketchfab.com/v3/users?'+urllib.parse.urlencode(dict(username=un)),timeout=30))['results']
    except Exception as e: print('ERR',un,e); continue
    if not u: print('nouser',un); continue
    uid=u[0]['uid']; print('##',un,uid,u[0].get('modelCount'))
    url='https://api.sketchfab.com/v3/models?'+urllib.parse.urlencode(dict(user=uid,count=24,sort_by='-likeCount'))
    for page in range(8):
        d=json.load(urllib.request.urlopen(url,timeout=30))
        for m in d['results']:
            print(' ',m['uid'],m['likeCount'],m.get('animationCount'),m['faceCount'],(m.get('license') or {}).get('label','-')[:12],m.get('isDownloadable'),'|',m['name'],'|',m['publishedAt'][:10])
        url=d.get('next')
        if not url: break
