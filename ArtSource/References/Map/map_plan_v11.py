#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Targeted v10 -> v11. Run with Python -B; writes only this revision.

The v10 JSON and its analysis/renderer are read-only inputs. No packages,
Unity, Git, handoff log, caches or files outside this directory are written.
"""
import copy
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import map_plan_v10 as v10

m, v7 = v10.m, v10.v7
ROOT = m.ROOT
STEM = 'MAP_PLAN_R01_v11'
OUTPUTS = {STEM + s for s in ('.json', '.svg', '.png', '_REPORT.md')} | {'map_plan_v11.py'}
CLUSTER = ['O06_T3_U1', 'O06_T3_U3', 'O06_T3_U4', 'O06_T3_U6', 'O06_T5_U4', 'O06_T5_U5']
HOUSE_MOVES = {
    'O06_T3_U1': ([544, 523], 85),
    'O06_T3_U3': ([543, 505], 96),
    'O06_T3_U4': ([559, 497], 5),
    'O06_T3_U6': ([578, 498], -7),
    'O06_T5_U4': ([597, 497], 8),
    'O06_T5_U5': ([616, 499], -5),
    'O06_T1_U1': ([496, 562], -85),
    'O06_T1_U3': ([497, 533], -96),
}
INDUSTRIAL_IDS = {'F06_COMPLEX', 'F06_TOW', 'F06_DEPOT', 'F06_CHIMNEY',
                  'F06_WARE1', 'F06_WARE2', 'F06_SCRAP', 'F06_MAINT'}
ALTERED_ROADS = {'I_CONNECT', 'I_YARD', 'ACCESS_B05', 'ACCESS_P12', 'ACCESS_P14',
    'ACCESS_CHIMNEY', 'ACCESS_F06_WARE1', 'ACCESS_F06_WARE2', 'ACCESS_F06_SCRAP',
    'ACCESS_P09-3', 'ACCESS_F06_CHURCH', 'ACCESS_F06_MAINT'}
AVENUE_Y = 723.5
AVENUE_SHIFT = 5.5
NORTH_SHIFT = 12
SOUTH_SHIFT = -1
NORTH_ROADS = {'EXIT_NE', 'EXIT_APPROACH_NE', 'ACCESS_P07', 'ACCESS_F06_K3',
               'ACCESS_P08', 'ACCESS_P11-3', 'ACCESS_P09-2'}
FRONT_FUNCTIONS = {'F06_GBASE', 'F06_K1', 'F06_24'}
FRONT_ROADS = {'ACCESS_B03', 'ACCESS_F06_K1', 'ACCESS_F06_24', 'ACCESS_P11-2'}
FOLLOWUP_ROADS = NORTH_ROADS | FRONT_ROADS | {'ARC_AVENUE', 'ARC_RURAL', 'HUT_BRANCH',
    'RECEPTION_BRANCH', 'R_COURTS', 'COURT_ACCESS_1', 'COURT_ACCESS_2', 'COURT_ACCESS_3',
    'R_REAR', 'ACCESS_P13-4', 'OLD_TOWN_CONNECTOR'}
FENCE_STYLES = {
    'concrete_fence': ('#888b8e', 2.1, 'Бетонный забор / 2,5 м'),
    'wooden_fence': ('#946847', 1.8, 'Деревянный / 1,6 м + деревья'),
    'elite_fence': ('#343b41', 1.9, 'Ограда элитки / 2,4 м'),
    'canal_railing': ('#647c87', 1.2, 'Перила канала / 1,1 м'),
    'rock_scarp': ('#877c70', 2.6, 'Скалы / закрытый конец пляжа'),
}
BEACH_LAND = [[350, 358], [510, 376.25], [526, 340], [800, 340], [800, 470], [925, 470]]


def parallel_chain(points, distance, lock_end_x=False):
    """Offset a coastal polyline to its right; intersect adjoining offset lines."""
    lines = []
    for a, b in zip(points, points[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        n = math.hypot(dx, dy)
        lines.append(([a[0] + distance*dy/n, a[1] - distance*dx/n], [dx, dy]))
    start = lines[0][0][:]
    last, direction = lines[-1]
    end = [last[k] + direction[k] for k in (0, 1)]
    if lock_end_x:
        start[1] += (points[0][0]-start[0])*lines[0][1][1]/lines[0][1][0]
        start[0] = points[0][0]
        end[1] += (points[-1][0]-end[0])*direction[1]/direction[0]
        end[0] = points[-1][0]
    result = [start]
    for (a, u), (b, v) in zip(lines, lines[1:]):
        den = u[0]*v[1] - u[1]*v[0]
        t = ((b[0]-a[0])*v[1] - (b[1]-a[1])*v[0])/den
        result.append([a[k]+t*u[k] for k in (0, 1)])
    return [[round(q, 3) for q in p] for p in result + [end]]


COAST = parallel_chain(BEACH_LAND, 25, lock_end_x=True)


def hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.iterdir()) if p.is_file() and p.name not in OUTPUTS}


def source_data():
    return json.loads((ROOT / 'MAP_PLAN_R01_v10.json').read_text(encoding='utf-8'))


def shift_to(q, center):
    old = q['center_m']
    dx, dy = center[0] - old[0], center[1] - old[1]
    for key in ('footprint_m', 'polygon_m', 'yard_polygon_m'):
        if key in q:
            q[key] = [[round(x + dx, 3), round(y + dy, 3)] for x, y in q[key]]
    q['center_m'] = center


def seed():
    d = source_data()
    d.update(revision='v11', title_ru='VOLUNTEERS ONLY — план карты R01 / v11')
    d['specification']['brief_override'] = 'req_map_plan_v11.md, targeted review, 2026-10-04'
    d['provenance'] = dict(brief='req_map_plan_v11.md', source_schema='MAP_PLAN_R01_v10.json',
        owner_decisions_date='2026-10-04', method='targeted v10 edits; unaffected geometry retained',
        previous_files_sha256=hashes())
    d['comparison'] = {'v10': {'extent_m': d['metrics']['extent_m'], 'area_m2': d['metrics']['area_m2']},
                       'policy': 'targeted edits; compact industry and new coast; no scaling'}
    bs = {b['id']: b for b in d['building_masses']}
    plots = {p['id']: p for p in d['plots']}
    for bid, (center, angle) in HOUSE_MOVES.items():
        b = bs[bid]
        b.update(center_m=center, polygon_m=m.rectangle(*center, b['width_m'], b['depth_m'], angle))
        # South-facing houses use local -Y; houses on the west leg use +Y.
        heading = math.radians(angle)
        front = [center[0] + 9 * math.sin(heading), center[1] - 9 * math.cos(heading)]
        # The two inner western houses face west, so their front is local +Y.
        if bid in CLUSTER[:2]:
            front = [center[0] - 11 * math.sin(heading), center[1] + 11 * math.cos(heading)]
        # Outer western houses face east (local +Y at -90 degrees).
        if bid.startswith('O06_T1_'):
            front = [center[0] - 11 * math.sin(heading), center[1] + 11 * math.cos(heading)]
        plots[bid + '_FRONT']['polygon_m'] = m.rectangle(*front, 7, 6, angle)

    fs = {f['id']: f for f in d['functional_buildings']}
    pts = {p['id']: p for p in d['points']}
    roads = {r['id']: r for r in d['roads']}

    def move(fid, center, door, parent, start, route=None):
        f = fs[fid]
        shift_to(f, center)
        f.update(entrance_m=door, access_road_id=parent)
        pid = f.get('poi_id')
        if pid:
            pts[pid]['position_m'] = door[:]
        rid = 'ACCESS_' + (pid or fid)
        poly = route or [start, door]
        if rid not in roads:
            r = dict(id=rid, **{'class': 'town_street'}, width_m=6,
                     district_ids=[f['district_id']], access_only=True, polyline_m=poly)
            d['roads'].append(r)
            roads[rid] = r
        else:
            roads[rid]['polyline_m'] = poly

    move('F06_CHURCH', [572, 524], [562, 534], 'O_RING', [525, 534])
    # One northern and one southern building row, separated by a yard spine.
    roads['I_CONNECT']['polyline_m'] = [[650, 480], [650, 392]]
    roads['I_YARD']['polyline_m'] = [[531, 392], [650, 392], [775, 392]]
    move('F06_COMPLEX', [589, 415], [589, 397], 'I_YARD', [589, 392])
    move('F06_TOW', [702, 418], [702, 408], 'I_YARD', [702, 392])
    move('F06_DEPOT', [775, 377], [775, 391], 'I_YARD', [775, 392])
    move('F06_CHIMNEY', [531, 417], [531, 409], 'I_YARD', [531, 392])
    move('F06_WARE1', [559, 376], [559, 389], 'I_YARD', [559, 392])
    move('F06_WARE2', [700, 376], [700, 389], 'I_YARD', [700, 392])
    move('F06_SCRAP', [616, 373], [616, 384], 'I_YARD', [616, 392])
    move('F06_MAINT', [745, 420], [745, 410], 'I_YARD', [745, 392])
    pts['P09-3']['position_m'] = [627, 410]
    roads['ACCESS_P09-3']['polyline_m'] = [[638, 392], [638, 410], [627, 410]]
    sites = {s['id']: s for s in d['functional_sites']}
    sites['F06_TOW_YARD']['polygon_m'] = [[687, 407], [717, 407], [717, 429], [687, 429]]
    sites['F06_SCRAP_YARD']['polygon_m'] = [[600, 363], [632, 363], [632, 381], [600, 381]]
    sites['SITE_P09-3']['position_m'] = [627, 410]
    d['functional_sites'].append(dict(id='B05_YARD', type='production_yard', district_id='industrial',
        building_id='F06_COMPLEX', polygon_m=[[558, 398], [622, 398], [622, 433], [558, 433]]))
    # Keep even the final 10m of the original valley alignment, up to x=510.
    d['railway']['polyline_m'] = d['railway']['polyline_m'][:5] + [[510, 396.25], [526, 360], [775, 360]]
    d['roads'] = [r for r in d['roads'] if r['id'] != 'EXIT_S']
    d['points'] = [p for p in d['points'] if p['id'] != 'P16-3']
    d['exits'] = [e for e in d['exits'] if e['id'] != 'S']
    ds = {q['id']: q for q in d['districts']}
    ds['industrial']['polygon_m'] = [[510, 376.25], [526, 340], [800, 340], [800, 440], [510, 440]]
    ds['industrial']['notes_ru'] = 'ЖД — южный предел; ниже неё только полоса до 20 м. Все здания и дворы севернее ЖД.'
    ds['fields']['polygon_m'] = [[350, 358], [510, 376.25], [510, 440], [470, 440], [470, 540], [350, 540]]
    ds['fields']['notes_ru'] = 'Южный край продлён до пляжа; проход перекрыт оградой, путь от B06 отсутствует.'
    d['beaches'] = [dict(id='BEACH', name_ru='Пляж', polygon_m=BEACH_LAND + list(reversed(COAST)),
        surface='sand', access_road_ids=['BEACH_ACCESS'],
        closed_ends_ru='Западный конец у Малой долины закрыт скалами и оградой; восточный конец — скалами. Вход только через элитку.')]
    d['water'].append(dict(id='SEA', kind='sea', name_ru='Море',
        polygon_m=COAST + [[1075, 445], [1075, 165], [200, 165], [200, COAST[0][1]]],
        return_rule='return_to_last_ground_point'))
    canal = next(w for w in d['water'] if w['id'] == 'CANAL')
    canal['centerline_m'][-1] = [796, 440]
    canal['name_ru'] = 'Канал; выпуск под пляжем'
    canal['banks'] = 'steep_concrete; sealed outlet under beach to SEA; no surface cut or pedestrian opening'
    d['functional_sites'].append(dict(id='CANAL_BEACH_CULVERT', type='culvert', district_id='industrial',
        polyline_m=[[796, 440], [826, 440]], width_m=4, label_ru='Канал под пляжем',
        tunnel_carrier='water_below_sand', blocks_foot_bypass=True))
    d['roads'].append(dict(id='BEACH_ACCESS', **{'class': 'town_street'}, width_m=6,
        polyline_m=[[900, 485], [900, 458], [890, 458]], district_ids=['elite'], access_only=True))
    d['functional_sites'].append(dict(id='BEACH_TURNAROUND', type='turnaround', district_id='beach',
        polygon_m=m.rectangle(890, 458, 12, 10), label_ru='Разворот / парковка'))
    d['boundary']['polygon_m'] = [[110, 470], [350, 470]] + COAST + [
        [925, 620], [780, 620], [780, 865], [470, 865], [470, 780], [350, 780],
        [350, 710], [230, 710], [180, 780], [110, 780], [110, 740], [180, 690], [180, 550], [110, 550]]
    d['boundary']['coast_segments_m'] = [[a, b] for a, b in zip(COAST, COAST[1:])]
    d['boundary']['barrier'] = ('continuous thin rock scarp and fence on every non-coast edge; '
        'coast_segments_m have no wall: SEA returns player and van to last ground point')

    def fence(fid, district, poly, material='security_fence', gate=None):
        q = dict(id=fid, kind='interdistrict_barrier', district_id=district, polygon_m=poly,
                 blocks_foot=True, blocks_van=True, material=material, height_target_m=2.4,
                 continuity_group='BEACH_ACCESS_CONTROL')
        if gate:
            q['gate_road_id'] = gate
        d['vegetation_parcels'].append(q)

    for q in d['vegetation_parcels']:
        if q['id'] == 'RURAL_TRANSITION_1':
            q['polygon_m'] = [[348, 358], [352, 358], [352, 598.1], [348, 598.1]]
        if q['id'] == 'VALLEY_URBAN':
            q['polygon_m'] = [[508, 376.25], [512, 376.25], [512, 440], [508, 440]]
    industrial_edge = BEACH_LAND[1:4] + [[800, 440]]
    fence('INDUSTRIAL_BEACH_FENCE', 'industrial', industrial_edge + list(reversed(parallel_chain(industrial_edge, -2))))
    fence('OLD_TOWN_BEACH_FENCE', 'old_town', [[798, 440], [800, 440], [800, 470], [798, 470]])
    valley_edge = BEACH_LAND[:2]
    fence('VALLEY_BEACH_FENCE', 'fields', valley_edge + list(reversed(parallel_chain(valley_edge, -2))))
    fence('BEACH_WEST_ROCKS', 'fields', [[350, COAST[0][1]], [353, COAST[0][1]], [353, 358], [350, 358]], 'rock_scarp')
    fence('ELITE_BEACH_1', 'elite', [[800, 469], [897, 469], [897, 471], [800, 471]], gate='BEACH_ACCESS')
    fence('ELITE_BEACH_2', 'elite', [[903, 469], [925, 469], [925, 471], [903, 471]], gate='BEACH_ACCESS')
    fence('BEACH_EAST_ROCKS', 'elite', [[922, 445], [925, 445], [925, 469], [922, 469]], 'rock_scarp')
    d['planning_notes_ru'] = [
        'Восемь малых домов переразмещены: шесть у почты вдоль западной/южной стороны кольца; два у супермаркета вынесены за западную сторону.',
        'Церковь перенесена к юго-западному углу кольца (572;524), подъезд с западной стороны. Остальные объекты старого города сохранены.',
        'Промзона сокращена: y=340–440; ЖД внутри неё идёт по y=360, южнее остаётся не более 20 м.',
        'B05 с двором, P12 с парковкой, P14, оба склада, труба, металлолом, сарай и P09-3 расположены севернее ЖД; дорога дворов y=392.',
        'I_CONNECT — единственный въезд из старого города. Переезд удалён: дороги больше не пересекают ЖД; лесной и долинный участки сохранены.',
        'Южный пост P16-3, EXIT_S, южный тупик, его барьеры и триггер удалены. Сохранены посты СЗ P16 и СВ P16-2.',
        'Пляж шириной 25 м огибает юг элитки, восток и юг промзоны, доходит до Малой долины; долина продлена на 32 м к югу.',
        'Единственный автомобильный и пеший вход: ELITE_SOUTH → BEACH_ACCESS (37 м) → площадка разворота 12 × 10 м.',
        'Промзона, старый город и долина от пляжа отделены непрерывными оградами; концы закрыты скалами. Частного пути от B06 нет.',
        'Открытый канал заканчивается у x=796 и уходит в закрытый выпуск под песком до моря: пляж не разрезан открытой водой.',
        'SEA вне игровой территории, не менее 150 м за берегом. Игрок и бусик возвращаются в последнюю точку суши входа в воду.',
        'Южная граница проходит по морской кромке пляжа; coast_segments_m без стены, остальные рёбра со скалами/оградой.',
        'Усадьбы, элитные дома, вилла B06, озеро, реки и поля сохранены без масштабирования.',
        'Геометрия и графы проверены расчётно; физическая реализация оград, выпуска и возврата из моря требует Unity-плейтеста.']
    followup(d)
    return d


def followup(d):
    """Apply req_map_plan_v11_followup.md after all original v11 edits."""
    d['specification']['brief_override'] = 'req_map_plan_v11.md + req_map_plan_v11_followup.md, 2026-10-04'
    d['provenance']['brief'] = 'req_map_plan_v11.md + req_map_plan_v11_followup.md'
    d['provenance']['method'] = 'v10 source + original v11 edits + courtyard setbacks and contextual fences'
    for key in ('building_masses', 'functional_buildings', 'points', 'functional_sites'):
        for i, q in enumerate(d[key]):
            if q.get('district_id') != 'residential':
                continue
            if q['id'].startswith('R06_C3_') or q['id'] in ('BAD_BLOCK_3', 'P13-4'):
                amount = SOUTH_SHIFT
            elif q.get('center_m', q.get('position_m', [0, 0]))[1] > 718:
                amount = NORTH_SHIFT
            elif q['id'] in FRONT_FUNCTIONS | {'B03', 'P11-2'}:
                amount = AVENUE_SHIFT
            else:
                continue
            d[key][i] = v10.shifted(q, amount)
    for i, q in enumerate(d['microdistricts']):
        d['microdistricts'][i] = v10.shifted(q, NORTH_SHIFT if i < 2 else SOUTH_SHIFT)
    next(p for p in d['points'] if p['id'] == 'BAD_CENTER')['position_m'] = [650, AVENUE_Y]
    d['exits'] = [v10.shifted(e, NORTH_SHIFT) if e['id'] == 'NE' else e for e in d['exits']]
    roads = {r['id']: r for r in d['roads']}
    for rid in NORTH_ROADS:
        roads[rid]['polyline_m'] = v10.shifted(roads[rid], NORTH_SHIFT)['polyline_m']
    for rid in FRONT_ROADS:
        roads[rid]['polyline_m'] = v10.shifted(roads[rid], AVENUE_SHIFT)['polyline_m']
    roads['ARC_AVENUE']['polyline_m'] = [[470, AVENUE_Y], [770, AVENUE_Y]]
    roads['ARC_RURAL']['polyline_m'][-2:] = [[405, AVENUE_Y], [470, AVENUE_Y]]
    for rid in ('HUT_BRANCH', 'RECEPTION_BRANCH', 'R_COURTS', 'OLD_TOWN_CONNECTOR'):
        roads[rid]['polyline_m'][0][1] = AVENUE_Y
    for rid in ('COURT_ACCESS_1', 'COURT_ACCESS_2'):
        roads[rid]['polyline_m'][0][1] = AVENUE_Y
        roads[rid]['polyline_m'][-1][1] += NORTH_SHIFT
    roads['COURT_ACCESS_3']['polyline_m'][0][1] += NORTH_SHIFT
    roads['COURT_ACCESS_3']['polyline_m'][-1][1] += SOUTH_SHIFT
    roads['R_REAR']['polyline_m'][0][1] = AVENUE_Y
    for p in roads['R_REAR']['polyline_m'][1:]:
        p[1] += NORTH_SHIFT
    roads['ACCESS_P13-4']['polyline_m'] = v10.shifted(roads['ACCESS_P13-4'], SOUTH_SHIFT)['polyline_m']
    for q in (d['boundary'], next(q for q in d['districts'] if q['id'] == 'residential')):
        q['polygon_m'] = [[x, y + NORTH_SHIFT if y == 865 else y] for x, y in q['polygon_m']]
    ds = next(q for q in d['districts'] if q['id'] == 'residential')
    ds['notes_ru'] = 'Проспект y=723,5; корпуса по обе стороны в 10 м от его кромок. Север +12 м, двор 3 −1 м; стык со старым городом открыт.'
    removed = {'BAD_OLD_1', 'BAD_OLD_2', 'OLD_INDUSTRIAL_1', 'OLD_INDUSTRIAL_2'}
    d['vegetation_parcels'] = [q for q in d['vegetation_parcels'] if q['id'] not in removed]
    for q in d['vegetation_parcels']:
        if q['id'] == 'TRANSITION_URBAN_1':
            q['polygon_m'] = [[468, 440], [472, 440], [472, AVENUE_Y-3.5], [468, AVENUE_Y-3.5]]
        elif q['id'] == 'TRANSITION_URBAN_2':
            q['polygon_m'] = [[468, AVENUE_Y+3.5], [472, AVENUE_Y+3.5], [472, 877], [468, 877]]
        if q['kind'] != 'interdistrict_barrier':
            continue
        if q['id'].startswith(('FOREST_VILLAGE', 'RURAL_TRANSITION', 'VALLEY_NORTH')) or q['id'] == 'VALLEY_BEACH_FENCE':
            material, height, trees = 'wooden_fence', 1.6, True
        elif q['id'].startswith(('OLD_ELITE', 'ELITE_')):
            material, height, trees = 'elite_fence', 2.4, False
        elif q['material'] == 'rock_scarp':
            material, height, trees = 'rock_scarp', q['height_target_m'], False
        else:
            material, height, trees = 'concrete_fence', 2.5, False
        q.update(material=material, height_target_m=height, tree_line=trees)
    # Thin railings along each bank; the steep canal, not a green belt, separates districts.
    for bank, y in (('N', 444), ('S', 436)):
        for side, x1, x2 in (('W', 510, 647), ('E', 653, 796)):
            d['vegetation_parcels'].append(dict(id=f'CANAL_RAILING_{bank}_{side}',
                kind='interdistrict_barrier', district_id='old_town' if bank == 'N' else 'industrial',
                polygon_m=[[x1, y-.5], [x2, y-.5], [x2, y+.5], [x1, y+.5]],
                material='canal_railing', height_target_m=1.1, tree_line=False,
                blocks_foot=True, blocks_van=True, continuity_group='CANAL_BANKS', gate_road_id='I_CONNECT'))
    canal = next(w for w in d['water'] if w['id'] == 'CANAL')
    canal.update(material='canal_railing', height_target_m=1.1, tree_line=False,
        banks='steep_concrete with canal_railing 1.1m; only I_CONNECT road bridge; sealed outlet under BEACH to SEA; no footbridges')
    # Keep the original report compact: three follow-up lines replace its last three notes.
    d['planning_notes_ru'][-3:] = [
        'Проспект y=723,5: зазоры до северных и южных корпусов по 10 м. Двор 3 −1 м, северные дворы/службы/пост/граница +12 м; размеры и этажность сохранены.',
        'Двор 3: до края старого города 4 м, до его зданий 8 м (требование ≥5 м); подъезды к B03, киоскам 1–2, магазину, ATM и бару ≤25 м.',
        'Спальник/старый город без ограды; промзону отделяет канал с перилами 1,1 м. Элитка: ограда 2,4 м; городская кромка: бетон 2,5 м; сельские границы: дерево 1,6 м + отдельные деревья.']


def clean(q):
    return {k: v for k, v in q.items() if k not in ('road_node_id', 'dead_end_node_id')}


def corridor(poly, road):
    return any(v7.gap(poly, a, b) < road['width_m'] / 2 - .005
               for a, b in zip(road['polyline_m'], road['polyline_m'][1:]))


def on_edge(p, poly):
    return m.inside(p, poly) or any(m.projection(p, a, b)[0] < .005 for a, b in v7.edges(poly))


def reachable(graph, start, removed_roads=(), removed_nodes=()):
    adj = {n['id']: set() for n in graph['nodes']}
    for e in graph['edges']:
        if e['road_id'] in removed_roads or set((e['from_node'], e['to_node'])) & set(removed_nodes):
            continue
        adj[e['from_node']].add(e['to_node'])
        adj[e['to_node']].add(e['from_node'])
    seen, todo = set(), [start]
    while todo:
        n = todo.pop()
        if n not in seen:
            seen.add(n)
            todo.extend(adj[n] - seen)
    return seen


def validate_targeted(d, check):
    old = source_data()
    fs = {f['id']: f for f in d['functional_buildings']}
    bs = {b['id']: b for b in d['building_masses']}
    pts = {p['id']: p for p in d['points']}
    roads = {r['id']: r for r in d['roads']}
    ds = {q['id']: q for q in d['districts']}
    beach = d['beaches'][0]
    sand = beach['polygon_m']
    sea = next(w for w in d['water'] if w['id'] == 'SEA')
    check('v10 schema retained; only beaches added at top level',
          d['schema_version'] == old['schema_version'] and set(d) == set(old) | {'beaches'} and
          all(type(d[k]) == type(v) for k, v in old.items()))
    check('boundary only new nested key is coast_segments_m', set(d['boundary']) == set(old['boundary']) | {'coast_segments_m'})
    check('all 88 building identities retained', len(v7.physical(d)) == 88 and
          {b['id'] for b in d['building_masses']} == {b['id'] for b in old['building_masses']} and
          set(fs) == {f['id'] for f in old['functional_buildings']})
    preserved = ('farmsteads', 'hills', 'field_parcels_m', 'paths', 'road_classes',
                 'coordinates', 'geometry_repairs', 'land_transfers', 'replaced_generic_building_ids',
                 'sightline', 'distribution_targets')
    check('all unrelated top-level geometry and settings unchanged', all(d[k] == old[k] for k in preserved))
    allowances = {
        'functional_buildings': INDUSTRIAL_IDS | {'F06_CHURCH'} | FRONT_FUNCTIONS |
            {q['id'] for q in old['functional_buildings'] if q['district_id'] == 'residential' and q['center_m'][1] > 718},
        'building_masses': set(HOUSE_MOVES) | {q['id'] for q in old['building_masses'] if q['kind'] == 'slab'},
        'plots': {bid + '_FRONT' for bid in HOUSE_MOVES},
        'roads': ALTERED_ROADS | FOLLOWUP_ROADS | {'EXIT_S'},
        'points': {'B05', 'P12', 'P14', 'CHIMNEY', 'P09-3', 'P16-3', 'B03', 'P11-2', 'BAD_CENTER', 'BAD_BLOCK_3', 'P13-4'} |
            {q['id'] for q in old['points'] if q.get('district_id') == 'residential' and q['position_m'][1] > 718},
        'functional_sites': {'F06_TOW_YARD', 'F06_SCRAP_YARD', 'SITE_P09-3', 'SITE_P09-2'},
        'vegetation_parcels': {q['id'] for q in old['vegetation_parcels'] if q['kind'] == 'interdistrict_barrier'},
    }
    for key, allowed in allowances.items():
        now = {q['id']: q for q in d[key]}
        unchanged = [q for q in old[key] if q['id'] not in allowed]
        check(key + ' unaffected records exactly retained', all(q['id'] in now and clean(now[q['id']]) == clean(q) for q in unchanged))
    for key in ('width_m', 'depth_m', 'floors', 'district_id'):
        check('moved houses retain ' + key, all(bs[bid][key] == next(b for b in old['building_masses'] if b['id'] == bid)[key] for bid in HOUSE_MOVES))
    check('24 small houses retained', sum('terrace_id' in b for b in bs.values()) == 24)
    ring = roads['O_RING']['polyline_m'][:-1]
    check('two supermarket houses moved across west ring; other two stay',
          all(not m.inside(bs[bid]['center_m'], ring) and bs[bid]['center_m'][0] < 525 for bid in ('O06_T1_U1', 'O06_T1_U3')) and
          all(bs[bid]['center_m'] == next(b for b in old['building_masses'] if b['id'] == bid)['center_m'] for bid in ('O06_T1_U4', 'O06_T1_U6')))
    # Two houses follow the west leg; four follow the south leg, spaced 18–19 m.
    spacing = [m.length(bs[a]['center_m'], bs[b]['center_m']) for a, b in zip(CLUSTER, CLUSTER[1:])]
    check('post-office houses individually spaced 15 to20m along ring legs', all(15 <= s <= 20 for s in spacing), str(spacing))
    front_hits = []
    for bid in HOUSE_MOVES:
        p = next(p for p in d['plots'] if p['id'] == bid + '_FRONT')['polygon_m']
        c = [sum(q[k] for q in p) / len(p) for k in (0, 1)]
        bc = bs[bid]['center_m']
        distance = min(m.projection(c, a, b)[0] for a, b in zip(roads['O_RING']['polyline_m'], roads['O_RING']['polyline_m'][1:]))
        original = min(m.projection(bc, a, b)[0] for a, b in zip(roads['O_RING']['polyline_m'], roads['O_RING']['polyline_m'][1:]))
        if not distance < original or corridor(p, roads['O_RING']):
            front_hits.append(bid)
    check('all eight moved house fronts face ring and gardens clear carriageway', not front_hits, str(front_hits))
    check('church shifted southwest and access attached to ring', fs['F06_CHURCH']['center_m'] == [572, 524] and fs['F06_CHURCH']['access_road_id'] == 'O_RING')
    check('industrial zone shrunken and northern edge unchanged', m.area(ds['industrial']['polygon_m']) < m.area(next(q for q in old['districts'] if q['id'] == 'industrial')['polygon_m']) and max(p[1] for p in ds['industrial']['polygon_m']) == 440)
    check('railway retains full forest and valley course and endpoint at depot', d['railway']['polyline_m'][:5] == old['railway']['polyline_m'][:5] and
          d['railway']['polyline_m'][5] == [510, 396.25] and m.projection([510, 396.25], *old['railway']['polyline_m'][4:6])[0] < .001 and
          d['railway']['polyline_m'][-1] == old['railway']['polyline_m'][-1] and m.length(fs['F06_DEPOT']['center_m'], d['railway']['polyline_m'][-1]) == 17)
    rail_y = lambda x: 396.25 - (x - 510) * 36.25 / 16 if x < 526 else 360
    industrial = [q for q in v7.physical(d) if q['district_id'] == 'industrial']
    check('all eight industrial footprints fully north of railway', len(industrial) == 8 and all(p[1] >= rail_y(p[0]) + 2 for q in industrial for p in q['poly']))
    check('industrial strip south of railway at most20m', all(rail_y(p[0]) - p[1] <= 20.005 for p in ds['industrial']['polygon_m']))
    sites = {s['id']: s for s in d['functional_sites']}
    check('B05 tow and scrap yards entirely north of railway and inside industry',
          all(p[1] > rail_y(p[0]) and on_edge(p, ds['industrial']['polygon_m']) for sid in ('B05_YARD', 'F06_TOW_YARD', 'F06_SCRAP_YARD') for p in sites[sid]['polygon_m']))
    check('meeting P09-3 next to B05; matching site position', m.length(pts['P09-3']['position_m'], fs['F06_COMPLEX']['center_m']) < 40 and sites['SITE_P09-3']['position_m'] == pts['P09-3']['position_m'])
    check('yard roads north of railway; no level crossings remain', all(p[1] > rail_y(p[0]) for r in d['roads'] if 'industrial' in r.get('district_ids', []) for p in r['polyline_m']) and not d['railway']['road_crossings'])
    check('only NW NE exits; south post road trigger barriers entirely removed',
          {e['id'] for e in d['exits']} == {'NW', 'NE'} and 'P16-3' not in pts and 'EXIT_S' not in roads and
          not any(e['road_id'] == 'EXIT_S' for e in d['road_graph']['edges']))
    check('NW unchanged; NE dead end barriers and trigger translated exactly12m',
          [clean(e) for e in d['exits']] == [clean(v10.shifted(e, NORTH_SHIFT) if e['id'] == 'NE' else e) for e in old['exits'] if e['id'] != 'S'])
    for district in old['districts']:
        if district['id'] not in ('fields', 'industrial', 'residential'):
            check(district['id'] + ' district geometry unchanged', ds[district['id']]['polygon_m'] == district['polygon_m'])
    check('lake and both rivers unchanged', [w for w in d['water'] if w['id'] not in ('SEA', 'CANAL')] == [w for w in old['water'] if w['id'] != 'CANAL'])
    check('canal only shortened4m at outlet; culvert passes under sand to SEA', canal_check(d, sand, sea, sites))
    # Normal separation for each of the five inner/outer shoreline legs.
    widths = [m.projection([(a[0] + b[0]) / 2, (a[1] + b[1]) / 2], c, e)[0]
              for a, b, c, e in zip(BEACH_LAND, BEACH_LAND[1:], COAST, COAST[1:])]
    check('continuous sand beach width20to30m along all five coast legs', beach['surface'] == 'sand' and all(20 <= w <= 30 for w in widths), str(widths))
    b_hits = [b['id'] for b in v7.physical(d) if positive_overlap(b['poly'], sand)]
    s_hits = [b['id'] for b in v7.physical(d) if positive_overlap(b['poly'], sea['polygon_m'])]
    check('beach and sea outside every building', not b_hits and not s_hits, str([b_hits, s_hits]))
    beach_roads = [r['id'] for r in d['roads'] if corridor(sand, r)]
    sea_roads = [r['id'] for r in d['roads'] if corridor(sea['polygon_m'], r)]
    check('beach touches only elite access road; sea clear of every road', beach_roads == ['BEACH_ACCESS'] and not sea_roads, str([beach_roads, sea_roads]))
    district_hits = [(q['id'], zone) for q in d['districts'] for zone, poly in [('beach', sand), ('sea', sea['polygon_m'])] if positive_overlap(q['polygon_m'], poly)]
    check('beach and sea have no positive-area overlap with districts', not district_hits, str(district_hits))
    partition = [q['polygon_m'] for q in d['districts']] + [sand]
    partition_hits = [(i, j) for i, p in enumerate(partition) for j, q in enumerate(partition[i+1:], i+1) if positive_overlap(p, q)]
    check('district and beach partition has no overlaps and covers only playable land', not partition_hits and
          all(abs(intersection_area(p, d['boundary']['polygon_m']) - m.area(p)) < .01 for p in partition), str(partition_hits))
    check('beach lies inside playable boundary; SEA lies outside', all(on_edge(p, d['boundary']['polygon_m']) for p in sand) and not positive_overlap(d['boundary']['polygon_m'], sea['polygon_m']))
    check('beach turnaround on dry sand and clear of sea', all(on_edge(p, sand) for p in sites['BEACH_TURNAROUND']['polygon_m']) and not v7.overlap(sites['BEACH_TURNAROUND']['polygon_m'], sea['polygon_m']))
    check('beach access single short branch from ELITE_SOUTH', beach['access_road_ids'] == ['BEACH_ACCESS'] and roads['BEACH_ACCESS']['polyline_m'][0] == [900, 485] and sum(m.length(a, b) for a, b in zip(roads['BEACH_ACCESS']['polyline_m'], roads['BEACH_ACCESS']['polyline_m'][1:])) == 37)
    for mode, graph in [('vehicle', d['road_graph']), ('walking', d['pedestrian_graph'])]:
        beach_nodes = {n['id'] for n in graph['nodes'] if m.inside(n['position_m'], sand)}
        start = pts['B01']['road_node_id']
        gate = pts['ELITE_GATE']['road_node_id']
        access_cut = reachable(graph, start, ['BEACH_ACCESS'])
        elite_cut = reachable(graph, start, ['ELITE_GATE_ROAD'])
        node_cut = reachable(graph, start, removed_nodes=[gate])
        check(mode + ' graph reaches beach only through elite and its access', bool(beach_nodes) and beach_nodes <= reachable(graph, start) and
              not beach_nodes & access_cut and not beach_nodes & elite_cut and not beach_nodes & node_cut)
    check('no B06 private beach road or walking path', d['paths'] == [] and next(r for r in d['roads'] if r['id'] == 'ACCESS_B06') == next(r for r in old['roads'] if r['id'] == 'ACCESS_B06'))
    fences = {q['id']: q for q in d['vegetation_parcels']}
    check('continuous foot and van fence along industry beach sides',
          all(fences[s]['blocks_foot'] and fences[s]['blocks_van'] for s in ('INDUSTRIAL_BEACH_FENCE', 'OLD_TOWN_BEACH_FENCE', 'VALLEY_BEACH_FENCE')) and
          all(on_edge(p, fences['INDUSTRIAL_BEACH_FENCE']['polygon_m']) for p in BEACH_LAND[1:4] + [[800, 440]]))
    check('valley end closed; elite south fence has exactly6m gate',
          fences['BEACH_WEST_ROCKS']['blocks_foot'] and fences['BEACH_EAST_ROCKS']['blocks_foot'] and
          max(p[0] for p in fences['ELITE_BEACH_1']['polygon_m']) == 897 and min(p[0] for p in fences['ELITE_BEACH_2']['polygon_m']) == 903)
    check('SEA returns player and van to last ground point; extends at least150m', sea['kind'] == 'sea' and sea['name_ru'] == 'Море' and sea['return_rule'] == 'return_to_last_ground_point' and
          min(p[1] for p in sea['polygon_m']) <= min(p[1] for p in COAST) - 150 and max(p[0] for p in sea['polygon_m']) >= max(p[0] for p in COAST) + 150)
    check('coast segments match sea edge; wall exception explicit', d['boundary']['coast_segments_m'] == [[a, b] for a, b in zip(COAST, COAST[1:])] and 'no wall' in d['boundary']['barrier'])
    check('remaining boundary edges retain 5m wall band', d['boundary']['barrier_band_m'] == old['boundary']['barrier_band_m'] == 5 and 'every non-coast edge' in d['boundary']['barrier'])
    check('all road centre lines inside playable boundary', all(on_edge(p, d['boundary']['polygon_m']) for r in d['roads'] for p in r['polyline_m']))
    slabs = [b for b in bs.values() if b['kind'] == 'slab']
    clearance = min(v7.gap(b['polygon_m'], a, c) - r['width_m'] / 2 for b in slabs for r in d['roads'] for a, c in zip(r['polyline_m'], r['polyline_m'][1:]))
    check('all nine slabs at least3m clear of all road edges', clearance >= 3 - .005, f'{clearance:.3f} m')
    frontage = ['ACCESS_B03', 'ACCESS_F06_K1', 'ACCESS_F06_K2', 'ACCESS_F06_24', 'ACCESS_P06', 'ACCESS_P11-2']
    frontage_lengths = {rid: sum(m.length(a, b) for a, b in zip(roads[rid]['polyline_m'], roads[rid]['polyline_m'][1:])) for rid in frontage}
    check('v10 southern residential frontage accesses remain at most25m', all(v <= 25 for v in frontage_lengths.values()), str(frontage_lengths))
    validate_followup(d, check)


def courtyard_gaps(d):
    slabs = [q for q in d['building_masses'] if q['kind'] == 'slab']
    avenue = next(r for r in d['roads'] if r['id'] == 'ARC_AVENUE')
    y = avenue['polyline_m'][0][1]
    half = avenue['width_m']/2
    south = [b for b in slabs if b['id'].startswith('R06_C3_')]
    north = [b for b in slabs if b not in south]
    return (min(p[1] for b in north for p in b['polygon_m']) - y - half,
            y - half - max(p[1] for b in south for p in b['polygon_m']))


def validate_followup(d, check):
    old = source_data()
    oldbs = {b['id']: b for b in old['building_masses']}
    slabs = [b for b in d['building_masses'] if b['kind'] == 'slab']
    check('all nine slabs retain v10 x positions dimensions floors and exact shapes',
          all(b == v10.shifted(oldbs[b['id']], SOUTH_SHIFT if b['id'].startswith('R06_C3_') else NORTH_SHIFT) for b in slabs))
    check('three courtyard yards translated with unchanged v10 interlocking arrangement',
          d['microdistricts'] == [v10.shifted(c, NORTH_SHIFT if i < 2 else SOUTH_SHIFT) for i, c in enumerate(old['microdistricts'])] and
          all(min(p[0] for p in oldbs[bid]['polygon_m']) < x < max(p[0] for p in oldbs[bid]['polygon_m'])
              for bid, x in (('R06_C1_S1', 552.5), ('R06_C2_S1', 632.5))))
    north_gap, south_gap = courtyard_gaps(d)
    check('avenue has10m slab clearance on both sides', abs(north_gap-10) < .001 and abs(south_gap-10) < .001, f'north {north_gap:.3f}m; south {south_gap:.3f}m')
    roads = {r['id']: r for r in d['roads']}
    check('avenue straight y723.5; aligned transition connector; town connector x650',
          roads['ARC_AVENUE']['polyline_m'] == [[470, AVENUE_Y], [770, AVENUE_Y]] and
          roads['ARC_RURAL']['polyline_m'][-2:] == [[405, AVENUE_Y], [470, AVENUE_Y]] and
          roads['OLD_TOWN_CONNECTOR']['polyline_m'] == [[650, AVENUE_Y], [650, 540], [800, 540]])
    southern = [b for b in slabs if b['id'].startswith('R06_C3_')]
    edge_gap = min(p[1] for b in southern for p in b['polygon_m']) - 620
    oldtown = [b for b in v7.physical(d) if b['district_id'] == 'old_town']
    building_gap = min(v7.gap(b['polygon_m'], a, c) for b in southern for f in oldtown for a, c in v7.edges(f['poly']))
    check('court3 maximally south with4m district clearance and at least5m to town buildings', abs(edge_gap-4) < .001 and building_gap >= 5 - .005,
          f'district {edge_gap:.3f}m; buildings {building_gap:.3f}m')
    for key in ('functional_buildings', 'points', 'functional_sites'):
        before = [q for q in old[key] if q.get('district_id') == 'residential' and q.get('center_m', q.get('position_m', [0, 0]))[1] > 718]
        now = {q['id']: q for q in d[key]}
        check(key + ' every northern service and reference translated exactly12m', all(clean(now[q['id']]) == clean(v10.shifted(q, NORTH_SHIFT)) for q in before))
    check('northern district and boundary expanded exactly12m; coast preserved',
          next(q['polygon_m'] for q in d['districts'] if q['id'] == 'residential') == [[470, 620], [780, 620], [780, 877], [470, 877]] and
          max(p[1] for p in d['boundary']['polygon_m']) == 877 and d['metrics']['extent_m'] == [815, 562] and
          d['boundary']['coast_segments_m'] == [[a, b] for a, b in zip(COAST, COAST[1:])])
    check('den road between northern courts; south stub retained in court3 yard',
          roads['COURT_ACCESS_3']['polyline_m'] == [[592.5, 832], [592.5, 674]] and
          roads['R_REAR']['polyline_m'] == [[710, AVENUE_Y], [710, 832], [535, 832]] and
          roads['ACCESS_P13-4']['polyline_m'] == [[592.5, 674], [606, 674]])
    before_roads = {r['id']: r for r in old['roads']}
    check('all northern access and exit roads translated exactly12m',
          all(roads[rid] == v10.shifted(before_roads[rid], NORTH_SHIFT) for rid in NORTH_ROADS))
    parcels = {q['id']: q for q in d['vegetation_parcels']}
    check('bad old-town seam has no separator; old industrial belts removed',
          not {'BAD_OLD_1', 'BAD_OLD_2', 'OLD_INDUSTRIAL_1', 'OLD_INDUSTRIAL_2'} & parcels.keys() and
          not any(q.get('continuity_group') in ('BAD_OLD', 'OLD_INDUSTRIAL') for q in parcels.values()))
    groups = [(['OLD_ELITE_1', 'OLD_ELITE_2', 'ELITE_NORTH_FENCE'], 'elite_fence', 2.4, False),
        (['TRANSITION_URBAN_1', 'TRANSITION_URBAN_2', 'VALLEY_URBAN'], 'concrete_fence', 2.5, False),
        (['FOREST_VILLAGE_1', 'FOREST_VILLAGE_2', 'RURAL_TRANSITION_1', 'RURAL_TRANSITION_2', 'VALLEY_NORTH_1', 'VALLEY_NORTH_2'], 'wooden_fence', 1.6, True)]
    for ids, material, height, trees in groups:
        check(material + ' borders have exact height and tree-line settings',
              all(parcels[q]['kind'] == 'interdistrict_barrier' and parcels[q]['material'] == material and
                  parcels[q]['height_target_m'] == height and parcels[q]['tree_line'] == trees for q in ids))
    check('concrete transition fence follows shifted avenue with exact7m opening',
          max(p[1] for p in parcels['TRANSITION_URBAN_1']['polygon_m']) == AVENUE_Y-3.5 and
          min(p[1] for p in parcels['TRANSITION_URBAN_2']['polygon_m']) == AVENUE_Y+3.5 and
          max(p[1] for p in parcels['TRANSITION_URBAN_2']['polygon_m']) == 877)
    canal = next(w for w in d['water'] if w['id'] == 'CANAL')
    railings = [q for q in parcels.values() if q.get('material') == 'canal_railing']
    check('canal separates town industry; four thin1.1m railings; only road bridge',
          canal['material'] == 'canal_railing' and canal['height_target_m'] == 1.1 and canal['banks'].startswith('steep_concrete') and
          len(railings) == 4 and all(q['height_target_m'] == 1.1 and not q['tree_line'] for q in railings) and
          {s['road_id'] for s in d['water_crossings'] if s['water_id'] == 'CANAL'} == {'I_CONNECT'})
    check('elite district entry remains only at security booth road',
          parcels['OLD_ELITE_1']['gate_road_id'] == parcels['OLD_ELITE_2']['gate_road_id'] == 'OLD_TOWN_CONNECTOR' and
          roads['ELITE_GATE_ROAD']['polyline_m'][0] == [800, 540] and next(f for f in d['functional_buildings'] if f['id'] == 'F06_GUARD')['access_road_id'] == 'ELITE_GATE_ROAD')
    check('all separators have believable material height and explicit tree_line',
          all(q['material'] in FENCE_STYLES and isinstance(q['tree_line'], bool) and q['height_target_m'] > 0 for q in parcels.values() if q['kind'] == 'interdistrict_barrier'))


def canal_check(d, sand, sea, sites):
    c = next(w for w in d['water'] if w['id'] == 'CANAL')
    old = next(w for w in source_data()['water'] if w['id'] == 'CANAL')
    q = sites['CANAL_BEACH_CULVERT']
    return (c['centerline_m'] == old['centerline_m'][:-1] + [[796, 440]] and q['polyline_m'][0] == c['centerline_m'][-1] and
            m.inside(q['polyline_m'][-1], sea['polygon_m']) and q['tunnel_carrier'] == 'water_below_sand' and
            not corridor(sand, dict(polyline_m=c['centerline_m'], width_m=c['width_m'])))


def triangles(poly):
    """Ear-clip simple polygons for exact positive-area intersection checks."""
    p = [list(q) for q in poly]
    cross = lambda a, b, c: (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    signed = sum(a[0]*b[1]-b[0]*a[1] for a, b in v7.edges(p))
    if signed < 0:
        p.reverse()
    result = []
    while len(p) > 3:
        for i, b in enumerate(p):
            a, c = p[i-1], p[(i+1) % len(p)]
            if cross(a, b, c) <= 1e-8:
                continue
            others = [q for j, q in enumerate(p) if j not in (i, (i-1) % len(p), (i+1) % len(p))]
            if any(all(cross(u, v, q) >= -1e-8 for u, v in v7.edges([a, b, c])) for q in others):
                continue
            result.append([a, b, c])
            del p[i]
            break
        else:
            raise ValueError('Cannot triangulate polygon: ' + str(p))
    result.append(p)
    return result


def intersection_area(a, b):
    total = 0
    for ta in triangles(a):
        for tb in triangles(b):
            clipped = ta
            for u, v in v7.edges(tb):
                side = lambda p: (v[0]-u[0])*(p[1]-u[1]) - (v[1]-u[1])*(p[0]-u[0])
                output = []
                if not clipped:
                    break
                for x, y in v7.edges(clipped):
                    sx, sy = side(x), side(y)
                    if sx >= -1e-8:
                        output.append(x)
                    if (sx < -1e-8) != (sy < -1e-8):
                        t = sx / (sx - sy)
                        output.append([x[k] + t*(y[k]-x[k]) for k in (0, 1)])
                clipped = output
            if len(clipped) >= 3:
                total += m.area(clipped)
    return total


def positive_overlap(a, b):
    if any(max(p[k] for p in a) <= min(p[k] for p in b) + .001 or
           max(p[k] for p in b) <= min(p[k] for p in a) + .001 for k in (0, 1)):
        return False
    return intersection_area(a, b) > .01


def separator_axis(q):
    p = q['polygon_m']
    if len(p) == 4 and max(a[1] for a in p)-min(a[1] for a in p) > max(a[0] for a in p)-min(a[0] for a in p):
        pairs = [(p[0], p[1]), (p[2], p[3])]
    else:
        pairs = [(p[i], p[-1-i]) for i in range(len(p)//2)]
    return [[(a[k]+b[k])/2 for k in (0, 1)] for a, b in pairs]


def draw_separator(q, line, svg, xy):
    color, width, _ = FENCE_STYLES[q['material']]
    axis = separator_axis(q)
    line(axis, color, width, **({'stroke_dasharray': '3 3'} if q['material'] == 'rock_scarp' else {}))
    if q['tree_line']:
        for a, b in zip(axis, axis[1:]):
            n = m.length(a, b)
            dx, dy = b[0]-a[0], b[1]-a[1]
            for i in range(max(0, int((n-12)/12)+1)):
                t = (6 + i*12)/n
                tree = [a[0]+t*dx-3*dy/n, a[1]+t*dy+3*dx/n]
                svg.circle(*xy(tree), 3, '#93aa80', stroke='#6e8865', stroke_width=.8)


def analysis_scope():
    """Compile v10's inherited checks and renderer with scoped v11 updates."""
    src = (ROOT / 'map_plan_v10.py').read_text(encoding='utf-8')
    fn = src[src.index('def analysis_scope():'):src.index('\ndef report(')]
    analysis_edits = {
        "abs(sum(d['area_m2'] for d in data['districts'])-total)<.01":
            "abs(sum(d['area_m2'] for d in data['districts']) + sum(m.area(b['polygon_m']) for b in data['beaches']) - total)<.01",
        'districts partition the playable area': 'districts plus beach partition playable area',
        'physical count: v09 minus six T4 houses': 'physical count:88 retained from v10',
        "('transition/bad',[470,718],'ARC_RURAL')": "('transition/bad',[470,723.5],'ARC_RURAL')",
        'barrier belts closed except exact road openings': 'material fences and canal railings leave road openings clear',
    }
    inject = '\n'.join('    analysis = replace_exact(analysis, ' + repr(a) + ', ' + repr(b) + ')'
                       for a, b in analysis_edits.items())
    fn = v10.replace_exact(fn, '    scope = dict(vars(v7))', inject + '\n    scope = dict(vars(v7))')
    render_edits = {
        'v10': 'v11', '815 × 725 м': '815 × 562 м',
        'узкие дороги • один въезд между районами • решения 04.10.2026': 'проспект y=723,5 • зазоры 10 / 10 м • решения 04.10.2026',
        '([640,855]': '([640,867]',
        'Район → площадь: 178 м; элитка: ещё 150 м.': 'Район → площадь: 183,5 м; элитка: ещё 150 м.',
        'Один въезд на район; за городом петель нет.': 'Спальник и старый город без ограды.',
        'Ограды / скалы / канал закрывают срезки.': 'Заборы по месту; канал без пеших мостов.',
        "s.add('<g clip-path=\"url(#land)\">')":
            "polygon(next(w['polygon_m'] for w in data['water'] if w['id']=='SEA'),'#91c3d9','#739eaf',1)\n    s.add('<g clip-path=\"url(#land)\">')",
        "    for d in data['districts']:polygon(d['polygon_m'],d['color'],'#a7aa99',1)":
            "    for d in data['districts']:polygon(d['polygon_m'],d['color'],'#a7aa99',1)\n    for b in data['beaches']:polygon(b['polygon_m'],'#efd69a','#c8ad6d',1)",
        "    for w in data['water']:\n": "    for w in data['water']:\n        if w['id']=='SEA':continue\n",
        "            polygon(q['polygon_m'],'#70846b','#516a55',.8)": "            pass  # Fences are drawn as material-specific thin lines after water.",
        "    for structure in data['water_crossings']:": "    for q in data['vegetation_parcels']:\n        if q['kind']=='interdistrict_barrier':draw_separator(q,line,s,xy)\n    for structure in data['water_crossings']:",
        "    line(bp+[bp[0]],'#61765e',5)\n    line(bp+[bp[0]],'#d8d9c7',1,stroke_dasharray='3 7')":
            "    for a,b in edges(bp):\n        coast=any([a,b]==q or [b,a]==q for q in data['boundary']['coast_segments_m'])\n        line([a,b],'#6bacc2' if coast else '#777d7b',1.5 if coast else 3)\n        if not coast:line([a,b],'#d8d9c7',1,stroke_dasharray='3 7')",
        "([700,265],'ПРОМЫШЛЕННАЯ ОКРАИНА'": "([535,350],'ПРОМЫШЛЕННАЯ ОКРАИНА'",
        "s.text(x,y,title,size=22,weight='bold',anchor=anchor,halo=True)": "s.text(x,y,title,size=18 if title=='ПРОМЫШЛЕННАЯ ОКРАИНА' else 22,weight='bold',anchor=anchor,halo=True)",
        "s.text(x,y+24,sub,size=15,anchor=anchor,color='#65776b',halo=True)": "s.text(x,y+(17 if title=='ПРОМЫШЛЕННАЯ ОКРАИНА' else 24),sub,size=15,anchor=anchor,color='#65776b',halo=True)",
        "('CLOCK_SQUARE','BAD_CENTER','ELITE_GATE') else p['id']": "('CLOCK_SQUARE','BAD_CENTER','ELITE_GATE','BEACH_ENTRY') else p['id']",
        "    for ex in data['exits']:\n        for p in ex['barrier_polygons_m']":
            "    for site in data['functional_sites']:\n        if site['id']=='BEACH_TURNAROUND':polygon(site['polygon_m'],'#d9cba5','#9c947b',1)\n        if site['id']=='CANAL_BEACH_CULVERT':line(site['polyline_m'],'#557c88',1.6,stroke_dasharray='3 4')\n    for ex in data['exits']:\n        for p in ex['barrier_polygons_m']",
        "    used=[]":
            "    x,y=xy([700,327]);s.text(x,y,'ПЛЯЖ / 25 м',size=16,anchor='middle',halo=True)\n    x,y=xy([650,225]);s.text(x,y,'МОРЕ / ВНЕ КАРТЫ',size=25,anchor='middle',color='#3c718a')\n    s.text(x,y+28,'Игрок / бусик → последняя точка суши',size=17,anchor='middle',color='#3c718a')\n    x,y=xy([872,455]);s.text(x,y,'Вход только через элитку',size=13,anchor='middle',halo=True)\n    used=[]",
        "'P05 на стыке районов; P12 у конца старой ЖД.'": "'Пляж: один вход через ELITE_SOUTH.'",
    }
    render_inject = '\n'.join('    renderer = replace_exact(renderer, ' + repr(a) + ', ' + repr(b) + ')'
                              for a, b in render_edits.items())
    legend_inject = """    legend = legend.replace('v10','v11')
    legend = replace_exact(legend, "    y+=15;s.text(x,y,'ЦВЕТ И ЗНАК = ФУНКЦИЯ'", "    for color,label in [('#efd69a','Пляж / песок / вход из элитки'),('#91c3d9','Море / возврат на последнюю сушу')]:\\n        s.rect(x,y-13,18,16,color);s.text(x+28,y,label,size=14);y+=25\\n    y+=15;s.text(x,y,'ЦВЕТ И ЗНАК = ФУНКЦИЯ'")
"""
    old_legend = """    for color,label,dash in [('#747080','Старая ЖД / депо у конца','2 7'),('#70846b','Сплошной барьер; разрыв = въезд',None)]:
        s.line([[x,y-5],[x+34,y-5]],color,5,**({'stroke_dasharray':dash} if dash else {}))
        s.text(x+44,y,label,size=14);y+=25"""
    new_legend = """    s.line([[x,y-5],[x+34,y-5]],'#747080',5,stroke_dasharray='2 7')
    s.text(x+44,y,'Старая ЖД / депо у конца',size=14);y+=25
    for material in ('concrete_fence','wooden_fence','elite_fence','canal_railing'):
        color,width,label=FENCE_STYLES[material]
        s.line([[x,y-5],[x+34,y-5]],color,width)
        if material=='wooden_fence':s.circle(x+17,y-10,3,'#93aa80',stroke='#6e8865',stroke_width=.8)
        s.text(x+44,y,label,size=14);y+=25"""
    legend_inject += '    legend = replace_exact(legend, ' + repr(old_legend) + ', ' + repr(new_legend) + ')\n'
    fn = v10.replace_exact(fn, "    exec(compile(legend, str(ROOT / 'map_plan_v10.py'), 'exec'), scope)",
                          render_inject + '\n' + legend_inject + "    exec(compile(legend, str(ROOT / 'map_plan_v11.py'), 'exec'), scope)")
    env = dict(vars(v10))
    env.update(hashes=hashes, validate_targeted=validate_targeted)
    exec(compile(fn, str(ROOT / 'map_plan_v11.py'), 'exec'), env)
    scope = env['analysis_scope']()
    scope.update(FENCE_STYLES=FENCE_STYLES, draw_separator=draw_separator)
    scope['ROUTES'] += [('ELITE_GATE', 'BEACH_ENTRY'), ('B01', 'BEACH_ENTRY')]
    return scope


def report(d):
    checks = d['validation']['checks']
    lines = ['# VOLUNTEERS ONLY — R01 v11', '',
        'Основание: req_map_plan_v11.md + req_map_plan_v11_followup.md; правки v10 от 04.10.2026.',
        f'Карта: {d["metrics"]["extent_m"][0]:.0f} × {d["metrics"]["extent_m"][1]:.0f} м; {d["metrics"]["area_m2"]:.1f} м²; 88 зданий; SVG/PNG 2400 × 2400.',
        *d['planning_notes_ru'], '',
        '| Маршрут | Дорога, м | 60 км/ч, с | 90 км/ч, с | Пешком, м / мин |',
        '|---|---:|---:|---:|---:|']
    for r in d['metrics']['routes']:
        lines.append(f'| {r["from_id"]} → {r["to_id"]} | {r["length_m"]:.1f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["pedestrian_length_m"]:.1f} / {r["walk_5_minutes"]:.2f} |')
    lines += ['', f'Проверки: {sum(c["passed"] for c in checks)}/{len(checks)} — PASS; полный перечень и детали в validation.checks JSON.',
        'Повторены все дистанционные ограничения v10, авто/пешая связность, единственные въезды и возврат через два сохранившихся поста.',
        'Пересечения зданий друг с другом / дорогами / водой / ЖД: 0 / 0 / 0 / 0; до кромок проспекта с обеих сторон ровно 10 м — PASS.',
        'Все промышленные здания и дворы севернее ЖД; полоса южнее ≤20 м; пляж/море вне зданий и районов, исключение дороги — BEACH_ACCESS — PASS.',
        'Авто/пеший граф достигает пляжа только через элитку; удаление входа или элитного соединителя разрывает доступ — PASS.',
        'Схема v10 сохранена; добавлены beaches и boundary.coast_segments_m. SHA-256 предыдущих файлов совпали; Git и WORK_SYNC.md не затрагивались.',
        'Сборка: Python -B map_plan_v11.py; SVG разобран, PNG 2400 × 2400 просмотрен. Время расчётное; ограды, канал и возврат из моря требуют Unity-плейтеста.']
    assert len(lines) <= 50, len(lines)
    return '\n'.join(lines) + '\n'


def main():
    before = hashes()
    d = seed()
    d['points'].append(dict(id='BEACH_ENTRY', canonical_id='BEACH_ENTRY', name_ru='Пляж / разворот',
        position_m=[890, 458], district_id='beach', category='poi', label_offset_px=[-80, 24]))
    scope = analysis_scope()
    scope['analyse'](d)
    svg, png = ROOT / (STEM + '.svg'), ROOT / (STEM + '.png')
    svg.write_text(scope['render'](d), encoding='utf-8')
    ET.parse(svg)
    env = os.environ.copy()
    env['MAGICK_TEMPORARY_PATH'] = str(ROOT)
    subprocess.run([str(m.MAGICK), '-background', '#f6f3e9', str(svg), '-strip', str(png)],
                   check=True, cwd=ROOT, env=env, capture_output=True)
    h = png.read_bytes()[:24]
    assert h[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', h[16:24]) == (2400, 2400)
    (ROOT / (STEM + '.json')).write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (ROOT / (STEM + '_REPORT.md')).write_text(report(d), encoding='utf-8')
    assert hashes() == before, 'Older files changed'
    print(f'OK: {len(d["validation"]["checks"])} checks; extent {d["metrics"]["extent_m"]}; 88 buildings; PNG2400x2400')
    for r in d['metrics']['routes']:
        print(r['from_id'], '->', r['to_id'], r['length_m'], 'm')


if __name__ == '__main__':
    main()
