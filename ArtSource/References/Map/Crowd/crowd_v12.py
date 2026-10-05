#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Crowd planning data for immutable R01 v12. Python + NumPy, Shapely 2, Pillow.

python -B crowd_v12.py; python -B crowd_v12.py --validate-only
Only outputs beside this script are written. No Unity or source-plan changes.
All routes are metre polylines, east +x / north +y, Unity (x, ground height, y).
"""
import argparse
import collections
import hashlib
import heapq
import json
import math
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union, nearest_points
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MAP = ROOT.parent
STEP = 1.25
RADIUS = .30
DENSITY = dict(forest=(2,2), village=(3,2), transition=(6,5),
               residential=(14,14), old_town=(12,14), elite=(3,2),
               industrial=(5,3), fields=(6,9), beach=(8,4))
COLORS = dict(forest='#647849', village='#936637', transition='#95773e',
              residential='#c94f54', old_town='#087daa', elite='#7554a9',
              industrial='#55787c', fields='#dc8129', beach='#ce950e')
# Coverage anchors are planning intentions, snapped to the connected dry graph.
# They deliberately cover all three slab courtyards and both beach entrances.
ROUTE_ANCHORS = dict(
    forest=[[[185,512],[222,531]], [[198,514],[234,546]]],
    village=[[[234,577],[300,600],[325,582]], [[289,705],[300,645],[220,670]]],
    transition=[[[398,574],[405,608],[455,611]], [[390,690],[405,730],[440,713]]],
    residential=[[[528,782],[554,769],[535,737]], [[646,785],[656,768],[650,738]],
                 [[590,665],[587,690],[630,719],[680,704]]],
    old_town=[[[582,589],[633,545],[752,578]], [[664,532],[748,500],[685,488]],
              [[512,586],[535,515],[579,513],[588,479]]],
    elite=[[[844,610],[885,602],[920,618]], [[920,552],[870,502],[864,550]]],
    industrial=[[[590,396],[536,392],[558,389]], [[745,409],[774,394],[700,400]]],
    fields=[[[435,387],[396,383],[470,376]], [[401,523],[383,484],[450,488]]],
    beach=[[[420,281],[515,285],[605,283]], [[1028,517],[998,480],[965,438]]])
ACTIVITIES = {'bench_sit','shop_queue','bus_wait','smoke_corner','playground',
              'beach_lie','church_steps','casino_door','bar_door','kiosk'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def xy(point):
    return [round(point.x,5),round(point.y,5)]


def parts(g, kind):
    if g.is_empty:
        return []
    if g.geom_type == kind:
        return [g]
    return [p for child in getattr(g,'geoms',[]) for p in parts(child,kind)]


def polygon(q):
    return Polygon(q['polygon'],q.get('holes',[]))


class Crowd:
    def __init__(self):
        self.plan = read(MAP/'MAP_PLAN_R01_v12.json')
        self.dress = read(MAP/'MAP_DRESSING_R01_v12.json')
        assert self.dress['source_plan_sha256'] == sha(MAP/'MAP_PLAN_R01_v12.json')
        self.districts = {q['id']:Polygon(q['polygon_m']) for q in self.plan['districts']}
        self.beach = unary_union([Polygon(q['polygon_m']) for q in self.plan['beaches']])
        self.districts['beach'] = self.beach
        self.boundary = Polygon(self.plan['boundary']['polygon_m'])
        self.buildings = {b['id']:Polygon(b['footprint_m']) for b in self.dress['buildings'] if b['spawn_geometry']}
        self.building_union = unary_union(list(self.buildings.values()))
        self.roads = {r['id']:(r,LineString(r['polyline_m'])) for r in self.plan['roads']}
        self.road_area = unary_union([line.buffer(r['width_m']/2,cap_style=2) for r,line in self.roads.values()])
        self.raw_water = unary_union([Polygon(w['polygon_m']) if 'polygon_m' in w else LineString(w['centerline_m']).buffer(w['width_m']/2)
                                      for w in self.plan['water']])
        # A deck is dry ground over water, recorded explicitly for height/bridge handling.
        self.decks = [dict(id=c['id'],road_id=c['road_id'],kind=c['kind'],polyline_m=c['deck_axis_m'],
                           width_m=self.roads[c['road_id']][0]['width_m']+8)
                      for c in self.plan['water_crossings']]
        deck_area = unary_union([LineString(c['polyline_m']).buffer(c['width_m']/2,cap_style=2) for c in self.decks])
        # Other approved tunnel carriers must also stay dry at the walking surface.
        tunnel_roads = {rid for w in self.plan['water'] for rid in w.get('short_tunnel_road_ids',[])}
        deck_area = deck_area.union(unary_union([self.roads[rid][1].buffer(self.roads[rid][0]['width_m']/2+4)
                                               for rid in tunnel_roads if rid in self.roads]))
        self.water = self.raw_water.difference(deck_area)
        fence_lines = [LineString(q['polyline']) for q in self.dress['elite_fences']+self.dress['industrial_fences']]
        fence_lines += [LineString(seq) for q in self.dress['yards'] for seq in q['fence_polylines_m'] if len(seq)>1]
        self.fences = unary_union(fence_lines).buffer(.18)
        trunk = [Point(t['x'],t['y']).buffer(.3) for t in self.dress['trees']]
        furniture = [Point(f['x'],f['y']).buffer(min(f.get('reserved_radius_m',.4),2.6))
                     for f in self.dress['street_furniture'] if f['type'] not in ('bus_stop','bench')]
        self.obstacles = unary_union([self.building_union,self.water,self.fences]+trunk+furniture)
        self.crossings = []
        self.make_crossings()
        self.make_walk_space()

    def make_crossings(self):
        for z in self.dress['zebra_crossings']:
            self.crossings.append(dict(id=z['id'],kind='zebra',road_ids=[z['road_id']],geometry=polygon(z)))
        # Road/road intersections only; dead-end road tips are not invented crossings.
        seen = set()
        roads = list(self.roads.values())
        for i,(r,line) in enumerate(roads):
            for s,other in roads[i+1:]:
                intersection = line.intersection(other)
                candidates = parts(intersection,'Point')
                for p in candidates:
                    key = (round(p.x,1),round(p.y,1))
                    if key in seen:
                        continue
                    seen.add(key)
                    ids = [q['id'] for q,l in roads if l.distance(p)<.25]
                    radius = max(self.roads[rid][0]['width_m']/2 for rid in ids)+4
                    self.crossings.append(dict(id=f'JUNCTION{len(seen):03d}',kind='junction',road_ids=ids,geometry=p.buffer(radius)))
        self.cross_area = unary_union([c['geometry'] for c in self.crossings])
        self.forbidden_road = self.road_area.difference(self.cross_area)

    def make_walk_space(self):
        spaces = []
        for s in self.dress['sidewalks']:
            spaces.append(LineString(s['polyline_m']).buffer(s['width_m']/2))
        # Lane verges stay outside the road; road centre is never a walking route.
        for r,line in self.roads.values():
            half = r['width_m']/2
            spaces.append(line.buffer(half+3.0).difference(line.buffer(half+.15)))
        # Building aprons let pedestrians reach the back without cutting through a mass.
        for b in self.buildings.values():
            spaces.append(b.buffer(4.5).difference(b))
        for y in self.dress['yards']:
            spaces.append(polygon(y))
        for m in self.plan['microdistricts']:
            spaces.append(Polygon(m['yard_polygon_m']))
        for g in self.dress['ground_materials']:
            if g['context'] in ('CLOCK_SQUARE','BAD_CENTER','BUS_VILLAGE','BUS_AVENUE','CHURCH12_YARD','site:CHURCH12_YARD'):
                spaces.append(polygon(g))
        for path in self.plan['paths']:
            spaces.append(LineString(path['polyline_m']).buffer(path['width_m']/2))
        # Beach loungers use local sand paths. Other profiles exclude the entire beach.
        for path in self.plan['paths']:
            if path['district_id']=='beach':
                spaces.append(LineString(path['polyline_m']).buffer(7).intersection(self.beach))
        spaces.append(self.cross_area.buffer(2))
        self.free = unary_union(spaces).intersection(self.boundary).difference(
            self.obstacles.buffer(RADIUS).union(self.forbidden_road))
        shapely.prepare(self.free)

    def graph(self):
        minx,miny,maxx,maxy = self.free.bounds
        xs = np.arange(math.floor(minx/STEP)*STEP,maxx+STEP,STEP)
        ys = np.arange(math.floor(miny/STEP)*STEP,maxy+STEP,STEP)
        gx,gy = np.meshgrid(xs,ys)
        mask = shapely.contains_xy(self.free,gx.ravel(),gy.ravel()).reshape(gx.shape)
        grid = np.column_stack(np.where(mask))
        self.positions = np.column_stack((xs[grid[:,1]],ys[grid[:,0]]))
        lookup = np.full(mask.shape,-1,dtype=np.int32)
        lookup[grid[:,0],grid[:,1]] = np.arange(len(grid))
        self.adj = [[] for _ in grid]
        edges = []
        for dr,dc in [(0,1),(1,0),(1,1),(1,-1)]:
            rr,cc = grid[:,0]+dr,grid[:,1]+dc
            valid = (rr>=0)&(rr<lookup.shape[0])&(cc>=0)&(cc<lookup.shape[1])
            a = np.where(valid)[0]
            b = lookup[rr[valid],cc[valid]]
            a,b = a[b>=0],b[b>=0]
            lines = shapely.linestrings(np.stack((self.positions[a],self.positions[b]),axis=1))
            ok = shapely.covers(self.free,lines)
            for u,v in zip(a[ok].tolist(),b[ok].tolist()):
                self.adj[u].append(v)
                self.adj[v].append(u)
                edges.append((u,v))
        self.edges = edges
        self.land = ~shapely.contains_xy(self.beach,self.positions[:,0],self.positions[:,1])
        self.land_nodes = self.largest_component(self.land)
        self.all_nodes = self.largest_component(np.ones(len(grid),dtype=bool))
        self.land_set = set(self.land_nodes)
        self.all_set = set(self.all_nodes)
        self.by_district = {}
        for district,g in self.districts.items():
            nodes = self.all_nodes if district=='beach' else self.land_nodes
            pos = self.positions[nodes]
            inside = shapely.contains_xy(g,pos[:,0],pos[:,1])
            self.by_district[district] = np.asarray(nodes)[inside].tolist()
            assert self.by_district[district], f'No connected walking cells in {district}'
        print(f'Graph: {len(self.positions)} nodes, connected land {len(self.land_nodes)}, beach-inclusive {len(self.all_nodes)}.',flush=True)

    def largest_component(self,allowed):
        seen = set()
        largest = []
        for start in np.where(allowed)[0]:
            start = int(start)
            if start in seen:
                continue
            stack,component = [start],[]
            seen.add(start)
            while stack:
                u = stack.pop()
                component.append(u)
                for v in self.adj[u]:
                    if allowed[v] and v not in seen:
                        seen.add(v)
                        stack.append(v)
            if len(component)>len(largest):
                largest = component
        return sorted(largest)

    def nearest(self,target,nodes):
        nodes = np.asarray(nodes)
        distances = np.sum((self.positions[nodes]-target)**2,axis=1)
        i = int(np.argmin(distances))
        return int(nodes[i]),float(distances[i]**.5)

    def path(self,start,end,beach=False,penalty=None):
        allowed = self.all_set if beach else self.land_set
        goal = self.positions[end]
        queue = [(0.0,0.0,start)]
        cost,previous = {start:0.0},{}
        while queue:
            _,g,u = heapq.heappop(queue)
            if g>cost[u]+1e-8:
                continue
            if u==end:
                result = [end]
                while result[-1]!=start:
                    result.append(previous[result[-1]])
                return result[::-1]
            for v in self.adj[u]:
                if v not in allowed:
                    continue
                length = math.dist(self.positions[u],self.positions[v])
                candidate = g+length*(2.5 if penalty and (min(u,v),max(u,v)) in penalty else 1)
                if candidate<cost.get(v,math.inf):
                    cost[v],previous[v] = candidate,u
                    heapq.heappush(queue,(candidate+math.dist(self.positions[v],goal),candidate,v))
        raise ValueError(f'No path {start}->{end}')

    def polyline(self,ids):
        # Remove collinear cells only; arbitrary geometric simplification could cut a corner.
        out = [ids[0]]
        for i in range(1,len(ids)-1):
            a,b,c = self.positions[ids[i-1]],self.positions[ids[i]],self.positions[ids[i+1]]
            v,w = b-a,c-b
            if abs(v[0]*w[1]-v[1]*w[0])>1e-7 or np.dot(v,w)<=0:
                out.append(ids[i])
        out.append(ids[-1])
        return self.positions[out].tolist()

    def edge_record(self,ids):
        seq = self.polyline(ids)
        line = LineString(seq)
        crossed = [c['id'] for c in self.crossings if line.intersects(c['geometry']) and line.intersection(c['geometry']).intersects(self.road_area)]
        return dict(polyline_m=seq,length_m=round(line.length,2),crossing_refs=crossed)

    def pois(self):
        result = []
        def add(district,tag,target,reference,max_distance=12,dwell=(8,30),capacity=1):
            node,distance = self.nearest(target,self.by_district[district])
            if distance>max_distance:
                raise ValueError(f'POI too far from {reference}: {distance:.1f}m ({tag})')
            result.append(dict(id=f'POI{len(result)+1:03d}',district_id=district,activity=tag,
                               position_m=self.positions[node].tolist(),source_ref=reference,
                               target_offset_m=round(distance,2),capacity=capacity,dwell_s=list(dwell),node=node))
        for f in self.dress['street_furniture']:
            if f['type'] in ('bench','swings','bus_stop','bus_stop_marker'):
                tag = dict(bench='bench_sit',swings='playground',bus_stop='bus_wait',bus_stop_marker='bus_wait')[f['type']]
                angle = math.radians(f['angle_deg'])
                offset = 1.0 if f['type']=='bench' else 3.5
                target = [f['x']+math.cos(angle)*offset,f['y']+math.sin(angle)*offset]
                # Existing bus shelter is a physical building: use its entrance, not its centre.
                if f['id']=='SF_BUS_EXISTING':
                    target = [315,605]
                add(f['district_id'],tag,target,f['id'],max_distance=8,dwell=(12,50),capacity=2 if tag!='bench_sit' else 1)
        func = {q['id']:q for q in self.plan['functional_buildings']}
        tags = dict(village_shop='shop_queue',pharmacy='shop_queue',shop_24h='shop_queue',
                    supermarket='shop_queue',casino='casino_door',bar='bar_door',kiosk='kiosk',church='church_steps')
        dressed = {q['id']:q for q in self.dress['buildings']}
        for b in func.values():
            if b['type'] in tags:
                door = dressed[b['id']]['entrances'][0]
                angle = math.radians(door['angle_deg'])
                target = [door['x']+2.2*math.cos(angle),door['y']+2.2*math.sin(angle)]
                add(b['district_id'],tags[b['type']],target,b['id'],max_distance=10,capacity=3,dwell=(10,45))
        for district,bid in [('residential','F06_GBASE'),('old_town','F06_BANK'),('industrial','F06_MAINT'),('fields','F12_NIGHTCLUB')]:
            b = self.buildings[bid]
            road = self.roads[dressed[bid]['front_road_id']][1]
            front = nearest_points(b,road)[0]
            rear = b.centroid.coords[0]
            vector = np.asarray(rear)-np.asarray(front.coords[0])
            vector /= np.linalg.norm(vector)
            target = np.asarray(rear)+vector*(math.sqrt(b.area)/2+3)
            add(district,'smoke_corner',target,bid,max_distance=18,dwell=(20,70),capacity=2)
        for fraction in [.04,.21,.40,.63,.82,.97]:
            beach_path = LineString(self.plan['paths'][0]['polyline_m'])
            p = beach_path.interpolate(fraction,normalized=True)
            add('beach','beach_lie',xy(p),'WALK_BEACH',max_distance=8,dwell=(35,100),capacity=2)
        assert ACTIVITIES=={q['activity'] for q in result}
        return result

    def spawns(self):
        result = []
        dress = {q['id']:q for q in self.dress['buildings'] if q['spawn_geometry']}
        for district in DENSITY:
            candidates = []
            source_districts = ['fields','elite'] if district=='beach' else [district]
            for bid,b in self.buildings.items():
                entry = dress[bid]
                if entry['district_id'] not in source_districts:
                    continue
                road_id = entry['front_road_id']
                road = self.roads[road_id][1]
                if road_id.startswith('ACCESS_'):
                    parents = [(rid,l) for rid,(r,l) in self.roads.items()
                               if not rid.startswith('ACCESS_') and l.distance(Point(road.coords[0]))<.3]
                    if parents:
                        road_id,road = min(parents,key=lambda q:q[1].distance(b.centroid))
                station = road.project(b.centroid)
                span = min(20,road.length)
                begin = max(0,min(road.length-span,station-span/2))
                observers = [road.interpolate(begin+span*f) for f in (0,.5,1)]
                nodes = self.by_district[entry['district_id']]
                pos = self.positions[nodes]
                dist = np.sum((pos-np.asarray(b.centroid.coords[0]))**2,axis=1)
                nearby = np.asarray(nodes)[dist < (math.sqrt(b.area)+12)**2]
                for node in nearby:
                    p = Point(self.positions[node])
                    if not .7<b.distance(p)<4.2:
                        continue
                    if all(LineString([o,p]).intersection(b.buffer(-.1)).length>.35 for o in observers):
                        score = sum(o.distance(p) for o in observers)
                        if district=='beach':
                            score -= 100*p.distance(self.beach)
                        candidates.append((score,int(node),bid,road_id,observers,entry['district_id']))
            candidates.sort(reverse=True,key=lambda q:q[0])
            selected = []
            for _,node,bid,rid,observers,source in candidates:
                if any(math.dist(self.positions[node],self.positions[s['node']])<4 for s in selected):
                    continue
                # Prefer two different occluders; forest has only the wagon.
                if selected and bid==selected[0]['occluder_building_id'] and any(c[2]!=bid for c in candidates):
                    continue
                if district=='beach' and selected and source==selected[0]['location_district_id']:
                    continue
                selected.append(dict(id=f'SPAWN_{district}_{len(selected)+1:02d}',district_id=district,
                                     location_district_id=source,position_m=self.positions[node].tolist(),node=node,
                                     usage=['spawn','despawn'],occluder_building_id=bid,observer_road_id=rid,
                                     tested_observer_positions_m=[xy(o) for o in observers],
                                     require_runtime_camera_occlusion=True,min_player_distance_m=25,visibility_grace_s=2))
                if len(selected)==2:
                    break
            assert len(selected)==2, f'Need two occluded spawn points in {district}'
            result.extend(selected)
        return result

    def routes(self,pois,spawns):
        result = []
        for district in DENSITY:
            nodes = self.by_district[district]
            local = [q for q in pois if q['district_id']==district]
            for j,targets in enumerate(ROUTE_ANCHORS[district]):
                anchors = [self.nearest(target,nodes)[0] for target in targets]
                ids,penalty = [anchors[0]],set()
                for a,b in zip(anchors,anchors[1:]+anchors[:1]):
                    leg = self.path(a,b,district=='beach',penalty)
                    ids.extend(leg[1:])
                    penalty.update((min(u,v),max(u,v)) for u,v in zip(leg,leg[1:]))
                record = dict(id=f'ROUTE_{district}_{j+1:02d}',district_id=district,
                              profile='beach_walker' if district=='beach' else 'town_walker',closed=True,
                              speed_mps=[.8,1.25] if district=='beach' else [1.0,1.5],
                              poi_ids=[q['id'] for q in local if LineString(self.polyline(ids)).distance(Point(q['position_m']))<6])
                record.update(self.edge_record(ids))
                record['_nodes'] = ids
                result.append(record)
        # Police foot patrol: several separated anchors in BOTH districts.
        anchors = [self.nearest(target,self.by_district[district])[0] for district,target in
                   [('old_town',[755,580]),('old_town',[535,510]),('old_town',[650,540]),
                    ('residential',[590,670]),('residential',[535,777]),('residential',[650,777]),('residential',[720,730])]]
        ids = [anchors[0]]
        for a,b in zip(anchors,anchors[1:]+anchors[:1]):
            ids.extend(self.path(a,b)[1:])
        police = dict(id='POLICE_OLD_BAD_01',profile='police_foot_patrol',district_ids=['old_town','residential'],
                      closed=True,officers=2,speed_mps=[1.15,1.45],pause_at_anchors_s=[5,15],_nodes=ids)
        police.update(self.edge_record(ids))
        return result,police

    def output(self):
        self.graph()
        pois,spawns = self.pois(),self.spawns()
        routes,police = self.routes(pois,spawns)
        connectors = []
        # Connect all exported routes to one dry-land hub; links are explicit, no teleporting.
        hub = police['_nodes'][0]
        for route in routes:
            ids = self.path(hub,route['_nodes'][0],route['profile']=='beach_walker')
            connectors.append(dict(id=f"LINK_{route['id']}",profile=route['profile'],route_id=route['id'],
                                   purpose='network_connection',**self.edge_record(ids)))
        for q in pois+spawns:
            district = q['district_id']
            choices = [r for r in routes if r['district_id']==district]
            r = min(choices,key=lambda r:LineString(r['polyline_m']).distance(Point(q['position_m'])))
            endpoint,_ = self.nearest(q['position_m'],r['_nodes'])
            ids = self.path(q['node'],endpoint,district=='beach')
            connectors.append(dict(id=f"LINK_{q['id']}",profile=r['profile'],route_id=r['id'],point_id=q['id'],
                                   purpose='spawn_access' if q in spawns else 'activity_access',**self.edge_record(ids)))
            q['route_id'],q['access_link_id'] = r['id'],connectors[-1]['id']
        hotspots = []
        for context,district,target,eyes in [('BAD_CENTER','residential',[650,723.5],[8,10]),
                                            ('MB06_1','residential',[535,777],[5,5]),('MB06_2','residential',[650,777],[5,5]),
                                            ('MB06_3','residential',[592.5,670],[4,4]),('CLOCK_SQUARE','old_town',[650,540],[9,10]),
                                            ('SUPERMARKET','old_town',[582,589],[6,5]),('BUS_AVENUE','residential',[722,730],[5,4]),
                                            ('CASINO','fields',[435,387],[4,8]),('CHURCH','transition',[398,574],[5,3])]:
            node,_ = self.nearest(target,self.by_district[district])
            hotspots.append(dict(id=f'WITNESS_{context}',district_id=district,position_m=self.positions[node].tolist(),
                                 radius_m=20,expected_eyes_day=eyes[0],expected_eyes_evening=eyes[1],
                                 estimates_only=True,require_runtime_los=True,source_ref=context))
        for q in pois+spawns:
            q.pop('node')
        for q in routes+[police]:
            q.pop('_nodes')
        names = {q['id']:q['name_ru'] for q in self.plan['districts']}
        names['beach'] = 'Пляж'
        out = dict(schema_version='1.0',revision='R01_v12',generator='crowd_v12.py',
                   sources=[dict(path=f'../{n}',sha256=sha(MAP/n)) for n in ('MAP_PLAN_R01_v12.json','MAP_DRESSING_R01_v12.json')],
                   coordinates=self.plan['coordinates'],
                   runtime_contract=dict(status='planning_data_not_baked_navmesh',walker_radius_m=RADIUS,
                       sample_position_max_distance_m=.5,require_navmesh_complete_path=True,
                       require_height_projection=True,bridge_height_from_decks=True,
                       spawn_policy='Every observer/camera of every player must fail line of sight for 2s; >=25m from each player. If visible, defer spawn/despawn.',
                       profile_policy='town_walker and police exclude all beach sand; beach_walker may use dry land access links.',
                       movement_policy='Follow each explicit polyline corridor; unconstrained NavMesh shortest paths may cut roads.',
                       apron_policy='Building apron and yard polylines are proposed pedestrian paths on existing ground, not new imported paving.',
                       witness_policy='eyes are overlapping local estimates, not extra spawns or a guaranteed detection count; evaluate actual LOS.'),
                   districts=[dict(id=k,name_ru=names[k],walkers_day=v[0],walkers_evening=v[1],
                       route_ids=[r['id'] for r in routes if r['district_id']==k]) for k,v in DENSITY.items()],
                   points_of_interest=pois,routes=routes,spawn_despawn_points=spawns,witness_hotspots=hotspots,
                   police_patrol=police,connections=connectors,
                   allowed_crossings=[dict(id=c['id'],kind=c['kind'],road_ids=c['road_ids'],polygon_m=list(c['geometry'].exterior.coords)[:-1]) for c in self.crossings],
                   dry_decks=self.decks)
        out['validation'] = self.validate(out)
        return out

    def validate(self,out):
        assert all(2<=q[key]<=14 for q in out['districts'] for key in ('walkers_day','walkers_evening'))
        points = out['points_of_interest']+out['spawn_despawn_points']+out['witness_hotspots']
        for q in points:
            p = Point(q['position_m'])
            assert self.free.covers(p), f"Point outside dry free ground: {q['id']}"
            assert not self.building_union.intersects(p) and not self.water.intersects(p),q['id']
            district = q.get('location_district_id',q['district_id'])
            assert self.districts[district].covers(p),f"Point outside its district: {q['id']}"
        paths = out['routes']+[out['police_patrol']]+out['connections']
        ids = [q['id'] for q in points+paths]
        assert len(ids)==len(set(ids)),'Duplicate entity IDs'
        for q in paths:
            seq = q['polyline_m']
            assert len(seq)>=2
            line = LineString(seq)
            assert self.free.covers(line), f"Blocked route {q['id']}"
            assert not line.intersects(self.building_union) and not line.intersects(self.water),q['id']
            assert line.intersection(self.forbidden_road).length<1e-7,f"Illegal road crossing {q['id']}"
            if q.get('closed'):
                assert seq[0]==seq[-1] and line.length>20,q['id']
            if q['profile']!='beach_walker':
                assert not line.intersects(self.beach),f"Non-beach walker on sand {q['id']}"
        routes = {r['id']:r for r in out['routes']}
        links = {c['id']:c for c in out['connections']}
        for q in out['points_of_interest']+out['spawn_despawn_points']:
            link = links[q['access_link_id']]
            assert link['point_id']==q['id'] and link['route_id']==q['route_id']
            assert link['polyline_m'][0]==q['position_m'],q['id']
            assert LineString(routes[q['route_id']]['polyline_m']).distance(Point(link['polyline_m'][-1]))<1e-7,q['id']
        for c in out['connections']:
            if c['purpose']=='network_connection':
                assert c['polyline_m'][0]==out['police_patrol']['polyline_m'][0]
                assert c['polyline_m'][-1]==routes[c['route_id']]['polyline_m'][0]
        patrol = LineString(out['police_patrol']['polyline_m'])
        assert all(patrol.intersection(self.districts[d]).length>100 for d in ('old_town','residential'))
        for q in out['spawn_despawn_points']:
            b = self.buildings[q['occluder_building_id']]
            assert len({tuple(p) for p in q['tested_observer_positions_m']})==3,q['id']
            assert all(LineString([o,q['position_m']]).intersection(b.buffer(-.1)).length>.35
                       for o in q['tested_observer_positions_m']),q['id']
        # Split crossings in the exported line network and count actual connected pieces.
        network = unary_union([LineString(q['polyline_m']) for q in paths])
        segments = parts(network,'LineString')
        adjacency = collections.defaultdict(set)
        for line in segments:
            a,b = tuple(line.coords[0]),tuple(line.coords[-1])
            adjacency[a].add(b)
            adjacency[b].add(a)
        seen = set()
        if adjacency:
            stack = [next(iter(adjacency))]
            while stack:
                u = stack.pop()
                if u in seen:
                    continue
                seen.add(u)
                stack.extend(adjacency[u]-seen)
        assert len(seen)==len(adjacency),'Disconnected exported network'
        assert ACTIVITIES=={q['activity'] for q in out['points_of_interest']}
        assert len({tuple(map(tuple,r['polyline_m'])) for r in out['routes']})==len(out['routes'])
        for source in out['sources']:
            assert source['sha256']==sha(ROOT/source['path'])
        return dict(passed=True,point_count=len(points),route_count=len(out['routes']),
                    connection_count=len(out['connections']),exported_network_components=1,
                    blocked_segments=0,illegal_road_crossings=0,non_beach_sand_segments=0,
                    occlusion_reference_rays=len(out['spawn_despawn_points'])*3,
                    method='Exact Shapely segment coverage / obstacle / road intersection; connected exported network; building-occluded road observer rays.',
                    limitation='2D planning checks; moving van/player cameras require runtime occlusion; no Unity/NavMesh/play test performed.')

    def preview(self,out):
        w,h = 2000,1500
        img = Image.new('RGB',(w,h),'#eff1ed')
        draw = ImageDraw.Draw(img)
        bounds = self.boundary.bounds
        scale = min((w-100)/(bounds[2]-bounds[0]),(h-190)/(bounds[3]-bounds[1]))
        def px(p):
            return (round(50+(p[0]-bounds[0])*scale),round(h-65-(p[1]-bounds[1])*scale))
        def area(g,color):
            for p in parts(g,'Polygon'):
                draw.polygon([px(q) for q in p.exterior.coords],fill=color)
                for ring in p.interiors:
                    draw.polygon([px(q) for q in ring.coords],fill='#eff1ed')
        try:
            font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
            small = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
            title = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',29)
        except OSError:
            font = small = title = ImageFont.load_default()
        area(self.boundary,'#e0e5d9')
        for d in self.plan['districts']:
            area(Polygon(d['polygon_m']),d['color'])
        area(self.beach,'#e8d7ae')
        area(self.raw_water,'#a1c8db')
        area(self.road_area,'#969b97')
        for c in self.crossings:
            if c['kind']=='zebra':
                area(c['geometry'],'#f7f5e8')
        for r,line in self.roads.values():
            draw.line([px(q) for q in line.coords],fill='#a7aba6',width=1)
        area(self.building_union,'#6d746d')
        for r in out['routes']:
            draw.line([px(q) for q in r['polyline_m']],fill=COLORS[r['district_id']],width=4)
        for c in out['connections']:
            if c['purpose']!='network_connection':
                draw.line([px(q) for q in c['polyline_m']],fill='#adb2ac',width=2)
        seq = out['police_patrol']['polyline_m']
        # Dashed police loop remains readable over crowded walking paths.
        line = LineString(seq)
        for start in np.arange(0,line.length,7):
            end = min(start+4,line.length)
            from shapely.ops import substring
            chunk = substring(line,start,end)
            draw.line([px(q) for q in chunk.coords],fill='#2543e4',width=3)
        symbols = dict(bench_sit='B',shop_queue='Q',bus_wait='U',smoke_corner='S',playground='P',
                       beach_lie='L',church_steps='C',casino_door='D',bar_door='R',kiosk='K')
        for p in out['witness_hotspots']:
            x,y = px(p['position_m'])
            radius = round(p['radius_m']*scale)
            draw.ellipse((x-radius,y-radius,x+radius,y+radius),outline='#c1246b',width=3)
        for p in out['points_of_interest']:
            x,y = px(p['position_m'])
            draw.ellipse((x-6,y-6,x+6,y+6),fill='#fff9e9',outline='#333d41',width=1)
            draw.text((x+7,y-8),symbols[p['activity']],fill='#202d31',font=small)
        for s in out['spawn_despawn_points']:
            x,y = px(s['position_m'])
            draw.rectangle((x-5,y-5,x+5,y+5),fill='#13a38d',outline='#12362e',width=1)
        draw.rectangle((0,0,w,124),fill='#24343e')
        draw.text((30,13),'CROWD R01 v12 — routes / activity / hidden spawns',fill='white',font=title)
        draw.text((30,53),'Solid = walkers    Blue dashed = police    Pink rings = witnesses    Green squares = spawn/despawn',fill='#d7e8eb',font=font)
        draw.text((30,83),'B bench  Q queue  U bus  S smoke  P playground  L beach  C church  D casino  R bar  K kiosk',fill='#d7e8eb',font=small)
        for i,d in enumerate(out['districts']):
            x,y = px(self.districts[d['id']].representative_point().coords[0])
            draw.text((x,y),f"{d['name_ru']} {d['walkers_day']}/{d['walkers_evening']}",fill='#273036',font=font,stroke_width=2,stroke_fill='#eff1ed')
        draw.rectangle((0,h-43,w,h),fill='#24343e')
        draw.text((30,h-34),'Planning data; 2D validation passed. Moving-camera occlusion and NavMesh projection required at runtime.',fill='white',font=font)
        img.save(ROOT/'crowd_v12.png')

    def report(self,out):
        lines = ['# Толпа R01 v12', 'Координаты: метры, x восток, y север; Unity: (x, высота земли, y).',
                 '| Район | День/вечер | POI | Петли | Спавн/деспавн | Свидетели |', '|---|---:|---:|---:|---:|---:|']
        for d in out['districts']:
            district = d['id']
            counts = [sum(q['district_id']==district for q in out[key]) for key in
                      ['points_of_interest','routes','spawn_despawn_points','witness_hotspots']]
            lines.append(f"| {d['name_ru']} | {d['walkers_day']}/{d['walkers_evening']} | "+' | '.join(map(str,counts))+' |')
        lines += [f"Всего: {len(out['points_of_interest'])} POI, {len(out['routes'])} петель, {len(out['spawn_despawn_points'])} общих точек спавна/деспавна, {len(out['connections'])} связей.",
                  f"Полиция: замкнутая пешая петля {out['police_patrol']['length_m']:.0f} м через старый город и неблагополучный район, 2 сотрудника.",
                  'Все 10 тегов активности представлены; длительность остановок и вместимость заданы.',
                  'Петли следуют тротуарам, обочинам сельских переулков, дворам и предложенным обходам зданий; проезжая часть только на зебрах/узлах.',
                  'Обычная толпа и полиция не заходят на песок; пляжный профиль имеет отдельные маршруты и подходы.',
                  'Проверены целые отрезки: здания, вода, ограды, стволы, мебель, запрещённые пересечения дорог; ошибок 0.',
                  'Выгруженная сеть связна: 1 компонент; замыкание каждой петли проверено.',
                  'Спавны за зданиями: по 3 проверенных 2D луча с подъездной дороги; скрытие от любой движущейся камеры проверять в runtime.',
                  'Пляжные спавны расположены за зданиями в долине/элитке; до песка есть связные пешие подходы.',
                  'Мост/тоннели считаются сухой поверхностью; высоту брать с настила, а не с воды.',
                  'Число глаз — локальные пересекающиеся оценки; не дополнительная толпа и не гарантия обнаружения.',
                  'Исходные JSON сохранены; SHA-256 зафиксированы и сверены. Unity, Assets и WORK_SYNC не изменялись.',
                  'Повтор: Python + NumPy, Shapely 2, Pillow; `python -B crowd_v12.py`; `--validate-only` проверяет JSON.',
                  'Это плановые данные, без запечённого NavMesh; художественная/игровая приёмка требует проверки в Unity.']
        assert len(lines)<=30
        (ROOT/'CROWD_v12_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-only',action='store_true')
    args = parser.parse_args()
    crowd = Crowd()
    if args.validate_only:
        out = read(ROOT/'crowd_v12.json')
        result = crowd.validate(out)
    else:
        out = crowd.output()
        (ROOT/'crowd_v12.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        crowd.preview(out)
        crowd.report(out)
        result = out['validation']
    print(json.dumps(result,ensure_ascii=True),flush=True)


if __name__ == '__main__':
    main()
