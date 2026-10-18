"""Неблагополучный район — план v09 (TASK-000572): план Вадима v04 как есть (без новых домов), магазин уменьшен до реального
масштаба, гаражи расставлены логично (кооператив рядами с тупиковыми проездами, ряд у базы, ряды вдоль проездов).
Ранее v08 (TASK-000571): основа — утверждённый план Вадима v04 (дома из Планировка_v03.json
на своих местах), дорисовано плотнее и «карикатурнее» под погони: новые хрущёвки по краям, щели-тупики между домами,
гаражные массивы и пары гаражей, закоулки, база — гараж в Г-доме, ДК-притон, коробка, магазин. Без парковок.
Единицы — как в плане Вадима (1 ед. ≈ 0,22 м), y вниз. Не перезаписывает.
Запуск: python build_rough_v09.py -> Неблагополучный_район_v09.png + Легенда_v09.txt
"""
import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PNG = os.path.join(HERE, 'Неблагополучный_район_v09.png')
OUT_LEG = os.path.join(HERE, 'Легенда_v09.txt')
for p in (OUT_PNG, OUT_LEG):
    if os.path.exists(p):
        raise SystemExit(os.path.basename(p) + ' exists')
D = json.load(open(os.path.join(HERE, 'Планировка_v03.json'), encoding='utf-8'))
K = 1.35
W, H = int(1536 * K), int(1024 * K)
img = Image.new('RGB', (W, H), (206, 210, 198))
dr = ImageDraw.Draw(img, 'RGBA')
rnd = random.Random(808)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 15)
FS = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 13)
FT = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 22)


def P(x, y):
    return (x * K, y * K)


def rect(x0, y0, x1, y1, fill, out=None, w=1):
    x0, x1 = min(x0, x1), max(x0, x1)
    y0, y1 = min(y0, y1), max(y0, y1)
    dr.rectangle([P(x0, y0), P(x1, y1)], fill=fill, outline=out, width=w)


def poly(pts, fill, out=None, w=1):
    dr.polygon([P(*p) for p in pts], fill=fill, outline=out)
    if out and w > 1:
        dr.line([P(*p) for p in list(pts) + [pts[0]]], fill=out, width=w)


def line(pts, col, wu):
    dr.line([P(*p) for p in pts], fill=col, width=max(1, int(wu * K)), joint='curve')


NUMS = []


def num(lab, x, y):
    NUMS.append((lab, x, y))


# ---------------------------------------------------------------- земля
for _ in range(320):
    x, y, r = rnd.uniform(0, 1536), rnd.uniform(0, 1024), rnd.uniform(8, 28)
    col = rnd.choice(((190, 184, 146, 90), (176, 178, 152, 80), (164, 154, 134, 70)))
    dr.ellipse([P(x - r, y - r * 0.6), P(x + r, y + r * 0.6)], fill=col)

# ---------------------------------------------------------------- дороги Вадима: внешняя — асфальт с тротуаром, внутренние — разбитые
roads = D['roads']
outer, spurs, inner = roads[0], roads[1:4], roads[4:]
for pts in [outer] + spurs:
    line(pts, (176, 176, 170), 52)
for pts in [outer] + spurs:
    line(pts, (92, 96, 100), 34)
for _ in range(40):
    a, b = rnd.choice(list(zip(outer[:-1], outer[1:])))
    t = rnd.random()
    x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    rect(x - 5, y - 3, x + 6, y + 4, (80, 84, 88))


def worn(pts, w=22):
    line(pts, (128, 122, 112), w + 4)
    line(pts, (112, 110, 104), w)
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.dist(a, b)
        for k in range(int(L / 30)):
            t = rnd.random()
            x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            r = rnd.uniform(3, 7)
            if rnd.random() < 0.5:
                dr.ellipse([P(x - r, y - r * 0.7), P(x + r, y + r * 0.7)], fill=(120, 140, 150, 160))
            else:
                rect(x - r, y - r * 0.6, x + r, y + r * 0.6, (96, 94, 90))


for pts in inner:
    worn(pts)
EXTRA_LANES = [[(405, 809), (405, 714), (353, 714)]]
for pts in EXTRA_LANES:
    worn(pts, 20)
for pts in ([(250, 809), (270, 760)], [(700, 809), (690, 770)], [(1240, 809), (1230, 760)]):
    line(pts, (150, 140, 120), 6)

# ---------------------------------------------------------------- хрущёвки (все серые): дома Вадима + новые
GREY, GREY_OUT = (150, 152, 152), (70, 72, 74)


def roofboxes(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    horiz = (x1 - x0) > (y1 - y0)
    L = (x1 - x0) if horiz else (y1 - y0)
    n = max(1, int(L / 62))
    for k in range(n):
        t = (k + 0.5) / n
        cx, cy = (x0 + (x1 - x0) * t, (y0 + y1) / 2) if horiz else ((x0 + x1) / 2, y0 + (y1 - y0) * t)
        if pts_inside((cx, cy), pts):
            rect(cx - 6, cy - 6, cx + 6, cy + 6, (128, 130, 130), GREY_OUT)


def pts_inside(pt, pl):
    x, y = pt
    c = False
    for i in range(len(pl)):
        (x0, y0), (x1, y1) = pl[i], pl[(i + 1) % len(pl)]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / ((y1 - y0) or 1e-9) + x0:
            c = not c
    return c


def house(pts, new=False):
    poly([(x + 5, y + 7) for x, y in pts], (60, 64, 66, 70))
    poly(pts, GREY, GREY_OUT, 2)
    if new:
        poly(pts, None, (40, 90, 150), 2)                      # новые дома v08 — синяя обводка на схеме
    roofboxes(pts)


def R(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


for b in D['buildings']:
    if b['id'] in ('den', 'blind_alley_closed_end'):
        continue
    house(b['polygon'])
NEW_HOUSES = []
# арки Вадима: двор-колодец и подворотня
for (x0, y0, x1, y1) in ((243, 281, 278, 326), (279, 495, 315, 532)):
    rect(x0, y0, x1, y1, (190, 188, 180))
    line([(x0, y0), (x0, y1)], GREY_OUT, 2); line([(x1, y0), (x1, y1)], GREY_OUT, 2)
num('09', 232, 238); num('10', 260, 344); num('11', 298, 445)


def garages(x0, y, n, face, w=15, d=27, vertical=False):
    for k in range(n):
        col = rnd.choice(((122, 98, 82), (96, 112, 124), (112, 120, 100), (130, 110, 92), (104, 104, 108), (140, 90, 70)))
        if not vertical:
            gx = x0 + k * w
            rect(gx, y, gx + w, y + d, col, (60, 60, 60))
            dy = y + d - 2 if face == 'S' else y
            rect(gx + 2, dy, gx + w - 2, dy + 2, (50, 52, 54))
        else:
            gy = y + k * w
            rect(x0, gy, x0 + d, gy + w, col, (60, 60, 60))
            dx = x0 + d - 2 if face == 'E' else x0
            rect(dx, gy + 2, dx + 2, gy + w - 2, (50, 52, 54))


def nook(pts, lab, at):
    poly(pts, (84, 86, 90, 230), (40, 42, 46))
    num(lab, *at)


# ---------------------------------------------------------------- 07 гаражный кооператив: 3 ряда, ворота к проездам, тупиковые проезды
garages(600, 214, 16, 'S'); garages(600, 280, 16, 'N'); garages(600, 307, 16, 'S')
rect(598, 241, 842, 280, (112, 110, 104)); rect(598, 334, 842, 352, (112, 110, 104))
rect(840, 241, 846, 280, (50, 50, 50))                                       # глухой конец проезда — тупик
num('07', 720, 260)
rect(855, 300, 880, 325, (190, 110, 80), (90, 50, 30), 2); num('06', 868, 292)
# 05 притон-клуб — двухэтажный бывший ДК с неоном (на месте притона Вадима)
rect(669, 436, 871, 500, (116, 100, 120), (50, 40, 60), 2)
rect(680, 432, 860, 437, (236, 90, 200))
for x in (690, 720, 750, 780, 810, 840):
    dr.ellipse([P(x, 418), P(x + 7, 425)], fill=(190, 186, 176), outline=(90, 90, 90))
num('05', 770, 468)
nook(R(669, 500, 720, 530), '15', (700, 515))
# 04 футбольная коробка (как у Вадима, проработана)
bx0, by0, bx1, by1 = 680, 555, 860, 670
rect(bx0 - 5, by0 - 5, bx1 + 5, by1 + 5, (120, 96, 70))
rect(bx0, by0, bx1, by1, (108, 140, 96))
for _ in range(18):
    x, y, r = rnd.uniform(bx0 + 8, bx1 - 8), rnd.uniform(by0 + 8, by1 - 8), rnd.uniform(3, 9)
    dr.ellipse([P(x - r, y - r * 0.7), P(x + r, y + r * 0.7)], fill=(150, 150, 120))
dr.rectangle([P(bx0, by0), P(bx1, by1)], outline=(230, 232, 226), width=2)
line([((bx0 + bx1) / 2, by0), ((bx0 + bx1) / 2, by1)], (230, 232, 226), 1.5)
cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
dr.ellipse([P(cx - 13, cy - 13), P(cx + 13, cy + 13)], outline=(230, 232, 226), width=2)
dr.rectangle([P(bx0 - 7, by0 - 7), P(bx1 + 7, by1 + 7)], outline=(60, 64, 70), width=2)
rect(bx1 - 40, by1 + 5, bx1 - 22, by1 + 9, (206, 210, 198)); rect(bx0 + 25, by0 - 9, bx0 + 40, by0 - 6, (206, 210, 198))
for px, py in ((bx0 - 11, by0 - 11), (bx1 + 11, by1 + 11)):
    dr.ellipse([P(px - 4, py - 4), P(px + 4, py + 4)], fill=(250, 230, 120), outline=(90, 80, 40))
num('04', cx, cy)
# 03 магазин 24 ч у южной дороги — реальный масштаб ~20×10 м
rect(721, 722, 811, 767, (186, 120, 96), (90, 50, 40), 2); rect(721, 764, 811, 768, (250, 220, 140))
num('03', 766, 744)

# ---------------------------------------------------------------- 01 база: гараж в первом этаже Г-дома Вадима, дворик за гаражами
rect(318, 738, 346, 744, (60, 64, 68))                                    # ворота гаража базы в фасаде (вход Вадима 328,742)
rect(250, 650, 368, 738, (166, 164, 156), (130, 128, 120))                # дворик базы
rect(300, 690, 345, 712, (220, 220, 214, 0), (40, 60, 90), 2)              # место бусика
garages(250, 616, 7, 'S')                                                  # прикрывают дворик с севера
num('01', 300, 763); num('02', 335, 700); num('18', 300, 605)

# ---------------------------------------------------------------- гаражи по логике района
garages(1080, 690, 5, 'N'); num('17', 1117, 682)                             # во глухом дворе 13, вдоль его края
garages(150, 470, 6, 'E', vertical=True)                                     # ряд вдоль западной дороги, ворота во двор
garages(1330, 440, 10, 'W', vertical=True)                                   # ряд вдоль восточной дороги, ворота к домам
nook(R(986, 503, 1035, 520), '14', (1011, 549))                               # глухая подворотня Вадима
for (x, y) in ((574, 386), (1000, 700), (200, 590)):
    for k in range(3):
        rect(x + k * 10, y, x + k * 10 + 8, y + 7, (70, 110, 80), (40, 60, 44))
num('08', 574, 400)
num('12', 1123, 255); num('13', 1123, 637)
TREES = [(220, 160), (300, 200), (1100, 170), (1130, 280), (250, 470), (1100, 620), (600, 300), (900, 300), (1200, 420)]
for x, y in TREES:
    dr.ellipse([P(x - 3, y - 3), P(x + 3, y + 3)], fill=(90, 70, 56))
    for a in range(0, 360, 60):
        a2 = a + rnd.uniform(-20, 20); L = rnd.uniform(9, 15)
        line([(x, y), (x + L * math.cos(math.radians(a2)), y + L * math.sin(math.radians(a2)))], (100, 82, 66), 1.4)
CARS = [(160, 380, 'v'), (600, 700, 'v'), (880, 200, 'v'), (1200, 360, 'h'), (1240, 740, 'h'), (480, 560, 'v')]
for x, y, o in CARS:
    col = rnd.choice(((176, 64, 52), (210, 206, 190), (80, 110, 140), (120, 140, 96)))
    rect(x, y, x + (19 if o == 'h' else 8), y + (8 if o == 'h' else 19), col, (40, 40, 40))
for x, y in ((130, 300), (130, 600), (500, 820), (900, 820), (1380, 300), (1380, 600), (1000, 100), (620, 420)):
    on = rnd.random() < 0.55
    dr.ellipse([P(x - 4, y - 4), P(x + 4, y + 4)], fill=(250, 230, 140) if on else (90, 90, 90), outline=(50, 50, 50))

for lab, x, y in NUMS:
    px, py = P(x, y)
    dr.ellipse([px - 13, py - 13, px + 13, py + 13], fill=(255, 255, 255), outline=(40, 52, 70), width=2)
    dr.text((px, py), lab, font=F, fill=(40, 52, 70), anchor='mm')
dr.rectangle([12, 10, 1180, 64], fill=(255, 255, 255), outline=(140, 160, 170))
dr.text((24, 18), 'НЕБЛАГОПОЛУЧНЫЙ РАЙОН · план v09 — план Вадима v04: магазин в реальном масштабе, гаражи по логике', font=FT, fill=(40, 52, 70))
dr.text((24, 44), 'Дома и дворы Вадима без изменений · 07 гаражный кооператив (3 ряда, тупиковый проезд) · 18 ряд у базы · ряды вдоль дорог · 1 ед. ≈ 0,22 м',
        font=FS, fill=(100, 110, 116))
img.save(OUT_PNG)
open(OUT_LEG, 'w', encoding='utf-8-sig').write('''НЕБЛАГОПОЛУЧНЫЙ РАЙОН — ЛЕГЕНДА v09 (план Вадима v04, Планировка_v03.json)
Дома, дворы, арки и дороги Вадима без изменений. Изменено: магазин 03 уменьшен до ~20×10 м; гаражи расставлены по логике района:
07 — гаражный кооператив за северным рядом: 3 ряда по 16, ворота к двум проездам, один проезд тупиковый (глухой конец справа); 06 шаурма у выезда.
18 — ряд гаражей прикрывает дворик базы 01/02 с севера. 17 — 5 гаражей вдоль края глухого двора 13.
Ряд из 6 гаражей вдоль западной дороги (ворота во двор), ряд из 10 вдоль восточной дороги (ворота к домам).
Остальное как у Вадима: 04 коробка, 05 притон (ДК), 08 мусорки, 09/10 двор-колодец с аркой, 11 подворотня, 12 тихий двор, 13 глухой двор, 14 глухая подворотня.
''')

print('ok', OUT_PNG)
