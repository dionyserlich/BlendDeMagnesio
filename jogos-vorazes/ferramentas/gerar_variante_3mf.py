#!/usr/bin/env python3
"""Gera uma variante de um projeto .3mf do Bambu Studio sem tocar na malha.

O original só é lido. A variante é um arquivo novo, com as mesmas entradas
na mesma ordem e com a mesma compressão. Só três arquivos internos podem
mudar:
  * Metadata/project_settings.config: recebe só as chaves pedidas em
    --processo e --filamento, com a mesma formatação. A chave também é
    acrescentada a "different_settings_to_system" (posição 0 = processo,
    1 = filamento), em ordem alfabética, como a interface faz. Sem isso, o
    Bambu Studio volta a chave ao valor do perfil de sistema ao abrir o
    projeto (Preset.cpp, update_non_diff_values_to_base_config);
  * 3D/3dmodel.model e Metadata/model_settings.config: com --instancias, o
    único objeto passa a ter N instâncias na placa 1, nas posições X,Y
    dadas. Z e rotação ficam como no original. É o formato que o exportador
    do Bambu Studio 02.08.02.60 grava: um <item> por instância com o mesmo
    objectid e um <model_instance> por instância.

A malha (3D/Objects/*.model) e todo o resto são copiados byte a byte.

Uso:
    python3 -I gerar_variante_3mf.py ORIGINAL.3mf SAIDA.3mf \\
        --processo default_acceleration=6000 --processo wall_generator=arachne \\
        --filamento cooling_slowdown_logic=consistent_surface \\
        --instancias 77.4,128 113.4,128 149.4,128 185.4,128
"""
import argparse
import json
import os
import re
import sys
import zipfile

SETTINGS = 'Metadata/project_settings.config'
MODEL = '3D/3dmodel.model'
MODEL_SETTINGS = 'Metadata/model_settings.config'

ITEM_RE = re.compile(r'( *)<item objectid="(\d+)" ([^>]*?)transform="([^"]+)"([^>]*)/>\n')
INSTANCE_RE = re.compile(r'( *)<model_instance>\n.*?</model_instance>\n', re.S)


def edit_settings(raw, process, filament):
    """Aplica as edições. Devolve (JSON em bytes, lista de mudanças)."""
    cfg = json.loads(raw)
    changes = []
    diff = cfg.get('different_settings_to_system')
    for group, edits in ((0, process), (1, filament)):
        for key, value in edits:
            if key not in cfg:
                sys.exit(f'chave inexistente no projeto: {key}')
            old = cfg[key]
            new = [value] * len(old) if isinstance(old, list) else value
            if new == old:
                continue
            cfg[key] = new
            changes.append((key, old, new))
            if diff is not None:
                keys = [k for k in diff[group].split(';') if k]
                if key not in keys:
                    diff[group] = ';'.join(sorted(keys + [key]))
    return json.dumps(cfg, indent=4, ensure_ascii=False).encode('utf-8') + b'\n', changes


def fmt(v):
    """Número no formato do exportador: decimal simples, sem zeros à direita."""
    s = f'{v:.9g}'
    if 'e' in s:
        s = f'{v:.6f}'.rstrip('0').rstrip('.')
    return s


def set_instances(model_xml, settings_xml, positions):
    """Reescreve <build> e as instâncias da placa para N posições X,Y."""
    model = model_xml.decode('utf-8')
    items = ITEM_RE.findall(model)
    if len(items) != 1:
        sys.exit(f'esperado 1 item no <build>, encontrados {len(items)}')
    indent, objectid, before, transform, after = items[0]
    t = transform.split()
    if len(t) != 12:
        sys.exit('transformação inesperada no item original')
    new_items = []
    for x, y in positions:
        tt = t[:9] + [fmt(x), fmt(y), t[11]]
        new_items.append(f'{indent}<item objectid="{objectid}" {before}transform="{" ".join(tt)}"{after}/>\n')
    model = ITEM_RE.sub(lambda m: ''.join(new_items), model, count=1)

    st = settings_xml.decode('utf-8')
    full = INSTANCE_RE.search(st)
    if full is None or len(INSTANCE_RE.findall(st)) != 1:
        sys.exit('esperado 1 <model_instance> na placa original')
    block = full.group(0)
    ident = int(re.search(r'key="identify_id" value="(\d+)"', block).group(1))
    if re.search(r'key="object_id" value="(\d+)"', block).group(1) != objectid:
        sys.exit('model_instance não corresponde ao objeto do <build>')
    new_blocks = []
    for i in range(len(positions)):
        b = re.sub(r'(key="instance_id" value=)"\d+"', rf'\1"{i}"', block)
        b = re.sub(r'(key="identify_id" value=)"\d+"', rf'\1"{ident + i}"', b)
        new_blocks.append(b)
    st = st[:full.start()] + ''.join(new_blocks) + st[full.end():]
    return model.encode('utf-8'), st.encode('utf-8')


def parse_kv(items):
    out = []
    for it in items or []:
        if '=' not in it:
            sys.exit(f'use chave=valor: {it}')
        k, v = it.split('=', 1)
        out.append((k.strip(), v.strip()))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('original')
    ap.add_argument('saida')
    ap.add_argument('--processo', action='append', help='chave=valor do processo (repetível)')
    ap.add_argument('--filamento', action='append', help='chave=valor do filamento (repetível)')
    ap.add_argument('--instancias', nargs='+', metavar='X,Y',
                    help='posição X,Y de cada instância na placa 1 (mm)')
    args = ap.parse_args()
    if os.path.abspath(args.original) == os.path.abspath(args.saida):
        sys.exit('a saída não pode ser o próprio original')
    if os.path.exists(args.saida):
        sys.exit(f'{args.saida} já existe; apague antes de gerar de novo')

    positions = None
    if args.instancias:
        positions = [tuple(float(v) for v in p.split(',')) for p in args.instancias]

    zin = zipfile.ZipFile(args.original)
    replaced = {}
    replaced[SETTINGS], changes = edit_settings(zin.read(SETTINGS), parse_kv(args.processo),
                                                parse_kv(args.filamento))
    if positions:
        replaced[MODEL], replaced[MODEL_SETTINGS] = set_instances(
            zin.read(MODEL), zin.read(MODEL_SETTINGS), positions)

    with zipfile.ZipFile(args.saida, 'w') as zout:
        for info in zin.infolist():
            data = replaced.get(info.filename)
            if data is None:
                data = zin.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zout.writestr(zi, data)

    print(f'Gerado: {args.saida}')
    for key, old, new in changes:
        print(f'  {key}: {json.dumps(old, ensure_ascii=False)} -> {json.dumps(new, ensure_ascii=False)}')
    if positions:
        print(f'  {len(positions)} instâncias: ' + '; '.join(f'({fmt(x)}, {fmt(y)})' for x, y in positions))


if __name__ == '__main__':
    main()
