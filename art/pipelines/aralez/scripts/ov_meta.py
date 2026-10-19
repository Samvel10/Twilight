import gzip,json,sys,urllib.request
from concurrent.futures import ThreadPoolExecutor
lv=json.load(gzip.open(sys.argv[1])); cats=sys.argv[3].split(','); out=sys.argv[2]
uids={u:c for c in cats for u in lv.get(c,[])}
def get(u):
    try:
        d=json.load(urllib.request.urlopen('https://api.sketchfab.com/v3/models/'+u,timeout=30))
        return u,dict(cat=uids[u],name=d['name'],user=d['user']['username'],lic=(d.get('license') or {}).get('label','?'),anims=d.get('animationCount'),faces=d['faceCount'],likes=d['likeCount'],pub=d['publishedAt'][:10],
            thumb=max((t for t in d['thumbnails']['images']),key=lambda t:t['width'] if t['width']<=400 else 0)['url'],desc=(d.get('description') or '')[:300])
    except Exception as e: return u,dict(cat=uids[u],err=str(e))
with ThreadPoolExecutor(8) as ex: res=dict(ex.map(get,list(uids)))
json.dump(res,open(out,'w'),indent=0)
for u,m in sorted(res.items(),key=lambda x:(x[1].get('cat'),-(x[1].get('anims') or 0))):
    if 'err' in m: continue
    print(u,m['cat'],m['anims'],m['faces'],m['likes'],m['lic'][:16],m['user'],'|',m['name'])
