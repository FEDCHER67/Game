"""Step 3 (v85 data, W86 relief pass 2026-10-22): terrain heightmap — "harmoniously uneven" relief (handoff v10 §3, v02 §3 / §8),
water levels + waterfalls, the far steppe backdrop beyond the north border.

Grid 1 m (1744 x 950), exported as Unity RAW 16-bit LE 2049 x 2049 (row 0 = south), terrain 1744 x HEIGHT_RANGE x 950 m at Y = BASE_Y.
W86 changes (Working/Reviews/MapW85_Audit_2026-10-21 AUDIT §5 1-13, RELIEF_SCAN §7 A-G; Vadim 22.10 complaints 1-3):
 - river gorge CUT INTO the ground: one water profile (surface_m per axis point) from the mountain lake on a bench of the NW ridge
   (30 m) -> brook -> mountain waterfall (29.3 -> 12 m) -> plunge pool -> stream in a ravine -> river in the gorge round the Hamlet ->
   two natural land bridges -> road bridge -> gorge through the grey rocks -> waterfall straight into the sea; soft shoulders (6-11 %
   slopes, no box, no pad holes) only where the ground is lower than surface + 4-5 m (A: Fedya's wall, the lab pit);
 - pads blend over a width that follows the height difference (B), plots too (G); Construction hill with wide, uneven, asymmetric
   rings (F); Elite hill = octagonal plateau with natural flanks (gentle to the city, rocky to the sea), plateau + villa terraces
   re-applied after the roads, stone road corridor capped (AUDIT 3, 11);
 - roads: profiled in rank order, every end pinned to its parent road / pad / Downtown entry (D), road samples inside a pad = pad
   height (port, Rough, lab yards flat), one weighted corridor per road (no nearest-line seam), per-kind side slope and reach (C),
   VIEW B berm only on the outer (downhill) side; Hamlet streets get a gentle profile (<= 8-10 %);
 - Hamlet relief: designed hills / dips of hamlet_v85.json terrain_features (s04_west) before the plots are flattened;
 - north: soft steppe rise, a continuous rocky coastal ridge on the Rough's east edge (v02 §8.4 "~30 m, hides the harbour"), the
   north strip smoothed for the seam of the separate far-steppe backdrop terrain (steppe_backdrop_v02.json + RAW);
 - trap filler only caps closed land depressions at 0.8 m (soft), designed dips / water / gorge exempt; Downtown v37 land interface;
 - export samples the 1 m cell-centre grid at the real world positions of the RAW vertices (v01 was ~0.5 m off).
Set SNAP_HOOK = callable(name, h, extra) to receive a copy of h after every block (relief scan stage attribution).
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
SNAP_HOOK = None


def snap(name, h, **extra):
    if SNAP_HOOK is not None:
        SNAP_HOOK(name, h.copy(), extra)


def sm(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def smax(a, b, k=1.0):
    return 0.5 * (a + b + np.sqrt((a - b) ** 2 + k * k))


def fbm(xs, ys, scale, oct_=4, seed=0):
    out = np.zeros(xs.shape, np.float32)
    amp, tot = 1.0, 0.0
    r_ = np.random.default_rng(seed)
    x_min, y_min = float(np.min(xs)), float(np.min(ys))
    for o in range(oct_):
        s = scale / (2 ** o)
        gw, gh = int((float(np.max(xs)) - min(0.0, x_min)) / s) + 3, int((float(np.max(ys)) - min(0.0, y_min)) / s) + 3
        g = r_.random((max(gh, int(H / s) + 3), max(gw, int(W / s) + 3))).astype(np.float32)
        fx, fy = (xs - min(0.0, x_min)) / s, (ys - min(0.0, y_min)) / s
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


def bbox_slice(mask, pad):
    ys_, xs_ = np.nonzero(mask)
    if len(ys_) == 0:
        return None
    return (slice(max(0, ys_.min() - pad), min(mask.shape[0], ys_.max() + pad + 1)),
            slice(max(0, xs_.min() - pad), min(mask.shape[1], xs_.max() + pad + 1)))


KEEP_OUT = None                                                           # set in main(): mountains / rocks / Elite plateau (0..1)


def flatten(h, mask, hp, b_min, b_max, angle=22.0, round_m=None):
    """flat at hp inside mask; outside the ground is kept inside the cone hp +- tan(angle) * d (soft clamp, RELIEF_SCAN §7 B / G: the edge
    slope never exceeds `angle`, whatever the height difference), plus a short rounding blend (round_m, default b_min / 2) at the edge.
    Returns the horizontal reach of the change (m)."""
    sl = bbox_slice(mask, int(b_max) + 2)
    if sl is None:
        return 0.0
    m = mask[sl]
    hh = h[sl]
    d = ndimage.distance_transform_edt(~m)
    t = math.tan(math.radians(angle))
    lo, hi = hp - t * d, hp + t * d
    hc = 0.5 * (hh + hi - np.sqrt((hh - hi) ** 2 + 0.6))
    hc = 0.5 * (hc + lo + np.sqrt((hc - lo) ** 2 + 0.6))
    rm = round_m if round_m is not None else max(3.0, b_min / 2.0)
    w = sm(1 - d / rm)
    new = hc * (1 - w) + hp * w
    new = np.where(m, hp, new)
    fade = sm(1 - (d - (b_max - 12.0)) / 12.0)                               # the window edge never shows
    if KEEP_OUT is not None:
        fade = fade * (1 - KEEP_OUT[sl])
        fade = np.where(m, 1.0, fade)
    h[sl] = hh + (new - hh) * fade
    ch = np.abs(new - hh) > 0.05
    return float(d[ch].max()) if ch.any() else 0.0


# designed medium relief (world v85 metres): kind, crest polyline, half-width, height (+ hill / - gully), role
RELIEF = [
    ('hill', [(552, 522), (596, 534), (640, 546)], 34, 7.0, 'разделяет Стройку и Неблагополучный, закрывает вид на Неблагополучный с главной дороги; объезд по лугу'),
    ('hill', [(706, 418), (738, 438), (770, 452)], 38, 9.0, 'закрывает западный фасад Даунтауна от Стройки; смотровая точка на город'),
    ('hill', [(712, 262), (744, 274), (776, 280)], 26, 5.0, 'отделяет скалы Тихой долины от юго-западного угла Даунтауна, ломает прямой вид с пляжа на главную дорогу'),
    ('hill', [(472, 204), (492, 214), (512, 227)], 26, 5.5, 'отделяет лес от Тихой долины; грунтовка огибает его'),
    ('hill', [(575, 612), (598, 626)], 16, 3.5, 'бугор на лугу перед Неблагополучным (вопрос 9: да)'),
    ('hill', [(690, 590), (704, 604)], 19, 3.0, 'бугор у подножия холма B, разнообразит луг'),
    ('hill', [(536, 640), (552, 652)], 14, 2.5, 'бугор у дороги Хутор - Неблагополучный'),
    ('hill', [(232, 248), (262, 262)], 30, 4.5, 'пологий подъём в лесу'),
    ('hill', [(338, 112), (372, 126)], 26, 3.5, 'пологий подъём в лесу'),
    ('gully', [(580, 556), (548, 560), (516, 563)], 9, -3.0, 'промоина к реке: бездорожье интереснее, сток'),
    ('gully', [(700, 500), (680, 516), (656, 528)], 8, -2.5, 'ложбина между холмом Стройки и холмом B'),
]
# NE coastal rocky ridge along the cliff band east of the Rough (v02 §8.4 l.71 "скалистая гряда ~30 м на восточном краю Rough закрывает
# гавань"): crest on the coast, height above the ground per crest point; joins the right ridge at the north edge
NE_RIDGE = [(1044, 908, 26.0), (1050, 884, 25.0), (1066, 856, 24.0), (1088, 826, 22.0), (1110, 799, 20.0), (1133, 773, 18.0),
            (1155, 751, 15.0), (1172, 733, 11.0)]
# mountain lake on a bench of the NW ridge (Vadim 22.10: "on the mountain"; map v85: lake at the ridge foot, waterfall between two rocks,
# plunge pool) - bench polygon (merges into the ridge in the west / north), two rock buttresses that frame the waterfall
LAKE_BENCH = [(458, 704), (474, 702), (500, 704), (510, 712), (515, 730), (517, 752), (513, 772), (503, 786), (484, 792), (464, 790),
              (454, 772), (452, 740)]
BENCH_BACK = ([(446, 806), (474, 813), (498, 810)], 22.0, 40.0)            # rock wall behind the lake (crest, half width, top m)
BENCH_H = 31.6
FALL_ROCKS = [((472.5, 699.0), 7.0, 24.0), ((499.0, 700.0), 7.5, 23.0)]   # (centre, radius, top m) - "водопад между двумя камнями"
LAKE_SURF, POOL_SURF = 30.0, 12.0
# water surface along the river axis (world point -> nearest axis station), metres; between the controls: linear in arc length
RIVER_CTRL = [('lake_edge', (488.7, 747.2), LAKE_SURF), ('fall_lip', (485.3, 703.6), 29.3), ('fall_base', (485.2, 698.3), POOL_SURF),
              ('pool_exit', (484.9, 686.3), POOL_SURF), ('stream_mid', (480.0, 636.0), 8.2), ('land_bridge_2', (488.0, 572.6), 5.6),
              ('hamlet_mid', (481.2, 484.0), 4.9), ('land_bridge_1', (484.0, 349.0), 4.4), ('bend', (496.0, 316.0), 4.35),
              ('road_bridge', (543.2, 303.2), 4.3), ('rocks_in', (626.8, 283.9), 4.2), ('rocks_mid', (650.6, 217.4), 4.1),
              ('sea_lip', None, 4.0)]
WATER_DEPTH = 1.2
QV_MOUTH_RIB = [(660, 89), (672, 89), (679, 118), (678, 150), (672, 168), (662, 168), (661, 120)]   # high grey rock on the east bank where the river leaves the rocks                                                          # river surface above the bed (builder flow mesh)
# road ranks (parents first) and corridor parameters per kind: side slope k (dz / run; smoothstep peak = 1.5 x), reach cap m
ROAD_ORDER = ['rough_ring', 'main_hamlet_downtown', 'hamlet_main_link', 'hamlet_bypass', 'hamlet_to_rough', 'rough_west_link', 'port_road',
              'rough_to_port', 'bridge_tramduro', 'cornice_view_c', 'serpentine_view_b', 'tunnel_north_approach', 'tunnel_south_approach',
              'to_quiet_valley', 'valley_lab_spur', 'construction_gate', 'border_checkpoint_road', 'elite_stone_road', 'beach_van_track',
              'forest_road_hamlet', 'forest_road_wagon_east', 'forest_road_east', 'forest_link_bypass', 'forest_link_hamlet', 'forest_to_valley']
KIND_RANK = {'district_ring': 0, 'rural_asphalt': 1, 'bridge': 1, 'serpentine': 2, 'stone_serpentine': 2, 'drive': 3, 'sand_track': 4, 'dirt': 4}
ROAD_K = {'serpentine': (0.25, 30.0), 'stone_serpentine': (0.55, 12.0), 'sand_track': (0.25, 25.0), 'dirt': (0.25, 30.0), 'drive': (0.25, 35.0)}
ROAD_K_DEFAULT = (0.25, 45.0)


def main():
    cls = c.apply_land_override(np.load(os.path.join(WORK, 'classes_v85.npy')))
    xs, ys = grid()
    F = load_json('features_v85.json')
    roads_doc = load_json('roads_v85.json')
    roads = roads_doc['roads']
    water_doc = load_json('water_v85.json')
    water = water_doc['bodies']
    Dd = {n: load_json('districts/%s_v85.json' % n) for n in
          ('beach', 'construction', 'downtown', 'elite', 'forest', 'hamlet', 'port', 'quiet_valley', 'rough', 'tramduro')}
    dt37 = c.downtown_v37_land()
    sea = (cls == 1) | ((xs > 1440) & (ys < 145))                       # legend box drawn over the sea
    rib = poly_mask(QV_MOUTH_RIB, xs, ys)
    sea &= ~rib
    land = ~sea
    d_sea = ndimage.distance_transform_edt(land)
    d_land = ndimage.distance_transform_edt(sea)
    relief_log = []
    # ---- coast + sea floor
    h = np.where(land, 0.6 + (GROUND - 0.6) * sm(d_sea / 30.0), -np.minimum(0.4 + d_land * 0.16, 12.0)).astype(np.float32)
    sand = ndimage.binary_closing(cls == 3, iterations=2)
    near_sand = ndimage.distance_transform_edt(~sand)
    h = np.where(land & (near_sand < 25), np.minimum(h, 0.6 + 1.6 * sm(d_sea / 70.0) + 0.1 * near_sand), h)
    beach_sea = sea & (ndimage.distance_transform_edt(~sand) < 40)
    h = np.where(beach_sea, np.maximum(h, -0.3 - d_land * 0.09), h)
    coastfade = sm(d_sea / 40.0)
    snap('coast', h)
    # ---- micro relief 0.3-1.5 m (two scales, no grid pattern) + very soft swells
    micro = 0.55 * fbm(xs, ys, 9, 2, 11) + 0.75 * fbm(xs, ys, 23, 3, 12)
    swell = 1.6 * fbm(xs, ys, 120, 2, 13)
    h = np.where(land, h + (micro + swell) * coastfade, h)
    snap('micro_swell', h)
    # ---- designed medium relief (world) + Hamlet relief (s04_west terrain_features)
    dips = np.zeros((H, W), bool)
    feats = [(k, cr, hw, hh, role, None) for k, cr, hw, hh, role in RELIEF]
    for f_ in Dd['hamlet'].get('terrain_features') or []:
        feats.append((f_['kind'], [tuple(p) for p in f_['crest']], f_['half_width_m'], f_['height_m'], f_['role_ru'], f_['id']))
    for i, (kind, crest, hw, hh, role, fid) in enumerate(feats):
        d = dist_pl(crest, xs, ys, hw * 1.6)
        along = 1.0 + 0.15 * fbm(xs, ys, 40, 2, int(abs(hh) * 10) + len(crest) + i)
        prof = sm(1 - d / hw) ** (1.25 if hh > 0 else 1.3)                  # W86: gullies U-shaped (0.8 -> 1.3, RELIEF_SCAN #25)
        h = np.where(land, h + hh * prof * along * coastfade, h)
        if hh < 0:
            dips |= d < hw
        relief_log.append({'id': fid or ('%s%d' % ('H' if hh > 0 else 'G', i + 1)), 'kind': kind, 'crest': [list(map(float, p)) for p in crest],
                           'half_width_m': hw, 'height_m': hh, 'role_ru': role, 'district': 'hamlet' if fid else None})
    snap('designed_relief', h)
    # ---- NW ridge (map mountains + generator crest functions), right ridge, NE coastal ridge, mountain-lake bench
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
    # NE coastal ridge: crest heights interpolated along the crest, inland half width 30 m, rocky (ridged noise)
    ner = [(x, y) for x, y, _ in NE_RIDGE]
    ner_h = np.array([v for _, _, v in NE_RIDGE], np.float32)
    d_ne = dist_pl(ner, xs, ys, 60)
    st_m = np.zeros((H, W), bool)
    hv = np.zeros((H, W), np.float32)
    for (a, ha), (b, hb_) in zip(zip(ner[:-1], ner_h[:-1]), zip(ner[1:], ner_h[1:])):
        nseg = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.5))
        for t in np.linspace(0, 1, nseg):
            ix_, iy_ = int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t)
            st_m[iy_, ix_] = True
            hv[iy_, ix_] = ha + (hb_ - ha) * t
    _, (iy_n, ix_n) = ndimage.distance_transform_edt(~st_m, return_indices=True)
    h_ne = hv[iy_n, ix_n] * sm(1 - d_ne / 30.0) ** 1.1 * (0.82 + 0.18 * ridged)
    mtv = np.maximum.reduce([mtn, h_diag, h_ext, h_ext2, h_r2, h_ne]) + 3.0 * fbm(xs, ys, 11, 2, 21) * np.clip(np.maximum.reduce([h_diag, h_ext, h_ext2, h_ne]) / 12.0, 0, 1)
    mtv = np.minimum(mtv, 90.0)
    k = np.clip(mtv / 2.0, 0, 1)
    h = np.where(land | mt, h + (np.maximum(h, GROUND + mtv) - h) * k, h)
    relief_log.append({'id': 'NE_RIDGE', 'kind': 'ridge', 'crest': [list(p) for p in ner], 'half_width_m': 30, 'height_m': float(ner_h.max()),
                       'role_ru': 'скалистая гряда на восточном краю Неблагополучного (~30 м абс.): закрывает гавань и море на северо-востоке (v02 §8.4)'})
    # mountain-lake bench on the NW ridge: flat shelf, steep rocky faces to the south (waterfall) and east, merges into the ridge
    bench = poly_mask(LAKE_BENCH, xs, ys)
    jag = 5.0 * fbm(xs, ys, 9, 3, 32) * sm((xs - 492.0) / 10.0)              # jagged rocky east face, clean waterfall face
    d_b0 = ndimage.distance_transform_edt(~bench)
    d_b = np.where(bench, 0.0, np.maximum(0, d_b0 + jag * sm(d_b0 / 3.0)))
    bench = d_b <= 0
    L_face = 7.0 + (9.0 + 4.0 * fbm(xs, ys, 17, 2, 34)) * sm((xs - 500.0) / 14.0)   # 7 m (waterfall face) .. 12-20 m (east face)
    cr_b, hw_b, top_b = BENCH_BACK
    db_ = dist_pl(cr_b, xs, ys, hw_b * 1.5)
    h = np.maximum(h, np.where(db_ < hw_b, GROUND + (top_b - GROUND) * sm(1 - db_ / hw_b) ** 1.1 * (0.8 + 0.2 * ridged), h))
    bh = BENCH_H + 0.6 * fbm(xs, ys, 16, 2, 31) + 7.0 * sm((476.0 - xs) / 26.0) + 5.0 * sm((ys - 772.0) / 22.0)   # cirque floor rises to the ridge
    wb = np.where(bench, 1.0, 1 - sm(d_b / L_face))
    h = np.where(wb > 0, np.maximum(h, h * (1 - wb) + bh * wb), h)
    for (cx_, cy_), r_, top_ in FALL_ROCKS:                                  # the two rocks that frame the waterfall and the pool
        dr_ = np.hypot(xs - cx_, ys - cy_) / r_
        h = np.maximum(h, np.where(dr_ < 1.6, top_ - (top_ - h) * sm(dr_ - 0.55) + 1.2 * fbm(xs, ys, 4, 2, 33) * (dr_ < 1), h))
    relief_log.append({'id': 'LAKE_BENCH', 'kind': 'bench', 'crest': [[470.0, 745.0], [505.0, 760.0]], 'half_width_m': 40, 'height_m': BENCH_H,
                       'role_ru': 'уступ хребта с горным озером (30 м): ручей к обрыву, водопад между двумя камнями в чашу (12 м)'})
    snap('mountains_ridges', h)
    # steppe beyond the border rises softly to the horizon (faded near the sea: no wall at the NW corner, RELIEF_SCAN #8 / #17)
    try:
        fl = np.array(load_json('border_v85.json')['fence_line'], float)
        fl = fl[np.argsort(fl[:, 0])]
    except Exception:
        fl = None
    y_st = np.interp(xs, [0, 540, 1060, 1744], [905, 912, 912, 905])
    if fl is not None:                                                     # behind the state fence: steppe from the fence line on
        on_f = (xs >= fl[0, 0]) & (xs <= fl[-1, 0])
        y_st = np.where(on_f, np.interp(xs, fl[:, 0], fl[:, 1]) + 1.0, y_st)
    steppe = ys > y_st
    h = np.where(steppe & land, np.maximum(h, 0.6 + (GROUND - 0.6) * sm(d_sea / 30.0) + 2.5 * sm((ys - y_st) / 25.0) * sm(d_sea / 45.0)), h)
    snap('steppe', h)
    # ---- grey crags (Quiet Valley rocks between the valley and the beach, cornice cliffs, coast rocks), impassable
    rock = ndimage.binary_opening(ndimage.binary_closing(cls == 6, iterations=2), iterations=2) & ~mt
    lab, n = ndimage.label(rock)
    rock = np.isin(lab, [i + 1 for i, s_ in enumerate(ndimage.sum(rock, lab, range(1, n + 1))) if s_ > 250])
    tz = [z for z in Dd['tramduro']['zones'] if z['kind'] in ('yard', 'lawn', 'palace_lawn', 'golf') and len(z.get('poly') or []) >= 3]
    for z in tz:
        rock &= ~poly_mask(z['poly'], xs, ys)
    qvr = poly_mask(F['quiet_valley_rocks'], xs, ys)
    rock |= qvr & land
    spikes = ndimage.binary_opening(cls == 5, iterations=1) & ~mt & (xs > 600) & (xs < 720) & (ys > 80) & (ys < 320)   # grey rock spikes east of the river
    rock |= ndimage.binary_fill_holes(ndimage.binary_closing(spikes, iterations=5)) & land
    rock |= poly_mask(QV_MOUTH_RIB, xs, ys) & land
    d_rock = ndimage.distance_transform_edt(rock)
    h = np.where(rock, np.maximum(h, GROUND + 4 + np.minimum(d_rock * 1.6, 10) + 2 * fbm(xs, ys, 8, 2, 7)), h)
    snap('rocks', h)
    # ---- hill B 50 m (west summit over the tunnel); the VIEW B pass is cut only as far as the serpentine needs (bench, <= 18 deg banks)
    hb = F['hill_B']
    d = dist_pl(hb['crest'], xs, ys, 140)
    py0 = next(z for z in Dd['port']['zones'] if z['id'] == '06-yard')['poly']
    d_port = ndimage.distance_transform_edt(~poly_mask(py0, xs, ys))
    hb_x = np.interp(xs, [700, 790, 830, 990, 1050, 1180], [0.9, 1.0, 1.2, 1.2, 0.78, 0.6])            # summit W of the pass, lower east part
    d_port_n = d_port + 10.0 * fbm(xs, ys, 30, 2, 81)
    hillB = (41.0 * sm(1 - d / 110.0) ** 1.15 + 4.0 * sm(1 - d / 40.0)) * hb_x * sm(d_port_n / 95.0) ** 0.5   # east end runs down to the port
    hbv = GROUND + hillB * (1 + 0.03 * fbm(xs, ys, 30, 2, 8))
    dt_m = poly_mask(dt37['pad_poly'], xs, ys) if (dt37 and dt37.get('pad_poly')) else \
        np.logical_or.reduce([poly_mask(z['poly'], xs, ys) for z in Dd['downtown']['zones'] if z['kind'] == 'ground'])
    rg_m = poly_mask(next(z for z in Dd['rough']['zones'] if z['kind'] == 'ground')['poly'], xs, ys)
    dt_m = ndimage.binary_dilation(dt_m, iterations=3)                        # = the pad masks below (inner = 3)
    rg_m = ndimage.binary_dilation(rg_m, iterations=3)
    t32 = math.tan(math.radians(28.0))
    for pm_ in (dt_m, rg_m):
        dpm = ndimage.distance_transform_edt(~pm_)
        cone_p = GROUND + 0.3 + t32 * np.maximum(0, dpm + 4.0 * fbm(xs, ys, 40, 2, 82) * sm(dpm / 10.0))
        hbv = 0.5 * (hbv + cone_p - np.sqrt((hbv - cone_p) ** 2 + 2.0))
    hill_body = sm((hbv - GROUND - 0.3) / 1.0)
    serp = next(r for r in roads if r['id'] == 'serpentine_view_b')
    vb = F['view_B']
    sp_pts = resample([tuple(p) for p in serp['points']], 2.0)
    sp_L = np.concatenate([[0], np.cumsum(np.hypot(np.diff([p[0] for p in sp_pts]), np.diff([p[1] for p in sp_pts])))])
    i_top = int(np.argmin([math.hypot(p[0] - vb[0], p[1] - vb[1]) for p in sp_pts]))
    g_s = serp.get('max_grade', 0.12) * 0.96
    sp_z = np.minimum(GROUND + g_s * sp_L, GROUND + 0.06 + g_s * (sp_L[-1] - sp_L))   # provisional profile: climb from both ends
    st_s = np.zeros((H, W), bool)
    zst = np.zeros((H, W), np.float32)
    for p, z in zip(resample(sp_pts, 0.5), np.interp(np.linspace(0, 1, len(resample(sp_pts, 0.5))), np.linspace(0, 1, len(sp_z)), sp_z)):
        st_s[int(p[1]), int(p[0])] = True
        zst[int(p[1]), int(p[0])] = z
    d_s, (iy_s, ix_s) = ndimage.distance_transform_edt(~st_s, return_indices=True)
    cap = ndimage.gaussian_filter(zst[iy_s, ix_s] + 1.0 + np.tan(np.radians(22.0)) * np.maximum(0, d_s - serp['width_m'] / 2 - 2.0), 4.0)
    hbv = np.where(d_s < 220, 0.5 * (hbv + cap - np.sqrt((hbv - cap) ** 2 + 4.0)), hbv)   # soft min: hill under the 18 deg cone above the road
    spur_info = None
    for rs_ in roads:
        if rs_.get('climb_to_m') is None:
            continue
        fp_ = resample([tuple(p) for p in rs_['points']], 0.5)
        fL = np.concatenate([[0], np.cumsum(np.hypot(np.diff([p[0] for p in fp_]), np.diff([p[1] for p in fp_])))])
        kJ = int(np.argmin([math.hypot(p[0] - fp_[0][0], p[1] - fp_[0][1]) for p in sp_pts]))
        z0 = float(sp_z[kJ])
        fz = np.minimum(z0 + 0.118 * fL, float(rs_['climb_to_m']))
        stw_ = np.zeros((H, W), bool)
        zw_ = np.zeros((H, W), np.float32)
        for p, z in zip(fp_, fz):
            stw_[int(p[1]), int(p[0])] = True
            zw_[int(p[1]), int(p[0])] = z
        pk = rs_.get('pocket')
        pk_h = min(float(pk['height_m']), z0 + 0.118 * float(fL[-1])) if pk else None   # pocket = the end of the climb
        if pk:
            pm_ = poly_mask(pk['poly'], xs, ys)
            stw_ |= pm_
            zw_[pm_] = pk_h
        dsp = ndimage.distance_transform_edt(~stw_)
        cap_s = np.full((H, W), 1e4, np.float32)
        flo_s = np.full((H, W), -1e4, np.float32)
        hw_s = rs_['width_m'] / 2 + 4.6                                       # = the spur's flat bench (corridor) half width
        samp = [(p, z) for p, z in zip(fp_[::4], fz[::4])]
        if pk:
            samp += [(tuple(q), pk_h) for q in pk['poly']] + [(tuple(pk['centre']), pk_h)]
        for (px_, py_), z in samp:
            y0, y1 = max(0, int(py_) - 60), min(H, int(py_) + 61)
            x0, x1 = max(0, int(px_) - 60), min(W, int(px_) + 61)
            dd = np.maximum(0, np.hypot(xs[y0:y1, x0:x1] - px_, ys[y0:y1, x0:x1] - py_) - hw_s)
            np.minimum(cap_s[y0:y1, x0:x1], z + 0.4 + math.tan(math.radians(22.0)) * dd + 300 * sm((dd - 45.0) / 12.0), out=cap_s[y0:y1, x0:x1])
            np.maximum(flo_s[y0:y1, x0:x1], z - 0.4 - math.tan(math.radians(24.0)) * dd - 300 * sm((dd - 45.0) / 12.0), out=flo_s[y0:y1, x0:x1])
        w_fl = sm(1 - dsp / 38.0)
        hbv = np.where(dsp < 120, 0.5 * (hbv + cap_s - np.sqrt((hbv - cap_s) ** 2 + 3.0)), hbv)
        hbv = np.where(w_fl > 0, hbv + (0.5 * (hbv + flo_s + np.sqrt((hbv - flo_s) ** 2 + 3.0)) - hbv) * w_fl, hbv)
        spur_info = {'id': rs_['id'], 'z_join_provisional_m': round(z0, 2)}
    k = np.clip((hbv - GROUND) / 2.0, 0, 1)
    h = np.where(land, h + (np.maximum(h, hbv) - h) * k, h)
    relief_log.append({'id': 'HILL_B', 'kind': 'hill', 'crest': hb['crest'], 'half_width_m': 110, 'height_m': 50.0,
                       'role_ru': 'холм B 50 м: барьер между Неблагополучным и Даунтауном, тоннель; перевал VIEW B вырезан только под серпантин (склоны <= 22°)'})
    snap('hill_B', h)
    # ---- Elite hill: plateau plane (+40 S .. +44 N) inside the fence; natural flanks outside (gentle to the city, rocky to the sea)
    el = F['elite']
    ex, ey = el['centre']
    pz = next(z for z in Dd['elite']['zones'] if z['kind'] == 'plateau')
    hf = pz['height_field']
    a_ = hf['abs_m']
    u, v = (xs - hf['centre'][0]) / hf['half_size_m'][0], (ys - hf['centre'][1]) / hf['half_size_m'][1]
    plateau = a_['C'] + u * (a_['E'] - a_['W']) / 2 + v * (a_['N'] - a_['S']) / 2 + 0.4 * fbm(xs, ys, 18, 2, 9)
    fence_m = poly_mask(pz['poly'], xs, ys)
    d_f, (iy_f, ix_f) = ndimage.distance_transform_edt(~fence_m, return_indices=True)
    edge_h = plateau[iy_f, ix_f]
    th = np.degrees(np.arctan2(ys - ey, xs - ex))                           # 0 = east, 90 = north
    L_n = np.interp(th, [-180, -135, -90, -45, 0, 45, 90, 135, 180], [80, 66, 58, 50, 46, 46, 44, 66, 80])   # W 80 / S 58 / E 46 / N 44
    L_n = L_n * (1 + 0.14 * fbm(xs, ys, 35, 2, 41))
    bvt = next((r_ for r_ in roads if r_['kind'] == 'sand_track'), None)
    d_bvt = dist_pl(bvt['points'], xs, ys, 120) if bvt else np.full((H, W), 120.0, np.float32)
    L_n = np.clip(L_n, 24.0, np.maximum(24.0, d_f + np.minimum(d_sea + 4.0, d_bvt - 7.0)))   # foot reaches the ground at the coast / track
    t_ = np.clip(d_f / L_n, 0, 1)
    flank = GROUND + (edge_h - GROUND) * (1 - sm(t_) ** 0.8) ** 1.15        # convex rim, concave foot
    elite = np.where(fence_m, plateau, flank)
    k = np.where(fence_m, 1.0, np.clip((flank - GROUND) / 2.0, 0, 1)) * (d_f < 110)
    h = np.where(land | fence_m, h + (np.maximum(h, elite) - h) * k, h)
    for z in Dd['elite']['zones']:                                      # villa terraces: flat at their absolute height
        if z['kind'] == 'villa_plot' and z.get('terrace_abs_m') is not None:
            m = poly_mask(z['poly'], xs, ys)
            w_ = sm(1 - ndimage.distance_transform_edt(~m) / 6.0) * fence_m
            h = h * (1 - w_) + z['terrace_abs_m'] * w_
    relief_log.append({'id': 'ELITE', 'kind': 'hill', 'crest': [[ex - 40, ey], [ex + 40, ey]], 'half_width_m': 120, 'height_m': 44.0,
                       'role_ru': 'Элитный холм 44 м: неровное плато +40..+44 за забором, террасы вилл; склоны пологие к городу, скалистые к морю'})
    snap('elite', h)
    # ---- Construction hill +8 m: site pad, ramp from the gate; wide uneven rings, gentle to the road / gate, steeper behind (F)
    ch = F['construction_hill']
    site = poly_mask(ch['site'], xs, ys)
    d_out = ndimage.distance_transform_edt(~site)
    base_c = float(np.median(h[site]))
    pad_c = base_c + ch['rel_m']
    gx, gy = ch['gate']
    d_gate = np.hypot(xs - gx, ys - gy)
    ramp = sm((d_gate - 6.0) / 70.0)
    site_h = pad_c - (ch['rel_m'] - 3.0) * (1 - ramp)
    scx, scy = np.mean(np.array(ch['site'], float), axis=0)
    ang = np.degrees(np.arctan2(ys - scy, xs - scx))
    Lr = np.interp(ang, [-180, -135, -90, -45, 0, 45, 90, 135, 180], [40, 52, 60, 52, 44, 46, 46, 42, 40])  # S (road, gate) gentlest, W (gorge) shorter
    Lr = Lr * (1 + 0.28 * fbm(xs, ys, 60, 2, 51))
    hill = np.where(site, site_h, site_h - (site_h - h) * sm(d_out / Lr))
    k = np.where(site, 1.0, sm(1 - d_out / Lr))
    h = np.where(land, h * (1 - k) + np.maximum(hill, h) * k, h)
    relief_log.append({'id': 'CONSTRUCTION', 'kind': 'hill', 'crest': [[scx - 30, scy], [scx + 30, scy]], 'half_width_m': 110, 'height_m': ch['rel_m'],
                       'role_ru': 'холм Стройки +8 м: площадка видна издалека; склоны 40-60 м, пологие к дороге и воротам, без «торта»'})
    snap('construction_hill', h)
    # ---- river: one water profile (surface per axis point); soft gorge shoulders where the ground is lower than surface + D
    riv = next(b for b in water if b['id'] == 'river')
    axis, widths = clean_axis(riv['axis'], riv['width_m'])
    seg = np.hypot(np.diff([p[0] for p in axis]), np.diff([p[1] for p in axis]))
    S = np.concatenate([[0], np.cumsum(seg)])
    ctrl = []
    for key, pt, z in RIVER_CTRL:
        i = len(axis) - 1 if pt is None else int(np.argmin([math.hypot(p[0] - pt[0], p[1] - pt[1]) for p in axis]))
        ctrl.append((key, i, float(S[i]), z))
    ctrl.sort(key=lambda t: t[2])
    keys = {k_: (i, s_) for k_, i, s_, _ in ctrl}
    surf = np.interp(S, [t[2] for t in ctrl], [t[3] for t in ctrl])
    surf[keys['fall_lip'][0] + 1:keys['fall_base'][0]] = np.interp(S[keys['fall_lip'][0] + 1:keys['fall_base'][0]],
                                                                    [S[keys['fall_lip'][0]], S[keys['fall_base'][0]]], [29.3, POOL_SURF])
    RC = ['brook', 'waterfall', 'pool', 'stream', 'river', 'gorge_rocks']
    rc = np.full(len(axis), 4, np.int8)
    rc[:keys['fall_lip'][0] + 1] = 0
    rc[keys['fall_lip'][0] + 1:keys['fall_base'][0]] = 1
    rc[keys['fall_base'][0]:keys['pool_exit'][0] + 1] = 2
    rc[keys['pool_exit'][0] + 1:keys['land_bridge_2'][0]] = 3
    rc[keys['rocks_in'][0]:] = 5
    reach = np.array([RC[k_] for k_ in rc], object)
    Dg = np.array([2.0, 4.0, 4.0, 4.5, 4.8, 4.0])[rc]
    slope_s = np.array([1.0, 1.0, 0.5, 0.11, 0.06, 0.25])[rc]
    slope_s = np.where((S > keys['bend'][1]) & (rc == 4), 0.07, slope_s)
    Dg = smooth_s(Dg, S, 30.0)                                               # no steps between reaches (one-row ridges)
    slope_s = np.exp(smooth_s(np.log(slope_s), S, 40.0))
    bed = surf - WATER_DEPTH
    rim = surf + Dg
    hw_bed = np.asarray(widths, float) / 2 + 0.6
    run_w = np.maximum(np.where(reach == 'brook', 1.6, 3.0), 0.85 * (rim - bed))
    # axis raster with station index -> per-cell parameters of the nearest axis point
    st = np.zeros((H, W), bool)
    sst = np.zeros((H, W), np.float32)
    for i in range(len(axis) - 1):
        n_ = max(2, int(seg[i] / 0.3))
        for t in np.linspace(0, 1, n_, endpoint=False):
            ix_, iy_ = int(axis[i][0] + (axis[i + 1][0] - axis[i][0]) * t), int(axis[i][1] + (axis[i + 1][1] - axis[i][1]) * t)
            if 0 <= ix_ < W and 0 <= iy_ < H:
                st[iy_, ix_] = True
                sst[iy_, ix_] = S[i] + seg[i] * t
    d_riv, (iy_r, ix_r) = ndimage.distance_transform_edt(~st, return_indices=True)
    s_c = ndimage.gaussian_filter(sst[iy_r, ix_r], 1.5)
    ni = np.clip(np.searchsorted(S, s_c), 0, len(axis) - 1)
    gnoise = fbm(xs, ys, 26, 2, 71)
    hb_c = np.interp(s_c, S, hw_bed) * (1 + 0.12 * gnoise)
    run_c = np.interp(s_c, S, run_w) * (1 + 0.32 * gnoise)
    bed_c = np.interp(s_c, S, bed)
    d_rim = hb_c + run_c
    # shoulder target = upper envelope of cones from stations every 2 m (continuous; nearest-station fields fold at river bends)
    Sst = np.arange(S[keys['fall_base'][0]], S[-1], 2.0)
    pst = np.array([np.interp(Sst, S, [p[0] for p in axis]), np.interp(Sst, S, [p[1] for p in axis])]).T
    target = np.full((H, W), -50.0, np.float32)
    Rst = np.interp(Sst, S, rim)
    slst = np.interp(Sst, S, slope_s)
    drst = np.interp(Sst, S, hw_bed + run_w)
    for (px, py), Rk, slk, drk in zip(pst, Rst, slst, drst):
        rad = drk + max(0.0, Rk - 2.0) / slk
        y0, y1 = max(0, int(py - rad)), min(H, int(py + rad) + 1)
        x0, x1 = max(0, int(px - rad)), min(W, int(px + rad) + 1)
        dd = np.hypot(xs[y0:y1, x0:x1] - px, ys[y0:y1, x0:x1] - py)
        np.maximum(target[y0:y1, x0:x1], Rk - slk * np.maximum(0, dd - drk), out=target[y0:y1, x0:x1])
    target = target + 0.9 * fbm(xs, ys, 45, 2, 72) * (target > 0)
    bridge = np.zeros((H, W), bool)
    br_e = np.full((H, W), 9.0, np.float32)
    for lb_ in F['land_bridges']:
        e = np.sqrt(((xs - lb_['centre'][0]) / lb_['rx_m']) ** 2 + ((ys - lb_['centre'][1]) / lb_['ry_m']) ** 2)
        br_e = np.minimum(br_e, e)
        bridge |= e < 1
    shoulder_on = land & (target > h - 3.0)
    w_sea = sm((d_sea - 6.0) / 30.0) * (1 - ndimage.gaussian_filter(sand.astype(np.float32), 3.0))
    h = np.where(shoulder_on, h + (smax(h, target, 1.2) - h) * w_sea, h)
    snap('gorge_shoulder', h)
    # ---- district pads (flat), edges inside a 21 deg cone (B); Downtown v37 interface
    global KEEP_OUT
    KEEP_OUT = np.clip(np.maximum.reduce([sm(1 - ndimage.distance_transform_edt(~mt) / 8.0), sm(1 - ndimage.distance_transform_edt(~rock) / 6.0),
                                          fence_m.astype(np.float32), hill_body, sm(h_ne / 4.0), sm(h_r2 / 4.0),
                                          sm((flank - GROUND - 2.0) / 6.0) * (d_f < 110), 1 - sm((d_sea - 6.0) / 16.0)]), 0, 1).astype(np.float32)
    pads = {}
    padmask = np.zeros((H, W), bool)

    def pad(name, poly, hh, blend=40.0, inner=0.0, bmax=130.0):
        nonlocal h, padmask
        m = poly_mask(poly, xs, ys)
        if inner > 0:
            m = ndimage.binary_dilation(m, iterations=int(inner))
        hp = float(np.median(h[m])) if hh is None else float(hh)
        bl = flatten(h, m, hp, blend, bmax, angle=19.0, round_m=blend)
        padmask |= m
        pads[name] = {'poly': [list(map(float, p)) for p in poly], 'height_m': round(hp, 2), 'blend_m': round(bl, 1)}
        return m

    if dt37 and dt37.get('pad_poly'):
        pad('downtown', dt37['pad_poly'], float(dt37.get('pad_height_m') or 5.0), 40.0, 3)
    else:
        for z in Dd['downtown']['zones']:
            if z['kind'] == 'ground':
                pad('downtown' if z['id'] == '05-ground' else 'downtown_' + z['id'][-3:], z['poly'], 5.0, 40.0, 3)
    rg = next(z for z in Dd['rough']['zones'] if z['kind'] == 'ground')
    pad('rough', rg['poly'], 5.0, 40.0, 3)
    if fl is not None:
        rx0, rx1 = min(p[0] for p in rg['poly']), max(p[0] for p in rg['poly'])
        ry1 = max(p[1] for p in rg['poly'])
        top = [(x, float(np.interp(x, fl[:, 0], fl[:, 1])) - 0.8) for x in np.arange(rx0, rx1 + 0.1, 4.0)]
        strip = [(rx0, ry1 - 2.0)] + top + [(rx1, ry1 - 2.0)]
        if max(q[1] for q in top) > ry1 + 1.0:
            pad('rough_north_strip', strip, 5.0, 20.0, 1)
    py_ = next(z for z in Dd['port']['zones'] if z['id'] == '06-yard')
    pad('port', py_['poly'], 2.5, 30.0, 2)
    ty = next((z for z in Dd['tramduro']['zones'] if z['id'] == '10-concrete_yard'), None)
    if ty:
        pad('tramduro_yard', ty['poly'], None, 18.0, 1)
    lab_b = next(b for b in Dd['quiet_valley']['buildings'] if b.get('base') == '5' or 'lab' in b['kind'])
    lb = np.array(lab_b['footprint'])
    lab_poly = [[lb[:, 0].min() - 22, lb[:, 1].min() - 22], [lb[:, 0].max() + 22, lb[:, 1].min() - 22],
                [lb[:, 0].max() + 22, lb[:, 1].max() + 22], [lb[:, 0].min() - 22, lb[:, 1].max() + 22]]
    lm = poly_mask(lab_poly, xs, ys)
    pad('quiet_valley_lab', lab_poly, max(4.8, float(np.median(h[lm]))), 25.0)
    snap('district_pads', h)
    # ---- plots: Hamlet house plots, yards, fields, square, base 2; other districts' building plots (blend from the height difference, G)
    flats = np.zeros((H, W), bool)
    for z in Dd['hamlet']['zones']:
        if z['kind'] in ('yard', 'field', 'plaza', 'loading_pad', 'apron', 'cemetery') and len(z.get('poly') or []) >= 3:
            m = poly_mask(z['poly'], xs, ys)
            if m.sum():
                flatten(h, m, float(np.median(h[m])), 8.0 if z['kind'] == 'yard' else 10.0, 40.0, angle=22.0)
                flats |= m
    for b in Dd['hamlet']['buildings']:
        m = ndimage.binary_dilation(poly_mask(b['footprint'], xs, ys), iterations=3)
        if m.sum():
            flatten(h, m, float(np.median(h[m])), 8.0, 36.0, angle=22.0)
            flats |= m
    base2 = [(238.0, 502.0), (253.0, 502.0), (253.0, 528.0), (238.0, 528.0)]   # grandpa's yard (base 2): G43 operating shed + paint table
    m = poly_mask(base2, xs, ys) | poly_mask(next(z for z in Dd['hamlet']['zones'] if z['id'] == '02-A-BASE-TURN')['poly'], xs, ys)
    flatten(h, m, float(np.median(h[m])), 10.0, 40.0, angle=20.0)
    flats |= m
    for dn in ('forest', 'quiet_valley', 'beach', 'port', 'tramduro', 'construction', 'rough'):
        for b in Dd[dn]['buildings']:
            if b.get('disabled') or b.get('scope') == 'north_border' and dn != 'rough':
                continue
            m = ndimage.binary_dilation(poly_mask(b['footprint'], xs, ys), iterations=2)
            if m.sum() == 0 or padmask[m].mean() > 0.95:
                continue
            flatten(h, m, float(np.median(h[m])), 6.0, 36.0, angle=22.0)
    snap('plot_flattening', h)
    # ---- gorge channel cut into the ground (bed, steep natural walls), land bridges solid (the river runs under them)
    h_rim = ndimage.gaussian_filter(h, 2.0)
    t_w = (d_riv - hb_c) / run_c
    f_t = np.where(t_w <= 0, 0.0, sm(t_w) ** 0.75)
    carve = bed_c + (np.maximum(h_rim, bed_c) - bed_c) * f_t
    cw = sm((br_e - 1.0) / 0.35) * (d_riv < d_rim + 2)
    gorge = (d_riv < d_rim + 1) & (cw > 0.01)
    h = np.where(gorge, h * (1 - cw) + np.minimum(h, carve) * cw, h)
    # sea fall: the river leaves the rock slot at the coast and drops into a small sea inlet (never onto the beach tip)
    p1, p0 = axis[-1], axis[-4]
    dv = np.array([p1[0] - p0[0], p1[1] - p0[1]])
    dv = dv / (np.linalg.norm(dv) or 1.0)
    fb = (p1[0] + dv[0] * 4.0, p1[1] + dv[1] * 4.0)
    dfb = np.hypot(xs - fb[0], ys - fb[1])
    ahead = (xs - p1[0]) * dv[0] + (ys - p1[1]) * dv[1] > 0.5
    sea_pts = np.argwhere(sea & (np.hypot(xs - fb[0], ys - fb[1]) < 40) & ~ahead)
    dch = np.full((H, W), 99.0, np.float32)
    if len(sea_pts):                                                         # open the inlet to the nearest open sea (short channel)
        j_, i_ = sea_pts[np.argmin(np.hypot(sea_pts[:, 1] + 0.5 - fb[0], sea_pts[:, 0] + 0.5 - fb[1]))]
        dch = polyline_dist([fb, (i_ + 0.5, j_ + 0.5)], xs, ys, 20)
    dfb = np.minimum(dfb, dch + 1.5)
    inlet = ((dfb < 9.0) & ahead) | (dch < 5.0)
    h = np.where(inlet, np.minimum(h, -1.8 + 2.4 * sm((dfb - 4.0) / 5.0)), h)
    sea = sea | (inlet & (dfb < 5.0))
    snap('gorge_channel', h)
    # ---- lakes, pools, pond, swamp (mountain lake / plunge pool at their design levels)
    lakes = []
    water_keep = np.zeros((H, W), bool)
    for b in water:
        if b['kind'] in ('lake', 'pond', 'swamp') and b.get('outline'):
            m = poly_mask(b['outline'], xs, ys)
            if m.sum() == 0:
                continue
            dl = ndimage.distance_transform_edt(~m)
            ring = (dl > 0) & (dl < 4)
            surf_l = float(np.percentile(h[ring], 20)) - 0.25
            if b['id'] == 'mountain_lake':
                surf_l = LAKE_SURF
            elif b['id'] == 'plunge_pool':
                surf_l = POOL_SURF
            inside_d = ndimage.distance_transform_edt(m)
            bed_l = surf_l - b['depth_m'] * sm(inside_d / 6.0)
            h = np.where(m, np.minimum(h, bed_l), h)
            shore = (dl > 0) & (dl < 8)
            if b['id'] == 'plunge_pool':                                       # rock bowl: the waterfall face and the two rocks stay steep
                shore &= (h < surf_l + 4.0)
            h = np.where(shore, np.minimum(h, surf_l + 0.25 + 0.5 * (dl / 8.0) + np.maximum(0, h - surf_l) * sm(dl / 8.0)), h)
            lakes.append({'id': b['id'], 'kind': b['kind'], 'surface_m': round(surf_l, 2)})
            water_keep |= ndimage.binary_dilation(m, iterations=3)
    # piers / jetties are decks over the water, not causeways
    near_sea = ndimage.binary_dilation(sea, iterations=10) & ~(cls == 3)
    for dn in ('beach', 'elite', 'port'):
        for z in Dd[dn]['zones']:
            if z.get('kind') == 'pier' and len(z.get('poly') or []) >= 3:
                m = ndimage.binary_dilation(poly_mask(z['poly'], xs, ys), iterations=1) & near_sea
                h = np.where(m, np.minimum(h, -1.5), h)
    snap('lakes', h)
    # ---- roads: rank order, pinned joins / pads / entries, grade limit, one weighted corridor per road
    sm6 = ndimage.gaussian_filter(h, 6)
    protect = np.zeros((H, W), np.float32)
    protect = np.maximum(protect, sm(1 - ndimage.distance_transform_edt(~ndimage.binary_dilation(fence_m, iterations=2)) / 3.0))
    protect = np.maximum(protect, (gorge & ~bridge & (d_riv < d_rim)).astype(np.float32))
    protect = np.maximum(protect, water_keep.astype(np.float32))
    bldm = np.zeros((H, W), bool)
    for dn, d_ in Dd.items():
        if dn in ('downtown', 'elite'):
            continue
        for b in d_['buildings']:
            if not b.get('disabled') and len(b.get('footprint') or []) >= 3:
                bldm |= poly_mask(b['footprint'], xs, ys)
    protect = np.maximum(protect, sm(1 - ndimage.distance_transform_edt(~ndimage.binary_dilation(bldm, iterations=2)) / 2.0))
    pad_list = [(nm, poly_mask(p_['poly'], xs, ys), p_['height_m']) for nm, p_ in pads.items()]
    tun_ax = [tuple(p) for p in F['tunnel_axis']]
    tpp = resample(tun_ax, 0.5)
    tLL = np.concatenate([[0], np.cumsum(np.hypot(np.diff([p[0] for p in tpp]), np.diff([p[1] for p in tpp])))])
    st_a = np.zeros((H, W), bool)
    st_s = np.zeros((H, W), np.float32)
    for p, l_ in zip(tpp, tLL):
        st_a[int(p[1]), int(p[0])] = True
        st_s[int(p[1]), int(p[0])] = l_
    d_tax, (iya, ixa) = ndimage.distance_transform_edt(~st_a, return_indices=True)
    s_tax = st_s[iya, ixa]
    behind = (d_tax < 22.0) & (s_tax > 1.5) & (s_tax < tLL[-1] - 1.5)        # the hill over the tunnel, between the portal faces
    near_portal_m = np.zeros((H, W), bool)
    for p in (tun_ax[0], tun_ax[-1]):
        near_portal_m |= np.hypot(xs - p[0], ys - p[1]) < 30.0
    report, bridges, done, pins_log = [], [], {}, []
    order = sorted(roads, key=lambda r_: (ROAD_ORDER.index(r_['id']) if r_['id'] in ROAD_ORDER else 100 + KIND_RANK.get(r_['kind'], 5), r_['id']))
    corr = []
    for rd in order:
        if rd['kind'] == 'tunnel':
            continue
        pts = resample([tuple(p) for p in rd['points']], 2.0)
        ix = np.clip([int(p[0]) for p in pts], 0, W - 1)
        iy = np.clip([int(p[1]) for p in pts], 0, H - 1)
        seg_r = np.hypot(np.diff([p[0] for p in pts]), np.diff([p[1] for p in pts]))
        L = np.concatenate([[0], np.cumsum(seg_r)])
        span = None
        if rd.get('bridge'):
            span = (rd['bridge']['from'], rd['bridge']['to'])
            bridges.append({'road': rd['id'], 'from': span[0], 'to': span[1]})
        fixed = {}
        if rd['kind'] == 'stone_serpentine' and rd.get('heights_abs'):
            ha = np.array(rd['heights_abs'], float)
            Ls = np.array(rd['heights_abs_s'], float)
            prof = np.interp(L * (Ls[-1] / max(L[-1], 1e-6)), Ls, ha)
            fixed = {i: prof[i] for i in range(len(prof))}
        else:
            prof = sm6[iy, ix].astype(np.float64)
            if span:                                                         # deck span: abutment to abutment, never down into the gorge
                inb = np.array([c.seg_dist(p, span[0], span[1])[0] < 3.0 for p in pts])
                if inb.any():
                    i0, i1 = int(np.argmax(inb)), len(inb) - 1 - int(np.argmax(inb[::-1]))
                    a0, b0 = max(0, i0 - 3), min(len(prof) - 1, i1 + 3)
                    prof[a0:b0 + 1] = np.interp(L[a0:b0 + 1], [L[a0], L[b0]], [max(prof[a0], prof[a0 - 1] if a0 else prof[a0]), max(prof[b0], prof[min(b0 + 1, len(prof) - 1)])])
            prof = ndimage.uniform_filter1d(prof, 21, mode='nearest')
            prof = np.maximum(prof, 0.9)
            if rd['kind'] == 'bridge':
                a0, b0 = sm6[iy[0], ix[0]], sm6[iy[-1], ix[-1]]
                prof = np.maximum(np.interp(L, [0, L[-1]], [max(a0, 3.0), max(b0, 3.0)]), 3.0)
            # samples inside a pad = pad height (+6 cm): no embankment across the port / Rough / lab yards
            for nm, pm, ph in pad_list:
                inside_ = pm[iy, ix]
                for i in np.nonzero(inside_)[0]:
                    fixed[int(i)] = ph + 0.06
            if rd.get('dt_entry'):
                fixed[len(prof) - 1] = 5.0 + 0.06
            for end in (0, len(prof) - 1):                                     # joins: pin the end to the parent road already profiled
                if end in fixed:
                    continue
                p = pts[end]
                best = None
                for pid, (ppts, pprof) in done.items():
                    dd = np.hypot(ppts[:, 0] - p[0], ppts[:, 1] - p[1])
                    j = int(np.argmin(dd))
                    if dd[j] < 4.5 and (best is None or dd[j] < best[0]):
                        best = (float(dd[j]), pid, float(pprof[j]))
                if best:
                    fixed[end] = best[2]
                    pins_log.append({'road': rd['id'], 'end': 'start' if end == 0 else 'end', 'parent': best[1], 'h_m': round(best[2], 2), 'gap_m': round(best[0], 2)})
            for i, z in fixed.items():
                prof[i] = z
            if rd.get('climb_to_m') is not None:
                prof = np.minimum(prof[0] + 0.118 * L, float(rd['climb_to_m']))
                fixed = {i: prof[i] for i in range(len(prof))}
            g = rd.get('max_grade', 0.08)
            for _ in range(6):
                for i in range(1, len(prof)):
                    if i not in fixed:
                        prof[i] = np.clip(prof[i], prof[i - 1] - g * seg_r[i - 1], prof[i - 1] + g * seg_r[i - 1])
                for i in range(len(prof) - 2, -1, -1):
                    if i not in fixed:
                        prof[i] = np.clip(prof[i], prof[i + 1] - g * seg_r[i], prof[i + 1] + g * seg_r[i])
        done[rd['id']] = (np.array(pts, float), prof.copy())
        grade = np.abs(np.diff(prof)) / np.maximum(seg_r, 1e-3)
        report.append({'id': rd['id'], 'max_grade_pct': round(float(np.percentile(grade, 98)) * 100, 1), 'max_grade_abs_pct': round(float(grade.max()) * 100, 1),
                       'length_m': round(float(seg_r.sum()), 1)})
        rd['heights'] = [round(float(v), 2) for v in prof]
        rd['heights_step_m'] = 2.0
        if rd['kind'] == 'bridge':
            bridges.append({'road': rd['id'], 'from': rd['points'][0], 'to': rd['points'][-1]})
            continue                                                    # deck over the water: no terrain imprint
        corr.append((rd, pts, L, prof, span))
    # corridors per road CHUNK (~30 m; hairpin legs never share one nearest-line field), combined by weight -> no crease where roads /
    # legs at different heights meet; samples on a pad (= pad height) only shape a short shoulder (the pad already did the rest)
    Wmax = np.zeros((H, W), np.float32)
    acc_w = np.zeros((H, W), np.float32)
    acc_h = np.zeros((H, W), np.float32)
    sinkf = np.zeros((H, W), np.float32)
    serp_pre = sm6.copy()
    padm_all = np.logical_or.reduce([pm for _, pm, _ in pad_list]) if pad_list else np.zeros((H, W), bool)
    bestd = np.full((H, W), 1e9, np.float32)                                 # nearest carriageway: the ground under a road = that road
    besth = np.zeros((H, W), np.float32)
    besthw = np.zeros((H, W), np.float32)
    env_pts = []                                                             # (x, y, z, half width + bench) for the earthwork cones
    for rd, pts, L, prof, span in corr:
        hw = rd['width_m'] / 2
        rk, rcap = ROAD_K.get(rd['kind'], ROAD_K_DEFAULT)
        if rd.get('climb_to_m') is not None:                                  # the VIEW B spur: hill B is already shaped to it (hill_B block)
            rk, rcap = 0.25, 10.0
        finep = resample([tuple(p) for p in rd['points']], 0.5)
        Lf = np.concatenate([[0], np.cumsum(np.hypot(np.diff([p[0] for p in finep]), np.diff([p[1] for p in finep])))])
        zf = np.interp(Lf * (L[-1] / max(Lf[-1], 1e-6)), L, prof)
        keepi = [i for i, p in enumerate(finep) if not (span and c.seg_dist(p, span[0], span[1])[0] < 3.0)]
        if not keepi:
            continue
        if rd['kind'] != 'stone_serpentine' and not rd['id'].startswith('tunnel_'):
            for i in keepi[::6]:
                env_pts.append((finep[i][0], finep[i][1], float(zf[i]), hw + (1.7 if rd['kind'] == 'serpentine' else 0.0)))
        n_ch = max(1, int(round(Lf[-1] / 30.0)))
        bounds = np.linspace(0, Lf[-1], n_ch + 1)
        for ci in range(n_ch):
            sel = [i for i in keepi if bounds[ci] - 2.0 <= Lf[i] <= bounds[ci + 1] + 2.0]
            if not sel:
                continue
            cx_ = np.array([finep[i][0] for i in sel])
            cy_ = np.array([finep[i][1] for i in sel])
            pad_ = int(hw + rcap + 6)
            y0, y1 = max(0, int(cy_.min()) - pad_), min(H, int(cy_.max()) + pad_ + 1)
            x0, x1 = max(0, int(cx_.min()) - pad_), min(W, int(cx_.max()) + pad_ + 1)
            stw = np.zeros((y1 - y0, x1 - x0), bool)
            zw = np.zeros((y1 - y0, x1 - x0), np.float32)
            pw = np.zeros((y1 - y0, x1 - x0), bool)
            for i in sel:
                ixx, iyy = int(finep[i][0]) - x0, int(finep[i][1]) - y0
                if 0 <= ixx < stw.shape[1] and 0 <= iyy < stw.shape[0]:
                    stw[iyy, ixx] = True
                    zw[iyy, ixx] = zf[i]
                    pw[iyy, ixx] = padm_all[int(finep[i][1]), int(finep[i][0])]
            if not stw.any():
                continue
            dist, (iyw, ixw) = ndimage.distance_transform_edt(~stw, return_indices=True)
            rh = zw[iyw, ixw]
            dz = ndimage.maximum_filter(np.abs(sm6[y0:y1, x0:x1] - rh), 5)
            reach_ = hw + 1.0 + np.clip(dz / rk, 4.0, rcap)
            reach_ = np.where(pw[iyw, ixw], np.minimum(reach_, hw + 6.0), reach_)
            if rd['id'].startswith('tunnel_'):                                   # portal mouth: retaining walls, not a 35 m funnel
                reach_ = np.minimum(reach_, hw + 8.0)
            flat = hw + (4.6 if rd.get('climb_to_m') is not None else 3.4 if rd['kind'] == 'serpentine' else 1.7)
            w_ = sm(1 - (dist - flat) / np.maximum(reach_ - flat, 0.5))
            w_ = np.where(dist > reach_, 0.0, w_) * (1 - protect[y0:y1, x0:x1])
            if rd['kind'] == 'stone_serpentine':                              # ledge road: no 70 m cuts into the plateau flank
                w_ = w_ * (1 - fence_m[y0:y1, x0:x1])
            ww = w_ ** 2 + 1e-9 * (w_ > 0)
            bm = dist < bestd[y0:y1, x0:x1]
            bestd[y0:y1, x0:x1] = np.where(bm, dist, bestd[y0:y1, x0:x1])
            besth[y0:y1, x0:x1] = np.where(bm, rh, besth[y0:y1, x0:x1])
            besthw[y0:y1, x0:x1] = np.where(bm, hw, besthw[y0:y1, x0:x1])
            Wmax[y0:y1, x0:x1] = np.maximum(Wmax[y0:y1, x0:x1], w_)
            acc_w[y0:y1, x0:x1] += ww
            acc_h[y0:y1, x0:x1] += ww * rh
            if rd['kind'] not in ('dirt', 'sand_track'):
                sinkf[y0:y1, x0:x1] = np.maximum(sinkf[y0:y1, x0:x1], np.where(dist < hw + 0.7, 0.10, 0.0))
    for rd, pts, L, prof, span in corr:
        pk = rd.get('pocket')
        if not pk:
            continue
        pm_ = poly_mask(pk['poly'], xs, ys)
        sl_ = bbox_slice(pm_, 24)
        dist = ndimage.distance_transform_edt(~pm_[sl_])
        zpk = min(float(pk['height_m']), float(prof[-1]))                     # flat turnaround at the end of the climb
        dz = ndimage.maximum_filter(np.abs(sm6[sl_] - zpk), 5)
        reach_ = 1.0 + np.clip(dz / 0.25, 2.0, 6.0)
        w_ = sm(1 - (dist - 1.0) / np.maximum(reach_ - 1.0, 0.5)) * (dist <= reach_)
        ww = w_ ** 2 + 1e-9 * (w_ > 0)
        bm = dist < bestd[sl_]
        bestd[sl_] = np.where(bm, dist, bestd[sl_])
        besth[sl_] = np.where(bm, zpk, besth[sl_])
        besthw[sl_] = np.where(bm, 0.0, besthw[sl_])
        Wmax[sl_] = np.maximum(Wmax[sl_], w_)
        acc_w[sl_] += ww
        acc_h[sl_] += ww * zpk
        for q in pk['poly'][::2]:
            env_pts.append((q[0], q[1], zpk, 0.0))
    Hr = np.where(acc_w > 0, acc_h / np.maximum(acc_w, 1e-9), h)
    Hr = np.where(Wmax > 0, ndimage.gaussian_filter(Hr, 1.2), Hr)            # no comb of nearest-sample steps
    on_road = sm(1 - (bestd - besthw - 0.3) / 1.2)                            # carriageway + 0.3 m: exactly its own road (-10 cm)
    Hr = Hr * (1 - on_road) + besth * on_road
    h = h * (1 - Wmax) + (Hr - sinkf) * Wmax
    # earthworks: lower / upper envelope of cones round every road sample (continuous, no seam between hairpin legs): within 60 m of a
    # road the ground stays inside road +- (1 m + tan 23 deg * distance past the shoulder); not on mountains / rocks / coast / Elite flank
    t23 = math.tan(math.radians(23.0))
    cone_up = np.full((H, W), 1e4, np.float32)
    cone_dn = np.full((H, W), -1e4, np.float32)
    dcn = np.full((H, W), 1e4, np.float32)
    R_ = 62                                                                  # each road's cone is local: it fades out 40-55 m from the road
    for px, py, pz, hwp in env_pts:
        y0, y1 = max(0, int(py) - R_), min(H, int(py) + R_ + 1)
        x0, x1 = max(0, int(px) - R_), min(W, int(px) + R_ + 1)
        dd = np.hypot(xs[y0:y1, x0:x1] - px, ys[y0:y1, x0:x1] - py)
        run_ = np.maximum(0, dd - hwp - 2.0)
        np.minimum(cone_up[y0:y1, x0:x1], pz + 1.0 + t23 * run_ + 300.0 * sm((run_ - 30.0) / 14.0), out=cone_up[y0:y1, x0:x1])   # cut banks: near zone
        np.maximum(cone_dn[y0:y1, x0:x1], pz - 1.0 - t23 * run_ - 300.0 * sm((run_ - 10.0) / 12.0), out=cone_dn[y0:y1, x0:x1])   # fills: close to the road
        np.minimum(dcn[y0:y1, x0:x1], dd, out=dcn[y0:y1, x0:x1])
    keep_cone = np.clip(np.maximum.reduce([sm(1 - ndimage.distance_transform_edt(~mt) / 8.0), sm(1 - ndimage.distance_transform_edt(~rock) / 6.0),
                                            1 - sm((d_sea - 4.0) / 12.0), sm((flank - GROUND - 2.0) / 6.0) * (d_f < 110)]), 0, 1)
    corr_zone = ndimage.gaussian_filter(ndimage.binary_dilation(Wmax > 0.02, iterations=10).astype(np.float32), 4.0)   # only where a corridor works
    tun_p = [tuple(p) for p in F['tunnel_axis']]
    near_portal = np.zeros((H, W), np.float32)
    for p in (tun_p[0], tun_p[-1]):                                         # portals and their mouths keep their own shape
        near_portal = np.maximum(near_portal, sm(1 - (np.hypot(xs - p[0], ys - p[1]) - 30.0) / 15.0))
    on_cw = sm(1 - (bestd - besthw - 0.5) / 1.5)
    wcone = corr_zone * sm(1 - (dcn - 60.0) / 50.0) * (1 - protect) * (1 - near_portal) * (1 - on_cw) * land * (1 - fence_m) * (1 - keep_cone)
    hc = 0.5 * (h + cone_up - np.sqrt((h - cone_up) ** 2 + 1.0))
    hc = 0.5 * (hc + cone_dn + np.sqrt((hc - cone_dn) ** 2 + 1.0))
    h = np.where(wcone > 0, h + (hc - h) * wcone, h)
    # hill B: soften the creases where the earthwork cones meet the natural hill (never on a carriageway or a pad)
    w_sm = ndimage.gaussian_filter(hill_body.astype(np.float32), 3.0) * (1 - ndimage.gaussian_filter((Wmax > 0.6).astype(np.float32), 2.0)) *         (1 - ndimage.binary_dilation(padmask, iterations=2)) * (1 - protect)
    h = h + (ndimage.gaussian_filter(h, 3.0) - h) * np.clip(w_sm, 0, 1)
    snap('road_imprint', h, rh=Hr, road_w=Wmax, pre_road=sm6)
    # VIEW B: low berm 1-1.5 m on the OUTER (downhill) side of the serpentine only (v10 §3.2), view stays open
    berm = np.zeros((H, W), np.float32)
    bpts = []
    for brd in [r_ for r_ in roads if r_.get('berm') and r_['kind'] != 'tunnel']:
        bpts += berm_points(brd, serp_pre, vb, F, bestd_other(roads, brd['id'], xs, ys))
    if bpts:
        stb = np.zeros((H, W), bool)
        for p in bpts:
            stb[int(p[1]), int(p[0])] = True
        stb = ndimage.binary_dilation(stb, iterations=1)
        db = ndimage.distance_transform_edt(~stb)
        berm = 1.0 * sm(1 - db / 1.4)
        onr = np.full((H, W), 99.0, np.float32)
        for brd in [r_ for r_ in roads if r_.get('berm')]:
            onr = np.minimum(onr, dist_pl(brd['points'], xs, ys, 12) - brd['width_m'] / 2)
        berm = np.where(onr < 1.0, 0.0, berm)
        berm = berm * sm((bestd_other_multi(roads, [r_['id'] for r_ in roads if r_.get('berm')], xs, ys) - 6.0) / 8.0)
        h = h + berm.astype(np.float32)
    snap('serp_berm', h)
    # ---- Hamlet streets: gentle along-profile (<= 8 % main, <= 10 % local), pinned to the bypass / other streets, flat cross-section
    street_log = hamlet_streets(h, Dd['hamlet'], done, xs, ys)
    snap('hamlet_streets', h)
    # ---- Elite plateau + villa terraces re-applied after the roads (the corridors never reach into the fence)
    h = np.where(fence_m, plateau, h)
    for z in Dd['elite']['zones']:
        if z['kind'] == 'villa_plot' and z.get('terrace_abs_m') is not None:
            m = poly_mask(z['poly'], xs, ys)
            w_ = sm(1 - ndimage.distance_transform_edt(~m) / 6.0) * fence_m
            h = h * (1 - w_) + z['terrace_abs_m'] * w_
    gz = next((z for z in Dd['elite']['zones'] if z['kind'] == 'gate_trap'), None)
    if gz:
        gm = np.hypot(xs - gz['pos'][0], ys - gz['pos'][1]) < 6.0
        ko, KEEP_OUT = KEEP_OUT, None
        flatten(h, gm, float(gz.get('abs_height_m', 44.0)), 6.0, 14.0, angle=20.0, round_m=4.0)
        for b in Dd['elite']['buildings']:
            if b['kind'] == 'guard_booth' and b.get('base_abs_m') is not None:
                flatten(h, ndimage.binary_dilation(poly_mask(b['footprint'], xs, ys), iterations=2), float(b['base_abs_m']), 4.0, 14.0, angle=26.0, round_m=3.0)
        KEEP_OUT = ko
    snap('elite_terraces', h)
    # ---- tunnel: holes at the portals
    tun = [tuple(p) for p in F['tunnel_axis']]
    za = float(h[int(tun[0][1]), int(tun[0][0])])
    zb = float(h[int(tun[-1][1]), int(tun[-1][0])])
    d = dist_pl(tun, xs, ys, 30)
    # portal cover: from each portal 0..40 m into the hill the ground stays >= road + 5.5 m clearance + 3 m cover (A3 22.10: the
    # v37 city pushed the south portal 74 m up the axis, the hill must cover it ~25 m beyond the pad); sideways it falls off over 12 m
    tp = resample(tun, 1.0)
    tL = np.concatenate([[0], np.cumsum(np.hypot(np.diff([p[0] for p in tp]), np.diff([p[1] for p in tp])))])
    stt = np.zeros((H, W), bool)
    sst_t = np.zeros((H, W), np.float32)
    for p, l_ in zip(tp, tL):
        stt[int(p[1]), int(p[0])] = True
        sst_t[int(p[1]), int(p[0])] = l_
    dtn, (iyt, ixt) = ndimage.distance_transform_edt(~stt, return_indices=True)
    st_n = sst_t[iyt, ixt]
    z_ax = za + (zb - za) * st_n / max(tL[-1], 1.0)
    from_portal = np.minimum(st_n, tL[-1] - st_n)
    need = z_ax + 8.5
    w_c = sm(1 - (dtn - 6.0) / 12.0) * sm(1 - (from_portal - 40.0) / 20.0) * (from_portal > 0.5)
    for p in (tun[0], tun[-1]):
        ahead = np.hypot(xs - p[0], ys - p[1]) < 3.0
        w_c = np.where(ahead, 0.0, w_c)
    h = np.where(w_c > 0, np.maximum(h, h + (need - h) * w_c * (need > h)), h)
    holes = np.zeros((H, W), bool)
    for p, z in ((tun[0], za), (tun[-1], zb)):
        nearp = np.hypot(xs - p[0], ys - p[1]) < 14
        holes |= nearp & (d < 4.0) & (h > z + 1.5)
    cover = float(np.min([h[int(p[1]), int(p[0])] - (za + (zb - za) * i / (len(tun) - 1)) for i, p in enumerate(tun)][1:-1]))
    snap('tunnel', h)
    # ---- van traps: closed land depressions are capped at 0.8 m deep (soft), water / gorge / designed dips / holes exempt
    keep = water_keep | ndimage.binary_dilation((d_riv < d_rim + 2) & ~bridge, iterations=2) | sea | holes
    filled = priority_flood(h, sea | (xs < 1) | (xs > W - 2) | (ys < 1) | (ys > H - 2))
    depth_ = filled - h
    raise_ = np.where((depth_ > 0.8) & ~keep & land, depth_ - 0.8, 0.0)
    n_trap = int(ndimage.label(raise_ > 0)[1])
    hn = h + raise_
    rz = ndimage.binary_dilation(raise_ > 0, iterations=3) & ~keep
    h = np.where(rz, np.maximum(ndimage.gaussian_filter(hn, 1.0), filled - 0.85), hn).astype(np.float32)
    h = np.where(keep, hn, h)
    snap('trap_fill', h)
    # ---- north strip: smooth along x for the seam with the far-steppe backdrop terrain (no T-junction cracks)
    hs = ndimage.gaussian_filter1d(h, 5.0, axis=1)
    wn = sm((ys - 930.0) / 16.0)
    h = (h * (1 - wn) + hs * wn).astype(np.float32)
    snap('seam', h)
    # ---- export
    np.save(os.path.join(WORK, 'height_1m.npy'), h)
    os.makedirs(OUT, exist_ok=True)
    zz = np.clip((h - BASE_Y) / HEIGHT_RANGE, 0, 1)
    from scipy.ndimage import map_coordinates
    gxw = np.linspace(0, W, RES) - 0.5                                       # RAW vertex i at world x = i W / (RES - 1); cell centre = index + 0.5
    gyw = np.linspace(0, H, RES) - 0.5
    GX, GY = np.meshgrid(np.clip(gxw, 0, W - 1), np.clip(gyw, 0, H - 1))
    hr = map_coordinates(zz, [GY, GX], order=1)
    hr = seam_linear(hr, 8)
    raw = (hr * 65535).round().astype('<u2')
    raw.tofile(os.path.join(OUT, 'Heightmap_v85_2049_r16.bytes'))
    hm = map_coordinates(holes.astype(np.float32), [np.clip(np.linspace(0, H, RES - 1) - 0.5, 0, H - 1)[:, None] * np.ones((1, RES - 1)),
                                                    np.ones((RES - 1, 1)) * np.clip(np.linspace(0, W, RES - 1) - 0.5, 0, W - 1)[None, :]], order=0)
    np.packbits((hm < 0.5).astype(np.uint8)).tofile(os.path.join(OUT, 'Holes_v85_2048_bits.bytes'))
    gy_, gx_ = np.gradient(h)
    slope = np.degrees(np.arctan(np.hypot(gx_, gy_)))
    # water data: levels, waterfalls, underground spans (land bridges)
    wf, river_out = water_out(axis, widths, S, surf, bed, reach, keys, F, cls, h, water, sea)
    lk = {l_['id']: l_['surface_m'] for l_ in lakes}
    river_out = [({**b, 'surface_m': lk[b['id']]} if b.get('id') in lk and 'surface_m' not in b else b) for b in river_out]
    fit = ground_fit(h, Dd, xs, ys)
    back = steppe_backdrop(raw, h)
    river_check = river_depth_check(h, axis, surf, reach, br_e, xs, ys)
    save_json('terrain_v85.json', {
        'heightmap': 'Heightmap_v85_2049_r16.bytes', 'format': 'RAW 16-bit LE, %d x %d, row 0 = south (world y 0), column 0 = west; vertex i at world '
                                                              'x = i * %g / %d (W86: sampled at the real vertex positions)' % (RES, RES, W, RES - 1),
        'holes': 'Holes_v85_2048_bits.bytes (packbits, 1 = solid, 2048 x 2048, row 0 = south)',
        'size_m': [W, HEIGHT_RANGE, H], 'position_m': [0, BASE_Y, 0], 'sea_level_m': 0.0, 'ground_m': GROUND,
        'pads': pads, 'construction_pad_m': round(pad_c, 2), 'tunnel': {'axis': [list(p) for p in tun], 'portal_heights_m': [round(za, 2), round(zb, 2)],
                                                                       'clear_height_m': 5.5, 'width_m': 9.0, 'min_cover_m': round(cover, 1)},
        'road_grades': report, 'road_pins': pins_log, 'hamlet_streets': street_log, 'bridges': bridges, 'lakes': lakes,
        'river': {'profile': 'water_v85.json river.surface_m (per axis point); bed = surface - %.1f m' % WATER_DEPTH,
                  'surface_m_range': [round(float(surf.min()), 2), round(float(surf.max()), 2)], 'gorge_rim_above_surface_m': [4.0, 4.8],
                  'depth_check': river_check},
        'waterfalls': wf, 'relief': relief_log, 'traps_capped': n_trap, 'ground_fit': fit, 'steppe_backdrop': back,
        'downtown_v37_land': dt37['path'] if dt37 else None,
        'peaks_m': {'hill_B': round(float(h[(ys > 540) & (ys < 640) & (xs > 750) & (xs < 1150)].max()), 1), 'elite': round(float(h[fence_m].max()), 1),
                    'nw_ridge': round(float(h[xs < 560].max()), 1), 'right_ridge': round(float(h[(xs > 1020) & (xs < 1110) & (ys > 870)].max()), 1),
                    'ne_ridge': round(float(h[(d_ne < 6)].max()), 1),
                    'view_B_road': round(float(max(serp['heights'])), 1), 'view_B_hill_within_80m': round(float(h[np.hypot(xs - vb[0], ys - vb[1]) < 80].max()), 1),
                    'view_B_pocket': round(float(h[int(F['view_B_pocket']['centre'][1]), int(F['view_B_pocket']['centre'][0])]), 1) if F.get('view_B_pocket') else None,
                    'view_B_spur_top_road': round(float(max(next((r_['heights'] for r_ in roads if r_.get('climb_to_m') is not None), [0]))), 1)},
        'land_slope_deg_p99': round(float(np.percentile(slope[land & ~mt & ~rock], 99)), 1)})
    save_json('roads_v85.json', {**roads_doc, 'roads': roads})
    water_doc['bodies'] = river_out
    water_doc['levels_note'] = ('W86 (s03): river.surface_m per axis point (brook 30 -> waterfall 29.3 / 12 -> pool 12 -> stream -> river 5.6 .. 3.2 -> '
                                'waterfall into the sea); waterfall_* carry top / bottom points, lip and base edges, width, drop, material; lakes '
                                'surface_m; underground_spans = land bridges (no water mesh there, rock portals)')
    save_json('water_v85.json', water_doc)
    preview(h, relief_log, F, roads)
    t = load_json('terrain_v85.json')
    print(json.dumps(t['peaks_m']), 'tunnel', t['tunnel']['portal_heights_m'], 'cover', t['tunnel']['min_cover_m'], 'traps capped', n_trap,
          'slope p99', t['land_slope_deg_p99'])
    print('pads', {k_: (v_['height_m'], v_['blend_m']) for k_, v_ in pads.items()})
    print('ground fit > 1.5 m:', fit['over_1_5_m'], fit['worst'][:6])
    print('river depth check:', river_check)
    for r_ in report:
        if r_['max_grade_pct'] > 8.5:
            print('  steep', r_)


def berm_points(rd, pre, vb, F, d_oth=None):
    """berm centre points 1.6 m outside the carriageway on the lower (outer) side; none in hairpins / near VIEW B / at the spur ends /
    where the outer side faces another road (the bank down to it)."""
    spts = resample([tuple(p) for p in rd['points']], 2.0)
    out = []
    pk = rd.get('pocket')
    for i, p in enumerate(spts):
        a, b_ = spts[max(0, i - 1)], spts[min(len(spts) - 1, i + 1)]
        tx_, ty_ = b_[0] - a[0], b_[1] - a[1]
        Ln = math.hypot(tx_, ty_) or 1.0
        nx_, ny_ = -ty_ / Ln, tx_ / Ln
        off = rd['width_m'] / 2 + 1.6
        zl = float(pre[int(np.clip(p[1] + ny_ * 9, 0, H - 1)), int(np.clip(p[0] + nx_ * 9, 0, W - 1))])
        zr = float(pre[int(np.clip(p[1] - ny_ * 9, 0, H - 1)), int(np.clip(p[0] - nx_ * 9, 0, W - 1))])
        side = 1 if zl < zr else -1
        a2, b2 = spts[max(0, i - 4)], spts[min(len(spts) - 1, i + 4)]
        turn = abs(math.degrees(math.atan2(b2[1] - p[1], b2[0] - p[0]) - math.atan2(p[1] - a2[1], p[0] - a2[0])))
        turn = min(turn, 360 - turn)
        if abs(zl - zr) < 0.6 or turn > 35 or (rd['id'] == 'serpentine_view_b' and math.hypot(p[0] - vb[0], p[1] - vb[1]) < 22):
            continue
        if pk and (i * 2.0 < 45.0 or math.hypot(p[0] - pk['centre'][0], p[1] - pk['centre'][1]) < 16.0):
            continue
        if d_oth is not None:
            qx, qy = int(np.clip(p[0] + side * nx_ * 12, 0, W - 1)), int(np.clip(p[1] + side * ny_ * 12, 0, H - 1))
            if d_oth[qy, qx] < 20.0:
                continue
        out.append((p[0] + side * nx_ * off, p[1] + side * ny_ * off))
    return out


def bestd_other_multi(roads, rids, xs, ys):
    d = np.full(xs.shape, 60.0, np.float32)
    for r_ in roads:
        if r_['id'] not in rids and r_['kind'] != 'tunnel':
            d = np.minimum(d, polyline_dist([tuple(p) for p in r_['points']], xs, ys, 60.0))
    return d


def bestd_other(roads, rid, xs, ys):
    """distance to the nearest road other than rid (berm stops before junctions)."""
    d = np.full(xs.shape, 60.0, np.float32)
    for r_ in roads:
        if r_['id'] != rid and r_['kind'] != 'tunnel':
            d = np.minimum(d, polyline_dist([tuple(p) for p in r_['points']], xs, ys, 60.0))
    return d


def smooth_s(v, S, win):
    """moving average of a per-axis-point value over +- win / 2 metres of arc length."""
    Sf = np.arange(S[0], S[-1] + 0.5, 0.5)
    vf = np.interp(Sf, S, v)
    k = max(1, int(win / 0.5))
    vf = ndimage.uniform_filter1d(vf, k, mode='nearest')
    return np.interp(S, Sf, vf)


def clean_axis(axis, widths):
    """drop near-duplicate / backtracking points of the vector river axis (two SVG polylines joined with a 0.6 m zig-zag)."""
    out, wo = [tuple(axis[0])], [widths[0]]
    for p, w_ in zip(axis[1:], widths[1:]):
        q = out[-1]
        if math.hypot(p[0] - q[0], p[1] - q[1]) < 0.9:
            continue
        if len(out) >= 2:
            a = out[-2]
            if (q[0] - a[0]) * (p[0] - q[0]) + (q[1] - a[1]) * (p[1] - q[1]) < 0:
                out[-1] = tuple(p)
                wo[-1] = w_
                continue
        out.append(tuple(p))
        wo.append(w_)
    return out, wo


def seam_linear(hr, k):
    """top RAW rows: piecewise linear between every k-th vertex (the backdrop terrain has 1 vertex per k main vertices)."""
    n = hr.shape[1]
    idx = np.arange(0, n, k)
    for j in range(1, 7):
        row = hr[-j]
        lin = np.interp(np.arange(n), idx, row[idx])
        a = 1.0 if j == 1 else max(0.0, 1.0 - (j - 1) / 6.0)
        hr[-j] = row * (1 - a) + lin * a
    return hr


def hamlet_streets(h, hd, roads_done, xs, ys):
    """Hamlet dirt streets (splat only): profile = ground smoothed along the street, grade <= 8 % (main) / 10 % (local), ends pinned to the
    world road or the street they join; narrow corridor (flat street, banks <= 1:3 within 8 m)."""
    streets = [z for z in hd['zones'] if z['kind'] == 'street' and z.get('line') and len(z['line']) >= 2]
    streets.sort(key=lambda z: (0 if z.get('road_class') == 'village_main' or z.get('width_m', 0) >= 5 else 1, z['id']))
    done = {k: v for k, v in roads_done.items()}
    log = []
    Wm = np.zeros(h.shape, np.float32)
    aw = np.zeros(h.shape, np.float32)
    ah = np.zeros(h.shape, np.float32)
    hs = ndimage.gaussian_filter(h, 2.0)
    for z in streets:
        pts = resample([tuple(p) for p in z['line']], 1.0)
        if len(pts) < 2:
            continue
        seg_ = np.hypot(np.diff([p[0] for p in pts]), np.diff([p[1] for p in pts]))
        ix = np.clip([int(p[0]) for p in pts], 0, W - 1)
        iy = np.clip([int(p[1]) for p in pts], 0, H - 1)
        prof = ndimage.uniform_filter1d(hs[iy, ix].astype(np.float64), min(15, max(3, len(pts) // 2 * 2 - 1)), mode='nearest')
        g = 0.075 if (z.get('width_m') or 0) >= 5 else 0.09
        fixed = {}
        for end in (0, len(pts) - 1):
            p = pts[end]
            best = None
            for pid, (ppts, pprof) in done.items():
                dd = np.hypot(ppts[:, 0] - p[0], ppts[:, 1] - p[1])
                j = int(np.argmin(dd))
                lim = 4.5 if pid in roads_done else 2.5
                if dd[j] < lim and (best is None or dd[j] < best[0]):
                    best = (float(dd[j]), pid, float(pprof[j]))
            if best:
                fixed[end] = best[2]
        for i, v in fixed.items():
            prof[i] = v
        for _ in range(6):
            for i in range(1, len(prof)):
                if i not in fixed:
                    prof[i] = np.clip(prof[i], prof[i - 1] - g * seg_[i - 1], prof[i - 1] + g * seg_[i - 1])
            for i in range(len(prof) - 2, -1, -1):
                if i not in fixed:
                    prof[i] = np.clip(prof[i], prof[i + 1] - g * seg_[i], prof[i + 1] + g * seg_[i])
        done[z['id']] = (np.array(pts, float), prof.copy())
        gr = np.abs(np.diff(prof)) / np.maximum(seg_, 1e-3)
        log.append({'id': z['id'], 'max_grade_pct': round(float(gr.max()) * 100, 1), 'pins': len(fixed)})
        hw = (z.get('width_m') or 4.2) / 2
        pad_ = int(hw + 12)
        P = np.array(pts)
        y0, y1 = max(0, int(P[:, 1].min()) - pad_), min(H, int(P[:, 1].max()) + pad_ + 1)
        x0, x1 = max(0, int(P[:, 0].min()) - pad_), min(W, int(P[:, 0].max()) + pad_ + 1)
        stw = np.zeros((y1 - y0, x1 - x0), bool)
        zw = np.zeros((y1 - y0, x1 - x0), np.float32)
        for p, v in zip(resample(pts, 0.5), np.interp(np.linspace(0, 1, len(resample(pts, 0.5))), np.linspace(0, 1, len(prof)), prof)):
            stw[int(p[1]) - y0, int(p[0]) - x0] = True
            zw[int(p[1]) - y0, int(p[0]) - x0] = v
        dist, (a_, b_) = ndimage.distance_transform_edt(~stw, return_indices=True)
        rh = zw[a_, b_]
        dz = ndimage.maximum_filter(np.abs(h[y0:y1, x0:x1] - rh), 3)
        reach = hw + 1.5 + np.clip(dz / 0.33, 1.0, 9.0)
        flat = hw + 0.3
        w_ = sm(1 - (dist - flat) / np.maximum(reach - flat, 0.5)) * (dist <= reach)
        ww = w_ ** 2 + 1e-9 * (w_ > 0)
        Wm[y0:y1, x0:x1] = np.maximum(Wm[y0:y1, x0:x1], w_)
        aw[y0:y1, x0:x1] += ww
        ah[y0:y1, x0:x1] += ww * rh
    Hs = np.where(aw > 0, ah / np.maximum(aw, 1e-9), h)
    h[:] = h * (1 - Wm) + Hs * Wm
    return log


def water_out(axis, widths, S, surf, bed, reach, keys, F, cls, h, water, sea):
    """water_v85.json bodies with W86 levels: river surface / bed per axis point, reaches, underground spans, cascades; waterfall geometry."""
    bodies = []
    under = []
    inside = np.zeros(len(axis), bool)
    for lb_ in F['land_bridges']:
        e = np.array([math.hypot((p[0] - lb_['centre'][0]) / lb_['rx_m'], (p[1] - lb_['centre'][1]) / lb_['ry_m']) for p in axis])
        inside |= e < 1.05
    i = 0
    while i < len(axis):
        if inside[i]:
            j = i
            while j + 1 < len(axis) and inside[j + 1]:
                j += 1
            under.append([i, j])
            i = j + 1
        else:
            i += 1
    grade = np.concatenate([[0], -np.diff(surf) / np.maximum(np.diff(S), 1e-3)])
    casc = [int(i) for i in range(len(axis)) if reach[i] == 'stream' and grade[i] > 0.06 and i % 4 == 0]
    # waterfalls
    il, ib = keys['fall_lip'][0], keys['fall_base'][0]
    top = axis[il]
    base = axis[ib]
    dvec = (base[0] - top[0], base[1] - top[1])
    Ld = math.hypot(*dvec) or 1.0
    dvec = (dvec[0] / Ld, dvec[1] / Ld)
    nrm = (-dvec[1], dvec[0])
    w_top, w_base = max(3.4, widths[il] + 0.6), max(4.6, widths[il] + 1.8)

    def edge(p, w_, z):
        return [[round(p[0] + nrm[0] * w_ / 2, 2), round(p[1] + nrm[1] * w_ / 2, 2), round(z, 2)],
                [round(p[0] - nrm[0] * w_ / 2, 2), round(p[1] - nrm[1] * w_ / 2, 2), round(z, 2)]]
    mat = 'Working/Reviews/Textures_2026-10-17/own_textures_v01/WaterFX_waterfall_v02_tileY.png'
    wf_m = {'id': 'waterfall_mountain', 'kind': 'waterfall', 'at': [round(base[0], 2), round(base[1], 2)], 'top_m': round(float(surf[il] - surf[ib]), 2),
            'top': [round(top[0], 2), round(top[1], 2), round(float(surf[il]), 2)], 'bottom': [round(base[0], 2), round(base[1], 2), round(float(surf[ib]), 2)],
            'lip_edge': edge(top, w_top, float(surf[il])), 'base_edge': edge(base, w_base, float(surf[ib])), 'width_top_m': round(w_top, 2),
            'width_base_m': round(w_base, 2), 'drop_m': round(float(surf[il] - surf[ib]), 2), 'flow_dir_deg': round(math.degrees(math.atan2(dvec[1], dvec[0])), 1),
            'material_texture': mat, 'uv': 'U across the lip 0..1, V along the fall (texture tiles in Y, scroll down)', 'foam_at_base': True,
            'spray_radius_m': 6.0, 'axis_index': [int(il), int(ib)],
            'note': 'W86: mountain lake (30 m, on a bench of the NW ridge) -> brook -> this fall down the rock face between two rocks -> plunge pool '
                    '(12 m) -> stream -> river in the gorge (Vadim 22.10)'}
    # sea waterfall: last axis point on land -> extend the axis direction to the first sea cell
    p1, p0 = axis[-1], axis[-4]
    dv = (p1[0] - p0[0], p1[1] - p0[1])
    Lv = math.hypot(*dv) or 1.0
    dv = (dv[0] / Lv, dv[1] / Lv)
    q = p1
    for k in range(0, 60):
        q = (p1[0] + dv[0] * k * 0.5, p1[1] + dv[1] * k * 0.5)
        if sea[int(q[1]), int(q[0])]:
            break
    lip = (q[0] - dv[0] * 1.5, q[1] - dv[1] * 1.5)
    bot = (q[0] + dv[0] * 2.0, q[1] + dv[1] * 2.0)
    nr = (-dv[1], dv[0])
    ws = max(5.0, widths[-1] * 0.7)
    z_lip = float(surf[-1])
    wf_s = {'id': 'waterfall_sea', 'kind': 'waterfall', 'at': [round(lip[0], 2), round(lip[1], 2)], 'top_m': round(z_lip, 2),
            'top': [round(lip[0], 2), round(lip[1], 2), round(z_lip, 2)], 'bottom': [round(bot[0], 2), round(bot[1], 2), 0.0],
            'lip_edge': [[round(lip[0] + nr[0] * ws / 2, 2), round(lip[1] + nr[1] * ws / 2, 2), round(z_lip, 2)],
                         [round(lip[0] - nr[0] * ws / 2, 2), round(lip[1] - nr[1] * ws / 2, 2), round(z_lip, 2)]],
            'base_edge': [[round(bot[0] + nr[0] * (ws + 1.5) / 2, 2), round(bot[1] + nr[1] * (ws + 1.5) / 2, 2), 0.0],
                          [round(bot[0] - nr[0] * (ws + 1.5) / 2, 2), round(bot[1] - nr[1] * (ws + 1.5) / 2, 2), 0.0]],
            'width_top_m': round(ws, 2), 'width_base_m': round(ws + 1.5, 2), 'drop_m': round(z_lip, 2),
            'flow_dir_deg': round(math.degrees(math.atan2(dv[1], dv[0])), 1), 'material_texture': mat,
            'uv': 'U across the lip 0..1, V along the fall', 'foam_at_base': True, 'spray_radius_m': 5.0,
            'note': 'W86: the river leaves the gorge through the high grey rocks at the Quiet Valley east edge and falls straight into the sea (v02 §8.8)'}
    for b in water:
        if b['id'] == 'river':
            nb = dict(b)
            nb['axis'] = [[round(p[0], 2), round(p[1], 2)] for p in axis]
            nb['width_m'] = [round(float(w_), 2) for w_ in widths]
            nb['surface_m'] = [round(float(v), 2) for v in surf]
            nb['bed_m'] = [round(float(v), 2) for v in bed]
            nb['reach'] = [str(r_) for r_ in reach]
            nb['underground_spans'] = under
            nb['cascades_axis_index'] = casc
            nb['gorge_depth_m'] = [4.0, 13.0]
            nb['note'] = ('one river (W86): mountain lake on the NW ridge bench (30 m) -> brook -> waterfall 29.3 -> 12 m between two rocks -> plunge pool '
                          '-> stream with cascades -> river in a gorge cut into the ground round the Hamlet (surface 5.6 .. 4.3 m, rims 4-5 m higher) -> two '
                          'natural land bridges (river underground, rock portals) -> road bridge to the Quiet Valley -> gorge through the grey rocks -> '
                          'waterfall straight into the sea. Builder: water ribbon at surface_m (NOT the v01 RiverBed formula), skip underground_spans, '
                          'white water at cascades_axis_index and both falls')
            bodies.append(nb)
        elif b['id'] == 'mountain_lake':
            bodies.append({**b, 'surface_m': LAKE_SURF, 'note': 'W86: on a bench of the NW ridge (31.6 m), rocky shore to the west / north, outlet brook to the waterfall'})
        elif b['id'] == 'plunge_pool':
            bodies.append({**b, 'surface_m': POOL_SURF, 'note': 'pool under the mountain waterfall, rock bowl between two rocks, foam'})
        elif b['id'] == 'waterfall_mountain':
            bodies.append(wf_m)
        elif b['id'] == 'waterfall_sea':
            bodies.append(wf_s)
        else:
            bodies.append(b)
    return [wf_m, wf_s], bodies


def river_depth_check(h, axis, surf, reach, br_e, xs, ys):
    """'never at ground level': min ground 10-25 m either side of the axis minus the water surface (river / stream reaches, land bridges skipped)."""
    out = []
    for i in range(0, len(axis) - 1, 3):
        if reach[i] not in ('river', 'stream', 'gorge_rocks'):
            continue
        p, q = axis[i], axis[min(i + 1, len(axis) - 1)]
        tx_, ty_ = q[0] - p[0], q[1] - p[1]
        L = math.hypot(tx_, ty_) or 1.0
        nx_, ny_ = -ty_ / L, tx_ / L
        if br_e[int(p[1]), int(p[0])] < 1.4 or math.hypot(p[0] - axis[-1][0], p[1] - axis[-1][1]) < 14:
            continue
        sides = []
        for sgn in (1, -1):
            v = [h[int(np.clip(p[1] + sgn * ny_ * r, 0, H - 1)), int(np.clip(p[0] + sgn * nx_ * r, 0, W - 1))] for r in range(10, 21, 2)]
            sides.append(float(np.min(v)))
        out.append((i, min(sides) - float(surf[i])))
    v = np.array([d for _, d in out]) if out else np.array([0.0])
    worst = sorted(out, key=lambda t: t[1])[:5]
    return {'stations': len(out), 'min_bank_above_surface_m': round(float(v.min()), 2), 'p10_m': round(float(np.percentile(v, 10)), 2),
            'under_2m': int((v < 2.0).sum()), 'worst': [[int(i), [round(axis[i][0], 1), round(axis[i][1], 1)], round(d, 2)] for i, d in worst]}


def ground_fit(h, Dd, xs, ys):
    """AUDIT §5 13: terrain height range under every building footprint (> 1.5 m = the building floats or is buried)."""
    res = []
    for dn, d in Dd.items():
        if d.get('abs_heights') and dn == 'elite':
            pass
        for b in d.get('buildings', []):
            if b.get('disabled') or len(b.get('footprint') or []) < 3:
                continue
            m = poly_mask(b['footprint'], xs, ys)
            if m.sum() < 2:
                continue
            v = h[m]
            res.append((dn, b['id'], b['kind'], round(float(v.max() - v.min()), 2)))
    bad = [r_ for r_ in res if r_[3] > 1.5]
    return {'buildings': len(res), 'over_1_5_m': len(bad), 'worst': sorted(bad, key=lambda r_: -r_[3])[:25],
            'rule': 'footprint height range > 1.5 m = error (builder: plinth or move)'}


# ---------------------------------------------------------------- far steppe backdrop (separate Unity terrain north of the map)
BK = {'res': 1025, 'dx': W / (RES - 1) * 8, 'dz': 4.0, 'x_cells_west': 294, 'z0': H - 8.0, 'base_y': -20.0, 'range': 300.0}


def steppe_backdrop(raw_main, h):
    """Endless dry 'Mongolian' steppe beyond the north border (v02 §8.4, Vadim 22.10 #1): long gentle swells rising to far mountains on the
    horizon; on the LEFT the NW ridge continues north and curves away west (the steppe goes on behind it), on the RIGHT the rocky ridge
    of the Rough's east edge continues north with the sea behind it, so from the Rough no sea is seen to the N / NE / NW.
    Seam: backdrop row 2 (z = 950) = the main terrain's top RAW row at every 8th main vertex (x aligned); rows 0-1 (z 942, 946) lie
    0.5 m under the main terrain (skirt, hides LOD cracks)."""
    n = BK['res']
    dx, dz = BK['dx'], BK['dz']
    X0 = -BK['x_cells_west'] * dx
    Xb = X0 + np.arange(n) * dx
    Zb = BK['z0'] + np.arange(n) * dz
    XX, ZZ = np.meshgrid(Xb, Zb)
    zp = np.maximum(ZZ - H, 0.0)
    f = lambda sc, oc, sd: fbm(XX, ZZ, sc, oc, sd)
    base = 7.5 + 38.0 * sm(zp / 3200.0) + 5.0 * f(700, 2, 61) * sm(zp / 300.0) + 2.5 * f(260, 2, 62) + 0.6 * f(60, 2, 63)
    rid = 1 - np.abs(f(220, 3, 64))
    CL = [(548, 940), (540, 1100), (505, 1300), (410, 1550), (230, 1800), (-60, 2050), (-450, 2300), (-1000, 2550), (-1700, 2760), (-2300, 2860)]
    dL = pl_dist_grid(CL, XX, ZZ)
    hwL = 150 + 0.05 * zp
    mL = (88 + 30 * sm(zp / 1500)) * sm(1 - dL / hwL) ** 1.3 * (0.78 + 0.22 * rid)
    CR = [(1080, 940), (1098, 1050), (1128, 1300), (1178, 1700), (1248, 2200), (1330, 2800), (1420, 3500), (1500, 4300), (1560, 5200)]
    dR = pl_dist_grid(CR, XX, ZZ)
    xr = np.interp(ZZ, [p[1] for p in CR], [p[0] for p in CR])
    east = XX > xr
    hwR = np.where(east, 70.0, 110.0 + 0.04 * zp)
    topR = 30.0 + 28.0 * sm(zp / 450.0) + 22.0 * sm((zp - 900) / 1800)
    mR = topR * sm(1 - dR / hwR) ** 1.15 * (0.8 + 0.2 * rid)
    far = 230.0 * sm((zp - 2300.0) / 1400.0) ** 1.2 * (0.55 + 0.45 * (1 - np.abs(f(330, 3, 65))))
    hd = smax(smax(smax(base, mL, 6.0), mR, 6.0), far, 8.0)
    # sea: east of the right ridge, and the west coast going north-west from the island's NW corner
    sea_e = sm((XX - xr - 55.0) / 150.0)
    xw = 62.0 - 0.85 * zp
    sea_w = sm((xw - XX) / 140.0)
    sea_w = sea_w * (1 - sm((zp - 1500) / 600.0))                         # far north-west: mountains close the view
    sw = np.maximum(sea_e, sea_w)
    hd = hd * (1 - sw) + (-12.0) * sw
    # seam: blend from the main terrain's north edge into the design over 300 m
    seam_row = np.full(n, np.nan)
    main_top = raw_main[-1].astype(np.float64) / 65535 * HEIGHT_RANGE + BASE_Y
    for i in range(n):
        k = 8 * i - 8 * BK['x_cells_west']
        if 0 <= k < raw_main.shape[1]:
            seam_row[i] = main_top[k]
    have = ~np.isnan(seam_row)
    seam_full = np.where(have, seam_row, hd[2])
    w_ = sm(zp / 300.0)
    w_ = np.where(have[None, :], w_, 1.0)
    out = seam_full[None, :] * (1 - w_) + hd * w_
    out[0] = np.where(have, seam_full - 0.5, out[2])
    out[1] = np.where(have, seam_full - 0.5, out[2])
    out[2] = seam_full
    zzq = np.clip((out - BK['base_y']) / BK['range'], 0, 1)
    rawb = (zzq * 65535).round().astype('<u2')
    fn = 'Steppe_backdrop_v02_%d_r16.bytes' % n
    rawb.tofile(os.path.join(OUT, fn))
    # splat hint: R = dry steppe grass (L02), G = rock (L07), B = greener swales (L01), A = coast sand / gravel (L05/L06)
    gy_, gx_ = np.gradient(out, dz, dx)
    sl = np.degrees(np.arctan(np.hypot(gx_, gy_)))
    rockw = np.clip((sl - 24) / 12, 0, 1) * 0.9 + np.clip((out - 70) / 60, 0, 1) * 0.5
    sandw = np.clip(1 - np.abs(out - 0.8) / 2.5, 0, 1) * (out < 3.5)
    swale = np.clip(-(base - ndimage.gaussian_filter(base, 25)) / 2.0, 0, 1) * 0.6
    rockw = np.clip(rockw, 0, 1)
    greenw = np.clip(swale * (1 - rockw), 0, 1)
    dry = np.clip(1 - rockw - greenw - sandw, 0, 1)
    from PIL import Image
    spl = np.stack([dry, rockw, greenw, sandw], -1)
    spl = spl / np.maximum(spl.sum(-1, keepdims=True), 1e-6)
    os.makedirs(os.path.join(OUT, 'masks'), exist_ok=True)
    Image.fromarray((spl[::-1] * 255 + 0.5).astype(np.uint8), 'RGBA').resize((513, 513), Image.BILINEAR).save(os.path.join(OUT, 'masks', 'steppe_backdrop_splat_v02.png'))
    meta = {'heightmap': fn, 'format': 'RAW 16-bit LE, %d x %d, row 0 = south, column 0 = west' % (n, n),
            'position_m': [round(X0, 4), BK['base_y'], BK['z0']], 'size_m': [round(dx * (n - 1), 4), BK['range'], dz * (n - 1)],
            'cell_m': [dx, dz], 'height_range_m': [BK['base_y'], BK['base_y'] + BK['range']],
            'seam': {'z_m': float(H), 'row': 2, 'x_alignment': 'backdrop column i <-> main RAW column 8 i - %d (exact vertex match for 0 <= 8 i - %d <= 2048)'
                     % (8 * BK['x_cells_west'], 8 * BK['x_cells_west']), 'skirt': 'rows 0-1 (z 942 / 946) are 0.5 m under the main terrain: '
                     'place the backdrop terrain BEFORE / UNDER the main one, its skirt hides LOD cracks at z = 950',
                     'main_top_rows': 'the main RAW top 6 rows are piecewise linear between every 8th vertex (s03 seam_linear)'},
            'splat': 'masks/steppe_backdrop_splat_v02.png (RGBA 513 x 513, row 0 = NORTH): R = L02 dry steppe grass, G = L07 rock, B = L01 meadow '
                     '(greener swales), A = L05/L06 coast sand-gravel',
            'unity': {'collider': False, 'cast_shadows': False, 'pixel_error': 8, 'basemap_distance': 300, 'draw_trees_and_details': False,
                      'note': 'seen only (beyond the invisible wall on the border fence); no grass details beyond ~150 m'},
            'haze': {'fog': 'linear', 'start_m': 250, 'end_m': 3800, 'colour_hint': '#D8D3B8 (steppe dust) blended to the sky horizon',
                     'note': 'the far mountains (200+ m at 3-4 km) fade into haze; no hard horizon'},
            'design': {'steppe': '~7.5 m at the seam (main map: soft +2.5 m rise beyond the fence) rising in long swells to ~45 m at 3 km, '
                                 'swells +-5 m (700 m) and +-2.5 m (260 m)',
                       'left_mountains': 'NW ridge continues north from x ~548 and curves away west, 88 -> 118 m, the steppe goes on behind it',
                       'right_ridge': 'rocky ridge from the Rough\'s east edge (1092, 952) north-north-east, 30 -> 80 m, sea east of it',
                       'far_mountains': 'up to ~230 m from ~3 km north (horizon)', 'sea': 'east of the right ridge and north-west of the island\'s NW corner'},
            'heights_m': {'min': round(float(out.min()), 1), 'max': round(float(out.max()), 1), 'seam_max_abs_diff_m': 0.0}}
    save_json('steppe_backdrop_v02.json', meta)
    np.save(os.path.join(WORK, 'steppe_backdrop_h.npy'), out.astype(np.float32))
    return {'file': 'steppe_backdrop_v02.json', 'heightmap': fn, 'position_m': meta['position_m'], 'size_m': meta['size_m']}


def pl_dist_grid(pl, X, Z):
    best = np.full(X.shape, 1e9, np.float32)
    P = np.array(pl, np.float64)
    for a, b in zip(P[:-1], P[1:]):
        v = b - a
        L2 = float(v @ v) or 1e-6
        t = np.clip(((X - a[0]) * v[0] + (Z - a[1]) * v[1]) / L2, 0, 1)
        best = np.minimum(best, np.hypot(X - (a[0] + t * v[0]), Z - (a[1] + t * v[1])))
    return best


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
    dr = ImageDraw.Draw(im)
    P = lambda p: (p[0], (H - p[1]))
    for rd in roads:
        dr.line([P(p) for p in rd['points']], fill=(70, 70, 75) if rd['kind'] != 'dirt' else (160, 130, 90), width=3)
    for i, rf in enumerate(relief):
        col = (180, 40, 40) if rf['height_m'] > 0 else (40, 80, 200)
        dr.line([P(p) for p in rf['crest']], fill=col, width=3)
        q = P(rf['crest'][len(rf['crest']) // 2])
        dr.text((q[0] + 4, q[1] - 12), '%s %+.0f m' % (rf['id'], rf['height_m']), fill=col)
    for name, p, txt in (('B', F['view_B'], 'VIEW B'), ('C', F['view_C'], 'VIEW C')):
        q = P(p)
        dr.ellipse((q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4), fill=(255, 255, 255))
        dr.text((q[0] + 6, q[1] - 6), txt, fill=(255, 255, 255))
    im.save(os.path.join(WORK, 'relief_scheme_v85.png'))


if __name__ == '__main__':
    main()
