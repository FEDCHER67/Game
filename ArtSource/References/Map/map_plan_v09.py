#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Targeted v08 -> v09 revision. Run with Python -B; stdlib + ImageMagick."""
import copy
import hashlib
import json
import os
import struct
import subprocess
import xml.etree.ElementTree as ET
import map_plan_v08 as v8

v7 = v8.v7
m = v8.m
ROOT = m.ROOT
STEM = 'MAP_PLAN_R01_v09'


def hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.iterdir()) if p.is_file()
            and not p.name.startswith((STEM, 'map_plan_v09'))}


def seed():
    d = json.loads((ROOT / 'MAP_PLAN_R01_v08.json').read_text(encoding='utf-8'))
    d.update(revision='v09', title_ru='VOLUNTEERS ONLY — план карты R01 / v09')
    d['specification']['brief_override'] = 'req_map_plan_v09.md, targeted review, 2026-10-04'
    d['provenance'] = dict(brief='req_map_plan_v09.md', source_schema='MAP_PLAN_R01_v08.json',
        owner_decisions_date='2026-10-04', method='targeted v08 edits; unchanged geometry retained',
        previous_files_sha256=hashes())
    d['comparison'] = {'v08': {'extent_m': d['metrics']['extent_m']},
                       'policy': 'targeted edits; no uniform scaling'}
    # Remove both eastern rows, their lane, and the elite boutique/driveway.
    d['building_masses'] = [b for b in d['building_masses']
        if not (b['district_id'] == 'residential' and b.get('subtype') == 'garage_box')
        and b['district_id'] != 'elite']
    d['functional_buildings'] = [f for f in d['functional_buildings']
        if f['district_id'] != 'elite' or f['type'] in ('mansion', 'private_security')]
    d['roads'] = [r for r in d['roads'] if r['id'] not in ('R_GARAGE_LANE', 'ACCESS_F06_BOUTIQUE')]
    roads = {r['id']: r for r in d['roads']}
    fs = {f['id']: f for f in d['functional_buildings']}
    next(q for q in d['districts'] if q['id'] == 'residential')['polygon_m'] = [
        [470,620], [780,620], [780,825], [470,825]]
    bp = d['boundary']['polygon_m']
    i = bp.index([870,620])
    bp[i:i+4] = [[780,620], [780,825]]
    roads['R_COURTS_EAST']['polyline_m'] = [[650,675], [770,675]]
    # Replace the eastern utility function with P08 between the bar and NE post.
    d['functional_buildings'] = [f for f in d['functional_buildings']
        if f['id'] not in ('F06_BOILER', 'F06_CLOCK')]
    d['roads'] = [r for r in d['roads']
        if r['id'] not in ('ACCESS_F06_BOILER', 'ACCESS_F06_CLOCK')]
    pts = {p['id']: p for p in d['points']}
    hospital = fs['F06_HOSPITAL']
    former_hospital = hospital['center_m'][:]
    police = fs['F06_POLICE']
    former_police = police['center_m'][:]

    def relocate(f, center, door, district, rid, access_start):
        dx, dy = center[0]-f['center_m'][0], center[1]-f['center_m'][1]
        f.update(center_m=center, footprint_m=[[round(x+dx,3),round(y+dy,3)]
            for x,y in f['footprint_m']], entrance_m=door,
            district=district, district_id=district, access_road_id=rid)
        pid=f.get('poi_id')
        if pid:
            pts[pid].update(position_m=door, district_id=district)
        access=roads['ACCESS_'+(pid or f['id'])]
        access.update(polyline_m=[access_start,door],district_ids=[district])

    relocate(hospital,[741,724],[719,724],'residential','R_REAR',[710,724])
    hospital['label_ru']='Больница · C03'
    pts['P08']['name_ru']='Больница — работа C03'
    relocate(police,former_hospital,[760,582],'old_town','O_RING',[750,582])
    relocate(fs['F06_POST'],former_police,[510,490],'old_town','O_RING',[525,490])
    relocate(fs['F06_ATM'],[741,752],[741,758.5],'residential','R_REAR',[710,760])
    roads['ACCESS_P11-3']['polyline_m']=[[710,760],[741,760],[741,758.5]]
    pts['P11-3']['name_ru']='ATM у больницы'
    pts['CLOCK_SQUARE']['name_ru']='Малая площадь'

    # Keep all thirty house identities, sizes and storeys; separate the party walls.
    houses={
        1:[[539,567],[550,563],[563,568],[540,545],[552,546],[565,546]],
        2:[[686,568],[701,565],[722,566],[682,552],[704,551],[729,552]],
        3:[[538,517],[550,512],[564,516],[539,495],[552,491],[566,497]],
        4:[[682,516],[697,513],[719,517],[683,495],[701,495],[727,496]],
        5:[[536,460],[550,462],[568,458],[587,465],[603,459],[616,463]],
    }
    for b in d['building_masses']:
        if 'terrace_id' in b:
            group=int(b['terrace_id'].split('_')[-1])
            unit=int(b['id'].split('_U')[-1])-1
            b['center_m']=houses[group][unit]
            b['polygon_m']=m.rectangle(*b['center_m'],b['width_m'],b['depth_m'])

    meetings={
        'P09':('old_town',[608,588],'Обычная: за супермаркетом','main',[608,590]),
        'P09-2':('residential',[724,770],'Запасная: дворы','backup',[710,770]),
        'P09-3':('industrial',[625,350],'Запасная: у B05','backup',[650,350]),
        'P09-4':('transition',[419,712],'Запасная: переход','backup',[405,712]),
    }
    p=copy.deepcopy(pts['P09-3']);p['id']='P09-4';d['points'].append(p);pts[p['id']]=p
    site=copy.deepcopy(next(s for s in d['functional_sites'] if s.get('poi_id')=='P09-3'))
    site.update(id='SITE_P09-4',poi_id='P09-4');d['functional_sites'].append(site)
    d['roads'].append(dict(id='ACCESS_P09-4',polyline_m=[],width_m=3.8,
        **{'class':'rural_road'},district_ids=['transition'],access_only=True))
    roads={r['id']:r for r in d['roads']}
    for pid,(district,pos,label,role,start) in meetings.items():
        pts[pid].update(district_id=district,position_m=pos,name_ru=label,meeting_role=role)
        s=next(s for s in d['functional_sites'] if s.get('poi_id')==pid)
        s.update(district_id=district,position_m=pos,label_ru=label)
        roads['ACCESS_'+pid].update(polyline_m=[start,pos],district_ids=[district])
    return d


def courtyard(d):
    """Fit the third U south of a straight street without moving fixed shops."""
    roads = {r['id']: r for r in d['roads']}
    bs = {b['id']: b for b in d['building_masses']}
    c = d['microdistricts'][2]
    c.update(center_m=[592.5,652], yard_polygon_m=m.rectangle(592.5,657,30,28))
    base = bs['R06_C3_S1']
    base.update(center_m=[592.5,635], width_m=36, polygon_m=m.rectangle(592.5,635,36,12,180))
    for bid, x in (('R06_C3_S2',614.5), ('R06_C3_S3',570.5)):
        bs[bid].update(center_m=[x,657], width_m=30,
            polygon_m=m.rectangle(x,657,30,12,270))
    # Retain all entrances and fixed frontage objects; divert the avenue around U3.
    roads['ARC_AVENUE']['polyline_m'] = [
        [470,650], [535,650], [535,678], [650,678], [650,620], [650,540], [800,540]]
    roads['R_COURTS']['polyline_m'] = [[500,678], [535,678]]
    roads['COURT_ACCESS_1']['polyline_m'] = [[535,678], [535,705]]
    roads['COURT_ACCESS_2']['polyline_m'] = [[650,678], [650,705]]
    roads['R_LINK']['polyline_m'] = [[650,675], [650,678]]
    roads['COURT_ACCESS_3']['polyline_m'] = [[592.5,780], [592.5,661]]
    # The kiosk's existing access remains on its original y=650 frontage branch.
    roads['R_COURTS'].update(polyline_m=[[500,678], [535,678], [535,650], [560,650]])
    roads['ACCESS_P13-4']['polyline_m'] = [[606,678], [606,675]]
    next(p for p in d['points'] if p['id']=='BAD_BLOCK_3')['position_m'] = [592.5,661]
    # Retain only the purposeful hospital ATM passage and existing old-town alley.
    d['paths']=[p for p in d['paths'] if p['id'] in ('PASS06_BAD_2','PASS06_OLD')]
    for p in d['paths']:
        if p['id']=='PASS06_BAD_2':
            p.update(polyline_m=[[650,705],[650,678],[720,678],[720,745],[732,745],[732,758.5],[741,758.5]],
                label_ru='Двор 2 → ATM больницы',kind='yard_link',
                purpose_ru='Пешеходный проход из двора 2 к отдельному ATM P11-3 у больницы P08.')
        p['length_m'] = round(sum(m.length(a,b) for a,b in zip(p['polyline_m'],p['polyline_m'][1:])),3)
    d['planning_notes_ru'] = [
        'Дворы 1–2 и все их корпуса сохранены. Двор 3 ниже связанной улицы y=678; открыт на север, по центру между ними.',
        'Чтобы не двигать киоски, их подъезды и границу старого города, только двор 3 уплотнён: боковые корпуса 30 × 12 м, нижний 36 × 12 м вместо 72 × 12 м.',
        'Котельная с трубой удалена. Больница P08 / C03 — (741;724), между баром P06 и постом P16-2, в восточной служебной зоне.',
        'Отдельный ATM P11-3 рядом с больницей; к нему ведёт проход из двора 2. Два бесцельных прохода удалены; ATM магазина и банк сохранены.',
        'Удалены обе восточные линии гаражей (18 боксов) и их улица; район и внешняя граница обрезаны по x=780.',
        'Элитный холм: ровно четыре особняка, два доступны P15; только маленькая охранная будка у въезда. Бутик удалён.',
        'Полиция P10 — на прежнем месте больницы (779;582); почта — на прежнем месте полиции (495;490), дальше от B04.',
        '30 отдельных домов 2–3 этажа: зазоры, разные интервалы и смещения; сплошных террас нет. Часовая башня удалена, малая площадь сохранена.',
        'P09: ровно 4 точки — обычная в старом городе; запасные у B05, в неблагополучном районе и в переходе.',
        'B03, магазины, P05, P06, P07, банк, P16-2 и его тупик, вилла B06 у озера сохранены.',
        'Время расчётное; субъективное принятие и физические барьеры требуют Unity-плейтеста.']


def strip_nodes(q):
    return {k:v for k,v in q.items() if k not in ('road_node_id', 'dead_end_node_id')}


def validate_targeted(d, check):
    old=json.loads((ROOT/'MAP_PLAN_R01_v08.json').read_text(encoding='utf-8'))
    fs={f['id']:f for f in d['functional_buildings']}
    ofs={f['id']:f for f in old['functional_buildings']}
    pts={p['id']:p for p in d['points']}
    roads={r['id']:r for r in d['roads']}
    check('exact v08 schema version and top-level types',d['schema_version']==old['schema_version']
        and set(d)==set(old) and all(type(d[k])==type(v) for k,v in old.items()))
    check('upper two courtyards and all six slabs unchanged',d['microdistricts'][:2]==old['microdistricts'][:2]
        and [b for b in d['building_masses'] if b['id'].startswith(('R06_C1_','R06_C2_'))]
        == [b for b in old['building_masses'] if b['id'].startswith(('R06_C1_','R06_C2_'))])
    third=[b for b in d['building_masses'] if b['id'].startswith('R06_C3_')]
    upper=[b for b in d['building_masses'] if b['id'].startswith(('R06_C1_','R06_C2_'))]
    check('connected 7 m street fully separates U3 below from U1 and U2 above',
        max(p[1] for b in third for p in b['polygon_m'])<678-3.5 and
        min(p[1] for b in upper for p in b['polygon_m'])>678+3.5 and
        d['microdistricts'][2]['center_m'][0]==(535+650)/2 and
        d['microdistricts'][2]['opening_direction']=='north' and
        [535,678] in roads['ARC_AVENUE']['polyline_m'] and [650,678] in roads['ARC_AVENUE']['polyline_m'])
    h=fs['F06_HOSPITAL'];bar=fs['F06_BAR'];post=pts['P16-2']
    check('boiler and its chimney removed; P08 C03 hospital between bar and NE post',
        'F06_BOILER' not in fs and not any(f['type']=='boiler_house' for f in fs.values()) and
        h['district_id']=='residential' and h['poi_id']=='P08' and h['icon']=='+' and
        'C03' in h['label_ru'] and bar['center_m'][1]<h['center_m'][1]<post['position_m'][1])
    atm=[f for f in fs.values() if f['type']=='atm_pavilion']
    passage=next(p for p in d['paths'] if p['district_id']=='residential')
    check('one standalone ATM next to hospital; courtyard 2 passage ends at its entrance',
        len(atm)==1 and atm[0]['district_id']=='residential' and
        m.length(atm[0]['center_m'],h['center_m'])<35 and
        passage['polyline_m'][0]==pts['BAD_BLOCK_2']['position_m'] and
        passage['polyline_m'][-1]==atm[0]['entrance_m'] and
        len(d['paths'])==2 and next(p for p in d['paths'] if p['id']=='PASS06_OLD')==
        next(p for p in old['paths'] if p['id']=='PASS06_OLD'))
    check('police and post moved to exact requested former centres',
        fs['F06_POLICE']['center_m']==ofs['F06_HOSPITAL']['center_m'] and
        fs['F06_POST']['center_m']==ofs['F06_POLICE']['center_m'])
    check('police closer to mansions and farther from B06; post farther from B04',
        m.length(fs['F06_POLICE']['center_m'],fs['F08_MANSION_1']['center_m'])<
        m.length(ofs['F06_POLICE']['center_m'],ofs['F08_MANSION_1']['center_m']) and
        m.length(fs['F06_POLICE']['center_m'],fs['F07_VILLA']['center_m'])>
        m.length(ofs['F06_POLICE']['center_m'],ofs['F07_VILLA']['center_m']) and
        m.length(fs['F06_POST']['center_m'],fs['F06_HBASE']['center_m'])>
        m.length(ofs['F06_POST']['center_m'],ofs['F06_HBASE']['center_m']))
    houses=[b for b in d['building_masses'] if 'terrace_id' in b]
    check('thirty separate 2 to 3 storey houses; no touching walls; irregular spacing',len(houses)==30 and
        all(2<=b['floors']<=3 for b in houses) and all(min(
        v7.gap(a['polygon_m'],c,e) for c,e in v7.edges(b['polygon_m']))>=2
        for i,a in enumerate(houses) for b in houses[i+1:]) and
        all(len({b['center_m'][1] for b in houses if b['terrace_id']==tid})>=4
            for tid in {b['terrace_id'] for b in houses}))
    check('clock tower removed; small square and unchanged bank retained; no standalone old-town ATM',
        'F06_CLOCK' not in fs and 'CLOCK_SQUARE' in pts and fs['F06_BANK']==ofs['F06_BANK'] and
        not any(f['type']=='atm_pavilion' and f['district_id']=='old_town' for f in fs.values()))
    elite=[f for f in fs.values() if f['district_id']=='elite']
    check('elite exactly four unchanged mansions and original small entrance booth',len(elite)==5 and
        sum(f['type']=='mansion' for f in elite)==4 and sum(f.get('accessible',False) for f in elite)==2 and
        sum(f['type']=='private_security' and f['width_m']<=9 and f['depth_m']<=8 for f in elite)==1 and
        not any(b['district_id']=='elite' for b in d['building_masses']) and
        all(f==ofs[f['id']] for f in elite))
    meetings=[p for p in d['points'] if p['canonical_id']=='P09']
    sites=[s for s in d['functional_sites'] if s['type']=='meeting']
    check('four P09 sites exactly one per requested district; old town usual; others backup',
        len(meetings)==len(sites)==4 and {p['district_id'] for p in meetings}==
        {'industrial','residential','old_town','transition'} and
        all(p['meeting_role']==('main' if p['district_id']=='old_town' else 'backup') for p in meetings) and
        all(any(s['poi_id']==p['id'] and s['position_m']==p['position_m'] and
            s['district_id']==p['district_id'] for s in sites) for p in meetings) and
        m.length(pts['P09-3']['position_m'],fs['F06_COMPLEX']['center_m'])<40)
    check('eastern garage rows and lane removed; B03 unchanged',
        not any(b.get('subtype')=='garage_box' for b in d['building_masses']) and
        'R_GARAGE_LANE' not in roads and fs['F06_GBASE']==ofs['F06_GBASE'])
    check('district and outer boundary each shrink by 16650 square metres',
        abs(old['metrics']['area_m2']-d['metrics']['area_m2']-16650)<.01 and
        abs(next(q for q in old['districts'] if q['id']=='residential')['area_m2']-
            next(q for q in d['districts'] if q['id']=='residential')['area_m2']-16650)<.01)
    changed_functions={'F06_BOILER','F06_CLOCK','F06_HOSPITAL','F06_POLICE','F06_POST','F06_ATM','F06_BOUTIQUE'}
    check('every unrelated functional building including B03 shops bar den P05 B06 unchanged',
        [f for f in d['functional_buildings'] if f['id'] not in changed_functions]==
        [f for f in old['functional_buildings'] if f['id'] not in changed_functions])
    changed_points={'P08','P10','P11-3','P09','P09-2','P09-3','P09-4','CLOCK_SQUARE','BAD_BLOCK_3'}
    check('every unrelated point including NE post unchanged except regenerated node IDs',
        [strip_nodes(p) for p in d['points'] if p['id'] not in changed_points]==
        [strip_nodes(p) for p in old['points'] if p['id'] not in changed_points])
    check('all exits including NE post flanks trigger and dead end unchanged',
        [strip_nodes(e) for e in d['exits']]==[strip_nodes(e) for e in old['exits']])
    check('water railway fields hills estates plots vegetation unchanged',
        all(d[k]==old[k] for k in ('water','railway','field_parcels_m','hills','farmsteads','plots','vegetation_parcels')))
    check('all unrelated sites unchanged',
        [s for s in d['functional_sites'] if s['type']!='meeting']==
        [s for s in old['functional_sites'] if s['type']!='meeting'])
    unchanged_mass=lambda b: not b['id'].startswith('R06_C3_') and 'terrace_id' not in b and not (
        b['district_id']=='elite' or (b['district_id']=='residential' and b.get('subtype')=='garage_box'))
    check('all unrelated building masses unchanged',
        [b for b in d['building_masses'] if unchanged_mass(b)]==
        [b for b in old['building_masses'] if unchanged_mass(b)])
    check('all road centre lines inside boundary',all(m.inside(p,d['boundary']['polygon_m'])
        for r in d['roads'] for p in r['polyline_m']))
    check('NE flank barriers inside reduced district',all(m.inside(p,
        next(q for q in d['districts'] if q['id']=='residential')['polygon_m'])
        for e in d['exits'] if e['id']=='NE' for poly in e['barrier_polygons_m'] for p in poly))
    altered={'ARC_AVENUE','R_COURTS','R_LINK','COURT_ACCESS_1','COURT_ACCESS_2','COURT_ACCESS_3',
        'R_COURTS_EAST','ACCESS_F06_BOILER','ACCESS_P13-4','R_GARAGE_LANE','ACCESS_F06_BOUTIQUE',
        'ACCESS_F06_CLOCK','ACCESS_P08','ACCESS_P10','ACCESS_F06_POST','ACCESS_P11-3',
        'ACCESS_P09-2','ACCESS_P09-3','ACCESS_P09-4'}
    check('all unrelated road geometry unchanged',[r for r in d['roads'] if r['id'] not in altered]==
        [r for r in old['roads'] if r['id'] not in altered])
    check('all reported vehicle and pedestrian route distances finite',all(
        v7.math.isfinite(r[k]) for r in d['metrics']['routes'] for k in ('length_m','pedestrian_length_m')))


def analysis_scope():
    source = (ROOT/'map_plan_v07.py').read_text(encoding='utf-8')
    start=source.index('def analyse(data):');end=source.index('\ndef validate_targeted',start)
    analysis=source[start:end]
    analysis=analysis.replace("len(phys)==115", "len(phys)==94")
    analysis=analysis.replace('physical count matches v06 removals plus B07 and P01 pole', 'physical count: v08 minus 18 garages, boiler, clock tower and boutique')
    analysis=analysis.replace('exactly three 72 × 12 m slabs each', 'three slabs each; U3 side slabs fit retained frontage')
    analysis=analysis.replace("all(b['width_m']==72 and b['depth_m']==12 and 9<=b['floors']<=12 for b in slabs)",
        "all(b['width_m']==(30 if b['id'] in ('R06_C3_S2','R06_C3_S3') else 36 if b['id']=='R06_C3_S1' else 72) and b['depth_m']==12 and 9<=b['floors']<=12 for b in slabs)")
    analysis=analysis.replace("'private_security','boutique','prestige_base'", "'private_security','prestige_base'")
    analysis=analysis.replace("mansions=[f for f in fs if f['type'] in ('mansion','prestige_base')]",
        "mansions=[f for f in fs if f['district_id']=='elite' and f['type']=='mansion']")
    analysis=analysis.replace('garage_box_count=18', 'garage_box_count=sum(b.get(\'subtype\')==\'garage_box\' for b in bs)')
    analysis=analysis.replace("'shop_24h','boiler_house','hospital'", "'shop_24h','hospital'")
    analysis=analysis.replace("'house_base','clock_tower','bank'", "'house_base','bank'")
    analysis=analysis.replace("'three open P09 meeting sites'", "'four open P09 meeting sites'")
    analysis=analysis.replace("{'P09','P09-2','P09-3'}", "{'P09','P09-2','P09-3','P09-4'}")
    analysis=analysis.replace('five six-unit terraces; 7-m frontages; 2?3 floors', 'thirty small houses; 7-m frontages; 2?3 floors')
    analysis=analysis.replace('four clear urban-only walking passages', 'two clear urban-only walking passages')
    analysis=analysis.replace("len(data['paths'])==4", "len(data['paths'])==2")
    analysis=analysis.replace('dict(count=4,total_length_m=', "dict(count=len(data['paths']),total_length_m=")
    scope=dict(vars(v7));scope.update(hashes=hashes,validate_targeted=validate_targeted,
        ROUTES=[(a,'B06' if b=='B07' else b) for a,b in v7.ROUTES]+[
            ('P06','P08'),('P08','P11-3'),('B06','P10'),('P10','P15'),
            ('B05','P09-3'),('BAD_BLOCK_2','P11-3')])
    exec(compile(analysis,str(ROOT/'map_plan_v09.py'),'exec'),scope)
    start=source.index('def render(data):');end=source.index('\ndef legend(',start)
    renderer=source[start:end].replace("f['type']=='final_base'", "f.get('poi_id')=='B06'")
    renderer=renderer.replace('v07','v09').replace('18 боксов, B03', 'Без гаражных рядов; B03')
    renderer=renderer.replace('3 двора × 3 корпуса 72 × 12 м;', '3 двора × 3 корпуса; 9–12 этажей;')
    renderer=renderer.replace('4 особняка, B06 и 2 доступных P15;', '4 особняка, 2 доступны P15;')
    renderer=renderer.replace('охрана, бутик / B05', 'будка охраны / B05').replace('B07: вилла', 'B06: престижная вилла')
    renderer=renderer.replace('3 двора × 3 корпуса / 9–12 этажей', 'Двор 3 — за улицей')
    renderer=renderer.replace('Террасы 2–3 эт. / 2 высотки', 'Отдельные дома 2–3 эт. / 2 высотки')
    renderer=renderer.replace("('P01','P09','P09-2','P09-3')", "('P01','P09','P09-2','P09-3','P09-4')")
    renderer=renderer.replace("                if label.startswith('Кафе'):", """                if label.startswith('P09'):
                    pid=label.split()[0]
                    meeting=next(p for p in data['points'] if p['id']==pid)
                    world=[80+(box[0]+width/2-70)/scale,900-(box[1]+size/2-210)/scale]
                    district=next(q['polygon_m'] for q in data['districts'] if q['id']==meeting['district_id'])
                    if not m.inside(world,district):continue
                if label.startswith('Кафе'):""")
    # Compile the matching legend in the same scope; its distances are filled below.
    start=source.index('def legend(');end=source.index('\ndef report(',start)
    legend_source=source[start:end].replace('v07','v09')
    replacements={
        '3 двора × 3 корпуса 72 × 12 м;':'3 двора × 3 корпуса; 9–12 эт.;',
        '18 боксов, B03, бар P06, притон P07;':'B03, бар P06, притон P07;',
        '3 киоска, 24 ч, котельная / труба.':'3 киоска, 24 ч, P08 / C03, ATM.',
        '5 террас × 6 домов по 7 м;':'30 отдельных домов 2–3 эт.;',
        'две высотки, P05, B04, больница P08,':'две высотки, P05, B04,',
        'полиция P10, банк / ATM, магазин;':'полиция P10, банк, магазин;',
        'площадь / часы; P09 + 2 запасные.':'малая площадь; P09 — обычная.',
        '4 особняка, B06 и 2 доступных P15;':'4 особняка, 2 доступны P15;',
        'охрана, бутик / B05, P14, P12,':'будка охраны / B05, P14, P12,',
        'B07: вилла 2 эт., гараж для бусика;':'B06: вилла 2 эт., гараж для бусика;',
        '4 ЛОКАЛЬНЫХ ПРОХОДА':'2 ЛОКАЛЬНЫХ ПРОХОДА',
    }
    for old,new in replacements.items():
        assert old in legend_source,old
        legend_source=legend_source.replace(old,new)
    legend_source=legend_source.replace("y+=5;s.text(x,y,'2 ЛОКАЛЬНЫХ ПРОХОДА'", """y+=5;s.text(x,y,'P09 / 4 МЕСТА ВСТРЕЧ',size=18,weight='bold');y+=25
    s.text(x,y,'Обычная — за супермаркетом.',size=14);y+=21
    s.text(x,y,'Запасные — B05, дворы, переход.',size=14);y+=27
    s.text(x,y,'2 ЛОКАЛЬНЫХ ПРОХОДА'""")
    exec(compile(legend_source,str(ROOT/'map_plan_v09.py'),'exec'),scope)
    renderer=renderer.replace('4 локальных прохода / 2,5 м / только пешком.',
        '2 прохода / 2,5 м: к ATM и старый переулок.')
    exec(compile(renderer,str(ROOT/'map_plan_v09.py'),'exec'),scope)
    inherited_render = scope['render']
    def render(d):
        svg = inherited_render(d)
        routes = {(r['from_id'], r['to_id']):r for r in d['metrics']['routes']}
        decimal = lambda value, places: f'{value:.{places}f}'.replace('.', ',')
        for base, old_length, old_times, old_walk, old_footer in (
            ('B01', '588', '35,3 / 23,5', '7,06', '7,1'),
            ('B02', '328', '19,7 / 13,1', '3,94', '3,9')):
            r = routes[base, 'BAD_CENTER']
            distance = f'{r["length_m"]:.0f}'
            svg = svg.replace(f'{base} → РАЙОН / {old_length} м', f'{base} → РАЙОН / {distance} м')
            svg = svg.replace(f'60 / 90 км/ч: {old_times} с',
                f'60 / 90 км/ч: {decimal(r["van_60_seconds"],1)} / {decimal(r["van_90_seconds"],1)} с')
            svg = svg.replace(f'Пешком 5 км/ч: {old_walk} мин', f'Пешком 5 км/ч: {decimal(r["walk_5_minutes"],2)} мин')
            svg = svg.replace(f'{base} → район: {old_length} м; пешком {old_footer} мин.',
                f'{base} → район: {distance} м; пешком {decimal(r["walk_5_minutes"],1)} мин.')
        return svg
    scope['render'] = render
    return scope


def report(d):
    lines=['# VOLUNTEERS ONLY — R01 v09','',
        'Основание: req_map_plan_v09.md, целевые правки v08 от 04.10.2026.',
        f'Карта: 815 × 685 м; площадь {d["metrics"]["area_m2"]:.0f} м² (v08: 313250); {d["metrics"]["building_count"]} зданий; SVG/PNG 2400 × 2400.',
        *d['planning_notes_ru'][:-1],
        'Геометрическое уточнение: целые 72-метровые руки двора 3 не помещаются южнее прямой улицы без вторжения в неизменный старый город.',
        'Улица y=678 соединена с проспектом; местные подъезды адаптированы; 2 полезных прохода. Нижний корпус двора 3: (592,5;635), руки до y=672.',
        'Пост СВ (710;790), тупик (735;805), боковые барьеры и триггер полностью сохранены; вилла B06 у озера сохранена.', '',
        '| Маршрут | Дорога, м | 60 км/ч, с | 90 км/ч, с | Пешком, м / мин |',
        '|---|---:|---:|---:|---:|']
    for r in d['metrics']['routes']:
        lines.append(f'| {r["from_id"]} → {r["to_id"]} | {r["length_m"]:.1f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["pedestrian_length_m"]:.1f} / {r["walk_5_minutes"]:.2f} |')
    lines += ['',f'Проверки: {sum(c["passed"] for c in d["validation"]["checks"])}/{len(d["validation"]["checks"])}; детали и автомобильные/пешие дистанции в JSON.',
        'Повторены дистанционные ограничения, связность двух графов, отсутствие обходов въездов/постов, пересечения зданий с дорогами/проходами/водой/ЖД.',
        'Схема JSON v08 сохранена; старые файлы проверены SHA-256. Git и WORK_SYNC.md не затрагивались; новые файлы только в Map.',
        'Сборка: python -B map_plan_v09.py. PNG просмотрен после сборки.',
        'Время теоретическое: без разгона, поворотов, трафика и уклонов; необходим Unity-плейтест.']
    assert len(lines)<=50
    return '\n'.join(lines)+'\n'


def main():
    before=hashes();d=seed();courtyard(d);scope=analysis_scope();scope['analyse'](d)
    svg=ROOT/(STEM+'.svg');png=ROOT/(STEM+'.png')
    svg.write_text(scope['render'](d),encoding='utf-8');ET.parse(svg)
    env=os.environ.copy();env['MAGICK_TEMPORARY_PATH']=str(ROOT)
    subprocess.run([str(m.MAGICK),'-background','#f6f3e9',str(svg),'-strip',str(png)],
        check=True,cwd=ROOT,env=env,capture_output=True)
    header=png.read_bytes()[:24]
    assert header[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',header[16:24])==(2400,2400)
    (ROOT/(STEM+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (ROOT/(STEM+'_REPORT.md')).write_text(report(d),encoding='utf-8')
    assert before==hashes(),'Previous files changed'
    print(f'OK: {len(d["validation"]["checks"])} checks; {d["metrics"]["building_count"]} buildings; PNG 2400x2400')
    for r in d['metrics']['routes']:print(r['from_id'],'->',r['to_id'],r['length_m'],'m')


if __name__=='__main__': main()
