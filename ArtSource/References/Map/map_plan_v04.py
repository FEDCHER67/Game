"""Authored v04 proposal and validation; invoked by build_map_plan.py.

Only standard-library geometry. Earlier revision files are read, never written.
"""
import hashlib
import json
import math
import random
from collections import Counter


def clip(poly, a, b, c):
    """Keep a*x+b*y >= c; cuts here leave connected simple polygons."""
    out = []
    for u, v in zip(poly, poly[1:] + poly[:1]):
        du, dv = a*u[0]+b*u[1]-c, a*v[0]+b*v[1]-c
        if du >= 0:
            out.append(u)
        if (du >= 0) != (dv >= 0):
            out.append([u[k]+(v[k]-u[k])*du/(du-dv) for k in (0, 1)])
    return out


def seed(m):
    data = json.loads((m.ROOT/'MAP_PLAN_R01_v02.json').read_text(encoding='utf-8'))
    prior = {}
    for rev in ('v02', 'v03'):
        source = json.loads((m.ROOT/f'MAP_PLAN_R01_{rev}.json').read_text(encoding='utf-8'))
        prior[rev] = {d['id']: dict(area_m2=d['area_m2'], share_percent=d['share_percent'],
            building_count=sum(b['district_id'] == d['id'] for b in source['building_masses'])) for d in source['districts']}
    data.update(revision='v04', title_ru='VOLUNTEERS ONLY — план карты R01 (v04)', comparison=prior)
    data['provenance'] = dict(brief='req_map_plan_v04.md', owner_decisions_date='2026-10-04',
        source='MAP_PLAN_R01_v02.json', method='v02 geography; authored land transfers; sparse farmsteads; 78 apartment buildings',
        previous_files_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for rev in ('v02', 'v03') for p in sorted(m.ROOT.glob(f'MAP_PLAN_R01_{rev}*'))},
        specification_override='v04 brief supersedes v03 compaction and density; other map-spec requirements retained')
    for key in ('road_graph', 'metrics', 'validation', 'water_crossings'):
        data.pop(key, None)
    ds = {d['id']: d for d in data['districts']}
    original = ds['old_town']['polygon_m']
    # Move the shared industrial edge north; outer contour remains exact.
    industrial_edge = [[1590,100],[1480,420],[1730,550],[1980,510],[2180,310]]
    expanded_old = original[:12] + list(reversed(industrial_edge))[1:-1] + original[15:]
    ds['industrial']['polygon_m'] = industrial_edge + [[2040,120],[1790,70]]
    fields = clip(expanded_old, -1, 0, -1280)
    # V02's old-town edge crossed the outer contour beside [1090,150].
    # Clip the tiny forest spur to that contour and remove the field bow-tie.
    hit=m.crossing([1340,50],[1090,150],[1080,90],[1160,300])[0]
    loop_start=fields.index([1090,150])
    fields=fields[:loop_start]+[hit]+fields[loop_start+2:]
    forest=ds['forest']['polygon_m'];junction=forest.index([1080,90])
    ds['forest']['polygon_m']=forest[:junction]+[hit,[1090,150]]+forest[junction:]
    data['geometry_repairs']=[dict(source='v02 old-town/forest boundary self-intersection',
        intersection_m=hit,forest_area_trimmed_m2=round(prior['v02']['forest']['area_m2']-m.area(ds['forest']['polygon_m']),3),
        effect='outer contour unchanged; forest spur clipped; field polygon made simple')]
    remainder = clip(expanded_old, 1, 0, 1280)
    meadow = clip(remainder, -1, 1, 20)
    ds['old_town']['polygon_m'] = clip(remainder, 1, -1, -20)
    for id, name, poly, color, note in [
        ('fields', 'Новые поля у города', fields, '#dbd4ab', 'Освобождённая западная окраина города: поля, луга и сельские проезды.'),
        ('transition_meadow', 'Переход: городской луг', meadow, '#d6d8c0', 'Продолжение переходной среды у южного края спальника; отдельный участок.')]:
        data['districts'].append(dict(id=id, name_ru=name, polygon_m=poly, color=color, parent_id=None, notes_ru=note))
    ds = {d['id']: d for d in data['districts']}
    ds['village'].update(name_ru='Хутор и сельская среда', notes_ru='34 жилых дома; усадьбы по 2–4 постройки, поля, сады и рощи между группами.')
    ds['residential']['notes_ru'] = '78 многоквартирных домов: преимущественно 9/12 этажей, часть 16; три башни 20–22 этажа; дворы 60 × 44 м.'
    ds['old_town']['notes_ru'] = 'Площадь уменьшена примерно на 22%; часы, кривые улицы, два длинных проспекта и элитный холм сохранены.'
    data['planning_notes_ru'] = ['Размер карты и география v02 сохранены по брифу v04; сжатие v03 отменено.',
        'Новая геометрия — предложение планировки, а не утверждение новых игровых механик.',
        'Переходный городской луг учитывается отдельно: лес, сельская территория и спальник остаются в границах v02.',
        'Высоты, физические границы, обзор трубы и темп поездок требуют макета и плейтеста.']
    # Retain all urban geometry that still belongs to the smaller old town.
    data['building_masses'] = [b for b in data['building_masses'] if b['district_id'] not in ('village', 'residential')
        and (b['district_id'] != 'old_town' or all(m.inside(p, ds['old_town']['polygon_m']) for p in b['polygon_m']))]
    data['plots'] = [p for p in data['plots'] if p['kind'] == 'elite_garden']
    # The western premium block in v02 straddled the hill boundary by a corner.
    block=next(b for b in data['building_masses'] if b['id']=='BLD298')
    block['center_m']=[1935,1048]
    block['polygon_m']=m.rectangle(1935,1048,block['width_m'],block['depth_m'],-12)
    points = {p['id']: p for p in data['points']}
    points['P12']['position_m'] = [1330,490]
    next(r for r in data['roads'] if r['id']=='ACCESS_P12')['polyline_m'] = [[1360,380],[1330,490]]
    for p in data['points']:
        if p['district_id']=='old_town' and not m.inside(p['position_m'], ds['old_town']['polygon_m']):
            p['district_id'] = next(d['id'] for d in data['districts'] if not d['parent_id'] and m.inside(p['position_m'],d['polygon_m']))
    data['land_transfers'] = [dict(from_id='old_town', to_id=id, area_m2=round(m.area(ds[id]['polygon_m'])-(prior['v02'].get(id) or {}).get('area_m2',0)-(data['geometry_repairs'][0]['forest_area_trimmed_m2'] if id=='fields' else 0),2))
        for id in ('industrial','fields','transition_meadow')]
    hamlet(data, m)
    m.dense_residential(data)
    # Additional field strips occupy former urban land, clear of the rail route.
    for x,y,w,h in [(1205,600,80,130),(1190,790,100,110),(1205,1110,80,120),
                     (290,1590,120,160),(570,1640,120,130),(450,2040,130,130),(890,1430,110,90)]:
        poly=m.rectangle(x,y,w,h)
        if not any(m.inside(b['center_m'],poly) for b in data['building_masses']):
            data['field_parcels_m'].append(poly)
    return data


def hamlet(data, m):
    """34 homes: four beside the start, thirty across fifteen other farmsteads."""
    rng=random.Random(40417)
    village=next(d['polygon_m'] for d in data['districts'] if d['id']=='village')
    points={p['id']:p for p in data['points']}
    farms=[]; vegetation=[]
    data['farmsteads']=farms; data['vegetation_parcels']=vegetation
    def building(id, x,y,w,h,angle,kind,farm,poi=None):
        b=dict(id=id,district_id='village',kind=kind,floors=1,center_m=[x,y],width_m=w,depth_m=h,
               polygon_m=m.rectangle(x,y,w,h,angle),farmstead_id=farm)
        if poi: b['poi_id']=poi
        data['building_masses'].append(b)
        return id
    def road(id, line):
        data['roads'].append(dict(id=id,**{'class':'rural_road'},width_m=4,polyline_m=line))
    # Two compact start farmsteads: grandpa + one home + barn, pharmacy + two homes.
    starters=[('F04_01',[445,1330],[(452,1310,'rural_house','P02'),(432,1352,'rural_house',None),(412,1320,'rural_outbuilding',None)], [490,1250]),
              ('F04_02',[598,1270],[(570,1260,'pharmacy','P03'),(598,1250,'rural_house',None),(613,1284,'rural_house',None)], [530,1290])]
    for fid,center,items,attach in starters:
        ids=[]
        for j,(x,y,kind,poi) in enumerate(items):
            bid=f'{fid}_{j+1}'
            ids.append(building(bid,x,y,18 if kind!='pharmacy' else 22,12,0,kind,fid,poi))
            if poi:
                points[poi]['position_m']=[x,y]
                next(r for r in data['roads'] if r['id']=='ACCESS_'+poi)['polyline_m']=[attach,[x,y]]
            else:
                road('ACCESS_'+bid,[attach,[x,y]])
        yard=m.rectangle(*center,98,80)
        farms.append(dict(id=fid,center_m=center,building_ids=ids,yard_polygon_m=yard,start_cluster=True))
        data['plots'].append(dict(id=fid,polygon_m=yard,kind='farmstead_yard'))
    # Road-tangent placement leaves large empty intervals between compact groups.
    segments=[(a,b,r['width_m']/2) for r in data['roads'] for a,b in zip(r['polyline_m'],r['polyline_m'][1:])]
    rural=[(a,b) for r in data['roads'] if r['id'].startswith(('V_','ARC_RURAL')) for a,b in zip(r['polyline_m'],r['polyline_m'][1:])]
    water=[(a,b,w['width_m']/2+8) for w in data['water'] if 'centerline_m' in w for a,b in zip(w['centerline_m'],w['centerline_m'][1:])]
    for attempt in range(18000):
        if len(farms)==17: break
        x,y=rng.uniform(220,970),rng.uniform(1420,2230)
        if not m.inside([x,y],village): continue
        a,b=min(rural,key=lambda ab:m.projection([x,y],*ab)[0])
        distance,entry,_=m.projection([x,y],a,b)
        if not 55<distance<155: continue
        angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
        ca,sa=math.cos(math.radians(angle)),math.sin(math.radians(angle))
        if (x-entry[0])*(-sa)+(y-entry[1])*ca<0:
            angle+=180;ca=-ca;sa=-sa
        def at(dx,dy):return [round(x+dx*ca-dy*sa,3),round(y+dx*sa+dy*ca,3)]
        yard=m.rectangle(x,y,88,78,angle)
        if not all(m.inside(p,village) for p in yard): continue
        if any(m.length([x,y],f['center_m'])<140 for f in farms): continue
        if any(m.inside(p,yard) for p in [p['position_m'] for p in data['points']]): continue
        if any(m.projection(p,a,b)[0]<w+6 for p in yard+[[x,y]] for a,b,w in segments+water): continue
        if any(m.inside(a,yard) or any(m.crossing(a,b,c,d) for c,d in zip(yard,yard[1:]+yard[:1])) for a,b,w in segments+water): continue
        if any(m.inside(p,w['polygon_m']) for p in yard for w in data['water'] if 'polygon_m' in w): continue
        fid=f'F04_{len(farms)+1:02d}';ids=[]
        for j,(dx,dy,kind) in enumerate([(-30,5,'rural_house'),(30,5,'rural_house'),(30,32,'rural_outbuilding')]):
            bx,by=at(dx,dy)
            ids.append(building(f'{fid}_{j+1}',bx,by,18,12,angle,kind,fid))
        road('LANE_'+fid,[entry,at(0,-25),at(0,10)])
        farms.append(dict(id=fid,center_m=[x,y],building_ids=ids,yard_polygon_m=yard,start_cluster=False))
        data['plots'].append(dict(id=fid,polygon_m=yard,kind='farmstead_yard'))
        vegetation.append(dict(id='ORCHARD_'+fid,kind='orchard',polygon_m=m.rectangle(*at(-28,32),26,22,angle)))
    assert len(farms)==17, f'Only {len(farms)} farmsteads fit'
    # Small groves punctuate the open land between clusters; no forest expansion.
    grove_centers=[]
    candidates=[(330,1470),(575,1570),(595,1850),(830,2030),(710,2180),(800,1300)]
    candidates += [(rng.uniform(230,940),rng.uniform(1320,2210)) for _ in range(600)]
    for x,y in candidates:
        if len(grove_centers)==6:break
        poly=m.rectangle(x,y,60,48,16)
        if (all(m.inside(p,village) for p in poly) and all(m.length([x,y],f['center_m'])>95 for f in farms)
            and all(m.length([x,y],p)>130 for p in grove_centers)
            and all(m.projection([x,y],a,b)[0]>w+45 for a,b,w in segments+water)):
            vegetation.append(dict(id=f'GROVE_{len(vegetation)}',kind='grove',polygon_m=poly))
            grove_centers.append([x,y])
    assert len(grove_centers)>=3


def validate(data, m, check):
    prior=data['comparison'];ds={d['id']:d for d in data['districts']}
    original=json.loads((m.ROOT/'MAP_PLAN_R01_v02.json').read_text(encoding='utf-8'))
    old_ds={d['id']:d for d in original['districts']}
    check('v02 outer geography retained', data['boundary']==original['boundary'] and data['water']==original['water'])
    for id in ('village','residential'):
        check(id+' territory identical to v02',ds[id]['polygon_m']==old_ds[id]['polygon_m'])
    check('v02 forest retained except repaired boundary sliver',0<=prior['v02']['forest']['area_m2']-ds['forest']['area_m2']<500)
    self_crossings=[]
    for zone in data['districts']:
        poly=zone['polygon_m'];n=len(poly)
        for i in range(n):
            for j in range(i+2,n):
                if i==0 and j==n-1:continue
                hit=m.crossing(poly[i],poly[(i+1)%n],poly[j],poly[(j+1)%n])
                if hit and 1e-7<hit[1]<1-1e-7 and 1e-7<hit[2]<1-1e-7:self_crossings.append((zone['id'],i,j))
    check('district polygons have no self-crossings',not self_crossings,str(self_crossings))
    reduction=1-ds['old_town']['area_m2']/prior['v02']['old_town']['area_m2']
    check('old town area reduced 20–25%',.20<=reduction<=.25,f'{reduction:.2%}')
    check('freed land assigned to fields, industry and transition',all(t['area_m2']>0 for t in data['land_transfers']) and
          abs(sum(t['area_m2'] for t in data['land_transfers'])-(prior['v02']['old_town']['area_m2']-ds['old_town']['area_m2']))<1)
    res=[b for b in data['building_masses'] if b['district_id']=='residential']
    homes=[b for b in data['building_masses'] if b['kind']=='rural_house']
    check('hamlet approximately half v02 homes',.45<=len(homes)/prior['v02']['village']['building_count']<=.55,f'{len(homes)} / {prior["v02"]["village"]["building_count"]}')
    check('farmsteads of 2–4 buildings',all(2<=len(f['building_ids'])<=4 for f in data['farmsteads']))
    pts={p['id']:p for p in data['points']}
    start_ids={bid for f in data['farmsteads'] if f['start_cluster'] for bid in f['building_ids']}
    start_homes=[b for b in homes if b['id'] in start_ids and not b.get('poi_id')]
    distances={b['id']:round(m.shortest(data,pts['B01']['road_node_id'],min(data['road_graph']['nodes'],key=lambda n:m.length(n['position_m'],b['center_m']))['id'])[0],2) for b in start_homes}
    check('three additional starter homes within 400 m by graph',len(distances)==3 and all(d<=400 for d in distances.values()),str(distances))
    data['start_cluster_home_routes_m']=distances
    # Removing each authored branch junction must isolate just its own service.
    branch_checks=[]
    for road_id,own,other in [('HUT_BRANCH','B02','P04'),('RECEPTION_BRANCH','P04','B02')]:
        junction=next(r['polyline_m'][0] for r in data['roads'] if r['id']==road_id)
        node=min(data['road_graph']['nodes'],key=lambda n:m.length(n['position_m'],junction))['id']
        isolated=m.shortest(data,pts[own]['road_node_id'],pts['B01']['road_node_id'],blocked=node)[0]
        other_route=m.shortest(data,pts[other]['road_node_id'],pts['B01']['road_node_id'],blocked=node)[0]
        branch_checks.append(math.isinf(isolated) and math.isfinite(other_route))
    check('B02 and P04 topologically separate branches',all(branch_checks))
    check('farmstead lanes, orchards and groves', all(any(r['id']=='LANE_'+f['id'] for r in data['roads']) for f in data['farmsteads'] if not f['start_cluster']) and all(any(v['kind']==k for v in data['vegetation_parcels']) for k in ('orchard','grove')))
    check('75–80 apartment buildings',75<=len(res)<=80,str(len(res)))
    floors=Counter(b['floors'] for b in res)
    check('mostly 9/12 floors, some 16, at most three 20+ towers',floors[9]+floors[12]>.65*len(res) and floors[16]>0 and 0<sum(n for f,n in floors.items() if f>=20)<=3,str(dict(sorted(floors.items()))))
    check('larger courtyards than v03',len(data['microdistricts'])>=8 and all(2000<=m.area(c['yard_polygon_m'])<=3500 for c in data['microdistricts']),f'{len(data["microdistricts"])} courts, 60 × 44 m')
    check('all building IDs unique',len({b['id'] for b in data['building_masses']})==len(data['building_masses']))
    check('all building footprints in district',all(all(m.inside(p,ds[b['district_id']]['polygon_m']) for p in b['polygon_m']) for b in data['building_masses']))
    overlaps=[]
    buildings=data['building_masses']
    for i,b in enumerate(buildings):
        for c in buildings[i+1:]:
            if m.length(b['center_m'],c['center_m'])>max(b['width_m'],b['depth_m'])+max(c['width_m'],c['depth_m']):continue
            p,q=b['polygon_m'],c['polygon_m']
            if any(m.inside(a,q) for a in p) or any(m.inside(a,p) for a in q) or any(m.crossing(a,z,u,v) for a,z in zip(p,p[1:]+p[:1]) for u,v in zip(q,q[1:]+q[:1])):
                overlaps.append([b['id'],c['id']])
    check('all building footprints do not overlap',not overlaps,str(overlaps))
    check('earlier deliverables unchanged',all(hashlib.sha256((m.ROOT/name).read_bytes()).hexdigest()==digest for name,digest in data['provenance']['previous_files_sha256'].items()))
    data['residential_statistics']=dict(building_count=len(res),floor_counts=dict(sorted(floors.items())),footprint_coverage_percent=round(sum(m.area(b['polygon_m']) for b in res)/ds['residential']['area_m2']*100,2))
    data['hamlet_statistics']=dict(home_count=len(homes),farmstead_count=len(data['farmsteads']),outbuilding_count=sum(b['kind']=='rural_outbuilding' for b in buildings))


def report(data):
    m=data['metrics']; prior=data['comparison']; stats=data['residential_statistics'];hs=data['hamlet_statistics']
    lines=['# VOLUNTEERS ONLY — R01 v04','',
        'Основание: req_map_plan_v04.md, решения Феди 04.10.2026; бриф отменяет сжатие v03. Геометрия — предложение.',
        f'Контур **{m["extent_m"][0]:.0f} × {m["extent_m"][1]:.0f} м**, площадь **{m["area_m2"]/1e6:.3f} км²** — как v02; v03: 1988 × 1993 м / 3,335 км².',
        'Рамка 2400 × 2400 м; X — восток, Y — север; PNG/SVG 2400 × 2400 пикселей.','',
        '| Территория | v02 км² / % | v03 км² / % | v04 км² / % | Постройки v02 / v03 / v04 |','|---|---:|---:|---:|---:|']
    for d in data['districts']:
        old=[prior[r].get(d['id'],dict(area_m2=0,share_percent=0,building_count=0)) for r in ('v02','v03')]
        n=sum(b['district_id']==d['id'] for b in data['building_masses'])
        cols=[f'{p["area_m2"]/1e6:.3f} / {p["share_percent"]:.1f}%' for p in old]
        lines.append(f'| {d["name_ru"]}{" (вложена)" if d["parent_id"] else ""} | {cols[0]} | {cols[1]} | {d["area_m2"]/1e6:.3f} / {d["share_percent"]:.1f}% | {old[0]["building_count"]} / {old[1]["building_count"]} / {n} |')
    ds={d['id']:d for d in data['districts']}
    lines+=['','Элитка входит в старый город по площади; её постройки показаны отдельно, без двойного счёта.',
        f'Исправлен унаследованный самоперехлёст v02: лес обрезан по неизменному внешнему контуру на {data["geometry_repairs"][0]["forest_area_trimmed_m2"]:.0f} м²; остальная география леса сохранена.',
        f'Старый город: −{(1-ds["old_town"]["area_m2"]/prior["v02"]["old_town"]["area_m2"])*100:.1f}% к v02; освобождённое место передано новым полям, промзоне и городскому лугу перехода.',
        f'Хутор: {hs["home_count"]} жилых дома вместо 69; {hs["farmstead_count"]} усадеб по 3 постройки, {hs["outbuilding_count"]} хозпостроек и аптека. У старта дед + 3 жилых дома, аптека и объявление.',
        'Усадьбы связаны сельскими улицами и отдельными подъездами; между группами поля, сады и малые рощи.',
        f'Спальник: {stats["building_count"]} домов (v02: 36; v03: 122); этажи / домов: '+', '.join(f'{k}/{v}' for k,v in stats['floor_counts'].items())+'.',
        f'Покрытие спальника пятнами зданий {stats["footprint_coverage_percent"]:.1f}%; дворы {len(data["microdistricts"])} × 60 × 44 м против 36 × 28 м в v03; зазоры от 8 м.','',
        '| Кратчайший маршрут по дорогам | м | 60 км/ч, с | 90 км/ч, с | Пешком 5 км/ч, мин |','|---|---:|---:|---:|---:|']
    names={p['id']:p['id']+' '+p['name_ru'] for p in data['points']}
    for r in m['routes']:
        lines.append(f'| {names[r["from_id"]]} → {names[r["to_id"]]} | {r["length_m"]:.0f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["walk_5_minutes"]:.1f} |')
    lines+=['','Время теоретическое при постоянной скорости; разгон, повороты, трафик и уклоны не учтены. Это не игровой замер.','',
        '| Проверка | Результат |','|---|---|',
        '| Старт ≤ 400 м; B01/B02 → центр спальника ≥ 1200 м | Пройдено по графу, включая срезки. |',
        '| География | Контур, хутор, спальник и вода как v02; лес с указанной выше малой коррекцией границы. |',
        '| B02 / P04 | Две отдельные тупиковые ветки перехода. |',
        '| Старый город | Часы, кривые улицы, два широких проспекта, P08/P09/P10, B04/B06; 7 особняков + 2 корпуса. |',
        '| Промзона и ЖД | B05 и депо P14; непрерывная ветка от B01 с проездом рядом. |',
        '| §14, вариант А | Три поста, видимые тупики и фланги из леса/холмов; возврат по графу только через свой пост. |',
        f'| Автопроверки | {sum(c["passed"] for c in data["validation"]["checks"])}/{len(data["validation"]["checks"])}: площади, связность, расстояния, постройки, вода, ЖД, сохранность v02/v03. |','',
        f'Граф: {len(data["road_graph"]["nodes"])} узлов, {len(data["road_graph"]["edges"])} рёбер; независимых петель {m["cycle_rank"]}.',
        'Физическая непроходимость границ, видимость трубы, уклоны, перенос NPC и удобство езды требуют Unity-макета и плейтеста.',
        'Сборка: `python build_map_plan.py --revision v04`; `--reset-data` восстанавливает предложение. JSON сохраняет ручные правки.',
        'Режимы `--revision v02` и `--revision v03` сохранены; прежние файлы в этой задаче не перезаписаны (SHA-256 в JSON).']
    assert len(lines)<=60,len(lines)
    return '\n'.join(lines)+'\n'
