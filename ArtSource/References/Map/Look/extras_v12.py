"""Hand-sited 'extras' for the v12 look: kit pieces the plan never places (garage rows, wrecks, beach furniture).

Called from flatten_look.py (Look.run, after vegetation and the outfall extras) and merged into look_v12_flat.json
as ordinary furniture items {type, x, y, a}; the builder resolves them through the registry slot prop/<type>.
Deterministic: fixed anchors + a seeded rng, then every piece is checked as an oriented box against roads, sidewalks,
junctions, buildings, parking, yards, hard ground, water, rail, sites, trees, rocks, furniture, gameplay points,
the sightline and the B05 waste outfall. A wreck or beach piece that fails is searched a few metres around its anchor
and dropped (with a warning) when nothing fits; a garage unit is never moved (the row must stay straight) and is
dropped with a warning. A local 0.5 m flood fill from the van roads (blocked by buildings, water, trees, rocks,
furniture, yards, scarp and exit blockers, elite-fence runs and the rail) then checks that the van still reaches every
garage door, every wreck and that no pocket of ground was cut off.

Siting (Fedya: "where they would stand harmoniously"):
  * garages  - a garage co-op behind the garage base B03 (two facing rows across a 9 m dirt driveway that opens onto
               the K2 lane) and one row behind courtyard C2, doors onto the rear road R_REAR; Soviet colour mix, rust
               heavy (bad district), one open unit per row, one missing slot in the co-op.
  * wrecks   - a burnt car at the co-op, a wreck rotting in courtyard C3, one parked at the R_REAR row, two in the
               tow yard behind P12 (site F06_TOW_YARD). None on a road.
  * beach    - elite beach: two neat clusters of teal umbrellas with paired loungers either side of the turnaround,
               plus the lifeguard tower facing the sea; valley beach: two looser clusters (colour drawn per umbrella
               from a red-heavy red/teal mix - this seed draws all five red; some single loungers) west and south-east
               of the turnaround, ~200 m from the outfall (only its signs stand there). Every beach piece keeps >= 18 m
               from the sea outline and stands on dry sand (the beach drops -1.5 t^3 towards the sea edge and the sea
               level is -0.6 m, so roughly the last 14-15 m of a 55 m beach are under water).

Builder yaw jitter: PropScatterer adds +-3..12 deg (LookGeom.Hash01 by furniture index) to every piece. That is the
organic look we want for wrecks and beach furniture, but tiled garage units would cut into each other, so garages
are written pre-compensated (a = row yaw + small tilt - builder jitter) and land within ~1 deg of their row. This is a
deliberate exception to the 3..12 deg rule (tiled 6 m deep units cannot turn 3 deg without cutting into each other).
CAVEAT: builder_jitter below is a hand-kept Python MIRROR of PropScatterer.Jitter (PropScatterer.cs) and
LookGeom.Hash / Hash01 (LookGeom.cs). Nothing here can detect a change on the C# side; if either changes, the garage
rows silently come out 3..12 deg crooked and cut into each other. Change both sides together (better: a per-item
no-jitter flag on LookFurniture that Furniture() and FurnitureCollider() respect).
"""
import math

from look_geom import bbox, cumulative, dist_point_seg, point_at, point_in_poly, yaw_from_vec

# (width, depth, forward offset of the collider centre from the pivot); front = +Z in Unity = yaw direction
DIMS = {'garage_metal_green': (3.0, 6.06, 0.0), 'garage_metal_blue': (3.0, 6.06, 0.0),
        'garage_metal_rust': (3.0, 6.06, 0.0), 'garage_metal_open': (3.0, 6.93, 0.44),   # open: body width, doors in front
        # (its prefab BoxCollider is 3.26 m wide with the door leaves, so it overlaps the neighbours' colliders by
        # ~0.1 m - harmless, all static; it is also one solid box over the doorway: an asset fix, not a placement one)
        'car_wrecked': (1.96, 4.11, 0.0), 'car_burnt': (1.97, 4.11, 0.0),
        'beach_sunlounger': (0.66, 1.95, 0.0), 'beach_umbrella_red': (0.25, 0.25, 0.0),
        'beach_umbrella_teal': (0.25, 0.25, 0.0), 'beach_lifeguard_tower': (2.98, 3.74, 0.41)}   # tower collider z +0.41
GARAGE_PITCH = 3.04
OUTFALL_CLEAR = 40.0
SEA_LEVEL = -0.6          # look json sea.level
DRY_SAND = 0.1            # a beach piece's lowest corner stays this far above the sea level
M32 = 0xFFFFFFFF

# per category: road edge, sidewalk, building, water (lakes/rivers; the sea too except for beach pieces), sea outline
# (beach pieces only), tree, furniture, bounds margin, rail
CLEAR = {'garage': dict(road=0.8, sidewalk=0.6, fp=2.0, water=3.0, tree=1.0, furn=0.6, bounds=6.0, rail=4.0),
         'wreck': dict(road=0.8, sidewalk=0.5, fp=0.8, water=3.0, tree=0.8, furn=0.6, bounds=4.0, rail=4.0),
         'beach': dict(road=1.0, sidewalk=0.5, fp=2.0, water=3.0, sea=18.0, tree=1.0, furn=0.8, bounds=0.0, rail=4.0)}


# ---------------------------------------------------------------- builder jitter: MIRROR of LookGeom.Hash / Hash01 and
# PropScatterer.Jitter (C#). Keep in step by hand - see the CAVEAT in the module docstring.
def _hash(x):
    x &= M32
    x ^= x >> 16
    x = (x * 0x7feb352d) & M32
    x ^= x >> 15
    x = (x * 0x846ca68b) & M32
    x ^= x >> 16
    return x


def hash01(a, b, seed):
    h = _hash(((a * 73856093) & M32) ^ _hash(((b * 19349663) & M32) ^ ((seed * 83492791) & M32)))
    return (h & 0xFFFFFF) / 16777216.0


def builder_jitter(k, seed):
    a = 3.0 + hash01(k, 3, seed) * 9.0
    return -a if hash01(k, 5, seed) < 0.5 else a


# ---------------------------------------------------------------- oriented boxes
class Box:
    def __init__(self, key, p, yaw, cat, tag=''):
        w, d, off = DIMS[key]
        a = math.radians(yaw)
        self.key, self.p, self.yaw, self.cat, self.tag = key, p, yaw, cat, tag
        self.f = (math.sin(a), math.cos(a))
        self.r = (math.cos(a), -math.sin(a))
        self.c = (p[0] + self.f[0] * off, p[1] + self.f[1] * off)
        self.hw, self.hd = w / 2, d / 2

    def local(self, q):
        dx, dy = q[0] - self.c[0], q[1] - self.c[1]
        return dx * self.r[0] + dy * self.r[1], dx * self.f[0] + dy * self.f[1]

    def world(self, u, v):
        return (self.c[0] + self.r[0] * u + self.f[0] * v, self.c[1] + self.r[1] * u + self.f[1] * v)

    def dist(self, q):
        """Distance from q to the box (negative inside)."""
        u, v = self.local(q)
        du, dv = abs(u) - self.hw, abs(v) - self.hd
        if du <= 0 and dv <= 0:
            return max(du, dv)
        return math.hypot(max(du, 0.0), max(dv, 0.0))

    def corners(self):
        return [self.world(su * self.hw, sv * self.hd) for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    def samples(self, step=0.4):
        nu, nv = max(1, math.ceil(2 * self.hw / step)), max(1, math.ceil(2 * self.hd / step))
        return [self.world(-self.hw + 2 * self.hw * i / nu, -self.hd + 2 * self.hd * j / nv)
                for i in range(nu + 1) for j in range(nv + 1)]

    def gap_to(self, o):
        """Separating distance between two boxes (SAT; <= 0 when they overlap)."""
        best = -1e9
        for ax in (self.r, self.f, o.r, o.f):
            def ext(b):
                return abs(b.r[0] * ax[0] + b.r[1] * ax[1]) * b.hw + abs(b.f[0] * ax[0] + b.f[1] * ax[1]) * b.hd
            sep = abs((o.c[0] - self.c[0]) * ax[0] + (o.c[1] - self.c[1]) * ax[1]) - ext(self) - ext(o)
            best = max(best, sep)
        return best


# ---------------------------------------------------------------- placement
class Extras:
    def __init__(self, look):
        self.L = look
        self.seed = look.base_seed
        self.items = []          # placed Box
        self.fails = []          # (tag, reasons)
        self.drops = []
        self.rows = {}           # garage row tag -> placed unit boxes
        self.ground = []         # (mat, prio, ccw ring, ctx) soft patches for build_ground
        out = look.out
        self.trees = [(t['x'], t['y']) for t in out.get('trees', [])]
        self.rocks = [((r['x'], r['y']), max(r['sx'], r['sy']) / 2) for r in out.get('rocks', [])]
        self.furn = [((f['x'], f['y']), FURN_RAD.get(f['type'], 0.5), f['type']) for f in out.get('furniture', [])]
        # plan points: out['points'] is only written later by build_misc, so read them from the plan
        self.points = [(q['position_m'][0], q['position_m'][1], pid) for pid, q in look.points.items()]
        self.pipes = []
        for pp in out.get('pipes', []):
            v = pp['pts']
            self.pipes += [((v[i], v[i + 1]), (v[i + 2], v[i + 3])) for i in range(0, len(v) - 3, 2)]
        self.outfall_pts = [(q['x'], q['y']) for q in out.get('decals', [])]
        sea = look.sea['poly'] if look.sea else []
        self.sea_ring = sea
        src = look.beach['src'] if look.beach else {}
        self.beach_land = [tuple(q[:2]) for q in src.get('land_edge_m', [])]
        self.beach_sea = [tuple(q[:2]) for q in src.get('sea_edge_m', [])]

    # ---- environment queries
    def sea_dist(self, p):
        if not self.sea_ring:
            return 99.0
        ring = self.sea_ring
        best = min(dist_point_seg(p, ring[i], ring[(i + 1) % len(ring)])[0] for i in range(len(ring)))
        return -best if point_in_poly(p, ring) else best

    def sand_height(self, p):
        """Beach terrain drop at p as HeightModel.BakeCoast bakes it (-1.5 t^3, t = 0 at the land edge, 1 at the sea edge)."""
        if len(self.beach_land) < 2 or len(self.beach_sea) < 2:
            return 0.0

        def d(line):
            return min(dist_point_seg(p, line[i], line[i + 1])[0] for i in range(len(line) - 1))
        dl, ds = d(self.beach_land), d(self.beach_sea)
        t = dl / max(0.01, dl + ds)
        return -1.5 * t ** 3

    def in_inland_water(self, p, pad):
        L = self.L
        return L.in_list(p, L.lakes, pad) or L.strip_excess(p) < pad

    def seaward(self, p):
        """Unit vector from p towards the nearest point of the sea outline."""
        ring = self.sea_ring
        best = None
        for i in range(len(ring)):
            d, _, q = dist_point_seg(p, ring[i], ring[(i + 1) % len(ring)])
            if best is None or d < best[0]:
                best = (d, q)
        dx, dy = best[1][0] - p[0], best[1][1] - p[1]
        L = math.hypot(dx, dy) or 1.0
        return dx / L, dy / L

    def outfall_dist(self, p):
        best = 999.0
        for a, b in self.pipes:
            best = min(best, dist_point_seg(p, a, b)[0])
        for q in self.outfall_pts:
            best = min(best, math.hypot(p[0] - q[0], p[1] - q[1]))
        return best

    def problems(self, box, site_ok=(), others=None):
        """Every rule the box breaks (empty list = placeable)."""
        L, cl, why = self.L, CLEAR[box.cat], []
        smp = box.samples()
        if min(L.road_excess(s) for s in smp) < cl['road']:
            why.append('road')
        if min(L.sidewalk_excess(s) for s in smp) < cl['sidewalk']:
            why.append('sidewalk')
        if any(L.in_junction(s, 1.0) for s in smp):
            why.append('junction')
        if min(L.fp_excess(s) for s in smp) < cl['fp']:
            why.append('building')
        if any(L.in_list(s, L.parking_polys, 1.0) for s in smp):
            why.append('parking')
        if box.cat == 'beach':
            if any(self.in_inland_water(s, cl['water']) for s in smp):
                why.append('water')
            if min(self.sea_dist(s) for s in box.corners()) < cl['sea']:
                why.append('sea/surf')
            if min(self.sand_height(s) for s in box.corners()) < SEA_LEVEL + DRY_SAND:
                why.append('wet sand')
        elif any(L.in_water(s, cl['water']) for s in smp):
            why.append('water')
            if not all(L.in_beach(s) for s in box.corners()):
                why.append('off the sand')
        if min(L.rail_excess(s) for s in smp) < cl['rail']:
            why.append('rail')
        if any(L.in_list(s, L.yard_polys, 1.0) for s in smp):
            why.append('yard')
        if any(point_in_poly(s, g[2]) for g in L.hard_ground for s in box.corners() + [box.c]):
            why.append('hard ground (playground/square)')
        sites = [s for s in L.sites if s['src'].get('id') not in site_ok and s['src'].get('type') != 'meeting']
        if any(L.in_list(s, sites, 0.5) for s in smp):
            why.append('functional site')
        if not all(L.in_bounds(s, cl['bounds']) for s in box.corners()):
            why.append('map edge')
        if L.sightline and min(dist_point_seg(s, L.sightline[0], L.sightline[1])[0] for s in box.corners() + [box.c]) < L.sightline[2]:
            why.append('sightline')
        if L.fence_hash is not None:
            for s in box.corners() + [box.c]:
                if any(dist_point_seg(s, a, b)[0] < 2.0 for a, b, _ in L.fence_hash.near(s)):
                    why.append('fence')
                    break
        near = max(box.hw, box.hd) + 4.0
        for t in self.trees:
            if abs(t[0] - box.c[0]) < near and abs(t[1] - box.c[1]) < near and box.dist(t) < cl['tree']:
                why.append(f'tree ({t[0]:.0f},{t[1]:.0f})')
                break
        for q, r in self.rocks:
            if abs(q[0] - box.c[0]) < near + r and abs(q[1] - box.c[1]) < near + r and box.dist(q) < r + 0.5:
                why.append('rock')
                break
        for q, r, t in self.furn:
            if abs(q[0] - box.c[0]) < near + r and abs(q[1] - box.c[1]) < near + r and box.dist(q) < r + cl['furn']:
                why.append(f'furniture {t}')
                break
        for x, y, pid in self.points:
            if box.dist((x, y)) < 4.0:
                why.append(f'gameplay point {pid}')
        if min(self.outfall_dist(s) for s in box.corners()) < OUTFALL_CLEAR:
            why.append('waste outfall')
        for o in (self.items if others is None else others):
            need = -0.08 if (o.cat == box.cat == 'garage' and o.tag[:2] == box.tag[:2]) else 0.25 if o.cat == box.cat == 'beach' else 0.8
            if box.gap_to(o) < need:
                why.append(f'overlaps {o.tag}')
                break
        return why

    def put(self, key, p, yaw, cat, tag, site_ok=(), search=0.0, yaw_span=0.0):
        """Place a piece at p (searching up to `search` m / +-`yaw_span` deg around it); returns the Box or None."""
        k = len(self.L.out['furniture']) + len(self.items)
        final = yaw + (0.0 if cat == 'garage' else builder_jitter(k, self.seed))
        cands = [(0.0, 0.0, 0.0)]
        if search > 0:
            ring_n = int(search / 0.5)
            for i in range(1, ring_n + 1):
                r = 0.5 * i
                for j in range(8 + 4 * i):
                    a = 2 * math.pi * j / (8 + 4 * i)
                    cands.append((r * math.cos(a), r * math.sin(a), 0.0))
        if yaw_span > 0:
            cands = [(dx, dy, dyaw) for dx, dy, _ in cands for dyaw in (0.0, yaw_span / 2, -yaw_span / 2, yaw_span, -yaw_span)]
        first = None
        for dx, dy, dyaw in cands:
            q = (p[0] + dx, p[1] + dy)
            box = Box(key, q, final + dyaw, cat, tag)
            why = self.problems(box, site_ok)
            if not why:
                box.a_out = (yaw + dyaw) % 360.0          # written yaw (builder adds its jitter on top)
                box.k = k
                self.items.append(box)
                return box
            if first is None:
                first = why
        self.drops.append((tag, key, p, first))
        self.L.warn.append(f'extras: {tag} ({key}) at ({p[0]:.1f},{p[1]:.1f}) not placed: {", ".join(first)}')
        return None

    # ---- garages
    def garage_row(self, tag, first, along, facing, keys, gaps=(), rng=None):
        """Units side by side every GARAGE_PITCH m from `first` along `along`, doors towards `facing`."""
        yaw = yaw_from_vec(*facing)
        placed = 0
        slot = 0
        for i, key in enumerate(keys):
            while slot in gaps:
                slot += 1
            setback = rng.uniform(-0.12, 0.12)
            tilt = rng.uniform(0.2, 0.6) * rng.choice((-1, 1))
            p = (first[0] + along[0] * GARAGE_PITCH * slot + facing[0] * setback,
                 first[1] + along[1] * GARAGE_PITCH * slot + facing[1] * setback)
            k = len(self.L.out['furniture']) + len(self.items)
            box = Box(key, p, yaw + tilt, 'garage', f'{tag}-{i + 1}')
            why = self.problems(box)
            if why:
                self.drops.append((box.tag, key, p, why))
                self.L.warn.append(f'extras: garage {box.tag} at ({p[0]:.1f},{p[1]:.1f}) not placed: {", ".join(why)}')
            else:
                box.a_out = (yaw + tilt - builder_jitter(k, self.seed)) % 360.0
                box.k = k
                box.row_yaw = yaw
                box.apron = box.world(0.0, box.hd + 2.5)     # where the van stops in front of the door
                self.items.append(box)
                self.rows.setdefault(tag, []).append(box)
                placed += 1
            slot += 1
        return placed

    def garage_keys(self, rng, n, open_at):
        """Rust-heavy colour mix (bad district) from a shuffled deck, never three alike side by side; one open unit."""
        closed = n - 1
        n_rust = math.ceil(closed * 0.45)
        n_green = (closed - n_rust + 1) // 2
        deck = ['garage_metal_rust'] * n_rust + ['garage_metal_green'] * n_green + ['garage_metal_blue'] * (closed - n_rust - n_green)
        for _ in range(50):
            rng.shuffle(deck)
            keys = deck[:open_at] + ['garage_metal_open'] + deck[open_at:]
            if not any(keys[i] == keys[i + 1] == keys[i + 2] for i in range(n - 2)):
                break
        return keys

    def road_chord(self, road, x0, x1):
        """Straight chord of a road's centreline between plan x0 and x1 (first matching piece)."""
        pts = []
        for r in self.L.out['roads']:
            if r['road'] == road:
                v = r['pts']
                pts += [(v[i], v[i + 1]) for i in range(0, len(v) - 1, 2)]

        def at(x):
            best = None
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                if min(a[0], b[0]) <= x <= max(a[0], b[0]) and abs(b[0] - a[0]) > 1e-6:
                    t = (x - a[0]) / (b[0] - a[0])
                    q = (x, a[1] + t * (b[1] - a[1]))
                    if best is None or q[1] > best[1]:
                        best = q
            return best
        return at(x0), at(x1), next(r['w'] for r in self.L.out['roads'] if r['road'] == road)

    def garages(self):
        rng = self.L.rng('extras:garages')
        n = 0
        # co-op behind the garage base B03: two rows facing each other across a ~9 m dirt driveway opening east onto
        # the K2 lane; north row backs onto the base, south row has one slot missing (a demolished unit)
        n += self.garage_row('G1', (480.0, 676.0), (1.0, 0.0), (0.0, -1.0), self.garage_keys(rng, 7, 4), rng=rng)
        n += self.garage_row('G2', (485.2, 661.0), (1.0, 0.0), (0.0, 1.0), self.garage_keys(rng, 5, 1), gaps=(3,), rng=rng)
        # behind courtyard C2, across the rear road: doors onto R_REAR with a 5 m apron
        a, b, w = self.road_chord('R_REAR', 650.5, 669.5)
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        along = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        facing = (along[1], -along[0])                      # right of west->east = south, towards the road
        off = w / 2 + 5.0 + DIMS['garage_metal_rust'][1] / 2
        first = (a[0] - facing[0] * off + along[0] * 1.5, a[1] - facing[1] * off + along[1] * 1.5)
        n += self.garage_row('G3', first, along, facing, self.garage_keys(rng, 6, 2), rng=rng)
        return n

    # ---- wrecks
    def wrecks(self):
        n = 0
        spots = [('car_burnt', (480.0, 655.5), 8.0, 'W1 co-op B03', ()),         # by the west end of the south row
                 ('car_wrecked', (620.5, 676.0), 3.0, 'W2 courtyard C3', ()),    # rotting by the S2 slab
                 ('car_wrecked', (646.0, 849.0), 186.0, 'W3 R_REAR garages', ()),  # nosed in beside row G3
                 ('car_wrecked', (685.2, 419.0), 2.0, 'W4 tow yard P12', ('F06_TOW_YARD',)),
                 ('car_burnt', (718.5, 418.0), 78.0, 'W5 tow yard P12', ('F06_TOW_YARD',))]
        for key, p, yaw, tag, site_ok in spots:
            if self.put(key, p, yaw, 'wreck', tag, site_ok, search=3.0, yaw_span=10.0):
                n += 1
        return n

    # ---- beach
    def beach_cluster(self, tag, anchor, n_umb, spacing, colours, rng, neat):
        """Umbrellas along the shore, each with two loungers (one when not neat and the dice say so)."""
        n = 0
        sw = self.seaward(anchor)                             # towards the water
        t = (-sw[1], sw[0])                                   # along the shore
        for i in range(n_umb):
            s = (i - (n_umb - 1) / 2) * spacing
            if not neat:
                s += rng.uniform(-0.6, 0.6)
                depth = rng.uniform(-1.2, 1.2)
            else:
                depth = 0.0
            u = (anchor[0] + t[0] * s + sw[0] * depth, anchor[1] + t[1] * s + sw[1] * depth)
            col = colours[i % len(colours)] if neat else rng.choice(colours)
            if not self.put(f'beach_umbrella_{col}', u, 0.0, 'beach', f'{tag}-U{i + 1}', search=1.5):
                continue
            n += 1
            pair = (-1, 1) if neat or rng.random() > 0.3 else (rng.choice((-1, 1)),)
            for side in pair:
                c = (u[0] + t[0] * side * 0.75 + sw[0] * 0.45, u[1] + t[1] * side * 0.75 + sw[1] * 0.45)
                yaw = yaw_from_vec(-sw[0], -sw[1])            # backrest (front) landward: whoever lies there faces the sea
                if not neat:
                    yaw += rng.uniform(-8, 8)
                if self.put('beach_sunlounger', c, yaw, 'beach', f'{tag}-U{i + 1}{"LR"[side > 0]}', search=0.5):
                    n += 1
        return n

    def beach(self):
        rng = self.L.rng('extras:beach')
        n = 0
        # elite beach (BEACH_ENTRY): neat teal rows either side of the turnaround, lifeguard tower between them
        n += self.beach_cluster('E1', (1037.0, 545.0), 3, 4.2, ('teal',), rng, True)
        n += self.beach_cluster('E2', (1016.5, 494.7), 3, 4.2, ('teal',), rng, True)     # 3 m landward of (1019, 493)
        p = (1033.4, 530.9)                                                                 # 5 m landward of (1038, 529)
        sw = self.seaward(p)
        if self.put('beach_lifeguard_tower', p, yaw_from_vec(*sw), 'beach', 'LG elite beach', search=4.0):
            n += 1
        # valley beach (BEACH_VALLEY_ENTRY): looser public clusters west and south-east of the turnaround
        n += self.beach_cluster('V1', (393.0, 266.0), 3, 4.6, ('red', 'teal', 'red'), rng, False)
        n += self.beach_cluster('V2', (441.7, 265.0), 2, 4.8, ('red', 'teal'), rng, False)    # 3 m landward of (442, 262)
        return n

    # ---- van reach (local flood fill, 0.5 m cells, van half width 1.0 m)
    def reach(self, window, extras):
        L = self.L
        x0, y0, x1, y1 = window
        S, R = 0.5, 1.0
        nx, ny = int((x1 - x0) / S) + 1, int((y1 - y0) / S) + 1
        static = bytearray(nx * ny)
        seed = bytearray(nx * ny)
        # fenced yards, scarp blockers and exit barriers (plan polygons; out['exits'] is only written later)
        walls = [(y['bb'], y['poly']) for y in L.yard_polys]
        walls += [(bbox(q), q) for q in ([(b['pts'][i], b['pts'][i + 1]) for i in range(0, len(b['pts']) - 1, 2)]
                                         for b in L.out.get('blockers', [])) if len(q) >= 3]
        walls += [(bbox(q), q) for q in ([tuple(v[:2]) for v in g] for e in L.exits for g in e.get('barrier_polygons_m', []))
                  if len(q) >= 3]
        walls = [w for w in walls if w[0][0] - R <= x1 and w[0][2] + R >= x0 and w[0][1] - R <= y1 and w[0][3] + R >= y0]
        for j in range(ny):
            for i in range(nx):
                p = (x0 + i * S, y0 + j * S)
                k = j * nx + i
                if L.road_excess(p, van_only=True) < -0.5:
                    seed[k] = 1
                    continue
                if (L.fp_excess(p) < R or L.in_water(p, 0.3) or not L.in_bounds(p, 0.5) or L.rail_excess(p) < R
                        or L.in_list(p, walls, R)):
                    static[k] = 1

        def disc(mask, q, r):
            i0, i1 = int((q[0] - r - x0) / S), int((q[0] + r - x0) / S) + 1
            j0, j1 = int((q[1] - r - y0) / S), int((q[1] + r - y0) / S) + 1
            for j in range(max(0, j0), min(ny, j1 + 1)):
                for i in range(max(0, i0), min(nx, i1 + 1)):
                    if math.hypot(x0 + i * S - q[0], y0 + j * S - q[1]) < r:
                        mask[j * nx + i] = 1
        for t in self.trees:
            if x0 - 3 < t[0] < x1 + 3 and y0 - 3 < t[1] < y1 + 3:
                disc(static, t, 0.35 + R)
        for q, r in self.rocks:
            if x0 - 5 < q[0] < x1 + 5 and y0 - 5 < q[1] < y1 + 5:
                disc(static, q, r + R)
        for q, r, typ in self.furn:
            if x0 - 5 < q[0] < x1 + 5 and y0 - 5 < q[1] < y1 + 5 and typ not in ('sandbox',):
                disc(static, q, min(r, 0.5) + R)
        for f in L.out.get('elite_fence', []):                  # fence runs; the gate gaps stay open
            axis = [(f['pts'][i], f['pts'][i + 1]) for i in range(0, len(f['pts']) - 1, 2)]
            if len(axis) < 2:
                continue
            cum, gaps = cumulative(axis), f.get('gaps', [])
            for m in range(int(cum[-1] / (S / 2)) + 1):
                t = m * S / 2
                if any(gaps[g] <= t <= gaps[g + 1] for g in range(0, len(gaps) - 1, 2)):
                    continue
                q = point_at(axis, cum, t)[0]
                if x0 - 3 < q[0] < x1 + 3 and y0 - 3 < q[1] < y1 + 3:
                    disc(static, q, 0.15 + R)
        after = bytearray(static)
        for b in extras:
            rr = max(b.hw, b.hd) + R + 0.5
            i0, i1 = int((b.c[0] - rr - x0) / S), int((b.c[0] + rr - x0) / S) + 1
            j0, j1 = int((b.c[1] - rr - y0) / S), int((b.c[1] + rr - y0) / S) + 1
            for j in range(max(0, j0), min(ny, j1 + 1)):
                for i in range(max(0, i0), min(nx, i1 + 1)):
                    if b.dist((x0 + i * S, y0 + j * S)) < R:
                        after[j * nx + i] = 1

        def flood(blocked):
            seen = bytearray(nx * ny)
            stack = [k for k in range(nx * ny) if seed[k]]
            for k in stack:
                seen[k] = 1
            while stack:
                k = stack.pop()
                i, j = k % nx, k // nx
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ii, jj = i + di, j + dj
                    if 0 <= ii < nx and 0 <= jj < ny:
                        kk = jj * nx + ii
                        if not seen[kk] and not blocked[kk]:
                            seen[kk] = 1
                            stack.append(kk)
            return seen
        before, now = flood(static), flood(after)
        lost = sum(1 for k in range(nx * ny) if before[k] and not now[k] and not after[k]) * S * S
        unreached = []
        for b in extras:
            if b.cat == 'garage':
                targets = [b.apron]
            elif b.cat == 'wreck':
                targets = [b.world(0, b.hd + 1.6), b.world(0, -b.hd - 1.6), b.world(b.hw + 1.6, 0), b.world(-b.hw - 1.6, 0)]
            else:
                continue
            ok = False
            for q in targets:
                i, j = round((q[0] - x0) / S), round((q[1] - y0) / S)
                if 0 <= i < nx and 0 <= j < ny and now[j * nx + i]:
                    ok = True
                    break
            if not ok:
                unreached.append(b.tag)
        return lost, unreached

    def ground_patches(self):
        """Worn gravel where cars actually go: the co-op (rows + driveway out to the K2 lane) and the G3 apron."""
        rng = self.L.rng('extras:ground')

        def ring(pts):
            pts = [(x + rng.uniform(-0.6, 0.6), y + rng.uniform(-0.6, 0.6)) for x, y in pts]
            a = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
            return pts if a > 0 else pts[::-1]
        g1, g2 = self.rows.get('G1', []), self.rows.get('G2', [])
        if g1 and g2:
            xs = [q[0] for b in g1 + g2 for q in b.corners()]
            ys = [q[1] for b in g1 + g2 for q in b.corners()]
            x0, x1, y0, y1 = min(xs) - 1.5, max(xs) + 1.0, min(ys) - 1.0, max(ys) + 1.0
            dy0, dy1 = max(b.world(0, b.hd)[1] for b in g2), min(b.world(0, b.hd)[1] for b in g1)   # driveway band
            lane_x = 508.8                                       # west edge of the K2 lane sidewalk
            self.ground.append(('gravel', 32, ring([(x0, y0), (x1, y0), (x1, dy0 + 0.5), (lane_x, dy0 + 1.0),
                                                     (lane_x, dy1 - 1.0), (x1, dy1 - 0.5), (x1, y1), (x0, y1)]),
                                'extras:garage_coop_B03'))
        g3 = self.rows.get('G3', [])
        if g3:
            a, b = g3[0], g3[-1]
            sa = 1.0 if (a.c[0] - b.c[0]) * a.r[0] + (a.c[1] - b.c[1]) * a.r[1] > 0 else -1.0   # a's outer side
            self.ground.append(('gravel', 32, ring([a.world(sa * (a.hw + 1.0), -a.hd - 0.5), b.world(-sa * (b.hw + 1.0), -b.hd - 0.5),
                                                     b.world(-sa * (b.hw + 1.5), b.hd + 5.2), a.world(sa * (a.hw + 1.5), a.hd + 5.2)]),
                                'extras:garage_row_R_REAR'))

    def run(self):
        counts = dict(garages=self.garages(), wrecks=self.wrecks(), beach=self.beach())
        self.ground_patches()
        L = self.L
        report = []
        groups = {'B03 co-op (G1/G2/W1)': ('G1', 'G2', 'W1'), 'R_REAR row (G3/W3)': ('G3', 'W3'), 'courtyard C3 (W2)': ('W2',),
                  'tow yard P12 (W4/W5)': ('W4', 'W5'), 'elite beach': ('E1', 'E2', 'LG'), 'valley beach': ('V1', 'V2')}
        reach_ok = True
        for name, pref in groups.items():
            members = [b for b in self.items if b.tag.split('-')[0].split(' ')[0] in pref]
            if not members:
                continue
            xs = [q[0] for b in members for q in b.corners()]
            ys = [q[1] for b in members for q in b.corners()]
            win = (min(xs) - 30, min(ys) - 30, max(xs) + 30, max(ys) + 30)
            lost, unreached = self.reach(win, members)
            reach_ok &= lost < 2.0 and not unreached
            report.append(f'van reach {name}: {len(members)} pieces, ground cut off {lost:.1f} m2'
                          + (f', NOT reached: {", ".join(unreached)}' if unreached else ', every door/wreck reached'))
            if lost >= 2.0 or unreached:
                L.warn.append(f'extras: {name}: van reach problem (lost {lost:.1f} m2, unreached {unreached})')
        # final re-check of every placed piece at its built pose (written yaw + builder jitter)
        bad = 0
        for b in self.items:
            built = b.a_out + builder_jitter(b.k, self.seed)
            box = Box(b.key, b.p, built, b.cat, b.tag)
            if self.problems(box, ('F06_TOW_YARD',), [o for o in self.items if o is not b]):
                bad += 1
        min_road = min(min(L.road_excess(s) for s in b.samples()) for b in self.items) if self.items else 99
        min_sw = min(min(L.sidewalk_excess(s) for s in b.samples()) for b in self.items) if self.items else 99
        min_fp = min(min(L.fp_excess(s) for s in b.samples()) for b in self.items) if self.items else 99
        min_out = min(self.outfall_dist(q) for b in self.items for q in b.corners()) if self.items else 999
        beach_items = [b for b in self.items if b.cat == 'beach']
        min_sea = min(self.sea_dist(q) for b in beach_items for q in b.corners()) if beach_items else 99
        gy = [abs(((b.a_out + builder_jitter(b.k, self.seed)) - b.row_yaw + 180) % 360 - 180)
              for b in self.items if b.cat == 'garage']
        report.append(f'clearances: road edge >= {min_road:.2f} m, sidewalk >= {min_sw:.2f} m, building >= {min_fp:.2f} m, '
                      f'outfall >= {min_out:.0f} m, beach pieces to the sea >= {min_sea:.1f} m; '
                      f'garage built yaw within {max(gy) if gy else 0:.2f} deg of the planned row yaw (jitter compensated); '
                      f'{bad} pieces fail at the built pose; {len(self.drops)} dropped')
        L.notes['extras_placed'] = len(self.items)
        L.notes['extras_dropped'] = len(self.drops)
        self.report = report
        self.ok = reach_ok and bad == 0 and not self.drops
        return [dict(type=b.key, x=round(b.p[0], 2), y=round(b.p[1], 2), a=round(b.a_out % 360, 2)) for b in self.items]


FURN_RAD = {'lamp_street': 0.4, 'power_pole': 0.4, 'bench': 1.0, 'bin': 0.4, 'bus_stop': 2.4, 'bus_stop_sign': 0.3,
            'swings': 2.8, 'slide': 2.4, 'sandbox': 2.0, 'carpet_rack': 1.8, 'garbage_container': 1.0,
            'sign_crossing': 0.3, 'clock_post': 0.6, 'sign_no_swimming': 0.4, 'pipe_support': 0.6}


def place_extras(look):
    """Appends the extras to look.out['furniture']; returns the Extras object (report lines, placed boxes)."""
    ex = Extras(look)
    look.out['furniture'] = look.out['furniture'] + ex.run()
    look.extra_ground = ex.ground
    return ex
