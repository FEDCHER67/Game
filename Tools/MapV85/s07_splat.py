"""Step 7 (v85): terrain layer weights (splat), approved layers L01-L10 (handoff v02 §7.1, v10 §9).

Output: Data/<REV>/masks/splat_{0,1,2}_v85.png — RGBA, 1 px = 1 m, row 0 = NORTH; channel order = LAYERS
(splat_0 = L01..L04, splat_1 = L05..L08, splat_2 = L09, L10, -, -). Weights sum to 1.
Transitions are natural edges, never "a picture on a picture" (v10 §9): the Rough dry yellow-brown grass fades into the meadow over
40-80 m with a ragged noise edge (no halo ring); road shoulders = gravel strip; dirt roads = two ruts with grass in the middle;
white sand #F7F2E0 + wet band at the waterline; rock only on crags / steep faces; fields from the Hamlet zones; forest floor under
the dense forest; Construction yard dirt inside the fence; lawns (Elite plateau, Downtown squares, Quiet Valley, Tramduro).
"""
import os

import numpy as np
from PIL import Image
from scipy import ndimage

import common as c
from common import OUT, WORK, W, H, grid, poly_mask, load_json, save_json, resample

LAYERS = ['L01_meadow', 'L02_worn_grass', 'L03_dirt_SK1b', 'L04_forest_floor_p10', 'L05_sand_white', 'L05b_sand_wet', 'L06_gravel_SK1d',
          'L07_rock_macro', 'L08_lawn_park', 'L09_field_plowed', 'L10_field_stubble']


def sm(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def noise(xs, ys, scale, seed):
    r_ = np.random.default_rng(seed)
    gw, gh = int(W / scale) + 3, int(H / scale) + 3
    g = r_.random((gh, gw)).astype(np.float32)
    fx, fy = xs / scale, ys / scale
    x0, y0 = fx.astype(int), fy.astype(int)
    tx, ty = sm(fx - x0), sm(fy - y0)
    a = g[y0, x0] * (1 - tx) + g[y0, x0 + 1] * tx
    b = g[y0 + 1, x0] * (1 - tx) + g[y0 + 1, x0 + 1] * tx
    return a * (1 - ty) + b * ty


def line_dist(pl):
    m = c.stamp_polyline([tuple(p) for p in pl])
    return ndimage.distance_transform_edt(~m)


def main():
    cls = np.load(os.path.join(WORK, 'classes_v85.npy'))
    h = np.load(os.path.join(WORK, 'height_1m.npy'))
    xs, ys = grid()
    D = {n: load_json('districts/%s_v85.json' % n) for n in
         ('beach', 'construction', 'downtown', 'elite', 'forest', 'hamlet', 'port', 'quiet_valley', 'rough', 'tramduro')}
    roads = load_json('roads_v85.json')['roads']
    water = load_json('water_v85.json')['bodies']
    F = load_json('features_v85.json')
    gy, gx = np.gradient(h)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    forest = np.asarray(Image.open(os.path.join(OUT, 'masks', 'veg_forest_v85.png')), np.float32)[::-1] / 255
    sea = cls == 1
    n1, n2 = noise(xs, ys, 23, 71), noise(xs, ys, 7, 72)
    w = np.zeros((len(LAYERS), H, W), np.float32)
    w[0] = 1.0
    w[3] = np.clip((forest - 0.35) * 2.2, 0, 1) * (0.75 + 0.25 * n2)
    # Rough dry grass: whole district, fading to the meadow over 40-80 m (ragged), plus the steppe beyond the border
    rg = poly_mask(next(z for z in D['rough']['zones'] if z['kind'] == 'ground')['poly'], xs, ys)
    d_rg = ndimage.distance_transform_edt(~rg)
    fade = 40.0 + 40.0 * n1
    dry = np.where(rg, 1.0, sm(1 - d_rg / fade) ** 1.3 * (0.8 + 0.2 * n2))
    dry = np.maximum(dry, sm((ys - 905) / 12.0) * (xs > 30) * (xs < 1110))              # W86: the whole steppe band beyond the border
    w[1] = np.clip(dry, 0, 1)
    # sand
    sand = ndimage.binary_closing(cls == 3, iterations=2)
    for z in D['beach']['zones']:
        if z['kind'] in ('sand', 'dunes') and z.get('poly'):
            sand |= poly_mask(z['poly'], xs, ys)
    w[4] = ndimage.gaussian_filter(sand.astype(np.float32), 1.2)
    wet = (ndimage.distance_transform_edt(~sea) < 7.0) & ~sea & (ndimage.distance_transform_edt(~sand) < 10)
    w[5] = ndimage.gaussian_filter(wet.astype(np.float32), 0.8)
    # roads: gravel shoulders on rural asphalt, dirt roads = ruts + grass centre, sand ruts on the beach
    shoulder = np.zeros((H, W), np.float32)
    dirt = np.zeros((H, W), np.float32)
    ruts = np.zeros((H, W), np.float32)
    for rd in roads:
        if rd['kind'] == 'tunnel' or rd['kind'] == 'bridge':
            continue
        d = line_dist(rd['points'])
        hw = rd['width_m'] / 2
        if rd['kind'] in ('rural_asphalt', 'serpentine', 'drive', 'district_ring'):
            shoulder = np.maximum(shoulder, sm(1 - np.abs(d - hw - 0.6) / 1.1))
        elif rd['kind'] == 'dirt':
            dirt = np.maximum(dirt, np.where(d < hw, np.where(d < 0.7, 0.45, 1.0), sm(1 - (d - hw) / 1.0)))
        elif rd['kind'] == 'sand_track':
            ruts = np.maximum(ruts, sm(1 - np.abs(d - 0.95) / 0.6))
    for n_, d_ in D.items():                                               # district dirt streets / tracks
        for z in d_['zones']:
            line = z.get('line') or z.get('poly_line') or z.get('polyline')
            if not line or len(line) < 2 or z.get('world_road'):
                continue
            if z['kind'] in ('street', 'track', 'road', 'footpath', 'path') and z.get('surface') in ('dirt_SK1b', 'gravel_SK1d', None) and n_ != 'downtown':
                wd = z.get('width_m') or 3.6
                if isinstance(wd, list):
                    wd = max(wd)
                d = line_dist(line)
                hw = float(wd) / 2
                mid = 0.45 if z['kind'] in ('street', 'road') else 0.8
                dirt = np.maximum(dirt, np.where(d < hw, np.where(d < 0.6, mid, 1.0), sm(1 - (d - hw) / 0.8)))
            elif z['kind'] == 'track' and z.get('surface') == 'sand_ruts':
                d = line_dist(line)
                ruts = np.maximum(ruts, sm(1 - np.abs(d - 0.95) / 0.6))
    w[6] = np.maximum(shoulder * 0.85, ndimage.gaussian_filter((ndimage.binary_dilation(cls == 5, iterations=6) & ~(cls == 5) & (h > 8)).astype(np.float32), 1.5) * 0.6)
    w[5] = np.maximum(w[5], ruts)
    if F.get('view_B_pocket'):                                               # W86: VIEW B viewpoint pocket = gravel turnaround
        w[6] = np.maximum(w[6], ndimage.gaussian_filter(poly_mask(F['view_B_pocket']['poly'], xs, ys).astype(np.float32), 0.8))
    # rock: crags, high bare ridge, steep faces
    mt = cls == 5
    rock = (mt & (h > 24)) | (cls == 6) | (slope > 36)
    rock_soft = ndimage.gaussian_filter(rock.astype(np.float32), 1.2)
    w[7] = np.clip(rock_soft * (0.7 + 0.3 * n2), 0, 1)
    # lawns
    lawn = np.zeros((H, W), bool)
    pz = next((z for z in D['elite']['zones'] if z['kind'] == 'plateau'), None)       # W86: lawn inside the village fence
    if pz:
        lawn |= poly_mask(pz['poly'], xs, ys)
    else:
        el = F['elite']
        lawn |= ((np.abs(xs - el['centre'][0]) / el['half'][0]) ** 4 + (np.abs(ys - el['centre'][1]) / el['half'][1]) ** 4) < 1
    for n_, kinds in (('downtown', ('veg_zone', 'park')), ('quiet_valley', ('lawn', 'grounds')), ('tramduro', ('lawn', 'golf')), ('beach', ('palm_park',))):
        for z in D[n_]['zones']:
            if z['kind'] in kinds and z.get('poly'):
                lawn |= poly_mask(z['poly'], xs, ys)
    w[8] = ndimage.gaussian_filter(lawn.astype(np.float32), 1.5)
    # Construction yard dirt, Hamlet yards / gardens / square dirt, fields
    yard = np.zeros((H, W), bool)
    yard |= poly_mask(next(z for z in D['construction']['zones'] if z['kind'] == 'ground')['poly'], xs, ys)
    for z in D['hamlet']['zones']:
        if z['kind'] in ('vegetable_garden', 'plaza', 'loading_pad', 'apron', 'pig_pen', 'overgrown_beds') and z.get('poly'):
            yard |= poly_mask(z['poly'], xs, ys)
    for z in D['rough']['zones']:
        if z['kind'] in ('trash_section',) and z.get('poly'):
            yard |= poly_mask(z['poly'], xs, ys)
    w[2] = np.maximum(ndimage.gaussian_filter(yard.astype(np.float32), 1.0) * (0.85 + 0.15 * n2), dirt)
    for z in D['hamlet']['zones']:
        if z['kind'] == 'field' and z.get('poly'):
            m = poly_mask(z['poly'], xs, ys)
            k = 10 if 'stubble' in str(z.get('surface', '')) else 9
            w[k] = np.maximum(w[k], ndimage.gaussian_filter(m.astype(np.float32), 0.7))
    # under water: sand on the sea floor, dirt on river / lake beds (clear water shows the bed)
    w[4] = np.maximum(w[4], ndimage.gaussian_filter(sea.astype(np.float32), 1.0))
    wm = np.zeros((H, W), bool)
    for b in water:
        if b.get('outline'):
            wm |= poly_mask(b['outline'], xs, ys)
    riv = next((b for b in water if b['kind'] == 'river'), None)              # W86: river / stream bed (clear water shows it) + gravel bars
    if riv:
        rb = np.zeros((H, W), bool)
        for (a, b_), wa in zip(zip(riv['axis'][:-1], riv['axis'][1:]), riv['width_m'][1:]):
            for p in resample([tuple(a), tuple(b_)], 1.0):
                r_ = int(wa / 2 + 1.5)
                ix_, iy_ = int(p[0]), int(p[1])
                rb[max(0, iy_ - r_):iy_ + r_ + 1, max(0, ix_ - r_):ix_ + r_ + 1] = True
        wm |= rb
        w[6] = np.maximum(w[6], ndimage.gaussian_filter((ndimage.binary_dilation(rb, iterations=2) & ~rb).astype(np.float32), 1.0) * 0.7)
    for b in water:                                                        # waterfall faces: rock
        if b.get('kind') == 'waterfall' and b.get('top') and b.get('bottom'):
            for q in (b['top'], b['bottom']):
                rock |= np.hypot(xs - q[0], ys - q[1]) < 7.0
    w[7] = np.maximum(w[7], ndimage.gaussian_filter(rock.astype(np.float32), 1.2) * 0.9)
    w[2] = np.maximum(w[2], ndimage.gaussian_filter(wm.astype(np.float32), 1.0))
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
        ch = [acc[4 * k + j] if 4 * k + j < len(LAYERS) else np.zeros((H, W), np.float32) for j in range(4)]
        img = (np.stack(ch, -1)[::-1] * 255 + 0.5).astype(np.uint8)
        Image.fromarray(img, 'RGBA').save(os.path.join(OUT, 'masks', 'splat_%d_v85.png' % k))
    t = load_json('terrain_v85.json')
    t['splat'] = {'files': ['masks/splat_%d_v85.png' % k for k in range(3)], 'layers': LAYERS,
                  'format': 'RGBA 8-bit, 1 px = 1 m (1744 x 950), row 0 = NORTH; layer i = file i//4, channel i%4'}
    save_json('terrain_v85.json', t)
    # quick colour preview
    pal = np.array([(0.43, 0.50, 0.30), (0.66, 0.60, 0.38), (0.55, 0.45, 0.33), (0.30, 0.36, 0.22), (0.97, 0.95, 0.88), (0.78, 0.74, 0.64),
                    (0.60, 0.59, 0.56), (0.50, 0.50, 0.48), (0.36, 0.55, 0.27), (0.45, 0.33, 0.22), (0.72, 0.64, 0.42)], np.float32)
    rgb = np.tensordot(np.moveaxis(acc, 0, -1), pal, axes=([2], [0]))
    rgb[sea] = (0.45, 0.68, 0.82)
    Image.fromarray((np.clip(rgb, 0, 1)[::-1] * 255).astype(np.uint8)).save(os.path.join(WORK, 'splat_preview_v85.png'))
    print({L: round(float(acc[i].mean()), 3) for i, L in enumerate(LAYERS)})


if __name__ == '__main__':
    main()
