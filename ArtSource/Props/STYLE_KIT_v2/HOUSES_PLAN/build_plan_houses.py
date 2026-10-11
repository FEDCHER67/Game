"""STYLE_KIT_v2 / HOUSES_PLAN - one model per plan building of the trial region (style bible v2, sections 2.5-2.7, 7).

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python ArtSource/Props/STYLE_KIT_v2/HOUSES_PLAN/build_plan_houses.py -- --revision 2

What it is: a preview of the ProceduralBuilding roll-out for the trial scene Map_Look_v13_trial (bible 12). Every
building of ArtSource/References/Map/Look/look_v12_flat.json inside the region (x 440-960, y 360-870) gets a model with
its plan footprint, storeys, roof type and front, built with the facade grammar of _lib/sk2_house.py and coloured by
bible 7.5: special buildings by table 2.7, style tables 2.5, otherwise the district recipe weighted by hash(id), roofs
from the wall -> roof pairs 2.6, and the neighbour rule (no two buildings within 12 m share a wall swatch; panel blocks
compare the balcony accent). The plan is read, never written.

v02b: the region is the whole map, so the trial frames close their vistas with real plan buildings; archetypes
for rural houses (wood planks / painted, shutters), neon buildings (plum / chalk), the church, the water tower, the
gas station, ruins and small sheds were added.

Output: HS_P_<id>_v02.fbx (front = -Y / Unity -Z, pivot = footprint centre on the ground), plan_buildings_v02.json
(per building: asset, plan centre, front angle, Unity yaw, frontage/depth, eave and top heights, archetype, colours),
validation_v02.json and an overview render.
"""
import json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit2 as sk                                   # noqa: E402
import sk2_house as hk                                   # noqa: E402

PLAN = sk.REPO_DIR / 'ArtSource' / 'References' / 'Map' / 'Look' / 'look_v12_flat.json'
REGION = (0.0, 1400.0, -100.0, 1100.0)          # v02b: the whole map (the trial scene shows it to the horizon)

fam = sk.Family('SK2-PLANHOUSES-001', __file__, 'HS_P_', budget=(1, 60000),
                description='Plan buildings of the trial region (look_v12_flat.json, x 440-960, y 360-870) built with '
                            'the facade grammar of bible 7 - preview of the ProceduralBuilding roll-out')
D = json.loads(PLAN.read_text(encoding='utf-8'))
RECIPES = {r['district']: r for r in sk.BIBLE_DATA['recipes']}
STYLE_WALLS = {s['style']: s for s in sk.BIBLE_DATA['style_walls']}
PAIRS = {p['wall']: p['roofs'] for p in sk.BIBLE_DATA['wall_roof_pairs']}
SPECIAL = {                                      # bible 2.7 (type -> wall, pitched roof or 'grey' for flat)
    'police_station': ('cream', 'slate'), 'bank': ('ochre', 'slate'), 'supermarket': ('panel', 'grey'),
    'hospital': ('mint', 'grey'), 'industrial_chimney': ('brick', 'grey'), 'tower': ('cream', 'grey'),
    'church': ('cream', 'slate'), 'water_tower': ('brick', 'grey'), 'gas_station': ('chalk', 'grey'),
}


def weighted(items, weights, key):
    tot = sum(weights)
    r = hk.h32(key) % tot
    for it, w in zip(items, weights):
        if r < w:
            return it
        r -= w
    return items[-1]


def geometry(b):
    """(frontage W, depth D, front angle deg) from the plan rect and front_deg; slabs face their long side to the
    nearest road (the plan's front of a slab may point at its end wall)."""
    cx, cy, a, bb, ang = b['rects'][:5]
    f = b['front_deg'] % 360
    d = (ang - f) % 180
    if d < 45 or d > 135:
        depth, front = a, bb
    else:
        depth, front = bb, a
    if b['type'] == 'slab' and front < depth:
        front, depth = depth, front
        # long axis direction: along `ang` if a is the long side, else perpendicular
        long_dir = ang if a > bb else ang + 90
        best = None
        for cand in (long_dir + 90, long_dir - 90):
            px = cx + math.cos(math.radians(cand)) * depth / 2
            py = cy + math.sin(math.radians(cand)) * depth / 2
            dmin = min(dist_to_roads(px, py), 1e9)
            if best is None or dmin < best[0]:
                best = (dmin, cand % 360)
        f = best[1]
    return front, depth, f


def dist_to_roads(x, y):
    best = 1e9
    for r in D['roads']:
        p = r['pts']
        for i in range(0, len(p) - 2, 2):
            ax, ay, bx, by = p[i], p[i + 1], p[i + 2], p[i + 3]
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L2))
            best = min(best, math.hypot(ax + t * dx - x, ay + t * dy - y))
    return best


def fp_dist(b1, b2):
    """Minimum distance between two footprints (vertex-to-edge both ways; 0 if they overlap a vertex)."""
    def edges(fp):
        pts = [(fp[i], fp[i + 1]) for i in range(0, len(fp), 2)]
        return pts, list(zip(pts, pts[1:] + pts[:1]))

    def pe(p, e):
        (ax, ay), (bx, by) = e
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        return math.hypot(ax + t * dx - p[0], ay + t * dy - p[1])
    p1, e1 = edges(b1['fp'])
    p2, e2 = edges(b2['fp'])
    return min(min(pe(p, e) for p in p1 for e in e2), min(pe(p, e) for p in p2 for e in e1))


def wall_choices(b):
    """(list of wall swatches in recipe order, weights, kind) for the building's district and style (2.5)."""
    dist = b['district'] if b['district'] in RECIPES else 'transition'
    rec = RECIPES[dist]
    st = b['style']
    if b['type'] in SPECIAL:
        return [SPECIAL[b['type']][0]], [100], 'special'
    if b['type'] == 'kiosk':
        s = STYLE_WALLS['kiosk']
        return s['walls'], s['weights'], 'kiosk'
    if st == 'neon':
        s = STYLE_WALLS['neon']
        return s['walls'], s['weights'], 'neon'
    if st in ('panel', 'industrial', 'shed'):
        s = STYLE_WALLS[st]
        return s['walls'], s['weights'], st
    if st == 'villa':
        if b['roof'] == 'flat':
            return ['chalk'], [100], 'villa_modern'
        return rec['walls'], rec['wall_weights'], 'villa'
    if st == 'civic':
        return rec['civic_walls'], rec['civic_weights'], 'civic'
    if st == 'rural_wood':
        return rec['rural_walls'] or rec['walls'], rec['rural_weights'] or rec['wall_weights'], 'rural'
    return rec['walls'], rec['wall_weights'], 'oldtown'


def roof_for(b, wall):
    dist = b['district'] if b['district'] in RECIPES else 'transition'
    rec = RECIPES[dist]
    if b['roof'] in ('flat', 'none'):
        return 'grey'
    if b['type'] in SPECIAL:
        return SPECIAL[b['type']][1]
    if b['style'] == 'shed':
        return 'grey' if wall == 'wood' else 'slate'
    if b['style'] == 'industrial' and wall == 'grey':
        return 'slate'
    ok = [(r, w) for r, w in zip(rec['roofs'], rec['roof_weights']) if r in PAIRS.get(wall, [])]
    if not ok:
        return PAIRS.get(wall, ['grey'])[0]
    return weighted([r for r, _ in ok], [w for _, w in ok], (b['id'], 'roof'))


def recipe(b, wall):
    dist = b['district'] if b['district'] in RECIPES else 'transition'
    rec = RECIPES[dist]
    roof = roof_for(b, wall)
    plinth = rec['plinth']
    if wall in ('brick', 'wood', 'plum'):
        plinth = 'grey'
    if wall == 'coral':
        plinth = 'asphalt'
    acc = [a for a in rec['accents'] if a in sk.SWATCH and a not in ('neon_pink', 'neon_cyan', 'lamp_glow')] or ['red']
    rc = {'district': dist, 'style': b['style'], 'wall': wall, 'roof': roof, 'roof_c': roof if b['roof'] not in ('flat', 'none') else 'grey',
          'deck': 'grey', 'trim': rec['trim'], 'plinth': plinth,
          'door': rec['doors'][hk.h32(b['id'], 'door') % len(rec['doors'])],
          'accent': acc[hk.h32(b['id'], 'acc') % len(acc)]}
    if rc['door'] in ('grey',):
        rc['door'] = 'wood'
    if wall == 'chalk':
        rc['frame'] = 'ink'
    if b['type'] == 'police_station':
        rc['accent'] = 'cobalt'
    return rc


# ---------------------------------------------------------------- choose colours with the neighbour rule (7.5)
blds = sorted([b for b in D['buildings'] if REGION[0] <= b['x'] <= REGION[1] and REGION[2] <= b['y'] <= REGION[3]
               and b['type'] not in ('advertising_pole',)], key=lambda b: b['id'])
walls, accents = {}, {}
for b in blds:
    choices, weights, kind = wall_choices(b)
    w = weighted(choices, weights, (b['id'], 'wall'))
    near = [o for o in blds if o['id'] in walls and fp_dist(b, o) <= sk.BIBLE_DATA['rules']['neighbour_distance_m']]
    if kind not in ('special', 'panel') and len(choices) > 1:
        k = choices.index(w)
        for _ in range(len(choices)):
            if all(walls[o['id']] != w for o in near):
                break
            k = (k + 1) % len(choices)
            w = choices[k]
    walls[b['id']] = w
RC = {}
for b in blds:
    rc = recipe(b, walls[b['id']])
    if b['style'] == 'panel':                     # panel blocks: the neighbour rule works on the balcony accent
        acc = RECIPES['residential']['accents']
        k = hk.h32(b['id'], 'acc') % len(acc)
        near = [o for o in blds if o['id'] in accents and fp_dist(b, o) <= 30.0]
        for _ in range(len(acc)):
            if all(accents[o['id']] != acc[k] for o in near):
                break
            k = (k + 1) % len(acc)
        rc['accent'] = acc[k]
        accents[b['id']] = acc[k]
    RC[b['id']] = rc


# ---------------------------------------------------------------- archetypes per plan building
def build_spec(b):
    W, Dd, f = geometry(b)
    rc = RC[b['id']]
    t, st = b['type'], b['style']
    fl_h = b.get('floor_h') or 3.2
    sp = {'id': b['id'], 'W': round(W, 3), 'D': round(Dd, 3), 'floors': int(b['floors']), 'rc': rc, 'h': b['h'],
          'floor_h': fl_h if st in ('oldtown', 'civic', 'villa', 'rural_wood') else 3.2}
    if t == 'water_tower':
        return 'water_tower', dict(sp, d=min(W, Dd), h=b['h']), f
    if t in ('bus_stop', 'wagon_base'):
        return 'kiosk', sp, f
    if t == 'abandoned_farm':
        return 'industrial', dict(sp, roof='flat', h=min(b['h'], 4.5)), f
    if st == 'neon':
        return 'commercial', dict(sp, sign='ink', awning=False), f
    if st == 'rural_wood':
        return 'masonry', dict(sp, style='rural', roof='gable', accent_kind='shutters', pitch=38, shop=False), f
    if t == 'tower':
        return 'tower', sp, f
    if t == 'slab':
        return 'slab', sp, f
    if t == 'industrial_chimney':
        return 'chimney', dict(sp, d=min(W, Dd), h=b['h']), f
    if t == 'garage_base':
        return 'garages', sp, f
    if t == 'kiosk':
        return 'kiosk', sp, f
    if st in ('industrial', 'shed'):
        return 'industrial', dict(sp, roof=b['roof'] if b['roof'] in ('gable', 'flat') else 'shed'), f
    if st == 'commercial' or b['roof'] == 'flat' and st not in ('civic', 'oldtown', 'villa'):
        return 'commercial', dict(sp, awning=t in ('shop_24h',), sign={'supermarket': 'red', 'shop_24h': 'red'}.get(t)), f
    if st == 'villa' and b['roof'] == 'flat':
        return 'villa_modern', sp, f
    if st == 'villa':
        return 'masonry', dict(sp, style='villa', roof='hip', accent_kind='shutters'), f
    roof = b['roof'] if b['roof'] in ('gable', 'hip', 'flat') else 'gable'
    style = 'civic' if st == 'civic' else 'oldtown'
    acc = None
    if style == 'oldtown':
        acc = 'flower' if hk.h32(b['id'], 'acck') % 2 == 0 else 'shutters'
    spec = dict(sp, style=style, roof=roof, accent_kind=acc, shop=t in ('cafe', 'pharmacy', 'village_shop'),
                dormer=t in ('house_base', 'bank'), flag='cobalt' if t == 'police_station' else None,
                pitch=35 if roof == 'gable' else 30, central_door=t in ('house_base', 'bank', 'police_station'))
    if t == 'bar':
        spec['pitch'] = 30
    return 'masonry', spec, f


BUILD = {'masonry': hk.masonry, 'slab': hk.slab, 'tower': hk.tower, 'commercial': hk.commercial, 'garages': hk.garages,
         'industrial': hk.industrial, 'kiosk': hk.kiosk, 'chimney': hk.chimney_tower, 'villa_modern': hk.villa_modern,
         'water_tower': hk.water_tower}


def multi_block(b, kind, sp, f):
    """Composite plan buildings (several rects, e.g. the hospital): the main block + wings as extra masonry blocks,
    offsets taken from the plan and turned into the model frame (model +X = plan right of the front, -Y = front)."""
    m = BUILD[kind](sp)
    r = b['rects']
    cx, cy = b['x'], b['y']
    fr = math.radians(f)
    fx, fy = math.cos(fr), math.sin(fr)                     # front direction (plan)
    rx, ry = -fy, fx                                        # model +X in plan (= R(f + 90) applied to +X)
    for i in range(5, len(r), 5):
        wx, wy, a, bb, ang = r[i:i + 5]
        ox, oy = wx - cx, wy - cy
        lx, ly = ox * rx + oy * ry, -(ox * fx + oy * fy)   # model coordinates (front = -Y)
        d = (ang - f) % 180
        depth, front = (a, bb) if (d < 45 or d > 135) else (bb, a)
        wing = hk.masonry(dict(sp, id=b['id'] + f'_w{i // 5}', W=front, D=depth, roof='flat', accent_kind=None, shop=False,
                               dormer=False, flag=None, central_door=False))
        m.merge(wing, sk.T(lx, ly, 0.0))
    return m


manifest = []
for b in blds:
    kind, sp, f = build_spec(b)
    name = 'HS_P_' + b['id']
    fn = (lambda b=b, kind=kind, sp=sp, f=f: multi_block(b, kind, sp, f)) if len(b['rects']) > 5 else \
         (lambda kind=kind, sp=sp: BUILD[kind](sp))
    fam.add_asset(name, fn, budget=(1, 60000), row=0, recipe=RC[b['id']], archetype=kind, plan_id=b['id'],
                  plan_type=b['type'], plan_style=b['style'], district=b['district'])
    yaw = math.degrees(math.atan2(-math.cos(math.radians(f)), -math.sin(math.radians(f))))
    manifest.append({'id': b['id'], 'asset': name, 'x': b['x'], 'y': b['y'], 'front_deg': round(f, 3),
                     'unity_yaw': round(yaw, 3), 'W': sp['W'], 'D': sp['D'], 'floors': sp['floors'], 'archetype': kind,
                     'type': b['type'], 'style': b['style'], 'district': b['district'], 'wall': RC[b['id']]['wall'],
                     'roof': RC[b['id']]['roof'], 'accent': RC[b['id']]['accent'], 'plan_h': b['h']})

report = fam.finish(lineup_gap=8.0, extra_notes=[
    'One model per plan building of the trial region; colours by bible 7.5 (2.7 specials, 2.5 recipes by hash(id), 2.6 '
    'pairs, neighbour rule 12 m; panel blocks by balcony accent). Placement data: plan_buildings_v02.json.',
    'Unity: position (plan x, 0, plan y), rotation Euler(0, unity_yaw, 0); the model front is local -Z.'])
for e in manifest:
    r = report['assets'][e['asset']]
    e['top_m'] = r['bounds_max'][2]
    e['size_m'] = r['size_m']
    e['triangles'] = r['triangles']
(fam.out / f'plan_buildings_{fam.rev}.json').write_text(json.dumps({'source': str(PLAN.relative_to(sk.REPO_DIR)).replace('\\', '/'),
                                                                   'region_xy': REGION, 'buildings': manifest}, indent=1,
                                                                  ensure_ascii=False), encoding='utf-8')

# ---------------------------------------------------------------- preview: the region from the south-west
if not fam.args.no_render:
    cx0, cy0 = 650.0, 560.0
    objs = []
    for e in manifest:
        objs += fam.place(e['asset'], e['x'] - cx0, e['y'] - cy0, rot=e['front_deg'] + 90.0)
    fam.showcase(True)
    fam.shot('01_region_from_sw.png', objs, az=-35, el=32, res=(2400, 1400), lens=45, ground='meadow')
    fam.shot('02_region_top.png', objs, az=0, el=89, res=(2000, 2000), lens=50, ground='meadow', ortho=True)
    fam.clear_showcase()
    fam.showcase(False)
print('done')
