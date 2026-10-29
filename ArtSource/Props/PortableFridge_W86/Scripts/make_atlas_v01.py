"""PortableFridge_W86 v01 - colour atlas generator (PIL, offline, no downloads).

Palette follows COOLER-ASTRA-001 (white body, blue lid, navy hardware) with a
worn finish. The sticker repeats the approved COOLER design (biohazard symbol,
"ОРГАНЫ / НЕ КАНТОВАТЬ"); symbol drawn procedurally, text typeset with Arial Bold.

Usage: python make_atlas_v01.py  ->  ../Textures/PortableFridge_W86_Atlas_v01.png
                                     ../Textures/PortableFridge_W86_Atlas_v01_cells.json
"""
import json, math, os, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, "..", "Textures"))
SIZE = 1024
rng = random.Random(8642)

# cell rects in PIL pixels (x0, y0, x1, y1); UV conversion in the json
CELLS = {
    "BODY_WHITE": (0, 0, 512, 512),
    "LID_BLUE": (512, 0, 1024, 512),
    "STICKER": (0, 512, 420, 832),
    "TAPE": (420, 512, 512, 832),
    "LINER": (512, 512, 768, 768),
    "NAVY": (768, 512, 896, 640),
    "RUBBER": (896, 512, 1024, 640),
    "METAL": (768, 640, 896, 768),
    "DIVIDER": (896, 640, 1024, 768),
    "HAZARD": (0, 832, 512, 1024),
    "STEEL": (512, 768, 768, 1024),
    "YELLOW": (768, 768, 896, 896),
    "BLUE_SOLID": (896, 768, 1024, 896),
    "MARKER": (768, 896, 1024, 1024),
}

WHITE = (219, 221, 219)
BLUE = (46, 106, 193)
NAVY = (42, 61, 94)
LINER = (203, 212, 220)
RUBBER = (40, 42, 46)
METAL = (168, 172, 176)
DIVIDER = (228, 232, 236)
STEEL = (74, 78, 84)
YELLOW = (226, 176, 38)


def clamp(v):
    return max(0, min(255, int(round(v))))


def noise_layer(w, h, scale, amp, seed):
    """Smooth value noise as an 'L' image centred on 128."""
    r = random.Random(seed)
    sw, sh = max(2, w // scale), max(2, h // scale)
    small = Image.new("L", (sw, sh))
    small.putdata([clamp(128 + r.uniform(-amp, amp)) for _ in range(sw * sh)])
    return small.resize((w, h), Image.BICUBIC)


def tinted(w, h, base, layers):
    """Base colour modulated by a list of (scale, amp, seed) noise layers."""
    img = Image.new("RGB", (w, h), base)
    px = img.load()
    ns = [noise_layer(w, h, s, a, sd).load() for s, a, sd in layers]
    for y in range(h):
        for x in range(w):
            d = sum(n[x, y] - 128 for n in ns)
            c = px[x, y]
            px[x, y] = (clamp(c[0] + d), clamp(c[1] + d), clamp(c[2] + d))
    return img


def scuffs(draw, w, h, n, col, lw=(1, 2), length=(6, 30)):
    for _ in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        a = rng.uniform(0, math.pi)
        L = rng.uniform(*length)
        draw.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=col,
                  width=rng.randint(*lw))


def edge_wear(img, width, col, strength):
    """Blend col towards the cell border (box-projected edges = model edges)."""
    w, h = img.size
    px = img.load()
    for y in range(h):
        for x in range(w):
            d = min(x, y, w - 1 - x, h - 1 - y)
            if d < width:
                t = strength * (1 - d / width) ** 2 * (0.6 + 0.4 * rng.random())
                c = px[x, y]
                px[x, y] = tuple(clamp(c[i] * (1 - t) + col[i] * t) for i in range(3))


def body_white():
    w, h = 512, 512
    img = tinted(w, h, WHITE, [(64, 5, 1), (8, 2, 2)])
    px = img.load()
    # bottom grime: PIL y grows downward; cell bottom = model bottom
    for y in range(h):
        t = max(0.0, (y - h * 0.60) / (h * 0.40))
        t = t * t * 0.55
        for x in range(w):
            c = px[x, y]
            g = (166, 158, 140)
            px[x, y] = tuple(clamp(c[i] * (1 - t) + g[i] * t) for i in range(3))
    d = ImageDraw.Draw(img)
    scuffs(d, w, h, 120, (194, 195, 191))
    scuffs(d, w, h, 25, (178, 176, 170), lw=(1, 3), length=(4, 14))
    for _ in range(40):  # tiny chips/dirt dots
        x, y, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.8, 2.2)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(160, 158, 150))
    edge_wear(img, 28, (160, 154, 140), 0.65)
    return img.filter(ImageFilter.GaussianBlur(0.6))


def lid_blue():
    w, h = 512, 512
    img = tinted(w, h, BLUE, [(48, 7, 3), (8, 2, 4)])
    d = ImageDraw.Draw(img)
    # sun-faded patch on the top
    fade = Image.new("L", (w, h), 0)
    ImageDraw.Draw(fade).ellipse([60, 40, 420, 330], fill=70)
    fade = fade.filter(ImageFilter.GaussianBlur(60))
    img = Image.composite(Image.new("RGB", (w, h), (92, 140, 210)), img, fade)
    d = ImageDraw.Draw(img)
    scuffs(d, w, h, 130, (98, 146, 214))
    scuffs(d, w, h, 25, (150, 180, 222), lw=(1, 2), length=(3, 10))
    edge_wear(img, 22, (150, 180, 224), 0.7)
    return img.filter(ImageFilter.GaussianBlur(0.6))


def liner():
    w, h = 256, 256
    img = tinted(w, h, LINER, [(32, 4, 5), (6, 2, 6)])
    st = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(st)
    for _ in range(9):  # faint old stains (pink-brown), mostly lower half
        x, y = rng.uniform(10, w - 10), rng.uniform(h * 0.45, h - 8)
        rx, ry = rng.uniform(8, 26), rng.uniform(5, 14)
        sd.ellipse([x - rx, y - ry, x + rx, y + ry], fill=rng.randint(35, 70))
    st = st.filter(ImageFilter.GaussianBlur(5))
    img = Image.composite(Image.new("RGB", (w, h), (170, 132, 128)), img, st)
    d = ImageDraw.Draw(img)
    scuffs(d, w, h, 30, (188, 196, 204))
    edge_wear(img, 14, (176, 180, 182), 0.35)
    return img


def solid(w, h, col, amp=4, seed=9):
    return tinted(w, h, col, [(16, amp, seed)])


def steel():
    w, h = 256, 256
    img = tinted(w, h, STEEL, [(32, 4, 11), (4, 3, 12)])
    d = ImageDraw.Draw(img)
    scuffs(d, w, h, 60, (118, 122, 128), lw=(1, 1), length=(5, 30))
    scuffs(d, w, h, 12, (150, 152, 154), lw=(1, 2), length=(3, 9))
    for _ in range(10):  # rust freckles
        x, y, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(1, 3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(112, 78, 52))
    edge_wear(img, 12, (128, 130, 134), 0.5)
    return img


def hazard():
    w, h = 512, 192
    img = Image.new("RGB", (w, h), YELLOW)
    d = ImageDraw.Draw(img)
    step = 64
    for k in range(-4, w // step + 6):
        x0 = k * step
        d.polygon([(x0, h), (x0 + 32, h), (x0 + 32 + h, 0), (x0 + h, 0)], fill=(28, 28, 30))
    img = Image.blend(img, tinted(w, h, (128, 128, 128), [(24, 10, 13)]), 0.12)
    d = ImageDraw.Draw(img)
    scuffs(d, w, h, 40, (160, 150, 120), lw=(1, 2), length=(4, 16))
    return img


def tape():
    """Duct-tape patch drawn over lid blue so its torn ends blend into the lid."""
    w, h = 92, 320
    img = lid_blue().resize((w, h))
    t = tinted(w, h, (150, 152, 154), [(6, 6, 14), (2, 4, 15)])
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    pts = [(10, 18)]
    for i in range(1, 7):
        pts.append((10 + i * 12, 12 + rng.uniform(-6, 8)))
    pts.append((w - 10, 18))
    for i in range(1, 7):
        pts.append((w - 10, 18 + i * 40 + rng.uniform(-2, 2)))
    pts.append((w - 10, h - 18))
    for i in range(6, 0, -1):
        pts.append((10 + i * 12, h - 12 + rng.uniform(-8, 6)))
    pts.append((10, h - 18))
    md.polygon(pts, fill=255)
    img.paste(t, (0, 0), m)
    d = ImageDraw.Draw(img)
    for y in range(24, h - 24, 7):  # fabric weave lines
        d.line([(12, y), (w - 12, y)], fill=(138, 140, 142), width=1)
    return img


def biohazard(size):
    """Biohazard trefoil on transparent RGBA, black, drawn at 4x then reduced."""
    S = size * 4
    u = S / 56.0
    c = S / 2.0
    img = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(img)
    dirs = [math.radians(a) for a in (90, 210, 330)]

    def circ(cx, cy, r, f):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=f)

    def P(a, dist):
        return c + dist * u * math.cos(a), c - dist * u * math.sin(a) + 2.5 * u

    for a in dirs:  # outer discs
        x, y = P(a, 11.0)
        circ(x, y, 15.0 * u, 255)
    for a in dirs:  # inner cut-outs (open outwards)
        x, y = P(a, 16.0)
        circ(x, y, 10.2 * u, 0)
    # ring visible only inside the cut-outs, with a thin white gap
    ring = Image.new("L", (S, S), 0)
    rd = ImageDraw.Draw(ring)
    cx, cy = P(0, 0)
    rd.ellipse([cx - 18.0 * u, cy - 18.0 * u, cx + 18.0 * u, cy + 18.0 * u], fill=255)
    rd.ellipse([cx - 15.0 * u, cy - 15.0 * u, cx + 15.0 * u, cy + 15.0 * u], fill=0)
    holes = Image.new("L", (S, S), 0)
    hd = ImageDraw.Draw(holes)
    for a in dirs:
        x, y = P(a, 16.0)
        r = 10.2 * u - 1.1 * u
        hd.ellipse([x - r, y - r, x + r, y + r], fill=255)
    ring_in = Image.composite(ring, Image.new("L", (S, S), 0), holes)
    img = Image.composite(Image.new("L", (S, S), 255), img, ring_in)
    d = ImageDraw.Draw(img)
    # centre hole and three slits
    circ(cx, cy, 3.4 * u, 0)
    for a in dirs:
        x, y = P(a, 7.0)
        d.line([(cx, cy), (x, y)], fill=0, width=int(1.3 * u))
    img = img.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (20, 20, 22, 0))
    out.putalpha(img)
    return out


def sticker():
    w, h = 420, 320
    img = Image.new("RGB", (w, h), WHITE)  # cell background = body white
    lab = Image.new("RGB", (w, h), (240, 241, 240))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([6, 6, w - 7, h - 7], radius=22, fill=255)
    img.paste(lab, (0, 0), m)
    sym = biohazard(178)
    img.paste(sym, ((w - 178) // 2, 14), sym)
    d = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 50)
    f2 = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 34)
    for txt, f, y in (("ОРГАНЫ", f1, 200), ("НЕ КАНТОВАТЬ", f2, 258)):
        bb = d.textbbox((0, 0), txt, font=f)
        tw = bb[2] - bb[0]
        d.text(((w - tw) / 2 - bb[0], y), txt, font=f, fill=(22, 22, 24))
    # wear: scratches through the print and a lifted corner shadow
    scuffs(d, w, h, 14, (214, 214, 212), lw=(1, 2), length=(5, 26))
    d.line([(w - 40, h - 8), (w - 9, h - 36)], fill=(196, 196, 192), width=3)
    return img


def marker():
    return Image.new("RGB", (256, 128), (60, 200, 110))


def main():
    os.makedirs(TEX, exist_ok=True)
    atlas = Image.new("RGB", (SIZE, SIZE), (128, 128, 128))
    parts = {
        "BODY_WHITE": body_white(), "LID_BLUE": lid_blue(), "STICKER": sticker(),
        "TAPE": tape(), "LINER": liner(), "NAVY": solid(128, 128, NAVY, 4, 21),
        "RUBBER": solid(128, 128, RUBBER, 3, 22), "METAL": solid(128, 128, METAL, 6, 23),
        "DIVIDER": solid(128, 128, DIVIDER, 3, 24), "HAZARD": hazard(), "STEEL": steel(),
        "YELLOW": solid(128, 128, YELLOW, 5, 25), "BLUE_SOLID": solid(128, 128, BLUE, 4, 26),
        "MARKER": marker(),
    }
    for k, (x0, y0, x1, y1) in CELLS.items():
        im = parts[k]
        if im.size != (x1 - x0, y1 - y0):
            im = im.resize((x1 - x0, y1 - y0), Image.LANCZOS)
        atlas.paste(im, (x0, y0))
    path = os.path.join(TEX, "PortableFridge_W86_Atlas_v01.png")
    if os.path.exists(path):
        raise SystemExit("refusing to overwrite " + path)
    atlas.save(path)
    cells_uv = {k: [x0 / SIZE, 1 - y1 / SIZE, x1 / SIZE, 1 - y0 / SIZE]
                for k, (x0, y0, x1, y1) in CELLS.items()}
    with open(os.path.join(TEX, "PortableFridge_W86_Atlas_v01_cells.json"), "w", encoding="utf-8") as f:
        json.dump({"size": SIZE, "uv_rect_order": "u0 v0 u1 v1 (Blender UV, origin bottom-left)",
                   "cells": cells_uv}, f, indent=1)
    print("wrote", path)


if __name__ == "__main__":
    main()
