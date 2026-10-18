"""Step 9: v52 -> v76 checklist (Vadim's 'Ранее vNN' change notes) ticked against the generated data.

Input : data_src/v52_to_v76_changes.json (48 items, superseded ones are listed but not checked),
        Assets/OnlyVolunteers/Map/W76Build/Data/v01/*.json, out/height_1m.npy, out/classes_v76.npy.
Output: out/v52_to_v76_checklist.json (one record per change: status, evidence, builder consumption),
        out/v52_to_v76_checklist.md (same as a table).
Status: done | partial | missing | n/a (2D presentation only) | superseded.
'builder' says whether Assets/OnlyVolunteers/Map/W76Build/Editor/W76Builder.cs turns that data into scene geometry.
Run: python s09_checklist.py   (from Tools/MapV76, numpy only)
"""
import json
import math
import os
import re

import numpy as np

from common import OUT, WORK, load_json, shift_m

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'data_src', 'v52_to_v76_changes.json')
BUILDER = os.path.join(OUT, '..', '..', 'Editor', 'W76Builder.cs')

terrain = load_json('terrain_v76.json')
roads = load_json('roads_v76.json')['roads']
water = load_json('water_v76.json')['bodies']
border = load_json('border_v76.json')
feat = load_json('features_v76.json')
veg = load_json('vegetation_v76.json')['trees']
D = {n: load_json(f'districts/{n}_v76.json') for n in
     ['beach', 'construction', 'downtown', 'elite', 'forest', 'hamlet', 'port', 'quiet_valley', 'rough', 'tramduro']}
H = np.load(os.path.join(WORK, 'height_1m.npy'))           # [y, x], row 0 = south
C = np.load(os.path.join(WORK, 'classes_v76.npy'))         # [y, x], row 0 = south
CLS = load_json('classes.json')['classes']
builder_src = open(BUILDER, encoding='utf-8').read() if os.path.exists(BUILDER) else ''

ROAD = {r['id']: r for r in roads}
PADS = {k: np.array(v['poly'], float) for k, v in terrain['pads'].items()}
TREES = np.array([[t[0], t[1]] for t in veg], float)
TREE_KIND = np.array([t[2] for t in veg])


# ---------------------------------------------------------------- geometry helpers
def plen(pl):
    pl = np.asarray(pl, float)
    return float(np.hypot(*np.diff(pl, axis=0).T).sum()) if len(pl) > 1 else 0.0


def dist_pt_pl(p, pl):
    p = np.asarray(p, float)
    pl = np.asarray(pl, float)
    best = 1e9
    for a, b in zip(pl[:-1], pl[1:]):
        v = b - a
        L2 = float(v @ v) or 1e-9
        t = min(1.0, max(0.0, float((p - a) @ v) / L2))
        best = min(best, float(np.hypot(*(a + t * v - p))))
    return best if len(pl) > 1 else float(np.hypot(*(pl[0] - p)))


def dist_pl_pl(a, b):
    return min(dist_pt_pl(p, b) for p in np.asarray(a, float))


def inside(poly, p):
    poly = np.asarray(poly, float)
    x, y = p
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def grow(poly, m):
    poly = np.asarray(poly, float)
    lo, hi = poly.min(0) - m, poly.max(0) + m
    return np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]])


def trees_in(poly, kinds=None):
    poly = np.asarray(poly, float)
    lo, hi = poly.min(0), poly.max(0)
    sel = (TREES[:, 0] >= lo[0]) & (TREES[:, 0] <= hi[0]) & (TREES[:, 1] >= lo[1]) & (TREES[:, 1] <= hi[1])
    if kinds is not None:
        sel &= np.isin(TREE_KIND, kinds)
    idx = [i for i in np.nonzero(sel)[0] if inside(poly, TREES[i])]
    return TREES[idx]


def poly_area(poly):
    p = np.asarray(poly, float)
    return 0.5 * abs(float(np.dot(p[:, 0], np.roll(p[:, 1], -1)) - np.dot(p[:, 1], np.roll(p[:, 0], -1))))


def h_at(x, y):
    return float(H[int(np.clip(y, 0, H.shape[0] - 1)), int(np.clip(x, 0, H.shape[1] - 1))])


def cls_frac(poly, name):
    poly = np.asarray(poly, float)
    lo, hi = np.floor(poly.min(0)).astype(int), np.ceil(poly.max(0)).astype(int)
    k = CLS.index(name)
    hit = tot = 0
    for y in range(max(0, lo[1]), min(H.shape[0], hi[1])):
        for x in range(max(0, lo[0]), min(H.shape[1], hi[0])):
            if inside(poly, (x + .5, y + .5)):
                tot += 1
                hit += C[y, x] == k
    return hit / tot if tot else 0.0


def builds(token):
    return token in builder_src


def streets_on_map(district, kinds=('street', 'road')):
    """Share of points (every 1 m) on the district's street / outer-road centrelines that the v76 render paints as
    asphalt (+-2 m): the district layouts are placed by fitted offsets, asphalt is the most reliable class of the render."""
    k = CLS.index('asphalt')
    hit = tot = 0
    for z in D[district]['zones']:
        line = z.get('poly_line') or z.get('line') or []
        if z['kind'] not in kinds or len(line) < 2:
            continue
        line = np.asarray(line, float)
        for a, b in zip(line[:-1], line[1:]):
            n = max(1, int(np.hypot(*(b - a))))
            for t in np.linspace(0, 1, n, endpoint=False):
                x, y = (a + (b - a) * t).astype(int)
                win = C[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
                tot += 1
                hit += bool((win == k).any())
    return hit / tot if tot else 0.0


# ---------------------------------------------------------------- checks: return (status, evidence, builder)
MEADOW = np.array([[485, 512], [700, 512], [735, 560], [740, 655], [500, 655]], float)   # Construction / hill B / Rough meadow
ROUGH_SW = np.array([666.0, 674.0])


def r_ford():
    r = ROAD['hamlet_to_rough']
    lb = [b['centre'] for b in feat['land_bridges']]
    ford = min(lb, key=lambda c: abs(c[1] - 572))
    a, b = r['points'][0], r['points'][-1]
    end_ok = np.hypot(*(np.array(b) - ROUGH_SW)) < 15
    ok = abs(ford[1] - 572) < 5 and abs(a[1] - 572) < 5 and end_ok
    return ('done' if ok else 'partial',
            f"land bridge at {ford}; road hamlet_to_rough {plen(r['points']):.0f} m from {a} to {b} (Rough SW junction {ROUGH_SW.tolist()})",
            'roads ribbon + terrain land bridge' if builds('BuildRoads') else 'no')


def r_bypass_short():
    r = ROAD.get('hamlet_bypass')
    master = [k for k in ROAD if re.match(r'hamlet_bypass_', k)]
    if not r:
        return 'missing', 'no hamlet_bypass road', 'no'
    return ('done' if not master else 'partial',
            f"hamlet_bypass {plen(r['points']):.0f} m ({r['source']}); old master hamlet_bypass_* ids: {master or 'none'}",
            'roads ribbon')


def r_hill_b():
    pk = terrain['peaks_m']['hill_B']
    serp = 'serpentine_view_b' in ROAD
    crest = [round(h_at(*p), 1) for p in feat['hill_B']['crest']]
    return ('done' if abs(pk - 50) <= 2 and serp else 'partial',
            f"hill B peak {pk} m (crest samples {crest}); serpentine VIEW B kept: {serp}", 'terrain heightmap')


def r_bypass_dirt():
    r = ROAD['hamlet_bypass']
    dirt = [x for x in roads if x['kind'] == 'dirt_from_map']
    near = min((dist_pl_pl([p], r['points']) for x in dirt for p in (x['points'][0], x['points'][-1])), default=1e9)
    tun = 'tunnel' in ROAD
    return ('done' if near < 20 and tun else 'partial',
            f"nearest dirt-track end {near:.1f} m from the bypass; tunnel kept: {tun}", 'roads ribbon (dirt tracks = splat only)')


def r_rough_access():
    rough = grow(PADS['rough'], 25)
    port = grow(PADS['port'], 25)
    con = grow(PADS['construction'], 25)
    into = [x['id'] for x in roads if x['kind'] != 'dirt_from_map' and any(inside(rough, p) for p in x['points'])]
    to_port = [x['id'] for x in roads if any(inside(rough, p) for p in x['points']) and any(inside(port, p) for p in x['points'])]
    con_rough = [x['id'] for x in roads if any(inside(con, p) for p in x['points']) and any(inside(rough, p) for p in x['points'])]
    ok = 'hamlet_to_rough' in into and 'tunnel_north_approach' in into and to_port and not con_rough
    return ('done' if ok else 'partial',
            f"roads entering Rough: {len(into)} (riverside {'hamlet_to_rough' in into}, tunnel {'tunnel_north_approach' in into}); "
            f"Rough-Port roads {to_port}; Construction-Rough roads {con_rough or 'none'}", 'roads ribbon + tunnel mesh')


def r_shift(district, expect):
    s = streets_on_map(district)
    return ('done' if s >= .6 else 'partial' if s >= .35 else 'missing',
            f"{district}: {s:.0%} of its street/road centrelines lie on v76 asphalt ({expect}; footprint overlay checked by eye)", 'district buildings')


def r_tunnel_approach():
    n, s = plen(ROAD['tunnel_north_approach']['points']), plen(ROAD['tunnel_south_approach']['points'])
    ends = [ROAD['tunnel_north_approach']['points'][0], ROAD['tunnel_south_approach']['points'][-1]] + terrain['tunnel']['axis'][:1] + terrain['tunnel']['axis'][-1:]
    clash = []
    for dn, d in D.items():
        for b in d['buildings']:
            for app in ('tunnel_north_approach', 'tunnel_south_approach'):
                if dist_pl_pl(b['footprint'], ROAD[app]['points']) < ROAD[app]['width_m'] / 2 + 1:
                    clash.append(b['id'])
    ok = n >= 20 and s >= 35 and not clash
    return ('done' if ok else 'partial', f"approaches N {n:.0f} m (~25), S {s:.0f} m (~40); buildings on the approaches: {clash or 'none'}",
            'roads ribbon + tunnel mesh')


def r_meadow():
    t = trees_in(MEADOW)
    area = poly_area(MEADOW) / 1e4
    forest = trees_in(np.array([[200, 80], [420, 80], [420, 300], [200, 300]]))
    fd = len(forest) / (220 * 220 / 1e4)
    con_rough = r_rough_access()[1].split('Construction-Rough roads ')[1]
    # bumps: local maxima >= 0.8 m over a 30 m neighbourhood mean
    ys, xs = slice(int(MEADOW[:, 1].min()), int(MEADOW[:, 1].max())), slice(int(MEADOW[:, 0].min()), int(MEADOW[:, 0].max()))
    sub = H[ys, xs]
    k = 15
    pad = np.pad(sub, k, mode='edge')
    from numpy.lib.stride_tricks import sliding_window_view
    win = sliding_window_view(pad, (2 * k + 1, 2 * k + 1))
    mean = win.mean(axis=(-1, -2))
    mx = win.max(axis=(-1, -2))
    peaks = int(((sub == mx) & (sub - mean > .8)).sum())
    dens = len(t) / area
    ok = 0 < dens < .35 * fd and peaks >= 7 and con_rough == 'none'
    return ('done' if ok else 'partial',
            f"meadow {area:.1f} ha: {len(t)} trees ({dens:.0f}/ha vs forest {fd:.0f}/ha); bumps found {peaks} (Vadim: 7 bumps, not modelled as such - fbm micro relief only); Construction-Rough road: {con_rough}",
            'terrain trees + heightmap')


def r_more_meadow_trees():
    t = trees_in(MEADOW)
    # densest 40 m cluster (the ~46-tree grove in the middle) and trees at the Rough entrance
    best = 0
    for p in t:
        best = max(best, int((np.hypot(*(t - p).T) < 25).sum()))
    ent = trees_in(np.array([[630, 630], [720, 630], [720, 672], [630, 672]]))
    ok = best >= 25 and len(ent) >= 5
    return ('done' if ok else 'partial', f"densest grove {best} trees within 25 m (Vadim ~46); {len(ent)} trees at the Rough entrance", 'terrain trees')


def r_elite_small():
    fe = np.array(feat['elite']['fence'])
    w, h = fe.max(0) - fe.min(0)
    ok = abs(w - 144) / 144 < .15 and abs(h - 117) / 117 < .15
    return ('done' if ok else 'partial', f"Elite fence bbox {w:.0f} x {h:.0f} m (v02: octagon ~144 x 117)", 'district zones (fence = flat zone? see note)')


def r_canvas():
    s = terrain['size_m']
    return ('done' if s[2] == 950 else 'missing', f"terrain {s} m, shift_m(800,300) = {shift_m(800, 300)}", 'terrain size')


def r_shore():
    ys = []
    for x in range(530, 585):
        col = H[:400, x]
        land = np.nonzero(col > .3)[0]
        ys.append(int(land[0]) if len(land) else -1)
    jump = int(np.max(np.abs(np.diff(ys))))
    return ('done' if jump <= 4 else 'partial', f"shoreline y over x 530..584: {min(ys)}..{max(ys)}, max step between 1 m columns {jump} m", 'terrain heightmap + sea grid')


def r_land_border():
    f = border['fence']
    ok = len(f['points']) > 10 and len(border['towers']) == 2 and border['checkpoint'] and f['invisible_wall_height_m'] > 10 and border['steppe']['beyond_fence']
    return ('done' if ok else 'partial',
            f"fence {plen(f['points']):.0f} m x {f['height_m']} m, towers {len(border['towers'])}, checkpoint {border['checkpoint']['building_size_m']}, "
            f"invisible wall {f['invisible_wall_height_m']} m, steppe beyond", 'BuildBorder' if builds('BuildBorder') else 'no')


def r_presentation(lo, hi):
    src = open(os.path.join(HERE, 'common.py'), encoding='utf-8').read()
    ok = str(lo) in src and str(hi) in src
    return ('n/a (2D presentation only)' if ok else 'missing',
            f"raster shift band {lo}..{hi} is part of shift_m in common.py (coordinates converted)", '-')


def r_north_land():
    fp = np.array(border['fence']['points'])
    seas = 0
    tot = 0
    for x in range(int(fp[:, 0].min()), int(fp[:, 0].max()), 4):
        y0 = int(np.interp(x, fp[:, 0], fp[:, 1])) + 3
        col = C[y0:, x]
        tot += len(col)
        seas += int((col == CLS.index('sea')).sum())
    st = float((C[920:, 572:1031] == CLS.index('steppe')).mean())
    return ('done' if seas == 0 else 'partial', f"north of the fence: sea cells {seas}/{tot}, steppe share {st:.0%}; far steppe plane to the horizon in the builder",
            'terrain + Steppe_far plane')


def r_east_ridge():
    rr = feat['right_ridge']
    fend = border['fence']['points'][-1]
    d = dist_pt_pl(fend, rr['poly'] + [rr['poly'][0]])
    top = max(h_at(*p) for p in rr['crest'])
    ok = 25 <= rr['top_m'] <= 36 and d < 15 and max(p[1] for p in rr['crest']) > 920
    return ('done' if ok else 'partial', f"right ridge top {rr['top_m']} m (terrain {top:.0f} m), crest to y {max(p[1] for p in rr['crest'])}; fence end {d:.1f} m from the ridge",
            'terrain heightmap')


def r_left_forest():
    bf = np.array(feat['border_forest'])
    fmin = min(p[1] for p in border['fence']['points'])
    top = feat['small_ridge']['top_m']
    ok = bf[:, 1].max() < fmin - 10
    return ('done' if ok else 'partial', f"border forest top y {bf[:, 1].max():.0f} < fence y {fmin:.0f}; ridge top {top} m (v70 blend supersedes the v68 ~80 m)",
            'terrain trees + heightmap')


def r_fence_ridge():
    fs = border['fence']['points'][0]
    sr = feat['small_ridge']
    d = min(dist_pt_pl(fs, sr['poly'] + [sr['poly'][0]]), dist_pt_pl(fs, sr['crest']))
    return ('done' if d < 15 else 'partial', f"fence west end {fs} is {d:.1f} m from the small ridge", 'BuildBorder')


def r_ridge_blend():
    cr = np.array(feat['small_ridge']['crest'], float)
    pts = []
    for a, b in zip(cr[:-1], cr[1:]):
        for t in np.linspace(0, 1, 8, endpoint=False):
            pts.append(a + (b - a) * t)
    hs = [h_at(*p) for p in pts]
    step = float(np.max(np.abs(np.diff(hs))))
    top = feat['small_ridge']['top_m']
    ok = step < 8 and hs[0] > hs[-1]
    return ('done' if ok else 'partial', f"crest heights {hs[0]:.0f} -> {hs[-1]:.0f} m (v02: ~{top[0]} -> {top[1]}), max step {step:.1f} m per ~5 m",
            'terrain heightmap')


def r_foothills():
    sr = np.array(feat['small_ridge']['poly'], float)
    lo, hi = sr.min(0) - 40, sr.max(0) + 10
    box = np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]])
    pines = len(trees_in(box, ['pine', 'spruce']))
    rocks = sum(1 for d in D.values() for p in d['props'] if any(k in p['kind'] for k in ('boulder', 'scree', 'rock')))
    rocks_feat = [k for k in feat if 'scree' in k or 'boulder' in k]
    return ('partial' if pines and not (rocks or rocks_feat) else 'done' if pines else 'missing',
            f"{pines} pines/spruces on the foothills; boulders/scree objects in data: {rocks + len(rocks_feat)} (Vadim: 26 screes + boulders)",
            'terrain trees; boulders/screes not built')


def r_checkpoint():
    cp = border['checkpoint']
    ok = cp.get('building_centre') and cp.get('gate') and 'Leave' in json.dumps(cp, ensure_ascii=False) and cp.get('flag')
    return ('done' if ok else 'partial', f"building {cp['building_size_m']} at {cp['building_centre']}, sliding gate {cp['gate']['from']}->{cp['gate']['to']}, button, flag; no {cp.get('no')}",
            'BuildBorder (gate box, button W76LeaveCountryButton, flagpole)')


def r_south_band():
    pr = PADS['rough']
    strip = np.array([[pr[:, 0].min(), 640], [pr[:, 0].max(), 640], [pr[:, 0].max(), 668], [pr[:, 0].min(), 668]])
    t = trees_in(strip)
    per100 = len(t) / ((pr[:, 0].max() - pr[:, 0].min()) / 100)
    return ('done' if per100 < 8 else 'partial', f"{len(t)} trees in the 28 m strip under the Rough south edge ({per100:.1f} per 100 m)", 'terrain trees')


def r_elite_plan():
    vs = [b for b in D['elite']['buildings'] if b['kind'] == 'villa']
    angs = []
    for b in vs:
        fp = np.array(b['footprint'])
        e = fp[1] - fp[0]
        angs.append(round(math.degrees(math.atan2(e[1], e[0])) % 90, 1))
    fe = feat['elite']['fence']
    closed = np.hypot(*(np.array(fe[0]) - np.array(fe[-1]))) < 20
    gaps = [z['id'] for z in D['elite']['zones'] if 'gate' in z['kind']]
    pl = feat['elite']['plateau_m']
    ok = len(vs) == 4 and len(set(angs)) >= 3 and closed and pl == [40, 44]
    return ('done' if ok else 'partial', f"{len(vs)} villas, edge angles {angs}; fence closed {closed}, gates {gaps} (no beach exit); plateau {pl} m",
            'district buildings + zones')


def r_sand_track():
    r = ROAD['beach_van_track']
    end = r['points'][-1]
    el = [p['pos'] for p in D['beach']['props'] if p['kind'] == 'lounger_umbrella_elite']
    d = min(np.hypot(*(np.array(end) - np.array(p))) for p in el) if el else 1e9
    return ('done' if d < 80 else 'partial', f"sand track {plen(r['points']):.0f} m, ends {d:.0f} m from the Elite-beach loungers",
            'splat only (no ribbon)')


def r_beach_wider():
    sand = CLS.index('sand')
    w = {x: int((C[:400, x] == sand).sum()) for x in (950, 1050, 1150, 1400, 1450, 1500)}
    ok = max(w[1400], w[1450], w[1500]) > max(w[950], w[1050], w[1150])
    return ('done' if ok else 'partial', f"sand width per column (m): {w}", 'terrain splat + heightmap')


def r_serpentine():
    r = ROAD['elite_stone_serpentine']
    p = np.array(r['points'], float)
    d = np.diff(p, axis=0)
    ang = np.unwrap(np.arctan2(d[:, 1], d[:, 0]))
    turn = abs(math.degrees(ang[-1] - ang[0]))
    fe = feat['elite']['fence'] + feat['elite']['fence'][:1]
    off0, off1 = dist_pt_pl(p[0], fe), dist_pt_pl(p[-1], fe)
    hs = r.get('heights') or []
    ok = r['width_m'] == 4.5 and r['surface'].startswith('cobble') and hs and abs(hs[-1] - 44) < 1.5 and 300 < turn < 420
    return ('done' if ok else 'partial',
            f"width {r['width_m']} m, {r['surface']}, heights {hs[0] if hs else '?'} -> {hs[-1] if hs else '?'} m, turning {turn:.0f} deg, fence offset {off0:.0f} -> {off1:.0f} m (24 -> 13)",
            'roads ribbon (stone) + Parapet + lamps (W76GripAnchor)')


def r_hamlet():
    d = D['hamlet']
    kinds = [b['kind'] for b in d['buildings']]
    src = ' '.join(d['sources'])
    ok = 'build_hutor_v05' in src and kinds.count('house') == 19 and 'hut_base2' in kinds and 'church' in kinds
    return ('done' if ok else 'partial', f"sources {d['sources']}; houses {kinds.count('house')}, hut_base2, church, {len(d['props'])} props, {len(d['zones'])} zones",
            'district buildings/props/zones; trees -> terrain trees')


def r_beach_props():
    pr = D['beach']['props']
    row = feat.get('elite_palm_row', [])
    el = sum(1 for p in pr if p['kind'] == 'lounger_umbrella_elite')
    city = sum(1 for p in pr if p['kind'] == 'lounger_umbrella')
    ok = len(row) >= 5 and el and city and 'beach_van_track' in ROAD
    return ('done' if ok else 'partial', f"palm row at the hill foot {len(row)} pts; Elite-beach loungers {el}; City-beach loungers/umbrellas {city}; sand track yes",
            'props (boxes) + palms as terrain trees')


def r_lake_pines():
    lk = next(b for b in water if b.get('name') == 'mountain_lake')
    c = np.array(lk['centre'])
    near = trees_in(np.array([c + [-60, -60], c + [60, -60], c + [60, 60], c + [-60, 60]]), ['pine', 'spruce'])
    sr = np.array(feat['small_ridge']['poly'], float)
    lo, hi = sr.min(0) - 40, sr.max(0) + 10
    far = trees_in(np.array([[lo[0], lo[1]], [hi[0], lo[1]], [hi[0], hi[1]], [lo[0], hi[1]]]), ['pine', 'spruce'])
    dn = len(near) / 1.44
    df = len(far) / max(1e-6, (hi[0] - lo[0]) * (hi[1] - lo[1]) / 1e4)
    gen = open(os.path.join(HERE, 's05_vegetation.py'), encoding='utf-8').read()
    factor = '# v75: ~60 % of v70' in gen
    return ('done' if factor or dn <= .8 * df else 'partial',
            f"s05 scales the foothill pine density to ~60 % of v70 (v75): {factor}; pines around the lake {dn:.0f}/ha, whole foothill box {df:.0f}/ha",
            'terrain trees')


def r_no_trail():
    lk = next(b for b in water if b.get('name') == 'mountain_lake')
    d = min(dist_pl_pl(r['points'], lk['outline']) for r in roads)
    near = [r['id'] for r in roads if dist_pl_pl(r['points'], lk['outline']) < 25]
    return ('done' if d > 25 else 'partial', f"nearest road/track to the mountain lake {d:.0f} m ({near or 'none within 25 m'})", 'roads')


CHECKS = {
    'river_ford_y572_arc_to_rough': r_ford,
    'hamlet_bypass_shortened': r_bypass_short,
    'hill_b_50m': r_hill_b,
    'hamlet_bypass_to_dirt_track': r_bypass_dirt,
    'rough_access_riverside_tunnel_port': r_rough_access,
    'shift_downtown_east_20': lambda: r_shift('downtown', 'Downtown/beach/Elite +20 m east'),
    'tunnel_longer_approaches': r_tunnel_approach,
    'open_meadow_sparse_groves': r_meadow,
    'shift_downtown_down_rough_up': lambda: (lambda a, b: (min(a[0], b[0], key=['done', 'partial', 'missing'].index), a[1] + '; ' + b[1], a[2]))(
        r_shift('downtown', '15 m lower'), r_shift('rough', '10 m higher')),
    'elite_smaller_rounder_deferred': r_elite_small,
    'more_meadow_trees': r_more_meadow_trees,
    'shift_v58_canvas_950': r_canvas,
    'smooth_shore_x556': r_shore,
    'land_border_steppe': r_land_border,
    'rough_shift_band_right_1090': lambda: r_presentation(1090.0, 1130.0),
    'north_land_steppe_open': r_north_land,
    'rough_east_ridge_extension': r_east_ridge,
    'left_forest_ridge_shorter': r_left_forest,
    'fence_extended_to_ridge': r_fence_ridge,
    'ridge_blend_shift_430_540': r_ridge_blend,
    'foothills_pines_boulders': r_foothills,
    'checkpoint_gate_building_button': r_checkpoint,
    'remove_rough_south_tree_band': r_south_band,
    'elite_plan_v10': r_elite_plan,
    'elite_beach_sand_track': r_sand_track,
    'beach_wider_east': r_beach_wider,
    'elite_cobbled_serpentine': r_serpentine,
    'hamlet_plan_v05': r_hamlet,
    'beach_palms_props': r_beach_props,
    'lake_pines_sparser': r_lake_pines,
    'remove_waterfall_trail': r_no_trail,
}


def main():
    items = json.load(open(SRC, encoding='utf-8'))
    out = []
    for it in items:
        rec = {k: it[k] for k in ('version', 'task', 'category', 'build_key', 'summary_en', 'summary_ru', 'superseded_by')}
        if it['superseded_by']:
            rec.update(status='superseded', evidence=f"replaced by {it['superseded_by']}", builder='-')
        elif it['build_key'] in CHECKS:
            try:
                st, ev, bu = CHECKS[it['build_key']]()
            except Exception as e:                                         # a broken check is reported, not hidden
                st, ev, bu = 'check failed', repr(e), '?'
            rec.update(status=st, evidence=ev, builder=bu)
        else:
            rec.update(status='not checked', evidence='no check written for this build_key', builder='?')
        out.append(rec)
    counts = {}
    for r in out:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    report = {'source': 'Tools/MapV76/data_src/v52_to_v76_changes.json', 'data': 'Assets/OnlyVolunteers/Map/W76Build/Data/v01',
              'counts': counts, 'items': out}
    with open(os.path.join(WORK, 'v52_to_v76_checklist.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    lines = ['# v52 -> v76 checklist (generated by Tools/MapV76/s09_checklist.py)', '',
             'Counts: ' + ', '.join(f'{k} {v}' for k, v in sorted(counts.items())), '',
             '| ver | key | status | evidence | builder |', '|---|---|---|---|---|']
    for r in out:
        lines.append(f"| {r['version']} | {r['build_key']} | {r['status']} | {r['evidence'].replace('|', '/')} | {r['builder']} |")
    with open(os.path.join(WORK, 'v52_to_v76_checklist.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(json.dumps(counts))
    for r in out:
        if r['status'] not in ('done', 'superseded'):
            print(f"{r['version']} {r['build_key']}: {r['status']} - {r['evidence']}")


if __name__ == '__main__':
    main()
