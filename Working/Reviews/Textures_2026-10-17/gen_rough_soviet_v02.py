"""Обшарпанная панель хрущёвки KH1b (TASK-000820, Вадим: «на хрущёвке все одинаковые практически; будут не очень чистые,
обшарпанные — это как раз детализацию добавит»). Бесшовный albedo 2048 = 4 панели x 4 этажа = 12,8 x 11,2 м (крупнее KH1,
чтобы повтор не бросался в глаза): у каждой панели своя степень грязи — пятна сырости внизу панелей, подтёки от швов,
заплатки на швах (чёрный битум и свежий светлый герметик), сколы бетона, ржавые подтёки. Превью: та же хрущёвка чистая (KH1)
и обшарпанная (KH1b, + подтёки под окнами и балконами, грязный цоколь). PIL без numpy.
Файлы: candidates_rough_soviet_v02/, лист SHEET_05c_rough_khrushchyovka_shabby.jpg. v01 не меняется."""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'candidates_rough_soviet_v02')
os.makedirs(OUT, exist_ok=True)
KH1 = os.path.join(HERE, 'candidates_rough_soviet_v01', 'KH1_panel_grey_seams_albedo.png')   # 1024 = 2 x 2 панели
N = 2048
NP = 4                                      # панелей по ширине и по высоте тайла
PW = PH = N // NP                           # панель 3,2 x 2,8 м
TW_M, TH_M = 12.8, 11.2
PPY = N / TH_M                              # пикселей на метр по высоте


def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def smooth(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def noise_layer(seed, cells, size):
    r = random.Random(seed)
    g = Image.new('L', (cells, cells))
    g.putdata([r.randint(0, 255) for _ in range(cells * cells)])
    big = Image.new('L', (cells * 3, cells * 3))
    for i in range(3):
        for j in range(3):
            big.paste(g, (i * cells, j * cells))
    return big.resize((size * 3, size * 3), Image.BICUBIC).crop((size, size, 2 * size, 2 * size))


class WrapMask:
    """Маска на холсте 3N x 3N: всё рисуется 9 раз со сдвигом на N, размытие и обрезка центра — шов не виден."""

    def __init__(self):
        self.im = Image.new('L', (3 * N, 3 * N), 0)
        self.d = ImageDraw.Draw(self.im)

    def poly(self, pts, v):
        for ox in (0, N, 2 * N):
            for oy in (0, N, 2 * N):
                self.d.polygon([(x + ox, y + oy) for x, y in pts], fill=v)

    def rect(self, x0, y0, x1, y1, v):
        self.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], v)

    def done(self, blur):
        im = self.im.filter(ImageFilter.GaussianBlur(blur)) if blur else self.im
        return im.crop((N, N, 2 * N, 2 * N))


def streak(m, r, x, y0, length, w0, v):
    """Подтёк: сверху шире и темнее, книзу сужается и бледнеет."""
    steps = 8
    for s in range(steps):
        t0, t1 = s / steps, (s + 1) / steps
        wa, wb = w0 * (1 - 0.7 * t0), w0 * (1 - 0.7 * t1)
        xa = x + r.uniform(-0.6, 0.6)
        m.poly([(xa - wa / 2, y0 + length * t0), (xa + wa / 2, y0 + length * t0),
                (xa + wb / 2, y0 + length * t1), (xa - wb / 2, y0 + length * t1)], int(v * (1 - 0.85 * t0)))


def tint_composite(base, mask, colour, k):
    over = Image.new('RGB', base.size, colour)
    return Image.composite(over, base, mask.point(lambda q: int(q * k)))


def make_kh1b():
    r = random.Random(820)
    src = Image.open(KH1).convert('RGB')
    im = Image.new('RGB', (N, N))
    for i in range(2):
        for j in range(2):
            im.paste(src, (i * 1024, j * 1024))
    # своя «грязность» у каждой панели: 0 чистая … 1 очень грязная
    dirt = [[r.choice((0.0, 0.15, 0.35, 0.35, 0.6, 0.6, 0.85, 1.0)) for _ in range(NP)] for _ in range(NP)]
    # 1) панели чуть разного тона (заменённые / перекрашенные)
    pan = WrapMask()
    for i in range(NP):
        for j in range(NP):
            pan.rect(i * PW + 3, j * PH + 3, (i + 1) * PW - 4, (j + 1) * PH - 4, r.choice((0, 0, 40, 90, 140)))
    im = tint_composite(im, pan.done(0), (150, 149, 142), 0.35)
    # 2) пятна сырости — на половинном разрешении (мягкие), низ и углы панелей, рваные края
    H2 = N // 2
    nz = noise_layer(8201, 14, H2).load()
    nz2 = noise_layer(8202, 40, H2).load()
    damp = Image.new('L', (H2, H2), 0)
    dp = damp.load()
    pw2 = H2 // NP
    for y in range(H2):
        fy = (y % pw2) / pw2
        bottom = smooth((fy - 0.5) / 0.5)
        top = 0.3 * smooth((0.16 - fy) / 0.16)
        jy = y // pw2
        for x in range(H2):
            a = dirt[jy][x // pw2]
            if a <= 0:
                continue
            fx = (x % pw2) / pw2
            side = 0.5 * smooth((0.12 - min(fx, 1 - fx)) / 0.12)
            w = max(bottom, top, side * bottom * 2)
            n = (nz[x, y] / 255.0) * 0.7 + (nz2[x, y] / 255.0) * 0.3
            dp[x, y] = int(255 * a * w * smooth((n - 0.36) / 0.3))
    damp = damp.resize((N, N), Image.BICUBIC).filter(ImageFilter.GaussianBlur(3))
    im = tint_composite(im, damp, (102, 104, 100), 0.45)
    # 3) подтёки: в среднем 2–3 на панель, больше на грязных; от горизонтальных швов и редко с середины
    st = WrapMask()
    for i in range(NP):
        for j in range(NP):
            for _ in range(int(round(dirt[j][i] * r.uniform(2, 5)))):
                x = i * PW + r.uniform(20, PW - 20)
                y0 = j * PH + (r.uniform(4, 12) if r.random() < 0.8 else r.uniform(40, PH * 0.5))
                streak(st, r, x, y0, r.uniform(0.3, 1.5) * PPY, r.uniform(4, 12), r.randint(80, 150))
    im = tint_composite(im, st.done(2.2), (96, 98, 94), 0.5)
    # 4) ржавые подтёки (закладные, крепления)
    rs = WrapMask()
    for _ in range(9):
        x, y0 = r.uniform(0, N), r.randrange(NP) * PH + r.uniform(30, 140)
        rs.rect(x - 4, y0 - 4, x + 4, y0 + 4, 200)
        streak(rs, r, x, y0, r.uniform(0.5, 1.2) * PPY, r.uniform(5, 9), 160)
    im = tint_composite(im, rs.done(1.8), (139, 96, 62), 0.5)
    # 5) швы: заплатки чёрным битумом и свежим светлым герметиком
    sm, lm = WrapMask(), WrapMask()
    for _ in range(16):
        if r.random() < 0.5:
            x = r.randrange(NP) * PW
            y0, ln = r.uniform(0, N), r.uniform(80, 360)
            (sm if r.random() < 0.6 else lm).rect(x - r.uniform(5, 9), y0, x + r.uniform(5, 9), y0 + ln, 255)
        else:
            y = r.randrange(NP) * PH
            x0, ln = r.uniform(0, N), r.uniform(80, 380)
            (sm if r.random() < 0.6 else lm).rect(x0, y - r.uniform(5, 9), x0 + ln, y + r.uniform(5, 9), 255)
    im = tint_composite(im, sm.done(1.0), (52, 53, 55), 0.9)
    im = tint_composite(im, lm.done(1.0), (196, 195, 188), 0.85)
    # 6) сколы бетона у кромок панелей: светлое пятно + тёмная тень снизу
    chip, shad = WrapMask(), WrapMask()
    for _ in range(20):
        x = r.randrange(NP) * PW + r.uniform(-30, 30) if r.random() < 0.6 else r.uniform(0, N)
        y = r.randrange(NP) * PH + r.uniform(-30, 30) if r.random() < 0.6 else r.uniform(0, N)
        s_ = r.uniform(8, 22)
        pts = [(x + math.cos(a_) * s_ * r.uniform(0.5, 1.0), y + math.sin(a_) * s_ * 0.7 * r.uniform(0.5, 1.0))
               for a_ in [k * math.pi / 3 for k in range(6)]]
        chip.poly(pts, 255)
        shad.poly([(px_, py_ + 3) for px_, py_ in pts], 255)
    im = tint_composite(im, shad.done(1.0), (110, 110, 105), 0.6)
    im = tint_composite(im, chip.done(0.8), (205, 203, 195), 0.8)
    # 7) лёгкая крупная неравномерность
    big = noise_layer(8203, 6, N).load()
    px = im.load()
    for y in range(N):
        for x in range(N):
            k = 1.0 + 0.03 * (big[x, y] - 128) / 128.0
            r_, g_, b_ = px[x, y]
            px[x, y] = (min(255, int(r_ * k)), min(255, int(g_ * k)), min(255, int(b_ * k)))
    im = im.filter(ImageFilter.GaussianBlur(0.5))
    p = os.path.join(OUT, 'KH1b_panel_grey_shabby_albedo.png')
    im.save(p)
    return p


# ---------- превью фасадов (как в v01: 5 этажей, 30 м), чистая и обшарпанная
PPM = 24
F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 18)
f = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 14)


def tiled(path, w_px, h_px, wm, hm):
    t = Image.open(path).convert('RGB').resize((int(wm * PPM), int(hm * PPM)), Image.LANCZOS)
    out = Image.new('RGB', (w_px, h_px))
    for x in range(0, w_px, t.width):
        for yy in range(0, h_px, t.height):
            out.paste(t, (x, yy))
    return out


def window(d, x, y, w, h, frame='#E9E7E1', glass='#3E4B55', sash=3):
    d.rectangle((x, y, x + w, y + h), fill=hexc(frame))
    t = 3
    d.rectangle((x + t, y + t, x + w - t, y + h - t), fill=hexc(glass))
    for k in range(1, sash):
        xx = x + w * k // sash
        d.rectangle((xx - 1, y + t, xx + 1, y + h - t), fill=hexc(frame))
    d.rectangle((x + t, y + int(h * 0.3) - 1, x + w - t, y + int(h * 0.3) + 1), fill=hexc(frame))
    d.rectangle((x - 3, y + h, x + w + 3, y + h + 4), fill=hexc('#9A9C98'))   # отлив


def khrushchyovka(wall_path, wm, hm, title, seed, shabby):
    floors, fh = 5, 2.8
    Wm, Hm = 30.0, floors * fh + 0.9
    W, H = int(Wm * PPM), int(Hm * PPM)
    im = Image.new('RGB', (W + 40, H + 60), (200, 214, 222))
    im.paste(tiled(wall_path, W, H, wm, hm), (20, 40))
    r = random.Random(seed)
    ox, oy = 20, 40
    plinth_top = oy + H - int(0.9 * PPM)
    winw, winh = int(1.5 * PPM), int(1.45 * PPM)
    step = int(3.0 * PPM)
    entrances = (2, 7)
    sills, balconies = [], []
    for fl in range(floors):
        yb = plinth_top - int((fl + 1) * fh * PPM)
        for k in range(10):
            x = ox + int(0.75 * PPM) + k * step
            if fl == 0 and k in entrances:
                continue
            if fl >= 1 and k in entrances:
                sills.append((x + 6, yb + int(1.2 * PPM) + int(1.1 * PPM) + 4, winw - 12))
                continue
            sills.append((x, yb + int(0.6 * PPM) + winh + 4, winw))
            if fl >= 1 and k in (0, 4, 5, 9):
                balconies.append((x - int(0.5 * PPM), yb + int(0.6 * PPM) + winh + 6, x + winw + int(0.5 * PPM)))
    if shabby:                                                       # грязь под окнами, балконами, у цоколя и под парапетом
        ov = Image.new('L', im.size, 0)
        od = ImageDraw.Draw(ov)
        rv = Image.new('L', im.size, 0)
        rd = ImageDraw.Draw(rv)
        for x, y, w in sills:
            if r.random() < 0.35:
                continue
            for _ in range(r.randint(1, 2)):
                sx = x + r.uniform(4, w - 4)
                ln = r.uniform(0.3, 1.0) * PPM
                for s in range(6):
                    t0, t1 = s / 6, (s + 1) / 6
                    od.rectangle((sx - 2.5 * (1 - 0.6 * t0), y + ln * t0, sx + 2.5 * (1 - 0.6 * t0), y + ln * t1), fill=int(140 * (1 - 0.8 * t0)))
        for x0, y, x1 in balconies:
            for sx in (x0 + 3, x1 - 3):
                if r.random() < 0.4:
                    continue
                ln = r.uniform(0.8, 1.6) * PPM
                for s in range(6):
                    t0, t1 = s / 6, (s + 1) / 6
                    rd.rectangle((sx - 2, y + ln * t0, sx + 2, y + ln * t1), fill=int(160 * (1 - 0.8 * t0)))
        for xx in range(ox, ox + W, 3):                              # подтёки с парапета
            if r.random() < 0.15:
                ln = r.uniform(0.2, 0.9) * PPM
                od.rectangle((xx, oy + 4, xx + 2, oy + 4 + ln), fill=r.randint(60, 130))
        for yy in range(int(0.7 * PPM)):                             # грязь над цоколем (брызги, сырость)
            od.line((ox, plinth_top - yy, ox + W, plinth_top - yy), fill=int(110 * (1 - yy / (0.7 * PPM))))
        ov = ov.filter(ImageFilter.GaussianBlur(1.6))
        rv = rv.filter(ImageFilter.GaussianBlur(1.4))
        im = tint_composite(im, ov, (92, 94, 90), 0.6)
        im = tint_composite(im, rv, (139, 96, 62), 0.55)
    d = ImageDraw.Draw(im)
    d.rectangle((14, 34, W + 26, 44), fill=hexc('#6F706C'))           # парапет плоской крыши
    d.rectangle((ox, plinth_top, ox + W, oy + H), fill=hexc('#6E6D66' if shabby else '#7D7C75'))   # цоколь
    if shabby:
        for _ in range(10):                                          # отбитая штукатурка цоколя
            x = r.uniform(ox, ox + W - 30)
            d.rectangle((x, plinth_top + r.uniform(3, 10), x + r.uniform(12, 40), plinth_top + r.uniform(12, 20)), fill=hexc('#8D8A80'))
    rr = random.Random(seed + 1)
    for fl in range(floors):
        yb = plinth_top - int((fl + 1) * fh * PPM)
        for k in range(10):
            x = ox + int(0.75 * PPM) + k * step
            if fl == 0 and k in entrances:
                dx = x + winw // 2
                d.rectangle((dx - int(0.6 * PPM), plinth_top - int(2.2 * PPM), dx + int(0.6 * PPM), plinth_top), fill=hexc('#4E4036'))   # дверь подъезда
                d.rectangle((dx - int(1.0 * PPM), plinth_top - int(2.5 * PPM), dx + int(1.0 * PPM), plinth_top - int(2.3 * PPM)), fill=hexc('#8E8D86'))   # козырёк
                continue
            if fl >= 1 and k in entrances:
                window(d, x + 6, yb + int(1.2 * PPM), winw - 12, int(1.1 * PPM), sash=2)
                continue
            window(d, x, yb + int(0.6 * PPM), winw, winh, frame=rr.choice(('#E9E7E1', '#E9E7E1', '#F4F4F2', '#C9B79A')))
            if fl >= 1 and k in (0, 4, 5, 9):
                bx0, bx1 = x - int(0.5 * PPM), x + winw + int(0.5 * PPM)
                by = yb + int(0.6 * PPM) + winh + 6
                if rr.random() < 0.45:
                    d.rectangle((bx0, by - int(1.9 * PPM), bx1, by), fill=hexc(rr.choice(('#EDEBE6', '#B9A786', '#D7D5CE'))))
                    for q in range(4):
                        xx = bx0 + (bx1 - bx0) * (q + 0.1) / 4
                        d.rectangle((xx, by - int(1.75 * PPM), xx + (bx1 - bx0) / 4 - 6, by - int(0.95 * PPM)), fill=hexc('#455661'))
                    d.rectangle((bx0, by - int(0.9 * PPM), bx1, by), fill=hexc(rr.choice(('#9DA3A6', '#B8B1A2', '#7E8C93'))))
                else:
                    d.rectangle((bx0, by - 4, bx1, by), fill=hexc('#8B8A84'))
                    for q in range(0, bx1 - bx0, 5):
                        d.line((bx0 + q, by - int(1.0 * PPM), bx0 + q, by), fill=hexc('#55585A'), width=1)
                    d.line((bx0, by - int(1.0 * PPM), bx1, by - int(1.0 * PPM)), fill=hexc('#55585A'), width=2)
    for xx in (ox + int(6.0 * PPM), ox + int(21.0 * PPM)):             # водосточные трубы
        d.rectangle((xx, 44, xx + 4, plinth_top), fill=hexc('#7E7F7A' if shabby else '#8C8D88'))
    d.text((20, 8), title, font=F, fill=(30, 40, 46))
    return im


kh1b = make_kh1b()
T = 300
f1 = khrushchyovka(KH1, 6.4, 5.6, 'БЫЛО: KH1 чистая', 11, False)
f2 = khrushchyovka(kh1b, TW_M, TH_M, 'СТАЛО: KH1b обшарпанная', 11, True)
W = max(f1.width, 2 * (T + 10) + 2 * T + 10)
H = 46 + T + 50 + f1.height + f2.height + 30
sheet = Image.new('RGB', (W + 20, H), (240, 240, 236))
d = ImageDraw.Draw(sheet)
d.text((10, 10), 'Неблагополучный: одна текстура на все хрущёвки — обшарпанная панель KH1b', font=F, fill=(46, 80, 110))
cards = ((KH1, 'KH1 чистая (было), 6,4 x 5,6 м'), (kh1b, 'KH1b обшарпанная, 12,8 x 11,2 м'))
for i, (p, lab) in enumerate(cards):
    t = Image.open(p).convert('RGB').resize((T, T), Image.LANCZOS)
    sheet.paste(t, (10 + i * (T + 10), 40))
    d.text((10 + i * (T + 10), 40 + T + 4), lab, font=f, fill=(30, 40, 46))
two = Image.new('RGB', (2 * T, T))                                   # тайл 2x1 — проверка шва
tt = Image.open(kh1b).convert('RGB').resize((T, T), Image.LANCZOS)
two.paste(tt, (0, 0))
two.paste(tt, (T, 0))
sheet.paste(two, (10 + 2 * (T + 10), 40))
d.text((10 + 2 * (T + 10), 40 + T + 4), 'KH1b повтор 2 раза — без шва', font=f, fill=(30, 40, 46))
d.text((10, 40 + T + 24), 'У каждой панели своя грязь: пятна сырости, подтёки от швов, заплатки швов (битум и свежий герметик), сколы, ржавчина. '
       'На доме ещё подтёки под окнами и балконами, грязный цоколь.', font=f, fill=(70, 78, 84))
y = 40 + T + 50
sheet.paste(f1, (10, y))
sheet.paste(f2, (10, y + f1.height + 10))
out = os.path.join(HERE, 'SHEET_05c_rough_khrushchyovka_shabby.jpg')
sheet.save(out, quality=88)
print(out, sheet.size, kh1b)
