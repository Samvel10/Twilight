import json,urllib.request,urllib.parse,sys,re
pat=re.compile(sys.argv[1],re.I)
for un in sys.argv[2:]:
    url='https://api.sketchfab.com/v3/search?'+urllib.parse.urlencode(dict(type='models',user=un,count=24,downloadable='true'))
    n=0
    while url and n<20:
        d=json.load(urllib.request.urlopen(url,timeout=30)); n+=1
        for m in d['results']:
            if pat.search(m['name']): print(m['uid'],m['likeCount'],m['animationCount'],m['faceCount'],(m.get('license') or {}).get('label'),m['user']['username'],'|',m['name'])
        url=d.get('next')
