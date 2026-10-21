"""Step 4 / district 05 Downtown: plan v31 -> world v85 district data (lead brief "Map W85 build", CL-MAP85, 2026-10-21).

Authority (handoff v10 §0-§1, §4, §6, §7.5, §8; v02 §8.5; DOWNTOWN_LEGEND_v26 + DOWNTOWN_SPEC v03 where v10 is silent):
 footprints = the bld() polygons of Vadim's generator build_gorod_v31.py read back from Город_Downtown_v31.svg (group 'buildings',
 matched 1:1 with group 'shadows' -> conditional height class h of bld()); kinds from the generator colours + the numbered labels
 of group 'numbers'; streets = ST of build_gorod_v31.py (cross-checked with the asphalt polylines of the SVG); plaza, parking 03,
 base 13, yards 42/43, alleys, squares 20/23, gas 41, taxi 12 = the drawn plan geometry (squares_and_lots / buildings groups).
 v10 rules put into the data: streets 12 m + 2 x 5 m sidewalks (22 m between facades), curb 0.15 m, dead ends 5.6 m, houses 5-8 floors
 (corners higher), calmed "American" tints, varied facades / ground floors; trees only in squares 20 and 23; world-road entries.
 Drawing artefacts of the plan are fixed and logged in "fixed_by_logic"; gameplay-level choices are in "questions_for_vadim".

Chain (derived from the sources at run time, see `load_chain`): plan units (x east, y south, 1 u = 0.2 m) -> Chrome render of the plan
SVG (width / viewBox = 1.3 px/u) -> make_downtown_world_v31 resize 1/1.3 -> downtown_v31_world.png (1 px = 1 u) -> master-SVG units
(<image> x 590 y 0 inside D05 translate(2820 1000)) -> pre-shift metres (common.u2m) -> world = rigid (+20, -28) m. That is exactly what
post_shift_v85.shift_image did to the FINAL raster here: it samples the source at output - shift_m(output), and every Downtown output
point lies at y <= 470 m where shift_m = (20, -28). NOTE: common.u2w evaluates shift_m at the PRE-shift point, which differs inside the
gradient bands (Downtown north band: up to ~6 m off the drawn picture); this step uses the raster-consistent fixed point (pic_of_pre)
for verification and for the world-road ends. RIGID = False -> raster-consistent mapping per point (identical here).

Outputs: Data/<REV>/districts/downtown_v85.json (DISTRICT_SCHEMA.md), out_<REV>/check_downtown.png (preview x3),
out_<REV>/check_downtown_full.png (FINAL 5 px/m). Run: python s04_downtown.py (deterministic, ~20 s).
"""
import colorsys
import math
import os
import re

import numpy as np
from PIL import Image, ImageDraw

from common import (MAP_DIR, MAP_FULL, MAP_PREVIEW, ROOT, WORK, apply, attr, ccw, h01, points_of, rnd2, save_json, shift_m,
                    svg_tags, svg_text, u2m, u2w)
from common import num as anum

Image.MAX_IMAGE_PIXELS = None
PLAN_DIR = os.path.join(MAP_DIR, 'Districts')
PLAN_SVG = os.path.join(PLAN_DIR, 'Город_Downtown_v31.svg')
PLAN_PY = os.path.join(PLAN_DIR, 'build_gorod_v31.py')
PLAN_PNG = os.path.join(PLAN_DIR, 'Город_Downtown_v31.png')
WORLD_PY = os.path.join(MAP_DIR, 'make_downtown_world_v31.py')
RIGID = True

U = 0.2                                   # m per plan unit ("1 ед. = 0,2 м")
CARR, WALK, CURB, CORNER_R = 12.0, 5.0, 0.15, 6.0      # v10 §6 city street; curb ~15 cm (v10 §4); corner radius for a van turn
HW = (CARR / 2 + WALK) / U                # 55 u: street axis -> facade line
CW = CARR / 2 / U                         # 30 u: street axis -> curb
ALLEY = 5.6 / U                           # v10 §4 dead ends 5.6 m
FLOOR_H, GROUND_H, PARAPET = 3.4, 4.4, 0.9
H_SET = (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 20, 22, 30, 46, 70)
FIXES, QUESTIONS = [], []

BRICK_COLS = {'#A65A45', '#7E4436', '#B8735A', '#8C6A4F', '#7A5560'}
PALETTE = ('#A65A45', '#7E4436', '#B8735A', '#C9A35A', '#74805A', '#4F7D7A', '#5D7189', '#B98478', '#D9C9A8', '#BE9A72', '#A9A69C',
           '#4F6B55', '#B98B4E', '#7A5560', '#8C6A4F', '#9FB0A8')     # build_gorod_v31 HOUSE_COLS = v02 §8.5 city palette
AWNINGS = ('#3F5E4A', '#7A3B36', '#3E4C5E', '#A0603F', '#B08A3E', '#3A3D40', '#3F6E6A', '#D8CDB4', '#6B4E6A')
GROUND_FLOORS = ('storefront', 'cafe_terrace', 'office_lobby', 'stoop_doors', 'rollshutter_shop', 'plain_windows')
LEGEND = {
    '01': 'twin tower 1 (west): round faceted dark-blue glass, ~200 m / 55 floors, light crown on top, glass belt at podium level',
    '02': 'twin tower 2 (east): identical to 01',
    '35': 'big street screen on the podium between the towers, faces the plaza (Tramduro from app Z)',
    '03': 'underground parking under both towers: 1 level, 2 identical two-way ramps (from N2 and N3), van turns inside',
    '15': 'golden cartoon Tramduro monument (raised arm, no likeness) on a dark granite podium D 8.8 m, ring of 18 dry fountains R 9.2 m',
    '36': 'police booth at the monument', '08': 'ATM (one per district)',
    '16': 'glass pavilion ~18 x 10 m (cafe / shop), terrace with 3 yellow umbrellas', '17': 'glass pavilion with terrace',
    '18': 'glass pavilion with terrace', '19': 'glass pavilion with terrace',
    '04': 'plaza "Water Axis" (pedestrian, no trees): tribune stair + water cascade, mirror pool 16 x 60 m, monument, pavilions',
    '14': 'bus stop on the boulevard at the plaza', '23': 'square NW (trees only here and in 20)',
    '42': 'wide service yard, entry from Vb: concrete, bins, roll-shutter gate, bollards',
    '43': 'wide service yard, entry from Vd: concrete, bins, roll-shutter gate, bollards',
    '11': 'police 2 (NE)', '12': 'taxi depot with its own stand, exit onto Vd', '20': 'square with pond (NE)',
    '41': 'gas station at the west entry: canopy with 3 pump islands + shop', '10': 'police 1 (SW) with a rotunda on the corner',
    '07': 'van shop: rectangular, roll-shutter gates straight onto the street', '05': 'glass office south of the plaza',
    '06': 'glass office south of the plaza', '40': 'corner diner (chrome, red stripe)',
    '13': 'BASE 4 (plan no. 13): drive-through arch from Hse2 -> closed courtyard -> brick garage with roll shutter'}


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def fix(where, ru, why):
    FIXES.append({'id': 'downtown-%02d' % (len(FIXES) + 1), 'where_plan': where, 'ru': ru, 'why_ru': why})


def question(ru, options, default, applied):
    QUESTIONS.append({'id': 'downtown-q%d' % (len(QUESTIONS) + 1), 'ru': ru, 'options_ru': options, 'default': default, 'applied': applied})


# ---------------------------------------------------------------- small plan-unit geometry (x east, y SOUTH)
def R(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def bb(pl):
    xs, ys = [p[0] for p in pl], [p[1] for p in pl]
    return (min(xs), min(ys), max(xs), max(ys))


def parea(pl):
    return abs(sum(pl[i - 1][0] * pl[i][1] - pl[i][0] * pl[i - 1][1] for i in range(len(pl)))) / 2.0


def pcen(pl):
    return (sum(p[0] for p in pl) / len(pl), sum(p[1] for p in pl) / len(pl))


def is_rect(pl):
    if len(pl) != 4:
        return False
    x0, y0, x1, y1 = bb(pl)
    return all((abs(p[0] - x0) < 0.05 or abs(p[0] - x1) < 0.05) and (abs(p[1] - y0) < 0.05 or abs(p[1] - y1) < 0.05) for p in pl)


def pin(pt, pl):
    c = False
    for i in range(len(pl)):
        (x0, y0), (x1, y1) = pl[i - 1], pl[i]
        if (y0 > pt[1]) != (y1 > pt[1]) and pt[0] < x0 + (pt[1] - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def clip_axis(pl, ax, v, keep_le):
    out, n = [], len(pl)
    for i in range(n):
        a, b = pl[i], pl[(i + 1) % n]
        ia = a[ax] <= v + 1e-9 if keep_le else a[ax] >= v - 1e-9
        ib = b[ax] <= v + 1e-9 if keep_le else b[ax] >= v - 1e-9
        if ia:
            out.append(a)
        if ia != ib:
            t = (v - a[ax]) / (b[ax] - a[ax])
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    q = []
    for p in out:
        if not q or math.hypot(p[0] - q[-1][0], p[1] - q[-1][1]) > 1e-6:
            q.append(p)
    if len(q) > 1 and math.hypot(q[0][0] - q[-1][0], q[0][1] - q[-1][1]) < 1e-6:
        q.pop()
    return q


def clip_rect(pl, r):
    q = clip_axis(pl, 0, r[0], False)
    q = clip_axis(q, 0, r[2], True) if q else q
    q = clip_axis(q, 1, r[1], False) if q else q
    q = clip_axis(q, 1, r[3], True) if q else q
    return q


def overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])


def circle_pts(c, r, n=24):
    return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def dedup_closed(pts):
    return pts[:-1] if len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05 else pts


# ---------------------------------------------------------------- transform chain
def load_chain():
    img = None
    for nm, at, M, ids, s0, s1 in svg_tags(svg_text()):
        if nm == 'image' and 'downtown_v31_world.png' in (attr(at, 'href') or ''):
            img = {'M': M, 'x': anum(at, 'x'), 'y': anum(at, 'y'), 'w': anum(at, 'width'), 'h': anum(at, 'height'), 'group': ids[-1]}
    assert img, 'downtown_v31_world.png not found in the master SVG'
    plan = read(PLAN_SVG)
    m = re.search(r'<svg[^>]*\swidth="([\d.]+)" height="([\d.]+)" viewBox="([^"]+)"', plan)
    pw, ph = float(m.group(1)), float(m.group(2))
    vb = [float(v) for v in m.group(3).split()]
    k = float(re.search(r'dt\.width / ([\d.]+)\)', read(WORLD_PY)).group(1))
    iw, ih = int(pw / k), int(ph / k)

    def master(p):
        return apply(img['M'], (img['x'] + (p[0] - vb[0]) * pw / vb[2] / k * img['w'] / iw,
                                img['y'] + (p[1] - vb[1]) * ph / vb[3] / k * img['h'] / ih))

    def pre(p):
        return u2m(*master(p))

    o, ex, ey = pre((0.0, 0.0)), pre((1000.0, 0.0)), pre((0.0, 1000.0))
    lin = (o[0], (ex[0] - o[0]) / 1000.0, o[1], (o[1] - ey[1]) / 1000.0)
    s_ref = shift_m(*pre((1170.0, 760.0)))                                # district body (plaza / boulevard)

    def W(p):
        if RIGID:
            q = pre(p)
            return (q[0] + s_ref[0], q[1] + s_ref[1])
        return pic_of_pre(pre(p))

    def Wpic(p):                                                          # what the v85 raster shows (post_shift_v85.shift_image)
        return pic_of_pre(pre(p))

    def Winv(q):                                                          # rigid inverse
        return ((q[0] - s_ref[0] - lin[0]) / lin[1], (lin[2] - (q[1] - s_ref[1])) / lin[3])

    info = {'img': img, 'vb': vb, 'pw': pw, 'ph': ph, 'k': k, 'iw': iw, 'ih': ih, 'lin': lin, 's_ref': s_ref,
            'master0': master((0.0, 0.0))}
    return W, Winv, Wpic, (lambda p: u2w(*master(p))), info


def pic_of_pre(p):
    """post_shift_v85.shift_image samples the source at output - shift_m(output): the drawn point q solves q = p + shift_m(q)
    (common.u2w evaluates shift_m at the pre-shift point instead -> off in the gradient bands)."""
    q = (p[0], p[1])
    for _ in range(60):
        dx, dy = shift_m(q[0], q[1])
        q = (p[0] + dx, p[1] + dy)
    return q


# ---------------------------------------------------------------- generator model (streets, blocks, shrink)
def gen_model():
    src = read(PLAN_PY)
    road, sw = map(float, re.search(r'^ROAD, SW = ([\d.]+), ([\d.]+)', src, re.M).groups())
    road0, sw0 = map(float, re.search(r'^ROAD_OLD, SW_OLD = ([\d.]+), ([\d.]+)', src, re.M).groups())
    axis = float(re.search(r'^AXIS = (\d+)', src, re.M).group(1))
    Hh = float(re.search(r'^W, H = \d+, (\d+)', src, re.M).group(1))
    assert abs(road * U - CARR) < 1e-6 and abs(sw * U - WALK) < 1e-6, 'plan street profile is not 12 + 2 x 5 m'
    tok = lambda t: axis if t == 'AXIS' else (Hh if t == 'H' else float(t))
    blk = src[src.index('ST = {'):src.index('\nCANAL')]
    st = {}
    for name, body, cap in re.findall(r"'(\w+)': St\(\[([^\]]*)\], ROAD, SW(?:, cap='(\w+)')?\)", blk):
        st[name] = {'pts': [(tok(a), tok(b)) for a, b in re.findall(r'\(([\w.]+), ([\w.]+)\)', body)], 'cap': cap or 'butt'}
    ring = re.findall(r"'(\w+)'", re.search(r'^RING = \(([^)]*)\)', src, re.M).group(1))
    d0 = src.index('DISTRICT = [')
    district = [(float(a), float(b)) for a, b in re.findall(r'\(([\d.]+), ([\d.]+)\)', src[d0:src.index(']', d0)])]
    b0 = src.index('BLK = {')
    ns = {'R': R}
    exec(src[b0:src.index('\n}', b0) + 2], ns)                            # the block literal only (rectangles / lists)
    shrink = (road / 2 + sw) - (road0 / 2 + sw0)
    blocks = {}
    for kname, pl in ns['BLK'].items():
        o = bb(pl)
        n = (o[0] + shrink, o[1] + shrink, o[2] - shrink, o[3] - shrink)
        sx, sy = (n[2] - n[0]) / (o[2] - o[0]), (n[3] - n[1]) / (o[3] - o[1])
        blocks[kname] = {'old': o, 'new': n, 'sx': sx, 'sy': sy,
                         'poly': [(n[0] + (p[0] - o[0]) * sx, n[1] + (p[1] - o[1]) * sy) for p in pl]}
    hw = road / 2 + sw
    for m_ in re.finditer(r'x0, x1, y0, y1 = (\d+) - hw, \d+ \+ hw, (\d+) \+ hw, (\d+) - hw', src):      # v28 rows on closed Vd / Vs3
        x, y0, y1 = float(m_.group(1)), float(m_.group(2)), float(m_.group(3))
        name = 'VDF' if x == 1840 else 'VSF'
        r_ = (x - hw, y0 + hw, x + hw, y1 - hw)
        blocks[name] = {'old': r_, 'new': r_, 'sx': 1.0, 'sy': 1.0, 'poly': R(*r_)}
    return {'st': st, 'ring': ring, 'district': district, 'blocks': blocks, 'shrink': shrink, 'axis': axis, 'H': Hh, 'road': road, 'sw': sw}


def blk_of(model, p, pad=0.6):
    for k, b in model['blocks'].items():
        n = b['new']
        if n[0] - pad <= p[0] <= n[2] + pad and n[1] - pad <= p[1] <= n[3] + pad:
            return k
    return None


# ---------------------------------------------------------------- plan SVG elements
def plan_elements():
    s = read(PLAN_SVG)
    els = []
    for nm, at, M, ids, s0, s1 in svg_tags(s):
        e = {'tag': nm, 'g': ids[-1] if ids else '', 'fill': attr(at, 'fill'), 'stroke': attr(at, 'stroke'),
             'sw': float(attr(at, 'stroke-width') or 0), 'dash': attr(at, 'stroke-dasharray')}
        if nm == 'polygon':
            e['pts'] = dedup_closed(points_of(at))
        elif nm == 'polyline':
            e['pts'] = points_of(at)
        elif nm == 'circle':
            e['c'], e['r'] = (anum(at, 'cx'), anum(at, 'cy')), anum(at, 'r')
        elif nm == 'text':
            e['pos'], e['text'] = (anum(at, 'x'), anum(at, 'y') - 0.5), s[s1:s.index('</text>', s1)]
        els.append(e)
    return els


def sel(els, **kw):
    return [e for e in els if all((e.get(k) == v) if not callable(v) else v(e.get(k)) for k, v in kw.items())]


def match_buildings(els, model):
    """bld() writes SHADOW[i] = footprint + h * (0.55, 0.75) (both through the v28 block map) and BLD[i] = footprint; walk both."""
    bel = [e for e in els if e['g'] == 'buildings' and e['tag'] == 'polygon' and e['fill'] not in (None, 'none')]
    shs = sel(els, g='shadows', tag='polygon')
    out, j = [], 0
    for i, sh in enumerate(shs):
        S = sh['pts']
        for k in range(j, min(len(bel), j + 15)):
            B = bel[k]['pts']
            if len(B) != len(S):
                continue
            d = [(q[0] - p[0], q[1] - p[1]) for p, q in zip(B, S)]
            mx, my = sum(v[0] for v in d) / len(d), sum(v[1] for v in d) / len(d)
            if max(max(abs(v[0] - mx), abs(v[1] - my)) for v in d) > 0.45 or mx < 0.5 or my < 0.5:
                continue
            bk = blk_of(model, pcen(B), 0.0)
            sx, sy = (model['blocks'][bk]['sx'], model['blocks'][bk]['sy']) if bk else (1.0, 1.0)
            h = 0.5 * (mx / 0.55 / sx + my / 0.75 / sy)
            hs = min(H_SET, key=lambda v: abs(v - h))
            assert abs(hs - h) < 0.4, ('shadow height off the bld() classes', i, h)
            out.append({'pl': list(B), 'fill': bel[k]['fill'], 'stroke': bel[k]['stroke'], 'h': hs, 'block': bk, 'src_index': i})
            j = k + 1
            break
        else:
            raise SystemExit('shadow %d not matched to a building polygon' % i)
    assert len(out) == len(shs)
    return out


# ---------------------------------------------------------------- streets, bands, junctions
def street_model(model):
    st = {k: {'pts': list(v['pts']), 'cap': v['cap']} for k, v in model['st'].items()}
    ring = set(model['ring'])
    for n1 in list(st):                                                    # collinear duplicates (Vd runs 36 m on top of N3's bend)
        for n2 in list(st):
            if n1 == n2 or n2 in ring or n1 not in ring:
                continue
            for a, b in zip(st[n1]['pts'][:-1], st[n1]['pts'][1:]):
                p0, p1 = st[n2]['pts'][0], st[n2]['pts'][1]
                ax = 0 if abs(a[0] - b[0]) < 1e-6 else 1                    # 0: segment along y (x const)
                if abs(p0[ax] - p1[ax]) > 1e-6 or abs(p0[ax] - a[ax]) > 1e-6 or abs(a[ax] - b[ax]) > 1e-6:
                    continue
                lo, hi = sorted((a[1 - ax], b[1 - ax]))
                if abs(p0[1 - ax] - lo) < 1e-6 and hi < p1[1 - ax] and hi - lo > 1:
                    new0 = list(p0)
                    new0[1 - ax] = hi
                    st[n2]['pts'][0] = tuple(new0)
                    st[n2]['trimmed'] = (n1, (hi - lo) * U, tuple(p0), tuple(new0))
    for name in ('Va2', 'Vds'):                                            # continuation south of S1 = beach entries (see FIX)
        p = st[name]['pts']
        st[name]['pts'] = [p[0], (p[0][0], 1210.0)]
        st[name]['beyond_S1_plan'] = p[-1]
    return st


def street_bands(st):
    bands = []
    for name, s in st.items():
        pts = s['pts']
        n = len(pts) - 1
        for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
            e0 = 0.0 if (i == 0 and s['cap'] == 'butt') else HW
            e1 = 0.0 if (i == n - 1 and s['cap'] == 'butt') else HW
            if abs(a[1] - b[1]) < 1e-6:
                lo, hi = (a[0] - e0, b[0] + e1) if a[0] < b[0] else (b[0] - e1, a[0] + e0)
                bands.append({'street': name, 'rect': (lo, a[1] - HW, hi, a[1] + HW), 'ax': 1, 'axis': a[1], 'seg': (a, b)})
            else:
                lo, hi = (a[1] - e0, b[1] + e1) if a[1] < b[1] else (b[1] - e1, a[1] + e0)
                bands.append({'street': name, 'rect': (a[0] - HW, lo, a[0] + HW, hi), 'ax': 0, 'axis': a[0], 'seg': (a, b)})
    return bands


def seg_inter(a, b, c, d):
    r, s = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-9:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    if -1e-6 <= t <= 1 + 1e-6 and -1e-6 <= u <= 1 + 1e-6:
        return (a[0] + r[0] * t, a[1] + r[1] * t)
    return None


def legs(st, name, j):
    out = []
    for a, b in zip(st[name]['pts'][:-1], st[name]['pts'][1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        t = (j[0] - a[0]) * u[0] + (j[1] - a[1]) * u[1]
        if t < -1.5 or t > L + 1.5 or abs((j[0] - a[0]) * u[1] - (j[1] - a[1]) * u[0]) > 1.5:
            continue
        if L - t > 1.5:
            out.append((u, L - t))
        if t > 1.5:
            out.append(((-u[0], -u[1]), t))
    uniq = []
    for v, L in out:
        if all(v[0] * w[0] + v[1] * w[1] < 0.995 for w, _ in uniq):
            uniq.append((v, L))
    return uniq


def junctions(st):
    out = []
    names = list(st)
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            for a, b in zip(st[n1]['pts'][:-1], st[n1]['pts'][1:]):
                for c, d in zip(st[n2]['pts'][:-1], st[n2]['pts'][1:]):
                    p = seg_inter(a, b, c, d)
                    if p is None:
                        continue
                    for jj in out:
                        if math.hypot(jj[0][0] - p[0], jj[0][1] - p[1]) < 3:
                            jj[1].update((n1, n2))
                            break
                    else:
                        out.append((p, {n1, n2}))
    for p0, n0 in [(p, {n}) for n, s in st.items() for p in s['pts'][1:-1]]:                # bends of one street
        if not any(math.hypot(jj[0][0] - p0[0], jj[0][1] - p0[1]) < 3 for jj in out):
            out.append((p0, n0))
    return out


# ---------------------------------------------------------------- colours
def calm_bright(col, key):
    """v10 §7.5: brighter and more 'American' but not acid: HLS lightness +0.05, saturation x1.08 capped at 0.55, small per-house jitter."""
    r_, g_, b_ = [int(col[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    h, l, s = colorsys.rgb_to_hls(r_, g_, b_)
    h = (h + (h01(key + 'hue') - 0.5) * 0.03) % 1.0
    l = min(0.80, max(0.30, l + 0.05 + (h01(key + 'l') - 0.5) * 0.05))
    s = min(0.55, s * 1.08)
    return '#%02X%02X%02X' % tuple(int(round(c * 255)) for c in colorsys.hls_to_rgb(h, l, s))


# ---------------------------------------------------------------- build
def build():
    W, Winv, Wpic, Wu2w, info = load_chain()
    model = gen_model()
    st = street_model(model)
    els = plan_elements()
    svg_ax = [e['pts'] for e in sel(els, g='roads', tag='polyline', stroke='#5F666C', sw=60.0)]
    assert len(svg_ax) == len(model['st']) and all(
        len(a) == len(s['pts']) and all(abs(p[0] - q[0]) < 0.06 and abs(p[1] - q[1]) < 0.06 for p, q in zip(a, s['pts']))
        for a, s in zip(svg_ax, model['st'].values())), 'SVG asphalt != generator ST'
    bands = street_bands(st)
    for name, s_ in st.items():
        if 'trimmed' in s_:
            n1, L, p0, p1 = s_['trimmed']
            fix(p1, 'Улица %s на плане первые %.0f м идёт поверх %s (одна и та же ось) — в данных этот кусок один раз (%s), %s начинается от угла %s буквой Т.'
                % (name, L, n1, n1, name, n1), 'v10 §6: накладывающиеся полосы — это не перекрёсток; покрытие сплошное, без двойного полотна.')
    labels = {e['text']: e['pos'] for e in sel(els, g='numbers', tag='text')}
    WL = lambda pl: [rnd2(W(p)) for p in pl]

    # ------------------------------------------------ buildings: match + classify
    blds = match_buildings(els, model)
    arch_el = sel(els, g='buildings', tag='polygon', fill='none', stroke='#6E6A60')[0]['pts']
    loft_lines = sel(els, g='buildings', tag='polyline', stroke='#C9A58F')
    gas_lot = sel(els, g='squares_and_lots', fill='#C9CCCB')[0]['pts']
    special = {'#2E4E73': 'tower', '#B7C7D4': 'podium', '#A9C4D3': 'pavilion', '#3F6C99': 'tower_round', '#A7BED2': 'podium_round',
               '#4C78A3': 'glass_office', '#E2DCCC': 'classical', '#B9C8E6': 'police', '#E5D5A0': 'taxi_depot', '#E3A982': 'van_shop',
               '#D7DDE1': 'diner'}
    for b in blds:
        b['pl0'] = list(b['pl'])
        pl, f, h = b['pl'], b['fill'], b['h']
        kind = special.get(f, 'house')
        if kind == 'house':
            if h == 8:
                kind = 'alley_plug'
            elif h == 12 and f == '#B8735A':
                kind = 'base_garage'
            elif h == 6 and pin(pcen(pl), gas_lot):
                kind = 'gas_shop'
            elif h == 6:
                kind = 'podium_annex'
            elif all(bb(pl)[i] - 0.5 <= bb(arch_el)[i] for i in (0, 1)) and all(bb(arch_el)[i] <= bb(pl)[i] + 0.5 for i in (2, 3)):
                kind = 'arch_house'
            elif h == 11 and sum(1 for e in loft_lines if pin(pcen(e['pts']), pl)) >= 3:
                kind = 'loft'
        b['kind'] = kind
        b['label'] = next((k for k, p in labels.items() if pin(p, pl) and k not in ('04', '03')), None)
    kind_labels = {'diner': ('40',), 'police': ('10', '11'), 'glass_office': ('05', '06'), 'pavilion': ('16', '17', '18', '19'), 'van_shop': ('07',),
                   'taxi_depot': ('12',), 'tower': ('01', '02'), 'gas_shop': ('41',), 'base_garage': ('13',)}
    for b in blds:                                                         # labels drawn next to (not on) their building
        if b['label'] is None and b['kind'] in kind_labels:
            c = pcen(b['pl'])
            b['label'] = min(kind_labels[b['kind']], key=lambda k: math.hypot(labels[k][0] - c[0], labels[k][1] - c[1]))
    # rotunda of police 1: a plain circle in BLD (no bld() -> no shadow)
    rot = [e for e in sel(els, g='buildings', tag='circle', fill='#B9C8E6')]
    for e in rot:
        blds.append({'pl': circle_pts(e['c'], e['r'], 20), 'pl0': circle_pts(e['c'], e['r'], 20), 'fill': e['fill'], 'stroke': e['stroke'], 'h': 10,
                     'block': blk_of(model, e['c']),
                     'kind': 'police_rotunda', 'label': '10', 'src_index': None})
    # stable ids: sort by plan position (north -> south, west -> east)
    order = sorted(range(len(blds)), key=lambda i: (round(pcen(blds[i]['pl'])[1] / 10), pcen(blds[i]['pl'])[0]))
    blds = [blds[i] for i in order]
    k_house = 0
    for b in blds:
        if b['kind'] in ('tower',):
            b['id'] = '05-' + ('01' if pcen(b['pl'])[0] < model['axis'] else '02')
        elif b['kind'] in ('glass_office', 'police', 'taxi_depot', 'van_shop', 'diner', 'pavilion', 'gas_shop') and b['label']:
            b['id'] = '05-' + b['label']
        elif b['kind'] == 'police_rotunda':
            b['id'] = '05-10r'
        else:
            b['id'] = '05-B%03d' % k_house
            k_house += 1
    byid = {b['id']: b for b in blds}

    # ------------------------------------------------ FIX 1: houses inside the 22 m street profile (v28 shrink at L-block inner corners)
    moves = []
    for it in range(3):
        changed = False
        for b in blds:
            for bd in bands:
                ox, oy = overlap(bb(b['pl']), bd['rect'])
                if min(ox, oy) <= 0.5:
                    continue
                ax = 0 if ox < oy else 1
                c = pcen(b['pl'])
                bc = ((bd['rect'][0] + bd['rect'][2]) / 2, (bd['rect'][1] + bd['rect'][3]) / 2)
                le = c[ax] < bc[ax]
                v = bd['rect'][ax] if le else bd['rect'][ax + 2]
                old = bb(b['pl'])[ax + 2] if le else bb(b['pl'])[ax]
                if len(b['pl']) > 8:                                       # round towers / rotunda: move, never cut a circle
                    dv = v - old
                    group_ = [t for t in blds if t['kind'] == 'tower'] if b['kind'] == 'tower' else [b]   # twins stay identical
                    for t in group_:
                        t['pl'] = [(q[0] + (dv if ax == 0 else 0.0), q[1] + (dv if ax == 1 else 0.0)) for q in t['pl']]
                    moves.append({'id': b['id'], 'ax': ax, 'le': le, 'old': old, 'new': v, 'street': bd['street'], 'depth_m': min(ox, oy) * U,
                                  'cross': None, 'moved': [t['id'] for t in group_]})
                    changed = True
                    continue
                b['pl'] = clip_axis(b['pl'], ax, v, le)
                moves.append({'id': b['id'], 'ax': ax, 'le': le, 'old': old, 'new': v, 'street': bd['street'], 'depth_m': min(ox, oy) * U,
                              'cross': (bb(b['pl'])[1 - ax], bb(b['pl'])[3 - ax])})
                changed = True
        if not changed:
            break
    prop = []
    for mv in list(moves):                                                # neighbours that shared the moved wall follow it (no slit)
        if mv['cross'] is None:
            continue
        for n in blds:
            if n['id'] == mv['id'] or not is_rect(n['pl']):
                continue
            nb = bb(n['pl'])
            face = nb[mv['ax']] if mv['le'] else nb[mv['ax'] + 2]          # neighbour's opposite face
            lo, hi = nb[1 - mv['ax']], nb[3 - mv['ax']]
            if abs(face - mv['old']) > 0.6 or min(hi, mv['cross'][1]) - max(lo, mv['cross'][0]) < 1.0:
                continue
            q = list(nb)
            if mv['le']:
                q[mv['ax']] = mv['new']
            else:
                q[mv['ax'] + 2] = mv['new']
            if any(min(overlap(q, bd['rect'])) > 0.5 for bd in bands):
                continue
            n['pl'] = R(*q)
            prop.append((n['id'], mv['id'], abs(mv['new'] - mv['old']) * U))
    by_street, by_round = {}, {}
    for mv in moves:
        if mv['cross'] is None:
            by_round.setdefault(mv['id'], []).append(mv)
        else:
            by_street.setdefault(mv['street'], []).append(mv)
    for bid_, mvs in sorted(by_round.items()):
        moved = sorted({t for m_ in mvs for t in m_['moved']})
        fix(rnd2(pcen(byid[bid_]['pl'])),
            'Круглое здание %s (%s) заходило на тротуар %s (%s м) — сдвинуто целиком внутрь квартала, форма и размер как на плане%s.'
            % (bid_, byid[bid_]['kind'], '/'.join(m_['street'] for m_ in mvs), '/'.join('%.1f' % m_['depth_m'] for m_ in mvs),
               '; обе башни-близнеца (%s) сдвинуты одинаково' % ', '.join(moved) if len(moved) > 1 else ''),
            'Тротуар 5 м (v10 §6); круглую башню / ротонду нельзя срезать прямой линией.')
    for sname, mvs in sorted(by_street.items()):
        ids = sorted({m_['id'] for m_ in mvs})
        kinds = sorted({byid[i]['kind'] for i in ids})
        dmax = max(m_['depth_m'] for m_ in mvs)
        fix(rnd2(pcen(byid[ids[0]]['pl'])),
            'Улица %s: %d дом(а) (%s) заходили на тротуар до %.1f м — фасад отодвинут на линию 22-метрового профиля (%s)%s.'
            % (sname, len(ids), ', '.join(kinds), dmax, ', '.join(ids),
               '; соседний дом дотянут до новой стены, чтобы не было щели' if any(p[1] in ids for p in prop) else ''),
            'План v28–v31 ужал кварталы на 2,75 м с каждой стороны, но внутренние углы Г-образных кварталов (07/SC1, SE2 у залома бульвара, '
            'площадь у Nj) не сдвинулись — тротуар там 1–3 м вместо 5 м (v10 §6: 12 + 2 × 5 м = 22 м между фасадами).')

    # ------------------------------------------------ FIX 2: dead-end alleys back to 5.6 m (v10 §4)
    alley_els = sel(els, g='squares_and_lots', tag='polygon', fill='#9DA2A2')
    dws = [e['pts'] for e in sel(els, g='roads', tag='polygon', fill='#9DA2A2')]
    dead_lines = [e['pts'] for e in sel(els, g='buildings', tag='polyline', stroke='#3C3A36')]
    plugs = [b for b in blds if b['kind'] == 'alley_plug']
    alleys = []
    for e in alley_els:
        r_ = bb(e['pts'])
        horiz = (r_[2] - r_[0]) > (r_[3] - r_[1])
        ax_c = 1 if horiz else 0                                           # cross axis
        c = (r_[ax_c] + r_[ax_c + 2]) / 2
        w0 = r_[ax_c + 2] - r_[ax_c]
        alleys.append({'rect0': r_, 'horiz': horiz, 'cax': ax_c, 'c': c, 'w0': w0})
    groups = []                                                            # alleys on one line (pair with a plug) -> one group
    for a in alleys:
        for g in groups:
            if g[0]['horiz'] == a['horiz'] and abs(g[0]['c'] - a['c']) < 1.0 and blk_of(model, pcen(R(*g[0]['rect0']))) == blk_of(model, pcen(R(*a['rect0']))):
                g.append(a)
                break
        else:
            groups.append([a])
    alley_out = []
    for gi, g in enumerate(groups):
        a0 = g[0]
        cax, c = a0['cax'], a0['c']
        aax = 1 - cax
        lo, hi = c - ALLEY / 2, c + ALLEY / 2
        blk = blk_of(model, pcen(R(*a0['rect0'])))
        bnew = model['blocks'][blk]['new']
        span = (bnew[aax], bnew[aax + 2])
        rects = []
        for a in g:
            q = list(a['rect0'])
            q[cax], q[cax + 2] = lo, hi
            a['rect'] = tuple(q)
            rects.append(a['rect'])
        g_plugs = [p for p in plugs if blk_of(model, pcen(p['pl'])) == blk and abs(pcen(p['pl'])[cax] - c) < 3]
        for p in g_plugs:
            q = list(bb(p['pl']))
            q[cax], q[cax + 2] = lo, hi
            p['pl'] = R(*q)
        whole = [0, 0, 0, 0]
        whole[cax], whole[cax + 2], whole[aax], whole[aax + 2] = lo, hi, span[0], span[1]
        moved = 0
        for b in blds:
            if b in g_plugs or b['kind'] != 'house' and b['kind'] not in ('arch_house', 'loft'):
                continue
            ox, oy = overlap(bb(b['pl']), whole)
            if min(ox, oy) <= 0.05:
                continue
            le = pcen(b['pl'])[cax] < c
            b['pl'] = clip_axis(b['pl'], cax, lo if le else hi, le)
            moved += 1
        for i, d in enumerate(dws):                                       # curb drops at the alley mouths follow
            dr = bb(d)
            if abs((dr[cax] + dr[cax + 2]) / 2 - c) < 1.0 and blk_of(model, pcen(d), 30.0) == blk:
                q = list(dr)
                q[cax], q[cax + 2] = lo, hi
                dws[i] = R(*q)
        mouths = []
        for a in g:
            r_ = a['rect']
            for end in (0, 1):
                v = r_[aax] if end == 0 else r_[aax + 2]
                if abs(v - span[end]) < 0.6:                              # open end at the block edge
                    p = [0, 0]
                    p[aax], p[cax] = v, c
                    mouths.append({'pos': tuple(p), 'dir': (-1 if end == 0 else 1), 'rect': r_})
        alley_out.append({'id': '05-alley-%s' % blk, 'block': blk, 'cax': cax, 'aax': aax, 'c': c, 'lo': lo, 'hi': hi, 'rects': rects,
                          'plugs': g_plugs, 'mouths': mouths, 'w0_m': min(a['w0'] for a in g) * U, 'houses_trimmed': moved,
                          'pair': len(g) == 2, 'span': span})
    fix(None, 'Глухие переулки (%s) были %.1f–%.1f м — расширены до 5,6 м: задние стены домов вдоль переулка отодвинуты на %.2f–%.2f м, '
              'затычки и торцевые дома растянуты на всю ширину.' % (', '.join(sorted(a['block'] for a in alley_out)),
                                                                      min(a['w0_m'] for a in alley_out), max(a['w0_m'] for a in alley_out),
                                                                      min((5.6 - a['w0_m']) / 2 for a in alley_out), max((5.6 - a['w0_m']) / 2 for a in alley_out)),
        'План v28 ужал кварталы вместе с переулками (5,6 м -> 4,5–5,0 м); v10 §4: тупик 5,6 м, чтобы бусик заехал и выехал задом.')

    # ------------------------------------------------ FIX 3: slits 0.1-1.8 m between back-to-back buildings (v02 §8.5 "Не: щели между домами")
    court13 = None
    for e in sel(els, g='squares_and_lots', tag='polygon', fill='#D8D4CA'):
        if pin(labels['13'], e['pts']):
            court13 = bb(clip_axis(e['pts'], 1, bb(arch_el)[3], False))
    movable = ('house', 'arch_house', 'loft', 'base_garage', 'classical')
    pref = {'house': 0, 'arch_house': 1, 'loft': 1, 'base_garage': 2, 'classical': 3}
    slits = []
    for it in range(2):
        rects = [(b, bb(b['pl'])) for b in blds] + [(None, court13)]
        for i, (A, ra) in enumerate(rects):
            for B, rb in rects[i + 1:]:
                for ax in (0, 1):
                    lo, hi = max(ra[1 - ax], rb[1 - ax]), min(ra[3 - ax], rb[3 - ax])
                    if hi - lo < 10:
                        continue
                    if rb[ax] - ra[ax + 2] > 0:
                        first, second, rf, rs = A, B, ra, rb
                    elif ra[ax] - rb[ax + 2] > 0:
                        first, second, rf, rs = B, A, rb, ra
                    else:
                        continue
                    g = rs[ax] - rf[ax + 2]
                    if not 0.5 <= g <= 9.0:
                        continue
                    cand = [x for x in (second, first) if x is not None and x['kind'] in movable and is_rect(x['pl'])]
                    if not cand:
                        continue
                    mv = min(cand, key=lambda x: (pref[x['kind']], 0 if x is second else 1))
                    q = list(bb(mv['pl']))
                    if mv is second:
                        q[ax] = rf[ax + 2]
                    else:
                        q[ax + 2] = rs[ax]
                    if any(o is not mv and min(overlap(q, bb(o['pl']))) > 0.3 for o in blds) or                             (court13 and min(overlap(q, court13)) > 0.3) or any(min(overlap(q, bd['rect'])) > 0.5 for bd in bands):
                        continue
                    mv['pl'] = R(*q)
                    other = first if mv is second else second
                    slits.append((mv['id'], other['id'] if other else 'court 13', round(g * U, 2), blk_of(model, pcen(mv['pl']))))
        if not slits:
            break
    if slits:
        blks = sorted({sl[3] for sl in slits if sl[3]})
        fix(None, '%d щелей %.1f–%.1f м между домами спиной к спине (кварталы %s) закрыты: задняя стена дома дотянута до соседа%s.'
            % (len(slits), min(sl[2] for sl in slits), max(sl[2] for sl in slits), ', '.join(blks),
               '; двор базы 4 с юга закрыт глухими задними стенами ряда домов к S1 (на плане — отдельная стена и щель 1,7 м за ней)'
               if any(sl[1] == 'court 13' for sl in slits) else ''),
            'Генератор оставлял зазор 6 ед. (1,2 м до ужатия) между рядами; v02 §8.5: дома сплошной стеной, без щелей.')

    # ------------------------------------------------ overlaps between buildings (only towers on their podiums are intended)
    ov = []
    for i, a in enumerate(blds):
        for b in blds[i + 1:]:
            ox, oy = overlap(bb(a['pl']), bb(b['pl']))
            if min(ox, oy) <= 0.3:
                continue
            ar = parea(clip_rect(a['pl'], bb(b['pl']))) if is_rect(b['pl']) else (parea(clip_rect(b['pl'], bb(a['pl']))) if is_rect(a['pl']) else ox * oy)
            kinds = {a['kind'], b['kind']}
            if kinds in ({'tower', 'podium'}, {'tower_round', 'podium_round'}, {'police', 'police_rotunda'}):
                continue
            if ar > 1.0:
                ov.append((a['id'], b['id'], round(ar * U * U, 2)))
    assert not ov, ('unexpected building overlaps', ov)

    # ------------------------------------------------ attributes
    corner = lambda b: b['kind'] == 'house' and b['h'] >= 18
    adj = {b['id']: set() for b in blds}
    for i, a in enumerate(blds):
        ra = bb(a['pl'])
        for b in blds[i + 1:]:
            rb = bb(b['pl'])
            ox, oy = overlap(ra, rb)
            if (abs(ox) < 0.8 and oy > 2) or (abs(oy) < 0.8 and ox > 2):
                adj[a['id']].add(b['id'])
                adj[b['id']].add(a['id'])
    house_like = ('house', 'arch_house', 'loft', 'alley_plug')
    recol = 0
    for b in blds:                                                         # plan colour, neighbours never the same colour
        b['col'] = b['fill']
    for b in blds:
        if b['kind'] not in house_like:
            continue
        taken = {byid[n]['col'] for n in adj[b['id']]}
        if b['col'] in taken:
            pool = [c for c in PALETTE if c not in taken]
            b['col'] = pool[int(h01(b['id'] + 'col') * len(pool))]
            recol += 1
    if recol:
        fix(None, '%d дом(ов) того же цвета, что сосед вплотную, перекрашены в другой цвет палитры плана.' % recol,
            'v02 §8.5 / легенда §6: соседние дома всегда разного цвета.')
    for b in blds:                                                         # floors
        k, h = b['kind'], b['h']
        if k == 'house' or k == 'arch_house':
            lo, hi = {7: (5, 5), 9: (5, 6), 11: (5, 6), 13: (6, 7), 14: (6, 7), 15: (6, 7)}.get(h, (7, 8) if h >= 18 else (5, 6))
            b['fl_range'] = (lo, hi)
            b['floors'] = lo + int(h01(b['id'] + 'fl') * (hi - lo + 1) - 1e-9)
    for b in blds:                                                         # neighbours differ in height where the class allows
        if 'fl_range' in b and any(byid[n].get('floors') == b['floors'] for n in adj[b['id']]):
            lo, hi = b['fl_range']
            alt = [f for f in range(lo, hi + 1) if all(byid[n].get('floors') != f for n in adj[b['id']])]
            if alt:
                b['floors'] = alt[0]
    gf_of, aw_of, slot_of = {}, {}, {}
    for b in sorted(blds, key=lambda b: b['id']):
        if b['kind'] not in ('house', 'arch_house', 'loft'):
            continue
        used = {gf_of.get(n) for n in adj[b['id']]}
        pref = sorted(GROUND_FLOORS, key=lambda g: h01(b['id'] + g))
        if corner(b):                                                      # corners are commercial, but not all cafes
            com = sorted(('cafe_terrace', 'storefront', 'rollshutter_shop', 'office_lobby'), key=lambda g: h01(b['id'] + 'c' + g))
            pref = com + [g for g in pref if g not in com]
        gf_of[b['id']] = next((g for g in pref if g not in used), pref[0])
        if gf_of[b['id']] in ('storefront', 'cafe_terrace', 'rollshutter_shop') and h01(b['id'] + 'aw') < 0.6:
            usedc = {aw_of.get(n) for n in adj[b['id']]}
            aw_of[b['id']] = next(c for c in sorted(AWNINGS, key=lambda c: h01(b['id'] + c)) if c not in usedc)
        brick = b['col'] in BRICK_COLS
        slot = 'downtown_house_brick' if brick else 'downtown_house_stucco'
        if (not corner(b) and b['kind'] == 'house' and gf_of[b['id']] in ('storefront', 'rollshutter_shop') and h01(b['id'] + 'sf') < 0.5
                and all(slot_of.get(n) != 'downtown_storefront' for n in adj[b['id']])):
            slot = 'downtown_storefront'
        slot_of[b['id']] = slot

    # ------------------------------------------------ entrances
    alley_rects = [r_ for a in alley_out for r_ in a['rects']]
    shutters = [bb(e['pts']) for e in sel(els, g='buildings', tag='polygon', fill='#4E5559')]

    def outward(pl, a, b):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        n = (u[1], -u[0])
        c, m_ = pcen(pl), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if n[0] * (m_[0] - c[0]) + n[1] * (m_[1] - c[1]) < 0:
            n = (-n[0], -n[1])
        return u, n, L

    def frontages(pl):
        res = []
        for i in range(len(pl)):
            a, b = pl[i], pl[(i + 1) % len(pl)]
            u, n, L = outward(pl, a, b)
            if L < 3 or (abs(u[0]) > 0.02 and abs(u[1]) > 0.02):
                continue
            m_ = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            for bd in bands:
                ax = bd['ax']                                              # band axis: 1 = street along x (axis y = const)
                if abs(n[ax]) < 0.99:
                    continue
                t = (bd['axis'] - m_[ax]) * n[ax]
                if not (HW - 2 <= t <= HW + 25):
                    continue
                lo_, hi_ = bd['rect'][1 - ax], bd['rect'][3 - ax]
                e_lo, e_hi = min(a[1 - ax], b[1 - ax]), max(a[1 - ax], b[1 - ax])
                ov_ = min(e_hi, hi_ - HW * 0.5) - max(e_lo, lo_ + HW * 0.5)
                if ov_ < 2:
                    continue
                res.append({'street': bd['street'], 't': t, 'a': a, 'b': b, 'n': n, 'L': L, 'range': (max(e_lo, lo_ + HW * 0.5), min(e_hi, hi_ - HW * 0.5)), 'ax': ax})
        res.sort(key=lambda r_: (r_['t'], -r_['L']))
        return res

    def facing(n):
        return round(math.degrees(math.atan2(-n[1], n[0])) % 360.0, 1) + 0.0

    def door_at(fr, f, kind, w, role, key):
        ax = fr['ax']
        lo_, hi_ = fr['range']
        x = lo_ + (hi_ - lo_) * f
        x = min(max(x, lo_ + min(10, (hi_ - lo_) / 2)), hi_ - min(10, (hi_ - lo_) / 2))
        p = [0, 0]
        p[1 - ax], p[ax] = x, fr['a'][ax]
        return {'pos': rnd2(W(p)), 'facing_deg': facing(fr['n']), 'kind': kind, 'w_m': w, 'benches': 0, 'role': role, 'street': fr['street']}

    for b in blds:
        pl, k = b['pl'], b['kind']
        ent = []
        frs = frontages(pl)                                                # only straight axis-aligned walls count
        if k in ('pavilion',):
            c = pcen(pl)
            best = None
            for i in range(4):
                a, q = pl[i], pl[(i + 1) % 4]
                u, n, L = outward(pl, a, q)
                if n[0] * (model['axis'] - c[0]) > 0 and abs(n[0]) > 0.99:
                    best = (a, q, n)
            a, q, n = best
            m_ = ((a[0] + q[0]) / 2, (a[1] + q[1]) / 2)
            ent.append({'pos': rnd2(W(m_)), 'facing_deg': facing(n), 'kind': 'door', 'w_m': 2.0, 'benches': 0, 'role': 'glass double door to the terrace'})
        elif k == 'podium':
            x0, y0, x1, y1 = bb(pl)
            for t in [tw for tw in blds if tw['kind'] == 'tower']:
                ent.append({'pos': rnd2(W((pcen(t['pl'])[0], y1))), 'facing_deg': 270.0, 'kind': 'door', 'w_m': 4.0, 'benches': 0,
                            'role': 'tower lobby, top of the tribune stair (plaza side)'})
            ent.append({'pos': rnd2(W(((x0 + x1) / 2, y0))), 'facing_deg': 90.0, 'kind': 'door', 'w_m': 3.0, 'benches': 0, 'role': 'north lobby (N2 / Nj)'})
        elif k in ('tower', 'tower_round'):
            pass                                                           # entered through the podium
        elif k == 'podium_round':
            fr = frs[0]
            ent.append(door_at(fr, 0.5, 'door', 3.0, 'lobby of the round corner tower', b['id']))
        elif k == 'gas_shop':
            x0, y0, x1, y1 = bb(pl)
            ent.append({'pos': rnd2(W(((x0 + x1) / 2, y0))), 'facing_deg': 90.0, 'kind': 'door', 'w_m': 1.8, 'benches': 0, 'role': 'shop door to the forecourt / canopy'})
        elif frs:
            main = frs[0]
            if k == 'classical':
                main = next((f for f in frs if f['street'] == 'S1'), main)
            if k == 'arch_house':                                          # the door stays out of the drive-through arch
                ar = bb(arch_el)
                lo_, hi_ = main['range']
                parts = [(lo_, min(hi_, ar[1 - main['ax']] - 2)), (max(lo_, ar[3 - main['ax']] + 2), hi_)]
                main = dict(main, range=max(parts, key=lambda q_: q_[1] - q_[0]))
            w = {'police': 2.0, 'classical': 3.0, 'glass_office': 3.0, 'diner': 1.6, 'gas_shop': 1.8, 'taxi_depot': 1.6, 'podium_annex': 2.0}.get(k, 1.2)
            f = 0.5 if main['L'] < 50 else 0.25 + 0.5 * h01(b['id'] + 'door')
            role = 'main' if k not in ('house', 'arch_house', 'loft') else ('main / shop' if gf_of.get(b['id']) in ('storefront', 'cafe_terrace', 'rollshutter_shop') else 'main')
            if k == 'alley_plug':                                          # end house of a single blind alley faces a street
                ent.append(door_at(main, 0.5, 'door', 1.2, 'main (street side; blind wall to the alley)', b['id']))
            elif k != 'base_garage':
                ent.append(door_at(main, f, 'door', w, role, b['id']))
            if corner(b) or k in ('police', 'diner'):
                other = next((f2 for f2 in frs[1:] if f2['ax'] != main['ax']), None)
                if other:                                                  # second door on the side street, next to the shared corner
                    cc = main['a'][main['ax']]
                    lo_, hi_ = other['range']
                    ent.append(door_at(other, 0.0 if abs(lo_ - cc) < abs(hi_ - cc) else 1.0, 'door', 1.6,
                                       'corner shop door' if k == 'house' else 'side door', b['id']))
        for r_ in shutters:                                                # roll shutters drawn on the plan
            c = ((r_[0] + r_[2]) / 2, (r_[1] + r_[3]) / 2)
            if not pin(c, b['pl0']) and min(abs(c[0] - q_[0]) + abs(c[1] - q_[1]) for q_ in b['pl0']) > 40:
                continue
            for i in range(len(pl)):
                a, q = pl[i], pl[(i + 1) % len(pl)]
                u, n, L = outward(pl, a, q)
                if L < 3 or (abs(n[0]) < 0.99 and abs(n[1]) < 0.99):
                    continue
                ax = 0 if abs(n[0]) > 0.99 else 1
                if (abs(c[ax] - a[ax]) < 6 or (abs(c[ax] - a[ax]) < 20 and (c[ax] - a[ax]) * n[ax] > 0)) and                         min(a[1 - ax], q[1 - ax]) - 1 <= c[1 - ax] <= max(a[1 - ax], q[1 - ax]) + 1:
                    p = [0, 0]
                    p[ax], p[1 - ax] = a[ax], c[1 - ax]
                    w = max(r_[2] - r_[0], r_[3] - r_[1]) * U
                    ent.append({'pos': rnd2(W(p)), 'facing_deg': facing(n), 'kind': 'rollshutter', 'w_m': round(max(4.0, w), 1), 'benches': 0,
                                'role': 'garage roll shutter (plan)', 'clear_h_m': 4.0})
                    break
        if k in ('house', 'arch_house', 'loft'):                           # back doors into dead-end alleys (v02 §8.5)
            for i in range(len(pl)):
                a, q = pl[i], pl[(i + 1) % len(pl)]
                u, n, L = outward(pl, a, q)
                for ar in alley_rects:
                    for ax in (0, 1):
                        if abs(n[ax]) < 0.99:
                            continue
                        side = ar[ax] if n[ax] > 0 else ar[ax + 2]
                        if abs(a[ax] - side) > 0.6:
                            continue
                        lo_, hi_ = max(min(a[1 - ax], q[1 - ax]), ar[1 - ax]), min(max(a[1 - ax], q[1 - ax]), ar[3 - ax])
                        if hi_ - lo_ < 8:
                            continue
                        p = [0, 0]
                        p[ax], p[1 - ax] = a[ax], lo_ + (hi_ - lo_) * (0.3 + 0.4 * h01(b['id'] + 'bd'))
                        ent.append({'pos': rnd2(W(p)), 'facing_deg': facing(n), 'kind': 'door', 'w_m': 1.0, 'benches': 0, 'role': 'back door (alley)'})
        b['entrances'] = ent
        b['frontages'] = [f['street'] for f in frs]

    # ------------------------------------------------ sockets from the plan (fire escapes, water tanks)
    for e in sel(els, g='buildings', tag='polygon', fill='#3D4246'):
        p0, p1, p2 = e['pts'][0], e['pts'][1], e['pts'][2]
        o = ((p2[0] - p1[0]) / 3.6, (p2[1] - p1[1]) / 3.6)
        ax = 0 if abs(o[0]) > 0.5 else 1
        best = None
        for b in blds:
            r_ = bb(b['pl'])
            face = r_[ax + 2] if o[ax] > 0 else r_[ax]
            mid = (p0[1 - ax] + p1[1 - ax]) / 2
            if r_[1 - ax] - 1 <= mid <= r_[3 - ax] + 1:
                d = abs(face - p0[ax])
                if best is None or d < best[0]:
                    best = (d, b, face)
        if best and best[0] < 20:
            d, b, face = best
            q0, q1 = list(p0), list(p1)
            q0[ax] = q1[ax] = face
            b.setdefault('fire', []).append({'from': rnd2(W(q0)), 'to': rnd2(W(q1)), 'out_deg': facing(o), 'depth_m': 1.2, 'src': 'plan'})
    for e in sel(els, g='buildings', tag='circle', fill='#8B6B4A'):
        cands = [b for b in blds if pin(e['c'], b['pl'])] or sorted(blds, key=lambda b: math.hypot(pcen(b['pl'])[0] - e['c'][0], pcen(b['pl'])[1] - e['c'][1]))[:1]
        cands[0].setdefault('tanks', []).append(rnd2(W(e['c'])))
    for b in blds:                                                         # alley walls get fire escapes too (legend: "пожарные лестницы")
        if b['kind'] not in ('house', 'arch_house') or h01(b['id'] + 'fe') > 0.5:
            continue
        for d in b['entrances']:
            if d['role'] == 'back door (alley)':
                b.setdefault('fire', []).append({'at': d['pos'], 'out_deg': d['facing_deg'], 'depth_m': 1.2, 'src': 'rule: alley wall'})
                break

    # ------------------------------------------------ building records
    out_b = []
    for b in blds:
        k, h, bid = b['kind'], b['h'], b['id']
        tint = calm_bright(b['col'], bid)
        roof = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': PARAPET}
        notes, slot, walls, kit = [], 'downtown_house_stucco', 'facade_downtown_stucco', 'downtown'
        fl, fh, height = None, FLOOR_H, None
        if k == 'tower':
            fl, fh, height = 55, 3.6, 200.0
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            roof = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 1.2, 'crown': 'light canopy ring'}
            notes.append('round faceted dark-blue glass (v02 §8.5), identical twins, glass belt at podium level; Ø from the plan')
        elif k == 'podium':
            fl, fh, height = 1, 6.0, 6.0
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            notes.append('common glass podium of the twins; the tribune stair (5 steps) climbs 2.25 m from the plaza to its lobby terrace; screen 35 on its south face')
        elif k == 'tower_round':
            fl, fh = 24, 3.6
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            notes.append('round glass corner tower (legend §6); height not given -> 24 floors from the plan shadow 46 vs 70 of the twins (question)')
        elif k == 'podium_round':
            fl, fh = 2, 4.0
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            notes.append('glass podium of the round corner tower')
        elif k == 'glass_office':
            fl, fh = 10, 3.6
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            notes.append('glass office; floors not given -> 10 (plan shadow 30 vs 18-22 of corner houses) (question)')
        elif k == 'pavilion':
            fl, fh = 1, 4.5
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            roof = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.3}
            notes.append('glass pavilion, shop windows all round, terrace with 3 yellow umbrellas (props)')
        elif k == 'classical':
            fl, fh = 3, 4.6
            slot, walls, tint = 'downtown_classical', 'stucco_SK3b', '#D9D2C2'
            roof = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 1.2, 'skylight': 'round, centre'}
            notes.append('stone building (bank / library) with a colonnade along the promenade front (S1), round skylight')
        elif k == 'loft':
            fl, fh = 4, 4.2
            slot, walls = 'downtown_house_brick', 'facade_downtown_brick'
            roof = {'type': 'sawtooth', 'material': 'roof_profsheet_SK4c', 'parapet_h_m': 0.8, 'ridge_axis_deg': 90.0}
            notes.append('brick loft (old warehouse) with saw-tooth roof lights (legend §6)')
        elif k == 'police':
            fl, fh = 4, 3.6
            notes.append('police station (%s); light blue-grey civic stucco' % ('SW, rotunda on the corner' if b['label'] == '10' else 'NE, rounded corner'))
        elif k == 'police_rotunda':
            fl, fh = 2, 4.5
            roof = {'type': 'dome', 'material': 'metal_painted_SK6a', 'parapet_h_m': 0.6}
            notes.append('rotunda of police 1 on the W2 / S1 corner')
        elif k == 'taxi_depot':
            fl, fh = 2, 4.0
            notes.append('taxi depot office + garage, built onto police 2; own stand (zone 05-12-stand)')
        elif k == 'van_shop':
            fl, fh = 2, 4.5
            slot, walls = 'downtown_storefront', 'facade_storefront'
            notes.append('van shop 07: roll-shutter gates straight onto the boulevard (v10 §7.5 "магазин для бусика с воротами на улицу")')
        elif k == 'diner':
            fl, fh = 1, 4.5
            slot, walls, tint = 'downtown_storefront', 'facade_storefront', '#D7DDE1'
            roof = {'type': 'flat', 'material': 'metal_painted_SK6a', 'parapet_h_m': 0.4}
            notes.append('chrome corner diner with a red stripe, rounded corners (plan)')
        elif k == 'gas_shop':
            fl, fh = 1, 4.0
            slot, walls = 'downtown_storefront', 'facade_storefront'
            notes.append('gas-station shop (41), faces the canopy')
        elif k == 'podium_annex':
            fl, fh = 2, 3.5
            notes.append('low service / parking lobby building on N2 between ramp 1 and Nj (plan h = 6)')
        elif k == 'base_garage':
            fl, fh = 1, 5.5
            slot, walls = 'downtown_house_brick', 'facade_downtown_brick'
            notes.append('BASE 4 brick garage; roll shutter with canopy in its east end, faces the courtyard (legend §4)')
        elif k == 'alley_plug':
            fl, fh = 3, FLOOR_H
            slot, walls = 'downtown_house_brick', 'facade_downtown_brick'
            notes.append('dead-end plug: blind brick walls to the alley(s) (v02 §8.5 "NPC забегает — а там стена")')
        else:
            fl = b['floors']
            slot = slot_of.get(bid, 'downtown_house_stucco')
            walls = {'downtown_house_brick': 'facade_downtown_brick', 'downtown_house_stucco': 'facade_downtown_stucco',
                     'downtown_storefront': 'facade_storefront'}[slot]
            if corner(b):
                notes.append('corner house (plan class h %d) -> higher' % h)
            if k == 'arch_house':
                notes.append('house over the BASE 4 drive-through arch (from Hse2)')
            if bb(b['pl'])[1] < 150 and blk_of(model, pcen(b['pl'])) in ('OB1', 'NEX'):
                notes.append('stopper house outside the ring bend (legend §6: the street runs into a house)')
            if not b['entrances']:
                notes.append('inner house without a street frontage (between office 05 and the stone building): entered through its neighbours')
        if height is None:
            if k in ('house', 'arch_house'):
                height = GROUND_H + (fl - 1) * FLOOR_H
                fh = FLOOR_H
            else:
                height = fl * fh
        fp = ccw(WL(b['pl']))
        gf = gf_of.get(bid)
        rec = {'id': bid, 'kind': k, 'material_slot': slot, 'footprint': fp, 'floors': fl, 'floor_h_m': fh, 'height_m': round(height, 1),
               'roof': roof, 'walls': walls, 'tint': tint, 'entrances': b['entrances'], 'arches': [], 'facade_kit': kit,
               'sockets': {'balconies': 'none', 'windows': kit != 'none' or k == 'pavilion', 'fire_escape': b.get('fire', False),
                           'ac_units': 0 if kit == 'none' else int(h01(bid + 'ac') * 4), 'water_tank': b.get('tanks', False),
                           'awning': {'tint': aw_of[bid], 'pattern': 'striped' if h01(bid + 'st') < 0.2 else 'plain'} if bid in aw_of else False,
                           'storefront': gf in ('storefront', 'cafe_terrace', 'rollshutter_shop') or k in ('van_shop', 'diner', 'gas_shop', 'pavilion'),
                           'ridge_cap': None, 'antenna': kit != 'none' and h01(bid + 'ant') < 0.3, 'signs': 'no text (v02 §11)'},
               'collider': 'full_roof', 'disabled': False, 'src_colour': b['fill'], 'plan_h': h, 'frontages': b['frontages'], 'notes': '; '.join(notes)}
        if b['label']:
            rec['legend'] = b['label']
        if gf:
            rec['ground_floor'] = {'kind': gf, 'h_m': GROUND_H, 'material_slot': 'downtown_storefront' if gf in ('storefront', 'cafe_terrace', 'rollshutter_shop') else slot,
                                   'cafe_tables': gf == 'cafe_terrace'}
        if k == 'house' and h >= 18:
            rec['corner'] = True
        if k == 'arch_house':
            ar = bb(arch_el)
            rec['arches'].append({'id': '13-A1', 'rect': ccw(WL(R(*ar))), 'through': 'N-S', 'clear_w_m': round((ar[2] - ar[0]) * U, 2),
                                  'clear_h_m': 4.5, 'notes': 'drive-through arch from Hse2 into the BASE 4 courtyard (v10 §4: >= 4 m)'})
        out_b.append(rec)

    # ------------------------------------------------ zones
    zones, props = [], []
    jun = junctions(st)
    ring = set(model['ring'])
    for name, s in st.items():
        z = {'id': '05-street-' + name, 'kind': 'street', 'poly_line': WL(s['pts']), 'carriageway_m': CARR, 'sidewalk_m': WALK, 'curb_m': CURB,
             'corner_radius_m': CORNER_R, 'surface': 'asphalt_A5d12', 'sidewalk_surface': 'sidewalk_S1', 'lanes': 2,
             'markings': 'white dashed centre line', 'boulevard': name == 'B', 'ring': name in ring, 'cap': s['cap'],
             'length_m': round(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(s['pts'][:-1], s['pts'][1:])) * U, 1)}
        if name == 'B':
            z['notes'] = 'boulevard = same 2-lane street, no median (v02 §8.5); bends round the plaza; zebras across it only at Vb / AX / Vc'
        if name == 'S1':
            z['notes'] = ('one straight promenade street along the beach (v27, approved); its south sidewalk borders the promenade of district 09 '
                          '(the v85 picture cut the plan at plan y 1252, 2.6 m inside this sidewalk)')
        if 'beyond_S1_plan' in s:
            z['notes'] = 'ends at S1; the plan continuation to the beach is the south entry (zone 05-entry-S-%s)' % name
        zones.append(z)
    for jj, (p, names) in enumerate(sorted(jun, key=lambda t: (t[0][1], t[0][0]))):
        lg = [(n, v, L) for n in sorted(names) for v, L in legs(st, n, p)]
        typ = {2: 'bend', 3: 'T', 4: 'X'}.get(len(lg), 'multi')
        main = 'B' in names or 'AX' in names
        control = 'none' if len(lg) < 3 else ('traffic_light' if main else 'stop')
        cross = []
        if 'B' in names:                                                   # legend v26 §1 / v02 §8.5: zebras only at the boulevard
            plaza = bool({'AX', 'Vb', 'Vc'} & names)
            for n, v, L in lg:
                probe = (p[0] + v[0] * 60, p[1] + v[1] * 60)
                if (not pin(probe, model['district']) and n != 'AX') or (n == 'B' and not plaza) or L < 55:
                    continue
                q = (p[0] + v[0] * (CW + 12.5), p[1] + v[1] * (CW + 12.5))
                leg = round(math.degrees(math.atan2(-v[1], v[0])) % 360, 1)
                cross.append({'street': n, 'centre': rnd2(W(q)), 'leg_deg': leg, 'walk_deg': round((leg + 90) % 180, 1), 'w_m': 4.0,
                              'span_m': CARR, 'notes': 'zebra across the %s carriageway, 8.5 m from the junction centre' % n})
        zones.append({'id': '05-junction-%02d' % jj, 'kind': 'junction', 'pos': rnd2(W(p)), 'streets': sorted(names), 'type': typ,
                      'legs_deg': [round(math.degrees(math.atan2(-v[1], v[0])) % 360, 1) for n, v, L in lg], 'control': control,
                      'crosswalks': cross, 'corner_radius_m': CORNER_R})

    # entries (v10 §6): world roads from the master SVG
    master_roads, stubs = [], []
    for nm, at, M, ids, s0, s1 in svg_tags(svg_text()):
        if nm == 'polygon' and ids and ids[-1] == 'L06b_entry' and attr(at, 'fill') == '#5F666C':
            stubs.append([Winv(pic_of_pre(u2m(*q))) for q in points_of(at, M)])
        if nm == 'polyline' and ids and ids[-1] in ('R24_roads', 'R74_elite_ring', 'R84_downtown_entries') and attr(at, 'stroke') in ('#5F666C', '#B3A68D'):
            master_roads.append((ids[-1], attr(at, 'stroke-width'), [pic_of_pre(u2m(*q)) for q in points_of(at, M)]))

    def world_end(target, groups=('R24_roads', 'R74_elite_ring')):
        best = None
        for g, w, pl in master_roads:
            if g not in groups:
                continue
            for e_ in (pl[0], pl[-1]):
                d = math.hypot(e_[0] - target[0], e_[1] - target[1])
                if best is None or d < best[0]:
                    best = (d, e_, pl, g, w)
        return best

    ent_specs = [
        ('W', 'B', (model['st']['B']['pts'][0]), (-1, 0), 'R24 road from the west (Hamlet -> Construction -> Downtown straight, rural asphalt 6.4 m; '
         'R84_downtown_entries widens it to 9.6 m at the corner)'),
        ('E', 'B', (model['st']['B']['pts'][-1]), (1, 0), 'R74 Elite stone road 4.5 m (half-ring up the hill, gates on the east side)'),
        ('N-tunnel', 'Vn', (445.0, 70.0), (0, -1), 'R24 road from the tunnel under hill B (Rough), portal ~60 m north'),
        ('N-viewB', 'N3', None, (0, -1), 'R24 serpentine up to VIEW B (+46 m)'),
        ('NE-viewC', 'E1', (2240.0, 330.0), (0, -1), 'R24 cornice road VIEW C over the bay -> Port (not in the brief list; drawn on v85)'),
        ('S-Va2', 'Va2', (620.0, 1210.0), (0, 1), 'beach district 09: van entry onto the sand (beach plan v06), parking next to it'),
        ('S-Vds', 'Vds', (1840.0, 1210.0), (0, 1), 'beach district 09: van entry onto the sand (beach plan v06), parking next to it')]
    vb_end = world_end(W((1480.0, 150.0)))                                 # the serpentine lands on N3 between OB1 and NEX
    entries = []
    for key, street, ax_p, d, desc in ent_specs:
        if ax_p is None:
            gx = Winv(vb_end[1])[0]
            ax_p = (round(gx, 1), 150.0)
        pos = (ax_p[0] + d[0] * HW, ax_p[1] + d[1] * HW)
        curb_drop = R(min(ax_p[0] + d[0] * CW, pos[0]) if d[0] else ax_p[0] - CW, min(ax_p[1] + d[1] * CW, pos[1]) if d[1] else ax_p[1] - CW,
                      max(ax_p[0] + d[0] * CW, pos[0]) if d[0] else ax_p[0] + CW, max(ax_p[1] + d[1] * CW, pos[1]) if d[1] else ax_p[1] + CW)
        z = {'id': '05-entry-' + key, 'kind': 'entry', 'pos': rnd2(W(pos)), 'axis_point': rnd2(W(ax_p)), 'street': street,
             'heading_deg': round(math.degrees(math.atan2(-d[1], d[0])) % 360, 1), 'carriageway_m': CARR, 'world_road': desc,
             'curb_drop': ccw(WL(curb_drop)), 'join_rule': 'world road continues as carriageway up to this street; straight approach for the last 15-20 m; '
                                                        'lowered curb across the sidewalk (v10 §6)'}
        if not key.startswith('S-'):
            we = world_end(W(ax_p))
            if we and we[0] < 40:
                e_ = we[1]
                q = Winv(e_)
                lat = (q[0] - ax_p[0]) * U if d[0] == 0 else (q[1] - ax_p[1]) * U
                z['world_road_end'] = rnd2(e_)
                z['world_road_src'] = we[3]
                z['world_road_lateral_offset_m'] = round(lat * (1 if d[0] == 0 else -1), 2)
        entries.append(z)
    zones += entries
    for pl in stubs:                                                       # old asphalt patches of the world picture on Downtown sidewalks
        c = pcen(pl)
        if -60 < c[0] < 2400 and 0 < c[1] < 1270:
            on = [bd['street'] for bd in bands if min(overlap(bb(pl), bd['rect'])) > 0]
            fix(rnd2(c), 'Обрывок асфальта %.0f × %.0f м на тротуаре %s (картинка v85, слой L06b_entry — старый въезд) не строится: тротуар сплошной, '
                         'серпантин VIEW B входит в N3 в точке entry N-viewB.' % ((bb(pl)[2] - bb(pl)[0]) * U, (bb(pl)[3] - bb(pl)[1]) * U, '/'.join(on) or '?'),
                'v10 §6 / §11: обрывков дорог нет, каждая дорога куда-то ведёт.')

    # curb drops (driveways) of the plan + rule-based ones
    def drop_zone(zid, r_, why):
        c = ((r_[0] + r_[2]) / 2, (r_[1] + r_[3]) / 2)
        best = None
        for bd in bands:                                                   # the street whose sidewalk the drive crosses
            ax = bd['ax']
            lo_, hi_ = sorted((bd['seg'][0][1 - ax], bd['seg'][1][1 - ax]))
            d_ = abs(c[ax] - bd['axis'])
            out_ = max(0.0, lo_ - c[1 - ax], c[1 - ax] - hi_)               # beyond the segment end (inside the junction)
            if out_ <= HW and d_ <= HW + 4 and (best is None or (out_, d_) < best[0]):
                best = ((out_, d_), bd)
        assert best, ('curb drop without a street', zid)
        bd = best[1]
        ax = bd['ax']
        side = 1 if c[ax] > bd['axis'] else -1
        q = list(r_)
        q[ax], q[ax + 2] = sorted((bd['axis'] + side * CW, bd['axis'] + side * HW))   # across the sidewalk: curb -> facade line
        r_ = tuple(q)
        zones.append({'id': zid, 'kind': 'curb_drop', 'poly': ccw(WL(R(*r_))), 'for': why, 'street': bd['street'], 'surface': 'asphalt_old_SK2a',
                      'curb_m': 0.0, 'w_m': round((r_[3 - ax] - r_[1 - ax]) * U, 1), 'depth_m': WALK})

    labelled = {'42': '05-42', '43': '05-43', '13': '05-13'}
    for i, d in enumerate(dws):
        r_ = bb(d)
        c = pcen(d)
        why = 'drive'
        for a in alley_out:
            if abs(c[a['cax']] - a['c']) < 1 and blk_of(model, c, 30.0) == a['block']:
                why = 'alley %s mouth' % a['block']
        if why == 'drive':
            near = min(labels.items(), key=lambda kv: math.hypot(kv[1][0] - c[0], kv[1][1] - c[1]))[0]
            why = {'42': 'service yard 42 entry', '43': 'service yard 43 entry', '13': 'BASE 4 arch entry from Hse2', '07': 'van shop 07 gates'}.get(near, 'drive')
            if near == '13':                                               # the drop matches the arch opening
                ar = bb(arch_el)
                r_ = (ar[0], r_[1], ar[2], r_[3])
        drop_zone('05-drop-%02d' % i, r_, why)
    for e in sel(els, g='buildings', tag='polygon', fill='#6E757A'):                    # parking ramps
        r_ = bb(e['pts'])
        top = r_[1]
        bd = min((bd for bd in bands if bd['ax'] == 1 and bd['rect'][0] <= (r_[0] + r_[2]) / 2 <= bd['rect'][2]), key=lambda bd: abs(bd['rect'][3] - top))
        drop_zone('05-drop-ramp-%s' % bd['street'], (r_[0], bd['axis'] + CW, r_[2], bd['rect'][3]), 'parking 03 ramp from %s' % bd['street'])
    canopy = bb(sel(els, g='buildings', tag='polygon', fill='#E8E2D2')[0]['pts'])
    gl = bb(gas_lot)
    bdB = next(bd for bd in bands if bd['street'] == 'B' and bd['ax'] == 1 and bd['rect'][0] <= gl[0] <= bd['rect'][2])
    for j_, x in enumerate((canopy[0] + 5, canopy[2] - 45)):
        drop_zone('05-drop-41-%d' % j_, (x, bdB['axis'] + CW, x + 40, bdB['rect'][3]), 'gas station 41 %s (from B)' % ('in' if j_ == 0 else 'out'))
    taxi_lot = sel(els, g='squares_and_lots', fill='#C3C9CD')[0]['pts']
    tl = bb(taxi_lot)
    bdVd = next(bd for bd in bands if bd['street'] == 'Vd' and bd['rect'][1] <= (tl[1] + tl[3]) / 2 <= bd['rect'][3])
    yc = (tl[1] + tl[3]) / 2
    drop_zone('05-drop-12', (bdVd['axis'] + CW, yc - 20, tl[0], yc + 20), 'taxi stand 12 exit onto Vd')

    # plaza "Water Axis" (04) and parking 03
    plaza_drawn = sel(els, g='squares_and_lots', tag='polygon', fill='#D9D2C4')[0]['pts']
    plaza = model['blocks']['SQ']['poly']
    gap = (bb(plaza_drawn)[0] - bb(plaza)[0]) * U
    if gap > 0.3:
        fix(rnd2(pcen(plaza)), 'Площадь 04: плитка доведена до тротуаров (на плане между плиткой и тротуаром полоса «двора» %.1f м по всему краю).' % gap,
            'Генератор v28 ужал контур площади дважды (уже ужатый квартал SQ ещё раз через MPP) — это артефакт рисования, а не задумка.')
    zones.append({'id': '05-04-plaza', 'kind': 'plaza', 'poly': ccw(WL(plaza)), 'surface': 'plaza_M3', 'label': '04',
                  'notes': '1 x 1 m slabs of one warm grey-beige tone, joints barely visible, NO pattern; dark stone band 0.5 m only along the edge, '
                           'round the pool and the monument podium; pedestrian, no trees (v02 §8.5); van can drive on it (curb ramps at the boulevard)'})
    stairs = [e['pts'] for e in sel(els, g='squares_and_lots', tag='polyline', stroke='#CFC6B4')]
    sx0, sx1 = min(p[0] for s in stairs for p in s), max(p[0] for s in stairs for p in s)
    sy0, sy1 = min(p[1] for s in stairs for p in s), max(p[1] for s in stairs for p in s)
    podium = next(b for b in blds if b['kind'] == 'podium')
    py1 = bb(podium['pl'])[3]
    zones.append({'id': '05-04-stair', 'kind': 'stair', 'poly': ccw(WL(R(sx0, py1, sx1, sy1 + 1.0))), 'steps': 5, 'step_h_m': 0.45,
                  'rise_m': 2.25, 'surface': 'plaza_M3', 'climb_dir_deg': 90.0,
                  'notes': 'tribune steps, NPC sit on them; climbs from the plaza (south) to the podium lobby terrace; not drivable (v10 §4)'})
    wat = sorted(sel(els, g='squares_and_lots', tag='polygon', fill='#7FB3D0'), key=lambda e: parea(e['pts']))
    zones.append({'id': '05-04-cascade', 'kind': 'water_cascade', 'poly': ccw(WL(wat[0]['pts'])), 'notes': 'water steps down the middle of the stair into the pool'})
    band_ = sel(els, g='squares_and_lots', tag='polygon', fill='#8A8378')[0]['pts']
    zones.append({'id': '05-04-pool', 'kind': 'pool', 'poly': ccw(WL(wat[1]['pts'])), 'edge_poly': ccw(WL(band_)), 'depth_m': 0.3, 'edge_m': 1.2,
                  'surface': 'pool_tile', 'notes': 'mirror pool 16 x 60 m, ~30 cm: the van drives in with splashes and brakes (v02 §8.5)'})
    mon = sel(els, g='squares_and_lots', tag='circle', fill='#8A8378')[0]
    jets = sel(els, g='buildings', tag='circle', fill='#DDEFF5')
    jr = sum(math.hypot(e['c'][0] - mon['c'][0], e['c'][1] - mon['c'][1]) for e in jets) / len(jets)
    pod = sel(els, g='buildings', tag='circle', r=22.0)[0]
    zones.append({'id': '05-15-monument-ring', 'kind': 'dry_fountains', 'centre': rnd2(W(mon['c'])), 'podium_d_m': round(2 * pod['r'] * U, 2),
                  'jets_r_m': round(jr * U, 2), 'jets': len(jets), 'edge_r_m': round(mon['r'] * U, 2),
                  'notes': 'jets come out of the paving, people walk and the van drives over them; dark stone band at R edge'})
    pk = sel(els, g='buildings', tag='polygon', fill='none', stroke='#2F3A42')[0]['pts']
    ramps = [e['pts'] for e in sel(els, g='buildings', tag='polygon', fill='#6E757A')]
    zones.append({'id': '05-03-parking', 'kind': 'underground_parking', 'poly': ccw(WL(pk)), 'levels': 1, 'deck_m': -4.5, 'clear_h_m': 3.0,
                  'ramps': [ccw(WL(r_)) for r_ in ramps], 'ramp_slope_max': 0.15, 'surface': 'concrete_SK3c', 'label': '03',
                  'notes': 'one level under the podium and both towers: aisles, marked bays both sides, columns, dim light, a few cars; two identical two-way ramps; '
                           'the van drives in and turns inside. The drawn ramp mouths are 11-16 m long: the descent continues under the podium (~30 m in total) to keep <= 15 %'})
    fix(rnd2(pcen(ramps[1])), 'Рампы паркинга 03: на плане открытая часть 11–16 м — спуск продолжен под подиумом (~30 м всего, уклон ≤ 15 %).',
        'На глубину одного уровня (~4,5 м) 11–16 м дают уклон 30–40 % — бусик не заедет; вход рампы оставлен где нарисован.')
    scr = bb(sel(els, g='buildings', tag='polygon', fill='#1E2A36')[0]['pts'])
    props.append({'id': '05-35-screen', 'kind': 'big_screen', 'pos': rnd2(W(((scr[0] + scr[2]) / 2, (scr[1] + scr[3]) / 2))), 'rot_deg': 270.0,
                  'size': [round((scr[2] - scr[0]) * U, 1), 0.6, 8.0], 'grip_anchor': False, 'label': '35', 'notes': 'faces south onto the plaza, on the podium'})
    # monument, booth, ATM, benches, flags, lamps, food trucks, umbrellas, bollards, bus stop
    statue = sel(els, g='buildings', tag='circle', fill='#D9B13B')[0]
    props.append({'id': '05-15-monument', 'kind': 'monument_tramduro', 'pos': rnd2(W(statue['c'])), 'rot_deg': 270.0, 'size': [4.8, 4.8, 12.0],
                  'grip_anchor': False, 'label': '15', 'notes': 'golden cartoon figure with a raised arm on a granite podium D 8.8 m (3 steps); faces the boulevard'})
    for fill_, kid, kind, size, lab in (('#5B6E8C', '05-36-booth', 'police_booth', [3.2, 3.2, 3.0], '36'), ('#2F5D8A', '05-08-atm', 'atm', [1.0, 1.0, 2.0], '08')):
        e = sel(els, g='buildings', tag='polygon', fill=fill_)[0]
        props.append({'id': kid, 'kind': kind, 'pos': rnd2(W(pcen(e['pts']))), 'rot_deg': 0.0, 'size': size, 'grip_anchor': False, 'label': lab})
    for i, e in enumerate(sel(els, g='buildings', tag='circle', fill='#B07A4A')):
        props.append({'id': '05-04-bench%d' % (i + 1), 'kind': 'round_bench_flowerbed', 'pos': rnd2(W(e['c'])), 'rot_deg': 0.0,
                      'size': [round(2 * e['r'] * U, 1), round(2 * e['r'] * U, 1), 0.5], 'grip_anchor': True, 'notes': 'wooden round bench, flowerbed inside, no tree'})
    for i, e in enumerate(sel(els, g='buildings', tag='circle', fill='#2F3A42')):
        props.append({'id': '05-04-flag%d' % (i + 1), 'kind': 'flagpole', 'pos': rnd2(W(e['c'])), 'rot_deg': 0.0, 'size': [0.3, 0.3, 12.0], 'grip_anchor': True,
                      'notes': 'flag without text or logo'})
    for i, e in enumerate(sel(els, g='objects', tag='circle', fill='#FFFDF4')):
        props.append({'id': '05-04-lamp%d' % (i + 1), 'kind': 'lamp_tall', 'pos': rnd2(W(e['c'])), 'rot_deg': 0.0, 'size': [0.4, 0.4, 9.0], 'grip_anchor': True})
    for i, e in enumerate(sel(els, g='buildings', tag='polygon', fill='#C8503F')):
        r_ = bb(e['pts'])
        props.append({'id': '05-04-foodtruck%d' % (i + 1), 'kind': 'food_truck', 'pos': rnd2(W(pcen(e['pts']))), 'rot_deg': 0.0,
                      'size': [round((r_[2] - r_[0]) * U, 1), round((r_[3] - r_[1]) * U, 1), 3.0], 'grip_anchor': False})
    for i, e in enumerate(sel(els, g='buildings', tag='circle', fill='#E9D37A')):
        props.append({'id': '05-pav-umbrella%d' % (i + 1), 'kind': 'umbrella_yellow', 'pos': rnd2(W(e['c'])), 'rot_deg': 0.0, 'size': [2.8, 2.8, 2.6],
                      'grip_anchor': False, 'notes': 'pavilion terrace: table + chairs under it'})
    bol = sorted((e['c'] for e in sel(els, g='buildings', tag='circle', fill='#3C3E42', r=2.2)), key=lambda c: c[0])
    zones.append({'id': '05-04-bollards-B', 'kind': 'bollard_row', 'line': WL([bol[0], bol[-1]]), 'count': len(bol),
                  'spacing_m': round((bol[-1][0] - bol[0][0]) / (len(bol) - 1) * U, 2), 'grip_anchor': True,
                  'notes': 'dark bollards along the plaza edge on the boulevard (legend §3); gaps for the van ramps at the zebras'})
    bs = sel(els, g='buildings', tag='polygon', fill='#9AA7B0')[0]['pts']
    bsr = bb(bs)
    bdB2 = next(bd for bd in bands if bd['street'] == 'B' and bd['ax'] == 1 and bd['rect'][0] <= pcen(bs)[0] <= bd['rect'][2] and bd['rect'][1] <= pcen(bs)[1] <= bd['rect'][3])
    new_y = bdB2['axis'] - CW - 15.0
    props.append({'id': '05-14-bus-stop', 'kind': 'bus_stop_shelter', 'pos': rnd2(W((pcen(bs)[0], new_y))), 'rot_deg': 0.0,
                  'size': [round((bsr[2] - bsr[0]) * U, 1), 1.6, 2.6], 'grip_anchor': True, 'label': '14', 'notes': 'shelter + bench + bus-stop sign; bus waits at the curb'})
    fix(rnd2(pcen(bs)), 'Остановка 14: на плане навес стоит на краю проезжей части бульвара — перенесён на северный тротуар (3 м от бордюра).',
        'После расширения улиц (v28) рисунок остановки остался на старом месте и попал на полосу движения.')

    # base 13, service yards 42 / 43
    yards = sel(els, g='squares_and_lots', tag='polygon', fill='#D8D4CA')
    bins = sel(els, g='buildings', tag='polygon', fill='#4E6B52')
    ybol = sel(els, g='buildings', tag='circle', fill='#E3B71E')
    for e in yards:
        lab = next((k for k, p in labels.items() if pin(p, e['pts']) and k in ('42', '43', '13')), None)
        if lab is None:
            lab = min(('42', '43', '13'), key=lambda k: math.hypot(labels[k][0] - pcen(e['pts'])[0], labels[k][1] - pcen(e['pts'])[1]))
        yb = bb(e['pts'])
        if lab == '13':
            court = clip_axis(e['pts'], 1, bb(arch_el)[3], False)
            cb = bb(court)
            zones.append({'id': '05-13-yard', 'kind': 'yard', 'poly': ccw(WL(e['pts'])), 'court_poly': ccw(WL(court)), 'surface': 'concrete_SK3c', 'label': '13',
                          'size_m': [round((cb[2] - cb[0]) * U, 1), round((cb[3] - cb[1]) * U, 1)], 'closed': True, 'visible_from_street': False,
                          'loading_pad': True, 'notes': 'BASE 4 courtyard: closed on all sides (arch house N, garage W, house E, blind brick wall S), '
                                                        'van stops at the roll shutter; bins (green, blue), pallets, yellow bollards, tulip boxes, a bench, '
                                                        'AC units, fuse boxes, pipes, lamps over doors, neighbour fire escape (legend §4)'})
            wall = sel(els, g='buildings', tag='polyline', stroke='#8A4A36')[0]['pts']
            yw = cb[3] + 1.0                                               # plan draws it 2.5 u south of the court: put it on the court edge
            free = [(min(wall[0][0], wall[-1][0]), max(wall[0][0], wall[-1][0]))]
            for b in blds:                                                 # where a house back wall already closes the court, no extra wall
                r_ = bb(b['pl'])
                if r_[1] - 1.5 <= yw <= r_[3] + 0.5:
                    nf = []
                    for lo, hi in free:
                        if r_[2] <= lo or r_[0] >= hi:
                            nf.append((lo, hi))
                            continue
                        if r_[0] > lo:
                            nf.append((lo, r_[0]))
                        if r_[2] < hi:
                            nf.append((r_[2], hi))
                    free = nf
            for j_, (lo, hi) in enumerate(f_ for f_ in free if f_[1] - f_[0] > 2.5):
                zones.append({'id': '05-13-wall%d' % (j_ + 1), 'kind': 'wall', 'line': WL([(lo, yw), (hi, yw)]), 'h_m': 4.0, 'w_m': 0.4, 'material': 'brick_SK3a',
                              'notes': 'blind brick wall closing the courtyard to the south where no house back wall does (legend §4)'})
            zones.append({'id': '05-13-arch', 'kind': 'arch', 'poly': ccw(WL(R(*bb(arch_el)))), 'clear_w_m': round((bb(arch_el)[2] - bb(arch_el)[0]) * U, 2), 'clear_h_m': 4.5,
                          'notes': 'drive-through arch under the house, from Hse2 (curb drop 05-drop-*)'})
            ycap = court
            courtd = (cb[3] - cb[1]) * U
            question('База 4 (13): после расширения улиц до 22 м (план v28) двор-колодец ужался до %.1f × %.1f м (утверждено ~28 × 9 м; v10 §4 — дворы и '
                     'места погрузки от 12–15 м, чтобы развернуться). Бусик проезжает арку, встаёт к рольставне, выезжает задом или в 2–3 приёма.'
                     % ((cb[2] - cb[0]) * U, courtd),
                     ['1 — как на плане: двор %.1f м в глубину (сейчас в данных)' % courtd,
                      '2 — двор 12 м в глубину: ряд домов к набережной S1 становится мельче на %.1f м' % (12.0 - courtd)], 1, 'данные: вариант 1')
        else:
            zones.append({'id': '05-%s-yard' % lab, 'kind': 'service_yard', 'poly': ccw(WL(e['pts'])), 'surface': 'concrete_SK3c', 'label': lab,
                          'size_m': [round((yb[2] - yb[0]) * U, 1), round((yb[3] - yb[1]) * U, 1)], 'loading_pad': True,
                          'notes': 'wide service yard open to the street: bins, roll-shutter gate, yellow bollards (legend §5)'})
        for i, bn in enumerate(x for x in bins if pin(pcen(x['pts']), e['pts'])):
            r_ = bb(bn['pts'])
            props.append({'id': '05-%s-bin%d' % (lab, i + 1), 'kind': 'dumpster' if lab != '13' else ('bin_green' if i == 0 else 'bin_blue'),
                          'pos': rnd2(W(pcen(bn['pts']))), 'rot_deg': 0.0 if (r_[2] - r_[0]) > (r_[3] - r_[1]) else 90.0,
                          'size': [round(max(r_[2] - r_[0], r_[3] - r_[1]) * U, 1), round(min(r_[2] - r_[0], r_[3] - r_[1]) * U, 1), 1.3], 'grip_anchor': False})
        for i, c in enumerate(x['c'] for x in ybol if pin(x['c'], e['pts']) or min(abs(x['c'][0] - q[0]) + abs(x['c'][1] - q[1]) for q in e['pts']) < 12):
            props.append({'id': '05-%s-bollard%d' % (lab, i + 1), 'kind': 'bollard_yellow', 'pos': rnd2(W(c)), 'rot_deg': 0.0, 'size': [0.3, 0.3, 1.0], 'grip_anchor': True})
    pal = sel(els, g='buildings', tag='polygon', fill='#B08D5E')[0]['pts']
    props.append({'id': '05-13-pallets', 'kind': 'pallet_stack', 'pos': rnd2(W(pcen(pal))), 'rot_deg': 0.0, 'size': [2.2, 2.4, 1.2], 'grip_anchor': False})

    # alleys
    alley_bins = [x for x in bins if any(pin(pcen(x['pts']), R(*a['rect0'])) for a in alleys)]
    for a in alley_out:
        cax, aax = a['cax'], a['aax']
        whole = [0, 0, 0, 0]
        whole[cax], whole[cax + 2], whole[aax], whole[aax + 2] = a['lo'], a['hi'], min(r_[aax] for r_ in a['rects']), max(r_[aax + 2] for r_ in a['rects'])
        ends = []
        for r_ in a['rects']:
            m_ = next((m for m in a['mouths'] if m['rect'] == r_), None)
            st_name = None
            if m_:
                for bd in bands:
                    if bd['ax'] == cax and abs(abs(bd['axis'] - m_['pos'][aax]) - HW) < 1.0 and bd['rect'][1 - bd['ax']] <= a['c'] <= bd['rect'][3 - bd['ax']]:
                        st_name = bd['street']
                    elif bd['ax'] != cax and abs(abs(bd['axis'] - m_['pos'][aax]) - HW) < 1.0:
                        st_name = bd['street']
            ends.append({'poly': ccw(WL(R(*r_))), 'length_m': round((r_[aax + 2] - r_[aax]) * U, 1), 'mouth': rnd2(W(m_['pos'])) if m_ else None,
                         'mouth_street': st_name, 'facing_deg': facing(tuple(float(m_['dir']) if i == aax else 0.0 for i in (0, 1))) if m_ else None})
        z = {'id': a['id'], 'kind': 'dead_end_alley_pair' if a['pair'] else 'dead_end_alley', 'poly': ccw(WL(R(*whole))), 'width_m': ALLEY * U,
             'surface': 'asphalt_old_SK2a', 'dead_ends': ends, 'width_plan_m': round(a['w0_m'], 2),
             'dressing': 'dark asphalt, dumpsters, fire escapes, back doors, puddles, blind wall at the end, dim lamp over a back door',
             'notes': 'both ends open to a street, plug house in the middle -> two dead ends (v02 §8.5)' if a['pair'] else 'single blind alley (v10 §7.5: NW1 / SW2), one mouth'}
        if a['plugs']:
            z['plug_wall'] = ccw(WL(a['plugs'][0]['pl']))
            z['plug_building'] = next(b['id'] for b in blds if b is a['plugs'][0])
        zones.append(z)
        for i, bn in enumerate(x for x in alley_bins if pin(pcen(x['pts']), R(*whole))):
            c = list(pcen(bn['pts']))
            r_ = bb(bn['pts'])
            dpt = min(r_[2] - r_[0], r_[3] - r_[1])
            c[cax] = a['lo'] + dpt / 2 + 2.0                               # keep the bin against the (moved) alley wall
            props.append({'id': '%s-bin%d' % (a['id'], i + 1), 'kind': 'dumpster', 'pos': rnd2(W(c)), 'rot_deg': 0.0 if aax == 0 else 90.0,
                          'size': [round(max(r_[2] - r_[0], r_[3] - r_[1]) * U, 1), round(dpt * U, 1), 1.3], 'grip_anchor': False})

    # squares 20 / 23 (the only trees of Downtown), pond, paths
    parks = sel(els, g='squares_and_lots', tag='polygon', fill='#CFE0B5')
    pond = sel(els, g='squares_and_lots', tag='polygon', fill='#8FC3D9')[0]['pts']
    paths = [e['pts'] for e in sel(els, g='squares_and_lots', tag='polyline', stroke='#E9DFC6')]
    for e in parks:
        lab = next(k for k in ('20', '23') if pin(labels[k], e['pts']))
        has_pond = pin(pcen(pond), e['pts'])
        zones.append({'id': '05-%s-square' % lab, 'kind': 'park', 'poly': ccw(WL(e['pts'])), 'surface': 'lawn', 'label': lab,
                      'notes': 'city square: lawn, paths, benches with bins, lamps' + ('; pond with a stone edge' if has_pond else '')})
        zones.append({'id': '05-%s-veg' % lab, 'kind': 'veg_zone', 'poly': ccw(WL(e['pts'])), 'density': 'grove', 'species': 'leafy',
                      'target_count': 3 if has_pond else 4, 'groups': '2-5 trees', 'min_gap_path_m': 2.0,
                      'notes': 'Downtown trees ONLY here and in the other square (v10 §7.5, ~7 per district); keep off the paths and the pond'})
        for pth in paths:
            if pin(pth[len(pth) // 2], e['pts']) or any(pin(q, e['pts']) for q in pth[1:-1]):
                zones.append({'id': '05-%s-path%d' % (lab, sum(1 for z in zones if z['id'].startswith('05-%s-path' % lab)) + 1), 'kind': 'path',
                              'line': WL(pth), 'width_m': 2.8, 'surface': 'sidewalk_S1', 'closed': math.hypot(pth[0][0] - pth[-1][0], pth[0][1] - pth[-1][1]) < 1})
        if has_pond:
            zones.append({'id': '05-%s-pond' % lab, 'kind': 'pond', 'poly': ccw(WL(pond)), 'depth_m': 0.6, 'edge': 'stone'})

    # gas station 41, taxi stand 12
    pumps = sel(els, g='buildings', tag='polygon', fill='#C8372D')
    zones.append({'id': '05-41-forecourt', 'kind': 'gas_station', 'poly': ccw(WL(gas_lot)), 'surface': 'concrete_SK3c', 'label': '41',
                  'canopy': ccw(WL(R(*canopy))), 'canopy_clear_h_m': 5.0, 'notes': 'forecourt (not a parking lot): canopy over 3 pump islands, shop at the back, '
                                                                                   'entries from the boulevard (curb drops 05-drop-41-*)'})
    for i, e in enumerate(pumps):
        props.append({'id': '05-41-pump%d' % (i + 1), 'kind': 'fuel_pump_island', 'pos': rnd2(W(pcen(e['pts']))), 'rot_deg': 90.0, 'size': [1.2, 2.4, 1.9], 'grip_anchor': True})
    zones.append({'id': '05-12-stand', 'kind': 'taxi_stand', 'poly': ccw(WL(taxi_lot)), 'surface': 'asphalt_A5d12', 'label': '12',
                  'stalls': len(sel(els, g='squares_and_lots', tag='polyline', stroke='#F4F4F0')) - 1, 'stall_dir': 'perpendicular to Vd',
                  'notes': 'taxi depot stand (the only surface parking besides gas 41; v10 §7.5), exit onto Vd'})

    # legend objects
    for lab, p in sorted(labels.items()):
        props.append({'id': '05-L' + lab, 'kind': 'legend_object', 'label': lab, 'pos': rnd2(W(p)), 'desc': LEGEND.get(lab, ''),
                      'notes': 'label position of the plan (marker, not geometry)'})

    # district ground, no-tree, pads
    dist = model['district']
    def offset_rect_poly(pl, d):                                           # rectilinear miter offset (outward for y-south ccw-in-plan)
        n = len(pl)
        sgn = 1 if sum(pl[i - 1][0] * pl[i][1] - pl[i][0] * pl[i - 1][1] for i in range(n)) > 0 else -1
        out = []
        for i in range(n):
            a, p, b = pl[i - 1], pl[i], pl[(i + 1) % n]
            def nrm(u, v):
                L = math.hypot(v[0] - u[0], v[1] - u[1])
                return (-(v[1] - u[1]) / L * sgn, (v[0] - u[0]) / L * sgn)
            n1, n2 = nrm(a, p), nrm(p, b)
            out.append((p[0] + (n1[0] + n2[0]) * d - (n1[0] * n2[0] * 0) , p[1] + (n1[1] + n2[1]) * d))
        return out
    test = offset_rect_poly(dist, 10)
    if parea(test) < parea(dist):
        offset_rect_poly_ = lambda pl, d: offset_rect_poly(pl, -d)
    else:
        offset_rect_poly_ = offset_rect_poly
    outer = offset_rect_poly_(dist, HW + 10)                               # outer sidewalk edge + 2 m
    zones.append({'id': '05-ground', 'kind': 'ground', 'poly': ccw(WL(outer)), 'surface': 'concrete_SK3c', 'flat': True,
                  'notes': 'Downtown pad (Rough height, v10 §3.1): streets / sidewalks / plaza / yards on top; unbuilt block interiors = concrete; '
                           'meadow outside blends over 40-80 m (v10 §9)'})
    for nm_ in ('OB1', 'NEX'):
        r_ = model['blocks'][nm_]['new']
        zones.append({'id': '05-ground-' + nm_, 'kind': 'ground', 'poly': ccw(WL(R(r_[0] - 10, r_[1] - 10, r_[2] + 10, r_[3] + 10))), 'surface': 'concrete_SK3c',
                      'flat': True, 'notes': 'pad of the stopper houses outside the ring bend'})
    zones.append({'id': '05-no-tree-default', 'kind': 'no_tree', 'poly': ccw(WL(outer)), 'veg_zones_override': True,
                  'why': 'Downtown: trees ONLY inside squares 20 and 23 (veg_zone polygons of this file); never on streets, sidewalks, the plaza, yards, alleys '
                         '(v10 §7.5); the 2 m margin outside the ring sidewalk keeps the meadow trees off the curb'})
    fix(None, 'Деревья: в Даунтауне только скверы 20 и 23 (veg_zone); остальной район и 2 м за внешним тротуаром кольца — no_tree. Деревья картинки v85 '
              'на улице над Даунтауном и у базы 4 справа снизу в данные не попадают.', 'v10 §7.5: Вадим ругался на деревья на дороге сверху Даунтауна и у базы 4.')
    fix(None, 'Улицы Va2 и Vds южнее S1 (на плане — мосты через бывший канал) не строятся: улица кончается на S1, дальше — съезд на песок пляжа '
              '(зона entry S-Va2 / S-Vds, понижение бордюра на южном тротуаре S1).', 'Канала у города нет с v38 (v02 §5); пляж — район 09.')
    fix(None, 'Гидранты, фонари, знаки «стоп», светофоры и лавки плана не переносятся точками: вместо них зоны перекрёстков (control, зебры только у бульвара) '
              'и улицы с шириной — их расставляет шаг s06 по v10 §8.', 'v10 §1.2 и §8: мелкие детали по правилам, не по точкам картинки.')

    # ------------------------------------------------ questions (approved-decision level)
    question('Высоты стеклянных зданий не заданы ни легендой, ни v10: круглая угловая башня (у 43) и офисы 05/06.',
             ['1 — башня 24 эт. (~86 м), офисы 10 эт. (~36 м) — по длине тени на плане (сейчас в данных)', '2 — башня 16 эт., офисы 8 эт. (ниже, чтобы близнецы доминировали сильнее)'],
             1, 'данные: вариант 1')
    tun = next(z for z in entries if z['id'].endswith('N-tunnel'))
    eli = next(z for z in entries if z['id'].endswith('-E'))
    fix(Winv(tun['pos']), 'Въезд из тоннеля: на картинке дорога входит в угол N2 / Vn наискосок, в %.1f м западнее оси Vn — точка входа в данных на оси Vn '
                          '(продолжение улицы), последние 15–20 м дороги мира выпрямить по ней.' % abs(tun.get('world_road_lateral_offset_m', 0.0)),
        'v10 §6: примыкание под прямым углом, прямой подход 10–20 м, ось боковой дороги доходит до оси главной.')
    fix(Winv(eli['pos']), 'Въезд на Элиту: ось каменной дороги на картинке на %.1f м севернее оси бульвара B — в данных вход на оси B, начало каменной дороги '
                          'сдвинуть к ней (переход асфальт → камень на краю внешнего тротуара).' % abs(eli.get('world_road_lateral_offset_m', 0.0)),
        'v10 §6: дорога продолжается полотном до проезжей части улицы, без ступеньки и излома.')

    # ------------------------------------------------ checks
    checks = {}
    worst = 0.0
    for b in blds:
        for bd in bands:
            ox, oy = overlap(bb(b['pl']), bd['rect'])
            worst = max(worst, min(ox, oy) if min(ox, oy) > 0 else 0)
    checks['max_building_intrusion_into_street_profile_m'] = round(worst * U, 2)
    checks['alley_widths_m'] = {a['id']: round((a['hi'] - a['lo']) * U, 2) for a in alley_out}
    checks['entries'] = len(entries)
    checks['facade_to_facade_m'] = (CARR + 2 * WALK)
    checks['see_through_m'] = sight_lines(blds, st, model, outer)
    pk_ = pockets(blds, model, alley_out, els, bands)
    checks['unbuilt_block_pockets'] = pk_
    taxi_b = next(b for b in blds if b['kind'] == 'taxi_depot')
    tb = bb(taxi_b['pl'])
    zones.append({'id': '05-yard-12', 'kind': 'yard', 'poly': ccw(WL(R(tb[0], tb[3], tb[2], model['blocks']['Ea1']['new'][3]))), 'surface': 'concrete_SK3c',
                  'notes': 'taxi depot yard behind the depot building, reached from the stand (2 taxis parked, washing spot)'})
    for i, o in enumerate(x for x in pk_ if x['area_m2'] >= 100 and x['fill'] >= 0.8):
        why = {'NEX': 'back yard of the stopper houses outside the N3 bend (faces the slope; not a parking lot)',
               'Ea1': 'taxi depot yard behind the depot building, reached from the stand'}.get(o['block'], 'inner yard of block %s' % o['block'])
        zones.append({'id': '05-yard-%s' % o['block'], 'kind': 'yard', 'poly': ccw(WL(R(*o['rect']))), 'surface': 'concrete_SK3c', 'notes': why})

    fit = measure_fit(W, Wpic, Wu2w, st, out_b, model, blds)
    lin, s_ref = info['lin'], info['s_ref']
    transform = ('plan units (x east, y south; 1 u = 0.2 m) -> Chrome render of Город_Downtown_v31.svg (width %d / viewBox %g = %.3f px/u) -> '
                 'make_downtown_world_v31 resize 1/%.1f -> downtown_v31_world.png %dx%d (1 px = 1 u) -> master <image> x %g y %g in %s (translate(2820 1000)) '
                 '-> master units = (%.1f + gx, %.1f + gy) -> pre-shift metres (%.3f + %.4f gx, %.3f - %.4f gy) -> world: %s. Net: x = %.3f + 0.2 gx, '
                 'y = %.3f - 0.2 gy (scale 1.0, no rotation; v76 used 798 + 0.99 xm / 469 - 0.99 ym for v27). Fit on the v85 render: %s'
                 % (info['pw'], info['vb'][2], info['pw'] / info['vb'][2], info['k'], info['iw'], info['ih'], info['img']['x'], info['img']['y'],
                    info['img']['group'], info['master0'][0] - 0, info['master0'][1], lin[0], lin[1], lin[2], lin[3],
                    ('rigid post-shift (%+.1f, %+.1f) m = shift_m of the district body; post_shift_v85.shift_image applies exactly this to every '
                     'Downtown pixel (it evaluates shift_m at the output point, output y <= 470 m everywhere here)' % s_ref) if RIGID else
                    'raster-consistent post-shift per point (fixed point q = p + shift_m(q))',
                    lin[0] + s_ref[0], lin[2] + s_ref[1], fit['text']))

    # ------------------------------------------------ counts + output
    houses = [r_ for r_ in out_b if r_['kind'] in ('house', 'arch_house')]
    fl_hist = {}
    for r_ in houses:
        fl_hist[r_['floors']] = fl_hist.get(r_['floors'], 0) + 1
    counts = {'buildings': len(out_b), 'houses': len(houses), 'houses_by_floors': {str(k): fl_hist[k] for k in sorted(fl_hist)},
              'corner_houses': sum(1 for r_ in out_b if r_.get('corner')), 'stopper_houses_outside_ring': sum(1 for b in blds if b['kind'] == 'house' and b['block'] in ('OB1', 'NEX')),
              'towers': sum(1 for r_ in out_b if r_['kind'] in ('tower', 'tower_round')), 'twin_towers': sum(1 for r_ in out_b if r_['kind'] == 'tower'),
              'glass_offices': sum(1 for r_ in out_b if r_['kind'] == 'glass_office'), 'pavilions': sum(1 for r_ in out_b if r_['kind'] == 'pavilion'),
              'alley_plugs': sum(1 for r_ in out_b if r_['kind'] == 'alley_plug'), 'kinds': {},
              'alleys': {'zones': len(alley_out), 'pairs': sum(1 for a in alley_out if a['pair']), 'single': sum(1 for a in alley_out if not a['pair']),
                         'dead_ends': sum(len(a['rects']) for a in alley_out)},
              'squares': len(parks), 'veg_target_trees': sum(z.get('target_count', 0) for z in zones if z['kind'] == 'veg_zone'),
              'streets': len(st), 'junctions': sum(1 for z in zones if z['kind'] == 'junction'),
              'junctions_traffic_light': sum(1 for z in zones if z['kind'] == 'junction' and z['control'] == 'traffic_light'),
              'crosswalks': sum(len(z['crosswalks']) for z in zones if z['kind'] == 'junction'), 'entries': len(entries),
              'curb_drops': sum(1 for z in zones if z['kind'] == 'curb_drop'), 'props': len(props), 'zones': len(zones),
              'entrances': sum(len(r_['entrances']) for r_ in out_b), 'fire_escapes': sum(len(r_['sockets']['fire_escape'] or []) for r_ in out_b),
              'water_tanks': sum(len(r_['sockets']['water_tank'] or []) for r_ in out_b), 'material_slots': {}}
    for r_ in out_b:
        counts['kinds'][r_['kind']] = counts['kinds'].get(r_['kind'], 0) + 1
        counts['material_slots'][r_['material_slot']] = counts['material_slots'].get(r_['material_slot'], 0) + 1
    for f in FIXES:
        wp = f.pop('where_plan')
        ru, why = f.pop('ru'), f.pop('why_ru')
        f.update({'where': rnd2(W(wp)) if wp is not None else None, 'ru': ru, 'why_ru': why})
    out = {'district': 'downtown', 'version': 'v85 from plan v31',
           'sources': [os.path.relpath(p, ROOT).replace(os.sep, '/') for p in (PLAN_SVG, PLAN_PY, PLAN_PNG, WORLD_PY)] +
                      ['ArtSource/References/Map/World_v85/VOLUNTEERS_MAP_MASTER_v85.svg (<image> downtown_v31_world.png in D05, R84_downtown_entries, R24_roads, R74_elite_ring)',
                       'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §1 §4 §6 §7.5 §8 §14', 'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.5',
                       'docs/specs/DOWNTOWN_LEGEND_v26.md', 'docs/specs/DOWNTOWN_SPEC_2026-10-15_v03.md'],
           'transform': transform, 'fit': fit['data'], 'rigid': RIGID,
           'pad_height_m': 5.0, 'pad_note': 'flat pad, same height as the Rough (v10 §3.1)', 'abs_heights': False,
           'lighting': 'clear_blue_clouds', 'lighting_notes': 'juicy blue sky with clouds (v02 §6 table), light haze to the horizon, no fog in the streets',
           'street_profile': {'carriageway_m': CARR, 'sidewalk_m': WALK, 'curb_m': CURB, 'facade_to_facade_m': CARR + 2 * WALK, 'corner_radius_m': CORNER_R,
                              'surface': 'asphalt_A5d12', 'sidewalk_surface': 'sidewalk_S1', 'alley_m': ALLEY * U},
           'buildings': out_b, 'props': props, 'zones': zones, 'fixed_by_logic': FIXES, 'questions_for_vadim': QUESTIONS, 'counts': counts, 'checks': checks}
    return out, W


# ---------------------------------------------------------------- checks
def raster_buildings(blds, scale=1.0):
    im = Image.new('L', (int(2600 * scale), int(1500 * scale)), 0)
    dr = ImageDraw.Draw(im)
    for b in blds:
        dr.polygon([((p[0] + 120) * scale, p[1] * scale) for p in b['pl']], fill=255)
    return np.asarray(im) > 0


def sight_lines(blds, st, model, outer):
    """Straight open run (no building) along each street axis through the segment midpoint, clipped to the plan (x -60..2400,
    y 0..1265 = up to the S1 south sidewalk), metres (v10 §7.5: no see-through "hill to beach" lines)."""
    m = raster_buildings(blds)
    im = Image.new('L', (2600, 1500), 0)
    ImageDraw.Draw(im).polygon([(p[0] + 120, p[1]) for p in outer], fill=255)
    m = m | ~(np.asarray(im) > 0)                                          # outside the ring = end of the city view
    res = {}
    for name, s in st.items():
        for a, b in zip(s['pts'][:-1], s['pts'][1:]):
            vert = abs(a[0] - b[0]) < 1e-6
            line_ = m[0:1266, int(a[0] + 120)] if vert else m[int(a[1]), 60:2520]
            c = int((a[1] + b[1]) / 2) if vert else int((a[0] + b[0]) / 2 + 60)
            lo = hi = min(max(c, 0), len(line_) - 1)
            while lo > 0 and not line_[lo - 1]:
                lo -= 1
            while hi < len(line_) - 1 and not line_[hi + 1]:
                hi += 1
            key = '%s@%s%d' % (name, 'x' if vert else 'y', a[0] if vert else a[1])
            res[key] = max(res.get(key, 0), round((hi - lo + 1) * U, 1))
    return dict(sorted(res.items(), key=lambda kv: -kv[1])[:10])


def pockets(blds, model, alley_out, els, bands):
    """Unbuilt pockets inside blocks (v10 §7.5 "всё застроено"): block area minus buildings, alleys, yards, squares, lots, plaza, street profile."""
    from scipy import ndimage
    im = Image.new('L', (2600, 1500), 0)
    dr = ImageDraw.Draw(im)
    T = lambda pl: [(p[0] + 120, p[1]) for p in pl]
    for k, b in model['blocks'].items():
        if k != 'SQ':                                                      # SQ = plaza (paved to the sidewalk)
            dr.polygon(T(b['poly']), fill=255)
    for bd in bands:
        dr.polygon(T(R(*bd['rect'])), fill=0)
    for b in blds:
        dr.polygon(T(b['pl']), fill=0)
    for a in alley_out:
        for r_ in a['rects']:
            dr.polygon(T(R(*r_)), fill=0)
    for e in els:
        if e['g'] == 'squares_and_lots' and e['tag'] == 'polygon' and e['fill'] not in ('none', None):
            dr.polygon(T(e['pts']), fill=0)
    m = np.asarray(im) > 0
    m = ndimage.binary_opening(m, iterations=2)                            # ignore slivers < ~1 m
    lab, n = ndimage.label(m)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        a_m2 = len(xs) * U * U
        if a_m2 >= 15:
            r_ = (float(xs.min()) - 120, float(ys.min()), float(xs.max()) + 1 - 120, float(ys.max()) + 1)
            out.append({'plan_centre': [round(float(xs.mean()) - 120, 1), round(float(ys.mean()), 1)], 'area_m2': round(a_m2, 1),
                        'block': blk_of(model, (float(xs.mean()) - 120, float(ys.mean())), 5), 'rect': r_,
                        'fill': round(len(xs) / ((r_[2] - r_[0]) * (r_[3] - r_[1])), 2)})
    return sorted(out, key=lambda o: -o['area_m2'])


def measure_fit(W, Wpic, Wu2w, st, out_b, model, blds):
    pts = [W(p) for s in st.values() for p in s['pts']]
    x0w, x1w = int(min(p[0] for p in pts)) - 15, int(max(p[0] for p in pts)) + 15
    y0w, y1w = int(min(p[1] for p in pts)) - 15, int(max(p[1] for p in pts)) + 25
    im = Image.open(MAP_FULL).convert('RGB').crop((x0w * 5, (950 - y1w) * 5, x1w * 5, (950 - y0w) * 5))
    a = np.asarray(im).astype(np.int16)
    road = ((np.abs(a - np.array([95, 102, 108])) <= 10).all(-1)) | (a.min(-1) >= 238)
    Hh, Ww = road.shape
    pix = lambda q: (int(round((y1w - q[1]) * 5)), int(round((q[0] - x0w) * 5)))
    jun = [p for p, n in junctions(st)]
    res = {'body': [], 'north': []}
    widths, obstructed = [], []
    for name, s in st.items():
        for a_, b_ in zip(s['pts'][:-1], s['pts'][1:]):
            L = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
            u = ((b_[0] - a_[0]) / L, (b_[1] - a_[1]) / L)
            for t in np.arange(20, L - 20, 25):
                p = (a_[0] + u[0] * t, a_[1] + u[1] * t)
                if min(math.hypot(p[0] - j[0], p[1] - j[1]) for j in jun) < 90 or p[1] > 1240:
                    continue
                q0, q1 = W(p), W((p[0] - u[1] * 10, p[1] + u[0] * 10))
                n = ((q1[0] - q0[0]) / 2.0, (q1[1] - q0[1]) / 2.0)            # unit world normal
                prof = []
                for sv in np.arange(-10.0, 10.01, 0.2):
                    i, j = pix((q0[0] + n[0] * sv, q0[1] + n[1] * sv))
                    prof.append(bool(0 <= i < Hh and 0 <= j < Ww and road[i, j]))
                ss = np.arange(-10.0, 10.01, 0.2)
                k0 = int(np.argmin(np.abs(ss)))
                if not any(prof[max(0, k0 - 15):k0 + 16]):
                    continue
                kk = [k for k in range(len(prof)) if prof[k]]
                kc = min(kk, key=lambda k: abs(k - k0))
                lo = hi = kc
                while lo > 0 and (prof[lo - 1] or (lo > 1 and prof[lo - 2])):
                    lo -= 1
                while hi < len(prof) - 1 and (prof[hi + 1] or (hi < len(prof) - 2 and prof[hi + 2])):
                    hi += 1
                w_ = (hi - lo + 1) * 0.2
                if not 9.0 <= w_ <= 15.0:
                    continue
                if not 11.0 <= w_ <= 13.0:                                  # something drawn on the carriageway (bus stop 14)
                    obstructed.append((name, rnd2(p), round(w_, 1)))
                    continue
                cen = (ss[lo] + ss[hi]) / 2
                key = 'north' if p[1] < 150 else 'body'
                res[key].append((name, round(float(cen), 2)))

                widths.append(w_)
    house = 0
    tot = 0
    for b in blds:
        if b['kind'] not in ('house', 'arch_house', 'loft'):
            continue
        r_ = bb(b['pl'])
        if r_[1] < 150:
            continue
        fp = [W(p) for p in R(r_[0] + 5, r_[1] + 5, r_[2] - 5, r_[3] - 5)]
        if r_[2] - r_[0] < 12 or r_[3] - r_[1] < 12:
            continue
        xs, ys = [p[0] for p in fp], [p[1] for p in fp]
        i0, j0 = pix((min(xs), max(ys)))
        i1, j1 = pix((max(xs), min(ys)))
        sub = a[max(0, i0):i1, max(0, j0):j1].reshape(-1, 3)
        grounds = np.array([[95, 102, 108], [227, 225, 217], [232, 238, 219], [217, 210, 196], [227, 235, 212], [157, 162, 162], [216, 212, 202], [191, 195, 196]])
        g = (np.abs(sub[:, None, :] - grounds[None, :, :]).max(-1) <= 6).any(-1)
        house += int((~g).sum())
        tot += len(g)
    body = [c for _, c in res['body']]
    north = [c for _, c in res['north']]
    allp = [p for b in blds for p in b['pl']] + [p for s in st.values() for p in s['pts']]
    pic_dev = max(math.hypot(W(p)[0] - Wpic(p)[0], W(p)[1] - Wpic(p)[1]) for p in allp)
    u2w_dev = max((math.hypot(Wu2w(p)[0] - Wpic(p)[0], Wu2w(p)[1] - Wpic(p)[1]), p) for p in allp)
    n2 = W(st['N2']['pts'][0])
    n2u = Wu2w(st['N2']['pts'][0])
    data = {'street_axis_offset_body_m': {'n': len(body), 'median': round(float(np.median(body)), 2), 'max_abs': round(float(np.max(np.abs(body))), 2)},
            'street_axis_offset_north_band_m': {'n': len(north), 'median': round(float(np.median(north)), 2) if north else None,
                                                'max_abs': round(float(np.max(np.abs(north))), 2) if north else None},
            'carriageway_width_measured_m': {'median': round(float(np.median(widths)), 2), 'min': round(float(np.min(widths)), 2), 'max': round(float(np.max(widths)), 2)},
            'house_fill_on_house_colour': round(house / max(1, tot), 3), 'sections_obstructed': obstructed,
            'rigid_vs_raster_post_shift_max_m': round(pic_dev, 3),
            'common_u2w_vs_raster_m': {'max': round(u2w_dev[0], 2), 'at_plan': rnd2(u2w_dev[1]),
                                       'N2_axis': round(math.hypot(n2[0] - n2u[0], n2[1] - n2u[1]), 2)}}
    text = ('carriageway cross-sections on VOLUNTEERS_MAP_FINAL_v85.png (5 px/m, %d clean sections south of N1/N3): drawn axis vs data axis median %.2f m, max %.2f m; '
            'drawn carriageway width median %.1f m (12 m expected; %d sections skipped where the drawn bus stop 14 narrows the asphalt); houses (inset 1 m) %.0f %% on house colours; north band (N2 / Nj / stoppers) %d sections, '
            'max %.2f m. The raster post-shift (shift_m evaluated at the OUTPUT point) is exactly the rigid (+20, -28) for every Downtown point (max diff %.3f m); '
            'common.u2w (shift_m at the pre-shift point) would be up to %.1f m off the drawn picture in the north band (N2 axis %.1f m).'
            % (len(body), data['street_axis_offset_body_m']['median'], data['street_axis_offset_body_m']['max_abs'], data['carriageway_width_measured_m']['median'],
               len(obstructed), data['house_fill_on_house_colour'] * 100, len(north), data['street_axis_offset_north_band_m']['max_abs'] or 0, pic_dev,
               u2w_dev[0], data['common_u2w_vs_raster_m']['N2_axis']))
    return {'data': data, 'text': text}


# ---------------------------------------------------------------- check images
def draw(im, tp, d, s, full=False):
    dr = ImageDraw.Draw(im)
    for z in d['zones']:
        if z['kind'] in ('ground', 'no_tree', 'street'):
            continue
        col = (20, 140, 40) if z['kind'] == 'veg_zone' else (0, 200, 220)
        if 'poly' in z:
            dr.polygon([tp(q) for q in z['poly']], outline=col)
        if 'line' in z:
            dr.line([tp(q) for q in z['line']], fill=col, width=2)
        if z['kind'] in ('entry', 'junction'):
            x, y = tp(z['pos'])
            rr = s * (1.6 if z['kind'] == 'entry' else 0.6)
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(0, 200, 220), width=2)
            if z['kind'] == 'entry':
                dr.polygon([tp(q) for q in z['curb_drop']], outline=(0, 200, 220))
    for z in d['zones']:
        if z['kind'] == 'street':
            dr.line([tp(q) for q in z['poly_line']], fill=(0, 190, 0), width=2 if full else 1)
    for b in d['buildings']:
        dr.polygon([tp(p) for p in b['footprint']], outline=(255, 0, 0), width=2 if full else 1)
        for a in b.get('arches', []):
            dr.polygon([tp(p) for p in a['rect']], outline=(255, 140, 0))
        for e in b['entrances']:
            x, y = tp(e['pos'])
            rr = s * 0.45
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(0, 0, 255))
    for p in d['props']:
        x, y = tp(p['pos'])
        rr = s * (0.9 if p['kind'] == 'legend_object' else 0.4)
        if p['kind'] == 'legend_object':
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 0, 255), width=2)
        else:
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 0, 255))


def overlays(d):
    os.makedirs(WORK, exist_ok=True)
    xs = [p[0] for b in d['buildings'] for p in b['footprint']] + [z['pos'][0] for z in d['zones'] if z['kind'] == 'entry']
    ys = [p[1] for b in d['buildings'] for p in b['footprint']] + [z['pos'][1] for z in d['zones'] if z['kind'] == 'entry']
    x0, x1, y0, y1 = int(min(xs)) - 15, int(max(xs)) + 15, int(min(ys)) - 15, int(max(ys)) + 15
    s = 3
    im = Image.open(MAP_PREVIEW).convert('RGB').crop((x0, 950 - y1, x1, 950 - y0))
    im = im.resize((im.width * s, im.height * s), Image.NEAREST)
    draw(im, lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s), d, s)
    im.save(os.path.join(WORK, 'check_downtown.png'))
    s = 5
    im = Image.open(MAP_FULL).convert('RGB').crop((x0 * s, (950 - y1) * s, x1 * s, (950 - y0) * s))
    draw(im, lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s), d, s, full=True)
    im.save(os.path.join(WORK, 'check_downtown_full.png'))


def main():
    d, W = build()
    save_json('districts/downtown_v85.json', d)
    overlays(d)
    print('downtown_v85 counts:', d['counts'])
    print('fit:', d['transform'].split('Fit on the v85 render: ')[1])
    print('checks:', {k: v for k, v in d['checks'].items() if k != 'unbuilt_block_pockets'})
    print('pockets:', d['checks']['unbuilt_block_pockets'][:12])
    print('fixes:', len(d['fixed_by_logic']), 'questions:', len(d['questions_for_vadim']))


if __name__ == '__main__':
    main()
