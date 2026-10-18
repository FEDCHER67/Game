"""Асфальт темнее (TASK-000811, Вадим): A-5 (SK 2a v07) как есть, −12 %, −22 %; превью улицы как в One-Armed Robber —
тротуары S1 по 5,5 м, светлый бордюр, проезжая часть 11 м с осевой прерывистой. Варианты асфальта — albedo 1024 рядом."""
import os
from PIL import Image, ImageDraw, ImageEnhance, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = r'C:\Users\chern_0eqkb03\Desktop\GAME\Assets\OnlyVolunteers\Art\StyleKit_v3\Textures\2a_asphalt\2a_asphalt_v07_albedo.png'
SW = os.path.join(HERE, 'candidates_paving_v01', 'S1_sidewalk_oar_1p5m_albedo.png')
OUT = os.path.join(HERE, 'candidates_asphalt_v01')
os.makedirs(OUT, exist_ok=True)
base = Image.open(A).convert('RGB')
VAR = [('A5', 'как сейчас', base)]
for code, k in (('A5d12', 0.88), ('A5d22', 0.78)):
    v = ImageEnhance.Brightness(base).enhance(k)
    v.save(os.path.join(OUT, '2a_asphalt_v07_%s_albedo.png' % code))
    VAR.append((code, 'темнее на %d %%' % round((1 - k) * 100), v))


def solve(Am, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(Am)]
    for c in range(n):
        p = max(range(c, n), key=lambda r_: abs(M[r_][c]))
        M[c], M[p] = M[p], M[c]
        for r_ in range(n):
            if r_ != c:
                k = M[r_][c] / M[c][c]
                M[r_] = [a - k * b_ for a, b_ in zip(M[r_], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]


def persp(out_pts, in_pts):
    Am, b = [], []
    for (x, y), (u, v) in zip(out_pts, in_pts):
        Am.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        Am.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return solve(Am, b)


def tiled(img, metres, w_px, h_px, ppm):
    tp = int(metres * ppm)
    t = img.resize((tp, tp), Image.LANCZOS)
    out = Image.new('RGB', (w_px, h_px))
    for x in range(0, w_px, tp):
        for y in range(0, h_px, tp):
            out.paste(t, (x, y))
    return out


PPM = 40
Wm, Lm = 22.0, 60.0
sw_img = Image.open(SW).convert('RGB')
F = ImageFont.truetype(r'C:\Windows\Fonts\arialbd.ttf', 18)
f = ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf', 15)
PW, PH, HZ = 900, 380, 70
sheet = Image.new('RGB', (PW + 260, len(VAR) * (PH + 36) + 16), (240, 240, 236))
d = ImageDraw.Draw(sheet)
y = 8
for code, name, asph in VAR:
    W, H = int(Wm * PPM), int(Lm * PPM)
    src = Image.new('RGB', (W, H))
    sw_t = tiled(sw_img, 3.0, int(5.5 * PPM), H, PPM)
    src.paste(sw_t, (0, 0))
    src.paste(sw_t, (W - int(5.5 * PPM), 0))
    road = tiled(asph, 4.0, int(11 * PPM), H, PPM)
    src.paste(road, (int(5.5 * PPM), 0))
    ds = ImageDraw.Draw(src)
    for xc in (5.5, 16.5):                                          # светлый бордюр 25 см
        ds.rectangle((int((xc - 0.125) * PPM), 0, int((xc + 0.125) * PPM), H), fill=(214, 214, 209))
    for yy in range(0, H, int(9 * PPM)):                            # осевая прерывистая 3 м через 6 м
        ds.rectangle((int(10.92 * PPM), yy, int(11.08 * PPM), yy + int(3 * PPM)), fill=(236, 236, 230))
    out_pts = [(0, PH), (PW, PH), (PW * 0.56, HZ), (PW * 0.44, HZ)]
    co = persp(out_pts, [(0, H), (W, H), (W, 0), (0, 0)])
    pv = src.transform((PW, PH), Image.PERSPECTIVE, co, Image.BICUBIC)
    mask = Image.new('L', (PW, PH), 0)
    ImageDraw.Draw(mask).polygon(out_pts, fill=255)
    bg = Image.new('RGB', (PW, PH), (200, 218, 230))
    ImageDraw.Draw(bg).rectangle((0, HZ, PW, PH), fill=(170, 160, 150))
    bg.paste(pv, (0, 0), mask)
    sheet.paste(bg, (250, y))
    d.text((12, y + PH // 2 - 22), code, font=F, fill=(30, 40, 46))
    d.text((12, y + PH // 2 + 2), name, font=f, fill=(30, 40, 46))
    sheet.paste(asph.resize((120, 120)), (12, y + PH // 2 + 30))
    y += PH + 36
out = os.path.join(HERE, 'SHEET_02c_asphalt_darker_street.jpg')
sheet.save(out, quality=88)
print(out)
