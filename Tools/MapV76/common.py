"""Shared helpers for the map v76 data pipeline (TASK map-v76-build, cloud, 2026-10-18).

World frame (same as the 2D map v76 and the W19 greybox): x east 0..1744 m, y north 0..950 m;
in Unity x -> X, y -> Z, height -> Y. PNG v76: 5 px/m, x = px/5, y = (4750 - py)/5.
Coordinates in build_world_v76.py are BEFORE the raster shift of post_shift_v76.py; `shift_m` below is the
same function (copied 1:1) and `post(p)` converts a script coordinate to the final v76 world coordinate.
"""
import json
import math
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
MAP_DIR = os.path.join(ROOT, 'ArtSource', 'References', 'Map', 'World_v76')
MAP_FULL = os.path.join(MAP_DIR, 'VOLUNTEERS_MAP_FINAL_v76.png')
MAP_PREVIEW = os.path.join(MAP_DIR, 'VOLUNTEERS_MAP_PREVIEW_v76.png')   # same render at 1 px/m
OUT = os.path.join(ROOT, 'Assets', 'OnlyVolunteers', 'Map', 'W76Build', 'Data', 'v01')
WORK = os.path.join(ROOT, 'Tools', 'MapV76', 'out')                     # previews, renders, reports (git)
W, H = 1744, 950                                                         # world size, m (1 m grid)
SEA_LEVEL = 0.0
GROUND = 5.0                                                             # "ровная земля ~5 м" (handoff v02 §4)


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def shift_m(x, y):                                                       # post_shift_v76.py, verbatim
    m1 = r(x, 690.0, 770.0) * (1.0 - r(y, 470.0, 560.0))
    m2 = r(x, 430.0, 540.0) * (1.0 - r(x, 1090.0, 1130.0)) * r(y, 560.0, 650.0)
    return 20.0 * m1, -28.0 * m1 + 22.0 * m2


def post(p):
    dx, dy = shift_m(p[0], p[1])
    return (p[0] + dx, p[1] + dy)


def post_all(pts):
    return [post(p) for p in pts]


def chaikin(p, n=3):                                                     # build_world_v76.py, verbatim
    for _ in range(n):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            q += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        q.append(p[-1])
        p = q
    return p


def resample(pl, step=2.0):
    out = [pl[0]]
    for a, b in zip(pl[:-1], pl[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / step))
        for i in range(1, n + 1):
            t = i / n
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def grid():
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    return xs + 0.5, ys + 0.5                                            # row j = world y (j + .5), north up = last row


def poly_mask(poly, xs=None, ys=None):
    """Even-odd fill of a polygon on the 1 m grid (row = y)."""
    if xs is None:
        xs, ys = grid()
    m = np.zeros(xs.shape, bool)
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        if y0 == y1:
            continue
        c = ((ys >= min(y0, y1)) & (ys < max(y0, y1)))
        xi = x0 + (ys - y0) * (x1 - x0) / (y1 - y0)
        m ^= c & (xs < xi)
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
    along = np.zeros(X.shape, np.float32)
    acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        v = b - a
        L2 = float(v @ v) or 1e-6
        t = np.clip(((X - a[0]) * v[0] + (Y - a[1]) * v[1]) / L2, 0, 1)
        dd = np.hypot(X - (a[0] + t * v[0]), Y - (a[1] + t * v[1]))
        upd = dd < best
        best = np.where(upd, dd, best)
        along = np.where(upd, acc + t * math.sqrt(L2), along)
        acc += math.sqrt(L2)
    d[y0:y1, x0:x1] = best
    polyline_dist.last_along = (x0, y0, x1, y1, along)
    return d


def save_json(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def load_json(name):
    with open(os.path.join(OUT, name), encoding='utf-8') as f:
        return json.load(f)


def rnd2(p):
    return [round(float(p[0]), 2), round(float(p[1]), 2)]
