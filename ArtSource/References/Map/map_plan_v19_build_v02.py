"""Measured G18 layout corrections; retain original v19 outputs as the first checked revision."""
from pathlib import Path
import json,copy,sys,hashlib
ROOT=Path(__file__).resolve().parents[3];MAP=Path(__file__).resolve().parent
sys.path.insert(0,str(MAP));import map_plan_v19 as m
from shapely.geometry import Polygon,Point,box
from shapely.affinity import translate,rotate
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,d):
    with p.open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=1)
d=read(MAP/'MAP_PLAN_R01_v19.json');look=read(MAP/'Look/look_v19_flat.json');grey=read(MAP/'Greybox/greybox_v19_flat.json')
changes=[]
for b in d['functional_buildings']:
    if not b['id'].startswith('04_v19_east_garage_'):continue
    # Same district, parking edge, clear the established 04_drive loop. No POI is attached to these shells.
    moved=m.m16.move_building if hasattr(m.m16,'move_building') else None
    for key in ('footprint_m','polygon_m'):
        if key in b:b[key]=[[q[0]-12,q[1]] for q in b[key]]
    if 'center_m' in b:b['center_m'][0]-=12
    if 'position_m' in b:b['position_m'][0]-=12
    if 'entrance_m' in b:b['entrance_m'][0]-=12
    for point in b.get('v17',{}).get('doors',[]):point[0]-=12
    for output in (look,grey):
        q=next(q for q in output['buildings'] if q['id']==b['id']);q['x']-=12
        for k,stride in [('fp',2),('tris',2),('rects',5),('ent',3)]:
            if q.get(k):q[k]=m.shift_flat(q[k],[-12,0],stride)
    changes.append(dict(id=b['id'],delta_m=[-12,0],reason='Clear the measured van loop'))
for p in d['v19_pilots']['kit']:
    if p['id']=='V19_K045':p['z']-=7;changes.append(dict(id=p['id'],delta_m=[0,-7],reason='Clear frozen road and its shoulder'))
for p in d['v19_pilots']['garage_shells']:
    if str(p.get('id','')).startswith('04_v19_east_garage_'):
        if 'x' in p:p['x']-=12
for f in look['world_v11_extensions']['fences']:
    if f['id'] not in ('CL_v18_farm_1_fence','CL_v18_farm_2_fence','CL_v18_farm_3_fence'):continue
    poly=Polygon(f['polyline_m']);look['yards'].append(dict(id='Y19_'+f['id'],kind='calm_activity',district='village',fence='',h=0,pts=m.flat(f['polyline_m']),gaps=[],tris=m.m16.triangles(poly),perimeter=poly.length,ground='lawn'))
for output in (look,grey):output['v19']=copy.deepcopy(d['v19_pilots']);output['source_plan']='MAP_PLAN_R01_v19_build_v02.json'
d['v19_build_revision']=dict(revision='v02',changes=changes,terrain_rule='v19 calm activity pads are flat with 4-32 m fitted banks; building pads resolve from that field. Frozen revisions keep the old terrace algorithm.')
for name,data in [('MAP_PLAN_R01_v19_build_v02.json',d),('Look/look_v19_build_v02_flat.json',look),('Greybox/greybox_v19_build_v02_flat.json',grey),('MAP_PLAN_R01_v19_BUILD_PATCH_v02.json',d['v19_build_revision'])]:write(MAP/name,data)
print('Revision data saved; building crowd',flush=True)
W=m.m18.m17.World(d);m.m18.rehydrate(W,d);dc=m.m18.crowd_view(W,d)
kitdoc=read(ROOT/'ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01/validation_v01.json')['assets']
for p in d['v19_pilots']['kit']+d['v19_pilots']['natural']:
    size=kitdoc[p['module']]['size_m'] if 'module' in p else p['size'];w=size[0];depth=size[1] if 'module' in p else size[2]
    g=translate(rotate(box(-w/2,-depth/2,w/2,depth/2),-p.get('yaw',0),origin=(0,0)),p['x'],p['z']);ring=[list(q) for q in g.exterior.coords]
    dc['fences'].append(dict(id=p['id']+'_crowd',kind='v19_prop_obstacle',polyline_m=ring,gates=[],solid_runs_m=[ring],gap_intervals_m=[],height_target_m=1))
for p in d['v19_pilots']['happykeys']['rocks']:
    if not p['collider']:continue
    ring=[list(q) for q in Point(p['x'],p['z']).buffer(p['radius_m']).exterior.coords]
    dc['fences'].append(dict(id=p['id']+'_crowd',kind='v19_rock_obstacle',polyline_m=ring,gates=[],solid_runs_m=[ring],gap_intervals_m=[],height_target_m=1))
builder=m.m16.load_module(MAP/'Crowd/crowd_v19_builder.py','crowd_v19_builder')
crowd=builder.build_crowd(dc,look,hashlib.sha256(json.dumps(d).encode()).hexdigest())
write(MAP/'Crowd/crowd_v19_build_v02.json',crowd)
print('Crowd checks passed',flush=True)
