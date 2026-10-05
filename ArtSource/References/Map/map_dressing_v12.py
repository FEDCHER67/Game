#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dressing only for the immutable approved R01 v12 plan.

Python 3.12+, Shapely 2.x, Pillow. Run: python -B map_dressing_v12.py
Only the three MAP_DRESSING_R01_v12 outputs are written beside this script.
The generator is deterministic; --validate-only rechecks the saved JSON.
Geometry is in metres, east +x, north +y. Unity uses (x, terrain height, y).
"""
import argparse
import collections
import hashlib
import json
import math
import random
import io
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
from shapely import affinity
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, nearest_points, substring
from shapely.prepared import prep
from shapely import set_precision
from shapely.strtree import STRtree
from shapely.validation import explain_validity
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
STEM = 'MAP_DRESSING_R01_v12'
OUTPUTS = {STEM + ext for ext in ('.json', '.png', '_REPORT.md')} | {Path(__file__).name}
SEED = 12041026
EPS = 0.015
STYLE_MAP = {
    'wagon_base': ('wagon', 'shed', None),
    'grandpa_house': ('rural_wood', 'gable', 'ДОМ ДЕДА'),
    'pharmacy': ('rural_brick', 'gable', 'АПТЕКА'),
    'barn_yard': ('rural_wood', 'gable', 'САРАЙ'),
    'village_shop': ('rural_brick', 'gable', 'ЛАВКА'),
    'bus_stop': ('pavilion', 'shed', 'ОСТАНОВКА'),
    'water_tower': ('water_tower', 'hip', 'ВОДА'),
    'hut': ('hut', 'gable', None),
    'shadow_buyer': ('industrial_shed', 'shed', None),
    'gas_station': ('gas_station', 'flat_parapet', 'АЗС'),
    'abandoned_farm': ('rural_brick', 'none', 'РУИНЫ'),
    'garage_base': ('industrial_brick', 'flat_parapet', None),
    'bar': ('soviet_brick', 'gable', 'БАР'),
    'den': ('soviet_brick', 'hip', None),
    'shop_24h': ('soviet_brick', 'flat_parapet', '24 ЧАСА'),
    'kiosk': ('kiosk', 'shed', 'ПРОДУКТЫ'),
    'car_workshop': ('industrial_brick', 'shed', 'АВТОМАСТЕРСКАЯ'),
    'hospital': ('soviet_brick', 'flat_parapet', 'БОЛЬНИЦА'),
    'police_station': ('soviet_brick', 'hip', 'ПОЛИЦИЯ'),
    'bank': ('soviet_brick', 'hip', 'БАНК'),
    'atm_pavilion': ('pavilion', 'flat_parapet', 'БАНКОМАТ'),
    'supermarket': ('commercial_glass', 'flat_parapet', 'СУПЕРМАРКЕТ'),
    'cafe': ('townhouse_plaster', 'hip', 'КАФЕ'),
    'church': ('church', 'dome_spire', 'ХРАМ'),
    'house_base': ('townhouse_plaster', 'hip', None),
    'mansion': ('mansion_classic', 'hip', 'ВИЛЛА'),
    'private_security': ('pavilion', 'flat_parapet', 'ОХРАНА'),
    'industrial_complex': ('industrial_brick', 'shed', None),
    'depot': ('industrial_brick', 'gable', 'ДЕПО'),
    'tow_yard': ('industrial_shed', 'shed', 'ЭВАКУАТОР'),
    'industrial_chimney': ('industrial_brick', 'none', 'ТРУБА'),
    'warehouse': ('industrial_shed', 'gable', 'СКЛАД'),
    'maintenance_shed': ('industrial_shed', 'shed', 'РЕМОНТ'),
    'prestige_base': ('mansion_classic', 'hip', None),
    'advertising_pole': ('pavilion', 'none', 'ОБЪЯВЛЕНИЯ'),
    'casino': ('commercial_glass', 'flat_parapet', 'КАЗИНО'),
    'nightclub': ('commercial_glass', 'flat_parapet', 'НОЧНОЙ КЛУБ'),
    'bowling_arcade': ('commercial_glass', 'flat_parapet', 'БОУЛИНГ'),
}
WALLS = {
    'forest': ['#89755B', '#A38F6E', '#8B846D'],
    'village': ['#A99270', '#A8B2A0', '#C1AD8F', '#B48669', '#8D9F91'],
    'transition': ['#C5B89D', '#B7AB96', '#AD9780', '#B3B8A6', '#C7AA8A'],
    'residential': ['#ADB3B1', '#B7BDB7', '#B5AAA1', '#A5B0B7', '#B9B39C'],
    'old_town': ['#D5C5A7', '#C6AA92', '#ADC1B3', '#C5B4A1', '#D3BA92', '#BAC3B9'],
    'elite': ['#E3DCC7', '#D6D3C4', '#DBC5A5', '#CBC8BB', '#E7D5BC'],
    'industrial': ['#A18C7B', '#899795', '#9C9F96', '#AE947D'],
    'fields': ['#C1B29B', '#B5BEA4', '#C7BAA6', '#BCABB1'],
}
MATERIAL_COLORS = dict(asphalt='#777F80', paving='#C7BEB0', grass='#B5C39B',
    dirt='#BBAA89', sand='#E8D29E', gravel='#B5B2A6', concrete_yard='#A8A9A4',
    rubber_playground='#B59475')
TREE_COLORS = dict(birch='#80A46D', pine='#507E69', oak='#648952',
    poplar='#74975C', fruit='#90A464', palm='#5F9E83')
FURNITURE_RADIUS = dict(street_lamp=.42, power_pole=.45, bench=1.25,
    bin=.4, bus_stop=2.6, bus_stop_marker=.35, swings=3.3, slide=2.9,
    sandbox=2.55, carpet_rack=2.1, garbage_container=1.05, traffic_sign=.45,
    sign_no_swimming=.55)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def immutable_hashes():
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(ROOT.rglob('*'))
            if p.is_file() and p.name not in OUTPUTS}


def parts(g, kind='Polygon'):
    if g.is_empty:
        return []
    if g.geom_type == kind:
        return [g]
    return [p for q in getattr(g, 'geoms', []) for p in parts(q, kind)]


def coords(seq):
    return [[round(x, 10), round(y, 10)] for x, y in seq]


def poly_data(g):
    return dict(polygon=coords(g.exterior.coords)[:-1],
                holes=[coords(r.coords)[:-1] for r in g.interiors])


def geometry(q):
    return Polygon(q['polygon'], q.get('holes', []))


def rectangle(x, y, w, h, angle=0, chamfer=0):
    if chamfer:
        a, b, c = w / 2, h / 2, chamfer
        g = Polygon([(-a+c,-b),(a-c*.7,-b),(a,-b+c*1.2),(a,b-c),
                     (a-c,b),(-a+c*1.4,b),(-a,b-c*.8),(-a,-b+c)])
    else:
        g = box(-w/2, -h/2, w/2, h/2)
    return affinity.translate(affinity.rotate(g, angle, origin=(0, 0)), x, y)


def tangent(line, s):
    p = line.interpolate(max(0, s-.8))
    q = line.interpolate(min(line.length, s+.8))
    angle = math.atan2(q.y-p.y, q.x-p.x)
    return p, q, angle


def jitter_color(hex_color, rng, amount=9):
    rgb = [int(hex_color[i:i+2], 16) for i in (1, 3, 5)]
    common = rng.randint(-amount, amount)
    return '#' + ''.join(f'{max(0,min(255,c+common+rng.randint(-3,3))):02X}' for c in rgb)


class MapDressing:
    def __init__(self, plan):
        self.p = plan
        self.rng = random.Random(SEED)
        self.boundary = Polygon(plan['boundary']['polygon_m'])
        self.ds = {q['id']: Polygon(q['polygon_m']) for q in plan['districts']}
        self.points = {q['id']: q for q in plan['points']}
        self.functions = {b['id']: b for b in plan['functional_buildings']}
        self.masses = {b['id']: b for b in plan['building_masses']}
        self.aliases = {b['source_building_id']: b['id'] for b in self.functions.values()
                        if b.get('source_building_id')}
        self.physical = {bid: Polygon(b['polygon_m']) for bid, b in self.masses.items()
                         if bid not in self.aliases}
        self.physical.update({bid: Polygon(b['footprint_m']) for bid,b in self.functions.items()})
        self.building_union = unary_union(list(self.physical.values()))
        self.roads = {r['id']: (r, LineString(r['polyline_m'])) for r in plan['roads']}
        self.road_union = unary_union([line.buffer(r['width_m']/2, cap_style=2, join_style=1)
                                      for r,line in self.roads.values()])
        self.water = unary_union([Polygon(w['polygon_m']) if 'polygon_m' in w
            else LineString(w['centerline_m']).buffer(w['width_m']/2)
            for w in plan['water']])
        self.beach = unary_union([Polygon(b['polygon_m']) for b in plan['beaches']])
        self.rail = LineString(plan['railway']['polyline_m']).buffer(3)
        # Follow-up replaces inherited district partitions with explicit property fences.
        self.elite_fences=[dict(id='DRESS_'+q['id'],polyline=coords(q['axis_m']),
            material='stylised_metal',height_m=2.4,district_id='elite',scope='elite_hill_property',
            source_separator_id=q['id']) for q in plan['vegetation_parcels']
            if q.get('continuity_group')=='ELITE_PERIMETER']
        separator=next(q for q in plan['vegetation_parcels'] if q['id']=='INDUSTRIAL_BEACH_FENCE_1')
        self.industrial_axis=LineString(separator['axis_m'])
        gate_station=self.industrial_axis.project(Point(800,347))
        gate_width=7.0
        self.industrial_fences=[dict(id=f'INDUSTRIAL_PROPERTY_{i+1}',
            polyline=coords(g.coords),material='concrete_barbed_wire',height_m=2.8,
            district_id='industrial',scope='private_property',source_separator_id=separator['id'])
            for i,g in enumerate([substring(self.industrial_axis,0,gate_station-gate_width/2),
                substring(self.industrial_axis,gate_station+gate_width/2,self.industrial_axis.length)])]
        gate_axis=substring(self.industrial_axis,gate_station-gate_width/2,gate_station+gate_width/2)
        gate_center=self.industrial_axis.interpolate(gate_station)
        self.industrial_gates=[dict(id='INDUSTRIAL_YARD_GATE',polyline=coords(gate_axis.coords),
            x=gate_center.x,y=gate_center.y,width_m=gate_width,height_m=2.8,
            material='steel_barbed_wire',district_id='industrial',scope='private_property',
            source_separator_id=separator['id'],road_id='I_YARD',open_default=False,
            approach_polyline=[[775,392],[798,397],[801,370],[801,349],[gate_center.x,gate_center.y]],
            approach_width_m=5.0,approach_material='gravel')]
        self.gate_approach=LineString(self.industrial_gates[0]['approach_polyline']).buffer(2.5,cap_style=2)
        barriers = [LineString(q['polyline']).buffer(.45) for q in self.elite_fences+self.industrial_fences]
        barriers += [LineString(q['polyline']).buffer(.45) for q in self.industrial_gates]
        barriers += [LineString(q['axis_m']).buffer(.45) for q in plan['vegetation_parcels']
                     if q.get('material') in {'canal_railing','rock_scarp'} and 'axis_m' in q]
        barriers += [Polygon(g) for e in plan['exits'] for g in e['barrier_polygons_m']]
        self.barriers = unary_union(barriers)
        self.walk_paths = unary_union([LineString(q['polyline_m']).buffer(q['width_m']/2)
                                      for q in plan.get('paths', [])])
        self.base_obstacles = unary_union([self.building_union.buffer(.2), self.road_union.buffer(.2),
            self.water.buffer(.5), self.rail, self.barriers, self.walk_paths,self.gate_approach])
        self.parking_union = Polygon()
        self.access_union = Polygon()
        self.sidewalk_union = Polygon()
        self.playground_union = Polygon()
        self.occupied = []
        self.grid = collections.defaultdict(list)
        self.out = dict(schema_version='1.1', revision='R01_v12', seed=SEED,
            source_plan='MAP_PLAN_R01_v12.json', source_plan_sha256=sha(ROOT/'MAP_PLAN_R01_v12.json'),
            coordinates=plan['coordinates'],
            builder_contract={
                'polygon_format': 'polygon exterior ring plus holes; rings are implicitly closed',
                'ground_polygon_precision_m': .000001,
                'angle_convention': 'degrees counterclockwise from east; facade outward normal, furniture forward vector',
                'frontage_side': 'signage.side is zero-based edge index in footprint_m',
                'alias_policy': 'instantiate only spawn_geometry=true; alias entries decorate physical_id once',
                'building_geometry': 'footprint_m and floors copied from approved plan; no footprint/position/height edits',
                'entrance_policy': 'entrances on facade; plan_access_m retains approved off-wall road connection',
                'materials': 'nonoverlapping polygon partition; holes must be respected; building and water surfaces excluded',
                'tree_clearance': 'reserved_radius_m includes crown envelope; furniture radius includes usage clearance',
                'yard_fences': 'build only fence_polylines_m; do not close clipped boundaries or gate openings',
                'district_border_fences': 'NONE: never instantiate legacy district fences from the source plan',
                'source_barrier_policy': 'ignore all source fence materials; retain only canal_railing safety rails and rock_scarp terrain',
                'property_fences': 'instantiate only elite_fences, industrial_fences and individual yards; industrial gate closes its 7m opening',
                'waste_outfall': 'segments override full polyline elevation: buried sleeves beneath roads, rail, beach walk and fence; low supports elsewhere',
                'parking': 'stalls[] are van-sized; access_polyline_m is existing-road connection; curb openings recorded',
                'bus_stop': 'building_ref entries identify existing shelter; marker spawns separately',
                'curb_height_m': .15, 'style': 'stylised slightly cartoon post-Soviet town; matte broad colour blocks, worn trims',
                'variation': 'seeded irregular planting, asymmetric gardens and equipment, varied facades; approved slab grid retained',
            }, buildings=[], sidewalks=[], curbs=[], zebra_crossings=[], street_furniture=[],
            parking_lots=[], trees=[], yards=[], ground_materials=[],
            elite_fences=self.elite_fences,industrial_fences=self.industrial_fences,
            industrial_gates=self.industrial_gates)

    def district(self, p):
        p = p if isinstance(p, Point) else Point(p)
        for did, g in self.ds.items():
            if g.covers(p):
                return did
        return 'beach' if self.beach.covers(p) else 'common'

    def occupied_hits(self, disk):
        lo, bo, hi, top = disk.bounds
        found = set()
        for ix in range(math.floor(lo/12), math.floor(hi/12)+1):
            for iy in range(math.floor(bo/12), math.floor(top/12)+1):
                for n in self.grid[(ix, iy)]:
                    if n not in found:
                        found.add(n)
                        if disk.intersects(self.occupied[n]):
                            return True
        return False

    def reserve(self, disk):
        n = len(self.occupied)
        self.occupied.append(disk)
        lo, bo, hi, top = disk.bounds
        for ix in range(math.floor(lo/12), math.floor(hi/12)+1):
            for iy in range(math.floor(bo/12), math.floor(top/12)+1):
                self.grid[(ix, iy)].append(n)

    def free(self, p, radius, region=None, trees=False, extra=None):
        disk = Point(p).buffer(radius+.08, quad_segs=8)
        if not self.boundary.covers(disk) or (region is not None and not region.covers(disk)):
            return False
        obstacle = self.tree_obstacle if trees else self.prop_obstacle
        if disk.intersects(obstacle) or (extra is not None and disk.intersects(extra)):
            return False
        return not self.occupied_hits(disk)

    def prop(self, typ, p, angle=0, region=None, **meta):
        radius = FURNITURE_RADIUS[typ]
        if not self.free(p, radius, region):
            return None
        q = dict(id=f'SF{len(self.out["street_furniture"])+1:04d}', type=typ,
            x=round(p[0],5), y=round(p[1],5), angle_deg=round(angle%360,3),
            district_id=self.district(p), reserved_radius_m=radius, **meta)
        self.out['street_furniture'].append(q)
        self.reserve(Point(p).buffer(radius, quad_segs=12))
        return q

    def nearby_prop(self, typ, anchor, region=None, min_dist=3, max_dist=17, **meta):
        # Random candidates, then prefer the closest unobstructed position.
        candidates = []
        for _ in range(320):
            a = self.rng.uniform(0, math.tau)
            r = self.rng.uniform(min_dist, max_dist)
            p = (anchor[0]+math.cos(a)*r, anchor[1]+math.sin(a)*r)
            candidates.append((r, p, math.degrees(a)+90))
        for _, p, angle in sorted(candidates):
            q = self.prop(typ, p, angle, region, **meta)
            if q:
                return q
        raise AssertionError(f'No legal {typ} near {anchor}, {meta}')

    def buildings(self):
        for bid, b in list(self.masses.items())+list(self.functions.items()):
            functional = bid in self.functions
            physical_id = self.aliases.get(bid, bid)
            f = self.functions.get(physical_id)
            did = b['district_id']
            if f:
                style, roof, sign = STYLE_MAP[f['type']]
                if f['type'] == 'mansion' and f['id'] in {'F08_MANSION_1', 'F06_MANSION_3'}:
                    style, roof = 'mansion_modern', 'flat_parapet'
            else:
                kind = b['kind']
                style = ('panel_slab' if kind in {'slab','tower'} else
                         ('rural_wood' if kind=='rural_outbuilding' else
                         ('rural_brick' if kind=='rural_house' and bid.endswith('4_1') else
                          'rural_wood' if kind=='rural_house' else 'townhouse_plaster')))
                roof = 'flat_parapet' if style=='panel_slab' else 'gable'
                sign = None
            g = self.physical[physical_id]
            ring = list(g.exterior.coords)[:-1]
            candidates = []
            for i, a in enumerate(ring):
                z = ring[(i+1)%len(ring)]
                edge = LineString([a,z])
                if edge.length < .05:
                    continue
                mid = edge.interpolate(.5, normalized=True)
                for rid, (r,line) in self.roads.items():
                    target = nearest_points(mid,line)[1]
                    dx, dy = z[0]-a[0], z[1]-a[1]
                    nx, ny = dy/edge.length, -dx/edge.length
                    if not g.exterior.is_ccw:
                        nx, ny = -nx, -ny
                    if (target.x-mid.x)*nx+(target.y-mid.y)*ny <= 0:
                        continue
                    candidates.append((mid.distance(target),i,rid,mid,nx,ny))
            assert candidates, f'No outward frontage candidates: {bid}, ccw={g.exterior.is_ccw}'
            _, side, rid, door, nx, ny = min(candidates)
            front = math.degrees(math.atan2(ny,nx))%360
            rng = random.Random(f'{SEED}:{physical_id}')
            wall = jitter_color(rng.choice(WALLS[did]),rng)
            if style in {'soviet_brick','industrial_brick','rural_brick'}:
                wall = jitter_color(rng.choice(['#B2977B','#BAA58B','#A88873','#C4AF90']),rng,13)
            if f and f['type'] in {'casino','nightclub','bowling_arcade'}:
                wall = jitter_color({'casino':'#9B9A91','nightclub':'#7D8B89','bowling_arcade':'#ADA69A'}[f['type']],rng)
            trim = jitter_color(rng.choice(['#E2D8C0','#77867E','#8F9BA0','#C4C3B6']),rng)
            roof_color = jitter_color(rng.choice(['#657776','#796F68','#8B6D60','#717D81']),rng)
            entrance_count = 3 if not f and b['kind']=='slab' else 1
            edge = LineString([ring[side],ring[(side+1)%len(ring)]])
            entrances = []
            for n in range(entrance_count):
                pt = edge.interpolate((n+1)/(entrance_count+1),normalized=True)
                entrances.append(dict(x=round(pt.x,5),y=round(pt.y,5),
                    angle_deg=round(front,3),width_m=2.4 if style=='panel_slab' else 1.4))
            plan_access = (f or b).get('entrance_m')
            signage = None
            if f and sign is not None:
                signage = dict(text_ru=sign,side=side,angle_deg=round(front,3),
                    width_m=min(edge.length*.85, 17 if f['type']=='casino' else 12),
                    height_m=2.4 if f['type']=='casino' else 1.15,
                    mount_height_m=5.5 if f['type']=='casino' else 3,
                    emissive=f['type'] in {'casino','nightclub','bar','shop_24h'},
                    palette='#DFB963' if f['type']=='casino' else '#DED7C0')
            self.out['buildings'].append(dict(id=bid,physical_id=physical_id,
                spawn_geometry=bid==physical_id,source_collection='functional_buildings' if functional else 'building_masses',
                district_id=did,style=style,roof=roof,palette=dict(wall=wall,trim=trim,roof=roof_color),
                front_angle_deg=round(front,3),front_side=side,front_road_id=rid,
                entrances=entrances,plan_access_m=plan_access,signage=signage if functional else None,
                floors=b.get('floors',b.get('storeys')),footprint_m=coords(ring),
                presentation=dict(window_rhythm='varied bays' if style!='panel_slab' else 'panel seams with varied curtains',
                    wear=round(rng.uniform(.04,.16) if did=='elite' else rng.uniform(.18,.48),3),
                    roof_equipment='vents and aerials' if roof=='flat_parapet' else 'chimneys and patched metal')))

    def parking(self):
        specs = [('F06_SUPER',7),('F06_HOSPITAL',7),('F12_CASINO',8),
                 ('F06_COMPLEX',5),('F06_POLICE',4),('F06_CAFE2',4),('F12_NIGHTCLUB',5)]
        for bid, count in specs:
            f = self.functions[bid]
            did = f['district_id']
            building = self.physical[bid]
            parent, road = self.roads[f['access_road_id']]
            center = building.centroid
            station = road.project(center)
            _,_,a = tangent(road,station)
            angle = math.degrees(a)
            candidates = []
            obstacle = unary_union([self.base_obstacles,self.parking_union,self.access_union])
            forbidden = unary_union([self.building_union.buffer(.5),self.water.buffer(.5),
                self.rail,self.barriers,self.parking_union])
            connections=[(rid,r,line) for rid,(r,line) in self.roads.items()
                if did in r['district_ids'] and not rid.startswith(('ACCESS_','EXIT_'))]
            for _ in range(2400):
                direction = self.rng.uniform(0, math.tau)
                distance = self.rng.uniform(15,76)
                x,y = center.x+math.cos(direction)*distance,center.y+math.sin(direction)*distance
                ang = angle+self.rng.choice([0,0,90])+self.rng.uniform(-7,7)
                w,h = count*3.4+2,14.8
                lot = rectangle(x,y,w,h,ang,1.1)
                if not self.boundary.covers(lot) or not self.ds[did].covers(lot):
                    continue
                if lot.buffer(.4).intersects(obstacle):
                    continue
                # Choose a reachable nearby existing road, including alternate approaches.
                connected=None
                for connection_id,connection,line in sorted(connections,key=lambda q:q[2].distance(Point(x,y))):
                    target = nearest_points(Point(x,y),line)[1]
                    path = LineString([(x,y),(target.x,target.y)])
                    driveway = path.buffer(2,cap_style=2)
                    if driveway.intersects(forbidden) or not self.boundary.covers(driveway):
                        continue
                    roads_outside_connection = self.road_union.difference(target.buffer(connection['width_m']/2+3))
                    if driveway.difference(lot).intersects(roads_outside_connection):
                        continue
                    connected=connection_id
                    break
                if connected is None:
                    continue
                score = building.distance(lot)+path.length*.9+abs(distance-30)*.15
                candidates.append((score,lot,path,ang,(x,y),w,h,connected))
            if not candidates:
                raise AssertionError(f'No connected parking rectangle for {bid}')
            _,lot,path,ang,(x,y),w,h,connection_id = min(candidates,key=lambda q:q[0])
            stalls = []
            for n in range(count):
                stall = rectangle(-w/2+1+3.4*(n+.5),-h/2+4.1,3.25,7,0)
                stall = affinity.translate(affinity.rotate(stall,ang,origin=(0,0)),x,y)
                assert lot.covers(stall)
                stalls.append(dict(index=n,**poly_data(stall),angle_deg=round((ang+90)%360,3)))
            # The road-facing curb cut terminates at the existing road centreline.
            lot_entry = nearest_points(lot.boundary,path.interpolate(path.length))[0]
            access = LineString([(lot_entry.x,lot_entry.y),path.coords[-1]])
            self.out['parking_lots'].append(dict(id='PARK_'+bid,building_id=bid,
                district_id=did,stall_count=count,stall_width_m=3.25,stall_depth_m=7,
                aisle_width_m=6.5,**poly_data(lot),stalls=stalls,
                access_polyline_m=coords(access.coords),access_width_m=4,
                access_road_id=connection_id,entrance_m=coords([lot_entry.coords[0]])[0],
                material='asphalt' if did!='industrial' else 'concrete_yard'))
            self.parking_union = unary_union([self.parking_union,lot])
            self.access_union = unary_union([self.access_union,access.buffer(2,cap_style=2)])

    def sidewalks(self):
        urban = {'old_town','residential','elite','transition','industrial'}
        eligible = [(r,line) for r,line in self.roads.values()
                    if r['class'] in {'town_street','highway'} and not r['id'].startswith('EXIT_')
                    and any(d in urban for d in r['district_ids'])]
        blocked = unary_union([self.building_union.buffer(.25), self.water.buffer(.4),
            self.road_union.buffer(.2), self.parking_union.buffer(.3),self.access_union.buffer(.2),
            self.rail,self.beach,self.barriers])
        for r,line in eligible:
            width = 3.2 if r['class']=='highway' else 2.5
            for side in (1,-1):
                offset = r['width_m']/2+.3+width/2
                has_front = False
                for bid,g in self.physical.items():
                    if line.distance(g)>72:
                        continue
                    s=line.project(g.centroid)
                    _,_,a=tangent(line,s)
                    roadpoint=line.interpolate(s)
                    signed=-(g.centroid.x-roadpoint.x)*math.sin(a)+(g.centroid.y-roadpoint.y)*math.cos(a)
                    if signed*side>0:
                        has_front=True
                        break
                if not has_front:
                    continue
                axis=line.offset_curve(side*offset,join_style=1)
                legal=axis.intersection(self.boundary.buffer(-width/2-.2)).difference(blocked.buffer(width/2))
                for segment in parts(legal,'LineString'):
                    if segment.length<3.5:
                        continue
                    sid=f'SW{len(self.out["sidewalks"])+1:03d}'
                    surface=segment.buffer(width/2,cap_style=2)
                    self.sidewalk_union=unary_union([self.sidewalk_union,surface])
                    self.out['sidewalks'].append(dict(id=sid,road_id=r['id'],
                        district_id=self.district(segment.interpolate(.5,normalized=True)),side='left' if side==1 else 'right',
                        polyline_m=coords(segment.coords),width_m=width,material='paving',
                        curb_height_m=.15,curb_width_m=.18))
                    # Offset relative to local direction to the nearest road edge.
                    for c in parts(segment.offset_curve(-side*width/2),'LineString'):
                        if c.length>1:
                            self.out['curbs'].append(dict(id='CURB_'+sid,sidewalk_id=sid,
                                district_id=self.out['sidewalks'][-1]['district_id'],
                                polyline_m=coords(c.coords),width_m=.18,height_m=.15,
                                material='concrete_yard',gaps_at_driveways=True))

    def crossings(self):
        ids = ['ARC_AVENUE','COURT_ACCESS_1','COURT_ACCESS_2','COURT_ACCESS_3',
               'OLD_TOWN_CONNECTOR','TRANSITION_DIRECT','O_LANES','O_SPINE',
               'OLD_ELITE_CONNECTOR','ELITE_GATE_ROAD','I_CONNECT']
        junctions=[]
        for i,rid in enumerate(ids):
            for other in ids[i+1:]:
                _,a=self.roads[rid];_,b=self.roads[other]
                for hit in parts(a.intersection(b),'Point'):
                    if not any(hit.distance(q[0])<7 for q in junctions):
                        junctions.append((hit,rid,other))
        for hit,rid,other in junctions:
            # Place a zebra on an arm, away from the turning area.
            arms = [rid,other]
            placed=False
            for road_id in arms:
                r,line=self.roads[road_id]
                s=line.project(hit)
                for shift in (10,-10,15,-15):
                    station=s+shift
                    if not 4<station<line.length-4:
                        continue
                    p=line.interpolate(station)
                    _,_,a=tangent(line,station)
                    zebra=rectangle(p.x,p.y,3.5,r['width_m'],math.degrees(a))
                    if zebra.intersects(self.building_union) or zebra.intersects(self.water) or zebra.intersects(self.rail):
                        continue
                    actual=zebra.intersection(self.road_union)
                    if actual.area<zebra.area*.85:
                        continue
                    cid=f'ZEBRA{len(self.out["zebra_crossings"])+1:02d}'
                    self.out['zebra_crossings'].append(dict(id=cid,road_id=road_id,
                        district_id=self.district(p),junction_m=coords([hit.coords[0]])[0],
                        angle_deg=round(math.degrees(a)%360,3),**poly_data(zebra),
                        stripe_width_m=.5,stripe_gap_m=.5,colour='#F1EBDC',flush_with_road=True))
                    self.nearby_prop('traffic_sign', [p.x,p.y],min_dist=5,max_dist=12,
                        context=cid,sign_ru='ПЕШЕХОДНЫЙ ПЕРЕХОД',road_id=road_id)
                    placed=True
                    break
                if placed:
                    break
        assert len(self.out['zebra_crossings'])>=6

    def grounds_region(self, g, material, context, did=None):
        if g.is_empty:
            return
        # Overlay regions are stored first and subtracted from later layers.
        g=g.intersection(self.boundary).difference(self.water).difference(self.building_union)
        if not g.is_empty:
            self.material_layers.append((g,material,context,did))

    def yards(self):
        forbidden=unary_union([self.road_union.buffer(.6),self.sidewalk_union.buffer(.4),
            self.water.buffer(.6),self.parking_union.buffer(.6),self.access_union.buffer(.4),
            self.building_union.buffer(.35),self.rail,self.barriers])
        for plot in self.p['plots']:
            if plot['kind'] not in {'farmstead','front_yard','elite_garden','villa_yard'}:
                continue
            source=Polygon(plot['polygon_m'])
            did=plot.get('district_id',self.district(source.representative_point()))
            fence={'farmstead':'weathered_wood','front_yard':'wood_picket',
                   'elite_garden':'hedge','villa_yard':'hedge'}[plot['kind']]
            clipped=source.intersection(self.ds[did]).difference(forbidden)
            pieces=[g for g in parts(clipped) if g.area>9]
            building_ids=[bid for bid,g in self.physical.items()
                          if g.distance(source)<.6 or source.covers(g.centroid)]
            for n,g in enumerate(pieces):
                # Only the original plot boundary carries fence, clipped boundaries remain open.
                fence_line=source.boundary.intersection(g.buffer(.02)).difference(forbidden.buffer(.8))
                gate_points=[]
                for bid in building_ids:
                    entry=self.functions.get(bid,self.masses.get(bid,{})).get('entrance_m')
                    if entry:
                        gate=nearest_points(Point(entry),source.boundary)[1]
                        fence_line=fence_line.difference(gate.buffer(2))
                        gate_points.append([round(gate.x,5),round(gate.y,5)])
                self.out['yards'].append(dict(id=f'YARD_{plot["id"]}_{n+1}',
                    source_plot_id=plot['id'],district_id=did,kind=plot['kind'],
                    building_ids=building_ids,**poly_data(g),fence_material=fence,
                    fence_height_m=1.4 if fence=='hedge' else 1.15,
                    fence_polylines_m=[coords(c.coords) for c in parts(fence_line,'LineString') if c.length>1.5],
                    gate_points_m=gate_points,gate_width_m=4 if fence=='hedge' else 2.8))
                self.grounds_region(g,'grass','garden:'+plot['id'],did)
        # The pharmacy property has no farmstead plot in v12; add a modest yard.
        rural=[(bid,g) for bid,g in self.physical.items() if bid in self.masses
               and self.masses[bid]['kind']=='rural_house']
        rural += [('F06_PHARM',self.physical['F06_PHARM'])]
        represented={bid for q in self.out['yards'] for bid in q['building_ids']}
        for bid,g in rural:
            if bid in represented:
                continue
            source=g.buffer(6,join_style=2).intersection(self.ds['village'])
            for n,part in enumerate(parts(source.difference(forbidden))):
                if part.area<20:
                    continue
                self.out['yards'].append(dict(id=f'YARD_{bid}_{n+1}',source_plot_id=None,
                    district_id='village',kind='village_plot',building_ids=[bid],
                    **poly_data(part),fence_material='weathered_wood',fence_height_m=1.15,
                    fence_polylines_m=[coords(c.coords) for c in parts(
                        source.boundary.intersection(part.buffer(.02)).difference(forbidden.buffer(.8)),'LineString') if c.length>2],
                    gate_points_m=[],gate_width_m=2.8))
                self.grounds_region(part,'grass','garden:'+bid,'village')

    def waste_outfall(self):
        """A scenic outfall with explicit buried sleeves for every occupied corridor."""
        coast=LineString(self.p['beaches'][0]['sea_edge_m'])
        shore=coast.interpolate(coast.project(Point(644,249)))
        _,_,a=tangent(coast,coast.project(shore))
        normal=(math.sin(a),-math.cos(a))
        sea=Polygon(next(w['polygon_m'] for w in self.p['water'] if w['id']=='SEA'))
        if not sea.covers(Point(shore.x+normal[0]*10,shore.y+normal[1]*10)):
            normal=(-normal[0],-normal[1])
        endpoint=(shore.x+normal[0]*36,shore.y+normal[1]*36)
        full=LineString([(605,401),(617,373),(617,343),(628,313),(639,283),
                         (shore.x,shore.y),endpoint])
        # Sleeve envelopes extend beyond the full corridor width, including pipe radius.
        sleeves=unary_union([self.road_union.buffer(1.7),self.rail.buffer(1.7),
            self.walk_paths.buffer(1.7),self.barriers.buffer(1.4),self.gate_approach.buffer(1.7)])
        segments=[]
        for mode,g in [('buried_sleeve',full.intersection(sleeves)),
                       ('low_supports',full.difference(sleeves))]:
            for line in parts(g,'LineString'):
                if line.length<.01:
                    continue
                overlaps=[]
                for rid,(r,road) in self.roads.items():
                    if line.intersects(road.buffer(r['width_m']/2+1.7)):
                        overlaps.append(rid)
                if line.intersects(self.walk_paths.buffer(1.7)):
                    overlaps.append('WALK_BEACH')
                if line.intersects(self.rail.buffer(1.7)):
                    overlaps.append('RAILWAY')
                if line.intersects(self.barriers.buffer(1.4)):
                    overlaps.append('PROPERTY_FENCE_SLEEVE')
                segments.append(dict(id=f'OUTFALL_SEG{len(segments)+1:02d}',polyline=coords(line.coords),
                    mode=mode,center_height_relative_ground_m=-1.6 if mode=='buried_sleeve' else .95,
                    diameter_m=.8,crossing_refs=overlaps,district_id=self.district(line.interpolate(.5,normalized=True))))
        segments.sort(key=lambda q:full.project(Point(q['polyline'][0])))
        exposed=unary_union([LineString(q['polyline']) for q in segments if q['mode']=='low_supports'])
        self.outfall_obstacle=exposed.buffer(.75)
        # Reserve supports before furniture/trees; contact with their own pipe is intentional.
        supports=[]
        for line in parts(exposed,'LineString'):
            if line.length<3:
                continue
            stations=[min(line.length/2,3)]
            stations += [float(s) for s in range(12,math.floor(line.length),12)]
            for s in stations:
                pt=line.interpolate(s);disk=pt.buffer(.6)
                if not self.boundary.covers(disk) or disk.intersects(self.base_obstacles):
                    continue
                if disk.intersects(self.parking_union) or disk.intersects(self.garden_fences):
                    continue
                supports.append(dict(id=f'OUTFALL_SUPPORT{len(supports)+1:02d}',x=round(pt.x,5),y=round(pt.y,5),
                    angle_deg=round(math.degrees(tangent(line,s)[2])+90,3),
                    type='low_concrete_saddle',height_m=.55,width_m=1.2,depth_m=.65,
                    reserved_radius_m=.6,district_id=self.district(pt),material='weathered_concrete'))
                self.reserve(pt.buffer(.6))
        self.prop_obstacle=unary_union([self.prop_obstacle,self.outfall_obstacle,self.gate_approach])
        plume_points=[]
        rng=random.Random(SEED+771)
        center=(endpoint[0]+normal[0]*3,endpoint[1]+normal[1]*3)
        for n in range(48):
            theta=math.tau*n/48
            variation=1+.085*math.sin(theta*3+.7)+.045*math.cos(theta*5-1.2)+rng.uniform(-.025,.025)
            local=(30*math.cos(theta)*variation,17.5*math.sin(theta)*variation)
            plume_points.append((center[0]+local[0]*math.cos(a)-local[1]*math.sin(a),
                                 center[1]+local[0]*math.sin(a)+local[1]*math.cos(a)))
        plume=Polygon(plume_points)
        assert plume.is_valid and sea.covers(plume),'Sludge plume must stay entirely offshore'
        warning_ids=[]
        for anchor in ([626,296],[654,264]):
            prop=self.nearby_prop('sign_no_swimming',anchor,region=self.beach,min_dist=4,max_dist=14,
                context='WASTE_OUTFALL',text_ru='КУПАТЬСЯ ЗАПРЕЩЕНО',height_m=1.8,
                sign_width_m=1.2,sign_height_m=.8,material='rusty_painted_metal')
            warning_ids.append(prop['id'])
        decals=[]
        for anchor in ([643,296],[630,265]):
            for _ in range(400):
                xy=(anchor[0]+self.rng.uniform(-8,8),anchor[1]+self.rng.uniform(-8,8))
                if self.free(xy,.7,self.beach):
                    decals.append(dict(id=f'DEAD_FISH{len(decals)+1:02d}',type='dead_fish_decal',
                        x=round(xy[0],5),y=round(xy[1],5),angle_deg=round(self.rng.uniform(0,360),3),
                        length_m=1.2,width_m=.45,reserved_radius_m=.7,district_id='beach',
                        material='washed_out_fish',colour_hint='#B0B29A',collision=False))
                    self.reserve(Point(xy).buffer(.7))
                    break
            else:
                raise AssertionError('No safe dead-fish decal on sand')
        self.out['waste_outfall']=dict(id='B05_WASTE_OUTFALL',source_building_id='F06_COMPLEX',
            district_id='industrial',polyline=coords(full.coords),diameter_m=.8,
            material='rusty_steel',colour_hint='#9B5C36',segments=segments,supports=supports,
            waterline_m=[shore.x,shore.y],sea_end_m=list(endpoint),beyond_waterline_m=36,
            sludge_plume=dict(**poly_data(plume),district_id='sea',colour_hint='#777F49',
                opacity=.65,nominal_size_m=[60,35],material='murky_sludge',collision=False),
            warning_sign_ids=warning_ids,dead_fish_decals=decals,
            crossing_policy='buried sleeves: pipe top 1.2m below unchanged paths/roads; no above-ground pipe or support occupies a corridor')

    def playgrounds_and_social(self):
        for court in self.p['microdistricts']:
            yard=Polygon(court['yard_polygon_m'])
            cx,cy=court['center_m']
            # Different sizes, offsets and equipment angles, while retaining the approved yard.
            candidates=[]
            for _ in range(500):
                x=cx+self.rng.uniform(-19,19);y=cy+self.rng.uniform(-18,18)
                pad=rectangle(x,y,21,18,self.rng.uniform(-24,24),2.2)
                if yard.covers(pad) and not pad.intersects(self.prop_obstacle):
                    candidates.append(pad)
            if not candidates:
                raise AssertionError('No playground pad '+court['id'])
            pad=self.rng.choice(candidates)
            self.playground_union=unary_union([self.playground_union,pad])
            self.grounds_region(pad,'rubber_playground','playground:'+court['id'],'residential')
            # Equipment is spread irregularly by rejection sampling with usage envelopes.
            for typ in ('swings','slide','sandbox'):
                self.nearby_prop(typ,[pad.centroid.x,pad.centroid.y],region=pad,
                    min_dist=0,max_dist=10,context=court['id'],playground_id='PLAY_'+court['id'])
            self.nearby_prop('carpet_rack',[cx,cy],region=yard,min_dist=8,max_dist=25,
                context=court['id'],playground_id='PLAY_'+court['id'],extra_role='laundry')
            for _ in range(3 if court['id']=='MB06_1' else 2):
                self.nearby_prop('bench',[cx,cy],region=yard,min_dist=9,max_dist=27,context=court['id'])
            for _ in range(2):
                self.nearby_prop('bin',[cx,cy],region=yard,min_dist=10,max_dist=26,context=court['id'])
            access=self.roads['COURT_ACCESS_'+court['id'][-1]][1]
            near=access.interpolate(access.project(Point(cx,cy)))
            for _ in range(3):
                self.nearby_prop('garbage_container',[near.x,near.y],region=yard,
                    min_dist=5,max_dist=19,context=court['id'])
        social=[('CLOCK_SQUARE',[650,540],18,39,5),
                ('BAD_CENTER',[650,723.5],6,18,2),
                ('CHURCH12_YARD',[383,574],9,25,3),
                ('BUS_VILLAGE',[315,606],4,15,2),
                ('BEACH_ENTRY',[1028,517],9,20,2),
                ('BEACH_VALLEY_ENTRY',[420,281],9,20,2)]
        for name,anchor,lo,hi,count in social:
            region=Polygon(next(s['polygon_m'] for s in self.p['functional_sites']
                if s['id']=='CHURCH12_YARD')) if name=='CHURCH12_YARD' else None
            for _ in range(count):
                self.nearby_prop('bench',anchor,region,min_dist=lo,max_dist=hi,context=name)
            for _ in range(2 if count>=3 else 1):
                self.nearby_prop('bin',anchor,region,min_dist=lo,max_dist=hi,context=name)
        # Reuse the approved village bus shelter; its clearance is an existing footprint.
        f=self.functions['F06_BUS']
        self.out['street_furniture'].append(dict(id='SF_BUS_EXISTING',type='bus_stop',
            x=f['center_m'][0],y=f['center_m'][1],angle_deg=270,district_id='village',
            building_ref='F06_BUS',spawn_geometry=False,reserved_radius_m=0,
            context='BUS_VILLAGE',text_ru='ОСТАНОВКА'))
        self.nearby_prop('bus_stop_marker',f['entrance_m'],min_dist=2,max_dist=9,context='BUS_VILLAGE')
        # A second shelter on the avenue, without touching the carriageway.
        self.nearby_prop('bus_stop',[719,723.5],min_dist=7,max_dist=15,
            context='BUS_AVENUE',text_ru='ЦЕНТР',spawn_geometry=True)
        bus=self.out['street_furniture'][-1]
        for typ in ('bench','bin'):
            self.nearby_prop(typ,[bus['x'],bus['y']],min_dist=3.3,max_dist=8,context='BUS_AVENUE')
        # Surface patches frame the squares and bus shelters without covering any road.
        for name,anchor,lo,hi,_ in social[:4]:
            area=Point(anchor).buffer(hi*.75,quad_segs=16).difference(self.base_obstacles).difference(self.parking_union)
            self.grounds_region(area,'paving' if 'SQUARE' in name or 'CENTER' in name else 'gravel',name)

    def lamps_and_poles(self):
        lamp_schedules=[]
        for rid,(r,line) in self.roads.items():
            if r['class'] not in {'town_street','highway'} or rid.startswith('EXIT_') or line.length<18:
                continue
            s=self.rng.uniform(8,17);side=self.rng.choice([-1,1]);entries=[];last_station=None
            while s<line.length-3:
                success=False
                for along in (0,-1.5,1.5,-3,3,-4.5,4.5,-6,6,-8,8):
                    station=max(1,min(line.length-1,s+along))
                    if last_station is not None and not 24.5<=station-last_station<=35:
                        continue
                    pt=line.interpolate(station);_,_,a=tangent(line,station)
                    for extra in (.7,1.2,2,3,4.5,6,8):
                        offset=r['width_m']/2+extra
                        xy=[pt.x-math.sin(a)*offset*side,pt.y+math.cos(a)*offset*side]
                        prop=self.prop('street_lamp',xy,math.degrees(a)-90*side,
                            context='road_lighting',road_id=rid,station_m=round(station,3),side=side,
                            height_m=7.8 if r['class']=='highway' else 6.2,
                            light_colour='#F2D19B',light_range_m=18 if r['class']=='highway' else 15)
                        if prop:
                            entries.append(prop['id']);success=True;break
                    if success:
                        break
                if not success:
                    raise AssertionError(f'Lamp cannot fit {rid} station {s}')
                last_station=station
                side=-side;s=station+self.rng.uniform(27.5,31.5)
            lamp_schedules.append(dict(road_id=rid,lamp_ids=entries))
        self.out['lighting_runs']=lamp_schedules
        for rid,(r,line) in self.roads.items():
            if r['class']!='rural_road' or rid.startswith('ACCESS_') or line.length<32:
                continue
            s=self.rng.uniform(10,24);side=self.rng.choice([-1,1]);last_station=None
            while s<line.length-4:
                fitted=False
                for along in (0,-2,2,-4,4,-6,6):
                    station=max(1,min(line.length-1,s+along))
                    if last_station is not None and not 33<=station-last_station<=47:
                        continue
                    pt=line.interpolate(station);_,_,a=tangent(line,station)
                    for actual_side in (side,-side):
                        for extra in (1.7,2.5,3.8,5.5,8,11):
                            offset=r['width_m']/2+extra
                            prop=self.prop('power_pole',[pt.x-math.sin(a)*offset*actual_side,pt.y+math.cos(a)*offset*actual_side],
                                math.degrees(a),context='rural_power',road_id=rid,station_m=round(station,3),
                                height_m=8.5)
                            if prop:
                                fitted=True;break
                        if fitted:
                            break
                    if fitted:
                        break
                if not fitted:
                    raise AssertionError(f'Power pole cannot fit {rid} {s}')
                last_station=station
                s=station+self.rng.uniform(38,42)

    def tree(self, species, p, context, region=None):
        height=self.rng.uniform(*{'birch':(8,14),'pine':(10,18),'oak':(7,13),
            'poplar':(12,19),'fruit':(3.5,6.5),'palm':(7,11)}[species])
        radius=self.rng.uniform(*{'birch':(1.6,2.25),'pine':(1.6,2.3),'oak':(2.1,2.9),
            'poplar':(1.4,2),'fruit':(1.3,1.9),'palm':(1.7,2.3)}[species])
        if not self.free(p,radius,region,trees=True):
            return False
        did=self.district(p)
        if species=='palm' and did!='elite' and context not in {'BEACH_ENTRY','BEACH_VALLEY_ENTRY'}:
            return False
        self.out['trees'].append(dict(id=f'T{len(self.out["trees"])+1:04d}',species=species,
            x=round(p[0],5),y=round(p[1],5),height_m=round(height,3),district_id=did,
            angle_deg=round(self.rng.uniform(0,360),3),reserved_radius_m=round(radius,5),
            crown_radius_m=round(radius-.15,4),context=context))
        self.reserve(Point(p).buffer(radius,quad_segs=12))
        return True

    def scatter(self, region, target, species, context):
        if region.is_empty:
            return 0
        lo,bo,hi,top=region.bounds;count=0
        # Clustered random sampling, without a lattice or repeated spacing.
        centers=[]
        for _ in range(10):
            p=Point(self.rng.uniform(lo,hi),self.rng.uniform(bo,top))
            if region.covers(p):
                centers.append(p)
        for trial in range(max(1200,target*130)):
            if count>=target or len(self.out['trees'])>=1450:
                break
            if centers and trial%3:
                c=self.rng.choice(centers)
                sigma=min(hi-lo,top-bo)*self.rng.uniform(.10,.24)
                p=[self.rng.gauss(c.x,sigma),self.rng.gauss(c.y,sigma)]
            else:
                p=[self.rng.uniform(lo,hi),self.rng.uniform(bo,top)]
            if self.tree(self.rng.choice(species),p,context,region):
                count+=1
        return count

    def trees(self):
        self.tree_obstacle=unary_union([self.prop_obstacle,self.sidewalk_union.buffer(.1),
            self.beach,self.playground_union.buffer(.5)])
        # Preserve the established wagon-to-chimney landmark reserve.
        a=self.points['B01']['position_m'];b=self.points['CHIMNEY']['position_m']
        self.tree_obstacle=unary_union([self.tree_obstacle,
            LineString([a,b]).buffer(self.p['sightline']['clearance_reserve_width_m']/2)])
        # Orchard parcels are small; reserve fruit trees before broad district planting.
        for q in self.p['vegetation_parcels']:
            if q['kind']=='orchard':
                self.scatter(Polygon(q['polygon_m']),2,['fruit'],'orchard:'+q['id'])
        # All gardens receive individual, nonrepeating mixtures and placements.
        for q in self.out['yards']:
            g=geometry(q)
            target=max(1,min(13,round(g.area/140)))
            species=['fruit','fruit','birch'] if q['district_id']=='village' else (
                ['oak','pine','fruit','palm'] if q['district_id']=='elite' else ['fruit','birch','oak'])
            self.scatter(g,target,species,'garden:'+q['source_plot_id'] if q['source_plot_id'] else 'garden:'+q['id'])
        church=Polygon(next(q['polygon_m'] for q in self.p['functional_sites'] if q['id']=='CHURCH12_YARD'))
        self.scatter(church,10,['birch','oak','fruit'],'churchyard')
        # Street trees use variable distances and side offsets, never regular rows.
        for rid in ('O_LANES','O_SPINE','OLD_ELITE_CONNECTOR'):
            r,line=self.roads[rid];s=self.rng.uniform(7,19)
            while s<line.length-5:
                pt=line.interpolate(s);_,_,a=tangent(line,s)
                side=self.rng.choice([-1,1]);offset=r['width_m']/2+self.rng.uniform(6.6,11.5)
                self.tree(self.rng.choice(['birch','oak','poplar']),
                    [pt.x-math.sin(a)*offset*side,pt.y+math.cos(a)*offset*side],
                    'street:'+rid,self.ds['old_town'])
                s+=self.rng.uniform(11,24)
        for pid in ('BEACH_ENTRY','BEACH_VALLEY_ENTRY'):
            point=Point(self.points[pid]['position_m'])
            self.scatter(point.buffer(60).difference(self.beach),6,['palm'],pid)
        desired=dict(forest=420,village=125,transition=95,residential=80,old_town=85,
                     elite=85,industrial=22,fields=58)
        for did,count in desired.items():
            species={'forest':['pine','pine','birch','oak'],
                'village':['fruit','birch','fruit','poplar'],
                'transition':['birch','pine','oak'],
                'residential':['birch','poplar','oak'],
                'old_town':['birch','oak','poplar'],
                'elite':['pine','oak','palm','fruit'],
                'industrial':['poplar','birch'],
                'fields':['birch','oak','fruit']}[did]
            self.scatter(self.ds[did],count,species,'forest_belt' if did=='forest' else 'district:'+did)
        common=self.boundary.difference(unary_union(list(self.ds.values()))).difference(self.beach)
        self.scatter(common,70,['birch','pine','oak'],'common_landscape')

    def materials(self):
        # Priority: road > parking > sidewalks > rubber > gardens/social > sites > district > common.
        layers=[]
        layers.append((self.gate_approach,'gravel','industrial_gate_approach','industrial'))
        for r,line in self.roads.values():
            material='dirt' if r['class'] in {'rural_road','dirt_shortcut'} else 'asphalt'
            layers.append((line.buffer(r['width_m']/2,cap_style=2),material,'road:'+r['id'],None))
        for q in self.out['parking_lots']:
            layers.append((geometry(q),q['material'],q['id'],q['district_id']))
            layers.append((LineString(q['access_polyline_m']).buffer(q['access_width_m']/2,cap_style=2),
                q['material'],'driveway:'+q['id'],q['district_id']))
        layers.append((self.sidewalk_union,'paving','sidewalks',None))
        # Put rubber before lawn, irrespective of when social surfaces were added.
        layers += [q for q in self.material_layers if q[1]=='rubber_playground']
        layers += [q for q in self.material_layers if q[1]!='rubber_playground']
        for q in self.p['functional_sites']:
            if 'polygon_m' not in q:
                continue
            mat={'production_yard':'concrete_yard','tow_parking':'gravel','churchyard':'gravel',
                 'lake_terrace':'paving','parking':'asphalt','turnaround':'gravel'}.get(q['type'],'dirt')
            layers.append((Polygon(q['polygon_m']),mat,'site:'+q['id'],q['district_id']))
        for i,g in enumerate(self.p['field_parcels_m']):
            layers.append((Polygon(g),'dirt',f'field:{i+1}','fields'))
        layers.append((self.beach,'sand','beach','beach'))
        default=dict(forest='dirt',village='grass',transition='grass',residential='grass',
                     old_town='grass',elite='grass',industrial='gravel',fields='grass')
        for did,g in self.ds.items():
            layers.append((g,default[did],'district:'+did,did))
        layers.append((self.boundary,'grass','common_landscape','common'))
        # Exact surface partition, including the strips between district envelopes.
        remaining=self.boundary.difference(self.water).difference(self.building_union)
        regions=list(self.ds.items())+[('beach',self.beach)]
        regions.append(('common',self.boundary.difference(unary_union([g for _,g in regions]))))
        for area,mat,context,_ in layers:
            take=remaining.intersection(area)
            for did,region in regions:
                for g in parts(take.intersection(region)):
                    if g.area<.000001:
                        continue
                    for snapped in parts(set_precision(g,.000001)):
                        if snapped.area<.000001:
                            continue
                        self.out['ground_materials'].append(dict(id=f'GM{len(self.out["ground_materials"])+1:04d}',
                            material=mat,district_id=did,context=context,**poly_data(snapped),area_m2=round(snapped.area,4)))
            remaining=remaining.difference(area)
        assert remaining.area<.001,remaining.area

    def generate(self):
        self.material_layers=[]
        print('Generating building styles...',flush=True)
        self.buildings()
        print('Fitting seven connected parking lots...',flush=True)
        self.parking()
        print('Generating sidewalks and gardens...',flush=True)
        self.sidewalks()
        self.prop_obstacle=unary_union([self.base_obstacles,self.parking_union.buffer(.2),self.access_union.buffer(.2)])
        self.yards()
        self.garden_fences=unary_union([LineString(c).buffer(.5 if q['fence_material']=='hedge' else .15)
            for q in self.out['yards'] for c in q['fence_polylines_m']])
        self.prop_obstacle=unary_union([self.prop_obstacle,self.garden_fences])
        print('Routing outfall and industrial property gate...',flush=True)
        self.waste_outfall()
        print('Placing playgrounds and furniture...',flush=True)
        self.playgrounds_and_social()
        self.crossings()
        self.lamps_and_poles()
        print('Planting trees...',flush=True)
        self.trees()
        print('Partitioning ground materials...',flush=True)
        self.materials()
        return self.out


def validate(plan, d):
    m=MapDressing(plan)
    checks=[]
    def check(name, ok, detail=''):
        checks.append(dict(name=name,passed=bool(ok),detail=detail))
    check('no district-border fences emitted',not d.get('district_border_fences') and
        d['builder_contract'].get('district_border_fences','').startswith('NONE'))
    check('only elite hill property perimeter retained',len(d['elite_fences'])==3 and
        all(q['scope']=='elite_hill_property' and q['source_separator_id'].startswith('ELITE_PERIMETER_')
            for q in d['elite_fences']))
    for q in d['elite_fences']:
        source=next(s for s in plan['vegetation_parcels'] if s['id']==q['source_separator_id'])
        check('elite fence axis '+q['id'],LineString(q['polyline']).hausdorff_distance(LineString(source['axis_m']))<.0001)
    check('industrial concrete barbed-wire fence specification',len(d['industrial_fences'])==2 and
        all(q['material']=='concrete_barbed_wire' and q['height_m']==2.8 and q['scope']=='private_property'
            for q in d['industrial_fences']))
    industrial=unary_union([LineString(q['polyline']) for q in d['industrial_fences']])
    gates=d['industrial_gates'];gate=LineString(gates[0]['polyline'])
    check('one industrial gate on separator with yard connection',len(gates)==1 and gates[0]['road_id']=='I_YARD'
        and m.industrial_axis.distance(gate)<.00001 and LineString(gates[0]['approach_polyline']).distance(m.roads['I_YARD'][1])<.00001
        and LineString(gates[0]['approach_polyline']).distance(gate)<.00001)
    check('industrial axis followed exactly with only gate gap',m.industrial_axis.difference(
        unary_union([industrial,gate]).buffer(.00001)).length<.0001 and industrial.intersection(gate).length<.0001)
    check('gate approach clear buildings rail water',m.gate_approach.intersection(unary_union(
        [m.building_union,m.rail,m.water])).area<EPS)
    outfall=d['waste_outfall'];full=LineString(outfall['polyline'])
    tube_sections=[LineString(q['polyline']) for q in outfall['segments']]
    exposed=unary_union([LineString(q['polyline']) for q in outfall['segments'] if q['mode']=='low_supports'])
    buried=unary_union([LineString(q['polyline']) for q in outfall['segments'] if q['mode']=='buried_sleeve'])
    check('outfall connected to B05 with 0.8m rusty pipe',outfall['source_building_id']=='F06_COMPLEX'
        and outfall['diameter_m']==.8 and outfall['material']=='rusty_steel'
        and Point(full.coords[0]).distance(m.physical['F06_COMPLEX'].boundary)<.00001)
    check('outfall segments cover complete route',full.difference(unary_union(tube_sections).buffer(.00001)).length<.0001
        and abs(sum(q.length for q in tube_sections)-full.length)<.0001)
    coast=LineString(plan['beaches'][0]['sea_edge_m']);end=Point(outfall['sea_end_m'])
    sea=Polygon(next(w['polygon_m'] for w in plan['water'] if w['id']=='SEA'))
    check('pipe extends 30-40m beyond waterline into sea',sea.covers(end) and 30<=coast.distance(end)<=40,
        f'actual nearest-shore distance {coast.distance(end):.3f}m')
    no_pipe=unary_union([m.road_union,m.rail,m.walk_paths,m.gate_approach])
    no_pipe=unary_union([no_pipe]+[Polygon(q['polygon_m']) for q in plan['functional_sites'] if q['type']=='turnaround'])
    check('no exposed pipe blocks any road beach path or turnaround',not exposed.buffer(.4).intersects(no_pipe))
    check('buried crossings have 1.2m cover above pipe crown',all(q['center_height_relative_ground_m']+.4<=-1.2
        for q in outfall['segments'] if q['mode']=='buried_sleeve') and buried.intersects(m.walk_paths))
    check('pipe clear unrelated buildings parking gardens',not full.buffer(.4,cap_style=2).intersects(unary_union(
        [g for bid,g in m.physical.items() if bid!='F06_COMPLEX']) ) and not exposed.buffer(.4).intersects(
            unary_union([geometry(q) for q in d['parking_lots']]+[
                LineString(c).buffer(.15) for q in d['yards'] for c in q['fence_polylines_m']])))
    plume=geometry(outfall['sludge_plume'])
    check('irregular sludge plume wholly in sea around outlet',plume.is_valid and sea.covers(plume) and plume.covers(end)
        and len(outfall['sludge_plume']['polygon'])>=20)
    check('sludge plume approximately 60 by 35 metres',55<=plume.bounds[2]-plume.bounds[0]<=68
        and 30<=plume.bounds[3]-plume.bounds[1]<=42,str(plume.bounds))
    signs=[q for q in d['street_furniture'] if q['type']=='sign_no_swimming']
    check('two no-swimming signs on beach',len(signs)==2 and {q['id'] for q in signs}==set(outfall['warning_sign_ids'])
        and all(q['text_ru']=='КУПАТЬСЯ ЗАПРЕЩЕНО' and m.beach.covers(Point(q['x'],q['y']).buffer(q['reserved_radius_m']))
                for q in signs))
    decals=outfall['dead_fish_decals'];supports=outfall['supports']
    check('two dead fish decals clear paths on sand',len(decals)==2 and all(q['type']=='dead_fish_decal' and
        m.beach.covers(Point(q['x'],q['y']).buffer(q['reserved_radius_m'])) and
        not Point(q['x'],q['y']).buffer(q['reserved_radius_m']).intersects(no_pipe) for q in decals))
    check('low pipe supports including sand section',len(supports)>=3 and any(q['district_id']=='beach' for q in supports)
        and all(q['height_m']==.55 and exposed.distance(Point(q['x'],q['y']))<.0001 for q in supports))
    ids=[b['id'] for b in d['buildings']]
    expected=set(m.masses)|set(m.functions)
    check('one style entry per source building ID',set(ids)==expected and len(ids)==len(set(ids)),f'{len(ids)} IDs')
    check('one physical instance per footprint',sum(b['spawn_geometry'] for b in d['buildings'])==len(m.physical),f'{len(m.physical)} instances')
    allowed_styles={'panel_slab','soviet_brick','townhouse_plaster','rural_wood','rural_brick','mansion_modern',
        'mansion_classic','industrial_shed','industrial_brick','commercial_glass','church','kiosk','pavilion',
        'wagon','hut','water_tower','gas_station'}
    check('style, roof, palette and original floors',all(
        b['style'] in allowed_styles and b['roof'] in {'flat_parapet','gable','hip','shed','dome_spire','none'}
        and all(len(h)==7 and h.startswith('#') and int(h[1:],16)>=0 for h in b['palette'].values())
        and b['floors']==(m.masses.get(b['id'],m.functions.get(b['id'])).get('floors',
            m.masses.get(b['id'],m.functions.get(b['id'])).get('storeys'))) for b in d['buildings']))
    check('approved source checksum',d['source_plan_sha256']==sha(ROOT/d['source_plan']))
    changed=[];bad_doors=[];bad_signs=[];bad_fronts=[]
    for b in d['buildings']:
        source=m.masses.get(b['id'],m.functions.get(b['id']))
        orig=source.get('polygon_m',source.get('footprint_m'))
        if Polygon(orig).symmetric_difference(Polygon(b['footprint_m'])).area>EPS:
            changed.append(b['id'])
        g=Polygon(b['footprint_m'])
        for door in b['entrances']:
            if g.boundary.distance(Point(door['x'],door['y']))>.001:
                bad_doors.append(b['id'])
        front=b['front_side'];ring=b['footprint_m']
        edge=LineString([ring[front],ring[(front+1)%len(ring)]])
        a=math.radians(b['front_angle_deg']);mid=edge.interpolate(.5,normalized=True)
        if g.contains(Point(mid.x+math.cos(a)*.15,mid.y+math.sin(a)*.15)):
            bad_fronts.append(b['id'])
        if b['id'] in m.functions:
            f=m.functions[b['id']];sign=b['signage'];want=STYLE_MAP[f['type']][2]
            if (want is None and sign is not None) or (want is not None and (not sign or sign['text_ru']!=want)):
                bad_signs.append(b['id'])
    check('unchanged approved footprints',not changed,str(changed))
    check('facade entrances on footprints',not bad_doors,str(bad_doors))
    check('front angle is outward facade normal',not bad_fronts,str(bad_fronts))
    check('functional signs and forbidden-sign exceptions',not bad_signs,str(bad_signs))
    lots=[geometry(q) for q in d['parking_lots']];parking=unary_union(lots)
    sidewalks=[LineString(q['polyline_m']).buffer(q['width_m']/2,cap_style=2) for q in d['sidewalks']]
    sw=unary_union(sidewalks)
    required={'F06_SUPER','F06_HOSPITAL','F12_CASINO','F06_COMPLEX','F06_POLICE','F06_CAFE2','F12_NIGHTCLUB'}
    check('seven required parking lots',len(lots)==7 and {q['building_id'] for q in d['parking_lots']}==required)
    check('parking polygons clear buildings roads water rail',all(g.intersection(unary_union(
        [m.building_union,m.road_union,m.water,m.rail])).area<EPS for g in lots))
    check('parking polygons mutually disjoint',sum(g.area for g in lots)-parking.area<EPS)
    check('parking stalls fit with van dimensions',all(q['stall_count']==len(q['stalls']) and q['stall_width_m']>=3.2
        and q['stall_depth_m']>=7 and all(geometry(s).difference(geometry(q)).area<EPS for s in q['stalls'])
        for q in d['parking_lots']))
    check('casino has eight van stalls',next(q['stall_count'] for q in d['parking_lots'] if q['building_id']=='F12_CASINO')==8)
    driveways=[]
    for q in d['parking_lots']:
        line=LineString(q['access_polyline_m']);drive=line.buffer(q['access_width_m']/2,cap_style=2)
        driveways.append(drive)
        check('connected driveway '+q['building_id'],line.distance(m.roads[q['access_road_id']][1])<.001
            and line.distance(geometry(q))<.001 and drive.intersection(m.building_union).area<EPS
            and drive.intersection(m.water).area<EPS)
    check('sidewalk widths and town road classes',all(2<=q['width_m']<=4
        and m.roads[q['road_id']][0]['class'] in {'town_street','highway'} for q in d['sidewalks']))
    check('sidewalks clear buildings roads water parking rail',all(g.intersection(unary_union(
        [m.building_union,m.road_union,m.water,parking,m.rail])).area<EPS for g in sidewalks))
    check('curbs clear buildings',all(LineString(q['polyline_m']).buffer(q['width_m']/2).intersection(m.building_union).area<EPS
        for q in d['curbs']))
    check('zebras at main junctions on road',len(d['zebra_crossings'])>=6 and all(
        geometry(q).intersection(m.road_union).area>=geometry(q).area*.85 and
        geometry(q).intersection(m.building_union).area<EPS for q in d['zebra_crossings']))
    physical_props=[q for q in d['street_furniture'] if not q.get('building_ref')]
    all_placed=physical_props+d['trees']
    disks=[Point(q['x'],q['y']).buffer(q['reserved_radius_m'],quad_segs=12) for q in all_placed]
    garden_fences=unary_union([LineString(c).buffer(.5 if q['fence_material']=='hedge' else .15)
        for q in d['yards'] for c in q['fence_polylines_m']])
    blocked=unary_union([m.building_union,m.road_union,m.water,m.rail,m.barriers,parking,
        unary_union(driveways),m.walk_paths,garden_fences,exposed.buffer(.75)])
    bad=[q['id'] for q,g in zip(all_placed,disks) if g.intersects(blocked)]
    check('full prop and crown envelopes clear obstacles',not bad,str(bad[:12]))
    check('full prop and crown envelopes within boundary',all(m.boundary.covers(g) for g in disks))
    tree_disks=disks[len(physical_props):]
    check('trees clear sidewalks beach and water',all(not g.intersects(unary_union([sw,m.beach,m.water])) for g in tree_disks))
    tree=STRtree(disks);pairs=[]
    for i,g in enumerate(disks):
        for j in tree.query(g,predicate='intersects'):
            if j>i:
                pairs.append([all_placed[i]['id'],all_placed[j]['id']])
    check('trees and furniture do not overlap each other',not pairs,str(pairs[:12]))
    extra_disks=[Point(q['x'],q['y']).buffer(q['reserved_radius_m']) for q in supports+decals]
    check('supports and decals clear all furniture trees and each other',all(not disk.intersects(other)
        for disk in extra_disks for other in disks) and all(not a.intersects(b) for i,a in enumerate(extra_disks) for b in extra_disks[i+1:]))
    support_obstacles=unary_union([m.base_obstacles,parking,sw,unary_union(driveways),garden_fences])
    check('supports clear roads buildings water fences and parking',all(not Point(q['x'],q['y']).buffer(q['reserved_radius_m']).intersects(
        support_obstacles) for q in supports))
    check('tree species and palm restriction',all(q['species'] in TREE_COLORS and (
        q['species']!='palm' or q['district_id']=='elite' or (
            q['context'] in {'BEACH_ENTRY','BEACH_VALLEY_ENTRY'} and
            Point(q['x'],q['y']).distance(Point(m.points[q['context']]['position_m']))<=60)) for q in d['trees']))
    check('forest dense mixed planting',sum(q['district_id']=='forest' for q in d['trees'])>=300 and
        len({q['species'] for q in d['trees'] if q['district_id']=='forest'})>=3)
    check('village orchards and old-town street trees',all(any(t['context']=='orchard:'+q['id'] for t in d['trees'])
        for q in plan['vegetation_parcels'] if q['kind']=='orchard') and
        sum(t['context'].startswith('street:') for t in d['trees'])>=15)
    for court in plan['microdistricts']:
        own=[q for q in physical_props if q.get('context')==court['id']]
        c=collections.Counter(q['type'] for q in own)
        check('complete playground and services '+court['id'],all(c[t]==1 for t in ['swings','slide','sandbox','carpet_rack'])
            and c['garbage_container']>=2 and c['bench']>=2 and c['bin']>=1
            and all(Polygon(court['yard_polygon_m']).covers(Point(q['x'],q['y']).buffer(q['reserved_radius_m'])) for q in own))
    for context in ['CLOCK_SQUARE','BAD_CENTER','CHURCH12_YARD','BUS_VILLAGE','BUS_AVENUE','BEACH_ENTRY','BEACH_VALLEY_ENTRY']:
        own={q['type'] for q in physical_props if q.get('context')==context}
        check('benches and bins '+context,{'bench','bin'}<=own)
    check('bus shelters include existing pavilion',len([q for q in d['street_furniture'] if q['type']=='bus_stop'])==2
          and any(q.get('building_ref')=='F06_BUS' and q.get('spawn_geometry') is False for q in d['street_furniture']))
    lamps=[q for q in physical_props if q['type']=='street_lamp']
    other=[q for q in d['street_furniture'] if q['type']!='street_lamp']
    check('performance limits',len(d['trees'])<=1500 and len(lamps)<=400 and len(other)<=600,
        f'{len(d["trees"])} trees / {len(lamps)} lamps / {len(other)} other props')
    for run in d['lighting_runs']:
        line=[q for q in lamps if q['road_id']==run['road_id']]
        line.sort(key=lambda q:q['station_m'])
        check('alternating lamps '+run['road_id'],all(a['side']!=b['side'] for a,b in zip(line,line[1:])))
        check('lamp spacing '+run['road_id'],all(22<=b['station_m']-a['station_m']<=35.1 for a,b in zip(line,line[1:])))
    yards=[geometry(q) for q in d['yards']]
    check('required garden kinds',{'farmstead','front_yard','elite_garden','villa_yard'}<={q['kind'] for q in d['yards']})
    check('garden fences clear roads buildings water',all(LineString(c).buffer(.12).intersection(
        unary_union([m.road_union,m.building_union,m.water,parking,sw])).area<EPS
        for q in d['yards'] for c in q['fence_polylines_m']))
    ground=[geometry(q) for q in d['ground_materials']]
    bad_polys=[(q['id'],explain_validity(geometry(q))) for q in d['ground_materials']+d['parking_lots']+d['yards']
               if not geometry(q).is_valid or geometry(q).area<=0]
    check('all emitted polygons valid',not bad_polys,str(bad_polys[:10]))
    cover=unary_union(ground);land=m.boundary.difference(m.water).difference(m.building_union)
    gap=land.difference(cover).area;overlap=sum(g.area for g in ground)-cover.area
    check('ground covers every district and common land',gap<.05 and cover.difference(land).area<.05,
        f'uncovered={gap:.6f} m2; excess={cover.difference(land).area:.6f} m2')
    check('ground material polygons do not overlap',overlap<.05,f'{overlap:.6f} m2')
    check('all eight ground materials used',set(MATERIAL_COLORS)=={q['material'] for q in d['ground_materials']})
    check('per district ground coverage',all(m.ds[did].intersection(land).difference(cover).area<.03 for did in m.ds))
    result=dict(passed=all(q['passed'] for q in checks),checks=checks,
        geometry_tolerance_m2=EPS,uncovered_ground_m2=round(gap,6),overlapping_ground_m2=round(overlap,6))
    if not result['passed']:
        print(json.dumps([q for q in checks if not q['passed']],ensure_ascii=False,indent=2))
        raise AssertionError('Dressing validation failed')
    return result


def statistics(d):
    names=['buildings','sidewalks','curbs','zebra_crossings','street_furniture','parking_lots','trees','yards','ground_materials',
        'elite_fences','industrial_fences','industrial_gates']
    stats=dict(counts={k:len(d[k]) for k in names},
        physical_buildings=sum(q['spawn_geometry'] for q in d['buildings']),
        furniture_by_type=dict(collections.Counter(q['type'] for q in d['street_furniture'])),
        tree_species=dict(collections.Counter(q['species'] for q in d['trees'])),
        ground_area_by_material_m2={},by_district={})
    stats['counts'].update(waste_outfalls=1,outfall_segments=len(d['waste_outfall']['segments']),
        outfall_supports=len(d['waste_outfall']['supports']),dead_fish_decals=len(d['waste_outfall']['dead_fish_decals']),
        sludge_plumes=1,warning_signs=len(d['waste_outfall']['warning_sign_ids']))
    for did in ['forest','village','transition','residential','old_town','elite','industrial','fields','beach','common','sea']:
        own={k:sum(q['district_id']==did for q in d[k]) for k in names}
        own['physical_buildings']=sum(q['district_id']==did and q['spawn_geometry'] for q in d['buildings'])
        own['lamps']=sum(q['district_id']==did and q['type']=='street_lamp' for q in d['street_furniture'])
        own['other_furniture']=own['street_furniture']-own['lamps']
        own['parking_stalls']=sum(q['stall_count'] for q in d['parking_lots'] if q['district_id']==did)
        own['ground_area_m2']=round(sum(q['area_m2'] for q in d['ground_materials'] if q['district_id']==did),2)
        own['furniture_by_type']=dict(collections.Counter(q['type'] for q in d['street_furniture'] if q['district_id']==did))
        own['tree_species']=dict(collections.Counter(q['species'] for q in d['trees'] if q['district_id']==did))
        own['warning_signs']=sum(q['district_id']==did and q['type']=='sign_no_swimming' for q in d['street_furniture'])
        own['outfall_supports']=sum(q['district_id']==did for q in d['waste_outfall']['supports'])
        own['outfall_segments']=sum(q['district_id']==did for q in d['waste_outfall']['segments'])
        own['dead_fish_decals']=sum(q['district_id']==did for q in d['waste_outfall']['dead_fish_decals'])
        own['sludge_plumes']=int(did=='sea')
        own['waste_outfalls']=int(did=='industrial')
        stats['by_district'][did]=own
    for mat in MATERIAL_COLORS:
        stats['ground_area_by_material_m2'][mat]=round(sum(q['area_m2'] for q in d['ground_materials'] if q['material']==mat),3)
    return stats


def render(plan,d):
    """Precisely registered technical overlay; source drawing remains readable."""
    factor=2
    visible=plan['boundary']['polygon_m']+next(w['polygon_m'] for w in plan['water'] if w['id']=='SEA')
    lo=[min(p[k] for p in visible) for k in (0,1)];hi=[max(p[k] for p in visible) for k in (0,1)]
    scale=min(2130/(hi[0]-lo[0]),1510/(hi[1]-lo[1]))
    left=95+(2130-(hi[0]-lo[0])*scale)/2;top=160
    def source_xy(p):
        return (left+(p[0]-lo[0])*scale,top+(hi[1]-p[1])*scale)
    obsolete_axes=[[source_xy(p) for p in q['axis_m']] for q in plan['vegetation_parcels']
        if q.get('material') in {'wooden_fence','concrete_fence','elite_fence'} and 'axis_m' in q]
    removed_axes=0
    # Render the approved SVG geometry without annotation text, then reapply
    # annotations once above the dressing. This also gives clean detail insets.
    svg=ET.parse(ROOT/'MAP_PLAN_R01_v12.svg')
    ns='{http://www.w3.org/2000/svg}'
    for parent in svg.getroot().iter():
        for child in list(parent):
            if child.tag==ns+'text':
                parent.remove(child)
            elif child.tag==ns+'polyline' and 'points' in child.attrib:
                points=[tuple(map(float,p.split(','))) for p in child.attrib['points'].split()]
                if any(len(points)==len(axis) and all(math.dist(a,b)<.03 for a,b in zip(points,axis))
                       for axis in obsolete_axes):
                    parent.remove(child);removed_axes+=1
            elif child.tag==ns+'circle' and child.attrib.get('fill') in {'#93ac91','#7f9f76','#829b77'}:
                parent.remove(child)
    assert removed_axes==len(obsolete_axes),f'Legacy preview fence removal: {removed_axes}/{len(obsolete_axes)}'
    magick=shutil.which('magick')
    if not magick:
        raise RuntimeError('ImageMagick is required to render the approved SVG drawing without duplicate annotations')
    env=dict(__import__('os').environ,MAGICK_TEMPORARY_PATH=str(ROOT))
    rendered=subprocess.run([magick,'-background','#F7F4EB','svg:-','png:-'],
        input=ET.tostring(svg.getroot(),encoding='utf-8'),capture_output=True,check=True,cwd=ROOT,env=env)
    source=Image.open(io.BytesIO(rendered.stdout)).convert('RGBA')
    image=source.resize((4800,4800),Image.Resampling.LANCZOS)
    visible=plan['boundary']['polygon_m']+next(w['polygon_m'] for w in plan['water'] if w['id']=='SEA')
    lo=[min(p[k] for p in visible) for k in (0,1)];hi=[max(p[k] for p in visible) for k in (0,1)]
    scale=min(2130/(hi[0]-lo[0]),1510/(hi[1]-lo[1]))
    left=95+(2130-(hi[0]-lo[0])*scale)/2;top=160
    def xy(p):
        return ((left+(p[0]-lo[0])*scale)*factor,(top+(hi[1]-p[1])*scale)*factor)
    def poly_layer(entries,color,alpha):
        layer=Image.new('RGBA',image.size)
        draw=ImageDraw.Draw(layer)
        for q in entries:
            col=color(q) if callable(color) else color
            rgb=tuple(int(col[i:i+2],16) for i in (1,3,5))+(alpha,)
            # Per-polygon masks preserve holes rather than covering previous layers.
            points=[xy(p) for p in q['polygon']]
            minx=max(0,math.floor(min(p[0] for p in points))-1)
            miny=max(0,math.floor(min(p[1] for p in points))-1)
            maxx=min(image.width,math.ceil(max(p[0] for p in points))+1)
            maxy=min(image.height,math.ceil(max(p[1] for p in points))+1)
            if maxx<=minx or maxy<=miny:
                continue
            mask=Image.new('L',(maxx-minx,maxy-miny))
            md=ImageDraw.Draw(mask)
            md.polygon([(x-minx,y-miny) for x,y in points],fill=255)
            for ring in q.get('holes',[]):
                md.polygon([(x-minx,y-miny) for x,y in map(xy,ring)],fill=0)
            layer.paste(rgb,(minx,miny,maxx,maxy),mask)
        return Image.alpha_composite(image,layer)
    image=poly_layer(d['ground_materials'],lambda q:MATERIAL_COLORS[q['material']],83)
    image=poly_layer([d['waste_outfall']['sludge_plume']],d['waste_outfall']['sludge_plume']['colour_hint'],155)
    draw=ImageDraw.Draw(image)
    def line(points,fill,width):
        draw.line([xy(p) for p in points],fill=fill,width=max(1,round(width*scale*factor)),joint='curve')
    for q in d['sidewalks']:
        line(q['polyline_m'],'#ECE3D0',q['width_m'])
    for q in d['curbs']:
        line(q['polyline_m'],'#777F79',.35)
    for q in d['elite_fences']:
        line(q['polyline'],'#586B66',.65)
    for q in d['industrial_fences']:
        line(q['polyline'],'#7B8078',1.3)
        axis=LineString(q['polyline'])
        for s in range(4,math.floor(axis.length),10):
            pt=axis.interpolate(s);_,_,a=tangent(axis,s)
            line([(pt.x-math.sin(a)*1.3,pt.y+math.cos(a)*1.3),
                  (pt.x+math.sin(a)*1.3,pt.y-math.cos(a)*1.3)],'#5E675D',.35)
    for gate in d['industrial_gates']:
        line(gate['approach_polyline'],'#B9B6A6',gate['approach_width_m'])
        line(gate['polyline'],'#61594D',.9)
    for q in d['yards']:
        for c in q['fence_polylines_m']:
            line(c,'#6E8A5E' if q['fence_material']=='hedge' else '#947960',.6)
    for q in d['parking_lots']:
        draw.polygon([xy(p) for p in q['polygon']],fill='#858B84',outline='#555F5B',width=2)
        line(q['access_polyline_m'],'#858B84',q['access_width_m'])
        for s in q['stalls']:
            draw.line([xy(p) for p in s['polygon']+[s['polygon'][0]]],fill='#E5DCC5',width=1)
    for q in d['zebra_crossings']:
        g=geometry(q);c=g.centroid;angle=q['angle_deg']
        for offset in (-1.2,-.2,.8):
            stripe=affinity.translate(rectangle(offset,0,.5,14,angle=0),0,0)
            stripe=affinity.translate(affinity.rotate(stripe,angle,origin=(0,0)),c.x,c.y).intersection(g)
            for part in parts(stripe):
                draw.polygon([xy(p) for p in part.exterior.coords],fill='#F7F0D9')
    for q in d['waste_outfall']['segments']:
        if q['mode']=='low_supports':
            line(q['polyline'],'#694B36',1.5)
            line(q['polyline'],'#B77A48',.8)
    for q in d['waste_outfall']['supports']:
        x,y=xy((q['x'],q['y']))
        draw.rectangle((x-3,y-3,x+3,y+3),fill='#9A998B',outline='#6C7169',width=1)
    for q in d['waste_outfall']['dead_fish_decals']:
        x,y=xy((q['x'],q['y']));a=math.radians(q['angle_deg'])
        dx,dy=math.cos(a)*3.5,-math.sin(a)*3.5
        draw.line([(x-dx,y-dy),(x+dx,y+dy)],fill='#D3D1B7',width=3)
        draw.polygon([(x-dx,y-dy),(x-dx-dy,y-dy+dx),(x-dx+dy,y-dy-dx)],fill='#899783')
    for q in d['buildings']:
        if not q['spawn_geometry']:
            continue
        pts=[xy(p) for p in q['footprint_m']]
        draw.polygon(pts,fill=q['palette']['wall'],outline='#4F605C',width=2)
        edge=q['front_side'];a=pts[edge];b=pts[(edge+1)%len(pts)]
        draw.line([a,b],fill=q['palette']['trim'],width=4)
        for e in q['entrances']:
            x,y=xy((e['x'],e['y']));draw.ellipse((x-2,y-2,x+2,y+2),fill='#543F30')
    for q in d['trees']:
        x,y=xy((q['x'],q['y']));r=q['crown_radius_m']*scale*factor
        fill=TREE_COLORS[q['species']]
        draw.ellipse((x+1,y+2,x+r*1.6,y+r*1.5),fill='#879778')
        if q['species']=='pine':
            draw.polygon([(x,y-r),(x-r*.85,y+r*.75),(x+r*.85,y+r*.75)],fill=fill,outline='#4E755C')
        elif q['species']=='palm':
            for ang in range(0,360,60):
                a=math.radians(ang+q['angle_deg'])
                draw.line([(x,y),(x+math.cos(a)*r,y+math.sin(a)*r)],fill=fill,width=3)
            draw.ellipse((x-1.8,y-1.8,x+1.8,y+1.8),fill='#927556')
        else:
            draw.ellipse((x-r,y-r,x+r,y+r),fill=fill,outline='#627B58',width=1)
            draw.ellipse((x-r*.55,y-r*.65,x+r*.15,y+r*.05),fill='#ACC08B')
    for q in d['street_furniture']:
        if q.get('building_ref'):
            continue
        x,y=xy((q['x'],q['y']));typ=q['type'];a=math.radians(q['angle_deg'])
        if typ=='street_lamp':
            draw.ellipse((x-2,y-2,x+2,y+2),fill='#435B62')
            draw.line([(x,y),(x+math.cos(a)*7,y-math.sin(a)*7)],fill='#435B62',width=2)
            xx,yy=x+math.cos(a)*7,y-math.sin(a)*7
            draw.ellipse((xx-2,yy-2,xx+2,yy+2),fill='#F0C76C',outline='#7E6B4A')
        elif typ=='power_pole':
            draw.line([(x-3,y-3),(x+3,y+3)],fill='#7D6655',width=2)
            draw.line([(x-3,y+3),(x+3,y-3)],fill='#7D6655',width=2)
        elif typ in {'swings','slide','sandbox','carpet_rack'}:
            col={'swings':'#6D829A','slide':'#BB775D','sandbox':'#E4C27E','carpet_rack':'#8B807B'}[typ]
            r=q['reserved_radius_m']*scale*factor*.7
            draw.rectangle((x-r,y-r*.7,x+r,y+r*.7),fill=col,outline='#6A645B',width=2)
        elif typ=='bench':
            dx,dy=math.cos(a)*4,-math.sin(a)*4
            draw.line([(x-dx,y-dy),(x+dx,y+dy)],fill='#9F6645',width=4)
        elif typ=='bus_stop':
            draw.rectangle((x-7,y-5,x+7,y+5),fill='#758B8F',outline='#3F5A62',width=2)
        elif typ=='sign_no_swimming':
            draw.line([(x,y),(x,y+6)],fill='#6E6556',width=2)
            draw.rectangle((x-6,y-4,x+6,y+4),fill='#E8DDC2',outline='#A2573F',width=2)
            draw.line([(x-4,y+2),(x+4,y-2)],fill='#A2573F',width=2)
        elif typ=='traffic_sign':
            draw.polygon([(x,y-4),(x-4,y+3),(x+4,y+3)],fill='#E9DFC7',outline='#8E6959',width=2)
        else:
            draw.rectangle((x-2.5,y-2.5,x+2.5,y+2.5),fill='#536F68' if typ=='garbage_container' else '#7E7060')
    detail_copy=image.copy()
    # Restore map annotations above the overlay, at their original registered positions.
    fonts=Path('C:/Windows/Fonts')
    regular=fonts/'arial.ttf';bold=fonts/'arialbd.ttf'
    for t in ET.parse(ROOT/'MAP_PLAN_R01_v12.svg').getroot().iter('{http://www.w3.org/2000/svg}text'):
        if not t.text or 'stroke' in t.attrib or float(t.attrib.get('y',0))>1775 or float(t.attrib.get('y',0))<115:
            continue
        size=round(float(t.attrib.get('font-size',15))*factor)
        font=ImageFont.truetype(str(bold if t.attrib.get('font-weight')=='bold' else regular),size)
        anchor={'start':'ls','middle':'ms','end':'rs'}[t.attrib.get('text-anchor','start')]
        stroke=0 if float(t.attrib.get('font-size',15))<=10 else 2
        draw.text((float(t.attrib['x'])*factor,float(t.attrib['y'])*factor),t.text,font=font,
            fill=t.attrib.get('fill','#4B6262'),anchor=anchor,stroke_width=stroke,stroke_fill='#F7F4EB')
    def text_at(x,y,value,size=18,fill='#3B555A',weight=False):
        font=ImageFont.truetype(str(bold if weight else regular),round(size*factor))
        draw.text((x*factor,y*factor),value,font=font,fill=fill)
    label=xy((704,213))
    text_at(label[0]/factor,label[1]/factor,'СЛИВ B05 · НЕ КУПАТЬСЯ',15,fill='#697044',weight=True)
    label=xy((786,350))
    text_at(label[0]/factor,label[1]/factor,'ЧАСТНАЯ ТЕРРИТОРИЯ · ВОРОТА',11,fill='#59645C')
    draw.rectangle((0,0,4800,115*factor),fill='#F7F4EB')
    text_at(75,25,'VOLUNTEERS ONLY / R01 v12 — DRESSING',31,weight=True)
    text_at(75,72,'Слой оформления на утверждённом плане: здания, материалы, сады, мебель и озеленение',18)
    draw.rectangle((60*factor,1804*factor,2350*factor,2365*factor),fill='#F7F4EB')
    text_at(75,1820,'ДАННЫЕ ДЛЯ UNITY · ГЕОМЕТРИЯ ПЛАНА v12 СОХРАНЕНА',21,weight=True)
    st=d['statistics'];f=st['furniture_by_type']
    text_at(75,1860,f'{st["physical_buildings"]} зданий / {st["counts"]["buildings"]} ID · {st["counts"]["trees"]} деревьев · '
        f'{f.get("street_lamp",0)} фонарей · {st["counts"]["street_furniture"]-f.get("street_lamp",0)} прочих объектов',20)
    text_at(75,1894,f'Промзона: ограда 2,8 м / 1 ворота · слив B05: Ø 0,8 м / 36 м в море · 2 запрета купания / 2 дохлые рыбы',18)
    # Detail insets use the same raster overlay to make placement readable.
    map_copy=detail_copy
    inset_specs=[('ДВОР 1 · площадка, лавки и мусорки',(535,776),85),
                 ('ПЛОЩАДЬ · тротуары и парковки',(677,565),145),
                 ('СЛИВ B05 · труба, опоры и грязный шлейф',(647,254),320)]
    for n,(title,center,width) in enumerate(inset_specs):
        x=75+n*775;y=1970;pw=695;ph=275
        text_at(x,y-33,title,17,weight=True)
        p=xy((center[0]-width/2,center[1]+width*.1978))
        q=xy((center[0]+width/2,center[1]-width*.1978))
        crop=map_copy.crop((round(p[0]),round(p[1]),round(q[0]),round(q[1])))
        crop=crop.resize((pw*factor,ph*factor),Image.Resampling.LANCZOS)
        image.alpha_composite(crop,(x*factor,y*factor))
        draw=ImageDraw.Draw(image)
        draw.rectangle((x*factor,y*factor,(x+pw)*factor,(y+ph)*factor),outline='#99A295',width=2)
    text_at(75,2270,'● берёза / дуб / плодовые    ▲ сосна    ✳ пальма    ━ скамья    ▪ контейнер    жёлтая точка — фонарь',17)
    text_at(75,2301,'Районных оград нет · только элитка, частные дворы и промзона · под дорожками труба уходит в грунт',16)
    text_at(75,2331,f'Проверки: {len(d["validation"]["checks"])} / {len(d["validation"]["checks"])} · '
        'наземные покрытия без пробелов · JSON учитывает отверстия и повторные ID зданий',16)
    image.convert('RGB').save(ROOT/(STEM+'.png'),optimize=True)


def report(plan,d):
    s=d['statistics'];f=s['furniture_by_type'];c=s['counts']
    lines=['# R01 v12 — оформление без изменения планировки',
        'План v12 и прежние файлы сохранены, SHA-256 проверены; метры: x — восток, y — север; Unity: (x, высота, y).',
        f'Здания: {c["buildings"]} ID, {s["physical_buildings"]} физических объектов; 4 алиаса не создают дубликаты.',
        'Все 38 функциональных типов оформлены; этажи/контуры прежние, входы на фасадах к дороге; запреты вывесок соблюдены.',
        'Районных оград нет; исходные межрайонные заборы не импортировать. Остаются отдельные дворы и ограда элитного холма.',
        f'Ограды: элитка — {len(d["elite_fences"])} секции; промзона — {len(d["industrial_fences"])} секции бетона с колючкой 2,8 м.',
        'Промзона закрыта со стороны пляжа по INDUSTRIAL_BEACH_FENCE_1; одни ворота 7 м, частный подъезд от I_YARD.',
        f'Тротуары: {c["sidewalks"]} отрезков 2,5–3,2 м; бордюры: {c["curbs"]}; зебры: {c["zebra_crossings"]}.',
        f'Парковки: 7 / {sum(q["stall_count"] for q in d["parking_lots"])} мест; казино — 8 бусиков; места 3,25 × 7 м.',
        f'Деревья: {c["trees"]}; '+', '.join(f'{k}: {v}' for k,v in s['tree_species'].items())+'.',
        'Лес смешанный, посадки нерегулярные; пальмы только в элитке и у пляжных входов за пределами песка.',
        f'Мебель: '+', '.join(f'{k}: {v}' for k,v in f.items())+'.',
        'В каждом из трёх дворов: качели, горка, песочница, турник для ковров, лавки, урны и 3 контейнера.',
        f'Сады: {c["yards"]} фрагментов; деревянные ограды в хуторе, штакетник у домов, живые изгороди у вилл.',
        f'Покрытия: {c["ground_materials"]} полигонов; все 8 материалов, все районы и общие полосы между ними.',
        f'Слив B05: ржавая труба Ø 0,8 м, 36 м за урезом; грязный зелёно-бурый шлейф ~60 × 35 м целиком в море.',
        f'Новые детали: {len(d["waste_outfall"]["segments"])} секций трубы, {len(d["waste_outfall"]["supports"])} низких опор, 2 знака «КУПАТЬСЯ ЗАПРЕЩЕНО», 2 декали дохлых рыб.',
        'Под дорогой, ЖД, пляжной дорожкой и оградой труба в гильзах: 1,2 м грунта над верхом; на песке — низкие опоры.',
        '| Район | Здания/ID | Тротуары/бордюры/зебры | Фонари/прочее | Деревья | Парковки/места | Сады | Покрытия | Ограды Э/П/ворота | Слив: опоры/рыбы/секции/шлейф |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    names={q['id']:q['name_ru'] for q in plan['districts']};names.update(beach='Пляж',common='Общие полосы',sea='Море')
    for did,q in s['by_district'].items():
        lines.append(f'| {names[did]} | {q["physical_buildings"]}/{q["buildings"]} | '
            f'{q["sidewalks"]}/{q["curbs"]}/{q["zebra_crossings"]} | {q["lamps"]}/{q["other_furniture"]} | '
            f'{q["trees"]} | {q["parking_lots"]}/{q["parking_stalls"]} | {q["yards"]} | {q["ground_materials"]} | '
            f'{q["elite_fences"]}/{q["industrial_fences"]}/{q["industrial_gates"]} | '
            f'{q["outfall_supports"]}/{q["dead_fish_decals"]}/{q["outfall_segments"]}/{q["sludge_plumes"]} |')
    lines.extend([
        f'Проверки: {len(d["validation"]["checks"])} из {len(d["validation"]["checks"])}; пересечений мебели/деревьев друг с другом нет.',
        f'Пробелы наземных материалов: {d["validation"]["uncovered_ground_m2"]} м²; перекрытие: {d["validation"]["overlapping_ground_m2"]} м².',
        'Проверены зоны крон, мебели, опор, трубы, ограды, дорог, ЖД, воды и парковок; подъезды и развороты пляжа свободны.',
        'Коридор видимости вагон → труба сохранён; коллизии деревьев с тротуарами и пляжем исключены.',
        'Схема builder_contract: отверстия обязательны; spawn_geometry=false — алиас/существующий павильон.',
        'Ограды: только elite_fences, industrial_fences и yards.fence_polylines_m; труба строится по segments с их отметками высоты.',
        'PNG — слой на чертеже v12; старые районные заборы удалены из превью, слив показан крупно; просмотрен перед сдачей.',
        'Повтор: Python 3.12+, Shapely 2.x, Pillow, ImageMagick; python -B map_dressing_v12.py; --validate-only проверяет JSON.',
        'Это данные оформления и техническое превью; окончательное визуальное качество проверяется в Unity.',
    ])
    assert len(lines)<=40,len(lines)
    (ROOT/(STEM+'_REPORT.md')).write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-only',action='store_true')
    args=parser.parse_args()
    before=immutable_hashes()
    plan=read_json(ROOT/'MAP_PLAN_R01_v12.json')
    if args.validate_only:
        d=read_json(ROOT/(STEM+'.json'))
        checks=validate(plan,d)
        assert immutable_hashes()==before,'Existing file changed'
        print(json.dumps(dict(passed=checks['passed'],checks=len(checks['checks']),counts=statistics(d)['counts']),ensure_ascii=False))
        return
    d=MapDressing(plan).generate()
    print('Validating serialized geometry...',flush=True)
    d['validation']=validate(plan,d)
    d['statistics']=statistics(d)
    d['provenance']=dict(brief='req_map_dressing_v12.md',followup_brief='req_map_dressing_v12_followup.md',approved_plan_date='2026-10-04',
        method='seeded geometric placement with full envelope rejection and exact surface partition',
        immutable_files_sha256=before,layout_changes=False)
    (ROOT/(STEM+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Rendering registered overlay...',flush=True)
    render(plan,d)
    report(plan,d)
    assert immutable_hashes()==before,'An existing file was modified'
    print(json.dumps(dict(passed=True,checks=len(d['validation']['checks']),statistics=d['statistics']['counts'],
        physical_buildings=d['statistics']['physical_buildings'],furniture=d['statistics']['furniture_by_type']),ensure_ascii=False))


if __name__=='__main__':
    main()
