"""Хутор layout v04 (TASK-000550): Vadim's edits on top of GPT's HAMLET_LAYOUT_v03.json.
Removed: the kolkhoz barn (former cowshed) with its pad and spur, the village shop with its notice board and spur,
the obelisk, the transformer box (and their wires). Added: a small village square where NPCs gather
(packed earth, a long table under a big shade tree, benches, a lamp on the existing pole). Never overwrites.

  python hamlet_layout_v04_edit.py   -> Working/Reviews/Hamlet_2026-10-14/HAMLET_LAYOUT_v04.json
"""
import copy, json, math
from pathlib import Path

DIR = Path(r'C:\Users\chern_0eqkb03\Desktop\GAME\Working\Reviews\Hamlet_2026-10-14')
SRC, DST = DIR / 'HAMLET_LAYOUT_v03.json', DIR / 'HAMLET_LAYOUT_v04.json'
if DST.exists():
    raise SystemExit(f'{DST.name} exists')
L = json.load(open(SRC, encoding='utf-8'))

DROP = {'02-A-BARN', '02-A-BARN-PAD', '02-A-SHOP', '02-A-SIGN', '02-A-OBELISK', '02-U-TRANSFORMER',
        '02-A-SQUARE', '02-A-BENCH1', '02-A-BENCH2'}
DROP_STREETS = {'02-R-barn', '02-R-shop'}

# the new square: a rounded box north of the main road at the junction with the south road
SQ_C, SQ_W, SQ_L = (259.0, 505.5), 22.0, 12.0


def rect(c, w, l, rot=0.0):
    a = math.radians(rot)
    out = []
    for dx, dy in ((-w / 2, -l / 2), (w / 2, -l / 2), (w / 2, l / 2), (-w / 2, l / 2)):
        out.append([round(c[0] + dx * math.cos(a) - dy * math.sin(a), 2), round(c[1] + dx * math.sin(a) + dy * math.cos(a), 2)])
    return out


def rounded(c, w, l, r=3.0, n=5):
    pts = []
    for cx, cy, a0 in ((c[0] + w / 2 - r, c[1] - l / 2 + r, -90), (c[0] + w / 2 - r, c[1] + l / 2 - r, 0),
                       (c[0] - w / 2 + r, c[1] + l / 2 - r, 90), (c[0] - w / 2 + r, c[1] - l / 2 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append([round(cx + r * math.cos(a), 2), round(cy + r * math.sin(a), 2)])
    return pts


def inside_sq(p, pad=0.0):
    return abs(p[0] - SQ_C[0]) <= SQ_W / 2 + pad and abs(p[1] - SQ_C[1]) <= SQ_L / 2 + pad


objs = [o for o in L['objects'] if o['id'] not in DROP]
# loose dressing that falls on the new square goes
small = {'bucket', 'feed_sack', 'wooden_crate', 'watering_can', 'chair', 'tyre', 'stump', 'wheelbarrow', 'mud_patch', 'wheel_rut'}
gone = [o['id'] for o in objs if o['kind'] in small and o.get('centre_m') and inside_sq(o['centre_m'], 1.0)]
objs = [o for o in objs if o['id'] not in gone]
clash = [o['id'] + ' ' + o['kind'] for o in objs if o.get('centre_m') and inside_sq(o['centre_m'])
         and o['kind'] not in ('wooden_utility_pole', 'pole_lamp')]


def obj(i, kind, c, w, l, rot=0.0, notes='', **extra):
    o = {'id': i, 'kind': kind, 'centre_m': [round(c[0], 2), round(c[1], 2)], 'size_m': [w, l], 'rotation_deg': rot,
         'polygon_m': rect(c, w, l, rot), 'notes': notes}
    o.update(extra)
    return o


sx, sy = SQ_C
new = [
    {'id': '02-SQ', 'kind': 'village_square', 'centre_m': [sx, sy], 'size_m': [SQ_W, SQ_L], 'rotation_deg': 0,
     'polygon_m': rounded(SQ_C, SQ_W, SQ_L),
     'notes': 'Small village square where NPCs gather: packed earth with worn grass edges, open to the main road on the south; '
              'no monument, no shop, no playground. Van can drive across it.'},
    obj('02-SQ-TREE', 'tree', (sx - 6.0, sy + 2.0), 0.6, 0.6, notes='One big old shade tree over the table.',
        tree_type='shade', crown_diameter_m=9.0, planting_group='square'),
    obj('02-SQ-TABLE', 'gathering_table', (sx - 5.0, sy - 0.5), 4.0, 1.0, notes='Long plank table: dominoes, cards, sunflower seeds.'),
    obj('02-SQ-TB1', 'bench', (sx - 5.0, sy + 0.5), 4.0, 0.4, notes='Plank bench of the table.'),
    obj('02-SQ-TB2', 'bench', (sx - 5.0, sy - 1.5), 4.0, 0.4, notes='Plank bench of the table.'),
    obj('02-SQ-B1', 'bench', (sx + 4.0, sy + 5.1), 2.0, 0.5, notes='Bench along the north edge, facing the square.'),
    obj('02-SQ-B2', 'bench', (sx + 8.5, sy + 5.1), 2.0, 0.5, notes='Second bench, gossip spot.'),
    obj('02-SQ-B3', 'bench', (sx + 10.4, sy - 0.5), 2.0, 0.5, rot=90, notes='Bench on the east edge.'),
]
pole = next((o for o in objs if o['id'] == '02-P-15'), None)
if pole:
    new.append(obj('02-L-6', 'pole_lamp', pole['centre_m'], 0.2, 0.2, notes='Lamp on the existing pole 02-P-15 lights the square at night.'))
for k, c in enumerate([(sx - 7.5, sy - 0.5), (sx - 2.5, sy - 0.5), (sx + 4.0, sy + 3.6), (sx + 8.5, sy + 3.6),
                       (sx + 9.4, sy - 0.5), (sx + 1.0, sy - 2.5), (sx - 1.0, sy + 3.0)]):
    new.append(obj(f'02-SQ-NPC-{k}', 'npc_gathering_marker', c, 0.6, 0.6,
                   notes='NPC idle spot: sitting at the table or on a bench, standing in a talking group.'))
objs += new
L['objects'] = objs
L['streets'] = [s for s in L['streets'] if s['id'] not in DROP_STREETS]
ids = {o['id'] for o in objs}
L['utility_links'] = [u for u in L['utility_links'] if u['from_id'] in ids and u['to_id'] in ids]
L['status'] = 'v04: Vadim edits of the agreed GPT v03 (TASK-000550)'
L['date'] = '2026-10-14'
L['v04_changes'] = {
    'removed': ['kolkhoz barn (former cowshed) 02-A-BARN with pad and spur', 'village shop 02-A-SHOP with notice board and spur',
                'obelisk 02-A-OBELISK and the old forecourt 02-A-SQUARE', 'transformer box 02-U-TRANSFORMER'] + [f'dressing {i}' for i in gone],
    'added': ['village square 02-SQ (22 x 12 m) with a long table under a big shade tree, 3 benches, lamp 02-L-6, 7 NPC idle markers'],
    'still_not_built': ['playground', 'monument', 'shop', 'cowshed or barn', 'transformer box'],
    'notes': 'The pig pen 02-A-PEN stays where it was; the former barn spot is open grass.'}
json.dump(L, open(DST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('ok', len(L['objects']), 'objects; removed dressing', gone, '; still on the square:', clash)
