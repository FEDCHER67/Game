"""Лист воды v08 (TASK-000818): было v06 (голубые пятна гребней) -> стало v08 (один спокойный голубой, прозрачное мелководье)."""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
W_ = os.path.join(HERE, 'water')
F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 20)
fs = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 15)
rows = [
    ('БЫЛО v06: голубые пятна на гребнях', ['water_sot_v06_a.png', 'water_sot_v06_c.png']),
    ('СТАЛО v08: один голубой цвет, без пятен; мелководье прозрачное (дно подкрашено цветом воды); рябь и блики остались',
     ['water_calm_v08_a.png', 'water_calm_v08_s.png', 'water_calm_v08_c.png']),
]
TW, TH, PAD = 620, 349, 10
W = 3 * TW + 4 * PAD
H = PAD + len(rows) * (34 + TH + PAD) + 40
im = Image.new('RGB', (W, H), (240, 240, 236))
d = ImageDraw.Draw(im)
y = PAD
for title, files in rows:
    d.text((PAD, y), title, font=F, fill=(30, 40, 46))
    y += 34
    for i, f in enumerate(files):
        t = Image.open(os.path.join(W_, f)).convert('RGB').resize((TW, TH), Image.LANCZOS)
        im.paste(t, (PAD + i * (TW + PAD), y))
    y += TH + PAD
d.text((PAD, y + 4), 'Тестовая сцена: небо — плоский цвет, без пост-обработки; резкая диагональ на 3-м кадре — край дна тестовой сцены (дальше дна нет). На карте дно сплошное.',
       font=fs, fill=(70, 78, 84))
out = os.path.join(HERE, 'SUMMARY_water_calm_v08.jpg')
im.save(out, quality=90)
print(out, im.size)
