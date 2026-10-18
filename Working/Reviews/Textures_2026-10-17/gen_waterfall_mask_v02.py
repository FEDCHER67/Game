"""Маска струй водопада, бесшовная по X и Y (TASK-000825): наш шейдер воды (режим Waterfall) прокручивает маску вниз,
поэтому она должна повторяться по вертикали; у GPT (WaterFX_waterfall.png) повтор только по X. Тот же вид: белые вытянутые
струи с волнистыми краями на чёрном, разной ширины и длины. 1024, Linear-маска. PIL без numpy."""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'own_textures_v01', 'WaterFX_waterfall_v02_tileY.png')
N = 1024
r = random.Random(825)
big = Image.new('L', (3 * N, 3 * N), 0)
d = ImageDraw.Draw(big)


def streak(x, y, length, width, wob):
    """Струя: сверху вниз, ширина плавно меняется, края волнистые; рисуется 9 раз со сдвигом на N (бесшовность)."""
    steps = max(8, int(length / 6))
    left, right = [], []
    ph1, ph2 = r.uniform(0, 6.28), r.uniform(0, 6.28)
    for s in range(steps + 1):
        t = s / steps
        yy = y + length * t
        taper = math.sin(math.pi * min(1.0, t * 1.15)) ** 0.6           # тоньше на концах
        w = width * (0.35 + 0.65 * taper) * (1 + 0.25 * math.sin(t * 9 + ph1))
        cx = x + wob * math.sin(t * 4.0 + ph2)
        left.append((cx - w / 2, yy))
        right.append((cx + w / 2, yy))
    pts = left + right[::-1]
    for ox in (0, N, 2 * N):
        for oy in (0, N, 2 * N):
            d.polygon([(px + ox, py + oy) for px, py in pts], fill=255)


for _ in range(80):                                                      # основные струи
    streak(r.uniform(0, N), r.uniform(0, N), r.uniform(120, 520), r.uniform(4, 20), r.uniform(1, 6))
for _ in range(140):                                                     # мелкие капли и обрывки
    streak(r.uniform(0, N), r.uniform(0, N), r.uniform(15, 90), r.uniform(3, 9), r.uniform(0, 2))
im = big.filter(ImageFilter.GaussianBlur(1.0)).crop((N, N, 2 * N, 2 * N))
im.save(OUT)
rep = Image.new('L', (N, 2 * N))
rep.paste(im, (0, 0))
rep.paste(im, (0, N))
rep.resize((N // 2, N)).save(OUT.replace('.png', '_repeat_check.png'))
cover = sum(1 for v in im.getdata() if v > 128) / (N * N)
print(OUT, 'white share %.2f' % cover)
