"""Неблагополучный район — план v40 (TASK-000606), от v39:
- 2 трансформаторные будки (кирпич, знак «не влезай»): во дворе 12 у Г-дома и в щели между вертикалями у центра (закуток);
- 2 турника для атмосферы: во дворе 9 и во дворе 12;
- голые корявые деревья, редко: в палисадниках, у площадок, во дворах 11 и 13, по краям пустошей.
Провода и столбы не ставим (решение Вадима). Не перезаписывает.
Запуск: python build_rough_v40.py -> Неблагополучный_район_v40.png
"""
import math
import os
import random

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v39.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v40.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

rnd = random.Random(40)
img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)


def booth(x0, y0):
    """Трансформаторная будка ~4×4 м."""
    dr.rectangle([x0, y0, x0 + 34, y0 + 34], fill=(176, 132, 112), outline=(96, 66, 54), width=3)
    dr.polygon([(x0 + 17, y0 + 8), (x0 + 26, y0 + 24), (x0 + 8, y0 + 24)], fill=(240, 200, 40), outline=(60, 50, 30))


def turnik(x0, y0, x1):
    dr.rectangle([x0 - 4, y0 - 4, x0 + 4, y0 + 4], fill=(60, 60, 70))
    dr.rectangle([x1 - 4, y0 - 4, x1 + 4, y0 + 4], fill=(60, 60, 70))
    dr.line([(x0, y0), (x1, y0)], fill=(60, 60, 70), width=3)


def tree(x, y):
    """Голое корявое дерево: ствол + 6–7 веток."""
    for a in range(0, 360, rnd.choice((51, 60))):
        a2 = math.radians(a + rnd.uniform(-20, 20))
        L = rnd.uniform(14, 24)
        mx, my = x + L * 0.6 * math.cos(a2), y + L * 0.6 * math.sin(a2)
        ex, ey = x + L * math.cos(a2 + rnd.uniform(-0.4, 0.4)), y + L * math.sin(a2 + rnd.uniform(-0.4, 0.4))
        dr.line([(x, y), (mx, my), (ex, ey)], fill=(108, 88, 70), width=2)
    dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(92, 72, 56))


booth(2150, 860)                      # двор 12, у Г-дома, подальше от площадки
booth(780, 1480)                      # закуток между вертикалями у центра
turnik(285, 525, 345)                 # двор 9
turnik(1745, 800, 1805)               # двор 12

TREES = [(240, 420), (240, 525), (520, 450), (400, 535), (70, 400), (70, 650), (740, 300),     # двор 9 и край
         (330, 1060), (455, 1100), (175, 1150), (180, 1340),                                   # двор 11 и запад
         (1150, 650), (1400, 650), (1060, 1300), (1060, 1450), (795, 1690),                    # центр
         (1650, 420), (1720, 420), (2000, 650), (2120, 700), (2060, 900),                      # двор 12 и север
         (2250, 1320), (2350, 1450), (2280, 1610), (1800, 1660), (2000, 1665)]                 # двор 13 и юг
for x, y in TREES:
    tree(x, y)
img.save(OUT)
print('ok', OUT)
