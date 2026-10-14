"""G18 stage 1. Read frozen v18; translate whole pilot units and rebuild dependent geometry.

python -B ArtSource/References/Map/map_plan_v19.py --dry
python -B ArtSource/References/Map/map_plan_v19.py
python -B ArtSource/References/Map/map_plan_v19.py --render
All deliverables are exclusive-create. No source revision is regenerated or overwritten.
"""
from __future__ import annotations
import argparse, copy, hashlib, importlib.util, json, math
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.affinity import translate
from shapely.ops import unary_union
from PIL import Image, ImageDraw, ImageFont

MAP = Path(__file__).resolve().parent
ROOT = MAP.parents[2]
REVIEW = ROOT / 'Working/Reviews/Map_v19_Pilots'
spec = importlib.util.spec_from_file_location('g18_v18_helpers', MAP / 'map_plan_v18.py')
m18 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m18)
m16 = m18.m16
m16.REV, m16.STEM = 'v19', 'MAP_PLAN_R01_v19'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p, d):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8') as f: json.dump(d, f, ensure_ascii=False, indent=1)
def poly(r, key='footprint_m'): return shapely.make_valid(Polygon(r[key]))
def xy(p, t): return [round(p[0]+t[0], 4), round(p[1]+t[1], 4)]
def shift_ring(p, t): return [xy(q,t) for q in p]
def shift_flat(p, t, stride=2):
    out=list(p)
    for i in range(0,len(out),stride): out[i:i+2]=xy(out[i:i+2],t)
    return out
def flat(g): return [round(v,4) for p in g for v in p]

# Individually placed clusters, in metres. Buildings and people retain their physical dimensions.
HAMLET_CENTRES = {
 '02_ground_01':(183,565), '02_ground_03':(209,568), '02_ground_04':(272,579),
 '02_ground_05':(267,474), '02_ground_06':(332,465), '02_ground_07':(265,437),
 '02_ground_08':(301,437), '02_ground_09':(351,437), '02_plot_18':(297,507),
 '02_plot_19':(347,412), '02_plot_21':(236,568), '02_plot_20':(336,497),
 '02_v18_plot_01':(205,484), '02_v18_plot_02':(206,524),
 '02_v18_plot_03':(243,527), '02_v18_plot_04':(264,532),
}
# Tighten oversized yards individually. Building footprints, doors, vehicles and characters never scale.
# Household objects keep their dimensions; their anchors move inward with their own plot.
PLOT_COMPACTION = dict(zip(HAMLET_CENTRES,[.82,.82,.75,.63,.62,.65,.70,.62,.78,.95,.90,.82,.80,.70,1,.95]))
ROUGH_GROUPS = [
 (['04_den'],(-8,0)),
 (['04_northwest_court','04_northwest_south_wing'],(5,-3)),
 (['04_west_north'],(-3,-3)),
 (['04_north_horizontal','04_north_horizontal_s2'],(0,-6)),
 (['04_west_arch_court'],(2,0)),
 (['04_west_middle','04_west_middle_s2'],(-3,-7)),
 (['04_center_south','04_center_south_s2'],(3,0)),
 (['04_quiet_court','04_quiet_annex'],(-6,-2)),
 (['04_far_east_north','04_far_east_north_s2'],(-6,-2)),
 (['04_east_inner_south','04_east_inner_south_s2','04_east_crossbar',
   '04_southeast_court','04_far_east_south','04_blind_alley_closed_end'],(-14,0)),
]

def unit_groups(d):
    b={q['id']:q for q in d['functional_buildings']};s={q['id']:q for q in d['structures']};f={q['id']:q for q in d['fences']}
    units=[]
    for key, target in HAMLET_CENTRES.items():
        g=poly(s[key],'polygon_m') if key in s else poly(f[key+'_fence'],'polyline_m')
        t=(round(target[0]-g.centroid.x,4),round(target[1]-g.centroid.y,4))
        units.append(dict(id=key, region=g.buffer(.7), plot=g, delta=t, factor=PLOT_COMPACTION[key], district='village',
                          buildings=[q['id'] for q in b.values() if q['district_id']=='village' and g.contains(Point(q['center_m']))]))
    for ids,t in ROUGH_GROUPS:
        # Courtyard interiors belong to the enclosing building group too.
        g=unary_union([poly(b[k]) for k in ids]).convex_hull
        units.append(dict(id='+'.join(ids),region=g.buffer(.4),plot=None,delta=t,district='residential',buildings=ids))
    return units

def owner(units,x,z):
    p=Point(x,z)
    return next((u for u in units if u['region'].covers(p)),None)

def relocated(p,u):
    c=u['plot'].centroid.coords[0] if u['plot'] is not None else (0,0)
    s=u.get('factor',1)
    return [round(c[i]+(p[i]-c[i])*s+u['delta'][i],4) for i in (0,1)]

def anchor_delta(p,u):
    q=relocated(p,u)
    return (q[0]-p[0],q[1]-p[1])

def moved_plot(u):
    return Polygon([relocated(q,u) for q in u['plot'].exterior.coords])

def reshape_record(r,u):
    for k in ('footprint_m','polygon_m','polyline_m','centerline_m'):
        if r.get(k):r[k]=[relocated(q,u) for q in r[k]]
    for k in ('center_m','entrance_m','position_m'):
        if r.get(k):r[k]=relocated(r[k],u)
    if r.get('solid_runs_m'):r['solid_runs_m']=[[relocated(q,u) for q in run] for run in r['solid_runs_m']]
    for gate in r.get('gates',[]):gate['position_m']=relocated(gate['position_m'],u)

def move_record(r,t):
    for k in ('footprint_m','polygon_m','polyline_m','centerline_m'):
        if r.get(k):r[k]=shift_ring(r[k],t)
    for k in ('center_m','entrance_m','position_m'):
        if r.get(k):r[k]=xy(r[k],t)
    if r.get('v17',{}).get('doors'):r['v17']['doors']=shift_ring(r['v17']['doors'],t)
    if r.get('solid_runs_m'):r['solid_runs_m']=[shift_ring(run,t) for run in r['solid_runs_m']]
    for g in r.get('gates',[]):g['position_m']=xy(g['position_m'],t)

def centre(r):
    for k in ('center_m','position_m'): 
        if r.get(k):return r[k]
    for k in ('polygon_m','footprint_m','polyline_m'):
        if r.get(k):return list((LineString(r[k]) if k=='polyline_m' else poly(r,k)).centroid.coords[0])
    return None

def smooth_line(points,steps=8):
    # Chaikin cuts retain end points; a 6.4 m carriageway follows broad, rounded bends.
    q=[np.array(p,dtype=float) for p in points]
    for _ in range(2):
        n=[q[0]]
        for a,b in zip(q,q[1:]):n.extend([.75*a+.25*b,.25*a+.75*b])
        n.append(q[-1]);q=n
    return [[round(float(x),4),round(float(z),4)] for x,z in q]

def roads19(d, original, units):
    roads={r['id']:r for r in d['roads']};changes=[]
    # Keep the B02 access and north connection; shorten the southern residential loop by 25 m.
    proposed={
      '02_h_south':[(240,494),(240,479),(242,457),(241,433),(240,414),(237,394),(233.6,374.6)],
      '02_h_loop':[(320,486.4),(318,479),(313,462),(319,449),(319,428),(320,404),(285,404),(253,407),(240,414)],
      '02_h_field09':[(240,414),(222,417),(204,428)],
      'hamlet_rough_e':[(424.8,574),(437,579),(452,594),(470,608),(490,607),(512,617),(534,627),(550.4,627.8)],
    }
    for rid, pts in proposed.items():roads[rid]['polyline_m']=smooth_line(pts)
    # Bypass offset grows and returns smoothly; endpoints and external junctions stay fixed.
    r=roads['hamlet_bypass'];line=LineString(r['polyline_m']);pts=[]
    for x,z in r['polyline_m']:
        delta=7*math.sin(math.pi*(z-470)/100)**2 if 470<z<570 else 0
        pts.append([round(x+delta,4),z])
    r['polyline_m']=pts
    # Attach all moved plot driveways to the nearest retained/shortened lane, from its centreline to the translated gate.
    main_ids=['02_h_main','02_h_north','02_h_south','02_h_loop','02_h_base']
    main={k:LineString(roads[k]['polyline_m']) for k in main_ids}
    for r in d['roads']:
        if not r['id'].startswith('02_h_d'):continue
        old=next(q for q in original['roads'] if q['id']==r['id']);end=old['polyline_m'][-1]
        unit=owner(units,*end)
        if unit is None:
            # A driveway may stop just outside its plot fence.
            nearest=min(units[:16],key=lambda u:u['plot'].distance(Point(end)))
            if nearest['plot'].distance(Point(end))<3:unit=nearest
        if unit is None:continue
        end=relocated(end,unit);p=Point(end)
        rid=min(main,key=lambda k:main[k].distance(p));start=list(main[rid].interpolate(main[rid].project(p)).coords[0])
        r['polyline_m']=[start,end]
    # The tower is retained; its access wraps around the newly compact house-20 plot.
    roads['02_h_d_tower']['polyline_m']=smooth_line([(320,486.4),(319,502),(322,509),(330,513),(338.4,512.6)])
    roads['02_h_d16']['polyline_m']=smooth_line([(319.2,422),(311,422),(301,422),(301.07,427.06)])
    # Main's east junction must still meet the offset bypass.
    r=roads['02_h_north'];bypass=LineString(roads['hamlet_bypass']['polyline_m']);p=Point(r['polyline_m'][-1])
    r['polyline_m'][-1]=list(bypass.interpolate(bypass.project(p)).coords[0])
    for r,old in zip(d['roads'],original['roads']):
        if r['polyline_m']!=old['polyline_m']:
            r['length_m']=LineString(r['polyline_m']).length
            changes.append(dict(id=r['id'],before_m=old['length_m'],after_m=r['length_m'],before=old['polyline_m'],after=r['polyline_m']))
    return changes

def assemble():
    old=read(MAP/'MAP_PLAN_R01_v18.json'); d=copy.deepcopy(old);units=unit_groups(old);moves={}
    for u in units:
        for bid in u['buildings']:
            b=next(b for b in old['functional_buildings'] if b['id']==bid)
            moves[bid]=anchor_delta(b['center_m'],u)
    # The B09 shed needs its own small offset after the yard becomes narrower; its size is unchanged.
    sid='02_v18_shed_02_ground_06_4';moves[sid]=(moves[sid][0]+2,moves[sid][1]-2)
    # Move the garage that otherwise seals the pitch approach into the north service yard.
    garage=next(b for b in old['functional_buildings'] if b['id']=='04_garage_32')
    moves[garage['id']]=(686-garage['center_m'][0],635.5-garage['center_m'][1])
    # Membership is evaluated only against frozen v18 coordinates, never against already moved neighbours.
    for r in d['functional_buildings']:
        u=owner(units,*r['center_m'])
        t=moves.get(r['id'],anchor_delta(r['center_m'],u) if u and r['district_id']==u['district'] else None)
        if t:move_record(r,t);moves[r['id']]=t
    for key in ('structures','water','fences','points','pois'):
        for r in d[key]:
            c=centre(r)
            if c is None:continue
            u=owner(units,*c)
            if u and (r.get('district_id',u['district'])==u['district']):
                if key=='water' and not r['id'].startswith(('02_','04_')):continue
                if key=='structures' and r['kind']=='meadow_with_grass_tufts':continue
                # Point markers within a building move rigidly with that building; yards/fences shrink around anchors.
                b=next((b for b in old['functional_buildings'] if b['id'] in moves and poly(b).covers(Point(c))),None)
                if b and key in ('points','pois'):move_record(r,moves[b['id']])
                elif key in ('fences','structures'):reshape_record(r,u)
                else:move_record(r,anchor_delta(c,u))
    for r in d['functional_sites']:
        s=next((s for s in d['structures'] if s['id']==r['id'] and s.get('district_id') in ('village','residential')),None)
        if s:
            for k in ('polygon_m','position_m'):
                if k in s:r[k]=copy.deepcopy(s[k])
    for key in ('props','trees'):
        for r in d['v17_dressing'][key]:
            u=owner(units,r['x'],r['y'])
            if u:r['x'],r['y']=relocated([r['x'],r['y']],u)
    for r in d['v17_dressing']['pads']:
        u=owner(units,*centre(r))
        if u:reshape_record(r,u)
    changes=roads19(d,old,units)
    return old,d,units,moves,changes

def details19(d):
    """Large purposeful places and relief, not evenly scattered decorative filler."""
    p=dict(schema='g18_pilots_1',scope_boxes_m=[[132.6,373.6,374,605],[550,554,824.8,696.4],[374,535,554,646]],
           hills=[],ravines=[],calm_pads=[],kit=[],natural=[],decals=[],passages=[],places=[])
    # Finite cosine supports fade to zero at their boundary. Existing roads/building pads have priority.
    hills=[('orchard_back',165,434,27,31,8),('orchard_shoulder',194,451,17,22,3.6),
       ('hamlet_west_hollow',183,471,11,10,-2.4),('hamlet_cut_east',355,535,18,11,6.8),
       ('south_hay_terrace',278,390,28,12,3.2),('north_garden',337,573,20,18,4.8),
       ('south_boundary_rise',207,396,25,19,7.5),('south_garden_hollow',300,416,8,7,-1.8),
       ('bypass_screen',375,510,17,28,10.5),('road_cut_west',459,559,22,17,10.8),
       ('road_cut_east',526,582,23,20,11.8),('road_north_screen',482,635,30,17,9.8),
       ('road_north_hollow',520,640,12,8,-2.5),('rough_edge_rise',817,680,8,12,5.2),
       ('rough_entry_screen',556,588,6,26,3.2),('rough_play_rise',680,596,17,14,.7),
       ('rough_north_garden',678,688,24,7,.6)]
    for name,x,z,rx,rz,h in hills:p['hills'].append(dict(id='V19_'+name,x=x,z=z,rx=rx,rz=rz,height_m=h))
    p['ravines']=[
        dict(id='V19_hamlet_drainage_gully',pts=[[197,462],[188,450],[186,435],[191,422],[204,407]],depth_m=3.5,half_width_m=10,spacing_m=6,flow='seasonal hollow down the western orchard slope'),
        dict(id='V19_brook_side_ravine',pts=[[482,587],[469,580],[455,568],[443,555],[430,542]],depth_m=5.5,half_width_m=12,spacing_m=7,flow='meandering cutting beside the road, opening toward the brook / river corridor'),
        dict(id='V19_north_road_gully',pts=[[515,641],[501,644],[486,648],[473,651]],depth_m=2.5,half_width_m=8,spacing_m=5,flow='shallow tributary behind the northern rise'),
    ]
    def pad(name,rect,mat,height_offset=0):
        g=box(*rect);r=dict(id=name,polygon_m=[list(q) for q in g.exterior.coords[:-1]],surface=mat,height_offset_m=height_offset)
        p['calm_pads'].append(r);p['places'].append(dict(id=name,purpose=name.replace('_',' '),polygon_m=r['polygon_m']))
    pad('hamlet_orchard_workyard',[178,445,194,462],'gravel',.5)
    pad('hamlet_hay_field',[247,382,298,395],'dry_field',.8)
    pad('hamlet_north_allotment',[325,555,360,584],'dry_field',.7)
    pad('hamlet_market_garden',[314,524,347,549],'dry_field',.5)
    pad('rough_service_yard',[660,632,694,639],'concrete')
    pad('rough_playground',[664,583,686,607],'worn_grass',.4)
    pad('rough_garage_court',[668,608,695,614],'gravel')
    pad('rough_east_service_parking',[792,586,817,628],'gravel')
    pad('B02_loading',[178,500,199,516],'gravel')
    pad('B03_loading',[582,550,601,558],'gravel')
    def kit(module,x,z,yaw=0,place='',scale=1):
        p['kit'].append(dict(id='V19_K%03d'%len(p['kit']),module=module,x=x,z=z,yaw=yaw,scale=scale,place=place))
    for module,x,z,yaw in [('BARN_RUINED',184,454,0),('SHED_RUINED',191,459,90),('TRACTOR_BROKEN',182,447,20),
       ('CART_WOODEN',188,450,-15),('WOODPILE',192,455,90),('WELL_RURAL',321,536,0),
       ('SCARECROW',340,573,12),('OUTHOUSE',354,581,180),('SHED_RUINED',332,580,180),
       ('BARN_RUINED',282,389,0),('CART_WOODEN',290,391,90),('WOODPILE',200,532,15),
       ('DUMPSTER_ENCLOSURE',668,635,0),('LAUNDRY_POLE_PAIR',678,602,0),('BENCH_SOVIET',681,585,90)]:kit(module,x,z,yaw)
    for x,z in [(251,389),(257,387),(263,391),(274,386)]:kit('HAY_BALE_ROUND',x,z,15+x%17)
    for x in [330,335,340,345,350]:
        for z in [559,563,567]:kit('GARDEN_BED_2M',x,z,90,'north allotment')
    for x in [321,327,333,339]:
        for z in [531,537,543]:
            if (x,z)!=(321,537):kit('GARDEN_BED_2M',x,z,90,'market garden')
    kit('SCARECROW',343,545,20,'market garden')
    # New garage shells use the existing building grammar, with kit doors and roof edges attached by v19.
    for i in range(6):
        x=671+i*3.8;z=611.5
        kit('GARAGE_DOOR_METAL_3M_AJAR' if i==2 else 'GARAGE_DOOR_METAL_3M',x,z-3.05,0,'garage court')
        p.setdefault('garage_shells',[]).append(dict(id='04_v19_garage_%02d'%i,x=x,z=z,w=3.6,depth=6,h=2.8,yaw=0))
    for i in range(4):
        p['garage_shells'].append(dict(id='04_v19_east_garage_%02d'%i,x=813,z=593+i*8,w=6,depth=6,h=2.8,yaw=90))
        kit('GARAGE_DOOR_METAL_3M',809.95,593+i*8,90,'east service parking')
    # Explicit passage records are also consumed as ground strips and obstacle exclusions.
    p['passages']=[dict(id='hamlet_orchard_passage',pilot='village',width_m=3.6,van=True,pts=[[173,476],[188,466],[212,456],[231,449]],purpose='orchard cart access; low-speed undulating dirt'),
        dict(id='road_berm_footpass',pilot='road',width_m=1.8,van=False,pts=[[428,578],[443,586],[462,591],[487,592],[510,602],[535,618],[550,627.8]],purpose='readable foot route around the cutting banks'),
        dict(id='rough_west_passage',pilot='residential',width_m=2.0,van=False,pts=[[550,627.8],[566,631],[565,646],[585,645]],purpose='north courtyard foot entry beside garages')]
    lines=[LineString(r['polyline_m']) for r in d['roads']]
    for a in p['passages']:
        for end in (0,-1):
            q=Point(a['pts'][end]);line=min(lines,key=lambda l:l.distance(q))
            edge=list(line.interpolate(line.project(q)).coords[0])
            if end==0:a['pts'].insert(0,edge)
            else:a['pts'].append(edge)
    p['passages'].append(dict(id='rough_playground_gate',pilot='residential',width_m=2.0,van=False,pts=[[704,554],[704,577.9],[688.07,577.9],[688.07,583],[682,595]],purpose='walk around the low south block through the retained pitch gate'))
    for a in p['passages']:
        p['decals'].append(dict(id=a['id'],texture='WHEEL_TRACKS_DIRT_v01' if a['van'] else 'WORN_PATH_v01',width_m=3 if a['van'] else 1.2,pts=a['pts']))
    p['natural']=[dict(id='V19_rock_%02d'%i,kind='rock',x=x,z=z,size=[w,h,w*.8],yaw=17*i)
       for i,(x,z,w,h) in enumerate([(448,567,3.6,2.2),(453,569,2.4,1.8),(516,568,3.4,2.4),(536,586,4.2,2.8),(205,535,2.8,1.9),(365,535,3.4,2.2)])]
    p['natural'] += [dict(id='V19_log_%02d'%i,kind='log',x=x,z=z,size=[.65,.65,5.2],yaw=yaw)
       for i,(x,z,yaw) in enumerate([(449,572,75),(522,568,55),(352,535,65),(199,533,40)])]
    d['v19_pilots']=p
    # A compact inhabited envelope; the former south strip remains the explicitly named hay field.
    district=next(q for q in d['districts'] if q['id']=='village')
    district['polygon_m']=[[132.6,486],[156,418],[202,393],[307,384],[374,410],[374,585],[291,594],[132.6,605]]
    district['area_m2']=poly(district,'polygon_m').area
    district['outline_status']='v19 inhabited groups plus orchard, allotment and hay field; approved pilot scope'
    return p

def happykeys19(d):
    """Approved G19 addition: map-wide clustered rocks; protected traversal clearance is explicit."""
    manifest=read(ROOT/'ArtSource/ThirdParty/happykeys_rocks_dead_trees/v01/manifest_v01.json')
    models=[q for q in manifest['models'] if q['type']!='tree_bare']
    boundary=poly(d['boundary'],'polygon_m')
    exclusions=unary_union([poly(b).buffer(5) for b in d['functional_buildings']]+[LineString(r['polyline_m']).buffer(r['width_m']/2+4) for r in d['roads']+d['paths']]+[Point(p['position_m']).buffer(7) for p in d['points']]+[m16.water_geometry(w).buffer(2) for w in d['water']]+[LineString(f['polyline_m']).buffer(1.5) for f in d['fences']])
    rng=np.random.default_rng(19019);centres=[];rocks=[]
    # Irregular roadside groups cover the whole map; each occupies one shoulder only.
    for did in [q['id'] for q in d['districts']]:
        area=poly(next(q for q in d['districts'] if q['id']==did),'polygon_m')
        roads=[r for r in d['roads'] if LineString(r['polyline_m']).intersects(area)]
        if not roads:roads=[dict(polyline_m=list(area.exterior.coords))]
        accepted=0
        for attempt in range(90):
            if accepted>=7:break
            r=roads[int(rng.integers(len(roads)))];line=LineString(r['polyline_m']);s=rng.uniform(0,line.length);a=line.interpolate(max(0,s-1));b=line.interpolate(min(line.length,s+1));q=line.interpolate(s)
            tangent=np.array([b.x-a.x,b.y-a.y]);tangent/=max(1e-8,np.linalg.norm(tangent));normal=np.array([-tangent[1],tangent[0]])*rng.choice([-1,1]);c=np.array([q.x,q.y])+normal*rng.uniform(10,28)
            if not area.covers(Point(c)) or any(np.linalg.norm(c-np.array(o))<17 for o in centres):continue
            cluster=[]
            for j in range(int(rng.integers(4,9))):
                model=models[int(rng.integers(len(models)))];scale=float(rng.uniform(.85,1.15));rad=max(model['bounding_box_m']['size'][:2])*.5*scale
                v=c+rng.normal(0,[3.2,2.1]);g=Point(v).buffer(rad+.25)
                if not boundary.covers(g) or exclusions.intersects(g) or any(np.linalg.norm(v-np.array([o['x'],o['z']]))<rad+o['radius_m']+.35 for o in rocks+cluster):continue
                cluster.append(dict(id='HK19_'+did+'_'+str(accepted)+'_'+str(j),model=model['id'],x=round(float(v[0]),4),z=round(float(v[1]),4),yaw=round(float(rng.uniform(0,360)),3),scale=round(scale,4),radius_m=rad,district=did,collider=model['id']!='ROCK_01'))
            if len(cluster)>=3:rocks+=cluster;centres.append(c.tolist());accepted+=1
    # Deliberate bank clusters beside the pilot ravines make their cut faces readable.
    for ri,r in enumerate(d['v19_pilots']['ravines']):
        line=LineString(r['pts'])
        for i,s in enumerate(np.linspace(6,max(6,line.length-6),7)):
            q=line.interpolate(s);v=np.array([q.x,q.y])+rng.normal(0,4,2);model=models[(i+ri*3)%len(models)];rad=max(model['bounding_box_m']['size'][:2])*.5
            g=Point(v).buffer(rad+.3)
            if boundary.covers(g) and not exclusions.intersects(g):rocks.append(dict(id=f'HK19_ravine_{ri}_{i}',model=model['id'],x=round(float(v[0]),4),z=round(float(v[1]),4),yaw=round(float(rng.uniform(0,360)),3),scale=1,radius_m=rad,district='pilot_ravines',collider=model['id']!='ROCK_01'))
    d['v19_pilots']['happykeys']=dict(source='ArtSource/ThirdParty/happykeys_rocks_dead_trees/v01/manifest_v01.json',licence='CC0-1.0',rocks=rocks,tree_rule='All bare and deciduous tree instances inside Rough plus 60 m fade are replaced with T01-T03; other trees preserved; Unity appearance audit required.')
    print('G19 rocks:',len(rocks),'clusters:',len(centres),flush=True)

def finish_places(d,units):
    p=d['v19_pilots'];prototype=next(b for b in d['functional_buildings'] if b['id']=='04_v17_garages_001')
    p['unit_transforms']=[dict(id=u['id'],region_m=[list(q) for q in u['region'].exterior.coords],centre_m=list(u['plot'].centroid.coords[0]) if u['plot'] is not None else [0,0],scale=u.get('factor',1),delta_m=list(u['delta'])) for u in units]
    for a in p['garage_shells']:
        b=copy.deepcopy(prototype);g=box(a['x']-a['w']/2,a['z']-a['depth']/2,a['x']+a['w']/2,a['z']+a['depth']/2)
        b.update(id=a['id'],source_id=a['id'],footprint_m=[list(q) for q in g.exterior.coords[:-1]],center_m=[a['x'],a['z']],width_m=a['w'],depth_m=a['depth'],height_m=a['h'])
        b['entrance_m']=[a['x']-a['w']/2-.05,a['z']] if a['yaw']==90 else [a['x'],a['z']-a['depth']/2-.05]
        b['v17'].update(rev='v19',doors=[b['entrance_m']],floor_h=a['h'],ground_h=a['h'])
        d['functional_buildings'].append(b)
    # Yard footprints are explicit calm terrain areas, including complete relocated household units.
    for u in units[:16]:
        p['calm_pads'].append(dict(id='plot_'+u['id'],polygon_m=[list(q) for q in moved_plot(u).exterior.coords[:-1]],surface='lawn',height_offset_m=0))
    for h in p['hills']:
        d['hills'].append(dict(id=h['id'],center_m=[h['x'],h['z']],radii_m=[h['rx'],h['rz']],height_m=h['height_m'],height_target_m=h['height_m'],rotation_deg=0,note='v19 finite cosine relief; road and plot constraints take priority'))
    for ravine in p['ravines']:
        line=LineString(ravine['pts']);n=math.ceil(line.length/ravine['spacing_m'])
        # At the regular interior stations, overlapping cosine lobes sum to the requested approximate depth.
        strength=ravine['depth_m']*ravine['spacing_m']/ravine['half_width_m']
        for i,s in enumerate(np.linspace(0,line.length,n+1)):
            q=line.interpolate(s);taper=min(1,(i+1)/2,(n-i+1)/2)
            d['hills'].append(dict(id=ravine['id']+'_%02d'%i,center_m=[round(q.x,4),round(q.y,4)],radii_m=[ravine['half_width_m']]*2,height_m=-strength*taper,height_target_m=-strength*taper,rotation_deg=0,note='v19 connected ravine lobe; summed depth target '+str(ravine['depth_m'])+' m'))
    # The selected foot/cart passages are real graph geometry; vehicle restrictions are explicit.
    for a in p['passages']:
        d['paths'].append(dict(id=a['id'],polyline_m=a['pts'],width_m=a['width_m'],length_m=LineString(a['pts']).length,
            district_id=a['pilot'] if a['pilot']!='road' else 'common',source_class='trail',van_access=a['van'],**{'class':'pedestrian' if not a['van'] else 'dirt_shortcut'},lanes=1))
    # Keep full-size openings when the fence footprint shrinks.
    from shapely.ops import substring
    original_fences={f['id']:f for f in read(MAP/'MAP_PLAN_R01_v18.json')['fences']}
    for f in d['fences']:
        if f.get('district_id') not in ('village','residential'):continue
        if f['polyline_m']==original_fences[f['id']]['polyline_m']:continue
        line=LineString(f['polyline_m']);gaps=[]
        for gate in f.get('gates',[]):
            s=line.project(Point(gate['position_m']));w=gate.get('width_m',3.4)
            gaps.append([max(0,s-w/2),min(line.length,s+w/2)])
        # Refit gate openings to the changed lanes plus their walking shoulders.
        road_space=unary_union([LineString(r['polyline_m']).buffer(r['width_m']/2+1.1) for r in d['roads']])
        cut=line.intersection(road_space)
        for seg in m18.parts(cut,'LineString'):
            if seg.length<.05:continue
            aa,bb=sorted((line.project(Point(seg.coords[0])),line.project(Point(seg.coords[-1]))));aa=max(0,aa-.3);bb=min(line.length,bb+.3)
            if bb-aa<.1:continue
            middle=line.interpolate((aa+bb)/2);gaps.append([aa,bb]);nearest=min(d['roads'],key=lambda r:LineString(r['polyline_m']).distance(middle))
            f.setdefault('gates',[]).append(dict(id=f['id']+'_G19_'+str(len(f['gates'])),position_m=list(middle.coords[0]),width_m=bb-aa,road_id=nearest['id']))
        gaps.sort();cursor=0;solid=[]
        for a,b in gaps:
            if a>cursor+.05:solid.append([list(q) for q in substring(line,cursor,a).coords])
            cursor=max(cursor,b)
        if cursor<line.length-.05:solid.append([list(q) for q in substring(line,cursor,line.length).coords])
        f['solid_runs_m']=solid;f['gap_intervals_m']=gaps

def graph19(d,old,changes):
    changed={r['id'] for r in changes}
    # Existing helper nodes at road-surface joins are retained; only new geometry is intersected.
    d['road_graph']=m16.graph(d['roads'])
    d['pedestrian_graph']=m16.graph(d['roads']+d['paths'])
    roads={r['id']:LineString(r['polyline_m']) for r in d['roads']}
    point_changes=[]
    for p,q in zip(d['points'],old['points']):
        if p['district_id'] in ('village','residential'):
            loc=Point(p['position_m']);rid=min(roads,key=lambda k:roads[k].distance(loc))
            end=roads[rid].interpolate(roads[rid].project(loc));p['access_road_id']=rid;p['van_stop_m']=list(end.coords[0])
            p['van_stop_offset_m']=end.distance(loc)
        stop=p.get('van_stop_m')
        if stop:
            n=m16.graph_stop(d['road_graph'],stop);m16.graph_stop(d['pedestrian_graph'],stop)
            if p['district_id'] in ('village','residential'):p['road_node_id']=n['id'];p['van_node_gap_m']=0
        if p!=q:point_changes.append(dict(id=p['id'],before=q,after=copy.deepcopy(p)))
    # Report geometry ownership and every added/removed edge, including intersection splits.
    delta={}
    for k in ('road_graph','pedestrian_graph'):
        a={e['id']:e for e in old[k]['edges']};b={e['id']:e for e in d[k]['edges']}
        delta[k]=dict(removed=[a[x] for x in a.keys()-b.keys()],added=[b[x] for x in b.keys()-a.keys()],
                      changed=[dict(before=a[x],after=b[x]) for x in a.keys()&b.keys() if a[x]!=b[x]],
                      components=m16.graph_components(d[k]))
    return point_changes,delta

def flat19(d,old,units,moves,changes):
    look=read(MAP/'Look/look_v18_flat.json');grey=read(MAP/'Greybox/greybox_v18_flat.json')
    changed={r['id'] for r in changes};roads={r['id']:r for r in d['roads']}
    for output in (look,grey):
        output['revision']='v19'
        for b in output['buildings']:
            if b['id'] not in moves:continue
            t=moves[b['id']];b['x'],b['y']=xy([b['x'],b['y']],t)
            for k,stride in [('fp',2),('tris',2),('rects',5),('ent',3)]:
                if b.get(k):b[k]=shift_flat(b[k],t,stride)
        for r in output['roads']:
            if r['id'] in changed:
                r['pts']=flat(roads[r['id']]['polyline_m'])
                if 'length' in r:r['length']=roads[r['id']]['length_m']
        points={p['id']:p for p in d['points']}
        for q in output['points']:
            p=points[q['id']]
            if p['district_id'] in ('village','residential'):q['x'],q['y']=p['position_m']
        # The typed extensions carry the moved fences, gardens and points without touching unrelated records.
        for k in ('structures','pois','fences'):
            output['world_v11_extensions'][k]=copy.deepcopy(d[k])
    old_ids={b['id'] for b in old['functional_buildings']}
    generated=m16.flatten_look(d,no_veg=True)
    look['buildings'] += [b for b in generated['buildings'] if b['id'] not in old_ids]
    grey['buildings'] += [b for b in m16.flatten_greybox(d)['buildings'] if b['id'] not in old_ids]
    look['hills']=generated['hills']
    water_before={w['id']:w for w in old['water']};water_changed={w['id'] for w in d['water'] if w!=water_before[w['id']]}
    for output,regen in ((look,generated),(grey,m16.flatten_greybox(d))):
        fresh={w['id']:w for w in regen['water'] if 'id' in w}
        output['water']=[fresh.get(w.get('id'),w) if w.get('id') in water_changed else w for w in output['water']]
    for r in look['ground']:
        if not r.get('pts'):continue
        g=Polygon(list(zip(r['pts'][::2],r['pts'][1::2])));u=owner(units,*g.centroid.coords[0])
        if u:
            for k in ('pts','tris'):r[k]=flat([relocated(q,u) for q in zip(r[k][::2],r[k][1::2])])
    for r in look['elite_fence']:
        src=next((f for f in d['fences'] if f['id']==r['id']),None)
        if src:r['pts']=flat(src['polyline_m'])
    for t in look['trees']:
        u=owner(units,t['x'],t['y'])
        if u:t['x'],t['y']=relocated([t['x'],t['y']],u)
    look['v17']['props']=copy.deepcopy(d['v17_dressing']['props'])
    p=d['v19_pilots'];look['v19']=copy.deepcopy(p);grey['v19']=copy.deepcopy(p)
    look['source_plan']='MAP_PLAN_R01_v19.json'
    # Keep the source district noise mask so the new inhabited envelope cannot alter terrain outside the pilots.
    for q in look['districts']:
        if q['id']=='village':q['v19_inhabited_outline']=flat(next(q for q in d['districts'] if q['id']=='village')['polygon_m'])
    for pad in p['calm_pads']:
        look['ground'].append(m16.ground_record(poly(pad,'polygon_m'),pad['surface'],pad['id'],65))
        # HeightModel uses these footprints only as calm terraces. Typed fences remain the single fence owner.
        look['yards'].append(dict(id='Y19_'+pad['id'],kind='calm_activity',district='village' if poly(pad,'polygon_m').centroid.x<400 else 'residential',fence='',h=0,pts=flat(pad['polygon_m']),gaps=[],tris=m16.triangles(poly(pad,'polygon_m')),perimeter=poly(pad,'polygon_m').length,ground=pad['surface']))
    for a in p['passages']:
        look['ground'].append(m16.ground_record(LineString(a['pts']).buffer(a['width_m']/2), 'gravel' if a['van'] else 'worn_grass',a['id'],64))
    # Replace just affected junction patches with geometry from the revised plan.
    regen=generated
    look['junctions']=[j for j in look['junctions'] if not changed.intersection(j.get('roads',[]))]
    look['junctions'] += [j for j in regen['junctions'] if changed.intersection(j.get('roads',[]))]
    # No new trees or changed models: move existing instances only where relocated geometry needs clearance.
    from shapely.ops import nearest_points
    excluded=unary_union([poly(b).buffer(1.2) for b in d['functional_buildings']]+[LineString(r['polyline_m']).buffer(r['width_m']/2+1.1) for r in d['roads']]+[LineString(a['pts']).buffer(a['width_m']/2+.7) for a in p['passages']])
    scope=unary_union([box(*b) for b in p['scope_boxes_m']]);tree_moves=[]
    source_trees=read(MAP/'Look/look_v18_flat.json')['trees']
    for i,t in enumerate(look['trees']):
        q=Point(t['x'],t['y'])
        if scope.covers(q) and excluded.covers(q):
            e=nearest_points(q,excluded.boundary)[1];v=np.array([e.x-q.x,e.y-q.y]);v/=max(1e-8,np.linalg.norm(v));e=np.array([e.x,e.y])+v*.15
            if scope.covers(Point(e)):t['x'],t['y']=[round(float(x),4) for x in e]
        if t!=source_trees[i]:tree_moves.append(dict(index=i,before=source_trees[i],after=copy.deepcopy(t)))
    p['tree_placement_changes']=tree_moves
    look['v19']=copy.deepcopy(p);grey['v19']=copy.deepcopy(p)
    grey['tree_data']=[v for t in look['trees'] for v in (t['x'],t['y'],.3,t['h'])]
    for key in ('hedges','barriers'):
        for r in grey.get(key,[]):
            if not ('x' in r and 'y' in r):continue
            u=owner(units,r['x'],r['y'])
            if u:r['x'],r['y']=relocated([r['x'],r['y']],u)
    look['ground'].sort(key=lambda g:g['prio'])
    return look,grey

def metrics19(old,d,units):
    base=read(REVIEW/'baseline_dimensions_g18_v01.json')
    bs={b['id']:poly(b) for b in d['functional_buildings']};obs={b['id']:poly(b) for b in old['functional_buildings']}
    result={}
    for name,ids in [('houses',[old['v18_phase_b']['metrics']['generation']['hamlet']['plot_shifts'][k]['house'] for k in HAMLET_CENTRES]),
                     ('blocks',[b['id'] for b in old['functional_buildings'] if b['district_id']=='residential' and b['world_kind'] in ('panel_block','base3_house') and b['id']!='04_blind_alley_closed_end'])]:
        pairs=set()
        for a in ids:
            for _,b in sorted((obs[a].distance(obs[b]),b) for b in ids if b!=a)[:2]:pairs.add(tuple(sorted((a,b))))
        rows=[dict(a=a,b=b,before_m=obs[a].distance(obs[b]),after_m=bs[a].distance(bs[b])) for a,b in sorted(pairs)]
        result[name]=dict(pairs=rows,before_mean_m=float(np.mean([r['before_m'] for r in rows])),after_mean_m=float(np.mean([r['after_m'] for r in rows])),before_max_m=max(r['before_m'] for r in rows),after_max_m=max(r['after_m'] for r in rows))
        neighbours={}
        for rev,shapes in [('before',obs),('after',bs)]:
            near=set()
            for a in ids:
                for _,b in sorted((shapes[a].distance(shapes[b]),b) for b in ids if b!=a)[:2]:near.add(tuple(sorted((a,b))))
            gaps=[shapes[a].distance(shapes[b]) for a,b in near]
            neighbours[rev]=dict(mean_m=float(np.mean(gaps)),max_m=max(gaps),pairs=len(gaps))
        result[name]['current_neighbours']=neighbours
    for did in ('village','residential'):
        rr={}
        for rev,data in [('before',old),('after',d)]:
            g=poly(next(q for q in data['districts'] if q['id']==did),'polygon_m');buildings=unary_union([poly(b) for b in data['functional_buildings']]).intersection(g)
            circle=shapely.maximum_inscribed_circle(g.difference(buildings),tolerance=.05)
            rr[rev]=dict(area_m2=g.area,built_up_pct=100*buildings.area/g.area,building_free_circle_diameter_m=2*circle.length,centre_m=list(circle.coords[0]))
        result[did]=rr
    result['plots']=dict(before_area_m2=sum(u['plot'].area for u in units[:16]),after_area_m2=sum(moved_plot(u).area for u in units[:16]),count=16)
    return result

def diagnose(d,old,units,moves):
    bs={b['id']:poly(b) for b in d['functional_buildings']};obs={b['id']:poly(b) for b in old['functional_buildings']}
    collisions=[]
    for a in moves:
        for b in bs:
            if a>=b and b in moves or a==b:continue
            area=bs[a].intersection(bs[b]).area;prev=obs[a].intersection(obs[b]).area if b in obs else 0
            if area>prev+.02:collisions.append([a,b,round(area,3),round(prev,3)])
    plotcoll=[]
    for i,u in enumerate(units[:16]):
        a=moved_plot(u)
        for v in units[:i]:
            area=a.intersection(moved_plot(v)).area
            if area>.02:plotcoll.append([u['id'],v['id'],round(area,2)])
    return dict(new_building_overlaps=collisions,plot_overlaps=plotcoll,moved_buildings=len(moves),changed_roads=len([r for r,s in zip(d['roads'],old['roads']) if r!=s]))

def render19(d):
    dst=MAP/'MAP_PLAN_R01_v19.png'
    if dst.exists():raise FileExistsError(dst)
    # Keep intermediate evidence too: no previous revision or temporary file is removed.
    base=REVIEW/'plan_v19_base_v01.png';overlay=REVIEW/'plan_v19_overlay_v01.png'
    if base.exists() or overlay.exists():raise FileExistsError('Render intermediates already exist')
    info=m16.render(d,base,overlay);im=Image.open(base).convert('RGB');dr=ImageDraw.Draw(im)
    sx,sy,H=info['x_px_per_m'],info['y_px_per_m'],info['height_px'];px=lambda p:(p[0]*sx,H-p[1]*sy)
    for h in d['v19_pilots']['hills']:
        x,y=px((h['x'],h['z']));rx,ry=h['rx']*sx,h['rz']*sy
        dr.ellipse((x-rx,y-ry,x+rx,y+ry),outline='#866D49' if h['height_m']>0 else '#617D84',width=2)
    for p in d['v19_pilots']['calm_pads']:dr.polygon([px(q) for q in p['polygon_m']],outline='#A9A473',width=2)
    for b in d['functional_buildings']:
        if b['district_id'] in ('village','residential'):dr.polygon([px(q) for q in b['footprint_m']],fill='#AA8872',outline='#403F36')
    for t in d['v17_dressing']['trees']:
        x,y=px((t['x'],t['y']));dr.ellipse((x-2,y-2,x+2,y+2),fill='#4F7A45')
    for p in d['v19_pilots']['kit']:
        x,y=px((p['x'],p['z']));dr.rectangle((x-2,y-2,x+2,y+2),fill='#754F35')
    font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',24)
    dr.rectangle((40,H-182,950,H-122),fill='#f7f0dd');dr.text((48,H-176),'VOLUNTEERS ONLY — R01 v19 / G18 pilot layout',font=font,fill='#354843')
    dr.text((48,H-145),'Compact plots, courtyards, bent road chain and stronger relief',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16),fill='#354843')
    im.save(dst)

def report19(d,audit):
    met=audit['metrics'];lines=['# Map plan R01 v19 — G18 stage 1','',
      'Source: frozen v18. Pilot layout, road chain and dependent graphs change. Full-map palette/sky and the G19 happykeys rock clusters are explicitly approved additions. Human, van and building dimensions are unchanged. Rough District and fade-zone bare/deciduous trees use approved CC0 happykeys T01-T03 with the supplied cold recolour and capsule proxies; trees elsewhere retain their previous models/materials.','',
      '## Spacing','', '| Measure | v18 | v19 |','| --- | ---: | ---: |']
    for label,k in [('House','houses'),('Block','blocks')]:
        v=met[k];n=v['current_neighbours']
        lines += [f"| {label} current two-neighbour mean gap (m) | {n['before']['mean_m']:.2f} | {n['after']['mean_m']:.2f} |",f"| {label} current two-neighbour max gap (m) | {n['before']['max_m']:.2f} | {n['after']['max_m']:.2f} |",f"| {label} frozen v18 pairs mean / max (m) | {v['before_mean_m']:.2f} / {v['before_max_m']:.2f} | {v['after_mean_m']:.2f} / {v['after_max_m']:.2f} |"]
    for did in ('village','residential'):
        for key in ('area_m2','built_up_pct','building_free_circle_diameter_m'):
            lines.append(f"| {did}: {key} | {met[did]['before'][key]:.2f} | {met[did]['after'][key]:.2f} |")
    lines += [f"| 16 household plot area (m²) | {met['plots']['before_area_m2']:.2f} | {met['plots']['after_area_m2']:.2f} |",'',
      'Gaps are footprint-edge distances. Current neighbours are the union of each building’s two nearest neighbours in each revision. Frozen pairs keep the v18 pairs for an honest displacement comparison. The empty circle is building-only, so an orchard, working field or relief can remain inside it; it is not a claim that those places are empty lawns.','',
      '## Places and traversal','',
      'The Hamlet has three household groups, an orchard workyard, hay field, north allotment and B02 loading area. The southern housing loop is shortened; the Forest connector retains its fixed endpoint. The Rough District gains ten garage shells, a garage court, service yard, east parking and a calm playground. Road bends are rounded. The three named passages preserve readable alternatives to the direct meadow cuts.','',
      '## Terrain and new fields','',
      '`v19_pilots` carries scope boxes, hills (metres, finite cosine supports), connected ravines (depth/half-width/station spacing), calm activity polygons, PILOT_KIT module placements (ground anchor/yaw), natural solid props, decal strips and explicit passages with van access. `tree_placement_changes` is a complete before/after instance list. `height_offset_m` is a design target; the Unity height model gives road and building access priority. All achieved heights and road grades require the Unity validation report.','',
      'The height field uses explicit positive/negative hills and fitted road cuttings. Existing road/building/yard constraints retain calm access surfaces. `v19_pilots.happykeys` records the CC0 source, tree replacement rule and deterministic natural rock clusters across the map. Every rock cluster excludes roads, paths, buildings, water, fence lines and gameplay points. R01 stays decorative; all other rocks use the manifest proxies. Source FBXs and the v07 textures remain unchanged.','',
      '## Every moved building','', '| Building | dx (m) | dz (m) |','| --- | ---: | ---: |']
    for k,t in audit['building_moves'].items():lines.append(f'| {k} | {t[0]:.3f} | {t[1]:.3f} |')
    lines += ['','## Every changed street','','| Street | v18 length (m) | v19 length (m) |','| --- | ---: | ---: |']
    for r in audit['roads']:lines.append(f"| {r['id']} | {r['before_m']:.2f} | {r['after_m']:.2f} |")
    lines += ['','## Every changed point','','| Point | v18 position | v19 position | v19 access road |','| --- | --- | --- | --- |']
    for r in audit['points']:lines.append(f"| {r['id']} | {r['before']['position_m']} | {r['after']['position_m']} | {r['after'].get('access_road_id','')} |")
    lines += ['','## Graph changes and checks','',
      'The complete exact records for every added, removed and changed road/pedestrian edge are in `MAP_PLAN_R01_v19_CHANGES.json`, alongside all point records, road polylines, building translations and metrics. Nodes are stable coordinate hashes; splitting a moved street can change several edges. Existing disconnected beach footbridge components are retained.','']
    for k,v in audit['graphs'].items():lines.append(f"- {k}: {len(v['added'])} added, {len(v['removed'])} removed, {len(v['changed'])} changed; {len(v['components'])} components.")
    lines += ['', 'Geometry checks: '+json.dumps(audit['geometry_checks'])+'.','',
      'Python road-profile check: '+json.dumps(audit['road_profiles'])+'. This is the numerical port, not a replacement for Unity wheel/ground checks.','',
      'Unity build, screenshots, route comparison, collisions, missing sounds and per-spec acceptance are recorded separately in `docs/reports/MAP_PILOT_v19_PROGRESS.md`. Performance is NOT RUN by request.']
    with (MAP/'MAP_PLAN_R01_v19_REPORT.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dry',action='store_true');ap.add_argument('--render',action='store_true');a=ap.parse_args()
    old,d,units,moves,roads=assemble()
    if a.render:render19(read(MAP/'MAP_PLAN_R01_v19.json'));return
    details19(d);finish_places(d,units);happykeys19(d)
    points,graphs=graph19(d,old,roads);look,grey=flat19(d,old,units,moves,roads)
    checks=diagnose(d,old,units,moves)
    print(json.dumps(checks,indent=1))
    if checks['new_building_overlaps'] or checks['plot_overlaps']:raise ValueError('Unresolved geometry overlaps')
    if len(graphs['road_graph']['components'])!=1:raise ValueError('Disconnected road graph')
    T=m18.Terrain(look,d['hills']);fix={};start=len(d['hills'])
    for rnd in range(3):
        over=[k for k,v in T.grades().items() if v['max']>.0801 and (k.startswith(('02_','04_','hamlet_')) or k=='bridge_north')]
        if not over:break
        print('Fitting road cuttings:',over,flush=True);fix.update(m18.grade_fix(None,d,T,over,'G18_'+str(rnd)))
    for h in d['hills'][start:]:h['id']=h['id'].replace('V18_GRADE','V19_GRADE');h['note']=h['note'].replace('v18','v19')
    look['hills']=m16.flatten_look(d,no_veg=True)['hills']
    grades={k:round(v['max']*100,4) for k,v in T.grades().items()}
    if max(grades.values())>8.01:raise ValueError('Road grade exceeds 8% in numerical port')
    audit=dict(building_moves=moves,roads=roads,points=points,graphs=graphs,metrics=metrics19(old,d,units),geometry_checks=checks,road_profiles=grades,grade_fit=fix)
    print(json.dumps({'spacing':{k:{kk:vv for kk,vv in v.items() if kk!='pairs'} for k,v in audit['metrics'].items()},'grade_max':max(grades.values())}),flush=True)
    if a.dry:return
    d['revision']='v19';d['title_ru']='VOLUNTEERS ONLY / R01 v19 — G18 pilot layout';d['source_plan']='MAP_PLAN_R01_v18.json'
    d['provenance']['v19_source_sha256']=hashlib.sha256((MAP/'MAP_PLAN_R01_v18.json').read_bytes()).hexdigest()
    d['metrics']['building_count']=len(d['functional_buildings']);d['v19_pilots']['metrics']=audit['metrics']
    names=['MAP_PLAN_R01_v19.json','Look/look_v19_flat.json','Greybox/greybox_v19_flat.json','Crowd/crowd_v19.json','MAP_PLAN_R01_v19_CHANGES.json','MAP_PLAN_R01_v19_REPORT.md']
    for n in names:
        if (MAP/n).exists():raise FileExistsError(n)
    # Crowd uses the same existing obstacle policy as v18; explicit new solid kit/natural footprints are included.
    W=m18.m17.World(d);m18.rehydrate(W,d)
    dc=m18.crowd_view(W,d)
    kitdoc=read(ROOT/'ArtSource/Props/STYLE_KIT_v3/PILOT_KIT_v01/validation_v01.json')['assets']
    from shapely.affinity import rotate
    for p in d['v19_pilots']['kit']+d['v19_pilots']['natural']:
        if 'module' in p:
            size=kitdoc[p['module']]['size_m'];w,depth=size[0],size[1]
        else:w,depth=p['size'][0],p['size'][2]
        g=translate(rotate(box(-w/2,-depth/2,w/2,depth/2),-p.get('yaw',0),origin=(0,0)),p['x'],p['z']);ring=[list(q) for q in g.exterior.coords]
        dc['fences'].append(dict(id=p['id']+'_crowd',kind='v19_prop_obstacle',polyline_m=ring,gates=[],solid_runs_m=[ring],gap_intervals_m=[],height_target_m=1))
    for rock in d['v19_pilots']['happykeys']['rocks']:
        if not rock['collider']:continue
        ring=[list(q) for q in Point(rock['x'],rock['z']).buffer(rock['radius_m']).exterior.coords]
        dc['fences'].append(dict(id=rock['id']+'_crowd',kind='v19_rock_obstacle',polyline_m=ring,gates=[],solid_runs_m=[ring],gap_intervals_m=[],height_target_m=1))
    print('Building crowd routes',flush=True)
    plan_text=json.dumps(d,ensure_ascii=False,indent=1)
    crowd_builder=m16.load_module(MAP/'Crowd/crowd_v19_builder.py','crowd_v19_builder')
    try:crowd=crowd_builder.build_crowd(dc,look,hashlib.sha256(plan_text.encode()).hexdigest())
    except AssertionError as e:
        tb=e.__traceback__
        while tb:
            if 'out' in tb.tb_frame.f_locals and 'points_of_interest' in tb.tb_frame.f_locals['out']:
                result=tb.tb_frame.f_locals['out'];activities=sorted({q['activity'] for q in result['points_of_interest']})
                print('Crowd activity check failed; actual:',activities,flush=True)
                (REVIEW/'crowd_draft_diagnostic.json').write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
                break
            tb=tb.tb_next
        raise
    for name,data in zip(names[:5],[d,look,grey,crowd,audit]):save(MAP/name,data)
    report19(d,audit);print('Data written; render with --render',flush=True)

if __name__=='__main__':main()
