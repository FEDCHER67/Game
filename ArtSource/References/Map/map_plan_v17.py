"""VOLUNTEERS ONLY R01 v17, phase A: the v16 layout with game scale, density, occlusion and landscape for Downtown
(old_town) and the Rough District (residential).

Run with Python 3.12 + shapely/numpy/pillow, e.g.
    uv run --offline --no-project -p 3.12 --with shapely --with numpy --with pillow python -B map_plan_v17.py

Reads MAP_PLAN_R01_v16.json (never written). Writes, exclusive-create (no deliverable is ever overwritten):
    MAP_PLAN_R01_v17.json, MAP_PLAN_R01_v17.png, Greybox/greybox_v17_flat.json, Look/look_v17_flat.json,
    Crowd/crowd_v17.json, ../../../Working/Reviews/Map_v17_A/sightline_samples.json and v17_metrics.json.

Vadim's layout is kept: district envelopes, road centrelines/classes, water, bridges, coasts, exits, POIs, bases,
police parking, trip-meter destinations and spawn points keep their coordinates. Changed: Downtown buildings (perimeter
lots, game-scale storeys), Rough District panel blocks (sections, entrances), yard/courtyard infill, plaza fill, street
dressing, common-land landscape (forest belts, hills, garages, allotments, pylons, billboards). Fixed seeds throughout.
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
ROOT = MAP.parents[2]
REVIEW = ROOT / 'Working' / 'Reviews' / 'Map_v17_A'
REV, STEM, SRC = 'v17', 'MAP_PLAN_R01_v17', 'MAP_PLAN_R01_v16.json'


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m16 = load_module(MAP / 'map_plan_v16.py', 'map_plan_v16_for_v17')
m16.REV, m16.STEM = REV, STEM
parts, valid, geom, flat = m16.parts, m16.valid, m16.geom, m16.flat

# ---------------------------------------------------------------- game-scale rules (the lead's targets)
STOREY, SHOP_GROUND, GARAGE_H = 2.8, 3.3, 2.6
DT_BOX = box(646, 250, 1090, 478)
RD_BOX = box(550, 554, 824.8, 696.4)
PHASE_A = {'old_town': DT_BOX, 'residential': RD_BOX}
WID = {'old_town': '05', 'residential': '04'}
# Kept Downtown buildings: gameplay functions, the corner shops (crowd POIs), the podiums and the two landmarks.
DT_KEEP = {'05_B001', '05_B002', '05_B003', '05_B005', '05_B006', '05_B007', '05_B008', '05_B021', '05_B022',
           '05_B025', '05_B026', '05_B036', '05_B039', '05_B054'}
DT_REMOVED_TOWER = '05_B004'
LANDMARKS = {'05_B002': 11, '05_B022': 10}
# Lot recipes: (name, type, floors, frontage range m, weight). Variety per lot, never per window.
RECIPES = [('shop2', 'mid_rise', 2, (9, 14), 12), ('row3', 'mid_rise', 3, (8, 12), 30), ('walkup4', 'mid_rise', 4, (10, 16), 28),
           ('tenement5', 'mid_rise', 5, (12, 18), 16), ('loft5', 'brick_loft', 5, (14, 20), 8), ('block6', 'mid_rise', 6, (14, 20), 6)]
ROOFS = ['#6E6A64', '#7A7268', '#5F6260', '#857A6C', '#6B6E70']
DEVIATIONS = []


def dev(text):
    DEVIATIONS.append(text)


def R(x):
    return round(float(x), 3)


def rng_for(tag):
    return np.random.default_rng(int(hashlib.sha256(('v17:' + tag).encode()).hexdigest()[:8], 16))


def orect(cx, cy, ux, uy, length, width):
    vx, vy = -uy, ux
    hl, hw = length / 2, width / 2
    return Polygon([(cx - ux * hl - vx * hw, cy - uy * hl - vy * hw), (cx + ux * hl - vx * hw, cy + uy * hl - vy * hw),
                    (cx + ux * hl + vx * hw, cy + uy * hl + vy * hw), (cx - ux * hl + vx * hw, cy - uy * hl + vy * hw)])


def largest(g):
    ps = parts(g)
    return max(ps, key=lambda p: p.area) if ps else None


def unity_yaw(ux, uy):
    """Unity yaw (deg, clockwise from +Z = plan north) of the plan direction (ux, uy)."""
    return R((90 - math.degrees(math.atan2(uy, ux))) % 360)


def pole(g):
    p = polylabel(g, tolerance=0.6)
    return p, g.boundary.distance(p)


def min_dim(g):
    r = g.minimum_rotated_rectangle
    c = list(r.exterior.coords)
    return min(math.dist(c[0], c[1]), math.dist(c[1], c[2])), max(math.dist(c[0], c[1]), math.dist(c[1], c[2]))


def edge_dir_near(g, p):
    """Unit direction of the boundary segment of g nearest to p (for aligning placed items)."""
    best, bd = (1.0, 0.0), 1e9
    for ring in [g.exterior] + list(g.interiors):
        c = list(ring.coords)
        for a, b in zip(c, c[1:]):
            dd = LineString([a, b]).distance(p)
            if dd < bd and math.dist(a, b) > 1:
                bd, L = dd, math.dist(a, b)
                best = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
    return best


class World:
    """Everything placed for v17 (buildings, fences, props, trees, ground pads, hills)."""

    def __init__(self, d):
        self.d = d
        self.buildings = {b['id']: b for b in d['functional_buildings']}
        self.order = [b['id'] for b in d['functional_buildings']]
        self.fences, self.props, self.trees, self.pads, self.hills, self.structs = [], [], [], [], [], []
        self.roads = [(r, LineString(r['polyline_m'])) for r in d['roads'] + d['paths']]
        self.carriage = unary_union([l.buffer(r['width_m'] / 2, cap_style=2, join_style=2) for r, l in self.roads])
        self.corridor = unary_union([l.buffer(r['width_m'] / 2 + (r.get('sidewalk_width_m') or 0), cap_style=2, join_style=2) for r, l in self.roads])
        self.decks = unary_union([Polygon(b['polygon_m']) for b in d['bridges']])
        self.water = unary_union([m16.water_geometry(w) for w in d['water']])
        self.inland = unary_union([m16.water_geometry(w) for w in d['water'] if w['kind'] != 'sea'])
        self.sand = unary_union([valid(Polygon(q['polygon_m'])) for q in d['sand_areas']])
        self.land = valid(Polygon(d['boundary']['polygon_m']))
        deg = collections.Counter(n for e in d['road_graph']['edges'] for n in (e['from_node'], e['to_node']))
        self.nodes = [Point(n['position_m']) for n in d['road_graph']['nodes'] if deg[n['id']] >= 3]
        self.ends = [Point(n['position_m']) for n in d['road_graph']['nodes'] if deg[n['id']] == 1]
        self.points = [Point(p['position_m']) for p in d['points']]
        self.police = unary_union([Polygon(q['source_polygon_m'] if q.get('source_polygon_m') else [q['pts'][i:i + 2] for i in range(0, len(q['pts']), 2)])
                                   for q in d['police_parking_proposals']])
        self.driveways = unary_union([Polygon(q['polygon_m']) for q in d['road_areas'] if q['surface'] == 'lowered_curb_driveway'])
        self.solid = []          # (geometry, tag) of everything solid placed in v17 (for clearance and crowd)
        self.tree_pts = []

    # ------------------------------------------------------------ records
    def nearest_road(self, p):
        r, _ = min(self.roads, key=lambda x: x[1].distance(p))
        return r['id']

    def add_building(self, bid, district, wkind, btype, poly, floors, ground_h, floor_h, doors, label='', roof='flat', zone='district', roof_colour=None, extra=None):
        poly = orient(valid(poly).simplify(0.05), 1)
        w, dep, ang = m16.obb(poly)
        c = poly.centroid
        H = ground_h + (floors - 1) * floor_h
        doors = [[R(x), R(y)] for x, y in doors] or [[R(c.x), R(c.y)]]
        b = dict(id=bid, district=WID[district], kind=wkind, footprint_m=[[R(x), R(y)] for x, y in poly.exterior.coords[:-1]],
                 floors=floors, height_m=R(H), roof_colour=roof_colour or ROOFS[int(hashlib.md5(bid.encode()).hexdigest(), 16) % len(ROOFS)],
                 plan_label=label, type=btype, world_kind=wkind, district_id=district, world_district_id=WID[district],
                 center_m=[R(c.x), R(c.y)], width_m=R(w), depth_m=R(dep), orientation_deg=R(ang), storeys=floors, label_ru=label,
                 poi_id='', source_id=bid, access_road_id=self.nearest_road(Point(doors[0])), entrance_m=doors[0],
                 entrance_status='v17 generated door (lead rule: street/yard facing)',
                 v17=dict(floor_h=floor_h, ground_h=ground_h, doors=doors, roof=roof, zone=zone, **(extra or {})))
        self.buildings[bid] = b
        if bid not in self.order:
            self.order.append(bid)
        self.solid.append((poly, 'building'))
        return b

    def scale_building(self, b, floors=None, ground_h=STOREY, floor_h=STOREY):
        if floors is not None:
            b['floors'] = b['storeys'] = floors
        n = b['storeys']
        b['height_m'] = R(ground_h + (n - 1) * floor_h)
        b['v17'] = dict(floor_h=floor_h, ground_h=ground_h, doors=[b['entrance_m']], roof='flat', zone='kept')

    def add_fence(self, fid, kind, line, district, h, gates=(), closed=False):
        pts = [[R(x), R(y)] for x, y in line]
        if closed and pts[0] != pts[-1]:
            pts.append(pts[0])
        ls = LineString(pts)
        if ls.length < 1:
            return
        gate_recs, gaps = [], []
        for i, (gx, gy, gw) in enumerate(gates):
            s = ls.project(Point(gx, gy))
            gaps.append([R(max(0, s - gw / 2)), R(min(ls.length, s + gw / 2))])
            gate_recs.append(dict(id=f'{fid}_G{i + 1}', position_m=[R(gx), R(gy)], width_m=gw, status='v17 generated', along_m=R(s)))
        gaps.sort()
        runs, s0 = [], 0.0
        for a, b in gaps + [[ls.length, ls.length]]:
            if a - s0 > 0.3:
                seg = shapely.ops.substring(ls, s0, a)
                runs.append([[R(x), R(y)] for x, y in seg.coords])
            s0 = max(s0, b)
        self.fences.append(dict(id=fid, kind=kind, district_id=district, world_district_id=WID[district], polyline_m=pts, gates=gate_recs,
                                gap_intervals_m=gaps, solid_runs_m=runs, height_target_m=h, height_status='v17 generated',
                                perimeter_role='v17_yard_fence (inside a district or common-land property; never on a district border)',
                                exception_requires_confirmation=False))
        for run in runs:
            if len(run) >= 2:
                self.solid.append((LineString(run).buffer(0.15), 'fence'))

    def add_prop(self, key, x, y, yaw, solid=True, foot=(1, 1), tag='prop', scale=1.0, cast=True):
        self.props.append(dict(k=key, x=R(x), y=R(y), yaw=R(yaw % 360), solid=solid, cast=cast, s=R(scale)))
        if solid:
            a = math.radians(90 - yaw)
            g = orect(x, y, math.cos(a), math.sin(a), foot[1], foot[0])
            self.solid.append((g, tag))
            return g
        return None

    def add_tree(self, sp, x, y, h):
        self.trees.append(dict(sp=sp, x=R(x), y=R(y), h=R(h)))
        self.tree_pts.append((x, y))

    def add_pad(self, g, mat, ctx, prio=36):
        for p in parts(valid(g)):
            if p.area > 2:
                self.pads.append((p, mat, ctx, prio))

    def occupied(self, extra=0.0):
        gs = [g for g, _ in self.solid]
        u = unary_union(gs)
        return u.buffer(extra) if extra else u


# ---------------------------------------------------------------- greedy room filler
def greedy_fill(zone, place, r_stop, max_items=5000):
    """Fill the largest empty circle first (pole of inaccessibility) until no circle of radius r_stop fits.
    place(part, point, radius, k) returns the footprint it used (or None -> a small disc is consumed)."""
    heap, alive, k = [], [], 0
    for p in parts(zone):
        if p.area > 4:
            pt, r = pole(p)
            alive.append(p)
            heapq.heappush(heap, (-r, len(alive) - 1, pt))
    while heap and k < max_items:
        negr, i, pt = heapq.heappop(heap)
        part = alive[i]
        if part is None:
            continue
        r = -negr
        if r < r_stop:
            break
        used = place(part, pt, r, k)
        k += 1
        if used is None or used.is_empty:
            used = pt.buffer(min(r, 3.0))
        alive[i] = None
        rest = part.difference(used)
        for q in parts(rest):
            if q.area > 4:
                qpt, qr = pole(q)
                alive.append(q)
                heapq.heappush(heap, (-qr, len(alive) - 1, qpt))
    return k


def tree_disc(W, part, c, rc, spacing, species, hrange, rng, under=0.0):
    """Jittered hex grid of trees inside disc(c, rc) and part; optional undergrowth bushes."""
    disc = c.buffer(rc).intersection(part)
    if disc.is_empty:
        return None
    n = 0
    dy = spacing * 0.866
    rows = int(rc * 2 / dy) + 2
    for j in range(rows):
        y = c.y - rc + j * dy
        off = (j % 2) * spacing / 2
        cols = int(rc * 2 / spacing) + 2
        for i in range(cols):
            x = c.x - rc + off + i * spacing
            px, py = x + rng.uniform(-0.9, 0.9), y + rng.uniform(-0.9, 0.9)
            if not disc.contains(Point(px, py)):
                continue
            sp = species[int(rng.integers(len(species)))]
            W.add_tree(sp, px, py, rng.uniform(*hrange))
            n += 1
            if under and rng.random() < under:
                bx, by = px + rng.uniform(-2.2, 2.2), py + rng.uniform(-2.2, 2.2)
                if disc.contains(Point(bx, by)):
                    W.add_tree('bush', bx, by, rng.uniform(1.4, 2.4))
    if n == 0:
        W.add_tree(species[0], c.x, c.y, hrange[1])
    return disc


def car_keys(rough):
    if rough:
        return ['prop/car_sedan_beige', 'prop/car_hatchback', 'prop/car_sedan_green', 'prop/car_sedan_blue', 'prop/car_sedan_red', 'prop/car_hatchback', 'prop/car_wrecked']
    return ['prop/car_sedan_blue', 'prop/car_sedan_red', 'prop/car_sedan_beige', 'prop/car_hatchback', 'prop/car_sedan_green', 'prop/van_minibus']


def car_row(W, part, c, u, n, rng, rough, perpendicular=False):
    """n parked cars side by side (perpendicular stalls) or nose to tail along u, centred at c."""
    keys = car_keys(rough)
    pitch = 2.7 if perpendicular else 5.6
    used = []
    for i in range(n):
        s = (i - (n - 1) / 2) * pitch
        x, y = c.x + u[0] * s, c.y + u[1] * s
        heading = (-u[1], u[0]) if perpendicular else u
        if rng.random() < 0.5:
            heading = (-heading[0], -heading[1])
        g = orect(x, y, heading[0], heading[1], 4.6, 2.0)
        if not part.buffer(0.01).contains(g):
            continue
        W.add_prop(keys[int(rng.integers(len(keys)))], x, y, unity_yaw(*heading), foot=(1.9, 4.5), tag='car')
        used.append(g)
    if not used:
        return None
    u_all = unary_union(used).buffer(0.8)
    W.add_pad(u_all.buffer(0.6), 'gravel' if rough else 'asphalt', 'v17_parking')
    return u_all


# ---------------------------------------------------------------- Downtown
def downtown(W):
    d = W.d
    rng = rng_for('downtown')
    keep = {k: W.buildings[k] for k in DT_KEEP}
    removed = [b['id'] for b in d['functional_buildings'] if b['district_id'] == 'old_town' and b['id'] not in DT_KEEP]
    for bid in removed:
        W.buildings.pop(bid)
        W.order.remove(bid)
    dev(f'Downtown: {len(removed)} v16/v11 buildings replaced by perimeter-block lots (kept {len(DT_KEEP)}: gameplay functions, '
        f'corner shops, podiums, landmarks): ' + ', '.join(removed))
    # Landmarks: at most two, 9-12 floors, footprint <= 20 x 20 m.
    b2 = keep['05_B002']
    cx, cy = b2['center_m']
    b2['footprint_m'] = [[R(cx - 10), R(cy - 10)], [R(cx + 10), R(cy - 10)], [R(cx + 10), R(cy + 10)], [R(cx - 10), R(cy + 10)]]
    b2['width_m'] = b2['depth_m'] = 20.0
    for bid, b in keep.items():
        ground = SHOP_GROUND if b['type'] not in ('podium', 'glass_podium', 'round_glass_tower', 'building') else STOREY + 0.4
        W.scale_building(b, LANDMARKS.get(bid), ground, STOREY)
    dev('Downtown landmarks: 05_B002 tower 20 -> 11 floors on a 20 x 20 m footprint (was 23 x 23); 05_B022 round glass tower 15 -> 10 floors; '
        '05_B004 (second 20-floor tower) removed, its podium 05_B003 stays.')
    for b in keep.values():
        W.solid.append((geom(b), 'building'))
    # Vadim's 'park / square' POIs on block edges become pocket squares in the street wall; the parking ramps stay clear.
    park_pois = [Point(p['position_m']) for p in d['points'] if p['id'].startswith('D05_POI') and p['name_ru'] == 'park / square']
    keep_zone = unary_union([geom(b).buffer(1.2) for b in keep.values()] + [W.police.buffer(1.5), W.driveways.buffer(2.5)] +
                            [q.buffer(7.5) for q in park_pois] + [Point(805.8, 447.6).buffer(6.0)])
    blocks_src = unary_union([valid(Polygon(s['polygon_m'])) for s in d['structures'] if s['kind'] == 'city_block_inside_sidewalks'])
    blocks = [orient(p.simplify(0.3), 1) for p in parts(blocks_src.difference(W.corridor)) if p.area > 150]
    blocks.sort(key=lambda p: (round(p.centroid.y), round(p.centroid.x)))
    plaza = next(p for p in blocks if p.contains(Point(868, 394)))
    placed = []
    lots = []
    fire, tanks, boards = [], [], []
    lot_no = 0

    def placed_union():
        return unary_union(placed) if placed else Polygon()

    for bi, P in enumerate(blocks):
        if P is plaza:
            continue
        md, Md = min_dim(P)
        D = 15.0 if md >= 44 else max(8.0, min(15.0, (md - 3.0) / 2.0))
        coords = list(P.exterior.coords)
        convex = []
        n = len(coords) - 1
        for i in range(n):
            a, b, c = coords[i - 1], coords[i], coords[(i + 1) % n]
            cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if cross > 1e-6:
                convex.append(Point(b))
        prev_f = None
        for i in range(n):
            a, b = coords[i], coords[i + 1]
            L = math.dist(a, b)
            if L < 6:
                continue
            u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            nrm = (u[1], -u[0])          # outward for a CCW ring
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            probe = Point(mid[0] + nrm[0] * 2.0, mid[1] + nrm[1] * 2.0)
            if not W.corridor.contains(probe):
                continue
            pu = placed_union()
            s = 0.0
            while s < L and pu.contains(Point(a[0] + u[0] * (s + 0.5) - nrm[0] * 1.0, a[1] + u[1] * (s + 0.5) - nrm[1] * 1.0)):
                s += 0.5
            if s > 0:
                s += 0.25
            alley_at = None
            if L > 70:
                alley_at = L * rng.uniform(0.38, 0.62)
            edge_lots = []
            while s < L - 0.5:
                # Recipe with the neighbour rule: 1-2 floors apart from the previous lot (75 %).
                for _ in range(20):
                    rec = RECIPES[int(rng.choice(len(RECIPES), p=np.array([r[4] for r in RECIPES]) / sum(r[4] for r in RECIPES)))]
                    if prev_f is None or (1 <= abs(rec[2] - prev_f) <= 2) or rng.random() < 0.25:
                        break
                f = rng.uniform(*rec[3])
                if L - s - f < 6.5:
                    f = L - s
                if f > 21.5:
                    f = (L - s) / 2 if L - s < 43 else 16.0
                s0, s1 = s + 0.12, s + f - 0.12
                if alley_at is not None and s0 < alley_at < s1 and alley_at - s0 > 6 and s1 - alley_at > 6:
                    s1 = alley_at - 1.75
                    f = s1 - s + 0.12
                rect = Polygon([(a[0] + u[0] * s0, a[1] + u[1] * s0), (a[0] + u[0] * s1, a[1] + u[1] * s1),
                                (a[0] + u[0] * s1 - nrm[0] * D, a[1] + u[1] * s1 - nrm[1] * D),
                                (a[0] + u[0] * s0 - nrm[0] * D, a[1] + u[1] * s0 - nrm[1] * D)])
                g = rect.intersection(P).difference(placed_union().buffer(0.1)).difference(keep_zone)
                g = largest(g)
                ok = g is not None and g.area >= 40 and min_dim(g)[0] >= 5
                if ok:
                    g = orient(g.simplify(0.2), 1)
                    corner = any(g.buffer(1.0).contains(q) for q in convex)
                    floors = rec[2] + (1 if corner else 0)
                    floors = min(6, max(2, floors))
                    lot_no += 1
                    door_s = (s0 + s1) / 2 + (rng.uniform(-0.25, 0.25) * (s1 - s0) if s1 - s0 > 9 else 0)
                    door = (a[0] + u[0] * door_s, a[1] + u[1] * door_s)
                    if not g.buffer(0.5).contains(Point(door)):
                        door = tuple(g.exterior.interpolate(g.exterior.project(Point(door))).coords[0])
                    lots.append(dict(g=g, floors=floors, type=rec[1], recipe=rec[0], corner=corner, door=door, u=u, nrm=nrm, D=D, block=bi, s0=s0, s1=s1, a=a))
                    placed.append(g)
                    edge_lots.append(len(lots) - 1)
                    prev_f = floors
                elif g is not None and g.area > 8 and edge_lots:
                    j = edge_lots[-1]
                    merged = lots[j]['g'].union(g.buffer(0.15)).buffer(-0.15)
                    if merged.geom_type == 'Polygon' and min_dim(merged)[1] <= 24.5:
                        lots[j]['g'] = orient(merged.simplify(0.2), 1)
                        placed[-1] = lots[j]['g']
                s += f
                if alley_at is not None and abs(s - (alley_at - 1.75 + 0.12)) < 0.3:
                    s = alley_at + 1.75
                    alley_at = None
    # Lots -> buildings (stable ids by order of placement).
    for k, lot in enumerate(lots):
        bid = f'05_L{k + 1:03d}'
        g = lot['g']
        yaw_out = unity_yaw(*lot['nrm'])
        b = W.add_building(bid, 'old_town', 'v17_lot', lot['type'], g, lot['floors'], SHOP_GROUND, STOREY, [lot['door']],
                           extra=dict(recipe=lot['recipe'], corner=lot['corner'], block=lot['block']))
        b['v17']['door_yaw'] = yaw_out
        # American recipe: fire escapes on the street facade, rooftop water tanks and billboards.
        fw = lot['s1'] - lot['s0']
        if lot['floors'] >= 4 and fw >= 9 and rng.random() < 0.32:
            sm = (lot['s0'] + lot['s1']) / 2 + (fw / 2 - 3.5) * (1 if rng.random() < 0.5 else -1)
            a, u = lot['a'], lot['u']
            p0 = (a[0] + u[0] * (sm - 2.5), a[1] + u[1] * (sm - 2.5))
            p1 = (a[0] + u[0] * (sm + 2.5), a[1] + u[1] * (sm + 2.5))
            fire.append(dict(id=f'05_v17_fire_escape_{k + 1:03d}', district='05', kind='fire_escape', facade_segment_m=[[R(p0[0]), R(p0[1])], [R(p1[0]), R(p1[1])]],
                             note='v17 lot fire escape (street facade)', district_id='old_town', world_district_id='05'))
        if lot['floors'] >= 4 and g.area > 120 and rng.random() < 0.35:
            c = g.representative_point()
            tanks.append(dict(id=f'05_v17_water_tower_{k + 1:03d}', district='05', kind='rooftop_water_tower', position_m=[R(c.x), R(c.y)],
                              note='v17 rooftop water tank', district_id='old_town', world_district_id='05'))
        if lot['corner'] and lot['floors'] >= 4 and rng.random() < 0.3:
            c = g.representative_point()
            boards.append(dict(id=f'05_v17_rooftop_billboard_{k + 1:03d}', district='05', kind='rooftop_billboard', position_m=[R(c.x), R(c.y)],
                               note='v17 corner rooftop billboard', district_id='old_town', world_district_id='05'))
    old_struct = [s for s in d['structures'] if s['district_id'] == 'old_town' and s['kind'] in ('fire_escape', 'rooftop_water_tower', 'rooftop_billboard')]
    d['structures'] = [s for s in d['structures'] if s not in old_struct] + fire + tanks + boards
    dev(f'Downtown facade structures regenerated for the new lots: {len(old_struct)} v16 fire escapes/rooftop tanks/billboards removed, '
        f'{len(fire)} fire escapes, {len(tanks)} rooftop water tanks, {len(boards)} rooftop billboards added.')
    # Courtyards: annexes, back-yard fences, then the room filler.
    lots_u = unary_union([lot['g'] for lot in lots])
    annex_no = 0
    court_rng = rng_for('downtown-courts')
    courts = []
    for bi, P in enumerate(blocks):
        if P is plaza:
            continue
        cy = P.difference(lots_u.buffer(0.3)).difference(keep_zone)
        cy = unary_union([q for q in parts(cy) if q.area > 30])
        if cy.is_empty:
            continue
        free = cy
        for k, lot in enumerate(lots):
            if lot['block'] != bi:
                continue
            u, nrm, a = lot['u'], lot['nrm'], lot['a']
            fw = lot['s1'] - lot['s0']
            back_mid = ((a[0] + u[0] * (lot['s0'] + lot['s1']) / 2) - nrm[0] * lot['D'], (a[1] + u[1] * (lot['s0'] + lot['s1']) / 2) - nrm[1] * lot['D'])
            if court_rng.random() < 0.42 and fw >= 7:
                depth = court_rng.uniform(5, 8)
                ann = orect(back_mid[0] - nrm[0] * (depth / 2 + 0.3), back_mid[1] - nrm[1] * (depth / 2 + 0.3), u[0], u[1], fw - 1.5, depth)
                ann = largest(ann.intersection(free.buffer(-0.2)))
                if ann is not None and ann.area >= 24 and min_dim(ann)[0] >= 4:
                    annex_no += 1
                    door = tuple(ann.exterior.interpolate(ann.exterior.project(Point(back_mid[0] - nrm[0] * (depth + 0.3), back_mid[1] - nrm[1] * (depth + 0.3)))).coords[0])
                    W.add_building(f'05_A{annex_no:03d}', 'old_town', 'v17_annex', 'car_workshop', ann, int(court_rng.integers(1, 3)), 3.0, STOREY, [door],
                                   extra=dict(recipe='annex'))
                    free = free.difference(ann.buffer(1.2))
            if court_rng.random() < 0.5:
                corner_back = (a[0] + u[0] * lot['s1'] - nrm[0] * lot['D'], a[1] + u[1] * lot['s1'] - nrm[1] * lot['D'])
                end = (corner_back[0] - nrm[0] * court_rng.uniform(5, 9), corner_back[1] - nrm[1] * court_rng.uniform(5, 9))
                seg = LineString([corner_back, end]).intersection(free.buffer(-0.3))
                seg = max(parts(seg, 'LineString'), key=lambda q: q.length) if not seg.is_empty and parts(seg, 'LineString') else None
                if seg is not None and seg.length > 3:
                    W.add_fence(f'05_v17_yard_fence_{k + 1:03d}', 'fence_wood_yard', list(seg.coords), 'old_town', 1.8)
                    free = free.difference(seg.buffer(0.8))
        courts.append(free)
    court_items = collections.Counter()

    def place_court(part, pt, r, k):
        rr = rng_for(f'court{k}')
        u = edge_dir_near(part, pt)
        choice = ['trees', 'cars', 'trees', 'dumpsters', 'garage', 'trees', 'shed', 'cars'][k % 8]
        if choice == 'garage' and r >= 7.5:
            n = int(min(4, max(2, (2 * r - 2) // 3.2)))
            g = orect(pt.x, pt.y, u[0], u[1], n * 3.2, 6.2)
            if part.buffer(0.01).contains(g):
                W.add_building(f'05_G{k:03d}', 'old_town', 'v17_garage', 'metal_garage_row', g, 1, GARAGE_H, GARAGE_H,
                               [(pt.x + u[1] * 3.1, pt.y - u[0] * 3.1)], extra=dict(recipe='court_garage'))
                court_items['garage'] += 1
                return g.buffer(4.5)
        if choice == 'cars' and r >= 3.5:
            n = int(min(4, max(1, (2 * r - 1) // 2.7)))
            used = car_row(W, part, pt, u, n, rr, False, perpendicular=True)
            if used is not None:
                court_items['cars'] += n
                return used.buffer(1.5)
        if choice == 'dumpsters' and r >= 2.5:
            pad = orect(pt.x, pt.y, u[0], u[1], 5.0, 2.4)
            for i in (-1, 0, 1):
                W.add_prop('prop/garbage_container_closed' if i else 'prop/garbage_container_open', pt.x + u[0] * i * 1.6, pt.y + u[1] * i * 1.6, unity_yaw(-u[1], u[0]), foot=(1.2, 1.5), tag='dumpster')
            W.add_pad(pad.buffer(0.5), 'concrete', 'v17_dumpster_pad')
            court_items['dumpsters'] += 1
            return pad.buffer(2.0)
        if choice == 'shed' and r >= 3.5:
            g = orect(pt.x, pt.y, u[0], u[1], 3.2, 2.6)
            W.add_building(f'05_S{k:03d}', 'old_town', 'v17_shed', 'shed', g, 1, 2.5, 2.5, [(pt.x - u[1] * 1.3, pt.y + u[0] * 1.3)], roof='gable', extra=dict(recipe='shed'))
            court_items['shed'] += 1
            return g.buffer(2.5)
        rc = min(r - 0.8, 7.0)
        court_items['tree_clusters'] += 1
        return tree_disc(W, part, pt, max(rc, 1.5), 5.0, ['linden', 'oak', 'linden', 'poplar'], (7, 11), rr)

    for free in courts:
        greedy_fill(free.buffer(-0.5), place_court, 4.5)
    # Parks inside blocks become courtyard gardens behind the new street walls.
    trimmed = []
    for s in d['structures']:
        if s['district_id'] == 'old_town' and s['kind'] == 'park_lawn':
            g0 = valid(Polygon(s['polygon_m']))
            g1 = largest(g0.difference(lots_u.buffer(1.0)).difference(W.occupied().buffer(0.5)))
            if g1 is None or g1.area < 60:
                trimmed.append((s['id'], R(g0.area), 0))
                s['polygon_m'] = None
                s['v17_status'] = 'removed: covered by the street wall / courtyard buildings'
            elif g1.area < g0.area - 1:
                trimmed.append((s['id'], R(g0.area), R(g1.area)))
                s['polygon_m'] = [[R(x), R(y)] for x, y in orient(g1.simplify(0.2), 1).exterior.coords[:-1]]
    d['structures'] = [s for s in d['structures'] if not (s['kind'] == 'park_lawn' and s.get('polygon_m') is None)]
    dev('Downtown park lawns trimmed to the courtyards behind the new street walls (id, m2 before -> after): ' + ', '.join(f'{a} {b}->{c}' for a, b, c in trimmed))
    pockets = 0
    for q in park_pois:
        if lots_u.distance(q) > 9 or not any(P.distance(q) < 4 for P in blocks if P is not plaza):
            continue
        rr = rng_for(f'pocket{q.x:.0f}{q.y:.0f}')
        spot = q.buffer(7.0).difference(lots_u.buffer(1.0)).difference(W.occupied(1.0)).difference(W.corridor)
        placed_t = 0
        for ang in (30, 150, 270):
            x, y = q.x + 3.6 * math.cos(math.radians(ang)), q.y + 3.6 * math.sin(math.radians(ang))
            if spot.contains(Point(x, y).buffer(1.0)):
                W.add_tree('linden' if placed_t % 2 else 'oak', x, y, rr.uniform(7.5, 9.5))
                placed_t += 1
        if spot.contains(q.buffer(1.2)):
            W.add_prop('prop/bench_park', q.x, q.y, float(rr.integers(0, 4)) * 90, foot=(0.7, 1.9), tag='bench')
        pockets += 1
    dev(f'{pockets} Downtown "park / square" POIs on block edges kept as pocket squares in the street wall (lots stop 7.5 m short); POI 03 parking ramps kept clear.')
    plaza_fill(W, plaza, keep)
    return dict(pockets=pockets, lots=len(lots), annexes=annex_no, court_items=dict(court_items), blocks=len(blocks), fire=len(fire), tanks=len(tanks), boards=len(boards))


def plaza_fill(W, P, keep):
    """Central square: <= 40 x 40 m open paving round the fountain; a tree-lined square, market stalls, kiosks, benches,
    lamps and a clock column fill the rest (CLOCK_SQUARE and the P11 ATM stay clear)."""
    rng = rng_for('plaza')
    core = box(848, 360, 888, 400)
    bld = unary_union([geom(b) for b in keep.values()]).buffer(3.0)
    clear = unary_union([Point(807.6, 394.6).buffer(4.5), Point(884.8, 410.2).buffer(3.0), Point(805.8, 447.6).buffer(6.0), core])
    W.add_prop('prop/fountain', 868, 370.6, 0, foot=(7, 7), tag='fountain')
    W.add_prop('proc/clock_column', 807.6, 394.6, 90, foot=(1.6, 1.6), tag='monument')
    stalls = box(826, 377, 844, 411)
    for x, face in ((829.5, 90), (840.5, 270)):
        for i in range(7):
            y = 379.5 + i * 4.6
            W.add_prop('prop/market_stall', x, y, face, foot=(2.6, 3.2), tag='stall')
    W.add_pad(stalls.buffer(1), 'paving', 'v17_market')
    kiosks = [('prop/news_kiosk', 897, 381, 270), ('prop/kiosk', 907, 386, 270), ('prop/kiosk', 897, 398, 270), ('prop/atm_pavilion', 907, 403, 270), ('prop/ad_column', 902, 391.5, 0)]
    kiosk_zone = box(892, 377, 912, 408)
    for k, x, y, yaw in kiosks:
        W.add_prop(k, x, y, yaw, foot=(2.8, 3.0), tag='kiosk')
    block = P.buffer(-2.5).difference(bld).difference(clear.buffer(2.0)).difference(stalls.buffer(2.5)).difference(kiosk_zone.buffer(2.5))
    walk = unary_union([box(864, 300, 872, 470), box(780, 376, 960, 384)])
    n_trees = 0
    for j in range(20):
        for i in range(20):
            x, y = 801 + i * 8.5, 359 + j * 8.5
            p = Point(x, y)
            if block.contains(p) and not walk.contains(p):
                W.add_tree('linden' if (i + j) % 3 else 'oak', x, y, 8.5 + ((i * 7 + j * 3) % 5) * 0.5)
                n_trees += 1
                if (i + j) % 2 == 0 and block.contains(Point(x + 4.2, y)):
                    W.add_prop('prop/bench_park', x + 4.2, y, 0 if y < 394 else 180, foot=(0.7, 1.9), tag='bench')
    ring = core.buffer(1.2, join_style=2).exterior
    for i in range(16):
        p = ring.interpolate(i / 16, normalized=True)
        if p.distance(Point(884.8, 410.2)) > 3:
            W.add_prop('prop/lamp_oldtown_double' if i % 4 == 0 else 'prop/lamp_oldtown_single', p.x, p.y, 0, foot=(0.4, 0.4), tag='lamp', cast=False)
    for i in range(12):
        p = core.buffer(-1.5, join_style=2).exterior.interpolate((i + 0.5) / 12, normalized=True)
        c = core.centroid
        if p.distance(Point(884.8, 410.2)) > 3 and abs(p.x - 868) > 5 and abs(p.y - 380) > 5:
            W.add_prop('prop/bench_park', p.x, p.y, unity_yaw(c.x - p.x, c.y - p.y), foot=(0.7, 1.9), tag='bench')
    for x, y in ((850.5, 362.5), (885.5, 362.5), (850.5, 397.5)):
        W.add_prop('prop/trashbin_concrete', x, y, 0, foot=(0.6, 0.6), tag='bin', cast=False)
    dev(f'Central plaza filled: open paving limited to the 40 x 40 m core (848-888 x 360-400) round the fountain at POI 15 (868, 370.6); {n_trees} square trees, 14 market stalls, '
        f'5 kiosks/ATM/ad column, benches, lamps, a clock column at CLOCK_SQUARE (807.6, 394.6). CLOCK_SQUARE and P11 keep their coordinates and clearance.')


# ---------------------------------------------------------------- street dressing
def offset_points(l, off, spacing, phase):
    """(x, y, ux, uy) every `spacing` m along the parallel of l at `off` (shapely: + = left)."""
    out = []
    try:
        par = l.offset_curve(off, join_style=2)
    except Exception:
        return out
    for seg in parts(par, 'LineString'):
        if seg.length < 2:
            continue
        s = phase
        while s < seg.length - 1:
            p, q = seg.interpolate(max(0, s - 0.5)), seg.interpolate(min(seg.length, s + 0.5))
            L = math.dist(p.coords[0], q.coords[0]) or 1
            c = seg.interpolate(s)
            out.append((c.x, c.y, (q.x - p.x) / L, (q.y - p.y) / L))
            s += spacing
    return out


def street_dressing(W, district, ids, rough):
    rng = rng_for('street-' + district)
    zone = PHASE_A[district].buffer(2)
    bld = unary_union([g for g, t in W.solid if t == 'building'])
    occ = W.occupied().buffer(0.8)
    stops = []
    counts = collections.Counter()

    def near_node(p, dist):
        return any(p.distance(n) < dist for n in W.nodes) or any(p.distance(n) < dist * 0.6 for n in W.ends)

    roads = [(r, l) for r, l in W.roads if r['id'] in ids]
    # Bus stops first (they keep a clear stretch for the bus).
    sidewalk = W.corridor.difference(W.carriage).buffer(-0.3)
    plan_stops = []
    by_id = {r['id']: (r, l) for r, l in roads}
    if district == 'old_town':
        poi = Point(892.0, 355.6)          # Vadim's POI 05:14 'bus stop'
        r, l = min(roads, key=lambda q: q[1].distance(poi))
        s = l.project(poi)
        c, q = l.interpolate(s), l.interpolate(min(l.length, s + 1))
        side = 1 if (q.x - c.x) * (poi.y - c.y) - (q.y - c.y) * (poi.x - c.x) > 0 else -1
        plan_stops += [(r, l, s, side)]
        if '05_N' in by_id:
            plan_stops.append((*by_id['05_N'], by_id['05_N'][1].length * 0.5, 1))
    elif '04_drive' in by_id:
        plan_stops.append((*by_id['04_drive'], by_id['04_drive'][1].length * 0.5, 1))
    for r, l, s, side in plan_stops:
            if True:
                c = l.interpolate(s)
                q = l.interpolate(min(l.length, s + 1))
                ux, uy = (q.x - c.x), (q.y - c.y)
                L = math.hypot(ux, uy) or 1
                ux, uy = ux / L, uy / L
                nx, ny = -uy * side, ux * side
                off = r['width_m'] / 2 + ((r.get('sidewalk_width_m') or 0) * 0.62 if r.get('sidewalk_width_m') else 2.6)
                x, y = c.x + nx * off, c.y + ny * off
                if not zone.contains(Point(x, y)) or bld.distance(Point(x, y)) < 1.0 or near_node(Point(x, y), 16):
                    continue
                W.add_prop('prop/busstop_shelter_vandalised' if rough else 'prop/busstop_shelter', x, y, unity_yaw(-nx, -ny), foot=(1.6, 4.0), tag='busstop')
                W.add_prop('prop/bus_stop_sign', x + ux * 3.2, y + uy * 3.2, unity_yaw(-nx, -ny), solid=False, cast=False)
                stops.append(Point(c.x + nx * r['width_m'] / 2, c.y + ny * r['width_m'] / 2))
                counts['bus_stops'] += 1
    stop_zone = unary_union([p.buffer(14) for p in stops]) if stops else Polygon()
    for r, l in roads:
        w = r['width_m']
        sw = r.get('sidewalk_width_m') or 0
        for side in (1, -1):
            # Parked cars on the carriageway by the kerb (town streets) or on the verge (the rural yard drive).
            car_off = (w / 2 - 1.0) if not rough else (w / 2 + 1.4)
            gap_run = 0
            for x, y, ux, uy in offset_points(l, side * car_off, 6.0, 3.0 + rng.uniform(0, 2)):
                p = Point(x, y)
                if not zone.contains(p) or near_node(p, 13.5) or stop_zone.contains(p) or W.driveways.buffer(4).contains(p) or W.police.buffer(4).contains(p):
                    continue
                if any(p.distance(q) < 5 for q in W.points):
                    continue
                if rough and occ.intersects(orect(x, y, ux, uy, 4.6, 2.0)):
                    continue
                if not rough and sidewalk.intersects(orect(x, y, ux, uy, 4.5, 1.9)):
                    continue
                gap_run += 1
                if rng.random() < (0.3 if not rough else 0.45) or gap_run > 6:
                    gap_run = 0
                    continue
                keys = car_keys(rough)
                hx, hy = (ux, uy) if side < 0 else (-ux, -uy)
                W.add_prop(keys[int(rng.integers(len(keys)))], x, y, unity_yaw(hx, hy), foot=(1.9, 4.5), tag='car_street')
                counts['parked_cars'] += 1
            # Street trees, lamps, bins, hydrants on the kerb strip of the sidewalk.
            if sw >= 2.5:
                for x, y, ux, uy in offset_points(l, side * (w / 2 + 0.9), 11.0, 5.5):
                    p = Point(x, y)
                    if not zone.contains(p) or near_node(p, 10) or stop_zone.contains(p) or bld.distance(p) < 1.6 or W.driveways.buffer(3).contains(p) or W.carriage.buffer(0.6).contains(p):
                        continue
                    W.add_tree('linden' if rng.random() < 0.7 else 'oak', x, y, rng.uniform(6.5, 8.5))
                    counts['street_trees'] += 1
                for i, (x, y, ux, uy) in enumerate(offset_points(l, side * (w / 2 + 0.4), 23.0, 0.0)):
                    p = Point(x, y)
                    if not zone.contains(p) or near_node(p, 4) or bld.distance(p) < 1.2 or W.carriage.buffer(0.3).contains(p) or W.carriage.buffer(0.3).contains(Point(x + ux * 1.2, y + uy * 1.2)):
                        continue
                    W.add_prop('prop/lamp_oldtown_single', x, y, unity_yaw(-ux * side, -uy * side), foot=(0.35, 0.35), tag='lamp', cast=False)
                    counts['lamps'] += 1
                    if i % 2 == 0:
                        W.add_prop('prop/bin', x + ux * 1.2, y + uy * 1.2, unity_yaw(ux, uy), foot=(0.5, 0.5), tag='bin', cast=False)
                        counts['bins'] += 1
                    if i % 3 == 1:
                        W.add_prop('prop/fire_hydrant', x - ux * 2.0, y - uy * 2.0, 0, solid=False, cast=False)
                        counts['hydrants'] += 1
            elif rough:
                for x, y, ux, uy in offset_points(l, side * (w / 2 + 2.0), 26.0, 8.0):
                    p = Point(x, y)
                    if not zone.contains(p) or near_node(p, 4) or occ.distance(p) < 0.5 or W.carriage.buffer(0.5).contains(p):
                        continue
                    W.add_prop('prop/lamp_soviet' if rng.random() < 0.85 else 'prop/lamp_soviet_broken', x, y, unity_yaw(-ux * side, -uy * side), foot=(0.35, 0.35), tag='lamp', cast=False)
                    counts['lamps'] += 1
                # Poplar/birch rows along the yard drive (both sides), clear of buildings, cars and the carriageway.
                for x, y, ux, uy in offset_points(l, side * (w / 2 + 5.2), 9.0, 2.0 + rng.uniform(0, 3)):
                    p = Point(x, y)
                    if not zone.contains(p) or near_node(p, 10) or occ.buffer(2.5).contains(p) or W.corridor.buffer(1.5).contains(p) or bld.distance(p) < 4:
                        continue
                    W.add_tree('poplar' if rng.random() < 0.55 else 'birch', x, y, rng.uniform(12, 17))
                    counts['drive_trees'] += 1
        # Junction signs (Downtown): give-way / stop 10 m before each node on the right-hand kerb.
        if not rough:
            for n in W.nodes:
                if l.distance(n) > 0.5 or not zone.contains(n):
                    continue
                s_node = l.project(n)
                for s, toward in ((s_node - 10, 1), (s_node + 10, -1)):
                    if s < 3 or s > l.length - 3:
                        continue
                    c = l.interpolate(s)
                    q = l.interpolate(min(l.length, s + 1))
                    ux, uy = q.x - c.x, q.y - c.y
                    L = math.hypot(ux, uy) or 1
                    tx, ty = ux / L * toward, uy / L * toward          # travel direction toward the node
                    off = w / 2 + 0.45
                    x, y = c.x + ty * off, c.y - tx * off                # right-hand side of the travel direction
                    if bld.distance(Point(x, y)) < 1.0:
                        continue
                    W.add_prop('prop/sign_giveway' if (int(n.x) + int(n.y)) % 2 else 'prop/sign_stop', x, y, unity_yaw(-tx, -ty), solid=False, cast=False)
                    counts['signs'] += 1
    return dict(counts)


# ---------------------------------------------------------------- Rough District
def rough(W):
    d = W.d
    rng = rng_for('rough')
    rd = [b for b in d['functional_buildings'] if b['district_id'] == 'residential']
    split = []
    for b in rd:
        g = geom(b)
        if b['world_kind'] == 'panel_block':
            md, Md = min_dim(g)
            if len(b['footprint_m']) == 4 and Md > 48:
                rr = g.minimum_rotated_rectangle
                c = list(rr.exterior.coords)
                e0 = (c[1][0] - c[0][0], c[1][1] - c[0][1])
                e1 = (c[2][0] - c[1][0], c[2][1] - c[1][1])
                long_e = e0 if math.hypot(*e0) >= math.hypot(*e1) else e1
                Lx = math.hypot(*long_e)
                u = (long_e[0] / Lx, long_e[1] / Lx)
                ct = rr.centroid
                n = math.ceil(Md / 40)
                seg = Md / n
                ids = []
                for i in range(n):
                    s = -Md / 2 + seg * (i + 0.5)
                    off = 0.75 * (1 if i % 2 else -1)
                    cx, cy = ct.x + u[0] * s - u[1] * off, ct.y + u[1] * s + u[0] * off
                    sec = orect(cx, cy, u[0], u[1], seg, md)
                    bid = b['id'] if i == 0 else f"{b['id']}_s{i + 1}"
                    W.add_building(bid, 'residential', 'panel_block', 'panel_block', sec, b['storeys'], STOREY, STOREY, [], label=b['label_ru'] if i == 0 else '',
                                   roof_colour=b.get('roof_colour'), extra=dict(recipe='panel_section', source=b['id']))
                    ids.append(bid)
                split.append((b['id'], R(Md), n))
                continue
        is_garage = b['world_kind'] == 'metal_garage_row'
        W.scale_building(b, None, GARAGE_H if is_garage else (3.0 if b['world_kind'] == 'low_shop_or_kiosk' else STOREY), GARAGE_H if is_garage else STOREY)
        W.solid.append((g, 'building'))
    dev('Rough District panel blocks over 48 m split into 1.5 m-staggered sections (id, length m, sections): ' + ', '.join(f'{a} {b} {c}' for a, b, c in split))
    # Entrances every 12-16 m on the yard side, each with a canopy (facade grammar), a bench and a bin.
    panels = [b for b in W.buildings.values() if b['district_id'] == 'residential' and b['world_kind'] == 'panel_block' and b['storeys'] >= 4]
    bld = unary_union([geom(b) for b in W.buildings.values() if b['district_id'] == 'residential'])
    corridors, facades = [], []
    gardens = n_doors = 0
    for b in sorted(panels, key=lambda q: q['id']):
        g = orient(geom(b), 1)
        cs = list(g.exterior.coords)
        cands = []
        for a, c in zip(cs, cs[1:]):
            L = math.dist(a, c)
            if L < 11.5:
                continue
            u = ((c[0] - a[0]) / L, (c[1] - a[1]) / L)
            nrm = (u[1], -u[0])
            free = 0
            for t in (0.2, 0.5, 0.8):
                for dist in (6, 12, 18):
                    p = Point(a[0] + u[0] * L * t + nrm[0] * dist, a[1] + u[1] * L * t + nrm[1] * dist)
                    if not W.corridor.buffer(2).contains(p) and not bld.contains(p) and RD_BOX.buffer(10).contains(p):
                        free += 1
            cands.append((free, L, a, u, nrm))
        cands.sort(key=lambda q: (-q[0], -q[1]))
        use = [q for q in cands if q[0] >= 5][:1 if len(cs) <= 5 else 2]
        doors = []
        for free, L, a, u, nrm in use:
            k = max(1, math.ceil(L / 16))
            mine = []
            for i in range(k):
                s = L * (i + 0.5) / k
                p = (a[0] + u[0] * s, a[1] + u[1] * s)
                mine.append(p)
                n_doors += 1
                corridors.append(orect(p[0] + nrm[0] * 4, p[1] + nrm[1] * 4, nrm[0], nrm[1], 8, 3.2))
                bx, by = p[0] + nrm[0] * 3.2 + u[0] * 2.4, p[1] + nrm[1] * 3.2 + u[1] * 2.4
                W.add_prop('prop/bench_soviet' if rng.random() < 0.8 else 'prop/bench_soviet_broken', bx, by, unity_yaw(-u[0], -u[1]), foot=(0.7, 1.9), tag='bench')
                W.add_prop('prop/trashbin_concrete', p[0] + nrm[0] * 1.9 - u[0] * 1.7, p[1] + nrm[1] * 1.9 - u[1] * 1.7, 0, foot=(0.6, 0.6), tag='bin', cast=False)
            doors += mine
            facades.append((b, a, u, nrm, L, k, mine))
        if doors:
            b['entrance_m'] = [R(doors[0][0]), R(doors[0][1])]
            b['v17']['doors'] = [[R(x), R(y)] for x, y in doors]
            b['entrance_status'] = 'v17: entrances every 12-16 m on the yard side'
    for s in d['structures']:
        if s['id'] == '04_football_pitch':
            g = orient(valid(Polygon(s['polygon_m'])).buffer(1.5, join_style=2), 1)
            c = g.centroid
            p0 = g.exterior.interpolate(g.exterior.project(Point(c.x, c.y - 40)))
            W.add_fence('04_v17_pitch_fence', 'fence_chainlink', list(g.exterior.coords), 'residential', 2.4, gates=[(p0.x, p0.y, 3.0)], closed=True)
    pts_clear = unary_union([p.buffer(4) for p in W.points if RD_BOX.buffer(20).contains(p)] +
                            [Point(q['position_m']).buffer(14) for q in d['points'] if q['category'] == 'base'])
    special = unary_union([valid(Polygon(s['polygon_m'])).buffer(3) for s in d['structures'] if s['id'] == '04_football_pitch'])
    base_zone = RD_BOX.intersection(W.land).difference(W.corridor.buffer(2.5)).difference(unary_union(corridors))
    base_zone = base_zone.difference(pts_clear).difference(special).difference(W.water.buffer(4))
    items = collections.Counter()
    state = dict(kg=False, k=0, play=0, garage=0)
    big_items = []

    def place_big(part, pt, r, k):
        rr = rng_for(f'roughbig{k}')
        u = edge_dir_near(part, pt)
        if not state['kg'] and r >= 11.5:
            state['kg'] = True
            yl, yw = min(40, 2 * r - 1), min(30, 2 * r - 4)
            yard = largest(orect(pt.x, pt.y, u[0], u[1], yl, yw).intersection(part))
            kg = orect(pt.x - u[1] * (yw / 2 - 5.5), pt.y + u[0] * (yw / 2 - 5.5), u[0], u[1], min(24, yl - 3), 9)
            if yard is not None and yard.buffer(0.2).contains(kg):
                W.add_building('04_v17_kindergarten', 'residential', 'v17_kindergarten', 'kindergarten', kg, 2, 3.0, STOREY,
                               [(kg.centroid.x + u[1] * 5.1, kg.centroid.y - u[0] * 5.1)], extra=dict(recipe='kindergarten'))
                yard = orient(yard, 1)
                gate = yard.exterior.interpolate(yard.exterior.project(Point(pt.x + u[1] * 30, pt.y - u[0] * 30)))
                W.add_fence('04_v17_kindergarten_fence', 'fence_kindergarten', list(yard.exterior.coords), 'residential', 1.5, gates=[(gate.x, gate.y, 2.4)], closed=True)
                play_c = (pt.x + u[1] * (yw / 2 - 8), pt.y - u[0] * (yw / 2 - 8))
                for j, key in enumerate(['prop/play_swings', 'prop/play_slide', 'prop/play_sandbox', 'prop/play_carousel']):
                    x, y = play_c[0] + u[0] * (-10 + j * 6.5), play_c[1] + u[1] * (-10 + j * 6.5)
                    if yard.buffer(-1.5).contains(Point(x, y)):
                        W.add_prop(key, x, y, unity_yaw(*u), foot=(2.4, 2.8), tag='play')
                W.add_pad(orect(play_c[0], play_c[1], u[0], u[1], min(30, yl - 6), 7).intersection(yard), 'rubber', 'v17_kindergarten_play')
                for j in range(5):
                    x, y = pt.x + u[0] * (-yl / 2 + 3 + j * (yl - 6) / 4) + u[1] * (yw / 2 - 2.5), pt.y + u[1] * (-yl / 2 + 3 + j * (yl - 6) / 4) - u[0] * (yw / 2 - 2.5)
                    if yard.buffer(-1).contains(Point(x, y)):
                        W.add_tree('linden', x, y, rr.uniform(8, 11))
                items['kindergarten'] += 1
                big_items.append(yard)
                return yard.buffer(2.0)
        if state['play'] < 2 and r >= 9.5 and (state['garage'] >= state['play'] or r < 10.5):
            g = orect(pt.x, pt.y, u[0], u[1], 16, 12)
            if part.contains(g):
                state['play'] += 1
                for j, key in enumerate(['prop/play_swings', 'prop/play_slide', 'prop/play_horizontal_bar', 'prop/play_sandbox', 'prop/play_carpet_rack']):
                    sx_, sy_ = -5.5 + (j % 3) * 5.5, (2.8 if j < 3 else -2.8)
                    W.add_prop(key, pt.x + u[0] * sx_ + u[1] * sy_, pt.y + u[1] * sx_ - u[0] * sy_, unity_yaw(*u), foot=(2.2, 2.8), tag='play')
                W.add_pad(g.buffer(-0.6), 'rubber', 'v17_playground')
                gate = g.exterior.interpolate(0.12, normalized=True)
                W.add_fence(f'04_v17_playground_{k:03d}', 'fence_low_garden', list(orient(g, 1).exterior.coords), 'residential', 0.9, gates=[(gate.x, gate.y, 1.6)], closed=True)
                for s in (-1, 1):
                    W.add_prop('prop/bench_soviet', pt.x + u[1] * s * 7.4, pt.y - u[0] * s * 7.4, unity_yaw(-u[1] * s, u[0] * s), foot=(0.7, 1.9), tag='bench')
                items['playgrounds'] += 1
                big_items.append(g)
                return g.buffer(2.5)
        if state['garage'] < 3 and r >= 7.5:
            n = int(min(10, max(4, (2 * r - 3) // 3.2)))
            g = orect(pt.x, pt.y, u[0], u[1], n * 3.2, 6.2)
            if part.contains(g):
                for sgn in (1, -1):
                    apron = orect(pt.x + u[1] * 6.6 * sgn, pt.y - u[0] * 6.6 * sgn, u[0], u[1], n * 3.2, 7.0)
                    if part.buffer(2).contains(apron):
                        break
                state['garage'] += 1
                ax, ay = apron.centroid.x - pt.x, apron.centroid.y - pt.y
                W.add_building(f'04_v17_garages_{k:03d}', 'residential', 'v17_garage', 'metal_garage_row', g, 1, GARAGE_H, GARAGE_H,
                               [(pt.x + ax * 0.47, pt.y + ay * 0.47)], extra=dict(recipe='garage_row'))
                W.add_pad(apron, 'gravel', 'v17_garage_apron')
                if rr.random() < 0.6:
                    W.add_prop(car_keys(True)[int(rr.integers(7))], apron.centroid.x, apron.centroid.y, unity_yaw(-ay, ax), foot=(1.9, 4.5), tag='car')
                items['garage_rows'] += 1
                big_items.append(g.union(apron))
                return g.union(apron).buffer(1.5)
        return pt.buffer(min(r, 4.0))

    greedy_fill(base_zone.difference(W.occupied(3.0)), place_big, 7.5, max_items=40)
    big_u = unary_union(big_items).buffer(1.5) if big_items else Polygon()
    # Facade dressing: bushes (gaps at the doors), front-garden fences between entrances, a tree row on the yard side.
    facade_band = []
    for b, a, u, nrm, L, k, mine in facades:
        for s in np.arange(1.5, L - 1, 2.6):
            x, y = a[0] + u[0] * s + nrm[0] * 1.6, a[1] + u[1] * s + nrm[1] * 1.6
            p = Point(x, y)
            if any(p.distance(Point(q)) < 2.6 for q in mine) or W.corridor.buffer(0.5).contains(p) or big_u.contains(p):
                continue
            W.add_tree('bush', x, y, rng.uniform(1.3, 2.2))
        cuts = [0.0] + [L * (i + 0.5) / k for i in range(k)] + [L]
        for j in range(len(cuts) - 1):
            s0 = cuts[j] + (2.3 if j > 0 else 0.8)
            s1 = cuts[j + 1] - (2.3 if j < len(cuts) - 2 else 0.8)
            if s1 - s0 < 4 or rng.random() < 0.45:
                continue
            line = [(a[0] + u[0] * s0, a[1] + u[1] * s0), (a[0] + u[0] * s0 + nrm[0] * 3.4, a[1] + u[1] * s0 + nrm[1] * 3.4),
                    (a[0] + u[0] * s1 + nrm[0] * 3.4, a[1] + u[1] * s1 + nrm[1] * 3.4), (a[0] + u[0] * s1, a[1] + u[1] * s1)]
            if W.corridor.buffer(1).intersects(LineString(line)) or big_u.intersects(LineString(line)):
                continue
            gardens += 1
            W.add_fence(f"04_v17_garden_{b['id']}_{gardens}", 'fence_low_garden', line, 'residential', 0.9)
        for s in np.arange(4.0, L - 2, 8.0):
            x, y = a[0] + u[0] * s + nrm[0] * 6.8, a[1] + u[1] * s + nrm[1] * 6.8
            p = Point(x, y)
            if any(p.distance(Point(q)) < 3.5 for q in mine) or W.corridor.buffer(2.5).contains(p) or bld.distance(p) < 4 or W.occupied(1.5).contains(p):
                continue
            W.add_tree('poplar' if rng.random() < 0.5 else 'birch', x, y, rng.uniform(11, 17))
        facade_band.append(orect(a[0] + u[0] * L / 2 + nrm[0] * 4.5, a[1] + u[1] * L / 2 + nrm[1] * 4.5, u[0], u[1], L, 9))
    dev(f'Rough District: {n_doors} panel entrances on the yard sides (12-16 m apart), {gardens} fenced front gardens; the entrance proposal of each panel block moved from the road-facing edge to the yard side.')
    cycle_mid = ['trees', 'trees', 'dumpsters', 'trees', 'laundry', 'trees', 'sheds', 'cars', 'trees', 'transformer', 'trees', 'cars']

    def place(part, pt, r, k):
        rr = rng_for(f'rough{k}')
        u = edge_dir_near(part, pt)
        state['k'] += 1
        choice = cycle_mid[state['k'] % len(cycle_mid)]
        if choice == 'cars' and r >= 4:
            n = int(min(6, max(2, (2 * r - 2) // 2.7)))
            used = car_row(W, part, pt, u, n, rr, True, perpendicular=True)
            if used is not None:
                items['yard_cars'] += n
                return used.buffer(1.0)
        if choice == 'dumpsters':
            pad = orect(pt.x, pt.y, u[0], u[1], 5.4, 2.6)
            if part.buffer(0.5).contains(pad):
                W.add_prop('proc/dumpster_pad', pt.x, pt.y, unity_yaw(*u), foot=(2.6, 5.4), tag='dumpster')
                for i in (-1, 0, 1):
                    W.add_prop('prop/garbage_container_closed' if i else 'prop/garbage_container_open', pt.x + u[0] * i * 1.65, pt.y + u[1] * i * 1.65, unity_yaw(-u[1], u[0]), solid=False)
                W.add_pad(pad.buffer(0.6), 'concrete', 'v17_dumpster_pad')
                items['dumpster_pads'] += 1
                return pad.buffer(3.0)
        if choice == 'laundry' and r >= 3.5:
            W.add_prop('proc/laundry_poles', pt.x, pt.y, unity_yaw(*u), foot=(0.4, 6.4), tag='laundry')
            W.add_prop('prop/carpet_rack', pt.x + u[1] * 3.0, pt.y - u[0] * 3.0, unity_yaw(*u), foot=(0.4, 2.6), tag='rack')
            items['laundry_poles'] += 1
            return pt.buffer(5.0)
        if choice == 'sheds':
            used = []
            for i in range(3):
                g = orect(pt.x + u[0] * (i - 1) * 3.6, pt.y + u[1] * (i - 1) * 3.6, u[0], u[1], 3.2, 3.0)
                if part.contains(g):
                    W.add_building(f'04_v17_shed_{k:03d}_{i}', 'residential', 'v17_shed', 'shed', g, 1, 2.4, 2.4,
                                   [(g.centroid.x - u[1] * 1.5, g.centroid.y + u[0] * 1.5)], roof='gable', extra=dict(recipe='shed'))
                    used.append(g)
            if used:
                items['sheds'] += len(used)
                return unary_union(used).buffer(2.5)
        if choice == 'transformer':
            g = orect(pt.x, pt.y, u[0], u[1], 4.0, 3.0)
            if part.contains(g):
                W.add_building(f'04_v17_transformer_{k:03d}', 'residential', 'v17_transformer', 'shed', g, 1, 3.0, 3.0,
                               [(pt.x - u[1] * 1.5, pt.y + u[0] * 1.5)], extra=dict(recipe='transformer_kiosk'))
                items['transformers'] += 1
                return g.buffer(2.5)
        rc = min(r - 1.0, 9.0)
        items['tree_clusters'] += 1
        return tree_disc(W, part, pt, max(rc, 2.0), 5.2, ['poplar', 'birch', 'birch', 'poplar', 'linden'], (10, 16), rr, under=0.25)

    zone = base_zone.difference(W.occupied(2.5)).difference(unary_union(facade_band)).difference(unary_union([Point(x, y).buffer(2.5) for x, y in W.tree_pts]))
    greedy_fill(zone, place, 5.0)
    return dict(items=dict(items), doors=n_doors, gardens=gardens, split=len(split))


# ---------------------------------------------------------------- common land around the phase-A districts
COMMON = box(525, 222, 1132, 732)


def common_land(W):
    d = W.d
    others = unary_union([box(*q['bbox_m'][0], *q['bbox_m'][1]).buffer(12) for q in d['districts'] if q['id'] not in PHASE_A])
    dense = unary_union([valid(Polygon(z['polygon_m'])) for z in d['vegetation_hints']['forest_zones'] if z['density'] == 'dense'])
    ridge = valid(Polygon(d['terrain_hints']['ridge']['out_of_bounds_polygon_m']))
    struct = unary_union([valid(Polygon(s['polygon_m'])).buffer(3) for s in d['structures'] if s.get('polygon_m') and s['district_id'] not in PHASE_A])
    pts = unary_union([p.buffer(8) for p in W.points])
    base_excl = unary_union([DT_BOX.buffer(5), RD_BOX.buffer(5), others, W.water.buffer(7), W.sand.buffer(5), W.decks.buffer(10), ridge.buffer(4), struct, pts])
    region = COMMON.intersection(W.land.buffer(-6))
    counts = collections.Counter()
    rng = rng_for('common')
    common_roads = [(r, l) for r, l in W.roads if r['district_id'] == 'common' and r['van_access'] and r['class'] in ('rural_road', 'highway') and l.intersects(COMMON)]
    # Tree tunnels: rows both sides of the inter-district roads.
    for r, l in common_roads:
        for side in (1, -1):
            for x, y, ux, uy in offset_points(l, side * (r['width_m'] / 2 + 4.2), 8.5, 4.0 + rng.uniform(0, 3)):
                p = Point(x, y)
                if not region.contains(p) or base_excl.contains(p) or dense.contains(p) or any(p.distance(n) < 18 for n in W.nodes) or W.corridor.buffer(3.0).contains(p):
                    continue
                if W.occupied().distance(p) < 2 if counts['tunnel'] % 25 == 0 else False:
                    continue
                W.add_tree(['birch', 'poplar', 'linden', 'birch', 'oak'][int(rng.integers(5))], x, y, rng.uniform(10, 15))
                counts['tunnel'] += 1
    # Billboards along the inter-district roads (every ~160 m, alternating sides, facing the road).
    for r, l in common_roads:
        s, side = 60.0, 1
        while s < l.length - 40:
            c = l.interpolate(s)
            q = l.interpolate(s + 1)
            ux, uy = q.x - c.x, q.y - c.y
            L = math.hypot(ux, uy) or 1
            ux, uy = ux / L, uy / L
            nx, ny = -uy * side, ux * side
            x, y = c.x + nx * (r['width_m'] / 2 + 9), c.y + ny * (r['width_m'] / 2 + 9)
            p = Point(x, y)
            if region.contains(p) and not base_excl.contains(p) and W.corridor.buffer(4).disjoint(p.buffer(3)) and W.occupied().distance(p) > 4:
                W.add_prop('prop/billboard_large', x, y, unity_yaw(-nx, -ny), foot=(1.0, 6.0), tag='billboard')
                counts['billboards'] += 1
            s += 160
            side = -side
    # A power line across the common land north of Downtown (lattice pylons every ~55 m; wires drawn between them).
    line = LineString([(548, 505), (690, 498), (812, 545), (935, 505), (1128, 500)])
    s, idx = 10.0, 0
    pylons = []
    while s < line.length:
        p = line.interpolate(s)
        q = line.interpolate(min(line.length, s + 1))
        if region.contains(p) and not base_excl.buffer(2).contains(p) and W.corridor.buffer(6).disjoint(p) and W.occupied().distance(p) > 5:
            ux, uy = q.x - p.x, q.y - p.y
            L = math.hypot(ux, uy) or 1
            W.add_prop('proc/pylon', p.x, p.y, unity_yaw(ux / L, uy / L), foot=(5.5, 5.5), tag='pylon')
            pylons.append([R(p.x), R(p.y)])
            idx += 1
        s += 55
    counts['pylons'] = idx
    # Rooms of the common land: garage cooperative, allotments, forest belts with undergrowth, hedgerows.
    zone = region.difference(base_excl).difference(W.corridor.buffer(4.5)).difference(W.occupied(3.0)).difference(dense)
    zone = zone.difference(unary_union([Point(x, y).buffer(3.5) for x, y in W.tree_pts]))
    state = dict(coop=0, allot=0)
    rough_near = RD_BOX.buffer(140)

    def place(part, pt, r, k):
        rr = rng_for(f'common{k}')
        u = edge_dir_near(part, pt)
        road_d = W.carriage.distance(pt)
        if state['coop'] < 1 and r >= 24 and rough_near.contains(pt) and road_d < 70:
            g = orect(pt.x, pt.y, u[0], u[1], 46, 38)
            if part.contains(g):
                state['coop'] += 1
                for j, off in enumerate((-12.5, 12.5)):
                    row = orect(pt.x - u[1] * off, pt.y + u[0] * off, u[0], u[1], 12 * 3.2, 6.2)
                    door = (pt.x - u[1] * off * 0.55, pt.y + u[0] * off * 0.55)
                    W.add_building(f'CL_v17_garage_coop_{j + 1}', 'residential', 'v17_garage', 'metal_garage_row', row, 1, GARAGE_H, GARAGE_H, [door], zone='common', extra=dict(recipe='garage_cooperative'))
                W.add_pad(orect(pt.x, pt.y, u[0], u[1], 40, 20), 'gravel', 'v17_garage_coop_lane')
                gate = g.exterior.interpolate(g.exterior.project(W.carriage.boundary.interpolate(W.carriage.boundary.project(pt))))
                W.add_fence('CL_v17_garage_coop_fence', 'fence_chainlink', list(orient(g, 1).exterior.coords), 'residential', 2.2, gates=[(gate.x, gate.y, 5.0)], closed=True)
                for j in range(3):
                    W.add_prop(car_keys(True)[int(rr.integers(7))], pt.x + u[0] * (j * 9 - 9), pt.y + u[1] * (j * 9 - 9), unity_yaw(*u), foot=(1.9, 4.5), tag='car')
                counts['garage_coop'] += 1
                return g.buffer(3)
        if state['allot'] < 2 and r >= 20 and rough_near.contains(pt):
            state['allot'] += 1
            used = []
            for i in range(3):
                for j in range(2):
                    cx = pt.x + u[0] * (i - 1) * 15.0 - u[1] * (j - 0.5) * 19.0
                    cy = pt.y + u[1] * (i - 1) * 15.0 + u[0] * (j - 0.5) * 19.0
                    plot = orect(cx, cy, u[0], u[1], 14.2, 18.2)
                    if not part.contains(plot):
                        continue
                    gate = plot.exterior.interpolate(0.06, normalized=True)
                    W.add_fence(f'CL_v17_allotment_{state["allot"]}_{i}{j}', 'fence_dacha', list(orient(plot, 1).exterior.coords), 'residential', 1.3, gates=[(gate.x, gate.y, 1.2)], closed=True)
                    shed = orect(cx + u[0] * 4.0 + u[1] * 5.5, cy + u[1] * 4.0 - u[0] * 5.5, u[0], u[1], 4.2, 3.4)
                    W.add_building(f'CL_v17_dacha_{state["allot"]}_{i}{j}', 'residential', 'v17_dacha', 'shed', shed, 1, 2.6, 2.6,
                                   [(shed.centroid.x - u[1] * 1.7, shed.centroid.y + u[0] * 1.7)], roof='gable', zone='common', extra=dict(recipe='allotment_dacha'))
                    W.add_pad(orect(cx - u[0] * 2.5 - u[1] * 2.0, cy - u[1] * 2.5 + u[0] * 2.0, u[0], u[1], 7.5, 9.0), 'dry_field', 'v17_allotment_beds')
                    for t in range(2):
                        W.add_tree('fruit', cx - u[0] * 4.5 + u[1] * (t * 6 - 3), cy - u[1] * 4.5 - u[0] * (t * 6 - 3), rr.uniform(4.5, 6))
                    used.append(plot)
            if used:
                counts['allotment_plots'] += len(used)
                return unary_union(used).buffer(3)
        # Forest belt: dense crowns with undergrowth; hedgerow lines in the widest meadows.
        if r >= 30 and k % 3 == 0:
            L = 2 * r - 8
            for s in np.arange(-L / 2, L / 2, 3.2):
                x, y = pt.x + u[0] * s, pt.y + u[1] * s
                if part.contains(Point(x, y)):
                    W.add_tree('bush' if int(s) % 3 else ['oak', 'birch', 'linden'][int(rr.integers(3))], x, y, rr.uniform(1.6, 2.6) if int(s) % 3 else rr.uniform(9, 13))
            counts['hedgerows'] += 1
            return orect(pt.x, pt.y, u[0], u[1], L, 10).intersection(part)
        rc = min(r * 0.7, 22.0)
        north = pt.y > 470
        sp = ['pine', 'pine', 'birch', 'spruce', 'birch'] if north else ['birch', 'oak', 'linden', 'pine', 'poplar']
        counts['forest_clumps'] += 1
        g = tree_disc(W, part, pt, max(rc, 4.0), 4.6, sp, (10, 17), rr, under=0.4)
        if g is not None:
            W.add_pad(g.buffer(-1.0), 'forest_floor', 'v17_forest_floor', prio=20)
        return g

    greedy_fill(zone, place, 14.0)
    return dict(counts), pylons


def relief(W):
    """Low-frequency relief: smooth hills/ridges in the common land around the phase-A districts, flat at district envelopes,
    away from water/coasts/bridges/junctions (the look builder grade-limits the roads that cross them)."""
    d = W.d
    rng = rng_for('relief')
    others = unary_union([box(*q['bbox_m'][0], *q['bbox_m'][1]).buffer(20) for q in d['districts']])
    old = unary_union([Point(h['center_m']).buffer(max(h['radii_m']) * 0.9) for h in d['hills']])
    excl = unary_union([others, W.water.buffer(24), W.sand.buffer(16), W.decks.buffer(30), old, unary_union([g for g, t in W.solid if t in ('building', 'fence')]).buffer(8),
                        unary_union([n.buffer(16) for n in W.nodes]), W.land.exterior.buffer(18)])
    allowed = COMMON.buffer(30).intersection(W.land).difference(excl)
    hills = []
    for j in range(17):
        for i in range(20):
            x = 515 + i * 32 + rng.uniform(-9, 9)
            y = 210 + j * 32 + rng.uniform(-9, 9)
            p = Point(x, y)
            if not allowed.contains(p):
                continue
            room = allowed.boundary.distance(p)
            if any(math.dist((x, y), (h['center_m'][0], h['center_m'][1])) < 0.6 * (max(h['radii_m']) + room) for h in hills):
                continue
            rx = min(room, rng.uniform(28, 62))
            if rx < 12:
                continue
            ry = rx * rng.uniform(0.42, 0.85)
            if rng.random() < 0.5:
                rx, ry = ry, rx
            h = R(rng.uniform(4, 13) * min(1.0, max(rx, ry) / 34))
            if h < 3:
                continue
            hills.append(dict(center_m=[R(x), R(y)], radii_m=[R(rx), R(ry)], rotation_deg=0, height_m=h, height_target_m=h,
                              note='v17 relief (common land; flat at district envelopes)', id=f'V17_RELIEF_{len(hills) + 1:02d}'))
    d['hills'] += hills
    dev(f'{len(hills)} low relief hills/ridges (3-13 m, radii 18-62 m) added in the common land round Downtown and the Rough District; '
        'none touch a district envelope, water, coast, bridge or junction; roads crossing them are grade-limited by the look builder (8 %).')
    return hills


# ---------------------------------------------------------------- metrics, samples, outputs
def open_area(W, district, buildings, trees, props_solid, deliberate):
    area = PHASE_A[district].intersection(W.land).difference(W.corridor).difference(W.water)
    obst = unary_union([geom(b) for b in buildings if PHASE_A[district].buffer(30).intersects(geom(b))] +
                       [Point(t['x'], t['y']).buffer(1.2 if t['sp'] == 'bush' else 2.6) for t in trees if PHASE_A[district].buffer(5).contains(Point(t['x'], t['y']))] +
                       props_solid + [deliberate])
    free = area.difference(obst)
    best = 0.0
    for p in parts(free):
        if p.area < 50:
            continue
        _, r = pole(p)
        best = max(best, r)
    return R(best), R(free.area / area.area)


def sightline_samples(W, d16_buildings, n_per=360):
    out = {}
    bl16 = unary_union([geom(b) for b in d16_buildings]).buffer(0.8)
    occ = W.occupied().buffer(0.8)
    trunks = unary_union([Point(x, y).buffer(0.7) for x, y in W.tree_pts])
    for dist, bx in PHASE_A.items():
        rng = rng_for('samples-' + dist)
        x0, y0, x1, y1 = bx.bounds
        pts, cls = [], collections.Counter()
        tries = 0
        while len(pts) < n_per and tries < 40000:
            tries += 1
            p = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
            if not W.land.contains(p) or W.water.buffer(1).contains(p) or bl16.contains(p) or occ.contains(p) or trunks.contains(p):
                continue
            c = 'street' if W.carriage.contains(p) else 'sidewalk' if W.corridor.contains(p) else 'yard'
            # Balance: streets/sidewalks at least a third of the samples.
            if c == 'yard' and cls['yard'] > n_per * 0.6:
                continue
            pts.append([R(p.x), R(p.y), c])
            cls[c] += 1
        out[dist] = dict(points=pts, classes=dict(cls))
    return out


def patch_flats(W, d, look, grey, pylons):
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
    occ = unary_union([geom(b).buffer(1.5) for b in d['functional_buildings'] if b.get('v17')] + [g for g, t in W.solid if t != 'building'])
    mine = unary_union([Point(x, y).buffer(2.4) for x, y in W.tree_pts])
    keep = lambda x, y: not occ.contains(Point(x, y)) and not mine.contains(Point(x, y))
    before = len(look['trees'])
    look['trees'] = [t for t in look['trees'] if keep(t['x'], t['y'])] + W.trees
    grey['tree_data'] = [v for t in look['trees'] for v in (t['x'], t['y'], .3, t['h'])]
    for g, mat, ctx, prio in W.pads:
        look['ground'].append(m16.ground_record(g, mat, ctx, prio))
    look['ground'].sort(key=lambda q: q['prio'])
    look['v17'] = dict(phase='A', props=W.props, pylon_line=pylons,
                       rules=dict(storey_m=STOREY, shop_ground_m=SHOP_GROUND, parapet_max_m=0.6, door_m=[1.1, 2.3], road_grade_max=0.08),
                       note='Props: registry keys (prop/...) or procedural kinds (proc/...); yaw = Unity yaw degrees; solid -> box collider.')
    look['warnings'].append('v17 phase A: Downtown/Rough buildings carry floor_h/ground_h (game scale); other districts unchanged from v16.')
    for p in W.props:
        if p['solid'] and p['k'] not in ('proc/laundry_poles',):
            grey['hedges'].append(dict(x=p['x'], y=p['y'], w=1.8, d=1.8, a=R(90 - p['yaw']), h=1.6, label='v17_prop', source_kind=p['k']))
    return before, len(look['trees'])


def crowd_view(W, d):
    """A copy of the plan for the crowd generator: solid v17 props become closed fence rings (obstacles); open fence lines
    become thin closed rings (the v12 crowd code treats fence polylines as polygons)."""
    dc = dict(d)
    fences = []
    for f in d['fences']:
        if f['id'].startswith(('04_v17', '05_v17', 'CL_v17')) and len(f['polyline_m']) < 4:
            ring = LineString(f['polyline_m']).buffer(0.12, cap_style=2)
            f = dict(f, polyline_m=[[R(x), R(y)] for x, y in ring.exterior.coords])
        fences.append(f)
    k = 0
    for g, tag in W.solid:
        if tag in ('building', 'fence', 'car_street'):
            continue
        k += 1
        ring = [[R(x), R(y)] for x, y in orient(g.buffer(0), 1).exterior.coords] if g.geom_type == 'Polygon' else None
        if ring and len(ring) >= 4:
            fences.append(dict(id=f'CROWD_OBST_{k}', kind='v17_prop_obstacle', polyline_m=ring, gates=[], solid_runs_m=[ring], gap_intervals_m=[], height_target_m=1))
    dc['fences'] = fences
    return dc


def render_png(W, d, dst):
    tmp = REVIEW / '_tmp_render_v17.png'
    tmp2 = REVIEW / '_tmp_overlay_v17.png'
    for t in (tmp, tmp2):
        if t.exists():
            t.unlink()
    info = m16.render(d, tmp, tmp2)
    im = Image.open(tmp).convert('RGB')
    dr = ImageDraw.Draw(im)
    sx, sy, H = info['x_px_per_m'], info['y_px_per_m'], info['height_px']
    px = lambda x, y: (x * sx, H - y * sy)
    for h in d['hills']:
        if h['id'].startswith('V17_RELIEF'):
            (cx, cy), (rx, ry) = h['center_m'], h['radii_m']
            a, b = px(cx - rx, cy + ry), px(cx + rx, cy - ry)
            dr.ellipse([a, b], outline='#8a7a55', width=2)
    for g, mat, ctx, prio in W.pads:
        for p in parts(g):
            dr.polygon([px(x, y) for x, y in p.exterior.coords], fill={'forest_floor': '#b4c3a6', 'rubber': '#c46a5a', 'gravel': '#b9b2a2', 'concrete': '#c9c7c0', 'asphalt': '#8f9594', 'dry_field': '#c8b98a', 'paving': '#d8d0bf'}.get(mat, '#cccccc'))
    for b in d['functional_buildings']:
        if b.get('v17') and b['v17'].get('zone') != 'kept':
            f = b['storeys']
            dr.polygon([px(x, y) for x, y in b['footprint_m']], fill=(150 + f * 14, 120 - f * 8, 95), outline='#3f4a48')
    for t in W.trees:
        x, y = px(t['x'], t['y'])
        r = 1.2 if t['sp'] == 'bush' else 2.2
        dr.ellipse([x - r, y - r, x + r, y + r], fill='#4f7a45' if t['sp'] != 'bush' else '#6f9a5a')
    for p in W.props:
        x, y = px(p['x'], p['y'])
        col = '#2f5f9a' if 'car' in p['k'] or 'van_' in p['k'] else '#7a3d2b' if p['k'].startswith('proc/pylon') else '#555555'
        dr.rectangle([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=col)
    for f in W.fences:
        for run in f['solid_runs_m']:
            if len(run) > 1:
                dr.line([px(x, y) for x, y in run], fill='#5a4632', width=1)
    if Path(dst).exists():
        raise FileExistsError(dst)
    im.save(dst)
    tmp.unlink()
    tmp2.unlink()
    return info


def check(W, d, d16):
    res = {}
    corr = W.corridor.buffer(-0.05)
    bad = [b['id'] for b in d['functional_buildings'] if b.get('v17') and b['v17'].get('zone') != 'kept' and geom(b).intersects(corr)]
    res['buildings_on_road_or_sidewalk'] = bad
    blds = unary_union([geom(b) for b in d['functional_buildings']])
    b16 = unary_union([geom(b) for b in d16['functional_buildings']])
    res['points_newly_inside_buildings'] = [p['id'] for p in d['points'] if blds.contains(Point(p['position_m'])) and not b16.contains(Point(p['position_m']))]
    solid_props = unary_union([g for g, t in W.solid if t not in ('building', 'fence', 'car_street')])
    res['solid_props_on_carriageway'] = dict(collections.Counter(t for g, t in W.solid if t not in ('building', 'fence', 'car_street') and g.intersects(W.carriage.buffer(-0.2))))
    res['street_cars_on_sidewalk'] = int(sum(1 for g, t in W.solid if t == 'car_street' and g.intersects(W.corridor.difference(W.carriage).buffer(-0.3))))
    res['police_lots_clear'] = not blds.intersects(W.police.buffer(-0.3)) and not solid_props.intersects(W.police.buffer(-0.3))
    spawn = [p for p in d['points'] if p['id'] in ('P02', 'B02')]
    res['spawn_clear'] = all(not W.occupied().contains(Point(p['position_m'])) for p in spawn)
    for kind in ('v17_lot', 'panel_block'):
        runs = sorted((R(min_dim(geom(b))[1]), b['id']) for b in d['functional_buildings'] if b['district_id'] in PHASE_A and b['world_kind'] == kind)
        res['max_facade_run_m_' + kind] = runs[-3:] if runs else []
    return res


def district_stats(bs, district):
    fl = sorted(b['storeys'] for b in bs if b['district_id'] == district)
    big = [b for b in bs if b['district_id'] == district and b['world_kind'] not in ('metal_garage_row', 'v17_garage', 'v17_shed', 'v17_annex', 'v17_transformer', 'v17_dacha')]
    fl2 = sorted(b['storeys'] for b in big)
    area = sum(geom(b).area for b in bs if b['district_id'] == district and PHASE_A[district].contains(geom(b).centroid))
    return dict(count=len(fl), main_buildings=len(big), floors_median=float(np.median(fl2)) if fl2 else 0, floors_max=max(fl2) if fl2 else 0,
                floors_hist=dict(collections.Counter(fl2)), built_up_pct=R(100 * area / PHASE_A[district].area),
                height_max_m=R(max(b['height_m'] for b in big)) if big else 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description='R01 v17 phase A')
    ap.add_argument('--out-dir', type=Path, default=MAP)
    ap.add_argument('--dry', action='store_true', help='compute and print metrics only; write nothing')
    a = ap.parse_args(argv)
    out = a.out_dir.resolve()
    names = [STEM + '.json', STEM + '.png', 'Greybox/greybox_v17_flat.json', 'Look/look_v17_flat.json', 'Crowd/crowd_v17.json']
    if not a.dry:
        existing = [str(out / n) for n in names if (out / n).exists()]
        if existing:
            raise FileExistsError('No existing deliverable may be overwritten: ' + ', '.join(existing))
    src = MAP / SRC
    d16 = m16.read(src)
    d = copy.deepcopy(d16)
    W = World(d)
    print('v17: Downtown lots', flush=True)
    dt = downtown(W)
    print('v17: Rough District', flush=True)
    rd = rough(W)
    print('v17: streets', flush=True)
    dt_roads = {r['id'] for r, l in W.roads if r['id'].startswith('05_') and r['van_access']}
    st_dt = street_dressing(W, 'old_town', dt_roads, False)
    st_rd = street_dressing(W, 'residential', {'04_drive'}, True)
    print('v17: common land + relief', flush=True)
    cl, pylons = common_land(W)
    hills = relief(W)
    d['functional_buildings'] = [W.buildings[i] for i in W.order if i in W.buildings]
    d['fences'] = d['fences'] + W.fences
    d['revision'] = REV
    d['title_ru'] = 'VOLUNTEERS ONLY / R01 v17 — World v11, phase A (game scale, density, occlusion)'
    d['provenance'] = dict(d['provenance'], v16_plan=SRC, v16_sha256=m16.sha(src), method_v17='map_plan_v17.py: v16 + phase A rules (fixed seeds)')
    d['metrics']['building_count'] = len(d['functional_buildings'])
    d['metrics']['building_counts_by_district'] = dict(collections.Counter(b['district_id'] for b in d['functional_buildings']))
    for q in d['districts']:
        q['building_count'] = d['metrics']['building_counts_by_district'].get(q['id'], 0)
    trees16 = m16.read(MAP / 'Look/look_v16_flat.json')['trees']
    plaza_core = box(848, 374, 888, 414)
    pitch = unary_union([valid(Polygon(s['polygon_m'])) for s in d['structures'] if s['id'] == '04_football_pitch'])
    props_solid = [g for g, t in W.solid if t not in ('building', 'car_street')]
    metrics = dict(
        downtown=dict(v16=district_stats(d16['functional_buildings'], 'old_town'), v17=district_stats(d['functional_buildings'], 'old_town'), generation=dt, streets=st_dt),
        rough=dict(v16=district_stats(d16['functional_buildings'], 'residential'), v17=district_stats(d['functional_buildings'], 'residential'), generation=rd, streets=st_rd),
        common_land=cl, relief_hills=len(hills), props=len(W.props), v17_trees=len(W.trees), fences_added=len(W.fences))
    for dist in PHASE_A:
        delib = plaza_core.union(box(799, 357, 937, 463)) if dist == 'old_town' else pitch
        v16r, v16f = open_area(W, dist, d16['functional_buildings'], trees16, [], Polygon())
        v17r, v17f = open_area(W, dist, d['functional_buildings'], [t for t in trees16] + W.trees, props_solid, delib if dist == 'residential' else plaza_core)
        metrics['downtown' if dist == 'old_town' else 'rough']['largest_empty_circle_r_m'] = dict(v16=v16r, v17=v17r, free_share_v16=v16f, free_share_v17=v17f)
    d['v17_phase_a'] = dict(rules=dict(storey_m=STOREY, shop_ground_m=SHOP_GROUND, parapet_max_m=0.6, door_m=[1.1, 2.3], max_facade_run_m=24,
                                       lot_frontage_m=[8, 20], street_wall_depth_max_m=15, panel_section_max_m=48, entrance_spacing_m=[12, 16]),
                            recipes=[dict(name=r[0], type=r[1], floors=r[2], frontage_m=list(r[3]), weight=r[4]) for r in RECIPES],
                            deviations_from_v16_v11=DEVIATIONS, metrics=metrics)
    d['v17_dressing'] = dict(props=W.props, trees=W.trees, pads=[dict(mat=m, ctx=c, prio=p, polygon_m=[[R(x), R(y)] for x, y in g.exterior.coords[:-1]]) for g, m, c, p in W.pads],
                             pylon_line=pylons)
    d['checks'] = dict(d['checks'], v17=check(W, d, d16))
    print(json.dumps(metrics, indent=1, default=str)[:6000])
    print(json.dumps(d['checks']['v17'], indent=1)[:2000])
    if a.dry:
        return
    m16.json_new(out / names[0], d)
    print('v17: flats', flush=True)
    grey = m16.flatten_greybox(d)
    look = m16.flatten_look(d)
    tb, ta = patch_flats(W, d, look, grey, pylons)
    print(f'v17: trees {tb} scatter -> {ta} total', flush=True)
    m16.json_new(out / names[2], grey)
    m16.json_new(out / names[3], look)
    print('v17: crowd', flush=True)
    crowd = m16.build_crowd(crowd_view(W, d), look, m16.sha(out / names[0]))
    crowd['generator'] = 'map_plan_v17.py (v16 crowd builder, crowd_v12 algorithms; v17 props as obstacles)'
    m16.json_new(out / names[4], crowd)
    print('crowd validation', json.dumps(crowd['validation'])[:800], flush=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    print('v17: render', flush=True)
    render_png(W, d, out / names[1])
    samples = sightline_samples(W, d16['functional_buildings'])
    m16.json_new(REVIEW / 'sightline_samples.json', dict(revision_pair=['v16', 'v17'], eye_m=[1.7, 2.2], rays=24, max_m=600, districts=samples))
    m16.json_new(REVIEW / 'v17_metrics.json', dict(metrics=metrics, checks=d['checks']['v17'], deviations=DEVIATIONS))
    print('done', flush=True)


if __name__ == '__main__':
    main()
