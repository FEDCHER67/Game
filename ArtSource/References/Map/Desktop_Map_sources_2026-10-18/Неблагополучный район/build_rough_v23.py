"""Неблагополучный район — план v23 (TASK-000587), от v22:
- магазин 3 в масштабе ~20×10 м (было ~31×18), ларьки по бокам придвинуты;
- СЗ: вместо двора-колодца 9 — 3 параллельных горизонтальных хрущёвки (как у GPT), арки в нижних двух, подъезды на юг;
- двор 12 больше: длинный дом снизу убран, детская площадка 18, рядом мусорная площадка (2 больших бункера + 4 зелёных бака), без лавочек;
- ЮВ: двор-колодец с притоном 5 внутри: дом сверху, дом справа, дом вдоль южной дороги, с запада — длинный дом;
  въезд в колодец — проезд ~11 м в ЮЗ углу, СВ угол закрыт гаражами; 14 — щель-закоулок между клубом и длинным домом.
Не перезаписывает. Запуск: python build_rough_v23.py -> Неблагополучный_район_v23.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v22.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v23.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
CLUB, CLUB_OUT = (178, 150, 168), (88, 64, 84)
SHOP, SHOP_OUT = (215, 167, 146), (122, 70, 58)
BIN, BIN_OUT = (104, 140, 104), (52, 74, 56)
SKIP, SKIP_OUT = (84, 120, 92), (40, 60, 46)
ARCH, ARCH_L = (246, 247, 240), (120, 128, 132)
FENCE = (112, 119, 119)
ANCHOR = (200, 130, 60)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)


def house(x0, y0, x1, y1, doors=0):
    dr.rectangle([x0, y0, x1, y1], fill=FILL, outline=OUTL, width=3)
    for k in range(doors):                                   # подъезды на юг
        dx = x0 + (x1 - x0) * (k + 0.5) / doors
        dr.rectangle([dx - 11, y1 + 1, dx + 11, y1 + 5], fill=(130, 140, 148))


def arch(x0, y0, x1, y1):
    dr.rectangle([x0, y0, x1, y1], fill=ARCH)
    dr.line([(x0 + 4, y0), (x0 + 4, y1)], fill=ARCH_L, width=2)
    dr.line([(x1 - 4, y0), (x1 - 4, y1)], fill=ARCH_L, width=2)


def label(t, x, y):
    dr.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(255, 255, 255), outline=(60, 70, 80), width=2)
    dr.text((x, y), t, font=F, fill=(40, 50, 60), anchor='mm')


def anchor(x, y):
    dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=ANCHOR, width=3)


def garage(x0, y0, x1, y1):
    dr.rectangle([x0, y0, x1, y1], fill=GAR, outline=GAR_OUT, width=2)


# ------------------------------------------------ 3 магазин в масштабе ~20×10 м
dr.rectangle([1112, 1405, 1470, 1556], fill=BG)
dr.rectangle([1209, 1472, 1371, 1553], fill=SHOP, outline=SHOP_OUT, width=3)
garage(1176, 1480, 1204, 1546); garage(1376, 1480, 1404, 1546)          # ларьки по бокам
label('3', 1290, 1510)

# ------------------------------------------------ СЗ: 3 параллельные хрущёвки вместо колодца 9
dr.rectangle([108, 330, 452, 760], fill=BG)
dr.rectangle([116, 216, 702, 226], fill=BG)                              # под верхним домом место под подъезды
dr.rectangle([118, 110, 700, 215], outline=OUTL, width=3)
for k in range(4):
    dx = 118 + 582 * (k + 0.5) / 4
    dr.rectangle([dx - 11, 216, dx + 11, 220], fill=(130, 140, 148))
house(118, 341, 490, 446, 3)                                            # средний — короче
house(118, 598, 610, 703, 4)                                            # нижний
arch(270, 598, 322, 703)                                                # арка в нижнем доме — проход к 11
arch(380, 341, 430, 446)                                                # арка в среднем доме
label('9', 300, 520); label('10', 296, 650)

# ------------------------------------------------ правая часть: снести всё ниже двора 12 (длинный дом, клуб, дома)
dr.rectangle([1712, 816, 2440, 1584], fill=BG)
dr.rectangle([1720, 405, 2205, 830], fill=BG)                           # двор 12 начисто (без лавочек)
dr.rectangle([1596, 909, 1706, 1529], fill=FILL, outline=OUTL, width=3)

# двор 12: детская площадка 18 и рядом мусорная площадка
dr.rectangle([1800, 560, 2040, 740], fill=(232, 220, 178), outline=(170, 150, 100), width=2)
dr.rectangle([1825, 590, 1875, 620], outline=(120, 100, 70), width=2)   # горка
dr.rectangle([1905, 590, 1965, 615], outline=(120, 100, 70), width=2)   # качели
dr.rectangle([1990, 585, 2020, 640], outline=(120, 100, 70), width=2)   # турник
dr.ellipse([1835, 670, 1885, 720], outline=(120, 100, 70), width=2)     # песочница
label('18', 1950, 690)
# мусорная площадка: бетон, профлист с трёх сторон (открыта на юг), 2 больших бункера + 4 зелёных бака
px0, py0, px1, py1 = 2070, 640, 2195, 720
dr.rectangle([px0, py0, px1, py1], fill=(206, 204, 196))
for seg in ([(px0, py0), (px1, py0)], [(px0, py0), (px0, py1)], [(px1, py0), (px1, py1)]):
    dr.line(seg, fill=FENCE, width=4)
dr.rectangle([px0 + 8, py0 + 8, px0 + 48, py0 + 30], fill=SKIP, outline=SKIP_OUT, width=2)
dr.rectangle([px0 + 56, py0 + 8, px0 + 96, py0 + 30], fill=SKIP, outline=SKIP_OUT, width=2)
for k in range(4):
    dr.rectangle([px0 + 10 + k * 22, py0 + 46, px0 + 26 + k * 22, py0 + 62], fill=BIN, outline=BIN_OUT, width=2)
label('8', 2132, 748)
label('12', 1830, 470)

# ЮВ: двор-колодец, внутри притон 5
house(1760, 1010, 2200, 1115)                                           # верхний дом колодца
house(2262, 1060, 2367, 1452)                                           # правый дом
house(1800, 1462, 2367, 1567)                                           # дом вдоль южной дороги (въезд ~11 м в ЮЗ углу)
garage(2203, 1012, 2259, 1060); garage(2203, 1062, 2259, 1112)          # СВ угол колодца закрыт гаражами
dr.rectangle([1740, 1185, 1960, 1305], fill=CLUB, outline=CLUB_OUT, width=3)     # 5 притон ~27×15 м
dr.rectangle([1828, 1305, 1880, 1322], fill=(120, 104, 116), outline=CLUB_OUT, width=2)
dr.ellipse([1846, 1307, 1862, 1321], fill=(236, 90, 170))
dr.rectangle([1800, 1336, 1960, 1410], fill=(226, 224, 214))           # пятачок-курилка у входа
label('5', 1850, 1245)
label('13', 2110, 1290)                                                 # двор-колодец
label('14', 1723, 1150)                                                 # щель между клубом и длинным домом, с севера тупик
anchor(1723, 1205); anchor(2150, 1400); anchor(1750, 1500); anchor(2400, 1200)
img.save(OUT)
print('ok', OUT)
