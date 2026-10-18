"""Неблагополучный район — план v18 (TASK-000582): исходный план Вадима v04 как есть (картинка), район увеличен на север:
сверху добавлена полоса ~30 м — 2 горизонтальные хрущёвки (СЗ и СВ) и ряд гаражей между ними, забор перенесён на новый край.
Стиль, цвета и толщины линий взяты из v04. Не перезаписывает.
Запуск: python build_rough_v18.py -> Неблагополучный_район_v18.png
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v04.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v18.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
FENCE = (112, 119, 119)
GAR, GAR_OUT = (180, 202, 204), (110, 128, 134)
X0, X1 = 25, 2566                    # ширина светлой подложки района на v04
EXT = 260                            # на сколько px район вырос на север (~32 м)

src = Image.open(SRC).convert('RGB')
W, H = src.size
img = Image.new('RGB', (W, H + EXT), (255, 255, 255))
img.paste(src, (0, EXT))
dr = ImageDraw.Draw(img)


def Y(y):
    """y в координатах v04 (px) -> новый холст."""
    return y + EXT


# убрать старый верхний забор (строки 0..39 v04) и залить новую полосу подложкой района
dr.rectangle([X0, Y(-EXT + 30), X1, Y(39)], fill=BG)
# новый забор по новому северному краю + продлить боковые
TOP = -205
dr.rectangle([36, Y(TOP), X1 - 5, Y(TOP) + 3], fill=FENCE)
dr.rectangle([36, Y(TOP), 39, Y(41)], fill=FENCE)
dr.rectangle([2557, Y(TOP), 2561, Y(41)], fill=OUTL)


def house(x0, y0, x1, y1):
    dr.rectangle([x0, Y(y0), x1, Y(y1)], fill=FILL, outline=OUTL, width=3)


house(118, -150, 700, -45)            # СЗ: длинная горизонтальная над колодцем 9 и вертикалью
house(1587, -150, 2308, -45)          # СВ: длинная горизонтальная над двором 12
for k in range(11):                   # ряд гаражей между ними, ворота на юг
    gx = 990 + k * 45
    dr.rectangle([gx, Y(-150), gx + 45, Y(-82)], fill=GAR, outline=GAR_OUT, width=2)
img.save(OUT)
print('ok', OUT)
