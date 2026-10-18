"""Неблагополучный район — план v35 (TASK-000599), от v34:
- верхний центр: вместо «молнии» с диагональной вставкой — два отдельных горизонтальных дома, сцепленные углами:
  правый нижний угол левого почти касается левого верхнего угла правого, между ними узкая щель (~1 м).
Не перезаписывает. Запуск: python build_rough_v35.py -> Неблагополучный_район_v35.png
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v34.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v35.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)
dr.rectangle([850, 232, 1500, 432], fill=BG)
for (x0, y0, x1, y1) in ((859, 240, 1172, 345), (1180, 352, 1491, 457)):
    dr.rectangle([x0, y0, x1, y1], fill=FILL, outline=OUTL, width=3)
    for k in range(2):                                       # подъезды на юг
        dx = x0 + (x1 - x0) * (k + 0.5) / 2
        dr.rectangle([dx - 11, y1 + 1, dx + 11, y1 + 5], fill=(130, 140, 148))
img.save(OUT)
print('ok', OUT)
