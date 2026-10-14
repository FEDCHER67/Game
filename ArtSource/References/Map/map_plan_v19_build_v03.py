"""G18 review round 1: compact inhabited Hamlet, preserve previous deliverables.
Draft validation prints diagnostics; --write is exclusive-create.
"""
from pathlib import Path
import sys,json,copy,math,hashlib
import numpy as np
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union
from shapely.affinity import translate,rotate
sys.path.insert(0,str(Path(__file__).resolve().parent))
import map_plan_v19 as m
MAP=m.MAP;ROOT=m.ROOT;REVIEW=m.REVIEW
m.HAMLET_CENTRES.update({
 '02_ground_01':(182,559),'02_ground_03':(202,560),'02_plot_21':(192,537),'02_ground_04':(307,580),
 '02_ground_05':(267,477),'02_ground_06':(325,518),'02_ground_07':(335,585),
 '02_ground_08':(306,560),'02_ground_09':(334,559),'02_plot_19':(299,529),
 '02_plot_18':(290,506),'02_plot_20':(318,497),
 '02_v18_plot_01':(232,481),'02_v18_plot_02':(211,514),
 '02_v18_plot_03':(243,527),'02_v18_plot_04':(264,532)})
m.PLOT_COMPACTION.update({'02_ground_01':.60,'02_ground_03':.62,'02_plot_21':.66,
 '02_ground_04':.65,'02_ground_07':.60,'02_ground_08':.62,'02_ground_09':.56,'02_plot_18':.70,'02_v18_plot_02':.62,'02_plot_19':.82})
final_centres=MAP/'v19_round1_house_centres_v01.json'
if final_centres.exists():m.HAMLET_CENTRES.update(m.read(final_centres))

def avoid_buildings(d,r,mains):
 """Visibility-route a small driveway around visible full-size buildings; no collision bypass."""
 import heapq
 end=Point(r['polyline_m'][-1]);space=unary_union([m.poly(b).buffer(r['width_m']/2+.55,join_style=2) for b in d['functional_buildings'] if m.poly(b).distance(end)<65])
 if space.covers(end):
  from shapely.ops import nearest_points
  edge=nearest_points(end,space.boundary)[1];vec=np.array(edge.coords[0])-np.array(end.coords[0]);vec/=max(np.linalg.norm(vec),1e-6);end=Point(np.array(edge.coords[0])+vec*.15)
 lines=[LineString(q['polyline_m']) for q in mains]
 starts=[g.interpolate(g.project(end)) for g in lines];starts=sorted(starts,key=lambda q:q.distance(end))[:3]
 candidates=[tuple(end.coords[0])]+[tuple(q.coords[0]) for q in starts]
 for g in m.m18.parts(space,'Polygon'):
  candidates.extend(tuple(q) for q in g.buffer(.08,join_style=2).simplify(.08).exterior.coords[:-1])
 nodes=candidates;edges=[[] for _ in nodes]
 for i in range(len(nodes)):
  for j in range(i):
   l=LineString([nodes[i],nodes[j]])
   if not l.intersects(space):edges[i].append((j,l.length));edges[j].append((i,l.length))
 heap=[(0,0)];dist={0:0};prev={};goal=None
 while heap:
  cost,i=heapq.heappop(heap)
  if cost!=dist[i]:continue
  if 1<=i<=len(starts):goal=i;break
  for j,w in edges[i]:
   if cost+w<dist.get(j,1e20):dist[j]=cost+w;prev[j]=i;heapq.heappush(heap,(cost+w,j))
 if goal is None:raise ValueError('No driveway path '+r['id'])
 path=[nodes[goal]]
 while goal!=0:goal=prev[goal];path.append(nodes[goal])
 r['polyline_m']=[list(q) for q in path];r['length_m']=LineString(path).length

def prepare():
 old,d,units,moves,roads=m.assemble();p=m.details19(d)
 # Keep the full-size shed out of its house after the narrower garden's anchor adjustment.
 shed=next(b for b in d['functional_buildings'] if b['id']=='02_v18_shed_02_ground_08_4')
 m.move_record(shed,(2,-1));t=moves[shed['id']];moves[shed['id']]=(t[0]+2,t[1]-1)
 shed=next(b for b in d['functional_buildings'] if b['id']=='02_shed_19');delta=(301-shed['center_m'][0],522-shed['center_m'][1]);m.move_record(shed,delta);t=moves[shed['id']];moves[shed['id']]=(t[0]+delta[0],t[1]+delta[1])
 # Keep the actual occupied village compact; southern land is now the named outer hay/orchard approach.
 village=next(q for q in d['districts'] if q['id']=='village')
 village['polygon_m']=[[132.6,486],[188,468],[231,458],[296,458],[365,479],[374,585],[291,599],[132.6,605]]
 village['area_m2']=Polygon(village['polygon_m']).area
 # Closed southern view through real hill mass, beyond the village's inhabited edge.
 p['hills'] += [dict(id='V19_review_south_screen',x=245,z=408,rx=29,rz=17,height_m=7.8),
                dict(id='V19_review_south_east_screen',x=308,z=429,rx=39,rz=23,height_m=6.5)]
 # Reuse the approved infill language at the two exposed Rough courtyard lawns.
 p['kit'] += [dict(id='V19_R1_K'+str(i),module=mod,x=x,z=z,yaw=yaw,scale=1,place=place)
  for i,(mod,x,z,yaw,place) in enumerate([
   ('LAUNDRY_POLE_PAIR',652,600,0,'rough drying yard'),('BENCH_SOVIET',650,590,90,'rough drying yard'),
   ('DUMPSTER_ENCLOSURE',637,597,90,'rough service corner'),
   ('GARDEN_BED_2M',628,683,90,'rough north gardens'),('GARDEN_BED_2M',632,683,90,'rough north gardens'),
   ('GARDEN_BED_2M',636,683,90,'rough north gardens'),('GARDEN_BED_2M',628,687,90,'rough north gardens'),
   ('GARDEN_BED_2M',632,687,90,'rough north gardens'),('BENCH_SOVIET',638,685,90,'rough north gardens')])]
 # A shared garden store and workyard gives the north-west opening a clear destination.
 prototype=copy.deepcopy(next(b for b in d['functional_buildings'] if b['id']=='CL_v18_farm_1_barn'))
 original=copy.deepcopy(prototype);m.move_record(prototype,(232-prototype['center_m'][0],580-prototype['center_m'][1]))
 prototype.update(id='02_v19_garden_barn_r1',source_id='02_v19_garden_barn_r1')
 d['functional_buildings'].append(prototype)
 store=copy.deepcopy(original);m.move_record(store,(195-store['center_m'][0],487-store['center_m'][1]))
 store.update(id='02_v19_orchard_store_r1',source_id='02_v19_orchard_store_r1');d['functional_buildings'].append(store)
 # Internal south loop becomes an orchard work lane. Keep its endpoints/road identity for graph continuity.
 for r in d['roads']:
  if r['id']=='02_h_loop':r['polyline_m']=m.smooth_line([(320,486.4),(308,481),(297,471),(290,458),(260,452),(242,444)]);r['length_m']=LineString(r['polyline_m']).length
 loop=next(r for r in d['roads'] if r['id']=='02_h_loop');south=LineString(next(r for r in d['roads'] if r['id']=='02_h_south')['polyline_m']);q=Point(loop['polyline_m'][-1]);loop['polyline_m'][-1]=list(south.interpolate(south.project(q)).coords[0]);loop['length_m']=LineString(loop['polyline_m']).length
 # Refit access stubs for every moved gate to the closest retained lane, preserving fixed tower access.
 mains=[r for r in d['roads'] if r['id'] in ('02_h_main','02_h_north','02_h_south','02_h_loop','02_h_base')]
 for r in d['roads']:
  if r['id'].startswith('02_h_d'):avoid_buildings(d,r,mains)
 # v02 corrections are retained.
 for a in p['garage_shells']:
  if a['id'].startswith('04_v19_east_garage_'):a['x']-=12
 for a in p['kit']:
  if a['id']=='V19_K045':a['z']-=7
 m.finish_places(d,units)
 prior=m.read(MAP/'MAP_PLAN_R01_v19_build_v02.json')
 p['happykeys']=copy.deepcopy(prior['v19_pilots']['happykeys'])
 # Keep all non-Hamlet clusters identical; shift only rocks that now conflict with the compact plots.
 exclusions=unary_union([m.poly(b).buffer(5) for b in d['functional_buildings']]+[LineString(r['polyline_m']).buffer(r['width_m']/2+4) for r in d['roads']+d['paths']])
 for rock in p['happykeys']['rocks']:
  if rock['x']>390 or not exclusions.intersects(Point(rock['x'],rock['z']).buffer(rock['radius_m']+.25)):continue
  for radius in range(5,65,3):
   candidates=[(rock['x']+radius*math.cos(t),rock['z']+radius*math.sin(t)) for t in np.linspace(0,2*math.pi,24,endpoint=False)]
   target=next((q for q in candidates if 135<q[0]<390 and 390<q[1]<600 and not exclusions.intersects(Point(q).buffer(rock['radius_m']+.25))),None)
   if target:rock['x'],rock['z']=map(float,target);break
 roads=[dict(id=r['id'],before_m=q['length_m'],after_m=r['length_m'],before=q['polyline_m'],after=r['polyline_m']) for r,q in zip(d['roads'],old['roads']) if r['polyline_m']!=q['polyline_m']]
 points,graphs=m.graph19(d,old,roads);look,grey=m.flat19(d,old,units,moves,roads)
 # Preserve v02 calm farm-yard fitting.
 for f in look['world_v11_extensions']['fences']:
  if f['id'] in ('CL_v18_farm_1_fence','CL_v18_farm_2_fence','CL_v18_farm_3_fence'):
   g=Polygon(f['polyline_m']);look['yards'].append(dict(id='Y19_'+f['id'],kind='calm_activity',district='village',fence='',h=0,pts=m.flat(f['polyline_m']),gaps=[],tris=m.m16.triangles(g),perimeter=g.length,ground='lawn'))
 for output in (look,grey):output['v19']=copy.deepcopy(p);output['source_plan']='MAP_PLAN_R01_v19_build_v03.json'
 checks=m.diagnose(d,old,units,moves);metrics=m.metrics19(old,d,units)
 return old,d,look,grey,units,dict(geometry=checks,metrics=metrics,building_moves=moves,roads=roads,points=points,graphs=graphs)

if __name__=='__main__':
 old,d,look,grey,units,audit=prepare()
 print(json.dumps(audit['geometry'],indent=1));print(json.dumps({k:(v['current_neighbours']['after'] if k in ('houses','blocks') else v.get('after',v)) for k,v in audit['metrics'].items()},indent=1))
 for u in units[:16]:
  q=m.moved_plot(u);cross=[r['id'] for r in d['roads'] if not r['id'].startswith('02_h_d') and q.intersection(LineString(r['polyline_m']).buffer(r['width_m']/2+.5)).area>1]
  if cross:print('PLOT ROAD',u['id'],cross)
 if '--write' in sys.argv:
  if audit['geometry']['new_building_overlaps'] or audit['geometry']['plot_overlaps']:raise ValueError('Overlapping geometry')
  if len(audit['graphs']['road_graph']['components'])!=1:raise ValueError('Disconnected roads')
  T=m.m18.Terrain(look,d['hills']);start=len(d['hills']);fix={}
  for rnd in range(3):
   over=[k for k,g in T.grades().items() if g['max']>.0801 and k.startswith(('02_','04_','hamlet_','bridge_north'))]
   if not over:break
   fix.update(m.m18.grade_fix(None,d,T,over,'G18R1_'+str(rnd)))
  for h in d['hills'][start:]:h['id']=h['id'].replace('V18_GRADE','V19R1_GRADE')
  look['hills']=m.m16.flatten_look(d,no_veg=True)['hills']
  audit['road_profiles']={k:round(g['max']*100,4) for k,g in T.grades().items()};audit['grade_fit']=fix
  d['revision']='v19';d['source_plan']='MAP_PLAN_R01_v18.json';d['v19_build_revision']={'revision':'v03','reason':'Claude review round 1: compact inhabited Hamlet and purposeful Rough courtyards'}
  d['v19_pilots']['metrics']=audit['metrics']
  W=m.m18.m17.World(d);m.m18.rehydrate(W,d);dc=m.m18.crowd_view(W,d)
  kitdoc=m.read(ROOT/'ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01/validation_v01.json')['assets']
  for p in d['v19_pilots']['kit']+d['v19_pilots']['natural']:
   size=kitdoc[p['module']]['size_m'] if 'module' in p else p['size'];w=size[0];dep=size[1] if 'module' in p else size[2]
   g=translate(rotate(box(-w/2,-dep/2,w/2,dep/2),-p.get('yaw',0),origin=(0,0)),p['x'],p['z']);ring=[list(q) for q in g.exterior.coords]
   dc['fences'].append(dict(id=p['id']+'_crowd',kind='v19_prop_obstacle',polyline_m=ring,gates=[],solid_runs_m=[ring],gap_intervals_m=[],height_target_m=1))
  for p in d['v19_pilots']['happykeys']['rocks']:
   if not p['collider']:continue
   ring=[list(q) for q in Point(p['x'],p['z']).buffer(p['radius_m']).exterior.coords]
   dc['fences'].append(dict(id=p['id']+'_crowd',kind='v19_rock_obstacle',polyline_m=ring,gates=[],solid_runs_m=[ring],gap_intervals_m=[],height_target_m=1))
  text=json.dumps(d,ensure_ascii=False,indent=1)
  builder=m.m16.load_module(MAP/'Crowd/crowd_v19_builder.py','crowd_v19_round1')
  crowd=builder.build_crowd(dc,look,hashlib.sha256(text.encode()).hexdigest())
  for path,data in [('MAP_PLAN_R01_v19_build_v03.json',d),('Look/look_v19_build_v03_flat.json',look),('Greybox/greybox_v19_build_v03_flat.json',grey),('Crowd/crowd_v19_build_v03.json',crowd),('MAP_PLAN_R01_v19_BUILD_PATCH_v03.json',audit)]:m.save(MAP/path,data)
  print('Round 1 exclusive outputs written',flush=True)
