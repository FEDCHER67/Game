"""Город / Downtown — предложение планировки v11.

Основа — v10. По замечаниям Вадима (11.10.2026):
- полиции на противоположных концах: 10 в левом нижнем углу, 11 в правом верхнем, таксопарк 12 пристроен к 11;
- будущая база 13 — в правом нижнем углу, П-образный дом, двор с воротами на поперечную улицу;
- по краям скверов 23 и 21 добавлены дома, чтобы квартал не просматривался насквозь слева направо;
- на месте полиции 1 на северо-западе — Т-образный дом, рядок и маленький сквер 30.
Остальное как в v10.
Скрипт печатает доли площади района: улицы, площадь, скверы, дома.
Стандарт схем: вид сверху, однотонные заливки, тонкие контуры, деревья — круги, на схеме только номера.
1 единица = 0,2 м. Запуск: python build_gorod_v11.py --png
"""
import io
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_SVG = os.path.join(HERE, 'Город_Downtown_v16.svg')
OUT_PNG = os.path.join(HERE, 'Город_Downtown_v16.png')
W, H = 2350, 1460
XMIN, XMAX = -110, 2460
PX = 1.3
INK = '#34424B'
FONT = 'Arial, sans-serif'
rnd = random.Random(1111)

LAWN, YARD, WALK, ASPH, MARK = '#E3EBD4', '#E8EEDB', '#E3E1D9', '#5F666C', '#F8F8F4'   # v14: тёмный асфальт
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


# ------------------------------------------------------------------ улицы: прямые, под 90°, кварталы разной формы, без тупиков
class St(object):
    def __init__(self, pts_, road, sw, kind='street', cap='butt'):
        self.pts, self.road, self.sw, self.kind, self.cap = pts_, road, sw, kind, cap

    @property
    def hw(self):
        return self.road / 2.0 + self.sw


AXIS = 1170                                                           # ось: башни — фонтан — бульвар — мост
ST = {
    'N': St([(100, 150), (1840, 150), (1840, 330), (2240, 330)], 40, 16, 'main', 'square'),   # северная, со ступенькой
    'W': St([(100, 150), (100, 1210)], 40, 16, cap='square'),
    'S': St([(100, 1210), (2240, 1210)], 40, 16, 'main', 'square'),                          # вдоль набережной
    'E': St([(2240, 330), (2240, 1210)], 40, 16, cap='square'),
    'B': St([(XMIN, 760), (XMAX, 760)], 60, 16, 'main'),                                      # бульвар
    'Va': St([(540, 150), (540, 760)], 40, 16, cap='square'),
    'Va2': St([(620, 760), (620, 1210)], 40, 16, cap='square'),                               # сдвиг у бульвара
    'Vb': St([(790, 150), (790, 760)], 40, 16, 'main', 'square'),
    'Vc': St([(1550, 150), (1550, 760)], 40, 16, 'main', 'square'),
    'AX': St([(AXIS, 760), (AXIS, H)], 40, 16, 'main'),                                       # к мосту на пляж
    'Vd': St([(1840, 330), (1840, 1210)], 40, 16, cap='square'),
    'L1': St([(100, 450), (320, 450), (320, 150)], 40, 16, cap='square'),                     # Г-образная улица
    'L2': St([(1550, 470), (1690, 470), (1690, 760)], 40, 16, cap='square'),                  # Г-образная улица
    'L3': St([(790, 760), (790, 1000), (AXIS, 1000)], 40, 16, cap='square'),                  # Г-образная улица
    'Hsw': St([(100, 990), (620, 990)], 40, 16, cap='square'),
    'Hse': St([(AXIS, 1030), (1840, 1030)], 40, 16, cap='square'),
    'Hse2': St([(1840, 960), (2240, 960)], 40, 16, cap='square'),
}   # v12: диагональные выезды NW/NE к старым соседям убраны — на общей карте дороги приходят по улицам сетки
for _s in ST.values():                                                # v14: улицы шире, как на референсах
    _s.road += 10
    _s.sw -= 1
CANAL = [(XMIN, 1342), (800, 1336), (1600, 1340), (XMAX, 1348)]
DISTRICT = [(100, 150), (1840, 150), (1840, 330), (2240, 330), (2240, 1210), (100, 1210)]


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


BLK = {   # кварталы внутри тротуаров (бульвар — 46 ед., остальные — 36 ед.)
    'NWa': R(136, 186, 284, 414),
    'NWb': [(356, 186), (504, 186), (504, 714), (136, 714), (136, 486), (356, 486)],                # Г-образный
    'NC': R(576, 186, 754, 714),
    'SQ': R(826, 186, 1514, 714),
    'NEl': [(1586, 186), (1804, 186), (1804, 714), (1726, 714), (1726, 434), (1586, 434)],           # Г-образный
    'NEr': R(1586, 506, 1654, 714),
    'Ea': R(1876, 366, 2204, 714),
    'SWa': R(136, 806, 584, 954),
    'SWb': R(136, 1026, 584, 1174),
    'SCl': [(656, 806), (754, 806), (754, 1036), (1134, 1036), (1134, 1174), (656, 1174)],           # Г-образный
    'SCr': R(826, 806, 1134, 964),
    'SEa': R(1206, 806, 1804, 994),
    'SEb': R(1206, 1066, 1804, 1174),
    'Eb': R(1876, 806, 2204, 924),
    'Ec': R(1876, 996, 2204, 1174),
}


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


def make_city():
    # ---- центральный квартал: 01, 02 небоскрёбы на подиумах, 03 одна общая подземная парковка под обеими башнями
    PAVE0.append(poly(BLK['SQ'], PLAZA))
    for x0, x1 in ((830, 890), (1450, 1510)):                                                   # газоны по бокам башен
        LAWNS.append(poly(fillet(R(x0, 196, x1, 320), 12), PARK_LAWN, '#A9C08C', 1))
        TREES.append((((x0 + x1) / 2.0, 296), 11))
    for x0, x1 in ((900, 1150), (1190, 1440)):
        bld(rrect(x0, 196, x1, 320, 26), '#C9D6E2', '#5F82A6', 1.2, h=8)
        c = ((x0 + x1) / 2.0, 258)
        h, ch = 58, 25
        oc = [(c[0] - h + ch, c[1] - h), (c[0] + h - ch, c[1] - h), (c[0] + h, c[1] - h + ch), (c[0] + h, c[1] + h - ch),
              (c[0] + h - ch, c[1] + h), (c[0] - h + ch, c[1] + h), (c[0] - h, c[1] + h - ch), (c[0] - h, c[1] - h + ch)]
        bld(oc, '#9DB9D6', '#3E5F80', 1.8, count=False, h=60)
        BLD.append(circle(c, 25, '#86A6C8', '#5F82A6', 0.8))
        BLD.append(circle(c, 9, '#D7E4F0', '#5F82A6', 0.8))
    num('01', (1025, 258))
    num('02', (1315, 258))
    SPEC.append(poly(rrect(836, 190, 1504, 326, 18), 'none', '#4F5A62', 1.2, ' stroke-dasharray="7 5"'))   # контур паркинга
    ramp(842, 876, 170, 236, True)                                                                  # въезд
    ramp(1464, 1498, 170, 236, False)                                                               # выезд
    num('03', (859, 262))
    # ---- 04 площадь: круг плитки и лучи к проходам, клумбы, террасы кафе, ступени к башням
    sq_rect = (826, 330, 1514, 714)
    AREA['square'] = (sq_rect[2] - sq_rect[0]) * (sq_rect[3] - sq_rect[1])
    F = (AXIS, 527)
    for p in ((AXIS, 330), (AXIS, 714), (826, F[1]), (1514, F[1])):
        PAVE.append(line([F, p], '#E7DABE', 44, 'butt'))
    PAVE.append(circle(F, 156, '#EEE4CC', '#D6C9AC', 1.2))
    for a0 in (15, 105, 195, 285):                                                                  # клумбы между лучами
        PAVE.append(poly(arc_pts(F, 104, a0, a0 + 60, 12) + arc_pts(F, 74, a0 + 60, a0, 12), '#CFE0B5', '#9DB884', 1))
        PAVE.append(line(arc_pts(F, 89, a0 + 6, a0 + 54, 10), '#E7A9B8', 4, 'round'))
    for r_ in (162, 172, 182):                                                                      # ступени к башням
        PAVE.append(line(arc_pts(F, r_, 238, 302, 14), '#CDBF9F', 1.6, 'butt'))
    shops = (('16', 'NW', (836, 340, 996, 452)), ('17', 'NE', (1344, 340, 1504, 452)),
             ('18', 'SW', (836, 600, 996, 704)), ('19', 'SE', (1344, 600, 1504, 704)))
    for lab, corner, (x0, y0, x1, y1) in shops:
        pl = bld(lshape(x0, y0, x1, y1, 48, 48, corner), '#E2B49A', INK, 1.3)
        AREA['square'] -= parea(pl)
        ix = x0 + 48 if corner in ('NW', 'SW') else x1 - 48
        iy = y0 + 48 if corner in ('NW', 'NE') else y1 - 48
        fx = x1 if corner in ('NW', 'SW') else x0
        fy = y1 if corner in ('NW', 'NE') else y0
        SPEC.append(line([(ix, fy), (ix, iy), (fx, iy)], '#F7EADC', 3, 'butt'))             # витрины внутрь площади
        num(lab, ((x0 + ix) / 2.0 if corner in ('NW', 'SW') else (ix + x1) / 2.0,
                  (y0 + iy) / 2.0 if corner in ('NW', 'NE') else (iy + y1) / 2.0))
    for x0, x1 in ((890, 986), (1354, 1450)):                                                     # террасы кафе у магазинов 16, 17
        PAVE.append(poly(rrect(x0, 394, x1, 446, 6), '#E6D2BA', '#C9A98A', 1))
        PAVE.append(line([(x0 + 4, 446), (x1 - 4, 446)], '#9DB884', 3, 'butt'))
    lobes = [(F[0] + 36, F[1]), (F[0] - 36, F[1]), (F[0], F[1] + 36), (F[0], F[1] - 36)]          # 15 фонтан-четырёхлистник
    for r_lobe, r_mid, col in ((43, 47, '#8E8676'), (41, 45, '#CFC7B4'), (32, 36, WATER)):
        for c in lobes:
            SPEC.append(circle(c, r_lobe, col))
        SPEC.append(circle(F, r_mid, col))
    SPEC.append(circle(F, 14, '#CFC7B4', '#8E8676', 0.8))
    SPEC.append(circle(F, 5, '#DDEFF5', '#6FA6C0', 0.6))
    SPEC.append(poly(rr((F[0] + 60, F[1] - 60), 10, 14, 0), '#2F5D8A', '#1E3F60', 0.8))      # 08 ATM у фонтана
    SPEC.append(poly(rr((F[0] + 60, F[1] - 62), 6, 5, 0), '#BFD8EA'))
    num('08', (F[0] + 84, F[1] - 78))
    num('15', (F[0], F[1] + 120))
    for x in (1090, 1250):                                                                       # киоски у южного прохода
        SPEC.append(poly(rrect(x - 13, 680, x + 13, 698, 4), '#9C7A5E', '#5E4A3A', 0.8))
        SPEC.append(rect(x - 9, 684, x + 9, 688, '#E8DCC8'))
    num('04', (868, 527))
    for a in (45, 135, 225, 315):
        r_ = math.radians(a)
        BENCH.append(((F[0] + 120 * math.cos(r_), F[1] + 120 * math.sin(r_)), a + 90))
        LAMPS.append((F[0] + 146 * math.cos(r_), F[1] + 146 * math.sin(r_)))
    for p in ((1056, 668), (1284, 668), (1040, 400), (1300, 400)):
        TREES.append((p, 12))
    SPEC.append(poly(rr((1340, 722), 40, 7, 0), '#9AA7B0', '#5E6A72', 0.8))                     # 14 остановка
    num('14', (1290, 722))
    BLUE.append([(AXIS, 196), (AXIS, 330)])

    # ---- северо-западный угол: Т-образный кирпичный дом у северной улицы, крупный бежевый дом у Г-образной улицы,
    #      30 сквер вокруг ножки «Т»
    shaped([(146, 196), (284, 196), (284, 250), (240, 250), (240, 330), (190, 330), (190, 250), (146, 250)], PAL['brick'],
           tower=(215, 222))
    fire_escape((160, 196), (200, 196), (0, -1))
    house(146, 346, 284, 414, PAL['beige'], tower=(262, 368), boxes=[(158, 360, 192, 380)])
    fire_escape((160, 414), (200, 414), (0, 1))
    park(fillet([(146, 256), (184, 256), (184, 334), (246, 334), (246, 256), (284, 256), (284, 338), (146, 338)], 8),
         [], 16, label='30', at=(165, 300), trees=3, seed=30)

    # ---- Г-образный квартал северо-запада: крупный дом со световым колодцем у северной улицы, два больших дома
    #      у бульвара, высокий каменный дом вдоль Va, два дома у западной улицы; 23 сквер заполняет остальное
    house(356, 186, 504, 264, PAL['brick2'], well=(410, 206, 450, 238), tower=(478, 214))
    fire_escape((368, 186), (396, 186), (0, -1))
    house(146, 634, 300, 714, PAL['tan'], tower=(178, 660), boxes=[(236, 650, 276, 672)])
    house(300, 628, 504, 714, PAL['dark'], well=(372, 652, 432, 688), tower=(478, 652))
    billboard(318, 640, 360, 646)
    fire_escape((226, 714), (270, 714), (0, 1))
    fire_escape((362, 714), (408, 714), (0, 1))
    house(444, 280, 504, 470, PAL['stone'], tower=(474, 432), boxes=[(456, 326, 492, 348)])
    fire_escape((504, 300), (504, 350), (1, 0))
    house(146, 492, 214, 548, PAL['teal'])
    house(146, 568, 214, 622, PAL['brick'], tower=(180, 596))
    fire_escape((146, 500), (146, 540), (-1, 0))
    park(fillet([(356, 272), (440, 272), (440, 476), (504, 476), (504, 622), (220, 622), (220, 492), (356, 492)], 16),
         [([(400, 272), (396, 340), (410, 430), (380, 520), (300, 556), (214, 559), (136, 559)], False),
          ([(380, 520), (450, 556), (504, 566)], False)], 18, label='23', at=(262, 596), trees=10, seed=23)

    # ---- квартал между западной улицей и площадью: большой бежевый дом с колодцем, лофт у бульвара, кирпичный дом
    #      вдоль Va; 21 сквер целиком
    house(586, 186, 744, 262, PAL['beige'], well=(640, 204, 690, 238), tower=(722, 230))
    fire_escape((650, 186), (686, 186), (0, -1))
    loft(586, 632, 744, 714, PAL['dark'])
    fire_escape((670, 714), (700, 714), (0, 1))
    house(586, 446, 640, 620, PAL['brick2'], tower=(612, 594), boxes=[(596, 470, 630, 490)])   # v16: опущен вниз к лофту
    fire_escape((586, 470), (586, 530), (-1, 0))
    park(fillet([(576, 276), (754, 276), (754, 624), (650, 624), (650, 436), (576, 436)], 16),
         [([(700, 276), (684, 360), (700, 450), (680, 540), (690, 624)], False),
          ([(576, 360), (665, 372), (754, 360)], False)], 20, label='21', at=(612, 300), trees=9, seed=21)
    SPEC.append(rect(661, 508, 675, 522, '#B8B2A6', '#6E6A60', 0.8))                          # памятник в сквере 21
    SPEC.append(circle((668, 515), 4, '#8E8676'))

    # ---- Г-образный квартал северо-востока: кирпичный дом, на углу круглая стеклянная башня, два дома вдоль улицы;
    #      скверы 24 и 22 целиком
    house(1586, 186, 1690, 258, PAL['brick'], tower=(1665, 214))
    fire_escape((1598, 186), (1626, 186), (0, -1))
    glass_round((1752, 243), 50, R(1700, 186, 1804, 300))
    house(1736, 330, 1804, 520, PAL['beige'], tower=(1770, 486), boxes=[(1748, 372, 1792, 394)])
    billboard(1746, 420, 1794, 426)
    house(1736, 520, 1804, 714, PAL['brick2'], tower=(1770, 646))
    fire_escape((1804, 470), (1804, 540), (1, 0))
    park(fillet([(1586, 268), (1694, 268), (1694, 308), (1730, 308), (1730, 434), (1586, 434)], 14),
         [([(1586, 356), (1652, 344), (1730, 366)], False)], 16, label='24', at=(1626, 404), trees=5, seed=24)
    park(fillet(R(1586, 506, 1654, 714), 14), [([(1586, 540), (1615, 600), (1625, 660), (1654, 700)], False)], 14,
         label='22', at=(1620, 540), trees=3, seed=22)

    # ---- северо-восточный угол: 11 полиция 2, к ней пристроен 12 таксопарк, стоянка такси у Vd; у бульвара
    #      большой дом и угловой дом со срезанным углом; 20 сквер с прудом между ними
    bld(rect_rc(2054, 376, 2204, 490, 'NE', 50), '#B9C8E6', INK, 2)
    BLD.append(line(arc_pts((2154, 426), 34, -90, 0, 8), '#8E9CB8', 1, 'butt'))
    SPEC.append(rect(2066, 478, 2190, 490, '#D9E1F0', '#8E9CB8', 0.8))
    num('11', (2124, 436))
    bld(R(1966, 376, 2054, 452), '#E5D5A0', INK, 1.8)
    for y in (388, 418):
        SPEC.append(rect(1960, y, 1966, y + 24, '#5E6569'))                                  # ворота гаража к стоянке
    num('12', (2010, 414))
    LOTS.append(poly(rrect(1886, 376, 1956, 496, 10), '#C3C9CD', '#9AA2A8', 0.8))
    stall_lines(1892, 1950, 382, 490, 14, vertical=False)
    house(1886, 632, 2040, 714, PAL['tan'], tower=(2006, 676), boxes=[(1900, 650, 1940, 670)])
    shaped([(2040, 620), (2174, 620), (2204, 650), (2204, 714), (2040, 714)], PAL['brick'], tower=(2150, 668))
    fire_escape((1984, 714), (2028, 714), (0, 1))
    park(fillet([(1876, 512), (2204, 512), (2204, 612), (2100, 612), (2100, 624), (1876, 624)], 14),
         [([(2066, 522), (2150, 534), (2154, 592), (2062, 606), (1984, 598), (1986, 532)], True),
          ([(1876, 566), (1930, 566), (1984, 572)], False), ([(1961, 714), (1961, 640), (1984, 598)], False),
          ([(2204, 560), (2172, 560), (2152, 566)], False)], 18,
         pond=organic((2068, 562), 40, 22, 7), label='20', at=(2178, 596), trees=7, seed=20)
    oc = [(2004 + 13 * math.cos(math.radians(22.5 + 45 * i)), 562 + 13 * math.sin(math.radians(22.5 + 45 * i)))
          for i in range(8)]
    SPEC.append(poly(oc, '#E9E1CE', '#8E8676', 1))                                              # беседка в сквере 20
    SPEC.append(circle((2004, 562), 4, '#B08D5E'))

    # ---- юго-запад: 28 задний переулок; по сторонам дома покрупнее, без пёстрых рядков
    PAVE.append(poly(R(136, 866, 584, 890), '#B9B6AC'))
    shaped([(146, 806), (240, 806), (240, 836), (270, 836), (270, 866), (146, 866)], PAL['cream'])
    shaped([(146, 890), (270, 890), (270, 954), (176, 954), (176, 924), (146, 924)], PAL['brick'])
    house(280, 806, 410, 866, PAL['brick2'], tower=(378, 832))
    house(410, 806, 500, 866, PAL['tan'])
    house(500, 806, 584, 866, PAL['teal'])
    house(280, 890, 380, 954, PAL['dark'])
    house(380, 890, 584, 954, PAL['beige'], tower=(508, 922), boxes=[(400, 904, 440, 924)])
    for x in (318, 448, 530):
        SPEC.append(rect(x, 869, x + 14, 877, '#4E6B52', '#2F4532', 0.6))                     # мусорные баки
    fire_escape((292, 806), (334, 806), (0, -1))
    fire_escape((420, 954), (466, 954), (0, 1))
    fire_escape((356, 866), (396, 866), (0, 1))
    num('28', (230, 878))
    # 10 полиция 1 в левом нижнем углу: ротонда на углу у западной и южной улиц, стоянка с выездом на поперечную улицу
    bld(R(146, 1056, 296, 1164), '#B9C8E6', INK, 2)
    BLD.append(circle((166, 1144), 28, '#B9C8E6', INK, 2))
    BLD.append(circle((166, 1144), 17, 'none', '#8E9CB8', 1))
    SPEC.append(rect(176, 1056, 284, 1068, '#D9E1F0', '#8E9CB8', 0.8))
    num('10', (230, 1106))
    LOTS.append(poly(rrect(310, 1036, 450, 1106, 12), '#C3C9CD', '#9AA2A8', 0.8))
    stall_lines(316, 444, 1042, 1068)
    stall_lines(316, 444, 1076, 1102)
    house(310, 1112, 450, 1174, PAL['brick2'], tower=(420, 1138))
    house(466, 1036, 584, 1174, PAL['stone'], well=(500, 1078, 550, 1128), tower=(562, 1152))
    fire_escape((584, 1050), (584, 1086), (1, 0))
    fire_escape((320, 1174), (366, 1174), (0, 1))

    # ---- южный центр: 07 магазин для бусика; 25 сквер целиком; у набережной кирпичный дом, каменное здание
    #      с колоннадой к скверу, бежевый дом; 05 стеклянный офис со скруглённым углом напротив площади; 27 сквер
    bld(lshape(656, 806, 754, 990, 62, 56, 'NW'), '#E3A982', INK, 1.8)
    PAVE.append(poly(R(712, 868, 754, 990), '#D3CFC3'))
    for y in (884, 930):
        SPEC.append(rect(706, y, 712, y + 28, '#5E6569'))
    num('07', (684, 930))
    park(fillet([(656, 996), (754, 996), (754, 1040), (1134, 1040), (1134, 1088), (656, 1088)], 14),
         [([(656, 1060), (780, 1066), (960, 1064), (1134, 1066)], False)], 16, label='25', at=(700, 1030),
         trees=8, seed=25)
    house(666, 1100, 806, 1174, PAL['brick'], tower=(771, 1130), boxes=[(680, 1116, 716, 1136)])
    classical(806, 1096, 1016, 1174, 'N')
    house(1016, 1094, 1124, 1174, PAL['tan'], tower=(1070, 1130))
    fire_escape((680, 1174), (724, 1174), (0, 1))
    glass_office(rect_rc(1000, 816, 1124, 954, 'NE', 50))
    num('05', (1052, 900))
    park(fillet(R(836, 814, 992, 956), 16), [([(826, 885), (910, 880), (992, 892)], False)], 16, label='27',
         at=(870, 932), trees=5, seed=27)

    # ---- юго-восток: 06 стеклянный офис; у бульвара кирпичный дом и большой дом с колодцем; Г-образный кирпичный
    #      дом; 26 сквер целиком; у набережной каменный дом, узкий бирюзовый, кирпичный и лофт с проходом между ними
    glass_office(R(1216, 816, 1336, 940))
    num('06', (1276, 868))
    house(1350, 806, 1486, 880, PAL['brick2'], tower=(1450, 840))
    house(1486, 806, 1630, 884, PAL['beige'], well=(1530, 826, 1582, 860), tower=(1606, 842))
    billboard(1496, 868, 1540, 874)
    shaped(lshape(1640, 806, 1804, 994, 58, 60, 'NE'), PAL['dark'], tower=(1770, 850))
    fire_escape((1426, 806), (1476, 806), (0, -1))
    park(fillet([(1340, 890), (1640, 890), (1640, 994), (1216, 994), (1216, 946), (1340, 946)], 14),
         [([(1216, 970), (1340, 966), (1450, 940), (1560, 946), (1640, 944)], False)], 16, label='26',
         at=(1700, 960), trees=8, seed=26)
    house(1216, 1100, 1360, 1174, PAL['stone'], tower=(1330, 1130), boxes=[(1232, 1116, 1270, 1136)])
    house(1360, 1104, 1430, 1174, PAL['teal'])
    house(1470, 1096, 1610, 1174, PAL['brick'], tower=(1505, 1130))
    loft(1610, 1090, 1794, 1174, PAL['dark'])
    fire_escape((1300, 1174), (1350, 1174), (0, 1))
    BLUE.append([(1450, 1066), (1450, 1174)])

    # ---- восток у бульвара: Г-образный бежевый дом, кирпичный угловой дом, 29 сквер между ними
    shaped(lshape(1886, 806, 2030, 924, 58, 60, 'NW'), PAL['beige'], tower=(1916, 880))
    shaped(rect_rc(2104, 806, 2204, 924, 'NE', 34), PAL['brick'])
    fire_escape((1900, 806), (1950, 806), (0, -1))
    park(fillet([(1948, 866), (2032, 866), (2032, 806), (2100, 806), (2100, 924), (1948, 924)], 12), [], 16,
         label='29', at=(2066, 846), trees=3, seed=29)

    # ---- юго-восточный угол: 13 будущая база — единственный П-образный дом, двор с воротами на поперечную улицу
    bld([(1960, 1006), (2008, 1006), (2008, 1126), (2156, 1126), (2156, 1006), (2204, 1006), (2204, 1174), (1960, 1174)],
        '#C0D6C4', INK, 2.2)
    PAVE.append(poly(R(2008, 1006, 2156, 1126), '#D8D4C6'))
    SPEC.append(line([(2008, 1006), (2054, 1006)], '#6E7A70', 2.4, 'butt'))                  # забор с воротами
    SPEC.append(line([(2110, 1006), (2156, 1006)], '#6E7A70', 2.4, 'butt'))
    SPEC.append(rect(2050, 1060, 2114, 1094, 'none', '#6E7A70', 0.9, ' stroke-dasharray="3 2"'))   # место для бусика
    num('13', (2180, 1090))
    house(1886, 1010, 1950, 1174, PAL['stone'], tower=(1918, 1130))
    fire_escape((1886, 1040), (1886, 1100), (-1, 0))

# ------------------------------------------------------------------ разметка, гидранты
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


RING = ('N', 'W', 'S', 'E')                     # улицы по краю района: за ними город кончается


def crossing_legs(j, names):
    """Где на перекрёстке j нужны зебры (v15):
    - не на ногах, уходящих из района (кроме оси к мосту на пляж);
    - не поперёк окружных улиц N/W/E — за ними некуда идти; поперёк S — один переход к набережной;
    - на Т-образном перекрёстке внутри района — только поперёк примыкающей улицы;
      на главной оси у площади (бульвар × AX) — все ноги."""
    all_legs = [(n, v, L) for n in names for v, L in legs(n, j)]
    if len(all_legs) < 3:
        return []
    keep = []
    s_done = False
    axis = 'AX' in names and 'B' in names
    for name, v, L in all_legs:
        if name in RING:
            if name != 'S' or s_done or v[0] < 0:
                continue
            s_done = True
            keep.append((name, v, L))
            continue
        probe = vadd(j, vmul(v, 60))
        if not inside_poly(probe, DISTRICT) and name != 'AX':
            continue
        if len(all_legs) == 3 and not axis and len(legs(name, j)) != 1:
            continue
        keep.append((name, v, L))
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
            k = -s.road / 2.0 + 5
            while k <= s.road / 2.0 - 4:
                out.append(poly(rr(vadd(c, vmul(nrm, k)), 16, 4, ang_of(v)), MARK))
                k += 8


def traffic_lights(out):
    """Светофоры по углам перекрёстков, где сходятся три и больше направлений (как на референсах)."""
    for j, names in JUN:
        if len(crossing_legs(j, names)) < 2:
            continue
        hw = max(ST[n].road / 2.0 + ST[n].sw for n in names) - 3
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = (j[0] + dx * hw, j[1] + dy * hw)
            out.append(rect(p[0] - 3.2, p[1] - 3.2, p[0] + 3.2, p[1] + 3.2, '#2E3238', '#1A1D20', 0.6))
            out.append(circle(p, 1.6, '#F2C230'))


def centre_dashes(out):
    for name, s in ST.items():
        if name == 'B':
            continue
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
                k2 = min(L - 2, k + 14)
                if not any(z0 < k2 and k < z1 for z0, z1 in zones):
                    out.append(line([vadd(a, vmul(u, k)), vadd(a, vmul(u, k2))], MARK, 1.6, 'butt'))
                k += 26


def boulevard_median(out, trs):
    """Зелёная полоса посередине бульвара с деревьями; на перекрёстках разрыв под переходы."""
    a, b = ST['B'].pts
    u = vunit(vsub(b, a))
    L = vlen(vsub(b, a))
    zones = []
    for j, names in JUN:
        if 'B' not in names:
            continue
        t = vdot(vsub(j, a), u)
        r = max(cross_dist('B', j, u, names, lambda st: st.sw + 10),
                cross_dist('B', j, (-u[0], -u[1]), names, lambda st: st.sw + 10))
        zones.append((t - r, t + r))
    zones.sort()
    pos = 0.0
    for z0, z1 in zones + [(L, L)]:
        if z0 - pos > 40:
            p0, p1 = vadd(a, vmul(u, pos + 6)), vadd(a, vmul(u, z0 - 6))
            out.append(line([p0, p1], '#C9C3B5', 22, 'round'))
            out.append(line([p0, p1], PARK_LAWN, 18, 'round'))
            k = 28.0
            while k < (z0 - pos) - 24:
                trs.append(circle(vadd(a, vmul(u, pos + k)), 8, '#B9D19F', '#86A274', 1))
                k += 62
        pos = max(pos, z1)


DRIVEWAYS = [R(356, 1010, 392, 1036),                                  # 10 стоянка полиции → поперечная улица
             R(1860, 420, 1886, 456),                                  # 12 стоянка таксопарка → Vd
             R(754, 910, 770, 946),                                    # 07 площадка магазина → Г-образная улица
             R(2064, 980, 2100, 1006),                                 # 13 ворота базы → поперечная улица
             R(120, 866, 136, 890), R(584, 866, 600, 890)]             # 28 переулок → западная улица и Va2


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


def build():
    make_city()
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%d 0 %d %d">' % (
        (XMAX - XMIN) * PX, H * PX, XMIN, XMAX - XMIN, H)]
    o.append(rect(XMIN, 0, XMAX, H, 'white'))

    # ---- terrain: газон, пляж, набережная, канал, газоны кварталов
    ter = [rect(XMIN, 0, XMAX, H, LAWN)]
    ter.append(poly(offset_pl(CANAL, -40) + [(XMAX + 5, H + 5), (XMIN - 5, H + 5)], SAND))
    ter.append(poly([(XMIN - 5, 1246), (XMAX + 5, 1246)] + offset_pl(CANAL, 40)[::-1], PROM))
    ter.append(line(CANAL, WALL, 84, 'butt'))
    ter.append(line(CANAL, WATER, 72, 'butt'))
    for pl in BLK.values():
        ter.append(poly(pl, YARD))
    o += group('terrain', ter)

    # ---- roads
    rd = []
    for s in ST.values():
        rd.append(line(s.pts, WALK, s.road + 2 * s.sw, s.cap))
    for s in ST.values():
        rd.append(line(s.pts, ASPH, s.road, s.cap))
    for pl in DRIVEWAYS:                                                                     # выезды через тротуар
        rd.append(poly(pl, '#B3B9BD'))
    med_trees = []
    boulevard_median(rd, med_trees)
    for x in (AXIS - 36, AXIS + 36):                                                         # перила моста
        rd.append(line([(x, 1294), (x, 1390)], '#5E5A50', 1.8, 'butt'))
    centre_dashes(rd)
    crosswalks(rd)
    traffic_lights(rd)
    o += group('roads', rd)

    # ---- площадь, скверы, дворы, стоянки
    o += group('squares_and_lots', PAVE0 + LAWNS + PAVE + LOTS)

    # ---- paths: пешеходные проходы (синий пунктир)
    o += group('paths', [line(p, '#5E8FBF', 2.2, extra=' stroke-dasharray="6 5"') for p in BLUE])

    # ---- buildings
    o += group('shadows', SHADOW)
    o += group('buildings', BLD + SPEC)

    # ---- trees: простые круги без точек
    trs = [circle(p, r, '#B9D19F', '#86A274', 1) for p, r in TREES]
    trs += med_trees                                                                         # деревья на полосе бульвара
    x = XMIN + 30.0
    while x < XMAX:
        if abs(x - AXIS) > 64:
            trs.append(circle((x, 1270), 9, '#B9D19F', '#86A274', 1))
        x += 84
    avoid = list(BLK.values()) + [R(628, 0, 1312, 90), R(2330, 190, 2410, 280)]
    scatter_trees(trs, 30, (XMIN, 0, XMAX, 112), avoid)
    scatter_trees(trs, 10, (XMIN, 112, 62, 1200), avoid)
    scatter_trees(trs, 14, (1880, 112, XMAX, 294), avoid)
    scatter_trees(trs, 10, (2280, 294, XMAX, 1200), avoid)
    for x in range(int(XMIN) + 70, int(XMAX), 170):
        if abs(x - AXIS) > 70:
            trs.append(circle((x, 1428), 8, '#A9C98A', '#7E9E62', 1))                          # пальмы на пляже
    o += group('trees', trs)

    # ---- objects: гидранты, немного фонарей и лавок, перила набережной
    ob = []
    hydrants(ob)
    for p in LAMPS:
        ob.append(circle(p, 4, '#FFFDF4', '#BA8442', 1.5))
    for p, a in BENCH:
        ob.append(poly(rr(p, 16, 4, a), '#B08D5E', '#6E5A3A', 0.6))
    x = XMIN + 72.0
    while x < XMAX:
        if abs(x - AXIS) > 64:
            ob.append(poly(rr((x, 1288), 16, 4, 0), '#B08D5E', '#6E5A3A', 0.6))
        x += 168
    rail = offset_pl(CANAL, 41)
    left = [q for q in rail if q[0] < AXIS - 36]
    right = [q for q in rail if q[0] > AXIS + 36]
    yl = rail[1][1] + (rail[2][1] - rail[1][1]) * (AXIS - 36 - rail[1][0]) / (rail[2][0] - rail[1][0])
    ob.append(line(left + [(AXIS - 36, yl)], '#6E6A60', 1.0, 'butt'))
    ob.append(line([(AXIS + 36, yl)] + right, '#6E6A60', 1.0, 'butt'))
    o += group('objects', ob)

    # ---- numbers
    nb = []
    for s, (x, y) in NUMS:
        nb.append(circle((x, y), 13, '#FFFFFF', INK, 1.6))
        nb.append(text(x, y + 0.5, s, 12, 700, INK, 'middle'))
    o += group('numbers', nb)

    # ---- title, directions, north arrow, scale
    tt = [rect(640, 14, 1300, 76, '#FFFFFF', '#8FA9B1', 1.2, ' fill-opacity="0.94"')]
    tt.append(text(658, 36, 'ГОРОД / DOWNTOWN · предложение v16', 22, 700))
    tt.append(text(658, 61, 'VOLUNTEERS ONLY · полиции слева снизу и справа сверху, база справа снизу · 1 ед. = 0,2 м', 12.5, 400,
                   '#6D7A80'))
    for x, y, s, anc in ((150, 40, '↖ Неблагополучный район', 'start'), (2440, 112, 'Промзона, порт ↗', 'end'),
                         (XMIN + 6, 690, '← Интернацио-', 'start'), (XMIN + 6, 708, 'нальная стройка', 'start'),
                         (XMAX - 6, 700, 'Элитный холм →', 'end'), (AXIS + 50, 1446, '↓ Городской пляж', 'start')):
        tt.append(text(x, y, s, 13, 700, '#5F6E75', anc))
    tt.append(text(2370, 214, 'С', 14, 700, INK, 'middle'))
    tt.append(line([(2370, 262), (2370, 232)], INK, 2.2))
    tt.append(poly([(2370, 225), (2365, 238), (2375, 238)], INK))
    for i in range(5):
        tt.append(rect(140 + i * 50, 1426, 190 + i * 50, 1435, INK if i % 2 == 0 else '#FFFFFF', INK, 1))
    tt.append(text(140, 1414, '0', 11, 600, INK, 'middle'))
    tt.append(text(390, 1414, '50 м', 11, 600, INK, 'middle'))
    o += group('title', tt)
    o.append('</svg>')
    return '\n'.join(o)


def shares():
    total = parea(DISTRICT)
    blocks = sum(parea(pl) for pl in BLK.values())
    return {'улицы и тротуары': (total - blocks) / total, 'площадь': AREA['square'] / total,
            'скверы': AREA['park'] / total, 'дома': AREA['bld'] / total}


if __name__ == '__main__':
    io.open(OUT_SVG, 'w', encoding='utf-8').write(build())
    print('wrote', OUT_SVG)
    for k, v in shares().items():
        print('  %-18s %5.1f %%' % (k, v * 100))
    if '--png' in sys.argv:
        sys.path.insert(0, r'C:\Users\chern_0eqkb03\AppData\Local\Temp\npcw\mapjoin\build')
        import render
        print(render.render(OUT_SVG, OUT_PNG, int((XMAX - XMIN) * PX)))
