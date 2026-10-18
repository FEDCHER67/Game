"""Неблагополучный район — план v43 (TASK-000609), от v42: фонари только вплотную к домам (у углов фасадов с подъездами)
и к детским площадкам/коробке, ни одного на проездах и тропах; вдоль внешней дороги — на обочине за кюветом;
гаражи у базы сдвинуты вправо (~6 м) — бусику свободнее.
Ранее v42 (TASK-000608), от v41: земля как у GPT — серый разбитый асфальт/утоптанная земля почти везде,
между ним рваные пятна сухой травы; связки-тропы светлее; коробка с забором, воротами и одним входом; фонари по краям проездов,
у подъездов, у площадок и вдоль внешней дороги (не на проезжей части).
Ранее v41 (TASK-000607): векторная пересборка плана v40 (раньше правили картинку).
- район чуть шире: блоки домов раздвинуты на 8 % от центра, размеры домов те же (масштаб одинаковый);
- у каждого подъезда палисадник: газон вдоль фасада, дорожка от подъезда, лавочки по бокам (где одна, где две, у части нет), урна;
- вокруг каждого дома серый «почти проезд» (разбитый асфальт), между ними связки к дорогам и аркам;
- детская площадка и мусорная секция в сердце двора 12 (большая площадка) и двора 9 (поменьше);
- будки, турники, голые деревья, фонари, машины, граффити — перенесены.
Координаты объектов — в пикселях v37 (до раздвижки); трансформация T() применяется при рисовании.
Не перезаписывает. Запуск: python build_rough_v43.py -> Неблагополучный_район_v43.png
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'Неблагополучный_район_v43.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

S, CX, CY, OX, OY = 1.08, 1290, 900, 110, 80
W, H = 3060, 2120
BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
DRIVE, LAWN, WALK = (158, 154, 146), (152, 176, 122), (196, 190, 178)
ROAD, ROAD_EDGE = (233, 216, 172), (176, 166, 140)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
FENCE = (112, 119, 119)
DOOR, DOOR_OUT = (96, 106, 116), (50, 58, 66)
BENCH, BENCH_OUT = (150, 112, 80), (90, 64, 44)
BIN, BIN_OUT = (104, 140, 104), (52, 74, 56)
SKIP, SKIP_OUT = (84, 120, 92), (40, 60, 46)
ARCH, ARCH_L = (246, 247, 240), (120, 128, 132)
CLUB, CLUB_OUT = (178, 150, 168), (88, 64, 84)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)
rnd = random.Random(41)

OUTSIDE, GROUND, TRACK = (198, 190, 158), (170, 166, 158), (186, 182, 172)
img = Image.new('RGB', (W, H), OUTSIDE)
dr = ImageDraw.Draw(img)


def T(x, y):
    return (CX + S * (x - CX) + OX, CY + S * (y - CY) + OY)


def mv(r, d):
    return (r[0] + d[0], r[1] + d[1], r[2] + d[0], r[3] + d[1])


def delta(bbox):
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    tx, ty = T(cx, cy)
    return (tx - cx, ty - cy)


# ================================================================ модель (координаты v37)
# дом: компоненты-прямоугольники, арки, подъезды (сторона, индекс компонента, a, b, n, пропуск-арка)
HOUSES = {
    'H1':  dict(c=[(118, 110, 700, 215), (118, 215, 223, 480)], doors=[('S', 0, 223, 700, 3, None), ('E', 1, 215, 480, 1, None)]),
    'H2':  dict(c=[(118, 573, 540, 670)], doors=[('N', 0, 118, 540, 2, None)]),
    'H3':  dict(c=[(118, 750, 540, 849)], arches=[(267, 750, 324, 849)], doors=[('S', 0, 118, 540, 2, (267, 324))]),
    'H5':  dict(c=[(859, 180, 1172, 285)], doors=[('S', 0, 859, 1172, 2, None)]),
    'H6':  dict(c=[(1175, 288, 1491, 393)], doors=[('S', 0, 1175, 1491, 2, None)]),
    'H7':  dict(c=[(859, 492, 1491, 597)], doors=[('S', 0, 859, 1491, 4, None)]),
    'H8':  dict(c=[(1587, 259, 2306, 364)], doors=[('S', 0, 1587, 2306, 4, None)]),
    'H9':  dict(c=[(1790, 450, 2318, 555), (2213, 555, 2318, 950)], arches=[(2000, 450, 2052, 555)],
                doors=[('S', 0, 1790, 2213, 3, (2000, 2052)), ('W', 1, 555, 950, 2, None)]),
    'H11': dict(c=[(208, 1011, 294, 1238), (493, 938, 564, 1238), (294, 1141, 493, 1238)], arches=[(368, 1169, 440, 1238)],
                doors=[('E', 0, 1011, 1141, 1, None), ('W', 1, 938, 1141, 1, None), ('N', 2, 294, 493, 2, (368, 440))]),
    'H13': dict(c=[(1107, 1083, 1482, 1167)], doors=[('S', 0, 1107, 1482, 2, None)]),
    'H14': dict(c=[(843, 1125, 951, 1653)], doors=[('E', 0, 1125, 1653, 2, None)]),
    'H17': dict(c=[(200, 1389, 295, 1713), (295, 1610, 536, 1713)], doors=[('E', 0, 1389, 1610, 1, None)]),
}
# блоки, которые двигаются вместе (дома с аркой между ними, сцепленные углами, молния с длинным домом)
BLOCKS = {
    'W': dict(c=[(651, 486, 764, 858), (654, 960, 759, 1410)], arches=[(682, 858, 736, 960)],
              doors=[('E', 0, 486, 858, 2, None), ('E', 1, 960, 1410, 2, None)]),
    'E': dict(c=[(1596, 489, 1701, 951), (1596, 1059, 1706, 1679), (2050, 1140, 2405, 1245), (2050, 1245, 2155, 1455),
                 (1706, 1455, 2155, 1560)],
              arches=[(1619, 951, 1675, 1059), (1860, 1455, 1912, 1560)],
              doors=[('E', 0, 489, 951, 2, None), ('E', 1, 1059, 1455, 2, None), ('S', 2, 2155, 2405, 2, None),
                     ('S', 4, 1706, 2155, 2, (1860, 1912))]),
}
HOUSES['H56'] = dict(c=HOUSES.pop('H5')['c'] + HOUSES.pop('H6')['c'],
                     doors=[('S', 0, 859, 1172, 2, None), ('S', 1, 1175, 1491, 2, None)])
HOUSES.update(BLOCKS)

for h in HOUSES.values():
    xs = [r[0] for r in h['c']] + [r[2] for r in h['c']]
    ys = [r[1] for r in h['c']] + [r[3] for r in h['c']]
    h['d'] = delta((min(xs), min(ys), max(xs), max(ys)))
    h['C'] = [mv(r, h['d']) for r in h['c']]
    h['A'] = [mv(r, h['d']) for r in h.get('arches', [])]

# ================================================================ земля района: серый разбитый асфальт почти везде + пятна сухой травы
BAND, LAWN_D, DOORBAND = 20, 32, 26
DISTRICT = [(36, 40), (772, 40), (772, 18), (1565, 18), (1565, 208), (2559, 208), (2559, 1047), (2445, 1047),
            (2445, 1743), (137, 1743), (137, 1068), (36, 1068)]
DPOLY = [T(*p) for p in DISTRICT]
dr.polygon(DPOLY, fill=GROUND)
LINKS = [[(113, 905), (785, 905), (785, 1012), (2470, 1012)],   # с запада через арку к востоку
         [(1552, 1765), (1552, 1012)],                          # от южной дороги у коробки
         [(622, 1765), (622, 1577), (500, 1577)],               # к базе и бусику
         [(588, 905), (588, 277)],                              # в двор 9
         [(588, 442), (1590, 442)],                             # между верхними и средним домом
         [(812, 465), (812, 142), (1495, 142)],                 # к гаражам у северного забора
         [(1957, 1012), (1957, 900)]]                           # в двор 12 с юга
TLINKS = [[T(*q) for q in pts] for pts in LINKS]


def inside(pt, poly):
    x, y = pt
    c = False
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / ((y1 - y0) or 1e-9) + x0:
            c = not c
    return c


def segdist(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / ((dx * dx + dy * dy) or 1)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


KEEP = []                                                      # где травы нет: дома + палисадники, гаражи, площадки
for h in HOUSES.values():
    for (x0, y0, x1, y1) in h['C']:
        KEEP.append((x0 - 75, y0 - 75, x1 + 75, y1 + 75))
for bb, d in (((905, 50, 1445, 118), None), ((883, 702, 1417, 943), None), ((2350, 462, 2554, 915), None),
              ((410, 1390, 635, 1532), HOUSES['H17']['d']), ((1114, 1238, 1477, 1541), None), ((1176, 1622, 1404, 1703), None)):
    x0, y0, x1, y1 = mv(bb, d or delta(bb))
    KEEP.append((x0 - 45, y0 - 45, x1 + 45, y1 + 45))
for c in ((1930, 790, 260, 200), (440, 450, 200, 260)):
    cx, cy = T(c[0], c[1])
    KEEP.append((cx - c[2] / 2 - 40, cy - c[3] / 2 - 40, cx + c[2] / 2 + 40, cy + c[3] / 2 + 40))
gr = random.Random(7)
xs = [p[0] for p in DPOLY]; ys = [p[1] for p in DPOLY]
for gy in range(int(min(ys)), int(max(ys)), 46):
    for gx in range(int(min(xs)), int(max(xs)), 46):
        p = (gx + gr.uniform(-18, 18), gy + gr.uniform(-18, 18))
        if not inside(p, DPOLY) or gr.random() > 0.8:
            continue
        if any(r[0] < p[0] < r[2] and r[1] < p[1] < r[3] for r in KEEP):
            continue
        if any(segdist(p, a, b) < 42 for pts in TLINKS for a, b in zip(pts[:-1], pts[1:])):
            continue
        R = gr.uniform(26, 46)
        pts = [(p[0] + R * gr.uniform(0.6, 1.15) * math.cos(t * math.pi / 5), p[1] + R * gr.uniform(0.6, 1.15) * math.sin(t * math.pi / 5)) for t in range(10)]
        dr.polygon(pts, fill=(int(gr.uniform(170, 184)), int(gr.uniform(160, 170)), int(gr.uniform(116, 128))))
for pts in TLINKS:                                              # тропы-проезды светлее, без бордюров
    dr.line(pts, fill=TRACK, width=34, joint='curve')

# ================================================================ дорога вокруг района и выезды
ROADPTS = [(113, 1068), (113, 1765), (2470, 1765), (2470, 1012)]
EXITS = [[(113, 1068), (-120, 1068)], [(2470, 1122), (2760, 1122)], [(453, 1765), (453, 1960)],
         [(686, 1765), (686, 1960)], [(1765, 1765), (1765, 1960)]]
for pts in [ROADPTS] + EXITS:
    p = [T(*q) for q in pts]
    dr.line(p, fill=ROAD_EDGE, width=62, joint='curve')
for pts in [ROADPTS] + EXITS:
    p = [T(*q) for q in pts]
    dr.line(p, fill=ROAD, width=50, joint='curve')

# ================================================================ палисадники у подъездов (газон вдоль фасада)
DOORS = []
for h in HOUSES.values():
    for side, ci, a, b, n, skip in h['doors']:
        x0, y0, x1, y1 = h['C'][ci]
        dx, dy = h['d']
        if side in 'SN':
            a2, b2 = a + dx, b + dx
            dr.rectangle([a2, y1, b2, y1 + LAWN_D] if side == 'S' else [a2, y0 - LAWN_D, b2, y0], fill=LAWN)
        else:
            a2, b2 = a + dy, b + dy
            dr.rectangle([x1, a2, x1 + LAWN_D, b2] if side == 'E' else [x0 - LAWN_D, a2, x0, b2], fill=LAWN)
        sk = (skip[0] + dx, skip[1] + dx) if skip else None
        for k in range(n):
            t = a2 + (b2 - a2) * (k + 0.5) / n
            if sk and sk[0] - 20 <= t <= sk[1] + 20:
                t = sk[0] - 50 if t < (sk[0] + sk[1]) / 2 else sk[1] + 50
            if side == 'S':
                DOORS.append((side, t, y1))
            elif side == 'N':
                DOORS.append((side, t, y0))
            elif side == 'E':
                DOORS.append((side, x1, t))
            else:
                DOORS.append((side, x0, t))
        if sk:                                                   # под аркой газона нет — проход
            if side == 'S':
                dr.rectangle([sk[0], y1, sk[1], y1 + LAWN_D], fill=DRIVE)
            elif side == 'N':
                dr.rectangle([sk[0], y0 - LAWN_D, sk[1], y0], fill=DRIVE)
for side, x, y in DOORS:                                         # дорожка от подъезда через палисадник
    if side == 'S':
        dr.rectangle([x - 13, y, x + 13, y + LAWN_D], fill=WALK)
    elif side == 'N':
        dr.rectangle([x - 13, y - LAWN_D, x + 13, y], fill=WALK)
    elif side == 'E':
        dr.rectangle([x, y - 13, x + LAWN_D, y + 13], fill=WALK)
    else:
        dr.rectangle([x - LAWN_D, y - 13, x, y + 13], fill=WALK)


# ================================================================ двор 12 и двор 9: детская площадка + мусорка в центре
def playground(cx, cy, w, h):
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    dr.rectangle([x0, y0, x1, y1], fill=(222, 206, 160), outline=(120, 100, 70), width=3)
    dr.line([(x0 + 16, y0 + 16), (x0 + 80, y0 + 16)], fill=(90, 80, 70), width=4)          # качели
    for k in (22, 50):
        dr.rectangle([x0 + 16 + k - 6, y0 + 24, x0 + 16 + k + 6, y0 + 31], fill=(170, 60, 50))
    gx = x1 - 74                                                                         # горка
    dr.rectangle([gx, y0 + 16, gx + 18, y0 + 34], fill=(120, 130, 150), outline=(70, 70, 80))
    dr.rectangle([gx + 18, y0 + 21, gx + 60, y0 + 29], fill=(200, 80, 60), outline=(110, 50, 40))
    dr.rectangle([cx - 32, y1 - 52, cx + 32, y1 - 12], fill=(236, 214, 150), outline=(140, 100, 60), width=3)  # песочница
    if w > 180:                                                                          # на большой ещё карусель и вторые качели
        dr.ellipse([x0 + 22, y1 - 56, x0 + 62, y1 - 16], outline=(110, 90, 70), width=3)
        dr.line([(x1 - 80, y1 - 30), (x1 - 20, y1 - 30)], fill=(90, 80, 70), width=4)


def trash(x0, y0, open_side):
    x1, y1 = x0 + 80, y0 + 62
    dr.rectangle([x0, y0, x1, y1], fill=(206, 204, 196))
    segs = {'N': [(x0, y0), (x1, y0)], 'S': [(x0, y1), (x1, y1)], 'W': [(x0, y0), (x0, y1)], 'E': [(x1, y0), (x1, y1)]}
    for k, sg in segs.items():
        if k != open_side:
            dr.line(sg, fill=FENCE, width=4)
    dr.rectangle([x0 + 8, y0 + 8, x0 + 38, y0 + 26], fill=SKIP, outline=SKIP_OUT, width=2)
    dr.rectangle([x0 + 42, y0 + 8, x0 + 72, y0 + 26], fill=SKIP, outline=SKIP_OUT, width=2)
    for k in range(3):
        dr.rectangle([x0 + 10 + k * 22, y0 + 36, x0 + 26 + k * 22, y0 + 52], fill=BIN, outline=BIN_OUT, width=2)


p12 = T(1930, 790)
playground(p12[0], p12[1], 230, 170)
trash(p12[0] + 135, p12[1] - 31, 'S')
p9 = T(440, 395)
playground(p9[0], p9[1], 160, 120)
trash(p9[0] - 40, p9[1] + 68, 'W')

# ================================================================ дома, арки, подъезды, лавочки
for h in HOUSES.values():
    for r in h['C']:
        dr.rectangle(r, fill=FILL)
for h in HOUSES.values():                       # контур объединения: рисуем рамки, потом закрашиваем стыки
    for r in h['C']:
        dr.rectangle(r, outline=OUTL, width=3)
for h in HOUSES.values():
    for i, r in enumerate(h['C']):
        for j, q in enumerate(h['C']):
            if i < j:
                ix0, iy0, ix1, iy1 = max(r[0], q[0]), max(r[1], q[1]), min(r[2], q[2]), min(r[3], q[3])
                if ix1 - ix0 >= 0 and iy1 - iy0 >= 0 and (ix1 - ix0 > 6 or iy1 - iy0 > 6):
                    if ix1 - ix0 <= 6:      # общая вертикальная грань
                        dr.rectangle([ix0 - 3, iy0 + 3, ix1 + 3, iy1 - 3], fill=FILL)
                    elif iy1 - iy0 <= 6:    # общая горизонтальная грань
                        dr.rectangle([ix0 + 3, iy0 - 3, ix1 - 3, iy1 + 3], fill=FILL)
for h in HOUSES.values():
    for (x0, y0, x1, y1) in h['A']:
        dr.rectangle([x0, y0, x1, y1], fill=ARCH)
        if x1 - x0 < y1 - y0 or True:
            vert = (y1 - y0) > (x1 - x0) and (x1 - x0) > 70
            if vert:
                dr.line([(x0, y0 + 4), (x1, y0 + 4)], fill=ARCH_L, width=2)
                dr.line([(x0, y1 - 4), (x1, y1 - 4)], fill=ARCH_L, width=2)
            else:
                dr.line([(x0 + 4, y0), (x0 + 4, y1)], fill=ARCH_L, width=2)
                dr.line([(x1 - 4, y0), (x1 - 4, y1)], fill=ARCH_L, width=2)

# притон 5 в первом этаже молнии
dE = HOUSES['E']['d']
dr.rectangle(mv((2051, 1262, 2125, 1440), dE), fill=CLUB, outline=CLUB_OUT, width=3)
dr.rectangle(mv((2034, 1320, 2051, 1382), dE), fill=(120, 104, 116), outline=CLUB_OUT, width=2)
cx, cy = 2042 + dE[0], 1351 + dE[1]
dr.ellipse([cx - 7, cy - 8, cx + 7, cy + 8], fill=(236, 90, 170))
dr.rectangle(mv((1940, 1300, 2028, 1402), dE), fill=(226, 224, 214))


def bench_urn(side, x, y, s):
    if side in 'SN':
        by = y + LAWN_D + 4 if side == 'S' else y - LAWN_D - 12
        bx = x + s * 30
        dr.rectangle([bx - 14, by, bx + 14, by + 8], fill=BENCH, outline=BENCH_OUT)
    else:
        bx = x + LAWN_D + 4 if side == 'E' else x - LAWN_D - 12
        by = y + s * 30
        dr.rectangle([bx, by - 14, bx + 8, by + 14], fill=BENCH, outline=BENCH_OUT)


for side, x, y in DOORS:
    if side == 'S':
        dr.rectangle([x - 11, y + 2, x + 11, y + 9], fill=DOOR, outline=DOOR_OUT)
    elif side == 'N':
        dr.rectangle([x - 11, y - 9, x + 11, y - 2], fill=DOOR, outline=DOOR_OUT)
    elif side == 'E':
        dr.rectangle([x + 2, y - 11, x + 9, y + 11], fill=DOOR, outline=DOOR_OUT)
    else:
        dr.rectangle([x - 9, y - 11, x - 2, y + 11], fill=DOOR, outline=DOOR_OUT)
    r = rnd.random()
    sides = [] if r < 0.2 else ([rnd.choice((-1, 1))] if r < 0.65 else [-1, 1])
    for s in sides:
        bench_urn(side, x, y, s)
    if sides:                                                     # урна у входа на дорожку
        ux, uy = {'S': (x + 18, y + LAWN_D + 4), 'N': (x + 18, y - LAWN_D - 12),
                  'E': (x + LAWN_D + 4, y + 18), 'W': (x - LAWN_D - 12, y + 18)}[side]
        dr.rectangle([ux, uy, ux + 8, uy + 8], fill=(70, 110, 80), outline=(40, 60, 46))

# база: ворота гаража в фасаде, бусик
dB = HOUSES['H17']['d']
dr.rectangle(mv((446, 1606, 477, 1613), dB), fill=(60, 64, 68))
dr.rectangle(mv((460, 1530, 502, 1600), dB), fill=(250, 250, 248), outline=(80, 90, 100), width=2)
dr.rectangle(mv((466, 1540, 496, 1552), dB), fill=(160, 170, 180))


# ================================================================ гаражи
def garage(r, door):
    dr.rectangle(r, fill=GAR, outline=GAR_OUT, width=2)
    x0, y0, x1, y1 = r
    dd = {'S': [x0 + 6, y1 - 5, x1 - 6, y1 - 2], 'N': [x0 + 6, y0 + 2, x1 - 6, y0 + 5],
          'E': [x1 - 5, y0 + 6, x1 - 2, y1 - 6], 'W': [x0 + 2, y0 + 6, x0 + 5, y1 - 6]}[door]
    dr.rectangle(dd, fill=(80, 96, 104))


GARAGES = []
GN = [((905 + k * 45, 50, 950 + k * 45, 118), 'S') for k in range(12)]
G7 = [((966 + k * 46, 702, 1012 + k * 46, 770), 'S') for k in range(8)] + \
     [((966 + k * 46, 875, 1012 + k * 46, 943), 'N') for k in range(8)] + \
     [((883, 763 + k * 60, 940, 823 + k * 60), 'E') for k in range(2)] + \
     [((1360, 763 + k * 60, 1417, 823 + k * 60), 'W') for k in range(2)]
GNE = [((2350, 510 + k * 45, 2418, 555 + k * 45), 'E') for k in range(9)] + \
      [((2486, 510 + k * 45, 2554, 555 + k * 45), 'W') for k in range(9)] + [((2418, 462, 2486, 510), 'S')]
GB = [((410 + k * 45, 1390, 455 + k * 45, 1458), 'S') for k in range(5)] + \
     [((567, 1458 + k * 37, 635, 1495 + k * 37), 'W') for k in range(2)]
for grp, d in ((GN, delta((905, 50, 1445, 118))), (G7, delta((883, 702, 1417, 943))),
               (GNE, delta((2350, 462, 2554, 915))), (GB, dB)):
    for r, door in grp:
        rr = mv(r, d)
        garage(rr, door)
        GARAGES.append(rr)
TAGS = ((214, 60, 150), (40, 160, 170), (230, 190, 40), (90, 90, 200))
for rr in rnd.sample(GARAGES, 14):                                   # граффити
    x0, y0, x1, y1 = rr
    cy0 = (y0 + y1) / 2
    pts = [(x0 + 5 + i * (x1 - x0 - 10) / 6, cy0 + (4 if i % 2 else -4)) for i in range(7)]
    dr.line(pts, fill=rnd.choice(TAGS), width=3)

# ================================================================ коробка, магазин
dBox = delta((1114, 1238, 1477, 1541))
BOX = mv((1114, 1238, 1477, 1541), dBox)
x0, y0, x1, y1 = BOX
dr.rectangle([x0, y0, x1, y1], fill=(214, 226, 200), outline=(170, 186, 160), width=2)
dr.rectangle([x0 + 18, y0 + 18, x1 - 18, y1 - 18], fill=(168, 196, 146), outline=(90, 120, 80), width=4)
dr.rectangle([x0 + 28, y0 + 28, x1 - 28, y1 - 28], outline=(250, 250, 250), width=2)
dr.line([((x0 + x1) / 2, y0 + 28), ((x0 + x1) / 2, y1 - 28)], fill=(250, 250, 250), width=2)
dr.ellipse([(x0 + x1) / 2 - 30, (y0 + y1) / 2 - 30, (x0 + x1) / 2 + 30, (y0 + y1) / 2 + 30], outline=(250, 250, 250), width=2)
gw = (y1 - y0) * 0.22                                            # ворота на коротких сторонах
for gx in (x0 + 28, x1 - 28):
    dr.rectangle([gx - 6, (y0 + y1) / 2 - gw / 2, gx + 6, (y0 + y1) / 2 + gw / 2], outline=(250, 250, 250), width=3)
gate = ((x0 + x1) / 2 - 24, (x0 + x1) / 2 + 24)                  # единственный вход — калитка с севера
dr.line([(x0, y0), (gate[0], y0)], fill=(60, 64, 70), width=5)
dr.line([(gate[1], y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], fill=(60, 64, 70), width=5)
for px in range(int(x0), int(x1) + 1, 40):                         # столбы сетки
    for py in (y0, y1):
        if not (gate[0] < px < gate[1] and py == y0):
            dr.rectangle([px - 3, py - 3, px + 3, py + 3], fill=(50, 54, 60))
dShop = delta((1176, 1622, 1404, 1703))
dr.rectangle(mv((1209, 1622, 1371, 1703), dShop), fill=(215, 167, 146), outline=(122, 70, 58), width=3)
garage(mv((1176, 1630, 1204, 1696), dShop), 'S'); garage(mv((1376, 1630, 1404, 1696), dShop), 'S')

# ================================================================ будки, турники, деревья, фонари, машины
for (bx, by) in ((2105, 905), (780, 1480)):
    x, y = T(bx, by)
    dr.rectangle([x, y, x + 34, y + 34], fill=(176, 132, 112), outline=(96, 66, 54), width=3)
    dr.polygon([(x + 17, y + 8), (x + 26, y + 24), (x + 8, y + 24)], fill=(240, 200, 40), outline=(60, 50, 30))
for (ax, ay, bx) in ((245, 455, 295), (1800, 950, 1860)):
    x, y = T(ax, ay)
    x1 = x + (bx - ax)
    for px in (x, x1):
        dr.rectangle([px - 4, y - 4, px + 4, y + 4], fill=(60, 60, 70))
    dr.line([(x, y), (x1, y)], fill=(60, 60, 70), width=3)


def tree(x, y):
    for a in range(0, 360, rnd.choice((51, 60))):
        a2 = math.radians(a + rnd.uniform(-20, 20))
        L = rnd.uniform(14, 24)
        mx, my = x + L * 0.6 * math.cos(a2), y + L * 0.6 * math.sin(a2)
        ex, ey = x + L * math.cos(a2 + rnd.uniform(-0.4, 0.4)), y + L * math.sin(a2 + rnd.uniform(-0.4, 0.4))
        dr.line([(x, y), (mx, my), (ex, ey)], fill=(108, 88, 70), width=2)
    dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(92, 72, 56))


for p in [(330, 320), (580, 320), (330, 470), (560, 470),                     # двор 9 вокруг площадки
          (1790, 690), (2090, 690), (1790, 900), (2090, 960),                  # двор 12 вокруг площадки
          (1150, 655), (1400, 655), (1060, 1300), (1060, 1480),                # центр
          (410, 1060), (60, 420), (60, 680), (790, 1700), (175, 1300),         # двор 11, запад, пустошь
          (2290, 1340), (2360, 1500), (2250, 1660), (1820, 1700), (2010, 1700)]:   # двор 13, юг
    tree(*T(*p))
LAMPS = []
for h in HOUSES.values():                                         # вплотную к углам фасада с подъездами
    for side, ci, a, b, n, skip in h['doors']:
        x0, y0, x1, y1 = h['C'][ci]
        if side in 'SN':
            yy = y1 + 14 if side == 'S' else y0 - 14
            LAMPS += [(x0 - 12, yy), (x1 + 12, yy)] if x1 - x0 > 260 else [(x1 + 12, yy)]
        else:
            xx = x1 + 14 if side == 'E' else x0 - 14
            LAMPS += [(xx, y0 - 12), (xx, y1 + 12)] if y1 - y0 > 260 else [(xx, y1 + 12)]
for (cx, cy, w, hh) in ((*T(1930, 790), 230, 170), (*T(440, 395), 160, 120)):   # вплотную к углам детских площадок
    LAMPS += [(cx - w / 2 - 10, cy - hh / 2 - 10), (cx + w / 2 + 10, cy - hh / 2 - 10),
              (cx - w / 2 - 10, cy + hh / 2 + 10), (cx + w / 2 + 10, cy + hh / 2 + 10)]
LAMPS += [(BOX[0] - 10, BOX[1] - 10), (BOX[2] + 10, BOX[1] - 10), (BOX[0] - 10, BOX[3] + 10), (BOX[2] + 10, BOX[3] + 10)]
RP = [T(*q) for q in ROADPTS]                                     # вдоль внешней дороги — на обочине, не на асфальте
for (ax, ay), (bx, by) in zip(RP[:-1], RP[1:]):
    L = math.hypot(bx - ax, by - ay)
    nx, ny = (by - ay) / L, -(bx - ax) / L
    if not inside(((ax + bx) / 2 + nx * 60, (ay + by) / 2 + ny * 60), DPOLY):
        nx, ny = -nx, -ny
    for k in range(1, int(L // 360) + 1):
        t = k * 360 / L
        LAMPS.append((ax + (bx - ax) * t + nx * 42, ay + (by - ay) * t + ny * 42))
TRACKS = [(a, b) for pts in TLINKS for a, b in zip(pts[:-1], pts[1:])]
for x, y in LAMPS:
    if any(r[0] - 4 < x < r[2] + 4 and r[1] - 4 < y < r[3] + 4 for h in HOUSES.values() for r in h['C']):
        continue
    if any(segdist((x, y), a, b) < 26 for a, b in TRACKS):        # на тропе-проезде фонарь не ставим
        continue
    dr.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(250, 226, 120), outline=(70, 70, 60), width=2)
for (p, col, horiz) in (((300, 882), (176, 64, 52), True), ((1300, 462), (210, 206, 190), True),
                        ((1957, 1050), (80, 110, 140), False), ((1190, 1735), (120, 140, 96), True),
                        ((1100, 150), (150, 150, 154), True)):
    x, y = T(*p)
    w, h = (36, 18) if horiz else (18, 36)
    dr.rectangle([x - w / 2, y - h / 2, x + w / 2, y + h / 2], fill=col, outline=(40, 40, 40), width=2)

# ================================================================ забор, номера
FENCEPTS = [(36, 1030), (36, 40), (772, 40), (772, 18), (1565, 18), (1565, 208), (2559, 208), (2559, 1047), (2448, 1047)]
dr.line([T(*p) for p in FENCEPTS], fill=FENCE, width=4)


def label(t, p, dark=False):
    x, y = p
    dr.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(40, 60, 80) if dark else (255, 255, 255), outline=(60, 70, 80), width=2)
    dr.text((x, y), t, font=F, fill=(255, 255, 255) if dark else (40, 50, 60), anchor='mm')


label('1', (380 + dB[0], 1662 + dB[1]), True)
label('2', (520 + dB[0], 1570 + dB[1]))
label('3', (1290 + dShop[0], 1662 + dShop[1]))
label('4', ((BOX[0] + BOX[2]) / 2, (BOX[1] + BOX[3]) / 2))
label('5', (2088 + dE[0], 1351 + dE[1]))
label('7', T(1150, 822))
label('9', (p9[0], p9[1] - 85))
dH3 = HOUSES['H3']['d']
label('10', (296 + dH3[0], 800 + dH3[1]))
label('11', T(395, 1075))
label('12', (p12[0], p12[1] - 112))
label('13', T(2300, 1420))
label('15', (24, T(0, 1068)[1])); label('16', T(2650, 1122)); label('17', T(1765, 1900))
img.save(OUT)
print('ok', OUT)
