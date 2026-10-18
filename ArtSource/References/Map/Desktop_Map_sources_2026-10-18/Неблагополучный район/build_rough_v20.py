"""Неблагополучный район — план v20 (TASK-000584): v19 без розовых подложек дворов (9, 11, 12, 13, 14) — всё одной светлой землёй.
Не перезаписывает. Запуск: python build_rough_v20.py -> Неблагополучный_район_v20.png
"""
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v19.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v20.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG = (238, 240, 231)
img = Image.open(SRC).convert('RGB')
px = img.load()
W, H = img.size
n = 0
for y in range(H):
    for x in range(W):
        r, g, b = px[x, y]
        if 222 <= r <= 240 and 208 <= g <= 226 and 196 <= b <= 216 and r - b >= 14:   # розовая подложка двора и её края
            px[x, y] = BG
            n += 1
img.save(OUT)
print('ok', n, OUT)
