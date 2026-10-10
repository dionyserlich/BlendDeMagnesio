"""Analisa G-code do Bambu Studio (A1): tempo por FEATURE, por camada, travels,
retrações, z-hop. Planejador simples com lookahead (jerk clássico + trapézio)."""
import sys, re, math, json, collections

JERK = 9.0          # machine_max_jerk_x/y
MAXACC = 12000.0
import os
INCLUDE_COND = os.environ.get('INCLUDE_COND') == '1'
FD_PAT = re.compile(r'([A-Z])(-?\d*\.?\d+)')

def parse(path):
    moves = []      # (dx,dy,dz,de,f,acc,feature,layer,kind)
    x = y = z = e = 0.0
    f = 1800.0; acc = 4000.0
    feature = "Start/End"; layer = -1
    in_body = False
    extra = collections.Counter()
    retracts = 0; zhops = 0; m400 = 0; dwell = 0.0
    cond_depth = 0; cond_cmds = 0
    with open(path, errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line: continue
            if line[0] == ';':
                if line.startswith('; FEATURE: '): feature = line[11:]
                elif line.startswith('; CHANGE_LAYER'): layer += 1; feature = "Layer change"
                elif line.startswith('; MACHINE_START_GCODE_END'): in_body = True; feature = "Body?"
                elif line.startswith('; MACHINE_END_GCODE_START'): in_body = False; feature = "Start/End"
                elif line.startswith('; WIPE_START'): feature_save = feature; feature = "Wipe"
                elif line.startswith('; WIPE_END'): feature = feature_save
                continue
            code = line.split(';', 1)[0].strip()
            if not code: continue
            cmd = code.split()[0]
            if cmd == 'M622':
                cond_depth += 1; continue
            if cmd == 'M623':
                cond_depth = max(0, cond_depth - 1); continue
            if cond_depth > 0 and in_body:
                cond_cmds += 1
                if not INCLUDE_COND: continue
            if cmd in ('G0', 'G1', 'G2', 'G3'):
                p = dict((k, float(v)) for k, v in FD_PAT.findall(code[len(cmd):]))
                if 'F' in p: f = p['F']
                nx, ny, nz = p.get('X', x), p.get('Y', y), p.get('Z', z)
                de = p.get('E', 0.0)
                dx, dy, dz = nx - x, ny - y, nz - z
                if cmd in ('G2', 'G3') and ('I' in p or 'J' in p) and ('X' in p or 'Y' in p):
                    cx, cy = x + p.get('I', 0), y + p.get('J', 0)
                    r = math.hypot(x - cx, y - cy)
                    a0 = math.atan2(y - cy, x - cx); a1 = math.atan2(ny - cy, nx - cx)
                    da = a1 - a0
                    if cmd == 'G2' and da >= 0: da -= 2 * math.pi
                    if cmd == 'G3' and da <= 0: da += 2 * math.pi
                    L = abs(da) * r
                    k = max(1, int(math.ceil(L / 0.3)))
                    px_, py_ = x, y
                    for i in range(1, k + 1):
                        a = a0 + da * i / k
                        qx, qy = cx + r * math.cos(a), cy + r * math.sin(a)
                        kind = 'extrude' if de > 0 else 'travel'
                        moves.append((qx - px_, qy - py_, dz / k, de / k, f / 60.0, acc, feature, layer, kind, in_body))
                        px_, py_ = qx, qy
                    if dz > 0 and in_body: zhops += 1
                    x, y, z = nx, ny, nz
                    continue
                if cmd in ('G2', 'G3'):
                    # z-hop em espiral (círculo completo, sem X/Y): comprimento = 2*pi*r
                    r = math.hypot(p.get('I', 0), p.get('J', 0))
                    dxy = (2 * math.pi * r, 0.0)
                else:
                    dxy = (dx, dy)
                kind = 'extrude' if de > 0 and (dxy[0] or dxy[1]) else ('retract' if de < 0 and not (dxy[0] or dxy[1] or dz) else ('unretract' if de > 0 and not (dxy[0] or dxy[1] or dz) else 'travel'))
                if kind == 'retract': retracts += 1
                if dz > 0 and in_body: zhops += 1
                moves.append((dxy[0], dxy[1], dz, de, f / 60.0, acc, feature, layer, kind, in_body))
                x, y, z = nx, ny, nz
            elif cmd == 'M204':
                p = dict((k, float(v)) for k, v in FD_PAT.findall(code[4:]))
                if 'S' in p: acc = min(p['S'], MAXACC)
            elif cmd == 'G4':
                p = dict((k, float(v)) for k, v in FD_PAT.findall(code[2:]))
                dwell += p.get('S', 0) + p.get('P', 0) / 1000
            elif cmd == 'M400': m400 += 1
            elif cmd == 'G92': pass
            elif cmd == 'G28': pass
    return moves, dict(retracts=retracts, zhops=zhops, m400=m400, dwell=dwell, cond_cmds_skipped=cond_cmds if not INCLUDE_COND else 0)

def plan(moves):
    n = len(moves)
    L = [0.0] * n; V = [0.0] * n; A = [0.0] * n; U = [None] * n
    for i, m in enumerate(moves):
        dx, dy, dz, de, v, a = m[:6]
        l = math.sqrt(dx * dx + dy * dy + dz * dz)
        if l < 1e-9:
            l = abs(de); v = min(v, 30.0); a = 5000.0; U[i] = None
        else:
            U[i] = (dx / l, dy / l)
        if dz and not (dx or dy): v = min(v, 30.0); a = min(a, 1500)
        L[i] = l; V[i] = v; A[i] = a
    # velocidade de junção (jerk clássico)
    J = [0.0] * (n + 1)
    for i in range(1, n):
        u0, u1 = U[i - 1], U[i]
        if u0 is None or u1 is None: J[i] = 0.0; continue
        v0, v1 = V[i - 1], V[i]
        vj = min(v0, v1)
        # máximo vj tal que |vj*u1 - vj*u0| por eixo <= JERK (aprox.)
        d = max(abs(u1[0] - u0[0]), abs(u1[1] - u0[1]))
        if d > 1e-9: vj = min(vj, JERK / d)
        J[i] = vj
    # backward / forward pass
    for i in range(n - 1, -1, -1):
        J[i] = min(J[i], math.sqrt(J[i + 1] ** 2 + 2 * A[i] * L[i]))
    for i in range(n):
        J[i + 1] = min(J[i + 1], math.sqrt(J[i] ** 2 + 2 * A[i] * L[i]))
    T = [0.0] * n
    for i in range(n):
        v, a, l, vi, vo = V[i], A[i], L[i], J[i], J[i + 1]
        if l <= 0: continue
        da = max(0.0, (v * v - vi * vi) / (2 * a)); dd = max(0.0, (v * v - vo * vo) / (2 * a))
        if da + dd <= l:
            T[i] = (v - vi) / a + (v - vo) / a + (l - da - dd) / v
        else:
            vp = math.sqrt(max(0.0, (2 * a * l + vi * vi + vo * vo) / 2))
            T[i] = max(0.0, (vp - vi) / a + (vp - vo) / a)
    return T, L

def main(path, out_json=None):
    moves, misc = parse(path)
    T, L = plan(moves)
    feat_t = collections.Counter(); feat_l = collections.Counter(); feat_e = collections.Counter()
    feat_vmax = collections.defaultdict(collections.Counter)
    layer_t = collections.Counter()
    body_t = 0.0; total = 0.0
    for m, t, l in zip(moves, T, L):
        dx, dy, dz, de, v, a, feat, layer, kind, inb = m
        total += t
        key = feat if kind == 'extrude' else ('Travel' if kind == 'travel' and feat != 'Wipe' else ('Wipe' if feat == 'Wipe' else 'Retract/unretract'))
        if not inb: key = 'Start/End gcode'
        feat_t[key] += t
        if kind == 'extrude':
            feat_l[key] += l; feat_e[key] += de
            feat_vmax[key][round(v)] += l
        if inb: body_t += t; layer_t[layer] += t
    area = math.pi * 1.75 ** 2 / 4
    res = dict(total_s=total, body_s=body_t, misc=misc, features={}, layers=dict(layer_t))
    print(f"Tempo cinemático total: {total/60:.1f} min  (corpo: {body_t/60:.1f} min)  ", misc)
    print(f"{'feature':28s} {'min':>7s} {'%':>5s} {'m':>7s} {'cm3':>6s}  velocidade dominante (mm/s:%comp)")
    for k, t in feat_t.most_common():
        vs = feat_vmax.get(k)
        top = ""
        if vs:
            tot = sum(vs.values()); top = " ".join(f"{s}:{100*c/tot:.0f}%" for s, c in vs.most_common(3))
        res['features'][k] = dict(t=t, len=feat_l[k], vol=feat_e[k] * area / 1000)
        print(f"{k:28s} {t/60:7.1f} {100*t/total:5.1f} {feat_l[k]/1000:7.2f} {feat_e[k]*area/1000:6.2f}  {top}")
    if out_json: json.dump(res, open(out_json, 'w'))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
