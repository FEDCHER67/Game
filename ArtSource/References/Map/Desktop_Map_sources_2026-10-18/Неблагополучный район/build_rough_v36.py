"""Неблагополучный район — план v36 (TASK-000600), от v35:
- два верхних дома в центре придвинуты: углы почти касаются (щель ~0,3 м);
- мусорка 8 в центре убрана;
- гаражи напротив бусика буквой Г: к правому концу ряда добавлены 2 гаража вниз — прикрывают дворик базы с востока.
Не перезаписывает. Запуск: python build_rough_v36.py -> Неблагополучный_район_v36.png
"""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v35.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v36.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)

# верхние дома: углы почти вплотную
dr.rectangle([1170, 340, 1500, 470], fill=BG)
dr.rectangle([859, 240, 1172, 345], fill=FILL, outline=OUTL, width=3)
for k in range(2):
    dx = 859 + 313 * (k + 0.5) / 2
    dr.rectangle([dx - 11, 346, dx + 11, 350], fill=(130, 140, 148))
dr.rectangle([1175, 348, 1491, 453], fill=FILL, outline=OUTL, width=3)
for k in range(2):
    dx = 1175 + 316 * (k + 0.5) / 2
    dr.rectangle([dx - 11, 454, dx + 11, 458], fill=(130, 140, 148))

# мусорка 8 в центре
dr.rectangle([880, 994, 972, 1037], fill=BG)
dr.rectangle([905, 945, 948, 990], fill=BG)

# гаражи у базы буквой Г: 2 гаража вниз от правого конца ряда, ворота на запад к дворику
for k in range(2):
    gy = 1458 + k * 37
    dr.rectangle([472, gy, 540, gy + 37], fill=GAR, outline=GAR_OUT, width=2)
    dr.rectangle([474, gy + 6, 477, gy + 31], fill=(80, 96, 104))
img.save(OUT)
print('ok', OUT)
