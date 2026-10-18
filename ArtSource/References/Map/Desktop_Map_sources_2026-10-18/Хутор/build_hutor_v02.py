"""Хутор v02 (TASK-000547, Vadim): re-plan of the Hamlet district on the approved world map v11 at real building sizes.

  python build_hutor_v02.py            -> Хутор_v02.png, Хутор_v02.svg, Планировка_v02.json, Легенда_v02.txt (never overwrites)

Keeps the anchors and the street skeleton of v11 (church top-left, grandpa's hut / base 2 below it, barn top-centre, field 1
top-right, shop in the centre, water tower east, well and pond west, field 2 bottom-left, the east entries from the asphalt
bypass and the south exit to the forest). Every building gets a real footprint (houses 8-11 x 6-8 m), so there are more
houses, set along the streets without fences between them; outbuildings, gardens, orchards, bushes, power poles with
wires and one-off set pieces fill the gaps. World metres (x east, y north), as WORLD_MAP_v11.json; 1 px = 0.1 m here.
"""
import json, math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
WORLD = Path(r'C:\Users\chern_0eqkb03\Desktop\GAME\ArtSource\References\Map\World_v11')
REV = 'v02'
OUT_PNG, OUT_SVG = HERE / f'Хутор_{REV}.png', HERE / f'Хутор_{REV}.svg'
OUT_JSON, OUT_LEG = HERE / f'Планировка_{REV}.json', HERE / f'Легенда_{REV}.txt'
for p in (OUT_PNG, OUT_SVG, OUT_JSON, OUT_LEG):
    if p.exists():
        raise SystemExit(f'{p.name} exists: bump REV')
rnd = random.Random(446)
W = json.load(open(WORLD / 'WORLD_MAP_v11.json', encoding='utf-8'))
X0, X1, Y0, Y1 = 118.0, 442.0, 355.0, 618.0          # view window (m)
S = 10.0                                              # px per metre in the output

# ------------------------------------------------------------------ geometry
def rect(c, ang, w, l):
    """Oriented rectangle: centre c, angle of its long side l (radians), width w across."""
    ca, sa = math.cos(ang), math.sin(ang)
    u, v = (ca, sa), (-sa, ca)
    return [(c[0] + u[0] * a * l / 2 + v[0] * b * w / 2, c[1] + u[1] * a * l / 2 + v[1] * b * w / 2)
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def circle(c, r, n=16):
    return [(c[0] + r * math.cos(2 * math.pi * k / n), c[1] + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def _proj(poly, ax):
    ds = [p[0] * ax[0] + p[1] * ax[1] for p in poly]
    return min(ds), max(ds)


def overlap(a, b, gap=0.0):
    """Separating-axis test for convex polygons, with a clearance gap."""
    for poly in (a, b):
        for i in range(len(poly)):
            x0, y0 = poly[i]; x1, y1 = poly[(i + 1) % len(poly)]
            ax = (y0 - y1, x1 - x0); n = math.hypot(*ax) or 1.0; ax = (ax[0] / n, ax[1] / n)
            a0, a1 = _proj(a, ax); b0, b1 = _proj(b, ax)
            if a1 + gap < b0 or b1 + gap < a0:
                return False
    return True


def seg_dist(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1.0)))
    return math.hypot(p[0] - a[0] - t * ax, p[1] - a[1] - t * ay)


def poly_road_dist(poly, road):
    pts = list(poly) + [(sum(p[0] for p in poly) / len(poly), sum(p[1] for p in poly) / len(poly))]
    ext = []                                           # edge midpoints too
    for i in range(len(poly)):
        ext.append(((poly[i][0] + poly[(i + 1) % len(poly)][0]) / 2, (poly[i][1] + poly[(i + 1) % len(poly)][1]) / 2))
    return min(seg_dist(p, road[i], road[i + 1]) for p in pts + ext for i in range(len(road) - 1))


def resample(line, step):
    out, acc = [line[0]], 0.0
    for a, b in zip(line, line[1:]):
        L = math.dist(a, b); t = step - acc
        while t <= L:
            out.append((a[0] + (b[0] - a[0]) * t / L, a[1] + (b[1] - a[1]) * t / L)); t += step
        acc = (acc + L) % step
    return out


def at(line, s):
    """Point and unit tangent at arc length s along a polyline."""
    for a, b in zip(line, line[1:]):
        L = math.dist(a, b)
        if s <= L:
            t = s / L
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        s -= L
    a, b = line[-2], line[-1]; L = math.dist(a, b)
    return b, ((b[0] - a[0]) / L, (b[1] - a[1]) / L)


def length(line):
    return sum(math.dist(a, b) for a, b in zip(line, line[1:]))

# ------------------------------------------------------------------ the scene
ROADS = {r['id']: [tuple(p) for p in r['polyline_m']] for r in W['roads']}
STREETS = ['02_h_main', '02_h_north', '02_h_south', '02_h_loop', '02_h_church', '02_h_base', 'hamlet_bypass', 'hamlet_forest',
           '02_h_field09', '02_h_d_tower', '02_h_d21']
HALF = {'hamlet_bypass': 4.6, '02_h_field09': 1.8, '02_h_d_tower': 1.8, '02_h_d21': 1.8}
ROAD_LINES = [(ROADS[k], HALF.get(k, 2.7)) for k in STREETS if k in ROADS]
items = []          # dict(kind, layer, poly | line | pts, fill, outline, label)
blocked = []        # polygons that new objects must not overlap


def add(kind, poly, fill, outline=(70, 60, 50), layer='objects', note=None, block=True, width=1):
    items.append(dict(kind=kind, poly=poly, fill=fill, outline=outline, layer=layer, note=note, width=width))
    if block:
        blocked.append(poly)
    return poly


def free(poly, gap=0.6, road_gap=1.2):
    if any(overlap(poly, b, gap) for b in blocked):
        return False
    return all(poly_road_dist(poly, r) > h + road_gap for r, h in ROAD_LINES)

# colours (flat, as the v11 map)
ROOF = {'izba': (206, 178, 150), 'brick': (196, 104, 78), 'L': (190, 150, 120), 'new2': (150, 120, 108), 'tin': (128, 164, 146),
        'abandoned': (128, 120, 112), 'unfinished': (214, 206, 196)}
WOOD, DARKWOOD, GREEN_TREE, FRUIT, BUSH = (178, 142, 102), (136, 104, 76), (118, 164, 104), (150, 196, 120), (128, 176, 108)
GARDEN, GARDEN_LINE, FIELD = (206, 222, 180), (172, 196, 146), (232, 206, 122)

# anchors kept from v11 (church as is; the rest at real size on the old centres)
pond = next(p for p in W['water']['ponds_and_pools'] if p['kind'] == 'village_pond')['polygon_m']
for b in W['buildings']:
    if b['district'] == '02' and b['kind'] == 'church':
        add('church', [tuple(p) for p in b['footprint_m']], (214, 208, 226), layer='buildings', note='02 Церковь')
blocked.append([(p[0], p[1]) for p in pond])
for s in W['structures']:
    if s.get('district') == '02' and s['kind'] == 'yellow_field':
        blocked.append([tuple(p) for p in s['polygon_m']])
    if s.get('district') == '02' and s['kind'] == 'haystack':
        add('haystack', circle(s['position_m'], s['radius_m']), (228, 196, 110), layer='objects')
blocked.append(rect((217.9, 472.7), 0.0, 4.0, 9.0))          # the old well and its path

A = math.radians
hut = add('grandpa_hut_base2', rect((166.0, 520.0), A(0), 7.5, 10.0), (176, 196, 186), layer='buildings', note='01 Хижина деда — база 2')
add('porch', rect((166.0, 515.3), A(0), 1.6, 3.6), WOOD, layer='objects')
add('base_yard_van_spot', rect((186.4, 511.1), A(0), 9.2, 9.2), (226, 214, 190), outline=(150, 130, 100), layer='ground', note='база 2: место бусика')
add('banya', rect((152.0, 512.0), A(90), 4.0, 4.5), DARKWOOD)
add('shed', rect((153.5, 528.0), A(0), 3.0, 4.0), WOOD)
add('woodpile', rect((175.5, 526.0), A(90), 1.2, 3.5), (160, 120, 80))
add('dog_kennel', rect((178.5, 516.5), A(0), 1.2, 1.2), (150, 110, 80))
add('garden', rect((160.0, 535.5), A(0), 9.0, 14.0), GARDEN, outline=GARDEN_LINE, layer='ground')
shop = add('village_shop', rect((270.3, 502.5), A(0), 8.0, 12.0), (222, 170, 150), layer='buildings', note='04 Сельпо')
add('shop_porch', rect((270.3, 497.6), A(0), 1.8, 5.0), (190, 180, 170))
add('square', rect((250.0, 507.5), A(0), 9.0, 11.0), (218, 210, 196), outline=(170, 160, 146), layer='ground', note='площадь у сельпо')
add('war_memorial', rect((250.0, 509.0), A(0), 2.4, 2.4), (200, 196, 190), outline=(90, 90, 90), note='05 Памятник (обелиск со звездой)')
for k in range(3):
    add('bench', rect((246.0 + 4.0 * k, 504.4), A(0), 0.5, 1.8), WOOD)
add('bus_stop', rect((374.0, 477.6), A(-18), 1.8, 4.0), (120, 150, 170), note='13 Автобусная остановка')
barn = add('barn_cowshed', rect((273.6, 555.0), A(0), 10.0, 18.0), (160, 128, 108), layer='buildings', note='03 Колхозный коровник')
add('hay_shed', rect((293.0, 556.0), A(90), 6.0, 10.0), (200, 178, 120), note='навес для сена')
add('cow_pen', rect((273.6, 565.6), A(0), 7.0, 14.0), (214, 206, 168), outline=(140, 110, 80), layer='ground', note='загон, 3 коровы')
for k, x in enumerate((268.5, 273.0, 278.0)):
    add('cow', rect((x, 565.4 + 1.2 * (k % 2)), A(20 * k - 15), 0.8, 2.2), (240, 240, 236), outline=(60, 60, 60))
add('old_tractor', rect((299.0, 566.0), A(-30), 2.0, 3.6), (200, 60, 50), note='старый трактор «Беларусь»')
add('water_tower', circle((338.4, 517.8), 1.9), (176, 188, 200), layer='buildings', note='07 Водонапорная башня Рожновского')

# ------------------------------------------------------------------ houses along the streets
ARCH = [  # name, (w, l) ranges, weight (GPT's mix: old huts and brick bungalows the most, L-shaped, a few new two-storey)
    ('izba', (6.0, 6.8), (8.0, 9.0), 26), ('brick', (7.5, 8.0), (9.5, 10.5), 26), ('L', (7.0, 8.0), (9.5, 10.5), 18),
    ('new2', (8.0, 8.5), (9.0, 10.0), 12), ('tin', (6.0, 7.0), (7.5, 9.0), 14)]
houses = []


def pick_arch():
    t = rnd.uniform(0, sum(a[3] for a in ARCH))
    for a in ARCH:
        t -= a[3]
        if t <= 0:
            return a
    return ARCH[0]


def house_l_shape(c, ang, w, l):
    """An L-shaped house: main block plus a wing at the back corner (two rectangles)."""
    main = rect(c, ang, w, l)
    ca, sa = math.cos(ang), math.sin(ang)
    wing_c = (c[0] + ca * (l / 2 - 2.2) - sa * (w / 2 + 2.0), c[1] + sa * (l / 2 - 2.2) + ca * (w / 2 + 2.0))
    return main, rect(wing_c, ang, 4.0, 4.4)


def backyard(c, ang, side_n, depth):
    """Outbuildings, a garden and fruit trees behind a house; side_n points away from the street."""
    bx, by = side_n
    tx, ty = math.cos(ang), math.sin(ang)
    def P(f, b):                                      # f along the street, b away from it (from the house centre)
        return (c[0] + tx * f + bx * b, c[1] + ty * f + by * b)
    placed = 0
    # garden bed behind
    g = rect(P(rnd.uniform(-2, 2), depth + 8.5), ang, rnd.uniform(6, 9), rnd.uniform(8, 12))
    if free(g, 0.4, 2.0):
        add('garden', g, GARDEN, outline=GARDEN_LINE, layer='ground')
    menu = [('shed', 3.0, 3.6, WOOD), ('chicken_coop', 2.4, 3.2, (196, 160, 118)), ('outhouse', 1.3, 1.3, DARKWOOD),
            ('banya', 4.0, 4.5, DARKWOOD), ('woodpile', 1.1, 3.2, (160, 120, 80)), ('greenhouse', 3.0, 6.0, (214, 234, 236)),
            ('summer_kitchen', 4.0, 5.0, (210, 186, 160)), ('garage', 4.0, 6.0, (170, 170, 168)), ('dog_kennel', 1.2, 1.2, (150, 110, 80))]
    rnd.shuffle(menu)
    for kind, w, l, col in menu[:rnd.randint(2, 4)]:
        for _ in range(6):
            f = rnd.choice((-1, 1)) * rnd.uniform(3.0, 7.0)
            p = rect(P(f, depth + rnd.uniform(0.0, 4.0)), ang + A(rnd.choice((0, 90))), w, l)
            if free(p, 0.5, 2.0):
                add(kind, p, col, outline=(90, 160, 170) if kind == 'greenhouse' else (70, 60, 50))
                placed += 1
                break
    for _ in range(rnd.randint(2, 4)):                   # fruit trees
        for _ in range(5):
            p = circle(P(rnd.uniform(-7, 7), depth + rnd.uniform(4, 14)), rnd.uniform(1.6, 2.4), 12)
            if free(p, 0.2, 1.5):
                add('fruit_tree', p, FRUIT, outline=(110, 150, 90), layer='trees', block=False)
                break
    if rnd.random() < 0.6:                               # a lilac / elder bush at the front corner
        p = circle(P(rnd.choice((-1, 1)) * rnd.uniform(4.5, 6.0), -depth * 0.2), rnd.uniform(1.0, 1.5), 10)
        if free(p, 0.2, 1.2):
            add('bush', p, BUSH, outline=(96, 140, 86), layer='trees', block=False)
    for kind, w, l, col, chance in (('grape_arbor', 3.0, 5.0, (198, 216, 150), 0.45), ('compost', 1.5, 2.0, (150, 120, 90), 0.4),
                                    ('flower_strip', 1.0, 4.0, (232, 160, 178), 0.55), ('rain_barrel', 0.6, 0.6, (90, 110, 130), 0.6),
                                    ('outdoor_table', 0.8, 1.5, (190, 160, 120), 0.35)):
        if rnd.random() < chance:
            for _ in range(5):
                if kind == 'flower_strip':
                    pp = rect(P(rnd.uniform(-2.0, 2.0), -depth + 0.3), ang, w, l)
                elif kind == 'grape_arbor':
                    pp = rect(P(rnd.choice((-1, 1)) * rnd.uniform(5.5, 7.0), rnd.uniform(-1.0, 2.0)), ang + A(90), w, l)
                else:
                    pp = rect(P(rnd.uniform(-6, 6), depth + rnd.uniform(-1, 6)), ang, w, l)
                if free(pp, 0.3, 1.2):
                    add(kind, pp, col, outline=(120, 140, 90) if kind == 'grape_arbor' else (110, 90, 70), block=kind == 'grape_arbor')
                    break
    if rnd.random() < 0.4:                               # a clothes line
        a = P(rnd.uniform(-5, 5), depth + rnd.uniform(1, 4))
        b = (a[0] + math.cos(ang) * 5.0, a[1] + math.sin(ang) * 5.0)
        items.append(dict(kind='clothesline', poly=None, line=[a, b], fill=None, outline=(120, 120, 120), layer='objects', note=None, width=1))
    if rnd.random() < 0.35:                              # bench by the gate
        p = rect(P(rnd.uniform(-2.5, 2.5), -depth * 0.55 - 1.2), ang, 0.5, 1.8)
        if free(p, 0.2, 0.8):
            add('bench', p, WOOD)


def line_houses(road, box, max_n, sides=(1, -1), gap=(4.0, 8.0), setback=(3.0, 7.0)):
    """A loose group of houses along one street inside box = (x0, y0, x1, y1): walls 4-8 m apart, now and then a wider
    gap for a shared orchard or a shortcut; setbacks 3-7 m; houses face the street (GPT layout rules 2-4)."""
    line = ROADS[road]
    half = HALF.get(road, 2.7)
    L = length(line)
    n_here = 0
    for side in sides:
        s = rnd.uniform(0, 4)
        while s < L - 4 and n_here < max_n:
            p, t = at(line, s)
            n = (-t[1] * side, t[0] * side)
            name, wr, lr, _ = pick_arch()
            w, l = rnd.uniform(*wr), rnd.uniform(*lr)
            off = half + rnd.uniform(*setback) + w / 2
            c = (p[0] + n[0] * off, p[1] + n[1] * off)
            if not (box[0] <= c[0] <= box[2] and box[1] <= c[1] <= box[3]):
                s += 3.0
                continue
            ang = math.atan2(t[1], t[0]) + A(rnd.uniform(-6, 6))
            if name == 'L':
                main, wing = house_l_shape(c, ang, w, l)
                shapes = [main, wing]
            else:
                shapes = [rect(c, ang, w, l)]
            if all(free(sh, 1.2, 1.5) for sh in shapes):
                for k, sh in enumerate(shapes):
                    add('house_' + name, sh, ROOF[name], layer='buildings')
                houses.append(dict(c=c, ang=ang, arch=name, w=w, l=l, n=n))
                n_here += 1
                backyard(c, ang, n, w / 2 + 1.5)
                s += l + (rnd.uniform(10.0, 13.0) if rnd.random() < 0.2 else rnd.uniform(*gap))
            else:
                s += 3.0

# one-off set pieces before the generic houses, so they get their spots
add('cemetery', rect((166.0, 595.0), A(-4), 14.0, 20.0), (214, 220, 200), outline=(110, 110, 110), layer='ground',
    note='06 Сельское кладбище (кресты, оградки)')
for i in range(4):
    for j in range(5):
        add('grave', rect((159.5 + j * 3.4, 590.0 + i * 3.2), A(-4), 0.8, 1.6), (180, 176, 168), outline=(110, 110, 110), block=False)
ab = add('house_abandoned', rect((206.0, 433.0), A(18), 6.5, 8.5), ROOF['abandoned'], layer='buildings', note='08 Заброшенный дом (провалилась крыша)')
add('rusty_car', rect((214.0, 439.0), A(62), 1.7, 4.0), (150, 110, 90), note='ржавый «Москвич»')
for c in ((199.0, 428.0), (211.0, 427.5), (201.5, 440.0)):
    add('overgrowth', circle(c, rnd.uniform(1.8, 2.6), 12), BUSH, outline=(96, 140, 86), layer='trees', block=False)
add('house_unfinished', rect((318.0, 398.0), A(-3), 8.0, 10.0), ROOF['unfinished'], layer='buildings', note='09 Недострой из кирпича')
add('brick_pallets', rect((327.0, 393.0), A(0), 1.2, 2.4), (196, 104, 78))
add('concrete_mixer', rect((326.5, 402.5), A(30), 1.4, 1.8), (120, 140, 160))
add('playground', rect((268.0, 455.0), A(0), 10.0, 13.0), (226, 214, 190), outline=(160, 140, 110), layer='ground', note='10 Детская площадка (качели, горка)')
for c, w, l in (((264.5, 456.5), 1.0, 3.0), ((270.5, 456.0), 1.2, 2.6), ((268.0, 452.0), 2.6, 2.6)):
    add('play_item', rect(c, 0.0, w, l), (220, 90, 80), block=False)
add('apiary', rect((322.0, 570.0), A(0), 7.0, 9.0), (226, 222, 170), outline=(170, 160, 110), layer='ground', note='11 Пасека (ульи)')
for i in range(2):
    for j in range(4):
        add('beehive', rect((318.0 + j * 2.6, 568.0 + i * 3.6), 0.0, 0.7, 0.7), (230, 196, 90), block=False)
add('melon_field', rect((282.0, 418.0), A(-8), 20.0, 28.0), (190, 214, 150), outline=(150, 180, 120), layer='ground',
    note='12 Бахча (арбузы, подсолнухи)')
add('dump', rect((150.0, 380.0), A(25), 6.0, 9.0), (176, 168, 150), outline=(130, 120, 100), layer='ground', note='14 Стихийная свалка у леса')
add('football_pitch', rect((298.0, 530.5), A(-1), 18.0, 34.0), (200, 222, 168), outline=(240, 240, 236), layer='ground',
    note='23 Сельское футбольное поле (ворота из труб)')
for x in (281.6, 314.4):
    add('goal', rect((x, 530.5), A(90), 0.6, 5.0), (240, 240, 236), outline=(120, 120, 120), block=False)
# GPT's one-off spots and village infrastructure
add('tractor_bay', rect((299.0, 568.0), A(0), 6.0, 8.0), (204, 200, 192), outline=(150, 146, 140), layer='ground',
    note='16 Ремонтная площадка: трактор с открытым капотом')
add('watermelon_stall', rect((279.0, 497.5), A(0), 2.0, 3.0), (110, 170, 90), note='17 Бахчевой развал у сельпо')
add('dance_floor', rect((236.0, 470.0), A(-8), 6.0, 8.0), (206, 176, 136), outline=(140, 110, 80), layer='ground',
    note='18 Танцплощадка с выцветшими флажками')
for c in ((232.3, 467.0), (239.7, 466.0), (232.3, 474.0), (239.7, 473.0)):
    add('bunting_pole', circle(c, 0.25, 6), (90, 70, 60), block=False)
add('repair_bench', rect((181.0, 523.0), A(90), 1.0, 3.0), (150, 110, 80), note='19 Верстак деда: недочиненные холодильник и мотоцикл')
add('kiosk_abandoned', rect((366.0, 481.0), A(-18), 2.5, 3.0), (170, 120, 100), note='20 Заброшенный ларёк у остановки')
add('transformer', rect((289.0, 509.0), A(0), 2.0, 3.0), (150, 160, 150), note='21 Трансформаторная будка')
add('noticeboard', rect((262.0, 497.6), A(0), 0.4, 1.5), (120, 90, 70))
for c in ((233.0, 501.0), (318.0, 476.0)):
    add('standpipe', rect(c, 0.0, 0.6, 0.6), (70, 110, 150))
for c, a in (((226.0, 523.0), 90), ((330.0, 437.0), 0)):
    add('refuse_point', rect(c, A(a), 2.0, 4.0), (110, 130, 110))

CLUSTERS = [  # (street, box, houses): about two thirds south and east, the rest round the base, the church approach and the barn
    ('02_h_church', (135, 540, 200, 590), 2), ('02_h_main', (140, 540, 205, 575), 2),            # church approach
    ('02_h_main', (196, 512, 240, 572), 3),                                                      # base neighbours
    ('02_h_north', (296, 530, 330, 580), 4),                                                     # barn lane
    ('02_h_main', (284, 470, 333, 510), 5),                                                      # shop street
    ('02_h_main', (340, 448, 388, 500), 4),                                                      # east end by the asphalt
    ('02_h_south', (220, 398, 262, 486), 6),                                                     # south street
    ('02_h_loop', (240, 372, 345, 486), 7)]                                                      # south-east loop
for road, box, n in CLUSTERS:
    line_houses(road, box, n)

# ------------------------------------------------------------------ power poles with wires along the main streets
poles = []
for road, side in (('02_h_main', 1), ('02_h_north', -1), ('02_h_south', 1), ('02_h_loop', 1)):
    line = ROADS[road]
    chain = []
    for k, (p, t) in enumerate(at(line, s) for s in [x for x in range(4, int(length(line)), 31)]):
        n = (-t[1] * side, t[0] * side)
        q = (p[0] + n[0] * 4.4, p[1] + n[1] * 4.4)
        if not any(overlap(circle(q, 0.4, 6), b, 0.2) for b in blocked):
            chain.append(q)
    poles.append(chain)
pole_pts = [q for c in poles for q in c]
drops = []
for h in houses:                                          # a service wire from the nearest pole to most houses
    if rnd.random() < 0.85 and pole_pts:
        q = min(pole_pts, key=lambda z: math.dist(z, h['c']))
        if math.dist(q, h['c']) < 40:
            drops.append((q, h['c']))

# ------------------------------------------------------------------ nature: trees along the roads, willows at the pond, groves
for road in ('02_h_main', '02_h_north', '02_h_south', '02_h_loop'):
    line = ROADS[road]
    for s in range(10, int(length(line)), 13):
        if rnd.random() < 0.55:
            p, t = at(line, s + rnd.uniform(-3, 3))
            side = rnd.choice((1, -1))
            n = (-t[1] * side, t[0] * side)
            r = rnd.uniform(2.2, 3.4)
            off = HALF.get(road, 2.7) + 1.8 + r
            c = (p[0] + n[0] * off, p[1] + n[1] * off)
            poly = circle(c, r, 14)
            if free(poly, 0.4, 1.4):
                add('tree', poly, GREEN_TREE, outline=(90, 136, 80), layer='trees', block=False)
cx = sum(p[0] for p in pond) / len(pond); cy = sum(p[1] for p in pond) / len(pond)
for k in range(9):                                          # willows round the pond
    a = 2 * math.pi * k / 9 + rnd.uniform(-0.2, 0.2)
    c = (cx + 25 * math.cos(a), cy + 21 * math.sin(a))
    poly = circle(c, rnd.uniform(2.6, 3.4), 14)
    if free(poly, 0.3, 1.0):
        add('willow', poly, (140, 182, 122), outline=(100, 146, 90), layer='trees', block=False)
for k in range(14):                                         # reeds at the pond edge
    a = 2 * math.pi * k / 14
    c = (cx + 21 * math.cos(a), cy + 17.5 * math.sin(a))
    add('reeds', circle(c, 1.0, 8), (160, 190, 120), outline=(130, 160, 100), layer='trees', block=False)
for gc, n in (((150.0, 565.0), 9), ((300.0, 500.0), 6), ((205.0, 560.0), 7), ((355.0, 430.0), 8)):   # birch groves
    for k in range(n):
        c = (gc[0] + rnd.uniform(-10, 10), gc[1] + rnd.uniform(-8, 8))
        poly = circle(c, rnd.uniform(1.8, 2.6), 12)
        if free(poly, 0.3, 1.2):
            add('birch', poly, (176, 210, 150), outline=(130, 170, 110), layer='trees', block=False)
def blob(c, rx, ry, rot=0.0, n=12, rough=0.25):
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = 1.0 + rnd.uniform(-rough, rough)
        x, y = rx * r * math.cos(a), ry * r * math.sin(a)
        pts.append((c[0] + x * math.cos(rot) - y * math.sin(rot), c[1] + x * math.sin(rot) + y * math.cos(rot)))
    return pts


def scatter(kind, count, fill, outline, rr, layer='trees', box=(140, 378, 372, 592), gap=0.6, block=False, shape='circle'):
    done = 0
    for _ in range(count * 30):
        if done >= count:
            break
        c = (rnd.uniform(box[0], box[2]), rnd.uniform(box[1], box[3]))
        if shape == 'circle':
            poly = circle(c, rnd.uniform(*rr), 14)
        else:
            poly = blob(c, rnd.uniform(*rr), rnd.uniform(*rr) * rnd.uniform(1.6, 2.6), rnd.uniform(0, math.pi))
        if free(poly, gap, 1.5):
            add(kind, poly, fill, outline=outline, layer=layer, block=block)
            done += 1


scatter('shade_tree', 22, (104, 150, 92), (80, 124, 72), (3.2, 4.4), gap=1.0, block=True)
for h in rnd.sample(houses, min(len(houses), 22)):                 # lilac / elder clumps by the houses
    for _ in range(12):
        a = rnd.uniform(0, 2 * math.pi)
        c = (h['c'][0] + math.cos(a) * rnd.uniform(6.5, 10.0), h['c'][1] + math.sin(a) * rnd.uniform(6.5, 10.0))
        poly = blob(c, rnd.uniform(1.1, 1.6), rnd.uniform(1.3, 2.0), rnd.uniform(0, math.pi), rough=0.15)
        if free(poly, 0.4, 1.4):
            add('shrub', poly, BUSH, outline=(96, 140, 86), layer='trees', block=False)
            break
for _ in range(16):                                                   # thickets along the district edge
    side = rnd.choice(('w', 's', 'n'))
    c = {'w': (rnd.uniform(140, 152), rnd.uniform(440, 575)), 's': (rnd.uniform(160, 330), rnd.uniform(376, 383)),
         'n': (rnd.uniform(180, 250), rnd.uniform(590, 598))}[side]
    for k in range(rnd.randint(2, 4)):
        poly = blob((c[0] + rnd.uniform(-3, 3), c[1] + rnd.uniform(-3, 3)), rnd.uniform(1.2, 1.8), rnd.uniform(1.4, 2.2),
                    rnd.uniform(0, math.pi), rough=0.15)
        if free(poly, 0.2, 1.4):
            add('shrub', poly, BUSH, outline=(96, 140, 86), layer='trees', block=False)
orch = rect((222.0, 580.0), A(-3), 22.0, 46.0)                        # the old kolkhoz orchard: irregular rows
add('kolkhoz_orchard', orch, (214, 228, 190), outline=(180, 200, 160), layer='ground', note='22 Старый колхозный сад', block=False)
for i in range(4):
    for j in range(9):
        if rnd.random() < 0.82:
            c = (202.0 + j * 5.0 + rnd.uniform(-0.8, 0.8), 571.5 + i * 5.4 + rnd.uniform(-0.8, 0.8))
            poly = circle(c, rnd.uniform(1.5, 2.1), 12)
            if free(poly, 0.2, 1.4):
                add('orchard_tree', poly, FRUIT, outline=(110, 150, 90), layer='trees', block=False)
scatter('earth_mound', 4, (196, 206, 160), (160, 176, 130), (1.4, 2.0), layer='ground', shape='blob', block=True)
for _ in range(5):                                                   # limestone outcrops near the ridge and the forest edge
    for _ in range(30):
        c = (rnd.uniform(142, 200), rnd.uniform(380, 598))
        poly = blob(c, rnd.uniform(0.8, 1.2), rnd.uniform(0.9, 1.4), rnd.uniform(0, math.pi), rough=0.18)
        if free(poly, 0.6, 1.5):
            add('limestone', poly, (200, 198, 190), outline=(150, 148, 140))
            break
for k in range(5):
    a = 2 * math.pi * k / 5 + 0.4
    add('reed_patch', blob((cx + 19 * math.cos(a), cy + 15.5 * math.sin(a)), 1.2, 3.0, a + math.pi / 2), (160, 190, 120),
        outline=(130, 160, 100), layer='trees', block=False)
ditch = []
for sv in range(6, int(length(ROADS['02_h_main'])) - 6, 2):
    p, t = at(ROADS['02_h_main'], sv)
    ditch.append((p[0] + t[1] * 4.3, p[1] - t[0] * 4.3))
items.append(dict(kind='ditch', poly=None, line=ditch, fill=None, outline=(120, 160, 150), layer='ground', note=None, width=3))

# fishing spot on the river bank east of the bypass
add('fishing_path', [(368.0, 462.0), (386.0, 458.0), (397.0, 455.0), (408.0, 452.0)], None, layer='paths', block=False)
add('fishing_landing', rect((411.0, 451.0), A(-15), 2.0, 4.0), WOOD, note='15 Рыбацкий спуск: мостки, сети на кольях, лодка')
add('nets', rect((406.0, 446.0), A(70), 0.4, 6.0), (90, 110, 120), block=False)
add('nets', rect((404.0, 448.5), A(70), 0.4, 5.0), (90, 110, 120), block=False)
add('boat', rect((407.5, 456.0), A(-30), 1.3, 4.0), (90, 130, 170))
add('fire_pit', circle((402.0, 452.5), 0.8, 10), (120, 100, 90), block=False)

# ------------------------------------------------------------------ render
Image.MAX_IMAGE_PIXELS = None
big = Image.open(WORLD / 'VOLUNTEERS_MAP_v11_FINAL.png').convert('RGB')
H = big.height
crop = big.crop((int(X0 / 0.2), int(H - Y1 / 0.2), int(X1 / 0.2), int(H - Y0 / 0.2)))
img = crop.resize((int((X1 - X0) * S), int((Y1 - Y0) * S)), Image.LANCZOS)
dr = ImageDraw.Draw(img)


def PX(p):
    return ((p[0] - X0) * S, (Y1 - p[1]) * S)


bg = img.getpixel(PX((300.0, 470.0)))
interior = [(150, 377), (372, 377), (372, 596), (182, 600), (176, 586), (156, 576), (146, 540), (146, 440)]
dr.polygon([PX(p) for p in interior], fill=bg)
for s2 in W['structures']:
    if s2.get('district') == '02' and s2['kind'] == 'yellow_field':
        fp = [tuple(q) for q in s2['polygon_m']]
        dr.polygon([PX(q) for q in fp], fill=FIELD, outline=(200, 170, 90), width=2)
        for k in range(1, 9):
            a = (fp[0][0] + (fp[1][0] - fp[0][0]) * k / 9, fp[0][1] + (fp[1][1] - fp[0][1]) * k / 9)
            b = (fp[3][0] + (fp[2][0] - fp[3][0]) * k / 9, fp[3][1] + (fp[2][1] - fp[3][1]) * k / 9)
            dr.line([PX(a), PX(b)], fill=(214, 182, 96), width=2)
    if s2.get('district') == '02' and s2['kind'] == 'meadow_with_grass_tufts':
        dr.polygon([PX(tuple(q)) for q in s2['polygon_m']], fill=(222, 232, 200))
dr.polygon([PX(tuple(q)) for q in pond], fill=(168, 212, 228), outline=(120, 170, 196), width=3)
wl = next(p2 for p2 in W['water']['ponds_and_pools'] if p2['kind'] == 'well')['polygon_m']
wc = (sum(q[0] for q in wl) / len(wl), sum(q[1] for q in wl) / len(wl))
dr.ellipse([PX((wc[0] - 1.2, wc[1] + 1.2)), PX((wc[0] + 1.2, wc[1] - 1.2))], fill=(150, 170, 190), outline=(90, 100, 110), width=3)
# erase the old hamlet buildings, plots, beds, sheds, tower and haystacks of v11 (roads, pond, fields stay)
for b in W['buildings']:
    if b['district'] == '02' and b['kind'] != 'church':
        dr.polygon([PX(p) for p in b['footprint_m']], fill=bg, outline=bg, width=int(2.5 * S))
for s in W['structures']:
    if s.get('district') == '02' and s['kind'] in ('plot_or_garden', 'vegetable_beds', 'haystack', 'water_tower', 'base_yard_van_spot'):
        if 'polygon_m' in s:
            dr.polygon([PX(p) for p in s['polygon_m']], fill=bg, outline=bg, width=int(2.5 * S))
        else:
            dr.polygon([PX(p) for p in circle(s['position_m'], s['radius_m'] + 1.0)], fill=bg)
for k in ROADS:
    if k.startswith('02_h_d') and k != '02_h_d_tower':
        dr.line([PX(p) for p in ROADS[k]], fill=bg, width=int(5 * S))
# (re)draw the dirt streets on top of the erased plots so they stay continuous
for k in STREETS:
    if k in ROADS and k != 'hamlet_bypass':
        w = 2 * HALF.get(k, 2.7) * S
        dr.line([PX(p) for p in ROADS[k]], fill=(230, 208, 164), width=int(w), joint='curve')
for layer in ('ground', 'trees', 'objects', 'buildings'):
    for it in items:
        if it['layer'] != layer or not it.get('poly'):
            continue
        if it['kind'] == 'fishing_path':
            continue
        dr.polygon([PX(p) for p in it['poly']], fill=it['fill'], outline=it['outline'], width=2 if layer == 'buildings' else 1)
    if layer == 'ground':
        for it in items:                                   # garden stripes
            if it['kind'] in ('garden', 'melon_field') and it['layer'] == 'ground':
                p = it['poly']
                for k in range(1, 6):
                    a = (p[0][0] + (p[1][0] - p[0][0]) * k / 6, p[0][1] + (p[1][1] - p[0][1]) * k / 6)
                    b = (p[3][0] + (p[2][0] - p[3][0]) * k / 6, p[3][1] + (p[2][1] - p[3][1]) * k / 6)
                    dr.line([PX(a), PX(b)], fill=GARDEN_LINE, width=2)
for it in items:
    if it.get('line') and it['kind'] == 'ditch':
        pts = it['line']
        for a, b in zip(pts[::2], pts[1::2]):
            dr.line([PX(a), PX(b)], fill=it['outline'], width=it['width'])
    elif it.get('line'):
        dr.line([PX(p) for p in it['line']], fill=it['outline'], width=it['width'])
# fishing path (blue dashed, as pedestrian paths)
fp = next(it for it in items if it['kind'] == 'fishing_path')['poly']
for a, b in zip(resample(fp, 1.5)[::2], resample(fp, 1.5)[1::2]):
    dr.line([PX(a), PX(b)], fill=(80, 120, 190), width=4)
# wires then poles
for chain in poles:
    if len(chain) > 1:
        dr.line([PX(p) for p in chain], fill=(70, 70, 76), width=2)
for q, c in drops:
    dr.line([PX(q), PX(c)], fill=(110, 110, 116), width=1)
for chain in poles:
    for q in chain:
        x, y = PX(q)
        dr.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(60, 48, 40))
# numbers
font = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 26)
legend = []
for it in items:
    if it['note'] and it['note'][:2].isdigit() and it.get('poly'):
        num, text = it['note'][:2], it['note'][3:]
        p = it['poly']
        c = (sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p))
        x, y = PX(c)
        dr.ellipse([x - 18, y - 18, x + 18, y + 18], fill=(40, 52, 70), outline=(255, 255, 255), width=3)
        dr.text((x, y), str(int(num)), fill=(255, 255, 255), font=font, anchor='mm')
        legend.append((int(num), text))
img.save(OUT_PNG)

# ------------------------------------------------------------------ svg (editable source: base raster + vector layers)
def svg_poly(p, fill, outline, w):
    pts = ' '.join(f'{x:.1f},{y:.1f}' for x, y in (PX(q) for q in p))
    f = 'none' if fill is None else 'rgb%s' % (tuple(fill),)
    return f'<polygon points="{pts}" fill="{f}" stroke="rgb{tuple(outline)}" stroke-width="{w}"/>'


with open(OUT_SVG, 'w', encoding='utf-8') as f:
    f.write(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{img.width}" height="{img.height}">\n')
    f.write(f'<image href="{OUT_PNG.name}" x="0" y="0" width="{img.width}" height="{img.height}" opacity="0.0"/>\n')
    for layer in ('ground', 'trees', 'objects', 'buildings'):
        f.write(f'<g id="{layer}">\n')
        for it in items:
            if it['layer'] == layer and it['kind'] != 'fishing_path' and it.get('poly'):
                f.write(svg_poly(it['poly'], it['fill'], it['outline'], 2 if layer == 'buildings' else 1) + '\n')
        f.write('</g>\n')
    f.write('<g id="wires">\n')
    for chain in poles:
        if len(chain) > 1:
            f.write('<polyline points="%s" fill="none" stroke="rgb(70,70,76)" stroke-width="2"/>\n' % ' '.join('%.1f,%.1f' % PX(p) for p in chain))
    f.write('</g>\n</svg>\n')

# ------------------------------------------------------------------ json + legend
def bbox_dims(p):
    xs = [q[0] for q in p]; ys = [q[1] for q in p]
    return round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)


out = {'schema': 'volunteers_hamlet_plan/1', 'revision': REV, 'units': 'metres, world map v11 coordinates (x east, y north)',
       'source': 'build_hutor_v02.py', 'objects': [], 'power_poles': [[round(c, 2) for c in q] for q in pole_pts],
       'wires': [[[round(c, 2) for c in q] for q in chain] for chain in poles],
       'service_drops': [[[round(c, 2) for c in q], [round(c, 2) for c in h]] for q, h in drops]}
for it in items:
    geo = it.get('poly') or it.get('line')
    out['objects'].append({'kind': it['kind'], 'layer': it['layer'], ('polygon_m' if it.get('poly') else 'polyline_m'):
                           [[round(c, 2) for c in q] for q in geo], 'note': it['note']})
OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
from collections import Counter
cnt = Counter(it['kind'] for it in items)
with open(OUT_LEG, 'w', encoding='utf-8-sig') as f:
    f.write(f'ХУТОР {REV} — VOLUNTEERS ONLY (перепланировка под настоящие размеры, TASK-000547)\n')
    for num, text in sorted(legend):
        f.write(f'{num:02d} — {text}.\n')
    f.write(f'\nЖилых домов: {len(houses)} (избы 6–7×8–9,5 м, кирпичные 7–8×9–10,5 м, Г-образные, двухэтажные 8–9×10–11,5 м, '
            f'под шифером/жестью 6–7×7,5–9 м), без заборов между ними.\n')
    f.write('Хозпостройки за домами: ' + ', '.join(f'{k} ×{v}' for k, v in sorted(cnt.items()) if k in (
        'shed', 'chicken_coop', 'outhouse', 'banya', 'woodpile', 'greenhouse', 'summer_kitchen', 'garage', 'dog_kennel')) + '.\n')
    f.write(f'Огородов: {cnt["garden"]}, фруктовых деревьев: {cnt["fruit_tree"]}, кустов: {cnt["bush"] + cnt["overgrowth"]}, '
            f'деревьев вдоль улиц: {cnt["tree"]}, берёз: {cnt["birch"]}, ив у пруда: {cnt["willow"]}.\n')
    f.write(f'Деревянных столбов с проводами: {len(pole_pts)} (через ~31 м вдоль главных улиц), отводов проводов к домам: {len(drops)}.\n')
    f.write('Бежевые полосы — грунтовые улицы v11 (не менялись), синий пунктир — тропа к реке.\n')
print('houses', len(houses), 'poles', len(pole_pts), 'objects', len(items))
print(dict(cnt))
