"""python3 -P gpudiff.py <logdir> <A> <B> [n] -- average exclusive GPU time per pass over perf_<A>_1..n vs perf_<B>_1..n, print biggest deltas"""
import re, sys, collections
D, A, B = sys.argv[1], sys.argv[2], sys.argv[3]; N = int(sys.argv[4]) if len(sys.argv) > 4 else 3
def prof(fn):
    blk = open(fn, errors='ignore').read().split('GPU Profile for Frame')[1]; d = collections.defaultdict(float)
    for line in blk.splitlines():
        if 'Display:' not in line or '┃' not in line: continue
        c = [x.strip() for x in re.split('[┃│]', line.split('Display:', 1)[1])]
        if len(c) < 14: continue
        try: ex = float(c[6].replace('ms', ''))
        except ValueError: continue
        d[re.sub(r'Frame \d+', 'Frame', re.sub(r'\d+x\d+', '', c[13]))] += ex
    return d
def avg(t):
    ds = [prof('%s/perf_%s_%d.log' % (D, t, i)) for i in range(1, N+1)]; ks = set().union(*ds)
    return {k: sum(d.get(k, 0) for d in ds)/len(ds) for k in ks}
a, b = avg(A), avg(B); diff = sorted(((a.get(k, 0)-b.get(k, 0), k) for k in set(a) | set(b)), reverse=True)
print('%s - %s: total %+.2f ms (%.2f vs %.2f)' % (A, B, sum(a.values())-sum(b.values()), sum(a.values()), sum(b.values())))
for dv, k in diff[:10] + diff[-4:]: print('  %+.3f  %s' % (dv, k[:90]))
