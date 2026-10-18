"""Неблагополучный район — план v24 (TASK-000588), от v23:
- ЮВ сектор очищен: дом буквой Т лежит горизонтально, шляпка (вертикальное крыло) смотрит на восток к дороге,
  ножка идёт на запад до длинного дома; в ножке арка; притон 5 — к северу от ножки, внутри района, закрыт со всех сторон
  кроме севера (длинный дом, ножка Т, шляпка Т); до детской площадки ~35 м; 14 — щель между клубом и длинным домом, с юга тупик;
- СЗ: средний из трёх домов без арки, короче и сдвинут от западного края (проход с запада).
Не перезаписывает. Запуск: python build_rough_v24.py -> Неблагополучный_район_v24.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v23.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v24.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
CLUB, CLUB_OUT = (178, 150, 168), (88, 64, 84)
ARCH, ARCH_L = (246, 247, 240), (120, 128, 132)
ANCHOR = (200, 130, 60)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)


def label(t, x, y):
    dr.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(255, 255, 255), outline=(60, 70, 80), width=2)
    dr.text((x, y), t, font=F, fill=(40, 50, 60), anchor='mm')


def anchor(x, y):
    dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=ANCHOR, width=3)


def poly_house(pts):
    dr.polygon(pts, fill=FILL)
    dr.line(pts + [pts[0]], fill=OUTL, width=3)


# ------------------------------------------------ СЗ: средний дом — без арки, короче, проход с запада
dr.rectangle([108, 330, 500, 462], fill=BG)
dr.rectangle([160, 341, 470, 446], fill=FILL, outline=OUTL, width=3)
for k in range(3):
    dx = 160 + 310 * (k + 0.5) / 3
    dr.rectangle([dx - 11, 447, dx + 11, 451], fill=(130, 140, 148))

# ------------------------------------------------ ЮВ: очистить сектор
dr.rectangle([1707, 830, 2440, 1584], fill=BG)
dr.rectangle([1596, 909, 1706, 1529], fill=FILL, outline=OUTL, width=3)        # длинный дом слева

# дом буквой Т: шляпка — вертикальное крыло у восточной дороги, ножка — на запад до длинного дома
poly_house([(1706, 1200), (2250, 1200), (2250, 990), (2355, 990), (2355, 1510),
            (2250, 1510), (2250, 1305), (1706, 1305)])
dr.rectangle([1960, 1200, 2012, 1305], fill=ARCH)                                # арка в ножке Т
dr.line([(1964, 1200), (1964, 1305)], fill=ARCH_L, width=2)
dr.line([(2008, 1200), (2008, 1305)], fill=ARCH_L, width=2)

# 5 притон: к северу от ножки Т, внутри района (с З — длинный дом, с Ю — ножка Т, с В — шляпка Т), вход на восток
dr.rectangle([1745, 1040, 1955, 1160], fill=CLUB, outline=CLUB_OUT, width=3)
dr.rectangle([1955, 1075, 1972, 1125], fill=(120, 104, 116), outline=CLUB_OUT, width=2)
dr.ellipse([1957, 1092, 1971, 1108], fill=(236, 90, 170))
dr.rectangle([1990, 1050, 2080, 1150], fill=(226, 224, 214))                     # пятачок-курилка у входа
label('5', 1850, 1100)
label('14', 1726, 1180)                                                          # щель клуб/длинный дом, с юга тупик
label('13', 2050, 1420)                                                          # двор к югу от Т
for k in range(3):                                                               # 3 гаража у южной дороги
    gx = 1820 + k * 45
    dr.rectangle([gx, 1480, gx + 45, 1548], fill=GAR, outline=GAR_OUT, width=2)
    dr.rectangle([gx + 6, 1543, gx + 39, 1546], fill=(80, 96, 104))
anchor(2120, 1120); anchor(1760, 1400); anchor(2400, 1250)
img.save(OUT)
print('ok', OUT)
