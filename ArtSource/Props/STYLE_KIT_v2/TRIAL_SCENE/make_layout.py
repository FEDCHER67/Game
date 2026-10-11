"""Map_Look_v13_trial layout: ground meshes + placements from look_v12_flat.json (read only) for the Unity builder.

Writes (into ./out next to this script):
  ground_v2b.txt  - per material: 'MAT name nverts ntris', a line of vertex floats (Unity X Y Z), a line of indices
  place_v2b.txt   - 'key|x|y|z|yaw|scale|group' (Unity world, yaw degrees); key = kit:<asset> or prefab:<path>
  layout_v2b.json - stats + rule log
  top_v2b.png     - top-down check plot
Unity world = plan (x, height, y). Triangles are wound so that Cross(b - a, c - a) points to the visible side.
"""
import json, math, os, sys, zlib
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = 'C:/Dev/Game/ArtSource/References/Map/Look/look_v12_flat.json'
HEIGHTS = os.path.join(HERE, 'heights_full_4m.txt')      # sampled from Terrain_v12 (4 m grid), see README
BUILD_JSON = 'C:/Dev/Game/ArtSource/Props/STYLE_KIT_v2/HOUSES_PLAN/plan_buildings_v02.json'
REG = json.load(open(os.path.join(HERE, 'registry_map.json')))   # MapLookRegistry keys -> prefab paths
D = json.load(open(PLAN, encoding='utf-8'))
BLD = json.load(open(BUILD_JSON, encoding='utf-8'))['buildings']

R = (0.0, 1400.0, -100.0, 1100.0)         # v2b: the whole map is dressed (vistas close on real plan content)
O = (40.0, 1290.0, -30.0, 985.0)          # terrain grid (the v12 terrain extent); the sea plane goes beyond
LOG = []


def h32(*p):
    return zlib.crc32('|'.join(str(x) for x in p).encode())


def frac(*p):
    return (h32(*p) % 10007) / 10007.0


# ---------------------------------------------------------------- terrain heights
_hl = open(HEIGHTS).read().split('\n')
_hdr = _hl[0].split()
HX0, HZ0, HS = float(_hdr[1]), float(_hdr[3]), float(_hdr[5])
HG = [[float(v) for v in l.split()] for l in _hl[1:] if l.strip()]
HNZ, HNX = len(HG), len(HG[0])


def H(x, y):
    fx, fz = (x - HX0) / HS, (y - HZ0) / HS
    if fx < 0 or fz < 0 or fx >= HNX - 1 or fz >= HNZ - 1:
        return 0.0
    i, j = int(fx), int(fz)
    tx, tz = fx - i, fz - j
    a = HG[j][i] * (1 - tx) + HG[j][i + 1] * tx
    b = HG[j + 1][i] * (1 - tx) + HG[j + 1][i + 1] * tx
    return a * (1 - tz) + b * tz


def Hf0(x, y):
    return max(H(x, y), 0.0)


def Hf(x, y):
    """Town surfaces never dip below 0 (bridges over the canal, the paved banks); on slopes they lift a little so the
    4 m terrain triangles never poke through a draped ribbon."""
    g = math.hypot(Hf0(x + 1.0, y) - Hf0(x - 1.0, y), Hf0(x, y + 1.0) - Hf0(x, y - 1.0)) / 2.0
    return Hf0(x, y) + min(0.6, 0.35 * g)


# ---------------------------------------------------------------- geometry helpers
def pairs(p):
    return [(p[i], p[i + 1]) for i in range(0, len(p) - 1, 2)]


def pip(x, y, poly):
    c = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            c = not c
    return c


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def poly_dist(px, py, pts, closed=False):
    best = 1e9
    n = len(pts)
    for i in range(n - (0 if closed else 1)):
        a, b = pts[i], pts[(i + 1) % n]
        best = min(best, seg_dist(px, py, a[0], a[1], b[0], b[1]))
    return best


def inR(x, y, box=R, m=0.0):
    return box[0] - m <= x <= box[1] + m and box[2] - m <= y <= box[3] + m


def resample(pts, step):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(math.ceil(L / step)))
        for k in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n))
    return out


def trim_line(pts, t0, t1):
    """Cut t0 metres from the start and t1 from the end of a polyline."""
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    L = cum[-1]
    s0, s1 = t0, L - t1
    if s1 - s0 < 0.2:
        return []

    def at(s):
        for i in range(len(pts) - 1):
            if cum[i + 1] >= s:
                t = (s - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
                return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
        return pts[-1]
    out = [at(s0)] + [p for p, c in zip(pts, cum) if s0 < c < s1] + [at(s1)]
    return out


def offsets(pts, w):
    """Left/right offset polylines (miter, limited) at half-width w/2."""
    n = len(pts)
    L, Rr = [], []
    for i in range(n):
        if i == 0:
            d = (pts[1][0] - pts[0][0], pts[1][1] - pts[0][1])
            nx, ny = -d[1], d[0]
            l = math.hypot(nx, ny) or 1
            nx, ny, sc = nx / l, ny / l, 1.0
        elif i == n - 1:
            d = (pts[-1][0] - pts[-2][0], pts[-1][1] - pts[-2][1])
            nx, ny = -d[1], d[0]
            l = math.hypot(nx, ny) or 1
            nx, ny, sc = nx / l, ny / l, 1.0
        else:
            d0 = (pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1])
            d1 = (pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            l0, l1 = math.hypot(*d0) or 1, math.hypot(*d1) or 1
            n0 = (-d0[1] / l0, d0[0] / l0)
            n1 = (-d1[1] / l1, d1[0] / l1)
            nx, ny = n0[0] + n1[0], n0[1] + n1[1]
            l = math.hypot(nx, ny) or 1
            nx, ny = nx / l, ny / l
            cosa = nx * n0[0] + ny * n0[1]
            sc = min(1.0 / max(cosa, 0.3), 2.5)
        L.append((pts[i][0] + nx * w / 2 * sc, pts[i][1] + ny * w / 2 * sc))
        Rr.append((pts[i][0] - nx * w / 2 * sc, pts[i][1] - ny * w / 2 * sc))
    return L, Rr


# ---------------------------------------------------------------- mesh accumulator
class Acc:
    def __init__(self):
        self.v = defaultdict(list)
        self.t = defaultdict(list)

    def tri(self, m, a, b, c, want=(0, 1, 0)):
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
        if n[0] * want[0] + n[1] * want[1] + n[2] * want[2] < 0:
            b, c = c, b
        i = len(self.v[m]) // 3
        self.v[m] += [*a, *b, *c]
        self.t[m] += [i, i + 1, i + 2]

    def quad(self, m, a, b, c, d, want=(0, 1, 0)):
        self.tri(m, a, b, c, want)
        self.tri(m, a, c, d, want)

    def write(self, path):
        with open(path, 'w') as f:
            for m in sorted(self.v):
                nv, nt = len(self.v[m]) // 3, len(self.t[m]) // 3
                f.write(f'MAT {m} {nv} {nt}\n')
                f.write(' '.join(f'{x:.3f}' for x in self.v[m]) + '\n')
                f.write(' '.join(str(i) for i in self.t[m]) + '\n')
        return {m: len(self.t[m]) // 3 for m in self.v}


G = Acc()


def U(x, y, z):
    """plan (x, y) + height z -> Unity (X, Y, Z)"""
    return (x, z, y)


def flat_poly_tris(tris, mat, dz, floor=True):
    for i in range(0, len(tris) - 5, 6):
        p = [(tris[i], tris[i + 1]), (tris[i + 2], tris[i + 3]), (tris[i + 4], tris[i + 5])]
        G.tri(mat, *[U(x, y, (Hf(x, y) if floor else H(x, y)) + dz) for x, y in p])


def strip(pts, w, mat, dz, step=3.0, sides=None, base_dz=None):
    """Flat ribbon along a polyline; optional side walls (sides = colour) down to base_dz."""
    pts = resample(pts, step)
    if len(pts) < 2:
        return
    L, Rr = offsets(pts, w)
    for i in range(len(pts) - 1):
        a, b, c, d = L[i], L[i + 1], Rr[i + 1], Rr[i]
        G.quad(mat, U(*a, Hf(*a) + dz), U(*b, Hf(*b) + dz), U(*c, Hf(*c) + dz), U(*d, Hf(*d) + dz))
        if sides:
            for e0, e1, other in ((a, b, d), (d, c, a)):
                ox, oy = e0[0] - other[0], e0[1] - other[1]
                l = math.hypot(ox, oy) or 1
                want = (ox / l, 0, oy / l)
                G.quad(sides, U(*e0, Hf(*e0) + base_dz), U(*e1, Hf(*e1) + base_dz), U(*e1, Hf(*e1) + dz),
                       U(*e0, Hf(*e0) + dz), want)
    if sides:                                         # end caps
        for (p, q, inner) in ((L[0], Rr[0], pts[1]), (L[-1], Rr[-1], pts[-2])):
            mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
            ox, oy = mx - inner[0], my - inner[1]
            l = math.hypot(ox, oy) or 1
            G.quad(sides, U(*p, Hf(*p) + base_dz), U(*q, Hf(*q) + base_dz), U(*q, Hf(*q) + dz), U(*p, Hf(*p) + dz),
                   (ox / l, 0, oy / l))


def box(mat, x0, y0, x1, y1, z0, z1, ang=0.0, cx=None, cy=None):
    """Axis box in a frame rotated by ang (deg) about (cx, cy) (plan), heights absolute (Unity Y)."""
    cx = (x0 + x1) / 2 if cx is None else cx
    cy = (y0 + y1) / 2 if cy is None else cy
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))

    def P(x, y, z):
        dx, dy = x - cx, y - cy
        return U(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca, z)
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    G.quad(mat, *[P(x, y, z1) for x, y in c])
    for i in range(4):
        a, b = c[i], c[(i + 1) % 4]
        mx, my = (a[0] + b[0]) / 2 - (x0 + x1) / 2, (a[1] + b[1]) / 2 - (y0 + y1) / 2
        wx, wy = mx * ca - my * sa, mx * sa + my * ca
        l = math.hypot(wx, wy) or 1
        G.quad(mat, P(*a, z0), P(*b, z0), P(*b, z1), P(*a, z1), (wx / l, 0, wy / l))


# ---------------------------------------------------------------- districts, materials
DIST = [(d['id'], pairs(d['pts'])) for d in D['districts']]


def district_of(x, y):
    for did, poly in DIST:
        if pip(x, y, poly):
            return did
    best = min(DIST, key=lambda dp: poly_dist(x, y, dp[1], True))
    return best[0]


BASE_MAT = {'forest': 'lawn', 'elite': 'meadow', 'industrial': 'meadow', 'fields': 'meadow', 'village': 'meadow',
            'transition': 'meadow', 'residential': 'meadow', 'old_town': 'meadow'}
SOFT_MAT = {'gravel': 'greylight', 'sand': 'sand', 'rubber': 'terracotta', 'concrete': 'greylight', 'asphalt': 'asphalt',
            'lawn': 'lawn', 'park_grass': 'lawn', 'meadow': 'meadow', 'worn_grass': 'meadow', 'dry_field': 'field',
            'forest_floor': 'lawn', 'paving': 'paving'}

# ---------------------------------------------------------------- 1. base terrain grid (meadow / lawn by district)
step = 5.0
nx, nz = int((O[1] - O[0]) / step), int((O[3] - O[2]) / step)
for j in range(nz):
    for i in range(nx):
        x0, y0 = O[0] + i * step, O[2] + j * step
        x1, y1 = x0 + step, y0 + step
        dname = district_of(x0 + 2, y0 + 2)
        m = BASE_MAT.get(dname, 'meadow')
        if dname == 'industrial' and inR(x0, y0):
            m = 'meadow'
        G.quad(m, U(x0, y0, H(x0, y0)), U(x1, y0, H(x1, y0)), U(x1, y1, H(x1, y1)), U(x0, y1, H(x0, y1)))
LOG.append(f'base grid {nx}x{nz} cells of {step} m (meadow; lawn in the forest)')
SEA = D['sea']['level']
G.quad('water', U(-2500, -2500, SEA), U(4000, -2500, SEA), U(4000, 4000, SEA), U(-2500, 4000, SEA))
flat_poly_tris(D['beach']['tris'], 'sand', 0.03, floor=False)
for w in D['water']:
    if w['kind'] == 'lake' and w.get('tris'):
        for i in range(0, len(w['tris']) - 5, 6):
            pp = [(w['tris'][i], w['tris'][i + 1]), (w['tris'][i + 2], w['tris'][i + 3]), (w['tris'][i + 4], w['tris'][i + 5])]
            G.tri('water', *[U(x, y, w['level']) for x, y in pp])

# ---------------------------------------------------------------- 2. soft / hard ground polygons in the region
PAVING_POLYS = []
for g in D['ground']:
    ctx = g.get('ctx', '')
    pts = pairs(g['pts'])
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if max(xs) < R[0] or min(xs) > R[1] or max(ys) < R[2] or min(ys) > R[3]:
        continue
    if ctx.startswith('district:'):
        continue                       # the base grid carries district colours
    if ctx.startswith('shoulder:'):
        continue                       # v2b: no gravel shoulders in town - meadow to the road edge
    if g['mat'] == 'paving':
        PAVING_POLYS.append((ctx, pts, g['tris']))
        continue
    if ctx.startswith('garden:'):
        flat_poly_tris(g['tris'], 'lawn', 0.012)
        continue
    m = SOFT_MAT.get(g['mat'], 'meadow')
    if m == 'meadow':
        continue
    flat_poly_tris(g['tris'], m, 0.010 if g['soft'] else 0.02)
for y in D['yards']:
    if inR(*pairs(y['pts'])[0]) and y.get('tris'):
        flat_poly_tris(y['tris'], 'lawn', 0.014)

# ---------------------------------------------------------------- 3. roads, junctions, parking, markings
OLD = ('old_town', 'elite')


def road_mat(r):
    if r['surface'] == 'dirt':
        return 'sand'
    if r['surface'] == 'boardwalk':
        return 'wood'
    if r['cls'] == 'highway':
        return 'asphalt'                                    # arterial: the darker asphalt stays
    if r['district'] in OLD:
        return 'road'                                       # v2b road swatch (#B9B5AE)
    return 'asphalt'


ROADS = []
for r in D['roads']:
    pts = pairs(r['pts'])
    if not any(inR(x, y, m=30) for x, y in pts):
        continue
    t = trim_line(pts, r.get('trim_start', 0.0) or 0.0, r.get('trim_end', 0.0) or 0.0)
    ROADS.append((r, pts))
    if len(t) >= 2:
        strip(t, r['w'], road_mat(r), 0.03)
JMAT = {}
for j in D['junctions']:
    if not inR(j['x'], j['y'], m=30):
        continue
    mats = [road_mat(r) for r, _ in ROADS if r['road'] in j['roads'] or r['id'].split('#')[0] in j['roads']]
    m = 'road' if mats.count('road') * 2 >= len(mats) and mats else ('asphalt' if 'asphalt' in mats else (mats[0] if mats else 'road'))
    JMAT[j['id']] = m
    flat_poly_tris(j['tris'], m, 0.034)
for p in D['parking']:
    if inR(*pairs(p['pts'])[0], m=10):
        dist = district_of(*pairs(p['pts'])[0])
        flat_poly_tris(p['tris'], 'road' if dist in OLD else 'asphalt', 0.03)
for mk in D['markings']:
    pts = pairs(mk['pts'])
    if not any(inR(x, y, m=5) for x, y in pts):
        continue
    if mk['kind'] == 'zebra':
        (ax, ay), (bx, by) = pts[0], pts[-1]
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        k, s = 0, 0.25
        while s + mk['dash'] <= L - 0.2:
            c0 = (ax + ux * s, ay + uy * s)
            c1 = (ax + ux * (s + mk['dash']), ay + uy * (s + mk['dash']))
            strip([c0, c1], mk['w'], 'mark', 0.046, step=10)
            s += mk['dash'] + mk['gap']
        continue
    if mk['kind'] == 'center' and mk['dash'] > 0:
        res = resample(pts, 0.5)
        cum = 0.0
        on_seg = []
        period = mk['dash'] + mk['gap']
        for a, b in zip(res, res[1:]):
            l = math.hypot(b[0] - a[0], b[1] - a[1])
            if (cum % period) < mk['dash']:
                on_seg.append((a, b))
            cum += l
        for a, b in on_seg:
            strip([a, b], mk['w'], 'mark', 0.046, step=10)
    elif mk['kind'] == 'edge':
        strip(pts, mk['w'], 'mark', 0.046, step=4)

# ---------------------------------------------------------------- 4. sidewalks (raised paving, chalk.dark curb on the road side)
SIDEWALKS = []
for s in D['sidewalks']:
    pts = pairs(s['pts'])
    if len(pts) < 2 or not any(inR(x, y, m=10) for x, y in pts):
        continue
    # which side is the road: offset the middle of the first segment both ways
    (ax, ay), (bx, by) = pts[0], pts[1]
    mx, my = (ax + bx) / 2, (ay + by) / 2
    dx, dy = bx - ax, by - ay
    l = math.hypot(dx, dy) or 1
    nx_, ny_ = -dy / l, dx / l
    rd = [p for r, p in ROADS if r['road'] == s['road'] or r['id'].startswith(s['road'])]
    def dmin(x, y):
        return min((poly_dist(x, y, p) for p in rd), default=1e9)
    sgn = 1 if dmin(mx + nx_ * s['w'], my + ny_ * s['w']) < dmin(mx - nx_ * s['w'], my - ny_ * s['w']) else -1
    SIDEWALKS.append((s, pts, sgn))


# ---------------------------------------------------------------- 5. the clock square: raised paving, curbs on its outline
SQUARE_TRIS = []
for ctx, pts, tris in PAVING_POLYS:
    for i in range(0, len(tris) - 5, 6):
        p = [(tris[i], tris[i + 1]), (tris[i + 2], tris[i + 3]), (tris[i + 4], tris[i + 5])]
        G.tri('pavingsq', *[U(x, y, Hf(x, y) + 0.145) for x, y in p])
        SQUARE_TRIS.append(p)
SQ_POLYS = [pts for _, pts, _ in PAVING_POLYS]


def _in_tri(x, y, t):
    (ax, ay), (bx, by), (cx, cy) = t
    d1 = (x - bx) * (ay - by) - (ax - bx) * (y - by)
    d2 = (x - cx) * (by - cy) - (bx - cx) * (y - cy)
    d3 = (x - ax) * (cy - ay) - (cx - ax) * (y - ay)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


SQ_BB = [(min(p[0] for p in t), max(p[0] for p in t), min(p[1] for p in t), max(p[1] for p in t)) for t in SQUARE_TRIS]


def in_square(x, y):
    """Exactly what is drawn: inside any paving triangle of the square."""
    return any(b[0] <= x <= b[1] and b[2] <= y <= b[3] and _in_tri(x, y, t) for t, b in zip(SQUARE_TRIS, SQ_BB))


ROAD_LINES = [(r['w'], p) for r, p in ROADS]


JPOLYS = [pairs(j['pts']) for j in D['junctions'] if inR(j['x'], j['y'], m=30)]


SIDE_LINES = [(sw['w'], pairs(sw['pts'])) for sw in D['sidewalks'] if any(inR(x, y, m=10) for x, y in pairs(sw['pts']))]


def on_road(x, y, pad=0.0):
    """Roads, junctions AND sidewalks (everything hard and raised that a tree, bush or tuft must not stand on)."""
    if any(poly_dist(x, y, p) < w / 2 + pad for w, p in ROAD_LINES):
        return True
    if any(poly_dist(x, y, p) < w / 2 + pad for w, p in SIDE_LINES):
        return True
    return any(pip(x, y, jp) or (pad > 0 and poly_dist(x, y, jp, True) < pad) for jp in JPOLYS)


SQ_OUTLINE = []                   # boundary edges of the drawn square triangles (welded at 1 cm)
_ek = {}
for t in SQUARE_TRIS:
    q = [(round(x, 2), round(y, 2)) for x, y in t]
    for i in range(3):
        a, b = q[i], q[(i + 1) % 3]
        if a == b:
            continue
        k = (min(a, b), max(a, b))
        _ek.setdefault(k, []).append(t)
for (a, b), ts in _ek.items():
    if len(ts) != 1:
        continue
    t = ts[0]
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if L < 0.05:
        continue
    cx_, cy_ = sum(p[0] for p in t) / 3, sum(p[1] for p in t) / 3
    ox, oy = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    if (mx - cx_) * ox + (my - cy_) * oy < 0:
        ox, oy = -ox, -oy
    if in_square(mx + ox * 0.3, my + oy * 0.3):
        continue                                           # welded seam between paving pieces
    onside = any(poly_dist(mx + ox * 0.4, my + oy * 0.4, p_) < w_ / 2 + 0.05 for w_, p_ in SIDE_LINES)
    SQ_OUTLINE.append((a, b, (ox, oy), on_road(mx + ox * 1.2, my + oy * 1.2, 0.5) or onside))
    if onside:
        continue                                           # the sidewalk continues the paving: no curb, no wall
    G.quad('pavingdark', U(*a, Hf(*a)), U(*b, Hf(*b)), U(*b, Hf(*b) + 0.14), U(*a, Hf(*a) + 0.14), (ox, 0, oy))
    ia = (a[0] - ox * 0.15, a[1] - oy * 0.15)
    ib = (b[0] - ox * 0.15, b[1] - oy * 0.15)
    G.quad('curb', U(*a, Hf(*a) + 0.165), U(*b, Hf(*b) + 0.165), U(*ib, Hf(*ib) + 0.165), U(*ia, Hf(*ia) + 0.165))
    G.quad('curb', U(*a, Hf(*a) + 0.13), U(*b, Hf(*b) + 0.13), U(*b, Hf(*b) + 0.165), U(*a, Hf(*a) + 0.165), (ox, 0, oy))

def raised(x, y, self_s):
    if in_square(x, y):
        return True
    for o, opts, _ in SIDEWALKS:
        if o is self_s:
            continue
        if poly_dist(x, y, opts) < o['w'] / 2 - 0.05:
            return True
    return False


for s, pts, sgn in SIDEWALKS:
    res = resample(pts, 2.0)
    Lw0, Rw0 = offsets(res, s['w'])
    Lw1, Rw1 = offsets(res, s['w'] + 0.5)               # the lawn side reaches 0.25 m further (closes seams to the square)
    Lw, Rw = (Lw0, Rw1) if sgn > 0 else (Lw1, Rw0)
    Lc, Rc = offsets(res, s['w'] - 0.15)
    for i in range(len(res) - 1):
        a, b, c, d = Lw[i], Lw[i + 1], Rw[i + 1], Rw[i]
        mx, my = (a[0] + b[0] + c[0] + d[0]) / 4, (a[1] + b[1] + c[1] + d[1]) / 4
        if in_square(mx, my):
            continue                                       # the square is already paved
        G.quad('paving', U(*a, Hf(*a) + 0.14), U(*b, Hf(*b) + 0.14), U(*c, Hf(*c) + 0.14), U(*d, Hf(*d) + 0.14))
        for e0, e1, other in ((a, b, d), (d, c, a)):
            ox, oy = e0[0] - other[0], e0[1] - other[1]
            l = math.hypot(ox, oy) or 1
            ox, oy = ox / l, oy / l
            ex, ey = (e0[0] + e1[0]) / 2 + ox * 0.35, (e0[1] + e1[1]) / 2 + oy * 0.35
            if raised(ex, ey, s):
                continue                                   # another sidewalk or the square continues here
            G.quad('pavingdark', U(*e0, Hf(*e0)), U(*e1, Hf(*e1)), U(*e1, Hf(*e1) + 0.14), U(*e0, Hf(*e0) + 0.14), (ox, 0, oy))
        # curb ribbon on the road side (0.16 m wide, 0.165 m high)
        ca, cb = (Lc[i], Lc[i + 1]) if sgn > 0 else (Rc[i], Rc[i + 1])
        oa, ob = (a, b) if sgn > 0 else (d, c)
        G.quad('curb', U(*ca, Hf(*ca) + 0.165), U(*cb, Hf(*cb) + 0.165), U(*ob, Hf(*ob) + 0.165), U(*oa, Hf(*oa) + 0.165))
        ox, oy = oa[0] - ca[0], oa[1] - ca[1]
        l = math.hypot(ox, oy) or 1
        G.quad('curb', U(*oa, Hf(*oa)), U(*ob, Hf(*ob)), U(*ob, Hf(*ob) + 0.165), U(*oa, Hf(*oa) + 0.165), (ox / l, 0, oy / l))

# ---------------------------------------------------------------- 6. water: canal and river (opaque water + concrete banks)
for w in D['water']:
    if w['kind'] == 'lake':
        continue
    pts = pairs(w['pts'])
    if not any(inR(x, y, m=20) for x, y in pts):
        continue
    ww = w['w'] or 6.0
    res = resample(pts, 3.0)
    Lw, Rw = offsets(res, ww)
    for i in range(len(res) - 1):
        a, b, c, d = Lw[i], Lw[i + 1], Rw[i + 1], Rw[i]
        G.quad('water', U(*a, w['level']), U(*b, w['level']), U(*c, w['level']), U(*d, w['level']))
    # banks: a 1.2 m concrete edge band on both sides from water level up to ground (the canal only)
    for side in ((1, -1) if w.get('bank_mat') == 'concrete' else ()):
        Lb, Rb = offsets(res, ww + 2.4 * 1)
        inner = Lw if side > 0 else Rw
        outer = Lb if side > 0 else Rb
        for i in range(len(res) - 1):
            a, b = inner[i], inner[i + 1]
            c, d = outer[i + 1], outer[i]
            G.quad('greylight', U(*a, w['level'] + 0.02), U(*b, w['level'] + 0.02), U(*c, max(H(*c), w['level']) + 0.05),
                   U(*d, max(H(*d), w['level']) + 0.05))

# ---------------------------------------------------------------- placements
PL = []


def put(key, x, y, z=None, yaw=0.0, scale=1.0, group='Props'):
    if z is None:
        z = Hf(x, y)
    PL.append(f'{key}|{x:.3f}|{z:.3f}|{y:.3f}|{yaw:.2f}|{scale:.3f}|{group}')


def plan_yaw(a):
    return 90.0 - a


# buildings
BFP = {b['id']: pairs(b['fp']) for b in D['buildings']}
EAVE = {}
for e in BLD:
    fp = BFP[e['id']]
    z = min(Hf0(x, y) for x, y in fp)
    put('kit:' + e['asset'], e['x'], e['y'], z, e['unity_yaw'], 1.0, 'Buildings')
    EAVE[e['id']] = (fp, e['plan_h'], e['floors'], e['type'])

# landmarks
for l in D['landmarks']:
    if not inR(l['x'], l['y']):
        continue
    t = l['type']
    if t == 'fountain':
        put('kit:SQ_Fountain', l['x'], l['y'], Hf(l['x'], l['y']) + 0.14, 0.0, 1.0, 'Square')
    elif t == 'market_stall':
        z = Hf(l['x'], l['y']) + (0.14 if in_square(l['x'], l['y']) else 0.0)
        put('prefab:Assets/OnlyVolunteers/Art/Map/Prefabs/OLD_TOWN/market_stall.prefab', l['x'], l['y'], z, plan_yaw(l['a']), 1.0, 'Square')
    elif t == 'clock_tower_top':
        z0 = Hf(l['x'], l['y']) + (0.14 if in_square(l['x'], l['y']) else 0.0)
        fdx, fdy = 650.0 - l['x'], 540.0 - l['y']                  # the shaft door faces the junction / square centre
        put('kit:SQ_ClockShaft', l['x'], l['y'], z0, math.degrees(math.atan2(-fdx, -fdy)), 1.0, 'Square')
        put('prefab:Assets/OnlyVolunteers/Art/Map/Prefabs/OLD_TOWN/clock_tower_top.prefab', l['x'], l['y'], z0 + l['shaft_h'],
            plan_yaw(l['a']), 1.0, 'Square')
    elif t.startswith('billboard') or t.startswith('neon'):
        put(f'prefab:Assets/OnlyVolunteers/Art/Map/Prefabs/VALLEY/{t}.prefab', l['x'], l['y'], Hf(l['x'], l['y']) + l['z'],
            plan_yaw(l['a']), l['s'], 'Props')

# furniture
FMAP = {'lamp_street': None, 'bench': None, 'bin': 'prop/bin', 'garbage_container': 'prop/garbage_container',
        'sign_crossing': 'prop/sign_crossing', 'power_pole': 'prop/power_pole', 'bus_stop': 'prop/bus_stop',
        'sandbox': 'prop/sandbox', 'swings': 'prop/swings', 'slide': 'prop/slide', 'carpet_rack': 'prop/carpet_rack',
        'car_burnt': 'prop/car_burnt', 'car_wrecked': 'prop/car_wrecked', 'garage_metal_rust': 'prop/garage_metal_rust',
        'garage_metal_green': 'prop/garage_metal_green', 'garage_metal_blue': 'prop/garage_metal_blue',
        'garage_metal_open': 'prop/garage_metal_open', 'pipe_support': 'prop/pipe_support'}
SQC = (626.0, 541.0)                     # fountain
for f in D['furniture']:
    x, y = f['x'], f['y']
    if not inR(x, y):
        continue
    t = f['type']
    dist = district_of(x, y)
    z = Hf(x, y) + (0.14 if in_square(x, y) else 0.0)
    if t == 'bench' and math.hypot(x - SQC[0], y - SQC[1]) < 18:
        continue                                            # the fountain benches are re-laid on a ring below
    if t == 'lamp_street':
        if dist in OLD:
            put('kit:SQ_LampPost', x, y, z, plan_yaw(f['a']), 1.0, 'Lamps')
        else:
            put('prefab:' + REG['prop/lamp_street'], x, y, z, plan_yaw(f['a']), 1.0, 'Lamps')
        continue
    if t == 'bench':
        put('kit:SQ_Bench' if dist in OLD else 'prefab:' + REG['prop/bench'], x, y, z, plan_yaw(f['a']) + (180 if dist in OLD else 0), 1.0, 'Props')
        continue
    key = FMAP.get(t)
    if key and REG.get(key):
        put('prefab:' + REG[key], x, y, z, plan_yaw(f['a']), 1.0, 'Props')

# vehicles (the plan's parked cars, scooters)
for v in D['vehicles']:
    if inR(v['x'], v['y']) and REG.get('prop/' + v['type']):
        put('prefab:' + REG['prop/' + v['type']], v['x'], v['y'], Hf(v['x'], v['y']) + 0.03, plan_yaw(v['a']), 1.0, 'Vehicles')

# the fountain ring (critique 13d): two bench pairs TANGENT on one ring (r 6.2 m), facing the fountain; lamps and
# planters on the same ring between the pairs
zq = Hf(*SQC) + 0.14
for k, ang in enumerate((20.0, 200.0)):
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)
    tx, ty = -dy, dx
    for s_ in (-1, 1):
        bx, by = SQC[0] + dx * 6.2 + tx * s_ * 1.25, SQC[1] + dy * 6.2 + ty * s_ * 1.25
        yaw = math.degrees(math.atan2(-(-dx), -(-dy)))          # front (-Z) toward the fountain
        put('kit:SQ_Bench', bx, by, zq, yaw, 1.0, 'Square')
for ang in (110.0, 290.0):
    a = math.radians(ang)
    put('kit:SQ_LampPost', SQC[0] + math.cos(a) * 6.4, SQC[1] + math.sin(a) * 6.4, zq, 0.0, 1.0, 'Square')
for ang in (65.0, 155.0, 245.0, 335.0):
    a = math.radians(ang)
    put('kit:SQ_Planter', SQC[0] + math.cos(a) * 6.0, SQC[1] + math.sin(a) * 6.0, zq, ang, 1.0, 'Square')

# ---------------------------------------------------------------- trees (bible 5.3-5.5 + critique 3, 5, 6)
SPEC = {s['name']: s for s in json.load(open('C:/Dev/Game/ArtSource/Props/STYLE_KIT_v2/_lib/Look_Palette_v2.json',
                                              encoding='utf-8')).get('species', [])} if False else None
MODEL_H = {'Round_A': 8.0, 'Round_B': 6.0, 'Birch_A': 10.0, 'Birch_B': 8.0, 'Poplar_A': 12.0, 'Poplar_B': 9.5,
           'Spruce_A': 11.0, 'Spruce_B': 8.0, 'Pine_A': 13.0, 'Pine_B': 10.0}
RANGE = {'round': (5.5, 8.5), 'birch': (7.5, 10.5), 'poplar': (9.0, 12.5), 'spruce': (7.0, 11.5), 'pine': (9.5, 13.5)}
MODEL = {'round': 'Round', 'birch': 'Birch', 'poplar': 'Poplar', 'spruce': 'Spruce', 'pine': 'Pine'}
WATER_LINES = [pairs(w['pts']) for w in D['water'] if w['kind'] != 'lake']
ALL_PLAN_H = defaultdict(list)
for t in D['trees']:
    ALL_PLAN_H[t['sp']].append(t['h'])
for k in ALL_PLAN_H:
    ALL_PLAN_H[k].sort()


def species_for(t, dist):
    sp = t['sp']
    near_water = min((poly_dist(t['x'], t['y'], wl) for wl in WATER_LINES), default=1e9) < 25
    if dist == 'old_town':
        return 'birch' if (sp == 'birch' and near_water) else 'round'
    if dist == 'residential':
        return {'poplar': 'poplar', 'birch': 'birch'}.get(sp, 'round' if sp in ('oak', 'linden', 'fruit', 'palm') else 'birch')
    if dist == 'elite':
        return 'spruce' if sp in ('pine', 'spruce') else 'round'
    if dist == 'industrial':
        return 'poplar'
    if dist == 'transition':
        return 'round' if sp in ('oak', 'linden') else 'birch'
    if dist == 'village':
        return 'birch' if sp in ('poplar', 'pine', 'spruce', 'birch') else 'round'
    if dist == 'fields':
        return 'birch' if sp in ('spruce', 'pine', 'birch') else 'round'
    if dist == 'forest':
        if sp in ('pine', 'spruce'):
            return 'pine' if h32(round(t['x'], 1), round(t['y'], 1)) % 3 == 0 else 'spruce'
        return 'birch'
    return 'round'


# view corridors in front of every house front: no tree within 14 m of the entrance facade (the facade reads, and the
# eye-level camera sees the house, not a crown)
CORRIDORS = []
for e in BLD:
    if e['archetype'] not in ('masonry', 'commercial', 'villa_modern', 'tower', 'slab'):
        continue
    fr = math.radians(e['front_deg'])
    fx, fy = math.cos(fr), math.sin(fr)
    CORRIDORS.append((e['x'] + fx * e['D'] / 2, e['y'] + fy * e['D'] / 2, fx, fy, e['W'] / 2 + 1.0, 14.0))


def in_corridor(x, y):
    for cx, cy, fx, fy, hw, L in CORRIDORS:
        dx, dy = x - cx, y - cy
        a = dx * fx + dy * fy
        if 0.0 <= a <= L and abs(-dx * fy + dy * fx) <= hw:
            return True
    return False


def blocked(x, y, rad):
    """Trunk position not allowed: on roads / sidewalks / the square, in water, in a house's front view corridor, or
    the crown into a building."""
    if on_road(x, y, 1.0):
        return True
    if in_corridor(x, y):
        return True
    if in_square(x, y):
        return True
    for wl in WATER_LINES:
        if poly_dist(x, y, wl) < 6.0:
            return True
    for fp in BFP.values():
        if abs(fp[0][0] - x) > 90 or abs(fp[0][1] - y) > 90:
            continue
        if pip(x, y, fp) or poly_dist(x, y, fp, True) < rad + 0.5:
            return True
    return False


CROWN_R = {'round': 3.0, 'birch': 2.2, 'poplar': 1.6, 'spruce': 2.7, 'pine': 2.9}
trees = []
for t in D['trees']:
    if not inR(t['x'], t['y'], O):
        continue
    dist = district_of(t['x'], t['y'])
    sp = species_for(t, dist)
    trees.append({'x': t['x'], 'y': t['y'], 'sp': sp, 'dist': dist, 'h': t['h'], 'plan_sp': t['sp']})

# town districts: clusters (single linkage 14 m); lone trees -> triads or removed; one species per cluster
TOWN = ('old_town', 'residential', 'transition', 'elite', 'industrial')
town = [t for t in trees if t['dist'] in TOWN]
other = [t for t in trees if t['dist'] not in TOWN]
parent = list(range(len(town)))


def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


for i in range(len(town)):
    for j in range(i + 1, len(town)):
        if abs(town[i]['x'] - town[j]['x']) < 14 and math.hypot(town[i]['x'] - town[j]['x'], town[i]['y'] - town[j]['y']) < 14:
            parent[find(i)] = find(j)
clusters = defaultdict(list)
for i, t in enumerate(town):
    clusters[find(i)].append(t)
placed = []
stats = defaultdict(int)
for cid, cl in clusters.items():
    sps = defaultdict(int)
    for t in cl:
        sps[t['sp']] += 1
    sp = max(sorted(sps), key=lambda k: sps[k])
    cl = [dict(t, sp=sp) for t in cl]
    c0 = cl[0]
    if len(cl) == 1:
        if h32('lone', round(c0['x'], 1), round(c0['y'], 1)) % 2 == 0:
            stats['lone_removed'] += 1
            continue
        stats['lone_to_triad'] += 1
        base = h32('tri', round(c0['x'], 1)) % 360
        for k in (1, 2):
            a = math.radians(base + k * 120 + 15)
            cl.append(dict(c0, x=c0['x'] + math.cos(a) * 4.6, y=c0['y'] + math.sin(a) * 4.6))
    elif len(cl) == 2:
        stats['pair_to_triad'] += 1
        mx, my = (cl[0]['x'] + cl[1]['x']) / 2, (cl[0]['y'] + cl[1]['y']) / 2
        dx, dy = cl[1]['x'] - cl[0]['x'], cl[1]['y'] - cl[0]['y']
        l = math.hypot(dx, dy) or 1
        cl.append(dict(c0, x=mx - dy / l * 4.0, y=my + dx / l * 4.0))
    for k, t in enumerate(cl):
        placed.append(t)
placed += other

# the square ring (critique 3): linden B every 12 m on the lawn 2.2 m outside the square's lawn-side edges.
# Candidates every 1 m along the outer outline, kept only with a clear road margin; then walked around the square
# centre by angle and picked every 12 m of arc.
SQ_CENTRE = (650.0, 540.0)


def road_clear(x, y, margin):
    for w, p in ROAD_LINES:
        if poly_dist(x, y, p) < w / 2 + margin:
            return False
    for w, p in SIDE_LINES:
        if poly_dist(x, y, p) < w / 2 + margin * 0.6:
            return False
    return not any(pip(x, y, jp) or poly_dist(x, y, jp, True) < margin for jp in JPOLYS)


def outline_points(off, margin):
    pts = []
    for a, b, (ox, oy), road in SQ_OUTLINE:
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L))
        for k in range(n):
            t = (k + 0.5) / n
            x, y = a[0] + (b[0] - a[0]) * t + ox * off, a[1] + (b[1] - a[1]) * t + oy * off
            if in_square(x, y) or not road_clear(x, y, margin):
                continue
            pts.append((math.atan2(y - SQ_CENTRE[1], x - SQ_CENTRE[0]), x, y))
    pts.sort()
    return pts


ring = []
for ang, x, y in outline_points(2.2, 2.0):
    if all(math.hypot(x - rx, y - ry) >= 11.5 for rx, ry in ring):
        ring.append((x, y))
# drop plan trees close to the square (inside a 9 m margin) - the ring replaces them
placed = [t for t in placed if not any(math.hypot(t['x'] - px, t['y'] - py) < 7.0 for px, py in ring)
          and not (min((poly_dist(t['x'], t['y'], p, True) for p in SQ_POLYS), default=99) < 5.0)]
for px, py in ring:
    placed.append({'x': px, 'y': py, 'sp': 'round', 'dist': 'old_town', 'h': 6.0, 'variant': 'B', 'ring': True})


def eave_near(x, y):
    best = None
    for bid, (fp, h, floors, typ) in EAVE.items():
        if abs(fp[0][0] - x) > 60 or abs(fp[0][1] - y) > 60:
            continue
        if floors <= 4 and typ not in ('industrial_chimney',) and poly_dist(x, y, fp, True) <= 12.0:
            best = h if best is None else min(best, h)
    return best


TREES_OUT = []
for t in placed:
    sp = t['sp']
    if blocked(t['x'], t['y'], CROWN_R[sp] if not t.get('ring') else 1.5):
        stats['blocked'] += 1
        continue
    v = t.get('variant') or ('A' if h32('var', round(t['x'], 1), round(t['y'], 1)) % 3 else 'B')
    model = f'TR_{MODEL[sp]}_{v}'
    lst = ALL_PLAN_H.get(t.get('plan_sp', ''), [])
    pct = (sum(1 for h in lst if h < t['h']) / len(lst)) if lst else 0.5
    lo, hi = RANGE[sp]
    hv = lo + (hi - lo) * pct
    if t.get('ring'):
        hv = 6.0
    cap = eave_near(t['x'], t['y'])
    if cap is not None:
        hv = min(hv, cap + (3.0 if sp == 'poplar' else 1.0))
    hv = min(hv, 14.0)
    sc = max(0.8, min(1.15, hv / MODEL_H[f'{MODEL[sp]}_{v}']))
    if t.get('ring'):
        sc = 1.0
    yaw = h32('yaw', round(t['x'], 1), round(t['y'], 1)) % 360
    put('kit:' + model, t['x'], t['y'], H(t['x'], t['y']), yaw, sc, 'Trees')
    TREES_OUT.append((t['x'], t['y'], sp, v, sc))
    stats['tree_' + sp] += 1

# ---------------------------------------------------------------- bushes and hedges (bible 6.4, critique 4)
def hedge_run(pts, kind='Low', group='Hedges'):
    """2 m modules along a polyline (tangent), dome ends at both free ends."""
    res = resample(pts, 0.25)
    cum = [0.0]
    for a, b in zip(res, res[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    L = cum[-1]
    n = int(L // 2.0)
    if n < 1:
        return 0
    off = (L - n * 2.0) / 2

    def at(s):
        for i in range(len(res) - 1):
            if cum[i + 1] >= s:
                t = (s - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
                return (res[i][0] + (res[i + 1][0] - res[i][0]) * t, res[i][1] + (res[i + 1][1] - res[i][1]) * t), \
                       (res[i + 1][0] - res[i][0], res[i + 1][1] - res[i][1])
        return res[-1], (res[-1][0] - res[-2][0], res[-1][1] - res[-2][1])
    for k in range(n):
        p, d = at(off + 2.0 * k + 1.0)
        yaw = math.degrees(math.atan2(d[0], d[1])) - 90.0          # module +X along the run
        put(f'kit:BU_Hedge_{kind}', p[0], p[1], None, yaw, 1.0, group)
    for s_, sign in ((off, -1), (off + 2.0 * n, 1)):
        p, d = at(s_)
        yaw = math.degrees(math.atan2(d[0], d[1])) - 90.0 + (180.0 if sign < 0 else 0.0)
        put(f'kit:BU_Hedge_{kind}_End', p[0], p[1], None, yaw, 1.0, group)
    return n


nh = 0
for y in D['yards']:
    pts = pairs(y['pts'])
    if not inR(*pts[0]) or y['kind'] != 'front_yard':
        continue
    # fenced runs = perimeter minus gaps -> low hedge instead of the picket fence (old town)
    ring_pts = pts + [pts[0]]
    cum = [0.0]
    for a, b in zip(ring_pts, ring_pts[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = cum[-1]
    gaps = [(y['gaps'][i], y['gaps'][i + 1]) for i in range(0, len(y['gaps']) - 1, 2)]
    runs, s = [], 0.0
    for g0, g1 in sorted(gaps):
        if g0 > s + 0.5:
            runs.append((s, g0))
        s = max(s, g1)
    if total > s + 0.5:
        runs.append((s, total))

    def at(sv):
        for i in range(len(ring_pts) - 1):
            if cum[i + 1] >= sv:
                t = (sv - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
                return (ring_pts[i][0] + (ring_pts[i + 1][0] - ring_pts[i][0]) * t, ring_pts[i][1] + (ring_pts[i + 1][1] - ring_pts[i][1]) * t)
        return ring_pts[-1]
    for s0, s1 in runs:
        if s1 - s0 < 2.5:
            continue
        seg = [at(s0 + k * (s1 - s0) / 12) for k in range(13)]
        nh += hedge_run(seg, 'Low')
    # one bush group of 3 and (every other yard) a lilac inside the yard, near the house side
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    a0 = h32(y['id']) % 360
    for k, (r_, sc) in enumerate(((0.0, 1.0), (1.3, 0.94), (1.3, 1.05))):
        a = math.radians(a0 + k * 130)
        put('kit:BU_Round', cx + math.cos(a) * r_ + 1.2, cy + math.sin(a) * r_, None, (a0 + k * 97) % 360, sc, 'Bushes')
    if h32(y['id'], 'lilac') % 2 == 0:
        put('kit:BU_Flower', cx - 1.6, cy + 0.8, None, a0, 1.0, 'Bushes')
LOG.append(f'front-yard hedge modules: {nh}')

# square: low hedges along the lawn-side edges of the square (0.9 m outside the edge): contiguous runs of the
# outline candidates, broken at roads, gaps > 1.6 m and at the ring trees (a 3 m opening at each)
hp = outline_points(0.9, 1.2)
runs, cur = [], []
for ang, x, y in hp:
    if any(math.hypot(x - rx, y - ry) < 2.6 for rx, ry in ring) or (cur and math.hypot(x - cur[-1][0], y - cur[-1][1]) > 1.6):
        if len(cur) >= 3:
            runs.append(cur)
        cur = []
        if any(math.hypot(x - rx, y - ry) < 2.6 for rx, ry in ring):
            continue
    cur.append((x, y))
if len(cur) >= 3:
    runs.append(cur)
for r_ in runs:
    nh += hedge_run(r_, 'Low', 'Square')

# bush groups at building corners (old town, residential): 3 round bushes at one front corner, by template
for e in BLD:
    if e['district'] not in ('old_town', 'residential', 'transition') or e['archetype'] in ('chimney', 'kiosk'):
        continue
    fp = BFP[e['id']]
    k = h32(e['id'], 'bushcorner') % len(fp)
    cx, cy = sum(p[0] for p in fp) / len(fp), sum(p[1] for p in fp) / len(fp)
    px, py = fp[k]
    dx, dy = px - cx, py - cy
    l = math.hypot(dx, dy) or 1
    bx, by = px + dx / l * 2.2, py + dy / l * 2.2
    if on_road(bx, by, 1.5) or in_square(bx, by):
        continue
    kind = 'BU_Scrub' if e['district'] == 'residential' else 'BU_Round'
    for j, (ox_, oy_, sc) in enumerate(((0, 0, 1.0), (1.2, 0.5, 0.93), (0.3, 1.3, 1.06))):
        put('kit:' + kind, bx + ox_, by + oy_, None, (h32(e['id'], j) % 360), sc, 'Bushes')

# forest edge (critique 5): a bush rim - groups of 3 round bushes / scrub - on the outer side of the conifer trees that
# stand within 10 m of the forest district edge; birches already take the edge by species rule
FOREST = [pl_ for did, pl_ in DIST if did == 'forest']
for x, y, sp, v, sc in TREES_OUT:
    if sp not in ('spruce', 'pine', 'birch') or not FOREST:
        continue
    de = min(poly_dist(x, y, fpoly, True) for fpoly in FOREST)
    if de > 10.0 or not any(pip(x, y, fpoly) for fpoly in FOREST):
        continue
    if h32('rim', round(x, 1), round(y, 1)) % 2:
        continue
    # outward: towards the nearest point of the forest outline
    best = None
    for fpoly in FOREST:
        n = len(fpoly)
        for i in range(n):
            a_, b_ = fpoly[i], fpoly[(i + 1) % n]
            d_ = seg_dist(x, y, a_[0], a_[1], b_[0], b_[1])
            if best is None or d_ < best[0]:
                best = (d_, (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2)
    ox, oy = best[1] - x, best[2] - y
    l = math.hypot(ox, oy) or 1
    bx, by = x + ox / l * 3.5, y + oy / l * 3.5
    if on_road(bx, by, 1.0):
        continue
    kind = 'BU_Scrub' if h32('rimk', round(x, 1)) % 3 == 0 else 'BU_Round'
    for j, (ddx, ddy, scl) in enumerate(((0, 0, 1.0), (1.1, 0.6, 0.93), (0.2, 1.3, 1.06))):
        put('kit:' + kind, bx + ddx, by + ddy, None, h32('rimyaw', j, round(x, 1)) % 360, scl, 'Bushes')

# elite perimeter: the stylised fence (bible 2.5 - the only fence between districts), panels along the plan polyline
for ef in D['elite_fence']:
    pts = pairs(ef['pts'])
    res = resample(pts, 0.5)
    cum = [0.0]
    for a_, b_ in zip(res, res[1:]):
        cum.append(cum[-1] + math.hypot(b_[0] - a_[0], b_[1] - a_[1]))
    gaps = [(ef['gaps'][i], ef['gaps'][i + 1]) for i in range(0, len(ef.get('gaps', [])) - 1, 2)]
    sv = 1.25
    while sv < cum[-1] - 1.25:
        if any(g0 - 1.25 <= sv <= g1 + 1.25 for g0, g1 in gaps):
            sv += 2.5
            continue
        k = next(i for i in range(len(cum) - 1) if cum[i + 1] >= sv)
        a_, b_ = res[k], res[k + 1]
        t_ = (sv - cum[k]) / max(cum[k + 1] - cum[k], 1e-9)
        x_, y_ = a_[0] + (b_[0] - a_[0]) * t_, a_[1] + (b_[1] - a_[1]) * t_
        yaw = math.degrees(math.atan2(b_[0] - a_[0], b_[1] - a_[1])) - 90.0
        put('prefab:' + REG['prop/fence_elite_panel'], x_, y_, None, yaw, 1.0, 'Fences')
        sv += 2.5

# ---------------------------------------------------------------- grass tufts and flowers (bible 6.5): near the cameras only
FOCI = [(640.0, 545.0, 75.0), (532.0, 506.0, 40.0)]


def near_focus(x, y):
    return any(math.hypot(x - fx, y - fy) < r for fx, fy, r in FOCI)


def grass_ok(x, y):
    if on_road(x, y, 0.8) or in_square(x, y):
        return False
    for fp in BFP.values():
        if abs(fp[0][0] - x) > 40 or abs(fp[0][1] - y) > 40:
            continue
        if pip(x, y, fp) or poly_dist(x, y, fp, True) < 0.3:
            return False
    return True


ntuft = 0
# edge lines: along building plinths 0.45 m out, every 1.5-3 m (template steps)
for e in BLD:
    fp = BFP[e['id']]
    if not any(near_focus(x, y) for x, y in fp):
        continue
    cx, cy = sum(p[0] for p in fp) / len(fp), sum(p[1] for p in fp) / len(fp)
    for i in range(len(fp)):
        a, b = fp[i], fp[(i + 1) % len(fp)]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ox, oy = (b[1] - a[1]) / L, -(b[0] - a[0]) / L
        if (a[0] + b[0]) / 2 + ox - cx < (a[0] + b[0]) / 2 - cx and (a[1] + b[1]) / 2 + oy - cy < (a[1] + b[1]) / 2 - cy:
            pass
        mx, my = (a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy
        if ox * mx + oy * my < 0:
            ox, oy = -ox, -oy
        s = 0.6
        k = 0
        while s < L - 0.6:
            x = a[0] + (b[0] - a[0]) * s / L + ox * 0.75
            y = a[1] + (b[1] - a[1]) * s / L + oy * 0.75
            if grass_ok(x, y):
                put('kit:GR_Tuft_C' if k % 3 == 0 else 'kit:GR_Tuft_B', x, y, None, (k * 67) % 360, 0.92 + 0.16 * frac('t', k, e['id']), 'Grass')
                ntuft += 1
            s += 1.5 + 1.5 * frac('ts', k, e['id'])
            k += 1
# meadow clusters 3-7 tufts, 1 per ~20 m2 on a template grid (jitter by hash within the cell), flowers 1 per ~110 m2
for fx, fy, r in FOCI:
    gs = 4.5
    nn = int(r * 2 / gs)
    for i in range(nn):
        for j in range(nn):
            x = fx - r + (i + 0.2 + 0.6 * frac('cx', i, j, fx)) * gs
            y = fy - r + (j + 0.2 + 0.6 * frac('cy', i, j, fy)) * gs
            if math.hypot(x - fx, y - fy) > r or not grass_ok(x, y):
                continue
            n = 3 + h32('n', i, j, fx) % 5
            for k in range(n):
                a = k * 2.39996 + frac('a', i, j, k)
                rr = 0.55 * math.sqrt((k + 0.5) / n)
                put('kit:GR_Tuft_C' if k % 2 else 'kit:GR_Tuft_A', x + math.cos(a) * rr, y + math.sin(a) * rr, None,
                    (k * 83 + i * 7) % 360, 0.92 + 0.16 * frac('s', i, j, k), 'Grass')
                ntuft += 1
            if h32('fl', i, j, fx) % 6 == 0:
                col = ['Chalk', 'Red'][h32('flc', i, j) % 2]
                for k in range(5):
                    a = k * 2.39996
                    put(f'kit:GR_Flowers_{col}', x + 1.4 + math.cos(a) * 0.5 * math.sqrt((k + .5) / 5),
                        y + math.sin(a) * 0.5 * math.sqrt((k + .5) / 5), None, k * 71, 1.0, 'Grass')
LOG.append(f'tufts {ntuft}')

# ---------------------------------------------------------------- NPCs for scale (critique 14): existing prefabs, unchanged
NPC_A = 'Assets/OnlyVolunteers/Characters/SausageBuddy/SausageBuddy_A.prefab'
NPC_B = 'Assets/OnlyVolunteers/Characters/SausageBuddy/SausageBuddy_B.prefab'
npcs = [(NPC_A, 640.95, 533.69, 224.8),                 # play_npc_clock: the walker in front of the camera
        (NPC_B, 633.5, 536.4, 300.0), (NPC_A, 629.4, 547.6, 160.0),   # by the fountain and the stalls (square_a)
        (NPC_B, 652.0, 522.0, 40.0),
        (NPC_A, 533.0, 504.2, 220.0), (NPC_B, 536.8, 506.9, 250.0)]   # facade camera: at the door of O06_T3_U1
for p, x, y, yaw in npcs:
    put('prefab:' + p, x, y, Hf(x, y) + (0.14 if in_square(x, y) else 0.0), yaw, 1.0, 'NPC')

# ---------------------------------------------------------------- write
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
stats_tris = G.write(os.path.join(HERE, 'out', 'ground_v2b.txt'))
with open(os.path.join(HERE, 'out', 'place_v2b.txt'), 'w') as f:
    f.write('\n'.join(PL) + '\n')
json.dump({'ground_tris': stats_tris, 'placements': len(PL), 'stats': dict(stats), 'log': LOG, 'square_ring': len(ring)},
          open(os.path.join(HERE, 'out', 'layout_v2b.json'), 'w'), indent=1)
print(json.dumps({'ground_tris': stats_tris, 'placements': len(PL), 'stats': dict(stats), 'log': LOG, 'ring': len(ring)}, indent=1))
