import gzip,json,glob,re,sys
d=sys.argv[1]; out=sys.argv[2]
pat=re.compile(sys.argv[3],re.I); neg=re.compile(sys.argv[4],re.I) if len(sys.argv)>4 else None
res={}
for f in sorted(glob.glob(d+'/*.json.gz')):
    for u,m in json.load(gzip.open(f)).items():
        lic=m.get('license') or ''
        if lic not in ('by','cc0'): continue
        txt=m['name']+' '+' '.join(t['name'] for t in m.get('tags',[]))
        if not pat.search(txt): continue
        if neg and neg.search(txt): continue
        th=[t for t in m['thumbnails']['images'] if t['width']<=400]
        res[u]=dict(name=m['name'],user=m['user']['username'],lic=lic,anims=m.get('animationCount',0),faces=m.get('faceCount'),likes=m['likeCount'],pub=m['publishedAt'][:10],
           thumb=(max(th,key=lambda t:t['width'])['url'] if th else ''),tags=[t['name'] for t in m.get('tags',[])][:15],desc=(m.get('description') or '')[:300],shard=f.split('/')[-1][:7])
json.dump(res,open(out,'w'),indent=0); print(len(res))
