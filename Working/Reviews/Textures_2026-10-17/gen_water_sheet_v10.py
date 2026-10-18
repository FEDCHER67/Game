"""Лист воды v08 / v09 / v10 (TASK-000821, Вадим: «голубее сделай море»): тот же один цвет без пятен, три степени голубого."""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
W_ = os.path.join(HERE, 'water')
F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 20)
fs = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 15)
rows = [
    ('v08 — как было (прошлый лист)', 'water_calm_v08_%s.png'),
    ('ВАРИАНТ 1 (v09) — голубее', 'water_calm_v09_%s.png'),
    ('ВАРИАНТ 2 (v10) — ещё голубее', 'water_calm_v10_%s.png'),
]
TW, TH, PAD = 560, 315, 10
W = 3 * TW + 4 * PAD
H = PAD + len(rows) * (32 + TH + PAD) + 34
im = Image.new('RGB', (W, H), (240, 240, 236))
d = ImageDraw.Draw(im)
y = PAD
for title, pat in rows:
    d.text((PAD, y), title, font=F, fill=(30, 40, 46))
    y += 32
    for i, k in enumerate(('a', 's', 'c')):
        t = Image.open(os.path.join(W_, pat % k)).convert('RGB').resize((TW, TH), Image.LANCZOS)
        im.paste(t, (PAD + i * (TW + PAD), y))
    y += TH + PAD
d.text((PAD, y + 2), 'Тестовая сцена: небо — плоский цвет; диагональ на 3-м кадре — край дна тестовой сцены. Скажи номер варианта.', font=fs, fill=(70, 78, 84))
out = os.path.join(HERE, 'SUMMARY_water_bluer_v10.jpg')
im.save(out, quality=90)
print(out, im.size)
