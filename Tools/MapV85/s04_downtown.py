"""Step 4 / district 05 Downtown: plan v31 -> world v85 district data (lead brief "Map W85 build", CL-MAP85, 2026-10-21).

Authority (handoff v10 §0-§1, §4, §6, §7.5, §8; v02 §8.5; DOWNTOWN_LEGEND_v26 + DOWNTOWN_SPEC v03 where v10 is silent):
 footprints = the bld() polygons of Vadim's generator build_gorod_v31.py read back from Город_Downtown_v31.svg (group 'buildings',
 matched 1:1 with group 'shadows' -> conditional height class h of bld()); kinds from the generator colours + the numbered labels
 of group 'numbers'; streets = ST of build_gorod_v31.py (cross-checked with the asphalt polylines of the SVG); plaza, parking 03,
 base 13, yards 42/43, alleys, squares 20/23, gas 41, taxi 12 = the drawn plan geometry (squares_and_lots / buildings groups).
 v10 rules put into the data: streets 12 m + 2 x 5 m sidewalks (22 m between facades), curb 0.15 m, dead ends 5.6 m, houses 5-8 floors
 (corners higher), calmed "American" tints, varied facades / ground floors; trees only in squares 20 and 23; world-road entries.
 Drawing artefacts of the plan are fixed and logged in "fixed_by_logic"; gameplay-level choices are in "questions_for_vadim".

Chain (derived from the sources at run time, see `load_chain`): plan units (x east, y south, 1 u = 0.2 m) -> Chrome render of the plan
SVG (width / viewBox = 1.3 px/u) -> make_downtown_world_v31 resize 1/1.3 -> downtown_v31_world.png (1 px = 1 u) -> master-SVG units
(<image> x 590 y 0 inside D05 translate(2820 1000)) -> pre-shift metres (common.u2m) -> world = rigid (+20, -28) m. That is exactly what
post_shift_v85.shift_image did to the FINAL raster here: it samples the source at output - shift_m(output), and every Downtown output
point lies at y <= 470 m where shift_m = (20, -28). NOTE: common.u2w evaluates shift_m at the PRE-shift point, which differs inside the
gradient bands (Downtown north band: up to ~6 m off the drawn picture); this step uses the raster-consistent fixed point (pic_of_pre)
for verification and for the world-road ends. RIGID = False -> raster-consistent mapping per point (identical here).

Outputs: Data/<REV>/districts/downtown_v85.json (DISTRICT_SCHEMA.md), out_<REV>/check_downtown.png (preview x3),
out_<REV>/check_downtown_full.png (FINAL 5 px/m). Run: python s04_downtown.py (deterministic, ~20 s).

PLAN v37 (REV != v01; Map W86, agent A3, 2026-10-22; Vadim: "+ a row of blocks at the top and at the bottom, alleys 7 m, beach as it was ...
one-to-one from v85, only 54 m lower"). Only the picture exists (Working/Reviews/MapW86_Inputs_2026-10-22/downtown_plan_v37_vadim.webp,
1932 x 2000 px = the generator viewBox (-110, -330, 2570, 2660) in the SAME plan units as v31: px = (x + 110) * 0.75175, (y + 330) * 0.75188;
calibrated on the v31 polygons, street axes within 1 u). All v31 blocks are unchanged in v37 (v31 footprints overlay the picture 1:1);
the v31 stopper rows outside the ring (OB1, NEX) are replaced by full blocks. `make_plan_v37` rebuilds the plan as an SVG with Vadim's
v31 generator itself: v31 make_city (RNG sequence kept, OB1 / NEX rows dropped) + the new rows V37_ROWS (house splits / colours measured on
the picture) + V37_ST streets; this SVG (out_<REV>/plan_v37/) is then read exactly like the v31 SVG. v37 rules on top of v10 / Fedya 22.10:
alleys 7 m, houses 3-6 floors (neighbours differ, corners the 6s), office facade class, per-building separation spec (facade variant,
end pilasters, cornice break, setbacks, a few gaps), new entries (tunnel / VIEW B on the top ring, VIEW C on the top of E1, beach van entries
from the promenade street SP). Extra outputs: out_<REV>/downtown_v37_land.json (pad / land override / beach for the terrain),
Working/Reviews/MapW86_Downtown_2026-10-22/*.png (plan vs data overlay, floors top view).
"""
import colorsys
import json
import math
import os
import re

import numpy as np
from PIL import Image, ImageDraw

from common import (MAP_DIR, MAP_FULL, MAP_PREVIEW, REV, ROOT, WORK, apply, attr, ccw, h01, points_of, rnd2, save_json, shift_m,
                    svg_tags, svg_text, u2m, u2w)
from common import num as anum

Image.MAX_IMAGE_PIXELS = None
PLAN = 'v31' if REV == 'v01' else 'v37'
PLAN_DIR = os.path.join(MAP_DIR, 'Districts')
PLAN_SVG_V31 = os.path.join(PLAN_DIR, 'Город_Downtown_v31.svg')
PLAN_SVG = PLAN_SVG_V31 if PLAN == 'v31' else os.path.join(WORK, 'plan_v37', 'Город_Downtown_v37_recon.svg')
PLAN_PY = os.path.join(PLAN_DIR, 'build_gorod_v31.py')
PLAN_PNG = os.path.join(PLAN_DIR, 'Город_Downtown_v31.png')
WORLD_PY = os.path.join(MAP_DIR, 'make_downtown_world_v31.py')
V37_IMG = os.path.join(ROOT, 'Working', 'Reviews', 'MapW86_Inputs_2026-10-22', 'downtown_plan_v37_vadim.webp')
REPORT_DIR = os.path.join(ROOT, 'Working', 'Reviews', 'MapW86_Downtown_2026-10-22')
RIGID = True

U = 0.2                                   # m per plan unit ("1 ед. = 0,2 м")
CARR, WALK, CURB, CORNER_R = 12.0, 5.0, 0.15, 6.0      # v10 §6 city street; curb ~15 cm (v10 §4); corner radius for a van turn
HW = (CARR / 2 + WALK) / U                # 55 u: street axis -> facade line
CW = CARR / 2 / U                         # 30 u: street axis -> curb
ALLEY = (5.6 if PLAN == 'v31' else 7.0) / U   # v10 §4 dead ends 5.6 m; plan v37 / Fedya 22.10: 7 m
FLOOR_H, GROUND_H, PARAPET = 3.4, 4.4, 0.9
FL_MIN, FL_MAX = (5, 8) if PLAN == 'v31' else (3, 6)   # v10 §7.5: 5-8; Fedya 22.10 (plan v37): min 3, max 6, twin towers unchanged
H_SET = (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 20, 22, 30, 46, 70)
FIXES, QUESTIONS = [], []
PLANDATA = {}

BRICK_COLS = {'#A65A45', '#7E4436', '#B8735A', '#8C6A4F', '#7A5560'}
PALETTE = ('#A65A45', '#7E4436', '#B8735A', '#C9A35A', '#74805A', '#4F7D7A', '#5D7189', '#B98478', '#D9C9A8', '#BE9A72', '#A9A69C',
           '#4F6B55', '#B98B4E', '#7A5560', '#8C6A4F', '#9FB0A8')     # build_gorod_v31 HOUSE_COLS = v02 §8.5 city palette
AWNINGS = ('#3F5E4A', '#7A3B36', '#3E4C5E', '#A0603F', '#B08A3E', '#3A3D40', '#3F6E6A', '#D8CDB4', '#6B4E6A')
GROUND_FLOORS = ('storefront', 'cafe_terrace', 'office_lobby', 'stoop_doors', 'rollshutter_shop', 'plain_windows')
LEGEND = {
    '01': 'twin tower 1 (west): round faceted dark-blue glass, ~200 m / 55 floors, light crown on top, glass belt at podium level',
    '02': 'twin tower 2 (east): identical to 01',
    '35': 'big street screen on the podium between the towers, faces the plaza (Tramduro from app Z)',
    '03': 'underground parking under both towers: 1 level, 2 identical two-way ramps (from N2 and N3), van turns inside',
    '15': 'golden cartoon Tramduro monument (raised arm, no likeness) on a dark granite podium D 8.8 m, ring of 18 dry fountains R 9.2 m',
    '36': 'police booth at the monument', '08': 'ATM (one per district)',
    '16': 'glass pavilion ~18 x 10 m (cafe / shop), terrace with 3 yellow umbrellas', '17': 'glass pavilion with terrace',
    '18': 'glass pavilion with terrace', '19': 'glass pavilion with terrace',
    '04': 'plaza "Water Axis" (pedestrian, no trees): tribune stair + water cascade, mirror pool 16 x 60 m, monument, pavilions',
    '14': 'bus stop on the boulevard at the plaza', '23': 'square NW (trees only here and in 20)',
    '42': 'wide service yard, entry from Vb: concrete, bins, roll-shutter gate, bollards',
    '43': 'wide service yard, entry from Vd: concrete, bins, roll-shutter gate, bollards',
    '11': 'police 2 (NE)', '12': 'taxi depot with its own stand, exit onto Vd', '20': 'square with pond (NE)',
    '41': 'gas station at the west entry: canopy with 3 pump islands + shop', '10': 'police 1 (SW) with a rotunda on the corner',
    '07': 'van shop: rectangular, roll-shutter gates straight onto the street', '05': 'glass office south of the plaza',
    '06': 'glass office south of the plaza', '40': 'corner diner (chrome, red stripe)',
    '13': 'BASE 4 (plan no. 13): drive-through arch from Hse2 -> closed courtyard -> brick garage with roll shutter'}

# ---------------------------------------------------------------- plan v37 (picture only) in v31 plan units
V37_PX = (0.75175, 2000 / 2660.0)          # picture px per plan unit (x, y); px = (x + 110) kx, (y + 330) ky
V37_ST = {                                 # street axes measured on the picture (every axis within 1 u of these round values)
    'N0w': [(100, -150), (445, -150)],     # new top ring (52-60 m further north than v31 N1 / N2 / N3)
    'N0c': [(445, -190), (1550, -190)],
    'N0e': [(1550, -110), (2240, -110)],
    'W1': [(100, -150), (100, 760)],
    'W2': [(20, 760), (20, 1480)],
    'E1': [(2240, -110), (2240, 760)],
    'E2': [(2320, 760), (2320, 1480)],
    'SP': [(20, 1480), (2320, 1480)],      # new bottom ring = promenade street along the beach (v31 S1 moved 54 m south)
    'B': [(20, 760), (790, 760), (790, 860), (1550, 860), (1550, 760), (2320, 760)],
    'N1': [(100, 150), (445, 150)],        # v31 ring streets, now inner
    'N2': [(445, 70), (1170, 70)],
    'Nj': [(1170, 70), (1170, 150)],
    'N3': [(1170, 150), (1840, 150)],
    'N3b': [(1840, 330), (2240, 330)],
    'S1': [(20, 1210), (2320, 1210)],
    'Vn': [(445, -190), (445, 760)],
    'Vb': [(790, -190), (790, 760)],
    'Vc': [(1550, -190), (1550, 760)],
    'Vd': [(1840, -110), (1840, 760)],
    'Hnw': [(100, 455), (790, 455)],
    'Hne': [(1550, 455), (1840, 455)],
    'Hne2': [(1840, 545), (2240, 545)],
    'Vs1': [(320, 760), (320, 1210)],
    'Va2': [(620, 760), (620, 1210)],
    'Vs2': [(900, 860), (900, 1210)],
    'AX': [(1170, 860), (1170, 1210)],
    'Vs3': [(1505, 1030), (1505, 1210)],
    'Vds': [(1840, 960), (1840, 1210)],
    'Hsw': [(20, 990), (620, 990)],
    'Hse': [(1170, 1030), (1840, 1030)],
    'Hse2': [(1840, 960), (2320, 960)],
    'Vp1': [(470, 1210), (470, 1480)],     # promenade row: staggered against the grid above (T-joins on S1 and SP)
    'Vp2': [(760, 1210), (760, 1480)],
    'Vp3': [(1340, 1210), (1340, 1480)],
    'Vp4': [(2080, 1210), (2080, 1480)]}
V37_RING = ('N0w', 'N0c', 'N0e', 'W1', 'W2', 'E1', 'E2', 'SP')
V37_DISTRICT = [(100, -150), (445, -150), (445, -190), (1550, -190), (1550, -110), (2240, -110), (2240, 760), (2320, 760), (2320, 1480),
                (20, 1480), (20, 760), (100, 760)]
V37_BLOCKS = {                             # new blocks (facade lines = axis +- 55 u); all other blocks are the v31 ones
    'NW0': [(155, -95), (390, -95), (390, 95), (155, 95)], 'NC0': [(500, -135), (735, -135), (735, 15), (500, 15)],
    'NT0': [(845, -135), (1495, -135), (1495, 95), (1225, 95), (1225, 15), (845, 15)],
    'NE0': [(1605, -55), (1785, -55), (1785, 95), (1605, 95)], 'NEB': [(1895, -55), (2185, -55), (2185, 275), (1895, 275)],
    'SP1': [(75, 1265), (415, 1265), (415, 1425), (75, 1425)], 'SP2': [(525, 1265), (705, 1265), (705, 1425), (525, 1425)],
    'SP3': [(815, 1265), (1285, 1265), (1285, 1425), (815, 1425)], 'SP4': [(1395, 1265), (2025, 1265), (2025, 1425), (1395, 1425)],
    'SP5': [(2135, 1265), (2265, 1265), (2265, 1425), (2135, 1425)]}
V37_DROP_ROWS = {(1211, 12): 'OB1', (1881, 225): 'NEX', (1881, 105): 'NEX'}    # v31 rowfill calls outside the ring (old coords)
V37_ROWS = (    # (block, along axis, cross range, edges along the row, plan colours) - house splits measured on the picture
    ('NW0', 'x', (-95, -17.5), (155, 236, 313, 390), ('#9FB0A8', '#D9C9A8', '#B98478')),
    ('NW0', 'x', (17.5, 95), (155, 206, 274, 314.5, 390), ('#5D7189', '#9FB0A8', '#8C6A4F', '#D9C9A8')),
    ('NC0', 'x', (-135, -77.5), (500, 579.5, 651, 735), ('#BE9A72', '#5D7189', '#7E4436')),
    ('NC0', 'x', (-42.5, 15), (500, 549, 593.5, 662, 735), ('#74805A', '#4F6B55', '#8C6A4F', '#A9A69C')),
    ('NT0', 'x', (-135, -77.5), (845, 920.5, 975.5, 1048.5, 1089, 1135, 1192.5, 1243.5, 1320.5, 1396.5, 1495),
     ('#A65A45', '#4F7D7A', '#A65A45', '#4F6B55', '#8C6A4F', '#4F6B55', '#74805A', '#B98B4E', '#4F7D7A', '#7E4436')),
    ('NT0', 'x', (-42.5, 15), (845, 923, 995, 1050, 1093, 1141.5, 1225), ('#B98478', '#B8735A', '#C9A35A', '#4F6B55', '#74805A', '#9FB0A8')),
    ('NT0', 'x', (-42.5, 95), (1225, 1276, 1333.5, 1397, 1447.5, 1495), ('#B98478', '#A65A45', '#C9A35A', '#7E4436', '#A9A69C')),
    ('NE0', 'x', (-55, 2.5), (1605, 1689, 1785), ('#74805A', '#C9A35A')),
    ('NE0', 'x', (37.5, 95), (1605, 1678.5, 1749.5, 1785), ('#B8735A', '#BE9A72', '#D9C9A8')),
    ('NEB', 'y', (1895, 2022.5), (-55, 36.5, 105, 141, 202, 275), ('#B98478', '#4F6B55', '#A65A45', '#4F6B55', '#8C6A4F')),
    ('NEB', 'y', (2057.5, 2185), (-55, 5, 65.5, 139.5, 182, 224.5, 275), ('#A65A45', '#B8735A', '#4F6B55', '#9FB0A8', '#7E4436', '#7A5560')),
    ('SP1', 'x', (1265, 1327.5), (75, 150.5, 224.5, 289, 337, 415), ('#4F6B55', '#BE9A72', '#7A5560', '#B98B4E', '#8C6A4F')),
    ('SP1', 'x', (1362.5, 1425), (75, 136, 187.5, 265, 323.5, 376, 415), ('#9FB0A8', '#B98478', '#B8735A', '#8C6A4F', '#B98478', '#BE9A72')),
    ('SP2', 'x', (1265, 1345), (525, 611, 705), ('#4F6B55', '#A65A45')),
    ('SP2', 'x', (1345, 1425), (525, 595.5, 660, 705), ('#4F7D7A', '#B8735A', '#BE9A72')),
    ('SP3', 'x', (1265, 1327.5), (815, 906.5, 958, 1033.5, 1095, 1139, 1207, 1285),
     ('#8C6A4F', '#9FB0A8', '#A9A69C', '#4F6B55', '#74805A', '#7A5560', '#BE9A72')),
    ('SP3', 'x', (1362.5, 1425), (815, 884.5, 959.5, 1030, 1100, 1171.5, 1221.5, 1285),
     ('#D9C9A8', '#7E4436', '#9FB0A8', '#7A5560', '#C9A35A', '#4F7D7A', '#B98B4E')),
    ('SP4', 'x', (1265, 1345), (1395, 1491, 1535.5, 1582.5, 1632, 1696, 1755, 1797, 1835.5, 1897.5, 1947, 2025),
     ('#7A5560', '#BE9A72', '#4F6B55', '#BE9A72', '#74805A', '#A9A69C', '#9FB0A8', '#B98B4E', '#9FB0A8', '#B8735A', '#4F6B55')),
    ('SP4', 'x', (1345, 1425), (1395, 1469.5, 1539, 1589.5, 1634.5, 1680, 1721.5, 1764.5, 1827, 1893.5, 1933, 2025),
     ('#D9C9A8', '#4F6B55', '#B98478', '#BE9A72', '#5D7189', '#4F6B55', '#D9C9A8', '#B98B4E', '#7E4436', '#BE9A72', '#C9A35A')),
    ('SP5', 'x', (1265, 1345), (2135, 2195.5, 2265), ('#4F7D7A', '#4F6B55')),
    ('SP5', 'x', (1345, 1425), (2135, 2203.5, 2265), ('#A9A69C', '#D9C9A8')))
V37_ALLEYS = (  # (block, along axis, cross lo / hi, span lo / hi, open ends, plug along-range) - 7 m (35 u), measured on the picture
    ('NW0', 'x', -17.5, 17.5, 155, 390, ('lo',), (356, 390)),
    ('NC0', 'x', -77.5, -42.5, 500, 735, ('lo',), (701, 735)),
    ('NT0', 'x', -77.5, -42.5, 845, 1495, ('lo', 'hi'), (1150, 1190)),
    ('NE0', 'x', 2.5, 37.5, 1605, 1785, ('hi',), (1605, 1639)),
    ('NEB', 'y', 2022.5, 2057.5, -55, 275, ('lo', 'hi'), (98, 122)),
    ('SP1', 'x', 1327.5, 1362.5, 75, 415, ('lo',), (381, 415)),
    ('SP3', 'x', 1327.5, 1362.5, 815, 1285, ('lo',), (1251, 1285)))
V37_TANKS = ((1309.7, -121.1), (1444.4, -114.5), (539.1, -108.1), (1215.1, -103.1), (1368.7, -102.3), (1715.7, -41.8), (1930.6, -40.2),
             (522.8, -20.8), (1199.6, -19.4), (1417.8, -14.1), (952.7, -10.1), (561.9, -5.4), (239.2, 60.4), (375.6, 79.5), (2110.2, 172.6),
             (2002.0, 253.2), (1548.7, 1276.5), (89.9, 1279.3), (859.3, 1293.3), (1259.5, 1297.5), (362.2, 1300.6), (2011.3, 1310.3),
             (198.8, 1312.9), (660.0, 1312.0), (2182.7, 1327.8), (2189.4, 1359.5), (295.3, 1380.4), (228.5, 1381.0), (1209.2, 1381.0),
             (2243.6, 1382.4), (338.7, 1407.6), (1068.6, 1408.3), (998.7, 1412.7))
V37_FIRE = (    # fire escapes drawn on the picture: (facade axis, facade value, from, to, outward sign)
    ('y', -135, 585.7, 619.0, -1), ('y', -135, 658.9, 692.1, -1), ('y', -135, 1097.8, 1127.1, -1), ('y', -135, 1197.6, 1230.9, -1),
    ('y', -95, 161.4, 194.6, -1), ('x', 1895, -48.0, -16.1, -1), ('x', 2185, -48.0, -16.1, 1), ('y', 15, 1148.4, 1181.7, 1),
    ('y', 95, 1232.2, 1264.1, 1), ('y', 95, 1282.8, 1314.7, 1), ('x', 1895, 111.6, 132.8, -1), ('x', 1895, 147.5, 180.7, -1),
    ('x', 2185, 190.0, 215.3, 1), ('x', 1895, 208.6, 240.6, -1), ('x', 2185, 229.9, 261.8, 1), ('y', 1265, 154.7, 188.0, -1),
    ('y', 1265, 295.7, 325.0, -1), ('y', 1265, 343.6, 375.5, -1), ('y', 1265, 531.2, 564.4, -1), ('y', 1265, 1144.4, 1177.7, -1),
    ('y', 1265, 1405.1, 1434.4, -1), ('y', 1265, 1641.9, 1671.2, -1), ('y', 1265, 1701.8, 1733.7, -1), ('y', 1265, 2142.1, 2174.0, -1),
    ('y', 1265, 2203.3, 2236.5, -1), ('y', 1425, 531.2, 564.4, 1), ('y', 1425, 142.7, 176.0, 1), ('y', 1425, 666.9, 697.4, 1),
    ('y', 1425, 1038.0, 1071.2, 1), ('y', 1425, 1228.2, 1261.5, 1), ('y', 1425, 1898.6, 1923.9, 1))
# office buildings (facade class "office"): legend 05 / 06 + the business ring round the towers and the plaza (proposal, question to Vadim)
V37_OFFICE_FRONTS = ('Vb', 'Vc', 'Nj', 'N3', 'N2')       # houses whose MAIN frontage faces the plaza / towers across these streets
V37_OFFICE_RING = False                                   # Fedya 22.10 (item 11): offices ONLY 05 / 06; the business ring was the proposal
V37_BASE13_DEPTH_M = 12.0                                 # Fedya 22.10 (item 12): BASE 4 courtyard 12 m deep, the van turns inside
V37_GAP_PAIRS = {('05-H004', '05-H005'), ('05-H039', '05-H048'), ('05-H105', '05-H106'), ('05-H107', '05-H108'), ('05-H116', '05-H117'),
                 ('05-H118', '05-H119'), ('05-H177', '05-H178'), ('05-H228', '05-H229')}   # Fedya 22.10 (item 10): keep exactly these 8 gaps
V37_NEB_COURT = True                                      # Fedya 22.10 (item 9): NEB alley north end = gated courtyard + trimmed hedges
SEP_VARIANTS = ('A', 'B', 'C', 'D', 'E', 'F')            # facade rhythm variants (window bays / trim), neighbours always differ
OFFICE_FACADE = {'glass_ratio': 0.5, 'windows': 'large punched or ribbon, aligned in a grid, thin dark mullions, no balconies',
                 'spandrels': 'stone / fibre-cement panels between floors', 'frames': 'dark metal', 'ground_floor': 'glazed lobby 4.4 m',
                 'grade': 'better than the residential facades (bigger aligned windows, stone / metal), worse than the twin towers (no curtain wall); '
                          'NOT all glass (Fedya 22.10)', 'texture_focus': 'Downtown offices (sample sheet, Fedya edits)'}
V37_BEACH_LOTS = ((640.0, 810.0), (1875.0, 2045.0))   # beach parking lots (v85 LOTS pre 902-936 / 1149-1183 -> plan x)
V37_ENTRY_X = {'N-tunnel': 185.0, 'N-viewB': 1248.0, 'NE-viewC': 2040.0,   # plan x of the entry axes on the new rings (s02 bends the roads to them)
               'S-van-W': 605.0, 'S-van-E': 1840.0}                           # beach van entries = v85 beach x (VAN_IN 895 / 1142 pre-shift)


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def fix(where, ru, why):
    FIXES.append({'id': 'downtown-%02d' % (len(FIXES) + 1), 'where_plan': where, 'ru': ru, 'why_ru': why})


def question(ru, options, default, applied):
    QUESTIONS.append({'id': 'downtown-q%d' % (len(QUESTIONS) + 1), 'ru': ru, 'options_ru': options, 'default': default, 'applied': applied})


# ---------------------------------------------------------------- small plan-unit geometry (x east, y SOUTH)
def R(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def bb(pl):
    xs, ys = [p[0] for p in pl], [p[1] for p in pl]
    return (min(xs), min(ys), max(xs), max(ys))


def parea(pl):
    return abs(sum(pl[i - 1][0] * pl[i][1] - pl[i][0] * pl[i - 1][1] for i in range(len(pl)))) / 2.0


def pcen(pl):
    return (sum(p[0] for p in pl) / len(pl), sum(p[1] for p in pl) / len(pl))


def is_rect(pl):
    if len(pl) != 4:
        return False
    x0, y0, x1, y1 = bb(pl)
    return all((abs(p[0] - x0) < 0.05 or abs(p[0] - x1) < 0.05) and (abs(p[1] - y0) < 0.05 or abs(p[1] - y1) < 0.05) for p in pl)


def pin(pt, pl):
    c = False
    for i in range(len(pl)):
        (x0, y0), (x1, y1) = pl[i - 1], pl[i]
        if (y0 > pt[1]) != (y1 > pt[1]) and pt[0] < x0 + (pt[1] - y0) * (x1 - x0) / (y1 - y0):
            c = not c
    return c


def clip_axis(pl, ax, v, keep_le):
    out, n = [], len(pl)
    for i in range(n):
        a, b = pl[i], pl[(i + 1) % n]
        ia = a[ax] <= v + 1e-9 if keep_le else a[ax] >= v - 1e-9
        ib = b[ax] <= v + 1e-9 if keep_le else b[ax] >= v - 1e-9
        if ia:
            out.append(a)
        if ia != ib:
            t = (v - a[ax]) / (b[ax] - a[ax])
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    q = []
    for p in out:
        if not q or math.hypot(p[0] - q[-1][0], p[1] - q[-1][1]) > 1e-6:
            q.append(p)
    if len(q) > 1 and math.hypot(q[0][0] - q[-1][0], q[0][1] - q[-1][1]) < 1e-6:
        q.pop()
    return q


def clip_rect(pl, r):
    q = clip_axis(pl, 0, r[0], False)
    q = clip_axis(q, 0, r[2], True) if q else q
    q = clip_axis(q, 1, r[1], False) if q else q
    q = clip_axis(q, 1, r[3], True) if q else q
    return q


def overlap(a, b):
    return min(a[2], b[2]) - max(a[0], b[0]), min(a[3], b[3]) - max(a[1], b[1])


def circle_pts(c, r, n=24):
    return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def dedup_closed(pts):
    return pts[:-1] if len(pts) > 2 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 0.05 else pts


# ---------------------------------------------------------------- transform chain
def load_chain():
    img = None
    for nm, at, M, ids, s0, s1 in svg_tags(svg_text()):
        if nm == 'image' and 'downtown_v31_world.png' in (attr(at, 'href') or ''):
            img = {'M': M, 'x': anum(at, 'x'), 'y': anum(at, 'y'), 'w': anum(at, 'width'), 'h': anum(at, 'height'), 'group': ids[-1]}
    assert img, 'downtown_v31_world.png not found in the master SVG'
    plan = read(PLAN_SVG_V31)                                             # v37 uses the same plan-unit frame (calibrated)
    m = re.search(r'<svg[^>]*\swidth="([\d.]+)" height="([\d.]+)" viewBox="([^"]+)"', plan)
    pw, ph = float(m.group(1)), float(m.group(2))
    vb = [float(v) for v in m.group(3).split()]
    k = float(re.search(r'dt\.width / ([\d.]+)\)', read(WORLD_PY)).group(1))
    iw, ih = int(pw / k), int(ph / k)

    def master(p):
        return apply(img['M'], (img['x'] + (p[0] - vb[0]) * pw / vb[2] / k * img['w'] / iw,
                                img['y'] + (p[1] - vb[1]) * ph / vb[3] / k * img['h'] / ih))

    def pre(p):
        return u2m(*master(p))

    o, ex, ey = pre((0.0, 0.0)), pre((1000.0, 0.0)), pre((0.0, 1000.0))
    lin = (o[0], (ex[0] - o[0]) / 1000.0, o[1], (o[1] - ey[1]) / 1000.0)
    s_ref = shift_m(*pre((1170.0, 760.0)))                                # district body (plaza / boulevard)

    def W(p):
        if RIGID:
            q = pre(p)
            return (q[0] + s_ref[0], q[1] + s_ref[1])
        return pic_of_pre(pre(p))

    def Wpic(p):                                                          # what the v85 raster shows (post_shift_v85.shift_image)
        return pic_of_pre(pre(p))

    def Winv(q):                                                          # rigid inverse
        return ((q[0] - s_ref[0] - lin[0]) / lin[1], (lin[2] - (q[1] - s_ref[1])) / lin[3])

    info = {'img': img, 'vb': vb, 'pw': pw, 'ph': ph, 'k': k, 'iw': iw, 'ih': ih, 'lin': lin, 's_ref': s_ref,
            'master0': master((0.0, 0.0))}
    return W, Winv, Wpic, (lambda p: u2w(*master(p))), info


def pic_of_pre(p):
    """post_shift_v85.shift_image samples the source at output - shift_m(output): the drawn point q solves q = p + shift_m(q)
    (common.u2w evaluates shift_m at the pre-shift point instead -> off in the gradient bands)."""
    q = (p[0], p[1])
    for _ in range(60):
        dx, dy = shift_m(q[0], q[1])
        q = (p[0] + dx, p[1] + dy)
    return q


# ---------------------------------------------------------------- generator model (streets, blocks, shrink)
def gen_model():
    src = read(PLAN_PY)
    road, sw = map(float, re.search(r'^ROAD, SW = ([\d.]+), ([\d.]+)', src, re.M).groups())
    road0, sw0 = map(float, re.search(r'^ROAD_OLD, SW_OLD = ([\d.]+), ([\d.]+)', src, re.M).groups())
    axis = float(re.search(r'^AXIS = (\d+)', src, re.M).group(1))
    Hh = float(re.search(r'^W, H = \d+, (\d+)', src, re.M).group(1))
    assert abs(road * U - CARR) < 1e-6 and abs(sw * U - WALK) < 1e-6, 'plan street profile is not 12 + 2 x 5 m'
    tok = lambda t: axis if t == 'AXIS' else (Hh if t == 'H' else float(t))
    blk = src[src.index('ST = {'):src.index('\nCANAL')]
    st = {}
    for name, body, cap in re.findall(r"'(\w+)': St\(\[([^\]]*)\], ROAD, SW(?:, cap='(\w+)')?\)", blk):
        st[name] = {'pts': [(tok(a), tok(b)) for a, b in re.findall(r'\(([\w.]+), ([\w.]+)\)', body)], 'cap': cap or 'butt'}
    ring = re.findall(r"'(\w+)'", re.search(r'^RING = \(([^)]*)\)', src, re.M).group(1))
    d0 = src.index('DISTRICT = [')
    district = [(float(a), float(b)) for a, b in re.findall(r'\(([\d.]+), ([\d.]+)\)', src[d0:src.index(']', d0)])]
    b0 = src.index('BLK = {')
    ns = {'R': R}
    exec(src[b0:src.index('\n}', b0) + 2], ns)                            # the block literal only (rectangles / lists)
    shrink = (road / 2 + sw) - (road0 / 2 + sw0)
    blocks = {}
    for kname, pl in ns['BLK'].items():
        o = bb(pl)
        n = (o[0] + shrink, o[1] + shrink, o[2] - shrink, o[3] - shrink)
        sx, sy = (n[2] - n[0]) / (o[2] - o[0]), (n[3] - n[1]) / (o[3] - o[1])
        blocks[kname] = {'old': o, 'new': n, 'sx': sx, 'sy': sy,
                         'poly': [(n[0] + (p[0] - o[0]) * sx, n[1] + (p[1] - o[1]) * sy) for p in pl]}
    hw = road / 2 + sw
    for m_ in re.finditer(r'x0, x1, y0, y1 = (\d+) - hw, \d+ \+ hw, (\d+) \+ hw, (\d+) - hw', src):      # v28 rows on closed Vd / Vs3
        x, y0, y1 = float(m_.group(1)), float(m_.group(2)), float(m_.group(3))
        name = 'VDF' if x == 1840 else 'VSF'
        r_ = (x - hw, y0 + hw, x + hw, y1 - hw)
        blocks[name] = {'old': r_, 'new': r_, 'sx': 1.0, 'sy': 1.0, 'poly': R(*r_)}
    return {'st': st, 'ring': ring, 'district': district, 'blocks': blocks, 'shrink': shrink, 'axis': axis, 'H': Hh, 'road': road, 'sw': sw}


def blk_of(model, p, pad=0.6):
    for k, b in model['blocks'].items():
        n = b['new']
        if n[0] - pad <= p[0] <= n[2] + pad and n[1] - pad <= p[1] <= n[3] + pad:
            return k
    return None


# ---------------------------------------------------------------- plan v37: rebuild the SVG with Vadim's v31 generator + the measured new rows
def load_generator():
    src = read(PLAN_PY)
    ns = {'__name__': 'build_gorod_v31_for_v37', '__file__': PLAN_PY}
    exec(compile(src, PLAN_PY, 'exec'), ns)                               # module level only: ST / BLK / JUN, no files written
    return ns


def make_plan_v37():
    g = load_generator()
    orig_rowfill = g['rowfill']
    dropped = []

    def rowfill(x0, y0, x1, y1, street, *a, **kw):                        # v31 stopper rows outside the ring: run (keeps the RNG), drop output
        n = (len(g['BLD']), len(g['SHADOW']), len(g['SPEC']))
        orig_rowfill(x0, y0, x1, y1, street, *a, **kw)
        if (x0, y0) in V37_DROP_ROWS:
            dropped.append((V37_DROP_ROWS[(x0, y0)], len(g['BLD']) - n[0]))
            del g['BLD'][n[0]:], g['SHADOW'][n[1]:], g['SPEC'][n[2]:]
    g['rowfill'] = rowfill
    g['make_city_v28']()                                                  # v31 content = v37 content of the old blocks
    house, bld_ = g['house'], g['bld']
    corner_of = {}
    for blk, ax, (c0, c1), edges, cols in V37_ROWS:
        poly = V37_BLOCKS[blk]
        xs_, ys_ = [p[0] for p in poly], [p[1] for p in poly]
        for i, (a0, a1) in enumerate(zip(edges[:-1], edges[1:])):
            r_ = (a0, c0, a1, c1) if ax == 'x' else (c0, a0, c1, a1)
            on_x = any(abs(r_[0] - p[0]) < 0.6 or abs(r_[2] - p[0]) < 0.6 for p in poly)
            on_y = any(abs(r_[1] - p[1]) < 0.6 or abs(r_[3] - p[1]) < 0.6 for p in poly)
            corner = on_x and on_y and not (blk == 'NT0' and r_[3] <= 15.5 and abs(r_[2] - 1225) < 0.6)
            house(r_[0], r_[1], r_[2], r_[3], cols[i], h=18 if corner else 11)
            corner_of[tuple(round(v, 1) for v in r_)] = corner
    for blk, ax, c0, c1, s0, s1, ends, plug in V37_ALLEYS:
        R2 = (lambda a0, a1: R(a0, c0, a1, c1)) if ax == 'x' else (lambda a0, a1: R(c0, a0, c1, a1))
        house(*(bb(R2(plug[0], plug[1]))), '#8C6A4F', h=8)                # plug / end house (blind walls to the alley)
        parts = [(s0, plug[0]), (plug[1], s1)]
        for p0, p1 in parts:
            if p1 - p0 < 5:
                continue
            dead = []
            for v in (p0, p1):
                if abs(v - s0) > 0.5 and abs(v - s1) > 0.5:
                    dead = [(v, c0 - 2), (v, c1 + 2)] if ax == 'x' else [(c0 - 2, v), (c1 + 2, v)]
            g['alley'](R2(p0, p1), dead=dead or None)
        for e in ends:                                                    # curb drop across the sidewalk at the open end
            v = s0 if e == 'lo' else s1
            d0, d1 = (v - g['SW'] - 1, v) if e == 'lo' else (v, v + g['SW'] + 1)
            g['ALLEY_DW'].append(R2(d0, d1))
    for x, y in V37_TANKS:
        g['water_tower']((x, y))
    for ax, v, a0, a1, sgn in V37_FIRE:
        if ax == 'y':
            g['fire_escape']((a0, v), (a1, v), (0, sgn))
        else:
            g['fire_escape']((v, a0), (v, a1), (sgn, 0))
    # streets, blocks, district of v37
    g['ST'] = {k: g['St'](list(map(tuple, v)), g['ROAD'], g['SW'], cap='square') for k, v in V37_ST.items()}
    g['JUN'] = g['junctions']()
    g['DISTRICT'] = list(V37_DISTRICT)
    for k in ('OB1', 'NEX'):
        g['BLK'].pop(k, None)
    g['BLK'].update({k: list(v) for k, v in V37_BLOCKS.items()})
    g['CANAL'] = [(g['XMIN'], 3000), (g['XMAX'], 3000)]                   # no canal (v38); the beach is district 09 (s04_coast)
    g['H'] = 2330
    g['scatter_trees'] = lambda *a, **k: None
    g['make_city_v28'] = lambda: None                                     # content already made above
    svg = g['build']()
    svg = re.sub(r'<svg [^>]*>', '<svg xmlns="http://www.w3.org/2000/svg" width="1932" height="2000" viewBox="-110 -330 2570 2660">', svg, 1)
    svg = re.sub(r'<polyline points="[^"]*" fill="none" stroke="#5E5A50"[^>]*/>', '', svg)        # v31 bridge rails over the old canal
    svg = svg.replace('план v31 — улицы 12 м + тротуары 5 м, всё застроено', 'план v37 (реконструкция с картинки Вадима, A3 22.10)')
    path = PLAN_SVG
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(svg)
    return {'dropped_v31_rows': dropped, 'corner_houses_new': sum(1 for v in corner_of.values() if v), 'new_houses': len(corner_of)}


def gen_model_v37():
    m = gen_model()                                                       # v31 blocks (shrunk), road profile, axis
    m['st'] = {k: {'pts': [tuple(map(float, p)) for p in v], 'cap': 'square'} for k, v in V37_ST.items()}
    m['ring'] = list(V37_RING)
    m['district'] = [tuple(map(float, p)) for p in V37_DISTRICT]
    for k in ('OB1', 'NEX'):
        m['blocks'].pop(k)
    for k, pl in V37_BLOCKS.items():
        r_ = bb(pl)
        m['blocks'][k] = {'old': r_, 'new': r_, 'sx': 1.0, 'sy': 1.0, 'poly': [tuple(map(float, p)) for p in pl]}
    m['H'] = 1535.0
    return m


# ---------------------------------------------------------------- plan SVG elements
def plan_elements():
    s = read(PLAN_SVG)
    els = []
    for nm, at, M, ids, s0, s1 in svg_tags(s):
        e = {'tag': nm, 'g': ids[-1] if ids else '', 'fill': attr(at, 'fill'), 'stroke': attr(at, 'stroke'),
             'sw': float(attr(at, 'stroke-width') or 0), 'dash': attr(at, 'stroke-dasharray')}
        if nm == 'polygon':
            e['pts'] = dedup_closed(points_of(at))
        elif nm == 'polyline':
            e['pts'] = points_of(at)
        elif nm == 'circle':
            e['c'], e['r'] = (anum(at, 'cx'), anum(at, 'cy')), anum(at, 'r')
        elif nm == 'text':
            e['pos'], e['text'] = (anum(at, 'x'), anum(at, 'y') - 0.5), s[s1:s.index('</text>', s1)]
        els.append(e)
    return els


def sel(els, **kw):
    return [e for e in els if all((e.get(k) == v) if not callable(v) else v(e.get(k)) for k, v in kw.items())]


def match_buildings(els, model):
    """bld() writes SHADOW[i] = footprint + h * (0.55, 0.75) (both through the v28 block map) and BLD[i] = footprint; walk both."""
    bel = [e for e in els if e['g'] == 'buildings' and e['tag'] == 'polygon' and e['fill'] not in (None, 'none')]
    shs = sel(els, g='shadows', tag='polygon')
    out, j = [], 0
    for i, sh in enumerate(shs):
        S = sh['pts']
        for k in range(j, min(len(bel), j + 15)):
            B = bel[k]['pts']
            if len(B) != len(S):
                continue
            d = [(q[0] - p[0], q[1] - p[1]) for p, q in zip(B, S)]
            mx, my = sum(v[0] for v in d) / len(d), sum(v[1] for v in d) / len(d)
            if max(max(abs(v[0] - mx), abs(v[1] - my)) for v in d) > 0.45 or mx < 0.5 or my < 0.5:
                continue
            bk = blk_of(model, pcen(B), 0.0)
            sx, sy = (model['blocks'][bk]['sx'], model['blocks'][bk]['sy']) if bk else (1.0, 1.0)
            h = 0.5 * (mx / 0.55 / sx + my / 0.75 / sy)
            hs = min(H_SET, key=lambda v: abs(v - h))
            assert abs(hs - h) < 0.4, ('shadow height off the bld() classes', i, h)
            out.append({'pl': list(B), 'fill': bel[k]['fill'], 'stroke': bel[k]['stroke'], 'h': hs, 'block': bk, 'src_index': i})
            j = k + 1
            break
        else:
            raise SystemExit('shadow %d not matched to a building polygon' % i)
    assert len(out) == len(shs)
    return out


# ---------------------------------------------------------------- streets, bands, junctions
def street_model(model):
    st = {k: {'pts': list(v['pts']), 'cap': v['cap']} for k, v in model['st'].items()}
    ring = set(model['ring'])
    for n1 in list(st):                                                    # collinear duplicates (Vd runs 36 m on top of N3's bend)
        for n2 in list(st):
            if n1 == n2 or n2 in ring or n1 not in ring:
                continue
            for a, b in zip(st[n1]['pts'][:-1], st[n1]['pts'][1:]):
                p0, p1 = st[n2]['pts'][0], st[n2]['pts'][1]
                ax = 0 if abs(a[0] - b[0]) < 1e-6 else 1                    # 0: segment along y (x const)
                if abs(p0[ax] - p1[ax]) > 1e-6 or abs(p0[ax] - a[ax]) > 1e-6 or abs(a[ax] - b[ax]) > 1e-6:
                    continue
                lo, hi = sorted((a[1 - ax], b[1 - ax]))
                if abs(p0[1 - ax] - lo) < 1e-6 and hi < p1[1 - ax] and hi - lo > 1:
                    new0 = list(p0)
                    new0[1 - ax] = hi
                    st[n2]['pts'][0] = tuple(new0)
                    st[n2]['trimmed'] = (n1, (hi - lo) * U, tuple(p0), tuple(new0))
    for name in (('Va2', 'Vds') if PLAN == 'v31' else ()):               # continuation south of S1 = beach entries (see FIX)
        p = st[name]['pts']
        st[name]['pts'] = [p[0], (p[0][0], 1210.0)]
        st[name]['beyond_S1_plan'] = p[-1]
    return st


def street_bands(st):
    bands = []
    for name, s in st.items():
        pts = s['pts']
        n = len(pts) - 1
        for i, (a, b) in enumerate(zip(pts[:-1], pts[1:])):
            e0 = 0.0 if (i == 0 and s['cap'] == 'butt') else HW
            e1 = 0.0 if (i == n - 1 and s['cap'] == 'butt') else HW
            if abs(a[1] - b[1]) < 1e-6:
                lo, hi = (a[0] - e0, b[0] + e1) if a[0] < b[0] else (b[0] - e1, a[0] + e0)
                bands.append({'street': name, 'rect': (lo, a[1] - HW, hi, a[1] + HW), 'ax': 1, 'axis': a[1], 'seg': (a, b)})
            else:
                lo, hi = (a[1] - e0, b[1] + e1) if a[1] < b[1] else (b[1] - e1, a[1] + e0)
                bands.append({'street': name, 'rect': (a[0] - HW, lo, a[0] + HW, hi), 'ax': 0, 'axis': a[0], 'seg': (a, b)})
    return bands


def seg_inter(a, b, c, d):
    r, s = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1])
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-9:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    if -1e-6 <= t <= 1 + 1e-6 and -1e-6 <= u <= 1 + 1e-6:
        return (a[0] + r[0] * t, a[1] + r[1] * t)
    return None


def legs(st, name, j):
    out = []
    for a, b in zip(st[name]['pts'][:-1], st[name]['pts'][1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        t = (j[0] - a[0]) * u[0] + (j[1] - a[1]) * u[1]
        if t < -1.5 or t > L + 1.5 or abs((j[0] - a[0]) * u[1] - (j[1] - a[1]) * u[0]) > 1.5:
            continue
        if L - t > 1.5:
            out.append((u, L - t))
        if t > 1.5:
            out.append(((-u[0], -u[1]), t))
    uniq = []
    for v, L in out:
        if all(v[0] * w[0] + v[1] * w[1] < 0.995 for w, _ in uniq):
            uniq.append((v, L))
    return uniq


def junctions(st):
    out = []
    names = list(st)
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            for a, b in zip(st[n1]['pts'][:-1], st[n1]['pts'][1:]):
                for c, d in zip(st[n2]['pts'][:-1], st[n2]['pts'][1:]):
                    p = seg_inter(a, b, c, d)
                    if p is None:
                        continue
                    for jj in out:
                        if math.hypot(jj[0][0] - p[0], jj[0][1] - p[1]) < 3:
                            jj[1].update((n1, n2))
                            break
                    else:
                        out.append((p, {n1, n2}))
    for p0, n0 in [(p, {n}) for n, s in st.items() for p in s['pts'][1:-1]]:                # bends of one street
        if not any(math.hypot(jj[0][0] - p0[0], jj[0][1] - p0[1]) < 3 for jj in out):
            out.append((p0, n0))
    return out


# ---------------------------------------------------------------- colours
def calm_bright(col, key):
    """v10 §7.5: brighter and more 'American' but not acid: HLS lightness +0.05, saturation x1.08 capped at 0.55, small per-house jitter."""
    r_, g_, b_ = [int(col[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    h, l, s = colorsys.rgb_to_hls(r_, g_, b_)
    h = (h + (h01(key + 'hue') - 0.5) * 0.03) % 1.0
    l = min(0.80, max(0.30, l + 0.05 + (h01(key + 'l') - 0.5) * 0.05))
    s = min(0.55, s * 1.08)
    return '#%02X%02X%02X' % tuple(int(round(c * 255)) for c in colorsys.hls_to_rgb(h, l, s))


# ---------------------------------------------------------------- plan v37: floors 3-6, offices, separation between buildings
def street_faces(pl, bands):
    """Faces of a rectangular footprint that stand on a street facade line: (street, band axis, face value, outward sign, along lo, hi)."""
    r_ = bb(pl)
    out = []
    for bd in bands:
        ax = bd['ax']                                                      # 1 = street along x (axis y const), 0 = along y
        lo_, hi_ = bd['rect'][1 - ax] + HW * 0.5, bd['rect'][3 - ax] - HW * 0.5
        if min(r_[3 - ax], hi_) - max(r_[1 - ax], lo_) < 4:
            continue
        for face, sgn in ((r_[ax], -1), (r_[ax + 2], 1)):
            if abs(face + sgn * HW - bd['axis']) < 1.5:
                out.append((bd['street'], ax, face, sgn, max(r_[1 - ax], lo_), min(r_[3 - ax], hi_)))
    return out


def v37_floors_offices_separation(blds, byid, adj, bands, model):
    """Fedya 22.10 / Vadim v37: ordinary houses 3-6 floors, neighbours always differ (no runs of one height), corners and the business ring
    the 6s; office facade class for 05 / 06 + the houses facing the plaza / towers across a street; a separation spec on every row building
    (facade variant, end pilasters, corner trim, cornice break, plinth, setback) and a few real 1.5-2.5 m gaps in long rows."""
    sq = model['blocks']['SQ']['poly']
    rowk = ('house', 'arch_house', 'loft', 'alley_plug')
    for b in blds:
        fs = street_faces(b['pl'], bands) if is_rect(b['pl']) else []
        b['faces37'] = fs
        b['corner37'] = b['kind'] in ('house', 'arch_house') and len({f[1] for f in fs}) >= 2
        plaza = []
        for st_, ax, face, sgn, lo_, hi_ in fs:
            q = [0.0, 0.0]
            q[ax], q[1 - ax] = face + sgn * (2 * HW + 10), (lo_ + hi_) / 2
            if pin(tuple(q), sq):
                plaza.append(st_)
        b['office37'] = b['kind'] == 'glass_office' or (V37_OFFICE_RING and b['kind'] == 'house' and bool(plaza))
        b['office_front37'] = sorted(set(plaza))
    for b in blds:                                                         # floors (ordinary houses only; specials keep their own)
        if b['kind'] not in ('house', 'arch_house'):
            continue
        if b['office37'] or b['corner37']:
            pref = [6, 5, 4] if h01(b['id'] + 'c6') < 0.6 else [5, 6, 4]
        else:
            base = 3 + int(h01(b['id'] + 'fl') * 3 - 1e-9)
            pref = sorted((3, 4, 5), key=lambda f: (abs(f - base), h01(b['id'] + str(f)))) + [6]
        taken = {byid[n].get('floors') for n in adj[b['id']]}
        b['fl_range'] = (FL_MIN, FL_MAX)
        b['floors'] = next((f for f in pref if f not in taken), pref[0])
    for it in range(4):                                                    # neighbours never equal (where 3-6 allows)
        bad = 0
        for b in blds:
            if 'fl_range' in b and any(byid[n].get('floors') == b['floors'] for n in adj[b['id']]):
                alt = [f for f in range(FL_MIN, FL_MAX + 1) if all(byid[n].get('floors') != f for n in adj[b['id']])]
                if alt:
                    b['floors'] = min(alt, key=lambda f: (abs(f - b['floors']), -f))
                bad += 1
        if not bad:
            break
    for b in blds:                                                         # 05 / 06: office, max 6 floors
        if b['kind'] == 'glass_office':
            b['floors'] = 6
    # separation spec: facade variant (neighbours differ), pilasters, corner trim, cornice profile (neighbours differ), plinth, setback
    prof = ('flat_band', 'stepped', 'dentil', 'metal_cap', 'brick_corbel')
    for b in sorted(blds, key=lambda b: b['id']):
        if b['kind'] not in rowk + ('glass_office',):
            continue
        used_v = {byid[n].get('sep', {}).get('facade_variant') for n in adj[b['id']]}
        used_c = {byid[n].get('sep', {}).get('cornice', {}).get('profile') for n in adj[b['id']]}
        var = next(v for v in sorted(SEP_VARIANTS, key=lambda v: h01(b['id'] + 'v' + v)) if v not in used_v)
        cp = next((c for c in sorted(prof, key=lambda c: h01(b['id'] + 'p' + c)) if c not in used_c), prof[0])
        hs = h01(b['id'] + 'sep')
        sep = {'facade_variant': var,
               'end_pilasters': {'w_m': round(0.35 + 0.3 * hs, 2), 'proud_m': 0.12, 'tone': ('lighter', 'darker', 'stone')[int(hs * 3 - 1e-9)],
                                 'where': 'both ends of every street / alley facade (at the party walls)'},
               'corner_trim': 'quoins' if b.get('corner37') else None,
               'cornice': {'profile': cp, 'h_m': round(0.45 + 0.4 * h01(b['id'] + 'ch'), 2), 'proud_m': round(0.2 + 0.25 * h01(b['id'] + 'cp'), 2)},
               'cornice_break': True,
               'plinth': {'h_m': round(0.5 + 0.4 * h01(b['id'] + 'pl'), 2), 'material': 'stone' if h01(b['id'] + 'pm') < 0.5 else 'dark_paint'},
               'party_wall_joint': {'w_m': 0.25, 'depth_m': 0.12, 'downpipe': h01(b['id'] + 'dp') < 0.6},
               'setback_m': 0.0}
        if b['kind'] == 'house' and not b.get('corner37') and not b.get('office37') and h01(b['id'] + 'sb') < 0.35:
            sep['setback_m'] = (0.3, 0.45, 0.6)[int(h01(b['id'] + 'sv') * 3 - 1e-9)]
        b['sep'] = sep
    # real gaps 1.5-2.5 m between two ordinary mid-row houses: at most one per row of >= 5 houses, never next to a corner / office
    rows = {}
    for b in blds:
        if b['kind'] != 'house' or b.get('corner37') or b.get('office37') or not b['faces37'] or b.get('no_gap'):
            continue
        for st_, ax, face, sgn, lo_, hi_ in b['faces37']:
            rows.setdefault((st_, ax, round(face, 1)), []).append(b)
    gaps = []
    taken_ids = set()
    for key, mem in sorted(rows.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        st_, ax, face = key
        allrow = [o for o in blds if any(f[0] == st_ and f[1] == ax and abs(f[2] - face) < 0.6 for f in o.get('faces37', []))]
        if len(allrow) < 5:
            continue
        cands = []
        along = 1 - ax                                                     # row direction index (0 = x)
        for a in mem:
            for n_id in adj[a['id']]:
                o = byid[n_id]
                if o not in mem or a['id'] > o['id'] or o.get('no_gap'):
                    continue
                ra, ro = bb(a['pl']), bb(o['pl'])
                if not (abs(ra[along + 2] - ro[along]) < 0.6 or abs(ro[along + 2] - ra[along]) < 0.6):
                    continue                                               # not side by side along the street
                first, second = (a, o) if ra[along] < ro[along] else (o, a)
                wide = max((first, second), key=lambda x: bb(x['pl'])[along + 2] - bb(x['pl'])[along])
                if bb(wide['pl'])[along + 2] - bb(wide['pl'])[along] < 70 or {first['id'], second['id']} & taken_ids:
                    continue
                if V37_GAP_PAIRS and (first['id'], second['id']) not in V37_GAP_PAIRS:
                    continue
                cands.append((h01(first['id'] + second['id'] + 'gap'), first['id'], first, second, wide))
        if not cands:
            continue
        hsh, _, first, second, wide = min(cands, key=lambda c: (c[0], c[1]))
        g = round(1.5 + h01(first['id'] + 'gw') * 1.0, 1) / U               # 1.5-2.5 m
        r_ = list(bb(wide['pl']))
        gap_r = [0.0, 0.0, 0.0, 0.0]
        if wide is first:
            r_[along + 2] -= g
            gap_r[along], gap_r[along + 2] = r_[along + 2], bb(second['pl'])[along]
        else:
            r_[along] += g
            gap_r[along], gap_r[along + 2] = bb(first['pl'])[along + 2], r_[along]
        rf, rs = bb(first['pl']), bb(second['pl'])
        gap_r[1 - along], gap_r[3 - along] = max(rf[1 - along], rs[1 - along]), min(rf[3 - along], rs[3 - along])
        wide['pl'] = R(*r_)
        taken_ids |= {first['id'], second['id']}
        gaps.append({'between': [first['id'], second['id']], 'street': st_, 'w_m': round(g * U, 1), 'rect': tuple(gap_r), 'shortened': wide['id']})
        first['sep']['gap_after'] = {'m': round(g * U, 1), 'to': second['id'], 'closure': 'iron gate 2.2 m at the facade line; blind wall / alley at the back'}
    return gaps


# ---------------------------------------------------------------- build
def build():
    W, Winv, Wpic, Wu2w, info = load_chain()
    recon = make_plan_v37() if PLAN == 'v37' else None
    model = gen_model() if PLAN == 'v31' else gen_model_v37()
    st = street_model(model)
    els = plan_elements()
    svg_ax = [e['pts'] for e in sel(els, g='roads', tag='polyline', stroke='#5F666C', sw=60.0)]
    assert len(svg_ax) == len(model['st']) and all(
        len(a) == len(s['pts']) and all(abs(p[0] - q[0]) < 0.06 and abs(p[1] - q[1]) < 0.06 for p, q in zip(a, s['pts']))
        for a, s in zip(svg_ax, model['st'].values())), 'SVG asphalt != generator ST'
    bands = street_bands(st)
    for name, s_ in st.items():
        if 'trimmed' in s_:
            n1, L, p0, p1 = s_['trimmed']
            fix(p1, 'Улица %s на плане первые %.0f м идёт поверх %s (одна и та же ось) — в данных этот кусок один раз (%s), %s начинается от угла %s буквой Т.'
                % (name, L, n1, n1, name, n1), 'v10 §6: накладывающиеся полосы — это не перекрёсток; покрытие сплошное, без двойного полотна.')
    labels = {e['text']: e['pos'] for e in sel(els, g='numbers', tag='text')}
    WL = lambda pl: [rnd2(W(p)) for p in pl]

    # ------------------------------------------------ buildings: match + classify
    blds = match_buildings(els, model)
    arch_el = sel(els, g='buildings', tag='polygon', fill='none', stroke='#6E6A60')[0]['pts']
    loft_lines = sel(els, g='buildings', tag='polyline', stroke='#C9A58F')
    gas_lot = sel(els, g='squares_and_lots', fill='#C9CCCB')[0]['pts']
    special = {'#2E4E73': 'tower', '#B7C7D4': 'podium', '#A9C4D3': 'pavilion', '#3F6C99': 'tower_round', '#A7BED2': 'podium_round',
               '#4C78A3': 'glass_office', '#E2DCCC': 'classical', '#B9C8E6': 'police', '#E5D5A0': 'taxi_depot', '#E3A982': 'van_shop',
               '#D7DDE1': 'diner'}
    for b in blds:
        b['pl0'] = list(b['pl'])
        pl, f, h = b['pl'], b['fill'], b['h']
        kind = special.get(f, 'house')
        if kind == 'house':
            if h == 8:
                kind = 'alley_plug'
            elif h == 12 and f == '#B8735A':
                kind = 'base_garage'
            elif h == 6 and pin(pcen(pl), gas_lot):
                kind = 'gas_shop'
            elif h == 6:
                kind = 'podium_annex'
            elif all(bb(pl)[i] - 0.5 <= bb(arch_el)[i] for i in (0, 1)) and all(bb(arch_el)[i] <= bb(pl)[i] + 0.5 for i in (2, 3)):
                kind = 'arch_house'
            elif h == 11 and sum(1 for e in loft_lines if pin(pcen(e['pts']), pl)) >= 3:
                kind = 'loft'
        b['kind'] = kind
        b['label'] = next((k for k, p in labels.items() if pin(p, pl) and k not in ('04', '03')), None)
    kind_labels = {'diner': ('40',), 'police': ('10', '11'), 'glass_office': ('05', '06'), 'pavilion': ('16', '17', '18', '19'), 'van_shop': ('07',),
                   'taxi_depot': ('12',), 'tower': ('01', '02'), 'gas_shop': ('41',), 'base_garage': ('13',)}
    for b in blds:                                                         # labels drawn next to (not on) their building
        if b['label'] is None and b['kind'] in kind_labels:
            c = pcen(b['pl'])
            b['label'] = min(kind_labels[b['kind']], key=lambda k: math.hypot(labels[k][0] - c[0], labels[k][1] - c[1]))
    if PLAN == 'v37':                                                      # owner decision 21.10 (Fedya, s04z in v01): only the twins are high-rise
        pod = next(b for b in blds if b['kind'] == 'podium_round')
        blds = [b for b in blds if b['kind'] != 'tower_round']
        pod['pl'], pod['kind'], pod['h'], pod['fill'] = R(*bb(pod['pl'])), 'house', 18, '#BE9A72'
        fix(pcen(pod['pl']), 'Решение Феди 21.10 (в W85 — шаг s04z): небоскрёбов только два (близнецы). Круглая стеклянная угловая башня легенды у двора 43 '
                             'и её подиум заменены обычным угловым домом на контуре подиума (%.1f x %.1f м), этажность по правилу v37 (3-6, угол).'
            % ((bb(pod['pl'])[2] - bb(pod['pl'])[0]) * U, (bb(pod['pl'])[3] - bb(pod['pl'])[1]) * U),
            'Вопрос Вадиму из W85 остаётся: вернуть ли башню (легенда §6).')
    # rotunda of police 1: a plain circle in BLD (no bld() -> no shadow)
    rot = [e for e in sel(els, g='buildings', tag='circle', fill='#B9C8E6')]
    for e in rot:
        blds.append({'pl': circle_pts(e['c'], e['r'], 20), 'pl0': circle_pts(e['c'], e['r'], 20), 'fill': e['fill'], 'stroke': e['stroke'], 'h': 10,
                     'block': blk_of(model, e['c']),
                     'kind': 'police_rotunda', 'label': '10', 'src_index': None})
    # stable ids: sort by plan position (north -> south, west -> east)
    order = sorted(range(len(blds)), key=lambda i: (round(pcen(blds[i]['pl'])[1] / 10), pcen(blds[i]['pl'])[0]))
    blds = [blds[i] for i in order]
    k_house = 0
    for b in blds:
        if b['kind'] in ('tower',):
            b['id'] = '05-' + ('01' if pcen(b['pl'])[0] < model['axis'] else '02')
        elif b['kind'] in ('glass_office', 'police', 'taxi_depot', 'van_shop', 'diner', 'pavilion', 'gas_shop') and b['label']:
            b['id'] = '05-' + b['label']
        elif b['kind'] == 'police_rotunda':
            b['id'] = '05-10r'
        else:
            b['id'] = ('05-B%03d' if PLAN == 'v31' else '05-H%03d') % k_house   # v37: new numbering (H) - v01 ids / s04z keys never collide
            k_house += 1
    byid = {b['id']: b for b in blds}

    # ------------------------------------------------ FIX 1: houses inside the 22 m street profile (v28 shrink at L-block inner corners)
    moves = []
    for it in range(3):
        changed = False
        for b in blds:
            for bd in bands:
                ox, oy = overlap(bb(b['pl']), bd['rect'])
                if min(ox, oy) <= 0.5:
                    continue
                ax = 0 if ox < oy else 1
                c = pcen(b['pl'])
                bc = ((bd['rect'][0] + bd['rect'][2]) / 2, (bd['rect'][1] + bd['rect'][3]) / 2)
                le = c[ax] < bc[ax]
                v = bd['rect'][ax] if le else bd['rect'][ax + 2]
                old = bb(b['pl'])[ax + 2] if le else bb(b['pl'])[ax]
                if len(b['pl']) > 8:                                       # round towers / rotunda: move, never cut a circle
                    dv = v - old
                    group_ = [t for t in blds if t['kind'] == 'tower'] if b['kind'] == 'tower' else [b]   # twins stay identical
                    for t in group_:
                        t['pl'] = [(q[0] + (dv if ax == 0 else 0.0), q[1] + (dv if ax == 1 else 0.0)) for q in t['pl']]
                    moves.append({'id': b['id'], 'ax': ax, 'le': le, 'old': old, 'new': v, 'street': bd['street'], 'depth_m': min(ox, oy) * U,
                                  'cross': None, 'moved': [t['id'] for t in group_]})
                    changed = True
                    continue
                b['pl'] = clip_axis(b['pl'], ax, v, le)
                moves.append({'id': b['id'], 'ax': ax, 'le': le, 'old': old, 'new': v, 'street': bd['street'], 'depth_m': min(ox, oy) * U,
                              'cross': (bb(b['pl'])[1 - ax], bb(b['pl'])[3 - ax])})
                changed = True
        if not changed:
            break
    prop = []
    for mv in list(moves):                                                # neighbours that shared the moved wall follow it (no slit)
        if mv['cross'] is None:
            continue
        for n in blds:
            if n['id'] == mv['id'] or not is_rect(n['pl']):
                continue
            nb = bb(n['pl'])
            face = nb[mv['ax']] if mv['le'] else nb[mv['ax'] + 2]          # neighbour's opposite face
            lo, hi = nb[1 - mv['ax']], nb[3 - mv['ax']]
            if abs(face - mv['old']) > 0.6 or min(hi, mv['cross'][1]) - max(lo, mv['cross'][0]) < 1.0:
                continue
            q = list(nb)
            if mv['le']:
                q[mv['ax']] = mv['new']
            else:
                q[mv['ax'] + 2] = mv['new']
            if any(min(overlap(q, bd['rect'])) > 0.5 for bd in bands):
                continue
            n['pl'] = R(*q)
            prop.append((n['id'], mv['id'], abs(mv['new'] - mv['old']) * U))
    by_street, by_round = {}, {}
    for mv in moves:
        if mv['cross'] is None:
            by_round.setdefault(mv['id'], []).append(mv)
        else:
            by_street.setdefault(mv['street'], []).append(mv)
    for bid_, mvs in sorted(by_round.items()):
        moved = sorted({t for m_ in mvs for t in m_['moved']})
        fix(rnd2(pcen(byid[bid_]['pl'])),
            'Круглое здание %s (%s) заходило на тротуар %s (%s м) — сдвинуто целиком внутрь квартала, форма и размер как на плане%s.'
            % (bid_, byid[bid_]['kind'], '/'.join(m_['street'] for m_ in mvs), '/'.join('%.1f' % m_['depth_m'] for m_ in mvs),
               '; обе башни-близнеца (%s) сдвинуты одинаково' % ', '.join(moved) if len(moved) > 1 else ''),
            'Тротуар 5 м (v10 §6); круглую башню / ротонду нельзя срезать прямой линией.')
    for sname, mvs in sorted(by_street.items()):
        ids = sorted({m_['id'] for m_ in mvs})
        kinds = sorted({byid[i]['kind'] for i in ids})
        dmax = max(m_['depth_m'] for m_ in mvs)
        fix(rnd2(pcen(byid[ids[0]]['pl'])),
            'Улица %s: %d дом(а) (%s) заходили на тротуар до %.1f м — фасад отодвинут на линию 22-метрового профиля (%s)%s.'
            % (sname, len(ids), ', '.join(kinds), dmax, ', '.join(ids),
               '; соседний дом дотянут до новой стены, чтобы не было щели' if any(p[1] in ids for p in prop) else ''),
            'План v28–v31 ужал кварталы на 2,75 м с каждой стороны, но внутренние углы Г-образных кварталов (07/SC1, SE2 у залома бульвара, '
            'площадь у Nj) не сдвинулись — тротуар там 1–3 м вместо 5 м (v10 §6: 12 + 2 × 5 м = 22 м между фасадами).')

    # ------------------------------------------------ FIX 2: dead-end alleys back to 5.6 m (v10 §4)
    alley_els = sel(els, g='squares_and_lots', tag='polygon', fill='#9DA2A2')
    dws = [e['pts'] for e in sel(els, g='roads', tag='polygon', fill='#9DA2A2')]
    dead_lines = [e['pts'] for e in sel(els, g='buildings', tag='polyline', stroke='#3C3A36')]
    plugs = [b for b in blds if b['kind'] == 'alley_plug']
    alleys = []
    for e in alley_els:
        r_ = bb(e['pts'])
        horiz = (r_[2] - r_[0]) > (r_[3] - r_[1])
        ax_c = 1 if horiz else 0                                           # cross axis
        c = (r_[ax_c] + r_[ax_c + 2]) / 2
        w0 = r_[ax_c + 2] - r_[ax_c]
        alleys.append({'rect0': r_, 'horiz': horiz, 'cax': ax_c, 'c': c, 'w0': w0})
    groups = []                                                            # alleys on one line (pair with a plug) -> one group
    for a in alleys:
        for g in groups:
            if g[0]['horiz'] == a['horiz'] and abs(g[0]['c'] - a['c']) < 1.0 and blk_of(model, pcen(R(*g[0]['rect0']))) == blk_of(model, pcen(R(*a['rect0']))):
                g.append(a)
                break
        else:
            groups.append([a])
    alley_out = []
    for gi, g in enumerate(groups):
        a0 = g[0]
        cax, c = a0['cax'], a0['c']
        aax = 1 - cax
        lo, hi = c - ALLEY / 2, c + ALLEY / 2
        blk = blk_of(model, pcen(R(*a0['rect0'])))
        bnew = model['blocks'][blk]['new']
        span = (bnew[aax], bnew[aax + 2])
        rects = []
        for a in g:
            q = list(a['rect0'])
            q[cax], q[cax + 2] = lo, hi
            a['rect'] = tuple(q)
            rects.append(a['rect'])
        g_plugs = [p for p in plugs if blk_of(model, pcen(p['pl'])) == blk and abs(pcen(p['pl'])[cax] - c) < 3]
        for p in g_plugs:
            q = list(bb(p['pl']))
            q[cax], q[cax + 2] = lo, hi
            p['pl'] = R(*q)
        whole = [0, 0, 0, 0]
        whole[cax], whole[cax + 2], whole[aax], whole[aax + 2] = lo, hi, span[0], span[1]
        moved = 0
        for b in blds:
            if b in g_plugs or b['kind'] != 'house' and b['kind'] not in ('arch_house', 'loft'):
                continue
            ox, oy = overlap(bb(b['pl']), whole)
            if min(ox, oy) <= 0.05:
                continue
            le = pcen(b['pl'])[cax] < c
            b['pl'] = clip_axis(b['pl'], cax, lo if le else hi, le)
            moved += 1
        for i, d in enumerate(dws):                                       # curb drops at the alley mouths follow
            dr = bb(d)
            if abs((dr[cax] + dr[cax + 2]) / 2 - c) < 1.0 and blk_of(model, pcen(d), 30.0) == blk:
                q = list(dr)
                q[cax], q[cax + 2] = lo, hi
                dws[i] = R(*q)
        mouths = []
        for a in g:
            r_ = a['rect']
            for end in (0, 1):
                v = r_[aax] if end == 0 else r_[aax + 2]
                if abs(v - span[end]) < 0.6:                              # open end at the block edge
                    p = [0, 0]
                    p[aax], p[cax] = v, c
                    mouths.append({'pos': tuple(p), 'dir': (-1 if end == 0 else 1), 'rect': r_})
        alley_out.append({'id': '05-alley-%s' % blk, 'block': blk, 'cax': cax, 'aax': aax, 'c': c, 'lo': lo, 'hi': hi, 'rects': rects,
                          'plugs': g_plugs, 'mouths': mouths, 'w0_m': min(a['w0'] for a in g) * U, 'houses_trimmed': moved,
                          'pair': len(g) == 2, 'span': span})
    narrow = [a for a in alley_out if a['w0_m'] < ALLEY * U - 0.05]
    fix(None, 'Глухие переулки (%s) были %.1f–%.1f м — расширены до %.1f м: задние стены домов вдоль переулка отодвинуты на %.2f–%.2f м, '
              'затычки и торцевые дома растянуты на всю ширину.' % (', '.join(sorted(a['block'] for a in narrow)),
                                                                      min(a['w0_m'] for a in narrow), max(a['w0_m'] for a in narrow), ALLEY * U,
                                                                      min((ALLEY * U - a['w0_m']) / 2 for a in narrow), max((ALLEY * U - a['w0_m']) / 2 for a in narrow)),
        'План v28 ужал кварталы вместе с переулками (5,6 м -> 4,5–5,0 м); v10 §4: тупик 5,6 м, чтобы бусик заехал и выехал задом' +
        ('' if PLAN == 'v31' else '; план v37 / Федя 22.10: переулки 7 м (новые ряды v37 нарисованы 7 м, старые кварталы расширены так же)') + '.')

    # ------------------------------------------------ FIX 3: slits 0.1-1.8 m between back-to-back buildings (v02 §8.5 "Не: щели между домами")
    court13 = None
    for e in sel(els, g='squares_and_lots', tag='polygon', fill='#D8D4CA'):
        if pin(labels['13'], e['pts']):
            court13 = bb(clip_axis(e['pts'], 1, bb(arch_el)[3], False))
    movable = ('house', 'arch_house', 'loft', 'base_garage', 'classical')
    pref = {'house': 0, 'arch_house': 1, 'loft': 1, 'base_garage': 2, 'classical': 3}
    slits = []
    for it in range(2):
        rects = [(b, bb(b['pl'])) for b in blds] + [(None, court13)]
        for i, (A, ra) in enumerate(rects):
            for B, rb in rects[i + 1:]:
                for ax in (0, 1):
                    lo, hi = max(ra[1 - ax], rb[1 - ax]), min(ra[3 - ax], rb[3 - ax])
                    if hi - lo < 10:
                        continue
                    if rb[ax] - ra[ax + 2] > 0:
                        first, second, rf, rs = A, B, ra, rb
                    elif ra[ax] - rb[ax + 2] > 0:
                        first, second, rf, rs = B, A, rb, ra
                    else:
                        continue
                    g = rs[ax] - rf[ax + 2]
                    if not 0.5 <= g <= 9.0:
                        continue
                    cand = [x for x in (second, first) if x is not None and x['kind'] in movable and is_rect(x['pl'])]
                    if not cand:
                        continue
                    mv = min(cand, key=lambda x: (pref[x['kind']], 0 if x is second else 1))
                    q = list(bb(mv['pl']))
                    if mv is second:
                        q[ax] = rf[ax + 2]
                    else:
                        q[ax + 2] = rs[ax]
                    if any(o is not mv and min(overlap(q, bb(o['pl']))) > 0.3 for o in blds) or                             (court13 and min(overlap(q, court13)) > 0.3) or any(min(overlap(q, bd['rect'])) > 0.5 for bd in bands):
                        continue
                    mv['pl'] = R(*q)
                    other = first if mv is second else second
                    slits.append((mv['id'], other['id'] if other else 'court 13', round(g * U, 2), blk_of(model, pcen(mv['pl']))))
        if not slits:
            break
    if slits:
        blks = sorted({sl[3] for sl in slits if sl[3]})
        fix(None, '%d щелей %.1f–%.1f м между домами спиной к спине (кварталы %s) закрыты: задняя стена дома дотянута до соседа%s.'
            % (len(slits), min(sl[2] for sl in slits), max(sl[2] for sl in slits), ', '.join(blks),
               '; двор базы 4 с юга закрыт глухими задними стенами ряда домов к S1 (на плане — отдельная стена и щель 1,7 м за ней)'
               if any(sl[1] == 'court 13' for sl in slits) else ''),
            'Генератор оставлял зазор 6 ед. (1,2 м до ужатия) между рядами; v02 §8.5: дома сплошной стеной, без щелей.')

    base13 = None
    if PLAN == 'v37' and court13:
        cx0, cy0, cx1, cy1 = court13
        ny1 = cy0 + V37_BASE13_DEPTH_M / U
        cand = [b for b in blds if b['kind'] == 'house' and is_rect(b['pl']) and bb(b['pl'])[1] < ny1 and bb(b['pl'])[3] > ny1 + 10
                and bb(b['pl'])[1] > cy0 and min(bb(b['pl'])[2], cx1) - max(bb(b['pl'])[0], cx0) > 2]
        trimmed, split, merged = [], [], []
        for b in sorted(cand, key=lambda b: bb(b['pl'])[0]):
            r_ = bb(b['pl'])
            b['pl'] = R(max(r_[0], cx0), ny1, min(r_[2], cx1), r_[3])
            trimmed.append(b['id'])
            for side, part in (('w', (r_[0], r_[1], cx0, r_[3])), ('e', (cx1, r_[1], r_[2], r_[3]))):
                if part[2] - part[0] < 0.6:
                    continue
                nb_ = None
                if part[2] - part[0] < 30:                                 # sliver < 6 m: the neighbour on that side takes it
                    for o in blds:
                        ro = bb(o['pl'])
                        if o['kind'] == 'house' and is_rect(o['pl']) and abs(ro[1] - part[1]) < 1 and abs(ro[3] - part[3]) < 1 and \
                                (abs(ro[2] - part[0]) < 0.6 if side == 'w' else abs(ro[0] - part[2]) < 0.6):
                            nb_ = o
                if nb_ is not None:
                    ro = bb(nb_['pl'])
                    nb_['pl'] = R(min(ro[0], part[0]), ro[1], max(ro[2], part[2]), ro[3])
                    merged.append((nb_['id'], round((part[2] - part[0]) * U, 1)))
                else:
                    nb_ = dict(b, pl=R(*part), pl0=R(*part), id=b['id'] + side, label=None)
                    blds.append(nb_)
                    split.append(nb_['id'])
        byid = {b['id']: b for b in blds}
        base13 = (cx0, cy0, cx1, ny1)
        for b in blds:                                                     # the court must stay closed: no separation gap next to it
            ox_, oy_ = overlap(bb(b['pl']), (cx0 - 40, cy0 - 1, cx1 + 40, ny1 + 1))
            if min(ox_, oy_) > -0.6:
                b['no_gap'] = True
        fix(pcen(R(*base13)), 'Решение Феди 22.10 (п. 12): двор базы 4 (13) — %.0f м в глубину (был %.1f м): ряд домов к S1 за двором стал мельче на %.1f м '
                              '(%s), дом, выходивший за двор, разделён (%s), узкий остаток отдан соседу (%s) — двор закрыт со всех сторон, бусик '
                              'разворачивается внутри.' % (V37_BASE13_DEPTH_M, (cy1 - cy0) * U, (ny1 - cy1) * U, ', '.join(trimmed), ', '.join(split) or '-',
                                                          ', '.join('%s +%.1f м' % m_ for m_ in merged) or '-'),
            'v10 §4: дворы и места погрузки 12-15 м, чтобы развернуться; улицы и тротуары не меняются (задние стены).')
    # ------------------------------------------------ overlaps between buildings (only towers on their podiums are intended)
    ov = []
    for i, a in enumerate(blds):
        for b in blds[i + 1:]:
            ox, oy = overlap(bb(a['pl']), bb(b['pl']))
            if min(ox, oy) <= 0.3:
                continue
            ar = parea(clip_rect(a['pl'], bb(b['pl']))) if is_rect(b['pl']) else (parea(clip_rect(b['pl'], bb(a['pl']))) if is_rect(a['pl']) else ox * oy)
            kinds = {a['kind'], b['kind']}
            if kinds in ({'tower', 'podium'}, {'tower_round', 'podium_round'}, {'police', 'police_rotunda'}):
                continue
            if ar > 1.0:
                ov.append((a['id'], b['id'], round(ar * U * U, 2)))
    assert not ov, ('unexpected building overlaps', ov)

    # ------------------------------------------------ attributes
    corner = lambda b: b['kind'] == 'house' and b['h'] >= 18
    adj = {b['id']: set() for b in blds}
    for i, a in enumerate(blds):
        ra = bb(a['pl'])
        for b in blds[i + 1:]:
            rb = bb(b['pl'])
            ox, oy = overlap(ra, rb)
            if (abs(ox) < 0.8 and oy > 2) or (abs(oy) < 0.8 and ox > 2):
                adj[a['id']].add(b['id'])
                adj[b['id']].add(a['id'])
    house_like = ('house', 'arch_house', 'loft', 'alley_plug')
    recol = 0
    for b in blds:                                                         # plan colour, neighbours never the same colour
        b['col'] = b['fill']
    for b in blds:
        if b['kind'] not in house_like:
            continue
        taken = {byid[n]['col'] for n in adj[b['id']]}
        if b['col'] in taken:
            pool = [c for c in PALETTE if c not in taken]
            b['col'] = pool[int(h01(b['id'] + 'col') * len(pool))]
            recol += 1
    if recol:
        fix(None, '%d дом(ов) того же цвета, что сосед вплотную, перекрашены в другой цвет палитры плана.' % recol,
            'v02 §8.5 / легенда §6: соседние дома всегда разного цвета.')
    gaps37 = []
    if PLAN == 'v31':
        for b in blds:                                                     # floors
            k, h = b['kind'], b['h']
            if k == 'house' or k == 'arch_house':
                lo, hi = {7: (5, 5), 9: (5, 6), 11: (5, 6), 13: (6, 7), 14: (6, 7), 15: (6, 7)}.get(h, (7, 8) if h >= 18 else (5, 6))
                b['fl_range'] = (lo, hi)
                b['floors'] = lo + int(h01(b['id'] + 'fl') * (hi - lo + 1) - 1e-9)
        for b in blds:                                                     # neighbours differ in height where the class allows
            if 'fl_range' in b and any(byid[n].get('floors') == b['floors'] for n in adj[b['id']]):
                lo, hi = b['fl_range']
                alt = [f for f in range(lo, hi + 1) if all(byid[n].get('floors') != f for n in adj[b['id']])]
                if alt:
                    b['floors'] = alt[0]
    else:
        gaps37 = v37_floors_offices_separation(blds, byid, adj, bands, model)
        corner = lambda b: bool(b.get('corner37'))
    gf_of, aw_of, slot_of = {}, {}, {}
    for b in sorted(blds, key=lambda b: b['id']):
        if b['kind'] not in ('house', 'arch_house', 'loft'):
            continue
        used = {gf_of.get(n) for n in adj[b['id']]}
        pref = sorted(GROUND_FLOORS, key=lambda g: h01(b['id'] + g))
        if corner(b):                                                      # corners are commercial, but not all cafes
            com = sorted(('cafe_terrace', 'storefront', 'rollshutter_shop', 'office_lobby'), key=lambda g: h01(b['id'] + 'c' + g))
            pref = com + [g for g in pref if g not in com]
        if b.get('office37'):                                              # v37 office: glazed lobby, sometimes a corner cafe
            pref = ['office_lobby', 'cafe_terrace', 'storefront'] if not corner(b) or h01(b['id'] + 'oc') < 0.6 else ['cafe_terrace', 'office_lobby']
            used.discard('office_lobby')
        gf_of[b['id']] = next((g for g in pref if g not in used), pref[0])
        if gf_of[b['id']] in ('storefront', 'cafe_terrace', 'rollshutter_shop') and h01(b['id'] + 'aw') < 0.6:
            usedc = {aw_of.get(n) for n in adj[b['id']]}
            aw_of[b['id']] = next(c for c in sorted(AWNINGS, key=lambda c: h01(b['id'] + c)) if c not in usedc)
        brick = b['col'] in BRICK_COLS
        slot = 'downtown_house_brick' if brick else 'downtown_house_stucco'
        if (not corner(b) and b['kind'] == 'house' and gf_of[b['id']] in ('storefront', 'rollshutter_shop') and h01(b['id'] + 'sf') < 0.5
                and all(slot_of.get(n) != 'downtown_storefront' for n in adj[b['id']])):
            slot = 'downtown_storefront'
        if b.get('office37'):
            slot = 'downtown_office'
        slot_of[b['id']] = slot

    # ------------------------------------------------ entrances
    alley_rects = [r_ for a in alley_out for r_ in a['rects']]
    shutters = [bb(e['pts']) for e in sel(els, g='buildings', tag='polygon', fill='#4E5559')]

    def outward(pl, a, b):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        n = (u[1], -u[0])
        c, m_ = pcen(pl), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if n[0] * (m_[0] - c[0]) + n[1] * (m_[1] - c[1]) < 0:
            n = (-n[0], -n[1])
        return u, n, L

    def frontages(pl):
        res = []
        for i in range(len(pl)):
            a, b = pl[i], pl[(i + 1) % len(pl)]
            u, n, L = outward(pl, a, b)
            if L < 3 or (abs(u[0]) > 0.02 and abs(u[1]) > 0.02):
                continue
            m_ = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            for bd in bands:
                ax = bd['ax']                                              # band axis: 1 = street along x (axis y = const)
                if abs(n[ax]) < 0.99:
                    continue
                t = (bd['axis'] - m_[ax]) * n[ax]
                if not (HW - 2 <= t <= HW + 25):
                    continue
                lo_, hi_ = bd['rect'][1 - ax], bd['rect'][3 - ax]
                e_lo, e_hi = min(a[1 - ax], b[1 - ax]), max(a[1 - ax], b[1 - ax])
                ov_ = min(e_hi, hi_ - HW * 0.5) - max(e_lo, lo_ + HW * 0.5)
                if ov_ < 2:
                    continue
                res.append({'street': bd['street'], 't': t, 'a': a, 'b': b, 'n': n, 'L': L, 'range': (max(e_lo, lo_ + HW * 0.5), min(e_hi, hi_ - HW * 0.5)), 'ax': ax})
        res.sort(key=lambda r_: (r_['t'], -r_['L']))
        return res

    def facing(n):
        return round(math.degrees(math.atan2(-n[1], n[0])) % 360.0, 1) + 0.0

    def door_at(fr, f, kind, w, role, key):
        ax = fr['ax']
        lo_, hi_ = fr['range']
        x = lo_ + (hi_ - lo_) * f
        x = min(max(x, lo_ + min(10, (hi_ - lo_) / 2)), hi_ - min(10, (hi_ - lo_) / 2))
        p = [0, 0]
        p[1 - ax], p[ax] = x, fr['a'][ax]
        return {'pos': rnd2(W(p)), 'facing_deg': facing(fr['n']), 'kind': kind, 'w_m': w, 'benches': 0, 'role': role, 'street': fr['street']}

    for b in blds:
        pl, k = b['pl'], b['kind']
        ent = []
        frs = frontages(pl)                                                # only straight axis-aligned walls count
        if k in ('pavilion',):
            c = pcen(pl)
            best = None
            for i in range(4):
                a, q = pl[i], pl[(i + 1) % 4]
                u, n, L = outward(pl, a, q)
                if n[0] * (model['axis'] - c[0]) > 0 and abs(n[0]) > 0.99:
                    best = (a, q, n)
            a, q, n = best
            m_ = ((a[0] + q[0]) / 2, (a[1] + q[1]) / 2)
            ent.append({'pos': rnd2(W(m_)), 'facing_deg': facing(n), 'kind': 'door', 'w_m': 2.0, 'benches': 0, 'role': 'glass double door to the terrace'})
        elif k == 'podium':
            x0, y0, x1, y1 = bb(pl)
            for t in [tw for tw in blds if tw['kind'] == 'tower']:
                ent.append({'pos': rnd2(W((pcen(t['pl'])[0], y1))), 'facing_deg': 270.0, 'kind': 'door', 'w_m': 4.0, 'benches': 0,
                            'role': 'tower lobby, top of the tribune stair (plaza side)'})
            ent.append({'pos': rnd2(W(((x0 + x1) / 2, y0))), 'facing_deg': 90.0, 'kind': 'door', 'w_m': 3.0, 'benches': 0, 'role': 'north lobby (N2 / Nj)'})
        elif k in ('tower', 'tower_round'):
            pass                                                           # entered through the podium
        elif k == 'podium_round':
            fr = frs[0]
            ent.append(door_at(fr, 0.5, 'door', 3.0, 'lobby of the round corner tower', b['id']))
        elif k == 'gas_shop':
            x0, y0, x1, y1 = bb(pl)
            ent.append({'pos': rnd2(W(((x0 + x1) / 2, y0))), 'facing_deg': 90.0, 'kind': 'door', 'w_m': 1.8, 'benches': 0, 'role': 'shop door to the forecourt / canopy'})
        elif frs:
            main = frs[0]
            if k == 'classical':
                main = next((f for f in frs if f['street'] == 'S1'), main)
            if k == 'arch_house':                                          # the door stays out of the drive-through arch
                ar = bb(arch_el)
                lo_, hi_ = main['range']
                parts = [(lo_, min(hi_, ar[1 - main['ax']] - 2)), (max(lo_, ar[3 - main['ax']] + 2), hi_)]
                main = dict(main, range=max(parts, key=lambda q_: q_[1] - q_[0]))
            w = {'police': 2.0, 'classical': 3.0, 'glass_office': 3.0, 'diner': 1.6, 'gas_shop': 1.8, 'taxi_depot': 1.6, 'podium_annex': 2.0}.get(k, 1.2)
            f = 0.5 if main['L'] < 50 else 0.25 + 0.5 * h01(b['id'] + 'door')
            role = 'main' if k not in ('house', 'arch_house', 'loft') else ('main / shop' if gf_of.get(b['id']) in ('storefront', 'cafe_terrace', 'rollshutter_shop') else 'main')
            if k == 'alley_plug':                                          # end house of a single blind alley faces a street
                ent.append(door_at(main, 0.5, 'door', 1.2, 'main (street side; blind wall to the alley)', b['id']))
            elif k != 'base_garage':
                ent.append(door_at(main, f, 'door', w, role, b['id']))
            if corner(b) or k in ('police', 'diner'):
                other = next((f2 for f2 in frs[1:] if f2['ax'] != main['ax']), None)
                if other:                                                  # second door on the side street, next to the shared corner
                    cc = main['a'][main['ax']]
                    lo_, hi_ = other['range']
                    ent.append(door_at(other, 0.0 if abs(lo_ - cc) < abs(hi_ - cc) else 1.0, 'door', 1.6,
                                       'corner shop door' if k == 'house' else 'side door', b['id']))
        for r_ in shutters:                                                # roll shutters drawn on the plan
            c = ((r_[0] + r_[2]) / 2, (r_[1] + r_[3]) / 2)
            if not pin(c, b['pl0']) and min(abs(c[0] - q_[0]) + abs(c[1] - q_[1]) for q_ in b['pl0']) > 40:
                continue
            for i in range(len(pl)):
                a, q = pl[i], pl[(i + 1) % len(pl)]
                u, n, L = outward(pl, a, q)
                if L < 3 or (abs(n[0]) < 0.99 and abs(n[1]) < 0.99):
                    continue
                ax = 0 if abs(n[0]) > 0.99 else 1
                if (abs(c[ax] - a[ax]) < 6 or (abs(c[ax] - a[ax]) < 20 and (c[ax] - a[ax]) * n[ax] > 0)) and                         min(a[1 - ax], q[1 - ax]) - 1 <= c[1 - ax] <= max(a[1 - ax], q[1 - ax]) + 1:
                    p = [0, 0]
                    p[ax], p[1 - ax] = a[ax], c[1 - ax]
                    w = max(r_[2] - r_[0], r_[3] - r_[1]) * U
                    ent.append({'pos': rnd2(W(p)), 'facing_deg': facing(n), 'kind': 'rollshutter', 'w_m': round(max(4.0, w), 1), 'benches': 0,
                                'role': 'garage roll shutter (plan)', 'clear_h_m': 4.0})
                    break
        if k in ('house', 'arch_house', 'loft'):                           # back doors into dead-end alleys (v02 §8.5)
            for i in range(len(pl)):
                a, q = pl[i], pl[(i + 1) % len(pl)]
                u, n, L = outward(pl, a, q)
                for ar in alley_rects:
                    for ax in (0, 1):
                        if abs(n[ax]) < 0.99:
                            continue
                        side = ar[ax] if n[ax] > 0 else ar[ax + 2]
                        if abs(a[ax] - side) > 0.6:
                            continue
                        lo_, hi_ = max(min(a[1 - ax], q[1 - ax]), ar[1 - ax]), min(max(a[1 - ax], q[1 - ax]), ar[3 - ax])
                        if hi_ - lo_ < 8:
                            continue
                        p = [0, 0]
                        p[ax], p[1 - ax] = a[ax], lo_ + (hi_ - lo_) * (0.3 + 0.4 * h01(b['id'] + 'bd'))
                        ent.append({'pos': rnd2(W(p)), 'facing_deg': facing(n), 'kind': 'door', 'w_m': 1.0, 'benches': 0, 'role': 'back door (alley)'})
        b['entrances'] = ent
        b['frontages'] = [f['street'] for f in frs]

    # ------------------------------------------------ sockets from the plan (fire escapes, water tanks)
    for e in sel(els, g='buildings', tag='polygon', fill='#3D4246'):
        p0, p1, p2 = e['pts'][0], e['pts'][1], e['pts'][2]
        o = ((p2[0] - p1[0]) / 3.6, (p2[1] - p1[1]) / 3.6)
        ax = 0 if abs(o[0]) > 0.5 else 1
        best = None
        for b in blds:
            r_ = bb(b['pl'])
            face = r_[ax + 2] if o[ax] > 0 else r_[ax]
            mid = (p0[1 - ax] + p1[1 - ax]) / 2
            if r_[1 - ax] - 1 <= mid <= r_[3 - ax] + 1:
                d = abs(face - p0[ax])
                if best is None or d < best[0]:
                    best = (d, b, face)
        if best and best[0] < 20:
            d, b, face = best
            q0, q1 = list(p0), list(p1)
            q0[ax] = q1[ax] = face
            b.setdefault('fire', []).append({'from': rnd2(W(q0)), 'to': rnd2(W(q1)), 'out_deg': facing(o), 'depth_m': 1.2, 'src': 'plan'})
    for e in sel(els, g='buildings', tag='circle', fill='#8B6B4A'):
        cands = [b for b in blds if pin(e['c'], b['pl'])] or sorted(blds, key=lambda b: math.hypot(pcen(b['pl'])[0] - e['c'][0], pcen(b['pl'])[1] - e['c'][1]))[:1]
        cands[0].setdefault('tanks', []).append(rnd2(W(e['c'])))
    for b in blds:                                                         # alley walls get fire escapes too (legend: "пожарные лестницы")
        if b['kind'] not in ('house', 'arch_house') or h01(b['id'] + 'fe') > 0.5:
            continue
        for d in b['entrances']:
            if d['role'] == 'back door (alley)':
                b.setdefault('fire', []).append({'at': d['pos'], 'out_deg': d['facing_deg'], 'depth_m': 1.2, 'src': 'rule: alley wall'})
                break

    # ------------------------------------------------ building records
    out_b = []
    for b in blds:
        k, h, bid = b['kind'], b['h'], b['id']
        tint = calm_bright(b['col'], bid)
        roof = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': PARAPET}
        notes, slot, walls, kit = [], 'downtown_house_stucco', 'facade_downtown_stucco', 'downtown'
        fl, fh, height = None, FLOOR_H, None
        if k == 'tower':
            fl, fh, height = 55, 3.6, 200.0
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            roof = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 1.2, 'crown': 'light canopy ring'}
            notes.append('round faceted dark-blue glass (v02 §8.5), identical twins, glass belt at podium level; Ø from the plan')
        elif k == 'podium':
            fl, fh, height = 1, 6.0, 6.0
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            notes.append('common glass podium of the twins; the tribune stair (5 steps) climbs 2.25 m from the plaza to its lobby terrace; screen 35 on its south face')
        elif k == 'tower_round':
            fl, fh = 24, 3.6
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            notes.append('round glass corner tower (legend §6); height not given -> 24 floors from the plan shadow 46 vs 70 of the twins (question)')
        elif k == 'podium_round':
            fl, fh = 2, 4.0
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            notes.append('glass podium of the round corner tower')
        elif k == 'glass_office' and PLAN == 'v37':
            k, fl, fh = 'office', 6, 3.6
            height = GROUND_H + 5 * 3.6
            slot, walls, kit = 'downtown_office', 'facade_downtown_stucco', 'downtown'
            tint = calm_bright('#9FB0A8' if b['label'] == '05' else '#A9A69C', bid)
            notes.append('legend %s office (v37 / Fedya 22.10: office facade class, NOT all-glass; 6 floors max): large punched / ribbon windows '
                         '~50 %% glass, stone or panel spandrels, thin dark mullions, glazed lobby on the boulevard; the plan draws a blue gridded '
                         'roof = glazed roof light over the lobby' % b['label'])
        elif k == 'glass_office':
            fl, fh = 10, 3.6
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            notes.append('glass office; floors not given -> 10 (plan shadow 30 vs 18-22 of corner houses) (question)')
        elif k == 'pavilion':
            fl, fh = 1, 4.5
            slot, walls, kit, tint = 'downtown_tower_glass', 'tower_glass', 'none', None
            roof = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 0.3}
            notes.append('glass pavilion, shop windows all round, terrace with 3 yellow umbrellas (props)')
        elif k == 'classical':
            fl, fh = 3, 4.6
            slot, walls, tint = 'downtown_classical', 'stucco_SK3b', '#D9D2C2'
            roof = {'type': 'flat', 'material': 'roof_flat_SK4d', 'parapet_h_m': 1.2, 'skylight': 'round, centre'}
            notes.append('stone building (bank / library) with a colonnade along the promenade front (S1), round skylight')
        elif k == 'loft':
            fl, fh = 4, 4.2
            slot, walls = 'downtown_house_brick', 'facade_downtown_brick'
            roof = {'type': 'sawtooth', 'material': 'roof_profsheet_SK4c', 'parapet_h_m': 0.8, 'ridge_axis_deg': 90.0}
            notes.append('brick loft (old warehouse) with saw-tooth roof lights (legend §6)')
        elif k == 'police':
            fl, fh = 4, 3.6
            notes.append('police station (%s); light blue-grey civic stucco' % ('SW, rotunda on the corner' if b['label'] == '10' else 'NE, rounded corner'))
        elif k == 'police_rotunda':
            fl, fh = 2, 4.5
            roof = {'type': 'dome', 'material': 'metal_painted_SK6a', 'parapet_h_m': 0.6}
            notes.append('rotunda of police 1 on the W2 / S1 corner')
        elif k == 'taxi_depot':
            fl, fh = 2, 4.0
            notes.append('taxi depot office + garage, built onto police 2; own stand (zone 05-12-stand)')
        elif k == 'van_shop':
            fl, fh = 2, 4.5
            slot, walls = 'downtown_storefront', 'facade_storefront'
            notes.append('van shop 07: roll-shutter gates straight onto the boulevard (v10 §7.5 "магазин для бусика с воротами на улицу")')
        elif k == 'diner':
            fl, fh = 1, 4.5
            slot, walls, tint = 'downtown_storefront', 'facade_storefront', '#D7DDE1'
            roof = {'type': 'flat', 'material': 'metal_painted_SK6a', 'parapet_h_m': 0.4}
            notes.append('chrome corner diner with a red stripe, rounded corners (plan)')
        elif k == 'gas_shop':
            fl, fh = 1, 4.0
            slot, walls = 'downtown_storefront', 'facade_storefront'
            notes.append('gas-station shop (41), faces the canopy')
        elif k == 'podium_annex':
            fl, fh = 2, 3.5
            notes.append('low service / parking lobby building on N2 between ramp 1 and Nj (plan h = 6)')
        elif k == 'base_garage':
            fl, fh = 1, 5.5
            slot, walls = 'downtown_house_brick', 'facade_downtown_brick'
            notes.append('BASE 4 brick garage; roll shutter with canopy in its east end, faces the courtyard (legend §4)')
        elif k == 'alley_plug':
            fl, fh = 3, FLOOR_H
            slot, walls = 'downtown_house_brick', 'facade_downtown_brick'
            notes.append('dead-end plug: blind brick walls to the alley(s) (v02 §8.5 "NPC забегает — а там стена")')
        else:
            fl = b['floors']
            slot = slot_of.get(bid, 'downtown_house_stucco')
            walls = {'downtown_house_brick': 'facade_downtown_brick', 'downtown_house_stucco': 'facade_downtown_stucco',
                     'downtown_storefront': 'facade_storefront', 'downtown_office': 'facade_downtown_stucco'}[slot]
            if b.get('office37'):
                fh = 3.6
                height = GROUND_H + (fl - 1) * 3.6
                notes.append('office building of the business ring (main facade faces the plaza / towers across %s): office facade class'
                             % '/'.join(b.get('office_front37', [])))
            if corner(b):
                notes.append('corner house (plan class h %d) -> higher' % h if PLAN == 'v31' else 'corner house (two street faces) -> one of the 6s')
            if k == 'arch_house':
                notes.append('house over the BASE 4 drive-through arch (from Hse2)')
            if bb(b['pl'])[1] < 150 and blk_of(model, pcen(b['pl'])) in ('OB1', 'NEX'):
                notes.append('stopper house outside the ring bend (legend §6: the street runs into a house)')
            if not b['entrances']:
                notes.append('inner house without a street frontage (between office 05 and the stone building): entered through its neighbours')
        if height is None:
            if k in ('house', 'arch_house'):
                height = GROUND_H + (fl - 1) * FLOOR_H
                fh = FLOOR_H
            else:
                height = fl * fh
        fp = ccw(WL(b['pl']))
        gf = gf_of.get(bid)
        rec = {'id': bid, 'kind': k, 'material_slot': slot, 'footprint': fp, 'floors': fl, 'floor_h_m': fh, 'height_m': round(height, 1),
               'roof': roof, 'walls': walls, 'tint': tint, 'entrances': b['entrances'], 'arches': [], 'facade_kit': kit,
               'sockets': {'balconies': 'none', 'windows': kit != 'none' or k == 'pavilion', 'fire_escape': b.get('fire', False),
                           'ac_units': 0 if kit == 'none' else int(h01(bid + 'ac') * 4), 'water_tank': b.get('tanks', False),
                           'awning': {'tint': aw_of[bid], 'pattern': 'striped' if h01(bid + 'st') < 0.2 else 'plain'} if bid in aw_of else False,
                           'storefront': gf in ('storefront', 'cafe_terrace', 'rollshutter_shop') or k in ('van_shop', 'diner', 'gas_shop', 'pavilion'),
                           'ridge_cap': None, 'antenna': kit != 'none' and h01(bid + 'ant') < 0.3, 'signs': 'no text (v02 §11)'},
               'collider': 'full_roof', 'disabled': False, 'src_colour': b['fill'], 'plan_h': h, 'frontages': b['frontages'], 'notes': '; '.join(notes)}
        if b['label']:
            rec['legend'] = b['label']
        if gf:
            rec['ground_floor'] = {'kind': gf, 'h_m': GROUND_H, 'material_slot': 'downtown_storefront' if gf in ('storefront', 'cafe_terrace', 'rollshutter_shop') else slot,
                                   'cafe_tables': gf == 'cafe_terrace'}
        if (k == 'house' and h >= 18 and PLAN == 'v31') or (PLAN == 'v37' and b.get('corner37')):
            rec['corner'] = True
        if PLAN == 'v37':
            off = b.get('office37') or k == 'office'
            rec['type'] = 'office' if off else ('residential' if k in ('house', 'arch_house', 'alley_plug') else k)
            rec['facade_class'] = 'office' if off else ('tower_glass' if slot == 'downtown_tower_glass' else
                                                        'residential' if k in ('house', 'arch_house', 'alley_plug', 'loft') else 'special')
            if off:
                rec['office_facade'] = OFFICE_FACADE
                rec['office_front'] = b.get('office_front37', [])
            if 'sep' in b:
                rec['separation'] = b['sep']
        if k == 'arch_house':
            ar = bb(arch_el)
            rec['arches'].append({'id': '13-A1', 'rect': ccw(WL(R(*ar))), 'through': 'N-S', 'clear_w_m': round((ar[2] - ar[0]) * U, 2),
                                  'clear_h_m': 4.5, 'notes': 'drive-through arch from Hse2 into the BASE 4 courtyard (v10 §4: >= 4 m)'})
        out_b.append(rec)

    # ------------------------------------------------ zones
    zones, props = [], []
    jun = junctions(st)
    ring = set(model['ring'])
    for name, s in st.items():
        z = {'id': '05-street-' + name, 'kind': 'street', 'poly_line': WL(s['pts']), 'carriageway_m': CARR, 'sidewalk_m': WALK, 'curb_m': CURB,
             'corner_radius_m': CORNER_R, 'surface': 'asphalt_A5d12', 'sidewalk_surface': 'sidewalk_S1', 'lanes': 2,
             'markings': 'white dashed centre line', 'boulevard': name == 'B', 'ring': name in ring, 'cap': s['cap'],
             'length_m': round(sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(s['pts'][:-1], s['pts'][1:])) * U, 1)}
        if name == 'B':
            z['notes'] = 'boulevard = same 2-lane street, no median (v02 §8.5); bends round the plaza; zebras across it only at Vb / AX / Vc'
        if name == 'S1' and PLAN == 'v31':
            z['notes'] = ('one straight promenade street along the beach (v27, approved); its south sidewalk borders the promenade of district 09 '
                          '(the v85 picture cut the plan at plan y 1252, 2.6 m inside this sidewalk)')
        elif name == 'S1':
            z['notes'] = 'v31 promenade street, inner street since plan v37 (the promenade row SP1-SP5 was added south of it)'
        elif name == 'SP':
            z['notes'] = ('plan v37: one straight promenade street along the beach (v31 S1 moved 54 m south); its south sidewalk = top edge of the palm '
                          'park of district 09 (beach moved 54 m south with it); van entries and the 2 beach lots join it from the south')
        elif name in ('N0w', 'N0c', 'N0e'):
            z['notes'] = 'plan v37: new top ring (city grew 52-60 m north); tunnel / VIEW B / VIEW C roads join it from the north (entries)'
        elif name.startswith('Vp'):
            z['notes'] = 'plan v37: street of the promenade row, staggered against the grid above and the beach entries (T on S1 and SP)'
        if 'beyond_S1_plan' in s:
            z['notes'] = 'ends at S1; the plan continuation to the beach is the south entry (zone 05-entry-S-%s)' % name
        zones.append(z)
    for jj, (p, names) in enumerate(sorted(jun, key=lambda t: (t[0][1], t[0][0]))):
        lg = [(n, v, L) for n in sorted(names) for v, L in legs(st, n, p)]
        typ = {2: 'bend', 3: 'T', 4: 'X'}.get(len(lg), 'multi')
        main = 'B' in names or 'AX' in names
        control = 'none' if len(lg) < 3 else ('traffic_light' if main else 'stop')
        cross = []
        if 'B' in names:                                                   # legend v26 §1 / v02 §8.5: zebras only at the boulevard
            plaza = bool({'AX', 'Vb', 'Vc'} & names)
            for n, v, L in lg:
                probe = (p[0] + v[0] * 60, p[1] + v[1] * 60)
                if (not pin(probe, model['district']) and n != 'AX') or (n == 'B' and not plaza) or L < 55:
                    continue
                q = (p[0] + v[0] * (CW + 12.5), p[1] + v[1] * (CW + 12.5))
                leg = round(math.degrees(math.atan2(-v[1], v[0])) % 360, 1)
                cross.append({'street': n, 'centre': rnd2(W(q)), 'leg_deg': leg, 'walk_deg': round((leg + 90) % 180, 1), 'w_m': 4.0,
                              'span_m': CARR, 'notes': 'zebra across the %s carriageway, 8.5 m from the junction centre' % n})
        zones.append({'id': '05-junction-%02d' % jj, 'kind': 'junction', 'pos': rnd2(W(p)), 'streets': sorted(names), 'type': typ,
                      'legs_deg': [round(math.degrees(math.atan2(-v[1], v[0])) % 360, 1) for n, v, L in lg], 'control': control,
                      'crosswalks': cross, 'corner_radius_m': CORNER_R})

    # entries (v10 §6): world roads from the master SVG
    master_roads, stubs = [], []
    for nm, at, M, ids, s0, s1 in svg_tags(svg_text()):
        if nm == 'polygon' and ids and ids[-1] == 'L06b_entry' and attr(at, 'fill') == '#5F666C':
            stubs.append([Winv(pic_of_pre(u2m(*q))) for q in points_of(at, M)])
        if nm == 'polyline' and ids and ids[-1] in ('R24_roads', 'R74_elite_ring', 'R84_downtown_entries') and attr(at, 'stroke') in ('#5F666C', '#B3A68D'):
            master_roads.append((ids[-1], attr(at, 'stroke-width'), [pic_of_pre(u2m(*q)) for q in points_of(at, M)]))

    def world_end(target, groups=('R24_roads', 'R74_elite_ring')):
        best = None
        for g, w, pl in master_roads:
            if g not in groups:
                continue
            for e_ in (pl[0], pl[-1]):
                d = math.hypot(e_[0] - target[0], e_[1] - target[1])
                if best is None or d < best[0]:
                    best = (d, e_, pl, g, w)
        return best

    ent_specs = [
        ('W', 'B', (model['st']['B']['pts'][0]), (-1, 0), 'R24 road from the west (Hamlet -> Construction -> Downtown straight, rural asphalt 6.4 m; '
         'R84_downtown_entries widens it to 9.6 m at the corner)'),
        ('E', 'B', (model['st']['B']['pts'][-1]), (1, 0), 'R74 Elite stone road 4.5 m (half-ring up the hill, gates on the east side)'),
        ('N-tunnel', 'Vn', (445.0, 70.0), (0, -1), 'R24 road from the tunnel under hill B (Rough), portal ~60 m north'),
        ('N-viewB', 'N3', None, (0, -1), 'R24 serpentine up to VIEW B (+46 m)'),
        ('NE-viewC', 'E1', (2240.0, 330.0), (0, -1), 'R24 cornice road VIEW C over the bay -> Port (not in the brief list; drawn on v85)'),
        ('S-Va2', 'Va2', (620.0, 1210.0), (0, 1), 'beach district 09: van entry onto the sand (beach plan v06), parking next to it'),
        ('S-Vds', 'Vds', (1840.0, 1210.0), (0, 1), 'beach district 09: van entry onto the sand (beach plan v06), parking next to it')]
    if PLAN == 'v37':                                                      # v37: the north entries move to the new top ring, south = promenade SP
        ent_specs = ent_specs[:2] + [
            ('N-tunnel', 'N0w', (V37_ENTRY_X['N-tunnel'], -150.0), (0, -1),
             'tunnel under hill B: the tunnel keeps its axis, its south portal moves ~45 m up the axis (the city grew 50 m north); the approach '
             'leaves the portal on the axis, bends right (R >= ~20 m) and runs straight 15 m into N0w (T, %.0f m east of the NW ring corner)'
             % ((V37_ENTRY_X['N-tunnel'] - 100.0) * U)),
            ('N-viewB', 'N0c', (V37_ENTRY_X['N-viewB'], -190.0), (0, -1),
             'R24 serpentine up to VIEW B (+46 m): cut where it meets the new top ring, last ~30 m bent onto a straight 12 m approach (T on N0c)'),
            ('NE-viewC', 'N0e', (V37_ENTRY_X['NE-viewC'], -110.0), (0, -1),
             'R24 cornice road VIEW C over the bay -> Port: starts on N0e (its v85 start on E1 is now the NE block / E1); the cornice line meets N0e '
             'exactly opposite the NEB alley mouth (alley axis x = road axis: a clean crossing, no 2-4 m jog)'),
            ('S-van-W', 'SP', (V37_ENTRY_X['S-van-W'], 1480.0), (0, 1),
             'beach district 09 (moved 54 m south with the city): van entry W onto the sand (beach plan v06, v85 x), parking lot W next to it'),
            ('S-van-E', 'SP', (V37_ENTRY_X['S-van-E'], 1480.0), (0, 1),
             'beach district 09: van entry E onto the sand, parking lot E next to it; the sand track to the Elite beach starts here')]
    vb_end = world_end(W((1480.0, 150.0)))                                 # the serpentine lands on N3 between OB1 and NEX
    entries = []
    for key, street, ax_p, d, desc in ent_specs:
        if ax_p is None:
            gx = Winv(vb_end[1])[0]
            ax_p = (round(gx, 1), 150.0)
        pos = (ax_p[0] + d[0] * HW, ax_p[1] + d[1] * HW)
        curb_drop = R(min(ax_p[0] + d[0] * CW, pos[0]) if d[0] else ax_p[0] - CW, min(ax_p[1] + d[1] * CW, pos[1]) if d[1] else ax_p[1] - CW,
                      max(ax_p[0] + d[0] * CW, pos[0]) if d[0] else ax_p[0] + CW, max(ax_p[1] + d[1] * CW, pos[1]) if d[1] else ax_p[1] + CW)
        z = {'id': '05-entry-' + key, 'kind': 'entry', 'pos': rnd2(W(pos)), 'axis_point': rnd2(W(ax_p)), 'street': street,
             'heading_deg': round(math.degrees(math.atan2(-d[1], d[0])) % 360, 1), 'carriageway_m': CARR, 'world_road': desc,
             'curb_drop': ccw(WL(curb_drop)), 'join_rule': 'world road continues as carriageway up to this street; straight approach for the last 15-20 m; '
                                                        'lowered curb across the sidewalk (v10 §6)'}
        if not key.startswith('S-') and (PLAN == 'v31' or key in ('W', 'E')):
            we = world_end(W(ax_p))
            if we and we[0] < 40:
                e_ = we[1]
                q = Winv(e_)
                lat = (q[0] - ax_p[0]) * U if d[0] == 0 else (q[1] - ax_p[1]) * U
                z['world_road_end'] = rnd2(e_)
                z['world_road_src'] = we[3]
                z['world_road_lateral_offset_m'] = round(lat * (1 if d[0] == 0 else -1), 2)
        entries.append(z)
    zones += entries
    for pl in stubs:                                                       # old asphalt patches of the world picture on Downtown sidewalks
        c = pcen(pl)
        if -60 < c[0] < 2400 and 0 < c[1] < 1270:
            on = [bd['street'] for bd in bands if min(overlap(bb(pl), bd['rect'])) > 0]
            fix(rnd2(c), 'Обрывок асфальта %.0f × %.0f м на тротуаре %s (картинка v85, слой L06b_entry — старый въезд) не строится: тротуар сплошной, '
                         'серпантин VIEW B входит в N3 в точке entry N-viewB.' % ((bb(pl)[2] - bb(pl)[0]) * U, (bb(pl)[3] - bb(pl)[1]) * U, '/'.join(on) or '?'),
                'v10 §6 / §11: обрывков дорог нет, каждая дорога куда-то ведёт.')

    # curb drops (driveways) of the plan + rule-based ones
    def drop_zone(zid, r_, why):
        c = ((r_[0] + r_[2]) / 2, (r_[1] + r_[3]) / 2)
        best = None
        for bd in bands:                                                   # the street whose sidewalk the drive crosses
            ax = bd['ax']
            lo_, hi_ = sorted((bd['seg'][0][1 - ax], bd['seg'][1][1 - ax]))
            d_ = abs(c[ax] - bd['axis'])
            out_ = max(0.0, lo_ - c[1 - ax], c[1 - ax] - hi_)               # beyond the segment end (inside the junction)
            if out_ <= HW and d_ <= HW + 4 and (best is None or (out_, d_) < best[0]):
                best = ((out_, d_), bd)
        assert best, ('curb drop without a street', zid)
        bd = best[1]
        ax = bd['ax']
        side = 1 if c[ax] > bd['axis'] else -1
        q = list(r_)
        q[ax], q[ax + 2] = sorted((bd['axis'] + side * CW, bd['axis'] + side * HW))   # across the sidewalk: curb -> facade line
        r_ = tuple(q)
        zones.append({'id': zid, 'kind': 'curb_drop', 'poly': ccw(WL(R(*r_))), 'for': why, 'street': bd['street'], 'surface': 'asphalt_old_SK2a',
                      'curb_m': 0.0, 'w_m': round((r_[3 - ax] - r_[1 - ax]) * U, 1), 'depth_m': WALK})

    labelled = {'42': '05-42', '43': '05-43', '13': '05-13'}
    for i, d in enumerate(dws):
        r_ = bb(d)
        c = pcen(d)
        why = 'drive'
        for a in alley_out:
            if abs(c[a['cax']] - a['c']) < 1 and blk_of(model, c, 30.0) == a['block']:
                why = 'alley %s mouth' % a['block']
        if why == 'drive':
            near = min(labels.items(), key=lambda kv: math.hypot(kv[1][0] - c[0], kv[1][1] - c[1]))[0]
            why = {'42': 'service yard 42 entry', '43': 'service yard 43 entry', '13': 'BASE 4 arch entry from Hse2', '07': 'van shop 07 gates'}.get(near, 'drive')
            if near == '13':                                               # the drop matches the arch opening
                ar = bb(arch_el)
                r_ = (ar[0], r_[1], ar[2], r_[3])
        drop_zone('05-drop-%02d' % i, r_, why)
    for e in sel(els, g='buildings', tag='polygon', fill='#6E757A'):                    # parking ramps
        r_ = bb(e['pts'])
        top = r_[1]
        bd = min((bd for bd in bands if bd['ax'] == 1 and bd['rect'][0] <= (r_[0] + r_[2]) / 2 <= bd['rect'][2]), key=lambda bd: abs(bd['rect'][3] - top))
        drop_zone('05-drop-ramp-%s' % bd['street'], (r_[0], bd['axis'] + CW, r_[2], bd['rect'][3]), 'parking 03 ramp from %s' % bd['street'])
    canopy = bb(sel(els, g='buildings', tag='polygon', fill='#E8E2D2')[0]['pts'])
    gl = bb(gas_lot)
    bdB = next(bd for bd in bands if bd['street'] == 'B' and bd['ax'] == 1 and bd['rect'][0] <= gl[0] <= bd['rect'][2])
    for j_, x in enumerate((canopy[0] + 5, canopy[2] - 45)):
        drop_zone('05-drop-41-%d' % j_, (x, bdB['axis'] + CW, x + 40, bdB['rect'][3]), 'gas station 41 %s (from B)' % ('in' if j_ == 0 else 'out'))
    taxi_lot = sel(els, g='squares_and_lots', fill='#C3C9CD')[0]['pts']
    tl = bb(taxi_lot)
    bdVd = next(bd for bd in bands if bd['street'] == 'Vd' and bd['rect'][1] <= (tl[1] + tl[3]) / 2 <= bd['rect'][3])
    yc = (tl[1] + tl[3]) / 2
    drop_zone('05-drop-12', (bdVd['axis'] + CW, yc - 20, tl[0], yc + 20), 'taxi stand 12 exit onto Vd')
    if PLAN == 'v37':                                                      # beach lots (district 09, perpendicular stalls straight off SP)
        for k_, (x0_, x1_) in enumerate(V37_BEACH_LOTS):
            drop_zone('05-drop-beach-lot-%s' % 'WE'[k_], (x0_, 1480.0 + CW, x1_, 1480.0 + HW),
                      'beach parking lot %s of district 09 (moved 54 m south with the city): stalls straight off SP' % 'WE'[k_])

    # plaza "Water Axis" (04) and parking 03
    plaza_drawn = sel(els, g='squares_and_lots', tag='polygon', fill='#D9D2C4')[0]['pts']
    plaza = model['blocks']['SQ']['poly']
    gap = (bb(plaza_drawn)[0] - bb(plaza)[0]) * U
    if gap > 0.3:
        fix(rnd2(pcen(plaza)), 'Площадь 04: плитка доведена до тротуаров (на плане между плиткой и тротуаром полоса «двора» %.1f м по всему краю).' % gap,
            'Генератор v28 ужал контур площади дважды (уже ужатый квартал SQ ещё раз через MPP) — это артефакт рисования, а не задумка.')
    zones.append({'id': '05-04-plaza', 'kind': 'plaza', 'poly': ccw(WL(plaza)), 'surface': 'plaza_M3', 'label': '04',
                  'notes': '1 x 1 m slabs of one warm grey-beige tone, joints barely visible, NO pattern; dark stone band 0.5 m only along the edge, '
                           'round the pool and the monument podium; pedestrian, no trees (v02 §8.5); van can drive on it (curb ramps at the boulevard)'})
    stairs = [e['pts'] for e in sel(els, g='squares_and_lots', tag='polyline', stroke='#CFC6B4')]
    sx0, sx1 = min(p[0] for s in stairs for p in s), max(p[0] for s in stairs for p in s)
    sy0, sy1 = min(p[1] for s in stairs for p in s), max(p[1] for s in stairs for p in s)
    podium = next(b for b in blds if b['kind'] == 'podium')
    py1 = bb(podium['pl'])[3]
    zones.append({'id': '05-04-stair', 'kind': 'stair', 'poly': ccw(WL(R(sx0, py1, sx1, sy1 + 1.0))), 'steps': 5, 'step_h_m': 0.45,
                  'rise_m': 2.25, 'surface': 'plaza_M3', 'climb_dir_deg': 90.0,
                  'notes': 'tribune steps, NPC sit on them; climbs from the plaza (south) to the podium lobby terrace; not drivable (v10 §4)'})
    wat = sorted(sel(els, g='squares_and_lots', tag='polygon', fill='#7FB3D0'), key=lambda e: parea(e['pts']))
    zones.append({'id': '05-04-cascade', 'kind': 'water_cascade', 'poly': ccw(WL(wat[0]['pts'])), 'notes': 'water steps down the middle of the stair into the pool'})
    band_ = sel(els, g='squares_and_lots', tag='polygon', fill='#8A8378')[0]['pts']
    zones.append({'id': '05-04-pool', 'kind': 'pool', 'poly': ccw(WL(wat[1]['pts'])), 'edge_poly': ccw(WL(band_)), 'depth_m': 0.3, 'edge_m': 1.2,
                  'surface': 'pool_tile', 'notes': 'mirror pool 16 x 60 m, ~30 cm: the van drives in with splashes and brakes (v02 §8.5)'})
    mon = sel(els, g='squares_and_lots', tag='circle', fill='#8A8378')[0]
    jets = sel(els, g='buildings', tag='circle', fill='#DDEFF5')
    jr = sum(math.hypot(e['c'][0] - mon['c'][0], e['c'][1] - mon['c'][1]) for e in jets) / len(jets)
    pod = sel(els, g='buildings', tag='circle', r=22.0)[0]
    zones.append({'id': '05-15-monument-ring', 'kind': 'dry_fountains', 'centre': rnd2(W(mon['c'])), 'podium_d_m': round(2 * pod['r'] * U, 2),
                  'jets_r_m': round(jr * U, 2), 'jets': len(jets), 'edge_r_m': round(mon['r'] * U, 2),
                  'notes': 'jets come out of the paving, people walk and the van drives over them; dark stone band at R edge'})
    pk = sel(els, g='buildings', tag='polygon', fill='none', stroke='#2F3A42')[0]['pts']
    ramps = [e['pts'] for e in sel(els, g='buildings', tag='polygon', fill='#6E757A')]
    zones.append({'id': '05-03-parking', 'kind': 'underground_parking', 'poly': ccw(WL(pk)), 'levels': 1, 'deck_m': -4.5, 'clear_h_m': 3.0,
                  'ramps': [ccw(WL(r_)) for r_ in ramps], 'ramp_slope_max': 0.15, 'surface': 'concrete_SK3c', 'label': '03',
                  'notes': 'one level under the podium and both towers: aisles, marked bays both sides, columns, dim light, a few cars; two identical two-way ramps; '
                           'the van drives in and turns inside. The drawn ramp mouths are 11-16 m long: the descent continues under the podium (~30 m in total) to keep <= 15 %'})
    fix(rnd2(pcen(ramps[1])), 'Рампы паркинга 03: на плане открытая часть 11–16 м — спуск продолжен под подиумом (~30 м всего, уклон ≤ 15 %).',
        'На глубину одного уровня (~4,5 м) 11–16 м дают уклон 30–40 % — бусик не заедет; вход рампы оставлен где нарисован.')
    scr = bb(sel(els, g='buildings', tag='polygon', fill='#1E2A36')[0]['pts'])
    props.append({'id': '05-35-screen', 'kind': 'big_screen', 'pos': rnd2(W(((scr[0] + scr[2]) / 2, (scr[1] + scr[3]) / 2))), 'rot_deg': 270.0,
                  'size': [round((scr[2] - scr[0]) * U, 1), 0.6, 8.0], 'grip_anchor': False, 'label': '35', 'notes': 'faces south onto the plaza, on the podium'})
    # monument, booth, ATM, benches, flags, lamps, food trucks, umbrellas, bollards, bus stop
    statue = sel(els, g='buildings', tag='circle', fill='#D9B13B')[0]
    props.append({'id': '05-15-monument', 'kind': 'monument_tramduro', 'pos': rnd2(W(statue['c'])), 'rot_deg': 270.0, 'size': [4.8, 4.8, 12.0],
                  'grip_anchor': False, 'label': '15', 'notes': 'golden cartoon figure with a raised arm on a granite podium D 8.8 m (3 steps); faces the boulevard'})
    for fill_, kid, kind, size, lab in (('#5B6E8C', '05-36-booth', 'police_booth', [3.2, 3.2, 3.0], '36'), ('#2F5D8A', '05-08-atm', 'atm', [1.0, 1.0, 2.0], '08')):
        e = sel(els, g='buildings', tag='polygon', fill=fill_)[0]
        props.append({'id': kid, 'kind': kind, 'pos': rnd2(W(pcen(e['pts']))), 'rot_deg': 0.0, 'size': size, 'grip_anchor': False, 'label': lab})
    for i, e in enumerate(sel(els, g='buildings', tag='circle', fill='#B07A4A')):
        props.append({'id': '05-04-bench%d' % (i + 1), 'kind': 'round_bench_flowerbed', 'pos': rnd2(W(e['c'])), 'rot_deg': 0.0,
                      'size': [round(2 * e['r'] * U, 1), round(2 * e['r'] * U, 1), 0.5], 'grip_anchor': True, 'notes': 'wooden round bench, flowerbed inside, no tree'})
    for i, e in enumerate(sel(els, g='buildings', tag='circle', fill='#2F3A42')):
        props.append({'id': '05-04-flag%d' % (i + 1), 'kind': 'flagpole', 'pos': rnd2(W(e['c'])), 'rot_deg': 0.0, 'size': [0.3, 0.3, 12.0], 'grip_anchor': True,
                      'notes': 'flag without text or logo'})
    for i, e in enumerate(sel(els, g='objects', tag='circle', fill='#FFFDF4')):
        props.append({'id': '05-04-lamp%d' % (i + 1), 'kind': 'lamp_tall', 'pos': rnd2(W(e['c'])), 'rot_deg': 0.0, 'size': [0.4, 0.4, 9.0], 'grip_anchor': True})
    for i, e in enumerate(sel(els, g='buildings', tag='polygon', fill='#C8503F')):
        r_ = bb(e['pts'])
        props.append({'id': '05-04-foodtruck%d' % (i + 1), 'kind': 'food_truck', 'pos': rnd2(W(pcen(e['pts']))), 'rot_deg': 0.0,
                      'size': [round((r_[2] - r_[0]) * U, 1), round((r_[3] - r_[1]) * U, 1), 3.0], 'grip_anchor': False})
    for i, e in enumerate(sel(els, g='buildings', tag='circle', fill='#E9D37A')):
        props.append({'id': '05-pav-umbrella%d' % (i + 1), 'kind': 'umbrella_yellow', 'pos': rnd2(W(e['c'])), 'rot_deg': 0.0, 'size': [2.8, 2.8, 2.6],
                      'grip_anchor': False, 'notes': 'pavilion terrace: table + chairs under it'})
    bol = sorted((e['c'] for e in sel(els, g='buildings', tag='circle', fill='#3C3E42', r=2.2)), key=lambda c: c[0])
    zones.append({'id': '05-04-bollards-B', 'kind': 'bollard_row', 'line': WL([bol[0], bol[-1]]), 'count': len(bol),
                  'spacing_m': round((bol[-1][0] - bol[0][0]) / (len(bol) - 1) * U, 2), 'grip_anchor': True,
                  'notes': 'dark bollards along the plaza edge on the boulevard (legend §3); gaps for the van ramps at the zebras'})
    bs = sel(els, g='buildings', tag='polygon', fill='#9AA7B0')[0]['pts']
    bsr = bb(bs)
    bdB2 = next(bd for bd in bands if bd['street'] == 'B' and bd['ax'] == 1 and bd['rect'][0] <= pcen(bs)[0] <= bd['rect'][2] and bd['rect'][1] <= pcen(bs)[1] <= bd['rect'][3])
    new_y = bdB2['axis'] - CW - 15.0
    props.append({'id': '05-14-bus-stop', 'kind': 'bus_stop_shelter', 'pos': rnd2(W((pcen(bs)[0], new_y))), 'rot_deg': 0.0,
                  'size': [round((bsr[2] - bsr[0]) * U, 1), 1.6, 2.6], 'grip_anchor': True, 'label': '14', 'notes': 'shelter + bench + bus-stop sign; bus waits at the curb'})
    fix(rnd2(pcen(bs)), 'Остановка 14: на плане навес стоит на краю проезжей части бульвара — перенесён на северный тротуар (3 м от бордюра).',
        'После расширения улиц (v28) рисунок остановки остался на старом месте и попал на полосу движения.')

    # base 13, service yards 42 / 43
    yards = sel(els, g='squares_and_lots', tag='polygon', fill='#D8D4CA')
    bins = sel(els, g='buildings', tag='polygon', fill='#4E6B52')
    ybol = sel(els, g='buildings', tag='circle', fill='#E3B71E')
    for e in yards:
        lab = next((k for k, p in labels.items() if pin(p, e['pts']) and k in ('42', '43', '13')), None)
        if lab is None:
            lab = min(('42', '43', '13'), key=lambda k: math.hypot(labels[k][0] - pcen(e['pts'])[0], labels[k][1] - pcen(e['pts'])[1]))
        yb = bb(e['pts'])
        if lab == '13':
            court = clip_axis(e['pts'], 1, bb(arch_el)[3], False)
            if base13:                                                     # v37: 12 m court (Fedya 22.10)
                court = R(*base13)
                e = dict(e, pts=R(bb(e['pts'])[0], bb(e['pts'])[1], bb(e['pts'])[2], base13[3]))
            cb = bb(court)
            zones.append({'id': '05-13-yard', 'kind': 'yard', 'poly': ccw(WL(e['pts'])), 'court_poly': ccw(WL(court)), 'surface': 'concrete_SK3c', 'label': '13',
                          'size_m': [round((cb[2] - cb[0]) * U, 1), round((cb[3] - cb[1]) * U, 1)], 'closed': True, 'visible_from_street': False,
                          'loading_pad': True, 'notes': 'BASE 4 courtyard: closed on all sides (arch house N, garage W, house E, blind brick wall S), '
                                                        'van stops at the roll shutter; bins (green, blue), pallets, yellow bollards, tulip boxes, a bench, '
                                                        'AC units, fuse boxes, pipes, lamps over doors, neighbour fire escape (legend §4)'})
            wall = sel(els, g='buildings', tag='polyline', stroke='#8A4A36')[0]['pts']
            yw = cb[3] + 1.0                                               # plan draws it 2.5 u south of the court: put it on the court edge
            free = [(min(wall[0][0], wall[-1][0]), max(wall[0][0], wall[-1][0]))]
            for b in blds:                                                 # where a house back wall already closes the court, no extra wall
                r_ = bb(b['pl'])
                if r_[1] - 1.5 <= yw <= r_[3] + 0.5:
                    nf = []
                    for lo, hi in free:
                        if r_[2] <= lo or r_[0] >= hi:
                            nf.append((lo, hi))
                            continue
                        if r_[0] > lo:
                            nf.append((lo, r_[0]))
                        if r_[2] < hi:
                            nf.append((r_[2], hi))
                    free = nf
            for j_, (lo, hi) in enumerate(f_ for f_ in free if f_[1] - f_[0] > 2.5):
                zones.append({'id': '05-13-wall%d' % (j_ + 1), 'kind': 'wall', 'line': WL([(lo, yw), (hi, yw)]), 'h_m': 4.0, 'w_m': 0.4, 'material': 'brick_SK3a',
                              'notes': 'blind brick wall closing the courtyard to the south where no house back wall does (legend §4)'})
            zones.append({'id': '05-13-arch', 'kind': 'arch', 'poly': ccw(WL(R(*bb(arch_el)))), 'clear_w_m': round((bb(arch_el)[2] - bb(arch_el)[0]) * U, 2), 'clear_h_m': 4.5,
                          'notes': 'drive-through arch under the house, from Hse2 (curb drop 05-drop-*)'})
            ycap = court
            courtd = (cb[3] - cb[1]) * U
            if PLAN == 'v31':
              question('База 4 (13): после расширения улиц до 22 м (план v28) двор-колодец ужался до %.1f × %.1f м (утверждено ~28 × 9 м; v10 §4 — дворы и '
                     'места погрузки от 12–15 м, чтобы развернуться). Бусик проезжает арку, встаёт к рольставне, выезжает задом или в 2–3 приёма.'
                     % ((cb[2] - cb[0]) * U, courtd),
                     ['1 — как на плане: двор %.1f м в глубину (сейчас в данных)' % courtd,
                      '2 — двор 12 м в глубину: ряд домов к набережной S1 становится мельче на %.1f м' % (12.0 - courtd)], 1, 'данные: вариант 1')
            else:
                zones[-1]['notes'] += ' | v37 (Fedya 22.10): court %.1f x %.1f m, the van turns inside (3-point)' % ((cb[2] - cb[0]) * U, courtd)
        else:
            zones.append({'id': '05-%s-yard' % lab, 'kind': 'service_yard', 'poly': ccw(WL(e['pts'])), 'surface': 'concrete_SK3c', 'label': lab,
                          'size_m': [round((yb[2] - yb[0]) * U, 1), round((yb[3] - yb[1]) * U, 1)], 'loading_pad': True,
                          'notes': 'wide service yard open to the street: bins, roll-shutter gate, yellow bollards (legend §5)'})
        for i, bn in enumerate(x for x in bins if pin(pcen(x['pts']), e['pts'])):
            r_ = bb(bn['pts'])
            props.append({'id': '05-%s-bin%d' % (lab, i + 1), 'kind': 'dumpster' if lab != '13' else ('bin_green' if i == 0 else 'bin_blue'),
                          'pos': rnd2(W(pcen(bn['pts']))), 'rot_deg': 0.0 if (r_[2] - r_[0]) > (r_[3] - r_[1]) else 90.0,
                          'size': [round(max(r_[2] - r_[0], r_[3] - r_[1]) * U, 1), round(min(r_[2] - r_[0], r_[3] - r_[1]) * U, 1), 1.3], 'grip_anchor': False})
        for i, c in enumerate(x['c'] for x in ybol if pin(x['c'], e['pts']) or min(abs(x['c'][0] - q[0]) + abs(x['c'][1] - q[1]) for q in e['pts']) < 12):
            props.append({'id': '05-%s-bollard%d' % (lab, i + 1), 'kind': 'bollard_yellow', 'pos': rnd2(W(c)), 'rot_deg': 0.0, 'size': [0.3, 0.3, 1.0], 'grip_anchor': True})
    pal = sel(els, g='buildings', tag='polygon', fill='#B08D5E')[0]['pts']
    props.append({'id': '05-13-pallets', 'kind': 'pallet_stack', 'pos': rnd2(W(pcen(pal))), 'rot_deg': 0.0, 'size': [2.2, 2.4, 1.2], 'grip_anchor': False})

    # alleys
    neb_court = None
    if PLAN == 'v37' and V37_NEB_COURT:
        a_ = next(a for a in alley_out if a['block'] == 'NEB')
        neb_court = min(a_['rects'], key=lambda r_: r_[1])                 # north part, mouth on N0e
        a_['rects'] = [r_ for r_ in a_['rects'] if r_ is not neb_court]
        a_['mouths'] = [m_ for m_ in a_['mouths'] if m_['rect'] is not neb_court]
        a_['pair'] = False
    alley_bins = [x for x in bins if any(pin(pcen(x['pts']), R(*a['rect0'])) for a in alleys)]
    for a in alley_out:
        cax, aax = a['cax'], a['aax']
        whole = [0, 0, 0, 0]
        whole[cax], whole[cax + 2], whole[aax], whole[aax + 2] = a['lo'], a['hi'], min(r_[aax] for r_ in a['rects']), max(r_[aax + 2] for r_ in a['rects'])
        ends = []
        for r_ in a['rects']:
            m_ = next((m for m in a['mouths'] if m['rect'] == r_), None)
            st_name = None
            if m_:
                for bd in bands:                                           # the street whose facade line the mouth stands on (band range checked)
                    rr_ = bd['rect']
                    if (abs(abs(bd['axis'] - m_['pos'][bd['ax']]) - HW) < 1.0 and rr_[0] - 1 <= m_['pos'][0] <= rr_[2] + 1
                            and rr_[1] - 1 <= m_['pos'][1] <= rr_[3] + 1):
                        st_name = bd['street']
            ends.append({'poly': ccw(WL(R(*r_))), 'length_m': round((r_[aax + 2] - r_[aax]) * U, 1), 'mouth': rnd2(W(m_['pos'])) if m_ else None,
                         'mouth_street': st_name, 'facing_deg': facing(tuple(float(m_['dir']) if i == aax else 0.0 for i in (0, 1))) if m_ else None})
        z = {'id': a['id'], 'kind': 'dead_end_alley_pair' if a['pair'] else 'dead_end_alley', 'poly': ccw(WL(R(*whole))), 'width_m': ALLEY * U,
             'surface': 'asphalt_old_SK2a', 'dead_ends': ends, 'width_plan_m': round(a['w0_m'], 2),
             'dressing': 'dark asphalt, dumpsters, fire escapes, back doors, puddles, blind wall at the end, dim lamp over a back door',
             'notes': 'both ends open to a street, plug house in the middle -> two dead ends (v02 §8.5)' if a['pair'] else 'single blind alley (v10 §7.5: NW1 / SW2), one mouth'}
        if a['plugs']:
            z['plug_wall'] = ccw(WL(a['plugs'][0]['pl']))
            z['plug_building'] = next(b['id'] for b in blds if b is a['plugs'][0])
        zones.append(z)
        for i, bn in enumerate(x for x in alley_bins if pin(pcen(x['pts']), R(*whole))):
            c = list(pcen(bn['pts']))
            r_ = bb(bn['pts'])
            dpt = min(r_[2] - r_[0], r_[3] - r_[1])
            c[cax] = a['lo'] + dpt / 2 + 2.0                               # keep the bin against the (moved) alley wall
            props.append({'id': '%s-bin%d' % (a['id'], i + 1), 'kind': 'dumpster', 'pos': rnd2(W(c)), 'rot_deg': 0.0 if aax == 0 else 90.0,
                          'size': [round(max(r_[2] - r_[0], r_[3] - r_[1]) * U, 1), round(dpt * U, 1), 1.3], 'grip_anchor': False})

    if neb_court:
        x0_, y0_, x1_, y1_ = neb_court                                    # plan: y0_ = N0e facade line (north), y1_ = plug face
        gw = (x1_ - x0_) * U
        zones[:] = [z for z in zones if not (z['kind'] == 'curb_drop' and z.get('street') == 'N0e' and 'NEB' in z.get('for', ''))]
        zones.append({'id': '05-NEB-courtyard', 'kind': 'courtyard', 'poly': ccw(WL(R(*neb_court))), 'surface': 'cobble_SK2c', 'closed': True,
                      'van_access': False, 'size_m': [round(gw, 1), round((y1_ - y0_) * U, 1)],
                      'gate': {'pos': rnd2(W(((x0_ + x1_) / 2, y0_ + 2.0))), 'facing_deg': 90.0, 'w_m': round(gw, 1)},
                      'notes': 'Fedya 22.10 (item 9): the north dead end of the NEB alley is closed by decorative gates (not a house) and becomes a '
                               'closed courtyard of the houses around it: paving, trimmed hedges along both walls, bench, lamp over a back door; '
                               'no dumpsters, no van. The VIEW C cornice road meets N0e right opposite the gate (clean T, no 2-4 m jog). '
                               'The south dead end (from N3b) stays a service alley.'})
        gy = y0_ + 2.0                                                     # gate line 0.4 m inside the facade line
        props.append({'id': '05-NEB-gate', 'kind': 'courtyard_gate', 'pos': rnd2(W(((x0_ + x1_) / 2, gy))), 'rot_deg': 0.0,
                      'size': [round(gw - 1.2, 2), 0.25, 2.4], 'grip_anchor': True, 'leaves': 2, 'material': 'wrought_iron_black',
                      'closed': True, 'notes': 'decorative double gate (black wrought iron, arched top, no text), closed; between two brick piers'})
        for k_, xp in enumerate((x0_ + 1.5, x1_ - 1.5)):
            props.append({'id': '05-NEB-gate-pier%d' % (k_ + 1), 'kind': 'gate_pier', 'pos': rnd2(W((xp, gy))), 'rot_deg': 0.0, 'size': [0.6, 0.6, 2.8],
                          'grip_anchor': True, 'material': 'brick_SK3a', 'notes': 'brick pier with a stone cap and a lantern'})
        hl = 14.0                                                          # 2.8 m flanking hedges on the sidewalk, against the corner houses
        for k_, (xa, xb) in enumerate(((x0_ - hl, x0_), (x1_, x1_ + hl))):
            props.append({'id': '05-NEB-hedge-out%d' % (k_ + 1), 'kind': 'hedge_trimmed', 'pos': rnd2(W(((xa + xb) / 2, y0_ - 2.5))), 'rot_deg': 0.0,
                          'size': [round((xb - xa) * U, 1), 0.8, 1.1], 'grip_anchor': False, 'style': 'boxwood, flat top, sharp corners, low planter kerb',
                          'notes': 'flanks the courtyard gate on the sidewalk, along the facade of the corner house (sidewalk stays >= 4.2 m)'})
        for k_, xc in enumerate((x0_ + 2.75, x1_ - 2.75)):
            props.append({'id': '05-NEB-hedge-in%d' % (k_ + 1), 'kind': 'hedge_trimmed', 'pos': rnd2(W((xc, (y0_ + 6 + y1_) / 2))), 'rot_deg': 90.0,
                          'size': [round((y1_ - y0_ - 6) * U, 1), 0.9, 1.2], 'grip_anchor': False, 'style': 'boxwood, flat top, sharp corners',
                          'notes': 'lines the courtyard wall from the gate to the end wall; leaves a %.1f m paved walk in the middle' % (gw - 2 * 1.1)})
        props.append({'id': '05-NEB-bench', 'kind': 'bench', 'pos': rnd2(W(((x0_ + x1_) / 2, y1_ - 8))), 'rot_deg': 0.0, 'size': [1.8, 0.6, 0.9], 'grip_anchor': True})
        fix(pcen(R(*neb_court)), 'Решение Феди 22.10 (п. 9): северный тупик переулка NEB (напротив стыка карниза VIEW C с N0e) закрыт декоративными воротами — '
                                 'закрытый дворик с подстриженными изгородями по обе стороны; понижение бордюра на N0e убрано, тротуар сплошной.',
            'стык VIEW C остаётся на оси переулка; погоня не уводит бусик в тупик.')
    for i, gp in enumerate(gaps37):                                         # v37 separation gaps (real, 1.5-2.5 m)
        zones.append({'id': '05-gap-%02d' % (i + 1), 'kind': 'side_gap', 'poly': ccw(WL(R(*gp['rect']))), 'w_m': gp['w_m'], 'between': gp['between'],
                      'street': gp['street'], 'surface': 'concrete_SK3c',
                      'closure': {'street': 'iron gate / railing 2.2 m on the facade line (no hiding hole, no shortcut)', 'back': 'blind wall or the alley'},
                      'notes': 'visible separation between two row houses (Fedya 22.10); %s shortened by the gap' % gp['shortened']})
    # squares 20 / 23 (the only trees of Downtown), pond, paths
    parks = sel(els, g='squares_and_lots', tag='polygon', fill='#CFE0B5')
    pond = sel(els, g='squares_and_lots', tag='polygon', fill='#8FC3D9')[0]['pts']
    paths = [e['pts'] for e in sel(els, g='squares_and_lots', tag='polyline', stroke='#E9DFC6')]
    for e in parks:
        lab = next(k for k in ('20', '23') if pin(labels[k], e['pts']))
        has_pond = pin(pcen(pond), e['pts'])
        zones.append({'id': '05-%s-square' % lab, 'kind': 'park', 'poly': ccw(WL(e['pts'])), 'surface': 'lawn', 'label': lab,
                      'notes': 'city square: lawn, paths, benches with bins, lamps' + ('; pond with a stone edge' if has_pond else '')})
        zones.append({'id': '05-%s-veg' % lab, 'kind': 'veg_zone', 'poly': ccw(WL(e['pts'])), 'density': 'grove', 'species': 'leafy',
                      'target_count': 3 if has_pond else 4, 'groups': '2-5 trees', 'min_gap_path_m': 2.0,
                      'notes': 'Downtown trees ONLY here and in the other square (v10 §7.5, ~7 per district); keep off the paths and the pond'})
        for pth in paths:
            if pin(pth[len(pth) // 2], e['pts']) or any(pin(q, e['pts']) for q in pth[1:-1]):
                zones.append({'id': '05-%s-path%d' % (lab, sum(1 for z in zones if z['id'].startswith('05-%s-path' % lab)) + 1), 'kind': 'path',
                              'line': WL(pth), 'width_m': 2.8, 'surface': 'sidewalk_S1', 'closed': math.hypot(pth[0][0] - pth[-1][0], pth[0][1] - pth[-1][1]) < 1})
        if has_pond:
            zones.append({'id': '05-%s-pond' % lab, 'kind': 'pond', 'poly': ccw(WL(pond)), 'depth_m': 0.6, 'edge': 'stone'})

    # gas station 41, taxi stand 12
    pumps = sel(els, g='buildings', tag='polygon', fill='#C8372D')
    zones.append({'id': '05-41-forecourt', 'kind': 'gas_station', 'poly': ccw(WL(gas_lot)), 'surface': 'concrete_SK3c', 'label': '41',
                  'canopy': ccw(WL(R(*canopy))), 'canopy_clear_h_m': 5.0, 'notes': 'forecourt (not a parking lot): canopy over 3 pump islands, shop at the back, '
                                                                                   'entries from the boulevard (curb drops 05-drop-41-*)'})
    for i, e in enumerate(pumps):
        props.append({'id': '05-41-pump%d' % (i + 1), 'kind': 'fuel_pump_island', 'pos': rnd2(W(pcen(e['pts']))), 'rot_deg': 90.0, 'size': [1.2, 2.4, 1.9], 'grip_anchor': True})
    zones.append({'id': '05-12-stand', 'kind': 'taxi_stand', 'poly': ccw(WL(taxi_lot)), 'surface': 'asphalt_A5d12', 'label': '12',
                  'stalls': len(sel(els, g='squares_and_lots', tag='polyline', stroke='#F4F4F0')) - 1, 'stall_dir': 'perpendicular to Vd',
                  'notes': 'taxi depot stand (the only surface parking besides gas 41; v10 §7.5), exit onto Vd'})

    # legend objects
    for lab, p in sorted(labels.items()):
        props.append({'id': '05-L' + lab, 'kind': 'legend_object', 'label': lab, 'pos': rnd2(W(p)), 'desc': LEGEND.get(lab, ''),
                      'notes': 'label position of the plan (marker, not geometry)'})

    # district ground, no-tree, pads
    dist = model['district']
    def offset_rect_poly(pl, d):                                           # rectilinear miter offset (outward for y-south ccw-in-plan)
        n = len(pl)
        sgn = 1 if sum(pl[i - 1][0] * pl[i][1] - pl[i][0] * pl[i - 1][1] for i in range(n)) > 0 else -1
        out = []
        for i in range(n):
            a, p, b = pl[i - 1], pl[i], pl[(i + 1) % n]
            def nrm(u, v):
                L = math.hypot(v[0] - u[0], v[1] - u[1])
                return (-(v[1] - u[1]) / L * sgn, (v[0] - u[0]) / L * sgn)
            n1, n2 = nrm(a, p), nrm(p, b)
            out.append((p[0] + (n1[0] + n2[0]) * d - (n1[0] * n2[0] * 0) , p[1] + (n1[1] + n2[1]) * d))
        return out
    test = offset_rect_poly(dist, 10)
    if parea(test) < parea(dist):
        offset_rect_poly_ = lambda pl, d: offset_rect_poly(pl, -d)
    else:
        offset_rect_poly_ = offset_rect_poly
    outer = offset_rect_poly_(dist, HW + 10)                               # outer sidewalk edge + 2 m
    zones.append({'id': '05-ground', 'kind': 'ground', 'poly': ccw(WL(outer)), 'surface': 'concrete_SK3c', 'flat': True,
                  'notes': 'Downtown pad (Rough height, v10 §3.1): streets / sidewalks / plaza / yards on top; unbuilt block interiors = concrete; '
                           'meadow outside blends over 40-80 m (v10 §9)'})
    for nm_ in (('OB1', 'NEX') if PLAN == 'v31' else ()):
        r_ = model['blocks'][nm_]['new']
        zones.append({'id': '05-ground-' + nm_, 'kind': 'ground', 'poly': ccw(WL(R(r_[0] - 10, r_[1] - 10, r_[2] + 10, r_[3] + 10))), 'surface': 'concrete_SK3c',
                      'flat': True, 'notes': 'pad of the stopper houses outside the ring bend'})
    zones.append({'id': '05-no-tree-default', 'kind': 'no_tree', 'poly': ccw(WL(outer)), 'veg_zones_override': True,
                  'why': 'Downtown: trees ONLY inside squares 20 and 23 (veg_zone polygons of this file); never on streets, sidewalks, the plaza, yards, alleys '
                         '(v10 §7.5); the 2 m margin outside the ring sidewalk keeps the meadow trees off the curb'})
    fix(None, 'Деревья: в Даунтауне только скверы 20 и 23 (veg_zone); остальной район и 2 м за внешним тротуаром кольца — no_tree. Деревья картинки v85 '
              'на улице над Даунтауном и у базы 4 справа снизу в данные не попадают.', 'v10 §7.5: Вадим ругался на деревья на дороге сверху Даунтауна и у базы 4.')
    if PLAN == 'v31':
        fix(None, 'Улицы Va2 и Vds южнее S1 (на плане — мосты через бывший канал) не строятся: улица кончается на S1, дальше — съезд на песок пляжа '
                  '(зона entry S-Va2 / S-Vds, понижение бордюра на южном тротуаре S1).', 'Канала у города нет с v38 (v02 §5); пляж — район 09.')
    else:
        fix(None, 'План v37: пляж (район 09) сдвинут на 54 м южнее как есть с карты v85; город связан с ним как на v85 — южный тротуар набережной SP = '
                  'верх пальмового парка, въезды бусика на песок (x как на v85) и две парковки — с южной стороны SP (понижение бордюра), площадь у пирса — '
                  'пешеходная. Улицы нового нижнего ряда (Vp1-Vp4) стоят со сдвигом к сетке выше и к въездам пляжа — сквозного прострела нет.',
            'Вадим 22.10 (подпись к v37): «пляж один в один с общей карты v85, только на 54 м ниже»; v10 §6 / §7.5.')
    fix(None, 'Гидранты, фонари, знаки «стоп», светофоры и лавки плана не переносятся точками: вместо них зоны перекрёстков (control, зебры только у бульвара) '
              'и улицы с шириной — их расставляет шаг s06 по v10 §8.', 'v10 §1.2 и §8: мелкие детали по правилам, не по точкам картинки.')

    # ------------------------------------------------ questions (approved-decision level)
    if PLAN == 'v31':
        question('Высоты стеклянных зданий не заданы ни легендой, ни v10: круглая угловая башня (у 43) и офисы 05/06.',
                 ['1 — башня 24 эт. (~86 м), офисы 10 эт. (~36 м) — по длине тени на плане (сейчас в данных)', '2 — башня 16 эт., офисы 8 эт. (ниже, чтобы близнецы доминировали сильнее)'],
                 1, 'данные: вариант 1')
    else:
        fix(None, 'Ответы Феди 22.10 (вопросы W86 8-12): выезд тоннеля — Т на N0w (как сейчас); VIEW C — напротив переулка NEB, его северный тупик закрыт '
                  'воротами-двориком с изгородями; 8 щелей между домами оставлены; офисы — только 05 и 06 (остальные дома жилые); двор базы 4 — 12 м.',
            'docs: Working/Reviews/MapW86_Questions_2026-10-22/ANSWERS_FEDYA_2026-10-22.md')
    tun = next(z for z in entries if z['id'].endswith('N-tunnel'))
    eli = next(z for z in entries if z['id'].endswith('-E'))
    if PLAN == 'v31':
        fix(Winv(tun['pos']), 'Въезд из тоннеля: на картинке дорога входит в угол N2 / Vn наискосок, в %.1f м западнее оси Vn — точка входа в данных на оси Vn '
                              '(продолжение улицы), последние 15–20 м дороги мира выпрямить по ней.' % abs(tun.get('world_road_lateral_offset_m', 0.0)),
            'v10 §6: примыкание под прямым углом, прямой подход 10–20 м, ось боковой дороги доходит до оси главной.')
    else:
        fix(Winv(tun['pos']), 'План v37: город вырос на 50-60 м на север, старый южный портал тоннеля (871.9, 492.3) оказался внутри квартала NW0. Ось тоннеля '
                              'не трогаем, южный портал переносится вверх по оси (~74 м, к новому подножию холма B), выезд — Т-примыкание к новой верхней улице '
                              'N0w в x %.0f (%.0f м от угла кольца): плавный поворот R >= ~20 м + прямой подход 15 м (s02).'
                              % (W((V37_ENTRY_X['N-tunnel'], 0))[0], (V37_ENTRY_X['N-tunnel'] - 100.0) * U),
            'v10 §6: примыкание под прямым углом, прямой подход 10–20 м; на картинке v37 въезда нет — вопрос Вадиму в отчёте.')
        fix(None, 'План v37: серпантин VIEW B и карниз VIEW C начинаются на новом верхнем кольце (N0c x %.0f, N0e x %.0f); их старые концы (N3 у OB1, '
                  'верх E1) теперь внутри города.' % (W((V37_ENTRY_X['N-viewB'], 0))[0], W((V37_ENTRY_X['NE-viewC'], 0))[0]),
            'v10 §6: въезды в Даунтаун — север: тоннель и серпантин VIEW B; дорога продолжается полотном до проезжей части.')
    fix(Winv(eli['pos']), 'Въезд на Элиту: ось каменной дороги на картинке на %.1f м севернее оси бульвара B — в данных вход на оси B, начало каменной дороги '
                          'сдвинуть к ней (переход асфальт → камень на краю внешнего тротуара).' % abs(eli.get('world_road_lateral_offset_m', 0.0)),
        'v10 §6: дорога продолжается полотном до проезжей части улицы, без ступеньки и излома.')

    # ------------------------------------------------ checks
    checks = {}
    worst = 0.0
    for b in blds:
        for bd in bands:
            ox, oy = overlap(bb(b['pl']), bd['rect'])
            worst = max(worst, min(ox, oy) if min(ox, oy) > 0 else 0)
    checks['max_building_intrusion_into_street_profile_m'] = round(worst * U, 2)
    checks['alley_widths_m'] = {a['id']: round((a['hi'] - a['lo']) * U, 2) for a in alley_out}
    checks['entries'] = len(entries)
    checks['facade_to_facade_m'] = (CARR + 2 * WALK)
    checks['see_through_m'] = sight_lines(blds, st, model, outer)
    pk_ = pockets(blds, model, alley_out, els, bands, [g_['rect'] for g_ in gaps37] + ([neb_court] if neb_court else []) + ([base13] if base13 else []))
    checks['unbuilt_block_pockets'] = pk_
    if PLAN == 'v37':
        PLANDATA['Winv_'] = Winv
        checks.update(v37_checks(blds, byid, adj, st, bands, model, outer, out_b, entries))
    taxi_b = next(b for b in blds if b['kind'] == 'taxi_depot')
    tb = bb(taxi_b['pl'])
    zones.append({'id': '05-yard-12', 'kind': 'yard', 'poly': ccw(WL(R(tb[0], tb[3], tb[2], model['blocks']['Ea1']['new'][3]))), 'surface': 'concrete_SK3c',
                  'notes': 'taxi depot yard behind the depot building, reached from the stand (2 taxis parked, washing spot)'})
    for i, o in enumerate(x for x in pk_ if x['area_m2'] >= 100 and x['fill'] >= 0.8):
        why = {'NEX': 'back yard of the stopper houses outside the N3 bend (faces the slope; not a parking lot)',
               'Ea1': 'taxi depot yard behind the depot building, reached from the stand'}.get(o['block'], 'inner yard of block %s' % o['block'])
        zones.append({'id': '05-yard-%s' % o['block'], 'kind': 'yard', 'poly': ccw(WL(R(*o['rect']))), 'surface': 'concrete_SK3c', 'notes': why})

    fit = measure_fit(W, Wpic, Wu2w, st, out_b, model, blds)
    lin, s_ref = info['lin'], info['s_ref']
    transform = ('plan units (x east, y south; 1 u = 0.2 m) -> Chrome render of Город_Downtown_v31.svg (width %d / viewBox %g = %.3f px/u) -> '
                 'make_downtown_world_v31 resize 1/%.1f -> downtown_v31_world.png %dx%d (1 px = 1 u) -> master <image> x %g y %g in %s (translate(2820 1000)) '
                 '-> master units = (%.1f + gx, %.1f + gy) -> pre-shift metres (%.3f + %.4f gx, %.3f - %.4f gy) -> world: %s. Net: x = %.3f + 0.2 gx, '
                 'y = %.3f - 0.2 gy (scale 1.0, no rotation; v76 used 798 + 0.99 xm / 469 - 0.99 ym for v27). Fit on the v85 render: %s'
                 % (info['pw'], info['vb'][2], info['pw'] / info['vb'][2], info['k'], info['iw'], info['ih'], info['img']['x'], info['img']['y'],
                    info['img']['group'], info['master0'][0] - 0, info['master0'][1], lin[0], lin[1], lin[2], lin[3],
                    ('rigid post-shift (%+.1f, %+.1f) m = shift_m of the district body; post_shift_v85.shift_image applies exactly this to every '
                     'Downtown pixel (it evaluates shift_m at the output point, output y <= 470 m everywhere here)' % s_ref) if RIGID else
                    'raster-consistent post-shift per point (fixed point q = p + shift_m(q))',
                    lin[0] + s_ref[0], lin[2] + s_ref[1], fit['text']))

    # ------------------------------------------------ counts + output
    houses = [r_ for r_ in out_b if r_['kind'] in ('house', 'arch_house')]
    fl_hist = {}
    for r_ in houses:
        fl_hist[r_['floors']] = fl_hist.get(r_['floors'], 0) + 1
    counts = {'buildings': len(out_b), 'houses': len(houses), 'houses_by_floors': {str(k): fl_hist[k] for k in sorted(fl_hist)},
              'corner_houses': sum(1 for r_ in out_b if r_.get('corner')), 'stopper_houses_outside_ring': sum(1 for b in blds if b['kind'] == 'house' and b['block'] in ('OB1', 'NEX')),
              'towers': sum(1 for r_ in out_b if r_['kind'] in ('tower', 'tower_round')), 'twin_towers': sum(1 for r_ in out_b if r_['kind'] == 'tower'),
              'glass_offices': sum(1 for r_ in out_b if r_['kind'] == 'glass_office'), 'pavilions': sum(1 for r_ in out_b if r_['kind'] == 'pavilion'),
              'alley_plugs': sum(1 for r_ in out_b if r_['kind'] == 'alley_plug'), 'kinds': {},
              'alleys': {'zones': len(alley_out), 'pairs': sum(1 for a in alley_out if a['pair']), 'single': sum(1 for a in alley_out if not a['pair']),
                         'dead_ends': sum(len(a['rects']) for a in alley_out)},
              'squares': len(parks), 'veg_target_trees': sum(z.get('target_count', 0) for z in zones if z['kind'] == 'veg_zone'),
              'streets': len(st), 'junctions': sum(1 for z in zones if z['kind'] == 'junction'),
              'junctions_traffic_light': sum(1 for z in zones if z['kind'] == 'junction' and z['control'] == 'traffic_light'),
              'crosswalks': sum(len(z['crosswalks']) for z in zones if z['kind'] == 'junction'), 'entries': len(entries),
              'curb_drops': sum(1 for z in zones if z['kind'] == 'curb_drop'), 'props': len(props), 'zones': len(zones),
              'entrances': sum(len(r_['entrances']) for r_ in out_b), 'fire_escapes': sum(len(r_['sockets']['fire_escape'] or []) for r_ in out_b),
              'water_tanks': sum(len(r_['sockets']['water_tank'] or []) for r_ in out_b), 'material_slots': {}}
    if PLAN == 'v37':
        counts['offices'] = sorted(r_['id'] for r_ in out_b if r_.get('type') == 'office')
        counts['offices_n'] = len(counts['offices'])
        counts['separation_gaps'] = len(gaps37)
        counts['houses_new_rows'] = recon['new_houses'] if recon else 0
        counts['stopper_houses_outside_ring'] = 0
    for r_ in out_b:
        counts['kinds'][r_['kind']] = counts['kinds'].get(r_['kind'], 0) + 1
        counts['material_slots'][r_['material_slot']] = counts['material_slots'].get(r_['material_slot'], 0) + 1
    for f in FIXES:
        wp = f.pop('where_plan')
        ru, why = f.pop('ru'), f.pop('why_ru')
        f.update({'where': rnd2(W(wp)) if wp is not None else None, 'ru': ru, 'why_ru': why})
    PLANDATA.update({'blds': blds, 'st': st, 'alleys': alley_out, 'entries': entries, 'gaps': gaps37, 'model': model, 'outer': outer, 'W': W, 'Winv': Winv,
                     'courts': [c_ for c_ in (neb_court, base13) if c_]})
    out = {'district': 'downtown', 'version': 'v85 from plan v31' if PLAN == 'v31' else 'W86 from plan v37 (Vadim 22.10, picture; rebuilt with the v31 generator)',
           'sources': ([os.path.relpath(V37_IMG, ROOT).replace(os.sep, '/') + ' (plan v37, authority for the new rows / streets)',
                        os.path.relpath(PLAN_SVG, ROOT).replace(os.sep, '/') + ' (plan v37 rebuilt by make_plan_v37)'] if PLAN == 'v37' else []) +
                      [os.path.relpath(p, ROOT).replace(os.sep, '/') for p in (PLAN_SVG_V31, PLAN_PY, PLAN_PNG, WORLD_PY)] +
                      ['ArtSource/References/Map/World_v85/VOLUNTEERS_MAP_MASTER_v85.svg (<image> downtown_v31_world.png in D05, R84_downtown_entries, R24_roads, R74_elite_ring)',
                       'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-20_v10.md §1 §4 §6 §7.5 §8 §14', 'docs/specs/MAP_BUILD_HANDOFF_FEDYA_2026-10-18_v02.md §8.5',
                       'docs/specs/DOWNTOWN_LEGEND_v26.md', 'docs/specs/DOWNTOWN_SPEC_2026-10-15_v03.md'],
           'transform': transform, 'fit': fit['data'], 'rigid': RIGID,
           'pad_height_m': 5.0, 'pad_note': 'flat pad, same height as the Rough (v10 §3.1)', 'abs_heights': False,
           'lighting': 'clear_blue_clouds', 'lighting_notes': 'juicy blue sky with clouds (v02 §6 table), light haze to the horizon, no fog in the streets',
           'street_profile': {'carriageway_m': CARR, 'sidewalk_m': WALK, 'curb_m': CURB, 'facade_to_facade_m': CARR + 2 * WALK, 'corner_radius_m': CORNER_R,
                              'surface': 'asphalt_A5d12', 'sidewalk_surface': 'sidewalk_S1', 'alley_m': ALLEY * U},
           'buildings': out_b, 'props': props, 'zones': zones, 'fixed_by_logic': FIXES, 'questions_for_vadim': QUESTIONS, 'counts': counts, 'checks': checks}
    return out, W


# ---------------------------------------------------------------- checks
FR_X, FR_Y = 120, (0 if PLAN == 'v31' else 340)                 # raster frame of the plan checks (plan units, 1 px = 1 u)
FR_W, FR_H = 2600, (1500 if PLAN == 'v31' else 1900)
PLAN_Y0, PLAN_Y1 = (0, 1265) if PLAN == 'v31' else (-245, 1535)   # city between the outer sidewalks (v31: plan top .. S1 south sidewalk)


def raster_buildings(blds, scale=1.0):
    im = Image.new('L', (int(FR_W * scale), int(FR_H * scale)), 0)
    dr = ImageDraw.Draw(im)
    for b in blds:
        dr.polygon([((p[0] + FR_X) * scale, (p[1] + FR_Y) * scale) for p in b['pl']], fill=255)
    return np.asarray(im) > 0


def sight_lines(blds, st, model, outer):
    """Straight open run (no building) along each street axis through the segment midpoint, clipped to the plan (x -60..2400,
    y 0..1265 = up to the S1 south sidewalk), metres (v10 §7.5: no see-through "hill to beach" lines)."""
    m = raster_buildings(blds)
    im = Image.new('L', (FR_W, FR_H), 0)
    ImageDraw.Draw(im).polygon([(p[0] + FR_X, p[1] + FR_Y) for p in outer], fill=255)
    m = m | ~(np.asarray(im) > 0)                                          # outside the ring = end of the city view
    res = {}
    for name, s in st.items():
        for a, b in zip(s['pts'][:-1], s['pts'][1:]):
            vert = abs(a[0] - b[0]) < 1e-6
            line_ = m[PLAN_Y0 + FR_Y:PLAN_Y1 + FR_Y + 1, int(a[0] + FR_X)] if vert else m[int(a[1] + FR_Y), 60:2520]
            c = int((a[1] + b[1]) / 2) - PLAN_Y0 if vert else int((a[0] + b[0]) / 2 + 60)
            lo = hi = min(max(c, 0), len(line_) - 1)
            while lo > 0 and not line_[lo - 1]:
                lo -= 1
            while hi < len(line_) - 1 and not line_[hi + 1]:
                hi += 1
            key = '%s@%s%d' % (name, 'x' if vert else 'y', a[0] if vert else a[1])
            res[key] = max(res.get(key, 0), round((hi - lo + 1) * U, 1))
    return dict(sorted(res.items(), key=lambda kv: -kv[1])[:10])


def pockets(blds, model, alley_out, els, bands, extra=()):
    """Unbuilt pockets inside blocks (v10 §7.5 "всё застроено"): block area minus buildings, alleys, yards, squares, lots, plaza, street profile."""
    from scipy import ndimage
    im = Image.new('L', (FR_W, FR_H), 0)
    dr = ImageDraw.Draw(im)
    T = lambda pl: [(p[0] + FR_X, p[1] + FR_Y) for p in pl]
    for k, b in model['blocks'].items():
        if k != 'SQ':                                                      # SQ = plaza (paved to the sidewalk)
            dr.polygon(T(b['poly']), fill=255)
    for bd in bands:
        dr.polygon(T(R(*bd['rect'])), fill=0)
    for b in blds:
        dr.polygon(T(b['pl']), fill=0)
    for a in alley_out:
        for r_ in a['rects']:
            dr.polygon(T(R(*r_)), fill=0)
    for e in els:
        if e['g'] == 'squares_and_lots' and e['tag'] == 'polygon' and e['fill'] not in ('none', None):
            dr.polygon(T(e['pts']), fill=0)
    for r_ in extra:
        dr.polygon(T(R(*r_)), fill=0)
    m = np.asarray(im) > 0
    m = ndimage.binary_opening(m, iterations=2)                            # ignore slivers < ~1 m
    lab, n = ndimage.label(m)
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        a_m2 = len(xs) * U * U
        if a_m2 >= 15:
            r_ = (float(xs.min()) - FR_X, float(ys.min()) - FR_Y, float(xs.max()) + 1 - FR_X, float(ys.max()) + 1 - FR_Y)
            out.append({'plan_centre': [round(float(xs.mean()) - FR_X, 1), round(float(ys.mean()) - FR_Y, 1)], 'area_m2': round(a_m2, 1),
                        'block': blk_of(model, (float(xs.mean()) - FR_X, float(ys.mean()) - FR_Y), 5), 'rect': r_,
                        'fill': round(len(xs) / ((r_[2] - r_[0]) * (r_[3] - r_[1])), 2)})
    return sorted(out, key=lambda o: -o['area_m2'])


def measure_fit(W, Wpic, Wu2w, st, out_b, model, blds):
    pts = [W(p) for s in st.values() for p in s['pts']]
    x0w, x1w = int(min(p[0] for p in pts)) - 15, int(max(p[0] for p in pts)) + 15
    y0w, y1w = int(min(p[1] for p in pts)) - 15, int(max(p[1] for p in pts)) + 25
    im = Image.open(MAP_FULL).convert('RGB').crop((x0w * 5, (950 - y1w) * 5, x1w * 5, (950 - y0w) * 5))
    a = np.asarray(im).astype(np.int16)
    road = ((np.abs(a - np.array([95, 102, 108])) <= 10).all(-1)) | (a.min(-1) >= 238)
    Hh, Ww = road.shape
    pix = lambda q: (int(round((y1w - q[1]) * 5)), int(round((q[0] - x0w) * 5)))
    jun = [p for p, n in junctions(st)]
    res = {'body': [], 'north': []}
    widths, obstructed = [], []
    for name, s in st.items():
        for a_, b_ in zip(s['pts'][:-1], s['pts'][1:]):
            L = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
            u = ((b_[0] - a_[0]) / L, (b_[1] - a_[1]) / L)
            for t in np.arange(20, L - 20, 25):
                p = (a_[0] + u[0] * t, a_[1] + u[1] * t)
                if min(math.hypot(p[0] - j[0], p[1] - j[1]) for j in jun) < 90 or p[1] > 1240 or (PLAN == 'v37' and p[1] < 150):
                    continue
                q0, q1 = W(p), W((p[0] - u[1] * 10, p[1] + u[0] * 10))
                n = ((q1[0] - q0[0]) / 2.0, (q1[1] - q0[1]) / 2.0)            # unit world normal
                prof = []
                for sv in np.arange(-10.0, 10.01, 0.2):
                    i, j = pix((q0[0] + n[0] * sv, q0[1] + n[1] * sv))
                    prof.append(bool(0 <= i < Hh and 0 <= j < Ww and road[i, j]))
                ss = np.arange(-10.0, 10.01, 0.2)
                k0 = int(np.argmin(np.abs(ss)))
                if not any(prof[max(0, k0 - 15):k0 + 16]):
                    continue
                kk = [k for k in range(len(prof)) if prof[k]]
                kc = min(kk, key=lambda k: abs(k - k0))
                lo = hi = kc
                while lo > 0 and (prof[lo - 1] or (lo > 1 and prof[lo - 2])):
                    lo -= 1
                while hi < len(prof) - 1 and (prof[hi + 1] or (hi < len(prof) - 2 and prof[hi + 2])):
                    hi += 1
                w_ = (hi - lo + 1) * 0.2
                if not 9.0 <= w_ <= 15.0:
                    continue
                if not 11.0 <= w_ <= 13.0:                                  # something drawn on the carriageway (bus stop 14)
                    obstructed.append((name, rnd2(p), round(w_, 1)))
                    continue
                cen = (ss[lo] + ss[hi]) / 2
                key = 'north' if p[1] < 150 else 'body'
                res[key].append((name, round(float(cen), 2)))

                widths.append(w_)
    house = 0
    tot = 0
    for b in blds:
        if b['kind'] not in ('house', 'arch_house', 'loft'):
            continue
        r_ = bb(b['pl'])
        if r_[1] < 150 or (PLAN == 'v37' and r_[3] > 1240):
            continue
        fp = [W(p) for p in R(r_[0] + 5, r_[1] + 5, r_[2] - 5, r_[3] - 5)]
        if r_[2] - r_[0] < 12 or r_[3] - r_[1] < 12:
            continue
        xs, ys = [p[0] for p in fp], [p[1] for p in fp]
        i0, j0 = pix((min(xs), max(ys)))
        i1, j1 = pix((max(xs), min(ys)))
        sub = a[max(0, i0):i1, max(0, j0):j1].reshape(-1, 3)
        grounds = np.array([[95, 102, 108], [227, 225, 217], [232, 238, 219], [217, 210, 196], [227, 235, 212], [157, 162, 162], [216, 212, 202], [191, 195, 196]])
        g = (np.abs(sub[:, None, :] - grounds[None, :, :]).max(-1) <= 6).any(-1)
        house += int((~g).sum())
        tot += len(g)
    body = [c for _, c in res['body']]
    north = [c for _, c in res['north']]
    allp = [p for b in blds for p in b['pl']] + [p for s in st.values() for p in s['pts']]
    if PLAN == 'v37':                                                      # new rows are not on the v85 render
        allp = [p for p in allp if 0 <= p[1] <= 1265]
    pic_dev = max(math.hypot(W(p)[0] - Wpic(p)[0], W(p)[1] - Wpic(p)[1]) for p in allp)
    u2w_dev = max((math.hypot(Wu2w(p)[0] - Wpic(p)[0], Wu2w(p)[1] - Wpic(p)[1]), p) for p in allp)
    n2 = W(st['N2']['pts'][0])
    n2u = Wu2w(st['N2']['pts'][0])
    data = {'street_axis_offset_body_m': {'n': len(body), 'median': round(float(np.median(body)), 2), 'max_abs': round(float(np.max(np.abs(body))), 2)},
            'street_axis_offset_north_band_m': {'n': len(north), 'median': round(float(np.median(north)), 2) if north else None,
                                                'max_abs': round(float(np.max(np.abs(north))), 2) if north else None},
            'carriageway_width_measured_m': {'median': round(float(np.median(widths)), 2), 'min': round(float(np.min(widths)), 2), 'max': round(float(np.max(widths)), 2)},
            'house_fill_on_house_colour': round(house / max(1, tot), 3), 'sections_obstructed': obstructed,
            'rigid_vs_raster_post_shift_max_m': round(pic_dev, 3),
            'common_u2w_vs_raster_m': {'max': round(u2w_dev[0], 2), 'at_plan': rnd2(u2w_dev[1]),
                                       'N2_axis': round(math.hypot(n2[0] - n2u[0], n2[1] - n2u[1]), 2)}}
    text = ('carriageway cross-sections on VOLUNTEERS_MAP_FINAL_v85.png (5 px/m, %d clean sections south of N1/N3): drawn axis vs data axis median %.2f m, max %.2f m; '
            'drawn carriageway width median %.1f m (12 m expected; %d sections skipped where the drawn bus stop 14 narrows the asphalt); houses (inset 1 m) %.0f %% on house colours; north band (N2 / Nj / stoppers) %d sections, '
            'max %.2f m. The raster post-shift (shift_m evaluated at the OUTPUT point) is exactly the rigid (+20, -28) for every Downtown point (max diff %.3f m); '
            'common.u2w (shift_m at the pre-shift point) would be up to %.1f m off the drawn picture in the north band (N2 axis %.1f m).'
            % (len(body), data['street_axis_offset_body_m']['median'], data['street_axis_offset_body_m']['max_abs'], data['carriageway_width_measured_m']['median'],
               len(obstructed), data['house_fill_on_house_colour'] * 100, len(north), data['street_axis_offset_north_band_m']['max_abs'] or 0, pic_dev,
               u2w_dev[0], data['common_u2w_vs_raster_m']['N2_axis']))
    return {'data': data, 'text': text}


# ---------------------------------------------------------------- check images
def draw(im, tp, d, s, full=False):
    dr = ImageDraw.Draw(im)
    for z in d['zones']:
        if z['kind'] in ('ground', 'no_tree', 'street'):
            continue
        col = (20, 140, 40) if z['kind'] == 'veg_zone' else (0, 200, 220)
        if 'poly' in z:
            dr.polygon([tp(q) for q in z['poly']], outline=col)
        if 'line' in z:
            dr.line([tp(q) for q in z['line']], fill=col, width=2)
        if z['kind'] in ('entry', 'junction'):
            x, y = tp(z['pos'])
            rr = s * (1.6 if z['kind'] == 'entry' else 0.6)
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(0, 200, 220), width=2)
            if z['kind'] == 'entry':
                dr.polygon([tp(q) for q in z['curb_drop']], outline=(0, 200, 220))
    for z in d['zones']:
        if z['kind'] == 'street':
            dr.line([tp(q) for q in z['poly_line']], fill=(0, 190, 0), width=2 if full else 1)
    for b in d['buildings']:
        dr.polygon([tp(p) for p in b['footprint']], outline=(255, 0, 0), width=2 if full else 1)
        for a in b.get('arches', []):
            dr.polygon([tp(p) for p in a['rect']], outline=(255, 140, 0))
        for e in b['entrances']:
            x, y = tp(e['pos'])
            rr = s * 0.45
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(0, 0, 255))
    for p in d['props']:
        x, y = tp(p['pos'])
        rr = s * (0.9 if p['kind'] == 'legend_object' else 0.4)
        if p['kind'] == 'legend_object':
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 0, 255), width=2)
        else:
            dr.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 0, 255))


def overlays(d):
    os.makedirs(WORK, exist_ok=True)
    xs = [p[0] for b in d['buildings'] for p in b['footprint']] + [z['pos'][0] for z in d['zones'] if z['kind'] == 'entry']
    ys = [p[1] for b in d['buildings'] for p in b['footprint']] + [z['pos'][1] for z in d['zones'] if z['kind'] == 'entry']
    x0, x1, y0, y1 = int(min(xs)) - 15, int(max(xs)) + 15, int(min(ys)) - 15, int(max(ys)) + 15
    s = 3
    im = Image.open(MAP_PREVIEW).convert('RGB').crop((x0, 950 - y1, x1, 950 - y0))
    im = im.resize((im.width * s, im.height * s), Image.NEAREST)
    draw(im, lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s), d, s)
    im.save(os.path.join(WORK, 'check_downtown.png'))
    s = 5
    im = Image.open(MAP_FULL).convert('RGB').crop((x0 * s, (950 - y1) * s, x1 * s, (950 - y0) * s))
    draw(im, lambda p: ((p[0] - x0) * s, (y1 - p[1]) * s), d, s, full=True)
    im.save(os.path.join(WORK, 'check_downtown_full.png'))


# ---------------------------------------------------------------- plan v37: checks, picture fit, report images, land file
def v37_open_runs(blds, st, outer):
    """N-S open runs (no building) along every street axis over the whole city height (outer sidewalk to outer sidewalk) and W-E runs.
    A hill-to-beach line = an open run over the whole city height that lies inside the ring (outer ring streets W1-W2 / E1-E2 run along the
    edge with meadow beside them: listed separately)."""
    m = raster_buildings(blds)
    im_ = Image.new('L', (FR_W, FR_H), 0)
    ImageDraw.Draw(im_).polygon([(p[0] + FR_X, p[1] + FR_Y) for p in outer], fill=255)
    inside_ = np.asarray(im_) > 0
    edge = []
    res_ns, res_we, hill_beach = {}, {}, []
    for name, s_ in st.items():
        for a, b in zip(s_['pts'][:-1], s_['pts'][1:]):
            if abs(a[0] - b[0]) < 1e-6:                                    # vertical segment
                for dx in (0, -25, 25):                                    # axis and both sidewalks
                    col = m[PLAN_Y0 + FR_Y:PLAN_Y1 + FR_Y + 1, int(a[0] + dx + FR_X)]
                    c = int((a[1] + b[1]) / 2) - PLAN_Y0
                    lo = hi = c
                    while lo > 0 and not col[lo - 1]:
                        lo -= 1
                    while hi < len(col) - 1 and not col[hi + 1]:
                        hi += 1
                    key = '%s@x%d%+d' % (name, a[0], dx) if dx else '%s@x%d' % (name, a[0])
                    res_ns[key] = max(res_ns.get(key, 0), round((hi - lo + 1) * U, 1))
                    if lo == 0 and hi == len(col) - 1:
                        ins = inside_[PLAN_Y0 + FR_Y:PLAN_Y1 + FR_Y + 1, int(a[0] + dx + FR_X)]
                        (hill_beach if ins.mean() > 0.9 and name not in V37_RING else edge).append(key)
                    elif name in V37_RING:
                        edge.append(key)
            else:
                row = m[int(a[1] + FR_Y), 60:2520]
                c = int((a[0] + b[0]) / 2 + 60)
                lo = hi = c
                while lo > 0 and not row[lo - 1]:
                    lo -= 1
                while hi < len(row) - 1 and not row[hi + 1]:
                    hi += 1
                key = '%s@y%d' % (name, a[1])
                res_we[key] = max(res_we.get(key, 0), round((hi - lo + 1) * U, 1))
    top = lambda d_: dict(sorted(d_.items(), key=lambda kv: -kv[1])[:6])
    inner = {k: v for k, v in res_ns.items() if k not in edge}
    return {'hill_to_beach_lines': sorted(set(hill_beach)), 'outer_edge_lines_meadow_beside': sorted(set(edge)),
            'city_height_m': round((PLAN_Y1 - PLAN_Y0) * U, 1), 'max_north_south_run_inside_m': max(inner.values()),
            'longest_north_south_runs_inside_m': top(inner),
            'max_north_south_run_m': max(res_ns.values()), 'longest_north_south_runs_m': top(res_ns),
            'longest_west_east_runs_m': top(res_we), 'note': 'raster 1 u; runs along street axes and both sidewalk lines (x +- 5 m); a hill-to-beach line '
                                                            'would span the whole city height'}


def v37_picture_fit(blds, st):
    """Data vs Vadim's v37 picture: street axes on asphalt, building footprints on house colours."""
    im = np.asarray(Image.open(V37_IMG).convert('RGB')).astype(np.int16)
    kx, ky = V37_PX
    pxy = lambda p: (int((p[0] + 110) * kx), int((p[1] + 330) * ky))
    asph = lambda c: abs(int(c[0]) - 95) + abs(int(c[1]) - 102) + abs(int(c[2]) - 108) < 45 or min(c) > 225
    jun = [p for p, n in junctions(st)]
    ok = tot = 0
    for name, s_ in st.items():
        for a, b in zip(s_['pts'][:-1], s_['pts'][1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            for t in np.arange(5, L - 5, 10):
                q = (a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L)
                for off in (-20, 20):                                      # both lanes, 4 m off the axis (clear of the centre dashes)
                    r_ = (q[0] + off, q[1]) if abs(a[0] - b[0]) < 1e-6 else (q[0], q[1] + off)
                    x, y = pxy(r_)
                    tot += 1
                    ok += asph(im[y, x])
    ground = np.array([[95, 102, 108], [227, 225, 217], [232, 238, 219], [157, 162, 162], [217, 210, 196], [241, 233, 214], [207, 224, 181],
                       [248, 248, 244], [255, 255, 255], [191, 195, 196]])
    per, allh, alln = [], 0, 0
    for b in blds:
        if b['kind'] not in ('house', 'arch_house', 'alley_plug', 'loft', 'glass_office', 'police', 'classical', 'van_shop', 'base_garage') or not is_rect(b['pl']):
            continue
        r_ = bb(b['pl'])
        if r_[2] - r_[0] < 14 or r_[3] - r_[1] < 14:
            continue
        x0, y0 = pxy((r_[0] + 5, r_[1] + 5))
        x1, y1 = pxy((r_[2] - 5, r_[3] - 5))
        sub = im[y0:y1, x0:x1].reshape(-1, 3)
        if not len(sub):
            continue
        g = (np.abs(sub[:, None, :] - ground[None, :, :]).max(-1) <= 9).any(-1)
        fr = 1.0 - float(g.mean())
        per.append((round(fr, 2), b['id']))
        allh += int((~g).sum())
        alln += len(g)
    per.sort()
    return {'street_lanes_on_asphalt': round(ok / max(1, tot), 3), 'street_samples': tot,
            'footprints_on_house_colour': round(allh / max(1, alln), 3), 'worst_buildings': per[:5],
            'note': 'every street axis sampled each 2 m on both lanes (4 m off the axis) on the v37 picture; footprints inset 1 m, share of pixels '
                    'that are not street / sidewalk / yard / alley / plaza / lawn colours'}


def v37_checks(blds, byid, adj, st, bands, model, outer, out_b, entries):
    res = {}
    ff = []                                                                # facade-to-facade across every street (both sides built)
    for b in blds:
        if not is_rect(b['pl']):
            continue
        for st_, ax, face, sgn, lo_, hi_ in street_faces(b['pl'], bands):
            mid = (lo_ + hi_) / 2
            for o in blds:
                if o is b or not is_rect(o['pl']):
                    continue
                ro = bb(o['pl'])
                f2 = ro[ax] if sgn > 0 else ro[ax + 2]
                if abs(f2 - (face + sgn * 2 * HW)) < 3 and ro[1 - ax] - 1 <= mid <= ro[3 - ax] + 1:
                    ff.append(abs(f2 - face) * U)
    res['facade_to_facade_measured_m'] = {'pairs': len(ff), 'min': round(min(ff), 2), 'median': round(float(np.median(ff)), 2), 'max': round(max(ff), 2),
                                          'note': 'footprints; the separation setbacks (0.3-0.6 m, builder insets) widen single facades to 22.3-22.6 m'}
    res['see_through_v37'] = v37_open_runs(blds, st, outer)
    hs = [b for b in blds if b['kind'] in ('house', 'arch_house')]
    hist = {}
    for b in hs:
        hist[b['floors']] = hist.get(b['floors'], 0) + 1
    eq = sorted({tuple(sorted((a['id'], n))) for a in hs for n in adj[a['id']] if byid[n] in hs and byid[n]['floors'] == a['floors']})
    res['floors'] = {'histogram_houses': {str(k): hist[k] for k in sorted(hist)}, 'min': min(hist), 'max': max(hist),
                     'adjacent_equal_pairs': len(eq), 'adjacent_equal_list': [list(e) for e in eq][:10],
                     'corner_houses_6': sum(1 for b in hs if b.get('corner37') and b['floors'] == 6),
                     'corner_houses': sum(1 for b in hs if b.get('corner37')),
                     'all_buildings_max_floors_except_towers': max(r_['floors'] for r_ in out_b if r_['kind'] not in ('tower', 'tower_round'))}
    res['offices'] = sorted(r_['id'] for r_ in out_b if r_.get('type') == 'office')
    ov = 0
    for i, a in enumerate(blds):
        for b in blds[i + 1:]:
            ox, oy = overlap(bb(a['pl']), bb(b['pl']))
            if min(ox, oy) > 0.3 and {a['kind'], b['kind']} not in ({'tower', 'podium'}, {'tower_round', 'podium_round'}, {'police', 'police_rotunda'}):
                ov += 1
    res['building_overlaps'] = ov
    dang = []                                                              # street ends must touch another street axis (junction / ring bend)
    for name, s_ in st.items():
        for p_ in (s_['pts'][0], s_['pts'][-1]):
            touch = False
            for n2, s2 in st.items():
                if n2 == name:
                    continue
                for a, b in zip(s2['pts'][:-1], s2['pts'][1:]):
                    L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 or 1e-9
                    t = max(0.0, min(1.0, ((p_[0] - a[0]) * (b[0] - a[0]) + (p_[1] - a[1]) * (b[1] - a[1])) / L2))
                    if math.hypot(p_[0] - a[0] - t * (b[0] - a[0]), p_[1] - a[1] - t * (b[1] - a[1])) < 1.0:
                        touch = True
            if not touch:
                dang.append('%s@%s' % (name, rnd2(p_)))
    res['dangling_street_ends'] = dang
    Winv_ = PLANDATA.get('Winv_')
    bad_e = []
    for e_ in entries:
        q = Winv_(e_['axis_point'])
        s2 = st[e_['street']]['pts']
        dmin = min(abs((q[0] - a[0]) * (b[1] - a[1]) - (q[1] - a[1]) * (b[0] - a[0])) / max(1e-9, math.hypot(b[0] - a[0], b[1] - a[1]))
                   for a, b in zip(s2[:-1], s2[1:]) if min(a[0], b[0]) - 1 <= q[0] <= max(a[0], b[0]) + 1 and min(a[1], b[1]) - 1 <= q[1] <= max(a[1], b[1]) + 1)
        if dmin > 0.5:
            bad_e.append(e_['id'])
    res['entries_off_their_street_axis'] = bad_e
    res['picture_fit_v37'] = v37_picture_fit(blds, st)
    return res


def v37_report_images(d):
    """Plan v37 picture with the data on top; top view of the layout with floors coloured."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    blds, st, alleys, entries, gaps = (PLANDATA[k] for k in ('blds', 'st', 'alleys', 'entries', 'gaps'))
    Winv = PLANDATA['Winv']
    recs = {r_['id']: r_ for r_ in d['buildings']}
    kx, ky = V37_PX
    # 1 -- overlay on the v37 picture (full resolution)
    im = Image.open(V37_IMG).convert('RGB')
    T = lambda p: ((p[0] + 110) * kx, (p[1] + 330) * ky)
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(lay)
    for a in alleys:
        for r_ in a['rects']:
            dl.polygon([T(q) for q in R(*r_)], fill=(0, 230, 255, 90))
    for g_ in gaps:
        dl.polygon([T(q) for q in R(*g_['rect'])], fill=(255, 0, 255, 170))
    for c_ in PLANDATA.get('courts', []):
        dl.polygon([T(q) for q in R(*c_)], fill=(40, 200, 60, 110))
    im = Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB')
    dr = ImageDraw.Draw(im)
    for name, s_ in st.items():
        dr.line([T(q) for q in s_['pts']], fill=(0, 200, 0), width=2)
    for b in blds:
        col = (0, 70, 255) if recs.get(b['id'], {}).get('type') == 'office' else (255, 0, 0)
        dr.polygon([T(q) for q in b['pl']], outline=col, width=2)
    for z in entries:
        x, y = T(Winv(z['pos']))
        dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=(255, 0, 255), width=3)
        dr.text((x + 11, y - 6), z['id'].replace('05-entry-', ''), fill=(120, 0, 120))
    dr.rectangle([8, 1904, 1000, 1994], fill=(255, 255, 255))
    dr.text((14, 1908), 'Downtown plan v37 (Vadim, picture) + A3 data: red = footprints, blue = offices 05/06, green lines = street axes, green fill = closed courts',
            fill=(0, 0, 0))
    dr.text((14, 1924), '(NEB gated court, BASE 4 yard 12 m), cyan = alleys 7 m, magenta = separation gaps / entries.  Fit: %s' % json.dumps(d['checks'].get('picture_fit_v37', {}).get('footprints_on_house_colour')), fill=(0, 0, 0))
    dr.text((14, 1940), 'street lanes on asphalt: %s   facade-to-facade: %s' % (d['checks']['picture_fit_v37']['street_lanes_on_asphalt'],
                                                                            d['checks']['facade_to_facade_measured_m']), fill=(0, 0, 0))
    im.save(os.path.join(REPORT_DIR, 'v37_plan_vs_data.png'))
    # 2 -- top view, floors coloured (plan units, 0.5 px per u = 2.5 px/m)
    sc = 0.5
    x0p, y0p = -120.0, -280.0
    Wd, Hd = int((2480 - x0p) * sc), int((1600 - y0p) * sc) + 70
    im = Image.new('RGB', (Wd, Hd), (226, 232, 214))
    dr = ImageDraw.Draw(im)
    T2 = lambda p: ((p[0] - x0p) * sc, (p[1] - y0p) * sc)
    for name, s_ in st.items():
        dr.line([T2(q) for q in s_['pts']], fill=(222, 220, 212), width=int(2 * HW * sc))
    for name, s_ in st.items():
        dr.line([T2(q) for q in s_['pts']], fill=(96, 102, 108), width=int(2 * CW * sc))
    for a in alleys:
        for r_ in a['rects']:
            dr.polygon([T2(q) for q in R(*r_)], fill=(160, 165, 165))
    FC = {3: (247, 226, 140), 4: (240, 170, 80), 5: (214, 98, 60), 6: (140, 40, 50)}
    for b in sorted(blds, key=lambda b: b['kind'] in ('tower', 'tower_round')):
        r_ = recs.get(b['id'])
        if not r_:
            continue
        fl = r_['floors']
        if r_['kind'] in ('tower', 'tower_round'):
            fill = (30, 50, 110)
        elif r_['kind'] in ('house', 'arch_house') or r_.get('type') == 'office':
            fill = FC.get(min(6, max(3, fl)), (200, 200, 200))
        else:
            fill = (175, 175, 170)
        dr.polygon([T2(q) for q in b['pl']], fill=fill, outline=(60, 50, 45))
        if r_.get('type') == 'office':
            dr.polygon([T2(q) for q in b['pl']], outline=(0, 90, 255), width=3)
        if r_['kind'] in ('house', 'arch_house') or r_.get('type') == 'office' or r_['kind'] == 'alley_plug':
            c = pcen(b['pl'])
            dr.text((T2(c)[0] - 3, T2(c)[1] - 6), str(fl), fill=(255, 255, 255) if fl >= 5 else (0, 0, 0))
    for g_ in gaps:
        dr.polygon([T2(q) for q in R(*g_['rect'])], fill=(255, 0, 255))
    for c_ in PLANDATA.get('courts', []):
        dr.polygon([T2(q) for q in R(*c_)], fill=(150, 205, 120), outline=(40, 120, 40))
    hist = d['checks']['floors']['histogram_houses']
    yy = Hd - 64
    dr.rectangle([0, yy - 6, Wd, Hd], fill=(255, 255, 255))
    xx = 10
    for f_ in (3, 4, 5, 6):
        dr.rectangle([xx, yy, xx + 22, yy + 16], fill=FC[f_], outline=(0, 0, 0))
        dr.text((xx + 28, yy + 2), '%d floors: %s houses' % (f_, hist.get(str(f_), 0)), fill=(0, 0, 0))
        xx += 170
    dr.rectangle([xx, yy, xx + 22, yy + 16], outline=(0, 90, 255), width=3)
    dr.text((xx + 28, yy + 2), 'office class: %d' % len(d['checks']['offices']), fill=(0, 0, 0))
    dr.rectangle([xx + 170, yy, xx + 192, yy + 16], fill=(255, 0, 255))
    dr.text((xx + 198, yy + 2), 'separation gap 1.5-2.5 m: %d' % len(gaps), fill=(0, 0, 0))
    dr.rectangle([xx + 420, yy, xx + 442, yy + 16], fill=(30, 50, 110))
    dr.text((xx + 448, yy + 2), 'twin towers 55 floors (unchanged)', fill=(0, 0, 0))
    dr.text((10, yy + 26), 'Downtown v37 data (A3, 22.10): houses 3-6 floors, neighbours always differ (adjacent equal pairs: %d), corners mostly 6; grey = special '
                           'buildings (police, diner, garage, ...). North up, 1 px = 0.4 m.' % d['checks']['floors']['adjacent_equal_pairs'], fill=(0, 0, 0))
    im.save(os.path.join(REPORT_DIR, 'v37_floors_top.png'))


def v37_land(d):
    """out_<REV>/downtown_v37_land.json for the terrain (agent A1): Downtown pad, sea that becomes land, the moved beach."""
    import s04_coast as C
    pad = next(z for z in d['zones'] if z['id'] == '05-ground')['poly']
    cls_p = os.path.join(ROOT, 'Tools', 'MapV85', 'out_v01', 'classes_v85.npy')
    cls = np.load(cls_p if os.path.exists(cls_p) else os.path.join(WORK, 'classes_v85.npy'))
    sea = cls == 1
    nc = C.new_coast(2.0, C.SHIFT_X[0], C.SHIFT_X[3])
    land_top = []
    from scipy import ndimage
    xs_ = np.arange(int(C.SHIFT_X[0]), int(C.SHIFT_X[3]) + 1)
    old = []
    for x in xs_:
        col = np.nonzero(sea[:400, x])[0]
        old.append(col.max() + 1.0 if len(col) else np.nan)
    old = ndimage.median_filter(np.array(old), size=21, mode='nearest')    # the pier is not coast
    def at(pl, x):
        for (ax, ay), (bx, by) in zip(pl[:-1], pl[1:]):
            if ax <= x <= bx:
                return ay + (by - ay) * (x - ax) / max(1e-6, bx - ax)
        return pl[0][1] if x < pl[0][0] else pl[-1][1]
    cb0 = [C.post0(q) for q in C.chaikin(C.COAST_B, 3)]
    for i, x in enumerate(xs_[::4]):
        land_top.append((float(x), round(max(float(old[i * 4]), at(cb0, x)) + 3.0, 2)))
    land_top.append((float(xs_[-1]), round(max(float(old[-1]), at(cb0, xs_[-1])) + 3.0, 2)))
    newc = [(float(x), round(at(nc, x), 2)) for x, _ in land_top]
    poly = newc + land_top[::-1]
    out = {'status': 'FINAL (A3 Downtown v37, 2026-10-22; from s04_downtown.py / s04_coast.py, REV %s)' % REV,
           'units': 'm, world v85 (x east, y north); Unity X = x, Z = y',
           'pad_poly': pad, 'pad_height_m': 5.0, 'pad_blend_m': 40.0,
           'pad_note': 'Downtown v37 pad = zone 05-ground (outer edge of the ring sidewalk + 2 m). Grows 52-60 m NORTH into the foot of hill B '
                       '(top ring axis y 494 / 502 / 510, outer edge y 507-523) and 54 m SOUTH (promenade street SP axis y 176, outer edge y 163). '
                       'Flat 5.0 m like v01; hill B must start rising beyond the 40 m blend (the tunnel portal and the VIEW B / VIEW C roads move, '
                       'see roads_v85.json of s02).',
           'land_override': [poly],
           'land_override_note': 'sea of the v85 picture (classes_v85 cls == 1) that becomes land: the city beach moves 54 m south (x %.0f-%.0f full, smoothstep '
                                 'taper to 0 at x %.0f / %.0f). Polygon = new waterline up to max(old waterline, coast_b) + 3 m. Inside = land (beach sand, '
                                 'dunes, palm park, city); the new waterline is the zone 09-waterline of beach_v85.json.' % (C.SHIFT_X[1], C.SHIFT_X[2], C.SHIFT_X[0], C.SHIFT_X[3]),
           'land_override_surface': 'sand_white (beach sand; the palm park / dunes / city on top come from beach_v85.json / this pad)',
           'beach_shift': {'dy_m': C.BEACH_DY, 'x': list(C.SHIFT_X), 'rule': 'world y += beach_dy(x) (s04_coast.beach_dy)'},
           'beach_poly': [C.beach_outline()],
           'beach_note': 'district 09 after the move: palm park + dunes + sand to the new waterline; top edge = south edge of the SP sidewalk (y ~164) along the '
                         'city; the Elite beach (x > 1400) unchanged. Heights as v01: park ~ +2.5 m falling to 0 at the water (beach pad_note).',
           'new_coastline': nc,
           'north_links_note': 'entries on the new top ring (world): tunnel %s on N0w, VIEW B serpentine %s on N0c, VIEW C cornice %s on N0e (axis points). '
                               's02_network (v37 branch) bends the roads into them; with the v85 tunnel axis the tunnel south portal moves to about '
                               '(822.6, 548.0) = 74 m shorter (scratch run 22.10): the hill B south flank must cover that portal (~8-10 m above the road) '
                               'only ~25 m beyond the pad edge.' % tuple(next(z['axis_point'] for z in d['zones'] if z['id'] == '05-entry-' + k)
                                                                     for k in ('N-tunnel', 'N-viewB', 'NE-viewC'))}
    os.makedirs(WORK, exist_ok=True)
    with open(os.path.join(WORK, 'downtown_v37_land.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    return out


def main():
    d, W = build()
    save_json('districts/downtown_v85.json', d)
    overlays(d)
    if PLAN == 'v37':
        v37_report_images(d)
        land = v37_land(d)
        print('land file:', os.path.join(WORK, 'downtown_v37_land.json'), 'pad pts', len(land['pad_poly']), 'override pts', len(land['land_override'][0]))
        print('v37 checks:', json.dumps({k: d['checks'][k] for k in ('facade_to_facade_measured_m', 'see_through_v37', 'floors', 'building_overlaps',
                                                                      'dangling_street_ends', 'picture_fit_v37')}, ensure_ascii=False))
    print('downtown_v85 counts:', d['counts'])
    print('fit:', d['transform'].split('Fit on the v85 render: ')[1])
    print('checks:', {k: v for k, v in d['checks'].items() if k != 'unbuilt_block_pockets'})
    print('pockets:', d['checks']['unbuilt_block_pockets'][:12])
    print('fixes:', len(d['fixed_by_logic']), 'questions:', len(d['questions_for_vadim']))


if __name__ == '__main__':
    main()
