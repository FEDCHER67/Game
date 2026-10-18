"""Неблагополучный район — план v32 (TASK-000596), от v31:
- гаражи у 14 убраны совсем (вместе с номером 14).
Зоны NPC (решение Вадима): 12–5 — главное скопление NPC, «центр района»; 9 — малый центр; остальное — пустоши, ловить легко.
Не перезаписывает. Запуск: python build_rough_v32.py -> Неблагополучный_район_v32.png
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v31.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v32.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

img = Image.open(SRC).convert('RGB')
ImageDraw.Draw(img).rectangle([1708, 1145, 2025, 1222], fill=(238, 240, 231))
img.save(OUT)
print('ok', OUT)
