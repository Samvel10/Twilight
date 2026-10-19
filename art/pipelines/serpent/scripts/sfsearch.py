import json,urllib.request,urllib.parse,sys
out=sys.argv[1]
seen={}
qs=['snake','snake rigged','serpent','sea serpent','leviathan','eel','moray eel','titanoboa','naga','wyrm','chinese dragon','eastern dragon','long dragon','lindworm','basilisk','python snake','cobra','anaconda','water dragon','sea monster','oarfish','loong','asian dragon','snake animated','serpent dragon','jormungandr','king cobra','boa','viper','dragon snake']
for lic in ('by','cc0'):
 for q in qs:
  url='https://api.sketchfab.com/v3/search?'+urllib.parse.urlencode(dict(type='models',q=q,downloadable='true',license=lic,count=24,sort_by='-likeCount'))
  for page in range(2):
    try: d=json.load(urllib.request.urlopen(url,timeout=30))
    except Exception as e: print('err',q,e); break
    for m in d['results']:
      th=[t for t in m['thumbnails']['images'] if t['width']<=700]
      seen[m['uid']]=dict(lic=(m.get('license') or {}).get('label','?'),faces=m['faceCount'],verts=m['vertexCount'],anims=m['animationCount'],likes=m['likeCount'],name=m['name'],user=m['user']['username'],q=q,thumb=max(th,key=lambda t:t['width'])['url'] if th else '')
    url=d.get('next')
    if not url: break
json.dump(seen,open(out,'w'))
print(len(seen))
