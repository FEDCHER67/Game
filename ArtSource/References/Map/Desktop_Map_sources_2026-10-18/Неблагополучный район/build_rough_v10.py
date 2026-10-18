"""Неблагополучный район — план v10 (TASK-000573): v09 без внутренних проездов и «кочек» на земле, притон — компактный
двухэтажный клуб, мусорки у выходов из дворов, гаражи: кооператив 2 ряда + ряд по северному краю + ряд у базы.
Ранее v09 (TASK-000572): план Вадима v04 как есть (без новых домов), магазин уменьшен до реального
масштаба, гаражи расставлены логично (кооператив рядами с тупиковыми проездами, ряд у базы, ряды вдоль проездов).
Ранее v08 (TASK-000571): основа — утверждённый план Вадима v04 (дома из Планировка_v03.json
на своих местах), дорисовано плотнее и «карикатурнее» под погони: новые хрущёвки по краям, щели-тупики между домами,
гаражные массивы и пары гаражей, закоулки, база — гараж в Г-доме, ДК-притон, коробка, магазин. Без парковок.
Единицы — как в плане Вадима (1 ед. ≈ 0,22 м), y вниз. Не перезаписывает.
Запуск: python build_rough_v10.py -> Неблагополучный_район_v10.png + Легенда_v10.txt
"""
import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PNG = os.path.join(HERE, 'Неблагополучный_район_v10.png')
OUT_LEG = os.path.join(HERE, 'Легенда_v10.txt')
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


# ---------------------------------------------------------------- гаражи
garages(610, 222, 15, 'S'); garages(610, 296, 15, 'N')                     # 07 кооператив: 2 ряда лицом друг к другу
rect(608, 249, 836, 296, (150, 146, 136))                                   # проезд между рядами (утоптанный)
rect(834, 249, 840, 296, (60, 60, 60))                                      # глухой конец — тупик
num('07', 720, 272)
rect(850, 262, 875, 287, (190, 110, 80), (90, 50, 30), 2); num('06', 862, 254)   # шаурма у въезда в кооператив
garages(1033, 70, 13, 'N'); garages(146, 70, 11, 'N')                      # ряды по северному краю района, за домами
# 05 притон-клуб — компактный двухэтажный клуб: облезлый, окна заклеены, у входа козырёк и неон-сердечко
rect(712, 432, 830, 500, (146, 126, 118), (70, 56, 50), 2)
rect(752, 500, 790, 512, (110, 100, 96), (60, 50, 46))                      # козырёк над входом
dr.ellipse([P(766, 502), P(776, 510)], fill=(236, 90, 170))                  # маленькое неоновое сердечко
num('05', 771, 466)
nook(R(830, 470, 871, 500), '15', (850, 485))                                # глухой закуток сбоку клуба
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

# ---------------------------------------------------------------- мусорки: у выходов из дворов, у магазина и у клуба
for (x, y) in ((300, 340), (395, 545), (1180, 300), (1180, 745), (835, 780), (700, 512)):
    rect(x - 3, y - 3, x + 31, y + 10, (170, 168, 160), (120, 118, 112))      # бетонная площадка
    for k in range(3):
        rect(x + k * 10, y, x + k * 10 + 8, y + 7, (70, 110, 80), (40, 60, 44))
num('08', 312, 330)
nook(R(986, 503, 1035, 520), '14', (1011, 549))
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
dr.text((24, 18), 'НЕБЛАГОПОЛУЧНЫЙ РАЙОН · план v10 — план Вадима v04: без внутренних проездов, клуб, мусорки, гаражи', font=FT, fill=(40, 52, 70))
dr.text((24, 44), 'Дома и дворы Вадима без изменений · 07 кооператив 2 ряда (тупик) · ряды гаражей по северному краю · 18 ряд у базы · мусорки у выходов из дворов',
        font=FS, fill=(100, 110, 116))
img.save(OUT_PNG)
open(OUT_LEG, 'w', encoding='utf-8-sig').write('''НЕБЛАГОПОЛУЧНЫЙ РАЙОН — ЛЕГЕНДА v10 (план Вадима v04)
Дома, дворы, арки Вадима без изменений; внутренние проезды пока убраны (только дорога-подкова вокруг и выезды), «кочки» на земле убраны.
05 Притон-клуб — компактный двухэтажный облезлый клуб ~26×15 м, окна заклеены, козырёк над входом, маленькое неоновое сердечко; 15 — закуток сбоку.
07 Гаражный кооператив — 2 ряда по 15 лицом друг к другу, проезд между ними с глухим концом; 06 шаурма у въезда.
Ряды гаражей по северному краю района за домами (11 и 13 шт.). 18 — ряд прикрывает дворик базы 01/02.
08 Мусорки (6) на бетонных площадках: у выхода из двора-колодца, у подворотни 11, у тихого 12 и глухого 13 дворов, у магазина, у клуба.
03 Магазин ~20×10 м. 04 Коробка. 09/10 колодец с аркой, 11 подворотня, 12 тихий двор, 13 глухой двор, 14 глухая подворотня.
''')


print('ok', OUT_PNG)
