"""Хутор: раскладка v06 (TASK-000851, Вадим 20.10.2026: «поля ровнее, аккуратнее, чуть поменьше… дома: рядом с лесом
парочку и около горы пару домов, чтобы основное скопление было по центру, а снизу и сверху чуть домов; подсоедини их
нормально»). Из HAMLET_LAYOUT_v05.json:
- поля меньше и ровнее: поле 1 — 32 × 26 м, поле 2 — 40 × 26 м, стороны вдоль улиц; рулоны сена — по их краям;
- +3 дома у леса (юг, у дороги в лес) и +2 у горы (запад, за прудом), у каждого участок и подъезд 3,6 м к улице;
- деревья, кусты и мелочи, налезающие на новое, убраны.
Пишет HAMLET_LAYOUT_v06.json (v05 не трогает)."""
import json
import math
from pathlib import Path

REV = Path(r'C:\Users\chern_0eqkb03\Desktop\GAME\Working\Reviews\Hamlet_2026-10-14')
SRC, OUT = REV / 'HAMLET_LAYOUT_v05.json', REV / 'HAMLET_LAYOUT_v06.json'
if OUT.exists():
    raise SystemExit('exists')
L = json.load(open(SRC, encoding='utf-8'))


def R(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def bb(o):
    xs = [p[0] for p in o['polygon_m']]; ys = [p[1] for p in o['polygon_m']]
    return min(xs), min(ys), max(xs), max(ys)


objs = [o for o in L['objects'] if o['kind'] != 'round_hay_bale' or o['id'].startswith('02-BALE-0') and False]
objs = [o for o in L['objects'] if o['kind'] != 'round_hay_bale']
FIELDS = {'02-A-FIELD1': (333, 556, 365, 582, 'stubble'), '02-A-FIELD2': (152, 395, 192, 421, 'plowed')}
for o in objs:
    if o['id'] in FIELDS:
        x0, y0, x1, y1, kind = FIELDS[o['id']]
        o['polygon_m'] = R(x0, y0, x1, y1); o['centre_m'] = [(x0 + x1) / 2, (y0 + y1) / 2]; o['size_m'] = [x1 - x0, y1 - y0]
        o['field_type'] = kind; o['furrow_step_m'] = 2.5; o['notes'] = 'v06: smaller and straight, sides along the streets'
new = []
HOUSES = [('02-H20', (226, 391), 'у леса, у дороги в лес'), ('02-H21', (252, 392), 'у леса'), ('02-H22', (268, 387), 'у леса'),
          ('02-H23', (144, 481), 'у горы, за прудом'), ('02-H24', (163, 457), 'у горы, за прудом')]
for hid, (cx, cy), note in HOUSES:
    w, l = 8.0, 7.0
    new.append({'id': hid, 'kind': 'house', 'centre_m': [cx, cy], 'size_m': [w, l], 'rotation_deg': 0, 'polygon_m': R(cx - w / 2, cy - l / 2, cx + w / 2, cy + l / 2),
                'material': 'timber_log', 'notes': 'v06: ' + note, 'source': 'v06 added'})
    new.append({'id': hid + '-YARD', 'kind': 'yard', 'polygon_m': R(cx - 9, cy - 8, cx + 9, cy + 8), 'centre_m': [cx, cy], 'source': 'v06 added'})
    new.append({'id': hid + '-S1', 'kind': 'shed', 'centre_m': [cx + 6.5, cy + 4.5], 'size_m': [3.2, 2.8], 'rotation_deg': 0,
                'polygon_m': R(cx + 4.9, cy + 3.1, cx + 8.1, cy + 5.9), 'source': 'v06 added'})
    new.append({'id': hid + '-G1', 'kind': 'vegetable_garden', 'polygon_m': R(cx - 8, cy - 7.5, cx - 2, cy - 4.5), 'centre_m': [cx - 5, cy - 6], 'source': 'v06 added'})
SPURS = [{'id': '02-R-forest_homes', 'width_m': 3.6, 'polyline_m': [[238.5, 400.0], [226, 396.5], [226, 394.5]]},
         {'id': '02-R-forest_homes_e', 'width_m': 3.6, 'polyline_m': [[239.0, 397.0], [252, 396.5], [268, 391.5], [268, 390.5]]},
         {'id': '02-R-mountain_homes', 'width_m': 3.6, 'polyline_m': [[194.0, 507.0], [172, 500], [156, 492], [152, 476], [154, 457], [159, 457]]},
         {'id': '02-R-mountain_h23', 'width_m': 3.6, 'polyline_m': [[152.5, 481.0], [148, 481]]}]
for sp in SPURS:
    sp.update({'kind': 'street', 'road_class': 'dirt_track', 'source': 'v06 added'})


def seg_d(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / ((dx * dx + dy * dy) or 1)))
    return math.hypot(a[0] + t * dx - p[0], a[1] + t * dy - p[1])


hard = [o for o in new if o['kind'] in ('house', 'shed')] + [o for o in objs if o['id'] in FIELDS]
drop = []
keep = []
for o in objs:
    if o['kind'] in ('tree', 'soft_shrub_cluster', 'reed_clump', 'woodpile', 'water_barrel', 'wooden_crate', 'stump', 'rounded_rock', 'flower_strip',
                     'mud_patch', 'dung_patch', 'chicken_coop', 'shed', 'outdoor_table', 'compost_heap', 'wheelbarrow', 'clothesline') and o['id'] not in FIELDS:
        c = o.get('centre_m') or [sum(p[0] for p in o['polygon_m']) / len(o['polygon_m']), sum(p[1] for p in o['polygon_m']) / len(o['polygon_m'])]
        r = 1.0 if o['kind'] == 'tree' else 1.5
        hit = any(bb(h)[0] - r <= c[0] <= bb(h)[2] + r and bb(h)[1] - r <= c[1] <= bb(h)[3] + r for h in hard)
        hit = hit or any(seg_d(c, a, b) < sp['width_m'] / 2 + r for sp in SPURS for a, b in zip(sp['polyline_m'][:-1], sp['polyline_m'][1:]))
        if hit:
            drop.append(o['id']); continue
    keep.append(o)
# рулоны сена: у навеса как было, у полей — вдоль края внутри
BALES = [((300.5, 552.0), 0.0, 4), ((300.5, 559.5), 0.0, 3), ((336.0, 558.5), 0.0, 6), ((362.5, 562.0), 90.0, 4),
         ((156.0, 418.5), 0.0, 5), ((154.5, 398.0), 90.0, 3)]
n = 0
for (x, y), rot, cnt in BALES:
    for k in range(cnt):
        a = math.radians(rot)
        c = [round(x + k * 2.1 * math.cos(a), 2), round(y + k * 2.1 * math.sin(a), 2)]
        n += 1
        keep.append({'id': '02-BALE-%02d' % n, 'kind': 'round_hay_bale', 'centre_m': c, 'size_m': [1.7, 1.7], 'polygon_m': R(c[0] - .85, c[1] - .85, c[0] + .85, c[1] + .85)})
L['objects'] = keep + new
L['streets'] = L['streets'] + SPURS
L['schema'] = 'volunteers_only.hamlet_layout.v06'
L['date'] = '2026-10-20'
L['status'] = 'v06: поля меньше и ровнее, +3 дома у леса, +2 у горы с подъездами (TASK-000851); основа v05'
L['dropped_v06'] = drop
json.dump(L, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('houses', sum(1 for o in L['objects'] if o['kind'] == 'house'), 'dropped', len(drop))
