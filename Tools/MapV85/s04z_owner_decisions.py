"""Step 4z (v85): owner decisions applied on top of the district ports (run after s04_*, before s05).

Fedya 21.10.2026: only TWO skyscrapers on the whole map — the T4 twins on the Water-axis plaza (texture sample, builder step).
 - the round glass corner tower of the Downtown legend (DOWNTOWN_LEGEND_v26 "Особые дома": round glass tower at the corner, centre
   (350; 49) plan m, Ø 18.4 m; W85 ids 05-B018 tower + 05-B017 its glass podium) is replaced by a normal Downtown block on the podium
   footprint: corner house, 8 floors (5-8 + corner), stucco, storefront ground floor (D4 style later); noted for Vadim;
 - no other tower-type building: the glass offices 05 / 06 (legend) are capped at 8 floors like the rest of Downtown (were 10).
Idempotent.
"""
import common as c
from common import load_json, save_json, rnd2

DT = 'districts/downtown_v85.json'


def main():
    d = load_json(DT)
    by = {b['id']: b for b in d['buildings']}
    log = []
    if '05-B018' in by or by.get('05-B017', {}).get('kind') == 'podium_round':
        pod = by.get('05-B017')
        xs = [p[0] for p in pod['footprint']]
        ys = [p[1] for p in pod['footprint']]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        fp = [rnd2(p) for p in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        # door on the side facing the nearest street (N3 north of it, Vd east of it)
        streets = {z['id']: z for z in d['zones'] if z['kind'] == 'street'}
        best = None
        for sid, z in streets.items():
            dd, q, i, t = c.nearest_on([tuple(p) for p in z['poly_line']], ((x0 + x1) / 2, (y0 + y1) / 2))
            if best is None or dd < best[0]:
                best = (dd, q, sid)
        q = best[1]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if abs(q[0] - cx) > abs(q[1] - cy):
            door, facing = ((x1 if q[0] > cx else x0), cy), (0 if q[0] > cx else 180)
        else:
            door, facing = (cx, (y1 if q[1] > cy else y0)), (90 if q[1] > cy else 270)
        house = {
            'id': '05-B017', 'kind': 'house', 'material_slot': 'downtown_house_stucco', 'floors': 8, 'floor_h_m': 3.4, 'height_m': 27.2,
            'roof': {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.9}, 'walls': 'facade_downtown_stucco', 'tint': '#B9A48A',
            'footprint': fp, 'arches': [], 'facade_kit': 'downtown', 'collider': 'full_roof', 'disabled': False, 'corner': True,
            'entrances': [{'pos': rnd2(door), 'facing_deg': facing, 'kind': 'door', 'w_m': 1.2, 'street': best[2]}],
            'sockets': {'balconies': 'none', 'windows': True, 'fire_escape': False, 'ac_units': 2, 'water_tank': True, 'awning': False, 'storefront': True},
            'ground_floor': {'kind': 'storefront', 'h_m': 4.4, 'material_slot': 'downtown_storefront'},
            'notes': 'owner decision 21.10 (Fedya): only two skyscrapers on the map -> the round glass corner tower of the legend (05-B018 + podium '
                     '05-B017) replaced by a normal corner block on the podium footprint, 8 floors; question for Vadim'}
        d['buildings'] = [b for b in d['buildings'] if b['id'] not in ('05-B017', '05-B018')] + [house]
        log.append('round glass corner tower 05-B018 + podium 05-B017 -> corner house 05-B017 (8 floors) on %.1f x %.1f m' % (x1 - x0, y1 - y0))
    for b in d['buildings']:
        if b['kind'] == 'glass_office' and b['floors'] > 8:
            b['floors'], b['height_m'] = 8, round(8 * b.get('floor_h_m', 3.6), 1)
            b['notes'] = (b.get('notes') or '') + ' | owner decision 21.10: capped at 8 floors (only the T4 twins are high-rise)'
            log.append('%s glass office -> 8 floors' % b['id'])
    high = [(b['id'], b['kind'], b['height_m']) for b in d['buildings'] if (b.get('height_m') or 0) > 30 and b['id'] not in ('05-01', '05-02')]
    d.setdefault('owner_decisions', [])
    for l in log:
        if l not in d['owner_decisions']:
            d['owner_decisions'].append(l)
    save_json(DT, d)
    others = []
    import glob, os, json
    for f in glob.glob(os.path.join(c.OUT, 'districts', '*_v85.json')):
        for b in json.load(open(f, encoding='utf-8'))['buildings']:
            if (b.get('height_m') or 0) > 30 and b['id'] not in ('05-01', '05-02') and not b.get('disabled'):
                others.append((b['id'], b['kind'], b['height_m']))
    print(log, '| buildings > 30 m besides the twins:', others)


if __name__ == '__main__':
    main()
