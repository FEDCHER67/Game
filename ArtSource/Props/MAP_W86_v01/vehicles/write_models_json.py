"""Writes MODELS_M1.json (data kind -> FBX, placement rule, variants, colliders) from the validation JSONs + W85 v02 data.

python write_models_json.py <out_json>
"""
import glob, json, sys
from pathlib import Path

ROOT = Path('C:/Dev/Game')
VD = ROOT / 'ArtSource/Props/MAP_W86_v01/vehicles'
UNITY = 'Assets/OnlyVolunteers/Art/Props/MapW86_v01/Vehicles'
DATA = ROOT / 'Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts'

val = {}
for p in glob.glob(str(VD / '*' / 'validation_*_v01.json')):
    r = json.load(open(p, encoding='utf-8'))
    val[r['asset']] = r


def unity_box(name, lo, hi):
    """Builder-coordinate box (Blender: x, y, z) -> Unity local centre/size after the pivot offset and FBX axis conversion
    (Unity = (-x, z, -y))."""
    off = val[name]['offset_applied_to_builder_coords']
    lo = [lo[k] + off[k] for k in range(3)]
    hi = [hi[k] + off[k] for k in range(3)]
    c = [-(lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2, -(lo[1] + hi[1]) / 2]
    s = [hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1]]
    return {'center': [round(v, 3) for v in c], 'size': [round(v, 3) for v in s]}


def bbox_box(name):
    a = val[name]['lod0']
    lo, hi = a['bounds_min'], a['bounds_max']
    c = [-(lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2, -(lo[1] + hi[1]) / 2]
    s = [hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1]]
    return {'center': [round(v, 3) for v in c], 'size': [round(v, 3) for v in s]}


def collider(name):
    if name == 'MW86_Helicopter':
        return {'type': 'box', 'boxes': [unity_box(name, (-1.4, -5.3, 0.0), (1.4, 5.8, 3.1))], 'note': 'fuselage + skids; no rotor collider'}
    if name == 'MW86_TruckContainer':
        return {'type': 'box', 'boxes': [unity_box(name, (-1.25, -8.62, 0.0), (1.25, 7.65, 4.0))], 'note': 'mirrors left out'}
    if name == 'MW86_RailWagon_Base1':
        b = [((-1.6, -11.5, 0.3), (1.6, 11.5, 1.3), 'underframe + floor (walk on top at 1.3 m)'),
             ((1.5, -11.5, 1.3), (1.62, 11.5, 3.45), 'wall +X (Blender) / -X (Unity)'),
             ((-1.62, -11.5, 1.3), (-1.5, -0.95, 3.45), 'door-side wall, rear part'),
             ((-1.62, 0.95, 1.3), (-1.5, 11.5, 3.45), 'door-side wall, front part'),
             ((-1.62, -0.95, 3.25), (-1.5, 0.95, 3.45), 'lintel over the door'),
             ((-1.6, -11.5, 1.3), (1.6, -11.4, 3.45), 'end wall'), ((-1.6, 11.4, 1.3), (1.6, 11.5, 3.45), 'end wall'),
             ((-1.68, -11.62, 3.45), (1.68, 11.62, 3.95), 'roof'),
             ((-1.86, -0.6, 0.35), (-1.6, 0.6, 0.45), 'step 1 (top 0.45)'), ((-1.86, -0.6, 0.77), (-1.6, 0.6, 0.87), 'step 2 (top 0.87)')]
        return {'type': 'boxes', 'boxes': [dict(unity_box(name, lo, hi), note=n) for lo, hi, n in b],
                'note': 'hollow, enterable (Base 1). Step rises 0.45 / 0.42 / 0.43 m: if the character step offset is lower, add an invisible ramp at the door.'}
    if name in ('MW86_ReachStacker', 'MW86_AirDefence', 'MW86_WheelLoader'):
        return {'type': 'convex_mesh', 'mesh': 'LOD1', 'note': 'MeshCollider convex on the LOD1 mesh'}
    if name == 'MW86_MissileSilo':
        return {'type': 'boxes', 'boxes': [unity_box(name, (-1.05, -1.05, 0.0), (1.05, 1.05, 11.0)), bbox_box(name) | {'size': [6.57, 0.45, 6.57], 'center': [0.0, 0.225, 0.0]}],
                'note': 'missile column + low collar slab'}
    return {'type': 'box', 'boxes': [bbox_box(name)]}


KINDS = {
    # kind: (model(s), yaw_offset_deg, notes)
    'tank': ('MW86_Tank', 0, 'long axis on data size[1]; gun faces box local +Z. Flip 180 if the parade should face the other way.'),
    'stylized_air_defence': ('MW86_AirDefence', 90, 'long axis on data size[0]; launcher faces heading rot_deg.'),
    'fictional_nuclear_missile': ('MW86_MissileSilo', 0, 'round, any yaw.'),
    'military_utility_vehicle': ('MW86_MilJeep', 0, 'long axis on data size[1].'),
    'military_cargo_truck': ('MW86_MilTruck', 0, 'long axis on data size[1].'),
    'helicopter': ('MW86_Helicopter', 90, 'long axis on data size[0]; add elevation_m to the ground height if the pad is raised.'),
    'patrol_boat': ('MW86_PatrolBoat', 90, 'WATER: pivot = waterline, place at sea level 0.0 (not terrain). Moves on route_id: bow = local +Z.'),
    'yacht': (['MW86_Yacht_Motor22', 'MW86_Yacht_Cruiser10'], 90, 'WATER: pivot = waterline, place at sea level 0.0 (the W85 boxes stood on terrain, some inside the cliff). Model + uniform scale per instance below.'),
    'boat_on_keel_blocks': ('MW86_Boat_KeelBlocks', 90, 'stands on the yard (blocks + jack stands included).'),
    'upturned_boat': ('MW86_Rowboat_Upturned', 90, 'river bank; fishing_nets stay with M2 (static props).'),
    'jet_ski': ('MW86_JetSki', 90, 'on the sand.'),
    'sup_board': ('MW86_SUP', 0, 'lying flat on the sand.'),
    'concrete_mixer_truck': ('MW86_MixerTruck', 90, ''),
    'dump_truck': ('MW86_DumpTruck', 90, ''),
    'wheel_loader': ('MW86_WheelLoader', 90, ''),
    'van_on_jacks': ('MW86_VanOnJacks', 90, ''),
    'reach_stacker': ('MW86_ReachStacker', 0, 'P3 blue = variant A (data tint #E2B13B yellow = variant B).'),
    'forklift': ('MW86_Forklift', 90, 'forks = local +Z.'),
    'truck_with_container': ('MW86_TruckContainer', 90, 'cab_end east: with rot 0 the cab faces +X (heading) = local +Z after the 90 offset.'),
    'food_truck': ('MW86_FoodTruck', 90, 'serving window on Blender -X = expected Unity local +X = right of the heading; add 180 to the yaw if it faces away from the square.'),
    'black_suv': ('MW86_SUV_Black', 90, 'OPTIONAL: kind is not a box today (builder maps it to CARS/car_sedan_blue); this replaces it with a real black SUV.'),
}
VARIANTS = {
    '07-yacht0': ('MW86_Yacht_Motor22', 'A'), '07-yacht1': ('MW86_Yacht_Motor22', 'B'), '07-yacht2': ('MW86_Yacht_Cruiser10', 'C'),
    '07-yacht3': ('MW86_Yacht_Cruiser10', 'B'), '07-yacht4': ('MW86_Yacht_Cruiser10', 'A'),
    '09-jetski0': 'A', '09-jetski1': 'B', '09-jetski2': 'C',
    '09-sup0': 'A', '09-sup1': 'B', '09-sup2': 'C', '09-sup3': 'A', '09-sup4': 'B', '09-sup5': 'C',
    '06-09-forklift0': 'A', '06-09-forklift1': 'B', '05-04-foodtruck1': 'A', '05-04-foodtruck2': 'B',
    '07-guard-suv': 'C',
}


def instances():
    out = {}
    for f in sorted(DATA.glob('*_v85.json')):
        d = json.load(open(f, encoding='utf-8'))
        for p in d.get('props', []):
            if p.get('kind') in KINDS:
                out.setdefault(p['kind'], []).append((f.name, p))
    return out


def main(out_path):
    models = {}
    for name, r in sorted(val.items()):
        lo, hi = r['lod0']['bounds_min'], r['lod0']['bounds_max']
        models[name] = {
            'fbx': f'{UNITY}/{name}_v01.fbx',
            'blend': f'ArtSource/Props/MAP_W86_v01/vehicles/{Path(r["files"]["blend"]).parent.name}/{name}_v01.blend',
            'family': r['family'], 'material': r['material'],
            'textures': {v: f'{UNITY}/Textures/MW86_{r["family"]}_{v}.png' for v in 'ABC'},
            'lod': {'LOD0_tris': r['lod0']['triangles'], 'LOD1_tris': r['lod1']['triangles'], 'LOD1_ratio': r['lod1_ratio'],
                    'meshes': [f'{name}_LOD0', f'{name}_LOD1'], 'suggested_screen_heights': [0.6, 0.15, 0.02]},
            'size_unity_xyz_m': [round(hi[0] - lo[0], 3), round(hi[2] - lo[2], 3), round(hi[1] - lo[1], 3)],
            'pivot': r['pivot'], 'collider': collider(name), 'notes': r['notes'],
        }
    inst = instances()
    kinds = {}
    for kind, (mdl, yaw, note) in KINDS.items():
        rows = []
        for fname, p in inst.get(kind, []):
            sz = p.get('size') or []
            v = VARIANTS.get(p['id'], 'A')
            model = mdl if isinstance(mdl, str) else None
            scale = 1.0
            if isinstance(v, tuple):
                model, v = v
            if kind == 'yacht':
                native = val[model]['lod0']['size_xyz_m'][1]
                scale = round(max(sz[0], sz[1]) / native, 3)
            rows.append({'id': p['id'], 'file': fname, 'pos': p['pos'], 'rot_deg': p.get('rot_deg', 0), 'data_size': sz,
                         'model': model, 'variant': v, 'scale': scale,
                         'unity_yaw_deg': round(-float(p.get('rot_deg', 0)) + yaw, 2),
                         **({'elevation_m': p['elevation_m']} if 'elevation_m' in p else {}),
                         **({'route_id': p['route_id']} if 'route_id' in p else {})})
        kinds[kind] = {'model': mdl, 'yaw_offset_deg': yaw, 'notes': note, 'instances': rows}
    wagon = 'MW86_RailWagon_Base1'
    doc = {
        'version': 'M1 vehicles v01, 2026-10-22',
        'conventions': {
            'units': 'metres, 1 Unity unit = 1 m; FBX exported with FBX_SCALE_ALL + apply transform: import Scale Factor 1, Convert Units on, no rotation on the meshes',
            'axes': 'Unity Y up, model front (nose / bow / forks / gun) = local +Z',
            'pivot': 'centre of the footprint on the ground (min y = 0); WATER models: on the waterline (hull below y = 0) -> place at sea level 0.0',
            'placement': 'replace the W85 grey box: position = data pos (x, ground or sea level, y); rotation = Quaternion.Euler(0, unity_yaw_deg, 0) where unity_yaw_deg = -rot_deg + yaw_offset_deg (the boxes used Euler(0, -rot_deg, 0)); uniform scale only (1.0 except yachts)',
            'lod': 'each FBX holds <Name>_LOD0 and <Name>_LOD1 -> Unity builds the LODGroup on import (LOD1 ~31-48 % tris); suggested transitions 60 % / 15 % / cull 2 %',
            'static': 'all static (BatchingStatic) except patrol_boat (moves on its route)',
            'materials': 'one URP Lit material per family + colour variant: MW86_<Family>_<A|B|C> = same shader, _BaseMap = MW86_<Family>_<V>.png, _BaseColor white, Smoothness 0.1, Metallic 0; variants only swap the texture (SRP Batcher friendly)',
            'texture_import': 'sRGB, Wrap Clamp, Filter Bilinear, mipmaps ON, no compression (or High Quality), max size 512. Flat faces use one UV point per face (cell centre) so mips never bleed; camo / teak / hazard / wagon boards are projected patterns',
            'vertex_colours': 'none (URP Lit ignores them)',
        },
        'families': {
            'Water': 'yachts, boats, jet ski, SUP: white / teak / navy (A), navy hull (B), teal stripe (C)',
            'Military': 'Tramduro: olive camo (A, default), desert (B), parade grey-green low-contrast (C)',
            'Machines': 'construction yellow / orange, P3 blue stacker + forklift (A), alternates B / C; wagon rust-red (A, data tint #8C4A36), green (B), brown (C)',
        },
        'models': models,
        'kinds': kinds,
        'buildings': {
            'rail_wagon_base1': {
                'model': wagon, 'data': 'forest_v85.json buildings 01_B01 (kind rail_wagon_base1, material_slot forest_wagon)',
                'placement': 'position = footprint centre at the rail-top height (wheel bottoms = y 0); unity_yaw_deg = 90 - ridge_axis_deg (= 57.5 for v02); the sliding doorway (Blender -X, expected Unity local +X) then faces facing_deg 302.5 of the entrance; if it faces the other track side, add 180',
                'variant': 'A', 'collider': models[wagon]['collider'],
                'notes': 'replaces the W85 building box; interior is hollow (floor 1.3 m above the rail, inner height 2.15 m, doorway 1.9 x 1.95 m, door leaf slid open); stove pipe on the roof; the integrator keeps the door police_stop / base logic from the data',
            }
        },
        'mapped_to_existing_prefabs_not_new_models': {
            'parked_car (construction 03-02-fuel-car1 / car2, grey boxes today)': 'use the existing VEHICLES_KIT prefabs: tint #8FA9C2 -> Art/Map/Prefabs/CARS/car_sedan_blue, tint #C9876F -> CARS/car_sedan_beige (prefab yaw 90 - rot_deg like the other cars); no new model needed',
        },
        'not_done_by_M1': {
            'tower_crane (construction 03-06)': 'big machine but part of the C2 roll-out (red crane chosen); left to that agent',
            'fishing_nets (hamlet)': 'static prop, M2',
            'paz_bus, old_soviet_car, rusty_car_body, rusted_car, parked_tractor, farm_trailer': 'already real prefabs (not boxes)',
        },
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding='utf-8')
    print('written', out_path, len(models), 'models', sum(len(k['instances']) for k in kinds.values()), 'instances')


if __name__ == '__main__':
    main(sys.argv[1])
