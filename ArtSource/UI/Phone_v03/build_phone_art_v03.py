# Phone UI art v03 (TASK-000148): wallpaper from Vadim's picture (no driver, nameless van),
# new Gallery/Taxi/PayMarket icons.
# Run: python build_phone_art_v03.py  (Pillow only). Reuses helpers from Phone_v01; v01/v02 stay untouched.
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "Phone_v01"))
import build_phone_art as v01  # noqa: E402


SOURCE = os.path.join(HERE, "Sources", "wallpaper_busik_vadim.webp")
PREVIEW = os.path.join(HERE, "Previews")
W, H = 600, 1304             # in-game screen aspect (392 x 852)
CROP_X = (80, 928)           # keeps the running sausage and the BUSIK sign
EXTEND_TOP_SHARE = 0.58      # share of the missing height added above (sky), rest below (bushes)


def extend(strip, size, flip):
    """Soft continuation of an image edge: mirrored, blurred and slightly darkened."""
    part = strip.transpose(Image.FLIP_TOP_BOTTOM) if flip else strip
    part = part.resize(size, Image.BICUBIC).filter(ImageFilter.GaussianBlur(7))
    return Image.blend(part, Image.new("RGB", size, (12, 10, 26)), 0.25)


def pull_push(img, mask):
    """Fill masked pixels from their surroundings (premultiplied pull-push pyramid)."""
    known = ImageChops.invert(mask)
    colour = Image.composite(img, Image.new("RGB", img.size), known)  # premultiplied: holes are zero
    levels = [(colour, known)]
    while min(levels[-1][0].size) > 2:
        c, a = levels[-1]
        size = (max(1, c.width // 2), max(1, c.height // 2))
        levels.append((c.resize(size, Image.BOX), a.resize(size, Image.BOX)))
    c, a = levels[-1]
    fill = Image.new("RGB", c.size)
    cp, ap, fp = c.load(), a.load(), fill.load()
    for y in range(c.height):
        for x in range(c.width):
            k = max(ap[x, y], 1) / 255.0
            fp[x, y] = tuple(min(255, int(v / k)) for v in cp[x, y])
    for c, a in reversed(levels[:-1]):
        up = fill.resize(c.size, Image.BICUBIC)
        missing = ImageChops.multiply(up, ImageChops.invert(a).convert("RGB"))
        fill = ImageChops.add(c, missing)
    soft = fill.filter(ImageFilter.GaussianBlur(1.5))
    return Image.composite(soft, img, mask.filter(ImageFilter.GaussianBlur(1.5)))


def clean_van(src):
    """The van stays anonymous: no sausage behind the wheel, no ONLY VOLUNTEERS on the front."""
    # Driver: mirror the empty left half of the cabin into the driver's side (the cabin is
    # nearly symmetric; a second wiper there looks natural), feathered into the original.
    hole = (584, 684, 690, 780)
    width = hole[2] - hole[0]
    patch = src.crop((hole[0] - width, hole[1], hole[0], hole[3])).transpose(Image.FLIP_LEFT_RIGHT)
    alpha = Image.new("L", patch.size, 0)
    ImageDraw.Draw(alpha).rectangle((0, 8, patch.width - 9, patch.height), fill=255)
    alpha = alpha.filter(ImageFilter.GaussianBlur(4))
    ImageDraw.Draw(alpha).rectangle((0, 12, 6, patch.height), fill=255)  # seamless at the mirror line
    src.paste(patch, hole[:2], alpha)
    # The mirrored rows near the bottom carry bonnet from the left; refill that strip from dark glass.
    strip_box = (560, 700, 712, 784)
    local = src.crop(strip_box)
    strip = Image.new("L", local.size, 0)
    ImageDraw.Draw(strip).rectangle((584 - strip_box[0], 762 - strip_box[1], 690 - strip_box[0], 781 - strip_box[1]),
                                    fill=255)
    bright = local.convert("L").point(lambda v: 255 if v > 95 else 0)
    filled = pull_push(local, ImageChops.lighter(strip, bright))
    src.paste(Image.composite(filled, local, strip.filter(ImageFilter.GaussianBlur(1))), strip_box[:2])

    # Lettering: dark strokes below the windscreen edge (y = 752.5 + (x - 450) * 0.12).
    lum = src.convert("L")
    text = Image.new("L", src.size, 0)
    tp, lp = text.load(), lum.load()
    for y in range(768, 846):
        for x in range(462, 656):
            if y > 752.5 + (x - 450) * 0.12 + 5 and lp[x, y] < 125:
                tp[x, y] = 255
    for _ in range(3):
        text = text.filter(ImageFilter.MaxFilter(3))
    return pull_push(src, text)


def wallpaper():
    src = clean_van(Image.open(SOURCE).convert("RGB"))
    crop = src.crop((CROP_X[0], 0, CROP_X[1], src.height))
    full_height = round(crop.width * H / W)
    missing = full_height - crop.height
    top = round(missing * EXTEND_TOP_SHARE)
    bottom = missing - top
    canvas = Image.new("RGB", (crop.width, full_height))
    canvas.paste(extend(crop.crop((0, 0, crop.width, top)), (crop.width, top), True), (0, 0))
    canvas.paste(crop, (0, top))
    canvas.paste(extend(crop.crop((0, crop.height - bottom, crop.width, crop.height)), (crop.width, bottom), True),
                 (0, top + crop.height))
    # Feather both seams.
    for y0 in (top, top + crop.height):
        band = canvas.crop((0, y0 - 14, crop.width, y0 + 14)).filter(ImageFilter.GaussianBlur(5))
        canvas.paste(band, (0, y0 - 14))
    return canvas.resize((W, H), Image.LANCZOS)


def rounded_triangle_mask(points, radius, size=1024):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius)).point(lambda v: 255 if v > 128 else 0)


def diagonal(size, a, b):
    """Top-left to bottom-right gradient."""
    grad = Image.new("RGBA", (size, size))
    ca, cb = v01.hexc(a), v01.hexc(b)
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size - 2)
            px[x, y] = tuple(int(ca[i] + (cb[i] - ca[i]) * t) for i in range(4))
    return grad


def icon_gallery():
    base = v01.tile("#FF7AB6", "#7A4DFF")
    g, d = v01.layer()
    back, bd = v01.layer()
    bd.rounded_rectangle((250, 240, 820, 700), radius=50, fill=v01.hexc("#F4ECFF"))
    g.alpha_composite(back.rotate(-9, resample=Image.BICUBIC, center=(535, 470)))
    d.rounded_rectangle((196, 300, 812, 792), radius=54, fill="white")
    photo = v01.gradient(1024, 1024, [(0, "#5BC2FF"), (0.6, "#D8F3FF"), (1, "#D8F3FF")])
    pd = ImageDraw.Draw(photo)
    pd.ellipse((600, 360, 712, 472), fill=v01.hexc("#FFD54A"))
    pd.polygon([(222, 770), (420, 490), (540, 640), (630, 560), (790, 770)], fill=v01.hexc("#4C6FD8"))
    pd.polygon([(420, 490), (470, 562), (442, 580), (398, 522)], fill="white")
    pd.polygon([(222, 770), (330, 640), (470, 770)], fill=v01.hexc("#2E4FB0"))
    mask = Image.new("L", (1024, 1024), 0)
    ImageDraw.Draw(mask).rounded_rectangle((222, 326, 786, 766), radius=32, fill=255)
    g.paste(photo, (0, 0), mask)
    return v01.shadowed(base, g)


def icon_taxi():
    base = v01.tile("#323848", "#14171F")
    g, d = v01.layer()
    yellow, deep = v01.hexc("#FFC928"), v01.hexc("#F0A800")
    d.rounded_rectangle((236, 720, 352, 838), radius=30, fill=v01.hexc("#101216"))
    d.rounded_rectangle((672, 720, 788, 838), radius=30, fill=v01.hexc("#101216"))
    d.polygon([(300, 452), (382, 300), (642, 300), (724, 452)], fill=yellow)
    d.rounded_rectangle((178, 430, 846, 760), radius=96, fill=yellow)
    d.rounded_rectangle((178, 640, 846, 760), radius=60, fill=deep)
    d.polygon([(336, 440), (404, 326), (620, 326), (688, 440)], fill=v01.hexc("#27324A"))
    d.polygon([(420, 334), (470, 334), (420, 420), (370, 420)], fill=(255, 255, 255, 70))
    d.rounded_rectangle((420, 214, 604, 290), radius=22, fill="white")
    font = ImageFont.truetype(v01.FONT_BLACK, 56)
    d.text((512, 254), "TAXI", font=font, fill=v01.hexc("#14171F"), anchor="mm")
    for i in range(12):
        if i % 2 == 0:
            d.rectangle((272 + i * 40, 586, 312 + i * 40, 626), fill=v01.hexc("#14171F"))
    glow = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for cx in (290, 734):
        gd.ellipse((cx - 110, 420, cx + 110, 640), fill=(255, 240, 170, 150))
    g.alpha_composite(glow.filter(ImageFilter.GaussianBlur(30)))
    d = ImageDraw.Draw(g)
    for cx in (290, 734):
        d.ellipse((cx - 58, 472, cx + 58, 588), fill=v01.hexc("#FFF7D6"))
        d.ellipse((cx - 30, 500, cx + 30, 560), fill="white")
    d.rounded_rectangle((420, 486, 604, 556), radius=20, fill=v01.hexc("#1E232E"))
    d.rounded_rectangle((160, 690, 864, 750), radius=28, fill=v01.hexc("#3A3F4B"))
    return v01.shadowed(base, g)


def icon_market():
    base = v01.tile("#FFFFFF", "#E4E8F0")
    g, d = v01.layer()
    mask = rounded_triangle_mask([(300, 214), (300, 810), (820, 512)], 46)
    g.paste(diagonal(1024, "#00C9A7", "#7B4DFF"), (0, 0), mask)
    shine = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    ImageDraw.Draw(shine).polygon([(330, 270), (330, 500), (560, 380)], fill=(255, 255, 255, 60))
    g.alpha_composite(Image.composite(shine, Image.new("RGBA", (1024, 1024), (0, 0, 0, 0)), mask))
    d.ellipse((600, 600, 900, 900), fill="white")
    d.ellipse((622, 622, 878, 878), fill=v01.hexc("#F5A300"))
    d.ellipse((648, 648, 852, 852), fill=v01.hexc("#FFD54A"))
    font = ImageFont.truetype(v01.FONT_BLACK, 170)
    d.text((750, 758), "$", font=font, fill=v01.hexc("#B87400"), anchor="mm")
    return v01.shadowed(base, g, alpha=90)


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    results = []
    v01.save(wallpaper(), "wallpaper", results)
    for name, fn in (("app_gallery", icon_gallery), ("app_taxi", icon_taxi), ("app_market", icon_market)):
        v01.save(fn().resize((256, 256), Image.LANCZOS), name, results)
    sheet = Image.new("RGB", (330 + 3 * 200 + 40, 672), (42, 45, 51))
    sheet.paste(results[0][1].resize((320, 696)).crop((0, 0, 320, 652)), (10, 10))
    x = 350
    for name, img in results[1:]:
        small = img.resize((180, 180), Image.LANCZOS)
        sheet.paste(small, (x, 30), small)
        x += 200
    sheet.save(os.path.join(PREVIEW, "phone_art_v03.png"))
    print("wrote", [n for n, _ in results])


if __name__ == "__main__":
    main()
