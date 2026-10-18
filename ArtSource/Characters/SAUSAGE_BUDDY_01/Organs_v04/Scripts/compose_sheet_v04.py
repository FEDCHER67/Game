"""Compose the one compact review sheet Working/Reviews/Operations/organs_v04/organs_v04_sheet.png (system Python + Pillow).

python compose_sheet_v04.py      (tiles from render_review_v04.py)
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(r"C:/Dev/Game")
REV = REPO / "Working/Reviews/Operations/organs_v04"
T = REV / "tiles"
OUT = REV / "organs_v04_sheet.png"
B = json.loads((REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/organs_v04_build.json").read_text(encoding="utf-8"))
A = json.loads((REPO / "ArtSource/Props/TABLE-ASTRA-001/v04/OperationAbdomen_v04_validation.json").read_text(encoding="utf-8"))
W, PAD, BG = 2000, 12, (31, 33, 38)
HEAD, RED, GREEN = (60, 140, 170), (196, 70, 60), (70, 160, 95)
F = "C:/Windows/Fonts/"
ft = ImageFont.truetype(F + "arialbd.ttf", 34)
fh = ImageFont.truetype(F + "arialbd.ttf", 21)
fs = ImageFont.truetype(F + "arial.ttf", 19)


def load(name, crop=None):
    im = Image.open(T / name).convert("RGB")
    return im.crop(crop) if crop else im


def fit(img, w, h):
    r = max(w / img.width, h / img.height)
    im = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x0, y0 = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x0, y0, x0 + w, y0 + h))


def row(sheet, d, y, items, h):
    n = len(items)
    w = (W - PAD * (n + 1)) // n
    for k, (img, title, col) in enumerate(items):
        x = PAD + k * (w + PAD)
        d.rectangle((x, y, x + w, y + 32), fill=col)
        d.text((x + 9, y + 5), title, font=fh, fill=(255, 255, 255))
        sheet.paste(fit(img, w, h), (x, y + 32))
    return y + 32 + h + PAD


def main():
    sheet = Image.new("RGB", (W, 4000), BG)
    d = ImageDraw.Draw(sheet)
    sh = B["shift_rest_m"]
    d.text((PAD, 8), "organs v04 - whole organ block 4.5 cm lower + chest/belly opening (OperationAbdomen_v04)", font=ft, fill=(240, 240, 240))
    d.text((PAD, 50), f"Rigid move {sh} m of the accepted v03d block (organs, 4 rib pairs, sternum halves, spine, hinges, BREAK, 96 UCX, "
                      "vessels, airway, diaphragm). Rim = v03 rim. Blender Eevee; Unity not run.", font=fs, fill=(190, 195, 200))
    y = 84
    crop = (520, 520, 1120, 1080)
    y = row(sheet, d, y, [(load("01_operation_camera_before_v03d.png", crop), "BEFORE v03d - top table game camera: chest under the chin", RED),
                          (load("01_operation_camera.png", crop), "AFTER v04 - same camera: ribs, heart, lungs, liver, kidneys framed", GREEN)], 860)
    y = row(sheet, d, y, [(load("03_three_quarter.png"), "3/4 - lying patient (TABLE_REST)", HEAD),
                          (load("15_rim_closeup.png"), "Opening rim close-up (v03 skin lip + cut layers)", HEAD),
                          (load("16_rim_chest_end.png"), "Rim at the chest end, under the chin", HEAD)], 520)
    y = row(sheet, d, y, [(load("05_front_open_torso.png"), "FRONT - open torso (dissection, standing)", HEAD),
                          (load("06_side_open_torso.png"), "SIDE - left flank window", HEAD),
                          (load("08_back_v03_closed.png"), "BACK - flipped patient: solid skin, rib tips inside", GREEN)], 620)
    rs = B["rigid_shift_check"]
    lines = [
        f"Rigid move check: world matrices = shift @ v03d (max error {rs['max_world_matrix_error']:.1e} m); organ<->UCX min unchanged by the move: "
        f"closed {rs['organ_ucx_min_mm_v03d']['closed'][0]} -> {rs['organ_ucx_min_mm_v04']['closed'][0]} mm, open 35 deg "
        f"{rs['organ_ucx_min_mm_v03d']['open35'][0]} -> {rs['organ_ucx_min_mm_v04']['open35'][0]} mm",
        "(vertex-surface measure; G38 exact values 4.899 / 3.149 mm stay valid). Opening v04: rest z 1.112 (chin line 1.120) to 0.808 "
        "(waistband 0.800), 24.8 cm wide.",
        "Stencil zone (Patient_v04) already covered the bigger opening: 0 faces added. The v03d rib 1-2 tips that poked out under the chin "
        "(BEFORE, top) are inside now.",
        "Rib trim: posterior tips of ribs 3-4 (poked up to 4.6 mm out of the back after the move) bent inward up to 7 mm, rib 4 one ring "
        "shorter; >= 2.3 mm under the skin.",
        "21 UCX rebuilt; G38 contract re-checked: PASS (convex, <= 64 verts, <= 1.97 mm outside, <= 0.25 mm uncovered, organs >= 4.28 mm "
        "closed / 4.6 mm open35, rib gaps >= 12.2 mm).",
    ]
    for k, ln in enumerate(lines):
        d.text((PAD, y + k * 26), ln, font=fs, fill=(205, 210, 215))
    y += len(lines) * 26 + PAD
    sheet.crop((0, 0, W, y)).save(OUT, optimize=True)
    print("sheet", OUT, (W, y))


main()
