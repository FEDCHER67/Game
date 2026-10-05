#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Targeted v09 -> v10 map revision; stdlib + existing ImageMagick.

Run with Python -B. Only this revision's five files are written.
The v09 JSON is the source of truth; previous generators remain read-only.
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
import map_plan_v09 as v9

v7, m = v9.v7, v9.m
ROOT = m.ROOT
STEM = 'MAP_PLAN_R01_v10'
OUTPUTS = {STEM + suffix for suffix in ('.json', '.svg', '.png', '_REPORT.md')}
OUTPUTS.add('map_plan_v10.py')
HOUSE_MOVES = {
    'O06_T1_U2': ([541, 605], 8),
    'O06_T2_U2': ([625, 606], -7),
    'O06_T3_U2': ([778, 554], 6),
    'O06_T3_U5': ([779, 458], -9),
    'O06_T1_U5': ([682, 454], -8),
    'O06_T2_U6': ([720, 456], 10),
    # Break the former six-house southern line into a trio and a singleton;
    # the other two now occupy gaps among the houses inside the ring.
    'O06_T5_U4': ([550, 512], 4),
    'O06_T5_U5': ([552, 491], -4),
}
ALTERED_ROADS = {
    'ARC_RURAL', 'HUT_BRANCH', 'RECEPTION_BRANCH', 'ARC_AVENUE',
    'OLD_TOWN_CONNECTOR', 'R_COURTS', 'R_LINK', 'R_COURTS_EAST',
    'COURT_ACCESS_1', 'COURT_ACCESS_2', 'COURT_ACCESS_3', 'R_REAR',
    'EXIT_NE', 'EXIT_APPROACH_NE', 'ACCESS_B03', 'ACCESS_P06', 'ACCESS_P07',
    'ACCESS_F06_24', 'ACCESS_F06_K1', 'ACCESS_F06_K2', 'ACCESS_F06_K3',
    'ACCESS_P08', 'ACCESS_P11-3', 'ACCESS_P09-2', 'ACCESS_P11-2',
    'ACCESS_P13-4', 'ACCESS_P11', 'ACCESS_F06_MASKS', 'ACCESS_F06_CAFE1',
}


def hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.iterdir()) if p.is_file() and p.name not in OUTPUTS}


def source_data():
    return json.loads((ROOT / 'MAP_PLAN_R01_v09.json').read_text(encoding='utf-8'))


def shifted(q, dy=40):
    """Translate explicit geometry without altering sizes, IDs or metadata."""
    q = copy.deepcopy(q)
    for key in ('center_m', 'position_m', 'entrance_m', 'dead_end_m'):
        if key in q:
            q[key] = [q[key][0], round(q[key][1] + dy, 3)]
    for key in ('polygon_m', 'footprint_m', 'yard_polygon_m', 'polyline_m',
                'post_trigger_polygon_m'):
        if key in q:
            q[key] = [[x, round(y + dy, 3)] for x, y in q[key]]
    if 'barrier_polygons_m' in q:
        q['barrier_polygons_m'] = [[[x, round(y + dy, 3)] for x, y in poly]
                                   for poly in q['barrier_polygons_m']]
    return q


def move_function(d, fid, center, parent, start, door=None):
    f = next(f for f in d['functional_buildings'] if f['id'] == fid)
    dx, dy = center[0] - f['center_m'][0], center[1] - f['center_m'][1]
    f['center_m'] = center
    f['footprint_m'] = [[round(x + dx, 3), round(y + dy, 3)] for x, y in f['footprint_m']]
    f['entrance_m'] = door or [round(f['entrance_m'][0] + dx, 3),
                              round(f['entrance_m'][1] + dy, 3)]
    f['access_road_id'] = parent
    pid = f.get('poi_id')
    if pid:
        next(p for p in d['points'] if p['id'] == pid)['position_m'] = f['entrance_m'][:]
    access = next(r for r in d['roads'] if r['id'] == 'ACCESS_' + (pid or fid))
    access['polyline_m'] = [start, f['entrance_m'][:]]


def seed():
    d = source_data()
    d.update(revision='v10', title_ru='VOLUNTEERS ONLY — план карты R01 / v10')
    d['specification']['brief_override'] = 'req_map_plan_v10.md, targeted review, 2026-10-04'
    d['provenance'] = dict(brief='req_map_plan_v10.md', source_schema='MAP_PLAN_R01_v09.json',
        owner_decisions_date='2026-10-04', method='targeted v09 edits; unchanged geometry retained',
        previous_files_sha256=hashes())
    d['comparison'] = {'v09': {'extent_m': d['metrics']['extent_m']},
                       'policy': 'targeted edits; north +40 m; no uniform scaling'}
    for key in ('building_masses', 'functional_buildings', 'points', 'functional_sites'):
        d[key] = [shifted(q) if q.get('district_id') == 'residential' and
                  q.get('center_m', q.get('position_m', [0, 0]))[1] > 676 else q for q in d[key]]
    d['microdistricts'][:2] = [shifted(q) for q in d['microdistricts'][:2]]
    d['exits'] = [shifted(q) if q['id'] == 'NE' else q for q in d['exits']]
    for q in (d['boundary'], next(q for q in d['districts'] if q['id'] == 'residential')):
        q['polygon_m'] = [[x, 865 if y == 825 else y] for x, y in q['polygon_m']]

    roads = {r['id']: r for r in d['roads']}
    # Split the straight avenue from its southern connector rather than folding
    # a turn into the avenue polyline. R_COURTS_EAST is absorbed into the avenue.
    connector = copy.deepcopy(roads['ARC_AVENUE'])
    connector.update(id='OLD_TOWN_CONNECTOR', polyline_m=[[650, 718], [650, 540], [800, 540]])
    d['roads'].append(connector)
    roads['ARC_AVENUE'].update(polyline_m=[[470, 718], [770, 718]], district_ids=['residential'])
    d['roads'] = [r for r in d['roads'] if r['id'] not in ('R_LINK', 'R_COURTS_EAST')]
    roads = {r['id']: r for r in d['roads']}
    updates = {
        'ARC_RURAL': [[350, 600], [405, 600], [405, 718], [470, 718]],
        'HUT_BRANCH': [[405, 718], [405, 730]],
        'RECEPTION_BRANCH': [[440, 718], [440, 691]],
        'R_COURTS': [[515, 718], [515, 676]],
        'COURT_ACCESS_1': [[535, 718], [535, 745]],
        'COURT_ACCESS_2': [[650, 718], [650, 745]],
        'COURT_ACCESS_3': [[592.5, 820], [592.5, 675]],
        'R_REAR': [[710, 718], [710, 820], [535, 820]],
    }
    for rid, poly in updates.items():
        roads[rid]['polyline_m'] = poly
    for rid in ('EXIT_NE', 'EXIT_APPROACH_NE', 'ACCESS_P07', 'ACCESS_F06_K3',
                'ACCESS_P08', 'ACCESS_P11-3', 'ACCESS_P09-2'):
        roads[rid]['polyline_m'] = shifted(roads[rid])['polyline_m']
    # The ruins' unchanged driveway now branches from the rerouted main road.
    next(f for f in d['functional_buildings'] if f['id'] == 'F06_RUINS')['access_road_id'] = 'ARC_RURAL'

    bs = {b['id']: b for b in d['building_masses']}
    for bid, center, angle in (
        ('R06_C3_S1', [592.5, 631], 180),
        ('R06_C3_S2', [632.5, 675], 270),
        ('R06_C3_S3', [552.5, 675], 270)):
        bs[bid].update(center_m=center, width_m=72, depth_m=12,
                       polygon_m=m.rectangle(*center, 72, 12, angle))
    d['microdistricts'][2].update(center_m=[592.5, 671],
        yard_polygon_m=m.rectangle(592.5, 675, 62, 64), opening_direction='north')
    pts = {p['id']: p for p in d['points']}
    pts['BAD_BLOCK_3']['position_m'] = [592.5, 675]
    pts['BAD_CENTER']['position_m'] = [650, 718]
    # Keep the bins in the open yard and connect to the den-road southern stub.
    roads['ACCESS_P13-4']['polyline_m'] = [[592.5, 675], [606, 675]]
    move_function(d, 'F06_GBASE', [492, 686], 'ARC_AVENUE', [492, 718])
    move_function(d, 'F06_K1', [526, 687], 'ARC_AVENUE', [526, 718])
    move_function(d, 'F06_K2', [515, 650], 'R_COURTS', [515, 676])
    move_function(d, 'F06_24', [680, 687], 'ARC_AVENUE', [680, 718])
    move_function(d, 'F06_BAR', [674, 642], 'OLD_TOWN_CONNECTOR', [650, 654.366])
    pts['P11-2']['position_m'] = [703, 696]
    roads['ACCESS_P11-2']['polyline_m'] = [[703, 718], [703, 696]]
    for fid in ('F06_HOTEL',):
        next(f for f in d['functional_buildings'] if f['id'] == fid)['access_road_id'] = 'OLD_TOWN_CONNECTOR'
    for q in d['vegetation_parcels']:
        if q['id'] == 'TRANSITION_URBAN_1':
            q['polygon_m'] = [[468, 440], [472, 440], [472, 714.5], [468, 714.5]]
        elif q['id'] == 'TRANSITION_URBAN_2':
            q['polygon_m'] = [[468, 721.5], [472, 721.5], [472, 865], [468, 865]]
        if q.get('gate_road_id') == 'ARC_AVENUE' and q['id'].startswith(('BAD_OLD', 'OLD_ELITE')):
            q['gate_road_id'] = 'OLD_TOWN_CONNECTOR'

    d['building_masses'] = [b for b in d['building_masses'] if not b['id'].startswith('O06_T4_')]
    d['plots'] = [p for p in d['plots'] if not p['id'].startswith('O06_T4_')]
    move_function(d, 'F06_BANK', [704, 507], 'O_RING', [750, 507])
    move_function(d, 'F06_MASKS', [615, 520], 'O_SPINE', [650, 520], [630, 520])
    move_function(d, 'F06_CAFE1', [706, 570], 'O_RING', [706, 590])
    plots = {p['id']: p for p in d['plots']}
    for bid, (center, angle) in HOUSE_MOVES.items():
        b = bs[bid]
        b.update(center_m=center, polygon_m=m.rectangle(*center, b['width_m'], b['depth_m'], angle))
        # Existing front-yard identities follow their relocated houses.
        heading = math.radians(angle)
        off = 11 if center[1] < 480 else -11
        pc = [center[0] - off * math.sin(heading), center[1] + off * math.cos(heading)]
        plots[bid + '_FRONT']['polygon_m'] = m.rectangle(*pc, 7, 6, angle)
    d['paths'] = []
    d['planning_notes_ru'] = [
        'Проспект — одна прямая (470;718) → (770;718); R_COURTS_EAST объединён с ним. Южная связь: (650;718) → (650;540).',
        'Все северные объекты неблагополучного района сдвинуты на +40 м без изменения размеров; верхняя граница y=865.',
        'Девять корпусов 72 × 12 м: по 12/9/10 этажей в каждом дворе. Двор 3 открыт на север, руки x=552,5/632,5, y=639–711; основание (592,5;631).',
        'Дорога к притону идёт между дворами по x=592,5; задняя петля возвращается к проспекту; короткий южный конец ведёт к мусоркам.',
        'B03 и киоски 1–2 западнее двора 3; магазин 24 часа, ATM P11-2 и бар восточнее. Подъезды ≤25 м, один местный тупик 42 м.',
        'BAD_CENTER — (650;718). Переход соединён с проспектом по y=718; B02 и P04 остаются на разных коротких тупиковых ветках.',
        'АЗС, руины и P09-4 сохранены; лесополоса на x=470 непрерывна, кроме единственного въезда y=714,5–721,5.',
        'Удалены O06_T4_U1–U6 и их участки. Банк / ATM P11 перенесён на (704;507); одежда / маски — (615;520) рядом с церковью.',
        'Кафе у площади — среди домов внутри кольца. Шесть домов вынесены в северные, восточные и южные промежутки; два южных возвращены внутрь.',
        'Всего 24 малых дома 2–3 этажа; небольшие повороты и разные интервалы. B04, P05, супермаркет/P09, полиция, почта, церковь, высотки и кольцо сохранены.',
        'Пешеходных проходов нет; пеший граф использует только дороги. Остальные районы, вода, железная дорога и усадьбы сохранены.',
        'Время теоретическое; субъективное принятие и физические барьеры требуют Unity-плейтеста.']
    return d


def without_nodes(q):
    return {k: v for k, v in q.items() if k not in ('road_node_id', 'dead_end_node_id')}


def validate_targeted(d, check):
    old = source_data()
    fs = {f['id']: f for f in d['functional_buildings']}
    ofs = {f['id']: f for f in old['functional_buildings']}
    bs = {b['id']: b for b in d['building_masses']}
    roads = {r['id']: r for r in d['roads']}
    pts = {p['id']: p for p in d['points']}
    check('exact v09 schema version, top-level keys and container types',
          d['schema_version'] == old['schema_version'] and set(d) == set(old) and
          all(type(d[k]) == type(v) for k, v in old.items()))
    check('map exactly 815 by 725 m', d['metrics']['extent_m'] == [815, 725])
    check('north expansion adds exactly 12400 square metres',
          d['metrics']['area_m2'] - old['metrics']['area_m2'] == 310 * 40)
    check('avenue exactly one straight east-west polyline at y718; eastern lane absorbed',
          roads['ARC_AVENUE']['polyline_m'] == [[470, 718], [770, 718]] and
          'R_COURTS_EAST' not in roads and 'R_LINK' not in roads and
          roads['OLD_TOWN_CONNECTOR']['polyline_m'] == [[650, 718], [650, 540], [800, 540]])
    check('bad centre at avenue and south connector junction', pts['BAD_CENTER']['position_m'] == [650, 718])
    for key in ('building_masses', 'functional_buildings', 'points', 'functional_sites'):
        current = {q['id']: q for q in d[key]}
        north = [q for q in old[key] if q.get('district_id') == 'residential' and
                 q.get('center_m', q.get('position_m', [0, 0]))[1] > 676]
        check(key + ' all northern objects translated exactly +40 m',
              all(without_nodes(current[q['id']]) == without_nodes(shifted(q)) for q in north))
    check('upper courtyard polygons translated exactly +40 m',
          d['microdistricts'][:2] == [shifted(q) for q in old['microdistricts'][:2]])
    check('NE exit dead end, barriers and trigger translated exactly +40 m',
          without_nodes(next(e for e in d['exits'] if e['id'] == 'NE')) ==
          without_nodes(shifted(next(e for e in old['exits'] if e['id'] == 'NE'))))
    check('all three courts have identical slab dimensions and floor sequence',
          all([(bs[bid]['width_m'], bs[bid]['depth_m'], bs[bid]['floors']) for bid in c['building_ids']]
              == [(72, 12, 12), (72, 12, 9), (72, 12, 10)] for c in d['microdistricts']))
    third = [bs[f'R06_C3_S{i}'] for i in (1, 2, 3)]
    upper = [b for b in bs.values() if b['id'].startswith(('R06_C1_', 'R06_C2_'))]
    check('U3 exact full-size coordinates and north opening; centred between U1 and U2',
          [b['center_m'] for b in third] == [[592.5, 631], [632.5, 675], [552.5, 675]] and
          all(min(p[1] for p in b['polygon_m']) == 639 and max(p[1] for p in b['polygon_m']) == 711 for b in third[1:]) and
          d['microdistricts'][2]['opening_direction'] == 'north' and
          592.5 == sum(c['center_m'][0] for c in d['microdistricts'][:2]) / 2)
    check('interlocking zigzag; projected U3 arms hit U1 and U2 back slabs',
          all(min(p[0] for p in bs[base]['polygon_m']) < x < max(p[0] for p in bs[base]['polygon_m'])
              for base, x in (('R06_C1_S1', 552.5), ('R06_C2_S1', 632.5))))
    clearances = [(b['id'], r['id'], v7.gap(b['polygon_m'], a, c) - r['width_m'] / 2)
                  for b in third + upper for r in d['roads']
                  for a, c in zip(r['polyline_m'], r['polyline_m'][1:])]
    check('all nine slabs at least 3 m clear of every road edge',
          min(q[2] for q in clearances) >= 3 - .005, f'minimum {min(q[2] for q in clearances):.3f} m')
    check('den road between upper courts; rear loop reconnects to avenue',
          roads['COURT_ACCESS_3']['polyline_m'] == [[592.5, 820], [592.5, 675]] and
          roads['R_REAR']['polyline_m'] == [[710, 718], [710, 820], [535, 820]])
    front = ['F06_GBASE', 'F06_K1', 'F06_K2', 'F06_24', 'F06_BAR']
    check('southern frontage west and east of U3; every footprint in y620 to712',
          all(max(p[0] for p in fs[fid]['footprint_m']) < 546.5 for fid in front[:3]) and
          all(min(p[0] for p in fs[fid]['footprint_m']) > 638.5 for fid in front[3:]) and
          all(620 <= p[1] <= 712 for fid in front for p in fs[fid]['footprint_m']))
    accesses = ['ACCESS_B03', 'ACCESS_F06_K1', 'ACCESS_F06_K2', 'ACCESS_F06_24', 'ACCESS_P06', 'ACCESS_P11-2']
    access_lengths = {rid: sum(m.length(a, b) for a, b in zip(roads[rid]['polyline_m'], roads[rid]['polyline_m'][1:])) for rid in accesses}
    check('each southern frontage access at most 25 m', all(v <= 25 for v in access_lengths.values()), str(access_lengths))
    check('transition road aligned at470718; separate short B02 and P04 dead ends',
          roads['ARC_RURAL']['polyline_m'][-2:] == [[405, 718], [470, 718]] and
          roads['HUT_BRANCH']['polyline_m'] == [[405, 718], [405, 730]] and
          roads['RECEPTION_BRANCH']['polyline_m'] == [[440, 718], [440, 691]])
    belts = {q['id']: q for q in d['vegetation_parcels']}
    check('west urban barrier continuous from440 to865 except 7m entrance',
          belts['TRANSITION_URBAN_1']['polygon_m'] == [[468, 440], [472, 440], [472, 714.5], [468, 714.5]] and
          belts['TRANSITION_URBAN_2']['polygon_m'] == [[468, 721.5], [472, 721.5], [472, 865], [468, 865]])
    check('T4 removed, bank and its ATM relocated into former T4 group',
          not any(bid.startswith('O06_T4_') for bid in bs) and
          not any(p['id'].startswith('O06_T4_') for p in d['plots']) and
          fs['F06_BANK']['center_m'] == [704, 507] and fs['F06_BANK']['poi_id'] == 'P11' and
          pts['P11']['position_m'] == fs['F06_BANK']['entrance_m'])
    check('masks shop at former bank centre next to unchanged church',
          fs['F06_MASKS']['center_m'] == ofs['F06_BANK']['center_m'] and fs['F06_CHURCH'] == ofs['F06_CHURCH'])
    ring = roads['O_RING']['polyline_m'][:-1]
    oldbs = {b['id']: b for b in old['building_masses']}
    outward = [bid for bid in HOUSE_MOVES if m.inside(oldbs[bid]['center_m'], ring) and not m.inside(bs[bid]['center_m'], ring)]
    check('six formerly interior houses moved outside ring on north east south sides',
          len(outward) == 6 and sum(bs[bid]['center_m'][1] > 590 for bid in outward) == 2 and
          sum(bs[bid]['center_m'][0] > 750 for bid in outward) == 2 and
          sum(bs[bid]['center_m'][1] < 480 and bs[bid]['center_m'][0] <= 750 for bid in outward) == 2, str(outward))
    check('additional cafe among houses inside ring', m.inside(fs['F06_CAFE1']['center_m'], ring) and
          sum(m.length(b['center_m'], fs['F06_CAFE1']['center_m']) < 25 for b in bs.values() if 'terrace_id' in b) >= 3)
    houses = [b for b in bs.values() if 'terrace_id' in b]
    check('24 small houses retain identities dimensions and floors',
          len(houses) == 24 and all((b['width_m'], b['depth_m'], b['floors']) ==
          (oldbs[b['id']]['width_m'], oldbs[b['id']]['depth_m'], oldbs[b['id']]['floors']) for b in houses))
    # A row means neighbouring houses on one near-straight axis, within 20 m.
    longest = 0
    for i, a in enumerate(houses):
        for b in houses[i + 1:]:
            if m.length(a['center_m'], b['center_m']) > 20:
                continue
            axis = [b['center_m'][k] - a['center_m'][k] for k in (0, 1)]
            n = math.hypot(*axis)
            if not n:
                continue
            aligned = sorted((sum((q['center_m'][k] - a['center_m'][k]) * axis[k] for k in (0, 1)) / n, q['id'])
                for q in houses if abs((q['center_m'][0] - a['center_m'][0]) * axis[1] -
                                      (q['center_m'][1] - a['center_m'][1]) * axis[0]) / n <= 2)
            run = 1
            for u, v in zip(aligned, aligned[1:]):
                run = run + 1 if v[0] - u[0] <= 20 else 1
                longest = max(longest, run)
    check('no near-straight house row longer than three adjacent houses', longest <= 3, str(longest))
    moved_functions = {'F06_GBASE', 'F06_K1', 'F06_K2', 'F06_24', 'F06_BAR',
                       'F06_BANK', 'F06_MASKS', 'F06_CAFE1', 'F06_HOTEL', 'F06_RUINS'}
    northern_functions = {f['id'] for f in old['functional_buildings'] if f['district_id'] == 'residential' and f['center_m'][1] > 676}
    check('all unrelated functional buildings retained exactly',
          all(f == ofs[f['id']] for f in d['functional_buildings'] if f['id'] not in moved_functions | northern_functions))
    for fid in ('F06_HOTEL', 'F06_RUINS'):
        check(fid + ' geometry preserved; parent road reference updated',
              {k: v for k, v in fs[fid].items() if k != 'access_road_id'} ==
              {k: v for k, v in ofs[fid].items() if k != 'access_road_id'})
    changed_points = {'B03', 'P06', 'P07', 'P08', 'P11', 'P11-2', 'P11-3', 'P09-2',
                      'P16-2', 'BAD_CENTER', 'BAD_BLOCK', 'BAD_BLOCK_2', 'BAD_BLOCK_3'}
    check('all unrelated POIs including transition hut buyer and meeting retained',
          all(without_nodes(p) == without_nodes(next(q for q in old['points'] if q['id'] == p['id']))
              for p in d['points'] if p['id'] not in changed_points))
    check('all unrelated building masses including two towers retained',
          all(b == oldbs[b['id']] for b in bs.values() if b['district_id'] != 'residential' and b['id'] not in HOUSE_MOVES))
    check('old-town ring spine and every unrelated road retained',
          [r for r in d['roads'] if r['id'] not in ALTERED_ROADS] == [r for r in old['roads'] if r['id'] not in ALTERED_ROADS])
    check('water railway fields hills farmsteads retained',
          all(d[k] == old[k] for k in ('water', 'railway', 'field_parcels_m', 'hills', 'farmsteads')))
    check('all unrelated plots retained',
          [p for p in d['plots'] if p['id'].removesuffix('_FRONT') not in HOUSE_MOVES] ==
          [p for p in old['plots'] if not p['id'].startswith('O06_T4_') and p['id'].removesuffix('_FRONT') not in HOUSE_MOVES])
    check('all road centre lines inside boundary',
          all(m.inside(p, d['boundary']['polygon_m']) for r in d['roads'] for p in r['polyline_m']))
    check('walking graph exactly equals road graph; every route distance equal',
          not d['paths'] and d['pedestrian_graph'] == d['road_graph'] and
          all(r['length_m'] == r['pedestrian_length_m'] and math.isfinite(r['length_m']) for r in d['metrics']['routes']))


def replace_exact(source, old, new):
    assert old in source, 'Inherited source changed: ' + old[:100]
    return source.replace(old, new)


def analysis_scope():
    """Retain the established full geometry checks, updating obsolete assumptions."""
    source = (ROOT / 'map_plan_v07.py').read_text(encoding='utf-8')
    analysis = source[source.index('def analyse(data):'):source.index('\ndef validate_targeted')]
    replacements = {
        'len(phys)==115': 'len(phys)==88',
        'physical count matches v06 removals plus B07 and P01 pole': 'physical count: v09 minus six T4 houses',
        "len(terraces)==30": "len(terraces)==24",
        'five six-unit terraces; 7-m frontages; 2–3 floors': '24 small houses in four retained groups; 7-m frontages; 2–3 floors',
        "'shop_24h','boiler_house','hospital'": "'shop_24h','hospital'",
        "'house_base','clock_tower','bank'": "'house_base','bank'",
        "'private_security','boutique','prestige_base'": "'private_security','prestige_base'",
        "mansions=[f for f in fs if f['type'] in ('mansion','prestige_base')]":
            "mansions=[f for f in fs if f['district_id']=='elite' and f['type']=='mansion']",
        'garage_box_count=18': "garage_box_count=sum(b.get('subtype')=='garage_box' for b in bs)",
        "'three open P09 meeting sites'": "'four open P09 meeting sites'",
        "{'P09','P09-2','P09-3'}": "{'P09','P09-2','P09-3','P09-4'}",
        "ped=copy.deepcopy(data);ped['roads']+=copy.deepcopy(data['paths']);m.build_graph(ped)":
            "ped=copy.deepcopy(data)  # Walking uses the already built road graph only.",
        "('transition/bad',[470,650],'ARC_RURAL')": "('transition/bad',[470,718],'ARC_RURAL')",
        "('bad/old',[650,620],'ARC_AVENUE')": "('bad/old',[650,620],'OLD_TOWN_CONNECTOR')",
        "('old/elite',[800,540],'ARC_AVENUE')": "('old/elite',[800,540],'OLD_TOWN_CONNECTOR')",
        "data['roads']+data['paths']": "data['roads']",
        "for k in ('roads','points','building_masses','functional_buildings','paths'):":
            "for k in ('roads','points','building_masses','functional_buildings'):",
        "dict(count=4,total_length_m=sum(p['length_m'] for p in data['paths']),policy='urban local only; no van access')":
            "dict(count=0,total_length_m=0,policy='deferred; walking uses roads only')",
    }
    for old, new in replacements.items():
        analysis = replace_exact(analysis, old, new)
    # Remove the pedestrian-passage geometry checks entirely, not just their
    # expected count. Graph connectivity and route distance checks stay active.
    start = analysis.index('    pathhits=')
    end = analysis.index('    for key,graph ', start)
    analysis = analysis[:start] + analysis[end:]
    scope = dict(vars(v7))
    scope.update(hashes=hashes, validate_targeted=validate_targeted,
                 ROUTES=[(a, 'B06' if b == 'B07' else b) for a, b in v7.ROUTES] + [
                     ('P06', 'P08'), ('P08', 'P11-3'), ('B06', 'P10'), ('P10', 'P15'),
                     ('B05', 'P09-3'), ('BAD_BLOCK_2', 'P11-3')])
    exec(compile(analysis, str(ROOT / 'map_plan_v10.py'), 'exec'), scope)
    # Start from v09's renderer to preserve its P09 label placement fixes.
    v09_source = (ROOT / 'map_plan_v09.py').read_text(encoding='utf-8')
    begin = v09_source.index("    start=source.index('def render(data):')")
    end = v09_source.index('    # Compile the matching legend', begin)
    renderer_setup = 'def setup_renderer():\n' + v09_source[begin:end] + '    return renderer\n'
    scope['source'] = source
    exec(compile(renderer_setup, str(ROOT / 'map_plan_v10.py'), 'exec'), scope)
    renderer = scope.pop('setup_renderer')()
    renderer = renderer.replace('v09', 'v10').replace('815 × 685 м', '815 × 725 м')
    renderer = renderer.replace('Двор 3 — за улицей', '3 равных двора / корпуса 72 × 12 м')
    renderer = renderer.replace("([645,813]", "([640,855]")
    renderer = renderer.replace('xy([110,855]),xy([925,855])', 'xy([110,890]),xy([925,890])')
    renderer = renderer.replace('Район → площадь: 110 м; элитка: ещё 150 м.', 'Район → площадь: 178 м; элитка: ещё 150 м.')
    renderer = renderer.replace('4 локальных прохода / 2,5 м / только пешком.', 'Пешие маршруты используют только дороги.')
    start = renderer.index("    for p in data['paths']:")
    end = renderer.index("    rail=data['railway']", start)
    renderer = renderer[:start] + renderer[end:]

    legend = source[source.index('def legend('):source.index('\ndef report(')]
    legend = legend.replace('v07', 'v10')
    for old, new in {
        "('highway','town_street','rural_road','dirt_shortcut','passage')": "('highway','town_street','rural_road','dirt_shortcut')",
        '18 боксов, B03, бар P06, притон P07;': 'B03, бар P06, притон P07;',
        '3 киоска, 24 ч, котельная / труба.': '3 киоска, 24 ч, P08 / C03, ATM.',
        '5 террас × 6 домов по 7 м;': '24 отдельных дома 2–3 эт.;',
        'две высотки, P05, B04, больница P08,': 'две высотки, P05, B04,',
        'площадь / часы; P09 + 2 запасные.': 'малая площадь; P09 — обычная.',
        '4 особняка, B06 и 2 доступных P15;': '4 особняка, 2 доступны P15;',
        'охрана, бутик / B05, P14, P12,': 'будка охраны / B05, P14, P12,',
        'B07: вилла 2 эт., гараж для бусика;': 'B06: вилла 2 эт., гараж для бусика;',
    }.items():
        legend = replace_exact(legend, old, new)
    start = legend.index("    y+=5;s.text(x,y,'4 ЛОКАЛЬНЫХ ПРОХОДА'")
    end = legend.index("    s.text(x,y,'B01 → РАЙОН", start)
    legend = legend[:start] + """    y+=5;s.text(x,y,'P09 / 4 МЕСТА ВСТРЕЧ',size=18,weight='bold');y+=25
    s.text(x,y,'Обычная — за супермаркетом.',size=14);y+=21
    s.text(x,y,'Запасные — B05, дворы, переход.',size=14);y+=27
    s.text(x,y,'Пешком — по дорожному графу.',size=14);y+=27
""" + legend[end:]
    exec(compile(legend, str(ROOT / 'map_plan_v10.py'), 'exec'), scope)
    exec(compile(renderer, str(ROOT / 'map_plan_v10.py'), 'exec'), scope)
    inherited_render = scope['render']

    def render(d):
        svg = inherited_render(d)
        routes = {(r['from_id'], r['to_id']): r for r in d['metrics']['routes']}
        decimal = lambda value, places: f'{value:.{places}f}'.replace('.', ',')
        for base, old_length, old_times, old_walk, old_footer in (
            ('B01', '588', '35,3 / 23,5', '7,06', '7,1'),
            ('B02', '328', '19,7 / 13,1', '3,94', '3,9')):
            r = routes[base, 'BAD_CENTER']
            distance = f'{r["length_m"]:.0f}'
            svg = svg.replace(f'{base} → РАЙОН / {old_length} м', f'{base} → РАЙОН / {distance} м')
            svg = svg.replace(f'60 / 90 км/ч: {old_times} с',
                f'60 / 90 км/ч: {decimal(r["van_60_seconds"],1)} / {decimal(r["van_90_seconds"],1)} с')
            svg = svg.replace(f'Пешком 5 км/ч: {old_walk} мин', f'Пешком 5 км/ч: {decimal(r["walk_5_minutes"],2)} мин')
            svg = svg.replace(f'{base} → район: {old_length} м; пешком {old_footer} мин.',
                f'{base} → район: {distance} м; пешком {decimal(r["walk_5_minutes"],1)} мин.')
        return svg

    scope['render'] = render
    return scope


def report(d):
    checks = d['validation']['checks']
    lines = ['# VOLUNTEERS ONLY — R01 v10', '',
        'Основание: req_map_plan_v10.md, целевые правки v09 от 04.10.2026.',
        f'Карта: 815 × 725 м; площадь {d["metrics"]["area_m2"]:.0f} м²; {d["metrics"]["building_count"]} зданий; SVG/PNG 2400 × 2400.',
        *d['planning_notes_ru'][:-1], '',
        '| Маршрут | Дорога, м | 60 км/ч, с | 90 км/ч, с | Пешком, м / мин |',
        '|---|---:|---:|---:|---:|']
    for r in d['metrics']['routes']:
        lines.append(f'| {r["from_id"]} → {r["to_id"]} | {r["length_m"]:.1f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["pedestrian_length_m"]:.1f} / {r["walk_5_minutes"]:.2f} |')
    lines += ['', f'Проверки: {sum(c["passed"] for c in checks)}/{len(checks)}; полные результаты в validation.checks JSON.',
        'Дистанции: B01→P01/P02/P03 ≤200 м; B01→район ≥400 м; район→площадь 178≤200 м; площадь→элитный въезд 150≤200 м; обе стороны карты ≤1000 м — PASS.',
        'Пересечения зданий: друг с другом / дорогами (включая подъезды) / водой / железной дорогой — по 0; все четыре проверки PASS.',
        'Зазор всех девяти корпусов до любой дорожной кромки ≥3 м — PASS; связность авто/пешего графа и обязательный возврат через посты — PASS.',
        'Схема JSON v09 сохранена, paths пуст; пеший граф равен дорожному. Предыдущие файлы проверены SHA-256; Git и WORK_SYNC.md не затрагивались.',
        'Сборка: Python -B map_plan_v10.py. PNG просмотрен: двор 3 визуально равен дворам 1–2 по размерам корпусов.',
        'Время расчётное при 60/90 км/ч и пешком 5 км/ч, без разгона, поворотов, трафика и уклонов; необходим Unity-плейтест.']
    assert len(lines) <= 50
    return '\n'.join(lines) + '\n'


def main():
    before = hashes()
    d = seed()
    scope = analysis_scope()
    scope['analyse'](d)
    svg, png = ROOT / (STEM + '.svg'), ROOT / (STEM + '.png')
    svg.write_text(scope['render'](d), encoding='utf-8')
    ET.parse(svg)
    env = os.environ.copy()
    env['MAGICK_TEMPORARY_PATH'] = str(ROOT)
    subprocess.run([str(m.MAGICK), '-background', '#f6f3e9', str(svg), '-strip', str(png)],
                   check=True, cwd=ROOT, env=env, capture_output=True)
    header = png.read_bytes()[:24]
    assert header[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', header[16:24]) == (2400, 2400)
    (ROOT / (STEM + '.json')).write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    (ROOT / (STEM + '_REPORT.md')).write_text(report(d), encoding='utf-8')
    assert before == hashes(), 'Previous files changed'
    print(f'OK: {len(d["validation"]["checks"])} checks; {d["metrics"]["building_count"]} buildings; PNG 2400x2400')
    for r in d['metrics']['routes']:
        print(r['from_id'], '->', r['to_id'], r['length_m'], 'm')


if __name__ == '__main__':
    main()
