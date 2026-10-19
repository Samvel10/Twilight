import json,urllib.request,urllib.parse,sys
out=sys.argv[1]; qs=sys.argv[2].split('|'); anim=sys.argv[3] if len(sys.argv)>3 else 'true'
seen={}
for lic in ('by','cc0'):
 for q in qs:
  p=dict(type='models',q=q,downloadable='true',license=lic,count=24,sort_by='-likeCount')
  if anim=='true': p['animated']='true'
  url='https://api.sketchfab.com/v3/search?'+urllib.parse.urlencode(p)
  for page in range(2):
    try: d=json.load(urllib.request.urlopen(url,timeout=30))
    except Exception as e: print('err',q,e); break
    for m in d['results']:
      seen[m['uid']]=dict(lic=(m.get('license') or {}).get('label','?'),faces=m['faceCount'],anims=m['animationCount'],likes=m['likeCount'],name=m['name'],user=m['user']['username'],q=q,
        thumb=max((t for t in m['thumbnails']['images']),key=lambda t:t['width'] if t['width']<=700 else 0)['url'])
    url=d.get('next')
    if not url: break
json.dump(seen,open(out,'w'),indent=0)
for u,m in sorted(seen.items(),key=lambda x:-x[1]['likes']): print(u,m['likes'],m['anims'],m['faces'],m['lic'][:10],m['user'],'|',m['name'])
