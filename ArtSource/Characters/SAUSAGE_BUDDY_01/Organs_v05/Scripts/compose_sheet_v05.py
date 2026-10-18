"""Compose the one compact review sheet Working/Reviews/Operations/organs_v05/organs_v05_sheet.png (system Python + Pillow).

python compose_sheet_v05.py      (tiles from render_review_v05.py; the v04 top-camera tile from organs_v04/tiles)
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(r"C:/Dev/Game")
REV = REPO / "Working/Reviews/Operations/organs_v05"
T = REV / "tiles"
T4 = REPO / "Working/Reviews/Operations/organs_v04/tiles"
OUT = REV / "organs_v05_sheet.png"
B = json.loads((REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v05/organs_v05_build.json").read_text(encoding="utf-8"))
A = json.loads((REPO / "ArtSource/Props/TABLE-ASTRA-001/v05/OperationAbdomen_v05_validation.json").read_text(encoding="utf-8"))
S = json.loads((REPO / "ArtSource/Props/TABLE-ASTRA-001/v05/OperationSutured_v05.json").read_text(encoding="utf-8"))
P = json.loads((REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v05/build_report_SAUSAGE_BUDDY_PATIENT_v05.json").read_text(encoding="utf-8"))
W, PAD, BG = 2000, 12, (31, 33, 38)
HEAD, RED, GREEN = (60, 140, 170), (196, 70, 60), (70, 160, 95)
F = "C:/Windows/Fonts/"
ft = ImageFont.truetype(F + "arialbd.ttf", 34)
fh = ImageFont.truetype(F + "arialbd.ttf", 21)
fs = ImageFont.truetype(F + "arial.ttf", 19)
CROP = (540, 470, 1150, 1080)        # the patient in the 1920x1080 table-camera renders


def load(path, crop=None):
    im = Image.open(path).convert("RGB")
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
    d.text((PAD, 8), "organs v05 - bigger, lower opening, chest well inside, intestines back, sutured state", font=ft, fill=(240, 240, 240))
    d.text((PAD, 50), "Patient_v05 (low-rise trunks) + Organs_v05 + OperationAbdomen_v05 + OperationSutured_v05. Rim = v03 rim. "
                      "Blender Eevee, TABLE_REST pose; Unity not run.", font=fs, fill=(190, 195, 200))
    y = 84
    y = row(sheet, d, y, [(load(T4 / "01_operation_camera.png", CROP), "v04 - top table game camera", RED),
                          (load(T / "01_operation_camera.png", CROP), "v05 - same camera: 4 rib pairs, heart, lungs inside", GREEN),
                          (load(T / "20_sutured_game_camera.png", CROP), "v05 - closed with stitches (same camera)", GREEN)], 600)
    y = row(sheet, d, y, [(load(T / "03_three_quarter.png"), "3/4 - lying patient", HEAD),
                          (load(T / "17_intestines.png"), "Intestines (v03 size) in the lower belly", HEAD),
                          (load(T / "19_sutured_close.png"), "Suture close-up: cross-stitches, knots, dried blood", HEAD)], 420)
    sut = [load(T / f"18_sutured_{p:03d}.png", (60, 40, 1040, 1180)) for p in (0, 50, 100)]
    y = row(sheet, d, y, [(sut[0], "Sutured 0 % stitches", HEAD), (sut[1], "50 %", HEAD), (sut[2], "100 %", HEAD),
                          (load(T / "08_back_v03_closed.png"), "BACK - flipped: solid, nothing pokes out", GREEN)], 470)
    sc, sk = B["shift_chest_rest_m"], B["shift_kidney_rest_m"]
    op = A["outline"]
    u = B["ucx_rebuilt_v05"]
    tr = P["trunks"]
    bk = A["bowel_vs_kidneys"]
    lines = [
        f"v04 -> v05: chest + liver block (ribs, sternum, UCX, hinges, heart, lungs, vessels, diaphragm, liver) {sc[2] * 100:+.1f} cm; kidneys "
        f"{sk[2] * 100:+.1f} cm up, {sk[1] * 1000:.0f} mm back; ureter stubs shortened. Heart top now rest z "
        f"{B['rest_z_ranges_v05']['ORGAN_HEART'][1]:.3f} (opening top 1.112, chin 1.120).",
        f"Opening: rest z 1.112 -> 0.787 (v04: 0.808), {2 * op['half_width'] * 100:.1f} cm wide (v04 24.8), broad full top; trunks low-rise: "
        f"waistband {tr['waistband_rest_z_v04']} -> {tr['waistband_rest_z_v05']} (fitted, >= {tr['waist_min_gap_to_skin_mm']} mm off the skin); "
        f"stencil zone +{P['zone_faces_added']} faces.",
        f"Ribs 3-4 back tips re-bent <= {max(v['max_translation_mm'] for v in B['rib_bend_v05'].values())} mm (>= 2.3 mm under the skin, rest + "
        f"TABLE_REST); {len(u)} UCX rebuilt; G38 contract PASS: convex, <= {max(v['vertices'] for v in u.values())} verts, "
        f"<= {max(v['outside_certified_mm'] for v in u.values())} mm outside, rib gaps >= {min(B['rib_gaps_mm'].values())} mm, "
        f"UCX-kidneys >= {B['ucx_to_kidneys_min_mm']['open35']} mm.",
        f"Intestines: v03 coil (4 rows, tube r 10.8 mm), {A['bowel_verts_inside_cavity_pct']} % in the cavity, rest under the pubic rim "
        f"(>= {bk['bowel_outside_cavity_min_depth_under_skin_mm']} mm under the skin); gap to kidneys >= "
        f"{min(bk['ORGAN_KIDNEY_L']['min_gap_to_bowel_mm'], bk['ORGAN_KIDNEY_R']['min_gap_to_bowel_mm'])} mm, liver {bk['ORGAN_LIVER']['min_gap_to_bowel_mm']} mm.",
        f"Sutured: SUTURE_SKIN = same outline + 9 mm (mask + 6 mm), puffy seam; {S['stitches']} ordered SUTURE_STITCH_01..{S['stitches']:02d} "
        "(head -> pubic, props order/progress) + SUTURE_THREAD_ALL with UV1.x = 0..1 progress; SUTURE_BLOOD.",
    ]
    for k, ln in enumerate(lines):
        d.text((PAD, y + k * 26), ln, font=fs, fill=(205, 210, 215))
    y += len(lines) * 26 + PAD
    sheet.crop((0, 0, W, y)).save(OUT, optimize=True)
    print("sheet", OUT, (W, y))


main()
