import gzip,json,glob,sys
users=set(sys.argv[2:])
for f in sorted(glob.glob(sys.argv[1]+'/*.json.gz')):
    for u,m in json.load(gzip.open(f)).items():
        if m['user']['username'] in users: print(m['user']['username'],u,m['publishedAt'][:10],m.get('license'),m.get('animationCount'),m.get('faceCount'),'|',m['name'])
