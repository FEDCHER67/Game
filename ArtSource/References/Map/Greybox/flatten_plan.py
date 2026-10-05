"""Flatten MAP_PLAN_R01_vNN.json into a simple JSON that Unity's JsonUtility can read (rough grey-box).

usage: python flatten_plan.py [vNN] [--scale S] [--thin K] [--veg] [--narrow]   (default v05, S=1) -> greybox_<vNN>[_sNNN]_flat.json next to this script
Coordinates stay in metres: plan X -> Unity X, plan Y -> Unity Z. --scale shrinks the whole layout, road widths and
footprints uniformly (min road 3.5 m, min house 6x5 m) and lowers tall residential blocks to keep human-scale storeys.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
REV = next((a for a in ARGS if a.startswith('v')), 'v05')
S = float(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 1.0
FLOORS = {9: 5, 12: 7, 16: 10, 20: 13, 22: 13} if S < 1.0 else {}
plan = json.load(open(os.path.join(HERE, '..', f'MAP_PLAN_R01_{REV}.json'), encoding='utf-8'))


def flat(pts):
    return [round(c * S, 2) for p in pts for c in p[:2]]


def area(poly):
    return sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly))) / 2


def triangulate(poly):
    """Ear clipping for simple polygons; returns a flat list of triangle vertex coordinates."""
    pts = [tuple(p[:2]) for p in poly]
    if len(pts) > 3 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if area(pts) < 0:
        pts.reverse()
    idx = list(range(len(pts)))
    tris = []

    def inside(p, a, b, c):
        def s(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 0:
                continue
            if any(inside(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris += [a, b, c]
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris += [pts[i] for i in idx]
    return flat(tris)


def box_from(center, w, d, poly=None):
    ang = 0.0
    if poly and len(poly) >= 2:
        (x0, y0), (x1, y1) = poly[0][:2], poly[1][:2]
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        e1 = math.hypot(x1 - x0, y1 - y0)
        if abs(e1 - d) < abs(e1 - w):
            ang += 90.0
    return round(center[0] * S, 2), round(center[1] * S, 2), round(max(6.0, w * S) if S < 1 else w, 2), round(max(5.0, d * S) if S < 1 else d, 2), round(ang, 1)


# Fedya 2026-10-04: at most two lanes; villages one lane.
NARROW = {'highway': 7.0, 'town_street': 6.0, 'rural_road': 3.8, 'dirt_shortcut': 3.5, 'passage': 2.5} if '--narrow' in sys.argv else {}
out = {'revision': REV, 'roads': [], 'buildings': [], 'water': [], 'points': [], 'rail': [], 'walls': [], 'barriers': []}
for r in plan['roads']:
    out['roads'].append({'cls': r['class'], 'w': NARROW.get(r['class'], max(3.5, float(r['width_m']) * S)), 'pts': flat(r['polyline_m'])})
for p in plan.get('paths', []):
    out['roads'].append({'cls': 'passage', 'w': NARROW.get('passage', max(2.5, float(p['width_m']) * S)), 'pts': flat(p['polyline_m'])})

func_centers = []
for f in plan.get('functional_buildings', []):
    x, y, w, d, a = box_from(f['center_m'], f['width_m'], f['depth_m'], f.get('footprint_m'))
    func_centers.append((f['center_m'][0], f['center_m'][1]))
    out['buildings'].append({'x': x, 'y': y, 'w': w, 'd': d, 'a': a, 'h': max(3.0, 3.0 * (f.get('storeys') or 1)), 'f': 1, 'label': f.get('label_ru', '')})
THIN = float(sys.argv[sys.argv.index('--thin') + 1]) if '--thin' in sys.argv else 1.0
keep_ids = {i for f in plan.get('farmsteads', []) if f.get('start_cluster') for i in f.get('building_ids', [])}
def kept(b):
    if THIN >= 1.0 or b['district_id'] in ('elite', 'industrial') or b['id'] in keep_ids:
        return True
    return (sum(map(ord, b['id'])) * 7919 % 1000) / 1000.0 < THIN
for b in plan.get('building_masses', []):
    if not kept(b):
        continue
    c = b['center_m']
    if any(math.hypot(c[0] - fx, c[1] - fy) < 3.0 for fx, fy in func_centers):
        continue
    x, y, w, d, a = box_from(c, b['width_m'], b['depth_m'], b.get('polygon_m'))
    out['buildings'].append({'x': x, 'y': y, 'w': w, 'd': d, 'a': a, 'h': 3.0 * FLOORS.get(b.get('floors') or 2, b.get('floors') or 2), 'f': 0, 'label': ''})

out['water_strips'], out['sea'] = [], []
for wtr in plan.get('water', []):
    if 'polygon_m' in wtr:
        # v11+: the sea beyond the beach is out of bounds; Unity returns whoever enters it to land.
        out['sea' if wtr.get('kind') == 'sea' else 'water'].append({'tris': triangulate(wtr['polygon_m'])})
    elif 'centerline_m' in wtr:
        out['water_strips'].append({'cls': wtr.get('kind', 'river'), 'w': max(4.0, float(wtr.get('width_m', 10)) * S), 'pts': flat(wtr['centerline_m'])})
for p in plan.get('points', []):
    # Unique ids (canonical ids repeat, e.g. five P13 points), so lookups and labels hit the right point.
    out['points'].append({'id': p['id'], 'label': p.get('name_ru', ''), 'x': round(p['position_m'][0] * S, 2), 'y': round(p['position_m'][1] * S, 2), 'cat': p.get('category', '')})
out['beaches'] = [{'tris': triangulate(b['polygon_m'])} for b in plan.get('beaches', [])]
out['rail'] = flat(plan['railway']['polyline_m'])
bnd = plan['boundary']['polygon_m']
coast = plan['boundary'].get('coast_segments_m', [])


def on_coast(a, b):
    # A boundary edge facing the sea gets no wall: both its ends lie on one coast segment.
    def near(p, s):
        (x1, y1), (x2, y2) = s[0][:2], s[1][:2]
        dx, dy = x2 - x1, y2 - y1
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - x1) * dx + (p[1] - y1) * dy) / L))
        return math.hypot(x1 + t * dx - p[0], y1 + t * dy - p[1]) < 1.0
    return any(near(a, s) and near(b, s) for s in coast)


for i in range(len(bnd)):
    a, b = bnd[i], bnd[(i + 1) % len(bnd)]
    if not on_coast(a, b):
        out['walls'].append({'pts': flat([a, b])})
for e in plan.get('exits', []):
    for poly in e.get('barrier_polygons_m', []):
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        out['barriers'].append({'x': (min(xs) + max(xs)) / 2 * S, 'y': (min(ys) + max(ys)) / 2 * S, 'w': max(2.0, (max(xs) - min(xs)) * S), 'd': max(2.0, (max(ys) - min(ys)) * S)})
if '--veg' in sys.argv:
    import random
    rnd = random.Random(4)

    def pip(pt, poly):
        x, y, inside = pt[0], pt[1], False
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i][:2], poly[i - 1][:2]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
        return inside

    def seg_d2(p, a, b):
        ax, ay, bx, by = a[0], a[1], b[0], b[1]
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L))
        qx, qy = ax + t * dx - p[0], ay + t * dy - p[1]
        return qx * qx + qy * qy

    CELL = 40.0
    grid = {}
    def add_line(pts, clear):
        for a, b in zip(pts, pts[1:]):
            for gx in range(int(min(a[0], b[0]) // CELL) - 1, int(max(a[0], b[0]) // CELL) + 2):
                for gy in range(int(min(a[1], b[1]) // CELL) - 1, int(max(a[1], b[1]) // CELL) + 2):
                    grid.setdefault((gx, gy), []).append((a, b, clear))
    for r in plan['roads']:
        add_line(r['polyline_m'], r['width_m'] / 2 + 9.0)
    for wtr in plan.get('water', []):
        if 'centerline_m' in wtr:
            add_line(wtr['centerline_m'], wtr.get('width_m', 10) / 2 + 6.0)
    add_line(plan['railway']['polyline_m'], 6.0)
    blocked = [(c[0], c[1], max(w, d) / 2 + 7.0) for c, w, d in
               [(b['center_m'], b['width_m'], b['depth_m']) for b in plan.get('building_masses', [])] +
               [(f['center_m'], f['width_m'], f['depth_m']) for f in plan.get('functional_buildings', [])]]
    bgrid = {}
    for bx, by, br in blocked:
        bgrid.setdefault((int(bx // CELL), int(by // CELL)), []).append((bx, by, br))
    lake = [w['polygon_m'] for w in plan.get('water', []) if 'polygon_m' in w]
    beach_polys = [b['polygon_m'] for b in plan.get('beaches', [])]
    yards = [pl['polygon_m'] for pl in plan.get('plots', [])] + [m['yard_polygon_m'] for m in plan.get('microdistricts', [])]
    veg = [(v['kind'], v['polygon_m']) for v in plan.get('vegetation_parcels', [])]
    dists = [(d['id'], d['polygon_m']) for d in plan['districts'] if d.get('parent_id') is None]
    density = {'forest': 0.85, 'transition': 0.5, 'transition_meadow': 0.5, 'village': 0.22, 'fields': 0.0,
               'residential': 0.06, 'old_town': 0.06, 'industrial': 0.1}
    out['trees'], out['rocks'] = [], []
    STEP = 17.0
    x = min(p[0] for p in bnd)
    while x < max(p[0] for p in bnd):
        y = min(p[1] for p in bnd)
        while y < max(p[1] for p in bnd):
            pt = (x + rnd.uniform(-5, 5), y + rnd.uniform(-5, 5))
            y += STEP
            if not pip(pt, bnd):
                continue
            g = (int(pt[0] // CELL), int(pt[1] // CELL))
            if any(seg_d2(pt, a, b) < c * c for a, b, c in grid.get(g, [])):
                continue
            if any((pt[0] - bx) ** 2 + (pt[1] - by) ** 2 < br * br for gx in (-1, 0, 1) for gy in (-1, 0, 1) for bx, by, br in bgrid.get((g[0] + gx, g[1] + gy), [])):
                continue
            if any(pip(pt, l) for l in lake) or any(pip(pt, yd) for yd in yards) or any(pip(pt, bp) for bp in beach_polys):
                continue
            kind = next((k for k, poly in veg if pip(pt, poly)), None)
            dist = next((i for i, poly in dists if pip(pt, poly)), 'fields')
            dens = 0.9 if kind == 'grove' else 0.55 if kind == 'orchard' else density.get(dist, 0.3)
            if dist == 'fields' and kind is None:
                if rnd.random() < 0.05:
                    out['rocks'].append([round(pt[0] * S, 2), round(pt[1] * S, 2), round(rnd.uniform(1.5, 3.2), 2), round(rnd.uniform(0.8, 1.8), 2), round(rnd.uniform(1.2, 2.6), 2), round(rnd.uniform(0, 180), 1)])
                continue
            if rnd.random() < dens:
                if dist in ('transition', 'transition_meadow') and rnd.random() < 0.3:
                    out['rocks'].append([round(pt[0] * S, 2), round(pt[1] * S, 2), round(rnd.uniform(2.0, 4.0), 2), round(rnd.uniform(1.2, 2.5), 2), round(rnd.uniform(1.8, 3.5), 2), round(rnd.uniform(0, 180), 1)])
                else:
                    small = kind == 'orchard'
                    out['trees'].append([round(pt[0] * S, 2), round(pt[1] * S, 2), round(rnd.uniform(1.0, 1.6) if small else rnd.uniform(1.6, 2.6), 2), round(rnd.uniform(4.0, 6.0) if small else rnd.uniform(7.0, 12.0), 2)])
        x += STEP
    print(f"vegetation: {len(out['trees'])} trees, {len(out['rocks'])} rocks")
    out['tree_data'] = [v for t in out.pop('trees') for v in t]
    out['rock_data'] = [v for r in out.pop('rocks') for v in r]
def obb(poly):
    """Minimum-area oriented box of a polygon: centre, width, depth, angle (deg)."""
    pts = [tuple(p[:2]) for p in poly]
    best = None
    for i in range(len(pts)):
        (x1, y1), (x2, y2) = pts[i], pts[(i + 1) % len(pts)]
        a = math.atan2(y2 - y1, x2 - x1)
        c, s_ = math.cos(a), math.sin(a)
        us = [x * c + y * s_ for x, y in pts]
        vs = [-x * s_ + y * c for x, y in pts]
        area_ = (max(us) - min(us)) * (max(vs) - min(vs))
        if best is None or area_ < best[0]:
            cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
            best = (area_, cu * c - cv * s_, cu * s_ + cv * c, max(us) - min(us), max(vs) - min(vs), math.degrees(a))
    return best[1:]

# Separators between districts are drawn by material (Fedya 2026-10-04: no solid green walls): label = material, h = height.
def resample(pts, step):
    # Keeps a vertex every `step` metres along a polyline, so a curved fence becomes a few dozen straight panels.
    kept, acc = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        acc += math.hypot(b[0] - a[0], b[1] - a[1])
        if acc >= step:
            kept.append(b)
            acc = 0.0
    if kept[-1] != pts[-1]:
        kept.append(pts[-1])
    return kept


out['hedges'] = []
for v in plan.get('vegetation_parcels', []):
    if v.get('kind') != 'interdistrict_barrier':
        continue
    # Fedya 2026-10-04: no fences on district borders; only the stylised elite fence and the rocks closing the beach.
    material, height = v.get('material') or 'fence', float(v.get('height_target_m') or 2.4)
    if v['id'].startswith('INDUSTRIAL_BEACH'):
        # The industrial zone is fenced off from the beach as private property: concrete with barbed wire (Fedya).
        material, height = 'barbed_fence', 2.8
    elif material not in ('elite_fence', 'security_fence', 'rock_scarp'):
        continue
    if len(v.get('axis_m') or []) >= 2:
        # v12+: organic separators carry their centre line; one thin panel per stretch of the curve.
        axis = resample([p[:2] for p in v['axis_m']], 4.0)
        for k, (a, b) in enumerate(zip(axis, axis[1:])):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 0.2:
                continue
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            out['hedges'].append({'x': round((a[0] + b[0]) / 2 * S, 2), 'y': round((a[1] + b[1]) / 2 * S, 2), 'w': round(L * S + 0.3, 2), 'd': 0.3,
                                  'a': round(ang, 1), 'h': height, 'label': material})
            if v.get('tree_line') and 'tree_data' in out and k % 2 == 0:
                off = 2.2 if k % 4 else -2.2
                nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L
                out['tree_data'] += [round(((a[0] + b[0]) / 2 + nx * off) * S, 2), round(((a[1] + b[1]) / 2 + ny * off) * S, 2), 1.8, 8.0]
        continue
    cx, cy, w, d, a = obb(v['polygon_m'])
    out['hedges'].append({'x': round(cx * S, 2), 'y': round(cy * S, 2), 'w': round(max(1.5, w * S), 2), 'd': round(max(1.5, d * S), 2), 'a': round(a, 1),
                          'h': float(v.get('height_target_m') or 2.4), 'label': v.get('material') or 'fence'})
    if v.get('tree_line') and 'tree_data' in out:
        L, rad = max(w, d), math.radians(a if w >= d else a + 90.0)
        for k in range(int(L // 7.0)):
            t = -L / 2 + 3.5 + k * 7.0
            off = 2.0 if k % 2 else -2.0
            tx, ty = cx + t * math.cos(rad) - off * math.sin(rad), cy + t * math.sin(rad) + off * math.cos(rad)
            out['tree_data'] += [round(tx * S, 2), round(ty * S, 2), 1.8, 8.0]
xs = [p[0] for p in bnd]; ys = [p[1] for p in bnd]
out['bounds'] = [min(xs) * S, min(ys) * S, max(xs) * S, max(ys) * S]
dst = os.path.join(HERE, f'greybox_{REV}' + (f'_s{round(S * 100):03d}' if S != 1.0 else '') + '_flat.json')
json.dump(out, open(dst, 'w', encoding='utf-8'), ensure_ascii=False)
print(f"hedges {len(out['hedges'])}, roads {len(out['roads'])}, buildings {len(out['buildings'])} (functional {len(func_centers)}), water {len(out['water'])}, sea {len(out['sea'])}, beaches {len(out['beaches'])}, "
      f"points {len(out['points'])}, walls {len(out['walls'])}, barriers {len(out['barriers'])} -> {dst}")
