"""Текстуры Неблагополучного по хрущёвкам и сталинкам (TASK-000812, Вадим: «вдохновись прямо советскими сталинками,
хрущёвками»). Стилизованные бесшовные albedo 1024 + превью фасадов (хрущёвка панельная, хрущёвка кирпичная, сталинка).
PIL без numpy. Файлы: candidates_rough_soviet_v01/."""
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'candidates_rough_soviet_v01')
os.makedirs(OUT, exist_ok=True)
N = 1024


def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, k):
    return tuple(max(0, min(255, int(round(v * k)))) for v in c)


def noise_layer(seed, cells, size=N):
    r = random.Random(seed)
    g = Image.new('L', (cells, cells))
    g.putdata([r.randint(0, 255) for _ in range(cells * cells)])
    big = Image.new('L', (cells * 3, cells * 3))
    for i in range(3):
        for j in range(3):
            big.paste(g, (i * cells, j * cells))
    return big.resize((size * 3, size * 3), Image.BICUBIC).crop((size, size, 2 * size, 2 * size))


def apply_noise(im, seed, cells, amp):
    n = noise_layer(seed, cells, im.width).load()
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            k = 1.0 + amp * (n[x, y] - 128) / 128.0
            r_, g_, b_ = px[x, y]
            px[x, y] = (min(255, int(r_ * k)), min(255, int(g_ * k)), min(255, int(b_ * k)))
    return im


def rect_wrap(d, x0, y0, x1, y1, fill):
    for ox in (-N, 0, N):
        for oy in (-N, 0, N):
            d.rectangle((x0 + ox, y0 + oy, x1 + ox, y1 + oy), fill=fill)


TEX = {}   # код -> (название, путь, ширина тайла м, высота тайла м)


def save(code, name, im, w_m, h_m):
    p = os.path.join(OUT, '%s_%s_albedo.png' % (code, name))
    im.save(p)
    TEX[code] = (name, p, w_m, h_m)


# KH1 — панель хрущёвки: серый бетон, тонкие тёмные швы-герметик; тайл = 2 панели x 2 этажа (6,4 x 5,6 м)
r = random.Random(1)
im = Image.new('RGB', (N, N), hexc('#57595A'))
d = ImageDraw.Draw(im)
pw, ph = N // 2, N // 2
for i in range(2):
    for j in range(2):
        c = shade(hexc('#B4B3AC'), 1 + r.uniform(-0.035, 0.035))
        rect_wrap(d, i * pw + 3, j * ph + 3, (i + 1) * pw - 4, (j + 1) * ph - 4, c)
im = apply_noise(im, 101, 14, 0.014).filter(ImageFilter.GaussianBlur(0.6))
save('KH1', 'panel_grey_seams', im, 6.4, 5.6)

# KH2 — панель с мелкой керамической плиткой (серии 1-464): сетка ~12 см, кое-где выпавшие плитки
r = random.Random(2)
im = Image.new('RGB', (N, N), hexc('#4E5152'))
d = ImageDraw.Draw(im)
tile = N // 54                                                       # ~12 см при 6,4 м тайла
for i in range(0, N, pw):
    pass
for y in range(0, N, tile):
    for x in range(0, N, tile):
        if x % pw < 4 or y % ph < 4:
            continue
        base = hexc('#C3C8C9') if r.random() > 0.08 else hexc('#AEB6B9')
        c = shade(base, 1 + r.uniform(-0.04, 0.04))
        d.rectangle((x + 1, y + 1, x + tile - 2, y + tile - 2), fill=c)
for _ in range(14):                                                  # пятна выпавшей плитки
    cx, cy = r.randrange(N), r.randrange(N)
    w, h = r.randint(2, 6) * tile, r.randint(1, 4) * tile
    rect_wrap(d, cx, cy, cx + w, cy + h, hexc('#8E908A'))
for i in range(3):                                                   # швы между панелями
    rect_wrap(d, i * pw - 3, 0, i * pw + 3, N, hexc('#4A4C4D'))
    rect_wrap(d, 0, i * ph - 3, N, i * ph + 3, hexc('#4A4C4D'))
im = apply_noise(im, 102, 12, 0.025).filter(ImageFilter.GaussianBlur(0.5))
save('KH2', 'panel_small_tiles', im, 6.4, 5.6)

# KH3 — белый силикатный кирпич: 250 x 65 мм, шов 10 мм, ложковая перевязка; тайл 1 x 1 м
r = random.Random(3)
ppm = N / 1.0
im = Image.new('RGB', (N, N), hexc('#9C9C96'))
d = ImageDraw.Draw(im)
bw, bh, j = 0.26 * ppm, 0.076 * ppm, 0.011 * ppm
rows = round(1.0 / 0.076)
bh = N / rows
cols = round(1.0 / 0.26)
bw = N / cols
for row in range(rows):
    off = (row % 2) * bw / 2
    for col in range(cols + 1):
        c = shade(hexc('#DEDDD6') if r.random() > 0.12 else hexc('#CFCFC8'), 1 + r.uniform(-0.03, 0.03))
        x0 = col * bw + off
        y0 = row * bh
        rect_wrap(d, int(x0 + j / 2), int(y0 + j / 2), int(x0 + bw - j / 2), int(y0 + bh - j / 2), c)
im = apply_noise(im, 103, 10, 0.03).filter(ImageFilter.GaussianBlur(0.5))
save('KH3', 'silicate_brick_white', im, 1.0, 1.0)

# KH4 — красный кирпич хрущёвки (приглушённый, светлые швы); тайл 1 x 1 м
r = random.Random(4)
im = Image.new('RGB', (N, N), hexc('#B8AFA3'))
d = ImageDraw.Draw(im)
for row in range(rows):
    off = (row % 2) * bw / 2
    for col in range(cols + 1):
        c = shade(r.choice((hexc('#8E4B3C'), hexc('#9A5544'), hexc('#83463A'))), 1 + r.uniform(-0.04, 0.04))
        x0 = col * bw + off
        y0 = row * bh
        rect_wrap(d, int(x0 + j / 2), int(y0 + j / 2), int(x0 + bw - j / 2), int(y0 + bh - j / 2), c)
im = apply_noise(im, 104, 10, 0.03).filter(ImageFilter.GaussianBlur(0.5))
save('KH4', 'red_brick_muted', im, 1.0, 1.0)

# ST1 — сталинка: тёплая охристая штукатурка, мягкие пятна; тайл 2 x 2 м
im = Image.new('RGB', (N, N), hexc('#D2AE74'))
im = apply_noise(im, 105, 8, 0.02)
im = apply_noise(im, 106, 40, 0.008).filter(ImageFilter.GaussianBlur(0.8))
save('ST1', 'stalinka_ochre_plaster', im, 2.0, 2.0)

# ST2 — сталинка: руст первого этажа (горизонтальные русты через 0,45 м, вертикальные вразбежку через 1,2 м); тайл 2,4 x 1,8 м
r = random.Random(7)
im = Image.new('RGB', (N, N), hexc('#8E8574'))
d = ImageDraw.Draw(im)
rh = N / 4
for row in range(4):
    off = (row % 2) * N / 4
    for col in range(3):
        c = shade(hexc('#BFB39A'), 1 + r.uniform(-0.03, 0.03))
        x0 = col * N / 2 + off
        rect_wrap(d, int(x0 + 7), int(row * rh + 9), int(x0 + N / 2 - 7), int(row * rh + rh - 9), c)
        rect_wrap(d, int(x0 + 7), int(row * rh + 9), int(x0 + N / 2 - 7), int(row * rh + 16), shade(c, 1.08))   # светлая кромка сверху
im = apply_noise(im, 107, 10, 0.03).filter(ImageFilter.GaussianBlur(0.7))
save('ST2', 'stalinka_rustication', im, 2.4, 1.8)

# ST3 — сталинка: трим белых тяг/карнизов (полосы сверху вниз: карниз, тяга, наличник, подоконник, пояс)
im = Image.new('RGB', (N, N), hexc('#ECE7DC'))
d = ImageDraw.Draw(im)
y = 0
for hpx, col in ((70, '#F4F0E8'), (18, '#C9C2B4'), (60, '#E8E2D6'), (26, '#BDB5A6'), (90, '#F2EEE6'), (14, '#B7AF9F'),
                 (120, '#EFEBE2'), (30, '#CFC8BA'), (80, '#F4F1EA'), (22, '#C4BCAD'), (150, '#EDE8DE'), (40, '#D3CCBF'),
                 (110, '#F3EFE7'), (24, '#BEB6A7'), (250, '#ECE7DC')):
    d.rectangle((0, y, N, y + hpx), fill=hexc(col))
    y += hpx
im = apply_noise(im, 108, 10, 0.02)
save('ST3', 'stalinka_white_trim', im, 2.0, 2.0)


# ---------- превью фасадов
def tiled(code, w_px, h_px, ppm):
    name, path, wm, hm = TEX[code]
    t = Image.open(path).convert('RGB').resize((max(1, int(wm * ppm)), max(1, int(hm * ppm))), Image.LANCZOS)
    out = Image.new('RGB', (w_px, h_px))
    for x in range(0, w_px, t.width):
        for yy in range(0, h_px, t.height):
            out.paste(t, (x, yy))
    return out


PPM = 24
F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 18)
f = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 14)


def window(d, x, y, w, h, frame='#E9E7E1', glass='#3E4B55', sash=3):
    d.rectangle((x, y, x + w, y + h), fill=hexc(frame))
    t = 3
    inner = (x + t, y + t, x + w - t, y + h - t)
    d.rectangle(inner, fill=hexc(glass))
    for k in range(1, sash):
        xx = x + w * k // sash
        d.rectangle((xx - 1, y + t, xx + 1, y + h - t), fill=hexc(frame))
    d.rectangle((x + t, y + int(h * 0.3) - 1, x + w - t, y + int(h * 0.3) + 1), fill=hexc(frame))
    d.rectangle((x - 3, y + h, x + w + 3, y + h + 4), fill=hexc('#9A9C98'))   # отлив


def khrushchyovka(wall_code, title, glazed_seed):
    floors, fh = 5, 2.8
    Wm, Hm = 30.0, floors * fh + 0.9
    W, H = int(Wm * PPM), int(Hm * PPM)
    im = Image.new('RGB', (W + 40, H + 60), (200, 214, 222))
    wall = tiled(wall_code, W, H, PPM)
    im.paste(wall, (20, 40))
    d = ImageDraw.Draw(im)
    r = random.Random(glazed_seed)
    d.rectangle((14, 34, W + 26, 44), fill=hexc('#6F706C'))           # парапет плоской крыши
    d.rectangle((20, 40 + H - int(0.9 * PPM), W + 20, 40 + H), fill=hexc('#7D7C75'))   # цоколь
    winw, winh = int(1.5 * PPM), int(1.45 * PPM)
    step = int(3.0 * PPM)
    entrances = (2, 7)
    for fl in range(floors):
        yb = 40 + H - int(0.9 * PPM) - int((fl + 1) * fh * PPM)
        for k in range(10):
            x = 20 + int(0.75 * PPM) + k * step
            if fl == 0 and k in entrances:
                dx = x + winw // 2
                d.rectangle((dx - int(0.6 * PPM), 40 + H - int(0.9 * PPM) - int(2.2 * PPM), dx + int(0.6 * PPM), 40 + H - int(0.9 * PPM)), fill=hexc('#4E4036'))   # дверь подъезда
                d.rectangle((dx - int(1.0 * PPM), 40 + H - int(0.9 * PPM) - int(2.5 * PPM), dx + int(1.0 * PPM), 40 + H - int(0.9 * PPM) - int(2.3 * PPM)), fill=hexc('#8E8D86'))   # козырёк
                continue
            if fl >= 1 and k in entrances:                         # окна лестничной клетки — между этажами
                window(d, x + 6, yb + int(1.2 * PPM), winw - 12, int(1.1 * PPM), sash=2)
                continue
            balcony = fl >= 1 and k in (0, 4, 5, 9)
            window(d, x, yb + int(0.6 * PPM), winw, winh, frame=r.choice(('#E9E7E1', '#E9E7E1', '#F4F4F2', '#C9B79A')))
            if balcony:
                bx0, bx1 = x - int(0.5 * PPM), x + winw + int(0.5 * PPM)
                by = yb + int(0.6 * PPM) + winh + 6
                if r.random() < 0.45:                              # застеклённый балкон, разные рамы
                    d.rectangle((bx0, by - int(1.9 * PPM), bx1, by), fill=hexc(r.choice(('#EDEBE6', '#B9A786', '#D7D5CE'))))
                    for q in range(4):
                        xx = bx0 + (bx1 - bx0) * (q + 0.1) / 4
                        d.rectangle((xx, by - int(1.75 * PPM), xx + (bx1 - bx0) / 4 - 6, by - int(0.95 * PPM)), fill=hexc('#455661'))
                    d.rectangle((bx0, by - int(0.9 * PPM), bx1, by), fill=hexc(r.choice(('#9DA3A6', '#B8B1A2', '#7E8C93'))))
                else:                                              # открытый балкон с решёткой и бельём
                    d.rectangle((bx0, by - 4, bx1, by), fill=hexc('#8B8A84'))
                    for q in range(0, bx1 - bx0, 5):
                        d.line((bx0 + q, by - int(1.0 * PPM), bx0 + q, by), fill=hexc('#55585A'), width=1)
                    d.line((bx0, by - int(1.0 * PPM), bx1, by - int(1.0 * PPM)), fill=hexc('#55585A'), width=2)
    for xx in (20 + int(6.0 * PPM), 20 + int(21.0 * PPM)):             # водосточные трубы
        d.rectangle((xx, 44, xx + 4, 40 + H - int(0.9 * PPM)), fill=hexc('#8C8D88'))
    d.text((20, 8), title, font=F, fill=(30, 40, 46))
    return im


def stalinka(title):
    Wm, Hm = 30.0, 6 * 3.3 + 2.5
    W, H = int(Wm * PPM), int(Hm * PPM)
    im = Image.new('RGB', (W + 40, H + 90), (200, 214, 222))
    d = ImageDraw.Draw(im)
    top = 70
    d.polygon([(10, top + 20), (W + 30, top + 20), (W + 5, top - 35), (35, top - 35)], fill=hexc('#5C6B58'))   # скатная металлическая крыша
    wall = tiled('ST1', W, H, PPM)
    im.paste(wall, (20, top + 20))
    gf = int(4.0 * PPM)
    rust = tiled('ST2', W, gf, PPM)
    im.paste(rust, (20, top + 20 + H - gf))
    trim = tiled('ST3', W, int(1.0 * PPM), PPM)
    im.paste(trim, (20, top + 20))                                 # карниз
    im.paste(tiled('ST3', W, int(0.35 * PPM), PPM), (20, top + 20 + H - gf - int(0.35 * PPM)))   # пояс над рустом
    d = ImageDraw.Draw(im)
    d.rectangle((14, top + 14, W + 26, top + 24), fill=hexc('#F3EFE7'))
    step = int(3.3 * PPM)
    winw, winh = int(1.4 * PPM), int(2.1 * PPM)
    for fl in range(5):
        yb = top + 20 + H - gf - int((fl + 1) * 3.3 * PPM)
        for k in range(9):
            x = 20 + int(1.0 * PPM) + k * step
            if k == 4:
                continue
            d.rectangle((x - 6, yb + int(0.7 * PPM) - 6, x + winw + 6, yb + int(0.7 * PPM) + winh + 10), fill=hexc('#F1EDE4'))   # белый наличник
            if fl == 1:
                d.polygon([(x - 10, yb + int(0.7 * PPM) - 6), (x + winw + 10, yb + int(0.7 * PPM) - 6), (x + winw // 2, yb + int(0.7 * PPM) - 22)], fill=hexc('#F1EDE4'))   # сандрик
            window(d, x, yb + int(0.7 * PPM), winw, winh, frame='#EDE9E0', glass='#3B4852', sash=2)
        xm = 20 + int(1.0 * PPM) + 4 * step
        if fl in (1, 2, 3):                                        # балкон с балясинами над аркой
            d.rectangle((xm - 10, yb + int(0.7 * PPM), xm + winw + 10, yb + int(0.7 * PPM) + winh + 6), fill=hexc('#F1EDE4'))
            window(d, xm, yb + int(0.7 * PPM), winw, winh, frame='#EDE9E0', glass='#3B4852', sash=2)
            by = yb + int(0.7 * PPM) + winh + 8
            d.rectangle((xm - int(0.8 * PPM), by - int(0.9 * PPM), xm + winw + int(0.8 * PPM), by), fill=hexc('#E6E1D6'))
            for q in range(xm - int(0.7 * PPM), xm + winw + int(0.8 * PPM), 7):
                d.rectangle((q, by - int(0.8 * PPM), q + 3, by - 4), fill=hexc('#C4BCAE'))
    ax = 20 + int(1.0 * PPM) + 4 * step + int(0.7 * PPM)
    aw = int(4.2 * PPM)
    ay = top + 20 + H
    d.rectangle((ax - aw // 2, ay - int(3.3 * PPM), ax + aw // 2, ay), fill=hexc('#2E3236'))   # арка во двор
    d.pieslice((ax - aw // 2, ay - int(3.3 * PPM) - aw // 2, ax + aw // 2, ay - int(3.3 * PPM) + aw // 2), 180, 360, fill=hexc('#2E3236'))
    for k in (0, 1, 2, 3, 5, 6, 7, 8):                              # окна-витрины первого этажа
        x = 20 + int(1.0 * PPM) + k * step
        window(d, x - 4, ay - int(3.2 * PPM), winw + 8, int(2.4 * PPM), frame='#D9D3C6', glass='#3E4B55', sash=2)
    d.text((20, 8), title, font=F, fill=(30, 40, 46))
    return im


# ---------- лист (v01b: без сталинок — у нас только хрущёвки и американский город, Вадим)
T = 200
cards = ['KH1', 'KH2', 'KH3', 'KH4']
LABEL = {'KH1': 'Серая панель, швы', 'KH2': 'Панель с мелкой плиткой', 'KH3': 'Белый силикатный кирпич', 'KH4': 'Красный кирпич'}
f1 = khrushchyovka('KH1', 'ХРУЩЁВКА ПАНЕЛЬНАЯ (KH1): 5 этажей, плоская крыша, разные балконы', 11)
f2 = khrushchyovka('KH3', 'ХРУЩЁВКА КИРПИЧНАЯ (KH3, силикатный кирпич)', 12)
W = max(f1.width + f2.width + 30, len(cards) * (T + 10) + 20)
H = 50 + T + 40 + max(f1.height, f2.height) + 20
sheet = Image.new('RGB', (W, H), (240, 240, 236))
d = ImageDraw.Draw(sheet)
d.text((10, 10), 'Неблагополучный: хрущёвки — текстуры (свои, стилизованные)', font=F, fill=(46, 80, 110))
for i, code in enumerate(cards):
    name, path, wm, hm = TEX[code]
    t = Image.open(path).convert('RGB').resize((T, T))
    x = 10 + i * (T + 10)
    sheet.paste(t, (x, 44))
    d.text((x, 44 + T + 4), '%s %s' % (code, LABEL[code]), font=f, fill=(30, 40, 46))
y = 44 + T + 36
sheet.paste(f1, (10, y))
sheet.paste(f2, (20 + f1.width, y))
out = os.path.join(HERE, 'SHEET_05b_rough_khrushchyovka.jpg')
sheet.save(out, quality=88)
print(out, sheet.size)
