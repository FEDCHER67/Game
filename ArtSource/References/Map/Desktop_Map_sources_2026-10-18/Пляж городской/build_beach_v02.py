"""Городской пляж (район 09) — план v02 по спеке docs/specs/BEACH_SPEC_2026-10-15_v01.md (TASK-000622).
Поверх общей карты v17, окно x 680…1090, y 0…240 м мира, 4 px/м. Берег поднят (пляж меньше, чуть выпуклый), раскладка как на
американском пляже: набережная у канала → служебный проезд и парковка → полоса дюн с проходами (душ, урна) → сухой песок
(волейбол, ряды зонтов) → открытый песок у воды → вышки спасателей, буйки зоны купания; пирс по центру; прокат сбоку от
зоны купания; 2 кафе у мостов; на западе у Тихой долины — брызги разлитого мазута (как с кисточки) и плёнка на воде.
Не перезаписывает. Запуск: python build_beach_v02.py -> Пляж_городской_v02.png (+ _world.png, .json, Легенда_v02.txt)
"""
import json
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
MAPPNG = r'C:\Users\chern_0eqkb03\Desktop\Map\Итоговая карта\VOLUNTEERS_MAP_FINAL_v17.png'
OUT, OWD, OJS, OLG = (os.path.join(HERE, n) for n in ('Пляж_городской_v02.png', 'Пляж_городской_v02_world.png',
                                                      'Пляж_городской_v02.json', 'Легенда_v02.txt'))
for p in (OUT, OWD, OJS, OLG):
    if os.path.exists(p):
        raise SystemExit(os.path.basename(p) + ' exists')

X0, X1, Y0, Y1, K = 680.0, 1090.0, 0.0, 240.0, 4.0
big = Image.open(MAPPNG).convert('RGB')
crop = big.crop((int(X0 * 5), int(4200 - Y1 * 5), int(X1 * 5), 4200))
img = crop.resize((int((X1 - X0) * K), int((Y1 - Y0) * K)), Image.LANCZOS)
W, H = img.size
rnd = random.Random(9)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 16)
FS = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 14)
FT = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 22)
SAND, WET, DUNE = (241, 227, 184), (226, 210, 166), (214, 222, 178)
ASPH, EDGE, PAVE = (95, 102, 108), (205, 205, 196), (232, 226, 210)
EXP = {}


def P(x, y):
    return ((x - X0) * K, (Y1 - y) * K)


def PL(pts):
    return [P(*p) for p in pts]


def colx(x):
    return int((x - X0) * K)


def rowy(y):
    return min(H - 1, max(0, int((Y1 - y) * K)))


# ---------------------------------------------------------------- 1. новый берег: выше, чуть выпуклый, плавно к старому по краям
px = img.load()


def old_coast(x):
    c = colx(x)
    for yy in range(H - 1, -1, -1):                                         # снизу вверх: первая не-вода
        r, g, b = px[c, yy]
        if b - r < 20:
            return Y1 - yy / K
    return 0.0


OC = {xx: old_coast(X0 + xx / K) for xx in range(0, W, 1)}


def new_coast(x):
    core = 100.0 - 7.0 * math.sin(math.pi * max(0.0, min(1.0, (x - 745) / 250.0)))   # чуть выпуклый к морю
    if x < 700:
        return OC[colx(x)]
    if x < 760:
        t = (x - 700) / 60.0
        t = t * t * (3 - 2 * t)
        return OC[colx(x)] * (1 - t) + core * t
    if x <= 995:
        return core
    if x < 1045:
        t = (x - 995) / 50.0
        t = t * t * (3 - 2 * t)
        return core * (1 - t) + OC[colx(x)] * t
    return OC[colx(x)]


ref = colx(722)                                                               # эталон градиента воды (у берега светлее)
ref_coast = OC[ref]
ref_col = [px[ref, yy] for yy in range(H)]
for xx in range(W):
    x = X0 + xx / K
    yc = new_coast(x)
    if yc <= OC[xx] + 0.01 and not (742 <= x <= 1000):
        continue
    for yy in range(rowy(yc), H):                                             # ниже нового берега — вода с градиентом
        d = (Y1 - yy / K)
        depth = yc - d
        src = rowy(ref_coast - depth)
        px[xx, yy] = ref_col[src] if 0 <= src < H else ref_col[H - 1]
dr = ImageDraw.Draw(img, 'RGBA')
# песок пляжа начисто (старые зонты, дорожки, домики, пирс) между дюнами Тихой долины и пальмами востока
core_poly = [(742, 203)] + [(x, new_coast(x) + 0.2) for x in range(742, 1001, 2)] + [(1000, 203)]
dr.polygon(PL(core_poly), fill=SAND)
for x in range(700, 1046):                                                    # мокрая полоса и пена вдоль нового берега
    yc = new_coast(x)
    dr.line([P(x, yc + 0.3), P(x, yc + 2.6)], fill=WET)
    dr.line([P(x, yc - 0.2), P(x, yc + 0.3)], fill=(250, 252, 250))
EXP['coast'] = [[x, round(new_coast(x), 1)] for x in range(700, 1046, 10)]


def rect(x0, y0, x1, y1, fill, out=None, w=1):
    dr.rectangle([P(min(x0, x1), max(y0, y1)), P(max(x0, x1), min(y0, y1))], fill=fill, outline=out, width=w)


def dot(x, y, r, fill, out=None):
    dr.ellipse([P(x - r, y + r), P(x + r, y - r)], fill=fill, outline=out)


def line(pts, col, wm):
    dr.line(PL(pts), fill=col, width=max(1, int(wm * K)), joint='curve')


def palm(x, y, s=1.0):
    for a in range(0, 360, 60):
        t = math.radians(a + 15)
        line([(x, y), (x + 2.4 * s * math.cos(t), y + 2.4 * s * math.sin(t))], (96, 150, 80), 0.55 * s)
    dot(x, y, 0.5 * s, (120, 96, 70))


# ---------------------------------------------------------------- 2. полоса дюн, служебный проезд, парковка, кафе
rect(742, 168, 1000, 180, DUNE)                                               # дюны с травой и пальмами
for k in range(70):
    x, y = rnd.uniform(744, 998), rnd.uniform(169, 179)
    dot(x, y, rnd.uniform(0.4, 0.9), (170, 190, 130))
ROAD_Y = 196.0
for c, w in ((EDGE, 8.4), (ASPH, 6.0)):
    line([(758, 209), (758, ROAD_Y), (1002, ROAD_Y), (1002, 209)], c, w)     # от мостов вниз и вдоль набережной
for x in range(770, 995, 8):
    line([(x, ROAD_Y), (x + 3.5, ROAD_Y)], (240, 240, 232), 0.18)
PARK = (838, 180.5, 922, 192.8)
rect(*PARK, (172, 174, 170), (130, 132, 130), 1)
for x in range(int(PARK[0]) + 3, int(PARK[2]), 3):
    line([(x, PARK[1] + 0.4), (x, PARK[3] - 0.4)], (240, 240, 232), 0.12)
CARC = ((220, 120, 120), (120, 180, 210), (250, 250, 248), (240, 210, 110), (60, 64, 70), (170, 220, 200))
taken = rnd.sample(range(27), 15)
for i in taken:
    x = PARK[0] + 1.6 + i * 3
    if x > PARK[2] - 2:
        continue
    rect(x - 0.9, PARK[1] + 1.2, x + 0.9, PARK[1] + 5.6, rnd.choice(CARC), (50, 50, 50), 1)
EXP['parking'] = {'rect': PARK, 'spaces': 27, 'access': 'служебный проезд от обоих мостов'}
CAFES = [((770, 181, 800, 193), (255, 214, 214)), ((960, 181, 990, 193), (196, 236, 230))]   # пастельный ар-деко
for (x0, y0, x1, y1), col in CAFES:
    rect(x0 + 0.6, y0 - 0.8, x1 + 0.6, y1 - 0.8, (60, 70, 60, 70))
    rect(x0, y0, x1, y1, col, (110, 110, 110), 2)
    rect(x0 + 2, y0 + 2, x1 - 2, y1 - 2, tuple(min(255, c + 12) for c in col), None)
    rect(x0 + 3, y0 + 8.5, x1 - 3, y0 + 10.5, (90, 200, 210), None)           # неоновая полоса ар-деко
    rect(x0 - 1, y0 - 7, x1 + 1, y0, (200, 168, 130), (150, 120, 90), 1)        # терраса к морю
    for k in range(6):
        cx = x0 + 2 + k * (x1 - x0 - 4) / 5
        dot(cx, y0 - 3.5, 0.9, (250, 250, 245), (150, 150, 150))
        dot(cx, y0 - 3.5, 1.6, (255, 255, 255, 80))
EXP['cafes'] = [list(c[0]) for c in CAFES]

# ---------------------------------------------------------------- 3. проходы на пляж через дюны: дощатые дорожки, души, урны
ACC = [782, 830, 880, 930, 975]
for x in ACC:
    rect(x - 1.6, 166, x + 1.6, 181, (206, 176, 136), (150, 120, 90), 1)
    for k in range(int(166), int(181), 1):
        line([(x - 1.4, k), (x + 1.4, k)], (170, 140, 104), 0.08)
    if x != 880:
        line([(x + 2.6, 164.5), (x + 2.6, 167.5)], (90, 120, 160), 0.35)        # душ
        dot(x + 2.6, 167.8, 0.5, (90, 160, 220))
    rect(x - 3.6, 165, x - 2.6, 166.2, (70, 110, 80), (40, 60, 46), 1)          # урна
EXP['beach_access'] = ACC
for x in range(748, 998, 9):                                                    # пальмы вдоль проезда (сторона пляжа)
    if all(abs(x - a) > 4 for a in ACC) and not (836 < x < 924):
        palm(x, 183)

# ---------------------------------------------------------------- 4. сухой песок: волейбол и ряды зонтов
VB = [(796, 150, 812, 158), (796, 138, 812, 146)]
for (x0, y0, x1, y1) in VB:
    rect(x0 - 3, y0 - 3, x1 + 3, y1 + 3, (236, 220, 176), None)
    rect(x0, y0, x1, y1, None, (245, 245, 240), 2)
    line([((x0 + x1) / 2, y0 - 1.2), ((x0 + x1) / 2, y1 + 1.2)], (60, 60, 60), 0.18)   # сетка
EXP['volleyball'] = VB
UCOL = ((247, 160, 150), (110, 200, 205), (250, 214, 110), (180, 170, 230))
UMB = []
for row, y in enumerate((156, 149, 142, 135)):
    for x0, x1 in ((842, 873), (887, 920), (938, 992)):
        x = x0 + (row % 2) * 2.5
        while x <= x1:
            UMB.append((x, y))
            x += 5.0
for i, (x, y) in enumerate(UMB):
    for dx in (-0.9, 0.9):
        rect(x + dx - 0.35, y - 3.2, x + dx + 0.35, y - 1.2, (252, 252, 248), (160, 160, 160), 1)   # 2 лежака
    dot(x, y, 1.15, UCOL[(i // 7) % len(UCOL)], (140, 120, 110))
EXP['umbrella_sets'] = len(UMB)
for k in range(28):                                                               # полотенца у воды — открытый песок
    x, y = rnd.uniform(800, 990), rnd.uniform(103, 128)
    if abs(x - 880) < 6:
        continue
    rect(x, y, x + 0.9, y + 1.9, rnd.choice(UCOL), None)

# ---------------------------------------------------------------- 5. вышки спасателей, буйки зоны купания, пирс, прокат
TOW = [(832, 112, (247, 170, 190)), (928, 112, (130, 210, 215))]
for x, y, col in TOW:
    rect(x - 2.2, y - 2.2, x + 2.2, y + 2.2, col, (90, 90, 90), 2)
    rect(x - 0.6, y + 2.2, x + 0.6, y + 5.5, (220, 220, 214), None)              # пандус к суше
    line([(x + 2.6, y + 0.5), (x + 2.6, y + 3.5)], (90, 90, 90), 0.15)
    rect(x + 2.6, y + 2.4, x + 4.0, y + 3.5, (230, 60, 50), None)                # флаг
EXP['lifeguard_towers'] = [[t[0], t[1]] for t in TOW]
buoy = [(806, new_coast(806) - 1)] + [(806, 80), (956, 80)] + [(956, new_coast(956) - 1)]
for (ax, ay), (bx, by) in zip(buoy[:-1], buoy[1:]):
    L = math.hypot(bx - ax, by - ay)
    for k in range(int(L // 4) + 1):
        dot(ax + (bx - ax) * k * 4 / max(L, 1), ay + (by - ay) * k * 4 / max(L, 1), 0.45, (250, 210, 40), (150, 110, 20))
EXP['swim_zone'] = buoy
PIER_X, PIER_END = 880.0, 36.0
rect(PIER_X - 3.5, PIER_END + 9, PIER_X + 3.5, 166, (196, 162, 120), (130, 100, 70), 2)
rect(PIER_X - 11, PIER_END, PIER_X + 11, PIER_END + 9, (196, 162, 120), (130, 100, 70), 2)
for y in range(int(PIER_END + 10), 166, 1):
    line([(PIER_X - 3.3, y), (PIER_X + 3.3, y)], (170, 136, 98), 0.07)
for y in range(int(PIER_END + 12), 160, 8):                                    # фонари и скамейки по пирсу
    dot(PIER_X - 3.0, y, 0.45, (250, 226, 120), (70, 70, 60))
    rect(PIER_X + 2.2, y + 2, PIER_X + 3.1, y + 4.2, (150, 112, 80), None)
rect(PIER_X - 9, PIER_END + 2, PIER_X - 4, PIER_END + 6.5, (247, 214, 200), (110, 110, 110), 1)   # ларёк
rect(PIER_X + 4, PIER_END + 2, PIER_X + 9, PIER_END + 6.5, (205, 232, 240), (110, 110, 110), 1)   # ларёк
for k in range(5):                                                              # рыбаки по краю площадки
    dot(PIER_X - 10 + k * 5, PIER_END + 0.5, 0.45, (60, 70, 90))
EXP['pier'] = {'x': PIER_X, 'from_y': 166, 'to_y': PIER_END, 'width_m': 7, 'head': [PIER_X - 11, PIER_END, PIER_X + 11, PIER_END + 9]}
RX0 = 966                                                                        # прокат: сбоку от зоны купания
rect(RX0, 104, RX0 + 5, 108, (250, 230, 160), (120, 110, 90), 1)
for k in range(6):
    rect(RX0 + 6.5 + k * 1.0, 104, RX0 + 7.2 + k * 1.0, 107.5, rnd.choice(UCOL), None)   # сапы на стойке
for k, (x, y) in enumerate(((964, 92), (970, 90), (976, 92))):
    dr.polygon(PL([(x - 1.4, y - 0.6), (x + 1.0, y - 0.6), (x + 1.8, y), (x + 1.0, y + 0.6), (x - 1.4, y + 0.6)]), fill=(240, 240, 245), outline=(60, 80, 120))
EXP['rental'] = {'hut': [RX0, 104, RX0 + 5, 108], 'jetskis': 3, 'sups': 6}

# ---------------------------------------------------------------- 6. мазут: брызги как с кисточки, у воды гуще, + плёнка на воде
OIL = (28, 26, 24)
cx_oil = 728.0
for k in range(520):
    x = rnd.gauss(cx_oil, 11)
    if not (700 < x < 765):
        continue
    yc = new_coast(x)
    up = abs(rnd.gauss(0, 6.5))                                                  # чем дальше от воды — тем реже
    y = yc + up
    r = max(0.12, rnd.gauss(0.35, 0.25)) * (1.6 if up < 2 else 1.0)
    if rnd.random() < 0.18:                                                      # вытянутая капля-брызг
        ang = rnd.uniform(0, math.pi)
        L = rnd.uniform(0.6, 1.8)
        line([(x, y), (x + L * math.cos(ang), y + L * math.sin(ang))], OIL, r * 1.2)
    dot(x, y, r, OIL)
for k in range(14):                                                              # несколько крупных клякс у самой кромки
    x = rnd.uniform(712, 748)
    dot(x, new_coast(x) + rnd.uniform(0.2, 1.8), rnd.uniform(0.9, 1.8), (22, 20, 18))
for k in range(9):                                                               # маслянистая плёнка на воде
    x, y = rnd.uniform(712, 752), new_coast(728) - rnd.uniform(3, 14)
    dr.ellipse([P(x - rnd.uniform(3, 7), y + rnd.uniform(1.5, 3)), P(x + rnd.uniform(3, 7), y - rnd.uniform(1.5, 3))],
               fill=(52, 48, 60, 70))
EXP['oil_spill'] = {'center_x': cx_oil, 'span_x': [705, 760], 'note': 'брызги мазута как с кисточки, гуще у воды; плёнка на воде'}

# ---------------------------------------------------------------- 7. фонари вдоль проезда, номера, заголовок
for x in range(764, 1000, 16):
    dot(x, ROAD_Y + 4.2, 0.5, (250, 226, 120), (70, 70, 60))
img.save(OWD)


def label(t, x, y):
    cx, cy = P(x, y)
    dr.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=(255, 255, 255), outline=(40, 52, 70), width=2)
    dr.text((cx, cy), t, font=F, fill=(40, 52, 70), anchor='mm')


for t, (x, y) in (('01', (880, 186.5)), ('02', (785, 196.5)), ('03', (975, 196.5)), ('04', (804, 162)), ('05', (832, 118.5)),
                  ('05', (928, 118.5)), ('06', (880, 30)), ('07', (968, 113)), ('08', (905, 160)), ('09', (728, 108)), ('10', (830, 172))):
    label(t, x, y)
dr.rectangle([8, 8, W - 8, 74], fill=(255, 255, 255, 235), outline=(140, 160, 170))
dr.text((20, 14), 'ГОРОДСКОЙ ПЛЯЖ (09) · план v02 — майамский курорт, меньше прежнего, берег выше · песок ~250×70 м', font=FT, fill=(40, 52, 70))
dr.text((20, 44), '01 парковка ~27 мест + служебный проезд от мостов · 02, 03 кафе ар-деко · 04 волейбол · 05 вышки · 06 пирс ~60 м в море · 07 прокат · 08 зонты · 09 мазут · 10 проходы (душ, урна)',
        font=FS, fill=(90, 100, 106))
sx, sy = P(690, 10)
dr.rectangle([sx, sy, sx + 50 * K, sy + 5], fill=(40, 52, 70))
dr.text((sx + 50 * K + 8, sy + 2), '50 м', font=FS, fill=(40, 52, 70), anchor='lm')
img.save(OUT)
json.dump({'units': 'метры мира (x восток, y север), как WORLD_MAP', **EXP}, open(OJS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(OLG, 'w', encoding='utf-8-sig').write('''ГОРОДСКОЙ ПЛЯЖ (09) — ЛЕГЕНДА v02 (спека docs/specs/BEACH_SPEC_2026-10-15_v01.md)
Раскладка от канала к морю: набережная → служебный проезд от обоих мостов и парковка вдоль набережной (01) → полоса дюн с проходами (10: дощатая
дорожка, душ, урна) → сухой песок: волейбол (04), ряды зонтов с 2 лежаками (08) → открытый песок у воды (полотенца) → кромка.
02, 03 — пастельные кафе ар-деко у мостов, терраса к морю. 05 — 2 вышки спасателей у воды, флаги; буйки ограничивают зону купания между ними.
06 — пирс по центру, ~60 м в море, фонари, скамейки, 2 ларька и рыбаки на площадке. 07 — прокат сапов и гидроциклов сбоку от зоны купания.
09 — мазут на западе у Тихой долины: брызги как с кисточки, у воды гуще, отдельные кляксы, плёнка на воде. Не весь пляж.
NPC просто гуляют и лежат, отдельных зон сбора нет. Координаты — Пляж_городской_v02.json.
''')
print('ok', OUT)
