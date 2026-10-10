#!/usr/bin/env python3
"""Análise somente leitura de G-code do Bambu Studio (Bambu Lab A1).

O G-code de entrada só é aberto para leitura. Nada é reescrito.

O que o script faz:
  * lê o cabeçalho e o CONFIG_BLOCK (configuração usada no fatiamento);
  * refaz o tempo de cada movimento com um planejador trapezoidal com
    junções por jerk. É o mesmo modelo do GCodeProcessor do Bambu Studio
    e do PrusaSlicer: aceleração por M204, limites de velocidade,
    aceleração e jerk da máquina, look-ahead para frente e para trás;
  * separa os blocos condicionais (SKIPPABLE: timelapse e detecção de
    bico enrolado). O firmware só executa esses blocos se a opção estiver
    ligada na impressora;
  * soma tempo, comprimento e volume por tipo de linha (FEATURE) e por
    camada; conta deslocamentos, retrações e z-hops;
  * calcula de novo o tempo com as velocidades nominais, sem a redução
    feita para cumprir o tempo mínimo de camada. A diferença é o tempo
    gasto esperando o resfriamento;
  * projeta o tempo por unidade com N cópias na mesma mesa.

Uso:
    python3 -I analisar_gcode.py ARQUIVO.gcode [--json SAIDA.json]
"""
import argparse
import json
import math
import re
from collections import defaultdict

AXES = 'XYZE'
WORD = re.compile(r'([A-Za-z])\s*(-?\d*\.?\d+(?:[eE][-+]?\d+)?)')

# Tipos de linha que o resfriamento desacelera e cuja velocidade nominal
# pode ser calculada a partir da configuração.
SPEED_KEYS = {
    'Outer wall': 'outer_wall_speed',
    'Inner wall': 'inner_wall_speed',
    'Sparse infill': 'sparse_infill_speed',
    'Internal solid infill': 'internal_solid_infill_speed',
    'Floating vertical shell': 'internal_solid_infill_speed',
    'Top surface': 'top_surface_speed',
    'Gap infill': 'gap_infill_speed',
    'Support': 'support_speed',
    'Support interface': 'support_interface_speed',
}
# Tipos de linha usados para medir o fator de desaceleração da camada
# (a velocidade nominal deles não depende de saliência).
REFERENCE_FEATURES = ('Sparse infill', 'Inner wall', 'Support',
                      'Internal solid infill', 'Floating vertical shell')
# Linhas com velocidade própria, que o resfriamento não iguala
NOT_ADJUSTABLE = ('Bridge', 'Overhang wall')
START_END = 'Início/fim (G-code da máquina)'


def parse_config(path):
    header, cfg = {}, {}
    section = None
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if line.startswith('; HEADER_BLOCK_START'):
                section = 'h'
            elif line.startswith('; HEADER_BLOCK_END'):
                section = None
            elif line.startswith('; CONFIG_BLOCK_START'):
                section = 'c'
            elif line.startswith('; CONFIG_BLOCK_END'):
                break
            elif section == 'h' and ':' in line:
                k, v = line[2:].split(':', 1)
                header[k.strip()] = v.strip()
            elif section == 'c' and ' = ' in line:
                k, v = line[2:].rstrip('\n').split(' = ', 1)
                cfg[k] = v
    return header, cfg


def num(cfg, key, default=0.0, ref=None):
    """Primeiro valor numérico de uma chave; aceita porcentagem de `ref`."""
    v = cfg.get(key)
    if v is None:
        return default
    v = v.split(',')[0].split(';')[0].strip().strip('"')
    try:
        if v.endswith('%'):
            return float(v[:-1]) / 100.0 * (ref if ref is not None else 1.0)
        return float(v)
    except ValueError:
        return default


def arc_geometry(x0, y0, x1, y1, i, j, cw):
    cx, cy = x0 + i, y0 + j
    r = math.hypot(i, j)
    a0 = math.atan2(y0 - cy, x0 - cx)
    a1 = math.atan2(y1 - cy, x1 - cx)
    da = (a0 - a1) if cw else (a1 - a0)
    if da <= 1e-9:
        da += 2 * math.pi  # inclui o arco completo (P1) do z-hop em espiral
    s = -1.0 if cw else 1.0
    t0 = (-math.sin(a0) * s, math.cos(a0) * s)
    t1 = (-math.sin(a1) * s, math.cos(a1) * s)
    return r * da, t0, t1


class Move:
    __slots__ = ('kind', 'feature', 'layer', 'dist', 'feed', 'acc', 'delta',
                 'dir_in', 'dir_out', 'e', 'pause', 'cond', 'cmd')


def parse_moves(path):
    moves = []
    x = y = z = 0.0
    absolute = True
    feed = 50.0
    acc = 10000.0
    feature = 'Início/fim (G-code da máquina)'
    layer = 0
    layer_z, layer_h = {}, {}
    in_exec = in_wipe = False
    in_start = True
    in_end = False
    cond = None  # tipo do bloco condicional (SKIPPABLE) atual
    travel_dists = []
    counts = defaultdict(int)

    def push(kind, feat, dist, delta, de, dir_in=None, dir_out=None):
        m = Move()
        m.cmd = 'G1'
        m.kind, m.feature, m.layer = kind, feat, layer
        m.dist, m.feed, m.acc, m.delta, m.e = dist, feed, acc, delta, de
        m.dir_in, m.dir_out = dir_in, dir_out
        m.pause = 0.0
        m.cond = cond
        moves.append(m)

    def push_stop(seconds, cmd):
        m = Move()
        m.cmd = cmd
        m.kind, m.feature, m.layer = 'pause', current_feature(), layer
        m.dist = m.feed = m.acc = m.e = 0.0
        m.delta = m.dir_in = m.dir_out = None
        m.pause = seconds
        m.cond = cond
        moves.append(m)

    def current_feature():
        if in_start or in_end:
            return 'Início/fim (G-code da máquina)'
        if cond == 'timelapse':
            return 'Timelapse (condicional)'
        if cond is not None:
            return 'Detecção de bico (condicional)'
        return feature

    with open(path, encoding='utf-8', errors='replace') as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line[0] == ';':
                if line.startswith('; EXECUTABLE_BLOCK_START'):
                    in_exec = True
                elif line.startswith('; MACHINE_START_GCODE_END'):
                    in_start = False
                    feature = 'Transição'
                elif line.startswith('; MACHINE_END_GCODE_START'):
                    in_end = True
                elif line.startswith('; FEATURE:'):
                    feature = line.split(':', 1)[1].strip()
                elif line.startswith('; CHANGE_LAYER'):
                    layer += 1
                    feature = 'Transição'
                elif line.startswith('; Z_HEIGHT:'):
                    layer_z[layer] = float(line.split(':')[1])
                elif line.startswith('; LAYER_HEIGHT:'):
                    layer_h[layer] = float(line.split(':')[1])
                elif line.startswith('; WIPE_START'):
                    in_wipe = True
                elif line.startswith('; WIPE_END'):
                    in_wipe = False
                elif line.startswith('; SKIPTYPE:'):
                    cond = line.split(':', 1)[1].strip()
                elif line.startswith('; SKIPPABLE_END'):
                    cond = None
                continue
            if not in_exec:
                continue
            code = line.split(';', 1)[0]
            words = WORD.findall(code)
            if not words:
                continue
            cmd = (words[0][0] + words[0][1]).upper()
            p = {k.upper(): float(v) for k, v in words[1:]}
            if cmd in ('G0', 'G1', 'G2', 'G3'):
                if 'F' in p:
                    feed = p['F'] / 60.0
                if absolute:
                    nx, ny, nz = p.get('X', x), p.get('Y', y), p.get('Z', z)
                else:
                    nx, ny, nz = x + p.get('X', 0.0), y + p.get('Y', 0.0), z + p.get('Z', 0.0)
                de = p.get('E', 0.0)  # o corpo do Bambu usa E relativo (M83)
                dx, dy, dz = nx - x, ny - y, nz - z
                dir_in = dir_out = None
                if cmd in ('G2', 'G3') and ('I' in p or 'J' in p):
                    xy, t0, t1 = arc_geometry(x, y, nx, ny, p.get('I', 0.0), p.get('J', 0.0),
                                              cmd == 'G2')
                    dist = math.hypot(xy, dz)
                    if dist > 0:
                        dir_in = (t0[0] * xy / dist, t0[1] * xy / dist, dz / dist)
                        dir_out = (t1[0] * xy / dist, t1[1] * xy / dist, dz / dist)
                    # componente por eixo aproximada pela tangente média
                    delta = {'X': abs(t0[0] + t1[0]) / 2 * xy, 'Y': abs(t0[1] + t1[1]) / 2 * xy,
                             'Z': dz, 'E': de}
                    counts['arcos'] += 1
                else:
                    xy = math.hypot(dx, dy)
                    dist = math.hypot(xy, dz)
                    delta = {'X': dx, 'Y': dy, 'Z': dz, 'E': de}
                feat = current_feature()
                if dist < 1e-9:
                    if de != 0:
                        if de < 0:
                            counts['retracoes'] += 1
                        push('retract', 'Retração/desretração' if feat == feature else feat,
                             abs(de), {'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'E': de}, de)
                else:
                    if de > 0 and not in_wipe:
                        push('extrude', feat, dist, delta, de, dir_in, dir_out)
                    elif in_wipe or de < 0:
                        push('wipe', 'Wipe (limpeza do bico)' if feat == feature else feat,
                             dist, delta, de, dir_in, dir_out)
                    elif xy < 1e-9:
                        if feat == feature:
                            counts['movimentos_z'] += 1
                        push('travel', 'Z (troca de camada/z-hop)' if feat == feature else feat,
                             dist, delta, de, dir_in, dir_out)
                    else:
                        is_hop = cmd in ('G2', 'G3') and dz != 0
                        if feat == feature:
                            if is_hop:
                                counts['zhop_espiral'] += 1
                            else:
                                counts['deslocamentos'] += 1
                                travel_dists.append(xy)
                        push('travel', ('Z (troca de camada/z-hop)' if is_hop else 'Deslocamento')
                             if feat == feature else feat, dist, delta, de, dir_in, dir_out)
                x, y, z = nx, ny, nz
            elif cmd in ('G4', 'M400'):
                push_stop(p.get('S', 0.0) + p.get('P', 0.0) / 1000.0, cmd)
            elif cmd == 'M204' and 'S' in p:
                acc = p['S']
            elif cmd == 'G90':
                absolute = True
            elif cmd == 'G91':
                absolute = False
            elif cmd == 'M106' and not in_start and not in_end:
                counts['comandos_ventoinha'] += 1
            elif cmd in ('G28', 'G29', 'M109', 'M190', 'G380'):
                push_stop(0.0, cmd)
    return moves, layer_z, layer_h, travel_dists, dict(counts)


class Planner:
    """Planejador no modelo do GCodeProcessor (modo normal, não silencioso)."""

    def __init__(self, cfg):
        self.max_v = {a: num(cfg, f'machine_max_speed_{a.lower()}', 500) for a in AXES}
        self.max_a = {a: num(cfg, f'machine_max_acceleration_{a.lower()}', 12000) for a in AXES}
        self.jerk = {a: num(cfg, f'machine_max_jerk_{a.lower()}', 9) for a in AXES}
        self.a_extr = num(cfg, 'machine_max_acceleration_extruding', 12000)
        self.a_retr = num(cfg, 'machine_max_acceleration_retracting', 5000)
        self.a_trav = num(cfg, 'machine_max_acceleration_travel', 9000)

    def times(self, moves, feed_of, acc_of=None):
        """Devolve o tempo (s) de cada movimento.

        `feed_of(m)` dá a velocidade (mm/s); `acc_of(m)`, se dado, a aceleração pedida.
        """
        n = len(moves)
        cruise = [0.0] * n
        accel = [0.0] * n
        safe = [0.0] * n
        max_entry = [0.0] * n
        prev = -1
        for i, m in enumerate(moves):
            if m.kind == 'pause':
                prev = -1
                continue
            d = m.dist
            inv = 1.0 / d
            v = feed_of(m)
            for a in AXES:
                av = abs(m.delta[a]) * inv * v
                if av > self.max_v[a] > 0:
                    v *= self.max_v[a] / av
            req = acc_of(m) if acc_of else m.acc
            if m.kind == 'retract':
                acc = self.a_retr
            elif m.kind == 'travel':
                acc = min(req, self.a_trav)
            else:
                acc = min(req, self.a_extr)
            for a in AXES:
                frac = abs(m.delta[a]) * inv
                if frac > 0 and acc * frac > self.max_a[a] > 0:
                    acc = self.max_a[a] / frac
            sf = v
            for a in AXES:
                if abs(m.delta[a]) * inv * v > self.jerk[a]:
                    sf = min(sf, self.jerk[a])
            cruise[i], accel[i], safe[i] = v, acc, sf
            if m.dir_in is None:
                m.dir_in = m.dir_out = (m.delta['X'] * inv, m.delta['Y'] * inv, m.delta['Z'] * inv)
            vj = sf
            if prev >= 0 and cruise[prev] > 1e-4:
                pm = moves[prev]
                pv = cruise[prev]
                larger = pv > v
                small = (v / pv) if larger else (pv / v)
                vj = v if larger else pv
                k = 1.0
                limited = False
                ex = [pv * c * (small if larger else 1.0) for c in pm.dir_out]
                en = [v * c for c in m.dir_in]
                jv = [abs(en[t] - ex[t]) for t in range(3)]
                for t, a in enumerate('XYZ'):
                    if jv[t] > self.jerk[a]:
                        k *= self.jerk[a] / jv[t]
                        jv = [c * k for c in jv]
                        limited = True
                ve_x = pm.e / pm.dist * pv * (small if larger else 1.0)
                ve_n = m.e * inv * v
                if limited:
                    ve_x *= k
                    ve_n *= k
                if ve_x > ve_n:
                    j = (ve_x - ve_n) if (ve_n > 0 or ve_x < 0) else max(ve_x, -ve_n)
                else:
                    j = (ve_n - ve_x) if (ve_n < 0 or ve_x > 0) else max(-ve_x, ve_n)
                if j > self.jerk['E']:
                    k *= self.jerk['E'] / j
                    limited = True
                if limited:
                    vj *= k
                thr = vj * 0.99
                if safe[prev] > thr and sf > thr:
                    vj = sf
            max_entry[i] = vj
            prev = i
        # passe reverso
        entry = [0.0] * n
        nxt = 0.0
        for i in range(n - 1, -1, -1):
            if moves[i].kind == 'pause':
                nxt = 0.0
                continue
            entry[i] = min(max_entry[i], math.sqrt(nxt * nxt + 2 * accel[i] * moves[i].dist))
            nxt = entry[i]
        # passe direto
        prev = -1
        for i, m in enumerate(moves):
            if m.kind == 'pause':
                prev = -1
                continue
            if prev < 0:
                entry[i] = min(entry[i], safe[i])
            else:
                entry[i] = min(entry[i], math.sqrt(entry[prev] ** 2 + 2 * accel[prev] * moves[prev].dist))
            prev = i
        out = [0.0] * n
        for i, m in enumerate(moves):
            if m.kind == 'pause':
                out[i] = m.pause
                continue
            nx = i + 1
            v1 = safe[i] if nx >= n or moves[nx].kind == 'pause' else entry[nx]
            out[i] = trapezoid(m.dist, entry[i], cruise[i], v1, accel[i])
        return out


def trapezoid(d, v0, vc, v1, a):
    if a <= 0 or vc <= 0:
        return d / max(vc, 1e-6)
    v0, v1 = min(v0, vc), min(v1, vc)
    da = (vc * vc - v0 * v0) / (2 * a)
    dd = (vc * vc - v1 * v1) / (2 * a)
    if da + dd <= d:
        return (vc - v0) / a + (vc - v1) / a + (d - da - dd) / vc
    vp = math.sqrt(max((2 * a * d + v0 * v0 + v1 * v1) / 2, max(v0, v1) ** 2))
    return max((vp - v0) / a + (vp - v1) / a, 0.0)


def nominal_speed(m, cfg, fil_area):
    """Velocidade sem desaceleração de resfriamento para uma extrusão."""
    key = SPEED_KEYS.get(m.feature)
    if key is None:
        return None
    v = num(cfg, key, 0.0)
    if m.feature == 'Floating vertical shell':
        v = num(cfg, 'vertical_shell_speed', v, ref=v)
    # seção nominal da linha: o E já vem multiplicado pelo fator de fluxo
    flow = num(cfg, 'filament_flow_ratio', 1.0) * num(cfg, 'print_flow_ratio', 1.0)
    area = m.e * fil_area / m.dist / (flow or 1.0)
    vmax = num(cfg, 'filament_max_volumetric_speed', 0.0)
    if vmax > 0 and area > 0:
        v = min(v, vmax / area)
    return v


def filament_area(cfg):
    return math.pi * (num(cfg, 'filament_diameter', 1.75) / 2) ** 2


def cooling_nominal(moves, cfg, cfg_nominal=None):
    """Desfaz a desaceleração de resfriamento do Bambu Studio.

    O Bambu Studio 2.08 (lógica "uniform_cooling", não proporcional) iguala
    todas as linhas ajustáveis mais rápidas que uma velocidade v* até a camada
    atingir o tempo mínimo. Aqui v* de cada camada é a maior velocidade abaixo
    da nominal entre os tipos de referência. Devolve (nominal, v_estrela):
    nominal[i] é a velocidade antes da desaceleração (None se não ajustável) e
    v_estrela[camada] é v* (inf quando a camada não foi desacelerada).
    `cfg_nominal` permite recalcular a nominal com outro limite de fluxo.
    """
    fil_area = filament_area(cfg)
    cfg_nominal = cfg_nominal or cfg
    outer = num(cfg_nominal, 'outer_wall_speed', 60)
    by_layer = defaultdict(list)
    for i, m in enumerate(moves):
        if m.kind == 'extrude' and m.cond is None and m.layer > 0 \
                and m.feature not in NOT_ADJUSTABLE and m.feature != START_END:
            by_layer[m.layer].append(i)
    nominal = [None] * len(moves)
    v_star = {}
    for L, idx in by_layer.items():
        slowed = []
        for i in idx:
            m = moves[i]
            if m.feature in REFERENCE_FEATURES:
                vn = nominal_speed(m, cfg, fil_area)
                if vn and m.feed < vn * 0.995:
                    slowed.append(m.feed)
        vs = max(slowed) if slowed else math.inf
        v_star[L] = vs
        for i in idx:
            m = moves[i]
            vn_orig = nominal_speed(m, cfg, fil_area)
            vn = nominal_speed(m, cfg_nominal, fil_area)
            if m.feature == 'Outer wall':
                vn_orig = min(num(cfg, 'outer_wall_speed', 60), vn_orig or math.inf)
                vn = min(outer, vn or math.inf)
            if vn_orig and m.feed >= vn_orig * 0.995:
                nominal[i] = vn  # já estava na velocidade nominal
            elif vs < math.inf and m.feed >= vs - 0.05:
                nominal[i] = vn if vn else m.feed  # foi igualada a v*
            else:
                nominal[i] = m.feed  # velocidade própria menor (saliência etc.)
    return nominal, v_star


def analyze(path):
    header, cfg = parse_config(path)
    fil_area = filament_area(cfg)
    moves, layer_z, layer_h, travel_dists, counts = parse_moves(path)
    planner = Planner(cfg)

    t_real = planner.times(moves, lambda m: m.feed)
    nominal, v_star = cooling_nominal(moves, cfg)
    feeds = [nv if nv is not None else m.feed for m, nv in zip(moves, nominal)]
    pos = {id(m): i for i, m in enumerate(moves)}
    t_nom = planner.times(moves, lambda m: feeds[pos[id(m)]])

    def agg(times):
        by_feat = defaultdict(float)
        by_layer = defaultdict(float)
        by_layer_cond = defaultdict(float)
        for m, t in zip(moves, times):
            by_feat[m.feature] += t
            if m.cond is not None:
                by_layer_cond[m.layer] += t
            elif m.feature != 'Início/fim (G-code da máquina)':
                by_layer[m.layer] += t
        return by_feat, by_layer, by_layer_cond

    feat_r, layer_r, cond_r = agg(t_real)
    feat_n, layer_n, _ = agg(t_nom)

    dist = defaultdict(float)
    vol = defaultdict(float)
    layer_vol = defaultdict(float)
    outer_speed = defaultdict(lambda: defaultdict(float))
    for m in moves:
        if m.kind == 'extrude':
            dist[m.feature] += m.dist
            vol[m.feature] += m.e * fil_area
            layer_vol[m.layer] += m.e * fil_area
            if m.feature == 'Outer wall' and m.cond is None:
                outer_speed[m.layer][round(m.feed)] += m.dist

    layers = []
    for L in sorted(set(layer_r) | set(layer_vol)):
        if L == 0:
            continue
        layers.append({
            'camada': L, 'z': layer_z.get(L), 'altura': layer_h.get(L),
            'tempo_s': round(layer_r.get(L, 0.0), 3),
            'tempo_sem_desaceleracao_s': round(layer_n.get(L, 0.0), 3),
            'tempo_condicional_s': round(cond_r.get(L, 0.0), 3),
            'v_estrela_mm_s': None if v_star.get(L, math.inf) == math.inf else round(v_star[L], 1),
            'volume_mm3': round(layer_vol.get(L, 0.0), 2),
            # velocidade em que a maior parte da parede externa da camada foi feita
            'parede_externa_mm_s': max(outer_speed[L].items(), key=lambda kv: kv[1])[0]
            if outer_speed.get(L) else None,
        })

    travel_dists.sort()
    nt = len(travel_dists)
    travel = {
        'quantidade': nt,
        'distancia_total_mm': round(sum(travel_dists)),
        'mediana_mm': round(travel_dists[nt // 2], 2) if nt else 0,
        'p90_mm': round(travel_dists[int(nt * 0.9)], 2) if nt else 0,
        'acima_de_20mm': sum(1 for d in travel_dists if d > 20),
    }
    return {
        'arquivo': path,
        'cabecalho': header,
        'tempo_por_tipo_s': {k: round(v, 2) for k, v in feat_r.items()},
        'tempo_por_tipo_sem_desaceleracao_s': {k: round(v, 2) for k, v in feat_n.items()},
        'distancia_por_tipo_mm': {k: round(v, 1) for k, v in dist.items()},
        'volume_por_tipo_mm3': {k: round(v, 1) for k, v in vol.items()},
        'camadas': layers,
        'deslocamentos': travel,
        'contagens': counts,
        'config_num': {
            'outer_wall_speed': num(cfg, 'outer_wall_speed', 60),
            # parede interna de 0,45 mm limitada pelo fluxo máximo do filamento
            'inner_wall_nominal': min(num(cfg, 'inner_wall_speed', 150),
                                      num(cfg, 'filament_max_volumetric_speed', 1e9) /
                                      ((num(cfg, 'inner_wall_line_width', 0.45) -
                                        num(cfg, 'layer_height', 0.16) * (1 - math.pi / 4)) *
                                       num(cfg, 'layer_height', 0.16))),
        },
        'config': {k: cfg.get(k) for k in (
            'layer_height', 'initial_layer_print_height', 'wall_loops', 'wall_generator',
            'top_shell_layers', 'bottom_shell_layers', 'sparse_infill_density',
            'sparse_infill_pattern', 'outer_wall_speed', 'inner_wall_speed',
            'sparse_infill_speed', 'internal_solid_infill_speed', 'travel_speed',
            'outer_wall_acceleration', 'default_acceleration', 'travel_acceleration',
            'filament_max_volumetric_speed', 'nozzle_temperature', 'slow_down_layer_time',
            'slow_down_min_speed', 'fan_min_speed', 'fan_max_speed', 'fan_cooling_layer_time',
            'enable_support', 'support_type', 'support_threshold_angle', 'seam_position',
            'z_hop', 'z_hop_types', 'retraction_length', 'wipe', 'reduce_crossing_wall',
            'timelapse_type', 'filament_settings_id', 'print_settings_id')},
    }


def hms(s):
    s = int(round(s))
    return f'{s // 3600}h{(s % 3600) // 60:02d}m{s % 60:02d}s'


def report(r):
    tr = r['tempo_por_tipo_s']
    tn = r['tempo_por_tipo_sem_desaceleracao_s']
    tot = sum(tr.values())
    cond = sum(v for k, v in tr.items() if 'condicional' in k)
    start = tr.get('Início/fim (G-code da máquina)', 0.0)
    body = tot - cond - start
    body_n = sum(tn.values()) - cond - start
    h = r['cabecalho']
    print('Arquivo:', r['arquivo'])
    print('Bambu Studio — tempo do modelo / total:',
          h.get('model printing time', '?').replace('; total estimated time:', ' /'))
    print(f'Script — impressão (camadas, sem blocos condicionais): {hms(body)}')
    print(f'Script — blocos condicionais (timelapse/detecção):     {hms(cond)}')
    print(f'Script — G-code de início/fim (sem esperas de aquecimento): {hms(start)}')
    print(f'Script — impressão sem a desaceleração de resfriamento:     {hms(body_n)}'
          f'  (resfriamento acrescenta {hms(body - body_n)})')
    print()
    print(f"{'Tipo de linha':34s} {'tempo':>9s} {'% imp.':>7s} {'s/ desac.':>9s} {'mm':>8s} {'mm³':>7s}")
    for k, v in sorted(tr.items(), key=lambda kv: -kv[1]):
        if 'condicional' in k or k.startswith('Início'):
            continue
        print(f"{k:34s} {hms(v):>9s} {100 * v / body:7.1f} {hms(tn.get(k, 0)):>9s} "
              f"{r['distancia_por_tipo_mm'].get(k, 0):8.0f} {r['volume_por_tipo_mm3'].get(k, 0):7.0f}")
    print()
    lay = r['camadas']
    outer = r['config_num']['outer_wall_speed']
    inner = r['config_num']['inner_wall_nominal']
    vs = [c['v_estrela_mm_s'] for c in lay if c['camada'] > 1]
    slow_in = sum(1 for v in vs if v is not None and v < 0.95 * inner)
    slow_out = sum(1 for v in vs if v is not None and v < 0.99 * outer)
    print(f"Camadas: {len(lay)}. Desaceleradas pelo tempo mínimo de camada: {slow_in} "
          f"(paredes internas/preenchimento > 5% mais lentos); {slow_out} com a parede "
          f"externa abaixo de {outer:g} mm/s.")
    print()
    print('Velocidade predominante da parede externa por faixa de altura (mm/s):')
    bands = defaultdict(list)
    for c in lay:
        if c['parede_externa_mm_s'] is not None and c['camada'] > 1:
            bands[int(c['z'] // 4) * 4].append(c['parede_externa_mm_s'])
    for b in sorted(bands):
        v = sorted(bands[b])
        print(f"  {b:2d}–{b + 4:2d} mm: mín {v[0]:3d}  mediana {v[len(v) // 2]:3d}  máx {v[-1]:3d}")
    print()
    print('Deslocamentos:', r['deslocamentos'])
    print('Contagens:', r['contagens'])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('gcode')
    ap.add_argument('--json', help='grava o resultado completo em JSON')
    args = ap.parse_args()
    r = analyze(args.gcode)
    report(r)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump(r, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
