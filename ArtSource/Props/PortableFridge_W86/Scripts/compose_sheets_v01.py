"""PortableFridge_W86 v01 - compose labelled review sheets from render panels (PIL).

python compose_sheets_v01.py <panels_dir>   ->  ../Renders/PortableFridge_W86_v01_0N_*.png
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "Renders")
PANELS = sys.argv[1]
J = json.load(open(os.path.join(ROOT, "PortableFridge_W86_v01.json"), encoding="utf-8"))
FIT = json.load(open(os.path.join(ROOT, "Validation", "PortableFridge_W86_v01_fitcheck.json"), encoding="utf-8"))
F = r"C:\Windows\Fonts\arial.ttf"
FB = r"C:\Windows\Fonts\arialbd.ttf"
BG, BAR, FG, SUB = (40, 44, 52), (31, 37, 48), (240, 240, 240), (170, 176, 186)


def font(sz, bold=False):
    return ImageFont.truetype(FB if bold else F, sz)


def sheet(name, title, subtitle, grid, cols, cell, extra_lines=()):
    cw, ch = cell
    rows = (len(grid) + cols - 1) // cols
    foot = 40 * len(extra_lines) + (20 if extra_lines else 0)
    W, H = cw * cols, 120 + rows * (ch + 40) + foot
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 112], fill=BAR)
    d.text((28, 18), title, font=font(36, True), fill=FG)
    d.text((28, 68), subtitle, font=font(22), fill=SUB)
    for i, (panel, caption) in enumerate(grid):
        x, y = (i % cols) * cw, 120 + (i // cols) * (ch + 40)
        if panel.startswith("TEXT:"):
            d.rectangle([x + 8, y, x + cw - 8, y + ch], fill=(48, 53, 62))
            for k, line in enumerate(panel[5:].split("\n")):
                d.text((x + 30, y + 26 + k * 34), line, font=font(24, k == 0), fill=FG if k == 0 else SUB)
        else:
            p = Image.open(os.path.join(PANELS, panel + ".png")).convert("RGB")
            p.thumbnail((cw - 16, ch), Image.LANCZOS)
            im.paste(p, (x + (cw - p.width) // 2, y + (ch - p.height) // 2))
        d.text((x + 16, y + ch + 6), caption, font=font(22), fill=FG)
    for k, line in enumerate(extra_lines):
        d.text((28, H - foot + 10 + k * 40), line, font=font(24), fill=FG)
    path = os.path.join(OUT, name)
    if os.path.exists(path):
        raise SystemExit("refusing to overwrite " + path)
    im.save(path, optimize=True)
    print("wrote", path)


os.makedirs(OUT, exist_ok=True)
dm = J["dimensions"]
lods = J["lods"]
shell = "x".join("%.2f" % v for v in dm["shell_closed_xyz_blender"])
over = "x".join("%.2f" % v for v in dm["overall_closed_with_handles_hardware_xyz_blender"])
sub = "PortableFridge_W86 v01  |  корпус %s м, с ручками %s м  |  LOD0 %d / LOD1 %d треуг.  |  на ревью" % (
    shell, over, lods["LOD0_tris"], lods["LOD1_tris"])

info = ("TEXT:Переносной холодильник $1 000\n"
        "8 мест, несут двумя руками\n"
        "корпус 0.60 x 0.52 x 0.41 м\n"
        "с ручками/петлями %s м\n"
        "внутри 0.54 x 0.46, высота 0.305 м\n"
        "крышка на петле, открыта %d°\n"
        "ручки: высота 0.255 м, разнос 0.66 м\n"
        "LOD0 %d / LOD1 %d треугольников\n"
        "1 материал, атлас 1024 px" % (over, J["lid"]["open_angle_deg"], lods["LOD0_tris"], lods["LOD1_tris"]))
sheet("PortableFridge_W86_v01_01_closed.png", "ПЕРЕНОСНОЙ ХОЛОДИЛЬНИК — закрыт", sub,
      [("p01_front", "Спереди: наклейка, 2 защёлки, пробка слива"),
       ("p01_threequarter", "3/4: боковые ручки для двух рук"),
       ("p01_back", "Сзади: 2 петли крышки"),
       ("p01_side", "Сбоку: ручка с резиновой накладкой"),
       ("p01_lod1", "LOD1 (%d треуг.)" % lods["LOD1_tris"]),
       (info, "Стиль COOLER-ASTRA-001, потёртый")],
      3, (666, 506))

fitline = ", ".join("%s→%s" % (i["slot"], i["item"].split(" (")[0]) for i in FIT["items"] if i["slot"])
sheet("PortableFridge_W86_v01_02_open_slots.png", "ПЕРЕНОСНОЙ ХОЛОДИЛЬНИК — открыт, 8 мест", sub,
      [("p02_open_threequarter", "Якоря SLOT_01–08 (красная точка = якорь на дне)"),
       ("p02_open_top", "Сверху: 1–6 узкие, 7–8 широкие"),
       ("p02_fit_threequarter", "Проверка реальными моделями")],
      3, (666, 506),
      ["Места 1–6: 0.267 x 0.090 x 0.305 м (все органы, кроме мозга; пакеты органов и крови).",
       "Места 7–8: 0.267 x 0.172 x 0.305 м — влезает и мозг 0.14 x 0.16 x 0.15. Набор одного NPC (7 органов) = 6 узких + мозг.",
       "В кадре: " + fitline + "."])

sheet("PortableFridge_W86_v01_03_carry_reference.png", "ПЕРЕНОСНОЙ ХОЛОДИЛЬНИК — масштаб рядом с NPC толпы",
      "SAUSAGE_BUDDY_A_v04 (рост %.2f м в T-позе), руки через IK на точках GRIP_L/GRIP_R; второй холодильник стоит на полу" %
      json.load(open(os.path.join(PANELS, "carry.json")))["npc_height"],
      [("p03_carry_front", "Несёт двумя руками перед собой"), ("p03_carry_side", "Сбоку: ручки посередине глубины")],
      2, (1000, 760),
      ["У этого персонажа короткие руки (плечо–запястье 0.44 м) и живот, поэтому коробка выходит на уровень груди (ручки ≈ 1.15 м)."])

vm = J["van_mount"]
sheet("PortableFridge_W86_v01_04_van_mount.png", "КРЕПЛЕНИЕ В ФУРГОН (отдельный FBX)",
      "PortableFridge_W86_VanMount_v01  |  %s м  |  LOD0 %d / LOD1 %d треуг.  |  COOLER_SOCKET + плоскость стены" % (
          "x".join("%.2f" % v for v in vm["dims_xyz_blender"]), lods["per_object"]["SM_PortableFridge_VanMount_LOD0"],
          lods["per_object"]["SM_PortableFridge_VanMount_LOD1"]),
      [("p04_mount_empty", "Лоток, бортики, 2 прижима, кронштейн к стене"),
       ("p04_mount_open", "Холодильник в креплении, крышка открыта"),
       ("p04_mount_side", "Сбоку: открытая крышка не задевает стену")],
      3, (666, 506),
      ["Ставится у стены кузова петлями к стене; холодильник открывается прямо в креплении (по спеке).",
       "Открытая крышка (%d°) не доходит до стены на %.0f мм; отступ корпуса от стены %.0f мм." % (
           J["lid"]["open_angle_deg"], vm["lid_clearance_m"] * 1000, vm["standoff_m"] * 1000)])
