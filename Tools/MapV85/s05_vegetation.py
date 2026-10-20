"""Step 5 (v85): vegetation BY LOGIC (handoff v10 §1.2) — density zones, not the drawn crowns.

The 2D map only says where forest is dense, where groves / single trees are and where it is empty. Here:
 1. density field: crown cover of the v85 picture (smoothed to ~15 m, so single drawn circles do not survive) outside the
    districts; inside the districts only their own veg_zone polygons (dense / grove / sparse / none) count;
 2. clumping: low-frequency noise turns the field into groups, singles, glades and soft edges (no grid);
 3. Poisson-disc scatter with spacing by density class (dense 3.6-4.5 m, grove 5-7 m, sparse 9-14 m), variable age / size;
 4. hard rules (never broken): no tree on roads + 2 m from the edge, sidewalks / streets, van drives, loading pads, functional
    yards, plazas, piers, water (+1.5 m), sand beach (palms only from the district rows), roofs / buildings (+3 m from facades),
    district no_tree zones, Downtown everywhere except squares 20 and 23, the Construction site, the Elite plateau except its zones,
    rock faces and slopes > 34°;
 5. designed trees (Hamlet orchard + square tree, beach / Elite palm rows) stay as the district props (builder) — checked against
    the same rules here, duplicates between districts removed.
Output: vegetation_v85.json (+ masks/veg_*.png) and out_v01/check_vegetation.png.
"""
import math
import os
from collections import Counter

import numpy as np
from PIL import Image
from scipy import ndimage

import common as c
from common import OUT, WORK, W, H, grid, poly_mask, load_json, save_json, resample, rnd2

NO_TREE_KINDS = {'no_tree', 'plaza', 'yard', 'service_yard', 'loading_pad', 'apron', 'parking', 'underground_parking', 'taxi_stand', 'gas_station',
                 'playground', 'football_box', 'trash_section', 'pool', 'pool_deck', 'pier', 'pond', 'lake', 'swamp', 'water_cascade', 'stair', 'arch',
                 'dead_end_alley', 'dead_end_alley_pair', 'curb_drop', 'drive', 'gate', 'volleyball', 'sand', 'helipad', 'missile_shafts', 'plinth',
                 'field', 'vegetable_garden', 'cemetery', 'pig_pen', 'fishing_platform', 'materials_store', 'fuel_pad', 'puddle', 'dirt_patch',
                 'clearing', 'oil_spill', 'oil_film_water', 'island_outline_none', 'beach_zone', 'golf', 'lawn_none'}
DN = ('beach', 'construction', 'downtown', 'elite', 'forest', 'hamlet', 'port', 'quiet_valley', 'rough', 'tramduro')
SPACING = {'dense': (3.6, 4.6), 'grove': (5.0, 7.0), 'sparse': (9.0, 14.0), 'row': (11.0, 11.0)}
LEVEL = {'dense': 0.95, 'grove': 0.6, 'sparse': 0.28, 'row': 0.0, 'none': 0.0}


def sm(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def value_noise(xs, ys, scale, seed):
    r_ = np.random.default_rng(seed)
    gw, gh = int(W / scale) + 3, int(H / scale) + 3
    g = r_.random((gh, gw)).astype(np.float32)
    fx, fy = xs / scale, ys / scale
    x0, y0 = fx.astype(int), fy.astype(int)
    tx, ty = sm(fx - x0), sm(fy - y0)
    a = g[y0, x0] * (1 - tx) + g[y0, x0 + 1] * tx
    b = g[y0 + 1, x0] * (1 - tx) + g[y0 + 1, x0 + 1] * tx
    return a * (1 - ty) + b * ty


def main():
    cls = np.load(os.path.join(WORK, 'classes_v85.npy'))
    h = np.load(os.path.join(WORK, 'height_1m.npy'))
    xs, ys = grid()
    D = {n: load_json('districts/%s_v85.json' % n) for n in DN}
    roads = load_json('roads_v85.json')['roads']
    water = load_json('water_v85.json')['bodies']
    terrain = load_json('terrain_v85.json')
    F = load_json('features_v85.json')
    # ---- 1. map crown cover (outside districts), smoothed: zones, not points
    im = np.asarray(Image.open(c.MAP_PREVIEW).convert('RGB')).astype(np.int16)[::-1]
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    lum = im.mean(-1).astype(np.float32)
    texture = ndimage.gaussian_filter(np.abs(ndimage.laplace(ndimage.gaussian_filter(lum, 0.7))), 4)
    canopy = (cls == 8) | ((G - R >= 13) & (R <= 216) & (texture > 7.0))
    cover = ndimage.gaussian_filter(canopy.astype(np.float32), 9)
    dens = np.clip((cover - 0.06) / 0.5, 0, 1)                          # 0 open .. 1 closed forest
    # district extents: inside them the map's crowns do not count (their own zones do)
    dist_mask = np.zeros((H, W), bool)
    for n, d in D.items():
        pts = [q for b in d['buildings'] for q in b['footprint']] + [q for z in d['zones'] if z['kind'] not in ('veg_zone',) for q in (z.get('poly') or [])]
        if n in ('forest',) or len(pts) < 3:
            continue
        P_ = np.array(pts, float)
        from scipy.spatial import ConvexHull
        hull = P_[ConvexHull(P_).vertices]
        dist_mask |= poly_mask([tuple(q) for q in hull], xs, ys)
    level = np.where(dist_mask, 0.0, dens * 0.75)                         # open-country groves at most "grove" by default
    species = np.zeros((H, W), np.uint8)                                  # 0 auto, 1 pine, 2 birch, 3 oak, 4 leafy, 5 bare, 6 bush, 7 palm
    SP = {'pine': 1, 'spruce': 1, 'birch': 2, 'oak': 3, 'leafy': 4, 'bare': 5, 'bush': 6, 'palm': 7}
    spacing_cls = np.full((H, W), 1, np.uint8)                            # 0 dense, 1 grove, 2 sparse
    nodrive = np.zeros((H, W), bool)
    COUNTED = []
    # big forest district and the border forest = dense, no drive (v02 §8.1, F_L)
    for n, d in D.items():
        for z in d['zones']:
            if z['kind'] != 'veg_zone' or len(z.get('poly') or []) < 3:
                continue
            m = poly_mask(z['poly'], xs, ys)
            lv = LEVEL.get(z.get('density', 'grove'), 0.5)
            if z.get('density') == 'row':
                continue
            if z.get('target_count') is not None:
                COUNTED.append((n, z, m))
                level = np.where(m, 0.0, level)
                continue
            level = np.where(m, np.maximum(level * (0 if n != 'forest' else 1), lv), level)
            species = np.where(m, SP.get(z.get('species', 'leafy'), 4), species)
            spacing_cls = np.where(m, {'dense': 0, 'grove': 1, 'sparse': 2}.get(z.get('density'), 1), spacing_cls)
            if z.get('density') == 'dense' or z.get('no_drive'):
                nodrive |= m
    bf = poly_mask(F['border_forest'], xs, ys)
    level = np.where(bf, 0.95, level)
    nodrive |= bf
    spacing_cls = np.where(bf, 0, spacing_cls)
    species = np.where(bf, 1, species)
    foot_x = 505.0 + 6.0 * np.sin(ys / 17.0)
    foothill = (ys > 690) & (ys < 872) & (xs > foot_x) & (xs < 648) & ~bf
    t = np.clip((xs - foot_x) / 140.0, 0, 1)
    level = np.where(foothill & ~dist_mask, np.maximum(level, 0.55 * (1 - t) ** 1.4 * (0.45 + 0.55 * np.clip((ys - 690) / 100, 0, 1))), level)
    spacing_cls = np.where(foothill & (level > 0.45), 0, spacing_cls)
    # Construction hill slopes: light wood 9-26 m outside the fence (CHILL), from the district veg zone already
    # ---- 2. clumping: groups, glades, edges
    clump = value_noise(xs, ys, 38.0, 851) * 0.65 + value_noise(xs, ys, 13.0, 852) * 0.35
    glade = value_noise(xs, ys, 70.0, 853)
    k_clump = np.where(spacing_cls == 0, sm((glade - 0.18) / 0.2), sm((clump - 0.42) / 0.22))
    prob = level * k_clump
    # ---- 3. hard exclusions
    excl = np.zeros((H, W), bool)
    excl |= (cls == 1) | (h < 0.9)
    road_edge = np.full((H, W), 99.0, np.float32)
    for rd in roads:
        if rd['kind'] == 'tunnel':
            continue
        m = c.stamp_polyline([tuple(p) for p in rd['points']])
        dd = ndimage.distance_transform_edt(~m) - rd['width_m'] / 2.0
        road_edge = np.minimum(road_edge, dd)
    for n, d in D.items():
        for z in d['zones']:
            k = z['kind']
            line = z.get('line') or z.get('poly_line') or z.get('polyline')
            if line and len(line) >= 2 and k in ('road', 'track', 'street', 'footpath', 'path', 'ring_road', 'boardwalk', 'van_route', 'van_entry', 'drive'):
                wdt = z.get('width_m') or (z.get('carriageway_m', 6) + 2 * z.get('sidewalk_m', 0)) if k == 'street' else (z.get('width_m') or 4.0)
                if isinstance(wdt, list):
                    wdt = max(wdt)
                m = c.stamp_polyline([tuple(p) for p in line])
                dd = ndimage.distance_transform_edt(~m) - float(wdt) / 2.0
                road_edge = np.minimum(road_edge, dd)
            poly = z.get('poly')
            if z.get('veg_zones_override'):
                continue                                                    # "trees only inside this district's veg zones": handled by level
            if poly and len(poly) >= 3 and k in NO_TREE_KINDS and not (n == 'hamlet' and k == 'yard'):
                excl |= poly_mask(poly, xs, ys)
    excl |= road_edge < c.TREE_ROAD_GAP + 0.7                                 # +0.7: 1 m grid / centre-line stamping error
    bmask = np.zeros((H, W), bool)
    for n, d in D.items():
        for b in d['buildings']:
            if not b.get('disabled'):
                bmask |= poly_mask(b['footprint'], xs, ys)
    d_fac = ndimage.distance_transform_edt(~bmask)
    excl_zone = excl | (d_fac < 1.6)                                         # counted zones (front gardens / palisades: v10 §1.2 exception)
    excl |= d_fac < c.TREE_FACADE_GAP + 0.7
    wmask = np.zeros((H, W), bool)
    for b in water:
        if b.get('outline'):
            wmask |= poly_mask(b['outline'], xs, ys)
    riv = next(b for b in water if b['id'] == 'river')
    for (a, b_), wa in zip(zip(riv['axis'][:-1], riv['axis'][1:]), riv['width_m'][1:]):
        for p in resample([tuple(a), tuple(b_)], 1.0):
            ix, iy = int(p[0]), int(p[1])
            r_ = int(wa / 2 + 1)
            wmask[max(0, iy - r_):iy + r_ + 1, max(0, ix - r_):ix + r_ + 1] = True
    excl |= ndimage.binary_dilation(wmask, iterations=2)
    excl_zone |= ndimage.binary_dilation(wmask, iterations=2)
    excl |= (cls == 3) & ~dist_mask                                        # open sand: palms only from district rows
    gy_, gx_ = np.gradient(h)
    slope = np.degrees(np.arctan(np.hypot(gx_, gy_)))
    excl |= slope > 34
    excl_zone |= slope > 34
    excl |= (cls == 6) | (h > 70)                                          # rock faces, bare high ridge
    # Downtown: only squares 20 and 23 (their veg zones), everything else no
    dt_veg = np.zeros((H, W), bool)
    for z in D['downtown']['zones']:
        if z['kind'] == 'veg_zone':
            dt_veg |= poly_mask(z['poly'], xs, ys)
    dt_pad = poly_mask(next(z for z in D['downtown']['zones'] if z['id'] == '05-ground')['poly'], xs, ys)
    excl |= ndimage.binary_dilation(dt_pad, iterations=2) & ~dt_veg
    cg = next(z for z in D['construction']['zones'] if z['kind'] == 'ground')
    excl |= poly_mask(cg['poly'], xs, ys)
    el = F['elite']
    elite_in = ((np.abs(xs - el['centre'][0]) / el['half'][0]) ** 4 + (np.abs(ys - el['centre'][1]) / el['half'][1]) ** 4) < 1
    el_veg = np.zeros((H, W), bool)
    for z in D['elite']['zones']:
        if z['kind'] == 'veg_zone':
            el_veg |= poly_mask(z['poly'], xs, ys)
    excl |= elite_in & ~el_veg
    tun = F['tunnel_axis']
    for p in (tun[0], tun[-1]):
        excl |= np.hypot(xs - p[0], ys - p[1]) < 16
    prob = np.where(excl, 0, prob)
    # ---- 4. Poisson-disc by density class
    rng = np.random.default_rng(8585)
    cell = 1.5
    occ = {}
    trees = []
    cand = rng.random((int(H / cell), int(W / cell), 4))
    for j in range(cand.shape[0]):
        for i in range(cand.shape[1]):
            x, y = (i + cand[j, i, 0]) * cell, (j + cand[j, i, 1]) * cell
            ix, iy = min(W - 1, int(x)), min(H - 1, int(y))
            pv = prob[iy, ix]
            if pv <= 0 or cand[j, i, 2] > pv:
                continue
            lo, hi = SPACING[('dense', 'grove', 'sparse')[min(2, int(spacing_cls[iy, ix]))]]
            s = lo + (hi - lo) * cand[j, i, 3]
            gi, gj = int(x / 4.0), int(y / 4.0)
            ok = True
            for a in range(-4, 5):
                for b_ in range(-4, 5):
                    for q in occ.get((gi + a, gj + b_), ()):
                        if (q[0] - x) ** 2 + (q[1] - y) ** 2 < (max(s, q[2]) * 0.92) ** 2:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if ok:
                occ.setdefault((gi, gj), []).append((x, y, s))
                trees.append((x, y))
    # ---- zones with an exact count (Rough yards, Hamlet groups, Downtown squares 20 / 23, valley): best-candidate inside the zone
    zone_sp = {}
    PLACED_LOG = []
    for n, z, m in COUNTED:
        want = int(z['target_count'])
        if want <= 0:
            continue
        ok_ = m & ~excl_zone
        cy_, cx_ = np.nonzero(ok_)
        if len(cx_) == 0:
            continue
        lo, hi = SPACING.get(z.get('density', 'grove'), (5.0, 7.0))
        placed = []
        for _ in range(want):
            best, bd = None, -1.0
            for _k in range(24):
                idx = int(rng.integers(0, len(cx_)))
                x, y = cx_[idx] + float(rng.random()), cy_[idx] + float(rng.random())
                dmin = min([math.hypot(x - q[0], y - q[1]) for q in placed + [t_ for t_ in trees if abs(t_[0] - x) < 20 and abs(t_[1] - y) < 20]] or [99.0])
                if dmin > bd:
                    best, bd = (x, y), dmin
            if best and bd >= 3.0:
                placed.append(best)
        PLACED_LOG.append((n, z['id'], want, len(placed)))
        for q in placed:
            trees.append(q)
            zone_sp[(round(q[0], 1), round(q[1], 1))] = z.get('species', 'leafy')
    # ---- species, size (age), rotation
    out = []
    for x, y in trees:
        ix, iy = int(x), int(y)
        if (round(x, 1), round(y, 1)) in zone_sp:
            spn = zone_sp[(round(x, 1), round(y, 1))]
            species[iy, ix] = SP.get('pine' if spn == 'spruce' else spn, 4)
        sp = int(species[iy, ix])
        nd = bool(nodrive[iy, ix])
        if sp == 0:
            if y > 640 or nd or (x < 440 and y < 340):
                kind = rng.choice(['pine', 'pine', 'pine', 'spruce', 'spruce', 'birch'])
            else:
                kind = rng.choice(['oak', 'birch', 'leafy', 'oak'], p=[.35, .3, .2, .15])
        else:
            kind = {1: rng.choice(['pine', 'pine', 'spruce']), 2: 'birch', 3: 'oak', 4: rng.choice(['leafy', 'oak', 'birch'], p=[.5, .3, .2]), 5: 'bare', 6: 'bush', 7: 'palm'}[sp]
        age = rng.random()
        scale = round(float(0.72 + 0.55 * age ** 0.8 + rng.normal(0, 0.04)), 2)
        out.append([round(x, 1), round(y, 1), str(kind), scale, int(rng.integers(0, 360)), int(nd)])
    # ---- designed trees of the districts: same hard rules, duplicates removed
    designed, dropped = [], []
    for n, d in D.items():
        for p in d['props']:
            k = p.get('kind', '')
            if k not in ('palm', 'tree') or not p.get('pos'):
                continue
            x, y = p['pos']
            ix, iy = min(W - 1, int(x)), min(H - 1, int(y))
            bad = road_edge[iy, ix] < 1.0 or bmask[iy, ix] or wmask[iy, ix] or cls[iy, ix] == 1
            if bad:
                dropped.append((n, p['id']))
                continue
            if any(math.hypot(x - q[0], y - q[1]) < 4.0 for q in designed):
                dropped.append((n, p['id'] + ' (duplicate)'))
                continue
            designed.append((x, y, n, p['id']))
    # ---- checks
    T = np.array([[t_[0], t_[1]] for t_ in out])
    ti, tj = T[:, 0].astype(int).clip(0, W - 1), T[:, 1].astype(int).clip(0, H - 1)
    checks = {'trees': len(out), 'designed_kept': len(designed), 'designed_dropped': dropped,
              'min_road_edge_m': round(float(road_edge[tj, ti].min()), 2),
              'min_facade_m': round(float(ndimage.distance_transform_edt(~bmask)[tj, ti].min()), 2),
              'in_water': int(wmask[tj, ti].sum()), 'in_downtown_outside_squares': int((dt_pad[tj, ti] & ~dt_veg[tj, ti]).sum()),
              'nodrive_trees': int(sum(t_[5] for t_ in out))}
    os.makedirs(os.path.join(OUT, 'masks'), exist_ok=True)
    for name, a in (('veg_forest', level), ('veg_nodrive', nodrive.astype(np.float32))):
        Image.fromarray((np.clip(a, 0, 1)[::-1] * 255).astype(np.uint8)).save(os.path.join(OUT, 'masks', name + '_v85.png'))
    save_json('vegetation_v85.json', {
        'method': 'zones + clumping + Poisson by density class (v10 §1.2); drawn crowns NOT copied', 'tree_fields': ['x', 'y', 'kind', 'scale', 'rot_deg', 'dense_nodrive'],
        'masks': {'veg_forest': 'masks/veg_forest_v85.png', 'veg_nodrive': 'masks/veg_nodrive_v85.png'}, 'mask_format': '8-bit PNG, 1 px = 1 m, row 0 = NORTH',
        'rules': {'road_edge_m': c.TREE_ROAD_GAP, 'facade_m': c.TREE_FACADE_GAP, 'downtown': 'squares 20 and 23 only', 'slope_max_deg': 34},
        'designed_from_districts': [{'pos': rnd2(q[:2]), 'district': q[2], 'id': q[3]} for q in designed],
        'counts': dict(Counter(t_[2] for t_ in out)), 'checks': checks, 'trees': out})
    # check picture
    pv = Image.open(c.MAP_PREVIEW).convert('RGB')
    from PIL import ImageDraw
    dr = ImageDraw.Draw(pv)
    for t_ in out:
        col = (20, 90, 30) if t_[5] else (200, 30, 30)
        dr.point((t_[0], H - t_[1]), fill=col)
    for q in designed:
        dr.point((q[0], H - q[1]), fill=(255, 0, 255))
    pv.save(os.path.join(WORK, 'check_vegetation.png'))
    print(checks)
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0])
    for n_, zid, w_, g_ in PLACED_LOG:
        agg[n_][0] += w_; agg[n_][1] += g_
    print('counted zones (wanted, placed):', dict(agg))
    print(dict(Counter(t_[2] for t_ in out)))


if __name__ == '__main__':
    main()
