"""Ground textures (1024 px): paving, curb, road markings and decals, old asphalt,
gravel, dirt path, playground rubber. Basic asphalt/concrete/sand/grass live on the
cloud/map-props branch; here asphalt appears only as the base of marked/cracked variants."""
import numpy as np

from registry import texture
from texlib import (Surface, blur, box, cell_table, fbm, grid_coords, hexc, lerp, rect,
                    smoothstep, voronoi, warp)

G = 1024


def asphalt_base(shape, rng, fresh=0.5):
    s = Surface(shape, hexc("#4b4b4d"), rough=0.88, height=0.5)
    low = fbm(shape, 4, rng, octaves=3)
    s.albedo = lerp(hexc("#3f4042"), hexc("#5a5a5a"), low * 0.7 + (1 - fresh) * 0.3)
    s.albedo = s.albedo * (0.95 + 0.07 * fbm(shape, 48, rng, octaves=2))[..., None]
    s.height += 0.05 * fbm(shape, 64, rng, octaves=2)
    return s


def worn_paint(shape, rng, amount=0.35):
    """Mask that eats painted markings (wheel wear, low frequency)."""
    return smoothstep(1 - amount - 0.1, 1 - amount + 0.1, fbm(shape, 12, rng, octaves=4))


# ------------------------------------------------------------------ paving

@texture("ground_paving_sidewalk", "ground", (G, G), (4.0, 4.0), normal_strength=6.0,
         notes="Soviet 0.5 m concrete sidewalk slabs, uneven heights, cracked slabs, dirt in joints.")
def paving_sidewalk(name, shape, rng, ctx):
    xx, yy = grid_coords(shape)
    n = 8
    cs = G / n
    cx, cy = (xx // cs).astype(int), (yy // cs).astype(int)
    lx, ly = xx % cs, yy % cs
    d = np.minimum(np.minimum(lx, cs - lx), np.minimum(ly, cs - ly))
    slab = smoothstep(2, 5, d)
    tilt_x = (cell_table(rng, (n, n)) - 0.5)[cy, cx]
    tilt_y = (cell_table(rng, (n, n)) - 0.5)[cy, cx]
    lift = cell_table(rng, (n, n))[cy, cx]
    s = Surface(shape, hexc("#3c3a36"), rough=0.95, height=0.2)
    col = lerp(hexc("#a7a59e"), hexc("#bdbab1"), cell_table(rng, (n, n))[cy, cx])
    col = col * (0.92 + 0.12 * fbm(shape, 6, rng, octaves=3))[..., None]
    s.lay(slab, col, rough=0.85)
    s.height = 0.2 + slab * (0.5 + 0.12 * lift + 0.1 * (tilt_x * (lx / cs - 0.5) + tilt_y * (ly / cs - 0.5)))
    # cracks on some slabs
    cracked = cell_table(rng, (n, n))[cy, cx] > 0.85
    f1, f2, _ = voronoi(shape, 6, rng)
    crack = (1 - smoothstep(0.8, 2.2, f2 - f1)) * cracked * slab
    s.lay(crack, hexc("#4a4743"), add_height=-0.12)
    s.tint(1 - 0.1 * smoothstep(0.6, 0.9, fbm(shape, 5, rng, octaves=3)))
    return s


@texture("ground_paving_square", "ground", (G, G), (2.0, 2.0), normal_strength=6.0,
         notes="Old-town square pavers 20x10 cm, running bond, grey with red diamond pattern.")
def paving_square(name, shape, rng, ctx):
    xx, yy = grid_coords(shape)
    rows, cols = 20, 10
    bh, bw = G / rows, G / cols
    row = (yy // bh).astype(int)
    off = (row % 2) * bw / 2
    lx = (xx + off) % bw
    ly = yy % bh
    col = (((xx + off) % G) // bw).astype(int)
    d = np.minimum(np.minimum(lx, bw - lx), np.minimum(ly, bh - ly))
    body = smoothstep(2, 4, d)
    bevel = np.sqrt(np.clip((d - 2) / 6, 0, 1))
    s = Surface(shape, hexc("#57534d"), rough=0.95, height=0.2)
    # diamond pattern of red pavers, period = whole tile
    pcx = (col * bw + bw / 2 - off) % G
    pcy = row * bh + bh / 2
    dia = (np.abs(((pcx / G) % 0.5) - 0.25) + np.abs(((pcy / G) % 0.5) - 0.25))
    red = (np.abs(dia - 0.2) < 0.04)
    var = cell_table(rng, (rows, cols + 1))[row % rows, col % (cols + 1)]
    grey = lerp(hexc("#9c9993"), hexc("#b3afa6"), var)
    redc = lerp(hexc("#a65a46"), hexc("#b96a52"), var)
    c = np.where(red[..., None], redc, grey) * (0.93 + 0.1 * fbm(shape, 4, rng, octaves=3))[..., None]
    s.lay(body, c, rough=0.82)
    s.height = 0.2 + 0.6 * bevel * body
    s.tint(1 - 0.15 * smoothstep(0.6, 0.9, fbm(shape, 4, rng, octaves=3)))
    return s


@texture("ground_curb_concrete", "ground", (G, G), (2.0, 2.0), tiling="u", normal_strength=6.0,
         notes="Curb stone unwrap: U runs along the curb (1 m segments, repeats); V 0..0.45 = top, "
               "chamfer at 0.45-0.55, 0.55..1 = street face with grime toward the gutter.")
def curb(name, shape, rng, ctx):
    xx, yy = grid_coords(shape)
    seg = G / 2
    lx = xx % seg
    joint = 1 - smoothstep(2, 5, np.minimum(lx, seg - lx))
    s = Surface(shape, hexc("#b0ada5"), rough=0.85, height=0.6)
    s.albedo = lerp(hexc("#a8a59d"), hexc("#c2bfb6"), fbm(shape, 5, rng, octaves=3))
    seg_var = cell_table(rng, (2,))[(xx // seg).astype(int) % 2]
    s.tint(0.95 + 0.08 * seg_var)
    s.height += 0.04 * fbm(shape, 40, rng, octaves=2)
    v = yy / G
    chamfer = box(v, 0.45, 0.55, 4 / G)
    s.lay(chamfer * 0.5, hexc("#d2cfc6"), height=0.7)
    s.lay(joint, hexc("#5a5752"), height=0.3)
    grime = smoothstep(0.7, 1.0, v) * (0.5 + 0.5 * fbm(shape, 8, rng, octaves=3))
    s.tint(1 - 0.3 * grime)
    chips = smoothstep(0.78, 0.85, fbm(shape, 14, rng, octaves=4)) * smoothstep(0.08, 0.0, np.abs(v - 0.5))
    s.lay(chips, hexc("#8f8b83"), add_height=-0.15)
    s.tint(1 - 0.12 * smoothstep(0.6, 0.9, fbm(shape, 3, rng, octaves=3)))
    return s


# ------------------------------------------------------------------ road markings

@texture("ground_asphalt_lanes", "ground", (G, G), (8.0, 8.0), tiling="v", normal_strength=4.0,
         notes="Two-lane road strip, 8 m wide (U = road width, clamp), repeats along V every 8 m: "
               "dashed white centre line (4 m dash / 4 m gap), solid edge lines.")
def asphalt_lanes(name, shape, rng, ctx):
    xx, yy = grid_coords(shape)
    s = asphalt_base(shape, rng, 0.6)
    px = G / 8.0                         # px per metre
    edge = box(xx, 0.35 * px, 0.47 * px, 1.5) + box(xx, G - 0.47 * px, G - 0.35 * px, 1.5)
    centre = box(xx, G / 2 - 0.06 * px, G / 2 + 0.06 * px, 1.5) * box(yy, 0.0, 4 * px, 1.5)
    paint = np.clip(edge + centre, 0, 1) * (1 - 0.7 * worn_paint(shape, rng, 0.3))
    s.lay(paint, hexc("#e6e4dc"), rough=0.6, add_height=0.04)
    # wheel tracks: darker, smoother bands
    tracks = sum(np.exp(-((xx - c * px) / (0.45 * px)) ** 2) for c in (1.6, 3.0, 5.0, 6.4))
    s.tint(1 - 0.08 * tracks)
    s.rough = np.clip(s.rough - 0.08 * tracks, 0, 1)
    return s


@texture("decal_zebra_crossing", "ground", (G, G), (4.0, 4.0), tiling="none", kind="decal",
         normal_strength=3.0,
         notes="Pedestrian crossing decal, 4 x 4 m: 0.5 m white stripes, worn. Stripes run along V "
               "(parallel to traffic); project with URP Decal Projector, alpha = paint.")
def zebra(name, shape, rng, ctx):
    xx, yy = grid_coords(shape)
    px = G / 4.0
    s = Surface(shape, hexc("#e9e7e0"), rough=0.6, height=0.5)
    stripes = ((xx // (0.5 * px)).astype(int) % 2 == 0).astype(np.float32)
    stripes = stripes * box(xx % (0.5 * px), 2, 0.5 * px - 2, 1.5) * box(yy, 6, G - 6, 2)
    wear = worn_paint(shape, rng, 0.2)
    alpha = stripes * (1 - 0.8 * wear)
    s.alpha = blur(alpha, 0.7)
    s.height += 0.2 * alpha
    s.tint(0.95 + 0.06 * fbm(shape, 8, rng, octaves=2))
    return s


@texture("decal_parking_stalls", "ground", (G, G // 2), (10.0, 5.0), tiling="u", kind="decal",
         normal_strength=3.0,
         notes="4 parking stalls 2.5 x 5 m, white 10 cm lines; repeats along U for longer rows.")
def parking(name, shape, rng, ctx):
    xx, yy = grid_coords(shape)
    px = G / 10.0
    s = Surface(shape, hexc("#e9e7e0"), rough=0.6, height=0.5)
    lx = xx % (2.5 * px)
    lines = (1 - smoothstep(0.05 * px - 1, 0.05 * px + 1, np.minimum(lx, 2.5 * px - lx))) * box(yy, 0.05 * px, G / 2, 1.5)
    back = box(yy, 0.0, 0.1 * px, 1.5)
    alpha = np.clip(lines + back, 0, 1) * (1 - 0.8 * worn_paint(shape, rng, 0.3))
    s.alpha = alpha
    s.height += 0.2 * alpha
    return s


# ------------------------------------------------------------------ worn surfaces

@texture("ground_asphalt_cracked", "ground", (G, G), (6.0, 6.0), normal_strength=6.0,
         notes="Old faded asphalt of the bad district: alligator cracks, repair patches, a pothole.")
def asphalt_cracked(name, shape, rng, ctx):
    xx, yy = grid_coords(shape)
    s = asphalt_base(shape, rng, 0.0)
    s.albedo = lerp(s.albedo, hexc("#77746e"), 0.35)
    f1, f2, _ = voronoi(shape, 14, rng)
    wx = (fbm(shape, 8, rng, octaves=3) - 0.5) * 18
    wy = (fbm(shape, 8, rng, octaves=3) - 0.5) * 18
    e = warp(f2 - f1, wx, wy)
    zone = smoothstep(0.45, 0.65, fbm(shape, 3, rng, octaves=3))
    crack = (1 - smoothstep(0.6, 2.0, e)) * zone
    f1b, f2b, _ = voronoi(shape, 4, rng)
    big = 1 - smoothstep(0.8, 2.5, warp(f2b - f1b, wx * 2, wy * 2))
    crack = np.clip(crack + big, 0, 1)
    s.lay(crack, hexc("#2a2928"), add_height=-0.2, rough=0.95)
    # repair patches
    for _ in range(4):
        x0, y0 = rng.random(2) * G
        pw, ph = 120 + rng.random() * 220, 80 + rng.random() * 160
        m = rect((xx - x0) % G, (yy - y0) % G, 0, 0, pw, ph, 2)
        s.lay(m, hexc("#3a3a3b"), rough=0.8, add_height=0.03)
    # pothole with gravel
    pd = np.hypot(((xx - 700 + G / 2) % G) - G / 2, ((yy - 300 + G / 2) % G) - G / 2)
    pr = 70 + 15 * fbm(shape, 12, rng, octaves=2)
    hole = 1 - smoothstep(pr - 6, pr, pd)
    s.lay(hole, hexc("#5d564c"), rough=0.95)
    s.height -= 0.35 * hole * np.clip(1 - pd / (pr + 1), 0, 1) ** 0.5
    s.tint(1 - 0.15 * smoothstep(0.6, 0.9, fbm(shape, 4, rng, octaves=3)))
    return s


@texture("ground_gravel", "ground", (G, G), (2.0, 2.0), normal_strength=7.0,
         notes="Rounded courtyard gravel, warm greys; for parking lots, rail beds, village roads.")
def gravel(name, shape, rng, ctx):
    s = Surface(shape, hexc("#5b5247"), rough=0.95, height=0.1)
    f1, f2, cid = voronoi(shape, 40, rng, jitter=0.8)
    r = (f2 - f1)
    dome = np.clip(r / 14.0, 0, 1) ** 0.6
    stone = smoothstep(0.5, 2.0, r)
    table = rng.random(40 * 40).astype(np.float32)
    tone = table[cid]
    pal = lerp(hexc("#8d877d"), hexc("#b5aca0"), tone)
    pal = lerp(pal, hexc("#9a8470"), (table[(cid * 7) % (40 * 40)] > 0.7))
    s.lay(stone, pal * (0.9 + 0.12 * fbm(shape, 4, rng, octaves=2))[..., None], rough=0.8)
    s.height = 0.1 + 0.8 * dome * stone
    s.tint(0.92 + 0.1 * fbm(shape, 3, rng, octaves=2))
    return s


@texture("ground_dirt_path", "ground", (G, G), (4.0, 4.0), normal_strength=5.0,
         notes="Trodden dirt path / country track: two ruts along V, sparse pebbles, damp patches.")
def dirt_path(name, shape, rng, ctx):
    xx, yy = grid_coords(shape)
    s = Surface(shape, hexc("#7a5f45"), rough=0.92, height=0.5)
    low = fbm(shape, 4, rng, octaves=4)
    s.albedo = lerp(hexc("#6b5240"), hexc("#94775a"), low)
    s.height += 0.12 * fbm(shape, 10, rng, octaves=4)
    wob = (fbm(shape, (2, 6), rng, octaves=2) - 0.5) * 60
    ruts = sum(np.exp(-((xx - c + wob) / 70.0) ** 2) for c in (G * 0.3, G * 0.7))
    s.height -= 0.18 * ruts
    s.tint(1 - 0.12 * ruts)
    damp = smoothstep(0.6, 0.75, fbm(shape, 5, rng, octaves=3) * 0.6 + ruts * 0.5)
    s.lay(damp * 0.6, hexc("#4f3c2e"), rough=0.45)
    f1, f2, cid = voronoi(shape, 40, rng, jitter=0.9)
    keep = rng.random(40 * 40)[cid] > 0.82
    peb = (1 - smoothstep(4, 7, f1)) * keep
    s.lay(peb, hexc("#a29a8c"), rough=0.8)
    s.height += 0.15 * peb * np.clip(1 - f1 / 7, 0, 1)
    return s


@texture("ground_rubber_playground", "ground", (G, G), (4.0, 4.0), normal_strength=4.0,
         notes="Courtyard playground rubber tiles 0.5 m, terracotta and green checker with soft "
               "granule texture and faded patches.")
def rubber(name, shape, rng, ctx):
    xx, yy = grid_coords(shape)
    n = 8
    cs = G / n
    cx, cy = (xx // cs).astype(int), (yy // cs).astype(int)
    lx, ly = xx % cs, yy % cs
    d = np.minimum(np.minimum(lx, cs - lx), np.minimum(ly, cs - ly))
    tile = smoothstep(1.5, 4, d)
    red = ((cx + cy) % 2 == 0) ^ (cell_table(rng, (n, n))[cy, cx] > 0.85)
    col = np.where(red[..., None], hexc("#b55a46"), hexc("#5e8c58"))
    s = Surface(shape, hexc("#2e2b29"), rough=0.95, height=0.3)
    f1, f2, cid = voronoi(shape, 160, rng)
    gran = rng.random(160 * 160).astype(np.float32)[cid]
    col = col * (0.93 + 0.1 * gran)[..., None] * (0.9 + 0.15 * fbm(shape, 4, rng, octaves=3))[..., None]
    s.lay(tile, col, rough=0.95)
    s.height = 0.3 + tile * (0.5 + 0.04 * gran)
    fade = smoothstep(0.6, 0.85, fbm(shape, 3, rng, octaves=3))
    s.albedo = lerp(s.albedo, s.albedo.mean(-1, keepdims=True) * 1.1, fade[..., None] * 0.45)
    return s
