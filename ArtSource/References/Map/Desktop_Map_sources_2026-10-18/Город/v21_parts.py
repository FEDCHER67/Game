# ---- STREETS ----
AXIS = 1170
ROAD, SW = 42.5, 20.0
ST = {
    # кольцо с заломами (край города) — как в v20
    'N1': St([(100, 150), (445, 150)], ROAD, SW, cap='square'),
    'N2': St([(445, 70), (1170, 70)], ROAD, SW, cap='square'),
    'Nj': St([(1170, 70), (1170, 150)], ROAD, SW, cap='square'),
    'N3': St([(1170, 150), (1840, 150), (1840, 330), (2240, 330)], ROAD, SW, cap='square'),
    'W1': St([(100, 150), (100, 760)], ROAD, SW, cap='square'),
    'W2': St([(20, 760), (20, 1210)], ROAD, SW, cap='square'),
    'E1': St([(2240, 330), (2240, 760)], ROAD, SW, cap='square'),
    'E2': St([(2320, 760), (2320, 1130)], ROAD, SW, cap='square'),
    'S1': St([(20, 1210), (620, 1210)], ROAD, SW, cap='square'),
    'S2': St([(620, 1130), (1170, 1130)], ROAD, SW, cap='square'),
    'S3': St([(1170, 1210), (1840, 1210)], ROAD, SW, cap='square'),
    'S4': St([(1840, 1130), (2320, 1130)], ROAD, SW, cap='square'),
    'B': St([(XMIN, 760), (790, 760), (790, 860), (1550, 860), (1550, 760), (XMAX, 760)], ROAD, SW),
    # сетка: северная половина
    'Vn': St([(445, 70), (445, 760)], ROAD, SW, cap='square'),
    'Vb': St([(790, 70), (790, 760)], ROAD, SW, cap='square'),
    'Vc': St([(1550, 150), (1550, 760)], ROAD, SW, cap='square'),
    'Hnw': St([(100, 455), (790, 455)], ROAD, SW, cap='square'),
    'Hne': St([(1550, 455), (1840, 455)], ROAD, SW, cap='square'),
    'Hne2': St([(1840, 545), (2240, 545)], ROAD, SW, cap='square'),
    # сетка: южная половина — сдвинута относительно северной (стык буквой Т на бульваре)
    'Vs1': St([(320, 760), (320, 1210)], ROAD, SW, cap='square'),
    'Va2': St([(620, 760), (620, H)], ROAD, SW),                      # мост 1 на пляж
    'Vs2': St([(900, 860), (900, 1130)], ROAD, SW, cap='square'),
    'AX': St([(AXIS, 860), (AXIS, 1210)], ROAD, SW, cap='square'),
    'Vs3': St([(1505, 860), (1505, 1210)], ROAD, SW, cap='square'),
    'Vd': St([(1840, 150), (1840, H)], ROAD, SW),                     # мост 2 на пляж
    'Hsw': St([(20, 990), (620, 990)], ROAD, SW, cap='square'),
    'Hse': St([(AXIS, 1030), (1840, 1030)], ROAD, SW, cap='square'),
    'Hse2': St([(1840, 960), (2320, 960)], ROAD, SW, cap='square'),
}
CANAL = [(XMIN, 1342), (800, 1336), (1600, 1340), (XMAX, 1348)]
DISTRICT = [(100, 150), (445, 150), (445, 70), (1170, 70), (1170, 150), (1840, 150), (1840, 330), (2240, 330),
            (2240, 760), (2320, 760), (2320, 1130), (1840, 1130), (1840, 1210), (1170, 1210), (1170, 1130),
            (620, 1130), (620, 1210), (20, 1210), (20, 760), (100, 760)]
RING = ('N1', 'N2', 'Nj', 'N3', 'W1', 'W2', 'E1', 'E2', 'S1', 'S2', 'S3', 'S4')
# ---- /STREETS ----

# ---- BLOCKS ----
BLK = {
    'NW1': R(141, 191, 404, 414), 'NW2': R(141, 496, 404, 719),
    'NC1': R(486, 111, 749, 414), 'NC2': R(486, 496, 749, 719),
    'SQ': [(831, 111), (1129, 111), (1129, 191), (1509, 191), (1509, 814), (831, 814)],
    'NE1': R(1591, 191, 1799, 414), 'NE2': R(1591, 496, 1799, 719),
    'Ea1': R(1881, 371, 2199, 504), 'Ea2': R(1881, 586, 2199, 719),
    'SW1': R(61, 801, 279, 949), 'SW2': R(361, 801, 579, 949),
    'SW3': R(61, 1031, 279, 1169), 'SW4': R(361, 1031, 579, 1169),
    'SC1': [(661, 801), (749, 801), (749, 901), (859, 901), (859, 1089), (661, 1089)],
    'SC2': R(941, 901, 1129, 1089),
    'SE1': R(1211, 901, 1464, 989),
    'SE2': [(1546, 901), (1591, 901), (1591, 801), (1799, 801), (1799, 989), (1546, 989)],
    'SE3': R(1211, 1071, 1464, 1169), 'SE4': R(1546, 1071, 1799, 1169),
    'Eb': R(1881, 801, 2279, 919), 'Ec': R(1881, 1001, 2279, 1089),
    'S2s': R(661, 1171, 1129, 1240), 'S4s': R(1881, 1171, 2350, 1240),
    'NEX': R(1881, 105, 2150, 289),
    'OB1': R(1211, 12, 1450, 109), 'OB2': R(-70, 616, -21, 719), 'OB3': R(2361, 616, 2420, 719),
}
# ---- /BLOCKS ----

# ---- CITY ----
HOUSE_COLS = ('#A65A45', '#7E4436', '#B8735A', '#C9A35A', '#74805A', '#4F7D7A', '#5D7189', '#B98478',
              '#D9C9A8', '#BE9A72', '#A9A69C', '#4F6B55', '#B98B4E', '#7A5560', '#8C6A4F', '#9FB0A8')
_hr = random.Random(2121)
_last = ['']
ALLEY_DW = []


def pick_col():
    while True:
        c = _hr.choice(HOUSE_COLS)
        if c != _last[0]:
            _last[0] = c
            return c


def rowfill(x0, y0, x1, y1, street, gaps=(), wmin=36, wmax=80, corners=True):
    """Сплошная стена домов вдоль улицы без щелей. Угловые дома крупнее и выше (как в американском даунтауне)."""
    horiz = street in ('N', 'S')
    a0, a1 = (x0, x1) if horiz else (y0, y1)
    cuts = sorted(g for g in gaps if a0 < g[1] and g[0] < a1)
    spans, pos = [], a0
    for g0, g1 in cuts:
        if g0 > pos:
            spans.append((pos, g0))
        pos = max(pos, g1)
    if pos < a1:
        spans.append((pos, a1))
    for si, (s0, s1) in enumerate(spans):
        edges = [s0]
        big_first = corners and si == 0 and s1 - s0 > 150
        if big_first:
            edges.append(s0 + _hr.uniform(70, 96))
        while s1 - edges[-1] > wmax:
            edges.append(edges[-1] + _hr.uniform(wmin, wmax))
        if corners and si == len(spans) - 1 and s1 - s0 > 150 and s1 - edges[-1] < 70 and len(edges) > 2:
            edges.pop()                                              # последний (угловой) дом крупнее
        if len(edges) > 1 and s1 - edges[-1] < wmin * 0.7:
            edges.pop()
        edges.append(s1)
        n = len(edges) - 1
        for k, (p0, p1) in enumerate(zip(edges[:-1], edges[1:])):
            corner = corners and ((si == 0 and k == 0) or (si == len(spans) - 1 and k == n - 1))
            if horiz:
                hx0, hx1, hy0, hy1 = p0, p1, y0, y1
            else:
                hx0, hx1, hy0, hy1 = x0, x1, p0, p1
            col = pick_col()
            tower = None
            if _hr.random() < (0.55 if corner else 0.25) and (hx1 - hx0) > 26 and (hy1 - hy0) > 26:
                tower = (_hr.uniform(hx0 + 10, hx1 - 10), _hr.uniform(hy0 + 10, hy1 - 10))
            h = _hr.choice((18, 20, 22)) if corner else _hr.choice((7, 9, 11, 13, 15))
            house(hx0, hy0, hx1, hy1, col, tower=tower, h=h)
            if _hr.random() < 0.4:
                if street == 'N':
                    fire_escape((hx0 + 6, hy0), (min(hx1 - 6, hx0 + 40), hy0), (0, -1))
                elif street == 'S':
                    fire_escape((hx0 + 6, hy1), (min(hx1 - 6, hx0 + 40), hy1), (0, 1))
                elif street == 'W':
                    fire_escape((hx0, hy0 + 6), (hx0, min(hy1 - 6, hy0 + 40)), (-1, 0))
                else:
                    fire_escape((hx1, hy0 + 6), (hx1, min(hy1 - 6, hy0 + 40)), (1, 0))


def alley(pl, dead=None):
    """Глухой служебный переулок 5,6 м: тёмный асфальт, мусорные баки, стена в конце."""
    PAVE.append(poly(pl, '#9DA2A2', '#7E8484', 0.8))
    x0, y0, x1, y1 = bbox(pl)
    for k in range(2):
        if x1 - x0 > y1 - y0:
            bx, by = x0 + (x1 - x0) * (0.3 + 0.35 * k), y0 + 2
            SPEC.append(rect(bx, by, bx + 12, by + 7, '#4E6B52', '#2F4532', 0.6))
        else:
            bx, by = x0 + 2, y0 + (y1 - y0) * (0.3 + 0.35 * k)
            SPEC.append(rect(bx, by, bx + 7, by + 12, '#4E6B52', '#2F4532', 0.6))
    if dead:
        SPEC.append(line(dead, '#3C3A36', 4, 'butt'))


def us_block(x0, y0, x1, y1, horiz=None, plug=True):
    """Американский квартал: дома спиной к спине на всю глубину, посередине служебный переулок вдоль длинной
    стороны; затычка-дом посередине делает из него два глухих переулка, по одному с каждой улицы."""
    if horiz is None:
        horiz = (x1 - x0) >= (y1 - y0)
    if horiz:
        ym = (y0 + y1) / 2.0
        rowfill(x0, y0, x1, ym - 14, 'N')
        rowfill(x0, ym + 14, x1, y1, 'S', corners=False)
        xm = (x0 + x1) / 2.0
        alley(R(x0, ym - 14, xm - 12, ym + 14), dead=[(xm - 12, ym - 16), (xm - 12, ym + 16)])
        alley(R(xm + 12, ym - 14, x1, ym + 14), dead=[(xm + 12, ym - 16), (xm + 12, ym + 16)])
        house(xm - 12, ym - 14, xm + 12, ym + 14, '#8C6A4F', h=8)
        ALLEY_DW.extend([R(x0 - 21, ym - 14, x0, ym + 14), R(x1, ym - 14, x1 + 21, ym + 14)])
    else:
        xm = (x0 + x1) / 2.0
        rowfill(x0, y0, xm - 14, y1, 'W')
        rowfill(xm + 14, y0, x1, y1, 'E', corners=False)
        ym = (y0 + y1) / 2.0
        alley(R(xm - 14, y0, xm + 14, ym - 12), dead=[(xm - 16, ym - 12), (xm + 16, ym - 12)])
        alley(R(xm - 14, ym + 12, xm + 14, y1), dead=[(xm - 16, ym + 12), (xm + 16, ym + 12)])
        house(xm - 14, ym - 12, xm + 14, ym + 12, '#8C6A4F', h=8)
        ALLEY_DW.extend([R(xm - 14, y0 - 21, xm + 14, y0), R(xm - 14, y1, xm + 14, y1 + 21)])


def surface_lot(x0, y0, x1, y1, label=None):
    """Наземная парковка на пустыре за сеткой-рабицей (очень американская деталь)."""
    LOTS.append(poly(R(x0, y0, x1, y1), '#B9BDBF', '#8E9498', 0.8))
    stall_lines(x0 + 6, x1 - 6, y0 + 6, (y0 + y1) / 2.0 - 4, 12)
    stall_lines(x0 + 6, x1 - 6, (y0 + y1) / 2.0 + 4, y1 - 6, 12)
    SPEC.append(poly(R(x0 + 1, y0 + 1, x1 - 1, y1 - 1), 'none', '#5E6468', 1, ' stroke-dasharray="2 2"'))
    if label:
        num(label, ((x0 + x1) / 2.0, (y0 + y1) / 2.0))


def make_city():
#PLAZA#
    # ---- северо-запад: 4 американских квартала; 23 маленький сквер на месте половины квартала
    us_block(141, 191, 404, 414)
    rowfill(141, 496, 260, 719, 'W')
    park(fillet(R(260, 496, 404, 719), 12), [([(260, 600), (330, 590), (404, 610)], False)], 14,
         label='23', at=(330, 650), trees=4, seed=23)
    us_block(486, 111, 749, 414, horiz=False)
    us_block(486, 496, 749, 719)
    # ---- северо-восток: круглая стеклянная башня на углу; парковка-пустырь; полиция 2 + такси; сквер с прудом
    glass_round((1750, 245), 46, R(1700, 191, 1799, 300))
    rowfill(1591, 191, 1700, 255, 'N')
    rowfill(1591, 255, 1655, 414, 'W')
    rowfill(1655, 350, 1799, 414, 'S', corners=False)
    rowfill(1739, 300, 1799, 350, 'E', corners=False)
    rowfill(1591, 496, 1799, 590, 'N')
    surface_lot(1591, 600, 1799, 719, 'P')
    bld(rect_rc(2054, 376, 2199, 494, 'NE', 50), '#B9C8E6', INK, 2)
    num('11', (2124, 436))
    bld(R(1966, 376, 2054, 452), '#E5D5A0', INK, 1.8)
    num('12', (2010, 414))
    LOTS.append(poly(rrect(1886, 376, 1956, 499, 10), '#C3C9CD', '#9AA2A8', 0.8))
    stall_lines(1892, 1950, 382, 492, 14, vertical=False)
    park(fillet(R(1881, 586, 2070, 719), 14), [([(2005, 596), (2050, 640), (2005, 700), (1940, 690), (1920, 630)], True)],
         14, pond=organic((1985, 650), 34, 22, 7), label='20', at=(1900, 600), trees=3, seed=20)
    rowfill(2070, 586, 2199, 719, 'E')
    rowfill(1881, 225, 2150, 289, 'S')
    rowfill(1881, 105, 1945, 225, 'W')
    rowfill(1211, 12, 1450, 109, 'S', wmin=50, wmax=90)
    rowfill(-70, 616, -21, 719, 'S', wmin=30, wmax=60, corners=False)
    rowfill(2361, 616, 2420, 719, 'S', wmin=30, wmax=60, corners=False)
    # ---- юго-запад: 41 заправка на въезде в город, парковка-пустырь, 10 полиция 1 с ротондой
    LOTS.append(poly(R(61, 801, 279, 949), '#C9CCCB', '#9AA2A8', 0.8))
    SPEC.append(rect(80, 815, 200, 875, '#E8E2D2', '#8E8676', 1))            # навес над колонками
    for x in (105, 140, 175):
        SPEC.append(rect(x - 5, 840, x + 5, 852, '#C8372D', '#7A1E18', 0.6))
    bld(R(80, 895, 200, 945), '#D9C9A8', INK, 1.4, h=6)
    num('41', (240, 845))
    surface_lot(361, 801, 470, 949)
    rowfill(470, 801, 579, 949, 'E')
    bld(R(71, 1041, 221, 1159), '#B9C8E6', INK, 2)
    BLD.append(circle((91, 1139), 28, '#B9C8E6', INK, 2))
    num('10', (150, 1095))
    rowfill(221, 1031, 279, 1169, 'E', corners=False)
    us_block(361, 1031, 579, 1169)
    # ---- юг центра: 07 магазин для бусика; 05 стеклянный офис; кварталы с переулками; каменное здание у набережной
    bld(lshape(661, 801, 749, 990, 62, 56, 'NW'), '#E3A982', INK, 1.8)
    PAVE.append(poly(R(717, 863, 749, 990), '#D3CFC3'))
    num('07', (688, 930))
    us_block(749, 901, 859, 1089, horiz=False)
    rowfill(661, 990, 749, 1089, 'W', corners=False)
    glass_office(R(941, 901, 1129, 980))
    num('05', (1035, 940))
    rowfill(941, 980, 1129, 1089, 'S')
    classical(806, 1171, 1016, 1240, 'N')
    rowfill(661, 1171, 806, 1240, 'N')
    rowfill(1016, 1171, 1129, 1240, 'N')
    # ---- юго-восток: 06 офис; 40 дайнер на углу; лофт; кварталы с переулками
    glass_office(R(1211, 901, 1350, 989))
    num('06', (1280, 945))
    rowfill(1350, 901, 1464, 989, 'N')
    us_block(1546, 801, 1799, 989, horiz=True)
    bld(rrect(1211, 1071, 1300, 1125, 14), '#D7DDE1', '#5E6A72', 1.6, h=5)   # дайнер: хром, красная полоса
    SPEC.append(line([(1218, 1098), (1293, 1098)], '#C8372D', 3, 'butt'))
    num('40', (1255, 1145))
    rowfill(1300, 1071, 1464, 1169, 'S')
    rowfill(1211, 1125, 1300, 1169, 'S', corners=False)
    rowfill(1546, 1071, 1640, 1169, 'S')
    loft(1640, 1071, 1799, 1169, '#7E4436')
    # ---- восток: квартал с переулками; 13 база (бывший гараж, ворота на улицу)
    us_block(1881, 801, 2279, 919)
    rowfill(1881, 1001, 2080, 1089, 'N')
    bld(R(2090, 1001, 2279, 1089), '#8C9A8C', INK, 2.2, h=10)
    for x in (2110, 2160, 2210):
        SPEC.append(rect(x, 1083, x + 34, 1089, '#4E5559'))
    num('13', (2185, 1040))
    rowfill(1881, 1171, 2350, 1240, 'N')
# ---- /CITY ----
