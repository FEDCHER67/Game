"""Неблагополучный район — план v27 (TASK-000591), от v26:
- СЗ: Г-дом у цифры 9 убран; верхний левый дом стал буквой Г (перекладина сверху вправо, ножка слева вниз), двор 9 под перекладиной.
Не перезаписывает. Запуск: python build_rough_v27.py -> Неблагополучный_район_v27.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v26.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v27.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)

dr.rectangle([108, 100, 640, 590], fill=BG)                         # снять верхний дом с подъездами и Г у цифры 9
pts = [(118, 110), (700, 110), (700, 215), (223, 215), (223, 480), (118, 480)]
dr.polygon(pts, fill=FILL)
dr.line(pts + [pts[0]], fill=OUTL, width=3)
for k in range(4):                                                  # подъезды перекладины во двор
    dx = 223 + 477 * (k + 0.5) / 4
    dr.rectangle([dx - 11, 216, dx + 11, 220], fill=(130, 140, 148))
x, y = 400, 400
dr.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(255, 255, 255), outline=(60, 70, 80), width=2)
dr.text((x, y), '9', font=F, fill=(40, 50, 60), anchor='mm')
img.save(OUT)
print('ok', OUT)
