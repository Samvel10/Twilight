import json,urllib.request,urllib.parse,gzip,sys,time
P=sys.argv[1]; OP=sys.argv[2]
paths=json.load(gzip.open(OP))
seen={}
qs=['pine tree','scots pine','pine tree game ready','realistic pine','oak tree game ready','realistic oak tree','walnut tree','poplar tree','juniper','juniper bush','realistic tree low poly','tree pbr game ready','tree photoscan','birch tree realistic','apricot tree','grass pack','grass clump','grass game ready','realistic grass','wild grass','alpine grass','meadow grass','wildflowers','flower field','fern','bush realistic','shrub game ready','reeds','cattail','dry grass','tall grass','plants pack','vegetation pack','foliage pack','tree pack','speedtree']
for q in qs:
  url='https://api.sketchfab.com/v3/search?'+urllib.parse.urlencode(dict(type='models',q=q,downloadable='true',count=24,sort_by='-likeCount'))
  for page in range(2):
    try: d=json.load(urllib.request.urlopen(url,timeout=30))
    except Exception as e: print('err',q,e); break
    for m in d['results']:
      lic=(m.get('license') or {}).get('label','?')
      th=sorted(m.get('thumbnails',{}).get('images',[]),key=lambda i:-i['width'])
      th=[i['url'] for i in th if i['width']<=720][:1]
      if m['uid'] not in seen:
        seen[m['uid']]=dict(lic=lic,faces=m['faceCount'],likes=m['likeCount'],name=m['name'],user=m['user']['username'],inobj=paths.get(m['uid']),q=q,thumb=th[0] if th else None,tags=[t['name'] for t in m.get('tags',[])][:15])
    url=d.get('next')
    if not url: break
    time.sleep(0.2)
rows=[dict(uid=k,**v) for k,v in seen.items() if ('CC Attribution' == v['lic'] or 'CC0' in v['lic'] or v['lic']=='CC Attribution') and v['inobj'] and v['faces']<150000]
rows.sort(key=lambda r:-r['likes'])
json.dump(rows,open(P+'/dl/sf_veg.json','w'),indent=0)
for r in rows: print(r['uid'][:12],r['lic'][:16],'f',r['faces'],'L',r['likes'],r['q'][:12],'|',r['name'][:50],'|',r['user'])
print('total',len(seen),'ok+inobj',len(rows))
