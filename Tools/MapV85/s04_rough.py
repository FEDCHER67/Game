"""Step 4 / district 04 Rough ("Неблагополучный"): plan v52 -> world v85 district data (lead brief "Map W85 build", CL-MAP85, 2026-10-21).

Authority (handoff v10 §0-§1, §7.4): houses, arches, podyezds, garages, base 3, shop, club, box, playgrounds, trash sections 1:1 from
`World_v83/Districts/Планировка_v52.json` (+ the model of `build_rough_v52.py` for palisades, kiosks, squares); the football box
40 x 33 m and the gaps 6 / 8 m from v10 §7.4; roads / exits / KPP from the master SVG v85 (newest network); trees -> veg_zone /
no_tree zones (no plan tree points); lamps and the 8 cars by rule (ROUGH_LEGEND_v45 §1.6, v10 §8), validated against tracks.
Every deviation from the drawing is logged in "fixed_by_logic"; gameplay-level choices are in "questions_for_vadim".

Chain (derived from the sources at run time, see `load_chain`): plan metres (x east, z north, 0 = SW corner of the outer-road axis)
-> plan px (build_rough_v52 export: x/M + T(113,1765).x, T(113,1765).y - z/M) -> rough_v52_world.png px (make_rough_world_v52:
resize by k = M*5 to int size) -> master-SVG units (+ <image> x, y) -> world v85 = common.u2w (pre-shift metres + post_shift,
+22 m north in the Rough band). Fit against the v85 render is measured every run and written to "transform".

Outputs: Data/<REV>/districts/rough_v85.json (DISTRICT_SCHEMA.md), out_<REV>/check_rough.png (preview x3),
out_<REV>/check_rough_full.png (FINAL 5 px/m crop, footprints red). Run: python s04_rough.py (deterministic, ~15 s).
"""
import json
import math
import os
import random
import re

import numpy as np
from PIL import Image, ImageDraw

from common import (MAP_FULL, MAP_PREVIEW, REF, ROOT, WORK, apply, attr, area, ccw, h01, num, points_of, rnd2, save_json,
                    svg_tags, svg_text, u2w)

Image.MAX_IMAGE_PIXELS = None
SRC_DIR = os.path.join(REF, 'World_v83', 'Districts')
PLAN_JSON = os.path.join(SRC_DIR, 'Планировка_v52.json')
PLAN_PY = os.path.join(SRC_DIR, 'build_rough_v52.py')
PLAN_PNG = os.path.join(SRC_DIR, 'Неблагополучный_район_v52.png')
WORLD_PY = os.path.join(REF, 'World_v83', 'make_rough_world_v52.py')

FLOOR_H, FLOORS, PLINTH = 2.8, 5, 0.5
ARCH_H = 4.0                                 # v10 §4: arches >= 4 m clear
GATE_MIN = 4.0                               # v10 §4: gates >= 4 m
BOX_W, BOX_D = 40.0, 33.0                    # v10 §7.4 football box, east edge on the plan, gaps shop-box ~6, box-H13 ~8
ROAD_W = 6.4                                 # drawn ring asphalt (32 SVG units) = v10 §6 rural asphalt
LAMP_STEP = 30.0                             # v10 §8: 25-35 m along the outer road
CAR = (4.0, 1.6, 1.45)
FACING = {'E': 0, 'N': 90, 'W': 180, 'S': 270}
TRACK_W = {'T0': 4.5, 'T1': 4.0, 'T2': 3.5, 'T3': 3.5, 'T4': 3.5, 'T5': 4.0, 'T6': 3.5, 'T7': 4.0}
TRACK_NAME = {'T0': 'W-E through drive, stepped through A4 and A5 (main)', 'T1': 'from the south road at the box to the W-E drive',
              'T2': 'to base 3 (van spot)', 'T3': 'into yard 9', 'T4': 'between the upper houses and H7 (to coop 7 / H8)',
              'T5': 'left passage -> in front of the 12 garages at the north fence -> KPP road', 'T6': 'into yard 12 from the south',
              'T7': 'KPP road (asphalt end) -> north drive'}
FIXES, QUESTIONS = [], []


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


# ---------------------------------------------------------------- transform chain plan metres -> world v85
def load_chain(svg):
    src, wsrc = read(PLAN_PY), read(WORLD_PY)
    plan = json.loads(read(PLAN_JSON))
    S8, CX, CY, OX, OY = [float(v) for v in re.search(r'\nS, CX, CY, OX, OY = ([^#\n]+)', src).group(1).split(',')]
    M = float(plan['px_to_m'])
    T = lambda x, y: (CX + S8 * (x - CX) + OX, CY + S8 * (y - CY) + OY)
    ox, oy = T(*[float(v) for v in re.search(r'OXm, OYm = T\((\d+), (\d+)\)', src).groups()])
    k = float(re.search(r'\nM = ([\d.]+)', wsrc).group(1)) * float(re.search(r'k = M \* (\d+(?:\.\d+)?)', wsrc).group(1))
    pw, ph = Image.open(PLAN_PNG).size
    tag = [(at, Mx) for nm, at, Mx, g, a, b in svg_tags(svg) if nm == 'image' and 'rough_v52_world' in (attr(at, 'href') or '')]
    assert len(tag) == 1, 'rough_v52_world <image> not found once in the master SVG'
    at, Mx = tag[0]
    ix, iy, iw, ih = num(at, 'x'), num(at, 'y'), num(at, 'width'), num(at, 'height')
    assert (int(iw), int(ih)) == (int(pw * k), int(ph * k)), 'image size in the SVG != resized plan'

    def P(x, z):
        px, py = x / M + ox, oy - z / M
        return u2w(*apply(Mx, (ix + px * iw / pw, iy + py * ih / ph)))
    a0, a1, c0, c1 = P(0, 100)[0], P(100, 100)[0], P(100, 50)[1], P(100, 150)[1]
    lin = (a0, (a1 - a0) / 100.0, c0 - 50 * (c1 - c0) / 100.0, (c1 - c0) / 100.0)   # rigid part (z > 1 m): x_w = a + b x, y_w = c + d z

    def Pinv(xw, yw):
        return ((xw - lin[0]) / lin[1], (yw - lin[2]) / lin[3])
    info = {'M': M, 'origin_px': (ox, oy), 'k': k, 'plan_px': (pw, ph), 'img': (ix, iy, iw, ih), 'lin': lin}
    return P, Pinv, info, plan, T


def plan_model():
    """HOUSES / BLOCKS of build_rough_v52.py (model part only: v52 spread, +4 % bodies, deltas) + LAWN_D, DISTRICT."""
    src = read(PLAN_PY)
    a = src.index('\nS, CX, CY, OX, OY =') + 1
    b = src.index('# ================================================================ земля района')
    body = '\n'.join(ln for ln in src[a:b].split('\n') if not re.match(r'^(F|img|dr|rnd) = ', ln))
    ns = {'math': math, 'random': random}
    exec(body, ns)
    ns['LAWN_D'] = float(re.search(r'BAND, LAWN_D, DOORBAND = (\d+), (\d+), (\d+)', src).group(2))
    ns['DISTRICT'] = eval(re.search(r'\nDISTRICT = (\[[^\]]+\])', src).group(1))
    return ns


# ---------------------------------------------------------------- small geometry (local plan metres)
def rpoly(r):
    x0, z0, x1, z1 = r
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def rdist(p, r):
    return math.hypot(max(r[0] - p[0], 0.0, p[0] - r[2]), max(r[1] - p[1], 0.0, p[1] - r[3]))


def rinter(a, b, pad=0.0):
    return a[0] < b[2] + pad and b[0] < a[2] + pad and a[1] < b[3] + pad and b[1] < a[3] + pad


def grow(r, gx, gz=None):
    gz = gx if gz is None else gz
    return (r[0] - gx, r[1] - gz, r[2] + gx, r[3] + gz)


def rcen(r):
    return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)


def seg_d(p, a, b):
    vx, vz = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vz * vz or 1e-9
    t = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vz) / L2))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vz)


def line_d(p, pl):
    return min(seg_d(p, a, b) for a, b in zip(pl[:-1], pl[1:]))


def samples(pl, step=0.5):
    out = []
    for a, b in zip(pl[:-1], pl[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / step))
        out += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]
    return out


def buffer_line(pl, w, cap=True):
    """Miter buffer of a polyline (half width w) as a CCW polygon; ends extended by w when cap."""
    pts = [tuple(map(float, p)) for p in pl]

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


def ellipse(c, rx, rz, n=20):
    return [(c[0] + rx * math.cos(2 * math.pi * i / n), c[1] + rz * math.sin(2 * math.pi * i / n)) for i in range(n)]


def fix(where, ru, why):
    FIXES.append({'id': 'rough-%02d' % (len(FIXES) + 1), 'where_local': where, 'ru': ru, 'why_ru': why})


def question(ru, options, default, applied):
    QUESTIONS.append({'id': 'rough-q%d' % (len(QUESTIONS) + 1), 'ru': ru, 'options_ru': options, 'default': default, 'applied': applied})


# ---------------------------------------------------------------- master SVG: drawn world objects around the Rough
def svg_world(svg):
    out = {'roads': [], 'ring': None, 'kpp': [], 'border': [], 'towers': []}
    for nm, at, M, gids, a, b in svg_tags(svg):
        if nm not in ('polyline', 'polygon'):
            continue
        st, fl = attr(at, 'stroke'), attr(at, 'fill')
        pts = [u2w(*p) for p in points_of(at, M)]
        if not pts:
            continue
        if 'R85_rough_ring' in gids and st == '#5F666C':
            out['ring'] = pts
        elif 'R24_roads' in gids and st == '#5F666C':
            out['roads'].append(pts)
        elif 'R69_checkpoint' in gids:
            out['kpp'].append((nm, st, fl, num(at, 'stroke-width'), pts))
        elif 'R60_mountain_ext' in gids and nm == 'polyline' and st == '#7A7F82':
            out['border'].append(pts)
        elif 'R60_mountain_ext' in gids and nm == 'polygon' and fl == '#8A7A5E':
            out['towers'].append(pts)
    assert out['ring'] and len(out['border']) == 2 and len(out['towers']) == 2, 'master SVG v85 layout changed'
    return out


def road_starting(roads, p, tol=1.0, end=0):
    for pl in roads:
        q = pl[end]
        if math.hypot(q[0] - p[0], q[1] - p[1]) < tol:
            return pl
    raise SystemExit('road at %s not found in R24_roads' % (p,))


# ---------------------------------------------------------------- build
def build():
    svg = svg_text()
    P, Pinv, info, plan, T = load_chain(svg)
    ns = plan_model()
    M, LAWN = info['M'], ns['LAWN_D'] * info['M']
    OXm, OYm = info['origin_px']
    Pm = lambda x, y: ((x - OXm) * M, (OYm - y) * M)                       # plan px -> plan metres

    def Rm(r):
        a_, b_ = Pm(r[0], r[3]), Pm(r[2], r[1])
        return (a_[0], a_[1], b_[0], b_[1])
    W = lambda p: rnd2(P(p[0], p[1]))
    WR = lambda r: [W(q) for q in rpoly(r)]
    WL = lambda pl: [W(q) for q in pl]
    world = svg_world(svg)
    HM = ns['HOUSES']

    # ------------------------------------------------ houses (parts exactly as the JSON; the exec'd model is cross-checked)
    parts = []                                                             # (bid, hid, k, rect)
    err = 0.0
    for h in plan['houses']:
        for k, p in enumerate(h['parts']):
            r = (p['x0'], p['z0'], p['x1'], p['z1'])
            q = Rm(HM[h['id']]['C'][k])
            err = max(err, max(abs(a_ - b_) for a_, b_ in zip(r, q)))
            parts.append(('04-%s%s' % (h['id'], 'abcdefgh'[k] if len(h['parts']) > 1 else ''), h['id'], k, r))
    assert err < 0.02, 'build_rough_v52 model and Планировка_v52.json disagree (%.3f m)' % err
    pr = {b: r for b, _, _, r in parts}
    names = {h['id']: h['name'] for h in plan['houses']}

    # ------------------------------------------------ arches: inside a part (N-S cut) or a bridge block between two parts (W-E)
    arches = []
    for a in plan['arches']:
        a = dict(a, id=a['id'].replace(chr(0x410), 'A'))                  # Cyrillic А1..А6 of the plan -> Latin ids A1..A6
        r = (a['rect']['x0'], a['rect']['z0'], a['rect']['x1'], a['rect']['z1'])
        c = rcen(r)
        host = [b for b, _, _, q in parts if q[0] - 0.05 <= c[0] <= q[2] + 0.05 and q[1] - 0.05 <= c[1] <= q[3] + 0.05]
        if host:
            q = pr[host[0]]
            if r[1] > q[1] + 0.05 or r[3] < q[3] - 0.05:                       # arch must cut the whole depth (A3 does not on the plan)
                fix(c, 'Арка %s продлена на всю глубину корпуса: z %.1f…%.1f -> %.1f…%.1f м плана (на картинке штриховка кончается в %.1f м от северного фасада)'
                    % (a['id'], r[1], r[3], q[1], q[3], q[3] - r[3]),
                    'иначе арка глухая: со стороны двора за ней стена, а с северной стороны газон палисадника уже убран под проезд — проход задуман сквозным')
                r = (r[0], q[1], r[2], q[3])
            arches.append({'id': a['id'], 'host': host[0], 'rect': r, 'through': 'N-S', 'clear_w': r[2] - r[0]})
        else:
            arches.append({'id': a['id'], 'host': None, 'rect': r, 'through': 'W-E', 'clear_w': r[3] - r[1]})
            if a['through'] != 'W-E':
                fix(c, 'Арка %s — проезд запад–восток (в JSON плана помечено «%s»): это перемычка-мост 5 этажей над разрывом %.1f м между торцами двух корпусов'
                    % (a['id'], a['through'], r[3] - r[1]),
                    'через неё идёт сквозной проезд запад–восток (v10 §7.4); пометка «N-S» — автоматическая по ширине прямоугольника на плане')
    arch_by_host = {}
    for a in arches:
        arch_by_host.setdefault(a['host'], []).append(a)

    # ------------------------------------------------ palisades (front gardens) from the plan model, minus arch passages
    pals = []                                                             # dict(bid, side, rect, skip)
    for hid, h in HM.items():
        for side, ci, a_, b_, n, skip in h['doors']:
            x0, y0, x1, y1 = h['C'][ci]
            dx, dy = h['d']
            if side in 'SN':
                a2, b2 = a_ + dx, b_ + dx
                rr = [a2, y1, b2, y1 + ns['LAWN_D']] if side == 'S' else [a2, y0 - ns['LAWN_D'], b2, y0]
            else:
                a2, b2 = a_ + dy, b_ + dy
                rr = [x1, a2, x1 + ns['LAWN_D'], b2] if side == 'E' else [x0 - ns['LAWN_D'], a2, x0, b2]
            bid = '04-%s%s' % (hid, 'abcdefgh'[ci] if len(h['C']) > 1 else '')
            sk = None
            if skip:
                sk = (Pm(skip[0] + dx, 0)[0], Pm(skip[1] + dx, 0)[0])
            pals.append({'bid': bid, 'side': side, 'rect': Rm(rr), 'skip': sk})
    pal_pieces = []
    for p in pals:
        r = p['rect']
        if p['skip']:
            pal_pieces += [(r[0], r[1], p['skip'][0], r[3]), (p['skip'][1], r[1], r[2], r[3])]
        else:
            pal_pieces.append(r)

    # ------------------------------------------------ doors -> podyezds (+ path through the palisade)
    doors = []
    for i, dr in enumerate(plan['doors']):
        x, z = dr['pos']
        sd = dr['side']
        host = None
        for b, _, _, q in parts:
            on = {'S': abs(z - q[1]) < 0.05, 'N': abs(z - q[3]) < 0.05, 'E': abs(x - q[2]) < 0.05, 'W': abs(x - q[0]) < 0.05}[sd]
            inr = q[0] - 0.05 <= x <= q[2] + 0.05 if sd in 'SN' else q[1] - 0.05 <= z <= q[3] + 0.05
            if on and inr:
                host = b
                break
        assert host, 'door %d not on a facade' % i
        doors.append({'i': i, 'host': host, 'side': sd, 'pos': [x, z], 'benches': dr['benches']})

    def path_rect(d):
        x, z = d['pos']
        return {'S': (x - 1.6, z - LAWN, x + 1.6, z), 'N': (x - 1.6, z, x + 1.6, z + LAWN),
                'E': (x, z - 1.6, x + LAWN, z + 1.6), 'W': (x - LAWN, z - 1.6, x, z + 1.6)}[d['side']]
    for d in doors:                                                       # a door path must not run into another wing
        for b, _, _, q in parts:
            if b == d['host']:
                continue
            pth = path_rect(d)
            if rinter(pth, q, -0.01):
                old = list(d['pos'])
                if d['side'] in 'SN':
                    d['pos'][0] = (q[0] - 1.6 - 1.3) if d['pos'][0] < rcen(q)[0] else (q[2] + 1.6 + 1.3)
                else:
                    d['pos'][1] = (q[1] - 1.6 - 1.3) if d['pos'][1] < rcen(q)[1] else (q[3] + 1.6 + 1.3)
                fix(tuple(d['pos']), 'Подъезд %s (дверь %d) сдвинут вдоль фасада с %.2f на %.2f м плана — из внутреннего угла П-дома'
                    % (d['host'], d['i'], old[0] if d['side'] in 'SN' else old[1], d['pos'][0] if d['side'] in 'SN' else d['pos'][1]),
                    'на плане дверь в %.1f м от стены соседнего крыла: козырёк, ступени и дорожка через палисадник упираются в стену %s'
                    % (abs((old[0] if d['side'] in 'SN' else old[1]) - (q[0] if d['side'] in 'SN' else q[1])), b))

    # ------------------------------------------------ garages (58) by groups
    def ggroup(r):
        if r[1] > 220:
            return 'GN'
        if r[0] > 290:
            return 'GNE'
        if r[2] < 75 and r[3] < 55:
            return 'GB'
        return 'G7'
    garages = [{'rect': (g['rect']['x0'], g['rect']['z0'], g['rect']['x1'], g['rect']['z1']), 'gate': g['gate'],
                'group': ggroup((g['rect']['x0'], g['rect']['z0'], g['rect']['x1'], g['rect']['z1']))} for g in plan['garages']]

    # ------------------------------------------------ shop, kiosks, booths, club, base, box, playgrounds, trash, squares
    shop = (plan['shop']['x0'], plan['shop']['z0'], plan['shop']['x1'], plan['shop']['z1'])
    dShop = ns['delta']((1176, 1622, 1404, 1703))
    kiosks = [Rm(ns['mv']((1176, 1630, 1204, 1696), dShop)), Rm(ns['mv']((1376, 1630, 1404, 1696), dShop))]
    booths = [(b['x0'], b['z0'], b['x1'], b['z1']) for b in plan['booths']]
    dE = HM['E']['d']
    club = (plan['club']['x0'], plan['club']['z0'], plan['club']['x1'], plan['club']['z1'])
    e3 = pr['04-Ed']
    if club[0] < e3[0]:
        club = (e3[0], club[1], club[2], club[3])                             # the drawn club outline sticks 0.4 m out of the wall
    canopy = Rm(ns['mv']((2034, 1320, 2051, 1382), dE))
    smokers = Rm(ns['mv']((1940, 1300, 2028, 1402), dE))
    gate = (plan['base_gate']['x0'], plan['base_gate']['z0'], plan['base_gate']['x1'], plan['base_gate']['z1'])
    if gate[2] - gate[0] < GATE_MIN:
        c = rcen(gate)
        fix(c, 'Ворота гаража базы 3 в Г-доме H17: проём %.2f -> %.1f м (ось та же)' % (gate[2] - gate[0], GATE_MIN),
            'v10 §4: ворота и арки — проём не меньше 4 м; на плане 3,84 м')
        gate = (c[0] - GATE_MIN / 2, gate[1], c[0] + GATE_MIN / 2, gate[3])
    van = (plan['bus']['x0'], plan['bus']['z0'], plan['bus']['x1'], plan['bus']['z1'])
    b0 = (plan['box']['x0'], plan['box']['z0'], plan['box']['x1'], plan['box']['z1'])
    h13 = pr['04-H13']
    free = h13[1] - shop[3]
    gap_s = (free - BOX_D) * 6.0 / 14.0                                   # 6 : 8 split of what is left (v10: ~6 and ~8)
    box = (b0[2] - BOX_W, shop[3] + gap_s, b0[2], shop[3] + gap_s + BOX_D)
    fix(rcen(box), 'Футбольная коробка %.1f x %.1f м (на плане нарисована %.1f x %.1f), восточный край на месте; зазоры магазин–коробка %.1f м, коробка–H13 %.1f м'
        % (BOX_W, BOX_D, b0[2] - b0[0], b0[3] - b0[1], box[1] - shop[3], h13[1] - box[3]),
        'v10 §7.4: коробка 40 x 33, зазоры ~6 и ~8 м; в плане v51/52 размер посчитан с лишним множителем 1,08 (37 x 30,6 м в метрах плана)')
    plays = [(p['name'], (p['rect']['x0'], p['rect']['z0'], p['rect']['x1'], p['rect']['z1'])) for p in plan['playgrounds']]
    trashes = [(t['name'], (t['rect']['x0'], t['rect']['z0'], t['rect']['x1'], t['rect']['z1']), t['open']) for t in plan['trash']]
    squares = []
    for (sx, sy, rx, ry), nm in (((1035, 1395, 34, 70), 'mini-square at the box (H14)'), ((2300, 1500, 70, 50), 'mini-square of yard 13')):
        squares.append((nm, Pm(*T(sx, sy)), rx * M, ry * M))
    pockets = [Pm(*T(*p)) for p in ((860, 690), (1440, 955), (2330, 470), (395, 1375), (870, 40))]

    # ------------------------------------------------ roads: v85 drawn ring + hook, plan east leg, exits, KPP road
    ring = world['ring']
    hook = road_starting(world['roads'], (686.0, 788.0))                  # ROAD_RING of build_world_v85: entry -> west side of the ring
    hz_drawn = Pinv(*hook[0])[1]
    pal_h3 = [p for p in pals if p['bid'] == '04-H3'][0]['rect']
    hz = min(hz_drawn, pal_h3[1] - 1.3 - ROAD_W / 2)
    if hz < hz_drawn - 0.05:
        fix((10.0, hz), 'Асфальтовый заезд с западной стороны кольца (в начало сквозного проезда) сдвинут на %.1f м южнее: ось y %.1f -> %.1f мира'
            % (hz_drawn - hz, hook[0][1], P(0, hz)[1]),
            'на карте v85 асфальт шириной 6,4 м заходит на палисадник дома 10 (H3); теперь 1,3 м до газона')
    west_x = Pinv(*ring[3])[0]                                            # drawn west leg x (local)
    road = [(20.0, hz), (west_x, hz)] + [Pinv(*p) for p in ring if p[1] < 677.5 and p[0] <= 1000.0]
    road = [(round(x, 3), round(z, 3)) for x, z in road]
    xe = plan['outer_road'][2][0]
    ring_xy = [p for p in ring]
    z_e = None
    for a_, b_ in zip(ring_xy[:-1], ring_xy[1:]):
        xa, xb = Pinv(*a_)[0], Pinv(*b_)[0]
        if xa <= xe <= xb:
            t = (xe - xa) / (xb - xa)
            z_e = Pinv(a_[0], a_[1] + (b_[1] - a_[1]) * t)[1]
    east_leg = [(xe, z_e), (xe, plan['outer_road'][3][1])]
    fix((xe, 50.0), 'Восточная сторона внешней дороги «П» (x %.1f м плана, %.0f м асфальта) взята из плана v52 — на карте v85 её нет; сквозной проезд запад–восток выходит на неё'
        % (xe, east_leg[1][1] - z_e),
        'без неё колея запад–восток упирается в угол забора у восточных гаражей (висящий конец, v10 §6); план и легенда v45: асфальт буквой П')
    fence = [tuple(p) for p in plan['fence']]
    if fence[-1][0] < xe + ROAD_W / 2 + 1.0:
        fx = xe + ROAD_W / 2 + 1.2
        fix((fence[-1][0], fence[-1][1]), 'Огрызок забора у юго-восточного угла (z %.1f) укорочен до обочины: x %.1f -> %.1f м плана' % (fence[-1][1], fence[-1][0], fx),
            'на плане он перерезает восточную сторону дороги П (дорога через забор)')
        fence[-1] = (fx, fence[-1][1])
    kpp_road_w = road_starting(world['roads'], (860.0, 896.0))
    kx, kz0 = Pinv(*kpp_road_w[0])
    zf = max(p[1] for p in fence)
    step_i = [i for i in range(1, len(fence)) if abs(fence[i][0] - fence[i - 1][0]) < 0.01 and fence[i][1] < fence[i - 1][1] - 5 and fence[i - 1][1] == zf]
    assert step_i, 'north fence step not found'
    i = step_i[0]
    sx_old = fence[i][0]
    gate_half = ROAD_W / 2 + 0.6
    sx_new = round(kx + gate_half + 0.6, 2)
    if abs(sx_old - kx) < gate_half + 0.5:
        fence[i - 1] = (sx_new, fence[i - 1][1])
        fence[i] = (sx_new, fence[i][1])
        fix((kx, zf), 'Дорога с КПП входит в район через ворота %.1f м в северном заборе; уступ забора сдвинут на %.1f м восточнее (x %.2f -> %.2f м плана), дорога прямая, '
            'внутри короткая колея до проезда у гаражей' % (2 * gate_half, sx_new - sx_old, sx_old, sx_new),
            'на карте v85 ось дороги к КПП идёт ровно по вертикальному уступу забора и обрывается в 9 м внутри — дорога через забор и висящий конец (v10 §6)')
    north_gate = (kx - gate_half, zf, kx + gate_half, zf)
    f_left = fence[:i - 1] + [(north_gate[0], zf)]                     # west side + north side up to the gate
    f_right = [(north_gate[2], zf)] + fence[i - 1:]                    # gate -> moved step -> NE -> E -> stub

    # tracks (plan axes, then the fixes below)
    trk = {('T%d' % k): [tuple(p) for p in pl] for k, pl in enumerate(plan['tracks'])}
    t0 = trk['T0']
    t0[0] = (20.0, hz)                                                    # starts at the end of the asphalt hook
    t0[1] = (t0[1][0], hz)
    trk['T3'][0] = (trk['T3'][0][0], hz)
    w1pal = [p['rect'] for p in pals if p['bid'] == '04-Wb'][0]
    need = w1pal[2] + 0.6 + TRACK_W['T0'] / 2
    for j in range(len(t0)):
        if abs(t0[j][0] - 91.85) < 0.01:
            old = t0[j][0]
            t0[j] = (round(need, 2), t0[j][1])
    fix((need, 114.0), 'Колея запад–восток вдоль восточного фасада W (после арки А4 вниз) сдвинута с x %.2f на %.2f м плана' % (old, need),
        'на плане полоса колеи шириной ~4,5 м заходит на 1,5 м в палисадник корпуса W (газон с заборчиком у подъездов)')
    t5 = trk['T5']
    t5[-1] = (kx, t5[-1][1])                                              # north drive -> KPP road junction
    trk['T7'] = [(kx, t5[-1][1]), (kx, kz0)]

    # ------------------------------------------------ obstacles for checks
    obst = []                                                             # (name, rect)
    for b, hid, k, r in parts:
        cut = [a for a in arch_by_host.get(b, [])]
        if cut:
            a = cut[0]['rect']
            obst += [(b, (r[0], r[1], a[0], r[3])), (b, (a[2], r[1], r[2], r[3]))]
        else:
            obst.append((b, r))
    for j, g in enumerate(garages):
        obst.append(('G%02d' % (j + 1), g['rect']))
    obst += [('shop', shop), ('kiosk1', kiosks[0]), ('kiosk2', kiosks[1]), ('booth1', booths[0]), ('booth2', booths[1]), ('box', box)]
    obst += [('play-' + n, r) for n, r, in plays] + [('trash-' + n, r) for n, r, _ in trashes]
    soft = [('palisade-%s-%s' % (p['bid'], p['side']), r) for p in pals for r in ([(p['rect'][0], p['rect'][1], p['skip'][0], p['rect'][3]),
            (p['skip'][1], p['rect'][1], p['rect'][2], p['rect'][3])] if p['skip'] else [p['rect']])]

    def clearance(pl, hw, skip=()):
        worst = (99.0, None)
        for q in samples(pl, 0.5):
            for n_, r in obst + soft:
                if n_ in skip:
                    continue
                d_ = rdist(q, r) - hw
                if d_ < worst[0]:
                    worst = (d_, n_)
        return worst
    checks = {'tracks': {}}
    for k_, pl in trk.items():
        c_ = clearance(pl, TRACK_W[k_] / 2)
        checks['tracks'][k_] = {'min_clearance_m': round(c_[0], 2), 'nearest': c_[1]}
    road_c = {'ring': clearance([q for q in road if q[1] > 1.0 or q[0] < 300], ROAD_W / 2), 'east_leg': clearance(east_leg, ROAD_W / 2)}

    # ------------------------------------------------ cars (8, plan spots, moved off houses / ruts / arch mouths)
    arch_zone = []
    for a in arches:
        r = a['rect']
        arch_zone.append(grow(r, 0.0, 8.0) if a['through'] == 'N-S' else grow(r, 8.0, 0.0))

    def car_rect(c, ang):
        return grow((c[0], c[1], c[0], c[1]), CAR[0] / 2, CAR[1] / 2) if ang == 0 else grow((c[0], c[1], c[0], c[1]), CAR[1] / 2, CAR[0] / 2)
    hard = obst + soft + [('path', path_rect(d)) for d in doors] + [('van', van)]

    def car_problem(c, ang):
        cr = car_rect(c, ang)
        for n_, r in hard:
            if rinter(cr, r, 0.15):
                return 'в ' + n_
        for k_, pl in trk.items():
            if min(rdist(q, cr) for q in samples(pl, 0.5)) < TRACK_W[k_] / 2 + 0.1:
                return 'на колее ' + k_
        if min(rdist(q, cr) for q in samples(road + east_leg, 0.5)) < ROAD_W / 2 + 1.0:
            return 'на тротуаре внешней дороги'
        for r in arch_zone:
            if rinter(cr, r):
                return 'перед въездом в арку'
        return None
    cars = []
    moves = {7: ('за домом у коробки H13 (с северной стороны, 2 м от стены)', lambda c: (c[0], h13[3] + 2.0 + CAR[1] / 2)),
             4: ('у глухой северной стены H56, а не на колее у гаражей', lambda c: (c[0], pr['04-H56a'][3] + 1.6 + CAR[1] / 2)),
             0: ('вдоль колеи у дома 10 восточнее арки А1, а не перед её въездом', lambda c: (arches[0]['rect'][2] + 5.0, pal_h3[1] - 0.35 - CAR[1] / 2)),
             3: ('в кармане перед магазином, а не на тротуаре у бордюра', lambda c: (c[0], ROAD_W / 2 + 1.5 + 0.3 + CAR[1] / 2))}
    for j, cr in enumerate(plan['cars']):
        c = tuple(cr['pos'])
        ang = 0 if cr['along'] == 'W-E' else 90
        why = car_problem(c, ang)
        if why and j in moves:
            txt, fn = moves[j]
            c2 = fn(c)
            why2 = car_problem(c2, ang)
            assert not why2, 'car %d fix still bad: %s' % (j, why2)
            fix(c2, 'Машина %d переставлена %s (было x %.1f, z %.1f м плана: %s)' % (j + 1, txt, c[0], c[1], why),
                'машины стоят ровно и логично, не в домах, не на колеях и не у въезда в арку (v10 §8)')
            c = c2
        elif why:
            raise SystemExit('car %d: %s' % (j, why))
        cars.append((c, ang))

    # ------------------------------------------------ lamps by rule (ROUGH_LEGEND §1.6): house corners on podyezd sides, playgrounds, box, outer road
    cand = []
    for p in pals:
        q = pr[p['bid']]
        o = 14 * M
        e = 12 * M
        long_ = (q[2] - q[0] if p['side'] in 'SN' else q[3] - q[1]) > 260 * M
        if p['side'] in 'SN':
            zz = q[1] - o if p['side'] == 'S' else q[3] + o
            cand += ([((q[0] - e, zz), 'house corner')] if long_ else []) + [((q[2] + e, zz), 'house corner')]
        else:
            xx = q[2] + o if p['side'] == 'E' else q[0] - o
            cand += ([((xx, q[3] + e), 'house corner')] if long_ else []) + [((xx, q[1] - e), 'house corner')]
    for n_, r in plays:
        cand += [((x_, z_), 'playground corner') for x_ in (r[0] - 10 * M, r[2] + 10 * M) for z_ in (r[1] - 10 * M, r[3] + 10 * M)]
    cand += [((x_, box[1] - 10 * M), 'box corner') for x_ in (box[0] - 10 * M, box[2] + 10 * M)]
    off = ROAD_W / 2 + 1.5
    for a_, b_, nrm in (((west_x, hz - 3.0), (west_x, 8.0), (1, 0)), ((8.0, 0.0), (xe - 8.0, 0.0), (0, 1)), ((xe, 8.0), (xe, east_leg[1][1] - 3.0), (-1, 0))):
        L = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
        n = max(1, int(round(L / LAMP_STEP)))
        for s in range(n + 1):
            t = s / n
            cand.append(((a_[0] + (b_[0] - a_[0]) * t + nrm[0] * off, a_[1] + (b_[1] - a_[1]) * t + nrm[1] * off), 'outer road'))
    lamps, dropped = [], {}
    car_r = [car_rect(c, a) for c, a in cars]
    juncs = [trk[k_][0] for k_ in ('T1', 'T2')] + [(Pinv(748.0, 671.0)[0], 0.0), (Pinv(945.0, 671.0)[0], 0.0), (west_x, hz), (xe, z_e), (xe, east_leg[1][1])]
    for (q, why) in cand:
        bad = None
        if any(rdist(q, r) < 0.4 for n_, r in obst if not n_.startswith('play')):
            bad = 'building/garage'
        elif any(line_d(q, pl) < TRACK_W[k_] / 2 + 1.0 for k_, pl in trk.items()):
            bad = 'track'
        elif why != 'outer road' and line_d(q, road + east_leg) < ROAD_W / 2 + 1.0:
            bad = 'road'
        elif any(rdist(q, grow(path_rect(d), 0.4)) == 0 for d in doors) or rdist(q, grow(van, 1.0)) == 0:
            bad = 'path/van'
        elif any(rdist(q, r) == 0 for r in arch_zone):
            bad = 'arch mouth'
        elif any(rdist(q, grow(r, 1.0)) == 0 for r in car_r):
            bad = 'car'
        elif why == 'outer road' and any(math.hypot(q[0] - j[0], q[1] - j[1]) < 9.0 for j in juncs):
            bad = 'junction'
        elif any(math.hypot(q[0] - l_[0][0], q[1] - l_[0][1]) < 3.0 for l_ in lamps):
            bad = 'duplicate'
        if bad:
            dropped[bad] = dropped.get(bad, 0) + 1
        else:
            lamps.append((q, why))
    fix((rcen(box)[0], box[3] + 2.0), 'Фонари у северных углов коробки не ставятся (у южных углов — да)',
        'северная сторона коробки — подъезд бусика к калитке (полоса между коробкой и палисадником H13), фонарь там мешает проезду')

    # ------------------------------------------------ assemble JSON
    blds, props, zones = [], [], []
    soc = {'balconies': 'mixed', 'windows': True, 'fire_escape': False, 'ac_units': 0, 'water_tank': False, 'awning': False,
           'storefront': False, 'ridge_cap': None, 'satellite_dishes': True, 'gas_pipe_on_facade': True, 'drainpipes': True,
           'balcony_collider': 'solid, not walkable'}
    roof5 = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.6}
    kh_note = ('5-storey grey panel khrushchevka, ONE texture KH1b for all, shabby (streaks, damp spots, patched seams, rust under balconies, '
               'dark splashed plinth); 3D balconies mixed glazed/open with junk, solid collider; no basements, no interiors')

    def ent_of(d):
        x, z = d['pos']
        pth = path_rect(d)
        return {'pos': W((x, z)), 'facing_deg': FACING[d['side']], 'kind': 'podyezd', 'w_m': 1.2, 'benches': d['benches'],
                'urn': d['benches'] > 0, 'path': {'poly': WR(pth), 'surface': 'concrete_SK3c', 'w_m': 3.2},
                'kit': {'canopy': 'concrete', 'door': 'iron_intercom', 'steps': 3}, 'plan_door': d['i']}
    groups = {}
    for b, hid, k, r in parts:
        ents = [ent_of(d) for d in doors if d['host'] == b]
        arc = []
        for a in arch_by_host.get(b, []):
            ar = a['rect']
            arc.append({'id': a['id'], 'rect': WR(ar), 'through': a['through'], 'clear_w_m': round(a['clear_w'], 2), 'clear_h_m': ARCH_H,
                        'floors_above': 'from %.1f m: floors continue above the arch' % ARCH_H})
            ents.append({'pos': W(rcen(ar)), 'facing_deg': 90, 'kind': 'arch', 'w_m': round(a['clear_w'], 2), 'through': a['through'], 'arch_id': a['id']})
        if b == '04-H17b':
            ents.append({'pos': W((rcen(gate)[0], gate[3] - (gate[3] - pr[b][3]))), 'facing_deg': 90, 'kind': 'garage_gate', 'w_m': round(gate[2] - gate[0], 2),
                         'notes': 'BASE 3: van garage in the ground floor of the L-house H17, iron gate; van spot (yard 2) in front'})
        if b == '04-Ed':
            ents.append({'pos': W((club[0], rcen(canopy)[1])), 'facing_deg': 180, 'kind': 'door', 'w_m': 1.6,
                         'notes': 'club / den 5 ("притон"): canopy, neon heart sign WITHOUT words, bouncer, smokers corner in front'})
        nb = {'id': b, 'group': hid, 'name_ru': names[hid], 'kind': 'khrushchevka', 'material_slot': 'rough_khrushchevka',
              'footprint': WR(r), 'floors': FLOORS, 'floor_h_m': FLOOR_H, 'height_m': FLOORS * FLOOR_H + PLINTH, 'roof': dict(roof5),
              'walls': 'KH1b', 'tint': None, 'entrances': ents, 'arches': arc, 'facade_kit': 'rough', 'sockets': dict(soc),
              'collider': 'full_roof', 'disabled': False, 'notes': kh_note}
        if b == '04-Ed':
            nb['ground_floor_use'] = {'kind': 'club', 'rect': WR(club)}
        if b == '04-H17b':
            nb['ground_floor_use'] = {'kind': 'base3_garage', 'gate_rect': WR(gate)}
        blds.append(nb)
        groups.setdefault(hid, []).append(b)
    for a in arches:
        if a['host']:
            continue
        hid = [h for h, bs in groups.items() if any(abs(pr[b_][0] - a['rect'][0]) < 6 and (abs(pr[b_][1] - a['rect'][3]) < 0.05 or abs(pr[b_][3] - a['rect'][1]) < 0.05) for b_ in bs)][0]
        bid = '04-%s-%s' % (hid, a['id'])
        ar = a['rect']
        blds.append({'id': bid, 'group': hid, 'name_ru': names[hid] + ' — перемычка над аркой %s' % a['id'], 'kind': 'khrushchevka_arch_bridge',
                     'material_slot': 'rough_khrushchevka', 'footprint': WR(ar), 'floors': FLOORS, 'floor_h_m': FLOOR_H,
                     'height_m': FLOORS * FLOOR_H + PLINTH, 'roof': dict(roof5), 'walls': 'KH1b', 'tint': None,
                     'entrances': [{'pos': W(rcen(ar)), 'facing_deg': 0, 'kind': 'arch', 'w_m': round(a['clear_w'], 2), 'through': 'W-E', 'arch_id': a['id']}],
                     'arches': [{'id': a['id'], 'rect': WR(ar), 'through': 'W-E', 'clear_w_m': round(a['clear_w'], 2), 'clear_h_m': ARCH_H,
                                 'floors_above': 'ground floor open over the whole gap between the two end walls; floors continue above %.1f m' % ARCH_H}],
                     'facade_kit': 'rough', 'sockets': dict(soc), 'collider': 'full_roof', 'disabled': False,
                     'notes': 'bridge block %.1f m deep spanning the %.1f m gap between two wings of %s; the W-E through drive passes under it' % (ar[2] - ar[0], ar[3] - ar[1], hid)})
    graffiti = set(sorted(range(len(garages)), key=lambda j: h01('graffiti%d' % j))[:14])
    open_junk = set(sorted([j for j, g in enumerate(garages) if g['group'] in ('G7', 'GNE')], key=lambda j: h01('junk%d' % j))[:2])
    for j, g in enumerate(garages):
        r = g['rect']
        c = rcen(r)
        gp = {'S': (c[0], r[1]), 'N': (c[0], r[3]), 'E': (r[2], c[1]), 'W': (r[0], c[1])}[g['gate']]
        blds.append({'id': '04-G%02d' % (j + 1), 'group': g['group'], 'kind': 'garage', 'material_slot': 'rough_garage', 'footprint': WR(r),
                     'floors': 1, 'floor_h_m': 2.6, 'height_m': 2.6, 'roof': {'type': 'flat', 'material': 'metal_rusty', 'parapet_h_m': 0.0},
                     'walls': 'metal_rusty', 'tint': None,
                     'entrances': [{'pos': W(gp), 'facing_deg': FACING[g['gate']], 'kind': 'garage_gate', 'w_m': 2.6,
                                    'state': 'open_with_junk' if j in open_junk else 'closed'}],
                     'facade_kit': 'none', 'sockets': {'balconies': 'none', 'windows': False, 'graffiti': j in graffiti}, 'collider': 'full_roof',
                     'disabled': False, 'notes': {'GN': 'row of 12 at the north fence, gates south (v50/v52)', 'G7': 'cooperative 7: 2 rows of 8 gates facing + 2 + 2',
                                                  'GNE': 'NE block at yard 12: 9 + 9 facing + 1', 'GB': 'base 3 cover: 5 + 2 (L) around the van spot'}[g['group']]
                     + '; rusty, peeling paint of different colours'})
    blds.append({'id': '04-shop24', 'kind': 'shop', 'material_slot': 'rough_shop', 'footprint': WR(shop), 'floors': 1, 'floor_h_m': 3.2, 'height_m': 3.6,
                 'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.4}, 'walls': 'stucco_SK3b', 'tint': '#D7A792',
                 'entrances': [{'pos': W((rcen(shop)[0], shop[1])), 'facing_deg': 270, 'kind': 'door', 'w_m': 1.4, 'notes': 'drunks at the door'}],
                 'facade_kit': 'none', 'sockets': {'windows': True, 'storefront': True, 'awning': False, 'sign': '24 ЧАСА (no brand)'},
                 'collider': 'full_roof', 'disabled': False, 'notes': 'shop 24 h (3), ~20 x 10 m, two kiosks at the sides; tint = plan colour'})
    fix((rcen(shop)[0], shop[1]), 'Дверь магазина 24 ч — на южном фасаде, к внешней дороге (на плане двери нет)',
        'покупатели и алкаши у входа — со стороны дороги; север занят зазором 6 м до коробки')
    for j, kq in enumerate(kiosks):
        blds.append({'id': '04-kiosk%d' % (j + 1), 'kind': 'kiosk', 'material_slot': 'rough_shop', 'footprint': WR(kq), 'floors': 1, 'floor_h_m': 2.6,
                     'height_m': 2.6, 'roof': {'type': 'flat', 'material': 'metal_painted_SK6a'}, 'walls': 'metal_painted_SK6a', 'tint': None,
                     'entrances': [{'pos': W((rcen(kq)[0], kq[1])), 'facing_deg': 270, 'kind': 'rollshutter', 'w_m': 1.8}], 'facade_kit': 'none',
                     'sockets': {'windows': True}, 'collider': 'full_roof', 'disabled': False, 'notes': 'kiosk next to the shop (plan: drawn as a small garage)'})
    for j, bq in enumerate(booths):
        blds.append({'id': '04-transformer%d' % (j + 1), 'kind': 'transformer_booth', 'material_slot': 'generic_concrete', 'footprint': WR(bq),
                     'floors': 1, 'floor_h_m': 3.0, 'height_m': 3.0, 'roof': {'type': 'flat', 'material': 'roof_flat_SK4d'}, 'walls': 'brick_SK3a',
                     'tint': None, 'entrances': [], 'facade_kit': 'none', 'sockets': {'sign': 'do not enter (pictogram)'}, 'collider': 'full_roof',
                     'disabled': False, 'notes': 'brick transformer booth, "не влезай" pictogram, no wires'})
    # KPP (v85 R69_checkpoint) — on the country border, north of the district fence
    kpp = [k_ for k_ in world['kpp'] if k_[0] == 'polygon' and k_[2] == '#EEEEE8'][0][4]
    gate_k = [k_ for k_ in world['kpp'] if k_[0] == 'polygon' and k_[2] == '#8E9497' and k_[3] == 2.5][0][4]
    rail = [k_ for k_ in world['kpp'] if k_[0] == 'polygon' and k_[2] == '#8E9497' and k_[3] == 1.2][0][4]
    btn = [k_ for k_ in world['kpp'] if k_[0] == 'polygon' and k_[2] == '#D9DBD5'][0][4]
    blds.append({'id': '04-KPP', 'kind': 'border_control', 'material_slot': 'generic_concrete', 'footprint': [rnd2(p) for p in kpp],
                 'floors': 1, 'floor_h_m': 3.4, 'height_m': 3.8, 'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.4},
                 'walls': 'concrete_panel_SK3c', 'tint': None,
                 'entrances': [{'pos': rnd2(((kpp[1][0] + kpp[2][0]) / 2, (kpp[1][1] + kpp[2][1]) / 2)), 'facing_deg': 0, 'kind': 'door', 'w_m': 1.2}],
                 'facade_kit': 'none', 'sockets': {'windows': True, 'flag_on_roof': True}, 'collider': 'full_roof', 'disabled': False,
                 'scope': 'north_border', 'notes': 'border control, one storey, built into the border fence line, flag on the roof (v02 §8.4, canon); from the v85 master SVG'})
    gk = (min(p[0] for p in gate_k), min(p[1] for p in gate_k), max(p[0] for p in gate_k), max(p[1] for p in gate_k))
    props.append({'id': '04-KPP-gate', 'kind': 'sliding_gate_steel', 'pos': rnd2(rcen(gk)), 'rot_deg': 0, 'size': [round(gk[2] - gk[0], 2), 0.4, 3.2],
                  'grip_anchor': False, 'scope': 'north_border', 'material': 'metal_painted_SK6a',
                  'notes': 'ONE mighty steel sliding gate from the KPP wall across the road, red-white stripes, ribs, guide rail to the east; no barriers'})
    rk = (min(p[0] for p in rail), min(p[1] for p in rail), max(p[0] for p in rail), max(p[1] for p in rail))
    props.append({'id': '04-KPP-rail', 'kind': 'gate_guide_rail', 'pos': rnd2(rcen(rk)), 'rot_deg': 0, 'size': [round(rk[2] - rk[0], 2), 0.3, 0.6],
                  'grip_anchor': False, 'scope': 'north_border'})
    props.append({'id': '04-KPP-button', 'kind': 'leave_country_button', 'pos': rnd2(rcen((min(p[0] for p in btn), min(p[1] for p in btn), max(p[0] for p in btn), max(p[1] for p in btn)))),
                  'rot_deg': 270, 'size': [0.4, 0.3, 1.3], 'grip_anchor': False, 'scope': 'north_border',
                  'notes': '"Leave the country" -> "Нет, страну покинуть нельзя: введено военное положение", van turned back (canon)'})
    for j, tw in enumerate(world['towers']):
        props.append({'id': '04-border-tower%d' % (j + 1), 'kind': 'watch_tower', 'pos': rnd2((sum(p[0] for p in tw) / 4, sum(p[1] for p in tw) / 4)),
                      'rot_deg': 0, 'size': [5.0, 5.0, 9.0], 'grip_anchor': False, 'scope': 'north_border'})
    # key props of the plan
    for j, ((ax, az), (bx, bz)) in enumerate(plan['turniks']):
        for pq in pal_pieces:
            if pq[1] <= az <= pq[3] and pq[0] - 0.05 <= ax <= pq[2] + 0.05 and abs(az - bz) < 0.01:
                sh = pq[2] + 1.0 - ax
                fix((ax + sh, az), 'Турник %d сдвинут на %.1f м восточнее (x %.2f…%.2f -> %.2f…%.2f м плана)' % (j + 1, sh, ax, bx, ax + sh, bx + sh),
                    'на плане его западная стойка стоит в палисаднике, в 0,4 м от стены дома H1')
                ax, bx = ax + sh, bx + sh
        props.append({'id': '04-turnik%d' % (j + 1), 'kind': 'pull_up_bar', 'pos': W(((ax + bx) / 2, (az + bz) / 2)), 'rot_deg': 0,
                      'size': [round(math.hypot(bx - ax, bz - az), 2), 0.1, 2.4], 'grip_anchor': True})
    for (n_, (sx, sy), w_, h_) in (('yard12', T(1930, 790), 230, 170), ('yard9', T(440, 395), 160, 120)):
        x0, y0, x1, y1 = sx - w_ / 2, sy - h_ / 2, sx + w_ / 2, sy + h_ / 2
        kit = [('swing_set', (x0 + 16, y0 + 12, x0 + 80, y0 + 34)), ('slide', (x1 - 74, y0 + 16, x1 - 14, y0 + 34)),
               ('sandbox', (sx - 32, y1 - 52, sx + 32, y1 - 12))]
        if w_ > 180:
            kit += [('roundabout', (x0 + 22, y1 - 56, x0 + 62, y1 - 16)), ('swing_set', (x1 - 80, y1 - 40, x1 - 20, y1 - 20))]
        for k_, (kind, r) in enumerate(kit):
            rr = Rm(r)
            props.append({'id': '04-%s-%s%d' % (n_, kind, k_), 'kind': kind, 'pos': W(rcen(rr)), 'rot_deg': 0,
                          'size': [round(rr[2] - rr[0], 2), round(rr[3] - rr[1], 2), 2.2 if kind != 'sandbox' else 0.3], 'grip_anchor': kind == 'swing_set'})
    for n_, r, op in trashes:
        x0, z0 = r[0], r[3]
        for k_, (kind, a_, b_, c_, d_) in enumerate([('skip_bin', 8, 8, 38, 26), ('skip_bin', 42, 8, 72, 26)] + [('green_bin', 10 + k * 22, 36, 26 + k * 22, 52) for k in range(3)]):
            rr = (x0 + a_ * M, z0 - d_ * M, x0 + c_ * M, z0 - b_ * M)
            props.append({'id': '04-trash-%s-%s%d' % ('12' if '12' in n_ else '9', kind, k_), 'kind': kind, 'pos': W(rcen(rr)), 'rot_deg': 0,
                          'size': [round(rr[2] - rr[0], 2), round(rr[3] - rr[1], 2), 1.4 if kind == 'skip_bin' else 1.1], 'grip_anchor': False})
    cz = rcen(box)[1]
    for j, gx in enumerate((box[0] + 3.5, box[2] - 3.5)):
        props.append({'id': '04-box-goal%d' % (j + 1), 'kind': 'football_goal_torn_net', 'pos': W((gx, cz)), 'rot_deg': 90 if j == 0 else 270,
                      'size': [5.0, 1.2, 2.0], 'grip_anchor': False})
    for j, (fx_, fz_) in enumerate(((box[0] + 0.6, box[1] + 0.6), (box[2] - 0.6, box[1] + 0.6))):
        props.append({'id': '04-box-floodlight%d' % (j + 1), 'kind': 'floodlight_mast', 'pos': W((fx_, fz_)), 'rot_deg': 0, 'size': [0.4, 0.4, 9.0], 'grip_anchor': True})
    props.append({'id': '04-box-bench', 'kind': 'spectator_bench', 'pos': W((rcen(box)[0], box[1] + 1.2)), 'rot_deg': 0, 'size': [6.0, 0.6, 0.5], 'grip_anchor': True,
                  'notes': 'gopniks with beer; inside along the south board'})
    props.append({'id': '04-club-neon', 'kind': 'neon_heart_sign', 'pos': W((club[0] - 0.1, rcen(canopy)[1])), 'rot_deg': 180, 'size': [1.0, 0.1, 1.0], 'grip_anchor': False})
    for j, (c, ang) in enumerate(cars):
        props.append({'id': '04-car%d' % (j + 1), 'kind': 'old_soviet_car', 'pos': W(c), 'rot_deg': ang, 'size': list(CAR), 'grip_anchor': False,
                      'notes': 'parody, no brand; parked straight'})
    for j, (q, why) in enumerate(lamps):
        props.append({'id': '04-lamp%02d' % (j + 1), 'kind': 'street_lamp', 'pos': W(q), 'rot_deg': 0, 'size': [0.3, 0.3, 6.0], 'grip_anchor': True,
                      'rule': why, 'placed_by': 's04_rough rule (not plan points)'})
    for j, x_ in enumerate((north_gate[0], north_gate[2])):
        props.append({'id': '04-gatepost%d' % (j + 1), 'kind': 'gate_post', 'pos': W((x_, zf)), 'rot_deg': 0, 'size': [0.5, 0.5, 2.4], 'grip_anchor': True})

    # zones
    dist = [Pm(*T(*p)) for p in ns['DISTRICT']]
    dist = [((sx_new if abs(x - sx_old) < 0.05 else x), z) for x, z in dist]
    zones.append({'id': '04-ground', 'kind': 'ground', 'poly': WL(dist), 'surface': 'worn_grass_L02', 'flat': True,
                  'notes': 'dry faded yellow-brown grass (NOT asphalt, NOT green), trodden bare patches (dirt_SK1b 30-50 %) at podyezd paths, '
                           'garage fronts, trash sections; puddles; transition to the green meadow outside over 40-80 m (v10 §9), no halo'})
    zones.append({'id': '04-ring-road', 'kind': 'road', 'line': WL(road), 'surface': 'asphalt_old_SK2a', 'width_m': ROAD_W, 'kerb': True,
                  'sidewalk': {'side': 'district', 'w_m': 1.5}, 'world_road': True,
                  'kerb_ramps': [W(trk['T1'][0]), W(trk['T2'][0])], 'kerb_ramps_note': 'lowered kerb where the ruts T1 / T2 leave the ring (v10 §4)',
                  'notes': 'outer road as drawn on v85: entry hook into the W-E drive -> west side -> south side -> continues east to the Port '
                           '(D04 ring polyline of the master SVG beyond x 1000); old asphalt, cracks, patches, kerb, narrow sidewalk'})
    zones.append({'id': '04-ring-road-east', 'kind': 'road', 'line': WL(east_leg), 'surface': 'asphalt_old_SK2a', 'width_m': ROAD_W, 'kerb': True,
                  'sidewalk': {'side': 'district', 'w_m': 1.5}, 'world_road': False, 'junction': 'T onto the ring, perpendicular',
                  'notes': 'east side of the plan П-road (plan v52 / legend v45), not drawn on v85 — see questions'})
    hamlet = road_starting(world['roads'], (666.0, 674.0), end=-1)
    tun = road_starting(world['roads'], (748.0, 671.0))
    serp = road_starting(world['roads'], (945.0, 671.0))

    def clip(pl, c, Rr):
        return [rnd2(p) for p in pl if math.hypot(p[0] - c[0], p[1] - c[1]) <= Rr]
    ex = [('04-exit-hamlet', clip(hamlet, (666, 674), 45), 'Hamlet road (base 2 -> base 3), joins the SW corner'),
          ('04-exit-tunnel', clip(tun, (748, 671), 40), 'tunnel under hill B to Downtown (north portal)'),
          ('04-exit-serpentine', clip(serp, (945, 671), 40), 'serpentine VIEW B / Downtown'),
          ('04-exit-port', clip([p for p in ring if p[0] >= 990.0], (990, 674), 50), 'road to the Port and the Tramduro bridge (continuation of the ring)'),
          ('04-kpp-road', [rnd2(p) for p in kpp_road_w if p[1] <= 896.0] + [rnd2((860.0, 950.0))], 'road to the KPP, through the district gate; ends at the map edge (steppe, invisible wall)')]
    for zid, line, nm in ex:
        zones.append({'id': zid, 'kind': 'road', 'line': line, 'surface': 'asphalt_old_SK2a', 'width_m': ROAD_W, 'kerb': zid != '04-kpp-road',
                      'world_road': True, 'notes': nm + ' (drawn v85 network; first metres only, the road step owns the rest)'})
    for k_, pl in trk.items():
        zones.append({'id': '04-track-' + k_, 'kind': 'track', 'line': WL(pl), 'surface': 'dirt_SK1b', 'width_m': TRACK_W[k_],
                      'width_range_m': [TRACK_W[k_] - 1.0, TRACK_W[k_] + 0.5], 'name': TRACK_NAME[k_],
                      'notes': 'uneven grey ruts over dry grass: ragged edges, varying width, gaps, puddles; no kerb, no asphalt, no lamps / trees on it'})
    zones.append({'id': '04-fence-w-n', 'kind': 'fence', 'line': WL(f_left), 'surface': 'concrete_panel_SK3c', 'height_m': 2.2,
                  'notes': 'district fence (plan v52): old concrete panels, straight north side (v50); ends at the KPP-road gate'})
    zones.append({'id': '04-fence-n-e', 'kind': 'fence', 'line': WL(f_right), 'surface': 'concrete_panel_SK3c', 'height_m': 2.2,
                  'notes': 'district fence (plan v52) from the KPP-road gate: step, NE side, east side, stub to the verge of the east road'})
    zones.append({'id': '04-gate-kpp', 'kind': 'gate', 'poly': WR(grow(north_gate, 0.0, 0.3)), 'surface': None, 'w_m': round(north_gate[2] - north_gate[0], 2),
                  'open': True, 'notes': 'gateway with posts, no leaf / barrier; the KPP road passes straight through'})
    for j, bl in enumerate(world['border']):
        zones.append({'id': '04-border-fence%d' % (j + 1), 'kind': 'border_fence', 'line': [rnd2(p) for p in bl], 'surface': 'fence_net', 'height_m': 3.0,
                      'scope': 'north_border', 'notes': 'country border: chain-link on posts (x 572-1031), invisible wall along it, steppe beyond; meets the KPP'})
    zones.append({'id': '04-kpp-stopline', 'kind': 'road_marking', 'line': [rnd2((856.6, 922.5)), rnd2((863.4, 922.5))], 'surface': None,
                  'scope': 'north_border', 'notes': 'STOP line before the KPP gate (v85)'})
    for p in pals:
        r = p['rect']
        pieces = [(r[0], r[1], p['skip'][0], r[3]), (p['skip'][1], r[1], r[2], r[3])] if p['skip'] else [r]
        for k_, q in enumerate(pieces):
            zones.append({'id': '04-palisade-%s-%s%s' % (p['bid'][3:], p['side'], 'abc'[k_] if len(pieces) > 1 else ''), 'kind': 'front_garden',
                          'poly': WR(q), 'surface': 'lawn', 'low_fence': {'h_m': 0.6, 'side': 'outer edge', 'gaps': 'at every podyezd path'},
                          'facade': p['bid'], 'side': p['side'], 'notes': 'live green grass ~4 m with a low fence; podyezd paths cross it'})
    for n_, r in plays:
        zones.append({'id': '04-playground-' + ('yard12' if '12' in n_ else 'yard9'), 'kind': 'playground', 'poly': WR(r), 'surface': 'rubber',
                      'kerb': True, 'name_ru': n_, 'notes': 'neat rectangle with a kerb: swings, slide, sandbox (+ roundabout and 2nd swings on the big one)'})
    for n_, r, op in trashes:
        zones.append({'id': '04-trash-' + ('yard12' if '12' in n_ else 'yard9'), 'kind': 'trash_section', 'poly': WR(r), 'surface': 'concrete_SK3c',
                      'open_side': {'открыта на юг': 'S', 'открыта на запад': 'W'}.get(op, op), 'walls': 'roof_profsheet_SK4c on 3 sides',
                      'notes': '2 skip "boats" + 3 green bins'})
    zones.append({'id': '04-football-box', 'kind': 'football_box', 'poly': WR(box), 'surface': 'lawn', 'size_m': [BOX_W, BOX_D],
                  'fence': {'board_h_m': 1.0, 'net_h_m': 4.5, 'material': 'fence_net', 'hole_in_net': True, 'graffiti_on_board': True},
                  'wicket': {'pos': W((rcen(box)[0], box[3])), 'w_m': round(48 * M, 2), 'side': 'N', 'van_enters': True},
                  'notes': 'worn artificial turf with bald patches, goals with torn nets at both short ends, ONE wicket mid north side, 2 floodlights, '
                           'spectator bench, balls and bottles inside; NPC always play / hang out'})
    zones.append({'id': '04-box-lane', 'kind': 'drive', 'poly': WR((box[0], box[3], box[2], [p for p in pals if p['bid'] == '04-H13'][0]['rect'][1])),
                  'surface': 'worn_grass_L02', 'notes': 'approach to the box wicket between the box fence and the H13 palisade (see questions)'})
    zones.append({'id': '04-base3-van-spot', 'kind': 'loading_pad', 'poly': WR(van), 'surface': 'concrete_SK3c', 'base': 3,
                  'notes': 'yard 2: van spot 5.2 x 8.7 m in front of the base garage gate in H17; garage L (5 + 2) hides it; yard ~30 x 19 m to turn'})
    zones.append({'id': '04-base3-yard', 'kind': 'yard', 'poly': WR((pr['04-H17a'][2] + LAWN, pr['04-H17b'][3], max(g['rect'][2] for g in garages if g['group'] == 'GB'),
                                                                   min(g['rect'][1] for g in garages if g['group'] == 'GB' and g['gate'] == 'S'))),
                  'surface': 'worn_grass_L02', 'notes': 'base 3 yard (function: loading, turning) — no trees, no props in the middle'})
    zones.append({'id': '04-club-smokers', 'kind': 'plaza', 'poly': WR(smokers), 'surface': 'concrete_SK3c',
                  'notes': 'smokers corner in front of the club entrance: bouncer, crowd; central NPC area with yard 12'})
    for n_, c, rx, rz in squares:
        zones.append({'id': '04-square-' + ('box' if 'box' in n_ else 'yard13'), 'kind': 'mini_square', 'poly': WL(ellipse(c, rx, rz)), 'surface': 'lawn',
                      'notes': n_ + ': patch of lawn, a few bare trees, tyre flower bed; benches only at podyezds (legend)'})
    # vegetation
    trees = [tuple(t) for t in plan['trees']]
    used = set()

    def count_in(poly_or_rect, kind='rect'):
        n = 0
        for j, t in enumerate(trees):
            if j in used:
                continue
            ok = rdist(t, grow(poly_or_rect, 0.6)) == 0 if kind == 'rect' else ((t[0] - poly_or_rect[0][0]) / poly_or_rect[1]) ** 2 + ((t[1] - poly_or_rect[0][1]) / poly_or_rect[2]) ** 2 <= 1.15
            if ok:
                used.add(j)
                n += 1
        return n
    veg = 0
    for p in pals:
        r = p['rect']
        sn = p['side'] in 'SN'
        lo, hi = (r[0], r[2]) if sn else (r[1], r[3])
        cuts = [lo] + sorted(d['pos'][0] if sn else d['pos'][1] for d in doors if d['host'] == p['bid'] and d['side'] == p['side']) + [hi]
        holes = [p['skip']] if p['skip'] else []
        for u, v in zip(cuts[:-1], cuts[1:]):
            u2, v2 = u + (2.0 if u != lo else 0.5), v - (2.0 if v != hi else 0.5)
            for hlo, hhi in holes:
                if u2 < hhi and hlo < v2:
                    if hlo - u2 > v2 - hhi:
                        v2 = hlo - 1.0
                    else:
                        u2 = hhi + 1.0
            if v2 - u2 < 2.5:
                continue
            q = (u2, r[1] + 0.6, v2, r[3] - 0.6) if sn else (r[0] + 0.6, u2, r[2] - 0.6, v2)
            n = count_in(q)
            if n:
                veg += 1
                zones.append({'id': '04-veg-pal-%s-%s%d' % (p['bid'][3:], p['side'], veg), 'kind': 'veg_zone', 'poly': WR(q), 'density': 'sparse',
                              'species': 'bare', 'target_count': n, 'notes': 'bare crooked tree(s) in the palisade between podyezds (cold grey-brown bark)'})
    for n_, c, rx, rz in squares:
        n = count_in((c, rx, rz), 'ell')
        zones.append({'id': '04-veg-square-' + ('box' if 'box' in n_ else 'yard13'), 'kind': 'veg_zone', 'poly': WL(ellipse(c, rx * 0.8, rz * 0.8)),
                      'density': 'grove', 'species': 'bare', 'target_count': n, 'notes': n_})
    for j, c in enumerate(pockets):
        before = len(used)
        n = count_in((c[0], c[1], c[0], c[1]))
        if n:
            zones.append({'id': '04-veg-garages%d' % (j + 1), 'kind': 'veg_zone', 'poly': WL(ellipse(c, 3.0, 3.0, 10)), 'density': 'sparse',
                          'species': 'bare', 'target_count': n, 'notes': 'a tree behind / next to garages, not in their drive'})
    stray = [trees[j] for j in range(len(trees)) if j not in used]
    nt = []
    for k_, pl in trk.items():
        nt.append(('track ' + k_, buffer_line(pl, TRACK_W[k_] / 2 + 2.0)))
    nt.append(('outer road + verge', buffer_line(road, ROAD_W / 2 + 2.0)))
    nt.append(('east road + verge', buffer_line(east_leg, ROAD_W / 2 + 2.0)))
    nt.append(('KPP road', buffer_line([(kx, kz0 - 2.0), (kx, Pinv(860.0, 950.0)[1])], ROAD_W / 2 + 2.0, cap=False)))   # stops at the map edge
    nt.append(('base 3 yard + van spot (loading pad)', rpoly(grow(van, 2.0))))
    nt += [('playground', rpoly(grow(r, 1.5))) for n_, r in plays]
    nt += [('trash section + access', rpoly(grow(r, 2.0))) for n_, r, _ in trashes]
    nt.append(('football box + lane', rpoly(grow(box, 2.0))))
    gn = [g['rect'] for g in garages if g['group'] == 'GN']
    nt.append(('drive under / in front of the 12 garages', rpoly((min(r[0] for r in gn) - 2, pr['04-H56a'][3], max(r[2] for r in gn) + 2, min(r[1] for r in gn)))))
    nt.append(('drive under the 12 garages (west)', rpoly((min(r[0] for r in gn) - 2, pr['04-H1a'][3], pr['04-H1a'][2] + 2, min(r[1] for r in gn)))))
    g7 = [g for g in garages if g['group'] == 'G7']
    nt.append(('coop 7 lane', rpoly((max(g['rect'][2] for g in g7 if g['gate'] == 'E'), max(g['rect'][3] for g in g7 if g['gate'] == 'N'),
                                     min(g['rect'][0] for g in g7 if g['gate'] == 'W'), min(g['rect'][1] for g in g7 if g['gate'] == 'S')))))
    gne = [g['rect'] for g in garages if g['group'] == 'GNE']
    nt.append(('GNE garage lane', rpoly((max(r[2] for r in gne if r[0] < 300), plan['tracks'][0][-1][1], min(r[0] for r in gne if r[0] > 310), max(r[1] for r in gne)))))
    nt += [('arch approach', rpoly(r)) for r in arch_zone]
    nt.append(('club smokers corner', rpoly(grow(smokers, 1.0))))
    nt.append(('shop forecourt', rpoly((shop[0] - 4.0, ROAD_W / 2, shop[2] + 4.0, shop[1]))))
    nt.append(('KPP-road gate', rpoly(grow(north_gate, 1.0, 6.0))))
    for j, (why, poly) in enumerate(nt):
        zones.append({'id': '04-no-tree%02d' % (j + 1), 'kind': 'no_tree', 'poly': WL(poly), 'why': why})
    zones.append({'id': '04-no-tree-default', 'kind': 'no_tree', 'poly': WL(dist), 'why': 'Rough interior: trees ONLY inside the veg_zone polygons of this file '
                  '(legend v45 §1.7: palisades between podyezds, 2 mini-squares, a pair at garages; never on ruts or the waste ground)', 'veg_zones_override': True})

    # ------------------------------------------------ sight-line checks (v10 §7.4 / §14)
    solid = [r for n_, r in obst if not n_.startswith(('play', 'trash', 'box'))]          # chain-link box does not block a view
    fsegs = [(a_, b_) for fl in (f_left, f_right) for a_, b_ in zip(fl[:-1], fl[1:])]
    zmax = max(p[1] for p in plan['fence'])

    def ranges(vals, step):
        out = []
        for v in vals:
            if out and v - out[-1][1] <= step + 1e-6:
                out[-1][1] = v
            else:
                out.append([v, v])
        return [[round(a_, 1), round(b_, 1)] for a_, b_ in out]
    sn, we = [], []
    for k_ in range(0, 640):                                              # straight S->N lines x = const from the south road to the north fence
        x = k_ / 2.0
        if not 6.0 <= x <= xe - 6.0:                                      # core only: the strips along the west / east roads are the district edge
            continue
        hit = any(r[0] <= x <= r[2] for r in solid) or any(min(a_[0], b_[0]) <= x <= max(a_[0], b_[0]) and a_[1] == b_[1] and a_[1] < zmax - 1 for a_, b_ in fsegs)
        if not hit:
            sn.append(x)
    for k_ in range(2, 470):                                              # straight W->E lines z = const from the west road to the east road
        z = k_ / 2.0
        if not 10.0 <= z <= zmax - 2.0:                                   # core only: the strip along the south road is the district edge
            continue
        hit = any(r[1] <= z <= r[3] for r in solid) or any(min(a_[1], b_[1]) <= z <= max(a_[1], b_[1]) and a_[0] == b_[0] and 0 < a_[0] < xe for a_, b_ in fsegs)
        if not hit:
            we.append(z)
    checks['straight_S_to_N_open_x_ranges'] = ranges(sn, 0.5)
    checks['straight_W_to_E_open_z_ranges'] = ranges(we, 0.5)
    checks['straight_lines_note'] = ('core x 6..%.0f / z 10..%.0f (plan m); edges not counted: the strip x < 3.5 between the west road and H17/H11/H3/H2/H1 '
                                     'reaches the closed NW fence corner, the strip z < 9 is the south road verge. A result of [183.0, 183.0] is the 0.3 m '
                                     'slit between the east ends of H7/H56b (x 182.89) and the west end of the E wing (x 183.2) — no passage' % (xe - 6, zmax - 2))
    checks['arches'] = {a['id']: {'through': a['through'], 'clear_w_m': round(a['clear_w'], 2), 'clear_h_m': ARCH_H, 'ok': a['clear_w'] >= 4.0} for a in arches}
    checks['outer_road_clearance_m'] = {k_: round(v[0], 2) for k_, v in road_c.items()}
    a4 = [a for a in arches if a['id'].endswith('4')][0]['rect']
    a5 = [a for a in arches if a['id'].endswith('5')][0]['rect']
    checks['W_E_drive'] = {'through_A4': any(a4[0] <= q[0] <= a4[2] and a4[1] <= q[1] <= a4[3] for q in samples(trk['T0'])),
                           'through_A5': any(a5[0] <= q[0] <= a5[2] and a5[1] <= q[1] <= a5[3] for q in samples(trk['T0'])),
                           'A4_centre_z': round(rcen(a4)[1], 2), 'A5_centre_z': round(rcen(a5)[1], 2), 'step_m': round(rcen(a4)[1] - rcen(a5)[1], 2),
                           'v45_A4_z': 114.1, 'v45_A5_z': 100.85}
    gn_z0 = min(r[1] for r in gn)
    checks['garages_north_row'] = {'n': len(gn), 'depth_m': round(gn[0][3] - gn[0][1], 2), 'gates': 'S', 'drive_under_to_H1_m': round(gn_z0 - pr['04-H1a'][3], 2),
                                   'in_front_to_H56_m': round(gn_z0 - pr['04-H56a'][3], 2)}
    lane = [p for p in pals if p['bid'] == '04-H13'][0]['rect'][1] - box[3]
    checks['football_box'] = {'size_m': [BOX_W, BOX_D], 'gap_shop_box_m': round(box[1] - shop[3], 2), 'gap_box_H13_m': round(h13[1] - box[3], 2),
                              'lane_box_to_H13_palisade_m': round(lane, 2)}
    checks['lamps_dropped_by_rule'] = dropped
    checks['plan_trees_not_in_a_zone'] = [list(map(lambda v: round(v, 2), t)) for t in stray]
    question('Подъезд бусика к калитке футбольной коробки: коробка 40 x 33 м с зазором ~8 м до дома H13 (v10), но 4 м из них — палисадник H13 с заборчиком; '
             'между сеткой коробки и палисадником остаётся полоса %.1f м — бусик доедет вдоль неё, но развернуться в калитку посередине северной стороны не сможет.' % lane,
             ['1 — оставить как есть (калитка посередине севера, полоса %.1f м)' % lane,
              '2 — палисадник H13 напротив коробки уже, ~1,5 м: полоса ~%.1f м' % (lane + LAWN - 1.5),
              '3 — калитку перенести на западную короткую сторону (там пустырь ~28 м до H14)'], 1,
             'данные: вариант 1 (калитка в центре севера, палисадник H13 4 м, фонари у северных углов коробки не ставятся)')
    question('Восточная сторона внешней дороги «П» есть в плане v52 и в легенде, но не нарисована на карте v85; без неё сквозной проезд запад–восток заканчивается в углу забора у восточных гаражей.',
             ['1 — асфальт восточной стороны по плану v52: от кольца до конца колеи (сейчас в данных)', '2 — без восточной стороны: проезд кончается тупиком у гаражей (как на карте v85)',
              '3 — вместо асфальта колея по сухой траве до кольца'], 1, 'данные: вариант 1, zone 04-ring-road-east')
    question('Северная граница: забор района (план v52, с уступом 25 м над домом H8) и забор страны с КПП в 20–30 м севернее — двойной забор с полосой пустыря между ними. Дорога к КПП нарисована точно по уступу забора района.',
             ['1 — оба забора; уступ сдвинут на %.1f м восточнее, в северном заборе района ворота %.1f м, дорога к КПП прямая (сейчас в данных)' % (sx_new - sx_old, 2 * gate_half),
              '2 — северный забор района прямой на всю ширину (y %.1f мира), уступа нет, ворота там же' % P(0, zf)[1],
              '3 — северного забора района нет: край района — забор страны с КПП'], 1, 'данные: вариант 1')
    gap_t = {('12' if '12' in n_ else '9'): round(min(max(r[0] - q[2], q[0] - r[2], r[1] - q[3], q[1] - r[3], 0.0) for n2, q in plays), 1) for n_, r, _ in trashes}
    question('Мусорные секции дворов 12 и 9 стоят в %s м от детских площадок (план v52 и легенда v45: «в сердце двора»), а v02 §8.4 требует «мусорка ≥ 20 м от окон и площадки».'
             % ' и '.join('%.1f' % v for v in gap_t.values()),
             ['1 — как на плане: мусорка рядом с площадкой, открыта к проезду (сейчас в данных)', '2 — отодвинуть мусорки на ≥ 20 м от площадок и окон, к колее'], 1, 'данные: вариант 1')
    question('Арки А4 и А5 сквозного проезда — это перемычки над разрывом 13–14 м между торцами двух корпусов: проём получается шириной ~13–14 м, а не 6–7 м, как у остальных арок.',
             ['1 — как на плане: весь разрыв под перемычкой открыт (сейчас в данных)', '2 — проём ~7 м, по бокам глухие простенки (проезд «не так свободно»)'], 1,
             'данные: вариант 1, clear_w_m 13.1 / 13.9')

    # ------------------------------------------------ fit + output
    fit = measure_fit(P, parts, road, world)
    lin = info['lin']
    transform = ('plan v52 metres (x east, z north, 0 = SW corner of the outer-road axis) -> plan px (x/%.4f + %.2f, %.2f - z/%.4f; build_rough_v52 export, '
                 'origin T(113, 1765)) -> rough_v52_world.png px (x %d/%d, y %d/%d; make_rough_world_v52 k = %.4f) -> master-SVG units + (%.1f, %.1f) '
                 '-> world = common.u2w (pre-shift metres + post_shift: +22 m north for z > 1 m, less on the south exits). Net for z > 1 m: '
                 'x = %.3f + %.5f x, y = %.3f + %.5f z (scale 1.0, no rotation; the v76 port of v45 used +(667, 668)). Fit on the v85 render: %s'
                 % (info['M'], OXm, OYm, info['M'], info['img'][2], info['plan_px'][0], info['img'][3], info['plan_px'][1], info['k'],
                    info['img'][0], info['img'][1], lin[0], lin[1], lin[2], lin[3], fit['text']))
    for f in FIXES:
        f['where'] = W(f.pop('where_local'))
    for b in blds:                                                        # schema: every polygon counter-clockwise, arches key everywhere
        b['footprint'] = ccw(b['footprint'])
        b.setdefault('arches', [])
        for a in b['arches']:
            a['rect'] = ccw(a['rect'])
        for e in b['entrances']:
            if 'path' in e:
                e['path']['poly'] = ccw(e['path']['poly'])
        if 'ground_floor_use' in b:
            for k_ in ('rect', 'gate_rect'):
                if k_ in b['ground_floor_use']:
                    b['ground_floor_use'][k_] = ccw(b['ground_floor_use'][k_])
    for z in zones:
        if 'poly' in z:
            z['poly'] = ccw(z['poly'])
    nb_ = sum(d['benches'] for d in doors)
    counts = {'houses': len(plan['houses']), 'khrushchevka_parts': len(parts), 'arch_bridges': sum(1 for a in arches if not a['host']),
              'podyezds': len(doors), 'benches': nb_, 'arches': len(arches), 'garages': len(garages),
              'garages_by_group': {g: sum(1 for x in garages if x['group'] == g) for g in ('GN', 'G7', 'GNE', 'GB')},
              'lamps': len(lamps), 'lamps_by_rule': {w_: sum(1 for _, x in lamps if x == w_) for w_ in ('house corner', 'playground corner', 'box corner', 'outer road')},
              'cars': len(cars), 'playgrounds': len(plays), 'trash_sections': len(trashes), 'booths': len(booths), 'turniks': len(plan['turniks']),
              'tracks': len(trk), 'veg_zones': sum(1 for z in zones if z['kind'] == 'veg_zone'),
              'veg_target_trees': sum(z.get('target_count', 0) for z in zones if z['kind'] == 'veg_zone'),
              'no_tree_zones': sum(1 for z in zones if z['kind'] == 'no_tree'),
              'plan': {'podyezds': len(plan['doors']), 'benches': sum(d['benches'] for d in plan['doors']), 'lamps': len(plan['lamps']),
                       'trees': len(plan['trees']), 'cars': len(plan['cars']), 'garages': len(plan['garages'])}}
    out = {'district': 'rough', 'version': 'v85 from plan v52',
           'sources': [os.path.relpath(p, ROOT).replace(os.sep, '/') for p in (PLAN_JSON, PLAN_PY, PLAN_PNG, WORLD_PY)] +
                      ['ArtSource/References/Map/World_v85/VOLUNTEERS_MAP_MASTER_v85.svg (<image> rough_v52_world.png, R85_rough_ring, R24_roads, R69_checkpoint, R60 border)',
                       'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §4 §6 §7.4 §8', 'docs/specs/ROUGH_LEGEND_v45.md', 'docs/specs/ROUGH_SPEC_2026-10-15_v01.md',
                       'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.4'],
           'transform': transform, 'fit': fit['data'],
           'pad_height_m': 5.0, 'pad_note': 'flat pad; Rough and Downtown on the same height (v10 §3.1); edges blend softly into the terrain',
           'abs_heights': False, 'lighting': 'overcast_fog',
           'lighting_notes': 'low dark grey sky, dim, fog (visibility 120-150 m, ground haze in yards and at garages), lamps on at night, crows; '
                             'transitions 40-80 m at the district edge (v02 §6)',
           'no_wires': True, 'buildings': blds, 'props': props, 'zones': zones, 'fixed_by_logic': FIXES, 'questions_for_vadim': QUESTIONS,
           'counts': counts, 'checks': checks}
    return out, P, Pinv


# ---------------------------------------------------------------- fit against the v85 render
def measure_fit(P, parts, road, world):
    x0w, y0w, x1w, y1w = 640, 655, 1005, 915
    im = Image.open(MAP_FULL).convert('RGB').crop((x0w * 5, (950 - y1w) * 5, x1w * 5, (950 - y0w) * 5))
    a = np.asarray(im).astype(np.int16)
    house = (np.abs(a[..., 0] - 207) < 7) & (np.abs(a[..., 1] - 211) < 7) & (np.abs(a[..., 2] - 214) < 7)
    asph = (np.abs(a[..., 0] - 95) < 12) & (np.abs(a[..., 1] - 102) < 12) & (np.abs(a[..., 2] - 108) < 12)
    Hh, Ww = house.shape
    pm = Image.new('L', (Ww, Hh), 0)
    dr = ImageDraw.Draw(pm)
    tp = lambda p: ((p[0] - x0w) * 5, (y1w - p[1]) * 5)
    for b, hid, k, r in parts:
        q0, q1 = tp(P(r[0] + 0.9, r[1] + 0.9)), tp(P(r[2] - 0.9, r[3] - 0.9))
        dr.rectangle([q0[0], q1[1], q1[0], q0[1]], fill=255)
    pred = np.asarray(pm) > 0
    best = None
    for dy in range(-10, 11):
        for dx in range(-10, 11):
            sh = np.roll(np.roll(pred, dy, 0), dx, 1)
            sc = int((sh & house).sum()) - int((sh & ~house).sum())
            if best is None or sc > best[0]:
                best = (sc, dx, dy)
    frac = float((pred & house).sum()) / float(pred.sum())
    # edges: position of the dark outline (drawn 3 plan px = 0.37 m inside each edge) along normals
    dark = (a.sum(-1) < 300)
    errs = {'W': [], 'E': [], 'S': [], 'N': []}
    for b, hid, k, r in parts:
        lo, hi = P(r[0], r[1]), P(r[2], r[3])
        for side in errs:
            vals = []
            span = (lo[1], hi[1]) if side in 'WE' else (lo[0], hi[0])
            for t in np.linspace(span[0] + 2.0, span[1] - 2.0, 7):
                best_s = None
                for s in np.arange(-1.6, 1.61, 0.2):                     # s > 0 = outward
                    if side == 'W':
                        q = (lo[0] - s, t)
                    elif side == 'E':
                        q = (hi[0] + s, t)
                    elif side == 'S':
                        q = (t, lo[1] - s)
                    else:
                        q = (t, hi[1] + s)
                    i, j = int(round((y1w - q[1]) * 5)), int(round((q[0] - x0w) * 5))
                    if 0 <= i < Hh and 0 <= j < Ww and dark[i, j]:
                        best_s = s if best_s is None else max(best_s, s)
                if best_s is not None:
                    vals.append(best_s)
            if len(vals) >= 4:
                errs[side].append(float(np.median(vals)))
    edge = {k: (round(float(np.median(v)), 2) if v else None) for k, v in errs.items()}
    # outer road: centre of the drawn asphalt across the legs vs the plan axis
    rs, rw = [], []
    for xw in range(700, 961, 20):
        if min(abs(xw - 748), abs(xw - 945)) < 10:                     # skip the exits (asphalt continues south there)
            continue
        j = int(round((xw - x0w) * 5))
        col = [y1w - i / 5.0 for i in range(Hh) if asph[i, j] and 662 <= y1w - i / 5.0 <= 680]
        if len(col) > 10:
            rs.append(float(np.mean(col)) - P(xw - 665.99, 0.0)[1])
    for yw in range(690, 771, 10):
        i = int(round((y1w - yw) * 5))
        row = [x0w + j / 5.0 for j in range(Ww) if asph[i, j] and 657 <= x0w + j / 5.0 <= 675]
        if len(row) > 10:
            rw.append(float(np.mean(row)) - P(0.0, yw - 671.0)[0])
    svg_w = abs(P(0.0, 50.0)[0] - world['ring'][3][0])
    svg_s = abs(P(150.0, 0.0)[1] - 671.0)
    res = max(abs(v) for v in edge.values() if v is not None)
    data = {'houses_best_extra_shift_m': [best[1] / 5.0, -best[2] / 5.0], 'houses_fill_overlap': round(frac, 3),
            'house_outline_outer_edge_vs_footprint_m': edge, 'house_residual_max_m': round(res, 2),
            'road_axis_render_south_m': round(float(np.median(rs)), 2) if rs else None, 'road_axis_render_west_m': round(float(np.median(rw)), 2) if rw else None,
            'road_axis_svg_west_m': round(svg_w, 3), 'road_axis_svg_south_m': round(svg_s, 3)}
    text = ('houses (25 parts) on VOLUNTEERS_MAP_FINAL_v85.png (5 px/m): best extra shift (%.1f, %.1f) m in a +-2 m / 0.2 m search, %.0f %% of the footprints '
            '(inset 0.9 m) on house colour, outer edge of the drawn outline vs footprint edge per side %s m -> residual <= %.1f m (1 px); outer road: '
            'drawn axis vs plan axis %.2f m (west) / %.2f m (south) in the SVG, %.2f / %.2f m measured on the FINAL render'
            % (best[1] / 5.0, -best[2] / 5.0, frac * 100, edge, res, svg_w, svg_s, data['road_axis_render_west_m'] or 0, data['road_axis_render_south_m'] or 0))
    return {'data': data, 'text': text}


# ---------------------------------------------------------------- check images
def draw_dist(im, tp, d, s, full=False):
    """Bands of real width (tracks green, roads yellow, translucent), zones cyan, fences purple, footprints red, arches orange,
    entrances blue, props magenta (cars as rectangles)."""
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for z in d['zones']:
        if 'line' in z and z['kind'] in ('track', 'road'):
            col = (0, 210, 0, 90) if z['kind'] == 'track' else (255, 225, 0, 80)
            dl.polygon([tp(q) for q in buffer_line(z['line'], z['width_m'] / 2.0, cap=False)], fill=col)
    im.paste(Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB'))
    dr = ImageDraw.Draw(im)
    for z in d['zones']:
        if z['kind'] in ('ground', 'no_tree'):
            continue
        if 'poly' in z:
            col = {'veg_zone': (20, 140, 40), 'front_garden': (0, 170, 200)}.get(z['kind'], (0, 160, 255))
            dr.polygon([tp(q) for q in z['poly']], outline=col)
        if 'line' in z:
            col = (0, 150, 0) if z['kind'] == 'track' else ((200, 160, 0) if z['kind'] == 'road' else (150, 0, 200))
            dr.line([tp(q) for q in z['line']], fill=col, width=1 if z['kind'] in ('track', 'road') else max(2, s // 2))
    for b in d['buildings']:
        dr.polygon([tp(p) for p in b['footprint']], outline=(255, 0, 0), width=2 if full else 1)
        for a in b.get('arches', []):
            dr.polygon([tp(p) for p in a['rect']], outline=(255, 140, 0))
        for e in b.get('entrances', []):
            x, y = tp(e['pos'])
            dr.ellipse([x - s * 0.5, y - s * 0.5, x + s * 0.5, y + s * 0.5], fill=(0, 0, 255))
    for p in d['props']:
        x, y = tp(p['pos'])
        rr = s * (0.9 if p['kind'] in ('street_lamp', 'old_soviet_car') else 0.5)
        if p['kind'] == 'old_soviet_car':
            w_, h_ = (p['size'][0] / 2, p['size'][1] / 2) if p['rot_deg'] % 180 == 0 else (p['size'][1] / 2, p['size'][0] / 2)
            dr.rectangle([x - w_ * s, y - h_ * s, x + w_ * s, y + h_ * s], outline=(255, 0, 255), width=2)
        else:
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 0, 255))


def overlays(d):
    os.makedirs(WORK, exist_ok=True)
    x0, y0, x1, y1 = 625, 640, 1045, 948
    s = 3
    im = Image.open(MAP_PREVIEW).convert('RGB').crop((x0, 950 - y1, x1, 950 - y0))
    im = im.resize((im.width * s, im.height * s), Image.NEAREST)
    draw_dist(im, lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s), d, s)
    im.save(os.path.join(WORK, 'check_rough.png'))
    s = 5
    im = Image.open(MAP_FULL).convert('RGB').crop((x0 * s, (950 - y1) * s, x1 * s, (950 - y0) * s))
    draw_dist(im, lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s), d, s, full=True)
    im.save(os.path.join(WORK, 'check_rough_full.png'))


def main():
    d, P, Pinv = build()
    save_json('districts/rough_v85.json', d)
    overlays(d)
    print('rough_v85:', json.dumps(d['counts'], ensure_ascii=False))
    print('fit:', d['transform'].split('Fit on the v85 render: ')[1])
    print('tracks:', d['checks']['tracks'])
    print('straight S->N open x:', d['checks']['straight_S_to_N_open_x_ranges'], 'W->E open z:', d['checks']['straight_W_to_E_open_z_ranges'])
    print('cars/lamps/doors ok; lamps dropped:', d['checks']['lamps_dropped_by_rule'], 'stray plan trees:', d['checks']['plan_trees_not_in_a_zone'])
    print('fixes:', len(d['fixed_by_logic']), 'questions:', len(d['questions_for_vadim']))


if __name__ == '__main__':
    main()
