"""Неблагополучный район — план v21 (TASK-000585): v20, переделан правый нижний сектор:
убраны перемычка 14, П-двор 13, вертикаль у восточной дороги и одиночный гараж. Вместо них — компактный «квартал притона»:
Г-дом (верх + восточное крыло), притон-клуб 05 (старый двухэтажный ~26×15 м) с пятачком-курилкой перед входом,
дом фасадом к южной дороге, 13 — тесный двор внутри Г, 14 — тупиковый проход за клубом (с запада глухо), 2–3 гаража в углу.
Старый корпус 05 в центре стал обычным домом (номер снят). Не перезаписывает.
Запуск: python build_rough_v21.py -> Неблагополучный_район_v21.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v20.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v21.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
CLUB, CLUB_OUT = (178, 150, 168), (88, 64, 84)
ANCHOR = (200, 130, 60)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)

dr.rectangle([1707, 940, 2440, 1584], fill=BG)                   # снести старый сектор
dr.rectangle([2140, 880, 2440, 940], fill=BG)                    # верх старой вертикали у дороги
dr.rectangle([1596, 909, 1706, 1529], fill=FILL, outline=OUTL, width=3)   # длинный дом слева — чистый контур без перемычки
dr.ellipse([1268, 957, 1306, 995], fill=FILL)                     # старый 05 в центре — теперь обычный дом


def house(pts):
    dr.polygon(pts, fill=FILL)
    dr.line(pts + [pts[0]], fill=OUTL, width=3)


def label(t, x, y):
    dr.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(255, 255, 255), outline=(60, 70, 80), width=2)
    dr.text((x, y), t, font=F, fill=(40, 50, 60), anchor='mm')


def anchor(x, y):
    dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=ANCHOR, width=3)


house([(1770, 990), (2330, 990), (2330, 1410), (2225, 1410), (2225, 1095), (1770, 1095)])   # Г-дом
house([(1740, 1430), (2010, 1430), (2010, 1535), (1740, 1535)])                             # дом фасадом к южной дороге

# 05 притон-клуб: облезлый двухэтажный, вход с козырьком на юг, к пятачку; маленькое неоновое сердечко
dr.rectangle([1800, 1150, 2010, 1270], fill=CLUB, outline=CLUB_OUT, width=3)
dr.rectangle([1880, 1270, 1932, 1288], fill=(120, 104, 116), outline=CLUB_OUT, width=2)
dr.ellipse([1898, 1272, 1914, 1286], fill=(236, 90, 170))
label('5', 1905, 1210)
dr.rectangle([1845, 1300, 1965, 1385], fill=(226, 224, 214))    # пятачок-курилка перед входом (толпа, вышибала)

# 2–3 гаража в юго-восточном углу, ворота на юг к дороге
for k in range(3):
    gx = 2262 + k * 45
    dr.rectangle([gx, 1440, gx + 45, 1508], fill=GAR, outline=GAR_OUT, width=2)
    dr.rectangle([gx + 6, 1503, gx + 39, 1506], fill=(80, 96, 104))

label('13', 2118, 1250)                                               # тесный двор внутри Г
label('14', 1745, 1122)                                               # тупик за клубом: с запада глухая стена дома
anchor(2070, 1350); anchor(2390, 1250); anchor(1790, 1122)
img.save(OUT)
print('ok', OUT)
