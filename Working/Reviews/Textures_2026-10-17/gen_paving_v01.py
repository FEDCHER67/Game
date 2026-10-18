"""Свои стилизованные текстуры тротуара и площади (TASK-000810, Вадим): тротуар как в One-Armed Robber (светлые крупные
плиты, тонкие швы, плоский цвет), площадь — модерн (крупный формат, линейные плиты, гранитные полосы, терраццо).
Только albedo, бесшовные, 1024 px; превью сверху (3 x 3 м) и в перспективе. Генерация без numpy (PIL)."""
import os
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'candidates_paving_v01')
os.makedirs(OUT, exist_ok=True)
N = 1024


def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(c, k):
    return tuple(max(0, min(255, int(round(v * k)))) for v in c)


def tile_noise(seed, cells, amp):
    """Бесшовный мягкий шум: маленькая случайная сетка 3x3 раза, увеличение, центр."""
    r = random.Random(seed)
    g = Image.new('L', (cells, cells))
    g.putdata([r.randint(0, 255) for _ in range(cells * cells)])
    big = Image.new('L', (cells * 3, cells * 3))
    for i in range(3):
        for j in range(3):
            big.paste(g, (i * cells, j * cells))
    big = big.resize((N * 3, N * 3), Image.BICUBIC)
    n = big.crop((N, N, 2 * N, 2 * N))
    return n, amp


def apply_noise(im, noise, amp):
    n = noise.load()
    px = im.load()
    for y in range(N):
        for x in range(N):
            k = 1.0 + amp * (n[x, y] - 128) / 128.0
            r_, g_, b_ = px[x, y]
            px[x, y] = (min(255, int(r_ * k)), min(255, int(g_ * k)), min(255, int(b_ * k)))
    return im


def rect_wrap(d, x0, y0, x1, y1, fill):
    """Прямоугольник с переносом через край тайла (бесшовность)."""
    for ox in (-N, 0, N):
        for oy in (-N, 0, N):
            d.rectangle((x0 + ox, y0 + oy, x1 + ox, y1 + oy), fill=fill)


def slabs(base, slab_w, slab_h, seam, seam_k, var, seed, offset_rows=0.0, colors=None):
    """Сетка плит (в пикселях), тон каждой плиты чуть свой, тонкие швы чуть темнее."""
    r = random.Random(seed)
    im = Image.new('RGB', (N, N), shade(base, seam_k))
    d = ImageDraw.Draw(im)
    rows = round(N / slab_h)
    cols = round(N / slab_w)
    for j in range(rows):
        off = (j % 2) * offset_rows * slab_w
        for i in range(cols):
            c = r.choice(colors) if colors else base
            c = shade(c, 1.0 + r.uniform(-var, var))
            x0 = int(i * slab_w + off)
            y0 = int(j * slab_h)
            rect_wrap(d, x0 + seam // 2, y0 + seam // 2, x0 + int(slab_w) - (seam - seam // 2) - 1, y0 + int(slab_h) - (seam - seam // 2) - 1, c)
    return im


def planks(colors, row_h, lengths_m, px_per_m, seam, seam_k, seed):
    """Линейные плиты (модерн): ряды одинаковой ширины, длины случайные, швы рядов не совпадают."""
    r = random.Random(seed)
    im = Image.new('RGB', (N, N), shade(colors[0], seam_k))
    d = ImageDraw.Draw(im)
    rows = round(N / row_h)
    for j in range(rows):
        x = r.randint(0, N)                      # случайный сдвиг ряда, с переносом
        total = 0
        while total < N:
            L = int(r.choice(lengths_m) * px_per_m)
            if N - total < 0.5 * px_per_m:
                L = N - total
            elif N - total - L < 0.5 * px_per_m:
                L = N - total
            c = shade(r.choice(colors), 1.0 + r.uniform(-0.02, 0.02))
            x0 = (x + total) % N
            y0 = int(j * row_h)
            rect_wrap(d, x0 + seam // 2, y0 + seam // 2, x0 + L - (seam - seam // 2) - 1, y0 + int(row_h) - (seam - seam // 2) - 1, c)
            total += L
    return im


def speckle(im, seed, count, colors, rmin, rmax):
    r = random.Random(seed)
    d = ImageDraw.Draw(im)
    for _ in range(count):
        x, y = r.randrange(N), r.randrange(N)
        rr = r.uniform(rmin, rmax)
        c = r.choice(colors)
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                d.ellipse((x - rr + ox, y - rr + oy, x + rr + ox, y + rr + oy), fill=c)
    return im


CANDS = []   # (код, название, файл, метров на тайл)


def save(code, name, im, metres):
    path = os.path.join(OUT, '%s_%s_albedo.png' % (code, name))
    im.save(path)
    CANDS.append((code, name, path, metres))


# --- тротуар как в One-Armed Robber: светлые крупные плиты, тонкие швы, почти плоский цвет (тайл 3 м)
ppm = N / 3.0
for code, name, base, slab_m, seed in (('S1', 'sidewalk_oar_1p5m', '#D3D5D7', (1.5, 1.5), 11),
                                      ('S2', 'sidewalk_oar_1m', '#D1D3D4', (1.0, 1.0), 12),
                                      ('S3', 'sidewalk_oar_warm_1p5m', '#D6D3CD', (1.5, 1.5), 13)):
    im = slabs(hexc(base), slab_m[0] * ppm, slab_m[1] * ppm, 5, 0.86, 0.018, seed)
    n, a = tile_noise(seed + 100, 24, 0.008)
    save(code, name, apply_noise(im, n, a).filter(ImageFilter.GaussianBlur(0.6)), 3.0)
im = slabs(hexc('#D2D4D6'), 2.0 * (N / 4.0), 1.0 * (N / 4.0), 5, 0.86, 0.018, 14, offset_rows=0.5)   # тайл 4 м: плиты 2 x 1 м вразбежку
n, a = tile_noise(114, 24, 0.008)
save('S4', 'sidewalk_oar_2x1m', apply_noise(im, n, a).filter(ImageFilter.GaussianBlur(0.6)), 4.0)

# --- площадь, модерн
ppm = N / 2.4                                                               # тайл 2,4 м
im = slabs(hexc('#D9D7D1'), 1.2 * ppm, 0.6 * ppm, 4, 0.88, 0.015, 21, offset_rows=0.5, colors=[hexc('#D9D7D1'), hexc('#CDCBC5')])
n, a = tile_noise(121, 24, 0.006)
save('M1', 'plaza_large_format_60x120', apply_noise(im, n, a).filter(ImageFilter.GaussianBlur(0.5)), 2.4)
im = planks([hexc('#D8D8D4'), hexc('#CBCCC9'), hexc('#BEC0BD')], N / 8.0, (0.6, 0.9, 1.2, 1.5), ppm, 4, 0.86, 22)
n, a = tile_noise(122, 24, 0.006)
save('M2', 'plaza_linear_planks', apply_noise(im, n, a).filter(ImageFilter.GaussianBlur(0.5)), 2.4)
ppm = N / 4.0                                                               # тайл 4 м: плиты 1 x 1 м + гранитная полоса 20 см через 4 м
im = slabs(hexc('#DAD7CF'), 1.0 * ppm, 1.0 * ppm, 4, 0.88, 0.015, 23)
d = ImageDraw.Draw(im)
band = int(0.2 * ppm)
gran = hexc('#5A5E61')
d.rectangle((0, 0, N, band), fill=gran)
d.rectangle((0, 0, band, N), fill=gran)
n, a = tile_noise(123, 24, 0.006)
save('M3', 'plaza_1m_granite_bands', apply_noise(im, n, a).filter(ImageFilter.GaussianBlur(0.5)), 4.0)
ppm = N / 3.0                                                               # тайл 3 м: терраццо 1,5 м
im = slabs(hexc('#DEDBD3'), 1.5 * ppm, 1.5 * ppm, 4, 0.9, 0.01, 24)
im = speckle(im, 224, 5200, [hexc('#B9B6AE'), hexc('#EFEDE8'), hexc('#A7A9A6'), hexc('#C9B9A0')], 0.9, 2.2)
n, a = tile_noise(124, 24, 0.005)
save('M4', 'plaza_terrazzo_1p5m', apply_noise(im, n, a).filter(ImageFilter.GaussianBlur(0.5)), 3.0)


# --- превью: сверху 3 x 3 м и в перспективе (полоса 5,5 м x 16 м, глаз ~1,7 м)
def solve(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r_: abs(M[r_][c]))
        M[c], M[p] = M[p], M[c]
        for r_ in range(n):
            if r_ != c:
                k = M[r_][c] / M[c][c]
                M[r_] = [a - k * b_ for a, b_ in zip(M[r_], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def persp_coeffs(out_pts, in_pts):
    A, b = [], []
    for (x, y), (u, v) in zip(out_pts, in_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return solve(A, b)


def tiled(path, metres, w_m, h_m, ppm_prev):
    t = Image.open(path).convert('RGB')
    tp = int(metres * ppm_prev)
    t = t.resize((tp, tp), Image.LANCZOS)
    W, H = int(w_m * ppm_prev), int(h_m * ppm_prev)
    im = Image.new('RGB', (W, H))
    for x in range(0, W, tp):
        for y in range(0, H, tp):
            im.paste(t, (x, y))
    return im


F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 17)
f = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 14)
TOP, PW, PH = 300, 640, 300
ref = os.path.join(r'C:\Users\chern_0eqkb03\Desktop\GAME\ArtSource\References\Map\World_v11\References', 'REF_downtown_city_04.webp')
rows = [('OAR', 'референс One-Armed Robber (тротуар)', None)] + [(c, n, p) for c, n, p, m in CANDS]
sheet = Image.new('RGB', (230 + TOP + 12 + PW + 10, len(rows) * (PH + 34) + 20), (240, 240, 236))
d = ImageDraw.Draw(sheet)
y = 10
for code, name, path in rows:
    if path is None:
        r_ = Image.open(ref).convert('RGB')
        Wr, Hr = r_.size
        crop = r_.crop((0, int(Hr * 0.55), int(Wr * 0.62), Hr)).resize((TOP + 12 + PW, PH))
        sheet.paste(crop, (230, y))
        d.text((10, y + PH // 2 - 20), 'OAR', font=F, fill=(30, 40, 46))
        d.text((10, y + PH // 2 + 2), 'референс тротуара', font=f, fill=(30, 40, 46))
        y += PH + 34
        continue
    metres = next(m for c, n, p, m in CANDS if c == code)
    top = tiled(path, metres, 3.0, 3.0, TOP / 3.0)
    sheet.paste(top, (230, y))
    src = tiled(path, metres, 5.5, 16.0, 120)
    sw, sh = src.size
    hz = 46
    out_pts = [(0, PH), (PW, PH), (PW * 0.62, hz), (PW * 0.38, hz)]
    in_pts = [(0, sh), (sw, sh), (sw, 0), (0, 0)]
    co = persp_coeffs(out_pts, in_pts)
    pv = src.transform((PW, PH), Image.PERSPECTIVE, co, Image.BICUBIC)
    mask = Image.new('L', (PW, PH), 0)
    ImageDraw.Draw(mask).polygon(out_pts, fill=255)
    bg = Image.new('RGB', (PW, PH), (196, 214, 226))
    ImageDraw.Draw(bg).rectangle((0, hz, PW, PH), fill=(108, 112, 116))
    bg.paste(pv, (0, 0), mask)
    sheet.paste(bg, (230 + TOP + 12, y))
    d.text((10, y + PH // 2 - 20), code, font=F, fill=(30, 40, 46))
    d.text((10, y + PH // 2 + 2), name.replace('_', ' '), font=f, fill=(30, 40, 46))
    d.text((230, y + PH + 3), 'сверху 3 x 3 м', font=f, fill=(30, 40, 46))
    d.text((230 + TOP + 12, y + PH + 3), 'вид с тротуара', font=f, fill=(30, 40, 46))
    y += PH + 34
out = os.path.join(HERE, 'SHEET_02b_sidewalk_plaza_new.jpg')
sheet.save(out, quality=88)
print(out, sheet.size, len(CANDS))
