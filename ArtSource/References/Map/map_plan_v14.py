#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R01 v14: Fedya's illustrated map REF_FEDYA_v14_map_v23.png (alignment table) and his voice edits of 2026-10-06.
Valley without the night club and the bowling; elite marina with yachts and motor boats; a small bay opposite the
beach car park; the old town rebuilt around twin towers and a big square with a fountain and a monument
(REF_FEDYA_v14_old_town_square.png), mid-rise around the square, the low houses further out.
Standing rule (Fedya 2026-10-06): change only the named pieces. Everything outside the declared change regions stays
byte-identical to v13; the region guard check enforces it. Reads final v13; writes only the v14 deliverables in this
folder. Run with Python -B.
"""
import copy
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
sys.dont_write_bytecode = True
import map_plan_v13 as v13
m, v7, v11, v12 = v13.m, v13.v7, v13.v11, v13.v12
ROOT = m.ROOT
STEM = 'MAP_PLAN_R01_v14'
CROPS = {
    'old_town': ('Старый город: две башни, площадь с фонтаном, высоты домов', [470, 425, 830, 640]),
    'valley_beach': ('Малая долина без клуба и боулинга · бухта у пляжной парковки', [330, 226, 760, 468]),
    'elite_marina': ('Элитный холм и пристань с яхтами', [800, 404, 1180, 716]),
}
OUTPUTS = ({STEM+s for s in ('.json', '.svg', '.png', '_REPORT.md')} |
           {f'{STEM}_crop_{k}.png' for k in CROPS} | {'map_plan_v14.py'})
PREVIOUS = re.compile(r'^(build_map_plan\.py|map_plan_v(0[2-9]|1[0-3])\.py|map_dressing_v12\.py|'
                      r'MAP_(PLAN|DRESSING)_R01_v(0[2-9]|1[0-3])(\.json|\.svg|\.png|_REPORT\.md|_crop_[a-z_]+\.png)|'
                      r'REF_FEDYA_v14_[a-z0-9_]+\.png)$')
curve, rounded, oval, offset, nearest = v13.curve, v13.rounded, v13.oval, v13.offset, v13.nearest
contained, strict_overlap, simple, turn_max = v13.contained, v13.strict_overlap, v13.simple, v13.turn_max
circle, centroid, plen, local, poly_gap = v13.circle, v13.centroid, v13.plen, v13.local, v13.poly_gap
WIDTHS = v13.WIDTHS

# ------------------------------------------------------------------ change regions (Fedya 2026-10-06)
# The only places where v14 may differ from v13. bbox = [x0, y0, x1, y1] in metres; 'district' = that v13 polygon.
REGIONS = [
    ('valley_club', 'Малая долина: место ночного клуба и его подъезд', 'bbox', [356, 360, 404, 396]),
    ('valley_bowling', 'Малая долина: место боулинга, подъезд и хвост дороги к нему', 'bbox', [450, 330, 497, 392]),
    ('elite_marina', 'Пристань у элитного холма: разворот на пляже и море перед ним', 'bbox', [1018, 462, 1146, 566]),
    ('parking_bay', 'Бухта напротив пляжной парковки: берег, песок, тропинки на песок', 'bbox', [566, 234, 746, 302]),
    ('old_town', 'Старый город — весь район (контур района не менялся)', 'district', 'old_town'),
]
REGION_TOL = 1.0
LOG_KEYS = {'revision', 'title_ru', 'specification', 'provenance', 'comparison', 'planning_notes_ru', 'moves',
            'land_transfers', 'removed_buildings', 'removed_barriers', 'distribution_targets', 'validation', 'metrics',
            'road_graph', 'pedestrian_graph', 'water_crossings', 'render_statistics', 'residential_statistics',
            'hamlet_statistics', 'alley_statistics', 'passage_statistics', 'functional_statistics',
            'start_cluster_home_routes_m', 'replaced_generic_building_ids', 'geometry_repairs', 'v23_alignment',
            'change_regions', 'old_town_statistics', 'superseded_v13_checks'}
DERIVED = {'road_node_id', 'dead_end_node_id', 'area_m2', 'building_count', 'share_percent', 'length_m'}
GEO_SKIP = {'size_m', 'radii_m', 'width_m', 'extent_m', 'bounds_m', 'diameter_m', 'nave_size_m', 'tower_size_m'}
# Metadata edits allowed on records whose geometry lies outside every region (they only describe region changes).
META_ALLOWED = {('districts', 'fields'): {'notes_ru'}, ('beaches', 'BEACH'): {'bay_id'}}

# ------------------------------------------------------------------ 1. valley: night club and bowling removed
VALLEY_REMOVED = {'F12_NIGHTCLUB': 'ACCESS_F12_NIGHTCLUB', 'F12_BOWLING': 'ACCESS_F12_BOWLING'}
VALLEY_BRANCH_END = [460, 386]          # last kept vertex: inside the casino lot; the tail ran on to the bowling

# ------------------------------------------------------------------ 2. elite marina (pier frame: u seaward, v north)
MARINA_PROBE = [1050, 517]              # the pier root is the waterline point nearest to this, east of the turnaround
QUAY = (-9, 0, -7, 7)                   # u0, u1, v0, v1: paved apron on the sand at the pier root
QUAY_ROAD_U = -6                        # the quay road ends 6 m before the waterline
PIER = (-1.5, 62, -2, 2)
T_HEAD = (62, 66, -16, 16)
FINGERS = [18, 31, 44]                  # u of the finger pontoons on the north side, 2 x 12 m each
FINGER_V = (2, 14)
BREAKWATER = [[-4, 30], [24, 35.5], [52, 35], [78, 31], [94, 14], [99, -6]]
BREAKWATER_W = 6.0
# berth id: (kind, centre u, centre v, length, beam, heading: 'v' = bow along +v, 'u' = bow along +u), boat or None
BERTHS = {
    'B_F1_W': ('motorboat', 18-3.4, 8.5, 8, 2.8, 'v', 'BOAT_M1'), 'B_F1_E': ('motorboat', 18+3.4, 8.5, 8, 2.8, 'v', None),
    'B_F2_W': ('motorboat', 31-3.4, 8.5, 8, 2.8, 'v', 'BOAT_M2'), 'B_F2_E': ('motorboat', 31+3.4, 8.5, 8, 2.8, 'v', 'BOAT_M3'),
    'B_F3_W': ('motorboat', 44-3.4, 8.5, 8, 2.8, 'v', None), 'B_F3_E': ('motorboat', 44+3.4, 8.5, 8, 2.8, 'v', 'BOAT_M4'),
    'B_T_N': ('yacht', 69.4, 8.4, 15, 5.0, 'v', 'YACHT_2'), 'B_T_S': ('yacht', 69.4, -8.9, 16, 5.0, 'v', 'YACHT_3'),
    'B_P_S': ('yacht', 33, -5.5, 20, 5.6, 'u', 'YACHT_1'), 'B_P_S2': ('motorboat', 12, -4.2, 8, 3.0, 'u', None),
}
BOAT_NAMES = {'YACHT_1': 'Яхта 20 м', 'YACHT_2': 'Яхта 15 м', 'YACHT_3': 'Яхта 16 м', 'BOAT_M1': 'Катер', 'BOAT_M2': 'Катер',
              'BOAT_M3': 'Катер', 'BOAT_M4': 'Катер'}

# ------------------------------------------------------------------ 3. bay opposite the beach car park
BAY_KEEP = (25, 37)                     # beach sea-edge vertices kept on both sides of the bay (v13 indices)
BAY_SEA = [[589, 255.4], [600, 257.6], [609, 263.8], [618.5, 271.6], [629.5, 278.0], [641.5, 281.9], [653.5, 283.2],
           [666, 281.7], [678, 277.8], [688.5, 271.6], [697.5, 263.9], [705.5, 255.9], [713.5, 249.4]]
BAY_WALK = [[592.5, 288.2], [606, 291.4], [620, 294.2], [635, 296.1], [650, 296.8], [665, 296.0], [680, 293.6],
            [694, 290.2], [707, 285.5], [720, 280.2]]
WALK_KEEP = (569, 733)                  # WALK_BEACH vertices with x <= 569 or x >= 733 are kept
BAY_ROCKS = {'BAY14_ROCKS_W': ([590.5, 255.6], [6.5, 3.4], .4), 'BAY14_ROCKS_E': ([712.5, 249.6], [6.5, 3.4], 1.3)}
PARK_PATHS = ('PATH_BEACH_W', 'PATH_BEACH_C', 'PATH_BEACH_E')

# ------------------------------------------------------------------ 4. old town: twin towers, square, height gradient
OT_REMOVED_MASSES = {
    'O06_TOWER_1': 'Одиночная башня 14 эт. в середине: вместо неё пара башен у площади и 6-этажный дом на этом месте.',
    'O06_TOWER_2': 'Одиночная башня 16 эт. в ЮВ углу: вместо неё пара башен у площади; на месте — мастерская P05.',
    'O06_T2_U2': 'Низкий дом рядом с башнями: на его месте 7-этажный дом (ближе к башням — выше).',
    'O06_T3_U2': 'Низкий дом напротив площади: на его месте 5-этажный дом.',
}
OT_REMOVED_ROADS = ['ACCESS_O06_TOWER_1', 'ACCESS_O06_TOWER_2', 'ACCESS_O06_T2_U2', 'ACCESS_O06_T3_U2']
OT_REMOVED_PLOTS = ['O06_T2_U2_FRONT', 'O06_T3_U2_FRONT']
TOWERS = {'O14_TOWER_W': [676, 600], 'O14_TOWER_E': [706, 600]}
TOWER_SIZE, TOWER_FLOORS = 22, 20
MIDRISE = {  # id: (centre, w, d, rotation, floors, role)
    'O14_MID_NW': ([634, 602], 24, 20, -2, 7, 'у западной башни через проспект'),
    'O14_MID_W': ([612, 562], 24, 18, 4, 6, 'на месте одиночной башни, к площади через проспект'),
    'O14_MID_S': ([672.5, 516.5], 26, 20, -4, 6, 'южная сторона площади через улицу к элитке'),
    'O14_MID_E': ([777, 558], 26, 14, 3, 5, 'восточная сторона площади через улицу'),
}
SQUARE = [[663, 548], [700, 545.5], [742, 548], [746, 561], [745, 574], [738, 584.5], [700, 585.5], [664, 585],
          [661.5, 572], [661.5, 559]]
FOUNTAIN_C, FOUNTAIN_R, MONUMENT_R = [703, 566], 7.0, 1.6
LAWNS = [([680, 566], [7, 5], .3), ([726, 566], [7, 5], 1.1)]
REPAIR_C, REPAIR_DOOR_GAP = [778, 489], 3.5
CONNECTOR_TIP, CONNECTOR_JOIN = [740, 591], [651.625, 579.25]   # O_LANES vertices: cul-de-sac tip, last vertex west of OLD_TOWN_CONNECTOR
# Police v1 reads this lot from the dressing; v14 records it in the plan so the rebuild keeps it free.
POLICE_LOT = [[747.099, 607.481], [750.934, 594.298], [752.416, 593.927], [764.304, 597.385], [765.053, 598.749],
              [761.432, 611.193], [760.157, 612.426], [747.848, 608.845]]
POLICE_LOT_ACCESS = [[750.934, 594.298], [747.185, 587.963]]
TRUNK_ROADS = ('TRANSITION_DIRECT', 'OLD_TOWN_CONNECTOR', 'OLD_ELITE_CONNECTOR', 'O_SPINE', 'I_CONNECT')
GRADIENT_NEAR, GRADIENT_FAR = 100, 110

# ------------------------------------------------------------------ 5. v23 alignment (picture px -> metres by least squares)
# Anchors: objects that are the same in v13 and in the v23 picture; (px on the 1280-px picture, v13 record kind, id).
V23_ANCHORS = [
    ((131, 275), 'church', 'F06_CHURCH'), ((320, 342), 'building', 'F06_WATER'), ((392, 431), 'building', 'F06_GAS'),
    ((417, 550), 'building', 'F07_VILLA'), ((451, 484), 'water', 'LAKE'), ((282, 600), 'water', 'FOREST_LAKE'),
    ((442, 734), 'building', 'F12_CASINO'), ((675, 740), 'district', 'beach_parking'), ((896, 147), 'building', 'F06_DEPOT'),
    ((913, 231), 'building', 'F06_COMPLEX'), ((965, 201), 'building', 'F06_CHIMNEY'), ((995, 250), 'building', 'F13_TANK'),
    ((993, 178), 'building', 'F06_WARE1'), ((877, 325), 'building', 'F06_TOW'), ((1090, 576), 'point', 'BEACH_ENTRY'),
    ((506, 478), 'building', 'F06_HBASE'), ((281, 725), 'hill', 'HILL_FOREST'), ((856, 531), 'building', 'F06_GUARD'),
    ((902, 616), 'building', 'F06_MANSION_4'), ((974, 425), 'building', 'F06_MANSION_2'),
    ((895, 445), 'building', 'F08_MANSION_1'), ((999, 527), 'building', 'F06_MANSION_3')]
CLEAR_DIFF_M = 40          # about four times the median anchor residual: beyond this a place is "clearly different"
# (v23 label, px, v13 record kind/id or None, decision, note in Russian)
V23_OBJECTS = [
    ('Церковь', (131, 275), ('church', 'F06_CHURCH'), 'match', ''),
    ('B02 · Хижина деда', (153, 342), ('point', 'B02'), 'not_applied_canon',
     'По канону B02 — заброшенная хижина в переходе на своей ветке (отдельно от P04), а дом деда — P02 у края деревни, '
     'пешком от вагона (≤200 м). В v23 они слиты в «Хижину деда» у церкви — это смена канона, вопрос Феде.'),
    ('Сарай-хлев', (220, 292), ('building', 'F06_BARN'), 'not_applied_canon',
     'Это сарай двора деда (P02); переносится только вместе с решением по B02/P02.'),
    ('Старый колодец', (125, 395), None, 'new_unnamed', 'Нового объекта в v13 нет; хутор не назван — не добавляли.'),
    ('Пруд', (161, 437), None, 'new_unnamed', 'Нет в v13; на этом месте двор деда; хутор не назван — не добавляли.'),
    ('Водонапорная башня', (320, 342), ('building', 'F06_WATER'), 'match', ''),
    ('Ларёк-магазин', (340, 484), ('building', 'F06_VSHOP'), 'match', 'Это наш сельмаг.'),
    ('Одно жёлтое поле и огороды', (292, 292), ('crop', 'FIELD13_1'), 'not_applied_unnamed',
     'У нас 5 полосатых полей по прошлой картинке Феди; поля хутора не названы — не трогали.'),
    ('АЗС', (392, 431), ('building', 'F06_GAS'), 'match', ''),
    ('«Гараж» и «Дом» в переходе', (461, 271), ('point', 'P04'), 'label_only',
     'Подписи стоят на наших домах перехода (приёмка, хижина); новых объектов нет.'),
    ('B03 · База-гараж', (539, 325), ('point', 'B03'), 'same_place',
     'То же место — ЮЗ угол района у проспекта: в v23 проспект нарисован по южному краю района, поэтому сетка даёт сдвиг.'),
    ('Притон', (660, 284), ('point', 'P07'), 'not_applied_unnamed',
     'В v23 район подворотен нарисован другими кварталами (дворы-колодцы, проспект по южному краю); притон, гаражи, '
     'шаурма и мусорка там в центре. Перенос = перерисовка района, он не назван.'),
    ('Гаражи', (645, 230), ('site', 'GARAGE13'), 'not_applied_unnamed', 'См. «Притон».'),
    ('Шаурма', (690, 215), ('building', 'F13_SHAWARMA'), 'not_applied_unnamed', 'См. «Притон».'),
    ('Мусорка', (628, 252), ('point', 'P13-4'), 'not_applied_unnamed', 'См. «Притон».'),
    ('Двор-колодец, Тихий двор, Глухая подворотня, Глухой двор, Футбол за магазином', (762, 216), None, 'new_unnamed',
     'Новые названия в перерисованном районе подворотен — не добавляли.'),
    ('24 часа', (662, 370), ('building', 'F06_24'), 'match', ''),
    ('Кафе у проспекта (покупка)', (795, 392), ('building', 'F06_CAFE2'), 'same_place',
     'СВ угол старого города у главной улицы — как у нас; в v14 кафе стоит там же, у подножия башни.'),
    ('P14 · Депо', (896, 147), ('building', 'F06_DEPOT'), 'match', ''),
    ('Склад 1', (993, 178), ('building', 'F06_WARE1'), 'match', ''),
    ('Ремонтный сарай', (842, 217), ('building', 'F06_MAINT'), 'match', ''),
    ('Труба · 85 м', (965, 201), ('building', 'F06_CHIMNEY'), 'match', ''),
    ('Резервуар', (995, 250), ('building', 'F13_TANK'), 'match', ''),
    ('B05 · Промкомплекс', (913, 231), ('building', 'F06_COMPLEX'), 'match', ''),
    ('P12 · Стоянка эвакуатора', (877, 325), ('building', 'F06_TOW'), 'match', ''),
    ('Скала (островок с пирсом)', (1109, 219), ('outfall', 'OUTFALL_B05'), 'not_applied_unnamed',
     'На месте нашего слива и грязного пятна в v23 нарисован скалистый островок с мостком. Промзона не названа — оставили слив.'),
    ('Ограда промзоны по всему кругу', (870, 110), None, 'not_applied_unnamed',
     'У нас колючка только с запада и юга (набережная открыта); промзона не названа.'),
    ('B04 · Старый дом', (506, 478), ('building', 'F06_HBASE'), 'match', ''),
    ('B06 · Вилла у озера', (417, 550), ('building', 'F07_VILLA'), 'match', ''),
    ('Старый город (дома)', (640, 520), None, 'replaced', 'Заменено второй картинкой Феди (башни и площадь).'),
    ('Казино · 3 этажа', (442, 734), ('building', 'F12_CASINO'), 'match', ''),
    ('Ночной клуб', (375, 719), ('removed', 'F12_NIGHTCLUB'), 'replaced', 'Убран по правке Феди.'),
    ('Боулинг / аркада', (486, 753), ('removed', 'F12_BOWLING'), 'replaced', 'Убран по правке Феди.'),
    ('Особняк 1', (895, 445), ('building', 'F08_MANSION_1'), 'match', ''),
    ('P15 · Особняк / VIP', (974, 425), ('building', 'F06_MANSION_2'), 'match', ''),
    ('Охрана', (856, 531), ('building', 'F06_GUARD'), 'match', ''),
    ('Особняк 3', (999, 527), ('building', 'F06_MANSION_3'), 'match', ''),
    ('P15-2 · Особняк 2', (902, 616), ('building', 'F06_MANSION_4'), 'match', ''),
    ('Пляж: въезд из элитки', (1090, 576), ('point', 'BEACH_ENTRY'), 'match', ''),
    ('Болото', (100, 590), ('swamp', 'SWAMP13'), 'match', 'Нарисовано крупнее, место то же.'),
    ('Озеро', (282, 600), ('water', 'FOREST_LAKE'), 'match', ''),
    ('Холм', (281, 725), ('hill', 'HILL_FOREST'), 'match', ''),
    ('B01 · Вагон «Первая база»', (150, 687), ('point', 'B01'), 'not_applied_rule',
     'В v23 вагон ближе к берегу по тем же рельсам. Перенос ломает правило «вагон → аптека P03 ≤200 м» '
     '(сейчас 184 м), и лес не назван.'),
    ('Потухший костёр', (186, 694), ('hangout', 'HANGOUT13'), 'not_applied_rule', 'Стоит рядом с вагоном — переносится вместе с ним.'),
    ('ЖД (короткая, к ЮЗ берегу)', (70, 745), ('rail', 'RAIL_TUNNEL_W'), 'match',
     'У нас тоже короткая ветка от вагона в тоннель на западном берегу.'),
    ('Песок у леса (Лесная бухта)', (230, 800), ('beach', 'BEACH_FOREST_COVE'), 'not_applied_unnamed',
     'В v23 лес выходит прямо к воде, у нас — песчаная бухта; лес не назван.'),
    ('Пляжная парковка', (675, 740), ('district', 'beach_parking'), 'match', ''),
    ('Туалет / душевые', (700, 766), ('building', 'F13_PARK_WC'), 'match', ''),
    ('Пляж: въезд из долины', (430, 815), ('point', 'BEACH_VALLEY_ENTRY'), 'match', ''),
]
DECISIONS_RU = {'match': 'совпадает', 'same_place': 'то же место по смыслу', 'label_only': 'только подпись',
                'replaced': 'заменено правками Феди', 'not_applied_canon': 'не перенесено: канон',
                'not_applied_rule': 'не перенесено: правило маршрутов', 'not_applied_unnamed': 'не трогали: район не назван',
                'new_unnamed': 'новое, не добавляли: район не назван'}


def hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.iterdir()) if p.is_file() and PREVIOUS.match(p.name)}


def source_data():
    return json.loads((ROOT/'MAP_PLAN_R01_v13.json').read_text(encoding='utf-8'))


def r3(p):
    return [round(p[0], 3), round(p[1], 3)]


def by_id(items):
    return {q['id']: q for q in items}


def frame(root, angle):
    """Marina frame: u along the pier (seaward), v across it (north along the coast)."""
    return lambda u, v: local(root, angle, u, v)


def box(f, u0, u1, v0, v1):
    return [f(u0, v0), f(u1, v0), f(u1, v1), f(u0, v1)]


def hull(f, cu, cv, length, beam, heading, yacht):
    """Boat hull polygon: transom, pointed bow; heading 'u' or 'v' gives the bow direction in the pier frame."""
    pts = [(-length/2, -beam/2), (length/2-beam*(1.1 if yacht else .8), -beam/2), (length/2, 0),
           (length/2-beam*(1.1 if yacht else .8), beam/2), (-length/2, beam/2)]
    return [f(cu+a, cv+b) if heading == 'u' else f(cu-b, cv+a) for a, b in pts]


def seed():
    d = source_data()
    original = copy.deepcopy(d)
    d.update(revision='v14', title_ru='VOLUNTEERS ONLY — план карты R01 / v14')
    d['specification']['brief_override'] = ('Fedya 2026-10-06: v23 picture as an approximate target; no night club or bowling; '
                                            'elite marina; bay opposite the beach car park; old town with twin towers and a fountain square; '
                                            'change only the named pieces')
    d['provenance'] = dict(brief='Fedya voice edits 2026-10-06 + REF_FEDYA_v14_map_v23.png + REF_FEDYA_v14_old_town_square.png; '
                                 'lead rule: change only the named regions, the rest byte-identical to v13',
        source_schema='MAP_PLAN_R01_v13.json', owner_decisions_date='2026-10-06',
        reference_images=['REF_FEDYA_v14_map_v23.png', 'REF_FEDYA_v14_old_town_square.png'],
        method='deep copy of final v13; five local edits inside declared change regions; region guard against v13',
        previous_files_sha256=hashes(),
        pending_ru=['После «ок» Феди: map_dressing_v14 (без F12_NIGHTCLUB/F12_BOWLING и их стоянок, стоянка кафе заново, '
                    'стоянка полиции — POLICE14_LOT), look/flatten (площадь CLOCK_SQUARE теперь участок TOWER_SQUARE14), '
                    'пристань и бухта в Unity, затем полиция (police_v14).',
                    'Решения Феди по сверке с v23: B02 «Хижина деда» в хуторе; вагон ближе к берегу; район подворотен '
                    'по картинке v23; хутор с одним полем, прудом и колодцем; островок «Скала» вместо слива; лес без песка.'])
    md = original['metrics']
    d['comparison'] = dict(v13=dict(extent_m=md['extent_m'], building_count=md['building_count'], land_area_m2=md['area_m2'],
        building_counts_by_district=md['building_counts_by_district']),
        policy='v14 changes only the declared change regions; everything else is byte-identical to v13 (region guard)')
    d['change_regions'] = [dict(id=rid, label_ru=label, kind=kind,
                                bbox_m=geo if kind == 'bbox' else None, district_id=geo if kind == 'district' else None,
                                polygon_m=region_polygon((rid, label, kind, geo), original))
                           for rid, label, kind, geo in REGIONS]
    d['moves'] = []
    d['land_transfers'] = []
    trim_valley(d)
    build_marina(d)
    build_bay(d)
    rebuild_old_town(d)
    record_moves(d, original)
    d['v23_alignment'] = v23_alignment(original)
    notes(d)
    return d


def region_polygon(region, data):
    rid, label, kind, geo = region
    if kind == 'bbox':
        x0, y0, x1, y1 = geo
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    return copy.deepcopy(by_id(data['districts'])[geo]['polygon_m'])


def trim_valley(d):
    fs = by_id(d['functional_buildings'])
    for fid, rid in VALLEY_REMOVED.items():
        f = fs[fid]
        d['removed_buildings'].append(dict(id=fid, kind=f['type'], from_district='fields', access_road_id=rid, removed_in='v14',
            center_m=f['center_m'], footprint_m=f['footprint_m'],
            reason_ru='Федя 06.10: убрать ночной клуб и боулинг/аркаду из Малой долины; казино и его парковка остаются.'))
    d['functional_buildings'] = [f for f in d['functional_buildings'] if f['id'] not in VALLEY_REMOVED]
    d['roads'] = [r for r in d['roads'] if r['id'] not in VALLEY_REMOVED.values()]
    r = by_id(d['roads'])['VALLEY_BRANCH']
    i = next(i for i, p in enumerate(r['polyline_m']) if m.length(p, VALLEY_BRANCH_END) < 1e-6)
    r['polyline_m'] = r['polyline_m'][:i+1]
    r['length_m'] = plen(r['polyline_m'])
    r['trimmed_v14_ru'] = 'Хвост к боулингу убран: дорога кончается на парковке казино.'
    by_id(d['districts'])['fields']['notes_ru'] = ('Малая долина: вилла B06 у озера и казино с парковкой; ночной клуб и боулинг '
                                                  'убраны по правке Феди 06.10.')


def build_marina(d):
    """Pier with a T-head, three finger pontoons, berths with yachts and motor boats, a rubble breakwater; quay on the sand."""
    beach = d['beaches'][0]
    se = beach['sea_edge_m']
    i = min(range(len(se)-1), key=lambda k: m.projection(MARINA_PROBE, se[k], se[k+1])[0])
    a, b = se[i], se[i+1]
    root = r3(m.projection(MARINA_PROBE, a, b)[1])
    angle = round(math.degrees(math.atan2(-(b[0]-a[0]), b[1]-a[1])), 1)   # right-hand normal of the coast = seaward
    f = frame(root, angle)
    roads = by_id(d['roads'])
    start = roads['BEACH_ACCESS']['polyline_m'][-1]
    end = f(QUAY_ROAD_U, 0)
    d['roads'].append(dict(id='MARINA_QUAY', **{'class': 'rural_road'}, width_m=WIDTHS['rural_road'], district_ids=['beach'],
        polyline_m=[list(start), end], lanes=1, joins_road_ids=['BEACH_ACCESS'], length_m=round(m.length(start, end), 3),
        note_ru='Короткий проезд по песку от разворота элитки к пристани; на пляж новых въездов нет.'))
    d['points'].append(dict(id='ELITE_MARINA', canonical_id='ELITE_MARINA', name_ru='Пристань элитки', position_m=end,
                            district_id='beach', category='poi', label_offset_px=[0, 0]))
    d['functional_sites'].append(dict(id='MARINA14_QUAY', type='quay', district_id='beach', polygon_m=box(f, *QUAY),
        label_ru='Причал: площадка у пирса', point_id='ELITE_MARINA'))
    berths, boats = [], []
    for bid, (kind, cu, cv, length, beam, heading, boat) in sorted(BERTHS.items()):
        lu, lv = (length+1.2, beam+1.0) if heading == 'u' else (beam+1.0, length+1.2)
        berths.append(dict(id='MARINA14_'+bid, kind=kind, polygon_m=box(f, cu-lu/2, cu+lu/2, cv-lv/2, cv+lv/2),
                           size_m=[length+1.2, beam+1.0], occupied_by=('MARINA14_'+boat) if boat else None))
        if boat:
            boats.append(dict(id='MARINA14_'+boat, kind=kind, length_m=length, beam_m=beam, berth_id='MARINA14_'+bid,
                              heading_deg=round(angle+(0 if heading == 'u' else 90), 1), center_m=f(cu, cv),
                              polygon_m=hull(f, cu, cv, length, beam, heading, kind == 'yacht'), label_ru=BOAT_NAMES[boat]))
    axis = curve([f(u, v) for u, v in BREAKWATER], 4)
    stones = offset(axis, BREAKWATER_W/2)+list(reversed(offset(axis, -BREAKWATER_W/2)))
    d['marina'] = dict(id='MARINA14', name_ru='Пристань элитки', purpose_ru='Яхты и катера жителей элитного холма (Федя 06.10).',
        root_m=root, axis_deg=angle, quay_road_id='MARINA_QUAY', point_id='ELITE_MARINA', quay_site_id='MARINA14_QUAY',
        access_ru='Бусик: элитка → BEACH_ACCESS → разворот на пляже → MARINA_QUAY; дальше пешком по пирсу.',
        pier=dict(polygon_m=box(f, *PIER), width_m=PIER[3]-PIER[2], length_m=PIER[1]-PIER[0], material='деревянный настил на сваях'),
        t_head=dict(polygon_m=box(f, *T_HEAD), width_m=T_HEAD[1]-T_HEAD[0], length_m=T_HEAD[3]-T_HEAD[2]),
        fingers=[dict(id=f'MARINA14_FINGER_{k}', polygon_m=box(f, u-1, u+1, *FINGER_V), length_m=FINGER_V[1]-FINGER_V[0])
                 for k, u in enumerate(FINGERS, 1)],
        berths=berths, boats=boats,
        breakwater=dict(id='MARINA14_BREAKWATER', axis_m=axis, polygon_m=stones, width_m=BREAKWATER_W, material='каменный мол',
                        light_m=axis[-1], label_ru='Мол с огоньком'),
        walk_axis_m=[f(PIER[0], 0), f(T_HEAD[0]+2, 0)],
        dressing_hints_ru=['будка охраны элитки у площадки причала', 'кнехты и фонари на пирсе', 'спасательные круги',
                           'пара гидроциклов у пирса', 'вывеска «Яхт-клуб»'])


def build_bay(d):
    """A small cove of the main beach opposite the car park: the sea edge moves inland, the sand follows it."""
    beach, cove = d['beaches']
    se = beach['sea_edge_m']
    k0, k1 = BAY_KEEP
    controls = [se[k0-1], se[k0]]+BAY_SEA+[se[k1], se[k1+1]]
    pts = curve(controls, 2)
    inner = pts[2+1:2*(len(controls)-2)]
    new_se = se[:k0+1]+inner+se[k1:]
    bd = d['boundary']
    bp = bd['polygon_m']
    n_coast = len(bd['coast_segments_m'])+1
    coast = bp[:n_coast]
    i0 = len(cove['sea_edge_m'])-1
    assert coast[i0:i0+len(se)] == se
    new_coast = coast[:i0]+new_se+coast[i0+len(se):]
    bd['polygon_m'] = new_coast+bp[n_coast:]
    bd['coast_segments_m'] = [[p, q] for p, q in zip(new_coast, new_coast[1:])]
    sea = by_id(d['water'])['SEA']
    assert sea['polygon_m'][:n_coast] == coast
    sea['polygon_m'] = new_coast+sea['polygon_m'][n_coast:]
    beach['sea_edge_m'] = new_se
    beach['polygon_m'] = beach['land_edge_m']+list(reversed(new_se))
    beach['bay_id'] = 'BAY14_PARKING'
    paths = by_id(d['paths'])
    walk = paths['WALK_BEACH']
    wl = walk['polyline_m']
    lo = max(i for i, p in enumerate(wl) if p[0] <= WALK_KEEP[0])
    hi = min(i for i, p in enumerate(wl) if p[0] >= WALK_KEEP[1])
    assert all(p[0] < q[0] for p, q in zip(wl[lo:hi], wl[lo+1:hi+1]))
    controls = [wl[lo-1], wl[lo]]+BAY_WALK+[wl[hi], wl[hi+1]]
    pts = curve(controls, 3)
    walk['polyline_m'] = wl[:lo+1]+pts[3+1:3*(len(controls)-2)]+wl[hi:]
    walk['length_m'] = plen(walk['polyline_m'])
    walk['rerouted_v14_ru'] = 'В бухте тропа по песку ближе к дюне.'
    new_walk = walk['polyline_m']

    def walk_y(x):
        for p, q in zip(new_walk, new_walk[1:]):
            if p[0] <= x <= q[0]:
                return p[1]+(q[1]-p[1])*(x-p[0])/(q[0]-p[0])
        raise ValueError(x)
    trimmed = {}
    for pid in PARK_PATHS:
        p = paths[pid]
        keep = []
        for q in p['polyline_m']:
            if q[1] <= walk_y(q[0])+2.5:
                break
            keep.append(q)
        trimmed[pid] = len(p['polyline_m'])-len(keep)
        p['polyline_m'] = keep+[list(nearest(keep[-1], new_walk)[1])]
        p['length_m'] = plen(p['polyline_m'])
        p['end_v14_ru'] = 'Конец тропинки перенесён на новую тропу вдоль бухты.'
    old_section = se[k0:k1+1]
    new_section = new_se[k0:k0+len(inner)+2]
    apex = max(inner, key=lambda p: p[1])
    old_y = next(p[1]+(q[1]-p[1])*(apex[0]-p[0])/(q[0]-p[0]) for p, q in zip(old_section, old_section[1:]) if p[0] <= apex[0] <= q[0])
    d['bay'] = dict(id='BAY14_PARKING', name_ru='Бухта у пляжной парковки', beach_id='BEACH',
        purpose_ru='Небольшая бухта напротив пляжной парковки (Федя 06.10); пляж вокруг неё остаётся песчаным.',
        opposite_site_ids=['PARK13_LOT_W', 'PARK13_LOT_E', 'PARK13_DROP_OFF'],
        sea_edge_m=new_section, v13_sea_edge_m=old_section, apex_m=apex, depth_m=round(apex[1]-old_y, 1),
        mouth_m=[BAY_SEA[0], BAY_SEA[-1]], mouth_width_m=round(m.length(BAY_SEA[0], BAY_SEA[-1]), 1),
        water_area_m2=round(m.area(old_section+list(reversed(new_section))), 1),
        sand_at_apex_m=round(nearest(apex, beach['land_edge_m'])[0], 1),
        rocks=[dict(id=rid, polygon_m=oval(c, r, ph, 16), barrier=False, label_ru='камни на мысу') for rid, (c, r, ph) in BAY_ROCKS.items()],
        walk_path_id='WALK_BEACH', car_park_path_ids=list(PARK_PATHS), trimmed_path_vertices=trimmed,
        swimming_ru='Мелко и спокойно; дно песчаное.')


def square_trees(poly):
    """Lindens along the inner edge of the square; gaps at the hub corner, the tower passage and the fountain."""
    c = centroid(poly)
    out = []
    for p in v12.sample_line(poly+[poly[0]], 8.5)[:-1]:
        dx, dy = c[0]-p[0], c[1]-p[1]
        n = math.hypot(dx, dy)
        q = [round(p[0]+dx/n*3.4, 2), round(p[1]+dy/n*3.4, 2)]
        if (m.length(q, FOUNTAIN_C) < FOUNTAIN_R+6 or m.length(q, [664, 548]) < 9 or abs(q[0]-691) < 5.5 and q[1] > 578 or
                any(m.length(q, t) < 6 for t in out) or any(m.length(q, lw[0]) < 9 for lw in LAWNS)):
            continue
        out.append(q)
    return out


def rebuild_old_town(d):
    """Twin towers and a big square east of the north-south avenue; mid-rise around the square; low houses kept further out."""
    bs, fs, pts = by_id(d['building_masses']), by_id(d['functional_buildings']), by_id(d['points'])
    for bid, reason in OT_REMOVED_MASSES.items():
        b = bs[bid]
        d['removed_buildings'].append(dict(id=bid, kind=b['kind'], from_district='old_town', access_road_id='ACCESS_'+bid,
            removed_in='v14', center_m=b['center_m'], footprint_m=b['polygon_m'], floors=b['floors'], reason_ru=reason))
    d['building_masses'] = [b for b in d['building_masses'] if b['id'] not in OT_REMOVED_MASSES]
    d['roads'] = [r for r in d['roads'] if r['id'] not in OT_REMOVED_ROADS]
    d['plots'] = [p for p in d['plots'] if p['id'] not in OT_REMOVED_PLOTS]
    roads = by_id(d['roads'])
    lanes = roads['O_LANES']
    ol = lanes['polyline_m']
    assert ol[0] == ol[-1]
    tip = next(i for i, p in enumerate(ol) if m.length(p, CONNECTOR_TIP) < .05)
    join = next(i for i, p in enumerate(ol) if m.length(p, CONNECTOR_JOIN) < .05)
    conn = roads['OLD_TOWN_CONNECTOR']['polyline_m']
    hit = next(h for c1, c2 in zip(conn, conn[1:]) if (h := m.crossing(ol[join], ol[join+1], c1, c2)))
    lanes['polyline_m'] = ol[tip:]+ol[1:join+1]+[hit[0]]
    lanes['length_m'] = plen(lanes['polyline_m'])
    lanes['reshaped_v14_ru'] = ('Северо-восточная дуга через квартал башен убрана: улица идёт от тупичка у кафе по востоку, югу и '
                                'западу и выходит на проспект к площади.')
    for tid, c in TOWERS.items():
        twin = next(t for t in TOWERS if t != tid)
        d['building_masses'].append(dict(id=tid, district_id='old_town', kind='tower', center_m=c, width_m=TOWER_SIZE,
            depth_m=TOWER_SIZE, floors=TOWER_FLOORS, polygon_m=m.rectangle(*c, TOWER_SIZE, TOWER_SIZE, 0), rotation_deg=0,
            twin_id=twin, height_target_m=round(TOWER_FLOORS*3.3, 1), role='башня-близнец у площади, лицом к району подворотен',
            entrances_face='площадь; без своего подъезда'))
    for mid, (c, w, h, a, floors, role) in MIDRISE.items():
        d['building_masses'].append(dict(id=mid, district_id='old_town', kind='midrise', center_m=c, width_m=w, depth_m=h,
            floors=floors, polygon_m=m.rectangle(*c, w, h, a), rotation_deg=a, height_target_m=round(floors*3.2, 1), role=role,
            entrances_face='улица и площадь; без своего подъезда'))
    rep = fs['F06_REPAIR']
    door = [REPAIR_C[0]-rep['width_m']/2-REPAIR_DOOR_GAP, REPAIR_C[1]]
    rep.update(center_m=REPAIR_C, footprint_m=m.rectangle(*REPAIR_C, rep['width_m'], rep['depth_m'], 0), entrance_m=door)
    start = list(nearest(door, lanes['polyline_m'])[1])
    roads['ACCESS_P05'].update(polyline_m=[start, door], length_m=round(m.length(start, door), 3))
    pts['P05']['position_m'] = door
    cafe = fs['F06_CAFE2']
    roads['ACCESS_F06_CAFE2'].update(polyline_m=[list(lanes['polyline_m'][0]), cafe['entrance_m']],
                                     length_m=round(m.length(lanes['polyline_m'][0], cafe['entrance_m']), 3))
    pts['CLOCK_SQUARE']['name_ru'] = 'Площадь у башен'
    sq = rounded(SQUARE, 4)
    d['functional_sites'] += [
        dict(id='TOWER_SQUARE14', type='square', district_id='old_town', polygon_m=sq, surface='paving', label_ru='Площадь у башен',
             landmark_point_id='CLOCK_SQUARE', tower_ids=list(TOWERS), fountain_site_id='FOUNTAIN14',
             lawns_m=[oval(c, r, ph, 24) for c, r, ph in LAWNS], trees_m=square_trees(sq),
             dressing_hints_ru=['лавочки по краю и у фонтана', 'фонари', 'липы по краю площади', 'две клумбы по бокам от фонтана',
                                'часы на фасаде башни над площадью (канон: площадь с часами)']),
        dict(id='FOUNTAIN14', type='fountain', district_id='old_town', position_m=FOUNTAIN_C,
             polygon_m=circle(FOUNTAIN_C, FOUNTAIN_R+.6, 32), basin_radius_m=FOUNTAIN_R, label_ru='Фонтан с памятником',
             monument=dict(id='MONUMENT14', position_m=FOUNTAIN_C, pedestal_radius_m=MONUMENT_R, statue_height_m=4.5,
                           label_ru='Памятник на фонтане (условный)')),
        dict(id='POLICE14_LOT', type='parking', district_id='old_town', building_id='F06_POLICE', polygon_m=POLICE_LOT,
             capacity_vans=4, access_polyline_m=POLICE_LOT_ACCESS, access_road_id='O_LANES', label_ru='Стоянка полиции',
             source='PARK_F06_POLICE из MAP_DRESSING_R01_v12.json: её читает полиция v1; в v14 место сохранено'),
    ]
    by_id(d['districts'])['old_town']['notes_ru'] = ('Старый город: на севере две башни по 20 этажей лицом к подворотням и большая площадь '
                                                    'с фонтаном и памятником; вокруг площади дома 5–7 этажей, дальше прежние низкие дома; канал на месте.')


MOVE_REASONS = {
    'Мастерская P05 перенесена в ЮВ угол старого города: на её месте теперь башня у площади.': [('point', 'P05'), ('building', 'F06_REPAIR')],
}


def record_moves(d, original):
    before, after = v13.positions(original), v13.positions(d)
    for reason, keys in MOVE_REASONS.items():
        for key in keys:
            a, b = before[key], after[key]
            d['moves'].append(dict(kind=key[0], id=key[1], from_m=a, to_m=b, distance_m=round(m.length(a, b), 2),
                                   id_kept=True, reason_ru=reason))
    d['land_transfers'] = [
        dict(ids=['BEACH', 'SEA'], from_district='beach sand', to_district='sea',
             note_ru=f'Бухта у парковки: {d["bay"]["water_area_m2"]:.0f} м² песка стали водой; остальной пляж без изменений.'),
        dict(ids=list(VALLEY_REMOVED), from_district='fields', to_district='fields',
             note_ru='Места ночного клуба и боулинга — газон долины (контур района не менялся).'),
    ]


def v23_position(data, kind, oid):
    """Position of a v13 record in metres for the v23 comparison."""
    if kind == 'church':
        return by_id(data['functional_buildings'])[oid]['nave_center_m']
    if kind in ('building', 'removed'):
        return by_id(data['functional_buildings'])[oid]['center_m']
    if kind == 'point':
        return by_id(data['points'])[oid]['position_m']
    if kind == 'water':
        return by_id(data['water'])[oid]['center_m']
    if kind == 'district':
        return centroid(by_id(data['districts'])[oid]['polygon_m'])
    if kind == 'hill':
        return by_id(data['hills'])[oid]['center_m']
    if kind == 'site':
        s = by_id(data['functional_sites'])[oid]
        return s.get('position_m') or centroid(s['polygon_m'])
    if kind == 'crop':
        return centroid(by_id(data['crop_fields'])[oid]['polygon_m'])
    if kind == 'outfall':
        return centroid(by_id(data['outfalls'])[oid]['plume']['polygon_m'])
    if kind == 'swamp':
        return centroid(data['forest_features']['swamp']['polygon_m'])
    if kind == 'hangout':
        return by_id(data['functional_sites'])[oid]['dressing_hints']['campfire_ring']['position_m']
    if kind == 'rail':
        return by_id(data['functional_sites'])[oid]['position_m']
    if kind == 'beach':
        return centroid(by_id(data['beaches'])[oid]['polygon_m'])
    raise KeyError(kind)


def solve3(rows, target):
    """Least squares for target = a*u + b*v + c (normal equations, Gaussian elimination)."""
    mat = [[sum(r[i]*r[j] for r in rows) for j in range(3)] for i in range(3)]
    vec = [sum(r[i]*t for r, t in zip(rows, target)) for i in range(3)]
    for i in range(3):
        p = max(range(i, 3), key=lambda k: abs(mat[k][i]))
        mat[i], mat[p], vec[i], vec[p] = mat[p], mat[i], vec[p], vec[i]
        for k in range(i+1, 3):
            g = mat[k][i]/mat[i][i]
            mat[k] = [x-g*y for x, y in zip(mat[k], mat[i])]
            vec[k] -= g*vec[i]
    out = [0.0]*3
    for i in reversed(range(3)):
        out[i] = (vec[i]-sum(mat[i][k]*out[k] for k in range(i+1, 3)))/mat[i][i]
    return out


def v23_alignment(original):
    rows = [(px[0], px[1], 1) for px, kind, oid in V23_ANCHORS]
    targets = [v23_position(original, kind, oid) for px, kind, oid in V23_ANCHORS]
    coef = [solve3(rows, [t[k] for t in targets]) for k in (0, 1)]

    def to_m(px):
        return [round(sum(c*z for c, z in zip(coef[k], (px[0], px[1], 1))), 1) for k in (0, 1)]
    residuals = [round(m.length(to_m(px), t), 1) for (px, kind, oid), t in zip(V23_ANCHORS, targets)]
    objects = []
    for label, px, ref, decision, note in V23_OBJECTS:
        pos = to_m(px)
        row = dict(label_ru=label, v23_px=list(px), v23_m=pos, decision=decision, decision_ru=DECISIONS_RU[decision], note_ru=note)
        if ref:
            v13pos = [round(z, 1) for z in v23_position(original, *ref)]
            row.update(v13_ref=list(ref), v13_m=v13pos, distance_m=round(m.length(pos, v13pos), 1))
        objects.append(row)
    return dict(source='REF_FEDYA_v14_map_v23.png (1280 × 1280 px)', method='affine least squares px → m on 22 shared objects',
        coefficients=[[round(z, 5) for z in c] for c in coef], anchor_count=len(V23_ANCHORS),
        residual_median_m=sorted(residuals)[len(residuals)//2], residual_max_m=max(residuals),
        clear_difference_m=CLEAR_DIFF_M, objects=objects, applied_moves=[],
        rule_ru='Федя 06.10: менять только названные куски. Из сверки переносятся только объекты, которые явно стоят не там, '
                'и только если это не требует перерисовки неназванного района и не ломает канон.')


def notes(d):
    d['planning_notes_ru'] = [
        'v14 меняет только названные куски (правило Феди 06.10); остальное побайтно как в v13 — это проверяет охрана областей.',
        'Малая долина: ночной клуб и боулинг/аркада убраны вместе с подъездами и хвостом дороги; казино и его парковка на месте.',
        'Пристань элитки у разворота на пляже: пирс 64 м с Т-образной головой, 3 понтона, 10 мест, 3 яхты и 4 катера, каменный мол.',
        'Напротив пляжной парковки — небольшая бухта: песок обходит её, тропа и три тропинки с парковки ведут на песок.',
        'Старый город: на севере две башни по 20 этажей лицом к подворотням, перед ними большая площадь с фонтаном и памятником.',
        'Вокруг площади дома 5–7 этажей; дальше прежние низкие дома 2–3 этажа; канал, полиция P10 и её стоянка на месте.',
        'Сверка с картинкой v23: всё, что совпадает, оставлено; явные расхождения не переносили (канон или неназванные районы).',
    ]
    d['distribution_targets'] = {'policy': 'v14: local edits only; old town height gradient — twin towers 20 floors, mid-rise 5–7 '
                                           'within 100 m of the towers, low houses 2–3 floors beyond 110 m'}


# ------------------------------------------------------------------ region guard against v13
def region_tests(data):
    return [(rid, kind, geo if kind == 'bbox' else by_id(data['districts'])[geo]['polygon_m']) for rid, label, kind, geo in REGIONS]


def in_regions(p, regions):
    for rid, kind, geo in regions:
        if kind == 'bbox':
            x0, y0, x1, y1 = geo
            if x0-REGION_TOL <= p[0] <= x1+REGION_TOL and y0-REGION_TOL <= p[1] <= y1+REGION_TOL:
                return rid
        elif m.inside(p, geo) or v7.gap(geo, p, p) <= REGION_TOL:
            return rid
    return None


def is_pair(o):
    return isinstance(o, list) and len(o) == 2 and all(isinstance(z, (int, float)) and not isinstance(z, bool) for z in o)


def geo_points(o, key=''):
    """Every coordinate pair under a *_m key (sizes and radii excluded), rounded to 1 mm."""
    if isinstance(o, dict):
        return [p for k, v in o.items() if k not in DERIVED and k not in GEO_SKIP for p in geo_points(v, k)]
    if isinstance(o, list):
        if is_pair(o):
            return [(round(o[0], 3), round(o[1], 3))] if key.endswith('_m') else []
        return [p for v in o for p in geo_points(v, key)]
    return []


def strip_derived(o):
    if isinstance(o, dict):
        return {k: strip_derived(v) for k, v in o.items() if k not in DERIVED}
    if isinstance(o, list):
        return [strip_derived(v) for v in o]
    return o


def strip_geo(o, key=''):
    """The record without derived fields and with every coordinate list collapsed to 'geo' (metadata only)."""
    if isinstance(o, dict):
        return {k: strip_geo(v, k) for k, v in o.items() if k not in DERIVED}
    if isinstance(o, list):
        if is_pair(o) and key.endswith('_m') and key not in GEO_SKIP:
            return 'geo'
        items = [strip_geo(v, key) for v in o]
        return 'geo' if items and all(x == 'geo' for x in items) else items
    return o


def guard(old, new, regions):
    """Compare every non-log top-level item of v13 and v14 record by record. Returns (geometry issues, metadata issues,
    changed record keys). A geometry issue is a coordinate added or removed outside every region; a metadata issue is a
    changed non-geometric field on a record that does not touch any region (unless listed in META_ALLOWED)."""
    geo_issues, meta_issues, changed = [], [], []

    def compare(where, a, b):
        if a is not None and b is not None and strip_derived(a) == strip_derived(b):
            return
        changed.append(where)
        pa = set(geo_points(a)) if a is not None else set()
        pb = set(geo_points(b)) if b is not None else set()
        outside = sorted(p for p in pa ^ pb if not in_regions(p, regions))
        if outside:
            geo_issues.append(f'{where[0]}/{where[1]}: {len(outside)} points, e.g. {outside[:2]}')
        if a is not None and b is not None and strip_geo(a) != strip_geo(b):
            fields = sorted(k for k in set(a) | set(b) if k not in DERIVED and strip_geo(a.get(k), k) != strip_geo(b.get(k), k)) \
                if isinstance(a, dict) and isinstance(b, dict) else ['value']
            touches = any(in_regions(p, regions) for p in pa | pb)
            if not touches and not set(fields) <= META_ALLOWED.get(where, set()):
                meta_issues.append(f'{where[0]}/{where[1]}: {fields}')
    for key in sorted(set(old) | set(new)):
        if key in LOG_KEYS:
            continue
        a, b = old.get(key), new.get(key)
        keyed = [x for x in (a, b) if isinstance(x, list) and x and isinstance(x[0], dict) and 'id' in x[0]]
        if keyed:
            ia, ib = by_id(a or []), by_id(b or [])
            for rid in sorted(set(ia) | set(ib)):
                compare((key, rid), ia.get(rid), ib.get(rid))
        else:
            compare((key, None), a, b)
    return geo_issues, meta_issues, changed


def trees_outside(data, regions):
    conifers, rounds = v13.tree_layers(data)
    return sorted(tuple(t) for t in conifers+rounds if not in_regions(t[:2], regions))


# ------------------------------------------------------------------ checks
SUPERSEDED = {  # v13 checks whose premise v14 changes on purpose -> the v14 check that replaces each
    'old town keeps 19 buildings, mandatory functions and two towers':
        'old town rebuilt (Fedya 06.10): see "old town: two twin towers…", "…height gradient…", "…functions kept…"',
    'casino, club and bowling retained in the valley': 'Fedya 06.10 removed the club and the bowling: see "valley: …"',
    'no other road enters the beach or the cove': 'marina quay road on the sand: see "beach roads: …"',
    'beach width 45–60m along whole curve': 'the bay narrows the sand on purpose: see "bay: beach width …"',
    'v12 and earlier file hashes unchanged during the run': 'v14 provenance covers v02–v13: see "v13 and earlier deliverables …"',
    'guard: transition (minus church), old town, elite, valley and main beach identical to v12 except the 12 recorded border fences':
        'v14 region guard against v13: see "region guard: …"',
    'every id moved by >0.5m is recorded in moves with its id kept': 'v14 moves are recorded against v13: see "every id moved … vs v13 …"',
}
EXTRA_ROUTES = [('ELITE_GATE', 'ELITE_MARINA'), ('CLOCK_SQUARE', 'ELITE_MARINA'), ('CLOCK_SQUARE', 'P05'), ('B04', 'P05')]


def analyse(d, strict=True):
    v13.analyse(d, strict=False)
    old_checks = d['validation']['checks']
    missing = set(SUPERSEDED)-{c['name'] for c in old_checks}
    assert not missing, missing
    kept = [c for c in old_checks if c['name'] not in SUPERSEDED]
    superseded = [dict(name=c['name'], result_on_v14_data=c['passed'], replaced_by=SUPERSEDED[c['name']])
                  for c in old_checks if c['name'] in SUPERSEDED]
    pts = by_id(d['points'])
    for a, b in EXTRA_ROUTES:
        dist, ids = m.shortest(d, pts[a]['road_node_id'], pts[b]['road_node_id'])
        er = {e['id']: e['road_id'] for e in d['road_graph']['edges']}
        rids = []
        for eid in ids:
            if not rids or rids[-1] != er[eid]:
                rids.append(er[eid])
        d['metrics']['routes'].append(dict(from_id=a, to_id=b, length_m=round(dist, 3), edge_ids=ids, road_ids=rids,
                                           van_60_seconds=round(dist/(60/3.6), 2), added_in='v14'))
    new_checks = v14_checks(d)
    checks = kept+new_checks
    d['validation'] = dict(passed=all(c['passed'] for c in checks), checks=checks, superseded_v13_checks=superseded,
                           v13_suite_kept=len(kept), v14_added=len(new_checks))
    if strict and not d['validation']['passed']:
        raise ValueError(json.dumps([c for c in checks if not c['passed']], ensure_ascii=False, indent=2))
    return [c for c in checks if not c['passed']]


def v14_checks(d):
    checks = []

    def check(name, ok, detail=''):
        checks.append(dict(name=name, passed=bool(ok), detail=str(detail)[:700]))
    old = source_data()
    regions = region_tests(old)
    ds, pts, fs, bs = by_id(d['districts']), by_id(d['points']), by_id(d['functional_buildings']), by_id(d['building_masses'])
    roads, paths, sites, waters = by_id(d['roads']), by_id(d['paths']), by_id(d['functional_sites']), by_id(d['water'])
    ofs, oroads, osites, opaths = by_id(old['functional_buildings']), by_id(old['roads']), by_id(old['functional_sites']), by_id(old['paths'])
    phys = v7.physical(d)
    beach, cove = d['beaches']
    sea = waters['SEA']['polygon_m']
    bp = d['boundary']['polygon_m']
    # ---------------------------------------------------------- guard
    geo_issues, meta_issues, changed = guard(old, d, regions)
    per_kind = Counter(k for k, _ in changed)
    check('region guard: every geometry change vs v13 lies inside the 5 declared change regions', not geo_issues,
          geo_issues or f'{len(changed)} changed records: {dict(sorted(per_kind.items()))}')
    check('region guard: no metadata edits outside the change regions (only the valley district note)', not meta_issues, meta_issues)
    t_old, t_new = trees_outside(old, regions), trees_outside(d, regions)
    check('trees outside the change regions identical to v13 (forest, hamlet, green strip)', t_old == t_new, f'{len(t_new)} trees')
    current = hashes()
    check('v13 and earlier deliverables unchanged during the run (sha256), including the hashes recorded by v13',
          current == d['provenance']['previous_files_sha256'] and
          all(current.get(n) == h for n, h in old['provenance']['previous_files_sha256'].items()), f'{len(current)} files')
    # ---------------------------------------------------------- 1. valley
    removed = {q['id'] for q in d['removed_buildings'] if q.get('removed_in') == 'v14'}
    gone = all(f not in fs for f in VALLEY_REMOVED) and all(r not in roads for r in VALLEY_REMOVED.values())
    same = (fs['F12_CASINO'] == ofs['F12_CASINO'] and sites['CASINO12_PARKING'] == osites['CASINO12_PARKING'] and
            roads['ACCESS_F12_CASINO'] == oroads['ACCESS_F12_CASINO'] and fs['F07_VILLA'] == ofs['F07_VILLA'])
    valley = sorted(f['type'] for f in fs.values() if f['district_id'] == 'fields')
    check('valley: night club and bowling/arcade removed with their driveways and recorded; casino, its driveway and parking and the villa identical to v13',
          gone and set(VALLEY_REMOVED) <= removed and same and valley == ['casino', 'prestige_base'], valley)
    vb, ovb = roads['VALLEY_BRANCH']['polyline_m'], oroads['VALLEY_BRANCH']['polyline_m']
    check('valley: VALLEY_BRANCH ends inside the casino lot (the tail to the bowling trimmed), every kept vertex identical',
          vb == ovb[:len(vb)] and len(vb) < len(ovb) and m.inside(vb[-1], sites['CASINO12_PARKING']['polygon_m']),
          f'{len(ovb)} -> {len(vb)} vertices, end {vb[-1]}')
    # ---------------------------------------------------------- 2. marina
    mar = d['marina']
    deck = [mar['pier']['polygon_m'], mar['t_head']['polygon_m']]+[f['polygon_m'] for f in mar['fingers']]
    root_ok = nearest(mar['root_m'], beach['sea_edge_m'])[0] < .05
    over_sea = (all(m.inside(p, sea) for poly in deck[1:] for p in poly) and
                all(m.inside(p, sea) for p in deck[0] if m.length(p, mar['root_m']) > 6) and
                any(m.inside(p, beach['polygon_m']) for p in deck[0]))
    quay = sites['MARINA14_QUAY']['polygon_m']
    quay_ok = m.inside(centroid(quay), beach['polygon_m']) and all(m.inside(p, beach['polygon_m']) or m.inside(p, sea) for p in quay)
    check('marina: 4 m pier with a T-head and 3 finger pontoons over the sea, rooted on the waterline at a quay on the sand',
          root_ok and over_sea and quay_ok and len(mar['fingers']) >= 3, f'root {mar["root_m"]}, axis {mar["axis_deg"]}°')
    boats, berths = mar['boats'], by_id(mar['berths'])
    kinds = Counter(b['kind'] for b in boats)
    hits = [(a['id'], c['id']) for i, a in enumerate(boats) for c in boats[i+1:] if strict_overlap(a['polygon_m'], c['polygon_m'])]
    hits += [(b['id'], 'deck') for b in boats for poly in deck if strict_overlap(b['polygon_m'], poly)]
    hits += [(a, c) for i, a in enumerate(sorted(berths)) for c in sorted(berths)[i+1:]
             if strict_overlap(berths[a]['polygon_m'], berths[c]['polygon_m'])]
    hits += [(b, 'deck') for b in berths for poly in deck if strict_overlap(berths[b]['polygon_m'], poly)]
    off = [b['id'] for b in boats if not all(m.inside(p, berths[b['berth_id']]['polygon_m']) and m.inside(p, sea) for p in b['polygon_m'])]
    check('marina: >=8 berths with >=2 yachts and >=3 motor boats, each boat inside its berth and in the sea, nothing overlaps',
          len(berths) >= 8 and kinds['yacht'] >= 2 and kinds['motorboat'] >= 3 and not hits and not off,
          f'{len(berths)} berths, {dict(kinds)}, {hits or off}')
    bw = mar['breakwater']
    bw_ok = all(m.inside(p, sea) or contained(p, bp) for p in bw['polygon_m']) and \
        v7.gap(beach['polygon_m'], bw['axis_m'][0], bw['axis_m'][1]) < 1.5
    channel = min(poly_gap(bw['polygon_m'], poly) for poly in deck+[b['polygon_m'] for b in berths.values()])
    check('marina: stone breakwater in the sea, tied to the shore, >=8 m of clear water to every berth (fairway and entrance)',
          bw_ok and channel >= 8, f'{channel:.1f} m')
    route = next(r for r in d['metrics']['routes'] if (r['from_id'], r['to_id']) == ('ELITE_GATE', 'ELITE_MARINA'))
    to_sand = next(r for r in d['metrics']['routes'] if (r['from_id'], r['to_id']) == ('ELITE_GATE', 'BEACH_ENTRY'))
    q = roads['MARINA_QUAY']['polyline_m']
    cut = pts['ELITE_MARINA']['road_node_id'] not in v11.reachable(d['road_graph'], pts['B01']['road_node_id'],
                                                                  removed_roads=['BEACH_ACCESS'])
    check('marina: ELITE_MARINA reachable by van from the elite gate only via BEACH_ACCESS and the 17 m quay road '
          '(= elite gate → beach turnaround + quay), quay road on the sand from the turnaround',
          route['road_ids'][-2:] == ['BEACH_ACCESS', 'MARINA_QUAY'] and cut and
          abs(route['length_m']-to_sand['length_m']-roads['MARINA_QUAY']['length_m']) < .5 and
          q[0] == roads['BEACH_ACCESS']['polyline_m'][-1] and all(m.inside(p, beach['polygon_m']) for p in q) and
          m.inside(q[0], sites['BEACH_TURNAROUND']['polygon_m']), f'{route["length_m"]:.0f} m via {route["road_ids"]}')
    elite_gap = v7.gap(ds['elite']['polygon_m'], mar['root_m'], mar['root_m'])
    check('marina next to the elite hill: pier root <=80 m from the elite district, on its own beach access', elite_gap <= 80,
          f'{elite_gap:.0f} m')
    touching = sorted(r['id'] for r in d['roads'] if any(m.inside(p, beach['polygon_m']) or m.inside(p, cove['polygon_m'])
                                                          for p in r['polyline_m']))
    check('beach roads: only BEACH_ACCESS, BEACH_VALLEY_ACCESS and the marina quay (an extension inside the sand) touch the sand',
          touching == ['BEACH_ACCESS', 'BEACH_VALLEY_ACCESS', 'MARINA_QUAY'] and beach['access_road_ids'] == ['BEACH_ACCESS', 'BEACH_VALLEY_ACCESS'],
          touching)
    # ---------------------------------------------------------- 3. bay
    bay = d['bay']
    lot_x = [p[0] for p in ds['beach_parking']['polygon_m']]
    check('bay: the coast recedes 25–45 m at the apex, mouth 90–160 m, apex opposite the beach car park',
          25 <= bay['depth_m'] <= 45 and 90 <= bay['mouth_width_m'] <= 160 and min(lot_x) <= bay['apex_m'][0] <= max(lot_x),
          f'depth {bay["depth_m"]} m, mouth {bay["mouth_width_m"]} m, apex {bay["apex_m"]}, {bay["water_area_m2"]:.0f} m² of water')
    le, se = beach['land_edge_m'], beach['sea_edge_m']
    k0, k1 = BAY_KEEP
    shift = len(se)-len(le)
    width_out = [m.length(le[i], se[i if i <= k0 else i+shift]) for i in range(len(le)) if i <= k0 or i >= k1]
    width_in = [nearest(p, le)[0] for p in se[k0+1:k1+shift]]
    check('bay: beach width 45–60 m everywhere outside the bay, >=18 m of sand inside it',
          all(45 <= w <= 60 for w in width_out) and min(width_in) >= 18, f'outside {min(width_out):.1f}–{max(width_out):.1f} m, '
          f'bay min {min(width_in):.1f} m')
    walk = paths['WALK_BEACH']['polyline_m']
    bay_walk = [p for p in walk if WALK_KEEP[0] < p[0] < WALK_KEEP[1]]
    gw = min(nearest(p, se)[0] for p in bay_walk)
    gd = min(nearest(p, le)[0] for p in bay_walk)
    heads = all(paths[p]['polyline_m'][:-1] == opaths[p]['polyline_m'][:len(paths[p]['polyline_m'])-1] for p in PARK_PATHS)
    ends = [p for p in PARK_PATHS if not (nearest(paths[p]['polyline_m'][-1], walk)[0] < .01 and
                                           m.inside(paths[p]['polyline_m'][-1], beach['polygon_m']) and
                                           nearest(paths[p]['polyline_m'][-1], se)[0] >= 3)]
    check('bay: WALK_BEACH stays on the sand >=4 m from the water and the dune; the 3 car-park paths keep their v13 course and end on it in the sand',
          all(contained(p, beach['polygon_m']) for p in walk) and gw >= 4 and gd >= 4 and heads and not ends,
          f'water {gw:.1f} m, dune {gd:.1f} m, {ends}')
    # ---------------------------------------------------------- 4. old town
    ot = ds['old_town']['polygon_m']
    tw = sorted([b for b in bs.values() if b['district_id'] == 'old_town' and b['floors'] >= 12], key=lambda b: b['center_m'][0])
    ys = [p[1] for p in ot]
    north_third = min(ys)+2/3*(max(ys)-min(ys))
    res_gap = [v7.gap(ds['residential']['polygon_m'], b['center_m'], b['center_m']) for b in tw]
    twins = (len(tw) == 2 and all(18 <= b['floors'] <= 22 for b in tw) and tw[0]['floors'] == tw[1]['floors'] and
             (tw[0]['width_m'], tw[0]['depth_m']) == (tw[1]['width_m'], tw[1]['depth_m']) and
             abs(tw[0]['center_m'][1]-tw[1]['center_m'][1]) <= 4 and 6 <= poly_gap(tw[0]['polygon_m'], tw[1]['polygon_m']) <= 14 and
             all(b['center_m'][1] >= north_third for b in tw) and max(res_gap) <= 40)
    check('old town: exactly two twin towers (18–22 floors, same footprint) side by side in its northern third, <=40 m from the alley district',
          twins, [(b['id'], b['floors'], b['center_m']) for b in tw]+[f'alleys {max(res_gap):.0f} m'])
    sq = sites['TOWER_SQUARE14']['polygon_m']
    sq_area = m.area(sq)
    front = max(poly_gap(sq, b['polygon_m']) for b in tw) if tw else 99
    on_sq = [b['id'] for b in phys if strict_overlap(b['poly'], sq)]
    on_sq += [r['id'] for r in d['roads']+d['paths'] if any(v7.gap(sq, a, c) < r['width_m']/2 for a, c in zip(r['polyline_m'], r['polyline_m'][1:]))]
    check('old town: big square >=2,500 m² right in front of (south of) the towers (<=6 m), clear of buildings and roads',
          sq_area >= 2500 and front <= 6 and all(centroid(sq)[1] < b['center_m'][1] for b in tw) and not on_sq and
          all(contained(p, ot) for p in sq), f'{sq_area:.0f} m², {front:.1f} m, {on_sq}')
    fo = sites['FOUNTAIN14']
    mon = fo['monument']
    check('old town: fountain inside the square with a monument on a pedestal at its centre',
          all(m.inside(p, sq) for p in fo['polygon_m']) and m.length(mon['position_m'], fo['position_m']) < .01 and
          0 < mon['pedestal_radius_m'] < fo['basin_radius_m'] and mon['statue_height_m'] > 2, fo['position_m'])
    mid = [(tw[0]['center_m'][k]+tw[1]['center_m'][k])/2 for k in (0, 1)] if len(tw) == 2 else [0, 0]
    rings = [(b['id'], b['floors'], round(m.length(b['center_m'], mid))) for b in bs.values()
             if b['district_id'] == 'old_town' and b not in tw]
    near = [r for r in rings if r[2] <= GRADIENT_NEAR]
    far = [r for r in rings if r[2] > GRADIENT_FAR]
    band = [r for r in rings if GRADIENT_NEAR < r[2] <= GRADIENT_FAR]
    around = [b['id'] for b in bs.values() if b['kind'] == 'midrise' and poly_gap(b['polygon_m'], sq) > 40]
    check('old town height gradient: every house within 100 m of the towers 5–7 floors (>=4, all within 40 m of the square), '
          'every house beyond 110 m 2–3 floors (>=8), none in between',
          len(near) >= 4 and all(5 <= f <= 7 for _, f, _ in near) and len(far) >= 8 and all(f <= 3 for _, f, _ in far) and
          not band and not around, f'near {sorted(near, key=lambda r: r[2])} / far {len(far)} max {max((f for _, f, _ in far), default=0)} / {band} {around}')
    police_same = fs['F06_POLICE'] == ofs['F06_POLICE'] and roads['ACCESS_P10'] == oroads['ACCESS_P10'] and \
        strip_derived(pts['P10']) == strip_derived(by_id(old['points'])['P10'])
    lot = sites['POLICE14_LOT']
    lot_hits = [b['id'] for b in phys if strict_overlap(b['poly'], lot['polygon_m'])]
    lot_hits += [r['id'] for r in d['roads'] if any(v7.gap(lot['polygon_m'], a, c) < r['width_m']/2 for a, c in zip(r['polyline_m'], r['polyline_m'][1:]))]
    check('old town: police P10, its building and driveway identical to v13; its 4-van lot (police v1) free of buildings and roads and opening onto O_LANES',
          police_same and not lot_hits and nearest(lot['access_polyline_m'][-1], roads['O_LANES']['polyline_m'])[0] < .05 and
          all(contained(p, ot) for p in lot['polygon_m']), lot_hits)
    reach = v11.reachable(d['road_graph'], pts['B01']['road_node_id'])
    ot_points = ['B04', 'P05', 'P09', 'P10', 'P11', 'P13-3', 'P13-5', 'CLOCK_SQUARE']
    functions = {'F06_HBASE', 'F06_SUPER', 'F06_REPAIR', 'F06_POLICE', 'F06_BANK', 'F06_CAFE2'}
    bad_pts = [p for p in ot_points if not contained(pts[p]['position_m'], ot) or pts[p]['road_node_id'] not in reach]
    check('old town: B04, P05, P09, P10, P11, P13-3, P13-5 and CLOCK_SQUARE inside it and reachable by van; HBASE, SUPER, REPAIR, POLICE, BANK and the purchasable cafe kept',
          not bad_pts and all(fs[f]['district_id'] == 'old_town' for f in functions) and fs['F06_CAFE2'].get('purchasable'), bad_pts)
    check('old town: its five through roads (TRANSITION_DIRECT, OLD_TOWN_CONNECTOR, OLD_ELITE_CONNECTOR, O_SPINE, I_CONNECT), the canal and its railings identical to v13',
          all(roads[r] == oroads[r] for r in TRUNK_ROADS) and waters['CANAL'] == by_id(old['water'])['CANAL'] and
          all(q == by_id(old['vegetation_parcels'])[q['id']] for q in d['vegetation_parcels'] if q['id'].startswith('CANAL_RAILING')))
    otb = [b for b in phys if b['district_id'] == 'old_town']
    fresh = set(TOWERS) | set(MIDRISE) | {'F06_REPAIR'}
    gaps = sorted((round(poly_gap(a['poly'], b['poly']), 2), a['id'], b['id']) for i, a in enumerate(otb) for b in otb[i+1:]
                  if a['id'] in fresh or b['id'] in fresh)
    check('old town: new and moved buildings stand >=4 m from every other building', gaps[0][0] >= 4, gaps[:3])
    # ---------------------------------------------------------- ids, moves, v23
    before, after = v13.positions(old), v13.positions(d)
    recorded = {(q['kind'], q['id']) for q in d['moves']}
    unrecorded = [k for k in after if k in before and m.length(before[k], after[k]) > .5 and k not in recorded]
    check('every id moved by >0.5 m vs v13 is recorded in moves with its id kept', not unrecorded and recorded and
          all(q['id_kept'] for q in d['moves']), unrecorded or sorted(recorded))
    unreach = [p['id'] for p in d['points'] if p['road_node_id'] not in reach]
    check('all 44 v13 point ids kept (B01–B06, P01–P16, CLOCK_SQUARE …) plus ELITE_MARINA, every point reachable by the van from B01',
          {p['id'] for p in old['points']} <= set(pts) and len(pts) == len(old['points'])+1 and not unreach, unreach)
    gone_ids = ({f['id'] for f in old['functional_buildings']} | {b['id'] for b in old['building_masses']})-set(fs)-set(bs)
    check('removed buildings recorded: night club, bowling, the two lone towers and two low houses (nothing else removed)',
          removed == gone_ids == set(VALLEY_REMOVED) | set(OT_REMOVED_MASSES), sorted(gone_ids))
    al = d['v23_alignment']
    bad = [o['label_ru'] for o in al['objects'] if (o['decision'] == 'match' and o.get('distance_m', 0) > CLEAR_DIFF_M) or
           (o['decision'] != 'match' and not o['note_ru'])]
    check('v23 alignment: picture fitted to metres (median residual <=12 m), every named v23 object classified, matches within 40 m, every difference explained',
          al['residual_median_m'] <= 12 and not bad and len(al['objects']) >= 40 and not al['applied_moves'],
          f'median {al["residual_median_m"]} m, {len(al["objects"])} objects, {bad}')
    return checks


def old_town_statistics(d):
    bs, fs, sites = by_id(d['building_masses']), by_id(d['functional_buildings']), by_id(d['functional_sites'])
    tw = [bs[t] for t in TOWERS]
    mid = [(tw[0]['center_m'][k]+tw[1]['center_m'][k])/2 for k in (0, 1)]
    rows = sorted(((round(m.length(b['center_m'], mid)), b['id'], b['kind'], b['floors']) for b in bs.values()
                   if b['district_id'] == 'old_town'), key=lambda r: (r[0], r[1]))
    d['old_town_statistics'] = dict(tower_ids=list(TOWERS), tower_floors=TOWER_FLOORS, tower_footprint_m=[TOWER_SIZE, TOWER_SIZE],
        tower_gap_m=round(poly_gap(tw[0]['polygon_m'], tw[1]['polygon_m']), 1),
        square_area_m2=round(m.area(sites['TOWER_SQUARE14']['polygon_m'])), fountain_basin_radius_m=FOUNTAIN_R,
        houses_by_distance_from_towers=[dict(distance_m=r[0], id=r[1], kind=r[2], floors=r[3]) for r in rows],
        midrise_ids=list(MIDRISE), low_house_count=sum(1 for r in rows if r[3] <= 3),
        functions=sorted(f['id'] for f in fs.values() if f['district_id'] == 'old_town'),
        building_count=sum(1 for b in v7.physical(d) if b['district_id'] == 'old_town'),
        policy='towers 20 floors; mid-rise 5–7 floors within 100 m of the towers; low houses 2–3 floors beyond 110 m; functions keep their own heights')


# ------------------------------------------------------------------ rendering
POINT_NAMES = dict(v13.POINT_NAMES, ELITE_MARINA='Пристань элитки', CLOCK_SQUARE='Площадь у башен')
SHORT = {k: v for k, v in v13.SHORT.items() if k not in VALLEY_REMOVED}
BG = v13.BG
OT_TOWER, OT_TOWER_TOP, OT_MID, OT_LOW = '#4e5f82', '#6f84aa', '#988c78', '#c4775a'
SQUARE_FILL, SQUARE_EDGE, LAWN = '#ece2c9', '#b8a985', '#b3cf97'
WATER_LIGHT, RIM, STATUE = '#8cc6dc', '#a59d8c', '#5a544c'
DECK, PONTOON, HULL, HULL_EDGE = '#a7845b', '#c9b38c', '#fbfaf5', '#4a5966'
STONE, STONE_EDGE, REGION_COLOR = '#a39c90', '#7b746a', '#d9822b'
REGION_TAGS = {'valley_club': '1', 'valley_bowling': '1', 'elite_marina': '2', 'parking_bay': '3', 'old_town': '4'}
CAPTIONS = {
    'full': [(t, p, z) for t, p, z in v13.CAPTIONS['full'] if t not in ('СТАРЫЙ ГОРОД', 'МАЛАЯ ДОЛИНА')] +
            [('СТАРЫЙ ГОРОД', [560, 532], 17), ('МАЛАЯ ДОЛИНА', [421, 460], 17), ('БУХТА', [652, 262], 15)],
    'old_town': [('СТАРЫЙ ГОРОД', [545, 600], 26), ('РАЙОН ПОДВОРОТЕН', [720, 633], 18)],
    'valley_beach': [('МАЛАЯ ДОЛИНА', [420, 452], 24), ('ПЛЯЖНАЯ ПАРКОВКА', [652, 402], 20), ('БУХТА', [652, 266], 24),
                     ('ПЛЯЖ', [520, 290], 20), ('МОРЕ', [560, 236], 22), ('СТАРЫЙ ГОРОД', [700, 458], 18)],
    'elite_marina': [('ЭЛИТНЫЙ ХОЛМ', [880, 585], 26), ('ПРИСТАНЬ', [1104, 556], 22), ('ПЛЯЖ', [1022, 640], 20),
                     ('МОРЕ', [1140, 640], 26), ('ПРОМЗОНА', [880, 708], 18)],
}
GEO_LABELS = {
    'full': list(v13.GEO_LABELS['full'])+[('фонтан с памятником', [703, 552], 11), ('башни 20 эт.', [691, 628], 11)],
    'old_town': [('фонтан с памятником', [703, 553], 15),
                 ('башни-близнецы · по 20 этажей', [691, 625], 16), ('дома 5–7 этажей вокруг площади', [606, 545], 14),
                 ('низкие дома 2–3 этажа', [520, 530], 14), ('низкие дома 2–3 этажа', [700, 460], 14),
                 ('Канал', [560, 433], 15), ('Проспект к подворотням', [637, 632], 14), ('стоянка полиции', [757, 617], 13),
                 ('мастерская P05 (перенесена)', [778, 503], 13)],
    'valley_beach': [('убран: ночной клуб', [376, 378], 14), ('убран: боулинг / аркада', [474, 350], 14),
                     ('парковка казино', [446, 404], 13), ('камни на мысу', [588, 245], 13), ('камни на мысу', [716, 239], 13),
                     ('тропа вдоль бухты', [652, 300.5], 13), ('тропинки на песок', [700, 318], 13), ('дюна', [540, 318], 13),
                     ('Канал', [560, 434], 14)],
    'elite_marina': [('мол с огоньком', [1112, 540], 14), ('яхты', [1126, 505], 14), ('катера', [1068, 529], 14),
                     ('пирс 64 м', [1083, 495], 14), ('площадка причала', [1040, 532], 13), ('разворот', [1027, 503], 13)],
}
CROP_LEGEND = {
    'old_town': [('tower', 'башня 20 эт.'), ('midrise', 'дом 5–7 эт.'), ('lowhouse', 'дом 2–3 эт.'), ('square', 'площадь'),
                 ('fountain', 'фонтан с памятником'), ('round', 'деревья'), ('lot', 'стоянка полиции')],
    'valley_beach': [('ghost', 'убранное здание'), ('water', 'море и бухта'), ('sand', 'пляж'), ('rocks', 'камни'),
                     ('passage', 'тропинка на песок'), ('dune', 'дюна'), ('bays', 'места 3,25 × 7 м')],
    'elite_marina': [('pier', 'пирс и понтоны'), ('yacht', 'яхта'), ('motorboat', 'катер'), ('berth', 'место у причала'),
                     ('breakwater', 'мол'), ('region', 'изменено в v14')],
}


def draw_extras(d, s, xy, scale, k, view):
    """v14 layers drawn after v13's map and before the labels: bay rocks, marina, old town styling, ghosts, change regions."""
    sites = by_id(d['functional_sites'])

    def poly(p, fill, stroke='none', width=1, **kw):
        s.poly([xy(q) for q in p], fill, stroke, width, **kw)

    def line(p, color, width=1, **kw):
        s.line([xy(q) for q in p], color, width, **kw)

    def dash(*v):
        return ' '.join(f'{x*k:.1f}' for x in v)
    for rock in d['bay']['rocks']:
        poly(rock['polygon_m'], '#a39d93', '#7f786e', .7*k)
    # marina
    mar = d['marina']
    poly(mar['breakwater']['polygon_m'], STONE, STONE_EDGE, .9*k)
    line(mar['breakwater']['axis_m'], '#c3bdb2', max(1.2, 1.6*scale), opacity='.7')
    if view != 'full':
        for b in mar['berths']:
            poly(b['polygon_m'], 'none', '#5f8796', .7*k, stroke_dasharray=dash(2, 2))
    for f in mar['fingers']:
        poly(f['polygon_m'], PONTOON, '#7d6a4c', .6*k)
    poly(mar['pier']['polygon_m'], DECK, '#6e5638', .7*k)
    poly(mar['t_head']['polygon_m'], DECK, '#6e5638', .7*k)
    for b in mar['boats']:
        poly(b['polygon_m'], HULL, HULL_EDGE, .8*k)
        c = b['center_m']
        x, y = xy(c)
        cab = max(1.2, (1.3 if b['kind'] == 'yacht' else .9)*scale)
        s.circle(x, y, cab, '#7fa6bd' if b['kind'] == 'motorboat' else '#c9b48a', stroke=HULL_EDGE, stroke_width=f'{.4*k:.1f}')
    lx, ly = xy(mar['breakwater']['light_m'])
    s.circle(lx, ly, max(2.2, .9*scale), '#f2cf5b', stroke='#6b5a3b', stroke_width=f'{.6*k:.1f}')
    # old town: square, lawns, fountain with the monument, trees, building heights
    sq = sites['TOWER_SQUARE14']
    poly(sq['polygon_m'], SQUARE_FILL, SQUARE_EDGE, .9*k)
    fo = sites['FOUNTAIN14']
    for r, colour in ((FOUNTAIN_R+5, '#e2d6b8'), (FOUNTAIN_R+2.4, '#d9ccab')):
        poly(circle(fo['position_m'], r, 40), colour, 'none')
    for lawn in sq['lawns_m']:
        poly(lawn, LAWN, '#90ad7c', .6*k)
    poly(circle(fo['position_m'], FOUNTAIN_R+.6, 40), RIM, '#7e7666', .7*k)
    poly(circle(fo['position_m'], FOUNTAIN_R, 40), WATER_LIGHT, '#5f97ad', .5*k)
    fx, fy = xy(fo['position_m'])
    s.circle(fx, fy, max(2.4, MONUMENT_R*scale), '#d8d1c3', stroke=STATUE, stroke_width=f'{.7*k:.1f}')
    u = max(1.0, .55*scale)
    s.circle(fx, fy-1.9*u, 1.0*u, STATUE)
    s.poly([[fx-1.1*u, fy-1.0*u], [fx+1.1*u, fy-1.0*u], [fx+.8*u, fy+1.6*u], [fx-.8*u, fy+1.6*u]], STATUE)
    for x, y in (xy(t) for t in sq['trees_m']):
        s.circle(x, y, max(2.2, 2.3*scale), '#86a874', stroke='#6d905f', stroke_width=f'{.6*k:.1f}', opacity='.95')
    bs = by_id(d['building_masses'])
    for b in bs.values():
        if b['district_id'] != 'old_town':
            continue
        fill = OT_TOWER if b['kind'] == 'tower' else OT_MID if b['kind'] == 'midrise' else OT_LOW
        poly(b['polygon_m'], fill, '#3f4646', .9*k)
        if b['kind'] == 'tower':
            c = b['center_m']
            inset = m.rectangle(*c, b['width_m']*.62, b['depth_m']*.62, b.get('rotation_deg', 0))
            poly(inset, OT_TOWER_TOP, 'none')
        x, y = xy(b['center_m'])
        size = (11 if b['kind'] == 'small_house' else 13 if b['kind'] == 'midrise' else 15)*(k if view == 'full' else 1.25)
        s.text(x, y+size*.36, f'{b["floors"]}э', size, '#fbf7ee', 'bold', 'middle')
    if view == 'valley_beach':
        for q in d['removed_buildings']:
            if q.get('removed_in') == 'v14' and q['from_district'] == 'fields':
                poly(q['footprint_m'], 'none', '#8a6f8f', 1.3*k, stroke_dasharray=dash(5, 4))
    if view in ('full', 'elite_marina'):
        for region in d['change_regions']:
            if view == 'elite_marina' and region['id'] != 'elite_marina':
                continue
            ring = region['polygon_m']+[region['polygon_m'][0]]
            line(ring, REGION_COLOR, 2.0*k, stroke_dasharray=dash(7, 5), opacity='.9')
            if view == 'full':
                corner = max(ring, key=lambda p: (p[1], -p[0]))
                x, y = xy(corner)
                s.circle(x, y, 11, REGION_COLOR, stroke='#fbf7ee', stroke_width='1.5')
                s.text(x, y+5, REGION_TAGS[region['id']], 14, '#fbf7ee', 'bold', 'middle')


def place_labels(d, s, xy, scale, k, area, view, phys):
    """v13 label placer with the v14 names; marina structures count as occupied."""
    fs = by_id(d['functional_buildings'])
    occupied = []

    def box_points(poly):
        p = [xy(q) for q in poly]
        return (min(x for x, y in p)-3, min(y for x, y in p)-3, max(x for x, y in p)+3, max(y for x, y in p)+3)
    occupied += [box_points(b['poly']) for b in phys]
    mar = d['marina']
    occupied += [box_points(p) for p in [mar['pier']['polygon_m'], mar['t_head']['polygon_m']]+[b['polygon_m'] for b in mar['boats']]]
    for text, p, size in CAPTIONS[view]:
        x, y = xy(p)
        s.text(x, y, text, size, '#546960', 'bold', 'middle', halo=True)
        width = len(text)*size*.55
        occupied.append((x-width/2-4, y-size-3, x+width/2+4, y+5))
    for text, p, size in GEO_LABELS[view]:
        x, y = xy(p)
        s.text(x, y, text, size, '#5f7477', 'normal', 'middle', halo=True)
        width = len(text)*size*.55
        occupied.append((x-width/2-2, y-size-1, x+width/2+2, y+3))
    labels = []
    x0, y0, x1, y1 = area

    def inside_view(p):
        return x0 <= xy(p)[0] <= x1 and y0 <= xy(p)[1] <= y1
    for p in d['points']:
        pid = p['id']
        value = POINT_NAMES[pid] if p['category'] in {'reference', 'landmark'} or pid.startswith(('BEACH', 'ELITE_MARINA')) else pid+' · '+POINT_NAMES[pid]
        if inside_view(p['position_m']) and not (view == 'full' and pid.startswith('BAD_BLOCK')):
            labels.append((0 if pid.startswith('B0') else 1, p['position_m'], value, p['category'] == 'base'))
    for fid, value in SHORT.items():
        if fid in fs and inside_view(fs[fid]['center_m']) and (view != 'full' or not (fid in ('F06_K1', 'F06_K3') or fid in v13.BUSINESSES)):
            labels.append((2, fs[fid]['center_m'], value, False))
    label_boxes = []

    def intersection(a, b):
        return max(0, min(a[2], b[2])-max(a[0], b[0]))*max(0, min(a[3], b[3])-max(a[1], b[1]))
    base_size = 15 if view == 'full' else 16
    for _, p, value, base in sorted(labels, key=lambda q: q[0]):
        x, y = xy(p)
        size = base_size+(1 if base else 0)
        w, h = len(value)*size*.55, size+4
        candidates = []
        for radius in (14, 30, 48, 70, 100, 135):
            for dx, dy in ((1, -1), (1, 1), (-1, -1), (-1, 1), (0, -1), (0, 1), (1, 0), (-1, 0)):
                lx, ly = x+dx*radius, y+dy*radius
                if dx < 0:
                    lx -= w
                elif dx == 0:
                    lx -= w/2
                if dy == 0:
                    ly += h/3
                bx = (lx-4, ly-h, lx+w+4, ly+5)
                if bx[0] < x0 or bx[2] > x1 or bx[1] < y0 or bx[3] > y1:
                    continue
                score = sum(intersection(bx, b) for b in occupied)*12+radius+abs(dx)*2
                candidates.append((score, bx, lx, ly, radius))
        if not candidates:
            continue
        _, bx, lx, ly, radius = min(candidates)
        tx, ty = max(bx[0], min(x, bx[2])), max(bx[1], min(y, bx[3]))
        if radius >= 30:
            s.line([[x, y], [tx, ty]], '#7e8b88', .75)
        s.circle(x, y, 3.8 if base else 2.8, '#b36f3f' if base else '#47707a', stroke='#f5f1e6', stroke_width='1')
        s.text(lx, ly, value, size, '#3b4e51', 'bold' if base else 'normal', halo=True)
        occupied.append(bx)
        label_boxes.append(bx)
    overlaps = sum(intersection(a, b) > 0 for i, a in enumerate(label_boxes) for b in label_boxes[i+1:])
    return len(label_boxes), overlaps


def draw_map(d, s, xy, scale, k, area, view):
    """v13's renderer with a hook: its label step first draws the v14 layers, then the v14 labels."""
    def hook(d2, s2, xy2, scale2, k2, area2, view2, phys):
        draw_extras(d2, s2, xy2, scale2, k2, view2)
        return place_labels(d2, s2, xy2, scale2, k2, area2, view2, phys)
    saved = v13.place_labels
    v13.place_labels = hook
    try:
        return v13.draw_map(d, s, xy, scale, k, area, view)
    finally:
        v13.place_labels = saved


def swatch(s, kind, x, y):
    """26 x 17 px legend icon, top-left at (x, y-12); v14 kinds here, the rest from v13."""
    if kind in ('tower', 'midrise', 'lowhouse'):
        s.rect(x, y-12, 26, 17, {'tower': OT_TOWER, 'midrise': OT_MID, 'lowhouse': OT_LOW}[kind], stroke='#3f4646', stroke_width='.8')
        if kind == 'tower':
            s.rect(x+7, y-8, 12, 9, OT_TOWER_TOP)
    elif kind == 'square':
        s.rect(x, y-12, 26, 17, SQUARE_FILL, stroke=SQUARE_EDGE, stroke_width='.9')
    elif kind == 'fountain':
        s.circle(x+13, y-3, 8, RIM, stroke='#7e7666', stroke_width='.7')
        s.circle(x+13, y-3, 6.6, WATER_LIGHT)
        s.circle(x+13, y-3, 2.2, STATUE)
    elif kind == 'lot':
        s.rect(x, y-12, 26, 17, '#bebdb2', stroke='#969c96', stroke_width='.6')
    elif kind == 'ghost':
        s.rect(x+1, y-11, 24, 15, 'none', stroke='#8a6f8f', stroke_width='1.3', stroke_dasharray='4 3')
    elif kind == 'sand':
        s.rect(x, y-12, 26, 17, '#efdfb2')
    elif kind == 'rocks':
        for dx, r in ((7, 4.5), (16, 3.5), (22, 2.5)):
            s.circle(x+dx, y-3, r, '#a39d93', stroke='#7f786e', stroke_width='.6')
    elif kind == 'pier':
        s.rect(x, y-6, 26, 5, DECK, stroke='#6e5638', stroke_width='.6')
        s.rect(x+8, y-12, 3, 6, PONTOON)
        s.rect(x+17, y-12, 3, 6, PONTOON)
    elif kind in ('yacht', 'motorboat'):
        ln = 24 if kind == 'yacht' else 15
        s.poly([[x, y-7], [x+ln-6, y-7], [x+ln, y-3], [x+ln-6, y+1], [x, y+1]], HULL, HULL_EDGE, .9)
        s.circle(x+ln/2-2, y-3, 2.2, '#c9b48a' if kind == 'yacht' else '#7fa6bd')
    elif kind == 'berth':
        s.rect(x+2, y-11, 22, 15, 'none', stroke='#5f8796', stroke_width='.8', stroke_dasharray='2 2')
    elif kind == 'breakwater':
        s.line([[x, y], [x+10, y-8], [x+26, y-9]], STONE, 6)
        s.circle(x+26, y-9, 2.5, '#f2cf5b', stroke='#6b5a3b', stroke_width='.6')
    elif kind == 'region':
        s.rect(x+1, y-11, 24, 15, 'none', stroke=REGION_COLOR, stroke_width='2', stroke_dasharray='6 4')
    else:
        v13.swatch(s, kind, x, y)


def legend_full(d, s, scale):
    s.line([[65, 1800], [2335, 1800]], '#c1c8ba', 1)
    s.text(75, 1842, 'ДОРОГИ И ПРЕГРАДЫ', 19, '#3b555a', 'bold')
    rows = [('highway', 'Проспект — 7 м, 2 полосы'), ('town_street', 'Городская — 6 м, 2 полосы'),
            ('rural_road', 'Сельская — 3,8 м, 1 полоса'), ('alley', 'Проезд подворотен — 4,5 м'),
            ('foot_lane', 'Пеший проход / арка — 3 м'), ('trail', 'Лесная тропа — 2 м'), ('passage', 'Пешком к пляжу — 2,5 м')]
    for i, (cls, label) in enumerate(rows):
        yy = 1872+i*29
        if cls in ('passage', 'foot_lane', 'trail'):
            swatch(s, {'passage': 'passage', 'foot_lane': 'lane', 'trail': 'trail'}[cls], 91, yy+3)
        else:
            s.line([[78, yy], [130, yy]], '#9d9f91', 10.2)
            s.line([[78, yy], [130, yy]], d['road_classes'][cls]['color'], 9)
        s.text(143, yy+5, label, 16)
    for i, (material, label) in enumerate([('elite_fence', 'Ограда элитки — 2,4 м'), ('barbed_fence', 'Колючая проволока промзоны — 2,8 м'),
                                           ('rock_scarp', 'Скалы / закрытый край'), ('dune_ridge', 'Дюна над пляжем: бусик не проедет'),
                                           ('canal_railing', 'Перила канала — 1,1 м')]):
        yy = 2086+i*29
        if material in ('barbed_fence', 'dune_ridge'):
            swatch(s, 'barbed' if material == 'barbed_fence' else 'dune', 91, yy+3)
        else:
            s.line([[78, yy], [130, yy]], v11.FENCE_STYLES[material][0], 3.2 if material == 'rock_scarp' else 2)
        s.text(143, yy+5, label, 16)
    s.text(560, 1842, 'ФИЗИЧЕСКИЕ ЗДАНИЯ', 19, '#3b555a', 'bold')
    old = d['comparison']['v13']['building_counts_by_district']
    for i, q in enumerate(d['districts']):
        yy = 1872+i*30
        s.rect(560, yy-12, 17, 17, q['color'])
        s.text(589, yy+2, q['name_ru'], 16)
        delta = q['building_count']-old.get(q['id'], 0)
        s.text(930, yy+2, str(q['building_count'])+(f' ({delta:+d})' if delta else ''), 16, '#3b555a', 'bold', 'end')
    s.text(560, 2160, 'Всего: '+str(d['metrics']['building_count'])+'  (в v13: '+str(d['comparison']['v13']['building_count'])+')',
           17, '#3b555a', 'bold')
    s.text(985, 1842, 'МАРШРУТЫ НА БУСИКЕ', 19, '#3b555a', 'bold')
    names = {'BAD_CENTER': 'центр района', 'CLOCK_SQUARE': 'площадь', 'ELITE_GATE': 'элитка', 'B05': 'B05 промзона',
             'BEACH_PARK_ENTRY': 'пляжная парковка', 'P03': 'P03 аптека', 'ELITE_MARINA': 'пристань', 'P05': 'P05 мастерская'}
    pairs = [('B01', 'P03'), ('B01', 'BAD_CENTER'), ('B01', 'CLOCK_SQUARE'), ('B02', 'CLOCK_SQUARE'), ('BAD_CENTER', 'CLOCK_SQUARE'),
             ('CLOCK_SQUARE', 'ELITE_GATE'), ('BAD_CENTER', 'B05'), ('CLOCK_SQUARE', 'BEACH_PARK_ENTRY'), ('ELITE_GATE', 'ELITE_MARINA'),
             ('CLOCK_SQUARE', 'P05')]
    for i, (a, b) in enumerate(pairs):
        r = next(r for r in d['metrics']['routes'] if r['from_id'] == a and r['to_id'] == b)
        src = {'BAD_CENTER': 'Центр района', 'CLOCK_SQUARE': 'Площадь', 'ELITE_GATE': 'Элитка'}.get(a, a)
        s.text(985, 1872+i*30, src+' → '+names[b], 16)
        s.text(1390, 1872+i*30, f'{r["length_m"]:.0f} м', 16, '#3b555a', 'bold', 'end')
    s.text(1450, 1842, 'НОВОЕ НА СХЕМЕ', 19, '#3b555a', 'bold')
    items = [('tower', 'Башни-близнецы — 20 этажей'), ('midrise', 'Дома 5–7 этажей у площади'), ('lowhouse', 'Низкие дома 2–3 этажа'),
             ('fountain', 'Площадь, фонтан с памятником'), ('pier', 'Пристань: пирс и понтоны'), ('yacht', 'Яхта'),
             ('motorboat', 'Катер'), ('breakwater', 'Мол с огоньком'), ('rocks', 'Камни на мысах бухты'),
             ('region', 'Изменено в v14 (1–4)')]
    for i, (kind, label) in enumerate(items):
        yy = 1868+i*28
        swatch(s, kind, 1453, yy)
        s.text(1493, yy+3, label, 16)
    s.text(1905, 1842, 'ИЗМЕНЕНИЯ v14 (только 1–4)', 19, '#3b555a', 'bold')
    st = d['old_town_statistics']
    mar, bay = d['marina'], d['bay']
    kinds = Counter(b['kind'] for b in mar['boats'])
    for i, text in enumerate(['1 Долина: убраны ночной клуб и боулинг;',
                              '   казино с парковкой осталось.',
                              f'2 Пристань элитки: пирс, {kinds["yacht"]} яхты, {kinds["motorboat"]} катера, мол.',
                              f'3 Бухта у парковки: {bay["depth_m"]:.0f} м вглубь, песок вокруг.',
                              f'4 Старый город: 2 башни по {st["tower_floors"]} эт.,',
                              f'   площадь {st["square_area_m2"]:,} м² с фонтаном'.replace(',', ' '),
                              '   и памятником; вокруг 5–7 эт., дальше 2–3.',
                              'Остальная карта — как в v13 (проверено).',
                              'Сверка с картинкой v23 — в отчёте;',
                              'переносов нет: см. вопросы Феде.']):
        s.text(1905, 1872+i*30, text, 15)
    checks = d['validation']['checks']
    s.text(75, 2262, f'Проверки: {sum(c["passed"] for c in checks)} / {len(checks)} — охрана областей против v13, долина, пристань, '
                     'бухта, старый город, маршруты, связность.', 16, '#607371')
    s.text(75, 2290, 'Схема ArtSource в метрах, вне импорта Unity. Субъективное качество и движение требуют проверки в игре.', 15, '#74827c')


def render(d):
    s = m.SVG()
    s.rect(0, 0, 2400, 2400, BG)
    s.text(75, 65, 'VOLUNTEERS ONLY   /   R01 — v14', 34, '#273c42', 'bold')
    s.text(75, 99, 'Без клуба и боулинга · пристань элитки · бухта у парковки · старый город: две башни и площадь с фонтаном · 06.10.2026',
           19, '#627372')
    visible = d['boundary']['polygon_m']+by_id(d['water'])['SEA']['polygon_m']
    lo = [min(p[k] for p in visible) for k in (0, 1)]
    hi = [max(p[k] for p in visible) for k in (0, 1)]
    scale = min(2130/(hi[0]-lo[0]), 1510/(hi[1]-lo[1]))
    left, top = 95+(2130-(hi[0]-lo[0])*scale)/2, 160

    def xy(p):
        return [left+(p[0]-lo[0])*scale, top+(hi[1]-p[1])*scale]
    count, overlaps = draw_map(d, s, xy, scale, 1, (45, 120, 2355, 1730), 'full')
    s.line([[2280, 235], [2280, 170]], '#3c5358', 2)
    s.poly([[2280, 155], [2271, 176], [2289, 176]], '#3c5358')
    s.text(2280, 140, 'С', 20, '#3c5358', 'bold', 'middle')
    s.line([[85, 1745], [85+100*scale, 1745]], '#3c5358', 3)
    for dist in (0, 50, 100):
        x = 85+dist*scale
        s.line([[x, 1738], [x, 1752]], '#3c5358', 1.3)
        s.text(x, 1774, str(dist)+' м', 13, '#4c6265', 'normal', 'middle')
    s.text(2340, 1770, 'Размер суши: '+' × '.join(f'{z:.0f}' for z in d['metrics']['extent_m'])+' м', 16, '#4c6265', 'normal', 'end')
    legend_full(d, s, scale)
    d['render_statistics'] = dict(canvas_px=[2400, 2400], scale_px_per_m=round(scale, 4), label_count=count, overlapping_label_pairs=overlaps)
    return s.finish()


def render_crop(d, view):
    title, (x0, y0, x1, y1) = CROPS[view]
    bw, bh = x1-x0, y1-y0
    scale = min(2280/bw, 2120/bh)
    width, height = round(bw*scale+120), round(bh*scale+280)
    top = 178
    s = m.SVG()
    s.parts[0] = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    s.rect(0, 0, width, height, BG)

    def xy(p):
        return [60+(p[0]-x0)*scale, top+(y1-p[1])*scale]
    count, overlaps = draw_map(d, s, xy, scale, 1.6, (50, top+5, width-50, height-105), view)
    s.rect(0, 0, width, top-6, BG)
    s.rect(0, height-100, width, 100, BG)
    s.rect(0, 0, 58, height, BG)
    s.rect(width-58, 0, 58, height, BG)
    s.line([[58, top-2], [width-58, top-2], [width-58, height-102], [58, height-102], [58, top-2]], '#9aa49a', 1.2)
    lx, ly = 60, 130
    for kind, label in CROP_LEGEND[view]:
        step = 26+12+len(label)*15*.55+34
        if lx+step > width-60:
            lx, ly = 60, ly+28
        swatch(s, kind, lx, ly)
        s.text(lx+36, ly+2, label, 15, '#3b4e51')
        lx += step
    s.text(60, 55, 'R01 — v14 · '+title, 30, '#273c42', 'bold')
    s.text(60, 92, f'Фрагмент x {x0}–{x1} м, y {y0}–{y1} м · {scale:.2f} px/м · названия на русском', 17, '#627372')
    bar = 25 if bw < 450 else 50
    s.line([[70, height-55], [70+bar*2*scale, height-55]], '#3c5358', 3)
    for dist in (0, bar, 2*bar):
        x = 70+dist*scale
        s.line([[x, height-62], [x, height-48]], '#3c5358', 1.3)
        s.text(x, height-25, str(dist)+' м', 14, '#4c6265', 'normal', 'middle')
    s.line([[width-90, 98], [width-90, 40]], '#3c5358', 2)
    s.poly([[width-90, 28], [width-99, 48], [width-81, 48]], '#3c5358')
    s.text(width-120, 52, 'С', 20, '#3c5358', 'bold', 'middle')
    s.text(width-70, height-40, 'Схема на согласование Феде; Unity — только после «ок».', 15, '#74827c', 'normal', 'end')
    d['render_statistics'].setdefault('crops', {})[view] = dict(canvas_px=[width, height], scale_px_per_m=round(scale, 3),
                                                                 label_count=count, overlapping_label_pairs=overlaps)
    return s.finish(), (width, height)


def report(d):
    met, st, mar, bay = d['metrics'], d['old_town_statistics'], d['marina'], d['bay']
    old = d['comparison']['v13']
    counts = met['building_counts_by_district']
    lengths = {(r['from_id'], r['to_id']): r['length_m'] for r in met['routes']}
    checks = d['validation']['checks']
    kinds = Counter(b['kind'] for b in mar['boats'])
    al = d['v23_alignment']
    near = [r for r in st['houses_by_distance_from_towers'] if r['kind'] == 'midrise']
    quay = by_id(d['roads'])['MARINA_QUAY']['length_m']

    def num(v):
        return f'{v:,.0f}'.replace(',', ' ')
    lines = [
        '# R01 v14 — без клуба и боулинга, пристань элитки, бухта у парковки, старый город с башнями и площадью',
        '',
        'Правки Феди 06.10.2026 голосом, картинки REF_FEDYA_v14_map_v23.png («примерная карта») и REF_FEDYA_v14_old_town_square.png. '
        'Схема на «ок» Феди; Unity — после.',
        f'Суша {met["extent_m"][0]:.1f} × {met["extent_m"][1]:.1f} м, физических зданий {met["building_count"]} (в v13 {old["building_count"]}).',
        '',
        '## Правило Феди: меняем только названные куски',
        'Всё вне областей ниже побайтно как в v13 — это проверка «охрана областей» (сравнение каждой записи v13/v14 и деревьев). '
        'На общей карте области обведены оранжевым пунктиром с номерами 1–4.',
        '',
        '| № | Область | Где (м) |',
        '|---|---|---|',
    ]
    for rid, label, kind, geo in REGIONS:
        where = f'x {geo[0]}–{geo[2]}, y {geo[1]}–{geo[3]}' if kind == 'bbox' else 'контур района old_town (не менялся)'
        lines.append(f'| {REGION_TAGS[rid]} | {label} | {where} |')
    lines += [
        '',
        '## 1. Малая долина',
        '- Ночной клуб и боулинг/аркада убраны вместе с подъездами; хвост дороги VALLEY_BRANCH к боулингу укорочен до парковки казино.',
        '- Казино 3 этажа, его парковка на 8 бусиков и вилла B06 — без изменений. На месте клуба и боулинга газон.',
        '',
        '## 2. Пристань элитки',
        f'- У разворота «Пляж: въезд из элитки»: проезд по песку {quay:.0f} м к площадке причала, точка ELITE_MARINA. '
        f'Бусик от въезда в элитку до пристани — {lengths["ELITE_GATE", "ELITE_MARINA"]:.0f} м.',
        f'- Пирс 4 × {mar["pier"]["length_m"]:.0f} м с Т-образной головой, 3 понтона, {len(mar["berths"])} мест: '
        f'{kinds["yacht"]} яхты (15–20 м) и {kinds["motorboat"]} катера; каменный мол с огоньком прикрывает гавань с севера и востока.',
        '- Новых въездов на пляж нет: проезд к пристани — продолжение дороги элитки внутри песка.',
        '',
        '## 3. Бухта напротив пляжной парковки',
        f'- Берег уходит вглубь на {bay["depth_m"]:.0f} м, устье {bay["mouth_width_m"]:.0f} м, {num(bay["water_area_m2"])} м² песка '
        'стали водой; на мысах камни.',
        f'- Песок обходит бухту: в вершине {bay["sand_at_apex_m"]:.0f} м, вне бухты пляж по-прежнему 55 м; дюна не тронута.',
        '- Пляжная тропа в бухте идёт по песку ближе к дюне; три тропинки с парковки кончаются на ней (их начало как в v13).',
        '',
        '## 4. Старый город (вторая картинка Феди; прежние правки по старому городу отменены)',
        f'- На севере, лицом к району подворотен, две башни-близнеца по {st["tower_floors"]} этажей (22 × 22 м, между ними '
        f'{st["tower_gap_m"]:.0f} м прохода).',
        f'- Перед ними большая площадь {num(st["square_area_m2"])} м² с фонтаном, на фонтане памятник; по краю липы, две клумбы.',
        '- Ближе к башням дома выше: ' + ', '.join(f'{r["floors"]} эт. ({r["distance_m"]} м)' for r in near) +
        f'; дальше {st["low_house_count"]} прежних низких домов 2–3 эт. (все дальше 110 м от башен).',
        '- Сквозные улицы, точка CLOCK_SQUARE (угол площади), канал с перилами, полиция P10 и её стоянка — как в v13.',
        '- Убраны две одиночные башни 14 и 16 эт. и два низких дома у площади; мастерская P05 перенесена в ЮВ угол (на место башни).',
        '',
        '## 5. Сверка с картинкой v23',
        f'Картинка привязана к метрам по {al["anchor_count"]} общим объектам (медианная ошибка {al["residual_median_m"]} м). '
        'Совпадают: церковь, водонапорная башня, ларёк-магазин, АЗС, 24 часа, B04, B06, B05 и вся промзона, казино, элитка, '
        'болото, озеро, холм, ЖД, пляжная парковка, оба въезда на пляж.',
        '',
        '| v23 | Расхождение | Решение |',
        '|---|---|---|',
    ]
    for o in al['objects']:
        if o['decision'] in ('match', 'replaced'):
            continue
        dist = f'{o["distance_m"]:.0f} м' if 'distance_m' in o else 'нет в v13'
        lines.append(f'| {o["label_ru"]} | {dist} | {o["decision_ru"]}. {o["note_ru"]} |')
    lines += ['', '| Маршрут на бусике | м |', '|---|---:|']
    for a, b in [('B01', 'P03'), ('BAD_CENTER', 'CLOCK_SQUARE'), ('CLOCK_SQUARE', 'ELITE_GATE'), ('ELITE_GATE', 'ELITE_MARINA'),
                 ('CLOCK_SQUARE', 'P05'), ('CLOCK_SQUARE', 'BEACH_PARK_ENTRY')]:
        lines.append(f'| {a} → {b} | {lengths[a, b]:.1f} |')
    lines += [
        '',
        f'Проверки: {sum(c["passed"] for c in checks)}/{len(checks)} пройдены ({d["validation"]["v13_suite_kept"]} из набора v13 '
        f'и {d["validation"]["v14_added"]} новых; 7 проверок v13 заменены, потому что v14 нарочно меняет их предпосылку). '
        'Районные здания: ' + ', '.join(f'{q["name_ru"]} {counts.get(q["id"], 0)}' for q in d['districts'])+'.',
        'Вопросы Феде: 1) B02: по канону это хижина в переходе, а на v23 — «Хижина деда» в хуторе; объединять базу с домом деда? '
        '2) Вагон на v23 ближе к берегу — двигать его вместе с аптекой и дедом? 3) Район подворотен, хутор (одно поле, пруд, '
        'колодец), островок «Скала», лес без песка — назови район, если переделывать. 4) Часы площади повесить на башню?',
        'Файлы: MAP_PLAN_R01_v14.json/.svg/.png, кропы _crop_old_town, _crop_valley_beach, _crop_elite_marina. '
        'Дрессинг, look и полиция v14 — после «ок».',
    ]
    assert len(lines) <= 80, len(lines)
    return '\n'.join(lines)+'\n'


def main():
    before = hashes()
    d = seed()
    analyse(d)
    old_town_statistics(d)
    svg = render(d)
    ET.fromstring(svg)
    (ROOT/(STEM+'.svg')).write_text(svg, encoding='utf-8')
    v13.to_png(svg, ROOT/(STEM+'.png'), (2400, 2400))
    for view in CROPS:
        crop, size = render_crop(d, view)
        ET.fromstring(crop)
        v13.to_png(crop, ROOT/f'{STEM}_crop_{view}.png', size)
    (ROOT/(STEM+'.json')).write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    (ROOT/(STEM+'_REPORT.md')).write_text(report(d), encoding='utf-8')
    assert hashes() == before, 'A previous deliverable changed'
    checks = d['validation']['checks']
    print(json.dumps(dict(passed=d['validation']['passed'], checks=f'{sum(c["passed"] for c in checks)}/{len(checks)}',
        extent_m=d['metrics']['extent_m'], building_count=d['metrics']['building_count'],
        by_district=d['metrics']['building_counts_by_district'], report_lines=len(report(d).splitlines()),
        render=d['render_statistics']), ensure_ascii=False))


if __name__ == '__main__':
    main()
