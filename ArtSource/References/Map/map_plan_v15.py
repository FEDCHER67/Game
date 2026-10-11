#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Master v02 -> R01 v15. Python -B; Pillow, numpy and Shapely 2 required.

Source coordinates below are pixels in the supplied master, NOT a new frame.
The existing frame/m2_frame.json is the sole pixel/metre transform.
District functions own named regions; IDs and graph nodes do not depend on list order.
--baseline FILE --allow-region 05_downtown guards a later LOCAL revision.
Only v15 deliverables and Master_v02/fragments/v15_* are written. No Unity writes.
"""
import argparse
import builtins
import contextlib
import copy
import hashlib
import heapq
import html
import json
import io
import math
import random
import runpy
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely import affinity
from shapely.geometry import Point, LineString, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, nearest_points

ROOT = Path(__file__).resolve().parent
STEM = 'MAP_PLAN_R01_v15'
FRAME = json.loads((ROOT/'Master_v02/frame/m2_frame.json').read_text(encoding='utf-8'))
OLD = json.loads((ROOT/'MAP_PLAN_R01_v14.json').read_text(encoding='utf-8'))
S = FRAME['transform']['metres_per_px']
OX, OY = FRAME['transform']['origin_px']
FONT = Path('C:/Windows/Fonts/arial.ttf')
REGIONS = [
    ('01_forest', 'forest', 'Лес', 'Forest', '#b7cfa9'),
    ('02_hamlet', 'village', 'Хутор', 'Hamlet', '#dbe1b7'),
    ('03_crossing', 'transition', 'Перекрёсток', 'Crossing', '#e1e2ca'),
    ('04_rough', 'residential', 'Район подворотен', 'Rough District', '#d4d1b6'),
    ('05_downtown', 'old_town', 'Город', 'Downtown', '#e7ddc8'),
    ('06_port', 'industrial', 'Промышленный порт', 'Industrial Port', '#c5ced0'),
    ('07_elite', 'elite', 'Элитный холм', 'Elite Hill', '#c4d2ae'),
    ('08_valley', 'fields', 'Тихая долина', 'Quiet Valley', '#d8dec2'),
    ('09_beach', 'beach_parking', 'Городской пляж', 'City Beach', '#f2e1ae'),
]
REGION_OF = {d:r for r,d,*_ in REGIONS}
DISTRICT_OF = {r:d for r,d,*_ in REGIONS}
FOLD = {f['id']:f for f in OLD['functional_buildings']}
POLD = {p['id']:p for p in OLD['points']}
LAYERS = ['districts','roads','paths','water','building_masses','functional_buildings',
        'functional_sites','points','plots','microdistricts','farmsteads','vegetation_parcels',
          'crop_fields','hills','beaches','outfalls']


def digest(obj):
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()).hexdigest()


def m(p):
    return [round((p[0]-OX)*S,3), round((OY-p[1])*S,3)]


def px(p):
    return [OX+p[0]/S, OY-p[1]/S]


def mm(pts):
    return [m(p) for p in pts]


def beach_px(p):
    # Detail has no metre scale: register through three master bridges, buildings and T-pier end.
    return (float(np.interp(p[0],[0,220,647,1090,1254],[540,576,673,761,801])),
            float(np.interp(p[1],[0,246,500,840,1075,1254],[427,485,544,608,650,684])))


BEACH_SHORE_SRC=[(0,917),(80,862),(141,807),(226,750),(280,741),(350,774),(402,816),(507,854),
                 (642,862),(756,850),(862,802),(921,747),(986,733),(1049,765),(1099,831),(1141,887),(1254,935)]
CITY_SHORE_MASTER=[beach_px(p) for p in BEACH_SHORE_SRC]


def ring(g):
    if not isinstance(g, Polygon) or not g.is_valid or g.is_empty or g.interiors:
        raise ValueError('Expected valid simple polygon: '+str(g)[:220])
    return [[round(x,3),round(y,3)] for x,y in list(orient(g,1).exterior.coords)[:-1]]


def poly(pts):
    return ring(Polygon(mm(pts)))


def rect(cx,cy,w,h,angle=0):
    a=math.radians(angle)
    return [(cx+x*math.cos(a)-y*math.sin(a), cy+x*math.sin(a)+y*math.cos(a))
            for x,y in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]


def oval(cx,cy,rx,ry,n=40):
    return [(cx+rx*math.cos(i*2*math.pi/n),cy+ry*math.sin(i*2*math.pi/n)) for i in range(n)]


def smooth(pts,steps=2,closed=False):
    q=list(pts)
    for _ in range(steps):
        out=[] if closed else [q[0]]
        for a,b in zip(q,q[1:]+([q[0]] if closed else [])):
            out.extend([(a[0]*.75+b[0]*.25,a[1]*.75+b[1]*.25),
                        (a[0]*.25+b[0]*.75,a[1]*.25+b[1]*.75)])
        if not closed: out.append(q[-1])
        q=out
    return q


def interpolate_trace(pts):
    """Interpolating cubic shoreline: preserve surveyed vertices, round the faceted screenshot trace."""
    out=[]
    for i in range(len(pts)-1):
        a=np.asarray(pts[max(0,i-1)],float); b=np.asarray(pts[i],float)
        c=np.asarray(pts[i+1],float); e=np.asarray(pts[min(len(pts)-1,i+2)],float)
        for t in [0,.25,.5,.75]:
            q=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-e)*t*t+(-a+3*b-3*c+e)*t*t*t)
            out.append(tuple(q))
    return out+[pts[-1]]


def put(d,layer,record,region):
    record['change_region']=region
    d[layer].append(record)
    return record


def road(d,oid,pts,region,cls='town_street',width=None,walk=False):
    width=width or OLD['road_classes'][cls]['width_m']
    pts=mm(pts)
    q=dict(id=oid, **{'class':cls}, width_m=width, district_ids=[DISTRICT_OF.get(region,'common')],
           polyline_m=pts, lanes=0 if walk else (2 if width>=6 else 1), length_m=round(LineString(pts).length,3),
           walkable=True,van_access=not walk)
    return put(d,'paths' if walk else 'roads',q,region)


def site(d,oid,kind,pts,region,label='',**extra):
    return put(d,'functional_sites',dict(id=oid,type=kind,district_id=DISTRICT_OF.get(region,'common'),
               polygon_m=poly(pts),label_ru=label,**extra),region)


def water(d,oid,kind,pts,region,label):
    p=poly(pts)
    return put(d,'water',dict(id=oid,kind=kind,polygon_m=p,center_m=list(Polygon(p).centroid.coords[0]),
               name_ru=label,district_id=DISTRICT_OF.get(region,'common')),region)


def building(d,oid,pts,region,kind=None,label=None,floors=1,source_key='',confidence='proposed',poi=None):
    p=poly(pts); g=Polygon(p); bounds=g.bounds
    if oid in FOLD or kind:
        old=FOLD.get(oid,{})
        # Preserve semantics/IDs, never stale geometry, access references or special compound footprints.
        q={k:copy.deepcopy(old[k]) for k in ['type','group','icon','color','purchasable','accessible','on_rail'] if k in old}
        q.update(id=oid,type=kind or old['type'],district_id=DISTRICT_OF[region],district=DISTRICT_OF[region],
                 label_ru=label or old.get('label_ru',oid),group=q.get('group','building'),icon=q.get('icon',''),
                 color=q.get('color','#c7b49a'),center_m=[round(v,3) for v in g.centroid.coords[0]],
                 width_m=round(math.dist(p[0],p[1]),3),depth_m=round(g.area/math.dist(p[0],p[1]),3),
                 footprint_m=p,storeys=floors,footprint_shape='polygon',rotation_deg=0,
                 source_master_key=source_key,mapping_confidence=confidence,source_master_px=list(map(float,px(g.centroid.coords[0]))))
        if poi or old.get('poi_id'): q['poi_id']=poi or old['poi_id']
        put(d,'functional_buildings',q,region)
    else:
        q=dict(id=oid,district_id=DISTRICT_OF[region],kind='panel' if region=='04_rough' else ('tower' if 'TOWER' in oid else 'rural_house' if region=='02_hamlet' else 'midrise'),
               center_m=[round(v,3) for v in g.centroid.coords[0]],width_m=round(bounds[2]-bounds[0],3),
               depth_m=round(bounds[3]-bounds[1],3),floors=floors,polygon_m=p,
               source_master_key=source_key,source_master_px=list(map(float,px(g.centroid.coords[0]))))
        if region=='05_downtown': q['label_ru']=('Башня 1' if oid=='O14_TOWER_W' else 'Башня 2' if oid=='O14_TOWER_E' else f'Жилой дом · {floors} эт.')
        put(d,'building_masses',q,region)
    return q


def point(d,oid,pos,region,name=None,cat='poi',source='',confidence='proposed'):
    q=copy.deepcopy(POLD.get(oid,{}))
    q.update(id=oid,canonical_id=q.get('canonical_id',oid),name_ru=name or q.get('name_ru',oid),
             position_m=m(pos),district_id=DISTRICT_OF.get(region,'common'),category=q.get('category',cat),
             label_offset_px=[0,0],source_master_key=source,mapping_confidence=confidence)
    q.pop('road_node_id',None)
    return put(d,'points',q,region)


def seed():
    # Keep every v14 top-level key and its JSON type; historic statistics get recomputed or explicitly emptied.
    d={k:[] if isinstance(v,list) else {} if isinstance(v,dict) else v for k,v in OLD.items()}
    d.update(revision='v15',title_ru='VOLUNTEERS ONLY — мастер-карта / R01 v15',schema_version=OLD['schema_version'])
    d['road_classes']=copy.deepcopy(OLD['road_classes'])
    d['coordinates']=dict(unit='metre',origin='Master v02 source pixel (6,684)',x='east',y='north',
                          unity_mapping='(x, terrain_height, y)',district_outline_policy='Схематические границы районов; физических оград между районами нет.')
    d['specification']=dict(path='docs/CITY_MAP_REFERENCE_SPEC.md',revision='Master v02 / task v15',date='2026-10-07',
         brief_override='План по мастер-карте; листы Downtown/Beach точнее. Масштаб рамки сохранён. Решения игрового канона требуют согласования.')
    d['provenance']=dict(source_schema='MAP_PLAN_R01_v14.json',frame='Master_v02/frame/m2_frame.json',
         reference_images=['REF_FEDYA_MASTER_v02_'+n+'.png' for n in ['map','downtown_02','city_beach','marina']],
         method='Ручная трассировка в исходных пикселях; фиксированная рамка; отдельные локальные функции районов.',
         input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'MAP_PLAN_R01_v14.json',ROOT/'Master_v02/frame/m2_frame.json']+sorted(ROOT.glob('REF_FEDYA_MASTER_v02_*.png'))})
    return d


# Master shoreline, traced clockwise from NE to SW. Shared exactly by land, sea and coast segments.
COAST=[(1125,0),(1133,17),(1148,31),(1139,44),(1113,53),(1083,72),(1090,120),(1101,168),
       (1098,204),(1088,239),(1074,267),(1060,289),(1058,314),(1066,341),(1088,365),
       (1098,378),(1090,389),(1075,389),(1068,419),(1064,454),(1064,478),(1074,493),
       (1055,510),(1036,514),(1012,503),(994,508),(979,514),(952,517),(928,528),
       (902,542),(877,559),(858,580),(835,596),(808,610),
       (796,618),(781,614),(760,607),(740,599),(722,592),(704,596),(684,606),(661,611),
       (638,609),(620,603),(606,594),(590,591),(579,596),(574,613),(568,638),(549,648),
       (526,647),(503,656),(480,664),(466,657),(454,654),(443,658),(428,666),(407,656),
       (389,648),(367,644),(346,633),(323,628),(299,625),(271,626),(246,623),(226,624),
       (215,635),(209,627),(208,616),(191,613),(166,608),(153,613),(136,605),(113,601),
       (101,591),(82,590),(61,599),(36,613),(20,628),(6,648)]
MASTER_COAST_TRACE=COAST
# The higher-priority City Beach sheet replaces ONLY its shoreline span, with master coast kept elsewhere.
COAST=COAST[:COAST.index((796,618))]+list(reversed(CITY_SHORE_MASTER))+COAST[COAST.index((526,647)):]
COAST_TRACE=COAST
COAST=interpolate_trace(COAST_TRACE)


def coast_section(start,end):
    a=min(range(len(COAST)),key=lambda i:math.dist(COAST[i],start))
    b=min(range(len(COAST)),key=lambda i:math.dist(COAST[i],end))
    return COAST[a:b+1] if a<=b else list(reversed(COAST[b:a+1]))


MOUNTAIN=[(54,572),(58,496),(63,430),(68,365),(65,303),(67,253),(80,210),(113,193),(206,188),
          (297,181),(318,157),(338,127),(377,148),(425,165),(483,161),(536,144),(582,121),
          (639,110),(693,119),(756,99),(808,92),(851,61),(902,49),(956,58),(1004,48),(1048,49),(1080,62),(1118,28)]


def build_world(d):
    r='00_world'
    coast=mm(COAST)
    d['boundary']=dict(polygon_m=poly([(6,0),(1125,0)]+COAST[1:]),barrier='Горный хребет с севера/запада, берег с юга/востока',
                       barrier_band_m=5,coast_segments_m=[[a,b] for a,b in zip(coast,coast[1:])])
    water(d,'SEA','sea',COAST+[(6,864),(1377,864),(1377,-150),(1125,-150)],r,'Море').update(return_rule='return_to_last_ground_point',offshore_band_m=150)
    ridge=poly([(6,0),(1125,0),(1118,28)]+list(reversed(MOUNTAIN[:-1]))+[(6,648)])
    put(d,'vegetation_parcels',dict(id='MOUNTAIN_RIDGE',kind='rock_scarp',polygon_m=ridge,district_id='common',
        material='rock_scarp',barrier_role='natural_world_edge',height_target_m=45,blocks_foot=True,blocks_van=True,gate_road_ids=[]),r)
    d['mountain_foot_m']=mm(MOUNTAIN)
    river=smooth([(330,39),(344,57),(346,81),(357,106),(348,132),(349,202),(347,268),(349,338),
                  (356,376),(359,413),(381,438),(420,446),(468,446),(504,450),(531,461),(547,483),(573,486)],2)
    for oid,pts,width,kind in [('RIVER_N',river,6,'river'),('CANAL',[(573,486),(622,486),(673,485),(717,486),(761,485),(786,485)],7,'concrete_canal'),
                              ('RIVER_S',smooth([(786,485),(800,487),(805,510),(805,559),(805,585),(808,620)],2),6,'river')]:
        line=LineString(mm(pts))
        put(d,'water',dict(id=oid,kind=kind,centerline_m=mm(pts),polygon_m=ring(line.buffer(width/2,cap_style=2)),
            width_m=width,district_id='common',name_ru='Канал' if kind=='concrete_canal' else 'Река'),r)
    water(d,'MOUNTAIN_LAKE','lake',oval(329,39,17,10),r,'Горное озеро')
    roads=[('CROSS_NORTH',[(429,211),(489,211),(571,216),(624,213)]),
           ('CROSS_SPINE',[(429,211),(434,251),(430,291),(421,337),(409,373),(419,411),(420,450)]),
           ('HAMLET_CROSSING',[(217,320),(260,324),(300,330),(338,341),(363,364),(385,371),(409,373)]),
           ('CROSS_DOWNTOWN',[(409,373),(440,373),(479,371),(519,375),(539,375)]),
           ('ROUGH_PORT',[(624,213),(630,246),(641,287),(693,281),(748,275),(806,270),(880,263),(873,193),(898,198),(917,210),(937,219)]),
           ('ROUGH_DOWNTOWN',[(671,309),(669,283)]),
           ('HAMLET_VALLEY',[(291,437),(349,446),(397,454),(420,450)]),
           ('ELITE_APPROACH',[(811,403),(821,385),(841,375),(867,375),(882,377)]),
           ('ELITE_BEACH_ACCESS',[(811,452),(833,477),(850,503),(865,530),(882,520),(917,509),(946,507),(966,510)])]
    for oid,pts in roads:
        road(d,oid,pts,r,'highway' if oid in ['CROSS_SPINE','CROSS_DOWNTOWN','CROSS_NORTH','ROUGH_PORT'] else 'rural_road' if oid in ['HAMLET_CROSSING','HAMLET_VALLEY','ELITE_BEACH_ACCESS'] else 'town_street')
    # Approximate districts are zoning overlays, not physical fences.
    outlines={
      '01_forest':[(68,427),(291,428),(328,454),(345,623),(211,616),(100,586),(54,574)],
      '02_hamlet':[(72,211),(295,186),(335,192),(339,342),(331,428),(68,427),(65,303)],
      '03_crossing':[(359,158),(480,168),(574,145),(603,168),(616,215),(634,293),(536,305),(533,443),(421,440),(373,427),(361,340)],
      '04_rough':[(611,126),(872,110),(882,263),(642,288),(621,210)],
      '05_downtown':[(538,309),(811,309),(811,453),(538,453)],
      '06_port':[(912,76),(1061,61),(1082,71),(1099,208),(1088,230),(943,242),(927,226)],
      '07_elite':smooth([(841,304),(889,284),(933,291),(1012,312),(1053,349),(1062,410),(1044,458),(1003,481),(944,474),(881,480),(843,449),(827,392)],2,True),
      '08_valley':smooth([(374,461),(421,459),(475,468),(528,469),(543,492),(543,553),(531,605),(490,628),(444,647),(383,620),(354,568),(358,511)],2,True),
      '09_beach':[(548,493),(799,493)]+coast_section(CITY_SHORE_MASTER[-1],CITY_SHORE_MASTER[0])}
    for rid,did,ru,en,color in REGIONS:
        p=poly(outlines[rid]); g=Polygon(p)
        if rid=='09_beach': g=g.intersection(Polygon(d['boundary']['polygon_m'])); p=ring(g)
        put(d,'districts',dict(id=did,name_ru=f'{ru} [{en}]',color=color,polygon_m=p,parent_id=None,
             notes_ru='Контур зоны приблизительный; не ограда.',area_m2=round(g.area,3),building_count=0,share_percent=0),rid)
        d['change_regions'].append(dict(id=rid,label_ru=f'{ru} [{en}]',kind='district',district_id=did,
            polygon_m=p,bbox_m=list(g.bounds)))
    d['change_regions'].append(dict(id=r,label_ru='Берег, хребет и общие соединения',kind='world',bbox_m=list(Polygon(d['boundary']['polygon_m']).bounds)))


def build_forest(d):
    r='01_forest'
    building(d,'F06_WAGON',rect(154,529,22,7,-31),r,confidence='readable',source_key='01: wagon / black base badge')
    road(d,'START_ROAD',smooth([(291,437),(297,477),(296,512),(281,537),(249,553),(220,553),(194,536),(166,538)],2),r,'rural_road')
    d['railway']=dict(polyline_m=mm([(94,565),(117,551),(138,539),(164,524)]),from_point='RAIL_TUNNEL_W',to_point='B01',
        active_trains=False,service_road_id=None,road_crossings=[],water_bridges=[],buffer_stop_m=m((168,522)),
        notes_ru='Короткие рельсы у берега; вагон соответствует мастеру.',change_region=r)
    water(d,'FOREST_LAKE','lake',smooth([(229,449),(247,440),(273,446),(278,463),(268,480),(246,486),(224,474)],2,True),r,'Лесное озеро')
    water(d,'SWAMP_POND_1','swamp_pond',oval(127,456,19,19),r,'Болотный пруд')
    swamp=poly(oval(127,456,27,27))
    put(d,'vegetation_parcels',dict(id='SWAMP13',kind='swamp',district_id='forest',polygon_m=swamp),r)
    for i,pts in enumerate([[(78,454),(104,489),(100,538),(76,571),(60,546)],[(191,445),(213,445),(211,495),(171,508),(173,473)],
                            [(305,454),(325,474),(329,598),(303,610),(287,573),(310,526)],[(111,558),(175,552),(211,570),(247,565),(269,596),(243,610),(143,591)]]):
        put(d,'vegetation_parcels',dict(id=f'FOREST_GROVE_{i}',kind='grove',district_id='forest',polygon_m=poly(pts)),r)
    site(d,'HANGOUT13','hangout',oval(182,541,6,5),r,'Потухший костёр',base_id='B01')
    site(d,'RAIL_TUNNEL_W','rail_tunnel_portal',rect(94,565,8,7,-30),r,'ЖД у скалы')
    road(d,'TRAIL_FOREST_LAKE',smooth([(194,536),(196,509),(220,487),(238,486)],2),r,'trail',walk=True)
    road(d,'TRAIL_FOREST_COAST',smooth([(182,541),(163,565),(152,589)],2),r,'trail',walk=True)
    d['forest_features']=dict(swamp=dict(id='SWAMP13',kind='swamp',polygon_m=swamp,pond_ids=['SWAMP_POND_1']),
        lake=dict(water_id='FOREST_LAKE',label_ru='Лесное озеро'),hill={},hangout=dict(site_id='HANGOUT13',base_id='B01'),
        tunnel=dict(site_id='RAIL_TUNNEL_W',railway_end_m=m((94,565))),cove={},rocks=[],tree_policy='Рощи по мастеру; без случайного заполнения проходов.')


def build_hamlet(d):
    r='02_hamlet'
    for oid,pts in [('HAMLET_MAIN',[(217,320),(204,303),(199,274),(183,254),(183,240)]),
                    ('HAMLET_CHURCH',[(199,274),(185,263),(160,267),(129,264),(122,257)]),
                    ('HAMLET_FIELD',[(199,274),(235,269),(271,266),(313,259)]),
                    ('HAMLET_SOUTH',[(217,320),(208,365),(202,405),(194,440)]),
                    ('HAMLET_LOOP',smooth([(217,320),(251,328),(280,338),(290,357),(296,390),(292,414),(264,421),(230,416),(202,405)],2)),
                    ('HAMLET_WATER',[(299,330),(305,309),(304,302)]),
                    ('HAMLET_BASE',[(202,294),(177,296),(166,296)])]: road(d,oid,pts,r,'rural_road')
    for oid,c,w,h,ang in [('F06_GRANDPA',(151,282),27,16,0),('F06_CHURCH',(150,240),18,20,0),
         ('F06_PHARM',(224,393),24,15,0),('F06_BARN',(238,256),33,15,-2),('F06_VSHOP',(236,307),26,17,0),
         ('F06_WATER',(304,294),9,9,0),('F06_BUS',(173,288),5,5,0),('F07_AD_POLE',(188,321),2,2,0)]:
        building(d,oid,rect(*c,w,h,ang),r,confidence='readable' if oid in ['F06_CHURCH','F06_WATER'] else 'proposed')
    for i,(c,w,h) in enumerate([((122,246),20,13),((184,227),21,14),((250,234),22,13),((243,354),22,17),
                              ((307,349),25,14),((315,386),24,16),((270,403),24,14)],1):
        building(d,f'F06_HAMLET_{i:02}',rect(*c,w,h),r,floors=1)
    water(d,'HAMLET_POND','lake',oval(163,342,22,18),r,'Пруд хутора')
    for i,pts in enumerate([[(295,225),(328,220),(332,252),(297,258)],[(112,382),(140,377),(166,406),(131,413)]],1):
        p=poly(pts)
        put(d,'crop_fields',dict(id=f'FIELD13_{i}',district_id='village',crop='wheat',stripe_count=8,
            stripe_direction='north_south',polygon_m=p,area_m2=round(Polygon(p).area,2),label_ru='Поле'),r)
    for i,(c,w,h) in enumerate([((276,353),17,27),((317,405),23,11),((168,280),17,27),((239,375),21,10)],1):
        put(d,'vegetation_parcels',dict(id=f'ORCHARD06_{i}',kind='orchard',district_id='village',polygon_m=poly(rect(*c,w,h))),r)


def build_crossing(d):
    r='03_crossing'
    for oid,c,w,h in [('F06_BUYER',(506,250),35,20),('F06_GAS',(451,331),24,16),('F06_HUT',(398,325),23,17),
         ('F06_RUINS',(397,275),20,16),('F15_CROSS_NORTH',(503,184),22,19),('F15_CROSS_WEST',(397,204),21,17),
         ('F15_CROSS_EAST',(516,337),20,18),('F15_CROSS_SOUTH',(504,403),21,18)]:
        building(d,oid,rect(*c,w,h),r,kind='small_house' if oid.startswith('F15') else None,label='Дом' if oid.startswith('F15') else None)
    building(d,'F15_GAS_SHED',rect(477,338,18,14),r,kind='maintenance_shed',label='Сервис АЗС')
    road(d,'BUYER_YARD',[(430,291),(451,295),(481,296),(507,296),(507,274)],r,'rural_road')
    site(d,'BUYER_COMPOUND','production_yard',rect(490,253,75,65),r,'Двор приёмки')
    site(d,'GAS_FORECOURT','parking',rect(457,348,60,34),r,'АЗС · площадка')
    water(d,'LAKE','lake',smooth([(558,235),(578,232),(592,239),(587,253),(578,259),(561,256),(556,246)],2,True),r,'Пруд у перекрёстка')
    point(d,'P13',(589,254),r,source='03: pond edge')
    point(d,'P09-4',(476,272),r,source='03: buyer yard; proposed meeting')


def build_rough(d):
    r='04_rough'
    # Polygonal U/L panels match the open courtyards; no invented solid courtyard blocks.
    shapes=[[(623,155),(666,151),(669,194),(659,195),(656,164),(633,167),(636,194),(626,195)],
            [(679,148),(689,147),(692,185),(682,186)],[(698,147),(764,140),(765,150),(699,157)],
            [(774,138),(786,136),(793,182),(782,184)],
            [(792,137),(825,133),(831,171),(821,173),(818,146),(804,147),(807,177),(797,179)],
            [(837,129),(848,128),(853,177),(842,179)],
            [(635,204),(645,203),(647,220),(658,219),(657,203),(668,204),(674,230),(637,234)],
            [(681,198),(693,196),(699,244),(688,246)],[(706,221),(718,219),(723,265),(711,267)],
            [(731,206),(769,202),(771,213),(733,217)],
            [(782,198),(793,196),(803,262),(791,264)],
            [(802,218),(832,213),(841,250),(831,253),(825,225),(815,228),(822,254),(812,257)],
            [(840,188),(851,187),(858,232),(847,234)],[(803,188),(835,184),(836,195),(804,199)],
            [(644,245),(655,244),(658,267),(680,265),(682,275),(647,281)]]
    for i,p in enumerate(shapes,1): building(d,f'R15_P{i:02}',p,r,floors=5 if i%3 else 9)
    for oid,pts in [('ROUGH_W_LANE',[(675,146),(677,190),(680,251),(686,282)]),
                   ('ROUGH_C_LANE',[(770,157),(774,188),(779,238),(782,272)]),
                   ('ROUGH_E_LANE',[(858,136),(858,181),(864,248),(880,263)]),
                   ('ROUGH_MID',[(704,198),(724,198),(775,193),(817,182),(858,181)]),
                   ('ROUGH_COURT_W',[(678,199),(650,199),(646,195),(646,186)]),
                   ('ROUGH_COURT_E',[(817,182),(813,174),(813,169)]),
                   ('ROUGH_GARAGE_LANE',[(696,181),(720,181),(750,181),(773,181)])]:
        road(d,oid,pts,r,'alley')
    for oid,c,w,h,kind in [('F06_GBASE',(667,258),12,8,None),('F06_BAR',(645,174),17,10,None),
         ('F06_DEN',(824.5,237),4,8,None),('F06_24',(754,261),26,13,None),
         ('F06_HOSPITAL',(813,158),8,14,None),('F06_K1',(714,169),5,5,None),
         ('F06_K3',(853,245),7,6,None),('F13_SHAWARMA',(755,175),10,5,None),
         ('F13_BEER',(697,264),5,10,None),('F13_ATMSHOP',(667,258),0,0,'skip'),
         ('F13_DISCOUNTER',(867,150),8,23,None),('F13_LOMBARD',(795,218),0,0,'skip')]:
        if kind!='skip': building(d,oid,rect(*c,w,h),r,confidence='readable' if oid=='F06_24' else 'proposed')
    # Small v14 businesses occupy separate stalls visible in the master; proposals, not decoded labels.
    for i,(oid,c) in enumerate([('F13_ATMSHOP',(726,168)),('F13_LOMBARD',(737,167)),
                                ('F13_ZAIMY',(725,189)),('F13_BAR2',(736,188)),('F13_BETS',(747,187)),('F06_ATM',(710,205))]):
        building(d,oid,rect(*c,7,5),r)
    site(d,'ROUGH_FOOTBALL','football_pitch',rect(752,236,34,24),r,'Футбольное поле',surface='grass')
    for i,(c,w,h) in enumerate([((731,168),43,7),((731,188),41,7)],1):
        # A non-solid garage row site; the separate shop footprints remain the physical obstacles.
        site(d,f'GARAGE15_ROW_{i}','garage_yard',rect(*c,w,h),r,'Ряд гаражей',shell_count=6)
    for oid,c in [('BAD_CENTER',(724,210)),('BAD_BLOCK',(649,184)),('BAD_BLOCK_2',(813,177)),('BAD_BLOCK_3',(827,249)),
                  ('P09-2',(703,204)),('P13-4',(700,212)),('P11-3',(710,209))]:
        if oid=='P11-3': continue  # created at the F06_ATM entrance
        point(d,oid,c,r,source='04: courtyard / proposed v14 gameplay mapping')
    water(d,'ROUGH_POND','lake',oval(790,291,15,5),r,'Пруд южнее района')


def dt(p):
    return (539+(p[0]-35)*272/1210,309+(p[1]-125)*143/640)


def build_downtown(d):
    r='05_downtown'
    for oid,pts in [('DT_NORTH',[(35,125),(1245,125)]),('DT_SOUTH',[(35,765),(1245,765)]),
         ('DT_WEST',[(35,125),(35,420.385),(35,765)]),('DT_EAST',[(1245,125),(1245,545.7),(1245,765)]),
         ('DT_W_AVENUE',[(385,125),(385,583),(369,613),(369,765)]),('DT_E_AVENUE',[(879,125),(879,583),(886,623),(886,765)]),
         ('DT_CROSS',[(35,548),(385,548),(385,583),(879,583),(879,548),(1245,548)])]:
        road(d,oid,[dt(p) for p in pts],r,'town_street')
    features=[
      ('F06_POLICE',[(91,177),(112,177),(112,160),(185,160),(185,177),(222,177),(222,247),(184,247),(184,261),(112,261),(112,247),(91,247)],'police_station','Полиция 1',2,'10 (повторяется на башне)'),
      ('O14_TOWER_W',[(458,165),(518,165),(518,173),(574,173),(574,258),(550,258),(550,285),(474,285),(474,258),(458,258)],None,None,20,'башня 1'),
      ('O14_TOWER_E',[(671,173),(724,173),(724,165),(787,165),(787,256),(764,256),(764,284),(695,284),(695,256),(671,256)],None,None,20,'башня 2'),
      ('F06_CAFE2',rect(485,357,68,48),'cafe','Кафе',1,'кафе'),
      ('F06_SUPER',rect(758,357,71,49),'supermarket','Бутики',1,'бутики'),
      ('F15_BOOKS',[(446,475),(516,475),(516,501),(529,501),(529,540),(446,540)],'village_shop','Книги / подарки',1,'книги / подарки'),
      ('F15_RESTAURANT',[(722,475),(801,475),(801,540),(715,540),(715,501),(722,501)],'cafe','Кафе-ресторан',1,'кафе-ресторан'),
      ('F06_HBASE',[(86,612),(259,597),(267,696),(91,710)],'house_base','Будущая база #13',2,'13'),
      ('F06_REPAIR',rect(425,666,76,78),'car_workshop','Магазин для бусика #07',1,'07'),
      ('F15_OFFICE_1',rect(543,668,88,81),'office','Офис 1 #05',2,'05'),
      ('F15_OFFICE_2',[(773,628),(831,628),(831,643),(866,643),(866,708),(773,708)],'office','Офис 2 #06',2,'06'),
      ('F15_TAXI',rect(995,646,123,71),'depot','Таксопарк #12',1,'12'),
      ('F15_POLICE_2',[(1100,612),(1196,612),(1196,628),(1214,628),(1214,695),(1196,695),(1196,707),(1100,707)],'police_station','Полиция 2 #11',2,'11')]
    for oid,pts,kind,label,floors,key in features:
        building(d,oid,[dt(p) for p in pts],r,kind=kind,label=label,floors=floors,source_key='05:'+key,confidence='detail_sheet')
    for i,(pts,fl) in enumerate([([(70,320),(159,310),(168,434),(77,444)],5),
        ([(271,264),(338,256),(357,387),(284,396)],4),
        ([(940,187),(1022,187),(1022,165),(1153,165),(1153,239),(1003,239),(1003,252),(940,252)],6),
        (rect(1176,328,77,123),5), ([(912,331),(985,320),(1000,445),(928,456)],3),
        ([(1071,466),(1105,466),(1105,444),(1200,444),(1206,515),(1071,523)],4)],1):
        building(d,f'O15_RES_{i:02}',[dt(p) for p in pts],r,floors=fl,source_key=f'жильё {fl} этажей')
    site(d,'SQUARE14','square',[dt(p) for p in [(423,320),(831,320),(831,564),(423,564)]],r,'Центральная площадь',
         landmark_point_id='CLOCK_SQUARE',tower_ids=['O14_TOWER_W','O14_TOWER_E'],fountain_site_id='FOUNTAIN14')
    site(d,'FOUNTAIN14','fountain',[dt(p) for p in oval(622,433,37,37)],r,'Фонтан',basin_radius_m=8.3)
    for oid,c,w,h in [('DT_PARKING_W',(409,243),29,149),('DT_PARKING_E',(836,250),65,144),('POLICE14_PARKING',(238,211),27,70)]:
        site(d,oid,'parking',[dt(p) for p in rect(*c,w,h)],r,'Парковка',capacity_vans=6)
    for oid,c,w,h in [('DT_COURT_W',(224,386),74,228),('DT_PARK_E',(1068,350),115,172),('DT_COURT_S',(671,666),129,91)]:
        site(d,oid,'park',[dt(p) for p in rect(*c,w,h)],r,'Сквер' if oid=='DT_PARK_E' else 'Двор')
    # The two ATMs are point objects, not invented building footprints.
    point(d,'P11',dt((532,427)),r,name='Банкомат у кафе',cat='atm',source='05: ATM слева',confidence='detail_sheet')
    point(d,'P11-DT2',dt((714,427)),r,name='Банкомат у бутиков',cat='atm',source='05: ATM справа',confidence='detail_sheet')
    point(d,'CLOCK_SQUARE',dt((622,520)),r,name='Центральная площадь / фонтан',cat='landmark',source='05: центральная площадь (часы не показаны)',confidence='detail_sheet')
    point(d,'P10-2',dt((1155,720)),r,name='Полиция 2',source='05:11',confidence='detail_sheet')
    for oid,c in [('P09',(600,562)),('P13-3',(590,469)),('P13-5',(785,474))]: point(d,oid,c,r,source='05: proposed v14 point')
    # Those last coordinates are master pixels, explicitly kept south/inside Downtown.
    next(p for p in d['points'] if p['id']=='P09')['position_m']=m(dt((625,566)))
    next(p for p in d['points'] if p['id']=='P13-3')['position_m']=m((584,469))
    next(p for p in d['points'] if p['id']=='P13-5')['position_m']=m(dt((796,572)))
    lamps=[(445,400),(445,460),(449,551),(480,550),(526,465),(541,338),(565,321),(557,517),
           (586,552),(658,552),(686,517),(700,338),(802,400),(800,552),(450,727),(481,727),(829,727)]
    for i,p in enumerate(lamps,1):
        put(d,'functional_sites',dict(id=f'DT_LAMP_{i:02}',type='lamp',district_id='old_town',position_m=m(dt(p)),
            label_ru='Фонарь / якорь хвата',grip_anchor=True),r)
    # Individually read garden and street trees from the detailed sheet; no map-wide procedural redesign.
    trees=[(112,141),(213,144),(265,144),(321,144),(293,176),(339,180),(277,195),(243,276),
           (78,290),(140,294),(78,471),(107,498),(189,476),(233,444),(263,468),(293,410),(279,493),(322,470),
           (207,312),(242,330),(206,386),(160,447),(126,478),
           (462,143),(561,143),(649,153),(676,143),(783,169),(438,290),(476,317),(543,294),(567,294),
           (657,294),(698,314),(810,294),(818,343),(809,382),(820,518),(750,550),(712,546),(677,551),
           (638,534),(591,535),(548,495),(559,529),(485,550),(449,552),
           (963,145),(1008,145),(1100,143),(1200,147),(1223,185),(1223,219),(1066,278),(1100,301),
           (1039,332),(1105,369),(1063,397),(1017,415),(1098,414),(1208,423),(1027,484),(948,491),
           (1213,544),(987,548),(931,548),(65,612),(281,583),(335,615),(276,725),(484,614),
           (544,609),(590,614),(623,641),(622,701),(669,703),(713,702),(738,647),(741,620),
           (964,589),(1020,589),(1068,607),(1209,588),(1228,623)]
    for i,p in enumerate(trees,1):
        put(d,'functional_sites',dict(id=f'DT_TREE_{i:03}',type='tree',district_id='old_town',position_m=m(dt(p)),
            crown_radius_m=2.0,label_ru='Дерево'),r)
    for oid,pts in [('DT_W_COURT_PATH',[(193,289),(235,387),(175,488)]),
                    ('DT_E_PARK_PATH',[(1032,269),(1063,346),(1103,412),(1032,486)]),
                    ('DT_S_COURT_PATH',[(666,614),(667,696),(713,724)])]:
        road(d,oid,[dt(p) for p in pts],r,'foot_lane',width=1.6,walk=True)
    d['detail_registration']={'downtown':dict(source='REF_FEDYA_MASTER_v02_downtown_02.png',
       source_road_frame_px=[35,125,1245,765],master_road_frame_px=[539,309,811,452],method='axis affine; street frame anchors',
       note_ru='Номера 01–15 не восстановлены по догадке; на листе повторяется 10.')}


def build_port(d):
    r='06_port'
    for oid,c,w,h,ang in [('F06_DEPOT',(960,104),45,25,-5),('F06_WARE1',(1038,99),42,25,-5),
        ('F06_COMPLEX',(993,160),34,22,-5),('F06_MAINT',(1032,152),12,10,-4),('F06_TOW',(1033,168),12,10,-4),
        ('F13_TANK',(1011,204),14,14,0),('F06_CHIMNEY',(983,202),17,17,0),('F15_TANK_2',(1035,205),12,12,0)]:
        building(d,oid,oval(*c,w/2,h/2) if 'TANK' in oid or 'CHIMNEY' in oid else rect(*c,w,h,ang),r,
                 kind='storage_tank' if oid=='F15_TANK_2' else None,label='Резервуар 2' if oid=='F15_TANK_2' else None,
                 confidence='proposed',source_key='06: visible port structure; function proposed from v14')
    for oid,pts in [('PORT_MAIN',[(937,219),(954,203),(952,158),(949,135)]),
        ('PORT_NORTH_LOOP',[(949,135),(929,135),(926,89),(995,81),(1001,128),(1088,124)]),
        ('PORT_CROSS',[(949,135),(1001,128)]),
        ('PORT_SOUTH_LOOP',[(952,158),(977,181),(1057,179),(1060,218),(961,231),(954,203)])]:
        road(d,oid,pts,r,'rural_road')
    site(d,'PORT_QUAY','quay',[(1086,95),(1108,93),(1116,178),(1095,180)],r,'Портовый причал')
    site(d,'PORT_PIER','pier',[(1115,166),(1145,164),(1147,171),(1116,176)],r,'Пирс порта')
    road(d,'PORT_QUAY_ACCESS',[(1088,124),(1102,125),(1107,166)],r,'rural_road')
    point(d,'P09-3',(986,176),r,source='06: production yard, proposed')
    d['port_perimeter_px']=[(913,78),(1062,62),(1081,72),(1098,209),(1088,229),(943,240),(928,225),(913,78)]


def build_elite(d):
    r='07_elite'
    loop=smooth([(888,354),(924,351),(969,360),(1018,369),(1038,392),(1039,430),(1023,441),
                 (980,434),(930,420),(894,410),(881,395),(884,370),(888,354)],2)
    road(d,'ELITE_LOOP',loop,r,'rural_road')
    for oid,c,w,h,ang in [('F08_MANSION_1',(918,327),29,20,12),('F06_MANSION_2',(1008,344),30,21,12),
       ('F06_MANSION_3',(995,451),29,21,12),('F06_MANSION_4',(904,435),29,21,12),('F06_GUARD',(951,382),14,12,12),
       ('F15_ELITE_SERVICE',(985,394),31,21,12)]:
        building(d,oid,rect(*c,w,h,ang),r,kind='maintenance_shed' if oid.startswith('F15') else None,
                 label='Сервис холма' if oid.startswith('F15') else None,floors=2 if oid!='F06_GUARD' else 1)
    for i,(c,w,h,ang) in enumerate([((939,330),10,24,12),((1030,349),10,22,12),((1017,457),10,21,12),((880,427),9,21,12)],1):
        water(d,f'ELITE_POOL_{i}','pool',rect(*c,w,h,ang),r,'Бассейн')
    d['elite_perimeter_px']=smooth([(841,304),(889,284),(933,291),(1012,312),(1053,349),(1062,410),
                                   (1044,458),(1003,481),(944,474),(881,480),(843,449),(827,392)],2,True)
    hillpoly=poly(d['elite_perimeter_px'])
    put(d,'hills',dict(id='HILL_ELITE',center_m=m((948,381)),radii_m=[112*S,94*S],height_target_m=24,
        polygon_m=hillpoly,district_id='elite',notes_ru='Овал по мастеру; высота 24 м унаследована как предложение v14.'),r)
    point(d,'ELITE_GATE',(851,377),r,source='07: gate',confidence='readable')
    point(d,'BEACH_ENTRY',(966,510),r,source='07: beach access',confidence='readable')
    # Rigid transplant of EVERY v14 marina coordinate. No scale change, berth or boat count changes.
    old=OLD['marina']; root=list(LineString(mm(COAST)).interpolate(LineString(mm(COAST)).project(Point(m((981,515))))).coords[0]); angle=-35.; delta=angle-old['axis_deg']; theta=math.radians(delta)
    def transform(p):
        x,y=p[0]-old['root_m'][0],p[1]-old['root_m'][1]
        return [round(root[0]+x*math.cos(theta)-y*math.sin(theta),3),round(root[1]+x*math.sin(theta)+y*math.cos(theta),3)]
    def visit(o,key=''):
        if isinstance(o,dict): return {k:visit(v,k) for k,v in o.items()}
        if isinstance(o,list):
            if key in ['root_m','center_m','light_m'] and len(o)==2: return transform(o)
            if key in ['polygon_m','axis_m','walk_axis_m']: return [transform(p) for p in o]
            return [visit(v,key) for v in o]
        return o
    d['marina']=visit(old)
    d['marina'].update(axis_deg=angle,change_region=r,access_ru='Бусик: дорога из города → ELITE_BEACH_ACCESS → MARINA_QUAY; далее пешком.',
                       transplant=dict(source='MAP_PLAN_R01_v14.json#marina',rotation_deg=round(delta,4),scale=1.0))
    for b in d['marina']['boats']: b['heading_deg']=round(b['heading_deg']+delta,3)
    quay=next(s for s in OLD['functional_sites'] if s['id']==old['quay_site_id'])
    put(d,'functional_sites',dict(id=quay['id'],type='quay',polygon_m=[transform(p) for p in quay['polygon_m']],
        district_id='elite',point_id='ELITE_MARINA',label_ru='Причал элитки'),r)
    oldroad=next(q for q in OLD['roads'] if q['id']==old['quay_road_id'])
    tip=transform(oldroad['polyline_m'][-1]); tip_px=px(tip)
    road(d,'MARINA_QUAY',[(966,510),tip_px],r,'rural_road')
    point(d,'ELITE_MARINA',tip_px,r,cat='water_access',source='v14 marina rigid transplant',confidence='explicit_addition')
    road(d,'MARINA_WALK',[px(p) for p in d['marina']['walk_axis_m']],r,'passage',walk=True)


def build_valley(d):
    r='08_valley'
    building(d,'F07_VILLA',rect(498,489,45,23),r,source_key='08: blue building / base badge')
    building(d,'F12_CASINO',rect(444,593,47,21),r,source_key='08: southern large building (type proposed)')
    road(d,'VALLEY_MAIN',smooth([(420,450),(421,490),(434,524),(465,566),(479,591),(474,607),(455,629),(455,645)],2),r,'rural_road')
    road(d,'VALLEY_VILLA',smooth([(421,479),(444,469),(471,471),(498,471)],1),r,'rural_road')
    road(d,'VALLEY_POND_EAST',smooth([(498,471),(536,473),(550,512),(549,548),(540,582),(522,604),(478,612)],2),r,'rural_road')
    water(d,'VALLEY_POND','lake',smooth([(481,511),(492,513),(501,529),(509,544),(520,551),(515,565),
       (503,568),(492,558),(493,543),(482,528),(478,518)],2,True),r,'Пруд в долине')
    point(d,'P13-2',(480,537),r,source='08: pond edge')
    point(d,'BEACH_VALLEY_ENTRY',(455,640),r,source='08: small beach road',confidence='readable')
    sand=[(438,630),(462,629),(474,643),(483,657),(469,656),(454,653),(443,657),(435,658)]
    put(d,'beaches',dict(id='BEACH_VALLEY',name_ru='Малый пляж',polygon_m=poly(sand),land_edge_m=mm(sand[:3]),
        sea_edge_m=mm(sand[3:]),width_m=18,surface='sand',access_road_ids=['VALLEY_MAIN'],closed_ends_ru='Скалы'),r)


def build_beach(d):
    r='09_beach'
    for oid,c,w,h in [('F13_PARK_KIOSK',(521,483),104,62),('F13_PARK_WC',(789,516),125,67)]:
        building(d,oid,[beach_px(p) for p in rect(*c,w,h)],r,
                 label='Кофейный киоск' if 'KIOSK' in oid else 'Туалет / душ',source_key='09: left kiosk / right WC',confidence='detail_sheet')
    site(d,'BEACH_PARKING','parking',[beach_px(p) for p in rect(645,373,277,92)],r,'Пляжная парковка',capacity_vans=8)
    # Three canal bridges. Centre is the van route to parking and service stops; sides are pedestrian.
    for oid,srcx,masterx in [('BEACH_BRIDGE_W',220,576),('BEACH_BRIDGE_C',647,673),('BEACH_BRIDGE_E',1090,761)]:
        road(d,oid,[(masterx,452),(masterx,486),(masterx,503)],r,'rural_road' if srcx==647 else 'passage',walk=srcx!=647)
    road(d,'BEACH_PARK_AISLE',[(643,514),(673,514),(698,514)],r,'rural_road')
    road(d,'BEACH_SERVICE',[(673,503),(673,514),(673,547),(673,573)],r,'rural_road')
    point(d,'BEACH_PARK_ENTRY',(673,503),r,source='09: centre bridge -> parking',confidence='detail_sheet')
    for oid,pts in [('BEACH_WALK_W',[(220,320),(209,474),(382,572),(523,542),(647,565)]),
                    ('BEACH_WALK_E',[(1090,320),(1090,474),(923,562),(788,570),(647,565)]),
                    ('BEACH_PROMENADE',[(647,565),(647,723)])]:
        road(d,oid,[beach_px(p) for p in smooth(pts,2)],r,'passage',walk=True)
    site(d,'CITY_PIER','pier',[beach_px(p) for p in [(623,722),(665,722),(665,1020),(698,1020),(698,1077),(585,1077),(585,1020),(623,1020)]],r,'Деревянный Т-пирс',surface='wood')
    site(d,'BEACH_DETAIL_SHORE','shore_reference',[beach_px(p) for p in BEACH_SHORE_SRC+[(1254,320),(0,320)]],r,'Контур песка по детальному листу',dressing_only=True)
    beachpoly=next(q['polygon_m'] for q in d['districts'] if q['id']=='beach_parking')
    put(d,'beaches',dict(id='BEACH',name_ru='Городской пляж',polygon_m=beachpoly,land_edge_m=mm([(548,493),(797,493)]),
        sea_edge_m=mm(coast_section(CITY_SHORE_MASTER[0],CITY_SHORE_MASTER[-1])),width_m=105,surface='sand',access_road_ids=['BEACH_BRIDGE_C'],
        foot_access_path_ids=['BEACH_BRIDGE_W','BEACH_BRIDGE_E'],closed_ends_ru='Скалы и устье',bay_id='BAY15'),r)
    items=[(185,525),(142,606),(220,618),(290,558),(393,603),(425,690),
           (792,632),(830,691),(907,626),(1029,546),(1090,613),(1140,577)]
    for i,(x,y) in enumerate(items,1):
        site(d,f'BEACH_UMBRELLA_{i:02}','umbrella',[beach_px(p) for p in oval(x,y,20,20,16)],r,'Зонт')
        for j,dx in enumerate([-29,29],1):
            site(d,f'BEACH_LOUNGER_{i:02}_{j}','lounger',[beach_px(p) for p in rect(x+dx,y+30,13,29)],r,'Шезлонг')
    site(d,'BEACH_LIFEGUARD','lifeguard_tower',[beach_px(p) for p in rect(505,650,39,51)],r,'Спасательная вышка')
    for i,p in enumerate([(590,643),(694,645)],1):
        put(d,'functional_sites',dict(id=f'BEACH_FLAG_{i}',type='flag',district_id='beach_parking',position_m=m(beach_px(p)),label_ru='Флаг'),r)
    for i,p in enumerate([(89,554),(126,383),(167,309),(258,308),(395,343),(483,382),(612,419),(887,384),
                          (1006,326),(1148,437),(1176,316),(1035,406),(443,552)],1):
        put(d,'functional_sites',dict(id=f'BEACH_PALM_{i:02}',type='palm',district_id='beach_parking',position_m=m(beach_px(p)),label_ru='Пальма'),r)
    for i,p in enumerate([(41,655),(89,861),(136,843),(1234,719),(1135,888),(1167,915)],1):
        site(d,f'BEACH_ROCK_{i}','rock',[beach_px(q) for q in oval(*p,12,8,12)],r,'Камень')
    d['detail_registration']['beach']=dict(source='REF_FEDYA_MASTER_v02_city_beach.png',method='piecewise monotone landmark warp',
        source_x_px=[0,220,647,1090,1254],master_x_px=[540,576,673,761,801],source_y_px=[0,246,500,840,1075,1254],
        master_y_px=[427,485,544,608,650,684],note_ru='Три моста, киоск слева, душ справа, пирс — опоры привязки. Центральный мост: предложен служебный проезд бусика.')


def physical(d):
    return [(b,Polygon(b.get('footprint_m',b.get('polygon_m')))) for k in ['functional_buildings','building_masses'] for b in d[k]]


def connect_access(d):
    """Connect real exterior van stops, not graph-only teleports to building centres.

    Candidate drives are checked at their full 3.8 m width against all buildings and dry-land water.
    Shared streets are fixed; local drives belong only to the consumer's named district.
    """
    main=list(d['roads']); network=unary_union([LineString(r['polyline_m']) for r in main])
    blocks=physical(d)
    wet=unary_union([Polygon(w['polygon_m']) for w in d['water'] if w['kind'] not in ['sea']])
    sea=Polygon(next(w['polygon_m'] for w in d['water'] if w['id']=='SEA'))
    land=Polygon(d['boundary']['polygon_m'])
    obstacles=unary_union([g for _,g in blocks]+[wet,sea])
    def candidates(target,shape=None):
        found=[]
        for rr in main:
            ln=LineString(rr['polyline_m'])
            proj=ln.project(target)
            for dist in [proj, max(0,proj-12), min(ln.length,proj+12)]:
                hit=ln.interpolate(dist)
                if hit.distance(target)>105: continue
                if shape is None: stop=target; door=target
                else:
                    door=nearest_points(shape.boundary,hit)[0]
                    vx,vy=hit.x-door.x,hit.y-door.y
                    length=math.hypot(vx,vy)
                    if length<2.5: continue
                    stop=Point(door.x+vx/length*2.7,door.y+vy/length*2.7)
                drive=LineString([hit,stop])
                corridor=drive.buffer(1.91,cap_style=2)
                if corridor.intersection(obstacles).area>.002 or not land.buffer(.01).covers(corridor): continue
                if not land.covers(stop): continue
                found.append((drive.length,rr['id'],hit,stop,door))
        return sorted(found,key=lambda q:(q[0],q[1]))
    for b,g in blocks:
        options=candidates(g.centroid,g)
        if not options:
            d.setdefault('access_failures',[]).append(b['id']); continue
        length,parent,hit,stop,door=options[0]
        oid='ACCESS_'+b['id']; region=b['change_region']
        q=road(d,oid,[px(hit.coords[0]),px(stop.coords[0])],region,'alley' if region in ['04_rough','05_downtown','06_port'] else 'rural_road',width=3.8)
        q.update(access_only=True,parent_road_id=parent)
        b.update(entrance_m=[round(v,3) for v in door.coords[0]],van_stop_m=[round(v,3) for v in stop.coords[0]],access_road_id=oid)
        if b.get('poi_id') and b['poi_id'] not in {p['id'] for p in d['points']}:
            p=point(d,b['poi_id'],px(door.coords[0]),region,source=b.get('source_master_key') or b['id'],confidence=b.get('mapping_confidence','proposed'))
            p['building_id']=b['id']
            p['van_stop_m']=b['van_stop_m']; p['access_road_id']=oid
    for p in d['points']:
        if p.get('van_stop_m'): continue
        # Marina stop is already a street endpoint.
        target=Point(p['position_m']); options=candidates(target)
        if not options:
            d.setdefault('access_failures',[]).append(p['id']); continue
        length,parent,hit,stop,door=options[0]
        p['van_stop_m']=p['position_m'][:]
        if length<.05: p['access_road_id']=parent; continue
        oid='ACCESS_POINT_'+p['id']
        road(d,oid,[px(hit.coords[0]),px(stop.coords[0])],p['change_region'],'alley' if p['change_region'] in ['04_rough','05_downtown','06_port'] else 'rural_road',width=3.8).update(access_only=True,parent_road_id=parent)
        p['access_road_id']=oid


def fences(d):
    cutters=unary_union([LineString(r['polyline_m']).buffer(r['width_m']/2+1.5) for r in d['roads']+d['paths']])
    for key,oid,region,material,height in [('elite_perimeter_px','ELITE_PERIMETER','07_elite','elite_fence',2.4),
                                          ('port_perimeter_px','PORT_PERIMETER','06_port','port_wall',3.0)]:
        pts=d.pop(key)
        if pts[0]!=pts[-1]: pts=pts+[pts[0]]
        axis=LineString(mm(pts)); pieces=axis.difference(cutters)
        parts=list(pieces.geoms) if hasattr(pieces,'geoms') else [pieces]
        gates=[r['id'] for r in d['roads']+d['paths'] if axis.intersects(LineString(r['polyline_m']))]
        for i,p in enumerate(parts,1):
            if p.length<1: continue
            put(d,'vegetation_parcels',dict(id=f'{oid}_{i:02}',kind='interdistrict_barrier',material=material,
               district_id=DISTRICT_OF[region],axis_m=[list(q) for q in p.coords],polygon_m=ring(p.buffer(.4,cap_style=2)),
               height_target_m=height,blocks_van=True,blocks_foot=True,gate_road_ids=gates,barrier_role='property_fence'),region)


def graph(d,walk=False):
    ways=d['roads']+(d['paths'] if walk else [])
    lines=[LineString(r['polyline_m']) for r in ways]
    # Unary union nodes all actual intersections. Coordinates are snapped only at 1 mm.
    noded=unary_union(lines)
    parts=list(noded.geoms) if hasattr(noded,'geoms') else [noded]
    nodes={}; edges=[]
    for line in parts:
        owner=min((r for r,l in zip(ways,lines) if l.distance(line.interpolate(.5,normalized=True))<.002),key=lambda r:r['id'])
        coords=list(line.coords)
        # Stops already on a street still need an actual graph vertex (not nearest-node approximation).
        refined=[]
        for a,b in zip(coords,coords[1:]):
            seg=LineString([a,b]); along=[(0,a)]
            for p in d['points']:
                stop=Point(p.get('van_stop_m',p['position_m']))
                if seg.distance(stop)<.002:
                    t=seg.project(stop)
                    if .001<t<seg.length-.001: along.append((t,seg.interpolate(t).coords[0]))
            refined.extend(q for _,q in sorted(along))
        coords=refined+[coords[-1]]
        for aa,bb in zip(coords,coords[1:]):
            a=tuple(round(v,3) for v in aa); b=tuple(round(v,3) for v in bb)
            if a==b: continue
            for p in [a,b]: nodes.setdefault(p,'N'+digest(p)[:12])
            sub=LineString([a,b]); bridge=False
            for w in d['water']:
                if w['kind'] in ['river','concrete_canal'] and sub.intersects(Polygon(w['polygon_m'])): bridge=True
            eid='E'+digest([owner['id'],sorted([a,b])])[:14]
            edges.append(dict(id=eid,from_node=nodes[a],to_node=nodes[b],road_id=owner['id'],**{'class':owner['class']},
                width_m=owner['width_m'],length_m=round(math.dist(a,b),3),polyline_m=[list(a),list(b)],
                bridge=bridge,tunnel=False,bidirectional=True,walkable=True,van_access=owner.get('van_access',True)))
    result=dict(nodes=sorted([dict(id=v,position_m=list(k)) for k,v in nodes.items()],key=lambda n:n['id']),
                edges=sorted(edges,key=lambda e:e['id']),intersection_rule='All geometric intersections noded; stable coordinate hashes; bidirectional.')
    if not walk:
        for p in d['points']:
            stop=p.get('van_stop_m',p['position_m'])
            q=min(result['nodes'],key=lambda n:math.dist(stop,n['position_m']))
            p['road_node_id']=q['id']; p['van_node_gap_m']=round(math.dist(stop,q['position_m']),4)
    return result


def finalize(d):
    connect_access(d)
    snap_connections(d)
    fences(d)
    d['road_graph']=graph(d)
    d['pedestrian_graph']=graph(d,True)
    d['pedestrian_water_crossings']=[]
    for r in d['roads']+d['paths']:
        line=LineString(r['polyline_m'])
        for w in d['water']:
            if w['kind'] not in ['river','concrete_canal']: continue
            overlap=line.intersection(Polygon(w['polygon_m']))
            if overlap.is_empty: continue
            parts=list(overlap.geoms) if hasattr(overlap,'geoms') else [overlap]
            for i,part in enumerate(parts):
                if not isinstance(part,LineString) or part.length<.1: continue
                put(d,'water_crossings' if r.get('van_access',True) else 'pedestrian_water_crossings',dict(id='BR_'+r['id']+'_'+w['id']+'_'+str(i),road_id=r['id'],water_id=w['id'],
                    position_m=list(part.centroid.coords[0]),deck_axis_m=[list(part.coords[0]),list(part.coords[-1])],kind='bridge',
                    tunnel_carrier=None,width_m=r['width_m'],source_status='traced' if 'BRIDGE' in r['id'] or r['id'] in ['HAMLET_CROSSING','CROSS_SPINE'] else 'proposed'),r['change_region'])
    counts=Counter(b['district_id'] for b,g in physical(d))
    area=Polygon(d['boundary']['polygon_m']).area
    for q in d['districts']:
        q['building_count']=counts[q['id']]; q['share_percent']=round(q['area_m2']/area*100,2)
    bounds=Polygon(d['boundary']['polygon_m']).bounds
    d['metrics']=dict(area_m2=round(area,3),bounds_m=list(bounds),extent_m=[round(bounds[2]-bounds[0],3),round(bounds[3]-bounds[1],3)],
        building_count=sum(counts.values()),building_counts_by_district=dict(counts),routes=[],
        common_landscape_area_m2=round(area-sum(q['area_m2'] for q in d['districts']),3),
        timing_assumption='Geometric 2D access only. No driving/physics/playtest claim.')
    # Legacy Look exports only beaches[0]; keep the City Beach as the primary beach.
    d['beaches'].sort(key=lambda b:(b['id']!='BEACH',b['id']))
    d['functional_statistics']=dict(building_count=len(d['functional_buildings']),district_counts=dict(Counter(b['district_id'] for b in d['functional_buildings'])),
        type_counts=dict(Counter(b['type'] for b in d['functional_buildings'])))
    d['passage_statistics']=dict(count=len(d['paths']),total_length_m=round(sum(p['length_m'] for p in d['paths']),3),
        by_class=dict(Counter(p['class'] for p in d['paths'])),policy='Пешие дорожки; центральный мост пляжа — проезд.')
    d['old_town_statistics']=dict(tower_ids=['O14_TOWER_W','O14_TOWER_E'],tower_floors=20,
        building_count=counts['old_town'],policy='Детальный лист Downtown; 20 этажей башен — предложение v14, жилые 3–6 по листу.')
    d['hamlet_statistics']=dict(building_count=counts['village'],crop_field_count=len(d['crop_fields']),church_in_village=True)
    d['residential_statistics']=dict(panel_house_count=len([b for b in d['building_masses'] if b['district_id']=='residential']),
        policy='U/L панели по контуру мастера; этажность до уточнения района.')
    d['bay']=dict(id='BAY15',name_ru='Бухта',apex_m=m((808,610)),mouth_m=mm([(574,613),(1012,503)]),
        sea_edge_m=mm(coast_section((979,514),CITY_SHORE_MASTER[0])),beach_id='BEACH',rocks=[],walk_path_id='BEACH_PROMENADE',car_park_path_ids=['BEACH_BRIDGE_C'])
    d['sightline']=dict(from_point='B01',to_point='CHIMNEY',chimney_height_target_m=85,status='Не проверено в 3D; высокий объект в порту требует подтверждения Феди.')
    d['planning_notes_ru']=['Оцифровка для согласования 2D, не утверждённая игровая геометрия.',
         'Все подписи с низкой уверенностью явно отмечены в mapping_confidence и отчёте.',
         'Масштаб рамки не уменьшен до старого ограничения 1000 м.',
         'Автоматические подъезды — предлагаемые локальные соединения, проверенные в плане с полной шириной.',
         'Вода и двор могут содержать функциональные площадки; запрет перекрытий относится к физическим зданиям, проездам и преградам.']
    d['gameplay_mapping']=[]
    byid={p['id']:p for p in d['points']}
    for old in OLD['points']:
        p=byid.get(old['id'])
        d['gameplay_mapping'].append(dict(id=old['id'],name_ru=old['name_ru'],status=p.get('mapping_confidence','proposed') if p else 'unmapped',
            master_key=p.get('source_master_key','') if p else '',position_m=p['position_m'] if p else None,
            question_ru='' if p else 'Где этот объект на мастере? Координаты v14 не перенесены.'))
    for oid in ['P16','P16-2']:
        next(q for q in d['gameplay_mapping'] if q['id']==oid)['question_ru']='На мастере нет выездных постов. Нужны места и направления выезда.'
    functions={b['id']:b for b in d['functional_buildings']}
    d['building_mapping']=[dict(id=b['id'],type_v14=b['type'],status='reused' if b['id'] in functions else 'unmapped',
        master_key=functions.get(b['id'],{}).get('source_master_key',''),
        note_ru='Торговая функция сохранена под ID F06_SUPER; на детальном листе подписана «Бутики».' if b['id']=='F06_SUPER' else
                'Отдельного банка на листе нет, P11 относится к ATM. Где разместить прежний банк?' if b['id']=='F06_BANK' else '')
        for b in OLD['functional_buildings']]
    keys={5:['F15_OFFICE_1'],6:['F15_OFFICE_2'],7:['F06_REPAIR'],10:['F06_POLICE','O14_TOWER_W'],11:['F15_POLICE_2'],12:['F15_TAXI'],13:['F06_HBASE']}
    d['downtown_object_keys']=[dict(key=f'{i:02}',object_ids=keys.get(i,[]),status='ambiguous_duplicate' if i==10 else 'readable' if i in keys else 'unreadable_or_absent') for i in range(1,16)]
    d['comparison']=dict(v14=dict(building_count=OLD['metrics']['building_count']),policy='Полная новая мастер-раскладка; v14 сохранён как источник типов и ID.')
    d['region_fingerprints']=region_fingerprints(d)


def snap_connections(d):
    """Explicit common vertices at driveway joins; no reliance on floating point near-intersections.

    Only road ENDPOINTS may snap, at most 2 m. A join is inserted into the carrier's polyline.
    Existing fixed internal vertices stay in place. All edits are logged.
    """
    ways=d['roads']+d['paths']; changes=[]
    for r in ways:
        for end in [0,-1]:
            a=Point(r['polyline_m'][end]); choices=[]
            for carrier in ways:
                if carrier is r: continue
                if r.get('van_access',True) and not carrier.get('van_access',True): continue
                line=LineString(carrier['polyline_m']); dist=line.distance(a)
                limit=.002 if r['id'].startswith('ACCESS_') else 2.0
                if dist<=limit:
                    q=line.interpolate(line.project(a))
                    # Prefer an existing vertex if it is within 1 mm.
                    near=min(carrier['polyline_m'],key=lambda p:Point(p).distance(q))
                    pos=list(near) if Point(near).distance(q)<.002 else list(q.coords[0])
                    choices.append((dist,carrier['id'],carrier,pos))
            if not choices: continue
            dist,_,carrier,pos=min(choices,key=lambda x:(round(x[0],6),x[1]))
            pts=carrier['polyline_m']
            if pos not in pts:
                idx=min(range(len(pts)-1),key=lambda i:LineString(pts[i:i+2]).distance(Point(pos)))
                pts.insert(idx+1,pos)
            if dist>.002: changes.append(dict(road_id=r['id'],carrier_id=carrier['id'],distance_m=round(dist,4)))
            r['polyline_m'][end]=pos
    for r in ways: r['length_m']=round(LineString(r['polyline_m']).length,3)
    d['geometry_repairs']=changes


def region_records(d,rid):
    records={k:sorted([v for v in d.get(k,[]) if v.get('change_region')==rid],key=lambda x:x['id']) for k in LAYERS+['water_crossings','pedestrian_water_crossings']}
    for key in ['marina','railway']:
        if d.get(key,{}).get('change_region')==rid: records[key]=d[key]
    return records


def region_fingerprints(d):
    return {r['id']:digest(region_records(d,r['id'])) for r in d['change_regions']}


def build():
    d=seed()
    for fn in [build_world,build_forest,build_hamlet,build_crossing,build_rough,build_downtown,build_port,build_elite,build_valley,build_beach]: fn(d)
    finalize(d)
    return d


def validate(d,baseline=None,allowed=()):
    checks=[]
    def check(name,ok,detail=''):
        checks.append(dict(name=name,passed=bool(ok),detail=detail))
    allpolys=[]
    def visit(x,path=''):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in ['polygon_m','footprint_m','yard_polygon_m'] and v:
                    allpolys.append((path+'/'+k,Polygon(v)))
                elif isinstance(v,(dict,list)): visit(v,path+'/'+str(x.get('id',k)))
        elif isinstance(x,list):
            for v in x: visit(v,path)
    # Only source records: diagnostics/mappings must not double-count geometry.
    for k in LAYERS+['boundary','marina','railway']: visit(d[k],k)
    invalid=[name for name,g in allpolys if not g.is_valid or g.is_empty or g.area<=.001]
    check('Полигональная геометрия корректна',not invalid,f'{len(allpolys)-len(invalid)}/{len(allpolys)}; invalid={invalid}')
    check('Все полилинии простые и конечные',all(LineString(r['polyline_m']).is_simple for r in d['roads']+d['paths']),f"{len(d['roads'])+len(d['paths'])} осей")
    blocks=physical(d)
    collisions=[(a['id'],b['id'],round(g.intersection(h).area,3)) for i,(a,g) in enumerate(blocks) for b,h in blocks[i+1:] if g.intersection(h).area>.01]
    check('Здания не перекрываются',not collisions,str(collisions))
    roadareas={r['id']:LineString(r['polyline_m']).buffer(r['width_m']/2,cap_style=1) for r in d['roads']}
    road_hits=[(b['id'],rid,round(g.intersection(p).area,3)) for b,g in blocks for rid,p in roadareas.items() if g.intersection(p).area>.01]
    check('Полная ширина проездов свободна от зданий',not road_hits,str(road_hits))
    district_hits=[(a['id'],b['id']) for i,a in enumerate(d['districts']) for b in d['districts'][i+1:] if Polygon(a['polygon_m']).intersection(Polygon(b['polygon_m'])).area>.01]
    check('Районы не перекрываются',not district_hits,str(district_hits))
    land=Polygon(d['boundary']['polygon_m']); sea=Polygon(next(w['polygon_m'] for w in d['water'] if w['id']=='SEA'))
    check('Море не перекрывает сушу',land.intersection(sea).area<.01,f'{land.intersection(sea).area:.6f} м²')
    check('Берег совпадает у суши и моря',all(sea.boundary.distance(Point(p))<.005 for edge in d['boundary']['coast_segments_m'] for p in edge),f"{len(COAST)-1} общих сегментов")
    wet=unary_union([Polygon(w['polygon_m']) for w in d['water']])
    check('Здания стоят на сухой суше',all(g.intersection(wet).area<.01 and land.covers(g) for b,g in blocks),
          str([b['id'] for b,g in blocks if g.intersection(wet).area>=.01 or not land.covers(g)]))
    decks=unary_union([Polygon(s['polygon_m']) for s in d['functional_sites'] if s['type'] in ['quay','pier']])
    unsupported=sea.difference(decks)
    check('Проезды не уходят в море без настила',all(p.intersection(unsupported).area<.01 for p in roadareas.values()),str([rid for rid,p in roadareas.items() if p.intersection(unsupported).area>.01]))
    adj=defaultdict(list)
    for e in d['road_graph']['edges']:
        adj[e['from_node']].append((e['to_node'],e)); adj[e['to_node']].append((e['from_node'],e))
    unseen=set(adj); components=[]
    while unseen:
        root=min(unseen); found={root}; todo=[root]
        while todo:
            a=todo.pop()
            for b,e in adj[a]:
                if b not in found: found.add(b); todo.append(b)
        unseen-=found; components.append(found)
    check('Дорожный граф связен',len(components)==1,f'{len(components)} компонент; {len(adj)} узлов / {len(d["road_graph"]["edges"])} рёбер')
    bad_access=d.get('access_failures',[])
    check('Проверенные подъезды ко всем зданиям',not bad_access,str(bad_access))
    root=next(p for p in d['points'] if p['id']=='B01')['road_node_id']
    costs={root:0}; via={}; todo=[(0,root)]
    while todo:
        dist,a=heapq.heappop(todo)
        if dist!=costs[a]: continue
        for b,e in adj[a]:
            nd=dist+e['length_m']
            if nd<costs.get(b,float('inf')): costs[b]=nd; via[b]=(a,e); heapq.heappush(todo,(nd,b))
    reached=[]
    for p in d['points']:
        good=p['road_node_id'] in costs and p['van_node_gap_m']<.01 and p['id'] not in bad_access
        if good:
            reached.append(p['id']); cur=p['road_node_id']; edges=[]
            while cur!=root:
                prev,e=via[cur]; edges.append(e); cur=prev
            edges.reverse()
            d['metrics']['routes'].append(dict(from_id='B01',to_id=p['id'],length_m=round(costs[p['road_node_id']],2),
                edge_ids=[e['id'] for e in edges],road_ids=list(dict.fromkeys(e['road_id'] for e in edges))))
    check('Бусик достигает всех размещённых игровых точек',len(reached)==len(d['points']),
          f'{len(reached)}/{len(d["points"])}; missing='+str([p['id'] for p in d['points'] if p['id'] not in reached]))
    check('У каждой базы B01–B06 есть подъезд',all(f'B{i:02}' in reached for i in range(1,7)),str([f'B{i:02}' for i in range(1,7) if f'B{i:02}' not in reached]))
    check('Дороги максимум двухполосные',all(r['lanes']<=2 and r['width_m']<=7 for r in d['roads']),f'{len(d["roads"])} дорог')
    fences=[v for v in d['vegetation_parcels'] if v['kind']=='interdistrict_barrier']
    check('Нет разделительных оград районов',all(f['barrier_role']=='property_fence' and f['material'] in ['elite_fence','port_wall'] for f in fences),
          f'{len(fences)} отрезков только элитного/портового периметра; горы — естественный край')
    hits=[(f['id'],rid) for f in fences for rid,g in roadareas.items() if Polygon(f['polygon_m']).intersection(g).area>.01]
    check('В периметрах открыты ворота на проездах',not hits,str(hits))
    marina=d['marina']
    check('Марина доступна бусику до причала','ELITE_MARINA' in reached,'ELITE_BEACH_ACCESS → MARINA_QUAY')
    check('Марина: 3 понтона / 10 мест / 3 яхты / 4 катера',len(marina['fingers'])==3 and len(marina['berths'])==10 and Counter(b['kind'] for b in marina['boats'])=={'yacht':3,'motorboat':4},str(Counter(b['kind'] for b in marina['boats'])))
    check('Марина сохранена без масштабирования',all(abs(Polygon(a['polygon_m']).area-Polygon(b['polygon_m']).area)<.03 for a,b in zip(OLD['marina']['boats'],marina['boats'])),f"rigid rotation {marina['transplant']['rotation_deg']}°; scale 1")
    check('Причалы и суда марины в море',all(sea.buffer(2).covers(Polygon(b['polygon_m'])) for b in marina['boats']+marina['fingers']+[marina['t_head']]),'Допуск 2 м только у основания')
    fs={b['id']:b for b in d['functional_buildings']}; sites={s['id']:s for s in d['functional_sites']}
    mass={b['id']:b for b in d['building_masses']}
    required_dt=['F06_POLICE','F15_POLICE_2','F06_CAFE2','F06_SUPER','F15_BOOKS','F15_RESTAURANT','F06_HBASE','F06_REPAIR','F15_OFFICE_1','F15_OFFICE_2','F15_TAXI']
    check('Downtown: все 11 заданных функций',all(x in fs for x in required_dt),str(required_dt))
    check('Downtown: башни, обе парковки, площадь и фонтан',all(x in mass for x in ['O14_TOWER_W','O14_TOWER_E']) and all(x in sites for x in ['DT_PARKING_W','DT_PARKING_E','SQUARE14','FOUNTAIN14']),'6/6')
    check('Downtown: 2 ATM, жильё 3–6 этажей, дворы и сквер',all(x in reached for x in ['P11','P11-DT2']) and {b['floors'] for b in mass.values() if b['id'].startswith('O15_RES')}=={3,4,5,6} and all(x in sites for x in ['DT_COURT_W','DT_COURT_S','DT_PARK_E']),'2 ATM / 6 жилых домов / 3 зелёных площадки')
    check('Downtown: фонари — якоря хвата',len([q for q in d['functional_sites'] if q.get('grip_anchor')])==17,'17/17')
    check('Rough: футбольное поле, южнее магазин 24 часа','ROUGH_FOOTBALL' in sites and fs['F06_24']['center_m'][1]<Polygon(sites['ROUGH_FOOTBALL']['polygon_m']).centroid.y,'2/2')
    check('Beach: киоск слева, душ справа',fs['F13_PARK_KIOSK']['center_m'][0]<m((673,0))[0]<fs['F13_PARK_WC']['center_m'][0],'2/2')
    bridgeids={q['road_id'] for q in d['water_crossings']+d['pedestrian_water_crossings'] if q['water_id']=='CANAL'}
    check('Beach: ровно 3 моста через канал',{'BEACH_BRIDGE_W','BEACH_BRIDGE_C','BEACH_BRIDGE_E'}<=bridgeids and len([b for b in bridgeids if b.startswith('BEACH_BRIDGE')])==3,str(sorted(bridgeids)))
    check('Beach: парковка, 12 зонтов, 24 шезлонга, вышка, флаги, пальмы, камни, Т-пирс',
          'BEACH_PARKING' in sites and 'CITY_PIER' in sites and 'BEACH_LIFEGUARD' in sites and
          sum(s['type']=='umbrella' for s in sites.values())==12 and sum(s['type']=='lounger' for s in sites.values())==24 and
          sum(s['type']=='flag' for s in sites.values())==2 and sum(s['type']=='palm' for s in sites.values())==13 and sum(s['type']=='rock' for s in sites.values())==6,
          'парковка 1; зонты 12; шезлонги 24; вышка 1; флаги 2; пальмы 13; камни 6; пирс 1')
    check('Схема v14: все верхние ключи и типы сохранены',all(k in d and type(d[k])==type(v) for k,v in OLD.items()),f'{len(OLD)}/{len(OLD)} ключей; новые поля только добавлены')
    for k in LAYERS+['water_crossings','pedestrian_water_crossings']:
        check(f'Уникальные ID: {k}',len({q['id'] for q in d[k]})==len(d[k]),str(len(d[k])))
    checks.extend(fit_checks(d))
    if baseline:
        old=json.loads(Path(baseline).read_text(encoding='utf-8'))
        changed=[k for k,v in region_fingerprints(d).items() if old.get('region_fingerprints',{}).get(k)!=v and k not in allowed]
        check('Локальная правка не затронула другие районы',not changed,str(changed))
    d['validation']=dict(passed=all(c['passed'] for c in checks),checks=checks,
        scope='Геометрия 2D; непривязанные канонические точки перечислены отдельно; не проверка Unity/вождения/субъективной приёмки.')
    return d['validation']


def fit_checks(d):
    # Twelve direct-trace centre checks plus eleven detail-sheet registration checks.
    # Direct trace checks verify conversion, not independent reconstruction accuracy.
    observations=[('F06_WAGON',(154,529)),('F06_GRANDPA',(151,282)),('F06_CHURCH',(150,241)),('F06_WATER',(304,294)),
      ('F06_BUYER',(506,250)),('F06_GAS',(451,331)),('F06_24',(755,261)),('F06_DEPOT',(960,104)),
      ('F06_WARE1',(1038,99)),('F06_MANSION_2',(1008,344)),('F07_VILLA',(498,489)),('F12_CASINO',(444,593)),
      ('F06_POLICE',(566,329)),('O14_TOWER_W',(643,330)),('O14_TOWER_E',(695,330)),('F06_HBASE',(571,427)),
      ('F06_REPAIR',(627,430)),('F15_OFFICE_1',(652,430)),('F15_OFFICE_2',(714,431)),('F15_TAXI',(755,426)),
      ('F15_POLICE_2',(789,430)),('F13_PARK_KIOSK',(651,542)),('F13_PARK_WC',(701,545))]
    bs={b['id']:b for b,g in physical(d)}; rows=[]
    for oid,p in observations:
        err=math.dist(bs[oid]['center_m'],m(p))
        rows.append(dict(id=oid,master_observed_px=list(p),plan_center_m=bs[oid]['center_m'],residual_m=round(err,3),
                         role='detail_registration_check' if len(rows)>=12 else 'direct_trace_control'))
    d['fit_evidence']=dict(method='23 вручную прочитанных центров в master; ориентировочные центры, не геодезическая точность.',
       observations=rows,median_m=round(float(np.median([r['residual_m'] for r in rows])),3),max_m=max(r['residual_m'] for r in rows),
       caveat_ru='12 прямых опор трассировки проверяют преобразование, 11 центров — привязку деталей. Оценка ±2–4 м; не доказывает точность каждого контура. Детали без масштаба. Нечитаемые объекты, локальные подъезды и замена берега Beach в выборку не входят.')
    return [dict(name='Читаемые ориентиры: отклонение не более ~8 м',passed=all(r['residual_m']<=8 for r in rows),
                 detail=f"{sum(r['residual_m']<=8 for r in rows)}/{len(rows)}; median={d['fit_evidence']['median_m']} м; max={d['fit_evidence']['max_m']} м")]


class Canvas:
    """The SVG and PNG use exactly the same world coordinates and drawing commands."""
    def __init__(self,bounds,scale=3,header=70,footer=100):
        self.bounds=bounds; self.scale=scale; self.header=header
        self.w=round((bounds[2]-bounds[0])*scale); self.h=round((bounds[3]-bounds[1])*scale)+header+footer
        self.im=Image.new('RGB',(self.w,self.h),'#f8f5ed'); self.draw=ImageDraw.Draw(self.im)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">',
                  '<rect width="100%" height="100%" fill="#f8f5ed"/>']
        self.fonts={}
        self.label_boxes=[]
    def xy(self,p):
        u,v=px(p); return ((u-self.bounds[0])*self.scale,(v-self.bounds[1])*self.scale+self.header)
    def pts(self,pts): return [self.xy(p) for p in pts]
    def visible(self,p):
        x,y=self.xy(p); return 0<=x<=self.w and self.header<=y<self.h-5
    def polygon(self,pts,fill,stroke=None,width=.5):
        q=self.pts(pts); sw=max(1,round(width*self.scale))
        self.draw.polygon(q,fill=fill)
        if stroke: self.draw.line(q+[q[0]],fill=stroke,width=sw,joint='curve')
        self.svg.append(f'<polygon points="'+ ' '.join(f'{x:.2f},{y:.2f}' for x,y in q)+f'" fill="{fill}" stroke="{stroke or "none"}" stroke-width="{width*self.scale:.2f}"/>')
    def line(self,pts,color,width=1,dash=None):
        q=self.pts(pts); sw=max(1,round(width*self.scale))
        if dash:
            # Pillow dashed segments; SVG equivalent dash pattern.
            line=LineString(q); dashpx=dash*self.scale
            for start in np.arange(0,line.length,dashpx*2):
                a=line.interpolate(start); b=line.interpolate(min(line.length,start+dashpx)); self.draw.line([a.coords[0],b.coords[0]],fill=color,width=sw)
        else: self.draw.line(q,fill=color,width=sw,joint='curve')
        attrs=f' stroke-dasharray="{dash*self.scale:.2f} {dash*self.scale:.2f}"' if dash else ''
        self.svg.append('<polyline points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in q)+f'" fill="none" stroke="{color}" stroke-width="{width*self.scale:.2f}" stroke-linecap="round" stroke-linejoin="round"{attrs}/>')
    def circle(self,p,r,fill,stroke=None):
        x,y=self.xy(p); rr=r*self.scale
        self.draw.ellipse([x-rr,y-rr,x+rr,y+rr],fill=fill,outline=stroke,width=max(1,round(self.scale*.4)))
        self.svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{rr:.2f}" fill="{fill}" stroke="{stroke or "none"}"/>')
    def text(self,p,txt,size=4,color='#233c40',anchor='mm',halo=True):
        if not self.visible(p): return
        self.text_px(self.xy(p),txt,size*self.scale,color,anchor,halo)
    def text_px(self,pos,txt,size,color='#233c40',anchor='la',halo=False):
        size=max(9,round(size))
        if size not in self.fonts: self.fonts[size]=ImageFont.truetype(str(FONT),size)
        stroke=max(1,round(size*.08)) if halo else 0
        self.draw.text(pos,txt,font=self.fonts[size],fill=color,anchor=anchor,stroke_width=stroke,stroke_fill='#faf8f0')
        align='middle' if anchor[0]=='m' else 'start'
        baseline='central' if anchor.endswith('m') else 'text-before-edge'
        attr=f' stroke="#faf8f0" stroke-width="{stroke*2}" paint-order="stroke"' if halo else ''
        self.svg.append(f'<text x="{pos[0]:.2f}" y="{pos[1]:.2f}" font-family="Arial, sans-serif" font-size="{size}" text-anchor="{align}" dominant-baseline="{baseline}" fill="{color}"{attr}>{html.escape(str(txt))}</text>')
    def label(self,p,txt,size=3.1):
        if not self.visible(p): return
        lines=txt.split('\n'); fontsize=max(9,round(size*self.scale))
        if fontsize not in self.fonts: self.fonts[fontsize]=ImageFont.truetype(str(FONT),fontsize)
        font=self.fonts[fontsize]
        width=max(self.draw.textlength(line,font=font) for line in lines)+6
        height=len(lines)*(fontsize+2)+3; base=self.xy(p)
        offsets=[(0,0)]
        for dist in [7,14,22,30,42]:
            offsets.extend([(0,-dist),(0,dist),(-dist,0),(dist,0),(-dist,-dist),(dist,-dist),(-dist,dist),(dist,dist)])
        chosen=None
        for ox,oy in offsets:
            x,y=base[0]+ox*self.scale,base[1]+oy*self.scale
            bb=(x-width/2,y-height/2,x+width/2,y+height/2)
            if bb[0]<2 or bb[2]>self.w-2 or bb[1]<self.header+1 or bb[3]>self.header+(self.bounds[3]-self.bounds[1])*self.scale-2: continue
            if any(bb[0]<b[2]+3 and bb[2]>b[0]-3 and bb[1]<b[3]+3 and bb[3]>b[1]-3 for b in self.label_boxes): continue
            chosen=(x,y,bb,ox,oy); break
        if chosen is None: return  # only off-edge labels; full source mapping remains in JSON/report
        x,y,bb,ox,oy=chosen; self.label_boxes.append(bb)
        if ox or oy:
            end=m((self.bounds[0]+x/self.scale,self.bounds[1]+(y-self.header)/self.scale))
            self.line([p,end],'#6f8180',.25)
        for i,line in enumerate(lines): self.text_px((x,y+(i-(len(lines)-1)/2)*(fontsize+2)),line,fontsize,anchor='mm',halo=True)
    def finish(self): return '\n'.join(self.svg+['</svg>'])+'\n'


LABELS={
    'forest':(151,494),'village':(241,281),'transition':(474,306),'residential':(737,122),
    'old_town':(674,303),'industrial':(995,253),'elite':(928,301),'fields':(391,518),'beach_parking':(736,522)}


def draw_map(d,c,labels=True,crop=False):
    # Opaque landscape first; conceptual district boundaries deliberately have no strokes.
    c.polygon(d['boundary']['polygon_m'],'#e6ead5')
    sea=next(w for w in d['water'] if w['id']=='SEA')
    c.polygon(sea['polygon_m'],'#b7d9e3')
    for dist in d['districts']: c.polygon(dist['polygon_m'],dist['color'])
    for h in d['hills']:
        g=Polygon(h['polygon_m'])
        for factor in [.9,.7,.5,.3]: c.line(ring(affinity.scale(g,factor,factor,origin='centroid'))+ring(affinity.scale(g,factor,factor,origin='centroid'))[:1],'#aabc97',.6)
    for v in d['vegetation_parcels']:
        if v['kind']=='interdistrict_barrier': continue
        c.polygon(v['polygon_m'],{'grove':'#b5c99d','orchard':'#bfcb93','swamp':'#94ad92','rock_scarp':'#c1c1b1'}.get(v['kind'],'#bdcea5'))
        if v['kind']=='rock_scarp':
            g=Polygon(v['polygon_m']); xmin,ymin,xmax,ymax=g.bounds
            for x in range(int(xmin),int(xmax),22):
                for y in range(int(ymin),int(ymax),22):
                    if g.contains(Point(x,y)): c.line([[x-7,y-5],[x,y+6],[x+8,y-4]],'#a9afa1',1)
        if v['kind'] in ['grove','orchard']:
            g=Polygon(v['polygon_m']); xmin,ymin,xmax,ymax=g.bounds
            rng=random.Random(v['id'])
            for x in range(int(xmin)+3,int(xmax),10):
                for y in range(int(ymin)+3,int(ymax),11):
                    p=[x+rng.uniform(-2.6,2.6),y+rng.uniform(-2.6,2.6)]
                    if g.contains(Point(p)): c.circle(p,rng.uniform(2.2,3.2),'#92ae77')
    for b in d['beaches']: c.polygon(b['polygon_m'],'#f0dfaa')
    for f in d['crop_fields']:
        c.polygon(f['polygon_m'],'#ddc67b','#c4aa60',.4)
        g=Polygon(f['polygon_m']); x0,y0,x1,y1=g.bounds
        for x in np.arange(x0,x1,3):
            clipped=g.intersection(LineString([(x,y0-1),(x,y1+1)]))
            if isinstance(clipped,LineString): c.line(list(clipped.coords),'#c7b363',.4)
    for w in d['water']:
        if w['id']=='SEA': continue
        c.polygon(w['polygon_m'],'#91c5d6','#74afbf',.4)
    for s in d['functional_sites']:
        if s['type'] in ['production_yard','parking','garage_yard','square','park','quay','pier']:
            c.polygon(s['polygon_m'],{'parking':'#c3c9c6','production_yard':'#cecec0','garage_yard':'#a2b1b1',
                  'square':'#f5edd9','park':'#bed39f','quay':'#c5b797','pier':'#bfa07d'}[s['type']],'#a3a590',.4)
            if s['type']=='parking':
                g=Polygon(s['polygon_m']); x0,y0,x1,y1=g.bounds
                for x in np.arange(x0+2,x1-1,4): c.line([[x,y0+1],[x,min(y0+7,y1-1)]],'#f5f1de',.4)
    # Every road rendered at its actual validated width. Minor driveways visually secondary.
    for r in d['roads']:
        c.line(r['polyline_m'],'#afb8ae',r['width_m']+.8)
        c.line(r['polyline_m'],'#eee6d2' if r.get('access_only') else '#d8bc87' if r['class']=='rural_road' else '#8f9c9e',r['width_m'])
    for r in d['roads']:
        if r['lanes']==2 and not r.get('access_only'): c.line(r['polyline_m'],'#eee9d8',.25,4)
    for p in d['paths']: c.line(p['polyline_m'],'#f8eed5',p['width_m'])
    for w in d['water_crossings']+d['pedestrian_water_crossings']:
        c.line(w['deck_axis_m'],'#705e45',w['width_m']+1.2)
        c.line(w['deck_axis_m'],'#efe0bd',w['width_m'])
    for b,g in physical(d):
        kind=b.get('type',b.get('kind'))
        col=('#98b5d1' if kind=='police_station' else '#aac8db' if kind in ['tower','office'] else
             '#a9c8b5' if kind in ['house_base','wagon_base','prestige_base','garage_base'] else
             '#b5bec0' if kind in ['panel','midrise','warehouse','depot','industrial_complex'] else
             '#ccae8e' if kind in ['mansion','rural_house','rural_outbuilding'] else '#d6b8a1')
        p=b.get('footprint_m',b.get('polygon_m')); c.polygon(p,col,'#64757a',.5)
        if b.get('kind')=='tower': c.polygon(ring(affinity.scale(g,.72,.72,origin='centroid')),'#b8d3e5','#718ca0',.4)
        if b.get('type')=='church': c.text(b['center_m'],'✚',5,halo=False)
    for s in d['functional_sites']:
        kind=s['type']; p=s.get('polygon_m'); center=list(Polygon(p).centroid.coords[0]) if p else s.get('position_m')
        if kind=='fountain':
            c.polygon(p,'#9bcddd','#638fa3',.8); c.circle(center,1.7,'#edf8fb')
        elif kind=='football_pitch':
            c.polygon(p,'#87b46c','#ecf1dd',.7)
            c.circle(center,4.5,'#87b46c','#edf4d9'); q=Polygon(p).bounds
            c.line([[(q[0]+q[2])/2,q[1]],[(q[0]+q[2])/2,q[3]]],'#edf4d9',.4)
        elif kind=='umbrella':
            c.polygon(p,'#e6eeec','#78949b',.3); q=Polygon(p).bounds
            c.line([[q[0],center[1]],[q[2],center[1]]],'#c46c62',1.1)
            c.line([[center[0],q[1]],[center[0],q[3]]],'#c46c62',1.1)
        elif kind=='lounger': c.polygon(p,'#fbf7e6','#91a3a4',.3)
        elif kind=='lifeguard_tower': c.polygon(p,'#c08361','#775842',.5); c.text(center,'С',3.4,halo=False)
        elif kind=='rock': c.polygon(p,'#a7b2ad','#829791',.4)
        elif kind=='lamp': c.circle(center,.8,'#fcf8de','#4a6272')
        elif kind=='tree':
            c.circle(center,s.get('crown_radius_m',2),'#94b477')
            c.circle([center[0]-.45,center[1]+.45],s.get('crown_radius_m',2)*.7,'#a9c58d')
        elif kind=='palm':
            c.circle(center,.4,'#8f7e54')
            for a in range(0,360,60):
                ang=math.radians(a); c.line([center,[center[0]+3*math.cos(ang),center[1]+3*math.sin(ang)]],'#6a9b68',1)
        elif kind=='flag':
            c.line([center,[center[0],center[1]+3]],'#617b83',.35)
            c.polygon([center,[center[0]+3,center[1]+2],[center[0],center[1]+3]],'#679cbd')
        elif kind=='hangout': c.circle(center,2.1,'#9b7e5a','#806343')
    # Railway ties and two rails.
    rail=LineString(d['railway']['polyline_m'])
    c.line(d['railway']['polyline_m'],'#b0a28b',3)
    for dist in np.arange(0,rail.length,2):
        p=rail.interpolate(dist); q=rail.interpolate(min(rail.length,dist+1)); dx,dy=q.x-p.x,q.y-p.y; ll=math.hypot(dx,dy) or 1
        c.line([[p.x-dy/ll*2,p.y+dx/ll*2],[p.x+dy/ll*2,p.y-dx/ll*2]],'#746f60',.45)
    c.line(d['railway']['polyline_m'],'#536263',.7)
    for f in d['vegetation_parcels']:
        if f['kind']=='interdistrict_barrier': c.line(f['axis_m'],'#566562',1.1 if f['material']=='port_wall' else .65)
    mar=d['marina']
    c.polygon(mar['breakwater']['polygon_m'],'#9da39b','#758c89',.5)
    for part in [mar['pier'],mar['t_head']]+mar['fingers']: c.polygon(part['polygon_m'],'#bea17e','#877255',.4)
    for b in mar['berths']: c.line(b['polygon_m']+b['polygon_m'][:1],'#7fb1ba',.3,1)
    for b in mar['boats']: c.polygon(b['polygon_m'],'#f4f4e7','#628e99',.45)
    c.circle(mar['breakwater']['light_m'],1,'#f0d272','#817753')
    # Fine coast line makes the shared land/sea edge reviewable.
    c.line(mm(COAST),'#719eaa',.6)
    if not labels: return
    for dist in d['districts']:
        p=m(LABELS[dist['id']]); text=dist['name_ru']; num=next(r[:2] for r,di,*_ in REGIONS if di==dist['id'])
        c.label(p,num+' · '+text,7 if not crop else 4.4)
    if crop:
        for b,g in physical(d):
            if 'label_ru' not in b: continue
            if not c.visible(b['center_m']): continue
            label=b['label_ru']; words=label.split(); lines=[]; buf=''
            for word in words:
                if len(buf)+len(word)>17 and buf: lines.append(buf); buf=word
                else: buf=(buf+' '+word).strip()
            if buf: lines.append(buf)
            c.label(b['center_m'],'\n'.join(lines),2.8)
    for p in d['points']:
        if not crop and p['category'] not in ['base','landmark']: continue
        pos=p['position_m']; c.circle(pos,1.6,'#405b60' if p['mapping_confidence']!='proposed' else '#b87d3d','#fcf7e9')
        label=p['id']
        above=[pos[0],pos[1]+4.3]
        c.label(above,label,3.1 if crop else 3.8)
    for sid,label in [('ROUGH_FOOTBALL','Футбол'),('FOUNTAIN14','Фонтан'),('BEACH_PARKING','Парковка'),('CITY_PIER','Т-пирс')]:
        s=next(q for q in d['functional_sites'] if q['id']==sid)
        c.label(list(Polygon(s['polygon_m']).centroid.coords[0]),label,3.2)
    c.label(m((1061,530)),'Марина · 10 мест',4)


def decorate(c,title,subtitle):
    # Covers any off-canvas geometry in the header/footer while retaining a clean SVG clipping region.
    map_end=c.header+round((c.bounds[3]-c.bounds[1])*c.scale)
    c.draw.rectangle([0,0,c.w,c.header-1],fill='#f8f5ed'); c.draw.rectangle([0,map_end,c.w,c.h],fill='#f8f5ed')
    c.svg.extend([f'<rect x="0" y="0" width="{c.w}" height="{c.header}" fill="#f8f5ed"/>',
                  f'<rect x="0" y="{map_end}" width="{c.w}" height="{c.h-map_end}" fill="#f8f5ed"/>'])
    c.text_px((24,10),title,25); c.text_px((24,42),subtitle,14,color='#627776')
    c.text_px((c.w-54,10),'С ↑',20)
    foot=map_end+15
    c.text_px((24,foot),'2D на согласование · здания / дороги ≤2 полос · янтарные метки: предлагаемые игровые привязки',14)
    c.text_px((24,foot+24),'Ограды только у элитки и порта. Берег, река, рельсы — по Master v02. 3D и вождение не проверялись.',13,color='#6d7e78')
    length=100/S*c.scale; start=(max(24,c.w-length-30),foot+10)
    c.draw.line([start,(start[0]+length,start[1])],fill='#49676d',width=3)
    c.svg.append(f'<path d="M {start[0]:.2f},{start[1]} h {length:.2f}" stroke="#49676d" stroke-width="3"/>')
    c.text_px((start[0],start[1]+6),'0',12); c.text_px((start[0]+length-32,start[1]+6),'100 м',12)


def render_all(d):
    full=Canvas([6,0,1227,714],3,70,85)
    draw_map(d,full); decorate(full,'VOLUNTEERS ONLY · мастер-карта R01 / v15','Фиксированная рамка Master v02 · 1,013746 м/px · север сверху · 9 районов')
    (ROOT/(STEM+'.svg')).write_text(full.finish(),encoding='utf-8')
    full.im.save(ROOT/(STEM+'.png'))
    # Same extent/pixels as the source, no guessed rescale of the overlay.
    overlay=Canvas([0,0,1280,714],3,0,0); draw_map(d,overlay,labels=False)
    source=Image.open(ROOT/'REF_FEDYA_MASTER_v02_map.png').convert('RGB').resize(overlay.im.size,Image.Resampling.LANCZOS)
    Image.blend(source,overlay.im,.43).save(ROOT/(STEM+'_overlay.png'))
    crops={}
    for rid,did,ru,en,_ in REGIONS:
        bounds=FRAME['crops'][rid]['source_box_px']
        if rid=='07_elite': bounds=[785,255,1140,600]  # includes the transplanted breakwater, above source legend
        c=Canvas(bounds,5,70,80); draw_map(d,c,crop=True); decorate(c,f'{rid[:2]} · {ru} [{en}] · v15','Локальный район · игровые ID сохранены, сомнительные привязки отмечены в отчёте')
        path=ROOT/f'{STEM}_crop_{rid}.png'; c.im.save(path); crops[rid]=dict(file=path.name,source_box_px=bounds)
        if rid in ['05_downtown','09_beach']:
            ref='REF_FEDYA_MASTER_v02_'+('downtown_02' if rid=='05_downtown' else 'city_beach')+'.png'
            src=Image.open(ROOT/ref).convert('RGB'); height=1100
            a=c.im.resize((round(c.im.width*height/c.im.height),height),Image.Resampling.LANCZOS)
            b=src.resize((round(src.width*height/src.height),height),Image.Resampling.LANCZOS)
            pair=Image.new('RGB',(a.width+b.width+30,height+48),'#f8f5ed'); pair.paste(a,(0,48)); pair.paste(b,(a.width+30,48))
            draw=ImageDraw.Draw(pair); font=ImageFont.truetype(str(FONT),21)
            draw.text((20,12),'СХЕМА v15',font=font,fill='#29464b'); draw.text((a.width+50,12),'ДЕТАЛЬНЫЙ ЛИСТ ФЕДИ',font=font,fill='#29464b')
            pair.save(ROOT/f'{STEM}_compare_{rid}.png')
    d['render_statistics']=dict(canvas_px=list(full.im.size),scale_px_per_m=round(3/S,5),crops=crops,
        overlay_opacity=.43,overlay_source_px=[1280,714],overlay_upscale=3)


def report(d):
    v=d['validation']; checks=v['checks']; passed=sum(c['passed'] for c in checks); fit=d['fit_evidence']
    lines=['# VOLUNTEERS ONLY — мастер-карта R01 v15','',
      '**Статус:** 2D на согласование Феде и Вадиму. Не импортировано в Unity. Субъективная приёмка и вождение не проверялись.','',
      f'Технические проверки: **{passed}/{len(checks)}**. Отдельно два запуска генератора сравниваются по SHA-256 всех выходных файлов; результат в `MAP_PLAN_R01_v15_QA.json`.',
      '', '## Что оцифровано','',
      f"Девять районов в рамке Master v02: {d['metrics']['building_count']} физических зданий; {len(d['roads'])} дорог/подъездов; {len(d['paths'])} пеших путей; {len(d['points'])} размещённых игровых точек. Масштаб 1,013746 м/px сохранён; контур суши {d['metrics']['extent_m'][0]:.1f} × {d['metrics']['extent_m'][1]:.1f} м, включая хребет. Предел 1000 м из старого плана не применён.",
      '',
      '- Лес: вагон на рельсах у берега, костёр, болотный пруд и озеро, рощи и дороги.',
      '- Хутор: дома, церковь, два поля, огороды, водонапорная башня, пруд; Перекрёсток: дорожный узел, двор приёмки, АЗС, дома, пруд.',
      '- Подворотни: U/L-панели вокруг дворов, гаражные ряды, футбольное поле и магазин «24 часа» непосредственно южнее поля.',
      '- Город: две полиции, башни-близнецы с парковками по обе стороны, площадь и фонтан, кафе, бутики, 2 ATM, книги/подарки, кафе-ресторан; 6 жилых домов 3–6 этажей, дворы и сквер; база #13, магазин бусика #07, офисы #05/#06, таксопарк #12; 17 фонарей-якорей.',
      '- Порт: собственный периметр с воротами, промышленные здания и ёмкости, набережная и пирс. Функции неоднозначных построек предложены из v14.',
      '- Элитка: овальный холм, петля дороги, четыре особняка с бассейнами, сервис и охрана, свой периметр; марина v14 перенесена жёстко, без масштаба: Т-пирс, 3 понтона, 10 мест, 3 яхты, 4 катера, мол с огнём.',
      '- Долина: большой дом, пруд, южное большое здание, дорога к малому пляжу.',
      '- Городской пляж: канал с 3 мостами, парковка, кофейный киоск слева, душ/туалет справа, 12 зонтов и 24 шезлонга, спасательная вышка, 2 флага, 13 пальм, камни, деревянный Т-пирс.',
      '', '## Точность и интерпретации','',
      f"Контроль по {len(fit['observations'])} читаемым центрам на мастер-карте: медиана **{fit['median_m']:.2f} м**, максимум **{fit['max_m']:.2f} м**. Контрольные наблюдения сохранены в JSON `fit_evidence`. Это ручная оценка центров (±2–4 м), не доказательство точности каждого контура или нечитаемой подписи.",
      'Визуально просмотрены полный overlay, все девять районных кропов и пары Downtown/Beach с детальными листами. После просмотра уточнены подписи, берег Beach и озеленение Downtown. Сходство схемы — рабочая оценка, окончательное «ок» остаётся у Феди и Вадима.',
      'Downtown зарегистрирован по четырём углам уличной рамки: деталь (35,125)–(1245,765) → мастер (539,309)–(811,452). Beach привязан монотонно по трём мостам и Т-пирсу; полный набор опор в `detail_registration`. Детальные листы не имеют собственной достоверной метрической шкалы.',
      'Берег/море используют одну общую полилинию. В пределах City Beach контур заменён более точной волнистой береговой линией детального листа; остальной берег сохранён по мастеру. У западного края этого локального уточнения разница с мастером до ~30 м — намеренный приоритет детального листа, не заявление о допуске 8 м. Опоры сохранены в `BEACH_DETAIL_SHORE`. Парковка, киоск и душ также имеют приоритет над схематичными пятнами мастера.',
      'Из 23 опор 12 относятся к прямой трассировке и проверяют преобразование координат; 11 служат проверкой привязки детальных листов. Нулевые ошибки прямых опор не являются независимым измерением точности.',
      'Проезды к зданиям сгенерированы как локальные предложения и проверены на ширину 3,8 м. В подворотнях контуры нескольких малых объектов уточнены на единицы метров ради свободного прохода. Стыковки дорог до 2 м перечислены в `geometry_repairs`. Это не перенос старого уличного графа.',
      'Слои площадей, парков, дворов и функциональных объектов намеренно вложены друг в друга; запрет пересечений проверяет физические здания между собой, полную ширину дорог со зданиями/оградами, районы и сушу/море. Настилы портового причала и пирсов допускаются над водой.',
      '', '## Привязка игровых точек v14','', '| ID | Название v14 | Мастер / объект | Статус |','|---|---|---|---|']
    for q in d['gameplay_mapping']:
        status={'readable':'читается','detail_sheet':'детальный лист','proposed':'предложено; подтвердить','unmapped':'ВОПРОС','explicit_addition':'прямо добавлено в брифе'}.get(q['status'],q['status'])
        lines.append(f"| {q['id']} | {q['name_ru']} | {q['master_key'] or q['question_ru']} | {status} |")
    lines+=['','B01 — вагон; B03 — место чёрной метки у юго-западной L-панели, гаражная функция предложена; B04 — #13 будущая база Downtown; B05 — промкомплекс порта, предполагаемая привязка; B06 — синий дом у пруда долины, предполагаемая привязка. B02 сохранён отдельной хижиной на Перекрёстке как предложение, а не автоматически слит с домом деда P02.',
      'P10 закреплён за полицией 1, P10-2 добавлен у полиции 2. CLOCK_SQUARE сохраняет ID центральной площади; отдельные часы на листе отсутствуют. P05 сохранён для магазина/сервиса бусика #07, требует подтверждения функционального соответствия. Второй городской ATM имеет новый уникальный ID P11-DT2.',
      'Сохранено 50 из 51 функционального ID v14. F06_SUPER теперь обозначает подписанные на листе бутики; это торговое соответствие для подтверждения. F06_BANK не получил отдельного здания: лист показывает ATM, а не банк. Полная сверка — `building_mapping`; отдельный реестр ключей 01–15 — `downtown_object_keys`.',
      '', '## Вопросы Феде','',
      '1. Подтвердить B02/P02: чёрная метка в Хуторе означает дом деда, хижину-базу или другой дом? Пять читаемых меток не дают однозначной схемы шести баз B01–B06.',
      '2. Где выездные посты P16 и P16-2? На мастере их нет: в v15 они не выдуманы, записаны как unmapped и не входят в проверку достижимости размещённых точек.',
      '3. Прислать TXT/ключ Downtown 01–15: на картинке «10» повторён у полиции 1 и башни 1, остальные номера нельзя однозначно распределить. #05, #06, #07, #11, #12, #13 сохранены буквально.',
      '4. Подтвердить функции порта (B05, P14, P12, высокая труба), B03 в панельном квартале и B06 в долине; дом внизу долины интерпретирован как прежнее казино. Не все виды из v14 однозначно соответствуют пятнам мастера.',
      '5. P05 = магазин для бусика #07 или нужна отдельная автомастерская? Где F06_BANK и допустимо ли F06_SUPER → бутики? CLOCK_SQUARE остаётся названием ID; нужны ли физические часы? Высота башен 20 этажей из v14 пока предложение.',
      '6. Подтвердить служебный проезд бусика через центральный мост пляжа, предложенные дворовые подъезды и место марины. Боковые мосты пешеходные. До пирсов бусик доезжает по наземному причалу/парковке; не по понтонам.',
      '7. Принять масштаб рамки (~1,16 км по суше) или выдать новое отдельное решение о масштабе? Точность текста мелких ключей ограничена исходным 1280×714 изображением.',
      '', '## Проверки','', '| Проверка | Результат | Данные |','|---|---|---|']
    for c in checks: lines.append(f"| {c['name']} | {'PASS' if c['passed'] else 'FAIL'} | {str(c['detail']).replace('|','/')} |")
    lines+=['', '## Файлы и локальные уточнения','',
      '- `map_plan_v15.py` → `MAP_PLAN_R01_v15.json/.svg/.png`, `_overlay.png`, `_crop_01_forest.png` … `_crop_09_beach.png`, `_compare_05_downtown.png`, `_compare_09_beach.png`, этот отчёт и `_QA.json`.',
      '- `Master_v02/fragments/v15_<region>.json` — срезы по именованным регионам, в метрах и со стабильными ID. Исходные координаты каждого района находятся в отдельной `build_<district>()` функции; общие улицы/берег принадлежат `00_world`.',
      '- Повторная локальная редакция: `python -B map_plan_v15.py --baseline <предыдущий JSON> --allow-region 05_downtown`. Проверка сравнивает геометрию/атрибуты остальных регионов; общий граф и статистика вычисляются заново. Межрайонный стык/берег требует явного включения `00_world`.',
      '- Зависимости: Python 3.12, Pillow, numpy, Shapely 2. Скрипт не импортирует и не исполняет старые генераторы, не пишет pyc.',
      '- Схема v14 2.0 и все верхние типы сохранены, существующие типы/ID переиспользованы по смыслу. Техническая проба downstream описана в QA. Старый dressing v12 содержит жёсткие ID удалённых ещё в v14 объектов и не является универсальным потребителем; обновление dressing/Unity не входит в этот бриф.',
      '- Greybox и Look проверяются чтением v15 и построением результата в памяти: никаких файлов Unity/flattened-сцен не создаётся. Счётчики, предупреждения и тест локальности — в QA. Старый Look экспортирует только первый пляж (City Beach поставлен первым), не поддерживает все типы v13–v15 и предлагает старые парковки. Crowd привязан к v12; PoliceBaker не запускался. Совместимость чтения не означает готовность 3D сборки.',
      '- Предыдущие версии, рамка, референсы, Assets, WORK_SYNC.md, staging/commit/push не изменялись.']
    return '\n'.join(lines)+'\n'


def source_hashes():
    paths=[p for p in ROOT.rglob('*') if p.is_file() and (p.name.startswith('REF_') or p.name.startswith('map_plan_v1') and p.name!='map_plan_v15.py' or p.name.startswith('MAP_PLAN_R01_v1') and not p.name.startswith(STEM) or 'frame' in p.parts)]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def output_paths():
    return sorted([p for p in ROOT.glob(STEM+'*') if p.is_file() and p.name!=STEM+'_QA.json']+
                  list((ROOT/'Master_v02/fragments').glob('v15_*.json')))


def write_outputs(d):
    render_all(d)
    folder=ROOT/'Master_v02/fragments'; folder.mkdir(parents=True,exist_ok=True)
    for rid in d['region_fingerprints']:
        fragment=dict(id='v15_'+rid,frame='Master_v02/frame/m2_frame.json',region=rid,units='metre',
                      fingerprint=d['region_fingerprints'][rid],layers=region_records(d,rid))
        (folder/f'v15_{rid}.json').write_text(json.dumps(fragment,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (ROOT/(STEM+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (ROOT/(STEM+'_REPORT.md')).write_text(report(d),encoding='utf-8')


def downstream_smoke(d):
    """Read-only consumer probes. Greybox output is intercepted in memory, Look.run returns a dict.

    No flattened deliverable, editor invocation, scene, asset, or legacy script write occurs.
    A parser smoke test is deliberately not a claim that legacy dressing supports all new map content.
    """
    result={}; original_open=builtins.open; argv=sys.argv[:]; syspath=sys.path[:]
    memory=io.StringIO()
    target=(ROOT/'Greybox/greybox_v15_flat.json').resolve()
    def intercept(path,mode='r',*args,**kwargs):
        if any(c in mode for c in 'wa+'):
            if Path(path).resolve()!=target: raise RuntimeError('Unexpected consumer write: '+str(path))
            return memory
        return original_open(path,mode,*args,**kwargs)
    try:
        sys.argv=['flatten_plan.py','v15']
        with patch('builtins.open',intercept),contextlib.redirect_stdout(io.StringIO()):
            ns=runpy.run_path(str(ROOT/'Greybox/flatten_plan.py'),run_name='v15_consumer_probe')
        flat=ns['out']
        result['greybox']=dict(passed=len(flat['buildings'])==d['metrics']['building_count'] and len(flat['points'])==len(d['points']),
                               buildings=len(flat['buildings']),points=len(flat['points']),output='memory only')
    except Exception as exc: result['greybox']=dict(passed=False,error=repr(exc))
    finally: sys.argv=argv
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            ns=runpy.run_path(str(ROOT/'Look/flatten_look.py'),run_name='v15_look_probe')
            opts=SimpleNamespace(no_dressing=True,no_veg=True,no_extras=True,no_kits=True,lake_depth=1.1,canal_depth=1.2,seed=12)
            look=ns['Look'](d,None,opts)
            flat=look.run('v15',str(ROOT/(STEM+'.json')),None)
        result['look']=dict(passed=len(flat['buildings'])==d['metrics']['building_count'],buildings=len(flat['buildings']),
            warnings=flat['warnings'],output='memory only',options='no dressing, no vegetation, no legacy v12 extras/kits')
    except Exception as exc: result['look']=dict(passed=False,error=repr(exc))
    finally: sys.path[:]=syspath
    result['legacy_limits_ru']=[
       'Dressing v12 жёстко ищет INDUSTRIAL_BEACH_FENCE_1 и другие объекты старой карты; автоматический запуск на v15 не выполнялся.',
       'Crowd v12 жёстко читает v12 и проверяет hash dressing. Новая расстановка требует нового bake.',
       'PoliceBaker читает тот же road_graph/points/P10/F06_POLICE; реальный Unity bake не запускался.',
       'Старые flatteners не отображают все добавочные слои v14/v15, в частности port_wall, марину и детальный пляж. Это ограничение потребителей, не ошибка чтения схемы.']
    # Verify the locality guard with real mutations, without writing a duplicate baseline.
    before=region_fingerprints(d); test=copy.deepcopy(d)
    next(b for b in test['functional_buildings'] if b['id']=='F15_OFFICE_1')['label_ru']+=' (probe)'
    after=region_fingerprints(test)
    local=[k for k in before if before[k]!=after[k]]
    next(b for b in test['functional_buildings'] if b['id']=='F06_WAGON')['label_ru']+=' (probe)'
    cross=[k for k in before if before[k]!=region_fingerprints(test)[k]]
    result['locality_guard']=dict(passed=local==['05_downtown'] and set(cross)=={'01_forest','05_downtown'},
        local_change_regions=local,outside_change_detected='01_forest' in cross)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline'); parser.add_argument('--allow-region',action='append',default=[])
    parser.add_argument('--single-run',action='store_true',help='For iteration only: default performs two full builds/renders and byte comparison.')
    args=parser.parse_args()
    before=source_hashes(); d=build(); validate(d,args.baseline,args.allow_region)
    # Failed geometry still renders for inspection, but process returns failure and the report marks failures.
    write_outputs(d)
    first={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in output_paths()}
    same=None
    if not args.single_run:
        second=build(); validate(second,args.baseline,args.allow_region); write_outputs(second)
        after={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in output_paths()}
        same=first==after
    protected=source_hashes()==before
    consumers=downstream_smoke(d)
    qa=dict(checks_passed=sum(c['passed'] for c in d['validation']['checks']),checks_total=len(d['validation']['checks']),
       all_geometry_checks_passed=d['validation']['passed'],two_runs_byte_identical=same,compared_outputs=len(first),
       output_sha256=first,protected_inputs_unchanged=protected,protected_input_count=len(before),
       downstream=consumers,
       subjective_acceptance='pending Fedya and Vadim',unity_or_vehicle_test='not run; outside task scope')
    (ROOT/(STEM+'_QA.json')).write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in qa.items() if k not in ['output_sha256','downstream']},ensure_ascii=False))
    print(json.dumps(consumers,ensure_ascii=False))
    if not d['validation']['passed']:
        print(json.dumps([c for c in d['validation']['checks'] if not c['passed']],ensure_ascii=False,indent=2))
    if not protected or same is False or not d['validation']['passed'] or not all(consumers[k]['passed'] for k in ['greybox','look','locality_guard']): raise SystemExit(1)


if __name__=='__main__': main()
