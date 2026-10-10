# Phone UI art v04 (TASK-000149): wallpaper from the picture Vadim chose (empty cab, peeking sausage),
# used as delivered; Bank icon redesign: dollar bills only, no coins.
# Run: python build_phone_art_v04.py  (Pillow only). Reuses v01 (save/meta) and v03 (crop + soft extension).
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "Phone_v01"))
sys.path.insert(0, os.path.join(HERE, "..", "Phone_v03"))
import build_phone_art as v01  # noqa: E402
import build_phone_art_v03 as v03  # noqa: E402

SOURCE = os.path.join(HERE, "Sources", "wallpaper_busik_vadim_v2.webp")
PREVIEW = os.path.join(HERE, "Previews")


def wallpaper():
    src = Image.open(SOURCE).convert("RGB")
    crop = src.crop((v03.CROP_X[0], 0, v03.CROP_X[1], src.height))
    full_height = round(crop.width * v03.H / v03.W)
    missing = full_height - crop.height
    top = round(missing * v03.EXTEND_TOP_SHARE)
    bottom = missing - top
    canvas = Image.new("RGB", (crop.width, full_height))
    canvas.paste(v03.extend(crop.crop((0, 0, crop.width, top)), (crop.width, top), True), (0, 0))
    canvas.paste(crop, (0, top))
    canvas.paste(v03.extend(crop.crop((0, crop.height - bottom, crop.width, crop.height)), (crop.width, bottom), True),
                 (0, top + crop.height))
    for y0 in (top, top + crop.height):
        band = canvas.crop((0, y0 - 14, crop.width, y0 + 14)).filter(ImageFilter.GaussianBlur(5))
        canvas.paste(band, (0, y0 - 14))
    return canvas.resize((v03.W, v03.H), Image.LANCZOS)


def icon_bank():
    """A fanned stack of dollar bills, no coins."""
    base = v01.tile("#3E56C9", "#1B2775")
    g, _ = v01.layer()
    font = ImageFont.truetype(v01.FONT_BLACK, 210)
    small = ImageFont.truetype(v01.FONT_BLACK, 64)
    edge, line = v01.hexc("#2E8B47"), v01.hexc("#3FA35A")

    def bill(angle, dx, dy, top, bottom):
        b, bd = v01.layer()
        box = (512 - 340 + dx, 512 - 180 + dy, 512 + 340 + dx, 512 + 180 + dy)
        bd.rounded_rectangle(box, radius=34, fill=edge)
        inner = (box[0] + 20, box[1] + 20, box[2] - 20, box[3] - 20)
        paper = v01.gradient(inner[2] - inner[0], inner[3] - inner[1], [(0, top), (1, bottom)])
        mask = Image.new("L", paper.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, paper.width - 1, paper.height - 1), radius=22, fill=255)
        b.paste(paper, inner[:2], mask)
        bd.rounded_rectangle((inner[0] + 26, inner[1] + 26, inner[2] - 26, inner[3] - 26), radius=16, outline=line, width=8)
        cx, cy = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
        bd.ellipse((cx - 118, cy - 118, cx + 118, cy + 118), fill=edge)
        bd.ellipse((cx - 96, cy - 96, cx + 96, cy + 96), fill=v01.hexc(top))
        bd.text((cx, cy + 8), "$", font=font, fill=edge, anchor="mm")
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            bd.text((cx + sx * 232, cy + sy * 92 + 4), "$", font=small, fill=line, anchor="mm")
        g.alpha_composite(b.rotate(angle, resample=Image.BICUBIC, center=(cx, cy)))

    bill(16, -10, -40, "#9ED98C", "#7CC46B")
    bill(5, 6, 10, "#ADE29B", "#88CC77")
    bill(-7, 0, 66, "#C2EEB2", "#97D686")
    return v01.shadowed(base, g)


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    results = []
    v01.save(wallpaper(), "wallpaper", results)
    v01.save(icon_bank().resize((256, 256), Image.LANCZOS), "app_bank", results)
    sheet = Image.new("RGB", (560, 672), (42, 45, 51))
    sheet.paste(results[0][1].resize((300, 652)), (10, 10))
    icon = results[1][1].resize((200, 200), Image.LANCZOS)
    sheet.paste(icon, (340, 30), icon)
    sheet.save(os.path.join(PREVIEW, "phone_art_v04.png"))
    print("wrote", [n for n, _ in results])


if __name__ == "__main__":
    main()
