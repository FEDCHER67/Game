#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Organic R01 v12; corrected brief of 2026-10-04, including 14a and 15.
Read final v11; write only five v12 deliverables here. Run with Python -B.
"""
import copy
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
sys.dont_write_bytecode = True
import map_plan_v11 as v11
m, v7 = v11.m, v11.v7
ROOT = m.ROOT
STEM = 'MAP_PLAN_R01_v12'
OUTPUTS = {STEM+s for s in ('.json','.svg','.png','_REPORT.md')} | {'map_plan_v12.py'}
WIDTHS = dict(highway=7,town_street=6,rural_road=3.8,dirt_shortcut=3.5,passage=2.5)
REMOVED_FUNCTIONS = {'F06_HOTEL','F06_POST','F06_MASKS','F06_CAFE1','F06_WARE2','F06_SCRAP'}
REMOVED_HOUSES = {'O06_T3_U4','O06_T3_U6','O06_T5_U4','O06_T5_U5',
                  'O06_T2_U1','O06_T2_U3','O06_T2_U4','O06_T2_U5'}
HOUSE_LAYOUT = {
    'O06_T1_U1':('old_town',[500,553],-66),
    'O06_T1_U2':('transition',[360,659],12),
    'O06_T1_U3':('transition',[360,628],-23),
    'O06_T1_U4':('old_town',[553,563],21),
    'O06_T1_U5':('old_town',[690,466],13),
    'O06_T1_U6':('old_town',[577,519],-32),
    'O06_T2_U2':('old_town',[620,603],-14),
    'O06_T2_U6':('old_town',[730,456],-9),
    'O06_T3_U1':('old_town',[539,513],43),
    'O06_T3_U2':('old_town',[776,560],-18),
    'O06_T3_U3':('old_town',[542,492],-47),
    'O06_T3_U5':('old_town',[778,460],16),
    'O06_T5_U1':('village',[324,727],18),
    'O06_T5_U2':('transition',[371,751],-31),
    'O06_T5_U3':('transition',[446,760],17),
    'O06_T5_U6':('old_town',[613,464],-7),
}


def hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(ROOT.iterdir()) if p.is_file() and p.name not in OUTPUTS}


def source_data():
    return json.loads((ROOT/'MAP_PLAN_R01_v11.json').read_text(encoding='utf-8'))


def curve(controls,steps=6):
    result=m.smooth(controls,steps=steps)
    # Preserve fractional driveway junctions exactly, before graph intersection.
    for i,p in enumerate(controls):result[i*steps]=list(p)
    return result


def rounded(controls,steps=6):
    n=len(controls)
    return curve([controls[-1]]+controls+controls[:2],steps)[steps:(n+1)*steps]


def oval(center,radii,phase=0,count=48):
    cx,cy=center;rx,ry=radii
    result=[]
    for i in range(count):
        a=i*2*math.pi/count
        f=1+.055*math.sin(3*a+phase)+.035*math.cos(2*a+.6+phase)
        result.append([round(cx+rx*math.cos(a)*f,3),round(cy+ry*math.sin(a)*f,3)])
    return result


def offset(points,distance):
    lines=[]
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];n=math.hypot(dx,dy)
        lines.append(([a[0]+distance*dy/n,a[1]-distance*dx/n],[dx,dy]))
    result=[lines[0][0]]
    for (a,u),(b,v) in zip(lines,lines[1:]):
        den=u[0]*v[1]-u[1]*v[0]
        t=1 if abs(den)<1e-9 else ((b[0]-a[0])*v[1]-(b[1]-a[1])*v[0])/den
        result.append([a[k]+t*u[k] for k in (0,1)])
    a,u=lines[-1];result.append([a[k]+u[k] for k in (0,1)])
    return [[round(z,3) for z in p] for p in result]


def nearest(p,line):
    return min((m.projection(p,a,b) for a,b in zip(line,line[1:])),key=lambda q:q[0])


def transform(q,center,angle=None):
    old=q['center_m'];dx,dy=center[0]-old[0],center[1]-old[1]
    for key in ('footprint_m','polygon_m','main_house_footprint_m','garage_footprint_m'):
        if key in q:q[key]=[[round(x+dx,3),round(y+dy,3)] for x,y in q[key]]
    q['center_m']=center[:]
    if angle is not None:
        key='footprint_m' if 'footprint_m' in q else 'polygon_m'
        q[key]=m.rectangle(*center,q['width_m'],q['depth_m'],angle)
        q['rotation_deg']=angle


def seed():
    d=source_data();original=copy.deepcopy(d)
    d.update(revision='v12',title_ru='VOLUNTEERS ONLY — план карты R01 / v12')
    d['specification']['brief_override']='req_map_plan_v12.md; corrected 14a and 15; 2026-10-04'
    d['provenance']=dict(brief='req_map_plan_v12.md',source_schema='MAP_PLAN_R01_v11.json',
        owner_decisions_date='2026-10-04',method='organic geometry rebuilt from final v11 inventory',
        previous_files_sha256=hashes(),brief_corrections=['14a: valley beach access','15: maintenance shed retained'])
    d['comparison']=dict(v11={'extent_m':original['metrics']['extent_m'],
        'building_count':original['metrics']['building_count'],
        'old_town_building_count':original['metrics']['building_counts_by_district']['old_town']},
        policy='same approved courtyard and villa footprints; rebuilt organic surroundings')
    d['geometry_repairs'],d['land_transfers']=[],[]
    d['functional_buildings']=[f for f in d['functional_buildings'] if f['id'] not in REMOVED_FUNCTIONS]
    d['building_masses']=[b for b in d['building_masses'] if b['id'] not in REMOVED_HOUSES]
    ds={q['id']:q for q in d['districts']}
    outlines={
        'forest':[[110,476],[153,458],[260,467],[324,493],[333,529],[305,545],[231,544],[176,543],[124,535],[104,509]],
        'village':[[118,568],[184,556],[269,555],[323,556],[344,578],[340,620],[340,654],[334,691],[349,737],[311,752],[243,732],[213,747],[186,781],[128,780],[120,753],[148,702],[184,682],[177,613]],
        'transition':[[357,552],[397,551],[445,553],[464,578],[467,621],[467,671],[469,707],[464,737],[466,773],[429,784],[378,779],[358,752],[348,699],[353,659],[349,615]],
        'residential':[[477,648],[511,627],[546,622],[592,621],[638,624],[693,625],[749,630],[774,651],[781,711],[779,770],[779,824],[758,863],[709,889],[640,895],[571,892],[514,877],[478,848],[470,798],[474,746],[474,701]],
        'old_town':[[485,477],[509,450],[563,448],[613,446],[670,448],[737,444],[784,452],[799,490],[797,545],[797,580],[779,610],[728,617],[679,619],[632,618],[593,617],[554,615],[511,612],[477,601],[481,552],[480,514]],
        'elite':[[806,468],[843,443],[889,443],[946,468],[978,509],[986,567],[970,620],[941,669],[875,690],[829,659],[805,608],[804,558]],
        'industrial':[[519,360],[542,342],[597,335],[650,334],[710,339],[763,340],[798,354],[803,382],[808,417],[788,433],[736,433],[676,430],[618,432],[568,433],[528,430],[510,412],[510,387]],
        'fields':[[353,339],[389,318],[439,311],[478,323],[499,353],[499,394],[485,437],[472,464],[465,497],[459,535],[431,544],[399,544],[361,540],[343,525],[340,474],[343,430],[335,385]],
    }
    for did,controls in outlines.items():
        ds[did].update(polygon_m=rounded(controls),notes_ru='Плавный асимметричный контур; свободные озеленённые промежутки между кварталами.')
    # Additional sampling resolves the tighter grown-village bend without a corner.
    ds['village']['polygon_m']=rounded(outlines['village'],16)
    d['coordinates']['district_outline_policy']='organic neighbourhood envelopes; intervening common landscape, roads and water are not extra districts'
    inner=curve([[330,320],[405,299],[482,304],[538,316],[620,309],[695,301],[771,315],
        [823,337],[859,371],[895,408],[934,445],[972,490],[1004,551],[995,610],[965,664],[940,700]],7)
    coast=offset(inner,55)
    outer_sea=curve([[150,75],[370,40],[655,60],[910,105],[1130,240],[1220,440],[1210,670],[1155,850]],10)
    loop=[coast[-2],coast[-1],[930,752],[847,728],[803,713],[803,819],[784,880],
        [720,911],[609,910],[521,892],[481,868],[455,821],[430,796],[354,791],[309,775],
        [242,765],[185,804],[118,806],[89,772],[103,716],[136,676],[118,609],[95,550],
        [92,487],[107,449],[170,432],[260,443],[314,461],[325,433],[316,375],[307,318],
        [294,296],[coast[0][k]-2*(coast[1][k]-coast[0][k]) for k in (0,1)],coast[0],coast[1]]
    inland=curve(loop,12)[12:-12]
    d['boundary'].update(polygon_m=coast+inland[1:-1],
        coast_segments_m=[[a,b] for a,b in zip(coast,coast[1:])],
        barrier='closed rock scarp and fence on non-coast boundary; no wall on coast_segments_m; SEA returns to last ground point')
    d['beaches']=[dict(id='BEACH',name_ru='Пляж',polygon_m=inner+list(reversed(coast)),
        land_edge_m=inner,sea_edge_m=coast,width_m=55,surface='sand',
        access_road_ids=['BEACH_ACCESS','BEACH_VALLEY_ACCESS'],
        closed_ends_ru='Концы закрыты скалами. Два входа: элитный холм и Малая долина.')]
    waters={w['id']:w for w in d['water']};lake=waters['LAKE']
    oldcenter=[sum(p[k] for p in lake['polygon_m'])/len(lake['polygon_m']) for k in (0,1)]
    controls=[[x+435-oldcenter[0],y+575-oldcenter[1]] for x,y in lake['polygon_m']]
    lake.update(polygon_m=rounded(controls,8),center_m=[435,575],district_id='transition')
    waters['RIVER_N']['centerline_m']=curve([[450,619],[446,608],[439,596]])
    waters['RIVER_S']['centerline_m']=curve([[430,555],[438,548],[454,535],[460,511],[465,478],[480,452],[510,440]])
    waters['CANAL'].update(centerline_m=curve([[510,440],[565,437],[619,442],[670,438],[728,441],[780,438],[815,442]]),
        banks='steep concrete; 1.1m railings; I_CONNECT bridge; sealed outlet below terrain and beach',short_tunnel_road_ids=[])
    waters['SEA'].update(polygon_m=coast+list(reversed(outer_sea)),offshore_band_m=150)
    d['railway']['polyline_m']=curve([[202,496],[275,486],[324,469],[377,433],[420,408],
        [481,400],[505,391],[525,366],[561,359],[663,356],[728,361],[775,360]],7)
    d['hills']=[dict(id='HILL_ELITE',center_m=[899,566],radii_m=[99,115],height_target_m=24)]
    d['field_parcels_m']=[oval([371,467],[19,24],.6),oval([460,413],[26,22],1.7)]
    fs={f['id']:f for f in d['functional_buildings']};bs={b['id']:b for b in d['building_masses']};pts={p['id']:p for p in d['points']}
    d['plots']=[p for p in d['plots'] if not p['id'].startswith('O06_') and p['kind']!='elite_garden' and p['id']!='VILLA07_YARD']
    for bid,(did,center,angle) in HOUSE_LAYOUT.items():
        b=bs[bid];transform(b,center,angle)
        b.update(district_id=did,kind='small_house',detached=True,layout_policy='separate irregular house; terrace row removed')
        b.pop('terrace_id',None)
        d['plots'].append(dict(id=bid+'_FRONT',kind='front_yard',district_id=did,
            polygon_m=oval([center[0],center[1]-10],[5,3],angle/20)))
    for farm in d['farmsteads']:
        q=next(p for p in d['plots'] if p['id']==farm['id']);c=farm['center_m']
        dims=[24,23] if farm['id']=='FARM06_1' else [23,17]
        q['polygon_m']=farm['yard_polygon_m']=oval([c[0]+6,c[1]+7],dims,.3)

    def place(fid,center,door,parent,angle=None,did=None):
        f=fs[fid];transform(f,center,angle);f.update(entrance_m=door[:],access_road_id=parent)
        if did:f['district_id']=did
        if f.get('poi_id'):pts[f['poi_id']].update(position_m=door[:],district_id=f['district_id'])

    place('F06_CHURCH',[383,573],[398,574],'TRANSITION_DIRECT',did='transition')
    fs['F06_CHURCH']['footprint_m']=m.rectangle(383,573,12,30,-9)
    place('F06_POLICE',[773,583],[754,583],'O_LANES')
    place('F06_SUPER',[582,603],[582,589],'O_LANES')
    fs['F06_CAFE2'].update(purchasable=True,label_ru='Кафе у проспекта — можно купить')
    mansions=[([847,627],[847,614],9,[28,24]),([926,639],[923,625],-13,[30,27]),
        ([944,556],[924,550],24,[27,31]),([868,484],[870,499],-8,[33,25])]
    for i,(center,door,angle,radii) in enumerate(mansions,1):
        fid='F08_MANSION_1' if i==1 else 'F06_MANSION_'+str(i)
        place(fid,center,door,'ELITE_LANE' if i<=2 else 'ELITE_SOUTH',angle)
        d['plots'].append(dict(id='GARDEN06_'+str(i),kind='elite_garden',district_id='elite',
            polygon_m=oval(center,radii,i),building_id=fid,accessible=fs[fid].get('accessible',False)))
    fs['F07_VILLA'].update(lake_facing_direction='north',label_ru='Вилла у озера',access_road_id='VALLEY_BRANCH')
    terrace=oval([422,542],[12,4],.4)
    d['plots'].append(dict(id='VILLA07_YARD',kind='villa_yard',district_id='fields',polygon_m=terrace))
    venues=[('F12_CASINO','casino','Казино',[433,366],36,24,-13,[435,387],3),
        ('F12_NIGHTCLUB','nightclub','Ночной клуб',[376,378],26,18,12,[396,383],2),
        ('F12_BOWLING','bowling_arcade','Боулинг / аркада',[474,350],32,20,17,[470,370],2)]
    for fid,typ,label,center,w,h,angle,door,floors in venues:
        f=dict(id=fid,type=typ,label_ru=label,district_id='fields',center_m=center,width_m=w,depth_m=h,
            footprint_m=m.rectangle(*center,w,h,angle),rotation_deg=angle,storeys=floors,
            entrance_m=door,access_road_id='VALLEY_BRANCH',accessible=True)
        d['functional_buildings'].append(f);fs[fid]=f
    pts['P09'].update(position_m=[611,609],name_ru='Встреча за супермаркетом')
    pts['P13'].update(position_m=[457,581],district_id='transition')
    pts['P13-2']['position_m']=[454,488];pts['P13-5']['position_m']=[529,480]
    pts['BEACH_ENTRY']['position_m']=[1028,517]
    p=dict(id='BEACH_VALLEY_ENTRY',canonical_id='BEACH_VALLEY_ENTRY',name_ru='Пляж из долины / парковка',
        position_m=[420,281],district_id='beach',category='poi',label_offset_px=[0,0])
    d['points'].append(p);pts[p['id']]=p
    d['functional_sites']=[s for s in d['functional_sites'] if s['id'] not in
        {'F06_SCRAP_YARD','CANAL_BEACH_CULVERT','BEACH_TURNAROUND','VILLA07_TERRACE'}]
    sites={s['id']:s for s in d['functional_sites']}
    for pid in ('P09','P09-2','P09-3','P09-4'):sites['SITE_'+pid]['position_m']=pts[pid]['position_m'][:]
    sites['B05_YARD']['polygon_m']=oval([589,414],[35,21],.5)
    sites['F06_TOW_YARD']['polygon_m']=oval([702,418],[19,14],1)
    d['functional_sites'] += [
        dict(id='VILLA07_TERRACE',type='lake_terrace',district_id='fields',building_id='F07_VILLA',
            polygon_m=terrace,label_ru='Терраса на север, к озеру'),
        dict(id='CHURCH12_YARD',type='churchyard',district_id='transition',building_id='F06_CHURCH',
            polygon_m=oval([383,574],[23,23],.5),label_ru='Небольшой церковный двор'),
        dict(id='CASINO12_PARKING',type='parking',district_id='fields',building_id='F12_CASINO',
            polygon_m=oval([446,392],[26,9],.3),capacity_vans=8,label_ru='Парковка казино'),
        dict(id='CANAL_BEACH_CULVERT',type='culvert',district_id='industrial',
            polyline_m=curve([[815,442],[850,410],[870,360]]),width_m=4,
            tunnel_carrier='water_below_terrain_and_sand',blocks_foot_bypass=True,label_ru='Закрытый выпуск канала'),
        dict(id='BEACH_TURNAROUND',type='turnaround',district_id='beach',
            polygon_m=oval([1028,517],[8,6],.3),label_ru='Пляж: разворот из элитки'),
        dict(id='BEACH_VALLEY_TURNAROUND',type='turnaround',district_id='beach',
            polygon_m=oval([420,281],[9,6],1),label_ru='Пляж: парковка из долины'),
    ]
    d['replaced_generic_building_ids']=[]
    d['distribution_targets']={'policy':'v12 organic decluttering; no terrace row quota'}
    d['planning_notes_ru']=[
        'Округлые асимметричные районы, свободные озеленённые полосы и плавные улицы вместо сетки.',
        'Из старого города убраны четыре функции и восемь малых домов; пять домов перенесены в хутор и переход.',
        'Кафе у проспекта — единственное кафе, доступно для покупки (purchasable=true).',
        'Прямой путь через переход и новый разрыв бетона ведёт в западную часть старого города.',
        'Озеро и P13 перенесены к (435;575); церковь с небольшим двором — к новой улице перехода.',
        'B06 сохранён в (414;530), выше ЖД; терраса обращена на север к озеру.',
        'Казино, клуб и боулинг ниже ЖД; VALLEY_BRANCH имеет ровно один переезд.',
        'Пляж 55 м: два въезда с разворотами, из элитки и из долины; промзона закрыта оградой.',
        'Промзона: B05, труба, P12, депо P14, Склад 1 и Ремонтный сарай; Склад 2 и металлолом убраны.',
        'Море на 150 м за берегом; короткие coast_segments_m не получают стену.',
        'Корпуса трёх дворов и проспект y=723,5 сохранены, отступы 10 м; притон между дворами 1–2.',
    ]
    build_roads(d,original);build_fences(d)
    return d


def building_door(building,target,width):
    center=building['center_m'];poly=building.get('footprint_m',building.get('polygon_m'))
    dx,dy=target[0]-center[0],target[1]-center[1];n=math.hypot(dx,dy)
    far=[center[0]+dx/n*200,center[1]+dy/n*200]
    hits=[m.crossing(center,far,a,b) for a,b in v7.edges(poly)]
    hit=min((h[0] for h in hits if h),key=lambda p:m.length(center,p))
    return [round(hit[0]+dx/n*(width/2+1),3),round(hit[1]+dy/n*(width/2+1),3)]


def build_roads(d,original):
    roads={};d['roads']=[];d['paths']=[]
    pts={p['id']:p for p in d['points']}
    fs={f['id']:f for f in d['functional_buildings']}
    oldroads={r['id']:r for r in original['roads']}
    def add(rid,controls,cls,dids,curved=True,**kw):
        q=dict(id=rid,**{'class':cls},width_m=WIDTHS[cls],district_ids=dids,
            polyline_m=curve(controls) if curved and len(controls)>2 else controls,
            lanes=1 if cls=='rural_road' else 2,**kw)
        d['roads'].append(q);roads[rid]=q
        return q
    add('START_ROAD',[[190,510],[207,507],[228,522],[230,558],[234,577]],'rural_road',['forest','village'])
    add('V_MAIN',[[234,577],[267.377,590.679],[300,600],[330,602],[350,600]],'rural_road',['village'])
    add('V_NORTH',[[300,600],[293,621],[299,651],[300,687],[289,706]],'rural_road',['village'])
    add('V_WEST_BRANCH',[[289,706],[253,704],[230,700]],'rural_road',['village'])
    add('ARC_RURAL',[[350,600],[368,592],[394,600],[411,631],[414,668],[405,700],
        [405,723.5],[432,725],[451,723.5],[470,723.5]],'rural_road',['village','transition'])
    add('HUT_BRANCH',[[405,723.5],[406,727],[405,730]],'rural_road',['transition'])
    start=nearest([440,724],roads['ARC_RURAL']['polyline_m'])[1]
    add('RECEPTION_BRANCH',[start,[438,709],[440,691]],'rural_road',['transition'])
    add('ARC_AVENUE',[[470,723.5],[770,723.5]],'highway',['residential'],False,
        approved_straight_exception='v11 courts 1–2 north / 3 south, 10m slab setbacks')
    add('R_COURTS',[[515,723.5],[514,703],[519,680],[515,676]],'rural_road',['residential'])
    for rid in ('COURT_ACCESS_1','COURT_ACCESS_2','COURT_ACCESS_3'):
        old=oldroads[rid]
        add(rid,copy.deepcopy(old['polyline_m']),old['class'],['residential'],False,
            approved_straight_exception='approved U-court composition')
    add('R_REAR',[[710,723.5],[716,748],[715,788],[710,832],[670,840],[631,836],
        [592.5,832],[556,834],[535,832]],'rural_road',['residential'])
    add('EXIT_APPROACH_NE',[[710,832],[710,842]],'rural_road',['residential'],False)
    for rid in ('EXIT_NW','EXIT_NE'):
        old=oldroads[rid]
        # The final post/dead-end alignment preserves its mandatory-return flanks.
        add(rid,copy.deepcopy(old['polyline_m']),old['class'],old['district_ids'],False)
    add('TRANSITION_DIRECT',[[394,600],[414,615],[450,611],[477,602],[514,602],
        [545,584],[582,584],[610,587],[634,572],[650,540]],'town_street',['transition','old_town'],
        approved_extra_interdistrict_link=True)
    add('OLD_TOWN_CONNECTOR',[[650,723.5],[653,700],[652,666],[654,624],[655,582],[650,540]],
        'highway',['residential','old_town'])
    add('O_LANES',[[535,588],[559,583],[582,584],[610,587],[634,582],[670,578],[700,585],
        [740,591],[754,575],[752,541],[751,515],[739,485],[712,484],[669,490],
        [628,485],[586,473],[553,468],[529,480],[520,510],[517,543],[516,565],[535,588]],
        'town_street',['old_town'])
    add('O_SPINE',[[650,540],[640,516],[649,490],[650,463]],'town_street',['old_town'])
    add('OLD_ELITE_CONNECTOR',[[650,540],[699,534],[747,538],[781,542],[800,540]],
        'town_street',['old_town','elite'])
    add('I_CONNECT',[[650,463],[650,440],[642,416],[650,392]],'town_street',['old_town','industrial'])
    add('I_YARD',[[531,392],[576,393],[627,388],[650,392],[670,394],[715,393],[748,399],[775,392]],
        'town_street',['industrial'])
    add('ELITE_GATE_ROAD',[[800,540],[829,537],[859,551]],'town_street',['elite'])
    add('ELITE_LANE',[[859,551],[877,571],[887,600],[893,626]],'town_street',['elite'])
    add('ELITE_SOUTH',[[859,551],[849,532],[861,518],[892,521],[915,527]],'town_street',['elite'])
    add('BEACH_ACCESS',[[892,521],[927,507],[962,505],[1010,514],[1028,517]],
        'town_street',['elite','beach'])
    add('VALLEY_BRANCH',[[368,592],[366,569],[372,542],[379,513],[381,484],[379,453],
        [382,420],[391,399],[405,389],[433,390],[460,386],[481,380]],'rural_road',['transition','fields'])
    add('BEACH_VALLEY_ACCESS',[[405,389],[405,364],[411,339],[422,314],[420,281]],
        'town_street',['fields','beach'])
    def access(rid,door,parent,did,cls='rural_road',controls=None):
        start=nearest(door,roads[parent]['polyline_m'])[1]
        return add(rid,controls or [start,door],cls,[did],access_only=True,parent_road_id=parent)
    # Keep existing endpoint clearances; adapt each start to its curved parent.
    parent_override={'F06_CHURCH':'TRANSITION_DIRECT','F06_HBASE':'O_LANES',
        'F06_REPAIR':'O_LANES','F06_POLICE':'O_LANES','F06_BANK':'O_LANES',
        'F06_SUPER':'O_LANES','F06_CAFE2':'O_LANES','F07_VILLA':'VALLEY_BRANCH',
        'F06_GAS':'ARC_RURAL','F06_RUINS':'ARC_RURAL','F06_BAR':'OLD_TOWN_CONNECTOR',
        'F06_DEN':'R_REAR','F06_K3':'R_REAR','F06_HOSPITAL':'R_REAR','F06_ATM':'R_REAR',
        'F06_GBASE':'R_COURTS','F06_K1':'R_COURTS','F06_K2':'R_COURTS',
        'F06_24':'ARC_AVENUE','F06_WAGON':'START_ROAD','F06_VSHOP':'V_MAIN',
        'F06_BUS':'V_NORTH','F06_WATER':'V_NORTH','F06_BARN':'V_MAIN',
        'F06_GRANDPA':'V_MAIN','F06_PHARM':'V_MAIN','F07_AD_POLE':'START_ROAD',
        'F06_GUARD':'ELITE_GATE_ROAD'}
    for f in d['functional_buildings']:
        fid=f['id'];parent=parent_override.get(fid,f.get('access_road_id','I_YARD'))
        if fid in {'F06_COMPLEX','F06_TOW','F06_DEPOT','F06_CHIMNEY','F06_WARE1','F06_MAINT'}:parent='I_YARD'
        if parent=='O_RING':parent='O_LANES'
        f['access_road_id']=parent
        rid='ACCESS_'+(f.get('poi_id') or fid)
        if fid=='F07_AD_POLE':continue
        cls=oldroads.get(rid,{}).get('class','town_street' if fid.startswith('F12_') else 'rural_road')
        if fid=='F06_BARN':
            start=nearest([267.377,590.679],roads['V_MAIN']['polyline_m'])[1]
            controls=[start,[241,601],f['entrance_m']]
        elif fid=='F06_CHURCH':
            controls=[[394,600],[403,588],f['entrance_m']]
        elif fid=='F06_MANSION_4':
            start=nearest([873,518],roads[parent]['polyline_m'])[1]
            controls=[start,[873,508],f['entrance_m']]
        elif fid=='F06_BANK':
            controls=[[751,515],[739,512],f['entrance_m']]
        else:controls=None
        access(rid,f['entrance_m'],parent,f['district_id'],cls,controls)
    # Generic houses have their own front doors, instead of row/terrace metadata.
    promoted={f.get('source_building_id') for f in d['functional_buildings']}
    parents_by_did={'old_town':['O_LANES','O_SPINE'],'transition':['ARC_RURAL','TRANSITION_DIRECT'],
        'village':['V_MAIN','V_NORTH','V_WEST_BRANCH'],'residential':['R_COURTS']}
    for b in d['building_masses']:
        if b['id'] in promoted or b['kind']=='slab':continue
        choices=parents_by_did[b['district_id']]
        parent=min(choices,key=lambda rid:nearest(b['center_m'],roads[rid]['polyline_m'])[0])
        target=nearest(b['center_m'],roads[parent]['polyline_m'])[1]
        door=building_door(b,target,3.8)
        b['entrance_m']=door
        controls=None
        if b['id']=='F06_3_2':
            door=[331,635.6];start=nearest([294,626],roads['V_NORTH']['polyline_m'])[1]
            controls=[start,[315,626],door];parent='V_NORTH'
        elif b['id']=='F06_4_1':
            door=[270,677.9];parent='V_WEST_BRANCH'
        elif b['id']=='O06_T5_U2':
            door=building_door(b,[393,758],3.8)
            controls=[[432,725],[420,744],[393,758],door];parent='ARC_RURAL'
        b['entrance_m']=door
        access('ACCESS_'+b['id'],door,parent,b['district_id'],controls=controls)
    def poi(pid,parent,controls=None):
        access('ACCESS_'+pid,pts[pid]['position_m'],parent,pts[pid]['district_id'],controls=controls)
    for pid,parent in [('P09','O_LANES'),('P09-2','R_REAR'),('P09-3','I_CONNECT'),
        ('P09-4','ARC_RURAL'),('P11-2','ARC_AVENUE'),('P13-3','O_SPINE'),('P13-4','COURT_ACCESS_3')]:poi(pid,parent)
    poi('P13','TRANSITION_DIRECT',[[450,611],[460,596],[457,581]])
    start=nearest([381,484],roads['VALLEY_BRANCH']['polyline_m'])[1]
    poi('P13-2','VALLEY_BRANCH',[start,[419,486],[454,488]])
    # Reference points and P13-5 coincide with authored junctions.
    d['water'][1]['short_tunnel_road_ids']=['TRANSITION_DIRECT']
    for r in d['roads']:r['length_m']=round(sum(m.length(a,b) for a,b in zip(r['polyline_m'],r['polyline_m'][1:])),3)
    mid=offset(d['beaches'][0]['land_edge_m'],27.5)
    a=min(range(len(mid)),key=lambda i:m.length(mid[i],pts['BEACH_VALLEY_ENTRY']['position_m']))
    b=min(range(len(mid)),key=lambda i:m.length(mid[i],pts['BEACH_ENTRY']['position_m']))
    path=[pts['BEACH_VALLEY_ENTRY']['position_m']]+mid[a:b+1]+[pts['BEACH_ENTRY']['position_m']]
    d['paths']=[dict(id='WALK_BEACH',**{'class':'passage'},width_m=2.5,polyline_m=path,
        district_id='beach',district_ids=['beach'],walkable=True,van_access=False,
        length_m=round(sum(m.length(x,y) for x,y in zip(path,path[1:])),3))]


def sample_line(line,spacing=2):
    out=[line[0]]
    for a,b in zip(line,line[1:]):
        n=max(1,math.ceil(m.length(a,b)/spacing))
        out += [[a[k]+(b[k]-a[k])*i/n for k in (0,1)] for i in range(1,n+1)]
    return out


def build_fences(d):
    roads={r['id']:r for r in d['roads']}
    d['vegetation_parcels']=[q for q in d['vegetation_parcels'] if q['kind']=='orchard']
    for q in d['vegetation_parcels']:
        p=q['polygon_m'];c=[sum(x[k] for x in p)/len(p) for k in (0,1)]
        q['polygon_m']=oval(c,[5,5],.8)
    def fence(fid,line,material,did,gates=(),group=None):
        dense=sample_line(line,1.5);runs=[];run=[]
        def clear(p):
            return any(nearest(p,roads[rid]['polyline_m'])[0] < roads[rid]['width_m']/2+1.4 for rid in gates)
        for a,b in zip(dense,dense[1:]):
            mid=[(a[k]+b[k])/2 for k in (0,1)]
            if clear(mid):
                if len(run)>1:runs.append(run)
                run=[]
            else:
                if not run:run=[a]
                run.append(b)
        if len(run)>1:runs.append(run)
        for i,axis in enumerate(runs,1):
            q=dict(id=f'{fid}_{i}',kind='interdistrict_barrier',district_id=did,
                polygon_m=offset(axis,.5)+list(reversed(offset(axis,-.5))),axis_m=axis,
                blocks_foot=True,blocks_van=True,material=material,
                height_target_m={'concrete_fence':2.5,'wooden_fence':1.6,'elite_fence':2.4,'canal_railing':1.1,'rock_scarp':2.4}[material],
                tree_line=material=='wooden_fence',continuity_group=group or fid,
                gate_road_ids=list(gates))
            d['vegetation_parcels'].append(q)
    fence('FOREST_VILLAGE',curve([[110,550],[185,548],[230,550],[281,553],[343,550]]),
        'wooden_fence','forest',['START_ROAD'])
    fence('RURAL_TRANSITION',curve([[336,333],[342,449],[343,546],[347,600],[344,696],[351,769]]),
        'wooden_fence','transition',['ARC_RURAL','V_MAIN'])
    fence('TRANSITION_URBAN',curve([[470,440],[474,492],[469,539],[470,581],[469,645],
        [471,694],[470,723.5],[468,785],[477,849],[496,879]]),'concrete_fence','transition',
        ['TRANSITION_DIRECT','ARC_AVENUE'])
    fence('VALLEY_NORTH',curve([[339,543],[369,550],[425,548],[467,540]]),'wooden_fence','fields',['VALLEY_BRANCH'])
    elite=next(q['polygon_m'] for q in d['districts'] if q['id']=='elite')
    fence('ELITE_PERIMETER',elite+[elite[0]],'elite_fence','elite',
        ['ELITE_GATE_ROAD','OLD_ELITE_CONNECTOR','BEACH_ACCESS'])
    inner=d['beaches'][0]['land_edge_m']
    west=[p for p in inner if p[0]<=510]
    industrial=[p for p in inner if 510<p[0]<826]
    east=[p for p in inner if p[0]>=826]
    # Shared endpoints avoid gaps at material changes.
    industrial=[west[-1]]+industrial+[east[0]]
    fence('VALLEY_BEACH_FENCE',west,'wooden_fence','fields',['BEACH_VALLEY_ACCESS'],'BEACH_ACCESS_CONTROL')
    fence('INDUSTRIAL_BEACH_FENCE',industrial,'concrete_fence','industrial',(), 'BEACH_ACCESS_CONTROL')
    fence('ELITE_BEACH_FENCE',east,'elite_fence','elite',['BEACH_ACCESS'],'BEACH_ACCESS_CONTROL')
    coast=d['beaches'][0]['sea_edge_m']
    fence('BEACH_WEST_ROCKS',[inner[0],coast[0]],'rock_scarp','fields',(), 'BEACH_ACCESS_CONTROL')
    fence('BEACH_EAST_ROCKS',[inner[-1],coast[-1]],'rock_scarp','elite',(), 'BEACH_ACCESS_CONTROL')
    canal=next(w for w in d['water'] if w['id']=='CANAL')['centerline_m']
    for side,dist,did in [('N',-4,'old_town'),('S',4,'industrial')]:
        fence('CANAL_RAILING_'+side,offset(canal,dist),'canal_railing',did,['I_CONNECT'],'CANAL_BANKS')


def on_edge(p,poly):
    return min(m.projection(p,a,b)[0] for a,b in v7.edges(poly)) < .015


def contained(p,poly):
    return m.inside(p,poly) or on_edge(p,poly)


def strict_overlap(a,b):
    if any(max(p[k] for p in a)<=min(p[k] for p in b)+.001 or
        max(p[k] for p in b)<=min(p[k] for p in a)+.001 for k in (0,1)):return False
    if any(m.inside(p,b) and not on_edge(p,b) for p in a):return True
    if any(m.inside(p,a) and not on_edge(p,a) for p in b):return True
    return any(h and .000001<h[1]<.999999 and .000001<h[2]<.999999
        for x,y in v7.edges(a) for u,v in v7.edges(b) if (h:=m.crossing(x,y,u,v)))


def simple(poly):
    edges=list(v7.edges(poly))
    if any(m.length(a,b)<.001 for a,b in edges):return False
    for i,(a,b) in enumerate(edges):
        for j,(c,e) in enumerate(edges[i+1:],i+1):
            if j==i+1 or (i==0 and j==len(edges)-1):continue
            if m.crossing(a,b,c,e):return False
    return True


def turn_max(poly):
    turns=[]
    for i,b in enumerate(poly):
        a,c=poly[i-1],poly[(i+1)%len(poly)]
        u=[b[k]-a[k] for k in (0,1)];v=[c[k]-b[k] for k in (0,1)]
        turns.append(math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(u,v))/(m.length(a,b)*m.length(b,c)))))))
    return max(turns)


def analyse(d,strict=True):
    m.build_graph(d);checks=[]
    def check(name,ok,detail=''):checks.append(dict(name=name,passed=bool(ok),detail=detail))
    original=source_data();ds={q['id']:q for q in d['districts']}
    pts={p['id']:p for p in d['points']};fs={f['id']:f for f in d['functional_buildings']}
    roads={r['id']:r for r in d['roads']};phys=v7.physical(d)
    bp=d['boundary']['polygon_m'];beach=d['beaches'][0];counts=Counter(b['district_id'] for b in phys)
    bounds=[min(p[0] for p in bp),min(p[1] for p in bp),max(p[0] for p in bp),max(p[1] for p in bp)]
    extent=[round(bounds[2]-bounds[0],3),round(bounds[3]-bounds[1],3)]
    for q in d['districts']:
        q.update(area_m2=round(m.area(q['polygon_m']),3),building_count=counts[q['id']],
                 share_percent=round(m.area(q['polygon_m'])/m.area(bp)*100,3))
    ped=copy.deepcopy(d);ped['roads']+=copy.deepcopy(d['paths']);m.build_graph(ped)
    d['pedestrian_graph']=ped['road_graph']
    routes=[]
    pairs=[('B01',p) for p in ('P01','P02','P03','BAD_CENTER','CLOCK_SQUARE')]+[
        ('B02','BAD_CENTER'),('B02','CLOCK_SQUARE'),('BAD_CENTER','CLOCK_SQUARE'),
        ('CLOCK_SQUARE','ELITE_GATE'),('B01','B06'),('B06','BEACH_VALLEY_ENTRY'),
        ('ELITE_GATE','BEACH_ENTRY')]
    pedpts={p['id']:p for p in ped['points']}
    for a,b in pairs:
        dist,ids=m.shortest(d,pts[a]['road_node_id'],pts[b]['road_node_id'])
        walk,wids=m.shortest(ped,pedpts[a]['road_node_id'],pedpts[b]['road_node_id'],mode='walk')
        er={e['id']:e for e in d['road_graph']['edges']};rids=[]
        for eid in ids:
            rid=er[eid]['road_id']
            if not rids or rids[-1]!=rid:rids.append(rid)
        routes.append(dict(from_id=a,to_id=b,length_m=round(dist,3),edge_ids=ids,road_ids=rids,
            pedestrian_length_m=round(walk,3),pedestrian_edge_ids=wids,
            van_60_seconds=round(dist/(60/3.6),2),van_90_seconds=round(dist/(90/3.6),2),
            walk_5_minutes=round(walk/(5000/60),2)))
    lengths={(r['from_id'],r['to_id']):r['length_m'] for r in routes}
    check('playable extent <=1000m on both axes',max(extent)<=1000,str(extent))
    for pid in ('P01','P02','P03'):check('B01 -> '+pid+' <=200m',lengths['B01',pid]<=200,str(lengths['B01',pid]))
    check('B01 -> bad centre >=400m',lengths['B01','BAD_CENTER']>=400,str(lengths['B01','BAD_CENTER']))
    check('bad centre -> square <=200m',lengths['BAD_CENTER','CLOCK_SQUARE']<=200,str(lengths['BAD_CENTER','CLOCK_SQUARE']))
    check('square -> elite gate <=200m',lengths['CLOCK_SQUARE','ELITE_GATE']<=200,str(lengths['CLOCK_SQUARE','ELITE_GATE']))
    for label,poly in [('boundary',bp),('beach',beach['polygon_m'])]+[(q['id'],q['polygon_m']) for q in d['districts']]:
        check(label+' polygon simple',simple(poly))
        if label!='beach':check(label+' smooth organic outline',len(poly)>=40 and turn_max(poly)<42,f'{len(poly)} vertices / turn {turn_max(poly):.2f}deg')
    overlap=[(a['id'],b['id']) for i,a in enumerate(d['districts']) for b in d['districts'][i+1:] if strict_overlap(a['polygon_m'],b['polygon_m'])]
    check('district envelopes do not overlap',not overlap,str(overlap))
    outside=[q['id'] for q in d['districts'] if any(not contained(p,bp) for p in q['polygon_m'])]
    check('district envelopes within playable boundary',not outside,str(outside))
    hits=[(a['id'],b['id']) for i,a in enumerate(phys) for b in phys[i+1:] if strict_overlap(a['poly'],b['poly'])]
    check('building footprints do not overlap',not hits,str(hits))
    outside=[b['id'] for b in phys if any(not contained(p,bp) or not contained(p,ds[b['district_id']]['polygon_m']) for p in b['poly'])]
    check('every building inside its district and playable boundary',not outside,str(outside))
    road_hits=[]
    for b in phys:
        for r in d['roads']+d['paths']:
            if any(v7.gap(b['poly'],a,c)<r['width_m']/2-.01 for a,c in zip(r['polyline_m'],r['polyline_m'][1:])):
                road_hits.append((b['id'],r['id']))
    check('buildings clear of all roads, driveways and paths',not road_hits,str(road_hits))
    wet=[]
    for b in phys:
        for w in d['water']:
            if ('polygon_m' in w and strict_overlap(b['poly'],w['polygon_m'])) or any(
                v7.gap(b['poly'],a,c)<w['width_m']/2 for a,c in zip(w.get('centerline_m',[]),w.get('centerline_m',[])[1:])):
                wet.append((b['id'],w['id']))
    check('buildings clear of lake, rivers, canal and sea',not wet,str(wet))
    railhits=[b['id'] for b in phys if any(v7.gap(b['poly'],a,c)<2 for a,c in zip(d['railway']['polyline_m'],d['railway']['polyline_m'][1:]))]
    check('railway 4m corridor clear of buildings',not railhits,str(railhits))
    for label,g in [('vehicle',d['road_graph']),('walk',d['pedestrian_graph'])]:
        seen=v11.reachable(g,g['nodes'][0]['id'])
        check(label+' graph connected',len(seen)==len(g['nodes']),f'{len(seen)}/{len(g["nodes"])}')
    check('exact road classes, widths and lane limits',all(r['width_m']==WIDTHS[r['class']] and r.get('lanes',1)<=2 and
        (r['class']!='rural_road' or r['lanes']==1) for r in d['roads']+d['paths']))
    check('walk-only beach path excluded from vehicle graph',all(e['van_access'] and e['class']!='passage' for e in d['road_graph']['edges']))
    long_axis=[]
    for r in d['roads']:
        if r.get('approved_straight_exception'):continue
        for a,b in zip(r['polyline_m'],r['polyline_m'][1:]):
            if m.length(a,b)>35 and min(abs(a[0]-b[0]),abs(a[1]-b[1]))<.02:long_axis.append(r['id'])
    check('no long axis-aligned streets outside approved courts',not long_axis,str(long_axis))
    slabs=[b for b in d['building_masses'] if b['kind']=='slab']
    oldslabs=[b for b in original['building_masses'] if b['kind']=='slab']
    check('all nine slab footprints and three courtyard polygons exactly v11',slabs==oldslabs and d['microdistricts']==original['microdistricts'])
    gaps=v11.courtyard_gaps(d)
    check('approved slab-to-avenue setbacks exactly 10m',all(abs(g-10)<.01 for g in gaps),str(gaps))
    check('approved continuous straight avenue retained',roads['ARC_AVENUE']['polyline_m']==[[470,723.5],[770,723.5]] and
        m.length(roads['ARC_RURAL']['polyline_m'][-1],roads['ARC_AVENUE']['polyline_m'][0])<.001)
    check('den access remains between courts 1 and 2',all(581<p[0]<604 for p in roads['COURT_ACCESS_3']['polyline_m'] if p[1]>=737))
    check('villa footprint and centre exactly v11',fs['F07_VILLA']['center_m']==[414,530] and
        fs['F07_VILLA']['footprint_m']==next(f['footprint_m'] for f in original['functional_buildings'] if f['id']=='F07_VILLA'))
    check('villa terrace faces north toward relocated lake',fs['F07_VILLA']['lake_facing_direction']=='north' and
        next(s for s in d['functional_sites'] if s['id']=='VILLA07_TERRACE')['polygon_m'][0][1]>537)
    check('lake at 435,575 inside transition',next(w for w in d['water'] if w['id']=='LAKE')['center_m']==[435,575] and
        all(contained(p,ds['transition']['polygon_m']) for p in next(w for w in d['water'] if w['id']=='LAKE')['polygon_m']))
    check('P13 moves with lake and church moves to transition',pts['P13']['district_id']=='transition' and fs['F06_CHURCH']['district_id']=='transition')
    check('churchyard present',any(s['type']=='churchyard' and s['building_id']=='F06_CHURCH' for s in d['functional_sites']))
    check('exact requested removals',not REMOVED_FUNCTIONS.intersection(fs) and not REMOVED_HOUSES.intersection(b['id'] for b in d['building_masses']))
    check('only one cafe, purchasable',sum(f['type']=='cafe' for f in fs.values())==1 and fs['F06_CAFE2']['purchasable'])
    check('old town decluttered and five houses relocated',counts['old_town']==19 and sum(did!='old_town' for did,_,_ in HOUSE_LAYOUT.values())==5)
    check('all mandatory old-town functions and two towers retained',{'F06_HBASE','F06_REPAIR','F06_POLICE','F06_BANK','F06_SUPER','F06_CAFE2'}<=set(fs) and
        len([b for b in d['building_masses'] if b['district_id']=='old_town' and b['floors']>=12])==2)
    check('P09 behind supermarket away from its front door',pts['P09']['position_m'][0]>598 and pts['P09']['position_m'][1]>600)
    check('B02 and P04 separate short branches',fs['F06_HUT']['access_road_id']=='HUT_BRANCH' and
        fs['F06_BUYER']['access_road_id']=='RECEPTION_BRANCH' and roads['HUT_BRANCH']['length_m']<40 and roads['RECEPTION_BRANCH']['length_m']<40)
    check('transition retains gas, ruins and P09-4',{'F06_GAS','F06_RUINS'}<=set(fs) and 'P09-4' in pts)
    industry={f['id'] for f in fs.values() if f['district_id']=='industrial'}
    check('industrial correction: six structures, maintenance shed retained',industry=={'F06_COMPLEX','F06_CHIMNEY','F06_TOW','F06_DEPOT','F06_WARE1','F06_MAINT'},str(industry))
    check('depot at railway end',m.length(fs['F06_DEPOT']['center_m'],d['railway']['polyline_m'][-1])<30)
    check('exactly one level crossing on VALLEY_BRANCH',len(d['railway']['road_crossings'])==1 and d['railway']['road_crossings'][0]['road_id']=='VALLEY_BRANCH',str(d['railway']['road_crossings']))
    venues=[f for f in fs.values() if f['id'].startswith('F12_')]
    south=all(all(p[1]<nearest(p,d['railway']['polyline_m'])[1][1]-2 for p in f['footprint_m']) for f in venues)
    check('casino and two venues south of railway',len(venues)==3 and fs['F12_CASINO']['type']=='casino' and 2<=fs['F12_CASINO']['storeys']<=3 and south)
    check('casino parking supplied',any(s['id']=='CASINO12_PARKING' and s['capacity_vans']>=6 for s in d['functional_sites']))
    direct_route=next(r for r in routes if r['from_id']=='B02' and r['to_id']=='CLOCK_SQUARE')['road_ids']
    check('transition direct road bypasses bad district','TRANSITION_DIRECT' in direct_route and 'ARC_AVENUE' not in direct_route)
    check('four enlarged irregular elite gardens',len([p for p in d['plots'] if p['kind']=='elite_garden'])==4 and
        all(m.area(p['polygon_m'])>1800 for p in d['plots'] if p['kind']=='elite_garden'))
    gardenoutside=[p['id'] for p in d['plots'] if p['kind']=='elite_garden' and any(not contained(x,ds['elite']['polygon_m']) for x in p['polygon_m'])]
    gardenhits=[(p['id'],r['id']) for p in d['plots'] if p['kind']=='elite_garden' for r in d['roads'] if not r.get('access_only') and
        any(v7.gap(p['polygon_m'],a,b)<r['width_m']/2-.01 for a,b in zip(r['polyline_m'],r['polyline_m'][1:]))]
    check('elite gardens inside hill and clear of main streets',not gardenoutside and not gardenhits,str(gardenoutside+gardenhits))
    check('two beach entrances exactly as corrected',beach['access_road_ids']==['BEACH_ACCESS','BEACH_VALLEY_ACCESS'])
    touching=[r['id'] for r in d['roads'] if any(m.inside(p,beach['polygon_m']) for p in r['polyline_m'])]
    check('no other road enters beach',set(touching)==set(beach['access_road_ids']),str(touching))
    for pid in ('BEACH_ENTRY','BEACH_VALLEY_ENTRY'):
        removed=v11.reachable(d['road_graph'],pts['B01']['road_node_id'],removed_roads=beach['access_road_ids'])
        check(pid+' cut off when both authorized entrances removed',pts[pid]['road_node_id'] not in removed)
    check('beach width 45–60m along whole curve',all(45<=m.length(a,b)<=60 for a,b in zip(beach['land_edge_m'],beach['sea_edge_m'])))
    check('sea offshore band >=150m and return rule retained',next(w for w in d['water'] if w['id']=='SEA')['offshore_band_m']>=150 and
        next(w for w in d['water'] if w['id']=='SEA')['return_rule']=='return_to_last_ground_point')
    sea=next(w for w in d['water'] if w['id']=='SEA')
    offshore=sea['polygon_m'][len(beach['sea_edge_m']):]
    offshore_clearance=min(nearest(p,beach['sea_edge_m'])[0] for p in offshore)
    check('sea geometry measured >=150m beyond the curved coast',offshore_clearance>=150,f'{offshore_clearance:.3f}m')
    check('sea polygon simple and entirely outside playable land',simple(sea['polygon_m']) and not strict_overlap(sea['polygon_m'],bp))
    check('districts do not overlap beach or sea',not any(strict_overlap(q['polygon_m'],beach['polygon_m']) or
        strict_overlap(q['polygon_m'],sea['polygon_m']) for q in d['districts']))
    check('roads and walking paths inside playable boundary',all(all(contained(p,bp) for p in r['polyline_m']) for r in d['roads']+d['paths']))
    check('beach walking path entirely in sand',all(contained(p,beach['polygon_m']) for p in d['paths'][0]['polyline_m']))
    dryhits=[(r['id'],w['id']) for r in d['roads'] for w in d['water'] if w['id'] in {'LAKE','SEA'} and
        any(v7.gap(w['polygon_m'],a,b)<r['width_m']/2-.01 for a,b in zip(r['polyline_m'],r['polyline_m'][1:]))]
    check('all vehicle corridors clear of lake and sea',not dryhits,str(dryhits))
    lake=next(w for w in d['water'] if w['id']=='LAKE')
    oldlake=next(w for w in original['water'] if w['id']=='LAKE')
    ratio=m.area(lake['polygon_m'])/m.area(oldlake['polygon_m'])
    check('relocated lake remains similar in size to v11',.8<=ratio<=1.25,f'area ratio {ratio:.3f}')
    rivers={w['id']:w for w in d['water'] if w['id'].startswith('RIVER')}
    canal=next(w for w in d['water'] if w['id']=='CANAL')
    check('river remains connected from lake to canal',contained(rivers['RIVER_N']['centerline_m'][-1],lake['polygon_m']) and
        contained(rivers['RIVER_S']['centerline_m'][0],lake['polygon_m']) and
        m.length(rivers['RIVER_S']['centerline_m'][-1],canal['centerline_m'][0])<.01)
    unprotected=[]
    for r in d['roads']:
        for w in d['water']:
            for a,b in zip(r['polyline_m'],r['polyline_m'][1:]):
                for c,e in zip(w.get('centerline_m',[]),w.get('centerline_m',[])[1:]):
                    hit=m.crossing(a,b,c,e)
                    if hit and not any(s['road_id']==r['id'] and s['water_id']==w['id'] and m.length(s['position_m'],hit[0])<8
                        for s in d['water_crossings']):unprotected.append((r['id'],w['id']))
    check('every road/water intersection has a bridge or culvert',not unprotected,str(unprotected))
    coast=d['boundary']['coast_segments_m']
    check('coast many short consecutive segments, no wall',len(coast)>100 and max(m.length(a,b) for a,b in coast)<20 and
        all(a==beach['sea_edge_m'][i] and b==beach['sea_edge_m'][i+1] for i,(a,b) in enumerate(coast)))
    check('two beach turnaround lots inside sand',all(all(contained(p,beach['polygon_m']) for p in s['polygon_m'])
        for s in d['functional_sites'] if s['type']=='turnaround'))
    barrierhits=[(q['id'],r['id']) for q in d['vegetation_parcels'] if q['kind']=='interdistrict_barrier'
        for r in d['roads']+d['paths'] if any(v7.gap(q['polygon_m'],a,b)<r['width_m']/2-.015 for a,b in zip(r['polyline_m'],r['polyline_m'][1:]))]
    check('fences leave roads and foot paths clear',not barrierhits,str(barrierhits))
    check('new direct road opens concrete fence, valley beach road opens wooden fence',any('TRANSITION_DIRECT' in q.get('gate_road_ids',[]) and
        q['material']=='concrete_fence' for q in d['vegetation_parcels']) and any('BEACH_VALLEY_ACCESS' in q.get('gate_road_ids',[]) and
        q['material']=='wooden_fence' for q in d['vegetation_parcels']))
    shore_fences=[q for q in d['vegetation_parcels'] if q.get('continuity_group')=='BEACH_ACCESS_CONTROL']
    open_shore=[]
    for p in sample_line(beach['land_edge_m'],3):
        if any(nearest(p,roads[rid]['polyline_m'])[0]<roads[rid]['width_m']/2+2.3 for rid in beach['access_road_ids']):continue
        if min(nearest(p,q['axis_m'])[0] for q in shore_fences)>1.8:open_shore.append(p)
    check('shore fence closed everywhere except two authorized entrances',not open_shore,str(open_shore[:8]))
    check('each beach turnaround served by its own road',all(m.inside(pts[pid]['position_m'],next(s['polygon_m'] for s in d['functional_sites'] if s['id']==sid))
        for pid,sid in [('BEACH_ENTRY','BEACH_TURNAROUND'),('BEACH_VALLEY_ENTRY','BEACH_VALLEY_TURNAROUND')]))
    check('elite district and all gardens enlarged over v11',ds['elite']['area_m2']>next(q['area_m2'] for q in original['districts'] if q['id']=='elite') and
        all(m.area(p['polygon_m'])>2*m.area(next(q['polygon_m'] for q in original['plots'] if q['id']==p['id']))
            for p in d['plots'] if p['kind']=='elite_garden'))
    for ex in d['exits']:
        check('mandatory return through '+ex['post_id'],math.isinf(m.shortest(d,pts['B01']['road_node_id'],ex['dead_end_node_id'],blocked=pts[ex['post_id']]['road_node_id'])[0]))
    check('water crossings explicitly bridge or culvert',all(s['kind'] in {'bridge','short_canal_tunnel'} for s in d['water_crossings']) and len(d['water_crossings'])>=2,str(d['water_crossings']))
    check('v11 top-level schema and container types retained',all(k in d and type(d[k])==type(value) for k,value in original.items()))
    fields={'roads':{'id','class','polyline_m','width_m'},'building_masses':{'id','center_m','polygon_m','floors','kind','district_id'},
        'functional_buildings':{'id','center_m','width_m','depth_m','footprint_m','storeys','label_ru','type'},
        'districts':{'id','polygon_m','parent_id'},'plots':{'id','kind','polygon_m'},'beaches':{'id','polygon_m','access_road_ids'}}
    check('converter nested schema preserved',all(req<=set(q) for key,req in fields.items() for q in d[key]))
    for key in ('roads','points','paths','building_masses','functional_buildings','functional_sites','plots','vegetation_parcels'):
        check(key+' unique IDs',len({q['id'] for q in d[key]})==len(d[key]))
    check('B01–B06 and P01–P16 canonical IDs retained',{p['canonical_id'] for p in original['points']}<={p['canonical_id'] for p in d['points']})
    check('all v11 and earlier file hashes unchanged',hashes()==d['provenance']['previous_files_sha256'])
    check('older revisions match independent v11 recorded hashes',all(hashes().get(name)==digest
        for name,digest in original['provenance']['previous_files_sha256'].items()))
    d['metrics']=dict(area_m2=round(m.area(bp),3),bounds_m=bounds,extent_m=extent,routes=routes,
        building_count=len(phys),building_counts_by_district=dict(counts),
        common_landscape_area_m2=round(m.area(bp)-sum(q['area_m2'] for q in d['districts'])-m.area(beach['polygon_m']),3),
        timing_assumption='constant-speed route arithmetic; not gameplay or subjective visual acceptance')
    d['functional_statistics']=dict(building_count=len(fs),district_counts=dict(Counter(f['district_id'] for f in fs.values())),
        type_counts=dict(Counter(f['type'] for f in fs.values())),promoted_existing_count=sum('source_building_id' in f for f in fs.values()),
        new_footprint_count=sum('source_building_id' not in f for f in fs.values()))
    d['residential_statistics']=dict(complex_count=3,slab_count=9,physical_building_count=counts['residential'])
    d['hamlet_statistics']=dict(farmstead_count=4,building_count=counts['village'],start_cluster_count=1)
    d['passage_statistics']=dict(count=len(d['paths']),total_length_m=sum(p['length_m'] for p in d['paths']),policy='beach only, walk only, two entrances')
    d['start_cluster_home_routes_m']={}
    d['validation']=dict(passed=all(c['passed'] for c in checks),checks=checks)
    if strict and not d['validation']['passed']:raise ValueError(json.dumps([c for c in checks if not c['passed']],ensure_ascii=False,indent=2))
    return [c for c in checks if not c['passed']]


def render(d):
    s=m.SVG();s.rect(0,0,2400,2400,'#f7f4eb')
    s.text(75,65,'VOLUNTEERS ONLY   /   R01 — v12',34,'#273c42','bold')
    s.text(75,99,'Органический город · два входа на пляж · исправленный бриф 04.10.2026',19,'#627372')
    visible=d['boundary']['polygon_m']+next(w['polygon_m'] for w in d['water'] if w['id']=='SEA')
    lo=[min(p[k] for p in visible) for k in (0,1)];hi=[max(p[k] for p in visible) for k in (0,1)]
    scale=min(2130/(hi[0]-lo[0]),1510/(hi[1]-lo[1]))
    left=95+(2130-(hi[0]-lo[0])*scale)/2;top=160
    def xy(p):return [left+(p[0]-lo[0])*scale,top+(hi[1]-p[1])*scale]
    def poly(p,fill,stroke='none',width=1,**kw):s.poly([xy(q) for q in p],fill,stroke,width,**kw)
    def line(p,color,width=1,**kw):s.line([xy(q) for q in p],color,width,**kw)
    sea=next(w for w in d['water'] if w['id']=='SEA')
    poly(sea['polygon_m'],'#b8d7df')
    poly(d['boundary']['polygon_m'],'#e1e4cf')
    for q in d['districts']:poly(q['polygon_m'],q['color'],'#9ba396',.7)
    beach=d['beaches'][0];poly(beach['polygon_m'],'#efdfb2')
    line(beach['sea_edge_m'],'#f7edcf',4)
    for p in d['field_parcels_m']:poly(p,'#c7c69b','#b4b68f',.7)
    for p in d['plots']:
        color={'elite_garden':'#afc894','farmstead':'#eae1bf','front_yard':'#e6d7bd','villa_yard':'#d5c598'}.get(p['kind'],'#cfceba')
        poly(p['polygon_m'],color,'#a1b08a' if p['kind']=='elite_garden' else '#b3ab94',.55)
    for c in d['microdistricts']:poly(c['yard_polygon_m'],'#adbfac','#a2b4a0',.7)
    for site in d['functional_sites']:
        if 'polygon_m' not in site:continue
        color={'churchyard':'#c4cbaa','parking':'#b7b7aa','production_yard':'#b3b2b7',
            'tow_parking':'#b8b8b7','turnaround':'#d0c5a7','lake_terrace':'#c3a98c'}.get(site['type'],'#cec7b1')
        poly(site['polygon_m'],color,'#969c96',.6)
    for i in (1,2,3):poly(oval([899,566],[99-i*19,115-i*20],1),'none','#a2b78e',.65)
    # Sparse, irregular tree groups leave roads and footprints visible.
    forest=next(q['polygon_m'] for q in d['districts'] if q['id']=='forest')
    phys=v7.physical(d)
    for i in range(80):
        p=[114+(i*43.79)%214,466+(i*23.47)%70]
        if not m.inside(p,forest):continue
        if any(nearest(p,r['polyline_m'])[0]<r['width_m']/2+4 for r in d['roads']):continue
        if any(m.inside(p,b['poly']) for b in phys):continue
        x,y=xy(p);s.circle(x,y,3+(i%4), '#93ac91',opacity='.48')
    for q in d['vegetation_parcels']:
        if q['kind']=='orchard':
            poly(q['polygon_m'],'#b2c198')
            c=[sum(p[k] for p in q['polygon_m'])/len(q['polygon_m']) for k in (0,1)]
            for dx,dy in ((-2,-2),(2,1),(-1,2)):
                x,y=xy([c[0]+dx,c[1]+dy]);s.circle(x,y,3,'#7f9f76')
        else:
            color=v11.FENCE_STYLES[q['material']][0]
            line(q['axis_m'],color,1.5 if q['material']!='canal_railing' else .85)
            if q['tree_line']:
                for p in q['axis_m'][::10]:
                    x,y=xy([p[0]-3,p[1]]);s.circle(x,y,2.8,'#829b77',opacity='.75')
    n=len(beach['sea_edge_m'])
    inland=[d['boundary']['polygon_m'][n-1]]+d['boundary']['polygon_m'][n:]+[d['boundary']['polygon_m'][0]]
    line(inland,'#827b6a',2.6)
    for w in d['water']:
        if w['id']=='SEA':continue
        if 'polygon_m' in w:poly(w['polygon_m'],'#83b3c5','#638e9d',.8)
        else:
            if w['id']=='CANAL':line(w['centerline_m'],'#9babae',w['width_m']*scale)
            line(w['centerline_m'],'#7caec2',w.get('wet_width_m',w['width_m'])*scale)
    rail=d['railway']['polyline_m']
    line(rail,'#b4ad9f',4.8*scale);line(rail,'#52595a',1.1)
    line(rail,'#52595a',4.6,stroke_dasharray='2 11')
    for r in d['roads']:
        line(r['polyline_m'],'#9d9f91',r['width_m']*scale+1.2)
        line(r['polyline_m'],d['road_classes'][r['class']]['color'],r['width_m']*scale)
    for p in d['paths']:line(p['polyline_m'],'#997f57',1.25,stroke_dasharray='4 6')
    for bridge in d['water_crossings']:
        line(bridge['deck_axis_m'],'#8a9592',roads_width(d,bridge['road_id'])*scale+1.3)
        line(bridge['deck_axis_m'],'#eee9db',roads_width(d,bridge['road_id'])*scale)
    for ex in d['exits']:
        for p in ex['barrier_polygons_m']:poly(p,'#7d8572','#656d60',.9)
        x,y=xy(ex['dead_end_m']);s.line([[x-5,y-5],[x+5,y+5]],'#794f45',2);s.line([[x-5,y+5],[x+5,y-5]],'#794f45',2)
    functional={f['id']:f for f in d['functional_buildings']}
    for b in phys:
        f=functional.get(b['id']);generic=next((q for q in d['building_masses'] if q['id']==b['id']),None)
        fill='#a98d73'
        if f:
            fill='#7d9190' if f['type'] in {'industrial_complex','depot','warehouse','maintenance_shed','tow_yard','chimney'} else '#a99079'
            if f.get('poi_id','').startswith('B'):fill='#b57f56'
            if f['type'] in {'mansion','prestige_base'}:fill='#b29473'
            if f['id'].startswith('F12_'):fill='#9b7fa0'
        elif generic and generic['kind']=='slab':fill='#8d9aa7'
        elif generic and generic['floors']>=12:fill='#7d829b'
        poly(b['poly'],fill,'#566264',.8)
        if generic and (generic['kind']=='slab' or generic['floors']>=12):
            x,y=xy(generic['center_m']);s.text(x,y+3,str(generic['floors'])+'э',10,'#f8f4e8','bold','middle')
    occupied=[]
    def box_points(poly):
        p=[xy(q) for q in poly];return (min(x for x,y in p)-3,min(y for x,y in p)-3,max(x for x,y in p)+3,max(y for x,y in p)+3)
    occupied += [box_points(b['poly']) for b in phys]
    captions=[('ЛЕСНАЯ ПОЛОСА',[282,499]),('ХУТОР',[198,706]),('ПЕРЕХОД',[413,775]),
        ('НЕБЛАГОПОЛУЧНЫЙ РАЙОН',[633,879]),('СТАРЫЙ ГОРОД',[589,535]),
        ('ЭЛИТНЫЙ ХОЛМ',[891,585]),('ПРОМЫШЛЕННАЯ ОКРАИНА',[658,370]),
        ('МАЛАЯ ДОЛИНА',[421,453]),('ПЛЯЖ · 55 м',[650,280]),('МОРЕ',[668,145])]
    for value,p in captions:
        x,y=xy(p);size=17 if value!='МОРЕ' else 25
        s.text(x,y,value,size,'#546960','bold','middle',halo=True)
        width=len(value)*size*.55;occupied.append((x-width/2-4,y-size-3,x+width/2+4,y+5))
    labels=[]
    names={'B01':'Вагон','B02':'Хижина','B03':'Гараж','B04':'Старый дом','B05':'Промкомплекс','B06':'Вилла у озера',
        'P01':'Объявление','P02':'Дом деда','P03':'Аптека','P04':'Приёмка','P05':'Автомастерская','P06':'Бар','P07':'Притон',
        'P08':'Больница','P10':'Полиция','P11':'Банк / ATM','P11-2':'ATM магазина','P11-3':'ATM больницы',
        'P12':'Эвакуатор','P14':'Депо','P15':'Особняк / VIP','P15-2':'Особняк 2','P13':'Озеро: спуск',
        'P13-2':'Река: спуск','P13-3':'Канал: спуск','P13-4':'Мусорки','P13-5':'Мусорки','P16':'Пост СЗ','P16-2':'Пост СВ',
        'P09':'За супермаркетом','P09-2':'Встреча: дворы','P09-3':'Встреча: B05','P09-4':'Встреча: переход',
        'WATER_TOWER':'Водонапорная башня','CHIMNEY':'Труба / 85 м','BAD_CENTER':'Центр района',
        'CLOCK_SQUARE':'Малая площадь','ELITE_GATE':'Элитка: въезд','BAD_BLOCK':'Двор 1','BAD_BLOCK_2':'Двор 2','BAD_BLOCK_3':'Двор 3',
        'BEACH_ENTRY':'Пляж: въезд из элитки','BEACH_VALLEY_ENTRY':'Пляж: въезд из долины'}
    for p in d['points']:
        pid=p['id'];value=names[pid] if p['category'] in {'reference','landmark'} or pid.startswith('BEACH') else pid+' · '+names[pid]
        labels.append((0 if pid.startswith('B0') else 1,p['position_m'],value,p['category']=='base'))
    short={'F06_CAFE2':'Кафе у проспекта · покупка','F06_SUPER':'Супермаркет','F06_CHURCH':'Церковь',
        'F06_GAS':'АЗС','F06_RUINS':'Руины','F06_WARE1':'Склад 1','F06_MAINT':'Ремонтный сарай',
        'F12_CASINO':'Казино · 3 этажа','F12_NIGHTCLUB':'Ночной клуб','F12_BOWLING':'Боулинг / аркада',
        'F06_GUARD':'Охрана','F06_24':'Магазин 24 ч','F06_VSHOP':'Лавка','F06_BUS':'Остановка',
        'F06_BARN':'Сарай деда','F08_MANSION_1':'Особняк 1','F06_MANSION_3':'Особняк 3'}
    for fid,value in short.items():labels.append((2,functional[fid]['center_m'],value,False))
    label_boxes=[]
    def intersection(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    for _,p,value,base in sorted(labels,key=lambda q:q[0]):
        x,y=xy(p);size=15 if not base else 16;w=len(value)*size*.55;h=size+4
        candidates=[]
        for radius in (14,30,48,70,100,135):
            for dx,dy in ((1,-1),(1,1),(-1,-1),(-1,1),(0,-1),(0,1),(1,0),(-1,0)):
                lx=x+dx*radius;ly=y+dy*radius
                if dx<0:lx-=w
                elif dx==0:lx-=w/2
                if dy==0:ly+=h/3
                box=(lx-4,ly-h,lx+w+4,ly+5)
                if box[0]<45 or box[2]>2355 or box[1]<120 or box[3]>1730:continue
                score=sum(intersection(box,b) for b in occupied)*12+radius+abs(dx)*2
                candidates.append((score,box,lx,ly,radius))
        _,box,lx,ly,radius=min(candidates)
        tx=max(box[0],min(x,box[2]));ty=max(box[1],min(y,box[3]))
        if radius>=30:s.line([[x,y],[tx,ty]],'#7e8b88',.75)
        s.circle(x,y,3.8 if base else 2.8,'#b36f3f' if base else '#47707a',stroke='#f5f1e6',stroke_width='1')
        s.text(lx,ly,value,size,'#3b4e51','bold' if base else 'normal',halo=True)
        occupied.append(box);label_boxes.append(box)
    # Geographic labels do not obscure the corrected access rules.
    for text,p in [('Озеро',[434,575]),('Проспект',[738,718]),('Прямая улица',[489,611]),('Канал',[572,434])]:
        x,y=xy(p);s.text(x,y,text,12,'#657b7e','normal','middle',halo=True)
    for crossing in d['railway']['road_crossings']:
        x,y=xy(crossing['position_m']);s.circle(x,y,7,'none',stroke='#a5654c',stroke_width='2')
    # North arrow and explicit metric scale.
    s.line([[2280,235],[2280,170]],'#3c5358',2);s.poly([[2280,155],[2271,176],[2289,176]],'#3c5358')
    s.text(2280,140,'С',20,'#3c5358','bold','middle')
    s.line([[85,1735],[85+100*scale,1735]],'#3c5358',3)
    for dist in (0,50,100):
        x=85+dist*scale;s.line([[x,1728],[x,1742]],'#3c5358',1.3);s.text(x,1764,str(dist)+' м',13,'#4c6265','normal','middle')
    s.text(2340,1760,'Размер суши: '+ ' × '.join(f'{z:.0f}' for z in d['metrics']['extent_m'])+' м',16,'#4c6265','normal','end')
    s.line([[65,1800],[2335,1800]],'#c1c8ba',1)
    s.text(75,1842,'ДОРОГИ И ПРЕГРАДЫ',19,'#3b555a','bold')
    for i,(cls,label) in enumerate([('highway','Проспект — 7 м, 2 полосы'),('town_street','Городская — 6 м, 2 полосы'),
        ('rural_road','Сельская — 3,8 м, 1 полоса'),('passage','Пешком по пляжу — 2,5 м')]):
        y=1875+i*34
        if cls=='passage':s.line([[78,y],[130,y]],'#997f57',1.25,stroke_dasharray='4 6')
        else:
            s.line([[78,y],[130,y]],'#9d9f91',10.2)
            s.line([[78,y],[130,y]],d['road_classes'][cls]['color'],9)
        s.text(143,y+5,label,16)
    for i,(material,label) in enumerate([('concrete_fence','Бетон — 2,5 м'),('wooden_fence','Дерево — 1,6 м + деревья'),
        ('elite_fence','Элитная ограда — 2,4 м'),('canal_railing','Перила канала — 1,1 м')]):
        y=2035+i*32;s.line([[78,y],[130,y]],v11.FENCE_STYLES[material][0],2);s.text(143,y+5,label,16)
    s.text(655,1842,'ФИЗИЧЕСКИЕ ЗДАНИЯ',19,'#3b555a','bold')
    for i,q in enumerate(d['districts']):
        y=1875+i*33;s.rect(655,y-12,17,17,q['color']);s.text(684,y+2,q['name_ru'],16)
        s.text(1090,y+2,str(q['building_count']),16,'#3b555a','bold','end')
    s.text(655,2167,'Всего: '+str(d['metrics']['building_count'])+'  ·  Старый город: 37 → 19',17,'#3b555a','bold')
    s.text(1175,1842,'ОСНОВНЫЕ МАРШРУТЫ / НА БУСИКЕ',19,'#3b555a','bold')
    routepairs=[('B01','BAD_CENTER'),('B01','CLOCK_SQUARE'),('B02','BAD_CENTER'),('B02','CLOCK_SQUARE'),
        ('BAD_CENTER','CLOCK_SQUARE'),('CLOCK_SQUARE','ELITE_GATE')]
    for i,(a,b) in enumerate(routepairs):
        r=next(r for r in d['metrics']['routes'] if r['from_id']==a and r['to_id']==b)
        target={'BAD_CENTER':'центр района','CLOCK_SQUARE':'площадь','ELITE_GATE':'элитка'}[b]
        source={'BAD_CENTER':'Центр района','CLOCK_SQUARE':'Площадь'}.get(a,a)
        s.text(1175,1878+i*33,source+' → '+target,16)
        s.text(1640,1878+i*33,f'{r["length_m"]:.0f} м',16,'#3b555a','bold','end')
    s.text(1730,1842,'КЛЮЧЕВЫЕ ИЗМЕНЕНИЯ',19,'#3b555a','bold')
    for i,text in enumerate(['Пляж 55 м; море ≥150 м дальше.','Два въезда: элитка + долина.',
        'Казино, клуб и боулинг ниже ЖД.','Ровно один переезд в долину.',
        'Ремонтный сарай в промзоне сохранён.','Кафе у проспекта можно купить.',
        'B06 на месте; терраса к новому озеру.','Проспект и 3 двора сохранены.']):s.text(1730,1878+i*33,text,16)
    s.text(75,2250,'Проверки: '+str(len(d['validation']['checks']))+' / геометрия и связность. Промежутки между районами — общая озеленённая территория.',16,'#607371')
    s.text(75,2280,'Схема ArtSource в метрах, вне импорта Unity. Субъективное качество и движение требуют проверки в игре.',15,'#74827c')
    d['render_statistics']=dict(canvas_px=[2400,2400],scale_px_per_m=round(scale,4),label_count=len(label_boxes),
        overlapping_label_pairs=sum(intersection(a,b)>0 for i,a in enumerate(label_boxes) for b in label_boxes[i+1:]))
    return s.finish()


def roads_width(d,rid):
    return next(r['width_m'] for r in d['roads'] if r['id']==rid)


def report(d):
    counts=d['metrics']['building_counts_by_district'];lines=[
        '# R01 v12 — органический план',
        '',
        'Исправленный бриф от 04.10.2026: второй вход на пляж из долины; ремонтный сарай сохранён.',
        f'Суша: {d["metrics"]["extent_m"][0]:.1f} × {d["metrics"]["extent_m"][1]:.1f} м; {d["metrics"]["building_count"]} физических зданий.',
        'Контуры районов и границы — плавные асимметричные кривые; улицы с мягкими изгибами вместо сетки.',
        'Между районами оставлены общие озеленённые полосы, дороги и вода; это не дополнительные районы.',
        'Удалено: Малый отель, Почта, Одежда и маски, Кафе у площади; Склад 2 и Металлолом с площадкой.',
        'Удалены четыре дома южнее прежней церкви: O06_T3_U4, O06_T3_U6, O06_T5_U4, O06_T5_U5.',
        'Удалены четыре дома вокруг Кафе у площади: O06_T2_U1, O06_T2_U3, O06_T2_U4, O06_T2_U5.',
        'Старый город: 37 → 19 зданий; сохранены B04, P05, супермаркет, P09 позади, полиция, банк, два высотных ориентира, площадь и P13-3/P13-5.',
        'Кафе у проспекта — единственное кафе; игроки могут купить его (purchasable: true).',
        'O06_T1_U2, O06_T1_U3, O06_T5_U2, O06_T5_U3 перенесены в переход; O06_T5_U1 — на край хутора.',
        'Оставшиеся малые дома переразмещены отдельно, с разными углами и широкими промежутками, без террасных рядов.',
        'Озеро (~435;575), P13 и церковь с двором перенесены в переход; река соединяет озеро и канал.',
        'TRANSITION_DIRECT — новый прямой маршрут через разрыв бетонной ограды к западу старого города, в обход спальника.',
        'B02 и P04 остались на отдельных коротких ветках; АЗС, руины и P09-4 сохранены.',
        'Проспект y=723,5 и девять корпусов/три двора точно сохранены: дворы 1–2 севернее, 3 южнее; отступы 10 м.',
        'Подъезд к притону проходит между дворами 1 и 2; на стыке спальника и старого города ограды нет.',
        'Элитный холм увеличен; четыре особняка расставлены нерегулярно, сады >1800 м² каждый; охрана и ограда 2,4 м сохранены.',
        'B06 сохранён в (414;530), выше ЖД; терраса виллы обращена на север к новому озеру.',
        'Ниже ЖД добавлены казино (3 этажа, парковка на 8 бусиков), ночной клуб и боулинг/аркада.',
        'VALLEY_BRANCH ведёт из перехода в долину через ровно один железнодорожный переезд.',
        'Промзона: B05 с трубой, P12, депо P14 у конца ЖД, Склад 1 и Ремонтный сарай — 6 структур.',
        '',
        'Пляж шириной 55 м плавно огибает долину, промзону и элитку, включая её восточную и северо-восточную стороны.',
        'Входы только BEACH_ACCESS из элитки и BEACH_VALLEY_ACCESS из долины; у обоих есть небольшой разворот/парковка.',
        'Долинная ограда разомкнута только под второй въезд; промзона закрыта, концы пляжа закрыты скалами.',
        'По песку соединён пешеходный маршрут; автомобильного проезда вдоль всего пляжа нет.',
        'Канал выпускается в море по закрытой трубе под землёй и пляжем; открытая вода не разрезает песок.',
        'Море продолжается минимум на 150 м за берег; возврат игрока и бусика — в последнюю точку суши.',
        f'coast_segments_m: {len(d["boundary"]["coast_segments_m"])} коротких сегментов, без внешней стены.',
        '',
        '| Район | Физические здания |',
        '|---|---:|',
    ]
    lines += [f'| {q["name_ru"]} | {counts[q["id"]]} |' for q in d['districts']]
    lines += ['', '| Маршрут | Бусик, м | Пешком, м |','|---|---:|---:|']
    for r in d['metrics']['routes'][:9]:
        lines.append(f'| {r["from_id"]} → {r["to_id"]} | {r["length_m"]:.1f} | {r["pedestrian_length_m"]:.1f} |')
    lines += ['',f'Все {len(d["validation"]["checks"])} проверки пройдены: размеры, маршруты, пересечения, связность, два входа на пляж и один переезд.',
        'B01 → площадь: V_MAIN → ARC_RURAL → TRANSITION_DIRECT; B01/B02 → спальник: ARC_RURAL → ARC_AVENUE.',
        'B02 → площадь: ARC_RURAL → TRANSITION_DIRECT; площадь → элитка: OLD_ELITE_CONNECTOR.',
        'JSON сохраняет схему v11, beaches и boundary.coast_segments_m; старые файлы проверены SHA-256.',
        'PNG просмотрен перед сдачей. План не заменяет проверку субъективного качества и движения в Unity.']
    assert len(lines)<=60,len(lines)
    return '\n'.join(lines)+'\n'


def main():
    before=hashes();d=seed();analyse(d)
    svg=render(d);ET.fromstring(svg)
    (ROOT/(STEM+'.svg')).write_text(svg,encoding='utf-8')
    magick=r'C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe'
    subprocess.run([magick,'-background','#f7f4eb','-density','96',str(ROOT/(STEM+'.svg')),
        str(ROOT/(STEM+'.png'))],check=True,cwd=ROOT)
    raw=(ROOT/(STEM+'.png')).read_bytes()
    assert raw[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',raw[16:24])==(2400,2400)
    (ROOT/(STEM+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (ROOT/(STEM+'_REPORT.md')).write_text(report(d),encoding='utf-8')
    assert hashes()==before,'A previous deliverable changed'
    print(json.dumps(dict(passed=d['validation']['passed'],checks=len(d['validation']['checks']),
        extent_m=d['metrics']['extent_m'],building_count=d['metrics']['building_count'],
        report_lines=len(report(d).splitlines()),render=d['render_statistics']),ensure_ascii=False))


if __name__=='__main__':main()
