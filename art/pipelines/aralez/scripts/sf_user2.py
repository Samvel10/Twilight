import json,urllib.request,urllib.parse,sys
# args: model uids; lists all models of each model's author
for mu in sys.argv[1:]:
    m=json.load(urllib.request.urlopen('https://api.sketchfab.com/v3/models/'+mu,timeout=30))
    u=m['user']; print('##',u['username'],u['uid'],'| from',m['name'])
    url='https://api.sketchfab.com/v3/models?'+urllib.parse.urlencode(dict(user=u['uid'],count=24,sort_by='-likeCount'))
    for page in range(10):
        d=json.load(urllib.request.urlopen(url,timeout=30))
        for x in d['results']:
            print(' ',x['uid'],x['likeCount'],x.get('animationCount'),x['faceCount'],(x.get('license') or {}).get('label','-')[:12] if isinstance(x.get('license'),dict) else x.get('license'),x.get('isDownloadable'),'|',x['name'],'|',x['publishedAt'][:10])
        url=d.get('next')
        if not url: break
