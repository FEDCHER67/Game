"""Step 5: vegetation of map v76 — density masks + deterministic tree instances (handoff v02 §2, §8.1, §8.9).

Masks (1 m, PNG 8-bit, row 0 = north like the map): veg_forest (canopy density read from the drawn crowns / forest fill),
veg_nodrive (dense forest + border forest + foothill pines: trunks 3–6 m apart, capsule colliders),
veg_swamp, veg_grass (grass density: 0 on roads/water/pads/sand, thinner near roads).
Trees: Poisson-disc scatter driven by the masks; spacing 3.5–6 m in dense forest, groves elsewhere where the map draws
crowns. Trees come right up to the districts (no square clearings): only roads (+2 m), water and building footprints
(district JSONs) are excluded. District-owned trees (Hamlet, Rough, beach palms, Downtown squares) come from the district files.
Output: Data/v01/vegetation_v76.json, masks in Data/v01/masks/.
"""
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage

from common import MAP_FULL, MAP_PREVIEW, OUT, REV, WORK, W, H, grid, poly_mask, load_json, save_json, resample, rnd2


def poisson(mask_density, spacing_fn, seed, max_n=60000):
    """Dart throwing on a jittered grid: candidate per cell, accepted with prob = density, min distance = spacing."""
    rng = np.random.default_rng(seed)
    pts = []
    cell = 2.0
    occ = {}
    ny, nx = mask_density.shape
    cand = rng.random((int(ny / cell), int(nx / cell), 3))
    for j in range(cand.shape[0]):
        for i in range(cand.shape[1]):
            x = (i + cand[j, i, 0]) * cell
            y = (j + cand[j, i, 1]) * cell
            dval = mask_density[min(ny - 1, int(y)), min(nx - 1, int(x))]
            if dval <= 0 or cand[j, i, 2] > dval:
                continue
            s = spacing_fn(x, y, dval)
            gi, gj = int(x / s), int(y / s)
            ok = True
            for a in (-1, 0, 1):
                for b in (-1, 0, 1):
                    for q in occ.get((gi + a, gj + b), ()):
                        if (q[0] - x) ** 2 + (q[1] - y) ** 2 < s * s:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if ok:
                occ.setdefault((gi, gj), []).append((x, y))
                pts.append((x, y))
                if len(pts) >= max_n:
                    return pts
    return pts


def drawn_crowns(tile=1200, pad=48):
    """v02: one tree per crown DRAWN on the full map (5 px/m): crowns are green discs darker than their local
    background; a tree sits at each distance-transform peak (radius 1.4-4.8 m). Returns [(x, y, r_m)] in world metres.
    (v01 scattered Poisson trees by canopy density, ~3x the drawn crowns in the open meadow; Vadim: 8 sparse groves,
    one grove of ~46 trees, single trees.)"""
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(MAP_FULL).convert('RGB')
    PW, PH = im.size
    out = []
    for ty in range(0, PH, tile):
        for tx in range(0, PW, tile):
            x0, y0 = max(0, tx - pad), max(0, ty - pad)
            x1, y1 = min(PW, tx + tile + pad), min(PH, ty + tile + pad)
            a = np.asarray(im.crop((x0, y0, x1, y1))).astype(np.int16)
            R, G = a[..., 0], a[..., 1]
            lum = a.mean(-1)
            crown = (G - R >= 10) & (lum < ndimage.uniform_filter(lum, 61) - 8)
            crown = ndimage.binary_opening(crown, iterations=2)
            dt = ndimage.distance_transform_edt(crown)
            pk = (dt == ndimage.maximum_filter(dt, size=13)) & (dt >= 7) & (dt <= 24)
            lab, n = ndimage.label(pk)
            if n == 0:
                continue
            cs = ndimage.center_of_mass(pk, lab, range(1, n + 1))
            rad = ndimage.maximum(dt, lab, range(1, n + 1))
            for (py, px), r in zip(cs, rad):
                gx, gy = px + x0, py + y0
                if tx <= gx < tx + tile and ty <= gy < ty + tile:
                    out.append((gx / 5.0, (PH - gy) / 5.0, float(r) / 5.0))
    return out


def main():
    cls = np.load(os.path.join(WORK, 'classes_v76.npy'))
    h = np.load(os.path.join(WORK, 'height_1m.npy'))
    xs, ys = grid()
    im = np.asarray(Image.open(MAP_PREVIEW).convert('RGB')).astype(np.int16)[::-1]
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    Lum = im.mean(-1).astype(np.float32)
    texture = ndimage.gaussian_filter(np.abs(ndimage.laplace(ndimage.gaussian_filter(Lum, 0.7))), 4)   # drawn crowns = busy texture
    canopy = (cls == 8) | ((G - R >= 13) & (R <= 216) & (texture > 7.0))        # crowns; flat hill-contour tints excluded
    dens = ndimage.gaussian_filter(canopy.astype(np.float32), 5)
    F = load_json('features_v76.json')
    roads = load_json('roads_v76.json')['roads']
    water = (cls == 1) | (cls == 2) | (cls == 13)
    block = water | (cls == 4) | (cls == 3) | (cls == 5) | (cls == 10) | (cls == 6)
    road_d = np.full((H, W), 99.0, np.float32)
    for rd in roads:
        if rd['kind'] == 'tunnel':
            continue
        m = np.zeros((H, W), bool)
        for p in resample([tuple(q) for q in rd['points']], 2.0):
            ix, iy = int(p[0]), int(p[1])
            if 0 <= ix < W and 0 <= iy < H:
                m[iy, ix] = True
        dd = ndimage.distance_transform_edt(~m) - rd['width_m'] / 2
        road_d = np.minimum(road_d, dd)
    pads = load_json('terrain_v76.json')['pads']
    padm = np.zeros((H, W), bool)
    for k, v in pads.items():
        if k in ('downtown', 'rough', 'port', 'construction'):
            padm |= poly_mask(v['poly'], xs, ys)
    elite = ((np.abs(xs - F['elite']['centre'][0]) / (F['elite']['half'][0] + 6)) ** 4 + (np.abs(ys - F['elite']['centre'][1]) / (F['elite']['half'][1] + 6)) ** 4) < 1
    district_owned = ((xs > 1440) & (ys > 640)) | ((xs > 785) & (xs < 1270) & (ys < 262))   # Tramduro, beach palm park
    excl = block | padm | elite | district_owned | (road_d < 2.0) | (h < 0.8)
    forest = np.where(excl, 0, np.clip(dens * 1.6, 0, 1)).astype(np.float32)
    # dense (no-drive) forest: the big forest district, border forest F_L, foothill pines (v70, denser at the mountain)
    big = ndimage.binary_opening(dens > 0.45, iterations=3)
    lab, n = ndimage.label(big)
    sizes = ndimage.sum(big, lab, range(1, n + 1))
    nodrive = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 12000]) | poly_mask(F['border_forest'], xs, ys)
    foot_x = 505.0 + 6.0 * np.sin(ys / 17.0)                                              # FOOT_X(y) of the big ridge (pre-shift = post here)
    foothill = (ys > 690) & (ys < 872) & (xs > foot_x) & (xs < 648)
    t = np.clip((xs - foot_x) / 140.0, 0, 1)
    foot_d = 0.46 * (1 - t) ** 1.6 * (0.45 + 0.55 * np.clip((ys - 690) / 100, 0, 1)) * 0.6 * 2.2      # v75: ~60 % of v70
    forest = np.maximum(forest, np.where(foothill & ~excl, foot_d, 0))
    nodrive &= ~excl
    swamp = ndimage.binary_dilation(cls == 13, iterations=2)
    grass = np.where(excl & ~((cls == 10)), 0, 1.0) * np.clip((road_d - 0.5) / 4.0, 0.25, 1)
    grass = np.where(cls == 10, 0.35, grass)                                               # Rough: sparse dry grass
    os.makedirs(os.path.join(OUT, 'masks'), exist_ok=True)
    for name, a in (('veg_forest', forest), ('veg_nodrive', nodrive.astype(np.float32)), ('veg_swamp', swamp.astype(np.float32)), ('veg_grass', grass)):
        Image.fromarray((np.clip(a, 0, 1)[::-1] * 255).astype(np.uint8)).save(os.path.join(OUT, 'masks', name + '_v76.png'))
    # instances
    def spacing(x, y, d):
        return 3.6 if nodrive[int(y), int(x)] else 5.0 + 4.0 * (1 - d)
    if REV == 'v01':
        pts = poisson(np.where(nodrive, 0.95, forest * 0.8), spacing, 76, 80000)
    else:
        # v02: Poisson only in the no-drive forest and the foothill pines (designed densities); everywhere else one tree
        # per drawn crown. District-owned trees (Hamlet layout, Rough, beach, Tramduro) are not duplicated.
        pts = poisson(np.where(nodrive, 0.95, np.where(foothill, forest * 0.8, 0)), spacing, 76, 80000)
        ham = load_json('districts/hamlet_v76.json')
        hp = np.array([p['pos'] for p in ham['props'] if 'pos' in p] + [q for b in ham['buildings'] for q in b['footprint']], float)
        from scipy.spatial import ConvexHull
        hull = hp[ConvexHull(hp).vertices]
        hamlet = ndimage.binary_dilation(poly_mask([tuple(q) for q in hull], xs, ys), iterations=6)
        skip = excl | nodrive | foothill | hamlet
        crowns = [(x, y) for x, y, r_ in drawn_crowns() if 0 <= x < W and 0 <= y < H and not skip[int(y), int(x)]]
        pts = list(pts) + crowns
        print('drawn crowns kept', len(crowns))
    rng = np.random.default_rng(7676)
    trees = []
    for x, y in pts:
        j, i = int(y), int(x)
        if excl[j, i]:
            continue
        nd = bool(nodrive[j, i])
        if ys[j, i] > 640 or nd:                                                          # north / forest district: Finnish pines
            kind = rng.choice(['pine', 'pine', 'pine', 'pine', 'spruce', 'birch'], p=[.22, .22, .2, .16, .14, .06])
        else:                                                                             # meadow groves: oak / birch (GROVES of v76)
            kind = rng.choice(['oak', 'birch', 'leafy'], p=[.45, .35, .2])
        trees.append([round(x, 1), round(y, 1), str(kind), round(float(rng.uniform(0.8, 1.25)), 2), int(rng.integers(0, 360)), int(nd)])
    from collections import Counter
    save_json('vegetation_v76.json', {
        'masks': {k: 'masks/%s_v76.png' % k for k in ('veg_forest', 'veg_nodrive', 'veg_swamp', 'veg_grass')},
        'mask_format': '8-bit PNG, 1 px = 1 m, 1744 x 950, row 0 = NORTH (as the map)',
        'tree_fields': ['x', 'y', 'kind', 'scale', 'rot_deg', 'dense_nodrive'],
        'tree_prefabs_hint': {'pine': 'Art/Trees/OaksPines_i09 (pine)', 'spruce': 'Fedya spruce v03', 'birch': 'Art/Trees/Leafy_v04_i08 (birch)',
                              'oak': 'Art/Trees/OaksPines_i09 (oak)', 'leafy': 'Art/Trees/Leafy_v04_i08'},
        'colliders': 'capsule on trunks (dense forest blocks the van), none on grass/soft bushes',
        'counts': dict(Counter(t_[2] for t_ in trees)), 'trees': trees})
    print(len(trees), 'trees', dict(Counter(t_[2] for t_ in trees)), 'nodrive m2', int(nodrive.sum()))


if __name__ == '__main__':
    main()
