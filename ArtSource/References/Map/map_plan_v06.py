#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild v06 only: python -B map_plan_v06.py [--reset-data].
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
STEM='MAP_PLAN_R01_v06'
WIDTHS=dict(highway=7,town_street=6,rural_road=3.8,dirt_shortcut=3.5,passage=2.5)
NAMES=dict(forest='Лесная полоса',village='Хутор',transition='Переход',
    residential='Неблагополучный район',old_town='Старый город',elite='Элитный холм',
    industrial='Промышленная окраина',fields='Малая долина')
ROUTES=[('B01','P01'),('B01','P02'),('B01','P03'),('B01','BAD_CENTER'),
    ('B02','BAD_CENTER'),('B02','P04'),('BAD_CENTER','CLOCK_SQUARE'),
    ('CLOCK_SQUARE','ELITE_GATE'),('B03','P05'),('CLOCK_SQUARE','P14'),('P14','P12'),('B01','B05')]


def hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
        if p.is_file() and (p.name in ('build_map_plan.py','map_plan_v04.py','map_plan_v05.py')
        or any(p.name.startswith('MAP_PLAN_R01_'+r) for r in ('v02','v03','v04','v05')))}


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
    old=json.loads((ROOT/'MAP_PLAN_R01_v05.json').read_text(encoding='utf-8'))
    data=copy.deepcopy(old)
    for k in ('roads','points','building_masses','functional_buildings','functional_sites',
        'plots','microdistricts','farmsteads','vegetation_parcels','paths','districts','hills',
        'water','field_parcels_m','geometry_repairs','land_transfers','replaced_generic_building_ids','water_crossings'):
        data[k]=[]
    data.update(revision='v06',title_ru='VOLUNTEERS ONLY — план карты R01 / v06')
    data['coordinates']['origin']='bottom-left of 1000 x 1000 metre reference frame'
    data['specification']['brief_override']='req_map_plan_v06.md, final items 6–9, 2026-10-04'
    data['provenance']=dict(brief='req_map_plan_v06.md',source_schema='MAP_PLAN_R01_v05.json',
        owner_decisions_date='2026-10-04',method='new compact authored layout; real architectural dimensions',
        previous_files_sha256=hashes())
    data['comparison']={'v05':{'extent_m':old['metrics']['extent_m']},'policy':'replanned; buildings not uniformly scaled'}
    data['planning_notes_ru']=[
        'Последние пункты 6–9 brief имеют приоритет над ранними размерами и дистанциями.',
        'Лес — полоса у вагона; малая долина, короткая река, поля без объездных дорог.',
        'Между соседними районами один въезд; грунтовых срезок между районами нет.',
        'Непрерывные тонкие ограды и скальные пояса; только дорожные разрывы, без пеших лазов.',
        'Три двора по три корпуса; пять террас по шесть домов; две высотки старого города.',
        'Все районы доступны с начала; охрана элитки не является сюжетным замком.',
        'Времена по графу; темп и физические барьеры проверяются в Unity.']
    data['boundary']=dict(polygon_m=[[110,470],[350,470],[350,390],[510,390],[510,280],
        [625,280],[625,140],[675,140],[675,280],[800,280],[800,470],[925,470],
        [925,620],[870,620],[870,825],[470,825],[470,780],[110,780]],
        barrier='continuous thin rock scarp and fence; road dead ends inside',barrier_band_m=5)
    colors={d['id']:d['color'] for d in old['districts']}
    polygons={
        'forest':m.rectangle(230,510,240,80),'village':m.rectangle(230,665,240,230),
        'transition':m.rectangle(410,660,120,240),'residential':m.rectangle(670,722.5,400,205),
        'old_town':m.rectangle(635,530,330,180),'elite':m.rectangle(862.5,545,125,150),
        'industrial':[[510,280],[625,280],[625,140],[675,140],[675,280],[800,280],[800,440],[510,440]],
        'fields':[[350,390],[510,390],[510,440],[470,440],[470,540],[350,540]]}
    for id,poly in polygons.items():
        data['districts'].append(dict(id=id,name_ru=NAMES[id],color=colors[id],polygon_m=poly,
            parent_id=None,notes_ru='Программа v06; размеры в метрах.'))
    data['hills']=[dict(id='HILL_ELITE',center_m=[864,550],radii_m=[58,68],height_target_m=18)]
    data['field_parcels_m']=[m.rectangle(390,480,46,34),m.rectangle(407,420,55,24)]
    data['water']=[dict(id='LAKE',kind='lake',name_ru='Малое озеро',
        polygon_m=[[437,495],[443,515],[459,525],[471,513],[466,491],[451,483]]),
        dict(id='RIVER_N',kind='river',name_ru='Короткая река',width_m=6,centerline_m=[[454,540],[453,531],[459,523]]),
        dict(id='RIVER_S',kind='river',name_ru='Короткая река',width_m=6,centerline_m=[[452,485],[456,465],[470,450],[510,440]]),
        dict(id='CANAL',kind='concrete_canal',name_ru='Канал без пеших мостов',
            centerline_m=[[510,440],[800,440]],width_m=8,wet_width_m=4,depth_target_m=3,
            banks='steep_concrete',bed='uneven_silt_and_concrete',van_entry_point='P13-3',short_tunnel_road_ids=[])]
    data['railway']=dict(polyline_m=[[202,496],[300,480],[355,448],[420,408],[500,400],
        [540,385],[680,385],[775,360]],from_point='B01',to_point='P14',service_road_id=None,
        active_trains=False,road_crossings=[],water_bridges=[])
    for cls,width in WIDTHS.items():
        data['road_classes'][cls]['width_m']=width
        name={'highway':'Шоссе / проспект','town_street':'Городская улица','rural_road':'Сельская дорога',
            'dirt_shortcut':'Грунт (срезок нет)','passage':'Локальный пеший проход'}[cls]
        data['road_classes'][cls]['name_ru']=f'{name} — {width:g} м'
    def road(id,poly,cls='town_street',districts=None,**extra):
        data['roads'].append(dict(id=id,polyline_m=poly,width_m=WIDTHS[cls],**{'class':cls},district_ids=districts or [],**extra))
    road('START_ROAD',[[190,510],[230,510],[230,580]],'rural_road',['forest','village'])
    road('V_MAIN',[[230,580],[300,600],[350,600]],'rural_road',['village'])
    road('V_NORTH',[[300,600],[300,700],[300,765]],'rural_road',['village'])
    road('V_WEST_BRANCH',[[300,700],[230,700]],'rural_road',['village'])
    road('ARC_RURAL',[[350,600],[405,600],[405,650],[470,650]],'rural_road',['transition'])
    road('HUT_BRANCH',[[405,650],[405,730]],'rural_road',['transition'])
    road('RECEPTION_BRANCH',[[440,650],[440,691]],'rural_road',['transition'])
    road('ARC_AVENUE',[[470,650],[650,650],[650,620],[650,540],[800,540]],'highway',['residential','old_town'])
    road('R_COURTS',[[500,675],[820,675]],districts=['residential'])
    road('R_LINK',[[650,650],[650,675]],districts=['residential'])
    road('O_SPINE',[[650,540],[650,480]],districts=['old_town'])
    road('O_RING',[[525,590],[750,590],[750,480],[525,480],[525,590]],districts=['old_town'])
    road('I_CONNECT',[[650,480],[650,400],[650,330]],districts=['old_town','industrial'])
    road('I_YARD',[[550,330],[650,330],[760,330]],districts=['industrial'])
    road('ELITE_GATE_ROAD',[[800,540],[850,540]],districts=['elite'])
    road('ELITE_NORTH',[[850,540],[850,590],[900,590]],districts=['elite'])
    road('ELITE_SOUTH',[[850,540],[850,485],[900,485]],districts=['elite'])
    road('EXIT_NW',[[230,700],[170,735],[140,760]],'highway',['village'])
    road('R_GARAGE_LANE',[[820,675],[820,790]],districts=['residential'])
    road('EXIT_NE',[[820,790],[845,805]],'highway',['residential'])
    road('EXIT_S',[[650,330],[650,220],[650,160]],'highway',['industrial'])
    originals={p['id']:p for p in old['points']}
    def poi(id,pos,dist,name=None,category=None):
        p=copy.deepcopy(originals.get(id,dict(id=id,canonical_id=id,name_ru=name or id,
            category=category or 'landmark',label_offset_px=[10,-12])))
        p.update(position_m=pos,district_id=dist);p.pop('road_node_id',None)
        if name:p['name_ru']=name
        if category:p['category']=category
        data['points'].append(p);return p
    def mass(id,dist,kind,c,w,h,floors=1,angle=0,**extra):
        b=dict(id=id,district_id=dist,kind=kind,center_m=c,width_m=w,depth_m=h,
            floors=floors,polygon_m=m.rectangle(*c,w,h,angle),**extra)
        data['building_masses'].append(b);return b
    farms=[([200,600],True),([275,564],True),([320,642],False),([270,669],False),([316,730],False),([209,659],False)]
    for i,(c,start) in enumerate(farms,1):
        ids=[]
        local=[(0,0,14,10,'rural_house'),(18,0,8,7,'rural_outbuilding'),
               (-18,0,12,8,'rural_outbuilding') if i==2 else (0,18,12,8,'rural_outbuilding')]
        for j,(dx,dy,w,h,kind) in enumerate(local,1):
            ids.append(mass(f'F06_{i}_{j}','village',kind,[c[0]+dx,c[1]+dy],w,h)['id'])
        yard=m.rectangle(c[0],c[1]+5,54,26) if i==2 else m.rectangle(c[0]+7,c[1]+8,42,40)
        data['farmsteads'].append(dict(id=f'FARM06_{i}',center_m=c,yard_polygon_m=yard,building_ids=ids,start_cluster=start,district_id='village'))
        data['plots'].append(dict(id=f'FARM06_{i}',kind='farmstead',district_id='village',polygon_m=yard))
        data['vegetation_parcels'].append(dict(id=f'ORCHARD06_{i}',kind='orchard',district_id='village',polygon_m=m.rectangle(c[0]+18,c[1]+20,9,9)))
    mass('WAGON06','forest','rural_outbuilding',[190,520],18,3)
    for i,cx in enumerate((535,650,765),1):
        ids=[]
        for j,(dx,dy,a,floors) in enumerate([(0,40,0,12),(-40,-4,90,9),(40,-4,90,10)],1):
            ids.append(mass(f'R06_C{i}_S{j}','residential','slab',[cx+dx,725+dy],72,12,floors,a)['id'])
        data['microdistricts'].append(dict(id=f'MB06_{i}',center_m=[cx,725],angle=0,yard_polygon_m=m.rectangle(cx,721,62,64),
            building_ids=ids,arrangement='U',opening_direction='south',shared_courtyard=True))
        road(f'COURT_ACCESS_{i}',[[cx,675],[cx,705]],districts=['residential'])
        data['paths'].append(dict(id=f'PASS06_BAD_{i}',**{'class':'passage'},district_id='residential',width_m=2.5,
            polyline_m=[[cx,705],[cx+20,705],[cx+20,675]],label_ru=f'Выход из двора {i}',walkable=True,van_access=False,kind='yard_exit'))
    for row,x in enumerate((838,858),1):
        for j in range(9):mass(f'R06_G{row}_{j+1}','residential','workshop',[x,685+j*11],12,9,subtype='garage_box',garage_row=row)
    for i,(x,y) in enumerate(((536,565),(690,565),(536,515),(690,515),(580,462)),1):
        for j in range(6):
            b=mass(f'O06_T{i}_U{j+1}','old_town','historic_house',[x+j*7,y],7,12,2+i%2,terrace_id=f'T06_{i}',unit_width_m=7)
            data['plots'].append(dict(id=b['id']+'_FRONT',kind='front_yard',district_id='old_town',polygon_m=m.rectangle(x+j*7,y-10,7,6)))
    mass('O06_TOWER_1','old_town','tower',[608,566],22,20,14)
    mass('O06_TOWER_2','old_town','tower',[780,485],22,20,16)
    data['paths'].append(dict(id='PASS06_OLD',**{'class':'passage'},district_id='old_town',width_m=2.5,
        polyline_m=[[580,515],[580,480]],label_ru='Задний переулок',walkable=True,van_access=False,kind='rear_alley'))

    def belt(id,a,b,gate,dist,material='fence_rock_grove',width=4):
        horizontal=abs(a[1]-b[1])<.001;axis=0 if horizontal else 1
        for j,(lo,hi) in enumerate([(a[axis],gate[axis]-gate[2]/2),(gate[axis]+gate[2]/2,b[axis])],1):
            if hi<=lo:continue
            poly=m.rectangle((lo+hi)/2,a[1],hi-lo,width) if horizontal else m.rectangle(a[0],(lo+hi)/2,width,hi-lo)
            data['vegetation_parcels'].append(dict(id=f'{id}_{j}',kind='interdistrict_barrier',district_id=dist,
                polygon_m=poly,blocks_foot=True,blocks_van=True,material=material,height_target_m=2.4,
                continuity_group=id,gate_road_id=gate[3]))
    belt('FOREST_VILLAGE',[110,550],[350,550],[230,550,3.8,'START_ROAD'],'forest')
    belt('RURAL_TRANSITION',[350,390],[350,780],[350,600,3.8,'ARC_RURAL'],'transition')
    belt('TRANSITION_URBAN',[470,440],[470,825],[470,650,7,'ARC_AVENUE'],'transition')
    data['vegetation_parcels'].append(dict(id='VALLEY_URBAN',kind='interdistrict_barrier',district_id='fields',
        polygon_m=m.rectangle(510,415,4,50),blocks_foot=True,blocks_van=True,material='fence_rock_grove',
        height_target_m=2.4,continuity_group='TRANSITION_URBAN'))
    belt('OLD_ELITE',[800,470],[800,620],[800,540,7,'ARC_AVENUE'],'elite',material='security_fence',width=2)
    data['vegetation_parcels'].append(dict(id='ELITE_NORTH_FENCE',kind='interdistrict_barrier',district_id='elite',
        polygon_m=m.rectangle(862.5,620,125,2),blocks_foot=True,blocks_van=True,material='security_fence',
        height_target_m=2.4,continuity_group='OLD_ELITE'))
    belt('BAD_OLD',[470,620],[800,620],[650,620,7,'ARC_AVENUE'],'residential',material='frontage_fence',width=2)
    belt('OLD_INDUSTRIAL',[510,440],[800,440],[650,440,6,'I_CONNECT'],'industrial',material='canal_bank',width=8)
    belt('VALLEY_NORTH',[350,540],[470,540],[390,540,3.8,'VALLEY_BRANCH'],'fields')
    # River access is a dead-end branch; no parallel interdistrict link.
    road('VALLEY_BRANCH',[[370,600],[370,558],[390,558],[390,520],[420,501],[432,501]],'rural_road',['transition','fields'])
    road('RIVER_ACCESS',[[420,501],[420,471],[451,471]],'rural_road',['fields'])
    ds={d['id']:d for d in data['districts']}
    occupied=[b['polygon_m'] for b in data['building_masses']]
    def clear(poly,dist):
        if not all(m.inside(p,data['boundary']['polygon_m']) and m.inside(p,ds[dist]['polygon_m']) for p in poly):return False
        if any(overlap(poly,p) for p in occupied):return False
        if any(gap(poly,a,b)<r['width_m']/2+1.5 for r in data['roads']+data['paths'] for a,b in zip(r['polyline_m'],r['polyline_m'][1:])):return False
        if any(overlap(poly,q['polygon_m']) for q in data['vegetation_parcels'] if q['kind']=='interdistrict_barrier'):return False
        if any(('polygon_m' in w and overlap(poly,w['polygon_m'])) or any(gap(poly,a,b)<w['width_m']/2+1.5
            for a,b in zip(w.get('centerline_m',[]),w.get('centerline_m',[])[1:])) for w in data['water']):return False
        return not any(gap(poly,a,b)<3 for a,b in zip(data['railway']['polyline_m'],data['railway']['polyline_m'][1:]))
    def add(id,typ,dist,label,group,target,w,h,storeys=1,pid=None,source=None,shape='rect',**extras):
        if source:
            b=next(b for b in data['building_masses'] if b['id']==source)
            c=b['center_m'];poly=b['polygon_m'];w=b['width_m'];h=b['depth_m'];storeys=b['floors']
        else:
            found=None
            for radius in range(0,81,2):
                for k in range(1 if radius==0 else 32):
                    c=[round(target[0]+radius*math.cos(k*math.pi/16),3),round(target[1]+radius*math.sin(k*math.pi/16),3)]
                    poly=v5.outline(m,c,w,h,shape)
                    if clear(poly,dist):found=(c,poly);break
                if found:break
            if not found:raise ValueError('No footprint '+id)
            c,poly=found;occupied.append(poly)
        color,icon,_=v5.PALETTE[group]
        f=dict(id='F06_'+id,type=typ,district=dist,district_id=dist,label_ru=label,group=group,center_m=c,
            width_m=w,depth_m=h,footprint_m=poly,storeys=storeys,footprint_shape=shape,color=color,icon=icon,**extras)
        if source:f['source_building_id']=source
        if pid:f['poi_id']=pid;poi(pid,c,dist)
        data['functional_buildings'].append(f);return f

    add('WAGON','wagon_base','forest','Вагон','base',[190,520],18,3,pid='B01',source='WAGON06')
    add('GRANDPA','grandpa_house','village','Дом деда','base',[200,600],14,10,pid='P02',source='F06_1_1')
    add('PHARM','pharmacy','village','Аптека','health',[275,564],14,10,pid='P03',source='F06_2_1')
    add('BARN','barn_yard','village','Амбар','rural',[200,618],12,8,source='F06_1_3')
    add('VSHOP','village_shop','village','Сельмаг','retail',[325,575],18,12)
    add('BUS','bus_stop','village','Остановка','service',[315,611],10,4)
    add('WATER','water_tower','village','Водобашня','landmark',[325,690],8,8,pid='WATER_TOWER',shape='round')
    add('HUT','hut','transition','Хижина','base',[391,730],16,10,pid='B02')
    add('BUYER','shadow_buyer','transition','Приёмка','shadow',[452,703],20,14,pid='P04')
    add('GAS','gas_station','transition','АЗС','service',[385,626],22,14,shape='L')
    add('RUINS','abandoned_farm','transition','Руины фермы','rural',[379,688],24,16,shape='U')
    for id,typ,label,group,c,w,h,pid in [
        ('GBASE','garage_base','База-гараж','base',[492,634],28,18,'B03'),('BAR','bar','Бар','food',[705,632],24,16,'P06'),
        ('DEN','den','Притон','shadow',[817,706],18,16,'P07'),('24','shop_24h','24 часа','retail',[760,632],24,14,None),
        ('BOILER','boiler_house','Котельная','industry',[780,800],30,18,None),
        ('K1','kiosk','Киоск 1','retail',[535,632],8,6,None),('K2','kiosk','Киоск 2','retail',[560,632],8,6,None),
        ('K3','kiosk','Киоск 3','retail',[585,632],8,6,None)]:
        f=add(id,typ,'residential',label,group,c,w,h,2 if id=='DEN' else 1,pid)
        if id=='BOILER':f['chimney_m']=[f['center_m'][0]+10,f['center_m'][1]+4]
    for id,typ,label,group,c,w,h,floors,pid in [
        ('REPAIR','car_workshop','Мастерская бусика','service',[680,605],32,18,1,'P05'),
        ('CLOCK','clock_tower','Часовая башня','landmark',[667,557],10,10,4,None),
        ('HOSPITAL','hospital','Больница','health',[779,582],36,26,3,'P08'),
        ('POLICE','police_station','Полиция','civic',[495,490],30,22,2,'P10'),
        ('BANK','bank','Банк / ATM','finance',[615,520],26,18,3,'P11'),
        ('ATM','atm_pavilion','Банкомат','finance',[620,490],6,5,1,'P11-3'),
        ('SUPER','supermarket','Супермаркет','retail',[582,606],32,20,1,None),
        ('CAFE1','cafe','Кафе у площади','food',[685,454],20,14,2,None),
        ('CAFE2','cafe','Кафе у проспекта','food',[733,605],20,14,2,None),
        ('CHURCH','church','Церковь','landmark',[598,538],24,30,2,None),
        ('HOTEL','small_hotel','Малый отель','lodging',[778,520],28,20,3,None),
        ('POST','post_office','Почта','service',[495,550],22,16,2,None),
        ('MASKS','clothes_masks_shop','Одежда / маски','retail',[720,455],22,14,2,None),
        ('HBASE','house_base','Дом-база','base',[495,585],24,18,3,'B04')]:
        add(id,typ,'old_town',label,group,c,w,h,floors,pid,shape='cross' if id=='HOSPITAL' else 'chapel' if id=='CHURCH' else 'rect')
    for i,c in enumerate(([821,577],[879,577],[902,545],[879,517],[819,499],[875,610],[821,609]),1):
        pid={1:'B06',2:'P15',4:'P15-2'}.get(i)
        f=add(f'MANSION_{i}','prestige_base' if i==1 else 'mansion','elite','Престижная база' if i==1 else f'Особняк {i}',
            'base' if i==1 else 'lodging',c,20,14,2,pid,accessible=pid in ('P15','P15-2'))
        garden=m.rectangle(*f['center_m'],28,22)
        # Trim the north garden to the security fence; keep the real house size.
        garden=[[min(923,max(802,q[0])),min(618.8,max(472,q[1]))] for q in garden]
        if i==2:garden=[[q[0],min(q[1],586.5)] for q in garden]
        data['plots'].append(dict(id=f'GARDEN06_{i}',kind='elite_garden',district_id='elite',polygon_m=garden,accessible=f['accessible']))
    add('GUARD','private_security','elite','Охрана','civic',[812,553],9,8)
    add('BOUTIQUE','boutique','elite','Бутик','retail',[821,528],18,10)
    for id,typ,label,group,c,w,h,pid in [
        ('COMPLEX','industrial_complex','Промкомплекс','base',[590,330],46,28,'B05'),
        ('DEPOT','depot','Депо / конец ЖД','industry',[760,354],36,20,'P14'),
        ('TOW','tow_yard','Эвакуатор','service',[703,360],20,12,'P12'),
        ('CHIMNEY','industrial_chimney','Труба','landmark',[550,347],8,8,'CHIMNEY'),
        ('WARE1','warehouse','Склад 1','industry',[581,374],30,18,None),
        ('WARE2','warehouse','Склад 2','industry',[710,299],30,18,None),
        ('WARE3','warehouse','Склад 3','industry',[759,299],30,18,None),
        ('SCRAP','scrapyard','Металлолом','industry',[550,296],22,14,None),
        ('MAINT','maintenance_shed','Ремонтный сарай','industry',[610,297],20,12,None)]:
        f=add(id,typ,'industrial',label,group,c,w,h,pid=pid,shape='round' if id=='CHIMNEY' else 'rect')
        if id in ('TOW','SCRAP'):data['functional_sites'].append(dict(id=f['id']+'_YARD',type='tow_parking' if id=='TOW' else 'scrap_storage',
            district_id='industrial',building_id=f['id'],polygon_m=m.rectangle(*f['center_m'],w+10,h+10)))
    for id,c,dist,name in [
        ('P01',[230,558],'village',None),('BAD_CENTER',[650,650],'residential',None),
        ('CLOCK_SQUARE',[650,540],'old_town',None),('ELITE_GATE',[800,540],'elite','Въезд в элитку'),
        ('P09',[608,588],'old_town','Встреча: за супермаркетом'),('P09-2',[730,488],'old_town','Встреча: сквер'),
        ('P09-3',[675,470],'old_town','Встреча: у канала'),('P11-2',[778,632],'residential','ATM магазина'),
        ('P13',[432,501],'fields','Озеро: доступ'),('P13-2',[451,471],'fields','Река: доступ'),
        ('P13-3',[620,450],'old_town','Канал: спуск'),('P13-4',[606,675],'residential',None),
        ('P13-5',[530,480],'old_town',None),('P16',[170,735],'village',None),
        ('P16-2',[820,790],'residential',None),('P16-3',[650,220],'industrial',None)]:poi(id,c,dist,name)
    for i,cx in enumerate((535,650,765),1):poi('BAD_BLOCK' if i==1 else f'BAD_BLOCK_{i}',[cx,705],'residential')
    data['exits']=[]
    for id,post,end,a,b,typ in [('NW','P16',[140,760],[150,745],[175,772],'landslide'),
        ('NE','P16-2',[845,805],[837,788],[824,817],'destroyed_bridge'),
        ('S','P16-3',[650,160],[635,200],[665,200],'landslide')]:
        ex=copy.deepcopy(next(e for e in old['exits'] if e['id']==id))
        p=next(p for p in data['points'] if p['id']==post)['position_m']
        n=m.length(p,end);ux,uy=(end[0]-p[0])/n,(end[1]-p[1])/n
        def local(poly):return [[round(p[0]+u*ux-v*uy,3),round(p[1]+u*uy+v*ux,3)] for u,v in poly]
        # Two L-shaped flanks meet behind the visible dead end. The only opening
        # to this pocket is the full-width post trigger at u=0.
        flanks=[local([(0,-16),(n+12,-16),(n+12,0),(n+4,0),(n+4,-8),(0,-8)]),
                local([(0,8),(n+4,8),(n+4,0),(n+12,0),(n+12,16),(0,16)])]
        ex.update(dead_end_m=end,dead_end_type=typ,barrier_polygons_m=flanks,
            barrier_width_m=8,barrier_height_target_m=8)
        ex['post_trigger_polygon_m']=local([(-1,-8),(1,-8),(1,8),(-1,8)])
        ex['post_trigger_width_m']=16
        ex.pop('dead_end_node_id',None);data['exits'].append(ex)
    add_access(data)
    pts={p['id']:p for p in data['points']}
    for id in ('P09','P09-2','P09-3'):data['functional_sites'].append(dict(id='SITE_'+id,type='meeting',district_id='old_town',
        position_m=pts[id]['position_m'],poi_id=id,label_ru=pts[id]['name_ru']))
    data['sightline'].update(clearance_reserve_width_m=8,status='proposed 3D sightline; no quality acceptance')
    data['distribution_targets']={'policy':'latest compact v06 brief overrides v05 density/area targets'}
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
    check('120–130 unique physical buildings',120<=len(phys)<=130,str(len(phys)))
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
    check('seven mansions, gardens, two accessible P15',len(mansions)==7 and sum(f['accessible'] for f in mansions)==2 and
        len([p for p in data['plots'] if p['kind']=='elite_garden'])==7)
    gardenhits=[p['id'] for p in data['plots'] if p['kind']=='elite_garden' and
        (not all(m.inside(q,ds['elite']['polygon_m']) for q in p['polygon_m']) or
        any(gap(p['polygon_m'],a,b)<r['width_m']/2 for r in data['roads'] if not r['id'].startswith('ACCESS_')
            for a,b in zip(r['polyline_m'],r['polyline_m'][1:])))]
    check('elite gardens inside district and clear of streets',not gardenhits,str(gardenhits))
    check('B02 and P04 distinct dead-end branches',next(f for f in fs if f.get('poi_id')=='B02')['access_road_id']=='HUT_BRANCH' and
        next(f for f in fs if f.get('poi_id')=='P04')['access_road_id']=='RECEPTION_BRANCH')
    check('six sparse farmsteads, two start clusters',len(data['farmsteads'])==6 and sum(f['start_cluster'] for f in data['farmsteads'])==2)
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
    data['hamlet_statistics']=dict(farmstead_count=6,building_count=counts['village'],start_cluster_count=2)
    data['residential_statistics']=dict(complex_count=3,slab_count=9,garage_box_count=18)
    data['functional_statistics']=dict(building_count=len(fs),district_counts=dict(Counter(f['district_id'] for f in fs)),type_counts=dict(types),
        promoted_existing_count=sum('source_building_id' in f for f in fs),new_footprint_count=sum('source_building_id' not in f for f in fs))
    data['passage_statistics']=dict(count=4,total_length_m=sum(p['length_m'] for p in data['paths']),policy='urban local only; no van access')
    data['metrics']=dict(area_m2=total,bounds_m=bounds,extent_m=extent,routes=routes,building_count=len(phys),
        building_counts_by_district=dict(counts),timing_assumption='constant speeds; no acceleration, traffic, turns or slopes; not measured gameplay')
    data['validation']=dict(passed=all(c['passed'] for c in checks),checks=checks)
    if not data['validation']['passed']:raise ValueError(json.dumps([c for c in checks if not c['passed']],ensure_ascii=False,indent=2))


def render(data):
    s=m.SVG();scale=1824/900
    def xy(p):return [70+(p[0]-80)*scale,210+(900-p[1])*scale]
    def line(poly,col,w=1,**extra):s.line([xy(p) for p in poly],col,w,**extra)
    def polygon(poly,col,stroke='none',w=1,**extra):s.poly([xy(p) for p in poly],col,stroke,w,**extra)
    s.rect(0,0,2400,2400,'#f6f3e9')
    s.text(70,80,data['title_ru'],size=44,weight='bold')
    s.text(70,124,'Лесная полоса → хутор → короткий переход → три двора → старый город → элитный холм',size=24,color='#718078')
    s.text(70,164,'815 × 685 м • 125 зданий • узкие дороги • один въезд между районами • решения 04.10.2026',size=20,color='#718078')
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
    headings=[([210,748],'ХУТОР','6 усадеб / 21 постройка'),([405,760],'ПЕРЕХОД','B02 и P04 — разные ветки'),
        ([645,813],'НЕБЛАГОПОЛУЧНЫЙ РАЙОН','3 двора × 3 корпуса / 9–12 этажей'),
        ([520,458],'СТАРЫЙ ГОРОД','Террасы 2–3 эт. / 2 высотки'),
        ([875,647],'ЭЛИТНЫЙ ХОЛМ','7 особняков / 2 доступны'),
        ([700,265],'ПРОМЫШЛЕННАЯ ОКРАИНА','B05 / депо P14 / эвакуатор P12'),
        ([222,455],'ЛЕСНАЯ ПОЛОСА','Только стартовая опушка')]
    for pos,title,sub in headings:
        x,y=xy(pos);anchor='start' if title in ('ЭЛИТНЫЙ ХОЛМ','ПРОМЫШЛЕННАЯ ОКРАИНА') else 'middle'
        s.text(x,y,title,size=22,weight='bold',anchor=anchor,halo=True)
        s.text(x,y+24,sub,size=15,anchor=anchor,color='#65776b',halo=True)
        width=max(len(title)*12,len(sub)*8)
        reserve(x+width/2 if anchor=='start' else x,y,width,46)
    for pos,title in [([390,532],'МАЛАЯ ДОЛИНА'),([454,506],'ОЗЕРО'),([741,434],'КАНАЛ'),([409,402],'СТАРАЯ ЖД')]:
        x,y=xy(pos);s.text(x,y,title,size=14,anchor='middle',color='#617f80',halo=True);reserve(x,y,len(title)*8,18)
    for i,block in enumerate(data['microdistricts'],1):
        x,y=xy([block['center_m'][0],740]);s.text(x,y,f'ДВОР {i}',size=14,weight='bold',anchor='middle',color='#566d6b')
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
    s.text(70,2350,'R01 / v06 • 04.10.2026 • геометрия — проектное предложение • все районы доступны с начала',size=16,color='#889384')
    s.text(2330,2350,'JSON → SVG → PNG',size=16,color='#889384',anchor='end')
    return s.finish()


def legend(data,s,scale):
    x=1955;y=250
    s.rect(1932,211,400,1888,'#efede2',rx=12)
    s.text(x,y,'КАК ЧИТАТЬ ПЛАН v06',size=20,weight='bold');y+=32
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
    rows=[('Хутор / старт','6 усадеб по 3 постройки;|дед P02, аптека P03, амбар,|сельмаг, остановка, водобашня.'),
        ('Неблагополучный район','3 двора × 3 корпуса 72 × 12 м;|18 боксов, B03, бар P06, притон P07;|3 киоска, 24 ч, котельная / труба.'),
        ('Старый город','5 террас × 6 домов по 7 м;|две высотки, P05, B04, больница P08,|полиция P10, банк / ATM, магазин;|2 кафе, церковь, отель, почта, маски;|площадь / часы; P09 + 2 запасные.'),
        ('Элитка / промзона','7 особняков, B06 и 2 доступных P15;|охрана, бутик / B05, P14, P12,|3 склада, труба, металлолом, сарай.')]
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
    metrics=data['metrics'];lengths={(r['from_id'],r['to_id']):r for r in metrics['routes']}
    lines=['# VOLUNTEERS ONLY — R01 v06','',
        'Основание: req_map_plan_v06.md, последние решения владельцев 04.10.2026; приоритет пунктов 6–9.',
        f'Размер всей игровой территории: **{metrics["extent_m"][0]:.0f} × {metrics["extent_m"][1]:.0f} м**, площадь {metrics["area_m2"]/1e6:.5f} км²; PNG/SVG 2400 × 2400.',
        f'Всего **{metrics["building_count"]} уникальных физических зданий/сооружений**; source_building_id исключает двойной счёт.',
        'Лес только полосой 240 × 80 м у вагона; озеро около 34 × 42 м, короткая река, два малых поля.',
        'Основная дуга: лес → хутор → переход → неблагополучный район → старый город → элитный холм.','',
        '| Район | Всего зданий | Состав |','|---|---:|---|']
    programme=dict(forest='Вагон B01; деревья только вокруг старта.',
        village='6 усадеб по 3 постройки; P02/P03 и амбар оформлены на существующих пятнах; сельмаг, остановка, башня.',
        transition='B02, P04 на отдельных тупиковых ветках; АЗС, руины фермы.',
        residential='Ровно 3 U-двора по 3 корпуса 72 × 12 м, 9–12 этажей; 18 гаражных боксов; B03, P06/P07, 3 киоска, 24 ч, котельная с трубой.',
        old_town='5 террас по 6 домов, фасад 7 м, 2–3 этажа; 2 высотки 14/16 этажей; 14 функций, включая два кафе и мастерскую P05 на стыке районов.',
        elite='7 особняков с садами, включая B06; 2 доступных P15; охрана, бутик; дорогие NPC и спецзаказы.',
        industrial='B05, P14, P12, труба, 3 склада, металлолом, сарай; депо и эвакуатор у конца старой ЖД.',fields='Небольшая долина; зданий нет.')
    for d in data['districts']:lines.append(f'| {d["name_ru"]} | {d["building_count"]} | {programme[d["id"]]} |')
    lines+=['','P09: основная встреча за супермаркетом, запасной сквер, запасное место у канала; площадки не считаются зданиями.',
        'Старый город включает банк с ATM, супермаркет, больницу P08, полицию P10, церковь, отель, почту, одежду/маски, B04 и площадь с часовой башней.',
        'Ширины: шоссе/проспект 7 м, улица 6 м, село 3,8 м, грунт 3,5 м, проход 2,5 м; не более двух полос.',
        'Между соседними районами ровно один основной въезд. Грунтовых срезок 0 (разрешено ≤ 1); петель за городским ядром нет.',
        'Сплошные тонкие ограды/скальные пояса и канал оставляют только дорожные разрывы; межрайонных пеших путей и пеших мостов нет.',
        'Четыре прохода внутри города: три выхода из дворов и один задний переулок; бусику недоступны.',
        'Три поста P16: видимые тупики после постов; возврат через тот же пост, фланги оставляют дорогу свободной.','',
        '| Маршрут | По дороге, м | 60 км/ч, с | 90 км/ч, с | Пешком 5 км/ч, мин |','|---|---:|---:|---:|---:|']
    for r in metrics['routes']:lines.append(f'| {r["from_id"]} → {r["to_id"]} | {r["length_m"]:.1f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["walk_5_minutes"]:.2f} |')
    lines+=['','Время теоретическое: постоянная скорость, без разгона, поворотов, трафика и уклонов; 60/90 км/ч — расчётные сценарии, не измеренная средняя скорость.',
        'Для B01/B02 → район пеший граф даёт ту же дистанцию: ходьба в 12/18 раз медленнее поездки при 60/90 км/ч.',
        f'Проверки: **{sum(c["passed"] for c in data["validation"]["checks"])}/{len(data["validation"]["checks"])}**; все перечислены в validation JSON.',
        'Пороговые проверки: старт ≤ 200 м; B01 → район ≥ 400 м; район → площадь ≤ 200 м; площадь → ворота ≤ 200 м; обе стороны ≤ 1000 м.',
        'Проверены графы, единственные соединители, отсутствие внешних петель/срезок, уникальные ID, здания без наложений и пересечений с дорогами/водой/ЖД.',
        'Схема v05 сохранена; размеры корпусов/домов не уменьшались; предыдущие файлы v02–v05 сохранены побайтно (SHA-256 в provenance).',
        'Неизменённый Greybox/flatten_plan.py проверен в памяти: 125 зданий, 41 точка, 101 дорога/проход; новый greybox-файл не создавался.',
        'Сплошные ограды в vegetation_parcels и фигурные барьеры тупиков требуют полигональных коллайдеров в Unity; rough-конвертер пропускает ограды и упрощает тупики до AABB.',
        'Сборка: `python -B map_plan_v06.py`; `--reset-data` восстанавливает авторский v06. Старые сборщики не изменены.',
        'PNG просмотрен после сборки. Ощущение размера, видимость трубы, столкновения оград, уклоны и выгода бусика требуют нового Unity-плейтеста.']
    assert len(lines)<=60,len(lines)
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
