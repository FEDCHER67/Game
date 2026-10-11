"""MAP_ILLUSTRATED v09 -> v10 (Vadim, TASK-000265): only the harbour beach changes, every other pixel is copied.
The beach becomes simple: the club, pool, palms, cafes, volleyball court and jetty are cleared to sand and a grass
strip; added are a small parking right at the beach (drop-off point), two ATMs at the beach entrance by the parking,
short paths from the road and the parking to the sand, and two small groups of loungers with umbrellas.
Plain Python + Pillow:  python edit_v10.py
"""
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
SRC, OUT = HERE / 'MAP_ILLUSTRATED_v09.png', HERE / 'MAP_ILLUSTRATED_v10.png'
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
        # paths: from the left road and from the parking down to the sand
        for path, w in (([(548, 690), (590, 705), (630, 728)], 6), ([(905, 728), (880, 745), (860, 760)], 6)):
            d.line([T(*p) for p in path], fill=road_edge, width=int((w + 2) * S), joint='curve')
            d.line([T(*p) for p in path], fill=road, width=int(w * S), joint='curve')
        # small parking right by the road at the beach: drop-off point
        d.rounded_rectangle((*T(882, 690), *T(952, 726)), radius=3 * S, fill=(150, 152, 158, 255), outline=(110, 112, 118, 255), width=S)
        for k in range(6):
            x = 890 + k * 10
            d.line((T(x, 692), T(x, 704)), fill=(245, 245, 245, 255), width=S)
        d.line((T(950, 708), T(962, 708)), fill=(150, 152, 158, 255), width=10 * S)    # exit to the road
        # two ATMs at the beach entrance next to the parking
        for x in (893, 906):
            d.rounded_rectangle((*T(x + 1, 732), *T(x + 9, 744)), radius=S, fill=(90, 90, 90, 120))
            d.rounded_rectangle((*T(x, 730), *T(x + 8, 742)), radius=S, fill=(60, 96, 150, 255), outline=(40, 52, 70, 255), width=S)
            d.rectangle((*T(x + 2, 732), *T(x + 6, 736)), fill=(170, 220, 240, 255))
        # two small groups of loungers with umbrellas
        def lounger(x, y):
            d.rounded_rectangle((*T(x - 2.4, y - 5.5), *T(x + 2.4, y + 5.5)), radius=1.5 * S, fill=(250, 250, 248, 255), outline=(160, 160, 160, 255), width=S)

        def umbrella(x, y):
            for k in range(8):
                d.pieslice((*T(x - 6, y - 6), *T(x + 6, y + 6)), 45 * k, 45 * (k + 1), fill=(220, 60, 50, 255) if k % 2 == 0 else (250, 248, 244, 255))
            d.ellipse((*T(x - 6, y - 6), *T(x + 6, y + 6)), outline=(150, 60, 50, 255), width=S)

        def tree(x, y, r=7):
            d.ellipse((*T(x - r + 2, y - r + 3), *T(x + r + 2, y + r + 3)), fill=(60, 90, 50, 110))
            d.ellipse((*T(x - r, y - r), *T(x + r, y + r)), fill=(70, 150, 80, 255), outline=(46, 110, 60, 255), width=S)
            d.ellipse((*T(x - r * 0.5, y - r * 0.6), *T(x + r * 0.1, y - r * 0.1)), fill=(110, 185, 100, 255))
        for x, y in ((580, 662), (622, 668), (684, 660), (735, 666), (812, 662), (858, 668), (930, 664)):
            tree(x, y)
        for cx, cy in ((650, 752), (790, 756)):
            for dx in (-10, 0, 10):
                lounger(cx + dx, cy + 5)
            umbrella(cx - 5, cy - 4)
            umbrella(cx + 7, cy - 3)
        # a few NPCs chilling: lying on loungers and standing on the sand
        skin = (238, 196, 160, 255)
        for (x, y), c in (((640, 757), (90, 140, 220)), ((660, 757), (230, 120, 60)), ((780, 761), (70, 170, 120)), ((790, 761), (200, 80, 140))):
            d.rounded_rectangle((*T(x - 1.6, y - 2), *T(x + 1.6, y + 4)), radius=S, fill=(*c, 255))
            d.ellipse((*T(x - 1.6, y - 5), *T(x + 1.6, y - 1.8)), fill=skin)
        for (x, y), c in (((705, 772), (240, 200, 60)), ((716, 776), (90, 140, 220)), ((604, 768), (230, 90, 70))):
            d.ellipse((*T(x - 2.4, y - 1.4), *T(x + 3.4, y + 3.6)), fill=(150, 120, 80, 90))
            d.ellipse((*T(x - 3, y - 3), *T(x + 3, y + 3)), fill=(*c, 255), outline=(60, 60, 60, 200), width=S // 2)
            d.ellipse((*T(x - 1.7, y - 1.7), *T(x + 1.7, y + 1.7)), fill=skin)
    img = layer(img, (540, 640, 970, 800), details)
    img.save(OUT)
    print(OUT.name, img.size)


if __name__ == '__main__':
    main()
