"""Step 4 (south): districts Downtown (05), Elite hill (07), City beach (09) -> Data/v01/districts/<name>_v76.json.

Sources (nothing re-invented; assumptions are listed in each building's `notes` and in the district `open`):
 Downtown  footprints = the bld() polygons of Vadim's generator build_gorod_v27.py, read back from its output
           Город_Downtown_v27.svg (group 'buildings', matched 1:1 with group 'shadows' -> conditional height h);
           streets = ST of build_gorod_v27.py; numbered objects, plaza, base 13, yards, alleys = DOWNTOWN_LEGEND_v26.md.
           Placement on v76: least-squares fit of the ST centre lines to the asphalt of the v76 render (see FIT).
 Elite     D07_Elite_Hill_layout_v09.json (v11 m) + make_elite_v10.py (villa plots rotated/shifted) read back from
           World_v74/elite_v10_world.png (6 px/m, top-left = pre-shift (1260, 450)); fence/ring from build_world_v76.py.
 Beach     build_world_v76.py lines 1246-1375 (pre-shift constants) -> post_shift.
"""
import math
import os
import re

import numpy as np
from PIL import Image

from common import ROOT, WORK, post, rnd2, save_json

GOROD = os.path.join(ROOT, 'ArtSource', 'References', 'Map', 'Desktop_Map_sources_2026-10-18', 'Город')
SVG = os.path.join(GOROD, 'Город_Downtown_v27.svg')
GEN = os.path.join(GOROD, 'build_gorod_v27.py')
ELITE_JSON = os.path.join(ROOT, 'ArtSource', 'References', 'Map', 'World_v11', 'Districts', 'D07_Elite_Hill_layout_v09.json')
ELITE_PNG = os.path.join(ROOT, 'ArtSource', 'References', 'Map', 'World_v74', 'elite_v10_world.png')
PREVIEW = os.path.join(ROOT, 'ArtSource', 'References', 'Map', 'World_v76', 'VOLUNTEERS_MAP_PREVIEW_v76.png')

# plan metres (x east, y SOUTH, 1 generator unit = 0.2 m) -> v76 world; fitted to the v76 asphalt (mean miss 0.06 m)
FIT = {'scale': 0.99, 'tx': 798.0, 'ty': 469.0}


def dt(xm, ym):
    return (FIT['tx'] + FIT['scale'] * xm, FIT['ty'] - FIT['scale'] * ym)


def du(p):                                                   # generator units -> world
    return dt(p[0] / 5.0, p[1] / 5.0)


def area(pl):
    return 0.5 * abs(sum(pl[i][0] * pl[i - 1][1] - pl[i - 1][0] * pl[i][1] for i in range(len(pl))))


def ccw(pl):
    s = sum(pl[i][0] * pl[i - 1][1] - pl[i - 1][0] * pl[i][1] for i in range(len(pl)))
    return pl if s < 0 else pl[::-1]                         # shoelace sign above is reversed (p_i x p_{i-1})


def centroid(pl):
    return (sum(p[0] for p in pl) / len(pl), sum(p[1] for p in pl) / len(pl))


def inside(pt, pl):
    c = False
    for i in range(len(pl)):
        (x0, y0), (x1, y1) = pl[i - 1], pl[i]
        if (y0 > pt[1]) != (y1 > pt[1]) and pt[0] < x0 + (pt[1] - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy or 1e-9
    t = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy), (a[0] + t * vx, a[1] + t * vy)


def h01(s):                                                  # deterministic 0..1 from an id
    v = 2166136261
    for ch in s:
        v = ((v ^ ord(ch)) * 16777619) & 0xffffffff
    return v / 0xffffffff


def calm(col):
    """v02 §8.5: no bright red / yellow / blue — damp saturation of strong colours (generator palette otherwise kept)."""
    r, g, b = [int(col[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    mx, mn = max(r, g, b), min(r, g, b)
    sat = (mx - mn) / mx if mx else 0
    if sat > 0.5:
        k = 0.5 / sat
        r, g, b = [mx - (mx - c) * k for c in (r, g, b)]
    return '#%02X%02X%02X' % tuple(int(round(c * 255)) for c in (r, g, b))


# ---------------------------------------------------------------- Downtown
def svg_group(s, gid):
    a = s.index('<g id="%s"' % gid)
    return s[a:s.index('</g>', a)]


def svg_polys(seg):
    out = []
    for at in re.findall(r'<polygon\b([^>]*)>', seg):
        pts = [tuple(map(float, p.split(','))) for p in re.search(r'points="([^"]*)"', at).group(1).split()]
        out.append((pts, re.search(r'fill="([^"]*)"', at).group(1)))
    return out


def gen_streets():
    src = open(GEN, encoding='utf-8').read()
    blk = src[src.index('ST = {'):src.index('CANAL =')]
    xmin, xmax = -110, 2460
    out = {}
    for name, body in re.findall(r"'(\w+)': St\(\[([^\]]*)\]", blk):
        body = body.replace('XMIN', str(xmin)).replace('XMAX', str(xmax)).replace(', H)', ', 1460)')
        out[name] = [tuple(map(float, p)) for p in re.findall(r'\(([-\d.]+), ([-\d.]+)\)', body)]
    return out


LEGEND_OBJ = {   # DOWNTOWN_LEGEND_v26 §2 (plan m, y south)
    '01': ((201.0, 49.2), 'twin tower 1 (west)'), '02': ((267.0, 49.2), 'twin tower 2 (east)'),
    '35': ((234.0, 55.2), 'big screen on the podium (Tramduro from app Z)'), '03': ((173.2, 44.4), 'underground parking'),
    '15': ((250.0, 146.4), 'golden Tramduro monument'), '36': ((256.4, 138.0), 'police booth'), '08': ((218.4, 131.2), 'ATM (one per district)'),
    '16': ((181.2, 89.0), 'glass pavilion'), '17': ((286.8, 89.0), 'glass pavilion'), '18': ((181.2, 127.0), 'glass pavilion'),
    '19': ((286.8, 127.0), 'glass pavilion'), '04': ((176.0, 112.0), 'plaza Water Axis'), '14': ((294.0, 168.0), 'bus stop'),
    '23': ((66.0, 130.0), 'square NW'), '42': ((128.0, 121.6), 'service yard (entry from Vb)'), '43': ((348.0, 65.0), 'service yard (entry from Vd)'),
    'P': ((332.6, 131.9), 'surface parking behind chain-link'), '11': ((424.8, 87.2), 'police 2 (NE)'), '12': ((402.0, 82.8), 'taxi depot'),
    '20': ((380.0, 120.0), 'square with pond (NE)'), '41': ((48.0, 169.0), 'gas station'), '10': ((30.0, 219.0), 'police 1 (SW, rotunda)'),
    '07': ((137.6, 186.0), 'van shop'), '05': ((207.0, 188.0), 'glass office'), '06': ((256.0, 189.0), 'glass office'),
    '40': ((251.0, 229.0), 'corner diner (chrome, red stripe)'), '13': ((424.0, 212.4), 'BASE 4: courtyard behind an arch, garage with roll shutter')}
ALLEYS = [((28.2, 38.2, 80.8, 82.8), 'we', 60.5, 54.5), ((97.2, 22.2, 149.8, 82.8), 'ns', 123.5, 52.5),
          ((72.2, 206.2, 115.8, 233.8), 'we', 220.0, 94.0), ((149.8, 180.2, 171.8, 217.8), 'ns', 160.8, 199.0),
          ((318.2, 160.2, 359.8, 197.8), 'we', 179.0, 339.0), ((376.2, 160.2, 455.8, 183.8), 'we', 172.0, 416.0)]


def rect_m(x0, y0, x1, y1):
    return [rnd2(dt(x0, y0)), rnd2(dt(x1, y0)), rnd2(dt(x1, y1)), rnd2(dt(x0, y1))]


def downtown():
    s = open(SVG, encoding='utf-8').read()
    shadows = svg_polys(svg_group(s, 'shadows'))
    bseg = svg_group(s, 'buildings')
    blds = svg_polys(bseg)
    used, matched = set(), []
    for sp, _ in shadows:                                   # bld() writes the shadow = footprint + h * (0.55, 0.75)
        for i, (bp, f) in enumerate(blds):
            if i in used or f == 'none' or len(bp) != len(sp):
                continue
            dx, dy = sp[0][0] - bp[0][0], sp[0][1] - bp[0][1]
            if dx <= 0 or abs(dy / dx - 0.75 / 0.55) > 0.05:
                continue
            if all(abs(a[0] + dx - b[0]) < 0.35 and abs(a[1] + dy - b[1]) < 0.35 for a, b in zip(bp, sp)):
                used.add(i)
                matched.append((bp, f, dx / 0.55))
                break
    fire = [(bp[0], bp[1], (bp[3][0] - bp[0][0], bp[3][1] - bp[0][1])) for bp, f in blds if f == '#3D4246' and len(bp) == 4]
    tanks = [(float(a), float(b)) for a, b in re.findall(r'<circle cx="([-\d.]+)" cy="([-\d.]+)" r="5.5" fill="#8B6B4A"', bseg)]
    streets = gen_streets()
    st_world = {k: [du(p) for p in v] for k, v in streets.items()}
    buildings = []
    special = {'#2E4E73': 'tower', '#B7C7D4': 'podium', '#A9C4D3': 'pavilion', '#3F6C99': 'tower_round_corner', '#A7BED2': 'podium',
               '#4C78A3': 'glass_office', '#E2DCCC': 'classical'}
    for k, (bp, f, h) in enumerate(sorted(matched, key=lambda m: (centroid(m[0])[1], centroid(m[0])[0]))):
        fw = ccw([du(p) for p in bp])
        c = centroid(fw)
        bid = '05-B%03d' % k
        kind = special.get(f, 'house')
        notes = []
        if kind == 'tower':
            num = '01' if c[0] < dt(234, 0)[0] else '02'
            bid = '05-%s' % num
            floors, fh, height = 55, 3.6, 200.0
            walls, roof = 'tower_glass', {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 1.2}
            notes.append('round faceted dark-blue glass, light crown at the top, identical twins (legend §2)')
        elif kind == 'tower_round_corner':
            floors, fh = 24, 3.6
            height = floors * fh
            walls, roof = 'tower_glass', {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 1.2}
            notes.append('ASSUMPTION height: legend gives only Ø 18.4 m; generator shadow h=46 vs 70 for the 200 m twins -> ~24 floors (OPEN)')
        elif kind == 'podium':
            floors, fh = (1, 6.0) if area(fw) > 1500 else (2, 4.0)
            height = floors * fh
            walls, roof = 'tower_glass', {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 1.0}
            notes.append('glass podium; twins podium = top of the 5-step stair to the plaza' if area(fw) > 1500 else 'podium of the round corner tower')
        elif kind == 'pavilion':
            floors, fh, height = 1, 4.5, 4.5
            walls, roof = 'tower_glass', {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.3}
            notes.append('glass pavilion ~18x10 m with terrace and 3 yellow umbrellas (legend §3)')
        elif kind == 'glass_office':
            floors, fh = 10, 3.6
            height = floors * fh
            walls, roof = 'tower_glass', {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 1.0}
            notes.append('ASSUMPTION floors: legend gives no height; shadow h=30 vs 18 for 6-7-floor corner houses (OPEN)')
        elif kind == 'classical':
            floors, fh, height = 3, 4.6, 14.0
            walls, roof = 'stucco_SK3b', {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 1.0}
            notes.append('stone building with colonnade to the promenade, skylight in the middle')
        else:
            # legend §6: ordinary houses 4-7 floors, corner/large houses bigger and higher; generator h: 12 narrow, 18+ large
            lo, hi = (1, 2) if h < 7.5 else (4, 5) if h < 12.5 else (5, 6) if h < 16 else (6, 7)
            floors = lo + int(h01(bid) * (hi - lo + 1) - 1e-9)
            fh = 3.5
            height = floors * fh
            walls = 'facade_downtown_brick' if h01(bid + 'w') < 0.45 else 'facade_downtown_stucco'
            roof = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.8}
            if h < 7.5:
                notes.append('low structure (generator h=%.0f): kiosk / canopy / annex' % h)
            if abs(h - 11) < 0.6 and area(fw) > 500 and f == '#7E4436':
                kind, roof = 'loft', {'type': 'sawtooth', 'material': 'roof_profsheet_SK4c', 'parapet_h_m': 0.8}
                notes.append('brick loft with saw-tooth roof (legend §6)')
        # nearest street -> main entrance on that side
        best = None
        for sn, pl in st_world.items():
            for a, b in zip(pl[:-1], pl[1:]):
                d, q = seg_dist(c, a, b)
                if best is None or d < best[0]:
                    best = (d, q, sn)
        door = None
        if best:
            q = best[1]
            for a, b in zip(fw, fw[1:] + fw[:1]):               # wall point nearest to the street foot point
                d, w = seg_dist(q, a, b)
                if door is None or d < door[0]:
                    door = (d, w)
            ang = math.degrees(math.atan2(q[1] - door[1][1], q[0] - door[1][0]))
        sock_fire = []
        for p0, p1, o in fire:
            mid = du(((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2))
            if min(seg_dist(mid, a, b)[0] for a, b in zip(fw, fw[1:] + fw[:1])) < 0.8:
                sock_fire.append({'from': rnd2(du(p0)), 'to': rnd2(du(p1)), 'out_deg': round(math.degrees(math.atan2(-o[1], o[0])), 1)})
        tank = any(inside(du(t), fw) for t in tanks)
        tint = None if walls == 'tower_glass' else calm(f)
        buildings.append({
            'id': bid, 'kind': kind, 'footprint': [rnd2(p) for p in fw], 'floors': floors, 'floor_h_m': fh, 'height_m': round(height, 1),
            'roof': roof, 'walls': walls, 'tint': tint, 'src_colour': f, 'gen_shadow_h': round(h, 1),
            'entrances': [{'pos': rnd2(door[1]), 'facing_deg': round(ang, 1), 'kind': 'door', 'w_m': 1.2, 'street': best[2]}] if door else [],
            'facade_kit': 'downtown' if walls != 'tower_glass' else 'none',
            'sockets': {'balconies': 'none', 'windows': walls != 'tower_glass', 'fire_escape': sock_fire or False,
                        'ac_units': 0 if walls == 'tower_glass' else 1 + int(h01(bid + 'ac') * 3), 'water_tank': tank,
                        'awning': walls != 'tower_glass' and h01(bid + 'aw') < 0.35, 'storefront': walls != 'tower_glass' and h01(bid + 'sf') < 0.55,
                        'ridge_cap': None},
            'collider': 'full_roof', 'notes': '; '.join(notes)})
    # number the twin podium and objects for the builder
    zones, props = [], []
    for sn, pl in streets.items():
        zones.append({'id': 'street_' + sn, 'kind': 'street', 'poly_line': [rnd2(du(p)) for p in pl], 'carriageway_m': round(8.5 * FIT['scale'], 2),
                      'sidewalk_m': round(4.0 * FIT['scale'], 2), 'curb_m': 0.15, 'surface': 'asphalt_A5d12', 'sidewalk_surface': 'sidewalk_S1',
                      'corner_radius_m': 4.0, 'boulevard': sn == 'B'})
    zones += [
        {'id': '04_plaza', 'kind': 'plaza', 'poly': rect_m(166.2, 60, 301.8, 162.8), 'surface': 'plaza_M3', 'notes': 'no trees; dark 0.5 m stone band along edges'},
        {'id': '04_tower_podium', 'kind': 'podium', 'poly': rect_m(176, 39.2, 292, 60), 'surface': 'plaza_M3'},
        {'id': '04_stair', 'kind': 'stair', 'poly': rect_m(180, 60.8, 288, 65.6), 'steps': 5, 'surface': 'plaza_M3', 'notes': 'tribune steps, NPC sit'},
        {'id': '04_cascade', 'kind': 'water_cascade', 'poly': rect_m(229.2, 60.8, 238.8, 65.6)},
        {'id': '04_pool', 'kind': 'pool', 'poly': rect_m(226, 67.2, 242, 126.8), 'depth_m': 0.3, 'edge_m': 1.2, 'notes': 'van drives in with splashes'},
        {'id': '15_monument_ring', 'kind': 'dry_fountains', 'centre': rnd2(dt(234, 144.4)), 'podium_d_m': 8.8, 'jets_r_m': 9.2, 'jets': 18, 'edge_r_m': 12.8},
        {'id': '03_parking', 'kind': 'underground_parking', 'poly': rect_m(168, 38.4, 300, 60.8), 'levels': 1,
         'ramps': [rect_m(169.2, 22.2, 177.2, 38.4), rect_m(292, 38.2, 300, 50)], 'notes': 'two identical two-way ramps; van turns inside'},
        {'id': '13_base_arch', 'kind': 'arch', 'poly': rect_m(430, 200.2, 440, 208), 'notes': 'drive-through arch under the house x 412-440 (entry from Hse2)'},
        {'id': '13_base_yard', 'kind': 'yard', 'poly': rect_m(412, 208, 440, 217), 'surface': 'concrete_SK3c', 'notes': 'closed courtyard, not visible from street'},
        {'id': '13_base_garage', 'kind': 'garage', 'poly': rect_m(392, 200.2, 412, 217.8), 'walls': 'brick_SK3a', 'gate': {'pos': rnd2(dt(412, 213)), 'kind': 'rollshutter', 'w_m': 6.0}},
        {'id': '42_yard', 'kind': 'service_yard', 'poly': rect_m(109.2, 112, 149.8, 131), 'entry': rect_m(149.8, 114.4, 151.8, 128.6), 'surface': 'concrete_SK3c'},
        {'id': '43_yard', 'kind': 'service_yard', 'poly': rect_m(331, 51, 359.8, 70), 'entry': rect_m(359.8, 61.2, 361.8, 69.2), 'surface': 'concrete_SK3c'}]
    for k, ((x0, y0, x1, y1), d, line, plug) in enumerate(ALLEYS):
        if d == 'we':
            zones.append({'id': 'alley_%d' % k, 'kind': 'dead_end_alley_pair', 'poly': rect_m(x0, line - 2.8, x1, line + 2.8), 'width_m': 5.6,
                          'plug_wall': rect_m(plug - 2.4, line - 2.8, plug + 2.4, line + 2.8), 'surface': 'asphalt_old_SK2a'})
        else:
            zones.append({'id': 'alley_%d' % k, 'kind': 'dead_end_alley_pair', 'poly': rect_m(line - 2.8, y0, line + 2.8, y1), 'width_m': 5.6,
                          'plug_wall': rect_m(line - 2.8, plug - 2.4, line + 2.8, plug + 2.4), 'surface': 'asphalt_old_SK2a'})
    for num, (p, desc) in LEGEND_OBJ.items():
        props.append({'id': '05-' + num, 'kind': 'legend_object', 'label': desc, 'pos': rnd2(dt(*p))})
    for x in (212, 256):
        for y in (80, 104, 124):
            props.append({'id': 'bench_round_%d_%d' % (x, y), 'kind': 'round_bench_flowerbed', 'pos': rnd2(dt(x, y)), 'size': [5, 5, 0.5]})
    for x in (220, 248):
        for k, y in enumerate((72, 86, 100, 114)):
            props.append({'id': 'flag_%d_%d' % (x, k), 'kind': 'flagpole', 'pos': rnd2(dt(x, y)), 'size': [0.3, 0.3, 12], 'grip_anchor': True})
    for k, (x, y) in enumerate(((172, 70), (296, 70), (172, 116), (296, 116), (200, 158), (268, 158))):
        props.append({'id': 'plaza_lamp_%d' % k, 'kind': 'lamp_tall', 'pos': rnd2(dt(x, y)), 'grip_anchor': True,
                      'notes': 'legend: 6 tall lamps; exact spots not given -> plaza corners/edges (ASSUMPTION)'})
    return {'district': 'downtown', 'sources': [os.path.relpath(SVG, ROOT), os.path.relpath(GEN, ROOT), 'docs/specs/DOWNTOWN_LEGEND_v26.md'],
            'transform': 'world = (%.1f + %.3f*xm, %.1f - %.3f*ym), xm/ym = plan metres (generator units / 5, y south); fitted to v76 asphalt' % (
                FIT['tx'], FIT['scale'], FIT['ty'], FIT['scale']),
            'pad_height_m': 5.0, 'buildings': buildings, 'props': props, 'zones': zones,
            'open': ['street width: legend 8.5 m + 2x4 m sidewalks vs "like One-Armed Robber, a bit narrower" (v02 proposes ~10-11 + 5 m) — ASK VADIM; data keeps the legend',
                     'corner round tower height and glass offices 05/06 floors not given (assumed 24 / 10 floors)',
                     'house floors 4-7 drawn deterministically from the generator shadow height class (legend §6 gives only the range)',
                     'sky-scraper glass "more beautiful than TowerGlass" still to be found (handoff §3.2)']}


# ---------------------------------------------------------------- Elite
EC_PRE, EA, EB = (1398.2, 349.5), 72.5, 58.8
V11_TO_PRE = (140.2, 0.0)                                    # v11 fence centre (1258, 349.5) -> v76 pre-shift (1398.2, 349.5)
E_PPM, E_X0, E_Y0 = 6.0, 1260.0, 450.0                     # elite_v10_world.png
PLOTS = [((404, 264, 716, 486), -5.0, (-8, 6)), ((940, 264, 1250, 486), -9.0, (7, -2)),
         ((940, 708, 1252, 934), 4.0, (5, 6)), ((404, 714, 710, 934), 10.0, (-7, -4))]   # make_elite_v10.py


def epx(px, py):
    return post((E_X0 + px / E_PPM, E_Y0 - py / E_PPM))


def mask_rects(mask, min_px):
    from skimage import measure
    lab = measure.label(mask)
    out = []
    for rp in measure.regionprops(lab):
        if rp.area < min_px:
            continue
        cy, cx = rp.centroid
        ang = -rp.orientation + math.pi / 2                    # skimage: angle of major axis vs rows
        L, Wd = rp.axis_major_length, rp.axis_minor_length
        k = math.sqrt(rp.area / max(1.0, L * Wd))           # ellipse axes -> rectangle with the same area
        out.append(((cx, cy), L * k, Wd * k, ang, rp.area))
    return out


def rect_world(cpx, Lpx, Wpx, ang):
    c, s = math.cos(ang), math.sin(ang)
    pts = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        x = cpx[0] + sx * Lpx / 2 * c - sy * Wpx / 2 * s
        y = cpx[1] + sx * Lpx / 2 * s + sy * Wpx / 2 * c
        pts.append(epx(x, y))
    return ccw(pts)


def elite():
    import json
    d = json.load(open(ELITE_JSON, encoding='utf-8'))
    im = np.asarray(Image.open(ELITE_PNG).convert('RGB')).astype(int)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    from scipy import ndimage
    white = ndimage.binary_opening((R > 219) & (G > 215) & (B > 204) & (np.abs(R - G) < 10) & (R - B < 20), iterations=3)
    plotg = ndimage.binary_opening((np.abs(R - 206) < 10) & (np.abs(G - 226) < 9) & (np.abs(B - 184) < 12), iterations=2)
    pool = (B > 200) & (R < 150) & (G > 170)
    dark = (R < 110) & (B > R) & (B < 140)
    buildings, zones, props = [], [], []
    for k, ((x0, y0, x1, y1), ang, (dx, dy)) in enumerate(PLOTS):
        v = d['villas'][k]
        sub = np.zeros_like(white)
        sub[y0 + dy:y1 + dy, x0 + dx:x1 + dx] = True
        whites = sorted(mask_rects(white & sub, 300), key=lambda r: -r[4])
        pools = sorted(mask_rects(pool & sub, 200), key=lambda r: -r[4])
        vid = '07-V%s' % v['id']
        house = whites[0] if whites else None
        garage = next((w for w in whites[1:] if 0.6 < w[1] / max(1, w[2]) < 1.6 and w[4] < house[4] * 0.6), None) if house else None
        parts = [r[0] for r in (house, garage, pools[0] if pools else None) if r]
        pc = (sum(p[0] for p in parts) / len(parts), sum(p[1] for p in parts) / len(parts)) if parts else ((x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy)
        pa = house[3] if house else math.radians(-ang)
        if house and abs(math.cos(pa)) < 0.7:
            pa += math.pi / 2                                    # keep the long side of the plot along the house
        plot_poly = rect_world(pc, v['size'][0] * E_PPM, v['size'][1] * E_PPM, pa)   # plot size from v09 json, pose from v10 png
        zones.append({'id': vid + '_plot', 'kind': 'villa_plot', 'poly': [rnd2(p) for p in plot_poly], 'surface': 'lawn', 'hedge_h_m': 1.8,
                      'terrace': v.get('terrace'), 'notes': 'plot rotated %+.0f deg and shifted (make_elite_v10.py)' % ang})
        if house:
            fw = rect_world(house[0], house[1], house[2], house[3])
            buildings.append({'id': vid, 'kind': 'villa', 'footprint': [rnd2(p) for p in fw], 'floors': 2, 'floor_h_m': 3.4, 'height_m': 6.8,
                              'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.5, 'roof_terrace': True},
                              'walls': 'facade_elite_villa', 'tint': '#F2F0EA', 'entrances': [{'pos': rnd2(epx(*house[0])), 'facing_deg': 0, 'kind': 'door', 'w_m': 1.6}],
                              'facade_kit': 'none', 'sockets': {'balconies': 'none', 'windows': True, 'pergola': True, 'louvres': True},
                              'collider': 'full_roof', 'house_type': v.get('house_type'),
                              'notes': 'VIP villa (parody of %s); footprint read from elite_v10_world.png; ~22x10 m (v02 §8.7)' % ('IShowSpeed', 'Sweetie Fox', 'Michael Jackson', 'Satoru Gojo')[k]})
        if garage:
            buildings.append({'id': vid + '_garage', 'kind': 'garage', 'footprint': [rnd2(p) for p in rect_world(garage[0], garage[1], garage[2], garage[3])],
                              'floors': 1, 'floor_h_m': 3.2, 'height_m': 3.2, 'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.3},
                              'walls': 'facade_elite_villa', 'tint': '#ECEAE3', 'entrances': [], 'facade_kit': 'none', 'sockets': {}, 'collider': 'full_roof', 'notes': ''})
        if pools:
            zones.append({'id': vid + '_pool', 'kind': 'pool', 'poly': [rnd2(p) for p in rect_world(pools[0][0], pools[0][1], pools[0][2], pools[0][3])],
                          'surface': 'pool_tile', 'depth_m': 1.5, 'notes': 'deck 13x5 pool, loungers, umbrellas, palms'})
        props.append({'id': vid + '_gate', 'kind': 'villa_gate', 'pos': rnd2(post((v['gate'][0] + V11_TO_PRE[0], v['gate'][1]))), 'notes': 'v09 gate; plot was rotated in v10 — snap to plot edge'})
    fb = mask_rects(dark & (np.arange(im.shape[1])[None, :] > 700) & (np.arange(im.shape[1])[None, :] < 900) &
                    (np.arange(im.shape[0])[:, None] > 550) & (np.arange(im.shape[0])[:, None] < 650), 400)
    if fb:
        f0 = max(fb, key=lambda r: r[4])
        buildings.append({'id': '07-05_FBI', 'kind': 'fbi_post', 'footprint': [rnd2(p) for p in rect_world(f0[0], f0[1], f0[2], f0[3])], 'floors': 2, 'floor_h_m': 3.5,
                          'height_m': 7.0, 'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.6}, 'walls': 'concrete_panel_SK3c', 'tint': '#4E5A66',
                          'entrances': [], 'facade_kit': 'none', 'sockets': {'flag': True, 'cameras_decor': True}, 'collider': 'full_roof',
                          'notes': 'FBI building in the centre of the inner ring (~28x14 m), 3 black jeeps; trap at the gate (canon 18.10)'})
    fence = []
    for i in range(96):
        th = 2 * math.pi * i / 96
        c, s_ = math.cos(th), math.sin(th)
        fence.append(rnd2(post((EC_PRE[0] + EA * math.copysign(abs(c) ** 0.5, c), EC_PRE[1] + EB * math.copysign(abs(s_) ** 0.5, s_)))))
    ring = d['ring']
    rc = post((ring['center'][0] + V11_TO_PRE[0], ring['center'][1]))
    fence_oct = [rnd2(post((x + V11_TO_PRE[0], y))) for x, y in d['fence']]
    zones += [{'id': '07_fence', 'kind': 'fence', 'poly': fence_oct, 'height_m': 3.5, 'notes': 'high, solid (no beach exit: v10 closes the gap at gate 08), floodlights, barbed wire; octagon of v09/v10 plan'},
              {'id': '07_plateau', 'kind': 'plateau', 'poly': fence, 'abs_height_m': [40, 44], 'notes': 'uneven: +44 N, +41 W, +43 E, +40 S (elite_v10 labels)'},
              {'id': '07_inner_ring', 'kind': 'ring_road', 'centre': rnd2(rc), 'rx_m': ring['rx'], 'ry_m': ring['ry'], 'width_m': ring['width_m'], 'surface': 'asphalt_A5d12', 'lamps': True},
              {'id': '07_gate_06', 'kind': 'gate_trap', 'pos': rnd2(post((1327.0, 351.0))), 'abs_height_m': 44.0,
               'notes': 'gate latches shut right behind the van, very little time; FBI-style guards beat players (mechanics OPEN)'}]
    for p in d['piers']:
        zones.append({'id': '07_' + p['id'], 'kind': 'pier', 'poly': [rnd2(post((x + V11_TO_PRE[0], y))) for x, y in p['poly']], 'surface': 'boards_pier_SK5a_v02'})
    for k, y in enumerate(d['yachts']):
        props.append({'id': '07_yacht_%d' % k, 'kind': 'yacht', 'pos': rnd2(post((y['pos'][0] + V11_TO_PRE[0], y['pos'][1]))), 'rot_deg': y['angle'], 'size': [y['length_m'], y['width_m'], 3]})
    return {'district': 'elite', 'sources': [os.path.relpath(ELITE_JSON, ROOT), 'ArtSource/References/Map/World_v74/make_elite_v10.py', os.path.relpath(ELITE_PNG, ROOT),
                                             'ArtSource/References/Map/World_v76/build_world_v76.py (RING, fence)'],
            'transform': 'v11 + (140.2, 0) = v76 pre-shift, then post_shift (+20, -28); png px -> (1260 + px/6, 450 - py/6) pre-shift',
            'pad_height_m': None, 'abs_heights': True, 'buildings': buildings, 'props': props, 'zones': zones,
            'open': ['trap timing / consequences', 'catching on Elite beach', 'yachts/piers positions from v09 json (v10 png keeps them)']}


# ---------------------------------------------------------------- Beach
def beach():
    PARK_TOP, PARK_BOT, DUNE_BOT = 246.3, 229.0, 221.0
    LOTS = [(902.0, 936.0), (1149.0, 1183.0)]
    X0B, X1B = 786.0, 1240.0
    STREETS = (895.0, 1012.0, 1142.0)
    VAN_IN = (895.0, 1142.0)
    P = lambda pts: [rnd2(post(p)) for p in pts]
    zones = [{'id': '09_park', 'kind': 'palm_park', 'poly': P([(X0B, PARK_TOP), (X1B, PARK_TOP), (X1B, PARK_BOT), (X0B, PARK_BOT)]), 'surface': 'lawn',
              'notes': 'dense palms ~23 m, winding path, hides the sea from the city'},
             {'id': '09_dunes', 'kind': 'dunes', 'poly': P([(X0B, PARK_BOT), (X1B, PARK_BOT), (X1B, DUNE_BOT), (X0B, DUNE_BOT)]), 'surface': 'sand_white', 'shrubs': True}]
    path = [(X0B + 4, 240)] + [(x, 240 + 6 * math.sin((x - X0B) / 31.0)) for x in range(int(X0B) + 20, int(X1B) - 10, 20)] + [(X1B - 4, 240)]
    zones.append({'id': '09_park_path', 'kind': 'path', 'poly_line': P(path), 'width_m': 3.6, 'surface': 'sidewalk_S1'})
    for k, (l0, l1) in enumerate(LOTS):
        zones.append({'id': '09_parking_%d' % k, 'kind': 'parking', 'poly': P([(l0, 247.5), (l1, 247.5), (l1, 231), (l0, 231)]), 'surface': 'asphalt_A5d12', 'stall_w_m': 3.0})
    for sx in STREETS:
        if sx in VAN_IN:
            zones.append({'id': '09_van_entry_%d' % int(sx), 'kind': 'van_entry_sand', 'poly_line': P([(sx, PARK_TOP + 2), (sx, DUNE_BOT - 6)]), 'width_m': 8.0, 'surface': 'sand_ruts'})
        else:
            zones.append({'id': '09_pier_square', 'kind': 'square', 'poly': P([(sx - 14, PARK_TOP), (sx + 14, PARK_TOP), (sx + 14, PARK_BOT), (sx - 14, PARK_BOT)]), 'surface': 'plaza_M3'})
            zones.append({'id': '09_boardwalk_main', 'kind': 'boardwalk', 'poly_line': P([(sx, PARK_BOT), (sx, DUNE_BOT - 4)]), 'width_m': 6.0, 'surface': 'boards_pier_SK5a_v02'})
    for x in range(int(X0B) + 30, int(X1B) - 20, 55):
        if any(abs(x - sx) < 20 for sx in STREETS):
            continue
        zones.append({'id': '09_dune_walk_%d' % x, 'kind': 'boardwalk', 'poly_line': P([(x, PARK_BOT + 1), (x, DUNE_BOT - 3)]), 'width_m': 2.4, 'surface': 'boards_pier_SK5a_v02'})
    zones.append({'id': '09_pier', 'kind': 'pier', 'poly': P([(1007, 221), (1017, 221), (1017, 128), (1007, 128)]), 'surface': 'boards_pier_SK5a_v02', 'fishermen': True})
    zones.append({'id': '09_pier_head', 'kind': 'pier', 'poly': P([(997, 128), (1027, 128), (1027, 116), (997, 116)]), 'surface': 'boards_pier_SK5a_v02'})
    for cx in (1100.0, 1124.0):
        zones.append({'id': '09_volley_%d' % int(cx), 'kind': 'volleyball', 'poly': P([(cx - 8, 186), (cx + 8, 186), (cx + 8, 194), (cx - 8, 194)]), 'net': P([(cx, 185), (cx, 195)])})
    props, buildings = [], []
    for row, y in enumerate((249.0, 243.0, 236.0, 231.5)):
        for x in range(int(X0B) + 5 + (row % 2) * 4, int(X1B) - 3, 8):
            if any(abs(x - sx) < 9 for sx in STREETS) or abs(y - 240 - 6 * math.sin((x - X0B) / 31.0)) < 3.5 or any(l0 - 3 < x < l1 + 3 for l0, l1 in LOTS):
                continue
            props.append({'id': '09_palm_%d_%d' % (row, x), 'kind': 'palm', 'pos': rnd2(post((x, y))), 'jitter_m': 1.5})
    for q in ((947, 214), (963, 214), (1060, 214), (1076, 214), (800, 205), (1235, 204)):
        props.append({'id': '09_palm_bar_%d' % q[0], 'kind': 'palm', 'pos': rnd2(post(q))})
    FOOT_B = [(1236, 238), (1262, 244), (1282, 248), (1300, 254), (1322, 259), (1350, 263), (1400, 267), (1440, 270), (1466, 265)]
    acc, k = 0.0, 0
    for (ax, ay), (bx, by) in zip(FOOT_B[:-1], FOOT_B[1:]):
        L = math.hypot(bx - ax, by - ay)
        while acc < L:
            u = acc / L
            props.append({'id': '09_palm_elite_row_%02d' % k, 'kind': 'palm', 'pos': rnd2(post((ax + (bx - ax) * u, ay + (by - ay) * u)))})
            acc += 9.0
            k += 1
        acc -= L
    TOWERS = [(830, 200), (905, 191), (968, 184), (1062, 184), (1150, 196), (1218, 203)]
    for k, (x, y) in enumerate(TOWERS):
        props.append({'id': '09_lifeguard_%d' % k, 'kind': 'lifeguard_tower', 'pos': rnd2(post((x, y))), 'size': [3, 3, 4], 'grip_anchor': True})
    n = 0
    for bx, by, nx, ny in ((808, 213, 6, 2), (925, 213, 7, 2), (1040, 213, 8, 2), (1170, 213, 6, 2)):
        for i in range(nx):
            for j in range(ny):
                props.append({'id': '09_lounger_%02d' % n, 'kind': 'lounger_umbrella', 'pos': rnd2(post((bx + i * 6.5, by - j * 6.5)))})
                n += 1
    from common import chaikin
    coast_b = [(642, 62), (650, 76), (654, 90), (664, 116), (684, 146), (712, 168), (750, 182), (800, 186), (860, 178), (900, 170), (960, 163),
               (1020, 157), (1060, 161), (1100, 169), (1140, 178), (1190, 186), (1225, 191), (1255, 186), (1290, 188), (1330, 197), (1370, 207),
               (1410, 215), (1450, 224), (1482, 236), (1502, 250), (1512, 266)]   # build_world_v76.py l.1239 (v74 wider to Elite)
    cb = chaikin(coast_b, 3)

    def coast_at(x):
        for (ax, ay), (bx, by) in zip(cb[:-1], cb[1:]):
            if ax <= x <= bx:
                return ay + (by - ay) * (x - ax) / max(1e-6, bx - ax)
        return cb[-1][1]
    zones.append({'id': '09_waterline', 'kind': 'shoreline', 'poly_line': [rnd2(post(p)) for p in cb], 'wet_sand_m': 1.5})
    for k, x in enumerate(range(1424, 1484, 8)):                 # Elite beach: two rows of loungers with umbrellas at the water
        for j, off in enumerate((9.0, 17.0)):
            props.append({'id': '09_elite_lounger_%02d_%d' % (k, j), 'kind': 'lounger_umbrella_elite', 'pos': rnd2(post((x + 4 * j, coast_at(x + 4 * j) + off)))})
    buildings += [{'id': '09_bar_%d' % int(bx), 'kind': 'beach_bar', 'footprint': [rnd2(p) for p in ccw([post(q) for q in ((bx - 8, DUNE_BOT - 9), (bx + 8, DUNE_BOT - 9), (bx + 8, DUNE_BOT - 1), (bx - 8, DUNE_BOT - 1))])],
                   'floors': 1, 'floor_h_m': 3.4, 'height_m': 3.4, 'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.3}, 'walls': 'stucco_SK3b', 'tint': '#F2E3C6',
                   'entrances': [], 'facade_kit': 'none', 'sockets': {'awning': True}, 'collider': 'full_roof', 'notes': 'pastel art-deco bar at the dunes'} for bx in (955.0, 1068.0)]
    buildings.append({'id': '09_elite_cabana', 'kind': 'beach_bar', 'footprint': [rnd2(p) for p in ccw([post(q) for q in ((1406, 242), (1418, 242), (1418, 250), (1406, 250))])],
                      'floors': 1, 'floor_h_m': 3.0, 'height_m': 3.0, 'roof': {'type': 'flat', 'material': 'boards_SK5a', 'parapet_h_m': 0.0}, 'walls': 'boards_SK5a', 'tint': '#F4EFE4',
                      'entrances': [], 'facade_kit': 'none', 'sockets': {}, 'collider': 'full_roof', 'notes': 'cabana bar of the Elite beach (open canopy)'})
    zones.append({'id': '09_van_track', 'kind': 'track', 'note': 'see roads_v76.json beach_van_track'})
    return {'district': 'beach', 'sources': ['ArtSource/References/Map/World_v76/build_world_v76.py l.1246-1375', 'docs/specs BEACH_SPEC v01'],
            'transform': 'build_world_v76 pre-shift metres -> common.post', 'pad_height_m': None, 'buildings': buildings, 'props': props, 'zones': zones,
            'open': ['lifeguard towers: 6 on the map vs <= 2 in BEACH_SPEC (handoff v02 §16)', 'palm jitter / single towels use the script RNG (not reproducible) — positions are the un-jittered grid',
                     '~70 loungers: 54 city + 16 Elite here; scattered towels (60) to be placed by the builder on free sand']}


# ---------------------------------------------------------------- overlay check
def overlay(dist, name):
    from PIL import ImageDraw
    im = Image.open(PREVIEW).convert('RGB')
    xs = [p[0] for b in dist['buildings'] for p in b['footprint']] + [z['poly'][0][0] for z in dist['zones'] if 'poly' in z]
    ys = [p[1] for b in dist['buildings'] for p in b['footprint']] + [z['poly'][0][1] for z in dist['zones'] if 'poly' in z]
    x0, x1, y0, y1 = int(min(xs)) - 20, int(max(xs)) + 20, int(min(ys)) - 20, int(max(ys)) + 20
    S = 3
    crop = im.crop((x0, 950 - y1, x1, 950 - y0)).resize(((x1 - x0) * S, (y1 - y0) * S))
    d = ImageDraw.Draw(crop)
    T = lambda p: ((p[0] - x0) * S, (y1 - p[1]) * S)
    for z in dist['zones']:
        if 'poly' in z:
            d.polygon([T(p) for p in z['poly']], outline=(0, 160, 255))
        if 'poly_line' in z:
            d.line([T(p) for p in z['poly_line']], fill=(255, 140, 0), width=2)
    for b in dist['buildings']:
        d.polygon([T(p) for p in b['footprint']], outline=(255, 0, 0))
    for p in dist['props']:
        if 'pos' in p:
            q = T(p['pos'])
            d.ellipse((q[0] - 2, q[1] - 2, q[0] + 2, q[1] + 2), fill=(200, 0, 200))
    crop.save(os.path.join(WORK, 'check_%s.png' % name))


def main():
    for name, fn in (('downtown', downtown), ('elite', elite), ('beach', beach)):
        dist = fn()
        save_json('districts/%s_v76.json' % name, dist)
        overlay(dist, name)
        print(name, len(dist['buildings']), 'buildings', len(dist['props']), 'props', len(dist['zones']), 'zones')


if __name__ == '__main__':
    main()
