"""Неблагополучный район — план v29 (TASK-000593), от v28:
- убраны сквер 19, детская площадка 18 и обе новые мусорные площадки 8 (сделаем позже);
- ларёк шаурмы 6 убран; в гаражном дворе 7 справа — ряд гаражей зеркально левому, двор симметричный.
Не перезаписывает. Запуск: python build_rough_v29.py -> Неблагополучный_район_v29.png
"""
import os

from PIL import Image, ImageDraw, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v28.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v29.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG = (238, 240, 231)
img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)
dr.rectangle([285, 295, 635, 595], fill=BG)            # двор 9: сквер 19 + мусорка 8
dr.rectangle([1795, 555, 2200, 770], fill=BG)          # двор 12: площадка 18 + мусорка 8
dr.rectangle([1300, 628, 1434, 706], fill=BG)          # ларёк шаурмы 6
left = img.crop((882, 611, 942, 736))                  # левый боковой ряд гаражей
img.paste(ImageOps.mirror(left), (1358, 611))          # правый — зеркально (зазор до рядов как слева)
img.save(OUT)
print('ok', OUT)
