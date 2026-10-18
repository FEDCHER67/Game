"""Городской пляж (район 09) — план v03 (TASK-000623, правки Вадима к v02): лежаки и зонты вразброс (концепция рядов читается,
но всё стоит «рандомненько»); волейбольные площадки рядом друг с другом вдоль берега; бусик может ехать по пляжу (въезд с проезда
по центру, коридор к воде, полоса вдоль кромки и задняя полоса у дюн); пирс начинается только у кромки воды и идёт в море — на нём
рыбаки. Вода перестроена сдвигом столбцов (без швов), берег выше; мазут — брызги как с кисточки. Спека BEACH_SPEC_2026-10-15_v01.md.
Не перезаписывает. Запуск: python build_beach_v03.py -> Пляж_городской_v03.png (+ _world.png, .json, Легенда_v03.txt)
"""
import json
import math
import os
import random
from collections import Counter

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
MAPPNG = r'C:\Users\chern_0eqkb03\Desktop\Map\Итоговая карта\VOLUNTEERS_MAP_FINAL_v17.png'
OUT, OWD, OJS, OLG = (os.path.join(HERE, n) for n in ('Пляж_городской_v03.png', 'Пляж_городской_v03_world.png',
                                                      'Пляж_городской_v03.json', 'Легенда_v03.txt'))
for p in (OUT, OWD, OJS, OLG):
    if os.path.exists(p):
        raise SystemExit(os.path.basename(p) + ' exists')

X0, X1, Y0, Y1, K = 680.0, 1090.0, 0.0, 240.0, 4.0
big = Image.open(MAPPNG).convert('RGB')
crop = big.crop((int(X0 * 5), int(4200 - Y1 * 5), int(X1 * 5), 4200))
img = crop.resize((int((X1 - X0) * K), int((Y1 - Y0) * K)), Image.LANCZOS)
orig = img.copy()
W, H = img.size
opx, px = orig.load(), img.load()
rnd = random.Random(23)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 16)
FS = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 14)
FT = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 22)
ASPH, EDGE = (95, 102, 108), (205, 205, 196)
EXP = {}


def P(x, y):
    return ((x - X0) * K, (Y1 - y) * K)


def PL(pts):
    return [P(*p) for p in pts]


def colx(x):
    return min(W - 1, max(0, int(round((x - X0) * K))))


def rowy(y):
    return min(H - 1, max(0, int(round((Y1 - y) * K))))


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def sstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- 1. берег выше и чуть выпуклый; вода — сдвиг столбцов (без швов)
for yy in range(rowy(47), rowy(21) + 1):                                     # старый островок у запада — убрать (копия ряда воды)
    c = opx[colx(716), yy]
    for xx in range(colx(721), colx(748) + 1):
        opx[xx, yy] = c


def scan_coast(xx):                                                           # сверху вниз от песка: первая вода (4 м подряд)
    run = 0
    for yy in range(rowy(150), H):
        r, g, b = opx[xx, yy]
        run = run + 1 if b - r >= 20 else 0
        if run >= int(4 * K):
            return Y1 - (yy - run + 1) / K
    return 0.0


OC0 = [scan_coast(xx) for xx in range(W)]
a_, b_ = colx(852), colx(888)                                                 # старый пирс — интерполяция берега
for xx in range(a_ + 1, b_):
    OC0[xx] = OC0[a_] + (OC0[b_] - OC0[a_]) * (xx - a_) / (b_ - a_)
OC = [sum(OC0[max(0, i - 8):i + 9]) / len(OC0[max(0, i - 8):i + 9]) for i in range(W)]


def new_coast(x):
    core = 100.0 - 7.0 * math.sin(math.pi * max(0.0, min(1.0, (x - 745) / 250.0)))
    oc = OC[colx(x)]
    if x < 700 or x > 1045:
        return oc
    if x < 760:
        t = sstep((x - 700) / 60.0)
        return oc * (1 - t) + core * t
    if x <= 995:
        return core
    t = sstep((x - 995) / 50.0)
    return core * (1 - t) + oc * t


Y_DEEP = 8.5                                                                  # горизонтальная граница глубины карты — не трогаем
XR = colx(800)
OCR = OC0[XR] - 0.3                                                           # сырой берег эталона (без светлого прибоя)


def prof(depth):                                                              # цвет воды эталонного столбца по глубине от берега
    return opx[XR, rowy(max(Y_DEEP + 0.3, OCR - depth))]


for xx in range(colx(700), colx(1045) + 1):
    x = X0 + xx / K
    yc = new_coast(x)
    d = max(0.0, yc - OC[xx])
    wc = sstep((x - 738) / 10.0) * sstep((1004 - x) / 10.0)                   # ядро — по эталону (там старый пирс и надпись)
    for yy in range(rowy(yc), rowy(Y_DEEP) + 1):
        y = Y1 - yy / K
        cs = opx[xx, rowy(max(Y_DEEP + 0.3, y - d))]
        if cs[2] - cs[0] < 20:                                               # светлый прибой/песок старого берега -> вода
            cs = prof(yc - y)
        px[xx, yy] = mix(cs, prof(yc - y), wc) if wc > 0 else cs
EXP['coast'] = [[x, round(new_coast(x), 1)] for x in range(700, 1046, 10)]

# песок ядра начисто (старые зонты, дорожки, домики), края растушёваны в исходный песок
cnt = Counter(opx[xx, yy] for xx in range(colx(760), colx(990), 3) for yy in range(rowy(160), rowy(100), 3))
SAND = cnt.most_common(1)[0][0]
SDELTA = (247 - SAND[0], 242 - SAND[1], 224 - SAND[2])                         # майамский белый песок
for yy in range(H):
    for xx in range(W):
        r, g, b = px[xx, yy]
        if r >= 226 and g >= 210 and b <= 226 and r - b >= 15 and g < r + 2:
            if min(abs(r - 241) + abs(g - 227) + abs(b - 184), abs(r - 244) + abs(g - 230) + abs(b - 187)) <= 14:
                px[xx, yy] = (247, 242, 224)                                 # чистый песок — ровно в белый
            else:
                px[xx, yy] = mix((r, g, b), (247, 242, 224), 0.75)           # тени, кромки, старые светлые полосы
SAND = (247, 242, 224)
WET = mix(SAND, (200, 186, 150), 0.45)
DUNE = mix(SAND, (176, 200, 140), 0.45)
for xx in range(colx(736), colx(1000) + 1):
    x = X0 + xx / K
    al = sstep((x - 740) / 6.0) * sstep((1000 - x) / 8.0)
    for yy in range(rowy(203), rowy(new_coast(x))):
        c = px[xx, yy]
        if x < 747 and c[1] <= c[0] + 3:                                     # запад: старые дорожки — в песок, трава долины остаётся
            px[xx, yy] = SAND
        else:
            px[xx, yy] = mix(c, SAND, al) if al < 1 else SAND
dr = ImageDraw.Draw(img, 'RGBA')
for x10 in range(7000, 10450):                                                # мокрая полоса и пена вдоль нового берега
    x = x10 / 10.0
    yc = new_coast(x)
    dr.line([P(x, yc + 0.3), P(x, yc + 2.4)], fill=WET)
    dr.line([P(x, yc - 0.2), P(x, yc + 0.3)], fill=(250, 252, 250))


def rect(x0, y0, x1, y1, fill, out=None, w=1):
    dr.rectangle([P(min(x0, x1), max(y0, y1)), P(max(x0, x1), min(y0, y1))], fill=fill, outline=out, width=w)


def dot(x, y, r, fill, out=None):
    dr.ellipse([P(x - r, y + r), P(x + r, y - r)], fill=fill, outline=out)


def line(pts, col, wm):
    dr.line(PL(pts), fill=col, width=max(1, int(round(wm * K))), joint='curve')


def rpoly(cx, cy, w, h, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    return [P(cx + dx * ca - dy * sa, cy + dx * sa + dy * ca) for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


def palm(x, y, s=1.0):
    for a in range(0, 360, 60):
        t = math.radians(a + 15 + rnd.uniform(-12, 12))
        line([(x, y), (x + 2.4 * s * math.cos(t), y + 2.4 * s * math.sin(t))], (96, 150, 80), 0.55 * s)
    dot(x, y, 0.5 * s, (120, 96, 70))


# ---------------------------------------------------------------- 2. проезд от мостов, 2 парковки, въезд на песок по центру, кафе
ROAD_Y = 196.0
for c, w in ((EDGE, 8.4), (ASPH, 6.0)):
    line([(758, 209), (758, ROAD_Y), (1002, ROAD_Y), (1002, 209)], c, w)
for x in range(770, 995, 8):
    if not 870 < x < 890:
        line([(x, ROAD_Y), (x + 3.5, ROAD_Y)], (240, 240, 232), 0.18)
rect(742, 168, 1000, 180, DUNE)                                               # дюны с травой
for k in range(90):
    x, y = rnd.uniform(744, 998), rnd.uniform(168.6, 179.4)
    dot(x, y, rnd.uniform(0.4, 0.9), (170, 190, 130))
RAMP = (873.0, 887.0)                                                         # въезд на песок: бусик, спасатели, пешеходы
rect(RAMP[0], 164, RAMP[1], 192, mix(SAND, (200, 180, 140), 0.35))
for k in range(5):                                                            # зебра через проезд к въезду
    rect(RAMP[0] + 1, 193.4 + k * 1.15, RAMP[1] - 1, 193.4 + k * 1.15 + 0.55, (240, 240, 232))
LOTS = [(829.0, 180.5, 872.0, 192.8), (888.0, 180.5, 931.0, 192.8)]
CARC = ((220, 120, 120), (120, 180, 210), (250, 250, 248), (240, 210, 110), (60, 64, 70), (170, 220, 200))
for lot in LOTS:
    rect(*lot, (172, 174, 170), (130, 132, 130), 1)
    n = int((lot[2] - lot[0]) // 3)
    for i in range(n + 1):
        x = lot[0] + 0.5 + i * 3
        line([(x, lot[1] + 0.4), (x, lot[1] + 6.2)], (240, 240, 232), 0.12)
    for i in rnd.sample(range(n), int(n * 0.7)):
        x = lot[0] + 2.0 + i * 3
        rect(x - 0.9, lot[1] + 1.0, x + 0.9, lot[1] + 5.5, rnd.choice(CARC), (50, 50, 50), 1)
EXP['parking'] = {'lots': LOTS, 'spaces': sum(int((l[2] - l[0]) // 3) for l in LOTS), 'access': 'служебный проезд от обоих мостов'}
EXP['sand_ramp'] = {'x': list(RAMP), 'y': [164, 192], 'note': 'въезд на песок по центру — бусик, спасатели, пешеходы'}
CAFES = [((768, 180.5, 796, 191), (255, 214, 214)), ((964, 180.5, 992, 191), (196, 236, 230))]   # пастельный ар-деко
for (x0, y0, x1, y1), col in CAFES:
    rect(x0 + 0.6, y0 - 0.8, x1 + 0.6, y1 - 0.8, (60, 70, 60, 70))
    rect(x0, y0, x1, y1, col, (110, 110, 110), 2)
    rect(x0 + 2, y0 + 2, x1 - 2, y1 - 2, tuple(min(255, c + 12) for c in col), None)
    rect(x0 + 3, y0 + 7.5, x1 - 3, y0 + 9.3, (90, 200, 210), None)
    rect(x0 - 1, y0 - 7, x1 + 1, y0, (200, 168, 130), (150, 120, 90), 1)       # терраса к морю
    for k in range(6):
        cx = x0 + 2 + k * (x1 - x0 - 4) / 5 + rnd.uniform(-0.6, 0.6)
        dot(cx, y0 - 3.5 + rnd.uniform(-1, 1), 0.9, (250, 250, 245), (150, 150, 150))
EXP['cafes'] = [list(c[0]) for c in CAFES]
ACC = [812.0, 948.0]                                                          # пешие проходы через дюны (плитка), душ и урна внизу
for x in ACC:
    rect(x - 1.5, 166, x + 1.5, 191.8, (226, 214, 190), (180, 166, 140), 1)
for x in ACC + [RAMP[0] - 2.2]:
    line([(x + 2.6, 164.5), (x + 2.6, 167.0)], (90, 120, 160), 0.35)           # душ
    dot(x + 2.6, 167.2, 0.5, (90, 160, 220))
    rect(x - 3.6, 165, x - 2.6, 166.2, (70, 110, 80), (40, 60, 46), 1)          # урна
EXP['beach_access'] = {'walkways': ACC, 'showers_bins': ACC + [RAMP[0] - 2.2]}
for x in range(747, 998, 9):                                                  # пальмы по дюнам
    if any(c[0][0] - 3 < x < c[0][2] + 3 for c in CAFES) or any(abs(x - a) < 5 for a in ACC) or RAMP[0] - 4 < x < RAMP[1] + 4:
        continue
    palm(x + rnd.uniform(-1.5, 1.5), 174 + rnd.uniform(-2, 2))

# ---------------------------------------------------------------- 3. что стоит у воды: вышки, прокат, буйки, пирс с берега
TOW = [(838.0, new_coast(838) + 21, (247, 170, 190), 0.10), (934.0, new_coast(934) + 21, (130, 210, 215), -0.08)]
RENT = (966.0, 975.0)                                                         # будка проката (x0, x1) у воды
VB = [(800.0, 147.0, 0.03), (823.0, 146.2, -0.05)]                            # 2 корта 16×8 м рядом вдоль берега
PIER_X, PIER_W, PIER_END = 880.0, 4.0, 44.0


def blocked(x, y, r=1.6):
    yc = new_coast(x)
    if y < yc + 17 or y > 154:                                               # полоса вдоль воды и задняя полоса у дюн — проезд
        return True
    if RAMP[0] - 1 - r < x < RAMP[1] + 1 + r:                                # коридор от въезда к пирсу
        return True
    if x < 768:                                                              # запад — мазут, не загорают
        return True
    if 786 - r < x < 837 + r and 138 - r < y < 156:                          # волейбол
        return True
    for tx, ty, _, _ in TOW:
        if math.hypot(x - tx, y - ty) < 6 + r:
            return True
    if RENT[0] - 6 < x < RENT[1] + 12 and y < yc + 19:
        return True
    return False


UCOL = ((247, 160, 150), (110, 200, 205), (250, 214, 110), (180, 170, 230), (246, 246, 240), (130, 190, 140))
LCOL = ((252, 252, 248), (252, 252, 248), (210, 232, 246), (246, 226, 200))
SETS = []
for x0z, x1z, near in ((770.0, 871.0, 871.0), (889.0, 1000.0, 889.0)):      # ряды есть, но всё стоит вразброс
    row = 0
    y = 0.0
    while True:
        yb = 115.0 + row * 6.2
        if yb > 152:
            break
        x = x0z + (row % 2) * 2.7 + rnd.uniform(0, 2)
        while x < x1z:
            dist = abs(x - near)
            keep = 0.88 - 0.55 * min(1.0, dist / 95.0)                       # гуще у центра, реже к краям
            gx, gy = x + rnd.uniform(-1.2, 1.2), yb + rnd.uniform(-1.2, 1.2) + (new_coast(x) - 96.0)
            if rnd.random() < keep and not blocked(gx, gy) and all(math.hypot(gx - sx, gy - sy) > 3.4 for sx, sy, *_ in SETS):
                SETS.append((gx, gy, rnd.gauss(0, 0.2), rnd.choices(('u2', 'u1', 'l2', 'u0', 'u3'), (50, 18, 12, 12, 8))[0]))
            x += rnd.uniform(4.4, 6.4)
        row += 1
for k in range(60):                                                           # одиночки сзади и у краёв
    gx, gy = rnd.uniform(770, 998), rnd.uniform(118, 153)
    if not blocked(gx, gy) and all(math.hypot(gx - sx, gy - sy) > 4.5 for sx, sy, *_ in SETS) and len(SETS) < 400 and rnd.random() < 0.35:
        SETS.append((gx, gy, rnd.gauss(0, 0.45), rnd.choice(('u1', 'l2', 'u0'))))
for gx, gy, ang, kind in SETS:
    nl = {'u2': 2, 'u1': 1, 'l2': 2, 'u0': 0, 'u3': 3}[kind]
    lc = rnd.choice(LCOL)
    for j in range(nl):
        off = (j - (nl - 1) / 2) * 1.0
        aj = ang + rnd.gauss(0, 0.12)
        cx, cy = gx + off * math.cos(ang), gy - 0.7 + off * math.sin(ang)
        dr.polygon(rpoly(cx, cy, 0.7, 2.0, aj), fill=lc, outline=(150, 150, 150))
    if kind == 'u0':                                                          # полотенце вместо лежака
        dr.polygon(rpoly(gx + 0.6, gy - 0.9, 0.9, 1.9, ang + rnd.gauss(0, 0.3)), fill=rnd.choice(UCOL))
    if kind != 'l2':
        ux, uy = gx + rnd.uniform(-0.5, 0.5), gy + 0.4 + rnd.uniform(-0.3, 0.4)
        uc = rnd.choice(UCOL)
        dot(ux, uy, 1.25, uc, (140, 120, 110))
        dot(ux, uy, 0.55, mix(uc, (255, 255, 255), 0.45))
EXP['umbrella_sets'] = {'count': len(SETS), 'kinds': dict(Counter(s[3] for s in SETS)),
                        'note': 'вразброс: ряды угадываются, у центра гуще; зонт+2 лежака, зонт+1, 2 лежака, зонт+полотенце, зонт+3'}
for k in range(40):                                                           # полотенца у воды (бусик по ним проедет)
    x = rnd.uniform(772, 998)
    if RAMP[0] - 2 < x < RAMP[1] + 2:
        continue
    y = new_coast(x) + rnd.uniform(2.5, 8)
    dr.polygon(rpoly(x, y, 0.9, 1.9, rnd.gauss(0, 0.5)), fill=rnd.choice(UCOL))

for cx, cy, ang in VB:                                                        # волейбол: 2 корта рядом, сетка поперёк берега
    dr.polygon(rpoly(cx, cy, 22, 14, ang), fill=mix(SAND, (226, 212, 176), 0.35))      # разрыхлённый песок
    dr.polygon(rpoly(cx, cy, 16, 8, ang), outline=(60, 120, 200), width=2)                  # синие ленты разметки
    line([(cx - 4.6 * math.sin(ang), cy + 4.6 * math.cos(ang)), (cx + 4.6 * math.sin(ang), cy - 4.6 * math.cos(ang))], (60, 60, 60), 0.2)
EXP['volleyball'] = [{'center': [c[0], c[1]], 'size': [16, 8], 'angle_rad': c[2]} for c in VB]

for x, y, col, ang in TOW:                                                    # вышки на сваях, пандус к суше
    dr.polygon(rpoly(x, y + 4.0, 1.2, 4.0, ang), fill=(220, 220, 214), outline=(150, 150, 150))
    dr.polygon(rpoly(x, y, 4.4, 4.4, ang), fill=col, outline=(90, 90, 90))
    line([(x + 2.7, y + 0.6), (x + 2.7, y + 3.6)], (90, 90, 90), 0.15)
    rect(x + 2.7, y + 2.5, x + 4.1, y + 3.6, (230, 60, 50), None)
EXP['lifeguard_towers'] = [[t[0], t[1]] for t in TOW]
buoy = [(806, new_coast(806) - 1), (806, 74), (956, 74), (956, new_coast(956) - 1)]
for (ax, ay), (bx, by) in zip(buoy[:-1], buoy[1:]):
    L = math.hypot(bx - ax, by - ay)
    for k in range(int(L // 4) + 1):
        dot(ax + (bx - ax) * k * 4 / L, ay + (by - ay) * k * 4 / L, 0.45, (250, 210, 40), (150, 110, 20))
EXP['swim_zone'] = buoy
yc_r = new_coast(RENT[0])
rect(RENT[0], yc_r + 3, RENT[0] + 5, yc_r + 7, (250, 230, 160), (120, 110, 90), 1)
for k in range(6):
    rect(RENT[0] + 6.4 + k, yc_r + 3, RENT[0] + 7.1 + k, yc_r + 6.6, rnd.choice(UCOL), None)
for x, y in ((964, 89), (970.5, 86.5), (977, 89.5)):
    dr.polygon(PL([(x - 1.4, y - 0.6), (x + 1.0, y - 0.6), (x + 1.8, y), (x + 1.0, y + 0.6), (x - 1.4, y + 0.6)]), fill=(240, 240, 245), outline=(60, 80, 120))
EXP['rental'] = {'hut': [RENT[0], round(yc_r + 3, 1), RENT[0] + 5, round(yc_r + 7, 1)], 'jetskis': 3, 'sups': 6}

PIER_ROOT = new_coast(PIER_X) + 1.5                                           # пирс — только от кромки воды в море
WOOD, WOOD_D = (196, 162, 120), (130, 100, 70)
rect(PIER_X - PIER_W / 2, PIER_END, PIER_X + PIER_W / 2, PIER_ROOT, WOOD, WOOD_D, 2)
rect(PIER_X - 9, PIER_END - 8, PIER_X + 9, PIER_END, WOOD, WOOD_D, 2)          # площадка на конце
for y in range(int(PIER_END) + 1, int(PIER_ROOT)):
    line([(PIER_X - PIER_W / 2 + 0.2, y), (PIER_X + PIER_W / 2 - 0.2, y)], (172, 138, 100), 0.07)
for y in range(int(PIER_END) + 5, int(PIER_ROOT) - 3, 12):
    dot(PIER_X - PIER_W / 2 + 0.3, y, 0.4, (250, 226, 120), (70, 70, 60))       # фонари
FISH = []
for k in range(9):                                                            # рыбаки по краям пирса и на площадке
    y = rnd.uniform(PIER_END + 3, PIER_ROOT - 8)
    s = rnd.choice((-1, 1))
    FISH.append((PIER_X + s * (PIER_W / 2 - 0.5), y, s))
for k in range(6):
    FISH.append((PIER_X - 8 + k * 3.2 + rnd.uniform(-0.6, 0.6), PIER_END - 7.4, 0))
for x, y, s in FISH:
    dot(x, y, 0.45, (60, 70, 90))
    if s:
        line([(x, y), (x + s * 3.2, y + rnd.uniform(-1.2, 1.2))], (90, 90, 90), 0.08)  # удочка
    else:
        line([(x, y), (x + rnd.uniform(-1, 1), y - 3.2)], (90, 90, 90), 0.08)
    rect(x - 0.35, y + (0.6 if s == 0 else 0), x + 0.35, y + (1.2 if s == 0 else 0.6), (90, 140, 200))   # ведро
EXP['pier'] = {'x': PIER_X, 'from_y': round(PIER_ROOT, 1), 'to_y': PIER_END - 8, 'width_m': PIER_W, 'fishermen': len(FISH),
               'note': 'начинается у кромки воды, без настила через пляж; рыбаки'}

# ---------------------------------------------------------------- 4. мазут: брызги как с кисточки (капли и веер мелких), плёнка на воде
OIL = (26, 24, 22)
OIL_PTS = []
for k in range(24):
    fx = rnd.uniform(706, 765)
    fy = new_coast(fx) + 0.8 + abs(rnd.gauss(0, 6.5))
    ang, R = rnd.uniform(0, 2 * math.pi), rnd.uniform(0.35, 0.8)
    dot(fx, fy, R, OIL)
    OIL_PTS.append((round(fx, 1), round(fy, 1)))
    if rnd.random() < 0.5:
        line([(fx, fy), (fx + 1.6 * R * math.cos(ang + math.pi), fy + 1.6 * R * math.sin(ang + math.pi))], OIL, R * 1.1)
    for j in range(rnd.randint(4, 11)):                                       # веер брызг от капли
        dd, a = rnd.uniform(R + 0.4, 4.0), ang + rnd.gauss(0, 0.4)
        x, y = fx + dd * math.cos(a), fy + dd * math.sin(a)
        if y > new_coast(x) + 0.3:
            dot(x, y, max(0.15, R * rnd.uniform(0.15, 0.5)), OIL)
for k in range(170):                                                          # мелкие одиночные капли
    x = rnd.uniform(704, 768)
    y = new_coast(x) + 0.3 + abs(rnd.gauss(0, 8))
    dot(x, y, rnd.uniform(0.15, 0.35), OIL)
for k in range(7):
    x = rnd.uniform(712, 756)
    y = new_coast(x) - rnd.uniform(3, 13)
    dr.ellipse([P(x - rnd.uniform(3, 6), y + rnd.uniform(1.2, 2.5)), P(x + rnd.uniform(3, 6), y - rnd.uniform(1.2, 2.5))], fill=(56, 52, 66, 55))
EXP['oil_spill'] = {'span_x': [704, 768], 'drops_main': OIL_PTS, 'note': 'брызги как с кисточки: капли с веером мелких, у воды гуще, плёнка на воде'}

for x in range(764, 1000, 16):                                                # фонари вдоль проезда
    dot(x, ROAD_Y + 4.2, 0.5, (250, 226, 120), (70, 70, 60))
img.save(OWD)

# ---------------------------------------------------------------- 5. только на плане: где проезжает бусик, номера, заголовок
VAN = [[(880, 190), (880, new_coast(880) + 12)], [(x, round(new_coast(x) + 12, 1)) for x in range(772, 1000, 6)], [(770, 158.5), (998, 158.5)]]
for route in VAN:
    for (ax, ay), (bx, by) in zip(route[:-1], route[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) // 3))
        for k in range(n):
            t0, t1 = k / n, (k + 0.55) / n
            line([(ax + (bx - ax) * t0, ay + (by - ay) * t0), (ax + (bx - ax) * t1, ay + (by - ay) * t1)], (210, 120, 60, 170), 0.5)
EXP['van_routes'] = [[list(p) for p in r] for r in VAN]


def label(t, x, y):
    cx, cy = P(x, y)
    dr.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=(255, 255, 255), outline=(40, 52, 70), width=2)
    dr.text((cx, cy), t, font=F, fill=(40, 52, 70), anchor='mm')


for t, (x, y) in (('01', (850, 186.6)), ('01', (909, 186.6)), ('02', (782, 186)), ('03', (978, 186)), ('04', (811.5, 159)),
                  ('05', (838, TOW[0][1] + 7.5)), ('05', (934, TOW[1][1] + 7.5)), ('06', (880, 28)), ('07', (968.5, yc_r - 4)), ('08', (905, 140)),
                  ('09', (730, new_coast(730) + 26)), ('10', (812, 172)), ('10', (948, 172)), ('11', (880, 172))):
    label(t, x, y)
dr.rectangle([8, 8, W - 8, 74], fill=(255, 255, 255, 235), outline=(140, 160, 170))
dr.text((20, 14), 'ГОРОДСКОЙ ПЛЯЖ (09) · план v03 — белый песок, лежаки вразброс, бусик ездит по пляжу, пирс от кромки воды', font=FT, fill=(40, 52, 70))
dr.text((20, 44), '01 парковки (%d мест) · 02, 03 кафе · 04 волейбол · 05 вышки · 06 пирс, рыбаки · 07 прокат · 08 зонты и лежаки · 09 мазут · 10 проходы · 11 въезд на песок · оранжевый пунктир — проезд бусика'
        % EXP['parking']['spaces'], font=FS, fill=(90, 100, 106))
sx, sy = P(690, 10)
dr.rectangle([sx, sy, sx + 50 * K, sy + 5], fill=(40, 52, 70))
dr.text((sx + 50 * K + 8, sy + 2), '50 м', font=FS, fill=(40, 52, 70), anchor='lm')
img.save(OUT)
json.dump({'units': 'метры мира (x восток, y север), как WORLD_MAP', **EXP}, open(OJS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(OLG, 'w', encoding='utf-8-sig').write('''ГОРОДСКОЙ ПЛЯЖ (09) — ЛЕГЕНДА v03 (спека docs/specs/BEACH_SPEC_2026-10-15_v01.md, правки TASK-000623)
От канала к морю: набережная → служебный проезд от обоих мостов, 2 парковки вдоль набережной (01) → по центру между ними въезд на песок
(11: бусик, спасатели, пешеходы; зебра через проезд) → полоса дюн с пальмами и 2 пешими проходами (10; душ и урна внизу) → песок.
08 — зонты и лежаки ВРАЗБРОС: ряды угадываются, но каждый набор сдвинут и повёрнут; у центра гуще, к краям реже; наборы разные
(зонт+2 лежака, зонт+1, 2 лежака без зонта, зонт+полотенце, зонт+3). У воды — полотенца.
Бусик ездит по пляжу (оранжевый пунктир только на плане): от въезда по центру к воде, вдоль кромки воды и сзади вдоль дюн —
на этих полосах ничего не ставить.
04 — 2 волейбольных корта рядом вдоль берега, у кафе 02. 05 — 2 вышки спасателей. Буйки — зона купания между вышками.
06 — пирс начинается у кромки воды (настила через пляж нет), ~50 м в море + площадка; на нём рыбаки с удочками и вёдрами, фонари.
07 — прокат сапов и гидроциклов у воды восточнее зоны купания. 02, 03 — пастельные кафе ар-деко у мостов, террасы к морю.
09 — мазут на западе у Тихой долины: брызги как с кисточки (капли с веером мелких брызг), у воды гуще, плёнка на воде. Загорающих там нет.
NPC просто гуляют и лежат, зон сбора нет. Координаты — Пляж_городской_v03.json.
''')
print('ok', len(SETS), EXP['parking']['spaces'], round(PIER_ROOT, 1), SAND)
