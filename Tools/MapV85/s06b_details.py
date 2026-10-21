"""Step 6b (v85): small details BY RULES (handoff v10 §8) — not the dots of the picture.

 - Downtown street lamps: every ~30 m at the kerb edge of the sidewalk (0.7 m from the kerb), sides staggered, at every junction
   corner pair; boulevard = double lamps; never on a carriageway, curb drop / entry, door, arch or alley mouth.
 - hydrants at block corners (one or two diagonal corners per junction); traffic lights at the junctions the Downtown plan marks
   (control = lights) and at the plaza; stop / give-way signs on the minor approach of T-joins, facing their traffic.
 - parked cars parallel to the kerb in groups of 2-4, never within 14 m of a junction, entry, curb drop, arch, base 13 or a door
   with a garage / roll shutter; ~35 % of the free kerb length.
 - benches at podyezds (Rough: the plan's bench count per door) with a bin next to each group; garbage containers at the end of every
   Downtown dead-end alley and in the service yards.
 - give-way signs on world-road T-joins (rural).
Everything gets grip_anchor where the canon lists it (lamps, signs, lights, hydrants, benches, rails).
Output: details_v85.json (props for the builder: kind, pos, rot_deg (0 = +x, CCW), grip_anchor, district).
"""
import math

import common as c
from common import load_json, save_json, rnd2, nearest_on, resample, inside

D = {n: load_json('districts/%s_v85.json' % n) for n in
     ('beach', 'construction', 'downtown', 'elite', 'forest', 'hamlet', 'port', 'quiet_valley', 'rough', 'tramduro')}
OUTP = []


def put(kind, p, rot, district, grip=False, **kw):
    OUTP.append(dict(kind=kind, pos=rnd2(p), rot_deg=round(rot % 360, 1), grip_anchor=grip, district=district, **kw))


def ang(v):
    return math.degrees(math.atan2(v[1], v[0]))


def main():
    dt = D['downtown']
    streets = [z for z in dt['zones'] if z['kind'] == 'street']
    junctions = [z for z in dt['zones'] if z['kind'] == 'junction']
    blds = [b['footprint'] for b in dt['buildings']]
    blockers = []                                                          # points / polys where no kerb furniture may stand
    for z in dt['zones']:
        if z['kind'] in ('curb_drop', 'arch', 'entry', 'taxi_stand', 'gas_station', 'underground_parking', 'service_yard'):
            if z.get('poly'):
                blockers.append(('poly', z['poly']))
            elif z.get('pos'):
                blockers.append(('pt', z['pos']))
    for b in dt['buildings']:
        for e in b.get('entrances', []):
            blockers.append(('door', e['pos'], e.get('kind', 'door')))
    for z in dt['zones']:
        if z['kind'] in ('dead_end_alley', 'dead_end_alley_pair') and z.get('poly'):
            blockers.append(('poly', z['poly']))

    def blocked(p, r=3.0):
        for bk in blockers:
            if bk[0] == 'poly':
                if inside(p, bk[1]) or nearest_on(bk[1] + [bk[1][0]], p)[0] < r:
                    return True
            elif bk[0] == 'pt':
                if math.dist(p, bk[1]) < r + 4:
                    return True
            else:
                big = bk[2] in ('garage_gate', 'rollshutter', 'gate', 'arch')
                if math.dist(p, bk[1]) < (r + (6 if big else 1.5)):
                    return True
        return False

    def on_carriageway(p):
        for s in streets:
            if nearest_on([tuple(q) for q in s['poly_line']], p)[0] < s['carriageway_m'] / 2 + 0.2:
                return True
        return False

    def in_building(p, m=0.4):
        return any(inside(p, fp) or nearest_on(fp + [fp[0]], p)[0] < m for fp in blds)

    nl = nh = nc = nt = 0
    for s in streets:
        pl = [tuple(q) for q in s['poly_line']]
        cw, sw = s['carriageway_m'], s['sidewalk_m']
        L = c.plen(pl)
        step = 30.0
        k = 0
        acc = 6.0
        pts = resample(pl, 1.0)
        cum = [0.0]
        for a, b in zip(pts[:-1], pts[1:]):
            cum.append(cum[-1] + math.dist(a, b))
        lamp = 'lamp_oldtown_double' if s.get('boulevard') else 'lamp_oldtown_single'
        while acc < L - 6.0:
            i = min(range(len(cum)), key=lambda j: abs(cum[j] - acc))
            a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
            d = (b[0] - a[0], b[1] - a[1])
            ln = math.hypot(*d) or 1
            n = (-d[1] / ln, d[0] / ln)
            side = 1 if k % 2 == 0 else -1
            p = (pts[i][0] + n[0] * side * (cw / 2 + 0.7), pts[i][1] + n[1] * side * (cw / 2 + 0.7))
            if not on_carriageway(p) and not blocked(p, 2.0) and not in_building(p):
                put(lamp, p, ang((-n[0] * side, -n[1] * side)), 'downtown', True, street=s['id'])
                nl += 1
            k += 1
            acc += step
        # parked cars along the kerb: groups of 2-4, both sides
        for side in (1, -1):
            acc = 14.0
            g = 0
            while acc < L - 14.0:
                h_ = c.h01('%s%d%d' % (s['id'], side, int(acc)))
                if h_ < 0.35:
                    ncar = 2 + int(c.h01('n%s%d%d' % (s['id'], side, int(acc))) * 3)
                    span = []
                    for q in range(ncar):
                        s_ = acc + q * 5.6
                        i = min(range(len(cum)), key=lambda j: abs(cum[j] - s_))
                        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
                        d = (b[0] - a[0], b[1] - a[1])
                        ln = math.hypot(*d) or 1
                        n = (-d[1] / ln, d[0] / ln)
                        p = (pts[i][0] + n[0] * side * (cw / 2 - 1.2), pts[i][1] + n[1] * side * (cw / 2 - 1.2))
                        span.append((p, ang(d) + (180 if side < 0 else 0)))
                    ok = all(not blocked(p, 6.0) for p, _ in span) and all(
                        min(math.dist(p, j['pos']) for j in junctions) > 14.0 for p, _ in span)
                    if ok:
                        for q, (p, r) in enumerate(span):
                            kind = ('car_sedan_beige', 'car_sedan_blue', 'car_sedan_green', 'car_sedan_red', 'car_hatchback')[int(c.h01('%s%.1f%.1f' % (s['id'], p[0], p[1])) * 5) % 5]
                            put(kind, p, r, 'downtown', False, street=s['id'])
                            nc += 1
                        acc += ncar * 5.6 + 10.0
                        continue
                acc += 12.0
                g += 1
    for j in junctions:
        cx, cy = j['pos']
        corners = [(cx + sx * 8.2, cy + sy * 8.2) for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
        pick = int(c.h01(j['id']) * 4)
        for q, p in enumerate(corners):
            if on_carriageway(p) or in_building(p) or blocked(p, 1.5):
                continue
            if q in (pick, (pick + 2) % 4):
                put('fire_hydrant', p, 45 + 90 * q, 'downtown', True, junction=j['id'])
                nh += 1
            if j.get('control') in ('lights', 'traffic_light') and q in ((pick + 1) % 4, (pick + 3) % 4):
                put('traffic_light', p, 225 + 90 * q, 'downtown', True, junction=j['id'])
                nt += 1
        if j.get('control') in ('stop', 'giveway') and j.get('type') == 'T':
            legs = j.get('legs_deg') or []
            if legs:
                # the leg that has no opposite = minor approach
                minor = next((l for l in legs if not any(abs(((l - o + 180) % 360) - 180) > 170 for o in legs if o != l)), legs[-1])
                a = math.radians(minor)
                p = (cx + math.cos(a) * 12.0 - math.sin(a) * 7.0, cy + math.sin(a) * 12.0 + math.cos(a) * 7.0)
                if not on_carriageway(p) and not in_building(p):
                    put('sign_stop' if j['control'] == 'stop' else 'sign_giveway', p, minor, 'downtown', True, junction=j['id'])
    # garbage containers at dead ends + service yards
    for z in dt['zones']:
        if z['kind'] in ('dead_end_alley', 'dead_end_alley_pair', 'service_yard') and z.get('poly'):
            P = z['poly']
            cxy = c.centroid(P)
            put('garbage_container_closed', cxy, 0, 'downtown', False, zone=z['id'])
            put('garbage_container_open', (cxy[0] + 2.2, cxy[1]), 0, 'downtown', False, zone=z['id'])
    # Rough: benches at podyezds (plan count), a bin next to each group
    nb = 0
    for b in D['rough']['buildings']:
        for e in b.get('entrances', []):
            n_ = int(e.get('benches') or 0)
            if n_ <= 0:
                continue
            f = math.radians(e.get('facing_deg', 0))
            out = (math.cos(f), math.sin(f))
            along = (-out[1], out[0])
            for q in range(n_):
                sgn = 1 if q % 2 == 0 else -1
                p = (e['pos'][0] + out[0] * 2.4 + along[0] * sgn * (2.0 + 1.9 * (q // 2)), e['pos'][1] + out[1] * 2.4 + along[1] * sgn * (2.0 + 1.9 * (q // 2)))
                put('bench_soviet' if c.h01(b['id'] + str(q)) > .25 else 'bench_soviet_broken', p, math.degrees(f) + 90, 'rough', True, door=b['id'])
                nb += 1
            p = (e['pos'][0] + out[0] * 2.4 + along[0] * 3.6, e['pos'][1] + out[1] * 2.4 + along[1] * 3.6)
            put('trashbin_concrete', p, 0, 'rough', False, door=b['id'])
    # world-road T-joins (rural): give-way sign on the minor road, 8 m before the join, right side
    roads = load_json('roads_v85.json')
    byid = {r['id']: r for r in roads['roads']}
    ns = 0
    tjoins = []
    for r in roads['roads']:
        if r['kind'] in ('tunnel', 'bridge', 'sand_track', 'dirt'):
            continue
        for end in ('start', 'end'):
            p = tuple(r['points'][0 if end == 'start' else -1])
            for o in roads['roads']:
                if o['id'] == r['id'] or o['kind'] in ('tunnel',):
                    continue
                opl = [tuple(q) for q in o['points']]
                d, q, i, t = nearest_on(opl, p)
                if d < 0.8 and min(math.dist(p, opl[0]), math.dist(p, opl[-1])) > 8.0:
                    tjoins.append((r['id'], end))
                    break
    for rid, end in tjoins:
        r = byid[rid]
        pl = [tuple(p) for p in r['points']]
        if end == 'end':
            pl = pl[::-1]
        p0, p1 = pl[0], pl[min(len(pl) - 1, 4)]
        d = (p1[0] - p0[0], p1[1] - p0[1])
        ln = math.hypot(*d) or 1
        d = (d[0] / ln, d[1] / ln)
        right = (d[1], -d[0])                                                # traffic towards the join, keeps right
        p = (p0[0] + d[0] * 8.0 - right[0] * (r['width_m'] / 2 + 1.0), p0[1] + d[1] * 8.0 - right[1] * (r['width_m'] / 2 + 1.0))
        put('sign_giveway', p, ang((-d[0], -d[1])), 'world', True, road=rid)
        ns += 1
    save_json('details_v85.json', {'rules': 'handoff v10 §8 (see Tools/MapV85/s06b_details.py docstring)', 'props': OUTP,
                                   'counts': {'downtown_lamps': nl, 'hydrants': nh, 'parked_cars': nc, 'traffic_lights': nt, 'rough_benches': nb, 'rural_signs': ns,
                                              'total': len(OUTP)}})
    print({'downtown_lamps': nl, 'hydrants': nh, 'parked_cars': nc, 'traffic_lights': nt, 'rough_benches': nb, 'rural_signs': ns, 'total': len(OUTP)})


if __name__ == '__main__':
    main()
