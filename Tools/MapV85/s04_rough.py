"""Step 4 / district 04 Rough ("Неблагополучный"): plan v52 + W86 replanning (Vadim 22.10.2026) -> world v85 district data.

History. W85 (CL-MAP85, 21.10): plan v52 ported 1:1 -> Data/v01 (FROZEN: this script refuses to write v01). W86 (brief A2 "Rough
replanning", 22.10): the same sources + Vadim's prompt `Working/Reviews/MapW86_Inputs_2026-10-22/ПРОМПТ_Феде_Неблагополучный_перепланировка_v01.md`,
his marked plan `rough_v52_marked_by_vadim.webp` (red = extend the EXISTING house into the rectangle, white = van passage) and Fedya's crop
`rough_garages_crop_vadim.png` (free the van passage east of the base-3 garages). In order (replan_w86):
 1. denser (Fedya 22.10 item 3: smaller distances BETWEEN houses, edges as v52): house parts grow along their long axes at free ends
    (grow_houses); nothing moves, outer road, exits, KPP road, KPP, side fences and the district ground stay where v52 / v85 draw them;
 2. blocks W and E become continuous houses over the old A4 / A5 gaps (one rect part each);
 3. the 8 red marks: host lengthened or given a wing (same floors / facade / roof), podyezds + palisades on the new pieces;
 4. all 6 arches one size: clear ARCH_W x ARCH_H, real arches through a continuous house; A5 on the W-E drive between the new wings;
 5. coop 7 tighter (court 13 -> G7_COURT m) and raised: equal tight passages under it (white strip) and over it;
 6. base-3 garage L moved west: free N-S passage (white strip) between it and the new wing of H14 -> track T8;
 7. tracks re-derived from the new geometry (stepped W-E drive via A4 / A5 kept, T8 / T9 / T10 new);
 8. props that the new pieces would block are moved by logic (booths, pull-up bar, cars, pockets); lamps / trees by rule as before.
 9. Fedya 22.10 (ANSWERS_FEDYA_2026-10-22.md 1-7): no district fence on the north (the state fence with the KPP is the edge, side fences run up
    to it), football-box wicket on the west short side at its north end; kept: stepped W-E drive via A4 / A5, S-N see-throughs closed.
Checks in "checks.w86": arch list, van grid search (2.3 m disc, widest path to every target), 2.3 x 5.5 m rectangle sweep along every
track and through every arch (fillet radius TURN_R), min gaps, overlaps, entrances on facades. Report images: plan_images().

Transform chain (derived from the sources at run time, see `load_chain`): plan metres (x east, z north, 0 = SW corner of the outer-road
axis) -> plan px (build_rough_v52 export: x/M + T(113,1765).x, T(113,1765).y - z/M) -> rough_v52_world.png px (make_rough_world_v52:
resize by k = M*5 to int size) -> master-SVG units (+ <image> x, y) -> world v85 = common.u2w (pre-shift metres + post_shift,
+22 m north in the Rough band). Fit against the v85 render is measured every run and written to "transform" (houses of plan v52).

Outputs: Data/<REV>/districts/rough_v85.json (DISTRICT_SCHEMA.md), out_<REV>/check_rough.png (preview x3), out_<REV>/check_rough_full.png
(FINAL 5 px/m crop), out_<REV>/rough_w86_*.png (plan-frame images). Run: MAPV85_REV=v02 python s04_rough.py (deterministic, ~1 min).
"""
import json
import math
import os
import random
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

import common
from common import (MAP_FULL, MAP_PREVIEW, REF, REV, ROOT, apply, attr, area, ccw, h01, num, points_of, rnd2, save_json, svg_tags,
                    svg_text, u2w)

Image.MAX_IMAGE_PIXELS = None
SRC_DIR = os.path.join(REF, 'World_v83', 'Districts')
PLAN_JSON = os.path.join(SRC_DIR, 'Планировка_v52.json')
PLAN_PY = os.path.join(SRC_DIR, 'build_rough_v52.py')
PLAN_PNG = os.path.join(SRC_DIR, 'Неблагополучный_район_v52.png')
WORLD_PY = os.path.join(REF, 'World_v83', 'make_rough_world_v52.py')
INPUTS = os.path.join(ROOT, 'Working', 'Reviews', 'MapW86_Inputs_2026-10-22')
MARKED = os.path.join(INPUTS, 'rough_v52_marked_by_vadim.webp')
REG = (0.4295, -2.0, 5.0)                    # marked webp px = 0.4295 * plan PNG px + (-2, 5) (house-mask fit, 95 % score)

FLOOR_H, FLOORS, PLINTH = 2.8, 5, 0.5
GATE_MIN = 4.0                               # v10 §4: gates >= 4 m
BOX_W, BOX_D = 40.0, 33.0                    # v10 §7.4 football box, east edge on the plan, gaps shop-box ~6, box-H13 ~8
ROAD_W = 6.4                                 # drawn ring asphalt (32 SVG units) = v10 §6 rural asphalt
LAMP_STEP = 30.0                             # v10 §8: 25-35 m along the outer road
CAR = (4.0, 1.6, 1.45)
FACING = {'E': 0, 'N': 90, 'W': 180, 'S': 270}
OUTV = {'E': (1, 0), 'N': (0, 1), 'W': (-1, 0), 'S': (0, -1)}
# ---- W86 parameters
GROW = 0.05                                  # Fedya 22.10 item 3: ~2.5 % denser by smaller distances BETWEEN houses (long-axis growth, see grow_houses)
EDGE_RAY, MIN_GAP = 30.0, 8.0                # an end that sees the district edge within 30 m keeps its edge strip; >= 8 m left to the next building
ARCH_W, ARCH_H = 6.0, 4.5                    # Vadim 22.10: all arches about one size, van passes easily (brief: ~6 m clear, >= 4.5 m high)
G7_COURT = 10.5                              # coop 7: court between the two facing rows 13.0 -> 10.5 m ("чуть плотнее")
GB_PASS = 7.0                                # base-3 garages east end -> M6 wing west end (white strip ~6.6 m on the marked plan)
VAN = (5.5, 2.3)                             # check rectangle: van 5.5 x 2.1 m + 0.1 m a side
TURN_R = 6.0                                 # fillet radius of the van path at track corners (van turning circle ~11-12 m)
TRACK_W = {'T0': 4.5, 'T1': 4.0, 'T2': 3.5, 'T3': 3.5, 'T4': 3.5, 'T5': 4.0, 'T6': 3.5, 'T7': 4.0, 'T8': 3.5, 'T9': 3.5, 'T10': 3.5}
TRACK_NAME = {'T0': 'W-E through drive, stepped through A4 and A5 (main)', 'T1': 'from the south road at the box to the W-E drive',
              'T2': 'to base 3 (van spot)', 'T3': 'into yard 9', 'T4': 'between H7 and H56 (to coop 7 / H8)',
              'T5': 'left passage -> in front of the 12 garages at the north fence -> KPP road', 'T6': 'into yard 12 from the south',
              'T7': 'KPP road (asphalt end) -> north drive',
              'T8': 'W86 white strip: base-3 drive north past the base-3 garages to the W-E drive',
              'T9': 'W86 white strip: under coop 7 (between the garages and the new leg of E) -> corridor west of E -> T4',
              'T10': 'W86: around the north end of the lengthened W (yard 9 -> left passage; the W85 T4 piece is cut by M1)'}
# Vadim's red marks, measured on rough_v52_marked_by_vadim.webp (plan v52 metres): (id, host part, kind, rect, ru)
MARKS = [('M1', '04-Wa', 'extend_N', (73.26, 164.49, 87.10, 188.12), 'над аркой А4: дом над А4 (W) продлён на север'),
         ('M2', '04-Ef', 'extend_W', (153.97, 94.44, 187.69, 106.55), 'у арки А5: нижняя «нога» Г-дома E продлена на запад'),
         ('M3', '04-H9b', 'extend_S_wing_W', (253.12, 95.88, 294.05, 111.45), 'двор 12: правый дом H9 продлён вниз и загнут влево'),
         ('M4', '04-Ec', 'extend_W', (239.00, 69.65, 260.04, 83.20), 'над притоном 5: верхний дом продлён на запад'),
         ('M5', '04-H13', 'extend_W', (122.84, 68.50, 134.37, 77.15), 'над футбольной коробкой: дом H13 продлён на запад'),
         ('M6', '04-H14', 'wing_W_bottom', (74.99, 17.77, 100.07, 33.91), 'у трансформаторной будки: H14 внизу продлён на запад'),
         ('M7', '04-Ea', 'wing_E_bottom', (210.46, 95.31, 229.49, 112.31), 'НЕТ в списке промпта: справа от низа дома E у А5 — крыло на восток'),
         ('M8', '04-H14', 'extend_N', (99.20, 81.18, 111.88, 97.04), 'НЕТ в списке промпта: H14 продлён на север')]
WHITE = {'under_g7': (104.53, 109.00, 179.77, 111.30), 'base3': (64.47, 26.85, 71.10, 51.06)}     # white strips, plan v52 metres
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


def rgap(a, b):
    """Gap between two axis rects (0 if they touch / overlap)."""
    return math.hypot(max(b[0] - a[2], a[0] - b[2], 0.0), max(b[1] - a[3], a[1] - b[3], 0.0))


def rover(a, b):
    """Overlap area of two axis rects."""
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def grow(r, gx, gz=None):
    gz = gx if gz is None else gz
    return (r[0] - gx, r[1] - gz, r[2] + gx, r[3] + gz)


def rcen(r):
    return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)


def mvr(r, d):
    return (r[0] + d[0], r[1] + d[1], r[2] + d[0], r[3] + d[1])


def mvp(p, d):
    return (p[0] + d[0], p[1] + d[1])


def bbox(rs):
    return (min(r[0] for r in rs), min(r[1] for r in rs), max(r[2] for r in rs), max(r[3] for r in rs))


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


def sub_intervals(lo, hi, cuts, min_len=2.0):
    out = [(lo, hi)]
    for a, b in cuts:
        nxt = []
        for u, v in out:
            if b <= u or a >= v:
                nxt.append((u, v))
                continue
            if a > u:
                nxt.append((u, a))
            if b < v:
                nxt.append((b, v))
        out = nxt
    return [(u, v) for u, v in out if v - u >= min_len]


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


# ---------------------------------------------------------------- plan v52 in local metres
def load_plan(plan, ns, info, T):
    """Everything of plan v52 in plan metres (v52 frame), as mutable records (the W86 replanning edits them in place)."""
    M = info['M']
    OXm, OYm = info['origin_px']
    Pm = lambda x, y: ((x - OXm) * M, (OYm - y) * M)

    def Rm(r):
        a_, b_ = Pm(r[0], r[3]), Pm(r[2], r[1])
        return (a_[0], a_[1], b_[0], b_[1])
    HM = ns['HOUSES']
    L = {'M': M, 'LAWN': ns['LAWN_D'] * M, 'Pm': Pm, 'Rm': Rm, 'T': T}
    parts, err = [], 0.0
    for h in plan['houses']:
        for k, p in enumerate(h['parts']):
            r = (p['x0'], p['z0'], p['x1'], p['z1'])
            q = Rm(HM[h['id']]['C'][k])
            err = max(err, max(abs(a_ - b_) for a_, b_ in zip(r, q)))
            parts.append({'bid': '04-%s%s' % (h['id'], 'abcdefgh'[k] if len(h['parts']) > 1 else ''), 'hid': h['id'], 'rect': r})
    assert err < 0.02, 'build_rough_v52 model and Планировка_v52.json disagree (%.3f m)' % err
    L['parts'] = parts
    L['names'] = {h['id']: h['name'] for h in plan['houses']}
    pr = {p['bid']: p['rect'] for p in parts}
    arches = []
    for a in plan['arches']:
        aid = a['id'].replace(chr(0x410), 'A')                              # Cyrillic А1..А6 -> Latin A1..A6
        r = (a['rect']['x0'], a['rect']['z0'], a['rect']['x1'], a['rect']['z1'])
        c = rcen(r)
        host = [p['bid'] for p in parts if p['rect'][0] - 0.05 <= c[0] <= p['rect'][2] + 0.05 and p['rect'][1] - 0.05 <= c[1] <= p['rect'][3] + 0.05]
        arches.append({'id': aid, 'host': host[0] if host else None, 'rect': r, 'src': r, 'through': 'N-S' if host else 'W-E'})
    L['arches'] = arches
    pals = []                                                             # palisade = facade interval (lo, hi) along the facade axis
    for hid, h in HM.items():
        for side, ci, a_, b_, n, skip in h['doors']:
            dx, dy = h['d']
            bid = '04-%s%s' % (hid, 'abcdefgh'[ci] if len(h['C']) > 1 else '')
            if side in 'SN':
                lo, hi = sorted((Pm(a_ + dx, 0)[0], Pm(b_ + dx, 0)[0]))
            else:
                lo, hi = sorted((Pm(0, a_ + dy)[1], Pm(0, b_ + dy)[1]))
            pals.append({'bid': bid, 'side': side, 'lo': lo, 'hi': hi})
    L['pals'] = pals
    doors = []
    for i, dr in enumerate(plan['doors']):
        x, z = dr['pos']
        sd = dr['side']
        host = None
        for p in parts:
            q = p['rect']
            on = {'S': abs(z - q[1]) < 0.05, 'N': abs(z - q[3]) < 0.05, 'E': abs(x - q[2]) < 0.05, 'W': abs(x - q[0]) < 0.05}[sd]
            inr = q[0] - 0.05 <= x <= q[2] + 0.05 if sd in 'SN' else q[1] - 0.05 <= z <= q[3] + 0.05
            if on and inr:
                host = p['bid']
                break
        assert host, 'door %d not on a facade' % i
        doors.append({'i': i, 'host': host, 'side': sd, 'pos': [x, z], 'benches': dr['benches'], 'new': None})
    L['doors'] = doors

    def ggroup(r):
        if r[1] > 220:
            return 'GN'
        if r[0] > 290:
            return 'GNE'
        if r[2] < 75 and r[3] < 55:
            return 'GB'
        return 'G7'
    L['garages'] = [{'rect': (g['rect']['x0'], g['rect']['z0'], g['rect']['x1'], g['rect']['z1']), 'gate': g['gate'],
                     'group': ggroup((g['rect']['x0'], g['rect']['z0'], g['rect']['x1'], g['rect']['z1']))} for g in plan['garages']]
    O = {}
    O['shop'] = (plan['shop']['x0'], plan['shop']['z0'], plan['shop']['x1'], plan['shop']['z1'])
    dShop = ns['delta']((1176, 1622, 1404, 1703))
    O['kiosk1'], O['kiosk2'] = Rm(ns['mv']((1176, 1630, 1204, 1696), dShop)), Rm(ns['mv']((1376, 1630, 1404, 1696), dShop))
    O['booth1'], O['booth2'] = [(b['x0'], b['z0'], b['x1'], b['z1']) for b in plan['booths']]
    dE = HM['E']['d']
    club = (plan['club']['x0'], plan['club']['z0'], plan['club']['x1'], plan['club']['z1'])
    if club[0] < pr['04-Ed'][0]:
        club = (pr['04-Ed'][0], club[1], club[2], club[3])                 # the drawn club outline sticks 0.4 m out of the wall
    O['club'] = club
    O['canopy'] = Rm(ns['mv']((2034, 1320, 2051, 1382), dE))
    O['smokers'] = Rm(ns['mv']((1940, 1300, 2028, 1402), dE))
    gate = (plan['base_gate']['x0'], plan['base_gate']['z0'], plan['base_gate']['x1'], plan['base_gate']['z1'])
    if gate[2] - gate[0] < GATE_MIN:
        c = rcen(gate)
        fix(c, 'Ворота гаража базы 3 в Г-доме H17: проём %.2f -> %.1f м (ось та же)' % (gate[2] - gate[0], GATE_MIN),
            'v10 §4: ворота и арки — проём не меньше 4 м; на плане 3,84 м')
        gate = (c[0] - GATE_MIN / 2, gate[1], c[0] + GATE_MIN / 2, gate[3])
    O['gate'] = gate
    O['van'] = (plan['bus']['x0'], plan['bus']['z0'], plan['bus']['x1'], plan['bus']['z1'])
    O['b0'] = (plan['box']['x0'], plan['box']['z0'], plan['box']['x1'], plan['box']['z1'])
    L['O'] = O
    L['plays'] = [{'name': p['name'], 'key': 'yard12' if '12' in p['name'] else 'yard9',
                   'rect': (p['rect']['x0'], p['rect']['z0'], p['rect']['x1'], p['rect']['z1'])} for p in plan['playgrounds']]
    L['trashes'] = [{'name': t['name'], 'key': 'yard12' if '12' in t['name'] else 'yard9', 'open': t['open'],
                     'rect': (t['rect']['x0'], t['rect']['z0'], t['rect']['x1'], t['rect']['z1'])} for t in plan['trash']]
    kits = []
    for (n_, (sx, sy), w_, h_) in (('yard12', T(1930, 790), 230, 170), ('yard9', T(440, 395), 160, 120)):
        x0, y0, x1, y1 = sx - w_ / 2, sy - h_ / 2, sx + w_ / 2, sy + h_ / 2
        kit = [('swing_set', (x0 + 16, y0 + 12, x0 + 80, y0 + 34)), ('slide', (x1 - 74, y0 + 16, x1 - 14, y0 + 34)),
               ('sandbox', (sx - 32, y1 - 52, sx + 32, y1 - 12))]
        if w_ > 180:
            kit += [('roundabout', (x0 + 22, y1 - 56, x0 + 62, y1 - 16)), ('swing_set', (x1 - 80, y1 - 40, x1 - 20, y1 - 20))]
        kits += [{'key': n_, 'kind': kind, 'rect': Rm(r)} for kind, r in kit]
    L['kits'] = kits
    L['squares'] = []
    for (sx, sy, rx, ry), nm in (((1035, 1395, 34, 70), 'mini-square at the box (H14)'), ((2300, 1500, 70, 50), 'mini-square of yard 13')):
        L['squares'].append({'name': nm, 'c': Pm(*T(sx, sy)), 'rx': rx * M, 'rz': ry * M})
    L['pockets'] = [Pm(*T(*p)) for p in ((860, 690), (1440, 955), (2330, 470), (395, 1375), (870, 40))]
    L['trees'] = [tuple(t) for t in plan['trees']]
    L['cars'] = [{'pos': tuple(c['pos']), 'ang': 0 if c['along'] == 'W-E' else 90} for c in plan['cars']]
    L['turniks'] = [{'a': tuple(a), 'b': tuple(b)} for a, b in plan['turniks']]
    L['dist'] = [Pm(*T(*p)) for p in ns['DISTRICT']]
    return L


def ns_lawn(L):
    return L['LAWN']


def pr_of(L):
    return {p['bid']: p['rect'] for p in L['parts']}


def set_rect(L, bid, r):
    for p in L['parts']:
        if p['bid'] == bid:
            p['rect'] = tuple(r)
            return
    raise KeyError(bid)


# ---------------------------------------------------------------- W86 replanning (Vadim 22.10)
def grow_houses(L):
    """Grow each v52 house part along its long axis by GROW of its length, only at FREE ends: an end joined to another part of the same
    house (within 0.5 m) does not grow; an end whose outward ray reaches the district edge (fence / outer road) within EDGE_RAY m before any
    other building does not grow (edge strips stay as on v52); growth is capped so >= MIN_GAP m stays to the next building on the ray.
    If only one end is free it takes the whole growth. Nothing moves."""
    from common import inside
    pr = pr_of(L)
    hid_of = {p['bid']: p['hid'] for p in L['parts']}
    O = L['O']
    others = [(p['bid'], p['rect']) for p in L['parts']] + [('G', g['rect']) for g in L['garages']] +              [(k, O[k]) for k in ('shop', 'kiosk1', 'kiosk2', 'booth1', 'booth2', 'b0')]
    dist = L['dist']
    out = {}
    added = 0.0
    for p in L['parts']:
        r = p['rect']
        ax = 0 if r[2] - r[0] >= r[3] - r[1] else 1
        Ln = r[ax + 2] - r[ax]
        dep = r[3 - ax + (0 if ax else 0)] if False else (r[3] - r[1] if ax == 0 else r[2] - r[0])
        ends = {}
        for sgn in (-1, 1):
            e = r[ax] if sgn < 0 else r[ax + 2]
            sl = list(r)
            if sgn < 0:
                sl[ax + 2] = r[ax] + min(2.0, Ln / 4)
            else:
                sl[ax] = r[ax + 2] - min(2.0, Ln / 4)
            joined = any(hid_of[b] == p['hid'] and b != p['bid'] and rinter(tuple(sl), q, 0.5) for b, q in others if b in hid_of)
            if joined:
                ends[sgn] = ('joined', 0.0)
                continue
            lat0, lat1 = (r[1], r[3]) if ax == 0 else (r[0], r[2])
            hit = None
            for t in np.arange(0.5, EDGE_RAY + 40.0, 0.5):
                for f in (0.1, 0.5, 0.9):
                    lat = lat0 + (lat1 - lat0) * f
                    q = (e + sgn * t, lat) if ax == 0 else (lat, e + sgn * t)
                    if not inside(q, dist):
                        hit = hit or ('edge', t)
                    for b, rr in others:
                        if b != p['bid'] and rr[0] <= q[0] <= rr[2] and rr[1] <= q[1] <= rr[3]:
                            hit = hit or ('building ' + b, t)
                if hit:
                    break
            if hit and hit[0] == 'edge' and hit[1] <= EDGE_RAY:
                ends[sgn] = ('edge %.0f m' % hit[1], 0.0)
            else:
                cap = (hit[1] - MIN_GAP) if hit else 99.0
                ends[sgn] = ('free' + (' (%s at %.1f m)' % hit if hit else ''), max(0.0, cap))
        free = [k for k, v in ends.items() if v[0].startswith('free')]
        g = {}
        for k in free:
            g[k] = min(ends[k][1], GROW * Ln / len(free))
        nr = list(r)
        if -1 in g:
            nr[ax] -= g[-1]
        if 1 in g:
            nr[ax + 2] += g[1]
        for pl in L['pals']:                                              # palisades that reached a grown end follow it
            if pl['bid'] != p['bid'] or ((pl['side'] in 'SN') != (ax == 0)):
                continue
            if -1 in g and abs(pl['lo'] - r[ax]) < 0.6:
                pl['lo'] = nr[ax]
            if 1 in g and abs(pl['hi'] - r[ax + 2]) < 0.6:
                pl['hi'] = nr[ax + 2]
        p['rect'] = tuple(nr)
        added += sum(g.values()) * dep
        out[p['bid']] = {'axis': 'x' if ax == 0 else 'z', 'len_m': round(Ln, 2), 'grown_m': {('-' if k < 0 else '+'): round(v, 2) for k, v in g.items()},
                         'ends': {('lo' if k < 0 else 'hi'): v[0] for k, v in ends.items()}}
    area0 = sum((q[2] - q[0]) * (q[3] - q[1]) for q in pr.values())
    return {'rule': 'GROW %.3f of the long side per part at free ends; edge ray %.0f m; min gap %.0f m; no house moves' % (GROW, EDGE_RAY, MIN_GAP),
            'gross_added_area_m2': round(added), 'v52_area_m2': round(area0), 'gross_added_pct': round(100 * added / area0, 2),
            'net_note': 'gross includes growth later absorbed by the merges / red marks; A/B run 22.10 (GROW 0 vs 0.05): house area 19414 -> 19879 m2 '
                        '(+2.4 %), mean gap to the nearest other house 12.18 -> 10.74 m, median 11.40 -> 10.42 m', 'parts': out}


def replan_w86(L):
    """Edits L in place; returns a log dict for the checks / report."""
    LAWN = L['LAWN']
    log = {'growth': {}, 'marks': {}, 'arches': {}, 'g7': {}, 'gb': {}, 'moved_props': []}
    pr0 = pr_of(L)
    O = L['O']
    # ---- 1. denser WITHOUT moving houses (Fedya 22.10, item 3): every v52 house part grows along its long axis at its free ends
    #         (not at ends joined to another wing, not at ends that face the district edge -> edge strips stay as on v52)
    for a in L['arches']:
        a['v52'] = a['src']
    gl = grow_houses(L)
    log['growth'] = gl
    D = {g: (0.0, 0.0) for g in set(p['hid'] for p in L['parts']) | {'BOX', 'G7', 'GNE', 'GN', 'GB', 'Y9'}}
    L['D'] = D
    # ---- 2. continuous houses W and E (the A4 / A5 gaps are closed; the arches become real arches in them)
    pr = pr_of(L)
    wa, wb = pr['04-Wa'], pr['04-Wb']
    W_ = (wb[0], wb[1], wb[2], wa[3])
    ea, eb = pr['04-Ea'], pr['04-Eb']
    E_ = (eb[0], eb[1], eb[2], ea[3])
    L['parts'] = [p for p in L['parts'] if p['bid'] not in ('04-Wb', '04-Eb')]
    for p in L['parts']:
        if p['bid'] == '04-Wa':
            p['bid'], p['rect'] = '04-W', W_
        if p['bid'] == '04-Ea':
            p['rect'] = E_
    for dr in L['doors']:
        if dr['host'] in ('04-Wa', '04-Wb'):
            dr['host'], dr['pos'][0] = '04-W', W_[2]
        if dr['host'] in ('04-Ea', '04-Eb'):
            dr['host'], dr['pos'][0] = '04-Ea', E_[2]
    keep = []
    for p in L['pals']:
        if p['bid'] in ('04-Wb', '04-Eb'):
            continue
        if p['bid'] == '04-Wa':
            p['bid'], p['lo'], p['hi'] = '04-W', W_[1], W_[3]
        if p['bid'] == '04-Ea' and p['side'] == 'E':
            p['lo'], p['hi'] = eb[1] + (pr0['04-Ee'][3] - pr0['04-Eb'][1]), E_[3]          # from the top of Ee (as on the plan) to the top
        keep.append(p)
    L['pals'] = keep
    merged = {'W': (wa[1] - wb[3], W_[2] - W_[0]), 'E': (ea[1] - eb[3], E_[2] - E_[0])}
    # ---- 3. the 8 red marks (absolute plan v52 edges; D is zero since nothing moves)
    pr = pr_of(L)
    hostg = {'04-Wa': 'W', '04-Ef': 'E', '04-H9b': 'H9', '04-Ec': 'E', '04-H13': 'BOX', '04-H14': 'H14', '04-Ea': 'E'}
    newparts = []
    for mid, host, kind, r, ru in MARKS:
        m = mvr(r, D[hostg[host]])
        rec = {'kind': kind, 'host': host, 'ru': ru, 'mark_rect_local': [round(v, 2) for v in m], 'mark_rect_v52': list(r)}
        if kind == 'extend_N':
            bid = '04-W' if host == '04-Wa' else host
            q = pr[bid]
            set_rect(L, bid, (q[0], q[1], q[2], m[3]))
            rec.update(part=bid, added=(q[0], q[3], q[2], m[3]))
        elif kind == 'extend_W':
            q = pr[host]
            set_rect(L, host, (m[0], q[1], q[2], q[3]))
            rec.update(part=host, added=(m[0], q[1], q[0], q[3]))
        elif kind == 'extend_S_wing_W':                                   # M3: H9b down to the mark, then a wing west (house depth)
            q = pr[host]
            set_rect(L, host, (q[0], m[1], q[2], q[3]))
            wing = (m[0], m[1], q[0], q[1])
            newparts.append({'bid': '04-H9c', 'hid': 'H9', 'g': 'H9', 'rect': wing})
            rec.update(part=host, added=(q[0], m[1], q[2], q[1]), wing='04-H9c', wing_rect=wing)
        elif kind == 'wing_W_bottom':                                     # M6: wing west of H14 at its south end
            q = pr[host]
            wing = (m[0], q[1], q[0], m[3])
            newparts.append({'bid': '04-H14b', 'hid': 'H14', 'g': 'H14', 'rect': wing})
            rec.update(wing='04-H14b', wing_rect=wing, snapped='south face on H14 (mark %.1f m higher)' % (m[1] - q[1]))
        elif kind == 'wing_E_bottom':                                     # M7: wing east of E at the height of the leg
            q = pr['04-Ea']
            z0 = pr['04-Ef'][1]
            wing = (q[2], z0, m[2], m[3])
            newparts.append({'bid': '04-Eg', 'hid': 'E', 'g': 'E', 'rect': wing})
            rec.update(wing='04-Eg', wing_rect=wing, snapped='south face on the leg line (mark %.1f m higher)' % (m[1] - z0))
        pr = pr_of(L)
        log['marks'][mid] = rec
    L['parts'] += newparts
    pr = pr_of(L)
    # palisades of the lengthened / new pieces (podyezd side of the host house)
    for p in L['pals']:
        q = pr[p['bid']]
        if p['bid'] == '04-W' and p['side'] == 'E':
            p['hi'] = q[3]
        if p['bid'] == '04-Ef' and p['side'] == 'N':
            p['lo'] = q[0]
        if p['bid'] == '04-Ec' and p['side'] == 'S':
            p['lo'] = q[0]
        if p['bid'] == '04-H13' and p['side'] == 'S':
            p['lo'] = q[0]
        if p['bid'] == '04-H14' and p['side'] == 'E':
            p['hi'] = q[3]
    L['pals'] += [{'bid': '04-H9c', 'side': 'N', 'lo': pr['04-H9c'][0], 'hi': pr['04-H9c'][2]},
                  {'bid': '04-H14b', 'side': 'N', 'lo': pr['04-H14b'][0], 'hi': pr['04-H14b'][2]},
                  {'bid': '04-Eg', 'side': 'E', 'lo': pr['04-Eg'][1], 'hi': pr['04-Eg'][3]}]
    W_, E_ = pr['04-W'], pr['04-Ea']
    fix(rcen(W_), 'Блок W — один сплошной дом %.1f м (два корпуса и разрыв %.1f м под А4 закрыты, плюс отметка M1); ширина корпуса %.2f м — по нижнему корпусу'
        % (W_[3] - W_[1], merged['W'][0], merged['W'][1]), 'Вадим 22.10: арки — настоящие арки под сплошным домом, а не «дыра между домами»')
    fix(rcen(E_), 'Вертикаль блока E — один сплошной дом %.1f м (разрыв %.1f м под А5 закрыт); ширина %.2f м' % (E_[3] - E_[1], merged['E'][0], merged['E'][1]),
        'то же: А5 — арка в сплошном доме')
    for mid, rec in log['marks'].items():
        a_ = rec.get('added') or rec.get('wing_rect')
        what = []
        if 'part' in rec:
            what.append('продлён дом %s на %.1f x %.1f м' % (rec['part'], rec['added'][2] - rec['added'][0], rec['added'][3] - rec['added'][1]))
        if 'wing' in rec:
            wr = rec['wing_rect']
            what.append('новое крыло %s %.1f x %.1f м' % (rec['wing'], wr[2] - wr[0], wr[3] - wr[1]))
        fix(rcen(a_), 'Отметка Вадима %s (%s): %s; этажность, фасад, крыша — как у дома; подъезды и палисадник на стороне подъездов дома'
            % (mid, rec['ru'], ' + '.join(what)), 'красный прямоугольник = достроить существующий дом до его границы (промпт Вадима 22.10)')
    # ---- 4. arches: one size, real arches in continuous houses
    pr = pr_of(L)
    W_, E_ = pr['04-W'], pr['04-Ea']
    zA4 = rcen([a for a in L['arches'] if a['id'] == 'A4'][0]['src'])[1]
    up = min(pr['04-Ef'][1], pr['04-Eg'][1], pr['04-H9c'][1], pr['04-H9b'][1])
    zA5 = (pr['04-Ec'][3] + up) / 2.0                                     # the W-E drive east of A5 runs between Ec (+M4) and the new wings
    for a in L['arches']:
        old = a['src']
        if a['id'] == 'A4':
            a['host'], a['through'], a['rect'] = '04-W', 'W-E', (W_[0], zA4 - ARCH_W / 2, W_[2], zA4 + ARCH_W / 2)
        elif a['id'] == 'A5':
            a['host'], a['through'], a['rect'] = '04-Ea', 'W-E', (E_[0], zA5 - ARCH_W / 2, E_[2], zA5 + ARCH_W / 2)
        else:
            q = pr[a['host']]
            cx = rcen(old)[0]
            a['rect'] = (cx - ARCH_W / 2, q[1], cx + ARCH_W / 2, q[3])        # full depth of the host (A3 was short on the plan)
            a['through'] = 'N-S'
        a['clear_w'] = ARCH_W
        ow = (old[3] - old[1]) if a['id'] in ('A4', 'A5') else (old[2] - old[0])
        log['arches'][a['id']] = {'v52_rect': [round(v, 2) for v in a['v52']], 'old_clear_w_m': round(ow, 2), 'new_clear_w_m': ARCH_W, 'clear_h_m': ARCH_H, 'host': a['host'],
                                  'through': a['through'], 'passage_len_m': round((a['rect'][2] - a['rect'][0]) if a['through'] == 'W-E' else (a['rect'][3] - a['rect'][1]), 2)}
    fix(rcen(E_), 'Все 6 арок одного размера: проём %.1f м, высота %.1f м (было: А1 7,3, А2 6,7, А3 9,3 (и не на всю глубину), А4 13,1, А5 13,9, А6 6,7 м). '
        'А4 и А5 — в сплошных домах W и E; А5 по высоте посередине между верхним домом притона (Ec) и новыми крыльями: ось z %.1f м плана (была %.1f)'
        % (ARCH_W, ARCH_H, zA5, rcen([a for a in L['arches'] if a['id'] == 'A5'][0]['src'])[1]),
        'Вадим 22.10: арки примерно одинаковые, бусик спокойно проезжает (бусик 5,5 x 2,1 м)')
    # ---- 5. coop 7: court tighter, block raised -> equal passages under (white strip) and over it
    g7 = [g for g in L['garages'] if g['group'] == 'G7']
    rowS = [g for g in g7 if g['gate'] == 'S']
    rowN = [g for g in g7 if g['gate'] == 'N']
    court0 = min(g['rect'][1] for g in rowS) - max(g['rect'][3] for g in rowN)
    dz = (court0 - G7_COURT) / 2
    for g in rowS:
        g['rect'] = mvr(g['rect'], (0, -dz))
    for g in rowN:
        g['rect'] = mvr(g['rect'], (0, dz))
    b7 = bbox([g['rect'] for g in g7])
    below = pr['04-Ef'][3] + LAWN                                         # N palisade of the lengthened leg of E
    above = pr['04-H7'][1] - LAWN                                         # S palisade of H7
    free = above - below - (b7[3] - b7[1])
    sh = below + free / 2 - b7[1]
    for g in g7:
        g['rect'] = mvr(g['rect'], (0, sh))
    b7 = bbox([g['rect'] for g in g7])
    log['g7'] = {'court_m': [round(court0, 2), G7_COURT], 'raised_m': round(sh, 2), 'passage_under_m': round(b7[1] - below, 2),
                 'passage_over_m': round(above - b7[3], 2), 'block': [round(v, 2) for v in b7]}
    fix(rcen(b7), 'Гаражи 7: проезд между рядами %.1f -> %.1f м, весь блок поднят на %.1f м: под ним (до палисадника новой «ноги» E) %.1f м, над ним (до палисадника H7) %.1f м'
        % (court0, G7_COURT, sh, b7[1] - below, above - b7[3]),
        'Вадим 22.10: гаражи чуть выше и плотнее, бусик проезжает и над, и под ними, впритык (белая полоса под гаражами)')
    # ---- 6. base-3 garages: free the white strip east of them
    gb = [g for g in L['garages'] if g['group'] == 'GB']
    x1 = max(g['rect'][2] for g in gb)
    need = min(pr['04-H14b'][0] - GB_PASS, WHITE['base3'][0])              # the white strip itself must be free (it covers the L's east end)
    s = max(0.0, x1 - need)
    for g in gb:
        g['rect'] = mvr(g['rect'], (-s, 0))
    row = sorted([g for g in gb if g['gate'] == 'S'], key=lambda g: g['rect'][0])
    pair = [g for g in gb if g['gate'] == 'W']
    px0 = min(g['rect'][0] for g in pair)
    for g in row:
        r = g['rect']
        cx = rcen(r)[0]
        if r[2] > px0 + 0.05 and abs(r[1] - max(q['rect'][3] for q in pair)) < 0.1:
            new = 'E' if g is row[-1] else 'N'
            fix((cx, r[1]), 'Угловой гараж Г базы 3 (x %.1f…%.1f м): ворота %s вместо S — на плане его южные ворота упираются в крышу пары гаражей (артефакт рисунка)%s'
                % (r[0], r[2], new, ', теперь открываются на новый проезд (белая полоса)' if new == 'E' else ', теперь открываются на пустырь к северу'),
                'ворота гаража не должны упираться в соседний гараж')
            g['gate'] = new
    log['gb'] = {'shift_west_m': round(s, 2), 'passage_m': round(pr['04-H14b'][0] - max(g['rect'][2] for g in gb), 2),
                 'yard_w_m': round(min(g['rect'][0] for g in gb if g['gate'] == 'W') - (pr['04-H17a'][2] + LAWN), 2)}
    fix((need, rcen(bbox([g['rect'] for g in gb]))[1]), 'Гаражи базы 3 (Г из 5 + 2) сдвинуты на %.1f м на запад: между ними и новым крылом H14 (отметка M6) проезд %.1f м — белая полоса Вадима'
        % (s, log['gb']['passage_m']), 'Федя 22.10: освободить место у гаражей и поставить их так, чтобы там проезжал бусик')
    # ---- 7. props the new pieces would block
    pal_n = lambda bid: pr[bid][3] + LAWN
    b1 = O['booth1']
    if rinter(b1, (pr['04-H9c'][0], pr['04-H9c'][3], pr['04-H9c'][2], pal_n('04-H9c')), 0.3):
        O['booth1'] = mvr(b1, (0, pal_n('04-H9c') + 0.8 - b1[1]))
        log['moved_props'].append('booth1')
        fix(rcen(O['booth1']), 'Трансформаторная будка двора 12 сдвинута на %.1f м на север — на её месте палисадник нового крыла H9c' % (O['booth1'][1] - b1[1]),
            'ничего не должно стоять в палисаднике и у входа (промпт Вадима)')
    b2 = O['booth2']
    if rinter(b2, (pr['04-H14b'][0], pr['04-H14b'][3], pr['04-H14b'][2], pal_n('04-H14b')), 0.3):
        O['booth2'] = mvr(b2, (0, pal_n('04-H14b') + 0.8 - b2[1]))
        log['moved_props'].append('booth2')
        fix(rcen(O['booth2']), 'Трансформаторная будка у H14 сдвинута на %.1f м на север — вплотную к ней теперь крыло H14b с палисадником' % (O['booth2'][1] - b2[1]),
            'то же')
    t2 = L['turniks'][1]
    eg = pr['04-Eg']
    if rinter((min(t2['a'][0], t2['b'][0]), t2['a'][1] - 0.3, max(t2['a'][0], t2['b'][0]), t2['a'][1] + 0.3), grow(eg, LAWN), 0):
        z = eg[3] + 2.5
        L['turniks'][1] = {'a': (t2['a'][0], z), 'b': (t2['b'][0], z)}
        log['moved_props'].append('turnik2')
        fix((t2['a'][0], z), 'Турник 2 перенесён на %.1f м севернее, к краю двора 12 — на его месте крыло Eg (отметка M7)' % (z - t2['a'][1]), 'то же')
    return log


def add_doors_w86(L, log):
    """Podyezds on the new pieces, spaced like the rest of the host house, clear of arches, wings and props."""
    pr = pr_of(L)
    LAWN = L['LAWN']
    props = [L['O']['booth1'], L['O']['booth2']]
    spacing = {}
    hid_of = {p['bid']: p['hid'] for p in L['parts']}
    for hid in set(p['hid'] for p in L['parts']):
        ps = []
        for bid_side in set((d['host'], d['side']) for d in L['doors'] if hid_of.get(d['host']) == hid):
            v = sorted(d['pos'][0] if d['side'] in 'SN' else d['pos'][1] for d in L['doors'] if (d['host'], d['side']) == bid_side)
            ps += [b - a for a, b in zip(v[:-1], v[1:]) if b - a > 8]
        spacing[hid] = float(np.median(ps)) if ps else 22.0
    pieces = []                                                           # (mark, part, side, lo, hi)
    for mid, rec in log['marks'].items():
        if 'part' in rec:
            a_ = rec['added']
            bid = rec['part']
            side = [p['side'] for p in L['pals'] if p['bid'] == bid][0]
            lo, hi = (a_[0], a_[2]) if side in 'SN' else (a_[1], a_[3])
            pieces.append((mid, bid, side, lo, hi))
        if 'wing' in rec:
            bid = rec['wing']
            side = [p['side'] for p in L['pals'] if p['bid'] == bid][0]
            q = pr[bid]
            lo, hi = (q[0], q[2]) if side in 'SN' else (q[1], q[3])
            pieces.append((mid, bid, side, lo, hi))
    added = []
    for mid, bid, side, lo, hi in pieces:
        if hi - lo < 8.0:
            continue
        hid = [p['hid'] for p in L['parts'] if p['bid'] == bid][0]
        n = max(1, int(round((hi - lo) / spacing[hid])))
        q = pr[bid]
        for k in range(n):
            t0 = lo + (hi - lo) * (k + 0.5) / n
            best = None
            for dt in sorted(np.arange(-(hi - lo) / 2, (hi - lo) / 2 + 0.01, 0.25), key=abs):
                t = t0 + dt
                if t < lo + 3.0 or t > hi - 3.0:
                    continue
                pos = {'S': (t, q[1]), 'N': (t, q[3]), 'E': (q[2], t), 'W': (q[0], t)}[side]
                pth = path_rect({'pos': pos, 'side': side}, LAWN)
                front = grow(pth, 1.6) if side in 'SN' else grow(pth, 1.6)
                ext = {'S': (pth[0], pth[1] - 3.0, pth[2], pth[1]), 'N': (pth[0], pth[3], pth[2], pth[3] + 3.0),
                       'E': (pth[2], pth[1], pth[2] + 3.0, pth[3]), 'W': (pth[0] - 3.0, pth[1], pth[0], pth[3])}[side]
                if any(rinter(front, r) for r in props) or any(rinter(ext, r) for r in props):
                    continue
                if any(rinter(pth, p['rect'], -0.01) for p in L['parts'] if p['bid'] != bid):
                    continue
                other = [d for d in L['doors'] if d['host'] == bid and d['side'] == side]
                if any(abs((d['pos'][0] if side in 'SN' else d['pos'][1]) - t) < 9.0 for d in other):
                    continue
                if any(a['host'] == bid and abs(t - (rcen(a['rect'])[0] if side in 'SN' else rcen(a['rect'])[1])) < ARCH_W / 2 + 4.0 for a in L['arches']):
                    continue
                best = pos
                break
            if best is None:
                continue
            nb = 1 + int(h01('w86bench' + bid + str(k)) > 0.45)
            d = {'i': None, 'host': bid, 'side': side, 'pos': [best[0], best[1]], 'benches': nb, 'new': mid}
            L['doors'].append(d)
            added.append((mid, bid, side, [round(best[0], 2), round(best[1], 2)], nb))
    log['new_doors'] = added
    for mid, bid, side, pos, nb in added:
        fix(tuple(pos), 'Новый подъезд у достроенного куска (%s, %s, фасад %s): дверь, козырёк, дорожка через палисадник, лавочек %d + урна' % (mid, bid, side, nb),
            'промпт Вадима: у нового куска подъезды, палисадники, лавочки, урны, фонари — как у остального дома')


def path_rect(d, LAWN):
    x, z = d['pos']
    return {'S': (x - 1.6, z - LAWN, x + 1.6, z), 'N': (x - 1.6, z, x + 1.6, z + LAWN),
            'E': (x, z - 1.6, x + LAWN, z + 1.6), 'W': (x - LAWN, z - 1.6, x, z + 1.6)}[d['side']]


def pal_rect(p, pr, LAWN):
    q = pr[p['bid']]
    lo, hi = p['lo'], p['hi']
    return {'S': (lo, q[1] - LAWN, hi, q[1]), 'N': (lo, q[3], hi, q[3] + LAWN), 'E': (q[2], lo, q[2] + LAWN, hi), 'W': (q[0] - LAWN, lo, q[0], hi)}[p['side']]


def pal_pieces(L, p):
    """Palisade p minus other parts that touch it and minus arch mouths on this facade."""
    pr = pr_of(L)
    r = pal_rect(p, pr, L['LAWN'])
    ax = 0 if p['side'] in 'SN' else 1
    cuts = [(q[ax], q[ax + 2]) for b, q in pr.items() if b != p['bid'] and rinter(r, q, 0.0)]
    for a in L['arches']:
        if a['host'] == p['bid'] and ((a['through'] == 'N-S') == (p['side'] in 'SN')):
            cuts.append((a['rect'][ax], a['rect'][ax + 2]))
    out = []
    for u, v in sub_intervals(p['lo'], p['hi'], cuts):
        out.append((u, r[1], v, r[3]) if ax == 0 else (r[0], u, r[2], v))
    return out


# ---------------------------------------------------------------- tracks from the new geometry
def tracks_w86(L, hz, kx, kz0, xe):
    pr = pr_of(L)
    LAWN = L['LAWN']
    arch = {a['id']: a for a in L['arches']}
    W_, Ea, Ef, H3, H14, H14b, H13 = pr['04-W'], pr['04-Ea'], pr['04-Ef'], pr['04-H3'], pr['04-H14'], pr['04-H14b'], pr['04-H13']
    H7, H56a, H56b, H1a, H9c, Eg = pr['04-H7'], pr['04-H56a'], pr['04-H56b'], pr['04-H1a'], pr['04-H9c'], pr['04-Eg']
    g7 = [g['rect'] for g in L['garages'] if g['group'] == 'G7']
    gn = [g['rect'] for g in L['garages'] if g['group'] == 'GN']
    zA4, zA5 = rcen(arch['A4']['rect'])[1], rcen(arch['A5']['rect'])[1]
    h11top = max(pr[b][3] for b in pr if b.startswith('04-H11'))
    z_h = (h11top + H3[1] - LAWN) / 2                                     # between the top of H11 and the S palisade of H3
    x_a = W_[0] - 8.5                                                     # turn into A4 with room for a van (v52: 8.6 m)
    x_w = W_[2] + LAWN + 0.6 + TRACK_W['T0'] / 2                           # east of the W palisade
    g7b = min(r[1] for r in g7)
    z_r1 = (H14[3] + g7b) / 2
    x_s = Ef[0] - 6.0                                                     # step down just west of the lengthened leg (v52: 5.8 m)
    T = {}
    T['T0'] = [(20.0, hz)] + ([(24.0, z_h)] if abs(z_h - hz) > 0.3 else []) + [(x_a, z_h), (x_a, zA4), (x_w, zA4), (x_w, z_r1), (x_s, z_r1),
                                                                            (x_s, zA5), (xe, zA5)]
    x_t1 = (H13[2] + Ea[0]) / 2
    T['T1'] = [(x_t1, 0.0), (x_t1, zA5)]
    gbx1 = max(g['rect'][2] for g in L['garages'] if g['group'] == 'GB')
    x_t2 = (gbx1 + min(H14b[0], W_[0])) / 2                               # middle of the freed passage (white strip) east of the base-3 garages
    van = L['O']['van']
    z_vs = L['t2_turn_z']
    T['T2'] = [(x_t2, 0.0), (x_t2, z_vs), (van[2] - 0.66, z_vs)]
    z3 = H1a[1] - LAWN - TRACK_W['T3'] / 2 - 0.3
    T['T3'] = [(x_a, zA4), (x_a, z3)]
    z4 = (H7[3] + H56b[1] - LAWN) / 2
    x5 = W_[2] + LAWN + 0.6 + TRACK_W['T5'] / 2
    x4e = Ea[0] - TRACK_W['T4'] / 2 - 0.5
    T['T4'] = [(x5, z4), (x4e, z4)]
    z5 = (H56a[3] + min(r[1] for r in gn)) / 2
    T['T5'] = [(x5, z4), (x5, z5), (kx, z5)]
    plays12 = [p['rect'] for p in L['plays'] if p['key'] == 'yard12'][0]
    x6 = (Eg[2] + LAWN + H9c[0]) / 2
    T['T6'] = [(x6, zA5), (x6, plays12[1] - 2.5)]
    T['T7'] = [(kx, z5), (kx, kz0)]
    T['T8'] = [(x_t2, z_vs), (x_t2, z_h), (x_a, z_h)]
    z9 = (Ef[3] + LAWN + g7b) / 2
    x9e = (H7[2] + Ea[0]) / 2
    T['T9'] = [(x_s, z_r1), (x_s + 4.0, z9), (x9e, z9), (x9e, z4)]
    z10 = (W_[3] + H1a[1] - LAWN) / 2
    T['T10'] = [(x_a, z10), (x5, z10)]
    return {k: [(round(x, 3), round(z, 3)) for x, z in v] for k, v in T.items()}, {'zA4': zA4, 'zA5': zA5, 'x_s': x_s, 'z_r1': z_r1, 'z9': z9}


# ---------------------------------------------------------------- van checks (grid search + rectangle sweep)
class Grid:
    def __init__(self, x0=-16.0, z0=-10.0, x1=335.0, z1=240.0, res=0.25):
        self.x0, self.z0, self.res = x0, z0, res
        self.nx, self.nz = int((x1 - x0) / res), int((z1 - z0) / res)
        self.occ = np.zeros((self.nz, self.nx), bool)
        self.allow = np.zeros((self.nz, self.nx), bool)

    def ij(self, x, z):
        return int((z - self.z0) / self.res), int((x - self.x0) / self.res)

    def rect(self, r, arr=None, val=True):
        arr = self.occ if arr is None else arr
        i0, j0 = self.ij(r[0], r[1])
        i1, j1 = self.ij(r[2], r[3])
        arr[max(0, i0):max(0, i1 + 1), max(0, j0):max(0, j1 + 1)] = val

    def disc(self, p, rad):
        i, j = self.ij(*p)
        k = int(math.ceil(rad / self.res)) + 1
        for di in range(-k, k + 1):
            for dj in range(-k, k + 1):
                if (di * di + dj * dj) * self.res * self.res <= rad * rad and 0 <= i + di < self.nz and 0 <= j + dj < self.nx:
                    self.occ[i + di, j + dj] = True

    def line(self, pl, half):
        for q in samples(pl, self.res):
            self.rect((q[0] - half, q[1] - half, q[0] + half, q[1] + half))

    def poly_allow(self, poly):
        im = Image.new('L', (self.nx, self.nz), 0)
        ImageDraw.Draw(im).polygon([((x - self.x0) / self.res, (z - self.z0) / self.res) for x, z in poly], fill=255)
        self.allow |= np.asarray(im) > 0


def van_paths(pl, R=TURN_R, step=0.25):
    """Poses (x, z, heading) along a polyline with circular fillets (radius <= R) at the corners."""
    pts = [np.array(p, float) for p in pl]
    segs = []
    for a, b in zip(pts[:-1], pts[1:]):
        L_ = np.linalg.norm(b - a)
        if L_ > 1e-6:
            segs.append((a, b, (b - a) / L_, L_))
    if not segs:
        return []
    cut = [0.0] * (len(segs) + 1)
    fil = []
    for k in range(len(segs) - 1):
        u1, u2 = segs[k][2], segs[k + 1][2]
        th = math.acos(max(-1.0, min(1.0, float(u1 @ u2))))
        if th < 1e-3:
            fil.append(None)
            continue
        t = math.tan(th / 2)
        r = min(R, 0.49 * segs[k][3] / t, 0.49 * segs[k + 1][3] / t)
        cut[k + 1] = r * t
        fil.append((r, th))
    poses = []
    for k, (a, b, u, L_) in enumerate(segs):
        s0 = cut[k] if k > 0 else 0.0
        s1 = L_ - (cut[k + 1] if k < len(segs) - 1 else 0.0)
        for s in np.arange(s0, s1 + 1e-6, step):
            p = a + u * s
            poses.append((p[0], p[1], math.atan2(u[1], u[0])))
        if k < len(segs) - 1 and fil[k]:
            r, th = fil[k]
            u2 = segs[k + 1][2]
            cross = u[0] * u2[1] - u[1] * u2[0]
            nrm = np.array([-u[1], u[0]]) * (1 if cross > 0 else -1)
            start = b - u * cut[k + 1]
            cen = start + nrm * r
            a0 = math.atan2(start[1] - cen[1], start[0] - cen[0])
            n = max(2, int(r * th / step))
            for i in range(1, n):
                ang = a0 + (th * i / n) * (1 if cross > 0 else -1)
                p = cen + r * np.array([math.cos(ang), math.sin(ang)])
                hd = math.atan2(u[1], u[0]) + (th * i / n) * (1 if cross > 0 else -1)
                poses.append((p[0], p[1], hd))
    return poses


def sweep(G, dist, poses, size=VAN):
    """Min clearance (m) of a size[0] x size[1] rectangle along the poses: EDT of obstacles sampled over the rectangle."""
    if not poses:
        return None, None
    l2, w2 = size[0] / 2, size[1] / 2
    us = np.arange(-l2, l2 + 1e-6, G.res)
    vs = np.arange(-w2, w2 + 1e-6, G.res)
    U, V = np.meshgrid(us, vs)
    U, V = U.ravel(), V.ravel()
    best = (99.0, None)
    for x, z, h in poses:
        c, s = math.cos(h), math.sin(h)
        X = x + U * c - V * s
        Z = z + U * s + V * c
        i = ((Z - G.z0) / G.res).astype(int)
        j = ((X - G.x0) / G.res).astype(int)
        ok = (i >= 0) & (i < G.nz) & (j >= 0) & (j < G.nx)
        if not ok.all():
            continue
        v = float(dist[i, j].min())
        if v < best[0]:
            best = (v, (round(x, 1), round(z, 1)))
    return best


def van_checks(L, solid, pals, small, fences, road_lines, east_leg, kpp_line, trk, targets):
    """Obstacle raster -> (1) widest-path search from the south road to every target, (2) rectangle sweep along tracks and arches."""
    G = Grid()
    G.poly_allow(L['dist'])
    for pl, w in road_lines:
        G.poly_allow(buffer_line(pl, w / 2, cap=False))
    G.poly_allow(buffer_line(east_leg, ROAD_W / 2, cap=False))
    G.poly_allow(buffer_line(kpp_line, ROAD_W / 2, cap=False))
    for n_, r in solid:
        G.rect(r)
    for r in pals:
        G.rect(r)
    for kind, v in small:
        if kind == 'disc':
            G.disc(v[0], v[1])
        else:
            G.rect(v)
    for pl in fences:
        G.line(pl, 0.15)
    occ = G.occ | ~G.allow
    dist = ndimage.distance_transform_edt(~occ) * G.res                    # distance (m) from every free cell to the nearest obstacle
    # (1) widest path from the south road
    src = G.ij(150.0, 0.0)
    widths = [2.3, 2.6, 3.0, 3.5, 4.0, 5.0, 6.0]
    comps = {}
    for w in widths:
        lab, n = ndimage.label(dist >= w / 2)
        comps[w] = (lab, lab[src])
    res = {}
    for name, p in targets:
        i, j = G.ij(*p)
        k = int((3.5 if name.startswith('door') else 2.0) / G.res)
        best = 0.0
        for w in widths:
            lab, l0 = comps[w]
            win = lab[max(0, i - k):i + k + 1, max(0, j - k):j + k + 1]
            if l0 and (win == l0).any():
                best = w
        res[name] = best
    # (2) sweeps
    sw = {}
    trim = int(math.ceil(VAN[0] / 2 / G.res)) + 1                         # the van centre stays half a van inside the track ends
    for k_, pl in trk.items():
        v, where = sweep(G, dist, van_paths(pl)[trim:-trim])
        sw[k_] = {'min_clearance_m': round(v, 2) if v is not None else None, 'at': where}
    return G, dist, res, sw


# ---------------------------------------------------------------- build
def build():
    svg = svg_text()
    P, Pinv, info, plan, T = load_chain(svg)
    ns = plan_model()
    M = info['M']
    L = load_plan(plan, ns, info, T)
    LAWN = L['LAWN']
    Pm = L['Pm']
    L['t2_turn_z'] = plan['tracks'][2][1][1]
    v52 = json.loads(json.dumps({'parts': [dict(p) for p in L['parts']], 'garages': [dict(g) for g in L['garages']]}))   # for the images
    log = replan_w86(L)
    L['t2_turn_z'] += L['D']['H17'][1]
    add_doors_w86(L, log)
    W = lambda p: rnd2(P(p[0], p[1]))
    WR = lambda r: [W(q) for q in rpoly(r)]
    WL = lambda pl: [W(q) for q in pl]
    world = svg_world(svg)
    pr = pr_of(L)
    O = L['O']
    shop, kiosks, booths, club, canopy, smokers, gate, van, b0 = (O['shop'], [O['kiosk1'], O['kiosk2']], [O['booth1'], O['booth2']], O['club'],
                                                                 O['canopy'], O['smokers'], O['gate'], O['van'], O['b0'])
    parts = [(p['bid'], p['hid'], p['rect']) for p in L['parts']]
    names = L['names']
    arches = L['arches']
    arch_by_host = {}
    for a in arches:
        arch_by_host.setdefault(a['host'], []).append(a)
    doors = L['doors']
    for d in doors:                                                       # a door path must not run into another wing
        for b, _, q in parts:
            if b == d['host']:
                continue
            if rinter(path_rect(d, LAWN), q, -0.01):
                ax = 0 if d['side'] in 'SN' else 1
                old = d['pos'][ax]
                d['pos'][ax] = (q[ax] - 1.6 - 1.3) if old < rcen(q)[ax] else (q[ax + 2] + 1.6 + 1.3)
                fix(tuple(d['pos']), 'Подъезд %s (дверь %s) сдвинут вдоль фасада с %.2f на %.2f м плана — дорожка упиралась в %s'
                    % (d['host'], d['i'] if d['i'] is not None else d['new'], old, d['pos'][ax], b),
                    'козырёк, ступени и дорожка через палисадник не должны упираться в стену соседнего корпуса')
    for d in doors:                                                       # ... nor into the palisade of another facade (inner corners)
        for p in L['pals']:
            if p['bid'] == d['host'] and p['side'] == d['side']:
                continue
            q = pal_rect(p, pr, LAWN)
            pth = path_rect(d, LAWN)
            if rover(pth, q) > 0.3:
                ax = 0 if d['side'] in 'SN' else 1
                old = d['pos'][ax]
                d['pos'][ax] = (q[ax] - 1.6 - 0.3) if old < rcen(q)[ax] else (q[ax + 2] + 1.6 + 0.3)
                fix(tuple(d['pos']), 'Подъезд %s (дверь %s) сдвинут вдоль фасада с %.2f на %.2f м плана — дорожка выходила в палисадник соседнего крыла (%s %s)'
                    % (d['host'], d['i'] if d['i'] is not None else d['new'], old, d['pos'][ax], p['bid'], p['side']),
                    'дорожка от подъезда должна выходить на проезд, а не в чужой газон (внутренний угол П-дома)')
    pals = L['pals']
    pal_pcs = [(p, pal_pieces(L, p)) for p in pals]
    pal_all = [q for p, ps in pal_pcs for q in ps]
    garages = L['garages']
    plays = [(p['name'], p['rect']) for p in L['plays']]
    trashes = [(t['name'], t['rect'], t['open']) for t in L['trashes']]
    h13 = pr['04-H13']
    free = h13[1] - shop[3]
    gap_s = (free - BOX_D) * 6.0 / 14.0                                   # 6 : 8 split of what is left (v10: ~6 and ~8)
    box = (b0[2] - BOX_W, shop[3] + gap_s, b0[2], shop[3] + gap_s + BOX_D)
    fix(rcen(box), 'Футбольная коробка %.1f x %.1f м (на плане нарисована %.1f x %.1f), восточный край на месте; зазоры магазин–коробка %.1f м, коробка–H13 %.1f м'
        % (BOX_W, BOX_D, b0[2] - b0[0], b0[3] - b0[1], box[1] - shop[3], h13[1] - box[3]),
        'v10 §7.4: коробка 40 x 33, зазоры ~6 и ~8 м; магазин, коробка и H13 сжимаются как одна группа, чтобы эти зазоры остались')
    squares = [(s['name'], s['c'], s['rx'], s['rz']) for s in L['squares']]
    wz1 = box[3] - 1.0                                                    # Fedya 22.10 item 6: wicket on the WEST short side, at its north end
    wz0 = wz1 - 48 * M
    appr = (box[0] - 12.0, wz0 - 1.0, box[0], wz1 + 1.0)

    # ------------------------------------------------ roads: v85 drawn ring + hook, plan east leg, exits, KPP road (world-fixed)
    ring = world['ring']
    hook = road_starting(world['roads'], (686.0, 788.0))                  # ROAD_RING of build_world_v85: entry -> west side of the ring
    hz_drawn = Pinv(*hook[0])[1]
    pal_h3 = [r for p, ps in pal_pcs if p['bid'] == '04-H3' for r in ps]
    pal_h3_z0 = min(r[1] for r in pal_h3)
    hz = min(hz_drawn, pal_h3_z0 - 1.3 - ROAD_W / 2)
    if hz < hz_drawn - 0.05:
        fix((10.0, hz), 'Асфальтовый заезд с западной стороны кольца (в начало сквозного проезда) сдвинут на %.1f м южнее: ось y %.1f -> %.1f мира'
            % (hz_drawn - hz, hook[0][1], P(0, hz)[1]),
            'на карте v85 асфальт шириной 6,4 м заходит на палисадник дома 10 (H3); теперь 1,3 м до газона')
    west_x = Pinv(*ring[3])[0]
    road = [(20.0, hz), (west_x, hz)] + [Pinv(*p) for p in ring if p[1] < 677.5 and p[0] <= 1000.0]
    road = [(round(x, 3), round(z, 3)) for x, z in road]
    xe = plan['outer_road'][2][0]
    z_e = None
    for a_, b_ in zip(ring[:-1], ring[1:]):
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
    sx_new = round(kx + gate_half + 0.6, 2)                               # ground outline: the step moves east so the KPP road lies inside
    fence[i - 1] = (sx_new, fence[i - 1][1])
    fence[i] = (sx_new, fence[i][1])

    def border_z(x):                                                      # local z of the state fence (R60 border polylines) at local x
        xw = P(x, 100.0)[0]
        for bl in world['border']:
            for a_, b_ in zip(bl[:-1], bl[1:]):
                if min(a_[0], b_[0]) <= xw <= max(a_[0], b_[0]) and abs(b_[0] - a_[0]) > 1e-6:
                    yw = a_[1] + (b_[1] - a_[1]) * (xw - a_[0]) / (b_[0] - a_[0])
                    return Pinv(xw, yw)[1]
        raise SystemExit('state fence not found at x %.1f' % x)
    zb_w, zb_e = border_z(fence[0][0]), border_z(fence[i + 1][0])
    f_left = [fence[0], (fence[0][0], zb_w)]                              # west side of the district fence, up to the state fence
    f_right = [(fence[i + 1][0], zb_e)] + fence[i + 2:]                   # east side from the state fence down to the stub at the east road
    north_gate = (kx - gate_half, zf, kx + gate_half, zf)                 # where the W85 gate was (now only the KPP road entry, no fence)
    fix((kx, zf), 'Северного забора района нет (Федя 22.10, пункт 5, вариант 3): край района на севере — забор страны с КПП (один забор, вид на степь открыт). '
        'Западный и восточный заборы района доведены на север до забора страны (z %.1f / %.1f м плана); дорога к КПП идёт прямо, ворот и столбов в заборе района больше нет'
        % (zb_w, zb_e), 'v10 §7.4 «северный забор ровный, с КПП», без двойного забора (v10 §11); ответ Феди на вопрос W85 Q7')

    # ------------------------------------------------ tracks (W86: derived from the new geometry)
    trk, tk = tracks_w86(L, hz, kx, kz0, xe)
    fix((tk['x_s'], tk['z_r1']), 'Колеи пересчитаны по новой планировке: сквозной проезд запад–восток — заезд, вверх к А4 (z %.1f), вдоль W вниз, под гаражами 7, '
        'ступенька вниз у запада новой «ноги» E (x %.1f), через А5 (z %.1f) прямо к восточной дороге; новые колеи T8 (белая полоса у гаражей базы 3), '
        'T9 (белая полоса под гаражами 7 -> коридор у E -> T4), T10 (вокруг северного торца удлинённого W)' % (tk['zA4'], tk['x_s'], tk['zA5']),
        'старые оси W85 проходили сквозь новые куски домов (отметки M1, M2, M3, M7); ступенька та же, прямого «прострела» нет')

    # ------------------------------------------------ obstacles for checks
    obst = []                                                             # (name, rect)
    for b, hid, r in parts:
        cut = arch_by_host.get(b, [])
        if cut:
            a = cut[0]['rect']
            if cut[0]['through'] == 'N-S':
                obst += [(b, (r[0], r[1], a[0], r[3])), (b, (a[2], r[1], r[2], r[3]))]
            else:
                obst += [(b, (r[0], r[1], r[2], a[1])), (b, (r[0], a[3], r[2], r[3]))]
        else:
            obst.append((b, r))
    for j, g in enumerate(garages):
        obst.append(('G%02d' % (j + 1), g['rect']))
    obst += [('shop', shop), ('kiosk1', kiosks[0]), ('kiosk2', kiosks[1]), ('booth1', booths[0]), ('booth2', booths[1]), ('box', box)]
    obst += [('play-' + n, r) for n, r, in plays] + [('trash-' + n, r) for n, r, _ in trashes]
    soft = [('palisade-%s-%s' % (p['bid'], p['side']), r) for p, ps in pal_pcs for r in ps]

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

    # ------------------------------------------------ cars (8 plan spots, moved off houses / ruts / arch mouths by rule)
    arch_zone = []
    for a in arches:
        r = a['rect']
        arch_zone.append(grow(r, 0.0, 8.0) if a['through'] == 'N-S' else grow(r, 8.0, 0.0))

    def car_rect(c, ang):
        return grow((c[0], c[1], c[0], c[1]), CAR[0] / 2, CAR[1] / 2) if ang == 0 else grow((c[0], c[1], c[0], c[1]), CAR[1] / 2, CAR[0] / 2)
    hard = obst + soft + [('path', path_rect(d, LAWN)) for d in doors] + [('van', van)] + [('box wicket approach', grow(appr, 1.0))]

    def car_problem(c, ang, others=()):
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
        for o in others:
            if rinter(cr, car_rect(*o), 0.8):
                return 'вплотную к другой машине'
        return None
    cars = []
    h56a = pr['04-H56a']
    a1 = [a for a in arches if a['id'] == 'A1'][0]['rect']
    moves = {7: ('за домом у коробки H13 (с северной стороны, 2 м от стены)', lambda c: (c[0], h13[3] + 2.0 + CAR[1] / 2)),
             4: ('у глухой северной стены H56, а не на колее у гаражей', lambda c: (c[0], h56a[3] + 1.6 + CAR[1] / 2)),
             0: ('вдоль колеи у дома 10 восточнее арки А1, а не перед её въездом', lambda c: (a1[2] + 5.0, pal_h3_z0 - 0.35 - CAR[1] / 2)),
             3: ('в кармане перед магазином, а не на тротуаре у бордюра', lambda c: (c[0], ROAD_W / 2 + 1.5 + 0.3 + CAR[1] / 2))}
    for j, cr in enumerate(L['cars']):
        c, ang = cr['pos'], cr['ang']
        why = car_problem(c, ang, cars)
        if why and j in moves:
            txt, fn = moves[j]
            c2 = fn(c)
            if not car_problem(c2, ang, cars):
                fix(c2, 'Машина %d переставлена %s (было x %.1f, z %.1f м плана: %s)' % (j + 1, txt, c[0], c[1], why),
                    'машины стоят ровно и логично, не в домах, не на колеях и не у въезда в арку (v10 §8)')
                cars.append((c2, ang))
                continue
        if why:
            ax = (1, 0) if ang == 0 else (0, 1)
            best = None
            for du in sorted(np.arange(-18, 18.01, 0.5), key=abs):
                for dv in sorted(np.arange(-8, 8.01, 0.5), key=abs):
                    c2 = (c[0] + ax[0] * du - ax[1] * dv, c[1] + ax[1] * du + ax[0] * dv)
                    if not car_problem(c2, ang, cars):
                        cand = (math.hypot(du, dv), c2)
                        if best is None or cand[0] < best[0]:
                            best = cand
                if best and best[0] <= abs(du):
                    break
            assert best, 'car %d: no free spot near (%.1f, %.1f): %s' % (j, c[0], c[1], why)
            fix(best[1], 'Машина %d переставлена на %.1f м (было x %.1f, z %.1f м плана: %s)' % (j + 1, best[0], c[0], c[1], why),
                'после перепланировки W86 место занято / на колее — ближайшее ровное место у той же стены (v10 §8)')
            c = best[1]
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
        Ln = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
        n = max(1, int(round(Ln / LAMP_STEP)))
        for s in range(n + 1):
            t = s / n
            cand.append(((a_[0] + (b_[0] - a_[0]) * t + nrm[0] * off, a_[1] + (b_[1] - a_[1]) * t + nrm[1] * off), 'outer road'))
    lamps, dropped = [], {}
    car_r = [car_rect(c, a) for c, a in cars]
    juncs = [trk[k_][0] for k_ in ('T1', 'T2')] + [(Pinv(748.0, 671.0)[0], 0.0), (Pinv(945.0, 671.0)[0], 0.0), (west_x, hz), (xe, z_e), (xe, east_leg[1][1]),
                                                   trk['T0'][-1]]
    for (q, why) in cand:
        bad = None
        if any(rdist(q, r) < 0.4 for n_, r in obst if not n_.startswith('play')):
            bad = 'building/garage'
        elif any(rdist(q, r) < 0.2 for r in pal_all):
            bad = 'palisade'
        elif any(line_d(q, pl) < TRACK_W[k_] / 2 + 1.0 for k_, pl in trk.items()):
            bad = 'track'
        elif why != 'outer road' and line_d(q, road + east_leg) < ROAD_W / 2 + 1.0:
            bad = 'road'
        elif any(rdist(q, grow(path_rect(d, LAWN), 0.4)) == 0 for d in doors) or rdist(q, grow(van, 1.0)) == 0:
            bad = 'path/van'
        elif any(rdist(q, r) == 0 for r in arch_zone):
            bad = 'arch mouth'
        elif rdist(q, grow(appr, 1.0)) == 0:
            bad = 'box wicket approach'
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
    fix((box[0], (wz0 + wz1) / 2), 'Калитка футбольной коробки — на западной короткой стороне, у северного конца (z %.1f…%.1f м плана, ближе к M5); подъезд бусика с запада '
        'свободен: зона 04-box-wicket-approach %.0f x %.0f м без деревьев, фонарей и машин' % (wz0, wz1, appr[2] - appr[0], appr[3] - appr[1]),
        'Федя 22.10, пункт 6 (вариант 3, чуть выше): с севера между сеткой и палисадником H13 только ~4 м — бусик не развернётся в калитку')

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
        pth = path_rect(d, LAWN)
        e = {'pos': W((x, z)), 'facing_deg': FACING[d['side']], 'kind': 'podyezd', 'w_m': 1.2, 'benches': d['benches'],
             'urn': d['benches'] > 0, 'path': {'poly': WR(pth), 'surface': 'concrete_SK3c', 'w_m': 3.2},
             'kit': {'canopy': 'concrete', 'door': 'iron_intercom', 'steps': 3}, 'plan_door': d['i']}
        if d['new']:
            e['w86_new'] = d['new']
        return e
    groups = {}
    mark_of = {}
    for mid, rec in log['marks'].items():
        for k_ in ('part', 'wing'):
            if rec.get(k_):
                mark_of.setdefault(rec[k_], []).append(mid)
    for b, hid, r in parts:
        ents = [ent_of(d) for d in doors if d['host'] == b]
        arc = []
        for a in arch_by_host.get(b, []):
            ar = a['rect']
            plen = (ar[2] - ar[0]) if a['through'] == 'W-E' else (ar[3] - ar[1])
            arc.append({'id': a['id'], 'rect': WR(ar), 'through': a['through'], 'clear_w_m': ARCH_W, 'clear_h_m': ARCH_H, 'passage_len_m': round(plen, 2),
                        'floors_above': 'from %.1f m: floors 2-5 continue over the arch (continuous house)' % ARCH_H})
            ents.append({'pos': W(rcen(ar)), 'facing_deg': 0 if a['through'] == 'W-E' else 90, 'kind': 'arch', 'w_m': ARCH_W, 'clear_h_m': ARCH_H,
                         'through': a['through'], 'arch_id': a['id']})
        if b == '04-H17b':
            ents.append({'pos': W((rcen(gate)[0], pr[b][3])), 'facing_deg': 90, 'kind': 'garage_gate', 'w_m': round(gate[2] - gate[0], 2),
                         'notes': 'BASE 3: van garage in the ground floor of the L-house H17, iron gate; van spot (yard 2) in front'})
        if b == '04-Ed':
            ents.append({'pos': W((club[0], rcen(canopy)[1])), 'facing_deg': 180, 'kind': 'door', 'w_m': 1.6,
                         'notes': 'club / den 5 ("притон"): canopy, neon heart sign WITHOUT words, bouncer, smokers corner in front'})
        nb = {'id': b, 'group': hid, 'name_ru': names[hid], 'kind': 'khrushchevka', 'material_slot': 'rough_khrushchevka',
              'footprint': WR(r), 'floors': FLOORS, 'floor_h_m': FLOOR_H, 'height_m': FLOORS * FLOOR_H + PLINTH, 'roof': dict(roof5),
              'walls': 'KH1b', 'tint': None, 'entrances': ents, 'arches': arc, 'facade_kit': 'rough', 'sockets': dict(soc),
              'collider': 'full_roof', 'disabled': False, 'notes': kh_note}
        if b in mark_of:
            nb['w86'] = {'marks': mark_of[b], 'ru': '; '.join(log['marks'][m_]['ru'] for m_ in mark_of[b]),
                         'added_rect': [WR(log['marks'][m_].get('added') or log['marks'][m_]['wing_rect']) for m_ in mark_of[b]]}
        if b in ('04-W', '04-Ea'):
            nb.setdefault('w86', {})['continuous'] = 'W85 parts %s merged over the old arch gap (one continuous house, arch %s in it)' % (
                '04-Wa + 04-Wb' if b == '04-W' else '04-Ea + 04-Eb', 'A4' if b == '04-W' else 'A5')
        if b == '04-Ed':
            nb['ground_floor_use'] = {'kind': 'club', 'rect': WR(club)}
        if b == '04-H17b':
            nb['ground_floor_use'] = {'kind': 'base3_garage', 'gate_rect': WR(gate)}
        blds.append(nb)
        groups.setdefault(hid, []).append(b)
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
                     'disabled': False, 'notes': {'GN': 'row of 12 at the north fence, gates south (v50/v52)', 'G7': 'cooperative 7: 2 rows of 8 gates facing + 2 + 2 (W86: court %.1f m, raised)' % G7_COURT,
                                                  'GNE': 'NE block at yard 12: 9 + 9 facing + 1', 'GB': 'base 3 cover: 5 + 2 (L) around the van spot (W86: moved west, van passage east of it)'}[g['group']]
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
    # KPP (v85 R69_checkpoint) — on the country border, north of the district fence (unchanged from W85)
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
    for j, t in enumerate(L['turniks']):
        (ax, az), (bx, bz) = t['a'], t['b']
        for pq in pal_all:
            if pq[1] <= az <= pq[3] and pq[0] - 0.05 <= ax <= pq[2] + 0.05 and abs(az - bz) < 0.01:
                sh = pq[2] + 1.0 - ax
                fix((ax + sh, az), 'Турник %d сдвинут на %.1f м восточнее (x %.2f…%.2f -> %.2f…%.2f м плана)' % (j + 1, sh, ax, bx, ax + sh, bx + sh),
                    'на плане его западная стойка стоит в палисаднике, в 0,4 м от стены дома H1')
                ax, bx = ax + sh, bx + sh
        L['turniks'][j] = {'a': (ax, az), 'b': (bx, bz)}
        props.append({'id': '04-turnik%d' % (j + 1), 'kind': 'pull_up_bar', 'pos': W(((ax + bx) / 2, (az + bz) / 2)), 'rot_deg': 0,
                      'size': [round(math.hypot(bx - ax, bz - az), 2), 0.1, 2.4], 'grip_anchor': True})
    for k_, kt in enumerate(L['kits']):
        rr = kt['rect']
        props.append({'id': '04-%s-%s%d' % (kt['key'], kt['kind'], k_ if kt['key'] == 'yard12' else k_ - 5), 'kind': kt['kind'], 'pos': W(rcen(rr)), 'rot_deg': 0,
                      'size': [round(rr[2] - rr[0], 2), round(rr[3] - rr[1], 2), 2.2 if kt['kind'] != 'sandbox' else 0.3], 'grip_anchor': kt['kind'] == 'swing_set'})
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

    # zones
    dist = L['dist']
    dist = [((sx_new if abs(x - sx_old) < 0.05 else x), z) for x, z in dist]
    L['dist'] = dist
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
    zones.append({'id': '04-fence-w', 'kind': 'fence', 'line': WL(f_left), 'surface': 'concrete_panel_SK3c', 'height_m': 2.2,
                  'notes': 'district fence (plan v52), west side only, run north to the state fence (Fedya 22.10: no district fence on the north)'})
    zones.append({'id': '04-fence-e', 'kind': 'fence', 'line': WL(f_right), 'surface': 'concrete_panel_SK3c', 'height_m': 2.2,
                  'notes': 'district fence (plan v52), east side from the state fence down to the stub at the verge of the east road (no north side)'})
    for j, bl in enumerate(world['border']):
        zones.append({'id': '04-border-fence%d' % (j + 1), 'kind': 'border_fence', 'line': [rnd2(p) for p in bl], 'surface': 'fence_net', 'height_m': 3.0,
                      'scope': 'north_border', 'notes': 'country border: chain-link on posts (x 572-1031), invisible wall along it, steppe beyond; meets the KPP'})
    zones.append({'id': '04-kpp-stopline', 'kind': 'road_marking', 'line': [rnd2((856.6, 922.5)), rnd2((863.4, 922.5))], 'surface': None,
                  'scope': 'north_border', 'notes': 'STOP line before the KPP gate (v85)'})
    for p, ps in pal_pcs:
        for k_, q in enumerate(ps):
            zones.append({'id': '04-palisade-%s-%s%s' % (p['bid'][3:], p['side'], 'abcdefgh'[k_] if len(ps) > 1 else ''), 'kind': 'front_garden',
                          'poly': WR(q), 'surface': 'lawn', 'low_fence': {'h_m': 0.6, 'side': 'outer edge', 'gaps': 'at every podyezd path'},
                          'facade': p['bid'], 'side': p['side'], 'notes': 'live green grass ~4 m with a low fence; podyezd paths cross it'})
    for n_, r in plays:
        zones.append({'id': '04-playground-' + ('yard12' if '12' in n_ else 'yard9'), 'kind': 'playground', 'poly': WR(r), 'surface': 'rubber',
                      'kerb': True, 'name_ru': n_, 'notes': 'neat rectangle with a kerb: swings, slide, sandbox (+ roundabout and 2nd swings on the big one)'})
    for n_, r, op in trashes:
        zones.append({'id': '04-trash-' + ('yard12' if '12' in n_ else 'yard9'), 'kind': 'trash_section', 'poly': WR(r), 'surface': 'concrete_SK3c',
                      'open_side': {'открыта на юг': 'S', 'открыта на запад': 'W'}.get(op, op), 'walls': 'roof_profsheet_SK4c on 3 sides',
                      'notes': '2 skip "boats" + 3 green bins'})
    pal_h13 = [r for p, ps in pal_pcs if p['bid'] == '04-H13' for r in ps]
    lane = min(r[1] for r in pal_h13) - box[3]
    zones.append({'id': '04-football-box', 'kind': 'football_box', 'poly': WR(box), 'surface': 'lawn', 'size_m': [BOX_W, BOX_D],
                  'fence': {'board_h_m': 1.0, 'net_h_m': 4.5, 'material': 'fence_net', 'hole_in_net': True, 'graffiti_on_board': True},
                  'wicket': {'pos': W((box[0], (wz0 + wz1) / 2)), 'w_m': round(48 * M, 2), 'side': 'W', 'at': 'north end of the west short side (Fedya 22.10)',
                             'van_enters': True, 'approach_zone': '04-box-wicket-approach'},
                  'notes': 'worn artificial turf with bald patches, goals with torn nets at both short ends, ONE wicket at the north end of the west side, 2 floodlights, '
                           'spectator bench, balls and bottles inside; NPC always play / hang out'})
    zones.append({'id': '04-box-wicket-approach', 'kind': 'drive', 'poly': WR(appr), 'surface': 'worn_grass_L02',
                  'notes': 'free van approach to the box wicket from the west (open ground between H14 and the box; reached from the south road or from the '
                           'W-E drive past the west end of H13): no trees, lamps, cars or props'})
    zones.append({'id': '04-base3-van-spot', 'kind': 'loading_pad', 'poly': WR(van), 'surface': 'concrete_SK3c', 'base': 3,
                  'notes': 'yard 2: van spot 5.2 x 8.7 m in front of the base garage gate in H17; garage L (5 + 2) hides it; yard ~25 x 19 m to turn'})
    gbr = [g['rect'] for g in garages if g['group'] == 'GB']
    zones.append({'id': '04-base3-yard', 'kind': 'yard', 'poly': WR((pr['04-H17a'][2] + LAWN, pr['04-H17b'][3], max(r[2] for r in gbr),
                                                                   min(g['rect'][1] for g in garages if g['group'] == 'GB' and g['gate'] == 'S'))),
                  'surface': 'worn_grass_L02', 'notes': 'base 3 yard (function: loading, turning) — no trees, no props in the middle'})
    zones.append({'id': '04-club-smokers', 'kind': 'plaza', 'poly': WR(smokers), 'surface': 'concrete_SK3c',
                  'notes': 'smokers corner in front of the club entrance: bouncer, crowd; central NPC area with yard 12'})
    for n_, c, rx, rz in squares:
        zones.append({'id': '04-square-' + ('box' if 'box' in n_ else 'yard13'), 'kind': 'mini_square', 'poly': WL(ellipse(c, rx, rz)), 'surface': 'lawn',
                      'notes': n_ + ': patch of lawn, a few bare trees, tyre flower bed; benches only at podyezds (legend)'})
    # vegetation
    trees = L['trees']
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
    new_pal_m = 0.0
    for p, ps in pal_pcs:
        sn = p['side'] in 'SN'
        for r in ps:
            lo, hi = (r[0], r[2]) if sn else (r[1], r[3])
            cuts = [lo] + sorted(v for v in (d['pos'][0] if sn else d['pos'][1] for d in doors if d['host'] == p['bid'] and d['side'] == p['side']) if lo < v < hi) + [hi]
            for u, v in zip(cuts[:-1], cuts[1:]):
                u2, v2 = u + (2.0 if u != lo else 0.5), v - (2.0 if v != hi else 0.5)
                if v2 - u2 < 2.5:
                    continue
                q = (u2, r[1] + 0.6, v2, r[3] - 0.6) if sn else (r[0] + 0.6, u2, r[2] - 0.6, v2)
                n = count_in(q)
                if not n and p['bid'] in mark_of and v2 - u2 >= 6.0:     # new palisade pieces: trees like the rest of the house (~1 per 12 m)
                    seg_new = any(rinter(q, grow(log['marks'][m_].get('added') or log['marks'][m_]['wing_rect'], LAWN + 0.5)) for m_ in mark_of[p['bid']])
                    if seg_new:
                        n = max(1, int(round((v2 - u2) / 12.0)))
                        new_pal_m += v2 - u2
                if n:
                    veg += 1
                    zones.append({'id': '04-veg-pal-%s-%s%d' % (p['bid'][3:], p['side'], veg), 'kind': 'veg_zone', 'poly': WR(q), 'density': 'sparse',
                                  'species': 'bare', 'target_count': n, 'notes': 'bare crooked tree(s) in the palisade between podyezds (cold grey-brown bark)'})
    for n_, c, rx, rz in squares:
        n = count_in((c, rx, rz), 'ell')
        zones.append({'id': '04-veg-square-' + ('box' if 'box' in n_ else 'yard13'), 'kind': 'veg_zone', 'poly': WL(ellipse(c, rx * 0.8, rz * 0.8)),
                      'density': 'grove', 'species': 'bare', 'target_count': n, 'notes': n_})
    blocked = [r for _, r in obst] + pal_all
    for j, c in enumerate(L['pockets']):
        if any(rdist(c, r) < 1.0 for r in blocked) or any(line_d(c, pl) < TRACK_W[k_] / 2 + 2.0 for k_, pl in trk.items()):
            fix(c, 'Карман для дерева у гаражей %d не используется — место занято новым куском дома / палисадником / колеёй' % (j + 1), 'деревья не на колеях и не в домах')
            continue
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
    nt.append(('KPP road', buffer_line([(kx, kz0 - 2.0), (kx, Pinv(860.0, 950.0)[1])], ROAD_W / 2 + 2.0, cap=False)))
    nt.append(('base 3 yard + van spot (loading pad)', rpoly(grow(van, 2.0))))
    nt += [('playground', rpoly(grow(r, 1.5))) for n_, r in plays]
    nt += [('trash section + access', rpoly(grow(r, 2.0))) for n_, r, _ in trashes]
    nt.append(('football box', rpoly(grow(box, 2.0))))
    nt.append(('football box wicket approach (west)', rpoly(grow(appr, 1.0))))
    gn = [g['rect'] for g in garages if g['group'] == 'GN']
    nt.append(('drive under / in front of the 12 garages', rpoly((min(r[0] for r in gn) - 2, pr['04-H56a'][3], max(r[2] for r in gn) + 2, min(r[1] for r in gn)))))
    nt.append(('drive under the 12 garages (west)', rpoly((min(r[0] for r in gn) - 2, pr['04-H1a'][3], pr['04-H1a'][2] + 2, min(r[1] for r in gn)))))
    g7 = [g for g in garages if g['group'] == 'G7']
    nt.append(('coop 7 lane', rpoly((max(g['rect'][2] for g in g7 if g['gate'] == 'E'), max(g['rect'][3] for g in g7 if g['gate'] == 'N'),
                                     min(g['rect'][0] for g in g7 if g['gate'] == 'W'), min(g['rect'][1] for g in g7 if g['gate'] == 'S')))))
    gne = [g for g in garages if g['group'] == 'GNE']
    nt.append(('GNE garage lane', rpoly((max(g['rect'][2] for g in gne if g['gate'] == 'E'), tk['zA5'], min(g['rect'][0] for g in gne if g['gate'] == 'W'),
                                         max(g['rect'][1] for g in gne)))))
    nt.append(('coop 7 passages under / over (W86)', rpoly((min(g['rect'][0] for g in g7) - 2.0, pr['04-Ef'][3] + LAWN, max(g['rect'][2] for g in g7) + 2.0,
                                                            min(g['rect'][1] for g in g7)))))
    nt.append(('base-3 garages east passage (W86 white strip)', rpoly((max(r[2] for r in gbr), 0.0, pr['04-H14b'][0], max(r[3] for r in gbr) + 2.0))))
    nt += [('arch approach', rpoly(r)) for r in arch_zone]
    nt.append(('club smokers corner', rpoly(grow(smokers, 1.0))))
    nt.append(('shop forecourt', rpoly((shop[0] - 4.0, ROAD_W / 2, shop[2] + 4.0, shop[1]))))
    nt.append(('KPP road entry', rpoly(grow(north_gate, 1.0, 6.0))))
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
    for k_ in range(0, 640):
        x = k_ / 2.0
        if not 6.0 <= x <= xe - 6.0:
            continue
        hit = any(r[0] <= x <= r[2] for r in solid) or any(min(a_[0], b_[0]) <= x <= max(a_[0], b_[0]) and a_[1] == b_[1] and a_[1] < zmax - 1 for a_, b_ in fsegs)
        if not hit:
            sn.append(x)
    for k_ in range(2, 470):
        z = k_ / 2.0
        if not 10.0 <= z <= zmax - 2.0:
            continue
        hit = any(r[1] <= z <= r[3] for r in solid) or any(min(a_[1], b_[1]) <= z <= max(a_[1], b_[1]) and a_[0] == b_[0] and 0 < a_[0] < xe for a_, b_ in fsegs)
        if not hit:
            we.append(z)
    checks['straight_S_to_N_open_x_ranges'] = ranges(sn, 0.5)
    checks['straight_W_to_E_open_z_ranges'] = ranges(we, 0.5)
    xin0 = min(r[0] for r in solid)
    zin0 = min(r[1] for r in solid)
    checks['straight_interior'] = {'S_to_N': [g for g in ranges(sn, 0.5) if g[0] > xin0 + 0.5], 'W_to_E': [g for g in ranges(we, 0.5) if g[0] > zin0 + 0.5],
                                   'edge_strips': {'west_x_lt_first_house_m': round(xin0, 1), 'south_z_lt_first_house_m': round(zin0, 1)},
                                   'note': 'ranges inside the outermost houses; the strips between the outer road / fence and the first houses are the district edge '
                                           '(W85 note: not counted); they are as wide as on v52'}
    checks['straight_lines_note'] = ('core x 6..%.0f / z 10..%.0f (plan m); edges not counted: the strip along the west road / fence and the south road verge. '
                                     'Empty lists = no straight S->N or W->E see-through (v10 §7.4)' % (xe - 6, zmax - 2))
    checks['arches'] = {a['id']: {'host': a['host'], 'through': a['through'], 'clear_w_m': ARCH_W, 'clear_h_m': ARCH_H,
                                  'passage_len_m': log['arches'][a['id']]['passage_len_m'], 'old_clear_w_m': log['arches'][a['id']]['old_clear_w_m'],
                                  'ok': ARCH_W >= 4.0 and ARCH_H >= 4.5} for a in arches}
    checks['outer_road_clearance_m'] = {k_: round(v[0], 2) for k_, v in road_c.items()}
    a4 = [a for a in arches if a['id'] == 'A4'][0]['rect']
    a5 = [a for a in arches if a['id'] == 'A5'][0]['rect']
    checks['W_E_drive'] = {'through_A4': any(a4[0] <= q[0] <= a4[2] and a4[1] <= q[1] <= a4[3] for q in samples(trk['T0'])),
                           'through_A5': any(a5[0] <= q[0] <= a5[2] and a5[1] <= q[1] <= a5[3] for q in samples(trk['T0'])),
                           'A4_centre_z': round(rcen(a4)[1], 2), 'A5_centre_z': round(rcen(a5)[1], 2), 'step_m': round(rcen(a4)[1] - rcen(a5)[1], 2),
                           'v45_A4_z': 114.1, 'v45_A5_z': 100.85}
    gn_z0 = min(r[1] for r in gn)
    checks['garages_north_row'] = {'n': len(gn), 'depth_m': round(gn[0][3] - gn[0][1], 2), 'gates': 'S', 'drive_under_to_H1_m': round(gn_z0 - pr['04-H1a'][3], 2),
                                   'in_front_to_H56_m': round(gn_z0 - pr['04-H56a'][3], 2), 'gap_behind_to_district_edge_m': round(zf - max(r[3] for r in gn), 2)}
    checks['football_box'] = {'size_m': [BOX_W, BOX_D], 'gap_shop_box_m': round(box[1] - shop[3], 2), 'gap_box_H13_m': round(h13[1] - box[3], 2),
                              'lane_box_to_H13_palisade_m': round(lane, 2)}
    checks['lamps_dropped_by_rule'] = dropped
    checks['plan_trees_not_in_a_zone'] = [list(map(lambda v: round(v, 2), t)) for t in stray]

    # ------------------------------------------------ W86 checks: van grid search, rectangle sweep, gaps, overlaps, entrances
    w86 = {'growth': {k: v for k, v in log['growth'].items() if k != 'parts'}, 'growth_parts': log['growth']['parts'], 'marks': {m_: {k: (([round(v, 2) for v in val] if isinstance(val, tuple) else val)) for k, val in rec.items()}
                                                for m_, rec in log['marks'].items()},
           'arches': log['arches'], 'coop7': log['g7'], 'base3_garages': log['gb'], 'new_podyezds': log['new_doors'], 'moved_props': log['moved_props']}
    small = [('disc', (q, 0.25)) for q, _ in lamps] + [('rect', car_rect(c, a)) for c, a in cars]
    for t in L['turniks']:
        small += [('disc', (t['a'], 0.15)), ('disc', (t['b'], 0.15))]
    box_ring = [(box[0], box[1], box[2], box[1] + 0.3), (box[0], box[3] - 0.3, box[2], box[3]), (box[2] - 0.3, box[1], box[2], box[3]),
                (box[0], box[1], box[0] + 0.3, wz0), (box[0], wz1, box[0] + 0.3, box[3])]
    solid_v = [(n_, r) for n_, r in obst if n_ != 'box'] + [('boxfence', r) for r in box_ring]
    targets = []
    for d in doors:
        o = OUTV[d['side']]
        targets.append(('door %s %s' % (d['host'], d['i'] if d['i'] is not None else d['new']),
                        (d['pos'][0] + o[0] * (LAWN + 1.4), d['pos'][1] + o[1] * (LAWN + 1.4))))
    for a in arches:
        r = a['rect']
        c = rcen(r)
        if a['through'] == 'W-E':
            mouths = [('W', (r[0] - 3.0, c[1])), ('E', (r[2] + 3.0, c[1]))]
        else:
            mouths = [('S', (c[0], r[1] - 3.0)), ('N', (c[0], r[3] + 3.0))]
        targets += [('arch %s %s mouth' % (a['id'], s_), p) for s_, p in mouths]
        targets.append(('arch %s inside' % a['id'], c))
    for j, g in enumerate(garages):
        r = g['rect']
        c = rcen(r)
        o = OUTV[g['gate']]
        gp = {'S': (c[0], r[1]), 'N': (c[0], r[3]), 'E': (r[2], c[1]), 'W': (r[0], c[1])}[g['gate']]
        targets.append(('garage G%02d %s gate' % (j + 1, g['group']), (gp[0] + o[0] * 2.0, gp[1] + o[1] * 2.0)))
    targets += [('base3 van spot', rcen(van)), ('shop door', (rcen(shop)[0], shop[1] - 2.0)), ('box wicket (west side, north end)', (box[0] - 2.0, (wz0 + wz1) / 2)),
                ('club door / smokers', rcen(smokers)), ('yard 12 (trash, open side)', (rcen(trashes[0][1])[0], trashes[0][1][1] - 2.5)),
                ('yard 9 (trash, open side)', (trashes[1][1][0] - 2.5, rcen(trashes[1][1])[1])), ('KPP road entry', (kx, zf - 3.0))]
    targets += [('track %s end' % k_, pl[-1]) for k_, pl in trk.items()]
    targets += [('white strip under coop 7', (rcen(bbox([g['rect'] for g in g7]))[0], tk['z9'])),
                ('white strip base 3', (trk['T8'][0][0], rcen(bbox(gbr))[1]))]
    road_lines = [(road, ROAD_W), ([(kx, kz0 - 2.0), (kx, zf + 20.0)], ROAD_W)]
    G, dgrid, reach, sw = van_checks(L, solid_v, pal_all, small, [f_left, f_right], road_lines, east_leg, [(kx, kz0), (kx, zf + 25.0)], trk, targets)
    unreach = sorted(n_ for n_, w in reach.items() if w < 2.3)
    narrow = sorted(((w, n_) for n_, w in reach.items() if 2.3 <= w < 3.0))
    w86['van_grid'] = {'method': 'obstacles (houses minus arch openings, garages, shop, kiosks, booths, box fence with the wicket, playgrounds, trash sections, '
                                 'palisades, cars, lamps, pull-up bars, fences) on a 0.25 m grid; district ground + roads allowed; widest path from the south road, '
                                 'value = widest corridor (m) on the best path, tested at 2.3 / 2.6 / 3.0 / 3.5 / 4.0 / 5.0 / 6.0 m',
                       'targets': len(reach), 'reachable_2_3m': len(reach) - len(unreach), 'unreachable': unreach,
                       'reachable_but_narrow_lt_3m': [[round(w, 1), n_] for w, n_ in narrow],
                       'widest_by_target': {n_: w for n_, w in sorted(reach.items())}}
    asw = {}
    for a in arches:
        r = a['rect']
        c = rcen(r)
        if a['through'] == 'W-E':
            mouths = {'W': ((r[0], c[1]), (-1.0, 0.0)), 'E': ((r[2], c[1]), (1.0, 0.0))}
        else:
            mouths = {'S': ((c[0], r[1]), (0.0, -1.0)), 'N': ((c[0], r[3]), (0.0, 1.0))}
        (ma, _), (mb, _) = mouths.values()
        body, _ = sweep(G, dgrid, van_paths([ma, mb]))                   # van inside the arch, its ends 2.75 m out of both mouths
        ex = {}
        for mk, (m0, u) in mouths.items():
            opts = {'straight': [m0, (m0[0] + u[0] * 8.0, m0[1] + u[1] * 8.0)]}
            for side, rot in (('left', 1), ('right', -1)):
                nrm = (-u[1] * rot, u[0] * rot)
                p1 = (m0[0] + u[0] * TURN_R, m0[1] + u[1] * TURN_R)
                opts[side] = [m0, p1, (p1[0] + nrm[0] * 8.0, p1[1] + nrm[1] * 8.0)]
            vals = {k: sweep(G, dgrid, van_paths(v))[0] for k, v in opts.items()}
            best = max(vals, key=lambda k: vals[k] if vals[k] is not None else -1)
            ex[mk] = {'best_exit': best, 'clearance_m': round(vals[best], 2), 'all': {k: (round(v, 2) if v is not None else None) for k, v in vals.items()}}
        asw[a['id']] = {'body_clearance_m': round(body, 2) if body is not None else None, 'mouths': ex,
                        'ok': (body or 0) > 0.1 and all(e['clearance_m'] > 0.1 for e in ex.values())}
    w86['van_sweep'] = {'rect_m': list(VAN), 'turn_radius_m': TURN_R, 'tracks': sw, 'arches': asw,
                        'method': 'EDT of the obstacle raster sampled over the 2.3 x 5.5 m rectangle every 0.25 m along the path (corners filleted with '
                                  'r <= %.0f m); tracks trimmed by half a van at both ends; per arch: van inside the arch + best of straight / left / right '
                                  '90-degree exit at each mouth; value = clearance to the nearest obstacle (0 = touching)' % TURN_R}
    # gaps / overlaps / entrances
    solids_g = [(b, hid, r) for b, hid, r in parts] + [('G%02d' % (j + 1), g['group'], g['rect']) for j, g in enumerate(garages)] + \
               [('shop', 'BOX', shop), ('kiosk1', 'BOX', kiosks[0]), ('kiosk2', 'BOX', kiosks[1]), ('booth1', 'H9', booths[0]), ('booth2', 'H14', booths[1])]
    gaps, overlaps = [], []
    for i1 in range(len(solids_g)):
        for i2 in range(i1 + 1, len(solids_g)):
            n1, g1, r1 = solids_g[i1]
            n2, g2, r2 = solids_g[i2]
            ov = rover(r1, r2)
            if ov > 0.01:
                overlaps.append([n1, n2, round(ov, 2)])
            if g1 == g2 and n1.startswith('04-H') == n2.startswith('04-H') and rgap(r1, r2) < 0.01:
                continue                                                   # parts of one house / garages of one row touch on purpose
            if n1.startswith('G') and n2.startswith('G') and g1 == g2:
                continue
            gaps.append((round(rgap(r1, r2), 2), n1, n2))
    gaps.sort()
    for p, ps in pal_pcs:
        for q in ps:
            for n_, g_, r in solids_g:
                if n_ != p['bid'] and rover(q, r) > 0.01:
                    overlaps.append(['palisade %s %s' % (p['bid'], p['side']), n_, round(rover(q, r), 2)])
    for n_, r in plays + [(t[0], t[1]) for t in trashes] + [('box', box)]:
        for m_, g_, s_ in solids_g:
            if rover(r, s_) > 0.01:
                overlaps.append([n_, m_, round(rover(r, s_), 2)])
        for q in pal_all:
            if rover(r, q) > 0.01:
                overlaps.append([n_, 'palisade', round(rover(r, q), 2)])
    for c, a in cars:
        cr = car_rect(c, a)
        for m_, g_, s_ in solids_g:
            if rover(cr, s_) > 0.0:
                overlaps.append(['car', m_, round(rover(cr, s_), 2)])
    for q, why in lamps:
        for m_, g_, s_ in solids_g:
            if rdist(q, s_) < 0.2:
                overlaps.append(['lamp', m_, 0])
    for t in L['turniks']:
        for q in (t['a'], t['b']):
            for m_, g_, s_ in solids_g:
                if rdist(q, s_) < 0.3:
                    overlaps.append(['turnik post', m_, 0])
            for pq in pal_all:
                if rdist(q, pq) == 0:
                    overlaps.append(['turnik post', 'palisade', 0])
    ent_bad = []
    for d in doors:
        q = pr[d['host']]
        on = {'S': abs(d['pos'][1] - q[1]), 'N': abs(d['pos'][1] - q[3]), 'E': abs(d['pos'][0] - q[2]), 'W': abs(d['pos'][0] - q[0])}[d['side']]
        inr = q[0] + 1.5 <= d['pos'][0] <= q[2] - 1.5 if d['side'] in 'SN' else q[1] + 1.5 <= d['pos'][1] <= q[3] - 1.5
        long_side = (q[2] - q[0] >= q[3] - q[1]) == (d['side'] in 'SN')
        blocked_by = [b for b, _, r in parts if b != d['host'] and rinter(path_rect(d, LAWN), r, -0.01)]
        in_arch = [a['id'] for a in arches if a['host'] == d['host'] and rinter(grow(path_rect(d, LAWN), 0.5), grow(a['rect'], 0.0), 0)]
        props_block = [n_ for n_, r in [('booth1', booths[0]), ('booth2', booths[1])] if rinter(grow(path_rect(d, LAWN), 0.5), r)]
        if on > 0.05 or not inr or not long_side or blocked_by or in_arch or props_block:
            ent_bad.append({'door': d['i'] if d['i'] is not None else d['new'], 'host': d['host'], 'side': d['side'], 'on_facade_err_m': round(on, 3),
                            'inside_facade': inr, 'long_side': long_side, 'path_blocked_by': blocked_by + props_block, 'in_arch': in_arch})
    w86['min_gaps_m'] = {'smallest_10': [list(g) for g in gaps[:10]], 'note': 'axis gap between solids of different houses / groups (0 = touching)'}
    w86['overlaps'] = overlaps
    w86['entrances'] = {'podyezds': len(doors), 'new_w86': sum(1 for d in doors if d['new']), 'bad': ent_bad,
                        'rule': 'on the host facade line (<= 5 cm), >= 1.5 m from its ends, on a LONG side (R2c rollout puts entrance kits there only), '
                                'path not into another part / arch / booth'}
    def edges(prx, gar):
        return {'west_fence_to_H1_H2_H3': round(min(prx[b][0] for b in ('04-H1b', '04-H2', '04-H3')) - min(p[0] for p in plan['fence']), 2),
                'west_road_axis_to_H11_H17': round(min(prx[b][0] for b in prx if b.startswith(('04-H11', '04-H17'))), 2),
                'south_road_axis_to_first_houses': round(min(prx[b][1] for b in prx if b.startswith(('04-H17', '04-H14', '04-E'))), 2),
                'east_fence_to_GNE': round(max(p[0] for p in plan['fence']) - max(g['rect'][2] for g in gar if g['group'] == 'GNE'), 2),
                'north_edge_to_GN': round(zf - max(g['rect'][3] for g in gar if g['group'] == 'GN'), 2)}
    w86['edges_m'] = {'v52': edges({p['bid']: tuple(p['rect']) for p in v52['parts']}, v52['garages']), 'w86': edges(pr, garages),
                      'note': 'distance from the district edge (fence / outer road axis) to the first houses; must equal v52 (Fedya 22.10 item 3)'}
    def density(rs_by_group):
        allr = [r for rs in rs_by_group.values() for r in rs]
        bb = bbox(allr)
        gs = list(rs_by_group.items())
        nn = []
        for g1, r1 in gs:
            nn.append(min(min(rgap(a_, b_) for a_ in r1 for b_ in r2) for g2, r2 in gs if g2 != g1))
        return {'houses_bbox_m': [round(bb[2] - bb[0], 1), round(bb[3] - bb[1], 1)], 'house_area_m2': round(sum((r[2] - r[0]) * (r[3] - r[1]) for r in allr)),
                'built_share_of_bbox': round(sum((r[2] - r[0]) * (r[3] - r[1]) for r in allr) / ((bb[2] - bb[0]) * (bb[3] - bb[1])), 3),
                'median_gap_to_nearest_other_house_m': round(float(np.median(nn)), 2), 'mean_gap_to_nearest_other_house_m': round(float(np.mean(nn)), 2)}
    g_old, g_new = {}, {}
    for p in v52['parts']:
        g_old.setdefault(p['hid'], []).append(tuple(p['rect']))
    for b, hid, r in parts:
        g_new.setdefault(hid, []).append(r)
    w86['density'] = {'v52': density(g_old), 'w86': density(g_new),
                      'note': 'khrushchevka houses only (13 houses); gap = axis gap between a house and the nearest other house'}
    w86['van_grid']['narrowest_best_corridor_m'] = min(reach.values())
    checks['w86'] = w86
    L['_grid'] = (G, dgrid)
    L['_draw'] = {'road': road, 'east_leg': east_leg, 'kpp': [(kx, kz0), (kx, zf + 25.0)], 'fences': [f_left, f_right]}

    # ------------------------------------------------ owner decisions (Fedya 22.10, ANSWERS_FEDYA_2026-10-22.md items 1-7): no open Rough questions
    owner = ['1 M7 / M8 (marks not in the prompt list): keep both — built', '2 M6 / M7 depth: as drawn (~17 m) — built',
             '3 denser = smaller distances BETWEEN houses (~2.5 %%), edges as v52: houses grow along their long axes at free ends by %.0f %% of their length '
             '(net +2.4 %% house area over the marks-only layout, mean gap to the nearest house 12.2 -> 10.7 m), nothing moves; the 5 %% centre squeeze '
             'of the first W86 draft is gone' % (GROW * 100),
             '4 east side of the ring road: asphalt as plan v52 (zone 04-ring-road-east)', '5 north: no district fence, the edge is the state fence with the KPP',
             '6 football box wicket: west short side, north end (closer to M5), free van approach', '7 trash sections next to the playgrounds: as on the plan']
    # ------------------------------------------------ fit + output
    fit = measure_fit(P, [(p['bid'], p['hid'], 0, p['rect']) for p in v52['parts']], road, world)
    lin = info['lin']
    OXm, OYm = info['origin_px']
    transform = ('plan v52 metres (x east, z north, 0 = SW corner of the outer-road axis) -> plan px (x/%.4f + %.2f, %.2f - z/%.4f; build_rough_v52 export, '
                 'origin T(113, 1765)) -> rough_v52_world.png px (x %d/%d, y %d/%d; make_rough_world_v52 k = %.4f) -> master-SVG units + (%.1f, %.1f) '
                 '-> world = common.u2w (pre-shift metres + post_shift: +22 m north for z > 1 m, less on the south exits). Net for z > 1 m: '
                 'x = %.3f + %.5f x, y = %.3f + %.5f z (scale 1.0, no rotation). Fit of the PLAN v52 houses on the v85 render (the W86 layout '
                 'deliberately differs from the v85 picture): %s'
                 % (info['M'], OXm, OYm, info['M'], info['img'][2], info['plan_px'][0], info['img'][3], info['plan_px'][1], info['k'],
                    info['img'][0], info['img'][1], lin[0], lin[1], lin[2], lin[3], fit['text']))
    for f in FIXES:
        f['where'] = W(f.pop('where_local'))
    for b in blds:
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
    counts = {'houses': len(groups), 'khrushchevka_parts': len(parts), 'arch_bridges': 0,
              'podyezds': len(doors), 'podyezds_new_w86': sum(1 for d in doors if d['new']), 'benches': nb_, 'arches': len(arches), 'garages': len(garages),
              'garages_by_group': {g: sum(1 for x in garages if x['group'] == g) for g in ('GN', 'G7', 'GNE', 'GB')},
              'lamps': len(lamps), 'lamps_by_rule': {w_: sum(1 for _, x in lamps if x == w_) for w_ in ('house corner', 'playground corner', 'box corner', 'outer road')},
              'cars': len(cars), 'playgrounds': len(plays), 'trash_sections': len(trashes), 'booths': len(booths), 'turniks': len(L['turniks']),
              'tracks': len(trk), 'veg_zones': sum(1 for z in zones if z['kind'] == 'veg_zone'),
              'veg_target_trees': sum(z.get('target_count', 0) for z in zones if z['kind'] == 'veg_zone'),
              'no_tree_zones': sum(1 for z in zones if z['kind'] == 'no_tree'),
              'plan': {'podyezds': len(plan['doors']), 'benches': sum(d['benches'] for d in plan['doors']), 'lamps': len(plan['lamps']),
                       'trees': len(plan['trees']), 'cars': len(plan['cars']), 'garages': len(plan['garages'])}}
    out = {'district': 'rough', 'version': 'W86 (%s): plan v52 + Vadim replanning 22.10' % REV,
           'sources': [os.path.relpath(p, ROOT).replace(os.sep, '/') for p in (PLAN_JSON, PLAN_PY, PLAN_PNG, WORLD_PY)] +
                      ['ArtSource/References/Map/World_v85/VOLUNTEERS_MAP_MASTER_v85.svg (<image> rough_v52_world.png, R85_rough_ring, R24_roads, R69_checkpoint, R60 border)',
                       'Working/Reviews/MapW86_Inputs_2026-10-22/ПРОМПТ_Феде_Неблагополучный_перепланировка_v01.md',
                       'Working/Reviews/MapW86_Inputs_2026-10-22/rough_v52_marked_by_vadim.webp (red marks M1-M8, white strips)',
                       'Working/Reviews/MapW86_Inputs_2026-10-22/rough_garages_crop_vadim.png',
                       'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §4 §6 §7.4 §8', 'docs/specs/ROUGH_LEGEND_v45.md', 'docs/specs/ROUGH_SPEC_2026-10-15_v01.md',
                       'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.4'],
           'transform': transform, 'fit': fit['data'],
           'w86_id_changes': {'04-Wa + 04-Wb': '04-W', '04-Ea + 04-Eb': '04-Ea', 'new wings': ['04-H9c (M3)', '04-H14b (M6)', '04-Eg (M7)'],
                              'arch bridges 04-W-A4 / 04-E-A5': 'removed (A4 / A5 are arches inside 04-W / 04-Ea)'},
           'builder_contract': {'arch_entrance': 'entrances[kind=arch]: pos = arch centre, w_m = clear width, clear_h_m = clear height; arches[] has the rect',
                                'note': 'W85Builder / W85Rollout cut a fixed 4 m x 4.5 m opening (cuts.Add((s, 4f)), sa +- 2f) — must read w_m / clear_h_m to show 6 m arches'},
           'pad_height_m': 5.0, 'pad_note': 'flat pad; Rough and Downtown on the same height (v10 §3.1); edges blend softly into the terrain',
           'abs_heights': False, 'lighting': 'overcast_fog',
           'lighting_notes': 'low dark grey sky, dim, fog (visibility 120-150 m, ground haze in yards and at garages), lamps on at night, crows; '
                             'transitions 40-80 m at the district edge (v02 §6)',
           'no_wires': True, 'buildings': blds, 'props': props, 'zones': zones, 'fixed_by_logic': FIXES, 'questions_for_vadim': QUESTIONS,
           'owner_decisions': owner,
           'counts': counts, 'checks': checks}
    return out, P, Pinv, L, v52, trk, pal_all, box, cars, lamps, info


# ---------------------------------------------------------------- fit against the v85 render (plan v52 houses, unchanged method)
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
    dark = (a.sum(-1) < 300)
    errs = {'W': [], 'E': [], 'S': [], 'N': []}
    for b, hid, k, r in parts:
        lo, hi = P(r[0], r[1]), P(r[2], r[3])
        for side in errs:
            vals = []
            span = (lo[1], hi[1]) if side in 'WE' else (lo[0], hi[0])
            for t in np.linspace(span[0] + 2.0, span[1] - 2.0, 7):
                best_s = None
                for s in np.arange(-1.6, 1.61, 0.2):
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
    rs, rw = [], []
    for xw in range(700, 961, 20):
        if min(abs(xw - 748), abs(xw - 945)) < 10:
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
    text = ('plan v52 houses (25 parts) on VOLUNTEERS_MAP_FINAL_v85.png (5 px/m): best extra shift (%.1f, %.1f) m, %.0f %% of the footprints '
            '(inset 0.9 m) on house colour, outline edge vs footprint per side %s m -> residual <= %.1f m; outer road: drawn axis vs plan axis '
            '%.2f / %.2f m (SVG), %.2f / %.2f m (render)'
            % (best[1] / 5.0, -best[2] / 5.0, frac * 100, edge, res, svg_w, svg_s, data['road_axis_render_west_m'] or 0, data['road_axis_render_south_m'] or 0))
    return {'data': data, 'text': text}


# ---------------------------------------------------------------- check images on the world map (as W85)
def draw_dist(im, tp, d, s, full=False):
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
    work = common.WORK
    os.makedirs(work, exist_ok=True)
    x0, y0, x1, y1 = 625, 640, 1045, 948
    s = 3
    im = Image.open(MAP_PREVIEW).convert('RGB').crop((x0, 950 - y1, x1, 950 - y0))
    im = im.resize((im.width * s, im.height * s), Image.NEAREST)
    draw_dist(im, lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s), d, s)
    im.save(os.path.join(work, 'check_rough.png'))
    s = 5
    im = Image.open(MAP_FULL).convert('RGB').crop((x0 * s, (950 - y1) * s, x1 * s, (950 - y0) * s))
    draw_dist(im, lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s), d, s, full=True)
    im.save(os.path.join(work, 'check_rough_full.png'))


# ---------------------------------------------------------------- plan-frame images (same pixel frame as Неблагополучный_район_v52.png)
def plan_render(L, info, trk, pal_all, box, cars, lamps, title):
    """The W86 layout drawn in the style of plan v52, in the v52 PNG pixel frame (8.08 px/m)."""
    M = info['M']
    OXm, OYm = info['origin_px']
    pw, ph = info['plan_px']
    tp = lambda p: (p[0] / M + OXm, OYm - p[1] / M)
    im = Image.new('RGB', (pw, ph), (198, 190, 158))
    dr = ImageDraw.Draw(im)
    rc = lambda r: [tp((r[0], r[3])), tp((r[2], r[1]))]
    dr.polygon([tp(p) for p in L['dist']], fill=(170, 166, 158))
    X = L.get('_draw', {})
    for pl in [X.get('road'), X.get('east_leg'), X.get('kpp')]:
        if pl:
            dr.polygon([tp(q) for q in buffer_line(pl, ROAD_W / 2 + 0.6, cap=False)], fill=(176, 166, 140))
            dr.polygon([tp(q) for q in buffer_line(pl, ROAD_W / 2, cap=False)], fill=(233, 216, 172))
    for k_, pl in trk.items():
        col = (232, 222, 150) if k_ in ('T8', 'T9') else (196, 190, 178)
        dr.polygon([tp(q) for q in buffer_line(pl, TRACK_W[k_] / 2, cap=False)], fill=col)
        dr.line([tp(q) for q in pl], fill=(140, 136, 128), width=2)
        try:
            ft = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 20)
        except OSError:
            ft = None
        m = pl[len(pl) // 2] if len(pl) > 2 else ((pl[0][0] + pl[1][0]) / 2, (pl[0][1] + pl[1][1]) / 2)
        dr.text(tp(m), k_, fill=(90, 80, 40), font=ft)
    for fl in X.get('fences', []):
        dr.line([tp(q) for q in fl], fill=(112, 119, 119), width=5)
    for q in pal_all:
        dr.rectangle(rc(q), fill=(152, 176, 122))
    for p in L['parts']:
        dr.rectangle(rc(p['rect']), fill=(207, 211, 214), outline=(73, 83, 91), width=3)
    for a in L['arches']:
        r = a['rect']
        dr.rectangle(rc(r), fill=(250, 250, 246), outline=(120, 128, 132), width=2)
        (u0, v0), (u1, v1) = rc(r)
        hh = v1 - v0
        for k in np.arange(u0 - hh, u1, 12.0):                          # 45-degree hatching clipped to the arch rect
            pa = (k, v0) if k >= u0 else (u0, v0 + (u0 - k))
            pb = (k + hh, v1) if k + hh <= u1 else (u1, v1 - (k + hh - u1))
            if pa[1] <= v1 and pb[1] >= v0:
                dr.line([pa, pb], fill=(205, 205, 200), width=2)
        if a['through'] == 'N-S':
            dr.line([(u0, v0), (u0, v1)], fill=(73, 83, 91), width=4)
            dr.line([(u1, v0), (u1, v1)], fill=(73, 83, 91), width=4)
        else:
            dr.line([(u0, v0), (u1, v0)], fill=(73, 83, 91), width=4)
            dr.line([(u0, v1), (u1, v1)], fill=(73, 83, 91), width=4)
        try:
            f = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 15)
        except OSError:
            f = None
        c = tp(rcen(r))
        dr.text(c, 'А' + a['id'][1:], fill=(40, 50, 60), font=f, anchor='mm')
    for g in L['garages']:
        dr.rectangle(rc(g['rect']), fill=(180, 202, 204), outline=(100, 120, 128), width=2)
    O = L['O']
    for k_ in ('shop',):
        dr.rectangle(rc(O[k_]), fill=(215, 167, 146), outline=(90, 64, 44), width=2)
    for k_ in ('kiosk1', 'kiosk2'):
        dr.rectangle(rc(O[k_]), fill=(180, 202, 204), outline=(100, 120, 128), width=2)
    for k_ in ('booth1', 'booth2'):
        dr.rectangle(rc(O[k_]), fill=(190, 120, 90), outline=(90, 60, 40), width=2)
    dr.rectangle(rc(box), fill=(160, 196, 130), outline=(40, 40, 40), width=3)
    wz1 = box[3] - 1.0
    dr.line([tp((box[0], wz1)), tp((box[0], wz1 - 48 * M))], fill=(250, 250, 240), width=7)          # wicket (west side, north end)
    a_, b_ = tp((box[0] - 12.0, wz1 + 1.0)), tp((box[0], wz1 - 48 * M - 1.0))
    dr.rectangle([a_, b_], outline=(230, 200, 60), width=2)
    dr.rectangle(rc(O['van']), fill=(250, 250, 248), outline=(80, 90, 100), width=2)
    for p in L['plays']:
        dr.rectangle(rc(p['rect']), fill=(236, 214, 160), outline=(150, 130, 90), width=2)
    for t in L['trashes']:
        dr.rectangle(rc(t['rect']), fill=(220, 222, 214), outline=(90, 100, 90), width=2)
    for d in L['doors']:
        x, z = d['pos']
        o = OUTV[d['side']]
        a_, b_ = tp((x - 1.4 * abs(o[1]) + o[0] * 0.2, z - 1.4 * abs(o[0]) + o[1] * 0.2)), tp((x + 1.4 * abs(o[1]) + o[0] * 1.0, z + 1.4 * abs(o[0]) + o[1] * 1.0))
        dr.rectangle([min(a_[0], b_[0]), min(a_[1], b_[1]), max(a_[0], b_[0]), max(a_[1], b_[1])],
                     fill=(220, 60, 60) if d['new'] else (96, 106, 116), outline=(50, 58, 66))
    for t in L['turniks']:
        dr.line([tp(t['a']), tp(t['b'])], fill=(30, 30, 30), width=4)
    for c, a in cars:
        w_, h_ = (CAR[0] / 2, CAR[1] / 2) if a == 0 else (CAR[1] / 2, CAR[0] / 2)
        dr.rectangle(rc((c[0] - w_, c[1] - h_, c[0] + w_, c[1] + h_)), fill=(170, 50, 40), outline=(80, 20, 20))
    for q, _ in lamps:
        u, v = tp(q)
        dr.ellipse([u - 6, v - 6, u + 6, v + 6], fill=(250, 220, 90), outline=(90, 80, 30))
    try:
        f = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 40)
    except OSError:
        f = None
    dr.text((40, ph - 120), title, fill=(30, 30, 30), font=f)
    try:
        f2 = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 26)
    except OSError:
        f2 = None
    dr.text((40, ph - 66), 'red frames = Vadim marks M1-M8; red doors = new podyezds; yellow-green T8 / T9 = white strips; hatched = arches %.0f m; '
            'north: no district fence (state fence + KPP ~20-30 m north, outside this frame)' % ARCH_W, fill=(40, 40, 40), font=f2)
    return im, tp


def plan_images(d, L, v52, info, trk, pal_all, box, cars, lamps, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    pw, ph = info['plan_px']
    s_, ox, oy = REG
    mk = Image.open(MARKED).convert('RGB')
    big = mk.resize((int(round(mk.width / s_)), int(round(mk.height / s_))), Image.LANCZOS)
    before = Image.new('RGB', (pw, ph), (255, 255, 255))
    before.paste(big, (int(round(-ox / s_)), int(round(-oy / s_))))
    after, tp = plan_render(L, info, trk, pal_all, box, cars, lamps, 'W86 r2: plan v52 + Vadim 22.10 + Fedya answers (houses +%.0f %% along long axes, arches %.0f x %.1f m, no north fence)' % (GROW * 100, ARCH_W, ARCH_H))
    dra = ImageDraw.Draw(after)
    for mid, rec in d['checks']['w86']['marks'].items():
        r = rec['mark_rect_local']
        a_, b_ = tp((r[0], r[3])), tp((r[2], r[1]))
        dra.rectangle([a_, b_], outline=(230, 20, 20), width=3)
        dra.text((a_[0] + 4, a_[1] + 2), mid, fill=(200, 0, 0), font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 22))
    sbs = Image.new('RGB', (pw * 2 + 30, ph), (255, 255, 255))
    sbs.paste(before, (0, 0))
    sbs.paste(after, (pw + 30, 0))
    sbs.resize((sbs.width // 2, sbs.height // 2), Image.LANCZOS).save(os.path.join(out_dir, 'rough_w86_top_vs_v52_marked.png'))
    after.save(os.path.join(out_dir, 'rough_w86_plan_full.png'))
    # crops of every changed spot: before = v52 (+ Vadim marks) at the OLD place, after = W86 at the NEW place, same scale
    spots = []
    for mid, rec in d['checks']['w86']['marks'].items():
        spots.append((mid + ' ' + rec['host'] + ': ' + rec['kind'], rec['mark_rect_v52'], rec['mark_rect_local'], 22.0))
    for a in L['arches']:
        spots.append(('arch ' + a['id'] + ' (%.1f -> %.1f m)' % (d['checks']['w86']['arches'][a['id']]['old_clear_w_m'], ARCH_W),
                      d['checks']['w86']['arches'][a['id']]['v52_rect'], a['rect'], 16.0))
    g7n = bbox([g['rect'] for g in L['garages'] if g['group'] == 'G7'])
    g7o = bbox([g['rect'] for g in v52['garages'] if g['group'] == 'G7'])
    spots.append(('coop 7 garages: raised, court 13 -> %.1f m (white strip under)' % G7_COURT, g7o, g7n, 14.0))
    gbn = bbox([g['rect'] for g in L['garages'] if g['group'] == 'GB'])
    gbo = bbox([g['rect'] for g in v52['garages'] if g['group'] == 'GB'])
    spots.append(('base-3 garages: moved west (white strip east of them)', gbo, gbn, 16.0))
    tiles = []
    for name, ro, rn, pad in spots:
        wn = grow(rn, pad)
        co = rcen(ro)
        hw, hh = (wn[2] - wn[0]) / 2, (wn[3] - wn[1]) / 2
        wo = (co[0] - hw, co[1] - hh, co[0] + hw, co[1] + hh)
        crops = []
        for img, r in ((before, wo), (after, wn)):
            a_, b_ = tp((r[0], r[3])), tp((r[2], r[1]))
            crops.append(img.crop((int(a_[0]), int(a_[1]), int(b_[0]), int(b_[1]))))
        t0, t1 = crops
        k = 420.0 / max(t0.width, t0.height)
        t0 = t0.resize((int(t0.width * k), int(t0.height * k)), Image.LANCZOS)
        t1 = t1.resize((int(t1.width * k), int(t1.height * k)), Image.LANCZOS)
        tile = Image.new('RGB', (t0.width * 2 + 16, t0.height + 34), (255, 255, 255))
        tile.paste(t0, (0, 34))
        tile.paste(t1, (t0.width + 16, 34))
        ImageDraw.Draw(tile).text((6, 4), name + '   (left v52 + marks, right W86)', fill=(20, 20, 20),
                                  font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 18))
        tiles.append(tile)
    cols = 3
    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    rows = int(math.ceil(len(tiles) / cols))
    sheet = Image.new('RGB', (cols * (tw + 12), rows * (th + 12)), (235, 235, 235))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % cols) * (tw + 12), (k // cols) * (th + 12)))
    sheet.save(os.path.join(out_dir, 'rough_w86_changed_spots.png'))
    return ['rough_w86_top_vs_v52_marked.png', 'rough_w86_plan_full.png', 'rough_w86_changed_spots.png']


def main():
    if REV == 'v01':
        raise SystemExit('s04_rough builds the W86 layout now; Data/v01 is frozen (W85). Run with MAPV85_REV=v02 (or newer).')
    d, P, Pinv, L, v52, trk, pal_all, box, cars, lamps, info = build()
    save_json('districts/rough_v85.json', d)
    overlays(d)
    imgs = plan_images(d, L, v52, info, trk, pal_all, box, cars, lamps, common.WORK)
    w = d['checks']['w86']
    print('rough_v85 (%s):' % REV, json.dumps(d['counts'], ensure_ascii=False))
    print('tracks clearance:', {k: v['min_clearance_m'] for k, v in d['checks']['tracks'].items()})
    print('van sweep tracks:', {k: v['min_clearance_m'] for k, v in w['van_sweep']['tracks'].items()})
    print('van sweep arches:', {k: (v['body_clearance_m'], {m: (e['best_exit'], e['clearance_m']) for m, e in v['mouths'].items()}) for k, v in w['van_sweep']['arches'].items()})
    print('van grid: %d / %d reachable; unreachable %s; narrow %s' % (w['van_grid']['reachable_2_3m'], w['van_grid']['targets'], w['van_grid']['unreachable'],
                                                                      w['van_grid']['reachable_but_narrow_lt_3m']))
    print('overlaps:', w['overlaps'])
    print('entrances bad:', w['entrances']['bad'])
    print('min gaps:', w['min_gaps_m']['smallest_10'])
    print('straight S->N open x:', d['checks']['straight_S_to_N_open_x_ranges'], 'W->E open z:', d['checks']['straight_W_to_E_open_z_ranges'])
    print('coop7:', w['coop7'], 'base3:', w['base3_garages'])
    print('edges:', w['edges_m'])
    print('growth:', w['growth'], 'density:', w['density'])
    print('fixes:', len(d['fixed_by_logic']), 'questions:', len(d['questions_for_vadim']), 'images:', imgs)


if __name__ == '__main__':
    main()
