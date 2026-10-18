"""Неблагополучный район — план v34 (TASK-000598), от v33:
- верхний центр: самый верхний дом заменён «молнией» — два горизонтальных корпуса со сдвигом, соединены диагональной вставкой
  (как на фото Вадима: две секции, сцепленные углом); гаражи и забор выступа подняты чуть выше.
Не перезаписывает. Запуск: python build_rough_v34.py -> Неблагополучный_район_v34.png
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v33.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v34.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
FENCE = (112, 119, 119)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)
dr.rectangle([776, 75, 1561, 432], fill=BG)              # снести верхний дом, гаражи, старый забор выступа
dr.rectangle([772, 80, 1565, 83], fill=FENCE)            # забор выше
dr.rectangle([1562, 80, 1565, 208], fill=FENCE)
pts = [(859, 240), (1150, 240), (1200, 315), (1491, 315), (1491, 420), (1200, 420), (1150, 345), (859, 345)]
dr.polygon(pts, fill=FILL)
dr.line(pts + [pts[0]], fill=OUTL, width=3)
for (x0, x1, y) in ((859, 1150, 345), (1200, 1491, 420)):  # подъезды на юг
    for k in range(2):
        dx = x0 + (x1 - x0) * (k + 0.5) / 2
        dr.rectangle([dx - 11, y + 1, dx + 11, y + 5], fill=(130, 140, 148))
for k in range(12):                                       # гаражи выше, ворота на юг
    gx = 905 + k * 45
    dr.rectangle([gx, 110, gx + 45, 178], fill=GAR, outline=GAR_OUT, width=2)
    dr.rectangle([gx + 6, 173, gx + 39, 176], fill=(80, 96, 104))
img.save(OUT)
print('ok', OUT)
