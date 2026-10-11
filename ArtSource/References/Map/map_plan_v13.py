#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R01 v13: Fedya's evening brief of 2026-10-05 and REF_FEDYA_v13_hamlet_forest.png.
Alley district instead of the U-court slabs; hamlet and forest per the reference;
industrial zone in the NE corner with its outfall; beach car park on the old industrial site.
Reads final v12; writes only the v13 deliverables in this folder. Run with Python -B.
"""
import copy
import hashlib
import json
import math
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
sys.dont_write_bytecode = True
import map_plan_v12 as v12
m, v7, v11 = v12.m, v12.v7, v12.v11
ROOT = m.ROOT
STEM = 'MAP_PLAN_R01_v13'
CROPS = {
    'alleys': ('Район подворотен', [456, 612, 794, 885]),
    'hamlet_forest': ('Хутор и лес по референсу Феди', [78, 255, 480, 806]),
    'industrial_carpark': ('Промзона в СВ углу · пляжная парковка на старом месте', [535, 282, 1094, 925]),
}
OUTPUTS = ({STEM+s for s in ('.json', '.svg', '.png', '_REPORT.md')} |
           {f'{STEM}_crop_{k}.png' for k in CROPS} | {'map_plan_v13.py'})
MAGICK = r'C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe'
WIDTHS = dict(v12.WIDTHS, alley=4.5, foot_lane=3.0, trail=2.0)
WALK = {'passage', 'foot_lane', 'trail'}
FENCE_HEIGHTS = {'elite_fence': 2.4, 'barbed_fence': 2.8, 'rock_scarp': 2.4, 'canal_railing': 1.1, 'dune_ridge': 1.4}
curve, rounded, oval, offset, nearest = v12.curve, v12.rounded, v12.oval, v12.offset, v12.nearest
contained, strict_overlap, simple, turn_max = v12.contained, v12.strict_overlap, v12.simple, v12.turn_max
PREVIOUS = re.compile(r'^(build_map_plan\.py|map_plan_v(0[2-9]|1[0-2])\.py|map_dressing_v12\.py|'
                      r'MAP_(PLAN|DRESSING)_R01_v(0[2-9]|1[0-2])(\.json|\.svg|\.png|_REPORT\.md))$')

# ------------------------------------------------------------------ design geometry, metres (x east, y north)
COVE_SEA = [[103, 342], [111, 327], [125, 314], [145, 304], [170, 296.5], [197, 290.5], [225, 285.5],
            [253, 280.5], [280, 275], [300, 270.6], [313.506, 267.532]]
COVE_LAND = [[109, 356], [121, 346.5], [139, 338], [162, 331], [189, 326], [217, 322], [245, 319],
             [273, 317], [298, 316.8], [316, 318], [330, 320]]
QUAY = [[984.727, 732.008], [983.2, 738.5], [983.8, 746], [986.5, 756], [991, 768], [996, 782],
        [1000.5, 800], [1003.5, 820], [1004.5, 840], [1002.5, 858], [997, 874], [988, 888], [975, 899]]
NE_NORTH = [[975, 899], [958, 907], [935, 911.5], [905, 914], [870, 915], [835, 914.2], [800, 912.5],
            [765, 911], [735, 911]]
SW_EDGE = [[93.889, 471.704], [90.5, 458], [94, 440], [88.5, 421], [93, 402], [99, 386], [101.5, 370],
           [100.5, 356], [103, 342]]                # lobed cliff edge west of the forest
OUTER_SEA = [[-8, 215], [45, 120], [150, 62], [370, 40], [655, 60], [910, 105], [1130, 240],
             [1220, 440], [1228, 670], [1213, 845], [1150, 942]]
INLAND_FROM, INLAND_TO = 72, 267          # v12 inland ring: after (720,911) up to (93.889,471.704)
OUTLINES = {
    # East edge notched (the valley is unchanged and sits right next to it), west edge lobed along the cliff.
    'forest': ([[112, 366], [128, 352], [160, 340], [200, 332], [245, 327], [290, 325], [322, 330],
                [333, 352], [331, 378], [323, 400], [331, 424], [333, 450], [324, 476], [332, 502], [333, 529],
                [318, 543], [270, 546], [215, 545], [160, 543], [118, 537], [104, 512], [101, 490], [97, 466],
                [101, 446], [95, 424], [100, 404], [104, 386]], 6),
    'village': ([[118, 568], [184, 556], [269, 555], [323, 556], [344, 578], [340, 620], [340, 654],
                 [334, 691], [349, 737], [311, 752], [262, 744], [232, 757], [200, 781], [150, 795],
                 [116, 786], [106, 760], [118, 726], [140, 696], [152, 660], [140, 618]], 12),
    'industrial': ([[818, 728], [852, 722], [897, 724], [935, 734], [960, 747], [977, 766], [995, 792],
                    [997, 826], [992, 858], [979, 882], [954, 896], [910, 902], [860, 902], [828, 897],
                    [813, 880], [806, 856], [810, 830], [806, 806], [810, 780], [810, 758], [813, 742]], 6),
    # Paved lot only (about 5,800 m2); the rest of the old industrial strip is common green with trees.
    'beach_parking': ([[583, 374], [588, 361], [602, 350], [626, 340.5], [652, 336], [678, 340.5], [702, 350], [716, 361],
                       [719, 374], [711, 384.5], [690, 386], [652, 387], [614, 386], [591, 384.5]], 6),
}
NEW_DISTRICT = dict(id='beach_parking', name_ru='Пляжная парковка', color='#d3d0c4', parent_id=None,
                    notes_ru='Бывшая промзона: парковка для отдыхающих перед пляжем; остальное — общая зелень с деревьями.')
RENAMES = {'forest': 'Лес', 'residential': 'Район подворотен', 'industrial': 'Промзона'}
# Forest, swamp, lake, hill, railway spur, wagon and the drinkers' clearing.
FOREST_LAKE = [[262, 486], [270, 474], [287, 470], [303, 476], [310, 489], [303, 502], [285, 507], [268, 501]]
SWAMP = [[110, 470], [122, 452], [146, 444], [170, 452], [178, 474], [176, 500], [165, 522], [140, 530],
         [118, 520], [108, 496]]
PONDS = [([128, 505], [11, 8], .2), ([150, 512], [8, 6], 1.1), ([135, 478], [12, 9], 2.0),
         ([160, 486], [7, 9], .7), ([126, 461], [7, 5], 1.6)]
RAIL = [[107, 371], [128, 383], [152, 398], [176, 414], [198, 428], [214, 438], [226, 445]]
WAGON_C, WAGON_ANGLE = [209.58, 435.28], 32
CLEARING = ([224, 424], [26, 17], 1.3, 32)
CAMPFIRE, TENT, CRATE = [234, 418], [245, 426], [203.0, 436.4]   # crate along the wagon side, 5 m from the door
LOGS = [[229, 422, 30], [239, 422, -20], [234, 412, 80]]
BOTTLES = [[231.5, 415.2], [237.4, 414.6], [238.8, 420.9], [229.6, 419.4], [233.1, 423.6], [236.2, 411.3], [227.8, 414.0]]
HILL_C, HILL_R = [286, 368], [34, 30]
HUB = [238, 424]
ROCKS = {  # id: (centre, radii, phase): rock clusters along the cliff, the tunnel portal and the cove, as in the reference
    'TUNNEL_ROCKS_N': ([106.5, 382], [4.5, 3.5], .3), 'TUNNEL_ROCKS_S': ([108, 361], [4.5, 3], 1.7),
    'CLIFF_ROCKS_1': ([97, 430], [3.5, 6], .9), 'CLIFF_ROCKS_2': ([96.5, 458], [3.5, 5], 2.3),
    'COVE_W_ROCKS': ([121, 347.5], [6, 3.5], .5), 'COVE_SAND_ROCKS': ([150, 322], [5, 3], 1.1),
    'COVE_MID_ROCKS': ([206, 296], [6, 4], .7), 'SHORE_ROCKS': ([262, 318.5], [5, 3], 2.0),
    'HILL_ROCKS': ([301, 329], [7, 4], 1.2), 'COVE_E_ROCKS': ([316, 311], [7, 4], .4)}
# Hamlet: church in the NW corner, fields; NW exit and P16 shifted west.
CHURCH_C, CHURCH_ANGLE = [158, 748], 45
CHURCH_SQUARE = ([188, 718], [11, 8], .3)
CHURCH_YARD = ([162, 748], [25, 22], .5)          # 2 m SE of the design oval so it encloses the bell tower
EXIT_NW_POST, EXIT_NW_END = [177, 664], [159, 657]   # >=60 m south of the churchyard, off the church lane
FIELDS = {  # id: (controls, crop, stripes, stripe direction)
    'FIELD13_1': ([[222, 718], [258, 717], [262, 730], [258, 743], [222, 744], [218, 731]], 'wheat', 3, 'north_south'),
    'FIELD13_2': ([[234, 620], [278, 621], [281, 633], [278, 646], [234, 645], [231, 633]], 'wheat', 5, 'north_south'),
    'FIELD13_3': ([[147, 686], [171, 685], [178, 699], [175, 715], [150, 717], [142, 702]], 'sunflower', 4, 'east_west'),
    'FIELD13_4': ([[286, 560], [311, 559], [314, 575], [311, 591], [287, 592], [284, 575]], 'wheat', 4, 'north_south'),
    'FIELD13_5': ([[134, 575], [160, 571], [177, 577], [178, 595], [170, 607], [140, 607], [132, 592]], 'wheat', 5, 'east_west'),
}
# Alley district (id 'residential' kept): small blocks of panel houses with podvorotnya arches, the trashy
# businesses wedged between them, tiny courtyards. Arch: (offset along the long side from the centre, clear width,
# clear height, van passable); its axis crosses the short side and sticks out ARCH_EXT m beyond both faces.
PANELS = {  # id: (centre, w along x, d along y, rotation, floors, block, role, arches)
    'R13_P01': ([487, 778], 12, 34, 4, 7, 'A', 'west wing of block A', []),
    'R13_P02': ([503, 811], 30, 12, -5, 9, 'A', 'north wing of block A over LANE_A', [(1.0, 3.5, 3.2, False)]),
    'R13_P03': ([575, 739.5], 36, 12, 2, 5, 'B', 'avenue front over the COURT_B van arch', [(-1.0, 4.5, 4.2, True)]),
    'R13_P04': ([655, 739.5], 32, 12, -2, 5, 'D', 'avenue front at the district centre over LANE_C', [(13.0, 3.5, 3.2, False)]),
    'R13_P05': ([538, 786], 12, 40, -3, 9, 'B', 'west wing of block B on ALLEY_W over LANE_N', [(-2.0, 3.5, 3.2, False)]),
    'R13_P06': ([598, 784], 12, 36, 9, 7, 'C', 'middle of block C over the ALLEY_X van arch', [(2.0, 4.5, 4.2, True)]),
    'R13_P07': ([596, 818], 30, 12, -4, 5, 'C', 'rear of block C on R_REAR over LANE_R', [(12.0, 3.5, 3.2, False)]),
    'R13_P08': ([645, 790], 12, 40, -6, 9, 'D', 'middle of block D over LANE_E', [(-10.0, 3.5, 3.2, False)]),
    'R13_P09': ([690, 792], 12, 38, 5, 7, 'E', 'block E by the hospital over LANE_E2', [(-6.0, 3.5, 3.2, False)]),
    'R13_P10': ([580, 702], 40, 12, 2, 9, 'S', 'south front on the avenue over LANE_S', [(10.0, 3.5, 3.2, False)]),
    'R13_P11': ([594, 648], 32, 12, 6, 5, 'S', 'south strip behind ALLEY_S over LANE_S', [(4.4, 3.5, 3.2, False)]),
}
ARCH_EXT = 3.0
CORRIDORS = [('ALLEY_W', 'R13_P02', 'R13_P05'), ('COURT_B', 'F13_LOMBARD', 'R13_P06'), ('ALLEY_C', 'R13_P06', 'F13_BAR2'),
             ('LANE_C', 'R13_P08', 'R13_P09'), ('ALLEY_X', 'R13_P07', 'R13_P06')]
# id: (type, label, centre, w, d, rotation, storeys, door, group, colour, icon, poi, parent road)
BUSINESSES = {
    'F13_DISCOUNTER': ('supermarket', 'Дискаунтер', [492, 738.5], 26, 13, 0, 1, [492, 731.5], 'retail', '#d5a94e', 'М', None, 'ARC_AVENUE'),
    'F13_BEER': ('beer_kiosk', 'Разливное пиво', [511.5, 791], 10, 8, 0, 1, [517, 791], 'food', '#bd817d', 'Е', None, 'ALLEY_W'),
    'F13_ATMSHOP': ('atm_shop', 'Продукты · банкомат', [540, 738], 16, 11, 0, 1, [540, 732], 'retail', '#d5a94e', 'М', 'P11-2', 'ARC_AVENUE'),
    'F13_LOMBARD': ('pawn_shop', 'Ломбард', [559, 762], 10, 10, 0, 1, [564.5, 762], 'finance', '#c4875a', '$', None, 'COURT_B'),
    'F13_SHAWARMA': ('fast_food', 'Шаурма 24', [556, 820], 10, 8, -3, 1, [556.2, 824.5], 'food', '#bd817d', 'Е', None, 'R_REAR'),
    'F13_ZAIMY': ('payday_loans', 'Займы до зарплаты', [607, 737], 12, 9, 0, 1, [607, 732], 'finance', '#c4875a', '$', None, 'ARC_AVENUE'),
    'F13_BAR2': ('bar', 'Рюмочная', [636, 757], 12, 9, 0, 1, [629.5, 757], 'food', '#bd817d', 'Е', None, 'ALLEY_C'),
    'F13_BETS': ('betting_shop', 'Ставки', [640, 826], 12, 9, 2, 1, [639.85, 830.8], 'finance', '#c4875a', '$', None, 'R_REAR'),
}
COURTYARDS = {  # id: (centre, radii, phase, buildings)
    'AB13_1': ([501, 777], [5.5, 10], .2, ['R13_P01', 'R13_P02', 'F13_DISCOUNTER', 'F13_BEER']),
    'AB13_2': ([557, 789], [6.5, 11], .9, ['R13_P05', 'F13_LOMBARD', 'F13_SHAWARMA']),
    'AB13_3': ([598, 754], [11, 5.5], .4, ['R13_P03', 'R13_P06', 'F13_ZAIMY']),
    'AB13_4': ([652, 757.5], [7, 5], 1.4, ['R13_P04', 'R13_P08', 'F13_BAR2']),
    'AB13_5': ([705.5, 800], [4.5, 11], 2.1, ['R13_P09', 'F06_HOSPITAL']),
}
SQUARE_PYATACHOK = ([626, 704], [13, 8], .6)
GARAGE_YARD = [[496, 837], [520, 835.5], [546, 836], [549, 843], [546, 850], [520, 851], [497, 850], [494, 843]]
GARAGE_ROW = ([499.5, 843], 12, 3.4)              # first shell centre, count, pitch along x
# Residential envelope tightened to the blocks: the open north strip and SE quarter return to common green.
RES_OUTLINE = [[476, 671], [494, 664], [522, 660], [550, 656], [568, 647], [580, 633], [607, 626], [638, 625], [672, 625], [694, 629],
               [706, 642], [710, 664], [712, 690], [722, 707], [746, 712], [770, 714], [781, 728], [781, 760], [780, 792],
               [778, 824], [767, 849], [744, 865], [712, 870], [676, 869], [640, 866], [612, 869], [584, 871], [556, 863],
               [526, 859], [500, 857], [482, 846], [472, 820], [471, 784], [474, 748], [474, 716], [474, 690]]
# Industrial zone in the NE corner.
INDUSTRY = {  # id: (centre, w, d, rotation, door, poi, round radius)
    'F06_COMPLEX': ([895, 810], 46, 28, 4, [895, 791.9], 'B05', None),
    'F06_CHIMNEY': ([929, 829], 8, 8, 0, [937.5, 829], 'CHIMNEY', 4),
    'F06_TOW': ([858, 729], 20, 12, 3, [858, 740], 'P12', None),
    'F06_DEPOT': ([880, 882], 36, 20, -2, [880, 868], 'P14', None),
    'F06_WARE1': ([972, 850], 18, 30, -6, [959, 850], None, None),
    'F06_MAINT': ([826, 815], 12, 20, 3, [836, 815], None, None),
    'F13_TANK': ([968, 790], 14, 14, 0, [957, 790], None, 7),
}
TOW_LOT, B05_YARD = ([890, 738], [18, 9], .4), ([895, 810], [36, 25], .5)
OUTFALL = [[918, 812], [953, 812], [1006, 812.5], [1042, 815]]
PLUME = ([1062, 816], [26, 15], .4)
# West barbed fence follows the curved industrial outline about 4 m outside it, from the north cliff to the gate.
FENCE_W = [[838, 913.6], [824, 901], [809, 883.5], [802, 857], [806, 830], [802, 806], [806, 780], [806.2, 758], [808.4, 740.6]]
FENCE_S = [[811.6, 733.8], [850, 718], [900, 716], [945, 726], [972, 737], [983.5, 745]]
DEPOT_STUB = [[850, 866], [910, 866]]
# Beach car park on the old industrial site.
LOTS = {'PARK13_LOT_W': ([620.5, 372], 601, 'PARK_AISLE_W', 612), 'PARK13_LOT_E': ([681.5, 372], 662, 'PARK_AISLE_E', 690)}
AISLE_Y, TURN_HEADS = 372, {'PARK13_TURN_W': ([593, 372], 'PARK_AISLE_W'), 'PARK13_TURN_E': ([709, 372], 'PARK_AISLE_E')}
TURN_R = 6.5
DROP_OFF = ([652, 346], [11, 8], .2)
PARK_BUILDINGS = {
    'F13_PARK_KIOSK': ('kiosk', 'Киоск у пляжа', [627, 345], 8, 6, 0, 1, [634, 345], 'retail', '#d5a94e', 'М', None, 'PARK_ROAD'),
    'F13_PARK_WC': ('toilet_shower', 'Туалет / душ', [677, 345], 10, 6, 0, 1, [669, 345], 'service', '#709dac', 'С', None, 'PARK_ROAD'),
}
BOLLARDS = [[586, 357], [600, 345.5], [626, 337.5], [652, 335], [678, 337.5], [704, 345.5], [718, 357]]

# Roads: id, controls, class, district ids, start parent, end parent (parents snap the end exactly onto them).
ROADS = [
    ('START_ROAD', [[205.5, 444.5], [207.5, 460], [214, 482], [222, 505], [228, 530], [230, 558], [234, 577]],
     'rural_road', ['forest', 'village'], None, None),
    ('CHURCH_LANE', [[230, 700], [219, 706], [204, 704], [190, 709]], 'rural_road', ['village'], None, None),
    ('EXIT_NW', [[222, 704.5], [206, 692], [190, 681], EXIT_NW_POST, EXIT_NW_END], 'highway', ['village'], 'CHURCH_LANE', None),
    ('ALLEY_W', [[522, 723.5], [523, 748], [520.5, 772], [523.5, 797], [528, 817], [535, 832]], 'alley', ['residential'], 'ARC_AVENUE', 'R_REAR'),
    ('ALLEY_C', [[623, 723.5], [622, 745], [625, 768], [620.5, 793], [624, 815], [622, 834.5]], 'alley', ['residential'], 'ARC_AVENUE', 'R_REAR'),
    ('COURT_B', [[574, 723.5], 'R13_P03', [571.5, 764], [575, 786], [571.5, 810], [573, 832.9]], 'alley', ['residential'], 'ARC_AVENUE', 'R_REAR'),
    ('ALLEY_X', [[575, 786], 'R13_P06', [614, 787.5], [621.8, 786]], 'alley', ['residential'], 'COURT_B', 'ALLEY_C'),
    ('ALLEY_S', [[519, 680], [545, 676], [575, 672], [610, 674], [652, 666]], 'alley', ['residential'], 'R_COURTS', 'OLD_TOWN_CONNECTOR'),
    ('I_ACCESS', [[770, 723.5], [786, 727], [801, 733], [818, 741]], 'town_street', ['residential', 'industrial'], None, None),
    ('I_YARD', [[818, 741], [852, 752], [890, 763], [930, 771], [952, 795], [953, 832], [930, 853], [890, 858],
                [855, 850], [842, 822], [845, 785], [852, 752]], 'town_street', ['industrial'], None, None),
    ('PARK_ROAD', [[650, 392], [653, 383], [651, 372], [649.5, 362], [652, 353]], 'town_street', ['beach_parking'], None, None),
    ('PARK_AISLE_W', [[651, 372], [593, 372]], 'town_street', ['beach_parking'], 'PARK_ROAD', None),
    ('PARK_AISLE_E', [[651, 372], [709, 372]], 'town_street', ['beach_parking'], 'PARK_ROAD', None),
]
DROPPED_ROADS = {'COURT_ACCESS_1', 'COURT_ACCESS_2', 'COURT_ACCESS_3', 'ACCESS_P13-4', 'ACCESS_F06_K2', 'ACCESS_P09-3'}
RECREATED_ROADS = {'I_YARD', 'ACCESS_B05', 'ACCESS_P12', 'ACCESS_P14', 'ACCESS_CHIMNEY', 'ACCESS_F06_WARE1',
                   'ACCESS_F06_MAINT', 'START_ROAD', 'ACCESS_B01', 'ACCESS_F06_CHURCH', 'EXIT_NW', 'ACCESS_P11-2'}
# Walk-only paths: id, controls, class, district ids, start parent, end parent.
PATHS = [
    ('LANE_A', [[509.5, 723.5], [509.5, 738], [506, 750.5], [499, 761], [498.5, 789], 'R13_P02', [514, 827], [535, 832]], 'foot_lane',
     ['residential'], 'ARC_AVENUE', 'R_REAR'),
    ('LANE_N', [[522, 784], 'R13_P05', [557, 786], [575, 783]], 'foot_lane', ['residential'], 'ALLEY_W', 'COURT_B'),
    ('LANE_C', [[668, 723.5], 'R13_P04', [664.5, 764], [668, 790], [665, 814], [667.5, 839.8]], 'foot_lane', ['residential'], 'ARC_AVENUE', 'R_REAR'),
    ('LANE_R', [[614, 787.3], [612, 800], 'R13_P07', [608.5, 833.3]], 'foot_lane', ['residential'], 'ALLEY_X', 'R_REAR'),
    ('LANE_Y', [[573.4, 756], [586, 755], [599, 753.5], [612, 755.5], [623.6, 757.5]], 'foot_lane', ['residential'], 'COURT_B', 'ALLEY_C'),
    ('LANE_E', [[623.6, 781], 'R13_P08', [658, 779], [666.5, 778]], 'foot_lane', ['residential'], 'ALLEY_C', 'LANE_C'),
    ('LANE_E2', [[667.8, 787], 'R13_P09', [707, 788], [715, 788]], 'foot_lane', ['residential'], 'LANE_C', 'R_REAR'),
    ('LANE_S', [[590, 723.5], 'R13_P10', [590.5, 682], [596, 664], 'R13_P11', [606, 628], [611, 609]], 'foot_lane', ['residential', 'old_town'], 'ARC_AVENUE', 'ACCESS_P09'),
    ('TRAIL_E', [[380.5, 437], [358, 435], [334, 432], [306, 425], [281, 412], [258, 414], HUB], 'trail', ['fields', 'forest'], 'VALLEY_BRANCH', None),
    ('TRAIL_N', [[229.3, 535], [248, 526], [258, 514], [252, 498], [246, 480], [251, 462], [244, 444], HUB], 'trail', ['forest'], 'START_ROAD', None),
    ('TRAIL_HILL', [[262, 413.5], [262, 396], None], 'trail', ['forest'], 'TRAIL_E', None),
    ('TRAIL_SWAMP', [[205.5, 444.5], [186, 456], [174, 470], [160, 482]], 'trail', ['forest'], None, None),
    ('TRAIL_COVE', [HUB, [240, 400], [238, 380], [232, 352], [228, 330], [226, 310]], 'trail', ['forest', 'beach'], None, None),
    ('CLEARING_LINK', [[205.5, 444.5], [220, 446.5], [232, 440], HUB], 'trail', ['forest'], None, None),
    ('PATH_BEACH_W', [[612.375, 372], [612.375, 362], [612.375, 355], [611, 338], [608, 318], [606, 285]], 'passage',
     ['beach_parking', 'beach'], 'PARK_AISLE_W', 'WALK_BEACH'),
    ('PATH_BEACH_C', [[652, 353], [651.5, 338], [651, 318], [650, 285]], 'passage', ['beach_parking', 'beach'], 'PARK_ROAD', 'WALK_BEACH'),
    ('PATH_BEACH_E', [[689.625, 372], [689.625, 362], [689.625, 355], [692, 338], [695, 316], [696, 285]], 'passage',
     ['beach_parking', 'beach'], 'PARK_AISLE_E', 'WALK_BEACH'),
]
_INLAND = ('Забор на границе районов убран (Федя 04.10: никаких заборов между районами). flatten_plan.py такие '
           'деревянные/бетонные заборы и раньше не строил, так что в Unity эта граница уже была открыта.')
_BEACH = 'Забор над пляжем убран; вместо него естественное закрытие — дюна с плавником (бусик не проедет, люди пройдут).'
REMOVED_BARRIERS = {  # the 12 v12 border fences dropped in v13: id -> (replacement ids, reason)
    'FOREST_VILLAGE_1': ([], _INLAND), 'FOREST_VILLAGE_2': ([], _INLAND), 'RURAL_TRANSITION_1': ([], _INLAND),
    'RURAL_TRANSITION_2': ([], _INLAND), 'TRANSITION_URBAN_1': ([], _INLAND), 'TRANSITION_URBAN_2': ([], _INLAND),
    'TRANSITION_URBAN_3': ([], _INLAND), 'VALLEY_NORTH_1': ([], _INLAND), 'VALLEY_NORTH_2': ([], _INLAND),
    'VALLEY_BEACH_FENCE_1': (['BEACH_DUNE_W'], _BEACH), 'VALLEY_BEACH_FENCE_2': (['BEACH_DUNE_E'], _BEACH),
    'INDUSTRIAL_BEACH_FENCE_1': (['BEACH_DUNE_E'], _BEACH + ' Промзона переехала в СВ угол.'),
}
DUNE_FROM, DUNE_TO = [330, 320], [829, 341]    # BEACH_WEST_ROCKS end to the start of the elite beach fence
GUARD_DISTRICTS = ('transition', 'old_town', 'elite', 'fields')
HAMLET_BENDS = {'ACCESS_F06_6_1': 3, 'ACCESS_F06_6_2': 3, 'ACCESS_F06_4_1': 3, 'ACCESS_O06_T5_U1': 3, 'ACCESS_P02': 3,
                'ACCESS_F06_1_2': 3}


def hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(ROOT.iterdir()) if p.is_file() and PREVIOUS.match(p.name)}


def source_data():
    return json.loads((ROOT/'MAP_PLAN_R01_v12.json').read_text(encoding='utf-8'))


def circle(c, r, n=12):
    return [[round(c[0]+r*math.cos(2*math.pi*i/n), 3), round(c[1]+r*math.sin(2*math.pi*i/n), 3)] for i in range(n)]


def centroid(poly):
    return [round(sum(p[k] for p in poly)/len(poly), 3) for k in (0, 1)]


def plen(line):
    return round(sum(m.length(a, b) for a, b in zip(line, line[1:])), 3)


def local(c, angle, u, v):
    co, si = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return [round(c[0]+u*co-v*si, 3), round(c[1]+u*si+v*co, 3)]


def poly_gap(a, b):
    if strict_overlap(a, b):
        return 0.0
    return min(v7.gap(a, p, q) for p, q in v7.edges(b))


def spiral(c, r0, r1, a0, turns, n=60):
    out = []
    for i in range(n+1):
        t = i/n
        r, a = r0+(r1-r0)*t, a0+turns*2*math.pi*t
        out.append([round(c[0]+r*math.cos(a), 2), round(c[1]+r*0.88*math.sin(a), 2)])
    return out


def church_footprint():
    # Nave 12 x 30 m with a 7 x 7 m bell tower on the south-east gable, one merged footprint.
    corners = [(-6, -15), (-3.5, -15), (-3.5, -22), (3.5, -22), (3.5, -15), (6, -15), (6, 15), (-6, 15)]
    return [local(CHURCH_C, CHURCH_ANGLE, u, v) for u, v in corners]


def bays(lot):
    centre, x0, aisle, walk_x = LOTS[lot]
    out = []
    for row, yc in (('N', centre[1]+6.5), ('S', centre[1]-6.5)):
        for i in range(12):
            x = x0+3.25*(i+.5)
            walkway = row == 'S' and x0+3.25*i <= walk_x <= x0+3.25*(i+1)
            out.append(dict(id=f'{lot}_{row}{i+1:02d}', row=row, polygon_m=m.rectangle(x, yc, 3.25, 7, 0),
                            size_m=[3.25, 7], usable=not walkway, use='walkway' if walkway else 'van_bay'))
    return out


def seed():
    d = source_data()
    original = copy.deepcopy(d)
    d.update(revision='v13', title_ru='VOLUNTEERS ONLY — план карты R01 / v13')
    d['specification']['brief_override'] = ('Fedya 2026-10-05 evening: alley district, hamlet and forest per '
                                            'REF_FEDYA_v13_hamlet_forest.png, industrial zone NE, beach car park')
    d['provenance'] = dict(brief='Fedya voice brief 2026-10-05 (evening) + read-only v13 design analysis',
        source_schema='MAP_PLAN_R01_v12.json', owner_decisions_date='2026-10-05',
        reference_images=['REF_FEDYA_v13_hamlet_forest.png'],
        method='targeted rebuild of five areas on final v12; transition, old town, elite hill, valley and main beach copied unchanged',
        previous_files_sha256=hashes(),
        pending_ru=['Вторая фотка Феди к промзоне ещё не пришла: раскладка промзоны — заготовка (кольцо + 7 зданий по id).',
                    'После «ок» Феди: map_dressing_v13, crowd_v13, flatten_plan (barbed_fence, dune_ridge, арки, развороты), потом Unity.',
                    'Решения Феди: ЖД через долину; срезы бусиком по траве между районами; мосты с картинки; бухта пешком.'])
    md = original['metrics']
    d['comparison'] = dict(v12=dict(extent_m=md['extent_m'], building_count=md['building_count'], land_area_m2=md['area_m2'],
        building_counts_by_district=md['building_counts_by_district']),
        policy='v12 transition, old town, elite hill, valley and main beach unchanged; four areas rebuilt per Fedya 2026-10-05')
    d['geometry_repairs'] = []
    d['land_transfers'] = []
    build_land(d)
    build_forest(d)
    build_hamlet(d)
    build_alleys(d)
    build_industry(d)
    build_parking(d)
    build_roads(d, original)
    build_fences(d)
    record_moves(d, original)
    notes(d)
    return d


def build_land(d):
    ds = {q['id']: q for q in d['districts']}
    for did, (controls, steps) in OUTLINES.items():
        if did not in ds:
            q = dict(NEW_DISTRICT)
            d['districts'].append(q)
            ds[did] = q
        ds[did]['polygon_m'] = rounded(controls, steps)
    for did, name in RENAMES.items():
        ds[did]['name_ru'] = name
    ds['forest']['color'] = '#b3caa9'
    d['road_classes'].update(
        alley=dict(name_ru='Проезд подворотен — 4.5 м, 1 полоса', width_m=4.5, color='#eadcb6', lanes=1, van_access=True),
        foot_lane=dict(name_ru='Пеший проход / арка — 3 м', width_m=3.0, color='#8f7350', walkable=True, van_access=False),
        trail=dict(name_ru='Лесная тропа — 2 м', width_m=2.0, color='#7c6a43', walkable=True, van_access=False))
    ds['forest']['notes_ru'] = 'Лес по референсу Феди: слева болото, справа озеро, снизу холм, вагон у костра; лес выходит к бухте.'
    ds['village']['notes_ru'] = 'Хутор по референсу: церковь в СЗ углу, три полосатых поля, прежние усадьбы и улочки.'
    ds['residential']['notes_ru'] = 'Район подворотен: панельки 5–9 этажей вплотную, арки, узкие проезды и ларьки; id сохранён.'
    ds['industrial']['notes_ru'] = 'Промзона перенесена в СВ угол: кольцо, 7 строений, колючка на 2 сторонах, слив в море.'
    sea_edge = d['beaches'][0]['sea_edge_m']
    coast = curve(COVE_SEA, 3)[:-1]+sea_edge+curve(QUAY, 3)[1:]
    inland = d['boundary']['polygon_m'][len(sea_edge):]
    ring = curve(NE_NORTH, 3)[1:]+inland[INLAND_FROM:INLAND_TO]+curve(SW_EDGE, 3)[:-1]
    d['boundary'].update(polygon_m=coast+ring, coast_segments_m=[[a, b] for a, b in zip(coast, coast[1:])],
        barrier='closed rock scarp on the non-coast boundary; no wall on coast_segments_m (cove, beach, industrial quay); SEA returns to last ground point')
    cove_sea = curve(COVE_SEA, 3)
    cove_land = curve(COVE_LAND, 3)
    d['beaches'].append(dict(id='BEACH_FOREST_COVE', name_ru='Лесная бухта', polygon_m=cove_land+list(reversed(cove_sea)),
        land_edge_m=cove_land, sea_edge_m=cove_sea, width_m=[15, 40], surface='sand', access_road_ids=[],
        foot_access_path_ids=['TRAIL_COVE'],
        closed_ends_ru='Запад — скалы у тоннеля, восток — скалы BEACH_WEST_ROCKS; машиной не подъехать, только пешком из леса.'))
    sea = next(w for w in d['water'] if w['id'] == 'SEA')
    sea['polygon_m'] = coast+list(reversed(curve(OUTER_SEA, 6)))


def build_forest(d):
    lake = rounded(FOREST_LAKE, 6)
    d['water'].append(dict(id='FOREST_LAKE', kind='lake', name_ru='Лесное озеро', polygon_m=lake,
                           center_m=centroid(lake), district_id='forest'))
    ponds = []
    for i, (c, r, phase) in enumerate(PONDS, 1):
        ponds.append(f'SWAMP_POND_{i}')
        d['water'].append(dict(id=f'SWAMP_POND_{i}', kind='swamp_pond', name_ru=f'Болото: бочаг {i}',
                               polygon_m=oval(c, r, phase, 24), center_m=c, district_id='forest'))
    d['hills'].append(dict(id='HILL_FOREST', center_m=HILL_C, radii_m=HILL_R, height_target_m=9,
                           polygon_m=oval(HILL_C, HILL_R, .9, 40), district_id='forest', summit_path_id='PATH_HILL_SPIRAL',
                           dressing_hints_ru=['одинокая сосна и лавка на вершине']))
    rail = curve(RAIL, 6)
    d['railway'] = dict(polyline_m=rail, from_point='RAIL_TUNNEL_W', to_point='B01', service_road_id=None,
                        active_trains=False, road_crossings=[], water_bridges=[], buffer_stop_m=RAIL[-1],
                        notes_ru='Только ветка от вагона B01 к тоннелю в скале на западном берегу; линия через долину к депо убрана.')
    wagon = m.rectangle(*WAGON_C, 18, 3, WAGON_ANGLE)
    n = (-math.sin(math.radians(WAGON_ANGLE)), math.cos(math.radians(WAGON_ANGLE)))
    door = [round(WAGON_C[0]+n[0]*4.5, 3), round(WAGON_C[1]+n[1]*4.5, 3)]
    f = next(q for q in d['functional_buildings'] if q['id'] == 'F06_WAGON')
    f.update(center_m=WAGON_C, footprint_m=wagon, rotation_deg=WAGON_ANGLE, entrance_m=door, access_road_id='START_ROAD',
             on_rail=True)
    b = next(q for q in d['building_masses'] if q['id'] == 'WAGON06')
    b.update(center_m=WAGON_C, polygon_m=wagon, rotation_deg=WAGON_ANGLE)
    pts = {p['id']: p for p in d['points']}
    pts['B01'].update(position_m=door, district_id='forest')
    clearing = oval(*CLEARING)
    d['functional_sites'] += [
        dict(id='HANGOUT13', type='hangout', district_id='forest', building_id='F06_WAGON', polygon_m=clearing,
             label_ru='Поляна у вагона: тут бухают и отдыхают', doubles_as='van turning space in front of the wagon',
             dressing_hints=dict(campfire_ring=dict(position_m=CAMPFIRE, diameter_m=2),
                 logs=[dict(position_m=[x, y], length_m=2.5, rotation_deg=a) for x, y, a in LOGS],
                 tent=dict(position_m=TENT, size_m=[2.5, 2]), bottles_and_cans_m=BOTTLES, bottle_radius_m=6,
                 crate_by_wagon_door_m=CRATE, burnt_patch_m=[CAMPFIRE[0]+3, CAMPFIRE[1]-2],
                 sightline_tree_gap='keep trees thin on the NE side of the clearing (B01 -> chimney)')),
        dict(id='RAIL_TUNNEL_W', type='rail_tunnel_portal', district_id='forest', position_m=RAIL[0],
             label_ru='Тоннель в скале: рельсы уходят с карты', blocks_van=True, blocks_foot=True,
             closure='rubble and grating 6 m inside the stone portal'),
    ]
    d['forest_features'] = dict(
        swamp=dict(id='SWAMP13', kind='swamp', polygon_m=rounded(SWAMP, 6), area_m2=round(m.area(rounded(SWAMP, 6)), 1),
                   pond_ids=ponds, boardwalk_path_id='TRAIL_SWAMP', label_ru='Болото'),
        lake=dict(water_id='FOREST_LAKE', label_ru='Лесное озеро'),
        hill=dict(hill_id='HILL_FOREST', path_id='PATH_HILL_SPIRAL', label_ru='Холм со спиральной тропой'),
        hangout=dict(site_id='HANGOUT13', base_id='B01'),
        tunnel=dict(site_id='RAIL_TUNNEL_W', railway_end_m=RAIL[0]),
        cove=dict(beach_id='BEACH_FOREST_COVE', foot_path_id='TRAIL_COVE'),
        rocks=[dict(id=rid, polygon_m=oval(*row, 16), barrier=False) for rid, row in ROCKS.items()],
        tree_policy='dense conifers; open clearing, hill top, swamp ponds and lake; thin tree gap NE of the clearing for the chimney sightline')


def build_hamlet(d):
    fs = {f['id']: f for f in d['functional_buildings']}
    door = local(CHURCH_C, CHURCH_ANGLE, 0, -25)
    fs['F06_CHURCH'].update(district='village', district_id='village', center_m=local(CHURCH_C, CHURCH_ANGLE, 0, -3.5),
        width_m=12, depth_m=37, footprint_m=church_footprint(), rotation_deg=CHURCH_ANGLE, entrance_m=door,
        access_road_id='CHURCH_LANE', nave_center_m=CHURCH_C, nave_size_m=[12, 30], tower_size_m=[7, 7],
        tower_height_target_m=22, label_ru='Церковь')
    sites = {s['id']: s for s in d['functional_sites']}
    sites['CHURCH12_YARD'].update(district_id='village', polygon_m=oval(*CHURCH_YARD, 36),
        label_ru='Церковный двор; низкая ограда участка допустима', low_plot_wall=True)
    d['functional_sites'].append(dict(id='CHURCH_SQUARE13', type='square', district_id='village', building_id='F06_CHURCH',
        polygon_m=oval(*CHURCH_SQUARE, 24), surface='paved', label_ru='Площадка перед церковью'))
    d['crop_fields'] = [dict(id=fid, district_id='village', crop=crop, stripe_count=n, stripe_direction=direction,
        polygon_m=rounded(controls, 4), area_m2=round(m.area(rounded(controls, 4)), 1),
        label_ru={'wheat': 'Поле пшеницы', 'sunflower': 'Поле подсолнуха'}[crop])
        for fid, (controls, crop, n, direction) in FIELDS.items()]
    pts = {p['id']: p for p in d['points']}
    pts['P16']['position_m'] = EXIT_NW_POST
    ex = next(e for e in d['exits'] if e['id'] == 'NW')
    u = [EXIT_NW_END[k]-EXIT_NW_POST[k] for k in (0, 1)]
    n0 = math.hypot(*u)
    u = [u[0]/n0, u[1]/n0]
    nn = [-u[1], u[0]]

    def pt(t, s):
        return [round(EXIT_NW_POST[0]+u[0]*t+nn[0]*s, 3), round(EXIT_NW_POST[1]+u[1]*t+nn[1]*s, 3)]
    end = n0+6
    ex.update(dead_end_m=EXIT_NW_END,
        barrier_polygons_m=[[pt(0, 8*g), pt(end, 8*g), pt(end, 0), pt(end+6, 0), pt(end+6, 16*g), pt(0, 16*g)] for g in (1, -1)],
        post_trigger_polygon_m=[pt(-.75, 8), pt(.75, 8), pt(.75, -8), pt(-.75, -8)], post_trigger_width_m=16)


def panel_frame(pid):
    """Unit vectors along the long and the short side of a panel house."""
    c, w, h, a = PANELS[pid][:4]
    co, si = math.cos(math.radians(a)), math.sin(math.radians(a))
    return ((co, si), (-si, co), h) if w >= h else ((-si, co), (co, si), w)


def arch_axes(pid):
    """Each arch as [end, middle, end]; the axis crosses the short side and sticks out ARCH_EXT m on both faces."""
    c = PANELS[pid][0]
    (lu, lv), (su, sv), short = panel_frame(pid)
    out = []
    for u, *_ in PANELS[pid][7]:
        mid = [c[0]+lu*u, c[1]+lv*u]
        e = short/2+ARCH_EXT
        out.append([[round(mid[0]-su*e, 3), round(mid[1]-sv*e, 3)], [round(mid[0], 3), round(mid[1], 3)],
                    [round(mid[0]+su*e, 3), round(mid[1]+sv*e, 3)]])
    return out


def expand(controls):
    """A panel id inside a control list stands for its (first) arch: both ends and the middle, nearest end first."""
    out = []
    for p in controls:
        if isinstance(p, str):
            a, mid, b = arch_axes(p)[0]
            prev = out[-1]
            out += [a, mid, b] if m.length(prev, a) <= m.length(prev, b) else [b, mid, a]
        else:
            out.append(p)
    return out


def build_alleys(d):
    d['building_masses'] = [b for b in d['building_masses'] if b['kind'] != 'slab']
    d['functional_buildings'] = [f for f in d['functional_buildings'] if f['id'] != 'F06_K2']
    d['removed_buildings'] = [dict(id='F06_K2', kind='kiosk', from_district='residential', access_road_id='ACCESS_F06_K2',
        reason_ru='Ларёк v12 у снесённого двора-«П»; вместо него ларьки и лавки внутри кварталов подворотен.')]
    for pid, (c, w, h, a, floors, block, role, arches) in PANELS.items():
        axes = arch_axes(pid)
        q = dict(id=pid, district_id='residential', kind='panel', center_m=c, width_m=w, depth_m=h, floors=floors,
                 polygon_m=m.rectangle(*c, w, h, a), rotation_deg=a, block=block, role=role,
                 entrances_face='courtyards and lanes; no vehicle driveway',
                 gateway_arches=[dict(id=f'{pid}_ARCH', axis_m=[ax[0], ax[2]], width_m=wd, clear_height_m=ht, van_passable=van)
                                 for ax, (u, wd, ht, van) in zip(axes, arches)])
        d['building_masses'].append(q)
    add_functions(d, BUSINESSES, 'residential')
    d['microdistricts'] = [dict(id=cid, center_m=c, angle=0, yard_polygon_m=oval(c, r, ph, 24), building_ids=ids,
                                arrangement='alley_block', opening_direction='lanes and arches', shared_courtyard=True)
                           for cid, (c, r, ph, ids) in COURTYARDS.items()]
    (x0, y0), count, pitch = GARAGE_ROW
    d['functional_sites'] += [
        dict(id='GARAGE13', type='garage_yard', district_id='residential', polygon_m=rounded(GARAGE_YARD, 4),
             label_ru='Гаражи-ракушки за подворотней', shell_count=count,
             shells_m=[m.rectangle(x0+pitch*i, y0, 2.9, 6, 0) for i in range(count)],
             dressing_hints=['один ряд металлических гаражей', 'въезд с тупика R_REAR / ALLEY_W']),
        dict(id='SQUARE13_PYATACHOK', type='square', district_id='residential', polygon_m=oval(*SQUARE_PYATACHOK, 24),
             surface='paved', label_ru='Пятачок у центра района', dressing_hints=['лавки', 'урна', 'остановка-навес'])]
    ds = {q['id']: q for q in d['districts']}
    ds['residential']['polygon_m'] = rounded(RES_OUTLINE, 6)
    pts = {p['id']: p for p in d['points']}
    pts['P11-2'].update(position_m=BUSINESSES['F13_ATMSHOP'][7], name_ru='ATM в магазине «Продукты»')
    for pid, name in (('BAD_BLOCK', 'Подворотня 1'), ('BAD_BLOCK_2', 'Подворотня 2'), ('BAD_BLOCK_3', 'Подворотня 3')):
        pts[pid]['name_ru'] = name
    pts['BAD_CENTER']['name_ru'] = 'Центр района подворотен'
    pts['P09-2']['name_ru'] = 'Запасная: подворотни'


def add_functions(d, table, did):
    for fid, (typ, label, c, w, h, a, storeys, door, group, color, icon, poi, parent) in table.items():
        f = dict(id=fid, type=typ, district=did, district_id=did, label_ru=label, group=group, center_m=c,
                 width_m=w, depth_m=h, storeys=storeys, footprint_shape='rect', color=color, icon=icon,
                 footprint_m=m.rectangle(*c, w, h, a), rotation_deg=a, entrance_m=door, access_road_id=parent)
        if poi:
            f['poi_id'] = poi
        d['functional_buildings'].append(f)


def build_industry(d):
    fs = {f['id']: f for f in d['functional_buildings']}
    pts = {p['id']: p for p in d['points']}
    for fid, (c, w, h, a, door, poi, radius) in INDUSTRY.items():
        if fid not in fs:
            f = dict(id=fid, type='storage_tank', district='industrial', district_id='industrial', label_ru='Резервуар',
                     group='industry', storeys=1, footprint_shape='round', color='#928ba4', icon='П', height_target_m=12)
            d['functional_buildings'].append(f)
            fs[fid] = f
        f = fs[fid]
        f.update(center_m=c, width_m=w, depth_m=h, rotation_deg=a, entrance_m=door, access_road_id='I_YARD',
                 footprint_m=circle(c, radius) if radius else m.rectangle(*c, w, h, a))
        if poi:
            pts[poi].update(position_m=door, district_id='industrial')
    fs['F06_CHIMNEY']['height_target_m'] = 85
    fs['F06_DEPOT']['label_ru'] = 'Депо'
    sites = {s['id']: s for s in d['functional_sites']}
    sites['B05_YARD']['polygon_m'] = oval(*B05_YARD, 36)
    sites['F06_TOW_YARD'].update(polygon_m=oval(*TOW_LOT, 28), capacity_vans=8)
    sites['CANAL_BEACH_CULVERT']['district_id'] = None
    d['functional_sites'].append(dict(id='DEPOT13_RAIL_STUB', type='rail_stub', district_id='industrial',
        building_id='F06_DEPOT', polyline_m=DEPOT_STUB, dressing_only=True, embedded_in_pavement=True,
        label_ru='Тупиковый путь у депо со старым вагоном'))
    d['outfalls'] = [dict(id='OUTFALL_B05', source_building_id='F06_COMPLEX', polyline_m=OUTFALL, diameter_m=.8,
        length_m=plen(OUTFALL), sleeves_under=['I_YARD', 'quay'], plume_id='PLUME_B05',
        plume=dict(id='PLUME_B05', polygon_m=oval(*PLUME, 32), area_m2=round(m.area(oval(*PLUME, 32)), 1),
                   colour='brown-green', label_ru='Грязное пятно в воде'),
        dressing_hints_ru=['дохлая рыба у трубы', 'два знака «купаться запрещено»: на набережной и на СВ скалах пляжа'],
        label_ru='Слив промзоны в море')]
    d['sightline'].update(from_position_m=pts['B01']['position_m'], to_position_m=fs['F06_CHIMNEY']['center_m'],
        status='proposed 3D sightline B01 -> chimney; keep a tree gap NE of the clearing; confirm in Unity')


def build_parking(d):
    add_functions(d, PARK_BUILDINGS, 'beach_parking')
    for lot, (c, x0, aisle, walk_x) in LOTS.items():
        bay_list = bays(lot)
        d['functional_sites'].append(dict(id=lot, type='parking', district_id='beach_parking',
            polygon_m=m.rectangle(*c, 43, 21, 0), aisle_road_id=aisle, bays=bay_list,
            capacity_vans=sum(b['usable'] for b in bay_list), label_ru='Пляжная парковка'))
    d['functional_sites'] += [
        dict(id='PARK13_DROP_OFF', type='drop_off', district_id='beach_parking', polygon_m=oval(*DROP_OFF, 24),
             label_ru='Высадка у пляжа'),
        *[dict(id=tid, type='turning_head', district_id='beach_parking', polygon_m=circle(c, TURN_R, 24), diameter_m=2*TURN_R,
               road_id=rid, label_ru='Разворот в конце ряда') for tid, (c, rid) in TURN_HEADS.items()],
        dict(id='PARK13_BOLLARDS', type='bollard_line', district_id='beach_parking', polyline_m=curve(BOLLARDS, 4),
             post_height_m=.9, post_spacing_m=1.6, blocks_van=True, blocks_foot=False, dressing_only=True,
             label_ru='Столбики: люди проходят, бусик нет')]
    d['points'].append(dict(id='BEACH_PARK_ENTRY', canonical_id='BEACH_PARK_ENTRY', name_ru='Пляжная парковка',
        position_m=[652, 353], district_id='beach_parking', category='poi', label_offset_px=[0, 0]))


def build_roads(d, original):
    old = {r['id']: r for r in original['roads']}
    d['roads'] = [r for r in d['roads'] if r['id'] not in DROPPED_ROADS]
    roads = {r['id']: r for r in d['roads']}
    pts = {p['id']: p for p in d['points']}

    def snap(p, rid):
        return list(nearest(p, roads[rid]['polyline_m'])[1])

    def make(rid, controls, cls, dids, start=None, end=None, **kw):
        controls = [list(p) for p in expand(controls)]
        if start:
            controls[0] = snap(controls[0], start)
        if end:
            controls[-1] = snap(controls[-1], end)
        q = dict(id=rid, **{'class': cls}, width_m=WIDTHS[cls], district_ids=dids,
                 polyline_m=curve(controls) if len(controls) > 2 else controls,
                 lanes=1 if cls in ('rural_road', 'alley') else 2, **kw)
        if start or end:
            q['joins_road_ids'] = [x for x in (start, end) if x]
        if rid in roads:
            d['roads'][d['roads'].index(roads[rid])] = q
        else:
            d['roads'].append(q)
        roads[rid] = q
        return q
    for rid, controls, cls, dids, start, end in ROADS:
        arches = [f'{p}_ARCH' for p in controls if isinstance(p, str)]
        extra = {'van_through_arch_ids': arches} if arches else {}
        if rid.startswith('PARK_AISLE'):
            extra = dict(approved_straight_exception='car-park aisle between two straight bay rows',
                         turning_head_site_id=next(t for t, (c, r) in TURN_HEADS.items() if r == rid))
        make(rid, controls, cls, dids, start, end, **extra)
    roads['I_CONNECT']['district_ids'] = ['old_town', 'beach_parking']

    def access(rid, door, parent, did, controls=None):
        cls = old.get(rid, {}).get('class') or ('town_street' if parent in ('ARC_AVENUE', 'I_YARD') else 'rural_road')
        line = [list(p) for p in (controls or [door, door])]
        line[0], line[-1] = snap(line[0], parent), list(door)
        return make(rid, line, cls, [did], access_only=True, parent_road_id=parent)
    access('ACCESS_B01', pts['B01']['position_m'], 'START_ROAD', 'forest')
    church = next(f for f in d['functional_buildings'] if f['id'] == 'F06_CHURCH')
    access('ACCESS_F06_CHURCH', church['entrance_m'], 'CHURCH_LANE', 'village', [[190, 709], [186, 717], church['entrance_m']])
    # Pharmacy driveway now leaves V_MAIN 16 m after the START_ROAD junction: B01 -> P03 gets a ~15 m margin under 200 m.
    access('ACCESS_P03', pts['P03']['position_m'], 'V_MAIN', 'village', [[247.5, 583], [258, 580], [266, 575.5], pts['P03']['position_m']])
    for rid, o in HAMLET_BENDS.items():
        r = roads[rid]
        a, b = r['polyline_m'][0], r['polyline_m'][-1]
        u = [b[0]-a[0], b[1]-a[1]]
        n = [-u[1]/math.hypot(*u), u[0]/math.hypot(*u)]
        r['polyline_m'] = curve([a, [a[0]+u[0]/3+n[0]*o, a[1]+u[1]/3+n[1]*o], [a[0]+u[0]*2/3-n[0]*o, a[1]+u[1]*2/3-n[1]*o], b])
        r['reshaped_v13_ru'] = f'плавная S-кривая ±{o} м вместо прямой (органичные дороги)'
    for fid, (c, w, h, a, door, poi, radius) in INDUSTRY.items():
        access('ACCESS_'+(poi or fid), door, 'I_YARD', 'industrial')
    for fid, row in BUSINESSES.items():
        access('ACCESS_'+(row[11] or fid), row[7], row[12], 'residential')
    access('ACCESS_F13_PARK_KIOSK', PARK_BUILDINGS['F13_PARK_KIOSK'][7], 'PARK_ROAD', 'beach_parking',
           [[652, 353], [644, 348.5], PARK_BUILDINGS['F13_PARK_KIOSK'][7]])
    access('ACCESS_F13_PARK_WC', PARK_BUILDINGS['F13_PARK_WC'][7], 'PARK_ROAD', 'beach_parking',
           [[652, 353], [660, 348.5], PARK_BUILDINGS['F13_PARK_WC'][7]])
    # Reference and service points that now sit directly on the new lanes.
    on_road = {'P09-3': ([792, 729], 'I_ACCESS', 'industrial'), 'P13-4': ([606, 673.8], 'ALLEY_S', 'residential'),
               'BAD_BLOCK': ([522, 784], 'ALLEY_W', 'residential'), 'BAD_BLOCK_2': ([573.3, 753], 'COURT_B', 'residential'),
               'BAD_BLOCK_3': ([585.5, 785], 'ALLEY_X', 'residential')}
    for pid, (p, rid, did) in on_road.items():
        pts[pid].update(position_m=[round(z, 4) for z in snap(p, rid)], district_id=did)
    site = next(s for s in d['functional_sites'] if s['id'] == 'SITE_P09-3')
    site['position_m'] = pts['P09-3']['position_m'][:]
    site['label_ru'] = 'Запасная: у ворот промзоны'
    pts['P09-3']['name_ru'] = 'Запасная: у ворот B05'
    # Walk-only network: foot lanes of the alleys, forest trails, car-park paths onto the sand.
    ways = dict(roads)
    ways.update({p['id']: p for p in d['paths']})
    hill_path = spiral(HILL_C, 33, 3, math.radians(160), 1.6)
    for pid, controls, cls, dids, start, end in PATHS:
        through = [f'{p}_ARCH' for p in controls if isinstance(p, str)]
        controls = [list(p) if p is not None else hill_path[0] for p in expand(controls)]
        if start:
            controls[0] = list(nearest(controls[0], ways[start]['polyline_m'])[1])
        if end:
            controls[-1] = list(nearest(controls[-1], ways[end]['polyline_m'])[1])
        q = dict(id=pid, **{'class': cls}, width_m=WIDTHS[cls], polyline_m=curve(controls) if len(controls) > 2 else controls,
                 district_id=dids[0], district_ids=dids, walkable=True, van_access=False)
        if start or end:
            q['joins_way_ids'] = [x for x in (start, end) if x]
        if through:
            q['through_arch_ids'] = through
        d['paths'].append(q)
        ways[pid] = q
    d['paths'].append(dict(id='PATH_HILL_SPIRAL', **{'class': 'trail'}, width_m=WIDTHS['trail'], polyline_m=hill_path,
        district_id='forest', district_ids=['forest'], walkable=True, van_access=False, turns=1.6, summit_m=hill_path[-1]))
    for p in d['paths']:
        if p['id'] == 'TRAIL_SWAMP':
            p['ends_as'] = 'boardwalk jetty into SWAMP_POND_4'
        if p['id'] == 'CLEARING_LINK':
            p['note'] = 'steps over the rail stub east of the wagon'
    for r in d['roads']+d['paths']:
        r['length_m'] = plen(r['polyline_m'])


def build_fences(d):
    keep = [q for q in d['vegetation_parcels'] if q['id'] not in REMOVED_BARRIERS]
    d['removed_barriers'] = [dict(id=q['id'], kind=q['kind'], material=q['material'], district_id=q.get('district_id'),
        axis_from_m=q['axis_m'][0], axis_to_m=q['axis_m'][-1], length_m=plen(q['axis_m']), gate_road_ids=q.get('gate_road_ids', []),
        replaced_by_ids=REMOVED_BARRIERS[q['id']][0], reason_ru=REMOVED_BARRIERS[q['id']][1])
        for q in d['vegetation_parcels'] if q['id'] in REMOVED_BARRIERS]
    for q in keep:
        if q['id'].startswith('CANAL_RAILING_S'):
            q['district_id'] = None
    d['vegetation_parcels'] = keep

    def barrier(fid, axis, material, did, role, gates=(), group=None, foot=True, **kw):
        d['vegetation_parcels'].append(dict(id=fid, kind='interdistrict_barrier', district_id=did,
            polygon_m=offset(axis, .5)+list(reversed(offset(axis, -.5))), axis_m=axis, blocks_foot=foot,
            blocks_van=True, material=material, height_target_m=FENCE_HEIGHTS[material], tree_line=False,
            continuity_group=group or fid, gate_road_ids=list(gates), barrier_role=role, **kw))
    gate = dict(road_id='I_ACCESS', posts_m=[FENCE_W[-1], FENCE_S[0]], width_m=round(m.length(FENCE_W[-1], FENCE_S[0]), 2))
    barrier('INDUSTRIAL_FENCE_W', v12.sample_line(curve(FENCE_W, 3), 1.5), 'barbed_fence', 'industrial', 'property_fence',
            ['I_ACCESS'], 'INDUSTRIAL_FENCE', gate=gate, ends_ru='север: врезка в скальный край карты; юг: столб ворот')
    barrier('INDUSTRIAL_FENCE_S', v12.sample_line(curve(FENCE_S, 3), 1.5), 'barbed_fence', 'industrial', 'property_fence',
            ['I_ACCESS'], 'INDUSTRIAL_FENCE', gate=gate, ends_ru='запад: столб ворот; восток: у воды, 13 м севернее скал пляжа')
    barrier('COVE_WEST_ROCKS_1', v12.sample_line([COVE_LAND[0], COVE_SEA[0]], 1.5), 'rock_scarp', 'forest',
            'natural_closure', (), 'COVE_ACCESS_CONTROL')
    # Natural closure on top of the beach where the v12 valley and industrial fences stood: a low dune with
    # driftwood posts. Walkers cross it anywhere; the van only gets onto the sand by the two authorised roads.
    roads = {r['id']: r for r in d['roads']}
    gap_road = roads['BEACH_VALLEY_ACCESS']['polyline_m']
    edge = d['beaches'][0]['land_edge_m']
    i0 = min(range(len(edge)), key=lambda i: m.length(edge[i], DUNE_FROM))
    i1 = min(range(len(edge)), key=lambda i: m.length(edge[i], DUNE_TO))
    pts = v12.sample_line(edge[i0:i1+1], 1.5)
    half = WIDTHS[roads['BEACH_VALLEY_ACCESS']['class']]/2+1.2
    west = [p for p in pts if p[0] < 421 and nearest(p, gap_road)[0] >= half]
    east = [p for p in pts if p[0] > 421 and nearest(p, gap_road)[0] >= half]
    for fid, axis in (('BEACH_DUNE_W', west), ('BEACH_DUNE_E', east)):
        barrier(fid, [[round(x, 3), round(y, 3)] for x, y in axis], 'dune_ridge', None, 'natural_closure', ['BEACH_VALLEY_ACCESS'],
                'BEACH_LAND_EDGE', foot=False, label_ru='Дюна с плавником: люди проходят, бусик нет')


MOVE_REASONS = {
    'Вагон стоит на ветке к тоннелю у поляны, где бухают (референс Феди).':
        [('point', 'B01'), ('building', 'F06_WAGON'), ('building_mass', 'WAGON06')],
    'Пост СЗ и тупик перенесены на 60+ м южнее церковного двора: угол хутора остаётся церкви (ревью).': [('point', 'P16'), ('exit', 'NW')],
    'Церковь из перехода в хутор, сверху слева (Федя).': [('building', 'F06_CHURCH'), ('site', 'CHURCH12_YARD')],
    'Промзона перенесена в правый верхний угол (Федя).':
        [('point', 'B05'), ('building', 'F06_COMPLEX'), ('point', 'CHIMNEY'), ('building', 'F06_CHIMNEY'),
         ('point', 'P12'), ('building', 'F06_TOW'), ('site', 'F06_TOW_YARD'), ('point', 'P14'), ('building', 'F06_DEPOT'),
         ('building', 'F06_WARE1'), ('building', 'F06_MAINT'), ('site', 'B05_YARD'), ('point', 'P09-3'), ('site', 'SITE_P09-3')],
    'Банкомат теперь в новом магазине «Продукты · банкомат».': [('point', 'P11-2')],
    'Мусорки стоят прямо на проезде ALLEY_S (без отдельного подъезда).': [('point', 'P13-4')],
    'Ориентиры дворов стали подворотнями нового района.': [('point', 'BAD_BLOCK'), ('point', 'BAD_BLOCK_2'), ('point', 'BAD_BLOCK_3')],
}


def positions(d):
    out = {}
    for p in d['points']:
        out['point', p['id']] = p['position_m']
    for f in d['functional_buildings']:
        out['building', f['id']] = f['center_m']
    for b in d['building_masses']:
        out['building_mass', b['id']] = b['center_m']
    for s in d['functional_sites']:
        out['site', s['id']] = s.get('position_m') or centroid(s.get('polygon_m') or s.get('polyline_m'))
    for p in d['plots']:
        out['plot', p['id']] = centroid(p['polygon_m'])
    for e in d['exits']:
        out['exit', e['id']] = e['dead_end_m']
    for w in d['water']:
        if 'polygon_m' in w and w['id'] != 'SEA':
            out['water', w['id']] = centroid(w['polygon_m'])
    return out


def record_moves(d, original):
    before, after = positions(original), positions(d)
    d['moves'] = []
    for reason, keys in MOVE_REASONS.items():
        for key in keys:
            a, b = before[key], after[key]
            d['moves'].append(dict(kind=key[0], id=key[1], from_m=a, to_m=b, distance_m=round(m.length(a, b), 2),
                                   id_kept=True, reason_ru=reason))
    d['land_transfers'] = [
        dict(ids=['F06_CHURCH', 'CHURCH12_YARD'], from_district='transition', to_district='village',
             note_ru='Старое место церкви в переходе стало газоном.'),
        dict(ids=['CANAL_RAILING_S_1', 'CANAL_RAILING_S_2', 'CANAL_BEACH_CULVERT'], from_district='industrial',
             to_district=None, note_ru='Геометрия без изменений; теперь общая зелень между каналом и парковкой (district_id null).'),
        dict(ids=['residential'], from_district='residential', to_district=None,
             note_ru='Район подворотен ужат по кварталам: пустой север за R_REAR и юго-восток (x 710–780, y 628–712) — общая зелень.'),
        dict(ids=['beach_parking'], from_district='beach_parking', to_district=None,
             note_ru='Пляжная парковка — только асфальт с местами (~5 800 м²); остальная полоса бывшей промзоны — зелень с деревьями.'),
        dict(ids=['industrial'], from_district='south strip above the beach', to_district='NE corner on a new quay',
             note_ru='Id района сохранён; старый участок — пляжная парковка и общая зелень с деревьями.'),
        dict(ids=['forest'], from_district='forest strip', to_district='forest down to the new cove',
             note_ru='Лес вырос за счёт общей зелени и новой суши на юго-западе.'),
    ]


def notes(d):
    d['planning_notes_ru'] = [
        'Неблагополучный район целиком заменён районом подворотен: 11 панелек 5–9 этажей в 5 маленьких кварталах севернее проспекта и 2 южнее.',
        'Через дома — 10 арок-подворотен (2 для бусика); проезды 4,5 м и пешие проходы 3 м режут кварталы на крошечные дворы 10–20 м.',
        'Панельки чередуются с лавками: дискаунтер, «Продукты · банкомат», пиво, ломбард, шаурма, займы, ставки, рюмочная, бар, ларьки, 24 ч.',
        'Притон P07 оставлен «похихикать»; за подворотней один ряд гаражей-ракушек; пустые север и юго-восток отданы общей зелени.',
        'Хутор по картинке Феди: церковь в СЗ углу с площадкой на хуторскую улицу, пять полосатых полей, извилистые подъезды.',
        'Пост СЗ P16 и тупик перенесены на 60+ м южнее церковного двора, к западному краю хутора.',
        'Лес по картинке: болото слева, озеро справа, холм со спиралью снизу, тропы, лес выходит к бухте; по краю скалы.',
        'Вагон B01 стоит на рельсах, уходящих в тоннель в скале; рядом поляна: костёр, брёвна, палатка, бутылки, ящик.',
        'Промзона в правом верхнем углу: кольцевой проезд, B05 с трубой, P12, депо P14, склад, сарай, резервуар.',
        'Колючая проволока только по западу и югу промзоны (по её изгибу), с воротами; слив B05 в море, у трубы грязное пятно.',
        'На месте старой промзоны — компактная пляжная парковка: 46 мест, развороты, высадка, киоск, туалет, три тропинки на песок.',
        'Заборов на границах районов нет; над пляжем — дюна с плавником (люди проходят, бусик нет); колючка только у промзоны.',
        'Зона перехода, старый город, элитка и основной пляж не тронуты; в долине убрана только ЖД к старой промзоне.',
    ]
    d['distribution_targets'] = {'policy': 'v13: alley district of 11 panel houses with 10 arches and interleaved businesses; '
                                           'empty north strip and SE quarter returned to common green'}


def build_graph(data):
    m.build_graph(data)
    for e in data['road_graph']['edges']:
        if e['class'] in WALK:
            e['van_access'] = False


ROUTE_PAIRS = [('B01', 'P01'), ('B01', 'P02'), ('B01', 'P03'), ('B01', 'BAD_CENTER'), ('B01', 'CLOCK_SQUARE'),
               ('B02', 'BAD_CENTER'), ('B02', 'CLOCK_SQUARE'), ('BAD_CENTER', 'CLOCK_SQUARE'), ('CLOCK_SQUARE', 'ELITE_GATE'),
               ('B01', 'B06'), ('B06', 'BEACH_VALLEY_ENTRY'), ('ELITE_GATE', 'BEACH_ENTRY'), ('BAD_CENTER', 'B05'),
               ('CLOCK_SQUARE', 'B05'), ('B01', 'B05'), ('CLOCK_SQUARE', 'BEACH_PARK_ENTRY'), ('B03', 'P07'), ('B03', 'P08'),
               ('P08', 'P12'), ('B04', 'P09-3'), ('B01', 'P16')]


def node_at(graph, p):
    key = [round(p[0], 3), round(p[1], 3)]
    return next((n['id'] for n in graph['nodes'] if n['position_m'] == key), None)


def arch_list(d):
    return [(b['id'], a) for b in d['building_masses'] for a in b.get('gateway_arches', [])]


def analyse(d, strict=True):
    build_graph(d)
    checks = []

    def check(name, ok, detail=''):
        checks.append(dict(name=name, passed=bool(ok), detail=str(detail)[:700]))
    original = source_data()
    ds = {q['id']: q for q in d['districts']}
    pts = {p['id']: p for p in d['points']}
    fs = {f['id']: f for f in d['functional_buildings']}
    bs = {b['id']: b for b in d['building_masses']}
    roads = {r['id']: r for r in d['roads']}
    paths = {p['id']: p for p in d['paths']}
    ways = dict(roads)
    ways.update(paths)
    sites = {s['id']: s for s in d['functional_sites']}
    waters = {w['id']: w for w in d['water']}
    phys = v7.physical(d)
    polys = {b['id']: b['poly'] for b in phys}
    bp = d['boundary']['polygon_m']
    beach, cove = d['beaches'][0], d['beaches'][1]
    sea = waters['SEA']
    counts = Counter(b['district_id'] for b in phys)
    bounds = [min(p[0] for p in bp), min(p[1] for p in bp), max(p[0] for p in bp), max(p[1] for p in bp)]
    extent = [round(bounds[2]-bounds[0], 3), round(bounds[3]-bounds[1], 3)]
    for q in d['districts']:
        q.update(area_m2=round(m.area(q['polygon_m']), 3), building_count=counts[q['id']],
                 share_percent=round(m.area(q['polygon_m'])/m.area(bp)*100, 3))
    ped = copy.deepcopy(d)
    ped['roads'] += copy.deepcopy(d['paths'])
    build_graph(ped)
    d['pedestrian_graph'] = ped['road_graph']
    pedpts = {p['id']: p for p in ped['points']}
    er = {e['id']: e for e in d['road_graph']['edges']}
    routes = []
    for a, b in ROUTE_PAIRS:
        dist, ids = m.shortest(d, pts[a]['road_node_id'], pts[b]['road_node_id'])
        walk, wids = m.shortest(ped, pedpts[a]['road_node_id'], pedpts[b]['road_node_id'], mode='walk')
        rids = []
        for eid in ids:
            if not rids or rids[-1] != er[eid]['road_id']:
                rids.append(er[eid]['road_id'])
        routes.append(dict(from_id=a, to_id=b, length_m=round(dist, 3), edge_ids=ids, road_ids=rids,
            pedestrian_length_m=round(walk, 3), pedestrian_edge_ids=wids, van_60_seconds=round(dist/(60/3.6), 2),
            van_90_seconds=round(dist/(90/3.6), 2), walk_5_minutes=round(walk/(5000/60), 2)))
    lengths = {(r['from_id'], r['to_id']): r['length_m'] for r in routes}
    # ------------------------------------------------------------ v12 checks kept
    check('playable extent <=1000m on both axes', max(extent) <= 1000, extent)
    for pid in ('P01', 'P02', 'P03'):
        check('B01 -> '+pid+' <=200m', lengths['B01', pid] <= 200, lengths['B01', pid])
    check('B01 -> bad centre >=400m', lengths['B01', 'BAD_CENTER'] >= 400, lengths['B01', 'BAD_CENTER'])
    check('bad centre -> square <=200m', lengths['BAD_CENTER', 'CLOCK_SQUARE'] <= 200, lengths['BAD_CENTER', 'CLOCK_SQUARE'])
    check('square -> elite gate <=200m', lengths['CLOCK_SQUARE', 'ELITE_GATE'] <= 200, lengths['CLOCK_SQUARE', 'ELITE_GATE'])
    for label, poly in [('boundary', bp), ('beach', beach['polygon_m']), ('forest cove', cove['polygon_m'])]+[(q['id'], q['polygon_m']) for q in d['districts']]:
        check(label+' polygon simple', simple(poly))
        if 'beach' not in label and 'cove' not in label:
            check(label+' smooth organic outline', len(poly) >= 40 and turn_max(poly) < 42, f'{len(poly)} vertices / turn {turn_max(poly):.2f}deg')
    overlap = [(a['id'], b['id']) for i, a in enumerate(d['districts']) for b in d['districts'][i+1:] if strict_overlap(a['polygon_m'], b['polygon_m'])]
    check('district envelopes do not overlap', not overlap, overlap)
    outside = [q['id'] for q in d['districts'] if any(not contained(p, bp) for p in q['polygon_m'])]
    check('district envelopes within playable boundary', not outside, outside)
    hits = [(a['id'], b['id']) for i, a in enumerate(phys) for b in phys[i+1:] if strict_overlap(a['poly'], b['poly'])]
    check('building footprints do not overlap', not hits, hits)
    outside = [b['id'] for b in phys if any(not contained(p, bp) or not contained(p, ds[b['district_id']]['polygon_m']) for p in b['poly'])]
    check('every building inside its district and playable boundary', not outside, outside)
    own = {f['id']: 'ACCESS_'+(f.get('poi_id') or f['id']) for f in fs.values()}
    own.update({b['id']: 'ACCESS_'+b['id'] for b in bs.values()})
    arches = arch_list(d)

    def through_arch(bid, a, c):
        mid = [(a[0]+c[0])/2, (a[1]+c[1])/2]
        return any(owner == bid and m.projection(mid, *arch['axis_m'])[0] < arch['width_m']/2+.6 for owner, arch in arches)
    road_hits = []
    for b in phys:
        for r in d['roads']+d['paths']:
            if r['id'] == own.get(b['id']):
                continue
            if any(v7.gap(b['poly'], a, c) < r['width_m']/2-.01 and not through_arch(b['id'], a, c)
                   for a, c in zip(r['polyline_m'], r['polyline_m'][1:])):
                road_hits.append((b['id'], r['id']))
    check('buildings clear of roads, driveways and paths (gateway arches and own driveway exempt)', not road_hits, road_hits)
    wet = []
    for b in phys:
        for w in d['water']:
            if ('polygon_m' in w and strict_overlap(b['poly'], w['polygon_m'])) or any(
                    v7.gap(b['poly'], a, c) < w['width_m']/2 for a, c in zip(w.get('centerline_m', []), w.get('centerline_m', [])[1:])):
                wet.append((b['id'], w['id']))
    check('buildings clear of lakes, ponds, rivers, canal and sea', not wet, wet)
    rail = d['railway']['polyline_m']
    railhits = [b['id'] for b in phys if b['id'] != 'F06_WAGON' and any(v7.gap(b['poly'], a, c) < 2 for a, c in zip(rail, rail[1:]))]
    check('railway 4m corridor clear of buildings except the wagon on it', not railhits, railhits)
    for label, g in [('vehicle', d['road_graph']), ('walk', d['pedestrian_graph'])]:
        seen = v11.reachable(g, g['nodes'][0]['id'])
        check(label+' graph connected', len(seen) == len(g['nodes']), f'{len(seen)}/{len(g["nodes"])}')
    bad_class = [r['id'] for r in d['roads']+d['paths'] if r['width_m'] != WIDTHS[r['class']] or r.get('lanes', 1) > 2 or
                 (r['class'] in ('rural_road', 'alley') and r['lanes'] != 1)]
    bad_class += [r['id'] for r in d['roads'] if r['class'] in WALK]+[p['id'] for p in d['paths'] if p['class'] not in WALK]
    check('exact road classes, widths and lane limits (alley 4.5/1, foot lane 3, trail 2)', not bad_class and
          {'alley', 'foot_lane', 'trail'} <= set(d['road_classes']), bad_class)
    check('walk-only classes excluded from vehicle graph', all(e['van_access'] and e['class'] not in WALK for e in d['road_graph']['edges']))
    long_axis = []
    for r in d['roads']:
        if r.get('approved_straight_exception'):
            continue
        for a, b in zip(r['polyline_m'], r['polyline_m'][1:]):
            if m.length(a, b) > 35 and min(abs(a[0]-b[0]), abs(a[1]-b[1])) < .02:
                long_axis.append(r['id'])
    check('no long axis-aligned streets outside approved exceptions', not long_axis, long_axis)
    check('approved continuous straight avenue retained', roads['ARC_AVENUE']['polyline_m'] == [[470, 723.5], [770, 723.5]] and
          m.length(roads['ARC_RURAL']['polyline_m'][-1], roads['ARC_AVENUE']['polyline_m'][0]) < .001)
    ofs = {f['id']: f for f in original['functional_buildings']}
    check('villa record exactly v12', fs['F07_VILLA'] == ofs['F07_VILLA'])
    check('villa terrace faces north toward the lake', fs['F07_VILLA']['lake_facing_direction'] == 'north' and
          sites['VILLA07_TERRACE']['polygon_m'][0][1] > 537)
    lake = waters['LAKE']
    check('lake at 435,575 inside transition', lake['center_m'] == [435, 575] and all(contained(p, ds['transition']['polygon_m']) for p in lake['polygon_m']))
    yard = sites['CHURCH12_YARD']
    check('churchyard present around the church', yard['type'] == 'churchyard' and yard['building_id'] == 'F06_CHURCH' and
          all(m.inside(p, yard['polygon_m']) for p in fs['F06_CHURCH']['footprint_m']))
    c = fs['F06_CHURCH']['center_m']
    check('church in the hamlet top-left (village, x<=200, y>=720)', fs['F06_CHURCH']['district_id'] == 'village' and
          c[0] <= 200 and c[1] >= 720 and yard['district_id'] == 'village', c)
    check('only one cafe, purchasable', sum(f['type'] == 'cafe' for f in fs.values()) == 1 and fs['F06_CAFE2']['purchasable'])
    check('old town keeps 19 buildings, mandatory functions and two towers', counts['old_town'] == 19 and
          {'F06_HBASE', 'F06_REPAIR', 'F06_POLICE', 'F06_BANK', 'F06_SUPER', 'F06_CAFE2'} <= set(fs) and
          len([b for b in bs.values() if b['district_id'] == 'old_town' and b['floors'] >= 12]) == 2, counts['old_town'])
    check('P09 behind supermarket away from its front door', pts['P09']['position_m'][0] > 598 and pts['P09']['position_m'][1] > 600)
    check('B02 and P04 separate short branches', fs['F06_HUT']['access_road_id'] == 'HUT_BRANCH' and
          fs['F06_BUYER']['access_road_id'] == 'RECEPTION_BRANCH' and roads['HUT_BRANCH']['length_m'] < 40 and roads['RECEPTION_BRANCH']['length_m'] < 40)
    check('transition retains gas, ruins and P09-4', {'F06_GAS', 'F06_RUINS'} <= set(fs) and 'P09-4' in pts)
    industry = {f['id'] for f in fs.values() if f['district_id'] == 'industrial'}
    inside_ne = all(contained(p, ds['industrial']['polygon_m']) for fid in industry for p in fs[fid]['footprint_m'])
    check('industrial set: six v12 structures plus tank, all inside the NE polygon', industry ==
          {'F06_COMPLEX', 'F06_CHIMNEY', 'F06_TOW', 'F06_DEPOT', 'F06_WARE1', 'F06_MAINT', 'F13_TANK'} and inside_ne, sorted(industry))
    venues = [f for f in fs.values() if f['id'].startswith('F12_')]
    check('casino, club and bowling retained in the valley', len(venues) == 3 and fs['F12_CASINO']['type'] == 'casino' and
          2 <= fs['F12_CASINO']['storeys'] <= 3 and all(f['district_id'] == 'fields' for f in venues))
    check('casino parking supplied', sites['CASINO12_PARKING']['capacity_vans'] >= 6)
    # ALLEY_S makes the through-alley route 9 m shorter; the bypass must still exist and stay competitive.
    alley_roads = [r['id'] for r in d['roads'] if 'residential' in r['district_ids']]
    trimmed = copy.deepcopy(d)
    trimmed['roads'] = [r for r in d['roads'] if r['id'] not in alley_roads]
    trimmed['points'] = [p for p in trimmed['points'] if p['id'] in ('B02', 'CLOCK_SQUARE')]
    trimmed['exits'] = []
    build_graph(trimmed)
    tp = {p['id']: p for p in trimmed['points']}
    bypass, bids = m.shortest(trimmed, tp['B02']['road_node_id'], tp['CLOCK_SQUARE']['road_node_id'])
    bypass_roads = {e['road_id'] for e in trimmed['road_graph']['edges'] if e['id'] in set(bids)}
    shortest_b02 = lengths['B02', 'CLOCK_SQUARE']
    check('transition direct road still bypasses the alley district (<=5% longer than the shortest route)',
          'TRANSITION_DIRECT' in bypass_roads and bypass <= shortest_b02*1.05, f'bypass {bypass:.1f}m vs shortest {shortest_b02:.1f}m')
    ogardens = {p['id']: p for p in original['plots'] if p['kind'] == 'elite_garden'}
    gardens = [p for p in d['plots'] if p['kind'] == 'elite_garden']
    check('four elite gardens exactly v12', len(gardens) == 4 and all(p == ogardens[p['id']] for p in gardens))
    walk_end = paths['WALK_BEACH']['polyline_m']
    park_paths = [p for p in ('PATH_BEACH_W', 'PATH_BEACH_C', 'PATH_BEACH_E') if nearest(paths[p]['polyline_m'][-1], walk_end)[0] < .01]
    check('beach entrances: exactly two vehicle roads plus car-park walk paths', beach['access_road_ids'] == ['BEACH_ACCESS', 'BEACH_VALLEY_ACCESS']
          and cove['access_road_ids'] == [] and len(park_paths) >= 2, park_paths)
    touching = [r['id'] for r in d['roads'] if any(m.inside(p, beach['polygon_m']) or m.inside(p, cove['polygon_m']) for p in r['polyline_m'])]
    check('no other road enters the beach or the cove', set(touching) == set(beach['access_road_ids']), touching)
    for pid in ('BEACH_ENTRY', 'BEACH_VALLEY_ENTRY'):
        removed = v11.reachable(d['road_graph'], pts['B01']['road_node_id'], removed_roads=beach['access_road_ids'])
        check(pid+' cut off when both authorized entrances removed', pts[pid]['road_node_id'] not in removed)
    check('beach width 45–60m along whole curve', all(45 <= m.length(a, b) <= 60 for a, b in zip(beach['land_edge_m'], beach['sea_edge_m'])))
    check('sea offshore band >=150m and return rule retained', sea['offshore_band_m'] >= 150 and sea['return_rule'] == 'return_to_last_ground_point')
    coast = [a for a, b in d['boundary']['coast_segments_m']]+[d['boundary']['coast_segments_m'][-1][1]]
    offshore = sea['polygon_m'][len(coast):]
    clearance = min(nearest(p, coast)[0] for p in offshore)
    check('sea measured >=150m beyond cove, beach and quay', clearance >= 150, f'{clearance:.3f}m')
    check('sea polygon simple and entirely outside playable land', simple(sea['polygon_m']) and not strict_overlap(sea['polygon_m'], bp))
    check('districts do not overlap beaches or sea', not any(strict_overlap(q['polygon_m'], s) for q in d['districts']
          for s in (beach['polygon_m'], cove['polygon_m'], sea['polygon_m'])))
    check('beach and cove touch only along the rocks', not strict_overlap(beach['polygon_m'], cove['polygon_m']))
    check('roads and walking paths inside playable boundary', all(all(contained(p, bp) for p in r['polyline_m']) for r in d['roads']+d['paths']))
    check('beach walking path entirely in sand', all(contained(p, beach['polygon_m']) for p in walk_end))
    dry = [(r['id'], w['id']) for r in d['roads'] for w in d['water'] if 'polygon_m' in w and
           any(v7.gap(w['polygon_m'], a, b) < r['width_m']/2-.01 for a, b in zip(r['polyline_m'], r['polyline_m'][1:]))]
    check('vehicle roads clear of every water polygon (lakes, ponds, sea)', not dry, dry)
    owaters = {w['id']: w for w in original['water']}
    check('lake, rivers and canal exactly v12', all(waters[k] == owaters[k] for k in ('LAKE', 'RIVER_N', 'RIVER_S', 'CANAL')))
    rivers = {w['id']: w for w in d['water'] if w['id'].startswith('RIVER')}
    canal = waters['CANAL']
    check('river remains connected from lake to canal', contained(rivers['RIVER_N']['centerline_m'][-1], lake['polygon_m']) and
          contained(rivers['RIVER_S']['centerline_m'][0], lake['polygon_m']) and m.length(rivers['RIVER_S']['centerline_m'][-1], canal['centerline_m'][0]) < .01)
    unprotected = []
    for r in d['roads']:
        for w in d['water']:
            for a, b in zip(r['polyline_m'], r['polyline_m'][1:]):
                for c2, e in zip(w.get('centerline_m', []), w.get('centerline_m', [])[1:]):
                    hit = m.crossing(a, b, c2, e)
                    if hit and not any(s['road_id'] == r['id'] and s['water_id'] == w['id'] and m.length(s['position_m'], hit[0]) < 8
                                       for s in d['water_crossings']):
                        unprotected.append((r['id'], w['id']))
    check('every road/water intersection has a bridge or culvert', not unprotected, unprotected)
    check('water crossings still exactly S01 culvert and S02 bridge', [(s['id'], s['road_id'], s['kind']) for s in d['water_crossings']] ==
          [(s['id'], s['road_id'], s['kind']) for s in original['water_crossings']], d['water_crossings'])
    segs = d['boundary']['coast_segments_m']
    check('coast: cove + beach + quay, >100 short consecutive segments, no wall', len(segs) > 100 and max(m.length(a, b) for a, b in segs) < 20 and
          all(segs[i][1] == segs[i+1][0] for i in range(len(segs)-1)) and coast == bp[:len(coast)] and
          beach['sea_edge_m'] == coast[len(cove['sea_edge_m'])-1:len(cove['sea_edge_m'])-1+len(beach['sea_edge_m'])],
          f'{len(segs)} segments, longest {max(m.length(a, b) for a, b in segs):.2f}m')
    check('two beach turnaround lots inside sand', all(all(contained(p, beach['polygon_m']) for p in s['polygon_m'])
          for s in d['functional_sites'] if s['type'] == 'turnaround'))
    check('each beach turnaround served by its own road', all(m.inside(pts[pid]['position_m'], sites[sid]['polygon_m'])
          for pid, sid in [('BEACH_ENTRY', 'BEACH_TURNAROUND'), ('BEACH_VALLEY_ENTRY', 'BEACH_VALLEY_TURNAROUND')]))
    for ex in d['exits']:
        blocked = m.shortest(d, pts['B01']['road_node_id'], ex['dead_end_node_id'], blocked=pts[ex['post_id']]['road_node_id'])[0]
        check('mandatory return through '+ex['post_id'], math.isinf(blocked))
    barrierhits = [(q['id'], r['id']) for q in d['vegetation_parcels'] if q['kind'] == 'interdistrict_barrier'
                   for r in d['roads']+(d['paths'] if q['blocks_foot'] else []) if any(v7.gap(q['polygon_m'], a, b) < r['width_m']/2-.015 for a, b in zip(r['polyline_m'], r['polyline_m'][1:]))]
    check('fences and rocks leave roads and foot paths clear (the walkable dune only roads)', not barrierhits, barrierhits)
    closers = [q['axis_m'] for q in d['vegetation_parcels'] if q['kind'] == 'interdistrict_barrier' and q['blocks_van']]
    bva = roads['BEACH_VALLEY_ACCESS']['polyline_m']
    led = beach['land_edge_m']
    i0 = min(range(len(led)), key=lambda i: m.length(led[i], DUNE_FROM))
    i1 = min(range(len(led)), key=lambda i: m.length(led[i], DUNE_TO))
    open_edge = [p for p in v12.sample_line(led[i0:i1+1], 1.0) if min(nearest(p, ax)[0] for ax in closers) > 1.6 and nearest(p, bva)[0] > 5]
    check('beach land edge closed to the van from the cove rocks to the elite fence, except BEACH_VALLEY_ACCESS',
          not open_edge, [[round(z) for z in p] for p in open_edge[:6]])
    check('v12 top-level schema and container types retained', all(k in d and type(d[k]) == type(value) for k, value in original.items()))
    fields = {'roads': {'id', 'class', 'polyline_m', 'width_m'}, 'building_masses': {'id', 'center_m', 'polygon_m', 'floors', 'kind', 'district_id', 'width_m', 'depth_m'},
              'functional_buildings': {'id', 'center_m', 'width_m', 'depth_m', 'footprint_m', 'storeys', 'label_ru', 'type', 'district_id'},
              'districts': {'id', 'polygon_m', 'parent_id'}, 'plots': {'id', 'kind', 'polygon_m'}, 'beaches': {'id', 'polygon_m', 'access_road_ids'},
              'microdistricts': {'id', 'yard_polygon_m', 'building_ids'}, 'paths': {'id', 'class', 'polyline_m', 'width_m'}}
    check('converter nested schema preserved', all(req <= set(q) for key, req in fields.items() for q in d[key]))
    for key in ('roads', 'points', 'paths', 'building_masses', 'functional_buildings', 'functional_sites', 'plots',
                'vegetation_parcels', 'water', 'crop_fields', 'microdistricts'):
        check(key+' unique IDs', len({q['id'] for q in d[key]}) == len(d[key]))
    check('road and path IDs unique together', len({q['id'] for q in d['roads']+d['paths']}) == len(d['roads'])+len(d['paths']))
    check('B01–B06 and P01–P16 canonical IDs retained', {p['canonical_id'] for p in original['points']} <= {p['canonical_id'] for p in d['points']})
    current = hashes()
    check('v12 and earlier file hashes unchanged during the run', current == d['provenance']['previous_files_sha256'])
    check('older revisions match the hashes recorded by v12', all(current.get(n) == h for n, h in original['provenance']['previous_files_sha256'].items()))
    # ------------------------------------------------------------ v13 checks
    res = [b for b in phys if b['district_id'] == 'residential']
    panels = [b for b in bs.values() if b['kind'] == 'panel']
    ods = {q['id']: q for q in original['districts']}
    lane_x_limit = 832
    check('alley district: no slabs, 8–12 panel houses, 5–9 floors, footprint <=52 x 14m',
          not any(b['kind'] == 'slab' for b in bs.values()) and 8 <= len(panels) <= 12 and all(b['district_id'] == 'residential' and
          5 <= b['floors'] <= 9 and max(b['width_m'], b['depth_m']) <= 52 and min(b['width_m'], b['depth_m']) <= 14 for b in panels), len(panels))
    arch_ok = []
    for owner, arch in arches:
        a, b = arch['axis_m']
        poly = bs[owner]['polygon_m']
        crosses = not contained(a, poly) and not contained(b, poly) and m.inside([(a[0]+b[0])/2, (a[1]+b[1])/2], poly)
        users = [w['id'] for w in ways.values() if w['width_m'] <= arch['width_m'] and
                 any(m.projection([(a[0]+b[0])/2, (a[1]+b[1])/2], p, q)[0] < .5 for p, q in zip(w['polyline_m'], w['polyline_m'][1:])) and
                 nearest(a, w['polyline_m'])[0] < 1 and nearest(b, w['polyline_m'])[0] < 1]
        van = [u for u in users if u in roads]
        arch_ok.append(crosses and users and (van if arch['van_passable'] else True))
    van_arches = [o for o, a in arches if a['van_passable']]
    check('>=10 podvorotnya arches, >=2 for the van; each crosses its building and opens onto a road or path at both ends',
          len(arches) >= 10 and len(van_arches) >= 2 and all(arch_ok), f'{len(arches)} arches / van {van_arches} / {arch_ok}')
    types = Counter(f['type'] for f in fs.values() if f['district_id'] == 'residential')
    check('business mix: ATM shop with P11-2 at its door, supermarket, 2 bars, kiosk, 24h shop, pawn, shawarma, loans, betting, beer; den, hospital, P11-3, B03 kept',
          types['atm_shop'] == 1 and pts['P11-2']['position_m'] == fs['F13_ATMSHOP']['entrance_m'] and types['supermarket'] >= 1 and
          types['bar'] >= 2 and types['kiosk'] >= 1 and types['shop_24h'] == 1 and {'F06_DEN', 'F06_HOSPITAL', 'F06_ATM', 'F06_GBASE'} <= set(fs) and
          all(types[t] >= 1 for t in ('pawn_shop', 'fast_food', 'payday_loans', 'betting_shop', 'beer_kiosk')) and
          fs['F06_DEN']['poi_id'] == 'P07', dict(types))
    avenue = roads['ARC_AVENUE']['polyline_m']
    breaks = sorted({round(r['polyline_m'][0][0], 2) for r in d['roads']+d['paths'] if r['id'] != 'ARC_AVENUE' and
                     abs(r['polyline_m'][0][1]-723.5) < .01 and 470 < r['polyline_m'][0][0] < 770})
    alternation = []
    for side in (1, -1):
        row = sorted([b for b in res if (centroid(b['poly'])[1]-723.5)*side > 0 and
                      min(v7.gap(b['poly'], a, c) for a, c in zip(avenue, avenue[1:])) <= 30], key=lambda b: centroid(b['poly'])[0])
        for a, b in zip(row, row[1:]):
            if a['id'] in bs and b['id'] in bs:
                right_a, left_b = max(p[0] for p in a['poly']), min(p[0] for p in b['poly'])
                if not any(right_a <= x <= left_b for x in breaks):
                    alternation.append((a['id'], b['id']))
    check('avenue frontages: no two panel houses side by side without a business, alley or arch between', not alternation, alternation)
    gaps = [(round(poly_gap(a['poly'], b['poly']), 2), a['id'], b['id']) for i, a in enumerate(res) for b in res[i+1:]]
    check('alley district: every gap between buildings >=3m (no slivers)', min(gaps)[0] >= 3, min(gaps))
    near = {}
    for g, a, b in gaps:
        near[a], near[b] = min(near.get(a, 1e9), g), min(near.get(b, 1e9), g)
    nearest_gaps = dict(sorted(near.items()))
    median_gap = round(sorted(near.values())[len(near)//2], 2)
    check('alley district grain: median gap to the nearest neighbouring building <=14m', median_gap <= 14, f'{median_gap}m')

    def lane_x(rid, y):
        line = ways[rid]['polyline_m']
        return min(((abs(p[1]-y), p[0]) for p in line))[1]
    north = [b for b in res if centroid(b['poly'])[1] > 727 and centroid(b['poly'])[1] < lane_x_limit]
    blocks = {}
    for b in north:
        x, y = centroid(b['poly'])
        col = 'A' if x < lane_x('ALLEY_W', y) else 'B' if x < lane_x('COURT_B', y) else 'C' if x < lane_x('ALLEY_C', y) else               'D' if x < lane_x('LANE_C', y) else 'E' if x < lane_x('R_REAR', y) else 'X'
        kind = 'panel' if b['id'] in bs else 'shop' if fs[b['id']]['type'] in TRASHY else 'other'
        blocks.setdefault(col, Counter())[kind] += 1
    mixed = {c: dict(blocks.get(c, {})) for c in 'ABCDE'}
    check('blocks A–E north of the avenue each mix >=1 panel house with >=1 trashy business', all(blocks.get(c, {}).get('panel') and
          blocks.get(c, {}).get('shop') for c in 'ABCDE'), mixed)
    deep = sorted(f['id'] for f in fs.values() if f['district_id'] == 'residential' and f['type'] in TRASHY and
                  min(v7.gap(f['footprint_m'], a, c) for a, c in zip(avenue, avenue[1:])) > 20)
    check('>=4 trashy businesses stand inside the blocks (>20m from the avenue), not only on the frontage', len(deep) >= 4, deep)
    lanes = [p for p in d['paths'] if p['class'] == 'foot_lane']
    bad_blocks = []
    for pid in ('BAD_BLOCK', 'BAD_BLOCK_2', 'BAD_BLOCK_3'):
        p = pts[pid]['position_m']
        near_arch = min(m.projection(p, *a['axis_m'])[0] for _, a in arches)
        near_lane = min(nearest(p, q['polyline_m'])[0] for q in lanes)
        if min(near_arch, near_lane) > 6 or nearest(p, avenue)[0] < 6:
            bad_blocks.append((pid, round(near_arch, 1), round(near_lane, 1)))
    check('podvorotnya points sit at an arch or foot lane (<=6m), off the avenue', not bad_blocks, bad_blocks)
    dead = [p['id'] for p in lanes if len(p.get('joins_way_ids', [])) < 2]
    check('foot lanes join ways at both ends (no dead-end lanes)', not dead, dead)
    stubs = []
    for f in fs.values():
        if f['id'] in BUSINESSES:
            r = roads.get('ACCESS_'+(f.get('poi_id') or f['id']))
            if not r or m.length(r['polyline_m'][-1], f['entrance_m']) > .01 or                     nearest(r['polyline_m'][0], roads[f['access_road_id']]['polyline_m'])[0] > .01:
                stubs.append(f['id'])
    check('every new business has a driveway stub from its alley or street to its door', not stubs, stubs)
    unreach = [p['id'] for p in d['points'] if math.isinf(m.shortest(d, pts['B01']['road_node_id'], p['road_node_id'])[0])]
    check('every point reachable by the van from B01', not unreach, unreach)
    dry_court = []
    pe = ped['road_graph']['edges']
    for cid, mdist in ((q['id'], q) for q in d['microdistricts']):
        poly = mdist['yard_polygon_m']
        cc = centroid(poly)
        ok = False
        for e in pe:
            a, b = e['polyline_m']
            if v7.gap(poly, a, b) > 12:
                continue
            q = m.projection(cc, a, b)[1]
            if all(v7.gap(bpoly, cc, q) > 0 for bpoly in polys.values()):
                ok = True
                break
        if not ok:
            dry_court.append(cid)
    check('every courtyard reachable on foot', not dry_court, dry_court)
    crops = d['crop_fields']
    plots = [p['polygon_m'] for p in d['plots']]+[q['polygon_m'] for q in d['vegetation_parcels'] if q['kind'] == 'orchard']
    plots += [yard['polygon_m'], sites['CHURCH_SQUARE13']['polygon_m']]
    bad_crop = [f['id'] for f in crops if not 800 <= m.area(f['polygon_m']) <= 2000 or any(strict_overlap(f['polygon_m'], b['poly']) for b in phys) or
                any(strict_overlap(f['polygon_m'], p) for p in plots) or any(v7.gap(f['polygon_m'], a, b) < w['width_m']/2
                for w in d['roads']+d['paths'] for a, b in zip(w['polyline_m'], w['polyline_m'][1:])) or
                any(not contained(p, ds['village']['polygon_m']) for p in f['polygon_m'])]
    check('>=5 striped crop fields 800–2000 m² (as in the reference), clear of buildings, roads, yards and orchards',
          len(crops) >= 5 and not bad_crop, bad_crop)
    forest = ds['forest']['polygon_m']
    ff = d['forest_features']
    gap_cove = min(nearest(p, cove['land_edge_m'])[0] for p in forest)
    check('forest reaches the cove (<=15m, no overlap)', gap_cove <= 15 and not strict_overlap(forest, cove['polygon_m']), f'{gap_cove:.1f}m')
    ponds = [waters[w]['polygon_m'] for w in ff['swamp']['pond_ids']]
    check('swamp: >=4 ponds inside it, swamp inside the forest (west half)', len(ponds) >= 4 and
          all(contained(p, ff['swamp']['polygon_m']) for pd in ponds for p in pd) and all(contained(p, forest) for p in ff['swamp']['polygon_m']) and
          centroid(ff['swamp']['polygon_m'])[0] < centroid(forest)[0])
    flake = waters['FOREST_LAKE']['polygon_m']
    check('forest lake 900–1600 m² in the east half of the forest', 900 <= m.area(flake) <= 1600 and all(contained(p, forest) for p in flake) and
          centroid(flake)[0] > centroid(forest)[0], f'{m.area(flake):.0f} m²')
    hill = next(h for h in d['hills'] if h['id'] == 'HILL_FOREST')
    check('hill (south) and drinkers\' clearing inside the forest', all(contained(p, forest) for p in hill['polygon_m']) and
          all(contained(p, forest) for p in sites['HANGOUT13']['polygon_m']) and hill['center_m'][1] < centroid(forest)[1] and
          m.length(paths['PATH_HILL_SPIRAL']['polyline_m'][-1], hill['center_m']) < 4)
    tunnel = sites['RAIL_TUNNEL_W']
    edge_gap = min(m.projection(rail[0], a, b)[0] for a, b in v7.edges(bp))
    check('railway west end at the boundary in a tunnel that blocks van and walkers', edge_gap < 8 and tunnel['position_m'] == rail[0] and
          tunnel['blocks_van'] and tunnel['blocks_foot'] and d['railway']['from_point'] == 'RAIL_TUNNEL_W', f'{edge_gap:.2f}m')
    rx = [r['id'] for r in d['roads'] if any(m.crossing(a, b, c2, e) for a, b in zip(rail, rail[1:]) for c2, e in zip(r['polyline_m'], r['polyline_m'][1:]))]
    check('railway crosses no road', not rx and d['railway']['road_crossings'] == [], rx)
    wd = min(m.projection(fs['F06_WAGON']['center_m'], a, b)[0] for a, b in zip(rail, rail[1:]))
    check('wagon sits on the rails (<=0.6m)', wd <= .6, f'{wd:.2f}m')
    cxy = centroid(ds['industrial']['polygon_m'])
    check('industrial zone fills the NE corner (centroid x>850, y>780)', cxy[0] > 850 and cxy[1] > 780, cxy)
    fences = [q for q in d['vegetation_parcels'] if q.get('material') == 'barbed_fence']
    fx = [(q['id'], w['id']) for q in fences for w in d['roads']+d['paths']
          if any(m.crossing(a, b, c2, e) for a, b in zip(q['axis_m'], q['axis_m'][1:]) for c2, e in zip(w['polyline_m'], w['polyline_m'][1:]))]
    check('industrial fence crosses no road or path', not fx, fx)
    gate = fences[0]['gate']
    ia = roads['I_ACCESS']['polyline_m']
    check('industrial gate 6–9m spans I_ACCESS', 6 <= gate['width_m'] <= 9 and any(m.crossing(*gate['posts_m'], a, b) for a, b in zip(ia, ia[1:])), gate['width_m'])
    fb = [(q['id'], b['id']) for q in fences for b in phys if any(v7.gap(b['poly'], a, c2) < 2 for a, c2 in zip(q['axis_m'], q['axis_m'][1:]))]
    check('industrial fence >=2m from buildings', not fb, fb)
    north = next(q for q in fences if q['id'] == 'INDUSTRIAL_FENCE_W')['axis_m'][0]
    ngap = min(m.projection(north, a, b)[0] for a, b in v7.edges(bp))
    check('industrial fence ties into the north map edge (<=5m)', ngap <= 5, f'{ngap:.2f}m')
    fz = sorted({(q['id'], name) for q in fences for name, pl in (('beach', beach['polygon_m']), ('elite', ds['elite']['polygon_m']),
                 ('alleys', ds['residential']['polygon_m'])) for p in q['axis_m'] if m.inside(p, pl)})
    fo = [p for q in fences for p in q['axis_m'] if not contained(p, bp) and nearest(p, coast)[0] > .6]
    check('industrial fence on land, outside beach, elite and alley polygons', not fz and not fo, fz+fo[:3])
    outfall = d['outfalls'][0]
    end = outfall['polyline_m'][-1]
    plume = outfall['plume']['polygon_m']
    check('outfall ends in the sea >=30m beyond the coast; plume entirely in the sea', m.inside(end, sea['polygon_m']) and
          not m.inside(end, bp) and nearest(end, coast)[0] >= 30 and all(m.inside(p, sea['polygon_m']) for p in plume), f'{nearest(end, coast)[0]:.1f}m')
    lots = [s for s in d['functional_sites'] if s['id'].startswith('PARK13_LOT')]
    usable = sum(s['capacity_vans'] for s in lots)
    check('car park >=40 usable van bays', usable >= 40 and len([b for s in lots for b in s['bays']]) == 48, usable)
    park = ds['beach_parking']['polygon_m']
    entering = sorted({r['id'] for r in d['roads'] if any(m.inside(p, park) for p in r['polyline_m'])})
    cut = pts['BEACH_PARK_ENTRY']['road_node_id'] not in v11.reachable(d['road_graph'], pts['B01']['road_node_id'], removed_roads=['PARK_ROAD'])
    check('car park: only vehicle access is PARK_ROAD from I_CONNECT', cut and nearest(roads['PARK_ROAD']['polyline_m'][0], roads['I_CONNECT']['polyline_m'])[0] < .01
          and set(entering) <= {'I_CONNECT', 'PARK_ROAD', 'PARK_AISLE_W', 'PARK_AISLE_E', 'ACCESS_F13_PARK_KIOSK', 'ACCESS_F13_PARK_WC'}, entering)
    check('car park: >=2 walk paths end on WALK_BEACH', len(park_paths) >= 2, park_paths)
    bol = sites['PARK13_BOLLARDS']['polyline_m']
    bol_cross = [p for p in park_paths if any(m.crossing(a, b, c2, e) for a, b in zip(bol, bol[1:])
                 for c2, e in zip(paths[p]['polyline_m'], paths[p]['polyline_m'][1:]))]
    bol_roads = [r['id'] for r in d['roads'] if any(m.crossing(a, b, c2, e) for a, b in zip(bol, bol[1:])
                 for c2, e in zip(r['polyline_m'], r['polyline_m'][1:]))]
    bol_gap = min(v7.gap(b['poly'], p, q) for b in phys for p, q in zip(bol, bol[1:]))
    check('car park edge to the sand: bollard line (no fence) crossed by every beach path, no road, >=1m from buildings',
          sites['PARK13_BOLLARDS']['blocks_van'] and not sites['PARK13_BOLLARDS']['blocks_foot'] and len(bol_cross) == len(park_paths)
          and not bol_roads and bol_gap >= 1, f'{bol_cross} / {bol_roads} / {bol_gap:.1f}m')
    # Guard: everything outside the four rebuilt areas stays byte-identical to v12.
    derived = ('area_m2', 'building_count', 'share_percent', 'road_node_id')

    def strip(q):
        return {k: v for k, v in q.items() if k not in derived}
    diffs = []
    ods = {q['id']: q for q in original['districts']}
    diffs += ['district '+k for k in GUARD_DISTRICTS if strip(ds[k]) != strip(ods[k])]
    for key, exempt in (('functional_buildings', {'F06_CHURCH'}), ('building_masses', set()), ('plots', set()),
                        ('functional_sites', {'CHURCH12_YARD'}), ('points', set())):
        new = {q['id']: q for q in d[key]}
        diffs += [key+' '+q['id'] for q in original[key] if q.get('district_id') in GUARD_DISTRICTS+('beach',) and
                  q['id'] not in exempt and (q['id'] not in new or strip(new[q['id']]) != strip(q))]
    for r in original['roads']:
        if set(r['district_ids']) & set(GUARD_DISTRICTS+('beach',)) and r['id'] not in {'ACCESS_F06_CHURCH', 'I_CONNECT'}:
            if r != roads.get(r['id']):
                diffs.append('road '+r['id'])
    if roads['I_CONNECT']['polyline_m'] != next(r for r in original['roads'] if r['id'] == 'I_CONNECT')['polyline_m']:
        diffs.append('road I_CONNECT geometry')
    if d['field_parcels_m'] != original['field_parcels_m'] or d['beaches'][0] != original['beaches'][0]:
        diffs.append('valley parcels or main beach')
    if paths['WALK_BEACH'] != original['paths'][0] or d['hills'][0] != original['hills'][0]:
        diffs.append('beach walk or elite hill')
    oveg = {q['id']: q for q in original['vegetation_parcels']}
    diffs += ['barrier '+q['id'] for q in d['vegetation_parcels'] if q['id'] in oveg and not q['id'].startswith('CANAL_RAILING_S') and q != oveg[q['id']]]
    now = {q['id'] for q in d['vegetation_parcels']}
    diffs += ['barrier removed '+i for i in oveg if i not in now and i not in REMOVED_BARRIERS]
    diffs += ['removal not recorded '+i for i in REMOVED_BARRIERS if i in now or i not in {q['id'] for q in d['removed_barriers']}]
    check('guard: transition (minus church), old town, elite, valley and main beach identical to v12 except the 12 recorded border fences',
          not diffs and len(d['removed_barriers']) == 12, diffs)
    before, after = positions(original), positions(d)
    recorded = {(q['kind'], q['id']) for q in d['moves']}
    unrecorded = [k for k in after if k in before and m.length(before[k], after[k]) > .5 and k not in recorded]
    check('every id moved by >0.5m is recorded in moves with its id kept', not unrecorded and len(d['moves']) >= 20, unrecorded)
    materials = Counter(q['material'] for q in d['vegetation_parcels'] if q['kind'] == 'interdistrict_barrier')
    barbed = {q['id'] for q in d['vegetation_parcels'] if q.get('material') == 'barbed_fence'}
    check('only elite fence, industrial barbed fence, rock scarps, beach dune and canal railings remain', set(materials) <=
          {'elite_fence', 'barbed_fence', 'rock_scarp', 'canal_railing', 'dune_ridge'} and barbed == {'INDUSTRIAL_FENCE_W', 'INDUSTRIAL_FENCE_S'}, dict(materials))
    nw = next(e for e in d['exits'] if e['id'] == 'NW')
    nwbad = []
    for poly in nw['barrier_polygons_m']:
        if any(not contained(p, bp) for p in poly):
            nwbad.append('outside land')
        nwbad += [b['id'] for b in phys if strict_overlap(b['poly'], poly)]
        nwbad += ['yard/field' for p in plots+[f['polygon_m'] for f in crops] if strict_overlap(poly, p)]
        nwbad += [r['id'] for r in d['roads'] if any(v7.gap(poly, a, b) < r['width_m']/2 for a, b in zip(r['polyline_m'], r['polyline_m'][1:]))]
    check('NW exit barriers inside the land, clear of churchyard, fields, buildings and roads', not nwbad, nwbad)
    yard_gap = min(v7.gap(yard['polygon_m'], pts['P16']['position_m'], pts['P16']['position_m']), *(v7.gap(yard['polygon_m'], a, b)
                   for poly in nw['barrier_polygons_m'] for a, b in v7.edges(poly)))
    check('P16 checkpoint and its barriers >=60m / >=40m from the churchyard; church lane ends at the forecourt',
          v7.gap(yard['polygon_m'], pts['P16']['position_m'], pts['P16']['position_m']) >= 60 and yard_gap >= 40 and
          m.length(roads['CHURCH_LANE']['polyline_m'][-1], centroid(sites['CHURCH_SQUARE13']['polygon_m'])) < 12, f'{yard_gap:.1f}m')
    hang = sites['HANGOUT13']['dressing_hints']
    crate_door = m.length(hang['crate_by_wagon_door_m'], pts['B01']['position_m'])
    crate_wagon = v7.gap(fs['F06_WAGON']['footprint_m'], hang['crate_by_wagon_door_m'], hang['crate_by_wagon_door_m'])
    check('hangout props clear of the B01 door and the van stop (crate >=4m from the door, >=1.5m off the wagon)',
          crate_door >= 4 and crate_wagon >= 1.5 and all(m.inside(p, sites['HANGOUT13']['polygon_m']) for p in
          [hang['campfire_ring']['position_m'], hang['tent']['position_m']]+hang['bottles_and_cans_m']), f'{crate_door:.1f}m / {crate_wagon:.1f}m')
    rocks = d['forest_features']['rocks']
    rock_hits = [(q['id'], w['id']) for q in rocks for w in d['roads']+d['paths']
                 if any(v7.gap(q['polygon_m'], a, b) < w['width_m']/2 for a, b in zip(w['polyline_m'], w['polyline_m'][1:]))]
    rock_hits += [(q['id'], 'rail') for q in rocks if any(v7.gap(q['polygon_m'], a, b) < 2.4 for a, b in zip(rail, rail[1:]))]
    rock_hits += [(q['id'], 'outside') for q in rocks if not all(contained(p, bp) or m.inside(p, cove['polygon_m']) or
                  m.inside(p, sea['polygon_m']) for p in q['polygon_m'])]
    check('>=8 rock clusters along the forest cliff, tunnel and cove, clear of roads, trails and rails', len(rocks) >= 8 and not rock_hits, rock_hits)
    lot_bad = []
    for lot in lots:
        aisle = roads[lot['aisle_road_id']]
        turn = sites[aisle['turning_head_site_id']]
        lot_bad += [b['id'] for b in lot['bays'] if any(v7.gap(b['polygon_m'], p, q) < aisle['width_m']/2-.01
                    for p, q in zip(aisle['polyline_m'], aisle['polyline_m'][1:]))]
        if not m.inside(aisle['polyline_m'][-1], turn['polygon_m']) or turn['diameter_m'] < 12:
            lot_bad.append(turn['id'])
        for b in lot['bays']:
            if b['usable']:
                continue
            path = next(p for p in d['paths'] if p['id'] in ('PATH_BEACH_W', 'PATH_BEACH_E') and nearest(p['polyline_m'][0], aisle['polyline_m'])[0] < .01)
            cx = centroid(b['polygon_m'])[0]
            lot_bad += [b['id']] if abs(path['polyline_m'][0][0]-cx) > .01 else []
            lot_bad += [(path['id'], q['id']) for q in lot['bays'] if q['usable'] and any(v7.gap(q['polygon_m'], p1, p2) < path['width_m']/2-.01
                        for p1, p2 in zip(path['polyline_m'], path['polyline_m'][1:]))]
    check('car park: bays clear of the straight aisles, a 13m turning head at each aisle end, beach paths centred on their walkway bays',
          not lot_bad, lot_bad)
    park_area = m.area(ds['beach_parking']['polygon_m'])
    check('car park paved area 4,500–6,500 m² hugging the bays; the rest is green', 4500 <= park_area <= 6500, f'{park_area:.0f} m²')
    joins = []
    for graph, table in ((d['road_graph'], ROADS), (ped['road_graph'], PATHS)):
        touch = {}
        for e in graph['edges']:
            for n in (e['from_node'], e['to_node']):
                touch.setdefault(n, set()).add(e['road_id'])
        for rid, controls, cls, dids, start, end in table:
            line = ways[rid]['polyline_m']
            for parent, p in ((start, line[0]), (end, line[-1])):
                if parent and parent not in touch.get(node_at(graph, p), set()):
                    joins.append((rid, parent))
    check('new alleys, lanes, trails and paths join their parent ways at shared nodes', not joins, joins)
    open_hits = []
    for name, poly in [(q['id'], q['yard_polygon_m']) for q in d['microdistricts']]+[('GARAGE13', sites['GARAGE13']['polygon_m'])]:
        open_hits += [(name, b['id']) for b in phys if strict_overlap(b['poly'], poly)]
        open_hits += [(name, r['id']) for r in d['roads'] if not r.get('access_only') and
                      any(v7.gap(poly, a, b) < r['width_m']/2 for a, b in zip(r['polyline_m'], r['polyline_m'][1:]))]
    check('courtyards and garage yard clear of buildings and vehicle roads', not open_hits, open_hits)
    # ------------------------------------------------------------ metrics and statistics
    d['metrics'] = dict(area_m2=round(m.area(bp), 3), bounds_m=bounds, extent_m=extent, routes=routes,
        building_count=len(phys), building_counts_by_district=dict(counts),
        common_landscape_area_m2=round(m.area(bp)-sum(q['area_m2'] for q in d['districts'])-m.area(beach['polygon_m'])-m.area(cove['polygon_m']), 3),
        timing_assumption='constant-speed route arithmetic; not gameplay or subjective visual acceptance')
    d['functional_statistics'] = dict(building_count=len(fs), district_counts=dict(Counter(f['district_id'] for f in fs.values())),
        type_counts=dict(Counter(f['type'] for f in fs.values())), promoted_existing_count=sum('source_building_id' in f for f in fs.values()),
        new_footprint_count=sum('source_building_id' not in f for f in fs.values()))
    oslabs = [b for b in original['building_masses'] if b['kind'] == 'slab']
    corridor = {name: round(poly_gap(polys[a], polys[b]), 2) for name, a, b in CORRIDORS}
    d['alley_statistics'] = dict(panel_house_count=len(panels), floors_range=[min(b['floors'] for b in panels), max(b['floors'] for b in panels)],
        panel_footprint_m2=round(sum(m.area(b['polygon_m']) for b in panels)), panel_floor_area_m2=round(sum(m.area(b['polygon_m'])*b['floors'] for b in panels)),
        v12_slab_footprint_m2=round(sum(m.area(b['polygon_m']) for b in oslabs)), v12_slab_floor_area_m2=round(sum(m.area(b['polygon_m'])*b['floors'] for b in oslabs)),
        gateway_arch_count=len(arches), van_arch_count=sum(a['van_passable'] for _, a in arches),
        business_counts=dict(types), physical_building_count=counts['residential'],
        v12_physical_building_count=original['metrics']['building_counts_by_district']['residential'],
        min_gap_between_buildings_m=min(gaps)[0], alley_corridor_facade_to_facade_m=corridor,
        alley_road_ids=[r for r, *_ in ROADS if r.startswith(('ALLEY', 'COURT'))], foot_lane_ids=[p for p, *_ in PATHS if p.startswith('LANE')],
        courtyard_ids=[q['id'] for q in d['microdistricts']], nearest_facade_gap_m=nearest_gaps,
        median_nearest_facade_gap_m=median_gap, interleaved_business_ids=deep,
        district_area_m2=round(m.area(ds['residential']['polygon_m'])), v12_district_area_m2=round(m.area(ods['residential']['polygon_m'])),
        built_coverage_percent=round(sum(m.area(b['poly']) for b in res)/m.area(ds['residential']['polygon_m'])*100, 1))
    d['residential_statistics'] = dict(complex_count=0, slab_count=0, panel_house_count=len(panels), alley_block_count=7,
                                       physical_building_count=counts['residential'], policy='v13 alley district replaces the three U courts')
    d['hamlet_statistics'] = dict(farmstead_count=len(d['farmsteads']), building_count=counts['village'], start_cluster_count=1,
                                  crop_field_count=len(crops), church_in_village=True)
    d['passage_statistics'] = dict(count=len(d['paths']), total_length_m=round(sum(p['length_m'] for p in d['paths']), 3),
        by_class=dict(Counter(p['class'] for p in d['paths'])), policy='walk only: beach, car-park paths, foot lanes, forest trails')
    bdoor, chim = pts['B01']['position_m'], fs['F06_CHIMNEY']['center_m']
    sl = m.length(bdoor, chim)
    blockers = [(b['id'], round(m.length(bdoor, centroid(b['poly'])))) for b in phys if b['id'] not in ('F06_WAGON', 'F06_CHIMNEY') and
                v7.gap(b['poly'], bdoor, chim) < 4]
    floors = {b['id']: b['floors'] for b in bs.values()}
    floors.update({f['id']: f['storeys'] for f in fs.values()})
    d['sightline'].update(length_m=round(sl, 1), corridor_obstacles=[dict(id=i, storeys=floors.get(i), distance_m=dist) for i, dist in blockers],
        chimney_angle_deg=round(math.degrees(math.atan(85/sl)), 1),
        obstacle_max_angle_deg=round(max([math.degrees(math.atan(floors.get(i, 1)*3.5/dist)) for i, dist in blockers] or [0]), 1))
    d['validation'] = dict(passed=all(c['passed'] for c in checks), checks=checks)
    if strict and not d['validation']['passed']:
        raise ValueError(json.dumps([c for c in checks if not c['passed']], ensure_ascii=False, indent=2))
    return [c for c in checks if not c['passed']]


# ------------------------------------------------------------------ rendering
POINT_NAMES = {'B01': 'Вагон', 'B02': 'Хижина', 'B03': 'Гараж', 'B04': 'Старый дом', 'B05': 'Промкомплекс', 'B06': 'Вилла у озера',
    'P01': 'Объявление', 'P02': 'Дом деда', 'P03': 'Аптека', 'P04': 'Приёмка', 'P05': 'Автомастерская', 'P06': 'Бар', 'P07': 'Притон',
    'P08': 'Больница', 'P10': 'Полиция', 'P11': 'Банк / ATM', 'P11-2': 'ATM в «Продуктах»', 'P11-3': 'ATM больницы',
    'P12': 'Эвакуатор', 'P14': 'Депо', 'P15': 'Особняк / VIP', 'P15-2': 'Особняк 2', 'P13': 'Озеро: спуск',
    'P13-2': 'Река: спуск', 'P13-3': 'Канал: спуск', 'P13-4': 'Мусорки', 'P13-5': 'Мусорки', 'P16': 'Пост СЗ', 'P16-2': 'Пост СВ',
    'P09': 'За супермаркетом', 'P09-2': 'Встреча: подворотни', 'P09-3': 'Встреча: ворота B05', 'P09-4': 'Встреча: переход',
    'WATER_TOWER': 'Водонапорная башня', 'CHIMNEY': 'Труба / 85 м', 'BAD_CENTER': 'Центр района',
    'CLOCK_SQUARE': 'Малая площадь', 'ELITE_GATE': 'Элитка: въезд', 'BAD_BLOCK': 'Подворотня 1', 'BAD_BLOCK_2': 'Подворотня 2',
    'BAD_BLOCK_3': 'Подворотня 3', 'BEACH_ENTRY': 'Пляж: въезд из элитки', 'BEACH_VALLEY_ENTRY': 'Пляж: въезд из долины',
    'BEACH_PARK_ENTRY': 'Пляжная парковка'}
SHORT = {'F06_CAFE2': 'Кафе у проспекта · покупка', 'F06_SUPER': 'Супермаркет', 'F06_CHURCH': 'Церковь',
    'F06_GAS': 'АЗС', 'F06_RUINS': 'Руины', 'F06_WARE1': 'Склад 1', 'F06_MAINT': 'Ремонтный сарай',
    'F12_CASINO': 'Казино · 3 этажа', 'F12_NIGHTCLUB': 'Ночной клуб', 'F12_BOWLING': 'Боулинг / аркада',
    'F06_GUARD': 'Охрана', 'F06_24': 'Магазин 24 ч', 'F06_VSHOP': 'Лавка', 'F06_BUS': 'Остановка',
    'F06_BARN': 'Сарай деда', 'F08_MANSION_1': 'Особняк 1', 'F06_MANSION_3': 'Особняк 3',
    'F13_DISCOUNTER': 'Дискаунтер', 'F13_ATMSHOP': 'Продукты · банкомат', 'F13_BAR2': 'Рюмочная',
    'F13_BEER': 'Пиво', 'F13_LOMBARD': 'Ломбард', 'F13_SHAWARMA': 'Шаурма 24', 'F13_ZAIMY': 'Займы', 'F13_BETS': 'Ставки',
    'F13_TANK': 'Резервуар', 'F13_PARK_KIOSK': 'Киоск', 'F13_PARK_WC': 'Туалет / душ', 'F06_K1': 'Ларёк', 'F06_K3': 'Ларёк'}
TRASHY = {'supermarket', 'atm_shop', 'bar', 'kiosk', 'shop_24h', 'beer_kiosk', 'pawn_shop', 'fast_food', 'payday_loans', 'betting_shop'}
BG = '#f7f4eb'
BARBED = '#4b5054'
DUNE = '#cdb579'


def jitter(i, j, salt):
    return ((i*73856093) ^ (j*19349663) ^ (salt*83492791)) % 1000/1000


class SegIndex:
    """Spatial hash of road/path/rail segments for fast clearance tests while scattering trees."""
    def __init__(self, items, cell=20):
        self.cell, self.grid = cell, {}
        for line, half in items:
            for a, b in zip(line, line[1:]):
                for gx in range(int(min(a[0], b[0])//cell)-1, int(max(a[0], b[0])//cell)+2):
                    for gy in range(int(min(a[1], b[1])//cell)-1, int(max(a[1], b[1])//cell)+2):
                        self.grid.setdefault((gx, gy), []).append((a, b, half))

    def near(self, p, extra):
        return any(m.projection(p, a, b)[0] < half+extra for a, b, half in self.grid.get((int(p[0]//self.cell), int(p[1]//self.cell)), []))


def clip_band(poly, axis, lo, hi):
    def half(pts, keep, v):
        out = []
        for i, cur in enumerate(pts):
            prev = pts[i-1]
            if keep(cur) != keep(prev):
                t = (v-prev[axis])/(cur[axis]-prev[axis])
                out.append([prev[0]+(cur[0]-prev[0])*t, prev[1]+(cur[1]-prev[1])*t])
            if keep(cur):
                out.append(cur)
        return out
    pts = half(poly, lambda p: p[axis] >= lo, lo)
    return half(pts, lambda p: p[axis] <= hi, hi) if pts else []


def tree_layers(d):
    """Deterministic tree positions in metres: forest conifers, hamlet round trees, common green on the old industrial site."""
    ds = {q['id']: q for q in d['districts']}
    sites = {s['id']: s for s in d['functional_sites']}
    waters = {w['id']: w for w in d['water']}
    phys = v7.physical(d)
    ways = SegIndex([(r['polyline_m'], r['width_m']/2) for r in d['roads']] +
                    [(p['polyline_m'], p['width_m']/2) for p in d['paths']] + [(d['railway']['polyline_m'], 2.4)] +
                    [(q['axis_m'], .5) for q in d['vegetation_parcels'] if q['kind'] == 'interdistrict_barrier'] +
                    [(w['centerline_m'], w['width_m']/2) for w in d['water'] if 'centerline_m' in w] +
                    [(s['polyline_m'], 2) for s in d['functional_sites'] if 'polyline_m' in s])
    blocks = [(b['poly'], [min(p[0] for p in b['poly']), min(p[1] for p in b['poly']), max(p[0] for p in b['poly']), max(p[1] for p in b['poly'])]) for b in phys]

    def near_building(p, gap):
        return any(bb[0]-gap < p[0] < bb[2]+gap and bb[1]-gap < p[1] < bb[3]+gap and v7.gap(poly, p, p) < gap for poly, bb in blocks)

    def inside_any(p, polys, gap=0):
        return any(m.inside(p, q) or (gap and v7.gap(q, p, p) < gap) for q in polys)
    forest = ds['forest']['polygon_m']
    swamp = d['forest_features']['swamp']['polygon_m']
    ponds = [w['polygon_m'] for w in d['water'] if w.get('kind') == 'swamp_pond']
    hill = next(h for h in d['hills'] if h['id'] == 'HILL_FOREST')
    sight = [d['sightline']['from_position_m'], d['sightline']['to_position_m']]
    open_forest = [sites['HANGOUT13']['polygon_m'], oval(hill['center_m'], [r*.86 for r in hill['radii_m']], .9, 40)]
    conifers, rounds = [], []
    for i in range(int(95//6.2), int(560//6.2)):
        for j in range(int(300//6.2), int(560//6.2)):
            p = [i*6.2+jitter(i, j, 1)*4.4-2.2, j*6.2+jitter(i, j, 2)*4.4-2.2]
            if not m.inside(p, forest) or inside_any(p, open_forest) or inside_any(p, [waters['FOREST_LAKE']['polygon_m']], 2.5):
                continue
            if inside_any(p, ponds, 1.5) or ways.near(p, 1.6) or near_building(p, 3):
                continue
            if m.inside(p, swamp) and jitter(i, j, 3) > .35:
                continue
            if m.projection(p, *sight)[0] < 4 and jitter(i, j, 4) > .25:
                continue
            conifers.append([round(p[0], 2), round(p[1], 2), round(2.1+jitter(i, j, 5)*.9, 2)])
    village = ds['village']['polygon_m']
    no_tree = [f['polygon_m'] for f in d['crop_fields']] + [sites['CHURCH12_YARD']['polygon_m'], sites['CHURCH_SQUARE13']['polygon_m']]
    no_tree += [p for e in d['exits'] for p in e['barrier_polygons_m']]
    for i in range(int(100//9.5), int(360//9.5)):
        for j in range(int(550//9.5), int(800//9.5)):
            p = [i*9.5+jitter(i, j, 6)*5-2.5, j*9.5+jitter(i, j, 7)*5-2.5]
            if jitter(i, j, 8) > .5 or not m.inside(p, village) or inside_any(p, no_tree, 2) or ways.near(p, 2.2) or near_building(p, 3.5):
                continue
            rounds.append([round(p[0], 2), round(p[1], 2), round(2.3+jitter(i, j, 9)*1.1, 2)])
    churchyard = sites['CHURCH12_YARD']['polygon_m']
    for a in range(0, 360, 40):
        p = [168+19*math.cos(math.radians(a)), 744+16*math.sin(math.radians(a))]
        if not near_building(p, 3) and not ways.near(p, 2):
            rounds.append([round(p[0], 2), round(p[1], 2), 2.0])
    park = ds['beach_parking']['polygon_m']
    sand = [b['polygon_m'] for b in d['beaches']]
    others = [q['polygon_m'] for q in d['districts'] if q['id'] != 'beach_parking']
    for i in range(int(505//11), int(820//11)):
        for j in range(int(300//11), int(446//11)):
            p = [i*11+jitter(i, j, 10)*6-3, j*11+jitter(i, j, 11)*6-3]
            if jitter(i, j, 12) > .55 or not m.inside(p, d['boundary']['polygon_m']) or inside_any(p, sand, 3) or inside_any(p, others, 1):
                continue
            if inside_any(p, [park], 1.5):
                continue
            if ways.near(p, 2.5) or near_building(p, 3) or inside_any(p, [s['polygon_m'] for s in d['functional_sites'] if s.get('district_id') == 'beach_parking' and 'polygon_m' in s], 2.5):
                continue
            rounds.append([round(p[0], 2), round(p[1], 2), round(2.5+jitter(i, j, 13), 2)])
    return conifers, rounds


def draw_map(d, s, xy, scale, k, area, view):
    ds = {q['id']: q for q in d['districts']}
    sites = {s2['id']: s2 for s2 in d['functional_sites']}
    waters = {w['id']: w for w in d['water']}
    fs = {f['id']: f for f in d['functional_buildings']}
    bs = {b['id']: b for b in d['building_masses']}
    phys = v7.physical(d)

    def poly(p, fill, stroke='none', width=1, **kw):
        s.poly([xy(q) for q in p], fill, stroke, width, **kw)

    def line(p, color, width=1, **kw):
        s.line([xy(q) for q in p], color, width, **kw)

    def dash(*v):
        return ' '.join(f'{x*k:.1f}' for x in v)
    poly(waters['SEA']['polygon_m'], '#b8d7df')
    outfall = d['outfalls'][0]
    poly(outfall['plume']['polygon_m'], '#8d8f4f', '#6c6a3a', 1.1*k, opacity='.6', stroke_dasharray=dash(5, 4))
    poly(oval([1056, 815], [13, 7], 1.1, 24), '#77703c', opacity='.5')
    poly(d['boundary']['polygon_m'], '#e1e4cf')
    for q in d['districts']:
        poly(q['polygon_m'], q['color'], '#9ba396', .7*k)
    for b in d['beaches']:
        poly(b['polygon_m'], '#efdfb2')
        line(b['sea_edge_m'], '#f7edcf', 4*k)
    for p in d['field_parcels_m']:
        poly(p, '#c7c69b', '#b4b68f', .7)
    for f in d['crop_fields']:
        base, stripe = {'wheat': ('#e8cd6e', '#cfa23e'), 'sunflower': ('#f0d64a', '#8e9a44')}[f['crop']]
        poly(f['polygon_m'], base, '#bf9a45', .9*k)
        axis = 0 if f['stripe_direction'] == 'north_south' else 1
        lo, hi = min(p[axis] for p in f['polygon_m']), max(p[axis] for p in f['polygon_m'])
        n = f['stripe_count']
        for i in range(n):
            mid = lo+(hi-lo)*(i+.5)/n
            band = clip_band(f['polygon_m'], axis, mid-(hi-lo)/n*.18, mid+(hi-lo)/n*.18)
            if len(band) >= 3:
                poly(band, stripe, opacity='.75')
    for p in d['plots']:
        color = {'elite_garden': '#afc894', 'farmstead': '#eae1bf', 'front_yard': '#e6d7bd', 'villa_yard': '#d5c598'}.get(p['kind'], '#cfceba')
        poly(p['polygon_m'], color, '#a1b08a' if p['kind'] == 'elite_garden' else '#b3ab94', .55)
    for c in d['microdistricts']:
        poly(c['yard_polygon_m'], '#b7c6a9', '#9fb293', .8*k)
    site_colors = {'churchyard': '#cdd3b0', 'parking': '#bebdb2', 'production_yard': '#b3b2b7', 'tow_parking': '#b8b8b7',
                   'turnaround': '#d0c5a7', 'lake_terrace': '#c3a98c', 'square': '#d9cfba', 'garage_yard': '#c6c3b9',
                   'hangout': '#d3dda6', 'drop_off': '#cbc8ba', 'turning_head': '#bebdb2'}
    for site in d['functional_sites']:
        if 'polygon_m' in site:
            poly(site['polygon_m'], site_colors.get(site['type'], '#cec7b1'), '#969c96', .6*k)
    for box in sites['GARAGE13']['shells_m']:
        poly(box, '#8f9294', '#c9ccce', .4*k)
    for i in (1, 2, 3):
        poly(oval([899, 566], [99-i*19, 115-i*20], 1), 'none', '#a2b78e', .65*k)
    hill = next(h for h in d['hills'] if h['id'] == 'HILL_FOREST')
    poly(hill['polygon_m'], '#c3d4a3', '#9fb585', .8*k)
    for f in (.68, .38):
        poly(oval(hill['center_m'], [r*f for r in hill['radii_m']], .9, 40), 'none', '#9fb585', .6*k)
    sw = d['forest_features']['swamp']
    poly(sw['polygon_m'], '#a3b796', '#839c7c', .9*k, stroke_dasharray=dash(3, 2))
    conifers, rounds = tree_layers(d)
    for x, y, r in conifers:
        cx, cy = xy([x, y])
        rp = max(2.6, r*scale)
        s.poly([[cx, cy-rp*1.25], [cx-rp, cy+rp*.85], [cx+rp, cy+rp*.85]], '#4f7f5a', '#3e6a49', .5)
    for x, y, r in rounds:
        cx, cy = xy([x, y])
        s.circle(cx, cy, max(2.4, r*scale), '#86a874', stroke='#6d905f', stroke_width=f'{.6*k:.1f}', opacity='.92')
    for q in d['vegetation_parcels']:
        if q['kind'] == 'orchard':
            poly(q['polygon_m'], '#b2c198')
            c = centroid(q['polygon_m'])
            for dx, dy in ((-2, -2), (2, 1), (-1, 2)):
                x, y = xy([c[0]+dx, c[1]+dy])
                s.circle(x, y, 3*k, '#7f9f76')
    for rock in d['forest_features']['rocks']:
        poly(rock['polygon_m'], '#a39d93', '#7f786e', .7*k)
    for q in d['vegetation_parcels']:
        if q['kind'] != 'interdistrict_barrier':
            continue
        if q['material'] == 'barbed_fence':
            line(q['axis_m'], BARBED, 1.7*k)
            line(q['axis_m'], BARBED, 5*k, stroke_dasharray=dash(1, 5))
        elif q['material'] == 'rock_scarp':
            line(q['axis_m'], '#877c70', 3.2*k)
        elif q['material'] == 'dune_ridge':
            line(q['axis_m'], DUNE, 4.2*k, opacity='.9')
            line(q['axis_m'], '#9a8456', 2.6*k, stroke_dasharray=dash(1.2, 4.5))
        else:
            line(q['axis_m'], v11.FENCE_STYLES[q['material']][0], (1.5 if q['material'] != 'canal_railing' else .85)*k)
    bp = d['boundary']['polygon_m']
    n = len(d['boundary']['coast_segments_m'])+1
    line([bp[n-1]]+bp[n:]+[bp[0]], '#827b6a', 2.6*k)
    for w in d['water']:
        if w['id'] == 'SEA':
            continue
        if 'polygon_m' in w:
            pond = w.get('kind') == 'swamp_pond'
            poly(w['polygon_m'], '#5d8c88' if pond else '#83b3c5', '#47706c' if pond else '#638e9d', .8*k)
        else:
            if w['id'] == 'CANAL':
                line(w['centerline_m'], '#9babae', w['width_m']*scale)
            line(w['centerline_m'], '#7caec2', w.get('wet_width_m', w['width_m'])*scale)
    rail = d['railway']['polyline_m']
    line(rail, '#b4ad9f', 4.8*scale)
    line(rail, '#52595a', 1.1*k)
    line(rail, '#52595a', 4.6*k, stroke_dasharray=dash(2, 11))
    stub = sites['DEPOT13_RAIL_STUB']['polyline_m']
    line(stub, '#b4ad9f', 4*scale)
    line(stub, '#52595a', 3.6*k, stroke_dasharray=dash(2, 9))
    tx, ty = xy(sites['RAIL_TUNNEL_W']['position_m'])
    s.circle(tx, ty, max(5, 4.5*scale), '#4f4b45', stroke='#2f2c28', stroke_width=f'{1.2*k:.1f}')
    s.circle(tx, ty, max(2.5, 2.4*scale), '#1f1d1b')
    for r in d['roads']:
        line(r['polyline_m'], '#9d9f91', r['width_m']*scale+1.2*k)
        line(r['polyline_m'], d['road_classes'][r['class']]['color'], r['width_m']*scale)
    for p in d['paths']:
        if p['class'] == 'foot_lane':
            line(p['polyline_m'], '#efe5cc', max(2.2, p['width_m']*scale))
            line(p['polyline_m'], '#8f7350', 1.2*k, stroke_dasharray=dash(4, 4))
        elif p['class'] == 'trail':
            line(p['polyline_m'], '#e8dcbc', max(1.8, p['width_m']*scale), opacity='.85')
            line(p['polyline_m'], '#7c6a43', 1.2*k, stroke_dasharray=dash(1.5, 3.5))
        else:
            line(p['polyline_m'], '#997f57', 1.25*k, stroke_dasharray=dash(4, 6))
    for bridge in d['water_crossings']:
        w = next(r['width_m'] for r in d['roads'] if r['id'] == bridge['road_id'])
        line(bridge['deck_axis_m'], '#8a9592', w*scale+1.3)
        line(bridge['deck_axis_m'], '#eee9db', w*scale)
    for ex in d['exits']:
        for p in ex['barrier_polygons_m']:
            poly(p, '#7d8572', '#656d60', .9)
        x, y = xy(ex['dead_end_m'])
        s.line([[x-5*k, y-5*k], [x+5*k, y+5*k]], '#794f45', 2*k)
        s.line([[x-5*k, y+5*k], [x+5*k, y-5*k]], '#794f45', 2*k)
    for lot in ('PARK13_LOT_W', 'PARK13_LOT_E'):
        for bay in sites[lot]['bays']:
            poly(bay['polygon_m'], '#cfc6a6' if not bay['usable'] else 'none', '#f6f3ea', .9*k)
    for x, y in (xy(p) for p in v12.sample_line(sites['PARK13_BOLLARDS']['polyline_m'], 1.6)):
        s.circle(x, y, max(.9, .32*scale), '#4f5456')
    culvert = sites['CANAL_BEACH_CULVERT']['polyline_m']
    line(culvert, '#7caec2', 1.6*k, stroke_dasharray=dash(5, 4), opacity='.85')
    for b in phys:
        f = fs.get(b['id'])
        g = bs.get(b['id'])
        fill = '#a98d73'
        if f:
            fill = '#7d9190' if f['type'] in {'industrial_complex', 'depot', 'warehouse', 'maintenance_shed', 'tow_yard', 'industrial_chimney', 'storage_tank'} else '#a99079'
            if f['type'] in TRASHY and f['district_id'] == 'residential':
                fill = '#c4875a'
            if f.get('poi_id', '').startswith('B'):
                fill = '#b57f56'
            if f['type'] in {'mansion', 'prestige_base'}:
                fill = '#b29473'
            if f['id'].startswith('F12_'):
                fill = '#9b7fa0'
            if f['type'] == 'church':
                fill = '#9584ae'
        elif g and g['kind'] == 'panel':
            fill = '#8d9aa7'
        elif g and g['floors'] >= 12:
            fill = '#7d829b'
        poly(b['poly'], fill, '#566264', .8*k)
        for arch in (g or {}).get('gateway_arches', []):
            a, c = arch['axis_m']
            u = [c[0]-a[0], c[1]-a[1]]
            ln = math.hypot(*u)
            nrm = [-u[1]/ln*arch['width_m']/2, u[0]/ln*arch['width_m']/2]
            poly([[a[0]+nrm[0], a[1]+nrm[1]], [c[0]+nrm[0], c[1]+nrm[1]], [c[0]-nrm[0], c[1]-nrm[1]], [a[0]-nrm[0], a[1]-nrm[1]]],
                 '#f2cf5b' if arch['van_passable'] else '#efe5cc', '#6b5a3b', .6*k)
        if g and (g['kind'] == 'panel' or g['floors'] >= 12):
            c = g['center_m']
            if g.get('gateway_arches'):
                # Put the floor count on the long side away from the arch.
                ang = math.radians(g.get('rotation_deg', 0))
                long_x = g['width_m'] > g['depth_m']
                axis = (math.cos(ang), math.sin(ang)) if long_x else (-math.sin(ang), math.cos(ang))
                am = [sum(p[k] for p in g['gateway_arches'][0]['axis_m'])/2 for k in (0, 1)]
                t_arch = (am[0]-c[0])*axis[0]+(am[1]-c[1])*axis[1]
                shift = (-1 if t_arch > 2 else 1)*.3*max(g['width_m'], g['depth_m'])
                c = [c[0]+axis[0]*shift, c[1]+axis[1]*shift]
            x, y = xy(c)
            size = 10*k if view == 'full' else 13
            s.text(x, y+size*.35, str(g['floors'])+'э', size, '#f8f4e8', 'bold', 'middle')
        if f and f['type'] == 'church':
            x, y = xy(f.get('nave_center_m', f['center_m']))
            arm = max(4, 3*scale)
            s.line([[x, y-arm], [x, y+arm]], '#f6f1e6', 1.6*k)
            s.line([[x-arm*.6, y-arm*.35], [x+arm*.6, y-arm*.35]], '#f6f1e6', 1.6*k)
    # Drinkers' hangout as readable glyphs: exaggerated around the fire so they survive the full-map scale.
    hang = sites['HANGOUT13']['dressing_hints']
    g = max(k, scale/2.2)                                  # glyph unit, px
    spread = max(1.0, 2.6/scale)
    fx, fy = xy(hang['campfire_ring']['position_m'])

    def at(p):
        x, y = xy(p)
        return fx+(x-fx)*spread, fy+(y-fy)*spread
    for log in hang['logs']:
        x, y = at(log['position_m'])
        a = math.radians(log['rotation_deg'])
        dx, dy = math.cos(a)*5.5*g, -math.sin(a)*5.5*g
        s.line([[x-dx, y-dy], [x+dx, y+dy]], '#5e3f26', 3.4*g)
        s.line([[x-dx, y-dy], [x+dx, y+dy]], '#9a6b43', 2.2*g)
    x, y = at(hang['tent']['position_m'])
    s.poly([[x-7*g, y+5*g], [x+7*g, y+5*g], [x, y-6.5*g]], '#5f8fb8', '#2f4f6e', .9*g)
    s.line([[x, y-6.5*g], [x, y+5*g]], '#2f4f6e', .8*g)
    for i, b in enumerate(hang['bottles_and_cans_m']):
        x, y = at(b)
        s.rect(x-1.1*g, y-2.4*g, 2.2*g, 4.8*g, '#2f7a45' if i % 3 else '#8a6a2c', stroke='#f3efe2', stroke_width=f'{.5*g:.1f}')
    x, y = xy(hang['crate_by_wagon_door_m'])
    s.rect(x-3*g, y-3*g, 6*g, 6*g, '#9c7a4c', stroke='#5e4a2c', stroke_width=f'{.7*g:.1f}')
    s.line([[x-3*g, y], [x+3*g, y]], '#5e4a2c', .6*g)
    s.circle(fx, fy, 6.4*g, '#e0752d', stroke='#5b4a3a', stroke_width=f'{1.4*g:.1f}')
    s.circle(fx, fy, 2.8*g, '#f7d04a')
    line(outfall['polyline_m'], '#6d5a3b', 1.6*k, stroke_dasharray=dash(3, 3))
    coast = [a for a, b in d['boundary']['coast_segments_m']]
    wet = [p for p in outfall['polyline_m'] if not m.inside(p, bp)]
    line([outfall['polyline_m'][1]]+wet, '#5c4a30', 2.2*k)
    return place_labels(d, s, xy, scale, k, area, view, phys)


def place_labels(d, s, xy, scale, k, area, view, phys):
    fs = {f['id']: f for f in d['functional_buildings']}
    occupied = []

    def box_points(poly):
        p = [xy(q) for q in poly]
        return (min(x for x, y in p)-3, min(y for x, y in p)-3, max(x for x, y in p)+3, max(y for x, y in p)+3)
    occupied += [box_points(b['poly']) for b in phys]
    for text, p, size in CAPTIONS[view]:
        x, y = xy(p)
        s.text(x, y, text, size, '#546960', 'bold', 'middle', halo=True)
        width = len(text)*size*.55
        occupied.append((x-width/2-4, y-size-3, x+width/2+4, y+5))
    geo = list(GEO_LABELS[view])
    if view == 'alleys':
        for b in d['building_masses']:
            for arch in b.get('gateway_arches', []):
                (lu, lv), _, _ = panel_frame(b['id'])
                mid = [(arch['axis_m'][0][k]+arch['axis_m'][1][k])/2 for k in (0, 1)]
                off = -(arch['width_m']/2+(7.5 if arch['van_passable'] else 4.2))   # floor count sits on the + side or the far end
                geo.append(('арка · бусик' if arch['van_passable'] else 'арка', [mid[0]+lu*off, mid[1]+lv*off], 12))
        geo += [('двор', q['center_m'], 13) for q in d['microdistricts']]
    for text, p, size in geo:
        x, y = xy(p)
        s.text(x, y, text, size, '#5f7477', 'normal', 'middle', halo=True)
        width = len(text)*size*.55
        occupied.append((x-width/2-2, y-size-1, x+width/2+2, y+3))
    labels = []
    x0, y0, x1, y1 = area
    inside_view = lambda p: x0 <= xy(p)[0] <= x1 and y0 <= xy(p)[1] <= y1
    for p in d['points']:
        pid = p['id']
        value = POINT_NAMES[pid] if p['category'] in {'reference', 'landmark'} or pid.startswith('BEACH') else pid+' · '+POINT_NAMES[pid]
        if inside_view(p['position_m']) and not (view == 'full' and pid.startswith('BAD_BLOCK')):
            labels.append((0 if pid.startswith('B0') else 1, p['position_m'], value, p['category'] == 'base'))
    for fid, value in SHORT.items():
        if fid in fs and inside_view(fs[fid]['center_m']) and (view != 'full' or not (fid in ('F06_K1', 'F06_K3') or fid in BUSINESSES)):
            labels.append((2, fs[fid]['center_m'], value, False))
    label_boxes = []

    def intersection(a, b):
        return max(0, min(a[2], b[2])-max(a[0], b[0]))*max(0, min(a[3], b[3])-max(a[1], b[1]))
    base_size = 15 if view == 'full' else 16
    for _, p, value, base in sorted(labels, key=lambda q: q[0]):
        x, y = xy(p)
        size = base_size+(1 if base else 0)
        w, h = len(value)*size*.55, size+4
        candidates = []
        for radius in (14, 30, 48, 70, 100, 135):
            for dx, dy in ((1, -1), (1, 1), (-1, -1), (-1, 1), (0, -1), (0, 1), (1, 0), (-1, 0)):
                lx, ly = x+dx*radius, y+dy*radius
                if dx < 0:
                    lx -= w
                elif dx == 0:
                    lx -= w/2
                if dy == 0:
                    ly += h/3
                box = (lx-4, ly-h, lx+w+4, ly+5)
                if box[0] < x0 or box[2] > x1 or box[1] < y0 or box[3] > y1:
                    continue
                score = sum(intersection(box, b) for b in occupied)*12+radius+abs(dx)*2
                candidates.append((score, box, lx, ly, radius))
        if not candidates:
            continue
        _, box, lx, ly, radius = min(candidates)
        tx, ty = max(box[0], min(x, box[2])), max(box[1], min(y, box[3]))
        if radius >= 30:
            s.line([[x, y], [tx, ty]], '#7e8b88', .75)
        s.circle(x, y, 3.8 if base else 2.8, '#b36f3f' if base else '#47707a', stroke='#f5f1e6', stroke_width='1')
        s.text(lx, ly, value, size, '#3b4e51', 'bold' if base else 'normal', halo=True)
        occupied.append(box)
        label_boxes.append(box)
    overlaps = sum(intersection(a, b) > 0 for i, a in enumerate(label_boxes) for b in label_boxes[i+1:])
    return len(label_boxes), overlaps


CAPTIONS = {
    'full': [('ЛЕС · БОЛОТО · ОЗЕРО · ХОЛМ', [205, 352], 17), ('ХУТОР', [262, 772], 17), ('ПЕРЕХОД', [413, 775], 17),
             ('РАЙОН ПОДВОРОТЕН', [628, 880], 17), ('СТАРЫЙ ГОРОД', [589, 535], 17), ('ЭЛИТНЫЙ ХОЛМ', [891, 585], 17),
             ('ПРОМЗОНА', [918, 903], 17), ('МАЛАЯ ДОЛИНА', [421, 453], 17), ('ПЛЯЖ · 55 м', [820, 318], 17),
             ('БУХТА', [262, 296], 17), ('ПЛЯЖНАЯ ПАРКОВКА', [652, 402], 14), ('МОРЕ', [700, 150], 25),
             ('Тусовка у вагона: костёр, бутылки', [236, 399], 13)],
    'alleys': [('РАЙОН ПОДВОРОТЕН', [640, 877], 26), ('СТАРЫЙ ГОРОД', [700, 618], 20)],
    'hamlet_forest': [('ХУТОР', [250, 790], 26), ('ЛЕС', [300, 545], 24), ('БУХТА', [262, 298], 22), ('ПЕРЕХОД', [420, 770], 18),
                      ('МАЛАЯ ДОЛИНА', [425, 455], 18), ('ТУСОВКА У ВАГОНА', [250, 392], 17)],
    'industrial_carpark': [('ПРОМЗОНА', [905, 905], 26), ('ПЛЯЖНАЯ ПАРКОВКА', [652, 400], 20), ('РАЙОН ПОДВОРОТЕН', [640, 878], 20),
                           ('СТАРЫЙ ГОРОД', [640, 520], 20), ('ЭЛИТНЫЙ ХОЛМ', [895, 600], 20), ('ПЛЯЖ', [800, 300], 20), ('МОРЕ', [1060, 560], 26)],
}
GEO_LABELS = {
    'full': [('Озеро', [434, 575], 12), ('Проспект', [738, 718], 12), ('Прямая улица', [489, 611], 12), ('Канал', [572, 434], 12),
             ('Болото', [143, 532], 12), ('Лесное озеро', [286, 512], 12), ('Холм', [292, 372], 12), ('Тоннель', [128, 362], 12),
             ('Слив', [1062, 838], 13), ('Гаражи', [520, 857], 12), ('Колючка', [788, 830], 12), ('дюна', [520, 318], 12)],
    'alleys': [('Проспект', [478, 727], 14), ('проезд', [522, 812], 13), ('проезд', [573, 800], 13), ('проезд', [622, 806], 13),
               ('проезд', [548, 684], 13), ('Гаражи-ракушки', [520, 856], 14), ('Пятачок', [626, 704], 14)],
    'hamlet_forest': [('Пшеница', [240, 731], 14), ('Пшеница', [256, 633], 14), ('Подсолнух', [160, 701], 14),
                      ('Пшеница', [299, 575], 13), ('Пшеница', [156, 590], 14),
                      ('Болото', [143, 537], 16), ('Лесное озеро', [286, 489], 15), ('Холм', [286, 404], 15),
                      ('спиральная тропа', [286, 345], 13), ('костёр · брёвна · палатка · бутылки', [236, 409], 13),
                      ('Рельсы в тоннель', [140, 377], 14), ('Тоннель', [116, 368], 13), ('Площадка', [188, 712], 13),
                      ('Церковный двор', [160, 776], 13), ('мостки', [170, 495], 12), ('скалы', [104, 440], 12),
                      ('тропа к бухте', [214, 322], 13), ('Река — граница перехода', [438, 498], 13),
                      ('дюна: бусик не проедет', [372, 318], 13)],
    'industrial_carpark': [('колючка 2,8 м', [786, 878], 14), ('Ворота 7,5 м', [790, 744], 14),
                           ('колючка до воды', [930, 712], 14), ('Слив B05', [1015, 828], 15), ('Грязное пятно', [1062, 795], 15),
                           ('Набережная', [1013, 852], 14), ('Тупиковый путь', [880, 860], 13),
                           ('23 места', [620, 388], 15), ('23 места', [681, 388], 15), ('Высадка', [652, 341], 13),
                           ('разворот', [593, 381], 13), ('разворот', [709, 381], 13),
                           ('Столбики — бусик не проедет', [652, 328], 13), ('тропинки на песок', [700, 300], 13),
                           ('дюна с плавником — бусик не проедет', [610, 304], 13),
                           ('Канал', [560, 434], 14), ('Перила канала', [740, 446], 12), ('Выпуск канала под землёй', [880, 404], 13)],
}


def swatch(s, kind, x, y):
    """26 x 17 px legend icon whose top-left corner is (x, y-12)."""
    if kind == 'field':
        s.rect(x, y-12, 26, 17, '#e8cd6e')
        for dx in (6, 15):
            s.rect(x+dx, y-12, 3.5, 17, '#cfa23e')
    elif kind == 'swamp':
        s.rect(x, y-12, 26, 17, '#a3b796')
        s.circle(x+9, y-3, 4, '#5d8c88')
        s.circle(x+19, y-5, 3, '#5d8c88')
    elif kind == 'conifer':
        for dx in (5, 17):
            s.poly([[x+dx, y-13], [x+dx-6, y+4], [x+dx+6, y+4]], '#4f7f5a', '#3e6a49', .5)
    elif kind == 'round':
        for dx in (7, 19):
            s.circle(x+dx, y-3, 6, '#86a874', stroke='#6d905f', stroke_width='.8')
    elif kind == 'hill':
        s.circle(x+13, y-3, 10, '#c3d4a3', stroke='#9fb585', stroke_width='1')
        s.circle(x+13, y-3, 5, 'none', stroke='#7c6a43', stroke_width='1', stroke_dasharray='1.5 2')
    elif kind == 'fire':
        s.circle(x+13, y-3, 6, '#e0752d', stroke='#6b5a4a', stroke_width='.8')
        s.circle(x+13, y-3, 2.5, '#f7d04a')
    elif kind == 'bays':
        s.rect(x, y-12, 26, 17, '#bebdb2')
        for dx in (6, 13, 20):
            s.line([[x+dx, y-12], [x+dx, y+5]], '#f6f3ea', 1.2)
    elif kind == 'plume':
        s.poly([[x-1, y-4], [x+13, y-12], [x+27, y-4], [x+13, y+5]], '#8d8f4f', '#6c6a3a', 1, opacity='.7')
        s.line([[x-13, y-4], [x-1, y-4]], '#5c4a30', 2)
    elif kind == 'arch':
        s.rect(x, y-12, 26, 17, '#8d9aa7')
        s.rect(x+4, y-12, 5, 17, '#efe5cc')
        s.rect(x+15, y-12, 6, 17, '#f2cf5b')
    elif kind == 'vanarch':
        s.rect(x, y-12, 26, 17, '#8d9aa7')
        s.rect(x+10, y-12, 7, 17, '#f2cf5b')
    elif kind == 'footarch':
        s.rect(x, y-12, 26, 17, '#8d9aa7')
        s.rect(x+10, y-12, 6, 17, '#efe5cc')
    elif kind in ('shop', 'panel', 'industry'):
        s.rect(x, y-12, 26, 17, {'shop': '#c4875a', 'panel': '#8d9aa7', 'industry': '#7d9190'}[kind], stroke='#566264', stroke_width='.8')
    elif kind == 'court':
        s.rect(x, y-12, 26, 17, '#b7c6a9', stroke='#9fb293', stroke_width='.8')
    elif kind == 'water':
        s.rect(x, y-12, 26, 17, '#83b3c5', stroke='#638e9d', stroke_width='.8')
    elif kind == 'alley':
        s.line([[x, y-3], [x+26, y-3]], '#9d9f91', 9)
        s.line([[x, y-3], [x+26, y-3]], '#eadcb6', 8)
    elif kind == 'lane':
        s.line([[x, y-3], [x+26, y-3]], '#efe5cc', 5)
        s.line([[x, y-3], [x+26, y-3]], '#8f7350', 1.2, stroke_dasharray='4 4')
    elif kind == 'trail':
        s.line([[x, y-3], [x+26, y-3]], '#e8dcbc', 3.4)
        s.line([[x, y-3], [x+26, y-3]], '#7c6a43', 1.2, stroke_dasharray='1.5 3.5')
    elif kind == 'passage':
        s.line([[x, y-3], [x+26, y-3]], '#997f57', 1.4, stroke_dasharray='4 6')
    elif kind == 'rail':
        s.line([[x, y-3], [x+26, y-3]], '#b4ad9f', 7)
        s.line([[x, y-3], [x+26, y-3]], '#52595a', 1.1)
    elif kind == 'barbed':
        s.line([[x, y-3], [x+26, y-3]], BARBED, 1.7)
        s.line([[x, y-3], [x+26, y-3]], BARBED, 5, stroke_dasharray='1 5')
    elif kind == 'dune':
        s.line([[x, y-3], [x+26, y-3]], DUNE, 4.2)
        s.line([[x, y-3], [x+26, y-3]], '#9a8456', 2.6, stroke_dasharray='1.2 4.5')
    elif kind == 'bollard':
        for dx in range(2, 26, 5):
            s.circle(x+dx, y-3, 1.4, '#4f5456')


CROP_LEGEND = {
    'alleys': [('panel', 'панелька · этажи'), ('shop', 'ларёк / бар / магазин'), ('footarch', 'арка пешая'),
               ('vanarch', 'арка для бусика'), ('court', 'двор'), ('alley', 'проезд 4,5 м'), ('lane', 'пеший проход 3 м')],
    'hamlet_forest': [('field', 'поле'), ('conifer', 'хвойный лес'), ('round', 'деревья хутора'), ('swamp', 'болото'),
                      ('water', 'озеро'), ('hill', 'холм и спираль'), ('fire', 'костёр у вагона'), ('trail', 'тропа 2 м'),
                      ('rail', 'рельсы в тоннель')],
    'industrial_carpark': [('industry', 'промзона'), ('barbed', 'колючая проволока'), ('plume', 'слив и пятно'),
                           ('bays', 'места 3,25 × 7 м'), ('bollard', 'столбики'), ('passage', 'тропинка на песок'),
                           ('dune', 'дюна'), ('shop', 'ларёк / бар / магазин')],
}


def legend_full(d, s, scale):
    s.line([[65, 1800], [2335, 1800]], '#c1c8ba', 1)
    s.text(75, 1842, 'ДОРОГИ И ПРЕГРАДЫ', 19, '#3b555a', 'bold')
    rows = [('highway', 'Проспект — 7 м, 2 полосы'), ('town_street', 'Городская — 6 м, 2 полосы'),
            ('rural_road', 'Сельская — 3,8 м, 1 полоса'), ('alley', 'Проезд подворотен — 4,5 м'),
            ('foot_lane', 'Пеший проход / арка — 3 м'), ('trail', 'Лесная тропа — 2 м'), ('passage', 'Пешком к пляжу — 2,5 м')]
    for i, (cls, label) in enumerate(rows):
        y = 1872+i*29
        if cls == 'passage':
            s.line([[78, y], [130, y]], '#997f57', 1.25, stroke_dasharray='4 6')
        elif cls == 'foot_lane':
            s.line([[78, y], [130, y]], '#efe5cc', 5)
            s.line([[78, y], [130, y]], '#8f7350', 1.2, stroke_dasharray='4 4')
        elif cls == 'trail':
            s.line([[78, y], [130, y]], '#e8dcbc', 3.4)
            s.line([[78, y], [130, y]], '#7c6a43', 1.2, stroke_dasharray='1.5 3.5')
        else:
            s.line([[78, y], [130, y]], '#9d9f91', 10.2)
            s.line([[78, y], [130, y]], d['road_classes'][cls]['color'], 9)
        s.text(143, y+5, label, 16)
    for i, (material, label) in enumerate([('elite_fence', 'Ограда элитки — 2,4 м'), ('barbed_fence', 'Колючая проволока промзоны — 2,8 м'),
                                           ('rock_scarp', 'Скалы / закрытый край'), ('dune_ridge', 'Дюна над пляжем: бусик не проедет'),
                                           ('canal_railing', 'Перила канала — 1,1 м')]):
        y = 2086+i*29
        if material == 'barbed_fence':
            s.line([[78, y], [130, y]], BARBED, 1.7)
            s.line([[78, y], [130, y]], BARBED, 5, stroke_dasharray='1 5')
        elif material == 'dune_ridge':
            s.line([[78, y], [130, y]], DUNE, 4.2)
            s.line([[78, y], [130, y]], '#9a8456', 2.6, stroke_dasharray='1.2 4.5')
        else:
            s.line([[78, y], [130, y]], v11.FENCE_STYLES[material][0], 3.2 if material == 'rock_scarp' else 2)
        s.text(143, y+5, label, 16)
    s.text(560, 1842, 'ФИЗИЧЕСКИЕ ЗДАНИЯ', 19, '#3b555a', 'bold')
    for i, q in enumerate(d['districts']):
        y = 1872+i*30
        s.rect(560, y-12, 17, 17, q['color'])
        s.text(589, y+2, q['name_ru'], 16)
        s.text(930, y+2, str(q['building_count']), 16, '#3b555a', 'bold', 'end')
    old = d['comparison']['v12']['building_counts_by_district']['residential']
    s.text(560, 2160, 'Всего: '+str(d['metrics']['building_count'])+'  ·  подворотни: '+str(old)+' → '+
           str(d['metrics']['building_counts_by_district']['residential']), 17, '#3b555a', 'bold')
    s.text(985, 1842, 'МАРШРУТЫ НА БУСИКЕ', 19, '#3b555a', 'bold')
    names = {'BAD_CENTER': 'центр района', 'CLOCK_SQUARE': 'площадь', 'ELITE_GATE': 'элитка', 'B05': 'B05 промзона',
             'BEACH_PARK_ENTRY': 'пляжная парковка', 'P03': 'P03 аптека'}
    pairs = [('B01', 'P03'), ('B01', 'BAD_CENTER'), ('B01', 'CLOCK_SQUARE'), ('B02', 'CLOCK_SQUARE'), ('BAD_CENTER', 'CLOCK_SQUARE'),
             ('CLOCK_SQUARE', 'ELITE_GATE'), ('BAD_CENTER', 'B05'), ('CLOCK_SQUARE', 'BEACH_PARK_ENTRY')]
    for i, (a, b) in enumerate(pairs):
        r = next(r for r in d['metrics']['routes'] if r['from_id'] == a and r['to_id'] == b)
        src = {'BAD_CENTER': 'Центр района', 'CLOCK_SQUARE': 'Площадь'}.get(a, a)
        s.text(985, 1872+i*30, src+' → '+names[b], 16)
        s.text(1390, 1872+i*30, f'{r["length_m"]:.0f} м', 16, '#3b555a', 'bold', 'end')
    s.text(1450, 1842, 'НОВОЕ НА СХЕМЕ', 19, '#3b555a', 'bold')
    items = [('field', 'Поля хутора (полосы)'), ('swamp', 'Болото и бочаги'), ('conifer', 'Хвойный лес'),
             ('hill', 'Холм со спиральной тропой'), ('fire', 'Костёр у вагона (тусовка)'), ('bays', 'Парковка: места 3,25 × 7 м'),
             ('plume', 'Слив и грязное пятно'), ('arch', 'Арка: пешая / для бусика'), ('shop', 'Ларьки, бары, магазины'),
             ('dune', 'Дюна над пляжем')]
    for i, (kind, label) in enumerate(items):
        y = 1868+i*28
        swatch(s, kind, 1453, y)
        s.text(1493, y+3, label, 16)
    s.text(1905, 1842, 'КЛЮЧЕВЫЕ ИЗМЕНЕНИЯ v13', 19, '#3b555a', 'bold')
    st = d['alley_statistics']
    for i, text in enumerate([f'Спальник → район подворотен: {st["panel_house_count"]} панелек,',
                              f'{st["gateway_arch_count"]} арок ({st["van_arch_count"]} для бусика), лавки вперемешку; притон есть.',
                              f'Хутор и лес по картинке Феди: церковь СЗ, {len(d["crop_fields"])} полей,',
                              'болото, озеро, холм, вагон у костра.',
                              'Промзона в СВ углу, слив в море.',
                              'Старая промзона → парковка (46) и зелень с дюной.',
                              'Переход, старый город, элитка, пляж — без изменений.',
                              'Долина: убрана ЖД к промзоне — на решение Феди.',
                              'Заборов на границах районов нет; колючка только',
                              'у промзоны, ограда только у элитки.']):
        s.text(1905, 1872+i*30, text, 15)
    s.text(75, 2262, 'Проверки: '+str(len(d['validation']['checks']))+' / '+str(len(d['validation']['checks'])) +
           ' — геометрия, маршруты, связность, подворотни, лес, промзона, парковка. Промежутки между районами — общая зелень.', 16, '#607371')
    s.text(75, 2290, 'Схема ArtSource в метрах, вне импорта Unity. Субъективное качество и движение требуют проверки в игре.', 15, '#74827c')


def render(d):
    s = m.SVG()
    s.rect(0, 0, 2400, 2400, BG)
    s.text(75, 65, 'VOLUNTEERS ONLY   /   R01 — v13', 34, '#273c42', 'bold')
    s.text(75, 99, 'Район подворотен · хутор и лес по картинке Феди · промзона в СВ углу · пляжная парковка · 05.10.2026', 19, '#627372')
    visible = d['boundary']['polygon_m']+next(w['polygon_m'] for w in d['water'] if w['id'] == 'SEA')
    lo = [min(p[k] for p in visible) for k in (0, 1)]
    hi = [max(p[k] for p in visible) for k in (0, 1)]
    scale = min(2130/(hi[0]-lo[0]), 1510/(hi[1]-lo[1]))
    left, top = 95+(2130-(hi[0]-lo[0])*scale)/2, 160

    def xy(p):
        return [left+(p[0]-lo[0])*scale, top+(hi[1]-p[1])*scale]
    count, overlaps = draw_map(d, s, xy, scale, 1, (45, 120, 2355, 1730), 'full')
    s.line([[2280, 235], [2280, 170]], '#3c5358', 2)
    s.poly([[2280, 155], [2271, 176], [2289, 176]], '#3c5358')
    s.text(2280, 140, 'С', 20, '#3c5358', 'bold', 'middle')
    s.line([[85, 1745], [85+100*scale, 1745]], '#3c5358', 3)
    for dist in (0, 50, 100):
        x = 85+dist*scale
        s.line([[x, 1738], [x, 1752]], '#3c5358', 1.3)
        s.text(x, 1774, str(dist)+' м', 13, '#4c6265', 'normal', 'middle')
    s.text(2340, 1770, 'Размер суши: '+' × '.join(f'{z:.0f}' for z in d['metrics']['extent_m'])+' м', 16, '#4c6265', 'normal', 'end')
    legend_full(d, s, scale)
    d['render_statistics'] = dict(canvas_px=[2400, 2400], scale_px_per_m=round(scale, 4), label_count=count, overlapping_label_pairs=overlaps)
    return s.finish()


def render_crop(d, view):
    title, (x0, y0, x1, y1) = CROPS[view]
    bw, bh = x1-x0, y1-y0
    scale = min(2280/bw, 2120/bh)
    width, height = round(bw*scale+120), round(bh*scale+280)
    top = 178
    s = m.SVG()
    s.parts[0] = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    s.rect(0, 0, width, height, BG)

    def xy(p):
        return [60+(p[0]-x0)*scale, top+(y1-p[1])*scale]
    k = 1.6
    count, overlaps = draw_map(d, s, xy, scale, k, (50, top+5, width-50, height-105), view)
    s.rect(0, 0, width, top-6, BG)
    s.rect(0, height-100, width, 100, BG)
    s.rect(0, 0, 58, height, BG)
    s.rect(width-58, 0, 58, height, BG)
    s.line([[58, top-2], [width-58, top-2], [width-58, height-102], [58, height-102], [58, top-2]], '#9aa49a', 1.2)
    lx, ly = 60, 130
    for kind, label in CROP_LEGEND[view]:
        pad = 14 if kind == 'plume' else 0
        step = pad+26+12+len(label)*15*.55+34
        if lx+step > width-60:
            lx, ly = 60, ly+28
        swatch(s, kind, lx+pad, ly)
        s.text(lx+pad+36, ly+2, label, 15, '#3b4e51')
        lx += step
    s.text(60, 55, 'R01 — v13 · '+title, 30, '#273c42', 'bold')
    s.text(60, 92, f'Фрагмент x {x0}–{x1} м, y {y0}–{y1} м · {scale:.2f} px/м · названия на русском', 17, '#627372')
    bar = 25 if bw < 450 else 50
    s.line([[70, height-55], [70+bar*2*scale, height-55]], '#3c5358', 3)
    for dist in (0, bar, 2*bar):
        x = 70+dist*scale
        s.line([[x, height-62], [x, height-48]], '#3c5358', 1.3)
        s.text(x, height-25, str(dist)+' м', 14, '#4c6265', 'normal', 'middle')
    s.line([[width-90, 98], [width-90, 40]], '#3c5358', 2)
    s.poly([[width-90, 28], [width-99, 48], [width-81, 48]], '#3c5358')
    s.text(width-120, 52, 'С', 20, '#3c5358', 'bold', 'middle')
    s.text(width-70, height-40, 'Схема на согласование Феде; Unity — только после «ок».', 15, '#74827c', 'normal', 'end')
    d['render_statistics'].setdefault('crops', {})[view] = dict(canvas_px=[width, height], scale_px_per_m=round(scale, 3),
                                                                 label_count=count, overlapping_label_pairs=overlaps)
    return s.finish(), (width, height)


def to_png(svg, path, size):
    subprocess.run([MAGICK, '-background', BG, '-density', '96', 'svg:-', '-define', 'png:exclude-chunk=date,time', str(path)],
                   input=svg.encode('utf-8'), check=True, cwd=ROOT)
    raw = path.read_bytes()
    assert raw[:8] == b'\x89PNG\r\n\x1a\n' and struct.unpack('>II', raw[16:24]) == tuple(size), (path.name, struct.unpack('>II', raw[16:24]))


def report(d):
    met, st = d['metrics'], d['alley_statistics']
    counts = met['building_counts_by_district']
    old = d['comparison']['v12']
    ds = {q['id']: q for q in d['districts']}
    lengths = {(r['from_id'], r['to_id']): r['length_m'] for r in met['routes']}
    checks = d['validation']['checks']
    lake_area = m.area(next(w for w in d['water'] if w['id'] == 'FOREST_LAKE')['polygon_m'])
    old_forest = next(q for q in source_data()['districts'] if q['id'] == 'forest')['area_m2']
    fields = Counter(f['crop'] for f in d['crop_fields'])
    pts = {p['id']: p for p in d['points']}
    yard = next(s for s in d['functional_sites'] if s['id'] == 'CHURCH12_YARD')['polygon_m']
    p16_gap = v7.gap(yard, pts['P16']['position_m'], pts['P16']['position_m'])

    def num(v):
        return f'{v:,.0f}'.replace(',', ' ')

    def dec(v):
        return f'{v:.1f}'.replace('.', ',')
    lines = [
        '# R01 v13 — подворотни, хутор и лес по картинке, промзона в СВ углу, пляжная парковка',
        '',
        'Бриф Феди от 05.10.2026 (вечер) и картинка REF_FEDYA_v13_hamlet_forest.png; правки по двум ревью. Это схема на «ок» Феди; Unity — после.',
        f'Суша {dec(met["extent_m"][0])} × {dec(met["extent_m"][1])} м (≤1000), площадь {num(met["area_m2"])} м² (было {num(old["land_area_m2"])}); '
        f'физических зданий: {met["building_count"]} (было {old["building_count"]}).',
        '',
        '## 1. Неблагополучный район → район подворотен (id residential сохранён)',
        f'- Корпуса-«П» убраны. {st["panel_house_count"]} панелек {st["floors_range"][0]}–{st["floors_range"][1]} этажей в маленьких кварталах '
        f'(5 севернее проспекта, 2 южнее) стоят тесно: до ближайшего соседа обычно (медиана) {dec(st["median_nearest_facade_gap_m"])} м, '
        f'минимум {dec(st["min_gap_between_buildings_m"])} м.',
        f'- {st["gateway_arch_count"]} арок-подворотен, из них {st["van_arch_count"]} для бусика (с проспекта под R13_P03 и ALLEY_X под R13_P06). '
        'Проезды ALLEY_W/COURT_B/ALLEY_C/ALLEY_X/ALLEY_S по 4,5 м, пешие проходы LANE_A/N/C/R/Y/E/E2/S по 3 м, без тупиков.',
        '- Лавки чередуются с панельками в каждом квартале: «Дискаунтер», «Разливное пиво», «Продукты · банкомат» (P11-2 у двери), '
        '«Ломбард», «Шаурма 24», «Займы до зарплаты», «Рюмочная», «Ставки»; плюс бар P06, магазин 24 ч и два ларька. '
        f'Это настоящие здания с подъездом, а не надписи; {len(st["interleaved_business_ids"])} из них внутри кварталов, а не на проспекте.',
        '- Притон P07 оставлен «похихикать»; больница P08, ATM P11-3, гараж B03, пост СВ на месте. За подворотней один ряд из 12 гаражей-ракушек.',
        f'- Район ужат по кварталам: {num(st["district_area_m2"])} м² (было {num(st["v12_district_area_m2"])}), застройка {dec(st["built_coverage_percent"])} %; '
        'пустые север и юго-восток стали общей зеленью. Ларёк F06_K2 из v12 удалён (removed_buildings).',
        '- «Подворотни» 1–3 (BAD_BLOCK*) стоят у арок на проездах, а не на проспекте.',
        '',
        '## 2. Хутор и лес по картинке',
        '- Церковь с колокольней в СЗ углу хутора; площадка смотрит на хуторскую улицу. Пост СЗ P16 с тупиком отнесён к западному краю, '
        f'{num(p16_gap)} м от церковного двора.',
        f'- {len(d["crop_fields"])} полосатых полей ({fields["wheat"]} пшеницы, {fields["sunflower"]} подсолнух), как на картинке; '
        'церковная улица и подъезды к усадьбам — плавные S-кривые; подъезд к аптеке P03 короче.',
        f'- Лес {num(ds["forest"]["area_m2"])} м² (был {num(old_forest)}) с неровным краем выходит к Лесной бухте; слева болото с '
        f'{len(d["forest_features"]["swamp"]["pond_ids"])} бочагами, справа озеро {num(lake_area)} м², снизу холм со спиральной тропой; '
        f'по скалистому краю и бухте {len(d["forest_features"]["rocks"])} групп камней.',
        '- Вагон B01 на рельсах в тоннель на западном берегу. Рядом поляна «Тусовка у вагона»: костёр, три бревна, палатка, бутылки, '
        'ящик сбоку вагона (5 м от двери, бусику не мешает) — на общей карте подписано.',
        '- Зона перехода не тронута (кроме ушедшей церкви). Река — её граница с одним переездом, как в v12 (S01 у прямой дороги); '
        'двух мостов с картинки не добавляли, потому что переход оставлен нашим.',
        '',
        '## 3. Промзона → правый верхний угол',
        '- Новый угол суши с набережной; I_ACCESS от конца проспекта, ворота 7,5 м, кольцевой проезд I_YARD.',
        '- B05 с трубой 85 м, эвакуатор P12 (≈8 бусиков), депо P14 с тупиковым путём, склад, ремонтный сарай + резервуар.',
        '- Колючая проволока 2,8 м только по западу (по изгибу промзоны) и югу до воды; набережная открыта. Слив B05 — труба '
        f'{d["outfalls"][0]["length_m"]:.0f} м в море, там грязное пятно {num(d["outfalls"][0]["plume"]["area_m2"])} м².',
        '- Раскладка — заготовка до второй фотки Феди: кольцо + 7 зданий по id, легко переставить.',
        '',
        '## 4. Пляжная парковка на месте старой промзоны',
        f'- Только асфальт ~{num(m.area(ds["beach_parking"]["polygon_m"]))} м²: два ряда по 24 места 3,25 × 7 м (2 места — проходы к тропинкам) = 46; '
        'прямые проезды с разворотами 13 м на концах; въезд один — PARK_ROAD с I_CONNECT.',
        '- Высадка, киоск, туалет/душ; три тропинки на песок, столбики по краю. Остальная полоса — зелень с деревьями.',
        '',
        '## 5. Без изменений и правила',
        '- Переход, старый город, элитка и основной пляж как в v12 (проверка guard). В долине убрана только ЖД к старой промзоне — вопрос Феде.',
        '- 12 заборов v12 на границах районов удалены и записаны (removed_barriers). Над пляжем вместо них дюна с плавником: люди проходят, '
        'бусик нет, на песок по-прежнему только 2 въезда. Между переходом, хутором, лесом и долиной ничего не ставили (как и в Unity сейчас).',
        f'- Переезды: {len(d["moves"])} записей в moves (id сохранены): B01, P16, церковь, B05/P12/P14/труба, P09-3, P11-2, P13-4, подворотни.',
        '',
        '| Маршрут на бусике | м |',
        '|---|---:|',
    ]
    for a, b in [('B01', 'P01'), ('B01', 'P02'), ('B01', 'P03'), ('B01', 'BAD_CENTER'), ('BAD_CENTER', 'CLOCK_SQUARE'),
                 ('CLOCK_SQUARE', 'ELITE_GATE'), ('BAD_CENTER', 'B05'), ('CLOCK_SQUARE', 'BEACH_PARK_ENTRY'), ('B01', 'P16')]:
        lines.append(f'| {a} → {b} | {lengths[a, b]:.1f} |')
    lines += ['',
        f'Проверки: {sum(c["passed"] for c in checks)}/{len(checks)} пройдены. Районные здания: ' +
        ', '.join(f'{q["name_ru"]} {counts.get(q["id"], 0)}' for q in d['districts'])+'.',
        'Вопросы Феде: 1) ЖД через долину убрана — оставить так? 2) бусик может срезать по траве между районами — ок или нужны '
        'естественные преграды (канава, камни)? 3) мосты с картинки к переходу не добавлены; 4) бухта только пешком; '
        '5) промзона ждёт вторую фотку.',
        'Файлы: MAP_PLAN_R01_v13.json/.svg/.png, кропы _crop_alleys, _crop_hamlet_forest, _crop_industrial_carpark. '
        'Дрессинг и толпа v13 не пересобирались — после «ок».']
    assert len(lines) <= 60, len(lines)
    return '\n'.join(lines)+'\n'



def main():
    before = hashes()
    d = seed()
    analyse(d)
    svg = render(d)
    ET.fromstring(svg)
    (ROOT/(STEM+'.svg')).write_text(svg, encoding='utf-8')
    to_png(svg, ROOT/(STEM+'.png'), (2400, 2400))
    for view in CROPS:
        crop, size = render_crop(d, view)
        ET.fromstring(crop)
        to_png(crop, ROOT/f'{STEM}_crop_{view}.png', size)
    (ROOT/(STEM+'.json')).write_text(json.dumps(d, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    (ROOT/(STEM+'_REPORT.md')).write_text(report(d), encoding='utf-8')
    assert hashes() == before, 'A previous deliverable changed'
    checks = d['validation']['checks']
    print(json.dumps(dict(passed=d['validation']['passed'], checks=f'{sum(c["passed"] for c in checks)}/{len(checks)}',
        extent_m=d['metrics']['extent_m'], building_count=d['metrics']['building_count'],
        by_district=d['metrics']['building_counts_by_district'], report_lines=len(report(d).splitlines()),
        render=d['render_statistics']), ensure_ascii=False))


if __name__ == '__main__':
    main()
