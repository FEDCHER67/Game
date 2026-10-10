"""MAP_ILLUSTRATED v09 -> v12 (Vadim, TASK-000267, reference: a palm-lined beachfront parking lot): only the harbour
beach changes. Same clearing as v10/v11; on top of it a long asphalt beachfront parking along the whole beach, open to
both roads: three rows of slanted stalls full of cars, a palm median, a promenade with a low sea wall, palms and
ramps down to the sand, two ATMs on the promenade; below it the sand with scattered umbrellas, loungers and NPCs.
Plain Python + Pillow:  python edit_v12.py
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
SRC, OUT = HERE / 'MAP_ILLUSTRATED_v09.png', HERE / 'MAP_ILLUSTRATED_v12.png'
S = 4


def layer(img, box, fn):
    w, h = box[2] - box[0], box[3] - box[1]
    big = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    fn(ImageDraw.Draw(big), lambda x, y: ((x - box[0]) * S, (y - box[1]) * S))
    base = img.convert('RGBA')
    base.alpha_composite(big.resize((w, h), Image.LANCZOS), box[:2])
    return base.convert('RGB')


def main():
    if OUT.exists():
        raise SystemExit(f'Refusing to overwrite {OUT.name}')
    img = Image.open(SRC).convert('RGB')
    px = img.load()
    sand, grass = px[700, 760], px[985, 690]
    # 1) clear the tourist stuff: everything between the river bank and the water, between the two roads
    zone = Image.new('L', img.size, 0)
    ImageDraw.Draw(zone).polygon([(552, 648), (950, 648), (954, 760), (950, 830), (560, 830), (545, 700)], fill=255)
    water = Image.new('L', img.size, 0)
    wp = water.load()
    for y in range(766, 840):                               # the bay only (not the pool)
        for x in range(530, 970):
            r, g, b = px[x, y]
            if b > 200 and r < 140 and g > 150:
                wp[x, y] = 255
    water = water.filter(ImageFilter.MaxFilter(5))
    clear = ImageChops.subtract(zone, water)
    gr = Image.new('L', img.size, 0)                         # grass strip along the river, sand below it
    ImageDraw.Draw(gr).polygon([(545, 648), (955, 648), (955, 656), (545, 656)], fill=255)
    gr = gr.filter(ImageFilter.GaussianBlur(4))
    fill = Image.composite(Image.new('RGB', img.size, grass), Image.new('RGB', img.size, sand), gr)
    img = Image.composite(fill, img, clear.filter(ImageFilter.GaussianBlur(1.2)))
    # the wooden jetty standing in the bay becomes water
    sea = px[760, 806]
    jet = Image.new('L', img.size, 0)
    jp, ip = jet.load(), img.load()
    for y in range(768, 835):
        for x in range(800, 845):
            r, g, b = ip[x, y]
            if r - b > 35 and r < 200 and g < 175:          # wooden boards and their dark posts
                jp[x, y] = 255
    img = Image.composite(Image.new('RGB', img.size, sea), img, jet.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8)))
    ImageDraw.Draw(jet).rectangle((808, 788, 842, 832), fill=255)       # the jetty's outline and foam traces too
    img = Image.composite(Image.new('RGB', img.size, sea), img, jet.filter(ImageFilter.GaussianBlur(1.5)))
    # rebuild the shoreline where the jetty met the beach: clone the shore from 36 px to the left, shifted down
    src, ip = img.copy(), img.load()
    sp = src.load()
    for x in range(810, 852):
        w = min(1.0, (x - 810) / 4, (851 - x) / 4)
        yt = 782 + (x - 814) * 8.5 / 34
        xs = x - 36
        ys = 777.5 + (xs - 780) * 0.135
        dy = round(yt - ys)
        for y in range(772, 806):
            a, b = sp[xs, y - dy], sp[x, y]
            ip[x, y] = tuple(round(a[i] * w + b[i] * (1 - w)) for i in range(3))
    # the last post of the jetty in open water: clone plain water from the right
    for y in range(800, 830):
        for x in range(799, 815):
            ip[x, y] = sp[x + 16, y]

    def details(d, T):
        rnd = random.Random(12)
        asphalt, kerb, line = (128, 131, 138, 255), (222, 216, 200, 255), (236, 236, 232, 255)
        x0, x1 = 552, 962
        # long beachfront lot, open to the left and the right road
        d.polygon([T(553, 652), T(x1, 652), T(x1, 712), T(540, 712)], fill=kerb)
        d.polygon([T(554, 654), T(x1 + 2, 654), T(x1 + 2, 710), T(542, 710)], fill=asphalt)
        # promenade with a low sea wall and ramps down to the sand
        d.polygon([T(540, 711), T(x1, 711), T(x1, 720), T(536, 720)], fill=(236, 226, 204, 255))
        d.line((T(536, 720.5), T(x1, 720.5)), fill=(150, 138, 116, 255), width=int(1.5 * S))
        for rx in (600, 690, 790, 890):
            d.rectangle((*T(rx, 719), *T(rx + 9, 726)), fill=(236, 226, 204, 255))

        def car(cx, cy):
            c = rnd.choice([(245, 245, 245), (190, 194, 200), (40, 42, 48), (200, 50, 45), (60, 100, 180), (110, 114, 120), (230, 230, 225)])
            d.rounded_rectangle((*T(cx - 2.6, cy - 4.4), *T(cx + 2.6, cy + 4.4)), radius=1.4 * S, fill=(*c, 255), outline=(30, 30, 30, 160), width=S // 2)
            d.rectangle((*T(cx - 1.9, cy - 2.4), *T(cx + 1.9, cy - 0.9)), fill=(70, 90, 110, 255))
            d.rectangle((*T(cx - 1.9, cy + 1.8), *T(cx + 1.9, cy + 2.8)), fill=(70, 90, 110, 220))

        def stalls(y0, y1, start):
            for x in range(start, x1 - 4, 7):
                d.line((T(x, y0), T(x + 2.5, y1)), fill=line, width=S // 2 + 1)
                if rnd.random() < 0.62:
                    car(x + 4.7, (y0 + y1) / 2)
        stalls(655, 666, 566)          # top row along the river bank
        stalls(677, 687, 560)          # rows on both sides of the palm median
        stalls(692, 702, 556)
        d.line((T(560, 671.5), T(x1, 671.5)), fill=(200, 200, 196, 160), width=S // 2)
        d.line((T(552, 706), T(x1, 706)), fill=(200, 200, 196, 160), width=S // 2)
        d.rounded_rectangle((*T(570, 687.5), *T(x1 - 18, 691.5)), radius=2 * S, fill=kerb)

        def palm(x, y, r=8, rot=0.3):
            d.ellipse((*T(x - r + 4, y - r * 0.6 + 5), *T(x + r + 4, y + r * 0.6 + 5)), fill=(40, 40, 30, 70))
            for k in range(7):
                t = rot + k * 2 * math.pi / 7
                ux, uy, nx, ny = math.cos(t), math.sin(t), -math.sin(t), math.cos(t)
                tip = (x + ux * r, y + uy * r)
                mid = (x + ux * r * 0.45, y + uy * r * 0.45)
                pts = [(x, y), (mid[0] + nx * r * 0.22, mid[1] + ny * r * 0.22), tip, (mid[0] - nx * r * 0.22, mid[1] - ny * r * 0.22)]
                d.polygon([T(*p) for p in pts], fill=(58, 150, 72, 255), outline=(36, 100, 52, 255))
                d.line((T(x, y), T(*tip)), fill=(120, 190, 100, 255), width=S // 2)
            d.ellipse((*T(x - 1.6, y - 1.6), *T(x + 1.6, y + 1.6)), fill=(140, 100, 60, 255))

        # two ATMs on the promenade next to a ramp
        for x in (706, 715):
            d.rounded_rectangle((*T(x + 1, 712), *T(x + 8, 721)), radius=S, fill=(40, 40, 40, 110))
            d.rounded_rectangle((*T(x, 711), *T(x + 7, 720)), radius=S, fill=(60, 96, 150, 255), outline=(40, 52, 70, 255), width=S)
            d.rectangle((*T(x + 2, 712.5), *T(x + 5, 715.5)), fill=(170, 220, 240, 255))

        def lounger(x, y):
            d.rounded_rectangle((*T(x - 2.2, y - 5), *T(x + 2.2, y + 5)), radius=1.5 * S, fill=(250, 250, 248, 255), outline=(160, 160, 160, 255), width=S)

        def umbrella(x, y, c):
            d.ellipse((*T(x - 4, y - 3), *T(x + 9, y + 9)), fill=(150, 120, 80, 70))
            for k in range(8):
                d.pieslice((*T(x - 5.5, y - 5.5), *T(x + 5.5, y + 5.5)), 45 * k, 45 * (k + 1), fill=c if k % 2 == 0 else (250, 248, 244, 255))
            d.ellipse((*T(x - 5.5, y - 5.5), *T(x + 5.5, y + 5.5)), outline=tuple(v * 2 // 3 for v in c[:3]) + (255,), width=S)

        reds, blue, yel = (220, 60, 50, 255), (60, 140, 220, 255), (240, 190, 50, 255)
        spots = (((585, 752), blue), ((640, 742), reds), ((735, 744), yel), ((770, 760), blue), ((835, 748), reds), ((905, 752), blue), ((680, 766), yel))
        for (x, y), c in spots:
            lounger(x - 3.2, y + 8)
            lounger(x + 3.2, y + 8)
        for (x, y), c in spots:
            umbrella(x, y, c)
        # towels and people scattered on the sand
        for x, y, c in ((612, 736, (240, 120, 160)), (700, 738, (90, 160, 230)), (805, 736, (250, 210, 70)), (868, 742, (120, 200, 140)), (655, 775, (250, 140, 60))):
            d.rectangle((*T(x, y), *T(x + 4, y + 7)), fill=(*c, 255))
        skin = (238, 196, 160, 255)
        for (x, y), c in (((622, 758), (230, 90, 70)), ((712, 752), (90, 140, 220)), ((752, 770), (240, 200, 60)), ((760, 773), (120, 60, 160)),
                          ((818, 766), (70, 170, 120)), ((880, 768), (230, 90, 70)), ((600, 730), (60, 60, 70)), ((852, 728), (240, 240, 240))):
            d.ellipse((*T(x - 2.2, y - 1.2), *T(x + 3.2, y + 3.4)), fill=(150, 120, 80, 90))
            d.ellipse((*T(x - 2.6, y - 2.6), *T(x + 2.6, y + 2.6)), fill=(*c, 255), outline=(60, 60, 60, 200), width=S // 2)
            d.ellipse((*T(x - 1.5, y - 1.5), *T(x + 1.5, y + 1.5)), fill=skin)
        # palms: a row on the median and a row along the promenade
        for i, x in enumerate(range(588, x1 - 20, 44)):
            palm(x, 689, r=8, rot=0.4 * i)
        for i, x in enumerate(range(566, x1 - 10, 40)):
            palm(x, 716, r=9, rot=0.3 + 0.5 * i)
    img = layer(img, (540, 640, 970, 800), details)
    img.save(OUT)
    print(OUT.name, img.size)


if __name__ == '__main__':
    main()
