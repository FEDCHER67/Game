"""Неблагополучный район — план v19 (TASK-000583): v18 (план Вадима v04 + северный ряд), переделан правый верхний сектор:
двор 12 — один Г-дом (верх + восточное крыло) вместо П с пристройкой и отдельной вертикали справа; лишний забор убран;
гаражи — аккуратный блок у восточного забора: 2 ряда воротами друг к другу, проезд открыт на юг к выезду 16, с севера тупик.
Не перезаписывает. Запуск: python build_rough_v19.py -> Неблагополучный_район_v19.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v18.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v19.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
YARD = (234, 220, 209)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
ANCHOR = (200, 130, 60)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)

# снести старый сектор: П-двор 12 с пристройкой, вертикаль справа, забор-линию, разбросанные гаражи
dr.rectangle([1735, 290, 2556, 826], fill=BG)
dr.rectangle([2557, 55, 2561, 897], fill=OUTL)                                  # восточный забор целиком

# двор 12: подложка двора и один Г-дом (верхнее крыло + восточное крыло)
dr.rectangle([1745, 420, 2200, 815], fill=YARD)
dr.polygon([(1790, 300), (2318, 300), (2318, 800), (2213, 800), (2213, 405), (1790, 405)], fill=FILL)
dr.line([(1790, 300), (2318, 300), (2318, 800), (2213, 800), (2213, 405), (1790, 405), (1790, 300)], fill=OUTL, width=3)


def garage(x0, y0, x1, y1, door):
    dr.rectangle([x0, y0, x1, y1], fill=GAR, outline=GAR_OUT, width=2)
    if door == 'E':
        dr.rectangle([x1 - 5, y0 + 6, x1 - 2, y1 - 6], fill=(80, 96, 104))
    elif door == 'W':
        dr.rectangle([x0 + 2, y0 + 6, x0 + 5, y1 - 6], fill=(80, 96, 104))
    else:
        dr.rectangle([x0 + 6, y1 - 5, x1 - 6, y1 - 2], fill=(80, 96, 104))


# гаражный блок у восточного забора: 2 ряда по 9, проезд 8 м открыт на юг, с севера тупик
for k in range(9):
    y = 360 + k * 45
    garage(2350, y, 2418, y + 45, 'E')
    garage(2486, y, 2554, y + 45, 'W')
garage(2418, 312, 2486, 360, 'S')


def anchor(x, y):
    dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=ANCHOR, width=3)


anchor(1760, 432); anchor(2452, 800)

x, y = 1975, 615                       # номер двора в стиле v04
dr.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(255, 255, 255), outline=(60, 70, 80), width=2)
dr.text((x, y), '12', font=F, fill=(40, 50, 60), anchor='mm')
img.save(OUT)
print('ok', OUT)
