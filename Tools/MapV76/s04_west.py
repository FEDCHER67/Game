"""Step 4 (west): district layouts Hamlet (02), Forest (01), Quiet Valley (08) -> Data/v01/districts/*_v76.json.

Sources: Hamlet = Working/Reviews/Hamlet_2026-10-14/HAMLET_LAYOUT_v04.json as drawn by plan v05 (build_hutor_v05.py:
same objects, no wires, no drainage line, no terrain blobs); Forest / Quiet Valley = World_v11/WORLD_MAP_v11.json
(districts 01, 08) + handoff v02 §8.1 / §8.8. v11 metres -> v76: warp_m (build_world_v76.py, verbatim) then post_shift.
"""
import math
import os

import json
import numpy as np
from PIL import Image, ImageDraw

from common import ROOT, MAP_PREVIEW, WORK, post, rnd2, save_json

GROW_X, GROW_Y = 270.0, 85.0


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def warp_m(x, y):                                                     # build_world_v76.py, verbatim
    """Метры мира v22 -> v24."""
    if y >= 838:
        y2 = y + GROW_Y + 10
    else:
        y2 = None
    sy = r(y, 505, 575 - 35 * r(x, 880, 940))
    rn = r(x, 520, 545)
    dx = (1 - sy) * (70 + 70 * r(x, 575, 615)) + sy * (70 * (1 - rn) + rn * (110 + 140 * r(x, 880, 940) + 20 * r(x, 1088, 1110)))
    dy = sy * rn * (75 - 30 * r(x, 880, 940))
    return x + dx, (y2 if y2 is not None else y + dy)


def V(p):
    return rnd2(post(warp_m(p[0], p[1])))


def Vs(pts):
    return [V(p) for p in pts]


def ccw(poly):
    a = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))
    return poly if a > 0 else poly[::-1]


def rect(c, size, rot):
    w, d = size[0] / 2, size[1] / 2
    ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return [(c[0] + x * ca - y * sa, c[1] + x * sa + y * ca) for x, y in ((-w, -d), (w, -d), (w, d), (-w, d))]


FACE = {'east': 0, 'north': 90, 'west': 180, 'south': 270}

# house_type -> walls / roof (handoff v02 §8.2: доски D-3 (SK5a), брёвна B-7 (SK5b), окна Facade_Hamlet_wood, шифер S-4; кирпич — редкие акценты)
HOUSE_MAT = {'old_log': 'logs_SK5b', 'log': 'logs_SK5b', 'plank': 'boards_SK5a', 'board': 'boards_SK5a', 'wood_tin': 'boards_SK5a', 'brick': 'brick_SK3a'}


def roof_of(text):
    t = (text or '').lower()
    if 'slate' in t or 'шифер' in t or 'asbestos' in t:
        return 'roof_wavy_slate', 'slate'
    if 'tile' in t:
        return 'roof_tile_SK4a', 'tile'
    if 'metal' in t or 'tin' in t or 'sheet' in t:
        return 'roof_profsheet_SK4c', 'metal'
    return 'roof_wavy_slate', 'slate'


def hamlet():
    L = json.load(open(os.path.join(ROOT, 'Working', 'Reviews', 'Hamlet_2026-10-14', 'HAMLET_LAYOUT_v04.json'), encoding='utf-8'))
    objs = L['objects']
    B, P, Z = [], [], []
    BUILD = {'house', 'church', 'grandfather_base', 'shed', 'chicken_coop', 'pig_shelter', 'hay_shelter', 'water_tower', 'bus_stop'}
    ZONE = {'cultivated_field', 'vegetable_garden', 'open_working_grass', 'overgrown_beds', 'mud_patch', 'wheel_rut', 'dung_patch',
            'village_square', 'manoeuvring_apron', 'van_loading_pad', 'cemetery', 'orchard', 'pond', 'small_pig_pen', 'pedestrian_path',
            'fishing_platform', 'flower_strip'}
    for o in objs:
        k = o['kind']
        poly = o.get('polygon_m') or (rect(o['centre_m'], o['size_m'], o.get('rotation_deg') or 0) if o.get('size_m') and o.get('centre_m') else None)
        rot = o.get('rotation_deg') or 0
        if k in BUILD and poly:
            if k == 'house':
                ht = (o.get('house_type') or '').lower()
                walls = next((v for kk, v in HOUSE_MAT.items() if kk in ht), 'boards_SK5a')
                rmat, cap = roof_of(o.get('roof_material'))
                ent = [{'pos': V(o['door_m']), 'facing_deg': (FACE.get(o.get('front_face'), 270) + rot) % 360, 'kind': 'door', 'w_m': 1.0}] if o.get('door_m') else []
                B.append({'id': o['id'], 'kind': 'house', 'footprint': ccw(Vs(poly)), 'floors': o.get('floors', 1), 'floor_h_m': 2.8, 'height_m': 3.0,
                          'roof': {'type': 'gable', 'material': rmat, 'ridge_axis_deg': rot, 'ridge_h_m': 2.4, 'overhang_m': 0.4},
                          'walls': walls, 'tint': None, 'entrances': ent, 'facade_kit': 'hamlet',
                          'sockets': {'balconies': 'none', 'windows': True, 'shutters': True, 'porch_roof': True, 'chimney': True, 'gutter': True,
                                      'fire_escape': False, 'ac_units': 0, 'water_tank': False, 'awning': False, 'ridge_cap': cap},
                          'collider': 'full_roof', 'house_type': o.get('house_type'), 'abandoned': '19' in o['id'],
                          'notes': '%s; roof: %s; owner: %s' % (o.get('notes', ''), o.get('roof_material'), o.get('owner'))})
            else:
                spec = {'church': ('church', 'boards_SK5a', 'gable', 'roof_tile_SK4a', 'tile', 7.0, 5.0),
                        'grandfather_base': ('hut_base2', 'logs_SK5b', 'gable', 'roof_wavy_slate', 'slate', 3.0, 2.4),
                        'shed': ('shed', 'boards_SK5a', 'shed', 'roof_profsheet_SK4c', None, 2.4, 0.6),
                        'chicken_coop': ('coop', 'boards_SK5a', 'shed', 'roof_profsheet_SK4c', None, 1.8, 0.4),
                        'pig_shelter': ('pig_shelter', 'boards_SK5a', 'shed', 'roof_wavy_slate', None, 1.6, 0.4),
                        'hay_shelter': ('hay_shelter', 'logs_SK5b', 'gable', 'roof_profsheet_SK4c', 'metal', 4.0, 1.5),
                        'water_tower': ('water_tower', 'brick_SK3a', 'pyramid', 'roof_profsheet_SK4c', None, 12.0, 1.5),
                        'bus_stop': ('bus_stop', 'concrete_SK3c', 'shed', 'roof_profsheet_SK4c', None, 2.4, 0.2)}[k]
                hh = o.get('height_m') or spec[5]
                B.append({'id': o['id'], 'kind': spec[0], 'footprint': ccw(Vs(poly)), 'floors': 1, 'floor_h_m': hh, 'height_m': hh,
                          'roof': {'type': spec[2], 'material': spec[3], 'ridge_axis_deg': rot, 'ridge_h_m': spec[6], 'overhang_m': 0.3},
                          'walls': spec[1], 'tint': None, 'entrances': [], 'facade_kit': 'hamlet' if k in ('church', 'grandfather_base') else 'none',
                          'sockets': {'balconies': 'none', 'windows': k in ('church', 'grandfather_base'), 'ridge_cap': spec[4]},
                          'collider': 'full_roof', 'base': '2' if k == 'grandfather_base' else None,
                          'notes': (o.get('notes') or '') + ('' if o.get('height_m') else ' | height not in source, default by kind')})
        elif k in ZONE and poly:
            surf = {'cultivated_field': 'field_plowed', 'vegetable_garden': 'dirt_SK1b', 'village_square': 'dirt_SK1b', 'van_loading_pad': 'gravel_SK1d',
                    'manoeuvring_apron': 'gravel_SK1d', 'mud_patch': 'dirt_SK1b', 'wheel_rut': 'dirt_SK1b', 'dung_patch': 'dirt_SK1b',
                    'pond': 'water', 'fishing_platform': 'boards_SK5a', 'pedestrian_path': 'dirt_SK1b'}.get(k, 'lawn')
            Z.append({'id': o['id'], 'kind': k, 'poly': Vs(poly), 'surface': surf, 'notes': o.get('notes')})
        elif o.get('centre_m'):
            if k in ('chicken_spawn_marker', 'pig_spawn_marker', 'npc_gathering_marker'):
                kind = k
            else:
                kind = k
            P.append({'id': o['id'], 'kind': kind, 'pos': V(o['centre_m']), 'rot_deg': rot,
                      'size': (o.get('size_m') or [o.get('crown_diameter_m', 1), o.get('crown_diameter_m', 1)])[:2] + [o.get('height_m') or 0],
                      'grip_anchor': k in ('bench', 'pole_lamp', 'wooden_utility_pole', 'outdoor_table', 'gathering_table'),
                      **({'tree_type': o.get('tree_type')} if k == 'tree' else {})})
    for s in L['streets']:
        Z.append({'id': s['id'], 'kind': 'street', 'polyline': Vs(s['polyline_m']), 'width_m': s.get('width_m'), 'road_class': s.get('road_class'),
                  'surface': 'dirt_SK1b', 'notes': 'two ruts with grass in the middle, puddles (v02 §5)'})
    return {'district': 'hamlet', 'sources': ['Working/Reviews/Hamlet_2026-10-14/HAMLET_LAYOUT_v04.json', 'ArtSource/References/Map/World_v75/build_hutor_v05.py',
                                              'docs/specs/HAMLET_SPEC_2026-10-18_v01.md'],
            'transform': 'v11 m -> warp_m (build_world_v76.py) -> post_shift_v76.shift_m (net +70, 0)', 'pad_height_m': None,
            'buildings': B, 'props': P, 'zones': Z,
            'notes': 'Plan v05 = v04 objects without wires/drainage/terrain blobs; utility poles kept as props (v05 still draws poles, wires removed). '
                     'Terrain bumps +1.5..+3.8 m / dip -1.4 m are in terrain (HAMLET_LAYOUT terrain[]), not here. '
                     'Grandpa yard dressing = Fedya scene i09 (barrel, paint cans, red rocking chair) — exact layout OPEN (handoff §16).'}


def v11_buildings(dist):
    W11 = json.load(open(os.path.join(ROOT, 'ArtSource', 'References', 'Map', 'World_v11', 'WORLD_MAP_v11.json'), encoding='utf-8'))
    return [b for b in W11['buildings'] if str(b['district']) == dist], [s for s in W11['structures'] if str(s.get('district')) == dist]


def forest():
    bs, ss = v11_buildings('01')
    B, Z = [], []
    for b in bs:
        if b['id'] == '01_B02':
            continue                                                  # duplicate outline inside the wagon (same object)
        wagon = b['kind'] == 'old_railway_wagon'
        B.append({'id': b['id'], 'kind': 'rail_wagon_base1' if wagon else b['kind'], 'footprint': ccw(Vs(b['footprint_m'])), 'floors': 1,
                  'floor_h_m': b['height_m'], 'height_m': b['height_m'],
                  'roof': {'type': 'flat' if wagon else 'shed', 'material': 'metal_rusty', 'ridge_h_m': 0.4 if wagon else 0.3, 'overhang_m': 0.1},
                  'walls': 'metal_rusty' if wagon else 'boards_SK5a', 'tint': None, 'entrances': [], 'facade_kit': 'none',
                  'sockets': {'balconies': 'none', 'windows': wagon, 'ridge_cap': None}, 'collider': 'full_roof', 'base': '1' if wagon else None,
                  'notes': b.get('name', '') + (' | v02 §8.1: ~24 x 3.2 m at the end of a dead-end track; clearing, cold campfire' if wagon else '')})
    for s in ss:
        if 'polyline_m' in s:
            Z.append({'id': s['id'], 'kind': 'railway', 'polyline': Vs(s['polyline_m']), 'surface': 'gravel_SK1d', 'notes': s.get('note')})
    return {'district': 'forest', 'sources': ['ArtSource/References/Map/World_v11/WORLD_MAP_v11.json (district 01)', 'handoff v02 §8.1'],
            'transform': 'v11 m -> warp_m -> post_shift (net +70, 0)', 'pad_height_m': None, 'buildings': B, 'props': [], 'zones': Z,
            'notes': 'Rail starts at the map edge with a rock-blocked tunnel mouth; swamp/lake/trees come from water_v76.json and vegetation masks. '
                     'v11 gentle_hill_contour structures ignored (relief is in terrain_v76).'}


def valley():
    bs, ss = v11_buildings('08')
    B, Z = [], []
    for b in bs:
        lab = b['kind'] == 'lab_final_base'
        B.append({'id': b['id'], 'kind': b['kind'], 'footprint': ccw(Vs(b['footprint_m'])), 'floors': b['floors'], 'floor_h_m': 3.2, 'height_m': b['height_m'],
                  'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.6},
                  'walls': 'concrete_SK3c' if lab else 'stucco_SK3b', 'tint': None,
                  'entrances': [], 'facade_kit': 'none', 'sockets': {'balconies': 'none', 'windows': True, 'ridge_cap': None}, 'collider': 'full_roof',
                  'base': '5' if lab else None,
                  'notes': b.get('name', '') + (' | v02 §8.8: final lab, best base (concrete, glass, OR, organ fridges, van garage)' if lab else ' | second casino / Casino Island OPEN')})
    for s in ss:
        if 'polygon_m' in s and s['kind'] != 'open_lawn':
            Z.append({'id': s['id'], 'kind': s['kind'], 'poly': Vs(s['polygon_m']),
                      'surface': {'paved_forecourt': 'concrete_SK3c', 'parking': 'asphalt_A5d12', 'rock_waterfall': 'rock'}.get(s['kind'], 'lawn'),
                      'notes': 'v02 §8.8: no waterfall with pond inside the valley' if s['kind'] == 'rock_waterfall' else
                               ('low perimeter, open north entry and beach gate, no checkpoints/barriers' if 'fence' in s['kind'] else None)})
    return {'district': 'quiet_valley', 'sources': ['ArtSource/References/Map/World_v11/WORLD_MAP_v11.json (district 08)', 'handoff v02 §8.8'],
            'transform': 'v11 m -> warp_m -> post_shift', 'pad_height_m': None, 'buildings': B, 'props': [], 'zones': Z,
            'notes': 'Lab "top right", casino at the south exit to the small beach (canon). v11 rock_waterfall kept only as rocks: v02 forbids the in-valley waterfall pond.'}


def check(d, box, name):
    im = Image.open(MAP_PREVIEW).convert('RGB')
    dr = ImageDraw.Draw(im)
    for b in d['buildings']:
        dr.polygon([(x, 950 - y) for x, y in b['footprint']], outline=(255, 0, 0))
    for p in d['props']:
        x, y = p['pos']
        dr.point((x, 950 - y), fill=(255, 0, 255))
    x0, y0, x1, y1 = box
    im.crop((x0, 950 - y1, x1, 950 - y0)).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.NEAREST).save(os.path.join(WORK, 'check_%s.png' % name))


def main():
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Assets', 'OnlyVolunteers', 'Map', 'W76Build', 'Data', 'v01', 'districts'), exist_ok=True)
    for name, fn, box in (('hamlet', hamlet, (190, 370, 460, 610)), ('forest', forest, (180, 60, 430, 320)), ('quiet_valley', valley, (490, 110, 660, 300))):
        d = fn()
        save_json('districts/%s_v76.json' % name, d)
        check(d, box, name)
        print(name, len(d['buildings']), 'buildings', len(d['props']), 'props', len(d['zones']), 'zones')


if __name__ == '__main__':
    main()
