#!/usr/bin/env python3
"""Confere uma variante .3mf contra o original (somente leitura).

Relata:
  * cada arquivo do .3mf: idêntico, alterado, novo ou removido (CRC);
  * diferença das configurações de projeto, chave a chave;
  * itens de montagem (<build>) e instâncias da placa (model_settings);
  * caixa de cada instância na mesa, já com a folga dos suportes;
  * sobreposição entre instâncias e saída da área de impressão.

Uso:
    python3 -I conferir_variante_3mf.py ORIGINAL.3mf VARIANTE.3mf [--folga-suporte X-,X+,Y-,Y+]
"""
import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

CORE = '{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
PROD = '{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
SETTINGS = 'Metadata/project_settings.config'


def entries(z):
    return {i.filename: i for i in z.infolist()}


def settings_diff(a, b):
    ca, cb = json.loads(a), json.loads(b)
    out = []
    for k in sorted(set(ca) | set(cb)):
        if ca.get(k) != cb.get(k):
            out.append((k, ca.get(k), cb.get(k)))
    return out, cb


def build_items(z):
    root = ET.fromstring(z.read('3D/3dmodel.model'))
    items = []
    for it in root.iter(CORE + 'item'):
        t = [float(x) for x in it.get('transform').split()]
        items.append({'objectid': it.get('objectid'), 'uuid': it.get(PROD + 'UUID'),
                      'translacao': t[9:12], 'rotacao': t[:9], 'printable': it.get('printable')})
    return items


def plate_instances(z):
    root = ET.fromstring(z.read('Metadata/model_settings.config'))
    plates = []
    for plate in root.iter('plate'):
        meta = {m.get('key'): m.get('value') for m in plate.findall('metadata')}
        inst = []
        for mi in plate.findall('model_instance'):
            inst.append({m.get('key'): m.get('value') for m in mi.findall('metadata')})
        plates.append({'plater_id': meta.get('plater_id'), 'instancias': inst})
    assemble = [a.attrib for a in root.iter('assemble_item')]
    return plates, assemble


def mesh_xy_bbox(z, path):
    """Caixa XY da malha no sistema do objeto (sem a translação do item)."""
    data = z.read(path)
    xs = [float(v) for v in re.findall(rb'<vertex x="([^"]+)"', data)]
    ys = [float(v) for v in re.findall(rb'<vertex x="[^"]+" y="([^"]+)"', data)]
    return min(xs), max(xs), min(ys), max(ys)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('original')
    ap.add_argument('variante')
    # medido no G-code original (caminhos de extrusão, com largura de linha)
    ap.add_argument('--folga-suporte', default='7.41,0.34,2.57,0.01',
                    help='quanto os suportes passam da malha em X-, X+, Y-, Y+ (mm)')
    ap.add_argument('--mesa', default='0,256,0,256')
    ap.add_argument('--malha-editada', action='store_true',
                    help='a malha foi editada de propósito (editar_malha_3mf.py): não conta como erro')
    args = ap.parse_args()
    ok = True
    za, zb = zipfile.ZipFile(args.original), zipfile.ZipFile(args.variante)
    ea, eb = entries(za), entries(zb)
    print('Arquivos:')
    for name in sorted(set(ea) | set(eb)):
        if name not in eb:
            print(f'  removido   {name}')
        elif name not in ea:
            print(f'  novo       {name}')
        elif ea[name].CRC == eb[name].CRC and ea[name].file_size == eb[name].file_size:
            print(f'  idêntico   {name}')
        else:
            print(f'  ALTERADO   {name}')
    for name in ea:
        if name.startswith('3D/Objects/') and (name not in eb or ea[name].CRC != eb[name].CRC):
            if name in eb and args.malha_editada:
                print(f'  (malha editada de propósito: {name})')
            else:
                print(f'ERRO: malha alterada ou ausente: {name}')
                ok = False

    diff, cfg = settings_diff(za.read(SETTINGS), zb.read(SETTINGS))
    print('\nConfigurações alteradas:')
    for k, old, new in diff:
        print(f'  {k}: {json.dumps(old, ensure_ascii=False)} -> {json.dumps(new, ensure_ascii=False)}')

    items = build_items(zb)
    plates, assemble = plate_instances(zb)
    print(f'\nItens de montagem (<build>): {len(items)}')
    for it in items:
        print(f"  objeto {it['objectid']}  UUID {it['uuid']}  translação {it['translacao']}")
    # O exportador do Bambu Studio grava o UUID do item a partir do objectid
    # (bbs_3mf.cpp, _add_build_to_model_stream): instâncias do mesmo objeto
    # repetem o UUID. Só é erro se objetos diferentes compartilharem um UUID.
    by_uuid = {}
    for it in items:
        by_uuid.setdefault(it['uuid'], set()).add(it['objectid'])
    if any(len(objs) > 1 for objs in by_uuid.values()):
        print('ERRO: objetos diferentes com o mesmo UUID de item')
        ok = False
    for p in plates:
        ids = [i.get('identify_id') for i in p['instancias']]
        print(f"Placa {p['plater_id']}: {len(p['instancias'])} instâncias {p['instancias']}")
        if len(set(ids)) != len(ids):
            print('ERRO: identify_id repetido na placa')
            ok = False
    print(f'Itens de <assemble>: {len(assemble)}')

    # caixas na mesa com a folga dos suportes
    obj_paths = [n for n in eb if n.startswith('3D/Objects/') and n.endswith('.model')]
    if len(obj_paths) == 1 and items:
        x0, x1, y0, y1 = mesh_xy_bbox(zb, obj_paths[0])
        fx0, fx1, fy0, fy1 = (float(v) for v in args.folga_suporte.split(','))
        bx0, bx1, by0, by1 = (float(v) for v in args.mesa.split(','))
        boxes = []
        print('\nCaixa de cada instância na mesa (malha + suportes):')
        for i, it in enumerate(items):
            tx, ty = it['translacao'][:2]
            box = (x0 + tx - fx0, x1 + tx + fx1, y0 + ty - fy0, y1 + ty + fy1)
            boxes.append(box)
            inside = box[0] >= bx0 and box[1] <= bx1 and box[2] >= by0 and box[3] <= by1
            print(f'  {i}: X {box[0]:.1f}–{box[1]:.1f}  Y {box[2]:.1f}–{box[3]:.1f}'
                  f"{'' if inside else '  ERRO: fora da mesa'}")
            ok &= inside
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                gap_x = max(b[0] - a[1], a[0] - b[1])
                gap_y = max(b[2] - a[3], a[2] - b[3])
                gap = max(gap_x, gap_y)
                # entre malhas, o "Organizar" do Bambu reserva 24 mm com suporte em árvore
                mesh_gap = gap + (fx0 + fx1 if gap_x >= gap_y else fy0 + fy1)
                flag = '' if gap >= 5 else '  ERRO: menos de 5 mm'
                note = '' if mesh_gap >= 24 else '  (abaixo dos 24 mm que o Organizar usa)'
                print(f'  folga {i}–{j}: {gap:.1f} mm entre suportes, {mesh_gap:.1f} mm entre malhas'
                      f'{flag}{note}')
                ok &= gap >= 5
    print('\nResultado:', 'OK' if ok else 'COM ERROS')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
