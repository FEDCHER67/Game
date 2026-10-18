"""Свои недостающие текстуры (TASK-000824, пока GPT делает остальные):
1) мокрый песок у воды TL_sand_wet_albedo_v01.png — из нашего L05 TL_sand (темнее, чуть холоднее, глаже), бесшовный 1024, тайл 8 м;
2) атлас окон и дверей хрущёвки KH_windows_atlas_v01.png — RGBA 2048 x 1024, 200 px/м, прозрачный фон: окна в белой, деревянной
   и новой пластиковой раме, окно лестничной клетки, кухонное окно, две двери подъезда, три подтёка-декали. Стиль — как на листе KH.
Лист SHEET_06_own_textures_v01.jpg. PIL без numpy."""
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'own_textures_v01')
os.makedirs(OUT, exist_ok=True)
A = r'C:\Users\chern_0eqkb03\Desktop\GAME\Assets\OnlyVolunteers\Art\Map\Textures\Detail'
SAND = os.path.join(A, 'TL_sand_albedo.png')
KH1B = os.path.join(HERE, 'candidates_rough_soviet_v02', 'KH1b_panel_grey_shabby_albedo.png')


def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def wrap_blur(im, radius):
    w, h = im.size
    big = Image.new(im.mode, (w * 3, h * 3))
    for i in range(3):
        for j in range(3):
            big.paste(im, (i * w, j * h))
    return big.filter(ImageFilter.GaussianBlur(radius)).crop((w, h, 2 * w, 2 * h))


# ---------- 1) мокрый песок
src = Image.open(SAND).convert('RGB')
wet = Image.merge('RGB', [ch.point(lambda v, k=k: int(v * k)) for ch, k in zip(src.split(), (0.76, 0.78, 0.83))])
wet = wrap_blur(wet, 1.2)                                       # мокрый песок глаже
wet_rgba = wet.convert('RGBA')
WET = os.path.join(OUT, 'TL_sand_wet_albedo_v01.png')
wet_rgba.save(WET)

# ---------- 2) атлас окон и дверей хрущёвки (200 px/м)
PPM = 200
ATL = Image.new('RGBA', (2048, 1024), (0, 0, 0, 0))
d = ImageDraw.Draw(ATL)
CELL_W, CELL_H = 400, 500
cells = []


def window(x, y, w_m, h_m, frame, sash, glass='#3E4B55'):
    w, h = int(w_m * PPM), int(h_m * PPM)
    t = 14
    d.rectangle((x, y, x + w, y + h), fill=hexc(frame) + (255,))
    d.rectangle((x + t, y + t, x + w - t, y + h - t), fill=hexc(glass) + (255,))
    # мягкий светлый отблеск по диагонали в каждом стекле
    for k in range(sash):
        gx0 = x + t + (w - 2 * t) * k // sash
        gx1 = x + t + (w - 2 * t) * (k + 1) // sash
        d.polygon([(gx0 + 10, y + h - t - 10), (gx0 + 40, y + h - t - 10), (gx1 - 10, y + t + 40), (gx1 - 10, y + t + 10)],
                  fill=(76, 92, 104, 255))
    for k in range(1, sash):                                    # импосты
        xx = x + w * k // sash
        d.rectangle((xx - 6, y + t, xx + 6, y + h - t), fill=hexc(frame) + (255,))
    d.rectangle((x + t, y + int(h * 0.3) - 6, x + w - t, y + int(h * 0.3) + 6), fill=hexc(frame) + (255,))   # фрамуга
    d.rectangle((x - 14, y + h, x + w + 14, y + h + 18), fill=hexc('#9A9C98') + (255,))   # отлив
    return (x - 14, y, x + w + 14, y + h + 18)


def door(x, y, colour, frame='#3A3029'):
    w, h = int(1.2 * PPM), int(2.2 * PPM)
    d.rectangle((x - 16, y - 16, x + w + 16, y + h), fill=hexc(frame) + (255,))
    d.rectangle((x, y, x + w, y + h), fill=hexc(colour) + (255,))
    d.rectangle((x + 30, y + 40, x + w - 30, y + 150), fill=tuple(max(0, c - 18) for c in hexc(colour)) + (255,))   # филёнка
    d.rectangle((x + w - 50, y + int(h * 0.5) - 6, x + w - 20, y + int(h * 0.5) + 6), fill=hexc('#C9C2B0') + (255,))   # ручка
    d.rectangle((x + w + 24, y + 120, x + w + 60, y + 190), fill=hexc('#7A7D80') + (255,))   # домофон
    return (x - 16, y - 16, x + w + 60, y + h)


def streak_decal(x, y, w_px, len_px):
    lay = Image.new('L', (w_px * 3, len_px + 20), 0)
    ld = ImageDraw.Draw(lay)
    r = random.Random(x + y)
    for _ in range(3):
        sx = w_px + r.uniform(-w_px * 0.6, w_px * 0.6)
        ln = len_px * r.uniform(0.6, 1.0)
        steps = 40
        for s_ in range(steps):
            t0, t1 = s_ / steps, (s_ + 1) / steps
            ww = w_px * 0.22 * (1 - 0.65 * t0) * (0.85 + 0.3 * r.random())
            ld.rectangle((sx - ww, 10 + ln * t0, sx + ww, 10 + ln * t1), fill=int(190 * (1 - t0) ** 1.3))
    lay = lay.filter(ImageFilter.GaussianBlur(9))
    col = Image.new('RGBA', lay.size, hexc('#5A5C58') + (0,))
    col.putalpha(lay)
    ATL.alpha_composite(col, (x, y))
    return (x, y, x + lay.width, y + lay.height)


LAB = []
specs = [
    ('Окно, белая рама', lambda x, y: window(x + 50, y + 60, 1.5, 1.45, '#E9E7E1', 3)),
    ('Окно, деревянная рама', lambda x, y: window(x + 50, y + 60, 1.5, 1.45, '#C9B79A', 3)),
    ('Окно, новый пластик', lambda x, y: window(x + 50, y + 60, 1.5, 1.45, '#F4F4F2', 2)),
    ('Окно лестничной клетки', lambda x, y: window(x + 74, y + 80, 1.26, 1.1, '#E9E7E1', 2)),
    ('Кухонное окно', lambda x, y: window(x + 80, y + 60, 1.2, 1.45, '#E9E7E1', 2)),
    ('Дверь подъезда (металл)', lambda x, y: door(x + 60, y + 40, '#4E4036')),
    ('Дверь подъезда (крашеная)', lambda x, y: door(x + 60, y + 40, '#5E6B60')),
    ('Подтёк под окном', lambda x, y: streak_decal(x + 90, y + 40, 70, 300)),
    ('Подтёк длинный', lambda x, y: streak_decal(x + 90, y + 20, 60, 440)),
    ('Подтёк широкий', lambda x, y: streak_decal(x + 40, y + 40, 100, 260)),
]
for n, (lab, fn) in enumerate(specs):
    cx, cy = (n % 5) * CELL_W + 24, (n // 5) * CELL_H + 12
    box = fn(cx, cy)
    LAB.append((lab, (cx, cy)))
ATLAS = os.path.join(OUT, 'KH_windows_atlas_v01.png')
ATL.save(ATLAS)

# ---------- лист
F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 20)
f = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 14)
fs = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 13)
W, PAD = 1250, 10
sheet = Image.new('RGB', (W, 1010), (240, 240, 236))
sd = ImageDraw.Draw(sheet)
sd.text((PAD, 10), 'Свои текстуры (пока GPT делает остальные): мокрый песок и окна хрущёвок', font=F, fill=(46, 80, 110))
T = 220
sheet.paste(src.resize((T, T), Image.LANCZOS), (PAD, 44))
sd.text((PAD, 44 + T + 4), 'L05 Песок (сухой, есть)', font=f, fill=(30, 40, 46))
sheet.paste(wet.resize((T, T), Image.LANCZOS), (PAD + T + 10, 44))
sd.text((PAD + T + 10, 44 + T + 4), 'L05b Мокрый песок (новый)', font=f, fill=(30, 40, 46))
# берег: сухой -> мокрый (1,5 м) -> вода v09 с пеной
SW, SH = W - 2 * PAD - 2 * (T + 10), T
shore = Image.new('RGB', (SW, SH))
ppm_s = SW / 12.0
dry_t = src.resize((int(8 * ppm_s), int(8 * ppm_s)), Image.LANCZOS)
wet_t = wet.resize(dry_t.size, Image.LANCZOS)
for xx in range(0, SW, dry_t.width):
    for yy in range(0, SH, dry_t.height):
        shore.paste(dry_t, (xx, yy))
wet_l = Image.new('RGB', (SW, SH))
for xx in range(0, SW, wet_t.width):
    for yy in range(0, SH, wet_t.height):
        wet_l.paste(wet_t, (xx, yy))
mask = Image.new('L', (SW, SH), 0)
md = ImageDraw.Draw(mask)
x_wet0, x_wet1, x_water = int(5.0 * ppm_s), int(6.5 * ppm_s), int(7.0 * ppm_s)
for xx in range(SW):
    v = 0 if xx < x_wet0 else 255 if xx >= x_wet1 else int(255 * (xx - x_wet0) / (x_wet1 - x_wet0))
    md.line((xx, 0, xx, SH), fill=v)
shore = Image.composite(wet_l, shore, mask)
# вода — кусок настоящего рендера варианта 1 (мель, вид сверху), с мягкой полосой пены у кромки
wr = Image.open(os.path.join(HERE, 'water', 'water_calm_v09_s.png')).convert('RGB').crop((830, 470, 1200, 675))
wr = wr.resize((SW - x_water, int(wr.height * (SW - x_water) / wr.width)), Image.LANCZOS)
wr = wr.resize((SW - x_water, SH), Image.LANCZOS)
shore.paste(wr, (x_water, 0))
foam = Image.new('L', (SW, SH), 0)
fd = ImageDraw.Draw(foam)
rr_ = random.Random(5)
for yy in range(0, SH, 3):
    xw = x_water + int(10 * (0.5 + 0.5 * __import__('math').sin(yy * 0.07)) + rr_.uniform(-3, 3))
    fd.rectangle((xw - 10, yy, xw + 6, yy + 3), fill=230)
foam = foam.filter(ImageFilter.GaussianBlur(3))
shore = Image.composite(Image.new('RGB', (SW, SH), (246, 248, 246)), shore, foam)
sheet.paste(shore, (PAD + 2 * (T + 10), 44))
sd.text((PAD + 2 * (T + 10), 44 + T + 4), 'Как у воды: сухой песок → полоса мокрого 1,5 м → вода (вариант 1) с пеной', font=f, fill=(30, 40, 46))
# атлас окон на фоне обшарпанной панели
y0 = 44 + T + 40
sd.text((PAD, y0), 'Окна и двери хрущёвки — атлас 2048 x 1024 (прозрачный фон), на сером фоне панели для вида', font=F, fill=(46, 80, 110))
bg = Image.open(KH1B).convert('RGB').resize((2048, 2048), Image.LANCZOS).crop((0, 0, 2048, 1024))
bg.paste(ATL, (0, 0), ATL)
k = (W - 2 * PAD) / 2048
prev = bg.resize((W - 2 * PAD, int(1024 * k)), Image.LANCZOS)
sheet.paste(prev, (PAD, y0 + 30))
for lab, (cx, cy) in LAB:
    sd.rectangle((PAD + cx * k, y0 + 30 + (cy + CELL_H - 60) * k, PAD + cx * k + 190, y0 + 30 + (cy + CELL_H - 60) * k + 18), fill=(240, 240, 236))
    sd.text((PAD + cx * k + 3, y0 + 30 + (cy + CELL_H - 60) * k + 1), lab, font=fs, fill=(30, 40, 46))
sheet = sheet.crop((0, 0, W, y0 + 30 + prev.height + 10))
out = os.path.join(HERE, 'SHEET_06_own_textures_v01.jpg')
sheet.save(out, quality=90)
print(out, sheet.size, WET, ATLAS)
