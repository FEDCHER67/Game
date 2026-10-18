"""Неблагополучный район — план v39 (TASK-000605), от v36 (+ изменения v37/v38 повторены):
- подъездов меньше (~на 20 %), равномерно; у большинства подъездов лавочки: где одна, где две по бокам, у части нет;
- дворовые проезды (разбитый асфальт без бордюров): с западной дороги через арку к центру и к востоку,
  в двор 9, двор 12, к гаражам у северного забора, к базе, от южной дороги у коробки;
- двор 9 и двор 12: типичная детская площадка (аккуратный прямоугольник с бортиком: качели, горка, песочница)
  и рядом мусорная секция (профлист, 2 больших бункера + 3 зелёных бака), открыта к проезду;
- фонари вдоль проездов и внешней дороги; 5 машин у подъездов, у магазина, у гаражей; граффити на части гаражей.
Земля в районе ровная (небольшие неровности только для вида). Не перезаписывает.
Запуск: python build_rough_v39.py -> Неблагополучный_район_v39.png
"""
import os
import random

from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v36.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v39.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
FENCE = (112, 119, 119)
DOOR, DOOR_OUT = (96, 106, 116), (50, 58, 66)
BENCH, BENCH_OUT = (150, 112, 80), (90, 64, 44)
DRIVE = (156, 152, 144)
BIN, BIN_OUT = (104, 140, 104), (52, 74, 56)
SKIP, SKIP_OUT = (84, 120, 92), (40, 60, 46)
rnd = random.Random(39)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)

# ================================================= изменения v37 (верхний центр выше, гаражи у базы)
dr.rectangle([776, 18, 1561, 470], fill=BG)
dr.rectangle([772, 18, 775, 44], fill=FENCE)
dr.rectangle([772, 18, 1565, 21], fill=FENCE)
dr.rectangle([1562, 18, 1565, 208], fill=FENCE)
NORTH_GAR = [(905 + k * 45, 50) for k in range(12)]
for gx, gy in NORTH_GAR:
    dr.rectangle([gx, gy, gx + 45, gy + 68], fill=GAR, outline=GAR_OUT, width=2)
    dr.rectangle([gx + 6, gy + 63, gx + 39, gy + 66], fill=(80, 96, 104))
dr.rectangle([859, 180, 1172, 285], fill=FILL, outline=OUTL, width=3)
dr.rectangle([1175, 288, 1491, 393], fill=FILL, outline=OUTL, width=3)
dr.rectangle([468, 1456, 544, 1536], fill=BG)
dr.rectangle([540, 1390, 585, 1458], fill=GAR, outline=GAR_OUT, width=2)
dr.rectangle([546, 1453, 579, 1456], fill=(80, 96, 104))
for k in range(2):
    gy = 1458 + k * 37
    dr.rectangle([517, gy, 585, gy + 37], fill=GAR, outline=GAR_OUT, width=2)
    dr.rectangle([519, gy + 6, 522, gy + 31], fill=(80, 96, 104))
dr.rectangle([118, 216, 702, 222], fill=BG)
dr.rectangle([118, 672, 540, 682], fill=BG)
dr.rectangle([118, 852, 540, 860], fill=BG)
dr.rectangle([121, 216, 220, 222], fill=FILL)
dr.rectangle([118, 210, 120, 225], fill=OUTL)
dr.rectangle([118, 573, 540, 670], outline=OUTL, width=3)

# ================================================= дворовые проезды — только по свободной земле
DRIVES = [
    (137, 882, 182, 1065),     # от угла западной дороги вверх
    (137, 882, 760, 927),      # к арке между вертикалями и дальше
    (760, 882, 810, 1035),     # ступенька вниз
    (760, 990, 2445, 1035),    # к востоку через арку у двора 12 до восточной дороги
    (565, 255, 610, 930),      # в двор 9 (между домом над 10 и вертикалью)
    (230, 255, 610, 300),      # вдоль Г-дома двора 9
    (565, 420, 1590, 465),     # между верхними домами и средним длинным
    (790, 120, 835, 465),      # к гаражам у северного забора
    (790, 120, 1495, 165),     # проезд перед гаражами
    (1900, 600, 1945, 1035),   # в двор 12
    (1530, 1035, 1575, 1743),  # от южной дороги у коробки
    (600, 1532, 645, 1743),    # к базе от южной дороги
    (505, 1555, 645, 1600),    # к дворику бусика
]
layer = Image.new('L', img.size, 0)
ld = ImageDraw.Draw(layer)
for r in DRIVES:
    ld.rectangle(r, fill=255)
bgmask = ImageChops.difference(img, Image.new('RGB', img.size, BG)).convert('L').point(lambda v: 255 if v == 0 else 0)
mask = ImageChops.multiply(bgmask, layer)
img = Image.composite(Image.new('RGB', img.size, DRIVE), img, mask)
dr = ImageDraw.Draw(img)


# ================================================= подъезды и лавочки
def bench(x0, y0, x1, y1):
    dr.rectangle([x0, y0, x1, y1], fill=BENCH, outline=BENCH_OUT)


def door(side, x, y):
    if side == 'S':
        dr.rectangle([x - 11, y + 2, x + 11, y + 9], fill=DOOR, outline=DOOR_OUT)
    elif side == 'N':
        dr.rectangle([x - 11, y - 9, x + 11, y - 2], fill=DOOR, outline=DOOR_OUT)
    elif side == 'E':
        dr.rectangle([x + 2, y - 11, x + 9, y + 11], fill=DOOR, outline=DOOR_OUT)
    else:
        dr.rectangle([x - 9, y - 11, x - 2, y + 11], fill=DOOR, outline=DOOR_OUT)
    r = rnd.random()
    pattern = 'none' if r < 0.2 else ('one' if r < 0.65 else 'two')
    sides = [] if pattern == 'none' else ([rnd.choice((-1, 1))] if pattern == 'one' else [-1, 1])
    for s in sides:                                   # лавочка сбоку от входа, вдоль фасада
        if side in 'SN':
            by = y + 14 if side == 'S' else y - 22
            bx = x + s * 34
            bench(bx - 13, by, bx + 13, by + 8)
        else:
            bx = x + 14 if side == 'E' else x - 22
            by = y + s * 34
            bench(bx, by - 13, bx + 8, by + 13)


def doors(side, a, b, fixed, n, skip=None):
    for k in range(n):
        t = a + (b - a) * (k + 0.5) / n
        if skip and skip[0] - 20 <= t <= skip[1] + 20:
            t = skip[0] - 45 if t < (skip[0] + skip[1]) / 2 else skip[1] + 45
        door(side, t, fixed) if side in 'SN' else door(side, fixed, t)


doors('S', 223, 700, 215, 3)                             # СЗ Г: перекладина
doors('E', 215, 480, 223, 1)                             # СЗ Г: ножка
doors('N', 120, 534, 573, 2)                             # дом над 10
doors('S', 120, 534, 849, 2, skip=(267, 324))            # дом 10
doors('E', 486, 858, 759, 2)                             # вертикаль у двора 9 — только направо
doors('S', 859, 1172, 285, 2)                            # верхний центр, левый
doors('S', 1175, 1491, 393, 2)                           # верхний центр, правый
doors('S', 864, 1482, 591, 4)                            # средний длинный
doors('S', 1590, 2301, 360, 4)                           # северо-восточный длинный
doors('S', 1790, 2213, 555, 3, skip=(2000, 2052))        # Г двора 12: перекладина
doors('W', 555, 950, 2213, 2)                            # Г двора 12: ножка
doors('E', 489, 951, 1701, 2)                            # вертикаль у двора 12
doors('E', 1011, 1141, 294, 1)                           # дом 11: левое крыло
doors('W', 938, 1141, 493, 1)                            # дом 11: правое крыло
doors('N', 294, 493, 1141, 2, skip=(368, 440))           # дом 11: низ
doors('E', 960, 1410, 759, 2)                            # вертикаль слева-посередине
doors('S', 1107, 1482, 1167, 2)                          # горизонтальный у коробки
doors('E', 1125, 1653, 951, 2)                           # вертикаль у коробки
doors('E', 1062, 1458, 1701, 2)                          # длинный у молнии
doors('S', 2155, 2405, 1245, 2)                          # молния: верхнее крыло
doors('S', 1707, 2155, 1560, 2, skip=(1860, 1912))       # молния: нижнее крыло
doors('E', 1389, 1610, 295, 1)                           # база: ножка Г


# ================================================= детские площадки + мусорные секции (дворы 9 и 12)
def playground(x0, y0, x1, y1):
    dr.rectangle([x0, y0, x1, y1], fill=(222, 206, 160), outline=(120, 100, 70), width=3)   # бортик по периметру
    w, h = x1 - x0, y1 - y0
    sx0, sy0 = x0 + 12, y0 + 12                                       # качели: рама + 2 сиденья
    dr.line([(sx0, sy0), (sx0 + 60, sy0)], fill=(90, 80, 70), width=4)
    for k in (18, 42):
        dr.rectangle([sx0 + k - 5, sy0 + 8, sx0 + k + 5, sy0 + 14], fill=(170, 60, 50))
    gx0, gy0 = x1 - 62, y0 + 14                                        # горка: лестница + скат
    dr.rectangle([gx0, gy0, gx0 + 16, gy0 + 16], fill=(120, 130, 150), outline=(70, 70, 80))
    dr.rectangle([gx0 + 16, gy0 + 4, gx0 + 52, gy0 + 12], fill=(200, 80, 60), outline=(110, 50, 40))
    px0, py0 = x0 + w // 2 - 28, y1 - 48                               # песочница
    dr.rectangle([px0, py0, px0 + 56, py0 + 36], fill=(236, 214, 150), outline=(140, 100, 60), width=3)


def trash_section(x0, y0, open_side='E'):
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


playground(270, 350, 450, 480)        # двор 9
trash_section(480, 330, 'E')          # рядом, открыта к проезду
playground(1735, 640, 1885, 770)      # двор 12
trash_section(1815, 820, 'E')         # рядом, открыта к проезду

# ================================================= фонари
LAMPS = [(420, 873), (520, 873), (820, 982), (1080, 982), (1350, 982), (1800, 982), (2100, 982), (2370, 982),
         (620, 420), (620, 640), (230, 320), (930, 412), (1220, 412), (1500, 412), (850, 175),
         (1955, 760), (1585, 1250), (1585, 1520),
         (700, 1735), (1100, 1735), (1430, 1735), (1950, 1735), (2300, 1735),
         (145, 1250), (145, 1520), (2438, 1350), (2438, 1600)]
for x, y in LAMPS:
    dr.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(250, 226, 120), outline=(70, 70, 60), width=2)

# ================================================= машины
CARS = [((300, 858, 336, 876), (176, 64, 52)), ((1300, 468, 1336, 486), (210, 206, 190)),
        ((1950, 850, 1968, 886), (80, 110, 140)), ((1180, 1700, 1216, 1718), (120, 140, 96)),
        ((1100, 124, 1136, 142), (150, 150, 154))]
for (x0, y0, x1, y1), col in CARS:
    dr.rectangle([x0, y0, x1, y1], fill=col, outline=(40, 40, 40), width=2)

# ================================================= граффити на гаражах
TAG = ((214, 60, 150), (40, 160, 170), (230, 190, 40), (90, 90, 200))


def tag(x, y, w):
    pts = [(x + i * w / 6, y + (4 if i % 2 else -4)) for i in range(7)]
    dr.line(pts, fill=rnd.choice(TAG), width=3)


for k in (1, 4, 5, 9):
    gx, gy = NORTH_GAR[k]
    tag(gx + 4, gy + 30, 36)
for gx in (980, 1070, 1250):
    tag(gx, 735, 34)
    tag(gx + 20, 912, 34)
for gy in (560, 700, 840):
    tag(2360, gy, 40)
tag(380, 1420, 34)
img.save(OUT)
print('ok', OUT)
