#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Targeted v08 edits; run with Python -B. Writes only numbered v08 outputs."""
import copy
import hashlib
import json
import math
import os
import struct
import subprocess
import xml.etree.ElementTree as ET
import map_plan_v07 as v7

m=v7.m
ROOT=m.ROOT
STEM='MAP_PLAN_R01_v08'


def hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.iterdir())
        if p.is_file() and not p.name.startswith((STEM,'map_plan_v08'))}


def seed():
    d=json.loads((ROOT/'MAP_PLAN_R01_v07.json').read_text(encoding='utf-8'))
    d.update(revision='v08',title_ru='VOLUNTEERS ONLY — план карты R01 / v08')
    d['specification']['brief_override']='req_map_plan_v08.md, targeted review, 2026-10-04'
    d['provenance']=dict(brief='req_map_plan_v08.md',source_schema='MAP_PLAN_R01_v07.json',
        owner_decisions_date='2026-10-04',method='targeted v07 edits; unchanged geometry retained',previous_files_sha256=hashes())
    d['comparison']={'v07':{'extent_m':d['metrics']['extent_m']},'policy':'targeted edits; no uniform scaling'}
    d['planning_notes_ru']=[
        'B06 — единственная престижная и финальная база: существующая вилла у озера; B07 удалён.',
        'Старое здание B06 на холме удалено; в прежнем саду размещён обычный особняк. Всего четыре особняка, два доступны P15.',
        'Дворы 1–2 сохранены и открыты на юг; двор 3 между ними, на 25 м ниже, открыт на север. Узкие проходы огибают сцепленные корпуса.',
        'Бар, 24 ч и киоски размещены нерегулярно вдоль улиц; притон скрыт за дворами 1–2.',
        'Пост P16-2 и тупик сдвинуты на запад на 110 м; северо-восточный пустой угол района и карты вырезан.',
        'Времена расчётные; субъективное принятие и физические барьеры требуют Unity-плейтеста.']
    fs={f['id']:f for f in d['functional_buildings']}
    old=fs['F06_MANSION_1']
    mansion=copy.deepcopy(old)
    color,icon,_=v7.v5.PALETTE['lodging']
    mansion.update(id='F08_MANSION_1',type='mansion',label_ru='Особняк 1',group='lodging',color=color,icon=icon,
        center_m=[819,577],width_m=18,footprint_m=m.rectangle(819,577,18,14),entrance_m=[832,577])
    mansion.pop('poi_id')
    d['functional_buildings']=[mansion if f['id']==old['id'] else f for f in d['functional_buildings']]
    villa=fs['F07_VILLA']
    villa.update(type='prestige_base',poi_id='B06',label_ru='Престижная база — вилла у озера')
    d['points']=[p for p in d['points'] if p['id']!='B06']
    point=next(p for p in d['points'] if p['id']=='B07')
    point.update(id='B06',canonical_id='B06',name_ru=villa['label_ru'])
    roads={r['id']:r for r in d['roads']}
    roads['ACCESS_B06'].update(id='ACCESS_F08_MANSION_1',polyline_m=[[850,577],[832,577]])
    roads['ACCESS_B07']['id']='ACCESS_B06'
    court=d['microdistricts'][2]
    delta=[592.5-court['center_m'][0],700-court['center_m'][1]]
    for b in d['building_masses']:
        if b['id'] in court['building_ids']:
            b['center_m']=[b['center_m'][k]+delta[k] for k in (0,1)]
            b['polygon_m']=[[p[k]+delta[k] for k in (0,1)] for p in b['polygon_m']]
    court.update(center_m=[592.5,700],yard_polygon_m=m.rectangle(592.5,704,62,64))
    roads['R_COURTS']['polyline_m']=[[500,675],[535,675],[540,650]]
    roads['COURT_ACCESS_3']['polyline_m']=[[592.5,780],[592.5,675]]
    def road(id,poly):
        d['roads'].append(dict(id=id,polyline_m=poly,width_m=6,**{'class':'town_street'},district_ids=['residential']))
    road('R_COURTS_EAST',[[650,675],[820,675]])
    road('R_REAR',[[710,675],[710,780],[535,780]])
    road('EXIT_APPROACH_NE',[[710,780],[710,790]])
    road('ACCESS_P13-4',[[592.5,675],[606,675]])
    # Move complete checkpoint geometry; keep garage rows and the boiler house fixed.
    ex=next(e for e in d['exits'] if e['id']=='NE')
    ex['dead_end_m']=[ex['dead_end_m'][0]-110,ex['dead_end_m'][1]]
    ex['barrier_polygons_m']=[[[x-110,y] for x,y in p] for p in ex['barrier_polygons_m']]
    ex['post_trigger_polygon_m']=[[x-110,y] for x,y in ex['post_trigger_polygon_m']]
    roads['EXIT_NE']['polyline_m']=[[x-110,y] for x,y in roads['EXIT_NE']['polyline_m']]
    poly=[[470,620],[870,620],[870,780],[830,780],[830,825],[470,825]]
    next(q for q in d['districts'] if q['id']=='residential')['polygon_m']=poly
    bp=d['boundary']['polygon_m'];i=bp.index([870,620]);bp[i+1:i+2]=[[870,780],[830,780],[830,825]]
    pts={p['id']:p for p in d['points']}
    pts['P16-2']['position_m']=[710,790]
    pts['BAD_BLOCK_3']['position_m']=[592.5,720]
    # Only affected small functions receive new entrances; everything else stays fixed.
    placements={'F06_BAR':([752,644],17,'R_COURTS_EAST',[752,675]),
        'F06_24':([685,634],-8,'R_COURTS_EAST',[685,675]),
        'F06_K1':([526,631],11,'ARC_AVENUE',[526,650]),
        'F06_K2':([560,637],-23,'ARC_AVENUE',[560,650]),
        'F06_K3':([701,693],31,'R_REAR',[710,693]),
        'F06_DEN':([595,801],-11,'R_REAR',[595,780])}
    for id,(center,angle,rid,start) in placements.items():
        f=fs[id];f.update(center_m=center,footprint_m=m.rectangle(*center,f['width_m'],f['depth_m'],angle))
        hits=[hit[0] for a,b in v7.edges(f['footprint_m']) if (hit:=m.crossing(center,start,a,b))]
        door=min(hits,key=lambda p:m.length(p,start))
        n=m.length(door,start)
        door=[round(door[k]+(start[k]-door[k])/n*4,3) for k in (0,1)]
        f.update(entrance_m=door,access_road_id=rid)
        pid=f.get('poi_id');access='ACCESS_'+(pid or id)
        roads[access]['polyline_m']=[start,door]
        if pid:pts[pid]['position_m']=door
    # Shop ATM uses the same frontage, away from the footprint and main carriageway.
    pts['P11-2']['position_m']=[703,637]
    roads['ACCESS_P11-2']['polyline_m']=[[703,675],[703,637]]
    for p in d['paths']:
        if p['id']=='PASS06_BAD_1':
            p.update(polyline_m=[[535,705],[540,705],[540,744],[563,744],[563,680],[592.5,680],[592.5,720]],
                label_ru='Двор 1 ↔ двор 3',kind='yard_link')
        elif p['id']=='PASS06_BAD_2':
            p.update(polyline_m=[[650,705],[645,705],[645,744],[623,744],[623,680],[592.5,680],[592.5,720]],
                label_ru='Двор 2 ↔ двор 3',kind='yard_link')
        elif p['id']=='PASS06_BAD_3':
            p.update(polyline_m=[[592.5,720],[600,720],[600,780]],label_ru='Задний выход из двора 3')
        p['length_m']=round(sum(m.length(a,b) for a,b in zip(p['polyline_m'],p['polyline_m'][1:])),3)
    return d


def validate_targeted(d,check):
    old=json.loads((ROOT/'MAP_PLAN_R01_v07.json').read_text(encoding='utf-8'))
    check('exact v07 top-level schema and container types',set(d)==set(old) and all(type(d[k])==type(v) for k,v in old.items()))
    check('first two courtyards and slabs unchanged',d['microdistricts'][:2]==old['microdistricts'][:2] and
        [b for b in d['building_masses'] if b['id'].startswith(('R06_C1_','R06_C2_'))]==
        [b for b in old['building_masses'] if b['id'].startswith(('R06_C1_','R06_C2_'))])
    c=d['microdistricts'][2];cs=d['microdistricts'][:2]
    check('third courtyard interlocks between upper south-facing courts',c['center_m']==[592.5,700] and
        c['opening_direction']=='north' and all(q['opening_direction']=='south' for q in cs) and
        all(m.inside([c['center_m'][0]+dx,725],q['yard_polygon_m']) for dx,q in zip((-40,40),cs)))
    villa=next(f for f in d['functional_buildings'] if f.get('poi_id')=='B06')
    check('one canonical B06 prestige and final lakeside base; no B07',villa['id']=='F07_VILLA' and
        villa['type']=='prestige_base' and villa['district_id']=='fields' and villa['van_garage'] and villa['storeys']==2 and
        next(p for p in d['points'] if p['id']=='B06')['canonical_id']=='B06' and
        not any(p['id']=='B07' or p['canonical_id']=='B07' for p in d['points']) and
        not any(f['id']=='F06_MANSION_1' or (f.get('poi_id')=='B06' and f['district_id']=='elite') for f in d['functional_buildings']))
    previous=next(f for f in old['functional_buildings'] if f['id']=='F07_VILLA')
    check('villa geometry and private drive retained',all(villa[k]==previous[k] for k in previous if k not in ('type','poi_id','label_ru')) and
        next(r for r in d['roads'] if r['id']=='ACCESS_B06')['polyline_m']==next(r for r in old['roads'] if r['id']=='ACCESS_B07')['polyline_m'])
    den=next(f for f in d['functional_buildings'] if f.get('poi_id')=='P07')
    check('den behind both upper courtyards',min(p[1] for p in den['footprint_m'])>771)
    original=next(q for q in old['districts'] if q['id']=='residential')
    current=next(q for q in d['districts'] if q['id']=='residential')
    check('district and outer boundary shrink by same 1800 square metres',abs(original['area_m2']-current['area_m2']-1800)<.01 and
        abs(old['metrics']['area_m2']-d['metrics']['area_m2']-1800)<.01)
    for dist in ('forest','village','transition','old_town','industrial'):
        for key in ('building_masses','functional_buildings','points','plots','paths'):
            items=lambda x:[{k:v for k,v in q.items() if k!='road_node_id'} for q in x[key] if q.get('district_id')==dist]
            check(dist+' '+key+' unchanged',items(d)==items(old))
    check('water railway fields hills and farmsteads unchanged',all(d[k]==old[k] for k in ('water','railway','field_parcels_m','hills','farmsteads')))
    check('all road centre lines inside boundary',all(m.inside(p,d['boundary']['polygon_m']) for r in d['roads'] for p in r['polyline_m']))
    check('NE flank barriers inside reduced boundary',all(m.inside(p,d['boundary']['polygon_m']) for e in d['exits'] if e['id']=='NE' for poly in e['barrier_polygons_m'] for p in poly))
    shifted=next(e for e in d['exits'] if e['id']=='NE')
    original_exit=next(e for e in old['exits'] if e['id']=='NE')
    check('NE post dead end and complete flank geometry translated west by 110 m',
        next(p for p in d['points'] if p['id']=='P16-2')['position_m']==[710,790] and
        shifted['dead_end_m']==[original_exit['dead_end_m'][0]-110,original_exit['dead_end_m'][1]] and
        shifted['barrier_polygons_m']==[[[x-110,y] for x,y in poly] for poly in original_exit['barrier_polygons_m']])
    affected={'F06_MANSION_1','F06_BAR','F06_24','F06_K1','F06_K2','F06_K3','F06_DEN','F07_VILLA'}
    check('all other functional buildings and all plots sites vegetation retained',
        [f for f in d['functional_buildings'] if f['id'] not in affected|{'F08_MANSION_1'}]==
        [f for f in old['functional_buildings'] if f['id'] not in affected] and
        all(d[k]==old[k] for k in ('plots','functional_sites','vegetation_parcels')))
    check('only courtyard 3 building masses changed',
        [b for b in d['building_masses'] if b['id'] not in c['building_ids']]==
        [b for b in old['building_masses'] if b['id'] not in c['building_ids']])
    small=[f for f in d['functional_buildings'] if f['type'] in ('bar','shop_24h','kiosk')]
    angles=[round(math.degrees(math.atan2(
        f['footprint_m'][1][1]-f['footprint_m'][0][1],f['footprint_m'][1][0]-f['footprint_m'][0][0])),1) for f in small]
    kiosks=sorted((f for f in small if f['type']=='kiosk'),key=lambda f:f['id'])
    check('five small street buildings have distinct orientations and no regular kiosk spacing',
        len(small)==5 and len(set(angles))==5 and
        abs(m.length(kiosks[0]['center_m'],kiosks[1]['center_m'])-
            m.length(kiosks[1]['center_m'],kiosks[2]['center_m']))>1)


def report(d):
    old=json.loads((ROOT/'MAP_PLAN_R01_v07.json').read_text(encoding='utf-8'))
    lines=['# VOLUNTEERS ONLY — R01 v08','',
        'Основание: req_map_plan_v08.md; только целевые правки v07, 04.10.2026.',
        f'Карта: 815 × 685 м; площадь {d["metrics"]["area_m2"]:.0f} м² (v07: {old["metrics"]["area_m2"]:.0f}); {d["metrics"]["building_count"]} физических зданий; SVG/PNG 2400 × 2400.',
        'B06 «Престижная база — вилла у озера» — единственная престижная и финальная база; B07 удалён. Геометрия виллы, гараж, терраса и подъезд сохранены.',
        'Старое здание B06 на холме удалено; обычный особняк 1 размещён в прежнем саду со смещением на 2 м. Всего 4 особняка, 2 доступны P15; охрана и бутик сохранены.',
        'Дворы 1–2 сохранены: центры (535,725), (650,725), открыты вниз. Двор 3: (592,5;700), на 25 м ниже, открыт вверх.',
        'Боковые корпуса двора 3 направлены внутрь дворов 1–2; узкие проходы 2,5 м связывают соседние дворы, огибая сцепленные корпуса.',
        'Бар, магазин 24 ч и 3 киоска имеют разные углы, интервалы и положения вдоль улиц. ATM перенесён вместе с магазином.',
        'P07 скрыт за задними корпусами дворов 1–2, у тыльного подъезда; основная дорога остаётся на юге.',
        'P16-2 и разрушенный мост / тупик сдвинуты на 110 м на запад. Пустой северо-восточный угол срезан: район и карта уменьшены на 1800 м².',
        'Ряды гаражей, котельная, старый город, хутор, переход, промзона, вода и ЖД сохранены; улицы дворов адаптированы к новой геометрии.','',
        '| Маршрут | Дорога, м | 60 км/ч, с | 90 км/ч, с | Пешком 5 км/ч, мин |',
        '|---|---:|---:|---:|---:|']
    for r in d['metrics']['routes']:
        lines.append(f'| {r["from_id"]} → {r["to_id"]} | {r["length_m"]:.1f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["walk_5_minutes"]:.2f} |')
    lines += ['',f'Проверки: {sum(c["passed"] for c in d["validation"]["checks"])}/{len(d["validation"]["checks"])}; подробности в JSON.',
        'Повторены дистанционные проверки, связность обоих графов, единственные межрайонные въезды и возврат через каждый пост.',
        'Здания и проходы проверены на пересечения с дорогами, водой и ЖД; схема JSON v07 сохранена. Предыдущие файлы проверены SHA-256.',
        'Сборка: python -B map_plan_v08.py. Git и WORK_SYNC.md не изменялись; все новые файлы только в папке Map.',
        'Времена теоретические, без разгона, поворотов, трафика и уклонов; нужен Unity-плейтест. PNG просмотрен после сборки.']
    assert len(lines)<=40
    return '\n'.join(lines)+'\n'


def main():
    before=hashes();d=seed()
    # Retain v07's established geometry/graph checks and renderer, adapting only
    # revision-specific assumptions. No prior module or deliverable is edited.
    source=(ROOT/'map_plan_v07.py').read_text(encoding='utf-8')
    start=source.index('def analyse(data):');end=source.index('\ndef validate_targeted',start)
    analysis=source[start:end].replace("('B01','B07')","('B01','B06')")
    analysis=analysis.replace("physical count matches v06 removals plus B07 and P01 pole","physical count retained from v07")
    analysis=analysis.replace("mansions=[f for f in fs if f['type'] in ('mansion','prestige_base')]",
        "mansions=[f for f in fs if f['district_id']=='elite' and f['type']=='mansion']")
    scope=dict(vars(v7));scope.update(hashes=hashes,validate_targeted=validate_targeted,
        ROUTES=[(a,'B06' if b=='B07' else b) for a,b in v7.ROUTES])
    exec(compile(analysis,str(ROOT/'map_plan_v08.py'), 'exec'),scope)
    scope['analyse'](d)
    start=source.index('def render(data):');end=source.index('\ndef report(',start)
    renderer=source[start:end].replace("f['type']=='final_base'","f.get('poi_id')=='B06'")
    renderer=renderer.replace('v07','v08').replace('4 особняка, B06 и 2 доступных P15;','4 особняка, 2 доступны P15;').replace('B07: вилла','B06: престижная вилла')
    exec(compile(renderer,str(ROOT/'map_plan_v08.py'),'exec'),scope)
    (ROOT/(STEM+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    svg=ROOT/(STEM+'.svg');png=ROOT/(STEM+'.png')
    svg.write_text(scope['render'](d),encoding='utf-8');ET.parse(svg)
    env=os.environ.copy();env['MAGICK_TEMPORARY_PATH']=str(ROOT)
    subprocess.run([str(m.MAGICK),'-background','#f6f3e9',str(svg),'-strip',str(png)],check=True,cwd=ROOT,env=env,capture_output=True)
    header=png.read_bytes()[:24]
    assert header[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',header[16:24])==(2400,2400)
    (ROOT/(STEM+'_REPORT.md')).write_text(report(d),encoding='utf-8')
    assert before==hashes(),'Previous files changed'
    print(f'OK: {len(d["validation"]["checks"])} checks; {d["metrics"]["building_count"]} buildings; PNG 2400x2400')
    for r in d['metrics']['routes']:print(r['from_id'],'->',r['to_id'],r['length_m'],'m')


if __name__=='__main__':main()
