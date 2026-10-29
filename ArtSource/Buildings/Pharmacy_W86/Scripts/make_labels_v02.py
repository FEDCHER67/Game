"""Pharmacy_W86 v02 - label / price-card / package texture atlas (system Python + Pillow, not Blender).

Run:  python make_labels_v02.py [--force]
Out:  ../Pharmacy_labels_v02.png          2048 x 2048 sRGB atlas (MAT_PH_labels)
      ../Pharmacy_labels_v02_regions.json  region name -> UV rect [u0, v0, u1, v1] (Blender/Unity UV, origin bottom-left)

All readable text is English. Price cards use the G48 catalog prices (Assets/OnlyVolunteers/Buyers/Data/Economy_v01.json).
The storefront carries no words: the window poster / cross art regions have no text.
v02 (Fedya 29.10): the shop-window information sheet reads exactly "Open daily 8:00–20:00" (en dash) (no days off, closed at night);
every other region is pixel-identical to v01 (same layout, same regions).
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FORCE = '--force' in sys.argv
OUT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PNG = os.path.join(OUT, 'Pharmacy_labels_v02.png')
JSN = os.path.join(OUT, 'Pharmacy_labels_v02_regions.json')
S = 2048
FONT_B = 'C:/Windows/Fonts/arialbd.ttf'
FONT_R = 'C:/Windows/Fonts/arial.ttf'

# catalog key, line 1, price text, unit suffix
PRICE_CARDS = [
    ('syringe_blood', 'Blood Syringe', '$2', 'each'),
    ('syringe_anaesthesia', 'Empty Anesthetic Syringe', '$2', 'each'),
    ('zip_tie', 'Cable Tie', '$5', 'each'),
    ('zip_tie_pack_4', 'Cable Ties \u2014 Pack of 4', '$20', '/ pack'),
    ('blood_bag_empty', 'Empty Blood Bag', '$5', 'each'),
    ('organ_bag', 'Organ Bag', '$10', 'each'),
    ('body_bag', 'Body Bag', '$5', 'each'),
    ('trash_bag', 'Trash Bag', '$5', 'each'),
    ('anaesthesia_basic', 'Basic Anesthetic', '$200', '/ vial'),
]

INK = (30, 43, 47)
GREEN = (58, 132, 84)
TEAL = (63, 140, 143)
TEAL_D = (47, 111, 115)
RED = (176, 52, 44)
WHITE = (246, 244, 238)
PAPER = (251, 250, 246)
KRAFT = (180, 138, 90)
SWATCHES = [
    ('white', (244, 242, 236)), ('teal', TEAL), ('orange', (217, 119, 58)), ('green', (76, 140, 90)),
    ('blue', (62, 110, 158)), ('cream', (232, 220, 192)), ('dark', (43, 45, 48)), ('kraft', KRAFT),
    ('red', (184, 58, 50)), ('lightblue', (156, 195, 213)), ('amber', (122, 74, 34)), ('clear', (221, 232, 234)),
    ('black_bag', (26, 27, 29)), ('grey', (138, 144, 150)), ('tape', (201, 168, 119)), ('paper', PAPER),
    ('teal_dark', TEAL_D), ('kraft_dark', (150, 112, 70)), ('screen', (22, 34, 44)), ('steel', (170, 176, 182)),
    ('plunger_red', (190, 60, 52)), ('plunger_blue', (60, 110, 190)), ('bag_white', (236, 238, 240)), ('zip_blue', (70, 120, 200)),
]

regions = {}


def reg(name, x0, y0, x1, y1, inset=3):
    """Pixel rect (top-left origin) -> UV rect (bottom-left origin), inset to avoid mip bleeding."""
    regions[name] = [round((x0 + inset) / S, 6), round(1 - (y1 - inset) / S, 6),
                     round((x1 - inset) / S, 6), round(1 - (y0 + inset) / S, 6)]


def font(path, size):
    return ImageFont.truetype(path, size)


def fit(draw, text, path, size, maxw):
    while size > 10:
        f = font(path, size)
        if draw.textlength(text, font=f) <= maxw:
            return f
        size -= 1
    return font(path, 10)


def tcenter(draw, cx, y, text, f, fill):
    w = draw.textlength(text, font=f)
    draw.text((cx - w / 2, y), text, font=f, fill=fill)


def cross(draw, cx, cy, size, fill, arm=0.34):
    a = size * arm / 2
    h = size / 2
    draw.rectangle([cx - a, cy - h, cx + a, cy + h], fill=fill)
    draw.rectangle([cx - h, cy - a, cx + h, cy + a], fill=fill)


def price_card(im, x0, y0, key, name, price, unit):
    d = ImageDraw.Draw(im)
    w, h = 512, 256
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(206, 214, 210))
    d.rounded_rectangle([x0 + 6, y0 + 6, x0 + w - 7, y0 + h - 7], radius=14, fill=PAPER, outline=GREEN, width=6)
    d.rectangle([x0 + 12, y0 + 12, x0 + w - 13, y0 + 40], fill=GREEN)
    cross(d, x0 + 34, y0 + 26, 22, PAPER)
    # product name: one line if it fits at 46 px, else two lines
    maxw = w - 52
    f = font(FONT_B, 46)
    if d.textlength(name, font=f) <= maxw:
        d.text((x0 + 26, y0 + 56), name, font=f, fill=INK)
    else:
        words = name.split(' ')
        words = [w for w in words]
        merged = []
        for wd in words:
            if wd == '—' and merged:
                merged[-1] += ' ' + wd
            else:
                merged.append(wd)
        words = merged
        best = None
        for i in range(1, len(words)):
            a, b = ' '.join(words[:i]), ' '.join(words[i:])
            m = max(d.textlength(a, font=font(FONT_B, 40)), d.textlength(b, font=font(FONT_B, 40)))
            if best is None or m < best[0]:
                best = (m, a, b)
        _, a, b = best
        f2 = fit(d, a if d.textlength(a, font=font(FONT_B, 40)) > d.textlength(b, font=font(FONT_B, 40)) else b, FONT_B, 40, maxw)
        d.text((x0 + 26, y0 + 48), a, font=f2, fill=INK)
        d.text((x0 + 26, y0 + 48 + f2.size + 4), b, font=f2, fill=INK)
    fp = font(FONT_B, 92)
    pw = d.textlength(price, font=fp)
    py = y0 + h - 22 - 92
    d.text((x0 + 26, py - 6), price, font=fp, fill=GREEN)
    fu = font(FONT_B, 40)
    d.text((x0 + 26 + pw + 14, py + 40), unit, font=fu, fill=INK)
    reg('card_' + key, x0, y0, x0 + w, y0 + h)


def staff_only(im, x0, y0, name):
    d = ImageDraw.Draw(im)
    w, h = 512, 256
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(200, 200, 196))
    d.rounded_rectangle([x0 + 6, y0 + 6, x0 + w - 7, y0 + h - 7], radius=12, fill=PAPER, outline=RED, width=10)
    # no-entry roundel
    cx, cy, r = x0 + 92, y0 + 128, 62
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED)
    d.rectangle([cx - 42, cy - 12, cx + 42, cy + 12], fill=PAPER)
    f = font(FONT_B, 72)
    d.text((x0 + 176, y0 + 50), 'STAFF', font=f, fill=RED)
    d.text((x0 + 176, y0 + 128), 'ONLY', font=f, fill=RED)
    reg(name, x0, y0, x0 + w, y0 + h)


def package(im, x0, y0, name, sub, band, idx):
    d = ImageDraw.Draw(im)
    w = h = 256
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=WHITE)
    d.rectangle([x0, y0 + 150, x0 + w - 1, y0 + 196], fill=band)
    d.rectangle([x0, y0 + 202, x0 + w - 1, y0 + 208], fill=band)
    f = fit(d, name, FONT_B, 40, w - 36)
    d.text((x0 + 18, y0 + 34), name, font=f, fill=INK)
    d.text((x0 + 18, y0 + 34 + f.size + 10), sub, font=font(FONT_R, 24), fill=(80, 90, 94))
    cross(d, x0 + w - 34, y0 + 173, 30, WHITE)
    reg('pkg_%d' % idx, x0, y0, x0 + w, y0 + h)


def bottle_label(im, x0, y0, name, band, idx):
    d = ImageDraw.Draw(im)
    w = h = 256
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=WHITE)
    d.rectangle([x0, y0 + 30, x0 + w - 1, y0 + 70], fill=band)
    f = fit(d, name, FONT_B, 38, w - 30)
    tcenter(d, x0 + w / 2, y0 + 110, name, f, INK)
    for k in range(3):
        d.rectangle([x0 + 40, y0 + 170 + k * 22, x0 + w - 40 - k * 30, y0 + 178 + k * 22], fill=(170, 176, 180))
    reg('bottle_%d' % idx, x0, y0, x0 + w, y0 + h)


def simple_label(im, x0, y0, rname, title, sub, band, bg=WHITE, ink=INK, w=256, h=256):
    d = ImageDraw.Draw(im)
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=bg)
    d.rectangle([x0, y0, x0 + w - 1, y0 + 46], fill=band)
    f = fit(d, title, FONT_B, 40, w - 30)
    tcenter(d, x0 + w / 2, y0 + 80, title, f, ink)
    if sub:
        fs = fit(d, sub, FONT_R, 30, w - 30)
        tcenter(d, x0 + w / 2, y0 + 80 + f.size + 18, sub, fs, ink)
    reg(rname, x0, y0, x0 + w, y0 + h)


def carton_side(im, x0, y0):
    d = ImageDraw.Draw(im)
    w, h = 512, 256
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=KRAFT)
    # faint fibre streaks
    for k in range(0, h, 9):
        d.line([x0, y0 + k, x0 + w, y0 + k + 3], fill=(172, 131, 84), width=1)
    ink = (52, 44, 38)
    f = font(FONT_B, 40)
    d.text((x0 + 30, y0 + 40), 'MEDICAL SUPPLIES', font=f, fill=ink)
    d.text((x0 + 30, y0 + 92), 'KEEP DRY  \u2022  THIS SIDE UP', font=font(FONT_R, 28), fill=ink)
    for k in range(2):
        ax = x0 + 360 + k * 60
        d.polygon([(ax, y0 + 160), (ax + 22, y0 + 190), (ax - 22, y0 + 190)], fill=ink)
        d.rectangle([ax - 8, y0 + 190, ax + 8, y0 + 228], fill=ink)
    d.rectangle([x0 + 30, y0 + 170, x0 + 290, y0 + 222], outline=ink, width=3)
    d.text((x0 + 44, y0 + 180), 'LOT 2026-10', font=font(FONT_R, 28), fill=ink)
    reg('carton_side', x0, y0, x0 + w, y0 + h)


def carton_top(im, x0, y0):
    d = ImageDraw.Draw(im)
    w = h = 256
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(176, 134, 86))
    d.rectangle([x0, y0 + 126, x0 + w - 1, y0 + 130], fill=(140, 104, 64))   # flap seam
    d.rectangle([x0, y0 + 100, x0 + w - 1, y0 + 156], fill=(204, 174, 126))  # tape
    d.line([x0, y0 + 100, x0 + w, y0 + 100], fill=(186, 152, 104), width=2)
    d.line([x0, y0 + 156, x0 + w, y0 + 156], fill=(186, 152, 104), width=2)
    reg('carton_top', x0, y0, x0 + w, y0 + h)


def cross_poster(im, x0, y0, rname, frame=TEAL):
    d = ImageDraw.Draw(im)
    w = h = 512
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=frame)
    d.rectangle([x0 + 34, y0 + 34, x0 + w - 35, y0 + h - 35], fill=(240, 234, 216))
    cross(d, x0 + w / 2, y0 + h / 2, 300, (52, 150, 96), arm=0.36)
    reg(rname, x0, y0, x0 + w, y0 + h)


def info_sheet(im, x0, y0):
    d = ImageDraw.Draw(im)
    w = h = 512
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(220, 214, 200))
    d.rectangle([x0 + 18, y0 + 18, x0 + w - 19, y0 + h - 19], fill=PAPER)
    d.rectangle([x0 + 18, y0 + 18, x0 + w - 19, y0 + 96], fill=TEAL)
    tcenter(d, x0 + w / 2, y0 + 34, 'INFORMATION', font(FONT_B, 48), PAPER)
    f = font(FONT_B, 34)
    fr = font(FONT_R, 30)
    d.text((x0 + 50, y0 + 122), 'Opening hours', font=f, fill=INK)
    t = 'Open daily 8:00–20:00'
    tcenter(d, x0 + w / 2, y0 + 196, t, fit(d, t, FONT_B, 56, w - 70), GREEN)
    tcenter(d, x0 + w / 2, y0 + 300, 'No days off • closed at night', font(FONT_R, 30), INK)
    tcenter(d, x0 + w / 2, y0 + 352, 'Please ask at the counter.', font(FONT_R, 30), INK)
    reg('info_sheet', x0, y0, x0 + w, y0 + h)


def register_screen(im, x0, y0):
    d = ImageDraw.Draw(im)
    w, h = 512, 256
    d.rectangle([x0, y0, x0 + w - 1, y0 + h - 1], fill=(22, 34, 44))
    d.rectangle([x0 + 16, y0 + 16, x0 + w - 17, y0 + 60], fill=(40, 70, 80))
    d.text((x0 + 30, y0 + 22), 'SALE', font=font(FONT_B, 32), fill=(200, 236, 220))
    d.text((x0 + 30, y0 + 110), 'TOTAL', font=font(FONT_B, 44), fill=(150, 220, 170))
    d.text((x0 + 300, y0 + 104), '$0.00', font=font(FONT_B, 56), fill=(150, 220, 170))
    reg('register_screen', x0, y0, x0 + w, y0 + h)


def swatches(im, x0, y0):
    d = ImageDraw.Draw(im)
    for i, (n, c) in enumerate(SWATCHES):
        sx = x0 + (i % 8) * 128
        sy = y0 + (i // 8) * 128
        d.rectangle([sx, sy, sx + 127, sy + 127], fill=c)
        reg('sw_' + n, sx, sy, sx + 128, sy + 128, inset=40)


def main():
    if os.path.exists(PNG) and not FORCE:
        raise SystemExit('refusing to overwrite ' + PNG)
    im = Image.new('RGB', (S, S), (128, 128, 128))
    for i, (key, name, price, unit) in enumerate(PRICE_CARDS):
        price_card(im, (i % 4) * 512, (i // 4) * 256, key, name, price, unit)
    staff_only(im, 512, 512, 'staff_only')
    register_screen(im, 1024, 512)
    pk = [('VITAMIN C', '30 tablets', TEAL), ('PAIN RELIEF', '20 tablets', (217, 119, 58)),
          ('COLD & FLU', '10 sachets', (62, 110, 158)), ('ANTISEPTIC', '100 mL', (76, 140, 90)),
          ('GAUZE PADS', '10 x 10 cm', TEAL_D), ('BANDAGES', 'elastic, 4 m', (217, 119, 58)),
          ('SALINE', '0.9% \u2022 250 mL', (62, 110, 158)), ('ALLERGY', '14 tablets', (76, 140, 90))]
    for i, (n, s, b) in enumerate(pk):
        package(im, i * 256, 768, n, s, b, i)
    bl = [('COUGH SYRUP', (217, 119, 58)), ('IODINE', (120, 70, 40)), ('PEROXIDE', (62, 110, 158)), ('VITAMINS', (76, 140, 90))]
    for i, (n, b) in enumerate(bl):
        bottle_label(im, i * 256, 1024, n, b, i)
    simple_label(im, 1024, 1024, 'lbl_syringe_blood', 'STERILE', '5 mL syringe', (184, 58, 50))
    simple_label(im, 1280, 1024, 'lbl_syringe_anaesthesia', 'STERILE', '10 mL syringe', (60, 110, 190))
    simple_label(im, 1536, 1024, 'lbl_vial', 'ANESTHETIC', 'single vial', GREEN)
    simple_label(im, 1792, 1024, 'lbl_cable_ties', 'CABLE TIES', '4 PCS', (43, 45, 48))
    carton_side(im, 0, 1280)
    carton_top(im, 512, 1280)
    simple_label(im, 768, 1280, 'lbl_blood_bag', 'BLOOD BAG', 'empty \u2022 450 mL', (184, 58, 50))
    simple_label(im, 1024, 1280, 'lbl_trash_bag', 'TRASH BAGS', 'heavy duty', (43, 45, 48), bg=(60, 62, 66), ink=(235, 235, 230))
    simple_label(im, 1280, 1280, 'lbl_organ_bag', 'ZIP SEAL', 'leak-proof', (70, 120, 200))
    simple_label(im, 1536, 1280, 'lbl_gloves', 'GLOVES', 'nitrile \u2022 M', (62, 110, 158))
    simple_label(im, 1792, 1280, 'lbl_body_bag', 'HEAVY DUTY', '', (26, 27, 29), bg=(36, 37, 40), ink=(220, 220, 214))
    cross_poster(im, 0, 1536, 'poster_cross')
    info_sheet(im, 512, 1536)
    swatches(im, 1024, 1536)
    im.save(PNG)
    with open(JSN, 'w', encoding='utf-8') as f:
        json.dump(dict(atlas='Pharmacy_labels_v02.png', size=S, uv_origin='bottom-left',
                       price_cards=[dict(catalog_key=k, label=n, price=p, unit=u, region='card_' + k) for k, n, p, u in PRICE_CARDS],
                       regions=regions), f, indent=1)
    print('wrote', PNG, len(regions), 'regions')


if __name__ == '__main__':
    main()
