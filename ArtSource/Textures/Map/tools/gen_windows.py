"""Window decal atlas: 16 variants in a 4x4 grid (1024 px, 256 px cells)."""
import numpy as np

from registry import texture
from texlib import Surface, box, fbm, grid_coords, hexc, lerp, rect, smoothstep

A = 1024
C = 256
VARIANTS = [
    # name,                 style,      lit,   curtain
    ("soviet_white_bare",   "wood_w",   False, None),
    ("soviet_white_tulle",  "wood_w",   False, "tulle"),
    ("soviet_white_lit",    "wood_w",   True,  "orange"),
    ("soviet_brown_drape",  "wood_b",   False, "brown"),
    ("soviet_brown_lit",    "wood_b",   True,  "tulle"),
    ("pvc_blinds",          "pvc",      False, "blinds"),
    ("pvc_blinds_lit",      "pvc",      True,  "blinds_half"),
    ("pvc_flowers",         "pvc",      False, "flowers"),
    ("boarded_up",          "boarded",  False, None),
    ("broken_dark",         "broken",   False, None),
    ("village_shutters",    "village",  False, "lace"),
    ("village_lit",         "village",  True,  "lace"),
    ("shop_window",         "shop",     False, None),
    ("shop_window_lit",     "shop",     True,  None),
    ("modern_tall",         "modern",   False, None),
    ("modern_tall_lit",     "modern",   True,  "sheer"),
]
ATLAS = [{"name": n, "rect_px": [(i % 4) * C, (i // 4) * C, C, C],
          "uv_rect": [(i % 4) / 4, 1 - (i // 4 + 1) / 4, 0.25, 0.25], "lit": lit}
         for i, (n, _, lit, _) in enumerate(VARIANTS)]

WARM = hexc("#ffd68a")


def glass(u, v, x0, y0, x1, y1, lit, rng_noise):
    if lit:
        g = lerp(hexc("#f7c56e"), hexc("#ffe7b0"), smoothstep(y1, y0, v))
        return g * (0.92 + 0.08 * rng_noise)[..., None]
    t = (u - x0) / (x1 - x0) * 0.7 + (v - y0) / (y1 - y0)
    band = smoothstep(0.22, 0.0, np.abs(t - 0.55))
    return lerp(hexc("#34495a"), hexc("#a9c0cf"), np.clip(band * 0.6 + smoothstep(y1, y0, v) * 0.25, 0, 1))


def draw_cell(style, lit, curtain, rng):
    shape = (C, C)
    u, v = grid_coords(shape)
    n = fbm(shape, 4, rng, octaves=3)
    s = Surface(shape, hexc("#2b2927"), rough=0.6, height=0.3)
    s.alpha = np.zeros(shape, np.float32)
    s.emission = np.zeros((*shape, 3), np.float32)

    # outer opening per style
    if style in ("modern",):
        x0, y0, x1, y1 = 52, 8, 204, 248
    elif style == "shop":
        x0, y0, x1, y1 = 8, 36, 248, 220
    else:
        x0, y0, x1, y1 = 24, 20, 232, 236
    opening = rect(u, v, x0, y0, x1, y1, 1.2)
    s.alpha = opening.copy()

    frame_col = {"wood_w": "#e8e3d8", "wood_b": "#6d4b36", "pvc": "#f5f5f3", "village": "#efe9dc",
                 "shop": "#5a5f63", "modern": "#33373a", "boarded": "#6d4b36",
                 "broken": "#d9d3c4"}[style]
    fw = {"modern": 10, "shop": 10, "pvc": 14}.get(style, 12)
    s.lay(opening, hexc(frame_col), rough=0.55, height=0.65)
    ix0, iy0, ix1, iy1 = x0 + fw, y0 + fw, x1 - fw, y1 - fw
    inner = rect(u, v, ix0, iy0, ix1, iy1, 1)

    # mullions per style
    bars = np.zeros(shape, np.float32)
    if style in ("wood_w", "wood_b", "broken", "pvc"):
        mid = ix0 + (ix1 - ix0) * 0.6
        tr = iy0 + (iy1 - iy0) * 0.3
        bars = np.maximum(box(u, mid - 6, mid + 6, 1), box(v, tr - 5, tr + 5, 1) * (style != "pvc"))
    elif style == "village":
        mid = (ix0 + ix1) / 2
        tr = iy0 + (iy1 - iy0) * 0.33
        bars = np.maximum(box(u, mid - 5, mid + 5, 1), box(v, tr - 4, tr + 4, 1))
    elif style == "modern":
        bars = box(v, iy1 - 70, iy1 - 64, 1)
    elif style == "shop":
        bars = box(u, 124, 132, 1)
    pane = inner * (1 - bars)
    g = glass(u, v, ix0, iy0, ix1, iy1, lit, n)
    rough_g = 0.08

    # curtains behind glass
    if curtain in ("orange", "brown"):
        col = hexc("#d98c3f") if curtain == "orange" else hexc("#7a5238")
        folds = 0.78 + 0.22 * np.sin(u * 0.32)
        side = np.clip(box(u, ix0, ix0 + 60, 18) + box(u, ix1 - 55, ix1, 18), 0, 1)
        c = col * folds[..., None]
        if lit:
            c = c * 1.25 + 0.08
        g = lerp(g, c, side * 0.9)
    elif curtain in ("tulle", "lace", "sheer"):
        pattern = 0.85 + 0.15 * np.sin(u * 0.5) * (np.sin(v * 0.5) if curtain == "lace" else 1)
        lace = hexc("#f2efe6") * pattern[..., None]
        top = smoothstep(iy1, iy0 + 30, v) if curtain == "lace" else np.ones(shape, np.float32)
        g = lerp(g, lace, (0.55 if not lit else 0.45) * top)
    elif curtain in ("blinds", "blinds_half"):
        slats = 0.75 + 0.25 * (np.sin(v * 0.9) > 0)
        cov = np.ones(shape, np.float32) if curtain == "blinds" else smoothstep(iy0 + 110, iy0 + 100, v)
        g = lerp(g, hexc("#e8e4d8") * slats[..., None], cov * 0.92)
    elif curtain == "flowers":
        pots = rect(u, v, ix0 + 18, iy1 - 34, ix0 + 52, iy1 - 4, 1.5) + rect(u, v, ix1 - 70, iy1 - 30, ix1 - 40, iy1 - 4, 1.5)
        leaves = np.clip(1 - (np.hypot(u - (ix0 + 35), v - (iy1 - 52)) / 26), 0, 1) + \
            np.clip(1 - (np.hypot(u - (ix1 - 55), v - (iy1 - 44)) / 20), 0, 1)
        g = lerp(g, hexc("#5f8f4a"), smoothstep(0.0, 0.2, leaves))
        g = lerp(g, hexc("#b5603d"), np.clip(pots, 0, 1))
    s.lay(pane, g, rough=rough_g, height=0.4)
    if lit:
        em = g * WARM * 1.0
        s.emission = lerp(s.emission, em, pane)

    if style == "broken":
        cx, cy = ix0 + 70, iy0 + 120
        ang = np.arctan2(v - cy, u - cx)
        r = np.hypot(u - cx, v - cy)
        crack = (np.abs(np.sin(ang * 5 + 0.3)) < 0.03 + 6 / (r + 30)) * (r < 120)
        hole = (r < 16 + 7 * np.abs(np.sin(ang * 4.5)))
        s.lay(pane * crack, hexc("#e6edf0"), rough=0.3)
        s.lay(pane * hole, hexc("#141414"), rough=0.9, height=0.2)
    if style == "boarded":
        s.lay(inner, hexc("#1e1c1a"), height=0.2)
        planks = np.zeros(shape, np.float32)
        for k, (yc, tilt) in enumerate([(70, 0.08), (128, -0.05), (186, 0.04)]):
            planks = np.maximum(planks, box(v - (u - 128) * tilt, yc - 24, yc + 24, 1.5) * box(u, 14, 242, 1.5))
        grain = fbm(shape, (3, 30), rng, octaves=3)
        s.lay(planks, lerp(hexc("#8a7158"), hexc("#a88d6c"), grain), rough=0.9, height=0.9)
        s.alpha = np.maximum(s.alpha, planks)
        nails = sum(rect(u, v, xn - 3, yc - 3 - (128 - xn) * t, xn + 3, yc + 3 - (128 - xn) * t, 1)
                    for (yc, t) in [(70, 0.08), (128, -0.05), (186, 0.04)] for xn in (28, 228))
        s.lay(nails, hexc("#3b3633"), metal=0.6)
    if style == "village":
        # carved surround + painted shutters (outside the opening, still in the decal)
        sh_l = rect(u, v, 0, y0, x0 + 2, y1, 1.2)
        sh_r = rect(u, v, x1 - 2, y0, C, y1, 1.2)
        shut = np.clip(sh_l + sh_r, 0, 1)
        boards = 0.85 + 0.15 * (np.sin(v * 0.4) > 0.9)
        s.lay(shut, hexc("#3f78a8") * boards[..., None], rough=0.7, height=0.75)
        crown = rect(u, v, 4, 0, 252, y0 + 2, 1.2) * smoothstep(0, 6, 40 - np.abs(u - 128) * 0.25 - (y0 - v))
        s.lay(crown, hexc("#efe9dc"), height=0.8)
        s.alpha = np.clip(s.alpha + shut + crown, 0, 1)
    # sill
    if style in ("wood_w", "wood_b", "pvc", "village", "broken", "boarded"):
        sill = rect(u, v, x0 - 10, y1 - 4, x1 + 10, min(y1 + 14, C), 1.2)
        s.lay(sill, hexc("#d8d6d0"), rough=0.45, height=0.85, metal=0.3)
        s.alpha = np.maximum(s.alpha, sill)
    # gentle dirt on the frame
    s.tint(1 - 0.08 * fbm(shape, 6, rng, octaves=2))
    return s


@texture("window_atlas", "windows", (A, A), None, tiling="none", kind="decal_atlas",
         normal_strength=5.0, emission=True, atlas=ATLAS, ao_radius=4.0, ao_amount=3.0,
         notes="16 window decals, 4x4 grid, row-major from the top-left. Albedo alpha = coverage; "
               "emission only for *_lit cells. Use on URP Decal Projector or as alpha-clipped quads.")
def window_atlas(name, shape, rng, ctx):
    s = Surface(shape, hexc("#000000"), rough=0.6, height=0.3)
    s.alpha = np.zeros(shape, np.float32)
    s.emission = np.zeros((*shape, 3), np.float32)
    for i, (_, style, lit, curtain) in enumerate(VARIANTS):
        c = draw_cell(style, lit, curtain, rng)
        y, x = (i // 4) * C, (i % 4) * C
        sl = (slice(y, y + C), slice(x, x + C))
        s.albedo[sl] = c.albedo
        s.height[sl] = c.height
        s.rough[sl] = c.rough
        s.metal[sl] = c.metal
        s.alpha[sl] = np.clip(c.alpha, 0, 1)
        s.emission[sl] = c.emission
    return s
