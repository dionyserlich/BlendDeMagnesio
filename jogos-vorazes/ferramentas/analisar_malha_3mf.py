#!/usr/bin/env python3
"""Análise somente leitura da malha e do projeto de um .3mf do Bambu Studio.

Abre o .3mf (zip) só para leitura e informa:
  * se é um projeto editável (malha + configurações) ou se traz G-code
    fatiado (Metadata/plate_N.gcode);
  * perfil de impressora, processo e filamento, e o que difere do perfil
    de sistema;
  * medidas da malha já posicionada na mesa: caixa envolvente, volume,
    área, número de peças soltas e arestas abertas;
  * área de superfície em saliência (faces voltadas para baixo) por faixa
    de ângulo, que indica onde o fatiador precisa de suporte ou
    desacelera as paredes. O ângulo é medido a partir da vertical:
    0° = parede vertical, 90° = face horizontal voltada para baixo.

Uso:
    python3 -I analisar_malha_3mf.py PROJETO.3mf [--json SAIDA.json]
"""
import argparse
import json
import re
import zipfile

import numpy as np

VERT = re.compile(rb'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"')
TRI = re.compile(rb'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"')
ITEM = re.compile(r'<item objectid="(\d+)"[^>]*transform="([^"]+)"')
COMP = re.compile(r'<component p:path="([^"]+)" objectid="(\d+)"[^>]*transform="([^"]+)"')


def matrix(t):
    v = [float(x) for x in t.split()]
    m = np.eye(4)
    m[:3, :3] = np.array(v[:9]).reshape(3, 3).T
    m[:3, 3] = v[9:12]
    return m


def components(n_vertices, tris):
    parent = np.arange(n_vertices)

    def find(a):
        root = a
        while parent[root] != root:
            root = parent[root]
        while parent[a] != root:
            parent[a], a = root, parent[a]
        return root

    for a, b, c in tris.tolist():
        ra = find(a)
        for v in (b, c):
            rv = find(v)
            if rv != ra:
                parent[rv] = ra
    roots = {find(i) for i in np.unique(tris).tolist()}
    return len(roots)


def analyze(path):
    out = {'arquivo': path}
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        out['conteudo'] = names
        gcodes = [n for n in names if n.lower().endswith('.gcode')]
        out['tem_gcode_fatiado'] = bool(gcodes)
        out['tem_configuracao_de_projeto'] = 'Metadata/project_settings.config' in names
        cfg = json.loads(z.read('Metadata/project_settings.config'))
        out['perfis'] = {k: cfg.get(k) for k in (
            'printer_settings_id', 'print_settings_id', 'filament_settings_id',
            'different_settings_to_system', 'version')}
        root = z.read('3D/3dmodel.model').decode('utf-8')
        items = ITEM.findall(root)
        comps = COMP.findall(root)
        meshes = []
        for obj_id, item_t in items:
            M_item = matrix(item_t)
            for comp_path, _cid, comp_t in comps:
                data = z.read(comp_path.lstrip('/'))
                V = np.array(VERT.findall(data), dtype=float)
                T = np.array(TRI.findall(data), dtype=np.int64)
                M = M_item @ matrix(comp_t)
                Vh = np.c_[V, np.ones(len(V))] @ M.T
                meshes.append((Vh[:, :3], T))
    V, T = meshes[0]
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    cr = np.cross(b - a, c - a)
    area_f = 0.5 * np.linalg.norm(cr, axis=1)
    volume = np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6.0
    nz = np.where(area_f > 0, cr[:, 2] / np.maximum(2 * area_f, 1e-12), 0)
    # ângulo da face em relação ao plano da mesa, só para faces voltadas para baixo
    down = nz < 0
    ang = np.degrees(np.arcsin(np.clip(-nz, 0, 1)))  # 90 = face horizontal para baixo
    zc = (a[:, 2] + b[:, 2] + c[:, 2]) / 3
    bands = {}
    for lo, hi in ((0, 30), (30, 45), (45, 60), (60, 75), (75, 90.01)):
        sel = down & (ang >= lo) & (ang < hi) & (zc > 0.3)
        bands[f'{lo}-{int(hi)}°'] = round(float(area_f[sel].sum()), 1)
    edges = np.sort(np.r_[T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]], axis=1)
    _, cnt = np.unique(edges, axis=0, return_counts=True)
    first_layer = (zc < 0.2) & (nz < -0.99)
    out['malha'] = {
        'vertices': int(len(V)),
        'triangulos': int(len(T)),
        'bbox_min_mm': [round(float(x), 3) for x in V.min(axis=0)],
        'bbox_max_mm': [round(float(x), 3) for x in V.max(axis=0)],
        'dimensoes_mm': [round(float(x), 3) for x in V.max(axis=0) - V.min(axis=0)],
        'volume_mm3': round(float(volume), 1),
        'area_superficie_mm2': round(float(area_f.sum()), 1),
        'area_media_triangulo_mm2': round(float(area_f.mean()), 5),
        'aresta_media_mm': round(float(np.sqrt(area_f.mean() * 4 / np.sqrt(3))), 4),
        'pecas_soltas': components(len(V), T),
        'arestas_abertas': int((cnt == 1).sum()),
        'arestas_com_mais_de_2_faces': int((cnt > 2).sum()),
        'area_apoiada_na_mesa_mm2': round(float(area_f[first_layer].sum()), 2),
        'area_em_saliencia_por_angulo_mm2': bands,
    }
    # perfil de seção por altura (área projetada aproximada pelo volume de cada fatia)
    zmin, zmax = V[:, 2].min(), V[:, 2].max()
    out['malha']['altura_mm'] = round(float(zmax - zmin), 3)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('arquivo_3mf')
    ap.add_argument('--json')
    args = ap.parse_args()
    r = analyze(args.arquivo_3mf)
    print(json.dumps({k: v for k, v in r.items() if k != 'conteudo'}, ensure_ascii=False, indent=1))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
