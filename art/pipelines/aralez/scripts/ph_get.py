"""Download Poly Haven (CC0) assets: ph_get.py outdir kind:id:res ..."""
import json, urllib.request, sys, os
UA={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) twilight-proto'}
def op(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120)
out = sys.argv[1]
def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = op(url).read(); open(path, 'wb').write(data)
for spec in sys.argv[2:]:
    kind, aid, res = spec.split(':')
    f = json.load(op('https://api.polyhaven.com/files/' + aid))
    d = os.path.join(out, aid)
    if kind == 'hdri':
        e = f['hdri'][res]['hdr']; get(e['url'], os.path.join(d, os.path.basename(e['url'])))
    elif kind == 'tex':
        for m in ('Diffuse', 'nor_dx', 'arm', 'Rough', 'AO', 'Displacement'):
            if m in f and res in f[m]:
                k = 'jpg' if 'jpg' in f[m][res] else 'png'; e = f[m][res][k]; get(e['url'], os.path.join(d, os.path.basename(e['url'])))
    elif kind == 'model':
        g = f['gltf'][res]['gltf']; get(g['url'], os.path.join(d, os.path.basename(g['url'])))
        for rel, e in g['include'].items(): get(e['url'], os.path.join(d, rel))
    print('ok', spec)
