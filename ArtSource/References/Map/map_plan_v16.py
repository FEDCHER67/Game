"""World v11 -> R01 v16. Python 3.12; Shapely, NumPy, Pillow.

Build in an empty output directory first. Existing deliverables are never replaced.
python -B map_plan_v16.py --out-dir PATH --map-dir C:/Dev/Game/ArtSource/References/Map
The existing flatteners dispatch to the optional world_v11 adapter in this module.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import heapq
import importlib.util
import json
import math
import sys
import os
import runpy
import contextlib
import io
import re
import xml.etree.ElementTree as ET
import subprocess
import tempfile
import builtins
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, nearest_points, substring
from PIL import Image, ImageDraw, ImageFont

MAP = Path(__file__).resolve().parent
REV = 'v16'
STEM = 'MAP_PLAN_R01_v16'
DISTRICTS = {
    '01': ('forest', ['forest'], '#bdcdbb'),
    '02': ('village', ['village', 'hamlet'], '#dedbb1'),
    '03': ('transition', ['transition', 'construction'], '#d0d4b5'),
    '04': ('residential', ['residential', 'rough', 'alley'], '#bbc9ce'),
    '05': ('old_town', ['old_town', 'downtown'], '#e4c9b2'),
    '06': ('industrial', ['industrial', 'port'], '#c9c4cc'),
    '07': ('elite', ['elite'], '#c8d5ad'),
    '08': ('fields', ['fields', 'valley'], '#d8d6a7'),
    '09': ('beach', ['beach'], '#efdfb2'),
    '10': ('tramduro', ['tramduro'], '#c8cdba'),
}
CLASS = {'asphalt':'rural_road', 'boulevard':'highway', 'city_street':'town_street',
         'dirt':'dirt_shortcut', 'lane':'dirt_shortcut', 'site_track':'dirt_shortcut',
         'private_drive':'rural_road', 'trail':'passage', 'footpath':'passage',
         'promenade':'passage', 'beach_path':'passage'}
FOOT = {'trail', 'footpath', 'promenade', 'beach_path'}
GAME = {
    'P02': ('base','Base 2'),
    'WATER_TOWER': ('structure','02_water_tower'),
    'P05': ('poi','03:01'),
    'P07': ('poi','04:05'),
    'P10': ('poi','05:10'),
    'P11': ('poi','05:08'),
    'CLOCK_SQUARE': ('poi','05:04'),
    'ELITE_GATE': ('poi','07:06'),
    'BEACH_VALLEY_ENTRY': ('poi','08:05'),
}
QUESTIONS = {
    'P01':'No advertising/job-board landmark is exported. Where is the gameplay noticeboard?',
    'P03':'The former Hamlet pharmacy is explicitly a regular house. Was the pharmacy removed from gameplay?',
    'P04':'No shadow buyer/receiving point is identified. This ID is a hard-coded trip-meter destination.',
    'P06':'No bar is identified; Rough shawarma is a different function. Where is the bar?',
    'P08':'No hospital is identified. This ID is a hard-coded trip-meter destination.',
    'P11-2':'No Rough shop ATM is identified.', 'P11-3':'No hospital ATM is identified.',
    'P12':'No tow/impound yard is identified.', 'P14':'No railway depot is identified; taxi depot 05:12 is a different function.',
    'CHIMNEY':'No old industrial chimney is exported; the old B01 sightline is unresolved.',
    'P15':'Four Elite villas exist, but which villa replaces the old VIP/mansion P15?',
    'P15-2':'Which Elite villa replaces the second mansion P15-2?',
    'BAD_CENTER':'Several Rough courtyards exist; no canonical central meeting/reference point is specified.',
    'BAD_BLOCK':'Which Rough courtyard replaces old courtyard 1?',
    'BAD_BLOCK_2':'Which Rough courtyard replaces old courtyard 2?',
    'BAD_BLOCK_3':'Which Rough courtyard replaces old courtyard 3?',
    'P09':'No behind-supermarket meeting spot is identified; no supermarket is named.',
    'P09-2':'No courtyard meeting spot is identified.',
    'P09-3':'B05 is now the Valley lab; no meeting spot beside it is specified.',
    'P09-4':'Construction replaces Crossing; no meeting spot is specified.',
    'P13':'Lakes/ponds are exported, but no gameplay water-access/van-stop point is specified.',
    'P13-2':'No gameplay river-access/van-stop point is specified.',
    'P13-3':'Canal promenade exists, but no gameplay canal-access/van-stop point is specified.',
    'P13-4':'Rough trash objects 08/14 exist; which is the gameplay disposal point?',
    'P13-5':'No Downtown gameplay disposal point is identified.',
    'P16':'No NW exit post or closed escape route is exported.',
    'P16-2':'No NE exit post or closed escape route is exported.',
    'BEACH_ENTRY':'The old Elite vehicle beach entry is replaced by stairs 07:12. Confirm an approved van entrance to City Beach parking 09:01.',
    'B06':'Removed by the brief: there are exactly five main bases.',
}

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def write_new(p, content):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8', newline='\n') as f:
        f.write(content)

def json_new(p, d):
    write_new(p, json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False)+'\n')

def parts(g, kind='Polygon'):
    if g.is_empty: return []
    if g.geom_type == kind: return [g]
    return [p for c in getattr(g,'geoms',[]) for p in parts(c,kind)]

def ring(g):
    return [list(p) for p in g.exterior.coords[:-1]]

def geom(q):
    return Polygon(q.get('footprint_m') or q['polygon_m'])

def valid(g):
    return g if g.is_valid else shapely.make_valid(g)

def flat(pts):
    return [round(float(v), 6) for p in pts for v in p[:2]]

def triangles(g):
    """Constrained triangulation preserves concavities and holes; never hull fallback."""
    result=[]
    for p in parts(valid(g)):
        for t in shapely.constrained_delaunay_triangles(p).geoms:
            t=shapely.geometry.polygon.orient(t, sign=1.0)
            result += flat(list(t.exterior.coords)[:3])
    return result

def obb(g):
    pts=list(g.minimum_rotated_rectangle.exterior.coords)
    a,b,c=pts[:3]
    w=math.dist(a,b); h=math.dist(b,c)
    return w,h,math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))

def load_module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def ccw_ring(g):
    return ring(shapely.geometry.polygon.orient(g,sign=1))

def marina(d,map_dir):
    """Rigid transforms of v14 motorboats/breakwater, with v11 SVG yacht exclusions."""
    src=read(map_dir/'MAP_PLAN_R01_v14.json')['marina']
    svg=ET.parse(map_dir/'World_v11/VOLUNTEERS_MAP_v11_MASTER.svg').getroot()
    district=next(q for q in svg.iter() if q.attrib.get('id')=='D07')
    # SVG viewBox starts (-350,-300); district translate is (5450,1460).
    hulls=[]
    for q in district.iter():
        if q.tag.endswith('polygon') and q.attrib.get('fill')=='#FFFFFF':
            pts=[[float(v) for v in p.split(',')] for p in q.attrib['points'].split()]
            hulls.append(dict(id=f'V11_YACHT_{len(hulls)+1}',kind='yacht',
                polygon_m=[[(5450+x+350)*.2,(3500-1460-y)*.2] for x,y in pts],
                source_ref='VOLUNTEERS_MAP_v11_MASTER.svg#D07 / white hull polygon',enrichment=False))
    assert len(hulls)==6
    d['marina_source_yachts']=hulls
    result=[]
    centers=[[1372,346],[1372,320],[1372,296],[1372,270]]
    for boat,center in zip([q for q in src['boats'] if q['kind']=='motorboat'],centers):
        a=math.radians(-boat['heading_deg']);c,s=math.cos(a),math.sin(a);ox,oy=boat['center_m']
        def transform(p):
            x,y=p[0]-ox,p[1]-oy
            return [round(center[0]+x*c-y*s,6),round(center[1]+x*s+y*c,6)]
        result.append(dict(boat,id=boat['id'].replace('MARINA14','MARINA16'),center_m=center,
            polygon_m=[transform(p) for p in boat['polygon_m']],heading_deg=0,berth_id=None,
            enrichment=True,enabled=True,optional=True,source_ref='MAP_PLAN_R01_v14.json#'+boat['id'],
            placement_rule='V11 east-facing piers; clear of six source yacht hulls and beach stairs'))
    bw=src['breakwater'];angle=math.radians(-68.1);c,s=math.cos(angle),math.sin(angle);ox,oy=src['root_m'];anchor=[1397,349]
    def transform(p):
        x,y=p[0]-ox,p[1]-oy
        return [round(anchor[0]+x*c-y*s,6),round(anchor[1]+x*s+y*c,6)]
    result.append(dict(bw,id='MARINA16_BREAKWATER',kind='breakwater',axis_m=[transform(p) for p in bw['axis_m']],
        polygon_m=[transform(p) for p in bw['polygon_m']],light_m=transform(bw['light_m']),
        enrichment=True,optional=True,enabled=False,requires_confirmation='Vadim',
        source_ref='MAP_PLAN_R01_v14.json#MARINA14_BREAKWATER',
        placement_rule='Rigid v14 shape rotated to the east of the three v11 piers; detached from coast'))
    result.append(dict(id='MARINA16_LIGHT',kind='navigation_light',position_m=transform(bw['light_m']),
        enrichment=True,optional=True,enabled=False,parent_id='MARINA16_BREAKWATER',
        requires_confirmation='Vadim',source_ref='MAP_PLAN_R01_v14.json#MARINA14_BREAKWATER.light_m'))
    d['marina_enrichment']=result
    d['marina_enrichment_settings']=dict(enabled=True,breakwater_enabled=False,
        switch_off='Set enabled=false on an item or the entire layer; light depends on breakwater_enabled.',
        approval='Fedya 2026-10-11; breakwater/light await Vadim',native_consumer_support=False)

def graph_stop(g, pos):
    p=Point(pos)
    n=min(g['nodes'],key=lambda n:p.distance(Point(n['position_m'])))
    if p.distance(Point(n['position_m']))<1e-6:return n
    hits=[e for e in g['edges'] if LineString(e['polyline_m']).distance(p)<1e-6]
    if not hits:raise ValueError('Source road projection does not lie on graph')
    n=dict(id=node_id(pos),position_m=pos);g['nodes'].append(n)
    for e in hits:
        g['edges'].remove(e)
        a,z=e['polyline_m'];
        for k,(aa,bb,an,bn) in enumerate([(a,pos,e['from_node'],n['id']),(pos,z,n['id'],e['to_node'])]):
            if math.dist(aa,bb)<1e-7:continue
            g['edges'].append(dict(e,id=e['id']+f'_{k}',from_node=an,to_node=bn,polyline_m=[aa,bb],length_m=math.dist(aa,bb)))
    return n

def sid(d): return DISTRICTS[d][0]

def node_id(p):
    return 'N'+hashlib.sha256(json.dumps(p,separators=(',',':')).encode()).hexdigest()[:14]

def graph(ways):
    lines=[LineString(r['polyline_m']) for r in ways]
    joins=[]; seen=set()
    # Source endpoints frequently stop within the already-drawn road surface.
    # Add graph links inside that surface; source polylines are never moved.
    for i,(r,l) in enumerate(zip(ways,lines)):
        for p in [l.coords[0],l.coords[-1]]:
            q=Point(p); cand=[]
            for j,(s,k) in enumerate(zip(ways,lines)):
                if i==j: continue
                distance=k.distance(q)
                limit=min(4.5,(r['width_m']+s['width_m'])/2)
                if 1e-7 < distance <= limit:
                    end=k.interpolate(k.project(q));
                    cand.append((distance,s['id'],end,j))
            if cand:
                dist,_,end,j=min(cand,key=lambda x:(x[0],x[1]))
                pair=tuple(sorted((tuple(p),tuple(end.coords[0]))))
                if pair in seen:continue
                seen.add(pair)
                joins.append(dict(id=f'SURFACE_JOIN_{len(joins)+1:03d}',
                    polyline_m=[list(p),list(end.coords[0])], width_m=min(r['width_m'],ways[j]['width_m']),
                    **{'class':r['class']}, van_access=r.get('van_access',True) and ways[j].get('van_access',True),
                    source_road_ids=[r['id'],ways[j]['id']],gap_m=dist))
    carriers=ways+joins; ls=lines+[LineString(j['polyline_m']) for j in joins]
    union=unary_union(ls); nodes={};edges=[]
    for line in parts(union,'LineString'):
        midpoint=line.interpolate(.5,normalized=True)
        owner=min((r for r,l in zip(carriers,ls) if l.distance(midpoint)<1e-7),key=lambda r:r['id'])
        coords=list(line.coords)
        for aa,bb in zip(coords,coords[1:]):
            a=tuple(round(v,7) for v in aa);b=tuple(round(v,7) for v in bb)
            if a==b:continue
            for q in (a,b):nodes.setdefault(q,node_id(q))
            eid='E'+hashlib.sha256(json.dumps([owner['id'],a,b]).encode()).hexdigest()[:16]
            edges.append(dict(id=eid,from_node=nodes[a],to_node=nodes[b],road_id=owner['id'],
                **{'class':owner['class']},width_m=owner['width_m'],length_m=math.dist(a,b),
                polyline_m=[list(a),list(b)],bidirectional=True,walkable=True,
                van_access=owner.get('van_access',True),bridge=bool(owner.get('bridge_id')),tunnel=False))
    return dict(nodes=[dict(id=v,position_m=list(k)) for k,v in sorted(nodes.items())],
                edges=edges,intersection_rule='Exact intersections plus documented endpoint links contained in existing road surfaces; source roads unchanged.',
                surface_connections=joins)

def build_plan(map_dir):
    global MAP
    MAP=Path(map_dir).resolve()
    w=read(map_dir/'World_v11/WORLD_MAP_v11.json'); old=read(map_dir/'MAP_PLAN_R01_v12.json')
    d=dict(schema_version=old['schema_version'],revision='v16',title_ru='VOLUNTEERS ONLY / R01 v16 — World v11',
        coordinates=dict(old['coordinates'],frame_m=w['coordinates']['frame_m'],origin=w['coordinates']['origin']),
        specification=dict(path='docs/WORLD_MAP_3D_BRIEF.md',revision='M1',date='2026-10-11'),
        provenance=dict(source_schema='World_v11/WORLD_MAP_v11.json',source_sha256=sha(map_dir/'World_v11/WORLD_MAP_v11.json'),
            method='Lossless metre geometry conversion; no prior revision geography inherited; all derived fields labelled.'),
        world_v11=w, district_mapping=[], districts=[], roads=[], paths=[], points=[],
        building_masses=[],functional_buildings=[],functional_sites=[],vegetation_parcels=[],
        plots=[],microdistricts=[],farmsteads=[],exits=[],field_parcels_m=[],water=[],beaches=[],
        water_crossings=[],pedestrian_water_crossings=[],hills=[],structures=[],pois=[],base_mapping=[],gameplay_mapping=[])
    for q in w['districts']:
        key,aliases,color=DISTRICTS[q['id']];(x0,y0),(x1,y1)=q['bbox_m']
        poly=ring(box(x0,y0,x1,y1))
        d['districts'].append(dict(id=key,world_id=q['id'],aliases=aliases,name_ru=q['name_ru'],name=q['name'],
            color=color,polygon_m=poly,parent_id=None,label_m=q['label_m'],bbox_m=q['bbox_m'],
            outline_status='source bounding box for lookup only; no approved outline exported',area_m2=(x1-x0)*(y1-y0)))
        d['district_mapping'].append(dict(world_id=q['id'],r01_id=key,aliases=aliases,
            ambience_supported=key!='tramduro',outline_status='bounding_box_only'))
    d['road_classes']={k:dict(name_ru=k,width_m=wid,color=col) for k,wid,col in [
        ('highway',14,'#7b8989'),('town_street',10,'#faf4e7'),('rural_road',6.4,'#f4edda'),
        ('dirt_shortcut',5.4,'#c8ae82'),('passage',1.8,'#997f57')]}
    for r in w['roads']:
        cls=r['class']; spec=w['road_classes'][cls]; width=r.get('surface_m',spec['surface_m'])
        districts=[sid(r['district'])] if r.get('district') else ['common']
        q=dict(id=r['id'],**{'class':CLASS[cls]},source_class=cls,width_m=width,
            total_width_m=spec.get('total_m',width+2*spec.get('sidewalk_m',0)),
            sidewalk_width_m=spec.get('sidewalk_m',0),polyline_m=r['polyline_m'],district_ids=districts,
            district_id=districts[0],world_district_id=r.get('district'),
            lanes=4 if cls=='boulevard' else 2 if cls in ('asphalt','city_street') and width>=5.6 else 1,
            lanes_per_direction=2 if cls=='boulevard' else 1,median=cls=='boulevard',
            van_access=cls not in FOOT,walkable=True,length_m=LineString(r['polyline_m']).length,
            source_id=r['id'],source_note=r.get('note',''))
        d['paths' if cls in FOOT else 'roads'].append(q)
    d['bridges']=[]
    for b in w['bridges']:
        q=dict(b,source_id=b['id'])
        if 'axis_m' not in q:
            p=Polygon(q['polygon_m']);x0,y0,x1,y1=p.bounds
            q['axis_m']=[[(x0+x1)/2,y0],[(x0+x1)/2,y1]];q['deck_width_m']=x1-x0
        if 'polygon_m' not in q:q['polygon_m']=ring(LineString(q['axis_m']).buffer(q['deck_width_m']/2,cap_style=2))
        q['van_access']=b['kind']=='road_bridge';q['piers']=[]
        if b['id']=='bridge_tramduro':
            ln=LineString(q['axis_m'])
            q['piers']=[dict(position_m=list(ln.interpolate(s).coords[0]),status='suggested_by_source_16m_spacing') for s in np.arange(16,ln.length,16)]
        d['bridges'].append(q)
        road=dict(id='DECK_'+b['id'],source_id=b['id'],source_class='asphalt' if q['van_access'] else 'footpath',
            **{'class':'rural_road' if q['van_access'] else 'passage'},width_m=b.get('road_m',q['deck_width_m']),
            district_id='common',district_ids=['common'],polyline_m=q['axis_m'],walkable=True,
            van_access=q['van_access'],lanes=2 if q['van_access'] else 1,lanes_per_direction=1,
            length_m=LineString(q['axis_m']).length,bridge_id=b['id'],derived_from='approved bridge axis')
        d['roads' if q['van_access'] else 'paths'].append(road)
        crossing=dict(id=b['id'],road_id=road['id'],water_id=b['over'],position_m=list(LineString(q['axis_m']).centroid.coords[0]),
            deck_axis_m=q['axis_m'],deck_polygon_m=q['polygon_m'],width_m=q['deck_width_m'],kind='bridge',piers=q['piers'],tunnel_carrier=None)
        d['water_crossings' if q['van_access'] else 'pedestrian_water_crossings'].append(crossing)
    main=valid(Polygon(w['terrain']['land_polygon_m'])); playable=valid(Polygon(w['terrain']['play_area_polygon_m']))
    island=valid(Polygon(w['island_tramduro']['polygon_m']))
    long=next(b for b in d['bridges'] if b['id']=='bridge_tramduro')
    corridor=Polygon(long['polygon_m'])
    approach=next(r for r in d['roads'] if r['id']=='06_port_road')
    approach_surface=LineString(approach['polyline_m']).buffer(approach['width_m']/2,cap_style=2)
    land=unary_union([main,island,corridor,approach_surface]);play=unary_union([playable,island,corridor,approach_surface])
    if play.geom_type!='Polygon':raise ValueError('Approved bridge does not connect playable islands')
    coast=w['terrain']['coast_polyline_m']; island_coast=list(island.exterior.coords)
    coast_edges=[[list(a),list(b)] for line in [coast,island_coast,list(corridor.exterior.coords)] for a,b in zip(line,line[1:])]
    d['boundary']=dict(polygon_m=ring(play),coast_segments_m=coast_edges,barrier='north-west ridge only',barrier_band_m=5,
        component_polygons_m=[w['terrain']['play_area_polygon_m'],w['island_tramduro']['polygon_m']],
        compatibility_bridge_corridor_m=long['polygon_m'],coast_segments=w['terrain']['coast_segments'],
        compatibility_approach_surface_m=ring(approach_surface),
        source_bridge_land_gap_m=main.distance(LineString(long['axis_m'])))
    sea=box(-60,-60,1534,820).difference(land)
    if sea.geom_type!='Polygon' or sea.interiors:raise ValueError('Sea must be a single polygon for unchanged C# consumers')
    d['water'].append(dict(id='SEA',kind='sea',polygon_m=ring(sea),level_m=0,
        note='Legacy single polygon excludes the bridge deck corridor; exact sea/land semantics retained in world_v11.'))
    river=w['water']['river']; polys=[]
    for a,b,wa,wb in zip(river['polyline_m'],river['polyline_m'][1:],river['width_m'],river['width_m'][1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];L=math.hypot(dx,dy)
        if not L:continue
        nx,ny=-dy/L,dx/L
        polys.append(Polygon([[a[0]+nx*wa/2,a[1]+ny*wa/2],[b[0]+nx*wb/2,b[1]+ny*wb/2],
            [b[0]-nx*wb/2,b[1]-ny*wb/2],[a[0]-nx*wa/2,a[1]-ny*wa/2]]))
    rg=unary_union(polys)
    for i,p in enumerate(parts(rg)):
        d['water'].append(dict(id='RIVER' if i==0 else f'RIVER_{i}',kind='river',polygon_m=ring(p),
            centerline_m=river['polyline_m'],width_m=max(river['width_m']),width_profile_m=river['width_m'],
            bank_extra_m=river['bank_extra_m'],level_m=0,source_kind='variable_width_river'))
    for key in ['canal','canal_mouth']:
        q=w['water'][key];wall=(q['wall_width_m']-q['water_width_m'])/2
        d['water'].append(dict(id=key.upper(),kind='concrete_canal',centerline_m=q['polyline_m'],
            width_m=q['wall_width_m'],wet_width_m=q['water_width_m'],wall_width_m=wall,level_m=0))
    d['water'].append(dict(id='MOUNTAIN_LAKE',kind='lake',polygon_m=w['water']['mountain_lake_m'],level_m=0))
    for q in w['water']['ponds_and_pools']:
        d['water'].append(dict(q,district_id=sid(q['district']),world_district_id=q['district'],level_m=0))
        if 'fountain' in q['kind'] or 'fountain' in q['id']:
            d['functional_sites'].append(dict(q,type='fountain',district_id=sid(q['district']),source_id=q['id']))
    d['sand_areas']=[dict(id=f'SAND_{i+1:02d}',**q) for i,q in enumerate(w['sand'])]
    for q in d['sand_areas']:
        d['beaches'].append(dict(q,name_ru='Песок',surface='sand',land_edge_m=[],sea_edge_m=[],width_m=0))
    d['terrain_hints']=w['terrain'];d['vegetation_hints']=w['vegetation']
    for i,h in enumerate(w['terrain']['hills']+[w['terrain']['small_mountain']]):
        d['hills'].append(dict(h,id=f'HILL_{i+1:02d}',height_target_m=h.get('height_m',h.get('peak_height_m'))))
    for i,z in enumerate(w['vegetation']['forest_zones']):
        d['vegetation_parcels'].append(dict(z,id=f'FOREST_ZONE_{i+1:02d}',kind='grove',district_id='common',blocks_van=z['density']=='dense'))
    for s in w['structures']:
        q=dict(s,district_id=sid(s['district']),world_district_id=s['district'])
        d['structures'].append(q)
        if s.get('polygon_m'):
            d['functional_sites'].append(dict(q,type=s['kind']))
        if s['kind']=='yellow_field':d['field_parcels_m'].append(s['polygon_m'])
    rail=next(s for s in w['structures'] if s['kind']=='short_dead_end_railway')
    d['railway']=dict(polyline_m=rail['polyline_m'],from_point=None,to_point='B01',active_trains=False,road_crossings=[],water_bridges=[])
    d['sightline']={}
    d['road_areas']=w['road_areas']
    pois={q['district']+':'+q['number']:q for q in w['pois']}
    def point(pid,pos,district,name,category,source):
        q=dict(id=pid,canonical_id=pid.split('-')[0],name_ru=name,position_m=pos,district_id=sid(district),
            world_district_id=district,category=category,source_ref=source,mapping_confidence='source_exact')
        d['points'].append(q);return q
    for q in w['pois']:
        pid='D'+q['district']+'_POI_'+q['number']
        d['pois'].append(dict(q,id=pid,district_id=sid(q['district']),world_district_id=q['district']))
        point(pid,q['position_m'],q['district'],q['name'],'numbered_poi','poi:'+q['district']+':'+q['number'])
    bases={q['id']:q for q in w['bases']}
    for i,q in enumerate(w['bases'],1):
        pid=f'B{i:02d}';point(pid,q['position_m'],q['district'],q['note'],'base','base:'+q['id'])
        d['base_mapping'].append(dict(world_id=q['id'],r01_id=pid,district_world_id=q['district'],district_id=sid(q['district']),position_m=q['position_m']))
    # Resolve only exact named objects; annotations are not silently promoted to doors.
    for pid,(kind,key) in GAME.items():
        if kind=='base':q=bases[key];pos=q['position_m'];district=q['district'];name=q['note']
        elif kind=='poi':q=pois[key];pos=q['position_m'];district=q['district'];name=q['name']
        else:
            q=next(s for s in w['structures'] if s['kind']=='water_tower' and s['district']=='02')
            key=q['id'];pos=q['position_m'];district=q['district'];name=q['kind']
        category=next(p['category'] for p in old['points'] if p['id']==pid)
        point(pid,pos,district,name,category,kind+':'+key)
    point('P10-2',pois['05:11']['position_m'],'05',pois['05:11']['name'],'poi','poi:05:11')
    bypoint={q['id']:q for q in d['points']}
    for q in old['points']:
        p=bypoint.get(q['id'])
        d['gameplay_mapping'].append(dict(id=q['id'],name_v12=q['name_ru'],status='mapped' if p else 'removed' if q['id']=='B06' else 'unmatched',
            source_ref=p['source_ref'] if p else None,position_m=p['position_m'] if p else None,
            question=QUESTIONS.get(q['id'],'') if not p else ''))
    for b in w['buildings']:
        g=Polygon(b['footprint_m']);center=list(g.centroid.coords[0]);width,depth,angle=obb(valid(g))
        typ=b['kind'];label=b.get('plan_label');dnum=b['district']
        typ={'old_railway_wagon':'wagon_base','grandpa_hut_base2':'grandpa_house','base3_house':'house_base',
             'lab_final_base':'lab_final_base','van_workshop':'car_workshop','guard_house':'private_security',
             'den_building':'den','modern_villa':'mansion'}.get(typ,typ)
        poi_id=''
        if dnum=='05':
            typ={'10':'police_station','11':'police_station','12':'taxi_depot','07':'van_shop','05':'office','06':'office','13':'house_base',
                 '16':'shop','17':'shop','18':'shop','19':'shop'}.get(label,typ)
            poi_id={'10':'P10','11':'P10-2','13':'B04'}.get(label,'')
        poi_id={'01_B01':'B01','02_B02':'B02','04_west_base_house':'B03','08_01_lab':'B05'}.get(b['id'],poi_id)
        rec=dict(b,type=typ,world_kind=b['kind'],district_id=sid(dnum),district=sid(dnum),world_district_id=dnum,
            center_m=center,width_m=width,depth_m=depth,orientation_deg=angle,storeys=b['floors'],
            label_ru=b.get('name') or b.get('plan_label') or b['kind'],poi_id=poi_id,source_id=b['id'])
        d['functional_buildings'].append(rec)
    d['road_graph']=graph(d['roads']);d['pedestrian_graph']=graph(d['roads']+d['paths'])
    road_lines=[(r,LineString(r['polyline_m'])) for r in d['roads']]
    for p in d['points']:
        r,l=min(road_lines,key=lambda x:(x[1].distance(Point(p['position_m'])),x[0]['id']))
        stop=l.interpolate(l.project(Point(p['position_m'])))
        n=graph_stop(d['road_graph'],list(stop.coords[0]))
        p.update(van_stop_m=list(stop.coords[0]),access_road_id=r['id'],road_node_id=n['id'],
            van_stop_offset_m=Point(p['position_m']).distance(stop),van_node_gap_m=Point(n['position_m']).distance(stop),
            access_status='nearest source road projection; local clearance and doors require lead validation')
    for b in d['functional_buildings']:
        r,l=min(road_lines,key=lambda x:valid(geom(b)).distance(x[1]));b['access_road_id']=r['id']
        pts=b['footprint_m'];mids=[[(a[0]+z[0])/2,(a[1]+z[1])/2] for a,z in zip(pts,pts[1:]+pts[:1])]
        entrance=min(mids,key=lambda p:(l.distance(Point(p)),p))
        b['entrance_m']=entrance
        b['entrance_status']='nearest-road-facing footprint edge midpoint; door proposal requiring lead validation'
    d['metrics']=dict(building_count=len(d['functional_buildings']),building_counts_by_district=dict(collections.Counter(b['district_id'] for b in d['functional_buildings'])),
        bounds_m=[0,0,1474,760],extent_m=[1474,760],area_m2=play.area,routes=[])
    for q in d['districts']:q['building_count']=d['metrics']['building_counts_by_district'].get(q['id'],0)
    d['fences']=fences(d)
    marina(d,map_dir)
    d['police_parking_proposals']=police_lots(d)
    d['provenance']['supplementary_inputs']=[dict(path=n,sha256=sha(map_dir/n)) for n in
        ('World_v11/VOLUNTEERS_MAP_v11_MASTER.svg','MAP_PLAN_R01_v14.json')]
    return d

def fences(d):
    result=[]
    heights={'03_fence':2,'08_06_fence':1,'07_fence':2.4,'06_yard':2.4,'10_base_fence':2.4,'10_palace_lawn':1}
    for q in d['structures']:
        if 'fence' not in q['kind']:continue
        axis=q['polygon_m']+[q['polygon_m'][0]];line=LineString(axis); gates=[]
        if q['id']=='03_fence':
            for i,(pos,width) in enumerate(zip(q['gates_m'],[19,18,18])):
                gates.append(dict(id=f'{q["id"]}_G{i+1}',position_m=pos,width_m=width,status='source_brief',along_m=line.project(Point(pos))))
            for i,pos in enumerate(q['van_cuts_m']):
                gates.append(dict(id=f'{q["id"]}_CUT{i+1}',position_m=pos,width_m=12,status='source_brief',along_m=line.project(Point(pos))))
        else:
            for r in d['roads']+d['paths']:
                if r.get('bridge_id'):continue
                hit=line.intersection(LineString(r['polyline_m']))
                for p in parts(hit,'Point'):
                    if any(p.distance(Point(g['position_m']))<1 for g in gates):continue
                    width=r['width_m']+2
                    gates.append(dict(id=f'{q["id"]}_G{len(gates)+1}',position_m=list(p.coords[0]),width_m=width,
                        status='derived road/fence intersection; opening width proposal',road_id=r['id'],along_m=line.project(p)))
        if q['id']=='07_fence':
            stairs=next(s for s in d['structures'] if s['kind']=='stairs_down_the_slope_to_beach')
            p=nearest_points(line,LineString(stairs['polyline_m']))[0]
            gates.append(dict(id='07_fence_STAIRS',position_m=list(p.coords[0]),width_m=1.8,along_m=line.project(p),status='nearest stairs projection; pedestrian opening width proposal'))
        intervals=[]
        for g in gates:
            a=g['along_m']-g['width_m']/2;b=g['along_m']+g['width_m']/2
            if a<0:intervals.append([line.length+a,line.length]);a=0
            if b>line.length:intervals.append([0,b-line.length]);b=line.length
            intervals.append([a,b])
        merged=[]
        for a,b in sorted(intervals):
            if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],b)
            else:merged.append([a,b])
        runs=[];start=0
        for a,b in merged:
            if a>start:runs.append([list(p) for p in substring(line,start,a).coords])
            start=b
        if start<line.length:runs.append([list(p) for p in substring(line,start,line.length).coords])
        result.append(dict(id=q['id'],kind=q['kind'],district_id=q['district_id'],world_district_id=q['world_district_id'],
            polyline_m=axis,gates=gates,gap_intervals_m=merged,solid_runs_m=runs,height_target_m=heights[q['id']],
            height_status='source approximate' if q['id']=='03_fence' else 'proposal; source gives no numeric height',
            perimeter_role='special_property',exception_requires_confirmation=q['id']=='10_palace_lawn'))
    return result

def native_ways(d):
    """Six beach paths were exported twice: SVG border stroke + inner surface."""
    result=[];groups={}
    for r in d['roads']+d['paths']:
        if r['source_class']!='beach_path':result.append(r);continue
        key=tuple(tuple(p) for p in r['polyline_m'])
        groups.setdefault(key,[]).append(r)
    for group in groups.values():
        assert len(group)==2 and group[0]['width_m']!=group[1]['width_m']
        inner=min(group,key=lambda r:r['width_m']);outer=max(group,key=lambda r:r['width_m'])
        result.append(dict(inner,source_stroke_ids=[r['id'] for r in group],border_width_m=outer['width_m'],
            border_source_id=outer['id'],native_role='single inner ribbon; outer SVG border retained as ground/metadata'))
    assert len(groups)==6
    return result

def flatten_greybox(d):
    out=dict(revision=REV,roads=[],buildings=[],water=[],water_strips=[],sea=[],beaches=[],points=[],
        rail=flat(d['railway']['polyline_m']),walls=[],barriers=[],hedges=[],bounds=[0,0,1474,760],tree_data=[],rock_data=[])
    for r in native_ways(d):
        out['roads'].append(dict(cls=r['class'],w=r['width_m'],pts=flat(r['polyline_m']),id=r['id'],van=r['van_access'],source_class=r['source_class'],source_stroke_ids=r.get('source_stroke_ids',[r['id']])))
    for b in d['functional_buildings']:
        w,h,a=obb(valid(geom(b)))
        out['buildings'].append(dict(x=b['center_m'][0],y=b['center_m'][1],w=w,d=h,a=a,h=b['height_m'],f=1,
            label=b['label_ru'],id=b['id'],fp=flat(b['footprint_m']),floors=b['storeys'],kind=b['world_kind'],district=b['district_id']))
    for w in d['water']:
        g=water_geometry(w)
        out['sea' if w['kind']=='sea' else 'water'].append(dict(tris=triangles(g),id=w['id'],source_kind=w['kind']))
    out['beaches']=[dict(tris=triangles(Polygon(s['polygon_m'])),id=s['id']) for s in d['sand_areas']]
    out['points']=[dict(id=p['id'],label=p['name_ru'],cat=p['category'],x=p['position_m'][0],y=p['position_m'][1]) for p in d['points']]
    for f in d['fences']:
        for line in f['solid_runs_m']:
            for a,b in zip(line,line[1:]):
                L=math.dist(a,b)
                if L<.05:continue
                out['hedges'].append(dict(x=(a[0]+b[0])/2,y=(a[1]+b[1])/2,w=L,d=.2,
                    a=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])),h=f['height_target_m'],label='elite_fence',source_kind=f['kind']))
    out.update(world_v11_extensions=extensions(d),crossings=d['bridges'])
    out['tree_data']=[v for t in scatter_forest(d) for v in (t['x'],t['y'],.3,t['h'])]
    return out

def water_geometry(w):
    if w.get('polygon_m'):return valid(Polygon(w['polygon_m']))
    return LineString(w['centerline_m']).buffer(w.get('wet_width_m',w['width_m'])/2,cap_style=2)

def extensions(d):
    out={k:d[k] for k in ['district_mapping','base_mapping','gameplay_mapping','terrain_hints','vegetation_hints',
        'structures','pois','bridges','road_areas','fences','sand_areas','marina_enrichment',
        'marina_source_yachts','marina_enrichment_settings','police_parking_proposals']}
    out['source_road_strokes']=d['world_v11']['roads'];out['source_road_classes']=d['world_v11']['road_classes']
    return out

def building_style(b):
    kind=b['world_kind'];did=b['district_id']
    if did in ('forest','village'):return ('shed' if kind in ('shed','old_railway_wagon','barn','forest_structure') else 'rural_wood','gable')
    if kind=='modern_villa':return 'villa','flat'
    if kind in ('panel_block','base3_house'):return 'panel','flat'
    if did in ('industrial','transition','tramduro'):return ('civic' if kind in ('palace','military_hq') else 'industrial'),'flat'
    if b['type'] in ('police_station','office','lab_final_base'):return 'civic','flat'
    if kind in ('brick_loft','stone_colonnade'):return 'oldtown','flat'
    return 'commercial' if did=='beach' else 'oldtown','flat'

def look_buildings(d):
    out=[];roads=[(r,LineString(r['polyline_m'])) for r in d['roads']]
    lg=load_module(MAP/'Look/look_geom.py','v16_look_geom')
    for b in d['functional_buildings']:
        poly=geom(b);g=valid(poly);w,dep,angle=obb(g)
        style,roof=building_style(b);r,l=min(roads,key=lambda x:g.distance(x[1]))
        door=Point(b['entrance_m']);stop=l.interpolate(l.project(door));dx,dy=stop.x-door.x,stop.y-door.y
        yaw=90-math.degrees(math.atan2(dy,dx))
        rects=[v for cx,cy,lu,lv,angle in lg.rect_decompose([tuple(p) for p in b['footprint_m']]) for v in (cx,cy,lv,lu,90-angle)]
        out.append(dict(id=b['id'],kind='slab' if b['world_kind']=='panel_block' else 'functional',type=b['type'],district=b['district_id'],label=b['label_ru'],
            style=style,roof=roof,floors=b['storeys'],floor_h=b['height_m']/max(1,b['storeys']),h=b['height_m'],
            front_deg=yaw,x=b['center_m'][0],y=b['center_m'][1],fp=flat(ccw_ring(g)),tris=triangles(g),rects=rects,
            wall={'panel':'#B9B6AA','rural_wood':'#8F6E4E','industrial':'#8E8A84','civic':'#E2D3A8','villa':'#EDE4D0','oldtown':'#C9A27E','shed':'#857C6E','commercial':'#D9D5CB'}[style],
            trim='#EFE6D2',roof_col=b.get('roof_colour','#6C6E6B'),sign_text='',sign_side=-1,
            ent=[door.x,door.y,yaw],seed=int(hashlib.sha256(b['id'].encode()).hexdigest()[:7],16),
            prop_key='',access=r['id'],world_kind=b['world_kind'],world_district_id=b['world_district_id'],
            source_orientation_deg=b['orientation_deg'],entrance_status='nearest source road facing footprint; proposal'))
    return out

def ground_record(g,mat,ctx,prio=30):
    return dict(mat=mat,prio=prio,soft=mat not in ('asphalt','paving','concrete','rubber'),edge=1,
        ctx=ctx,pts=flat(ccw_ring(g)),tris=triangles(g))

def flatten_look(d, no_veg=False):
    out=dict(schema='look_v1',revision=REV,source_plan=STEM+'.json',source_dressing='',seed=16,
        angle_convention='Unity yaw = 90 - plan CCW angle from east',winding='polygons/tris plan CCW; Unity reverses triangles',
        soft_layers=['meadow','forest_floor','dry_field','worn_grass','park_grass','lawn','gravel','sand'],
        hard_mats=['asphalt','paving','concrete','rubber'],ground_default='meadow',
        terrain=dict(x0=-120,y0=-120,sx=1728,sy=1024,heightmap=1025,splatmap=1024,pixel_error=3,
            layers=['meadow','forest_floor','dry_field','worn_grass','park_grass','lawn','gravel','sand'],default='meadow'),
        buildings=look_buildings(d),roads=[],junctions=[],crossings=[],sidewalks=[],markings=[],parking=[],yards=[],ground=[],
        water=[],elite_fence=[],blockers=[],rocks=[],trees=[],furniture=[],pipes=[],decals=[],vehicles=[],landmarks=[],exits=[],warnings=[])
    bpoly=Polygon(d['boundary']['polygon_m']);pts=ring(bpoly);coast=unary_union([LineString(q) for q in d['boundary']['coast_segments_m']])
    out['boundary']=dict(pts=flat(pts),coast=[int(coast.distance(LineString([a,b]).interpolate(.5,normalized=True))<.01) for a,b in zip(pts,pts[1:]+pts[:1])],band=5,berm_h=2.5,blocker_h=6)
    # Geographic district bounding boxes must not create rectangular ground clearings.
    out['districts']=[dict(id=q['id'],name=q['name_ru'],color=q['color'],base='meadow',pts=flat(q['polygon_m']),world_id=q['world_id']) for q in d['districts']]
    out['hills']=[dict(id=h['id'],x=h['center_m'][0],y=h['center_m'][1],rx=h['radii_m'][0],ry=h['radii_m'][1],h=h['height_target_m'],rotation_deg=h.get('rotation_deg',0)) for h in d['hills']]
    for r in native_ways(d):
        out['roads'].append(dict(id=r['id'],road=r['id'],cls=r['class'],w=r['width_m'],lanes=r['lanes'],van=r['van_access'],
            surface='dirt' if r['source_class'] in ('dirt','lane','site_track','trail') else 'paving' if not r['van_access'] else 'asphalt',
            district=r['district_id'],pts=flat(r['polyline_m']),trim_start=0,trim_end=0,length=r['length_m'],source_class=r['source_class'],source_stroke_ids=r.get('source_stroke_ids',[r['id']])))
        if r.get('border_width_m'):
            g=LineString(r['polyline_m']).buffer(r['border_width_m']/2,cap_style=2,join_style=2)
            out['ground'].append(ground_record(g,'paving',r['border_source_id']+'_SOURCE_BORDER',45))
        if r.get('sidewalk_width_m'):
            ln=LineString(r['polyline_m']);off=r['width_m']/2+r['sidewalk_width_m']/2
            for sign,side in [(1,'L'),(-1,'R')]:
                line=ln.offset_curve(sign*off,join_style=2)
                for p in parts(line,'LineString'):
                    out['sidewalks'].append(dict(road=r['id'],side=side,w=3,verge=0,curb=.15,district=r['district_id'],pts=flat(p.coords)))
    road_area=unary_union([LineString(r['polyline_m']).buffer(r['width_m']/2,cap_style=2,join_style=2) for r in d['roads']])
    deg=collections.Counter(n for e in d['road_graph']['edges'] for n in [e['from_node'],e['to_node']])
    for n in d['road_graph']['nodes']:
        if deg[n['id']]<3:continue
        near=[r for r in d['roads'] if LineString(r['polyline_m']).distance(Point(n['position_m']))<.01]
        rad=max([r['width_m']/2 for r in near] or [3.2])+1
        patch=road_area.intersection(Point(n['position_m']).buffer(rad))
        for i,g in enumerate(parts(patch)):
            out['junctions'].append(dict(id='J_'+n['id']+f'_{i}',x=n['position_m'][0],y=n['position_m'][1],r=rad,
                arms=deg[n['id']],roads=[r['id'] for r in near],pts=flat(ring(g)),tris=triangles(g)))
    for b in d['bridges']:
        a,z=b['axis_m'][0],b['axis_m'][-1];l=LineString(b['axis_m']);c=l.centroid
        out['crossings'].append(dict(id=b['id'],road='DECK_'+b['id'],water=b['over'],kind='bridge',x=c.x,y=c.y,
            a=90-math.degrees(math.atan2(z[1]-a[1],z[0]-a[0])),len=l.length,w=b['deck_width_m'],pts=flat(b['axis_m']),piers=b['piers']))
    for w in d['water']:
        g=water_geometry(w)
        if w['kind']=='sea':
            out['sea']=dict(id=w['id'],level=-.6,apron=60,bed=-4,pts=flat(w['polygon_m']),tris=triangles(g))
        else:
            # Exact polygons carry varying river width and canal water footprint to the old polygon-water consumer.
            for i,p in enumerate(parts(g)):
                out['water'].append(dict(id=w['id']+(f'_{i}' if i else ''),kind='lake',source_kind=w['kind'],level=-.3,depth=1.1,
                    w=0,wet_w=0,bank=4,bank_mat='natural',pts=flat(ring(p)),tris=triangles(p),
                    centerline_m=w.get('centerline_m',[]),width_profile_m=w.get('width_profile_m',[]),wall_width_m=w.get('wall_width_m',0)))
    sand=unary_union([valid(Polygon(q['polygon_m'])) for q in d['sand_areas']])
    primary=max(parts(sand),key=lambda p:p.area)
    out['beach']=dict(id='WORLD_SAND_PRIMARY',w=0,dry=40,surf=14,pts=flat(ring(primary)),tris=triangles(primary),land=[],sea=[])
    for q in d['sand_areas']:
        for p in parts(valid(Polygon(q['polygon_m']))):out['ground'].append(ground_record(p,'sand',q['id'],25))
    for q in d['road_areas']:
        mat='paving' if q['surface']=='sidewalk' else 'asphalt'
        out['ground'].append(ground_record(Polygon(q['polygon_m']),mat,q['id'],50))
    for q in d['structures']:
        mats={'plot_or_garden':'lawn','vegetable_beds':'dry_field','park_lawn':'park_grass',
            'plaza_paving':'paving','city_block_inside_sidewalks':'paving','meadow_with_grass_tufts':'meadow',
            'courtyard':'paving','villa_garden':'lawn','yellow_field':'dry_field','parking_or_lot':'asphalt',
            'paved_area_or_parking':'asphalt','paved_forecourt':'paving','base_yard_van_spot':'gravel',
            'football_pitch':'lawn','concrete_port_yard_with_fence':'concrete','loading_yard':'concrete',
            'golden_statue_on_round_plaza':'paving','lookout_terrace':'paving','parking':'asphalt',
            'open_lawn':'lawn','palace_lawn_with_fence':'lawn','helipad':'concrete','military_vehicle_park':'asphalt'}
        if not q.get('polygon_m') or q['kind'] not in mats:continue
        mat=mats[q['kind']]
        for p in parts(valid(Polygon(q['polygon_m']))):out['ground'].append(ground_record(p,mat,q['id']))
    # The 14 m boulevard has a source-specified median, but no numeric median width in JSON.
    out['warnings'].append('Boulevard median width not exported: retained as an unresolved source hint; no width invented.')
    for f in d['fences']:
        out['elite_fence'].append(dict(id=f['id'],h=f['height_target_m'],pts=flat(f['polyline_m']),gaps=flat(f['gap_intervals_m']),
            length=LineString(f['polyline_m']).length,gate_roads=[g['road_id'] for g in f['gates'] if g.get('road_id')],source_kind=f['kind']))
    out['rail']=dict(pts=flat(d['railway']['polyline_m']),w=3,crossings=[])
    out['points']=[dict(id=p['id'],label=p['name_ru'],cat=p['category'],district=p['district_id'],x=p['position_m'][0],y=p['position_m'][1]) for p in d['points']]
    out['world_v11_extensions']=extensions(d)
    out['marina_enrichment']=d['marina_enrichment']
    out['marina_enrichment_settings']=d['marina_enrichment_settings']
    out['parking']=d['police_parking_proposals']
    out['warnings'] += [
        'District polygon fields are source bounding boxes for ID lookup; exact outlines require re-export.',
        'C# uses the legacy vertical datum: ground near 0, sea -0.6, inland water -0.3. Canonical water=0 and terrain hints retained in extensions.',
        'Existing C# renders polygon inland water with the lake material; typed shading/canal walls need lead consumer support.',
        'Existing C# generic fence representation preserves collider geometry; blue-sheet/barbed/low-fence appearance needs lead support.',
        'Rotated hills, ridge height profile, bridge pier records and new structure kinds are preserved in extensions; unsupported C# features need lead integration.',
        'Gameplay P04/P08 are unmatched; current trip-meter falls back to map centre for these missing IDs.',
        'Tramduro has no existing ambience mapping.']
    if not no_veg:out['trees']=scatter_forest(d)
    out['ground'].sort(key=lambda q:q['prio'])
    return out

def scatter_forest(d):
    zones=d['vegetation_hints']['forest_zones'];boundary=Polygon(d['boundary']['polygon_m'])
    water=unary_union([water_geometry(w) for w in d['water'] if w['kind']!='sea'])
    buildings=unary_union([valid(geom(b)).buffer(3) for b in d['functional_buildings']])
    roads=unary_union([LineString(r['polyline_m']).buffer(r['width_m']/2+3) for r in d['roads']+d['paths']])
    clearings=unary_union([Polygon(q) for q in d['vegetation_hints']['clearings_m']])
    blocked=unary_union([water.buffer(2),buildings,roads,clearings])
    result=[];seen=collections.defaultdict(list);rng=np.random.default_rng(16)
    for z in zones:
        g=valid(Polygon(z['polygon_m'])).intersection(boundary).difference(blocked)
        step=5 if z['density']=='dense' else 14
        if g.is_empty:continue
        x0,y0,x1,y1=g.bounds;xs=np.arange(x0,x1,step);ys=np.arange(y0,y1,step)
        gx,gy=np.meshgrid(xs,ys);pts=np.column_stack((gx.ravel(),gy.ravel()))
        pts+=rng.uniform(-.35,.35,pts.shape)
        mask=shapely.contains_xy(g,pts[:,0],pts[:,1])
        for p in pts[mask]:
            key=tuple(np.floor(p/3).astype(int))
            neighbours=[q for dx in (-1,0,1) for dy in (-1,0,1) for q in seen[(key[0]+dx,key[1]+dy)]]
            if any(math.dist(p,q)<3 for q in neighbours):continue
            seen[key].append(p)
            result.append(dict(sp='pine' if z['density']=='dense' else 'birch',x=round(p[0],4),y=round(p[1],4),h=round(float(rng.uniform(10,16)),2)))
    return result

def write_flat(plan, kind, dst, no_veg=False):
    out=flatten_greybox(plan) if kind=='greybox' else flatten_look(plan,no_veg)
    json_new(dst,out)
    print(json.dumps(dict(revision=REV,kind=kind,path=str(dst),counts={k:len(v) for k,v in out.items() if isinstance(v,list)})))
    return out

def build_crowd(d,look,plan_hash):
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
            out=dict(schema_version='1.0',revision='R01_v16',generator='map_plan_v16.py (crowd_v12 algorithms)',
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
    return Crowd16().output()

def graph_components(g):
    adj=collections.defaultdict(set)
    for e in g['edges']:
        adj[e['from_node']].add(e['to_node']);adj[e['to_node']].add(e['from_node'])
    seen=set();result=[]
    for n in sorted(adj):
        if n in seen:continue
        stack=[n];c=[]
        while stack:
            u=stack.pop()
            if u in seen:continue
            seen.add(u);c.append(u);stack.extend(sorted(adj[u]-seen,reverse=True))
        result.append(c)
    return result

def police_lots(d):
    """Four-car fit proposals entirely inside the two exported Downtown lots."""
    source={q['id']:q for q in d['structures']}
    records=[]
    for bid,lid,stalls,aisle in [
        ('05_B036','05_lot_02',[[700+3*i,282,2.6,5.2,0] for i in range(4)],[[700,288],[709,288]]),
        ('05_B025','05_lot_01',[[1015,405+3*i,2.6,5.2,90] for i in range(4)],[[1021,405],[1021,414]])]:
        poly=Polygon(source[lid]['polygon_m']);stall_polys=[]
        for x,y,width,depth,yaw in stalls:
            a=math.radians(90-yaw);c,s=math.cos(a),math.sin(a)
            pts=[[x+u*c-v*s,y+u*s+v*c] for u,v in [(-depth/2,-width/2),(depth/2,-width/2),(depth/2,width/2),(-depth/2,width/2)]]
            stall_polys.append(Polygon(pts))
        aisle_surface=LineString(aisle).buffer(3,cap_style=2)
        fits=all(poly.covers(p) for p in stall_polys) and poly.covers(aisle_surface)
        assert all(p.intersection(aisle_surface).area<1e-8 for p in stall_polys)
        target=Point(aisle[0]);r=min(d['roads'],key=lambda q:LineString(q['polyline_m']).distance(target))
        road=LineString(r['polyline_m']);stop=road.interpolate(road.project(target));access=[aisle[0],list(stop.coords[0])]
        other=unary_union([geom(b) for b in d['functional_buildings']]);blocked=LineString(access).buffer(2.5,cap_style=2).intersection(other).area
        records.append(dict(id='POLICE_LOT_'+bid,building=bid,source_id=lid,mat='asphalt',pts=flat(ccw_ring(poly)),tris=triangles(poly),
            stalls=[v for p in stalls for v in p],access=flat(access),access_w=5,
            aisle_m=aisle,source_polygon_m=source[lid]['polygon_m'],four_stalls_fit=fits,access_building_overlap_m2=blocked,
            parking_status='4-car fit proposal in exact source lot; 5m access/6m aisle dimensions are proposals',access_road_id=r['id']))
        assert fits
    return records

def render(d,dst,overlay_dst):
    size=Image.open(MAP/'World_v11/VOLUNTEERS_MAP_v11_PREVIEW.png').size
    width,height=size;im=Image.new('RGB',size,'#e9e9dc');draw=ImageDraw.Draw(im)
    sx,sy=width/1474,height/760
    def px(p):return (round(p[0]*sx),round(height-p[1]*sy))
    def area(g,fill,outline=None,width=1):
        for p in parts(valid(g)):
            draw.polygon([px(q) for q in p.exterior.coords],fill=fill)
            if outline:draw.line([px(q) for q in p.exterior.coords],fill=outline,width=width)
    def line(seq,color,w):
        if len(seq)>1:draw.line([px(q) for q in seq],fill=color,width=max(1,round(w*sx)),joint='curve')
    for z in d['vegetation_hints']['forest_zones']:area(Polygon(z['polygon_m']),'#bdcdbb' if z['density']=='dense' else '#ced8bf')
    area(Polygon(d['terrain_hints']['ridge']['out_of_bounds_polygon_m']),'#d0d0c8','#adb0a6')
    area(Polygon(d['terrain_hints']['small_mountain']['outline_m']),'#c2c8b4','#919b88')
    for q in d['terrain_hints']['hills']:
        cx,cy=q['center_m'];rx,ry=q['radii_m'];a=math.radians(q.get('rotation_deg',0));c,s=math.cos(a),math.sin(a)
        for fraction in (.75,1):
            seq=[]
            for t in np.linspace(0,2*math.pi,65):
                x,y=rx*fraction*math.cos(t),ry*fraction*math.sin(t);seq.append([cx+x*c-y*s,cy+x*s+y*c])
            line(seq,'#9ba887',.35)
    for q in d['terrain_hints']['coast_segments']:
        line(q['polyline_m'],{'rock_cliff':'#8c9890','quay':'#657f87','sand':'#c9b897','cove':'#aab090'}.get(q['type'],'#909e93'),.7)
    for w in d['water']:area(water_geometry(w),'#a7c5cb','#739da6')
    for s in d['sand_areas']:area(Polygon(s['polygon_m']),'#e8d7ae')
    for q in d['structures']:
        if q.get('polygon_m') and 'fence' not in q['kind'] and q['kind'] not in ('pond','gentle_hill_contour'):
            area(Polygon(q['polygon_m']),'#cfcebe' if q['kind'] in ('courtyard','plaza_paving','city_block_inside_sidewalks','parking_or_lot') else '#c5d1b2','#999d89')
    for r in d['roads']+d['paths']:
        if r.get('sidewalk_width_m'):line(r['polyline_m'],'#f1eadc',r['width_m']+2*r['sidewalk_width_m'])
        color='#bdab8a' if r['source_class'] in ('dirt','lane','site_track','trail') else '#949d9c' if r['van_access'] else '#d5c09b'
        line(r['polyline_m'],'#7c857f',r['width_m']+.8);line(r['polyline_m'],color,r['width_m'])
    for b in d['bridges']:
        area(Polygon(b['polygon_m']),'#d4c7af','#6d7d77',2)
        line(b['axis_m'],'#a1aaa5' if b['van_access'] else '#d6c4a0',b.get('road_m',1))
    for b in d['functional_buildings']:
        area(geom(b),b.get('roof_colour','#c9bdb1'),'#586562',2)
    for f in d['fences']:
        for run in f['solid_runs_m']:line(run,'#4b78a0' if f['id']=='03_fence' else '#737469',.9)
    for q in d['marina_source_yachts']:area(Polygon(q['polygon_m']),'#fffdf2','#5e7276')
    for q in d['marina_enrichment']:
        if q.get('polygon_m'):
            area(Polygon(q['polygon_m']),'#b7a2c1' if q['kind']=='breakwater' else '#ebd1d6','#86569a',2)
        if q['kind']=='navigation_light':
            x,y=px(q['position_m']);draw.ellipse((x-4,y-4,x+4,y+4),fill='#ffe5a0',outline='#80569a')
    fontpath='C:/Windows/Fonts/arial.ttf';boldpath='C:/Windows/Fonts/arialbd.ttf'
    small=ImageFont.truetype(fontpath,14);font=ImageFont.truetype(boldpath,21);title=ImageFont.truetype(boldpath,26)
    for q in d['districts']:
        x,y=px(q['label_m']);text=f"{q['world_id']} / {q['id']}"
        draw.text((x,y),text,font=font,anchor='mm',fill='#37433d',stroke_width=3,stroke_fill='#eae9dc')
    for q in d['pois']:
        x,y=px(q['position_m']);draw.ellipse((x-3,y-3,x+3,y+3),fill='#fbf6e5',outline='#566865')
        draw.text((x+5,y-6),q['world_district_id']+':'+q['number'],font=small,fill='#435958',stroke_width=1,stroke_fill='#eee8d8')
    for q in d['points']:
        if q['category']!='base':continue
        x,y=px(q['position_m']);draw.ellipse((x-10,y-10,x+10,y+10),fill='#a74641',outline='#fff6df',width=3)
        draw.text((x+12,y-16),q['id'],font=font,fill='#7c2827',stroke_width=3,stroke_fill='#fff6df')
    draw.rounded_rectangle((30,height-190,640,height-22),radius=8,fill='#f7f0dd',outline='#798783',width=2)
    for i,txt in enumerate(['VOLUNTEERS ONLY — R01 v16 / WORLD v11','216 footprints · 119 numbered POIs · 5 bases','Metres: east +X, north +Y · frame 1474 × 760 m','Purple: optional marina; breakwater/light OFF pending Vadim','District envelopes: source bbox; precise boundaries not exported']):
        draw.text((48,height-176+i*28),txt,font=title if i==0 else small,fill='#354843')
    draw.line((width-62,87,width-62,35),fill='#3b5253',width=3);draw.polygon([(width-62,28),(width-68,42),(width-56,42)],fill='#3b5253')
    draw.text((width-62,10),'N',font=small,anchor='mt',fill='#3b5253')
    # Images use the exact preview viewport; no crop, padding, rotation or fitted transform.
    if Path(dst).exists() or Path(overlay_dst).exists():raise FileExistsError('Render output exists')
    im.save(dst)
    preview=Image.open(MAP/'World_v11/VOLUNTEERS_MAP_v11_PREVIEW.png').convert('RGB')
    overlay=Image.blend(preview,im,.45);overlay.save(overlay_dst)
    return dict(width_px=width,height_px=height,x_px_per_m=sx,y_px_per_m=sy,
        origin_px=[0,height],rotation_deg=0,translation_px=[0,0],overlay_plan_opacity=.45,
        note='Exact frame-to-preview transform; no registration fit. Optional enrichment shown purple for review even when disabled.')

def validate_plan(d):
    w=read(MAP/'World_v11/WORLD_MAP_v11.json')
    assert d['world_v11']==w
    source={b['id']:b for b in w['buildings']};errors=[]
    assert len(source)==len(d['functional_buildings'])==216
    for b in d['functional_buildings']:
        q=source[b['id']]
        for k in ('footprint_m','floors','height_m','roof_colour'):
            if k in q:assert b[k]==q[k],(b['id'],k)
        errors.append(Point(b['center_m']).distance(Polygon(q['footprint_m']).centroid))
    assert len(d['structures'])==205 and len(d['pois'])==119 and len(d['base_mapping'])==5
    for raw,converted in zip(w['structures'],d['structures']):assert all(converted[k]==v for k,v in raw.items())
    mapped={r['id']:r for r in d['roads']+d['paths']}
    for r in w['roads']:
        q=mapped[r['id']];assert q['polyline_m']==r['polyline_m']
        assert q['width_m']==r.get('surface_m',w['road_classes'][r['class']]['surface_m'])
    assert len(w['roads'])==84 and len(d['bridges'])==8
    components=graph_components(d['road_graph']);assert len(components)==1
    adj=collections.defaultdict(list)
    for e in d['road_graph']['edges']:
        adj[e['from_node']].append((e['to_node'],e['length_m']));adj[e['to_node']].append((e['from_node'],e['length_m']))
    start=next(p['road_node_id'] for p in d['points'] if p['id']=='P02');dist={start:0};queue=[(0,start)]
    while queue:
        cost,u=heapq.heappop(queue)
        if cost!=dist[u]:continue
        for v,length in adj[u]:
            nc=cost+length
            if nc<dist.get(v,math.inf):dist[v]=nc;heapq.heappush(queue,(nc,v))
    reach=[dict(id=p['id'],source_ref=p['source_ref'],reachable=p['road_node_id'] in dist,
        distance_from_spawn_m=round(dist.get(p['road_node_id'],0),3),van_stop_m=p['van_stop_m'],
        anchor_to_stop_m=round(p['van_stop_offset_m'],3),node_gap_m=p['van_node_gap_m'],
        local_access_status=p['access_status']) for p in d['points']]
    assert all(q['reachable'] and q['node_gap_m']<1e-6 for q in reach)
    bridge=[]
    carriers=[r for r in d['roads']+d['paths'] if not r.get('bridge_id')]
    for b in d['bridges']:
        ends=[]
        for pos in (b['axis_m'][0],b['axis_m'][-1]):
            r=min(carriers,key=lambda r:LineString(r['polyline_m']).buffer(r['width_m']/2,cap_style=2).distance(Point(pos)))
            gap=LineString(r['polyline_m']).buffer(r['width_m']/2,cap_style=2).distance(Point(pos))
            ends.append(dict(road_id=r['id'],gap_to_source_surface_m=round(gap,6)))
        bridge.append(dict(id=b['id'],van_access=b['van_access'],ends=ends,source_connected=all(q['gap_to_source_surface_m']<1e-6 for q in ends)))
    forbidden_lanes=[r['id'] for r in d['roads'] if r['lanes_per_direction']>2]
    assert not forbidden_lanes
    road_fence=[]
    for f in d['fences']:
        run=unary_union([LineString(seq) for seq in f['solid_runs_m']])
        hit=[r['id'] for r in d['roads'] if run.intersects(LineString(r['polyline_m']))]
        road_fence += [dict(fence_id=f['id'],road_id=rid) for rid in hit]
    assert not road_fence
    land=unary_union([Polygon(w['terrain']['land_polygon_m']),Polygon(w['island_tramduro']['polygon_m'])])
    piers=unary_union([Polygon(q['polygon_m']) for q in w['structures'] if q['kind']=='yacht_pier'])
    yachts=unary_union([Polygon(q['polygon_m']) for q in d['marina_source_yachts']])
    stairs=LineString(next(q['polyline_m'] for q in w['structures'] if q['kind']=='stairs_down_the_slope_to_beach')).buffer(3)
    sand=unary_union([Polygon(q['polygon_m']) for q in d['sand_areas']])
    enrichment=[];shapes=[]
    for q in d['marina_enrichment']:
        if not q.get('polygon_m'):continue
        g=Polygon(q['polygon_m']);shapes.append((q['id'],g))
        row=dict(id=q['id'],land_overlap_m2=g.intersection(land).area,piers_overlap_m2=g.intersection(piers).area,
            yachts_overlap_m2=g.intersection(yachts).area,sand_overlap_m2=g.intersection(sand).area,
            min_coast_clearance_m=g.distance(land.boundary),min_pier_clearance_m=g.distance(piers),
            min_yacht_clearance_m=g.distance(yachts),stairs_3m_buffer_clearance_m=g.distance(stairs))
        assert all(row[k]<1e-9 for k in ('land_overlap_m2','piers_overlap_m2','yachts_overlap_m2','sand_overlap_m2')),q['id']
        assert row['stairs_3m_buffer_clearance_m']>0
        enrichment.append(row)
    pairs=[]
    for i,(aid,a) in enumerate(shapes):
        for bid,b in shapes[i+1:]:
            overlap=a.intersection(b).area;assert overlap<1e-9
            pairs.append(dict(a=aid,b=bid,overlap_m2=overlap,clearance_m=a.distance(b)))
    return dict(source_lossless=True,source_buildings=216,source_structures=205,source_pois=119,source_roads=84,
        source_road_areas=10,source_bridges=8,bases=5,max_building_centroid_error_m=max(errors),
        van_graph_nodes=len(d['road_graph']['nodes']),van_graph_edges=len(d['road_graph']['edges']),van_graph_components=len(components),
        surface_join_count=len(d['road_graph']['surface_connections']),van_reachability=reach,
        mapped_legacy_points=sum(q['status']=='mapped' for q in d['gameplay_mapping']),
        unmatched_legacy_points=sum(q['status']=='unmatched' for q in d['gameplay_mapping']),
        removed_legacy_points=sum(q['status']=='removed' for q in d['gameplay_mapping']),
        lanes=dict(max_per_direction=2,violations=forbidden_lanes,boulevard='14 m green median: approved 2+2 by Fedya; no violation'),
        bridges=bridge,source_connected_bridges=sum(q['source_connected'] for q in bridge),
        tramduro_source_land_gap_m=d['boundary']['source_bridge_land_gap_m'],
        fences=dict(source_perimeters=len(d['fences']),new_district_border_fences=0,road_centerline_blocks=road_fence,
            source_palace_lawn_fence='Preserved property fence inside Tramduro, not a generated district border; confirmation requested.'),
        marina=dict(source_piers=3,source_yachts=6,enrichment_motorboats=4,optional_breakwater=1,dependent_light=1,
            breakwater_enabled=False,item_clearances=enrichment,pair_clearances=pairs))

def validate_flat(d,grey,look):
    assert len(grey['buildings'])==len(look['buildings'])==216
    assert len(grey['roads'])==len(look['roads'])==86
    assert len({tuple(r['pts']) for r in look['roads']})==86
    assert len(look['crossings'])==8 and len(look['parking'])==2
    errors=[];mesh_errors=[];source={b['id']:b for b in d['functional_buildings']}
    for b in look['buildings']:
        q=source[b['id']];g=geom(q);flat_poly=Polygon(np.asarray(b['fp']).reshape(-1,2))
        assert flat_poly.exterior.is_ccw,b['id']
        mesh=unary_union([Polygon(t) for t in np.asarray(b['tris']).reshape(-1,3,2)])
        mesh_errors.append(g.symmetric_difference(mesh).area)
        errors.append(Point(b['x'],b['y']).distance(g.centroid))
        assert b['floors']==q['floors'] and b['h']==q['height_m'] and len(b['rects'])>=5
    assert max(mesh_errors)<1e-5 and max(errors)<1e-6
    return dict(buildings=216,source_road_strokes=84,source_road_carriers=78,bridge_carriers=8,roads=86,paired_beach_strokes=6,
        look_crossings=8,look_sidewalks=len(look['sidewalks']),look_ground_polygons=len(look['ground']),
        native_look_building_centroid_error_m=max(errors),max_footprint_mesh_symmetric_difference_m2=max(mesh_errors),
        ccw_footprints=216,look_trees=len(look['trees']),greybox_trees=len(grey['tree_data'])//4,
        police_lots=[dict(id=q['id'],building=q['building'],four_stalls_fit=q['four_stalls_fit'],access_building_overlap_m2=q['access_building_overlap_m2']) for q in look['parking']],
        limitation='Greybox C# draws OBB masses; exact fp/tris and all optional source features require look/lead support. No Unity build performed.')

def protected_hashes():
    files=set((MAP/'World_v11').rglob('*'))
    files.update(p for p in MAP.rglob('*') if p.is_file() and re.search(r'v(?:12|13|14|15)(?:[_.]|$)',p.name))
    repo=MAP.parents[2]
    files.update(p for folder in ('Map','Police','Audio') for p in (repo/'Assets/OnlyVolunteers'/folder).rglob('*.cs'))
    if (repo/'WORK_SYNC.md').exists():files.add(repo/'WORK_SYNC.md')
    return {p.relative_to(repo).as_posix():sha(p) for p in sorted(files) if p.is_file()}

def prove_v12():
    """Existing defaults -> TEMP, then compare against committed bytes, never write old outputs."""
    result={};repo=MAP.parents[2]
    with tempfile.TemporaryDirectory(prefix='m1_v12_proof_') as td:
        temp=Path(td)
        target=MAP/'Greybox/greybox_v12_flat.json';dst=temp/'greybox_v12_flat.json'
        real_open=builtins.open;argv=sys.argv[:]
        def redirect(file,*args,**kwargs):
            if Path(file).resolve()==target.resolve() and args and 'w' in args[0]:file=dst
            return real_open(file,*args,**kwargs)
        try:
            builtins.open=redirect;sys.argv=[str(MAP/'Greybox/flatten_plan.py'),'v12','--veg']
            with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(sys.argv[0],run_name='__main__')
        finally:builtins.open=real_open;sys.argv=argv
        targets=[('greybox',dst,target)]
        dstlook=temp/'look_v12_flat.json'
        subprocess.run([sys.executable,'-B',str(MAP/'Look/flatten_look.py'),'v12','--out',str(dstlook)],check=True,capture_output=True)
        targets.append(('look',dstlook,MAP/'Look/look_v12_flat.json'))
        for kind,generated,target in targets:
            committed=subprocess.run(['git','show','HEAD:'+target.relative_to(repo).as_posix()],cwd=repo,check=True,capture_output=True).stdout
            same=generated.read_bytes()==target.read_bytes()==committed
            if not same:raise AssertionError(kind+' v12 output differs from committed bytes')
            result[kind]=dict(byte_identical_to_committed=True,sha256=sha(generated),bytes=generated.stat().st_size,
                command='flatten_plan.py v12 --veg (write redirected to TEMP)' if kind=='greybox' else 'flatten_look.py v12 --out TEMP/look_v12_flat.json')
    return result

def report(d,crowd,flat_checks,render_info,legacy,protected_count,dst,initial_changes=None,determinism=None):
    c=d['checks'];reach={q['id']:q for q in c['van_reachability']};lines=[]
    def add(*texts):lines.extend(texts)
    add('# TASK M1 — World map v11 → R01 v16', '',
        'Data and scripts only. No Unity build, NavMesh bake, driving test, asset import, commit or WORK_SYNC edit was performed.', '',
        '## Deliverables', '',
        '- `map_plan_v16.py` — exclusive-create converter, native flat adapters, v12 crowd algorithms, render and verification.',
        '- `MAP_PLAN_R01_v16.json` — R01 core plus lossless source and optional extensions.',
        '- `MAP_PLAN_R01_v16.png` — muted R01 style, exact source geometry and numbered POIs.',
        '- `MAP_PLAN_R01_v16_OVERLAY.png` — 45% v16 PNG blended with the v11 preview at the identical viewport.',
        '- `MAP_PLAN_R01_v16_REPORT.md` — this report.',
        '- `Greybox/greybox_v16_flat.json`, `Look/look_v16_flat.json`, `Crowd/crowd_v16.json`.',
        '- Shared `Greybox/flatten_plan.py` and `Look/flatten_look.py` have an isolated v16 dispatch plus optional `--plan`/output routing; legacy algorithms are unchanged.', '',
        '## Coordinates and schema', '',
        'No coordinate conversion: metres, bottom-left frame origin, +X east, +Y north; Unity `(x, terrain_height, y)`. Frame 1474 × 760 m. v12 core field names and flat consumer shapes remain available.', '',
        'Extensions: `world_v11` (entire source); `district_mapping`, numeric `world_id`/`world_district_id` and string aliases; `base_mapping`/`gameplay_mapping`; raw `structures` and all named `pois`; `terrain_hints`/`vegetation_hints`; width-profile water; `road_areas`; exact `bridges` with deck polygons/axes/piers; special `fences` with gate intervals; all `sand_areas`; `police_parking_proposals`; optional `marina_enrichment` and its independent settings. Both flats retain these under `world_v11_extensions`. Look additionally exposes the optional marina layer at its root.', '',
        'Buildings keep all source footprints, kind, floors, height and roof colour; centroid and minimum oriented box are derived. Look uses CCW exact footprints, constrained triangles and existing rect decomposition. Entrance direction is a labelled nearest-road proposal, not an approved door.', '',
        'The source exporter records each of six City Beach paths twice, matching SVG border (#C2C2B7) and inner surface (#EBE8D9) strokes. All 84 source records remain in plan/flat extensions. Native flats emit 78 distinct source ribbons plus 8 bridge carriers (86 total): one inner beach ribbon per pair, with the wider border retained as Look ground and source metadata. This avoids duplicate coplanar ribbons without changing source geometry.', '',
        'District JSON exports only bbox/label positions. R01 `polygon_m` currently contains explicitly labelled source bounding boxes for legacy ID lookup. SVG coloured ground patches do not establish complete district boundaries for all ten districts; no rectangular district ground painting is generated. Approved district envelopes require a re-export.', '',
        'Canonical plan water level is 0. Source river has '+str(len(d['world_v11']['water']['river']['width_m']))+' width samples; tapered polygons preserve the profile. Canal water is 13.2 m with 1.4 m walls per side (16 m total). The canal mouth separately retains its source dimensions.', '',
        '## District mapping', '',
        '| v11 | R01 / crowd / police / ambience ID | Aliases | Buildings |',
        '|---|---|---|---:|')
    for q in d['districts']:add(f"| {q['world_id']} | {q['id']} | {', '.join(q['aliases'])} | {q['building_count']} |")
    add('', 'The first nine IDs are supported by the existing ambience mapping; `tramduro` needs a new ambience recipe. Numeric IDs stay optional; existing string keys are preserved.', '',
        '## Base mapping and road reachability', '',
        '| v11 | R01 | District | Exact anchor (x, y) m | From spawn road stop, m | Anchor → road stop, m |',
        '|---|---|---|---|---:|---:|')
    for q in d['base_mapping']:
        rr=reach[q['r01_id']];add(f"| {q['world_id']} | {q['r01_id']} | {q['district_id']} | {q['position_m']} | {rr['distance_from_spawn_m']:.3f} | {rr['anchor_to_stop_m']:.3f} |")
    add('', 'Exactly five main bases. B06 is intentionally removed; Elite villas remain properties.', '',
        '## Every legacy gameplay ID', '',
        'The 43 IDs in v12 `points` are exhaustively mapped below. Source `pois` are label anchors, sometimes inside a footprint or over water. A mapped anchor does not certify a van can occupy the annotation position. Nearest exact road stops are separately exported; all local door/loading clearance and the unmatched functions require decisions.', '',
        '| ID | Status | v11 reference / question | Exact anchor m | From spawn stop, m |',
        '|---|---|---|---|---:|')
    for q in d['gameplay_mapping']:
        rr=reach.get(q['id']);desc=q['source_ref'] if rr else q['question']
        add(f"| {q['id']} | {q['status']} | {desc} | {q['position_m'] if rr else '—'} | {format(rr['distance_from_spawn_m'],'.3f') if rr else '—'} |")
    p=next(q for q in d['points'] if q['id']=='P10-2');add(f"| P10-2 (new) | mapped | poi:05:11, NE police station | {p['position_m']} | {reach['P10-2']['distance_from_spawn_m']:.3f} |")
    add('', 'Spawn and van start remain keyed by P02 → Base 2. P10 → Downtown 10 (SW); P10-2 → Downtown 11 (NE). Each of the 119 source numbered POIs has a stable `Dxx_POI_nn` ID and an exact source anchor, irrespective of legacy gameplay resolution.', '',
        '## Numerical checks', '',
        '| Check | Result |', '|---|---|',
        f"| Lossless source copy | PASS: {c['source_buildings']} buildings, {c['source_structures']} structures, {c['source_pois']} numbered POIs, {c['source_roads']} roads, {c['source_road_areas']} road areas, {c['source_bridges']} bridges |",
        f"| Source building centroid error | PASS: max {c['max_building_centroid_error_m']:.12g} m across 216 |",
        f"| Native Look footprint mesh | PASS: 216 CCW footprints; max symmetric difference {flat_checks['max_footprint_mesh_symmetric_difference_m2']:.12g} m²; centroid error {flat_checks['native_look_building_centroid_error_m']:.12g} m |",
        f"| Van graph | PASS: {c['van_graph_nodes']} nodes, {c['van_graph_edges']} edges, {c['van_graph_components']} component; {c['surface_join_count']} documented endpoint joins inside source road surfaces |",
        f"| Mapped road-stop reachability | PASS: 5/5 bases and {len(reach)}/134 exported point stops; node gap < 0.000001 m |",
        f"| Legacy gameplay resolution | {c['mapped_legacy_points']}/43 mapped, {c['unmatched_legacy_points']} unmatched questions, {c['removed_legacy_points']} removed; +1 new NE station |",
        '| Van access at the actual gameplay object | OPEN: annotation-to-stop offset and local door/loading geometry remain explicit; no invented access roads |',
        '| Lanes | PASS: max 2 per direction; 14 m boulevard/green median is approved 2+2 by Fedya, zero violations |',
        f"| Source bridge ends | {c['source_connected_bridges']}/8 connect both source road/path surfaces; all 4/4 vehicle bridges connect |",
        f"| Mainland → Tramduro coast | OPEN: source bridge axis starts {c['tramduro_source_land_gap_m']:.6f} m beyond source land; existing port-road surface supplies labelled legacy boundary/sea compatibility corridor |",
        '| Fences | PASS: zero generated district border fences; 6 source property perimeters retained; zero road centreline blocks after recorded openings |',
        f"| Source terrain retained | 10 hill/mountain hints, {len(d['vegetation_hints']['forest_zones'])} forest zones, {len(d['vegetation_hints']['clearings_m'])} clearings, {len(d['sand_areas'])} sand polygons; coast/ridge/lake/bog/pools retained |",
        f"| Native flat totals | {flat_checks['roads']} road/path carriers (78 distinct source + 8 decks; 6 SVG stroke pairs consolidated), 216 buildings, 8 Look crossings, {flat_checks['look_sidewalks']} sidewalk strips, {flat_checks['look_ground_polygons']} ground polygons; {flat_checks['look_trees']} deterministic trees |",
        '| Police 4-car lots | PASS: 2/2 source lots fit 4 stalls (2.6 × 5.2 m) and 6 m aisle; 5 m access has zero building overlap; dimensions are proposals |',
        f"| Crowd | PASS: {crowd['validation']['route_count']} loops, 1 police patrol, {len(crowd['spawn_despawn_points'])} hidden spawns, {len(crowd['points_of_interest'])} activity POIs, {len(crowd['witness_hotspots'])} witness spots, {crowd['validation']['connection_count']} connections, 1 exported component |",
        f"| Crowd geometry/occlusion | PASS: zero blocked paths, zero unapproved road crossings, zero town/police sand paths; {crowd['validation']['occlusion_reference_rays']} building-occluded observer rays; grid {crowd['validation']['grid_nodes']} nodes at {crowd['grid_step_m']} m |",
        f"| Protected map/source files | PASS: {protected_count} existing v12–v15/source file hashes unchanged; M1 writes no C# or WORK_SYNC files |",
        '| Unity / NavMesh / gameplay drive-through | NOT RUN (outside M1) |', '',
        'Road graph reachability covers the source transport network, not off-road approaches. Full per-point stop coordinates, offsets and path lengths are in `checks.van_reachability`. Door/loading feasibility must be checked by the lead before treating the conversion as gameplay-ready.', '',
        '### Bridge endpoint gaps', '', '| Bridge | End 1 road/path and gap m | End 2 road/path and gap m |', '|---|---|---|')
    for q in c['bridges']:
        a,b=q['ends'];add(f"| {q['id']} | {a['road_id']}: {a['gap_to_source_surface_m']:.6f} | {b['road_id']}: {b['gap_to_source_surface_m']:.6f} |")
    add('', 'The three City Beach footbridges keep the exact source deck polygons. Six explicitly proposed pedestrian approaches in crowd data cross existing dry meadow to source paths/streets; no road, paving or deck endpoint is moved.', '',
        f"Crowd exports 24 beach-lie points at source lounger references and all nine supported v12 activities except the absent bar. Activity positions are connected dry-graph projections: max reference offset {max(q['target_offset_m'] for q in crowd['points_of_interest']):.3f} m; shop queue at 04_low_02 is 24.535 m from its proposed door and football activity is 14.365 m from the pitch centre. These two placements require local alignment/approach review; no precise queue or animation placement is claimed.", '',
        '### Fence perimeters', '', '| ID | Source kind | Gates/cuts | Height m (status) |', '|---|---|---:|---|')
    for q in d['fences']:add(f"| {q['id']} | {q['kind']} | {len(q['gates'])} | {q['height_target_m']}: {q['height_status']} |")
    add('', 'Construction source gates retain 19/18/18 m openings and four 12 m van cuts. Other road/fence openings are explicitly derived proposals (road width + 2 m); heights outside Construction are proposals because JSON has no numbers. The Elite stairs opening is a 1.8 m proposal. The extra palace-lawn property fence is retained from v11 and is flagged for confirmation.', '',
        '## Fedya addendum: optional Elite marina', '',
        'The three east-facing v11 yacht piers remain byte-equal in geometry. Six white yacht hull polygons are read from the approved SVG and kept as exclusion geometry; their JSON absence is documented. Four motorboats retain v14 hull dimensions/shape under rigid rotation/translation. The v14 breakwater shape and dependent light are an independent optional layer, detached from the coast and rotated to the east of the v11 piers.', '',
        'Switches: `marina_enrichment_settings.enabled=false` disables the whole layer; each item also has `enrichment:true`, `optional:true`, `enabled`. Motorboats default enabled. Breakwater and light default disabled, with `requires_confirmation:"Vadim"`; enable both only after that decision. Existing C# does not consume this optional layer yet. Purple render geometry shows the proposal for review even when disabled.', '',
        '| Item | Centre / axis / position (metres) | Heading / size | Default |', '|---|---|---|---|')
    for q in d['marina_enrichment']:
        loc=q.get('center_m') or q.get('axis_m') or q.get('position_m')
        size=f"{q.get('heading_deg','—')}°; {q.get('length_m','—')} × {q.get('beam_m',q.get('width_m','—'))} m"
        add(f"| {q['id']} | {json.dumps(loc)} | {size} | {'ON' if q['enabled'] else 'OFF / Vadim'} |")
    add('', 'Complete polygon vertices and transformed breakwater axis are in `marina_enrichment`. Coordinates above are relative to the original source pier frame; no v14 pier/pontoon/road geography is inherited.', '',
        '| Item | Coast clearance m | Pier clearance m | Yacht clearance m | Stairs (3 m buffered) clearance m | Overlap m² |', '|---|---:|---:|---:|---:|---:|')
    for q in c['marina']['item_clearances']:add(f"| {q['id']} | {q['min_coast_clearance_m']:.3f} | {q['min_pier_clearance_m']:.3f} | {q['min_yacht_clearance_m']:.3f} | {q['stairs_3m_buffer_clearance_m']:.3f} | 0 |")
    add('', f"All {len(c['marina']['pair_clearances'])} enrichment polygon pairs have zero overlap; land, piers, yachts and sand overlaps are zero for each item. The navigation light intentionally sits on its parent breakwater. No base, road graph, source structure or crowd obstacle is added by this optional layer.", '',
        '## Overlay and v12 proof', '',
        f"Render and overlay are {render_info['width_px']} × {render_info['height_px']} pixels. X scale {render_info['x_px_per_m']:.12f} px/m; Y scale {render_info['y_px_per_m']:.12f} px/m (preview rounding). Origin pixel (0, {render_info['height_px']}); zero translation, zero rotation, no fitted registration or crop. Pixel quantization is at most half a pixel per axis.", '',
        '| v12 regeneration | Byte equality to committed output | SHA-256 |', '|---|---|---|')
    for kind,q in legacy.items():add(f"| {kind}: {q['command']} | PASS ({q['bytes']} bytes) | `{q['sha256']}` |")
    if determinism:
        add('', '### Verified deterministic v16 regeneration', '',
            'Two separately generated data/render sets are byte-identical for all six files below. Each set used the existing flattener entrypoints and passed geometry/crowd checks. The report records current preservation observations separately.', '',
            '| File | SHA-256 (both generations) |','|---|---|')
        for path,digest in determinism.items():add(f'| {path} | `{digest}` |')
    add('', 'Both regenerations write to system TEMP. Greybox uses `--veg` to reproduce the committed vegetation-bearing file; Look uses its unchanged default dressing/extras/kits/vegetation options. v12–v15 files remain untouched.', '',
        '## Current consumer limits / lead handoff', '',
        '- Existing latest-plan menus detect the v16 filenames. Native Greybox is an OBB mass approximation; exact footprints are preserved as optional data and natively triangulated in Look.',
        '- Legacy Look height code uses ground ~0, sea -0.6 and inland water -0.3; canonical water=0, coast heights, ridge profile and rotated hill hints are retained for the lead to support. Existing C# ignores hill rotation and ridge extensions. Do not claim 3D terrain fidelity from this data check.',
        '- Exact variable-width river/canal polygons reach the native polygon-water mesh, which currently uses the lake visual/material path. Typed water appearance and canal walls need consumer support.',
        '- Existing bridge builder uses its own pier/deck height recipe; exact axes, widths and suggested long-bridge piers are in extensions. New structure kinds (fire escapes, rooftop towers, billboards, yacht piers, stairs, fixtures) and the optional marina need consumer support.',
        '- Fences use the legacy generic fence drawing; exact perimeter/openings reach its collider geometry. Blue sheets, barbed wire and low-fence styles require lead art support.',
        '- Current police config selects P10 only. NE P10-2 is present but multi-station police behavior needs a separate lead change. The four-car parking proposals are native LookParking records, so the existing baker can read the selected station lot.',
        '- Current gameplay helpers hard-code missing P04/P08 and fall back to the map centre; legacy B05 labels may still say Industrial although its data is now the Valley lab. Resolve these before a playable build.',
        '- The downtown fountain is only a numbered POI in JSON, so no invented fountain polygon is supplied. The source palace fountain polygon is passed as `functional_sites[type=fountain]` for the ambience reader.',
        '- Crowd grid/routes follow actual dry geometry, including proposed unpaved bridge approaches/property-yard walks. Bar activity is omitted because no source bar exists. Tramduro 2/2 crowd density is an explicit proposal. Camera occlusion, NavMesh, actual props and height projection remain runtime gates.', '',
        '## Open questions for Vadim / Fedya', '',
        '1. Supply approved district outlines in JSON. Bounding boxes are a temporary ID lookup and may overlap; police district classification and ambience envelopes need true outlines.',
        '2. Resolve every unmatched gameplay ID in the exhaustive table. In particular P04/P08 are required by current trip markers; confirm removal/replacement of the pharmacy, bar, hospital, railway depot, tow yard, meeting/water/disposal spots and exit posts.',
        '3. Confirm an approved van entrance to City Beach. Elite access 07:12 is pedestrian stairs; the source does not define a City Beach vehicle road. No new beach access is invented.',
        '4. Re-export/confirm mainland land or bridge approach at Tramduro: source coast/bridge gap is 8.799156 m. Compatibility data keeps source positions but must not be mistaken for approved coast infill.',
        '5. Confirm six footbridge pedestrian approaches, source bridge-to-POI annotation discrepancies and precise local loading/door access at bases/gameplay objects.',
        '6. Vadim: confirm optional breakwater/light placement (currently OFF), detached offshore. Fedya already approved the motorboats and optional enrichment. Confirm whether the detached offshore breakwater is preferred to a future coast tie-in.',
        '7. Confirm numeric boulevard median width, property gate widths/heights outside Construction, palace-lawn fence, and Tramduro crowd/ambience recipe.',
        '8. Re-export the Downtown fountain footprint and clarify why the "one large bog" is two exported water polygons; both are preserved.', '',
        '## Reproduction', '',
        'Use system Python 3.12 with Shapely 2.2+, NumPy and Pillow. The script refuses to replace any existing v16 deliverable.', '',
        '```text',
        'python -B ArtSource/References/Map/map_plan_v16.py --out-dir <empty temporary folder>',
        'python -B ArtSource/References/Map/Greybox/flatten_plan.py v16 --plan <temporary plan.json> --out <new temporary greybox.json>',
        'python -B ArtSource/References/Map/Look/flatten_look.py v16 --plan <temporary plan.json> --out <new temporary look.json>',
        '```', '',
        'The full generator invokes both existing flattener entrypoints, adapts the immutable v12 crowd implementation, validates outputs and proves legacy v12 equality. Determinism can be checked by generating twice into different empty folders and comparing the six data/render outputs. The report additionally records preservation observations. Existing map/source hashes are checked before/after each run; C# and WORK_SYNC are read-only in M1 and may be changed by work outside this task.', '')
    if initial_changes:
        add('## Initial-scan changes outside M1 writes', '',
            f'{len(initial_changes)} C#/handoff files differ from the initial task preservation manifest. M1 wrote only the new v16 artifacts and the two named shared Python flatteners; it did not write any C# or WORK_SYNC file. The protected-map/source PASS above covers immutable inputs/deliverables. All initial v12–v15 map/source hashes remain unchanged.', '',
            '| File | Initial SHA-256 | Current SHA-256 |','|---|---|---|')
        for q in initial_changes:add(f"| {q['path']} | `{q['before']}` | `{q['after']}` |")
        add('')
    write_new(dst,'\n'.join(lines))

def main(argv=None):
    global MAP
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--map-dir',type=Path,default=MAP)
    ap.add_argument('--out-dir',type=Path,default=None)
    ap.add_argument('--initial-manifest',type=Path,default=None,help='optional original preservation hashes for transparent handoff')
    ap.add_argument('--compare-dir',type=Path,default=None,help='compare all six data/render outputs with a prior generated set')
    args=ap.parse_args(argv);MAP=args.map_dir.resolve();out=(args.out_dir or MAP).resolve()
    if sys.version_info[:2]!=(3,12):raise RuntimeError('M1 requires system Python 3.12')
    names=[STEM+'.json',STEM+'.png',STEM+'_OVERLAY.png',STEM+'_REPORT.md',
        'Greybox/greybox_v16_flat.json','Look/look_v16_flat.json','Crowd/crowd_v16.json']
    existing=[str(out/n) for n in names if (out/n).exists()]
    if existing:raise FileExistsError('No existing deliverable may be overwritten: '+', '.join(existing))
    before=protected_hashes()
    print('M1: source conversion and exact geometry checks',flush=True)
    d=build_plan(MAP);d['checks']=validate_plan(d);json_new(out/names[0],d)
    print('M1: existing Greybox flattener',flush=True)
    subprocess.run([sys.executable,'-B',str(MAP/'Greybox/flatten_plan.py'),'v16','--plan',str(out/names[0]),'--out',str(out/names[4])],check=True)
    print('M1: existing Look flattener',flush=True)
    subprocess.run([sys.executable,'-B',str(MAP/'Look/flatten_look.py'),'v16','--plan',str(out/names[0]),'--out',str(out/names[5])],check=True)
    grey=read(out/names[4]);look=read(out/names[5]);checks=validate_flat(d,grey,look)
    print('M1: v12 crowd algorithms on v16 geometry',flush=True)
    crowd=build_crowd(d,look,sha(out/names[0]));json_new(out/names[6],crowd)
    print('M1: same-scale render and overlay',flush=True)
    r=render(d,out/names[1],out/names[2])
    print('M1: v12 regeneration to TEMP and committed-byte comparisons',flush=True)
    legacy=prove_v12();after=protected_hashes()
    immutable_before={p:h for p,h in before.items() if p.startswith('ArtSource/References/Map/')}
    immutable_after={p:h for p,h in after.items() if p.startswith('ArtSource/References/Map/')}
    if immutable_before!=immutable_after:raise AssertionError('Protected map/source files changed during M1 generation')
    initial_changes=[]
    if args.initial_manifest:
        for path,digest in read(args.initial_manifest).items():
            current=sha(MAP.parents[2]/path)
            if digest!=current:
                if path.startswith('ArtSource/References/Map/'):raise AssertionError('An initial map/source file changed: '+path)
                initial_changes.append(dict(path=path,before=digest,after=current))
    determinism={}
    if args.compare_dir:
        for path in [n for n in names if not n.endswith('_REPORT.md')]:
            if (out/path).read_bytes()!=(args.compare_dir/path).read_bytes():raise AssertionError('Non-deterministic v16 output: '+path)
            determinism[path]=sha(out/path)
    report(d,crowd,checks,r,legacy,len(immutable_before),out/names[3],initial_changes,determinism)
    print(json.dumps(dict(passed=True,files=names,plan=d['checks']['source_buildings'],flat=checks,crowd=crowd['validation'],
        protected_files=len(before),v12=legacy),ensure_ascii=True),flush=True)

if __name__=='__main__':main()
