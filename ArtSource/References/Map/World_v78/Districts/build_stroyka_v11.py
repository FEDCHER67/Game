"""Интернациональная стройка — v11 (TASK-000840/841, Вадим 20.10.2026: «чуть-чуть более понятнее планировку… бараки
обособленно, не прямо друг к другу впритирку, чуть-чуть между ними место… два недостроенных небольших дома, на одном
стоит кран, другой тоже недостроен»): корпуса А и Б — два небольших недостроенных дома (А 24 × 14 м: каркас, леса,
кран у него; Б 20 × 12 м: плита и первые колонны); бытовой городок — отдельной группой у восточного забора, одноэтажные
блок-контейнеры 6 × 2,4 м с проходами ~3 м, без двухэтажных рядов с галереями. Остальное как v10.
Ранее: Интернациональная стройка (вместо «Перехода») — предложение планировки v08.

По замечаниям Вадима: никаких внутренних заборчиков — один забор вокруг всего района (v04); бытовки стоят рядами,
как на типичной СНГ-стройке: блок-контейнеры 6 × 2,4 м, двухэтажные ряды с галереей и лестницей, прорабская,
столовая, душевая, ряд биотуалетов, ПАЗик у ворот (v06); здания ровные, стройматериалы слегка вразнобой, но
логично; бетонной дороги нет, въезд свободный по грунту; в заборе, кроме трёх ворот, вырезы под бусик (v07).
v08: бытовок ещё немного меньше, стоят ровно и не вплотную (зазор ~1 м); все въезды сильно шире; забор — ровный
прямоугольник, главная улица и дорога на Неблагополучный район идут параллельно забору, без перекоса.
Обычная СНГ-стройка в уменьшенном формате, базы нет. Маленькая АЗС стоит снаружи у дороги.
Стандарт схем: вид сверху, однотонные заливки, тонкие контуры, деревья — круги, проезды — песочные полосы,
пешеходные пути — синий пунктир, на схеме только номера. 1 единица = 0,2 м.
v10: дорога на Неблагополучный район прямая, вдоль забора до самого верха; проезды от ворот
уходят под асфальт; асфальт тёмный, как на общей карте.
Запуск: python build_stroyka_v10.py --png
"""
import io
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_SVG = os.path.join(HERE, 'Интернациональная_стройка_v11.svg')
OUT_PNG = os.path.join(HERE, 'Интернациональная_стройка_v11.png')
W, H = 940, 1000
INK = '#34424B'
FONT = 'Arial, sans-serif'
rnd = random.Random(9)


def f(v):
    s = '%.1f' % v
    return s[:-2] if s.endswith('.0') else s


def pts(p):
    return ' '.join('%s,%s' % (f(x), f(y)) for x, y in p)


def poly(p, fill, stroke='none', sw=1, extra=''):
    return '<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"%s/>' % (
        pts(p), fill, stroke, f(sw), extra)


def line(p, stroke, sw, cap='round', extra=''):
    return '<polyline points="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linejoin="round" ' \
           'stroke-linecap="%s"%s/>' % (pts(p), stroke, f(sw), cap, extra)


def rect(x0, y0, x1, y1, fill, stroke='none', sw=1, extra=''):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill, stroke, sw, extra)


def circle(c, r, fill, stroke='none', sw=1, extra=''):
    return '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"%s/>' % (
        f(c[0]), f(c[1]), f(r), fill, stroke, f(sw), extra)


def text(x, y, s, size, weight=400, fill=INK, anchor='start'):
    return ('<text x="%s" y="%s" font-family="%s" font-size="%s" font-weight="%s" fill="%s" text-anchor="%s" '
            'dominant-baseline="central">%s</text>' % (f(x), f(y), FONT, f(size), weight, fill, anchor, s))


def rr(c, w, h, ang):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    return [(c[0] + dx * ca - dy * sa, c[1] + dx * sa + dy * ca)
            for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2))]


def tr(c, ang, p):
    a = math.radians(ang)
    return (c[0] + p[0] * math.cos(a) - p[1] * math.sin(a), c[1] + p[0] * math.sin(a) + p[1] * math.cos(a))


def blob(c, rx, ry, seed, n=16, rough=0.22):
    r2 = random.Random(seed)
    out = []
    for i in range(n):
        t = 2 * math.pi * i / n
        k = 1 - rough + 2 * rough * r2.random()
        out.append((c[0] + rx * k * math.cos(t), c[1] + ry * k * math.sin(t)))
    return out


def group(gid, items):
    return ['<g id="%s">' % gid] + items + ['</g>']


# ------------------------------------------------------------------ каркас района (1 ед. = 0,2 м)
R1 = [(0, 718), (940, 718)]                                                                    # главная улица, вдоль забора
R2 = [(750, 718), (750, 0)]                                                                    # к Rough, прямо вдоль забора
R3 = [(316, 718), (316, 1000)]                                                                   # к долине и лесу, прямо
FENCE = [(160, 126), (300, 104), (470, 96), (600, 112), (712, 126), (712, 690), (176, 690), (120, 634),
         (120, 470), (104, 400), (110, 300), (120, 226)]   # v09: вдоль дорог ровно, с севера и запада ломаный, не квадрат
GATE_MAIN = ((417, 690), 96)    # ворота стройки на главную улицу (центр, ширина ~19 м)
GATE_SHOP = ((640, 690), 90)    # ворота мастерской на главную улицу (~18 м)
GATE_EAST = ((712, 328), 90)    # восточные ворота к дороге на Rough (~18 м)
CRANE = (336, 296)                                # v11: у корпуса А
# бытовой городок как на типичной СНГ-стройке: блок-контейнеры 6 × 2,4 м (12 × 30 ед.) ровно, не вплотную,
# двухэтажные ряды с галереей и лестницей, разные цвета
GAP = 15                                         # v11: проход между бытовками ~3 м (было ~1 м)
BLOCKS = [((548, 236), 4, 0, 'S'),               # жилой ряд А (одноэтажные бытовки)
          ((548, 340), 4, 0, 'N')]               # жилой ряд Б
EAST_BLOCK = ((674, 400), 2, 0)                  # две бытовки поперёк, у восточного забора
SERVICE_ROW = ((548, 432), (('#C8BFA8', 2), ('#A9C0CC', 1)), 0)  # столовая, душевая
OFFICE = ((676, 236), 1, 0)                       # прорабская у восточного въезда
# в заборе: три ворот + вырезы под бусик (центр, ширина ~12 м)
CUTS = [((210, 690), 60), ((120, 440), 60), ((482, 126), 60), ((712, 532), 60)]
DORM = ((612, 176), 0, 170, 56)
WORKSHOP = ((640, 612), 0, 120, 60)


def build():
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (W * 2, H * 2, W, H)]
    o.append('<rect width="%d" height="%d" fill="white"/>' % (W, H))

    # ---- terrain: луг, река с мостом, утоптанная земля за забором, грязь у стройки, лужи
    ter = [rect(0, 0, W, H, '#E9EFDC')]
    river = [(40, 0), (34, 200), (46, 400), (38, 600), (42, 800), (36, 1000)]
    ter.append(line(river, '#B7D6CC', 50))
    ter.append(line(river, '#8FC3D9', 40))
    ter.append(poly(FENCE, '#DDD1B3'))
    for i, (c, rx, ry) in enumerate((((300, 610), 80, 30), ((460, 640), 40, 22), ((210, 360), 50, 16),
                                     ((470, 520), 34, 20), ((560, 440), 50, 30), ((640, 650), 60, 20))):
        ter.append(poly(blob(c, rx, ry, 30 + i, 16, 0.3), '#CDB68C'))
    ter.append(poly(blob((610, 250), 90, 34, 51, 16, 0.25), '#E6DCC4'))                          # двор у общаги
    for c in ((418, 702), (290, 650), (626, 500), (470, 420), (700, 690)):
        ter.append(poly(blob(c, 10, 5, int(c[0]), 10, 0.3), '#A9CBD6'))
    o += group('terrain', ter)

    # ---- roads: асфальт, плиты на стройке, грунтовые проезды
    rd = []
    tracks = [[(640, 718), (640, 646)],                                     # к воротам мастерской (из-под дороги)
              [(750, 328), (712, 328), (650, 334), (610, 340)]]             # восточные ворота → городок (из-под R2)
    for t in tracks:
        rd.append(line(t, '#CDBB8C', 22))
    for t in tracks:
        rd.append(line(t, '#E3D1A2', 17))
    for pl in (R1, R2, R3):
        rd.append(line(pl, '#D3D2C3', 46, 'butt'))
    for pl in (R1, R2, R3):
        rd.append(line(pl, '#5F666C', 32, 'butt'))
    for i, c in enumerate(((180, 718), (560, 720), (800, 722), (750, 560))):
        rd.append(poly(blob(c, 11, 5, 90 + i, 10, 0.35), '#A9B1B5'))
    rd.append(rect(10, 697, 72, 739, '#C9BFA8', '#6E6352', 1.4))                                  # мост
    for y in (700, 736):
        rd.append(line([(12, y), (70, y)], '#6E6352', 2))
    for t in ([(417, 716), (417, 560), (380, 470), (300, 400), (200, 380)],
              [(410, 700), (400, 600), (430, 520), (460, 420), (470, 330)],
              [(212, 700), (230, 640), (300, 600)]):
        rd.append(line(t, '#B9A27A', 1.2, extra=' stroke-dasharray="7 6"'))                    # колеи по грунту
    rd.append(rect(150, 756, 262, 820, '#CDD3D5', '#AEB6B9', 1))                                  # площадка АЗС
    o += group('roads', rd)

    # ---- paths
    ph = []
    for p in ([(470, 420), (510, 380), (530, 330)], [(512, 560), (480, 610), (470, 640)],
              [(640, 206), (652, 222), (652, 276), (640, 330)]):
        ph.append(line(p, '#5E8FBF', 2.2, extra=' stroke-dasharray="6 5"'))
    o += group('paths', ph)

    # ---- buildings
    b = []
    # 04 корпус А — небольшой недострой 24 × 14 м: монолитный каркас (плиты, колонны), леса с юга, кран рядом
    b.append(rect(190, 200, 310, 270, '#D8D7D1', '#6F767B', 1.5))
    b.append(rect(250, 200, 310, 235, '#C9C8C1', '#6F767B', 0.8))                                 # верхний этаж не закрыт
    for x in range(200, 306, 20):
        for y in (210, 235, 260):
            b.append(rect(x - 3, y - 3, x + 3, y + 3, '#5E6569'))
    b.append(rect(236, 222, 256, 250, '#B9BCB8', '#6F767B', 1))                                   # лестнично-лифтовое ядро
    b.append(rect(190, 270, 310, 280, '#E6C98F', '#B08B4E', 1))                                   # леса
    for x in range(194, 306, 10):
        b.append(line([(x, 280), (x + 8, 270)], '#B08B4E', 0.8))
    b.append(rect(310, 226, 322, 244, '#7C8083', '#4F5458', 1))                                   # грузовой подъёмник
    # 05 корпус Б — недострой 20 × 12 м: плита, первые колонны, арматура торчит
    b.append(rect(190, 430, 290, 490, '#CFCFC8', '#6F767B', 1.4))
    for i, x in enumerate(range(200, 286, 20)):
        for y in (440, 460, 480):
            if i < 2:
                b.append(rect(x - 3.5, y - 3.5, x + 3.5, y + 3.5, '#5E6569'))
            else:
                b.append(line([(x - 2.5, y - 2.5), (x + 2.5, y + 2.5)], '#8E5B42', 1))
                b.append(line([(x - 2.5, y + 2.5), (x + 2.5, y - 2.5)], '#8E5B42', 1))
    for k in range(2):
        b.append(rect(204 + k * 30, 466, 228 + k * 30, 476, '#D2B48C', '#A88B5E', 0.8))           # опалубка
    # 08 общежитие
    c, a, w, h = DORM
    b.append(poly(rr(c, w, h, a), '#D4CBBB', '#49535B', 1.8))
    b.append(line([tr(c, a, (-w / 2 + 8, 0)), tr(c, a, (w / 2 - 8, 0))], '#B8AE9E', 1))
    for x in (-40, 40):
        b.append(poly(rr(tr(c, a, (x, h / 2 + 4)), 16, 8, a), '#8E979B', '#49535B', 0.8))
    # 07 бытовой городок
    cols = ('#8FA9B8', '#C9D2D8', '#A9C0CC', '#8FA9B8', '#C8BFA8', '#9DB1BE', '#A47E62', '#C9D2D8', '#8FA9B8')

    def cont(c, ang, w, h, col):
        b.append(poly(rr(c, w, h, ang), col, '#46596A', 1.1))

    step = 12 + GAP
    for (x0, y0), n, ang, side in BLOCKS:
        for i in range(n):
            c = tr((x0, y0), ang, (i * step + 6, 15))
            cont(c, ang, 12, 30, cols[(i * 7 + int(x0)) % len(cols)])
            st = tr(c, ang, (0, 18 if side == 'S' else -18))                                    # крылечко у двери
            b.append(poly(rr(st, 6, 4, ang), '#9AA3A8', '#5E6569', 0.6))
    (x0, y0), n, ang = EAST_BLOCK
    for i in range(n):
        c = tr((x0, y0), ang, (15, i * step + 6))
        cont(c, ang, 30, 12, cols[(i * 5 + 3) % len(cols)])
    (x0, y0), parts, ang = SERVICE_ROW
    k = 0
    for col, m in parts:
        for i in range(m):
            cont(tr((x0, y0), ang, (k * (12 + GAP) + 6, 15)), ang, 12, 30, col)
            k += 1
    (x0, y0), n, ang = OFFICE
    for i in range(n):
        cont(tr((x0, y0), ang, (i * 12 + 6, 15)), ang, 12, 30, '#DDE2E5')
    # 03 будка охраны у главных ворот
    b.append(rect(456, 640, 480, 662, '#B5C8CE', INK, 1.4))
    # 01 мастерская для бусика: ворота к своим воротам в заборе, перед ней пятак
    c, a, w, h = WORKSHOP
    b.append(rect(c[0] - w / 2, c[1] - h / 2, c[0] + w / 2, c[1] + h / 2, '#C6AB97', INK, 2))
    for x in (-36, 0, 36):
        b.append(rect(c[0] + x - 14, c[1] + h / 2 - 2, c[0] + x + 14, c[1] + h / 2 + 4, '#5E6569'))
    # 02 маленькая АЗС снаружи у дороги
    b.append(rect(162, 764, 222, 798, '#ECEEEF', '#6F767B', 1.3))
    b.append(rect(178, 778, 206, 784, '#8E979B', '#5E6569', 0.8))
    b.append(rect(230, 774, 256, 802, '#CAD5D7', INK, 1.6))
    o += group('buildings', b)

    # ---- objects: один забор с открытыми въездами, кран, склад, техника, быт
    ob = []
    fence = '#6F8FA8'
    gaps = [GATE_MAIN, GATE_SHOP, GATE_EAST] + CUTS
    ring = FENCE + [FENCE[0]]
    acc = [0.0]
    for a_, b_ in zip(ring[:-1], ring[1:]):
        acc.append(acc[-1] + math.hypot(b_[0] - a_[0], b_[1] - a_[1]))

    def at(L):
        for i in range(len(ring) - 1):
            if acc[i] <= L <= acc[i + 1]:
                t = (L - acc[i]) / ((acc[i + 1] - acc[i]) or 1)
                return (ring[i][0] + (ring[i + 1][0] - ring[i][0]) * t, ring[i][1] + (ring[i + 1][1] - ring[i][1]) * t)
        return ring[-1]

    def proj(q):
        best = (1e9, 0.0)
        for i in range(len(ring) - 1):
            a_, b_ = ring[i], ring[i + 1]
            dx, dy = b_[0] - a_[0], b_[1] - a_[1]
            L2 = dx * dx + dy * dy
            t = max(0.0, min(1.0, ((q[0] - a_[0]) * dx + (q[1] - a_[1]) * dy) / L2))
            d = math.hypot(a_[0] + t * dx - q[0], a_[1] + t * dy - q[1])
            if d < best[0]:
                best = (d, acc[i] + t * math.sqrt(L2))
        return best[1]
    cuts = sorted((proj(q) - wdt / 2.0, proj(q) + wdt / 2.0) for q, wdt in gaps)
    pos = 0.0
    for g0, g1 in cuts + [(acc[-1], acc[-1])]:
        if g0 > pos:
            seg = [at(pos)] + [ring[i] for i in range(len(ring)) if pos < acc[i] < g0] + [at(g0)]
            ob.append(line(seg, fence, 3.2, 'butt'))
        if g1 > g0:
            for L in (g0, g1):
                q = at(L)
                ob.append(rect(q[0] - 3, q[1] - 3, q[0] + 3, q[1] + 3, '#3E5A70'))
        pos = max(pos, g1)
    ob.append(rect(398, 632, 436, 658, '#9AA3A8', '#6F767B', 1))                                 # мойка колёс
    for x in range(402, 434, 5):
        ob.append(line([(x, 634), (x, 656)], '#6F767B', 0.7))
    # 06 кран
    ob.append(circle(CRANE, 150, 'none', '#D9A43A', 1, ' stroke-dasharray="4 8" stroke-opacity="0.45"'))
    ob.append(rect(CRANE[0] - 8, CRANE[1] - 8, CRANE[0] + 8, CRANE[1] + 8, '#E2B13B', '#8A6A1F', 1.2))
    ob.append(poly(rr((CRANE[0] - 72, CRANE[1] - 40), 150, 6, 30), '#F0C24E', '#8A6A1F', 1))        # стрела над корпусом А
    ob.append(poly(rr((CRANE[0] + 24, CRANE[1] + 14), 46, 8, 30), '#F0C24E', '#8A6A1F', 1))
    ob.append(rect(CRANE[0] + 38, CRANE[1] + 18, CRANE[0] + 52, CRANE[1] + 32, '#7C8083', '#4F5458', 1))
    # склад: кирпич, блоки, арматура, опалубка, трубы, песок, щебень — стопками, слегка вразнобой
    for i in range(3):
        for j in range(2):
            c = (444 + i * 22 + rnd.uniform(-2.5, 2.5), 176 + j * 22 + rnd.uniform(-2.5, 2.5))
            ob.append(poly(rr(c, 16, 16, rnd.uniform(-9, 9)), '#B5705A', '#7E4A3A', 0.8))
    for i in range(3):
        c = (444 + i * 21 + rnd.uniform(-3, 3), 226 + rnd.uniform(-3, 3))
        ob.append(poly(rr(c, 16, 16, rnd.uniform(-10, 10)), '#C3C6BF', '#7C8279', 0.8))
    for k in range(6):
        y = 252 + k * 3
        ob.append(line([(436 + rnd.uniform(-3, 3), y + rnd.uniform(-1, 1)),
                        (500 + rnd.uniform(-4, 4), y + rnd.uniform(-2, 2))], '#8E5B42', 1.2))
    for k in range(3):
        ob.append(poly(rr((467 + rnd.uniform(-4, 4), 424 + k * 12), 62, 8, rnd.uniform(-4, 4)), '#D2B48C',
                       '#A88B5E', 0.8))
    for k in range(3):
        ob.append(poly(rr((469 + rnd.uniform(-3, 3), 472 + k * 7), 62, 4, rnd.uniform(-3, 3)), '#9AA3A8',
                       '#6F767B', 0.6))
    ob.append(poly(blob((466, 548), 18, 15, 61, 14, 0.18), '#EBD9A2', '#C8B47A', 1.1))
    ob.append(poly(blob((494, 574), 13, 11, 62, 12, 0.18), '#BDBDB4', '#8E8E86', 1.1))
    for c, a in (((350, 330), 12), ((158, 420), -8), ((356, 560), 20), ((206, 560), -14)):
        ob.append(poly(rr(c, 34, 7, a), '#D2B48C', '#A88B5E', 0.7))                              # щиты опалубки у корпусов
    ob.append(rect(470, 604, 504, 622, '#6F7D74', '#3F4A43', 1))                                  # бункер для мусора
    ob.append(rect(140, 612, 162, 634, '#9DB1BE', '#46596A', 1))                                  # трансформаторная
    ob.append(circle((152, 660), 9, '#A9B7C2', '#46596A', 1))                                     # бак с водой
    # техника
    ob.append(rect(238, 362, 286, 382, '#B9C3C8', '#5E6569', 1))
    ob.append(circle((276, 372), 8, '#8E979B', '#5E6569', 0.8))
    ob.append(poly(rr((360, 570), 44, 18, -8), '#C7A04D', '#6E5A2A', 1))
    ob.append(poly(rr((262, 590), 22, 14, 20), '#E2B13B', '#6E5A2A', 1))
    # беспорядок в меру
    for c in ((150, 170), (150, 560), (300, 650), (500, 330), (360, 160), (220, 650), (520, 452), (520, 230)):
        ob.append(poly(rr(c, 20, 16, rnd.uniform(0, 40)), '#C9AE80', '#8E7651', 0.8))
    for c in ((700, 236), (520, 470), (650, 520), (566, 650)):
        for k in range(3):
            ob.append(circle((c[0] + rnd.uniform(-6, 6), c[1] + rnd.uniform(-6, 6)), 3.6, '#3F4447', '#26292B', 0.5))
    for c in ((640, 600), (516, 300)):
        for k in range(2):
            ob.append(circle((c[0] + k * 8, c[1]), 4, ('#5E7471', '#B5705A')[k], INK, 0.6))
    # двор городка: бельё, курилка, лавки, бочка-костёр; ряд биотуалетов, бункер, бак; ПАЗик у ворот
    for p0, p1 in (((552, 290), (612, 290)), ((552, 314), (612, 314))):
        ob.append(line([p0, p1], '#8E979B', 0.8))
        n = int(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 14)
        for k in range(1, n):
            t = k / float(n)
            x, y = p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t
            ob.append(rect(x - 3, y + 1, x + 3, y + 8, rnd.choice(('#C0705D', '#5E8FBF', '#E2B13B', '#F4F1E8'))))
    ob.append(poly(rr((624, 288), 22, 16, 2), '#B49B75', '#7A5E2E', 1, ' fill-opacity="0.6"'))      # курилка
    for x in (612, 636):
        ob.append(rect(x - 11, 300, x + 11, 305, '#B49B75', INK, 0.7))                            # лавки
    ob.append(circle((620, 318), 5, '#5E6569', '#26292B', 1))
    ob.append(circle((620, 318), 2.5, '#E2803A'))
    for i in range(4):
        ob.append(rect(600 + i * 10, 482, 606 + i * 10, 488, '#4E86B8', '#2F4F6E', 0.7))           # биотуалеты
    ob.append(rect(646, 478, 668, 492, '#6F7D74', '#3F4A43', 1))                                  # бункер
    ob.append(circle((688, 486), 8, '#A9B7C2', '#46596A', 1))                                     # бак с водой
    ob.append(poly(rr((678, 300), 40, 14, -2), '#E2C24E', '#6E5A2A', 1.2))                         # ПАЗик
    ob.append(rect(661, 296, 669, 304, '#9DB1BE'))
    # мастерская: бусик, шины, металлолом, бочки, ржавый кузов
    ob.append(rect(590, 650, 626, 666, '#8E979B', '#5E6569', 1))
    ob.append(rect(593, 652, 623, 664, '#E5E0D2', INK, 1))
    for c2 in ((690, 650), (700, 660), (690, 668)):
        ob.append(circle(c2, 5, '#3F4447', '#26292B', 0.8))
    ob.append(poly(blob((560, 640), 12, 8, 4, 9, 0.4), '#9A8F7E', '#6A6255', 0.8))
    ob.append(poly(rr((690, 590), 30, 14, 76), '#9B6A50', '#5C3F30', 1))
    # фонари / GripAnchor
    for p0 in ((140, 699), (330, 699), (560, 699), (776, 699), (420, 400), (600, 400), (560, 210), (729, 620)):
        ob.append(circle(p0, 4, '#FFFDF4', '#BA8442', 1.5))
    o += group('objects', ob)

    # ---- trees
    trs = []
    hidden = []

    clear = [(446, 56, 518, 126), (446, 126, 518, 172), (62, 404, 120, 476)]   # проезд через вырезы

    def blocked(c, r):
        return any(a[0] - r < c[0] < a[2] + r and a[1] - r < c[1] < a[3] + r for a in clear)

    def scatter(box, n, rmin=8, rmax=13, keep=()):
        x0, y0, x1, y1 = box
        k = tries = 0
        while k < n and tries < n * 40:
            tries += 1
            c = (rnd.uniform(x0, x1), rnd.uniform(y0, y1))
            if any(a[0] <= c[0] <= a[2] and a[1] <= c[1] <= a[3] for a in keep):
                continue
            r = rnd.uniform(rmin, rmax)
            k += 1
            if blocked(c, r):
                hidden.append((round(c[0]), round(c[1])))
                continue
            trs.append(circle(c, r, '#C7D7B4', '#8FA37D', 1))
            trs.append(circle(c, 2, '#82966F'))
    roadbox = [(0, 688, 940, 760), (720, 0, 790, 760), (292, 710, 344, 1000)]
    scatter((80, 0, 940, 112), 64, keep=roadbox)
    scatter((800, 270, 940, 690), 26, keep=roadbox)
    scatter((780, 760, 940, 1000), 16, keep=roadbox)
    scatter((80, 840, 780, 1000), 30, keep=roadbox + [(140, 750, 270, 830)])
    scatter((70, 112, 112, 1000), 18, 7, 10, keep=roadbox)
    scatter((360, 760, 780, 840), 14, keep=roadbox)
    for c in ((690, 150), (130, 300), (512, 160)):
        if blocked(c, 9):
            hidden.append(c)
            continue
        trs.append(circle(c, 9, '#C7D7B4', '#8FA37D', 1))
        trs.append(circle(c, 2, '#82966F'))
    o += group('trees', trs)
    print('trees hidden at cut-outs:', hidden)

    # ---- numbers
    nums = [('01', (WORKSHOP[0][0], WORKSHOP[0][1] - 4)), ('02', (243, 788)), ('03', (440, 580)), ('04', (226, 236)),
            ('05', (240, 452)), ('06', (CRANE[0] + 20, CRANE[1] - 22)), ('07', (640, 300)), ('08', (612, 176))]
    nb = []
    for s, (x, y) in nums:
        nb.append(circle((x, y), 11, '#FFFFFF', INK, 1.6))
        nb.append(text(x, y + 0.5, s, 11, 700, INK, 'middle'))
    o += group('numbers', nb)

    # ---- title, directions, north arrow, scale
    t = [rect(14, 14, 660, 74, '#FFFFFF', '#8FA9B1', 1.2, ' fill-opacity="0.94"')]
    t.append(text(30, 34, 'РАЙОН «ИНТЕРНАЦИОНАЛЬНАЯ СТРОЙКА» · v11', 19, 700))
    t.append(text(30, 58, 'Два небольших недостроя (у А — кран) · бытовки отдельно, с проходами · один забор · 1 ед. = 0,2 м', 11.5, 400,
                  '#6D7A80'))
    t.append(text(78, 676, '← Хутор (мост)', 12, 700, '#5F6E75'))
    t.append(text(930, 96, '↑ Неблагополучный район', 12, 700, '#5F6E75', 'end'))
    t.append(text(930, 766, 'Город (Downtown) →', 12, 700, '#5F6E75', 'end'))
    t.append(text(326, 980, '↓ Тихая долина, лес', 12, 700, '#5F6E75'))
    t.append(text(905, 112, 'С', 12, 700, INK, 'middle'))
    t.append(line([(905, 150), (905, 126)], INK, 2))
    t.append(poly([(905, 120), (901, 132), (909, 132)], INK))
    for i in range(5):
        t.append(rect(120 + i * 50, 950, 170 + i * 50, 958, INK if i % 2 == 0 else '#FFFFFF', INK, 1))
    t.append(text(120, 940, '0', 10, 600, INK, 'middle'))
    t.append(text(370, 940, '50 м', 10, 600, INK, 'middle'))
    o += group('title', t)
    o.append('</svg>')
    return '\n'.join(o)


if __name__ == '__main__':
    io.open(OUT_SVG, 'w', encoding='utf-8').write(build())
    print('wrote', OUT_SVG)
    if '--png' in sys.argv:
        sys.path.insert(0, r'C:\Users\chern_0eqkb03\AppData\Local\Temp\npcw\mapjoin\build')
        import render
        print(render.render(OUT_SVG, OUT_PNG, W * 2))
