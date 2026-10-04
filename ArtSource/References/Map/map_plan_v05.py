"""V05 functional layer. V04 geometry and earlier revision builders remain intact.

Functional buildings are a separate, explicitly typed layer; source_building_id
promotes an existing mass without double-counting its footprint. Pedestrian
passages have a separate graph so they cannot shorten reported van routes.
"""
import copy
import hashlib
import heapq
import json
import math
from collections import Counter


PALETTE = {
    'base': ('#aa6045', 'Б', 'Базы / дом деда'),
    'health': ('#e1ebe0', '+', 'Аптека / больница'),
    'retail': ('#d5a94e', 'М', 'Магазины / рынок / маски'),
    'food': ('#bd817d', 'Е', 'Бар / кафе / ресторан'),
    'service': ('#709dac', 'С', 'Автосервис / АЗС / почта'),
    'civic': ('#7a8eb7', 'Г', 'Полиция / школа / охрана'),
    'finance': ('#87a875', '$', 'Банк / банкоматы'),
    'industry': ('#928ba4', 'П', 'Депо / склады / гаражи'),
    'rural': ('#a5a36a', 'Ф', 'Ферма / руины'),
    'landmark': ('#c6b6d4', 'О', 'Башни / церковь / труба'),
    'lodging': ('#bc9975', 'Д', 'Дом / отель / особняки'),
    'shadow': ('#927179', 'Т', 'Приёмка / притон'),
}


def overlaps(m, p, q):
    return (any(m.inside(a, q) for a in p) or any(m.inside(a, p) for a in q)
            or any(m.crossing(a, b, c, d) for a, b in zip(p, p[1:]+p[:1])
                   for c, d in zip(q, q[1:]+q[:1])))


def outline(m, center, w, h, shape, angle=0):
    if shape == 'round':
        local = [(math.cos(i*math.pi/6)/2, math.sin(i*math.pi/6)/2) for i in range(12)]
    elif shape == 'cross':
        local = [(-.18,-.5),(.18,-.5),(.18,-.18),(.5,-.18),(.5,.18),
                 (.18,.18),(.18,.5),(-.18,.5),(-.18,.18),(-.5,.18),(-.5,-.18),(-.18,-.18)]
    elif shape == 'L':
        local = [(-.5,-.5),(.5,-.5),(.5,-.1),(-.1,-.1),(-.1,.5),(-.5,.5)]
    elif shape == 'U':
        local = [(-.5,-.5),(.5,-.5),(.5,.5),(.2,.5),(.2,-.1),(-.2,-.1),(-.2,.5),(-.5,.5)]
    elif shape == 'chapel':
        local = [(-.25,-.5),(.25,-.5),(.25,.23),(0,.5),(-.25,.23)]
    elif shape == 'shed':
        local = [(-.5,-.5),(.5,-.5),(.5,.28),(.35,.5),(-.35,.5),(-.5,.28)]
    else:
        return m.rectangle(*center, w, h, angle)
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    return [[round(center[0]+x*w*c-y*h*s,3),round(center[1]+x*w*s+y*h*c,3)] for x,y in local]


def segments(data):
    return [(r,a,b) for r in data['roads'] for a,b in zip(r['polyline_m'],r['polyline_m'][1:])]


def footprint_clear(data, m, poly, district, source=None, replace_historic=False):
    ds={d['id']:d for d in data['districts']}
    if not all(m.inside(p,ds[district]['polygon_m']) for p in poly): return False
    if district=='old_town' and any(m.inside(p,ds['elite']['polygon_m']) for p in poly): return False
    for r,a,b in segments(data):
        if r['id'].startswith('ACCESS_'): continue
        if m.inside(a,poly) or m.inside(b,poly) or any(m.crossing(a,b,c,d) for c,d in zip(poly,poly[1:]+poly[:1])): return False
        if any(m.projection(p,a,b)[0]<r['width_m']/2+2 for p in poly): return False
    for w in data['water']:
        if 'polygon_m' in w and overlaps(m,poly,w['polygon_m']): return False
        for a,b in zip(w.get('centerline_m',[]),w.get('centerline_m',[])[1:]):
            if any(m.projection(p,a,b)[0]<w['width_m']/2+4 for p in poly): return False
            if any(m.crossing(a,b,c,d) for c,d in zip(poly,poly[1:]+poly[:1])): return False
    for a,b in zip(data['railway']['polyline_m'],data['railway']['polyline_m'][1:]):
        if any(m.projection(p,a,b)[0]<5 for p in poly) or any(m.crossing(a,b,c,d) for c,d in zip(poly,poly[1:]+poly[:1])): return False
    for b in data['building_masses']:
        if b['id']==source or (replace_historic and b['kind']=='historic_house'): continue
        if overlaps(m,poly,b['polygon_m']): return False
    return not any(overlaps(m,poly,f['footprint_m']) for f in data.get('functional_buildings',[]))


def seed(m):
    data=json.loads((m.ROOT/'MAP_PLAN_R01_v04.json').read_text(encoding='utf-8'))
    data.update(revision='v05',title_ru='VOLUNTEERS ONLY — план карты R01 (v05)')
    data['provenance']=dict(brief='req_map_plan_v05.md',source='MAP_PLAN_R01_v04.json',
        owner_decisions_date='2026-10-04',method='unchanged v04 geography; functional layer; sparse pedestrian passages',
        previous_files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for rev in ('v02','v03','v04') for p in sorted(m.ROOT.glob(f'MAP_PLAN_R01_{rev}*'))})
    data['road_classes']['passage']=dict(name_ru='Пеший проход 3–4 м',width_m=3.5,color='#567e67',walkable=True,van_access=False)
    data['planning_notes_ru'] += ['v05: функциональные здания — отдельный слой; source_building_id исключает двойной счёт.',
        'Только несколько локальных проходов к машине; бусик остаётся основным транспортом.',
        'P12 перенесена в промзону по брифу v05; въезд и отдельная стоянка сохранены как предложение.']
    pts={p['id']:p for p in data['points']}
    pts['P12'].update(district_id='industrial',position_m=[1830,385])
    next(r for r in data['roads'] if r['id']=='ACCESS_P12')['polyline_m']=[[1790,420],[1830,385]]
    data['functional_buildings']=[]
    data['functional_sites']=[]
    data['replaced_generic_building_ids']=[]

    def add(id,typ,dist,label,group,w,h,shape='rect',storeys=1,poi=None,target=None,source=None):
        anchor=pts[poi]['position_m'] if poi else list(target)
        if source:
            b=next(b for b in data['building_masses'] if b['id']==source)
            center=b['center_m']; poly=b['polygon_m']; w=b['width_m'];h=b['depth_m'];storeys=b['floors']
        else:
            candidates=[(0,anchor,0)]
            for radius in range(12,145,12):
                for k in range(24):
                    a=k*math.pi/12
                    center=[round(anchor[0]+radius*math.cos(a),3),round(anchor[1]+radius*math.sin(a),3)]
                    candidates.append((radius,center,0))
            found=None
            for replace in (False,True) if dist=='old_town' else (False,):
                for radius,center,angle in candidates:
                    poly=outline(m,center,w,h,shape,angle)
                    if footprint_clear(data,m,poly,dist,replace_historic=replace):
                        found=(center,poly);break
                if found:break
            if not found: raise ValueError('No functional footprint fits: '+id)
            center,poly=found
            removed=[b['id'] for b in data['building_masses'] if b['kind']=='historic_house' and overlaps(m,poly,b['polygon_m'])]
            data['replaced_generic_building_ids']+=removed
            data['building_masses']=[b for b in data['building_masses'] if b['id'] not in removed]
        color,icon,_=PALETTE[group]
        f=dict(id=id,type=typ,district=dist,district_id=dist,label_ru=label,group=group,
            footprint_m=poly,storeys=storeys,center_m=center,width_m=w,depth_m=h,
            footprint_shape=shape,color=color,icon=icon,entrance_m=anchor)
        if poi:f['poi_id']=poi
        if source:f['source_building_id']=source
        data['functional_buildings'].append(f)
        return f

    add('F05_GRANDPA','grandpa_house','village','Дом деда','base',18,12,poi='P02',source='F04_01_1')
    add('F05_PHARMACY','pharmacy','village','Аптека','health',22,12,poi='P03',source='F04_02_1')
    add('F05_VSHOP','village_shop','village','Сельмаг','retail',24,16,'L',target=[700,1420])
    add('F05_BUS','bus_stop','village','Автобус','service',16,7,target=[640,1460])
    add('F05_FARM','barn_yard','village','Ферма / амбар','rural',18,12,source='F04_01_3',target=[412,1320])
    add('F05_WATER','water_tower','village','Водобашня','landmark',12,12,'round',poi='WATER_TOWER')
    add('F05_HUT','hut','transition','Хижина','base',20,14,'L',poi='B02')
    add('F05_BUYER','shadow_buyer','transition','Приёмка','shadow',32,20,'shed',poi='P04')
    add('F05_GAS','gas_station','transition','АЗС','service',42,24,'L',target=[1240,1770])
    add('F05_RUINS','abandoned_farm','transition','Руины фермы','rural',46,30,'U',target=[1120,2120])
    add('F05_GBASE','garage_base','residential','База-гараж','base',30,20,'shed',poi='B03')
    add('F05_REPAIR','car_workshop','residential','Автосервис','service',44,26,'U',poi='P05')
    add('F05_BAR','bar','residential','Бар','food',28,20,'L',poi='P06')
    add('F05_DEN','den','residential','Притон','shadow',26,20,'L',storeys=2,poi='P07')
    add('F05_24','shop_24h','residential','24 часа','retail',30,18,'L',target=[1810,1945])
    add('F05_MARKET','small_market','residential','Рынок / киоски','retail',38,22,'U',target=[1580,1885])
    add('F05_SCHOOL','closed_school','residential','Школа закрыта','civic',68,36,'U',storeys=2,target=[1790,2140])
    boiler=add('F05_BOILER','boiler_house','residential','Котельная','industry',38,22,'L',target=[1440,1930])
    boiler['chimney_m']=[boiler['center_m'][0]-13,boiler['center_m'][1]-7]
    for i,target in enumerate(([1620,1800],[1710,1960]),1):
        add(f'F05_GARAGES_{i}','garage_rows','residential',f'Гаражные боксы {i}','industry',52,12,target=target)
    add('F05_ATM_BAD','atm_pavilion','residential','Банкомат','finance',8,7,poi='P11-2')
    add('F05_CLOCK','clock_tower','old_town','Часовая башня','landmark',13,13,'round',storeys=4,poi='CLOCK_SQUARE')
    add('F05_HOSPITAL','hospital','old_town','Больница','health',70,54,'cross',storeys=3,poi='P08')
    add('F05_POLICE','police_station','old_town','Полиция','civic',48,30,'U',storeys=2,poi='P10')
    add('F05_BANK','bank','old_town','Банк / банкоматы','finance',40,28,'L',storeys=3,poi='P11')
    add('F05_ATM_OLD','atm_pavilion','old_town','Банкомат','finance',8,7,poi='P11-3')
    add('F05_SUPER','supermarket','old_town','Супермаркет','retail',56,32,'L',poi='P09')
    add('F05_CAFE','cafe','old_town','Кафе','food',26,22,'L',storeys=2,target=[1840,1280])
    add('F05_CHURCH','church','old_town','Церковь','landmark',34,46,'chapel',storeys=2,target=[1610,800])
    add('F05_HOTEL','small_hotel','old_town','Отель','lodging',42,30,'U',storeys=3,target=[2130,1260])
    add('F05_POST','post_office','old_town','Почта','service',30,24,'L',storeys=2,target=[1440,1030])
    add('F05_MASKS','clothes_masks_shop','old_town','Одежда / маски','retail',32,22,'L',storeys=2,target=[1790,960])
    add('F05_HBASE','house_base','old_town','Дом-база','base',30,24,'L',storeys=3,poi='B04')
    for b in [b for b in data['building_masses'] if b['kind']=='mansion']:
        poi=next((p['id'] for p in data['points'] if p['id'] in ('P15','P15-2','B06') and m.length(p['position_m'],b['center_m'])<1),None)
        add('F05_'+b['id'],'prestige_base' if poi=='B06' else 'mansion','elite',
            'Престижная база' if poi=='B06' else ('Доступный особняк' if poi else 'Особняк'),
            'base' if poi=='B06' else 'lodging',24,18,poi=poi,target=b['center_m'],source=b['id'])
    add('F05_GUARD','private_security','elite','Частная охрана','civic',16,12,target=[1980,1080])
    add('F05_BOUTIQUE','boutique','elite','Бутик','retail',42,23,source='BLD299',target=[2130,1055])
    add('F05_COMPLEX','industrial_complex','industrial','Промкомплекс','base',70,40,poi='B05',source='BLD305')
    add('F05_DEPOT','depot','industrial','Депо','industry',54,28,'shed',poi='P14')
    add('F05_CHIMNEY','industrial_chimney','industrial','Труба','landmark',10,10,'round',poi='CHIMNEY')
    for bid in ('BLD304','BLD306','BLD307'):
        b=next(b for b in data['building_masses'] if b['id']==bid)
        add('F05_'+bid,'warehouse','industrial','Склад','industry',b['width_m'],b['depth_m'],source=bid,target=b['center_m'])
    tow=add('F05_TOW','tow_yard','industrial','Эвакуатор / стоянка','service',22,14,'L',poi='P12')
    scrap=add('F05_SCRAP','scrapyard','industrial','Металлолом','industry',32,18,'shed',target=[1620,270])
    for f,kind in [(tow,'tow_parking'),(scrap,'scrap_storage')]:
        # Yard is illustrative open ground, not another building footprint.
        data['functional_sites'].append(dict(id=f['id']+'_YARD',type=kind,district_id=f['district_id'],
            polygon_m=m.rectangle(*f['center_m'],f['width_m']+16,f['depth_m']+18),building_id=f['id']))
    for pid,typ,label in [('P09','parking_behind_supermarket','Встреча: парковка'),
                           ('P09-2','small_park','Встреча: сквер'),('P09-3','canal_meeting','Встреча: у канала')]:
        data['functional_sites'].append(dict(id='SITE_'+pid,type=typ,district_id='old_town',
            position_m=pts[pid]['position_m'],poi_id=pid,label_ru=label))
    build_passages(data,m)
    return data


def walking_obstacles(data, m, center, radius=220):
    promoted={f.get('source_building_id') for f in data['functional_buildings']}
    polys=[b['polygon_m'] for b in data['building_masses'] if b['id'] not in promoted]
    polys += [f['footprint_m'] for f in data['functional_buildings']]
    # Conservative bounding rectangles give the 3.5 m passage a real clearance.
    boxes=[]
    for p in polys:
        x0,x1=min(v[0] for v in p)-3,max(v[0] for v in p)+3
        y0,y1=min(v[1] for v in p)-3,max(v[1] for v in p)+3
        if m.length(center,[(x0+x1)/2,(y0+y1)/2])<radius:
            boxes.append([[x0,y0],[x1,y0],[x1,y1],[x0,y1]])
    return boxes


def visible_route(m, start, end, boxes, allowed):
    points=[start,end]
    for p in boxes:
        cx=sum(v[0] for v in p)/4;cy=sum(v[1] for v in p)/4
        points += [[v[0]+(.15 if v[0]>cx else -.15),v[1]+(.15 if v[1]>cy else -.15)] for v in p]
    def free(a,b):
        if not all(allowed([a[k]+(b[k]-a[k])*t for k in (0,1)]) for t in (0,.25,.5,.75,1)): return False
        return not any(m.inside(a,p) or m.inside(b,p) or any(m.crossing(a,b,c,d) for c,d in zip(p,p[1:]+p[:1])) for p in boxes)
    adj=[[] for p in points]
    for i,a in enumerate(points):
        for j in range(i+1,len(points)):
            b=points[j]
            if free(a,b):
                d=m.length(a,b);adj[i].append((j,d));adj[j].append((i,d))
    queue=[(0,0)];costs={0:0};prev={}
    while queue:
        cost,i=heapq.heappop(queue)
        if cost!=costs[i]:continue
        if i==1:
            route=[end]
            while i!=0:i=prev[i];route.append(points[i])
            return list(reversed(route))
        for j,d in adj[i]:
            if cost+d<costs.get(j,math.inf):
                costs[j]=cost+d;prev[j]=i;heapq.heappush(queue,(cost+d,j))
    return None


def build_passages(data,m):
    ds={d['id']:d['polygon_m'] for d in data['districts']}
    roadsegs=segments(data)
    data['paths']=[]
    def dry(p):
        for w in data['water']:
            if 'polygon_m' in w and m.inside(p,w['polygon_m']):return False
            if any(m.projection(p,a,b)[0]<w['width_m']/2+3 for a,b in zip(w.get('centerline_m',[]),w.get('centerline_m',[])[1:])):return False
        return True
    # Only three yard exits and two short rear alleys, all locally authored.
    specs=[('PASS_BAD_1','residential',[1930,2050],'Двор → к бусику'),
           ('PASS_BAD_2','residential',[1630,1810],'Гаражи → к бусику'),
           ('PASS_BAD_3','residential',[1720,1670],'Двор → боковая улица'),
           ('PASS_OLD_1','old_town',[1580,1310],'За супермаркетом'),
           ('PASS_OLD_2','old_town',[2105,1210],'Задний переулок')]
    for id,dist,anchor,label in specs:
        boxes=walking_obstacles(data,m,anchor)
        allowed=lambda p:m.inside(p,ds[dist]) and dry(p)
        starts=[anchor]+[[anchor[0]+dx,anchor[1]+dy] for dx,dy in [(0,20),(20,0),(-20,0),(0,-20),(30,30),(-30,-30)]]
        ends=sorted([(m.projection(anchor,a,b)[0],m.projection(anchor,a,b)[1],r['id'])
            for r,a,b in roadsegs if not r['id'].startswith(('ACCESS_','EXIT_')) and m.projection(anchor,a,b)[0]>25],key=lambda v:v[0])
        chosen=None
        for start in starts:
            if not allowed(start) or any(m.inside(start,p) for p in boxes):continue
            for _,end,rid in ends[:8]:
                if not allowed(end):continue
                route=visible_route(m,start,end,boxes,allowed)
                if route and 25<=sum(m.length(a,b) for a,b in zip(route,route[1:]))<=190:
                    chosen=(route,rid);break
            if chosen:break
        if not chosen:raise ValueError('Cannot fit sparse passage '+id)
        route,rid=chosen
        data['paths'].append(dict(id=id,**{'class':'passage'},district_id=dist,width_m=3.5,
            polyline_m=route,label_ru=label,walkable=True,van_access=False,
            kind='yard_exit' if dist=='residential' else 'rear_alley',street_road_id=rid,
            purpose_ru='Тихий короткий перенос NPC со двора к припаркованному бусику; не автомобильная срезка.'))
    # Short north-bank walk beneath an existing canal bridge, with no junction
    # onto its deck. Endpoints connect to the neighbouring quay/small street.
    anchor=[1440,665.2];boxes=walking_obstacles(data,m,anchor,130)
    left=next(m.crossing(a,b,[1400,665.2],[1510,665.2])[0] for r,a,b in roadsegs
        if r['id']=='O_SMALL_5' and min(a[1],b[1])<665.2<max(a[1],b[1]))
    right=next(m.crossing(a,b,[1400,665.2],[1510,665.2])[0] for r,a,b in roadsegs
        if r['id']=='O_QUAY' and min(a[1],b[1])<665.2<max(a[1],b[1]))
    route=visible_route(m,left,right,boxes,lambda p:m.inside(p,ds['old_town']) and dry(p))
    if not route:raise ValueError('Cannot fit canal underpass')
    data['paths'].append(dict(id='PASS_CANAL_1',**{'class':'passage'},district_id='old_town',width_m=3.5,
        polyline_m=route,label_ru='Под мостом / берег',walkable=True,van_access=False,kind='under_bridge',
        grade_separated_road_ids=['ARC_AVENUE'],structure_road_id='ARC_AVENUE',
        vertical_relation='pedestrian bank below road bridge; no deck junction',
        headroom_target_m=2.8,purpose_ru='Один локальный проход по сухому берегу под существующим мостом; высота требует 3D-проверки.'))
    for p in data['paths']:
        p['length_m']=round(sum(m.length(a,b) for a,b in zip(p['polyline_m'],p['polyline_m'][1:])),2)


def analyse(data,m):
    checks=data['validation']['checks']
    def check(name,ok,detail=''):checks.append(dict(name=name,passed=bool(ok),detail=detail))
    old=json.loads((m.ROOT/'MAP_PLAN_R01_v04.json').read_text(encoding='utf-8'))
    check('v05 retains v04 geography and sizes',data['boundary']==old['boundary'] and data['water']==old['water']
        and all(d['polygon_m']==next(o['polygon_m'] for o in old['districts'] if o['id']==d['id']) for d in data['districts']))
    oldroads={r['id']:r for r in old['roads']}
    check('v04 vehicle roads retained except authorised P12 access',all(r==oldroads[r['id']] for r in data['roads'] if r['id']!='ACCESS_P12'))
    check('v04 route table unchanged',[(r['from_id'],r['to_id'],r['length_m']) for r in data['metrics']['routes']]
        ==[(r['from_id'],r['to_id'],r['length_m']) for r in old['metrics']['routes']])
    fs=data['functional_buildings'];ds={d['id']:d for d in data['districts']}
    check('functional schema, IDs and Russian labels',len({f['id'] for f in fs})==len(fs) and
        all(f['type'] and f['district']==f['district_id'] and f['storeys']>=1 and f['label_ru'] and f['color'] and f['icon'] for f in fs))
    required={
        'village':{'grandpa_house','pharmacy','village_shop','bus_stop','barn_yard','water_tower'},
        'transition':{'hut','shadow_buyer','gas_station','abandoned_farm'},
        'residential':{'garage_base','car_workshop','bar','den','shop_24h','small_market','closed_school','boiler_house','garage_rows','atm_pavilion'},
        'old_town':{'clock_tower','hospital','police_station','bank','supermarket','cafe','church','small_hotel','post_office','clothes_masks_shop','house_base'},
        'elite':{'mansion','prestige_base','private_security','boutique'},
        'industrial':{'industrial_complex','depot','industrial_chimney','warehouse','tow_yard','scrapyard'}}
    for dist,types in required.items():check('functional programme '+dist,types<={f['type'] for f in fs if f['district_id']==dist})
    check('all functional footprints within district',all(all(m.inside(p,ds[f['district_id']]['polygon_m']) for p in f['footprint_m']) for f in fs))
    collisions=[]
    for i,f in enumerate(fs):
        for g in fs[i+1:]:
            if overlaps(m,f['footprint_m'],g['footprint_m']):collisions.append((f['id'],g['id']))
        for b in data['building_masses']:
            if b['id']!=f.get('source_building_id') and overlaps(m,f['footprint_m'],b['polygon_m']):collisions.append((f['id'],b['id']))
    check('functional footprints do not overlap buildings',not collisions,str(collisions))
    roads=[]
    for f in fs:
        for r,a,b in segments(data):
            if r['id'].startswith('ACCESS_'):continue
            if m.inside(a,f['footprint_m']) or m.inside(b,f['footprint_m']) or any(m.crossing(a,b,c,d) for c,d in zip(f['footprint_m'],f['footprint_m'][1:]+f['footprint_m'][:1])):roads.append((f['id'],r['id']))
    check('functional footprints clear of through roads',not roads,str(roads))
    check('industrial P12 and separate service B03 P05 P12',next(p for p in data['points'] if p['id']=='P12')['district_id']=='industrial')
    check('all three P09 meeting sites retained',{s.get('poi_id') for s in data['functional_sites']} >= {'P09','P09-2','P09-3'})
    check('sparse passage programme: 3 yards, 2 alleys, 1 bank',Counter(p['kind'] for p in data['paths'])=={'yard_exit':3,'rear_alley':2,'under_bridge':1})
    check('passages pedestrian only and 3–4 m',all(p['class']=='passage' and 3<=p['width_m']<=4 and p['walkable'] and not p['van_access'] for p in data['paths']))
    path_hits=[]
    promoted={f.get('source_building_id') for f in fs}
    footprints=[b['polygon_m'] for b in data['building_masses'] if b['id'] not in promoted]+[f['footprint_m'] for f in fs]
    for p in data['paths']:
        for a,b in zip(p['polyline_m'],p['polyline_m'][1:]):
            for poly in footprints:
                if m.inside(a,poly) or m.inside(b,poly) or any(m.crossing(a,b,c,d) for c,d in zip(poly,poly[1:]+poly[:1])):path_hits.append(p['id'])
    check('passages do not cross building footprints',not path_hits,str(path_hits))
    pedestrian=copy.deepcopy(data)
    pedestrian['roads']+=copy.deepcopy(data['paths'])
    m.build_graph(pedestrian)
    data['pedestrian_graph']=pedestrian['road_graph']
    adj={n['id']:set() for n in pedestrian['road_graph']['nodes']}
    for e in pedestrian['road_graph']['edges']:
        adj[e['from_node']].add(e['to_node']);adj[e['to_node']].add(e['from_node'])
    seen=set();stack=[next(iter(adj))]
    while stack:
        n=stack.pop()
        if n not in seen:seen.add(n);stack.extend(adj[n]-seen)
    check('connected pedestrian graph and van exclusion',len(seen)==len(adj) and all(not e['van_access'] for e in pedestrian['road_graph']['edges'] if e['class']=='passage'),f'{len(seen)}/{len(adj)} nodes')
    canal=next(p for p in data['paths'] if p['kind']=='under_bridge')
    cross=[m.crossing(a,b,c,d) for a,b in zip(canal['polyline_m'],canal['polyline_m'][1:])
        for r,c,d in segments(data) if r['id']=='ARC_AVENUE']
    check('bank underpass crosses bridge road without deck junction',any(cross) and canal['grade_separated_road_ids']==['ARC_AVENUE'])
    bridge=next(s for s in data['water_crossings'] if s['road_id']=='ARC_AVENUE' and s['water_id']=='CANAL')
    span=m.length(*bridge['deck_axis_m'])
    margin=canal['width_m']/2/span
    check('underpass corridor lies inside existing bridge span',any(hit and m.projection(hit[0],*bridge['deck_axis_m'])[0]<8
        and margin<m.projection(hit[0],*bridge['deck_axis_m'])[2]<1-margin for hit in cross))
    check('passage length stays local and sparse',all(20<=p['length_m']<=190 for p in data['paths']) and sum(p['length_m'] for p in data['paths'])<=650)
    check('all earlier deliverables SHA256 unchanged',all(hashlib.sha256((m.ROOT/name).read_bytes()).hexdigest()==digest for name,digest in data['provenance']['previous_files_sha256'].items()))
    data['functional_statistics']=dict(building_count=len(fs),district_counts=dict(Counter(f['district_id'] for f in fs)),
        type_counts=dict(Counter(f['type'] for f in fs)),promoted_existing_count=sum('source_building_id' in f for f in fs),
        new_footprint_count=sum('source_building_id' not in f for f in fs))
    data['passage_statistics']=dict(count=len(data['paths']),total_length_m=round(sum(p['length_m'] for p in data['paths']),2),
        policy='sparse local walking alternatives; excluded from vehicle graph and all van timings')
    data['validation']['passed']=all(c['passed'] for c in checks)
    if not data['validation']['passed']:raise ValueError(json.dumps([c for c in checks if not c['passed']],ensure_ascii=False,indent=2))


def labelled_pois(data):
    # P09 is a meeting behind the supermarket, keep its separate meeting label.
    return {f['poi_id'] for f in data['functional_buildings'] if f.get('poi_id') and f['poi_id']!='P09'}


def draw_footprints(data,s,xy):
    for site in data['functional_sites']:
        if 'polygon_m' in site:
            s.poly([xy(p) for p in site['polygon_m']],'#bdbba9','#8d907b',.7,opacity='.65')
    for f in data['functional_buildings']:
        p=f['footprint_m'];center=f['center_m'];x,y=xy(center)
        s.poly([xy([q[0]+2,q[1]-2]) for q in p],'#3f5050',opacity='.20')
        s.poly([xy(q) for q in p],f['color'],'#485b5b',1.3)
        if f['type']=='garage_rows':
            for i in range(1,7):
                offset=-f['width_m']/2+i*f['width_m']/7
                s.line([xy([center[0]+offset,center[1]-f['depth_m']/2]),xy([center[0]+offset,center[1]+f['depth_m']/2])],'#f2ebdb',1)
        if f['type']=='small_market':
            for dx in (-12,0,12):s.rect(x+dx*.76-3,y+3,6,6,'#fff4d1',stroke='#8f7942',stroke_width=.5)
        if f['type']=='gas_station':
            s.rect(x+3,y-5,17,8,'#efe1bb',stroke='#577d84',stroke_width=1)
            for dx in (6,15):s.rect(x+dx,y-1,3,7,'#507e8d')
        if 'chimney_m' in f:
            a,b=xy(f['chimney_m']);s.circle(a,b,4,'#493f4f',stroke='#f4eddf',stroke_width=1)
        if f['type']=='abandoned_farm':
            s.line([xy(p[0]),xy(p[2])],'#665d49',1.6,stroke_dasharray='3 3')
        if f['type']=='hospital':
            s.rect(x-10,y-3,20,6,'#c1433a');s.rect(x-3,y-10,6,20,'#c1433a')
        elif f['type']=='clock_tower':
            s.circle(x,y,6,'#fff5d5',stroke='#665e66',stroke_width=1)
            s.line([[x,y-4],[x,y],[x+3,y+1]],'#665e66',1.2)
        elif f['type']=='church':
            s.line([[x-4,y],[x+4,y]],'#fff9e8',2);s.line([[x,y-6],[x,y+6]],'#fff9e8',2)
        else:
            s.circle(x,y,6.5,'#faf4e6',stroke=f['color'],stroke_width=1)
            s.text(x,y+4,f['icon'],size=11,color='#405958',weight='bold',anchor='middle')


def draw_passages(data,s,xy):
    for p in data['paths']:
        line=[xy(q) for q in p['polyline_m']]
        s.line(line,'#f6f3e9',p['width_m']*.76+2)
        s.line(line,'#567e67',p['width_m']*.76,stroke_dasharray='4 3')
        mid=line[len(line)//2]
        s.circle(mid[0],mid[1],7,'#567e67',stroke='#faf6e9',stroke_width=1)
        number=data['paths'].index(p)+1
        s.text(mid[0],mid[1]+4,str(number),size=11,color='white',anchor='middle',weight='bold')


def draw_labels(data,s,xy):
    used=[]
    def box(x,y,w,h):return [x,y-h,w,h]
    def hits(a,b):return a[0]<b[0]+b[2]+5 and b[0]<a[0]+a[2]+5 and a[1]<b[1]+b[3]+4 and b[1]<a[1]+a[3]+4
    # Reserve district headings, bridge/canal captions and retained POI labels.
    for p,w,h in [([390,790],270,55),([400,1720],250,55),([1070,2110],250,55),
        ([1760,2250],340,55),([1530,690],330,55),([1880,135],370,55),
        ([960,1600],270,55),([2020,800],230,55),([1920,550],350,55),([820,825],270,23)]:
        x,y=xy(p);used.append([x-w/2,y-24,w,h])
    for p in data['points']:
        if p['id'] in labelled_pois(data) or p['id'].startswith('BAD_BLOCK'):continue
        x,y=xy(p['position_m']);dx,dy=p['label_offset_px']
        label=p['id']+' '+p['name_ru']
        used.append(box(x+dx,y+dy,min(len(label)*7,230),18))
    for site in data['functional_sites']:
        if site.get('type')=='small_park':
            x,y=xy(site['position_m']);s.circle(x,y,17,'#9aaf81',opacity='.4')
    for f in sorted(data['functional_buildings'],key=lambda f:(not bool(f.get('poi_id')),f['district_id'],f['id'])):
        x,y=xy(f['center_m'])
        pid=f.get('poi_id')
        label=(pid+' ' if pid and pid not in ('CLOCK_SQUARE','WATER_TOWER','CHIMNEY','P09') else '')+f['label_ru']
        # The repeated non-accessible mansions still receive their own label.
        width=len(label)*7.6;choices=[]
        for distance in (20,36,52,72,96):
            for dx,dy in [(10,distance),(-width-10,distance),(10,-distance),(-width-10,-distance),(-width/2,distance),(-width/2,-distance)]:
                b=box(x+dx,y+dy,width,17)
                if b[0]<75 or b[0]+width>1890 or b[1]<215 or b[1]+17>2020:continue
                penalty=sum(hits(b,prior) for prior in used)*1000+distance+abs(dx)*.025
                choices.append((penalty,b,dx,dy))
        _,b,dx,dy=min(choices,key=lambda c:c[0])
        used.append(b)
        endx=x+dx+(width if dx<0 else 0);endy=y+dy-5
        s.line([[x,y],[endx,endy]],'#738174',.8)
        s.text(x+dx,y+dy,label,size=15,color='#3e514c',weight='bold',halo=True)


def draw_legend(data,s,scale):
    x=1955;y=250
    s.rect(1932,211,400,1888,'#efede2',rx=12)
    s.text(x,y,'КАК ЧИТАТЬ ПЛАН v05',size=20,weight='bold');y+=31
    for d in data['districts']:
        s.rect(x,y-12,15,15,d['color'],stroke='#8f9986',stroke_width=.6)
        names={'forest':'Лесные холмы','village':'Хутор и поля','transition':'Загородный переход',
            'residential':'Неблагополучный спальник','old_town':'Старый город','industrial':'Промышленная окраина',
            'elite':'Элитный холм (внутри города)','fields':'Новые поля','transition_meadow':'Городской луг перехода'}
        s.text(x+24,y,names[d['id']],size=15);s.text(2306,y,f'{d["share_percent"]:.1f}%',size=14,anchor='end',color='#7a887b');y+=23
    y+=17;s.line([[x,y],[2306,y]],'#c5c9bb',1);y+=28
    for id,c in data['road_classes'].items():
        s.line([[x,y-5],[x+40,y-5]],c['color'],4,**({'stroke_dasharray':'4 3'} if id=='passage' else {}))
        s.text(x+50,y,c['name_ru'],size=15);y+=25
    s.line([[x,y-5],[x+40,y-5]],'#747080',5,stroke_dasharray='2 7');s.text(x+50,y,'ЖД / мост / Т — тоннель канала',size=14);y+=31
    s.text(x,y,'ЦВЕТ И ЗНАК = ФУНКЦИЯ',size=18,weight='bold');y+=27
    for group,(color,icon,label) in PALETTE.items():
        s.rect(x,y-13,18,18,color,stroke='#536662',stroke_width=.7)
        s.text(x+9,y+1,icon,size=12,anchor='middle',weight='bold')
        s.text(x+28,y,label,size=14);y+=22
    y+=13;s.line([[x,y],[2306,y]],'#c5c9bb',1);y+=28
    s.text(x,y,'ЗДАНИЯ ПО РАЙОНАМ',size=18,weight='bold');y+=27
    registry=[
        ('Хутор — 6','Дед P02, аптека P03, сельмаг;|остановка, амбар, водобашня.'),
        ('Переход — 4','Хижина B02, приёмка P04;|АЗС у шоссе, руины фермы.'),
        ('Спальник — 11','Гараж B03, сервис P05, бар P06;|притон P07, 24 ч, рынок, школа;|котельная, 2 ряда боксов, ATM P11-2.'),
        ('Старый город — 12','Часы, больница P08, полиция P10;|банк и ATM, супермаркет, кафе;|церковь, отель, почта, одежда/маски;|дом B04. P09: парковка, сквер, канал.'),
        ('Элитный холм — 9','7 особняков, включая B06 и P15;|пост охраны, дорогой бутик.'),
        ('Промзона — 8','Комплекс B05, депо P14, труба;|3 склада, эвакуатор P12, металлолом.')]
    counts=data['functional_statistics']['district_counts']
    for i,(title,body) in enumerate(registry):
        dist=('village','transition','residential','old_town','elite','industrial')[i]
        title=title.split(' — ')[0]+f' — {counts[dist]}'
        s.text(x,y,title,size=15,weight='bold');y+=21
        for line in body.split('|'):s.text(x,y,line,size=14);y+=20
        y+=8
    y+=7;s.line([[x,y],[2306,y]],'#c5c9bb',1);y+=28
    s.text(x,y,'ВСЕГО 6 ПЕШИХ ПРОХОДОВ',size=18,weight='bold');y+=25
    for i,p in enumerate(data['paths'],1):
        s.text(x,y,f'{i}  {p["label_ru"]} — {p["length_m"]:.0f} м',size=14);y+=21
    s.text(x,y,f'Всего {data["passage_statistics"]["total_length_m"]:.0f} м; бусику недоступны.',size=14,weight='bold');y+=28
    # Keep the final scale independent of variable registry height.
    s.text(x,1940,'МАСШТАБ / МЕТРЫ',size=18,weight='bold')
    for i in range(4):s.rect(x+i*100*scale,1960,100*scale,10,'#577068' if i%2==0 else '#faf8ef',stroke='#81917d',stroke_width=1)
    for i in range(5):s.text(x+i*100*scale,1990,str(i*100),size=13,anchor='middle')
    s.text(x,2020,'Сетка 100 / 500 м • +Y = север ↑',size=14)
    s.text(x,2051,'Границы и просвет к трубе: 3D-проверка.',size=14)
    s.text(x,2075,'Пост → тупик; возврат через свой пост.',size=14)


def report(data):
    fs=data['functional_statistics'];ps=data['passage_statistics'];metrics=data['metrics']
    lines=['# VOLUNTEERS ONLY — R01 v05','',
        'Основание: req_map_plan_v05.md, решения Феди 04.10.2026. План — предложение, не реализация механик.',
        f'География v04 сохранена: {metrics["extent_m"][0]:.0f} × {metrics["extent_m"][1]:.0f} м; {metrics["area_m2"]/1e6:.3f} км². PNG/SVG 2400 × 2400.',
        'Контур, районы, вода, холмы, поля, усадьбы, дворы и основная дорожная сеть остаются как v04.',
        f'Функциональные здания: **{fs["building_count"]}**; {fs["promoted_existing_count"]} оформлены на прежних пятнах, {fs["new_footprint_count"]} новых пятен.',
        f'Заменены {len(data["replaced_generic_building_ids"])} обычных городских масс; 34 сельских дома, 78 многоквартирных домов и 7 особняков сохранены.',
        'Каждое здание имеет type, district, footprint_m, storeys, русский ярлык, цвет и значок. source_building_id исключает двойной счёт.','',
        '| Район | Функциональных зданий | Добавленные / оформленные функции |','|---|---:|---|']
    programme={
        'village':'Дед P02, аптека P03, сельмаг, остановка, амбарный двор, водобашня.',
        'transition':'Хижина B02, приёмка P04, АЗС у шоссе, заброшенная ферма.',
        'residential':'База B03, сервис P05, бар P06, притон P07, 24 ч, рынок, закрытая школа, котельная с трубой, 2 ряда боксов, ATM P11-2.',
        'old_town':'Часы, больница P08 с красным крестом, полиция P10, банк и ATM, супермаркет, кафе, церковь, отель, почта, одежда/маски, B04.',
        'elite':'7 особняков (B06 и доступные P15), охрана, дорогой бутик.',
        'industrial':'B05, депо P14, труба, 3 склада, стоянка P12, металлолом.'}
    names={d['id']:d['name_ru'] for d in data['districts']}
    for dist,desc in programme.items():lines.append(f'| {names[dist]} | {fs["district_counts"][dist]} | {desc} |')
    lines += ['',
        'P12 перенесена из старого города в промзону; изменён только её подъезд. Точки B03, P05 и P12 раздельны.',
        'P09 сохранены: парковка за супермаркетом, запасной сквер, запасное место у канала; открытые площадки не считаются зданиями.',
        f'Проходы: **{ps["count"]}**, ширина 3,5 м, общая длина **{ps["total_length_m"]:.2f} м**; 3 выхода из дворов, 2 задних переулка, 1 проход по берегу под мостом.',
        'Нового плотного пешего каркаса нет; задача проходов — редкий тихий перенос NPC со двора к бусику.',
        'paths и pedestrian_graph отделены от road_graph; van_access=false. Проход под мостом не соединён с проезжей частью.',
        'У прохода под мостом запас высоты 2,8 м — цель для макета, не доказанная высота на 2D-плане.','',
        '| Маршрут по автомобильным дорогам | м | 60 км/ч, с | 90 км/ч, с | Пешком по тем же дорогам, мин |','|---|---:|---:|---:|---:|']
    for r in metrics['routes']:
        lines.append(f'| {r["from_id"]} → {r["to_id"]} | {r["length_m"]:.0f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["walk_5_minutes"]:.1f} |')
    lines += ['',
        'Все строки автомобильной таблицы совпадают с v04. Время теоретическое: без разгона, трафика, поворотов и уклонов.',
        f'Автопроверки: **{sum(c["passed"] for c in data["validation"]["checks"])}/{len(data["validation"]["checks"])}**; география, районы, POI, расстояния, отдельные ветки B02/P04, тупики и ЖД.',
        'Проверены обязательные функции по районам, этажность и уникальность ID, пятна без наложений и без пересечений с транзитными дорогами.',
        'Проверены пешая связность, отсутствие пересечений проходов со зданиями, запрет проезда бусика и отсутствие соединения под мостом с его настилом.',
        'Легенда показывает районы, классы дорог, проходы, цвета/значки функций и полный районный перечень новых типов.',
        'v02–v04 сохранены побайтно; SHA-256 всех 12 прежних артефактов записаны в provenance JSON.',
        'Сборка: `python -B build_map_plan.py --revision v05`; `--reset-data` восстанавливает v05 из неизменной v04.',
        'Режимы v02/v03/v04 сохранены. Прежние ревизии проверяются без записи их файлов.',
        'Субъективное качество, физические границы, видимость трубы, высоты и перенос NPC требуют Unity-макета и плейтеста.']
    assert len(lines)<=60,len(lines)
    return '\n'.join(lines)+'\n'
