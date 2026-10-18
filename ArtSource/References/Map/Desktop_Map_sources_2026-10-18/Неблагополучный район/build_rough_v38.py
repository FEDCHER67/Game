"""Неблагополучный район — план v38 (TASK-000602), от v37: у вертикали слева-сверху (у двора 9) подъезды только на восток, к гаражному двору 7.
Не перезаписывает. Запуск: python build_rough_v38.py -> Неблагополучный_район_v38.png
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v37.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v38.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG = (238, 240, 231)
DOOR, DOOR_OUT = (96, 106, 116), (50, 58, 66)
img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)
dr.rectangle([642, 486, 651, 858], fill=BG)                   # снять подъезды с западной стороны
dr.rectangle([652, 486, 654, 858], fill=(73, 83, 91))         # западный контур
for k in range(3):
    y = 486 + (858 - 486) * (k + 0.5) / 3
    dr.rectangle([761, y - 11, 768, y + 11], fill=DOOR, outline=DOOR_OUT)
img.save(OUT)
print('ok', OUT)
