"""Неблагополучный район — план v33 (TASK-000597), от v32: убраны гаражи у 15 (за западной дорогой) и у 13 (у южной дороги).
Не перезаписывает. Запуск: python build_rough_v33.py -> Неблагополучный_район_v33.png
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v32.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v33.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG = (238, 240, 231)
img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)
dr.rectangle([24, 1160, 84, 1350], fill=BG)            # гаражи у 15
dr.rectangle([18, 1160, 23, 1350], fill=(255, 255, 255))
dr.rectangle([2195, 1625, 2340, 1703], fill=BG)        # гаражи у 13
img.save(OUT)
print('ok', OUT)
