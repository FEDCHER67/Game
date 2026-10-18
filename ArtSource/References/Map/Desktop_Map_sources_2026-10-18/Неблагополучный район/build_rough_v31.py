"""Неблагополучный район — план v31 (TASK-000595), от v30:
- верхний центр поднят на север (~12 м): над средним горизонтальным домом второй параллельный такой же длины,
  за ним (у забора) ряд гаражей воротами к проезду между гаражами и домом; забор обходит выступ.
Не перезаписывает. Запуск: python build_rough_v31.py -> Неблагополучный_район_v31.png
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v30.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v31.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
FENCE = (112, 119, 119)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)

dr.rectangle([776, 105, 1565, 209], fill=BG)            # выступ верхнего центра + старый забор
dr.rectangle([772, 110, 775, 209], fill=BG)             # ступенька забора у левого выступа — переносим
dr.rectangle([772, 40, 775, 113], fill=FENCE)
dr.rectangle([772, 110, 1565, 113], fill=FENCE)         # новый забор выступа
dr.rectangle([1562, 110, 1565, 208], fill=FENCE)
dr.rectangle([985, 255, 1490, 333], fill=BG)            # старый ряд гаражей
dr.rectangle([859, 300, 1491, 405], fill=FILL, outline=OUTL, width=3)   # новый дом, параллельный среднему
for k in range(4):
    dx = 859 + 632 * (k + 0.5) / 4
    dr.rectangle([dx - 11, 406, dx + 11, 410], fill=(130, 140, 148))
for k in range(12):                                       # гаражи за домом у забора, ворота на юг
    gx = 905 + k * 45
    dr.rectangle([gx, 140, gx + 45, 208], fill=GAR, outline=GAR_OUT, width=2)
    dr.rectangle([gx + 6, 203, gx + 39, 206], fill=(80, 96, 104))
img.save(OUT)
print('ok', OUT)
