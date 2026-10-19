import json,urllib.request,urllib.parse,sys,re
out=sys.argv[1]; pat=re.compile(sys.argv[2],re.I); qs=sys.argv[3].split('|'); anim=sys.argv[4]=='1'
seen={}
for lic in ('by','cc0'):
  for q in qs:
    for sb in ('-likeCount','-publishedAt','-viewCount'):
      p=dict(type='models',q=q,downloadable='true',license=lic,count=24,sort_by=sb)
      if anim: p['animated']='true'
      url='https://api.sketchfab.com/v3/search?'+urllib.parse.urlencode(p); n=0
      while url and n<6:
        try: d=json.load(urllib.request.urlopen(url,timeout=30))
        except Exception as e: print('err',e,file=sys.stderr); break
        n+=1
        for m in d['results']:
          if not pat.search(m['name']+' '+' '.join(t['name'] for t in m.get('tags',[]))): continue
          seen[m['uid']]=dict(lic=(m.get('license') or {}).get('label','?'),faces=m['faceCount'],anims=m['animationCount'],likes=m['likeCount'],name=m['name'],user=m['user']['username'],
            thumb=max((t for t in m['thumbnails']['images']),key=lambda t:t['width'] if t['width']<=400 else 0)['url'],tags=[t['name'] for t in m.get('tags',[])][:12])
        url=d.get('next')
json.dump(seen,open(out,'w'),indent=0)
for u,m in sorted(seen.items(),key=lambda x:-x[1]['likes']): print(u,m['likes'],m['anims'],m['faces'],m['lic'][:14],m['user'],'|',m['name'])
