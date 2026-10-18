"""Неблагополучный район — план v30 (TASK-000594), от v29:
- СЗ угол поднят на север (~18 м): перед домом 10 параллельный дом такой же длины, выше — Г-дом, двор 9 между ними; забор обходит выступ;
- арка в Г-доме двора 12 (в верхнем крыле);
- у базы вместо одиночного гаража ряд из 4 гаражей воротами к дворику базы.
Не перезаписывает. Запуск: python build_rough_v30.py -> Неблагополучный_район_v30.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v29.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v30.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
GAR, GAR_OUT = (180, 202, 204), (100, 120, 128)
ARCH, ARCH_L = (246, 247, 240), (120, 128, 132)
FENCE = (112, 119, 119)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)
EXT = 150

src = Image.open(SRC).convert('RGB')
W, H = src.size
img = Image.new('RGB', (W, H + EXT), (255, 255, 255))
img.paste(src, (0, EXT))
dr = ImageDraw.Draw(img)


def Y(y):
    return y + EXT


def R(x0, y0, x1, y1, **kw):
    dr.rectangle([x0, Y(y0), x1, Y(y1)], **kw)


def poly(pts):
    p = [(x, Y(y)) for x, y in pts]
    dr.polygon(p, fill=FILL)
    dr.line(p + [p[0]], fill=OUTL, width=3)


def label(t, x, y):
    dr.ellipse([x - 17, Y(y) - 17, x + 17, Y(y) + 17], fill=(255, 255, 255), outline=(60, 70, 80), width=2)
    dr.text((x, Y(y)), t, font=F, fill=(40, 50, 60), anchor='mm')


def doors(x0, x1, y, n):
    for k in range(n):
        dx = x0 + (x1 - x0) * (k + 0.5) / n
        R(dx - 11, y + 1, dx + 11, y + 5, fill=(130, 140, 148))


def arch(x0, y0, x1, y1):
    R(x0, y0, x1, y1, fill=ARCH)
    dr.line([(x0 + 4, Y(y0)), (x0 + 4, Y(y1))], fill=ARCH_L, width=2)
    dr.line([(x1 - 4, Y(y0)), (x1 - 4, Y(y1))], fill=ARCH_L, width=2)


# ------------------------------------------------ СЗ: поднять угол
R(25, -125, 775, 54, fill=BG)                     # подложка выступа
R(108, 50, 710, 225, fill=BG)                     # старый Г (перекладина) + забор над ним
R(108, 225, 640, 560, fill=BG)                    # ножка Г и двор 9
R(36, 55, 775, 58, fill=BG)                       # старый забор над выступом
R(36, -110, 775, -107, fill=FENCE)                # новый забор выступа
R(772, -110, 775, 58, fill=FENCE)
R(36, -110, 39, 60, fill=FENCE)
poly([(118, -40), (700, -40), (700, 65), (223, 65), (223, 330), (118, 330)])  # Г выше
doors(223, 700, 65, 4)
R(118, 420, 540, 525, fill=FILL, outline=OUTL, width=3)                       # новый дом перед домом 10
doors(118, 540, 525, 3)
label('9', 400, 240)

# ------------------------------------------------ арка в верхнем крыле Г-дома двора 12
arch(2000, 300, 2052, 405)

# ------------------------------------------------ у базы: ряд из 4 гаражей вместо одиночного
R(378, 1225, 500, 1315, fill=BG)
for k in range(4):
    gx = 360 + k * 45
    R(gx, 1240, gx + 45, 1308, fill=GAR, outline=GAR_OUT, width=2)
    R(gx + 6, 1303, gx + 39, 1306, fill=(80, 96, 104))
img.save(OUT)
print('ok', OUT)
