"""Write MODELS_M2.json (integrator manifest) from build_report_v01.json + the W85 v02 map data (system Python).
  python write_models_json_m2_v01.py
-> Assets/OnlyVolunteers/Art/Props/MapW86_v01/Static/MODELS_M2.json (+ copy in Working/Reviews/MapW86_TexturesAll_2026-10-22/M2/)."""
import json, glob, os, re, zlib, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
DATA = REPO / 'Assets/OnlyVolunteers/Map/W85Build/Data/v02'
OUT = REPO / 'Assets/OnlyVolunteers/Art/Props/MapW86_v01/Static/MODELS_M2.json'
COPY = REPO / 'Working/Reviews/MapW86_TexturesAll_2026-10-22/M2/MODELS_M2.json'
rep = json.loads((HERE / 'build_report_v01.json').read_text())

# ---- every prop the W85 builder turns into a box (same filter as W85Builder.Prop)
src = (REPO / 'Assets/OnlyVolunteers/Map/W85Build/Editor/W85Builder.cs').read_text(encoding='utf-8')
prefab_kinds = set(re.findall(r'\["([^"]+)"\]', re.search(r'PrefabOf = new\(\)\s*\{(.*?)\};', src, re.S).group(1)))
TREE = {'tree', 'trees', 'palm', 'bush', 'shrub', 'oak', 'apple', 'pine', 'birch', 'poplar', 'spruce'}
boxes = []
for f in sorted(glob.glob(str(DATA / 'districts/*.json'))) + [str(DATA / 'details_v85.json')]:
    d = json.load(open(f, encoding='utf-8'))
    dist = os.path.basename(f).replace('_v85.json', '')
    for p in d.get('props', []):
        k = (p.get('kind') or '').lower()
        if p.get('disabled') is True or (any(w in TREE for w in re.split(r'[_ \-]', k)) and 'lamp' not in k):
            continue
        if not isinstance(p.get('pos'), list) or len(p['pos']) < 2:
            continue
        if k == 'legend_object' or 'marker' in k or 'spawn' in k or k == 'trigger_marker' or k in prefab_kinds or p.get('dressing') is True:
            continue
        if any(s in k for s in ('lamp', 'light', 'pole', 'mast')) or k == 'flagpole':
            continue
        boxes.append(dict(district=dist, kind=k, id=p.get('id', k), pos=p['pos'], rot_deg=p.get('rot_deg', 0), size=p.get('size')))


def T(name):
    return name


# kind -> list of (predicate(box) -> bool, type)
KIND = {
    'campfire_cold': [(None, 'CampfireCold')], 'log_bench': [(None, 'LogBench')], 'blocked_tunnel_mouth': [(None, 'BlockedTunnelMouth')],
    'grave': [(None, 'Grave')], 'standpipe': [(None, 'Standpipe')], 'fishing_nets': [(None, 'FishingNets')],
    'net_drying_rack': [(None, 'NetDryingRack')], 'reed_clump': [(None, 'ReedClump')],
    'atm': [(None, 'ATM')], 'big_screen': [(None, 'BigScreen')], 'bollard_yellow': [(None, 'BollardYellow')],
    'courtyard_gate': [(None, 'CourtyardGate')], 'gate_pier': [(None, 'GatePier')],
    'hedge_trimmed': [(lambda b: b['size'][0] < 10, 'HedgeTrimmed_2p8'), (lambda b: b['size'][0] >= 10, 'HedgeTrimmed_29p4')],
    'monument_tramduro': [(None, 'MonumentTramduro')], 'police_booth': [(None, 'PoliceBooth')],
    'round_bench_flowerbed': [(None, 'RoundBenchFlowerbed')], 'pallet_stack': [(None, 'PalletStack')],
    'fuel_pump_island': [(lambda b: b['size'][0] < 3, 'FuelPumpSingle'), (lambda b: b['size'][0] >= 3, 'FuelPumpDouble')],
    'football_goal_torn_net': [(None, 'FootballGoalTornNet')], 'watch_tower': [(None, 'WatchTower')],
    'leave_country_button': [(None, 'LeaveCountryButton')], 'neon_heart_sign': [(None, 'NeonHeartSign')],
    'sliding_gate_steel': [(None, 'SlidingGateSteel')], 'gate_guide_rail': [(None, 'GateGuideRail')],
    'air_water_post': [(None, 'AirWaterPost')], 'price_pylon_blank': [(None, 'PricePylonBlank')],
    'bio_toilet': [(None, 'BioToilet')], 'portable_toilet': [(None, 'BioToilet')], 'bin': [(None, 'SiteBin')],
    'clothes_line': [(None, 'ClothesLine')], 'fire_barrel': [(None, 'FireBarrel')], 'formwork_panels': [(None, 'FormworkPanels')],
    'formwork_shields': [(None, 'FormworkShields')], 'formwork_stack': [(None, 'FormworkStack')], 'gravel_pile': [(None, 'GravelPile')],
    'sand_pile': [(None, 'SandPile')], 'ice_chest': [(None, 'IceChest')], 'pallet_bricks': [(None, 'PalletBricks')],
    'pallet_blocks': [(None, 'PalletBlocks')],
    'pipe_stack': [(lambda b: b['district'] == 'construction', 'PipeStackSite'), (lambda b: b['district'] == 'port', 'PipeStackPort')],
    'rebar_bundles': [(None, 'RebarBundles')], 'scrap_metal_pile': [(None, 'ScrapMetalPile')], 'smoking_shelter': [(None, 'SmokingShelter')],
    'tyre_stack': [(None, 'TyreStack')], 'water_tank': [(None, 'WaterTank')], 'wheel_wash': [(None, 'WheelWash')],
    'big_bags': [(None, 'BigBags')], 'bollard': [(None, 'MooringBollard')], 'rubber_fender': [(None, 'RubberFender')],
    'cable_reel': [(None, 'CableReel')], 'oil_drum': [(None, 'OilDrum')], 'pallets': [(None, 'Pallets')],
    'water_tower': [(lambda b: b['district'] == 'port', 'WaterTowerPort')], 'pipe_manifold': [(None, 'PipeManifold')],
    'bridge_barrier': [(None, 'BridgeBarrier')], 'fictional_nuclear_missile': [(None, 'FictionalNuclearMissile')],
    'gold_statue': [(None, 'GoldStatue')], 'stepped_monument_pedestal': [(None, 'StepPedestal')], 'golf_green': [(None, 'GolfGreen')],
    'portico_steps': [(None, 'PorticoSteps')], 'presidential_speech_stage': [(None, 'PresidentialSpeechStage')],
    'presidential_lectern': [(None, 'PresidentialLectern')], 'speech_platform_steps': [(None, 'SpeechPlatformSteps')],
}
NOT_MINE = {
    'concrete_mixer_truck': 'M1 (vehicles/machines)', 'dump_truck': 'M1', 'food_truck': 'M1', 'forklift': 'M1', 'helicopter': 'M1',
    'jet_ski': 'M1 (boats/water craft)', 'military_cargo_truck': 'M1', 'military_utility_vehicle': 'M1', 'parked_car': 'M1',
    'patrol_boat': 'M1', 'reach_stacker': 'M1', 'tank': 'M1', 'truck_with_container': 'M1', 'van_on_jacks': 'M1', 'wheel_loader': 'M1',
    'yacht': 'M1', 'boat_on_keel_blocks': 'M1', 'upturned_boat': 'M1 (boat) - doubt, confirm with M1',
    'sup_board': 'M1 (beach water craft, grouped with jet skis in T111) - doubt, confirm with M1',
    'stylized_air_defence': 'M1 (military vehicle, T118 with tanks) - doubt, confirm with M1',
    'tower_crane': 'M1 (machine; 32 m crane, C2 red) - doubt, confirm with M1',
    'shipping_container_20ft': 'texture rollout P1 (T85: containers stay boxes, multicolour atlas) - not a model task',
    'shipping_container_40ft': 'texture rollout P1 (T85)',
    'waterfall_to_sea': 'waterfall / relief agent (Vadim complaint 3; T106 suggests a Rock_Macro cliff, not a prop)',
    'npc_spot': 'NPC marker, no visual - integrator should turn it into an empty marker (W85Builder makes a 0.6 x 1.8 box today)',
    'police_post_npc': 'NPC marker (grandpa policeman sits at the square table) - no visual',
}


def stable(i, n):
    return zlib.crc32(i.encode()) % n


kinds_out = collections.OrderedDict()
unmatched = collections.Counter()
by_type_ids = collections.defaultdict(list)
for b in boxes:
    rules = KIND.get(b['kind'])
    if not rules:
        unmatched[b['kind']] += 1
        continue
    t = next((tt for pred, tt in rules if pred is None or pred(b)), None)
    if t is None:
        unmatched[b['kind']] += 1
        continue
    by_type_ids[t].append(b)

types_out = collections.OrderedDict()
for t, bl in by_type_ids.items():
    r = rep[t]
    vs = list(r['variants'])
    inst = []
    for i, b in enumerate(sorted(bl, key=lambda q: q['id'])):
        if t == 'FuelPumpSingle':
            v = 'B'
        elif t == 'FuelPumpDouble':
            v = 'A'
        elif t == 'BioToilet':
            v = 'A' if b['kind'] == 'portable_toilet' else vs[stable(b['id'], len(vs))]
        elif t == 'WaterTank':
            v = 'A' if b['size'][0] >= 3.5 else 'B'
        elif t in ('GolfGreen', 'RoundBenchFlowerbed'):
            v = vs[i % len(vs)]
        else:
            v = vs[stable(b['id'], len(vs))] if len(vs) > 1 else vs[0]
        scale = 1.0
        if t == 'WaterTank':
            scale = round(b['size'][0] / 3.6, 3)
        inst.append(dict(id=b['id'], district=b['district'], kind=b['kind'], pos=b['pos'], rot_deg=b['rot_deg'], data_size=b['size'],
                         variant=v, fbx=r['variants'][v]['fbx'], uniform_scale=scale))
    if r['placement'] == 'facing':
        rot = 'Quaternion.Euler(0, 90 - rot_deg, 0)  (prefab convention: model front +Z faces the data rot direction)'
    else:
        off = r['rotation_offset_y']
        rot = 'Quaternion.Euler(0, -rot_deg' + (f' + {off}' if off else '') + ', 0)  (same as the W85 placeholder box: local X = data size[0], local Z = data size[1])'
    vinfo = {}
    for v, x in r['variants'].items():
        mn, mx = x['bounds_min'], x['bounds_max']
        vinfo[v] = dict(fbx=x['fbx'], tris_lod0=x['tris_lod0'], tris_lod1=x['tris_lod1'], ucx_colliders=x['ucx'],
                        model_size_unity_xyz_m=[round(mx[0] - mn[0], 2), round(mx[2] - mn[2], 2), round(mx[1] - mn[1], 2)])
    types_out[t] = dict(kinds=sorted({b['kind'] for b in bl}), instances=len(bl), data_size=r['data_size'], unity_rotation=rot,
                        y_offset_m=r['y_offset'], front=r['front'], scale=r['scale_rule'] or 'none (1:1, modelled at data size)',
                        variant_rule=r['variant_rule'] or ('stable crc32(id) % n' if len(vs) > 1 else 'single'),
                        collider=r['collider_note'], notes=r['notes'], source_blend=r['blend'], variants=vinfo, ids=inst)

total_ids = sum(len(v['ids']) for v in types_out.values())
manifest = collections.OrderedDict(
    version='v01', agent='M2 (static props)', date='2026-10-22',
    summary=f'{len(types_out)} types, {sum(len(v["variants"]) for v in types_out.values())} FBX variants replacing {total_ids} W85 placeholder boxes '
            f'(of {len(boxes)} box props in Data/v02; the rest are listed under not_mine).',
    data_source='Assets/OnlyVolunteers/Map/W85Build/Data/v02/districts/*.json + details_v85.json (box props = W85Builder.Prop fallback, no PrefabOf entry)',
    conventions=dict(
        frame='Every model is built in the frame of the placeholder box it replaces: Unity local X = data size[0], local Z = data size[1], +Y up; '
              'pivot = centre of the base on the ground (P(pos), y = terrain height).',
        fbx='Blender Z up / front -Y exported with axis_forward -Z, axis_up Y, apply_unit_scale, FBX_SCALE_UNITS, bake_space_transform '
            '(same as GRANDPA_YARD_v01 / FACADE_KIT_v01): Blender -Y -> Unity +Z, root rotation identity, 1 unit = 1 m.',
        hierarchy='root MW86_<Type>_<Var> -> <root>_LOD0 + <root>_LOD1 (Unity auto-creates the LODGroup; suggested screen heights 0.35 / 0.08 / cull 0.01) '
                  'or a single <root>_Mesh when <= 1000 tris; plus UCX_<root>_NN convex collider meshes.',
        colliders='UCX_* children -> convex MeshCollider on the child and remove its MeshRenderer (exactly what W85Builder Kit() already does for '
                  'FACADE_KIT pieces). Without that step the UCX boxes RENDER. No other colliders needed.',
        components='Keep W85Builder.Prop behaviour on the root: W76GripAnchor for grip kinds (bollard, ...), W76LeaveCountryButton for '
                   'leave_country_button, static flags BatchingStatic | OccludeeStatic on all renderers.'),
    material=dict(
        name='MW86_StaticPalette_v01 (one material for every M2 prop; FBX materials carry this name -> remap by name)',
        shader='URP/Lit, Opaque, Workflow Metallic',
        base_map='Textures/MW86_StaticPalette_v01_Albedo.png (sRGB)',
        metallic_map='Textures/MW86_StaticPalette_v01_MetallicSmoothness.png (sRGB OFF; R = metallic, A = smoothness; Smoothness Source = Metallic Alpha, smoothness 1)',
        emission='on; Emission Map = Textures/MW86_StaticPalette_v01_Emission.png (sRGB), colour white, HDR intensity ~1.5 (neon heart, '
                 'lantern, screen, fire embers, beacons, displays; the other swatches are black)',
        texture_import='256 px, Generate Mip Maps OFF (16 px flat swatches - mips would blend neighbours), Filter Point or Bilinear, Compression None, Wrap Clamp',
        palette_json='ArtSource/Props/MAP_W86_v01/static/_common/palette_v01.json (swatch names, colours, UV centres)'),
    types=types_out,
    optional_unused={t: dict(fbx=[x['fbx'] for x in rep[t]['variants'].values()], kinds=rep[t]['kinds'],
                         why='built for a box kind that W85Builder now maps to a prefab (PrefabOf changed during this pass) - use only if wanted')
                     for t in rep if t not in types_out},
    not_mine=collections.OrderedDict(sorted({k: NOT_MINE.get(k, 'unassigned') for k in unmatched}.items())),
    not_mine_counts=dict(sorted(unmatched.items())),
)
OUT.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding='utf-8')
COPY.parent.mkdir(parents=True, exist_ok=True)
COPY.write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding='utf-8')
print(manifest['summary'])
print('unmatched:', dict(unmatched))
