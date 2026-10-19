import json,urllib.request,urllib.parse,gzip,sys,time
OUT=sys.argv[1]; OP=sys.argv[2]; qs=sys.argv[3].split('|')
paths=json.load(gzip.open(OP))
try: rows=json.load(open(OUT))
except Exception: rows=[]
have={r['uid'] for r in rows}; new=[]
for q in qs:
  url='https://api.sketchfab.com/v3/search?'+urllib.parse.urlencode(dict(type='models',q=q,downloadable='true',count=24,sort_by='-likeCount'))
  for page in range(int(sys.argv[4]) if len(sys.argv)>4 else 2):
    try: d=json.load(urllib.request.urlopen(url,timeout=30))
    except Exception as e: print('err',q,e); break
    for m in d['results']:
      lic=(m.get('license') or {}).get('label','?')
      if m['uid'] in have or 'NonCommercial' in lic or 'NoDerivs' in lic: continue
      have.add(m['uid'])
      th=sorted(m.get('thumbnails',{}).get('images',[]),key=lambda i:-i['width'])
      th=[i['url'] for i in th if i['width']<=720][:1]
      r=dict(uid=m['uid'],lic=lic,faces=m['faceCount'],verts=m['vertexCount'],anims=m['animationCount'],likes=m['likeCount'],name=m['name'],user=m['user']['username'],inobj=paths.get(m['uid']),q=q,thumb=th[0] if th else None,tags=[t['name'] for t in m.get('tags',[])][:15],date=m.get('publishedAt','')[:10])
      rows.append(r); new.append(r)
    url=d.get('next')
    if not url: break
    time.sleep(0.25)
json.dump(rows,open(OUT,'w'),indent=0)
new=[r for r in new if r['inobj']]
new.sort(key=lambda r:-r['likes'])
for r in new: print(r['uid'][:12],r['lic'][:8],'f',r['faces'],'a',r['anims'],'L',r['likes'],r['q'][:14],'|',r['name'][:48],'|',r['user'])
print('new inobj',len(new),'total',len(rows))
