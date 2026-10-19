"""python3 -P gpuprof.py <perf log> [min_ms] -- parse UE 'profilegpu' tables: prints frame time and passes (inclusive ms) per captured frame,
   plus the key rows (Translucency*, Lights, fire mesh). Rows: name -> inclusive ms."""
import sys, re
txt = open(sys.argv[1], errors='ignore').read().split('GPU Profile for Frame')[1:]
mn = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
KEY = re.compile(r'Translucen|FireHair|Lights$|RenderLight|BasePass$|PostProcessing$|Frame \d+$|Scene$|TSR|TemporalAA|Bloom|DepthOfField|SeparateTranslucency')
for i, blk in enumerate(txt):
    ft = re.search(r'Frame Time\s*:\s*([\d.]+)ms', blk).group(1)
    print('== profile %d frame %s ms' % (i+1, ft))
    for line in blk.splitlines():
        if 'Display:' not in line or '┃' not in line: continue
        cells = [c.strip() for c in re.split('[┃│]', line.split('Display:', 1)[1])]
        if len(cells) < 14: continue
        try: inc = float(cells[12].replace('ms', ''))
        except ValueError: continue
        name = cells[13]
        if KEY.search(name) and (inc >= mn or 'ranslu' in name or 'FireHair' in name): print('  %7.3f  %s' % (inc, name[:110]))
