"""Общая карта v28 (TASK-000680, Вадим): v27 +
  - Стройка — длинная полоса вдоль дороги Хутор -> Неблагополучный (справа от неё), повёрнута по дороге (27°);
    планировка переложена: постройки и техника группами переставлены по полосе (без искажения), грунт растянут;
  - верх острова: за горами и над Неблагополучным — море и скалистый берег;
  - подписи видов и высот в отдельной группе (в чистом рендере для макета их нет).
Ранее v27 (TASK-000679, Вадим): v25 +
  - дорога Хутор -> Неблагополучный выше по карте: заходит в середину западной стороны района и поворачивает направо
    (внутрь района), Стройка (меньше, 0.8) стоит справа от неё; холм VIEW H (+35 м) свободный, через него дорога в город;
  - Порт горизонтальный (1.25 x 0.8), правая сторона слегка выпуклая; карниз C вливается в дорогу через середину Порта
    (из Неблагополучного к мосту на Трамдуро); Трамдуро на 20 м правее.
Ранее v25 (TASK-000675, Вадим): v24 +
  - Порт и Стройка не прямоугольники: другой контур (Порт — скошенные стороны и пирс в бухту, Стройка — неправильный
    многоугольник с забором), Стройка ниже (на 60 м) на холме прямо у дороги Хутор -> Неблагополучный;
  - Порт и Трамдуро ещё на 40 м правее; карниз C заходит в южные ворота Порта.
Ранее v24 (TASK-000671, Вадим): от v22, вариант «одна большая гора»:
  - Стройка переезжает на север (к Неблагополучному, южнее гор); на её старом месте между Хутором и Даунтауном —
    большая живописная гора H (+40 м), главная дорога Хутор -> Даунтаун переваливает её: с плеча видно и долину
    Хутора, и весь город;
  - Неблагополучный правее (+150 м) и чуть выше (+45 м), ближе к Порту; между ним и Даунтауном большая гора RD;
  - Порт с Трамдуро — вместе с Неблагополучным (+150, +45), т. е. ниже, чем в v23;
  - карниз C: от северо-восточного угла Даунтауна к Порту, выгнут влево (вглубь суши) вокруг бухточки, гора-мыс слева;
  - даунтаун, пляж, Элитный холм +80 м на восток (растяжение в полосе x 575-615).
Деформация MASTER_v22.svg (как v23): постоянный сдвиг внутри районов, растяжение между ними; Стройка — жёсткий перенос
группы D03. Все дороги, которые будут в итоге, нарисованы и соединены."""
import math
import os
import random
import re
import subprocess
from urllib.parse import unquote

from PIL import Image

MAP = r'C:\Users\chern_0eqkb03\Desktop\Map'
OUTD = os.path.join(MAP, 'Итоговая карта')
ASSETS = os.path.join(MAP, '00_Сборка_общей_карты', 'v28_assets')
SRC = os.path.join(OUTD, 'VOLUNTEERS_MAP_MASTER_v22.svg')
SVG_OUT = os.path.join(OUTD, 'VOLUNTEERS_MAP_MASTER_v28.svg')
PNG_OUT = os.path.join(OUTD, 'VOLUNTEERS_MAP_FINAL_v28.png')
PRE_OUT = os.path.join(OUTD, 'VOLUNTEERS_MAP_PREVIEW_v28.png')
Image.MAX_IMAGE_PIXELS = None
os.makedirs(ASSETS, exist_ok=True)

GROW_X, GROW_Y = 210.0, 55.0
CONSTR_OLD = (425, 330, 560, 485)                  # Стройка в v22 (x0, y0, x1, y1)
CONSTR_D = (70.0, 85.0)                            # перенос Стройки, м -> (495..630, 415..570): на холме слева от дороги через VIEW H


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def warp_m(x, y):
    """Метры мира v22 -> v24."""
    if y >= 838:                                    # верхний край холста тянется к новому краю
        y2 = y + GROW_Y + 10
    else:
        y2 = None
    sy = r(y, 505, 575 - 35 * r(x, 880, 940))       # юг (Даунтаун и всё южнее) -> север (Неблагополучный, Порт)
    rn = r(x, 520, 545)
    dx = (1 - sy) * 80 * r(x, 575, 615) + sy * (150 * rn + 40 * r(x, 900, 945) + 20 * r(x, 1088, 1110))   # Порт +190, мост и Трамдуро +210
    dy = 45 * sy * rn
    return x + dx, (y2 if y2 is not None else y + dy)


def to_m(px, py):
    return (px + 350) / 5.0, (3500 - py) / 5.0


def to_u(xm, ym):
    return xm * 5 - 350, 3500 - ym * 5


def warp_u(px, py):
    return to_u(*warp_m(*to_m(px, py)))


NUM = r'-?\d+(?:\.\d+)?(?:e-?\d+)?'


def f1(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def warp_pairs(txt, ox, oy):
    out, pos = [], 0
    for m in re.finditer(r'(%s)(\s*,\s*|\s+)(%s)' % (NUM, NUM), txt):
        out.append(txt[pos:m.start()])
        X, Y = warp_u(float(m.group(1)) + ox, float(m.group(3)) + oy)
        out.append(f1(X - ox) + m.group(2) + f1(Y - oy))
        pos = m.end()
    out.append(txt[pos:])
    return ''.join(out)


def pairs_m(txt, ox, oy):
    n = [float(v) for v in re.findall(NUM, txt)]
    return [to_m(x + ox, y + oy) for x, y in zip(n[0::2], n[1::2])]


def attr(tag, name):
    m = re.search(r'\s%s="(%s)"' % (name, NUM), tag)
    return float(m.group(1)) if m else None


def set_attr(tag, name, val):
    return re.sub(r'(\s%s=")(%s)(")' % (name, NUM), lambda m: m.group(1) + f1(val) + m.group(3), tag, count=1)


def chaikin(p, n=3):
    for _ in range(n):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            q += [(a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25), (a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75)]
        q.append(p[-1])
        p = q
    return p


def seg_d(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1)))
    return math.hypot(a[0] + ax * t - p[0], a[1] + ay * t - p[1])


def pl_d(p, pl):
    return min(seg_d(p, a, b) for a, b in zip(pl[:-1], pl[1:]))


def inside(p, poly):
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < (x2 - x1) * (p[1] - y1) / (y2 - y1) + x1:
            c = not c
    return c


# ---------------------------------------------------------------- новое (метры мира v24)
CONSTR_NEW = (CONSTR_OLD[0] + CONSTR_D[0], CONSTR_OLD[1] + CONSTR_D[1], CONSTR_OLD[2] + CONSTR_D[0], CONSTR_OLD[3] + CONSTR_D[1])
VIEWS = {'H': (545, 394), 'C': (1134, 532)}
# главная дорога Хутор -> Даунтаун через гору H (от моста у ущелья до западного въезда в Даунтаун x 726)
ROAD_H = [(426, 348), (450, 349)] + chaikin([(462, 349.5), (473, 350), (492, 356), (510, 368), (527, 382), VIEWS['H'],
                                             (565, 392), (582, 384), (600, 372), (618, 361), (640, 353), (668, 349.5)])[1:-1] + [(695, 348), (726, 348)]
ROAD_VALLEY = [(473, 350), (473, 322)]                            # к Тихой долине (дальше старый мост и дорога)
# карниз: от северо-восточного угла Даунтауна, выгнут влево вокруг бухточки, к южным воротам Порта
ROAD_C = chaikin([(1162, 438), (1159, 462), (1150, 485), (1139, 508), VIEWS['C'], (1142, 556), (1162, 572), (1184, 582),
                  (1198, 596), (1203, 616), (1203, 633)])          # до середины Порта, на дорогу Неблагополучный -> мост на Трамдуро
# Хутор -> Неблагополучный: выше по карте, в середину западной стороны района, там поворот направо (внутрь района)
ROAD_R = chaikin([(425, 574), (440, 588), (458, 606), (478, 625), (500, 645), (525, 664), (552, 682), (582, 699), (614, 712),
                  (648, 723), (678, 731), (706, 736)]) + [(716, 736), (726, 736)]
ROAD_RING = [(706, 736), (706, 660)]                              # от въезда вниз к западной стороне кольца района
ROAD_CONSTR = [(0.0, 0.0), (0.0, 0.0)]                           # ворота Стройки (задаются ниже, после контура)
NEWROADS = [ROAD_H, ROAD_VALLEY, ROAD_C, ROAD_CONSTR, ROAD_R, ROAD_RING]
# горы: (имя, гребень, полуширина, высота)
MOUNTS = [
    ('H', [(530, 332), (545, 400), (560, 460), (574, 505)], 72, 35),
    ('NW', [(500, 728), (568, 768), (640, 800)], 32, 18),
    ('RD', [(692, 578), (722, 562), (800, 568), (880, 569), (960, 563), (1040, 556), (1105, 546)], 50, 35),
]
COVE = None                                                       # бухточка у карниза — вычисляется ниже


def _cove():
    pts = []
    for i in range(1, len(ROAD_C) - 1):
        a, b = ROAD_C[i - 1], ROAD_C[i + 1]
        p = ROAD_C[i]
        if not 488 < p[1] < 580:
            continue
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        off = 15 + 4 * math.sin(i * 0.7)
        pts.append((p[0] + dy / L * off, p[1] - dx / L * off))
    return pts + [(1290, pts[-1][1] - 6), (1290, pts[0][1] + 6)]


COVE = _cove()


def in_mount_core(p):
    return any(pl_d(p, crest) < hw * 0.8 for _, crest, hw, _ in MOUNTS)


def in_constr(p):
    return inside(p, CONSTR_POLY) or pl_d(p, CONSTR_POLY + CONSTR_POLY[:1]) < 6


# контур Стройки (локальные единицы группы D03: прямоугольник был 74..790 x 60..850)
CONSTR_CLIP_LOCAL = [(105, 200), (430, 93), (716, 260), (692, 693), (290, 694), (105, 560)]
CONSTR_LC = (410.0, 393.0)                                        # центр содержимого (локальные единицы D03)
CONSTR_SXY = (1.15, 0.62)                                         # полоса: вдоль дороги шире, поперёк уже
CONSTR_ROT = 27.0                                                 # по направлению дороги (против часовой)
CONSTR_G = (606.0, 649.0)                                         # центр полосы, м
CONSTR_CLIP_LOCAL = [(60, 236), (92, 205), (728, 205), (760, 236), (752, 330), (690, 440), (560, 545), (410, 590), (262, 560),
                     (140, 480), (75, 380)]


def constr_world(lx, ly):
    a = math.radians(-CONSTR_ROT)
    vx, vy = lx - CONSTR_LC[0], ly - CONSTR_LC[1]
    gx, gy = to_u(*CONSTR_G)
    return to_m(gx + vx * math.cos(a) - vy * math.sin(a), gy + vx * math.sin(a) + vy * math.cos(a))


CONSTR_POLY = [constr_world(x, y) for x, y in CONSTR_CLIP_LOCAL]
_gate = constr_world(410, 205)
ROAD_CONSTR[:] = [_gate, (_gate[0] - 0.454 * 18, _gate[1] + 0.891 * 18)]   # ворота Стройки на дорогу в Неблагополучный
CONSTR_BOX = (min(p[0] for p in CONSTR_POLY), min(p[1] for p in CONSTR_POLY), max(p[0] for p in CONSTR_POLY), max(p[1] for p in CONSTR_POLY))
CONSTR_LABEL_D = (112.0, 104.0)                                   # подпись Стройки — под её юго-западным концом
# Порт: масштаб вокруг центра, контур в итоговых координатах
PORT_C = (1201.0, 636.0)
PORT_SCALE = (1.25, 0.8)
PORT_SHAPE = [(1118, 672), (1116, 611), (1131, 599), (1260, 598), (1281, 609), (1292, 637), (1284, 664), (1265, 677), (1131, 679)]


def port_pre(p):
    return PORT_C[0] + (p[0] - PORT_C[0]) / PORT_SCALE[0], PORT_C[1] + (p[1] - PORT_C[1]) / PORT_SCALE[1]
# контур Порта (метры v25): скошенные углы; пирс отдельно
PORT_SHIFT = (190.0, 45.0)
PORT_POLY = [(1134, 686), (1134, 622), (1156, 587), (1236, 586), (1268, 606), (1270, 662), (1252, 686)]
PIER = [(1214, 677), (1238, 677), (1240, 714), (1230, 721), (1218, 716)]
ROUGH_LABEL_D = (235.0, 50.0)                                    # подпись Неблагополучного — к его новому углу


def old_rough_label(p):
    return 455 <= p[0] <= 620 and 800 <= p[1] <= 832


def old_in_constr(p):
    x0, y0, x1, y1 = CONSTR_OLD
    return x0 - 2 <= p[0] <= x1 + 2 and y0 - 2 <= p[1] <= y1 + 2


# ---------------------------------------------------------------- растровые вставки
def place_image(tag, ox, oy):
    x, y, w, h = attr(tag, 'x') + ox, attr(tag, 'y') + oy, attr(tag, 'width'), attr(tag, 'height')
    xm0, xm1 = to_m(x, 0)[0], to_m(x + w, 0)[0]
    ym0, ym1 = to_m(0, y + h)[1], to_m(0, y)[1]
    href = re.search(r'href="file:///([^"]+)"', tag)
    if href and xm0 < 423 < xm1 < 460:                          # план Хутора: в растре был кусок Стройки — убрать
        srcf = unquote(href.group(1)).replace('/', os.sep)
        im = Image.open(srcf).convert('RGBA')
        cut = int((423 - xm0) / (xm1 - xm0) * im.width)
        a = im.getchannel('A')
        a.paste(0, (cut, 0, im.width, im.height))
        im.putalpha(a)
        dst = os.path.join(ASSETS, 'C_' + os.path.basename(srcf))
        im.save(dst)
        tag = tag.replace(href.group(1), dst.replace(os.sep, '/'))
    if href and xm0 < 520 < xm1 and ym1 > 575:                  # план через полосу растяжения на севере — по столбцам
        srcf = unquote(href.group(1)).replace('/', os.sep)
        im = Image.open(srcf).convert('RGBA')
        sc = im.width / w
        yc = to_m(0, y + h / 2)[1]
        X0, X1 = warp_u(x, y + h / 2)[0], warp_u(x + w, y + h / 2)[0]
        nw = int(round((X1 - X0) * sc))
        out = Image.new('RGBA', (nw, im.height))
        fw = [warp_m(to_m(x + i / sc, 0)[0], yc)[0] for i in range(im.width + 1)]
        k = 0
        for c in range(nw):
            X = to_m(X0 + (c + .5) / sc, 0)[0]
            while k < len(fw) - 2 and fw[k + 1] < X:
                k += 1
            out.paste(im.crop((min(im.width - 1, k), 0, min(im.width - 1, k) + 1, im.height)), (c, 0))
        dst = os.path.join(ASSETS, 'W_' + os.path.basename(srcf))
        out.save(dst)
        tag = tag.replace(href.group(1), dst.replace(os.sep, '/'))
        Y0 = warp_u(x, y + h / 2)[1] - h / 2
        return set_attr(set_attr(set_attr(tag, 'x', X0 - ox), 'width', X1 - X0), 'y', Y0 - oy)
    cx, cy = x + w / 2, y + h / 2
    X, Y = warp_u(cx, cy)
    if href and 900 < xm0 < 930 and 1100 < xm1 < 1125:                  # план Порта: контур не прямоугольный
        from PIL import ImageChops, ImageDraw, ImageFilter
        srcf = unquote(href.group(1)).replace('/', os.sep)
        im = Image.open(srcf).convert('RGBA')
        sc = im.width / w
        pc = to_u(*PORT_C)
        wx0, wy0 = X - w / 2, Y - h / 2                                    # картинка после сдвига (+190, +45)
        nx0, ny0 = pc[0] + (wx0 - pc[0]) * PORT_SCALE[0], pc[1] + (wy0 - pc[1]) * PORT_SCALE[1]
        nw_, nh_ = w * PORT_SCALE[0], h * PORT_SCALE[1]
        im = im.resize((int(round(im.width * PORT_SCALE[0])), int(round(im.height * PORT_SCALE[1]))), Image.LANCZOS)
        mk = Image.new('L', im.size, 0)
        ImageDraw.Draw(mk).polygon([((to_u(*p)[0] - nx0) * sc, (to_u(*p)[1] - ny0) * sc) for p in PORT_SHAPE], fill=255)
        mk = mk.filter(ImageFilter.GaussianBlur(2))
        im.putalpha(ImageChops.multiply(im.getchannel('A'), mk))
        dst = os.path.join(ASSETS, 'P_' + os.path.basename(srcf))
        im.save(dst)
        tag = tag.replace(href.group(1), dst.replace(os.sep, '/'))
        tag = set_attr(set_attr(tag, 'width', nw_), 'height', nh_)
        return set_attr(set_attr(tag, 'x', nx0 - ox), 'y', ny0 - oy)
    return set_attr(set_attr(tag, 'x', x + X - cx - ox), 'y', y + Y - cy - oy)


# ---------------------------------------------------------------- дороги: что убрать / заменить
def drop_polyline(gids, pts_old):
    """Старые дороги, которых больше нет (по координатам v22)."""
    xs, ys = [p[0] for p in pts_old], [p[1] for p in pts_old]
    if 'R18_links' in gids and abs(pts_old[0][0] - 1082) < 3 and abs(pts_old[0][1] - 438) < 3:
        return True                                    # старый карниз v22
    if min(xs) > 548 and max(xs) < 568 and max(ys) - min(ys) > 40 and min(ys) > 340:
        return True                                    # Стройка -> Неблагополучный по x 556-563 (Стройки там больше нет)
    if min(xs) >= 565 and max(xs) <= 650 and all(340 < v < 356 for v in ys):
        return True                                    # главная Стройка -> Даунтаун (заменена дорогой через гору H)
    if abs(pts_old[0][0] - 425) < 2 and abs(pts_old[0][1] - 574) < 2 and max(xs) < 540:
        return True                                    # старая Хутор -> Неблагополучный (заменена дорогой мимо Стройки)
    if 'd03_roads' in gids or 'd03_terrain' in gids:
        return True                                    # дороги и река внутри плана Стройки (план переезжает без них)
    return False


# ---------------------------------------------------------------- проход по тегам
s = open(SRC, encoding='utf-8').read()


def _bbox(tag, name):
    if name == 'circle':
        cx, cy, rr = attr(tag, 'cx'), attr(tag, 'cy'), attr(tag, 'r') or 1
        return cx - rr, cy - rr, cx + rr, cy + rr
    if name == 'text':
        return attr(tag, 'x') - 10, attr(tag, 'y') - 10, attr(tag, 'x') + 10, attr(tag, 'y') + 10
    if name == 'rect':
        x, y = attr(tag, 'x'), attr(tag, 'y')
        return x, y, x + attr(tag, 'width'), y + attr(tag, 'height')
    src = re.search(r'(?:points|\sd)="([^"]*)"', tag)
    if not src:
        return None
    n = [float(v) for v in re.findall(NUM, src.group(1))]
    return min(n[0::2]), min(n[1::2]), max(n[0::2]), max(n[1::2])


# Стройка: элементы зданий, техники и номеров — кластерами по пересечению рамок; каждый кластер переставляется целиком
_d0, _d1 = s.index('<g id="D03"'), s.index('<g id="D09"')
_items, _grp = [], []
for q in re.finditer(r'<(/?)(\w+)([^>]*?)(/?)>', s[_d0:_d1]):
    cl, nm, tg = q.group(1), q.group(2), q.group(0)
    if nm == 'g':
        if cl:
            _grp.pop()
        else:
            gi = re.search(r'id="([^"]+)"', tg)
            _grp.append(gi.group(1) if gi else '')
            if q.group(4):
                _grp.pop()
        continue
    if cl or nm in ('clipPath', 'defs', 'tspan'):
        continue
    sub = next((g for g in reversed(_grp) if g.startswith('d03_')), '')
    bb = _bbox(tg, nm)
    if bb:
        _items.append((_d0 + q.start(), sub, bb))
_par = list(range(len(_items)))


def _find(i):
    while _par[i] != i:
        _par[i] = _par[_par[i]]
        i = _par[i]
    return i


_movable = [i for i, (_, sub, _) in enumerate(_items) if sub in ('d03_buildings', 'd03_objects', 'd03_numbers')]
for ai in range(len(_movable)):
    a_ = _items[_movable[ai]][2]
    for bi in range(ai + 1, len(_movable)):
        b_ = _items[_movable[bi]][2]
        if a_[0] - 2 <= b_[2] and b_[0] - 2 <= a_[2] and a_[1] - 2 <= b_[3] and b_[1] - 2 <= a_[3]:
            _par[_find(_movable[ai])] = _find(_movable[bi])
_cl = {}
for i in _movable:
    _cl.setdefault(_find(i), []).append(i)
RELAYOUT = {}
for root, members in _cl.items():
    x0 = min(_items[i][2][0] for i in members); y0 = min(_items[i][2][1] for i in members)
    x1 = max(_items[i][2][2] for i in members); y1 = max(_items[i][2][3] for i in members)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d = (CONSTR_LC[0] + (cx - CONSTR_LC[0]) * CONSTR_SXY[0] - cx, CONSTR_LC[1] + (cy - CONSTR_LC[1]) * CONSTR_SXY[1] - cy)
    for i in members:
        RELAYOUT[_items[i][0]] = d
for off, sub, bb in _items:
    if sub == 'd03_trees':
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        RELAYOUT[off] = (CONSTR_LC[0] + (cx - CONSTR_LC[0]) * CONSTR_SXY[0] - cx, CONSTR_LC[1] + (cy - CONSTR_LC[1]) * CONSTR_SXY[1] - cy)
_MAT = 'matrix(%s 0 0 %s %s %s)' % (CONSTR_SXY[0], CONSTR_SXY[1], f1(CONSTR_LC[0] * (1 - CONSTR_SXY[0])), f1(CONSTR_LC[1] * (1 - CONSTR_SXY[1])))


def relayout(tag, off, gids, name):
    if name in ('clipPath', 'defs', 'tspan') or tag.startswith('</'):
        return tag
    if off in RELAYOUT:
        dx_, dy_ = RELAYOUT[off]
        return tag.replace('<' + name, '<%s transform="translate(%s %s)"' % (name, f1(dx_), f1(dy_)), 1)
    if 'd03_terrain' in gids or 'd03_paths' in gids:
        return tag.replace('<' + name, '<%s transform="%s"' % (name, _MAT), 1)
    return tag
CLIP_OFS = {'clip_d03': (1700.0, 1042.0), 'clip_d05': (2820.0, 1000.0)}
out, pos, stack, clip, gids = [], 0, [], None, []
dropped = {'roads': 0, 'trees': 0, 'rocks': 0}
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
            gid = re.search(r'id="([^"]+)"', tag)
            gid = gid.group(1) if gid else ''
            if gid == 'D03':                            # Стройка: жёсткий перенос всей группы
                tx, ty = float(t.group(1)), float(t.group(2))
                gu = to_u(*CONSTR_G)
                tag = tag.replace(t.group(0), 'transform="translate(%s %s) rotate(%s) translate(%s %s)"' % (
                    f1(gu[0]), f1(gu[1]), f1(-CONSTR_ROT), f1(-CONSTR_LC[0]), f1(-CONSTR_LC[1])))
            if gid == 'D06':                            # Порт: шире и ниже (масштаб вокруг центра)
                cu = to_u(*PORT_C)
                tag = tag.replace('transform="', 'transform="translate(%s %s) scale(%s %s) translate(%s %s) ' % (
                    f1(cu[0]), f1(cu[1]), PORT_SCALE[0], PORT_SCALE[1], f1(-cu[0]), f1(-cu[1])), 1)
            stack.append((base[0] + float(t.group(1)), base[1] + float(t.group(2))) if t else base)
            gids.append(gid)
            if m.group(4):
                gids.pop()
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
    if clip:
        ox, oy = CLIP_OFS.get(clip, (0.0, 0.0))
        if clip == 'clip_d03':                          # клип Стройки: неправильный многоугольник вместо прямоугольника
            out.append('<polygon points="%s"/>' % ' '.join('%s,%s' % p for p in CONSTR_CLIP_LOCAL) if name == 'rect' else tag)
            continue
    in_d03 = 'D03' in gids
    if in_d03 and name != 'polyline':                   # содержимое Стройки: группой + перестановка по полосе
        out.append(relayout(tag, m.start(), gids, name))
        continue
    if name in ('polygon', 'polyline', 'path'):
        src = re.search(r'(?:points|\sd)="([^"]*)"', tag)
        old = pairs_m(src.group(1), ox, oy) if src else []
        if name == 'polyline' and old and drop_polyline(gids, old):
            dropped['roads'] += 1
            continue
        if name == 'polyline' and old and 'D04' in gids and abs(old[0][0] - 500) < 2 and abs(old[0][1] - 611) < 2:
            keep = [p for p in old if p[0] >= 552]               # западный хвост — к новой дороге мимо Стройки
            tag = re.sub(r'points="[^"]*"', 'points="%s"' % ' '.join('%s,%s' % (f1(to_u(*p)[0] - ox), f1(to_u(*p)[1] - oy)) for p in keep), tag, count=1)
        if in_d03:
            out.append(relayout(tag, m.start(), gids, name))
            continue
        if name in ('polygon', 'path') and old and any(g.startswith(('L03', 'coast_rocks', 'outcrop', 'islet')) for g in gids):
            if any(x_ > 880 and 500 < y_ < 545 for x_, y_ in old) and 'coast_rocks_island' not in gids:
                dropped['rocks'] += 1                    # береговые камни в полосе сдвига растянулись бы
                continue
    if name in ('polygon', 'polyline') and 'D06' in gids and re.search(r'points="30,40 690,40 700,520 40,530(?: 30,330)?"', tag):
        ring = [port_pre(p) for p in PORT_SHAPE]                               # площадка Порта: новый контур (до масштаба)
        ring = ring + (ring[:1] if name == 'polyline' else [])
        tag = re.sub(r'points="[^"]*"', 'points="%s"' % ' '.join('%s,%s' % (f1(to_u(*p)[0] - ox), f1(to_u(*p)[1] - oy)) for p in ring), tag, count=1)
        out.append(tag)
        continue
    if name in ('polygon', 'polyline'):
        tag = re.sub(r'points="([^"]*)"', lambda q: 'points="%s"' % warp_pairs(q.group(1), ox, oy), tag)
    elif name == 'path':
        tag = re.sub(r'\sd="([^"]*)"', lambda q: ' d="%s"' % warp_pairs(q.group(1), ox, oy), tag)
    elif name in ('circle', 'ellipse'):
        cx0, cy0 = attr(tag, 'cx') + ox, attr(tag, 'cy') + oy
        if 'L11_labels' in gids and old_in_constr(to_m(cx0, cy0 + 60)):
            X, Y = cx0 + CONSTR_LABEL_D[0] * 5, cy0 - CONSTR_LABEL_D[1] * 5
        elif 'L11_labels' in gids and old_rough_label(to_m(cx0, cy0)):
            X, Y = cx0 + ROUGH_LABEL_D[0] * 5, cy0 - ROUGH_LABEL_D[1] * 5
        else:
            X, Y = warp_u(cx0, cy0)
        if 'L08_vegetation' in gids:
            p = to_m(X, Y)
            if in_mount_core(p) or in_constr(p) or inside(p, COVE) or any(pl_d(p, rd) < 9 for rd in NEWROADS):
                dropped['trees'] += 1
                continue
        tag = set_attr(set_attr(tag, 'cx', X - ox), 'cy', Y - oy)
    elif name == 'text':
        x0, y0 = attr(tag, 'x') + ox, attr(tag, 'y') + oy
        if 'L11_labels' in gids and old_in_constr(to_m(x0, y0 + 60)) and float(attr(tag, 'font-size') or 0) >= 24:
            X, Y = x0 + CONSTR_LABEL_D[0] * 5, y0 - CONSTR_LABEL_D[1] * 5
        elif 'L11_labels' in gids and old_rough_label(to_m(x0, y0)):
            X, Y = x0 + ROUGH_LABEL_D[0] * 5, y0 - ROUGH_LABEL_D[1] * 5
        else:
            X, Y = warp_u(x0, y0)
        tag = set_attr(set_attr(tag, 'x', X - ox), 'y', Y - oy)
    elif name == 'rect':
        x, y, w, h = attr(tag, 'x'), attr(tag, 'y'), attr(tag, 'width'), attr(tag, 'height')
        if w >= 7000:
            gx, gy = GROW_X * 5, GROW_Y * 5
            tag = set_attr(set_attr(set_attr(set_attr(tag, 'x', x), 'y', y - gy), 'width', w + gx), 'height', h + gy)
        else:
            X0, Y0 = warp_u(x + ox, y + oy)
            X1, Y1 = warp_u(x + w + ox, y + h + oy)
            if abs((X1 - X0) - w) < 2 and abs((Y1 - Y0) - h) < 2:
                X1, Y1 = X0 + w, Y0 + h
            tag = set_attr(set_attr(set_attr(set_attr(tag, 'x', X0 - ox), 'y', Y0 - oy), 'width', X1 - X0), 'height', Y1 - Y0)
    elif name == 'image':
        tag = place_image(tag, ox, oy)
    out.append(tag)
out.append(s[pos:])
s = ''.join(out)
print('dropped', dropped)

s = s.replace('width="7370" height="4200" viewBox="-350 -700 7370 4200"',
              'width="%d" height="%d" viewBox="-350 %d %d %d"' % (7370 + GROW_X * 5, 4200 + GROW_Y * 5, -700 - GROW_Y * 5, 7370 + GROW_X * 5, 4200 + GROW_Y * 5), 1)


def fix_title_legend(g):
    g = re.sub(r'(<(?:rect|text)\b[^>]*?\sy=")(%s)(")' % NUM,
               lambda q: q.group(1) + f1(float(q.group(2)) - GROW_Y * 5) + q.group(3)
               if float(q.group(2)) < -400 and 'x="-348"' not in q.group(0) and 'x="-314"' not in q.group(0) else q.group(0), g)
    # легенда, масштаб, стрелка севера (справа внизу) — к новому правому краю (+70 м сверх сдвига Даунтауна)
    def shift(q):
        v = float(q.group(2))
        return q.group(1) + f1(v + 650) + q.group(3) if v > 5000 else q.group(0)
    g = re.sub(r'(\s(?:x|cx|x1|x2)=")(%s)(")' % NUM, shift, g)
    g = re.sub(r'(points=")([^"]*)(")', lambda q: q.group(1) + re.sub(r'(%s)(,)' % NUM, lambda z: (f1(float(z.group(1)) + 650) if float(z.group(1)) > 5000 else z.group(1)) + ',', q.group(2)) + q.group(3), g)
    return g


a = s.index('<g id="L12_title_legend"')
s = s[:a] + fix_title_legend(s[a:])

# ---------------------------------------------------------------- горы, лес, скалы, бухточка, дороги
rnd = random.Random(24)


def buffer_poly(crest, hw, seed):
    """Замкнутая горизонталь: точки на расстоянии ~hw от гребня (лучи из центра гребня, бинарный поиск)."""
    c = chaikin(crest, 3)
    cx = sum(p[0] for p in c) / len(c)
    cy = sum(p[1] for p in c) / len(c)
    rr = random.Random(seed)
    ph = [rr.uniform(0, 6.28) for _ in range(2)]
    pts = []
    for k in range(96):
        a = k * 2 * math.pi / 96
        d = hw * (1 + 0.06 * math.sin(3 * a + ph[0]) + 0.035 * math.sin(7 * a + ph[1]))
        lo, hi = 0.0, 2000.0
        for _ in range(28):
            mid = (lo + hi) / 2
            q = (cx + mid * math.cos(a), cy + mid * math.sin(a))
            if pl_d(q, c) < d:
                lo = mid
            else:
                hi = mid
        pts.append((cx + lo * math.cos(a), cy + lo * math.sin(a)))
    return pts


def ptxt(pts):
    return ' '.join('%s,%s' % tuple(f1(v) for v in to_u(*p)) for p in pts)


def rock(q, R):
    n = rnd.randint(6, 9)
    pts = [(q[0] + R * (0.7 + 0.5 * rnd.random()) * math.cos(t * 6.283 / n), q[1] + R * 0.8 * (0.7 + 0.5 * rnd.random()) * math.sin(t * 6.283 / n)) for t in range(n)]
    return '<polygon points="%s" fill="#C4C5B7" stroke="#8E938A" stroke-width="2" stroke-linejoin="round"/>' % ptxt(pts)


def coast_y(x):
    return 878 + 7 * math.sin(x / 41.0) + 5 * math.sin(x / 13.0 + 1.3) if 540 <= x <= 1060 else 9999


# все дороги, с которых убираем деревья (новые + старые асфальт и грунт после деформации, без групп со сдвигом)
KEEP_CLEAR = list(NEWROADS)
for gname in ('L05_roads', 'D04'):
    a = s.index('<g id="%s"' % gname)
    seg = s[a:a + 400000]
    seg = seg[:seg.index('<g id="', 20)] if '<g id="' in seg[20:] else seg
    for pl in re.findall(r'<polyline[^>]*stroke="#(?:D3D2C3|E5D2A4)"[^>]*/>', seg):
        KEEP_CLEAR.append(pairs_m(re.search(r'points="([^"]*)"', pl).group(1), 0, 0))

HILLS, TREES, ROCKS = ['<g id="R24_mountains">'], ['<g id="R24_forest" filter="url(#tshadow)">'], ['<g id="R24_rocks">']
for k, (nm, crest, hw, hgt) in enumerate(MOUNTS):
    for lvl in range(5):
        f = 1 - lvl * 0.19
        HILLS.append('<polygon points="%s" fill="%s" fill-opacity="%.2f" stroke="#93A979" stroke-width="3" stroke-opacity="0.6"/>'
                     % (ptxt(buffer_poly(crest, hw * f, k * 10 + lvl)), ('#C9D6B4', '#BFD0A8', '#B4C79C', '#A9BE91', '#9EB585')[lvl], 0.55 + lvl * 0.09))
    cc = chaikin(crest, 3)
    xs, ys = [p[0] for p in cc], [p[1] for p in cc]
    L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(cc[:-1], cc[1:]))
    for _ in range(int(hw * L / 24)):
        p = (rnd.uniform(min(xs) - hw, max(xs) + hw), rnd.uniform(min(ys) - hw, max(ys) + hw))
        if pl_d(p, cc) > hw * 0.84 or any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR) or in_constr(p):
            continue
        if any(math.hypot(p[0] - v[0], p[1] - v[1]) < 34 for v in VIEWS.values()):
            continue
        TREES.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                     % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(9, 14.5)), rnd.choice(('#7FA36A', '#86A971', '#93B47B', '#8AAE74', '#9DBB83'))))
    for j in range(len(cc) // 6):                       # скалы у вершины
        q = cc[rnd.randrange(len(cc))]
        q = (q[0] + rnd.uniform(-hw * .3, hw * .3), q[1] + rnd.uniform(-hw * .3, hw * .3))
        if not any(pl_d(q, r_) < 14 for r_ in KEEP_CLEAR):
            ROCKS.append(rock(q, rnd.uniform(4, 9)))
    mid = cc[len(cc) // 2]
    HILLS.append('<text x="%s" y="%s" font-size="32" font-style="italic" fill="#5E7149" text-anchor="middle">+%d m</text>'
                 % (f1(to_u(*mid)[0]), f1(to_u(*mid)[1]), hgt))
# гора-мыс у карниза (слева от дороги) — часть RD; лес по её склону к бухточке
for _ in range(260):
    p = (rnd.uniform(1060, 1140), rnd.uniform(500, 585))
    if any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR) or inside(p, COVE) or math.hypot(p[0] - VIEWS['C'][0], p[1] - VIEWS['C'][1]) < 30:
        continue
    TREES.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                 % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(9, 13)), rnd.choice(('#7FA36A', '#86A971', '#93B47B'))))
for _ in range(9):                                                # перелески у дороги Хутор - Неблагополучный
    c0 = (rnd.uniform(440, 640), rnd.uniform(600, 700))
    for _ in range(26):
        p = (c0[0] + rnd.gauss(0, 13), c0[1] + rnd.gauss(0, 10))
        if any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR) or in_constr(p) or abs(p[0] - 415) < 14:
            continue
        TREES.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                     % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(9, 13)), rnd.choice(('#86A971', '#93B47B', '#9DBB83', '#A7C48C'))))
# скалы обрыва вдоль карниза и бухточки
for q in COVE[:-2]:
    ROCKS.append(rock((q[0] + rnd.uniform(-2, 3), q[1] + rnd.uniform(-2, 2)), rnd.uniform(5, 9)))
# северный берег над Неблагополучным: море, камни, полоса леса
coast = [(x, coast_y(x)) for x in range(540, 1061, 6)]
SEA_N = '<polygon points="%s" fill="#ABD3E1"/>' % ptxt([(540, 1000)] + coast + [(1060, 1000)])
for x, y in coast[::3]:
    ROCKS.append(rock((x, y - 2), rnd.uniform(3, 6)))
for _ in range(220):
    p = (rnd.uniform(560, 1040), rnd.uniform(856, 876))
    if p[1] > coast_y(p[0]) - 7:
        continue
    TREES.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                 % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(8, 12)), rnd.choice(('#86A971', '#93B47B', '#9DBB83'))))
HILLS.append('</g>')
TREES.append('</g>')
ROCKS.append('</g>')

COVE_SVG = '<polygon points="%s" fill="#B4D9E5" filter="url(#soft_s)"/>' % ptxt(COVE)


def poly_ring(poly, d):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    closed = poly + poly[:1]
    pts = []
    for k in range(90):
        a = k * 2 * math.pi / 90
        lo, hi = 0.0, 600.0
        for _ in range(26):
            mid = (lo + hi) / 2
            q = (cx + mid * math.cos(a), cy + mid * math.sin(a))
            if inside(q, poly) or pl_d(q, closed) < d * (1 + 0.08 * math.sin(3 * a)):
                lo = mid
            else:
                hi = mid
        pts.append((cx + lo * math.cos(a), cy + lo * math.sin(a)))
    return pts


CHILL = ''.join('<polygon points="%s" fill="%s" fill-opacity="0.75" stroke="#93A979" stroke-width="3" stroke-opacity="0.6"/>'
                % (ptxt(poly_ring(CONSTR_POLY, d)), col) for d, col in ((26, '#C9D6B4'), (13, '#BFD0A8')))
CHILL_LABEL = '<text x="%s" y="%s" font-size="30" font-style="italic" fill="#5E7149">+8 m</text>' % (f1(to_u(668, 640)[0]), f1(to_u(668, 640)[1]))
_cx = sum(p[0] for p in CONSTR_POLY) / len(CONSTR_POLY)
_cy = sum(p[1] for p in CONSTR_POLY) / len(CONSTR_POLY)
for _ in range(1600):                                             # лес по склонам холма Стройки
    p = (rnd.uniform(_cx - 160, _cx + 160), rnd.uniform(_cy - 160, _cy + 160))
    if inside(p, CONSTR_POLY):
        continue
    d = pl_d(p, CONSTR_POLY + CONSTR_POLY[:1])
    if d < 9 or d > 26 or any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR) or math.hypot(p[0] - VIEWS['H'][0], p[1] - VIEWS['H'][1]) < 30:
        continue
    if rnd.random() > 0.55:
        continue
    TREES.insert(-1, '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                 % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(9, 14)), rnd.choice(('#7FA36A', '#86A971', '#93B47B', '#8AAE74'))))
FENCE = '<polygon points="%s" fill="none" stroke="#6E8AA6" stroke-width="4"/>' % ptxt(CONSTR_POLY)
PIER_SVG = ('<polygon points="%s" fill="#C9CBC4" stroke="#8E938A" stroke-width="3"/>' % ptxt(PIER) +
            ''.join('<circle cx="%s" cy="%s" r="4" fill="#5F666C"/>' % tuple(f1(v) for v in to_u(1217, yy)) for yy in (697, 707, 717)))
ROADS = ['<g id="R24_roads">']
for rd in NEWROADS:
    for col, w in (('#D3D2C3', 46), ('#5F666C', 32)):
        ROADS.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="round" stroke-linecap="round"/>' % (ptxt(rd), col, w))
for rd in (ROAD_H, ROAD_C):                               # осевая разметка
    ROADS.append('<polyline points="%s" fill="none" stroke="#F4F1E6" stroke-width="2.5" stroke-dasharray="18 22"/>' % ptxt(rd))
LABELS = ['<g id="R24_labels">']
for nm, v in VIEWS.items():
    X, Y = to_u(*v)
    LABELS.append('<circle cx="%s" cy="%s" r="20" fill="#FFFFFF" stroke="#34424B" stroke-width="4"/><circle cx="%s" cy="%s" r="7" fill="#34424B"/>'
                 '<text x="%s" y="%s" font-size="26" font-weight="bold" fill="#34424B">VIEW %s</text>' % (f1(X), f1(Y), f1(X), f1(Y), f1(X + 28), f1(Y - 22), nm))
ROADS.append('</g>')
LABELS += [h for h in HILLS if h.startswith('<text')]
HILLS = [h for h in HILLS if not h.startswith('<text')]
LABELS.append('</g>')

s = s.replace('<g id="L02_mountains"', SEA_N + '<g id="L02_mountains"', 1)
coast_w = [(x, 872 + 6 * math.sin(x / 37.0) + 4 * math.sin(x / 11.0 + 0.7)) for x in range(-80, 561, 6)]
SEA_NW = '<polygon points="%s" fill="#ABD3E1"/>' % ptxt([(-80, 1000)] + coast_w + [(560, 1000)])
ROCKS_NW = ''.join(rock((x, y - 3), rnd.uniform(4, 8)) for x, y in coast_w[::2])
s = s.replace('<g id="L03_relief_coast"', SEA_NW + ROCKS_NW + '<g id="L03_relief_coast"', 1)
s = s.replace('<g id="L04_water"', ''.join(HILLS) + CHILL + COVE_SVG + ''.join(ROCKS) + '<g id="L04_water"', 1)
s = s.replace('<g id="L06a_canal"', FENCE + PIER_SVG + '<g id="L06a_canal"', 1)
s = s.replace('<g id="L08_vegetation"', ''.join(ROADS) + '<g id="L08_vegetation"', 1)
s = s.replace('<g id="R18_plans"', ''.join(TREES) + '<g id="R18_plans"', 1)
_in_port = [p for p in ROAD_C if 590 <= p[1] < 624] + [(1203.0, 633.0)]                       # карниз внутри Порта — поверх плана Порта, до средней дороги
_in_port = [(ROAD_C[ROAD_C.index(_in_port[0]) - 1])] + _in_port
s = s.replace('<g id="L11_labels"', ''.join(LABELS[:-1]) + CHILL_LABEL + '</g>' + '<g id="R27_cornice_in_port">' + ''.join(
    '<polyline points="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="round" stroke-linecap="butt"/>' % (ptxt(_in_port[:-1] + [(_in_port[-1][0], end_)]), c_, w_)
    for c_, w_, end_ in (('#D3D2C3', 46, 629.0), ('#5F666C', 32, 634.0))) + '</g><g id="L11_labels"', 1)
s = s.replace('World map v22 · 16.10.2026 ·', 'World map v28 · 16.10.2026 · Construction strip along the Rough road, hill VIEW H, wide port, cornice C, rocky north coast ·')
open(SVG_OUT, 'w', encoding='utf-8').write(s)
print('svg ok', len(s))

if os.environ.get('NORENDER') != '1':
    html = os.path.join(OUTD, '_v28_render.html')
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
