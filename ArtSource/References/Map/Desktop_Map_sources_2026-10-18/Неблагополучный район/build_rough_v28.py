"""Неблагополучный район — план v28 (TASK-000592), от v27:
- двор 9: мини-сквер 19 и мусорная площадка 8 (2 больших бункера + 4 зелёных бака, профлист, открыта на юг к проезду);
- дом-молния чуть удлинён вправо; притон 5 больше не отдельное здание — он в первом этаже молнии,
  на её левой (западной) стене перемычки, вход с запада с неон-сердечком, перед ним пятачок; отдельный клуб убран;
- 14 — щель между гаражами и длинным домом, тупик.
Не перезаписывает. Запуск: python build_rough_v28.py -> Неблагополучный_район_v28.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'Неблагополучный_район_v27.png')
OUT = os.path.join(HERE, 'Неблагополучный_район_v28.png')
if os.path.exists(OUT):
    raise SystemExit(os.path.basename(OUT) + ' exists')

BG, FILL, OUTL = (238, 240, 231), (207, 211, 214), (73, 83, 91)
CLUB, CLUB_OUT = (178, 150, 168), (88, 64, 84)
ARCH, ARCH_L = (246, 247, 240), (120, 128, 132)
BIN, BIN_OUT = (104, 140, 104), (52, 74, 56)
SKIP, SKIP_OUT = (84, 120, 92), (40, 60, 46)
FENCE = (112, 119, 119)
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 20)

img = Image.open(SRC).convert('RGB')
dr = ImageDraw.Draw(img)


def label(t, x, y):
    dr.ellipse([x - 17, y - 17, x + 17, y + 17], fill=(255, 255, 255), outline=(60, 70, 80), width=2)
    dr.text((x, y), t, font=F, fill=(40, 50, 60), anchor='mm')


def trash_pad(x0, y0):
    """Мусорная площадка: бетон, профлист с трёх сторон (открыта на юг), 2 больших бункера + 4 зелёных бака."""
    x1, y1 = x0 + 125, y0 + 80
    dr.rectangle([x0, y0, x1, y1], fill=(206, 204, 196))
    for seg in ([(x0, y0), (x1, y0)], [(x0, y0), (x0, y1)], [(x1, y0), (x1, y1)]):
        dr.line(seg, fill=FENCE, width=4)
    dr.rectangle([x0 + 8, y0 + 8, x0 + 48, y0 + 30], fill=SKIP, outline=SKIP_OUT, width=2)
    dr.rectangle([x0 + 56, y0 + 8, x0 + 96, y0 + 30], fill=SKIP, outline=SKIP_OUT, width=2)
    for k in range(4):
        dr.rectangle([x0 + 10 + k * 22, y0 + 46, x0 + 26 + k * 22, y0 + 62], fill=BIN, outline=BIN_OUT, width=2)


# ------------------------------------------------ двор 9: мини-сквер 17 + мусорка 8
dr.rectangle([290, 300, 470, 440], fill=(200, 214, 180), outline=(140, 160, 120), width=2)
for (tx, ty) in ((320, 330), (440, 330), (320, 410), (440, 410)):
    dr.ellipse([tx - 12, ty - 12, tx + 12, ty + 12], fill=(150, 176, 130), outline=(100, 126, 90), width=2)
dr.ellipse([360, 350, 400, 390], outline=(110, 100, 80), width=2)            # клумба из покрышек
label('19', 380, 455)
trash_pad(505, 470)
label('8', 567, 575)

# ------------------------------------------------ правый низ: убрать отдельный клуб, удлинить молнию, притон в её стене
dr.rectangle([1708, 1103, 2048, 1300], fill=BG)
z = [(2050, 990), (2405, 990), (2405, 1095), (2155, 1095), (2155, 1410),
     (1706, 1410), (1706, 1305), (2050, 1305)]
dr.polygon(z, fill=FILL)
dr.line(z + [z[0]], fill=OUTL, width=3)
dr.rectangle([1860, 1305, 1912, 1410], fill=ARCH)                             # арка в нижнем крыле
dr.line([(1864, 1305), (1864, 1410)], fill=ARCH_L, width=2)
dr.line([(1908, 1305), (1908, 1410)], fill=ARCH_L, width=2)
dr.line([(1706, 1305), (1706, 1410)], fill=OUTL, width=3)

# 5 притон в первом этаже перемычки, на западной стене
dr.rectangle([2051, 1112, 2125, 1290], fill=CLUB, outline=CLUB_OUT, width=3)
dr.rectangle([2034, 1170, 2051, 1232], fill=(120, 104, 116), outline=CLUB_OUT, width=2)   # козырёк над входом
dr.ellipse([2035, 1193, 2049, 1209], fill=(236, 90, 170))                                    # неон-сердечко
dr.rectangle([1940, 1150, 2028, 1252], fill=(226, 224, 214))                                 # пятачок-курилка
label('5', 2088, 1200)
label('14', 1726, 1034)                                                       # щель гаражи/длинный дом
img.save(OUT)
print('ok', OUT)
