#!/usr/bin/env python3
"""Confere se um G-code corresponde à malha de um .3mf e se perdeu detalhes.

Somente leitura. Para camadas amostradas:
  * corta a malha no meio da camada;
  * mede a distância de cada ponto da parede externa do G-code até o
    contorno da malha (o esperado é meia largura de linha, ~0,21 mm);
  * procura trechos do contorno da malha sem nenhuma extrusão por perto
    (> limite). São detalhes finos que o fatiador descartou.

O deslocamento em X/Y entre a posição no .3mf e no G-code é detectado
alinhando as caixas envolventes.

Com --ilhas, também lista, camada a camada, as ilhas pequenas da malha
(seções isoladas com área até --area-max, como pontas de presas e bicos)
e se o G-code extrude algo sobre elas.

Uso:
    python3 -I comparar_gcode_malha.py PROJETO.3mf ARQUIVO.gcode [--passo 4] [--limite 1.0]
        [--ilhas] [--area-max 2.0]
"""
import argparse
import math
import os
import sys
import zipfile
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analisar_malha_3mf as M  # noqa: E402


def load_mesh(path):
    with zipfile.ZipFile(path) as z:
        root = z.read('3D/3dmodel.model').decode('utf-8')
        item_t = M.ITEM.findall(root)[0][1]
        comp_path, _cid, comp_t = M.COMP.findall(root)[0]
        data = z.read(comp_path.lstrip('/'))
    V = np.array(M.VERT.findall(data), dtype=float)
    T = np.array(M.TRI.findall(data), dtype=np.int64)
    mat = M.matrix(item_t) @ M.matrix(comp_t)
    V = (np.c_[V, np.ones(len(V))] @ mat.T)[:, :3]
    return V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]


def gcode_points(path, step=0.3):
    """Pontos de extrusão por camada (densificados), separados por tipo."""
    outer = defaultdict(list)
    model = defaultdict(list)
    x = y = 0.0
    z_layer = None
    feature = None
    started = False
    with open(path, encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            s = raw.strip()
            if not s:
                continue
            if s[0] == ';':
                if s.startswith('; MACHINE_START_GCODE_END'):
                    started = True
                elif s.startswith('; MACHINE_END_GCODE_START'):
                    break
                elif s.startswith('; Z_HEIGHT:'):
                    z_layer = float(s.split(':')[1])
                elif s.startswith('; FEATURE:'):
                    feature = s.split(':', 1)[1].strip()
                continue
            if not started:
                continue
            w = s.split(';')[0].split()
            if not w or w[0] not in ('G1', 'G2', 'G3'):
                continue
            p = {t[0]: float(t[1:]) for t in w[1:] if len(t) > 1 and t[0] in 'XYEIJ'}
            nx, ny = p.get('X', x), p.get('Y', y)
            if p.get('E', 0) > 0 and feature and 'Support' not in feature:
                if w[0] == 'G1':
                    n = max(1, int(math.hypot(nx - x, ny - y) / step))
                    pts = [(x + (nx - x) * k / n, y + (ny - y) * k / n) for k in range(1, n + 1)]
                else:
                    cx, cy = x + p.get('I', 0.0), y + p.get('J', 0.0)
                    r = math.hypot(x - cx, y - cy)
                    a0 = math.atan2(y - cy, x - cx)
                    a1 = math.atan2(ny - cy, nx - cx)
                    da = (a0 - a1) if w[0] == 'G2' else (a1 - a0)
                    if da <= 1e-9:
                        da += 2 * math.pi
                    n = max(1, int(r * da / step))
                    sgn = -1 if w[0] == 'G2' else 1
                    pts = [(cx + r * math.cos(a0 + sgn * da * k / n),
                            cy + r * math.sin(a0 + sgn * da * k / n)) for k in range(1, n + 1)]
                model[z_layer].extend(pts)
                if feature in ('Outer wall', 'Overhang wall'):
                    outer[z_layer].extend(pts)
            x, y = nx, ny
    return outer, model


def slice_mesh(a, b, c, zq):
    za, zb, zc = a[:, 2], b[:, 2], c[:, 2]
    sel = (np.minimum(np.minimum(za, zb), zc) < zq) & (np.maximum(np.maximum(za, zb), zc) > zq)
    P = np.stack([a[sel], b[sel], c[sel]], axis=1)
    segs = []
    for tri in P:
        q = []
        for i in range(3):
            p1, p2 = tri[i], tri[(i + 1) % 3]
            if (p1[2] - zq) * (p2[2] - zq) < 0:
                t = (zq - p1[2]) / (p2[2] - p1[2])
                q.append(p1[:2] + t * (p2[:2] - p1[:2]))
        if len(q) == 2:
            segs.append(q)
    return np.array(segs)


def loops(S):
    """Liga os segmentos do corte em laços fechados; devolve [(pontos, área)]."""
    key = lambda p: (round(float(p[0]), 5), round(float(p[1]), 5))  # noqa: E731
    adj = defaultdict(list)
    for i, (p, q) in enumerate(S):
        adj[key(p)].append((i, 1))
        adj[key(q)].append((i, 0))
    used, out = set(), []
    for i in range(len(S)):
        if i in used:
            continue
        pts = [S[i][0], S[i][1]]
        used.add(i)
        cur = key(S[i][1])
        while True:
            nxt = [(j, e) for j, e in adj[cur] if j not in used]
            if not nxt:
                break
            j, e = nxt[0]
            used.add(j)
            pts.append(S[j][e])
            cur = key(S[j][e])
        L = np.array(pts)
        area = 0.5 * abs(np.dot(L[:-1, 0], L[1:, 1]) - np.dot(L[1:, 0], L[:-1, 1]))
        out.append((L, area))
    return out


def point_to_segments(P, S, chunk=400):
    A, B = S[:, 0], S[:, 1]
    AB = B - A
    L2 = (AB ** 2).sum(1) + 1e-12
    out = np.empty(len(P))
    for k in range(0, len(P), chunk):
        p = P[k:k + chunk, None, :]
        t = np.clip(((p - A) * AB).sum(2) / L2, 0, 1)
        proj = A + t[..., None] * AB
        out[k:k + chunk] = np.sqrt(((proj - p) ** 2).sum(2)).min(1)
    return out


def nearest(P, Q, chunk=500):
    out = np.empty(len(P))
    for k in range(0, len(P), chunk):
        d = ((P[k:k + chunk, None, :] - Q[None, :, :]) ** 2).sum(2)
        out[k:k + chunk] = np.sqrt(d.min(1))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('arquivo_3mf')
    ap.add_argument('gcode')
    ap.add_argument('--passo', type=int, default=4, help='analisa 1 a cada N camadas')
    ap.add_argument('--limite', type=float, default=1.0,
                    help='distância (mm) acima da qual o contorno é considerado sem extrusão')
    ap.add_argument('--ilhas', action='store_true',
                    help='lista as ilhas pequenas da malha em todas as camadas e se foram impressas')
    ap.add_argument('--area-max', type=float, default=2.0,
                    help='área máxima (mm²) de uma ilha pequena')
    args = ap.parse_args()

    a, b, c = load_mesh(args.arquivo_3mf)
    outer, model = gcode_points(args.gcode)
    allv = np.r_[a, b, c]
    og = np.array([p for pts in outer.values() for p in pts])
    # centro a centro: o recuo da parede externa (~0,21 mm) se cancela
    shift = (og.min(0) + og.max(0)) / 2 - (allv[:, :2].min(0) + allv[:, :2].max(0)) / 2
    shift = np.round(shift, 1)
    print(f'Deslocamento detectado (G-code − 3MF): X {shift[0]:+.1f} mm, Y {shift[1]:+.1f} mm')

    zs = sorted(z for z in outer if z is not None)
    fwd_all = []
    missing = []
    for zl in zs[::args.passo]:
        S = slice_mesh(a, b, c, zl - 0.08)
        if len(S) == 0:
            continue
        P = np.array(outer[zl]) - shift
        fwd_all.append(point_to_segments(P[::2], S))
        mids = S.mean(1)
        Q = np.array(model[zl]) - shift
        d = nearest(mids, Q)
        far = mids[d > args.limite]
        if len(far):
            missing.append((zl, len(far), float(d.max()), far.min(0), far.max(0)))
    fwd = np.concatenate(fwd_all)
    print(f'Parede externa → malha: mediana {np.median(fwd):.3f} mm, '
          f'p95 {np.percentile(fwd, 95):.3f} mm, '
          f'{100 * (fwd > 0.45).mean():.2f}% dos pontos a mais de 0,45 mm')
    print(f'Camadas com contorno sem extrusão a mais de {args.limite} mm: {len(missing)}')
    for zl, n, dmax, lo, hi in missing:
        if n >= 5:
            print(f'  z={zl:6.2f}  trechos={n:3d}  distância máx {dmax:4.2f} mm  '
                  f'região X {lo[0]:.1f}–{hi[0]:.1f}  Y {lo[1]:.1f}–{hi[1]:.1f} (coordenadas do 3MF)')

    if args.ilhas:
        # ilha "impressa" = metade ou mais do contorno a até 0,6 mm de alguma extrusão
        total = falta = 0
        area_falta = 0.0
        print(f'\nIlhas pequenas (0,01 a {args.area_max} mm²), todas as camadas:')
        for zl in zs:
            S = slice_mesh(a, b, c, zl - 0.08)
            if len(S) == 0:
                continue
            Q = np.array(model[zl]) - shift
            for L, area in loops(S):
                if not 0.01 < area <= args.area_max:
                    continue
                total += 1
                printed = (nearest(L, Q) <= 0.6).mean() >= 0.5 if len(Q) else False
                if not printed:
                    falta += 1
                    area_falta += area
                    cx, cy = L[:, 0].mean(), L[:, 1].mean()
                    print(f'  z={zl:6.2f}  ilha {area:.3f} mm² em ({cx:.1f}, {cy:.1f})  NÃO impressa')
        print(f'Ilhas pequenas: {total}; não impressas: {falta} '
              f'(soma das áreas: {area_falta:.2f} mm² × camada)')


if __name__ == '__main__':
    main()
