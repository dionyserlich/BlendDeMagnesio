import json, sys
g, p = sys.argv[1], sys.argv[2]
cfg = {}
inblk = False
with open(g, errors="replace") as f:
    for line in f:
        if line.startswith("; CONFIG_BLOCK_START"): inblk = True; continue
        if line.startswith("; CONFIG_BLOCK_END"): break
        if inblk and " = " in line:
            k, v = line[2:].rstrip("\n").split(" = ", 1); cfg[k] = v
d = json.load(open(p))
def norm(v):
    if isinstance(v, list): return ",".join(v) if len(v)!=1 else v[0]
    return v
for k in sorted(set(cfg)|set(d)):
    a = cfg.get(k); b = d.get(k)
    if b is not None: b = norm(b)
    if a is None or b is None:
        if k not in ("name","from","version","inherits_group"): print("ONLY", "gcode" if b is None else "3mf", k, (a or b)[:80])
        continue
    if a.replace("\\n","\n") != b and a != b and len(a) < 300:
        print("DIFF", k, "| gcode:", a[:100], "| 3mf:", b[:100])
