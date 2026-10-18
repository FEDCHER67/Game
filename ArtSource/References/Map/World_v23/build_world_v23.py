"""Общая карта v23 (TASK-000663): районы раздвинуты под три живописных вида (референсы ГПТ, Relief_2026-10-16):
  A. Хутор (и всё западнее x 365) уходит на 100 м на запад от Стройки — между ними гряда с дорогой через гребень;
  B. Стройка / Тихая долина ещё на 120 м западнее Даунтауна (юг, y < 500) — гряда с видом на город и спуском;
  C. Порт и Трамдуро на 150 м севернее — мыс между Даунтауном и Портом, карниз с видом на Порт, мост и остров.
Делается деформацией готового MASTER_v22.svg: каждая координата проходит через W(x, y) (сдвиг постоянный внутри
районов, растяжение только в полосах между ними). Восток уходит вправо (холст шире), Порт — вверх (холст выше).
Полосы затем заполняются грядами (лес, скалы, горизонтали) и новыми дорогами — без пустого луга."""
import base64
import io
import math
import os
import re
import subprocess

from PIL import Image

MAP = r'C:\Users\chern_0eqkb03\Desktop\Map'
OUTD = os.path.join(MAP, 'Итоговая карта')
SRC = os.path.join(OUTD, 'VOLUNTEERS_MAP_MASTER_v22.svg')
SVG_OUT = os.path.join(OUTD, 'VOLUNTEERS_MAP_MASTER_v23.svg')
PNG_OUT = os.path.join(OUTD, 'VOLUNTEERS_MAP_FINAL_v23.png')
PRE_OUT = os.path.join(OUTD, 'VOLUNTEERS_MAP_PREVIEW_v23.png')
Image.MAX_IMAGE_PIXELS = None

W_OLD, H_OLD = 1474.0, 840.0
GROW_X, GROW_Y = 220.0, 150.0
W_NEW, H_NEW = W_OLD + GROW_X, H_OLD + GROW_Y


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def warp_m(x, y):
    """Метры мира v22 -> v23."""
    sy = r(y, 500, 570)
    re_ = r(x, 895, 945)
    dx = 100 * r(x, 365, 385) + 120 * ((1 - sy) * r(x, 575, 615) + sy * re_)
    dy = 150 * re_ * r(y, 512, 540)
    if dy == 0 and y >= 838:                       # верхний край холста (горы на северо-западе) тянется к новому краю
        dy = GROW_Y + 10
    return x + dx, y + dy


def to_m(px, py):
    return (px + 350) / 5.0, (3500 - py) / 5.0


def to_u(xm, ym):
    return xm * 5 - 350, 3500 - ym * 5


def warp_u(px, py):
    return to_u(*warp_m(*to_m(px, py)))


s = open(SRC, encoding='utf-8').read()
NUM = r'-?\d+(?:\.\d+)?(?:e-?\d+)?'


def f1(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def warp_pairs(txt, ox, oy):
    out, pos = [], 0
    for m in re.finditer(r'(%s)(\s*,\s*|\s+)(%s)' % (NUM, NUM), txt):
        out.append(txt[pos:m.start()])
        x, y = float(m.group(1)) + ox, float(m.group(3)) + oy
        X, Y = warp_u(x, y)
        out.append(f1(X - ox) + m.group(2) + f1(Y - oy))
        pos = m.end()
    out.append(txt[pos:])
    return ''.join(out)


def attr(tag, name):
    m = re.search(r'\s%s="(%s)"' % (name, NUM), tag)
    return float(m.group(1)) if m else None


def set_attr(tag, name, val):
    return re.sub(r'(\s%s=")(%s)(")' % (name, NUM), lambda m: m.group(1) + f1(val) + m.group(3), tag, count=1)


# ---------------------------------------------------------------- растровые вставки (планы районов)
def stretch_image(tag, ox, oy):
    x, y, w, h = attr(tag, 'x') + ox, attr(tag, 'y') + oy, attr(tag, 'width'), attr(tag, 'height')
    xm0, xm1 = to_m(x, 0)[0], to_m(x + w, 0)[0]
    if xm0 < 375 < xm1:                              # через полосу A (сдвиг только по x): перерисовать столбцами
        href = re.search(r'href="file:///([^"]+)"', tag)
        if href:
            from urllib.parse import unquote
            srcf = unquote(href.group(1)).replace('/', os.sep)
            im = Image.open(srcf).convert('RGBA')
            sc = im.width / w
            X0 = warp_u(x, 0)[0]
            X1 = warp_u(x + w, 0)[0]
            nw = int(round((X1 - X0) * sc))
            out = Image.new('RGBA', (nw, im.height))
            # обратное отображение x по сетке (сдвиг полосы A монотонный)
            xs = [x + i / sc for i in range(int(w * sc) + 1)]
            fw = [warp_u(v, 0)[0] for v in xs]
            k = 0
            for c in range(nw):
                X = X0 + (c + .5) / sc
                while k < len(fw) - 2 and fw[k + 1] < X:
                    k += 1
                src = min(im.width - 1, k)
                out.paste(im.crop((src, 0, src + 1, im.height)), (c, 0))
            dst = os.path.join(MAP, '00_Сборка_общей_карты', 'v23_assets', 'A_' + os.path.basename(srcf))
            out.save(dst)
            tag = tag.replace(href.group(1), dst.replace(os.sep, '/'))
            tag = set_attr(tag, 'x', X0 - ox)
            tag = set_attr(tag, 'width', X1 - X0)
            return tag
    cx, cy = x + w / 2, y + h / 2
    X, Y = warp_u(cx, cy)
    tag = set_attr(tag, 'x', x + X - cx - ox)
    tag = set_attr(tag, 'y', y + Y - cy - oy)
    return tag


# ---------------------------------------------------------------- проход по тегам
# ---------------------------------------------------------------- новые дороги (метры мира v23)
def chaikin(p, n=3):
    for _ in range(n):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            q += [(a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25), (a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75)]
        q.append(p[-1])
        p = q
    return p


VIEWS = {'A': (438, 416), 'B': (748, 378), 'C': (1334, 560)}
ROAD_A = chaikin([(490, 374), (472, 368), (454, 374), (442, 392), VIEWS['A'], (432, 440), (412, 456), (392, 462), (378, 478),
                  (368, 502), (361, 526), (358, 547)])
ROAD_B = [(660, 350)] + chaikin([(672, 351), (690, 356), (712, 364), (730, 373), VIEWS['B'], (770, 374), (792, 364), (814, 354)])[1:-1] + [(835, 350), (850, 350)]
ROAD_C = chaikin([(1302, 438), (1308, 462), (1318, 495), (1328, 530), VIEWS['C'], (1330, 592), (1318, 628), (1304, 662), (1294, 695)])


def road_fix(tag, ox, oy, gids):
    pts = [tuple(map(float, q.split(','))) for q in re.search(r'points="([^"]*)"', tag).group(1).split()] if ',' in tag else []
    if not pts:
        return tag
    wm = [to_m(x + ox, y + oy) for x, y in pts]
    if 'R18_links' in gids and abs(wm[0][0] - 1302) < 3 and abs(wm[0][1] - 438) < 3:
        return None                                   # старый карниз v22 — заменён новым
    for i in range(len(wm) - 1):                       # главная дорога Стройка -> Даунтаун: через гряду с видом
        (x0, y0), (x1, y1) = wm[i], wm[i + 1]
        if min(x0, x1) < 700 and max(x0, x1) > 800 and 330 < y0 < 370 and 330 < y1 < 370:
            route = ROAD_B if x0 < x1 else ROAD_B[::-1]
            new = wm[:i + 1] + [p for p in route if min(x0, x1) < p[0] < max(x0, x1)] + wm[i + 1:]
            txt = ' '.join('%s,%s' % (f1(to_u(*p)[0] - ox), f1(to_u(*p)[1] - oy)) for p in new)
            return re.sub(r'points="[^"]*"', 'points="%s"' % txt, tag, count=1)
    return tag


CLIP_OFS = {'clip_d03': (1700.0, 1042.0), 'clip_d05': (2820.0, 1000.0)}   # клипы в локальных координатах своих групп
out, pos, stack, clip, gids = [], 0, [], None, []
for m in re.finditer(r'<(/?)(\w+)([^>]*?)(/?)>', s):
    out.append(s[pos:m.start()])
    pos = m.end()
    tag = m.group(0)
    closing, name = m.group(1), m.group(2)
    if name == 'g':
        if closing:
            stack.pop()
            gids.pop()
        else:
            t = re.search(r'transform="translate\((%s)[ ,]+(%s)\)"' % (NUM, NUM), tag)
            base = stack[-1] if stack else (0.0, 0.0)
            stack.append((base[0] + float(t.group(1)), base[1] + float(t.group(2))) if t else base)
            gid = re.search(r'id="([^"]+)"', tag)
            gids.append(gid.group(1) if gid else '')
            if m.group(4):
                gids.pop()
            if m.group(4):
                stack.pop()
        out.append(tag)
        continue
    if name == 'clipPath':
        clip = None if closing else re.search(r'id="([^"]+)"', tag).group(1)
        out.append(tag)
        continue
    if closing or name in ('svg', 'defs', 'filter', 'feGaussianBlur', 'feDropShadow', 'title', 'clipPath', 'tspan'):
        out.append(tag)
        continue
    ox, oy = stack[-1] if stack else (0.0, 0.0)
    if name in ('polygon', 'path') and any(g.startswith(('L03', 'coast_rocks', 'outcrop', 'islet')) for g in gids):
        nums = [float(v) for v in re.findall(NUM, (re.search(r'(?:points|\sd)="([^"]*)"', tag) or re.search('()', '')).group(1))]
        if len(nums) >= 4:
            vs = [to_m(x_ + ox, y_ + oy) for x_, y_ in zip(nums[0::2], nums[1::2])]
            if any(x_ > 890 and 505 < y_ < 548 or 890 < x_ < 950 and y_ > 505 for x_, y_ in vs) and not any(g == 'coast_rocks_island' for g in gids):
                continue                                  # береговые камни в полосе подъёма Порта растянулись бы — рисуем заново
    if clip:
        ox, oy = CLIP_OFS.get(clip, (0.0, 0.0))
    if name in ('polygon', 'polyline'):
        tag = re.sub(r'points="([^"]*)"', lambda q: 'points="%s"' % warp_pairs(q.group(1), ox, oy), tag)
        if name == 'polyline':
            tag = road_fix(tag, ox, oy, gids)
            if tag is None:
                continue
    elif name == 'path':
        tag = re.sub(r'\sd="([^"]*)"', lambda q: ' d="%s"' % warp_pairs(q.group(1), ox, oy), tag)
    elif name in ('circle', 'ellipse'):
        X, Y = warp_u(attr(tag, 'cx') + ox, attr(tag, 'cy') + oy)
        tag = set_attr(set_attr(tag, 'cx', X - ox), 'cy', Y - oy)
    elif name == 'text':
        X, Y = warp_u(attr(tag, 'x') + ox, attr(tag, 'y') + oy)
        tag = set_attr(set_attr(tag, 'x', X - ox), 'y', Y - oy)
    elif name == 'rect':
        x, y, w, h = attr(tag, 'x'), attr(tag, 'y'), attr(tag, 'width'), attr(tag, 'height')
        if w >= 7000:                                   # фон и рамки: на весь новый холст
            gx, gy = GROW_X * 5, GROW_Y * 5
            tag = set_attr(set_attr(set_attr(set_attr(tag, 'x', x), 'y', y - gy), 'width', w + gx), 'height', h + gy)
        else:
            X0, Y0 = warp_u(x + ox, y + oy)
            X1, Y1 = warp_u(x + w + ox, y + h + oy)
            if abs((X1 - X0) - w) < 2 and abs((Y1 - Y0) - h) < 2:
                X1, Y1 = X0 + w, Y0 + h
            tag = set_attr(set_attr(set_attr(set_attr(tag, 'x', X0 - ox), 'y', Y0 - oy), 'width', X1 - X0), 'height', Y1 - Y0)
    elif name == 'image':
        tag = stretch_image(tag, ox, oy)
    out.append(tag)
out.append(s[pos:])
s = ''.join(out)

# холст
s = s.replace('width="7370" height="4200" viewBox="-350 -700 7370 4200"',
              'width="%d" height="%d" viewBox="-350 %d %d %d"' % (7370 + GROW_X * 5, 4200 + GROW_Y * 5, -700 - GROW_Y * 5, 7370 + GROW_X * 5, 4200 + GROW_Y * 5), 1)

# заголовок — к новому верхнему краю
def lift_title(g):
    return re.sub(r'(<(?:rect|text)\b[^>]*?\sy=")(%s)(")' % NUM,
                  lambda q: q.group(1) + f1(float(q.group(2)) - GROW_Y * 5) + q.group(3)
                  if float(q.group(2)) < -400 and 'x="-348"' not in q.group(0) and 'x="-314"' not in q.group(0) else q.group(0), g)


a = s.index('<g id="L12_title_legend"')
s = s[:a] + lift_title(s[a:])

# ---------------------------------------------------------------- гряды, лес, скалы, дороги в полосах
import random
rnd = random.Random(23)
# (имя, гребень [(x, y)], полуширина, высота над соседями, подпись)
RIDGES = [
    ('A', [(430, 290), (428, 360), (433, 430), (428, 500), (436, 570), (452, 630)], 46, 22),
    ('B', [(762, 112), (752, 200), (745, 290), (742, 380), (748, 450), (762, 505)], 58, 30),
    ('RD', [(690, 534), (800, 532), (900, 536), (1000, 528), (1080, 520), (1140, 515)], 34, 24),
    ('C', [(1060, 548), (1120, 562), (1180, 590), (1228, 628), (1256, 662)], 66, 28),
    ('NE', [(1000, 772), (1050, 798), (1105, 818), (1150, 840)], 42, 18),
    ('N', [(560, 834), (680, 840), (800, 838), (930, 832), (990, 822)], 20, 10),
]
def coast_y(x):
    return 852 + 9 * math.sin(x / 41.0) + 6 * math.sin(x / 13.0 + 1.3) if 500 <= x <= 1200 else 9999


NEWROADS = [ROAD_A, ROAD_B, ROAD_C]
KEEP_CLEAR = NEWROADS + [[(976, 574), (1158, 738)]]                 # и дорога Неблагополучный -> Порт
_l5 = s[s.index('<g id="L05_roads"'):s.index('<g id="L05b_bridges"')]
for _pl in re.findall(r'<polyline[^>]*stroke="#E5D2A4"[^>]*/>', _l5):                  # и грунтовки
    _n = [float(v) for v in re.findall(NUM, re.search(r'points="([^"]*)"', _pl).group(1))]
    KEEP_CLEAR.append([to_m(x_, y_) for x_, y_ in zip(_n[0::2], _n[1::2])])


def seg_d(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1)))
    return math.hypot(a[0] + ax * t - p[0], a[1] + ay * t - p[1])


def pl_d(p, pl):
    return min(seg_d(p, a, b) for a, b in zip(pl[:-1], pl[1:]))


def buffer_poly(crest, hw, seed):
    c = chaikin(crest, 3)
    rr = random.Random(seed)
    ph = [rr.uniform(0, 6.28) for _ in range(3)]
    def w(i, side):
        t = i / (len(c) - 1)
        return hw * (0.75 + 0.18 * math.sin(t * 9 + ph[0] + side) + 0.1 * math.sin(t * 23 + ph[1])) * (0.55 + 0.45 * math.sin(math.pi * min(1, max(0, t * 1.0))) ** .35)
    left, right = [], []
    for i, p in enumerate(c):
        a, b = c[max(0, i - 1)], c[min(len(c) - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        left.append((p[0] + nx * w(i, 0), p[1] + ny * w(i, 0)))
        right.append((p[0] - nx * w(i, 1.7), p[1] - ny * w(i, 1.7)))
    def cap(p, q, d):
        cx, cy = p
        a0 = math.atan2(q[1] - cy, q[0] - cx)
        return [(cx + d * math.cos(a0 + k * math.pi / 8), cy + d * math.sin(a0 + k * math.pi / 8)) for k in range(1, 8)]
    e0 = c[-1]
    return left + cap(e0, left[-1], math.hypot(left[-1][0] - e0[0], left[-1][1] - e0[1])) + right[::-1] +         cap(c[0], right[0], math.hypot(right[0][0] - c[0][0], right[0][1] - c[0][1]))


def ptxt(pts):
    return ' '.join('%s,%s' % tuple(f1(v) for v in to_u(*p)) for p in pts)


HILLS = ['<g id="R23_ridges">']
TREES = ['<g id="R23_forest" filter="url(#tshadow)">']
ROCKS = ['<g id="R23_rocks">']
for k, (nm, crest, hw, hgt) in enumerate(RIDGES):
    for lvl in range(4):
        f = 1 - lvl * 0.23
        poly = buffer_poly(crest, hw * f, k * 10 + lvl)
        HILLS.append('<polygon points="%s" fill="%s" fill-opacity="%.2f" stroke="#AFC197" stroke-width="2" stroke-opacity="0.55" filter="url(#soft_s)"/>'
                     % (ptxt(poly), ('#C9D6B4', '#BFD0A8', '#B4C79C', '#A9BE91')[lvl], 0.55 + lvl * 0.1))
    cc = chaikin(crest, 3)
    # лес: плотный на склонах, поляна у видовой точки, просеки у дорог
    xs = [p[0] for p in cc]; ys = [p[1] for p in cc]
    for _ in range(int(hw * sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(cc[:-1], cc[1:])) / 26)):
        p = (rnd.uniform(min(xs) - hw, max(xs) + hw), rnd.uniform(min(ys) - hw, max(ys) + hw))
        d = pl_d(p, cc)
        if d > hw * 0.82 or any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR) or p[1] > coast_y(p[0]) - 7 or p[0] > 1110 and p[1] > 790:
            continue
        if any(math.hypot(p[0] - v[0], p[1] - v[1]) < 30 for v in VIEWS.values()):
            continue
        rr_ = rnd.uniform(9, 14.5)
        col = rnd.choice(('#7FA36A', '#86A971', '#93B47B', '#8AAE74', '#9DBB83'))
        TREES.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>' % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rr_), col))
    # скалы у гребня
    for j in range(len(cc) // 9):
        q = cc[rnd.randrange(len(cc))]
        if any(pl_d(q, r_) < 14 for r_ in NEWROADS):
            continue
        n = rnd.randint(6, 9)
        R = rnd.uniform(4, 8)
        pts = [(q[0] + R * (0.7 + 0.5 * rnd.random()) * math.cos(t * 6.283 / n), q[1] + R * 0.8 * (0.7 + 0.5 * rnd.random()) * math.sin(t * 6.283 / n)) for t in range(n)]
        ROCKS.append('<polygon points="%s" fill="#C4C5B7" stroke="#8E938A" stroke-width="2" stroke-linejoin="round"/>' % ptxt(pts))
    mid = cc[len(cc) // 2]
    HILLS.append('<text x="%s" y="%s" font-size="30" font-style="italic" fill="#6E8259" text-anchor="middle">+%d m</text>' % (f1(to_u(*mid)[0]), f1(to_u(*mid)[1] + 70), hgt))
HILLS.append('</g>'); TREES.append('</g>'); ROCKS.append('</g>')

ROADS = ['<g id="R23_roads">']
_l5a = s.index('<g id="L05_roads"'); _l5b = s.index('<g id="L05b_bridges"')
for _pl in re.findall(r'<polyline[^>]*stroke="#(?:BEB18F|E5D2A4)"[^>]*/>', s[_l5a:_l5b]):   # грунтовки через гряду A — поверх гряды
    _xs = [(float(v) + 350) / 5 for v in re.findall(NUM, re.search(r'points="([^"]*)"', _pl).group(1))[0::2]]
    if _xs and min(_xs) < 400 and max(_xs) > 470:
        ROADS.append(_pl)
ROADS.sort(key=lambda t: 0 if 'BEB18F' in t else 1 if 'E5D2A4' in t else 2)
for rd in NEWROADS[::2]:                                         # A и C — новые; B уже вписана в главную дорогу
    for col, w in (('#D3D2C3', 46), ('#5F666C', 32)):
        ROADS.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="round" stroke-linecap="round"/>' % (ptxt(rd), col, w))
for nm, v in VIEWS.items():
    X, Y = to_u(*v)
    ROADS.append('<circle cx="%s" cy="%s" r="20" fill="#FFFFFF" stroke="#34424B" stroke-width="4"/><circle cx="%s" cy="%s" r="7" fill="#34424B"/>'
                 '<text x="%s" y="%s" font-size="26" font-weight="bold" fill="#34424B">VIEW %s</text>' % (f1(X), f1(Y), f1(X), f1(Y), f1(X + 28), f1(Y - 22), nm))
ROADS.append('</g>')

# северный берег над Неблагополучным: холст вырос на 150 м — там море, берег с камнями, лес по гряде
coast = [(x, 852 + 9 * math.sin(x / 41.0) + 6 * math.sin(x / 13.0 + 1.3)) for x in range(500, 1200, 6)]
SEA_N = '<polygon points="%s" fill="#ABD3E1"/>' % ptxt([(500, 1000)] + coast + [(1200, 1000)])
for x, y in coast[::3]:
    n = rnd.randint(6, 8); R = rnd.uniform(3, 6)
    ROCKS.insert(-1, '<polygon points="%s" fill="#C4C5B7" stroke="#8E938A" stroke-width="2" stroke-linejoin="round"/>'
                 % ptxt([(x + R * (0.7 + 0.5 * rnd.random()) * math.cos(t * 6.283 / n), y - 2 + R * 0.8 * math.sin(t * 6.283 / n)) for t in range(n)]))
s = s.replace('<g id="L02_mountains"', SEA_N + '<g id="L02_mountains"', 1)
# скалы обрыва вдоль карниза (со стороны моря)
for i in range(4, len(ROAD_C) - 4, 2):
    a_, b_ = ROAD_C[i - 1], ROAD_C[i + 1]
    dx_, dy_ = b_[0] - a_[0], b_[1] - a_[1]; L_ = math.hypot(dx_, dy_) or 1
    q = (ROAD_C[i][0] + dy_ / L_ * rnd.uniform(14, 22), ROAD_C[i][1] - dx_ / L_ * rnd.uniform(14, 22))
    n = rnd.randint(6, 9); R = rnd.uniform(5, 9)
    ROCKS.insert(-1, '<polygon points="%s" fill="#C4C5B7" stroke="#8E938A" stroke-width="2" stroke-linejoin="round"/>'
                 % ptxt([(q[0] + R * (0.7 + 0.5 * rnd.random()) * math.cos(t * 6.283 / n), q[1] + R * 0.8 * math.sin(t * 6.283 / n)) for t in range(n)]))
HILLS_A = [h for h in HILLS if h.startswith('<polygon')][:4]           # гряда A ещё раз поверх плана Хутора (его фон закрывает)
_d2 = s.index('<g id="D02"')
_im = s.index('/>', s.index('<image', _d2)) + 2                       # сразу после картинки Хутора: грунтовки остаются поверх
s = s[:_im] + '<g id="R23_ridge_A_over">' + ''.join(HILLS_A) + '</g>' + s[_im:]
s = s.replace('<g id="L04_water"', ''.join(HILLS) + ''.join(ROCKS) + '<g id="L04_water"', 1)
s = s.replace('<g id="L08_vegetation"', ''.join(ROADS) + '<g id="L08_vegetation"', 1)
s = s.replace('<g id="R18_plans"', ''.join(TREES) + '<g id="R18_plans"', 1)
s = s.replace('World map v22 · 16.10.2026 ·', 'World map v23 · 16.10.2026 · districts spread for 3 scenic views ·')

open(SVG_OUT, 'w', encoding='utf-8').write(s)
print('svg ok', len(s))

if __name__ == '__main__' and os.environ.get('NORENDER') != '1':
    html = os.path.join(OUTD, '_v23_render.html')
    open(html, 'w', encoding='utf-8').write('<html><head><meta charset="utf-8"></head><body style="margin:0">' + s + '</body></html>')
    chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    W, H = int(7370 + GROW_X * 5), int(4200 + GROW_Y * 5)
    subprocess.run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
                    '--screenshot=' + PNG_OUT, '--window-size=%d,%d' % (W, H), 'file:///' + html.replace(chr(92), '/')],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(html)
    im = Image.open(PNG_OUT)
    im.resize((W // 5, H // 5), Image.LANCZOS).save(PRE_OUT)
    print('ok', im.size)
