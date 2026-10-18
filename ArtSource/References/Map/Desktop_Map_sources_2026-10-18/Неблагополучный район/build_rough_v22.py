"""Неблагополучный район — план v22 (TASK-000586): v21, правая часть ниже двора 12 переделана:
угловой Г-дом убран — на его месте притон-клуб 05 (старый ДК ~30×20 м, вход на юг к пятачку);
короткий поперечный дом заменён длинным домом во всю ширину двора 12 (двор 12 теперь закрыт);
на месте старого клуба — обычный горизонтальный дом; нижний правый дом сдвинут вправо — между ним и длинным домом проезд ~11 м;
вдоль южной дороги второй дом уступом; 14 — тупик между длинным домом и клубом, с востока закрыт гаражами;
во дворе 12 — детская площадка 18, мусорка, лавочки. Не перезаписывает.
Запуск: python build_rough_v22.py -> Неблагополучный_район_v22.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v21.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v22.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
CLUB, CLUB_OUT = (178, 150, 168), (88, 64, 84)
BIN, BIN_OUT = (104, 140, 104), (52, 74, 56)
ANCHOR = (200, 130, 60)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)

dr.rectangle([1712, 816, 2440, 1584], fill=BG)                   # снести сектор ниже двора 12 (поперечный дом, Г-дом, клуб, дома, гаражи)
dr.rectangle([1596, 909, 1706, 1529], fill=FILL, outline=OUTL, width=3)   # длинный дом слева — контур
dr.rectangle([1720, 560, 2205, 812], fill=BG)                    # снять старый номер 12 и точку в середине двора


def house(x0, y0, x1, y1):
    dr.rectangle([x0, y0, x1, y1], fill=FILL, outline=OUTL, width=3)


def label(t, x, y):
    dr.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(255, 255, 255), outline=(60, 70, 80), width=2)
    dr.text((x, y), t, font=F, fill=(40, 50, 60), anchor='mm')


def anchor(x, y):
    dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=ANCHOR, width=3)


def garage(x0, y0, x1, y1, door):
    dr.rectangle([x0, y0, x1, y1], fill=GAR, outline=GAR_OUT, width=2)
    if door == 'W':
        dr.rectangle([x0 + 2, y0 + 6, x0 + 5, y1 - 6], fill=(80, 96, 104))


def bench(x, y):
    dr.rectangle([x, y, x + 34, y + 9], fill=(150, 112, 80), outline=(90, 64, 44), width=1)


house(1760, 860, 2318, 965)            # длинный дом во всю ширину — закрывает двор 12 снизу
house(1760, 1060, 2050, 1165)          # горизонтальный дом на месте старого клуба
house(1800, 1430, 2070, 1535)          # нижний правый дом сдвинут вправо: проезд ~11 м от длинного дома
house(2140, 1400, 2400, 1505)          # второй дом вдоль южной дороги, уступом

# 05 притон-клуб в углу (бывший ДК ~30×20 м), вход на юг с козырьком и неон-сердечком, пятачок-курилка
dr.rectangle([2130, 1040, 2375, 1205], fill=CLUB, outline=CLUB_OUT, width=3)
dr.rectangle([2225, 1205, 2280, 1223], fill=(120, 104, 116), outline=CLUB_OUT, width=2)
dr.ellipse([2244, 1207, 2260, 1221], fill=(236, 90, 170))
dr.rectangle([2185, 1238, 2320, 1318], fill=(226, 224, 214))
label('5', 2252, 1122)

# 14 тупик за клубом: между длинным домом и клубом, с востока закрыт гаражами, вход с запада
for k in range(2):
    garage(2378, 968 + k * 36, 2440, 1004 + k * 36, 'W')
label('14', 2250, 1003)

label('13', 1905, 1300)                # двор между домами, клубом и южными домами

# двор 12: детская площадка 18, мусорка у выхода, лавочки
dr.rectangle([1850, 600, 2030, 730], fill=(232, 220, 178), outline=(170, 150, 100), width=2)
for x0 in (1870, 1950):                # горка и качели — условно
    dr.rectangle([x0, 625, x0 + 40, 650], outline=(120, 100, 70), width=2)
dr.ellipse([1975, 675, 2005, 705], outline=(120, 100, 70), width=2)
label('18', 1940, 700)
for k in range(3):                     # 3 зелёных бака у выхода из двора
    dr.rectangle([2125 + k * 24, 770, 2145 + k * 24, 794], fill=BIN, outline=BIN_OUT, width=2)
bench(1800, 760); bench(1800, 520); bench(2140, 470)
label('12', 1830, 470)
anchor(1790, 600); anchor(2085, 1290); anchor(1740, 1490); anchor(2095, 805)
img.save(OUT)
print('ok', OUT)
