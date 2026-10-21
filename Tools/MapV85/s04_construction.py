"""Step 4 / district 03 International Construction ("Интернациональная стройка"): plan v11 -> world v85 district data
(lead brief "Map W85 build", CL-MAP85, 2026-10-21).

Authority (handoff v10 §1, §7.3; v02 §8.3; legend D03 v08): buildings, crane, machinery, materials store, cabin town, workshop,
dormitory, guard booth, wheel wash 1:1 from plan v11 (`World_v78/Districts/build_stroyka_v11.py`, 1 unit = 0.2 m, y down) as it is
embedded in the master SVG v85 (group D03, every element with its own relayout translate of build_world_v85.py); the ONE fence =
the site contour CONSTR_POLY of build_world_v85.py with the main gate ~19 m onto the road (`_ring_gap(CONSTR_POLY, _gate, 9.5)`,
read back from the drawn polyline). Trees -> veg_zone / no_tree (the forest band 9..26 m outside the contour, as the map draws it);
lamps, crates, barrels, loose tyres -> central s06 rules (not copied). Ground: dirt with ruts and puddles, no concrete roads.
Everything the v85 drawing gets wrong (objects cut by the contour, ruts into a removed fence cut, doors facing the fence) is fixed
and logged in "fixed_by_logic"; decisions for Vadim in "questions_for_vadim".

Chain: plan local (lx, ly) -> master units apply(M, (lx, ly)) with M = D03 group transform (translate(2670 1410) translate(-410 -393))
x the element's relayout translate (clusters spread by CONSTR_SXY (1.15, 0.95) about CONSTR_LC (410, 393)) -> world = common.u2w
(post_shift is 0 at the Construction). Terrain / paths / ruts use the D03 terrain matrix (1.15, 0.95 about the centre).

Outputs: Data/<REV>/districts/construction_v85.json, out_<REV>/check_construction.png (preview x3).
Run: python s04_construction.py (deterministic, ~10 s).
"""
import json
import math
import os
import re

import numpy as np
from PIL import Image, ImageDraw

from common import (MAP_DIR, MAP_FULL, MAP_PREVIEW, REF, ROOT, WORK, apply, area, attr, ccw, centroid, inside, num, points_of,
                    rnd2, rrect, save_json, seg_dist, svg_tags, svg_text, u2w)

Image.MAX_IMAGE_PIXELS = None
PLAN_PY = os.path.join(REF, 'World_v78', 'Districts', 'build_stroyka_v11.py')
PLAN_SVG = os.path.join(REF, 'World_v78', 'Districts', 'Интернациональная_стройка_v11.svg')
WORLD_PY = os.path.join(MAP_DIR, 'build_world_v85.py')
LEGEND = os.path.join(REF, 'World_v11', 'Districts', 'D03_International_Construction_legend_v08_ru.txt')
U = 0.2                                   # plan unit, m
FENCE_CLEAR = 1.5                         # building / prop clearance from the fence, m
TRACK_W = 3.6                             # rut pair width (v10 §6 farm track)
FIXES, QUESTIONS = [], []


def fix(where, ru, why):
    FIXES.append({'id': 'constr-%02d' % (len(FIXES) + 1), 'where': rnd2(where), 'ru': ru, 'why_ru': why})


def question(ru, options, default, applied):
    QUESTIONS.append({'id': 'constr-q%d' % (len(QUESTIONS) + 1), 'ru': ru, 'options_ru': options, 'default': default, 'applied': applied})


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def R(poly):
    return [rnd2(p) for p in poly]


# ---------------------------------------------------------------- geometry helpers (local)
def pl_d(p, pl):
    return min(seg_dist(p, a, b)[0] for a, b in zip(pl[:-1], pl[1:]))


def closed(poly):
    return list(poly) + [poly[0]]


def poly_clear(poly, contour):
    """min distance of the polygon vertices/edge samples to the contour, negative if any sample lies outside."""
    best = 1e9
    for a, b in zip(closed(poly)[:-1], closed(poly)[1:]):
        for t in np.linspace(0, 1, 6):
            q = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            d = pl_d(q, closed(contour))
            best = min(best, d if inside(q, contour) else -d)
    return best


def sat_overlap(A, B, pad=0.0):
    """convex polygons overlap (separating axis), with an extra gap `pad`."""
    for P in (A, B):
        for a, b in zip(closed(P)[:-1], closed(P)[1:]):
            n = (a[1] - b[1], b[0] - a[0])
            L = math.hypot(*n) or 1.0
            n = (n[0] / L, n[1] / L)
            pa = [q[0] * n[0] + q[1] * n[1] for q in A]
            pb = [q[0] * n[0] + q[1] * n[1] for q in B]
            if max(pa) + pad <= min(pb) or max(pb) + pad <= min(pa):
                return False
    return True


def poly_gap(A, B):
    """approx gap between two convex polygons (0 if overlapping)."""
    if sat_overlap(A, B):
        return 0.0
    d = 1e9
    for P, Q in ((A, B), (B, A)):
        for p in P:
            d = min(d, pl_d(p, closed(Q)))
    return d


def ring_offset(poly, d, n=90):
    """radial offset of a polygon (build_world_v85.poly_ring without the wobble): rays from the centroid, distance d outside."""
    cx, cy = centroid(poly)
    cl = closed(poly)
    out = []
    for k in range(n):
        a = k * 2 * math.pi / n
        lo, hi = 0.0, 400.0
        for _ in range(24):
            mid = (lo + hi) / 2
            q = (cx + mid * math.cos(a), cy + mid * math.sin(a))
            if inside(q, poly) or pl_d(q, cl) < d:
                lo = mid
            else:
                hi = mid
        out.append((cx + lo * math.cos(a), cy + lo * math.sin(a)))
    return out


def ring_inset(poly, d, n=90):
    """radial inset (points at distance d inside the contour along rays from the centroid)."""
    cx, cy = centroid(poly)
    cl = closed(poly)
    out = []
    for k in range(n):
        a = k * 2 * math.pi / n
        lo, hi = 0.0, 400.0
        for _ in range(24):
            mid = (lo + hi) / 2
            q = (cx + mid * math.cos(a), cy + mid * math.sin(a))
            if inside(q, poly) and pl_d(q, cl) >= d:
                lo = mid
            else:
                hi = mid
        out.append((cx + lo * math.cos(a), cy + lo * math.sin(a)))
    return out


def buffer_line(pl, w):
    pts = [tuple(map(float, p)) for p in pl]
    left, right = [], []
    for i, p in enumerate(pts):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        left.append((p[0] + nx * w, p[1] + ny * w))
        right.append((p[0] - nx * w, p[1] - ny * w))
    return ccw(left + right[::-1])


def prop_poly(p):
    return rrect(p['pos'], max(p['size'][0], 0.6), max(p['size'][1], 0.6), p['rot_deg'])


def free_spot(pref, w, h, rot, polys, site, clear=1.0, gap=0.8, rmax=18.0):
    """nearest position to pref (spiral, 0.5 m) where rrect(pos, w, h, rot) is >= clear inside the fence and >= gap from polys."""
    for r in np.arange(0.0, rmax + 0.01, 0.5):
        n = max(1, int(2 * math.pi * r / 0.5))
        for k in range(n):
            a = 2 * math.pi * k / n
            q = (pref[0] + r * math.cos(a), pref[1] + r * math.sin(a))
            poly = rrect(q, w, h, rot)
            if poly_clear(poly, site) < clear:
                continue
            if any(poly_gap(poly, P_) < gap for P_ in polys):
                continue
            return q
    raise SystemExit('no free spot near %s' % (pref,))


class Router:
    """A* on a 0.5 m grid inside the site, obstacles inflated by `infl`; paths simplified (Douglas-Peucker) + Chaikin."""

    def __init__(self, site, obst, infl, box, cell=0.5):
        from scipy import ndimage
        self.x0, self.y0, x1, y1 = box
        self.c = cell
        nx, ny = int((x1 - self.x0) / cell), int((y1 - self.y0) / cell)

        def mask(polys):
            im = Image.new('L', (nx, ny), 0)
            dr = ImageDraw.Draw(im)
            for o in polys:
                dr.polygon([((q[0] - self.x0) / cell - 0.5, (q[1] - self.y0) / cell - 0.5) for q in o], fill=255)
            return np.asarray(im) > 0                                   # row = y index (north = larger row)
        occ = mask(obst)
        ins = mask([site])
        dist = ndimage.distance_transform_edt(~occ) * cell
        dfence = ndimage.distance_transform_edt(ins) * cell
        self.free = (dist > infl) & (dfence > infl)
        self.cost = 1.0 + 2.0 * np.clip((infl + 2.5 - dist) / 2.5, 0, 1)        # prefer the middle of a passage

    def cell(self, p):
        return int((p[1] - self.y0) / self.c), int((p[0] - self.x0) / self.c)

    def snap(self, p):
        i, j = self.cell(p)
        fi, fj = np.nonzero(self.free)
        k = int(np.argmin((fi - i) ** 2 + (fj - j) ** 2))
        return int(fi[k]), int(fj[k])

    def route(self, a, b):
        import heapq
        s, t = self.snap(a), self.snap(b)
        ny, nx = self.free.shape
        g = {s: 0.0}
        prev = {}
        h = lambda q: math.hypot(q[0] - t[0], q[1] - t[1])
        pq = [(h(s), s)]
        nb = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1), (-1, -1, 1.4142), (-1, 1, 1.4142), (1, -1, 1.4142), (1, 1, 1.4142)]
        while pq:
            f, q = heapq.heappop(pq)
            if q == t:
                break
            for di, dj, w in nb:
                r_ = (q[0] + di, q[1] + dj)
                if not (0 <= r_[0] < ny and 0 <= r_[1] < nx) or not self.free[r_]:
                    continue
                ng = g[q] + w * self.cost[r_]
                if ng < g.get(r_, 1e18):
                    g[r_] = ng
                    prev[r_] = q
                    heapq.heappush(pq, (ng + h(r_), r_))
        assert t in g, 'no route %s -> %s' % (a, b)
        path = [t]
        while path[-1] != s:
            path.append(prev[path[-1]])
        pts = [(self.x0 + (j + 0.5) * self.c, self.y0 + (i + 0.5) * self.c) for i, j in path[::-1]]
        return dp(pts, 1.0)


def dp(pts, tol):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dmax, k = -1.0, 0
    for i in range(1, len(pts) - 1):
        dd = seg_dist(pts[i], a, b)[0]
        if dd > dmax:
            dmax, k = dd, i
    if dmax <= tol:
        return [a, b]
    return dp(pts[:k + 1], tol)[:-1] + dp(pts[k:], tol)


def chaikin_keep(p, n=2):
    for _ in range(n):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        q.append(p[-1])
        p = q
    return p


def rect_local(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def rr_local(c, w, h, ang):                                     # build_stroyka_v11.rr (y down)
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + dx * ca - dy * sa, c[1] + dx * sa + dy * ca) for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


def tr_local(c, ang, p):                                        # build_stroyka_v11.tr
    a = math.radians(ang)
    return (c[0] + p[0] * math.cos(a) - p[1] * math.sin(a), c[1] + p[0] * math.sin(a) + p[1] * math.cos(a))


# ---------------------------------------------------------------- sources
def plan_consts():
    """constants of build_stroyka_v11.py (layout only)."""
    src = read(PLAN_PY)
    ns = {}
    for name in ('FENCE', 'GATE_MAIN', 'GATE_SHOP', 'GATE_EAST', 'CRANE', 'GAP', 'BLOCKS', 'EAST_BLOCK', 'SERVICE_ROW', 'OFFICE', 'CUTS', 'DORM', 'WORKSHOP'):
        i = src.index('\n%s = ' % name) + 1
        j = src.index('\n', i)
        while src[j + 1:j + 2] == ' ':
            j = src.index('\n', j + 1)
        exec(src[i:j], ns)
    return ns


def world_consts():
    """CONSTR_SHAPE_W (= CONSTR_POLY, the site contour) and _gate of build_world_v85.py."""
    src = read(WORLD_PY)
    m = re.search(r'\nCONSTR_SHAPE_W = (\[.*?\]\])\n', src, re.S)
    shape = eval(m.group(1))
    gate = eval(re.search(r'\n_gate = (\([^)]*\))', src).group(1))
    road_h = eval(re.search(r'\nROAD_H = (\[[^\]]*\])', src).group(1))
    road_v = eval(re.search(r'\nROAD_VALLEY = (\[[^\]]*\])', src).group(1))
    return [tuple(map(float, p)) for p in shape], gate, road_h, road_v


class D03:
    """elements of group D03 in the master SVG: local points + full affine."""

    def __init__(self, svg):
        self.items = []
        self.fence, self.posts = None, []
        for nm, at, M, g, a, b in svg_tags(svg):
            if nm == 'polyline' and attr(at, 'stroke') == '#6E8AA6' and 'D03' not in g:
                self.fence = [u2w(*p) for p in points_of(at, M)]
            if 'D03' not in g:
                continue
            sub = next((x for x in reversed(g) if x.startswith('d03_')), '')
            if nm in ('polygon', 'polyline'):
                self.items.append((sub, nm, attr(at, 'fill'), attr(at, 'stroke'), points_of(at), M))
            elif nm == 'circle':
                self.items.append((sub, nm, attr(at, 'fill'), attr(at, 'stroke'), [(num(at, 'cx'), num(at, 'cy'))], M, num(at, 'r')))
        self.Mterr = next(it[5] for it in self.items if it[0] == 'd03_terrain')

    def find(self, sub, fill, local, tol=0.8, nm=None):
        for it in self.items:
            if it[0] != sub or (fill is not None and it[2] != fill) or (nm and it[1] != nm):
                continue
            pts = it[4]
            if len(pts) != len(local) and nm != 'circle':
                continue
            if all(math.hypot(p[0] - q[0], p[1] - q[1]) < tol for p, q in zip(pts, local)):
                return it[5]
        raise SystemExit('D03 element not found: %s %s %s' % (sub, fill, local[:2]))

    @staticmethod
    def W(M, p):
        return u2w(*apply(M, p))

    def place(self, sub, fill, local, nm=None):
        M = self.find(sub, fill, local, nm=nm)
        return [self.W(M, p) for p in local], M

    def terr(self, p):
        return u2w(*apply(self.Mterr, p))


# ---------------------------------------------------------------- build
def build():
    svg = svg_text()
    pc = plan_consts()
    shape, gate_q, road_h, road_v = world_consts()
    d = D03(svg)
    site = ccw(shape)
    assert d.fence and len(d.fence) >= 10, 'drawn Construction fence (stroke #6E8AA6) not found in the master SVG'
    on_contour = max(pl_d(p, closed(site)) for p in d.fence)
    assert on_contour < 0.2, 'drawn fence is not on CONSTR_POLY (%.2f m)' % on_contour
    gate_w = math.hypot(d.fence[0][0] - d.fence[-1][0], d.fence[0][1] - d.fence[-1][1])
    gate_c = ((d.fence[0][0] + d.fence[-1][0]) / 2, (d.fence[0][1] + d.fence[-1][1]) / 2)
    W = d.W
    blds, props, zones = [], [], []
    moved = {}

    def B(bid, kind, slot, poly, floors, fh, roof, walls, notes, ents=(), height=None, tint=None, extra=None):
        b = {'id': bid, 'kind': kind, 'material_slot': slot, 'footprint': R(ccw(poly)), 'floors': floors, 'floor_h_m': fh,
             'height_m': round(height if height is not None else floors * fh, 2), 'roof': roof, 'walls': walls, 'tint': tint,
             'entrances': list(ents), 'facade_kit': 'none', 'sockets': {'windows': kind not in ('scaffold', 'cargo_hoist', 'foundation_slab', 'fuel_canopy')},
             'collider': 'full_roof', 'disabled': False, 'notes': notes}
        if extra:
            b.update(extra)
        blds.append(b)
        return b

    def P(pid, kind, pos, rot, size, **kw):
        p = {'id': pid, 'kind': kind, 'pos': rnd2(pos), 'rot_deg': round(rot, 1), 'size': [round(v, 2) for v in size], 'grip_anchor': kw.pop('grip', False)}
        p.update(kw)
        props.append(p)
        return p

    def ent(pos, facing, kind='door', w=1.0, **kw):
        e = {'pos': rnd2(pos), 'facing_deg': round(facing % 360, 1), 'kind': kind, 'w_m': w}
        e.update(kw)
        return e

    def fac(M, vec):                                           # local direction (y down) -> world heading, deg
        o, q = W(M, (0, 0)), W(M, vec)
        return math.degrees(math.atan2(q[1] - o[1], q[0] - o[0]))

    def rot_w(ang_local):                                      # rr angle (y down, clockwise) -> world CCW deg
        return -ang_local

    flat = lambda m='roof_flat_SK4d', **kw: dict({'type': 'flat', 'material': m}, **kw)
    frame_note = 'unfinished: bare grey concrete frame, no glazing'

    # ---------------- 04 building A: 24 x 14 m frame, top floor open, scaffolding south, cargo hoist east, crane next to it
    fa, MA = d.place('d03_buildings', '#D8D7D1', rect_local(190, 200, 310, 270))
    top, _ = d.place('d03_buildings', '#C9C8C1', rect_local(250, 200, 310, 235))
    cols = [W(MA, (x, y)) for x in range(200, 306, 20) for y in (210, 235, 260)]
    core, _ = d.place('d03_buildings', '#B9BCB8', rect_local(236, 222, 256, 250))
    B('03-04-A', 'concrete_frame', 'construction_frame', fa, 5, 3.0,
      flat('concrete_SK3c', open_frame=True, top_floor_open=True, top_floor_slab_poly=R(ccw(top))), 'concrete_SK3c',
      '04 building A (plan v11 "небольшой недострой" 24 x 14 m): monolithic frame, slabs on 18 columns (columns_xy), floors 1-4 slabs + edge '
      'railings, top floor (5th) open: columns + slab only over top_floor_slab_poly (drawn lighter on the plan); walkable slabs; ' + frame_note,
      extra={'columns_xy': R(cols), 'column_m': 0.6, 'core_id': '03-04-A-core', 'crane_id': '03-06-crane', 'floors_note': 'floor count not on plan v11: 5 from legend v08 / handoff v02 §8.3'})
    B('03-04-A-core', 'stair_lift_core', 'construction_frame', core, 5, 3.0, flat('concrete_SK3c'), 'concrete_SK3c',
      'stair / lift core of building A (one core on plan v11), up to the open top floor + 1 m', height=16.0)
    sc, _ = d.place('d03_buildings', '#E6C98F', rect_local(190, 270, 310, 280))
    B('03-04-A-scaffold', 'scaffold', 'construction_frame', sc, 5, 3.0, {'type': 'none'}, 'metal_painted_SK6a',
      'scaffolding along the south face of A (2 m deep, diagonal braces, planks every floor), climbable, collider per deck', height=15.5)
    ho, MH = d.place('d03_buildings', '#7C8083', rect_local(310, 226, 322, 244))
    B('03-04-A-hoist', 'cargo_hoist', 'construction_frame', ho, 1, 17.0, {'type': 'none'}, 'metal_painted_SK6a',
      'cargo hoist mast on the east face of A with the cage at the ground', height=17.0,
      ents=[ent(W(MH, (322, 235)), fac(MH, (1, 0)), 'gate', 2.0)])
    # ---------------- 05 building B: 20 x 12 m slab + first columns
    fb, MB = d.place('d03_buildings', '#CFCFC8', rect_local(190, 430, 290, 490))
    bcols = [W(MB, (x, y)) for x in (200, 220) for y in (440, 460, 480)]
    rebar = [W(MB, (x, y)) for x in (240, 260, 280) for y in (440, 460, 480)]
    B('03-05-B', 'foundation_slab', 'construction_frame', fb, 1, 0.6, flat('concrete_SK3c'), 'concrete_SK3c',
      '05 building B (20 x 12 m): foundation slab 0.6 m, first 6 columns 3 m high (columns_xy) and rebar starters (rebar_xy), formwork', height=0.6,
      extra={'columns_xy': R(bcols), 'column_m': 0.7, 'column_h_m': 3.0, 'rebar_xy': R(rebar)})
    for k, x in enumerate((204, 234)):
        fw, M_ = d.place('d03_buildings', '#D2B48C', rect_local(x, 466, x + 24, 476))
        c = centroid(fw)
        P('03-05-formwork%d' % k, 'formwork_panels', c, fac(M_, (1, 0)), [4.8, 2.0, 1.2])
    # ---------------- 08 dormitory: old 4-storey
    c0, a0, w0, h0 = pc['DORM']
    fd, MD = d.place('d03_buildings', '#D4CBBB', rr_local(c0, w0, h0, a0))
    dents = []
    for x in (-40, 40):
        cp = tr_local(c0, a0, (x, h0 / 2 + 4))
        d.find('d03_buildings', '#8E979B', rr_local(cp, 16, 8, a0))
        dents.append(ent(W(MD, tr_local(c0, a0, (x, h0 / 2))), fac(MD, (0, 1)), 'door', 1.4, canopy=True))
    B('03-08-dorm', 'old_dormitory', 'construction_dorm', fd, 4, 3.0, flat('roof_flat_SK4d', parapet_h_m=0.5), 'stucco_SK3b_v07',
      '08 migrants dormitory: old 4-storey block 34 x 11.2 m, two entrances with canopies to the yard in front (south)', ents=dents)
    # ---------------- 07 cabin town: one-storey block containers 6 x 2.4 m, ~3 m passages, separate group by the east fence
    step = 12 + pc['GAP']
    cols_ = ('#8FA9B8', '#C9D2D8', '#A9C0CC', '#8FA9B8', '#C8BFA8', '#9DB1BE', '#A47E62', '#C9D2D8', '#8FA9B8')
    cabins = []
    k_ = 0
    for (x0, y0), n, ang, side in pc['BLOCKS']:
        for i in range(n):
            c = tr_local((x0, y0), ang, (i * step + 6, 15))
            col = cols_[(i * 7 + int(x0)) % len(cols_)]
            fp, M_ = d.place('d03_buildings', col, rr_local(c, 12, 30, ang))
            dv = 15 if side == 'S' else -15
            k_ += 1
            cabins.append(B('03-07-cabin%02d' % k_, 'site_cabin', 'construction_cabin', fp, 1, 2.6, flat('metal_painted_SK6a'), 'metal_painted_SK6a',
                            'block container 6 x 2.4 m, one storey, porch step, row %s' % ('A (doors S)' if side == 'S' else 'B (doors N)'),
                            ents=[ent(W(M_, (c[0], c[1] + dv)), fac(M_, (0, 1 if side == 'S' else -1)), 'door', 0.9, steps=1)], tint=col))
    (x0, y0), n, ang = pc['EAST_BLOCK']
    for i in range(n):
        c = tr_local((x0, y0), ang, (15, i * step + 6))
        fp, M_ = d.place('d03_buildings', cols_[(i * 5 + 3) % len(cols_)], rr_local(c, 30, 12, ang))
        k_ += 1
        cabins.append(B('03-07-cabin%02d' % k_, 'site_cabin', 'construction_cabin', fp, 1, 2.6, flat('metal_painted_SK6a'), 'metal_painted_SK6a',
                        'block container across, at the east fence', ents=[ent(W(M_, (c[0] - 15, c[1])), fac(M_, (-1, 0)), 'door', 0.9)],
                        tint=cols_[(i * 5 + 3) % len(cols_)]))
    (x0, y0), parts, ang = pc['SERVICE_ROW']
    kk = 0
    for col, m in parts:
        for i in range(m):
            c = tr_local((x0, y0), ang, (kk * step + 6, 15))
            fp, M_ = d.place('d03_buildings', col, rr_local(c, 12, 30, ang))
            kind = 'canteen' if col == '#C8BFA8' else 'shower'
            cabins.append(B('03-07-%s%d' % (kind, kk), kind, 'construction_cabin', fp, 1, 2.6, flat('metal_painted_SK6a'), 'metal_painted_SK6a',
                            '%s container 6 x 2.4 m' % kind, ents=[ent(W(M_, (c[0], c[1] - 15)), fac(M_, (0, -1)), 'door', 0.9)], tint=col))
            kk += 1
    (x0, y0), n, ang = pc['OFFICE']
    c = tr_local((x0, y0), ang, (6, 15))
    fp, M_ = d.place('d03_buildings', '#DDE2E5', rr_local(c, 12, 30, ang))
    cabins.append(B('03-07-office', 'foreman_office', 'construction_cabin', fp, 1, 2.6, flat('metal_painted_SK6a'), 'metal_painted_SK6a',
                    'foreman office container at the east end of row A', ents=[ent(W(M_, (c[0], c[1] + 15)), fac(M_, (0, 1)), 'door', 0.9)], tint='#DDE2E5'))
    # ---------------- 03 guard booth + wheel wash at the main gate
    fg, MG = d.place('d03_buildings', '#B5C8CE', rect_local(456, 640, 480, 662))
    B('03-03-guard', 'guard_booth', 'construction_cabin', fg, 1, 2.6, flat(), 'metal_painted_SK6a', '03 guard booth at the main gate (no barrier, gates open)',
      ents=[ent(W(MG, (456, 651)), fac(MG, (-1, 0)), 'door', 0.9)])
    ww, Mw = d.place('d03_objects', '#9AA3A8', rect_local(398, 632, 436, 658))
    P('03-03-wheelwash', 'wheel_wash', centroid(ww), fac(Mw, (0, 1)), [7.6, 5.2, 0.4], note='drive-over grate + low pump box, on the van path behind the gate')
    # ---------------- 01 van upgrade workshop (+ van, tyres, scrap, rusty body in front)
    c1, a1, w1, h1 = pc['WORKSHOP']
    fw_, MW = d.place('d03_buildings', '#C6AB97', rect_local(c1[0] - w1 / 2, c1[1] - h1 / 2, c1[0] + w1 / 2, c1[1] + h1 / 2))
    ws_items = []
    van, Mv = d.place('d03_objects', '#8E979B', rect_local(590, 650, 626, 666))
    ws_items.append(('03-01-van', 'van_on_jacks', centroid(van), [7.2, 3.2, 2.4]))
    for k, c2 in enumerate(((690, 650), (700, 660), (690, 668))):
        M_ = d.find('d03_objects', '#3F4447', [c2], nm='circle')
        ws_items.append(('03-01-tyres%d' % k, 'tyre_stack', W(M_, c2), [1.0, 1.0, 1.2]))
    Ms = next(it[5] for it in d.items if it[0] == 'd03_objects' and it[2] == '#9A8F7E')
    ws_items.append(('03-01-scrap', 'scrap_metal_pile', W(Ms, (560, 640)), [4.8, 3.2, 1.4]))
    rb, Mr = d.place('d03_objects', '#9B6A50', rr_local((690, 590), 30, 14, 76))
    ws_items.append(('03-01-rustybody', 'rusty_car_body', centroid(rb), [6.0, 2.8, 1.6]))
    ws = (fw_, ws_items, h1)                                     # placed after all other objects (see below)
    # ---------------- transformer + water tank (drawn outside the fence at the SW): moved inside next to each other
    ft, Mt = d.place('d03_objects', '#9DB1BE', rect_local(140, 612, 162, 634))
    Mtank = d.find('d03_objects', '#A9B7C2', [(152, 660)], nm='circle')
    tank = W(Mtank, (152, 660))
    best = None
    for dy in np.arange(0, 30.1, 0.5):
        for dx in np.arange(0, 30.1, 0.5):
            poly = [(p[0] + dx, p[1] + dy) for p in ft]
            tq = (tank[0] + dx, tank[1] + dy)
            tp = rrect(tq, 3.6, 3.6, 0)
            if poly_clear(poly, site) < FENCE_CLEAR or poly_clear(tp, site) < FENCE_CLEAR:
                continue
            if any(poly_gap(poly, b['footprint']) < 2.0 or poly_gap(tp, b['footprint']) < 2.0 for b in blds):
                continue
            L = math.hypot(dx, dy)
            if best is None or L < best[0]:
                best = (L, dx, dy)
    _, tdx, tdy = best
    ft2 = [(p[0] + tdx, p[1] + tdy) for p in ft]
    B('03-03-transformer', 'transformer_booth', 'generic_concrete', ft2, 1, 2.8, flat(), 'brick_SK3a', 'transformer substation 4.4 x 4.4 m, "do not enter" sign')
    P('03-03-watertank', 'water_tank', (tank[0] + tdx, tank[1] + tdy), 0, [3.6, 3.6, 2.4])
    fix(centroid(ft), 'Трансформаторная и бак с водой перенесены внутрь забора на (%.1f, %.1f) м' % (tdx, tdy),
        'на карте v85 они остались снаружи контура площадки (у юго-западного угла забора) — так не бывает, хозяйство стройки внутри забора')
    # ---------------- 02 small fuel station (outside, by the road): kept, DISABLED (v10 §7.3 / §12: ask Vadim)
    fz, Mf = d.place('d03_buildings', '#ECEEEF', rect_local(162, 764, 222, 798))
    fk, Mk = d.place('d03_buildings', '#CAD5D7', rect_local(230, 774, 256, 802))
    pad, _ = d.place('d03_roads', '#CDD3D5', rect_local(150, 756, 262, 820))
    xc_ = centroid(fz)[0]
    seg_ = next((a, b) for a, b in zip(road_h[:-1], road_h[1:]) if a[0] <= xc_ <= b[0])
    edge = seg_[0][1] + (seg_[1][1] - seg_[0][1]) * (xc_ - seg_[0][0]) / (seg_[1][0] - seg_[0][0]) - 3.2   # south edge of ROAD_H (6.4 m)
    fdy = min(0.0, edge - 1.0 - max(p[1] for p in fz + fk))
    sh = lambda poly: [(p[0], p[1] + fdy) for p in poly]
    fz2, fk2, pad2 = sh(fz), sh(fk), sh(pad)
    pad2 = [(p[0], min(p[1], edge) if p[1] < edge else edge) for p in pad2]
    B('03-02-fuel-canopy', 'fuel_canopy', 'generic_concrete', fz2, 1, 4.6, flat('metal_painted_SK6a'), None,
      '02 small fuel station: canopy on 4 columns, one pump island; DISABLED until Vadim answers (v10 §7.3)', extra={'disabled': True})
    B('03-02-fuel-kiosk', 'kiosk', 'generic_concrete', fk2, 1, 2.8, flat(), 'concrete_panel_SK3c', '02 fuel station cash kiosk; DISABLED', extra={'disabled': True})
    P('03-02-fuel-pump', 'fuel_pump_island', centroid(sh(d.place('d03_buildings', '#8E979B', rect_local(178, 778, 206, 784))[0])), 0, [5.6, 1.2, 1.8], disabled=True)
    pad_poly = ccw([(min(p[0] for p in pad2), min(p[1] for p in pad2)), (max(p[0] for p in pad2), min(p[1] for p in pad2)),
                    (max(p[0] for p in pad2), edge), (min(p[0] for p in pad2), edge)])
    zones.append({'id': '03-02-fuel-pad', 'kind': 'fuel_pad', 'poly': R(pad_poly), 'surface': 'concrete_SK3c', 'disabled': True,
                  'notes': 'apron of the fuel station, touching the south edge of the main road ROAD_H (two entries from the road)'})
    if fdy:
        fix(centroid(fz), 'АЗС (выключена) сдвинута на %.1f м к югу: навес и касса теперь в 1 м от южной кромки главной дороги, площадка '
                          'примыкает к дороге' % (-fdy),
            'в мастере v85 (кластерный разнос) навес АЗС лёг на полотно главной дороги ROAD_H; на карте v85 АЗС не видна (за клипом стройки)')
    question('АЗС у Стройки (канон её сохраняет, в v85 её не видно, Федя отвечал «пока не ставить»). Ставить?',
             ['1 — пока не ставить (в данных есть, выключена "disabled": true)', '2 — ставить у главной дороги к юго-западу от ворот, как в плане v11',
              '3 — убрать совсем'], 1, 'вариант 1: 03-02-fuel-* в данных с "disabled": true, площадка у южной кромки дороги ROAD_H')
    # ---------------- 06 tower crane (next to A)
    Mc = d.find('d03_objects', '#E2B13B', rect_local(pc['CRANE'][0] - 8, pc['CRANE'][1] - 8, pc['CRANE'][0] + 8, pc['CRANE'][1] + 8))
    mast = W(Mc, pc['CRANE'])
    jib_c = W(Mc, (pc['CRANE'][0] - 72, pc['CRANE'][1] - 40))
    jib_deg = math.degrees(math.atan2(jib_c[1] - mast[1], jib_c[0] - mast[0]))
    P('03-06-crane', 'tower_crane', mast, jib_deg, [3.2, 3.2, 32.0], jib_len_m=30.0, counter_jib_len_m=9.2, slew_radius_m=30.0, grip=True,
      note='06 tower crane at building A: mast 3.2 m (base 3.2 x 3.2 with ballast), hook height ~30 m over the 5-storey frame, jib over A; '
           'rot_deg = jib heading; dashed circle on the plan = jib reach 30 m')
    # ---------------- materials store (bricks, blocks, rebar, formwork, pipes, sand, gravel) + formwork shields at the buildings
    store = []
    for it in d.items:
        if it[0] != 'd03_objects':
            continue
        sub, nm, fill, stroke, pts, M_ = it[:6]
        wp = [W(M_, p) for p in pts]
        kind = {'#B5705A': 'pallet_bricks', '#C3C6BF': 'pallet_blocks'}.get(fill) if nm == 'polygon' else None
        if kind and len(pts) == 4:
            store.append(wp)
            P('03-03-%s%d' % (kind, sum(1 for p in props if p['kind'] == kind)), kind, centroid(wp), fac(M_, (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])), [3.2, 3.2, 1.2])
    reb = [W(it[5], p) for it in d.items if it[0] == 'd03_objects' and it[1] == 'polyline' and it[3] == '#8E5B42' for p in it[4]]
    rc = (sum(p[0] for p in reb) / len(reb), sum(p[1] for p in reb) / len(reb))
    P('03-03-rebar', 'rebar_bundles', rc, 0, [13.0, 3.0, 0.5])
    store.append(rrect(rc, 13, 3, 0))
    for k, it in enumerate([it for it in d.items if it[0] == 'd03_objects' and it[2] == '#D2B48C' and abs(it[4][1][0] - it[4][0][0]) > 40]):
        wp = [W(it[5], p) for p in it[4]]
        store.append(wp)
        P('03-03-formwork-stack%d' % k, 'formwork_stack', centroid(wp), fac(it[5], (it[4][1][0] - it[4][0][0], it[4][1][1] - it[4][0][1])), [12.4, 1.6, 1.0])
    for k, it in enumerate([it for it in d.items if it[0] == 'd03_objects' and it[2] == '#9AA3A8' and len(it[4]) == 4 and abs(it[4][1][0] - it[4][0][0]) > 40]):
        wp = [W(it[5], p) for p in it[4]]
        store.append(wp)
        P('03-03-pipes%d' % k, 'pipe_stack', centroid(wp), fac(it[5], (it[4][1][0] - it[4][0][0], it[4][1][1] - it[4][0][1])), [12.4, 0.8, 0.8])
    for fill, kind, size in (('#EBD9A2', 'sand_pile', [7.2, 6.0, 1.8]), ('#BDBDB4', 'gravel_pile', [5.2, 4.4, 1.5])):
        it = next(it for it in d.items if it[0] == 'd03_objects' and it[2] == fill)
        wp = [W(it[5], p) for p in it[4]]
        store.append(wp)
        P('03-03-' + kind, kind, centroid(wp), 0, size, footprint=R(ccw(wp)))
    for k, (c, a) in enumerate((((350, 330), 12), ((158, 420), -8), ((356, 560), 20), ((206, 560), -14))):
        wp, M_ = d.place('d03_objects', '#D2B48C', rr_local(c, 34, 7, a))
        P('03-03-shields%d' % k, 'formwork_shields', centroid(wp), rot_w(a), [6.8, 1.4, 1.2])
    allp = [p for poly in store for p in poly]
    xs_, ys_ = [p[0] for p in allp], [p[1] for p in allp]
    # ---------------- machinery, bins, toilets, bus, cabin-yard life
    mx, Mm = d.place('d03_objects', '#B9C3C8', rect_local(238, 362, 286, 382))
    P('03-03-mixer-truck', 'concrete_mixer_truck', centroid(mx), fac(Mm, (1, 0)), [9.6, 4.0, 3.4])
    for fill, c, w_, h_, a, kind, sz in (('#C7A04D', (360, 570), 44, 18, -8, 'dump_truck', [8.8, 3.6, 3.2]), ('#E2B13B', (262, 590), 22, 14, 20, 'wheel_loader', [4.4, 2.8, 3.0]),
                                         ('#E2C24E', (678, 300), 40, 14, -2, 'paz_bus', [8.0, 2.8, 3.0])):
        wp, M_ = d.place('d03_objects', fill, rr_local(c, w_, h_, a))
        P('03-%s' % kind.replace('_', '-'), kind, centroid(wp), rot_w(a), sz, note='PAZ bus of the workers at the cabin town' if kind == 'paz_bus' else '')
    for k, (r_, kind) in enumerate((((470, 604, 504, 622), 'skip_bin'), ((646, 478, 668, 492), 'skip_bin'))):
        wp, M_ = d.place('d03_objects', '#6F7D74', rect_local(*r_))
        P('03-%s%d' % (kind.replace('_', '-'), k), kind, centroid(wp), 0, [(r_[2] - r_[0]) * U, (r_[3] - r_[1]) * U, 1.6])
    Mt2 = d.find('d03_objects', '#A9B7C2', [(688, 486)], nm='circle')
    P('03-07-watertank', 'water_tank', W(Mt2, (688, 486)), 0, [3.2, 3.2, 2.2])
    for i in range(4):
        wp, M_ = d.place('d03_objects', '#4E86B8', rect_local(600 + i * 10, 482, 606 + i * 10, 488))
        P('03-07-biotoilet%d' % i, 'bio_toilet', centroid(wp), 0, [1.2, 1.2, 2.3])
    for k, y in enumerate((290, 314)):
        it = next(it for it in d.items if it[0] == 'd03_objects' and it[1] == 'polyline' and it[3] == '#8E979B' and abs(it[4][0][1] - y) < 0.5)
        a_, b_ = W(it[5], it[4][0]), W(it[5], it[4][-1])
        P('03-07-clothesline%d' % k, 'clothes_line', ((a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2), math.degrees(math.atan2(b_[1] - a_[1], b_[0] - a_[0])),
          [math.hypot(b_[0] - a_[0], b_[1] - a_[1]), 0.1, 1.8], grip=True)
    sm, Msm = d.place('d03_objects', '#B49B75', rr_local((624, 288), 22, 16, 2))
    P('03-07-smoking', 'smoking_shelter', centroid(sm), rot_w(2), [4.4, 3.2, 2.4])
    for k, x in enumerate((612, 636)):
        wp, M_ = d.place('d03_objects', '#B49B75', rect_local(x - 11, 300, x + 11, 305))
        P('03-07-bench%d' % k, 'bench', centroid(wp), 0, [4.4, 1.0, 0.5], grip=True)
    Mfb = d.find('d03_objects', '#5E6569', [(620, 318)], nm='circle')
    P('03-07-firebarrel', 'fire_barrel', W(Mfb, (620, 318)), 0, [1.0, 1.0, 1.0])
    # ---------------- resolve what the v85 drawing gets wrong
    # (a) the two cabins across at the east fence poke through the fence: shift them west (min) to >= FENCE_CLEAR
    for b in blds:
        if b['kind'] == 'site_cabin' and poly_clear(b['footprint'], site) < FENCE_CLEAR:
            dx = next(-k * 0.25 for k in range(1, 81) if poly_clear([(p[0] - k * 0.25, p[1]) for p in b['footprint']], site) >= FENCE_CLEAR)
            b['footprint'] = R(ccw([(p[0] + dx, p[1]) for p in b['footprint']]))
            for e in b['entrances']:
                e['pos'] = rnd2((e['pos'][0] + dx, e['pos'][1]))
            fix(centroid(b['footprint']), 'Бытовка %s у восточного забора сдвинута на %.2f м на запад' % (b['id'], -dx),
                'на карте v85 она частично за забором (контур площадки v85 режет восточный ряд); теперь >= %.1f м от забора' % FENCE_CLEAR)
    # (b) the drawn workshop is cut by the fence (SE corner outside) and its doors face the fence (its own gate is gone in v85):
    #     shift it inside (min shift) with a free 14 m apron in front of 3 roller doors turned to the yard (north)
    fw_, ws_items, h1 = ws
    wc = centroid(fw_)
    obst = [b['footprint'] for b in blds] + [prop_poly(p) for p in props]
    best = None
    for dy in np.arange(0, 20.1, 0.5):
        for dx in np.arange(-30, 4.1, 0.5):
            poly = [(p[0] + dx, p[1] + dy) for p in fw_]
            if poly_clear(poly, site) < FENCE_CLEAR + 0.5 or any(poly_gap(poly, o) < 2.0 for o in obst):
                continue
            apron = rrect((wc[0] + dx, wc[1] + dy + 6 + 7), 24, 14, 0)
            if any(poly_gap(apron, o) < 0.5 for o in obst) or poly_clear(apron, site) < 1.0:
                continue
            L = math.hypot(dx, dy)
            if best is None or L < best[0]:
                best = (L, dx, dy)
    assert best, 'no free spot for the workshop'
    _, wdx, wdy = best
    fw2 = [(p[0] + wdx, p[1] + wdy) for p in fw_]
    wc2 = centroid(fw2)
    apron = rrect((wc2[0], wc2[1] + 6 + 7), 24, 14, 0)
    doors = [ent((wc2[0] + x * U, wc2[1] + h1 / 2 * U), 90, 'rollshutter', 5.6) for x in (-36, 0, 36)]
    B('03-01-workshop', 'van_workshop', 'construction_workshop', fw2, 1, 4.8, flat('roof_profsheet_SK4c'), 'cinder_SK3d',
      '01 van upgrade workshop 24 x 12 m: 3 roller doors 5.6 m (to the yard, north), pit inside, tyres / scrap / rusty body / a van beside it; '
      'reached through the main gate', ents=doors, extra={'apron': R(apron), 'apron_note': '14 m loading / turning apron in front of the doors (v10 §4): keep free'})
    moved['03-01-workshop'] = (wdx, wdy)
    obst = [b['footprint'] for b in blds] + [prop_poly(p) for p in props] + [apron]
    for pid, kind, pos, size in ws_items:                                   # "in front of it" -> beside the apron, mirrored to the north
        q0 = (wc2[0] + (pos[0] - wc[0]), wc2[1] - (pos[1] - wc[1]))
        q = free_spot(q0, size[0], size[1], 0, obst, site, clear=1.0, gap=0.8)
        P(pid, kind, q, 0, size)
        obst.append(prop_poly(props[-1]))
    fix(wc, 'Мастерская бусика сдвинута на (%.1f, %.1f) м внутрь площадки и развёрнута воротами (3 рольставни) во двор, на север, с '
            'свободным фартуком 14 м; бусик, шины, металлолом и ржавый кузов — рядом с ней по бокам фартука' % (wdx, wdy),
        'на карте v85 её юго-восточный угол срезан контуром площадки (часть здания за забором), а ворота смотрели в забор: своих ворот '
        'мастерской в заборе v85 больше нет (один забор, одни главные ворота, v10 §7.3); бусику нужен фартук 12–15 м (v10 §4)')
    question('Мастерская улучшения бусика: в плане v11 у неё свои ворота ~18 м на главную дорогу, в v85 и v10 §7.3 — один забор с главными воротами. Как заезжать?',
             ['1 — через главные ворота, мастерская внутри площадки воротами во двор (сдвинута внутрь)',
              '2 — вернуть вторые ворота ~18 м в заборе у мастерской, на главную дорогу, как в плане v11'], 1,
             'вариант 1: 03-01-workshop сдвинута на (%.1f, %.1f) м, рольставни на север, фартук 14 м; колея 03-rut-workshop от главных ворот' % (wdx, wdy))
    # ---------------- fence (ONE), main gate
    zones.append({'id': '03-fence', 'kind': 'fence', 'line': R(d.fence), 'material': 'profiled_sheet_blue', 'surface': 'metal_painted_SK6a',
                  'tint': '#6E8AA6', 'height_m': 2.0, 'solid': True, 'posts_every_m': 3.0,
                  'notes': 'the ONE fence of v85 (build_world_v85 _ring_gap(CONSTR_POLY, _gate, 9.5)): blue profiled sheet ~2 m along the site '
                           'contour, open ring from gate post to gate post; no inner fences, no plan v11 fence, no stubs'})
    zones.append({'id': '03-gate-main', 'kind': 'gate', 'pos': rnd2(gate_c), 'w_m': round(gate_w, 2), 'open': True, 'barrier': False,
                  'posts': [rnd2(d.fence[0]), rnd2(d.fence[-1])], 'facing_deg': 270, 'guard_booth': '03-03-guard', 'wheel_wash': '03-03-wheelwash',
                  'connector': {'line': [rnd2(gate_q), rnd2((gate_q[0], 349.0))], 'surface': 'asphalt_A5d12', 'width_m': 6.4,
                                'note': 'ROAD_CONSTR of build_world_v85 (already in the world road network, R24) from the gate to ROAD_H'},
                  'notes': 'main gate ~19 m onto the main road, open, no barrier (v10 §7.3, v02 §8.3)'})
    # ---------------- ground: the pad (+8 m), dirt with ruts and puddles
    zones.append({'id': '03-ground', 'kind': 'ground', 'poly': R(site), 'surface': 'dirt_SK1b', 'flat': True, 'pad_rel_m': 8.0,
                  'notes': 'site yard = hill pad +8 m above the surroundings (v10 §3.1); bare packed dirt with ruts and puddles, '
                           'no concrete / slab roads (v02 §8.3); edges blend into the wooded slope 9..26 m outside the fence'})
    for k, it in enumerate([it for it in d.items if it[0] == 'd03_terrain' and it[2] in ('#CDB68C', '#A9CBD6', '#E6DCC4')]):
        wp = [W(it[5], p) for p in it[4]]
        kind = {'#CDB68C': 'dirt_patch', '#A9CBD6': 'puddle', '#E6DCC4': 'yard'}[it[2]]
        ins = sum(inside(p, site) for p in wp)
        if ins == 0:
            continue
        if ins < len(wp):                                                    # pull the outside vertices back inside the fence
            inn = ring_inset(site, 1.0, 180)
            wp = [p if inside(p, site) and pl_d(p, closed(site)) > 1.0 else min(inn, key=lambda q: math.hypot(q[0] - p[0], q[1] - p[1])) for p in wp]
        zones.append({'id': '03-%s%d' % (kind, k), 'kind': kind, 'poly': R(ccw(wp)),
                      'surface': {'dirt_patch': 'dirt_SK1b', 'puddle': 'water_puddle', 'yard': 'gravel_SK1d'}[kind],
                      'notes': {'dirt_patch': 'darker churned dirt with deep ruts (decal / terrain layer), drivable',
                                'puddle': 'shallow puddle decal, no collider', 'yard': 'compacted yard of the dormitory (08), NPC hang-out'}[kind]})
    fix(gate_c, 'Лужи и серые пятна старой главной улицы плана v11 за забором не переносятся; пятно грязи у мастерской обрезано по забору',
        'это заливки плана v11 вокруг его прежней дороги — на карте v85 их обрезает контур площадки')
    # ---------------- ruts (two wheel ruts, dirt): plan v11 dashed lines (D03 terrain matrix) as waypoints, routed around objects
    T = lambda pl: [d.terr(p) for p in pl]
    tr1 = T([(417, 560), (380, 470), (300, 400), (200, 380)])
    tr2 = T([(400, 600), (430, 520), (460, 420), (470, 330)])
    t3 = T([(212, 700), (230, 640), (300, 600)])
    g_in = (gate_c[0], gate_c[1] + 4.0)
    wsb = blds[[b['id'] for b in blds].index('03-01-workshop')]
    apron_c = centroid(wsb['apron'])
    rowAB = [b for b in blds if b['kind'] == 'site_cabin' and b['entrances'][0]['facing_deg'] in (90.0, 270.0)]
    yrows = sorted(set(round(centroid(b['footprint'])[1], 1) for b in rowAB))
    yard_in = (min(p[0] for b in rowAB for p in b['footprint']) - 3.5, (yrows[0] + yrows[-1]) / 2)
    obst = [b['footprint'] for b in blds if not b.get('disabled')] + [prop_poly(p) for p in props if p['kind'] not in ('wheel_wash',) and not p.get('disabled')]
    rt = Router(site, obst, TRACK_W / 2 + 0.7, (525, 355, 685, 495))
    routed = {}

    def via(pts):
        out = [pts[0]]
        for a_, b_ in zip(pts[:-1], pts[1:]):
            out += rt.route(out[-1], b_)[1:]
        return chaikin_keep(dp(out, 1.0), 2)
    routed['03-rut-main'] = ([gate_c] + via([g_in] + tr1), 'gate -> between buildings A and B -> west part (plan v11 rut 1)')
    routed['03-rut-north'] = ([gate_c] + via([g_in] + tr2[1:]), 'gate -> past the materials store -> north (plan v11 rut 2, around the stacks)')
    routed['03-rut-west'] = ([gate_c] + via([g_in, t3[2]]), 'gate -> machinery / west formwork (plan v11 rut 3, re-targeted)')
    routed['03-rut-workshop'] = ([gate_c] + via([g_in, apron_c]), 'gate -> workshop apron (replaces the workshop gate of plan v11)')
    routed['03-rut-cabins'] = ([gate_c] + via([g_in, yard_in]), 'gate -> cabin-town yard between rows A and B, from the west (replaces the east-gate drive)')
    fix(t3[0], 'Колея 3 плана v11 начиналась у выреза под бусик в южном заборе (его в v85 нет) — теперь идёт от главных ворот к технике',
        'колея не должна упираться в забор (v10 §1.3): в заборе v85 только главные ворота')
    fix(tr2[2], 'Колеи плана v11 проложены по точкам плана, но в обход штабелей опалубки и труб, бетономешалки и самосвала (не сквозь них)',
        'на плане v11 пунктир колей нарисован поверх склада и техники; бусик через штабеля не ездит')
    fix(apron_c, 'Добавлены колеи от главных ворот к фартуку мастерской и к двору бытовок (с запада)',
        'в плане v11 туда вели свои ворота (мастерской и восточные) — в v85 их нет, а бусик должен доезжать до мастерской и до людей у бытовок')
    for tid in ('03-rut-main', '03-rut-north', '03-rut-west', '03-rut-workshop', '03-rut-cabins'):
        pl, note = routed[tid]
        zones.append({'id': tid, 'kind': 'track', 'line': R(pl), 'surface': 'dirt_SK1b', 'width_m': TRACK_W,
                      'notes': note + '; two wheel ruts with puddles, no gravel / concrete; no props on it'})
    fix(gate_c, 'Отдельные ворота мастерской (~18 м), восточные ворота и 4 выреза под бусик плана v11 не делаются; один забор по контуру с главными воротами ~19 м',
        'карта v85 и v10 §7.3: «забор один — по контуру площадки, с главными воротами ~19 м на дорогу», двойного забора и обрывков нет')
    # pedestrian paths (blue dashes) -> trodden paths
    for k, it in enumerate([it for it in d.items if it[0] == 'd03_paths']):
        zones.append({'id': '03-path%d' % k, 'kind': 'path', 'line': R([W(it[5], p) for p in it[4]]), 'surface': 'dirt_SK1b', 'width_m': 1.2,
                      'notes': 'trodden footpath of the workers (plan blue dashes)'})
    par = list(range(len(store)))                                         # store clusters (bbox gap < 4 m)

    def root(i):
        while par[i] != i:
            i = par[i]
        return i
    bb = [(min(q[0] for q in P_), min(q[1] for q in P_), max(q[0] for q in P_), max(q[1] for q in P_)) for P_ in store]
    for i in range(len(store)):
        for j in range(i + 1, len(store)):
            if bb[i][0] - 4 < bb[j][2] and bb[j][0] - 4 < bb[i][2] and bb[i][1] - 4 < bb[j][3] and bb[j][1] - 4 < bb[i][3]:
                par[root(i)] = root(j)
    groups = {}
    for i in range(len(store)):
        groups.setdefault(root(i), []).append(i)
    for k, (r_, mem) in enumerate(sorted(groups.items(), key=lambda kv: -max(bb[i][3] for i in kv[1]))):
        x0_, y0_ = min(bb[i][0] for i in mem) - 1, min(bb[i][1] for i in mem) - 1
        x1_, y1_ = max(bb[i][2] for i in mem) + 1, max(bb[i][3] for i in mem) + 1
        zones.append({'id': '03-store%d' % k, 'kind': 'materials_store', 'poly': R(ccw([(x0_, y0_), (x1_, y0_), (x1_, y1_), (x0_, y1_)])),
                      'surface': 'dirt_SK1b', 'material_slot': 'construction_store',
                      'notes': 'open materials store (склад, v10 §7.3): bricks / blocks on pallets, rebar, formwork, pipes, sand, gravel - slightly irregular '
                               'but where they belong (legend); props 03-03-*; no store building on plan v11; keep the ruts free'})
    zones.append({'id': '03-cabin-yard', 'kind': 'yard', 'poly': R(ccw([(p[0], p[1]) for p in (
        (min(p[0] for b in cabins for p in b['footprint']) - 1, min(p[1] for b in cabins for p in b['footprint']) - 1),
        (max(p[0] for b in cabins for p in b['footprint']) + 1, min(p[1] for b in cabins for p in b['footprint']) - 1),
        (max(p[0] for b in cabins for p in b['footprint']) + 1, max(p[1] for b in cabins for p in b['footprint']) + 1),
        (min(p[0] for b in cabins for p in b['footprint']) - 1, max(p[1] for b in cabins for p in b['footprint']) + 1))])),
                  'surface': 'dirt_SK1b', 'npc': 'workers of different countries, brigades, foremen; smoking corner, clothes lines, fire barrel',
                  'notes': '07 cabin town: one-storey containers with ~3 m passages, a separate group by the east fence (v10 §7.3)'})
    # ---------------- vegetation: no tree points; wooded slope band 9..26 m outside the contour (as drawn), none in the yard / gate / road
    roads = [road_h, road_v, [gate_q, (gate_q[0], 349.0)]]
    inner, outer = ring_offset(site, 9.0, 72), ring_offset(site, 26.0, 72)
    n = len(inner)
    sector, sectors = [], []
    for i in range(n + 1):
        k = i % n
        ok = all(pl_d(q, rd) > 3.2 + 2.0 + 1.0 for rd in roads for q in (inner[k], outer[k], ((inner[k][0] + outer[k][0]) / 2, (inner[k][1] + outer[k][1]) / 2)))
        if ok:
            sector.append(k)
        if (not ok or i == n) and len(sector) > 1:
            sectors.append(sector)
        if not ok:
            sector = []
    if len(sectors) > 1 and sectors[0][0] == 0 and sectors[-1][-1] == 0:
        sectors[0] = sectors.pop()[:-1] + sectors[0]
    for j, sec in enumerate(sectors):
        poly = [inner[k] for k in sec] + [outer[k] for k in sec[::-1]]
        zones.append({'id': '03-veg-slope%d' % j, 'kind': 'veg_zone', 'poly': R(ccw(poly)), 'density': 'grove', 'species': 'leafy',
                      'mix': {'oak': 0.5, 'birch': 0.3, 'pine': 0.2}, 'notes': 'wooded slope of the Construction hill 9..26 m outside the fence '
                      '(build_world_v85 forest ring), groups and singles, glades; >= 2 m from roads'})
    zones.append({'id': '03-notree-site', 'kind': 'no_tree', 'poly': R(ring_offset(site, 6.0, 90)), 'why': 'site yard with function (ruts, store, cabins) + 6 m fence strip'})
    gx = gate_c[0]
    zones.append({'id': '03-notree-gate', 'kind': 'no_tree', 'poly': R(ccw([(gx - 14, 343.0), (gx + 14, 343.0), (gx + 14, gate_c[1] + 2), (gx - 14, gate_c[1] + 2)])),
                  'why': 'gate approach and the connector to the main road (van, view of the gate)'})
    zones.append({'id': '03-notree-fuel', 'kind': 'no_tree', 'poly': R(pad_poly), 'why': 'fuel station apron (disabled) + road verge'})
    fix(centroid(site), 'Деревья плана v11 (круги) и одиночные деревья внутри забора не переносятся: внутри площадки деревьев нет, '
                        'склон холма 9–26 м за забором — зона рощ (veg_zone)', 'v10 §1.2 и §7.3: деревья зонами, двор с функцией без деревьев')
    return blds, props, zones, site, d, gate_c, moved


# ---------------------------------------------------------------- checks and fit
def checks(blds, props, zones, site):
    out = {'fence_clearance_m': {}, 'overlaps': [], 'track_hits': [], 'cabin_gaps_m': []}
    fence = next(z for z in zones if z['id'] == '03-fence')
    for b in blds:
        if b.get('disabled'):
            continue
        c = poly_clear(b['footprint'], site)
        out['fence_clearance_m'][b['id']] = round(c, 2)
    act = [b for b in blds if not b.get('disabled') and b['kind'] not in ('stair_lift_core',)]
    for i in range(len(act)):
        for j in range(i + 1, len(act)):
            A, Bp = act[i], act[j]
            if A['id'].startswith('03-04-A') and Bp['id'].startswith('03-04-A'):
                continue
            if sat_overlap(A['footprint'], Bp['footprint']):
                out['overlaps'].append([A['id'], Bp['id']])
    cab = sorted([b for b in blds if b['kind'] in ('site_cabin', 'canteen', 'shower', 'foreman_office')], key=lambda b: b['id'])
    for i in range(len(cab)):
        g, j = min((poly_gap(cab[i]['footprint'], cab[j]['footprint']), j) for j in range(len(cab)) if j != i)
        out['cabin_gaps_m'].append([cab[i]['id'], cab[j]['id'], round(g, 2)])
    for z in zones:
        if z['kind'] != 'track':
            continue
        band = buffer_line(z['line'], z['width_m'] / 2)
        for b in blds:
            if not b.get('disabled') and sat_overlap(band, b['footprint']) and b['kind'] != 'scaffold':
                # concave band: confirm with samples
                if any(inside(q, b['footprint']) or pl_d(q, closed(b['footprint'])) < z['width_m'] / 2 for q in sample(z['line'], 1.0)):
                    out['track_hits'].append([z['id'], b['id']])
        smp = sample(z['line'], 0.5)
        for p in props:
            if p.get('disabled') or p['kind'] in ('wheel_wash',):
                continue
            pp = prop_poly(p)
            dmin = min(0.0 if inside(q, pp) else pl_d(q, closed(pp)) for q in smp)
            if dmin < z['width_m'] / 2:
                out['track_hits'].append([z['id'], p['id'], round(dmin, 2)])
    out['min_building_fence_clearance_m'] = round(min(out['fence_clearance_m'].values()), 2)
    out['min_cabin_gap_m'] = min(g[2] for g in out['cabin_gaps_m'])
    out['props_outside_fence'] = [p['id'] for p in props if not p.get('disabled') and not inside(p['pos'], site)]
    return out


def sample(pl, step):
    out = []
    for a, b in zip(pl[:-1], pl[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / step))
        out += [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]
    return out


DRAWN_FILL = {'03-04-A': '#D8D7D1 #C9C8C1 #5E6569 #B9BCB8', '03-04-A-core': '#B9BCB8', '03-04-A-scaffold': '#E6C98F #B08B4E',
              '03-04-A-hoist': '#7C8083', '03-05-B': '#CFCFC8 #5E6569 #8E5B42 #D2B48C', '03-08-dorm': '#D4CBBB #B8AE9E', '03-03-guard': '#B5C8CE'}


def measure_fit(blds, moved):
    """drawn buildings vs the FINAL render (5 px/m): bbox of the drawn fill colour around each footprint vs the footprint bbox, per side."""
    from scipy import ndimage
    x0w, y0w, x1w, y1w = 520, 350, 690, 500
    im = np.asarray(Image.open(MAP_FULL).convert('RGB').crop((x0w * 5, (950 - y1w) * 5, x1w * 5, (950 - y0w) * 5))).astype(np.int16)
    res = []
    for b in blds:
        fill = DRAWN_FILL.get(b['id']) or b.get('tint')
        if b.get('disabled') or b['id'] in moved or not fill or b['kind'] == 'site_cabin' and b['id'] in ('03-07-cabin09', '03-07-cabin10'):
            continue
        cols = [np.array([int(f[i:i + 2], 16) for i in (1, 3, 5)]) for f in fill.split()]
        xs = [p[0] for p in b['footprint']]
        ys = [p[1] for p in b['footprint']]
        j0, j1 = int((min(xs) - 1.0 - x0w) * 5), int((max(xs) + 1.0 - x0w) * 5)
        i0, i1 = int((y1w - max(ys) - 1.0) * 5), int((y1w - min(ys) + 1.0) * 5)
        sub = np.zeros(im[i0:i1, j0:j1].shape[:2], bool)
        for col in cols:
            sub |= np.all(np.abs(im[i0:i1, j0:j1] - col) < 5, axis=-1)
        sub = ndimage.binary_opening(sub, iterations=1)
        ii, jj = np.nonzero(sub)
        if len(ii) == 0:
            continue
        dx0 = (j0 + jj.min()) / 5 + x0w - min(xs)
        dx1 = (j0 + jj.max() + 1) / 5 + x0w - max(xs)
        dy1 = y1w - (i0 + ii.min()) / 5 - max(ys)
        dy0 = y1w - (i0 + ii.max() + 1) / 5 - min(ys)
        res.append((b['id'], float(dx0), float(dx1), float(dy0), float(dy1)))
    sides = [abs(v) for r in res for v in r[1:]]
    return {'buildings_checked': len(res), 'max_side_residual_m': round(max(sides), 2), 'median_side_residual_m': round(float(np.median(sides)), 2),
            'note': 'drawn fill (inside a 0.3 m outline) vs footprint edges; ~0.2 m = outline half width',
            'worst': [[r[0]] + [round(v, 2) for v in r[1:]] for r in sorted(res, key=lambda r: -max(abs(v) for v in r[1:]))[:3]]}


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
        if z['kind'] == 'track':
            dl.polygon([tp(q) for q in buffer_line(z['line'], z['width_m'] / 2)], fill=(0, 220, 0, 70))
        if z['kind'] == 'veg_zone':
            dl.polygon([tp(q) for q in z['poly']], fill=(20, 140, 40, 45))
    im = Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB')
    dr = ImageDraw.Draw(im)
    for z in dd['zones']:
        if 'poly' in z and z['kind'] not in ('veg_zone',):
            col = (0, 200, 255) if z['kind'] != 'no_tree' else (120, 120, 255)
            dr.polygon([tp(q) for q in z['poly']], outline=col)
        if 'line' in z:
            col = (150, 0, 200) if z['kind'] == 'fence' else (0, 160, 0)
            dr.line([tp(q) for q in z['line']], fill=col, width=2 if z['kind'] == 'fence' else 1)
        if z['kind'] == 'gate':
            for q in z['posts']:
                x, y = tp(q)
                dr.rectangle([x - 3, y - 3, x + 3, y + 3], fill=(150, 0, 200))
    for b in dd['buildings']:
        dr.polygon([tp(p) for p in b['footprint']], outline=(255, 0, 0) if not b.get('disabled') else (255, 150, 150), width=2)
        for e in b.get('entrances', []):
            x, y = tp(e['pos'])
            dr.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(0, 0, 255))
    for p in dd['props']:
        x, y = tp(p['pos'])
        r = max(2, min(p['size'][0], p['size'][1]) * k / 2)
        dr.ellipse([x - r, y - r, x + r, y + r], outline=(255, 0, 255), width=2)
    im.save(out)


def main():
    blds, props, zones, site, d, gate_c, moved = build()
    chk = checks(blds, props, zones, site)
    fit = measure_fit(blds, moved)
    cnt = {'buildings': len(blds), 'buildings_active': sum(1 for b in blds if not b.get('disabled')),
           'by_kind': {}, 'props': len(props), 'zones': len(zones), 'veg_zones': sum(1 for z in zones if z['kind'] == 'veg_zone'),
           'no_tree_zones': sum(1 for z in zones if z['kind'] == 'no_tree'), 'tracks': sum(1 for z in zones if z['kind'] == 'track'),
           'fixes': len(FIXES), 'questions': len(QUESTIONS)}
    for b in blds:
        cnt['by_kind'][b['kind']] = cnt['by_kind'].get(b['kind'], 0) + 1
    dd = {'district': 'construction', 'version': 'v85 from plan v11',
          'sources': [os.path.relpath(p, ROOT).replace('\\', '/') for p in (PLAN_PY, PLAN_SVG, LEGEND, WORLD_PY, os.path.join(MAP_DIR, 'VOLUNTEERS_MAP_MASTER_v85.svg'))]
          + ['docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §7.3', 'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.3'],
          'transform': 'plan v11 local units (0.2 m, y down) -> master SVG units by the D03 group transform translate(2670 1410) translate(-410 -393) and the '
                       'per-element relayout translate of build_world_v85 (clusters spread x1.15 / y0.95 about local (410, 393), sizes unscaled) -> '
                       'world = common.u2w (post_shift = 0 here). Fit on VOLUNTEERS_MAP_FINAL_v85.png: %d drawn footprints, drawn fill edge vs footprint edge '
                       'median %.2f m, max %.2f m per side; moved by logic: workshop %s m, transformer, 2 east cabins (see fixed_by_logic)'
                       % (fit['buildings_checked'], fit['median_side_residual_m'], fit['max_side_residual_m'], moved.get('03-01-workshop')),
          'fit': fit, 'pad_height_m': None, 'pad_rel_m': 8.0,
          'pad_note': 'the site stands on a hill pad +8 m (v10 §3.1); the lead terrain step makes the pad from zone 03-ground (flat yard). '
                      'NOTE: the gate is only ~14 m from ROAD_H (y 348): an 8 m rise needs ~100 m at 8 %% - let ROAD_H climb along the hill foot '
                      'and / or ramp the yard from the gate band (~+2 m) to the full +8 m within ~40 m north of the gate',
          'abs_heights': False, 'lighting': 'sunny_bright_no_fog', 'lighting_notes': 'bright, sunny, cheerful (v10 §7.3, §10): no fog',
          'buildings': blds, 'props': props, 'zones': zones, 'fixed_by_logic': FIXES, 'questions_for_vadim': QUESTIONS, 'counts': cnt, 'checks': chk}
    save_json('districts/construction_v85.json', dd)
    os.makedirs(WORK, exist_ok=True)
    overlay(dd, (520, 325, 700, 505), os.path.join(WORK, 'check_construction.png'))
    print('construction_v85:', json.dumps(cnt, ensure_ascii=False))
    print('fit:', fit)
    print('checks: min fence clearance', chk['min_building_fence_clearance_m'], 'overlaps', chk['overlaps'], 'track hits', chk['track_hits'],
          'min cabin gap', chk['min_cabin_gap_m'], 'props outside', chk['props_outside_fence'])
    print('fence clearance:', chk['fence_clearance_m'])


if __name__ == '__main__':
    main()
