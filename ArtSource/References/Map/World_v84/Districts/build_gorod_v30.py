"""Город / Downtown — план v30 (TASK-000852, Вадим 20.10.2026: «что это за начало дороги… такого не должно быть»): бульвар B
больше не торчит за кольцевую улицу на западе и востоке (отростки до краёв картинки убраны) — дороги карты входят прямо в углы
кольца. Ранее v29 (TASK-000843, Вадим 20.10.2026: «здесь не совсем понятно… не надо так много парковок,
пусть у нас будут домами всё закрыто, но зато широкие дороги и тротуары»; TASK-000844: «необязательно везде сдвоенные
переулки, где-то можно одинарный» — кварталы NW1 и SW2 с одним глухим переулком): наземных парковок-пустырей нет (под башнями
остался подземный паркинг 03, у такси — своя стоянка, заправка 41); на месте перекрытой Vd — сплошные дома (без хоздвора),
кварталы SE2 и Eb — два ряда спиной к спине (их переулки упёрлись бы в дома); квартал 07 проще: магазин для бусика — прямоугольный, ворота прямо
на улицу, за ним два ряда домов спиной к спине без переулка; въезды через тротуар — тёмным асфальтом переулка.
Ранее v28 (TASK-000840/841, Вадим 20.10.2026): улицы шире, как в One-Armed Robber — проезжая часть 12 м
(2 широкие полосы) + тротуары по 5 м = 22 м между фасадами (было 8,5 + 4 м); кварталы ужаты под это (всё внутри квартала
сжато к его центру, сетка улиц та же); сквозных прямых проездов «от холма до пляжа» нет: улица Vd у бульвара и Vs3 у бульвара
перекрыты домами (стык буквой Т), за домом на Vd — хоздвор с выходом на Hse2. Ранее v27 (TASK-000745, Вадим): нижний край — одна прямая набережная S1 вдоль пляжа на всю ширину (S2–S4 и узкие ряды под ними убраны), нижние кварталы до набережной, Vs2 и E2 продлены, каменное здание фасадом к пляжу. Ранее v26 (TASK-000562): v25 + дома справа от парковки P. Ранее v25 (TASK-000561): v24 + два широких хозяйственных двора 42 и 43 по референсу улицы. Ранее v24 (TASK-000560): v23 + въезд в базу 13 через арку под домом. Ранее v23 (TASK-000559): v22 + пешеходные переходы только в нужных местах (бульвар и площадь). Ранее v22 (TASK-000558): v21 + база 13 по референсу — дворик за углом с гаражом. Ранее v21 (TASK-000557): американская логика. Сетка длинных кварталов со сдвигом на бульваре
(стык буквой Т), кварталы застроены спиной к спине, посередине служебный переулок с затычкой (два глухих),
угловые дома крупнее и выше, парковки-пустыри, дайнер, заправка. Площадь «Водная ось», башни, полиции, база,
мосты — как в v20. 1 ед. = 0,2 м. Запуск: python build_gorod_v26.py (не перезаписывает)
"""
import io
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_SVG = os.path.join(HERE, 'Город_Downtown_v30.svg')
OUT_PNG = os.path.join(HERE, 'Город_Downtown_v30.png')
W, H = 2350, 1460
XMIN, XMAX = -110, 2460
PX = 1.3
INK = '#34424B'
FONT = 'Arial, sans-serif'
rnd = random.Random(1111)

LAWN, YARD, WALK, ASPH, MARK = '#E3EBD4', '#E8EEDB', '#E3E1D9', '#5F666C', '#F8F8F4'   # v14: тёмный асфальт
PLAZA_V19 = '#D9D2C4'
PLAZA, PARK_LAWN, PARK_PATH = '#F1E9D6', '#CFE0B5', '#E9DFC6'
WATER, WALL, PROM, SAND = '#8FC3D9', '#B9B09C', '#EDE6D3', '#F1E2B3'
WALKUP_COLS = ('#C47A66', '#B5654F', '#5FA8A8', '#7FA372', '#D9B65E', '#DB9A92', '#A87A5A', '#D7C7A6',
               '#8FA9C2', '#C9876F', '#6FB0A0', '#B88A5A')


# ------------------------------------------------------------------ svg helpers
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


def group(gid, items):
    return ['<g id="%s">' % gid] + items + ['</g>']


# ------------------------------------------------------------------ geometry
def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1])


def vmul(a, k):
    return (a[0] * k, a[1] * k)


def vlen(a):
    return math.hypot(a[0], a[1])


def vunit(a):
    l = vlen(a) or 1.0
    return (a[0] / l, a[1] / l)


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def vcross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def ang_of(u):
    return math.degrees(math.atan2(u[1], u[0]))


def clip_half(pl, p, d, keep):
    """Часть выпуклого многоугольника по ту сторону прямой (p, d), где лежит точка keep."""
    s = 1.0 if vcross(d, vsub(keep, p)) >= 0 else -1.0
    out = []
    n = len(pl)
    for i in range(n):
        a, b = pl[i], pl[(i + 1) % n]
        da, db = s * vcross(d, vsub(a, p)), s * vcross(d, vsub(b, p))
        if da >= 0:
            out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out


def centroid(pl):
    return (sum(p[0] for p in pl) / len(pl), sum(p[1] for p in pl) / len(pl))


def parea(pl):
    if len(pl) < 3:
        return 0.0
    return abs(sum(pl[i][0] * pl[(i + 1) % len(pl)][1] - pl[(i + 1) % len(pl)][0] * pl[i][1]
                   for i in range(len(pl)))) / 2.0


def clip_convex(subj, clip):
    out = subj
    c = centroid(clip)
    for i in range(len(clip)):
        if len(out) < 3:
            return []
        a, b = clip[i], clip[(i + 1) % len(clip)]
        out = clip_half(out, a, vsub(b, a), c)
    return out


def inter_area(a, b):
    return parea(clip_convex(a, b))


def inside(pt, pl):
    s = None
    for i in range(len(pl)):
        a, b = pl[i], pl[(i + 1) % len(pl)]
        c = vcross(vsub(b, a), vsub(pt, a))
        if abs(c) < 1e-9:
            continue
        if s is None:
            s = c > 0
        elif s != (c > 0):
            return False
    return True


def seg_dist(p, a, b):
    d = vsub(b, a)
    L2 = vdot(d, d) or 1.0
    t = max(0.0, min(1.0, vdot(vsub(p, a), d) / L2))
    return vlen(vsub(p, vadd(a, vmul(d, t))))


def seg_inter(a, b, c, d):
    r, s = vsub(b, a), vsub(d, c)
    den = vcross(r, s)
    if abs(den) < 1e-9:
        return None
    t = vcross(vsub(c, a), s) / den
    u = vcross(vsub(c, a), r) / den
    if -1e-6 <= t <= 1 + 1e-6 and -1e-6 <= u <= 1 + 1e-6:
        return vadd(a, vmul(r, t))
    return None


def offset_pl(pl, d):
    """Смещение ломаной на d (влево по ходу, в экранных координатах — к «верхней» стороне при движении вправо)."""
    out = []
    for i, p in enumerate(pl):
        ns = []
        if i > 0:
            u = vunit(vsub(p, pl[i - 1]))
            ns.append((u[1], -u[0]))
        if i < len(pl) - 1:
            u = vunit(vsub(pl[i + 1], p))
            ns.append((u[1], -u[0]))
        n = vunit((sum(x[0] for x in ns), sum(x[1] for x in ns)))
        k = d / max(0.5, vdot(n, ns[0]))
        out.append(vadd(p, vmul(n, k)))
    return out



class St(object):
    def __init__(self, pts_, road, sw, kind='street', cap='butt'):
        self.pts, self.road, self.sw, self.kind, self.cap = pts_, road, sw, kind, cap

    @property
    def hw(self):
        return self.road / 2.0 + self.sw



# ---- STREETS ----
# ---- STREETS ----
AXIS = 1170
ROAD, SW = 60.0, 25.0                                              # v28: 12 м + 2 × 5 м (было 42.5, 20.0)
ROAD_OLD, SW_OLD = 42.5, 20.0
ST = {
    # кольцо с заломами (край города) — как в v20
    'N1': St([(100, 150), (445, 150)], ROAD, SW, cap='square'),
    'N2': St([(445, 70), (1170, 70)], ROAD, SW, cap='square'),
    'Nj': St([(1170, 70), (1170, 150)], ROAD, SW, cap='square'),
    'N3': St([(1170, 150), (1840, 150), (1840, 330), (2240, 330)], ROAD, SW, cap='square'),
    'W1': St([(100, 150), (100, 760)], ROAD, SW, cap='square'),
    'W2': St([(20, 760), (20, 1210)], ROAD, SW, cap='square'),
    'E1': St([(2240, 330), (2240, 760)], ROAD, SW, cap='square'),
    'E2': St([(2320, 760), (2320, 1210)], ROAD, SW, cap='square'),
    'S1': St([(20, 1210), (2320, 1210)], ROAD, SW, cap='square'),     # v27: одна прямая набережная вдоль пляжа
    'B': St([(20, 760), (790, 760), (790, 860), (1550, 860), (1550, 760), (2320, 760)], ROAD, SW, cap='square'),   # v30: без отростков за кольцо
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
    'Vs2': St([(900, 860), (900, 1210)], ROAD, SW, cap='square'),
    'AX': St([(AXIS, 860), (AXIS, 1210)], ROAD, SW, cap='square'),
    'Vs3': St([(1505, 1030), (1505, 1210)], ROAD, SW, cap='square'),   # v28: от Hse (у бульвара — дом)
    'Vd': St([(1840, 150), (1840, 760)], ROAD, SW, cap='square'),      # v28: до бульвара (дальше дом)
    'Vds': St([(1840, 960), (1840, H)], ROAD, SW),                     # v28: от Hse2 к пляжу
    'Hsw': St([(20, 990), (620, 990)], ROAD, SW, cap='square'),
    'Hse': St([(AXIS, 1030), (1840, 1030)], ROAD, SW, cap='square'),
    'Hse2': St([(1840, 960), (2320, 960)], ROAD, SW, cap='square'),
}
CANAL = [(XMIN, 1342), (800, 1336), (1600, 1340), (XMAX, 1348)]
DISTRICT = [(100, 150), (445, 150), (445, 70), (1170, 70), (1170, 150), (1840, 150), (1840, 330), (2240, 330),
            (2240, 760), (2320, 760), (2320, 1210), (20, 1210), (20, 760), (100, 760)]
RING = ('N1', 'N2', 'Nj', 'N3', 'W1', 'W2', 'E1', 'E2', 'S1')
def junctions():
    out = []
    names = list(ST)
    for i, n1 in enumerate(names):
        for n2 in names[i + 1:]:
            s1, s2 = ST[n1], ST[n2]
            for a, b in zip(s1.pts[:-1], s1.pts[1:]):
                for c, d in zip(s2.pts[:-1], s2.pts[1:]):
                    p = seg_inter(a, b, c, d)
                    if p is None:
                        continue
                    for j in out:
                        if vlen(vsub(j[0], p)) < 3:
                            j[1].update((n1, n2))
                            break
                    else:
                        out.append((p, {n1, n2}))
    return out


JUN = junctions()


def R(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]



# ---- BLOCKS ----
# ---- BLOCKS ----
BLK = {
    'NW1': R(141, 191, 404, 414), 'NW2': R(141, 496, 404, 719),
    'NC1': R(486, 111, 749, 414), 'NC2': R(486, 496, 749, 719),
    'SQ': [(831, 111), (1129, 111), (1129, 191), (1509, 191), (1509, 814), (831, 814)],
    'NE1': R(1591, 191, 1799, 414), 'NE2': R(1591, 496, 1799, 719),
    'Ea1': R(1881, 371, 2199, 504), 'Ea2': R(1881, 586, 2199, 719),
    'SW1': R(61, 801, 279, 949), 'SW2': R(361, 801, 579, 949),
    'SW3': R(61, 1031, 279, 1169), 'SW4': R(361, 1031, 579, 1169),
    'SC1': [(661, 801), (749, 801), (749, 901), (859, 901), (859, 1169), (661, 1169)],
    'SC2': R(941, 901, 1129, 1169),
    'SE1': R(1211, 901, 1464, 989),
    'SE2': [(1546, 901), (1591, 901), (1591, 801), (1799, 801), (1799, 989), (1546, 989)],
    'SE3': R(1211, 1071, 1464, 1169), 'SE4': R(1546, 1071, 1799, 1169),
    'Eb': R(1881, 801, 2279, 919), 'Ec': R(1881, 1001, 2279, 1169),
    'NEX': R(1881, 105, 2150, 289),
    'OB1': R(1211, 12, 1450, 109), 'OB2': R(-70, 616, -21, 719), 'OB3': R(2361, 616, 2420, 719),
}
# v28: кварталы ужаты на разницу полуширин улиц; содержимое квартала сжимается к новому контуру
SHRINK = (ROAD / 2.0 + SW) - (ROAD_OLD / 2.0 + SW_OLD)
BBOX_OLD = []
for _pl in BLK.values():
    _xs, _ys = [p[0] for p in _pl], [p[1] for p in _pl]
    BBOX_OLD.append((min(_xs), min(_ys), max(_xs), max(_ys)))


def _blk_of(p):
    x, y = p
    for b in BBOX_OLD:
        if b[0] - 0.5 <= x <= b[2] + 0.5 and b[1] - 0.5 <= y <= b[3] + 0.5:
            return b
    return None


def _map_in(b, p):
    x0, y0, x1, y1 = b
    d = SHRINK
    return (x0 + d + (p[0] - x0) * (x1 - x0 - 2 * d) / (x1 - x0), y0 + d + (p[1] - y0) * (y1 - y0 - 2 * d) / (y1 - y0))


def MP(p):
    b = _blk_of(p)
    return _map_in(b, p) if b else (p[0], p[1])


def MPP(pl):
    """Вся фигура — по одному кварталу (пожарные лестницы, тени и козырьки у фасада не растягиваются)."""
    b = next((q for q in map(_blk_of, pl) if q), None)
    return [_map_in(b, p) for p in pl] if b else list(pl)


BLK = {k: [MP(p) for p in pl] for k, pl in BLK.items()}
# ------------------------------------------------------------------ формы
def bbox(pl):
    xs = [p[0] for p in pl]
    ys = [p[1] for p in pl]
    return min(xs), min(ys), max(xs), max(ys)


def arc_pts(c, r, a0, a1, n):
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / float(n))),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / float(n)))) for i in range(n + 1)]


def rrect(x0, y0, x1, y1, r, n=6):
    return (arc_pts((x1 - r, y0 + r), r, -90, 0, n) + arc_pts((x1 - r, y1 - r), r, 0, 90, n) +
            arc_pts((x0 + r, y1 - r), r, 90, 180, n) + arc_pts((x0 + r, y0 + r), r, 180, 270, n))


def rect_rc(x0, y0, x1, y1, corner, r, n=10):
    if corner == 'NE':
        return [(x0, y0)] + arc_pts((x1 - r, y0 + r), r, -90, 0, n) + [(x1, y1), (x0, y1)]
    if corner == 'SE':
        return [(x0, y0), (x1, y0)] + arc_pts((x1 - r, y1 - r), r, 0, 90, n) + [(x0, y1)]
    if corner == 'SW':
        return [(x0, y0), (x1, y0), (x1, y1)] + arc_pts((x0 + r, y1 - r), r, 90, 180, n)
    return arc_pts((x0 + r, y0 + r), r, 180, 270, n) + [(x1, y0), (x1, y1), (x0, y1)]


def lshape(x0, y0, x1, y1, th, tv, corner):
    if corner == 'NW':
        return [(x0, y0), (x1, y0), (x1, y0 + th), (x0 + tv, y0 + th), (x0 + tv, y1), (x0, y1)]
    if corner == 'NE':
        return [(x0, y0), (x1, y0), (x1, y1), (x1 - tv, y1), (x1 - tv, y0 + th), (x0, y0 + th)]
    if corner == 'SW':
        return [(x0, y0), (x0 + tv, y0), (x0 + tv, y1 - th), (x1, y1 - th), (x1, y1), (x0, y1)]
    return [(x1 - tv, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y1 - th), (x1 - tv, y1 - th)]


def ushape_e(x0, y0, x1, y1, t):
    return [(x0, y0), (x1, y0), (x1, y0 + t), (x0 + t, y0 + t), (x0 + t, y1 - t), (x1, y1 - t), (x1, y1), (x0, y1)]


def catmull(ctrl, closed, n=10):
    out = []
    m = len(ctrl)
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = ctrl[(i - 1) % m] if closed or i > 0 else ctrl[0]
        p1, p2 = ctrl[i], ctrl[(i + 1) % m]
        p3 = ctrl[(i + 2) % m] if closed or i + 2 < m else ctrl[-1]
        for k in range(n):
            t = k / float(n)
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    if not closed:
        out.append(ctrl[-1])
    return out


def organic(c, rx, ry, seed, k=9, amp=0.12):
    r2 = random.Random(seed)
    ctrl = []
    for i in range(k):
        a = 2 * math.pi * i / k
        f_ = 1 + r2.uniform(-amp, amp)
        ctrl.append((c[0] + rx * f_ * math.cos(a), c[1] + ry * f_ * math.sin(a)))
    return catmull(ctrl, True, 8)


# ------------------------------------------------------------------ содержимое кварталов
BLD, SPEC, LOTS, PAVE0, PAVE, LAWNS, NUMS, TREES, BENCH, LAMPS, BLUE = [], [], [], [], [], [], [], [], [], [], []
AREA = {'bld': 0.0, 'park': 0.0, 'square': 0.0}
PARK_SHAPES = []


def num(label, c):
    NUMS.append((label, c))


SHADOW = []


def bld(pl, fill, stroke='#5B4B43', sw=1.1, count=True, h=10):
    """h — условная высота: тень на юго-восток длиной по высоте (кирпичные дома короткая, башни длинная)."""
    SHADOW.append(poly([(x + h * 0.55, y + h * 0.75) for x, y in pl], '#2E3A40', 'none', 0, ' fill-opacity="0.16"'))
    BLD.append(poly(pl, fill, stroke, sw))
    if count:
        AREA['bld'] += parea(pl)
    return pl


def row(items):
    """Рядок узких домов вплотную: [(x0, y0, x1, y1, цвет)]."""
    for x0, y0, x1, y1, col in items:
        bld(R(x0, y0, x1, y1), col)


def fire_escape(p0, p1, o):
    u = vunit(vsub(p1, p0))
    SPEC.append(poly([p0, p1, vadd(p1, vmul(o, 3.6)), vadd(p0, vmul(o, 3.6))], '#3D4246'))
    L = vlen(vsub(p1, p0))
    k = 3.0
    while k < L - 1:
        q = vadd(p0, vmul(u, k))
        SPEC.append(line([q, vadd(q, vmul(o, 3.6))], '#8C9398', 0.6, 'butt'))
        k += 4


def water_tower(c):
    SPEC.append(circle(c, 5.5, '#8B6B4A', '#4A3A2C', 1))
    SPEC.append(circle(c, 2.2, '#A58560'))


def stall_lines(x0, x1, y0, y1, step=14, vertical=True):
    if vertical:
        x = x0
        while x <= x1:
            LOTS.append(line([(x, y0), (x, y1)], '#F4F4F0', 0.8, 'butt'))
            x += step
    else:
        y = y0
        while y <= y1:
            LOTS.append(line([(x0, y), (x1, y)], '#F4F4F0', 0.8, 'butt'))
            y += step


def park(blob, paths, width=18, pond=None, label=None, at=None, trees=8, seed=1):
    LAWNS.append(poly(blob, PARK_LAWN, '#A9C08C', 1))
    AREA['park'] += parea(blob)
    segs = []
    for ctrl, closed in paths:
        pl = catmull(ctrl, closed, 10)
        if closed:
            pl = pl + [pl[0]]
        PAVE.append(line(pl, PARK_PATH, width, 'round'))
        segs += list(zip(pl[:-1], pl[1:]))
    if pond:
        PAVE.append(poly(pond, WATER, '#6FA6C0', 1))
    x0, y0, x1, y1 = bbox(blob)
    r2 = random.Random(seed)
    placed = []
    for _ in range(400):
        p = (r2.uniform(x0 + 8, x1 - 8), r2.uniform(y0 + 8, y1 - 8))
        if not inside_poly(p, blob) or any(seg_dist(p, a, b) < width / 2.0 + 14 for a, b in segs):
            continue
        if pond and inside_poly(p, pond):
            continue
        if any(vlen(vsub(p, q)) < 30 for q in placed) or any(vlen(vsub(p, q)) < 24 for q, _ in TREES):
            continue
        placed.append(p)
        if len(placed) >= trees:
            break
    for p in placed:
        TREES.append((p, 10))
    if label:
        num(label, at)


def inside_poly(pt, pl):
    """Точка внутри любого многоугольника (чётно-нечётно)."""
    x, y = pt
    c = False
    n = len(pl)
    for i in range(n):
        x0, y0 = pl[i]
        x1, y1 = pl[(i + 1) % n]
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / ((y1 - y0) or 1e-9) + x0:
            c = not c
    return c


def fillet(pl, r, n=4):
    """Скругляет углы многоугольника радиусом до r — сквер заполняет участок целиком, без острых углов."""
    out = []
    m = len(pl)
    for i in range(m):
        p, a, b = pl[i], pl[i - 1], pl[(i + 1) % m]
        rr_ = min(r, vlen(vsub(a, p)) / 2.0, vlen(vsub(b, p)) / 2.0)
        q1 = vadd(p, vmul(vunit(vsub(a, p)), rr_))
        q2 = vadd(p, vmul(vunit(vsub(b, p)), rr_))
        for k in range(n + 1):
            t = k / float(n)
            out.append(((1 - t) ** 2 * q1[0] + 2 * (1 - t) * t * p[0] + t * t * q2[0],
                        (1 - t) ** 2 * q1[1] + 2 * (1 - t) * t * p[1] + t * t * q2[1]))
    return out


def ramp(x0, x1, y0, y1, down):
    """Съезд в подземный паркинг: тёмная полоса со стрелками (вниз — въезд, вверх — выезд)."""
    SPEC.append(poly(R(x0, y0, x1, y1), '#6E757A', '#3E4347', 1))
    xm = (x0 + x1) / 2.0
    for y in (y0 + 14, y0 + 30, y0 + 46):
        if down:
            SPEC.append(line([(x0 + 6, y), (xm, y + 8), (x1 - 6, y)], '#D7DCDF', 1.4, 'butt'))
        else:
            SPEC.append(line([(x0 + 6, y + 8), (xm, y), (x1 - 6, y + 8)], '#D7DCDF', 1.4, 'butt'))


# ------------------------------------------------------------------ v13: здания как в референсах Вадима
# Не пёстрые рядки узких домов вплотную, а разные крупные дома: кирпичные и бежевые 6–10 этажей со световыми
# колодцами, круглая стеклянная башня на углу, каменное здание с колоннадой, кирпичный лофт с зубчатой крышей,
# стеклянные офисы. Узкие дома остались короткими группами по 2–3, в спокойной кирпично-бежевой гамме.
PAL = {'brick': '#A9583F', 'brick2': '#B9714F', 'dark': '#8A4B3B', 'tan': '#C9A57A', 'beige': '#D8C4A0',
       'cream': '#E4D8BF', 'stone': '#CBC7BD', 'teal': '#5F8F8B', 'green': '#6F8C68'}


def shade(col, k):
    c = col.lstrip('#')
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    if k < 0:
        r, g, b = [int(v * (1 + k)) for v in (r, g, b)]
    else:
        r, g, b = [int(v + (255 - v) * k) for v in (r, g, b)]
    return '#%02X%02X%02X' % (r, g, b)


def parapet(pl, col):
    """Парапет по краю крыши: линия чуть внутри контура дома."""
    c = centroid(pl)
    inner = [vadd(p, vmul(vunit(vsub(c, p)), 5)) for p in pl]
    SPEC.append(poly(inner, 'none', shade(col, -0.25), 0.9))


def house(x0, y0, x1, y1, col, tower=None, well=None, boxes=(), h=None):
    """Дом сверху: крыша с парапетом, надстройки (выходы на крышу, вентиляция), световой колодец, водонапорный бак."""
    if h is None:                                                   # крупные дома выше узких
        h = 18 if (x1 - x0) * (y1 - y0) > 9000 else 12
    pl = bld(R(x0, y0, x1, y1), col, h=h)
    parapet(pl, col)
    if well:
        SPEC.append(rect(well[0], well[1], well[2], well[3], '#D9D4C5', shade(col, -0.4), 1))
    for bx in boxes:
        SPEC.append(rect(bx[0], bx[1], bx[2], bx[3], shade(col, -0.2), shade(col, -0.42), 0.6))
    if tower:
        water_tower(tower)
    return pl


def shaped(pl, col, tower=None, h=14):
    bld(pl, col, h=h)
    parapet(pl, col)
    if tower:
        water_tower(tower)


def glass_round(c, r, podium):
    """Круглая стеклянная башня на стеклянном подиуме — как на угловом референсе."""
    bld(podium, '#A7BED2', '#4A6C8C', 1.2, h=8)
    bld(arc_pts(c, r, 0, 360, 40), '#3F6C99', '#1F3E5E', 1.8, count=False, h=46)
    for k in (0.78, 0.56):
        SPEC.append(poly(arc_pts(c, r * k, 0, 360, 32), 'none', '#86ADD2', 1))
    SPEC.append(circle(c, r * 0.3, '#B3CDE5', '#5F82A6', 0.8))


def glass_office(pl):
    """Стеклянный офис: синяя крыша с сеткой (сетка не выходит за скруглённый угол)."""
    bld(pl, '#4C78A3', '#22405F', 1.6, h=30)
    x0, y0, x1, y1 = bbox(pl)
    x = x0 + 14
    while x < x1 - 8:
        seg = [(x, y0 + 6), (x, y1 - 6)]
        if inside_poly((x, y0 + 8), pl) and inside_poly((x, y1 - 8), pl):
            SPEC.append(line(seg, '#86ADD2', 0.8, 'butt'))
        x += 16
    y = y0 + 14
    while y < y1 - 8:
        if inside_poly((x0 + 8, y), pl) and inside_poly((x1 - 8, y), pl):
            SPEC.append(line([(x0 + 6, y), (x1 - 6, y)], '#86ADD2', 0.8, 'butt'))
        y += 16


def classical(x0, y0, x1, y1, front='N'):
    """Каменное здание с колоннадой вдоль фасада и световым фонарём посередине (банк/библиотека)."""
    pl = bld(R(x0, y0, x1, y1), '#E2DCCC', '#6E6A60', 1.6, h=14)
    parapet(pl, '#CFC8B6')
    yc = y0 + 10 if front == 'N' else y1 - 10
    SPEC.append(rect(x0 + 6, yc - 6, x1 - 6, yc + 6, '#EEEBE2', '#A59E8C', 0.8))
    x = x0 + 16
    while x < x1 - 10:
        SPEC.append(circle((x, yc), 3, '#F8F6EF', '#8E8676', 0.8))
        x += 14
    c = ((x0 + x1) / 2.0, (y0 + y1) / 2.0 + (6 if front == 'N' else -6))
    SPEC.append(circle(c, 20, '#D5CEBB', '#8E8676', 1))
    SPEC.append(circle(c, 8, '#E9E4D6', '#8E8676', 0.8))


def billboard(x0, y0, x1, y1):
    """Рекламный щит на крыше (как «Rodman is watching» на референсах)."""
    SPEC.append(rect(x0, y0, x1, y1, '#2F3A40', '#1A2024', 0.6))
    SPEC.append(rect(x0 + 2, y0 + 1.5, x1 - 2, y1 - 1.5, 'none', '#DCE3E6', 0.6))


def loft(x0, y0, x1, y1, col):
    """Кирпичный лофт (бывший склад) с зубчатой крышей — светлые полосы фонарей."""
    pl = bld(R(x0, y0, x1, y1), col, h=11)
    parapet(pl, col)
    x = x0 + 12
    while x < x1 - 8:
        SPEC.append(line([(x, y0 + 8), (x, y1 - 8)], '#C9A58F', 2.2, 'butt'))
        x += 16



# ---- CITY ----
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


def us_block(x0, y0, x1, y1, horiz=None, plug=True, single=None):
    """Американский квартал: дома спиной к спине на всю глубину, посередине служебный переулок вдоль длинной
    стороны; затычка-дом посередине делает из него два глухих переулка, по одному с каждой улицы."""
    if horiz is None:
        horiz = (x1 - x0) >= (y1 - y0)
    if single:                                                       # v29: одинарный глухой переулок — один въезд, стена у дальнего конца
        if horiz:
            ym = (y0 + y1) / 2.0
            rowfill(x0, y0, x1, ym - 14, 'N')
            rowfill(x0, ym + 14, x1, y1, 'S', corners=False)
            if single == 'W':
                alley(R(x0, ym - 14, x1 - 34, ym + 14), dead=[(x1 - 34, ym - 16), (x1 - 34, ym + 16)])
                house(x1 - 34, ym - 14, x1, ym + 14, '#8C6A4F', h=8)
                ALLEY_DW.append(R(x0 - 21, ym - 14, x0, ym + 14))
            else:
                alley(R(x0 + 34, ym - 14, x1, ym + 14), dead=[(x0 + 34, ym - 16), (x0 + 34, ym + 16)])
                house(x0, ym - 14, x0 + 34, ym + 14, '#8C6A4F', h=8)
                ALLEY_DW.append(R(x1, ym - 14, x1 + 21, ym + 14))
        else:
            xm = (x0 + x1) / 2.0
            rowfill(x0, y0, xm - 14, y1, 'W')
            rowfill(xm + 14, y0, x1, y1, 'E', corners=False)
            if single == 'N':
                alley(R(xm - 14, y0, xm + 14, y1 - 34), dead=[(xm - 16, y1 - 34), (xm + 16, y1 - 34)])
                house(xm - 14, y1 - 34, xm + 14, y1, '#8C6A4F', h=8)
                ALLEY_DW.append(R(xm - 14, y0 - 21, xm + 14, y0))
            else:
                alley(R(xm - 14, y0 + 34, xm + 14, y1), dead=[(xm - 16, y0 + 34), (xm + 16, y0 + 34)])
                house(xm - 14, y0, xm + 14, y0 + 34, '#8C6A4F', h=8)
                ALLEY_DW.append(R(xm - 14, y1, xm + 14, y1 + 21))
        return
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


def ramp2(x0, x1, y0, y1):
    """Рампа в подземный паркинг, двусторонняя: стрелки вниз и вверх."""
    SPEC.append(poly(R(x0, y0, x1, y1), '#6E757A', '#3E4347', 1))
    xm = (x0 + x1) / 2.0
    SPEC.append(line([(xm, y0 + 4), (xm, y1 - 4)], '#D7DCDF', 1, 'butt', ' stroke-dasharray="4 3"'))
    for y in (y0 + 12, y0 + 34):
        SPEC.append(line([(x0 + 4, y), ((x0 + xm) / 2.0, y + 6), (xm - 2, y)], '#D7DCDF', 1.3, 'butt'))
        SPEC.append(line([(xm + 2, y + 6), ((xm + x1) / 2.0, y), (x1 - 4, y + 6)], '#D7DCDF', 1.3, 'butt'))


def service_yard(pl, garage, bins, opening, label=None, at=None):
    """Широкий хозяйственный двор (не подворотня): бетон, баки, гаражные ворота-рольставня, болларды; въезд с улицы."""
    PAVE.append(poly(pl, '#D8D4CA', '#A9A498', 1))
    gx0, gy0, gx1, gy1 = garage
    SPEC.append(rect(gx0, gy0, gx1, gy1, '#4E5559', '#2E3236', 0.8))
    for bx, by in bins:
        SPEC.append(rect(bx, by, bx + 13, by + 9, '#4E6B52', '#2F4532', 0.6))
    for p in opening[1:]:
        SPEC.append(circle(p, 2, '#E3B71E', '#7A6210', 0.6))
    ALLEY_DW.append(opening[0])
    if label:
        num(label, at)


def make_city():
    # ---- v19: площадь «Водная ось» (концепт REF_downtown_plaza_water_axis_v01), площадь глубже: 136×100 м
    # 01, 02 круглые башни-близнецы на общем стеклянном подиуме; экран между ними; 03 подземный паркинг, 2 рампы
    PAVE0.append(poly(BLK['SQ'], PLAZA_V19))
    bld(rrect(880, 196, 1460, 300, 18), '#B7C7D4', '#4F6E8C', 1.2, h=8)         # общий стеклянный подиум
    for cx in (1005, 1335):
        ring = arc_pts((cx, 246), 54, 0, 360, 16)
        bld(ring, '#2E4E73', '#16293F', 1.8, count=False, h=70)
        for k in (0.72, 0.46):
            BLD.append(poly(arc_pts((cx, 246), 54 * k, 0, 360, 16), 'none', '#6F93BA', 1))
        BLD.append(circle((cx, 246), 8, '#9FB8D2', '#4F6E8C', 0.8))
    num('01', (1005, 246))
    num('02', (1335, 246))
    SPEC.append(rect(1100, 288, 1240, 300, '#1E2A36', '#0E151C', 1))           # большой экран на подиуме
    SPEC.append(rect(1104, 290, 1236, 297, '#5FA8D8'))
    num('35', (1170, 276))
    SPEC.append(poly(rrect(840, 192, 1500, 304, 14), 'none', '#2F3A42', 1.4, ' stroke-dasharray="8 5"'))
    house(895, 118, 1120, 186, '#A9A69C', h=6)
    ramp2(846, 886, 111, 192)
    ramp2(1460, 1500, 191, 250)
    num('03', (866, 222))
    sq = (831, 300, 1509, 814)
    AREA['square'] = (sq[2] - sq[0]) * (sq[3] - sq[1])
    # спуск с подиума: широкая лестница, по центру каскад воды
    for k in range(5):
        PAVE.append(line([(900, 304 + k * 6), (1440, 304 + k * 6)], '#CFC6B4', 1.4, 'butt'))
    PAVE.append(rect(1146, 300, 1194, 334, '#7FB3D0', '#4F7E99', 1))
    for k in range(4):
        PAVE.append(line([(1148, 306 + k * 7), (1192, 306 + k * 7)], '#D8ECF5', 1.2, 'butt'))
    # длинный зеркальный бассейн по оси, тёмная каменная полоса вокруг
    PAVE.append(rect(1124, 330, 1216, 640, '#8A8378'))
    PAVE.append(rect(1130, 336, 1210, 634, '#7FB3D0', '#4F7E99', 1))
    # памятник Трамдуро у бульвара: тёмный подиум, кольцо сухих фонтанов в плитке
    S_ = (AXIS, 722)
    PAVE.append(circle(S_, 64, '#8A8378'))
    PAVE.append(circle(S_, 60, PLAZA_V19))
    for a in range(0, 360, 20):
        p = (S_[0] + 46 * math.cos(math.radians(a)), S_[1] + 46 * math.sin(math.radians(a)))
        SPEC.append(circle(p, 3, '#DDEFF5', '#6FA6C0', 0.8))
    SPEC.append(circle(S_, 22, '#3C3E42', '#1E2024', 1.2))
    SPEC.append(circle(S_, 12, '#D9B13B', '#8A6A1A', 1.2))
    num('15', (S_[0] + 80, S_[1] + 10))
    SPEC.append(rect(1252, 700, 1268, 716, '#5B6E8C', '#2E3C52', 0.8))         # полицейская будка
    num('36', (1282, 690))
    SPEC.append(poly(rr((1110, 670), 10, 14, 0), '#2F5D8A', '#1E3F60', 0.8))   # ATM
    num('08', (1092, 656))
    # 4 стеклянных павильона с террасами под зонтиками (вместо Г-образных магазинов)
    for lab, (x0, y0, x1, y1), tx in (('16', (861, 420, 951, 470), 960), ('17', (1389, 420, 1479, 470), 1344),
                                      ('18', (861, 610, 951, 660), 960), ('19', (1389, 610, 1479, 660), 1344)):
        pl = bld(R(x0, y0, x1, y1), '#A9C4D3', '#4F6E8C', 1.3, h=5)
        AREA['square'] -= parea(pl)
        SPEC.append(rect(x0 + 6, y0 + 6, x1 - 6, y1 - 6, 'none', '#E8F1F6', 0.8))
        num(lab, ((x0 + x1) / 2.0, (y0 + y1) / 2.0))
        for k in range(3):
            SPEC.append(circle((tx + 6, y0 + 8 + k * 17), 7, '#E9D37A', '#A88E3A', 0.8))   # зонтики
    # круглые скамейки с клумбами, флаги, фонари; без деревьев
    for p in ((1060, 400), (1280, 400), (1060, 520), (1280, 520), (1060, 620), (1280, 620)):
        SPEC.append(circle(p, 13, '#B07A4A', '#6E4A2A', 1))
        SPEC.append(circle(p, 8, '#C98FB0', '#7E8F5E', 1))
    for y in (360, 430, 500, 570):
        for x in (1100, 1240):
            SPEC.append(circle((x, y), 2.2, '#2F3A42'))
            SPEC.append(rect(x + 2, y - 4, x + 9, y + 1, '#3E6FB0'))
    for p in ((900, 340), (1440, 340), (900, 780), (1440, 780), (1020, 740), (1320, 740)):
        LAMPS.append(p)
    for x in range(845, 1500, 24):                                              # болларды вдоль бульвара
        SPEC.append(circle((x, 806), 2.2, '#3C3E42'))
    for x0 in (1010, 1290):                                                     # фудтраки у южного края
        SPEC.append(rect(x0, 760, x0 + 34, 776, '#C8503F', '#7A2A20', 0.8))
    num('04', (880, 560))
    SPEC.append(poly(rr((1420, 838), 40, 7, 0), '#9AA7B0', '#5E6A72', 0.8))   # остановка
    num('14', (1470, 840))
    # ---- северо-запад: 4 американских квартала; 23 маленький сквер на месте половины квартала
    us_block(141, 191, 404, 414, single='E')                                       # v29: одинарный переулок с улицы Vn
    rowfill(141, 496, 260, 719, 'W')
    park(fillet(R(260, 496, 404, 719), 12), [([(260, 600), (330, 590), (404, 610)], False)], 14,
         label='23', at=(330, 650), trees=4, seed=23)
    us_block(486, 111, 749, 414, horiz=False)
    # 42 широкий двор: въезд с улицы Vb, баки, гаражные ворота
    rowfill(486, 496, 749, 560, 'N')
    rowfill(486, 655, 749, 719, 'S', corners=False)
    rowfill(486, 560, 546, 655, 'W', corners=False)
    service_yard(R(546, 560, 749, 655), (546, 585, 552, 625), ((580, 562), (596, 562), (700, 644)),
                 (R(749, 572, 770, 643), (744, 570), (744, 645)), '42', (640, 608))
    # ---- северо-восток: круглая стеклянная башня на углу; парковка-пустырь; полиция 2 + такси; сквер с прудом
    glass_round((1750, 245), 46, R(1700, 191, 1799, 300))
    rowfill(1591, 191, 1700, 255, 'N')
    rowfill(1591, 255, 1655, 414, 'W')
    rowfill(1655, 350, 1799, 414, 'S', corners=False)
    # 43 широкий двор справа сверху: внутренний двор квартала открыт на улицу Vd
    service_yard([(1655, 255), (1700, 255), (1700, 300), (1799, 300), (1799, 350), (1655, 350)], (1655, 270, 1661, 310),
                 ((1668, 336), (1684, 336), (1672, 262)), (R(1799, 306, 1820, 346), (1795, 304), (1795, 348)), '43', (1740, 325))
    rowfill(1591, 496, 1799, 590, 'N')
    rowfill(1591, 590, 1799, 719, 'S')                                             # v29: вместо парковки P — дома
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
    us_block(361, 801, 579, 949, single='W')                                       # v29: вместо пустыря — квартал, одинарный переулок с Vs1
    bld(R(71, 1041, 221, 1159), '#B9C8E6', INK, 2)
    BLD.append(circle((91, 1139), 28, '#B9C8E6', INK, 2))
    num('10', (150, 1095))
    rowfill(221, 1031, 279, 1169, 'E', corners=False)
    us_block(361, 1031, 579, 1169)
    # ---- юг центра: 07 магазин для бусика; 05 стеклянный офис; кварталы с переулками; каменное здание у набережной
    bld(R(661, 801, 749, 905), '#E3A982', INK, 1.8, h=9)                           # v29: 07 магазин для бусика — прямоугольный
    for y in (822, 862):
        SPEC.append(rect(743, y, 749, y + 26, '#4E5559', '#2E3236', 0.8))               # ворота-рольставни на улицу
    num('07', (705, 853))
    rowfill(661, 905, 749, 1169, 'W', corners=False)                                # два ряда спиной к спине, без переулка
    rowfill(749, 901, 859, 1169, 'E')
    glass_office(R(941, 901, 1129, 980))
    num('05', (1035, 940))
    rowfill(941, 980, 1129, 1070, 'N', corners=False)
    classical(941, 1076, 1129, 1169, 'S')                                           # каменное здание фасадом к набережной
    # ---- юго-восток: 06 офис; 40 дайнер на углу; лофт; кварталы с переулками
    glass_office(R(1211, 901, 1350, 989))
    num('06', (1280, 945))
    rowfill(1350, 901, 1464, 989, 'N')
    rowfill(1591, 801, 1799, 895, 'N')                                             # v29: без переулка — его конец упёрся бы в дома на месте Vd
    rowfill(1591, 895, 1799, 989, 'S', corners=False)
    rowfill(1546, 901, 1591, 989, 'W', corners=False)
    bld(rrect(1211, 1071, 1300, 1125, 14), '#D7DDE1', '#5E6A72', 1.6, h=5)   # дайнер: хром, красная полоса
    SPEC.append(line([(1218, 1098), (1293, 1098)], '#C8372D', 3, 'butt'))
    num('40', (1255, 1145))
    rowfill(1300, 1071, 1464, 1169, 'S')
    rowfill(1211, 1125, 1300, 1169, 'S', corners=False)
    rowfill(1546, 1071, 1640, 1169, 'S')
    loft(1640, 1071, 1799, 1169, '#7E4436')
    # ---- восток: квартал с переулками; 13 база по референсу REF_downtown_base_courtyard_v03_arch:
    #      с улицы — арка-проезд под домом, за ней закрытый со всех сторон бетонный дворик, в торце
    #      кирпичного гаража ворота-рольставня с козырьком; баки, поддоны, болларды, пожарная лестница соседа
    rowfill(1881, 801, 2279, 860, 'N')                                             # v29: без переулка — его конец упёрся бы в дома на месте Vd
    rowfill(1881, 860, 2279, 919, 'S', corners=False)
    rowfill(1881, 1001, 1960, 1089, 'N', corners=False)
    PAVE.append(poly([(2150, 1001), (2200, 1001), (2200, 1085), (2060, 1085), (2060, 1040), (2150, 1040)], '#D8D4CA', '#A9A498', 1))
    bld(R(1960, 1001, 2060, 1089), '#B8735A', INK, 2.2, h=12)                        # гараж базы (кирпич)
    SPEC.append(rect(2060, 1050, 2066, 1080, '#4E5559', '#2E3236', 0.8))            # рольставня в торце гаража
    SPEC.append(rect(2066, 1046, 2076, 1084, '#5E6468'))                            # козырёк над воротами
    house(2060, 1001, 2200, 1040, '#D9C9A8', h=13)                                  # дом с аркой-проездом во двор
    SPEC.append(poly(R(2150, 1001, 2200, 1040), 'none', '#6E6A60', 1.2, ' stroke-dasharray="4 3"'))   # арка под домом
    shaped(R(2200, 1001, 2279, 1089), '#A9B59A')
    fire_escape((2200, 1020), (2200, 1060), (-1, 0))                                # пожарная лестница соседа
    for bx in ((2084, 1072), (2100, 1072)):                                          # мусорные баки
        SPEC.append(rect(bx[0], bx[1], bx[0] + 13, bx[1] + 9, '#4E6B52', '#2F4532', 0.6))
    SPEC.append(rect(2185, 1062, 2196, 1074, '#B08D5E', '#6E5A3A', 0.6))            # поддоны
    for p in ((2072, 1044), (2072, 1086), (2156, 1004)):
        SPEC.append(circle(p, 2, '#E3B71E', '#7A6210', 0.6))                          # болларды
    SPEC.append(line([(2060, 1088), (2200, 1088)], '#8A4A36', 3, 'butt'))           # глухая стена двора со стороны S4
    ALLEY_DW.append(R(2150, 980, 2200, 1001))                                         # въезд через тротуар с Hse2
    num('13', (2120, 1062))
    rowfill(1881, 1095, 2279, 1169, 'S')                                            # ряд домов фасадом к набережной
def legs(name, j):
    s = ST[name]
    out = []
    for a, b in zip(s.pts[:-1], s.pts[1:]):
        if seg_dist(j, a, b) > 1.5:
            continue
        u = vunit(vsub(b, a))
        if vlen(vsub(b, j)) > 1.5:
            out.append((u, vlen(vsub(b, j))))
        if vlen(vsub(j, a)) > 1.5:
            out.append(((-u[0], -u[1]), vlen(vsub(j, a))))
    uniq = []
    for v, L in out:
        if all(vdot(v, w) < 0.995 for w, _ in uniq):
            uniq.append((v, L))
    return uniq


def cross_dist(name, j, v, names, extra):
    best = 0.0
    for m in names:
        if m == name:
            continue
        for w, _ in legs(m, j):
            sn = abs(vcross(v, w))
            if sn > 0.2:
                best = max(best, (ST[m].road / 2.0 + extra(ST[m])) / sn)
    return best



def hydrants(out):
    for j, names in JUN:
        if len(names) < 2:
            continue
        ns = sorted(names, key=lambda m: -ST[m].road)[:2]
        s, t = ST[ns[0]], ST[ns[1]]
        us, ut = legs(ns[0], j)[0][0], legs(ns[1], j)[0][0]
        sn = abs(vcross(us, ut)) or 1.0
        sg = 1 if rnd.random() < 0.5 else -1
        q = vadd(j, vadd(vmul(us, sg * (t.road / 2.0 + t.sw * 0.6) / sn), vmul(ut, -sg * (s.road / 2.0 + s.sw * 0.6) / sn)))
        if not any(inside(q, pl) for pl in BLK.values()):
            out.append(circle(q, 3, '#D9443B', '#8A2A24', 0.7))


def scatter_trees(trs, n, box, avoid):
    k = tries = 0
    while k < n and tries < n * 80:
        tries += 1
        p = (rnd.uniform(box[0], box[2]), rnd.uniform(box[1], box[3]))
        r = rnd.uniform(9, 13)
        if any(min(seg_dist(p, a, b) for a, b in zip(s.pts[:-1], s.pts[1:])) < s.hw + r + 3 for s in ST.values()):
            continue
        if any(inside(p, q) for q in avoid):
            continue
        trs.append(circle(p, r, '#C7D7B4', '#8FA37D', 1))
        k += 1




# ------------------------------------------------------------------ разметка, переходы, светофоры (v17)
def crossing_legs(j, names):
    """v23: зебры только там, где нужны: на перекрёстках с бульваром — поперёк боковых улиц; поперёк самого
    бульвара — только у площади (на углах Vb, Vc и на оси AX). Остальные перекрёстки без зебр."""
    if 'B' not in names:
        return []
    keep = []
    plaza = bool({'AX', 'Vb', 'Vc'} & set(names))
    for n in names:
        for v, L in legs(n, j):
            probe = vadd(j, vmul(v, 60))
            if not inside_poly(probe, DISTRICT) and n not in ('AX',):
                continue
            if n == 'B' and not plaza:
                continue
            keep.append((n, v, L))
    return keep


def crosswalks(out):
    for j, names in JUN:
        for name, v, L in crossing_legs(j, names):
            s = ST[name]
            dz = cross_dist(name, j, v, names, lambda t: t.sw * 0.5)
            if dz <= 0 or L < dz + 12:
                continue
            c = vadd(j, vmul(v, dz))
            nrm = (-v[1], v[0])
            k = -s.road / 2.0 + 4
            while k <= s.road / 2.0 - 3:
                out.append(poly(rr(vadd(c, vmul(nrm, k)), 16, 4, ang_of(v)), MARK))
                k += 7.5


def lights_and_stops(out):
    """Светофоры на штангах — на перекрёстках с бульваром и осью к площади; на остальных — знаки «стоп»."""
    for j, names in JUN:
        n_legs = len([1 for n in names for _ in legs(n, j)])
        if n_legs < 3:
            continue
        hw = max(ST[n].road / 2.0 + ST[n].sw for n in names) - 3
        main = 'B' in names or 'AX' in names
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = (j[0] + dx * hw, j[1] + dy * hw)
            if main:
                out.append(rect(p[0] - 3.2, p[1] - 3.2, p[0] + 3.2, p[1] + 3.2, '#2E3238', '#1A1D20', 0.6))
                out.append(circle(p, 1.6, '#F2C230'))
            elif (dx + dy) == 0:
                out.append(circle(p, 2.6, '#C8372D', '#7A1E18', 0.6))


def centre_dashes(out):
    for name, s in ST.items():
        for a, b in zip(s.pts[:-1], s.pts[1:]):
            u = vunit(vsub(b, a))
            L = vlen(vsub(b, a))
            zones = []
            for j, names in JUN:
                if name not in names or seg_dist(j, a, b) > 1.5:
                    continue
                t = vdot(vsub(j, a), u)
                r = max(cross_dist(name, j, u, names, lambda st: st.sw + 14),
                        cross_dist(name, j, (-u[0], -u[1]), names, lambda st: st.sw + 14))
                zones.append((t - r, t + r))
            zones.append((-30, 24))
            zones.append((L - 24, L + 30))
            k = 6.0
            while k < L - 4:
                k2 = min(L - 2, k + 12)
                if not any(z0 < k2 and k < z1 for z0, z1 in zones):
                    out.append(line([vadd(a, vmul(u, k)), vadd(a, vmul(u, k2))], MARK, 1.4, 'butt'))
                k += 24


DRIVEWAYS = [R(749, 820, 770, 890)]                              # v29: въезд к воротам 07 через тротуар



def render_png(svg, png, w, h):
    import subprocess
    chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    html = svg[:-4] + '_render.html'
    io.open(html, 'w', encoding='utf-8').write(
        '<html><head><meta charset="utf-8"></head><body style="margin:0">' + io.open(svg, encoding='utf-8').read() + '</body></html>')
    subprocess.run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--screenshot=' + png,
                    '--window-size=%d,%d' % (w, h), 'file:///' + html.replace('\\', '/')], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(html)
    return png


def make_city_v28():
    """make_city v27 с отображением координат в ужатые кварталы; затем дома на месте перекрытых улиц."""
    g = globals()
    orig = {k: g[k] for k in ('poly', 'line', 'circle', 'text')}
    g['poly'] = lambda p, *a, **k: orig['poly'](MPP(p), *a, **k)
    g['line'] = lambda p, *a, **k: orig['line'](MPP(p), *a, **k)
    g['circle'] = lambda c, *a, **k: orig['circle'](MP(c), *a, **k)
    g['text'] = lambda x, y, *a, **k: orig['text'](*(MP((x, y)) + tuple(a)), **k)
    try:
        make_city()
    finally:
        g.update(orig)
    TREES[:] = [(MP(p), r) for p, r in TREES]
    LAMPS[:] = [MP(p) for p in LAMPS]
    BENCH[:] = [(MP(p), a) for p, a in BENCH]
    NUMS[:] = [(s_, MP(c)) for s_, c in NUMS]
    BLUE[:] = [[MP(q) for q in pl] for pl in BLUE]
    for lst in (ALLEY_DW, DRIVEWAYS):                                     # въезд через тротуар: от нового края квартала до проезжей части
        for i, pl in enumerate(lst):
            x0, y0, x1, y1 = bbox(pl)
            q = [MP(p) for p in pl]
            nx0, ny0, nx1, ny1 = bbox(q)
            inside_x = [MP((x0, (y0 + y1) / 2))[0] != x0, MP((x1, (y0 + y1) / 2))[0] != x1]
            inside_y = [MP(((x0 + x1) / 2, y0))[1] != y0, MP(((x0 + x1) / 2, y1))[1] != y1]
            if inside_x[1] and not inside_x[0]:
                nx0 = nx1 - SW - 1
            elif inside_x[0] and not inside_x[1]:
                nx1 = nx0 + SW + 1
            if inside_y[1] and not inside_y[0]:
                ny0 = ny1 - SW - 1
            elif inside_y[0] and not inside_y[1]:
                ny1 = ny0 + SW + 1
            lst[i] = R(nx0, ny0, nx1, ny1)
    hw = ROAD / 2.0 + SW
    # Vd между бульваром и Hse2: дома вдоль бульвара + хоздвор с выходом на Hse2 (в него упираются переулки SE2 и Eb)
    x0, x1, y0, y1 = 1840 - hw, 1840 + hw, 760 + hw, 960 - hw
    rowfill(x0, y0, x1, (y0 + y1) / 2.0, 'N')                                      # v29: только дома, спиной к спине
    rowfill(x0, (y0 + y1) / 2.0, x1, y1, 'S', corners=False)
    BLK['VDF'] = R(x0, y0, x1, y1)
    # Vs3 между бульваром и Hse: ряд домов (стык буквой Т)
    x0, x1, y0, y1 = 1505 - hw, 1505 + hw, 860 + hw, 1030 - hw
    rowfill(x0, y0, x1, y1, 'N')
    BLK['VSF'] = R(x0, y0, x1, y1)


def build():
    make_city_v28()
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%d 0 %d %d">' % (
        (XMAX - XMIN) * PX, H * PX, XMIN, XMAX - XMIN, H)]
    o.append(rect(XMIN, 0, XMAX, H, 'white'))
    ter = [rect(XMIN, 0, XMAX, H, LAWN)]
    ter.append(poly(offset_pl(CANAL, -40) + [(XMAX + 5, H + 5), (XMIN - 5, H + 5)], SAND))
    ter.append(poly([(XMIN - 5, 1246), (XMAX + 5, 1246)] + offset_pl(CANAL, 40)[::-1], PROM))
    ter.append(line(CANAL, WALL, 84, 'butt'))
    ter.append(line(CANAL, WATER, 72, 'butt'))
    for pl in BLK.values():
        ter.append(poly(pl, YARD))
    o += group('terrain', ter)
    rd = []
    for s in ST.values():
        rd.append(line(s.pts, '#BFC3C4', s.road + 2 * s.sw + 2, s.cap))      # бордюр
    for s in ST.values():
        rd.append(line(s.pts, WALK, s.road + 2 * s.sw, s.cap))
    for s in ST.values():
        rd.append(line(s.pts, ASPH, s.road, s.cap))
    for pl in DRIVEWAYS + ALLEY_DW:
        rd.append(poly(pl, '#9DA2A2'))                                       # v29: въезд — тем же асфальтом, что переулок
    for bx in (620, 1840):                                                   # перила двух мостов
        for x in (bx - 36, bx + 36):
            rd.append(line([(x, 1294), (x, 1390)], '#5E5A50', 1.8, 'butt'))
    centre_dashes(rd)
    crosswalks(rd)
    lights_and_stops(rd)
    o += group('roads', rd)
    o += group('squares_and_lots', PAVE0 + LAWNS + PAVE + LOTS)
    o += group('paths', [line(p, '#5E8FBF', 2.2, extra=' stroke-dasharray="6 5"') for p in BLUE])
    o += group('shadows', SHADOW)
    o += group('buildings', BLD + SPEC)
    trs = [circle(p, r, '#B9D19F', '#86A274', 1) for p, r in TREES]
    avoid = list(BLK.values()) + [R(1460, 0, 2160, 80)]
    scatter_trees(trs, 16, (XMIN, 0, XMAX, 50), avoid)
    scatter_trees(trs, 6, (XMIN, 120, -30, 600), avoid)
    scatter_trees(trs, 8, (2290, 120, XMAX, 600), avoid)
    for x in range(int(XMIN) + 70, int(XMAX), 170):
        if min(abs(x - 620), abs(x - 1840)) > 70:
            trs.append(circle((x, 1428), 8, '#A9C98A', '#7E9E62', 1))
    o += group('trees', trs)
    ob = []
    hydrants(ob)
    for p in LAMPS:
        ob.append(circle(p, 4, '#FFFDF4', '#BA8442', 1.5))
    for p, a in BENCH:
        ob.append(poly(rr(p, 16, 4, a), '#B08D5E', '#6E5A3A', 0.6))
    x = XMIN + 72.0
    while x < XMAX:
        if min(abs(x - 620), abs(x - 1840)) > 64:
            ob.append(poly(rr((x, 1288), 16, 4, 0), '#B08D5E', '#6E5A3A', 0.6))
        x += 168
    o += group('objects', ob)
    nb = []
    for s, (x, y) in NUMS:
        nb.append(circle((x, y), 13, '#FFFFFF', INK, 1.6))
        nb.append(text(x, y + 0.5, s, 12, 700, INK, 'middle'))
    o += group('numbers', nb)
    tt = [rect(1480, 8, 2420, 70, '#FFFFFF', '#8FA9B1', 1.2, ' fill-opacity="0.94"')]
    tt.append(text(1496, 32, 'ГОРОД / DOWNTOWN · план v30 — улицы 12 м + тротуары 5 м, всё застроено', 20, 700))
    tt.append(text(1496, 56, 'Улицы упираются в дома буквой Т — сквозь город не видно · парковок-пустырей нет (03 — подземный паркинг) · 40 дайнер · 41 заправка',
                   11.5, 400, '#6D7A80'))
    for x, y, s, anc in ((150, 40, '↖ Неблагополучный район', 'start'),
                         (XMIN + 6, 690, '← Интернацио-', 'start'), (XMIN + 6, 708, 'нальная стройка', 'start'),
                         (XMAX - 6, 790, 'Элитный холм →', 'end'), (1240, 1446, '↓ Городской пляж ↓', 'middle')):
        tt.append(text(x, y, s, 13, 700, '#5F6E75', anc))
    for i in range(5):
        tt.append(rect(140 + i * 50, 1426, 190 + i * 50, 1435, INK if i % 2 == 0 else '#FFFFFF', INK, 1))
    tt.append(text(140, 1414, '0', 11, 600, INK, 'middle'))
    tt.append(text(390, 1414, '50 м', 11, 600, INK, 'middle'))
    o += group('title', tt)
    o.append('</svg>')
    return '\n'.join(o)


def straight_runs():
    """Длина каждого прямого куска крайних улиц, м."""
    out = []
    for n in RING:
        for a, b in zip(ST[n].pts[:-1], ST[n].pts[1:]):
            out.append((n, vlen(vsub(b, a)) * 0.2))
    return out


if __name__ == '__main__':
    if os.path.exists(OUT_SVG) or os.path.exists(OUT_PNG):
        raise SystemExit('v30 outputs exist')
    io.open(OUT_SVG, 'w', encoding='utf-8').write(build())
    print('wrote', OUT_SVG)
    print('ring runs, m:', ', '.join('%s %.0f' % r for r in straight_runs()))
    print('trees:', len(TREES), 'parks:', len([n for n in NUMS if n[0] in ('20', '21', '23', '27')]))
    print(render_png(OUT_SVG, OUT_PNG, int((XMAX - XMIN) * PX), int(H * PX)))
