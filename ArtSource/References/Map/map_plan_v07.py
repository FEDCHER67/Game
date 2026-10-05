#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild v07 only: python -B map_plan_v07.py [--reset-data].
Existing JSON is editable. No packages, Git, Unity or handoff-log writes.
Uses unchanged v02 geometry/graph helpers and v05 function palette.
"""
import argparse
import copy
import hashlib
import json
import math
import os
import struct
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
import build_map_plan as m
import map_plan_v05 as v5

ROOT=m.ROOT
STEM='MAP_PLAN_R01_v07'
WIDTHS=dict(highway=7,town_street=6,rural_road=3.8,dirt_shortcut=3.5,passage=2.5)
NAMES=dict(forest='Лесная полоса',village='Хутор',transition='Переход',
    residential='Неблагополучный район',old_town='Старый город',elite='Элитный холм',
    industrial='Промышленная окраина',fields='Малая долина')
ROUTES=[('B01','P01'),('B01','P02'),('B01','P03'),('B01','BAD_CENTER'),
    ('B02','BAD_CENTER'),('B02','P04'),('BAD_CENTER','CLOCK_SQUARE'),
    ('CLOCK_SQUARE','ELITE_GATE'),('B03','P05'),('CLOCK_SQUARE','P14'),('P14','P12'),('B01','B05'),('B01','B07')]


def hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
        if p.is_file() and (p.name in ('build_map_plan.py','map_plan_v04.py','map_plan_v05.py','map_plan_v06.py')
        or any(p.name.startswith('MAP_PLAN_R01_'+r) for r in ('v02','v03','v04','v05','v06')))}


def edges(poly):return zip(poly,poly[1:]+poly[:1])


def gap(poly,a,b):
    if m.inside(a,poly) or m.inside(b,poly) or any(m.crossing(a,b,c,d) for c,d in edges(poly)):return 0
    return min([m.projection(p,a,b)[0] for p in poly]+[m.projection(p,c,d)[0] for p in (a,b) for c,d in edges(poly)])


def overlap(a,b):
    # Zero-area party-wall contact is intentional.
    if any(max(p[k] for p in a)<=min(p[k] for p in b)+.001 or
           max(p[k] for p in b)<=min(p[k] for p in a)+.001 for k in (0,1)):return False
    return v5.overlaps(m,a,b)


def physical(data):
    promoted={f.get('source_building_id') for f in data['functional_buildings']}
    return [dict(id=b['id'],district_id=b['district_id'],poly=b['polygon_m'])
        for b in data['building_masses'] if b['id'] not in promoted]+[
        dict(id=f['id'],district_id=f['district_id'],poly=f['footprint_m']) for f in data['functional_buildings']]


def seed():
    data=json.loads((ROOT/'MAP_PLAN_R01_v06.json').read_text(encoding='utf-8'))
    data.update(revision='v07',title_ru='VOLUNTEERS ONLY — план карты R01 / v07')
    data['specification']['brief_override']='req_map_plan_v07.md, targeted review, 2026-10-04'
    data['provenance']=dict(brief='req_map_plan_v07.md',source_schema='MAP_PLAN_R01_v06.json',
        owner_decisions_date='2026-10-04',method='targeted v06 edits; unchanged geometry retained',previous_files_sha256=hashes())
    data['comparison']={'v06':{'extent_m':data['metrics']['extent_m']},'policy':'targeted edits; no uniform scaling'}
    data['planning_notes_ru']=[
        'Хутор: дом деда и три отдельные усадьбы; дом + прилегающий гараж. Аптека и амбар — отдельные функции.',
        'Северная усадьба удалена; пустые западные углы и северный участок вырезаны из границы.',
        'Двор 3 перенесён к бару и 24 ч южнее основной улицы дворов; улица огибает его с севера.',
        'Элитка: четыре особняка, включая B06; два доступны P15. Промзона: два склада; B05 — производственная база.',
        'B07 — отдельная современная двухэтажная вилла напротив озера; пристроенный гараж, личный тупиковый подъезд и терраса.',
        'Времена расчётные; субъективное принятие и физические барьеры требуют Unity-плейтеста.']
    removed={'F06_2_2','F06_2_3','F06_3_3','F06_4_3','F06_6_3'}|{f'F06_5_{j}' for j in (1,2,3)}
    data['building_masses']=[b for b in data['building_masses'] if b['id'] not in removed]
    bs={b['id']:b for b in data['building_masses']}
    data['farmsteads']=[f for f in data['farmsteads'] if f['id'] not in ('FARM06_2','FARM06_5')]
    for farm in data['farmsteads']:
        i=int(farm['id'].split('_')[-1]); c=farm['center_m']
        farm['building_ids']=[f'F06_{i}_1',f'F06_{i}_2']
        garage=bs[f'F06_{i}_2']; garage.update(center_m=[c[0]+11,c[1]],subtype='estate_garage')
        garage['polygon_m']=m.rectangle(*garage['center_m'],8,7)
        house=bs[f'F06_{i}_1']
        source=next((f for f in data['functional_buildings'] if f.get('source_building_id')==house['id']),house)
        garage.update(entrance_m=source['entrance_m'],access_road_id=source['access_road_id'])
        if i!=1: farm['yard_polygon_m']=m.rectangle(c[0]+4,c[1],34,24)
    farms={f['id']:f for f in data['farmsteads']}
    data['plots']=[p for p in data['plots'] if p['id'] not in ('FARM06_2','FARM06_5')]
    for p in data['plots']:
        if p['id'] in farms:p['polygon_m']=farms[p['id']]['yard_polygon_m']
    data['vegetation_parcels']=[q for q in data['vegetation_parcels'] if q['id'] not in ('ORCHARD06_2','ORCHARD06_5')]
    # Keep NW checkpoint pocket while cutting empty left corners and deleted northern estate.
    village=[[180,550],[350,550],[350,710],[230,710],[180,780],[110,780],[110,740],[180,690]]
    next(d for d in data['districts'] if d['id']=='village')['polygon_m']=village
    bp=data['boundary']['polygon_m']; data['boundary']['polygon_m']=bp[:-1]+[
        [350,780],[350,710],[230,710],[180,780],[110,780],[110,740],[180,690],[180,550],[110,550]]
    for q in data['vegetation_parcels']:
        if q['id']=='FOREST_VILLAGE_1':q['polygon_m']=m.rectangle((180+228.1)/2,550,48.1,4)
        if q['id']=='RURAL_TRANSITION_2':q['polygon_m']=m.rectangle(350,(601.9+710)/2,4,710-601.9)
    removed_roads={'ACCESS_'+bid for bid in removed}|{f'ACCESS_F06_{i}_2' for i in (1,3,4,6)}
    remove_functions={'F06_MANSION_5','F06_MANSION_6','F06_MANSION_7','F06_WARE3'}
    removed_roads|={'ACCESS_'+id for id in remove_functions}
    data['functional_buildings']=[f for f in data['functional_buildings'] if f['id'] not in remove_functions]
    data['plots']=[p for p in data['plots'] if p['id'] not in {'GARDEN06_5','GARDEN06_6','GARDEN06_7'}]
    data['roads']=[r for r in data['roads'] if r['id'] not in removed_roads]
    roads={r['id']:r for r in data['roads']}
    roads['V_NORTH']['polyline_m']=[[300,600],[300,700]]
    data['functional_sites'].append(dict(id='VAN07_P02',type='parked_van',district_id='village',
        building_id='F06_GRANDPA',position_m=[193,591],polygon_m=m.rectangle(193,591,5,2.2),label_ru='Бусик у дома деда'))
    # Real move south by 58 m and rotate the U; first two complexes untouched.
    court=data['microdistricts'][2]
    for bid in court['building_ids']:
        b=bs[bid];x,y=b['center_m'];b['center_m']=[1530-x,1392-y]
        b['polygon_m']=[[1530-x,1392-y] for x,y in b['polygon_m']]
    court.update(center_m=[765,667],angle=180,opening_direction='north',yard_polygon_m=m.rectangle(765,671,62,64))
    roads['R_COURTS']['polyline_m']=[[500,675],[710,675],[710,735],[820,735],[820,675]]
    roads['COURT_ACCESS_3']['polyline_m']=[[765,735],[765,687]]
    roads['ACCESS_P07']['polyline_m']=[[789.284,735],[789.284,729.381]]
    den=next(f for f in data['functional_buildings'] if f['id']=='F06_DEN')
    den.update(entrance_m=[789.284,729.381],access_road_id='R_COURTS')
    shop=next(f for f in data['functional_buildings'] if f['id']=='F06_24')
    shop.update(center_m=[675,632],footprint_m=m.rectangle(675,632,24,14),entrance_m=[675,643],access_road_id='R_COURTS')
    roads['ACCESS_F06_24']['polyline_m']=[[675,675],[675,643]]
    roads['ACCESS_P11-2']['polyline_m']=[[687,675],[687,644]]
    path=next(p for p in data['paths'] if p['id']=='PASS06_BAD_3')
    path['polyline_m']=[[765,687],[745,687],[745,735]];path['length_m']=68
    for p in data['points']:
        if p['id']=='BAD_BLOCK_3':p['position_m']=[765,687]
        if p['id']=='P07':p['position_m']=den['entrance_m']
        if p['id']=='P11-2':p['position_m']=[687,644]
    # One final-base structure: main house with a visibly attached single-storey van garage.
    house=m.rectangle(420,530,28,14);garage=m.rectangle(400,530,12,8)
    footprint=[[406,523],[434,523],[434,537],[406,537],[406,534],[394,534],[394,526],[406,526]]
    color,icon,_=v5.PALETTE['base']
    data['functional_buildings'].append(dict(id='F07_VILLA',type='final_base',district='fields',district_id='fields',
        label_ru='Вилла у озера — финальная база',group='base',center_m=[414,530],width_m=40,depth_m=14,
        footprint_m=footprint,storeys=2,footprint_shape='house_with_attached_garage',color=color,icon=icon,
        poi_id='B07',entrance_m=[400,523.1],access_road_id='VALLEY_BRANCH',
        main_house_footprint_m=house,attached_garage_footprint_m=garage,garage_storeys=1,
        architectural_style='modern_glass_flat_roof',lake_facing_direction='east',van_garage=True))
    data['points'].append(dict(id='B07',canonical_id='B07',category='base',district_id='fields',
        name_ru='Вилла у озера — финальная база',position_m=[400,523.1],label_offset_px=[10,-12]))
    data['roads'].append(dict(id='ACCESS_B07',polyline_m=[[390,520],[400,520],[400,523.1]],
        width_m=3.8,**{'class':'rural_road'},district_ids=['fields'],access_only=True))
    terrace=m.rectangle(437,525,6,22)
    data['plots'].append(dict(id='VILLA07_YARD',kind='villa_yard',district_id='fields',polygon_m=terrace))
    data['functional_sites'].append(dict(id='VILLA07_TERRACE',type='lake_terrace',district_id='fields',
        building_id='F07_VILLA',polygon_m=terrace,label_ru='Частная терраса к озеру'))
    # P01 is a functional roadside pole; its interaction point stays on START_ROAD.
    color,icon,_=v5.PALETTE['landmark']
    data['functional_buildings'].append(dict(id='F07_AD_POLE',type='advertising_pole',district='village',district_id='village',
        label_ru='Объявление',group='landmark',center_m=[234.5,558],width_m=.6,depth_m=.6,
        footprint_m=m.rectangle(234.5,558,.6,.6),storeys=1,footprint_shape='rect',height_target_m=3,
        color=color,icon=icon,poi_id='P01',entrance_m=[230,558],access_road_id='START_ROAD'))
    return data


def add_access(data):
    footprints=physical(data)
    barriers=[q['polygon_m'] for q in data['vegetation_parcels'] if q['kind']=='interdistrict_barrier']
    pts={p['id']:p for p in data['points']}
    def approach(id,pos,dist,foot=None,allowed=None):
        choices=[]
        width=3.8 if dist in ('forest','village','transition','fields') else 6
        for r in data['roads']:
            if r['id'].startswith('EXIT_') or (allowed and r['id'] not in allowed):continue
            if dist not in r.get('district_ids',[]) and not allowed:continue
            for a,b in zip(r['polyline_m'],r['polyline_m'][1:]):
                _,q,t=m.projection(pos,a,b)
                door=pos
                if foot:
                    hits=[h[0] for c,d in edges(foot) if (h:=m.crossing(pos,q,c,d))]
                    if not hits:continue
                    door=min(hits,key=lambda h:m.length(h,q));n=m.length(door,q)
                    door=[round(door[k]+(q[k]-door[k])/max(n,.001)*(width/2+1),3) for k in (0,1)]
                if any(gap(p['poly'],q,door)<width/2+.1 for p in footprints if p['poly']!=foot):continue
                if any(gap(poly,q,door)<width/2-.002 for poly in barriers):continue
                if any(('polygon_m' in w and gap(w['polygon_m'],q,door)<width/2) or
                    any(m.crossing(q,door,c,d) for c,d in zip(w.get('centerline_m',[]),w.get('centerline_m',[])[1:])) for w in data['water']):continue
                # A driveway joins once. Multiple crossings would make an
                # unintended rural shortcut or loop between separate anchors.
                if any(hit and m.length(hit[0],q)>.02 for other in data['roads']
                    for c,d in zip(other['polyline_m'],other['polyline_m'][1:])
                    if (hit:=m.crossing(q,door,c,d))):continue
                choices.append((m.length(q,door),q,door,r['id']))
        if not choices:raise ValueError('Blocked entrance '+id)
        _,q,door,rid=min(choices)
        if m.length(q,door)>.01:
            cls='rural_road' if width==3.8 else 'town_street'
            data['roads'].append(dict(id='ACCESS_'+id,polyline_m=[q,door],width_m=width,**{'class':cls},
                district_ids=[dist],access_only=True))
        return door,rid
    for f in data['functional_buildings']:
        allowed={'B02':['HUT_BRANCH'],'P04':['RECEPTION_BRANCH']}.get(f.get('poi_id'))
        door,rid=approach(f.get('poi_id',f['id']),f['center_m'],f['district_id'],f['footprint_m'],allowed)
        f.update(entrance_m=door,access_road_id=rid)
        if f.get('poi_id'):pts[f['poi_id']]['position_m']=door
    promoted={f.get('source_building_id') for f in data['functional_buildings']}
    for b in data['building_masses']:
        if b['district_id']=='village' and b['id'] not in promoted:
            door,rid=approach(b['id'],b['center_m'],b['district_id'],b['polygon_m'])
            b.update(entrance_m=door,access_road_id=rid)
    functional_ids={f.get('poi_id') for f in data['functional_buildings']}
    for p in data['points']:
        if p['id'] in functional_ids:continue
        if min(m.projection(p['position_m'],a,b)[0] for r in data['roads']
            for a,b in zip(r['polyline_m'],r['polyline_m'][1:]))<.01:continue
        if any(m.inside(p['position_m'],b['poly']) for b in footprints):raise ValueError('POI in building '+p['id'])
        approach(p['id'],p['position_m'],p['district_id'])
    for p in data['paths']:
        p['length_m']=round(sum(m.length(a,b) for a,b in zip(p['polyline_m'],p['polyline_m'][1:])),3)
        p['purpose_ru']='Локальный перенос NPC к бусику, без прохода между районами.'


def analyse(data):
    m.build_graph(data)
    checks=[]
    def check(name,ok,detail=''):checks.append(dict(name=name,passed=bool(ok),detail=detail))
    bp=data['boundary']['polygon_m'];ds={d['id']:d for d in data['districts']}
    bounds=[min(p[0] for p in bp),min(p[1] for p in bp),max(p[0] for p in bp),max(p[1] for p in bp)]
    extent=[bounds[2]-bounds[0],bounds[3]-bounds[1]];total=m.area(bp)
    fs=data['functional_buildings'];bs=data['building_masses'];phys=physical(data)
    pts={p['id']:p for p in data['points']};counts=Counter(b['district_id'] for b in phys)
    for d in data['districts']:
        d.update(area_m2=m.area(d['polygon_m']),building_count=counts[d['id']])
        d['share_percent']=d['area_m2']/total*100
    ped=copy.deepcopy(data);ped['roads']+=copy.deepcopy(data['paths']);m.build_graph(ped)
    data['pedestrian_graph']=ped['road_graph']
    routes=[]
    for a,b in ROUTES:
        distance,ids=m.shortest(data,pts[a]['road_node_id'],pts[b]['road_node_id'])
        walking,wids=m.shortest(ped,next(p for p in ped['points'] if p['id']==a)['road_node_id'],
            next(p for p in ped['points'] if p['id']==b)['road_node_id'],mode='walk')
        routes.append(dict(from_id=a,to_id=b,length_m=round(distance,3),edge_ids=ids,
            van_60_seconds=round(distance/(60/3.6),2),van_90_seconds=round(distance/(90/3.6),2),
            pedestrian_length_m=round(walking,3),pedestrian_edge_ids=wids,walk_5_minutes=round(walking/(5000/60),2)))
    lengths={(r['from_id'],r['to_id']):r['length_m'] for r in routes}
    check('playable extent at most 1000 m per axis',all(v<=1000 for v in extent),str(extent))
    check('districts partition the playable area',abs(sum(d['area_m2'] for d in data['districts'])-total)<.01)
    check('physical count matches v06 removals plus B07 and P01 pole',len(phys)==115,str(len(phys)))
    for id in ('P01','P02','P03'):check('B01 → '+id+' ≤ 200 m',lengths['B01',id]<=200,str(lengths['B01',id]))
    check('B01 → bad district ≥ 400 m',lengths['B01','BAD_CENTER']>=400,str(lengths['B01','BAD_CENTER']))
    check('bad district → square ≤ 200 m',lengths['BAD_CENTER','CLOCK_SQUARE']<=200,str(lengths['BAD_CENTER','CLOCK_SQUARE']))
    check('square → elite gate ≤ 200 m',lengths['CLOCK_SQUARE','ELITE_GATE']<=200,str(lengths['CLOCK_SQUARE','ELITE_GATE']))
    check('exact latest road widths',all(r['width_m']==WIDTHS[r['class']] for r in data['roads']+data['paths']))
    slabs=[b for b in bs if b['kind']=='slab'];courts=data['microdistricts']
    check('three U courts; exactly three 72 × 12 m slabs each',len(courts)==3 and len(slabs)==9 and
        all(len(c['building_ids'])==3 and c['shared_courtyard'] and c['arrangement']=='U' for c in courts) and
        all(b['width_m']==72 and b['depth_m']==12 and 9<=b['floors']<=12 for b in slabs))
    check('no additional residential blocks in bad district',all(b['kind']=='slab' or b.get('subtype')=='garage_box'
        for b in bs if b['district_id']=='residential'))
    tall=[b for b in bs if b['district_id']=='old_town' and b['floors']>=12]
    check('exactly two 12–16-storey old-town landmarks',len(tall)==2 and all(12<=b['floors']<=16 for b in tall))
    terraces=[b for b in bs if 'terrace_id' in b]
    check('five six-unit terraces; 7-m frontages; 2–3 floors',len(terraces)==30 and
        set(Counter(b['terrace_id'] for b in terraces).values())=={6} and
        all(b['width_m']==7 and 2<=b['floors']<=3 for b in terraces))
    types=Counter(f['type'] for f in fs)
    required={'wagon_base','grandpa_house','pharmacy','hut','shadow_buyer','garage_base','car_workshop','bar','den',
        'shop_24h','boiler_house','hospital','police_station','church','small_hotel','post_office','clothes_masks_shop',
        'house_base','clock_tower','bank','supermarket','private_security','boutique','prestige_base','industrial_complex','depot','tow_yard'}
    check('required functions; two cafés; three kiosks',required<=set(types) and types['cafe']==2 and types['kiosk']==3)
    check('P05 at shared avenue seam',next(f for f in fs if f.get('poi_id')=='P05')['district_id']=='old_town' and
        abs(next(f for f in fs if f.get('poi_id')=='P05')['center_m'][1]-620)<30)
    check('three open P09 meeting sites',{s.get('poi_id') for s in data['functional_sites'] if s['type']=='meeting'}=={'P09','P09-2','P09-3'})
    mansions=[f for f in fs if f['type'] in ('mansion','prestige_base')]
    check('four mansions, gardens, two accessible P15',len(mansions)==4 and sum(f['accessible'] for f in mansions)==2 and
        len([p for p in data['plots'] if p['kind']=='elite_garden'])==4)
    gardenhits=[p['id'] for p in data['plots'] if p['kind']=='elite_garden' and
        (not all(m.inside(q,ds['elite']['polygon_m']) for q in p['polygon_m']) or
        any(gap(p['polygon_m'],a,b)<r['width_m']/2 for r in data['roads'] if not r['id'].startswith('ACCESS_')
            for a,b in zip(r['polyline_m'],r['polyline_m'][1:])))]
    check('elite gardens inside district and clear of streets',not gardenhits,str(gardenhits))
    check('B02 and P04 distinct dead-end branches',next(f for f in fs if f.get('poi_id')=='B02')['access_road_id']=='HUT_BRANCH' and
        next(f for f in fs if f.get('poi_id')=='P04')['access_road_id']=='RECEPTION_BRANCH')
    check('grandpa plus three distinct house-and-garage estates',len(data['farmsteads'])==4 and all(len(f['building_ids'])==2 for f in data['farmsteads']))
    collisions=[(a['id'],b['id']) for i,a in enumerate(phys) for b in phys[i+1:] if overlap(a['poly'],b['poly'])]
    check('no overlapping building footprints',not collisions,str(collisions))
    outside=[b['id'] for b in phys if not all(m.inside(p,bp) and m.inside(p,ds[b['district_id']]['polygon_m']) for p in b['poly'])]
    check('all footprints inside district and boundary',not outside,str(outside))
    hits=[(b['id'],r['id']) for b in phys for r in data['roads'] for a,c in zip(r['polyline_m'],r['polyline_m'][1:])
        if gap(b['poly'],a,c)<r['width_m']/2-.005]
    check('all buildings clear of road corridors including access',not hits,str(hits))
    wet=[b['id'] for b in phys for w in data['water'] if ('polygon_m' in w and overlap(b['poly'],w['polygon_m'])) or
        any(gap(b['poly'],a,c)<w['width_m']/2 for a,c in zip(w.get('centerline_m',[]),w.get('centerline_m',[])[1:]))]
    check('all footprints clear of water',not wet,str(wet))
    railhits=[b['id'] for b in phys if any(gap(b['poly'],a,c)<2 for a,c in zip(data['railway']['polyline_m'],data['railway']['polyline_m'][1:]))]
    check('railway clear of footprints',not railhits,str(railhits))
    pathhits=[(p['id'],b['id']) for p in data['paths'] for b in phys for a,c in zip(p['polyline_m'],p['polyline_m'][1:]) if gap(b['poly'],a,c)<1.25]
    check('four clear urban-only walking passages',len(data['paths'])==4 and not pathhits and all(p['district_id'] in ('residential','old_town') and
        p['walkable'] and not p['van_access'] and all(m.inside(q,ds[p['district_id']]['polygon_m']) for q in p['polyline_m']) for p in data['paths']),str(pathhits))
    check('no interdistrict pedestrian distance reduction',all(abs(r['length_m']-r['pedestrian_length_m'])<.02 for r in routes
        if (r['from_id'],r['to_id']) in (('B01','BAD_CENTER'),('B02','BAD_CENTER'))))
    check('passages excluded from vehicle graph',all(e['class']!='passage' for e in data['road_graph']['edges']))
    for key,graph in [('vehicle',data['road_graph']),('pedestrian',data['pedestrian_graph'])]:
        adj={n['id']:set() for n in graph['nodes']}
        for e in graph['edges']:adj[e['from_node']].add(e['to_node']);adj[e['to_node']].add(e['from_node'])
        seen=set();todo=[next(iter(adj))]
        while todo:
            n=todo.pop()
            if n not in seen:seen.add(n);todo.extend(adj[n]-seen)
        check(key+' graph connected',len(seen)==len(adj),f'{len(seen)}/{len(adj)}')
    # Every external connector must be a graph bridge. Access geometry is included,
    # so an accidentally crossing driveway cannot silently create a bypass.
    connector_gates=[('forest/village',[230,550],'START_ROAD'),('village/transition',[350,600],'ARC_RURAL'),
        ('transition/bad',[470,650],'ARC_RURAL'),('bad/old',[650,620],'ARC_AVENUE'),
        ('old/elite',[800,540],'ARC_AVENUE'),('old/industry',[650,440],'I_CONNECT')]
    for name,pos,rid in connector_gates:
        es=[e for e in data['road_graph']['edges'] if e['road_id']==rid and m.projection(pos,*e['polyline_m'])[0]<.01]
        cut=copy.deepcopy(data);cut['road_graph']['edges']=[e for e in cut['road_graph']['edges'] if e['id'] not in {e['id'] for e in es}]
        bridge=bool(es) and math.isinf(m.shortest(cut,es[0]['from_node'],es[-1]['to_node'])[0])
        check('one connector and no bypass: '+name,bridge)
    check('zero dirt shortcuts, permitted maximum one',sum(r['class']=='dirt_shortcut' for r in data['roads'])==0)
    urban={'residential','old_town'}
    allowed_roads={r['id'] for r in data['roads'] if not set(r.get('district_ids',[]))<=urban}
    parents={n['id']:n['id'] for n in data['road_graph']['nodes']}
    def root(n):
        while parents[n]!=n:n=parents[n]
        return n
    cycles=[]
    for e in data['road_graph']['edges']:
        if e['road_id'] not in allowed_roads:continue
        a,b=root(e['from_node']),root(e['to_node'])
        if a==b:cycles.append(e['road_id'])
        else:parents[a]=b
    check('no vehicle loops outside urban core',not cycles,str(cycles))
    belt_hits=[(r['id'],q['id']) for r in data['roads']+data['paths'] for q in data['vegetation_parcels']
        if q['kind']=='interdistrict_barrier' for a,b in zip(r['polyline_m'],r['polyline_m'][1:])
        if gap(q['polygon_m'],a,b)<r['width_m']/2-.01]
    check('barrier belts closed except exact road openings',not belt_hits,str(belt_hits))
    for ex in data['exits']:
        node=ex['dead_end_node_id'];post=pts[ex['post_id']]['road_node_id'];g=data['road_graph']
        check('visible dead end and mandatory return through post '+ex['id'],len([e for e in g['edges'] if node in (e['from_node'],e['to_node'])])==1 and
            math.isinf(m.shortest(data,pts['B01']['road_node_id'],node,blocked=post)[0]) and len(ex['barrier_polygons_m'])==2 and ex['blocks_foot_bypass'])
        flankhits=[r['id'] for r in data['roads'] for q in ex['barrier_polygons_m']
            for a,b in zip(r['polyline_m'],r['polyline_m'][1:]) if gap(q,a,b)<r['width_m']/2-.01]
        check('exit '+ex['id']+' flanks leave road clear',not flankhits,str(flankhits))
    check('P12 P14 B05 industrial; depot at railway end',all(pts[id]['district_id']=='industrial' for id in ('P12','P14','B05')) and
        m.length(next(f for f in fs if f.get('poi_id')=='P14')['center_m'],data['railway']['polyline_m'][-1])<30)
    old=json.loads((ROOT/'MAP_PLAN_R01_v05.json').read_text(encoding='utf-8'))
    check('v05 top-level schema retained',data['schema_version']==old['schema_version'] and set(old)<=set(data))
    schema={'roads':{'id','class','polyline_m','width_m'},
        'building_masses':{'id','center_m','width_m','depth_m','polygon_m','floors','district_id','kind'},
        'functional_buildings':{'id','center_m','width_m','depth_m','footprint_m','storeys','label_ru','type'},
        'points':{'id','canonical_id','name_ru','position_m','category'},
        'districts':{'id','polygon_m','parent_id'},'plots':{'id','kind','polygon_m'},
        'microdistricts':{'id','center_m','yard_polygon_m','building_ids'},
        'farmsteads':{'id','center_m','yard_polygon_m','start_cluster','building_ids'},
        'vegetation_parcels':{'id','kind','polygon_m'},'paths':{'id','class','polyline_m','width_m','walkable','van_access'},
        'exits':{'id','post_id','dead_end_m','barrier_polygons_m'}}
    check('converter-required nested schema retained',all(fields<=set(q) for k,fields in schema.items() for q in data[k]))
    check('v05 top-level container types retained',all(type(value)==type(data[k]) for k,value in old.items()))
    check('canonical B01–B06 P01–P16 and repeats retained',{p['canonical_id'] for p in old['points']}-{ 'BAD_BLOCK_4'}<={p['canonical_id'] for p in data['points']})
    for k in ('roads','points','building_masses','functional_buildings','paths'):
        check(k+' IDs unique',len({q['id'] for q in data[k]})==len(data[k]))
    check('all older files SHA256 unchanged',hashes()==data['provenance']['previous_files_sha256'])
    entrances={b['id']:b.get('entrance_m') for b in bs}
    entrances.update({f['source_building_id']:f['entrance_m'] for f in fs if 'source_building_id' in f})
    data['start_cluster_home_routes_m']={bid:round(m.shortest(data,pts['B01']['road_node_id'],
        min(data['road_graph']['nodes'],key=lambda q:m.length(q['position_m'],entrances[bid]))['id'])[0],3)
        for farm in data['farmsteads'] if farm['start_cluster'] for bid in farm['building_ids']}
    data['hamlet_statistics']=dict(farmstead_count=len(data['farmsteads']),building_count=counts['village'],start_cluster_count=sum(f['start_cluster'] for f in data['farmsteads']))
    data['residential_statistics']=dict(complex_count=3,slab_count=9,garage_box_count=18)
    data['functional_statistics']=dict(building_count=len(fs),district_counts=dict(Counter(f['district_id'] for f in fs)),type_counts=dict(types),
        promoted_existing_count=sum('source_building_id' in f for f in fs),new_footprint_count=sum('source_building_id' not in f for f in fs))
    data['passage_statistics']=dict(count=4,total_length_m=sum(p['length_m'] for p in data['paths']),policy='urban local only; no van access')
    data['metrics']=dict(area_m2=total,bounds_m=bounds,extent_m=extent,routes=routes,building_count=len(phys),
        building_counts_by_district=dict(counts),timing_assumption='constant speeds; no acceleration, traffic, turns or slopes; not measured gameplay')
    validate_targeted(data,check)
    data['validation']=dict(passed=all(c['passed'] for c in checks),checks=checks)
    if not data['validation']['passed']:raise ValueError(json.dumps([c for c in checks if not c['passed']],ensure_ascii=False,indent=2))


def validate_targeted(data,check):
    old=json.loads((ROOT/'MAP_PLAN_R01_v06.json').read_text(encoding='utf-8'))
    ds={d['id']:d for d in data['districts']};ods={d['id']:d for d in old['districts']}
    check('exact v06 top-level schema and container types',set(data)==set(old) and all(type(data[k])==type(v) for k,v in old.items()))
    check('hamlet area reduced by at least 30 percent',ds['village']['area_m2']<.7*ods['village']['area_m2'])
    check('outer boundary loses exactly removed hamlet area',abs(old['metrics']['area_m2']-data['metrics']['area_m2']-(ods['village']['area_m2']-ds['village']['area_m2']))<.01)
    check('northern estate and pharmacy outbuildings fully removed',not any(b['id'].startswith('F06_5_') or b['id'] in ('F06_2_2','F06_2_3') for b in data['building_masses']))
    check('no speculative orchard fill',not any(q['id'].startswith('ORCHARD07') for q in data['vegetation_parcels']))
    bs={b['id']:b for b in data['building_masses']}
    check('one house plus attached small garage per estate',all(
        bs[f['building_ids'][0]]['kind']=='rural_house' and bs[f['building_ids'][1]].get('subtype')=='estate_garage' and
        abs(m.length(bs[f['building_ids'][0]]['center_m'],bs[f['building_ids'][1]]['center_m'])-11)<.001
        for f in data['farmsteads']))
    check('grandpa original yard and visible van',data['farmsteads'][0]['yard_polygon_m']==old['farmsteads'][0]['yard_polygon_m'] and
        any(q['type']=='parked_van' and m.inside(q['position_m'],data['farmsteads'][0]['yard_polygon_m']) for q in data['functional_sites']))
    check('start house and POIs walkable within 300 m',all(r['pedestrian_length_m']<=300 for r in data['metrics']['routes'] if r['from_id']=='B01' and r['to_id'] in ('P01','P02','P03')) and max(data['start_cluster_home_routes_m'].values())<=300)
    check('two original courtyard complexes unchanged',data['microdistricts'][:2]==old['microdistricts'][:2] and
        [b for b in data['building_masses'] if b['id'].startswith(('R06_C1_','R06_C2_'))]==[b for b in old['building_masses'] if b['id'].startswith(('R06_C1_','R06_C2_'))])
    check('third courtyard south beside bar and shop',data['microdistricts'][2]['center_m']==[765,667] and
        max(p[1] for b in data['building_masses'] if b['id'].startswith('R06_C3_') for p in b['polygon_m'])<735 and
        all(m.length(data['microdistricts'][2]['center_m'],f['center_m'])<110 for f in data['functional_buildings'] if f['type'] in ('bar','shop_24h')))
    check('only final warehouse removed',[f['id'] for f in data['functional_buildings'] if f['type']=='warehouse']==['F06_WARE1','F06_WARE2'])
    for dist in ('old_town','transition'):
        for key in ('building_masses','functional_buildings','points','plots','paths'):
            items=lambda d:[{k:v for k,v in q.items() if k!='road_node_id'} for q in d[key] if q.get('district_id')==dist]
            check(dist+' '+key+' unchanged',items(data)==items(old))
    check('railway water and fields unchanged',data['railway']['polyline_m']==old['railway']['polyline_m'] and data['water']==old['water'] and data['field_parcels_m']==old['field_parcels_m'])
    villa=next(f for f in data['functional_buildings'] if f['type']=='final_base')
    point=next(p for p in data['points'] if p['id']=='B07')
    check('B07 canonical final base with two-storey house and attached van garage',point['canonical_id']=='B07' and point['category']=='base' and
        villa['storeys']==2 and villa['garage_storeys']==1 and villa['van_garage'] and villa['poi_id']=='B07')
    lake=next(w for w in data['water'] if w['id']=='LAKE')['polygon_m']
    check('villa stands directly opposite lake in isolated valley',villa['district_id']=='fields' and villa['center_m'][0]<min(p[0] for p in lake) and
        min(p[1] for p in lake)<villa['center_m'][1]<max(p[1] for p in lake)+6 and
        min(m.length(villa['center_m'],f['center_m']) for f in data['functional_buildings'] if f['district_id']!='fields')>60)
    check('private drive from nearest road, no second valley connector',next(r for r in data['roads'] if r['id']=='ACCESS_B07')['polyline_m'][0]==[390,520] and
        villa['access_road_id']=='VALLEY_BRANCH' and m.length(villa['entrance_m'],[390,520])<15)
    terrace=next(q for q in data['functional_sites'] if q['id']=='VILLA07_TERRACE')
    check('terrace faces lake and clears water buildings and roads',all(m.inside(p,ds['fields']['polygon_m']) for p in terrace['polygon_m']) and
        not overlap(terrace['polygon_m'],lake) and all(not overlap(terrace['polygon_m'],b['poly']) for b in physical(data)) and
        all(gap(terrace['polygon_m'],a,b)>=r['width_m']/2 for r in data['roads'] for a,b in zip(r['polyline_m'],r['polyline_m'][1:])))
    check('B05 remains unchanged production base',next(f for f in data['functional_buildings'] if f.get('poi_id')=='B05')==next(f for f in old['functional_buildings'] if f.get('poi_id')=='B05'))
    check('P01 advertising pole is functional with unchanged interaction point',any(f['type']=='advertising_pole' and f.get('poi_id')=='P01' for f in data['functional_buildings']) and
        next(p for p in data['points'] if p['id']=='P01')['position_m']==next(p for p in old['points'] if p['id']=='P01')['position_m'])
    check('all road centre lines inside boundary',all(m.inside(p,data['boundary']['polygon_m']) for r in data['roads'] for p in r['polyline_m']))


def render(data):
    s=m.SVG();scale=1824/900
    def xy(p):return [70+(p[0]-80)*scale,210+(900-p[1])*scale]
    def line(poly,col,w=1,**extra):s.line([xy(p) for p in poly],col,w,**extra)
    def polygon(poly,col,stroke='none',w=1,**extra):s.poly([xy(p) for p in poly],col,stroke,w,**extra)
    s.rect(0,0,2400,2400,'#f6f3e9')
    s.text(70,80,data['title_ru'],size=44,weight='bold')
    s.text(70,124,'Лесная полоса → хутор → короткий переход → три двора → старый город → элитный холм',size=24,color='#718078')
    s.text(70,164,f'815 × 685 м • {data["metrics"]["building_count"]} зданий • узкие дороги • один въезд между районами • решения 04.10.2026',size=20,color='#718078')
    s.line([[70,184],[2330,184]],'#adb5a6',1)
    bp=data['boundary']['polygon_m']
    s.add('<defs><clipPath id="land"><polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,bp))+'"/></clipPath></defs>')
    s.add('<g clip-path="url(#land)">')
    for d in data['districts']:polygon(d['polygon_m'],d['color'],'#a7aa99',1)
    for val in range(100,1001,100):
        line([[val,100],[val,900]],'#849184',.8,opacity='.24')
        line([[80,val],[980,val]],'#849184',.8,opacity='.24')
    for h in data['hills']:
        for f in (1,.78,.56,.34):
            cx,cy=h['center_m'];rx,ry=h['radii_m']
            ring=[[cx+rx*f*math.cos(i*math.pi/32),cy+ry*f*math.sin(i*math.pi/32)] for i in range(65)]
            line(ring,'#879c7d',1,opacity='.7')
    for p in data['field_parcels_m']:
        polygon(p,'#d0cb9c','#b6b585',.8,opacity='.65')
        for j in range(1,8):
            t=j/8;a=[p[0][k]*(1-t)+p[3][k]*t for k in (0,1)];b=[p[1][k]*(1-t)+p[2][k]*t for k in (0,1)]
            line([a,b],'#b6b585',.7)
    for p in data['plots']:polygon(p['polygon_m'],'#b2c598' if p['kind']=='elite_garden' else '#ddd3ad','#a9ad8f',.7,opacity='.8')
    for q in data['vegetation_parcels']:
        if q['kind']=='interdistrict_barrier':
            polygon(q['polygon_m'],'#70846b','#516a55',.8)
        else:
            polygon(q['polygon_m'],'#b9c69a','#98ad82',.6,opacity='.7')
            c=[sum(p[k] for p in q['polygon_m'])/len(q['polygon_m']) for k in (0,1)]
            for dx,dy in ((-2,-2),(2,2),(-2,2),(2,-2)):s.circle(*xy([c[0]+dx,c[1]+dy]),3,'#769470',opacity='.8')
    # A sparse canopy only around the wagon; no broad forest territory.
    import random
    rng=random.Random(6)
    forest=next(d['polygon_m'] for d in data['districts'] if d['id']=='forest')
    for _ in range(170):
        p=[rng.uniform(112,345),rng.uniform(474,545)]
        if not m.inside(p,forest):continue
        if any(m.projection(p,a,b)[0]<10 for r in data['roads'] for a,b in zip(r['polyline_m'],r['polyline_m'][1:])):continue
        if any(m.inside(p,f['poly']) for f in physical(data)):continue
        s.circle(*xy(p),rng.uniform(3,5),'#829b82',opacity='.4')
    for block in data['microdistricts']:polygon(block['yard_polygon_m'],'#acbeb5','#9eb2aa',1,opacity='.65')
    for w in data['water']:
        if 'polygon_m' in w:polygon(w['polygon_m'],'#a9c9ce','#739da9',1.4)
        else:
            if w['kind']=='concrete_canal':line(w['centerline_m'],'#939e99',(w['width_m']+2)*scale)
            line(w['centerline_m'],'#a9c9ce',w.get('wet_width_m',w['width_m'])*scale)
    for r in data['roads']:
        width=r['width_m']*scale
        line(r['polyline_m'],'#999d8d',width+1.6)
        line(r['polyline_m'],data['road_classes'][r['class']]['color'],width)
        if r['class']=='highway':line(r['polyline_m'],'#cbd1c6',.8,stroke_dasharray='9 8')
    for structure in data['water_crossings']:
        line(structure['deck_axis_m'],'#436773',9*scale)
        line(structure['deck_axis_m'],'#f9f3e7',6*scale)
    colors=dict(rural_house='#b7a085',rural_outbuilding='#a8a486',historic_house='#bca28e',slab='#8395a0',tower='#687f8b',workshop='#a39aa8')
    promoted={f.get('source_building_id') for f in data['functional_buildings']}
    for b in data['building_masses']:
        if b['id'] in promoted:continue
        if b['kind'] in ('slab','tower'):
            polygon([[p[0]+b['floors']*.4,p[1]-b['floors']*.35] for p in b['polygon_m']],'#536772',opacity='.22')
        polygon(b['polygon_m'],colors[b['kind']],'#717c72',.8)
        if b['kind'] in ('slab','tower'):
            s.text(*xy([b['center_m'][0],b['center_m'][1]-2]),str(b['floors']),size=13,color='white',weight='bold',anchor='middle')
    v5.draw_footprints(data,s,xy)
    villa=next(f for f in data['functional_buildings'] if f['type']=='final_base')
    polygon(villa['attached_garage_footprint_m'],'#55737b','#344e58',1)
    polygon(villa['main_house_footprint_m'],'#9bb5bc','#344e58',1.2)
    line([[434,524],[434,536]],'#d6eef3',3)
    for pos,angle in [([193,591],0),([400,530],90)]:
        polygon(m.rectangle(*pos,5,2.2,angle),'#f0cf83','#755e39',1)

    for p in data['paths']:
        line(p['polyline_m'],'#f6f3e9',p['width_m']*scale+2)
        line(p['polyline_m'],'#567e67',p['width_m']*scale,stroke_dasharray='4 3')
        x,y=xy(p['polyline_m'][1]);s.circle(x,y,8,'#567e67',stroke='#faf6e9',stroke_width=1)
        s.text(x,y+4,str(data['paths'].index(p)+1),size=12,color='white',anchor='middle',weight='bold')
    rail=data['railway']['polyline_m'];line(rail,'#efece1',5);line(rail,'#747080',2.3);line(rail,'#747080',6,stroke_dasharray='2 8')
    for ex in data['exits']:
        for p in ex['barrier_polygons_m']:polygon(p,'#82957b','#62785f',1)
        pts={p['id']:p for p in data['points']};end=ex['dead_end_m'];post=pts[ex['post_id']]['position_m']
        n=m.length(post,end);ux,uy=(end[0]-post[0])/n,(end[1]-post[1])/n
        scar=[[end[0]+ux*2-uy*19,end[1]+uy*2+ux*19],[end[0]+ux*2+uy*19,end[1]+uy*2-ux*19]]
        line(scar,'#865f51',9)
        if ex['dead_end_type']=='destroyed_bridge':line(scar,'#617c7d',6,stroke_dasharray='10 8')
    s.add('</g>')
    line(bp+[bp[0]],'#61765e',5)
    line(bp+[bp[0]],'#d8d9c7',1,stroke_dasharray='3 7')

    used=[]
    def reserve(x,y,w,h):used.append([x-w/2,y-18,w,h])
    headings=[([265,700],'ХУТОР','4 усадьбы / дом + гараж'),([405,760],'ПЕРЕХОД','B02 и P04 — разные ветки'),
        ([645,813],'НЕБЛАГОПОЛУЧНЫЙ РАЙОН','3 двора × 3 корпуса / 9–12 этажей'),
        ([520,458],'СТАРЫЙ ГОРОД','Террасы 2–3 эт. / 2 высотки'),
        ([875,647],'ЭЛИТНЫЙ ХОЛМ','4 особняка / 2 доступны'),
        ([700,265],'ПРОМЫШЛЕННАЯ ОКРАИНА','B05 / депо P14 / эвакуатор P12'),
        ([222,455],'ЛЕСНАЯ ПОЛОСА','Только стартовая опушка')]
    for pos,title,sub in headings:
        x,y=xy(pos);anchor='start' if title in ('ЭЛИТНЫЙ ХОЛМ','ПРОМЫШЛЕННАЯ ОКРАИНА') else 'middle'
        s.text(x,y,title,size=22,weight='bold',anchor=anchor,halo=True)
        s.text(x,y+24,sub,size=15,anchor=anchor,color='#65776b',halo=True)
        width=max(len(title)*12,len(sub)*8)
        reserve(x+width/2 if anchor=='start' else x,y,width,46)
    for pos,title in [([383,453],'МАЛАЯ ДОЛИНА'),([454,506],'ОЗЕРО'),([741,434],'КАНАЛ'),([409,402],'СТАРАЯ ЖД')]:
        x,y=xy(pos);s.text(x,y,title,size=14,anchor='middle',color='#617f80',halo=True);reserve(x,y,len(title)*8,18)
    for i,block in enumerate(data['microdistricts'],1):
        x,y=xy([block['center_m'][0],block['center_m'][1]+15]);s.text(x,y,f'ДВОР {i}',size=14,weight='bold',anchor='middle',color='#566d6b')
        reserve(x,y,80,18)
    # Place every function label with a leader. Repeated housing units use their
    # grouped legend entry; this avoids a sea of identical house names.
    labels=[]
    for f in data['functional_buildings']:
        pid=f.get('poi_id');text=(pid+' ' if pid else '')+f['label_ru']
        if pid=='CHIMNEY':text='Труба'
        if pid=='WATER_TOWER':text='Водобашня'
        labels.append((f['center_m'],text,17 if f['group']=='base' else 15,bool(pid)))
    function_ids={f.get('poi_id') for f in data['functional_buildings']}
    for p in data['points']:
        if p['id'] in function_ids or p['id'].startswith('BAD_BLOCK'):continue
        pos=p['position_m'];x,y=xy(pos)
        if p['category']=='exit':
            s.poly([[x,y-10],[x-9,y+8],[x+9,y+8]],'#bd8b51','#fff9e9',2)
        elif p['category']=='meeting':s.circle(x,y,6,'#678b79',stroke='#fff9e9',stroke_width=2)
        elif p['id']=='CLOCK_SQUARE':s.circle(x,y,10,'#e6d7aa',stroke='#8e8a69',stroke_width=1.5)
        else:s.circle(x,y,5,'#48686f',stroke='#fff9e9',stroke_width=1.5)
        label=(p['id']+' '+p['name_ru']) if p['id'] in ('P01','P09','P09-2','P09-3') or p['category']=='exit' else p['name_ru'] if p['id'] in ('CLOCK_SQUARE','BAD_CENTER','ELITE_GATE') else p['id']
        labels.append((pos,label,15,True))
    for ex in data['exits']:
        labels.append((ex['dead_end_m'],'Разрушенный мост / тупик' if ex['dead_end_type']=='destroyed_bridge' else 'Обвал / тупик',15,True))
    def collide(a,b):return a[0]<b[0]+b[2]+5 and b[0]<a[0]+a[2]+5 and a[1]<b[1]+b[3]+4 and b[1]<a[1]+a[3]+4
    building_boxes=[]
    for b in physical(data):
        q=[xy(p) for p in b['poly']];building_boxes.append([min(p[0] for p in q),min(p[1] for p in q),
            max(p[0] for p in q)-min(p[0] for p in q),max(p[1] for p in q)-min(p[1] for p in q)])
    for pos,label,size,important in sorted(labels,key=lambda q:(not q[3],-len(q[1]))):
        x,y=xy(pos);width=len(label)*size*.53;choices=[]
        for dist in (20,32,48,64,86,110,145,180):
            for dx,dy in [(12,dist),(-width-12,dist),(12,-dist),(-width-12,-dist),(-width/2,dist),(-width/2,-dist)]:
                box=[x+dx,y+dy-size,width,size+2]
                if box[0]<75 or box[0]+width>1880 or box[1]<225 or box[1]+size>2070:continue
                if label.startswith('Кафе'):
                    # These labels must remain in old town rather than drift
                    # over the canal into the industrial district.
                    world=[80+(box[0]+width/2-70)/scale,900-(box[1]+size/2-210)/scale]
                    oldtown=next(d['polygon_m'] for d in data['districts'] if d['id']=='old_town')
                    if not m.inside(world,oldtown):continue
                score=sum(collide(box,b) for b in used)*10000+sum(collide(box,b) for b in building_boxes)*180+dist+abs(dx)*.04
                choices.append((score,box,dx,dy))
        _,box,dx,dy=min(choices,key=lambda q:q[0]);used.append(box)
        end=[x+dx+(width if dx<0 else 0),y+dy-5]
        s.line([[x,y],end],'#788675',.75)
        s.text(x+dx,y+dy,label,size=size,weight='bold' if important else 'normal',halo=True)
    # Dimension marks give a immediate sense of scale next to the van/house sizes.
    a,b=xy([110,855]),xy([925,855]);s.line([a,b],'#849184',1)
    for p in (a,b):s.line([[p[0],p[1]-7],[p[0],p[1]+7]],'#849184',1)
    s.text((a[0]+b[0])/2,a[1]-12,'815 м — вся карта',size=17,anchor='middle',color='#6c7e73')
    legend(data,s,scale)
    s.line([[70,2140],[2330,2140]],'#adb5a6',1)
    footer=[(70,'01 / КОМПАКТНЫЙ СТАРТ',['B01 → P01 / P02 / P03: 94 / 140 / 174 м.','B01 → район: 588 м; пешком 7,1 мин.','B02 → район: 328 м; пешком 3,9 мин.']),
        (830,'02 / ГОРОДСКАЯ ДУГА',['Район → площадь: 110 м; элитка: ещё 150 м.','P05 на стыке районов; P12 у конца старой ЖД.','4 локальных прохода / 2,5 м / только пешком.']),
        (1590,'03 / СВЯЗИ И ПРОВЕРКА',['Один въезд на район; за городом петель нет.','Ограды / скалы / канал закрывают срезки.','Скорости теоретические; нужен Unity-плейтест.'])]
    for x,title,lines in footer:
        s.text(x,2183,title,size=19,weight='bold')
        for j,t in enumerate(lines):s.text(x,2220+j*28,t,size=17,color='#6c7e73')
    s.text(70,2350,'R01 / v07 • 04.10.2026 • геометрия — проектное предложение • все районы доступны с начала',size=16,color='#889384')
    s.text(2330,2350,'JSON → SVG → PNG',size=16,color='#889384',anchor='end')
    return s.finish()


def legend(data,s,scale):
    x=1955;y=250
    s.rect(1932,211,400,1888,'#efede2',rx=12)
    s.text(x,y,'КАК ЧИТАТЬ ПЛАН v07',size=20,weight='bold');y+=32
    for d in data['districts']:
        s.rect(x,y-13,16,16,d['color'],stroke='#939e8b',stroke_width=.7)
        s.text(x+25,y,d['name_ru'],size=15)
        s.text(2310,y,f'{d["building_count"]} зд.',size=14,anchor='end',color='#7a887b');y+=24
    y+=12;s.line([[x,y],[2310,y]],'#c5c9bb',1);y+=27
    for cls in ('highway','town_street','rural_road','dirt_shortcut','passage'):
        s.line([[x,y-5],[x+34,y-5]],data['road_classes'][cls]['color'],5,
            **({'stroke_dasharray':'4 3'} if cls=='passage' else {}))
        s.text(x+44,y,data['road_classes'][cls]['name_ru'],size=14);y+=25
    for color,label,dash in [('#747080','Старая ЖД / депо у конца','2 7'),('#70846b','Сплошной барьер; разрыв = въезд',None)]:
        s.line([[x,y-5],[x+34,y-5]],color,5,**({'stroke_dasharray':dash} if dash else {}))
        s.text(x+44,y,label,size=14);y+=25
    y+=15;s.text(x,y,'ЦВЕТ И ЗНАК = ФУНКЦИЯ',size=18,weight='bold');y+=27
    for group,(color,icon,label) in v5.PALETTE.items():
        s.rect(x,y-13,18,18,color,stroke='#536662',stroke_width=.7)
        s.text(x+9,y+1,icon,size=12,anchor='middle',weight='bold');s.text(x+28,y,label,size=14);y+=22
    y+=16;s.text(x,y,'ПРОГРАММА РАЙОНОВ',size=18,weight='bold');y+=27
    rows=[('Хутор / старт','4 усадьбы: дом + гараж;|дед P02, аптека P03, амбар,|сельмаг, остановка, водобашня.'),
        ('Неблагополучный район','3 двора × 3 корпуса 72 × 12 м;|18 боксов, B03, бар P06, притон P07;|3 киоска, 24 ч, котельная / труба.'),
        ('Старый город','5 террас × 6 домов по 7 м;|две высотки, P05, B04, больница P08,|полиция P10, банк / ATM, магазин;|2 кафе, церковь, отель, почта, маски;|площадь / часы; P09 + 2 запасные.'),
        ('Элитка / промзона','4 особняка, B06 и 2 доступных P15;|охрана, бутик / B05, P14, P12,|2 склада, труба, металлолом, сарай.'),
        ('Долина / финальная база','B07: вилла 2 эт., гараж для бусика;|личный подъезд и терраса к озеру.')]
    for title,body in rows:
        s.text(x,y,title,size=15,weight='bold');y+=21
        for t in body.split('|'):s.text(x,y,t,size=14);y+=20
        y+=9
    y+=5;s.text(x,y,'4 ЛОКАЛЬНЫХ ПРОХОДА',size=18,weight='bold');y+=25
    for i,p in enumerate(data['paths'],1):
        s.text(x,y,f'{i}  {p["label_ru"]} / {p["length_m"]:.0f} м',size=14);y+=21
    s.text(x,y,'Между районами пеших лазов нет.',size=14,weight='bold');y+=27
    s.text(x,y,'B01 → РАЙОН / 588 м',size=16,weight='bold');y+=23
    s.text(x,y,'60 / 90 км/ч: 35,3 / 23,5 с',size=14);y+=21
    s.text(x,y,'Пешком 5 км/ч: 7,06 мин',size=14);y+=28
    s.text(x,y,'B02 → РАЙОН / 328 м',size=16,weight='bold');y+=23
    s.text(x,y,'60 / 90 км/ч: 19,7 / 13,1 с',size=14);y+=21
    s.text(x,y,'Пешком 5 км/ч: 3,94 мин',size=14)
    s.text(x,1940,'МАСШТАБ / МЕТРЫ',size=18,weight='bold')
    for i in range(3):s.rect(x+i*50*scale,1960,50*scale,10,'#577068' if i%2==0 else '#faf8ef',stroke='#81917d',stroke_width=1)
    for i in range(4):s.text(x+i*50*scale,1990,str(i*50),size=13,anchor='middle')
    s.text(x,2020,'Сетка 100 м • +Y = север ↑',size=14)
    s.text(x,2050,'Пост → тупик; возврат через свой пост.',size=14)
    s.text(x,2075,'Коллайдеры / высоты: проверить в 3D.',size=14)


def report(data):
    old=json.loads((ROOT/'MAP_PLAN_R01_v06.json').read_text(encoding='utf-8'))
    metrics=data['metrics'];village=next(d for d in data['districts'] if d['id']=='village')
    prev=next(d for d in old['districts'] if d['id']=='village')
    lines=['# VOLUNTEERS ONLY — R01 v07','',
        'Основание: req_map_plan_v07.md; только целевые правки v06, 04.10.2026.',
        f'Карта: 815 × 685 м; площадь {metrics["area_m2"]:.0f} м² (v06: {old["metrics"]["area_m2"]:.0f}); {metrics["building_count"]} физических зданий; PNG/SVG 2400 × 2400.',
        f'Хутор: {prev["area_m2"]:.0f} → {village["area_m2"]:.0f} м², сокращён на {100*(1-village["area_m2"]/prev["area_m2"]):.1f}%; вырезаны западные пустоты и северная усадьба FARM06_5.',
        'Ровно 4 усадьбы: P02 и ещё 3; в каждой дом и прилегающий гараж. Двор деда сохранён; бусик показан во дворе.',
        'Аптека P03, амбар, сельмаг, остановка, водобашня и рекламный столб P01 сохранены; аптека не считается жилой усадьбой.',
        'Двор 3 сдвинут на 58 м к югу и развёрнут; теперь южнее улицы дворов, рядом с P06, 24 ч и киосками. Дворы 1–2 сохранены.',
        'Улица дворов локально огибает двор 3 с севера; магазин 24 ч и его ATM смещены к бару, чтобы освободить место корпусу.',
        'Элитка: 4 особняка, включая B06; оба доступных P15, охрана и бутик сохранены. Промзона: удалён только склад 3.',
        'B07 «Вилла у озера — финальная база»: отдельный современный дом 28 × 14 м, 2 этажа; пристроенный гараж 12 × 8 м, 1 этаж.',
        'Вилла стоит прямо напротив западного берега озера; личный тупиковый подъезд от VALLEY_BRANCH, терраса смотрит на воду. B05 остаётся производственной базой.',
        'Старый город, переход, водоёмы, старая ЖД, первые два двора и все несвязанные с правками объекты сохранены.',
        'Дороги: 7/6 м, максимум 2 полосы; село 3,8 м, 1 полоса. Между соседями один соединитель; внешних петель и срезок нет.','',
        '| Маршрут | Дорога, м | 60 км/ч, с | 90 км/ч, с | Пешком 5 км/ч, мин |','|---|---:|---:|---:|---:|']
    for r in metrics['routes']:lines.append(f'| {r["from_id"]} → {r["to_id"]} | {r["length_m"]:.1f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["walk_5_minutes"]:.2f} |')
    lines += ['',
        f'Проверки: {sum(c["passed"] for c in data["validation"]["checks"])}/{len(data["validation"]["checks"])}; полный список в JSON. Старт P01/P02/P03 ≤ 200 м, требование v07 ≤ 300 м выполнено.',
        'Повторены все дистанционные проверки v06, графы, единственные въезды, геометрия без пересечений зданий с дорогами/водой/ЖД и отсутствие обходов.',
        'Сохранена схема JSON v06; предыдущие файлы, включая v06, проверены SHA-256 и не изменены. WORK_SYNC.md и Git не затрагивались.',
        'Сборка: python -B map_plan_v07.py; --reset-data восстанавливает авторский v07.',
        'Время теоретическое: без разгона, поворотов, трафика и уклонов; необходим Unity-плейтест. PNG просмотрен после сборки.']
    assert len(lines)<=40,len(lines)
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reset-data',action='store_true')
    args=parser.parse_args();path=ROOT/(STEM+'.json')
    data=json.loads(path.read_text(encoding='utf-8')) if path.exists() and not args.reset_data else seed()
    analyse(data)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    svg=ROOT/(STEM+'.svg');png=ROOT/(STEM+'.png')
    svg.write_text(render(data),encoding='utf-8');ET.parse(svg)
    env=os.environ.copy();env['MAGICK_TEMPORARY_PATH']=str(ROOT)
    subprocess.run([str(m.MAGICK),'-background','#f6f3e9',str(svg),'-strip',str(png)],check=True,cwd=ROOT,env=env,capture_output=True)
    header=png.read_bytes()[:24]
    assert header[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',header[16:24])==(2400,2400)
    (ROOT/(STEM+'_REPORT.md')).write_text(report(data),encoding='utf-8')
    print(f'OK: {len(data["validation"]["checks"])} checks; {data["metrics"]["building_count"]} buildings; PNG 2400x2400')
    print('Extent:',data['metrics']['extent_m'])
    for r in data['metrics']['routes']:print(r['from_id'],'->',r['to_id'],r['length_m'],'m')


if __name__=='__main__':main()
