"""MAP_ILLUSTRATED v02 -> v03 (Vadim, TASK-000258), a quick sketch-level edit of the forest only:
a high hill between the forest and the beach (south-east of the forest); a smaller lake moved away from the swamp;
the swamp moved further left and stretched along the left edge of the forest. Plain Python + Pillow."""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from edit_v02 import blob, layer

HERE = Path(__file__).resolve().parent
SRC, OUT = HERE / 'MAP_ILLUSTRATED_v02.png', HERE / 'MAP_ILLUSTRATED_v03.png'
rnd = random.Random(7)


def forest_fill(img, mask):
    """Cover the mask with patches of the dense forest (soft edges)."""
    tex = img.copy()
    src = img.crop((60, 470, 150, 545))
    pm = Image.new('L', src.size, 0)
    ImageDraw.Draw(pm).rectangle((10, 10, src.width - 11, src.height - 11), fill=255)
    pm = pm.filter(ImageFilter.GaussianBlur(5))
    b = mask.getbbox()
    for y in range(b[1] - 30, b[3] + 10, 50):
        for x in range(b[0] - 30, b[2] + 10, 65):
            tex.paste(src, (x + rnd.randint(-8, 8), y + rnd.randint(-6, 6)), pm)
    return Image.composite(tex, img, mask.filter(ImageFilter.GaussianBlur(1.5)))


def main():
    if OUT.exists():
        raise SystemExit(f'Refusing to overwrite {OUT.name}')
    img = Image.open(SRC).convert('RGB')
    # old lake and old swamp become forest
    old = Image.new('L', img.size, 0)
    d = ImageDraw.Draw(old)
    d.ellipse((212, 572, 318, 652), fill=255)        # v02 lake
    d.ellipse((30, 572, 118, 650), fill=255)         # v02 swamp
    img = forest_fill(img, old)

    # swamp: further left, a long marshy strip along the left edge of the forest
    def swamp(dr, T):
        pools = [(62, 545, 13, 20), (58, 585, 14, 19), (64, 625, 14, 17), (70, 660, 12, 15), (80, 600, 10, 10)]
        for k, (x, y, a, b) in enumerate(pools):
            dr.polygon([T(px, py) for px, py in blob(x, y, a + 6, b + 6, seed=40 + k)], fill=(112, 146, 96, 255))
        for k, (x, y, a, b) in enumerate(pools):
            dr.polygon([T(px, py) for px, py in blob(x, y, a, b, seed=40 + k)], fill=(76, 118, 104, 255))
        for k in range(30):
            x, y = 50 + rnd.random() * 34, 530 + rnd.random() * 150
            dr.line((T(x, y), T(x, y - 6)), fill=(80, 92, 54, 255), width=4)
    img = layer(img, (30, 515, 110, 690), swamp)

    # smaller lake, up near the north edge of the forest, away from the swamp
    def lake(dr, T):
        shape = blob(292, 548, 24, 17, seed=9, wob=0.12)
        dr.polygon([T(x, y) for x, y in shape], fill=(46, 181, 234, 255), outline=(74, 138, 104, 255), width=6)
    img = layer(img, (260, 525, 325, 572), lake)

    # high hill between the forest and the beach (south-east of the forest)
    def hill(dr, T):
        rings = [((300, 780, 120, 26), (128, 150, 92)), ((300, 776, 96, 19), (146, 162, 100)),
                 ((298, 772, 70, 13), (166, 172, 110)), ((296, 769, 40, 7), (186, 182, 128))]
        for k, ((x, y, a, b), col) in enumerate(rings):
            dr.polygon([T(px, py) for px, py in blob(x, y, a, b, seed=60 + k, wob=0.08)], fill=(*col, 255),
                       outline=(104, 120, 76, 255), width=3)
    img = layer(img, (170, 745, 430, 812), hill)
    img.save(OUT)
    print(OUT.name)


if __name__ == '__main__':
    main()
