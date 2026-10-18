"""Неблагополучный район — план v26 (TASK-000590), от v25:
- СЗ: короткий поперечный дом → Г-дом (ножка слева, перекладина вправо — зеркально к Г у двора 12), сдвинут левее;
- дом 10 короче — между ним и вертикалью справа проезд для бусика ~14 м; арка 10 оставлена;
- между детской площадкой 18 и притоном 5 — ряд из 6 гаражей воротами к двору 12: прикрывает клуб от двора,
  за гаражами тёмный проход ~5 м к клубу.
Не перезаписывает. Запуск: python build_rough_v26.py -> Неблагополучный_район_v26.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v25.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v26.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
ARCH, ARCH_L = (246, 247, 240), (120, 128, 132)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)


def label(t, x, y):
    dr.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(255, 255, 255), outline=(60, 70, 80), width=2)
    dr.text((x, y), t, font=F, fill=(40, 50, 60), anchor='mm')


def poly_house(pts):
    dr.polygon(pts, fill=FILL)
    dr.line(pts + [pts[0]], fill=OUTL, width=3)


def doors(x0, x1, y, n):
    for k in range(n):
        dx = x0 + (x1 - x0) * (k + 0.5) / n
        dr.rectangle([dx - 11, y + 1, dx + 11, y + 5], fill=(130, 140, 148))


# ------------------------------------------------ СЗ: Г-дом вместо поперечного + дом 10 короче
dr.rectangle([108, 228, 640, 720], fill=BG)
poly_house([(330, 290), (620, 290), (620, 395), (435, 395), (435, 545), (330, 545)])  # Г: ножка слева, перекладина вправо
label('9', 225, 420)
dr.rectangle([118, 598, 540, 703], fill=FILL, outline=OUTL, width=3)                # дом 10 короче: проезд ~14 м до вертикали справа
doors(118, 540, 703, 3)
dr.rectangle([270, 598, 322, 703], fill=ARCH)
dr.line([(274, 598), (274, 703)], fill=ARCH_L, width=2)
dr.line([(318, 598), (318, 703)], fill=ARCH_L, width=2)
label('10', 296, 650)

# ------------------------------------------------ между 18 и 5: ряд гаражей, ворота на север к двору 12
for k in range(6):
    gx = 1745 + k * 45
    dr.rectangle([gx, 1000, gx + 45, 1068], fill=GAR, outline=GAR_OUT, width=2)
    dr.rectangle([gx + 6, 1002, gx + 39, 1005], fill=(80, 96, 104))
img.save(OUT)
print('ok', OUT)
