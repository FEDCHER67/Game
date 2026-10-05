"""Shop sign atlas (2048 px): 12 Russian sign boards, 2 x 6 grid, with emission for night."""
import numpy as np
from PIL import Image, ImageDraw

from registry import texture
from texlib import Surface, blur, fbm, hexc, lerp, text_mask

S = 2048
CW, CH = 1024, 340
SIGNS = [
    # key,          text,                bg,        fg,        border,    icon,     glow, font
    ("apteka",      "АПТЕКА",            "#2f8f5b", "#ffffff", "#e9f3ec", "cross",  1.0, "display"),
    ("produkty24",  "ПРОДУКТЫ 24 ЧАСА",  "#2a5aa0", "#ffd23f", "#ffd23f", None,     1.0, "narrow"),
    ("bar",         "БАР",               "#3b2418", "#ffb347", "#8a5a33", "mug",    1.0, "display"),
    ("kazino",      "КАЗИНО",            "#8e1b22", "#ffd54a", "#ffd54a", "stars",  1.0, "display"),
    ("policiya",    "ПОЛИЦИЯ",           "#f1f1ee", "#1d3f8f", "#1d3f8f", "stripe", 0.0, "display"),
    ("bolnica",     "БОЛЬНИЦА",          "#f4f4f1", "#c62828", "#c62828", "cross",  0.0, "display"),
    ("bank",        "БАНК",              "#14284b", "#e8c66a", "#e8c66a", None,     0.5, "display"),
    ("kafe",        "КАФЕ",              "#efe1c4", "#6a3b22", "#6a3b22", "cup",    0.0, "display"),
    ("avtomaster",  "АВТОМАСТЕРСКАЯ",    "#f2b705", "#222222", "#222222", "wrench", 0.0, "narrow"),
    ("supermarket", "СУПЕРМАРКЕТ",       "#d6332b", "#ffffff", "#ffffff", None,     1.0, "narrow"),
    ("nochnoy_klub", "НОЧНОЙ КЛУБ",      "#241038", "#ff4fd8", "#37e0ff", None,     1.0, "display"),
    ("bouling",     "БОУЛИНГ",           "#1f6e8c", "#ffffff", "#ffffff", "pin",    1.0, "display"),
]
ATLAS = [{"name": k, "text": t, "rect_px": [(i % 2) * CW, (i // 2) * CH, CW, CH],
          "uv_rect": [(i % 2) / 2, 1 - ((i // 2) + 1) * CH / S, 0.5, CH / S], "night_glow": g > 0}
         for i, (k, t, _, _, _, _, g, _) in enumerate(SIGNS)]


def _mask(draw_fn):
    img = Image.new("L", (CW, CH), 0)
    draw_fn(ImageDraw.Draw(img))
    return np.asarray(img, np.float32) / 255.0


def icon_mask(icon, box):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = min(x1 - x0, y1 - y0) / 2

    def draw(d):
        if icon == "cross":
            a = r * 0.3
            d.rounded_rectangle([cx - a, cy - r * 0.85, cx + a, cy + r * 0.85], 8, fill=255)
            d.rounded_rectangle([cx - r * 0.85, cy - a, cx + r * 0.85, cy + a], 8, fill=255)
        elif icon == "mug":
            d.rounded_rectangle([cx - r * 0.55, cy - r * 0.6, cx + r * 0.3, cy + r * 0.8], 14, fill=255)
            d.ellipse([cx + r * 0.1, cy - r * 0.35, cx + r * 0.75, cy + r * 0.45], outline=255, width=int(r * 0.16))
            d.ellipse([cx - r * 0.7, cy - r * 0.95, cx + r * 0.45, cy - r * 0.45], fill=255)
        elif icon == "stars":
            for sx, sc in ((cx - r * 0.7, 0.32), (cx + r * 0.7, 0.32), (cx, 0.62)):
                pts = []
                for k in range(10):
                    ang = -np.pi / 2 + k * np.pi / 5
                    rr = r * sc * (1.0 if k % 2 == 0 else 0.42)
                    pts.append((sx + rr * np.cos(ang), cy + rr * np.sin(ang)))
                d.polygon(pts, fill=255)
        elif icon == "cup":
            d.chord([cx - r * 0.7, cy - r * 0.9, cx + r * 0.5, cy + r * 0.8], 0, 180, fill=255)
            d.ellipse([cx + r * 0.3, cy - r * 0.15, cx + r * 0.85, cy + r * 0.4], outline=255, width=int(r * 0.14))
            d.rounded_rectangle([cx - r * 0.85, cy + r * 0.72, cx + r * 0.7, cy + r * 0.86], 6, fill=255)
            for k in (-0.35, 0.0, 0.35):
                d.arc([cx + k * r - r * 0.12, cy - r * 0.6, cx + k * r + r * 0.12, cy - r * 0.15], 90, 270,
                      fill=255, width=int(r * 0.07))
        elif icon == "wrench":
            w = r * 0.28
            ang = np.pi / 4
            ex, ey = np.cos(ang) * r * 0.85, np.sin(ang) * r * 0.85
            d.line([cx - ex, cy + ey, cx + ex, cy - ey], fill=255, width=int(w))
            hx, hy = cx + ex, cy - ey
            d.ellipse([hx - r * 0.38, hy - r * 0.38, hx + r * 0.38, hy + r * 0.38], fill=255)
            d.ellipse([hx - r * 0.05, hy - r * 0.42, hx + r * 0.35, hy - r * 0.02], fill=0)
            d.ellipse([cx - ex - w * 0.7, cy + ey - w * 0.7, cx - ex + w * 0.7, cy + ey + w * 0.7], fill=255)
        elif icon == "pin":
            d.ellipse([cx - r * 0.28, cy - r * 0.95, cx + r * 0.28, cy - r * 0.4], fill=255)
            d.ellipse([cx - r * 0.45, cy - r * 0.35, cx + r * 0.45, cy + r * 0.95], fill=255)
            d.rectangle([cx - r * 0.2, cy - r * 0.55, cx + r * 0.2, cy - r * 0.2], fill=255)
    return _mask(draw)


def draw_sign(spec, fonts, rng):
    key, text, bg, fg, border, icon, glow, font = spec
    shape = (CH, CW)
    m = 14
    board = _mask(lambda d: d.rounded_rectangle([m, m, CW - m, CH - m], 28, fill=255))
    inner = _mask(lambda d: d.rounded_rectangle([m + 14, m + 14, CW - m - 14, CH - m - 14], 20, fill=255))
    frame = np.clip(board - inner, 0, 1)
    s = Surface(shape, hexc(bg), rough=0.55, height=0.0)
    s.alpha = board
    s.emission = np.zeros((*shape, 3), np.float32)
    s.height = 0.45 * blur(board, 1.0)
    s.albedo = hexc(bg) * (0.92 + 0.1 * fbm(shape, 3, rng, octaves=3))[..., None] * np.ones((*shape, 3), np.float32)
    s.lay(frame, hexc(border), rough=0.4, add_height=0.12, metal=0.2)

    tx0, tx1 = m + 50, CW - m - 50
    extra = np.zeros(shape, np.float32)
    if icon == "stripe":
        extra = _mask(lambda d: d.rectangle([m + 14, CH - m - 80, CW - m - 14, CH - m - 52], fill=255)) + \
            _mask(lambda d: d.rectangle([m + 14, CH - m - 46, CW - m - 14, CH - m - 30], fill=255))
        extra = np.clip(extra, 0, 1)
        ty0, ty1 = m + 40, CH - m - 100
        imask = None
    else:
        ty0, ty1 = m + 46, CH - m - 46
        imask = None
        if icon:
            imask = icon_mask(icon, (m + 50, m + 50, m + 50 + (CH - 2 * m - 100), CH - m - 50))
            tx0 = m + 50 + (CH - 2 * m - 100) + 40
    if key == "kazino":   # marquee bulbs along the frame
        def bulbs(d):
            for x in range(m + 40, CW - m - 20, 52):
                for y in (m + 7, CH - m - 7):
                    d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=255)
        extra = _mask(bulbs)
    tm = text_mask(shape, text, fonts[font], (tx0, ty0, tx1 - tx0, ty1 - ty0), 240)
    # drop shadow / outline for a chunky cartoon read
    shadow = np.clip(blur(np.roll(np.roll(tm, 6, 0), 6, 1), 2.0) * 1.3, 0, 1) * (1 - tm)
    s.tint(1 - 0.35 * shadow)
    s.lay(tm, hexc(fg), rough=0.35, add_height=0.3)
    if imask is not None:
        s.lay(imask, hexc(fg), rough=0.35, add_height=0.3)
        tm = np.maximum(tm, imask)
    if extra.any():
        col = hexc("#fff3c4") if key == "kazino" else hexc(border)
        s.lay(extra, col, rough=0.3, add_height=0.15)
    if key == "nochnoy_klub":
        tube = np.clip(blur(frame, 3) * 1.6, 0, 1) * board
        s.lay(tube, hexc(border))
        s.emission = lerp(s.emission, hexc(border), tube)
    if glow > 0:
        s.emission = lerp(s.emission, hexc(fg) * glow, tm)
        if key == "kazino":
            s.emission = lerp(s.emission, hexc("#fff3c4"), extra)
    # light weathering: dirt from the top edge, sun-faded paint
    grime = fbm(shape, 6, rng, octaves=3)
    s.tint(0.93 + 0.07 * grime)
    s.albedo = lerp(s.albedo, s.albedo.mean(-1, keepdims=True), 0.08)
    return s


@texture("sign_atlas", "signage", (S, S), None, tiling="none", kind="decal_atlas",
         normal_strength=6.0, emission=True, atlas=ATLAS, ao_radius=4.0, ao_amount=2.0,
         notes="12 shop/municipal sign boards (no post office), 2 columns x 6 rows of 1024x340 px "
               "from the top-left; bottom 8 px unused. Use on alpha-clipped quads or as decals; "
               "emission only on signs that glow at night.")
def sign_atlas(name, shape, rng, ctx):
    s = Surface(shape, hexc("#000000"), rough=0.6, height=0.0)
    s.alpha = np.zeros(shape, np.float32)
    s.emission = np.zeros((*shape, 3), np.float32)
    for i, spec in enumerate(SIGNS):
        c = draw_sign(spec, ctx["fonts"], rng)
        y, x = (i // 2) * CH, (i % 2) * CW
        sl = (slice(y, y + CH), slice(x, x + CW))
        s.albedo[sl] = c.albedo
        s.height[sl] = c.height
        s.rough[sl] = c.rough
        s.metal[sl] = c.metal
        s.alpha[sl] = c.alpha
        s.emission[sl] = c.emission
    return s
