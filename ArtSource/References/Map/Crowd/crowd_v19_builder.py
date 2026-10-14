"""G18 crowd builder. Frozen v16 algorithm copied to preserve all earlier revisions.
Only additions: explicit pilot path crossings and a read-only diagnostic entry.
All segment, component, activity and occlusion assertions remain enforced.
"""
from map_plan_v16 import *
REV="v19"
STEM="MAP_PLAN_R01_v19"

def build_crowd(d,look,plan_hash,return_instance=False):
    """Reuse v12 grid, segment coverage, A*, collinear removal and occlusion logic."""
    old=load_module(MAP/'Crowd/crowd_v12.py','crowd_v12_reference')
    old.DENSITY=dict(old.DENSITY,tramduro=(2,2))
    # Narrow source footbridges/bridge verges need a finer grid than v12.
    old.STEP=.625
    class Crowd16(old.Crowd):
        def __init__(self):
            self.plan=d
            self.districts={q['id']:Polygon(q['polygon_m']) for q in d['districts']}
            self.beach=unary_union([valid(Polygon(q['polygon_m'])) for q in d['sand_areas']])
            self.districts['beach']=self.beach
            self.boundary=Polygon(d['boundary']['polygon_m'])
            self.buildings={b['id']:valid(geom(b)) for b in d['functional_buildings']}
            self.building_union=unary_union(list(self.buildings.values()))
            self.roads={r['id']:(r,LineString(r['polyline_m'])) for r in d['roads']}
            self.road_area=unary_union([l.buffer(r['width_m']/2,cap_style=2) for r,l in self.roads.values()])
            self.raw_water=unary_union([water_geometry(w) for w in d['water']])
            self.decks=[dict(id=b['id'],road_id='DECK_'+b['id'],kind='bridge',polyline_m=b['axis_m'],
                width_m=b['deck_width_m'],polygon_m=b['polygon_m'],van_access=b['van_access']) for b in d['bridges']]
            deck_area=unary_union([Polygon(b['polygon_m']) for b in d['bridges']])
            self.water=self.raw_water.difference(deck_area)
            self.fences=unary_union([LineString(seq) for f in d['fences'] for seq in f['solid_runs_m']]).buffer(.18)
            trunks=unary_union([Point(t['x'],t['y']).buffer(.3) for t in look['trees']])
            self.obstacles=unary_union([self.building_union,self.water,self.fences,trunks])
            self.dress=dict(buildings=[dict(id=b['id'],spawn_geometry=True,district_id=b['district_id'],
                front_road_id=b['access_road_id']) for b in d['functional_buildings']])
            self.crossings=[]
            self.make_crossings()
            # Approved deck walking is shared with vehicles on narrow road bridges.
            for b in d['bridges']:
                self.crossings.append(dict(id='WALK_'+b['id'],kind='shared_bridge' if b['van_access'] else 'footbridge',
                    road_ids=['DECK_'+b['id']],geometry=Polygon(b['polygon_m'])))
            approach=self.roads['06_port_road'][1]
            self.crossings.append(dict(id='WALK_TRAMDURO_SOURCE_APPROACH',kind='shared_bridge_approach',road_ids=['06_port_road'],
                geometry=substring(approach,max(0,approach.length-20),approach.length).buffer(3.2,cap_style=2)))
            for f in d['fences']:
                for gate in f['gates']:
                    if gate.get('road_id'):
                        self.crossings.append(dict(id='WALK_GATE_'+gate['id'],kind='property_gate',road_ids=[gate['road_id']],
                            geometry=Point(gate['position_m']).buffer(gate['width_m']/2)))
            # G18 paths explicitly authorize walking across the road at their surveyed endpoints.
            for path in d.get('v19_pilots',{}).get('passages',[]):
                corridor=LineString(path['pts']).buffer(path['width_m']/2)
                for rid,(road,line) in self.roads.items():
                    patch=corridor.intersection(line.buffer(road['width_m']/2+.4))
                    for endpoint in (path['pts'][0],path['pts'][-1]):
                        p=Point(endpoint)
                        if line.distance(p)<.2:
                            # Reach both walking shoulders, not just the near half of the carriageway.
                            patch=patch.union(p.buffer(road['width_m']/2+1.3))
                    if not patch.is_empty:
                        for index,piece in enumerate(parts(patch,'Polygon')):
                            self.crossings.append(dict(id='WALK_V19_'+path['id']+'_'+rid+'_'+str(index),kind='pilot_path_crossing',road_ids=[rid],geometry=piece))
            self.cross_area=unary_union([c['geometry'] for c in self.crossings])
            self.forbidden_road=self.road_area.difference(self.cross_area)
            spaces=[]
            for r,l in self.roads.values():
                half=r['width_m']/2
                spaces.append(l.buffer(half+3).difference(l.buffer(half+.15)))
            for b in self.buildings.values():spaces.append(b.buffer(4.5).difference(b))
            for f in d['fences']:spaces.append(valid(Polygon(f['polyline_m'])))
            for q in d['structures']:
                if q.get('polygon_m') and q['kind'] in ('park_lawn','plaza_paving','city_block_inside_sidewalks','courtyard','open_lawn','football_pitch'):
                    spaces.append(valid(Polygon(q['polygon_m'])))
            for r in d['paths']:spaces.append(LineString(r['polyline_m']).buffer(r['width_m']/2))
            spaces += [Polygon(b['polygon_m']) for b in d['bridges']]
            spaces += [self.beach,self.cross_area.buffer(2)]
            self.approaches=[]
            for b in d['bridges']:
                if not b['id'].startswith('footbridge_beach_'):continue
                for end,kind in zip(b['axis_m'],('beach_path','city_street')):
                    candidates=[r for r in d['paths']+d['roads'] if r['source_class']==kind and not r.get('bridge_id')]
                    target=min(candidates,key=lambda r:LineString(r['polyline_m']).distance(Point(end)))
                    l=LineString(target['polyline_m']);p=l.interpolate(l.project(Point(end)));seq=[end,list(p.coords[0])]
                    # Existing dry meadow between source path/sidewalk and deck; no new paving/road.
                    spaces.append(LineString(seq).buffer(1.4))
                    self.approaches.append(dict(bridge_id=b['id'],polyline_m=seq,width_m=2.8,
                        status='proposed pedestrian route over existing dry ground; source lacks approaches'))
            self.free=unary_union(spaces).intersection(self.boundary).difference(self.obstacles.buffer(old.RADIUS).union(self.forbidden_road))
            shapely.prepare(self.free)
            if os.environ.get('M1_DEBUG_FREE'):
                Path(os.environ['M1_DEBUG_FREE']).write_bytes(shapely.to_wkb(self.free))

        def make_crossings(self):
            # Reuse v12 intersection policy, with no stale zebra coordinates.
            self.dress['zebra_crossings']=[]
            old.Crowd.make_crossings(self)

        def pois(self):
            result=[]
            def add(did,tag,target,ref,max_offset=25,capacity=2):
                node,distance=self.nearest(target,self.by_district[did])
                if distance>max_offset:return
                result.append(dict(id=f'POI{len(result)+1:03d}',district_id=did,activity=tag,
                    position_m=self.positions[node].tolist(),source_ref=ref,target_offset_m=round(distance,3),
                    capacity=capacity,dwell_s=[10,45],node=node,placement_status='dry graph projection; animation alignment pending'))
            tags={'village_shop':'shop_queue','casino':'casino_door','kiosk':'kiosk','church':'church_steps',
                'low_shop_or_kiosk':'shop_queue','shop':'shop_queue'}
            for b in d['functional_buildings']:
                if b['type'] in tags or b['world_kind'] in tags:
                    target=nearest_points(self.buildings[b['id']].boundary,self.roads[b['access_road_id']][1])[0]
                    add(b['district_id'],tags.get(b['type'],tags.get(b['world_kind'])),list(target.coords[0]),b['id'],30,3)
            for q in d['structures']:
                tag='beach_lie' if q['kind']=='sun_lounger' else 'bench_sit' if q['kind'] in ('park_lawn','open_lawn') else 'playground' if q['kind']=='football_pitch' else None
                if tag:
                    target=q.get('position_m') or list(valid(Polygon(q['polygon_m'])).representative_point().coords[0])
                    add('beach' if tag=='beach_lie' else q['district_id'],tag,target,q['id'],35)
            for q in d['pois']:
                if 'bus' in q['name'].lower() or 'останов' in q['name'].lower():add(q['district_id'],'bus_wait',q['position_m'],q['id'],35)
                if q['district_id']=='beach' and 'kiosk' in q['name'].lower():add('beach','kiosk',q['position_m'],q['id'],15)
            for did in ('residential','old_town','industrial','fields'):
                b=next(b for b in d['functional_buildings'] if b['district_id']==did)
                add(did,'smoke_corner',b['center_m'],b['id'],80)
            return result

        def spawns(self):
            # v12's exact three-observer building occlusion, now v11 buildings/roads.
            result=[]
            for did in old.DENSITY:
                candidates=[]
                source_districts=['beach','elite','fields'] if did=='beach' else [did]
                for b in d['functional_buildings']:
                    if b['district_id'] not in source_districts:continue
                    poly=self.buildings[b['id']];rid=b['access_road_id'];road=self.roads[rid][1]
                    station=road.project(poly.centroid);span=min(20,road.length);begin=max(0,min(road.length-span,station-span/2))
                    observers=[road.interpolate(begin+span*f) for f in (0,.5,1)]
                    nodes=self.by_district[did if did=='beach' else b['district_id']]
                    pos=self.positions[nodes];dist=np.sum((pos-np.asarray(poly.centroid.coords[0]))**2,axis=1)
                    nearby=np.asarray(nodes)[dist<(math.sqrt(poly.area)+12)**2]
                    for node in nearby:
                        p=Point(self.positions[node])
                        if not .7<poly.distance(p)<4.2:continue
                        if all(LineString([o,p]).intersection(poly.buffer(-.1)).length>.35 for o in observers):
                            candidates.append((sum(o.distance(p) for o in observers),int(node),b['id'],rid,observers))
                candidates.sort(reverse=True,key=lambda q:(q[0],q[2],q[1]));selected=[]
                for _,node,bid,rid,observers in candidates:
                    if any(math.dist(self.positions[node],self.positions[q['node']])<4 for q in selected):continue
                    if selected and bid==selected[0]['occluder_building_id'] and any(c[2]!=bid for c in candidates):continue
                    selected.append(dict(id=f'SPAWN_{did}_{len(selected)+1:02d}',district_id=did,
                        location_district_id=did,position_m=self.positions[node].tolist(),node=node,usage=['spawn','despawn'],
                        occluder_building_id=bid,observer_road_id=rid,tested_observer_positions_m=[old.xy(o) for o in observers],
                        require_runtime_camera_occlusion=True,min_player_distance_m=25,visibility_grace_s=2))
                    if len(selected)==2:break
                if len(selected)<2:raise ValueError(f'Need two hidden spawns in {did}; found {len(selected)}')
                result+=selected
            return result

        def routes(self,pois,spawns):
            result=[]
            for did in old.DENSITY:
                nodes=self.by_district[did];pos=self.positions[nodes]
                # Geographic extrema of the source-derived connected cells; no v12 anchors.
                axis=0 if np.ptp(pos[:,0])>=np.ptp(pos[:,1]) else 1
                order=np.argsort(pos[:,axis],kind='stable')
                for j,fracs in enumerate(((.15,.50,.85),(.25,.65,.90))):
                    anchors=[int(nodes[int(order[min(len(order)-1,int(f*(len(order)-1)))])]) for f in fracs]
                    ids=[anchors[0]];penalty=set()
                    for a,b in zip(anchors,anchors[1:]+anchors[:1]):
                        leg=self.path(a,b,did=='beach',penalty);ids+=leg[1:]
                        penalty.update((min(u,v),max(u,v)) for u,v in zip(leg,leg[1:]))
                    line=LineString(self.polyline(ids))
                    result.append(dict(id=f'ROUTE_{did}_{j+1:02d}',district_id=did,
                        profile='beach_walker' if did=='beach' else 'town_walker',closed=True,speed_mps=[.8,1.25] if did=='beach' else [1,1.5],
                        poi_ids=[q['id'] for q in pois if q['district_id']==did and line.distance(Point(q['position_m']))<6],
                        _nodes=ids,**self.edge_record(ids)))
            anchors=[r['_nodes'][0] for r in result if r['district_id'] in ('old_town','residential')];ids=[anchors[0]]
            for a,b in zip(anchors,anchors[1:]+anchors[:1]):ids+=self.path(a,b)[1:]
            police=dict(id='POLICE_OLD_BAD_01',profile='police_foot_patrol',district_ids=['old_town','residential'],closed=True,
                officers=2,speed_mps=[1.15,1.45],pause_at_anchors_s=[5,15],_nodes=ids,**self.edge_record(ids))
            return result,police

        def output(self):
            self.graph();pois=self.pois();spawns=self.spawns();routes,police=self.routes(pois,spawns);links=[]
            hub=police['_nodes'][0]
            for r in routes:
                ids=self.path(hub,r['_nodes'][0],r['profile']=='beach_walker')
                links.append(dict(id='LINK_'+r['id'],profile=r['profile'],route_id=r['id'],purpose='network_connection',**self.edge_record(ids)))
            for q in pois+spawns:
                r=min([r for r in routes if r['district_id']==q['district_id']],key=lambda r:LineString(r['polyline_m']).distance(Point(q['position_m'])))
                endpoint,_=self.nearest(q['position_m'],r['_nodes']);ids=self.path(q['node'],endpoint,q['district_id']=='beach')
                links.append(dict(id='LINK_'+q['id'],profile=r['profile'],route_id=r['id'],point_id=q['id'],
                    purpose='spawn_access' if q in spawns else 'activity_access',**self.edge_record(ids)))
                q.update(route_id=r['id'],access_link_id=links[-1]['id']);q.pop('node')
            hotspots=[]
            for did in ('residential','old_town','transition','fields','beach'):
                for p in [q for q in pois if q['district_id']==did][:2]:
                    hotspots.append(dict(id='WITNESS_'+p['id'],district_id=did,position_m=p['position_m'],radius_m=20,
                        expected_eyes_day=5,expected_eyes_evening=4,estimates_only=True,require_runtime_los=True,source_ref=p['source_ref']))
            for r in routes+[police]:r.pop('_nodes')
            names={q['id']:q['name_ru'] for q in d['districts']}
            out=dict(schema_version='1.0',revision='R01_v19',generator='crowd_v19_builder.py (v16/v12 validated grid algorithms, G18 passages)',
                sources=[dict(path='../'+STEM+'.json',sha256=plan_hash)],coordinates=d['coordinates'],
                runtime_contract=dict(status='planning_data_not_baked_navmesh',walker_radius_m=.3,
                    sample_position_max_distance_m=.5,require_navmesh_complete_path=True,require_height_projection=True,
                    bridge_height_from_decks=True,spawn_policy='All player cameras must fail LOS for 2s; >=25m from each player; defer visible spawn/despawn.',
                    profile_policy='town_walker/police avoid all source sand; beach_walker may use dry access links.',
                    movement_policy='Follow exported corridors; NavMesh shortest paths may cut roads.',
                    apron_policy='Aprons/verges are proposed walks on existing ground, not new paving.',
                    witness_policy='Eyes are overlapping estimates; actual runtime LOS is required.'),
                districts=[dict(id=k,name_ru=names[k],walkers_day=v[0],walkers_evening=v[1],density_status='v12 planning density' if k!='tramduro' else 'proposal pending Fedya',
                    route_ids=[r['id'] for r in routes if r['district_id']==k]) for k,v in old.DENSITY.items()],
                points_of_interest=pois,routes=routes,spawn_despawn_points=spawns,witness_hotspots=hotspots,
                police_patrol=police,connections=links,
                allowed_crossings=[dict(id=c['id'],kind=c['kind'],road_ids=c['road_ids'],polygon_m=ring(c['geometry'])) for c in self.crossings],
                dry_decks=self.decks,pedestrian_approaches=self.approaches,
                missing_activities=['bar_door: no approved v11 bar'],grid_step_m=old.STEP)
            self.validate16(out)
            return out

        def validate16(self,out):
            pts=out['points_of_interest']+out['spawn_despawn_points']+out['witness_hotspots']
            paths=out['routes']+[out['police_patrol']]+out['connections']
            for q in pts:
                p=Point(q['position_m']);assert self.free.covers(p),q['id']
                assert not self.building_union.intersects(p) and not self.water.intersects(p),q['id']
            for q in paths:
                l=LineString(q['polyline_m']);assert self.free.covers(l),q['id']
                assert l.intersection(self.forbidden_road).length<1e-7,q['id']
                if q.get('closed'):assert q['polyline_m'][0]==q['polyline_m'][-1] and l.length>20,q['id']
                if q['profile']!='beach_walker':assert not l.intersects(self.beach),q['id']
            for q in out['spawn_despawn_points']:
                b=self.buildings[q['occluder_building_id']]
                assert all(LineString([o,q['position_m']]).intersection(b.buffer(-.1)).length>.35 for o in q['tested_observer_positions_m']),q['id']
            net=unary_union([LineString(q['polyline_m']) for q in paths]);edges=[]
            for l in parts(net,'LineString'):
                a,z=list(l.coords)[0],list(l.coords)[-1]
                edges.append(dict(from_node=str(a),to_node=str(z)))
            components=graph_components(dict(edges=edges))
            assert len(components)==1,'Crowd exported network disconnected'
            assert len({tuple(map(tuple,r['polyline_m'])) for r in out['routes']})==len(out['routes'])
            assert {q['activity'] for q in out['points_of_interest']}==old.ACTIVITIES-{'bar_door'}
            out['validation']=dict(passed=True,point_count=len(pts),route_count=len(out['routes']),connection_count=len(out['connections']),
                exported_network_components=len(components),blocked_segments=0,illegal_road_crossings=0,non_beach_sand_segments=0,
                occlusion_reference_rays=len(out['spawn_despawn_points'])*3,grid_nodes=len(self.positions),land_component_nodes=len(self.land_nodes),
                beach_inclusive_component_nodes=len(self.all_nodes),
                method='v12 exact segment coverage, 8-neighbour A*, collinear reduction, 3 building-occluded observer rays.',
                limitation='2D planning only; crowd camera/height/NavMesh tests belong to lead Unity work.')
    return Crowd16() if return_instance else Crowd16().output()
