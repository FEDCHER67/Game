"""Geometry helpers for flatten_look.py. Python 3.12 standard library only.

Points are (x, y) tuples in plan metres (x east, y north). Polygons are lists of points without a repeated
closing vertex; "CCW" means counter-clockwise in the plan frame (positive signed area).
"""
import math

EPS = 1e-9


# ---------------------------------------------------------------- basics

def pts2(seq):
    return [(float(p[0]), float(p[1])) for p in seq]


def flat(pts, nd=2):
    return [round(c, nd) for p in pts for c in p]


def unflat(a):
    return [(a[i], a[i + 1]) for i in range(0, len(a) - 1, 2)]


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def area(poly):
    n = len(poly)
    return sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n)) / 2.0


def ccw(poly):
    return list(poly) if area(poly) >= 0 else list(poly)[::-1]


def centroid(poly):
    a = area(poly)
    if abs(a) < EPS:
        return (sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))
    cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        c = x0 * y1 - x1 * y0
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    return (cx / (6 * a), cy / (6 * a))


def bbox(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def strip_closing(poly):
    poly = list(poly)
    if len(poly) > 1 and dist(poly[0], poly[-1]) < 1e-6:
        poly = poly[:-1]
    return poly


def dedupe(pts, eps=1e-6):
    out = []
    for p in pts:
        if not out or dist(out[-1], p) > eps:
            out.append(p)
    return out


def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def left_normal(dx, dy):
    L = math.hypot(dx, dy) or 1.0
    return (-dy / L, dx / L)


def yaw_from_vec(dx, dy):
    """Unity yaw (degrees, 0 = +Z = plan north, clockwise) of a plan direction: yaw = 90 - plan angle."""
    return (90.0 - math.degrees(math.atan2(dy, dx))) % 360.0


def yaw_from_plan_deg(a):
    return (90.0 - a) % 360.0


# ---------------------------------------------------------------- cleaning / simplification

def clean(poly, min_edge=0.3, collinear_deg=0.5):
    """Drop closing/duplicate vertices, merge edges shorter than min_edge, drop collinear vertices; CCW."""
    p = dedupe(strip_closing(pts2(poly)))
    if len(p) > 1 and dist(p[0], p[-1]) < 1e-6:
        p = p[:-1]
    changed = True
    while changed and len(p) > 3:
        changed = False
        for i in range(len(p)):
            a, b = p[i], p[(i + 1) % len(p)]
            if dist(a, b) < min_edge:
                p[i] = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                del p[(i + 1) % len(p)]
                changed = True
                break
    sin_tol = math.sin(math.radians(collinear_deg))
    changed = True
    while changed and len(p) > 3:
        changed = False
        for i in range(len(p)):
            a, b, c = p[i - 1], p[i], p[(i + 1) % len(p)]
            l1, l2 = dist(a, b), dist(b, c)
            if l1 < EPS or l2 < EPS:
                del p[i]
                changed = True
                break
            s = cross(a, b, c) / (l1 * l2)
            dot = (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1])
            if abs(s) < sin_tol and dot > 0:
                del p[i]
                changed = True
                break
    return ccw(p)


def _dp(pts, tol):
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i0, i1 = stack.pop()
        a, b = pts[i0], pts[i1]
        best, bi = -1.0, -1
        for k in range(i0 + 1, i1):
            d = dist_point_seg(pts[k], a, b)[0]
            if d > best:
                best, bi = d, k
        if bi >= 0 and best > tol:
            keep[bi] = True
            stack.append((i0, bi))
            stack.append((bi, i1))
    return [p for p, k in zip(pts, keep) if k]


def simplify_line(pts, tol=0.5):
    return _dp(dedupe(pts2(pts)), tol)


def simplify_poly(poly, tol=0.5):
    """Douglas-Peucker on a closed ring (split at vertex 0 and the vertex farthest from it)."""
    p = dedupe(strip_closing(pts2(poly)))
    if len(p) < 5:
        return ccw(p)
    far = max(range(len(p)), key=lambda i: dist(p[0], p[i]))
    a = _dp(p[:far + 1], tol)
    b = _dp(p[far:] + [p[0]], tol)
    r = a[:-1] + b[:-1]
    if len(r) < 3 or abs(area(r)) < 0.5 * abs(area(p)):
        return ccw(p)
    return ccw(r)


# ---------------------------------------------------------------- distances / tests

def dist_point_seg(p, a, b):
    """Returns (distance, t in [0,1], closest point)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0.0 if L < EPS else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    q = (a[0] + t * dx, a[1] + t * dy)
    return math.hypot(p[0] - q[0], p[1] - q[1]), t, q


def point_in_poly(p, poly):
    x, y, inside = p[0], p[1], False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def dist_point_ring(p, poly):
    return min(dist_point_seg(p, poly[i], poly[(i + 1) % len(poly)])[0] for i in range(len(poly)))


def seg_intersect(a, b, c, d):
    """Proper or touching intersection point of segments ab and cd, or None."""
    r = (b[0] - a[0], b[1] - a[1])
    s = (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < EPS:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    if -1e-9 <= t <= 1 + 1e-9 and -1e-9 <= u <= 1 + 1e-9:
        return (a[0] + t * r[0], a[1] + t * r[1]), t, u
    return None


def line_intersect(p, d1, q, d2):
    """Intersection of lines p + t*d1 and q + u*d2: returns (t, u) or None."""
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((q[0] - p[0]) * d2[1] - (q[1] - p[1]) * d2[0]) / den
    u = ((q[0] - p[0]) * d1[1] - (q[1] - p[1]) * d1[0]) / den
    return t, u


def self_intersects(poly):
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i or (j + 1) % n == i or j == (i + 1) % n:
                continue
            c, d = poly[j], poly[(j + 1) % n]
            if seg_intersect(a, b, c, d):
                return True
    return False


# ---------------------------------------------------------------- polylines

def cumulative(pts):
    c = [0.0]
    for a, b in zip(pts, pts[1:]):
        c.append(c[-1] + dist(a, b))
    return c


def point_at(pts, cum, s):
    """Point and unit tangent at arc length s."""
    s = max(0.0, min(cum[-1], s))
    lo, hi = 0, len(cum) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cum[mid] <= s:
            lo = mid
        else:
            hi = mid
    a, b = pts[lo], pts[hi]
    L = cum[hi] - cum[lo]
    t = 0.0 if L < EPS else (s - cum[lo]) / L
    dx, dy = b[0] - a[0], b[1] - a[1]
    l = math.hypot(dx, dy) or 1.0
    return (a[0] + t * dx, a[1] + t * dy), (dx / l, dy / l)


def sub_polyline(pts, cum, s0, s1):
    s0, s1 = max(0.0, s0), min(cum[-1], s1)
    if s1 - s0 < 1e-6:
        return []
    out = [point_at(pts, cum, s0)[0]]
    for p, c in zip(pts, cum):
        if s0 + 1e-6 < c < s1 - 1e-6:
            out.append(p)
    out.append(point_at(pts, cum, s1)[0])
    return dedupe(out)


def project(pts, cum, p):
    """Closest point on a polyline: (distance, station)."""
    best = (1e18, 0.0)
    for i in range(len(pts) - 1):
        d, t, _ = dist_point_seg(p, pts[i], pts[i + 1])
        if d < best[0]:
            best = (d, cum[i] + t * (cum[i + 1] - cum[i]))
    return best


def resample(pts, step):
    cum = cumulative(pts)
    L = cum[-1]
    n = max(1, int(round(L / step)))
    return [point_at(pts, cum, L * k / n)[0] for k in range(n + 1)]


def offset_polyline(pts, d, miter_limit=3.0):
    """Offsets a polyline to the left by d (negative = right), mitred joints."""
    n = len(pts)
    if n < 2:
        return list(pts)
    normals = [left_normal(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(n - 1)]
    out = []
    for i in range(n):
        if i == 0:
            m = normals[0]
            k = 1.0
        elif i == n - 1:
            m = normals[-1]
            k = 1.0
        else:
            n1, n2 = normals[i - 1], normals[i]
            mx, my = n1[0] + n2[0], n1[1] + n2[1]
            l = math.hypot(mx, my)
            if l < 1e-6:
                m, k = n1, 1.0
            else:
                m = (mx / l, my / l)
                c = m[0] * n1[0] + m[1] * n1[1]
                k = min(miter_limit, 1.0 / max(c, 1e-3))
        out.append((pts[i][0] + m[0] * d * k, pts[i][1] + m[1] * d * k))
    return out


def ribbon_poly(pts, half_left, half_right):
    """Closed outline of a strip between left offset half_left and right offset half_right (CCW)."""
    left = offset_polyline(pts, half_left)
    right = offset_polyline(pts, -half_right)
    return ccw(right + left[::-1])


def strip_tris(left, right):
    """Triangles (CCW) of a quad strip given matching left/right point lists along a direction."""
    tris = []
    for i in range(len(left) - 1):
        a, b, c, d = right[i], right[i + 1], left[i + 1], left[i]
        for t in ((a, b, c), (a, c, d)):
            if cross(*t) > 1e-9:
                tris.append(t)
            elif cross(*t) < -1e-9:
                tris.append((t[0], t[2], t[1]))
    return tris


# ---------------------------------------------------------------- hull / OBB / rectangles

def convex_hull(points):
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def obb(poly):
    """Minimum-area oriented box: (cx, cy, w along angle, d across, angle_deg of the w axis)."""
    pts = convex_hull(poly) or list(poly)
    best = None
    for i in range(len(pts)):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
        if dist((x1, y1), (x2, y2)) < 1e-6:
            continue
        a = math.atan2(y2 - y1, x2 - x1)
        c, s = math.cos(a), math.sin(a)
        us = [x * c + y * s for x, y in pts]
        vs = [-x * s + y * c for x, y in pts]
        ar = (max(us) - min(us)) * (max(vs) - min(vs))
        if best is None or ar < best[0] - 1e-9:
            cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
            best = (ar, cu * c - cv * s, cu * s + cv * c, max(us) - min(us), max(vs) - min(vs), math.degrees(a))
    if best is None:
        x0, y0, x1, y1 = bbox(poly)
        return ((x0 + x1) / 2, (y0 + y1) / 2, max(0.1, x1 - x0), max(0.1, y1 - y0), 0.0)
    return best[1:]


def rect_poly(cx, cy, w, d, angle_deg):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    out = []
    for u, v in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
        out.append((cx + u * c - v * s, cy + u * s + v * c))
    return out


def _cluster(vals, tol):
    vals = sorted(vals)
    out = []
    for v in vals:
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return [sum(c) / len(c) for c in out]


def rect_decompose(poly, tol=0.08, max_rects=8):
    """Splits a rectilinear footprint (L/U/cross/...) into axis rectangles in its own OBB frame.

    Returns [(cx, cy, len_u, len_v, angle_deg_of_u)], or the OBB alone when the footprint is not rectilinear.
    """
    cx, cy, w, d, ang = obb(poly)
    a = math.radians(ang)
    c, s = math.cos(a), math.sin(a)
    loc = [((x - cx) * c + (y - cy) * s, -(x - cx) * s + (y - cy) * c) for x, y in poly]
    for i in range(len(loc)):
        p, q = loc[i], loc[(i + 1) % len(loc)]
        if abs(p[0] - q[0]) > tol and abs(p[1] - q[1]) > tol:
            return [(cx, cy, w, d, ang)]
    xs = _cluster([p[0] for p in loc], tol)
    ys = _cluster([p[1] for p in loc], tol)
    if len(xs) < 2 or len(ys) < 2:
        return [(cx, cy, w, d, ang)]
    cells = set()
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if point_in_poly(((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2), loc):
                cells.add((i, j))
    used = set()
    rects = []
    for j in range(len(ys) - 1):
        i = 0
        while i < len(xs) - 1:
            if (i, j) not in cells or (i, j) in used:
                i += 1
                continue
            i1 = i
            while (i1 + 1, j) in cells and (i1 + 1, j) not in used:
                i1 += 1
            j1 = j
            while all((k, j1 + 1) in cells and (k, j1 + 1) not in used for k in range(i, i1 + 1)):
                j1 += 1
            for k in range(i, i1 + 1):
                for m in range(j, j1 + 1):
                    used.add((k, m))
            u0, u1, v0, v1 = xs[i], xs[i1 + 1], ys[j], ys[j1 + 1]
            ucx, vcy = (u0 + u1) / 2, (v0 + v1) / 2
            rects.append((cx + ucx * c - vcy * s, cy + ucx * s + vcy * c, u1 - u0, v1 - v0, ang))
            i = i1 + 1
    if not rects or len(rects) > max_rects:
        return [(cx, cy, w, d, ang)]
    return rects


# ---------------------------------------------------------------- triangulation

def _in_tri(p, a, b, c):
    d1, d2, d3 = cross(a, b, p), cross(b, c, p), cross(c, a, p)
    neg = d1 < -1e-12 or d2 < -1e-12 or d3 < -1e-12
    pos = d1 > 1e-12 or d2 > 1e-12 or d3 > 1e-12
    return not (neg and pos)


def bridge_holes(outer, holes):
    """Splices holes (any winding) into a CCW outer ring with zero-width bridges."""
    ring = ccw(outer)
    hs = [list(reversed(ccw(h))) for h in holes if len(h) >= 3]   # holes clockwise
    hs.sort(key=lambda h: -max(p[0] for p in h))
    for h in hs:
        mi = max(range(len(h)), key=lambda i: h[i][0])
        m = h[mi]
        best = None
        for vi, v in enumerate(ring):
            dd = dist(m, v)
            if best is not None and dd >= best[0]:
                continue
            ok = True
            for k in range(len(ring)):
                a, b = ring[k], ring[(k + 1) % len(ring)]
                if k == vi or (k + 1) % len(ring) == vi:
                    continue
                if seg_intersect(m, v, a, b):
                    ok = False
                    break
            if ok:
                for k in range(len(h)):
                    a, b = h[k], h[(k + 1) % len(h)]
                    if k == mi or (k + 1) % len(h) == mi:
                        continue
                    if seg_intersect(m, v, a, b):
                        ok = False
                        break
            if ok:
                best = (dd, vi)
        if best is None:
            continue
        vi = best[1]
        hole_seq = h[mi:] + h[:mi] + [h[mi]]
        ring = ring[:vi + 1] + hole_seq + [ring[vi]] + ring[vi + 1:]
    return ring


def triangulate(poly, holes=(), allow_hull=True):
    """Ear clipping (linked list). Returns (triangles, ok). Triangles are CCW (plan). Falls back to a hull fan."""
    p = ccw(dedupe(strip_closing(pts2(poly))))
    if holes:
        p = bridge_holes(p, [dedupe(strip_closing(pts2(h))) for h in holes])
    n = len(p)
    if n < 3:
        return [], False
    x0, y0, x1, y1 = bbox(p)
    tiny = 1e-9 * max(1.0, (x1 - x0) * (y1 - y0))
    prv = [(i - 1) % n for i in range(n)]
    nxt = [(i + 1) % n for i in range(n)]
    alive = n
    tris = []
    cur = 0
    stall = 0

    def remove(i):
        nxt[prv[i]] = nxt[i]
        prv[nxt[i]] = prv[i]

    while alive > 3:
        if stall > alive:
            # No ear in a full lap: drop one degenerate (collinear / spike) vertex, else give up.
            j, drop = cur, None
            for _ in range(alive):
                a, b, c = p[prv[j]], p[j], p[nxt[j]]
                if abs(cross(a, b, c)) <= tiny * 1e3 or a == c:
                    drop = j
                    break
                j = nxt[j]
            if drop is None:
                break
            cur = nxt[drop]
            remove(drop)
            alive -= 1
            stall = 0
            continue
        i0, i1, i2 = prv[cur], cur, nxt[cur]
        a, b, c = p[i0], p[i1], p[i2]
        if cross(a, b, c) > tiny:
            ok = True
            j = nxt[i2]
            while j != i0:
                q = p[j]
                if q != a and q != b and q != c and cross(p[prv[j]], q, p[nxt[j]]) <= tiny and _in_tri(q, a, b, c):
                    ok = False
                    break
                j = nxt[j]
            if ok:
                tris.append((a, b, c))
                remove(i1)
                alive -= 1
                cur = i2
                stall = 0
                continue
        cur = nxt[cur]
        stall += 1
    if alive == 3:
        a, b, c = p[prv[cur]], p[cur], p[nxt[cur]]
        if cross(a, b, c) > tiny:
            tris.append((a, b, c))
        return tris, True
    if not allow_hull:
        return tris, False
    h = convex_hull(p)
    return [(h[0], h[i], h[i + 1]) for i in range(1, len(h) - 1)], False


def tris_flat(tris, nd=2):
    return [round(c, nd) for t in tris for p in t for c in p]


# ---------------------------------------------------------------- spatial hashes

class SegHash:
    """Segments bucketed into square cells, padded so a query of radius <= pad needs only one cell."""

    def __init__(self, cell=20.0, pad=15.0):
        self.cell, self.pad, self.grid = cell, pad, {}

    def add(self, a, b, data):
        c, pd = self.cell, self.pad
        for gx in range(int(math.floor((min(a[0], b[0]) - pd) / c)), int(math.floor((max(a[0], b[0]) + pd) / c)) + 1):
            for gy in range(int(math.floor((min(a[1], b[1]) - pd) / c)), int(math.floor((max(a[1], b[1]) + pd) / c)) + 1):
                self.grid.setdefault((gx, gy), []).append((a, b, data))

    def add_polyline(self, pts, data):
        for a, b in zip(pts, pts[1:]):
            self.add(a, b, data)

    def near(self, p):
        return self.grid.get((int(math.floor(p[0] / self.cell)), int(math.floor(p[1] / self.cell))), ())


class BoxHash:
    """Arbitrary items with bounding boxes (padded)."""

    def __init__(self, cell=20.0, pad=15.0):
        self.cell, self.pad, self.grid = cell, pad, {}

    def add(self, box, data):
        c, pd = self.cell, self.pad
        for gx in range(int(math.floor((box[0] - pd) / c)), int(math.floor((box[2] + pd) / c)) + 1):
            for gy in range(int(math.floor((box[1] - pd) / c)), int(math.floor((box[3] + pd) / c)) + 1):
                self.grid.setdefault((gx, gy), []).append(data)

    def near(self, p):
        return self.grid.get((int(math.floor(p[0] / self.cell)), int(math.floor(p[1] / self.cell))), ())


class PointHash:
    def __init__(self, cell=8.0):
        self.cell, self.grid, self.maxr = cell, {}, 0.0

    def add(self, p, r=0.0):
        self.maxr = max(self.maxr, r)
        self.grid.setdefault((int(math.floor(p[0] / self.cell)), int(math.floor(p[1] / self.cell))), []).append((p, r))

    def clear_of(self, p, r):
        gx, gy = int(math.floor(p[0] / self.cell)), int(math.floor(p[1] / self.cell))
        reach = int(math.ceil((r + self.maxr) / self.cell))
        for dx in range(-reach, reach + 1):
            for dy in range(-reach, reach + 1):
                for q, rq in self.grid.get((gx + dx, gy + dy), ()):
                    if dist(p, q) < r + rq:
                        return False
        return True
