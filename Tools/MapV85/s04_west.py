"""Step 4 / west districts: Hamlet (02, plan v07 / layout v06), Forest (01), Quiet Valley (08) -> world v85 district data
(lead brief "Map W85 build", CL-MAP85, 2026-10-21). Reads the sources, never writes them.

Authority (handoff v10 §0-§1, §6, §7.1, §7.2, §7.8; v02 §8.1, §8.2, §8.8; HAMLET_SPEC v01):
- Hamlet: every object of `Working/Reviews/Hamlet_2026-10-14/HAMLET_LAYOUT_v06.json` (metres of the v11 world = metres of plan
  Хутор_v07.png, build_hutor_v07.py X0 = 118, Y1 = 618, 10 px/m). The master SVG v85 places hamlet_v07_world.png (5 px/m) at
  <image x, y>, so plan (x, y) -> SVG (x_img + (x - 118) * 5, y_img + (618 - y) * 5) -> world = common.u2w (net +70, 0; the
  post-shift is 0 inside the Hamlet). Fit measured on the v85 FINAL render every run.
- Forest / Quiet Valley: master SVG v85 vectors (groups D01 / district_08 + the connecting L05 / R34 / R38 roads, rocks, river),
  cross-checked against World_v11/WORLD_MAP_v11.json districts 01 / 08 (+70, 0).
- Trees are never copied point by point: designed trees (square table tree, orchard grid) stay props, everything else becomes
  veg_zone polygons + no_tree zones. Drawing artefacts are fixed and logged ("fixed_by_logic"), gameplay-level changes are asked
  ("questions_for_vadim").

Outputs: Data/<REV>/districts/{hamlet,forest,quiet_valley}_v85.json, out_<REV>/check_{hamlet,forest,quiet_valley}.png
(preview 1 px/m crop x3: footprints red, entrances blue, props magenta, zones cyan, vegetation green, lines / road bands yellow-green,
fence purple, gates orange). Run: python s04_west.py (deterministic, ~20 s).
"""
import json
import math
import os
import re

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

from common import (MAP_FULL, MAP_PREVIEW, REF, ROOT, WORK, WIDTH, area, attr, ccw, centroid, contour, inside, nearest_on, num, u2m,
                    plen, points_of, poly_mask, rnd2, rrect, save_json, seg_dist, svg_tags, svg_text, u2w)

Image.MAX_IMAGE_PIXELS = None
HAMLET_JSON = os.path.join(ROOT, 'Working', 'Reviews', 'Hamlet_2026-10-14', 'HAMLET_LAYOUT_v06.json')
HUTOR_PY = os.path.join(REF, 'World_v83', 'Districts', 'build_hutor_v07.py')
V11_JSON = os.path.join(REF, 'World_v11', 'WORLD_MAP_v11.json')
REL = lambda p: os.path.relpath(p, ROOT).replace(os.sep, '/')

LOG = {}                                                                   # district -> {'fix': [], 'q': []}

# W86 (Vadim 22.10 "hills badly placed, too flat"; Fedya "the village should be more hilly"): designed Hamlet relief, built by s03 BEFORE
# the plots / fields / yards / streets are flattened (they stay flat, as terraces on the slopes). Base: the 5 terrain_feature polygons of
# HAMLET_LAYOUT_v04 (world = layout + (70, 0)) - each re-fitted to the v06 houses (they stood on v04 house places) - plus 6 new ones.
# Every hill has a role (separates house groups / frames the pond and the church / viewpoint); crest polyline + half width, smoothstep
# profile, height varies +-15 % along the crest (s03), micro relief 0.3-1.5 m comes from the world field. Heights relative to the ground.
HAMLET_TERRAIN = [
    ('02-TR-north_fold', 'hill', [(268, 620), (318, 628), (372, 624)], 32, 4.6, 'v04 02-TR-north_fold +3.8 (moved ~35 m north: v06 houses on its place)',
     'северная складка под хребтом: закрывает деревню с севера, северный ряд домов стоит на её подножии; с гребня вид на крыши и пруд'),
    ('02-TR-field_knoll', 'hill', [(398, 606), (430, 612)], 22, 3.4, 'new',
     'бугор над полем 1: обрамляет поле с севера и отделяет его от ручья'),
    ('02-TR-church_rise', 'hill', [(205, 590), (248, 592)], 34, 2.0, 'new',
     'церковь и кладбище на пологом подъёме над главной улицей - церковь видна с площади'),
    ('02-TR-pond_west_hill', 'hill', [(176, 450), (182, 476), (188, 500)], 28, 5.6, 'new (hill with a rock drawn on map v85)',
     'холм с камнем к западу от пруда (нарисован на карте): обрамляет пруд, отделяет западные дома от леса и осыпей'),
    ('02-TR-base2_swell', 'hill', [(170, 522), (174, 552)], 18, 2.5, 'new',
     'увал у подножия хребта за двором деда: закрывает задний двор базы 2; с него вид на пруд'),
    ('02-TR-west_hollow', 'dip', [(286, 440), (264, 434), (244, 428)], 12, -1.2, 'v04 02-TR-west_hollow -1.4 (moved south of the pond: v06 houses H23/H24 on its place)',
     'ложбина стока из пруда к полю 2: весной сырая, бусик проезжает'),
    ('02-TR-central_rise', 'hill', [(326, 452), (376, 456)], 32, 2.6, 'v04 02-TR-central_rise +2.6 (re-fitted to the v06 loop block)',
     'центральные дома на низком подъёме внутри петли: улицы огибают его, от площади вид вверх на дворы'),
    ('02-TR-east_knoll', 'hill', [(430, 490), (437, 512), (434, 532)], 19, 2.8, 'v04 02-TR-east_rise +3.4 (moved to the free ground between the two streets at the bypass)',
     'бугор между двумя улицами у объездной: прикрывает асфальт и машины от деревни'),
    ('02-TR-south_swell', 'hill', [(332, 352), (372, 360), (414, 352)], 30, 4.2, 'v04 02-TR-south_ripple +1.5 (moved to the forest edge, raised: v06 houses H20-H22 on its place)',
     'южный увал у кромки леса: закрывает деревню с юга, точка обзора на крыши; лесная дорога обходит его по западному краю'),
    ('02-TR-green_hollow', 'dip', [(380, 527), (414, 530)], 10, -1.0, 'new',
     'сырая ложбина на лугу между площадью и полем 1'),
    ('02-TR-sw_swell', 'hill', [(172, 388), (182, 414)], 24, 3.4, 'new',
     'увал к западу от поля 2: отделяет поле от леса и берега'),
]


def fix(dist, where, ru, why):
    L = LOG.setdefault(dist, {'fix': [], 'q': []})['fix']
    L.append({'id': '%s-%02d' % (dist, len(L) + 1), 'where': rnd2(where), 'ru': ru, 'why_ru': why})


def question(dist, ru, options, default, applied):
    L = LOG.setdefault(dist, {'fix': [], 'q': []})['q']
    L.append({'id': '%s-q%d' % (dist, len(L) + 1), 'ru': ru, 'options_ru': options, 'default': default, 'applied': applied})


# ---------------------------------------------------------------- geometry helpers (local; common.py is shared)
def R(pts):
    return [rnd2(p) for p in pts]


def clean(pl, tol=0.05):
    """Drop consecutive duplicate points (SVG polylines repeat points; zero-length segments break buffers)."""
    out = [tuple(pl[0])]
    for p in pl[1:]:
        if math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(tuple(p))
    return out


def poly_d(p, poly):
    n = len(poly)
    return min(seg_dist(p, poly[i], poly[(i + 1) % n])[0] for i in range(n))


def buffer_line(pl, w, cap=True):
    """Miter buffer of a polyline (half width w) as a CCW polygon; ends extended by w when cap (same as s04_rough)."""
    pts = clean([tuple(map(float, p)) for p in pl])

    def unit(a, b):
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1e-9
        return ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    if cap:
        d0, d1 = unit(pts[1], pts[0]), unit(pts[-2], pts[-1])
        pts[0] = (pts[0][0] + d0[0] * w, pts[0][1] + d0[1] * w)
        pts[-1] = (pts[-1][0] + d1[0] * w, pts[-1][1] + d1[1] * w)
    L_, R_ = [], []
    for i, p in enumerate(pts):
        ds = []
        if i > 0:
            ds.append(unit(pts[i - 1], p))
        if i < len(pts) - 1:
            ds.append(unit(p, pts[i + 1]))
        ns = [(-d[1], d[0]) for d in ds]
        m = (sum(n[0] for n in ns), sum(n[1] for n in ns))
        Lm = math.hypot(*m) or 1e-9
        m = (m[0] / Lm, m[1] / Lm)
        s = w / max(0.3, m[0] * ns[0][0] + m[1] * ns[0][1])
        L_.append((p[0] + m[0] * s, p[1] + m[1] * s))
        R_.append((p[0] - m[0] * s, p[1] - m[1] * s))
    poly = R_ + L_[::-1]
    return poly if area(poly) > 0 else poly[::-1]


def ellipse(c, rx, ry, n=16, rot=0.0):
    a = math.radians(rot)
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((c[0] + x * math.cos(a) - y * math.sin(a), c[1] + x * math.sin(a) + y * math.cos(a)))
    return out


def hull(pts):
    P = sorted(set((round(p[0], 3), round(p[1], 3)) for p in pts))
    if len(P) < 3:
        return P

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in P:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(P):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def grow_poly(poly, d):
    """Offset a convex-ish CCW polygon outwards by d (vertex normals)."""
    poly = ccw(poly)
    n = len(poly)
    out = []
    for i in range(n):
        a, b, c_ = poly[i - 1], poly[i], poly[(i + 1) % n]
        n1 = (b[1] - a[1], -(b[0] - a[0]))
        n2 = (c_[1] - b[1], -(c_[0] - b[0]))
        l1, l2 = math.hypot(*n1) or 1e-9, math.hypot(*n2) or 1e-9
        m = (n1[0] / l1 + n2[0] / l2, n1[1] / l1 + n2[1] / l2)
        lm = math.hypot(*m) or 1e-9
        out.append((b[0] + m[0] / lm * d, b[1] + m[1] / lm * d))
    return out


def edge_door(poly, target, keep_pt=None, long_only=False):
    """Door on the footprint edge: nearest edge to keep_pt (snapped) or the edge whose outward normal faces target.
    Returns (pos, facing_deg); the door stays >= 1 m from the corners."""
    poly = ccw(poly)
    n = len(poly)
    best = None
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1.0 or (long_only and L < 0.99 * max(math.dist(poly[j], poly[(j + 1) % n]) for j in range(n))):
            continue
        nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L               # outward normal of a CCW edge
        ref = keep_pt if keep_pt is not None else target
        d, q, t = seg_dist(ref, a, b)
        if keep_pt is not None:
            score = d
        else:
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            vx, vy = target[0] - mid[0], target[1] - mid[1]
            dd = math.hypot(vx, vy) or 1e-9
            score = -(vx * nx + vy * ny) / dd + 0.02 * dd
        if best is None or score < best[0]:
            mg = min(0.5, 1.0 / L)
            t = 0.5 if long_only else min(max(t, mg), 1 - mg)
            best = (score, (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), math.degrees(math.atan2(ny, nx)) % 360)
    return best[1], round(best[2], 1)


def long_axis_deg(poly):
    e = [(poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly))]
    a, b = max(e, key=lambda ab: math.hypot(ab[1][0] - ab[0][0], ab[1][1] - ab[0][1]))
    return round(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180, 1)


def seg_inter(p1, p2, p3, p4):
    d = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (p4[0] - p3[0])
    if abs(d) < 1e-12:
        return None
    t = ((p3[0] - p1[0]) * (p4[1] - p3[1]) - (p3[1] - p1[1]) * (p4[0] - p3[0])) / d
    u = ((p3[0] - p1[0]) * (p2[1] - p1[1]) - (p3[1] - p1[1]) * (p2[0] - p1[0])) / d
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
    return None


def crossings(pl, loop):
    out = []
    for a, b in zip(pl[:-1], pl[1:]):
        for i in range(len(loop) - 1):
            q = seg_inter(a, b, loop[i], loop[i + 1])
            if q:
                out.append(q)
    return out


def polys_overlap(a, b):
    if any(inside(p, b) for p in a) or any(inside(p, a) for p in b):
        return True
    return any(seg_inter(a[i], a[(i + 1) % len(a)], b[j], b[(j + 1) % len(b)]) for i in range(len(a)) for j in range(len(b)))


def snap_end(pl, end, target_pl):
    """Move the end point of pl onto the axis of target_pl (keeps a straight last segment)."""
    d, q, i, t = nearest_on(target_pl, pl[end])
    pl = [list(p) for p in pl]
    pl[end] = [q[0], q[1]]
    return pl, d


# ---------------------------------------------------------------- master SVG world objects for the west
def svg_west():
    s = svg_text()
    img = re.search(r'<image[^>]*C_hamlet_v07_world\.png"[^>]*>', s)
    assert img, 'hamlet image not in the master SVG v85'
    out = {'hamlet_img': tuple(float(attr(img.group(0), k)) for k in ('x', 'y', 'width', 'height')),
           'd01': [], 'd08': [], 'links': [], 'bypass': None, 'rocks': None, 'river': None, 'svg_text_len': len(s)}
    for nm, at, M, gids, a, b in svg_tags(s):
        st, fl, sw = (attr(at, 'stroke') or '').upper(), (attr(at, 'fill') or '').upper(), num(at, 'stroke-width', 0.0)
        if nm in ('polyline', 'polygon'):
            pts = [u2w(*p) for p in points_of(at, M)]
            if not pts:
                continue
            if nm == 'polyline':
                pts = clean(pts)
            rec = (gids[-1] if gids else "", nm, fl, st, sw, pts)
            if 'D01' in gids:
                out['d01'].append(rec)
            elif 'D08' in gids:
                out['d08'].append(rec)
            elif gids and gids[-1] == 'L05_roads' and st == '#E5D2A4':
                out['links'].append(pts)
            elif gids and gids[-1] == 'R52_bypass' and st == '#5F666C':
                out['bypass'] = pts
            elif gids and gids[-1] == 'R34_sharp_rocks' and fl == '#B9BCB4' and st == '#8E938A':
                out['rocks'] = pts
            elif gids and gids[-1] == 'R38_river_mouth' and st == '#97C8DC':
                out['river'] = (pts, sw / 5.0)
        elif nm == 'circle' and ('D01' in gids or 'D08' in gids):
            cx_, cy_ = num(at, 'cx'), num(at, 'cy')
            c = u2w(M[0] * cx_ + M[2] * cy_ + M[4], M[1] * cx_ + M[3] * cy_ + M[5])
            (out['d01'] if 'D01' in gids else out['d08']).append((gids[-1], 'circle', (attr(at, 'fill') or '').upper(), st, num(at, 'r') / 5.0, c))
    assert out['bypass'] and out['rocks'] and out['river'], 'master SVG v85 layout changed (bypass / rocks / river)'
    return out


# ---------------------------------------------------------------- render fit
def render_fit(polys, rgb, tol, box, inset=0.6):
    """Share of footprint pixels (inset) on the drawn fill colour of VOLUNTEERS_MAP_FINAL_v85.png + best extra shift (+-2 m, 0.2 m)."""
    x0, y0, x1, y1 = box
    im = Image.open(MAP_FULL).convert('RGB').crop((x0 * 5, (950 - y1) * 5, x1 * 5, (950 - y0) * 5))
    a = np.asarray(im).astype(np.int16)
    fill = np.all(np.abs(a - np.array(rgb)) <= tol, -1)
    pm = Image.new('L', im.size, 0)
    dr = ImageDraw.Draw(pm)
    for p in polys:
        c = centroid(p)
        q = [(c[0] + (v[0] - c[0]) * (1 - inset / max(1.0, math.hypot(v[0] - c[0], v[1] - c[1]))),
              c[1] + (v[1] - c[1]) * (1 - inset / max(1.0, math.hypot(v[0] - c[0], v[1] - c[1])))) for v in p]
        dr.polygon([((v[0] - x0) * 5, (y1 - v[1]) * 5) for v in q], fill=255)
    pred = np.asarray(pm) > 0
    best = None
    for dy in range(-10, 11):
        for dx in range(-10, 11):
            sh = np.roll(np.roll(pred, dy, 0), dx, 1)
            sc = int((sh & fill).sum()) - int((sh & ~fill).sum())
            if best is None or sc > best[0]:
                best = (sc, dx, dy)
    frac = float((pred & fill).sum()) / max(1.0, float(pred.sum()))
    return {'on_fill_share': round(frac, 3), 'best_extra_shift_m': [best[1] / 5.0, -best[2] / 5.0],
            'residual_m': round(math.hypot(best[1], best[2]) / 5.0, 2)}


# ================================================================ HAMLET
HOUSE = {   # house_type -> walls, material_slot, roof material, ridge cap
    'old_log': ('logs_SK5b', 'hamlet_house_log', 'roof_wavy_slate', 'slate'),
    'timber_log': ('logs_SK5b', 'hamlet_house_log', 'roof_wavy_slate', 'slate'),
    'old_board': ('boards_SK5a', 'hamlet_house_board', 'roof_wavy_slate', 'slate'),
    'abandoned_board': ('boards_SK5a', 'hamlet_house_board', 'roof_wavy_slate', 'slate'),
    'tin_timber': ('boards_SK5a', 'hamlet_house_board', 'roof_profsheet_SK4c', 'metal'),
    'brick': ('brick_SK3a', 'hamlet_house_brick', 'roof_tile_SK4a', 'tile')}
OUTB = {    # kind -> (out kind, slot, walls, roof type, roof material, height, ridge)
    'shed': ('shed', 'hamlet_shed', 'boards_SK5a', 'shed', 'roof_profsheet_SK4c', 2.4, 0.5),
    'chicken_coop': ('chicken_coop', 'hamlet_shed', 'boards_SK5a', 'shed', 'roof_profsheet_SK4c', 1.8, 0.4),
    'pig_shelter': ('pig_shelter', 'hamlet_shed', 'boards_SK5a', 'shed', 'roof_wavy_slate', 1.6, 0.4),
    'hay_shelter': ('hay_shelter', 'hamlet_shed', 'logs_SK5b', 'gable', 'roof_profsheet_SK4c', 4.0, 1.5),
    'water_tower': ('water_tower', 'hamlet_water_tower', 'brick_SK3a', 'pyramid', 'roof_profsheet_SK4c', 12.0, 1.5),
    'bus_stop': ('bus_stop', 'generic_concrete', 'concrete_SK3c', 'shed', 'roof_profsheet_SK4c', 2.4, 0.2)}
ZONE = {    # layout kind -> (zone kind, surface)
    'yard': ('yard', 'worn_grass_L02'), 'open_working_grass': ('yard', 'worn_grass_L02'), 'vegetable_garden': ('vegetable_garden', 'field_plowed'),
    'overgrown_beds': ('overgrown_beds', 'lawn'), 'flower_strip': ('flower_strip', 'lawn'), 'mud_patch': ('decal_patch', 'dirt_SK1b'),
    'dung_patch': ('decal_patch', 'dirt_SK1b'), 'village_square': ('plaza', 'dirt_SK1b'), 'van_loading_pad': ('loading_pad', 'gravel_SK1d'),
    'manoeuvring_apron': ('apron', 'gravel_SK1d'), 'cemetery': ('cemetery', 'lawn'), 'orchard': ('orchard', 'lawn'), 'pond': ('pond', 'water'),
    'small_pig_pen': ('pig_pen', 'dirt_SK1b'), 'fishing_platform': ('fishing_platform', 'boards_SK5a'), 'cultivated_field': ('field', None)}
KEY_PROPS = {'round_hay_bale', 'grave', 'old_well', 'parked_tractor', 'farm_trailer', 'rusted_car', 'upturned_boat', 'fishing_nets',
             'net_drying_rack', 'gathering_table', 'bench', 'pole_lamp', 'chicken_spawn_marker', 'pig_spawn_marker', 'npc_gathering_marker',
             'woodpile', 'clothesline', 'reed_clump', 'tree', 'standpipe'}
GRIP = {'bench', 'pole_lamp', 'outdoor_table', 'gathering_table', 'clothesline', 'standpipe', 'net_drying_rack'}
SPECIES = {'shade': 'leafy', 'fruit': 'leafy', 'willow': 'leafy', 'birch': 'birch', 'oak': 'oak', 'pine': 'pine'}
ROAD_CLASS = {5.4: 'village_main', 4.2: 'village_local', 3.6: 'farm_track'}


def hamlet(W_):
    L = json.load(open(HAMLET_JSON, encoding='utf-8'))
    hp = open(HUTOR_PY, encoding='utf-8').read()
    m = re.search(r'X0, X1, Y0, Y1 = ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+)', hp)
    X0, X1, Y0, Y1 = map(float, m.groups())
    ix, iy, iw, ih = W_['hamlet_img']
    k = iw / (X1 - X0)
    assert abs(ih / (Y1 - Y0) - k) < 1e-6 and abs(k - 5.0) < 1e-6, (iw, ih, k)

    shifts = [0.0]

    def T(p):
        X, Y = ix + (p[0] - X0) * k, iy + (Y1 - p[1]) * k
        w, m0 = u2w(X, Y), u2m(X, Y)
        shifts[0] = max(shifts[0], math.hypot(w[0] - m0[0], w[1] - m0[1]))
        return w

    def TT(pts):
        return [T(p) for p in pts]
    tr0 = T((0.0, 0.0))
    D = 'hamlet'
    O = L['objects']
    byid = {o['id']: o for o in O}
    # ------------------------------------------------ streets (plan metres), fixes first
    S = {s['id']: {'id': s['id'], 'w': s['width_m'], 'cls': s.get('road_class'), 'pl': [list(map(float, p)) for p in s['polyline_m']], 'src': s.get('source')}
         for s in L['streets']}
    byp_plan = [((p[0] - tr0[0]), (p[1] - tr0[1])) for p in W_['bypass']]          # bypass axis in plan metres (pure translation here)
    for sid, end in (('02-R-main', 0), ('02-R-north', -1)):
        S[sid]['pl'], d = snap_end(S[sid]['pl'], end, byp_plan)
        fix(D, T(S[sid]['pl'][end]), 'Конец улицы %s доведён до оси объездной (асфальт): было не доходит на %.1f м' % (sid, d),
            'v10 §6: ось примыкающей дороги доходит до оси главной, без щели и «обрывка»')
    snapped = []
    for sid, end, tid in (('02-R-church', 0, '02-R-main'), ('02-R-north', 0, '02-R-main'), ('02-R-base', 0, '02-R-main'),
                          ('02-R-mountain_homes', 0, '02-R-base'), ('02-R-forest_homes', 0, '02-R-south'),
                          ('02-R-forest_homes_e', 0, '02-R-south'), ('02-R-mountain_h23', 0, '02-R-mountain_homes'), ('02-R-d16', 0, '02-R-loop')):
        tgt = S[tid]['pl'] if not (sid == '02-R-church') else S[tid]['pl']
        if sid == '02-R-church':                                                # the church lane continues the main street's west end
            d = math.hypot(S[sid]['pl'][0][0] - S[tid]['pl'][-1][0], S[sid]['pl'][0][1] - S[tid]['pl'][-1][1])
            S[sid]['pl'][0] = list(S[tid]['pl'][-1])
        else:
            S[sid]['pl'], d = snap_end(S[sid]['pl'], end, tgt)
        if d > 0.05:
            snapped.append('%s %.1f м' % (sid, d))
    fix(D, T(S['02-R-north']['pl'][0]), 'Начала боковых улиц и подъездов поставлены на ось улицы, к которой примыкают (%s)' % ', '.join(snapped),
        'v10 §6: стык без ступеньки — ось боковой дороги доходит до оси главной; на плане начала висели рядом с осью')
    # field track: field 2 became 40 x 26 m in v06, the track to it ends 12 m short in the grass
    f2 = byid['02-A-FIELD2']['polygon_m']
    fx1 = max(p[0] for p in f2)
    e = S['02-R-field09']['pl'][-1]
    S['02-R-field09']['pl'] += [[fx1 + 4.5, e[1] - 5.0], [fx1 + 0.6, 418.0]]
    fix(D, T((fx1, 418.0)), 'Хоз. трек 02-R-field09 продлён на ~13 м до восточного края пашни (въезд на поле у СВ угла)',
        'в v06 поле уменьшили до 40×26 м, а трек остался кончаться в траве в 12 м от поля — «дорога в никуда» (v10 §6)')
    # drive d12 runs through the pig pen
    pen = byid['02-A-PEN']['polygon_m']
    pen_y0 = min(p[1] for p in pen)
    a, b = S['02-R-d12']['pl']
    t = (pen_y0 - 2.5 - a[1]) / (b[1] - a[1])
    S['02-R-d12']['pl'] = [a, [a[0] + (b[0] - a[0]) * t, pen_y0 - 2.5]]
    fix(D, T(S['02-R-d12']['pl'][-1]), 'Подъезд 02-R-d12 укорочен: кончается у южного края свинарника (2,5 м до загона), а не идёт сквозь загон к H07',
        'на плане полоса подъезда нарисована поверх загона 14×7 м; к двору H07 бусик доезжает по открытой траве вокруг загона (заборов нет)')
    # v06 spurs to H20-H22: the drive ran over H21 and ended inside the house walls
    S['02-R-forest_homes']['pl'] = [S['02-R-forest_homes']['pl'][0], [226.0, 397.6], [226.0, 396.6]]
    S['02-R-forest_homes_e']['pl'] = [S['02-R-forest_homes_e']['pl'][0], [252.0, 398.9], [264.5, 395.6], [268.0, 393.2]]
    fix(D, T((252.0, 398.9)), 'Подъезды к H20–H24 (v06) кончаются перед дверью (0,6–1,6 м до стены), а не в стене дома; подъезд к H20–H22 сдвинут на ~2 м к северу',
        'на плане v06 полоса 3,6 м к H21 шла по северной стене дома, концы подъездов к H20 и H22 были на стене')
    S['02-R-mountain_homes']['pl'][-1] = [157.4, 457.0]
    S['02-R-mountain_h23']['pl'][-1] = [149.6, 481.0]
    # ------------------------------------------------ buildings
    B, P, Z = [], [], []
    houses = [o for o in O if o['kind'] == 'house']
    drives = [s for s in S.values() if s['w'] <= 3.7]
    doors_fixed = []
    plan_bld = {}
    for o in O:
        if o['kind'] in ('house', 'grandfather_base', 'church') or o['kind'] in OUTB:
            plan_bld[o['id']] = [tuple(p) for p in o['polygon_m']]
    # v06 sheds of H20-H24 that sit on their own drive -> other corner of the house
    moved = []
    for o in O:
        if o['kind'] == 'shed' and o['id'][:6] in ('02-H20', '02-H21', '02-H22', '02-H23', '02-H24'):
            h = byid[o['id'][:6]]
            cx, cy = h['centre_m']

            def bad(poly):
                if any(min(nearest_on(s['pl'], p)[0] for p in poly + [centroid(poly)]) < s['w'] / 2 + 0.8 for s in S.values()):
                    return True
                return any(polys_overlap(poly, q['polygon_m']) for q in O if q is not o and q.get('polygon_m') and q['kind'] in
                           ('house', 'shed', 'vegetable_garden', 'pond', 'cultivated_field'))
            if bad(o['polygon_m']):
                for dx, dy in ((6.5, -4.5), (-6.5, 4.5), (-6.5, -4.5), (0.0, -6.5), (8.5, 0.0), (-8.5, 0.0)):
                    q = rrect((cx + dx, cy + dy), 3.2, 2.8, 0)
                    if not bad(q):
                        o = dict(o, polygon_m=[list(v) for v in q], centre_m=[cx + dx, cy + dy])
                        moved.append(o['id'])
                        byid[o['id']] = o
                        break
    O = [byid[o['id']] for o in O]
    if moved:
        fix(D, T(byid[moved[0]]['centre_m']), 'Сараи %s (добавлены в v06 стандартно в СВ углу участка) переставлены в другой угол своего участка' % ', '.join(moved),
            'на плане сарай стоял на собственном подъезде 3,6 м')
    for o in O:
        k_ = o['kind']
        if k_ == 'house':
            ht = o.get('house_type') or ('timber_log' if o.get('material') == 'timber_log' else 'old_log')
            walls, slot, rmat, cap = HOUSE[ht]
            fp = [tuple(p) for p in o['polygon_m']]
            dp = o.get('door_m')
            cen = centroid(fp)
            dd, tgt = min(((min(math.hypot(s['pl'][-1][0] - v[0], s['pl'][-1][1] - v[1]) for v in fp + [cen]), s['pl'][-1]) for s in drives),
                          key=lambda x: x[0])
            if dd <= 9.0:                                                   # a drive ends at this house: the door faces it
                pos, fac = edge_door(fp, tgt)
            elif dp and poly_d(dp, fp) <= 1.5:
                pos, fac = edge_door(fp, None, keep_pt=dp)
            else:
                pos, fac = edge_door(fp, min((nearest_on(s['pl'], cen)[:2] for s in S.values()), key=lambda x: x[0])[1])
            if not dp or math.dist(pos, dp) > 1.6:
                doors_fixed.append(o['id'] + ('' if not dp else ' (сдвиг %.0f м)' % math.dist(pos, dp)))
            wf = [T(p) for p in fp]
            B.append({'id': o['id'], 'kind': 'house', 'material_slot': slot, 'footprint': R(ccw(wf)), 'floors': 1, 'floor_h_m': 2.8, 'height_m': 3.0,
                      'roof': {'type': 'gable', 'material': rmat, 'ridge_axis_deg': long_axis_deg(wf), 'ridge_h_m': 2.4, 'overhang_m': 0.4},
                      'walls': walls, 'tint': None,
                      'entrances': [{'pos': rnd2(T(pos)), 'facing_deg': fac, 'kind': 'door', 'w_m': 1.0, 'porch': True, 'benches': 0}],
                      'facade_kit': 'hamlet',
                      'sockets': {'balconies': 'none', 'windows': True, 'window_tex': 'Facade_Hamlet_wood', 'shutters': True, 'porch_roof': True,
                                  'chimney': True, 'gutter': True, 'fire_escape': False, 'ac_units': 0, 'water_tank': False, 'awning': False,
                                  'storefront': False, 'ridge_cap': cap, 'broken_windows': ht == 'abandoned_board'},
                      'collider': 'full_roof', 'house_type': ht, 'abandoned': ht == 'abandoned_board', 'owner': o.get('owner'),
                      'yard_profile': o.get('yard_profile'), 'interior': bool(o.get('accessible_interior')),
                      'notes': '; '.join(x for x in (o.get('notes'), 'layout roof: %s' % o.get('roof_material') if o.get('roof_material') else None,
                                                     'roof per HAMLET_SPEC §3 (slate S-4; tin_timber = sheet metal, brick = tile)', o.get('source')) if x)})
        elif k_ in ('grandfather_base', 'church'):
            fp = [tuple(p) for p in o['polygon_m']]
            if k_ == 'grandfather_base':
                pos, fac = edge_door(fp, byid['02-A-BASE-PAD']['centre_m'])
                B.append({'id': o['id'], 'kind': 'hut_base2', 'base': 2, 'material_slot': 'hamlet_base2', 'footprint': R(ccw(TT(fp))), 'floors': 1,
                          'floor_h_m': 2.8, 'height_m': 3.0,
                          'roof': {'type': 'gable', 'material': 'roof_wavy_slate', 'ridge_axis_deg': long_axis_deg(TT(fp)), 'ridge_h_m': 2.4, 'overhang_m': 0.5},
                          'walls': 'logs_SK5b', 'tint': None,
                          'entrances': [{'pos': rnd2(T(pos)), 'facing_deg': fac, 'kind': 'door', 'w_m': 1.1, 'porch': True, 'police_stop': True}],
                          'facade_kit': 'hamlet', 'sockets': {'balconies': 'none', 'windows': True, 'window_tex': 'Facade_Hamlet_wood', 'shutters': True,
                                                              'porch_roof': True, 'chimney': True, 'ridge_cap': 'slate'},
                          'collider': 'full_roof', 'interior': True,
                          'yard': {'pad': '02-A-BASE-PAD', 'apron': '02-A-BASE-TURN', 'dressing_ref': 'Assets/OnlyVolunteers/Scenes/Map/Map_Look_v19_Play_i09_oaks_pines.unity',
                                   'dressing': ['barrel', 'paint cans + brush (van paint, "ТЦК")', 'red rocking chair of grandpa away from the work spot', 'van pad gravel 9.2 x 9.2 + apron 15 x 14'],
                                   'status': 'exact dressing layout = lead (v10 §7.2, §12 open)'},
                          'notes': (o.get('notes') or '') + ' | HAMLET_SPEC §2: as in Fedya i09, best textures (D-3 boards, B-7 logs, S-4 slate, ground L03)'})
            else:
                pos, fac = edge_door(fp, S['02-R-church']['pl'][-1])
                B.append({'id': o['id'], 'kind': 'church', 'material_slot': 'hamlet_church', 'footprint': R(ccw(TT(fp))), 'floors': 1, 'floor_h_m': 7.0,
                          'height_m': 7.0, 'roof': {'type': 'gable', 'material': 'roof_tile_SK4a', 'ridge_axis_deg': 90.0, 'ridge_h_m': 5.0, 'overhang_m': 0.5},
                          'walls': 'stucco_SK3b', 'tint': '#F2EEE4', 'entrances': [{'pos': rnd2(T(pos)), 'facing_deg': fac, 'kind': 'door', 'w_m': 2.0, 'steps': 2}],
                          'facade_kit': 'hamlet', 'sockets': {'balconies': 'none', 'windows': True, 'bell_tower': True, 'dome': 'small_onion', 'ridge_cap': 'tile'},
                          'collider': 'full_roof', 'notes': 'church 18.4 x 20.6 m, westmost and northmost (v02 §8.2); plaster W-5 (HAMLET_SPEC §3); tower/dome = lead'})
        elif k_ in OUTB:
            ok, slot, walls, rt, rm, hh, rh = OUTB[k_]
            fp = [tuple(p) for p in o['polygon_m']]
            ent = []
            if k_ == 'water_tower':
                pos, fac = edge_door(fp, S['02-R-d_tower']['pl'][-1])
                ent = [{'pos': rnd2(T(pos)), 'facing_deg': fac, 'kind': 'door', 'w_m': 0.9}]
            hh = o.get('height_m') or hh
            B.append({'id': o['id'], 'kind': ok, 'material_slot': slot, 'footprint': R(ccw(TT(fp))), 'floors': 1, 'floor_h_m': hh, 'height_m': hh,
                      'roof': {'type': rt, 'material': rm, 'ridge_axis_deg': long_axis_deg(TT(fp)), 'ridge_h_m': rh, 'overhang_m': 0.3},
                      'walls': walls, 'tint': None, 'entrances': ent, 'facade_kit': 'none',
                      'sockets': {'balconies': 'none', 'windows': False, 'ridge_cap': None, 'open_sides': k_ in ('hay_shelter', 'bus_stop')},
                      'collider': 'full_roof', 'notes': (o.get('notes') or '') + ('' if o.get('height_m') else ' | height by kind (not in layout)')})
    fix(D, B[0]['entrances'][0]['pos'], 'Двери %d домов поставлены на стену, обращённую к своему подъезду/улице: %s' % (len(doors_fixed), ', '.join(doors_fixed)),
        'door_m в раскладке v06 остались от старых домов v04 (в 8–52 м от стены своего дома, часто у чужого дома, у H18 — на стене напротив подъезда); у H20–H24 двери не было')
    # ------------------------------------------------ zones, props, vegetation
    trees = [o for o in O if o['kind'] == 'tree']
    orchard = byid['02-U-ORCHARD']['polygon_m']
    sq = byid['02-SQ']
    designed = {'02-SQ-TREE'} | {o['id'] for o in trees if inside(o['centre_m'], orchard) and o.get('tree_type') == 'fruit'}
    bands = [(s['pl'], s['w'] / 2) for s in S.values()]

    def road_clear(p):
        return min(nearest_on(pl, p)[0] - hw for pl, hw in bands)
    pushed, dropped = [], []
    for o in O:
        k_ = o['kind']
        if k_ in ('house', 'grandfather_base', 'church') or k_ in OUTB:
            continue
        if k_ in ZONE and o.get('polygon_m'):
            zk, surf = ZONE[k_]
            z = {'id': o['id'], 'kind': zk, 'poly': R(ccw(TT(o['polygon_m']))), 'surface': surf}
            if k_ == 'cultivated_field':
                ft = o.get('field_type')
                z.update({'surface': 'field_plowed' if ft == 'plowed' else 'field_stubble', 'field_type': ft, 'size_m': o.get('size_m'),
                          'flat': True, 'furrow_step_m': o.get('furrow_step_m', 2.5), 'furrow_dir_deg': 0.0, 'balk': {'w_m': 1.5, 'surface': 'lawn'},
                          'driveable': True, 'notes': 'v10 §7.2: flat, smaller (stubble 32 x 26 / plough 40 x 26 m) with a grassy balk; drivable, shakes the van'})
            elif k_ == 'pond':
                z.update({'van_blocked': True, 'reeds': True, 'water_lilies': True, 'notes': 'pond: reeds, lilies, van does not pass (v02 §8.2)'})
            elif k_ == 'small_pig_pen':
                z['rail_fence'] = {'h_m': 1.1, 'material': 'boards_SK5a', 'kind': 'wooden rails', 'gate_w_m': 1.2,
                                   'notes': 'the only fence of the Hamlet: rails of the 14 x 7 m pig pen (v02 §8.2)'}
            elif k_ == 'village_square':
                z.update({'name_ru': 'Площадь: стол под большим деревом', 'npc_gathering': True})
            elif k_ in ('van_loading_pad', 'manoeuvring_apron'):
                z.update({'base': 2, 'flat': True})
            elif k_ in ('mud_patch', 'dung_patch'):
                z['decal'] = k_.split('_')[0]
            elif k_ == 'fishing_platform':
                z.update({'deck_h_m': 0.4, 'notes': (o.get('notes') or '') + ' | mostki 5 x 2 m on the west river bank'})
            elif k_ == 'open_working_grass':
                z.update({'kind': 'meadow_patch', 'surface': None, 'grass': 'taller grass + wildflowers, soft edges, same ground texture as the meadow',
                          'open': True})
            elif k_ == 'yard':
                z.update({'fenced': False})
            if o.get('notes') and 'notes' not in z:
                z['notes'] = o['notes']
            Z.append(z)
            continue
        if k_ == 'pedestrian_path':
            Z.append({'id': o['id'], 'kind': 'footpath', 'line': R(TT(o['polyline_m'])), 'width_m': o.get('width_m', 1.8), 'surface': 'dirt_SK1b',
                      'crosses_road_at_grade': True, 'notes': o.get('notes')})
            continue
        if k_ == 'soft_shrub_cluster':
            w, l = o['size_m'][:2]
            Z.append({'id': o['id'], 'kind': 'veg_zone', 'poly': R(ccw(TT(ellipse(o['centre_m'], w * 0.7, l * 0.7, 12, o.get('rotation_deg') or 0)))),
                      'density': 'grove', 'species': 'bush', 'target_count': 1, 'collider': False, 'notes': 'soft shrub cluster of the layout'})
            continue
        if k_ == 'tree' and o['id'] not in designed:
            continue
        cen = o.get('centre_m') or centroid(o['polygon_m'])
        if k_ not in ('tree', 'reed_clump', 'fishing_nets', 'upturned_boat') and road_clear(cen) < 0.4:
            pl, hw = min(bands, key=lambda b_: nearest_on(b_[0], cen)[0] - b_[1])
            d, q, _, _ = nearest_on(pl, cen)
            nx, ny = ((cen[0] - q[0]) / d, (cen[1] - q[1]) / d) if d > 1e-6 else (0.0, 1.0)
            cen = (q[0] + nx * (hw + 0.6), q[1] + ny * (hw + 0.6))
            pushed.append(o['id'])
        size = (o.get('size_m') or [o.get('crown_diameter_m', 1.0)] * 2)[:2]
        pr = {'id': o['id'], 'kind': k_, 'pos': rnd2(T(cen)), 'rot_deg': o.get('rotation_deg') or 0,
              'size': [round(v, 2) for v in size] + [o.get('height_m') or 0], 'grip_anchor': k_ in GRIP, 'dressing': k_ not in KEY_PROPS}
        if k_ == 'tree':
            pr.update({'species': SPECIES.get(o.get('tree_type'), 'leafy'), 'tree_type': o.get('tree_type'), 'crown_d_m': o.get('crown_diameter_m'),
                       'designed': 'square table tree' if o['id'] == '02-SQ-TREE' else 'orchard grid'})
        if o.get('notes'):
            pr['notes'] = o['notes']
        P.append(pr)
    if pushed:
        fix(D, next(p['pos'] for p in P if p['id'] == pushed[0]), 'Предметы %s отодвинуты с полосы улицы на её край (0,6 м за кромкой)' % ', '.join(pushed),
            'точка детали попала на проезжую часть грунтовки (v10 §8: детали не мешают проезду)')
    mp = [z for z in Z if z['kind'] == 'meadow_patch']
    fix(D, centroid(mp[0]['poly']), '%d «луговых пятен» плана Феди v19 не красятся отдельной заливкой: та же земля луга, только трава выше и цветы, мягкий край' % len(mp),
        'на плане это светлые пятна поверх луга — «картинка на картинке»; Вадим: Хутор вписан в природу без шва (v10 §7.2)')
    # vegetation zones from the free (not designed) layout trees: single-link clusters, hull of the crowns
    free = [o for o in trees if o['id'] not in designed]
    lab = list(range(len(free)))

    def root(i):
        while lab[i] != i:
            lab[i] = lab[lab[i]]
            i = lab[i]
        return i
    for i in range(len(free)):
        for j in range(i + 1, len(free)):
            if math.dist(free[i]['centre_m'], free[j]['centre_m']) < 9.0:
                lab[root(i)] = root(j)
    groups = {}
    for i in range(len(free)):
        groups.setdefault(root(i), []).append(free[i])
    for n_, g in enumerate(sorted(groups.values(), key=lambda g: (g[0]['centre_m'][0], g[0]['centre_m'][1]))):
        pts = []
        for o in g:
            r_ = o.get('crown_diameter_m', 5.0) / 2 + 0.5
            pts += ellipse(o['centre_m'], r_, r_, 12)
        sp = {}
        for o in g:
            sp[o.get('tree_type') or 'shade'] = sp.get(o.get('tree_type') or 'shade', 0) + 1
        main = max(sp, key=sp.get)
        Z.append({'id': '02-veg%02d' % (n_ + 1), 'kind': 'veg_zone', 'poly': R(ccw(TT(hull(pts)))), 'density': 'grove' if len(g) >= 3 else 'sparse',
                  'species': SPECIES.get(main, 'leafy'), 'mix': sp, 'target_count': len(g),
                  'notes': 'replaces %d layout tree points (%s); s05 places them freely, mixed ages, >= 3 m from facades, never on drives' % (len(g), ', '.join(o['id'] for o in g))})
    fix(D, T(sq['centre_m']), 'Деревья раскладки (%d точек) не перенесены поштучно: %d групп veg_zone (+ кусты 32 зоны); пропсами оставлены только '
        'дерево над столом площади и сетка сада (%d)' % (len(free), len(groups), len(designed) - 1),
        'v10 §1.2: деревья — зонами плотности, кроме задуманных (стол под деревом, сад)')
    # streets (world)
    ncls = {}
    for s in S.values():
        cls = ROAD_CLASS[min(ROAD_CLASS, key=lambda w: abs(w - s['w']))]
        ncls[cls] = ncls.get(cls, 0) + 1
        Z.append({'id': s['id'], 'kind': 'street', 'line': R(TT(s['pl'])), 'width_m': WIDTH[cls], 'road_class': cls, 'surface': 'dirt_SK1b',
                  'ruts': True, 'grass_centre': True, 'puddles': True, 'kerb': False, 'markings': False, 'lamps': False,
                  'end_caps': 'rounded at places (house, pad, field, church, tower)', 'layout_class': s['cls'], 'source': s['src'],
                  'notes': 'v10 §6: two ruts with grass in the middle and puddles; drains into the meadow, no edging'})
    # church forecourt: the church lane ends 9 m before the church door
    ce = S['02-R-church']['pl'][-1]
    cd = byid['02-A-CHURCH']['polygon_m']
    cy0 = min(p[1] for p in cd)
    Z.append({'id': '02-church-forecourt', 'kind': 'plaza', 'poly': R(ccw(TT([(ce[0] - 5.0, ce[1] - 1.5), (ce[0] + 5.0, ce[1] - 1.5), (ce[0] + 5.0, cy0), (ce[0] - 5.0, cy0)]))),
              'surface': 'dirt_SK1b', 'notes': 'trodden earth in front of the church door: the church lane ends here (HAMLET_SPEC §2 roads end at a place)'})
    fix(D, T((ce[0], (ce[1] + cy0) / 2)), 'Перед дверью церкви добавлена утоптанная площадка 10×9 м от конца проезда до двери',
        'проезд к церкви на плане кончается в 9 м от стены в траве; дорога должна упираться в место (HAMLET_SPEC §2)')
    # no_tree
    nt = []
    for s in S.values():
        nt.append((s['id'], buffer_line(s['pl'], s['w'] / 2 + 2.0), 'street / drive + 2 m (v10 §1.2)'))
    for o in O:
        if o['kind'] in ('cultivated_field', 'vegetable_garden', 'village_square', 'van_loading_pad', 'manoeuvring_apron', 'cemetery', 'small_pig_pen', 'pond'):
            nt.append((o['id'], o['polygon_m'], {'cultivated_field': 'field', 'vegetable_garden': 'vegetable garden', 'village_square': 'square (table tree is a prop)',
                                                  'van_loading_pad': 'van pad base 2', 'manoeuvring_apron': 'van apron base 2', 'cemetery': 'cemetery graves and paths',
                                                  'small_pig_pen': 'pig pen', 'pond': 'water'}[o['kind']]))
    for o in O:
        if o['kind'] == 'house':
            fp = o['polygon_m']
            nt.append((o['id'] + '-core', hull(grow_poly(fp, 3.0)), 'yard core: house + 3 m (door, porch, drive end)'))
    for o in O:
        if o['kind'] == 'open_working_grass':
            nt.append((o['id'], o['polygon_m'], 'open meadow patch (keeps the village airy, views)'))
    nt.append(('02-G-ground_02', byid['02-G-ground_02']['polygon_m'], 'grandpa yard (base 2): van work yard'))
    nt.append(('02-church-forecourt', [(ce[0] - 6, ce[1] - 2), (ce[0] + 6, ce[1] - 2), (ce[0] + 6, cy0), (ce[0] - 6, cy0)], 'church forecourt'))
    for i, (nid, poly, why) in enumerate(nt):
        Z.append({'id': '02-no-tree-%s' % nid.replace('02-', ''), 'kind': 'no_tree', 'poly': R(ccw(TT(poly))), 'why': why})
    # ------------------------------------------------ checks (plan metres)
    bpolys = [(b['id'], b['footprint']) for b in B]
    bad_b = []
    for i in range(len(bpolys)):
        for j in range(i + 1, len(bpolys)):
            if polys_overlap(bpolys[i][1], bpolys[j][1]):
                bad_b.append((bpolys[i][0], bpolys[j][0]))
    road_hits = []
    for b in B:
        for z in Z:
            if z['kind'] == 'street':
                hw = z['width_m'] / 2
                m_ = min(nearest_on(z['line'], p)[0] for p in b['footprint'] + [centroid(b['footprint'])])
                if m_ < hw - 0.05:
                    road_hits.append((b['id'], z['id'], round(m_ - hw, 2)))
    dangling = []
    world_ends = [W_['bypass']] + W_['links']
    for z in Z:
        if z['kind'] != 'street':
            continue
        for end in (0, -1):
            p = z['line'][end]
            on_axis = min([nearest_on(o_['line'], p)[0] for o_ in Z if o_['kind'] == 'street' and o_ is not z] +
                          [min(math.hypot(p[0] - q[0], p[1] - q[1]) for q in (pl[0], pl[-1])) for pl in W_['links']] + [nearest_on(W_['bypass'], p)[0]])
            if on_axis > 0.15:
                near_b = min(poly_d(p, b['footprint']) for b in B)
                near_z = min((0.0 if inside(p, z2['poly']) else poly_d(p, z2['poly'])) for z2 in Z if z2['kind'] in
                             ('yard', 'field', 'loading_pad', 'apron', 'plaza', 'pig_pen', 'vegetable_garden'))
                if min(near_b, near_z) > 4.0:
                    dangling.append((z['id'], 'start' if end == 0 else 'end', rnd2(p), round(min(near_b, near_z), 1)))
    a_props = [(p['id'], round(min(nearest_on(z['line'], p['pos'])[0] - z['width_m'] / 2 for z in Z if z['kind'] == 'street'), 2)) for p in P]
    on_road = [x for x in a_props if x[1] < 0.3 and not x[0].startswith(('02-REED', '02-FISH'))]
    fitd = render_fit([b['footprint'] for b in B if b['kind'] == 'house'], (206, 178, 150), 6, (195, 370, 470, 625))
    fitc = render_fit([b['footprint'] for b in B if b['kind'] == 'church'], (214, 208, 226), 6, (195, 370, 470, 625), inset=1.0)
    transform = ('HAMLET_LAYOUT_v06 metres = plan Хутор_v07 metres (build_hutor_v07.py X0 = %.0f, Y1 = %.0f) -> master SVG v85 <image C_hamlet_v07_world.png '
                 'x %.0f y %.0f w %.0f h %.0f> = %.1f units/m: X = %.0f + (x - %.0f) * 5, Y = %.0f + (%.0f - y) * 5 -> world = common.u2w '
                 '= (x + %.2f, y + %.2f) (post-shift over all output points <= %.2f m). Fit on VOLUNTEERS_MAP_FINAL_v85.png: houses %.0f %% of the '
                 'inset footprints on the house fill, best extra shift %s m (residual %.1f m = render pixel grid); church %.0f %%, shift %s m. '
                 'v76 (layout v04) used warp_m + post_shift = net (+70, 0) too.'
                 % (X0, Y1, ix, iy, iw, ih, k, ix, X0, iy, Y1, tr0[0], tr0[1], shifts[0], fitd['on_fill_share'] * 100,
                    fitd['best_extra_shift_m'], fitd['residual_m'], fitc['on_fill_share'] * 100, fitc['best_extra_shift_m']))
    if not any(q['ru'].startswith('Фонари') for q in LOG.get(D, {}).get('q', [])):
        question(D, 'Фонари на деревянных столбах без проводов: в раскладке v06 их 4 (у главной улицы и площади); HAMLET_SPEC §5 оставил это открытым.',
                 ['1 — оставить 4 фонаря раскладки, без проводов (сейчас)', '2 — фонарей в Хуторе нет совсем', '3 — фонари только у площади и на въездах с асфальта'],
                 1, '4 pole_lamp props kept (grip anchors), no wires')
    tbl = next((p for p in P if p['id'] == '02-SQ-TABLE'), None)
    if tbl:
        P.append({'id': '02-POLICE-POST', 'kind': 'police_post_npc', 'pos': rnd2((tbl['pos'][0] - 2.0, tbl['pos'][1] - 2.0)), 'rot_deg': 270.0,
                  'size': [0.8, 0.8, 1.8], 'grip_anchor': False, 'dressing': False, 'npc': 'grandpa_policeman_with_rifle', 'facing_deg': 270.0,
                  'notes': 'post of the only Hamlet policeman (slow grandpa with a rifle, comes to noise): sits at the square table under the tree, '
                           'faces the main street (south) - Fedya 22.10 item 21, option A'})
    n_out = sum(1 for b in B if b['kind'] in ('shed', 'chicken_coop', 'pig_shelter', 'hay_shelter'))
    counts = {'houses': sum(1 for b in B if b['kind'] == 'house'), 'abandoned': sum(1 for b in B if b.get('abandoned')), 'base2_hut': 1,
              'church': 1, 'water_tower': 1, 'bus_stop': 1, 'outbuildings': n_out,
              'outbuildings_by_kind': {k2: sum(1 for b in B if b['kind'] == k2) for k2 in ('shed', 'chicken_coop', 'pig_shelter', 'hay_shelter')},
              'buildings_total': len(B), 'fields': sum(1 for z in Z if z['kind'] == 'field'), 'vegetable_gardens': sum(1 for z in Z if z['kind'] == 'vegetable_garden'),
              'yards': sum(1 for z in Z if z['kind'] == 'yard'), 'meadow_patches': sum(1 for z in Z if z['kind'] == 'meadow_patch'), 'streets': sum(ncls.values()), 'streets_by_class': ncls,
              'street_length_m_by_class': {c_: round(sum(plen(z['line']) for z in Z if z['kind'] == 'street' and z['road_class'] == c_)) for c_ in ncls},
              'hay_bales': sum(1 for p in P if p['kind'] == 'round_hay_bale'), 'props': len(P), 'props_key': sum(1 for p in P if not p['dressing']),
              'props_dressing': sum(1 for p in P if p['dressing']), 'designed_trees': len(designed), 'layout_trees_to_zones': len(free),
              'veg_zones': sum(1 for z in Z if z['kind'] == 'veg_zone'), 'no_tree_zones': sum(1 for z in Z if z['kind'] == 'no_tree')}
    checks = {'building_overlaps': bad_b, 'buildings_on_streets': road_hits, 'dangling_street_ends': dangling, 'props_on_streets': on_road,
              'fences_between_houses': 0, 'wires': 0, 'kolkhoz_barn': 0, 'shop': 0, 'backing_plate': False}
    return {'district': 'hamlet', 'version': 'v85 from plan v07 / layout v06',
            'sources': [REL(HAMLET_JSON), REL(HUTOR_PY), 'ArtSource/References/Map/World_v83/Districts/Хутор_v07.png',
                        'ArtSource/References/Map/World_v83/Districts/hamlet_layout_v06_build.py',
                        'ArtSource/References/Map/World_v85/VOLUNTEERS_MAP_MASTER_v85.svg (<image C_hamlet_v07_world.png>, R52_bypass, L05_roads)',
                        'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §1 §4 §6 §7.2 §8', 'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.2',
                        'docs/specs/HAMLET_SPEC_2026-10-18_v01.md'],
            'transform': transform, 'fit': {'houses': fitd, 'church': fitc}, 'pad_height_m': None,
            'pad_note': 'no pad: the Hamlet lies on the natural terrain - designed hills / dips in terrain_features (built by s03, W86), the ground rises '
                        'gently to the gorge rim in the east; house plots, yards, fields, square, base 2 and streets are flattened on top (terraces)',
            'terrain_features': [{'id': i_, 'kind': k_, 'crest': [list(map(float, q)) for q in cr], 'half_width_m': float(hw_), 'height_m': float(hh_),
                                  'source': src_, 'role_ru': role_} for i_, k_, cr, hw_, hh_, src_, role_ in HAMLET_TERRAIN],
            'abs_heights': False, 'lighting': 'warm_rural', 'no_wires': True,
            'seam': 'NO backing plate, no district ground polygon, no border: outside the listed zones the ground is the world meadow L01; zone edges blend '
                    '1.5-3 m into the meadow (v10 §7.2 "без шва")', 'surface_edge_blend_m': 2.0,
            'buildings': B, 'props': P, 'zones': Z, 'fixed_by_logic': LOG[D]['fix'], 'questions_for_vadim': LOG[D]['q'], 'counts': counts, 'checks': checks,
            'notes': 'No fences between houses, no wires, no kolkhoz barn, no shop (v10 §7.2); the pig pen rails are the only fence. Props with "dressing": true '
                     'are the per-owner yard clutter of the layout (kept as data, s06 may re-place them by rule).'}


# ================================================================ FOREST
def forest(W_):
    D = 'forest'
    d01 = W_['d01']
    v11 = json.load(open(V11_JSON, encoding='utf-8'))
    B, P, Z = [], [], []
    roads = [r for r in d01 if r[1] == 'polyline' and r[3] == '#E5D2A4']
    keep = []
    for r in sorted(roads, key=lambda r: -len(r[5])):
        if any(max(nearest_on(k[5], p)[0] for p in r[5]) < 0.5 for k in keep):
            fix(D, centroid(r[5]), 'Дубль грунтовки (%d точек, %.0f м) поверх ветки к вагону не перенесён' % (len(r[5]), plen(r[5])),
                'на карте одна и та же дорога нарисована дважды (наложение полос)')
            continue
        keep.append(r)
    names = {}
    for r in keep:
        a, b = r[5][0], r[5][-1]
        if abs(a[0] - 272.6) < 2 and b[0] > 390:
            names[id(r)] = ('01-road-wagon-east', 'from the wagon clearing east over the hills to the right road (v02 §8.1)')
        elif abs(a[0] - 272.6) < 2:
            names[id(r)] = ('01-road-hamlet', 'trail to the Hamlet: clearing -> north (v10 §7.1)')
        else:
            names[id(r)] = ('01-road-east', 'right road: junction with the valley dirt road (south) -> north to the Hamlet bypass')
    for r in keep:
        nid, nt = names[id(r)]
        Z.append({'id': nid, 'kind': 'road', 'line': R(r[5]), 'width_m': WIDTH['village_main'], 'road_class': 'village_main', 'surface': 'dirt_SK1b',
                  'ruts': True, 'grass_centre': True, 'puddles': True, 'kerb': False, 'markings': False, 'world_road': True,
                  'notes': nt + '; drawn 27 SVG units = 5.4 m; ruts with grass, roots, puddles'})
    for i, pl in enumerate(W_['links']):
        if pl[0][0] < 420 and pl[-1][1] > 300:
            nid = '01-link-hamlet' if pl[0][0] < 350 else '01-link-bypass'
            Z.append({'id': nid, 'kind': 'road', 'line': R(pl), 'width_m': WIDTH['village_main'], 'road_class': 'village_main', 'surface': 'dirt_SK1b',
                      'ruts': True, 'grass_centre': True, 'puddles': True, 'world_road': True, 'shared': True,
                      'notes': 'connector drawn outside D01 (L05_roads): %s; listed here so the forest network is complete' %
                               ('Hamlet street 02-R-south end -> forest trail' if nid == '01-link-hamlet' else 'forest right road -> Hamlet bypass asphalt')})
    # railway, wagon (base 1), clearing, campfire
    ball = next(r for r in d01 if r[1] == 'polyline' and r[3] == '#C4C6BF')[5]
    rails = [r[5] for r in d01 if r[1] == 'polyline' and r[3] == '#586266']
    a, b = (ball[0], ball[-1]) if ball[0][0] < ball[-1][0] else (ball[-1], ball[0])
    Lt = math.dist(a, b)
    u = ((b[0] - a[0]) / Lt, (b[1] - a[1]) / Lt)
    ang = math.degrees(math.atan2(u[1], u[0]))
    Z.append({'id': '01-railway', 'kind': 'railway', 'line': R([a, b]), 'width_m': 3.6, 'gauge_m': 1.52, 'surface': 'gravel_SK1d', 'rails': [R(x) for x in rails],
              'sleepers': True, 'overgrown': True, 'rusty': True, 'dead_end': 'east (at the wagon)',
              'notes': 'short dead-end single track from the coastal cliff to the wagon only (v02 §8.1); tunnel mouth blocked by rocks at the west end'})
    P.append({'id': '01-tunnel-mouth', 'kind': 'blocked_tunnel_mouth', 'pos': rnd2(a), 'rot_deg': round(ang, 1), 'size': [6.0, 3.0, 5.0], 'grip_anchor': False,
              'notes': 'rail tunnel mouth in the cliff, filled with rocks (v02 §8.1); no way out'})
    wag_svg = next(r for r in d01 if r[1] == 'polygon' and r[2] == '#B99079')[5]
    clr = next(r for r in d01 if r[1] == 'polygon' and r[2] == '#EAE7D5')[5]
    WL, WW = 24.0, 3.2
    tc = Lt - WL / 2 - 0.5
    wc = (a[0] + u[0] * tc, a[1] + u[1] * tc)
    wfp = rrect(wc, WL, WW, ang)
    pos, fac = edge_door(wfp, centroid(clr), long_only=True)
    v11w = next(x for x in v11['buildings'] if x['id'] == '01_B01')['footprint_m']
    dv11 = max(min(math.dist((p[0] + 70, p[1]), q) for q in wag_svg) for p in v11w)
    sw = sorted(math.dist(wag_svg[i], wag_svg[(i + 1) % 4]) for i in range(4))
    B.append({'id': '01_B01', 'kind': 'rail_wagon_base1', 'base': 1, 'material_slot': 'forest_wagon', 'footprint': R(ccw(wfp)), 'floors': 1,
              'floor_h_m': 2.6, 'height_m': 3.9, 'floor_above_rail_m': 1.3,
              'roof': {'type': 'barrel', 'material': 'metal_rusty', 'ridge_axis_deg': round(ang % 180, 1), 'ridge_h_m': 0.4, 'overhang_m': 0.05},
              'walls': 'metal_rusty', 'tint': '#8C4A36', 'entrances': [{'pos': rnd2(pos), 'facing_deg': fac, 'kind': 'sliding_door', 'w_m': 1.8, 'police_stop': True}],
              'facade_kit': 'none', 'sockets': {'balconies': 'none', 'windows': True, 'ridge_cap': None, 'bogies': 2, 'steps': True},
              'collider': 'full_roof', 'on_track': '01-railway',
              'notes': 'old railway wagon at the end of the dead-end track = BASE 1 (start, cramped). Map icon %.1f x %.1f m -> v02 §8.1 size %.0f x %.1f m '
                       'on the track axis, east end 0.5 m before the track end' % (sw[2], sw[0], WL, WW)})
    fix(D, wc, 'Вагон базы 1: размер по v02 §8.1 (%.0f×%.1f м) на оси пути у его тупика, а не значок карты %.1f×%.1f м' % (WL, WW, sw[2], sw[0]),
        'на карте вагон нарисован значком шириной %.0f м (вдвое шире ж/д вагона); положение и направление — как на карте' % sw[0])
    question(D, 'База 1 (вагон): ширина на карте ~%.0f м (значок), в передаче v02 — вагон ~24×3,2 м. Тесная база — это по канону («старт, тесно»).' % sw[0],
             ['1 — настоящий вагон 24×3,2 м на путях (сейчас)', '2 — шире, как значок карты (~22×8 м): не вагон, а «барак»'], 1,
             'wagon 24 x 3.2 m on the track axis')
    Z.append({'id': '01-clearing', 'kind': 'clearing', 'poly': R(ccw(clr)), 'surface': 'worn_grass_L02',
              'notes': 'clearing at the wagon: trodden grass, cold campfire, "people come here to drink" traces; birches at the edge (v02 §8.1)'})
    fire = next(r for r in d01 if r[1] == 'circle' and r[2] == '#C9C8BD')
    P.append({'id': '01-campfire', 'kind': 'campfire_cold', 'pos': rnd2(fire[5]), 'rot_deg': 0, 'size': [round(2 * fire[4], 1)] * 2 + [0.4],
              'grip_anchor': False, 'notes': 'cold campfire: ring of 9 stones, charred logs (v02 §8.1)'})
    log_ = next(r for r in d01 if r[1] == 'polygon' and r[2] == '#AF9676')[5]
    lw = sorted(math.dist(log_[i], log_[(i + 1) % 4]) for i in range(4))
    P.append({'id': '01_B03', 'kind': 'log_bench', 'pos': rnd2(centroid(log_)), 'rot_deg': 0, 'size': [round(lw[2], 1), round(lw[0], 1), 0.5],
              'grip_anchor': True, 'notes': 'v11 01_B03 "forest_structure" %.1f x %.1f m by the campfire -> a fallen-log bench (not a 3.2 m building)' % (lw[2], lw[0])})
    fix(D, centroid(log_), 'Объект 01_B03 у костра (%.1f×%.1f м, в v11 «постройка» 3,2 м высотой) сделан бревном-скамьёй' % (lw[2], lw[0]),
        'полоска 1,4 м шириной у костра — это бревно для сидения, а не дом; v76 строил её коробкой 3,2 м')
    P.append({'id': '01-litter', 'kind': 'party_litter_spot', 'pos': rnd2((fire[5][0] - 3.5, fire[5][1] + 3.0)), 'rot_deg': 0, 'size': [6.0, 4.0, 0.2],
              'grip_anchor': False, 'dressing': True, 'notes': 'bottles, cans, cigarette butts as decals around the fire (v02 §8.1), not on the track or road'})
    # water
    sw_out = next(r for r in d01 if r[1] == 'polygon' and r[2] == '#ABC098')[5]
    sw_in = next(r for r in d01 if r[1] == 'polygon' and r[2] == '#7D9E83')[5]
    lake = next(r for r in d01 if r[1] == 'polygon' and r[2] == '#95CADB')[5]
    Z.append({'id': '01-swamp', 'kind': 'swamp', 'poly': R(ccw(sw_out[:-1])), 'surface': 'swamp_moss', 'water': R(ccw(sw_in[:-1])), 'water_surface': 'dark_water',
              'van_blocked': True, 'notes': 'ONE swamp (v02 §8.1): dark water, hummocks, reeds, moss, a few dead trees; not dozens of puddles'})
    Z.append({'id': '01-lake', 'kind': 'lake', 'poly': R(ccw(lake[:-1])), 'surface': 'water', 'van_blocked': True,
              'notes': 'ONE lake, rounder, at the north edge of the forest (v02 §8.1); reeds at the shore'})
    # vegetation: crown density of the v85 preview -> veg zones (no tree points)
    pre = np.asarray(Image.open(MAP_PREVIEW).convert('RGB')).astype(np.int16)[::-1]
    Rr, G, Bb = pre[..., 0], pre[..., 1], pre[..., 2]
    crown = (G - Rr >= 18) & (G - Bb >= 20) & (pre.max(-1) <= 212)
    ys, xs = np.mgrid[0:pre.shape[0], 0:pre.shape[1]]
    region = (xs >= 182) & (xs <= 505) & (ys >= 40) & (ys <= 352)
    fence = W_.get('valley_fence')
    if fence:
        region &= ~ndimage.binary_dilation(poly_mask(fence), iterations=6)
    dens = ndimage.gaussian_filter(crown.astype(np.float32), 5.0)
    zone = ndimage.binary_opening(ndimage.binary_closing((dens > 0.20) & region, iterations=4), iterations=3) & region
    lab_, n = ndimage.label(zone)
    vz = 0
    big = None
    for i in range(1, n + 1):
        m_ = lab_ == i
        ar = int(m_.sum())
        if ar < 1200:
            continue
        cont = contour(m_, step=4)
        if len(cont) < 8:
            continue
        mean_d = float(crown[m_].mean())
        dense = ar > 20000 and mean_d >= 0.30
        vz += 1
        zid = '01-veg%02d' % vz
        if dense and (big is None or ar > big[1]):
            big = (zid, ar)
        Z.append({'id': zid, 'kind': 'veg_zone', 'poly': R(ccw(cont)), 'density': 'dense' if dense else 'grove', 'species': 'pine',
                  'mix': {'pine': 0.8, 'spruce': 0.12, 'birch': 0.08}, 'no_drive': dense, 'area_m2': ar, 'crown_cover_on_map': round(mean_d, 2),
                  'trunk_spacing_m': [3, 6] if dense else [5, 10], 'collider': 'capsule',
                  'notes': ('big forest: Finnish pine, tall straight orange-brown trunks, some spruce, birches at clearings; view between trunks, van cannot '
                            'drive off the roads (v02 §8.1, v10 §7.1)') if dense else 'forest edge / grove: same species, sparser, drivable gaps'})
    assert big, 'forest zone not found'
    # no_tree
    for z in list(Z):
        if z['kind'] == 'road':
            Z.append({'id': '01-no-tree-' + z['id'][3:], 'kind': 'no_tree', 'poly': R(buffer_line(z['line'], z['width_m'] / 2 + 2.0)), 'why': 'road + 2 m'})
    Z.append({'id': '01-no-tree-railway', 'kind': 'no_tree', 'poly': R(buffer_line([a, b], 3.5)), 'why': 'railway bed + 1.7 m'})
    Z.append({'id': '01-no-tree-clearing', 'kind': 'no_tree', 'poly': R(ccw(clr)), 'why': 'wagon clearing (base 1 loading / turning)'})
    Z.append({'id': '01-no-tree-base1', 'kind': 'no_tree', 'poly': R(ccw(grow_poly(wfp, 3.0))), 'why': 'wagon + 3 m'})
    Z.append({'id': '01-no-tree-campfire', 'kind': 'no_tree', 'poly': R(ccw(ellipse(fire[5], 6.0, 6.0, 12))), 'why': 'campfire spot'})
    # checks
    r_hamlet = next(z for z in Z if z['id'] == '01-road-hamlet')['line']
    junction = min(math.dist(r_hamlet[-1], pl[-1]) for pl in W_['links'])
    v11c = {x['id']: x for x in v11['buildings']}
    checks = {'wagon_v11_plus70_vs_svg_m': round(dv11, 2), 'trail_to_hamlet_end_gap_m': round(junction, 2),
              'roads_reach_beach': False, 'swamps': 1, 'lakes': 1,
              'dense_forest_zone': big[0], 'v11_buildings': sorted(k_ for k_ in v11c if k_.startswith('01_'))}
    counts = {'buildings': len(B), 'base1_wagon': 1, 'roads': sum(1 for z in Z if z['kind'] == 'road'),
              'road_length_m': round(sum(plen(z['line']) for z in Z if z['kind'] == 'road')), 'railway_m': round(Lt, 1),
              'veg_zones': sum(1 for z in Z if z['kind'] == 'veg_zone'), 'dense_veg_zones': sum(1 for z in Z if z.get('density') == 'dense'),
              'no_tree_zones': sum(1 for z in Z if z['kind'] == 'no_tree'), 'props': len(P)}
    fix(D, centroid(next(z['poly'] for z in Z if z['id'] == big[0])), 'Деревья леса не перенесены точками: зоны veg_zone по плотности крон карты v85 '
        '(зон: %d; большой лес dense — непроезжий)' % counts['veg_zones'], 'v10 §1.2: деревья — зонами плотности; густой лес — непроезжий (v10 §7.1)')
    return {'district': 'forest', 'version': 'v85 (map v85 vectors D01 + WORLD_MAP_v11 district 01)',
            'sources': ['ArtSource/References/Map/World_v85/VOLUNTEERS_MAP_MASTER_v85.svg (D01 translate(200 1780): D01_water, D01_roads_paths, D01_buildings; L05_roads)',
                        REL(V11_JSON) + ' (district 01)', 'ArtSource/References/Map/World_v85/VOLUNTEERS_MAP_PREVIEW_v85.png (crown density -> veg zones)',
                        'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §1 §7.1', 'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.1'],
            'transform': 'master SVG units -> world = common.u2w (group D01 translate(200 1780) via svg_tags affine); equals WORLD_MAP_v11 metres + (70, 0): '
                         'wagon v11 + 70 vs SVG max vertex gap %.2f m; no post-shift in the forest' % dv11,
            'pad_height_m': None, 'abs_heights': False, 'lighting': 'forest_haze', 'no_wires': True,
            'buildings': B, 'props': P, 'zones': Z, 'fixed_by_logic': LOG[D]['fix'], 'questions_for_vadim': LOG[D]['q'], 'counts': counts, 'checks': checks,
            'notes': 'No exit from the forest to the beach (high cliff to the SE). Hill contours of D01_relief are terrain, not objects. '
                     'Forest floor: moss, blueberry, low grass, ferns, mushrooms, stumps, mossy boulders, fallen trunks, fog in hollows — in groups (v02 §8.1).'}


# ================================================================ QUIET VALLEY
def valley(W_):
    D = 'quiet_valley'
    d8 = W_['d08']
    v11 = json.load(open(V11_JSON, encoding='utf-8'))
    v11b = {x['id']: x for x in v11['buildings']}
    B, P, Z = [], [], []

    def poly_by(fill, stroke=None):
        return [r[5] for r in d8 if r[1] == 'polygon' and r[2] == fill and (stroke is None or r[3] == stroke)]
    lab = poly_by('#BCD3DA')[0]
    cas = poly_by('#DDB9A0')[0]
    lab_door = poly_by('#7E9AA3')[0]
    cas_door = poly_by('#A07A5A')[0]
    lab_pad = poly_by('#EDE8DA', '#D3CCB8')[0]
    cas_fc = next(r[5] for r in d8 if r[1] == 'polygon' and r[2] == '#EDE8DA' and r[3] != '#D3CCB8')
    park = poly_by('#D3D6D7')[0]
    lawn = poly_by('#D7E5C2')[0]
    grounds = poly_by('#E4ECD6')[0]
    posts = poly_by('#E9EDE3')
    fl = [r[5] for r in d8 if r[1] == 'polyline' and r[3] == '#8B7355']
    asph = sorted([r for r in d8 if r[1] == 'polyline' and r[3] == '#5F666C'], key=lambda r: -r[4])
    main, spur = asph[0][5], asph[1][5]
    path = next(r for r in d8 if r[1] == 'polyline' and r[3] == '#DCD3BC')
    trees = [r for r in d8 if r[1] == 'circle' and r[2] == '#B9D19F']
    resid = {}
    for vid, poly in (('08_01_lab', lab), ('08_03_casino', cas)):
        resid[vid] = round(max(min(math.dist((p[0] + 70, p[1]), q) for q in poly) for p in v11b[vid]['footprint_m']), 2)
    # ---- fence loop through the gate posts (fence ends 3-6 m short of the posts closed)
    pc = sorted((centroid(p) for p in posts), key=lambda c: (-c[1], c[0]))
    north = sorted(pc[:2], key=lambda c: c[0])
    south = sorted(pc[2:], key=lambda c: c[0])
    nw = next(x for x in fl if max(p[0] for p in x) < north[0][0] and min(p[1] for p in x) > 260)           # NW corner -> north gate (west)
    east = next(x for x in fl if x[0][0] > north[1][0] - 3 and x[0][1] > 260)                               # north gate (east) -> south gate (east)
    west = next(x for x in fl if x is not nw and x is not east)                                             # south gate (west) -> NW corner
    gaps = [math.dist(nw[-1], north[0]), math.dist(east[0], north[1]), math.dist(east[-1], south[1]), math.dist(west[0], south[0])]
    loop = list(nw) + [north[0], north[1]] + list(east) + [south[1], south[0]] + list(west)
    if math.dist(loop[0], loop[-1]) < 0.5:
        loop[-1] = loop[0]
    else:
        loop.append(loop[0])
    W_['valley_fence'] = loop
    pw = sorted(math.dist(posts[0][i], posts[0][(i + 1) % 4]) for i in range(4))[0]
    gates = []
    for gid, (pa, pb), road in (('08-gate-north', north, 'asphalt from the bridge (north entry 04)'), ('08-gate-beach', south, 'asphalt to the small beach (beach gate 05)')):
        c = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
        gates.append({'id': gid, 'centre': rnd2(c), 'width_m': round(math.dist(pa, pb) - pw, 2), 'posts': [rnd2(pa), rnd2(pb)], 'post_size_m': [round(pw, 1)] * 2 + [1.4],
                      'leaf': None, 'barrier': False, 'kpp': False, 'road': road})
    assert all(g['width_m'] >= 4.0 for g in gates)
    Z.append({'id': '08-fence', 'kind': 'fence', 'line': R(loop), 'closed': True, 'height_m': 1.0, 'surface': 'boards_SK5a', 'style': 'low wooden: posts + 2 rails',
              'post_step_m': 3.2, 'gates': gates, 'nw_corner_intact': True,
              'notes': 'v10 §7.8: low wooden fence ~1 m around the perimeter; openings ONLY at the north asphalt entry and at the beach gate (no KPP, no barrier); '
                       'the NW corner is intact, the dirt road from the forest passes outside it. Builder: cut the fence between the posts of each gate.'})
    fix(D, north[0], 'Забор доведён до столбов ворот: на карте концы забора не доходили до столбов на %s м' % ', '.join('%.1f' % g for g in gaps),
        'лишние щели 1–6 м у ворот — артефакт рисования; проёмы по v10 §7.8 только у северного въезда и у пляжных ворот (между столбами)')
    # ---- roads
    Z.append({'id': '08-asphalt-main', 'kind': 'road', 'line': R(main), 'width_m': WIDTH['rural_asphalt'], 'road_class': 'rural_asphalt', 'surface': 'asphalt_A5d12',
              'shoulder': 'gravel_SK1d', 'markings': False, 'world_road': True,
              'notes': 'from the bridge over the river (north entry) down the valley as a gentle snake to the beach gate and the small beach (v02 §8.8)'})
    d0, q0, _, _ = nearest_on(main, spur[0])
    Z.append({'id': '08-asphalt-lab', 'kind': 'road', 'line': R(spur), 'width_m': round(asph[1][4] / 5.0, 1), 'road_class': 'drive', 'surface': 'asphalt_A5d12',
              'kerb': False, 'notes': 'drive to the final lab (base 5); joins the main axis (gap %.2f m)' % d0})
    vr = None
    for nm, at, M, gids, a_, b_ in svg_tags(svg_text()):
        if nm == 'polyline' and gids and gids[-1] == 'L05_roads' and (attr(at, 'stroke') or '').upper() == '#E5D2A4':
            pts = [u2w(*p) for p in points_of(at, M)]
            if math.dist(pts[-1], (543.3, 291.6)) < 2.0:
                vr = clean(pts)
    assert vr, 'valley dirt road not found'
    vr_min = min(nearest_on(loop, p)[0] for p in vr)
    vr_cross = crossings(vr, loop)
    Z.append({'id': '08-dirt-from-forest', 'kind': 'road', 'line': R(vr), 'width_m': WIDTH['village_main'], 'road_class': 'village_main', 'surface': 'dirt_SK1b',
              'ruts': True, 'grass_centre': True, 'puddles': True, 'world_road': True, 'shared': True,
              'notes': 'dirt road from the forest junction: passes OUTSIDE the intact NW fence corner (min %.1f m) and joins the asphalt right after the bridge '
                       '(v10 §7.8); never through the fence' % vr_min})
    Z.append({'id': '08-footpath-loop', 'kind': 'footpath', 'line': R(path[5]), 'width_m': round(path[4] / 5.0, 1), 'surface': 'gravel_SK1d', 'closed': True,
              'notes': 'gravel walking loop inside the fence; crosses the asphalt at grade'})
    main_x = crossings(main, loop)
    # ---- buildings
    lpos = centroid(lab_door)
    lc = centroid(lab)
    rotcw = lambda p: (lc[0] + (p[1] - lc[1]), lc[1] - (p[0] - lc[0]))        # 90 deg clockwise about the lab centre
    lab_v11 = list(lab)
    lab = [rotcw(p) for p in lab_v11]
    lab_pad = [(p[0], min(p[1], max(q[1] for q in lab) + 1.0)) for p in (rotcw(p) for p in lab_pad)]   # stays inside the fence
    lfp = ccw(lab)
    lx0r, lx1r = min(p[0] for p in lab), max(p[0] for p in lab)
    ly0r, ly1r = min(p[1] for p in lab), max(p[1] for p in lab)
    gate_w = round(math.dist(lab_door[0], lab_door[1]), 1)
    gate_p = rotcw((lpos[0], min(p[1] for p in lab_v11)))                    # v11 south gate -> west side
    door_p = rotcw((min(p[0] for p in lab_v11) + 6.0, min(p[1] for p in lab_v11)))
    ly0 = ly0r
    B.append({'id': '08_01_lab', 'kind': 'lab_final_base', 'base': 5, 'material_slot': 'valley_lab', 'footprint': R(lfp), 'floors': 2, 'floor_h_m': 3.2, 'height_m': 6.4,
              'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.6, 'skylights': True},
              'walls': 'concrete_SK3c', 'tint': '#E8ECEE', 'glazing': 'tower_glass bands', 'facade_kit': 'none',
              'entrances': [{'pos': rnd2(gate_p), 'facing_deg': 180.0, 'kind': 'garage_gate', 'w_m': gate_w,
                             'notes': 'big van garage gate, W86: on the WEST long side facing the end of the approach drive (Fedya 22.10 item 20)'},
                            {'pos': rnd2(door_p), 'facing_deg': 180.0, 'kind': 'door', 'w_m': 1.4, 'police_stop': True,
                             'notes': 'glass entrance next to the garage (not drawn; by logic: police / people door)'},
                            {'pos': rnd2(((lx0r + lx1r) / 2, ly0r)), 'facing_deg': 270.0, 'kind': 'garage_gate_small', 'w_m': 4.0,
                             'notes': 'small exit gate on the SOUTH short side: the exit drive points down (south) to the loading pad (Fedya 22.10 item 20)'}],
              'sockets': {'balconies': 'none', 'windows': True, 'ridge_cap': None, 'ac_units': 4, 'antenna': True, 'floodlights': True},
              'collider': 'full_roof', 'interior': True,
              'notes': 'FINAL lab = base 5, the most elaborate base of the game (v10 §7.8, v02 §8.8): concrete, glass, clean lines; OR, organ fridges, '
                       'automation, van garage, light; feels like a reward. v11: 2 floors 6.4 m. W86 (Fedya 22.10 item 20): the building and its plot '
                       'rotated 90 deg clockwise about the centre - big gate west (approach drive), small exit gate south (loading pad).'})
    cpos = centroid(cas_door)
    cy0 = min(p[1] for p in cas)
    B.append({'id': '08_03_casino', 'kind': 'casino', 'material_slot': 'valley_casino', 'footprint': R(ccw(cas)), 'floors': 2, 'floor_h_m': 3.2, 'height_m': 6.4,
              'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.8}, 'walls': 'stucco_SK3b', 'tint': '#DDB9A0', 'facade_kit': 'none',
              'entrances': [{'pos': rnd2((cpos[0], cy0)), 'facing_deg': 270.0, 'kind': 'door', 'w_m': round(math.dist(cas_door[0], cas_door[1]), 1),
                             'canopy': True, 'notes': 'main entrance to the beach-gate forecourt'}],
              'sockets': {'balconies': 'none', 'windows': True, 'ridge_cap': None, 'sign': 'neon sign WITHOUT a name (Fedya 22.10 item 19: later a strip club)',
                          'awning': True},
              'collider': 'full_roof', 'notes': 'casino at the beach gate with its own parking and sign (v10 §7.8); second casino / Casino Island OPEN (v10 §12)'})
    # ---- base 5 loading: the drawn drive ends at the lab's west wall, the garage gate is on the south side (6.4 m to the lawn)
    # W86 item 20: the loading pad keeps its size (18 x 15) and its x span; the rotated 38 m building stands on its old place, so the pad
    # sits 4 m south of the new south (small-gate) side; the approach drive ends in front of the west gate; the exit drive leaves the
    # small south gate straight down to the pad; the side drive (west of the lab) links the pad back to the approach drive
    yx = ly0r - 4.0
    pad = [(lpos[0] - 9.0, yx - 15.0), (lpos[0] + 9.0, yx - 15.0), (lpos[0] + 9.0, yx), (lpos[0] - 9.0, yx)]
    spur = list(spur[:-1]) + [(lx0r - 9.0, gate_p[1] + 2.3)] if math.dist(spur[-1], (lx0r - 9.0, gate_p[1])) < 25 else list(spur)
    Z[[i for i, z_ in enumerate(Z) if z_['id'] == '08-asphalt-lab'][0]]['line'] = R(spur)
    se = spur[-1]
    exit_drive = [((lx0r + lx1r) / 2, ly0r), ((lx0r + lx1r) / 2, yx)]
    link = [se, (se[0] - 3.0, se[1] - 5.0), (se[0] - 3.0, yx - 4.0), (lpos[0] - 9.0, yx - 7.5)]
    Z.append({'id': '08-base5-forecourt', 'kind': 'plaza', 'poly': R(ccw(lab_pad)), 'surface': 'concrete_SK3c', 'base': 5, 'notes': 'drawn paved plot of the lab'})
    Z.append({'id': '08-base5-loading', 'kind': 'loading_pad', 'poly': R(ccw(pad)), 'surface': 'concrete_SK3c', 'base': 5, 'size_m': [18.0, 15.0],
              'notes': 'loading / turning pad in front of the garage gate (v10 §4: >= 12-15 m at every base); police car spot at its west edge'})
    Z.append({'id': '08-base5-drive', 'kind': 'road', 'line': R(link), 'width_m': 4.8, 'road_class': 'drive', 'surface': 'asphalt_A5d12', 'kerb': False,
              'notes': 'side drive west of the lab: approach drive end -> loading pad (W86 item 20)'})
    Z.append({'id': '08-base5-exit', 'kind': 'road', 'line': R(exit_drive), 'width_m': 4.8, 'road_class': 'drive', 'surface': 'concrete_SK3c', 'kerb': False,
              'notes': 'small exit drive: from the small south gate straight down (south) to the loading pad (Fedya 22.10 item 20)'})
    fix(D, gate_p, 'Лаборатория (база 5) повёрнута на 90° по часовой вместе с участком: большие ворота гаража смотрят на запад, на конец подъезда; '
                   'малые ворота на южной короткой стороне, выезд прямо вниз к площадке 18×15 м (площадка того же размера, сдвинута на юг '
                   'под новый торец здания: на старом месте теперь стоит само 38-метровое здание)',
        'Федя 22.10, ответ 20: ворота к подъезду, площадка остаётся, малый выезд вниз с короткой стороны (не со стороны больших ворот)')
    Z.append({'id': '08-casino-forecourt', 'kind': 'plaza', 'poly': R(ccw(cas_fc)), 'surface': 'concrete_SK3c', 'notes': 'casino forecourt to the beach gate'})
    Z.append({'id': '08-casino-parking', 'kind': 'parking', 'poly': R(ccw(park)), 'surface': 'asphalt_A5d12', 'markings': True, 'bays': 4,
              'notes': 'casino parking (drawn 4 bays)'})
    Z.append({'id': '08-lawn', 'kind': 'lawn', 'poly': R(ccw(lawn[:-1] if lawn[0] == lawn[-1] else lawn)), 'surface': 'lawn', 'notes': 'open mown lawn (v11 08_open_lawn)'})
    Z.append({'id': '08-grounds', 'kind': 'grounds', 'poly': R(ccw(grounds)), 'surface': 'lawn',
              'notes': 'mown grounds inside the fence: calm, green, slightly mysterious (v02 §8.8); edge = the fence, outside the meadow continues'})
    # ---- nature at the valley
    rk = W_['rocks']
    Z.append({'id': '08-rocks-east', 'kind': 'rock_massif', 'poly': R(ccw(rk)), 'surface': 'rock', 'height_m': [25, 40], 'van_blocked': True, 'shared': True,
              'notes': 'high grey sharp rocks between the valley / river and the city beach: cannot be crossed (v10 §7.8, v02 §8.8)'})
    rv, rw = W_['river']
    P.append({'id': '08-waterfall', 'kind': 'waterfall_to_sea', 'pos': rnd2(rv[-1]), 'rot_deg': round(math.degrees(math.atan2(rv[-1][1] - rv[-2][1], rv[-1][0] - rv[-2][0])), 1),
              'size': [round(rw, 1), 6.0, 8.0], 'grip_anchor': False, 'shared': True,
              'notes': 'the river along the east edge of the valley falls into the sea as a waterfall (v10 §7.8); no waterfall pond inside the valley'})
    lbl02 = next((r for r in d8 if r[1] == 'circle' and r[2] == '#FFFFFF' and abs(r[5][0] - 589.2) < 1 and abs(r[5][1] - 180.0) < 1), None)
    if lbl02:
        fix(D, lbl02[5], 'Метка «02» (бывшие скалы с водопадом и прудом внутри долины, v11 08_02) ничего не ставит',
            'v02 §8.8 / v39: водопада с прудом внутри долины нет; на карте осталась только цифра')
    # ---- vegetation
    Z.append({'id': '08-veg-park', 'kind': 'veg_zone', 'poly': R(ccw(grounds)), 'density': 'sparse', 'species': 'leafy', 'target_count': len(trees),
              'notes': 'a few specimen trees in the mown grounds (map shows %d), never on the asphalt, drives, forecourts, lawn or loading pad' % len(trees)})
    for z in list(Z):
        if z['kind'] in ('road', 'footpath') and z['id'] != '08-dirt-from-forest':
            Z.append({'id': '08-no-tree-' + z['id'][3:], 'kind': 'no_tree', 'poly': R(buffer_line(z['line'], z['width_m'] / 2 + 2.0, cap=False)), 'why': z['kind'] + ' + 2 m'})
        elif z['kind'] in ('plaza', 'loading_pad', 'parking', 'lawn'):
            Z.append({'id': '08-no-tree-' + z['id'][3:], 'kind': 'no_tree', 'poly': z['poly'], 'why': z['kind']})
    Z.append({'id': '08-no-tree-dirt', 'kind': 'no_tree', 'poly': R(buffer_line(vr, WIDTH['village_main'] / 2 + 2.0)), 'why': 'dirt road + 2 m'})
    Z.append({'id': '08-no-tree-fence', 'kind': 'no_tree', 'poly': R(buffer_line(loop, 2.0, cap=False)), 'why': 'fence line +- 2 m'})
    for g in gates:
        Z.append({'id': '08-no-tree-' + g['id'][3:], 'kind': 'no_tree', 'poly': R(ccw(ellipse(g['centre'], g['width_m'] / 2 + 4, g['width_m'] / 2 + 4, 12))), 'why': 'gate'})
    # ---- checks
    lab_ok = poly_d(link[-1], pad)
    checks = {'v11_plus70_vs_svg_m': resid, 'asphalt_fence_crossings': [rnd2(p) for p in main_x],
              'asphalt_crossings_inside_gates': all(min(math.dist(p, g['centre']) for g in gates) < 3.5 for p in main_x),
              'dirt_road_fence_crossings': len(vr_cross), 'dirt_road_min_dist_to_fence_m': round(vr_min, 2), 'lab_spur_to_main_axis_m': round(d0, 2),
              'fence_post_gaps_closed_m': [round(g, 2) for g in gaps], 'nw_corner_intact': True, 'base5_drive_to_pad_m': round(lab_ok, 2)}
    assert checks['asphalt_crossings_inside_gates'] and not vr_cross and vr_min > 4.0, checks
    fitl = render_fit([lab], (188, 211, 218), 6, (470, 90, 660, 320), inset=1.0)
    fitc = render_fit([cas], (221, 185, 160), 6, (470, 90, 660, 320), inset=1.0)
    counts = {'buildings': len(B), 'base5_lab': 1, 'casino': 1, 'gates': len(gates), 'fence_m': round(plen(loop), 1),
              'roads': sum(1 for z in Z if z['kind'] == 'road'), 'veg_zones': 1, 'map_trees_inside': len(trees), 'no_tree_zones': sum(1 for z in Z if z['kind'] == 'no_tree')}
    return {'district': 'quiet_valley', 'version': 'v85 (map v85 vectors district_08 + WORLD_MAP_v11 district 08)',
            'sources': ['ArtSource/References/Map/World_v85/VOLUNTEERS_MAP_MASTER_v85.svg (D08 translate(1766 2080) / district_08; L05_roads; R34_sharp_rocks; R38_river_mouth)',
                        'ArtSource/References/Map/World_v85/build_world_v85.py (v83 fence, v85 dirt road reroute)', REL(V11_JSON) + ' (district 08)',
                        'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §4 §7.8 §12', 'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.8'],
            'transform': 'master SVG units -> world = common.u2w (svg_tags affine, D08 translate(1766 2080)); = WORLD_MAP_v11 metres + (70, 0): lab / casino max vertex gap %s m; '
                         'render fit lab %.0f %% / casino %.0f %% of the inset footprint on the drawn fill, extra shift %s / %s m'
                         % (resid, fitl['on_fill_share'] * 100, fitc['on_fill_share'] * 100, fitl['best_extra_shift_m'], fitc['best_extra_shift_m']),
            'fit': {'lab': fitl, 'casino': fitc}, 'pad_height_m': None, 'abs_heights': False, 'lighting': 'calm_green_mysterious', 'no_wires': True,
            'buildings': B, 'props': P, 'zones': Z, 'fixed_by_logic': LOG[D]['fix'], 'questions_for_vadim': LOG[D]['q'], 'counts': counts, 'checks': checks,
            'notes': 'Population of the valley and the second casino are OPEN (v10 §12). Entry from the Hamlet bypass over the river bridge (railings, continuous road).'}


# ================================================================ check images
def check(d, box, name, W_=None):
    x0, y0, x1, y1 = box
    s = 3
    im = Image.open(MAP_PREVIEW).convert('RGB').crop((x0, 950 - y1, x1, 950 - y0))
    im = im.resize((im.width * s, im.height * s), Image.NEAREST)
    tp = lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s)
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for z in d['zones']:
        if z['kind'] == 'veg_zone':
            dl.polygon([tp(q) for q in z['poly']], fill=(0, 120, 0, 40) if z.get('density') != 'dense' else (0, 90, 0, 55))
        if 'line' in z and z['kind'] in ('street', 'road', 'railway', 'footpath'):
            col = {'street': (255, 225, 0, 110), 'road': (255, 140, 0, 150), 'railway': (90, 90, 90, 120), 'footpath': (0, 200, 120, 110)}[z['kind']]
            dl.polygon([tp(q) for q in buffer_line(z['line'], z['width_m'] / 2.0, cap=False)], fill=col)
    im = Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB')
    dr = ImageDraw.Draw(im)
    for z in d['zones']:
        if z['kind'] in ('no_tree',):
            continue
        if 'poly' in z:
            col = (20, 140, 40) if z['kind'] == 'veg_zone' else (0, 190, 230)
            dr.polygon([tp(q) for q in z['poly']], outline=col)
        if 'line' in z:
            if z['kind'] == 'fence':
                dr.line([tp(q) for q in z['line']], fill=(150, 0, 200), width=3)
                for g in z['gates']:
                    for pp in g['posts']:
                        x, y = tp(pp)
                        dr.rectangle([x - 4, y - 4, x + 4, y + 4], fill=(255, 140, 0))
            else:
                dr.line([tp(q) for q in z['line']], fill=(0, 150, 0), width=1)
    for b in d['buildings']:
        dr.polygon([tp(p) for p in b['footprint']], outline=(255, 0, 0), width=2)
        for e in b.get('entrances', []):
            x, y = tp(e['pos'])
            dr.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(0, 0, 255))
    for p in d['props']:
        x, y = tp(p['pos'])
        rr = 1.5 if p.get('dressing') else 2.5
        dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 0, 255))
    os.makedirs(WORK, exist_ok=True)
    im.save(os.path.join(WORK, 'check_%s.png' % name))


def main():
    W_ = svg_west()
    v = valley(W_)                                                       # first: its fence masks the forest vegetation
    h = hamlet(W_)
    f = forest(W_)
    for name, d, box in (('hamlet', h, (190, 362, 480, 628)), ('forest', f, (178, 40, 515, 385)), ('quiet_valley', v, (470, 80, 700, 330))):
        save_json('districts/%s_v85.json' % name, d)
        check(d, box, name)
        print(name, json.dumps(d['counts'], ensure_ascii=True))
        print('  checks', json.dumps(d['checks'], ensure_ascii=True)[:600])
        print('  fixes %d questions %d' % (len(d['fixed_by_logic']), len(d['questions_for_vadim'])))
    print('hamlet transform:', h['transform'].encode('ascii', 'replace').decode())


if __name__ == '__main__':
    main()
