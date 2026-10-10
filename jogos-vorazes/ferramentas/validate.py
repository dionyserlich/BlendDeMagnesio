"""Validação de integridade de um G-code do Bambu Studio para a A1, comparado a uma referência.
Uso: python3 -I validate.py referencia.gcode candidato.gcode"""
import sys, re, collections

BED = (0.0, 256.0)
BAMBU_CMDS = ["M73", "M991", "M1002", "M622", "M623", "M622.1", "M620", "M621", "M624", "M625",
              "G29", "G29.1", "G29.2", "G29.4", "M975", "M1007", "M17", "M18", "M104", "M109",
              "M140", "M190", "M106", "M204", "G392", "M1006", "M960", "M400", "M83", "G90", "G91", "G17", "G2", "G3", "G380", "M900"]

def load(path):
    return open(path, errors="replace").read().split("\n")

def section(lines, start, end):
    s = next(i for i, l in enumerate(lines) if l.startswith(start))
    e = next(i for i, l in enumerate(lines) if l.startswith(end) and i > s)
    return lines[s:e + 1]

def cmd_counts(lines):
    c = collections.Counter()
    for l in lines:
        t = l.split(";", 1)[0].strip()
        if t: c[t.split()[0]] += 1
    return c

def norm_start(lines):
    # remove números que dependem da área da peça (G29 / linhas de purga), para comparar estrutura
    out = []
    for l in lines:
        t = l.split(";", 1)[0].strip()
        if not t or t.startswith("M73 ") or t == "M106 S0": continue  # progresso / diferença de versão 2.04 x 2.08
        out.append(re.sub(r"[-\d.]+", "#", t))
    return out

def check(ref, cand):
    R, C = load(ref), load(cand)
    ok = True
    def rep(flag, msg):
        nonlocal ok
        ok &= flag
        print(("OK   " if flag else "FALHA") + " " + msg)

    # 1. Estrutura de blocos
    for mk in ["; HEADER_BLOCK_START", "; HEADER_BLOCK_END", "; CONFIG_BLOCK_START", "; CONFIG_BLOCK_END",
               "; EXECUTABLE_BLOCK_START", "; MACHINE_START_GCODE_END", "; MACHINE_END_GCODE_START", "; EXECUTABLE_BLOCK_END"]:
        rep(sum(1 for l in C if l.startswith(mk)) == 1, f"marcador único {mk}")

    # 2. Start/End gcode: mesma sequência de comandos (valores numéricos podem mudar por área de nivelamento)
    rs = norm_start(section(R, "; EXECUTABLE_BLOCK_START", "; MACHINE_START_GCODE_END"))
    cs = norm_start(section(C, "; EXECUTABLE_BLOCK_START", "; MACHINE_START_GCODE_END"))
    rep(rs == cs, f"start G-code com a mesma sequência de comandos ({len(cs)} linhas)")
    re_ = norm_start(section(R, "; MACHINE_END_GCODE_START", "; EXECUTABLE_BLOCK_END"))
    ce = norm_start(section(C, "; MACHINE_END_GCODE_START", "; EXECUTABLE_BLOCK_END"))
    rep(re_ == ce, f"end G-code com a mesma sequência de comandos ({len(ce)} linhas)")

    # 3. Comandos Bambu presentes
    rc, cc = cmd_counts(R), cmd_counts(C)
    missing = [k for k in BAMBU_CMDS if rc[k] > 0 and cc[k] == 0]
    rep(not missing, f"comandos específicos da Bambu presentes (faltando: {missing})")
    rep(cc["M622"] == cc["M623"], f"blocos condicionais balanceados M622={cc['M622']} M623={cc['M623']}")
    rep(cc["M624"] == cc["M625"], f"exclusão de objetos balanceada M624={cc['M624']} M625={cc['M625']}")

    # 4. Camadas, Z, progresso
    layers = sum(1 for l in C if l.startswith("; CHANGE_LAYER"))
    hdr = int(re.search(r"total layer number: (\d+)", "\n".join(C[:12])).group(1))
    rep(layers == hdr, f"camadas no corpo = cabeçalho ({layers})")
    m73l = [int(m.group(1)) for l in C for m in [re.match(r"M73 L(\d+)", l)] if m]
    rep(m73l == list(range(1, hdr + 1)), "M73 L (progresso de camada) sequencial 1..N")
    m73p = [int(m.group(1)) for l in C for m in [re.match(r"M73 P(\d+)", l)] if m]
    rep(all(a <= b for a, b in zip(m73p, m73p[1:])) and m73p[-1] == 100, "M73 P monotônico até 100%")

    # 5. Limites de mesa, Z e extrusão
    x = y = z = 0.0; body = False; rel = True
    xs, ys, zs = [], [], []; ext = 0.0; first_layer = collections.defaultdict(list)
    layer = -1; obj = None; feat = ''; maxz_jump = 0.0; lastz = 0.0
    for l in C:
        if l.startswith("; MACHINE_START_GCODE_END"): body = True
        if l.startswith("; MACHINE_END_GCODE_START"): body = False
        if l.startswith("; CHANGE_LAYER"): layer += 1
        if l.startswith("M624 "): obj = l.split()[1]
        if l.startswith("M625"): obj = None
        if l.startswith("; FEATURE: "): feat = l[11:].strip()
        t = l.split(";", 1)[0].strip()
        if not body or not t.startswith(("G0", "G1", "G2", "G3")): continue
        for k, v in re.findall(r"([XYZE])(-?[\d.]+)", t):
            v = float(v)
            if k == "X": x = v
            elif k == "Y": y = v
            elif k == "Z": z = v
            elif k == "E" and v > 0 and ("X" in t or "Y" in t):
                ext += v; xs.append(x); ys.append(y); zs.append(z)
                if layer == 0 and obj and feat != 'Brim': first_layer[obj].append((x, y))  # brim é agrupado num rótulo só
    rep(min(xs) >= BED[0] and max(xs) <= BED[1] and min(ys) >= BED[0] and max(ys) <= BED[1],
        f"extrusões dentro da mesa X {min(xs):.1f}–{max(xs):.1f} Y {min(ys):.1f}–{max(ys):.1f}")
    print(f"     Z máx de extrusão {max(zs):.2f} mm; filamento extrudado no corpo {ext/1000:.2f} m")

    # 6. Separação entre objetos na 1ª camada
    boxes = {o: (min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts)) for o, pts in first_layer.items()}
    overl = []
    ks = sorted(boxes)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = boxes[ks[i]], boxes[ks[j]]
            if a[0] < b[1] and b[0] < a[1] and a[2] < b[3] and b[2] < a[3]: overl.append((ks[i], ks[j]))
    if boxes:
        gx = min((boxes[b][0] - boxes[a][1]) for a in ks for b in ks if a != b and boxes[b][0] > boxes[a][1] and abs(boxes[b][2]-boxes[a][2]) < 5) if len(ks) > 1 else None
        rep(not overl, f"{len(boxes)} objeto(s) na 1ª camada sem sobreposição de bbox" + (f" (folga mínima em X {gx:.1f} mm)" if gx else ""))

    # 7. Configurações: mostra o que mudou em relação à referência
    def cfg(L):
        d = {}; s = L.index("; CONFIG_BLOCK_START")
        for l in L[s + 1:]:
            if l.startswith("; CONFIG_BLOCK_END"): break
            if " = " in l: k, v = l[2:].split(" = ", 1); d[k] = v
        return d
    a, b = cfg(R), cfg(C)
    diffs = {k: (a.get(k), b.get(k)) for k in set(a) | set(b) if a.get(k) != b.get(k) and len(str(a.get(k))) < 200}
    print("     diferenças de configuração vs referência:")
    for k in sorted(diffs): print(f"       {k}: {diffs[k][0]} -> {diffs[k][1]}")
    print("RESULTADO:", "APROVADO" if ok else "REPROVADO")
    return ok

if __name__ == "__main__":
    sys.exit(0 if check(sys.argv[1], sys.argv[2]) else 1)
