"""Step 3: terrain heightmap of map v76 (handoff v01 §2.2–2.3, v02 §3–4).

Grid: 1 m (1744 x 950) built here, exported as Unity RAW 16-bit little-endian 2049 x 2049 (row 0 = south),
terrain size 1744 x HEIGHT_RANGE x 950 m at world Y = BASE_Y (x 0.851 m, z 0.464 m per sample).
Components (all from the map / generator, nothing invented beyond "soft uneven ground" asked in §2.3):
 sea floor + coast ramp, white sand beaches, NW ridge (map mountains + _h_diag small ridge 92 -> 56 m),
 right ridge 32 m (_h_r2), hill B 50 m (MOUNTS crest, hw 58) + "+8 m" knoll, Elite hill 44 m with a stone
 serpentine (one loop, +11/+22/+33/+44) and uneven plateau +40..+44, river gorge 6–13 m with two natural land bridges,
 mountain lake + waterfall, steppe rising to the horizon, flat district pads (Rough = Downtown height), micro relief,
 then road corridors profiled to <= 8 % where possible (report lists the rest).
"""
import json
import math
import os

import numpy as np
from scipy import ndimage

from common import OUT, REV, WORK, W, H, GROUND, grid, poly_mask, polyline_dist, load_json, save_json, resample

BASE_Y, HEIGHT_RANGE, RES = -15.0, 135.0, 2049
rng = np.random.default_rng(76)


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def fbm(xs, ys, scale, oct_=4, seed=0):
    """Value-noise fBm on the grid (deterministic)."""
    out = np.zeros(xs.shape, np.float32)
    amp, tot = 1.0, 0.0
    r_ = np.random.default_rng(seed)
    for o in range(oct_):
        s = scale / (2 ** o)
        gw, gh = int(W / s) + 3, int(H / s) + 3
        g = r_.random((gh, gw)).astype(np.float32)
        fx, fy = xs / s, ys / s
        x0, y0 = fx.astype(int), fy.astype(int)
        tx, ty = smoothstep(fx - x0), smoothstep(fy - y0)
        a = g[y0, x0] * (1 - tx) + g[y0, x0 + 1] * tx
        b = g[y0 + 1, x0] * (1 - tx) + g[y0 + 1, x0 + 1] * tx
        out += amp * (a * (1 - ty) + b * ty)
        tot += amp
        amp *= 0.5
    return out / tot * 2 - 1                                             # -1..1


def main():
    cls = np.load(os.path.join(WORK, 'classes_v76.npy'))
    xs, ys = grid()
    F = load_json('features_v76.json')
    roads = load_json('roads_v76.json')['roads']
    sea = cls == 1
    # legend box (bottom-right) and title (top-left) are drawn over the sea / steppe
    sea |= (xs > 1440) & (ys < 145)
    land = ~sea
    d_sea = ndimage.distance_transform_edt(land)                         # m to sea, on land
    d_land = ndimage.distance_transform_edt(sea)                         # m to land, in sea
    h = np.full((H, W), GROUND, np.float32)
    # --- coast: land ramps up from +0.6 m at the shore to ground over 30 m; sea floor down to -12 m
    h = np.where(land, 0.6 + (GROUND - 0.6) * smoothstep(d_sea / 30.0), -np.minimum(0.4 + d_land * 0.16, 12.0))
    sand = ndimage.binary_closing(cls == 3, iterations=2)
    near_sand = ndimage.distance_transform_edt(~sand)
    h = np.where(land & (near_sand < 25), np.minimum(h, 0.6 + 1.6 * smoothstep(d_sea / 70.0) + 0.1 * near_sand), h)
    beach_sea = sea & (ndimage.distance_transform_edt(~sand) < 40)
    h = np.where(beach_sea, np.maximum(h, -0.3 - d_land * 0.09), h)      # ~8 m shallow band at beaches
    # --- micro relief and hillocks everywhere (soft), damped later on pads / roads
    micro = 0.9 * fbm(xs, ys, 22, 3, 1) + 2.6 * np.clip(fbm(xs, ys, 90, 2, 2), 0, 1) ** 1.3 * 2.2
    folds = 1.2 * fbm(xs, ys, 45, 3, 3)
    h = np.where(land, h + (micro + folds) * smoothstep(d_sea / 40.0), h)
    # --- NW mountains (map faceted greys) + small ridge (_h_diag) + right ridge (_h_r2)
    mt = ndimage.binary_opening(ndimage.binary_closing(cls == 5, iterations=4), iterations=2)
    lab, n = ndimage.label(mt)
    sizes = ndimage.sum(mt, lab, range(1, n + 1))
    mt = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 4000])
    d_in = ndimage.distance_transform_edt(mt)
    top = 92.0 - 36.0 * smoothstep((xs - 470.0) / 102.0)
    ridged = 1 - np.abs(fbm(xs, ys, 60, 3, 5))
    mtn = top * (1 - np.exp(-d_in / 38.0)) * (0.78 + 0.22 * ridged) + 5.0 * fbm(xs, ys, 14, 3, 6) * np.minimum(1, d_in / 12)
    d = polyline_dist(F['small_ridge']['crest'], xs, ys, 80)
    h_diag = (92.0 - 36.0 * smoothstep((xs - 470.0) / 102.0)) * np.clip(1 - d / 44.0, 0, 1) ** 1.12 * (0.8 + 0.2 * ridged)
    d = polyline_dist(F['right_ridge']['crest'], xs, ys, 60)
    h_r2 = 32.0 * np.clip(1 - d / 24.0, 0, 1) ** 1.1
    mtv = np.maximum(mtn, np.maximum(h_diag, h_r2))
    # v02 fix: lift only where a mountain / ridge term exists (v01 lifted ALL land to >= GROUND, which flattened the
    # 0.6 -> 5 m coast ramp and the beach slope into a ~5 m cliff along every shore)
    k = np.clip(mtv / 2.0, 0, 1)                                       # full v01 lift once the ridge adds >= 2 m, fades out below
    h = np.where(land | mt, h + (np.maximum(h, GROUND + mtv) - h) * k, h)
    # --- grey sharp rocks (Quiet Valley, cornice cliffs, Tramduro shore): 6–14 m crags, impassable
    rock = ndimage.binary_opening(ndimage.binary_closing(cls == 6, iterations=2), iterations=2) & ~mt
    lab, n = ndimage.label(rock)
    rock = np.isin(lab, [i + 1 for i, s_ in enumerate(ndimage.sum(rock, lab, range(1, n + 1))) if s_ > 250])   # crags, not tree outlines
    tram_base = None
    if REV != 'v01' and os.path.exists(os.path.join(OUT, 'districts', 'tramduro_v76.json')):
        # v02: Tramduro's grey concrete military yard and the lawn are not crags (v01 turned the whole south half into rock);
        # the sharp rocks stay along the shore only (handoff v02 §8.10: "острые скалы 5–10 м по берегам")
        tz = load_json('districts/tramduro_v76.json')['zones']
        inner = np.zeros((H, W), bool)
        for z in tz:
            if z.get('kind') in ('continuous_concrete_base', 'coastal_presidential_lawn') and len(z.get('poly') or []) >= 3:
                inner |= poly_mask(z['poly'], xs, ys)
                if z['kind'] == 'continuous_concrete_base':
                    tram_base = [tuple(q) for q in z['poly']]
        rock &= ~ndimage.binary_erosion(inner, iterations=2)
    d_rock = ndimage.distance_transform_edt(rock)
    h = np.where(rock, np.maximum(h, GROUND + 4 + np.minimum(d_rock * 1.6, 10) + 2 * fbm(xs, ys, 8, 2, 7)), h)
    # --- hill B 50 m (crest hw 58, outer contour ~ +40 m) and the +8 m knoll
    d = polyline_dist(F['hill_B']['crest'], xs, ys, 140)
    hillB = 41.0 * smoothstep(1 - d / 110.0) ** 1.15 + 4.0 * smoothstep(1 - d / 40.0)          # GROUND + 45 = 50 m peak
    # v02 fix: v01 shape where the hill adds >= 2 m, faded out below (v01: max(h, GROUND + 0) lifted all land to 5 m)
    hb = GROUND + hillB * (1 + 0.025 * fbm(xs, ys, 30, 2, 8))
    k = np.clip(hillB / 2.0, 0, 1)
    h = np.where(land, h + (np.maximum(h, hb) - h) * k, h)
    cx, cy = F['chill_knoll']['centre']
    h += 8.0 * smoothstep(1 - np.hypot(xs - cx, ys - cy) / 34.0) ** 1.4
    # --- Elite hill 44 m: superellipse plateau +40..+44, slopes to ground / sea
    ex, ey = F['elite']['centre']
    ea, eb = F['elite']['half']
    rho = ((np.abs(xs - ex) / ea) ** 4 + (np.abs(ys - ey) / eb) ** 4) ** 0.25
    plateau = 40.0 + 4.0 * (0.5 + 0.5 * fbm(xs, ys, 26, 2, 9))
    lift = 39.0 * smoothstep(1 - (rho - 1.0) / 0.75)
    cone = GROUND + lift
    elite = np.where(rho <= 1.0, plateau, cone)
    # v02 fix: v01 shape where the cone adds >= 2 m, faded out below (v01: GROUND floor = 5 m wall at the City / Elite beach)
    k = np.where(rho <= 1.0, 1.0, np.clip(lift / 2.0, 0, 1))
    h = np.where(rho < 1.9, np.where(land, h + (np.maximum(h, elite) - h) * k, np.minimum(np.maximum(h, elite), h + 0.0)), h)
    # --- district pads (flat; Rough = Downtown height, Rough ground Y = 0 relative to the pad)
    pads = {'downtown': ([(790, 228), (1268, 228), (1268, 470), (790, 470)], GROUND),
            'rough': ([(655, 668), (1006, 668), (1006, 905), (655, 905)], GROUND),
            'construction': ([(528, 352), (700, 352), (700, 492), (528, 492)], None),
            'port': ([(1172, 596), (1356, 596), (1356, 684), (1172, 684)], 2.5),
            'quiet_valley_lab': ([(560, 225), (620, 225), (620, 265), (560, 265)], None)}
    if tram_base:
        pads['tramduro_base'] = (tram_base, None)                       # v02: flat concrete yard (hangar, vehicles, helipad)
    padw = np.zeros((H, W), np.float32)
    for name, (poly, hh) in pads.items():
        m = poly_mask(poly, xs, ys)
        hp = float(np.median(h[m])) if hh is None else hh
        w = smoothstep(1 - ndimage.distance_transform_edt(~m) / 22.0)
        h = h * (1 - w) + hp * w
        padw = np.maximum(padw, w)
        pads[name] = (poly, hp)
    # Elite plateau keeps its +40..44 unevenness (no pad)
    # --- rivers / lakes / swamp
    water = load_json('water_v76.json')['bodies']
    river = np.zeros((H, W), bool)
    lakes = []
    not_water = np.zeros((H, W), bool)                                       # v02: bodies dropped by s02b (legend, labels, roofs)
    for b in water:
        if 'outline' not in b:
            continue
        m = poly_mask(b['outline'], xs, ys)
        if b['kind'] == 'dropped':
            not_water |= ndimage.binary_dilation(m, iterations=3)
        elif b['kind'] == 'river':
            river |= m
        else:
            lakes.append((b, m))
    wc = (cls == 2) & ~not_water
    lab_w, n_w = ndimage.label(wc, structure=np.ones((3, 3)))
    big_w = np.isin(lab_w, [i + 1 for i, s_ in enumerate(ndimage.sum(wc, lab_w, range(1, n_w + 1))) if s_ >= 120])   # v02: no label letters
    river |= ndimage.binary_closing(big_w, iterations=2) & ~not_water & (xs > 440) & (xs < 690) & (ys > 80) & (ys < 760) & (padw < 0.5)
    bridge = np.zeros((H, W), bool)
    for lb in F['land_bridges']:
        bridge |= ((xs - lb['centre'][0]) / lb['rx_m']) ** 2 + ((ys - lb['centre'][1]) / lb['ry_m']) ** 2 < 1
    d_riv = ndimage.distance_transform_edt(~river)
    # river never at ground level: bed falls from the lake (~+16 m) to the sea waterfall (+1.5 m), banks rise to bed + 6..13 m
    bed_line = 1.5 + 2.5 * smoothstep((ys - 96.0) / 200.0) + 11.0 * smoothstep((ys - 560.0) / 180.0)
    depth = np.clip(6.0 + 7.0 * smoothstep((ys - 300) / 400.0), 6, 13)
    bank = bed_line + depth
    near = smoothstep(1 - (d_riv - 12.0) / 95.0) ** 0.7                     # wide valley shoulders, not levees
    h = np.where(land & ~mt, np.maximum(h, h * (1 - near) + bank * near), h)
    chan = smoothstep(1 - (d_riv - 2.0) / 7.0)
    h = np.where(bridge, np.maximum(h, bank), h * (1 - chan) + bed_line * chan)
    river_surface = bed_line + 1.2
    for b, m in lakes:
        dl = ndimage.distance_transform_edt(~m)
        surf = float(np.median(h[m]))
        if b.get('name') == 'mountain_lake':
            surf = max(surf, GROUND + 14.0)
        b['surface_m'] = round(surf - 0.3, 2)
        h = np.where(dl < 10, np.minimum(h, surf - b['depth_m'] * smoothstep(1 - dl / 10.0) + 0.6 * smoothstep(dl / 10.0)), h)
    # --- v02: piers and jetties are decks over the water (the builder lays the boards), not earth causeways drawn as land
    if os.path.exists(os.path.join(OUT, 'districts', 'beach_v76.json')):
        near_sea = ndimage.binary_dilation(sea, iterations=10) & ~(cls == 3)
        for dn in ('beach', 'elite'):
            for z in load_json('districts/%s_v76.json' % dn).get('zones', []):
                if z.get('kind') == 'pier' and len(z.get('poly') or []) >= 3:
                    m = ndimage.binary_dilation(poly_mask(z['poly'], xs, ys), iterations=1) & near_sea
                    h = np.where(m, np.minimum(h, -1.5), h)
    # --- steppe beyond the fence rises softly to the horizon
    steppe = ys > np.interp(xs, [0, 540, 1060, 1744], [905, 912, 912, 905])
    h = np.where(steppe & land, np.maximum(h, GROUND + 18.0 * smoothstep((ys - 912) / 38.0)), h)
    # --- roads: profile each centreline (smoothed terrain, grade limit) and imprint corridor
    rough_h = h.copy()
    sm = ndimage.gaussian_filter(h, 6)
    road_h = np.full((H, W), np.nan, np.float32)
    road_w = np.zeros((H, W), np.float32)
    report = []
    for rd in roads:
        if rd['kind'] == 'tunnel':
            continue
        pts = resample([tuple(p) for p in rd['points']], 2.0)
        ix = np.clip([int(p[0]) for p in pts], 0, W - 1)
        iy = np.clip([int(p[1]) for p in pts], 0, H - 1)
        prof = sm[iy, ix].astype(np.float64)
        if rd['kind'] == 'stone_serpentine':                       # +0 at the bottom -> +44 at gate 06, uniform
            L = np.concatenate([[0], np.cumsum(np.hypot(np.diff([p[0] for p in pts]), np.diff([p[1] for p in pts])))])
            prof = GROUND + 39.0 * np.clip((L - 30) / (L[-1] - 40), 0, 1)
        else:
            prof = ndimage.uniform_filter1d(prof, 41, mode='nearest')
            prof = np.maximum(prof, 0.8)
            seg0 = np.hypot(np.diff([p[0] for p in pts]), np.diff([p[1] for p in pts]))
            g = 0.08 if rd['kind'] != 'serpentine' or rd.get('variant') else 0.12   # VIEW B serpentine: 12 % kept (Fedya 18.10, Q7); s02c hairpin variant: 8 %
            if rd['id'] == 'border_checkpoint_road' and REV != 'v01':
                g = 1.0          # v02: beyond the KPP the road just follows the steppe rise (v01 cut a 15 m trench into it)
            for _ in range(3):                                         # grade limit: cut on the way up, fill on the way down
                for i in range(1, len(prof)):
                    prof[i] = np.clip(prof[i], prof[i - 1] - g * seg0[i - 1], prof[i - 1] + g * seg0[i - 1])
                for i in range(len(prof) - 2, -1, -1):
                    prof[i] = np.clip(prof[i], prof[i + 1] - g * seg0[i], prof[i + 1] + g * seg0[i])
        seg = np.hypot(np.diff([p[0] for p in pts]), np.diff([p[1] for p in pts]))
        grade = np.abs(np.diff(prof)) / np.maximum(seg, 1e-3)
        report.append({'id': rd['id'], 'max_grade_pct': round(float(np.percentile(grade, 98)) * 100, 1), 'length_m': round(float(seg.sum()), 1)})
        rd['heights'] = [round(float(v), 2) for v in prof[::2]]
        hw = rd['width_m'] / 2
        for p, z in zip(pts, prof):
            x0, x1 = int(max(0, p[0] - hw - 8)), int(min(W, p[0] + hw + 9))
            y0, y1 = int(max(0, p[1] - hw - 8)), int(min(H, p[1] + hw + 9))
            dd = np.hypot(xs[y0:y1, x0:x1] - p[0], ys[y0:y1, x0:x1] - p[1])
            wgt = smoothstep(1 - (dd - hw - 0.5) / 7.0)
            cur = road_w[y0:y1, x0:x1]
            upd = wgt > cur
            road_h[y0:y1, x0:x1] = np.where(upd, z, road_h[y0:y1, x0:x1])
            road_w[y0:y1, x0:x1] = np.where(upd, wgt, cur)
    h = np.where(np.isnan(road_h), h, h * (1 - road_w) + np.nan_to_num(road_h) * road_w)
    # --- tunnel: bed between portal ground heights, holes at portals (Unity terrain holes)
    tun = [tuple(p) for p in F['tunnel_axis']]
    za = float(h[int(tun[0][1]), int(tun[0][0])])
    zb = float(h[int(tun[-1][1]), int(tun[-1][0])])
    d = polyline_dist(tun, xs, ys, 30)
    holes = np.zeros((H, W), bool)
    for p, z in ((tun[0], za), (tun[-1], zb)):
        near = np.hypot(xs - p[0], ys - p[1]) < 14
        holes |= near & (d < 4.0) & (h > z + 1.5)
    tunnel = {'axis': [list(p) for p in tun], 'portal_heights_m': [round(za, 2), round(zb, 2)], 'clear_height_m': 5.5, 'width_m': 9.0,
              'min_cover_m': round(float(np.min([h[int(p[1]), int(p[0])] - (za + (zb - za) * i / (len(tun) - 1)) for i, p in enumerate(tun)][1:-1])), 1),
              'exit_glare': {'kind': 'post exposure flash + 1.5 s adaptation', 'strongest': 'Rough -> Downtown (south portal)'}}
    # --- export
    os.makedirs(OUT, exist_ok=True)
    np.save(os.path.join(WORK, 'height_1m.npy'), h)
    zz = np.clip((h - BASE_Y) / HEIGHT_RANGE, 0, 1)
    from scipy.ndimage import map_coordinates
    gx = np.linspace(0, W - 1, RES)
    gy = np.linspace(0, H - 1, RES)
    GX, GY = np.meshgrid(gx, gy)
    hr = map_coordinates(zz, [GY, GX], order=1)
    (hr * 65535).round().astype('<u2').tofile(os.path.join(OUT, 'Heightmap_v76_2049_r16.bytes'))
    hm = map_coordinates(holes.astype(np.float32), [np.linspace(0, H - 1, RES - 1)[:, None] * np.ones((1, RES - 1)), np.ones((RES - 1, 1)) * np.linspace(0, W - 1, RES - 1)[None, :]], order=0)
    np.packbits((hm < 0.5).astype(np.uint8)).tofile(os.path.join(OUT, 'Holes_v76_2048_bits.bytes'))
    from PIL import Image
    Image.fromarray((np.clip((h - BASE_Y) / HEIGHT_RANGE, 0, 1)[::-1] * 255).astype(np.uint8)).save(os.path.join(WORK, 'heightmap_preview_v76.png'))
    save_json('terrain_v76.json', {
        'heightmap': 'Heightmap_v76_2049_r16.bytes', 'format': 'RAW 16-bit little-endian, %d x %d, row 0 = south (world y 0), column 0 = west' % (RES, RES),
        'holes': 'Holes_v76_2048_bits.bytes (packbits, 1 = solid, 2048 x 2048, row 0 = south)',
        'size_m': [W, HEIGHT_RANGE, H], 'position_m': [0, BASE_Y, 0], 'sample_spacing_m': [round(W / (RES - 1), 3), round(H / (RES - 1), 3)],
        'sea_level_m': 0.0, 'ground_m': GROUND, 'pads': {k: {'poly': v[0], 'height_m': round(v[1], 2)} for k, v in pads.items()},
        'tunnel': tunnel, 'road_grades': report, 'lakes': [{'id': b['id'], 'name': b.get('name'), 'surface_m': b.get('surface_m')} for b, _ in lakes],
        'river': {'bed_m': [1.5, 15.0], 'gorge_depth_m': [6, 13], 'surface_above_bed_m': 1.2},
        'peaks_m': {'hill_B': round(float(h[(ys > 540) & (ys < 640) & (xs > 750) & (xs < 1150)].max()), 1),
                    'elite': round(float(h[rho < 1].max()), 1), 'nw_ridge': round(float(h[xs < 560].max()), 1)}})
    save_json('roads_v76.json', {**load_json('roads_v76.json'), 'roads': roads})
    print(json.dumps(load_json('terrain_v76.json')['peaks_m']), 'tunnel', tunnel['portal_heights_m'], tunnel['min_cover_m'])
    for r_ in report:
        if r_['max_grade_pct'] > 8:
            print('  steep', r_)


if __name__ == '__main__':
    main()
