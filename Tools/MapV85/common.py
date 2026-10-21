"""Shared helpers for the map v85 data pipeline (lead brief "Map W85 build", 2026-10-21; supersedes Tools/MapV76 for new builds).

World frame (same as maps v76/v85 and the W19/W76 builds): x east 0..1744 m, y north 0..950 m; Unity X = x, Z = y, Y = height.
PNG v85 (VOLUNTEERS_MAP_FINAL_v85.png): 8720 x 4750, 5 px/m, x = px/5, y = (4750 - py)/5. Preview: 1744 x 950, 1 px/m.
Master SVG v85 coordinates are BEFORE the raster shift: x = (X + 350)/5, y = (3500 - Y)/5, then + shift_m(x, y)
(post_shift_v85.py; identical to v76). `post(p)` converts a pre-shift metre point to the final world point,
`u2w(X, Y)` converts master-SVG units directly.
Authority (handoff v10 §0-§1): buildings / key objects 1:1 from the district plans; trees, small details, road joins and
surface transitions by logic (never copied point by point from the picture).
Data revision: REV (env MAPV85_REV, default v01) -> Assets/OnlyVolunteers/Map/W85Build/Data/<REV>, work files Tools/MapV85/out_<REV>.
"""
import json
import math
import os
import re

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REF = os.path.join(ROOT, 'ArtSource', 'References', 'Map')
MAP_DIR = os.path.join(REF, 'World_v85')
MAP_FULL = os.path.join(MAP_DIR, 'VOLUNTEERS_MAP_FINAL_v85.png')
MAP_PREVIEW = os.path.join(MAP_DIR, 'VOLUNTEERS_MAP_PREVIEW_v85.png')     # same render at 1 px/m
MAP_SVG = os.path.join(MAP_DIR, 'VOLUNTEERS_MAP_MASTER_v85.svg')
REV = os.environ.get('MAPV85_REV', 'v01')
OUT = os.path.join(ROOT, 'Assets', 'OnlyVolunteers', 'Map', 'W85Build', 'Data', REV)
WORK = os.path.join(ROOT, 'Tools', 'MapV85', 'out_' + REV)                 # previews, checks, reports (git)
W, H = 1744, 950                                                          # world size, m (1 m grid)
SEA_LEVEL = 0.0
GROUND = 5.0                                                              # flat ground ~5 m (handoff v02 §4)
SUFFIX = '_v85'

# handoff v10 §6 road widths (m)
WIDTH = {'city_carriageway': 12.0, 'city_sidewalk': 5.0, 'rural_asphalt': 6.4, 'village_main': 5.4, 'village_local': 4.2,
         'farm_track': 3.6, 'elite_stone': 4.5, 'alley': 5.6}
TREE_ROAD_GAP = 2.0                                                       # v10 §1.2: tree >= ~2 m from the road edge
TREE_FACADE_GAP = 3.0                                                     # v10 §1.2: tree >= ~3 m from a facade


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def shift_m(x, y):                                                        # post_shift_v85.py, verbatim
    m1 = r(x, 690.0, 770.0) * (1.0 - r(y, 470.0, 560.0))
    m2 = r(x, 430.0, 540.0) * (1.0 - r(x, 1090.0, 1130.0)) * r(y, 560.0, 650.0)
    return 20.0 * m1, -28.0 * m1 + 22.0 * m2


def post(p):
    """Pre-shift metres -> final world metres. post_shift_v85.shift_image samples the source at q - shift_m(q) for every
    OUTPUT point q, so the drawn position of a pre-shift point p is the fixed point q = p + shift_m(q) (not p + shift_m(p);
    the two differ by up to ~6 m in the gradient bands — found by the Downtown port, 21.10)."""
    q = (p[0], p[1])
    for _ in range(30):
        dx, dy = shift_m(q[0], q[1])
        nq = (p[0] + dx, p[1] + dy)
        if abs(nq[0] - q[0]) < 1e-6 and abs(nq[1] - q[1]) < 1e-6:
            return nq
        q = nq
    return q


def post_all(pts):
    return [post(p) for p in pts]


def u2m(X, Y):
    """master SVG units -> pre-shift metres."""
    return ((X + 350.0) / 5.0, (3500.0 - Y) / 5.0)


def u2w(X, Y):
    """master SVG units -> final world metres (pre-shift metres + shift_m)."""
    return post(u2m(X, Y))


def chaikin(p, n=3):                                                      # build_world_v85.py, verbatim
    for _ in range(n):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        q.append(p[-1])
        p = q
    return p


def resample(pl, step=2.0):
    out = [tuple(pl[0])]
    for a, b in zip(pl[:-1], pl[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / step))
        for i in range(1, n + 1):
            t = i / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def plen(pl):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pl[:-1], pl[1:]))


def grid():
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    return xs + 0.5, ys + 0.5                                             # row j = world y (j + .5), north = last row


def poly_mask(poly, xs=None, ys=None):
    """Even-odd fill of a polygon on the 1 m grid (row = y), bbox-limited."""
    if xs is None:
        xs, ys = grid()
    m = np.zeros(xs.shape, bool)
    pts = np.asarray(poly, float)
    if len(pts) < 3:
        return m
    x0, y0 = max(0, int(pts[:, 0].min()) - 1), max(0, int(pts[:, 1].min()) - 1)
    x1, y1 = min(xs.shape[1], int(pts[:, 0].max()) + 2), min(xs.shape[0], int(pts[:, 1].max()) + 2)
    if x0 >= x1 or y0 >= y1:
        return m
    X, Y = xs[y0:y1, x0:x1], ys[y0:y1, x0:x1]
    sub = np.zeros(X.shape, bool)
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        if ay == by:
            continue
        c = (Y >= min(ay, by)) & (Y < max(ay, by))
        xi = ax + (Y - ay) * (bx - ax) / (by - ay)
        sub ^= c & (X < xi)
    m[y0:y1, x0:x1] = sub
    return m


def stamp_polyline(pl, shape=(H, W), step=0.5):
    """Boolean raster of a polyline centre line (1 m grid), for distance transforms."""
    m = np.zeros(shape, bool)
    for p in resample(pl, step):
        ix, iy = int(p[0]), int(p[1])
        if 0 <= ix < shape[1] and 0 <= iy < shape[0]:
            m[iy, ix] = True
    return m


def polyline_dist(pl, xs, ys, cap=200.0):
    """Distance field (m) to a polyline on the grid, limited to its bbox + cap."""
    d = np.full(xs.shape, cap, np.float32)
    pts = np.array(pl, np.float32)
    x0, y0 = max(0, int(pts[:, 0].min() - cap)), max(0, int(pts[:, 1].min() - cap))
    x1, y1 = min(W, int(pts[:, 0].max() + cap) + 1), min(H, int(pts[:, 1].max() + cap) + 1)
    if x0 >= x1 or y0 >= y1:
        return d
    X, Y = xs[y0:y1, x0:x1], ys[y0:y1, x0:x1]
    best = np.full(X.shape, cap, np.float32)
    for a, b in zip(pts[:-1], pts[1:]):
        v = b - a
        L2 = float(v @ v) or 1e-6
        t = np.clip(((X - a[0]) * v[0] + (Y - a[1]) * v[1]) / L2, 0, 1)
        dd = np.hypot(X - (a[0] + t * v[0]), Y - (a[1] + t * v[1]))
        best = np.minimum(best, dd)
    d[y0:y1, x0:x1] = best
    return d


def seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy or 1e-9
    t = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    q = (a[0] + t * vx, a[1] + t * vy)
    return math.hypot(p[0] - q[0], p[1] - q[1]), q, t


def nearest_on(pl, p):
    """(distance, point, segment index, t) of the nearest point of polyline pl to p."""
    best = None
    for i, (a, b) in enumerate(zip(pl[:-1], pl[1:])):
        d, q, t = seg_dist(p, a, b)
        if best is None or d < best[0]:
            best = (d, q, i, t)
    return best


def inside(pt, pl):
    c = False
    for i in range(len(pl)):
        (x0, y0), (x1, y1) = pl[i - 1], pl[i]
        if (y0 > pt[1]) != (y1 > pt[1]) and pt[0] < x0 + (pt[1] - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def area(pl):
    """Signed area (> 0 = counter-clockwise in x east / y north)."""
    return 0.5 * sum(pl[i - 1][0] * pl[i][1] - pl[i][0] * pl[i - 1][1] for i in range(len(pl)))


def ccw(pl):
    return list(pl) if area(pl) > 0 else list(pl)[::-1]


def centroid(pl):
    return (sum(p[0] for p in pl) / len(pl), sum(p[1] for p in pl) / len(pl))


def rrect(c, w, d, ang_deg):
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + dx * ca - dy * sa, c[1] + dx * sa + dy * ca) for dx, dy in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]


def h01(s):                                                               # deterministic 0..1 from a string (FNV-1a)
    v = 2166136261
    for ch in s:
        v = ((v ^ ord(ch)) * 16777619) & 0xffffffff
    return v / 0xffffffff


def save_json(name, obj):
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def load_json(name):
    with open(os.path.join(OUT, name), encoding='utf-8') as f:
        return json.load(f)


def rnd2(p):
    return [round(float(p[0]), 2), round(float(p[1]), 2)]


# ---------------------------------------------------------------- master SVG (absolute coordinates of every tag)
_NUM = r'-?\d+(?:\.\d+)?(?:e-?\d+)?'


def svg_text():
    return open(MAP_SVG, encoding='utf-8').read()


def parse_transform(t):
    """SVG transform list -> affine (a, b, c, d, e, f): x' = a x + c y + e, y' = b x + d y + f."""
    M = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r'(\w+)\s*\(([^)]*)\)', t or ''):
        v = [float(x) for x in re.findall(_NUM, args)]
        if name == 'translate':
            T = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == 'scale':
            T = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == 'rotate':
            a_ = math.radians(v[0])
            ca, sa = math.cos(a_), math.sin(a_)
            T = (ca, sa, -sa, ca, 0, 0)
            if len(v) == 3:
                T = mat_mul(mat_mul((1, 0, 0, 1, v[1], v[2]), T), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == 'matrix':
            T = tuple(v[:6])
        else:
            continue
        M = mat_mul(M, T)
    return M


def mat_mul(A, B):
    a, b, c, d, e, f = A
    a2, b2, c2, d2, e2, f2 = B
    return (a * a2 + c * b2, b * a2 + d * b2, a * c2 + c * d2, b * c2 + d * d2, a * e2 + c * f2 + e, b * e2 + d * f2 + f)


def apply(M, p):
    return (M[0] * p[0] + M[2] * p[1] + M[4], M[1] * p[0] + M[3] * p[1] + M[5])


IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def svg_tags(text):
    """Yield (name, attrs, M, group_ids, start, end) for every element except <g>; M = full affine of the enclosing groups
    and of the element's own transform (apply(M, local) -> master-SVG units); group_ids = ids of the enclosing groups."""
    stack = []
    for q in re.finditer(r'<(/?)(\w+)([^>]*?)(/?)>', text):
        cl, nm, at, sc = q.groups()
        if nm == 'g':
            if cl:
                if stack:
                    stack.pop()
                continue
            gid = re.search(r'(?:^|\s)id="([^"]+)"', at)
            M0, ids0 = stack[-1] if stack else (IDENT, ())
            nb = (mat_mul(M0, parse_transform(attr(at, 'transform'))), ids0 + ((gid.group(1),) if gid else ()))
            if not sc:
                stack.append(nb)
            continue
        if cl:
            continue
        M0, ids0 = stack[-1] if stack else (IDENT, ())
        tr = attr(at, 'transform')
        yield nm, at, (mat_mul(M0, parse_transform(tr)) if tr else M0), ids0, q.start(), q.end()


def attr(at, k, default=None):
    m = re.search(r'(?:^|\s)%s="([^"]*)"' % re.escape(k), at)
    return m.group(1) if m else default


def points_of(at, M=IDENT):
    p = attr(at, 'points')
    if not p:
        return []
    vals = [float(v) for v in re.findall(_NUM, p)]
    return [apply(M, (vals[i], vals[i + 1])) for i in range(0, len(vals) - 1, 2)]


def num(at, k, default=0.0):
    v = attr(at, k)
    return float(v) if v not in (None, '') else default


# ---------------------------------------------------------------- contours without scikit-image (local Python has none)
def contour(mask, step=3):
    """Outer boundary of the largest component of a boolean mask as an ordered list of (x, y) cell centres
    (Moore-neighbour tracing), every `step`-th point. Coordinates in grid units (row = y)."""
    from scipy import ndimage
    lab, n = ndimage.label(mask)
    if n == 0:
        return []
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    m = lab == (int(np.argmax(sizes)) + 1)
    m = np.pad(m, 1)
    ys, xs = np.nonzero(m)
    j0 = int(np.argmin(ys * m.shape[1] + xs))
    start = (int(xs[j0]), int(ys[j0]))
    nbr = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
    out = [start]
    cur, back = start, 4                                                  # came from the west
    for _ in range(4 * int(m.sum()) + 8):
        found = False
        for k in range(8):
            d = (back + 1 + k) % 8
            nx_, ny_ = cur[0] + nbr[d][0], cur[1] + nbr[d][1]
            if m[ny_, nx_]:
                back = (d + 4) % 8
                cur = (nx_, ny_)
                found = True
                break
        if not found or cur == start:
            break
        out.append(cur)
    return [(x - 1 + 0.5, y - 1 + 0.5) for x, y in out[::step]]
