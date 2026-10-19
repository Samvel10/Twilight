# parse ProfileGPU dumps from a -SerpProfAB run: per-pass inclusive ms for visible vs hidden
import sys,re
lines=open(sys.argv[1],errors='ignore').read().split('\n')
dumps=[];cur=None;vis=None
for l in lines:
    m=re.search(r'SERP profab step=\d+ visible=(\d)',l)
    if m: vis=int(m.group(1)); continue
    if 'GPU Profile for Frame' in l: cur={'vis':vis,'p':{}}; dumps.append(cur); continue
    if cur is not None and '┃' in l:
        parts=l.split('┃')
        if len(parts)<4: continue
        name=parts[3].strip(); incl=re.findall(r'([0-9.]+) ms',parts[2])
        m2=re.search(r'Frame Time\s*:\s*([0-9.]+)ms',l)
        if incl and name:
            key=name.split(' ')[0]
            if key in ('Scene','BasePass','PrePass','ShadowDepths','Velocity','GPUSkinCache_UpdateSkinningBatches','Lights','PostProcessing','Translucency'):
                cur['p'].setdefault(key,float(incl[0]))
    m3=re.search(r'Frame Time\s*:\s*([0-9.]+)ms',l)
    if m3 and cur is not None: cur['p']['Frame']=float(m3.group(1))
for d in dumps: print('visible' if d['vis'] else 'hidden ', ' '.join('%s=%.2f'%(k,v) for k,v in d['p'].items()))
