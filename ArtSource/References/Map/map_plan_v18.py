"""VOLUNTEERS ONLY R01 v18, phase B: the v17 game-scale / density / occlusion rules applied to every district and to the
common land, plus the fixes of the phase A weak spots (Downtown plaza core and vistas, Rough District yard rooms).

Run with Python 3.12 + shapely/numpy/pillow, e.g.
    uv run --offline --no-project -p 3.12 --with shapely --with numpy --with pillow python -B map_plan_v18.py

Reads MAP_PLAN_R01_v17.json (the accepted phase A result, never regenerated) and MAP_PLAN_R01_v16.json / Look/look_v16_flat.json
(the "before" side of the metrics); imports map_plan_v17.py (and through it map_plan_v16.py) for the shared helpers.
Writes, exclusive-create (no deliverable is ever overwritten):
    MAP_PLAN_R01_v18.json, Greybox/greybox_v18_flat.json, Look/look_v18_flat.json, Crowd/crowd_v18.json.
The top-down picture is a separate step (it needs the Windows fonts and the v11 preview PNG, like v16/v17):
    python -B map_plan_v18.py --render        -> MAP_PLAN_R01_v18.png, from MAP_PLAN_R01_v18.json only.

Vadim's layout is kept: district envelopes, road centrelines/classes, water, bridges, coasts, exits, POIs, bases, police
parking, trip-meter destinations and spawn points keep their coordinates (checked against v16 at the end). Changed: village
houses (6-10 m), plot fences and yards, farmsteads, industrial/port, construction site, Tramduro, elite gardens, beach,
forest undergrowth and clearings, fields, common-land rooms everywhere, relief (hills 3-15 m), grade fixes (terrain only),
the plaza core and the Downtown vista stoppers, more Rough District playgrounds and trees. Fixed seeds throughout.

Fedya's feedback on the v17 trial (2026-10-12), applied in place: the hamlet house plots move as whole units toward their
neighbours (hamlet()), the moved plots' driveways are reshaped and the road/pedestrian graphs rebuilt with the v16 method, POIs
inside moved houses move with them (listed exceptions to the protected layout); the empty hamlet land gets the fallback fill of
small objects (~10 %); about 20 % of the trees and tall bushes v18 generated are thinned, densest first (thin_trees()).

Schema: identical to v17 (plan keys v17_phase_a / v17_dressing, look key "v17", building key "v17"). Optional additions:
plan "v18_phase_b" (rules, deviations, metrics, checks), building "v17.rev" = "v18" on records made or rescaled by v18,
look "v17.phase" = "B", props scale "s" != 1 on a few props, new water records of kind "well"/"swimming_pool" (same kinds
as v11's own) and hills with a negative height ("cutting" bumps of the grade fixes; HeightModel adds them like any hill).
"""
from __future__ import annotations
import argparse, collections, copy, hashlib, heapq, importlib.util, json, math, sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Point, Polygon, LineString, MultiPolygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, polylabel
from PIL import Image, ImageDraw

MAP = Path(__file__).resolve().parent
REV, STEM, SRC = 'v18', 'MAP_PLAN_R01_v18', 'MAP_PLAN_R01_v17.json'


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m17 = load_module(MAP / 'map_plan_v17.py', 'map_plan_v17_for_v18')
m16 = m17.m16
m16.REV, m16.STEM = REV, STEM
parts, valid, geom, flat = m16.parts, m16.valid, m16.geom, m16.flat
orect, largest, unity_yaw, pole, min_dim, edge_dir_near = m17.orect, m17.largest, m17.unity_yaw, m17.pole, m17.min_dim, m17.edge_dir_near
greedy_fill, tree_disc, car_row, car_keys, offset_points = m17.greedy_fill, m17.tree_disc, m17.car_row, m17.car_keys, m17.offset_points
STOREY, SHOP_GROUND, GARAGE_H, R = m17.STOREY, m17.SHOP_GROUND, m17.GARAGE_H, m17.R
# World records need the world id of every district (v17 only knew 04/05).
m17.WID.update({'forest': '01', 'village': '02', 'transition': '03', 'residential': '04', 'old_town': '05', 'industrial': '06',
                'elite': '07', 'fields': '08', 'beach': '09', 'tramduro': '10', 'common': 'CL'})

DEVIATIONS = []
ROAD_GRADE = 0.08
FIX_ROADS = ('07_drive', 'forest_valley', 'hamlet_rough_e')


def dev(text):
    DEVIATIONS.append(text)


def rng_for(tag):
    return np.random.default_rng(int(hashlib.sha256(('v18:' + tag).encode()).hexdigest()[:8], 16))


# Footprints (width across, length along the yaw axis) of the registry props, for clearance and the crowd obstacles.
FOOT = {'prop/bench_park': (0.7, 1.9), 'prop/bench_soviet': (0.7, 1.9), 'prop/bench_soviet_broken': (0.7, 1.9), 'prop/trashbin_concrete': (0.6, 0.6),
        'prop/garbage_container_closed': (1.2, 1.5), 'prop/garbage_container_open': (1.2, 1.5), 'prop/market_stall': (2.6, 3.2),
        'prop/news_kiosk': (2.8, 3.0), 'prop/kiosk': (2.8, 3.0), 'prop/atm_pavilion': (2.8, 3.0), 'prop/ad_column': (1.2, 1.2), 'prop/fountain': (7, 7),
        'proc/clock_column': (1.6, 1.6), 'prop/lamp_oldtown_single': (0.4, 0.4), 'prop/lamp_oldtown_double': (0.4, 0.4), 'prop/lamp_soviet': (0.35, 0.35),
        'prop/lamp_soviet_broken': (0.35, 0.35), 'prop/bin': (0.5, 0.5), 'proc/laundry_poles': (0.4, 6.4), 'prop/carpet_rack': (0.4, 2.6),
        'proc/dumpster_pad': (2.6, 5.4), 'prop/billboard_large': (1.0, 6.0), 'proc/pylon': (5.5, 5.5), 'prop/busstop_shelter': (1.6, 4.0),
        'prop/busstop_shelter_vandalised': (1.6, 4.0), 'prop/truck_tow': (2.5, 7.0), 'prop/bus_city': (2.6, 11.0), 'prop/tractor_small': (1.8, 3.4),
        'prop/default_crate': (1.2, 1.2), 'prop/pipe_support': (1.0, 1.0), 'prop/pipe_support_040': (1.0, 1.0), 'prop/log_bench': (0.6, 2.4),
        'prop/beach_lifeguard_tower': (2.4, 2.4), 'prop/beach_sunlounger': (0.8, 2.0), 'prop/beach_umbrella_red': (0.3, 0.3),
        'prop/beach_umbrella_teal': (0.3, 0.3), 'prop/hedge_box': (1.0, 2.0), 'prop/fence_concrete_panel': (0.4, 3.0), 'prop/parking_barrier': (0.3, 3.0),
        'prop/lamp_bollard': (0.3, 0.3), 'prop/lamp_iron': (0.35, 0.35), 'prop/gas_pump': (0.8, 1.2), 'prop/van_minibus': (2.0, 5.0),
        # hamlet fill after Fedya's 2026-10-12 feedback; scarecrow / mailbox / cart_wooden are new kinds (no Unity model yet)
        'prop/garage_metal_rust': (3.4, 6.0), 'prop/garage_metal_open': (3.4, 6.0), 'prop/scarecrow': (0.6, 1.2), 'prop/mailbox': (0.4, 0.4),
        'prop/cart_wooden': (1.6, 3.0)}
for _p in ('prop/play_swings', 'prop/play_slide', 'prop/play_sandbox', 'prop/play_carousel', 'prop/play_horizontal_bar', 'prop/play_carpet_rack'):
    FOOT[_p] = (2.4, 2.8)
CAR = (1.9, 4.5)
# Props a standing eye (1.7 m) cannot see over (sightline metric); cars, benches, bins, lamps and lattice pylons are see-through.
TALL = {'prop/market_stall', 'prop/news_kiosk', 'prop/kiosk', 'prop/atm_pavilion', 'prop/ad_column', 'proc/clock_column', 'prop/busstop_shelter',
        'prop/busstop_shelter_vandalised', 'prop/truck_tow', 'prop/bus_city', 'prop/beach_lifeguard_tower', 'prop/hedge_box', 'prop/van_minibus',
        'proc/dumpster_pad', 'prop/garage_metal_rust', 'prop/garage_metal_open'}
NEW_PROP_KINDS = ('prop/scarecrow', 'prop/mailbox', 'prop/cart_wooden')   # not in MapLookRegistry yet: Unity skips and logs them
OPAQUE_FENCES = {'fence_wood_yard', 'fence_profiled_sheet_blue', 'military_fence', 'concrete_port_yard_with_fence', 'high_fence_with_barbed_wire'}


def foot_of(key):
    if 'car_' in key:
        return CAR
    return FOOT.get(key, (1.0, 1.0))


def tag_of(key):
    if 'car_' in key or key in ('prop/van_minibus',):
        return 'car'
    return key.split('/')[-1]


def district_boxes(d):
    return {q['id']: box(*q['bbox_m'][0], *q['bbox_m'][1]) for q in d['districts']}


def rehydrate(W, d):
    """Rebuild the v17 World state (props, trees, pads, solids) from the delivered v17 plan, so phase A stays exactly as
    accepted and v18 only adds to it."""
    v = d['v17_dressing']
    W.props = [dict(p) for p in v['props']]
    W.trees = [dict(t) for t in v['trees']]
    W.tree_pts = [(t['x'], t['y']) for t in W.trees]
    W.pads = [(valid(Polygon(p['polygon_m'])), p['mat'], p['ctx'], p['prio']) for p in v['pads'] if len(p['polygon_m']) >= 3]
    W.fences = []
    W.solid = []
    W.bidx, W.bidx_rev = {}, {}
    for b in d['functional_buildings']:
        W.bidx[b['id']] = len(W.solid)
        W.bidx_rev[len(W.solid)] = b['id']
        W.solid.append((valid(geom(b)), 'building'))
    for f in d['fences']:
        for run in f['solid_runs_m']:
            if len(run) >= 2:
                W.solid.append((LineString(run).buffer(0.15), 'fence'))
    for p in W.props:
        if not p['solid']:
            continue
        w, l = foot_of(p['k'])
        a = math.radians(90 - p['yaw'])
        g = orect(p['x'], p['y'], math.cos(a), math.sin(a), l * p.get('s', 1), w * p.get('s', 1))
        t = tag_of(p['k'])
        if t == 'car' and g.intersects(W.carriage.buffer(-0.2)):
            t = 'car_street'
        W.solid.append((g, t))
    W.clear_zones = []          # v18: areas whose scatter-forest trees are removed (clearings, plots, yards)
    W.structs = []              # v18: new plan structures (haystacks, beds, lounger rows)
    W.new_water = []            # v18: wells and villa pools
    W.hamlet_new_plots = []     # v18: (plot id, polygon) of the new fenced hamlet plots
    W.tunnel = {}               # v18: id(tree) -> (road id, side, index along the road) of the common-land tree tunnels
    W.v18_props_from = len(W.props)
    W.v18_trees_from = len(W.trees)
    W.v18_pads_from = len(W.pads)


# ---------------------------------------------------------------- terrain: port of HeightModel (smooth field + road profile)
class Terrain:
    """SmoothHeight of Assets/OnlyVolunteers/Map/Look/HeightModel.cs (hills + coast on the 1025^2 heightmap grid, bilinear)
    and its grade-limited, junction-pinned road profiles (Gaussian sigma 8 m, 2 m resampling, 40 relaxation passes).
    Ported so the plan can prove the drivable grade without Unity; verified on v17: exactly 07_drive, forest_valley and
    hamlet_rough_e exceed 9 %, as in the v17 Unity build log."""

    def __init__(self, look, hills):
        t = look['terrain']
        self.look = look
        self.n = 1025
        self.x0, self.y0 = t['x0'], t['y0']
        self.dx, self.dy = t['sx'] / (self.n - 1), t['sy'] / (self.n - 1)
        xs = self.x0 + np.arange(self.n) * self.dx
        ys = self.y0 + np.arange(self.n) * self.dy
        self.GX, self.GY = np.meshgrid(xs, ys)
        f = np.zeros_like(self.GX)
        pts = lambda a: list(zip(a[0::2], a[1::2]))
        beach = valid(Polygon(pts(look['beach']['pts'])))
        sea = valid(Polygon(pts(look['sea']['pts'])))
        inb = shapely.contains_xy(beach, self.GX, self.GY)
        ins = shapely.contains_xy(sea, self.GX, self.GY) & ~inb
        f[inb] += -1.5 * 0.125                      # beach.land / beach.sea are empty in the look: t = 0.5 everywhere
        dd = shapely.distance(sea.exterior, shapely.points(self.GX[ins], self.GY[ins]))
        u = np.clip(dd / 40, 0, 1)
        f[ins] += -1.5 + (-4 + 1.5) * u * u * (3 - 2 * u)
        self.coast = f
        self.hills = []
        self.f = f.copy()
        for h in hills:
            self.add(h)
        self._jh = None

    def bump(self, h):
        rx, ry = h['radii_m']
        cx, cy = h['center_m']
        i0 = max(0, int((cx - rx - self.x0) / self.dx) - 1)
        i1 = min(self.n - 1, int((cx + rx - self.x0) / self.dx) + 2)
        j0 = max(0, int((cy - ry - self.y0) / self.dy) - 1)
        j1 = min(self.n - 1, int((cy + ry - self.y0) / self.dy) + 2)
        X, Y = self.GX[j0:j1 + 1, i0:i1 + 1], self.GY[j0:j1 + 1, i0:i1 + 1]
        r = np.sqrt(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2)
        return (slice(j0, j1 + 1), slice(i0, i1 + 1)), np.where(r < 1, h['height_target_m'] * 0.5 * (1 + np.cos(np.pi * np.minimum(r, 1))), 0.0)

    def add(self, h, sign=1):
        if h['radii_m'][0] <= 0 or h['radii_m'][1] <= 0:
            return
        sl, v = self.bump(h)
        self.f[sl] += sign * v
        if sign > 0:
            self.hills.append(h)
        self._jh = None

    def remove(self, h):
        self.add(h, -1)
        self.hills.remove(h)

    def h(self, x, y):
        gx = np.clip((np.asarray(x, float) - self.x0) / self.dx, 0, self.n - 1.001)
        gy = np.clip((np.asarray(y, float) - self.y0) / self.dy, 0, self.n - 1.001)
        i, j = gx.astype(int), gy.astype(int)
        fx, fy = gx - i, gy - j
        F = self.f
        a, b, c, e = F[j, i], F[j, i + 1], F[j + 1, i], F[j + 1, i + 1]
        return a + (b - a) * fx + (c - a) * fy + (a - b - c + e) * fx * fy

    def junction_heights(self):
        if self._jh is None:
            self._jh = {}
            for j in self.look['junctions']:
                xs = [j['x'] + math.cos(k * math.pi / 2) * (0 if k == 4 else 4) for k in range(5)]
                ys = [j['y'] + math.sin(k * math.pi / 2) * (0 if k == 4 else 4) for k in range(5)]
                self._jh[j['id']] = float(np.mean(self.h(xs, ys)))
        return self._jh

    def _pins(self):
        JH = self.junction_heights()
        L = self.look

        def jpin(road, x, y):
            best, h = 8.0, None
            for j in L['junctions']:
                dd = math.hypot(x - j['x'], y - j['y'])
                if dd < best and road in j['roads']:
                    best, h = dd, JH[j['id']]
            return h
        ends = []
        for r in L['roads']:
            p = r['pts']
            if len(p) >= 4:
                ends += [(r['road'], p[0], p[1]), (r['road'], p[-2], p[-1])]
        used = [False] * len(ends)
        joins = []
        for a in range(len(ends)):
            if used[a]:
                continue
            cl, q = [a], 0
            used[a] = True
            while q < len(cl):
                for b in range(len(ends)):
                    if not used[b] and math.hypot(ends[cl[q]][1] - ends[b][1], ends[cl[q]][2] - ends[b][2]) < 1.5:
                        used[b] = True
                        cl.append(b)
                q += 1
            if len(cl) < 2:
                continue
            pins = [jpin(*ends[e]) for e in cl]
            if all(p is not None for p in pins):
                continue
            anyp = next((p for p in pins if p is not None), None)
            sh = sum(float(self.h(ends[e][1], ends[e][2])) for e in cl) / len(cl)
            joins.append((sum(ends[e][1] for e in cl) / len(cl), sum(ends[e][2] for e in cl) / len(cl), anyp if anyp is not None else sh))

        def pin(road, x, y):
            h = jpin(road, x, y)
            if h is not None:
                return h
            best, hh = 1.5, None
            for jx, jy, jh in joins:
                dd = math.hypot(x - jx, y - jy)
                if dd < best:
                    best, hh = dd, jh
            return hh
        return pin

    def profile(self, r, pin=None, passes=40, grade=ROAD_GRADE):
        pin = pin or self._pins()
        p = np.array(r['pts'], float).reshape(-1, 2)
        seg = np.hypot(*np.diff(p, axis=0).T)
        cum = np.concatenate([[0], np.cumsum(seg)])
        total = cum[-1]
        n = max(1, math.ceil(total / 2))
        s = total * np.arange(n + 1) / n
        xy = np.column_stack([np.interp(s, cum, p[:, 0]), np.interp(s, cum, p[:, 1])])
        raw = self.h(xy[:, 0], xy[:, 1])
        ds = s[None, :] - s[:, None]
        g = np.where(np.abs(ds) <= 24.0, np.exp(-ds ** 2 / 128.0), 0.0)
        h = (g * raw[None, :]).sum(1) / g.sum(1)
        p0, p1 = pin(r['road'], *xy[0]), pin(r['road'], *xy[-1])
        d0 = p0 - h[0] if p0 is not None else 0.0
        d1 = p1 - h[-1] if p1 is not None else 0.0
        if p0 is not None and p1 is None:
            d1 = d0 * max(0.0, 1 - total / 60)
        if p1 is not None and p0 is None:
            d0 = d1 * max(0.0, 1 - total / 60)
        h = h + d0 + (d1 - d0) * (s / total if total > 0 else 0)
        base = h.copy()
        N = len(s)
        for _ in range(passes):
            changed = False
            for i in range(N - 1):
                lim = grade * (s[i + 1] - s[i])
                diff = h[i + 1] - h[i]
                if abs(diff) <= lim + 1e-4:
                    continue
                ex = (abs(diff) - lim) * math.copysign(1, diff)
                la, lb = p0 is not None and i == 0, p1 is not None and i + 1 == N - 1
                if la and lb:
                    continue
                if la:
                    h[i + 1] -= ex
                elif lb:
                    h[i] += ex
                else:
                    h[i] += ex * 0.5
                    h[i + 1] -= ex * 0.5
                changed = True
            if not changed:
                break
        gr = np.abs(np.diff(h)) / np.maximum(0.01, np.diff(s)) if N > 1 else np.zeros(1)
        k = int(np.argmax(gr))
        return dict(max=float(gr.max()), at=[R(xy[k, 0]), R(xy[k, 1])], s=s, xy=xy, base=base, h=h, pinned=(p0 is not None, p1 is not None))

    def grades(self, ids=None):
        pin = self._pins()
        return {r['id']: self.profile(r, pin) for r in self.look['roads'] if len(r['pts']) >= 4 and (ids is None or r['id'] in ids)}


# ---------------------------------------------------------------- placement helpers (v18)
def solid_tree(W):
    if getattr(W, '_tree_n', -1) != len(W.solid):
        W._tree = shapely.STRtree([g for g, _ in W.solid])
        W._tree_n = len(W.solid)
    return W._tree


def occ_near(W, g, buf=0.0, skip=()):
    """Union of the solids near g (buffered by buf), optionally skipping some tags."""
    idx = solid_tree(W).query(g.buffer(buf + 0.5), predicate='intersects')
    gs = [W.solid[i][0] for i in idx if W.solid[i][1] not in skip]
    if not gs:
        return Polygon()
    u = unary_union(gs)
    return u.buffer(buf) if buf else u


def trees_near(W, g, r=2.5, start=0):
    pts = [(x, y) for x, y in W.tree_pts[start:] if g.buffer(r + 1).contains(Point(x, y))] if not g.is_empty else []
    return unary_union([Point(x, y).buffer(r) for x, y in pts]) if pts else Polygon()


def exclusions(W, d):
    pts = [Point(p['position_m']).buffer(14 if p['category'] == 'base' else 4.5) for p in d['points']]
    pts += [Point(p['van_stop_m']).buffer(3.5) for p in d['points'] if p.get('van_stop_m')]
    return unary_union([W.corridor.buffer(2.0), W.water.buffer(3.0), W.decks.buffer(8.0), unary_union(pts), W.police.buffer(2.5), W.driveways.buffer(2.5)])


def prepare(W, d):
    """Shared exclusions: roads with sidewalks, water, bridge decks, every gameplay point (bases 14 m), van stops, police lots."""
    W.excl0 = exclusions(W, d)
    W.boxes = district_boxes(d)
    W.border = unary_union([bx.exterior for bx in W.boxes.values()]).buffer(4.0)
    W.ridge = valid(Polygon(d['terrain_hints']['ridge']['out_of_bounds_polygon_m']))
    W.counts = collections.Counter()


def nearest_district(W, p):
    return min(W.boxes, key=lambda k: W.boxes[k].distance(p))


def bld(W, bid, district, wkind, btype, poly, floors, ground_h, floor_h, doors, roof='flat', zone='district', recipe='', label=''):
    """A v18 building. Common-land buildings carry the nearest district id (as v17's garage cooperative did) and zone 'common'."""
    b = W.add_building(bid, district, wkind, btype, poly, floors, ground_h, floor_h, doors, label=label, roof=roof, zone=zone, extra=dict(recipe=recipe, rev='v18'))
    b['entrance_status'] = 'v18 generated door (lead rule: street/yard facing)'
    # the crowd builder looks access roads up among the roads only (not the footpaths)
    door = Point(b['entrance_m'])
    ids = {r['id'] for r in W.d['roads']}
    b['access_road_id'] = min(((r, l) for r, l in W.roads if r['id'] in ids), key=lambda q: q[1].distance(door))[0]['id']
    return b


def fence(W, fid, kind, coords, district, h, gates=(), closed=False):
    """A yard/plot fence that never runs on a district border (the 4 m band round every district outline becomes a hedge
    instead) and never crosses a carriageway or water."""
    pts = list(coords)
    if closed and tuple(pts[0]) != tuple(pts[-1]):
        pts = pts + [pts[0]]
    line = LineString(pts)
    bad = unary_union([W.border, W.carriage.buffer(0.8), W.water.buffer(0.5)])
    keep = line.difference(bad)
    hedge = line.intersection(W.border).difference(W.carriage.buffer(1.5)).difference(W.water.buffer(1.0))
    pieces = [q for q in parts(keep, 'LineString') if q.length >= 1.5]
    n = 0
    for i, q in enumerate(pieces):
        gs = [(gx, gy, gw) for gx, gy, gw in gates if q.distance(Point(gx, gy)) < 0.6]
        fid_i = fid if len(pieces) == 1 else f'{fid}_{i + 1}'
        W.add_fence(fid_i, kind, list(q.coords), district, h, gates=gs)
        f = W.fences[-1]
        f['height_status'] = 'v18 generated'
        f['perimeter_role'] = 'v18_yard_fence (inside a district or common-land property; never on a district border)'
        n += 1
    for q in parts(hedge, 'LineString'):
        for s in np.arange(0.7, q.length, 1.5):
            p = q.interpolate(s)
            W.add_tree('bush', p.x, p.y, 1.6 + 0.3 * math.sin(p.x + p.y))
    return n


def structure(W, d, sid, district, kind, **geo):
    rec = dict(id=sid, district=m17.WID.get(district, 'CL'), kind=kind, district_id=district, world_district_id=m17.WID.get(district), note='v18 generated')
    rec.update(geo)
    d['structures'].append(rec)
    W.structs.append(rec)
    if kind == 'haystack':
        W.solid.append((Point(geo['position_m']).buffer(geo['radius_m']), 'haystack'))
    return rec


def well(W, d, wid, district, x, y):
    """A village well: a 1.6 m stone ring (water kind 'well', like v11's own 02_pond_2) with a bucket post (log bench)."""
    poly = [[R(x - 0.8), R(y - 0.8)], [R(x + 0.8), R(y - 0.8)], [R(x + 0.8), R(y + 0.8)], [R(x - 0.8), R(y + 0.8)]]
    d['water'].append(dict(id=wid, district=m17.WID.get(district, 'CL'), kind='well', polygon_m=poly, district_id=district,
                           world_district_id=m17.WID.get(district), level_m=0, note='v18 generated well'))
    W.new_water.append(wid)
    W.solid.append((Point(x, y).buffer(1.1), 'well'))


def pool(W, d, pid, district, g):
    d['water'].append(dict(id=pid, district=m17.WID[district], kind='swimming_pool', polygon_m=[[R(x), R(y)] for x, y in orient(g, 1).exterior.coords[:-1]],
                           district_id=district, world_district_id=m17.WID[district], level_m=0, note='v18 generated villa pool'))
    W.new_water.append(pid)
    W.solid.append((g, 'pool'))


def remove_trees(W, g, start=0):
    """Drop dressing trees (index >= start) inside g (a playground or a plot replaces a v17 tree clump)."""
    keep, gone = [], 0
    for i, t in enumerate(W.trees):
        if i >= start and g.contains(Point(t['x'], t['y'])):
            gone += 1
            continue
        keep.append(t)
    W.trees = keep
    W.tree_pts = [(t['x'], t['y']) for t in W.trees]
    return gone


def hedge_line(W, a, b, step=1.4, h=(1.5, 2.1), rng=None):
    L = math.dist(a, b)
    for s in np.arange(0.5, L, step):
        x, y = a[0] + (b[0] - a[0]) * s / L, a[1] + (b[1] - a[1]) * s / L
        W.add_tree('bush', x, y, float(rng.uniform(*h)) if rng is not None else 1.8)


def fit_dims(r, Lmax, Wmax, Lmin):
    """Largest L x W rectangle (aspect Lmax:Wmax) that fits the greedy disc of radius r, or None if L < Lmin."""
    k = min(1.0, (r - 0.4) / (0.5 * math.hypot(Lmax, Wmax)))
    return (Lmax * k, Wmax * k) if Lmax * k >= Lmin else None


def side(u):
    return (-u[1], u[0])


# ---------------------------------------------------------------- phase A fix 1: Downtown plaza core
PLAZA_CORE = box(848, 360, 888, 400)
PLAZA_WALKS = unary_union([box(864, 300, 872, 470), box(780, 376, 960, 384)])


def plaza_core(W):
    """The 40 x 40 m core round Vadim's fountain (POI 15) becomes a furnished square: the fountain is the centrepiece (scaled
    x1.6), a monument column north of it on the walk axis, four planter islands with a tree, bushes and benches, kiosks, double
    lamps. The two 8 m walks through the square stay clear; no open paving larger than ~25 x 25 m remains."""
    rng = rng_for('plaza-core')
    for p in W.props:
        if p['k'] == 'prop/fountain' and abs(p['x'] - 868) < 1 and abs(p['y'] - 370.6) < 1:
            p['s'] = 1.6
            W.solid.append((Point(868, 370.6).buffer(5.6), 'fountain'))
    W.add_prop('proc/clock_column', 868, 393.0, 180, foot=(1.6, 1.6), tag='monument')
    W.add_pad(Point(868, 393).buffer(3.2, 6), 'paving', 'v18_monument_plinth', prio=38)
    n = 0
    for cx, cy in ((855.5, 392.5), (880.5, 392.5), (855.0, 366.5), (881.0, 366.5)):
        isl = box(cx - 4.2, cy - 3.4, cx + 4.2, cy + 3.4)
        W.add_pad(isl, 'park_grass', 'v18_plaza_planter', prio=40)
        W.solid.append((isl.buffer(-0.2), 'planter'))
        W.add_tree('linden' if n % 2 else 'oak', cx, cy, float(rng.uniform(8.5, 10.0)))
        for dx, dy in ((-3.2, -2.4), (3.2, -2.4), (-3.2, 2.4), (3.2, 2.4)):
            W.add_tree('bush', cx + dx, cy + dy, float(rng.uniform(1.2, 1.6)))
        for sgn in (-1, 1):
            W.add_prop('prop/bench_park', cx, cy + sgn * 4.3, 0 if sgn < 0 else 180, foot=(0.7, 1.9), tag='bench')
        n += 1
    for x, y, k in ((850.5, 380.0, 'prop/kiosk'), (885.5, 380.0, 'prop/news_kiosk')):
        W.add_prop(k, x, y, 90 if x > 868 else 270, foot=(2.8, 3.0), tag='kiosk')
    for x, y in ((862, 386.5), (874, 386.5), (862, 376.5), (874, 376.5)):
        W.add_prop('prop/lamp_oldtown_double', x, y, 0, foot=(0.4, 0.4), tag='lamp', cast=False)
    for x, y in ((861.0, 391.5), (875.0, 391.5)):
        W.add_prop('prop/trashbin_concrete', x, y, 0, foot=(0.6, 0.6), tag='bin', cast=False)
    dev('Downtown plaza core (848-888 x 360-400): the fountain at POI 15 is the centrepiece (scaled x1.6); a monument column '
        '(the v17 clock-column model, no statue asset exists) at (868, 393); 4 planter islands with a tree, bushes and 2 benches each; '
        '2 kiosks; 4 double lamps; the two 8 m walks stay clear.')


def largest_open(g, obst, min_area=20):
    best, at = 0.0, None
    for p in parts(g.difference(obst)):
        if p.area < min_area:
            continue
        c, r = pole(p)
        if r > best:
            best, at = r, c
    return R(best), ([R(at.x), R(at.y)] if at is not None else None)


# ---------------------------------------------------------------- phase A fix 2: Rough District yards as rooms
def rough_rooms(W, d):
    """More rooms in the panel-block yards: playgrounds where the biggest gaps are (v17 tree clumps there are moved), extra
    laundry poles / dumpster pads / sheds / a garage row, then yard trees in every gap left."""
    RD = m17.RD_BOX
    rng = rng_for('rough-rooms')
    pitch = unary_union([valid(Polygon(s['polygon_m'])).buffer(3) for s in d['structures'] if s['id'] == '04_football_pitch'])
    doors = []
    for b in W.buildings.values():
        if b['district_id'] == 'residential' and b['world_kind'] == 'panel_block':
            for x, y in b.get('v17', {}).get('doors', []):
                doors.append(Point(x, y).buffer(6.0))
    area = RD.intersection(W.land).difference(W.excl0).difference(pitch).difference(unary_union(doors))
    hard = occ_near(W, RD, 0, skip=())
    blds = unary_union([g for g, t in W.solid if t == 'building' and g.intersects(RD.buffer(20))])
    zone = area.difference(hard.buffer(1.2)).difference(blds.buffer(3.0))
    items = collections.Counter()
    moved = 0
    state = dict(play=0)

    def place_big(part, pt, r, k):
        nonlocal moved
        u = edge_dir_near(part, pt)
        dims = fit_dims(r, 16.0, 12.0, 10.5)
        if state['play'] < 3 and dims:
            L, Wd = dims
            g = orect(pt.x, pt.y, u[0], u[1], L, Wd)
            if not part.buffer(0.3).contains(g):
                return pt.buffer(min(r, 4))
            state['play'] += 1
            moved += remove_trees(W, g.buffer(1.2))
            vx, vy = side(u)
            for j, key in enumerate(['prop/play_swings', 'prop/play_slide', 'prop/play_carousel', 'prop/play_sandbox', 'prop/play_horizontal_bar', 'prop/play_carpet_rack']):
                sx_, sy_ = (-L / 2 + 3.2) + (j % 3) * (L - 6.4) / 2, (Wd / 4 if j < 3 else -Wd / 4)
                W.add_prop(key, pt.x + u[0] * sx_ + vx * sy_, pt.y + u[1] * sx_ + vy * sy_, unity_yaw(*u), foot=(2.2, 2.8), tag='play')
            W.add_pad(g.buffer(-0.6), 'rubber', 'v18_playground')
            gate = g.exterior.interpolate(0.12, normalized=True)
            fence(W, f'04_v18_playground_{state["play"]}', 'fence_low_garden', list(orient(g, 1).exterior.coords), 'residential', 0.9,
                  gates=[(gate.x, gate.y, 1.6)], closed=True)
            for s_ in (-1, 1):
                W.add_prop('prop/bench_soviet', pt.x + vx * s_ * (Wd / 2 + 1.4), pt.y + vy * s_ * (Wd / 2 + 1.4), unity_yaw(-vx * s_, -vy * s_), foot=(0.7, 1.9), tag='bench')
            for s_ in (-1, 1):
                W.add_tree('linden', pt.x + u[0] * s_ * (L / 2 + 2.2), pt.y + u[1] * s_ * (L / 2 + 2.2), float(rng.uniform(8, 11)))
            items['playgrounds'] += 1
            return g.buffer(3.0)
        return pt.buffer(min(r, 4.0))

    greedy_fill(zone, place_big, 6.8, max_items=12)
    cycle = ['laundry', 'dumpsters', 'sheds', 'laundry', 'dumpsters', 'trees', 'sheds', 'trees']
    st = dict(k=0)

    def place_mid(part, pt, r, k):
        rr = rng_for(f'rough-mid{k}')
        u = edge_dir_near(part, pt)
        choice = cycle[st['k'] % len(cycle)] if st['k'] < len(cycle) else 'trees'
        st['k'] += 1
        if choice == 'laundry' and r >= 3.6:
            W.add_prop('proc/laundry_poles', pt.x, pt.y, unity_yaw(*u), foot=(0.4, 6.4), tag='laundry')
            W.add_prop('prop/carpet_rack', pt.x + side(u)[0] * 2.6, pt.y + side(u)[1] * 2.6, unity_yaw(*u), foot=(0.4, 2.6), tag='rack')
            items['laundry_poles'] += 1
            return pt.buffer(4.5)
        if choice == 'dumpsters' and r >= 3.2:
            pad = orect(pt.x, pt.y, u[0], u[1], 5.4, 2.6)
            if part.buffer(0.5).contains(pad):
                W.add_prop('proc/dumpster_pad', pt.x, pt.y, unity_yaw(*u), foot=(2.6, 5.4), tag='dumpster')
                for i in (-1, 0, 1):
                    W.add_prop('prop/garbage_container_closed' if i else 'prop/garbage_container_open', pt.x + u[0] * i * 1.65, pt.y + u[1] * i * 1.65, unity_yaw(-u[1], u[0]), solid=False)
                W.add_pad(pad.buffer(0.6), 'concrete', 'v18_dumpster_pad')
                items['dumpster_pads'] += 1
                return pad.buffer(2.5)
        if choice == 'sheds' and r >= 3.4:
            used = []
            for i in range(3):
                g = orect(pt.x + u[0] * (i - 1) * 3.6, pt.y + u[1] * (i - 1) * 3.6, u[0], u[1], 3.2, 3.0)
                if part.contains(g):
                    bld(W, f'04_v18_shed_{k:03d}_{i}', 'residential', 'v17_shed', 'shed', g, 1, 2.4, 2.4,
                        [(g.centroid.x - u[1] * 1.5, g.centroid.y + u[0] * 1.5)], roof='gable', recipe='shed')
                    used.append(g)
            if used:
                items['sheds'] += len(used)
                return unary_union(used).buffer(2.0)
        items['tree_clusters'] += 1
        return tree_disc(W, part, pt, max(min(r - 0.8, 7.0), 1.8), 5.0, ['poplar', 'birch', 'linden', 'birch', 'oak'], (9, 15), rr, under=0.3)

    hard = occ_near(W, RD, 0)
    zone2 = area.difference(hard.buffer(1.4)).difference(blds.buffer(3.0)).difference(trees_near(W, RD, 2.6))
    n_trees0 = len(W.trees)
    greedy_fill(zone2, place_mid, 3.0)
    items['trees_added'] = sum(1 for t in W.trees[n_trees0:] if t['sp'] != 'bush')
    items['trees_moved_for_playgrounds'] = moved
    dev(f'Rough District yards: {items["playgrounds"]} more fenced playgrounds (now {2 + items["playgrounds"]} + the kindergarten yard) in the largest '
        f'yard gaps ({moved} v17 yard trees there moved/replanted), {items["laundry_poles"]} laundry poles, {items["dumpster_pads"]} dumpster pads, '
        f'{items["sheds"]} sheds, {items["tree_clusters"]} more yard tree clumps.')
    return dict(items)


# ---------------------------------------------------------------- phase A fix 3: Downtown vista stoppers
VIEW_BLOCK = {'building', 'kiosk', 'stall', 'fountain', 'monument', 'busstop', 'truck', 'lifeguard', 'haystack', 'dumpster', 'heap', 'planter'}
def vistas(W, d):
    """Terminate the long straight Downtown views where the street axis leaves the carriageway (T-ends and bends): a
    tree clump with a kiosk/ad column on the axis just past the corridor; where the axis runs on as another road (05_B is one
    593 m straight with main_construction_city / main_city_elite) a 'gateway' of tree pairs and kiosks narrows the view."""
    rng = rng_for('vistas')
    out = []
    roads = {r['id']: (r, l) for r, l in W.roads}
    corr = W.corridor
    for rid in ('05_N', '05_B', '05_Va', '05_Vb', '05_Vc', '05_Vd', '05_W', '05_E', '05_S', '05_AX', '05_Va2'):
        r, l = roads[rid]
        cs = list(l.coords)
        for i in range(len(cs) - 1):
            a, b = cs[i], cs[i + 1]
            L = math.dist(a, b)
            if L < 100:
                continue
            u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            for end, dirn in ((b, u), (a, (-u[0], -u[1]))):
                # walk the axis past the end until it leaves the road corridor
                s, exit_s = 0.0, None
                while s < 700:
                    p = Point(end[0] + dirn[0] * s, end[1] + dirn[1] * s)
                    if not corr.buffer(0.5).contains(p):
                        exit_s = s
                        break
                    s += 1.0
                rec = dict(road=rid, from_=[R(end[0]), R(end[1])], dir=[R(dirn[0]), R(dirn[1])], straight_m=R(L))
                if exit_s is None or exit_s > 60:
                    rec['result'] = 'axis continues on another road (no stopper possible without moving a centreline)'
                    if rid == '05_B':
                        # gateway: tree pairs and kiosks on both sides just outside the corridor at the district edge
                        n = 0
                        for off in (10.0, 20.0, 30.0, 40.0):
                            c = Point(end[0] + dirn[0] * off, end[1] + dirn[1] * off)
                            nx, ny = side(dirn)
                            for sd in (-1, 1):
                                q = Point(c.x + nx * sd * 9.5, c.y + ny * sd * 9.5)
                                if corr.buffer(1.5).contains(q) or not occ_near(W, q.buffer(3.0)).is_empty or W.excl0.contains(q):
                                    continue
                                W.add_tree('linden', q.x, q.y, float(rng.uniform(11, 14)))
                                n += 1
                                if off == 20.0:
                                    k = Point(q.x + nx * sd * 4.5, q.y + ny * sd * 4.5)
                                    if occ_near(W, k.buffer(2.5)).is_empty and not W.excl0.contains(k):
                                        W.add_prop('prop/kiosk', k.x, k.y, unity_yaw(-nx * sd, -ny * sd), foot=(2.8, 3.0), tag='kiosk')
                        rec['gateway_trees'] = n
                    out.append(rec)
                    continue
                ex = Point(end[0] + dirn[0] * exit_s, end[1] + dirn[1] * exit_s)
                # already terminated (a building/tree right behind the corridor)?
                probe = LineString([ex, (ex.x + dirn[0] * 35, ex.y + dirn[1] * 35)])
                idx = solid_tree(W).query(probe.buffer(1.0), predicate='intersects')
                blocked = any(W.solid[i][1] in VIEW_BLOCK and W.solid[i][0].intersects(probe.buffer(1.0)) for i in idx) or \
                    any(probe.distance(Point(x, y)) < 2.5 for x, y in W.tree_pts if abs(x - ex.x) < 40 and abs(y - ex.y) < 40)
                if blocked:
                    rec['result'] = 'already terminated within 35 m past the corridor'
                    out.append(rec)
                    continue
                c = Point(ex.x + dirn[0] * 9.0, ex.y + dirn[1] * 9.0)
                spot = c.buffer(7.5).difference(corr.buffer(2.0)).difference(occ_near(W, c.buffer(8), 1.0)).difference(W.water.buffer(2))
                if spot.is_empty or spot.area < 30:
                    rec['result'] = 'no room past the corridor'
                    out.append(rec)
                    continue
                tree_disc(W, largest(spot), c, 6.5, 4.2, ['linden', 'oak', 'linden'], (9, 13), rng, under=0.35)
                k = Point(c.x + dirn[0] * -2.0 + side(dirn)[0] * 4.0, c.y + dirn[1] * -2.0 + side(dirn)[1] * 4.0)
                if spot.buffer(-1.2).contains(k):
                    W.add_prop('prop/kiosk' if len(out) % 2 else 'prop/ad_column', k.x, k.y, unity_yaw(-dirn[0], -dirn[1]), foot=(2.8, 3.0), tag='kiosk')
                rec['result'] = f'stopper (tree clump + kiosk) at {R(c.x)}, {R(c.y)}'
                out.append(rec)
    n_stop = sum(1 for q in out if q['result'].startswith('stopper'))
    dev(f'Downtown vistas: {n_stop} street ends terminated with a tree clump and a kiosk/ad column on the axis just past the corridor; '
        '05_B / main_construction_city / main_city_elite stay one 593 m straight (centrelines fixed) - a tree-and-kiosk gateway narrows '
        'it at the district edge, the elite KPP closes it in the east; a planted median or a roundabout is an open question for Vadim.')
    return out


# ---------------------------------------------------------------- phase B: game scale for the buildings v17 did not touch
SCALE = {  # type -> (ground floor m, upper floors m); special volumes (tanks, hangars, frames, containers, towers, barns) keep their height
    'village_shop': (SHOP_GROUND, STOREY), 'grandpa_house': (STOREY, STOREY), 'old_dormitory': (3.0, STOREY), 'guard_booth': (2.8, STOREY),
    'kiosk': (3.0, STOREY), 'container_cabin_2storey': (2.6, 2.6), 'container_cabin': (2.6, 2.6), 'container_canteen_or_shower': (2.6, 2.6),
    'container_foreman_office': (2.6, 2.6), 'barracks': (3.0, STOREY), 'military_hq': (SHOP_GROUND, STOREY), 'mansion': (3.2, 3.0),
    'beach_service_building': (SHOP_GROUND, STOREY), 'lab_final_base': (SHOP_GROUND, STOREY), 'private_security': (3.0, STOREY),
    'checkpoint_booth': (2.8, STOREY), 'shed': (2.5, 2.5), 'car_workshop': (4.2, STOREY), 'warehouse': (4.5, 3.2)}


def rescale_rest(W, d):
    n, ex = 0, []
    for b in d['functional_buildings']:
        if b.get('v17') or b['district_id'] in ('old_town', 'residential'):
            continue
        if b['type'] in SCALE:
            g, f = SCALE[b['type']]
            h0 = b['height_m']
            W.scale_building(b, None, g, f)
            b['v17'].update(rev='v18', recipe='rescaled')
            n += 1
            if len(ex) < 8:
                ex.append(f"{b['id']} {h0} -> {b['height_m']} m")
    dev(f'{n} buildings outside phase A get game-scale storeys (2.8 m; shop/public ground floor 3.3 m; tanks, hangars, barns, frames, '
        f'containers, towers, church and palace keep their volume), e.g. ' + ', '.join(ex))
    return n


def zone_of(W, area, buf=2.0, trees=True, extra=()):
    g = area.intersection(W.land).difference(W.excl0)
    for e in extra:
        g = g.difference(e)
    g = g.difference(occ_near(W, area, buf))
    if trees:
        g = g.difference(trees_near(W, area, 2.4))
    return valid(g)


def keep_open(d, dist, kinds, buf=2.0):
    return unary_union([valid(Polygon(s['polygon_m'])).buffer(buf) for s in d['structures']
                        if s['district_id'] == dist and s['kind'] in kinds and s.get('polygon_m') and len(s['polygon_m']) >= 3])


def struct_poly(d, sid):
    s = next(q for q in d['structures'] if q['id'] == sid)
    return valid(Polygon(s['polygon_m']))


def toward_road(W, p):
    q = W.carriage.boundary.interpolate(W.carriage.boundary.project(p))
    dx, dy = q.x - p.x, q.y - p.y
    L = math.hypot(dx, dy) or 1
    return (dx / L, dy / L), L


# ---------------------------------------------------------------- village (Hamlet) and farmsteads
def farm_plot(W, d, pid, district, pt, u, L, Wd, rng, items, house=True, beds=True, well_ok=True, hay=True, barn=False, zone='district'):
    """A fenced plot: a 6-10 m house at the road side, a shed at the back, orchard rows, vegetable beds, a woodpile, a
    well and haystacks. u = unit vector toward the road (house side)."""
    v = side(u)
    plot = orect(pt.x, pt.y, v[0], v[1], L, Wd)        # L along the road, Wd away from it
    used = [plot]
    door = None
    if house:
        hw, hd = float(rng.uniform(7.0, 10.0)), float(rng.uniform(6.0, 8.0))
        c = (pt.x + u[0] * (Wd / 2 - hd / 2 - 2.5), pt.y + u[1] * (Wd / 2 - hd / 2 - 2.5))
        c = (c[0] + v[0] * float(rng.uniform(-1, 1)) * max(0, L / 2 - hw / 2 - 3), c[1] + v[1] * float(rng.uniform(-1, 1)) * max(0, L / 2 - hw / 2 - 3))
        hg = orect(c[0], c[1], v[0], v[1], hw, hd)
        door = (c[0] + u[0] * hd / 2, c[1] + u[1] * hd / 2)
        bld(W, f'{pid}_house', district, 'village_house', 'village_house', hg, 1, STOREY, STOREY, [door], roof='gable', zone=zone, recipe='plot_house_6_10m')
        items['houses'] += 1
    back = (pt.x - u[0] * (Wd / 2 - 3.2), pt.y - u[1] * (Wd / 2 - 3.2))
    sg = orect(back[0] + v[0] * (L / 2 - 4.0), back[1] + v[1] * (L / 2 - 4.0), v[0], v[1], 3.6, 3.0)
    bld(W, f'{pid}_shed', district, 'shed', 'shed', sg, 1, 2.4, 2.4, [(sg.centroid.x + u[0] * 1.5, sg.centroid.y + u[1] * 1.5)], roof='gable', zone=zone, recipe='plot_shed')
    items['sheds'] += 1
    if barn:
        bc = (back[0] - v[0] * (L / 2 - 10.0), back[1] - v[1] * (L / 2 - 10.0))
        bg = orect(bc[0], bc[1], v[0], v[1], 14.0, 8.0)
        bld(W, f'{pid}_barn', district, 'barn', 'barn', bg, 1, 5.5, 5.5, [(bc[0] + u[0] * 4.0, bc[1] + u[1] * 4.0)], roof='gable', zone=zone, recipe='farm_barn')
        items['barns'] += 1
    # orchard: two rows of fruit trees in the back half
    for i in range(int((L - 6) // 5.5)):
        for j in range(2):
            x = pt.x + v[0] * (-L / 2 + 3.5 + i * 5.5) - u[0] * (1.0 + j * 4.5)
            y = pt.y + v[1] * (-L / 2 + 3.5 + i * 5.5) - u[1] * (1.0 + j * 4.5)
            if sg.buffer(2.0).contains(Point(x, y)) or (barn and bg.buffer(2.0).contains(Point(x, y))):
                continue
            W.add_tree('fruit', x, y, float(rng.uniform(4.0, 6.0)))
            items['orchard_trees'] += 1
    if beds:
        bg = orect(pt.x - u[0] * (Wd / 2 - 3.5) - v[0] * (L / 4), pt.y - u[1] * (Wd / 2 - 3.5) - v[1] * (L / 4), v[0], v[1], min(9, L / 2 - 2), 4.5)
        structure(W, d, f'{pid}_beds', district, 'vegetable_beds', polygon_m=[[R(x), R(y)] for x, y in orient(bg, 1).exterior.coords[:-1]])
        items['vegetable_beds'] += 1
    wp = (pt.x + v[0] * (L / 2 - 2.0) + u[0] * 1.0, pt.y + v[1] * (L / 2 - 2.0) + u[1] * 1.0)
    W.add_prop('prop/log_bench', wp[0], wp[1], unity_yaw(*u), foot=(0.6, 2.4), tag='woodpile')
    W.add_prop('prop/log_bench', wp[0] + u[0] * 0.7, wp[1] + u[1] * 0.7, unity_yaw(*u), foot=(0.6, 2.4), tag='woodpile')
    items['woodpiles'] += 1
    if well_ok:
        well(W, d, f'{pid}_well', district, pt.x - v[0] * (L / 2 - 2.5) + u[0] * 2.0, pt.y - v[1] * (L / 2 - 2.5) + u[1] * 2.0)
        items['wells'] += 1
    if hay:
        hx, hy = back[0] - v[0] * (L / 2 - 4.5), back[1] - v[1] * (L / 2 - 4.5)
        structure(W, d, f'{pid}_haystack', district, 'haystack', position_m=[R(hx), R(hy)], radius_m=2.0)
        items['haystacks'] += 1
    gate = (pt.x + u[0] * Wd / 2 + v[0] * (L / 2 - 4), pt.y + u[1] * Wd / 2 + v[1] * (L / 2 - 4))
    fence(W, f'{pid}_fence', 'fence_wood_yard' if rng.random() < 0.6 else 'fence_dacha', list(orient(plot, 1).exterior.coords), district,
          1.6, gates=[(gate[0], gate[1], 3.0)], closed=True)
    W.clear_zones.append(plot)
    if district == 'village' and zone == 'district':
        W.hamlet_new_plots.append((pid, plot))
    items['plots'] += 1
    return plot


def village(W, d):
    rng = rng_for('village')
    V = W.boxes['village']
    items = collections.Counter()
    resized = []
    pts = [Point(p['position_m']) for p in d['points']]
    for b in [b for b in d['functional_buildings'] if b['district_id'] == 'village' and b['world_kind'] == 'village_house']:
        g0 = valid(geom(b))
        rr = g0.minimum_rotated_rectangle
        cs = list(rr.exterior.coords)
        e0, e1 = (cs[1][0] - cs[0][0], cs[1][1] - cs[0][1]), (cs[2][0] - cs[1][0], cs[2][1] - cs[1][1])
        door0 = Point(b['entrance_m'])
        c0 = g0.centroid
        inward = (c0.x - door0.x, c0.y - door0.y)
        Li = math.hypot(*inward) or 1
        inward = (inward[0] / Li, inward[1] / Li)
        # facade axis: the rectangle edge most perpendicular to the inward direction
        fa = max((e0, e1), key=lambda e: abs(e[0] * inward[1] - e[1] * inward[0]) / (math.hypot(*e) or 1))
        La = math.hypot(*fa)
        fa = (fa[0] / La, fa[1] / La)
        nin = (-fa[1], fa[0]) if (-fa[1]) * inward[0] + fa[0] * inward[1] > 0 else (fa[1], -fa[0])
        hw, hd = float(rng.uniform(7.5, 10.0)), float(rng.uniform(6.0, 8.0))
        inside = [q for q in pts if g0.contains(q)]
        c = (inside[0].x, inside[0].y) if inside else (door0.x + nin[0] * (hd / 2 + 0.05), door0.y + nin[1] * (hd / 2 + 0.05))
        for _ in range(40):
            ng = orect(c[0], c[1], fa[0], fa[1], hw, hd)
            if g0.buffer(0.3).contains(ng):
                break
            c = (c[0] + (c0.x - c[0]) * 0.15, c[1] + (c0.y - c[1]) * 0.15)
        door = (c[0] - nin[0] * hd / 2, c[1] - nin[1] * hd / 2)
        ng = orient(ng, 1)
        w_, dep, ang = m16.obb(ng)
        old = f"{b['id']} {R(b['width_m'])}x{R(b['depth_m'])}"
        b.update(footprint_m=[[R(x), R(y)] for x, y in ng.exterior.coords[:-1]], center_m=[R(ng.centroid.x), R(ng.centroid.y)], width_m=R(w_),
                 depth_m=R(dep), orientation_deg=R(ang), entrance_m=[R(door[0]), R(door[1])], storeys=1, floors=1,
                 entrance_status='v18: same street side, house shrunk to 6-10 m')
        W.scale_building(b, 1, STOREY, STOREY)
        b['v17'].update(rev='v18', roof='gable', recipe='village_house_6_10m')
        W.solid[W.bidx[b['id']]] = (ng, 'building')
        resized.append(f"{old} -> {R(hw)}x{R(hd)}")
    dev(f'Hamlet: {len(resized)} village houses shrunk to 6-10 m on their own plots (same street side and door direction; houses holding a '
        'POI keep it inside): ' + ', '.join(resized))
    # Existing plots: fence + yard furniture.
    plots = [s for s in d['structures'] if s['district_id'] == 'village' and s['kind'] == 'plot_or_garden']
    blds = unary_union([g for g, t in W.solid if t == 'building' and g.intersects(V.buffer(30))])
    k_well = 0
    for s in plots:
        g = valid(Polygon(s['polygon_m']))
        if g.area < 60:
            continue
        gi = orient(largest(g.buffer(-0.6)) or g, 1)
        dr, _ = toward_road(W, gi.centroid)
        gate = gi.exterior.interpolate(gi.exterior.project(Point(gi.centroid.x + dr[0] * 60, gi.centroid.y + dr[1] * 60)))
        ring = LineString(list(gi.exterior.coords)).difference(blds.buffer(0.4))
        for i, q in enumerate(parts(ring, 'LineString')):
            if q.length > 1.5:
                fence(W, f"02_v18_plotfence_{s['id']}_{i + 1}", 'fence_wood_yard' if i % 3 else 'fence_dacha', list(q.coords), 'village', 1.5,
                      gates=[(gate.x, gate.y, 3.0)])
        items['plot_fences'] += 1
        free = gi.buffer(-1.0).difference(occ_near(W, gi, 1.2)).difference(keep_open(d, 'village', ('vegetable_beds',), 0.8)).difference(W.excl0)
        st = dict(k=0)

        def place(part, pt, r, k, s=s):
            nonlocal k_well
            rr = rng_for(f"plot-{s['id']}-{k}")
            u = edge_dir_near(part, pt)
            ch = ['orchard', 'woodpile', 'well', 'orchard', 'shed', 'orchard', 'haystack'][st['k'] % 7]
            st['k'] += 1
            if ch == 'well' and k_well < 8 and r >= 1.8:
                k_well += 1
                well(W, d, f"02_v18_well_{s['id']}", 'village', pt.x, pt.y)
                items['wells'] += 1
                return pt.buffer(2.6)
            if ch == 'woodpile' and r >= 1.6:
                W.add_prop('prop/log_bench', pt.x, pt.y, unity_yaw(*u), foot=(0.6, 2.4), tag='woodpile')
                W.add_prop('prop/log_bench', pt.x + side(u)[0] * 0.7, pt.y + side(u)[1] * 0.7, unity_yaw(*u), foot=(0.6, 2.4), tag='woodpile')
                items['woodpiles'] += 1
                return pt.buffer(2.4)
            if ch == 'shed' and r >= 2.6:
                g2 = orect(pt.x, pt.y, u[0], u[1], 3.4, 2.8)
                if part.contains(g2):
                    bld(W, f"02_v18_shed_{s['id']}_{k}", 'village', 'shed', 'shed', g2, 1, 2.4, 2.4, [(pt.x - u[1] * 1.4, pt.y + u[0] * 1.4)], roof='gable', recipe='plot_shed')
                    items['sheds'] += 1
                    return g2.buffer(1.5)
            if ch == 'haystack' and r >= 2.6:
                structure(W, d, f"02_v18_hay_{s['id']}_{k}", 'village', 'haystack', position_m=[R(pt.x), R(pt.y)], radius_m=2.0)
                items['haystacks'] += 1
                return pt.buffer(3.4)
            n0 = len(W.trees)
            tree_disc(W, part, pt, max(1.5, min(r - 0.6, 5.0)), 4.4, ['fruit'], (3.8, 5.8), rr)
            items['orchard_trees'] += len(W.trees) - n0
            return pt.buffer(max(2.0, min(r, 5.6)))
        greedy_fill(free, place, 1.8)
        W.clear_zones.append(gi)
    # New fenced plots on the empty lawn, then orchards, hedgerows and haystacks until no lawn wider than ~30 m is left.
    fields = keep_open(d, 'village', ('yellow_field',), 1.0)
    keep = keep_open(d, 'village', ('plot_or_garden', 'vegetable_beds', 'base_yard_van_spot'), 2.0)
    tower = unary_union([Point(s['position_m']).buffer(s['radius_m'] + 3) for s in d['structures'] if s['district_id'] == 'village' and s['kind'] in ('water_tower', 'haystack')])
    zone = zone_of(W, V.buffer(-5.0), 2.5, extra=(fields, keep, tower))
    st = dict(plots=0, k=0)

    def place_v(part, pt, r, k):
        rr = rng_for(f'village{k}')
        u, dist = toward_road(W, pt)
        dims = fit_dims(r, 28.0, 22.0, 18.0)
        if st['plots'] < 10 and dims and dist < 45:
            L, Wd = dims
            plot = orect(pt.x, pt.y, -u[1], u[0], L, Wd)
            if part.buffer(0.3).contains(plot):
                st['plots'] += 1
                farm_plot(W, d, f'02_v18_plot_{st["plots"]:02d}', 'village', pt, u, L, Wd, rr, items, well_ok=st['plots'] % 2 == 1, hay=st['plots'] % 3 != 2)
                return plot.buffer(2.5)
        st['k'] += 1
        ch = ['orchard', 'hedgerow', 'orchard', 'haystacks'][st['k'] % 4]
        if ch == 'hedgerow' and r >= 9:
            v = edge_dir_near(part, pt)
            a = (pt.x - v[0] * (r - 2), pt.y - v[1] * (r - 2))
            b = (pt.x + v[0] * (r - 2), pt.y + v[1] * (r - 2))
            hedge_line(W, a, b, 1.6, (1.6, 2.4), rr)
            for t in np.arange(3, 2 * r - 4, 9):
                W.add_tree(['oak', 'linden', 'birch'][int(rr.integers(3))], a[0] + v[0] * t, a[1] + v[1] * t, float(rr.uniform(9, 13)))
            items['hedgerows'] += 1
            return LineString([a, b]).buffer(5.0)
        if ch == 'haystacks' and r >= 5:
            for j in range(3):
                structure(W, d, f'02_v18_hay_{k}_{j}', 'village', 'haystack', position_m=[R(pt.x + (j - 1) * 4.6), R(pt.y + (j % 2) * 3.0)], radius_m=2.0)
            items['haystacks'] += 3
            return pt.buffer(7.0)
        n0 = len(W.trees)
        tree_disc(W, part, pt, max(2.0, min(r - 1.0, 9.0)), 5.0, ['fruit', 'fruit', 'oak', 'birch', 'fruit'], (4.5, 9.0), rr, under=0.15)
        items['orchard_trees'] += len(W.trees) - n0
        return pt.buffer(max(3.0, min(r, 9.5)))

    greedy_fill(zone, place_v, 7.5)
    # Yellow fields: haystack rows and a hedge along the long edges (POI 08/09 stay clear).
    for s in d['structures']:
        if s['district_id'] == 'village' and s['kind'] == 'yellow_field':
            g = valid(Polygon(s['polygon_m'])).buffer(-3)
            for j, q in enumerate(parts(g)):
                c = q.centroid
                for i in range(3):
                    p = Point(c.x + (i - 1) * 7.0, c.y + (i % 2) * 5.0 - 2.5)
                    if q.contains(p.buffer(2.2)) and W.excl0.distance(p) > 2.5:
                        structure(W, d, f"02_v18_fieldhay_{s['id']}_{i}", 'village', 'haystack', position_m=[R(p.x), R(p.y)], radius_m=2.2)
                        items['haystacks'] += 1
    dev(f"Hamlet: {items['plot_fences']} existing plots fenced (gates to the street) and furnished; {items['plots']} new fenced plots with 6-10 m houses; "
        f"{items['sheds']} sheds, {items['orchard_trees']} orchard trees, {items['vegetable_beds']} vegetable beds, {items['woodpiles']} woodpiles, "
        f"{items['wells']} wells, {items['haystacks']} haystacks, {items['hedgerows']} hedgerows.")
    return dict(items, resized=len(resized))


# ---------------------------------------------------------------- Fedya 2026-10-12: a tighter hamlet
HAMLET_TARGET = 0.30      # aimed cut of every big gap between neighbouring house plots (fallback: ~20 % + small-object fill)
HAMLET_BIG_GAP = 8.0      # plot-to-plot gaps (fence to fence) from 8 m up count as "big"
HAMLET_MAX_ACCESS = 20.0  # a moved plot stays within 20 m of a fixed hamlet street (or its old distance, if that was larger)
HAMLET_FILL_SHARE = 0.10  # fallback: small objects cover ~10 % of the empty land left


def hamlet_units(W, d):
    """House plots that move as one unit: every v11 plot with a house (not the base 2 yard) and every new v18 plot."""
    base_pts = [Point(p['position_m']) for p in d['points'] if p['category'] == 'base']
    units = []
    for s in d['structures']:
        if s['district_id'] != 'village' or s['kind'] != 'plot_or_garden':
            continue
        g = valid(Polygon(s['polygon_m']))
        if any(g.buffer(1.0).contains(q) for q in base_pts):
            continue
        hs = [b for b in W.buildings.values() if b['district_id'] == 'village' and b['world_kind'] == 'village_house' and g.contains(geom(b).centroid)]
        if hs:
            units.append(dict(id=s['id'], poly=g, house=hs[0]['id']))
    for pid, plot in W.hamlet_new_plots:
        units.append(dict(id=pid, poly=plot, house=f'{pid}_house'))
    return units


def hamlet_members(W, d, u, drive_ids):
    """Everything that belongs to a plot unit: buildings, plan structures (plot, beds, haystacks), wells, fences, trees, props,
    ground pads, solids, clear zones, POIs inside its house and its driveway."""
    reg = u['poly'].buffer(1.0)
    inr = lambda x, y: reg.contains(Point(x, y))
    m = dict(buildings=[b['id'] for b in W.buildings.values() if b['district_id'] == 'village' and u['poly'].contains(geom(b).centroid)])
    m['structures'] = [s for s in d['structures'] if s['district_id'] == 'village' and s['kind'] != 'meadow_with_grass_tufts' and (
        (s.get('polygon_m') and len(s['polygon_m']) >= 3 and reg.contains(valid(Polygon(s['polygon_m'])).centroid)) or
        (s.get('position_m') and s['kind'] != 'water_tower' and inr(*s['position_m'])))]
    m['water'] = [w for w in d['water'] if w['id'] in W.new_water and reg.contains(valid(Polygon(w['polygon_m'])).centroid)]
    m['fences'] = [f for f in W.fences if f['district_id'] == 'village' and reg.buffer(0.5).contains(LineString(f['polyline_m']))]
    m['trees'] = [t for t in W.trees if inr(t['x'], t['y'])]
    m['props'] = [p for p in W.props if inr(p['x'], p['y'])]
    m['pads'] = [i for i, (g, _, _, _) in enumerate(W.pads) if reg.contains(g.centroid)]
    m['solids'] = [i for i, (g, _) in enumerate(W.solid) if reg.buffer(0.5).contains(g)]
    m['clear'] = [i for i, g in enumerate(W.clear_zones) if reg.buffer(0.5).contains(g)]
    house = geom(W.buildings[u['house']]).buffer(0.3)
    m['points'] = [p['id'] for p in d['points'] if house.contains(Point(p['position_m']))]
    m['drive'] = [r['id'] for r in d['roads'] if r['id'] in drive_ids and reg.buffer(4.0).contains(Point(r['polyline_m'][-1]))]
    return m


def hamlet_solve(W, d, units, mem, drive_ids):
    """Deterministic spring relaxation: every unit steps 0.5 m toward its two nearest neighbour plots while any of those gaps
    is above (1 - HAMLET_TARGET) of its start; a step is taken only if the plot gets no deeper into fixed roads (all roads but
    the plots' own driveways), fixed buildings, fields, the base yard, the water tower, fixed points / van stops, water or the
    4 m district-border band than it was, keeps 2.5 m to other plots, stays near a hamlet street and widens no neighbour gap."""
    V = W.boxes['village']
    moving = {i for m in mem.values() for i in m['buildings']}
    moved_pts = {i for m in mem.values() for i in m['points']}
    fixed_roads = [(r, l) for r, l in W.roads if r['id'] not in drive_ids]
    streets = [l for r, l in fixed_roads if r['district_id'] == 'village']
    corr = unary_union([l.buffer(r['width_m'] / 2 + (r.get('sidewalk_width_m') or 0), cap_style=2, join_style=2) for r, l in fixed_roads if l.distance(V) < 30])
    fixb = unary_union([geom(b) for b in W.buildings.values() if b['id'] not in moving and geom(b).intersects(V.buffer(10))])
    uid = {u['id'] for u in units}
    fixs = unary_union([valid(Polygon(s['polygon_m'])) for s in d['structures'] if s['district_id'] == 'village' and (
                            s['kind'] in ('yellow_field', 'base_yard_van_spot') or (s['kind'] == 'plot_or_garden' and s['id'] not in uid))] +
                       [Point(s['position_m']).buffer(s['radius_m'] + 1) for s in d['structures'] if s['district_id'] == 'village' and s['kind'] == 'water_tower'])
    pts = []
    for p in d['points']:
        if p['id'] in moved_pts:
            continue
        pts.append(Point(p['position_m']).buffer(14 if p['category'] == 'base' else 4.5))
        if p.get('van_stop_m'):
            pts.append(Point(p['van_stop_m']).buffer(3.5))
    OB = unary_union([corr.buffer(1.0), fixb.buffer(2.0), fixs.buffer(2.0), unary_union(pts), W.water.buffer(2.0)])
    inner = V.buffer(-4.0)
    U = {u['id']: u['poly'] for u in units}
    ids = [u['id'] for u in units]
    ov0 = {k: U[k].intersection(OB).area for k in ids}
    out0 = {k: U[k].difference(inner).area for k in ids}
    acc0 = {k: min(l.distance(U[k]) for l in streets) for k in ids}
    T = {k: (0.0, 0.0) for k in ids}
    placed = lambda k, t=None: shapely.affinity.translate(U[k], *(t or T[k]))
    NB = set()
    for a in ids:
        for _, b in sorted((U[a].distance(U[b]), b) for b in ids if b != a)[:2]:
            NB.add(tuple(sorted((a, b))))
    NB = sorted(NB)
    g0 = {p: U[p[0]].distance(U[p[1]]) for p in NB}

    def ok(k, t):
        g = shapely.affinity.translate(U[k], *t)
        if g.difference(inner).area > out0[k] + 0.05 or g.intersection(OB).area > ov0[k] + 0.05:
            return False
        if min(l.distance(g) for l in streets) > max(acc0[k], HAMLET_MAX_ACCESS) + 0.01:
            return False
        cur = placed(k)
        for o in ids:
            if o != k:
                dn = g.distance(placed(o))
                if dn < 2.5 and dn < cur.distance(placed(o)) - 1e-6:
                    return False
        for p in NB:
            if k in p:
                o = p[1] if p[0] == k else p[0]
                if g.distance(placed(o)) > max(g0[p], cur.distance(placed(o))) + 1e-6:
                    return False
        return True

    ca = sa = math.sqrt(0.5)
    for it in range(800):
        moved = 0
        for k in ids:
            fx = fy = 0.0
            cur = placed(k)
            for p in NB:
                if k not in p:
                    continue
                o = p[1] if p[0] == k else p[0]
                if cur.distance(placed(o)) > max(3.0, (1 - HAMLET_TARGET) * g0[p]):
                    a, b = shapely.ops.nearest_points(cur, placed(o))
                    L = a.distance(b)
                    fx, fy = fx + (b.x - a.x) / L, fy + (b.y - a.y) / L
            L = math.hypot(fx, fy)
            if L < 1e-6:
                continue
            ux, uy = fx / L, fy / L
            for vx, vy in ((ux, uy), (ux * ca - uy * sa, ux * sa + uy * ca), (ux * ca + uy * sa, -ux * sa + uy * ca)):
                t = (T[k][0] + vx * 0.5, T[k][1] + vy * 0.5)
                if ok(k, t):
                    T[k] = t
                    moved += 1
                    break
        if not moved:
            break
    T = {k: (R(x), R(y)) for k, (x, y) in T.items()}
    return T, NB, g0, it


def shift_xy(p, t):
    return [R(p[0] + t[0]), R(p[1] + t[1])]


def hamlet_apply(W, d, mem, T):
    """Translate every member of every unit by its vector."""
    for k, m in mem.items():
        t = T[k]
        if t == (0.0, 0.0):
            continue
        for bid in m['buildings']:
            b = W.buildings[bid]
            b['footprint_m'] = [shift_xy(q, t) for q in b['footprint_m']]
            b['center_m'] = shift_xy(b['center_m'], t)
            b['entrance_m'] = shift_xy(b['entrance_m'], t)
            if b.get('v17', {}).get('doors'):
                b['v17']['doors'] = [shift_xy(q, t) for q in b['v17']['doors']]
            b['v18_hamlet_shift_m'] = list(t)
        for s in m['structures']:
            if s.get('polygon_m') and len(s['polygon_m']) >= 3:
                s['polygon_m'] = [shift_xy(q, t) for q in s['polygon_m']]
            if s.get('position_m'):
                s['position_m'] = shift_xy(s['position_m'], t)
            s['v18_hamlet_shift_m'] = list(t)
        for w in m['water']:
            w['polygon_m'] = [shift_xy(q, t) for q in w['polygon_m']]
        for f in m['fences']:
            f['polyline_m'] = [shift_xy(q, t) for q in f['polyline_m']]
            f['solid_runs_m'] = [[shift_xy(q, t) for q in run] for run in f['solid_runs_m']]
            for g in f['gates']:
                g['position_m'] = shift_xy(g['position_m'], t)
        for tr in m['trees']:
            tr['x'], tr['y'] = R(tr['x'] + t[0]), R(tr['y'] + t[1])
        for p in m['props']:
            p['x'], p['y'] = R(p['x'] + t[0]), R(p['y'] + t[1])
        for i in m['pads']:
            g, mat, ctx, prio = W.pads[i]
            W.pads[i] = (shapely.affinity.translate(g, *t), mat, ctx, prio)
        for i in m['solids']:
            g, tag = W.solid[i]
            W.solid[i] = (shapely.affinity.translate(g, *t), tag)
        for i in m['clear']:
            W.clear_zones[i] = shapely.affinity.translate(W.clear_zones[i], *t)
        for p in d['points'] + d['pois']:
            if p['id'] in m['points']:
                p['position_m'] = shift_xy(p['position_m'], t)
    W.tree_pts = [(t['x'], t['y']) for t in W.trees]
    W._tree_n = -1


def hamlet_clear(W, d, mem, units):
    """Village dressing outside the plots that the moved plots now cover is removed (trees, props, haystacks, ground pads)."""
    V = W.boxes['village']
    mine_t = {id(t) for m in mem.values() for t in m['trees']}
    mine_p = {id(p) for m in mem.values() for p in m['props']}
    mine_s = {id(s) for m in mem.values() for s in m['structures']}
    mine_i = {i for m in mem.values() for i in m['solids']}
    mine_pad = {i for m in mem.values() for i in m['pads']}
    cover = unary_union([m_['poly'] for m_ in units]).buffer(1.5)
    cover1 = cover.buffer(1.0)
    shapely.prepare(cover)
    shapely.prepare(cover1)
    gone = collections.Counter()
    keep = []
    for t in W.trees:
        if id(t) not in mine_t and V.contains(Point(t['x'], t['y'])) and cover.contains(Point(t['x'], t['y'])):
            gone['trees_bushes'] += 1
            continue
        keep.append(t)
    W.trees = keep
    W.tree_pts = [(t['x'], t['y']) for t in W.trees]
    keep = []
    for p in W.props:
        q = Point(p['x'], p['y'])
        if id(p) not in mine_p and V.contains(q) and cover1.contains(q):
            gone['props'] += 1
            continue
        keep.append(p)
    W.props = keep
    hay = [s for s in d['structures'] if s['district_id'] == 'village' and s['kind'] == 'haystack' and id(s) not in mine_s and cover1.contains(Point(s['position_m']))]
    for s in hay:
        d['structures'].remove(s)
        W.structs.remove(s)
    gone['haystacks'] = len(hay)
    solid, remap = [], {}
    for i, (g, tag) in enumerate(W.solid):
        if i in mine_i or tag in ('building', 'fence') or not (V.contains(g.centroid) and cover1.contains(g.centroid)):
            remap[i] = len(solid)
            solid.append((g, tag))
    W.solid = solid
    W.bidx = {k: remap[i] for k, i in W.bidx.items()}
    W.bidx_rev = {remap[i]: k for i, k in W.bidx_rev.items()}
    pads = []
    for i, (g, mat, ctx, prio) in enumerate(W.pads):
        if i not in mine_pad and g.intersects(V) and g.intersects(cover):
            gone['pads_cut'] += 1
            for q in parts(g.difference(cover)):
                if q.area > 2:
                    pads.append((q, mat, ctx, prio))
            continue
        pads.append((g, mat, ctx, prio))
    W.pads = pads
    W._tree_n = -1
    return dict(gone)


def hamlet_roads(W, d, mem, T, drive_ids):
    """Reshape the driveways of moved plots (straight spur from the old street to the moved end), re-project the van stops of
    the POIs that moved with their houses, rebuild both graphs with the v16 method and refresh the road-derived exclusions."""
    streets = {r['id']: LineString(r['polyline_m']) for r in d['roads'] if r['district_id'] == 'village' and r['id'] not in drive_ids}
    out = []
    for k, m in mem.items():
        t = T[k]
        if t == (0.0, 0.0):
            continue
        for rid in m['drive']:
            r = next(q for q in d['roads'] if q['id'] == rid)
            a, z = r['polyline_m'][0], r['polyline_m'][-1]
            parent = min(streets, key=lambda s: streets[s].distance(Point(a)))
            pl = streets[parent]
            nz = shift_xy(z, t)
            na = pl.interpolate(pl.project(Point(nz)))
            old = R(LineString(r['polyline_m']).length)
            r['polyline_m'] = [[R(na.x), R(na.y)], nz]
            r['length_m'] = LineString(r['polyline_m']).length
            r['source_note'] = f'v18: reshaped after its plot moved by {R(math.hypot(*t))} m (Fedya 2026-10-12)'
            out.append(dict(road=rid, parent=parent, length_before_m=old, length_after_m=R(r['length_m'])))
    lines = {r['id']: LineString(r['polyline_m']) for r in d['roads']}
    moved = {pid: k for k, m in mem.items() for pid in m['points'] if T[k] != (0.0, 0.0)}
    for p in d['points']:
        if p['id'] in moved:
            l = lines[p['access_road_id']]
            stop = l.interpolate(l.project(Point(p['position_m'])))
            p['van_stop_m'] = list(stop.coords[0])
            p['van_stop_offset_m'] = Point(p['position_m']).distance(stop)
            p['access_status'] = 'v18: moved with its house (hamlet plot moved, Fedya 2026-10-12); van stop re-projected on the same access road'
    old_nodes = {p['id']: p['road_node_id'] for p in d['points']}
    d['road_graph'] = m16.graph(d['roads'])
    d['pedestrian_graph'] = m16.graph(d['roads'] + d['paths'])
    for p in d['points']:
        n = m16.graph_stop(d['road_graph'], list(p['van_stop_m']))
        if p['id'] in moved:
            p['road_node_id'] = n['id']
            p['van_node_gap_m'] = Point(n['position_m']).distance(Point(p['van_stop_m']))
        elif n['id'] != old_nodes[p['id']]:
            raise RuntimeError('graph rebuild changed the node of fixed point ' + p['id'])
    W.roads = [(r, LineString(r['polyline_m'])) for r in d['roads'] + d['paths']]
    W.carriage = unary_union([l.buffer(r['width_m'] / 2, cap_style=2, join_style=2) for r, l in W.roads])
    W.corridor = unary_union([l.buffer(r['width_m'] / 2 + (r.get('sidewalk_width_m') or 0), cap_style=2, join_style=2) for r, l in W.roads])
    deg = collections.Counter(n for e in d['road_graph']['edges'] for n in (e['from_node'], e['to_node']))
    W.nodes = [Point(n['position_m']) for n in d['road_graph']['nodes'] if deg[n['id']] >= 3]
    W.ends = [Point(n['position_m']) for n in d['road_graph']['nodes'] if deg[n['id']] == 1]
    W.points = [Point(p['position_m']) for p in d['points']]
    W.excl0 = exclusions(W, d)
    return out, sorted(moved)


def hamlet_fill(W, d, units):
    """Fallback fill: small objects on the empty hamlet land left after the move (scarecrows, bushes, garages, a ruined shed or
    barn, abandoned cars, crop rows, hay bales, a broken tractor, a cart, a well) until they cover ~10 % of it."""
    V = W.boxes['village']
    plots = unary_union([u['poly'] for u in units] + [valid(Polygon(s['polygon_m'])) for s in d['structures'] if s['district_id'] == 'village' and s['kind'] == 'plot_or_garden'])
    fields = keep_open(d, 'village', ('yellow_field', 'vegetable_beds', 'base_yard_van_spot'), 1.0)
    tower = unary_union([Point(s['position_m']).buffer(s['radius_m'] + 3) for s in d['structures'] if s['district_id'] == 'village' and s['kind'] == 'water_tower'])
    zone = zone_of(W, V.buffer(-4.0), 1.5, extra=(plots.buffer(1.5), fields, tower))
    empty = zone.area
    st = dict(covered=0.0, k=0, wells=0, tractors=0, barns=0)
    items = collections.Counter()
    cyc = ['crop_rows', 'scarecrow', 'hay_bales', 'abandoned_car', 'ruined_shed', 'bushes', 'garage', 'cart', 'crop_rows', 'well', 'hay_bales',
           'broken_tractor', 'abandoned_car', 'bushes', 'garage', 'scarecrow']

    def bush_ring(pt, n, r, rr):
        for j in range(n):
            a = 2 * math.pi * (j + rr.uniform(0, 0.5)) / n
            W.add_tree('bush', pt.x + r * math.cos(a), pt.y + r * math.sin(a), float(rr.uniform(1.1, 1.6)))

    def place(part, pt, r, k):
        if st['covered'] >= HAMLET_FILL_SHARE * empty:
            return pt.buffer(r + 1.0)
        rr = rng_for(f'hamlet-fill{k}')
        u = edge_dir_near(part, pt)
        v = side(u)
        ch = cyc[st['k'] % len(cyc)]
        st['k'] += 1
        if ch == 'crop_rows' and r >= 5.0:
            L, Wd = min(2 * r - 2.5, 18.0), min(2 * r - 2.5, 11.0)
            g = orect(pt.x, pt.y, u[0], u[1], L, Wd).intersection(part)
            W.add_pad(g.buffer(-0.3), 'dry_field', 'v18_crop_rows', prio=31)
            st['covered'] += g.area
            items['crop_row_patches'] += 1
            if k % 2:
                W.add_prop('prop/scarecrow', pt.x, pt.y, unity_yaw(*v), foot=(0.6, 1.2), tag='scarecrow')
                items['scarecrows'] += 1
            return g.buffer(1.5)
        if ch == 'scarecrow':
            W.add_prop('prop/scarecrow', pt.x, pt.y, float(rr.uniform(0, 360)), foot=(0.6, 1.2), tag='scarecrow')
            bush_ring(pt, 3, 2.2, rr)
            st['covered'] += 0.7 + 3 * math.pi
            items['scarecrows'] += 1
            items['bushes'] += 3
            return pt.buffer(min(r, 4.5))
        if ch == 'hay_bales' and r >= 3.2:
            for j in range(3):
                structure(W, d, f'02_v18b_bale_{k}_{j}', 'village', 'haystack', position_m=[R(pt.x + u[0] * (j - 1) * 2.9), R(pt.y + u[1] * (j - 1) * 2.9)], radius_m=1.2)
            st['covered'] += 3 * math.pi * 1.44
            items['hay_bales'] += 3
            return pt.buffer(min(r, 5.0))
        if ch == 'abandoned_car' and r >= 3.2:
            W.add_prop('prop/car_wrecked' if k % 2 else 'prop/car_burnt', pt.x, pt.y, float(rr.uniform(0, 360)), foot=CAR, tag='car')
            bush_ring(pt, 2, 3.0, rr)
            st['covered'] += CAR[0] * CAR[1] + 2 * math.pi
            items['abandoned_cars'] += 1
            return pt.buffer(min(r, 4.5))
        if ch == 'ruined_shed' and r >= 3.6:
            barn = r >= 7.0 and st['barns'] < 1
            L, Wd = (9.0, 6.0) if barn else (4.2, 3.4)
            g = orect(pt.x, pt.y, u[0], u[1], L, Wd)
            if part.contains(g):
                st['barns'] += barn
                bld(W, f'02_v18b_ruin_{k:03d}', 'village', 'barn' if barn else 'shed', 'barn' if barn else 'shed', g, 1, 3.2 if barn else 2.0, 3.2 if barn else 2.0,
                    [(pt.x + v[0] * Wd / 2, pt.y + v[1] * Wd / 2)], roof='gable', recipe='ruined_barn' if barn else 'ruined_shed', label='ruined')
                st['covered'] += g.area
                items['ruined_barns' if barn else 'ruined_sheds'] += 1
                return g.buffer(2.5)
        if ch == 'garage' and r >= 4.0:
            dr, _ = toward_road(W, pt)
            W.add_prop('prop/garage_metal_rust' if k % 2 else 'prop/garage_metal_open', pt.x, pt.y, unity_yaw(*dr), foot=(3.4, 6.0), tag='garage')
            st['covered'] += 3.4 * 6.0
            items['garages'] += 1
            return pt.buffer(min(r, 5.5))
        if ch == 'cart' and r >= 3.0:
            W.add_prop('prop/cart_wooden', pt.x, pt.y, float(rr.uniform(0, 360)), foot=(1.6, 3.0), tag='cart')
            structure(W, d, f'02_v18b_bale_{k}_c', 'village', 'haystack', position_m=[R(pt.x + v[0] * 2.6), R(pt.y + v[1] * 2.6)], radius_m=1.2)
            st['covered'] += 4.8 + math.pi * 1.44
            items['carts'] += 1
            items['hay_bales'] += 1
            return pt.buffer(min(r, 4.5))
        if ch == 'well' and st['wells'] < 2 and r >= 2.5:
            st['wells'] += 1
            well(W, d, f'02_v18b_well_{k}', 'village', pt.x, pt.y)
            st['covered'] += math.pi * 1.21
            items['wells'] += 1
            return pt.buffer(min(r, 3.5))
        if ch == 'broken_tractor' and st['tractors'] < 2 and r >= 3.2:
            st['tractors'] += 1
            W.add_prop('prop/tractor_small', pt.x, pt.y, float(rr.uniform(0, 360)), foot=(1.8, 3.4), tag='tractor')
            bush_ring(pt, 2, 3.0, rr)
            st['covered'] += 1.8 * 3.4 + 2 * math.pi
            items['broken_tractors'] += 1
            return pt.buffer(min(r, 4.5))
        n = int(rr.integers(3, 6))
        bush_ring(pt, n, min(r - 0.8, 2.5), rr)
        st['covered'] += n * math.pi
        items['bushes'] += n
        return pt.buffer(min(r, 4.0))

    greedy_fill(zone, place, 2.5)
    # a mailbox beside the street gate of every house plot
    for u in units:
        reg = u['poly'].buffer(1.5)
        gates = [g for f in W.fences if f['district_id'] == 'village' and reg.contains(LineString(f['polyline_m'])) for g in f['gates']]
        if not gates:
            continue
        g = min(gates, key=lambda q: W.carriage.distance(Point(q['position_m'])))
        c = Point(g['position_m'])
        dr, _ = toward_road(W, c)
        for sgn in (1, -1):
            q = Point(c.x + dr[0] * 0.7 - dr[1] * sgn * (g['width_m'] / 2 + 0.6), c.y + dr[1] * 0.7 + dr[0] * sgn * (g['width_m'] / 2 + 0.6))
            if W.carriage.buffer(0.5).disjoint(q) and occ_near(W, q.buffer(0.3)).is_empty:
                W.add_prop('prop/mailbox', q.x, q.y, unity_yaw(dr[0], dr[1]), foot=(0.4, 0.4), tag='mailbox')
                items['mailboxes'] += 1
                break
    return dict(items, empty_land_m2=R(empty), covered_m2=R(st['covered']), covered_pct=R(100 * st['covered'] / empty) if empty else 0)


def hamlet_gaps(W, d, units, NB, g0):
    """Plot-to-plot (fence to fence) gaps for the neighbour pairs fixed at the start, and house-to-house distances for each
    house's two nearest houses at the start."""
    B = W.buildings
    S = {s['id']: s for s in d['structures']}
    poly = {}
    for u in units:
        if u['id'] in S:
            poly[u['id']] = valid(Polygon(S[u['id']]['polygon_m']))
        else:
            t = B[u['house']].get('v18_hamlet_shift_m', (0.0, 0.0))
            poly[u['id']] = shapely.affinity.translate(u['poly'], *t)
    rows = [dict(a=a, b=b, before_m=R(g0[(a, b)]), after_m=R(poly[a].distance(poly[b]))) for a, b in NB]
    big = [q for q in rows if q['before_m'] >= HAMLET_BIG_GAP]
    return rows, big


def hamlet_house_pairs(houses0, houses1):
    ids = sorted(houses0)
    pairs = set()
    for a in ids:
        for _, b in sorted((houses0[a].distance(houses0[b]), b) for b in ids if b != a)[:2]:
            pairs.add(tuple(sorted((a, b))))
    return [dict(a=a, b=b, before_m=R(houses0[a].distance(houses0[b])), after_m=R(houses1[a].distance(houses1[b]))) for a, b in sorted(pairs)]


def hamlet(W, d):
    units = hamlet_units(W, d)
    drive_ids = {r['id'] for r in d['roads'] if r['district_id'] == 'village' and r['id'].startswith('02_h_d') and r['id'] != '02_h_d_tower'}
    mem = {u['id']: hamlet_members(W, d, u, drive_ids) for u in units}
    houses0 = {u['house']: geom(W.buildings[u['house']]) for u in units}
    T, NB, g0, iters = hamlet_solve(W, d, units, mem, drive_ids)
    hamlet_apply(W, d, mem, T)
    gone = hamlet_clear(W, d, mem, units)
    drives, moved_pois = hamlet_roads(W, d, mem, T, drive_ids)
    fill = hamlet_fill(W, d, units)
    rows, big = hamlet_gaps(W, d, units, NB, g0)
    houses1 = {u['house']: geom(W.buildings[u['house']]) for u in units}
    hp = hamlet_house_pairs(houses0, houses1)
    mean = lambda q, k: float(np.mean([x[k] for x in q])) if q else 0.0
    cut = lambda q: R(100 * (1 - mean(q, 'after_m') / mean(q, 'before_m'))) if q else 0.0
    hbig = [q for q in hp if q['before_m'] >= 30]
    shifts = {k: dict(shift_m=list(t), dist_m=R(math.hypot(*t)), house=next(u['house'] for u in units if u['id'] == k),
                      pois=[p for p in mem[k]['points'] if t != (0.0, 0.0)]) for k, t in T.items()}
    res = dict(units=len(units), solver_rounds=iters, target_cut_pct=100 * HAMLET_TARGET, plot_shifts=shifts,
               plot_gap_pairs=rows, big_plot_gaps=dict(n=len(big), mean_before_m=R(mean(big, 'before_m')), mean_after_m=R(mean(big, 'after_m')), cut_pct=cut(big)),
               house_pairs=hp, house_gaps=dict(n=len(hp), mean_before_m=R(mean(hp, 'before_m')), mean_after_m=R(mean(hp, 'after_m')), cut_pct=cut(hp)),
               house_gaps_ge_30m=dict(n=len(hbig), mean_before_m=R(mean(hbig, 'before_m')), mean_after_m=R(mean(hbig, 'after_m')), cut_pct=cut(hbig)),
               removed_under_moved_plots=gone, driveways=drives, pois_moved_with_houses=moved_pois, fill=fill,
               fallback=cut(big) < 100 * HAMLET_TARGET - 3)
    n_moved = sum(1 for t in T.values() if t != (0.0, 0.0))
    dev(f"Hamlet tightened (Fedya 2026-10-12): {n_moved} of {len(units)} house plots moved as whole units (house, fence, yard, sheds, garden) "
        f"by up to {max(v['dist_m'] for v in shifts.values())} m toward their neighbours; big plot-to-plot gaps {res['big_plot_gaps']['mean_before_m']} -> "
        f"{res['big_plot_gaps']['mean_after_m']} m ({res['big_plot_gaps']['cut_pct']} %), house-to-house {res['house_gaps']['mean_before_m']} -> "
        f"{res['house_gaps']['mean_after_m']} m; {len(drives)} driveways reshaped; POIs moved with their houses: {', '.join(moved_pois) or 'none'}; "
        f"fallback fill {fill['covered_pct']} % of {fill['empty_land_m2']} m2 empty land.")
    return res


def thin_trees(W, keep_ids, share=0.2):
    """Deterministic ~20 % cut of the trees and tall bushes (>= eye height) v18 generated outside the phase A fixes: the
    tree-tunnel rows lose every 5th tree (gaps of ~17 m); everything else is thinned densest-first (most neighbours within
    8 m for trees, 5 m for tall bushes; ties by a hash of the position); a tree with fewer than 3 neighbours is never cut."""
    cand = [t for t in W.trees if id(t) not in keep_ids and (t['sp'] != 'bush' or t['h'] >= EYE)]
    tunnel = [t for t in cand if id(t) in W.tunnel]
    cut = set()
    for t in tunnel:
        if W.tunnel[id(t)][2] % 5 == 2:
            cut.add(id(t))
    n_tun = len(cut)
    out = dict(candidates=len(cand), tunnel=len(tunnel), tunnel_cut=n_tun)
    for cls, rad in (('tree', 8.0), ('tall_bush', 5.0)):
        pool = [t for t in cand if id(t) not in W.tunnel and (t['sp'] == 'bush') == (cls == 'tall_bush')]
        need = int(round(share * len(pool)))
        xy = np.array([(t['x'], t['y']) for t in pool]) if pool else np.zeros((0, 2))
        cell = collections.defaultdict(list)
        for i, (x, y) in enumerate(xy):
            cell[(int(x // rad), int(y // rad))].append(i)
        nb = []
        for i, (x, y) in enumerate(xy):
            cx, cy = int(x // rad), int(y // rad)
            nb.append([j for a in (-1, 0, 1) for b in (-1, 0, 1) for j in cell[(cx + a, cy + b)] if j != i and (xy[j, 0] - x) ** 2 + (xy[j, 1] - y) ** 2 <= rad * rad])
        cnt = [len(q) for q in nb]
        key = lambda i: int(hashlib.md5(f"{pool[i]['x']:.3f},{pool[i]['y']:.3f}".encode()).hexdigest()[:8], 16)
        heap = [(-cnt[i], key(i), i) for i in range(len(pool))]
        heapq.heapify(heap)
        alive = [True] * len(pool)
        done = 0
        while heap and done < need:
            c, h, i = heapq.heappop(heap)
            if not alive[i]:
                continue
            if -c != cnt[i]:
                heapq.heappush(heap, (-cnt[i], h, i))
                continue
            if cnt[i] < 3:
                break
            alive[i] = False
            cut.add(id(pool[i]))
            done += 1
            for j in nb[i]:
                if alive[j]:
                    cnt[j] -= 1
        out[cls] = dict(pool=len(pool), cut=done)
    removed = [t for t in W.trees if id(t) in cut]
    W.trees = [t for t in W.trees if id(t) not in cut]
    W.tree_pts = [(t['x'], t['y']) for t in W.trees]
    out['cut_total'] = len(removed)
    out['cut_pct'] = R(100 * len(removed) / len(cand)) if cand else 0
    by = collections.Counter()
    for t in removed:
        p = Point(t['x'], t['y'])
        by[next((k for k, bx in W.boxes.items() if bx.contains(p)), 'common')] += 1
    out['cut_by_district'] = dict(sorted(by.items()))
    dev(f"Trees thinned (Fedya 2026-10-12): {out['cut_total']} of {out['candidates']} v18 trees and tall bushes ({out['cut_pct']} %), densest first; "
        f"the tree tunnels keep 4 of every 5 trees ({n_tun} cut, gaps of ~17 m); phase A fixes (plaza, vistas, Rough District yards) untouched.")
    return out, removed


# ---------------------------------------------------------------- industrial port, construction site, Tramduro
def container_block(W, district, bid, pt, u, n_long, n_wide, tiers, rng):
    """A block of shipping-container stacks: each stack 12.2 x 2.5 m, 1-3 high (2.6 m per tier), 0.4 m joints."""
    v = side(u)
    used = []
    for i in range(n_wide):
        for j in range(n_long):
            c = (pt.x + v[0] * (i - (n_wide - 1) / 2) * 2.9 + u[0] * (j - (n_long - 1) / 2) * 12.8,
                 pt.y + v[1] * (i - (n_wide - 1) / 2) * 2.9 + u[1] * (j - (n_long - 1) / 2) * 12.8)
            g = orect(c[0], c[1], u[0], u[1], 12.2, 2.5)
            t = int(rng.integers(1, tiers + 1))
            bld(W, f'{bid}_{i}{j}', district, 'shipping_container_stack', 'shipping_container_stack', g, t, 2.6, 2.6, [(c[0] + u[0] * 6.1, c[1] + u[1] * 6.1)], recipe='container_stack')
            used.append(g)
    return unary_union(used)


def industrial(W, d):
    rng = rng_for('industrial')
    items = collections.Counter()
    yard = struct_poly(d, '06_yard')
    keep = unary_union([keep_open(d, 'industrial', ('loading_yard', 'quay_gantry_crane'), 2.5)])
    # Tank farm: an inner chain-link fence round both tanks with a gate, pipe racks to the quay.
    tanks = unary_union([geom(W.buildings[i]) for i in ('06_05_tank_1', '06_05_tank_2')])
    tf = orient(tanks.minimum_rotated_rectangle.buffer(4.0, join_style=2), 1)
    gate = tf.exterior.interpolate(tf.exterior.project(Point(1041, 600)))
    fence(W, '06_v18_tankfarm_fence', 'fence_chainlink', list(tf.exterior.coords), 'industrial', 2.2, gates=[(gate.x, gate.y, 5.0)])
    items['inner_fences'] += 1
    tb = tf.bounds
    for x0, y0, x1, y1 in ((tb[0] - 2.5, tb[1] - 2.5, tb[2] + 14, tb[1] - 2.5), (tb[2] + 14, tb[1] - 2.5, tb[2] + 14, tb[3])):
        L = math.dist((x0, y0), (x1, y1))
        for s in np.arange(0, L + 0.1, 4.0):
            x, y = x0 + (x1 - x0) * s / L, y0 + (y1 - y0) * s / L
            if W.excl0.contains(Point(x, y)) or not occ_near(W, Point(x, y).buffer(0.8)).is_empty:
                continue
            W.add_prop('prop/pipe_support', x, y, unity_yaw(x1 - x0, y1 - y0), foot=(1.0, 1.0), tag='pipe')
            items['pipe_supports'] += 1
    zone = zone_of(W, yard.buffer(-3.0), 2.5, extra=(keep, tf.buffer(2.0)))
    st = dict(k=0, wh=0)
    cyc = ['containers', 'trucks', 'pallets', 'containers', 'fence', 'pallets', 'containers', 'trucks']

    def place(part, pt, r, k):
        rr = rng_for(f'ind{k}')
        u = edge_dir_near(part, pt)
        dims = fit_dims(r, 30.0, 18.0, 22.0)
        if st['wh'] < 2 and dims:
            L, Wd = dims
            g = orect(pt.x, pt.y, u[0], u[1], L, Wd)
            if part.buffer(0.3).contains(g):
                st['wh'] += 1
                dr, _ = toward_road(W, pt)
                bld(W, f'06_v18_warehouse_{st["wh"]}', 'industrial', 'warehouse', 'warehouse', g, 2, 4.5, 3.2, [(pt.x + dr[0] * Wd / 2, pt.y + dr[1] * Wd / 2)], recipe='port_warehouse')
                items['warehouses'] += 1
                return g.buffer(4.0)
        ch = cyc[st['k'] % len(cyc)]
        st['k'] += 1
        if ch == 'containers' and r >= 6.5:
            nl = int(min(3, max(1, (2 * r - 2) // 12.8)))
            nw = int(min(4, max(1, (2 * r - 2) // 2.9)))
            g = container_block(W, 'industrial', f'06_v18_cont_{k:03d}', pt, u, nl, nw, 3, rr)
            items['container_stacks'] += nl * nw
            return g.buffer(3.0)
        if ch == 'trucks' and r >= 4.5:
            n = int(min(3, max(1, (2 * r - 1) // 3.4)))
            for i in range(n):
                x, y = pt.x + side(u)[0] * (i - (n - 1) / 2) * 3.4, pt.y + side(u)[1] * (i - (n - 1) / 2) * 3.4
                W.add_prop('prop/truck_tow' if (i + k) % 3 else 'prop/van_minibus', x, y, unity_yaw(*u), foot=foot_of('prop/truck_tow'), tag='truck')
            items['trucks'] += n
            return pt.buffer(min(r, 3.4 * n / 2 + 4))
        if ch == 'fence' and r >= 7:
            a = (pt.x - u[0] * (r - 1.5), pt.y - u[1] * (r - 1.5))
            b = (pt.x + u[0] * (r - 1.5), pt.y + u[1] * (r - 1.5))
            fence(W, f'06_v18_inner_fence_{k:03d}', 'fence_chainlink', [a, b], 'industrial', 2.2)
            items['inner_fences'] += 1
            return LineString([a, b]).buffer(3.0)
        n = int(min(6, max(2, r // 1.4)))
        for i in range(n):
            W.add_prop('prop/default_crate', pt.x + u[0] * (i % 3) * 1.4, pt.y + u[1] * (i % 3) * 1.4 + 0 * i, unity_yaw(*u), foot=(1.2, 1.2), tag='pallet')
        items['pallet_stacks'] += n
        return pt.buffer(min(r, 4.5))

    greedy_fill(zone, place, 4.5)
    # Outside the yard fence (rest of the district box): trees and a few parked trucks along the port road.
    zone2 = zone_of(W, W.boxes['industrial'].buffer(-5).difference(yard.buffer(4)), 2.5)

    def place2(part, pt, r, k):
        rr = rng_for(f'ind2{k}')
        n0 = len(W.trees)
        g = tree_disc(W, part, pt, max(2.0, min(r - 1, 9)), 5.0, ['poplar', 'birch', 'poplar'], (11, 16), rr, under=0.3)
        items['trees'] += len(W.trees) - n0
        return g
    greedy_fill(zone2, place2, 5.0)
    dev(f"Industrial port: {items['container_stacks']} container stacks, {items['warehouses']} warehouses, {items['pipe_supports']} pipe-rack supports, "
        f"{items['inner_fences']} inner chain-link fences (tank farm, yard rows), {items['trucks']} trucks/vans, {items['pallet_stacks']} pallet stacks; "
        "the loading yard and the gantry crane stay clear.")
    return dict(items)


def transition(W, d):
    rng = rng_for('transition')
    items = collections.Counter()
    site = largest(valid(Polygon(next(f for f in d['fences'] if f['id'] == '03_fence')['polyline_m'])))
    T = W.boxes['transition']
    crane = Point(next(s for s in d['structures'] if s['id'] == '03_06_tower_crane')['position_m']).buffer(7)
    zone = zone_of(W, site.buffer(-3.0), 2.5, extra=(crane,))
    st = dict(k=0)
    cyc = ['pallets', 'cabins', 'gravel', 'truck', 'pallets', 'rebar', 'toilets', 'gravel']

    def place(part, pt, r, k):
        rr = rng_for(f'site{k}')
        u = edge_dir_near(part, pt)
        ch = cyc[st['k'] % len(cyc)]
        st['k'] += 1
        if ch == 'cabins' and r >= 5:
            used = []
            for i in range(3):
                g = orect(pt.x + side(u)[0] * (i - 1) * 2.9, pt.y + side(u)[1] * (i - 1) * 2.9, u[0], u[1], 6.0, 2.4)
                if part.contains(g):
                    bld(W, f'03_v18_cabin_{k:03d}_{i}', 'transition', 'container_cabin', 'container_cabin', g, 1, 2.6, 2.6, [(g.centroid.x + u[0] * 3, g.centroid.y + u[1] * 3)], recipe='site_cabin')
                    used.append(g)
            if used:
                items['cabins'] += len(used)
                return unary_union(used).buffer(2.0)
        if ch == 'toilets' and r >= 2.5:
            for i in range(2):
                g = orect(pt.x + u[0] * i * 1.6, pt.y + u[1] * i * 1.6, u[0], u[1], 1.3, 1.3)
                bld(W, f'03_v18_toilet_{k:03d}_{i}', 'transition', 'kiosk', 'kiosk', g, 1, 2.3, 2.3, [(g.centroid.x - u[1] * 0.65, g.centroid.y + u[0] * 0.65)], recipe='site_toilet')
            items['toilets'] += 2
            return pt.buffer(2.8)
        if ch == 'truck' and r >= 4.5:
            W.add_prop('prop/truck_tow', pt.x, pt.y, unity_yaw(*u), foot=foot_of('prop/truck_tow'), tag='truck')
            items['trucks'] += 1
            return pt.buffer(5.0)
        if ch == 'gravel' and r >= 3:
            g = pt.buffer(min(r - 0.5, 5.0), 8)
            W.add_pad(g, 'gravel' if st['k'] % 2 else 'sand', 'v18_site_heap', prio=37)
            W.solid.append((g.buffer(-0.5), 'heap'))
            items['heaps'] += 1
            return g.buffer(1.5)
        n = int(min(8, max(2, r // 1.3)))
        for i in range(n):
            W.add_prop('prop/default_crate', pt.x + u[0] * (i % 4) * 1.35 + side(u)[0] * (i // 4) * 1.35, pt.y + u[1] * (i % 4) * 1.35 + side(u)[1] * (i // 4) * 1.35,
                       unity_yaw(*u), foot=(1.2, 1.2), tag='pallet')
        items['pallets' if ch == 'pallets' else 'rebar_stacks'] += n
        return pt.buffer(min(r, 4.0))

    greedy_fill(zone, place, 3.5)
    # Outside the site fence: the workshop yard and the gas station get parked cars, tyre stacks and trees.
    zone2 = zone_of(W, T.buffer(-5).difference(site.buffer(3)), 2.5)
    st2 = dict(k=0)

    def place2(part, pt, r, k):
        rr = rng_for(f'trans2{k}')
        u = edge_dir_near(part, pt)
        st2['k'] += 1
        if st2['k'] % 3 == 1 and r >= 4:
            used = car_row(W, part, pt, u, int(min(4, max(1, (2 * r - 1) // 2.7))), rr, True, perpendicular=True)
            if used is not None:
                items['cars'] += 1
                return used.buffer(1.0)
        n0 = len(W.trees)
        g = tree_disc(W, part, pt, max(2.0, min(r - 1, 8)), 5.0, ['birch', 'poplar', 'linden'], (10, 15), rr, under=0.3)
        items['trees'] += len(W.trees) - n0
        return g
    greedy_fill(zone2, place2, 4.5)
    dev(f"Construction site (transition): {items['pallets'] + items['rebar_stacks']} pallet/rebar stacks, {items['cabins']} more container cabins, "
        f"{items['toilets']} site toilets, {items['heaps']} gravel/sand heaps, {items['trucks']} trucks inside the blue fence; parked cars and trees round the workshop/gas station.")
    return dict(items)


def tramduro(W, d):
    rng = rng_for('tramduro')
    items = collections.Counter()
    base = largest(valid(Polygon(next(f for f in d['fences'] if f['id'] == '10_base_fence')['polyline_m'])))
    Tb = W.boxes['tramduro']
    helipad = Point(next(s for s in d['structures'] if s['id'] == '10_05_helipad')['position_m']).buffer(16)
    park = struct_poly(d, '10_06_vehicle_park')
    # Vehicle park: rows of trucks.
    c = park.centroid
    for i in range(4):
        for j in range(3):
            x, y = c.x - 10.5 + i * 7.0, c.y - 8 + j * 8
            if park.buffer(-2).contains(Point(x, y)) and W.excl0.distance(Point(x, y)) > 1:
                W.add_prop('prop/truck_tow', x, y, 0, foot=foot_of('prop/truck_tow'), tag='truck')
                items['vehicles'] += 1
    # Watch towers at the inner corners of the base fence.
    cs = list(orient(base.simplify(2.0), 1).exterior.coords)[:-1]
    inner = orient(base.buffer(-6.0, join_style=2), 1).exterior
    for i, (x, y) in enumerate(cs):
        s0 = inner.project(Point(x, y))
        for off in (0, 6, -6, 12, -12, 18, -18):
            p = inner.interpolate((s0 + off) % inner.length)
            g = orect(p.x, p.y, 1, 0, 4.0, 4.0)
            if W.excl0.intersects(g) or not occ_near(W, g, 1.5).is_empty or g.intersects(helipad):
                continue
            bld(W, f'10_v18_watchtower_{i + 1}', 'tramduro', 'watch_tower', 'watch_tower', g, 3, 3.0, 3.0, [(p.x, p.y - 2.0)], recipe='watch_tower')
            items['watch_towers'] += 1
            break
    zone = zone_of(W, base.buffer(-3.0), 2.5, extra=(helipad, park.buffer(2)))
    st = dict(k=0)
    cyc = ['tents', 'barriers', 'tents', 'trees', 'trucks', 'barriers', 'tents', 'trees']

    def place(part, pt, r, k):
        rr = rng_for(f'mil{k}')
        u = edge_dir_near(part, pt)
        ch = cyc[st['k'] % len(cyc)]
        st['k'] += 1
        if ch == 'tents' and r >= 5:
            g = orect(pt.x, pt.y, u[0], u[1], 8.0, 5.0)
            if part.contains(g):
                bld(W, f'10_v18_tent_{k:03d}', 'tramduro', 'barracks', 'barracks', g, 1, 2.8, 2.8, [(pt.x + side(u)[0] * 2.5, pt.y + side(u)[1] * 2.5)], recipe='army_tent_barracks')
                items['tents'] += 1
                return g.buffer(2.5)
        if ch == 'barriers' and r >= 3:
            for i in range(-1, 2):
                W.add_prop('prop/fence_concrete_panel', pt.x + u[0] * i * 3.1, pt.y + u[1] * i * 3.1, unity_yaw(*side(u)), foot=(0.4, 3.0), tag='barrier')
            items['concrete_barriers'] += 3
            return pt.buffer(5.0)
        if ch == 'trucks' and r >= 4.5:
            W.add_prop('prop/truck_tow', pt.x, pt.y, unity_yaw(*u), foot=foot_of('prop/truck_tow'), tag='truck')
            items['vehicles'] += 1
            return pt.buffer(5.0)
        n0 = len(W.trees)
        g = tree_disc(W, part, pt, max(2.0, min(r - 1, 7)), 4.8, ['pine', 'pine', 'spruce'], (10, 15), rr, under=0.2)
        items['trees'] += len(W.trees) - n0
        return g
    greedy_fill(zone, place, 3.5)
    # Palace lawn: hedges, cypress rows and iron lamps along the inner edge (the lawn fence is Vadim's).
    lawn = struct_poly(d, '10_palace_lawn')
    inner = orient(lawn.buffer(-3.0), 1)
    k = 0
    for q in parts(inner):
        ring = q.exterior
        for s in np.arange(0, ring.length, 1.5):
            p = ring.interpolate(s)
            if W.excl0.contains(p) or not occ_near(W, p.buffer(1.2)).is_empty:
                continue
            W.add_tree('bush', p.x, p.y, 1.5)
            k += 1
            if int(s / 1.5) % 8 == 0:
                p2 = Point(p.x + (q.centroid.x - p.x) * 0.06, p.y + (q.centroid.y - p.y) * 0.06)
                W.add_tree('cypress', p2.x, p2.y, float(rng.uniform(7, 9)))
            if int(s / 1.5) % 14 == 7:
                W.add_prop('prop/lamp_iron', p.x, p.y, 0, foot=(0.35, 0.35), tag='lamp', cast=False)
    items['palace_hedge_bushes'] = k
    # Rest of the island: pine clumps.
    zone2 = zone_of(W, Tb.buffer(-5).difference(base.buffer(4)).difference(lawn.buffer(2)), 2.5)

    def place2(part, pt, r, k):
        n0 = len(W.trees)
        g = tree_disc(W, part, pt, max(2.0, min(r - 1, 10)), 5.0, ['pine', 'pine', 'birch'], (10, 16), rng_for(f'tram2{k}'), under=0.3)
        items['trees'] += len(W.trees) - n0
        return g
    greedy_fill(zone2, place2, 6.0)
    dev(f"Tramduro: {items['vehicles']} military trucks (vehicle park and yard), {items['watch_towers']} more watch towers inside the fence corners, "
        f"{items['tents']} army tents, {items['concrete_barriers']} concrete barrier blocks, {items['trees']} trees, palace lawn hedge/cypress/lamps; helipad clear.")
    return dict(items)


# ---------------------------------------------------------------- elite hill, beach, forest, fields
def elite(W, d):
    rng = rng_for('elite')
    items = collections.Counter()
    E = W.boxes['elite']
    ring = largest(valid(Polygon(next(f for f in d['fences'] if f['id'] == '07_fence')['polyline_m'])))
    keep = unary_union([keep_open(d, 'elite', ('golden_statue_on_round_plaza', 'lookout_terrace'), 4.0),
                        unary_union([Point(s['position_m']).buffer(10) for s in d['structures'] if s['id'] in ('07_07_statue', '07_08_lookout') and s.get('position_m')])])
    # Existing villa gardens: hedge ring (gap toward the drive), cypress, loungers by the pools, garden bollards.
    for s in [s for s in d['structures'] if s['district_id'] == 'elite' and s['kind'] == 'villa_garden']:
        g = orient(valid(Polygon(s['polygon_m'])), 1)
        dr, _ = toward_road(W, g.centroid)
        gap = Point(g.centroid.x + dr[0] * 100, g.centroid.y + dr[1] * 100)
        ring_g = g.buffer(-0.8).exterior
        gap_s = ring_g.project(gap)
        for s_ in np.arange(0, ring_g.length, 1.3):
            if min(abs(s_ - gap_s), ring_g.length - abs(s_ - gap_s)) < 3.5:
                continue
            p = ring_g.interpolate(s_)
            if W.excl0.contains(p) or not occ_near(W, p.buffer(0.9)).is_empty:
                continue
            W.add_tree('bush', p.x, p.y, float(rng.uniform(1.8, 2.3)))
            items['hedge_bushes'] += 1
            if int(s_ / 1.3) % 7 == 3:
                W.add_tree('cypress', p.x, p.y, float(rng.uniform(7, 10)))
        items['gardens_hedged'] += 1
    for w in [w for w in d['water'] if w['kind'] == 'swimming_pool' and w['district_id'] == 'elite']:
        g = valid(Polygon(w['polygon_m']))
        u = edge_dir_near(g, g.centroid)
        mrr = g.minimum_rotated_rectangle
        c = list(mrr.exterior.coords)
        long_e = max(((c[1][0] - c[0][0], c[1][1] - c[0][1]), (c[2][0] - c[1][0], c[2][1] - c[1][1])), key=lambda e: math.hypot(*e))
        Le = math.hypot(*long_e)
        u = (long_e[0] / Le, long_e[1] / Le)
        v = side(u)
        for sgn in (1, -1):
            for i in range(3):
                x = g.centroid.x + v[0] * sgn * (min_dim(g)[0] / 2 + 1.8) + u[0] * (i - 1) * 2.2
                y = g.centroid.y + v[1] * sgn * (min_dim(g)[0] / 2 + 1.8) + u[1] * (i - 1) * 2.2
                if occ_near(W, Point(x, y).buffer(0.9)).is_empty and not W.excl0.contains(Point(x, y)):
                    W.add_prop('prop/beach_sunlounger', x, y, unity_yaw(-v[0] * sgn, -v[1] * sgn), foot=(0.8, 2.0), tag='lounger')
                    items['pool_loungers'] += 1
            break
    # New villas on the free slope inside the elite ring: villa 2 floors, pool, lawn, hedge ring, cypress, bollards, a car.
    zone = zone_of(W, ring.buffer(-4.0).intersection(E.buffer(-4)), 3.0, extra=(keep,))
    st = dict(v=0, k=0)

    def place(part, pt, r, k):
        rr = rng_for(f'elite{k}')
        u, dist = toward_road(W, pt)
        dims = fit_dims(r, 36.0, 28.0, 24.0)
        if st['v'] < 4 and dims and dist < 60:
            v = side(u)
            plot = orect(pt.x, pt.y, v[0], v[1], *dims)
            if not part.buffer(0.3).contains(plot):
                return pt.buffer(min(r, 6))
            st['v'] += 1
            vid = f'07_v18_villa_{st["v"]}'
            hc = (pt.x + u[0] * 4.0, pt.y + u[1] * 4.0)
            hg = orect(hc[0], hc[1], v[0], v[1], float(rr.uniform(15, 19)), float(rr.uniform(10, 12)))
            door = (hc[0] + u[0] * 5.5, hc[1] + u[1] * 5.5)
            bld(W, vid, 'elite', 'modern_villa', 'mansion', hg, 2, 3.2, 3.0, [door], recipe='villa_v18', label='villa (v18)')
            pc = (pt.x - u[0] * 9.0 + v[0] * 3.0, pt.y - u[1] * 9.0 + v[1] * 3.0)
            pg = orect(pc[0], pc[1], v[0], v[1], 10.0, 4.5)
            pool(W, d, f'{vid}_pool', 'elite', pg)
            W.add_pad(plot.buffer(-1.2).difference(hg.buffer(0.5)).difference(pg.buffer(0.3)), 'lawn', 'v18_villa_garden', prio=33)
            W.add_pad(pg.buffer(1.6).difference(pg), 'paving', 'v18_pool_deck', prio=39)
            for i in range(3):
                W.add_prop('prop/beach_sunlounger', pc[0] - u[0] * 3.4 + v[0] * (i - 1) * 2.2, pc[1] - u[1] * 3.4 + v[1] * (i - 1) * 2.2, unity_yaw(*u), foot=(0.8, 2.0), tag='lounger')
            gate_p = Point(pt.x + u[0] * plot_w(plot, u) / 2, pt.y + u[1] * plot_w(plot, u) / 2)
            ringp = orient(plot.buffer(-0.6), 1).exterior
            gs = ringp.project(gate_p)
            for s_ in np.arange(0, ringp.length, 1.3):
                if min(abs(s_ - gs), ringp.length - abs(s_ - gs)) < 3.5:
                    continue
                p = ringp.interpolate(s_)
                W.add_tree('bush', p.x, p.y, float(rr.uniform(1.8, 2.4)))
                if int(s_ / 1.3) % 6 == 2:
                    W.add_tree('cypress', p.x, p.y, float(rr.uniform(7, 10)))
            for sgn in (-1, 1):
                W.add_prop('prop/lamp_bollard', gate_p.x + v[0] * sgn * 2.4 - u[0] * 1.0, gate_p.y + v[1] * sgn * 2.4 - u[1] * 1.0, 0, solid=False, cast=False)
            W.add_prop('prop/car_sedan_blue' if st['v'] % 2 else 'prop/car_sedan_red', pt.x + u[0] * 11.5 - v[0] * 9, pt.y + u[1] * 11.5 - v[1] * 9, unity_yaw(*u), foot=CAR, tag='car')
            items['villas'] += 1
            return plot.buffer(3.0)
        st['k'] += 1
        n0 = len(W.trees)
        sp = ['oak', 'linden', 'cypress', 'oak', 'palm'] if st['k'] % 3 else ['cypress', 'cypress', 'linden']
        g = tree_disc(W, part, pt, max(2.0, min(r - 1, 8)), 5.5, sp, (8, 13), rr, under=0.35)
        items['park_trees'] += len(W.trees) - n0
        return g
    greedy_fill(zone, place, 7.0)
    zone2 = zone_of(W, E.buffer(-4).difference(ring.buffer(3.0)), 2.5, extra=(keep, W.sand.buffer(2)))

    def place2(part, pt, r, k):
        n0 = len(W.trees)
        g = tree_disc(W, part, pt, max(2.0, min(r - 1, 8)), 5.0, ['pine', 'cypress', 'oak', 'pine'], (8, 13), rng_for(f'elite2{k}'), under=0.4)
        items['slope_trees'] += len(W.trees) - n0
        return g
    greedy_fill(zone2, place2, 7.0)
    dev(f"Elite hill: {items['villas']} new villas (2 floors) with pool, lawn, hedge ring, cypress, bollards and a car; {items['gardens_hedged']} existing "
        f"gardens hedged, {items['pool_loungers']} loungers by the existing pools, {items['park_trees']} park trees; statue plaza and lookout clear; "
        "the elite ring fence is Vadim's and untouched.")
    return dict(items)


def plot_w(plot, u):
    c = list(plot.exterior.coords)
    return max(abs((q[0] - plot.centroid.x) * u[0] + (q[1] - plot.centroid.y) * u[1]) for q in c) * 2


def beach(W, d):
    rng = rng_for('beach')
    items = collections.Counter()
    B = W.boxes['beach']
    sand = W.sand.intersection(B.buffer(-2))
    sea = unary_union([m16.water_geometry(w) for w in d['water'] if w['kind'] == 'sea'])
    promenade = unary_union([LineString(r['polyline_m']) for r in d['paths'] if r['id'].startswith('09_path')])
    zone = zone_of(W, sand, 1.5, extra=(sea.buffer(4.0),))
    towers = []
    # Lifeguard towers every ~70 m along the waterline, 9 m up the beach.
    shore = sea.boundary.intersection(B.buffer(12)).intersection(W.sand.buffer(3))
    for q in parts(shore, 'LineString'):
        for s in np.arange(25, q.length, 70):
            p = q.interpolate(s)
            for off in (9, 12, 15):
                # step inland (away from the sea)
                c = None
                for ang in range(0, 360, 30):
                    t = Point(p.x + off * math.cos(math.radians(ang)), p.y + off * math.sin(math.radians(ang)))
                    if zone.contains(t.buffer(1.6)) and sea.distance(t) > off - 2:
                        c = t
                        break
                if c is not None:
                    break
            if c is None or any(c.distance(t) < 50 for t in towers):
                continue
            W.add_prop('prop/beach_lifeguard_tower', c.x, c.y, unity_yaw(p.x - c.x, p.y - c.y), foot=(2.4, 2.4), tag='lifeguard')
            towers.append(c)
            items['lifeguard_towers'] += 1
    zone = zone.difference(unary_union([t.buffer(6) for t in towers]) if towers else Polygon())
    st = dict(k=0, kiosk=0)

    def place(part, pt, r, k):
        rr = rng_for(f'beach{k}')
        u = edge_dir_near(part, pt)
        near_prom = promenade.distance(pt) < 14
        st['k'] += 1
        if near_prom and st['kiosk'] < 8 and r >= 3.5 and st['k'] % 3 == 0:
            W.add_prop('prop/kiosk' if st['kiosk'] % 2 else 'prop/news_kiosk', pt.x, pt.y, unity_yaw(*u), foot=(2.8, 3.0), tag='kiosk')
            W.add_prop('prop/bin', pt.x + u[0] * 2.4, pt.y + u[1] * 2.4, 0, foot=(0.5, 0.5), tag='bin', cast=False)
            st['kiosk'] += 1
            items['kiosks'] += 1
            return pt.buffer(5.0)
        if r >= 2.6:
            # umbrella with two loungers
            W.add_prop('prop/beach_umbrella_red' if (k % 2) else 'prop/beach_umbrella_teal', pt.x, pt.y, 0, foot=(0.3, 0.3), tag='umbrella')
            for sgn in (-1, 1):
                W.add_prop('prop/beach_sunlounger', pt.x + side(u)[0] * sgn * 1.1, pt.y + side(u)[1] * sgn * 1.1, unity_yaw(*u), foot=(0.8, 2.0), tag='lounger')
            items['umbrella_sets'] += 1
            return pt.buffer(3.8)
        return pt.buffer(min(r, 2.5))
    greedy_fill(zone, place, 4.0, max_items=260)
    # Palms along the back of the beach (land side of the sand, clear of paths and points).
    back = W.sand.intersection(B).boundary.difference(sea.buffer(30))
    for q in parts(back, 'LineString'):
        for s in np.arange(4, q.length, 11):
            p = q.interpolate(s)
            if W.excl0.contains(p) or not occ_near(W, p.buffer(2.0)).is_empty or not W.land.contains(p):
                continue
            W.add_tree('palm', p.x, p.y, float(rng.uniform(7, 10)))
            items['palms'] += 1
    dev(f"Beach: {items['lifeguard_towers']} lifeguard towers along the waterline, {items['umbrella_sets']} umbrella + 2 lounger sets, {items['kiosks']} kiosks by the "
        f"paths, {items['palms']} palms at the back of the sand; the paths, the pier and the canal footbridges stay clear.")
    return dict(items)


def forest(W, d):
    rng = rng_for('forest')
    items = collections.Counter()
    F = W.boxes['forest']
    zones = [(valid(Polygon(z['polygon_m'])), z['density']) for z in d['vegetation_hints']['forest_zones']]
    wood = unary_union([g for g, dn in zones]).intersection(F.buffer(-3)).intersection(W.land)
    # Clearings at the forest POIs (campfire, hills, lake shore, railway end) and two more in the deepest forest.
    clear_pts = [(209.2, 157.0, 11), (275.4, 137.0, 10), (282.4, 232.0, 9), (151.6, 150.0, 8), (230.0, 230.0, 12), (300.0, 280.0, 10)]
    clears = []
    for i, (x, y, r) in enumerate(clear_pts):
        c = Point(x, y)
        g = c.buffer(r, 12).difference(W.corridor.buffer(1.0)).difference(W.water.buffer(1.0))
        g = largest(g)
        if g is None:
            continue
        clears.append(g)
        W.clear_zones.append(g)
        W.add_pad(g.buffer(-1.0), 'worn_grass', 'v18_forest_clearing', prio=22)
        for j in range(3):
            a = rng.uniform(0, 2 * math.pi)
            p = Point(x + (r - 3) * math.cos(a), y + (r - 3) * math.sin(a))
            if g.buffer(-1).contains(p) and W.excl0.distance(p) > 1.5:
                W.add_prop('prop/log_bench', p.x, p.y, R(math.degrees(a)), foot=(0.6, 2.4), tag='woodpile')
                items['log_piles'] += 1
        for j in range(4):
            a = rng.uniform(0, 2 * math.pi)
            p = Point(x + (r - 1.5) * math.cos(a), y + (r - 1.5) * math.sin(a))
            if g.contains(p) and W.excl0.distance(p) > 1.5:
                W.add_prop(f'prop/rock_0{1 + j % 5}', p.x, p.y, R(math.degrees(a)), foot=(0.8, 0.8), tag='stump', scale=0.5)
                items['stumps'] += 1
        items['clearings'] += 1
    # Trails: 1.6 m worn paths between the forest POIs and the roads (ground decal only; no graph change).
    pois = [Point(p['position_m']) for p in d['points'] if p['district_id'] == 'forest' and p['category'] == 'numbered_poi']
    trails = []
    for i, a in enumerate(pois):
        b = min((q for q in pois if q is not a), key=lambda q: a.distance(q))
        key = tuple(sorted([(a.x, a.y), (b.x, b.y)]))
        if key in [t[0] for t in trails] or a.distance(b) > 90:
            continue
        mid = Point((a.x + b.x) / 2 + rng.uniform(-6, 6), (a.y + b.y) / 2 + rng.uniform(-6, 6))
        ln = LineString([a, mid, b]).simplify(0)
        g = ln.buffer(0.8, cap_style=1).difference(W.water.buffer(1)).difference(W.corridor)
        trails.append((key, g))
        W.add_pad(g, 'worn_grass', 'v18_forest_trail', prio=23)
        W.clear_zones.append(ln.buffer(1.6))
        items['trails'] += 1
    # Light forest gets denser: extra pine/birch clumps in its open gaps.
    zone = zone_of(W, F.buffer(-4), 2.0, extra=(unary_union(clears).buffer(2) if clears else Polygon(), unary_union([t[1] for t in trails]).buffer(1.5) if trails else Polygon()))
    dense = unary_union([g for g, dn in zones if dn == 'dense'])
    zone = zone.difference(dense)

    def place(part, pt, r, k):
        n0 = len(W.trees)
        g = tree_disc(W, part, pt, max(2.0, min(r - 1, 10)), 4.6, ['pine', 'pine', 'birch', 'spruce'], (10, 16), rng_for(f'forest{k}'), under=0.4)
        items['clump_trees'] += len(W.trees) - n0
        return g
    greedy_fill(zone, place, 8.0)
    # Undergrowth under the scatter forest: bushes and young spruce on a jittered grid.
    blocked = unary_union([W.corridor.buffer(1.5), W.water.buffer(1.5), unary_union(clears) if clears else Polygon(), unary_union([t[1] for t in trails]).buffer(1.0) if trails else Polygon(),
                           occ_near(W, F, 2.0), W.excl0])
    for g, dn in zones:
        part = g.intersection(F.buffer(-3)).intersection(W.land).difference(blocked)
        if part.is_empty:
            continue
        step = 6.0 if dn == 'dense' else 9.0
        x0, y0, x1, y1 = part.bounds
        for y in np.arange(y0, y1, step):
            for x in np.arange(x0, x1, step):
                px, py = x + rng.uniform(-2, 2), y + rng.uniform(-2, 2)
                if not part.contains(Point(px, py)):
                    continue
                if rng.random() < 0.72:
                    W.add_tree('bush', px, py, float(rng.uniform(1.4, 2.6)))
                    items['undergrowth_bushes'] += 1
                else:
                    W.add_tree('spruce', px, py, float(rng.uniform(3.0, 6.0)))
                    items['young_spruce'] += 1
    dev(f"Forest: {items['undergrowth_bushes']} undergrowth bushes and {items['young_spruce']} young spruces under the canopy, {items['clearings']} clearings "
        f"(worn grass, {items['log_piles']} log piles, {items['stumps']} stumps), {items['trails']} worn trails between the forest POIs (ground only, "
        f"no new graph edges), {items['clump_trees']} more trees in the light forest.")
    return dict(items)


def fields_district(W, d):
    rng = rng_for('fields')
    items = collections.Counter()
    Fd = W.boxes['fields']
    keep = keep_open(d, 'fields', ('paved_forecourt', 'parking', 'rock_waterfall'), 3.0)
    zone = zone_of(W, Fd.buffer(-5), 2.5, extra=(keep,))
    st = dict(k=0)

    def place(part, pt, r, k):
        rr = rng_for(f'fields{k}')
        u = edge_dir_near(part, pt)
        st['k'] += 1
        ch = ['parcel', 'hedgerow', 'orchard', 'parcel', 'haystacks', 'hedgerow'][st['k'] % 6]
        if ch == 'parcel' and r >= 9:
            g = orect(pt.x, pt.y, u[0], u[1], 2 * r - 3, min(2 * r - 3, 18))
            g = g.intersection(part)
            W.add_pad(g.buffer(-0.5), 'dry_field', 'v18_crop_parcel', prio=31)
            for sgn in (-1, 1):
                a = (pt.x + side(u)[0] * sgn * (min(r, 10.5) - 0.5) - u[0] * (r - 2), pt.y + side(u)[1] * sgn * (min(r, 10.5) - 0.5) - u[1] * (r - 2))
                b = (a[0] + u[0] * (2 * r - 4), a[1] + u[1] * (2 * r - 4))
                hedge_line(W, a, b, 1.5, (1.6, 2.4), rr)
            if rr.random() < 0.5:
                W.add_prop('prop/tractor_small', pt.x, pt.y, unity_yaw(*u), foot=(1.8, 3.4), tag='tractor')
                items['tractors'] += 1
            items['crop_parcels'] += 1
            return g.buffer(1.5)
        if ch == 'hedgerow' and r >= 7:
            a = (pt.x - u[0] * (r - 1), pt.y - u[1] * (r - 1))
            b = (pt.x + u[0] * (r - 1), pt.y + u[1] * (r - 1))
            hedge_line(W, a, b, 1.5, (1.8, 2.6), rr)
            for t in np.arange(2, 2 * r - 2, 8):
                W.add_tree(['oak', 'poplar', 'linden'][int(rr.integers(3))], a[0] + u[0] * t, a[1] + u[1] * t, float(rr.uniform(10, 14)))
            items['hedgerows'] += 1
            return LineString([a, b]).buffer(4.5)
        if ch == 'haystacks' and r >= 5:
            for j in range(3):
                structure(W, d, f'08_v18_hay_{k}_{j}', 'fields', 'haystack', position_m=[R(pt.x + (j - 1) * 4.8), R(pt.y + (j % 2) * 3.2)], radius_m=2.1)
            items['haystacks'] += 3
            return pt.buffer(7.5)
        n0 = len(W.trees)
        g = tree_disc(W, part, pt, max(2.0, min(r - 1, 8)), 5.0, ['fruit', 'fruit', 'oak', 'poplar'], (5, 11), rr, under=0.2)
        items['orchard_trees'] += len(W.trees) - n0
        return g
    greedy_fill(zone, place, 7.5)
    dev(f"Fields: {items['crop_parcels']} crop parcels with hedges, {items['hedgerows']} hedgerows, {items['haystacks']} haystacks, {items['tractors']} tractors, "
        f"{items['orchard_trees']} orchard/field trees; lab forecourt, casino parking and the waterfall stay clear.")
    return dict(items)


# ---------------------------------------------------------------- common land everywhere
PYLON_LINES = [[(548, 505), (480, 525), (450, 580), (440, 660), (446, 730)],          # west: on from v17's line, east of the river, north
               [(640, 244), (600, 214), (572, 170), (566, 120)],                       # south-west: Downtown -> past the Fields
               [(1128, 500), (1138, 470), (1145, 420), (1140, 380), (1135, 320), (1130, 262)]]  # east: on from v17's line past the elite gate


def common_land(W, d):
    rng = rng_for('common')
    items = collections.Counter()
    others = unary_union([bx.buffer(6) for bx in W.boxes.values()])
    dense = unary_union([valid(Polygon(z['polygon_m'])) for z in d['vegetation_hints']['forest_zones'] if z['density'] == 'dense'])
    struct = unary_union([valid(Polygon(s['polygon_m'])).buffer(3) for s in d['structures'] if s.get('polygon_m') and len(s['polygon_m']) >= 3])
    mountain = valid(Polygon(d['terrain_hints']['small_mountain']['outline_m']))
    base_excl = unary_union([others, W.water.buffer(7), W.sand.buffer(5), W.decks.buffer(10), W.ridge.buffer(4), struct, W.excl0])
    region = W.land.buffer(-6)
    roads = [(r, l) for r, l in W.roads if r['district_id'] == 'common' and r['van_access'] and not r['id'].startswith('DECK')]
    v17box = m17.COMMON
    # 1. Tree tunnels and billboards on the inter-district roads outside v17's box (v17 dressed the ones inside it).
    for r, l in roads:
        for sd in (1, -1):
            for j, (x, y, ux, uy) in enumerate(offset_points(l, sd * (r['width_m'] / 2 + 4.2), 8.5, 4.0 + rng.uniform(0, 3))):
                p = Point(x, y)
                if v17box.contains(p) or not region.contains(p) or base_excl.contains(p) or dense.contains(p) or any(p.distance(n) < 18 for n in W.nodes) or W.corridor.buffer(3.0).contains(p):
                    continue
                W.add_tree(['birch', 'poplar', 'linden', 'birch', 'oak'][int(rng.integers(5))], x, y, float(rng.uniform(10, 15)))
                W.tunnel[id(W.trees[-1])] = (r['id'], sd, j)
                items['tunnel_trees'] += 1
        s, sd = 60.0, 1
        while s < l.length - 40:
            c, q = l.interpolate(s), l.interpolate(s + 1)
            ux, uy = q.x - c.x, q.y - c.y
            L = math.hypot(ux, uy) or 1
            nx, ny = -uy / L * sd, ux / L * sd
            x, y = c.x + nx * (r['width_m'] / 2 + 9), c.y + ny * (r['width_m'] / 2 + 9)
            p = Point(x, y)
            if not v17box.contains(p) and region.contains(p) and not base_excl.contains(p) and W.corridor.buffer(4).disjoint(p.buffer(3)) and occ_near(W, p.buffer(4)).is_empty:
                W.add_prop('prop/billboard_large', x, y, unity_yaw(-nx, -ny), foot=(1.0, 6.0), tag='billboard')
                items['billboards'] += 1
            s += 160
            sd = -sd
    # 2. Power lines (lattice pylons every ~55 m; the Unity builder strings wires between consecutive pylons < 90 m apart).
    pylons = []
    for line in PYLON_LINES:
        ln = LineString(line)
        s = 0.0
        while s < ln.length:
            p, q = ln.interpolate(s), ln.interpolate(min(ln.length, s + 1))
            why = ('outside_land' if not region.contains(p) else 'district' if others.contains(p) else 'water' if W.water.buffer(6).contains(p) else
                   'road' if not W.corridor.buffer(6).disjoint(p) else 'occupied' if not occ_near(W, p.buffer(5.5)).is_empty else 'point' if W.excl0.contains(p) else '')
            items['pylon_skip_' + (why or 'none')] += 1
            if not why:
                W.add_prop('proc/pylon', p.x, p.y, unity_yaw((q.x - p.x) or 1e-6, q.y - p.y), foot=(5.5, 5.5), tag='pylon')
                pylons.append([R(p.x), R(p.y)])
                items['pylons'] += 1
            s += 55
    # 3. Rooms: farmsteads, garage cooperatives, dacha allotments, hedgerows and forest belts with undergrowth.
    zone = region.difference(base_excl).difference(W.corridor.buffer(4.5)).difference(dense)
    zone = zone.difference(occ_near(W, zone.envelope, 3.0)).difference(trees_near(W, zone.envelope, 3.5))
    near_road = W.carriage.buffer(150)
    st = dict(farm=0, coop=0, allot=0)

    def place(part, pt, r, k):
        rr = rng_for(f'cl{k}')
        u = edge_dir_near(part, pt)
        dr, road_d = toward_road(W, pt)
        dv = min(W.boxes['village'].distance(pt), W.boxes['fields'].distance(pt))
        dres = min(W.boxes[q].distance(pt) for q in ('residential', 'old_town', 'industrial', 'transition'))
        dims = fit_dims(r, 40.0, 32.0, 34.0)
        if st['farm'] < 4 and dims and dv < 230 and road_d < 60:
            L, Wd = dims
            plot = orect(pt.x, pt.y, -dr[1], dr[0], L, Wd)
            if part.buffer(0.3).contains(plot):
                st['farm'] += 1
                farm_plot(W, d, f'CL_v18_farm_{st["farm"]}', 'village', pt, dr, L, Wd, rr, items, beds=False, hay=False, barn=True, zone='common')
                for j in range(3):
                    hx = pt.x - dr[0] * (Wd / 2 + 4) + (-dr[1]) * (j - 1) * 5.0
                    hy = pt.y - dr[1] * (Wd / 2 + 4) + dr[0] * (j - 1) * 5.0
                    if part.contains(Point(hx, hy).buffer(2.2)):
                        structure(W, d, f'CL_v18_farm_{st["farm"]}_hay_{j}', 'village', 'haystack', position_m=[R(hx), R(hy)], radius_m=2.1)
                        items['haystacks'] += 1
                items['farmsteads'] += 1
                return plot.buffer(9.0)
        dist = 'village' if dv < dres else 'residential'          # as v17: common-land properties carry a neighbour district id
        if st['coop'] < 2 and r >= 26.5 and dres < 160 and road_d < 70:
            g = orect(pt.x, pt.y, u[0], u[1], 42, 34)
            if part.buffer(0.3).contains(g):
                st['coop'] += 1
                for j, off in enumerate((-12.5, 12.5)):
                    row = orect(pt.x - u[1] * off, pt.y + u[0] * off, u[0], u[1], 12 * 3.2, 6.2)
                    bld(W, f'CL_v18_garage_coop_{st["coop"]}_{j + 1}', 'residential', 'v17_garage', 'metal_garage_row', row, 1, GARAGE_H, GARAGE_H,
                        [(pt.x - u[1] * off * 0.55, pt.y + u[0] * off * 0.55)], zone='common', recipe='garage_cooperative')
                W.add_pad(orect(pt.x, pt.y, u[0], u[1], 38, 18), 'gravel', 'v18_garage_coop_lane')
                gate = g.exterior.interpolate(g.exterior.project(Point(pt.x + dr[0] * road_d, pt.y + dr[1] * road_d)))
                fence(W, f'CL_v18_garage_coop_{st["coop"]}_fence', 'fence_chainlink', list(orient(g, 1).exterior.coords), 'residential', 2.2, gates=[(gate.x, gate.y, 5.0)], closed=True)
                for j in range(3):
                    W.add_prop(car_keys(True)[int(rr.integers(7))], pt.x + u[0] * (j * 9 - 9), pt.y + u[1] * (j * 9 - 9), unity_yaw(*u), foot=CAR, tag='car')
                items['garage_coops'] += 1
                return g.buffer(3)
        if st['allot'] < 4 and r >= 20 and (dv < 200 or dres < 200):
            st['allot'] += 1
            used = []
            for i in range(3):
                for j in range(2):
                    cx = pt.x + u[0] * (i - 1) * 15.0 - u[1] * (j - 0.5) * 19.0
                    cy = pt.y + u[1] * (i - 1) * 15.0 + u[0] * (j - 0.5) * 19.0
                    plot = orect(cx, cy, u[0], u[1], 14.2, 18.2)
                    if not part.contains(plot):
                        continue
                    gate = plot.exterior.interpolate(0.06, normalized=True)
                    fence(W, f'CL_v18_allotment_{st["allot"]}_{i}{j}', 'fence_dacha', list(orient(plot, 1).exterior.coords), dist, 1.3, gates=[(gate.x, gate.y, 1.2)], closed=True)
                    shed = orect(cx + u[0] * 4.0 + u[1] * 5.5, cy + u[1] * 4.0 - u[0] * 5.5, u[0], u[1], 4.2, 3.4)
                    bld(W, f'CL_v18_dacha_{st["allot"]}_{i}{j}', dist, 'v17_dacha', 'shed', shed, 1, 2.6, 2.6,
                        [(shed.centroid.x - u[1] * 1.7, shed.centroid.y + u[0] * 1.7)], roof='gable', zone='common', recipe='allotment_dacha')
                    W.add_pad(orect(cx - u[0] * 2.5 - u[1] * 2.0, cy - u[1] * 2.5 + u[0] * 2.0, u[0], u[1], 7.5, 9.0), 'dry_field', 'v18_allotment_beds')
                    for t in range(2):
                        W.add_tree('fruit', cx - u[0] * 4.5 + u[1] * (t * 6 - 3), cy - u[1] * 4.5 - u[0] * (t * 6 - 3), float(rr.uniform(4.5, 6)))
                    W.clear_zones.append(plot)
                    used.append(plot)
            if used:
                items['allotment_plots'] += len(used)
                return unary_union(used).buffer(3)
        if r >= 26 and k % 3 == 0:
            L = 2 * r - 8
            for s in np.arange(-L / 2, L / 2, 3.2):
                x, y = pt.x + u[0] * s, pt.y + u[1] * s
                if part.contains(Point(x, y)):
                    big = int(s) % 3 == 0
                    W.add_tree(['oak', 'birch', 'linden'][int(rr.integers(3))] if big else 'bush', x, y, float(rr.uniform(9, 13)) if big else float(rr.uniform(1.6, 2.6)))
            items['hedgerows'] += 1
            return orect(pt.x, pt.y, u[0], u[1], L, 10).intersection(part)
        rc = min(r * 0.7, 22.0)
        sp = ['pine', 'pine', 'birch', 'spruce', 'birch'] if pt.y > 470 or pt.x < 420 else ['birch', 'oak', 'linden', 'pine', 'poplar']
        items['forest_clumps'] += 1
        g = tree_disc(W, part, pt, max(rc, 4.0), 4.6, sp, (10, 17), rr, under=0.4)
        if g is not None:
            W.add_pad(g.buffer(-1.0), 'forest_floor', 'v18_forest_floor', prio=20)
        return g

    greedy_fill(zone.intersection(near_road), place, 14.0)
    zone2 = zone.difference(near_road).difference(occ_near(W, zone.envelope, 3.0)).difference(trees_near(W, zone.envelope, 3.5, start=W.v18_trees_from))
    greedy_fill(zone2, place, 28.0)
    dev(f"Common land (whole map): {items['tunnel_trees']} tree-tunnel trees and {items['billboards']} billboards on the inter-district roads outside v17's box, "
        f"{items['pylons']} more pylons on 3 power lines, {items['farmsteads']} farmsteads (fenced yard, 6-10 m house, barn, shed, orchard, well, haystacks), "
        f"{items['garage_coops']} garage cooperatives, {items['allotment_plots']} dacha plots, {items['hedgerows']} hedgerows, {items['forest_clumps']} forest belts/clumps "
        "with undergrowth. No fence within 4 m of any district outline (hedges there instead).")
    return dict(items), pylons


# ---------------------------------------------------------------- relief 3-15 m and the grade fixes
def relief(W, d, T):
    """Hills/ridges of 3-15 m over all the common land, a cos falloff that ends before every district envelope (+12 m),
    away from water/coast/bridges/junctions and new buildings; a hill is kept only if every road near it stays <= 7.5 %
    in the HeightModel port, or no steeper than before for a road that is already steeper (fixed afterwards by grade_fix)."""
    rng = rng_for('relief')
    others = unary_union([bx.buffer(12) for bx in W.boxes.values()])
    old = unary_union([Point(h['center_m']).buffer(max(h['radii_m']) * 0.9) for h in d['hills']])
    solids = unary_union([g for g, t in W.solid if t in ('building', 'fence')])
    excl = unary_union([others, W.water.buffer(14), W.sand.buffer(10), W.decks.buffer(25), old.buffer(-6), solids.buffer(5),
                        unary_union([n.buffer(16) for n in W.nodes]), W.land.exterior.buffer(14), W.ridge.buffer(8)])
    allowed = W.land.difference(excl)
    look_roads = {r['id']: r for r in T.look['roads'] if len(r['pts']) >= 4}
    road_lines = {k: LineString(np.array(r['pts']).reshape(-1, 2)) for k, r in look_roads.items()}
    hills, rejected, tried = [], 0, 0
    g0 = {k: v['max'] for k, v in T.grades().items()}
    for j in range(34):
        for i in range(62):
            x = 15 + i * 24 + rng.uniform(-7, 7)
            y = 8 + j * 24 + rng.uniform(-7, 7)
            p = Point(x, y)
            if not allowed.contains(p):
                continue
            tried += 1
            room = allowed.boundary.distance(p)
            if any(math.dist((x, y), h['center_m']) < 0.55 * (max(h['radii_m']) + min(room, 75)) for h in hills):
                continue
            rx = min(room, rng.uniform(22, 75))
            if rx < 11:
                continue
            ry = rx * rng.uniform(0.45, 0.9)
            if rng.random() < 0.5:
                rx, ry = ry, rx
            hgt = R(rng.uniform(3, 15) * min(1.0, max(rx, ry) / 45))
            if hgt < 3:
                continue
            h = dict(center_m=[R(x), R(y)], radii_m=[R(rx), R(ry)], rotation_deg=0, height_m=hgt, height_target_m=hgt,
                     note='v18 relief (common land; cos falloff ends before the district envelopes)', id=f'V18_RELIEF_{len(hills) + 1:02d}')
            T.add(h)
            near = [k for k, l in road_lines.items() if l.distance(p) < max(rx, ry) + 30]
            g = T.grades(set(near)) if near else {}
            if any(v['max'] > max(0.075, g0[k] + 0.001) for k, v in g.items()):
                T.remove(h)
                rejected += 1
                continue
            hills.append(h)
    d['hills'] += hills
    dev(f'{len(hills)} relief hills/ridges (3-15 m, radii 11-75 m) added over the common land of the whole map; none reaches a district envelope '
        f'(+12 m), water, coast, bridge or junction; {tried} grid candidates on allowed ground, {rejected} dropped because a nearby road would exceed 7.5 % (HeightModel port).')
    return hills


def grade_fix(W, d, T, road_ids, tag):
    """Reshape the terrain (never the road): least-squares 'embankment' (+) and 'cutting' (-) bumps of radius 13 m along the
    road so its smoothed, pinned profile already meets the grade target before Unity's 40-pass relaxation runs."""
    look_roads = {r['id']: r for r in T.look['roads']}
    out = {}
    for rid in road_ids:
        r = look_roads[rid]
        before = T.profile(r)['max']
        added = []
        for it in range(5):
            pr = T.profile(r)
            if pr['max'] <= 0.077:
                break
            tgt = T.profile(r, passes=20000, grade=0.068)['h']
            s, xy, base = pr['s'], pr['xy'], pr['base']
            cand = []
            for k in range(0, len(s), 3):
                cand.append(dict(center_m=[R(xy[k, 0]), R(xy[k, 1])], radii_m=[13.0, 13.0], rotation_deg=0, height_m=1.0, height_target_m=1.0))
            A = np.zeros((len(s), len(cand)))
            for j, h in enumerate(cand):
                T.add(h)
                A[:, j] = T.profile(r, passes=0)['base'] - base
                T.remove(h)
            lam = 0.02
            x = np.linalg.solve(A.T @ A + lam * np.eye(len(cand)), A.T @ (tgt - base))
            for h, v in zip(cand, x):
                if abs(v) < 0.05:
                    continue
                v = R(float(np.clip(v, -9, 9)))
                h = dict(h, height_m=v, height_target_m=v, id=f'V18_GRADE_{tag}_{rid}_{len(added) + 1:02d}',
                         note=('v18 grade fix: embankment' if v > 0 else 'v18 grade fix: cutting') + f' under road {rid} (terrain only, road unchanged)')
                T.add(h)
                added.append(h)
        d['hills'] += added
        out[rid] = dict(before=R(before * 100), after=R(T.profile(r)['max'] * 100), bumps=len(added))
    return out


# ---------------------------------------------------------------- metrics: sightline proxy and empty-lawn circles
RES = 0.5          # raster metres per cell
EYE = 1.7


def crown_r(t):
    if t['sp'] == 'bush':
        return 1.0 if t['h'] >= EYE else 0.0
    return float(np.clip(0.24 * t['h'], 1.6, 3.2))


def obstacle_raster(buildings, trees, fences, props):
    """1 = blocks a 1.7 m eye: building footprints, tree crowns (bushes >= 1.7 m), opaque fences, tall props."""
    W_, H_ = int(1474 / RES), int(760 / RES)
    im = Image.new('1', (W_, H_), 0)
    dr = ImageDraw.Draw(im)
    P = lambda x, y: (x / RES, (760 - y) / RES)
    for g in buildings:
        for q in parts(g):
            dr.polygon([P(x, y) for x, y in q.exterior.coords], fill=1)
    for t in trees:
        r = crown_r(t) / RES
        if r > 0:
            x, y = P(t['x'], t['y'])
            dr.ellipse([x - r, y - r, x + r, y + r], fill=1)
    for f in fences:
        if f['kind'] in OPAQUE_FENCES and f.get('height_target_m', 2) >= EYE:
            for run in f['solid_runs_m']:
                if len(run) > 1:
                    dr.line([P(x, y) for x, y in run], fill=1, width=2)
    for p in props:
        if p['k'] in TALL:
            w, l = foot_of(p['k'])
            a = math.radians(90 - p['yaw'])
            g = orect(p['x'], p['y'], math.cos(a), math.sin(a), l * p.get('s', 1), w * p.get('s', 1))
            dr.polygon([P(x, y) for x, y in g.exterior.coords], fill=1)
    return np.array(im, dtype=bool)


def march(rast, T, pts, rays=24, max_m=600.0, seed=0):
    """Free distance of each ray: first raster hit or first point where the ground rises above the eye (h0 + 1.7 m)."""
    rng = np.random.default_rng(seed)
    out = []
    steps = np.arange(RES, max_m + 1e-6, RES)
    H_, W_ = rast.shape
    for (x, y) in pts:
        a0 = rng.uniform(0, 2 * np.pi / rays)
        ang = a0 + np.arange(rays) * 2 * np.pi / rays
        X = x + np.cos(ang)[:, None] * steps[None, :]
        Y = y + np.sin(ang)[:, None] * steps[None, :]
        ix = np.clip((X / RES).astype(int), 0, W_ - 1)
        iy = np.clip(((760 - Y) / RES).astype(int), 0, H_ - 1)
        hit = rast[iy, ix] | (X < 0) | (X > 1474) | (Y < 0) | (Y > 760)
        h0 = float(T.h(x, y)) + EYE
        hit |= T.h(X, Y) > h0
        first = np.where(hit.any(1), hit.argmax(1), len(steps) - 1)
        out.extend(steps[first].tolist())
    return np.array(out)


def sample_points(W, rasts, area, n, seed, roads_only=False):
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = area.bounds
    pts, cls = [], collections.Counter()
    tries = 0
    H_, W_ = rasts[0].shape
    while len(pts) < n and tries < 60000:
        tries += 1
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        p = Point(x, y)
        if not area.contains(p) or not W.land.contains(p) or W.water.buffer(1).contains(p):
            continue
        ix, iy = int(x / RES), int((760 - y) / RES)
        if any(r[min(iy, H_ - 1), min(ix, W_ - 1)] for r in rasts):
            continue
        c = 'street' if W.carriage.contains(p) else 'sidewalk' if W.corridor.contains(p) else 'yard'
        if c == 'yard' and cls['yard'] > n * 0.6 and not roads_only:
            continue
        pts.append((x, y))
        cls[c] += 1
    return pts, dict(cls)


def sightlines(W, revs, n_per=260):
    """revs: {name: (raster, Terrain)}; the same sample points (free in every revision) for all of them."""
    areas = dict(W.boxes)
    others = unary_union(list(W.boxes.values()))
    areas['common'] = W.land.difference(others.buffer(5)).intersection(W.carriage.buffer(60))
    res = {}
    rl = [v[0] for v in revs.values()]
    for k, area in areas.items():
        pts, cls = sample_points(W, rl, area, n_per, int(hashlib.md5(k.encode()).hexdigest()[:6], 16))
        row = dict(samples=len(pts), classes=cls)
        for name, (rast, T) in revs.items():
            dd = march(rast, T, pts, seed=7)
            row[name] = dict(median_m=R(np.median(dd)), free_gt60_pct=R(100 * np.mean(dd > 60)), free_gt120_pct=R(100 * np.mean(dd > 120)),
                             free_gt250_pct=R(100 * np.mean(dd > 250)))
        res[k] = row
    return res


def vista_axes(W, revs):
    """Free distance straight along the long Downtown street axes (eye on the carriageway centre, both directions)."""
    out = {}
    for rid in ('05_N', '05_B', '05_S', '05_W', '05_E'):
        l = next(l for r, l in W.roads if r['id'] == rid)
        cs = list(l.coords)
        a, b = max(zip(cs, cs[1:]), key=lambda q: math.dist(*q))
        L = math.dist(a, b)
        u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        row = dict(straight_m=R(L))
        for name, (rast, T) in revs.items():
            dd = []
            for (p, dirn) in ((a, u), (b, (-u[0], -u[1]))):
                for f in (0.15, 0.5):
                    q = (p[0] + dirn[0] * L * f, p[1] + dirn[1] * L * f)
                    steps = np.arange(RES, 700, RES)
                    X, Y = q[0] + dirn[0] * steps, q[1] + dirn[1] * steps
                    H_, W_ = rast.shape
                    ix = np.clip((X / RES).astype(int), 0, W_ - 1)
                    iy = np.clip(((760 - Y) / RES).astype(int), 0, H_ - 1)
                    hit = rast[iy, ix] | (T.h(X, Y) > float(T.h(*q)) + EYE) | (X < 0) | (X > 1474) | (Y < 0) | (Y > 760)
                    dd.append(R(steps[hit.argmax()] if hit.any() else 700))
            row[name] = dd
        out[rid] = row
    return out


def lawn_circles(W, d, trees, props_solid, extra_obst=()):
    """Largest empty circle of open ground (no building, crown, solid prop, fence, field/bed/paved surface) per district and in
    the common land within 150 m of a road (the 'no empty lawn wider than 30 / 60 m' rules)."""
    surf = unary_union([valid(Polygon(s['polygon_m'])) for s in d['structures'] if s.get('polygon_m') and len(s['polygon_m']) >= 3 and s['kind'] in
                        ('yellow_field', 'vegetable_beds', 'parking', 'paved_forecourt', 'helipad', 'plaza_paving', 'football_pitch', 'loading_yard',
                         'paved_area_or_parking', 'parking_or_lot', 'golden_statue_on_round_plaza', 'lookout_terrace', 'military_vehicle_park',
                         'base_yard_van_spot', 'city_block_inside_sidewalks', 'rock_waterfall', 'wooden_pier', 'yacht_pier')])
    surf = unary_union([surf] + [g for g, m, c, p in W.pads if m in ('dry_field', 'gravel', 'concrete', 'asphalt', 'paving', 'rubber')])
    obst_tree = unary_union([Point(t['x'], t['y']).buffer(1.2 if t['sp'] == 'bush' else 2.6) for t in trees])
    obst = unary_union([unary_union([g for g, t in W.solid]), obst_tree, unary_union(props_solid) if props_solid else Polygon()] + list(extra_obst))
    base = W.land.difference(W.corridor).difference(W.water.buffer(1)).difference(W.sand).difference(surf)
    out = {}
    others = unary_union(list(W.boxes.values()))
    areas = dict(W.boxes)
    areas['common_near_roads'] = W.land.difference(others).intersection(W.carriage.buffer(150))
    for k, a in areas.items():
        r, at = largest_open(base.intersection(a), obst, 50)
        out[k] = dict(r_m=r, diameter_m=R(2 * r), at=at)
    return out


# ---------------------------------------------------------------- checks
def graph_edge_keys(g):
    """Edges keyed by owner (a surface join by the roads it joins, since joins are numbered) and polyline."""
    joins = {j['id']: tuple(j['source_road_ids']) for j in g['surface_connections']}
    return {(joins.get(e['road_id'], (e['road_id'],)), json.dumps(e['polyline_m'])) for e in g['edges']}


def protected_equal(d, d16, allow=None):
    """Vadim's layout must be byte-equal to v16 (v11) for every protected field. allow (Fedya 2026-10-12): the reshaped hamlet
    driveways, the POIs that moved inside their houses, and graph edges of those roads / of the roads their van stops split."""
    allow = allow or {}
    ar, ap, ag = set(allow.get('roads', ())), set(allow.get('points', ())), set(allow.get('graph_roads', ()))
    bad = []
    pick = lambda q, ks: {k: q.get(k) for k in ks}
    for a, b in zip(d16['districts'], d['districts']):
        if pick(a, ('id', 'polygon_m', 'bbox_m', 'label_m')) != pick(b, ('id', 'polygon_m', 'bbox_m', 'label_m')):
            bad.append('district ' + a['id'])
    for key in ('roads', 'paths'):
        A = {r['id']: pick(r, ('polyline_m', 'class', 'width_m', 'source_class', 'van_access')) for r in d16[key]}
        B = {r['id']: pick(r, ('polyline_m', 'class', 'width_m', 'source_class', 'van_access')) for r in d[key]}
        if A.keys() != B.keys() or {k for k in A if A[k] != B[k]} - ar:
            bad.append(key)
    for key in ('points', 'pois'):
        A = {q['id']: q for q in d16[key]}
        B = {q['id']: q for q in d[key]}
        if A.keys() != B.keys() or {k for k in A if A[k] != B[k]} - ap:
            bad.append(key)
    for key in ('road_graph', 'pedestrian_graph'):
        if d16[key] != d[key] and {r for k, _ in graph_edge_keys(d16[key]) ^ graph_edge_keys(d[key]) for r in k} - ag:
            bad.append(key)
    W16 = {w['id']: w for w in d16['water']}
    for w in d['water']:
        if w['id'] in W16 and w != W16[w['id']]:
            bad.append('water ' + w['id'])
    if set(W16) - {w['id'] for w in d['water']}:
        bad.append('water removed')
    for key in ('bridges', 'exits', 'police_parking_proposals', 'boundary', 'sand_areas', 'base_mapping', 'gameplay_mapping'):
        if d16[key] != d[key]:
            bad.append(key)
    for key in ('coast_segments', 'coast_polyline_m', 'land_polygon_m', 'ridge', 'small_mountain'):
        if d16['terrain_hints'][key] != d['terrain_hints'][key]:
            bad.append('terrain_hints.' + key)
    return bad


def border_fences(d, fences):
    """MapLookValidator.BorderFences rule: no generated fence runs within 3 m of a district outline for 6 m in a row."""
    rings = [box(*q['bbox_m'][0], *q['bbox_m'][1]).exterior for q in d['districts']]
    band = unary_union([r.buffer(3.0) for r in rings])
    bad = []
    for f in fences:
        for run in f['solid_runs_m']:
            if len(run) < 2:
                continue
            ln = LineString(run)
            hug = 0
            for s in np.arange(0, ln.length + 0.01, 1.0):
                hug = hug + 1 if band.contains(ln.interpolate(s)) else 0
                if hug >= 6:
                    bad.append(f['id'])
                    break
            if bad and bad[-1] == f['id']:
                break
    return bad


def checks18(W, d, d16, T, allow=None):
    res = m17.check(W, d, d16)
    allow = allow or {}
    moved = set(allow.get('points', ()))
    res['points_newly_inside_buildings'] = [p for p in res['points_newly_inside_buildings'] if p not in moved]
    houses = {b['id']: geom(b) for b in d['functional_buildings'] if b.get('v18_hamlet_shift_m')}
    res['hamlet_pois_inside_their_moved_house'] = {p['id']: any(g.contains(Point(p['position_m'])) for g in houses.values()) for p in d['points'] if p['id'] in moved}
    res['hamlet_moved_buildings_on_roads'] = [k for k, g in houses.items() if g.intersects(W.corridor.buffer(-0.05))]
    dl = [LineString(r['polyline_m']) for r in d['roads'] if r['id'] in set(allow.get('roads', ()))]
    res['hamlet_driveways_through_buildings'] = [b['id'] for b in d['functional_buildings'] if b['district_id'] == 'village' and any(l.intersects(geom(b).buffer(-0.2)) for l in dl)]
    res['protected_exceptions'] = {k: sorted(v) for k, v in allow.items()}
    sp = [Point(p['position_m']) for p in d['points'] if p['id'] in ('P02', 'B02')]
    b16 = {b['id'] for b in d16['functional_buildings']}
    res['spawn_clear'] = not any(g.contains(q) for q in sp for i, (g, t) in enumerate(W.solid) if not (t == 'building' and i in W.bidx_rev and W.bidx_rev[i] in b16))
    res['spawn_note'] = 'P02/B02 stand inside the base 2 hut since v11; only solids new in v17/v18 are tested.'
    res['protected_layout_changed'] = protected_equal(d, d16, allow)
    res['generated_fences_on_district_borders'] = border_fences(d, W.fences)
    roads = unary_union([LineString(r['polyline_m']) for r in d['roads'] + d['paths']])
    res['generated_fences_crossing_road_centrelines'] = [f['id'] for f in W.fences if any(LineString(run).intersects(roads) for run in f['solid_runs_m'] if len(run) > 1)]
    res['new_water_on_roads_or_buildings'] = [w['id'] for w in d['water'] if w['id'] in W.new_water and (valid(Polygon(w['polygon_m'])).intersects(W.corridor) or
                                              any(valid(Polygon(w['polygon_m'])).intersects(geom(b)) for b in d['functional_buildings']))]
    g = T.grades()
    res['roads_over_8pct'] = {k: R(v['max'] * 100) for k, v in g.items() if v['max'] > ROAD_GRADE + 0.002}
    res['max_road_grade_pct'] = R(max(v['max'] for v in g.values()) * 100)
    nb = [b for b in d['functional_buildings'] if b.get('v17', {}).get('rev') == 'v18' and b['v17'].get('zone') != 'kept']
    blds_other = unary_union([geom(b) for b in d['functional_buildings'] if not (b.get('v17', {}).get('rev') == 'v18' and b['v17'].get('zone') != 'kept')])
    res['v18_buildings_overlapping_others'] = [b['id'] for b in nb if geom(b).buffer(-0.05).intersects(blds_other)]
    return res


# ---------------------------------------------------------------- flats, crowd, render
def patch_flats(W, d, look, grey, pylons, mine_pts=None):
    blds = {b['id']: b for b in d['functional_buildings']}
    for lb in look['buildings']:
        b = blds[lb['id']]
        v = b.get('v17')
        if not v:
            continue
        lb['floor_h'] = v['floor_h']
        lb['ground_h'] = v['ground_h']
        lb['h'] = b['height_m']
        doors = v.get('doors') or [b['entrance_m']]
        lb['ent'] = [q for x, y in doors for q in (R(x), R(y), R(lb['ent'][2] if len(lb['ent']) > 2 else 0))]
        if v.get('roof') == 'gable':
            lb['roof'] = 'gable'
        lb['v17_recipe'] = v.get('recipe', v.get('zone', ''))
    occ = unary_union([geom(b).buffer(1.5) for b in d['functional_buildings'] if b.get('v17')] + [g for g, t in W.solid if t != 'building'] + W.clear_zones)
    # scatter trees next to v18 trees go; the positions before the thinning are used so the cut trees leave real gaps
    mine = unary_union([Point(x, y).buffer(2.4) for x, y in (W.tree_pts if mine_pts is None else mine_pts)])
    before = len(look['trees'])
    xs = np.array([t['x'] for t in look['trees']])
    ys = np.array([t['y'] for t in look['trees']])
    bad = shapely.contains_xy(occ, xs, ys) | shapely.contains_xy(mine, xs, ys)
    look['trees'] = [t for t, b in zip(look['trees'], bad) if not b] + W.trees
    grey['tree_data'] = [v for t in look['trees'] for v in (t['x'], t['y'], .3, t['h'])]
    for g, mat, ctx, prio in W.pads:
        look['ground'].append(m16.ground_record(g, mat, ctx, prio))
    look['ground'].sort(key=lambda q: q['prio'])
    look['v17'] = dict(phase='B', props=W.props, pylon_line=pylons,
                       rules=dict(storey_m=STOREY, shop_ground_m=SHOP_GROUND, parapet_max_m=0.6, door_m=[1.1, 2.3], road_grade_max=ROAD_GRADE),
                       note='Props: registry keys (prop/...) or procedural kinds (proc/...); yaw = Unity yaw degrees; solid -> box collider; s = scale. '
                            'v18 (phase B) keeps the v17 key so MapLookBuilderV3 builds it with only the revision switched.')
    look['warnings'].append('v18 phase B: every district and the common land at game scale and density (map_plan_v18.py); props/trees/pads include phase A.')
    for p in W.props:
        if p['solid'] and p['k'] not in ('proc/laundry_poles',):
            grey['hedges'].append(dict(x=p['x'], y=p['y'], w=1.8, d=1.8, a=R(90 - p['yaw']), h=1.6, label='v17_prop', source_kind=p['k']))
    return before, len(look['trees'])


def crowd_view(W, d):
    """Plan copy for the crowd generator: solid props, haystacks, wells and pools become closed obstacle rings; open fence
    lines become thin closed rings (the v12 crowd code treats fence polylines as polygons)."""
    dc = dict(d)
    fences = []
    for f in d['fences']:
        if ('_v17_' in f['id'] or '_v18_' in f['id']) and (len(f['polyline_m']) < 4 or f['polyline_m'][0] != f['polyline_m'][-1]):
            ring = LineString(f['polyline_m']).buffer(0.12, cap_style=2)
            f = dict(f, polyline_m=[[R(x), R(y)] for x, y in ring.exterior.coords])
        fences.append(f)
    k = 0
    for g, tag in W.solid:
        if tag in ('building', 'fence', 'car_street'):
            continue
        for q in parts(g.buffer(0)):
            k += 1
            ring = [[R(x), R(y)] for x, y in orient(q, 1).exterior.coords]
            if len(ring) >= 4:
                fences.append(dict(id=f'CROWD_OBST_{k}', kind='v18_prop_obstacle', polyline_m=ring, gates=[], solid_runs_m=[ring], gap_intervals_m=[], height_target_m=1))
    dc['fences'] = fences
    return dc


def render(plan_path, dst):
    """Top-down PNG in the look of MAP_PLAN_R01_v16/_v17.png: the v16 base render (needs C:/Windows/Fonts/arial*.ttf and
    World_v11/VOLUNTEERS_MAP_v11_PREVIEW.png) plus relief ellipses, ground pads, generated buildings, trees, props and fences."""
    d = m16.read(plan_path)
    if Path(dst).exists():
        raise FileExistsError(dst)
    tmp, tmp2 = Path(dst).with_name('_tmp_render_v18.png'), Path(dst).with_name('_tmp_overlay_v18.png')
    for t in (tmp, tmp2):
        if t.exists():
            t.unlink()
    info = m16.render(d, tmp, tmp2)
    im = Image.open(tmp).convert('RGB')
    dr = ImageDraw.Draw(im)
    sx, sy, H = info['x_px_per_m'], info['y_px_per_m'], info['height_px']
    # The v16 legend names v16: overwrite its first two lines.
    try:
        title, small = m16.ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 26), m16.ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 14)
    except OSError:
        title = small = m16.ImageFont.load_default()
    dr.rectangle((40, H - 182, 630, H - 122), fill='#f7f0dd')
    dr.text((48, H - 176), 'VOLUNTEERS ONLY — R01 v18 / WORLD v11 (phase B)', font=title, fill='#354843')
    dr.text((48, H - 148), f"{len(d['functional_buildings'])} footprints · 119 numbered POIs · 5 bases · game scale + density, all districts", font=small, fill='#354843')
    px = lambda x, y: (x * sx, H - y * sy)
    for h in d['hills']:
        if h['id'].startswith(('V17_RELIEF', 'V18_RELIEF', 'V18_GRADE')):
            (cx, cy), (rx, ry) = h['center_m'], h['radii_m']
            col = '#8a7a55' if h['height_target_m'] > 0 else '#6a7f9a'
            dr.ellipse([px(cx - rx, cy + ry), px(cx + rx, cy - ry)], outline=col, width=1 if h['id'].startswith('V18_GRADE') else 2)
    v = d['v17_dressing']
    cols = {'forest_floor': '#b4c3a6', 'rubber': '#c46a5a', 'gravel': '#b9b2a2', 'concrete': '#c9c7c0', 'asphalt': '#8f9594', 'dry_field': '#c8b98a',
            'paving': '#d8d0bf', 'lawn': '#b9cf9c', 'park_grass': '#a9c48f', 'worn_grass': '#c2c49a', 'sand': '#e3cf9e'}
    for p in v['pads']:
        if len(p['polygon_m']) >= 3:
            dr.polygon([px(x, y) for x, y in p['polygon_m']], fill=cols.get(p['mat'], '#cccccc'))
    for w in d['water']:
        if w.get('note', '').startswith('v18'):
            dr.polygon([px(x, y) for x, y in w['polygon_m']], fill='#a7c5cb', outline='#739da6')
    for b in d['functional_buildings']:
        if b.get('v17') and b['v17'].get('zone') != 'kept' or b.get('v17', {}).get('rev') == 'v18':
            f = b['storeys']
            dr.polygon([px(x, y) for x, y in b['footprint_m']], fill=(150 + min(f, 7) * 14, 120 - min(f, 7) * 8, 95), outline='#3f4a48')
    for s in d['structures']:
        if s.get('note') == 'v18 generated' and s['kind'] == 'haystack':
            x, y = px(*s['position_m'])
            r = s['radius_m'] * sx
            dr.ellipse([x - r, y - r, x + r, y + r], fill='#d9b45a', outline='#8a6a2a')
    for t in v['trees']:
        x, y = px(t['x'], t['y'])
        r = 1.2 if t['sp'] == 'bush' else 2.2
        dr.ellipse([x - r, y - r, x + r, y + r], fill='#4f7a45' if t['sp'] != 'bush' else '#6f9a5a')
    for p in v['props']:
        x, y = px(p['x'], p['y'])
        col = '#2f5f9a' if 'car' in p['k'] or 'van_' in p['k'] or 'truck' in p['k'] else '#7a3d2b' if p['k'].startswith('proc/pylon') else '#555555'
        dr.rectangle([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=col)
    for f in d['fences']:
        if '_v17_' in f['id'] or '_v18_' in f['id']:
            for run in f['solid_runs_m']:
                if len(run) > 1:
                    dr.line([px(x, y) for x, y in run], fill='#5a4632', width=1)
    im.save(dst)
    tmp.unlink()
    tmp2.unlink()
    return info


def district_stats(bs, district, bx):
    fl = [b['storeys'] for b in bs if b['district_id'] == district]
    small = ('metal_garage_row', 'v17_garage', 'v17_shed', 'v17_annex', 'v17_transformer', 'v17_dacha', 'shed', 'shipping_container_stack', 'kiosk')
    big = [b for b in bs if b['district_id'] == district and b['world_kind'] not in small and b['type'] not in small]
    fl2 = sorted(b['storeys'] for b in big)
    area = sum(geom(b).area for b in bs if bx.contains(geom(b).centroid))
    return dict(count=len(fl), main_buildings=len(big), floors_median=float(np.median(fl2)) if fl2 else 0, floors_max=max(fl2) if fl2 else 0,
                built_up_pct=R(100 * area / bx.area), height_max_m=R(max(b['height_m'] for b in big)) if big else 0)


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description='R01 v18 phase B')
    ap.add_argument('--out-dir', type=Path, default=MAP)
    ap.add_argument('--dry', action='store_true', help='compute and print metrics only; write nothing')
    ap.add_argument('--render', action='store_true', help='only render MAP_PLAN_R01_v18.png from MAP_PLAN_R01_v18.json (Windows fonts + v11 preview needed)')
    a = ap.parse_args(argv)
    out = a.out_dir.resolve()
    if a.render:
        info = render(out / (STEM + '.json'), out / (STEM + '.png'))
        print('rendered', out / (STEM + '.png'), info)
        return
    names = [STEM + '.json', 'Greybox/greybox_v18_flat.json', 'Look/look_v18_flat.json', 'Crowd/crowd_v18.json']
    if not a.dry:
        existing = [str(out / n) for n in names if (out / n).exists()]
        if existing:
            raise FileExistsError('No existing deliverable may be overwritten: ' + ', '.join(existing))
    d17 = m16.read(MAP / SRC)
    d16 = m16.read(MAP / 'MAP_PLAN_R01_v16.json')
    d = copy.deepcopy(d17)
    W = m17.World(d)
    rehydrate(W, d)
    prepare(W, d)
    gen = {}
    print('v18: phase A fixes', flush=True)
    plaza_core(W)
    gen['rough_rooms'] = rough_rooms(W, d)
    gen['vistas'] = vistas(W, d)
    phase_a_trees = {id(t) for t in W.trees}          # v17 trees and the phase A fixes: never thinned
    print('v18: districts', flush=True)
    gen['rescaled'] = rescale_rest(W, d)
    for name, fn in (('village', village), ('hamlet', hamlet), ('industrial', industrial), ('transition', transition), ('tramduro', tramduro), ('elite', elite),
                     ('beach', beach), ('forest', forest), ('fields', fields_district)):
        print('  ', name, flush=True)
        gen[name] = fn(W, d)
    print('v18: common land', flush=True)
    gen['common'], pylons_new = common_land(W, d)
    print('v18: thinning trees', flush=True)
    pre_thin_pts = list(W.tree_pts)
    gen['tree_thinning'], _ = thin_trees(W, phase_a_trees)
    print('v18: relief + grades', flush=True)
    skel = m16.flatten_look(d, no_veg=True)
    T = Terrain(skel, d['hills'])
    g17 = {k: R(v['max'] * 100) for k, v in T.grades().items() if v['max'] > ROAD_GRADE + 0.002}
    hills = relief(W, d, T)
    fix = {}
    for rnd in range(5):
        over = sorted(set(k for k, v in T.grades().items() if v['max'] > ROAD_GRADE - 0.003) | (set(FIX_ROADS) if rnd == 0 else set()))
        if not over:
            break
        for k, v in grade_fix(W, d, T, over, 'ABCDE'[rnd]).items():
            fix[k] = dict(v, before=fix[k]['before'], bumps=fix[k]['bumps'] + v['bumps']) if k in fix else v
    for k in fix:
        fix[k]['after'] = R(T.profile(next(r for r in T.look['roads'] if r['id'] == k))['max'] * 100)
    dev('Road grades: ' + ', '.join(f"{k} {v['before']} -> {v['after']} % ({v['bumps']} terrain bumps)" for k, v in fix.items()) +
        '; all roads <= 8 % in the HeightModel port; centrelines untouched.')
    gen['grade_fix'] = fix
    # Assemble the plan.
    d['functional_buildings'] = [W.buildings[i] for i in W.order if i in W.buildings]
    d['fences'] = d['fences'] + W.fences
    d['revision'] = REV
    d['title_ru'] = 'VOLUNTEERS ONLY / R01 v18 — World v11, phase B (all districts at game scale and density)'
    d['provenance'] = dict(d['provenance'], v17_plan=SRC, v17_sha256=m16.sha(MAP / SRC), method_v18='map_plan_v18.py: v17 + phase B rules (fixed seeds)')
    d['metrics']['building_count'] = len(d['functional_buildings'])
    d['metrics']['building_counts_by_district'] = dict(collections.Counter(b['district_id'] for b in d['functional_buildings']))
    for q in d['districts']:
        q['building_count'] = d['metrics']['building_counts_by_district'].get(q['id'], 0)
    pylons = list(d17['v17_dressing'].get('pylon_line', [])) + pylons_new
    d['v17_dressing'] = dict(props=W.props, trees=W.trees, pads=[dict(mat=m, ctx=c, prio=p, polygon_m=[[R(x), R(y)] for x, y in g.exterior.coords[:-1]])
                                                                for g, m, c, p in W.pads], pylon_line=pylons)
    print('v18: flats', flush=True)
    grey = m16.flatten_greybox(d)
    look = m16.flatten_look(d)
    tb, ta = patch_flats(W, d, look, grey, pylons, pre_thin_pts)
    print(f'v18: trees {tb} scatter -> {ta} total', flush=True)
    print('v18: metrics', flush=True)
    T18 = Terrain(look, d['hills'])
    look16 = m16.read(MAP / 'Look/look_v16_flat.json')
    look17 = m16.read(MAP / 'Look/look_v17_flat.json')
    T16, T17 = Terrain(look16, d16['hills']), Terrain(look17, d17['hills'])
    props17 = d17['v17_dressing']['props']
    r16 = obstacle_raster([geom(b) for b in d16['functional_buildings']], look16['trees'], d16['fences'], [])
    r17 = obstacle_raster([geom(b) for b in d17['functional_buildings']], look17['trees'], d17['fences'], props17)
    r18 = obstacle_raster([geom(b) for b in d['functional_buildings']], look['trees'], d['fences'], W.props)
    revs = dict(v16=(r16, T16), v17=(r17, T17), v18=(r18, T18))
    sl = sightlines(W, revs)
    vx = vista_axes(W, revs)
    props_solid = [g for g, t in W.solid if t not in ('building', 'car_street')]
    lawn18 = lawn_circles(W, d, look['trees'], props_solid)
    stats = {k: dict(v16=district_stats(d16['functional_buildings'], k, W.boxes[k]), v18=district_stats(d['functional_buildings'], k, W.boxes[k])) for k in W.boxes}
    core_obst = unary_union([g for g, t in W.solid if t != 'car_street' and g.intersects(PLAZA_CORE)] +
                            [Point(t['x'], t['y']).buffer(1.2 if t['sp'] == 'bush' else 2.6) for t in W.trees if PLAZA_CORE.buffer(3).contains(Point(t['x'], t['y']))] +
                            [g for g, m, c, p in W.pads if m == 'park_grass' and g.intersects(PLAZA_CORE)])
    plaza = dict(core_largest_open_circle=largest_open(PLAZA_CORE, core_obst, 4), core_largest_open_square_side_m=None)
    plaza['core_largest_open_square_side_m'] = R(plaza['core_largest_open_circle'][0] * math.sqrt(2))
    metrics = dict(sightlines_eye_1_7m=sl, vista_axes_m=vx, empty_lawn_circles_v18=lawn18, buildings=stats, plaza_core=plaza, generation=gen,
                   relief_hills_added=len(hills), road_grades_over_8pct_v17=g17, props=len(W.props), dressing_trees=len(W.trees),
                   fences_added_v18=len(W.fences), look_trees=ta)
    hm = gen['hamlet']
    allow = dict(roads=[q['road'] for q in hm['driveways']], points=hm['pois_moved_with_houses'],
                 graph_roads=sorted({q['road'] for q in hm['driveways']} | {q['parent'] for q in hm['driveways']} |
                                    {next(p['access_road_id'] for p in d['points'] if p['id'] == i) for i in hm['pois_moved_with_houses']}))
    res = checks18(W, d, d16, T18, allow)
    d['checks'] = dict(d['checks'], v18=res)
    d['v18_phase_b'] = dict(rules=dict(storey_m=STOREY, shop_ground_m=SHOP_GROUND, village_house_m=[6, 10], village_empty_lawn_max_m=30,
                                       common_empty_lawn_max_m=60, plaza_open_paving_max_m=25, road_grade_max=ROAD_GRADE, relief_hills_m=[3, 15],
                                       fence_border_band_m=4, sightline=dict(eye_m=EYE, raster_m=RES, rays=24, max_m=600, samples_per_area=260)),
                            deviations_from_v17_v11=DEVIATIONS, metrics=metrics,
                            schema_note='v17 schema kept; optional: building v17.rev, look v17.phase, prop s, water kinds well/swimming_pool (v18 notes), negative hill heights (cuttings).')
    print(json.dumps(dict(sightlines=sl, vistas=vx, lawn=lawn18, plaza=plaza), indent=1, default=str)[:12000])
    print(json.dumps(res, indent=1, default=str)[:4000])
    if a.dry:
        return d, look, grey, W
    m16.json_new(out / names[0], d)
    m16.json_new(out / names[1], grey)
    m16.json_new(out / names[2], look)
    print('v18: crowd', flush=True)
    crowd = m16.build_crowd(crowd_view(W, d), look, m16.sha(out / names[0]))
    crowd['generator'] = 'map_plan_v18.py (v16 crowd builder, crowd_v12 algorithms; v17+v18 props, haystacks, wells, pools as obstacles)'
    m16.json_new(out / names[3], crowd)
    print('crowd validation', json.dumps(crowd['validation'])[:800], flush=True)
    print('done', flush=True)


if __name__ == '__main__':
    main()
