"""Хутор: раскладка v05 (TASK-000840/841, Вадим 20.10.2026: «на карте Феди планировка домов логичнее, чем у меня…
не надо брать 1 в 1, надо сделать чуть лучше»).

Берёт из последнего плана Феди MAP_PLAN_R01_v19.json сетку улиц Хутора (02_h_*), 20 домов на участках, огороды,
сараи у домов, пруд, водонапорную башню, рулоны сена в поле. Из нашей утверждённой раскладки HAMLET_LAYOUT_v04.json —
церковь, хижину деда с площадкой бусика, площадь со столом под большим деревом, кладбище, сад, свинарник, навес сена,
трактора, остановку, рыбацкое место, заброшенный двор, деревья и мелочи по дворам (мелочи двора переезжают вместе с
ближайшим домом). Не берёт (решения Вадима): магазин, колхозный сарай, дачи, колодцы у каждого дома, заборы между
домами. Улучшения против v19: подъезды к домам не уже 3,6 м (бусик), всё, что налезает на дома, улицы и сараи,
убирается, деревья не стоят на дорогах. Пишет HAMLET_LAYOUT_v05.json (новая версия, v04 не трогает).
"""
import json, math
from pathlib import Path
from PIL import Image, ImageDraw

GAME = Path(r'C:\Users\chern_0eqkb03\Desktop\GAME')
V19 = GAME / r'ArtSource\References\Map\MAP_PLAN_R01_v19.json'
V04 = GAME / r'Working\Reviews\Hamlet_2026-10-14\HAMLET_LAYOUT_v04.json'
OUT = GAME / r'Working\Reviews\Hamlet_2026-10-14\HAMLET_LAYOUT_v05.json'
if OUT.exists():
    raise SystemExit(f'{OUT.name} exists')
F = json.load(open(V19, encoding='utf-8'))
L = json.load(open(V04, encoding='utf-8'))


def rect(c, w, l, rot=0.0):
    a = math.radians(rot); ca, sa = math.cos(a), math.sin(a)
    return [[round(c[0] + x * ca - y * sa, 3), round(c[1] + x * sa + y * ca, 3)]
            for x, y in ((-w / 2, -l / 2), (w / 2, -l / 2), (w / 2, l / 2), (-w / 2, l / 2))]


def centre(poly):
    return [sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly)]


# --- улицы Феди (подъезды не уже 3,6 м)
WID = {'02_h_main': 5.4, '02_h_north': 5.4, '02_h_south': 5.4, '02_h_base': 4.2, '02_h_loop': 4.2}
streets = []
for r in F['roads']:
    if not r['id'].startswith('02_h_'):
        continue
    w = WID.get(r['id'], 3.6)
    streets.append({'id': '02-R-' + r['id'][5:], 'kind': 'street', 'road_class': 'dirt_main' if w >= 5 else 'dirt_track',
                    'width_m': w, 'polyline_m': r['polyline_m'], 'source': 'Fedya v19 ' + r['id']})

objs = []
# --- дома Феди
def inside(c):                                                        # фермы Феди CL_v18_farm_* стоят за пределами Хутора
    return 125 <= c[0] <= 400 and 370 <= c[1] <= 612


fhouses = [b for b in F['functional_buildings'] if b.get('district_id') == 'village' and b['kind'] == 'village_house' and inside(b['center_m'])]
v04h = [o for o in L['objects'] if o['kind'] == 'house']
# каждому дому v04 (материал, занятие жильцов, мелочи двора) — ближайший дом Феди
pairs, free = {}, set(range(len(fhouses)))
for dd, hid, j in sorted((math.dist(h['centre_m'], b['center_m']), h['id'], k) for h in v04h for k, b in enumerate(fhouses)):
    if j in free and hid not in pairs:                                # ближайшие пары первыми
        free.discard(j); pairs[hid] = j
spare = [h for h in v04h if h['id'] not in pairs]                     # дома v04 без пары остаются на своём месте
inv = {j: hid for hid, j in pairs.items()}
for j, b in enumerate(fhouses):
    hid = inv.get(j)
    src = next((h for h in v04h if h['id'] == hid), None)
    o = dict(src) if src else {'kind': 'house', 'material': 'timber_log', 'notes': 'Extra household from Fedya v19.'}
    o['id'] = hid or f'02-H{20 + len([1 for k in range(j) if k not in inv]):02d}'
    o['centre_m'] = [round(v, 3) for v in b['center_m']]
    o['size_m'] = [round(b['width_m'], 2), round(b['depth_m'], 2)]
    o['rotation_deg'] = b.get('orientation_deg') or 0
    o['polygon_m'] = b['footprint_m']
    o['source'] = 'Fedya v19 ' + b['id']
    objs.append(o)
for h in spare:
    o = dict(h); o['source'] = 'v04 position (no Fedya house nearby)'; objs.append(o)
delta = {hid: (fhouses[j]['center_m'][0] - next(h for h in v04h if h['id'] == hid)['centre_m'][0],
               fhouses[j]['center_m'][1] - next(h for h in v04h if h['id'] == hid)['centre_m'][1]) for hid, j in pairs.items()}

# --- сараи у домов, участки, огороды, луговины Феди
for b in F['functional_buildings']:
    if b.get('district_id') == 'village' and b['kind'] == 'shed' and inside(b['center_m']):
        objs.append({'id': '02-S-' + b['id'][3:], 'kind': 'shed', 'centre_m': b['center_m'], 'size_m': [b['width_m'], b['depth_m']],
                     'rotation_deg': b.get('orientation_deg') or 0, 'polygon_m': b['footprint_m'], 'source': 'Fedya v19 ' + b['id']})
KIND = {'plot_or_garden': 'yard', 'vegetable_beds': 'vegetable_garden', 'meadow_with_grass_tufts': 'open_working_grass'}
for s in F['functional_sites']:
    if s.get('district_id') == 'village' and s['kind'] in KIND and inside(centre(s['polygon_m'])):
        objs.append({'id': '02-G-' + s['id'][3:], 'kind': KIND[s['kind']], 'polygon_m': s['polygon_m'], 'centre_m': centre(s['polygon_m']),
                     'source': 'Fedya v19 ' + s['id']})
for w in F['water']:
    if w['id'] == '02_pond_1':
        objs.append({'id': '02-A-POND', 'kind': 'pond', 'polygon_m': w['polygon_m'], 'centre_m': centre(w['polygon_m']), 'source': 'Fedya v19 02_pond_1'})
# рулоны сена группами (Вадим: «круглые рулоны, группами у навеса и краёв полей»), вместо 83 одиночных стогов v19
BALES = [((300.5, 552.0), 0.0, 4), ((300.5, 559.5), 0.0, 3),             # у навеса сена
         ((333.0, 552.5), 0.0, 6), ((364.0, 588.0), 90.0, 4),             # поле 1: южный и восточный край
         ((196.0, 424.0), 0.0, 5), ((150.0, 395.0), 90.0, 3)]             # поле 2: северный и западный край
n = 0
for (x, y), rot, cnt in BALES:
    for k in range(cnt):
        a = math.radians(rot)
        c = [round(x + k * 2.1 * math.cos(a), 2), round(y + k * 2.1 * math.sin(a), 2)]
        n += 1
        objs.append({'id': f'02-BALE-{n:02d}', 'kind': 'round_hay_bale', 'centre_m': c, 'size_m': [1.7, 1.7], 'polygon_m': rect(c, 1.7, 1.7)})
# --- наше из v04
KEEP = {'church', 'grandfather_base', 'van_loading_pad', 'manoeuvring_apron', 'village_square', 'gathering_table', 'bench',
        'npc_gathering_marker', 'pole_lamp', 'cemetery', 'grave', 'orchard', 'small_pig_pen', 'pig_shelter', 'pig_spawn_marker',
        'feed_trough', 'hay_shelter', 'parked_tractor', 'farm_trailer', 'bus_stop', 'fishing_platform', 'upturned_boat',
        'fishing_nets', 'net_drying_rack', 'fishing_bucket', 'rusted_car', 'broken_timber', 'overgrown_beds', 'cultivated_field',
        'old_well', 'water_tower', 'tree', 'soft_shrub_cluster', 'reed_clump', 'chicken_coop', 'chicken_spawn_marker',
        'chicken_feeder', 'egg_basket', 'woodpile', 'water_barrel', 'clothesline', 'compost_heap', 'wheelbarrow', 'outdoor_table',
        'chair', 'flower_strip', 'flower_pot', 'watering_can', 'bucket', 'feed_sack', 'wooden_crate', 'wash_basin', 'wooden_pallet',
        'stump', 'rounded_rock', 'standpipe', 'shared_bin', 'tyre', 'rusted_wheel', 'handcart', 'feed_bin', 'mud_patch', 'dung_patch',
        'pedestrian_path'}
SKIP_V04 = {'round_hay_bale'}
YARD_OF = {}
for o in L['objects']:
    if o['kind'] not in KEEP or o['kind'] in SKIP_V04:
        continue
    o = json.loads(json.dumps(o))
    parts = o['id'].split('-')
    hid = '-'.join(parts[:2]) if len(parts) >= 3 and parts[1].startswith('H') else None
    if hid in delta and o['kind'] not in ('tree',):                     # мелочь двора переезжает вместе с домом
        dx, dy = delta[hid]
        for key in ('centre_m',):
            if o.get(key):
                o[key] = [o[key][0] + dx, o[key][1] + dy]
        if o.get('polygon_m'):
            o['polygon_m'] = [[p[0] + dx, p[1] + dy] for p in o['polygon_m']]
        o['moved_with'] = hid
    objs.append(o)

# --- отбор по пересечениям (растр 0,5 м)
X0, X1, Y0, Y1, R = 118.0, 442.0, 355.0, 618.0, 2.0


def mask(polys=(), lines=()):
    m = Image.new('1', (int((X1 - X0) * R), int((Y1 - Y0) * R)), 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon([((x - X0) * R, (Y1 - y) * R) for x, y in p], fill=1)
    for pts, w in lines:
        d.line([((x - X0) * R, (Y1 - y) * R) for x, y in pts], fill=1, width=max(1, int(w * R)), joint='curve')
    return m


def hits(m, poly):
    t = mask([poly])
    return Image.composite(m, Image.new('1', m.size, 0), t).getbbox() is not None


HARD = {'house', 'church', 'grandfather_base', 'shed', 'water_tower', 'hay_shelter', 'chicken_coop', 'pig_shelter', 'bus_stop'}
road_m = mask(lines=[(s['polyline_m'], s['width_m'] + 0.6) for s in streets])
hard_polys = [o['polygon_m'] for o in objs if o['kind'] in HARD and o.get('polygon_m')]
dropped = []
keep = []
bld_m = mask(hard_polys)
for o in objs:
    if o['kind'] in ('house', 'church', 'grandfather_base'):
        keep.append(o); continue
    poly = o.get('polygon_m') or (rect(o['centre_m'], *(o.get('size_m') or [1, 1])) if o.get('centre_m') else None)
    if poly is None:
        keep.append(o); continue
    if o['kind'] == 'tree':                                            # ствол не на дороге и не в доме; крона может нависать
        c = o['centre_m']; poly = rect(c, 1.2, 1.2)
    small = o['kind'] not in ('yard', 'vegetable_garden', 'open_working_grass', 'cultivated_field', 'orchard', 'pond', 'cemetery',
                              'village_square', 'manoeuvring_apron', 'van_loading_pad', 'small_pig_pen', 'mud_patch', 'dung_patch',
                              'overgrown_beds', 'pedestrian_path')
    on_road = hits(road_m, poly)
    if o['kind'] in HARD:
        others = mask([p for p in hard_polys if p is not o['polygon_m']])
        in_bld = hits(others, poly)
    else:
        in_bld = hits(bld_m, poly) if small or o['kind'] in ('vegetable_garden',) else False
    if o['kind'] in ('npc_gathering_marker', 'pig_spawn_marker', 'chicken_spawn_marker'):
        keep.append(o); continue
    if (small and (on_road or in_bld)) or (o['kind'] in ('vegetable_garden', 'cultivated_field', 'orchard') and on_road and o['kind'] != 'cultivated_field'):
        dropped.append((o['id'], o['kind'], 'road' if on_road else 'building')); continue
    keep.append(o)

# дома против дорог и друг друга — только отчёт (чинить руками)
road_core = mask(lines=[(s['polyline_m'], s['width_m'] + 1.0) for s in streets])
for o in keep:                                                         # дом на дороге — сдвинуть на ближайшее свободное место
    if o['kind'] != 'house' or not hits(road_core, o['polygon_m']):
        continue
    others = mask([q['polygon_m'] for q in keep if q is not o and q['kind'] in HARD and q.get('polygon_m')])
    for r_ in range(1, 9):
        ok = None
        for a in range(0, 360, 45):
            dx, dy = r_ * math.cos(math.radians(a)), r_ * math.sin(math.radians(a))
            poly = [[x + dx, y + dy] for x, y in o['polygon_m']]
            if not hits(road_core, poly) and not hits(others, poly):
                ok = (dx, dy, poly); break
        if ok:
            o['polygon_m'] = ok[2]; o['centre_m'] = [o['centre_m'][0] + ok[0], o['centre_m'][1] + ok[1]]
            o['note_v05'] = f'сдвинут с дороги на {r_} м'
            break
report = []
for o in keep:
    if o['kind'] in ('house', 'church', 'grandfather_base') and hits(mask(lines=[(s['polyline_m'], s['width_m']) for s in streets]), o['polygon_m']):
        report.append(f"{o['id']} {o['kind']} на дороге")
res = {'schema': 'volunteers_only.hamlet_layout.v05', 'date': '2026-10-20', 'units': 'metres',
       'coordinate_system': L['coordinate_system'], 'source_map': L['source_map'],
       'status': 'v05: улицы и дома с участками — по плану Феди v19, наши объекты v04 (TASK-000840/841)',
       'confirmed_decisions': L['confirmed_decisions'] + ['20.10.2026 Вадим: планировка домов как у Феди v19, но лучше, не 1:1'],
       'streets': streets, 'objects': keep, 'npc_population': L['npc_population'],
       'dropped_on_overlap': [{'id': a, 'kind': b, 'reason': c} for a, b, c in dropped], 'house_overlap_report': report}
json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
from collections import Counter
print('streets', len(streets), 'objects', len(keep), Counter(o['kind'] for o in keep).most_common(12))
print('dropped', len(dropped), Counter(k for _, k, _ in dropped))
print('report', report)
