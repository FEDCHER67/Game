"""Step 2 (v85): world road network, water bodies, northern border, relief features.

Sources, in this order (handoff v10 §1, §2, §6):
 1. district data (s04_*: roads flagged world_road, Downtown entries, Elite stone road with heights, port road, bridge to Tramduro,
    beach van track, forest / valley dirt roads) — these are already fitted 1:1 and fixed by logic;
 2. the vector road layers of the v85 master SVG (R24_roads, R52_bypass, R33_tunnel, R27_cornice_in_port, L05 / L05b, district_08 …)
    for everything else (Vadim's v84 joins: every road end on the neighbour road axis);
 3. no raster skeletons (v76 vectorised the render; v85 has vectors).
Rules applied here (logged in fixes[] -> docs/reports/MAP_W85_FIXED_BY_LOGIC.md):
 - duplicates of the same road (R52 vs R24 bypass, D04 vs R85 ring, R84 port road vs district_06) built once;
 - every road end is snapped onto the axis of the road it meets (T-join) or onto a Downtown entry point (carriageway edge),
   with a straight approach over the last ~15 m; ends that meet nothing must be an approved dead end (gate, KPP, base, bridge);
 - widths: rural asphalt 6.4, village / forest dirt 5.4, Elite stone 4.5, lab drive 4.8, sand ruts 5.0 (v10 §6).
Output: roads_v85.json, water_v85.json, border_v85.json, features_v85.json (Data/<REV>).

Downtown plan v37 (Map W86, agent A3, 2026-10-22; active when downtown_v85.json is the W86 / v37 file): the city grew 52-60 m north and 54 m
south, so the north roads meet the NEW top ring: the tunnel keeps its axis but its south portal moves ~74 m up the axis to the new hill foot
(the old portal is inside block NW0), its approach bends (Bezier, R >= ~20 m) into a straight 26 m T-approach on N0w; the VIEW B serpentine
and the VIEW C cornice are cut where they reach the ring and bent the same way into T's on N0c / N0e (smooth_join). The beach van track
to the Elite beach comes from the moved beach file. Nothing else changes here.
"""
import math
import os

import numpy as np

import common as c
from common import post, rnd2, resample, plen, nearest_on, save_json, load_json

D = {n: load_json('districts/%s_v85.json' % n) for n in
     ('beach', 'construction', 'downtown', 'elite', 'forest', 'hamlet', 'port', 'quiet_valley', 'rough', 'tramduro')}
FIXES = []


def fix(rid, where, ru, why):
    FIXES.append({'id': 'road-%02d' % (len(FIXES) + 1), 'road': rid, 'where': rnd2(where), 'ru': ru, 'why_ru': why})


def zone(dn, zid):
    return next(z for z in D[dn]['zones'] if z['id'] == zid)


def zline(dn, zid):
    z = zone(dn, zid)
    return [tuple(p) for p in (z.get('line') or z.get('poly_line') or z.get('polyline'))]


# ------------------------------------------------------------------ SVG road vectors
def svg_roads():
    s = c.svg_text()
    out = []
    for nm, at, M, gids, a, b in c.svg_tags(s):
        if nm != 'polyline' or not gids or gids[-1] in ('L12_title_legend', 'R84_junctions'):
            continue
        st, w = c.attr(at, 'stroke'), c.attr(at, 'stroke-width')
        kind = {('#5F666C', '32'): 'asphalt', ('#5F666C', '24'): 'asphalt_narrow', ('#E5D2A4', '27'): 'dirt'}.get((st, w))
        if not kind:
            continue
        pts = [c.u2w(*p) for p in c.points_of(at, M)]
        out.append({'group': gids[-1], 'kind': kind, 'svg_id': c.attr(at, 'id'), 'pts': pts})
    return out


def pick(svg, group, start, end, tol=4.0):
    for r in svg:
        if r['group'] != group:
            continue
        a, b = r['pts'][0], r['pts'][-1]
        if math.dist(a, start) < tol and math.dist(b, end) < tol:
            return list(r['pts'])
        if math.dist(b, start) < tol and math.dist(a, end) < tol:
            return list(r['pts'])[::-1]
    raise SystemExit('svg road not found %s %s %s' % (group, start, end))


def dedupe(pl, step=1.0):
    out = [pl[0]]
    for p in pl[1:]:
        if math.dist(p, out[-1]) >= step:
            out.append(p)
    if math.dist(out[-1], pl[-1]) > 1e-6:
        out[-1] = pl[-1]
    return out


def clip_from(pl, p, keep='after'):
    """Cut a polyline at its nearest point to p; keep the part after (or before) it."""
    d, q, i, t = nearest_on(pl, p)
    if keep == 'after':
        return [q] + pl[i + 1:]
    return pl[:i + 1] + [q]


def straighten_end(pl, target, axis_dir, L=15.0):
    """Make the last L metres of pl run straight along axis_dir into target (v10 §6: straight approach 10-20 m)."""
    pl = list(pl)
    acc, k = 0.0, len(pl) - 1
    while k > 0 and acc < L:
        acc += math.dist(pl[k], pl[k - 1])
        k -= 1
    start = (target[0] - axis_dir[0] * L, target[1] - axis_dir[1] * L)
    keep = pl[:k + 1]
    # blend: drop points of `keep` that are already beyond the straight start
    while len(keep) > 1 and math.dist(keep[-1], target) < L:
        keep.pop()
    return keep + [start, target]


ROADS = []


def smooth_join(pl, target, d, Ls=23.0, Lb=30.0, n=14):
    """pl runs from its far end towards the city. Cut it at the first point P that comes within Lb of S = target - d * Ls, then a cubic
    Bezier P -> S (tangent of pl at P, tangent d at S, handles |PS| / 3) and the straight S -> target (v10 §6: right angle, straight approach
    10-20 m, axis to axis). Returns (kept far part ending at P, joined road P .. target, min radius of the bend m, P)."""
    S = (target[0] - d[0] * Ls, target[1] - d[1] * Ls)
    pts = resample([tuple(q) for q in pl], 0.5)
    k = next((i for i, q in enumerate(pts) if math.dist(q, S) <= Lb), None)
    if k is None:
        k = min(range(len(pts)), key=lambda i: math.dist(pts[i], S))
    P = pts[k]
    a = pts[max(0, k - 4)]
    t0 = ((P[0] - a[0]), (P[1] - a[1]))
    L0 = math.hypot(*t0) or 1.0
    t0 = (t0[0] / L0, t0[1] / L0)
    h = math.dist(P, S) / 3.0
    B = [P, (P[0] + t0[0] * h, P[1] + t0[1] * h), (S[0] - d[0] * h, S[1] - d[1] * h), S]
    curve = []
    for i in range(n + 1):
        u = i / n
        w = ((1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u * u, u ** 3)
        curve.append((sum(w[j] * B[j][0] for j in range(4)), sum(w[j] * B[j][1] for j in range(4))))
    rmin = 1e9
    for q0, q1, q2 in zip(curve[:-2], curve[1:-1], curve[2:]):
        a_ = math.dist(q0, q1)
        b_ = math.dist(q1, q2)
        c_ = math.dist(q0, q2)
        cr = abs((q1[0] - q0[0]) * (q2[1] - q0[1]) - (q1[1] - q0[1]) * (q2[0] - q0[0]))
        if cr > 1e-9:
            rmin = min(rmin, a_ * b_ * c_ / (2 * cr))
    acc, far = 0.0, [tuple(pl[0])]                                         # original vertices up to P (no resampling of the kept part)
    sP = 0.5 * k
    for a_, b_ in zip(pl[:-1], pl[1:]):
        L_ = math.dist(a_, b_)
        if acc + L_ >= sP - 1e-6:
            break
        far.append(tuple(b_))
        acc += L_
    far.append(P)
    return dedupe(far), curve + [tuple(target)], round(rmin, 1), P


def add(rid, kind, pts, width, surface, src, **kw):
    pts = dedupe([tuple(map(float, p)) for p in pts])
    ROADS.append(dict(id=rid, kind=kind, surface=surface, width_m=width, source=src, points=[rnd2(p) for p in pts], **kw))


VIEWB_POCKET_M = 46.0


def view_b_spur(pass_pl):
    """VIEW B spur polyline (T-join on the pass road near its top -> south shoulder -> one hairpin at the west end of the summit knob -> along
    the summit ridge) and the turnaround pocket at its end (world m)."""
    serp = [tuple(p) for p in pass_pl]
    d, J, i, t = nearest_on(serp, (996.0, 606.0))
    a, b = serp[i], serp[min(i + 1, len(serp) - 1)]
    tx, ty = b[0] - a[0], b[1] - a[1]
    L = math.hypot(tx, ty) or 1.0
    tx, ty = tx / L, ty / L
    n = (-ty, tx) if -ty < 0 else (ty, -tx)                                # normal pointing to the west side (the summit)
    S1 = (J[0] + n[0] * 12.0, J[1] + n[1] * 12.0)                          # 12 m straight perpendicular approach (T-join)
    sm_ = c.chaikin([S1, (962, 582), (930, 564), (900, 552), (872, 549), (853, 556), (840, 574)], 2)
    C_, R_ = (840.0, 588.0), 14.0
    arc = [(C_[0] + R_ * math.cos(a_), C_[1] + R_ * math.sin(a_)) for a_ in np.linspace(-math.pi / 2, -3 * math.pi / 2, 21)]
    tail = [(854.0, 602.5), (862.0, 603.5)]
    pl = [J] + sm_ + arc[1:] + tail
    pc = (872.0, 604.5)
    poly = [(pc[0] + 11.0 * math.cos(a_), pc[1] + 8.5 * math.sin(a_)) for a_ in np.linspace(0, 2 * math.pi, 28, endpoint=False)]
    pocket = {'centre': rnd2(pc), 'poly': [rnd2(q) for q in poly], 'size_m': [22.0, 17.0], 'height_m': VIEWB_POCKET_M, 'surface': 'gravel_SK1d',
              'view': 'open to the south / south-east (city, bay); low stone parapet on the south rim, VIEW B sign',
              'turnaround': 'van 5.5 x 2.1 m: 3-point turn in 22 x 17 m', 'hairpin': {'centre': list(C_), 'radius_m': R_},
              'spur_length_m': round(plen(pl), 1)}
    return pl, pocket


def snap_ends():
    """Joins: an end within 6 m of another road's END continues it (moved onto that end point); otherwise an end within 6 m of
    another road's axis becomes a T-join (moved onto the axis). Roads are processed in order; joined ends are not moved again."""
    report, locked = [], set()
    for r in ROADS:
        if r.get('ends') == 'fixed':
            locked.add((r['id'], 0)); locked.add((r['id'], -1))
    for r in ROADS:
        pts = [tuple(p) for p in r['points']]
        for end in (0, -1):
            if (r['id'], end) in locked:
                continue
            p = pts[end]
            best = None
            for o in ROADS:
                if o['id'] == r['id'] or o['kind'] == 'tunnel':
                    continue
                opl = [tuple(q) for q in o['points']]
                for oe in (0, -1):
                    d = math.dist(p, opl[oe])
                    if d < 6.0 and (best is None or best[0] != 'end' or d < best[1]):
                        best = ('end', d, opl[oe], o['id'], oe)
                if best is None or best[0] != 'end':
                    d, q, i, t = nearest_on(opl, p)
                    if d < 6.0 and (best is None or d < best[1]):
                        best = ('axis', d, q, o['id'], None)
            if best and math.dist(best[2], pts[-1 - end]) < 6.0:
                best = None                                                 # would collapse this (short) road onto itself
            if best and best[1] > 0.05:
                pts[end] = best[2]
                report.append((r['id'], 'start' if end == 0 else 'end', best[0], best[3], round(best[1], 2)))
            if best:
                locked.add((r['id'], end))
                if best[0] == 'end':
                    locked.add((best[3], best[4]))
        r['points'] = [rnd2(p) for p in pts]
    return report


def main():
    svg = svg_roads()
    E = {z['id']: z for z in D['downtown']['zones'] if z['kind'] == 'entry'}
    V37 = str(D['downtown'].get('version', '')).startswith('W86')               # Downtown plan v37 (A3, 22.10)

    # 1 main road Hamlet -> Construction -> Downtown west entry (R24), joined to the carriageway edge of street W1
    pl = pick(svg, 'R24_roads', (496, 348), (813, 320))
    e = E['05-entry-W']
    pl = clip_from(pl, (e['pos'][0] - 12, 320.0), 'before')
    pl = straighten_end(pl, tuple(e['axis_point']), (1.0, 0.0), 18.0)
    add('main_hamlet_downtown', 'rural_asphalt', pl, 6.4, 'asphalt_A5d12', 'SVG R24 (ROAD_H) + Downtown entry W', dt_entry='05-entry-W')
    fix('main_hamlet_downtown', e['axis_point'], 'Дорога с запада доведена полотном до кромки проезжей части улицы W1 (без светлой обочины внутри улицы), последние 18 м прямо по оси.',
        'v10 §6: въезд в Даунтаун — полотно до проезжей части, бордюр понижен.')
    # 1b short link from the Hamlet main street onto the land bridge (L05 main_bridge_construction)
    add('hamlet_main_link', 'rural_asphalt', pick(svg, 'L05_roads', (491, 348), (496, 348)), 6.4, 'asphalt_A5d12', 'SVG L05 main_bridge_construction (land bridge over the river)')
    # 2 Hamlet bypass (R52 == R24 copy: built once)
    add('hamlet_bypass', 'rural_asphalt', pick(svg, 'R52_bypass', (496, 348), (505, 573)), 6.4, 'asphalt_A5d12', 'SVG R52_bypass (ROAD_BN; R24 copy dropped)')
    fix('hamlet_bypass', (463, 460), 'Объездная Хутора есть на карте дважды (слои R52 и R24) — построена один раз.', 'Две одинаковые полосы одна поверх другой — артефакт рисования.')
    # 3 Quiet Valley road: R24 (530,347)->(543,297) + bridge + district_08 -> valley gate; one continuous road (v10 §5: through the bridge)
    a = pick(svg, 'R24_roads', (530, 347), (543, 297))
    b = zline('quiet_valley', '08-asphalt-main')
    pl = a[:-1] + b
    add('to_quiet_valley', 'rural_asphalt', pl, 6.4, 'asphalt_A5d12', 'SVG R24 ROAD_VALLEY + quiet_valley 08-asphalt-main', ends_dead='Quiet Valley beach gate',
        bridge={'from': [543.0, 310.0], 'to': [543.0, 292.0], 'kind': 'road_bridge', 'deck_w_m': 8.8, 'rails': True, 'over': 'river'})
    add('valley_lab_spur', 'drive', zline('quiet_valley', '08-asphalt-lab') + zline('quiet_valley', '08-base5-drive')[1:], 4.8, 'asphalt_A5d12',
        'quiet_valley 08-asphalt-lab + 08-base5-drive (base 5)', ends_dead='base 5 garage pad')
    # 4 Construction gate drive (15 m, gate ~19 m in the single fence)
    add('construction_gate', 'drive', pick(svg, 'R24_roads', (600, 348), (600, 363))[::-1][::-1], 6.4, 'asphalt_A5d12', 'SVG R24 ROAD_CONSTR', ends_dead='Construction main gate')
    # 5 Hamlet -> Rough (R24 ROAD_R) and the west link of the ring (ROAD_RING)
    add('hamlet_to_rough', 'rural_asphalt', pick(svg, 'R24_roads', (505, 573), (666, 674)), 6.4, 'asphalt_A5d12', 'SVG R24 ROAD_R (over the land bridge y 572)')
    add('rough_west_link', 'rural_asphalt', pick(svg, 'R24_roads', (686, 788), (666, 674))[::-1], 6.4, 'asphalt_A5d12', 'SVG R24 ROAD_RING')
    # 6 Rough ring (district data, old asphalt with kerb) and the link to the port (SVG R85 east of the ring) -> port road -> bridge
    ring = zline('rough', '04-ring-road')
    add('rough_ring', 'district_ring', ring, 6.4, 'asphalt_old_SK2a', 'rough 04-ring-road (plan v52)', kerb=True)
    r85 = pick(svg, 'R85_rough_ring', (666, 718), (1188, 633))
    port = zline('port', '06-port-road')
    tail = clip_from(r85, ring[-1], 'after')
    tail = clip_from(tail, port[0], 'before')
    add('rough_to_port', 'rural_asphalt', tail, 6.4, 'asphalt_A5d12', 'SVG R85 (east of the Rough ring) up to the port road')
    add('port_road', 'rural_asphalt', port, 6.4, 'asphalt_A5d12', 'port 06-port-road (through the port, no step)')
    br = zone('tramduro', '10-bridge')
    add('bridge_tramduro', 'bridge', [tuple(p) for p in br['line']], 8.8, 'asphalt_A5d12', 'tramduro 10-bridge (real bridge on piers)',
        carriageway_m=6.4, pier_step_m=br.get('pier_step_m', 20.9), ends='fixed')
    # 7 tunnel under hill B with its approaches
    add('tunnel_north_approach', 'rural_asphalt', zline('rough', '04-exit-tunnel'), 6.4, 'asphalt_A5d12', 'rough 04-exit-tunnel (TUN_N)')
    tun = pick(svg, 'R33_tunnel', (748, 649), (872, 492))
    e = E['05-entry-N-tunnel']
    if V37:
        far, appr, rmin, P = smooth_join(tun, tuple(e['axis_point']), (0.0, -1.0), Ls=26.0, Lb=22.0)
        cut = plen(tun) - plen(far)
        add('tunnel', 'tunnel', far, 7.0, 'asphalt_A5d12', 'SVG R33_tunnel (TUN axis), south portal moved up the axis (Downtown v37)', ends='fixed',
            portal_south=rnd2(P), shortened_m=round(cut, 1))
        add('tunnel_south_approach', 'rural_asphalt', appr, 6.4, 'asphalt_A5d12', 'tunnel portal -> Downtown v37 entry N-tunnel (T on N0w)',
            dt_entry='05-entry-N-tunnel', bend_min_radius_m=rmin, straight_m=26.0)
        fix('tunnel', P, 'Даунтаун v37 вырос на ~50 м на север: старый южный портал тоннеля (871.9, 492.3) внутри квартала NW0. Ось тоннеля та же, '
                         'южный портал перенесён вверх по оси в (%.1f, %.1f), тоннель короче на %.0f м; выезд — плавный поворот (R мин. %.0f м) и прямой '
                         'подход 26 м в Т-примыкание к верхней улице N0w (x %.0f).' % (P[0], P[1], cut, rmin, e['axis_point'][0]),
            'v10 §6: примыкание под прямым углом, прямой подход 10–20 м; рельеф: портал у нового подножия холма B (A1).')
    else:
        add('tunnel', 'tunnel', tun, 7.0, 'asphalt_A5d12', 'SVG R33_tunnel (TUN axis)', ends='fixed')
        pl = pick(svg, 'R24_roads', (872, 492), (880, 442))
        pl = clip_from(pl, (e['pos'][0], e['pos'][1] + 10), 'before')
        pl = straighten_end(pl, tuple(e['axis_point']), (0.0, -1.0), 16.0)
        add('tunnel_south_approach', 'rural_asphalt', pl, 6.4, 'asphalt_A5d12', 'SVG R24 TUN_S + Downtown entry N (tunnel)', dt_entry='05-entry-N-tunnel')
        fix('tunnel_south_approach', e['axis_point'], 'Выезд из тоннеля приходил на 2,7 м западнее оси улицы Vn — последние 16 м выпрямлены по оси Vn.',
            'v10 §6: ось боковой дороги доходит до оси главной, прямой подход 10–20 м.')
    # 8 serpentine to VIEW B (12 %, Fedya 18.10) from the ring to the Downtown entry N3
    e = E['05-entry-N-viewB']
    pl = pick(svg, 'R24_roads', (945, 671), (1090, 442))
    if V37:
        far, appr, rmin, P = smooth_join(pl, tuple(e['axis_point']), (0.0, -1.0), Ls=23.0, Lb=40.0)
        pl = far[:-1] + appr
        fix('serpentine_view_b', P, 'Даунтаун v37: серпантин VIEW B обрезан у нового верхнего кольца и плавно (R мин. %.0f м) заведён в Т-примыкание к N0c '
                                    '(x %.0f), прямой подход 23 м; старый конец (N3 у OB1) теперь внутри города.' % (rmin, e['axis_point'][0]),
            'v10 §6: примыкание под прямым углом, прямой подход 10–20 м.')
    else:
        pl = clip_from(pl, (e['pos'][0], e['pos'][1] + 12), 'before')
        pl = straighten_end(pl, tuple(e['axis_point']), (0.0, -1.0), 15.0)
    vb = post((1010, 594))
    add('serpentine_view_b', 'serpentine', pl, 6.4, 'asphalt_A5d12', 'SVG R24 ROAD_S (v85: smooth start at the ring)', dt_entry='05-entry-N-viewB',
        viewpoint=rnd2(vb), max_grade=0.12, berm={'height_m': [1.0, 1.5], 'side': 'outer', 'note': 'v10 §3.2: low earth berm, view open, no 15 m cut'})
    # 8b VIEW B viewpoint spur (W86, Fedya 22.10 "VIEW B ~+46 m, view to the city and the bay"): the pass road stays low over the saddle;
    # a dead-end spur leaves it at the pass top (T-join, 12 m straight), climbs <= 12 % along the south shoulder of hill B, turns in ONE
    # hairpin (R 12.5 m, van 5.5 x 2.1 m) at the west end of the summit knob (on the hill body, ~20 m above the tunnel axis, >= 26 m from
    # the south portal) and runs east along the summit ridge into a 22 x 17 m turnaround pocket at ~45.5 m, open to the south (city, bay)
    spur, pocket = view_b_spur(pl)
    add('view_b_spur', 'serpentine', spur, 5.0, 'asphalt_A5d12', 'W86 VIEW B viewpoint spur (lead 22.10: pass road low, spur up to the crest)',
        ends_dead='VIEW B viewpoint pocket (turnaround)', max_grade=0.12, climb_to_m=VIEWB_POCKET_M, pocket=pocket,
        berm={'height_m': [1.0, 1.25], 'side': 'outer', 'note': 'low earth berm with stones on the outer (downhill) side only; none in the hairpin'},
        notes='climb profile: pass-road height at the T-join + 11.5 % up to the pocket height, then flat (s03 climb_to_m); the hill is shaped to the road '
              '(bench <= 2-3 m uphill, berm outside)')
    fix('view_b_spur', pocket['centre'], 'Смотровая VIEW B: перевальная дорога осталась низкой (~17 м), от её верхней точки — тупиковый отворот %.0f м '
                                         '(≤ 12 %%, один разворот R 12,5 м) на гребень холма B к смотровому карману 22 × 17 м на ~%.1f м с видом на город и бухту'
        % (pocket['spur_length_m'], VIEWB_POCKET_M), 'Федя 22.10: VIEW B ~+46 м с видом на город и бухту; перевал на 46 м требовал ~700 м дороги и стен')
    # 9 cornice VIEW C: Downtown NE entry -> T into the port road
    e = E['05-entry-NE-viewC']
    pl = pick(svg, 'R24_roads', (1243, 403), (1263, 633))[::-1]                 # from the port T down to Downtown
    if V37:
        far, appr, rmin, P = smooth_join(pl, tuple(e['axis_point']), (0.0, -1.0), Ls=23.0, Lb=25.0)
        pl = far[:-1] + appr
        fix('cornice_view_c', P, 'Даунтаун v37: начало карниза VIEW C (верх E1) теперь внутри города (квартал NEB / E1); дорога обрезана у верхнего '
                                 'кольца и плавно (R мин. %.0f м) заведена в Т-примыкание к N0e (x %.0f), прямой подход 23 м.' % (rmin, e['axis_point'][0]),
            'v10 §6: каждая дорога куда-то ведёт, примыкание под прямым углом.')
    else:
        pl = clip_from(pl, (e['pos'][0], e['pos'][1] + 12), 'before')
        pl = straighten_end(pl, tuple(e['axis_point']), (0.0, -1.0), 15.0)
    cT = zline('port', '06-cornice-T')                                       # last 46 m straightened onto the port road (coast step)
    d0, q0, i0, t0 = nearest_on(pl, cT[0])
    pl = cT[::-1] + pl[i0 + 1:] if math.dist(cT[0], pl[0]) > math.dist(cT[-1], pl[0]) else pl
    add('cornice_view_c', 'rural_asphalt', pl, 6.4, 'asphalt_A5d12', 'SVG R24 ROAD_C + port 06-cornice-T', dt_entry='05-entry-NE-viewC', viewpoint=rnd2(post((1194, 532))))
    # 10 border KPP road (through the checkpoint gate; beyond it the road just follows the steppe)
    add('border_checkpoint_road', 'rural_asphalt', zline('rough', '04-kpp-road'), 6.4, 'asphalt_old_SK2a', 'rough 04-kpp-road (ROAD_N)', ends_dead='KPP gate / steppe edge', follow_ground_north=True)
    # 11 Elite stone road (half ring, data heights +5 -> +44 at the east gate)
    ez = zone('elite', '07-stone-road')
    add('elite_stone_road', 'stone_serpentine', [tuple(p) for p in ez['line']], 4.5, 'cobble_SK2c', 'elite 07-stone-road (plan v12)',
        heights_abs=ez.get('h_abs'), heights_abs_s=[round(v, 2) for v in np.concatenate([[0], np.cumsum(np.hypot(*np.diff(np.array(ez['line'], float), axis=0).T))])],
        parapet='outer', lamps_every_m=ez.get('lamps_every_m', 18),
        dt_entry='05-entry-E', ends='fixed')
    # 12 beach van ruts to the Elite beach
    add('beach_van_track', 'sand_track', zline('beach', '09-van-track-elite'), 5.0, 'sand_ruts', 'beach 09-van-track-elite', ends='fixed')
    # 13 forest / valley dirt roads (district data, shared)
    for rid in ('01-road-hamlet', '01-road-wagon-east', '01-road-east', '01-link-bypass', '01-link-hamlet'):
        add('forest_' + rid[3:].replace('-', '_'), 'dirt', zline('forest', rid), 5.4, 'dirt_SK1b', 'forest ' + rid, ruts=True)
    add('forest_to_valley', 'dirt', zline('quiet_valley', '08-dirt-from-forest'), 5.4, 'dirt_SK1b', 'quiet_valley 08-dirt-from-forest (outside the fence)', ruts=True)
    joins = snap_ends()
    # dangling-end report: an end must touch another road axis (<= 0.5 m), a Downtown entry, or be an approved dead end
    axes = {r['id']: [tuple(p) for p in r['points']] for r in ROADS}
    ends = []
    for r in ROADS:
        for end in (0, -1):
            p = tuple(r['points'][end])
            dmin = min((nearest_on(opl, p)[0] for oid, opl in axes.items() if oid != r['id']), default=99)
            ok = dmin < 0.6 or r.get('dt_entry') or r.get('ends_dead') or r.get('ends') == 'fixed' or 'hamlet' in r['id']
            ends.append({'road': r['id'], 'end': 'start' if end == 0 else 'end', 'pos': rnd2(p), 'nearest_axis_m': round(dmin, 2), 'ok': bool(ok)})
    save_json('roads_v85.json', {'units': 'm, world v85 (x east, y north); Unity X = x, Z = y', 'roads': ROADS, 'joins_snapped': joins, 'ends': ends,
                                 'rules': 'v10 §6: continuous surface, T / radius joins, straight approach 10-20 m, no dangling ends, no road through a fence; grade <= 8 % '
                                          'except VIEW B serpentine 12 % and the Elite stone road (data heights, <= 15 %)',
                                 'fixes': FIXES})
    bad = [e_ for e_ in ends if not e_['ok']]
    print(len(ROADS), 'roads; joins', joins)
    print('unresolved ends', bad)
    water()
    border_and_features()


# ------------------------------------------------------------------ water (vectors; v76 used raster blobs)
def water():
    s = c.svg_text()
    river, banks, lake = [], [], None
    plunge = None
    for nm, at, M, gids, a, b in c.svg_tags(s):
        g = gids[-1] if gids else ''
        if g not in ('L04_water', 'R38_river_mouth'):
            continue
        st, w = c.attr(at, 'stroke'), c.attr(at, 'stroke-width')
        if nm == 'polyline' and st == '#97C8DC':
            pts = [c.u2w(*p) for p in c.points_of(at, M)]
            river.append((pts, float(w) / 5.0))
        elif nm == 'polyline' and st == '#C3DCCB':
            banks.append(float(w) / 5.0)
        elif nm == 'polygon' and c.attr(at, 'fill') == '#97C8DC':
            lake = [c.u2w(*p) for p in c.points_of(at, M)]
        elif nm == 'circle' and c.attr(at, 'fill') == '#97C8DC':
            cx, cy = c.apply(M, (c.num(at, 'cx'), c.num(at, 'cy')))
            plunge = (c.u2w(cx, cy), c.num(at, 'r') / 5.0)
    axis, widths = [], []
    for pts, w in river:                                                    # ordered from the mountain lake to the sea
        for p in (pts if not axis else pts[1:]):
            axis.append(p)
            widths.append(w)
    bodies = [{'id': 'river', 'kind': 'river', 'axis': [rnd2(p) for p in axis], 'width_m': [round(w, 2) for w in widths],
               'depth_m': 1.4, 'flow': True, 'gorge_depth_m': [6, 13], 'disposal': 'River',
               'note': 'one river: mountain lake -> waterfall -> gorge -> Hamlet (2 natural land bridges) -> road bridge to the Quiet Valley -> gorge between grey rocks -> waterfall into the sea'}]
    if lake:
        bodies.append({'id': 'mountain_lake', 'kind': 'lake', 'outline': [rnd2(p) for p in lake], 'depth_m': 4.0, 'disposal': 'Lake',
                       'note': 'at the foot of the ridge, waterfall into the river (no trail)'})
    if plunge:
        (px, py), r_ = plunge
        bodies.append({'id': 'plunge_pool', 'kind': 'lake', 'outline': [rnd2((px + r_ * math.cos(t), py + r_ * math.sin(t))) for t in np.linspace(0, 2 * math.pi, 24, endpoint=False)],
                       'depth_m': 2.0, 'disposal': 'Lake', 'note': 'pool under the mountain waterfall'})
    for dn, zid, kind, disp in (('forest', '01-lake', 'lake', 'Lake'), ('forest', '01-swamp', 'swamp', 'Bog'), ('hamlet', '02-A-POND', 'pond', 'Pond')):
        z = zone(dn, zid)
        bodies.append({'id': zid, 'kind': kind, 'outline': z['poly'], 'depth_m': {'lake': 3.0, 'swamp': 0.6, 'pond': 1.5}[kind], 'disposal': disp,
                       'note': z.get('notes', '')})
    bodies.append({'id': 'waterfall_mountain', 'kind': 'waterfall', 'at': rnd2(axis[min(len(axis) - 1, 4)]), 'top_m': 8.0, 'note': 'from the mountain lake into the river gorge'})
    bodies.append({'id': 'waterfall_sea', 'kind': 'waterfall', 'at': rnd2(axis[-1]), 'top_m': 9.0, 'note': 'river falls straight into the sea at the Quiet Valley'})
    bodies.append({'id': 'sea', 'kind': 'sea', 'level_m': 0.0, 'material': 'Sea_trial_calm_v09', 'disposal': 'Sea (no)'})
    save_json('water_v85.json', {'units': 'm, world v85', 'bodies': bodies,
                                 'disposal_rule': 'corpse disposal works in River / Lake (WaterQuery); Pond, Bog, Pool, Sea do not (canon); no canal since v38'})
    print('water: river axis', len(axis), 'pts, widths', round(min(widths), 1), '..', round(max(widths), 1), 'm; bodies', [b['id'] for b in bodies])


# ------------------------------------------------------------------ border + relief features (build_world_v85 constants, pre-shift -> post)
def coast_y(x):
    return 908 + 7 * math.sin(x / 41.0) + 5 * math.sin(x / 13.0 + 1.3) if 540 <= x <= 1060 else 9999


def border_and_features():
    north = [z for z in D['rough']['zones'] if z.get('scope') == 'north_border'] + [p for p in D['rough']['props'] if p.get('scope') == 'north_border'] + \
        [b for b in D['rough']['buildings'] if b.get('scope') == 'north_border']
    fence = [post((x, coast_y(x) + 2)) for x in range(572, 1031, 4)]
    border = {'built_by_district': 'rough' if north else None, 'district_items': [x['id'] for x in north],
              'fence_line': [rnd2(p) for p in fence], 'invisible_wall_height_m': 60.0,
              'note': 'fence, towers, KPP building, sliding gate and the Leave-the-country button are in rough_v85.json (scope north_border); '
                      'the builder adds only the invisible wall along fence_line, past the ends, and the far steppe',
              'steppe': {'rises_to_horizon_m': 18.0}, 'right_ridge_crest': [rnd2(post(p)) for p in [(1046, 884), (1062, 893), (1078, 908), (1092, 930)]]}
    save_json('border_v85.json', border)
    P = lambda pts: [rnd2(post(p)) for p in pts]
    feats = {
        'hill_B': {'crest': P([(752, 556), (840, 574), (920, 590), (1000, 586), (1080, 574), (1150, 562)]), 'half_width_m': 58, 'peak_m': 50},
        'view_B': rnd2(post((1010, 594))), 'view_C': rnd2(post((1194, 532))),
        'view_B_pocket': next((r['pocket'] for r in ROADS if r['id'] == 'view_b_spur'), None),
        'tunnel_axis': next(r['points'] for r in ROADS if r['id'] == 'tunnel'),
        'land_bridges': [{'centre': rnd2(post(p)), 'rx_m': 14, 'ry_m': 15} for p in [(484, 349), (488, 572)]],
        'small_ridge': {'poly': P([(436, 826), (466, 818), (498, 822), (528, 836), (552, 856), (570, 878), (574, 896), (558, 906), (530, 904), (502, 896), (478, 886), (452, 877), (436, 872)]),
                        'crest': P([(440, 846), (476, 852), (510, 865), (540, 880), (562, 894)]), 'top_m': [92, 56]},
        'ridge_ext': {'crest': P([(500, 850), (540, 856), (580, 862), (612, 866), (632, 866)]), 'top_m': [92, 46], 'east_cliff_x': 643},
        'ridge_north': {'crest': P([(566, 864), (556, 900), (548, 950)]), 'top_m': 96},
        'right_ridge': {'poly': P([(1026, 906), (1034, 891), (1050, 880), (1066, 883), (1080, 896), (1092, 912), (1100, 930), (1030, 930)]),
                        'crest': P([(1046, 884), (1062, 893), (1078, 908), (1092, 930)]), 'top_m': 32},
        'border_forest': P([(512, 782), (560, 790), (598, 800), (626, 816), (640, 840), (642, 862), (630, 874), (608, 874), (584, 862), (556, 848), (530, 834), (512, 826)]),
        'foot_x': '505 + 6 sin(y / 17)',
        'quiet_valley_rocks': P([(616, 88), (632, 84), (634, 104), (645, 138), (668, 170), (688, 190), (698, 214), (692, 246), (674, 276), (652, 292), (638, 268), (630, 205), (628, 140), (620, 90)]),
        'elite': {'centre': rnd2(post((1398.2, 349.5))), 'half': [72.5, 58.8], 'plateau_m': [40, 44]},
        'construction_hill': {'rel_m': 8.0, 'site': zone('construction', next(z['id'] for z in D['construction']['zones'] if z['kind'] == 'ground'))['poly'],
                              'gate': [600.0, 363.0], 'rings_m': [13, 26]}}
    save_json('features_v85.json', feats)


if __name__ == '__main__':
    main()
