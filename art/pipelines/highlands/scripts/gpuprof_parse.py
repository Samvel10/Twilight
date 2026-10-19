# parse ProfileGPU dumps between "HLP SET" markers -> frame time + inclusive ms of key passes (and biggest leaf draws)
import sys, re
lines = open(sys.argv[1], errors='replace').read().split('\n')
KEYS = ('PrePass', 'BasePass', 'ShadowDepths', 'Lights', 'TAA', 'Translucency', 'PostProcessing', 'HZB', 'Occlusion', 'SkyAtmosphere',
        'ReflectionEnvironment', 'ScreenSpaceReflections', 'Fog', 'Velocity', 'Water')
res = []; cur = None
for ln in lines:
    m = re.search(r'HLP SET (\d+) (.*)', ln)
    if m:
        cur = {'set': m.group(2), 'frame': None, 'p': {}, 'leaf': []}; res.append(cur); continue
    if cur is None or 'LogRHI' not in ln: continue
    m = re.search(r'Frame Time\s*:\s*([\d.]+)ms', ln)
    if m and cur['frame'] is None: cur['frame'] = float(m.group(1)); continue
    m = re.search(r'│\s*([\d.]+) ms ┃( *)([^┃]*?)\s*┃\s*$', ln)
    if m:
        t, ind, name = m.group(1), m.group(2), m.group(3); t = float(t); depth = len(ind)
        for k in KEYS:
            if name.lower().startswith(k.lower()) and k not in cur['p']:
                cur['p'][k] = t
        cur['leaf'].append((t, depth, name[:60]))
for r in res:
    print('SET %-40s frame %s ms | %s' % (r['set'], r['frame'], ', '.join('%s %.2f' % kv for kv in r['p'].items())))
    if '-v' in sys.argv:
        for t, d, n in sorted([x for x in r['leaf'] if x[1] > 10], reverse=True)[:12]:
            print('        %.2f %s%s' % (t, ' ' * (d // 3), n))
