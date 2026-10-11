# Phone UI art v02 (TASK-000146): wallpaper from Vadim's mockup, banknote Bank icon.
# Run: python build_phone_art_v02.py  (Pillow only). Reuses helpers from Phone_v01.
# Writes Assets/OnlyVolunteers/UI/Phone/Resources/Phone/{wallpaper,app_bank}.png and Previews.
import os
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "Phone_v01"))
import build_phone_art as v01  # noqa: E402

SOURCE = os.path.join(HERE, "Sources", "wallpaper_mockup_vadim.webp")
PREVIEW = os.path.join(HERE, "Previews")
W, H = 600, 1304  # same aspect as the in-game screen (392 x 852)
# Screen quad in the mockup (upper-left, lower-left, lower-right, upper-right); the phone is tilted ~2 deg.
SCREEN_QUAD = (181, 102, 136, 1420, 757, 1441, 803, 123)


def mask_rect(mask, box):
    ImageDraw.Draw(mask).rectangle(box, fill=255)


def bright_strokes(img, box, blur, threshold, grow):
    """Mask of thin bright strokes (text, cracks) inside box: brighter than their surroundings."""
    lum = img.convert("L")
    local = lum.filter(ImageFilter.GaussianBlur(blur))
    diff = ImageChops.subtract(lum, local).point(lambda v: 255 if v > threshold else 0)
    region = Image.new("L", img.size, 0)
    mask_rect(region, box)
    strokes = ImageChops.multiply(diff, region)
    for _ in range(grow):
        strokes = strokes.filter(ImageFilter.MaxFilter(3))
    return strokes


def pull_push(img, mask):
    """Fill masked pixels from their surroundings with a pyramid (pull-push) interpolation."""
    rgba = img.convert("RGBA")
    rgba.putalpha(ImageChops.invert(mask))
    levels = [rgba]
    while min(levels[-1].size) > 4:
        w, h = levels[-1].size
        levels.append(levels[-1].resize((max(1, w // 2), max(1, h // 2)), Image.BOX))
    filled = Image.new("RGBA", levels[-1].size, (0, 0, 0, 255))
    filled.alpha_composite(levels[-1])
    for level in reversed(levels[:-1]):
        up = filled.resize(level.size, Image.BICUBIC)
        up.putalpha(255)
        up.alpha_composite(level)
        filled = up
    result = filled.convert("RGB")
    # Soften the filled area a little so it reads as out-of-focus background.
    soft = result.filter(ImageFilter.GaussianBlur(3))
    return Image.composite(soft, result, mask.filter(ImageFilter.GaussianBlur(2)))


# Icon slots of the mockup in wallpaper pixels; the game grid uses the same centres
# (PhoneHome.SlotCentre), so the patches left by the old icons stay under the new ones.
SLOT_X = (107, 294, 482)
SLOT_Y = (780, 947, 1112)
SLOT_HALF = 64


def white_strokes(img, box, minimum, grow):
    """White text: all channels bright (the orange sunset behind it is not)."""
    r, g, b = img.split()
    low = ImageChops.darker(ImageChops.darker(r, g), b).point(lambda v: 255 if v > minimum else 0)
    region = Image.new("L", img.size, 0)
    mask_rect(region, box)
    strokes = ImageChops.multiply(low, region)
    for _ in range(grow):
        strokes = strokes.filter(ImageFilter.MaxFilter(3))
    return strokes


def mirror_fill(img, box, feather=26):
    """Replace an opaque box by the rows above it mirrored downwards, feathered into the original."""
    x0, y0, x1, y1 = box
    height = y1 - y0
    patch = img.crop((x0, y0 - height, x1, y0)).transpose(Image.FLIP_TOP_BOTTOM)
    patch = patch.filter(ImageFilter.GaussianBlur(2))
    alpha = Image.new("L", patch.size, 255)
    ad = ImageDraw.Draw(alpha)
    for i in range(feather):
        v = int(255 * (i + 1) / feather)
        ad.rectangle((i, i, patch.width - 1 - i, patch.height - 1 - i), outline=v)
    # Fully opaque where the old card was, soft only outside it.
    out = img.copy()
    grown = (x0 - feather // 2, y0 - feather // 2, x1 + feather // 2, y1 + feather // 2)
    patch = patch.resize((grown[2] - grown[0], grown[3] - grown[1]), Image.BICUBIC)
    alpha = alpha.resize(patch.size, Image.BICUBIC)
    out.paste(patch, grown[:2], alpha)
    return out


def wallpaper():
    src = Image.open(SOURCE).convert("RGB")
    img = src.transform((W, H), Image.QUAD, SCREEN_QUAD, Image.BICUBIC)
    mask = Image.new("L", (W, H), 0)
    mask_rect(mask, (0, 0, W, 50))                 # old status bar and camera hole
    mask_rect(mask, (0, 1246, 60, H))              # duct tape corner
    for x in SLOT_X:
        for y in SLOT_Y:
            mask_rect(mask, (x - SLOT_HALF, y - SLOT_HALF, x + SLOT_HALF, y + SLOT_HALF))
    mask_rect(mask, (130, 700, 190, 752))          # unread badge
    mask = ImageChops.lighter(mask, bright_strokes(img, (0, 0, 470, 470), 5, 18, 2))       # cracks
    mask = ImageChops.lighter(mask, white_strokes(img, (140, 80, 480, 300), 125, 7))      # clock and date
    mask = ImageChops.lighter(mask, white_strokes(img, (0, 840, W, H), 165, 3))           # labels, home bar
    img = pull_push(img, mask)
    img = mirror_fill(img, (6, 314, 514, 472))  # old notification card: reflect the trees above it

    # Gentle dimming under the icon grid for readable labels.
    fade = Image.new("L", (W, H), 0)
    fd = ImageDraw.Draw(fade)
    top, full = 640, 860
    for y in range(top, H):
        fd.line([(0, y), (W, y)], fill=int(90 * min(1.0, (y - top) / (full - top))))
    return Image.composite(Image.new("RGB", (W, H), (8, 10, 20)), img, fade)


def icon_bank():
    """Banknotes and coins: reads as money at a glance."""
    base = v01.tile("#3E56C9", "#1B2775")
    g, d = v01.layer()
    font = ImageFont.truetype(v01.FONT_BLACK, 190)

    def note(cx, cy, angle, fill, edge):
        n, nd = v01.layer()
        nd.rounded_rectangle((cx - 300, cy - 165, cx + 300, cy + 165), radius=36, fill=v01.hexc(edge))
        nd.rounded_rectangle((cx - 276, cy - 141, cx + 276, cy + 141), radius=24, fill=v01.hexc(fill))
        nd.rounded_rectangle((cx - 246, cy - 111, cx + 246, cy + 111), radius=18, outline=v01.hexc(edge), width=10)
        nd.ellipse((cx - 98, cy - 98, cx + 98, cy + 98), fill=v01.hexc(edge))
        nd.text((cx, cy + 6), "$", font=font, fill=v01.hexc(fill), anchor="mm")
        for sx in (-1, 1):
            nd.ellipse((cx + sx * 190 - 26, cy - 26, cx + sx * 190 + 26, cy + 26), fill=v01.hexc(edge))
        g.alpha_composite(n.rotate(angle, resample=Image.BICUBIC, center=(cx, cy)))

    note(500, 430, 14, "#9FDE8E", "#3E8F45")
    note(512, 500, -4, "#B5EBA3", "#3E8F45")
    for cx, cy in ((690, 760), (790, 700)):
        d.ellipse((cx - 112, cy - 112, cx + 112, cy + 112), fill=v01.hexc("#E59A0B"))
        d.ellipse((cx - 92, cy - 92, cx + 92, cy + 92), fill=v01.hexc("#FFD25E"))
        d.text((cx, cy + 4), "$", font=ImageFont.truetype(v01.FONT_BLACK, 120), fill=v01.hexc("#C07A00"), anchor="mm")
    return v01.shadowed(base, g)


def main():
    os.makedirs(PREVIEW, exist_ok=True)
    os.makedirs(v01.OUT, exist_ok=True)
    results = []
    v01.save(wallpaper(), "wallpaper", results)
    v01.save(icon_bank().resize((256, 256), Image.LANCZOS), "app_bank", results)
    sheet = Image.new("RGB", (640 + 280, 1304 // 2 + 20), (42, 45, 51))
    sheet.paste(results[0][1].convert("RGB").resize((300, 652)), (10, 10))
    src = Image.open(SOURCE).convert("RGB").transform((W, H), Image.QUAD, SCREEN_QUAD, Image.BICUBIC)
    sheet.paste(src.resize((300, 652)), (320, 10))
    icon = results[1][1]
    sheet.paste(icon.resize((200, 200)), (660, 20), icon.resize((200, 200)))
    sheet.save(os.path.join(PREVIEW, "phone_art_v02.png"))
    print("wrote", [name for name, _ in results])


if __name__ == "__main__":
    main()
