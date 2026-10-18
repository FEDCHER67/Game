"""Элитный холм (район 07) — план v01 по спеке docs/specs/ELITE_SPEC_2026-10-15_v01.md (TASK-000616).
Рисуется поверх общей карты v16 (вокруг видно мыс, берег, дорогу из Даунтауна), 6 px/м, координаты — метры мира
(x на восток, y на север). Старый район (огромный овал, виллы, площадь, причалы) закрашен.
Территория ~145×120 м, 4 виллы знаменитостей по углам, кольцевая дорога, КПП со шлагбаумом, в центре — здание ФБР,
на восточном краю — смотровая, лестница к частному пляжу с запертой калиткой, 3 разных угловатых причала с яхтами.
Не перезаписывает. Запуск: python build_elite_v01.py -> Элитный_холм_v01.png, Элитный_холм_v01.json, Легенда_v01.txt
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
MAPPNG = r'C:\Users\chern_0eqkb03\Desktop\Map\Итоговая карта\VOLUNTEERS_MAP_FINAL_v16.png'
OUT, OJS, OLG = (os.path.join(HERE, n) for n in ('Элитный_холм_v01.png', 'Элитный_холм_v01.json', 'Легенда_v01.txt'))
for p in (OUT, OJS, OLG):
    if os.path.exists(p):
        raise SystemExit(os.path.basename(p) + ' exists')

X0, X1, Y0, Y1, K = 1120.0, 1420.0, 200.0, 450.0, 6.0      # окно в метрах мира, px на метр
big = Image.open(MAPPNG).convert('RGB')
crop = big.crop((int(X0 * 5), int(4200 - Y1 * 5), int(X1 * 5), int(4200 - Y0 * 5)))
img = crop.resize((int((X1 - X0) * K), int((Y1 - Y0) * K)), Image.LANCZOS)
dr = ImageDraw.Draw(img, 'RGBA')
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 18)
FS = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 15)
FT = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 24)


def P(x, y):
    return ((x - X0) * K, (Y1 - y) * K)


def PL(pts):
    return [P(*p) for p in pts]


def rect(x0, y0, x1, y1, fill, out=None, w=2):
    a, b = P(min(x0, x1), max(y0, y1)), P(max(x0, x1), min(y0, y1))
    dr.rectangle([a, b], fill=fill, outline=out, width=w)


def rot(pts, cx, cy, deg):
    a = math.radians(deg)
    return [(cx + (x - cx) * math.cos(a) - (y - cy) * math.sin(a), cy + (x - cx) * math.sin(a) + (y - cy) * math.cos(a)) for x, y in pts]


HILL, SEA, SAND = (226, 235, 210), (182, 219, 231), (241, 227, 184)
ASPH, EDGE = (95, 102, 108), (211, 210, 195)
EXP = {}

# ---------------------------------------------------------------- 0. убрать старый район
dr.ellipse([P(1248 - 93, 335 + 73), P(1248 + 93, 335 - 73)], fill=HILL)
rect(1324, 303, 1344, 332, HILL, None)                                       # старая лестница
px = img.load()
for (y0, y1) in ((321, 345), (297, 320), (272, 296)):                       # старые причалы — под воду: по столбцам из ряда выше
    for xx in range(int(P(1349, 0)[0]), int(P(1397, 0)[0])):
        c = px[xx, int(P(0, y1 + 1.5)[1])]
        for yy in range(int(P(0, y1)[1]), int(P(0, y0)[1]) + 1):
            px[xx, yy] = c
dr = ImageDraw.Draw(img, 'RGBA')
dr.polygon(PL([(1333, 347), (1346, 348), (1355, 341), (1359, 326), (1360, 304), (1358, 284), (1352, 271), (1341, 265), (1333, 265)]),
           fill=SAND)                                                         # частный пляж вдоль берега, ровно
dr = ImageDraw.Draw(img, 'RGBA')

# ---------------------------------------------------------------- 1. территория, забор, КПП
FENCE = [(1185, 300), (1199, 283), (1238, 275), (1300, 278), (1324, 292), (1331, 330), (1325, 371), (1301, 392),
         (1240, 395), (1200, 388), (1186, 370), (1185, 357)]                  # разрыв 345…357 — въезд через КПП
dr.polygon(PL(FENCE + [(1185, 345)]), fill=(222, 233, 206))
dr.line(PL(FENCE[-1:] + FENCE[:-1] + [(1185, 300)]), fill=None)
dr.line(PL([(1185, 345)] + FENCE + [(1185, 357)][:0]), fill=(70, 88, 62), width=5)
for t in range(0, len(FENCE) - 1):                                           # колючка — штрихи вдоль забора
    (ax, ay), (bx, by) = FENCE[t], FENCE[t + 1]
    L = math.hypot(bx - ax, by - ay)
    for k in range(int(L // 3)):
        x, y = ax + (bx - ax) * k * 3 / L, ay + (by - ay) * k * 3 / L
        dr.line([P(x - 0.6, y - 0.6), P(x + 0.6, y + 0.6)], fill=(70, 88, 62), width=2)
EXP['fence'] = FENCE
# въездная дорога от дороги из Даунтауна + КПП
for c, w in ((EDGE, 10.5), (ASPH, 7.5)):
    dr.line(PL([(1150, 349), (1185, 349), (1222, 347)]), fill=c, width=int(w * K), joint='curve')
rect(1186, 354, 1192, 360, (176, 196, 210), (60, 70, 80))                   # будка КПП
dr.line(PL([(1189, 353.5), (1189, 344.5)]), fill=(210, 60, 50), width=4)    # шлагбаум
EXP['kpp'] = {'booth': [1186, 354, 1192, 360], 'barrier_x': 1189}

# ---------------------------------------------------------------- 2. кольцо и ФБР в центре
RC, RX, RY = (1258, 341), 35, 24
ring = [(RC[0] + RX * math.cos(t * math.pi / 36), RC[1] + RY * math.sin(t * math.pi / 36)) for t in range(73)]
for c, w in ((EDGE, 10), (ASPH, 7)):
    dr.line(PL(ring), fill=c, width=int(w * K), joint='curve')
EXP['ring'] = {'center': RC, 'rx': RX, 'ry': RY, 'width_m': 7}
dr.ellipse([P(RC[0] - RX + 5, RC[1] + RY - 5), P(RC[0] + RX - 5, RC[1] - RY + 5)], fill=(205, 222, 186))
FBR = (1243, 334, 1273, 350)
rect(*FBR, (72, 84, 98), (40, 48, 58), 3)
rect(1246, 337, 1270, 347, (88, 102, 118), None)
rect(1268, 350, 1271, 356, (60, 64, 70), None)                              # вход, ступени
dr.line(PL([(1250, 351), (1250, 357)]), fill=(60, 60, 60), width=3)        # флагшток
dr.rectangle([P(1250, 357), P(1254, 355)], fill=(40, 70, 140))
rect(1276, 330, 1284, 337, (150, 152, 156), (70, 70, 74))                  # пара чёрных джипов охраны
EXP['fbr'] = {'rect': FBR, 'note': 'главный пост охраны, ФБР; 2 джипа у входа'}

# ---------------------------------------------------------------- 3. 4 виллы по углам (несимметрично по склону)
VILLAS = [
    dict(id='01', plot=[(1192, 360), (1236, 366), (1232, 392), (1200, 388), (1190, 374)], c=(1213, 377), ang=-6,
         body=[(-12, -6), (6, -6), (6, -1), (12, -1), (12, 7), (-12, 7)], pool=(-10, -12, 2, -9), link=(1232, 362)),
    dict(id='02', plot=[(1282, 363), (1322, 358), (1324, 376), (1300, 391), (1280, 389)], c=(1302, 376), ang=10,
         body=[(-11, -7), (11, -7), (11, 5), (2, 5), (2, 8), (-11, 8)], pool=(-9, -13, 5, -10), link=(1286, 362)),
    dict(id='03', plot=[(1281, 286), (1322, 294), (1327, 324), (1296, 322), (1284, 316)], c=(1304, 306), ang=14,
         body=[(-12, -6), (12, -6), (12, 6), (-2, 6), (-2, 9), (-12, 9)], pool=(-10, -11, 4, -8), link=(1286, 322)),
    dict(id='04', plot=[(1192, 300), (1204, 286), (1236, 282), (1238, 318), (1194, 322)], c=(1215, 302), ang=-12,
         body=[(-13, -5), (13, -5), (13, 4), (4, 4), (4, 9), (-13, 9)], pool=(-11, -11, 3, -8), link=(1232, 320)),
]
for v in VILLAS:
    dr.polygon(PL(v['plot']), fill=(206, 226, 184), outline=(150, 176, 130))
    cx, cy = v['c']
    body = rot([(cx + x, cy + y) for x, y in v['body']], cx, cy, v['ang'])
    for k, (dx, dy) in enumerate(((1.2, -1.6),)):                         # тень
        dr.polygon(PL([(x + dx, y + dy) for x, y in body]), fill=(60, 70, 60, 70))
    dr.polygon(PL(body), fill=(242, 240, 232), outline=(80, 88, 96))
    upper = rot([(cx + x * 0.55, cy + y * 0.55 + 1) for x, y in v['body']], cx, cy, v['ang'])   # второй объём — терраса/пергола
    dr.polygon(PL(upper), fill=(226, 222, 210), outline=(120, 120, 120))
    x0, y0, x1, y1 = v['pool']
    pool = rot([(cx + x0, cy + y0), (cx + x1, cy + y0), (cx + x1, cy + y1), (cx + x0, cy + y1)], cx, cy, v['ang'])
    dr.polygon(PL(pool), fill=(120, 196, 228), outline=(70, 130, 170))
    # подъезд к кольцу
    near = min(ring, key=lambda p: math.hypot(p[0] - v['link'][0], p[1] - v['link'][1]))
    for c, w in ((EDGE, 6.5), (ASPH, 4.5)):
        dr.line(PL([near, v['link'], (cx, cy)]), fill=c, width=int(w * K), joint='curve')
    dr.polygon(PL(body), fill=(242, 240, 232), outline=(80, 88, 96))
    dr.polygon(PL(upper), fill=(226, 222, 210), outline=(120, 120, 120))
    for t in range(6):                                                    # пальмы и живая изгородь по участку
        a = t / 6
        (ax, ay), (bx, by) = v['plot'][t % len(v['plot'])], v['plot'][(t + 1) % len(v['plot'])]
        x, y = ax + (bx - ax) * 0.5, ay + (by - ay) * 0.5
        dr.ellipse([P(x - 1.6, y + 1.6), P(x + 1.6, y - 1.6)], fill=(110, 160, 90), outline=(70, 110, 60))
    EXP.setdefault('villas', []).append({'id': v['id'], 'plot': v['plot'], 'body': [[round(a, 1), round(b, 1)] for a, b in body],
                                         'pool': [[round(a, 1), round(b, 1)] for a, b in pool], 'note': 'вилла знаменитости-стримера'})

# ---------------------------------------------------------------- 4. восточный край: смотровая, лестница с калиткой, причалы
dr.pieslice([P(1318, 352), P(1336, 334)], 270, 90, fill=(232, 222, 200), outline=(150, 130, 100), width=2)   # смотровая
EXP['lookout'] = [1327, 343, 'открыто: оставлять ли']
stairs = [(1331, 326), (1336, 323), (1333, 318), (1340, 315), (1346, 313)]
dr.line(PL(stairs), fill=(150, 140, 125), width=int(2.6 * K), joint='curve')
for (x, y) in stairs[1:]:
    dr.line(PL([(x - 1, y + 0.6), (x + 1, y - 0.6)]), fill=(110, 100, 90), width=2)
dr.line(PL([(1344, 318), (1347, 309)]), fill=(70, 88, 62), width=5)       # калитка внизу — на замке
dr.ellipse([P(1345.2, 314.2), P(1346.8, 312.6)], fill=(200, 160, 40))
EXP['stairs'] = {'path': stairs, 'gate': [1345.5, 313.5], 'note': 'калитка внизу на замке; с пляжа не забежать'}
WOOD, WOOD_D = (176, 142, 102), (120, 92, 62)
PIERS = [
    dict(n='P1', poly=[(1358, 334), (1382, 334), (1382, 344), (1386, 344), (1386, 330), (1358, 330)]),          # Г-причал
    dict(n='P2', poly=[(1358, 304), (1388, 304), (1388, 296), (1393, 296), (1393, 318), (1388, 318), (1388, 309), (1358, 309)]),  # Т-причал
    dict(n='P3', poly=[(1357, 286), (1370, 283), (1381, 275), (1389, 275), (1389, 266), (1379, 266), (1379, 271), (1369, 279), (1357, 282)]),  # ломаный + плавучая площадка
]
for p in PIERS:
    dr.polygon(PL([(x + 0.8, y - 0.8) for x, y in p['poly']]), fill=(60, 80, 90, 60))
    dr.polygon(PL(p['poly']), fill=WOOD, outline=WOOD_D)
    xs = [q[0] for q in p['poly']]
    for x in range(int(min(xs)) + 2, int(max(xs)), 3):                       # доски
        ys = [q[1] for q in p['poly']]
    EXP.setdefault('piers', []).append({'id': p['n'], 'poly': p['poly']})


def yacht(x, y, L, W, ang, col=(250, 250, 248)):
    hull = [(x - L / 2, y - W / 2), (x + L / 2 - W, y - W / 2), (x + L / 2, y), (x + L / 2 - W, y + W / 2), (x - L / 2, y + W / 2)]
    hull = rot(hull, x, y, ang)
    dr.polygon(PL(hull), fill=col, outline=(90, 100, 110))
    cab = rot([(x - L * 0.25, y - W * 0.28), (x + L * 0.15, y - W * 0.28), (x + L * 0.15, y + W * 0.28), (x - L * 0.25, y + W * 0.28)], x, y, ang)
    dr.polygon(PL(cab), fill=(200, 212, 222), outline=(110, 120, 130))
    EXP.setdefault('yachts', []).append({'pos': [x, y], 'length_m': L, 'width_m': W, 'angle': ang})


yacht(1372, 326, 22, 6, 0)               # большая у Г-причала
yacht(1398, 312, 15, 5, 90)              # у Т-головы
yacht(1398, 300, 12, 4, 90, (235, 240, 246))
yacht(1374, 313.5, 10, 3.6, 0, (238, 236, 228))
yacht(1395, 270, 8, 3, 20, (250, 250, 248))      # катер у плавучей площадки

# ---------------------------------------------------------------- 5. фонари вдоль кольца и у въезда
for t in range(0, 72, 9):
    x, y = RC[0] + (RX + 6) * math.cos(t * math.pi / 36), RC[1] + (RY + 6) * math.sin(t * math.pi / 36)
    dr.ellipse([P(x - 0.9, y + 0.9), P(x + 0.9, y - 0.9)], fill=(250, 226, 120), outline=(70, 70, 60))
for x, y in ((1182, 361), (1196, 342)):
    dr.ellipse([P(x - 0.9, y + 0.9), P(x + 0.9, y - 0.9)], fill=(250, 226, 120), outline=(70, 70, 60))


# ---------------------------------------------------------------- 6. номера, заголовок, масштаб
def label(t, x, y):
    cx, cy = P(x, y)
    dr.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], fill=(255, 255, 255), outline=(40, 52, 70), width=2)
    dr.text((cx, cy), t, font=F, fill=(40, 52, 70), anchor='mm')


for v in VILLAS:
    label(v['id'], v['c'][0], v['c'][1] - 11)
label('05', 1258, 330)
label('06', 1189, 366)
label('08', 1327, 357)
label('11', 1402, 288)
label('12', 1350, 320)
W = img.width
dr.rectangle([10, 10, W - 10, 92], fill=(255, 255, 255, 235), outline=(140, 160, 170))
dr.text((24, 16), 'ЭЛИТНЫЙ ХОЛМ (07) · план v01 — территория ~145×120 м (было ~222×180)', font=FT, fill=(40, 52, 70))
dr.text((24, 50), '01–04 виллы знаменитостей-стримеров по углам · кольцо · 05 ФБР — главная охрана · 06 КПП со шлагбаумом',
        font=FS, fill=(90, 100, 106))
dr.text((24, 70), '08 смотровая · 12 лестница к частному пляжу (калитка на замке) · 11 три разных угловатых причала с яхтами',
        font=FS, fill=(90, 100, 106))
sx, sy = P(1130, 210)
dr.rectangle([sx, sy, sx + 50 * K, sy + 6], fill=(40, 52, 70))
dr.text((sx + 50 * K + 10, sy + 3), '50 м', font=FS, fill=(40, 52, 70), anchor='lm')
img.save(OUT)
json.dump({'units': 'метры мира (x восток, y север), как WORLD_MAP', **EXP}, open(OJS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(OLG, 'w', encoding='utf-8-sig').write('''ЭЛИТНЫЙ ХОЛМ (07) — ЛЕГЕНДА v01 (спека docs/specs/ELITE_SPEC_2026-10-15_v01.md)
Территория ~145×120 м (x 1185…1331, y 275…395 м мира), высокий забор с колючкой.
01–04 Виллы знаменитостей-стримеров по углам (СЗ, СВ, ЮВ, ЮЗ), на террасах разной высоты, у каждой сад и бассейн.
Кольцевая дорога вокруг центра, к ней подъезды всех вилл. Въезд с запада от дороги из Даунтауна.
05 ФБР — в центре кольца, главный пост охраны, флаг, 2 джипа охраны.
06 КПП со шлагбаумом у въезда.
08 Смотровая на восточном краю (открыто — оставлять ли).
12 Лестница вниз к частному пляжу, внизу калитка на замке.
11 Три разных угловатых причала: Г-образный, Т-образный, ломаный с плавучей площадкой; 5 яхт и катер.
Координаты всех объектов — Элитный_холм_v01.json.
''')
print('ok', OUT)
