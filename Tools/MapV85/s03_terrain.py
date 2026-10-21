"""Step 3 (v85): terrain heightmap — "harmoniously uneven" relief (handoff v10 §3).

Grid 1 m (1744 x 950), exported as Unity RAW 16-bit LE 2049 x 2049 (row 0 = south), terrain 1744 x HEIGHT_RANGE x 950 m at Y = BASE_Y.
Composition (every hill / ravine has a role, listed in terrain_v85.json "relief"):
 - big relief from the map / generator: NW ridge 92-96 -> 46/56 m (cls mountains + _h_ext/_h_ext2/_h_diag of build_world_v85),
   right ridge ~32 m, hill B 50 m (west summit over the tunnel) with a natural PASS where the VIEW B serpentine crosses
   (v10 §3.2: low 1-1.5 m berm, open view, no 15 m cut), Elite hill 44 m with the uneven plateau (+40 S .. +44 N, villa terraces),
   river gorge 6-13 m (v76 model: raised shoulders, two natural land bridges), Construction hill +8 m (site pad, rings 13 / 26 m);
 - designed medium relief 3-8 (12) m: separating hills, a viewpoint hill, forest swells, soft gullies 2-4 m to the river / bay;
 - micro relief 0.3-1.5 m (no bumps on a grid);
 - calm pads: Downtown = Rough = 5.0 m, port 2.5 m, Tramduro yard, Quiet Valley lab yard, Hamlet house plots + fields flat,
   pad edges blended over 40 m (no "cake" wall);
 - roads profiled <= 8 % (VIEW B serpentine 12 %, Elite stone road = district heights) with gentle side slopes
   (serpentine <= 30 %: the pass), bridges / tunnel not imprinted;
 - no van traps: closed depressions on land deeper than 0.6 m are filled (priority flood), except water bodies.
"""
import heapq
import json
import math
import os

import numpy as np
from scipy import ndimage

import common as c
from common import OUT, WORK, W, H, GROUND, grid, poly_mask, polyline_dist, load_json, save_json, resample, post

BASE_Y, HEIGHT_RANGE, RES = -15.0, 135.0, 2049


def sm(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def fbm(xs, ys, scale, oct_=4, seed=0):
    out = np.zeros(xs.shape, np.float32)
    amp, tot = 1.0, 0.0
    r_ = np.random.default_rng(seed)
    for o in range(oct_):
        s = scale / (2 ** o)
        gw, gh = int(W / s) + 3, int(H / s) + 3
        g = r_.random((gh, gw)).astype(np.float32)
        fx, fy = xs / s, ys / s
        x0, y0 = fx.astype(int), fy.astype(int)
        tx, ty = sm(fx - x0), sm(fy - y0)
        a = g[y0, x0] * (1 - tx) + g[y0, x0 + 1] * tx
        b = g[y0 + 1, x0] * (1 - tx) + g[y0 + 1, x0 + 1] * tx
        out += amp * (a * (1 - ty) + b * ty)
        tot += amp
        amp *= 0.5
    return out / tot * 2 - 1


def dist_pl(pl, xs, ys, cap):
    return polyline_dist([tuple(p) for p in pl], xs, ys, cap)


# designed medium relief (world v85 metres): kind, crest polyline, half-width, height (+ hill / - gully), role
RELIEF = [
    ('hill', [(552, 522), (596, 534), (640, 546)], 34, 7.0, 'разделяет Стройку и Неблагополучный, закрывает вид на Неблагополучный с главной дороги; объезд по лугу'),
    ('hill', [(706, 418), (738, 438), (770, 452)], 30, 9.0, 'закрывает западный фасад Даунтауна от Стройки; смотровая точка на город'),
    ('hill', [(712, 262), (744, 274), (776, 280)], 26, 5.0, 'отделяет скалы Тихой долины от юго-западного угла Даунтауна, ломает прямой вид с пляжа на главную дорогу'),
    ('hill', [(456, 196), (484, 210), (510, 226)], 28, 6.0, 'отделяет лес от Тихой долины; грунтовка огибает его'),
    ('hill', [(575, 612), (598, 626)], 16, 3.5, 'бугор на лугу перед Неблагополучным (вопрос 9: да)'),
    ('hill', [(690, 590), (704, 604)], 14, 3.0, 'бугор у подножия холма B, разнообразит луг'),
    ('hill', [(536, 640), (552, 652)], 14, 2.5, 'бугор у дороги Хутор - Неблагополучный'),
    ('hill', [(232, 248), (262, 262)], 30, 4.5, 'пологий подъём в лесу'),
    ('hill', [(338, 112), (372, 126)], 26, 3.5, 'пологий подъём в лесу'),
    ('hill', [(1130, 520), (1170, 506)], 26, 6.0, 'восточный отрог холма B над Северной бухтой: вид на порт'),
    ('gully', [(580, 556), (548, 560), (512, 564)], 9, -3.0, 'промоина к реке: бездорожье интереснее, сток'),
    ('gully', [(1166, 552), (1196, 528), (1222, 506)], 8, -3.5, 'промоина с холма B к Северной бухте'),
    ('gully', [(700, 500), (680, 516), (656, 528)], 8, -2.5, 'ложбина между холмом Стройки и холмом B'),
]


def main():
    cls = np.load(os.path.join(WORK, 'classes_v85.npy'))
    xs, ys = grid()
    F = load_json('features_v85.json')
    roads = load_json('roads_v85.json')['roads']
    water = load_json('water_v85.json')['bodies']
    Dd = {n: load_json('districts/%s_v85.json' % n) for n in
          ('beach', 'construction', 'downtown', 'elite', 'forest', 'hamlet', 'port', 'quiet_valley', 'rough', 'tramduro')}
    sea = (cls == 1) | ((xs > 1440) & (ys < 145))                       # legend box drawn over the sea
    land = ~sea
    d_sea = ndimage.distance_transform_edt(land)
    d_land = ndimage.distance_transform_edt(sea)
    # ---- coast + sea floor
    h = np.where(land, 0.6 + (GROUND - 0.6) * sm(d_sea / 30.0), -np.minimum(0.4 + d_land * 0.16, 12.0)).astype(np.float32)
    sand = ndimage.binary_closing(cls == 3, iterations=2)
    near_sand = ndimage.distance_transform_edt(~sand)
    h = np.where(land & (near_sand < 25), np.minimum(h, 0.6 + 1.6 * sm(d_sea / 70.0) + 0.1 * near_sand), h)
    beach_sea = sea & (ndimage.distance_transform_edt(~sand) < 40)
    h = np.where(beach_sea, np.maximum(h, -0.3 - d_land * 0.09), h)
    coastfade = sm(d_sea / 40.0)
    # ---- micro relief 0.3-1.5 m (two scales, no grid pattern) + very soft swells
    micro = 0.55 * fbm(xs, ys, 9, 2, 11) + 0.75 * fbm(xs, ys, 23, 3, 12)
    swell = 1.6 * fbm(xs, ys, 120, 2, 13)
    h = np.where(land, h + (micro + swell) * coastfade, h)
    # ---- designed medium relief
    relief_log = []
    for kind, crest, hw, hh, role in RELIEF:
        d = dist_pl(crest, xs, ys, hw * 1.6)
        along = 1.0 + 0.15 * fbm(xs, ys, 40, 2, int(abs(hh) * 10) + len(crest))
        prof = sm(1 - d / hw) ** (1.25 if hh > 0 else 0.8)
        h = np.where(land, h + hh * prof * along * coastfade, h)
        relief_log.append({'kind': kind, 'crest': [list(p) for p in crest], 'half_width_m': hw, 'height_m': hh, 'role_ru': role})
    # ---- NW ridge (map mountains + generator crest functions) and the right ridge
    mt = ndimage.binary_opening(ndimage.binary_closing(cls == 5, iterations=4), iterations=2)
    lab, n = ndimage.label(mt)
    sizes = ndimage.sum(mt, lab, range(1, n + 1))
    mt = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 4000])
    d_in = ndimage.distance_transform_edt(mt)
    ridged = 1 - np.abs(fbm(xs, ys, 60, 3, 5))
    top = 92.0 - 36.0 * sm((xs - 470.0) / 102.0)
    mtn = top * (1 - np.exp(-d_in / 38.0)) * (0.78 + 0.22 * ridged) + 5.0 * fbm(xs, ys, 14, 3, 6) * np.minimum(1, d_in / 12)
    sr = F['small_ridge']
    d = dist_pl(sr['crest'], xs, ys, 80)
    h_diag = (92.0 - 36.0 * sm((xs - 470.0) / 102.0)) * np.clip(1 - d / 44.0, 0, 1) ** 1.12 * (0.8 + 0.2 * ridged)
    ex_ = F['ridge_ext']
    d = dist_pl(ex_['crest'], xs, ys, 90)
    hw_e = np.where(ys > 862, 40.0, 70.0)
    east = np.clip((643.0 - xs) / 16.0, 0, 1) ** 0.6
    h_ext = (92.0 - 46.0 * np.clip((xs - 520) / 115.0, 0, 1)) * np.clip(1 - d / hw_e, 0, 1) ** 1.15 * east
    d = dist_pl(F['ridge_north']['crest'], xs, ys, 80)
    h_ext2 = 89.0 * np.clip(1 - d / 62.0, 0, 1) ** 1.1
    d = dist_pl(F['right_ridge']['crest'], xs, ys, 60)
    h_r2 = 26.0 * np.clip(1 - d / 24.0, 0, 1) ** 1.1
    mtv = np.maximum.reduce([mtn, h_diag, h_ext, h_ext2, h_r2]) + 3.0 * fbm(xs, ys, 11, 2, 21) * np.clip(np.maximum.reduce([h_diag, h_ext, h_ext2]) / 12.0, 0, 1)
    mtv = np.minimum(mtv, 90.0)
    k = np.clip(mtv / 2.0, 0, 1)
    h = np.where(land | mt, h + (np.maximum(h, GROUND + mtv) - h) * k, h)
    # ---- grey crags (Quiet Valley rocks between the valley and the beach, cornice cliffs, coast rocks), impassable
    rock = ndimage.binary_opening(ndimage.binary_closing(cls == 6, iterations=2), iterations=2) & ~mt
    lab, n = ndimage.label(rock)
    rock = np.isin(lab, [i + 1 for i, s_ in enumerate(ndimage.sum(rock, lab, range(1, n + 1))) if s_ > 250])
    tz = [z for z in Dd['tramduro']['zones'] if z['kind'] in ('yard', 'lawn', 'palace_lawn', 'golf') and len(z.get('poly') or []) >= 3]
    for z in tz:
        rock &= ~poly_mask(z['poly'], xs, ys)
    qvr = poly_mask(F['quiet_valley_rocks'], xs, ys)
    rock |= qvr & land
    d_rock = ndimage.distance_transform_edt(rock)
    h = np.where(rock, np.maximum(h, GROUND + 4 + np.minimum(d_rock * 1.6, 10) + 2 * fbm(xs, ys, 8, 2, 7)), h)
    # ---- hill B 50 m (west summit over the tunnel) with the VIEW B pass
    hb = F['hill_B']
    d = dist_pl(hb['crest'], xs, ys, 140)
    hillB = 41.0 * sm(1 - d / 110.0) ** 1.15 + 4.0 * sm(1 - d / 40.0)
    serp = next(r for r in roads if r['id'] == 'serpentine_view_b')
    d_s = dist_pl(serp['points'], xs, ys, 160)
    vb = F['view_B']
    pass_k = np.exp(-(d_s / 55.0) ** 2) * sm(1 - np.hypot(xs - vb[0], ys - vb[1]) / 170.0)   # the pass: hill lowered around the serpentine
    hillB = hillB * (1 - 0.62 * pass_k)
    hbv = GROUND + hillB * (1 + 0.03 * fbm(xs, ys, 30, 2, 8))
    k = np.clip(hillB / 2.0, 0, 1)
    h = np.where(land, h + (np.maximum(h, hbv) - h) * k, h)
    # ---- Elite hill: plateau plane (+40 S .. +44 N) inside the fence, slopes outside
    el = F['elite']
    ex, ey = el['centre']
    ea, eb = el['half']
    rho = ((np.abs(xs - ex) / ea) ** 4 + (np.abs(ys - ey) / eb) ** 4) ** 0.25
    pz = next(z for z in Dd['elite']['zones'] if z['kind'] == 'plateau')['height_field']
    a_ = pz['abs_m']
    u, v = (xs - pz['centre'][0]) / pz['half_size_m'][0], (ys - pz['centre'][1]) / pz['half_size_m'][1]
    plateau = a_['C'] + u * (a_['E'] - a_['W']) / 2 + v * (a_['N'] - a_['S']) / 2 + 0.6 * fbm(xs, ys, 18, 2, 9)
    lift = (plateau - GROUND - 1.0) * sm(1 - (rho - 1.0) / 0.75)
    elite = np.where(rho <= 1.0, plateau, GROUND + lift)
    k = np.where(rho <= 1.0, 1.0, np.clip(lift / 2.0, 0, 1))
    h = np.where(rho < 1.9, np.where(land, h + (np.maximum(h, elite) - h) * k, h), h)
    for z in Dd['elite']['zones']:                                      # villa terraces: flat at their absolute height
        if z['kind'] == 'villa_plot' and z.get('terrace_abs_m') is not None:
            m = poly_mask(z['poly'], xs, ys)
            w_ = sm(1 - ndimage.distance_transform_edt(~m) / 6.0)
            h = h * (1 - w_) + z['terrace_abs_m'] * w_
    # ---- Construction hill +8 m: site pad, rings 13 / 26 m, ramp from the gate (road at the foot)
    ch = F['construction_hill']
    site = poly_mask(ch['site'], xs, ys)
    d_out = ndimage.distance_transform_edt(~site)
    base_c = float(np.median(h[site]))
    pad_c = base_c + ch['rel_m']
    gx, gy = ch['gate']
    d_gate = np.hypot(xs - gx, ys - gy)
    ramp = sm((d_gate - 6.0) / 70.0)                                        # yard rises from the gate (+~3 m) to the pad over ~70 m
    site_h = pad_c - (ch['rel_m'] - 3.0) * (1 - ramp)
    hill = np.where(site, site_h, site_h - (site_h - h) * sm(d_out / 26.0))
    k = np.where(site, 1.0, sm(1 - d_out / 26.0))
    h = np.where(land, h * (1 - k) + np.maximum(hill, h) * k, h)
    # ---- district pads (flat), edges blended over 40 m
    pads = {}

    def pad(name, poly, hh, blend=40.0, inner=0.0):
        nonlocal h
        m = poly_mask(poly, xs, ys)
        if inner > 0:
            m = ndimage.binary_dilation(m, iterations=int(inner))
        hp = float(np.median(h[m])) if hh is None else hh
        w_ = sm(1 - ndimage.distance_transform_edt(~m) / blend)
        h = h * (1 - w_) + hp * w_
        pads[name] = {'poly': [list(map(float, p)) for p in poly], 'height_m': round(hp, 2)}
        return m

    for z in Dd['downtown']['zones']:
        if z['kind'] == 'ground':
            pad('downtown' if z['id'] == '05-ground' else 'downtown_' + z['id'][-3:], z['poly'], 5.0, 40.0, 3)
    rg = next(z for z in Dd['rough']['zones'] if z['kind'] == 'ground')
    pad('rough', rg['poly'], 5.0, 40.0, 3)
    py_ = next(z for z in Dd['port']['zones'] if z['id'] == '06-yard')
    pad('port', py_['poly'], 2.5, 30.0, 2)
    ty = next((z for z in Dd['tramduro']['zones'] if z['id'] == '10-concrete_yard'), None)
    if ty:
        pad('tramduro_yard', ty['poly'], None, 18.0, 1)
    lab_b = next(b for b in Dd['quiet_valley']['buildings'] if b.get('base') == '5' or 'lab' in b['kind'])
    lb = np.array(lab_b['footprint'])
    pad('quiet_valley_lab', [[lb[:, 0].min() - 22, lb[:, 1].min() - 22], [lb[:, 0].max() + 22, lb[:, 1].min() - 22],
                             [lb[:, 0].max() + 22, lb[:, 1].max() + 22], [lb[:, 0].min() - 22, lb[:, 1].max() + 22]], None, 25.0)
    # Hamlet: house plots and outbuildings flat (+3 m), fields flat, square flat — the village keeps the natural ground between
    for b in Dd['hamlet']['buildings']:
        m = ndimage.binary_dilation(poly_mask(b['footprint'], xs, ys), iterations=3)
        if m.sum() == 0:
            continue
        hp = float(np.median(h[m]))
        w_ = sm(1 - ndimage.distance_transform_edt(~m) / 8.0)
        h = h * (1 - w_) + hp * w_
    # grandpa's yard (base 2): the play-scene integrator (G43) puts the open operating shed and the paint table next to the hut
    base2 = [(238.0, 502.0), (253.0, 502.0), (253.0, 528.0), (238.0, 528.0)]
    m = poly_mask(base2, xs, ys)
    hp = float(np.median(h[m]))
    w_ = sm(1 - ndimage.distance_transform_edt(~m) / 10.0)
    h = h * (1 - w_) + hp * w_
    for z in Dd['hamlet']['zones']:
        if z['kind'] in ('field', 'plaza', 'loading_pad', 'apron', 'cemetery') and len(z.get('poly') or []) >= 3:
            m = poly_mask(z['poly'], xs, ys)
            if m.sum() == 0:
                continue
            hp = float(np.median(h[m]))
            w_ = sm(1 - ndimage.distance_transform_edt(~m) / 10.0)
            h = h * (1 - w_) + hp * w_
    for dn in ('forest', 'quiet_valley', 'beach', 'port', 'tramduro'):
        for b in Dd[dn]['buildings']:                                    # every other building sits on a locally flat plot
            if b.get('disabled'):
                continue
            m = ndimage.binary_dilation(poly_mask(b['footprint'], xs, ys), iterations=2)
            if m.sum() == 0:
                continue
            hp = float(np.median(h[m]))
            w_ = sm(1 - ndimage.distance_transform_edt(~m) / 6.0)
            h = h * (1 - w_) + hp * w_
    padw = np.zeros((H, W), np.float32)
    for p_ in pads.values():
        padw = np.maximum(padw, poly_mask(p_['poly'], xs, ys).astype(np.float32))
    # ---- river gorge (v76 model on the vector river), lakes, pond, swamp
    riv = next(b for b in water if b['id'] == 'river')
    axis = [tuple(p) for p in riv['axis']]
    widths = riv['width_m']
    rmask = np.zeros((H, W), bool)
    for (a, b), wa in zip(zip(axis[:-1], axis[1:]), widths[1:]):
        for p in resample([a, b], 0.7):
            r_ = wa / 2.0
            x0, x1 = int(max(0, p[0] - r_ - 1)), int(min(W, p[0] + r_ + 2))
            y0, y1 = int(max(0, p[1] - r_ - 1)), int(min(H, p[1] + r_ + 2))
            rmask[y0:y1, x0:x1] |= np.hypot(xs[y0:y1, x0:x1] - p[0], ys[y0:y1, x0:x1] - p[1]) <= r_
    bridge = np.zeros((H, W), bool)
    for lb_ in F['land_bridges']:
        bridge |= ((xs - lb_['centre'][0]) / lb_['rx_m']) ** 2 + ((ys - lb_['centre'][1]) / lb_['ry_m']) ** 2 < 1
    d_riv = ndimage.distance_transform_edt(~rmask)
    bed_line = 0.9 + 1.4 * sm((ys - 96.0) / 220.0) + 10.0 * sm((ys - 600.0) / 160.0)      # lower bed: gorge cut into the ground
    depth = np.clip(6.0 + 7.0 * sm((ys - 320) / 380.0), 6, 13)
    bank = bed_line + depth
    near = sm(1 - (d_riv - 9.0) / 150.0) ** 1.4                         # wide gentle rise towards the gorge rims (no levee wall)
    riv_zone = (ys > 80) & (ys < 770) & (xs > 430) & (xs < 700) & (padw < 0.5)
    h = np.where(land & ~mt & riv_zone, np.maximum(h, h * (1 - near) + bank * near), h)
    chan = sm(1 - (d_riv - 1.0) / 6.0) * riv_zone
    h = np.where(bridge, np.maximum(h, bank), h * (1 - chan) + bed_line * chan)
    lakes = []
    for b in water:
        if b['kind'] in ('lake', 'pond', 'swamp') and b.get('outline'):
            m = poly_mask(b['outline'], xs, ys)
            if m.sum() == 0:
                continue
            dl = ndimage.distance_transform_edt(~m)
            ring = (dl > 0) & (dl < 4)
            surf = float(np.percentile(h[ring], 20)) - 0.25
            if b['id'] == 'mountain_lake':
                surf = max(surf, GROUND + 14.0)
            inside_d = ndimage.distance_transform_edt(m)
            bed = surf - b['depth_m'] * sm(inside_d / 6.0)
            h = np.where(m, np.minimum(h, bed), h)
            h = np.where((dl > 0) & (dl < 8), np.minimum(h, surf + 0.25 + 0.5 * (dl / 8.0) + np.maximum(0, h - surf) * sm(dl / 8.0)), h)
            lakes.append({'id': b['id'], 'kind': b['kind'], 'surface_m': round(surf, 2)})
    # piers / jetties are decks over the water, not causeways
    near_sea = ndimage.binary_dilation(sea, iterations=10) & ~(cls == 3)
    for dn in ('beach', 'elite', 'port'):
        for z in Dd[dn]['zones']:
            if z.get('kind') == 'pier' and len(z.get('poly') or []) >= 3:
                m = ndimage.binary_dilation(poly_mask(z['poly'], xs, ys), iterations=1) & near_sea
                h = np.where(m, np.minimum(h, -1.5), h)
    # steppe beyond the border rises softly to the horizon
    steppe = ys > np.interp(xs, [0, 540, 1060, 1744], [905, 912, 912, 905])
    h = np.where(steppe & land, np.maximum(h, GROUND + 7.0 * sm((ys - 912) / 38.0)), h)
    # ---- roads: profile, grade limit, imprint with gentle side slopes
    sm6 = ndimage.gaussian_filter(h, 6)
    stamp_h = np.full((H, W), np.nan, np.float32)
    stamp_hw = np.zeros((H, W), np.float32)
    stamp_k = np.full((H, W), 0.45, np.float32)
    report = []
    bridges = []
    for rd in roads:
        if rd['kind'] == 'tunnel':
            continue
        pts = resample([tuple(p) for p in rd['points']], 2.0)
        ix = np.clip([int(p[0]) for p in pts], 0, W - 1)
        iy = np.clip([int(p[1]) for p in pts], 0, H - 1)
        seg = np.hypot(np.diff([p[0] for p in pts]), np.diff([p[1] for p in pts]))
        L = np.concatenate([[0], np.cumsum(seg)])
        if rd['kind'] == 'stone_serpentine' and rd.get('heights_abs'):
            ha = np.array(rd['heights_abs'], float)
            Ls = np.array(rd['heights_abs_s'], float)
            prof = np.interp(L * (Ls[-1] / max(L[-1], 1e-6)), Ls, ha)
        else:
            prof = sm6[iy, ix].astype(np.float64)
            prof = ndimage.uniform_filter1d(prof, 41, mode='nearest')
            prof = np.maximum(prof, 0.9)
            if rd.get('dt_entry'):
                prof[-1] = 5.0 + 0.06                                          # Downtown pad height at the entry
            if rd['kind'] == 'bridge':
                a0, b0 = sm6[iy[0], ix[0]], sm6[iy[-1], ix[-1]]
                prof = np.maximum(np.interp(L, [0, L[-1]], [max(a0, 3.0), max(b0, 3.0)]), 3.0)
            g = rd.get('max_grade', 0.08)
            fixed = [len(prof) - 1] if rd.get('dt_entry') else []
            for _ in range(4):
                for i in range(1, len(prof)):
                    if i in fixed:
                        continue
                    prof[i] = np.clip(prof[i], prof[i - 1] - g * seg[i - 1], prof[i - 1] + g * seg[i - 1])
                for i in range(len(prof) - 2, -1, -1):
                    prof[i] = np.clip(prof[i], prof[i + 1] - g * seg[i], prof[i + 1] + g * seg[i])
        grade = np.abs(np.diff(prof)) / np.maximum(seg, 1e-3)
        report.append({'id': rd['id'], 'max_grade_pct': round(float(np.percentile(grade, 98)) * 100, 1), 'length_m': round(float(seg.sum()), 1)})
        rd['heights'] = [round(float(v), 2) for v in prof]
        rd['heights_step_m'] = 2.0
        span = None
        if rd.get('bridge'):
            span = (rd['bridge']['from'], rd['bridge']['to'])
            bridges.append({'road': rd['id'], 'from': span[0], 'to': span[1]})
        if rd['kind'] == 'bridge':
            bridges.append({'road': rd['id'], 'from': rd['points'][0], 'to': rd['points'][-1]})
            continue                                                    # deck over the water: no terrain imprint
        hw = rd['width_m'] / 2
        slope_k = 0.30 if rd['kind'] == 'serpentine' else 0.9 if rd['kind'] == 'stone_serpentine' else 0.45
        fine = resample([tuple(p) for p in rd['points']], 0.5)
        Lf = np.concatenate([[0], np.cumsum(np.hypot(np.diff([p[0] for p in fine]), np.diff([p[1] for p in fine])))])
        zf = np.interp(Lf, L, prof)
        for p, z in zip(fine, zf):
            if span and c.seg_dist(p, span[0], span[1])[0] < 3.0:
                continue
            ix, iy = int(p[0]), int(p[1])
            if 0 <= ix < W and 0 <= iy < H:
                stamp_h[iy, ix] = z
                stamp_hw[iy, ix] = hw
                stamp_k[iy, ix] = slope_k
    # one smooth corridor field for all roads (v01 imprinted per sample point -> scalloped banks): nearest centre line -> its height,
    # half width and slope; reach from the SMOOTHED height difference, so cut / fill slopes are even along the road
    has = ~np.isnan(stamp_h)
    dist, (iy_, ix_) = ndimage.distance_transform_edt(~has, return_indices=True)
    rh = stamp_h[iy_, ix_]
    rhw = stamp_hw[iy_, ix_]
    rk = stamp_k[iy_, ix_]
    dz = ndimage.gaussian_filter(np.abs(sm6 - rh), 5)
    reach = rhw + 1.0 + np.clip(dz / rk, 5.0, 70.0)
    flat = rhw + 1.7                                                        # asphalt + ~1.5 m flat shoulder (1 m grid / stamping error)
    road_w = sm(1 - (dist - flat) / np.maximum(reach - flat, 0.5))
    road_w = np.where(dist > reach, 0.0, road_w)
    sink = np.where(dist < rhw + 0.7, 0.10, 0.0)                            # terrain 10 cm under the road mesh: no poking through
    h = h * (1 - road_w) + (rh - sink) * road_w
    # VIEW B: low outer berm 1-1.5 m along the serpentine where it runs on a fill / along the pass (v10 §3.2), view stays open
    serp_pts = resample([tuple(p) for p in serp['points']], 2.0)
    d_s = dist_pl(serp['points'], xs, ys, 12)
    berm = 1.25 * sm(1 - np.abs(d_s - (serp['width_m'] / 2 + 2.2)) / 1.6) * sm(np.hypot(xs - vb[0], ys - vb[1]) / 25.0)
    h = h + berm.astype(np.float32)
    # ---- tunnel: holes at the portals
    tun = [tuple(p) for p in F['tunnel_axis']]
    za = float(h[int(tun[0][1]), int(tun[0][0])])
    zb = float(h[int(tun[-1][1]), int(tun[-1][0])])
    d = dist_pl(tun, xs, ys, 30)
    holes = np.zeros((H, W), bool)
    for p, z in ((tun[0], za), (tun[-1], zb)):
        nearp = np.hypot(xs - p[0], ys - p[1]) < 14
        holes |= nearp & (d < 4.0) & (h > z + 1.5)
    cover = float(np.min([h[int(p[1]), int(p[0])] - (za + (zb - za) * i / (len(tun) - 1)) for i, p in enumerate(tun)][1:-1]))
    # ---- no van traps: fill closed land depressions deeper than 0.6 m (priority flood), water bodies excluded
    keep = np.zeros((H, W), bool)
    for b in water:
        if b.get('outline'):
            keep |= ndimage.binary_dilation(poly_mask(b['outline'], xs, ys), iterations=3)
    keep |= ndimage.binary_dilation(rmask, iterations=3) | sea | holes
    filled = priority_flood(h, sea | (xs < 1) | (xs > W - 2) | (ys < 1) | (ys > H - 2))
    depth_ = filled - h
    trap = (depth_ > 0.6) & ~keep & land
    n_trap = int(ndimage.label(trap)[1])
    h = np.where(trap, filled - 0.6, h)
    # ---- export
    np.save(os.path.join(WORK, 'height_1m.npy'), h)
    os.makedirs(OUT, exist_ok=True)
    zz = np.clip((h - BASE_Y) / HEIGHT_RANGE, 0, 1)
    from scipy.ndimage import map_coordinates
    GX, GY = np.meshgrid(np.linspace(0, W - 1, RES), np.linspace(0, H - 1, RES))
    hr = map_coordinates(zz, [GY, GX], order=1)
    (hr * 65535).round().astype('<u2').tofile(os.path.join(OUT, 'Heightmap_v85_2049_r16.bytes'))
    hm = map_coordinates(holes.astype(np.float32), [np.linspace(0, H - 1, RES - 1)[:, None] * np.ones((1, RES - 1)),
                                                    np.ones((RES - 1, 1)) * np.linspace(0, W - 1, RES - 1)[None, :]], order=0)
    np.packbits((hm < 0.5).astype(np.uint8)).tofile(os.path.join(OUT, 'Holes_v85_2048_bits.bytes'))
    gy_, gx_ = np.gradient(h)
    slope = np.degrees(np.arctan(np.hypot(gx_, gy_)))
    save_json('terrain_v85.json', {
        'heightmap': 'Heightmap_v85_2049_r16.bytes', 'format': 'RAW 16-bit LE, %d x %d, row 0 = south (world y 0), column 0 = west' % (RES, RES),
        'holes': 'Holes_v85_2048_bits.bytes (packbits, 1 = solid, 2048 x 2048, row 0 = south)',
        'size_m': [W, HEIGHT_RANGE, H], 'position_m': [0, BASE_Y, 0], 'sea_level_m': 0.0, 'ground_m': GROUND,
        'pads': pads, 'construction_pad_m': round(pad_c, 2), 'tunnel': {'axis': [list(p) for p in tun], 'portal_heights_m': [round(za, 2), round(zb, 2)],
                                                                       'clear_height_m': 5.5, 'width_m': 9.0, 'min_cover_m': round(cover, 1)},
        'road_grades': report, 'bridges': bridges, 'lakes': lakes,
        'river': {'bed_formula': '0.9 + 1.4 sm((y-96)/220) + 10 sm((y-600)/160)', 'surface_above_bed_m': 1.2, 'gorge_depth_m': [6, 13]},
        'relief': relief_log, 'traps_filled': n_trap,
        'peaks_m': {'hill_B': round(float(h[(ys > 540) & (ys < 640) & (xs > 750) & (xs < 1150)].max()), 1), 'elite': round(float(h[rho < 1].max()), 1),
                    'nw_ridge': round(float(h[xs < 560].max()), 1), 'right_ridge': round(float(h[(xs > 1020) & (xs < 1110) & (ys > 870)].max()), 1),
                    'view_B_road': round(float(h[int(vb[1]), int(vb[0])]), 1)},
        'land_slope_deg_p99': round(float(np.percentile(slope[land & ~mt & ~rock], 99)), 1)})
    save_json('roads_v85.json', {**load_json('roads_v85.json'), 'roads': roads})
    preview(h, relief_log, F, roads)
    t = load_json('terrain_v85.json')
    print(json.dumps(t['peaks_m']), 'tunnel', t['tunnel']['portal_heights_m'], 'cover', t['tunnel']['min_cover_m'], 'traps filled', n_trap, 'slope p99', t['land_slope_deg_p99'])
    for r_ in report:
        if r_['max_grade_pct'] > 8.5:
            print('  steep', r_)


def priority_flood(h, seeds):
    """Fill closed depressions (Barnes et al. priority flood, 8-connected)."""
    Hh, Ww = h.shape
    out = h.astype(np.float64).copy()
    done = np.zeros(h.shape, bool)
    pq = []
    ys_, xs_ = np.nonzero(seeds)
    for y, x in zip(ys_.tolist(), xs_.tolist()):
        heapq.heappush(pq, (out[y, x], y, x))
        done[y, x] = True
    nb = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))
    while pq:
        z, y, x = heapq.heappop(pq)
        for dy, dx in nb:
            ny, nx = y + dy, x + dx
            if 0 <= ny < Hh and 0 <= nx < Ww and not done[ny, nx]:
                done[ny, nx] = True
                if out[ny, nx] < z:
                    out[ny, nx] = z
                heapq.heappush(pq, (out[ny, nx], ny, nx))
    return out.astype(np.float32)


def preview(h, relief, F, roads):
    from PIL import Image, ImageDraw
    gy, gx = np.gradient(h)
    n = np.dstack([-gx, -gy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    l = np.array([-0.5, 0.5, 0.7]); l /= np.linalg.norm(l)
    sh = np.clip(n @ l, 0, 1)
    base = np.dstack([0.55 + 0.004 * h, 0.62 + 0.002 * h, 0.45 + 0.004 * h])
    img = base * (0.35 + 0.75 * sh[..., None])
    img[h < 0] = np.array([0.45, 0.7, 0.85]) * (1 + h[h < 0, None] / 30)
    im = Image.fromarray((np.clip(img, 0, 1)[::-1] * 255).astype(np.uint8))
    im.save(os.path.join(WORK, 'relief_shaded_v85.png'))
    sc = 1
    dr = ImageDraw.Draw(im)
    P = lambda p: (p[0] * sc, (H - p[1]) * sc)
    for rd in roads:
        dr.line([P(p) for p in rd['points']], fill=(70, 70, 75) if rd['kind'] != 'dirt' else (160, 130, 90), width=3)
    for i, rf in enumerate(relief):
        col = (180, 40, 40) if rf['height_m'] > 0 else (40, 80, 200)
        dr.line([P(p) for p in rf['crest']], fill=col, width=3)
        q = P(rf['crest'][len(rf['crest']) // 2])
        dr.text((q[0] + 4, q[1] - 12), '%s%d %+.0f m' % ('H' if rf['height_m'] > 0 else 'G', i + 1, rf['height_m']), fill=col)
    for name, p, txt in (('B', F['view_B'], 'VIEW B (перевал)'), ('C', F['view_C'], 'VIEW C')):
        q = P(p)
        dr.ellipse((q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4), fill=(255, 255, 255))
        dr.text((q[0] + 6, q[1] - 6), txt, fill=(255, 255, 255))
    im.save(os.path.join(WORK, 'relief_scheme_v85.png'))


if __name__ == '__main__':
    main()
