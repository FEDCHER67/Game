#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R01 v05. Python 3.12 standard library only. Run: python build_map_plan.py.

Existing JSON is authoritative: edit it and rerun to recalculate the graph,
metrics, SVG, PNG and report. --reset-data restores this authored proposal.
--revision v02 / v03 / v04 retain the previous builders. Default output is v05.
All outputs are written beside this script. No Unity/project/Git operations.
"""
from __future__ import annotations

import argparse
import heapq
import html
import hashlib
import json
import math
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
STEM = 'MAP_PLAN_R01_v03'
MAGICK = Path(r'C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe')


def length(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])


def area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly, poly[1:]+poly[:1])))/2


def inside(p, poly):
    x,y = p
    hit = False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>y)!=(b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            hit = not hit
    return hit


def projection(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy or 1)))
    q=[a[0]+t*dx,a[1]+t*dy]
    return length(p,q),q,t


def crossing(a,b,c,d):
    rx,ry=b[0]-a[0],b[1]-a[1]
    sx,sy=d[0]-c[0],d[1]-c[1]
    den=rx*sy-ry*sx
    if abs(den)<1e-9:
        return None
    qx,qy=c[0]-a[0],c[1]-a[1]
    t=(qx*sy-qy*sx)/den
    u=(qx*ry-qy*rx)/den
    if -1e-8<=t<=1+1e-8 and -1e-8<=u<=1+1e-8:
        return [a[0]+t*rx,a[1]+t*ry],max(0,min(1,t)),max(0,min(1,u))
    return None


def smooth(points, steps=8):
    """Interpolating Catmull-Rom: all authored junctions remain exact."""
    result=[]
    for i in range(len(points)-1):
        p0,p1,p2,p3=points[max(0,i-1)],points[i],points[i+1],points[min(len(points)-1,i+2)]
        for j in range(steps):
            t=j/steps
            result.append([round(.5*((2*p1[k])+(-p0[k]+p2[k])*t+(2*p0[k]-5*p1[k]+4*p2[k]-p3[k])*t*t+(-p0[k]+3*p1[k]-3*p2[k]+p3[k])*t*t*t),4) for k in (0,1)])
    return result+[list(points[-1])]


def rectangle(x,y,w,h,angle=0):
    c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    return [[round(x+u*c-v*s,3),round(y+u*s+v*c,3)] for u,v in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]


def seed_data():
    # Shared irregular chains form an exact planar partition, not radial wedges.
    A=[100,1280]; B=[880,2320]; C=[1230,2290]; D=[2350,1400]
    E=[2180,310]; F=[1590,100]; G=[1080,90]; J=[880,930]; K=[1250,1460]
    ab=[A,[75,1550],[150,1810],[120,2030],[260,2230],[480,2320],[730,2280],B]
    bc=[B,[1050,2350],C]
    cd=[C,[1450,2350],[1750,2310],[2010,2360],[2240,2200],[2320,1980],[2290,1720],D]
    de=[D,[2320,1250],[2380,960],[2280,740],[2340,540],E]
    ef=[E,[2040,120],[1790,70],F]
    fg=[F,[1340,50],[1090,150],G]
    ga=[G,[680,160],[420,100],[230,290],[180,580],[80,830],[130,1080],A]
    aj=[A,[290,1330],[390,1260],[540,1190],[660,1120],[720,990],J]
    jg=[J,[1100,790],[1060,600],[1000,460],[1160,300],G]
    jk=[J,[1130,990],[1130,1150],[1230,1310],K]
    bk=[B,[800,2120],[830,1950],[920,1830],[920,1680],[1070,1550],K]
    ck=[C,[1370,2160],[1320,1990],[1380,1820],[1340,1620],K]
    kd=[K,[1470,1320],[1620,1370],[1810,1340],[1960,1460],[2150,1440],D]
    fe=[F,[1690,400],[1840,470],[2040,410],E]
    def join(*chains):
        out=[]
        for ch in chains:
            out+=ch[:-1]
        return out
    districts=[]
    def district(id,name,color,poly,notes,parent=None):
        districts.append(dict(id=id,name_ru=name,color=color,polygon_m=poly,parent_id=parent,notes_ru=notes))
    district('forest','Лесные холмы','#bdcdbb',join(aj,jg,ga),'Холмы; вагон на опушке; просвет к промышленной трубе.')
    district('village','Деревня и сельская среда','#e2dbb5',join(ab,bk,list(reversed(jk)),list(reversed(aj))),'Сельские дороги, участки и открытые поля внутренней долины.')
    district('transition','Загородный переход','#d6d8c0',join(bc,ck,list(reversed(bk))),'Пологие луга между селом и спальником; две отдельные ветки B02 и P04.')
    district('residential','Неблагополучный спальник','#bdc9d0',join(cd,list(reversed(kd)),list(reversed(ck))),'Большие микрорайоны; 4–5-этажные пластины и три высотных ориентира.')
    district('old_town','Старый город','#e2cbb6',join(kd,de,list(reversed(fe)),fg,list(reversed(jg)),jk),'Крупнейшая зона; исторические улицы, просторные проспекты, вложенный элитный холм.')
    district('industrial','Промышленная окраина','#cbc5cc',join(fe,ef),'Цеха и депо в конце старой железнодорожной ветки.')
    elite=[[1850,815],[1900,760],[2070,780],[2160,880],[2170,1060],[2080,1130],[1920,1090],[1850,970]]
    district('elite','Элитный холм','#c8d5b2',elite,'Семь особняков с садами и два дорогих многоквартирных корпуса.','old_town')
    boundary=join(ab,bc,cd,de,ef,fg,ga)
    classes={'highway':dict(name_ru='Магистраль / проспект',width_m=16,color='#7b8989'),
             'town_street':dict(name_ru='Городская улица',width_m=11,color='#faf4e7'),
             'rural_road':dict(name_ru='Сельская дорога',width_m=7,color='#f4edda'),
             'dirt_shortcut':dict(name_ru='Грунтовая срезка',width_m=5,color='#c8ae82')}
    roads=[]
    def road(id,cls,pts,width=None,**extra):
        roads.append(dict(id=id,**{'class':cls},width_m=width or classes[cls]['width_m'],polyline_m=smooth(pts),**extra))
    # Rural ribbon settlement, an arc highway and loops around large urban yards.
    road('V_MAIN','rural_road',[[460,1190],[490,1250],[530,1290],[650,1410],[730,1560],[740,1780],[680,1930],[600,2110]])
    road('V_WEST','rural_road',[[530,1290],[400,1440],[365,1600],[450,1790],[680,1930]])
    road('V_EAST','rural_road',[[650,1410],[820,1500],[880,1650],[740,1780]])
    road('ARC_RURAL','rural_road',[[740,1780],[860,1840],[995,1820],[1120,1765],[1260,1740]])
    road('HUT_BRANCH','rural_road',[[995,1820],[965,1960],[1030,2050],[970,2170],[950,2220]])
    road('RECEPTION_BRANCH','rural_road',[[1260,1740],[1195,1830],[1230,1920],[1170,2000]])
    road('ARC_AVENUE','highway',[[1260,1740],[1470,1730],[1720,1800],[1870,1910],[2170,1840],[2110,1640],[1940,1410],[1700,1090],[1520,820],[1410,570],[1360,380]])
    road('R_OUTER','town_street',[[1470,1730],[1500,2090],[1770,2170],[2090,2110],[2170,1840]],14)
    road('R_SOUTH','town_street',[[1470,1730],[1570,1585],[1790,1580],[2110,1640]],13)
    road('R_DIAGONAL','town_street',[[1500,2090],[1690,2030],[1870,1910],[1790,1580]])
    road('R_NORTH','town_street',[[1770,2170],[1840,2030],[1870,1910]])
    road('R_EAST','town_street',[[1870,1910],[1995,2010],[2090,2110]])
    road('R_YARD_W','town_street',[[1720,1800],[1635,1915],[1690,2030]],7)
    road('R_YARD_E','town_street',[[2110,1640],[1990,1770],[2170,1840]],7)
    # Historic streets curve and radiate from the clock square; no Manhattan grid.
    road('O_NORTH','town_street',[[1570,1585],[1490,1370],[1565,1210],[1700,1090],[1930,1160],[2170,1250],[2210,1440],[2110,1640]],13)
    road('O_CROWN','town_street',[[1490,1370],[1660,1450],[1940,1410],[2170,1250]],11)
    road('O_MARKET','town_street',[[1565,1210],[1770,1310],[1940,1410]])
    road('O_RIVER','town_street',[[1490,1370],[1340,1200],[1330,1050],[1420,940],[1520,820],[1750,740],[2040,750],[2220,880],[2170,1250]],12)
    road('O_EAST_AVENUE','highway',[[1700,1090],[1770,970],[1830,830],[1930,670],[2030,490],[2010,300]])
    road('O_SOUTH_ARC','town_street',[[1330,1050],[1210,880],[1250,730],[1410,570],[1650,510],[1840,530],[2030,490],[2180,580],[2220,880]],12)
    road('O_WEST','town_street',[[1210,880],[1090,720],[1100,490],[1210,350],[1360,380],[1650,510]])
    road('O_SMALL_1','town_street',[[1420,940],[1600,995],[1700,1090]],8)
    road('O_SMALL_2','town_street',[[1770,1310],[1785,1180],[1700,1090]],8)
    road('O_SMALL_3','town_street',[[1770,970],[1700,890],[1520,820]],8)
    road('O_SMALL_4','town_street',[[1930,1160],[2020,1210],[2170,1250]],8)
    road('O_SMALL_5','town_street',[[1410,570],[1440,720],[1520,820]],8)
    road('O_SMALL_6','town_street',[[1650,510],[1700,630],[1750,740]],8)
    road('O_QUAY','town_street',[[1410,570],[1480,680],[1750,740]])
    road('ELITE_LOOP','town_street',[[1930,1160],[1980,1040],[2070,1000],[2100,885],[2000,825],[1910,900],[1945,995],[1980,1040]],8)
    road('ELITE_SOUTH','town_street',[[2000,825],[2040,750]],8)
    road('FIELD_NORTH','dirt_shortcut',[[820,1500],[1000,1515],[1150,1450],[1340,1200]])
    road('FIELD_EAST','dirt_shortcut',[[880,1650],[1000,1720],[1260,1740]])
    road('FIELD_SOUTH','dirt_shortcut',[[650,1410],[750,1290],[800,1160],[910,950],[1080,1000],[1330,1050]])
    railpts=[[460,1190],[600,1130],[760,1070],[910,950],[1070,760],[1250,570],[1450,370],[1650,270],[1890,280]]
    road('RAIL_SERVICE','dirt_shortcut',[[460,1190],[500,1140],[680,1050],[840,930],[970,750],[1140,570],[1360,380],[1640,330],[1810,320],[1890,280]],6,railway_service=True)
    road('I_YARD','town_street',[[1640,330],[1790,420],[2010,300],[2090,235],[2060,180],[1950,170],[1890,280]],10)
    road('EXIT_NW','highway',[[600,2110],[420,2140],[315,2150],[245,2140]],12)
    road('EXIT_NE','highway',[[2090,2110],[2200,2050],[2260,2100]],12)
    road('EXIT_S','highway',[[1360,380],[1260,270],[1230,190]],12)
    points=[]
    def poi(id,name,xy,dist,category='poi',attach=None,offset=(15,-16),**extra):
        points.append(dict(id=id,canonical_id=id.split('-')[0],name_ru=name,position_m=list(xy),district_id=dist,category=category,label_offset_px=list(offset),**extra))
        if attach:
            cls='rural_road' if dist in ('forest','village','transition') else 'town_street'
            road('ACCESS_'+id,cls,[attach,xy],5)
    poi('B01','Вагон',[460,1190],'forest','base',offset=(-140,32))
    poi('B02','Хижина',[950,2220],'transition','base',offset=(-155,-14))
    poi('B03','База-гараж',[1650,1835],'residential','base',[1720,1800],(-146,32))
    poi('B04','Старый дом',[1460,1150],'old_town','base',[1565,1210],(-132,-8))
    poi('B05','Промкомплекс',[1980,210],'industrial','base',[2010,300],(-245,32))
    poi('B06','Престижная база',[1905,955],'elite','base',[1945,995],(-155,6),optional=True,property_type='unconfirmed')
    poi('P01','Объявление',[490,1250],'village',offset=(-165,-12))
    poi('P02','Дом и двор деда',[580,1375],'village',attach=[650,1410],offset=(-204,5),interior=True,van_repair_parts_in_yard=True)
    poi('P03','Аптека',[710,1370],'village',attach=[650,1410],offset=(18,22),interior=True)
    poi('P04','Теневая приёмка',[1170,2000],'transition',offset=(-245,5),interior=True)
    poi('P05','Автомастерская',[2030,1710],'residential',attach=[1990,1770],offset=(17,30),interior=True)
    poi('P06','Бар',[1900,2080],'residential',attach=[1840,2030],offset=(16,-15),interior=True)
    poi('P07','Притон',[2090,1940],'residential',attach=[1995,2010],offset=(16,8),interior=True)
    poi('P08','Больница',[2070,1340],'old_town',attach=[1940,1410],offset=(14,25),interior=False,landmark='cross')
    poi('P09','Встреча C03',[1570,1290],'old_town','meeting',[1565,1210],(-148,-13),meeting_role='main')
    poi('P09-2','Встреча: запасная',[2160,1160],'old_town','meeting',[2170,1250],(18,0),meeting_role='backup')
    poi('P09-3','Встреча: запасная',[1600,570],'old_town','meeting',[1650,510],(-180,-14),meeting_role='backup')
    poi('P10','Полиция',[1430,840],'old_town',attach=[1520,820],offset=(-180,0),interior='unconfirmed',arrest_spawn='outside')
    poi('P11','Банкомат',[1735,1130],'old_town','atm',[1700,1090],(15,-14))
    poi('P11-2','Банкомат',[1810,1960],'residential','atm',[1870,1910],(-84,-13))
    poi('P11-3','Банкомат',[1820,790],'old_town','atm',[1830,830],(-84,-12))
    poi('P12','Стоянка эвакуатора',[1240,410],'old_town',attach=[1210,350],offset=(-228,-9))
    poi('P13','Озеро: доступ',[918,1140],'village','water_access',[800,1160],(-52,25))
    poi('P13-2','Река: доступ',[1150,1460],'village','water_access',[1150,1450],(14,-14))
    poi('P13-3','Канал: спуск',[1770,653],'old_town','water_access',[1750,740],(18,27),van_entry=True,exit_guaranteed=False)
    poi('P13-4','Мусорки',[1600,1890],'residential','bin',[1635,1915],(-80,-16))
    poi('P13-5','Мусорки',[1390,980],'old_town','bin',[1420,940],(-80,-16))
    poi('P14','Заброшенное депо',[1890,280],'industrial',offset=(-242,-14),interior='unconfirmed')
    poi('P15','Особняк / VIP',[2120,970],'elite',attach=[2070,1000],offset=(15,-16),interior=True)
    poi('P15-2','Особняк 2',[2050,860],'elite',attach=[2100,885],offset=(14,28),interior=True)
    poi('P16','Пост СЗ',[315,2150],'village','exit',offset=(-95,38),wanted_on_crossing=True)
    poi('P16-2','Пост СВ',[2200,2050],'residential','exit',offset=(-36,40),wanted_on_crossing=True)
    poi('P16-3','Пост Ю',[1260,270],'old_town','exit',offset=(16,-4),wanted_on_crossing=True)
    poi('CLOCK_SQUARE','Площадь / часы',[1700,1090],'old_town','landmark',offset=(-110,38))
    poi('BAD_CENTER','Центр спальника',[1870,1910],'residential','reference',offset=(15,32))
    poi('BAD_BLOCK','Ближайший двор',[1625,1940],'residential','reference',[1635,1915],(-140,-4))
    poi('BAD_BLOCK_2','Жилой двор 2',[1930,2050],'residential','reference',[1995,2010])
    poi('BAD_BLOCK_3','Жилой двор 3',[2070,1810],'residential','reference',[1990,1770])
    poi('BAD_BLOCK_4','Жилой двор 4',[1720,1670],'residential','reference',[1790,1580])
    poi('WATER_TOWER','Водонапорная башня',[550,1840],'village','landmark',[450,1790],(-180,-22))
    poi('CHIMNEY','Труба',[2040,220],'industrial','landmark',[2090,235],(16,0))
    for p in points:
        if p['category']=='base':
            p.update(team_shared=True,retained_after_move=True,interior=True,access_reserve_m=[20,25],door_clearance_target_m=2.4)
    lake=[[938,1210],[963,1250],[1008,1240],[1040,1200],[1080,1170],[1075,1110],[1040,1070],[990,1060],[948,1090],[928,1150]]
    river=smooth([[1320,2280],[1350,2180],[1280,2020],[1360,1850],[1280,1660],[1210,1530],[1140,1380],[1015,1250],[1000,1200]])
    river2=smooth([[1020,1080],[1100,1040],[1190,900],[1260,820],[1320,730],[1400,650]])
    canal=smooth([[1400,650],[1680,640],[1980,590],[2210,640],[2330,730]])
    water=[dict(id='LAKE',kind='lake',name_ru='Малое озеро',polygon_m=lake),
           dict(id='RIVER_N',kind='river',name_ru='Река',centerline_m=river,width_m=15),
           dict(id='RIVER_S',kind='river',name_ru='Река',centerline_m=river2,width_m=16),
           dict(id='CANAL',kind='concrete_canal',name_ru='Открытый бетонный канал',centerline_m=canal,width_m=24,wet_width_m=6,depth_target_m=3,banks='steep_concrete',bed='uneven_silt_and_concrete',van_entry_point='P13-3',short_tunnel_road_ids=['O_EAST_AVENUE','O_SOUTH_ARC'])]
    exits=[]
    for id,post,end,kind,road_id in [('NW','P16',[245,2140],'landslide','EXIT_NW'),('NE','P16-2',[2260,2100],'destroyed_bridge','EXIT_NE'),('S','P16-3',[1230,190],'landslide','EXIT_S')]:
        p=next(p['position_m'] for p in points if p['id']==post)
        ln=length(p,end); ux,uy=(end[0]-p[0])/ln,(end[1]-p[1])/ln
        barriers=[]
        for side in (-1,1):
            local=[[-22,22],[8,15],[ln-15,17],[ln+20,28],[ln+160,35],[ln+160,115],[ln+70,92],[ln+5,105],[-25,77]]
            barriers.append([[round(p[0]+u*ux-side*v*uy,3),round(p[1]+u*uy+side*v*ux,3)] for u,v in local])
        exits.append(dict(id=id,post_id=post,dead_end_m=end,dead_end_type=kind,road_id=road_id,return_via_post_only=True,blocks_foot_bypass=True,barrier_materials=['steep_hills','dense_forest','rock_scarp'],barrier_polygons_m=barriers,barrier_height_target_m=22,barrier_width_m=55))
    hills=[dict(id='HILL_W',center_m=[380,770],radii_m=[230,390],height_target_m=70),dict(id='HILL_SW',center_m=[630,420],radii_m=[220,170],height_target_m=50),dict(id='HILL_N',center_m=[980,2250],radii_m=[150,95],height_target_m=35),dict(id='HILL_ELITE',center_m=[2010,950],radii_m=[145,180],height_target_m=42)]
    return dict(schema_version='2.0',title_ru='VOLUNTEERS ONLY — план карты R01 (v02)',specification=dict(path='docs/CITY_MAP_REFERENCE_SPEC.md',revision='1.1',date='2026-10-04'),
                coordinates=dict(unit='metre',origin='bottom-left of 2400 x 2400 reference frame',x='east',y='north',unity_mapping='(x, terrain_height, y)'),
                boundary=dict(polygon_m=boundary,barrier='steep hills and dense forest; no invisible walls',barrier_band_m=45),districts=districts,road_classes=classes,roads=roads,points=points,water=water,exits=exits,hills=hills,
                railway=dict(polyline_m=smooth(railpts),from_point='B01',to_point='P14',service_road_id='RAIL_SERVICE',active_trains=False),
                sightline=dict(from_point='B01',to_point='CHIMNEY',chimney_height_target_m=85,clearance_reserve_width_m=25,status='proposed; check with player camera in grey-box'),
                field_parcels_m=[[[785,1570],[910,1570],[1010,1460],[875,1420]],[[860,1330],[915,1400],[1100,1355],[1030,1270]],[[760,1140],[875,1150],[914,1030],[850,985]],[[580,1970],[470,2020],[450,2130],[580,2150]]],
                planning_notes_ru=['Геометрия, размеры зданий и высоты — предложение v02, не новая игровая механика.','Открытый мир с начала; сюжетных ворот нет. Парковка свободная.','Поля входят в сельскую среду; элитка — вложенная часть города без двойного счёта.','План не подтверждает уклоны, физику, времена реальной поездки или видимость трубы.'],
                provenance=dict(brief='req_map_plan_v02.md',prior_drafts=['gpt_xhigh/map_plan_v01','fable_xhigh/map_plan_v01'],reuse='presentation and Dijkstra analysis concept; separate transition branches; new authored geometry'))


def v03_mesh():
    """Continuous, orientation-preserving affine cells keep shared boundaries exact."""
    s=1/math.sqrt(1.4)
    xs=[0,1100,2400]; ys=[0,1400,2400]
    source=[[[x,y] for x in xs] for y in ys]
    target=[[[0,y*s],[1100*s,y*s],right] for y,right in
            zip(ys,([1970,150],[1970,1400*s],[2220,2118]))]
    triangles=[]
    for j in range(2):
        for i in range(2):
            for indices in (((j,i),(j,i+1),(j+1,i+1)),((j,i),(j+1,i+1),(j+1,i))):
                triangles.append(([source[y][x] for y,x in indices],[target[y][x] for y,x in indices]))
    return triangles


def v03_point(p):
    for src,dst in v03_mesh():
        a,b,c=src; x,y=p
        det=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        u=((x-a[0])*(c[1]-a[1])-(y-a[1])*(c[0]-a[0]))/det
        v=((b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]))/det
        if min(u,v,1-u-v)>=-1e-8:
            return [round(dst[0][k]+u*(dst[1][k]-dst[0][k])+v*(dst[2][k]-dst[0][k]),6) for k in (0,1)]
    # Terrain barrier shoulders can extend beyond the authored reference frame.
    return [round(p[k]/math.sqrt(1.4),6) for k in (0,1)]


def v03_line(points,closed=False):
    mesh_edges=[(a,b) for src,_ in v03_mesh() for a,b in zip(src,src[1:]+src[:1])]
    result=[]
    for a,b in zip(points,points[1:]+([points[0]] if closed else [])):
        cuts=[(0,a)]
        for c,d in mesh_edges:
            hit=crossing(a,b,c,d)
            if hit and 1e-8<hit[1]<1-1e-8:
                cuts.append((hit[1],hit[0]))
        for _,p in sorted(cuts):
            q=v03_point(p)
            if not result or length(result[-1],q)>1e-5:
                result.append(q)
    if not closed:
        result.append(v03_point(points[-1]))
    return result


def seed_v03():
    source_path=ROOT/'MAP_PLAN_R01_v02.json'
    data=json.loads(source_path.read_text(encoding='utf-8'))
    comparison={d['id']:dict(area_m2=d['area_m2'],share_percent=d['share_percent']) for d in data['districts']}
    old_res=[b for b in data['building_masses'] if b['district_id']=='residential']
    comparison['residential'].update(building_count=len(old_res),footprint_m2=sum(area(b['polygon_m']) for b in old_res))
    for key in ('road_graph','metrics','validation','water_crossings'):
        data.pop(key,None)
    for key in ('road_crossings','water_bridges'):
        data['railway'].pop(key,None)
    data['building_masses']=[b for b in data['building_masses'] if b['district_id']!='residential']
    original_footprints={b['id']:b['polygon_m'] for b in data['building_masses']}
    data['microdistricts']=[]
    def transform(obj):
        if isinstance(obj,list):
            for item in obj: transform(item)
        elif isinstance(obj,dict):
            for key,value in list(obj.items()):
                if key in ('position_m','center_m','dead_end_m'):
                    obj[key]=v03_point(value)
                elif key in ('polygon_m','yard_polygon_m'):
                    obj[key]=v03_line(value,True)
                elif key in ('polyline_m','centerline_m'):
                    obj[key]=v03_line(value)
                elif key in ('field_parcels_m','barrier_polygons_m'):
                    obj[key]=[v03_line(poly,True) for poly in value]
                elif key=='radii_m':
                    obj[key]=[round(v/math.sqrt(1.4),3) for v in value]
                else:
                    transform(value)
    transform(data)
    for b in data['building_masses']:
        # Mesh cuts can introduce extra vertices; retain full facade dimensions.
        corners=original_footprints[b['id']]
        sides=[v03_line([corners[i],corners[(i+1)%4]]) for i in range(4)]
        lengths=[sum(length(a,z) for a,z in zip(side,side[1:])) for side in sides]
        b['width_m']=round((lengths[0]+lengths[2])/2,3)
        b['depth_m']=round((lengths[1]+lengths[3])/2,3)
    data['revision']='v03'
    data['title_ru']='VOLUNTEERS ONLY — план карты R01 (v03)'
    data['coordinates']['origin']='bottom-left of 2160 x 2160 metre reference frame'
    data['comparison_v02']=comparison
    data['provenance']=dict(brief='req_map_plan_v03.md',source='MAP_PLAN_R01_v02.json',
        source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        method='continuous piecewise-affine compaction; rebuilt dense residential footprints',
        owner_decisions_date='2026-10-04',reproducible_v02='--revision v02; original seed retained')
    for d in data['districts']:
        if d['id']=='residential': d['notes_ru']='Плотные микрорайоны: длинные 9-, 12-, 16-этажные пластины, несколько башен, редкие 4–5-этажные дома; тесные дворы.'
        if d['id']=='old_town': d['notes_ru']='Уменьшенный исторический город; кривые улицы, площадь с часами, семь особняков на вложенном холме.'
    data['planning_notes_ru'][0]='Геометрия, размеры зданий и высоты — предложение v03 по решениям Феди от 04.10.2026; не новая игровая механика.'
    dense_residential(data)
    return data


def dense_residential(data):
    """Pack real rectangles with narrow clearances; never force road collisions."""
    v04=data.get('revision')=='v04'
    rng=random.Random(30103)
    district=next(d['polygon_m'] for d in data['districts'] if d['id']=='residential')
    out=data['building_masses']; grid={}; cell=80; reserved_yards=[]
    def cells(poly,pad=0):
        return [(x,y) for x in range(math.floor((min(p[0] for p in poly)-pad)/cell),math.floor((max(p[0] for p in poly)+pad)/cell)+1)
                      for y in range(math.floor((min(p[1] for p in poly)-pad)/cell),math.floor((max(p[1] for p in poly)+pad)/cell)+1)]
    segments=[]; roadgrid={}; through_indices=set()
    for r in data['roads']:
        for a,b in zip(r['polyline_m'],r['polyline_m'][1:]):
            i=len(segments); segments.append((a,b,r['width_m']/2+3))
            if not r['id'].startswith('ACCESS_'): through_indices.add(i)
            for key in cells([a,b],r['width_m']/2+3): roadgrid.setdefault(key,set()).add(i)
    waters=[(a,b,w['width_m']/2+8) for w in data['water'] if 'centerline_m' in w for a,b in zip(w['centerline_m'],w['centerline_m'][1:])]
    rail=list(zip(data['railway']['polyline_m'],data['railway']['polyline_m'][1:]))
    def register(b):
        for key in cells(b['polygon_m'],8): grid.setdefault(key,set()).add(len(out)-1)
    for i,b in enumerate(out):
        for key in cells(b['polygon_m'],8): grid.setdefault(key,set()).add(i)
    def polygon_gap(a,b):
        # Separating-axis test with an eight-metre empty interval between blocks.
        for poly in (a,b):
            for p,q in zip(poly,poly[1:]+poly[:1]):
                nx,ny=q[1]-p[1],p[0]-q[0]; norm=math.hypot(nx,ny)
                aa=[x*nx+y*ny for x,y in a]; bb=[x*nx+y*ny for x,y in b]
                if max(aa)+8*norm<=min(bb) or max(bb)+8*norm<=min(aa): return True
        return False
    def hits_segment(poly,a,b,gap):
        if inside(a,poly) or inside(b,poly): return True
        for c,d in zip(poly,poly[1:]+poly[:1]):
            if crossing(a,b,c,d): return True
            if min(projection(c,a,b)[0],projection(d,a,b)[0],projection(a,c,d)[0],projection(b,c,d)[0])<gap: return True
        return False
    def add(x,y,w,h,angle,floors,kind='slab',court=None):
        if v04 and sum(b['district_id']=='residential' and b['kind']==kind for b in out)>=(3 if kind=='tower' else 75): return False
        poly=rectangle(x,y,w,h,angle)
        if not all(inside(p,district) for p in poly): return False
        if any(not polygon_gap(poly,yard) for yard in reserved_yards): return False
        if any(crossing(a,b,c,d) for a,b in zip(poly,poly[1:]+poly[:1]) for c,d in zip(district,district[1:]+district[:1])): return False
        near=set().union(*(roadgrid.get(key,set()) for key in cells(poly,12)))
        if any(hits_segment(poly,*segments[i]) for i in near): return False
        if any(hits_segment(poly,a,b,gap) for a,b,gap in waters if min(length([x,y],a),length([x,y],b))<150): return False
        if any(hits_segment(poly,a,b,10) for a,b in rail if min(length([x,y],a),length([x,y],b))<150): return False
        for p in data['points']:
            if p['district_id']!='residential': continue
            reserve=18 if p['category']=='base' else 10
            if inside(p['position_m'],poly) or min(projection(p['position_m'],a,b)[0] for a,b in zip(poly,poly[1:]+poly[:1]))<reserve: return False
        neighbors=set().union(*(grid.get(key,set()) for key in cells(poly,8)))
        if any(not polygon_gap(poly,out[i]['polygon_m']) for i in neighbors): return False
        b=dict(id=f'{"R04" if v04 else "R03"}_{sum(v["district_id"]=="residential" for v in out)+1:03d}',district_id='residential',kind=kind,floors=floors,
               center_m=[round(x,3),round(y,3)],width_m=w,depth_m=h,polygon_m=poly,courtyard_id=court)
        out.append(b); register(b)
        return b
    # Four named gameplay courtyards plus staggered infill courts between streets.
    centers=[(v03_point(p),a) for p,a in [([1625,1940],12),([1930,2050],-14),([2070,1810],24),([1720,1670],-8)]]
    centers += [([x,y],rng.choice([12,-14,24,-8])) for y in range(1320,1980,125) for x in range(1190,2000,125) if inside([x,y],district)]
    if v04:
        centers=[(p,a) for p,a in [([1625,1940],12),([1930,2050],-14),([2070,1810],24),([1720,1670],-8)]]
        centers += [([x,y],rng.choice([12,-14,24,-8])) for y in range(1530,2240,170) for x in range(1420,2260,170) if inside([x,y],district)]
    courts=[]
    for n,((x,y),angle) in enumerate(centers):
        cid=f'MB03_{n+1:02d}'; ids=[]; ca,sa=math.cos(math.radians(angle)),math.sin(math.radians(angle))
        yard=rectangle(x,y,60 if v04 else 36,44 if v04 else 28,angle)
        if not all(inside(p,district) for p in yard): continue
        near=set().union(*(roadgrid.get(key,set()) for key in cells(yard,12))) & through_indices
        if any(hits_segment(yard,*segments[i]) for i in near): continue
        neighbors=set().union(*(grid.get(key,set()) for key in cells(yard,8)))
        if any(not polygon_gap(yard,out[i]['polygon_m']) for i in neighbors): continue
        if any(not polygon_gap(yard,p) for p in reserved_yards): continue
        layout=[(0,44,86,15,0),(0,-44,86,15,0),(-59,0,60,15,90),(59,0,60,15,90)] if v04 else [(0,31,76,14,0),(0,-31,76,14,0),(-52,0,48,14,90),(52,0,48,14,90)]
        for dx,dy,w,h,rot in layout:
            b=add(x+dx*ca-dy*sa,y+dx*sa+dy*ca,w,h,angle+rot,rng.choice([9,9,12,12,16] if v04 else [9,12,16]),court=cid)
            if b: ids.append(b['id'])
        if ids:
            reserved_yards.append(yard)
            courts.append(dict(id=cid,center_m=[x,y],angle=angle,yard_polygon_m=yard,building_ids=ids))
    # A few taller point towers are legible above the predominantly slab skyline.
    minx,maxx=min(p[0] for p in district),max(p[0] for p in district)
    miny,maxy=min(p[1] for p in district),max(p[1] for p in district)
    for _ in range(1500):
        if sum(b['kind']=='tower' for b in out)>=(3 if v04 else 5): break
        add(rng.uniform(minx,maxx),rng.uniform(miny,maxy),22,22,rng.choice([12,-14,24]),rng.choice([20,22] if v04 else [18,20,22]),'tower')
    for _ in range(6500):
        x,y=rng.uniform(minx,maxx),rng.uniform(miny,maxy)
        if not inside([x,y],district): continue
        near=set().union(*(roadgrid.get(key,set()) for key in cells([[x,y]],110)))
        if not near: continue
        best=min(near,key=lambda i:projection([x,y],*segments[i][:2])[0])
        if projection([x,y],*segments[best][:2])[0]>110: continue
        a,b,_=segments[best]; angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
        # Infill follows the local street; no map-wide rectangular street grid.
        add(x,y,rng.choice([60,72,84,96]),rng.choice([13,14,16]),angle,rng.choices([9,12,16],[4,5,1])[0] if v04 else rng.choices([4,5,9,12,16],[1,1,7,8,7])[0])
    data['microdistricts']=courts


def build_graph(data):
    """Split every same-level road intersection, including POI access branches."""
    segments=[]
    for r in data['roads']:
        for a,b in zip(r['polyline_m'],r['polyline_m'][1:]):
            if length(a,b)>1e-6:
                segments.append(dict(road=r,a=a,b=b,cuts=[(0,a),(1,b)]))
    for i,s in enumerate(segments):
        a,b=s['a'],s['b']
        for t in segments[i+1:]:
            if (t['road']['id'] in s['road'].get('grade_separated_road_ids', []) or
                    s['road']['id'] in t['road'].get('grade_separated_road_ids', [])):
                continue
            c,d=t['a'],t['b']
            if max(a[0],b[0])+1e-6<min(c[0],d[0]) or max(c[0],d[0])+1e-6<min(a[0],b[0]) or max(a[1],b[1])+1e-6<min(c[1],d[1]) or max(c[1],d[1])+1e-6<min(a[1],b[1]):
                continue
            hit=crossing(a,b,c,d)
            if hit:
                p,u,v=hit
                s['cuts'].append((u,p)); t['cuts'].append((v,p))
    # Explicit POI/dead-end vertices, even in the middle of a sampled segment.
    for p in [x['position_m'] for x in data['points']]+[x['dead_end_m'] for x in data['exits']]:
        best=min(((*projection(p,s['a'],s['b']),i) for i,s in enumerate(segments)),key=lambda q:q[0])
        if best[0]>0.02:
            raise ValueError(f'POI is disconnected from roads: {p}, gap={best[0]}')
        segments[best[3]]['cuts'].append((best[2],best[1]))
    nodes=[]; edges=[]; lookup={}
    def node(p):
        key=(round(p[0],3),round(p[1],3))
        if key not in lookup:
            lookup[key]=f'N{len(nodes):04d}'
            nodes.append(dict(id=lookup[key],position_m=list(key)))
        return lookup[key]
    for s in segments:
        cuts=sorted(s['cuts'])
        for (_,a),(_,b) in zip(cuts,cuts[1:]):
            u,v=node(a),node(b)
            if u==v:
                continue
            r=s['road']
            edges.append(dict(id=f'E{len(edges):04d}',from_node=u,to_node=v,road_id=r['id'],**{'class':r['class']},width_m=r['width_m'],length_m=round(length(a,b),6),polyline_m=[a,b],bridge=False,tunnel=False,bidirectional=True,walkable=True,van_access=r['class']!='passage'))
    data['road_graph']=dict(nodes=nodes,edges=edges,intersection_rule='all same-level crossings split into shared nodes; railway crossings are marked separately')
    for p in data['points']:
        p['road_node_id']=min(nodes,key=lambda n:length(n['position_m'],p['position_m']))['id']
    for e in data['exits']:
        e['dead_end_node_id']=min(nodes,key=lambda n:length(n['position_m'],e['dead_end_m']))['id']
    # Road/water structures; tunnels describe the water passage BELOW the road.
    structures=[]
    for r in data['roads']:
        if r['id'].startswith('ACCESS_'):
            continue
        for w in data['water']:
            if 'centerline_m' not in w:
                continue
            for a,b in zip(r['polyline_m'],r['polyline_m'][1:]):
                for c,d in zip(w['centerline_m'],w['centerline_m'][1:]):
                    hit=crossing(a,b,c,d)
                    if hit and not any(x['road_id']==r['id'] and x['water_id']==w['id'] and length(x['position_m'],hit[0])<8 for x in structures):
                        p=hit[0]; l=length(a,b); ux,uy=(b[0]-a[0])/l,(b[1]-a[1])/l
                        wl=length(c,d); sine=abs(ux*(d[1]-c[1])/wl-uy*(d[0]-c[0])/wl)
                        half=(w['width_m']+12)/max(.2,sine)/2
                        tunnel=r['id'] in w.get('short_tunnel_road_ids',[])
                        structures.append(dict(id=f'S{len(structures)+1:02d}',road_id=r['id'],water_id=w['id'],position_m=p,deck_axis_m=[[p[0]-ux*half,p[1]-uy*half],[p[0]+ux*half,p[1]+uy*half]],kind='short_canal_tunnel' if tunnel else 'bridge',tunnel_carrier='water_below_road' if tunnel else None))
    for edge in edges:
        mid=[sum(p[k] for p in edge['polyline_m'])/2 for k in (0,1)]
        for s in structures:
            if edge['road_id']==s['road_id'] and projection(mid,*s['deck_axis_m'])[0]<1.5:
                edge['bridge']=s['kind']=='bridge'; edge['tunnel']=s['kind']=='short_canal_tunnel'; edge['structure_id']=s['id']
                if edge['tunnel']:
                    edge['tunnel_carrier']='water_below_road'
    data['water_crossings']=structures
    rail=data['railway']; rail['road_crossings']=[]; rail['water_bridges']=[]
    for a,b in zip(rail['polyline_m'],rail['polyline_m'][1:]):
        for r in data['roads']:
            for c,d in zip(r['polyline_m'],r['polyline_m'][1:]):
                hit=crossing(a,b,c,d)
                if hit and not any(length(hit[0],p['position_m'])<4 for p in rail['road_crossings']):
                    rail['road_crossings'].append(dict(position_m=hit[0],road_id=r['id'],kind='level_crossing'))
        for w in data['water']:
            line=w.get('centerline_m',[])
            for c,d in zip(line,line[1:]):
                hit=crossing(a,b,c,d)
                if hit and not any(length(hit[0],p['position_m'])<4 for p in rail['water_bridges']):
                    rail['water_bridges'].append(dict(position_m=hit[0],water_id=w['id']))


def shortest(data,start,end,blocked=None,mode='van'):
    g=data['road_graph']; adj={n['id']:[] for n in g['nodes']}
    for e in g['edges']:
        if mode=='van' and not e['van_access']:
            continue
        u,v=e['from_node'],e['to_node']
        if blocked in (u,v):
            continue
        adj[u].append((v,e['length_m'],e['id'])); adj[v].append((u,e['length_m'],e['id']))
    queue=[(0,start)]; costs={start:0}; prev={}
    while queue:
        cost,u=heapq.heappop(queue)
        if cost!=costs[u]:
            continue
        if u==end:
            route=[]
            while u!=start:
                u,e=prev[u]; route.append(e)
            return cost,list(reversed(route))
        for v,w,e in adj[u]:
            alt=cost+w
            if alt<costs.get(v,math.inf):
                costs[v]=alt; prev[v]=(u,e); heapq.heappush(queue,(alt,v))
    return math.inf,[]


def buildings(data):
    """Deterministic footprints follow road tangents; no arbitrary street grid."""
    rng=random.Random(20102); out=[]; plots=[]
    district={d['id']:d for d in data['districts']}
    segments=[(a,b,r['width_m']/2) for r in data['roads'] for a,b in zip(r['polyline_m'],r['polyline_m'][1:])]
    waters=[(a,b,w['width_m']/2) for w in data['water'] if 'centerline_m' in w for a,b in zip(w['centerline_m'],w['centerline_m'][1:])]
    def allowed(poly,dist,gap=3):
        if not all(inside(p,district[dist]['polygon_m']) for p in poly):
            return False
        if dist=='old_town' and any(inside(p,district['elite']['polygon_m']) for p in poly):
            return False
        cx=sum(p[0] for p in poly)/4; cy=sum(p[1] for p in poly)/4
        # Corner samples alone miss roads cutting through long slab footprints.
        for a,b,w in segments:
            if inside(a,poly) or any(crossing(a,b,c,d) for c,d in zip(poly,poly[1:]+poly[:1])):
                return False
        for p in poly+[[cx,cy]]:
            if any(projection(p,a,b)[0]<w+gap for a,b,w in segments):
                return False
            if any(projection(p,a,b)[0]<w+7 for a,b,w in waters):
                return False
            if any(inside(p,w['polygon_m']) for w in data['water'] if 'polygon_m' in w):
                return False
        if any(length([cx,cy],p['position_m'])<34 for p in data['points']):
            return False
        if any(length([cx,cy],b['center_m'])<max(b['width_m'],b['depth_m'])/2+max(length(poly[0],poly[1]),length(poly[1],poly[2]))/2+8 for b in out):
            return False
        return True
    def add(x,y,w,h,angle,dist,kind,floors,force=False):
        poly=rectangle(x,y,w,h,angle)
        if force or allowed(poly,dist):
            out.append(dict(id=f'BLD{len(out)+1:03d}',district_id=dist,kind=kind,floors=floors,center_m=[round(x,3),round(y,3)],width_m=w,depth_m=h,polygon_m=poly))
            return True
        return False
    # Three intentionally different large courtyard groupings plus edge slabs.
    blocks=[dict(id='MB01',center_m=[1595,1980],radius_m=110,angle=12),dict(id='MB02',center_m=[1940,2070],radius_m=110,angle=-14),dict(id='MB03',center_m=[2030,1820],radius_m=130,angle=24),dict(id='MB04',center_m=[1760,1690],radius_m=110,angle=-8)]
    for block in blocks:
        x,y=block['center_m']; a=block['angle']
        block['yard_polygon_m']=rectangle(x,y,145,115,a)
        for dx,dy,w,h,rot in [(-100,0,105,18,90),(90,0,115,19,90),(0,95,130,18,0),(0,-95,115,18,0)]:
            ca,sa=math.cos(math.radians(a)),math.sin(math.radians(a))
            add(x+dx*ca-dy*sa,y+dx*sa+dy*ca,w,h,a+rot,'residential','slab',rng.choice([4,5]))
    for r in data['roads']:
        if r['id'].startswith(('ACCESS_','EXIT_','ELITE_')) or r['class']=='dirt_shortcut':
            continue
        line=r['polyline_m']; total=0; next_at=25
        for a,b in zip(line,line[1:]):
            seg=length(a,b)
            while next_at<=total+seg:
                t=(next_at-total)/seg; x,y=a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t
                angle=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))
                for side in (-1,1):
                    dist=next((d['id'] for d in data['districts'] if d['id'] in ('village','old_town','residential') and inside([x,y],d['polygon_m'])),None)
                    if dist is None:
                        continue
                    setback={'village':36,'old_town':24,'residential':66}[dist]
                    px=x-side*(b[1]-a[1])/seg*setback; py=y+side*(b[0]-a[0])/seg*setback
                    if dist=='village':
                        if add(px,py,18,12,angle,'village','rural_house',1):
                            plots.append(dict(polygon_m=rectangle(px,py,44,52,angle),kind='rural_plot'))
                    elif dist=='old_town':
                        add(px,py,rng.randrange(19,35),rng.randrange(13,22),angle,'old_town','historic_house',rng.choice([3,4,5]))
                    else:
                        add(px,py,rng.randrange(75,115),18,angle,'residential','slab',rng.choice([4,5]))
                next_at+=rng.randrange(45,75)
            total+=seg
    # Elite gardens, seven mansions and exactly two expensive residential blocks.
    mansions=[(1895,890,20),(1970,895,-10),(2010,930,5),(2050,860,15),(2120,970,-5),(2030,1050,10),(1905,955,10)]
    for i,(x,y,a) in enumerate(mansions):
        add(x,y,24,18,a,'elite','mansion',2,True)
        plots.append(dict(id=f'MANSION_{i+1}',polygon_m=rectangle(x,y,53,46,a),kind='elite_garden',accessible=i in (3,4)))
    add(1907,1048,45,24,-12,'elite','expensive_block',4,True)
    add(2130,1055,42,23,25,'elite','expensive_block',4,True)
    for x,y in [(1545,2150),(2210,1830),(1840,1625)]:
        add(x,y,28,26,8,'residential','tower',9,True)
    for x,y,w,h,a in [(1780,275,80,30,6),(1920,398,55,30,10),(1990,215,70,40,-6),(2095,340,65,28,-30),(1740,375,46,28,12)]:
        add(x,y,w,h,a,'industrial','workshop',2,True)
    data['building_masses']=out; data['plots']=plots; data['microdistricts']=blocks


def analyse(data):
    v03=data.get('revision')=='v03'
    v04=data.get('revision') in ('v04','v05')
    g=data['road_graph']; points={p['id']:p for p in data['points']}; districts={d['id']:d for d in data['districts']}
    total=area(data['boundary']['polygon_m'])
    for d in data['districts']:
        d['area_m2']=round(area(d['polygon_m']),2); d['share_percent']=round(d['area_m2']/total*100,3)
    pairs=[('B01','P03'),('B01','P02'),('B01','CLOCK_SQUARE'),('B02','BAD_CENTER'),('B02','P04'),('B03','BAD_BLOCK'),('B04','P09'),('CLOCK_SQUARE','B05'),('B01','P01'),('B01','BAD_CENTER')]
    routes=[]
    for a,b in pairs:
        d,edges=shortest(data,points[a]['road_node_id'],points[b]['road_node_id'])
        routes.append(dict(from_id=a,to_id=b,length_m=round(d,2),van_60_seconds=round(d/ (60000/3600),2),van_90_seconds=round(d/(90000/3600),2),walk_5_minutes=round(d/(5000/60),2),edge_ids=edges))
    checks=[]
    def check(name,ok,detail=''):
        checks.append(dict(name=name,passed=bool(ok),detail=detail))
    check('canonical IDs',all(x in {p['canonical_id'] for p in points.values()} for x in [f'B{i:02}' for i in range(1,7)]+[f'P{i:02}' for i in range(1,17)]))
    check('polygon areas cover boundary',abs(sum(d['area_m2'] for d in data['districts'] if not d['parent_id'])-total)<1)
    samples=0; failures=0
    for x in range(60,2381,20):
        for y in range(60,2381,20):
            if inside([x+.123,y+.123],data['boundary']['polygon_m']):
                samples+=1
                if sum(inside([x+.123,y+.123],d['polygon_m']) for d in data['districts'] if not d['parent_id'])!=1:
                    failures+=1
    check('district partition sampled at 20 m',failures==0,f'{samples} interior samples; {failures} gaps/overlaps')
    check('elite contained in old town',all(inside(p,districts['old_town']['polygon_m']) for p in districts['elite']['polygon_m']))
    check('all POIs in declared district',all(inside(p['position_m'],districts[p['district_id']]['polygon_m']) for p in points.values()),str([p['id'] for p in points.values() if not inside(p['position_m'],districts[p['district_id']]['polygon_m'])]))
    check('B02 and P04 separate transition branches',points['B02']['district_id']==points['P04']['district_id']=='transition' and any(r['id']=='HUT_BRANCH' for r in data['roads']) and any(r['id']=='RECEPTION_BRANCH' for r in data['roads']))
    rd={(r['from_id'],r['to_id']):r['length_m'] for r in routes}
    courtyard_routes={p['id']:shortest(data,points['B03']['road_node_id'],p['road_node_id'])[0] for p in points.values() if p['id'].startswith('BAD_BLOCK')}
    check('nearest residential block selected by graph',abs(rd['B03','BAD_BLOCK']-min(courtyard_routes.values()))<.02,str({k:round(v) for k,v in courtyard_routes.items()}))
    start_limit=400 if v03 or v04 else 450; bad_limit=1000 if v03 else 1200
    check(f'walkable start <= {start_limit} m',all(rd['B01',p]<=start_limit for p in ('P01','P02','P03')),str({p:rd['B01',p] for p in ('P01','P02','P03')}))
    check(f'distant bad district >= {bad_limit} m',all(rd[b,'BAD_CENTER']>=bad_limit for b in ('B01','B02')),str({b:rd[b,'BAD_CENTER'] for b in ('B01','B02')}))
    check('B03 and workshop distinct',points['B03']['district_id']==points['P05']['district_id']=='residential' and length(points['B03']['position_m'],points['P05']['position_m'])>100)
    old_services=('P08','P10','P09','P09-2','P09-3') if data.get('revision')=='v05' else ('P08','P10','P12','P09','P09-2','P09-3')
    check('old town services and meetings',all(points[x]['district_id']=='old_town' for x in old_services))
    check('seven mansions and two expensive blocks',sum(b['kind']=='mansion' for b in data['building_masses'])==7 and sum(b['kind']=='expensive_block' for b in data['building_masses'])==2)
    adjacency={n['id']:set() for n in g['nodes']}
    for e in g['edges']:
        adjacency[e['from_node']].add(e['to_node']); adjacency[e['to_node']].add(e['from_node'])
    seen=set(); stack=[g['nodes'][0]['id']]
    while stack:
        u=stack.pop()
        if u not in seen:
            seen.add(u); stack.extend(adjacency[u]-seen)
    check('connected road graph',len(seen)==len(g['nodes']),f'{len(seen)}/{len(g["nodes"])} nodes')
    check('road loops',len(g['edges'])-len(g['nodes'])+1>=8,f'cycle rank {len(g["edges"])-len(g["nodes"])+1}')
    check('all roads inside playable contour',all(inside(n['position_m'],data['boundary']['polygon_m']) for n in g['nodes']))
    for e in data['exits']:
        post=points[e['post_id']]['road_node_id']; end=e['dead_end_node_id']
        d,_=shortest(data,end,points['B01']['road_node_id'],blocked=post)
        check(f'exit {e["id"]}: dead end only returns via post',math.isinf(d) and len(adjacency[end])==1)
    check('bridges and short canal tunnels',sum(x['kind']=='short_canal_tunnel' for x in data['water_crossings'])>=2 and any(e['bridge'] for e in g['edges']) and any(e['tunnel'] for e in g['edges']))
    check('railway endpoints',length(data['railway']['polyline_m'][0],points['B01']['position_m'])<.01 and length(data['railway']['polyline_m'][-1],points['P14']['position_m'])<.01)
    box=[min(p[0] for p in data['boundary']['polygon_m']),min(p[1] for p in data['boundary']['polygon_m']),max(p[0] for p in data['boundary']['polygon_m']),max(p[1] for p in data['boundary']['polygon_m'])]
    check('playable extent about 2.0 km' if v03 else 'playable extent 2.0–2.5 km',all((1950<=d<=2050 if v03 else 2000<=d<=2500) for d in (box[2]-box[0],box[3]-box[1])))
    check('old town is largest',districts['old_town']['area_m2']==max(d['area_m2'] for d in data['districts']))
    collisions=[]
    for b in data['building_masses']:
        poly=b['polygon_m']
        for r in data['roads']:
            if r['id'].startswith('ACCESS_'):
                continue  # A POI access can end at the building's entrance.
            if any(inside(p,poly) for p in r['polyline_m']) or any(crossing(a,z,c,d) for a,z in zip(r['polyline_m'],r['polyline_m'][1:]) for c,d in zip(poly,poly[1:]+poly[:1])):
                collisions.append([b['id'],r['id']])
    check('building footprints clear of through roads',not collisions,str(collisions))
    if v03:
        prior=data['comparison_v02']
        for id in ('forest','village','old_town'):
            factor=prior[id]['area_m2']/districts[id]['area_m2']
            check(f'{id} area reduction',1.5<=factor<=2 if id=='old_town' else 1.35<=factor<=1.45,f'{factor:.3f}x smaller')
        res=[b for b in data['building_masses'] if b['district_id']=='residential']
        coverage=sum(area(b['polygon_m']) for b in res)/districts['residential']['area_m2']
        oldcoverage=prior['residential']['footprint_m2']/prior['residential']['area_m2']
        check('dense residential building count',len(res)>=prior['residential']['building_count']*2,f'{len(res)} vs {prior["residential"]["building_count"]}')
        check('dense residential footprint coverage',coverage>=oldcoverage*2,f'{coverage:.1%} vs {oldcoverage:.1%}')
        floors={n:sum(b['floors']==n for b in res) for n in sorted({b['floors'] for b in res})}
        check('9/12/16 storey slabs dominate; occasional 4/5; a few towers',all(floors.get(n,0)>0 for n in (4,5,9,12,16)) and sum(b['kind']=='tower' for b in res) in range(3,7) and sum(b['floors'] in (9,12,16) for b in res)>len(res)*.75,str(floors))
        check('residential masses in district',all(inside(p,districts['residential']['polygon_m']) for b in res for p in b['polygon_m']))
        check('building IDs unique',len({b['id'] for b in data['building_masses']})==len(data['building_masses']))
        overlaps=[]
        for i,b in enumerate(res):
            for c in res[i+1:]:
                if length(b['center_m'],c['center_m'])>max(b['width_m'],b['depth_m'])+max(c['width_m'],c['depth_m']): continue
                p,q=b['polygon_m'],c['polygon_m']
                if any(inside(a,q) for a in p) or any(inside(a,p) for a in q) or any(crossing(a,z,u,v) for a,z in zip(p,p[1:]+p[:1]) for u,v in zip(q,q[1:]+q[:1])):
                    overlaps.append([b['id'],c['id']])
        check('residential buildings do not overlap',not overlaps,str(overlaps))
        check('small residential courtyards',len(data['microdistricts'])>=8 and all(area(b['yard_polygon_m'])<1200 for b in data['microdistricts']),f'{len(data["microdistricts"])} courts; 36 x 28 m')
        data['residential_statistics']=dict(building_count=len(res),previous_building_count=prior['residential']['building_count'],footprint_coverage_percent=round(coverage*100,2),previous_footprint_coverage_percent=round(oldcoverage*100,2),floor_counts=floors)
    if v04:
        import map_plan_v04
        map_plan_v04.validate(data,sys.modules[__name__],check)
    # Extra isolation measure uses the nearest actual residential street node.
    resnodes=[n for n in g['nodes'] if inside(n['position_m'],districts['residential']['polygon_m'])]
    nearest_street=min(length(points['B02']['position_m'],n['position_m']) for n in resnodes)
    data['metrics']=dict(area_m2=total,bounds_m=box,extent_m=[box[2]-box[0],box[3]-box[1]],routes=routes,cycle_rank=len(g['edges'])-len(g['nodes'])+1,b02_nearest_residential_street_euclidean_m=round(nearest_street,1),timing_assumption='constant speeds, no acceleration/traffic/terrain; not measured gameplay')
    data['validation']=dict(passed=all(c['passed'] for c in checks),checks=checks)
    if not data['validation']['passed']:
        raise ValueError(json.dumps([c for c in checks if not c['passed']],ensure_ascii=False,indent=2))


class SVG:
    def __init__(self):
        self.parts=['<svg xmlns="http://www.w3.org/2000/svg" width="2400" height="2400" viewBox="0 0 2400 2400">']
    def add(self,text): self.parts.append(text)
    def shape(self,tag,**attrs):
        self.add('<'+tag+' '+' '.join(f'{k.replace("_","-")}="{html.escape(str(v),quote=True)}"' for k,v in attrs.items())+'/>')
    def line(self,pts,color,width=1,**kw):
        self.shape('polyline',points=' '.join(f'{x:.2f},{y:.2f}' for x,y in pts),fill='none',stroke=color,stroke_width=width,stroke_linecap='round',stroke_linejoin='round',**kw)
    def poly(self,pts,fill,stroke='none',width=1,**kw):
        self.shape('polygon',points=' '.join(f'{x:.2f},{y:.2f}' for x,y in pts),fill=fill,stroke=stroke,stroke_width=width,**kw)
    def rect(self,x,y,w,h,fill,**kw): self.shape('rect',x=x,y=y,width=w,height=h,fill=fill,**kw)
    def circle(self,x,y,r,fill,**kw): self.shape('circle',cx=x,cy=y,r=r,fill=fill,**kw)
    def text(self,x,y,value,size=18,color='#354b50',weight='normal',anchor='start',halo=False,**kw):
        attrs=f'font-family="Arial,DejaVu Sans,sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}"'
        # Duplicate halo layer works in ImageMagick's MSVG renderer as well.
        if halo:
            self.add(f'<text x="{x:.2f}" y="{y:.2f}" {attrs} stroke="#f7f4e9" stroke-width="5" stroke-linejoin="round">{html.escape(value)}</text>')
        self.add(f'<text x="{x:.2f}" y="{y:.2f}" {attrs}>{html.escape(value)}</text>')
    def finish(self): return '\n'.join(self.parts+['</svg>'])


def render(data):
    v03=data.get('revision')=='v03'
    v04=data.get('revision') in ('v04','v05')
    v05=data.get('revision')=='v05'
    if v05:
        import map_plan_v05
    frame=2160 if v03 else 2400
    s=SVG(); scale=1824/frame; left=70; top=210
    def xy(p): return [left+p[0]*scale,top+(frame-p[1])*scale]
    def annotation(p): return v03_point(p) if v03 else p
    def line(p,c,w=1,**kw): s.line([xy(q) for q in p],c,w,**kw)
    def poly(p,c,stroke='none',w=1,**kw): s.poly([xy(q) for q in p],c,stroke,w,**kw)
    def text(p,t,**kw): s.text(*xy(p),t,**kw)
    s.add('<title>'+html.escape(data['title_ru'])+'</title>')
    s.add('<desc>План в метрах. Иррегулярные районы, речная долина, связный граф дорог, места B01–B06 и P01–P16. Геометрия — проектное предложение.</desc>')
    s.rect(0,0,2400,2400,'#f6f3e9')
    s.text(70,80,data['title_ru'],size=44,weight='bold')
    s.text(70,125,'Лесные гряды → сельский переход → микрорайоны → исторический город',size=25,color='#718078')
    subtitle=(f'{data["metrics"]["extent_m"][0]/1000:.2f} × {data["metrics"]["extent_m"][1]/1000:.2f} км • решения Феди 04.10.2026 • метры / +Y север • источник: JSON' if v03 or v04 else '2,31 × 2,31 км • спецификация 1.1 • метры / +Y север • источник геометрии: JSON')
    s.text(70,163,subtitle,size=19,color='#718078')
    s.line([[70,184],[2330,184]],'#adb5a6',1)
    bp=data['boundary']['polygon_m']
    s.add('<defs><clipPath id="land"><polygon points="'+' '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,bp))+'"/></clipPath></defs>')
    s.add('<g clip-path="url(#land)">')
    for d in data['districts']:
        poly(d['polygon_m'],d['color'],'#9d9f8d',1)
    # Subtle peripheral terrain belt follows the irregular outer contour.
    center=[frame/2,frame/2]
    for factor in (1,.978,.954):
        contour=[[center[k]+(p[k]-center[k])*factor for k in (0,1)] for p in bp]
        line(contour+[contour[0]],'#85967d',1.2,opacity='.62')
    for h in data['hills']:
        for j,factor in enumerate((1,.78,.56,.34)):
            cx,cy=h['center_m']; rx,ry=h['radii_m']
            ring=[]
            for t in range(65):
                a=t/64*2*math.pi
                organic=1+.07*math.sin(3*a)+.04*math.cos(5*a)
                ring.append([cx+rx*factor*math.cos(a)*organic,cy+ry*factor*math.sin(a)*organic])
            line(ring,'#889b7d',1.25,opacity='.75')
    # Field parcels follow the valley rather than a rectangular urban pattern.
    for f in data['field_parcels_m']:
        poly(f,'#d0cb9c','#c3bd8d',1,opacity='.4')
        for i in range(1,9):
            t=i/9
            a=[f[0][k]*(1-t)+f[3][k]*t for k in (0,1)]; b=[f[1][k]*(1-t)+f[2][k]*t for k in (0,1)]
            line([a,b],'#b6b585',.8,opacity='.6')
    # Forest canopy symbols, kept off roads and away from the sightline reserve.
    rng=random.Random(422)
    roadseg=[(a,b) for r in data['roads'] for a,b in zip(r['polyline_m'],r['polyline_m'][1:])]
    forest=next(d for d in data['districts'] if d['id']=='forest')['polygon_m']
    for _ in range(2000):
        p=[rng.uniform(60,2350),rng.uniform(60,2350)]
        edge=min(projection(p,a,b)[0] for a,b in zip(bp,bp[1:]+bp[:1]))
        if (inside(p,forest) or edge<45) and all(projection(p,a,b)[0]>20 for a,b in roadseg):
            x,y=xy(p); r=rng.uniform(3,6)
            s.circle(x,y,r,'#829b82',opacity='.30')
            s.circle(x-2,y+2,r*.6,'#718e76',opacity='.30')
    for val in range(0,frame+1,100):
        major=val%500==0
        for a,b in (([val,0],[val,frame]),([0,val],[frame,val])):
            line([a,b],'#7b877d' if major else '#faf8ed',1.05 if major else .6,opacity='.38' if major else '.58')
    for plot in data['plots']:
        poly(plot['polygon_m'],'#b2c598' if plot['kind']=='elite_garden' else '#ddd3ad','#a9ad8f',.6,opacity='.85')
    for parcel in data.get('vegetation_parcels',[]):
        p=parcel['polygon_m']; poly(p,'#b9c69a','#98ad82',.7,opacity='.7')
        for y in range(int(min(q[1] for q in p)),int(max(q[1] for q in p)),9):
            for x in range(int(min(q[0] for q in p)),int(max(q[0] for q in p)),10):
                if inside([x,y],p): s.circle(*xy([x,y]),2.7,'#769470',opacity='.8')
    for block in data['microdistricts']:
        poly(block['yard_polygon_m'],'#acbeb5','#9eb2aa',.8,opacity='.6')
    colors={'rural_house':'#b7a085','rural_outbuilding':'#a8a486','pharmacy':'#c0b88b','historic_house':'#bca28e','slab':'#8b9aa3','tower':'#687f8b','mansion':'#efe4c5','expensive_block':'#aaa987','workshop':'#a39aa8'}
    for b in data['building_masses']:
        if v05 and any(b['id']==f.get('source_building_id') for f in data['functional_buildings']):
            continue
        color=colors[b['kind']]
        if (v03 or v04) and b['district_id']=='residential':
            color={4:'#a2aeb3',5:'#a2aeb3',9:'#8395a0',12:'#6d8492',16:'#576f81'}.get(b['floors'],'#425c70')
            # Offset shadow and floor figures distinguish the high-rise masses.
            shadow=[[p[0]+b['floors']*.65,p[1]-b['floors']*.55] for p in b['polygon_m']]
            poly(shadow,'#536772',opacity='.20')
        poly(b['polygon_m'],color,'#7d8276',.65)
        if b['kind']=='tower' or ((v03 or v04) and b['kind']=='slab'):
            text(b['center_m'],str(b['floors']),size=10 if v03 else 12,color='white',weight='bold',anchor='middle')
    if v05: map_plan_v05.draw_footprints(data,s,xy)
    for w in data['water']:
        if w['kind']=='lake':
            poly(w['polygon_m'],'#a9c9ce','#739da9',1.4)
        elif w['kind']=='concrete_canal':
            line(w['centerline_m'],'#949e99',w['width_m']*scale+4)
            line(w['centerline_m'],'#d4d4c9',w['width_m']*scale)
            line(w['centerline_m'],'#8fb9c5',w['wet_width_m']*scale)
        else:
            line(w['centerline_m'],'#739da9',w['width_m']*scale+1.2)
            line(w['centerline_m'],'#a9c9ce',w['width_m']*scale)
    for r in data['roads']:
        w=r['width_m']*scale; color=data['road_classes'][r['class']]['color']
        line(r['polyline_m'],'#999d8d',w+2)
        line(r['polyline_m'],color,w)
        if r['class']=='dirt_shortcut': line(r['polyline_m'],'#f8ecd4',1.4,stroke_dasharray='5 6')
        if r['class']=='highway': line(r['polyline_m'],'#cbd1c6',.8,stroke_dasharray='10 9')
    for st in data['water_crossings']:
        line(st['deck_axis_m'],'#436773',11)
        line(st['deck_axis_m'],'#f9f3e7',7)
        if st['kind']=='short_canal_tunnel':
            x,y=xy(st['position_m']); s.rect(x-8,y-8,16,16,'#436773',rx=2); s.text(x,y+4,'Т',size=12,color='white',anchor='middle',weight='bold')
    rail=data['railway']['polyline_m']
    line(rail,'#efece1',6); line(rail,'#747080',2.5); line(rail,'#747080',7,stroke_dasharray='2 9')
    for c in data['railway']['road_crossings']:
        s.circle(*xy(c['position_m']),3.5,'#f6f3e9',stroke='#747080',stroke_width=1)
    for c in data['railway']['water_bridges']:
        s.circle(*xy(c['position_m']),7,'none',stroke='#436773',stroke_width=2)
    if v05: map_plan_v05.draw_passages(data,s,xy)
    pts={p['id']:p for p in data['points']}
    line([pts['B01']['position_m'],pts['CHIMNEY']['position_m']],'#a99567',1.4,stroke_dasharray='10 8',opacity='.65')
    # Visible closure: two flanking terrain masses and an impassable transverse scar.
    for ex in data['exits']:
        end=ex['dead_end_m']; post=pts[ex['post_id']]['position_m']; dx,dy=end[0]-post[0],end[1]-post[1]; ln=math.hypot(dx,dy); ux,uy=dx/ln,dy/ln
        for barrier in ex['barrier_polygons_m']:
            poly(barrier,'#92a487','#72866d',1,opacity='.9')
            center=[sum(p[k] for p in barrier)/len(barrier) for k in (0,1)]
            for f in (.65,.36):
                ring=[[center[k]+(p[k]-center[k])*f for k in (0,1)] for p in barrier]
                line(ring+[ring[0]],'#6f876b',1,opacity='.7')
        scar=[[end[0]-uy*45,end[1]+ux*45],[end[0]+uy*45,end[1]-ux*45]]
        line(scar,'#865f51',10)
        if ex['dead_end_type']=='destroyed_bridge':
            line(scar,'#617c7d',7)
            line([[end[0]-ux*20,end[1]-uy*20],[end[0]-ux*6,end[1]-uy*6]],'#e9e4d1',8)
            line([[end[0]+ux*14,end[1]+uy*14],[end[0]+ux*28,end[1]+uy*28]],'#e9e4d1',8)
        else:
            for i in range(6):
                q=[scar[0][k]+(scar[1][k]-scar[0][k])*i/5 for k in (0,1)]
                poly(rectangle(*q,10,13,27*i),'#a58b70','#785d51',.6)
    s.add('</g>')
    line(bp+[bp[0]],'#71826f',2.2)
    # Exterior annotations and coordinate frame.
    for val in range(0,frame+1,500):
        x,y=xy([val,0]); s.text(x,2067,str(val),size=16,color='#819085',anchor='middle')
        x,y=xy([0,val]); s.text(57,y+5,str(val),size=16,color='#819085',anchor='end')
    s.text(70,2100,'(0; 0) • начало координат',size=17,color='#738479')
    s.text(1892,2100,'X / восток →',size=17,color='#738479',anchor='end')
    labels=[([390,790],'ЛЕСНЫЕ ХОЛМЫ','Опушка • рельеф • старые пути'),([400,1720],'ДЕРЕВНЯ','Дома, дворы и сельские дороги'),([1070,2110],'ЗАГОРОДНЫЙ','ПЕРЕХОД'),([1760,2250],'НЕБЛАГОПОЛУЧНЫЙ','СПАЛЬНИК • 4–5 этажей'),([1530,690],'СТАРЫЙ ГОРОД','Исторические улицы • 3–5 этажей'),([1880,135],'ПРОМЫШЛЕННАЯ ОКРАИНА','Депо и поздняя база'),([960,1600],'ПОЛЯ ДОЛИНЫ','Грунтовые срезки и мосты')]
    for p,t,sub in labels:
        if (v03 or v04) and t=='НЕБЛАГОПОЛУЧНЫЙ': sub='ТЕСНЫЕ ДВОРЫ • 9 / 12 / 16 ЭТАЖЕЙ'
        if v04 and t=='ДЕРЕВНЯ': t='ХУТОР'; sub='34 дома • усадьбы, сады и поля'
        x,y=xy(annotation(p)); s.text(x,y,t,size=23,weight='bold',anchor='middle',color='#5b6d63',halo=True); s.text(x,y+25,sub,size=17,anchor='middle',color='#6b7b70',halo=True)
    # The following authored callouts use v02 coordinates; geometry above is v03.
    def text(p,t,**kw): s.text(*xy(annotation(p)),t,**kw)
    text([2020,800],'ЭЛИТНЫЙ ХОЛМ',size=18,anchor='middle',weight='bold',halo=True)
    text([2020,769],'7 особняков + 2 корпуса',size=14,anchor='middle',halo=True)
    text([1010,1170],'ОЗЕРО',size=15,anchor='middle',color='#507d8a',halo=True)
    text([1310,1540],'река',size=16,color='#507d8a',halo=True)
    text([1920,550],'БЕТОННЫЙ КАНАЛ',size=16,anchor='middle',color='#507d8a',halo=True)
    text([1870,515],'Открытое русло • Т = короткий тоннель',size=13,anchor='middle',color='#507d8a',halo=True)
    text([820,825],'Старая ЖД и проезд рядом',size=17,color='#767182',halo=True)
    text([650,750],'Просвет к трубе*',size=16,color='#988454',halo=True)
    for ex,p,t in [(data['exits'][0],[230,2245],'Обвал / тупик'),(data['exits'][1],[2120,2210],'Разрушенный мост'),(data['exits'][2],[1070,150],'Обвал / тупик')]:
        x,y=xy(annotation(p)); s.text(x,y,t,size=17,color='#946756',weight='bold',halo=True); s.text(x,y+21,'Холмы и лес: пешего обхода нет',size=13,color='#946756',halo=True)
    # Compact ID labels for repeated points, full readable names in the index.
    for p in data['points']:
        if p['id'].startswith('BAD_BLOCK'):
            continue
        x,y=xy(p['position_m']); cat=p['category']; color='#ad5f4b' if cat=='base' else '#48686f'
        if cat=='base': s.rect(x-8,y-8,16,16,color,stroke='#fff9e9',stroke_width=2,rx=2)
        elif cat=='exit': s.poly([[x,y-10],[x-9,y+8],[x+9,y+8]],'#bd8b51','#fff9e9',2)
        elif cat=='water_access': s.poly([[x,y-7],[x+7,y],[x,y+7],[x-7,y]],'#61909d','#fff9e9',1.5)
        elif cat=='atm': s.rect(x-5,y-5,10,10,'#68826d',stroke='#fff9e9',stroke_width=1)
        elif cat=='meeting': s.circle(x,y,7,'#678b79',stroke='#fff9e9',stroke_width=2)
        elif p['id']=='P08':
            s.rect(x-9,y-3,18,6,'#b57065'); s.rect(x-3,y-9,6,18,'#b57065')
        elif p['id']=='CLOCK_SQUARE':
            s.circle(x,y,12,'#e6d7aa',stroke='#8e8a69',stroke_width=1.5); s.line([[x,y-7],[x,y],[x+5,y+2]],'#51665e',1.5)
        else: s.circle(x,y,5,color,stroke='#fff9e9',stroke_width=1.5)
        dx,dy=p['label_offset_px']
        label=p['id']+' '+p['name_ru'] if p['id'].startswith(('B','P0')) or p['id'] in ('P10','P12','P14') else p['id']
        if p['id'] in ('WATER_TOWER','CHIMNEY','CLOCK_SQUARE','BAD_CENTER'): label=p['name_ru']
        if cat in ('atm','bin','water_access') or p['id'].startswith('P15'): label=p['id']
        if cat=='exit': label=p['id']+' '+p['name_ru']
        if v05 and p['id'] in map_plan_v05.labelled_pois(data):
            continue
        s.text(x+dx,y+dy,label,size=18 if cat=='base' else 16,color=color,weight='bold' if cat=='base' else 'normal',halo=True)
        if math.hypot(dx,dy)>70:
            endx=x+dx+(min(len(label)*8,170) if dx<0 else 0)
            s.line([[x,y],[endx,y+dy-5]],'#8a9586',.8)
    # Carefully spaced sidebar: key, registry, measured routes and scale.
    if v05: map_plan_v05.draw_labels(data,s,xy)
    legend_start=len(s.parts)
    sx=1960; s.rect(1932,211,400,1888,'#efede2',rx=12)
    s.text(sx,250,'КАК ЧИТАТЬ ПЛАН',size=21,weight='bold')
    y=285
    for d in data['districts']:
        s.rect(sx,y-15,18,18,d['color'],stroke='#939e8b',stroke_width=.8)
        name={'forest':'Лесные холмы','village':'Хутор + поля' if v04 else 'Деревня + поля','transition':'Загородный переход','residential':'Неблагополучный спальник','old_town':'Старый город','industrial':'Промышленная окраина','elite':'Элитка, внутри старого города','fields':'Новые поля у города','transition_meadow':'Переход: городской луг'}[d['id']]
        share=f'{d["share_percent"]:.1f}%'
        s.text(sx+30,y,name,size=15 if v04 else 17); s.text(2300,y,share,size=16,color='#7d8778',anchor='end'); y+=24 if v04 else 30
    y+=18; s.line([[sx,y],[2300,y]],'#c7cabc',1); y+=37
    for id,c in data['road_classes'].items():
        s.line([[sx,y-6],[sx+43,y-6]],'#8a958a',8)
        s.line([[sx,y-6],[sx+43,y-6]],c['color'],5)
        if id=='dirt_shortcut': s.line([[sx,y-6],[sx+43,y-6]],'#fff3d9',1,stroke_dasharray='5 4')
        s.text(sx+58,y,c['name_ru'],size=16); y+=30
    for name,col,dash in [('Старая железнодорожная ветка','#747080','2 7'),('Мост / Т — тоннель канала','#436773',None)]:
        kw={'stroke_dasharray':dash} if dash else {}
        s.line([[sx,y-6],[sx+43,y-6]],col,5,**kw); s.text(sx+58,y,name,size=16); y+=30
    s.rect(sx,y-13,13,13,'#ad5f4b'); s.text(sx+20,y,'База',size=15)
    s.circle(sx+94,y-6,5,'#48686f'); s.text(sx+106,y,'Место',size=15)
    s.poly([[sx+191,y-14],[sx+183,y],[sx+199,y]],'#bd8b51'); s.text(sx+205,y,'ДПС',size=15)
    s.poly([[sx+275,y-13],[sx+282,y-6],[sx+275,y+1],[sx+268,y-6]],'#61909d'); s.text(sx+289,y,'Вода',size=15); y+=32
    y+=15; s.line([[sx,y],[2300,y]],'#c7cabc',1); y+=34
    s.text(sx,y,'ОБЪЕКТЫ И СЕРВИСЫ',size=20,weight='bold'); y+=32
    for textline in ['B01–B06   Общие базы команды','P01   Объявление у старта','P02   Двор деда и первый бусик','P03   Деревенская аптека','P04   Теневая приёмка','P05   Общественная автомастерская','P06 / P07   Бар / притон','P08   Больница — внешний ориентир','P09   Встреча C03 + 2 запасные','P10   Полицейский участок','P11   Банкоматы (3)','P12   Стоянка эвакуатора','P13   Вода (3) / мусорки (2)','P14   Депо и конец ЖД','P15   Доступные особняки (2)','P16   Посты ДПС (3)']:
        s.text(sx,y,textline,size=16); y+=28
    y+=8; s.line([[sx,y],[2300,y]],'#c7cabc',1); y+=35
    s.text(sx,y,'РАССТОЯНИЯ ПО ДОРОГАМ',size=20,weight='bold'); y+=32
    routes={(r['from_id'],r['to_id']):r for r in data['metrics']['routes']}
    for a,b,title in [('B01','P03','Вагон → аптека'),('B01','P02','Вагон → двор деда'),('B02','BAD_CENTER','Хижина → центр спальника'),('B02','P04','Хижина → приёмка')]:
        s.text(sx,y,title,size=16); y+=24; r=routes[a,b]; s.text(sx,y,f'{r["length_m"]:.0f} м  /  пешком {r["walk_5_minutes"]:.1f} мин',size=17,weight='bold',color='#728470'); y+=34
    y+=5; s.line([[sx,y],[2300,y]],'#c7cabc',1); y+=35
    s.text(sx,y,'ГРАНИЦА И КАНАЛ',size=20,weight='bold'); y+=30
    for t in ['Пост → розыск → видимый тупик.','Обратный путь — через тот же пост.','Обход закрыт холмами и густым лесом.','Канал открыт; въезд у P13-3.','Риск застрять: крутые борта,','неровное дно; эвакуатор — P12.']:
        s.text(sx,y,t,size=16); y+=25
    y+=24; s.text(sx,y,'МАСШТАБ / МЕТРЫ',size=20,weight='bold'); y+=25
    scale_step=100*scale if v03 else 76
    for i in range(4): s.rect(sx+i*scale_step,y,scale_step,10,'#577068' if i%2==0 else '#faf8ef',stroke='#81917d',stroke_width=1)
    for i in range(5): s.text(sx+i*scale_step,y+30,str(i*100),size=14,anchor='middle')
    s.text(sx,y+62,'Сетка: 100 м / крупная: 500 м',size=16)
    s.line([[2250,2053],[2250,1965]],'#4f6b62',3); s.poly([[2250,1950],[2240,1975],[2260,1975]],'#4f6b62'); s.text(2250,1940,'С',size=22,weight='bold',anchor='middle'); s.text(2250,2078,'+Y',size=16,anchor='middle')
    if v05:
        del s.parts[legend_start:]
        map_plan_v05.draw_legend(data,s,scale)
    s.line([[70,2140],[2330,2140]],'#adb5a6',1)
    columns=[(70,'01 / ДУГА И ДОЛИНА',['Лес → деревня → спальник → старый город.','Две сельские ветки: хижина B02 и приёмка P04.','Поля, мосты и проезд вдоль ЖД замыкают петли.']),
             (830,'02 / РАЗНЫЕ МЕСТА',['Гараж B03, автомастерская P05 и стоянка P12.','Больница P08 и городские встречи P09.','Элитка вложена в город: 7 особняков и 2 корпуса.']),
             (1590,'03 / ПРОЕКТНЫЙ СТАТУС',['Расстояния рассчитаны по связному графу JSON.','*Просвет к трубе — резерв для проверки в 3D.','Уклоны, физика и темп поездок требуют макета.'])]
    for x,title,lines in columns:
        s.text(x,2184,title,size=19,weight='bold')
        for i,t in enumerate(lines): s.text(x,2222+i*29,t,size=17,color='#6c7e73')
    s.text(70,2350,f'R01 / {data.get("revision","v02")} • 04.10.2026 • геометрия — предложение • все районы доступны с начала',size=16,color='#889384')
    s.text(2330,2350,'JSON → SVG → PNG',size=16,color='#889384',anchor='end')
    return s.finish()


def report(data):
    if data.get('revision')=='v05':
        import map_plan_v05
        return map_plan_v05.report(data)
    if data.get('revision')=='v04':
        import map_plan_v04
        return map_plan_v04.report(data)
    if data.get('revision')=='v03': return report_v03(data)
    m=data['metrics']; routes=m['routes']; v=data['validation']
    names={'B01':'Вагон B01','B02':'Хижина B02','B03':'Гараж B03','B04':'Дом B04','B05':'Комплекс B05','P02':'двор деда P02','P03':'аптека P03','P04':'приёмка P04','P09':'основная встреча P09','CLOCK_SQUARE':'площадь с часами','BAD_CENTER':'центр спальника','BAD_BLOCK':'ближайший жилой двор'}
    lines=['# VOLUNTEERS ONLY — R01 v02','',
           'Источник: CITY_MAP_REFERENCE_SPEC.md, ред. 1.1; конкретная геометрия — предложение планировки.',
           f'Контур: **{m["extent_m"][0]:.0f} × {m["extent_m"][1]:.0f} м**, площадь **{m["area_m2"]/1e6:.3f} км²**. Рамка 2400 × 2400 м; X — восток, Y — север, начало слева внизу.',
           'JSON — источник геометрии; обычный запуск сохраняет его правки, пересчитывает граф, SVG/PNG и этот отчёт. `--reset-data` восстанавливает авторскую v02.','',
           '| Территория | Площадь, км² | Доля |','|---|---:|---:|']
    for d in data['districts']:
        lines.append(f'| {d["name_ru"]}{" (вложена)" if d["parent_id"] else ""} | {d["area_m2"]/1e6:.3f} | {d["share_percent"]:.1f}% |')
    lines+=['','Поля долины учтены в сельской среде; элитка входит в площадь города и не суммируется повторно. Доли — приближённые ориентиры §3.2.','',
            '| Маршрут по графу | м | Бусик 60 км/ч, с | Бусик 90 км/ч, с | Пешком 5 км/ч, мин |','|---|---:|---:|---:|---:|']
    for r in routes[:8]:
        lines.append(f'| {names[r["from_id"]]} → {names[r["to_id"]]} | {r["length_m"]:.0f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["walk_5_minutes"]:.1f} |')
    rd={(r['from_id'],r['to_id']):r['length_m'] for r in routes}
    lines+=['','Время теоретическое при постоянной скорости: без разгона, трафика, поворотов и уклонов. Это не игровой замер.',
            f'Старт → объявление: {rd["B01","P01"]:.0f} м; старт → центр спальника: {rd["B01","BAD_CENTER"]:.0f} м. От B02 до ближайшей улицы спальника по прямой: {m["b02_nearest_residential_street_euclidean_m"]:.0f} м.','',
            '| Проверка спецификации / брифа | Результат |','|---|---|',
            '| Масштаб, дуга, поля и малая вода | Выполнено на плане; река задаёт границы перехода и города. |',
            '| B01 → P01/P02/P03 ≤ 450 м; B01/B02 → центр спальника ≥ 1,2 км | Все пороги пройдены по кратчайшему пути. |',
            '| B02 и P04 между деревней и спальником | Отдельный переход; две разные тупиковые сельские ветки. |',
            '| Характер застройки | Село с участками; крупные дворы и 4–5-этажные пластины; город с кривыми улицами и широкими проспектами. |',
            '| B03 / P05 / P12; P08 / P09 / P10 | Раздельные точки; размещение проверено по районным полигонам. |',
            '| Элитка и промзона | 7 особняков + 2 дорогих корпуса внутри города; B05 и P14 на промышленной окраине. |',
            '| B01–B06, P01–P16 | Все ID и экземпляры присутствуют; P09 — основная + 2 запасные. |',
            '| ЖД, срезки, мосты и канал | Непрерывная ЖД B01–P14, проезд рядом; открытый канал и 2 коротких тоннеля под дорогами. |',
            '| Вариант А / §14 | 3 поста; за каждым обвал или разрушенный мост, фланги из холмов/леса; граф не допускает возврата мимо поста. |',
            '| Оформление | SVG/PNG 2400², сетка 100/500 м, север, масштаб, русские подписи и легенда. |',
            f'| Автопроверки | {sum(c["passed"] for c in v["checks"])}/{len(v["checks"])}: площади, покрытие, POI, связность, маршруты, тупики, ЖД, мосты. |','',
            f'Граф: {len(data["road_graph"]["nodes"])} узлов, {len(data["road_graph"]["edges"])} рёбер, {m["cycle_rank"]} независимых петель; все геометрические пересечения дорог соединены.',
            'Высоты рельефа, крутые физические границы, проход каталки, обзор трубы и реальное удобство движения требуют проверки в Unity. R02–R10 и игровые системы вне задачи.',
            'Запуск: `python build_map_plan.py` (Python 3.12, только stdlib); PNG — ImageMagick 7.1.2 по пути из брифа.']
    assert len(lines)<=60
    return '\n'.join(lines)+'\n'


def report_v03(data):
    m=data['metrics']; prior=data['comparison_v02']; stats=data['residential_statistics']
    names={p['id']:p['name_ru']+' '+p['id'] for p in data['points']}
    lines=['# VOLUNTEERS ONLY — R01 v03','',
        'Основание: решения Феди 04.10.2026, req_map_plan_v03.md; остальные условия — v02 / спецификация 1.1.',
        f'Контур: **{m["extent_m"][0]:.0f} × {m["extent_m"][1]:.0f} м**, площадь **{m["area_m2"]/1e6:.3f} км²** (v02: 2305 × 2310 м, 4,708 км²).',
        'Координаты в метрах: начало слева внизу рамки 2160² м, X — восток, Y — север; изображение 2400 × 2400 пикселей.','',
        '| Территория | v02, км² / доля | v03, км² / доля | Уменьшение площади |','|---|---:|---:|---:|']
    for d in data['districts']:
        p=prior[d['id']]
        lines.append(f'| {d["name_ru"]}{" (вложена)" if d["parent_id"] else ""} | {p["area_m2"]/1e6:.3f} / {p["share_percent"]:.1f}% | {d["area_m2"]/1e6:.3f} / {d["share_percent"]:.1f}% | {p["area_m2"]/d["area_m2"]:.2f}× |')
    lines+=['','Поля входят в сельскую среду; элитка входит в старый город, повторно не суммируется.',
        f'Спальник: **{stats["building_count"]} домов вместо {stats["previous_building_count"]}**; покрытие пятнами зданий **{stats["footprint_coverage_percent"]:.1f}% вместо {stats["previous_footprint_coverage_percent"]:.1f}%**.',
        'Этажность (этажей: домов): '+', '.join(f'{k}: {v}' for k,v in stats['floor_counts'].items())+'.',
        f'Длинные пластины; малые дворы: {len(data["microdistricts"])} по 36 × 28 м; зазоры между домами от 8 м. Цифры на домах — этажи.','',
        '| Кратчайший маршрут по дорогам | м | 60 км/ч, с | 90 км/ч, с | Пешком 5 км/ч, мин |','|---|---:|---:|---:|---:|']
    for r in m['routes']:
        lines.append(f'| {names[r["from_id"]]} → {names[r["to_id"]]} | {r["length_m"]:.0f} | {r["van_60_seconds"]:.1f} | {r["van_90_seconds"]:.1f} | {r["walk_5_minutes"]:.1f} |')
    lines+=['','Время теоретическое, при постоянной скорости: без разгона, поворотов, трафика и рельефа; это не игровой замер.','',
        '| Проверка | Результат |','|---|---|',
        '| B01 → P01/P02/P03 ≤ 400 м; B01/B02 → центр спальника ≥ 1000 м | Все пороги пройдены по кратчайшим путям, включая грунтовые срезки. |',
        '| Дуга и переход | Лес → деревня → переход → спальник → старый город; B02 и P04 на отдельных ветках. |',
        '| Центральная долина | Поля, озеро, река и срезки сохранены; все районы доступны с начала. |',
        '| Старый город | Кривые улицы, площадь с часами, B04, больница, полиция, основная и две запасные встречи сохранены. |',
        '| Элитный холм | 7 особняков и 2 дорогих корпуса внутри старого города. |',
        '| ЖД / промзона / канал | Непрерывная ветка B01–P14, проезд рядом; B05 на окраине; открытый канал, мосты и 2 коротких тоннеля. |',
        '| Посты и тупики | 3 поста, видимые обвалы / разрушенный мост и фланги из леса/холмов; обратный путь по графу только через свой пост. |',
        '| Застройка | Число домов и покрытие выросли более чем вдвое; преобладают 9/12/16 этажей; наложений домов и пересечений с улицами нет. |',
        f'| Автопроверки | {sum(c["passed"] for c in data["validation"]["checks"])}/{len(data["validation"]["checks"])}; районы, POI, связность, пороги, застройка, тупики и ЖД. |','',
        f'Граф: {len(data["road_graph"]["nodes"])} узлов, {len(data["road_graph"]["edges"])} рёбер, {m["cycle_rank"]} независимых петель.',
        'Высоты, видимость трубы, физическая непроходимость границ, перенос NPC и удобство езды требуют макета и плейтеста в Unity.',
        'JSON — источник геометрии: обычный запуск сохраняет правки и пересчитывает граф, SVG, PNG и отчёт.',
        'Сборка v03: `python build_map_plan.py`; пересоздание из v02: `python build_map_plan.py --reset-data`.',
        'Сборка v02 сохранена: `python build_map_plan.py --revision v02` (явно перезапишет только выбранную v02); в этой задаче v02 не пересобиралась.',
        'Python 3.12 stdlib; PNG — ImageMagick. Файлы v02 сохранены без изменений; исходный SHA-256 записан в provenance JSON.']
    assert len(lines)<=60
    return '\n'.join(lines)+'\n'


def main():
    global STEM
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset-data',action='store_true')
    parser.add_argument('--revision',choices=('v02','v03','v04','v05'),default='v05')
    args=parser.parse_args()
    STEM='MAP_PLAN_R01_'+args.revision
    path=ROOT/(STEM+'.json')
    if path.exists() and not args.reset_data:
        data=json.loads(path.read_text(encoding='utf-8'))
    elif args.revision=='v05':
        import map_plan_v05
        data=map_plan_v05.seed(sys.modules[__name__])
    elif args.revision=='v04':
        import map_plan_v04
        data=map_plan_v04.seed(sys.modules[__name__])
    else:
        data=seed_v03() if args.revision=='v03' else seed_data()
    if data['schema_version']!='2.0': raise ValueError('Unsupported schema')
    build_graph(data)
    if 'building_masses' not in data: buildings(data)
    analyse(data)
    if args.revision=='v05':
        import map_plan_v05
        map_plan_v05.analyse(data,sys.modules[__name__])
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    svg=ROOT/(STEM+'.svg'); png=ROOT/(STEM+'.png')
    svg.write_text(render(data),encoding='utf-8'); ET.parse(svg)
    if not MAGICK.is_file(): raise FileNotFoundError(MAGICK)
    env=os.environ.copy(); env['MAGICK_TEMPORARY_PATH']=str(ROOT)
    subprocess.run([str(MAGICK),'-background','#f6f3e9',str(svg),'-strip',str(png)],check=True,cwd=ROOT,env=env,capture_output=True)
    header=png.read_bytes()[:24]
    assert header[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',header[16:24])==(2400,2400)
    (ROOT/(STEM+'_REPORT.md')).write_text(report(data),encoding='utf-8')
    print(f'OK: {len(data["validation"]["checks"])} checks, PNG 2400x2400, Python {sys.version.split()[0]}')
    for d in data['districts']: print(d['id'],round(d['share_percent'],1))
    for r in data['metrics']['routes']: print(r['from_id'],'->',r['to_id'],round(r['length_m']), 'm')


if __name__=='__main__': main()
