"""Gera um 3MF com N instâncias da mesma peça em grade (cópia; o original não muda).
Uso: python3 -I batch3mf.py entrada.3mf saida.3mf COLS ROWS PITCH_X PITCH_Y [overrides.json]
As instâncias compartilham o mesmo objeto (mesma malha), como "Clonar" no Bambu Studio."""
import sys, re, json, zipfile

src, dst = sys.argv[1], sys.argv[2]
cols, rows = int(sys.argv[3]), int(sys.argv[4])
px, py = float(sys.argv[5]), float(sys.argv[6])
overrides = json.load(open(sys.argv[7])) if len(sys.argv) > 7 else {}
BED = 256.0

zi = zipfile.ZipFile(src)
model = zi.read("3D/3dmodel.model").decode()
ms = zi.read("Metadata/model_settings.config").decode()

item_re = re.compile(r'(<item objectid="2" p:UUID=")([^"]+)(" transform="1 0 0 0 1 0 0 0 1 )([-\d.]+) ([-\d.]+) ([-\d.]+)(" printable="1"/>)')
m = item_re.search(model)
assert m, "item não encontrado"
x0, y0, z0 = float(m.group(4)), float(m.group(5)), m.group(6)
# centro da grade no centro da mesa (o item original está em 118,128: centro do bbox ~ mesa)
cx, cy = BED / 2 - 10, BED / 2  # mesmo deslocamento X do original (118 vs 128)
cx = x0; cy = y0
xs = [cx + (i - (cols - 1) / 2) * px for i in range(cols)]
ys = [cy + (j - (rows - 1) / 2) * py for j in range(rows)]
items, insts = [], []
k = 0
for j, y in enumerate(ys):
    for i, x in enumerate(xs):
        uuid = "%08x-b1ec-4553-aec9-835e5b724bb4" % (0x00000002 + (k << 16))
        items.append(f'{m.group(1)}{uuid}{m.group(3)}{x:.4f} {y:.4f} {z0}{m.group(7)}')
        insts.append(f'    <model_instance>\n      <metadata key="object_id" value="2"/>\n      <metadata key="instance_id" value="{k}"/>\n      <metadata key="identify_id" value="{1000 + k}"/>\n    </model_instance>')
        k += 1
model2 = model[:m.start()] + "\n  ".join(items) + model[m.end():]
inst_re = re.compile(r'    <model_instance>.*?</model_instance>', re.S)
assert len(inst_re.findall(ms)) == 1
ms2 = inst_re.sub(lambda _: "\n".join(insts), ms)
# assemble: uma entrada por instância
asm_re = re.compile(r'(   <assemble_item object_id="2" instance_id="0" [^\n]*\n)')
am = asm_re.search(ms2)
if am:
    line = am.group(1)
    ms2 = ms2.replace(line, "".join(line.replace('instance_id="0"', f'instance_id="{i}"') for i in range(k)))

with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zo:
    for it in zi.infolist():
        data = zi.read(it.filename)
        if it.filename == "3D/3dmodel.model": data = model2.encode()
        elif it.filename == "Metadata/model_settings.config": data = ms2.encode()
        elif it.filename == "Metadata/project_settings.config" and overrides:
            cfg = json.loads(data)
            for kk, v in overrides.items():
                old = cfg.get(kk)
                cfg[kk] = [v] if isinstance(old, list) and not isinstance(v, list) else v
            data = json.dumps(cfg, indent=4, ensure_ascii=False).encode()
        elif it.filename == "Metadata/plate_1.json":
            continue  # bbox antigo; o slicer regenera
        zo.writestr(it, data)
print(f"{k} instâncias; X={[round(v,1) for v in xs]} Y={[round(v,1) for v in ys]}")
