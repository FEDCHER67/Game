"""Step 2: vector data of map v76 — roads, water bodies, northern border, tunnel, land bridges, viewpoints.

Priority of sources (nothing re-invented):
 1. vector constants of build_world_v76.py (ROAD_*, TUN, RING, TRACK, VIEWS, fence, KPP, land bridges, rivers) -> post_shift;
 2. roads that only exist in Vadim's master SVG (Downtown grid, Rough outer road, Port -> Tramduro bridge, Quiet Valley,
    village streets) -> vectorised from the v76 render (asphalt / dirt classes, skeleton + width from the distance field).
Output: Data/v01/roads_v76.json, water_v76.json, border_v76.json, features_v76.json.
"""
import math
import os

import numpy as np

from common import (WORK, W, H, chaikin, post, post_all, rnd2, save_json, resample)

# ---------- build_world_v76.py constants (pre-shift) ----------
VIEWS = {'B': (1010, 594), 'C': (1194, 532)}
ROAD_H = [(496, 348), (530, 347), (600, 348), (700, 348), (786, 348)]
ROAD_VALLEY = [(530, 347), (541, 336), (543, 322)]
ROAD_C = chaikin([(1222, 438), (1219, 462), (1210, 485), (1199, 508), VIEWS['C'], (1202, 556), (1222, 572), (1244, 582),
                  (1258, 596), (1263, 616), (1263, 633)])
ROAD_R = chaikin([(505, 572), (555, 573), (590, 581), (612, 598), (630, 624), (646, 644), (658, 651)], 3) + [(666, 652)]
BYP_PTS = [(496, 348), (481, 348), (467, 357), (463, 392), (461, 480), (461, 534), (463, 555), (469, 567), (482, 572), (505, 572)]
ROAD_BN = chaikin(BYP_PTS, 3)
ROAD_RING = [(686, 766), (676, 766), (666, 766), (666, 652)]
TUN = [(748, 627), (770, 604), (805, 568), (838, 532), (855, 516)]
TUN_N = [(748, 652), (748, 640), (748, 627)]
TUN_S = [(855, 516), (859, 497), (860, 477)]
ROAD_S = [(945, 650)] + chaikin([(952, 636), (938, 618), (962, 604), VIEWS['B'], (1038, 584), (1020, 566), (1044, 550), (1068, 540),
                                 (1056, 522), (1070, 500)], 3) + [(1070, 477)]
ROAD_N = [(860, 874), (860, 1000)]
MOUNT_B = [(752, 556), (840, 574), (920, 590), (1000, 586), (1080, 574), (1150, 562)]   # crest, half-width 58, 50 m
MT_E = [(436, 826), (466, 818), (498, 822), (528, 836), (552, 856), (570, 878), (574, 896), (558, 906), (530, 904), (502, 896), (478, 886), (452, 877), (436, 872)]
CREST_D = [(440, 846), (476, 852), (510, 865), (540, 880), (562, 894)]
MT_R2 = [(1026, 906), (1034, 891), (1050, 880), (1066, 883), (1080, 896), (1092, 912), (1100, 930), (1030, 930)]
CREST_R2 = [(1046, 884), (1062, 893), (1078, 908), (1092, 930)]
F_L = [(512, 782), (560, 790), (598, 800), (626, 816), (640, 840), (642, 862), (630, 874), (608, 874), (584, 862), (556, 848), (530, 834), (512, 826)]
LAND_BRIDGES = [(484, 349), (488, 572)]
CHILL = (668, 640)                                                   # "+8 m" knoll label
RIV_QV = chaikin([(556, 284), (636, 282), (646, 266), (650, 230), (652, 190), (654, 150), (656, 116), (657, 96)], 3)   # warp_m(556,284) ~ identity here
ROCKZ = [(616, 88), (632, 84), (634, 104), (645, 138), (668, 170), (688, 190), (698, 214), (692, 246), (674, 276), (652, 292), (638, 268), (630, 205), (628, 140), (620, 90)]
FOOT_B = [(1236, 238), (1262, 244), (1282, 248), (1300, 254), (1322, 259), (1350, 263), (1400, 267), (1440, 270), (1466, 265)]
TRACK = chaikin([(1142, 214), (1190, 207), (1240, 214), (1290, 230), (1340, 244), (1390, 252), (1440, 256), (1470, 254), (1488, 262), (1492, 280), (1490, 300)], 2)
PIER = [(1007, 221), (1017, 221), (1017, 128), (1007, 128)]
PIER_HEAD = [(997, 128), (1027, 128), (1027, 116), (997, 116)]
EC, EA, EB = (1398.2, 349.5), 72.5, 58.8                            # Elite fence: centre, half sizes (superellipse n = 4)


def coast_y(x):
    return 908 + 7 * math.sin(x / 41.0) + 5 * math.sin(x / 13.0 + 1.3) if 540 <= x <= 1060 else 9999


def elite_ring():
    ring = [(1240.0, 351.0), (1270.0, 350.5)]
    for i in range(241):
        t = i / 240.0
        th = math.pi - 2 * math.pi * t
        off = 24.0 - 11.0 * t
        c, s = math.cos(th), math.sin(th)
        ex, ey = math.copysign(abs(c) ** 0.5, c), math.copysign(abs(s) ** 0.5, s)
        ring.append((EC[0] + (EA + off) * ex, EC[1] + (EB + off) * ey))
    ring += [(1318.0, 351.0), (1327.0, 351.0)]
    return ring


def elite_fence(n=96):
    out = []
    for i in range(n):
        th = 2 * math.pi * i / n
        c, s = math.cos(th), math.sin(th)
        out.append((EC[0] + EA * math.copysign(abs(c) ** 0.5, c), EC[1] + EB * math.copysign(abs(s) ** 0.5, s)))
    return out


# ---------- skeleton roads from the render ----------
def skeleton_polylines(mask, min_len=12):
    from skimage.morphology import skeletonize
    sk = skeletonize(mask)
    ys, xs = np.nonzero(sk)
    pts = set(zip(xs.tolist(), ys.tolist()))
    nb = lambda p: [(p[0] + dx, p[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and (p[0] + dx, p[1] + dy) in pts]
    deg = {p: len(nb(p)) for p in pts}
    seen, lines = set(), []
    starts = [p for p in pts if deg[p] != 2] + list(pts)
    for s in starts:
        for n0 in nb(s):
            e = (min(s, n0), max(s, n0))
            if e in seen:
                continue
            line, prev, cur = [s], s, n0
            seen.add(e)
            while True:
                line.append(cur)
                if deg[cur] != 2:
                    break
                nxt = [q for q in nb(cur) if q != prev and (min(cur, q), max(cur, q)) not in seen]
                if not nxt:
                    break
                seen.add((min(cur, nxt[0]), max(cur, nxt[0])))
                prev, cur = cur, nxt[0]
            if len(line) >= min_len:
                lines.append(line)
    return lines


def simplify(pl, eps=1.2):
    if len(pl) < 3:
        return pl
    a, b = np.array(pl[0], float), np.array(pl[-1], float)
    v = b - a
    L = np.hypot(*v) or 1e-6
    d = [abs(v[0] * (p[1] - a[1]) - v[1] * (p[0] - a[0])) / L for p in pl[1:-1]]
    i = int(np.argmax(d)) + 1
    if d[i - 1] > eps:
        return simplify(pl[:i + 1], eps)[:-1] + simplify(pl[i:], eps)
    return [pl[0], pl[-1]]


def raster_roads(cls, cls_id, kind, known, min_w, exclude=None):
    from scipy import ndimage
    m = cls == cls_id
    m = ndimage.binary_closing(m, iterations=1)
    m = ndimage.binary_opening(m, iterations=1)
    if exclude is not None:
        m &= ~exclude
    dist = ndimage.distance_transform_edt(m)
    out = []
    for line in skeleton_polylines(m):
        pts = [(x + 0.5, y + 0.5) for x, y in line]                     # cls rows are world y already
        w = float(np.median([dist[y, x] for x, y in line])) * 2.0
        if w < min_w:
            continue
        mid = pts[len(pts) // 2]
        if min((math.hypot(mid[0] - q[0], mid[1] - q[1]) for k in known for q in resample(k, 3.0)), default=99) < max(4.0, w):
            continue                                                    # already covered by a script spline
        out.append({'id': '%s_%03d' % (kind, len(out)), 'kind': kind, 'source': 'v76 render (skeleton)',
                    'width_m': round(max(w, min_w), 1), 'points': [rnd2(p) for p in simplify(pts)]})
    return out


def main():
    cls = np.load(os.path.join(WORK, 'classes_v76.npy'))
    S = lambda pl: post_all(pl)
    roads = []

    def add(rid, kind, pts, width, surface, note, **kw):
        roads.append(dict(id=rid, kind=kind, surface=surface, width_m=width, source='build_world_v76.py ' + note,
                          points=[rnd2(p) for p in resample(S(pts), 4.0)], **kw))

    add('hamlet_to_downtown', 'rural_asphalt', ROAD_H, 6.4, 'asphalt_A5d12', 'ROAD_H')
    add('to_quiet_valley', 'rural_asphalt', ROAD_VALLEY, 6.4, 'asphalt_A5d12', 'ROAD_VALLEY')
    add('cornice_view_c', 'rural_asphalt', ROAD_C, 6.4, 'asphalt_A5d12', 'ROAD_C (VIEW C cornice over the bay)', viewpoint=rnd2(post(VIEWS['C'])))
    add('hamlet_to_rough', 'rural_asphalt', ROAD_R, 6.4, 'asphalt_A5d12', 'ROAD_R (over land bridge y 572)')
    add('rough_west_link', 'rural_asphalt', ROAD_RING, 6.4, 'asphalt_A5d12', 'ROAD_RING')
    add('hamlet_bypass', 'rural_asphalt', ROAD_BN, 6.4, 'asphalt_A5d12', 'ROAD_BN / BYP_PTS')
    add('tunnel_north_approach', 'rural_asphalt', TUN_N, 6.4, 'asphalt_A5d12', 'TUN_N (~25 m approach, Rough side)')
    add('tunnel', 'tunnel', TUN, 7.0, 'asphalt_A5d12', 'TUN (tunnel axis under hill B; portals at the foot)', tunnel=True)
    add('tunnel_south_approach', 'rural_asphalt', TUN_S, 6.4, 'asphalt_A5d12', 'TUN_S (~40 m approach, Downtown side)')
    add('serpentine_view_b', 'serpentine', ROAD_S, 6.4, 'asphalt_A5d12', 'ROAD_S (serpentine through hill B, VIEW B +46 m)', viewpoint=rnd2(post(VIEWS['B'])), viewpoint_height_m=46.0)
    add('border_checkpoint_road', 'rural_asphalt', [(860, 874), (860, 950)], 6.4, 'asphalt_A5d12', 'ROAD_N (through the checkpoint into the steppe)')
    add('elite_stone_serpentine', 'stone_serpentine', elite_ring(), 4.5, 'cobble_SK2c', 'RING (v74/v75: one loop, offset 24 -> 13 m, +44 m at gate 06)',
        gate_height_m=44.0, parapet='outer, stone', lamps_every_m=18)
    add('beach_van_track', 'sand_track', TRACK, 5.0, 'sand_ruts', 'TRACK (van track over sand to Elite beach)')

    known = [r_['points'] for r_ in roads]
    roads += raster_roads(cls, 4, 'asphalt_from_map', known, 3.5)
    roads += raster_roads(cls, 9, 'dirt_from_map', known, 2.5)

    # ---------- water ----------
    from scipy import ndimage
    water = []
    wm = cls == 2
    lab, n = ndimage.label(ndimage.binary_closing(wm, iterations=2))
    pads = district_boxes()
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < 60:
            continue
        cx, cy = float(xs.mean()) + .5, float(ys.mean()) + .5
        inside = [k for k, b in pads.items() if b[0] <= cx <= b[2] and b[1] <= cy <= b[3]]
        if inside:
            continue                                                    # pools / water plaza / roofs: district data
        ext = (xs.max() - xs.min(), ys.max() - ys.min())
        elong = max(ext) / max(1, min(ext))
        kind = 'river' if elong > 4 or len(xs) > 2500 and elong > 2.5 else 'lake'
        cont = contour(lab == i)
        rec = {'id': '%s_%02d' % (kind, len(water)), 'kind': kind, 'area_m2': int(len(xs)), 'centre': rnd2((cx, cy)),
               'outline': [rnd2(p) for p in cont]}
        if kind == 'lake':
            if cy > 700:
                rec.update(name='mountain_lake', depth_m=4.0, note='at the foot of the ridge; waterfall into the stream (no trail, v76)')
            elif cx < 300 and cy > 400:
                rec.update(name='hamlet_pond', depth_m=1.5, note='reeds, water lilies, van cannot pass')
            else:
                rec.update(name='forest_lake', depth_m=3.0, note='one lake, rounder, at the northern edge of the forest')
        else:
            rec.update(depth_m=1.6, flow=True, gorge_depth_m=[6, 13], note='one river: mountain lake -> waterfall -> gorge -> Hamlet (2 land bridges) -> Quiet Valley -> waterfall into the sea')
        water.append(rec)
    sw = cls == 13
    lab2, n2 = ndimage.label(ndimage.binary_closing(sw, iterations=2))
    for i in range(1, n2 + 1):
        if (lab2 == i).sum() > 300:
            ys, xs = np.nonzero(lab2 == i)
            water.append({'id': 'swamp_%02d' % i, 'kind': 'swamp', 'area_m2': int(len(xs)), 'centre': rnd2((xs.mean() + .5, ys.mean() + .5)),
                          'depth_m': 0.6, 'outline': [rnd2(p) for p in contour(lab2 == i)],
                          'note': 'dark-green patch in the forest = swamp (dark water, tussocks, reeds, moss) — not a lake'})
    water.append({'id': 'sea', 'kind': 'sea', 'level_m': 0.0, 'depth_profile': 'shore -1 m -> -12 m at 70 m off; ~8 m shallow band on beaches',
                  'material': 'Sea_trial_calm_v09 (default; v10 = OPEN)', 'mesh': 'dense grid near camera'})
    water.append({'id': 'waterfall_sea', 'kind': 'waterfall', 'at': rnd2(post((657, 96))), 'top_m': 9.0, 'note': 'river falls straight into the sea at Quiet Valley'})
    save_json('water_v76.json', {'units': 'm, world v76', 'bodies': water})

    # ---------- border ----------
    fence = [(x, coast_y(x) + 2) for x in range(572, 1031, 4)]
    fence = S(fence)
    gx, gy = post((860, coast_y(860) + 2))
    border = {'fence': {'kind': 'chain_link', 'height_m': 2.5, 'points': [rnd2(p) for p in fence], 'invisible_wall_height_m': 60.0,
                        'note': 'invisible wall along the fence; steppe beyond is only visible'},
              'towers': [rnd2(post((x, coast_y(x) - 2))) for x in (735.0, 975.0)],
              'checkpoint': {'building_centre': rnd2((gx - 14, gy - 3)), 'building_size_m': [16, 9, 3.6], 'flag': True,
                             'gate': {'from': rnd2((gx - 6, gy)), 'to': rnd2((gx + 7, gy)), 'kind': 'sliding steel gate, red-white band, ribs, rail',
                                      'button': 'Leave the country', 'reply_ru': 'Нет, страну покинуть нельзя: введено военное положение'},
                             'no': ['barrier arm', 'APC', 'spikes', 'hedgehogs', 'sandbags', 'separate road']},
              'steppe': {'rises_to_horizon_m': 18.0, 'beyond_fence': True, 'far_mountains_backdrop': True},
              'right_ridge': {'crest': [rnd2(p) for p in S(CREST_R2)], 'height_m': 32}}
    save_json('border_v76.json', border)

    # ---------- relief features ----------
    feats = {'hill_B': {'crest': [rnd2(p) for p in S(MOUNT_B)], 'half_width_m': 58, 'peak_m': 50},
             'view_B': rnd2(post(VIEWS['B'])), 'view_C': rnd2(post(VIEWS['C'])),
             'chill_knoll': {'centre': rnd2(post(CHILL)), 'height_m': 8},
             'tunnel_axis': [rnd2(p) for p in S(TUN)],
             'land_bridges': [{'centre': rnd2(post(p)), 'rx_m': 14, 'ry_m': 15} for p in LAND_BRIDGES],
             'small_ridge': {'poly': [rnd2(p) for p in S(MT_E)], 'crest': [rnd2(p) for p in S(CREST_D)], 'top_m': [92, 56]},
             'right_ridge': {'poly': [rnd2(p) for p in S(MT_R2)], 'crest': [rnd2(p) for p in S(CREST_R2)], 'top_m': 32},
             'border_forest': [rnd2(p) for p in S(F_L)],
             'quiet_valley_rocks': [rnd2(p) for p in S(ROCKZ)],
             'quiet_valley_river': [rnd2(p) for p in S(RIV_QV)],
             'elite': {'centre': rnd2(post(EC)), 'half': [EA, EB], 'fence': [rnd2(p) for p in S(elite_fence())], 'plateau_m': [40, 44]},
             'elite_palm_row': [rnd2(p) for p in S(FOOT_B)],
             'beach_pier': [rnd2(p) for p in S(PIER)], 'beach_pier_head': [rnd2(p) for p in S(PIER_HEAD)]}
    save_json('features_v76.json', feats)
    save_json('roads_v76.json', {'units': 'm, world v76 (x east, y north); Unity X = x, Z = y', 'roads': roads,
                                 'rules': 'junctions: minor road meets major at right angle with straight approach; max grade target 8 %'})
    print(len(roads), 'roads;', len(water), 'water bodies')


def contour(mask, step=3):
    from skimage import measure
    cs = measure.find_contours(np.pad(mask, 1).astype(float), 0.5)
    c = max(cs, key=len)
    return [(p[1] - 0.5, p[0] - 0.5) for p in c[::step]]


def district_boxes():
    """World bboxes of districts on v76 (from the render, used only to skip pools/roofs when picking natural water)."""
    return {'downtown': (790, 220, 1265, 465), 'rough': (655, 665, 1005, 905), 'elite': (1325, 255, 1515, 395),
            'port': (1170, 600, 1350, 690), 'tramduro': (1440, 650, 1665, 880), 'construction': (530, 340, 695, 485),
            'quiet_valley_lab': (560, 230, 615, 260)}


if __name__ == '__main__':
    main()
