"""MAP_ILLUSTRATED v09 -> v11 (Vadim, TASK-000266): revision of v10, again only the harbour beach changes.
Same clearing as v10 (club, pool, palms, cafes, volleyball court, jetty -> sand and a grass strip); on top of it:
a big plain asphalt entry/drop-off area in front of the beach, open to the right road, two ATMs at its beach edge,
a path from the left road, umbrellas with loungers spread over the sand, palms, a few NPCs chilling.
Plain Python + Pillow:  python edit_v11.py
"""
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
SRC, OUT = HERE / 'MAP_ILLUSTRATED_v09.png', HERE / 'MAP_ILLUSTRATED_v11.png'
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
    ImageDraw.Draw(gr).polygon([(545, 648), (955, 648), (955, 690), (760, 700), (545, 692)], fill=255)
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
        road_edge, road = (214, 196, 168, 255), (250, 248, 240, 255)
        # path from the left road down to the sand
        path = [(548, 690), (590, 705), (630, 728)]
        d.line([T(*p) for p in path], fill=road_edge, width=8 * S, joint='curve')
        d.line([T(*p) for p in path], fill=road, width=6 * S, joint='curve')
        # big plain asphalt entry area in front of the beach, open to the right road (drop-off, cars park anywhere)
        d.rounded_rectangle((*T(755, 650), *T(962, 732)), radius=8 * S, fill=(225, 220, 205, 255))
        d.rounded_rectangle((*T(757, 652), *T(964, 730)), radius=7 * S, fill=(128, 131, 138, 255))
        # two ATMs at the beach edge of the asphalt
        for x in (872, 886):
            d.rounded_rectangle((*T(x + 1, 717), *T(x + 9, 729)), radius=S, fill=(40, 40, 40, 110))
            d.rounded_rectangle((*T(x, 715), *T(x + 8, 727)), radius=S, fill=(60, 96, 150, 255), outline=(40, 52, 70, 255), width=S)
            d.rectangle((*T(x + 2, 717), *T(x + 6, 721)), fill=(170, 220, 240, 255))

        def lounger(x, y):
            d.rounded_rectangle((*T(x - 2.4, y - 5.5), *T(x + 2.4, y + 5.5)), radius=1.5 * S, fill=(250, 250, 248, 255), outline=(160, 160, 160, 255), width=S)

        def umbrella(x, y, c):
            d.ellipse((*T(x - 4, y - 3), *T(x + 9, y + 9)), fill=(150, 120, 80, 70))
            for k in range(8):
                d.pieslice((*T(x - 6, y - 6), *T(x + 6, y + 6)), 45 * k, 45 * (k + 1), fill=c if k % 2 == 0 else (250, 248, 244, 255))
            d.ellipse((*T(x - 6, y - 6), *T(x + 6, y + 6)), outline=tuple(v * 2 // 3 for v in c[:3]) + (255,), width=S)

        def tree(x, y, r=7):
            d.ellipse((*T(x - r + 2, y - r + 3), *T(x + r + 2, y + r + 3)), fill=(60, 90, 50, 110))
            d.ellipse((*T(x - r, y - r), *T(x + r, y + r)), fill=(70, 150, 80, 255), outline=(46, 110, 60, 255), width=S)
            d.ellipse((*T(x - r * 0.5, y - r * 0.6), *T(x + r * 0.1, y - r * 0.1)), fill=(110, 185, 100, 255))

        def palm(x, y, r=9, rot=0.3):
            d.ellipse((*T(x - r + 3, y - r * 0.6 + 4), *T(x + r + 3, y + r * 0.6 + 4)), fill=(120, 110, 60, 80))
            for k in range(7):
                t = rot + k * 2 * math.pi / 7
                ux, uy, nx, ny = math.cos(t), math.sin(t), -math.sin(t), math.cos(t)
                tip = (x + ux * r, y + uy * r)
                mid = (x + ux * r * 0.45, y + uy * r * 0.45)
                pts = [(x, y), (mid[0] + nx * r * 0.22, mid[1] + ny * r * 0.22), tip, (mid[0] - nx * r * 0.22, mid[1] - ny * r * 0.22)]
                d.polygon([T(*p) for p in pts], fill=(58, 150, 72, 255), outline=(36, 100, 52, 255))
                d.line((T(x, y), T(*tip)), fill=(120, 190, 100, 255), width=S // 2)
            d.ellipse((*T(x - 1.6, y - 1.6), *T(x + 1.6, y + 1.6)), fill=(140, 100, 60, 255))

        for x, y in ((580, 662), (622, 668), (684, 660), (722, 668)):
            tree(x, y)
        # umbrellas with two loungers each, spread over the sand; free sand stays between them
        reds, blue, yel = (220, 60, 50, 255), (60, 120, 210, 255), (240, 190, 50, 255)
        spots = (((600, 748), reds), ((652, 738), blue), ((700, 730), yel), ((750, 742), reds), ((806, 748), blue),
                 ((856, 752), yel), ((676, 764), reds), ((728, 760), blue), ((910, 750), reds))
        for (x, y), c in spots:
            lounger(x - 3.5, y + 9)
            lounger(x + 3.5, y + 9)
        for (x, y), c in spots:
            umbrella(x, y, c)
        for x, y, rot in ((572, 718, 0.2), (624, 704, 1.0), (735, 708, 0.5), (780, 742, 1.3), (836, 744, 0.1),
                          (884, 748, 0.8), (938, 740, 0.4), (590, 785, 0.9), (700, 752, 0.6)):
            palm(x, y, rot=rot)
        # a few NPCs chilling: lying on loungers and standing on the sand
        skin = (238, 196, 160, 255)
        for (x, y), c in (((596.5, 757), (90, 140, 220)), ((655.5, 747), (230, 120, 60)), ((746.5, 751), (70, 170, 120)),
                          ((809.5, 757), (200, 80, 140)), ((859.5, 761), (240, 200, 60))):
            d.rounded_rectangle((*T(x - 1.6, y - 2), *T(x + 1.6, y + 4)), radius=S, fill=(*c, 255))
            d.ellipse((*T(x - 1.6, y - 5), *T(x + 1.6, y - 1.8)), fill=skin)
        for (x, y), c in (((760, 772), (240, 200, 60)), ((771, 775), (90, 140, 220)), ((626, 778), (230, 90, 70)), ((900, 724), (120, 60, 160))):
            d.ellipse((*T(x - 2.4, y - 1.4), *T(x + 3.4, y + 3.6)), fill=(150, 120, 80, 90))
            d.ellipse((*T(x - 3, y - 3), *T(x + 3, y + 3)), fill=(*c, 255), outline=(60, 60, 60, 200), width=S // 2)
            d.ellipse((*T(x - 1.7, y - 1.7), *T(x + 1.7, y + 1.7)), fill=skin)
    img = layer(img, (540, 640, 970, 800), details)
    img.save(OUT)
    print(OUT.name, img.size)


if __name__ == '__main__':
    main()
