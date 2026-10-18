"""Неблагополучный район — план v25 (TASK-000589), от v24:
- ЮВ: вместо Т — дом-«молния» с прямыми углами: от правого верха к левому низу
  (верхнее крыло справа → вертикальная перемычка → нижнее крыло влево до длинного дома), арка в нижнем крыле;
  притон 5 — в кармане к северу от нижнего крыла и к западу от перемычки (внутри района), вход на восток;
  14 — щель клуб/длинный дом, с юга тупик; 13 — двор справа-снизу от молнии, 3 гаража у южной дороги;
- СЗ: средний дом (9) убран — вместо него короткий поперечный дом с восточной стороны, двор 9 открыт на запад;
  гараж и мусорка у 9 убраны (поставим позже).
Не перезаписывает. Запуск: python build_rough_v25.py -> Неблагополучный_район_v25.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v24.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v25.png')
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


# ------------------------------------------------ СЗ: убрать средний дом, гараж и мусорку у 9
dr.rectangle([108, 330, 640, 540], fill=BG)
dr.rectangle([118, 110, 700, 215], outline=OUTL, width=3)                      # контур верхнего дома
dr.rectangle([470, 262, 575, 552], fill=FILL, outline=OUTL, width=3)          # короткий поперечный дом с востока
label('9', 300, 400)

# ------------------------------------------------ ЮВ: очистить и поставить «молнию»
dr.rectangle([1707, 830, 2440, 1584], fill=BG)
dr.rectangle([1596, 909, 1706, 1529], fill=FILL, outline=OUTL, width=3)
poly_house([(2050, 990), (2355, 990), (2355, 1095), (2155, 1095), (2155, 1410),
            (1706, 1410), (1706, 1305), (2050, 1305)])
dr.rectangle([1860, 1305, 1912, 1410], fill=ARCH)                              # арка в нижнем крыле
dr.line([(1864, 1305), (1864, 1410)], fill=ARCH_L, width=2)
dr.line([(1908, 1305), (1908, 1410)], fill=ARCH_L, width=2)

# 5 притон в кармане: с З — длинный дом, с Ю — нижнее крыло, с В — перемычка; вход на восток
dr.rectangle([1745, 1110, 1950, 1230], fill=CLUB, outline=CLUB_OUT, width=3)
dr.rectangle([1950, 1145, 1967, 1195], fill=(120, 104, 116), outline=CLUB_OUT, width=2)
dr.ellipse([1952, 1162, 1966, 1178], fill=(236, 90, 170))
dr.rectangle([1975, 1120, 2045, 1220], fill=(226, 224, 214))                   # пятачок-курилка
label('5', 1848, 1170)
label('14', 1726, 1265)
label('13', 2290, 1300)
for k in range(3):                                                             # 3 гаража у южной дороги
    gx = 2200 + k * 45
    dr.rectangle([gx, 1480, gx + 45, 1548], fill=GAR, outline=GAR_OUT, width=2)
    dr.rectangle([gx + 6, 1543, gx + 39, 1546], fill=(80, 96, 104))
anchor(2100, 1240); anchor(1800, 1490); anchor(2400, 1250)
img.save(OUT)
print('ok', OUT)
