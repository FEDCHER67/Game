"""Порт (район 06) — план v03 (TASK-000630): сыпучка и самосвал убраны; на их месте водонапорная башня и кирпичная насосная —
статичные «эстетичные» постройки. Ранее v02 (TASK-000629): экскаватор убран совсем, лишнего не добавляем. Ранее v01 (TASK-000628). Поверх общей карты v17, окно x 912…1112, y 528…684 м мира, 6 px/м.
Вадим: «уже всё нравится», козловой кран не нужен, контейнеров меньше и расставить лучше, добавить типичные портовые мелочи
(экскаваторы и т. п.). Северная половина (КПП 01, склад 02, баки 05) остаётся; южная площадка перерисована начисто.
Не перезаписывает. Запуск: python build_port_v03.py -> Порт_v03.png (+ _world.png, .json, Легенда_v03.txt)
"""
import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
MAPPNG = r'C:\Users\chern_0eqkb03\Desktop\Map\Итоговая карта\VOLUNTEERS_MAP_FINAL_v17.png'
OUT, OWD, OJS, OLG = (os.path.join(HERE, n) for n in ('Порт_v03.png', 'Порт_v03_world.png', 'Порт_v03.json', 'Легенда_v03.txt'))
for p in (OUT, OWD, OJS, OLG):
    if os.path.exists(p):
        raise SystemExit(os.path.basename(p) + ' exists')

X0, X1, Y0, Y1, K = 912.0, 1112.0, 528.0, 684.0, 6.0
big = Image.open(MAPPNG).convert('RGB')
img = big.crop((int(X0 * 5), int(4200 - Y1 * 5), int(X1 * 5), int(4200 - Y0 * 5))).resize((int((X1 - X0) * K), int((Y1 - Y0) * K)), Image.LANCZOS)
W, H = img.size
dr = ImageDraw.Draw(img, 'RGBA')
rnd = random.Random(6)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 16)
FS = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 14)
FT = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 22)
CONC = (203, 207, 209)
EXP = {}


def P(x, y):
    return ((x - X0) * K, (Y1 - y) * K)


def PL(pts):
    return [P(*p) for p in pts]


def rect(x0, y0, x1, y1, fill, out=None, w=1):
    dr.rectangle([P(min(x0, x1), max(y0, y1)), P(max(x0, x1), min(y0, y1))], fill=fill, outline=out, width=w)


def dot(x, y, r, fill, out=None, w=1):
    dr.ellipse([P(x - r, y + r), P(x + r, y - r)], fill=fill, outline=out, width=w)


def line(pts, col, wm):
    dr.line(PL(pts), fill=col, width=max(1, int(round(wm * K))), joint='curve')


def rpts(cx, cy, w, h, ang):                                                   # w — вдоль оси ang, h — поперёк
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca) for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


def rpoly(cx, cy, w, h, ang, fill, out=None, wd=1):
    dr.polygon(PL(rpts(cx, cy, w, h, ang)), fill=fill, outline=out, width=wd)


def local(cx, cy, ang, dx, dy):
    ca, sa = math.cos(ang), math.sin(ang)
    return (cx + dx * ca - dy * sa, cy + dx * sa + dy * ca)


# ---------------------------------------------------------------- 0. южная площадка начисто (контейнеры-кирпичи, кран, рельсы, «04»)
rect(950.5, 545.0, 1074.5, 583.3, CONC)
for k in range(14):                                                            # пятна масла на бетоне — немного и бледно
    x, y = rnd.uniform(952, 1072), rnd.uniform(547, 582)
    rx, ry = rnd.uniform(0.6, 1.8), rnd.uniform(0.4, 1.1)
    dr.ellipse([P(x - rx, y + ry), P(x + rx, y - ry)], fill=(50, 52, 54, rnd.randint(18, 34)))

CCOL = [(176, 74, 58), (62, 100, 150), (72, 122, 92), (206, 120, 52), (128, 132, 138), (118, 52, 60), (214, 176, 64)]
CONT = []


def container(cx, cy, L, ang, col, tiers=1, doors_open=False):
    sh = 0.55 * tiers                                                          # тень к юго-востоку = высота штабеля
    rpoly(cx + sh, cy - sh, L, 2.44, ang, (40, 44, 48, 70))
    rpoly(cx, cy, L, 2.44, ang, col, (40, 36, 34), 1)
    n = int(L / 0.9)
    for i in range(1, n):                                                      # гофра поперёк
        a = local(cx, cy, ang, -L / 2 + i * L / n, -1.1)
        b = local(cx, cy, ang, -L / 2 + i * L / n, 1.1)
        line([a, b], tuple(min(255, c + 22) for c in col), 0.06)
    if tiers > 1:                                                              # верхний ярус чуть светлее, по краю — полоса
        rpoly(cx, cy, L - 0.4, 2.0, ang, None, tuple(min(255, c + 45) for c in col), 1)
    if doors_open:
        for s in (-1, 1):
            a = local(cx, cy, ang, L / 2, s * 1.2)
            b = local(cx, cy, ang, L / 2 + 1.1, s * 1.9)
            line([a, b], (40, 36, 34), 0.18)
    CONT.append({'c': [round(cx, 2), round(cy, 2)], 'len': L, 'angle': round(ang, 3), 'tiers': tiers})


# ---------------------------------------------------------------- 1. контейнеры: два небольших штабеля + несколько вразнобой (04)
for row, cols in enumerate(((2, 1), (3, 0), (1, 2), (0, 1))):                 # штабель А: 40-футовые, 4 ряда × 2, ярусы 0–3
    for c, t in enumerate(cols):
        if t:
            container(955.2 + 6.15 + c * 12.5, 563.4 + row * 2.6, 12.2, 0.0, rnd.choice(CCOL), t)
for row, cols in enumerate(((1, 2, 0), (2, 1, 1), (0, 1, 0))):                # штабель Б: 20-футовые, 3 ряда × 3
    for c, t in enumerate(cols):
        if t:
            container(990.5 + 3.05 + c * 6.35, 563.4 + row * 2.6, 6.1, 0.0, rnd.choice(CCOL), t)
container(1017.5, 556.5, 6.1, 0.42, (176, 74, 58), 1, doors_open=True)          # открытый, у дверей ящики
for k in range(5):
    rpoly(1022.2 + (k % 3) * 1.3, 554.8 + (k // 3) * 1.3 + rnd.uniform(-0.2, 0.2), 1.1, 1.1, rnd.uniform(-0.3, 0.3), (176, 140, 96), (110, 84, 56))
container(1031.0, 571.0, 6.1, -0.12, (128, 132, 138), 1)                       # ржавый одиночка у края
EXP['containers'] = CONT

# ---------------------------------------------------------------- 2. техника: ричстакер, фура с контейнером, экскаватор, самосвал, погрузчики
RS = (1000.0, 554.0)                                                           # ричстакер (контейнерный погрузчик) несёт 20-футовый
rpoly(RS[0] + 0.5, RS[1] - 0.5, 4.2, 7.2, 0.0, (40, 44, 48, 70))
rpoly(RS[0], RS[1], 4.2, 7.2, 0.0, (232, 178, 40), (90, 70, 20), 2)
rect(RS[0] - 2.4, RS[1] - 2.2, RS[0] - 1.0, RS[1] + 0.2, (70, 90, 110), (40, 40, 40))   # кабина
rect(RS[0] - 0.5, RS[1] - 1.0, RS[0] + 0.5, RS[1] + 5.6, (200, 150, 30), (90, 70, 20))  # стрела
container(RS[0], RS[1] + 6.0, 6.1, 0.0, (62, 100, 150), 1)
TRUCK = (1022.0, 578.6)                                                        # фура: прицеп с 40-футовым, тягач к выезду на дорогу
rect(TRUCK[0] - 7.5, TRUCK[1] - 1.3, TRUCK[0] + 6.5, TRUCK[1] + 1.3, (70, 72, 76), (30, 30, 30))
container(TRUCK[0] - 0.5, TRUCK[1], 12.2, 0.0, (72, 122, 92), 1)
rect(TRUCK[0] + 7.0, TRUCK[1] - 1.25, TRUCK[0] + 10.6, TRUCK[1] + 1.25, (210, 60, 50), (60, 20, 20), 1)
rect(TRUCK[0] + 9.6, TRUCK[1] - 1.1, TRUCK[0] + 10.5, TRUCK[1] + 1.1, (70, 90, 110))
WT = (1063.0, 559.0)                                                           # водонапорная башня: бак на опорах (вид сверху)
for a in range(4):
    t = math.pi / 4 + a * math.pi / 2
    rect(WT[0] + 3.6 * math.cos(t) - 0.35 + 1.2, WT[1] + 3.6 * math.sin(t) - 0.35 - 1.2, WT[0] + 3.6 * math.cos(t) + 0.35 + 1.2, WT[1] + 3.6 * math.sin(t) + 0.35 - 1.2, (40, 44, 48, 60))
dot(WT[0] + 2.2, WT[1] - 2.2, 4.6, (40, 44, 48, 70))                          # тень высокой башни
dot(WT[0], WT[1], 4.6, (150, 176, 190), (70, 90, 100), 2)
dot(WT[0], WT[1], 3.0, (172, 196, 208), (110, 130, 140), 1)
for a in range(8):                                                             # швы конической крыши
    t = a * math.pi / 4
    line([(WT[0] + 0.5 * math.cos(t), WT[1] + 0.5 * math.sin(t)), (WT[0] + 4.4 * math.cos(t), WT[1] + 4.4 * math.sin(t))], (110, 130, 140), 0.08)
dot(WT[0], WT[1], 0.6, (90, 100, 110))
PH = (1044.0, 551.0, 1054.0, 558.0)                                            # кирпичная насосная, двускатная крыша
rect(PH[0] + 0.8, PH[1] - 0.8, PH[2] + 0.8, PH[3] - 0.8, (40, 44, 48, 70))
rect(*PH, (160, 78, 60), (90, 40, 30), 2)
rect(PH[0], (PH[1] + PH[3]) / 2 - 0.15, PH[2], (PH[1] + PH[3]) / 2 + 0.15, (110, 50, 38))
for x in (1046.5, 1051.5):
    rect(x - 0.6, PH[1] - 0.2, x + 0.6, PH[1] + 0.2, (70, 70, 74))           # окошки по южной стене
line([(PH[2], 554.5), (WT[0] - 4.6, 556.0)], (110, 116, 122), 0.4)          # труба от насосной к башне
EXP['water_tower'] = {'center': list(WT), 'tank_r': 4.6, 'note': 'водонапорная башня на опорах, статичная'}
EXP['pump_house'] = list(PH)

FORK = [(992.0, 598.0, 0.0), (1007.5, 600.5, 1.57)]                           # вилочные погрузчики у склада + паллеты
for fx, fy, fa in FORK:
    rpoly(fx, fy, 2.4, 1.2, fa, (236, 140, 40), (100, 60, 20), 1)
    rpoly(*local(fx, fy, fa, 0.2, 0), 0.9, 0.9, fa, (60, 70, 80))
    for s in (-1, 1):
        line([local(fx, fy, fa, 1.2, s * 0.35), local(fx, fy, fa, 2.3, s * 0.35)], (60, 60, 60), 0.12)
for i in range(4):
    for j in range(2):
        if (i, j) != (3, 1):
            rect(1003.5 + i * 1.4, 604.0 + j * 1.4, 1004.7 + i * 1.4, 605.2 + j * 1.4, (184, 150, 104), (120, 90, 60))
for i in range(3):                                                             # биг-бэги (белые мешки)
    rect(1016.0 + i * 1.3, 598.5, 1017.1 + i * 1.3, 599.6, (244, 244, 238), (150, 150, 150))
EXP['machines'] = {'reach_stacker': list(RS), 'truck_with_40ft': list(TRUCK), 
                   'forklifts': [list(f[:2]) for f in FORK]}

# ---------------------------------------------------------------- 3. мелочи: катушки, трубы, бочки, бытовка, мачты света, лодка на кильблоках
for x, y in ((1022.0, 548.6), (1024.6, 548.4), (1023.3, 551.0)):              # кабельные катушки
    dot(x, y, 1.1, (176, 138, 90), (110, 84, 56), 2)
    dot(x, y, 0.35, (110, 84, 56))
for k in range(7):                                                             # пачка труб
    y = 547.3 + k * 0.45
    line([(1028.0, y), (1037.0, y)], (110, 116, 122), 0.36)
    dot(1037.0, y, 0.2, (70, 74, 78))
DRUMS = []
for k in range(14):                                                            # бочки у баков, пятна мазута
    x, y = 1014.0 + (k % 5) * 0.75 + rnd.uniform(-0.1, 0.1), 614.0 + (k // 5) * 0.75
    dot(x, y, 0.32, rnd.choice(((60, 90, 150), (150, 80, 50), (60, 60, 64))), (30, 30, 30))
    DRUMS.append([round(x, 1), round(y, 1)])
dot(1016.0, 611.3, 0.32, (150, 80, 50), (30, 30, 30))                          # опрокинутая
for k in range(6):
    x, y = rnd.uniform(1011, 1022), rnd.uniform(608, 618)
    dr.ellipse([P(x - 1.8, y + 1.0), P(x + 1.8, y - 1.0)], fill=(30, 30, 32, 70))
rect(951.5, 577.8, 957.5, 580.3, (236, 236, 228), (110, 110, 110), 1)          # бытовка
rect(952.0, 578.3, 957.0, 579.8, (226, 226, 218))
rect(958.3, 578.2, 959.5, 579.4, (60, 120, 200), (30, 60, 110), 1)             # синий туалет
MASTS = [(951.5, 547.0), (1012.0, 582.0), (1074.0, 582.5), (1004.0, 638.0)]
for x, y in MASTS:                                                             # мачты освещения
    dot(x, y, 0.5, (90, 90, 96))
    for a in range(4):
        t = math.pi / 4 + a * math.pi / 2
        dot(x + 0.9 * math.cos(t), y + 0.9 * math.sin(t), 0.3, (250, 226, 120), (90, 90, 96))
BOAT = (1066.5, 601.0)                                                         # старая лодка на кильблоках
for dx in (-3, 0, 3):
    rect(BOAT[0] + dx - 0.3, BOAT[1] - 1.6, BOAT[0] + dx + 0.3, BOAT[1] + 1.6, (120, 100, 80))
dr.polygon(PL([(BOAT[0] - 5, BOAT[1] - 1.5), (BOAT[0] + 3, BOAT[1] - 1.5), (BOAT[0] + 5.2, BOAT[1]), (BOAT[0] + 3, BOAT[1] + 1.5), (BOAT[0] - 5, BOAT[1] + 1.5)]),
           fill=(230, 230, 224), outline=(140, 70, 50))
dr.polygon(PL([(BOAT[0] - 4.4, BOAT[1] - 1.0), (BOAT[0] + 2.6, BOAT[1] - 1.0), (BOAT[0] + 4.3, BOAT[1]), (BOAT[0] + 2.6, BOAT[1] + 1.0), (BOAT[0] - 4.4, BOAT[1] + 1.0)]),
           fill=(150, 170, 180))
rect(BOAT[0] - 2.2, BOAT[1] - 0.8, BOAT[0] - 0.2, BOAT[1] + 0.8, (230, 230, 224), (120, 120, 120))
EXP['small'] = {'cable_reels': 3, 'pipe_stack': [1028, 547.3, 1037, 550.0], 'drums': DRUMS, 'site_cabin': [951.5, 577.8, 957.5, 580.3],
                'toilet': [958.3, 578.2], 'light_masts': MASTS, 'boat_on_blocks': list(BOAT)}
img.save(OWD)

# ---------------------------------------------------------------- 4. номера, заголовок
def label(t, x, y):
    cx, cy = P(x, y)
    dr.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=(255, 255, 255), outline=(40, 52, 70), width=2)
    dr.text((cx, cy), t, font=F, fill=(40, 52, 70), anchor='mm')


dot(947.6, 573.8, 2.65, (255, 255, 255))                                       # старый номер 08 с карты — под новый
for t, (x, y) in (('04', (968.0, 576.0)), ('03', (1004.5, 551.5)), ('07', (1022.0, 582.6)), ('06', (1056.0, 566.5)), ('09', (998.0, 605.5)),
                  ('10', (1026.0, 553.8)), ('11', (1018.0, 620.0)), ('12', (951.5, 551.0)), ('13', (955.0, 575.0)), ('14', (1066.5, 606.5)),
                  ('08', (947.6, 573.8))):
    label(t, x, y)
dr.rectangle([8, 8, W - 8, 74], fill=(255, 255, 255, 235), outline=(140, 160, 170))
dr.text((20, 14), 'ПОРТ (06) · план v03 — без крана и сыпучки, водонапорная башня', font=FT, fill=(40, 52, 70))
dr.text((20, 44), '04 контейнеры · 03 ричстакер · 06 водонапорная башня, насосная · 07 фура · 09 погрузчики, паллеты · 10 катушки, трубы · 11 бочки · 12 мачты света · 13 бытовка · 14 лодка',
        font=FS, fill=(90, 100, 106))
sx, sy = P(918, 532)
dr.rectangle([sx, sy, sx + 20 * K, sy + 5], fill=(40, 52, 70))
dr.text((sx + 20 * K + 8, sy + 2), '20 м', font=FS, fill=(40, 52, 70), anchor='lm')
img.save(OUT)
json.dump({'units': 'метры мира (x восток, y север), как WORLD_MAP', **EXP}, open(OJS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(OLG, 'w', encoding='utf-8-sig').write('''ПОРТ (06) — ЛЕГЕНДА v03 (TASK-000628–000629). Северная половина без изменений: 01 КПП, 02 склад, 05 два бака, 08 пост.
Козлового крана, экскаватора, сыпучки и самосвала нет.
04 — контейнеры, их стало меньше (~15): 2 небольших штабеля (40- и 20-футовые, 1–3 яруса, высоту видно по тени) с проходами
для техники + несколько вразнобой: открытый с ящиками у дверей, ржавый одиночка, один на фуре, один на ричстакере.
03 — ричстакер (контейнерный погрузчик) несёт 20-футовый. 07 — фура с 40-футовым, тягач к выезду на дорогу.
06 — водонапорная башня (бак на 4 опорах) и кирпичная насосная с трубой к башне — статичные постройки.
09 — 2 вилочных погрузчика у склада, паллеты, биг-бэги. 10 — кабельные катушки и пачка труб.
11 — бочки у баков (одна опрокинута) и пятна мазута; пятна масла по всей площадке. 12 — мачты освещения (4).
13 — бытовка и синий туалет у поста 08. 14 — старая лодка на кильблоках.
Между штабелями и вдоль дороги — проезды ≥ 8 м (бусик, фура). Координаты — Порт_v03.json.
''')
print('ok', len(CONT))
