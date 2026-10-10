"""Cria uma cópia do 3MF com overrides em project_settings.config, fatia com o
Bambu Studio CLI e resume tempos.  Uso:
  python3 -I variant.py NOME base.3mf '{"chave": "valor", ...}' [--clone N]
O 3MF original nunca é modificado."""
import sys, os, json, zipfile, subprocess, re, shutil

S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = "/home/user/bambulab/bs"

def make_variant(src, dst, overrides, extra_files=None):
    with zipfile.ZipFile(src) as zi, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in zi.infolist():
            data = zi.read(it.filename)
            if it.filename == "Metadata/project_settings.config" and overrides:
                cfg = json.loads(data)
                for k, v in overrides.items():
                    if k not in cfg:
                        print(f"  aviso: chave nova {k}")
                    old = cfg.get(k)
                    cfg[k] = [v] if isinstance(old, list) and not isinstance(v, list) else v
                data = json.dumps(cfg, indent=4, ensure_ascii=False).encode()
            if extra_files and it.filename in extra_files:
                data = extra_files.pop(it.filename)
            zo.writestr(it, data)
        for name, data in (extra_files or {}).items():
            zo.writestr(name, data)

def header(gcode):
    h = {}
    with open(gcode, errors="replace") as f:
        for _ in range(12):
            line = f.readline()
            m = re.search(r"model printing time: (.*?); total estimated time: (.*)", line)
            if m: h["model"], h["total"] = m.group(1), m.group(2).strip()
            m = re.search(r"total layer number: (\d+)", line)
            if m: h["layers"] = int(m.group(1))
            m = re.search(r"total filament weight \[g\] : ([\d.]+)", line)
            if m: h["g"] = float(m.group(1))
    return h

def run(name, src, overrides, clone=None, extra_files=None, arrange=None):
    d = os.path.join(S, "run", name)
    shutil.rmtree(d, ignore_errors=True) if os.path.isdir(d) and d.startswith(os.path.join(S, "run")) else None
    os.makedirs(d, exist_ok=True)
    v3mf = os.path.join(d, "input.3mf")
    make_variant(src, v3mf, overrides, dict(extra_files or {}))
    cmd = [BS, "--debug", "2", "--allow-newer-file", "--slice", "0", "--outputdir", d, "--export-3mf", "out.3mf"]
    if clone: cmd += ["--clone-objects", str(clone)]
    if arrange is not None: cmd += ["--arrange", str(arrange)]
    cmd.append(v3mf)
    with open(os.path.join(d, "log.txt"), "w") as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=d)
    res = json.load(open(os.path.join(d, "result.json")))
    plate = res.get("sliced_plates", [{}])[0]
    g = os.path.join(d, "plate_1.gcode")
    h = header(g) if os.path.exists(g) else {}
    out = dict(name=name, rc=res.get("return_code"), err=res.get("error_string"),
               model_s=plate.get("main_predication"), total_s=plate.get("total_predication"),
               g=h.get("g"), layers=h.get("layers"), hdr_total=h.get("total"),
               warn=plate.get("warning_message"), objects=len(plate.get("objects", [])))
    json.dump(out, open(os.path.join(d, "summary.json"), "w"), indent=1)
    print(json.dumps(out, ensure_ascii=False))
    return out

if __name__ == "__main__":
    a = sys.argv[1:]
    clone = None; arrange = None
    if "--clone" in a:
        i = a.index("--clone"); clone = a[i + 1]; del a[i:i + 2]
    if "--arrange" in a:
        i = a.index("--arrange"); arrange = a[i + 1]; del a[i:i + 2]
    run(a[0], a[1], json.loads(a[2]) if len(a) > 2 else {}, clone, arrange=arrange)
