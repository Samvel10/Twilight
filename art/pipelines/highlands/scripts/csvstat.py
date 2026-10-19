# csvstat.py <csv> [skip] : summarise a UE CSV profile (frame / GPU / thread times) per 300-frame segment and overall after skip
import sys, csv, statistics as st
csv.field_size_limit(10**9)
rows = list(csv.reader(open(sys.argv[1])))
skip = int(sys.argv[2]) if len(sys.argv) > 2 else 600
h = rows[0]; data = [r for r in rows[1:] if len(r) > 10 and not r[0].startswith('[')]
def col(n, a=0, b=None):
    i = h.index(n); out = []
    for r in data[a:b]:
        try: out.append(float(r[i]))
        except (ValueError, IndexError): pass
    return out
keys = [c for c in ('FrameTime', 'GPUTime', 'GameThreadTime', 'RenderThreadTime', 'RHIThreadTime') if c in h]
for a in range(0, len(data), 300):
    print('%4d-%4d ' % (a, a + 300) + ' '.join('%s=%.1f' % (k, st.mean(col(k, a, a + 300))) for k in keys if col(k, a, a + 300)))
ft = col('FrameTime', skip); g = col('GPUTime', skip) if 'GPUTime' in h else []
q = lambda v, p: sorted(v)[int(len(v) * p)]
print('RESULT frames=%d frame avg %.2f ms = %.1f fps, p95 %.2f ms | GPU avg %s p95 %s' % (len(ft), st.mean(ft), 1000 / st.mean(ft), q(ft, .95),
      ('%.2f' % st.mean(g)) if g else '-', ('%.2f' % q(g, .95)) if g else '-'))
# GPU pass breakdown (steady state)
gp = []
for i, c in enumerate(h):
    if c.startswith('GPU/'):
        v = []
        for r in data[skip:]:
            try: v.append(float(r[i]))
            except (ValueError, IndexError): pass
        if v and st.mean(v) > 0.15:
            gp.append((st.mean(v), c))
print('GPU passes: ' + ', '.join('%s %.2f' % (c[4:], m) for m, c in sorted(gp, reverse=True)[:14]))
seg = []
for a in range(skip if skip < len(data) - 300 else 300, len(data) - 299, 150):
    f = col('FrameTime', a, a + 300); gg = col('GPUTime', a, a + 300)
    if f and gg: seg.append((st.mean(gg), st.mean(f), a))
if seg:
    b = min(seg)
    print('BEST300 from frame %d: frame %.2f ms (%.1f fps) GPU %.2f ms   [GPU shared with other agents editors; worst segment GPU %.2f]' % (b[2], b[1], 1000 / b[1], b[0], max(seg)[0]))
