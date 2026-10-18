"""Step 7: terrain layer weights (splat) for map v76, approved layers L01–L10 (handoff v02 §7.1).

Output: Data/v01/masks/splat_{0,1,2}_v76.png — RGBA, 1 px = 1 m, row 0 = NORTH; channel order = LAYERS below
(splat_0 = L01..L04, splat_1 = L05..L08, splat_2 = L09, L10, -, -). Weights sum to 1.
Rules: meadow everywhere; forest floor under forest density; worn grass = Rough dry ground + steppe (soft halo, not "stuck on");
white sand, wet sand ~1.5 m band at the waterline; gravel = rural-road shoulders + scree at the ridge foot; rock = mountains / crags / slopes > 38°;
lawn = Downtown verges, Elite, Tramduro; dirt = village streets, tracks, Construction yard; fields from the Hamlet zones.
"""
import os

import numpy as np
from PIL import Image
from scipy import ndimage

from common import OUT, REV, WORK, W, H, grid, poly_mask, load_json, resample

LAYERS = ['L01_meadow', 'L02_worn_grass', 'L03_dirt_SK1b', 'L04_forest_floor_p10', 'L05_sand_white', 'L05b_sand_wet', 'L06_gravel_SK1d',
          'L07_rock_macro', 'L08_lawn_park', 'L09_field_plowed', 'L10_field_stubble']


def main():
    cls = np.load(os.path.join(WORK, 'classes_v76.npy'))
    h = np.load(os.path.join(WORK, 'height_1m.npy'))
    xs, ys = grid()
    gy, gx = np.gradient(h)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    forest = np.asarray(Image.open(os.path.join(OUT, 'masks', 'veg_forest_v76.png')), np.float32)[::-1] / 255
    sea = cls == 1
    w = np.zeros((len(LAYERS), H, W), np.float32)
    w[0] = 1.0
    w[3] = np.clip(forest * 1.4, 0, 1)
    dry = ndimage.gaussian_filter(((cls == 10) | (cls == 7) | (ys > 905)).astype(np.float32), 6)            # soft halo
    w[1] = np.clip(dry * 1.5, 0, 1)
    sand = ndimage.gaussian_filter(ndimage.binary_closing(cls == 3, iterations=2).astype(np.float32), 1.5)
    w[4] = sand
    wet = (ndimage.distance_transform_edt(~sea) < 9.0) & ~sea & (ndimage.distance_transform_edt(sand < 0.3) < 12)   # foam band drawn between sand and sea
    w[5] = ndimage.gaussian_filter(wet.astype(np.float32), 0.8)
    roads = load_json('roads_v76.json')['roads']
    shoulder = np.zeros((H, W), bool)
    track = np.zeros((H, W), bool)
    for rd in roads:
        pts = resample([tuple(p) for p in rd['points']], 1.5)
        m = np.zeros((H, W), bool)
        for p in pts:
            if 0 <= p[0] < W and 0 <= p[1] < H:
                m[int(p[1]), int(p[0])] = True
        d = ndimage.distance_transform_edt(~m)
        if rd['kind'] in ('rural_asphalt', 'serpentine'):
            shoulder |= (d > rd['width_m'] / 2 - 0.3) & (d < rd['width_m'] / 2 + 1.2)
        elif rd['kind'] in ('dirt_from_map', 'sand_track'):
            track |= d < rd['width_m'] / 2 + 0.5
    foot = ndimage.binary_dilation((cls == 5), iterations=6) & ~(cls == 5) & (h > 6)
    w[6] = ndimage.gaussian_filter((shoulder | foot).astype(np.float32), 0.8)
    rock = (cls == 5) & (h > 22) | (cls == 6) | (slope > 38)
    tpath = os.path.join(OUT, 'districts', 'tramduro_v76.json')
    if REV != 'v01' and os.path.exists(tpath):                          # v02: Tramduro yard / lawn are not rock (crags on the shore only)
        import json
        inner = np.zeros((H, W), bool)
        for z in json.load(open(tpath, encoding='utf-8'))['zones']:
            if z.get('kind') in ('continuous_concrete_base', 'coastal_presidential_lawn') and len(z.get('poly') or []) >= 3:
                inner |= poly_mask(z['poly'], xs, ys)
        rock &= ~ndimage.binary_erosion(inner, iterations=2) | (slope > 38)
    w[7] = ndimage.gaussian_filter(rock.astype(np.float32), 1.0)
    pads = load_json('terrain_v76.json')['pads']
    F = load_json('features_v76.json')
    lawn = poly_mask(pads['downtown']['poly'], xs, ys) | (((np.abs(xs - F['elite']['centre'][0]) / F['elite']['half'][0]) ** 4 +
                                                         (np.abs(ys - F['elite']['centre'][1]) / F['elite']['half'][1]) ** 4) < 1) | ((xs > 1440) & (ys > 640) & (cls == 0))
    w[8] = ndimage.gaussian_filter(lawn.astype(np.float32), 1.5)
    site = pads['construction']['poly']
    cpath = os.path.join(OUT, 'districts', 'construction_v76.json')
    if REV != 'v01' and os.path.exists(cpath):                          # v02: dirt inside the site fence (contour of v76), not the pad rectangle
        import json
        g = [z for z in json.load(open(cpath, encoding='utf-8'))['zones'] if z.get('kind') == 'ground' and z.get('poly')]
        if g:
            site = g[0]['poly']
    yard = ndimage.binary_dilation(poly_mask(site, xs, ys), iterations=2) | (cls == 9) | track
    w[2] = ndimage.gaussian_filter(yard.astype(np.float32), 1.0)
    dpath = os.path.join(OUT, 'districts', 'hamlet_v76.json')
    if os.path.exists(dpath):
        import json
        for z in json.load(open(dpath, encoding='utf-8')).get('zones', []):
            k = (z.get('kind', '') + ' ' + str(z.get('surface', ''))).lower()
            if 'poly' in z and ('field' in k or 'plough' in k or 'plow' in k or 'stubble' in k or 'garden_bed' in k or 'ogorod' in k):
                m = poly_mask(z['poly'], xs, ys)
                w[10 if 'stubble' in k else 9] = np.maximum(w[10 if 'stubble' in k else 9], m)
    if REV != 'v01':                                                    # v02: no meadow under water (clear water shows the bed)
        w[4] = np.maximum(w[4], ndimage.gaussian_filter(sea.astype(np.float32), 1.0))          # sea floor: white sand
        w[2] = np.maximum(w[2], ndimage.gaussian_filter((cls == 2).astype(np.float32), 1.0) * ~sea)   # river / lake beds: dirt
    # priority: later layers override earlier where strong
    order = [0, 3, 1, 8, 2, 9, 10, 6, 4, 5, 7]
    acc = np.zeros((len(LAYERS), H, W), np.float32)
    rest = np.ones((H, W), np.float32)
    for i in order[::-1]:
        a = np.clip(w[i], 0, 1) * rest if i != 0 else rest
        acc[i] = a
        rest = rest - a
    acc /= np.maximum(acc.sum(0), 1e-6)
    os.makedirs(os.path.join(OUT, 'masks'), exist_ok=True)
    for k in range(3):
        ch = [acc[4 * k + c] if 4 * k + c < len(LAYERS) else np.zeros((H, W), np.float32) for c in range(4)]
        img = (np.stack(ch, -1)[::-1] * 255 + 0.5).astype(np.uint8)
        Image.fromarray(img, 'RGBA').save(os.path.join(OUT, 'masks', 'splat_%d_v76.png' % k))
    t = load_json('terrain_v76.json')
    t['splat'] = {'files': ['masks/splat_%d_v76.png' % k for k in range(3)], 'layers': LAYERS,
                  'format': 'RGBA 8-bit, 1 px = 1 m (1744 x 950), row 0 = NORTH; layer i = file i//4, channel i%4'}
    from common import save_json
    save_json('terrain_v76.json', t)
    print({L: round(float(acc[i].mean()), 3) for i, L in enumerate(LAYERS)})


if __name__ == '__main__':
    main()
