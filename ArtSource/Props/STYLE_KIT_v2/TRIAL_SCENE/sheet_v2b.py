import sys
from PIL import Image, ImageDraw, ImageFont
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as M

A = 'C:/Dev/Game/ArtSource/References/Art/'
ROWS = [('SquareA', 'Кадр square_a: fly-cam 3/4 над площадью с часами (поза и FOV сняты с кадра от 05.10)'),
        ('PlayNpcClock', 'Кадр play_npc_clock: камера игры за NPC у площади (поза снята с кадра от 05.10)'),
        ('Facade_1p6m', 'Глаза на 1,6 м, 15 м до фасада дома O06_T3_U1 (грамматика фасада, библия §12)'),
        ('Wide', 'Общий план района: старый город, панельки, башни, канал, элитный холм')]
W, H = 960, 540
PAD, CAP, HEAD = 10, 64, 56
font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 26)
fcap = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
fnum = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
sheet = Image.new('RGB', (2 * W + 3 * PAD, HEAD + len(ROWS) * (H + CAP) + PAD), (243, 239, 230))
d = ImageDraw.Draw(sheet)
d.text((PAD, 14), 'ДО: Map_Look_v12 (та же поза камеры)', font=font, fill=(40, 40, 40))
d.text((2 * PAD + W, 14), 'ПОСЛЕ: Map_Look_v13_trial — STYLE_KIT_v2 (v02) + свет библии v2', font=font, fill=(40, 40, 40))
y = HEAD
for key, cap in ROWS:
    for col, path in enumerate((A + f'Before_v12_{key}_v2b.png', A + f'StyleTrial_v2b_{key}.png')):
        im = Image.open(path).convert('RGB').resize((W, H), Image.LANCZOS)
        x = PAD + col * (W + PAD)
        sheet.paste(im, (x, y))
        m = M.metrics(path)
        d.text((x, y + H + 6), cap if col == 0 else cap.split(':')[0], font=fcap, fill=(50, 50, 50))
        d.text((x, y + H + 32), f"светлые B1+B2 {m['B1+B2'] * 100:.0f} %   зелёный {m['green'] * 100:.0f} %   тёплый {m['warm'] * 100:.0f} %   средний L* {m['meanL']:.0f}",
               font=fnum, fill=(90, 90, 90))
    y += H + CAP
sheet.save(A + 'StyleTrial_v2b_BeforeAfter.png')
print(sheet.size)
