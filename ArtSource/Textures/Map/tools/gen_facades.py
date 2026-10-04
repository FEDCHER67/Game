"""Facade textures (2048 px): panel slab, bricks, plaster, planks, mansion, metal."""
import numpy as np

from registry import texture
from texlib import (Surface, blur, box, cell_table, fbm, grid_coords, hexc, lerp, rect,
                    smoothstep)

F = 2048


def streaks(shape, rng, density=48, length=3):
    """Vertical rain/dirt streaks: thin in x, long in y (0..1)."""
    s = fbm(shape, (density, length), rng, octaves=3)
    return smoothstep(0.55, 0.95, s)


def glass_color(xx, yy, x0, y0, x1, y1, base="#3c5468", sky="#9fb8c8"):
    """Stylised glass: dark base with a soft diagonal sky reflection band."""
    u = (xx - x0) / np.maximum(x1 - x0, 1)
    v = (yy - y0) / np.maximum(y1 - y0, 1)
    band = smoothstep(0.25, 0.0, np.abs((u * 0.7 + v) - 0.55)) * 0.6
    top = np.clip(1.0 - v, 0, 1) * 0.35
    return lerp(lerp(hexc(base), hexc(sky), np.clip(band + top, 0, 1)), hexc(base), 0.0)


# ------------------------------------------------------------------ Soviet panel slab

@texture("facade_panel_slab", "facades", (F, F), (12.0, 12.0), normal_strength=12.0,
         notes="4x4 window bays (3 m each). Seams with black mastic, balcony stack in "
               "column 2, two glazed balconies, sill streaks. For 5/9-storey blocks.")
def panel_slab(name, shape, rng, ctx):
    h, w = shape
    xx, yy = grid_coords(shape)
    cs = 512
    cx = (xx // cs).astype(int)
    cy = (yy // cs).astype(int)
    u = xx % cs
    v = yy % cs
    s = Surface(shape, hexc("#c9c2b2"), rough=0.85, height=0.6)

    # panel-by-panel tint (classic patchwork of slightly different concrete batches)
    tint = cell_table(rng, (4, 4))
    panel_col = lerp(hexc("#cbc4b4"), hexc("#b8b4aa"), tint[cy, cx])
    lowf = fbm(shape, 4, rng, octaves=3)
    s.albedo = panel_col * (0.92 + 0.12 * lowf)[..., None]
    # pebble-dash finish: very soft, low contrast
    s.height += 0.02 * fbm(shape, 64, rng, octaves=2)

    # seams + black mastic
    seam = np.maximum(1 - box(u, 7, cs - 7, 2.5), 1 - box(v, 7, cs - 7, 2.5))
    mastic_wobble = fbm(shape, (16, 16), rng, octaves=3)
    mastic = np.maximum(1 - box(u, 11 + 6 * mastic_wobble, cs - 11 - 6 * mastic_wobble, 3),
                        1 - box(v, 11 + 6 * mastic_wobble, cs - 11 - 6 * mastic_wobble, 3))
    s.lay(mastic * 0.85, hexc("#3a3836"), rough=0.6)
    s.lay(seam, hexc("#5e5a54"), height=0.35)

    # balconies: column 2 full stack, two glazed cells, one random extra
    balcony = np.zeros((4, 4), bool)
    balcony[:, 2] = True
    glazed = np.zeros((4, 4), bool)
    glazed[1, 2] = glazed[3, 2] = True
    frame_kind = (cell_table(rng, (4, 4)) * 3).astype(int)   # 0 white wood, 1 brown wood, 2 PVC
    curtain = cell_table(rng, (4, 4))
    curtain_col = np.array([hexc("#d9c27a"), hexc("#b36a4e"), hexc("#e9e4d6"), hexc("#7f9a76")])
    curtain_pick = (cell_table(rng, (4, 4)) * 4).astype(int)

    # window opening
    wx0, wx1, wy0, wy1 = 136, 376, 112, 360
    win = rect(u, v, wx0, wy0, wx1, wy1, 1.5)
    s.lay(win, hexc("#2c2a28"), height=0.25)
    # reveal shadow at top/left of opening
    reveal = rect(u, v, wx0, wy0, wx1, wy0 + 14, 1.5) + rect(u, v, wx0, wy0, wx0 + 10, wy1, 1.5)
    s.tint(1 - 0.25 * np.clip(reveal, 0, 1) * win)
    fx0, fx1, fy0, fy1 = wx0 + 10, wx1 - 6, wy0 + 12, wy1 - 6
    frame_area = rect(u, v, fx0, fy0, fx1, fy1, 1)
    fk = frame_kind[cy, cx]
    frame_col = np.where((fk == 1)[..., None], hexc("#6b4a36"),
                         np.where((fk == 0)[..., None], hexc("#e6e1d6"), hexc("#f4f4f2")))
    s.lay(frame_area, frame_col, rough=0.55, height=0.32)
    # panes: left 2/3 split by transom, right narrow casement + fortochka
    mid = fx0 + (fx1 - fx0) * 0.62
    tr = fy0 + (fy1 - fy0) * 0.3
    f = 9
    panes = (rect(u, v, fx0 + f, fy0 + f, mid - f / 2, tr - f / 2) +
             rect(u, v, fx0 + f, tr + f / 2, mid - f / 2, fy1 - f) +
             rect(u, v, mid + f / 2, fy0 + f, fx1 - f, tr - f / 2) +
             rect(u, v, mid + f / 2, tr + f / 2, fx1 - f, fy1 - f))
    panes = np.clip(panes, 0, 1) * frame_area
    gl = glass_color(u, v, fx0, fy0, fx1, fy1)
    # curtains behind glass (vertical folds)
    folds = 0.8 + 0.2 * np.sin(u * 0.35)
    has_cur = (curtain[cy, cx] > 0.35)
    cur_side = np.clip(box(u, fx0, fx0 + 70, 20) + box(u, mid - 40, fx1, 25) * (curtain[cy, cx] > 0.7), 0, 1)
    cur_rgb = curtain_col[curtain_pick[cy, cx]] * folds[..., None]
    gl = lerp(gl, cur_rgb, (cur_side * has_cur * 0.75))
    s.lay(panes, gl, rough=0.08, height=0.28)
    # sill (tin flashing, light) + streaks from the corners
    sill = rect(u, v, wx0 - 8, wy1, wx1 + 8, wy1 + 12, 1.5)
    s.lay(sill, hexc("#d8d6d0"), rough=0.45, height=0.72, metal=0.4)
    drip = streaks(shape, rng, 96, 4) * box(u, wx0 - 4, wx1 + 4, 20) * smoothstep(wy1 + 12, wy1 + 20, v)
    drip *= np.exp(-np.maximum(v - wy1, 0) / 110.0)
    s.tint(1 - 0.22 * drip)
    s.lay(drip * 0.6, rough=0.95)

    # balcony slab + parapet (only lower part of the bay, under the window)
    bal = balcony[cy, cx]
    par = rect(u, v, 36, 330, cs - 36, 500, 1.5) * bal
    ribs = 0.5 + 0.5 * np.sin((u - 36) / 22.0 * np.pi)
    par_col = lerp(hexc("#d2ccc0"), hexc("#bdb7ab"), ribs)
    s.lay(par, par_col, rough=0.85, height=0.85)
    s.height += par * 0.03 * ribs
    slab = rect(u, v, 28, 494, cs - 28, 512, 1.5) * bal
    s.lay(slab, hexc("#a9a397"), height=0.9)
    # soft shadow under the slab, on the panel below (cy+1): v in 0..40 of the next cell
    above_bal = balcony[(cy - 1) % 4, cx]
    shadow = box(u, 28, cs - 28, 18) * np.exp(-v / 26.0) * above_bal
    s.tint(1 - 0.35 * shadow)
    # parapet top rust streaks from rail fixings
    rust = streaks(shape, rng, 128, 6) * par * smoothstep(330, 350, v) * np.exp(-(v - 330) / 90.0)
    s.lay(rust * 0.5, hexc("#8a5a3c"), rough=0.9)

    # glazed balconies: aluminium/wood frames above the parapet, mismatched cladding
    gz = glazed[cy, cx]
    gzone = rect(u, v, 36, 40, cs - 36, 330, 1.5) * gz
    gframe_x = np.abs(((u - 36) % 73) - 36.5) > 31
    gframe_y = (np.abs(v - 40) < 7) | (np.abs(v - 330) < 7) | (np.abs(v - 130) < 5)
    gframe = gzone * (gframe_x | gframe_y)
    gpane = gzone * (1 - gframe)
    s.lay(gpane, glass_color(u, v, 36, 40, cs - 36, 330, "#4a6476", "#b9ccd8"), rough=0.08, height=0.95)
    s.lay(gframe, hexc("#ebe8e0"), rough=0.5, height=1.0)
    # profiled sheet cladding on glazed parapets
    clad = rect(u, v, 36, 330, cs - 36, 500, 1.5) * gz
    prof = 0.5 + 0.5 * np.sign(np.sin(u / 9.0))
    s.lay(clad, lerp(hexc("#8fa2a8"), hexc("#7c8f96"), prof), rough=0.55, metal=0.3)

    # global weathering: soot streaks and low-frequency grime
    st = streaks(shape, rng, 40, 2)
    s.tint(1 - 0.12 * st)
    grime = fbm(shape, 3, rng, octaves=2)
    s.tint(0.94 + 0.08 * grime)
    s.rough = np.clip(s.rough + 0.05 * st, 0, 1)
    return s


# ------------------------------------------------------------------ bricks

def brick_wall(shape, rng, rows, cols, palette, joint_col, joint_px, bevel=5.0,
               chip=0.2, header_every=0):
    h, w = shape
    xx, yy = grid_coords(shape)
    ch = h / rows
    cw = w / cols
    row = np.floor(yy / ch).astype(int)
    off = (row % 2) * 0.5 * cw
    if header_every:
        # Soviet "chain" bond: every Nth course is headers (half bricks)
        hdr = (row % header_every) == 0
        cw_r = np.where(hdr, cw / 2, cw)
        off = np.where(hdr, cw / 4, off)
    else:
        cw_r = np.full(shape, cw, np.float32)
    lx = (xx + off) % cw_r
    ly = yy - row * ch
    col = np.floor(((xx + off) % w) / cw_r).astype(int)
    d = np.minimum(np.minimum(lx, cw_r - lx), np.minimum(ly, ch - ly))
    edge_noise = fbm(shape, 48, rng, octaves=3)
    d = d - chip * 6 * smoothstep(0.6, 1.0, edge_noise)
    body = smoothstep(joint_px / 2, joint_px / 2 + 1.5, d)
    shape_h = np.clip((d - joint_px / 2) / bevel, 0, 1)
    shape_h = np.sqrt(shape_h)
    pick = cell_table(rng, (rows, cols * 2 + 2))
    var = cell_table(rng, (rows, cols * 2 + 2))
    idx = (row % rows, col % (cols * 2 + 2))
    pal = np.array(palette, np.float32)
    k = np.minimum((pick[idx] * len(pal)).astype(int), len(pal) - 1)
    bcol = pal[k] * (0.9 + 0.2 * var[idx])[..., None]
    s = Surface(shape, joint_col, rough=0.95, height=0.2)
    low = fbm(shape, 6, rng, octaves=3)
    bcol = bcol * (0.93 + 0.1 * low)[..., None]
    s.lay(body, bcol, rough=0.85)
    s.height = 0.2 + 0.6 * shape_h * body + 0.04 * fbm(shape, 32, rng, octaves=2) * body
    return s, body, (row, col)


@texture("facade_brick_soviet", "facades", (F, F), (4.0, 4.0), normal_strength=5.0,
         notes="Pale silicate brick of Khrushchyovka 5-storeys; chain bond, grey joints.")
def brick_soviet(name, shape, rng, ctx):
    pal = [hexc("#d8d3c6"), hexc("#cfc9bb"), hexc("#e0dccf"), hexc("#c4bdae"), hexc("#d4c7b0")]
    s, body, _ = brick_wall(shape, rng, 54, 16, pal, hexc("#8f8b84"), 6, header_every=6)
    st = streaks(shape, rng, 36, 2)
    s.tint(1 - 0.1 * st)
    s.tint(0.95 + 0.07 * fbm(shape, 3, rng, octaves=2))
    return s


@texture("facade_brick_factory_red", "facades", (F, F), (4.0, 4.0), normal_strength=5.5,
         notes="Red pre-war factory brick: dark joints, soot, efflorescence, patched bricks.")
def brick_factory(name, shape, rng, ctx):
    pal = [hexc("#9a4a35"), hexc("#a8553b"), hexc("#8a3f2e"), hexc("#b0644a"), hexc("#7a3a2c")]
    s, body, (row, col) = brick_wall(shape, rng, 48, 15, pal, hexc("#4a433e"), 8, bevel=7, chip=0.45)
    # replaced bricks: a few lighter, newer ones
    rep = cell_table(rng, (48, 32))[row % 48, col % 32] > 0.96
    s.lay(body * rep, hexc("#c27a5a"))
    soot = smoothstep(0.45, 0.9, fbm(shape, 3, rng, octaves=3))
    s.tint(1 - 0.35 * soot)
    st = streaks(shape, rng, 30, 2)
    s.tint(1 - 0.18 * st)
    eff = smoothstep(0.7, 0.95, fbm(shape, 8, rng, octaves=3)) * (1 - body)
    eff = blur(eff, 3)
    s.lay(np.clip(eff * 1.5, 0, 0.7), hexc("#d9d5cb"))
    return s


# ------------------------------------------------------------------ plaster (6 tints)

PLASTER_TINTS = {
    "ochre": "#e3c27c", "salmon": "#e2a28e", "mint": "#a9d1b4",
    "skyblue": "#a7c4dc", "cream": "#ece0c2", "lilac": "#c4b2d6",
}


def make_plaster(tint_hex, salt):
    def gen(name, shape, rng, ctx):
        h, w = shape
        base = hexc(tint_hex)
        s = Surface(shape, base, rough=0.9, height=0.7)
        low = fbm(shape, 3, rng, octaves=3)
        mid = fbm(shape, 12, rng, octaves=3)
        s.albedo = lerp(base * 0.9, np.minimum(base * 1.08, 1), low)
        s.albedo = s.albedo * (0.97 + 0.05 * mid)[..., None]
        # soft trowel strokes
        trowel = fbm(shape, (6, 18), rng, octaves=3)
        s.height += 0.04 * trowel
        # chipping: plaster falls off, revealing red/grey brick underneath
        chips = fbm(shape, 5, rng, octaves=5, gain=0.55)
        hole = smoothstep(0.80, 0.83, chips)
        rim = smoothstep(0.75, 0.80, chips) * (1 - hole)
        bpal = [hexc("#a35a42"), hexc("#b4694c"), hexc("#94503b")]
        bs, bbody, _ = brick_wall(shape, rng, 52, 16, bpal, hexc("#8d857a"), 6, chip=0.4)
        s.lay(hole, None, rough=0.9)
        s.albedo = lerp(s.albedo, bs.albedo, hole)
        s.height = lerp(s.height, bs.height * 0.4, hole)
        s.lay(rim, np.minimum(base * 1.12 + 0.05, 1))   # fresh broken plaster edge
        # grime: streaks and bottom-heavy dirt is not tileable, so keep it uniform
        st = streaks(shape, rng, 44, 2)
        s.tint(1 - 0.05 * st)
        s.tint(0.95 + 0.06 * fbm(shape, 2, rng, octaves=2))
        return s
    return gen


for _i, (_tname, _hex) in enumerate(PLASTER_TINTS.items()):
    texture(f"facade_plaster_{_tname}", "facades", (F, F), (4.0, 4.0), normal_strength=5.0,
            notes="Old-town townhouse plaster, chipped to brick. One of 6 pastel tints.")(
        make_plaster(_hex, _i))


# ------------------------------------------------------------------ rural planks

@texture("facade_wood_planks", "facades", (F, F), (3.0, 3.0), normal_strength=7.0,
         notes="Village clapboard, faded blue-green paint worn to grey wood; nails every 0.6 m.")
def wood_planks(name, shape, rng, ctx):
    h, w = shape
    xx, yy = grid_coords(shape)
    boards = 20
    bh = h / boards
    row = np.floor(yy / bh).astype(int)
    ly = (yy - row * bh) / bh            # 0 top .. 1 bottom of board
    # butt joints: 1-2 per row at random x
    j1 = cell_table(rng, (boards,))[row] * w
    j2 = (cell_table(rng, (boards,))[row] * 0.5 + 0.25) * w + j1
    dj = np.minimum(np.abs(((xx - j1 + w / 2) % w) - w / 2), np.abs(((xx - j2 + w / 2) % w) - w / 2))
    has2 = cell_table(rng, (boards,))[row] > 0.5
    dj = np.where(has2, dj, np.abs(((xx - j1 + w / 2) % w) - w / 2))
    joint = 1 - smoothstep(1.5, 3.5, dj)
    s = Surface(shape, hexc("#8d8a80"), rough=0.85)
    # clapboard wedge profile: thicker at the bottom, crisp shadow under each board
    s.height = 0.3 + 0.55 * ly - 0.5 * smoothstep(0.93, 1.0, ly)
    s.height -= 0.15 * joint
    # grain
    gnoise = fbm(shape, (3, 40), rng, octaves=3)
    grain = 0.5 + 0.5 * np.sin(gnoise * 40 + yy * 0.09)
    wood = lerp(hexc("#7b7468"), hexc("#a39b8b"), grain * 0.7 + 0.3 * gnoise)
    s.height += 0.03 * grain
    paint = lerp(hexc("#6f9e9a"), hexc("#8db6ae"), fbm(shape, 4, rng, octaves=3))
    wear = fbm(shape, (8, 30), rng, octaves=4)
    worn = smoothstep(0.70, 0.78, wear + 0.2 * smoothstep(0.75, 1.0, ly))
    s.albedo = lerp(paint, wood, worn)
    s.rough = lerp(np.full(shape, 0.7, np.float32), np.full(shape, 0.92, np.float32), worn)
    s.tint(1 - 0.35 * smoothstep(0.92, 1.0, ly))
    s.tint(1 - 0.4 * joint)
    nails = rect(((xx + 20) % (w / 5)), ly * bh, 0, bh * 0.75, 7, bh * 0.75 + 7, 1)
    s.lay(nails, hexc("#4d4744"), rough=0.6, metal=0.5)
    st = streaks(shape, rng, 50, 3)
    s.tint(1 - 0.1 * st)
    return s


# ------------------------------------------------------------------ mansion render

@texture("facade_mansion_render", "facades", (F, F), (8.0, 8.0), normal_strength=4.0,
         notes="Elite hill villa: white render, floor-to-ceiling glazing in anthracite frames, "
               "larch slat panel in the right bay, stone slab band between floors.")
def mansion(name, shape, rng, ctx):
    h, w = shape
    xx, yy = grid_coords(shape)
    cs = 1024
    cx = (xx // cs).astype(int)
    u = xx % cs
    v = yy % cs
    s = Surface(shape, hexc("#f1eee8"), rough=0.75, height=0.6)
    s.albedo = s.albedo * (0.97 + 0.04 * fbm(shape, 3, rng, octaves=3))[..., None]
    s.height += 0.015 * fbm(shape, 48, rng, octaves=2)
    # slab band
    band = 1 - box(v, 24, cs - 64, 1.5)
    s.lay(band, hexc("#c9c3b8"), rough=0.6, height=0.7)
    s.lay(box(v, cs - 66, cs - 60, 1.5), hexc("#8d877e"), height=0.5)
    # big glazing
    right = (cx == 1)
    wx0 = np.where(right, 120, 140)
    wx1 = np.where(right, 640, 884)
    win = rect(u, v, wx0, 130, wx1, cs - 90, 1.5)
    s.lay(win, hexc("#34383c"), rough=0.4, height=0.45, metal=0.6)
    fw = 16
    inner = rect(u, v, wx0 + fw, 130 + fw, wx1 - fw, cs - 90 - fw, 1)
    nm = np.where(right, 2, 3)
    pitch = (wx1 - wx0) / nm
    md = (u - wx0) % pitch
    mull = np.minimum(md, pitch - md) < fw * 0.6
    transom = np.abs(v - (cs - 90 - 230)) < fw * 0.5
    pane = inner * (1 - mull) * (1 - transom)
    gl = glass_color(u, v, wx0, 130, wx1, cs - 90, "#2f4a5e", "#c6dae6")
    s.lay(pane, gl, rough=0.04, height=0.4, metal=0.0)
    # glass balustrade reflection strip at the bottom
    s.lay(pane * box(v, cs - 90 - 228, cs - 90 - fw, 1) * 0.25, hexc("#e2eef2"))
    # larch slats beside the narrower window
    slat_zone = rect(u, v, 700, 110, cs - 60, cs - 70, 1.5) * right
    slat = np.abs(((u - 700) % 28) - 14) < 10
    larch = lerp(hexc("#a0714c"), hexc("#c08d60"), fbm(shape, (6, 60), rng, octaves=3))
    s.lay(slat_zone, hexc("#3a3027"), height=0.4)
    s.lay(slat_zone * slat, larch, rough=0.7, height=0.75)
    # very light rain shadow under sills only
    under = box(u, wx0, wx1, 30) * box(v, cs - 90, cs - 64, 3)
    s.tint(1 - 0.12 * under)
    return s


# ------------------------------------------------------------------ corrugated metal

@texture("facade_corrugated_metal", "facades", (F, F), (4.0, 4.0), normal_strength=10.0,
         notes="Industrial profiled sheet: faded blue-grey paint, one galvanised replacement "
               "sheet, lap joints with bolts, rust streaks. Metallic varies by area.")
def corrugated(name, shape, rng, ctx):
    h, w = shape
    xx, yy = grid_coords(shape)
    ripples = 48
    pitch = w / ripples
    prof = 0.5 + 0.5 * np.sin(xx / pitch * 2 * np.pi)
    sheet_w = w / 4                       # 1 m sheets, 2 m tall
    sx = (xx // sheet_w).astype(int)
    sy = (yy // (h / 2)).astype(int)
    lap_y = yy % (h / 2)
    kind = np.array([[0, 0, 1, 0], [0, 2, 0, 0]])[sy % 2, sx % 4]   # 0 paint, 1 galvanised, 2 repaint
    s = Surface(shape, hexc("#7f97a6"), rough=0.55, height=0.5)
    paint = lerp(hexc("#7893a3"), hexc("#94aab6"), fbm(shape, 4, rng, octaves=3))
    galv = lerp(hexc("#a9adae"), hexc("#c6c9c8"), fbm(shape, 6, rng, octaves=3))
    repaint = lerp(hexc("#6b8a88"), hexc("#7f9c96"), fbm(shape, 4, rng, octaves=3))
    s.albedo = np.where((kind == 1)[..., None], galv, np.where((kind == 2)[..., None], repaint, paint))
    s.metal = np.where(kind == 1, 0.85, 0.25).astype(np.float32)
    s.rough = np.where(kind == 1, 0.38, 0.55).astype(np.float32)
    s.height = 0.25 + 0.6 * prof
    # sheet overlaps
    lap = 1 - smoothstep(0, 10, lap_y)
    s.height += 0.08 * lap
    s.tint(1 - 0.35 * (1 - smoothstep(0, 5, lap_y)))
    # bolts on crests along the laps
    crest = ((xx / pitch) % 1.0)
    bolt = (np.abs(crest - 0.25) < 0.07) * box(lap_y, 14, 24, 1) * (((xx // pitch).astype(int) % 2) == 0)
    s.lay(bolt, hexc("#55585a"), height=1.0, metal=0.7, rough=0.5)
    # rust: streaks from bolts + patches in valleys
    rs = fbm(shape, (ripples, 3), rng, octaves=3)
    rust_streak = smoothstep(0.55, 0.95, rs) * np.exp(-np.maximum(lap_y - 24, 0) / 260) * (lap_y > 20)
    patches = smoothstep(0.80, 0.9, fbm(shape, 6, rng, octaves=4)) * (1 - prof * 0.6)
    rust = np.clip(rust_streak * 0.5 + patches, 0, 1)
    rust_col = lerp(hexc("#8a4a2a"), hexc("#b0683a"), fbm(shape, 12, rng, octaves=2))
    s.lay(rust, rust_col, rough=0.92, metal=0.0)
    s.tint(1 - 0.12 * streaks(shape, rng, 40, 2))
    return s
