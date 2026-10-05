"""Roof textures (1024 px): clay tiles, standing-seam metal, flat tar roof, wavy slate."""
import numpy as np

from registry import texture
from texlib import Surface, blur, box, cell_table, fbm, grid_coords, hexc, lerp, rect, smoothstep

R = 1024


@texture("roof_clay_tiles", "roofs", (R, R), (2.0, 2.0), normal_strength=8.0,
         notes="Terracotta beaver-tail tiles, staggered rows (8 x 10 per tile), lichen spots.")
def clay_tiles(name, shape, rng, ctx):
    h, w = shape
    xx, yy = grid_coords(shape)
    cols, rows = 8, 10
    tw, th = w / cols, h / rows
    row = np.floor(yy / th).astype(int)
    off = (row % 2) * tw / 2
    lx = (xx + off) % tw
    col = np.floor(((xx + off) % w) / tw).astype(int)
    ly = (yy - row * th) / th
    # rounded bottom edge: tile visible length shrinks toward its side edges
    cx = (lx - tw / 2) / (tw / 2)
    edge = 1.0 - 0.18 * cx ** 2
    inside = smoothstep(0.0, 0.04, edge - ly)
    # profile: thicker toward the bottom edge, shallow gap between neighbours
    side = smoothstep(0, 4, np.minimum(lx, tw - lx))
    s = Surface(shape, hexc("#5a2f22"), rough=0.8, height=0.1)
    s.height = 0.1 + inside * (0.3 + 0.6 * ly) * side
    var = cell_table(rng, (rows, cols))[row % rows, col % cols]
    pal = lerp(hexc("#b4583a"), hexc("#cf7a4f"), var)
    pal = lerp(pal, hexc("#8e4632"), (var > 0.85))
    low = fbm(shape, 4, rng, octaves=3)
    tile_col = pal * (0.9 + 0.15 * low)[..., None] * (0.85 + 0.15 * ly)[..., None]
    s.lay(inside * side, tile_col, rough=0.75)
    lichen = smoothstep(0.72, 0.85, fbm(shape, 10, rng, octaves=4)) * inside
    s.lay(lichen * 0.8, hexc("#b9b47a"), rough=0.95)
    s.tint(0.92 + 0.1 * fbm(shape, 2, rng, octaves=2))
    return s


@texture("roof_metal_sheet", "roofs", (R, R), (4.0, 4.0), normal_strength=8.0,
         notes="Standing-seam sheet, faded green paint, oil-canning, rust at seams and cross laps.")
def metal_sheet(name, shape, rng, ctx):
    h, w = shape
    xx, yy = grid_coords(shape)
    pitch = w / 8                     # 0.5 m pans
    lx = xx % pitch
    seam_d = np.minimum(lx, pitch - lx)
    seam = 1 - smoothstep(3, 7, seam_d)
    lap_y = yy % (h / 2)
    lap = 1 - smoothstep(0, 4, np.minimum(lap_y, h / 2 - lap_y))
    s = Surface(shape, hexc("#5f7f5c"), rough=0.5, height=0.4)
    paint = lerp(hexc("#567a56"), hexc("#7a9a6e"), fbm(shape, 4, rng, octaves=3))
    pan_var = cell_table(rng, (8,))[(xx // pitch).astype(int) % 8]
    s.albedo = paint * (0.94 + 0.1 * pan_var)[..., None]
    s.metal[:] = 0.35
    oil = fbm(shape, (8, 4), rng, octaves=2)
    s.height = 0.4 + 0.05 * oil + 0.5 * seam + 0.1 * lap
    s.tint(1 - 0.25 * lap)
    s.lay(seam, np.minimum(paint * 1.2, 1), rough=0.45)
    s.tint(1 - 0.3 * (1 - smoothstep(6, 12, seam_d)) * (1 - seam))
    rust_n = fbm(shape, 10, rng, octaves=4)
    rust = smoothstep(0.62, 0.8, rust_n * 0.6 + 0.6 * np.maximum(seam, lap) * rust_n)
    s.lay(rust, lerp(hexc("#86462a"), hexc("#a8653a"), rust_n), rough=0.9, metal=0.0)
    s.tint(1 - 0.12 * smoothstep(0.55, 0.9, fbm(shape, (24, 2), rng, octaves=3)))
    return s


@texture("roof_tar_flat", "roofs", (R, R), (6.0, 6.0), normal_strength=5.0,
         notes="Flat bitumen roll roof of panel blocks: 1 m strips with seams, fresh shiny "
               "patches, dried puddle rings, dust.")
def tar_flat(name, shape, rng, ctx):
    h, w = shape
    xx, yy = grid_coords(shape)
    strip = h / 6
    ly = yy % strip
    seam = 1 - smoothstep(0, 5, np.minimum(ly, strip - ly))
    s = Surface(shape, hexc("#3b3a39"), rough=0.75, height=0.4)
    base = lerp(hexc("#34332f"), hexc("#4a4844"), fbm(shape, 5, rng, octaves=3))
    s.albedo = base
    s.height = 0.4 + 0.06 * fbm(shape, 12, rng, octaves=3) + 0.12 * seam
    s.lay(seam * 0.7, hexc("#232220"), rough=0.4)
    # patches: blobby and rectangular
    blobs = smoothstep(0.8, 0.83, fbm(shape, 4, rng, octaves=4))
    rects = np.zeros(shape, np.float32)
    for _ in range(7):
        x0, y0 = rng.random(2) * np.array([w, h])
        pw, ph = 60 + rng.random() * 160, 40 + rng.random() * 110
        rects = np.maximum(rects, rect((xx - x0) % w, (yy - y0) % h, 0, 0, pw, ph, 2))
    patch = np.clip(blobs + rects, 0, 1)
    s.lay(patch, hexc("#1f1e1d"), rough=0.3, add_height=0.08)
    rim = np.clip(blur(patch, 3) - patch, 0, 1) * 3
    s.lay(np.clip(rim, 0, 1), hexc("#2a2826"), add_height=0.05)
    # dried puddles: light dusty rings
    pud = fbm(shape, 3, rng, octaves=3)
    ring = np.exp(-((pud - 0.75) / 0.025) ** 2)
    inner = smoothstep(0.75, 0.8, pud)
    s.lay(inner * 0.35, hexc("#6e6a62"), rough=0.85)
    s.lay(ring * 0.6, hexc("#8a857a"), rough=0.9)
    s.tint(0.94 + 0.1 * fbm(shape, 2, rng, octaves=2))
    return s


@texture("roof_slate_wavy", "roofs", (R, R), (4.0, 4.0), normal_strength=9.0,
         notes="Post-Soviet asbestos-cement wavy slate (shifer): grey sheets, overlaps, nails on "
               "crests, moss in troughs and yellow lichen.")
def slate(name, shape, rng, ctx):
    h, w = shape
    xx, yy = grid_coords(shape)
    waves = 28
    pitch = w / waves
    prof = 0.5 + 0.5 * np.cos(xx / pitch * 2 * np.pi)
    sheet_h = h / 2
    row = (yy // sheet_h).astype(int)
    ly = yy % sheet_h
    sheet_w = pitch * 7
    sx = (((xx + row * pitch * 3) % w) // sheet_w).astype(int)
    lx = (xx + row * pitch * 3) % sheet_w
    s = Surface(shape, hexc("#9a9a94"), rough=0.88, height=0.4)
    var = cell_table(rng, (2, 4))[row % 2, sx % 4]
    base = lerp(hexc("#8f908b"), hexc("#a9a9a1"), var)
    s.albedo = base * (0.9 + 0.14 * fbm(shape, 6, rng, octaves=3))[..., None]
    # the sheet below shows under this one's lower edge: step + shadow
    s.height = 0.2 + 0.6 * prof + 0.12 * (ly / sheet_h)
    edge_shadow = 1 - smoothstep(0, 18, ly)
    s.tint(1 - 0.35 * edge_shadow)
    vert = 1 - smoothstep(0, 4, np.minimum(lx, sheet_w - lx))
    s.tint(1 - 0.25 * vert)
    # nails on crests near the top of each sheet
    crest_d = np.abs(((xx / pitch) % 1.0) - 0.0)
    crest_d = np.minimum(crest_d, 1 - crest_d) * pitch
    nail = (crest_d < 4) * box(ly, sheet_h - 46, sheet_h - 38, 1) * (((xx // pitch).astype(int) % 3) == 0)
    s.lay(nail, hexc("#5c5753"), metal=0.6, rough=0.5, add_height=0.1)
    moss = smoothstep(0.62, 0.8, fbm(shape, 6, rng, octaves=3) * 0.8 + (1 - prof) * 0.35)
    s.lay(moss * 0.8, lerp(hexc("#4f6a34"), hexc("#6d8a43"), fbm(shape, 8, rng, octaves=2)), rough=0.95)
    lichen = smoothstep(0.86, 0.92, fbm(shape, 8, rng, octaves=3)) * prof
    s.lay(lichen, hexc("#c9b85a"), rough=0.95)
    s.tint(1 - 0.12 * smoothstep(0.55, 0.9, fbm(shape, (28, 2), rng, octaves=3)))
    return s
