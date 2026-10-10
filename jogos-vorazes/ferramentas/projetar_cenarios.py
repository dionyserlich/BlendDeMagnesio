#!/usr/bin/env python3
"""Projeção de tempo por unidade para cenários de produção (somente leitura).

Usa os caminhos de ferramenta de um G-code já fatiado (uma cópia da peça) e
simula, sem gerar G-code novo:
  * N cópias na mesma mesa, impressas camada a camada;
  * timelapse ligado ou desligado no envio da impressão;
  * aceleração padrão diferente (paredes internas, preenchimento, suporte);
  * tempo mínimo de camada e lógica de desaceleração ("uniform_cooling" ou
    "consistent_surface") reaplicados como o Bambu Studio 2.08 faz
    (CoolingBuffer/GCodeEditor: tempo de linha = comprimento / velocidade,
    sem aceleração; as linhas mais rápidas são igualadas a uma velocidade v*
    até o tempo da camada chegar ao mínimo, respeitando a velocidade mínima).

Limites: não refaz o fatiamento. Mudanças que alteram caminhos (altura de
camada, preenchimento, Arachne, suportes) precisam ser fatiadas de novo no
Bambu Studio. O deslocamento entre cópias e o tempo de preparação usam
valores médios medidos neste G-code.

Uso:
    python3 -I projetar_cenarios.py ARQUIVO.gcode [--json SAIDA.json]
"""
import argparse
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analisar_gcode as A  # noqa: E402



def prepare(path, max_volumetric=None):
    header, cfg = A.parse_config(path)
    moves, layer_z, _, _, _ = A.parse_moves(path)
    by_layer = defaultdict(list)
    for i, m in enumerate(moves):
        if m.feature != A.START_END and m.layer > 0:
            by_layer[m.layer].append(i)
    # v* é medido com a configuração original; a nominal pode usar outro fluxo máximo
    cfg_nom = dict(cfg, filament_max_volumetric_speed=str(max_volumetric)) if max_volumetric else None
    nominal, v_star = A.cooling_nominal(moves, cfg, cfg_nom)
    return {
        'header': header, 'cfg': cfg, 'moves': moves, 'by_layer': by_layer,
        'nominal': nominal, 'observed_v': v_star,
        'min_speed': A.num(cfg, 'slow_down_min_speed', 20), 'layer_z': layer_z,
    }


def simple_time(moves, idx, nominal, v_int, v_ext, min_speed):
    """Tempo de camada no modelo do Bambu Studio (comprimento / velocidade)."""
    t = 0.0
    for i in idx:
        m = moves[i]
        if m.kind == 'pause':
            if m.cmd == 'G4':  # o Bambu Studio só conta G4 no tempo de camada
                t += m.pause
            continue
        vn = nominal[i]
        if vn is None:
            t += m.dist / max(m.feed, 1e-6)
            continue
        cap = v_ext if m.feature == 'Outer wall' else v_int
        v = vn if vn <= cap else max(cap, min_speed)
        t += m.dist / max(v, 1e-6)
    return t


def solve_layer(st, idx, copies, hop_simple, target, logic):
    """Devolve (v_interno, v_externo) para cumprir o tempo mínimo de camada."""
    moves, nominal, ms = st['moves'], st['nominal'], st['min_speed']
    own = [i for i in idx if moves[i].cond is None]
    cond = [i for i in idx if moves[i].cond is not None]
    t_cond = simple_time(moves, cond, nominal, math.inf, math.inf, ms)
    extra = t_cond + (copies - 1) * hop_simple

    def total(vi, ve):
        return copies * simple_time(moves, own, nominal, vi, ve, ms) + extra

    inf = math.inf
    if total(inf, inf) >= target:
        return inf, inf

    def bisect(f):
        lo, hi = ms, 400.0
        if f(lo) < target:
            return lo
        for _ in range(40):
            mid = (lo + hi) / 2
            if f(mid) >= target:
                lo = mid
            else:
                hi = mid
        return lo

    if logic == 'consistent_surface':
        if total(ms, inf) >= target:
            return bisect(lambda v: total(v, inf)), inf
        return ms, bisect(lambda v: total(ms, v))
    v = bisect(lambda v: total(v, v))
    return v, v


def scenario(st, planner, copies=1, timelapse=True, target=None, logic='uniform_cooling',
             default_acc=None, outer_acc=None, hop_real=0.40, hop_simple=0.12, prep_s=None):
    cfg, moves, nominal = st['cfg'], st['moves'], st['nominal']
    if target is None:
        target = A.num(cfg, 'slow_down_layer_time', 8) * 1.001
    v_layer = {}
    for L, idx in st['by_layer'].items():
        v_layer[L] = solve_layer(st, idx, copies, hop_simple, target, logic)
    ms = st['min_speed']
    orig_default = A.num(cfg, 'default_acceleration', 4000)

    feeds = [m.feed for m in moves]
    for L, idx in st['by_layer'].items():
        vi, ve = v_layer[L]
        for i in idx:
            vn = nominal[i]
            if vn is None:
                continue
            cap = ve if moves[i].feature == 'Outer wall' else vi
            feeds[i] = vn if vn <= cap else max(cap, ms)
    index = {id(m): i for i, m in enumerate(moves)}

    def acc_of(m):
        if default_acc and m.kind == 'extrude' and abs(m.acc - orig_default) < 1:
            return default_acc
        if outer_acc and m.feature == 'Outer wall':
            return outer_acc
        return m.acc

    times = planner.times(moves, lambda m: feeds[index[id(m)]], acc_of)
    per_copy = 0.0
    cond_t = 0.0
    outer_len = defaultdict(float)
    for L, idx in st['by_layer'].items():
        for i in idx:
            m = moves[i]
            if m.cond is not None:
                if m.cond == 'timelapse':
                    cond_t += times[i]
            else:
                per_copy += times[i]
                if m.kind == 'extrude' and m.feature == 'Outer wall':
                    outer_len[round(feeds[i])] += m.dist
    n_layers = len(st['by_layer'])
    if prep_s is None:
        h = st['header'].get('model printing time', '')
        prep_s = 393.0
        try:
            model, total = [parse_hms(x) for x in h.split('; total estimated time:')]
            prep_s = total - model
        except ValueError:
            pass
    plate = prep_s + copies * per_copy + (copies - 1) * hop_real * n_layers
    if timelapse:
        plate += cond_t
    tot_outer = sum(outer_len.values()) or 1.0
    at_nominal = sum(v for k, v in outer_len.items() if k >= 59) / tot_outer
    slowed_layers = sum(1 for v in v_layer.values() if v[1] < math.inf or v[0] < math.inf)
    return {
        'copias': copies, 'timelapse': timelapse, 'logica': logic,
        'tempo_minimo_camada_s': round(target / 1.001, 2),
        'aceleracao_padrao': default_acc or orig_default,
        'tempo_mesa_s': round(plate), 'tempo_por_unidade_s': round(plate / copies),
        'camadas_desaceleradas': slowed_layers,
        'parede_externa_na_velocidade_nominal_pct': round(100 * at_nominal, 1),
    }


def parse_hms(s):
    s = s.strip()
    total = 0
    for part in s.split():
        if part.endswith('h'):
            total += int(part[:-1]) * 3600
        elif part.endswith('m'):
            total += int(part[:-1]) * 60
        elif part.endswith('s'):
            total += int(part[:-1])
    if not s:
        raise ValueError
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('gcode')
    ap.add_argument('--json')
    args = ap.parse_args()
    st = prepare(args.gcode)
    planner = A.Planner(st['cfg'])

    rows = []
    base = scenario(st, planner, 1, True)
    rows.append(('Original (1 peça, timelapse ligado)', base))
    rows.append(('1 peça, timelapse desligado', scenario(st, planner, 1, False)))
    rows.append(('1 peça, "consistent surface", timelapse desligado',
                 scenario(st, planner, 1, False, logic='consistent_surface')))
    for n in (2, 3, 4, 6, 8):
        rows.append((f'{n} peças, timelapse desligado', scenario(st, planner, n, False)))
    rows.append(('4 peças, timelapse ligado', scenario(st, planner, 4, True)))
    rows.append(('4 peças, timelapse desligado, aceleração padrão 6000',
                 scenario(st, planner, 4, False, default_acc=6000)))
    rows.append(('4 peças, idem, deslocamento entre peças 0,6 s (pessimista)',
                 scenario(st, planner, 4, False, default_acc=6000, hop_real=0.6)))
    rows.append(('4 peças, idem, aceleração da parede externa 3000 (não recomendado)',
                 scenario(st, planner, 4, False, default_acc=6000, outer_acc=3000)))
    st10 = prepare(args.gcode, max_volumetric=10)
    rows.append(('4 peças, idem (aceleração 6000), fluxo máximo 10 mm³/s',
                 scenario(st10, planner, 4, False, default_acc=6000)))
    rows.append(('1 peça, tempo mínimo 5 s (referência; não recomendado)',
                 scenario(st, planner, 1, False, target=5 * 1.001)))

    ref = base['tempo_por_unidade_s']
    print(f"{'Cenário':62s} {'mesa':>9s} {'por peça':>9s} {'ganho':>7s} {'ext@60':>7s}")
    for name, r in rows:
        gain = 100 * (1 - r['tempo_por_unidade_s'] / ref)
        print(f"{name:62s} {A.hms(r['tempo_mesa_s']):>9s} {A.hms(r['tempo_por_unidade_s']):>9s} "
              f"{gain:6.1f}% {r['parede_externa_na_velocidade_nominal_pct']:6.1f}%")
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as fh:
            json.dump([{'cenario': n, **r} for n, r in rows], fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
