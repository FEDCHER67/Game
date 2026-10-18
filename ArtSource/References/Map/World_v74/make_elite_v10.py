"""План Элитного холма v10 (TASK-000827, Вадим 18.10.2026) из v22_assets/elite_v09_world_white.png (6 px/м, левый верх = мир
x 1260, y 450 до сдвига v73):
- серпантин на западном склоне убран (вместо него кольцевая дорога вокруг холма — рисуется на карте v74, build_world_v74.py);
- выхода из посёлка на пляж нет: ворота 08 и лестница 12 убраны, забор сплошной;
- виллы стоят вразнобой: каждый участок повёрнут и чуть сдвинут;
- плато неровное: отметки высот +40…+44 м и пара горизонталей.
Выход: v74_assets/elite_v10_world.png. v09 не меняется."""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'v22_assets', 'elite_v09_world_white.png')
OUTD = os.path.join(HERE, 'v74_assets')
os.makedirs(OUTD, exist_ok=True)
OUT = os.path.join(OUTD, 'elite_v10_world.png')
assert not os.path.exists(OUT)
PPM, X0, Y0 = 6.0, 1260.0, 450.0
HILL, PLATEAU, FENCE, SAND = (226, 235, 210, 255), (222, 233, 206, 255), (70, 88, 62, 255), (247, 242, 224, 255)
r = random.Random(827)
im = Image.open(SRC).convert('RGBA')
W, H = im.size


def px(x, y):
    return ((x - X0) * PPM, (Y0 - y) * PPM)


def patch(poly_px, colour, feather=4):
    """Залить многоугольник цветом с мягким краем."""
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).polygon(poly_px, fill=255)
    if feather:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    im.paste(Image.new('RGBA', im.size, colour), (0, 0), m)


# 1) серпантин: всё к западу от забора, кроме будки охраны у ворот и подхода к воротам
patch([(0, 300), (392, 300), (392, 568), (356, 568), (356, 662), (392, 662), (392, 1000), (0, 1000)], HILL, 3)
patch([(330, 104), (770, 104), (770, 206), (330, 206)], HILL, 5)            # своя подпись «07 ELITE HILL» (подпись — на карте)
# 2) ворота 08 и лестница 12 к пляжу
patch([(1263, 525), (1320, 525), (1320, 668), (1263, 668)], HILL, 3)
patch([(1240, 528), (1255, 528), (1255, 664), (1240, 664)], PLATEAU, 2)
patch([(1266, 596), (1372, 596), (1372, 840), (1266, 840)], SAND, 6)
d = ImageDraw.Draw(im)
patch([(1214, 494), (1256, 494), (1256, 538), (1214, 538)], PLATEAU, 2)   # метка 08
patch([(1354, 730), (1408, 730), (1408, 784), (1354, 784)], SAND, 3)       # метка 12
patch([(1262, 690), (1290, 690), (1290, 740), (1262, 740)], SAND, 3)       # верх лестницы
d = ImageDraw.Draw(im)
d.rectangle((1256, 520, 1261, 672), fill=FENCE)                      # забор снова сплошной
# 3) участки вилл вразнобой: поворот и небольшой сдвиг
plots = [((404, 264, 716, 486), -5.0, (-8, 6)), ((940, 264, 1250, 486), -9.0, (7, -2)),
         ((940, 708, 1252, 934), 4.0, (5, 6)), ((404, 714, 710, 934), 10.0, (-7, -4))]
for (x0, y0, x1, y1), ang, (dx, dy) in plots:
    crop = im.crop((x0, y0, x1, y1))
    cp = crop.load()
    mask = Image.new('L', crop.size, 0)
    mp = mask.load()
    for y in range(crop.height):
        for x in range(crop.width):
            c = cp[x, y]
            if abs(c[0] - PLATEAU[0]) + abs(c[1] - PLATEAU[1]) + abs(c[2] - PLATEAU[2]) > 12:
                mp[x, y] = 255
    mask = mask.filter(ImageFilter.MaxFilter(5))
    im.paste(Image.new('RGBA', crop.size, PLATEAU), (x0, y0), mask)    # стереть старый участок
    rc = crop.rotate(ang, resample=Image.BICUBIC, fillcolor=PLATEAU)
    rm = mask.rotate(ang, resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.8))
    im.paste(rc, (x0 + dx, y0 + dy), rm)
# 4) неровное плато: горизонтали и отметки высот
d = ImageDraw.Draw(im)
CONT = (200, 216, 186, 255)
for cx, cy, rx, ry, a0, a1 in ((700, 470, 60, 26, 200, 340), (760, 920, 70, 22, 20, 160), (360, 470, 0, 0, 0, 0)):
    if rx:
        pts = [(cx + rx * math.cos(math.radians(a)) + r.uniform(-2, 2), cy + ry * math.sin(math.radians(a)) + r.uniform(-2, 2)) for a in range(a0, a1 + 1, 10)]
        d.line(pts, fill=CONT, width=3)
try:
    F = ImageFont.truetype(r'C:\Windows\Fonts\ariali.ttf', 26)
except OSError:
    F = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 26)
for (x, y), t in (((770, 290), '+44 м'), ((470, 660), '+41 м'), ((1120, 660), '+43 м'), ((770, 890), '+40 м')):
    d.text((x, y), t, font=F, fill=(120, 140, 128, 255))
# 5) деревья на бывшем серпантине (вне коридора кольцевой дороги ~ x 0..330 по картинке, y 170..620)
RING_W = [(1258, 352), (1268, 375), (1282, 400), (1300, 417), (1330, 422), (1304, 305), (1305, 330), (1312, 346), (1327, 351)]


def near_ring(x, y):
    p = [(px(a, b)) for a, b in RING_W]
    return any(math.hypot(x - qx, y - qy) < 80 for qx, qy in p)


for _ in range(70):
    x, y = r.uniform(10, 380), r.uniform(320, 990)
    if near_ring(x, y) or (340 < x < 400 and 560 < y < 670):
        continue
    rr = r.uniform(14, 26)
    d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(185, 209, 159, 255), outline=(160, 190, 135, 255), width=2)
im.save(OUT)
print(OUT, im.size)
