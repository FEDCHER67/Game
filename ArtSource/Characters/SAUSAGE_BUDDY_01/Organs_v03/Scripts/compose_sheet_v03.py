"""Compose Working/Reviews/Operations/organs_v03/organs_v03_sheet.png from the review tiles (system Python + Pillow).

python compose_sheet_v03.py
Inputs: Working/Reviews/Operations/organs_v03/tiles/*.png (render_review_v03.py), the blood bag v05 and syringe v02 previews,
Organs_v03/organs_v03_build.json, Patient_v03/ORGANS_LAYOUT_v03.json.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(r"C:/Dev/Game")
REV = REPO / "Working/Reviews/Operations/organs_v03"
TILES = REV / "tiles"
OUT = REV / "organs_v03_sheet.png"
BAG = REPO / "ArtSource/Props/BLOOD-BAG-ASTRA-001/v05/Previews"
SYR = REPO / "ArtSource/Props/SYRINGE-ASTRA-001/v02/Previews"
ORGB = json.loads((REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03/organs_v03_build.json").read_text(encoding="utf-8"))
LAYOUT = json.loads((REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v03/ORGANS_LAYOUT_v03.json").read_text(encoding="utf-8"))
BAGJ = json.loads((REPO / "ArtSource/Props/BLOOD-BAG-ASTRA-001/v05/blood_bag_v05_validation.json").read_text(encoding="utf-8"))
SYRJ = json.loads((REPO / "ArtSource/Props/SYRINGE-ASTRA-001/v02/syringe_v02_validation.json").read_text(encoding="utf-8"))

W = 2400
PAD = 14
BG = (31, 33, 38)
HEAD = (60, 140, 170)
RED = (196, 70, 60)
GREEN = (70, 160, 95)
F = "C:/Windows/Fonts/"
font_t = ImageFont.truetype(F + "segoeuib.ttf" if Path(F + "segoeuib.ttf").exists() else F + "arialbd.ttf", 40)
font_h = ImageFont.truetype(F + "arialbd.ttf", 22)
font_s = ImageFont.truetype(F + "arial.ttf", 20)
font_l = ImageFont.truetype(F + "arialbd.ttf", 19)
font_big = ImageFont.truetype(F + "arialbd.ttf", 60)


def tile(img, w, h):
    """Fit an image into w x h (cover-crop to the centre)."""
    r = max(w / img.width, h / img.height)
    im = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x0, y0 = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x0, y0, x0 + w, y0 + h))


def row(sheet, d, y, items, h, header_h=34):
    """items: (image, title, colour). Equal widths."""
    n = len(items)
    w = (W - PAD * (n + 1)) // n
    for k, (img, title, col) in enumerate(items):
        x = PAD + k * (w + PAD)
        d.rectangle((x, y, x + w, y + header_h), fill=col)
        d.text((x + 10, y + 5), title, font=font_h, fill=(255, 255, 255))
        sheet.paste(tile(img, w, h), (x, y + header_h))
    return y + header_h + h + PAD


def load(p):
    return Image.open(p).convert("RGB")


def strip(paths, labels, crop=None):
    ims = [load(p) for p in paths]
    if crop:
        ims = [i.crop(crop) for i in ims]
    h = min(i.height for i in ims)
    ims = [i.resize((round(i.width * h / i.height), h)) for i in ims]
    out = Image.new("RGB", (sum(i.width for i in ims), h), BG)
    x = 0
    dd = ImageDraw.Draw(out)
    for i, lab in zip(ims, labels):
        out.paste(i, (x, 0))
        dd.rectangle((x + 14, 14, x + 230, 92), fill=(20, 20, 24))
        dd.text((x + 26, 18), lab, font=font_big, fill=(255, 255, 255))
        x += i.width
    return out


def lineup():
    img = load(TILES / "10_lineup.png")
    lay = json.loads((TILES / "10_lineup_layout.json").read_text())
    ow, cx = lay["ortho_width_m"], lay["centre_x"]
    rx, ry = lay["res"]
    oh = ow * ry / rx
    ztop = 0.085 + oh / 2
    d = ImageDraw.Draw(img)
    names = {"ORGAN_HEART": "HEART", "ORGAN_LUNG_R": "LUNG R", "ORGAN_LUNG_L": "LUNG L", "ORGAN_LIVER": "LIVER",
             "ORGAN_KIDNEY_R": "KIDNEY R", "ORGAN_KIDNEY_L": "KIDNEY L"}
    for n, p in lay["organs"].items():
        s = ORGB["objects"][n]["size_m_xyz"]
        x = (p["x_left"] - (cx - ow / 2)) / ow * rx
        y = (ztop - (p["height"] + 0.012)) / oh * ry
        d.text((x, y - 44), names[n], font=font_l, fill=(255, 255, 255))
        d.text((x, y - 22), f"{s[0]*100:.1f} x {s[1]*100:.1f} x {s[2]*100:.1f} cm", font=font_s, fill=(200, 205, 210))
    bx = (-0.36 + 0.102 - (cx - ow / 2)) / ow * rx
    by = (ztop + 0.004) / oh * ry
    d.text((bx, by - 22), "10 cm", font=font_l, fill=(255, 255, 255))
    return img


def main():
    sheet = Image.new("RGB", (W, 6000), BG)
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 10), "VOLUNTEERS ONLY - organs v03: chest, lowered liver/kidneys, closed back, real-fill blood bag + syringe",
           font=font_t, fill=(240, 240, 240))
    d.text((PAD, 62), "Blender 5.2 Eevee review, 2026-10-18. Patient_v03 (v02 rig/weights unchanged), Organs_v03, OperationAbdomen_v03, "
           "BLOOD-BAG v05, SYRINGE v02. Dissection windows and the stencil emulation are review-only tricks (Unity uses the "
           "ABDOMEN_MASK stencil).", font=font_s, fill=(190, 195, 200))
    y = 100
    T = TILES
    y = row(sheet, d, y, [(load(T / "05_front_open_torso.png"), "FRONT - open torso, all organs (ribcage on)", HEAD),
                          (load(T / "05b_front_open_torso_no_ribs.png"), "FRONT - ribs hidden: heart, lungs, liver, kidneys", HEAD),
                          (load(T / "06_side_open_torso.png"), "SIDE - left flank window (lung, heart, liver, kidney)", HEAD)], 900)
    y = row(sheet, d, y, [(load(T / "07_back_v02_bug.png"), "BEFORE (v02) - flipped patient: back culled by the stencil", RED),
                          (load(T / "08_back_v03_closed.png"), "AFTER (v03) - flipped patient: back is solid skin", GREEN),
                          (load(T / "09_stencil_zone.png"), "v03 Body: only the teal front zone is stencil-tested", GREEN)], 560)
    y = row(sheet, d, y, [(load(T / "02_opening_top_close.png"), "GAME VIEW - OperationAbdomen_v03 (top camera)", HEAD),
                          (load(T / "03_three_quarter.png"), "3/4 - lying patient, TABLE_REST", HEAD),
                          (load(T / "04_chest_xray.png"), "Chest under the skin (op camera, skin x-ray)", HEAD)], 600)
    li = lineup()
    d.rectangle((PAD, y, W - PAD, y + 34), fill=HEAD)
    d.text((PAD + 10, y + 5), "ORGAN LINEUP at 1:1 (each organ in its socket frame, front view) - 10 cm bar; sizes = mesh bounds X x Y x Z",
           font=font_h, fill=(255, 255, 255))
    lw = W - 2 * PAD
    lh = round(li.height * lw / li.width)
    sheet.paste(li.resize((lw, lh), Image.LANCZOS), (PAD, y + 34))
    y += 34 + lh + PAD
    y = row(sheet, d, y, [(load(T / "11_ribcage_closed.png"), "RIBCAGE - 9 rib pairs + split sternum + spine", HEAD),
                          (load(T / "12_ribcage_open.png"), "RIBCAGE opened - halves 35 deg about their hinges", HEAD),
                          (load(T / "13_heart_vessels.png"), "HEART + aorta, venae cavae, pulmonary vessels", HEAD),
                          (load(T / "14_heart_vessels_nolungs.png"), "HEART vessels (lungs hidden)", HEAD)], 560)
    bag = strip([BAG / f"blood_bag_v05_fill_{n}.png" for n in ("000", "050", "100")], ["0 %", "50 %", "100 %"])
    syr = strip([SYR / f"syringe_v02_fill_{n}.png" for n in ("000", "050", "100")], ["0 %", "50 %", "100 %"], crop=(110, 0, 590, 940))
    half = (W - 3 * PAD) // 2
    for k, (img, title) in enumerate(((bag, "BLOOD BAG v05 - translucent pouch, flat blood level (shape keys), fill 0 / 50 / 100 %"),
                                      (syr, "SYRINGE v02 - plunger + blood column move together, fill 0 / 50 / 100 %"))):
        x = PAD + k * (half + PAD)
        d.rectangle((x, y, x + half, y + 34), fill=HEAD)
        d.text((x + 10, y + 5), title, font=font_h, fill=(255, 255, 255))
        h = round(img.height * half / img.width)
        sheet.paste(img.resize((half, h), Image.LANCZOS), (x, y + 34))
        hh = h
    y += 34 + hh + PAD
    # key numbers
    o = ORGB["objects"]
    s = LAYOUT["organs"]
    lines = [
        "Key numbers (patient rest frame, metres; organs 1:1, scale 1, pivot = organ centre)",
        f"Heart {o['ORGAN_HEART']['size_m_xyz'][1]*100:.1f} cm tall (real 12 x 0.9), centre {s['ORGAN_HEART']['rest_socket']['rest_position']}; "
        f"lungs {o['ORGAN_LUNG_L']['size_m_xyz'][1]*100:.1f} cm tall (25 cm real scaled to Buddy's short chest), 10.2 x 10.2 cm",
        f"Liver {o['ORGAN_LIVER']['size_m_xyz'][0]*100:.1f} cm wide, centre {s['ORGAN_LIVER']['rest_socket']['rest_position']} (v02 z 1.032); "
        f"kidneys {o['ORGAN_KIDNEY_L']['size_m_xyz'][1]*100:.1f} cm incl. ureter stub, L z 0.908 / R z 0.885 (v02 0.975 / 0.955)",
        "Ribcage: RIB_L/R_01..09 (bone + cartilage), STERNUM_L/R (split for the osteotome), SPINE_THORACIC; hinges RIBCAGE_HALF_L/R; "
        "great vessels join the abdominal aorta / IVC at z ~1.02",
        f"Closed back: Body slots Buddy_Skin (front zone, {LAYOUT['stencil_zone']['faces']['zone_Buddy_Skin']} faces) / Buddy_Skin_Nose / "
        f"Patient_Skin_Closed ({LAYOUT['stencil_zone']['faces']['Patient_Skin_Closed']} faces); verts, weights, UVs, 65 bones hash-identical to v02",
        f"Blood bag v05: {BAGJ['total_tris']} tris, {BAGJ['bounds_m']['size'][2]*100:.0f} cm tall; syringe v02: {SYRJ['total_tris']} tris, "
        f"plunger travel {SYRJ['plunger']['travel_m']*1000:.1f} mm = blood column, 0.5 mm gap",
        "Report: Working/Reviews/Operations/organs_v03/PROGRESS.md; integration steps in Patient_v03/ORGANS_LAYOUT_v03.json (unity_integration)",
    ]
    for k, ln in enumerate(lines):
        d.text((PAD, y + k * 28), ln, font=font_l if k == 0 else font_s, fill=(235, 235, 235) if k == 0 else (200, 205, 210))
    y += len(lines) * 28 + PAD
    sheet = sheet.crop((0, 0, W, y))
    sheet.save(OUT, optimize=True)
    print("sheet", OUT, sheet.size)


main()
