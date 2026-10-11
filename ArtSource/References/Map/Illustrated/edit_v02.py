"""MAP_ILLUSTRATED v01 -> v02 (Vadim, TASK-000257). Only these sectors change, every other pixel is copied:
- no railway in the industrial zone (the rail and the wagon on it are painted out);
- forest: a collapsed tunnel where the railway enters the map (stone portal blocked with rocks), the rail inside ends at
  the wagon; a small clearing round the wagon; the lake is rounder; forest trails in the map's road style; a camp with
  a fire pit; a swampy patch in the far left of the forest.
Plain Python + Pillow:  python edit_v02.py
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
SRC, OUT = HERE / 'MAP_ILLUSTRATED_v01.png', HERE / 'MAP_ILLUSTRATED_v02.png'
S = 4                                        # supersampling for drawn details
rnd = random.Random(5)


def mask_where(img, box, test):
    m = Image.new('L', img.size, 0)
    px, mp = img.load(), m.load()
    for y in range(box[1], box[3]):
        for x in range(box[0], box[2]):
            if test(px[x, y]):
                mp[x, y] = 255
    return m


def diffuse(img, hole, iters=90, radius=2.5):
    """Fill the hole (L mask) from its surroundings by repeated blurring inside the hole's box."""
    box = hole.getbbox()
    if not box:
        return img
    box = (max(0, box[0] - 8), max(0, box[1] - 8), min(img.width, box[2] + 8), min(img.height, box[3] + 8))
    region, known, h = img.crop(box), img.crop(box), hole.crop(box)
    for _ in range(iters):
        region = Image.composite(region.filter(ImageFilter.GaussianBlur(radius)), known, h)
    out = img.copy()
    out.paste(region, box[:2])
    return out


def layer(img, box, draw_fn):
    """Draw anti-aliased details: draw_fn(draw, T) with T(x, y) mapping image coordinates into the 4x layer."""
    w, h = box[2] - box[0], box[3] - box[1]
    big = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    T = lambda x, y: ((x - box[0]) * S, (y - box[1]) * S)
    draw_fn(d, T)
    small = big.resize((w, h), Image.LANCZOS)
    base = img.convert('RGBA')
    base.alpha_composite(small, box[:2])
    return base.convert('RGB')


def blob(cx, cy, rx, ry, seed, n=40, wob=0.12):
    r = random.Random(seed)
    ph = [r.uniform(0, 6.28) for _ in range(3)]
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        f = 1 + wob * (math.sin(2 * a + ph[0]) * 0.6 + math.sin(3 * a + ph[1]) * 0.4 + math.sin(5 * a + ph[2]) * 0.2)
        pts.append((cx + rx * f * math.cos(a), cy + ry * f * math.sin(a)))
    return pts


def main():
    if OUT.exists():
        raise SystemExit(f'Refusing to overwrite {OUT.name}')
    img = Image.open(SRC).convert('RGB')

    # ---- 1) industrial zone: no railway
    rail = mask_where(img, (562, 748, 920, 784), lambda c: sum(c) < 430 and c[2] - c[0] < 18)
    img = diffuse(img, rail.filter(ImageFilter.MaxFilter(5)), iters=120, radius=3)

    # ---- 2) rounder lake
    lake_old = mask_where(img, (195, 540, 350, 685), lambda c: c[2] > 150 and c[2] - c[0] > 50)
    bb = lake_old.getbbox()
    area = sum(1 for v in lake_old.get_flattened_data() if v)
    cx, cy = (bb[0] + bb[2]) / 2 - 4, (bb[1] + bb[3]) / 2 + 2
    ry = math.sqrt(area / (math.pi * 1.25)) * 1.02
    rx = ry * 1.25
    shape = blob(cx, cy, rx, ry, seed=3, wob=0.11)
    new_lake = Image.new('L', img.size, 0)
    ImageDraw.Draw(new_lake).polygon(shape, fill=255)
    gone = ImageChops.subtract(lake_old.filter(ImageFilter.MaxFilter(9)), new_lake)
    # the old lake's leftover becomes forest: patches of the dense forest next to it, soft edges
    tex = img.copy()
    src = img.crop((60, 470, 150, 545))
    pm = Image.new('L', src.size, 0)
    ImageDraw.Draw(pm).rectangle((10, 10, src.width - 11, src.height - 11), fill=255)
    pm = pm.filter(ImageFilter.GaussianBlur(5))
    gb = gone.getbbox()
    for yy in range(gb[1] - 30, gb[3] + 10, 50):
        for xx in range(gb[0] - 30, gb[2] + 10, 65):
            tex.paste(src, (xx + rnd.randint(-8, 8), yy + rnd.randint(-6, 6)), pm)
    img = Image.composite(tex, img, gone.filter(ImageFilter.GaussianBlur(1.5)))

    def lake(d, T):
        p = [T(x, y) for x, y in shape]
        d.polygon(p, fill=(46, 181, 234, 255), outline=(74, 138, 104, 255), width=int(1.5 * S))
        inner = [T(cx + (x - cx) * 0.93, cy + (y - cy) * 0.93) for x, y in shape]
        d.line(inner + inner[:1], fill=(128, 214, 245, 200), width=int(1.5 * S))
    img = layer(img, (int(cx - rx - 20), int(cy - ry - 20), int(cx + rx + 20), int(cy + ry + 20)), lake)

    # ---- 3) forest trails in the map's road style (white with a beige edge)
    trail = mask_where(img, (0, 460, 365, 875), lambda c: c[0] > 165 and c[0] - c[2] > 40 and 140 < c[1] < 185)
    trail = ImageChops.subtract(trail, new_lake)
    edge = ImageChops.subtract(trail.filter(ImageFilter.MaxFilter(3)), trail)
    img = Image.composite(Image.new('RGB', img.size, (222, 200, 172)), img, edge.filter(ImageFilter.GaussianBlur(0.6)))
    img = Image.composite(Image.new('RGB', img.size, (246, 242, 233)), img, trail.filter(ImageFilter.GaussianBlur(0.5)))

    # ---- 4) clearing round the wagon (the wagon and the rails stay on top)
    protect = mask_where(img, (125, 630, 230, 712), lambda c: (c[0] > c[1] + 25 and c[0] < 200) or (sum(c) < 330 and abs(c[0] - c[2]) < 40))
    clear = Image.new('L', img.size, 0)
    ImageDraw.Draw(clear).polygon(blob(178, 672, 52, 34, seed=8, wob=0.10), fill=255)
    clear = ImageChops.subtract(clear.filter(ImageFilter.GaussianBlur(3)), protect.filter(ImageFilter.MaxFilter(3)))
    img = Image.composite(Image.new('RGB', img.size, (150, 196, 112)), img, clear)

    # ---- 5) swamp in the far left of the forest
    def swamp(d, T):
        for k, (x, y, a, b) in enumerate(((62, 600, 26, 15), (88, 622, 22, 13), (52, 632, 18, 11), (80, 588, 15, 9))):
            d.polygon([T(px, py) for px, py in blob(x, y, a + 5, b + 5, seed=20 + k)], fill=(104, 140, 92, 255))
        for k, (x, y, a, b) in enumerate(((62, 600, 26, 15), (88, 622, 22, 13), (52, 632, 18, 11), (80, 588, 15, 9))):
            d.polygon([T(px, py) for px, py in blob(x, y, a, b, seed=20 + k)], fill=(74, 118, 104, 255),
                      outline=(56, 92, 78, 255), width=S)
        for x, y in ((57, 598), (70, 606), (93, 624), (49, 634), (84, 590), (66, 593)):     # lily pads
            d.ellipse((*T(x - 2.4, y - 1.6), *T(x + 2.4, y + 1.6)), fill=(132, 178, 96, 255))
        for k in range(26):                                                                 # reeds
            x, y = 40 + rnd.random() * 70, 580 + rnd.random() * 62
            d.line((T(x, y), T(x + rnd.uniform(-1, 1), y - rnd.uniform(5, 8))), fill=(78, 92, 52, 255), width=S)
            d.ellipse((*T(x - 0.9, y - 8.5), *T(x + 0.9, y - 5.5)), fill=(120, 84, 52, 255))
    img = layer(img, (25, 565, 125, 655), swamp)

    # ---- 6) camp with a fire pit
    camp_c = (232, 716)
    cm = Image.new('L', img.size, 0)
    ImageDraw.Draw(cm).polygon(blob(*camp_c, 24, 16, seed=11), fill=255)
    img = Image.composite(Image.new('RGB', img.size, (166, 198, 118)), img, cm.filter(ImageFilter.GaussianBlur(2)))

    def camp(d, T):
        x, y = camp_c
        d.ellipse((*T(x - 6, y - 4.5), *T(x + 6, y + 4.5)), fill=(120, 120, 124, 255), outline=(70, 70, 74, 255), width=S)
        d.ellipse((*T(x - 3.6, y - 2.6), *T(x + 3.6, y + 2.6)), fill=(60, 48, 40, 255))
        d.polygon([T(x - 2.6, y + 1), T(x, y - 7), T(x + 2.6, y + 1)], fill=(242, 132, 40, 255))
        d.polygon([T(x - 1.3, y + 1), T(x, y - 4), T(x + 1.3, y + 1)], fill=(255, 220, 90, 255))
        for lx, ly, ang in ((x - 13, y + 2, 10), (x + 12, y + 3, -15)):                   # log benches
            dx, dy = 6 * math.cos(math.radians(ang)), 6 * math.sin(math.radians(ang))
            d.line((T(lx - dx, ly - dy), T(lx + dx, ly + dy)), fill=(126, 82, 50, 255), width=int(3.4 * S))
        tx, ty = x + 2, y - 15                                                              # tent
        d.polygon([T(tx - 9, ty + 6), T(tx, ty - 5), T(tx + 9, ty + 6)], fill=(226, 120, 58, 255), outline=(150, 72, 36, 255), width=S)
        d.polygon([T(tx - 2, ty + 6), T(tx, ty), T(tx + 2, ty + 6)], fill=(110, 56, 30, 255))
    img = layer(img, (205, 690, 260, 740), camp)

    # ---- 7) collapsed tunnel where the railway crosses the map edge
    tx, ty = 70, 721
    ang = math.atan2(745 - 685, 0 - 140)        # rail direction, outwards
    ux, uy = math.cos(ang), math.sin(ang)        # along the rail
    vx, vy = -uy, ux                             # across

    def tunnel(d, T):
        def P(a, b):                             # a: along the rail (outwards +), b: across
            return T(tx + ux * a + vx * b, ty + uy * a + vy * b)
        hill = [P(-6, -22), P(4, -24), P(10, -14), P(12, 0), P(10, 14), P(4, 24), P(-6, 22), P(-10, 0)]
        d.polygon(hill, fill=(140, 132, 120, 255), outline=(82, 78, 72, 255), width=S)
        arch = [P(8, -9)] + [P(8 - 9 * math.sin(math.pi * k / 10), -9 * math.cos(math.pi * k / 10)) for k in range(11)] + [P(8, 9)]
        d.polygon(arch, fill=(46, 44, 46, 255))
        for k, (a, b, r) in enumerate(((7, -5, 3.6), (7, 2, 4.2), (6, 7, 3.0), (10, -1, 3.4), (11, 5, 2.8), (10, -7, 2.6),
                                       (13, 1, 2.4), (4, -2, 2.6), (4, 5, 2.2))):
            c = P(a, b)
            g = 118 + (k * 17) % 40
            d.ellipse((c[0] - r * S, c[1] - r * S, c[0] + r * S, c[1] + r * S), fill=(g, g, g + 4, 255), outline=(70, 70, 74, 255), width=S)
            d.ellipse((c[0] - r * 0.45 * S, c[1] - r * 0.6 * S, c[0] + r * 0.1 * S, c[1] - r * 0.1 * S), fill=(g + 40, g + 40, g + 44, 255))
    img = layer(img, (tx - 40, ty - 40, tx + 40, ty + 40), tunnel)

    img.save(OUT)
    print(OUT.name, img.size)


if __name__ == '__main__':
    main()
