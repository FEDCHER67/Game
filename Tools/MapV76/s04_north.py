"""Step 4a: district layouts — Rough (04), International Construction (03), Industrial Port (06), Tramduro (10).

Output: Data/v01/districts/{rough,construction,port,tramduro}_v76.json (schema: DISTRICT_SCHEMA.md),
check overlays out/check_<district>.png (footprints in red on the v76 render).
Placement on v76 is fitted to what the 2D map v76 draws (nothing re-invented); fits are reported in `transform`.
"""
import json
import math
import os

from PIL import Image, ImageDraw

from common import ROOT, WORK, MAP_PREVIEW, post, rnd2, save_json

REF = os.path.join(ROOT, 'ArtSource', 'References', 'Map')
ROUGH_SRC = os.path.join(REF, 'World_v11', 'Districts', 'D04_Rough_District_layout_v45.json')
PORT_SRC = os.path.join(REF, 'World_v11', 'Districts', 'D06_Industrial_Port_layout_v03.json')
WORLD11 = os.path.join(REF, 'World_v11', 'WORLD_MAP_v11.json')
TRAM_SRC = os.path.join(ROOT, 'Working', 'Reviews', 'Tramduro_2026-10-14', 'TRAMDURO_LAYOUT_v06.json')
CONSTR_SRC = os.path.join(REF, 'Desktop_Map_sources_2026-10-18', 'Интернациональная стройка', 'build_stroyka_v10.py')
FLOOR_R = 2.8
FACING = {'E': 0, 'N': 90, 'W': 180, 'S': 270}


def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def rrect(c, w, d, ang):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    return [[c[0] + dx * ca - dy * sa, c[1] + dx * sa + dy * ca] for dx, dy in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]


def R(poly):
    return [rnd2(p) for p in poly]


def load(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


# ------------------------------------------------------------------ 04 Rough
ROUGH_ANCHOR = (667.0, 668.0)     # local (0, 0) = SW corner of the outer road; fitted on the v76 render (asphalt + houses), scale 1.0


def rough():
    d = load(ROUGH_SRC)
    ox, oy = ROUGH_ANCHOR
    W_ = lambda x, z: [round(x + ox, 2), round(z + oy, 2)]
    Wr = lambda r: [W_(r['x0'], r['z0']), W_(r['x1'], r['z0']), W_(r['x1'], r['z1']), W_(r['x0'], r['z1'])]
    parts = []
    for h in d['houses']:
        for k, p in enumerate(h['parts']):
            parts.append((h, k, p))
    blds = []
    for h, k, p in parts:
        bid = '04-%s%s' % (h['id'], 'abcdefgh'[k] if len(h['parts']) > 1 else '')
        ents = []
        for dr in d['doors']:
            x, z = dr['pos']
            on = (p['x0'] - 0.3 <= x <= p['x1'] + 0.3 and p['z0'] - 0.3 <= z <= p['z1'] + 0.3 and
                  (abs(x - p['x0']) < 0.3 or abs(x - p['x1']) < 0.3 or abs(z - p['z0']) < 0.3 or abs(z - p['z1']) < 0.3))
            if on:
                ents.append({'pos': W_(x, z), 'facing_deg': FACING[dr['side']], 'kind': 'podyezd', 'w_m': 1.2, 'benches': dr['benches'],
                             'canopy': 'FK_R_Entrance_Canopy', 'steps': 'FK_R_Entrance_Steps2|3', 'door': 'FK_R_IronDoor'})
        arches = []
        for a in d['arches']:
            r_ = a['rect']
            cx, cz = (r_['x0'] + r_['x1']) / 2, (r_['z0'] + r_['z1']) / 2
            if p['x0'] - 0.5 <= cx <= p['x1'] + 0.5 and p['z0'] - 0.5 <= cz <= p['z1'] + 0.5:
                ns = a['through'] == 'N-S'
                arches.append({'id': a['id'], 'rect': Wr(r_), 'through': a['through'], 'clear_w_m': 4.0, 'clear_h_m': 4.0})
                ents.append({'pos': W_(cx, cz), 'facing_deg': 90 if ns else 0, 'kind': 'arch', 'w_m': round(r_['w'] if ns else r_['d'], 2),
                             'through': a['through'], 'arch_id': a['id']})
        if h['id'] == 'H17' and k == 1:
            g = d['base_gate']
            ents.append({'pos': W_((g['x0'] + g['x1']) / 2, g['z0']), 'facing_deg': 270, 'kind': 'garage_gate', 'w_m': 3.8,
                         'note': 'base 3: van garage in the ground floor, iron gate 3.8 m'})
        blds.append({'id': bid, 'group': h['id'], 'name_ru': h.get('name'), 'kind': 'khrushchevka', 'footprint': Wr(p),
                     'floors': 5, 'floor_h_m': FLOOR_R, 'height_m': 5 * FLOOR_R + 0.5,
                     'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.6, 'kit_parapet': 'FK_R_Parapet_3m2', 'vents': 'FK_R_Roof_Vent'},
                     'walls': 'KH1b', 'tint': None, 'entrances': ents, 'arches': arches, 'facade_kit': 'rough',
                     'sockets': {'balconies': 'mixed', 'windows': True, 'window_frame': 'FK_R_Window_Frame', 'drainpipes': 'FK_R_Drainpipe_2m8',
                                 'fire_escape': False, 'ac_units': 0, 'water_tank': False, 'awning': False, 'ridge_cap': None,
                                 'balcony_pieces': ['FK_R_Balcony_Open', 'FK_R_Balcony_Glazed'], 'balcony_collider': 'solid, not walkable inside'},
                     'collider': 'full_roof',
                     'notes': 'all one grey KH1b, shabby (streaks, patched seams, rust under balconies, dark plinth); bay 3.2 m (kit rough_grid); no basements, no interiors; palisade ~4 m live grass + low fence on podyezd sides'})
    for i, g in enumerate(d['garages']):
        r_ = g['rect']
        cx, cz = (r_['x0'] + r_['x1']) / 2, (r_['z0'] + r_['z1']) / 2
        gp = {'S': (cx, r_['z0']), 'N': (cx, r_['z1']), 'E': (r_['x1'], cz), 'W': (r_['x0'], cz)}[g['gate']]
        blds.append({'id': '04-G%02d' % (i + 1), 'kind': 'garage', 'footprint': Wr(r_), 'floors': 1, 'floor_h_m': 2.6, 'height_m': 2.6,
                     'roof': {'type': 'flat', 'material': 'metal_rusty', 'parapet_h_m': 0.0}, 'walls': 'metal_rusty', 'tint': None,
                     'entrances': [{'pos': W_(*gp), 'facing_deg': FACING[g['gate']], 'kind': 'garage_gate', 'w_m': 2.6}],
                     'facade_kit': 'none', 'sockets': {'balconies': 'none', 'windows': False}, 'collider': 'full_roof',
                     'notes': 'rusty, peeling paint, ~14 of 58 with graffiti, a couple open with junk (legend); walls material: facade_corrugated_metal (handoff 3.1 "ржавый — гаражи")'})
    s = d['shop']
    blds.append({'id': '04-shop24', 'kind': 'shop', 'footprint': Wr(s), 'floors': 1, 'floor_h_m': 3.2, 'height_m': 3.6,
                 'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.4}, 'walls': None, 'tint': None,
                 'entrances': [], 'facade_kit': 'none', 'sockets': {'windows': True}, 'collider': 'full_roof',
                 'notes': '24 h shop ~20x10 m, drunks at the door, two kiosks next to it (legend); wall material and door side NOT given -> OPEN'})
    for i, b in enumerate(d['booths']):
        blds.append({'id': '04-transformer%d' % (i + 1), 'kind': 'transformer_booth', 'footprint': Wr(b), 'floors': 1, 'floor_h_m': 3.0, 'height_m': 3.0,
                     'roof': {'type': 'flat', 'material': 'roof_flat_SK4d'}, 'walls': 'brick_SK3a', 'tint': None, 'entrances': [],
                     'facade_kit': 'none', 'sockets': {}, 'collider': 'full_roof', 'notes': 'brick, "do not enter" sign (legend)'})
    c = d['club']
    ce = d['club_entrance']
    props, zones = [], []
    zones.append({'id': '04-club5', 'kind': 'club_in_ground_floor', 'poly': Wr(c), 'surface': None,
                  'entrance': {'pos': W_(*ce), 'facing_deg': 180, 'canopy': True, 'neon_heart_no_words': True},
                  'notes': 'club (притон 5) in the ground floor of the "lightning" block; smokers corner with bouncer and crowd'})
    zones.append({'id': '04-box', 'kind': 'football_box', 'poly': Wr(d['box']), 'surface': 'lawn',
                  'notes': '44.9 x 37.5 m, wooden board + tall chain-link, goals with torn nets, one wicket from the north (van enters), 2 floodlights, bench with gopniks, worn grass'})
    for p in d['playgrounds']:
        zones.append({'id': '04-play-' + p['name'], 'kind': 'playground', 'poly': Wr(p['rect']), 'surface': 'rubber', 'notes': 'swings, slide, sandbox, roundabout; neat rectangle with kerb'})
    for t in d['trash']:
        zones.append({'id': '04-trash-' + t['name'], 'kind': 'trash_section', 'poly': Wr(t['rect']), 'surface': 'concrete_SK3c', 'open': t.get('open'),
                      'notes': 'concrete, profiled sheet on 3 sides, 2 skip bins + 3 green bins'})
    zones.append({'id': '04-base-yard', 'kind': 'van_yard', 'poly': Wr(d['bus']), 'surface': 'asphalt_old_SK2a', 'notes': 'base 3 van spot 5.2 x 8.7 m'})
    for i, tr in enumerate(d['tracks']):
        zones.append({'id': '04-track%d' % i, 'kind': 'track', 'line': [W_(*q) for q in tr], 'surface': 'dirt_SK1b', 'width_m': [3.0, 5.0],
                      'notes': 'uneven grey ruts over faded dry grass (L02), ragged edges, gaps, puddles — NOT concrete; no lamps/trees on ruts'})
    zones.append({'id': '04-outer-road', 'kind': 'road', 'line': [W_(*q) for q in d['outer_road']], 'surface': 'asphalt_old_SK2a', 'width_m': 6.0, 'kerb': True})
    for i, e in enumerate(d['exits']):
        zones.append({'id': '04-exit%d' % i, 'kind': 'road', 'line': [W_(*q) for q in e], 'surface': 'asphalt_old_SK2a', 'width_m': 6.0, 'kerb': True})
    zones.append({'id': '04-fence', 'kind': 'fence', 'line': [W_(*q) for q in d['fence']], 'surface': None, 'notes': 'district edge per layout v45 (legend: tree band / blind fences = light boundary with Construction)'})
    zones.append({'id': '04-ground', 'kind': 'ground', 'poly': [W_(-10.3, -26), W_(353.9, -26), W_(353.9, 233.6), W_(-10.3, 233.6)], 'surface': 'worn_grass_L02',
                  'notes': 'flat (Y = pad), dry faded yellow-brown grass'})
    for i, t in enumerate(d['turniks']):
        (ax, az), (bx, bz) = t
        props.append({'id': '04-turnik%d' % i, 'kind': 'pull_up_bar', 'pos': W_((ax + bx) / 2, (az + bz) / 2), 'rot_deg': 0,
                      'size': [round(math.hypot(bx - ax, bz - az), 2), 0.1, 2.4], 'grip_anchor': True})
    for i, t in enumerate(d['trees']):
        props.append({'id': '04-tree%02d' % i, 'kind': 'tree_bare_crooked', 'pos': W_(*t), 'rot_deg': 0, 'size': [5, 5, 7], 'grip_anchor': False})
    for i, t in enumerate(d['lamps']):
        props.append({'id': '04-lamp%02d' % i, 'kind': 'street_lamp', 'pos': W_(*t), 'rot_deg': 0, 'size': [0.3, 0.3, 6], 'grip_anchor': True})
    for i, cr in enumerate(d['cars']):
        props.append({'id': '04-car%d' % i, 'kind': 'old_soviet_car', 'pos': W_(*cr['pos']), 'rot_deg': 0 if cr['along'] == 'W-E' else 90, 'size': [4.0, 1.6, 1.45], 'grip_anchor': False})
    nb = sum(e.get('benches', 0) for b in blds for e in b['entrances'])
    out = {'district': 'rough', 'sources': [os.path.relpath(ROUGH_SRC, ROOT), 'docs/specs/ROUGH_LEGEND_v45.md', 'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.4'],
           'transform': 'v76 = local v45 (x east, z north, origin SW outer-road corner) + (%.0f, %.0f), scale 1.0, fitted on the v76 render (outer asphalt U + 13 houses)' % ROUGH_ANCHOR,
           'pad_height_m': 5.0, 'lighting': 'overcast_fog', 'buildings': blds, 'props': props, 'zones': zones,
           'counts': {'khrushchevka_parts': len(parts), 'houses': len(d['houses']), 'podyezds': len(d['doors']), 'benches': nb, 'arches': len(d['arches']),
                      'garages': len(d['garages']), 'trees': len(d['trees']), 'lamps': len(d['lamps']), 'cars': len(d['cars'])}}
    return out


# ------------------------------------------------------------------ 03 Construction (build_stroyka_v10.py, 1 unit = 0.2 m, y down)
LC, SXY, G = (410.0, 393.0), (1.15, 0.95), (604.0, 418.0)
CONSTR_SHAPE_W = [(604 + (x - 564) * 0.82, y - 186) for x, y in [(482, 652), (500, 659), (545, 659), (585, 667), (617, 674), (640, 666), (650, 640), (642, 612),
                  (649, 586), (636, 562), (608, 550), (570, 547), (530, 552), (500, 561), (486, 581), (479, 616)]]


def cw(lx, ly):
    """D03 local unit -> world m (cluster centres spread by CONSTR_SXY about CONSTR_LC, as build_world_v76.relayout)."""
    return (G[0] + SXY[0] * (lx - LC[0]) / 5.0, G[1] - SXY[1] * (ly - LC[1]) / 5.0)


def cwc(lx, ly, cc):
    """Item of a cluster with local centre cc: the whole cluster is translated (relayout), items keep their spacing."""
    gx, gy = cw(*cc)
    return (gx + (lx - cc[0]) / 5.0, gy - (ly - cc[1]) / 5.0)


def c_rect(cx, cy, w, h, ang=0.0, cc=None):
    return R(rrect(cwc(cx, cy, cc) if cc else cw(cx, cy), w / 5.0, h / 5.0, -ang))


def construction():
    ns = {}
    src = open(CONSTR_SRC, encoding='utf-8').read()
    for name in ('BLOCKS', 'EAST_BLOCK', 'SERVICE_ROW', 'OFFICE', 'DORM', 'WORKSHOP', 'CRANE', 'GAP', 'GATE_MAIN', 'GATE_SHOP', 'GATE_EAST', 'CUTS'):
        i = src.index('\n%s = ' % name) + 1
        j = src.index('\n', i)
        while src[j + 1:j + 2] == ' ':
            j = src.index('\n', j + 1)
        exec(src[i:j], ns)
    step = 12 + ns['GAP']
    blds, props, zones = [], [], []

    def B(bid, kind, poly, floors, fh, roof, walls, notes, ents=(), height=None, kit='none'):
        blds.append({'id': bid, 'kind': kind, 'footprint': poly, 'floors': floors, 'floor_h_m': fh, 'height_m': height or floors * fh,
                     'roof': roof, 'walls': walls, 'tint': None, 'entrances': list(ents), 'facade_kit': kit, 'sockets': {'windows': True},
                     'collider': 'full_roof', 'notes': notes})
    flat = lambda m='roof_flat_SK4d': {'type': 'flat', 'material': m}
    CA = (282.0, 251.0)
    B('03-04-corpusA', 'concrete_frame', c_rect(269, 245, 198, 110, cc=CA), 5, 3.2, {'type': 'flat', 'material': 'concrete_SK3c', 'open_frame': True}, 'concrete_SK3c',
      '04 Building A: monolithic frame, 5 floors, slabs + columns, 2 stair/lift cores (x 220, 316 local), scaffold S and E, cargo hoist; walkable slabs')
    for x in (220, 316):
        B('03-04-core%d' % x, 'stair_lift_core', c_rect(x, 246, 24, 40, cc=CA), 5, 3.2, flat('concrete_SK3c'), 'concrete_SK3c', 'core of Building A', height=17.0)
    B('03-04-scaffold-S', 'scaffold', c_rect(275, 306, 210, 12, cc=CA), 5, 3.2, {'type': 'none'}, 'metal_painted_SK6a', 'scaffold along the south face')
    B('03-04-scaffold-E', 'scaffold', c_rect(374, 245, 12, 110, cc=CA), 5, 3.2, {'type': 'none'}, 'metal_painted_SK6a', 'scaffold along the east face')
    B('03-04-hoist', 'cargo_hoist', c_rect(387, 245, 14, 18, cc=CA), 5, 3.4, {'type': 'none'}, 'metal_painted_SK6a', 'cargo hoist')
    B('03-05-corpusB', 'foundation_slab', c_rect(255, 480, 170, 100), 1, 1.2, flat('concrete_SK3c'), 'concrete_SK3c',
      '05 Building B: foundation slab, first columns (3 rows done, rest rebar starters), formwork')
    c, a, w, h = ns['DORM']
    B('03-08-dorm', 'old_dormitory', c_rect(c[0], c[1], w, h, a), 4, 3.0, {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.5}, 'stucco_SK3b_v07',
      '08 migrants dormitory, old 4-storey; yard in front', ents=[{'pos': rnd2(cw(c[0] + x, c[1] + h / 2 + 4)), 'facing_deg': 270, 'kind': 'door', 'w_m': 1.4} for x in (-40, 40)])
    cols = ('#8FA9B8', '#C9D2D8', '#A9C0CC', '#8FA9B8', '#C8BFA8', '#9DB1BE', '#A47E62', '#C9D2D8', '#8FA9B8')
    k_ = 0
    for (x0, y0), n, ang, side in ns['BLOCKS']:
        cc = (x0 + (n * step - ns['GAP']) / 2.0, y0 + 15)
        for i in range(n):
            k_ += 1
            B('03-07-cabin%02d' % k_, 'block_container_2storey', c_rect(x0 + i * step + 6, y0 + 15, 12, 30, cc=cc), 2, 2.6, flat('metal_painted_SK6a'), 'metal_painted_SK6a',
              'block container 6 x 2.4 m, two storeys, ~1 m gaps, gallery %s + stair' % side)
            blds[-1]['tint'] = cols[(i * 7 + int(x0)) % len(cols)]
        L = n * step - ns['GAP']
        gy = 32 if side == 'S' else -2
        props.append({'id': '03-07-gallery-%d' % y0, 'kind': 'container_gallery', 'pos': rnd2(cwc(x0 + L / 2, y0 + gy, cc)), 'rot_deg': 0, 'size': [L / 5, 0.8, 2.6]})
        props.append({'id': '03-07-stair-%d' % y0, 'kind': 'container_stair', 'pos': rnd2(cwc(x0 + L + 5, y0 + (24 if side == 'S' else 6), cc)), 'rot_deg': 0, 'size': [1.8, 2.8, 2.6]})
    (x0, y0), n, ang = ns['EAST_BLOCK']
    cc = (x0 + 15, y0 + (n * step - ns['GAP']) / 2.0)
    for i in range(n):
        k_ += 1
        B('03-07-cabin%02d' % k_, 'block_container_2storey', c_rect(x0 + 15, y0 + i * step + 6, 30, 12, cc=cc), 2, 2.6, flat('metal_painted_SK6a'), 'metal_painted_SK6a',
          'two cabins across at the east fence')
    (x0, y0), parts, ang = ns['SERVICE_ROW']
    kk = 0
    cc = (x0 + (sum(m for _, m in parts) * step - ns['GAP']) / 2.0, y0 + 15)
    for col, m in parts:
        for i in range(m):
            B('03-07-service%d' % kk, 'canteen' if col == '#C8BFA8' else 'shower', c_rect(x0 + kk * step + 6, y0 + 15, 12, 30, cc=cc), 1, 2.6, flat('metal_painted_SK6a'),
              'metal_painted_SK6a', 'canteen (2) / shower (1) containers')
            blds[-1]['tint'] = col
            kk += 1
    (x0, y0), n, ang = ns['OFFICE']
    B('03-07-office', 'foreman_office', c_rect(x0 + 6, y0 + 15, 12, 30), 1, 2.6, flat('metal_painted_SK6a'), 'metal_painted_SK6a', 'foreman office at the east gate')
    B('03-03-guard', 'guard_booth', c_rect(468, 651, 24, 22), 1, 2.6, flat(), 'metal_painted_SK6a', 'guard booth at the main gate (+ wheel wash)')
    c, a, w, h = ns['WORKSHOP']
    B('03-01-workshop', 'van_workshop', c_rect(c[0], c[1], w, h), 1, 4.5, flat('roof_profsheet_SK4c'), 'cinder_SK3d',
      '01 van upgrade workshop: tyres, scrap metal, rusty body in front', ents=[{'pos': rnd2(cw(c[0] + x, c[1] + h / 2)), 'facing_deg': 270, 'kind': 'rollshutter', 'w_m': 5.6} for x in (-36, 0, 36)])
    B('03-02-fuel-canopy', 'fuel_canopy', c_rect(192, 781, 60, 34), 1, 4.5, flat('metal_painted_SK6a'), None, '02 small gas station canopy outside the fence (columns only). OPEN: outside CONSTR_CLIP, not drawn on 2D v76 — handoff keeps the AZS; position = D03 v10 mapped, check next to the main road')
    B('03-02-fuel-kiosk', 'kiosk', c_rect(243, 788, 26, 28), 1, 2.8, flat(), 'concrete_panel_SK3c', '02 gas station cash kiosk')
    B('03-03-transformer', 'transformer_booth', c_rect(151, 623, 22, 22), 1, 2.8, flat(), 'brick_SK3a', 'transformer substation')
    cr = ns['CRANE']
    props.append({'id': '03-06-crane', 'kind': 'tower_crane', 'pos': rnd2(cw(*cr)), 'rot_deg': 0, 'size': [3.2, 3.2, 40], 'note': 'jib reach = dashed circle on plan'})
    for i, p in enumerate(((475, 650), (487, 613), (651, 465), (622, 465), (250, 372))):
        props.append({'id': '03-misc%d' % i, 'kind': ['wheel_wash', 'skip_bin', 'skip_bin', 'bio_toilets_row', 'materials_store'][i], 'pos': rnd2(cw(*p)), 'rot_deg': 0, 'size': [6, 3, 2]})
    zones.append({'id': '03-fence', 'kind': 'fence', 'poly': R(CONSTR_SHAPE_W), 'surface': 'metal_painted_SK6a', 'height_m': 2.0,
                  'notes': 'one blue profiled-sheet fence ~2 m around everything (contour CONSTR_SHAPE_W of build_world_v76.py); open gates main ~19 m, workshop ~18 m, east ~18 m + 4 van cuts ~12 m; no barriers'})
    gates = [('main', ns['GATE_MAIN']), ('workshop', ns['GATE_SHOP']), ('east', ns['GATE_EAST'])] + [('cut%d' % i, c_) for i, c_ in enumerate(ns['CUTS'])]
    zones.append({'id': '03-gates', 'kind': 'gates', 'items': [{'name': n_, 'centre_local': list(c_[0]), 'centre_v76_estimate': rnd2(cw(*c_[0])), 'w_m': c_[1] / 5} for n_, c_ in gates],
                  'notes': 'v76 contour is not the D03 rectangle: snap each gate to the nearest point of the fence polygon; v76 gate to the main road at (600, 363) (build_world_v76 _gate)'})
    zones.append({'id': '03-ground', 'kind': 'ground', 'poly': R(CONSTR_SHAPE_W), 'surface': 'dirt_SK1b', 'notes': 'no concrete roads: dirt, ruts, puddles'})
    return {'district': 'construction', 'sources': [os.path.relpath(CONSTR_SRC, ROOT), 'Легенда_v08.txt', 'build_world_v76.py CONSTR_*', 'handoff v02 §8.3'],
            'transform': 'v76 = (604 + 1.15 (lx - 410) / 5, 418 - 0.95 (ly - 393) / 5) for centres, sizes / 5 unscaled (relayout of build_world_v76); post_shift = 0 here',
            'pad_height_m': None, 'lighting': 'sunny_bright_no_fog', 'buildings': blds, 'props': props, 'zones': zones,
            'counts': {'buildings': len(blds)}}


# ------------------------------------------------------------------ 06 Port, 10 Tramduro (v11 m)
def warp_m(x, y):                                    # build_world_v76.py, verbatim
    from common import r as r_
    GROW_Y = 85.0
    y2 = y + GROW_Y + 10 if y >= 838 else None
    sy = r_(y, 505, 575 - 35 * r_(x, 880, 940))
    rn = r_(x, 520, 545)
    dx = (1 - sy) * (70 + 70 * r_(x, 575, 615)) + sy * (70 * (1 - rn) + rn * (110 + 140 * r_(x, 880, 940) + 20 * r_(x, 1088, 1110)))
    dy = sy * rn * (75 - 30 * r_(x, 880, 940))
    return x + dx, (y2 if y2 is not None else y + dy)


PORT_C, PORT_SCALE = (1261, 636.0), (1.25, 0.8)
PORT_FIT = (0.0, 0.0)                                 # residual fit on the v76 render


def port_w(p):
    x, y = warp_m(*p)
    x, y = PORT_C[0] + (x - PORT_C[0]) * PORT_SCALE[0], PORT_C[1] + (y - PORT_C[1]) * PORT_SCALE[1]
    x, y = post((x, y))
    return [round(x + PORT_FIT[0], 2), round(y + PORT_FIT[1], 2)]


def port():
    d = load(PORT_SRC)
    w11 = load(WORLD11)
    blds, props, zones = [], [], []
    for b in w11['buildings']:
        if str(b['district']) != '06' or b['kind'] == 'shipping_container_stack':
            continue
        kind = b['kind']
        walls = {'warehouse': 'facade_warehouse', 'storage_tank': 'metal_painted_SK6a', 'checkpoint_booth': 'concrete_panel_SK3c'}.get(kind, 'concrete_panel_SK3c')
        roof = {'type': 'flat', 'material': 'roof_profsheet_SK4c' if kind == 'warehouse' else 'roof_flat_SK4d'}
        if kind == 'storage_tank':
            roof = {'type': 'dome_low', 'material': 'metal_painted_SK6a'}
        blds.append({'id': b['id'], 'kind': kind, 'footprint': [port_w(p) for p in b['footprint_m']], 'floors': b.get('floors', 1), 'floor_h_m': 3.2,
                     'height_m': b.get('height_m', 3.2), 'roof': roof, 'walls': walls, 'tint': None, 'entrances': [], 'facade_kit': 'none',
                     'sockets': {'windows': kind == 'warehouse'}, 'collider': 'full_roof', 'notes': b.get('name', '')})
    ph = d['pump_house']
    blds.append({'id': '06-pump-house', 'kind': 'pump_house', 'footprint': [port_w(p) for p in rect(*ph)], 'floors': 1, 'floor_h_m': 3.4, 'height_m': 3.4,
                 'roof': {'type': 'gable', 'material': 'roof_tile_SK4a', 'ridge_h_m': 1.6, 'overhang_m': 0.3}, 'walls': 'brick_SK3a', 'tint': None,
                 'entrances': [], 'facade_kit': 'none', 'sockets': {'ridge_cap': 'tile'}, 'collider': 'full_roof', 'notes': 'brick pump house; roof type not given -> gable = OPEN'})
    for i, c in enumerate(d['containers']):
        L = c['len']
        x, y = c['c']
        poly = rrect((x, y), L, 2.44, c['angle'])
        props.append({'id': '06-cont%02d' % i, 'kind': 'shipping_container_%dft' % (40 if L > 7 else 20), 'pos': port_w((x, y)), 'rot_deg': c['angle'], 'tiers': c['tiers'],
                      'size': [L, 2.44, 2.59 * c['tiers']], 'footprint': [port_w(p) for p in poly], 'material': 'metal_painted_SK6a'})
    wt = d['water_tower']
    props.append({'id': '06-water-tower', 'kind': 'water_tower', 'pos': port_w(wt['center']), 'rot_deg': 0, 'size': [wt['tank_r'] * 2, wt['tank_r'] * 2, 18]})
    m = d['machines']
    props.append({'id': '06-reach-stacker', 'kind': 'reach_stacker', 'pos': port_w(m['reach_stacker']), 'rot_deg': 0, 'size': [11, 4, 5]})
    props.append({'id': '06-truck-40ft', 'kind': 'truck_with_container', 'pos': port_w(m['truck_with_40ft']), 'rot_deg': 0, 'size': [17, 2.5, 4]})
    for i, f in enumerate(m['forklifts']):
        props.append({'id': '06-forklift%d' % i, 'kind': 'forklift', 'pos': port_w(f), 'rot_deg': 0, 'size': [3.2, 1.2, 2.2]})
    sm = d['small']
    for k, v in sm.items():
        if isinstance(v, list) and v and isinstance(v[0], list):
            for i, q in enumerate(v):
                props.append({'id': '06-%s%02d' % (k, i), 'kind': k.rstrip('s'), 'pos': port_w(q[:2]), 'rot_deg': 0})
        elif isinstance(v, list) and len(v) == 4:
            props.append({'id': '06-' + k, 'kind': k, 'footprint': [port_w(p) for p in rect(*v)], 'pos': port_w(((v[0] + v[2]) / 2, (v[1] + v[3]) / 2)), 'rot_deg': 0})
        elif isinstance(v, list) and len(v) == 2:
            props.append({'id': '06-' + k, 'kind': k, 'pos': port_w(v), 'rot_deg': 0})
        else:
            props.append({'id': '06-' + k, 'kind': k, 'count': v, 'pos': None, 'notes': 'count only in layout v03 — place by logic (OPEN)'})
    shape = [(1178, 672), (1176, 611), (1191, 599), (1320, 598), (1341, 609), (1352, 637), (1344, 664), (1325, 677), (1191, 679)]
    zones.append({'id': '06-yard', 'kind': 'yard', 'poly': R([post(p) for p in shape]), 'surface': 'concrete_SK3c', 'fence': True,
                  'notes': 'PORT_SHAPE of build_world_v76.py; quay with bollards/fenders, pier into the bay; checkpoint without barrier'})
    return {'district': 'port', 'sources': [os.path.relpath(PORT_SRC, ROOT), os.path.relpath(WORLD11, ROOT) + ' (district 06 buildings)', 'build_world_v76.py PORT_*'],
            'transform': 'v76 = post_shift(scale about PORT_C (1261, 636) by (1.25, 0.8) of warp_m(v11)) + fit %s' % (PORT_FIT,),
            'pad_height_m': 2.5, 'lighting': 'sea_fog_cold', 'buildings': blds, 'props': props, 'zones': zones,
            'counts': {'buildings': len(blds), 'containers': len(d['containers'])}}


TRAM_FIT = (244.2, 194.5)     # pure translation v11 -> v76, fitted on the drawn palace (01) and hangar (03): residual < 0.5 m
                               # (warp_m + post would give +270/+44 — the island was moved again later with the Port; the drawing wins)


def tram_w(p):
    return [round(p[0] + TRAM_FIT[0], 2), round(p[1] + TRAM_FIT[1], 2)]


def tramduro():
    d = load(TRAM_SRC)
    blds, props, zones = [], [], []
    bkinds = {'closed_residence': ('palace_facade_only', 'stucco_SK3b', {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.8}),
              'large_three_tank_hangar': ('arched_hangar_open', 'concrete_panel_SK3c', {'type': 'barrel', 'material': 'roof_profsheet_SK4c'}),
              'guard_booth': ('guard_booth', 'concrete_panel_SK3c', {'type': 'flat', 'material': 'roof_flat_SK4d'})}
    for o in d['objects']:
        if o['kind'] in bkinds and o.get('centre_m'):
            k, wl, rf = bkinds[o['kind']]
            c = o['centre_m']
            poly = rrect(c, o['size_m'][0], o['size_m'][1], o.get('rotation_deg', 0))
            blds.append({'id': '10-' + o['id'], 'kind': k, 'footprint': [tram_w(p) for p in poly], 'floors': 1 if o['kind'] != 'closed_residence' else 3,
                         'floor_h_m': 3.2, 'height_m': o.get('height_m') or 3.2, 'roof': rf, 'walls': wl, 'tint': '#F4F1EA' if o['kind'] == 'closed_residence' else None,
                         'entrances': [], 'facade_kit': 'none', 'sockets': {'windows': True}, 'collider': 'full_roof',
                         'notes': {'closed_residence': 'white palace 48x22 m on a +2 m mound, facade only, no interior',
                                   'large_three_tank_hangar': 'open arched hangar 44x30x8 m with 3 tanks; walls/roof open at the front',
                                   'guard_booth': 'bridge checkpoint booth'}[o['kind']]})
        elif o.get('polygon_m'):
            zones.append({'id': '10-' + o['id'], 'kind': o['kind'], 'poly': [tram_w(p) for p in o['polygon_m']],
                          'surface': {'continuous_concrete_base': 'concrete_SK3c', 'coastal_presidential_lawn': 'lawn', 'three_short_hole_golf_area': 'lawn'}.get(o['kind'])})
        elif o.get('centre_m'):
            props.append({'id': '10-' + o['id'], 'kind': o['kind'], 'pos': tram_w(o['centre_m']), 'rot_deg': o.get('rotation_deg', 0),
                          'size': list(o['size_m']) + [o.get('height_m') or 0], 'solid': o.get('solid')})
        else:
            zones.append({'id': '10-' + o['id'], 'kind': o['kind'], 'data': {k: v for k, v in o.items() if k not in ('id', 'kind')}, 'notes': 'non-spatial or line data in v06, see source'})
    return {'district': 'tramduro', 'sources': [os.path.relpath(TRAM_SRC, ROOT), 'TRAMDURO_PLAN_06_FINAL.png', 'handoff v02 §8.10'],
            'transform': 'v76 = v11 + %s (translation fitted on the v76 render: palace + hangar)' % (TRAM_FIT,), 'pad_height_m': None, 'lighting': 'light_sea_haze',
            'buildings': blds, 'props': props, 'zones': zones, 'counts': {'buildings': len(blds), 'props': len(props)},
            'notes': 'missiles are fired at the van already on the bridge (18.10); 20-25 soldiers, 1-2 patrol boats; fence 4 m steel + barbed wire, one gate'}


def overlay(dist, out, box):
    im = Image.open(MAP_PREVIEW).convert('RGB')
    dr = ImageDraw.Draw(im)
    P = lambda p: (p[0], 950 - p[1])
    for b in dist['buildings']:
        dr.polygon([P(p) for p in b['footprint']], outline=(255, 0, 0))
        for e in b.get('entrances', []):
            dr.point(P(e['pos']), fill=(0, 0, 255))
    for p in dist['props']:
        if p.get('pos'):
            dr.point(P(p['pos']), fill=(255, 0, 255))
        if p.get('footprint'):
            dr.polygon([P(q) for q in p['footprint']], outline=(255, 0, 255))
    for z in dist['zones']:
        if 'poly' in z:
            dr.polygon([P(q) for q in z['poly']], outline=(0, 160, 255))
        if 'line' in z:
            dr.line([P(q) for q in z['line']], fill=(0, 200, 0))
    x0, y0, x1, y1 = box
    c = im.crop((x0, 950 - y1, x1, 950 - y0))
    s = max(1, int(900 / max(c.size)))
    c.resize((c.width * s, c.height * s), Image.NEAREST).save(out)


def main():
    os.makedirs(WORK, exist_ok=True)
    boxes = {'rough': (630, 640, 1040, 930), 'construction': (500, 320, 720, 520), 'port': (1150, 580, 1380, 710), 'tramduro': (1420, 640, 1690, 900)}
    for name, fn in (('rough', rough), ('construction', construction), ('port', port), ('tramduro', tramduro)):
        dist = fn()
        save_json('districts/%s_v76.json' % name, dist)
        overlay(dist, os.path.join(WORK, 'check_%s.png' % name), boxes[name])
        print(name, dist['counts'])


if __name__ == '__main__':
    main()
