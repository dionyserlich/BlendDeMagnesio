import sys, collections
sys.path.insert(0, sys.argv[2])
import gstats
moves, misc = gstats.parse(sys.argv[1])
T0, L = gstats.plan(moves)
NOM = {'Outer wall':60,'Inner wall':112.8,'Sparse infill':112.8,'Floating vertical shell':121.6,'Support':121.6,
       'Internal solid infill':121.6,'Gap infill':121.6,'Top surface':121.6}
m2 = []
for m in moves:
    m = list(m)
    if m[8]=='extrude' and m[6] in NOM and m[4] < NOM[m[6]]*0.97:
        m[4] = NOM[m[6]]
    m2.append(tuple(m))
T1, _ = gstats.plan(m2)
by = collections.Counter()
for m,a,b in zip(moves,T0,T1):
    if m[9]: by[m[6] if m[8]=='extrude' else 'other'] += a-b
print(f"tempo perdido por redução de velocidade (resfriamento/etc): {(sum(T0)-sum(T1))/60:.1f} min")
for k,v in by.most_common(8): print(f"  {k}: {v/60:.1f} min")
