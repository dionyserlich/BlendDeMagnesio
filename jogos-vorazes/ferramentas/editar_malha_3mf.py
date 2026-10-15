#!/usr/bin/env python3
"""Edita a malha de um projeto .3mf do Bambu Studio com operações booleanas.

O original só é lido. A variante é um arquivo novo, com as mesmas entradas
na mesma ordem e com a mesma compressão. Muda só:
  * 3D/Objects/object_*.model: a malha, depois das operações pedidas;
  * Metadata/model_settings.config: a contagem de faces (face_count).

As operações vêm de um JSON, em coordenadas da malha (sem a translação do
item na mesa):
  [
    {"op": "subtrair_cilindro", "p0": [x,y,z], "p1": [x,y,z], "diametro": 0.95,
     "segmentos": 64, "nome": "furo cabeça 1"},
    {"op": "subtrair_casco", "pontos": [[x,y,z], ...], "nome": "saliência"}
  ]
"subtrair_casco" subtrai o fecho convexo dos pontos dados.

Depois das operações o script confere:
  * a malha continua fechada e válida (status do manifold3d) e com o mesmo
    genus;
  * os vértices fora das caixas das operações (com folga) são os mesmos do
    original, posição por posição, ou seja, nada mudou fora das edições;
  * volume removido em cada operação.

Requer numpy e manifold3d (pip install manifold3d).

Uso:
    python3 -I editar_malha_3mf.py ORIGINAL.3mf SAIDA.3mf --edicoes edicoes.json
"""
import argparse
import json
import os
import re
import sys
import zipfile

import numpy as np

try:
    import manifold3d as m3
except ImportError:  # pragma: no cover
    sys.exit('instale o manifold3d: pip install manifold3d')

VERT = re.compile(rb'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"/>')
TRI = re.compile(rb'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"')
MODEL_SETTINGS = 'Metadata/model_settings.config'


def read_mesh(data):
    V = np.array(VERT.findall(data), dtype=np.float64).astype(np.float32)
    T = np.array(TRI.findall(data), dtype=np.uint32)
    head = data[:data.index(b'<vertices>') + len(b'<vertices>\n')]
    tail = data[data.index(b'    </triangles>'):]
    return V, T, head, tail


def write_mesh(V, T, head, tail):
    parts = [head]
    parts.append(''.join(f'     <vertex x="{x:.9g}" y="{y:.9g}" z="{z:.9g}"/>\n'
                         for x, y, z in V.tolist()).encode())
    parts.append(b'    </vertices>\n    <triangles>\n')
    parts.append(''.join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>\n'
                         for a, b, c in T.tolist()).encode())
    parts.append(tail)
    return b''.join(parts)


def cylinder(p0, p1, diameter, segments):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    axis = p1 - p0
    length = float(np.linalg.norm(axis))
    cyl = m3.Manifold.cylinder(length, diameter / 2, diameter / 2, int(segments), False)
    d = axis / length
    # rotação que leva o eixo Z ao eixo pedido
    z = np.array([0.0, 0.0, 1.0])
    v = np.cross(z, d)
    s, c = np.linalg.norm(v), float(np.dot(z, d))
    if s < 1e-12:
        Rm = np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        Rm = np.eye(3) + vx + vx @ vx * ((1 - c) / s ** 2)
    M = np.hstack([Rm, p0.reshape(3, 1)])
    return cyl.transform(M.tolist())


def tool_solid(op):
    if op['op'] == 'subtrair_cilindro':
        return cylinder(op['p0'], op['p1'], float(op['diametro']), op.get('segmentos', 64))
    if op['op'] == 'subtrair_casco':
        return m3.Manifold.hull_points([list(map(float, p)) for p in op['pontos']])
    sys.exit(f"operação desconhecida: {op['op']}")


def bbox_of(solid, margin):
    lo, hi = solid.bounding_box()[:3], solid.bounding_box()[3:]
    return np.array(lo) - margin, np.array(hi) + margin


def outside(V, boxes):
    mask = np.ones(len(V), dtype=bool)
    for lo, hi in boxes:
        inside = np.all((V >= lo) & (V <= hi), axis=1)
        mask &= ~inside
    return mask


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('original')
    ap.add_argument('saida')
    ap.add_argument('--edicoes', required=True, help='JSON com a lista de operações')
    ap.add_argument('--folga', type=float, default=0.5,
                    help='folga (mm) em volta de cada operação para a conferência de vértices')
    args = ap.parse_args()
    if os.path.abspath(args.original) == os.path.abspath(args.saida):
        sys.exit('a saída não pode ser o próprio original')
    if os.path.exists(args.saida):
        sys.exit(f'{args.saida} já existe; apague antes de gerar de novo')
    ops = json.load(open(args.edicoes, encoding='utf-8'))

    zin = zipfile.ZipFile(args.original)
    objs = [n for n in zin.namelist() if n.startswith('3D/Objects/') and n.endswith('.model')]
    if len(objs) != 1:
        sys.exit(f'esperado 1 arquivo de malha, encontrados {objs}')
    obj_name = objs[0]
    V0, T0, head, tail = read_mesh(zin.read(obj_name))
    man = m3.Manifold(m3.Mesh(vert_properties=V0, tri_verts=T0))
    if man.status() != m3.Error.NoError:
        sys.exit(f'malha original inválida: {man.status()}')
    genus0, vol0 = man.genus(), man.volume()
    print(f'Original: {len(V0)} vértices, {len(T0)} triângulos, volume {vol0:.2f} mm³, genus {genus0}')

    boxes = []
    for op in ops:
        solid = tool_solid(op)
        before = man.volume()
        man = man - solid
        removed = before - man.volume()
        boxes.append(bbox_of(solid, args.folga))
        print(f"  {op.get('nome', op['op'])}: removidos {removed:.4f} mm³")
        if removed <= 0:
            sys.exit('operação não removeu material: confira as coordenadas (são da malha, não da mesa)')

    if man.status() != m3.Error.NoError:
        sys.exit(f'malha resultante inválida: {man.status()}')
    if man.genus() != genus0:
        sys.exit(f'o genus mudou ({genus0} -> {man.genus()}): uma edição atravessou a peça')
    out = man.to_mesh()
    V1 = np.asarray(out.vert_properties, dtype=np.float32)[:, :3]
    T1 = np.asarray(out.tri_verts, dtype=np.uint32)

    # nada pode mudar fora das caixas das operações
    def keyset(V):
        return {tuple(v) for v in V.tolist()}
    o0, o1 = keyset(V0[outside(V0, boxes)]), keyset(V1[outside(V1, boxes)])
    if o0 != o1:
        sys.exit(f'vértices fora das edições mudaram: {len(o0 ^ o1)} diferenças')
    print(f'Resultado: {len(V1)} vértices, {len(T1)} triângulos, volume {man.volume():.2f} mm³, '
          f'genus {man.genus()}; {len(o0)} vértices fora das edições idênticos ao original')

    new_obj = write_mesh(V1, T1, head, tail)
    settings = zin.read(MODEL_SETTINGS).decode('utf-8')
    settings = re.sub(r'face_count="\d+"', f'face_count="{len(T1)}"', settings)
    replaced = {obj_name: new_obj, MODEL_SETTINGS: settings.encode('utf-8')}
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


if __name__ == '__main__':
    main()
