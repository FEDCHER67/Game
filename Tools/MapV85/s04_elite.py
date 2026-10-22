"""Step 4 / district 07 Elite Hill ("Элитный холм"): plan picture v12 -> world v85 district data
(lead brief "Map W85 build", CL-MAP85, 2026-10-21).

Authority (handoff v10 §1, §3.2, §6, §7.7, §12 Q13; v02 §8.7; ELITE_SPEC v01 partly outdated): the plan picture
`World_v85/v85_assets/elite_v12_world.png` (1800 x 1500 px, 6 px/m, top-left = pre-shift world (1260, 450)) is the v09 plan drawing
(`build_elite_v09.py`, metres of the v11 world, X0 = 1120 -> exactly +140 m) with the v10 changes (`make_elite_v10.py`: each villa
plot crop rotated by PIL about the crop centre and pasted with an offset; west serpentine, beach gate 08 and stairs 12 removed) and v11
(`make_elite_v11.py`: west gate closed, trap gate + 6.4 m road to the EAST side, guard parking inside, guard booth outside) and v12
(label patch removed). Here the exact v09 geometry is pushed through those operations (no blob tracing), then through the <image> of the
master SVG (x 5950, y 1250, w 1500, h 1250 units = 300 x 250 m) and common.u2w (post_shift = +20 / -28 m, uniform here).
The stone road = the half ring RING of build_world_v85.py read from the master SVG (R74_elite_ring), corners filleted; piers / yachts /
east-cove loungers from the plan. The south Elite beach (cabana, loungers, FOOT_B palm row, van ruts) is NOT duplicated: it is drawn by
build_world_v85 and already lives in districts/beach_v85.json (09e-*); it is only read here for checks and the tree mask.
Trees -> veg_zone / no_tree (no tree points). Plateau objects carry absolute heights ("abs_heights": true).

Outputs: Data/<REV>/districts/elite_v85.json, out_<REV>/check_elite.png (preview x3). Run: python s04_elite.py (deterministic, ~20 s).
"""
import json
import math
import os
import re

import numpy as np
from PIL import Image, ImageDraw

from common import (GROUND, MAP_DIR, MAP_FULL, MAP_PREVIEW, REF, ROOT, WORK, H as WH, W as WW, apply, attr, ccw, centroid, contour,
                    inside, num, points_of, resample, rnd2, rrect, save_json, seg_dist, svg_tags, svg_text, u2w)

Image.MAX_IMAGE_PIXELS = None
SRC09 = os.path.join(REF, 'Desktop_Map_sources_2026-10-18', 'Элитный холм', 'build_elite_v09.py')
SRC10 = os.path.join(REF, 'World_v74', 'make_elite_v10.py')
SRC11 = os.path.join(REF, 'World_v78', 'make_elite_v11.py')
SRC12 = os.path.join(MAP_DIR, 'make_elite_v12.py')
PNG12 = os.path.join(MAP_DIR, 'v85_assets', 'elite_v12_world.png')
LAYOUT = os.path.join(REF, 'World_v11', 'Districts', 'D07_Elite_Hill_layout_v09.json')
WORLD_PY = os.path.join(MAP_DIR, 'build_world_v85.py')
CLASSES = os.path.join(WORK, 'classes_v85.npy')
X0_09, Y1_09, K09 = 1120.0, 450.0, 6.0          # build_elite_v09: P(x, y) = ((x - X0) K, (Y1 - y) K)
ROAD_W, PARAPET_W, LAMP_STEP = 4.5, 0.5, 18.0     # v10 §6 stone road 4.5 m, stone parapet outside, lamps
FENCE_GAP = 9.0                                   # W86 / plan v09: stone road edge >= 9 m from the village fence (except at the gate)
RING_W, DRIVE_W, GATE_ROAD_W = 6.4, 3.8, 6.4      # plan v09: inner ring 6.4 m, drives 3.8 m, v11 gate road 6.4 m
H_BOTTOM, H_GATE = GROUND, 44.0                   # v10 §7.7 / brief: +5 at the city -> +44 at the east gate
PLATEAU = {'N': 44.0, 'W': 41.0, 'E': 43.0, 'S': 40.0, 'C': 42.0}   # plan v10 labels "+44 / +41 / +43 / +40" (uneven plateau)
VIP = ('IShowSpeed', 'Sweetie Fox', 'Michael Jackson', 'Satoru Gojo')  # v02 §8.7 parody list (assignment to plots = OPEN)
FIXES, QUESTIONS = [], []


def fix(where, ru, why):
    FIXES.append({'id': 'elite-%02d' % (len(FIXES) + 1), 'where': rnd2(where), 'ru': ru, 'why_ru': why})


def question(ru, options, default, applied):
    QUESTIONS.append({'id': 'elite-q%d' % (len(QUESTIONS) + 1), 'ru': ru, 'options_ru': options, 'default': default, 'applied': applied})


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def R(poly):
    return [rnd2(p) for p in poly]


def closed(p):
    return list(p) + [p[0]]


def pl_d(p, pl):
    return min(seg_dist(p, a, b)[0] for a, b in zip(pl[:-1], pl[1:]))


def plen(pl):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pl[:-1], pl[1:]))


def buffer_line(pl, w):
    pts = [tuple(map(float, p)) for p in pl]
    left, right = [], []
    for i, p in enumerate(pts):
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        left.append((p[0] - dy / L * w, p[1] + dx / L * w))
        right.append((p[0] + dy / L * w, p[1] - dx / L * w))
    return ccw(left + right[::-1])


def offset_line(pl, d):
    """polyline offset to the LEFT of the direction by d (negative = right)."""
    out = []
    for i, p in enumerate(pl):
        a, b = pl[max(0, i - 1)], pl[min(len(pl) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        out.append((p[0] - dy / L * d, p[1] + dx / L * d))
    return out


def keep_off_fence(pl, fence_closed, dmin, win=4):
    """push polyline points that are closer than dmin to the fence polyline straight away from it, smooth the push over +-win points."""
    pts = [tuple(map(float, p)) for p in pl]
    push = []
    for p in pts:
        best = min((seg_dist(p, a, b) for a, b in zip(fence_closed[:-1], fence_closed[1:])), key=lambda r_: r_[0])
        d, q = best[0], best[1]
        L = math.hypot(p[0] - q[0], p[1] - q[1]) or 1.0
        push.append((max(0.0, dmin - d), ((p[0] - q[0]) / L, (p[1] - q[1]) / L)))
    amt = [m for m, _ in push]
    sm_amt = []
    for i in range(len(pts)):                                  # running max then mean: never less than needed, no kinks
        lo, hi = max(0, i - win), min(len(pts), i + win + 1)
        sm_amt.append(max(amt[lo:hi]))
    sm2 = [sum(sm_amt[max(0, i - win):i + win + 1]) / len(sm_amt[max(0, i - win):i + win + 1]) for i in range(len(pts))]
    out = [(p[0] + d_[0] * max(a_, b_), p[1] + d_[1] * max(a_, b_)) for p, (a_, d_), b_ in zip(pts, push, sm2)]
    return out, max(amt) if amt else 0.0


def ellipse(c, rx, ry, n=72):
    return [(c[0] + rx * math.cos(2 * math.pi * k / n), c[1] + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


def sat_overlap(A, B):
    for P in (A, B):
        for a, b in zip(closed(P)[:-1], closed(P)[1:]):
            n = (a[1] - b[1], b[0] - a[0])
            pa = [q[0] * n[0] + q[1] * n[1] for q in A]
            pb = [q[0] * n[0] + q[1] * n[1] for q in B]
            if max(pa) <= min(pb) or max(pb) <= min(pa):
                return False
    return True


# ---------------------------------------------------------------- sources -> one exact chain v09 metres -> world v85
def grab(src, name):
    i = src.index('\n%s = ' % name) + 1
    j = src.index('\n', i)
    while src[j + 1:j + 2] in (' ', ']', ')'):
        j = src.index('\n', j + 1)
    return src[i:j]


def load_sources():
    s09, s10, s11 = read(SRC09), read(SRC10), read(SRC11)
    ns = {'CY': 350.0}
    for name in ('VILLAS', 'FENCE', 'FBR', 'PIERS'):
        exec(grab(s09, name), ns)
    exec(re.search(r'\nRC, RX, RY = [^\n]+', s09).group(0).strip(), ns)
    X0, X1, Y0, Y1, K = eval(re.search(r'\nX0, X1, Y0, Y1, K = ([^\n]+)', s09).group(1))
    assert (X0, Y1, K) == (X0_09, Y1_09, K09), 'build_elite_v09 frame changed'
    ns['yachts'] = [eval('(' + a + ')')[:5] for a in re.findall(r'\nyacht\(([^\n]*)\)', s09)]
    ns['loungers09'] = eval(re.search(r'for k, \(x, y\) in enumerate\((\(\([^\n]*\)\))\):\s+# шезлонги', s09).group(1))
    ns['kpp_booth'] = eval(re.search(r"rect\((1180, 340\.5, 1186, 346\.2)", s09).group(1))
    ns['guard_parking'] = eval(re.search(r"rect\((1196, 354, 1206, 359)", s09).group(1))
    ns['fbr_parking'] = eval(re.search(r"rect\((1271, 343\.5, 1278\.5, 356\.5)", s09).group(1))
    ns['plots10'] = eval(re.search(r'\nplots = (\[.*?\)\)\])\n', s10, re.S).group(1))
    # v11: east road y px, x px span; crops (booth = guard parking crop, post = booth crop) and their paste offsets
    ns['v11_road'] = (int(re.search(r'\ny = (\d+)', s11).group(1)),) + tuple(int(v) for v in re.search(r'dr\.rectangle\(\[(\d+), y - 19, (\d+), y \+ 19\]', s11).groups())
    ns['v11_crop_park'] = eval(re.search(r'booth = im\.crop\((\([^)]*\))\)', s11).group(1))
    ns['v11_crop_booth'] = eval(re.search(r'post = im\.crop\((\([^)]*\))\)', s11).group(1))
    ns['v11_paste_park'] = eval(re.search(r'alpha_composite\(booth, (\([^)]*\))\)', s11).group(1))
    ns['v11_paste_booth'] = eval(re.search(r'alpha_composite\(post, (\([^)]*\))\)', s11).group(1))
    ns['v11_fence_x'] = int(re.search(r'dr\.line\(\[\((\d+), 520\), \(\d+, y - 23\)\]', s11).group(1))
    return ns


class Chain:
    def __init__(self, svg, ns):
        tag = [(at, M) for nm, at, M, g, a, b in svg_tags(svg) if nm == 'image' and 'elite_v12_world' in (attr(at, 'href') or '')]
        assert len(tag) == 1
        at, self.M = tag[0]
        self.img = (num(at, 'x'), num(at, 'y'), num(at, 'width'), num(at, 'height'))
        self.pw, self.ph = Image.open(PNG12).size
        self.plots = ns['plots10']

    def px09(self, p):
        return ((p[0] - X0_09) * K09, (Y1_09 - p[1]) * K09)

    def rot(self, k, q):
        """make_elite_v10: crop (x0, y0, x1, y1) of plot k rotated by PIL (CCW, about the crop centre), pasted at (x0 + dx, y0 + dy)."""
        (x0, y0, x1, y1), ang, (dx, dy) = self.plots[k]
        assert x0 - 1 <= q[0] <= x1 + 1 and y0 - 1 <= q[1] <= y1 + 1, 'point outside the v10 crop of plot %d: %s' % (k, q)
        cx, cy = (x1 - x0) / 2.0, (y1 - y0) / 2.0
        u, v = q[0] - x0 - cx, q[1] - y0 - cy
        a = math.radians(ang)
        return (x0 + dx + cx + u * math.cos(a) + v * math.sin(a), y0 + dy + cy - u * math.sin(a) + v * math.cos(a))

    def px2w(self, q):
        ix, iy, iw, ih = self.img
        return u2w(*apply(self.M, (ix + q[0] * iw / self.pw, iy + q[1] * ih / self.ph)))

    def w(self, p, k=None):
        q = self.px09(p)
        if k is not None:
            q = self.rot(k, q)
        return self.px2w(q)

    def w_px(self, q):
        return self.px2w(q)

    def world2px(self, p):
        ix, iy, iw, ih = self.img
        x0, y0 = self.px2w((0, 0))
        x1, y1 = self.px2w((self.pw, self.ph))
        return ((p[0] - x0) / (x1 - x0) * self.pw, (p[1] - y0) / (y1 - y0) * self.ph)


# ---------------------------------------------------------------- geometry of a v09 villa (build_elite_v09.villa, verbatim)
def villa_T(c, w, h, ang, side):
    su = 1 if side in ('NW', 'SW') else -1
    sv = 1 if side in ('NW', 'NE') else -1
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))

    def T(u, v):
        lx, ly = (u - w / 2) * su, (v - h / 2) * sv
        return (c[0] + lx * ca - ly * sa, c[1] + lx * sa + ly * ca)
    return T


def Q(T, u0, v0, u1, v1):
    return [T(u0, v0), T(u1, v0), T(u1, v1), T(u0, v1)]


def fillet(pl, i, R, n=12):
    """replace corner pl[i] by a circular arc of radius R tangent to both legs (legs taken from the neighbouring points)."""
    C = pl[i]
    a, b = pl[i - 1], pl[i + 1]
    u_in = ((C[0] - a[0]), (C[1] - a[1]))
    L = math.hypot(*u_in)
    u_in = (u_in[0] / L, u_in[1] / L)
    u_out = ((b[0] - C[0]), (b[1] - C[1]))
    L = math.hypot(*u_out)
    u_out = (u_out[0] / L, u_out[1] / L)
    th = math.acos(max(-1.0, min(1.0, u_in[0] * u_out[0] + u_in[1] * u_out[1])))
    t = R * math.tan(th / 2)
    T1 = (C[0] - u_in[0] * t, C[1] - u_in[1] * t)
    T2 = (C[0] + u_out[0] * t, C[1] + u_out[1] * t)
    cross = u_in[0] * u_out[1] - u_in[1] * u_out[0]
    nrm = (-u_in[1], u_in[0]) if cross > 0 else (u_in[1], -u_in[0])
    O = (T1[0] + nrm[0] * R, T1[1] + nrm[1] * R)
    a0 = math.atan2(T1[1] - O[1], T1[0] - O[0])
    a1 = math.atan2(T2[1] - O[1], T2[0] - O[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    arc = [(O[0] + R * math.cos(a0 + da * k / n), O[1] + R * math.sin(a0 + da * k / n)) for k in range(n + 1)]
    return pl[:i] + arc + pl[i + 1:], t


# ---------------------------------------------------------------- build
def build():
    svg = svg_text()
    ns = load_sources()
    ch = Chain(svg, ns)
    blds, props, zones = [], [], []
    # chain sanity: v09 + (160, -28) for unrotated points (image = 6 px/m, pre-shift top-left (1260, 450), post_shift (+20, -28))
    for p in ((1258.0, 350.0), (1330.0, 397.0)):
        q = ch.w(p)
        assert abs(q[0] - p[0] - 160.0) < 1e-6 and abs(q[1] - p[1] + 28.0) < 1e-6, q
    W = ch.w
    EC = W(ns['RC'])                                               # plateau / inner ring centre, world (1418, 322)
    EA, EB = 72.0, 58.5                                            # half sizes of the fence octagon (v09 144 x 117 m)

    def h_plateau(p):
        u = (p[0] - EC[0]) / EA
        v = (p[1] - EC[1]) / EB
        return PLATEAU['C'] + u * (PLATEAU['E'] - PLATEAU['W']) / 2 + v * (PLATEAU['N'] - PLATEAU['S']) / 2

    def B(bid, kind, slot, poly, floors, fh, roof, walls, notes, ents=(), height=None, tint=None, base=None, extra=None):
        b = {'id': bid, 'kind': kind, 'material_slot': slot, 'footprint': R(ccw(poly)), 'floors': floors, 'floor_h_m': fh,
             'height_m': round(height if height is not None else floors * fh, 2), 'base_abs_m': round(base, 2) if base is not None else None,
             'roof': roof, 'walls': walls, 'tint': tint, 'entrances': list(ents), 'facade_kit': 'none', 'sockets': {'windows': True},
             'collider': 'full_roof', 'disabled': False, 'notes': notes}
        if extra:
            b.update(extra)
        blds.append(b)
        return b

    def P(pid, kind, pos, rot, size, **kw):
        p = {'id': pid, 'kind': kind, 'pos': rnd2(pos), 'rot_deg': round(rot % 360, 1), 'size': [round(v, 2) for v in size], 'grip_anchor': kw.pop('grip', False)}
        p.update(kw)
        props.append(p)
        return p

    def heading(a, b):
        return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))

    # ---------------- fence (high, solid, floodlights, barbed wire); west gate closed (v11), trap gate on the EAST side
    fx = ns['FENCE']
    octa = [(1186, 302), (1186, 397), (1200, 408), (1316, 408), (1330, 397), (1330, 302), (1316, 291), (1200, 291)]
    assert all(tuple(p) in [tuple(q) for q in fx] for p in octa)
    gy, gx0, gx1 = ns['v11_road']
    assert ns['v11_fence_x'] == int((1330 - X0_09) * K09)
    g_n = Y1_09 - (gy - 23) / K09                                  # gap between the fence lines of v11 (px y - 23 .. y + 23)
    g_s = Y1_09 - (gy + 23) / K09
    gate_n, gate_s = W((1330.0, g_n)), W((1330.0, g_s))
    gate_c = ((gate_n[0] + gate_s[0]) / 2, (gate_n[1] + gate_s[1]) / 2)
    fence_line = [gate_n] + [W(p) for p in [(1330, 397), (1316, 408), (1200, 408), (1186, 397), (1186, 302), (1200, 291), (1316, 291), (1330, 302)]] + [gate_s]
    fence_poly = ccw([W(p) for p in octa])
    zones.append({'id': '07-fence', 'kind': 'fence', 'line': R(fence_line), 'material': 'elite_high_fence', 'kit': ['FN_Elite_Panel_v01', 'FN_Elite_Post_v01'],
                  'height_m': 3.5, 'solid': True, 'barbed_wire': True, 'floodlights_at_corners': R([W(p) for p in octa]),
                  'notes': 'high solid fence of the gated village (~144 x 117 m octagon, v02 §8.7), ONE opening = the trap gate on the east side; '
                           'west gate closed (plan v11, v10 §7.7); NO exit to the beach'})
    zones.append({'id': '07-gate-east', 'kind': 'gate_trap', 'pos': rnd2(gate_c), 'w_m': round(gate_n[1] - gate_s[1], 2), 'posts': [rnd2(gate_n), rnd2(gate_s)],
                  'facing_deg': 0, 'abs_height_m': H_GATE, 'gate_kit': 'FN_Elite_Gate_v01', 'barrier': {'pos': rnd2((gate_c[0] + 1.5, gate_c[1])), 'kind': 'boom_red_yellow_black'},
                  'trap': {'close_after_s': 4.0, 'guards_after_s': 2.0, 'note': 'gate latches shut right behind the van; FBI-style guards beat the players '
                           '(marker only - mechanics separate); timing 4 s + 2 s confirmed by Fedya 22.10 (item 13)'},
                  'notes': 'the only way in: stone road (outside) -> trap gate -> 6.4 m asphalt -> inner ring'})
    question('Ловушка у восточных ворот Элиты: время закрытия ворот за бусиком и появления охраны?',
             ['1 — 4 с до закрытия ворот + 2 с до охраны (предложение Феди)', '2 — другое время (назови)'], 1,
             'вариант 1: 07-gate-east.trap = {close_after_s: 4, guards_after_s: 2} (только метка, механика отдельно)')
    question('Можно ли ловить NPC на пляже Элиты (под холмом, доезд по песку с Городского пляжа)?',
             ['1 — можно, без ловушки (пляж вне забора)', '2 — можно, но там патруль охраны', '3 — нельзя (NPC не ловятся)'], 1,
             'вариант 1: пляж Элиты как обычный пляж — лежаки, бар-кабана, причалы, NPC можно ловить; патрулей в данных нет')
    # ---------------- plateau (uneven +40..+44 abs) and the inner ring + FBI
    zones.append({'id': '07-plateau', 'kind': 'plateau', 'poly': R(fence_poly), 'surface': 'lawn', 'abs_heights': True,
                  'height_field': {'type': 'plane', 'centre': rnd2(EC), 'half_size_m': [EA, EB], 'abs_m': PLATEAU,
                                   'formula': 'h = C + u (E - W) / 2 + v (N - S) / 2, u = (x - cx) / a, v = (y - cy) / b'},
                  'notes': 'uneven plateau +40..+44 m (plan labels +44 N, +41 W, +43 E, +40 S): gentle tilt to the north-east, villa plots terraced with '
                           'retaining walls on the downhill side; lawns, white paths; the gate pad +44 at the east gate'})
    ring = ellipse(EC, ns['RX'], ns['RY'], 72)
    zones.append({'id': '07-inner-ring', 'kind': 'ring_road', 'line': R(ring + [ring[0]]), 'closed': True, 'width_m': RING_W, 'surface': 'asphalt_A5d12',
                  'markings': False, 'kerb': True, 'h_abs': [round(h_plateau(p), 2) for p in ring + [ring[0]]], 'lamps': 'outer verge (s06)',
                  'notes': 'inner ring (ellipse 58 x 38 m on the axis, 6.4 m asphalt, plan v09); follows the plateau tilt (+/-0.7 m)'})
    fbr = ns['FBR']
    fb = [W((fbr[0], fbr[1])), W((fbr[2], fbr[1])), W((fbr[2], fbr[3])), W((fbr[0], fbr[3]))]
    door = W((1257.0, fbr[1]))
    B('07-05-FBI', 'fbi_post', 'elite_fbi', fb, 2, 3.5, {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.6, 'roof_units': True}, 'concrete_panel_SK3c',
      '05 FBI building in the centre of the inner ring = main guard post of the hill: dark grey-blue, 2 floors, flag, decor cameras, 3 black SUVs on the '
      'parking east of it; plan footprint 24 x 12 m (v02 §8.7 says ~28 x 14 -> question)', base=PLATEAU['C'], tint='#485462',
      ents=[{'pos': rnd2(door), 'facing_deg': 270.0, 'kind': 'door', 'w_m': 2.0, 'path_to_ring': True}])
    question('Здание ФБР: на плане Элиты (v09–v12) 24 × 12 м, в передаче v02 §8.7 «~28 × 14 м». Какой размер?',
             ['1 — 24 × 12 м, как на плане (2 этажа)', '2 — 28 × 14 м (парковка джипов сдвигается на восток)'], 1,
             'вариант 1: 07-05-FBI 24 × 12 м, 2 этажа по 3,5 м')
    fp = ns['fbr_parking']
    zones.append({'id': '07-fbi-parking', 'kind': 'parking', 'poly': R(ccw([W((fp[0], fp[1])), W((fp[2], fp[1])), W((fp[2], fp[3])), W((fp[0], fp[3]))])),
                  'surface': 'asphalt_A5d12', 'abs_height_m': PLATEAU['C'], 'notes': '3 black SUVs of the FBI (plan)'})
    for k in range(3):
        P('07-05-suv%d' % k, 'black_suv', W(((fp[0] + fp[2]) / 2, 344.2 + k * 4.1 + 1.6)), 0, [5.9, 3.2, 1.9], base_abs_m=PLATEAU['C'])
    P('07-05-flag', 'flagpole', W((1244.0, 359.5)), 0, [0.3, 0.3, 8.0], grip=True, base_abs_m=PLATEAU['C'], note='US-style flag (no text / logos)')
    for k, (x, y) in enumerate(((1240, 342), (1275, 359), (1238, 356))):
        P('07-05-camera%d' % k, 'security_camera_pole', W((x, y)), 30, [0.3, 0.3, 4.0], grip=True, base_abs_m=PLATEAU['C'])
    zones.append({'id': '07-fbi-walk', 'kind': 'path', 'line': R([door, W((1257.0, 340.5))]), 'width_m': 1.4, 'surface': 'plaza_M3', 'notes': 'walk from the FBI door to the ring'})
    # ---------------- 4 villas, irregular (v10 rotation), each on its own terrace
    for k, (vid, c, w, h, ang, side, terr, kind) in enumerate(ns['VILLAS']):
        T = villa_T(c, w, h, ang, side)
        Wk = lambda p: W(p, k)
        plot = [Wk(p) for p in Q(T, 0, 0, w, h)]
        pc = centroid(plot)
        base = round(h_plateau(pc) * 2) / 2
        if kind == 'L':
            main = [Wk(p) for p in Q(T, 3, 16.8, 29, 26.2)]
            house = [Wk(T(3, 10.5)), Wk(T(11, 10.5)), Wk(T(11, 16.8)), Wk(T(29, 16.8)), Wk(T(29, 26.2)), Wk(T(3, 26.2))]
            terrace = [Wk(p) for p in Q(T, 14, 18.5, 26, 24.5)]
            fdoor_v = 16.8
        else:
            house = [Wk(p) for p in Q(T, 3, 15.8, 30, 25.6)]
            terrace = [Wk(p) for p in Q(T, 6, 17.5, 20, 23.8)]
            fdoor_v = 15.8
        face = heading(Wk(T(16, 1.0)), Wk(T(16, 0.0)))                # -v = towards the ring
        B('07-V%s' % vid, 'villa', 'elite_villa', house, 2, 3.4,
          {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.5, 'roof_terrace': True,
           'pergola' if kind == 'R' else 'upper_terrace': R(ccw(terrace))}, 'facade_elite_villa',
          'VIP villa %s (house type %s of plan v09): white stucco volumes, dark frames, big glass, flat roof terraces, louvres, stone; '
          'never a plain box; VIP parody slot %d (%s - assignment OPEN)' % (vid, kind, k + 1, VIP[k]),
          ents=[{'pos': rnd2(Wk(T(16, fdoor_v))), 'facing_deg': round(face % 360, 1), 'kind': 'door', 'w_m': 2.0}],
          tint='#F2F0EA', base=base, extra={'house_type': kind, 'plot_id': '07-V%s-plot' % vid})
        gar = [Wk(p) for p in Q(T, w - 8.5, 1.5, w - 0.5, 9.5)]
        B('07-V%s-garage' % vid, 'garage', 'elite_garage', gar, 1, 3.2, {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.3},
          'facade_elite_villa', 'double garage 8 x 8 m at the plot corner next to the gate', tint='#ECEAE3', base=base,
          ents=[{'pos': rnd2(Wk(T(w - 4.5, 1.5))), 'facing_deg': round(face % 360, 1), 'kind': 'garage_gate', 'w_m': 6.0}])
        G = Wk(T(w - 4.5, -0.2))
        zones.append({'id': '07-V%s-plot' % vid, 'kind': 'villa_plot', 'poly': R(ccw(plot)), 'surface': 'lawn', 'terrace_abs_m': base,
                      'hedge': {'h_m': 1.8, 'w_m': 0.9, 'line': R(closed(plot))}, 'retaining_wall': R([Wk(T(-0.8, 0)), Wk(T(-0.8, h + 0.8)), Wk(T(w, h + 0.8))]),
                      'gate': {'pos': rnd2(G), 'w_m': 5.4, 'facing_deg': round(face % 360, 1)}, 'terrace_label_plan': terr,
                      'notes': 'plot %g x %g m behind a hedge, flat terrace at %.1f m abs; retaining wall on the downhill side' % (w, h, base)})
        du = 13 if kind == 'L' else 3
        zones.append({'id': '07-V%s-deck' % vid, 'kind': 'pool_deck', 'poly': R(ccw([Wk(p) for p in Q(T, du, 3, du + 21, 12.5)])), 'surface': 'boards_SK5a', 'abs_height_m': base})
        zones.append({'id': '07-V%s-pool' % vid, 'kind': 'pool', 'poly': R(ccw([Wk(p) for p in Q(T, du + 2, 4.8, du + 16, 10.2)])), 'surface': 'pool_tile',
                      'depth_m': 1.5, 'abs_height_m': base, 'notes': 'pool 14 x 5.4 m on the deck'})
        zones.append({'id': '07-V%s-path' % vid, 'kind': 'path', 'line': R([Wk(T(w - 9.5, 1)), Wk(T(w - 12, 1)), Wk(T(w - 12, 14.5)), Wk(T(16, 14.5)), Wk(T(16, fdoor_v))]),
                      'width_m': 1.1, 'surface': 'plaza_M3', 'notes': 'white path gate -> house door'})
        la = heading(Wk(T(du + 17, 0)), Wk(T(du + 20.2, 0)))
        for j in range(3):
            P('07-V%s-lounger%d' % (vid, j), 'sun_lounger', Wk(T(du + 18.6, 4.8 + j * 2.6)), la, [3.2, 1.2, 0.5], base_abs_m=base)
        P('07-V%s-umbrella' % vid, 'beach_umbrella', Wk(T(du + 18.5, 11.2)), 0, [3.2, 3.2, 2.6], base_abs_m=base)
        for j, (u, v) in enumerate(((2.5, 2.5), (2.5, h - 2.5), (w - 2.5, h - 2.5), (w - 11, 13))):
            P('07-V%s-palm%d' % (vid, j), 'palm', Wk(T(u, v)), 0, [3.4, 3.4, 8.0 + (j % 2) * 1.5], base_abs_m=base, note='designed plot palm (plan)')
        # drive: from the inner ring straight to the (rotated) plot gate (build_elite_v09 rule, re-applied after the v10 rotation)
        t = math.atan2((G[1] - EC[1]) / ns['RY'], (G[0] - EC[0]) / ns['RX'])
        Rp = (EC[0] + (ns['RX'] - 1.0) * math.cos(t), EC[1] + (ns['RY'] - 1.0) * math.sin(t))
        hr, hg = h_plateau(Rp), base
        zones.append({'id': '07-V%s-drive' % vid, 'kind': 'drive', 'line': R([Rp, G]), 'width_m': DRIVE_W, 'surface': 'asphalt_A5d12',
                      'h_abs': [round(hr, 2), round(hg, 2)], 'grade_pct': round(abs(hg - hr) / math.hypot(G[0] - Rp[0], G[1] - Rp[1]) * 100, 1),
                      'notes': 'one asphalt with the ring, no seam (plan v04+)'})
        old_G = W(T(w - 4.5, -0.2))
        if math.hypot(old_G[0] - G[0], old_G[1] - G[1]) > 1.0:
            fix(G, 'Подъезд к вилле %s проложен от кольца прямо к воротам повёрнутого участка (сдвиг ворот %.1f м)' % (vid, math.hypot(old_G[0] - G[0], old_G[1] - G[1])),
                'в v10 участки повернули и сдвинули картинкой, а нарисованные подъезды остались старые и обрываются, не доходя до ворот')
    # ---------------- east trap gate: 6.4 m asphalt from the ring through the fence; guard parking inside, guard booth outside (plan v11)
    ring_e = (EC[0] + ns['RX'], gate_c[1])
    zones.append({'id': '07-gate-road', 'kind': 'road', 'line': R([ring_e, gate_c]), 'width_m': GATE_ROAD_W, 'surface': 'asphalt_A5d12', 'markings': False,
                  'h_abs': [round(h_plateau(ring_e), 2), H_GATE], 'world_road': False, 'notes': 'plan v11: inner ring -> east trap gate, 6.4 m asphalt; '
                  'ends at the gate (outside it the stone road continues)'})
    (px0, py0, px1, py1), (qx, qy) = ns['v11_crop_park'], ns['v11_paste_park']
    gp = ns['guard_parking']
    gpx = [ch.px09((gp[0], gp[1])), ch.px09((gp[2], gp[3]))]
    gpx = [(qx + q[0] - px0, qy + q[1] - py0) for q in gpx]
    gpw = [ch.w_px(q) for q in gpx]
    gpark = ccw([(gpw[0][0], gpw[0][1]), (gpw[1][0], gpw[0][1]), (gpw[1][0], gpw[1][1]), (gpw[0][0], gpw[1][1])])
    zones.append({'id': '07-guard-parking', 'kind': 'parking', 'poly': R(gpark), 'surface': 'asphalt_A5d12', 'abs_height_m': 43.5,
                  'notes': 'guard parking inside the trap gate (plan v11 crop), 1 black SUV'})
    P('07-guard-suv', 'black_suv', centroid(gpark), 0, [4.8, 2.2, 1.9], base_abs_m=43.5)
    (bx0, by0, bx1, by1), (qx, qy) = ns['v11_crop_booth'], ns['v11_paste_booth']
    kb = ns['kpp_booth']
    bpx = [ch.px09((kb[0], kb[1])), ch.px09((kb[2], kb[3]))]
    bpx = [(qx + q[0] - bx0, qy + q[1] - by0) for q in bpx]
    bw = [ch.w_px(q) for q in bpx]
    booth = ccw([(bw[0][0], bw[0][1]), (bw[1][0], bw[0][1]), (bw[1][0], bw[1][1]), (bw[0][0], bw[1][1])])
    B('07-guard-booth', 'guard_booth', 'elite_fbi', booth, 1, 2.8, {'type': 'flat', 'material': 'roof_flat_SK4d'}, 'concrete_panel_SK3c',
      'guard booth of the trap gate, outside the fence at the end of the stone road (plan v11 "пост снаружи"), window to the road', base=H_GATE,
      ents=[{'pos': rnd2((centroid(booth)[0], max(p[1] for p in booth))), 'facing_deg': 90.0, 'kind': 'door', 'w_m': 0.9}])
    fix(gate_c, 'Шлагбаум ловушки поставлен в створ восточных ворот (в заборе), а не в 6 м снаружи на асфальтовом отростке плана v11; '
                'асфальт плана за забором заменён концом каменной дороги', 'снаружи забора дорога одна — каменная (v10 §6, §7.7); две дороги '
                'внахлёст и шлагбаум на повороте каменной дороги были бы артефактом склейки плана с картой')
    fix(gate_c, 'Смотровая площадка v09 у восточного края не строится', 'в v11 на её месте сделали въезд-ловушку (ворота, будка, парковка охраны)')
    # ---------------- the stone road (half ring 180 deg over the north slope, city -> east gate)
    rg = None
    for nm, at, M, g, a, b in svg_tags(svg):
        if nm == 'polyline' and 'R74_elite_ring' in g and attr(at, 'stroke') == '#C7BBA4':
            rg = [u2w(*p) for p in points_of(at, M)]
    assert rg and len(rg) > 100, 'R74_elite_ring stone road not found in the master SVG'
    road = [rg[0], rg[1], rg[2]] + [p for p in rg[3:-3]]
    # W86 (Fedya 22.10, v09): the stone road edge stays >= FENCE_GAP m outside the fence everywhere (the SVG ring came within 4.5 m on the
    # east leg / NE corner); points closer than the gap are pushed straight away from the fence, the push is smoothed along the road
    road, pushed = keep_off_fence(road, closed(fence_poly), FENCE_GAP + ROAD_W / 2 + 0.25)
    east_x = max(rg[-3][0], max(p[0] for p in fence_poly) + FENCE_GAP + ROAD_W / 2 + 0.25)
    if pushed > 0.05:
        fix(rg[-3], 'Каменная дорога отодвинута от забора: край полотна не ближе %.0f м к забору (было 4,5 м у восточной ветви и северо-восточного угла), '
                    'максимальный сдвиг оси %.1f м, восточная ветвь x = %.1f' % (FENCE_GAP, pushed, east_x),
            'Федя 22.10: вернуть отступ ~9 м от забора, как в плане v09 (AUDIT D7b); ось кольца SVG шла в 6,8 м от забора у угла')
    # west corner: the straight from the street meets the vertical west leg at rg[2] -> fillet R 12
    road, t_w = fillet(road, 2, 12.0)
    # east hook: down the east leg, then west into the gate -> corner (east_x, gate y), fillet R = east_x - fence x
    while road[-1][1] < gate_c[1] + 0.5:
        road.pop()
    road = road + [(east_x, gate_c[1]), gate_c]
    R_e = east_x - gate_c[0]
    road, t_e = fillet(road, len(road) - 2, R_e - 0.01)
    road = road[:-1] + [gate_c]
    fix(rg[2], 'Каменная дорога: угол у подножия (прямая от улицы -> западная ветвь) скруглён радиусом 12 м; крюк к восточным воротам — '
               'радиусом %.1f м, дорога кончается ровно в створе ворот' % R_e,
        'на карте v85 оба места — излом ~90° (кривая полукольца вертикальна у подножия, конец уходит за ворота и возвращается); '
        'бусику нужен плавный радиус, стык с воротами — без хвоста')
    rs = resample(road, 2.0)
    s = [0.0]
    for a, b in zip(rs[:-1], rs[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    Ltot = s[-1]
    # grade profile: flat 3 m at the street, ease-in 12 m, constant, ease-out 12 m, flat 4 m gate pad; solve the constant grade
    s_a, e_in, e_out, s_b = 3.0, 12.0, 12.0, 4.0

    def prof(gc):
        def g(si):
            if si < s_a or si > Ltot - s_b:
                return 0.0
            if si < s_a + e_in:
                return gc * (si - s_a) / e_in
            if si > Ltot - s_b - e_out:
                return gc * (Ltot - s_b - si) / e_out
            return gc
        hh = [H_BOTTOM]
        for a, b in zip(s[:-1], s[1:]):
            hh.append(hh[-1] + g((a + b) / 2) * (b - a))
        return hh
    lo, hi = 0.0, 0.5
    for _ in range(60):
        mid = (lo + hi) / 2
        if prof(mid)[-1] < H_GATE:
            lo = mid
        else:
            hi = mid
    gc = (lo + hi) / 2
    hh = prof(gc)
    grades = [(b - a) / (s[i + 1] - s[i]) for i, (a, b) in enumerate(zip(hh[:-1], hh[1:]))]
    lamps_s = list(np.arange(12.0, Ltot - 6.0, LAMP_STEP))
    zones.append({'id': '07-stone-road', 'kind': 'road', 'line': R(rs), 'width_m': ROAD_W, 'surface': 'cobble_SK2c', 'markings': False, 'world_road': True,
                  'parapet': 'outer', 'parapet_spec': {'side_of_line': 'left', 'material': 'stone', 'h_m': 0.7, 'w_m': PARAPET_W, 'from_s_m': 0.0, 'to_s_m': round(Ltot - 1.0, 1),
                                                       'note': 'outer = downhill side (left of the line direction city -> gate)'},
                  'lamps_every_m': LAMP_STEP, 'lamps_side': 'outer', 'lamps_s_m': [round(v, 1) for v in lamps_s],
                  'h_abs': [round(v, 2) for v in hh], 'h_note': '+%.0f at the Downtown street edge -> +%.0f at the east trap gate (abs m), per vertex' % (H_BOTTOM, H_GATE),
                  'grade': {'length_m': round(Ltot, 1), 'avg_pct': round((H_GATE - H_BOTTOM) / Ltot * 100, 2),
                            'avg_climbing_pct': round((H_GATE - H_BOTTOM) / (Ltot - s_a - s_b) * 100, 2), 'max_pct': round(max(grades) * 100, 2),
                            'limit_pct': 15.0, 'v10_target_avg_pct': 12.5},
                  'start': {'pos': rnd2(rs[0]), 'joins': 'east edge of the Downtown N-S street carriageway (perpendicular, kerb ramp, no markings on the stone)'},
                  'end': {'pos': rnd2(rs[-1]), 'joins': '07-gate-east (trap gate), then 07-gate-road'},
                  'notes': 'stone (cobbled) road 4.5 m, no markings, "not like in the city", stone parapet on the outer (downhill) side, lamps; half ring 180 deg over '
                           'the NORTH slope from the Downtown street around the village to the EAST gate (v10 §7.7, R74_elite_ring of build_world_v85); '
                           'climb starts right at the city; offset from the fence 24 -> 9 m (W86: edge >= 9 m everywhere except the gate mouth)'})
    # ---------------- Elite beach under the hill (master SVG: loungers, umbrellas, cabana, palm row FOOT_B); piers + yachts + east cove (plan)
    world_src = read(WORLD_PY)
    foot = [(x + 20.0, y - 28.0) for x, y in eval(re.search(r'\nFOOT_B = (\[[^\]]*\])', world_src).group(1))]
    umb = eval(re.search(r'\nELITE_UMB = (\([^)]*\))', world_src).group(1))
    cab, lounge, umbs, palms = None, [], [], []
    for nm, at, M, g, a, b in svg_tags(svg):
        if nm == 'rect' and attr(at, 'fill') == '#F4EFE4' and attr(at, 'stroke') == '#8E7B5A':
            x, y, w_, h_ = num(at, 'x'), num(at, 'y'), num(at, 'width'), num(at, 'height')
            cab = [u2w(*apply(M, q)) for q in ((x, y), (x + w_, y), (x + w_, y + h_), (x, y + h_))]
        elif nm == 'rect' and attr(at, 'fill') == '#FFFFFF' and attr(at, 'stroke') == '#B9B2A0':
            x, y, w_, h_ = num(at, 'x'), num(at, 'y'), num(at, 'width'), num(at, 'height')
            lounge.append(u2w(*apply(M, (x + w_ / 2, y + h_ / 2))))
        elif nm == 'circle' and attr(at, 'fill') in umb and attr(at, 'stroke') == '#5E5A50' and num(at, 'r') == 9:
            umbs.append((u2w(*apply(M, (num(at, 'cx'), num(at, 'cy')))), attr(at, 'fill')))
        elif nm == 'circle' and attr(at, 'fill') == '#8A7A55' and num(at, 'r') == 4:
            palms.append(u2w(*apply(M, (num(at, 'cx'), num(at, 'cy')))))
    assert cab and lounge and umbs, 'Elite beach objects not found in the master SVG'
    # the south Elite beach (cabana, loungers + umbrellas, FOOT_B palm row, cabana palms, van ruts) is drawn by build_world_v85 (not the Elite plan)
    # and is already in districts/beach_v85.json (09e-*): NOT duplicated here; read only for checks and the tree mask
    row = [q for q in palms if pl_d(q, foot) < 2.0]
    row.sort(key=lambda q: q[0])
    gaps = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(row[:-1], row[1:])]
    bpts = lounge + [q for q, c in umbs] + list(cab)
    beach_box = (min(p[0] for p in bpts) - 4, min(p[1] for p in bpts) - 4, max(p[0] for p in bpts) + 4, max(p[1] for p in bpts) + 3)
    fix(centroid(cab), 'Южный пляж Элиты (бар-кабана, лежаки с зонтами, ряд пальм у подножия FOOT_B с шагом ~11 м, колея по песку) в этот файл не '
                       'дублируется — он уже в beach_v85.json (09e-*); здесь только объекты плана Элиты: причалы, яхты, восточная бухта',
        'один объект — один источник данных: иначе в сборке будут две кабаны и двойной ряд пальм')
    for p in ns['PIERS']:
        zones.append({'id': '07-pier-' + p['n'], 'kind': 'pier', 'poly': R(ccw([W(q) for q in p['poly']])), 'surface': 'boards_pier_SK5a_v02', 'deck_abs_m': 1.2,
                      'notes': 'angular yacht pier on piles, bollards, ladders (plan v09; each different)'})
    for k, (x, y, L_, Wd, a_) in enumerate(ns['yachts']):
        P('07-yacht%d' % k, 'yacht', W((x, y)), a_, [L_, Wd, 4.0 if L_ > 14 else 3.0], on_water=True)
    for k, (x, y) in enumerate(ns['loungers09']):
        for j, dx in enumerate((0.65, 2.85)):
            P('07-cove-lounger%d%d' % (k, j), 'sun_lounger', W((x + dx, y + 1.6)), 90, [3.2, 1.3, 0.5], on_terrain=True)
        P('07-cove-umbrella%d' % k, 'beach_umbrella', W((x + 1.8, y + 4.2)), 0, [3.4, 3.4, 2.6], on_terrain=True)
    cpts = [p['pos'] for p in props if p['id'].startswith('07-cove-')]
    cx0, cx1 = min(p[0] for p in cpts) - 4, max(p[0] for p in cpts) + 4
    cy0, cy1 = min(p[1] for p in cpts) - 4, max(p[1] for p in cpts) + 4
    zones.append({'id': '07-east-cove', 'kind': 'beach_zone', 'poly': R(ccw([(cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1)])), 'surface': 'sand_white',
                  'notes': 'east cove of the Elite beach under the cliff (plan v09 private beach, stairs / wicket removed in v10): 3 lounger pairs with '
                           'umbrellas next to the yacht piers; reached over the sand around the south-east foot'})
    zones.append({'id': '07-notree-cove', 'kind': 'no_tree', 'poly': R(ccw([(cx0, cy0), (cx1, cy0), (cx1, cy1), (cx0, cy1)])), 'why': 'beach with loungers, pier roots'})
    return dict(blds=blds, props=props, zones=zones, ch=ch, ns=ns, EC=EC, fence_poly=fence_poly, road=rs, hh=hh, gc=gc, Ltot=Ltot, foot=foot,
                gaps=gaps, row=row, cab=cab, beach_box=beach_box, gate=gate_c, h_plateau=h_plateau)


# ---------------------------------------------------------------- vegetation zones (traced masks: candidate minus exclusions)
def vegetation(D):
    from scipy import ndimage
    zones = D['zones']
    cls = np.load(CLASSES)                                         # s01_classify: row = world y (north = last row)
    bad = np.isin(cls, [1, 2, 3, 4, 5, 6, 11])                     # sea, water, sand, asphalt, mountain rock, rock, object
    ys, xs = np.mgrid[0:WH, 0:WW]
    X, Y = xs + 0.5, ys + 0.5
    x0, x1, y0, y1 = 1262, 1560, 215, 440
    win = (X > x0) & (X < x1) & (Y > y0) & (Y < y1)

    def mask(poly):
        im = Image.new('L', (WW, WH), 0)
        ImageDraw.Draw(im).polygon([(p[0], p[1]) for p in poly], fill=255)
        return np.asarray(im) > 0
    excl = np.zeros((WH, WW), bool)
    fence_buf = [(D['EC'][0] + (p[0] - D['EC'][0]) * 1.05, D['EC'][1] + (p[1] - D['EC'][1]) * 1.05) for p in D['fence_poly']]
    excl |= mask(fence_buf)
    excl |= mask(buffer_line(D['road'], ROAD_W / 2 + PARAPET_W + 2.0))
    excl |= mask(buffer_line(D['foot'], 5.0))
    for b in D['blds']:
        excl |= mask(b['footprint'])
    for z in zones:
        if z['kind'] in ('pier', 'beach_zone', 'parking'):
            excl |= mask(z['poly'])
    bb = D['beach_box']
    excl |= mask([(bb[0], bb[1]), (bb[2], bb[1]), (bb[2], bb[3]), (bb[0], bb[3])])
    excl |= X < 1268                                               # Downtown street + sidewalk
    bad = ndimage.binary_opening(bad, iterations=1)               # ignore 1-px specks (contour lines, labels)
    cand = win & ~ndimage.binary_dilation(excl, iterations=1) & ~ndimage.binary_dilation(bad, iterations=2)
    cand = ndimage.binary_opening(cand, iterations=2)
    th = np.degrees(np.arctan2((Y - D['EC'][1]) / 58.5, (X - D['EC'][0]) / 72.0))
    sectors = [('W', (np.abs(th) > 125), 'grove', 'leafy', 'west slope between the city and the stone road (the drawn wood of the plan)'),
               ('N', (th >= 55) & (th <= 125), 'sparse', 'leafy', 'north slope around the stone road, down to the rocks'),
               ('S', (th <= -55) & (th >= -125), 'sparse', 'leafy', 'south slope between the fence and the palm row at the foot'),
               ('E', (np.abs(th) < 55), 'sparse', 'bush', 'east slope / cliff top')]
    out = []
    for sname, smask, dens, sp, name in sectors:
        lab, n = ndimage.label(cand & smask)
        for i in range(1, n + 1):
            m = lab == i
            if m.sum() < 150:
                continue
            ring = contour(m, step=2)
            if len(ring) < 4:
                continue
            out.append({'kind': 'veg_zone', 'poly': R(ccw(ring)), 'density': dens, 'species': sp, 'area_m2': int(m.sum()), 'sector': sname,
                        'notes': name + ': groups and singles with glades, Mediterranean leafy (stone pine / olive-like) + bushes; '
                                 'none on the stone road (>= 2 m from the parapet), in the village, on the beach'})
    out.sort(key=lambda z: -z['area_m2'])
    for k, z in enumerate(out):
        z['id'] = '07-veg%d' % k
        zones.append(z)
    zones.append({'id': '07-notree-village', 'kind': 'no_tree', 'poly': R(ccw(fence_buf)), 'why': 'gated village plateau: only the designed plot palms (props)'})
    zones.append({'id': '07-notree-road', 'kind': 'no_tree', 'poly': R(buffer_line(D['road'], ROAD_W / 2 + PARAPET_W + 2.0)), 'why': 'stone road + parapet + 2 m'})
    fix(D['EC'], 'Деревья плана v12 (круги на склонах) не переносятся по одному: зоны рощ / редколесья по склонам вне посёлка и дороги, на плато — только '
                 'пальмы участков', 'v10 §1.2: деревья — зонами; дерево не ставится на дорогу, в посёлок с функцией, на пляж')
    return out


# ---------------------------------------------------------------- checks and fit
def gap_to_downtown(road):
    """v10 §12 Q13: gap between the stone road (edge + parapet) and the nearest Downtown house, measured on the FINAL render."""
    from scipy import ndimage
    x0w, y0w, x1w, y1w = 1180, 260, 1300, 390
    a = np.asarray(Image.open(MAP_FULL).convert('RGB').crop((x0w * 5, (950 - y1w) * 5, x1w * 5, (950 - y0w) * 5))).astype(np.int16)
    keep = [(95, 102, 108), (229, 228, 222), (223, 234, 206), (255, 255, 255), (199, 187, 164), (140, 130, 113), (226, 235, 210)]
    bg = np.zeros(a.shape[:2], bool)
    for c in keep:
        bg |= np.all(np.abs(a - np.array(c)) < 16, axis=-1)
    house = ~bg
    house &= (np.arange(a.shape[1])[None, :] / 5 + x0w) < 1262          # Downtown only (west of the street edge)
    house = ndimage.binary_opening(house, iterations=2)
    lab, n = ndimage.label(house)
    sizes = ndimage.sum(house, lab, range(1, n + 1))
    big = np.isin(lab, [i + 1 for i, s_ in enumerate(sizes) if s_ > 25 * 25])  # >= 25 m2 at 5 px/m
    ii, jj = np.nonzero(big)
    pts = np.stack([x0w + (jj + 0.5) / 5, y1w - (ii + 0.5) / 5], 1)
    seg = [p for p in road if p[0] < 1300]
    best = 1e9
    for a_, b_ in zip(seg[:-1], seg[1:]):
        a_, b_ = np.array(a_), np.array(b_)
        v = b_ - a_
        t = np.clip(((pts - a_) @ v) / (v @ v), 0, 1)
        dd = np.hypot(*(pts - (a_ + t[:, None] * v)).T)
        best = min(best, float(dd.min()))
    return round(best - ROAD_W / 2 - PARAPET_W, 2)


def measure_fit(D):
    """footprints / pools vs the plan picture v12 (6 px/m) and vs the FINAL render (5 px/m): fraction of the inset shape on its drawn colour and
    the best extra shift in a +-2 m search."""
    ch = D['ch']
    png = np.asarray(Image.open(PNG12).convert('RGB')).astype(np.int16)
    fin_box = (1270, 160, 1600, 440)
    fin = np.asarray(Image.open(MAP_FULL).convert('RGB').crop((fin_box[0] * 5, (950 - fin_box[3]) * 5, fin_box[2] * 5, (950 - fin_box[1]) * 5))).astype(np.int16)
    VILLA = [(244, 242, 236), (226, 222, 212), (80, 88, 96), (170, 150, 120)]
    items = []
    for b in D['blds']:
        if b['kind'] == 'villa':
            items.append((b['id'], b['footprint'], VILLA))
        if b['kind'] == 'fbi_post':
            items.append((b['id'], b['footprint'], [(72, 84, 98), (88, 102, 118), (96, 108, 120), (150, 170, 190), (130, 140, 150), (40, 48, 58)]))
        if b['kind'] == 'garage':
            items.append((b['id'], b['footprint'], [(232, 230, 224), (60, 64, 70), (80, 88, 96)]))
    for z in D['zones']:
        if z['kind'] == 'pool':
            items.append((z['id'], z['poly'], [(120, 196, 228), (70, 130, 170)]))
        if z['kind'] == 'pier':
            items.append((z['id'], z['poly'], [(176, 142, 102), (120, 92, 62)]))
    res = {}
    for name, img, ppm, tp in (('plan_v12', png, 6.0, lambda p: ch.world2px(p)),
                               ('final_v85', fin, 5.0, lambda p: ((p[0] - fin_box[0]) * 5, (fin_box[3] - p[1]) * 5))):
        rows = []
        for iid, poly, col in items:
            from scipy import ndimage
            pp = [tp(p) for p in poly]
            j0, j1 = int(min(q[0] for q in pp) - 3 * ppm), int(max(q[0] for q in pp) + 3 * ppm)
            i0, i1 = int(min(q[1] for q in pp) - 3 * ppm), int(max(q[1] for q in pp) + 3 * ppm)
            sub = img[i0:i1, j0:j1]
            m = Image.new('L', (j1 - j0, i1 - i0), 0)
            ImageDraw.Draw(m).polygon([(q[0] - j0, q[1] - i0) for q in pp], fill=255)
            pm = np.asarray(m) > 0
            ring = ndimage.binary_dilation(pm, iterations=int(ppm)) & ~pm
            match = np.zeros(pm.shape, bool)
            for c_ in col:
                match |= np.all(np.abs(sub - np.array(c_)) < 14, axis=-1)
            frac0 = float((pm & match).sum()) / max(1, pm.sum())
            best = None
            rng = int(round(2 * ppm))
            for dy in range(-rng, rng + 1):
                for dx in range(-rng, rng + 1):
                    ps, rs_ = np.roll(np.roll(pm, dy, 0), dx, 1), np.roll(np.roll(ring, dy, 0), dx, 1)
                    sc = int((ps & match).sum()) - int((ps & ~match).sum()) - int((rs_ & match).sum())
                    key = (sc, -(dx * dx + dy * dy))
                    if best is None or key > best[0]:
                        best = (key, dx, dy)
            rows.append((iid, frac0, best[1] / ppm, -best[2] / ppm))
        sh = [math.hypot(r[2], r[3]) for r in rows]
        res[name] = {'items': len(rows), 'median_fill_match': round(float(np.median([r[1] for r in rows])), 3), 'min_fill_match': round(min(r[1] for r in rows), 3),
                     'max_best_shift_m': round(max(sh), 2), 'median_best_shift_m': round(float(np.median(sh)), 2),
                     'worst': [[r[0], round(r[1], 2), round(r[2], 2), round(r[3], 2)] for r in sorted(rows, key=lambda r: r[1])[:3]]}
    return res


def checks(D):
    out = {}
    blds = D['blds']
    act = [b for b in blds if not b.get('disabled')]
    out['overlaps'] = [[a['id'], b['id']] for i, a in enumerate(act) for b in act[i + 1:] if sat_overlap(a['footprint'], b['footprint'])]
    fz = D['fence_poly']
    out['inside_fence_violations'] = [b['id'] for b in blds if b['kind'] in ('villa', 'garage', 'fbi_post') and not all(inside(p, fz) for p in b['footprint'])]
    rd = D['road']
    out['road_to_fence_min_m'] = round(min(pl_d(p, closed(fz)) for p in rd if not (abs(p[0] - D['gate'][0]) < 12 and abs(p[1] - D['gate'][1]) < 12)) - ROAD_W / 2, 2)
    out['road_to_booth_min_m'] = round(min(pl_d(q, rd) for b in blds if b['id'] == '07-guard-booth' for q in b['footprint']) - ROAD_W / 2, 2)
    out['downtown_house_gap_m'] = gap_to_downtown(rd)
    out['downtown_house_gap_ok'] = out['downtown_house_gap_m'] >= 3.0
    out['foot_palm_gaps_m'] = {'n': len(D['row']), 'min': round(min(D['gaps']), 2), 'max': round(max(D['gaps']), 2)}
    drv = [z for z in D['zones'] if z['kind'] == 'drive']
    out['drive_grades_pct'] = {z['id']: z['grade_pct'] for z in drv}
    out['villa_terraces_abs_m'] = {z['id']: z['terrace_abs_m'] for z in D['zones'] if z['kind'] == 'villa_plot'}
    return out


# ---------------------------------------------------------------- check image
def overlay(dd, box, out, src=MAP_PREVIEW, s=3, ppm=1):
    x0, y0, x1, y1 = box
    im = Image.open(src).convert('RGB')
    Hm = im.height
    im = im.crop((int(x0 * ppm), int(Hm - y1 * ppm), int(x1 * ppm), int(Hm - y0 * ppm)))
    im = im.resize((im.width * s, im.height * s), Image.NEAREST)
    k = s * ppm
    tp = lambda p: ((p[0] - x0) * k, (y1 - p[1]) * k)
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for z in dd['zones']:
        if z['kind'] in ('road', 'drive', 'ring_road'):
            dl.polygon([tp(q) for q in buffer_line(z['line'], z['width_m'] / 2)], fill=(0, 220, 0, 80))
        if z['kind'] == 'veg_zone':
            dl.polygon([tp(q) for q in z['poly']], fill=(20, 140, 40, 60))
    im = Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB')
    dr = ImageDraw.Draw(im)
    for z in dd['zones']:
        if 'poly' in z and z['kind'] not in ('veg_zone', 'no_tree'):
            dr.polygon([tp(q) for q in z['poly']], outline=(0, 200, 255))
        if 'line' in z:
            col = (150, 0, 200) if z['kind'] == 'fence' else (0, 150, 0)
            dr.line([tp(q) for q in z['line']], fill=col, width=2 if z['kind'] == 'fence' else 1)
        if z['kind'] == 'gate_trap':
            x, y = tp(z['pos'])
            dr.rectangle([x - 4, y - 4, x + 4, y + 4], outline=(255, 120, 0), width=2)
    for b in dd['buildings']:
        dr.polygon([tp(p) for p in b['footprint']], outline=(255, 0, 0), width=2)
        for e in b.get('entrances', []):
            x, y = tp(e['pos'])
            dr.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(0, 0, 255))
    for p in dd['props']:
        x, y = tp(p['pos'])
        r = max(1.5, min(p['size'][0], p['size'][1]) * k / 2)
        dr.ellipse([x - r, y - r, x + r, y + r], outline=(255, 0, 255), width=1)
    im.save(out)


def main():
    D = build()
    veg = vegetation(D)
    chk = checks(D)
    fit = measure_fit(D)
    blds, props, zones = D['blds'], D['props'], D['zones']
    cnt = {'buildings': len(blds), 'by_kind': {}, 'props': len(props), 'props_by_kind': {}, 'zones': len(zones),
           'veg_zones': len(veg), 'no_tree_zones': sum(1 for z in zones if z['kind'] == 'no_tree'), 'fixes': len(FIXES), 'questions': len(QUESTIONS)}
    for b in blds:
        cnt['by_kind'][b['kind']] = cnt['by_kind'].get(b['kind'], 0) + 1
    for p in props:
        cnt['props_by_kind'][p['kind']] = cnt['props_by_kind'].get(p['kind'], 0) + 1
    road = next(z for z in zones if z['id'] == '07-stone-road')
    dd = {'district': 'elite', 'version': 'v85 from plan v12 (v09 geometry + v10 / v11 / v12 edits)',
          'sources': [os.path.relpath(p, ROOT).replace('\\', '/') for p in (PNG12, SRC09, SRC10, SRC11, SRC12, LAYOUT, WORLD_PY, os.path.join(MAP_DIR, 'VOLUNTEERS_MAP_MASTER_v85.svg'))]
          + ['docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §3.2 §6 §7.7 §12', 'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.7', 'docs/specs/ELITE_SPEC_2026-10-15_v01.md (partly outdated)'],
          'transform': 'v09 plan metres (build_elite_v09, frame X0 1120 / Y1 450, 6 px/m) -> v12 px ((x - 1120) 6, (450 - y) 6); villa plots additionally rotated '
                       'about their v10 crop centres (PIL CCW) and offset (make_elite_v10 plots); v11 crops (guard parking, booth) re-pasted; px -> master units '
                       'by the <image> (x 5950, y 1250, 1500 x 1250 for 1800 x 1500 px) -> world = common.u2w = pre-shift + (20, -28). Net for unrotated '
                       'plan points: world = v09 + (160, -28) (v11 layout JSON + 140 + post_shift). Fit: plan picture v12 median fill %.0f %%, max best '
                       'shift %.2f m; FINAL v85 render median fill %.0f %%, max best shift %.2f m (%d villas / garages / pools / FBI / piers)'
                       % (fit['plan_v12']['median_fill_match'] * 100, fit['plan_v12']['max_best_shift_m'], fit['final_v85']['median_fill_match'] * 100,
                          fit['final_v85']['max_best_shift_m'], fit['final_v85']['items']),
          'fit': fit, 'pad_height_m': None, 'abs_heights': True,
          'heights_note': 'absolute heights (m above sea 0): plateau +40..+44 (07-plateau.height_field), villas base_abs_m = terrace, FBI +42, stone road h_abs '
                          '+5 -> +44, gate pad +44; beach objects on_terrain (sand ~+1), piers deck +1.2, yachts on water',
          'lighting': 'bright_sunny_coastal', 'lighting_notes': 'Miami-like sun, warm evening lights of the villas, lamps along the stone road and the ring',
          'buildings': blds, 'props': props, 'zones': zones, 'fixed_by_logic': FIXES, 'questions_for_vadim': QUESTIONS, 'counts': cnt, 'checks': chk}
    save_json('districts/elite_v85.json', dd)
    os.makedirs(WORK, exist_ok=True)
    overlay(dd, (1255, 175, 1555, 445), os.path.join(WORK, 'check_elite.png'))
    print('elite_v85:', json.dumps(cnt, ensure_ascii=False))
    print('road:', road['grade'], 'start', road['start']['pos'], 'end', road['end']['pos'])
    print('fit:', json.dumps(fit))
    print('checks:', json.dumps(chk))


if __name__ == '__main__':
    main()
