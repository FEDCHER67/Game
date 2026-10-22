# Map W86 texture agent T1 (2026-10-22): CC0 ambientCG sets -> One-Armed Robber painted look, plus own procedural textures,
# for Forest / Hamlet / Rough / Downtown specials / World groups of Working/Reviews/MapW86_TextureInventory_2026-10-22.
# Output: Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Textures (1024 px; 2048 only for the decal / door atlases).
# Adaptation rules (as TextureTest v07): grain off (median + light blur), low-frequency grime off (high-pass), contrast compressed
# toward a painted mean; coloured sets keep a cleaned hue or are recoloured from their luminance. Normals = ambientCG NormalGL
# or own (from a height field). Run: python -P gen_textures_t1.py [name-filter]
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as nd

A1 = 'C:/Dev/Game/ArtSource/Textures/W86_T1/ambientCG/'
A22 = 'C:/Dev/Game/ArtSource/Textures/ambientCG_2026-10-22/'
GPT = 'C:/Dev/Game/Working/Reviews/Textures_2026-10-17/gpt_missing_v02_2026-10-18/Textures/'
L02 = 'C:/Dev/Game/Assets/OnlyVolunteers/Art/Map/Textures/Detail/TL_worn_grass_albedo.png'
FONT = 'C:/Dev/Game/ArtSource/Textures/W86_T1/fonts/Oswald.ttf'
OUT = 'C:/Dev/Game/Assets/OnlyVolunteers/Art/MapTextures_W86/T1/Textures/'
N = 1024
ONLY = sys.argv[1] if len(sys.argv) > 1 else None
rng = np.random.default_rng(861)
os.makedirs(OUT, exist_ok=True)
made = []


def want(name): return ONLY is None or ONLY in name


def load(sid, m='Color', root=A1, size=N):
    im = Image.open(f'{root}{sid}/{sid}_1K-JPG_{m}.jpg').convert('RGB')
    if im.size != (size, size): im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im, np.float32) / 255.0


def lum(a): return a[..., 0] * .299 + a[..., 1] * .587 + a[..., 2] * .114
def blur(a, s): return nd.gaussian_filter(a, s if a.ndim == 2 else (s, s, 0), mode='wrap')


def med(a, k):
    if a.ndim == 2: return nd.median_filter(a, size=k, mode='wrap')
    return np.dstack([nd.median_filter(a[..., i], size=k, mode='wrap') for i in range(a.shape[2])])


def paint(L, target, keep, k=3, soft=0.0, big=60, keep_lo=.25):
    """grain off (median k + blur soft), blotches off (high-pass, keep_lo of the low band), contrast `keep` around `target`"""
    if k > 1: L = med(L, k)
    if soft > 0: L = blur(L, soft)
    lo = blur(L, big)
    L = L - lo * (1 - keep_lo) + lo.mean() * (1 - keep_lo)
    return np.clip(target + (L - L.mean()) * keep, 0, 1)


def clean_color(Aa, k=5, big=50, flat=.8, keep=.7, sat=1.0, gain=1.0):
    Aa = med(Aa, k)
    L = lum(Aa)
    lo = blur(L, big)
    Aa = Aa / np.clip((lo / lo.mean()) ** flat, .3, 3)[..., None]
    mean = Aa.reshape(-1, 3).mean(0)
    Aa = mean + (Aa - mean) * keep
    L2 = lum(Aa)[..., None]
    Aa = L2 + (Aa - L2) * sat
    return np.clip(Aa * gain, 0, 1)


def hexc(h): h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], np.float32)


def recolor(L, hx, keep=1.0):
    """colour from a luminance detail field: mean -> hx, relative detail kept (x keep)"""
    c = hexc(hx)
    rel = 1 + (L - L.mean()) / max(L.mean(), 1e-3) * keep
    return np.clip(c[None, None, :] * rel[..., None], 0, 1)


def save(a, name, alpha=None, size=None):
    if not want(name): return
    a = np.clip(a, 0, 1)
    if a.ndim == 2: a = np.dstack([a, a, a])
    if alpha is not None:
        a = np.dstack([a, np.clip(alpha, 0, 1)])
        im = Image.fromarray((a * 255 + .5).astype(np.uint8), 'RGBA')
    else:
        im = Image.fromarray((a * 255 + .5).astype(np.uint8), 'RGB')
    if size: im = im.resize(size, Image.LANCZOS)
    im.save(OUT + name)
    made.append(name)


def nrm_from_h(H, s):
    gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * .5
    gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) * .5
    n = np.dstack([-gx * s, gy * s, np.ones_like(H)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * .5 + .5


def nrm_load(sid, root=A1, rot=0):
    n = load(sid, 'NormalGL', root)
    if rot:
        n = np.rot90(n, rot).copy()
        x, y = n[..., 0] * 2 - 1, n[..., 1] * 2 - 1
        for _ in range(rot % 4): x, y = -y, x                        # rotate the tangent-space vector with the image (CCW)
        n[..., 0] = x * .5 + .5; n[..., 1] = y * .5 + .5
    return n


def nrm_mix(a, b):
    x = a * 2 - 1; y = b * 2 - 1
    n = np.dstack([x[..., 0] + y[..., 0], x[..., 1] + y[..., 1], x[..., 2] * y[..., 2]])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * .5 + .5


def nrm_soft(n, k):
    """flatten a normal map toward up by k (0 = unchanged)"""
    x = (n * 2 - 1); x[..., 0] *= 1 - k; x[..., 1] *= 1 - k
    x /= np.linalg.norm(x, axis=2, keepdims=True)
    return x * .5 + .5


def noise(shape, s, seed=None):
    g = np.random.default_rng(seed) if seed is not None else rng
    a = blur(g.normal(0, 1, shape).astype(np.float32), s)
    return a / (a.std() + 1e-6)


def joints(w, h, xs, ys, width, soft=1.0):
    m = np.zeros((h, w), np.float32)
    for x in xs:
        for d in range(-(width // 2), width - width // 2): m[:, int(x + d) % w] = 1
    for y in ys:
        for d in range(-(width // 2), width - width // 2): m[int(y + d) % h, :] = 1
    return blur(m, soft) if soft > 0 else m


def rot(a, k=1): return np.ascontiguousarray(np.rot90(a, k))


# =============================================================== WOOD
# boards: ambientCG sets rotated to vertical boards (sheds, wagon, jetty), cleaned and recoloured from luminance
def boards(sid, hx, keep, name, rotk=1, root=A1, k=5, extra=None):
    L = lum(load(sid, root=root))
    L = paint(L, .6, 1.0, k=k, soft=.6, big=70, keep_lo=.2)
    if rotk: L = rot(L, rotk)
    col = recolor(L, hx, keep)
    if extra is not None: col = extra(col, L)
    save(col, name + '_albedo.png')
    save(nrm_soft(nrm_load(sid, root, rotk), .25), name + '_normal.png')
    return L

if want('boards') or want('wagon'):
    boards('WoodSiding005', '#6B3A2F', .75, 'T1_boards_red')                 # wagon a (teplushka oxide red)
    boards('WoodSiding007', '#4C6650', .8, 'T1_boards_green')               # wagon b (faded bottle green)
    boards('Planks023A', '#7E766B', .9, 'T1_boards_grey')                   # silver-grey weathered (sheds c, jetty b, wagon c)
    boards('WoodSiding007', '#4F4238', .85, 'T1_boards_dark')               # shed a: dark brown-grey vertical boards
    boards('Planks037A', '#3B302A', .8, 'T1_boards_tar')                    # shed b: tarred black-brown
    boards('Planks037B', '#8A6644', .85, 'T1_boards_warm')                  # warm honey boards (operating shed a, table)
    # whitewashed boards: lime wash with grey wood showing through on worn patches
    def wash(col, L):
        m = np.clip(nd.gaussian_filter(rng.normal(0, 1, col.shape[:2]).astype(np.float32), (40, 4), mode='wrap') * 12 + .88, 0, 1)[..., None]
        white = recolor(L, '#D9D3C6', .35)
        return white * m + col * (1 - m)
    boards('Planks023A', '#8A8276', .8, 'T1_boards_whitewash', extra=wash)
    # painted green boards with chipped paint (football box)
    def chips(col, L):
        m = (noise(col.shape[:2], 3, 9) + noise(col.shape[:2], 12, 10) * .8 > 1.9).astype(np.float32)
        m = blur(m, .7)[..., None]
        wood = recolor(L, '#8A8070', .8)
        return col * (1 - m) + wood * m
    boards('Planks023A', '#3E6B4C', .55, 'T1_boards_green_chipped', extra=chips)
    # cream painted horizontal siding (hut variant c)
    S = clean_color(load('WoodSiding009'), k=5, big=60, flat=.8, keep=.6, sat=.7, gain=1.0)
    save(recolor(lum(S), '#D6C9A6', .9), 'T1_siding_cream_albedo.png')
    save(nrm_soft(nrm_load('WoodSiding009'), .2), 'T1_siding_cream_normal.png')

# logs wall: own horizontal round logs 0.26 m (1024 px = 2.08 m -> 8 logs), grain from Wood087, warm brown
if want('logs'):
    yy = np.mgrid[0:N, 0:N][0].astype(np.float32)
    t = (yy % 128) / 128.0
    prof = np.sqrt(np.clip(1 - (2 * t - 1) ** 2, 0, 1))                     # round log section
    gr = paint(lum(load('Wood087', root=A22)), .6, 1.0, k=3, soft=.8, big=60, keep_lo=.2)
    gr = rot(gr, 1)
    shade = .55 + .45 * prof
    seam = np.exp(-((t - 0) * 128 / 5) ** 2) + np.exp(-((t - 1) * 128 / 5) ** 2)
    L = gr * .35 + shade * .65
    col = recolor(L, '#6E5640', .85) * (1 - .45 * seam[..., None])
    rowtone = (np.floor(yy / 128) * 37 % 11 / 11.0 - .5) * .08
    save(col * (1 + rowtone[..., None]), 'T1_logs_wall_albedo.png')
    save(nrm_from_h(prof * 30 + gr * 2, 1.0), 'T1_logs_wall_normal.png')

# bark / debarked logs (1 m tile around the circumference)
if want('bark'):
    save(clean_color(load('Bark012'), k=5, big=60, flat=.8, keep=.7, sat=.8, gain=.95), 'T1_bark_brown_albedo.png')
    save(nrm_load('Bark012'), 'T1_bark_brown_normal.png')
    Lb = paint(lum(load('Bark007')), .7, 1.0, k=3, soft=.6, big=50, keep_lo=.3)
    dark = nd.gaussian_filter(rng.normal(0, 1, (N, N)).astype(np.float32), (1.5, 9), mode='wrap'); dark = (dark / dark.std() + noise((N, N), 30, 22) * .5) > 2.1
    birch = recolor(Lb, '#CFC9BC', .5)
    birch[dark] = birch[dark] * .45
    save(blur(birch, .6), 'T1_bark_birch_albedo.png')
    save(nrm_load('Bark007'), 'T1_bark_birch_normal.png')
    Ld = paint(lum(load('Wood087', root=A22)), .6, 1.0, k=3, soft=.8, big=60, keep_lo=.2)
    save(recolor(rot(Ld, 1), '#9A9186', .8), 'T1_log_debarked_albedo.png')
    # log end rings (caps), 1 tile = one end disk
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    r = np.hypot(xx - N / 2, yy - N / 2) / (N / 2)
    ring = .5 + .5 * np.sin(r * 2 * np.pi * 14 + noise((N, N), 30, 23) * .8)
    endc = recolor(.6 + .15 * ring, '#B28E62', 1.0)
    endc[r > .9] = hexc('#5A4636')
    save(blur(endc, 1.0), 'T1_logend_albedo.png')

# =============================================================== METAL
if want('metal') or want('rust') or want('galv') or want('seam'):
    # rusty profiled sheet (trapezoid ribs from CorrugatedSteel002 normal), dark brown paint + rust patches (Rust009 colour)
    n2 = nrm_load('CorrugatedSteel002')
    rib = np.abs(n2[..., 0] * 2 - 1)
    rust = clean_color(load('Rust009'), k=5, big=60, flat=.8, keep=.55, sat=.75, gain=1.0)
    m = np.clip(noise((N, N), 40, 31) * .5 + noise((N, N), 8, 32) * .25 + .2, 0, 1)
    m = np.clip(m + blur((rng.random((N, N)) > .997).astype(np.float32), 6) * 3, 0, 1)
    paintc = recolor(paint(lum(load('CorrugatedSteel002')), .6, .5, k=3, big=60), '#5A4A40', .6)
    col = paintc * (1 - m[..., None]) + rust * m[..., None]
    save(col * (1 - .12 * rib[..., None]), 'T1_rust_sheet_albedo.png')
    save(n2, 'T1_rust_sheet_normal.png')
    # galvanised wave sheet with soft rust streaks running down (vertical blur of spots)
    n5 = nrm_load('CorrugatedSteel005', root=A22)
    g = paint(lum(load('CorrugatedSteel005', root=A22)), .66, .35, k=5, soft=1.2, big=50, keep_lo=.15)
    spots = (rng.random((N, N)) > .9993).astype(np.float32)
    streak = nd.gaussian_filter(spots, (60, 3), mode='wrap') * 60
    streak = np.clip(streak * 1.6, 0, .8)
    galv = recolor(g, '#9DA2A3', 1.0)
    col = galv * (1 - streak[..., None] * .7) + rust * (streak[..., None] * .7)
    save(col * (1 - .08 * np.abs(n5[..., 0] * 2 - 1)[..., None]), 'T1_galv_rust_albedo.png')
    save(n5, 'T1_galv_rust_normal.png')
    # neutral painted metal (colour from the material), faint brush and few chips
    pm = paint(lum(load('PaintedMetal004')), .78, .25, k=5, soft=1.0, big=40, keep_lo=.1)
    save(pm, 'T1_painted_metal_albedo.png')
    # painted metal with rust patches, two colours (gate green, mast grey)
    p6 = load('PaintedMetal006')
    rmask = np.clip((p6[..., 0] - p6[..., 1]) * 4 - .2, 0, 1)                # rust = red over green
    rmask = blur(rmask, 1.5)
    base = paint(lum(p6), .7, .3, k=5, soft=1.0, big=50, keep_lo=.1)
    for nm, hx in (('green', '#3E5A47'), ('grey', '#6C7073'), ('blue', '#3F5F7E')):
        c = recolor(base, hx, .5)
        save(c * (1 - rmask[..., None]) + rust * rmask[..., None], f'T1_metal_{nm}_rust_albedo.png')
    # standing-seam roof sheet, seams every 0.5 m (1024 px = 2 m), neutral
    xx = np.mgrid[0:N, 0:N][1].astype(np.float32)
    s = (xx % 256) / 256.0
    seam = np.exp(-((s - .5) * 256 / 4) ** 2)
    H = seam * 1.0
    L = .78 + .015 * noise((N, N), 60, 35) - .25 * seam + .1 * np.exp(-((s - .5) * 256 / 9) ** 2)
    save(L, 'T1_standing_seam_albedo.png')
    save(nrm_from_h(H * 8, 1.0), 'T1_standing_seam_normal.png')
    # steel tank plates: painted neutral, weld seams every 1.5 m (horizontal) / 2 m (vertical), rivets, faint streaks
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    seams = joints(N, N, [0, 512], [0, 341, 683], 3, .8)
    riv = ((((xx + 8) % 32) < 5) & (((yy + 8) % 341) < 5)) | ((((yy + 8) % 32) < 5) & (((xx + 8) % 512) < 5))
    Ht = seams * .6 + blur(riv.astype(np.float32), 1.2) * 1.5
    tank = pm * (1 - .15 * seams) * (1 + .05 * noise((N, N), 80, 36))
    save(tank, 'T1_steel_plates_albedo.png')
    save(nrm_from_h(Ht * 4, 1.0), 'T1_steel_plates_normal.png')

# =============================================================== MASONRY / CONCRETE / ROOFING
if want('brick') or want('plaster') or want('concrete') or want('panel') or want('po2') or want('tile') or want('ashlar') or want('roof') or want('slab') or want('tunnel') or want('mosaic') or want('shingle') or want('shotcrete'):
    save(clean_color(load('Bricks094'), k=7, big=60, flat=.9, keep=.5, sat=.55, gain=.92), 'T1_brick_red_albedo.png')
    save(nrm_load('Bricks094'), 'T1_brick_red_normal.png')
    pl = paint(lum(load('PaintedPlaster015')), .86, .35, k=5, soft=1.0, big=40, keep_lo=.15)
    save(recolor(pl, '#E7E1D3', .7), 'T1_plaster_whitewash_albedo.png')
    save(nrm_soft(nrm_load('PaintedPlaster015'), .5), 'T1_plaster_whitewash_normal.png')
    c34 = paint(lum(load('Concrete034')), .74, .35, k=5, soft=1.0, big=50, keep_lo=.15)
    save(recolor(c34, '#A29F99', .9), 'T1_plaster_grey_albedo.png')
    save(recolor(c34, '#BDB9B1', .8), 'T1_concrete_light_albedo.png')
    save(nrm_soft(nrm_load('Concrete034'), .4), 'T1_concrete_light_normal.png')
    # P-5 panels 3.0 x 1.2 m (1024 px = 3.0 m wide x 3.0 m tall: 1 x 2.5 rows -> use 3 x 3.6 m: rows at 0, 1.2, 2.4)
    Jp = joints(N, N, [0], [0, 341, 683], 5, 1.0)
    pt = np.vectorize(lambda r: 1 + ((r * 7919) % 13 / 13.0 - .5) * .05)((np.mgrid[0:N, 0:N][0] // 341)).astype(np.float32)
    save(recolor(c34, '#B5B2AB', .7) * (pt * (1 - .45 * Jp))[..., None], 'T1_panel_p5_albedo.png')
    save(nrm_from_h(-Jp * 2, 2.0), 'T1_panel_p5_normal.png')
    # bridge concrete: smooth light concrete, vertical expansion joints every 4 m (tile), faint formwork lines every 1 m
    Jb = joints(N, N, [0], [], 6, 1.0)
    fw = joints(N, N, [256, 512, 768], [256, 512, 768], 1, .8)
    save(recolor(c34, '#B3AFA7', .8) * (1 - .5 * Jb - .05 * fw)[..., None], 'T1_concrete_bridge_albedo.png')
    save(nrm_mix(nrm_soft(nrm_load('Concrete034'), .4), nrm_from_h(-Jb * 3 - fw * .4, 1.5)), 'T1_concrete_bridge_normal.png')
    # yard slabs 3 x 3 m (tile 6 m: 2 x 2 slabs), joints, two cracks, one darker patched slab
    Js = joints(N, N, [0, 512], [0, 512], 5, 1.0)
    sl = recolor(c34, '#9E9B95', .9)
    pid = (np.mgrid[0:N, 0:N][0] // 512) * 2 + (np.mgrid[0:N, 0:N][1] // 512)
    sl *= np.array([1.0, .96, 1.03, .93], np.float32)[pid][..., None]
    cr = np.zeros((N, N), np.float32)
    im = Image.new('L', (N, N), 0); d = ImageDraw.Draw(im)
    for (x0, y0) in ((140, 600), (700, 150)):
        pts = [(x0, y0)]
        for _ in range(9): pts.append((pts[-1][0] + rng.integers(15, 45), pts[-1][1] + rng.integers(-25, 26)))
        d.line(pts, fill=255, width=3)
    cr = blur(np.asarray(im, np.float32) / 255, .8)
    save(sl * (1 - .5 * Js - .45 * cr)[..., None], 'T1_concrete_slabs_old_albedo.png')
    save(nrm_from_h(-(Js * 2 + cr), 2.0), 'T1_concrete_slabs_old_normal.png')
    # shotcrete (tunnel c)
    sc = paint(lum(load('Concrete019')), .64, .55, k=3, soft=.6, big=60, keep_lo=.2)
    save(recolor(sc, '#8F8C86', .9), 'T1_shotcrete_albedo.png')
    save(nrm_load('Concrete019'), 'T1_shotcrete_normal.png')
    # white ceramic tiles (operating corner, tunnel), Tiles107 cleaned
    t107 = paint(lum(load('Tiles107')), .88, .6, k=3, soft=.5, big=60, keep_lo=.4)
    save(recolor(t107, '#E6E6E0', .8), 'T1_tiles_white_albedo.png')
    save(nrm_load('Tiles107'), 'T1_tiles_white_normal.png')
    # small facade tiles (Soviet shop), neutral
    t36 = paint(lum(load('Tiles036')), .8, .6, k=3, soft=.5, big=50, keep_lo=.4)
    save(t36, 'T1_tile_facade_albedo.png')
    save(nrm_load('Tiles036'), 'T1_tile_facade_normal.png')
    # roll roofing (tar paper): strips 1 m (1024 px = 4 m -> 256 px), overlap seams, granular, dark
    gr = paint(lum(load('Asphalt031', root=A22)), .5, .5, k=3, soft=.5, big=40, keep_lo=.2)
    yy = np.mgrid[0:N, 0:N][0].astype(np.float32)
    lap = ((yy % 256) / 256.0)
    edge = np.exp(-(lap * 256 / 6) ** 2)
    H = np.clip(lap * .2, 0, 1) - edge * .2
    save(recolor(gr, '#3E3E40', .6) * (1 - .25 * edge + .06 * lap)[..., None], 'T1_roof_tar_albedo.png')
    save(nrm_from_h(H * 6, 1.0), 'T1_roof_tar_normal.png')
    # wooden fish-scale shingles (wooden church roof)
    sh = clean_color(load('RoofingTiles002'), k=5, big=50, flat=.8, keep=.7, sat=.3, gain=1.0)
    save(recolor(lum(sh), '#5C5148', .9), 'T1_shingle_wood_albedo.png')
    save(nrm_load('RoofingTiles002'), 'T1_shingle_wood_normal.png')
    # big dressed granite ashlar 0.9 x 0.45 m, chamfered (tile 1.8 m = 1024 px -> block 512 x 256 px)
    g = paint(lum(load('Granite002A', root=A22)), .66, .55, k=3, soft=.8, big=40, keep_lo=.3)
    yy, xx = np.mgrid[0:N, 0:N]
    row = yy // 256
    xo = (xx + (row % 2) * 256) % 512
    dy = np.minimum(yy % 256, 255 - yy % 256); dx = np.minimum(xo, 511 - xo)
    Hc = np.clip(np.minimum(dx, dy).astype(np.float32) / 12.0, 0, 1)
    bid = row * 3 + (xx + (row % 2) * 256) // 512
    tone = (1 + ((bid * 7 + 3) % 9 / 9.0 - .5) * .1).astype(np.float32)
    save(recolor(g, '#8E8D88', .9) * (tone * (.62 + .38 * Hc))[..., None], 'T1_ashlar_granite_albedo.png')
    save(nrm_from_h(Hc * 6, 1.0), 'T1_ashlar_granite_normal.png')
    # PO-2 concrete fence panel, rhombus relief: 1024 x 512 = 4.0 x 2.0 m; frame 8 cm; rhombi 0.5 x 0.33 m
    W, Hh = 1024, 512
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32)
    u = (xx - 20) / (W - 40); v = (yy - 20) / (Hh - 40)
    inside = (u > 0) & (u < 1) & (v > 0) & (v < 1)
    du = (u * 8) % 1 - .5; dv = (v * 6) % 1 - .5
    rh = np.clip(1 - (np.abs(du) + np.abs(dv)) * 2, 0, 1)                  # pyramid per cell (rhombus field)
    Hpo = np.where(inside, .25 + .55 * np.clip(rh * 1.6 - .3, 0, 1), 1.0)
    cb = paint(lum(load('Concrete034')), .72, .35, k=5, soft=1.0, big=40, keep_lo=.15)
    cb = np.asarray(Image.fromarray((cb * 255).astype(np.uint8)).resize((W, Hh), Image.LANCZOS), np.float32) / 255
    shade = nrm_from_h(Hpo * 10, 1.0)
    lit = np.clip(.75 + (shade[..., 0] - .5) * -.6 + (shade[..., 1] - .5) * .6, .4, 1.1)
    save(recolor(cb, '#B1ADA5', .8) * lit[..., None], 'T1_po2_rhombus_albedo.png')
    save(shade, 'T1_po2_rhombus_normal.png')
    # PO-2 variant with vertical ribs (ribbed panel)
    rib = np.where(inside, .3 + .5 * (np.sin((u * 16) * 2 * np.pi) * .5 + .5) ** 2, 1.0)
    shade2 = nrm_from_h(rib * 8, 1.0)
    lit2 = np.clip(.78 + (shade2[..., 0] - .5) * -.6, .45, 1.1)
    save(recolor(cb, '#ADA9A2', .8) * lit2[..., None], 'T1_po2_ribbed_albedo.png')
    save(shade2, 'T1_po2_ribbed_normal.png')
    # tunnel walls: one texture over the whole wall height (u 4 m, v 0..1 = 0..5.5 m): kerb band, white tiles to 2.6 m,
    # blue stripe, light concrete above (the ceiling must use v 0.6..1 = concrete; builder request)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    hgt = (N - 1 - yy) / (N - 1) * 5.5
    tt = np.asarray(Image.fromarray((t107 * 255).astype(np.uint8)).resize((N // 2, N // 2), Image.LANCZOS), np.float32) / 255
    tt = np.tile(tt, (2, 2))
    conc = recolor(c34, '#B9B6AF', .7)
    tw = np.where((hgt < 2.6)[..., None], recolor(tt, '#E4E4DD', .8), conc)
    tw = np.where(((hgt >= 2.6) & (hgt < 2.78))[..., None], hexc('#3D5878')[None, None, :] * (.95 + .05 * tt[..., None]), tw)
    tw = np.where((hgt < .18)[..., None], hexc('#55534F')[None, None, :] * (.9 + .1 * c34[..., None]), tw)
    save(tw, 'T1_tunnel_tile_albedo.png')
    Ht = np.where(hgt < 2.6, tt * 1.5, 0) + np.where(hgt < .18, 2, 0)
    save(nrm_from_h(Ht.astype(np.float32) * 2, 1.0), 'T1_tunnel_tile_normal.png')
    # tunnel segments: concrete rings every 2 m (joints), painted white band 0-1.2 m with black/yellow edge line
    Jt = joints(N, N, [0, 512], [], 6, 1.2)
    seg = recolor(c34, '#A9A69F', .8) * (1 - .45 * Jt)[..., None]
    seg = np.where((hgt < 1.2)[..., None], hexc('#E2E0D8')[None, None, :] * (.94 + .06 * c34[..., None]) * (1 - .3 * Jt)[..., None], seg)
    seg = np.where(((hgt >= 1.2) & (hgt < 1.3))[..., None], hexc('#2E2E30')[None, None, :], seg)
    save(seg, 'T1_tunnel_segments_albedo.png')
    save(nrm_from_h(-Jt * 3, 1.0), 'T1_tunnel_segments_normal.png')
    # Soviet bus-stop mosaic (abstract sun over waves, no text), 2 cm tesserae, 1024 px = 3.4 x 2.4 m panel (non-square UVs)
    W, Hh = 1024, 724
    img = Image.new('RGB', (W, Hh), (226, 222, 210)); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, Hh * .55], fill=(206, 214, 222))
    d.ellipse([W * .58, Hh * .08, W * .86, Hh * .48], fill=(222, 150, 70))
    for k in range(9):
        a = k / 9 * math.pi * 2
        cx, cy = W * .72, Hh * .28
        d.line([cx + math.cos(a) * 140, cy + math.sin(a) * 140, cx + math.cos(a) * 200, cy + math.sin(a) * 200], fill=(222, 170, 80), width=14)
    for k, colr in enumerate([(70, 110, 160), (96, 140, 182), (52, 86, 134), (120, 160, 196)]):
        y0 = Hh * (.52 + k * .12)
        pts = [(x, y0 + 26 * math.sin(x / W * math.pi * 4 + k)) for x in range(0, W + 20, 20)]
        d.polygon(pts + [(W, Hh), (0, Hh)], fill=colr)
    d.polygon([(W * .12, Hh * .55), (W * .3, Hh * .12), (W * .48, Hh * .55)], fill=(178, 92, 70))
    d.polygon([(W * .26, Hh * .55), (W * .4, Hh * .25), (W * .54, Hh * .55)], fill=(150, 76, 62))
    mo = np.asarray(img, np.float32) / 255
    cell = 7
    yy, xx = np.mgrid[0:Hh, 0:W]
    gx = (xx // cell) * cell + cell // 2; gy = (yy // cell) * cell + cell // 2
    mo = mo[np.clip(gy, 0, Hh - 1), np.clip(gx, 0, W - 1)]
    jit = rng.uniform(-.05, .05, (Hh // cell + 1, W // cell + 1)).astype(np.float32)[yy // cell, xx // cell]
    grout = (((xx % cell) < 1) | ((yy % cell) < 1)).astype(np.float32)
    mo = mo * (1 + jit[..., None]) * (1 - .35 * grout[..., None]) + grout[..., None] * .35 * .8
    save(mo, 'T1_mosaic_albedo.png')

# =============================================================== GROUND (terrain-layer candidates, banks, ballast, fields, steppe)
if want('bank') or want('field') or want('ballast') or want('steppe'):
    g48 = paint(lum(load('Ground048')), .45, .6, k=5, soft=1.0, big=60, keep_lo=.2)
    save(recolor(g48, '#5E4D3C', .7), 'T1_bank_mud_albedo.png')
    save(nrm_soft(nrm_load('Ground048'), .3), 'T1_bank_mud_normal.png')
    r22 = clean_color(load('Rocks022'), k=5, big=60, flat=.8, keep=.75, sat=.6, gain=.95)
    save(r22, 'T1_bank_pebbles_albedo.png')
    save(nrm_load('Rocks022'), 'T1_bank_pebbles_normal.png')
    g23 = paint(lum(load('Gravel023')), .6, .8, k=3, soft=.6, big=50, keep_lo=.2)
    save(recolor(g23, '#8B8984', .9), 'T1_ballast_grey_albedo.png')
    save(recolor(g23, '#7B6A58', .9), 'T1_ballast_brown_albedo.png')
    save(nrm_load('Gravel023'), 'T1_ballast_normal.png')
    # fields: 1024 px = 4 m; furrows 0.5 m (128 px)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    fur = (np.sin(yy / 128 * 2 * np.pi) * .5 + .5) ** 1.5 + noise((N, N), 6, 41) * .06
    g103 = paint(lum(load('Ground103')), .5, .7, k=5, soft=1.0, big=60, keep_lo=.2)
    save(recolor(g103, '#6E5843', .7) * (.72 + .36 * fur)[..., None], 'T1_field_plowed_b_albedo.png')
    save(nrm_from_h(fur * 12, 1.0), 'T1_field_plowed_b_normal.png')
    save(recolor(g48, '#4E3E31', .7) * (.7 + .38 * fur)[..., None], 'T1_field_plowed_c_albedo.png')
    # stubble: rows 0.25 m of short straw stalks over soil
    rowm = .55 + .45 * ((yy % 64) < 34).astype(np.float32)
    stalks = (rng.random((N, N)) > .55).astype(np.float32)
    stalks = nd.gaussian_filter(stalks, (2.5, .6), mode='wrap')
    st = np.clip(rowm * (stalks * 2.2) + .25, 0, 1)
    soil = recolor(g103, '#6B5A45', .6)
    for nm, hx in (('b', '#BFA766'), ('c', '#A2A462')):
        straw = recolor(.6 + .4 * stalks, hx, .5)
        save(soil * (1 - st[..., None]) + straw * st[..., None], f'T1_field_stubble_{nm}_albedo.png')
    save(nrm_from_h(st * 4, 1.0), 'T1_field_stubble_normal.png')
    # steppe macro: 1024 px = 64 m; the L02 dry grass at 8 m tile (128 px) + large soft patches + faint wheel tracks
    l2 = np.asarray(Image.open(L02).convert('RGB').resize((128, 128), Image.LANCZOS), np.float32) / 255
    base = np.tile(l2, (8, 8, 1))
    base = clean_color(base, k=3, big=40, flat=.6, keep=.8, sat=1.0, gain=1.0)
    p1 = noise((N, N), 70, 51); p2 = noise((N, N), 22, 52)
    light = np.clip(p1 * .5 + p2 * .25, -1.5, 1.5)
    tr = np.zeros((N, N), np.float32)
    im = Image.new('L', (N, N), 0); d = ImageDraw.Draw(im)
    for off in (0, 22):
        pts = [(x, 300 + off + 120 * math.sin(x / N * 2 * math.pi)) for x in range(0, N + 8, 8)]
        d.line(pts, fill=255, width=4)
    tr = blur(np.asarray(im, np.float32) / 255, 2)
    for nm, warm in (('', 0.0), ('_warm', 1.0)):
        c = recolor(lum(base), '#968F62' if not warm else '#A68E5E', .9) * (1 + .10 * light[..., None])
        tint = np.ones(3, np.float32)
        olive = np.array([.92, .98, .86], np.float32)
        wo = np.clip((p1 - .4) * 1.2, 0, 1)[..., None]
        c = c * (olive * wo + (1 - wo)) * tint
        c = c * (1 - .18 * tr[..., None]) + tr[..., None] * .18 * hexc('#9C8C6C')
        save(c, f'T1_steppe_macro{nm}_albedo.png')

# =============================================================== WATER FX (duckweed, foam, spray)
if want('duck') or want('foam') or want('spray'):
    # duckweed (lemna): clusters of 6-10 mm fronds, 1024 px = 4 m; alpha clip
    cl = np.clip(noise((N, N), 35, 61) * .7 + noise((N, N), 9, 62) * .5 + .2, -3, 3)
    dens = np.clip((cl - .35) * 1.0, 0, 1)
    fr = np.zeros((N, N), np.float32); colv = np.zeros((N, N), np.float32)
    pts = rng.random((60000, 2)) * N
    keep = dens[pts[:, 1].astype(int), pts[:, 0].astype(int)] > rng.random(60000)
    im = Image.new('L', (N, N), 0); d = ImageDraw.Draw(im)
    imc = Image.new('L', (N, N), 0); dc = ImageDraw.Draw(imc)
    for (x, y) in pts[keep]:
        r = rng.uniform(1.6, 2.6)
        d.ellipse([x - r, y - r * .8, x + r, y + r * .8], fill=255)
        dc.ellipse([x - r, y - r * .8, x + r, y + r * .8], fill=int(rng.uniform(150, 255)))
    a = np.asarray(im, np.float32) / 255; cv = np.asarray(imc, np.float32) / 255
    col = recolor(.5 + .5 * cv, '#5E7832', .35)
    save(col, 'T1_duckweed_rgba.png', alpha=a)
    # foam strip (shore / plunge pool): u along 8 m (1024 px), v across 0..1 (water side v=1); soft painted blobs, white
    W, Hh = 1024, 256
    yy, xx = np.mgrid[0:Hh, 0:W].astype(np.float32)
    band = np.exp(-((yy / Hh - .45) / .18) ** 2)
    bl = np.zeros((Hh, W), np.float32)
    im = Image.new('L', (W, Hh), 0); d = ImageDraw.Draw(im)
    for _ in range(420):
        x = rng.uniform(0, W); y = rng.normal(.42, .14) * Hh; r = rng.uniform(3, 14)
        for dxw in (-W, 0, W): d.ellipse([x + dxw - r, y - r * .7, x + dxw + r, y + r * .7], fill=255)
    bl = blur(np.asarray(im, np.float32) / 255, 1.2)
    lace = np.clip(bl * .9 + band * .5 * (noise((Hh, W), 6, 63) * .3 + .7), 0, 1)
    lace = np.clip((lace - .25) * 1.6, 0, 1)
    save(np.full((Hh, W), .97, np.float32), 'T1_shore_foam_b_rgba.png', alpha=lace)
    # cleaned GPT shore foam: mask -> alpha, softened, white
    g = np.asarray(Image.open(GPT + 'WaterFX_shore_foam.png').convert('L'), np.float32) / 255
    g = blur(g, 1.2) * .85
    save(np.full(g.shape, .97, np.float32), 'T1_gpt_shore_foam_clean_rgba.png', alpha=g)
    # plunge-pool foam ring (radial), 512 px
    M = 512
    yy, xx = np.mgrid[0:M, 0:M].astype(np.float32)
    r = np.hypot(xx - M / 2, yy - M / 2) / (M / 2)
    ring = np.exp(-((r - .55) / .22) ** 2) * (noise((M, M), 5, 64) * .35 + .75)
    ring = np.clip((ring - .2) * 1.5, 0, 1) * (r < .98)
    save(np.full((M, M), .97, np.float32), 'T1_foam_ring_rgba.png', alpha=ring)
    # spray puff billboard
    sp = np.exp(-(r / .6) ** 2) * (noise((M, M), 14, 65) * .25 + .8)
    save(np.full((M, M), .95, np.float32), 'T1_spray_rgba.png', alpha=np.clip(sp * .8, 0, 1))

# =============================================================== CHAIN-LINK (wire colour from the material)
if want('chain'):
    # diamond mesh 5 cm (1024 px = 1 m -> 20 diamonds), wire 3.5 mm galvanised / 5 mm PVC; slight wire shading in RGB
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    p = N / 20.0
    a1 = ((xx + yy) % p) / p; a2 = ((xx - yy) % p) / p
    def wire(t, w): return np.clip(1 - np.abs(t - .5) * 2 / w, 0, 1)
    for nm, w in (('', .095), ('_thick', .14)):
        d1 = np.minimum(np.abs(a1 - .5), .5 - np.abs(a1 - .5))
        dist = np.minimum(np.minimum(a1, 1 - a1), np.minimum(a2, 1 - a2)) * p      # px distance to the nearest wire line
        half = w * p * .5
        al = np.clip((half - dist) / 1.0 + .5, 0, 1)
        sh = np.clip(1 - dist / max(half, 1), 0, 1)
        save(.62 + .38 * sh, f'T1_chainlink{nm}_rgba.png', alpha=al)

# =============================================================== HAY BALE atlas: left half = straw wrap (u around, 4.7 m x 1.2 m),
# right half = end spiral (disk, centred); 1024 x 1024, three colourways
if want('hay'):
    th = lum(load('ThatchedRoof001A'))
    th = paint(th, .6, 1.0, k=3, soft=.5, big=40, keep_lo=.3)
    th = rot(th, 1)                                                     # straws run around the bale
    side = np.asarray(Image.fromarray((th * 255).astype(np.uint8)).resize((512, N), Image.LANCZOS), np.float32) / 255
    M = 512
    yy, xx = np.mgrid[0:M, 0:M].astype(np.float32)
    rr = np.hypot(xx - M / 2, yy - M / 2) / (M / 2)
    ang = np.arctan2(yy - M / 2, xx - M / 2)
    spiral = np.sin((rr * 9 - ang / (2 * np.pi)) * 2 * np.pi) * .5 + .5
    fib = noise((M, M), 1.2, 71) * .15
    endL = np.clip(.55 + .3 * spiral + fib, 0, 1) * (rr < 1)
    endL = endL + (rr >= 1) * .5
    for nm, hx, hx2 in (('a', '#C9A55A', '#B3914E'), ('b', '#D2C08E', '#BDAA7C'), ('c', '#8F7F5E', '#7E7052')):
        S = recolor(side, hx, .8)
        E = recolor(np.vstack([endL, endL]), hx2, .6)
        save(np.concatenate([S, E], 1), f'T1_haybale_{nm}_albedo.png')
    Hn = np.concatenate([side * 2, np.vstack([spiral, spiral]) * 3], 1)
    save(nrm_from_h(Hn, 1.0), 'T1_haybale_normal.png')

# =============================================================== GARAGE DOORS atlas 2048: 4 styles (columns) x 4 colours (rows);
# each cell 512 px = 2.6 m wide x 2.6 m (door 2.5 x 2.1 m in the lower part, frame band); rust two strengths
if want('garage'):
    W = 2048; C = 512
    rustc = clean_color(load('Rust009'), k=5, big=60, flat=.8, keep=.55, sat=.75, gain=1.0)
    rust2 = np.asarray(Image.fromarray((rustc * 255).astype(np.uint8)).resize((C, C), Image.LANCZOS), np.float32) / 255
    cols = ['#4E6B55', '#4B6382', '#7A4A3A', '#7C7E7A']                 # faded green, blue, brown-red, grey
    for nm, rust_k in (('med', .55), ('heavy', 1.0)):
        A = np.zeros((W, W, 3), np.float32); Hh = np.zeros((W, W), np.float32)
        for r in range(4):
            for s in range(4):
                yy, xx = np.mgrid[0:C, 0:C].astype(np.float32)
                u = xx / C; v = 1 - yy / C                              # v up
                H = np.zeros((C, C), np.float32)
                frame = (u < .03) | (u > .97) | (v > .80) & (v < .835)
                door = (v < .80) & ~frame
                if s == 0:   # two leaves, vertical ribs, wicket door outline in the left leaf
                    H += door * ((np.sin(u * 2 * np.pi * 16) > .6) * .4)
                    H -= door * (np.abs(u - .5) < .006) * 1.0
                    wk = (np.abs(u - .25) < .13) & (v > .04) & (v < .70)
                    H -= ((np.abs(np.abs(u - .25) - .13) < .004) & (v > .04) & (v < .70)) * .8 + ((np.abs(v - .70) < .004) & (np.abs(u - .25) < .13)) * .8
                elif s == 1:  # two leaves plain with horizontal stiffeners
                    H += door * (((np.abs(v - .2) < .02) | (np.abs(v - .5) < .02) | (np.abs(v - .74) < .02)) * .6)
                    H -= door * (np.abs(u - .5) < .006) * 1.0
                elif s == 2:  # single up-and-over panel with pressed rectangles
                    H += door * (((u % .25) > .03) & ((u % .25) < .22) & (((v % .26) > .04) & ((v % .26) < .22))) * .35
                else:         # patched leaves (welded plates)
                    H -= door * (np.abs(u - .5) < .006) * 1.0
                    for (u0, v0, u1, v1) in ((.08, .1, .3, .35), (.62, .45, .9, .7), (.55, .05, .75, .22)):
                        H += ((u > u0) & (u < u1) & (v > v0) & (v < v1)) * .3
                H += frame * .8
                base = hexc(cols[r])
                L = .93 + .035 * noise((C, C), 30, 100 + r * 4 + s)
                col = base[None, None, :] * L[..., None]
                if s == 3: col = col * np.where(H[..., None] > .2, .85, 1.0)
                # rust: bottom band + edges + spots, strength by style / row
                edge = np.clip(1 - v / .16, 0, 1) ** 1.5 + np.clip(noise((C, C), 14, 200 + r * 4 + s) - 1.6, 0, 1) * .8
                rm = np.clip((edge * (.6 + .4 * ((r + s) % 3) / 2) + np.clip(noise((C, C), 4, 300 + s) - 2.6, 0, 1) * 2) * rust_k, 0, 1)
                col = col * (1 - rm[..., None]) + rust2 * rm[..., None]
                wall = hexc('#5A5856') * (.96 + .03 * noise((C, C), 20, 400 + r))[..., None]
                col = np.where((v >= .835)[..., None], wall, col)
                lit = 1 + (np.gradient(blur(H, 1.0), axis=1) * -6)
                col = col * np.clip(lit, .7, 1.2)[..., None]
                A[r * C:(r + 1) * C, s * C:(s + 1) * C] = col
                Hh[r * C:(r + 1) * C, s * C:(s + 1) * C] = H
        save(A, f'T1_garage_doors_{nm}_albedo.png')
    save(nrm_from_h(blur(Hh, 1.0) * 6, 1.0), 'T1_garage_doors_normal.png')

# =============================================================== DECALS (mesh decals on roads; alpha-blended, colour in RGB)
def bleed(rgb, a, it=12):
    """dilate colour into transparent texels (mips do not pull black into the edges)"""
    rgb = rgb.copy(); m = a > .02
    for _ in range(it):
        if m.all(): break
        acc = np.zeros_like(rgb); cnt = np.zeros(a.shape, np.float32)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            mm = np.roll(m, (dy, dx), (0, 1)); cc = np.roll(rgb, (dy, dx), (0, 1))
            acc += cc * mm[..., None]; cnt += mm
        grow = (~m) & (cnt > 0)
        rgb[grow] = acc[grow] / cnt[grow][..., None]
        m = m | grow
    return rgb

if want('road') or want('gpt'):
    # cleaned GPT atlases: alpha bleed; RoadWear cracks / patches given readable contrast; OilTar softened
    for nm, gain in (('RoadMarks', 1.0), ('RoadWear', 1.0), ('StreetUtility', 1.0), ('OilTar', 1.0)):
        im = np.asarray(Image.open(GPT + nm + '.png').convert('RGBA'), np.float32) / 255
        rgb, a = im[..., :3], im[..., 3]
        if nm == 'RoadWear':
            rgb = rgb * .75; a = np.clip(a * 1.6, 0, 1)
        if nm == 'OilTar':
            a = blur(a, 1.5) * .8
        save(bleed(rgb, a), f'T1_gpt_{nm}_clean_rgba.png', alpha=a)

    # own road marks atlas 2048: 4 x 4 cells of 512 px; layout (row, col) mirrored in the builder (T1Decal enum)
    W = 2048; C = 512
    def marks(worn):
        img = Image.new('L', (W, W), 0); d = ImageDraw.Draw(img)
        yel = Image.new('L', (W, W), 0); dy = ImageDraw.Draw(yel)
        def cell(r, c): return c * C, r * C
        x, y = cell(0, 0); d.rectangle([x + 236, y + 32, x + 276, y + 480], fill=255)                     # solid line 0.15 x 4 m (cell = 4 m)
        x, y = cell(0, 1); d.rectangle([x + 236, y + 32, x + 276, y + 240], fill=255)                     # dash 0.15 x ~1.8 m (3 m gap via spacing)
        x, y = cell(0, 2); d.rectangle([x + 40, y + 226, x + 472, y + 286], fill=255)                     # stop line
        x, y = cell(0, 3)
        for k in range(5): d.rectangle([x + 40 + k * 90, y + 40, x + 40 + k * 90 + 50, y + 472], fill=255)  # zebra block (5 bars)
        x, y = cell(1, 0); d.polygon([(x + 256, y + 40), (x + 330, y + 170), (x + 280, y + 170), (x + 280, y + 470), (x + 232, y + 470), (x + 232, y + 170), (x + 182, y + 170)], fill=255)
        x, y = cell(1, 1); d.polygon([(x + 120, y + 180), (x + 230, y + 80), (x + 230, y + 150), (x + 330, y + 150), (x + 330, y + 470), (x + 282, y + 470), (x + 282, y + 200), (x + 230, y + 200), (x + 230, y + 280)], fill=255)
        x, y = cell(1, 2); d.polygon([(x + 392, y + 180), (x + 282, y + 80), (x + 282, y + 150), (x + 182, y + 150), (x + 182, y + 470), (x + 230, y + 470), (x + 230, y + 200), (x + 282, y + 200), (x + 282, y + 280)], fill=255)
        x, y = cell(1, 3); d.rectangle([x + 60, y + 60, x + 452, y + 452], outline=255, width=26)          # parking bay outline
        x, y = cell(2, 0); d.rectangle([x + 236, y + 32, x + 276, y + 480], fill=0); dy.rectangle([x + 200, y + 32, x + 230, y + 480], fill=255); dy.rectangle([x + 282, y + 32, x + 312, y + 480], fill=255)   # double yellow
        x, y = cell(2, 1); dy.rectangle([x + 236, y + 32, x + 276, y + 220], fill=255)                     # yellow dash
        x, y = cell(2, 2)
        try:
            f = ImageFont.truetype(FONT, 330)
            try: f.set_variation_by_name('Bold')
            except Exception: pass
            d.text((x + 256, y + 256), 'P', font=f, fill=255, anchor='mm')
            x, y = cell(2, 3); d.text((x + 256, y + 256), 'BUS', font=ImageFont.truetype(FONT, 170), fill=255, anchor='mm')
        except Exception as e: print('font', e)
        x, y = cell(3, 0); d.ellipse([x + 60, y + 60, x + 452, y + 452], outline=255, width=24); d.text((x + 256, y + 250), 'H', font=ImageFont.truetype(FONT, 280), fill=255, anchor='mm')
        x, y = cell(3, 1); d.polygon([(x + 40, y + 472), (x + 256, y + 40), (x + 472, y + 472)], outline=255, width=24)   # give-way triangle
        x, y = cell(3, 2); d.rectangle([x + 40, y + 200, x + 472, y + 312], fill=255)                                     # wide bar (bus lane / chevron)
        x, y = cell(3, 3)
        for k in range(4): d.polygon([(x + 60 + k * 110, y + 472), (x + 110 + k * 110, y + 472), (x + 220 + k * 110, y + 40), (x + 170 + k * 110, y + 40)], fill=255)   # hatching
        a = np.asarray(img, np.float32) / 255; ay = np.asarray(yel, np.float32) / 255
        a = blur(a, 1.0); ay = blur(ay, 1.0)
        # worn edges: low-frequency loss + chipped speckle; worn = faded + more loss
        loss = np.clip(noise((W, W), 25, 81) * (.35 if not worn else .6) + noise((W, W), 3, 82) * (.15 if not worn else .35) - (.7 if not worn else .05), 0, 1)
        A = np.clip(a + ay, 0, 1) * (1 - loss) * (.92 if not worn else .62)
        rgb = np.dstack([np.full((W, W), .92), np.full((W, W), .91), np.full((W, W), .86)]).astype(np.float32)
        yc = hexc('#E0B640')
        m = (ay > a)[..., None]
        rgb = np.where(m, yc[None, None, :], rgb)
        return bleed(rgb, A, 8), A
    for nm, worn in (('clean', False), ('worn', True)):
        rgb, A = marks(worn)
        save(rgb, f'T1_roadmarks_{nm}_rgba.png', alpha=A)

    # own wear / utility atlas 2048: row0 cracks (4), row1 patches (2) + oil (2), row2 manhole, grate, tar seam, puddle stain; row3 heavy (Rough)
    def wear(heavy):
        rgbA = np.zeros((W, W, 3), np.float32); A = np.zeros((W, W), np.float32); Hn = np.zeros((W, W), np.float32)
        def put(r, c, rgb, a, h=None):
            rgbA[r * C:(r + 1) * C, c * C:(c + 1) * C] = rgb; A[r * C:(r + 1) * C, c * C:(c + 1) * C] = a
            if h is not None: Hn[r * C:(r + 1) * C, c * C:(c + 1) * C] = h
        yy, xx = np.mgrid[0:C, 0:C].astype(np.float32)
        for k in range(4):                                              # cracks
            im = Image.new('L', (C, C), 0); d = ImageDraw.Draw(im)
            g = np.random.default_rng(900 + k + (50 if heavy else 0))
            for br in range(3 + (3 if heavy else 0)):
                p = [(g.uniform(80, 430), g.uniform(80, 430))]
                ang = g.uniform(0, 2 * np.pi)
                for _ in range(int(g.integers(6, 14))):
                    ang += g.normal(0, .5); p.append((p[-1][0] + math.cos(ang) * 22, p[-1][1] + math.sin(ang) * 22))
                d.line(p, fill=255, width=int(g.integers(3, 6)))
            a = blur(np.asarray(im, np.float32) / 255, .8)
            halo = blur(a, 6) * .35
            put(0, k, np.dstack([np.full((C, C), .16)] * 3), np.clip(a * .95 + halo, 0, 1) * (1 if heavy else .85), -a)
        for k in range(2):                                              # patches (sealed rectangles, slightly darker asphalt)
            g = np.random.default_rng(950 + k)
            x0, y0 = g.uniform(40, 120), g.uniform(40, 120); x1, y1 = g.uniform(380, 470), g.uniform(300, 470)
            box = ((xx > x0) & (xx < x1) & (yy > y0) & (yy < y1)).astype(np.float32)
            edge = np.clip(blur(box, 3) * (1 - blur(box, 3)) * 8, 0, 1)
            gr = .12 + .02 * noise((C, C), 2, 960 + k)
            put(1, k, np.dstack([gr, gr, gr * 1.02]), np.clip(box * .8 + edge * .6, 0, 1), box * .3)
        for k in range(2):                                              # oil / tar stains
            g = np.random.default_rng(970 + k)
            m = np.zeros((C, C), np.float32)
            for _ in range(5):
                cx, cy, r = g.uniform(160, 350), g.uniform(160, 350), g.uniform(50, 120)
                m = np.maximum(m, np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)) ** 2))
            m = np.clip(m * (noise((C, C), 10, 980 + k) * .2 + .9), 0, 1)
            put(1, 2 + k, np.dstack([np.full((C, C), .07), np.full((C, C), .07), np.full((C, C), .08)]), m * (.55 if not heavy else .7))
        # manhole (round, 0.8 m in a 1 m cell)
        rr = np.hypot(xx - 256, yy - 256)
        lid = (rr < 200).astype(np.float32); rim = ((rr > 200) & (rr < 228)).astype(np.float32)
        pat = ((np.sin(xx / 14) > .3) ^ (np.sin(yy / 14) > .3)).astype(np.float32) * (rr < 170)
        g = .3 + .08 * pat + .05 * rim
        put(2, 0, np.dstack([g, g * .99, g * .97]), np.clip(lid + rim, 0, 1), pat * .4 + rim * .8 - (np.abs(rr - 200) < 3) * 1.0)
        # drain grate
        box = ((np.abs(xx - 256) < 200) & (np.abs(yy - 256) < 120)).astype(np.float32)
        slots = box * ((np.abs(yy - 256) < 100) & (((xx - 56) % 40) < 18)).astype(np.float32)
        g = .32 - slots * .25
        put(2, 1, np.dstack([g, g, g]), box, box * .5 - slots)
        # tar seam strip (sealed joint along the lane)
        seam = (np.abs(xx - 256 + 12 * np.sin(yy / 60)) < 10).astype(np.float32)
        put(2, 2, np.dstack([np.full((C, C), .1)] * 3), blur(seam, 1.0) * .85)
        # puddle stain / damp patch (darker asphalt, soft)
        m = np.clip(np.exp(-((xx - 256) ** 2 / 180 ** 2 + (yy - 256) ** 2 / 110 ** 2) ** 1.5) * (noise((C, C), 12, 990) * .25 + .9), 0, 1)
        put(2, 3, np.dstack([np.full((C, C), .12), np.full((C, C), .13), np.full((C, C), .14)]), m * .45)
        # row 3: Rough extras: pothole patch (cold-mix, lighter grey), alligator cracking, sunk manhole ring, scattered gravel
        g = np.random.default_rng(999)
        m = np.zeros((C, C), np.float32)
        for _ in range(7):
            cx, cy, r = g.uniform(150, 360), g.uniform(150, 360), g.uniform(30, 90)
            m = np.maximum(m, ((xx - cx) ** 2 + (yy - cy) ** 2 < r * r).astype(np.float32))
        m = blur(m, 2)
        cm = .26 + .05 * noise((C, C), 1.5, 998)
        put(3, 0, np.dstack([cm, cm * .98, cm * .95]), m * .95, m * .4)
        im = Image.new('L', (C, C), 0); d = ImageDraw.Draw(im)
        for i in range(0, C, 34):
            for j in range(0, C, 34):
                if np.hypot(i - 256, j - 256) < 220:
                    d.polygon([(i + g.uniform(-6, 6), j + g.uniform(-6, 6)), (i + 34 + g.uniform(-6, 6), j + g.uniform(-6, 6)), (i + 34 + g.uniform(-6, 6), j + 34 + g.uniform(-6, 6)), (i + g.uniform(-6, 6), j + 34 + g.uniform(-6, 6))], outline=255)
        a = blur(np.asarray(im, np.float32) / 255, .7)
        put(3, 1, np.dstack([np.full((C, C), .15)] * 3), a * .9, -a)
        ring = ((rr > 200) & (rr < 250)).astype(np.float32)
        put(3, 2, np.dstack([np.full((C, C), .18)] * 3), blur(ring, 2) * .8, -ring)
        grv = (g.random((C, C)) > .985).astype(np.float32)
        grv = blur(grv, .8) * 3 * (rr < 230)
        put(3, 3, np.dstack([np.full((C, C), .55), np.full((C, C), .53), np.full((C, C), .5)]), np.clip(grv, 0, 1))
        return bleed(rgbA, A, 8), A, Hn
    for nm, heavy in (('b', False), ('c', True)):
        rgb, A, Hn = wear(heavy)
        save(rgb, f'T1_roadwear_{nm}_rgba.png', alpha=A)
        if nm == 'b': save(nrm_from_h(blur(Hn, 1.0) * 4, 1.0), 'T1_roadwear_normal.png')

# =============================================================== SIGNS / EMISSIVE / SMALL ATLASES
if want('sign') or want('neon') or want('plate') or want('stripe') or want('grille') or want('flag') or want('hazard'):
    def font(sz):
        f = ImageFont.truetype(FONT, sz)
        try: f.set_variation_by_name('Bold')
        except Exception: pass
        return f
    # word signs atlas 2048 x 1024: 8 rows of 128 px x 2048 (one word per row, centred); RGBA, colour in the material / RGB
    W, Hh = 2048, 1024
    words = ['POLICE', 'TAXI', 'GAS', 'DINER', 'VANS', 'GARAGE', 'OPEN 24', 'BUS']
    im = Image.new('L', (W, Hh), 0); d = ImageDraw.Draw(im)
    for i, w in enumerate(words):
        d.text((W / 2, i * 128 + 64), w, font=font(104), fill=255, anchor='mm')
    a = blur(np.asarray(im, np.float32) / 255, .6)
    save(np.full((Hh, W), .97, np.float32), 'T1_sign_words_rgba.png', alpha=a)
    # shop light box "24" (Rough), 1024 x 256: white box, red digits, dark frame
    W, Hh = 1024, 256
    im = Image.new('RGB', (W, Hh), (236, 232, 222)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W - 1, Hh - 1], outline=(40, 40, 42), width=14)
    d.text((W / 2, Hh / 2 + 4), '24', font=font(200), fill=(196, 40, 36), anchor='mm')
    save(np.asarray(im, np.float32) / 255, 'T1_sign_24_albedo.png')
    # neon hearts (RGBA; RGB = tube colour, A = tube + glow), 512 px
    M = 512
    def heart_pts(s, cx, cy):
        pts = []
        for k in range(200):
            t = k / 200 * 2 * np.pi
            x = 16 * np.sin(t) ** 3; y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
            pts.append((cx + x * s, cy - y * s))
        return pts
    for nm, colr, kind in (('a', (255, 70, 150), 'tube'), ('b', (255, 50, 50), 'double'), ('c', (210, 60, 255), 'box')):
        im = Image.new('L', (M, M), 0); d = ImageDraw.Draw(im)
        if kind == 'box':
            d.polygon(heart_pts(13, M / 2, M / 2 - 10), fill=200); d.line(heart_pts(13, M / 2, M / 2 - 10) + [heart_pts(13, M / 2, M / 2 - 10)[0]], fill=255, width=10)
        else:
            d.line(heart_pts(13, M / 2, M / 2 - 10) + [heart_pts(13, M / 2, M / 2 - 10)[0]], fill=255, width=12)
            if kind == 'double': d.line(heart_pts(10, M / 2, M / 2 - 14) + [heart_pts(10, M / 2, M / 2 - 14)[0]], fill=255, width=8)
        tube = np.asarray(im, np.float32) / 255
        glow = blur(tube, 10) * .7
        a = np.clip(tube + glow, 0, 1)
        rgb = np.ones((M, M, 3), np.float32) * (np.array(colr, np.float32) / 255)[None, None, :]
        rgb = rgb * (1 - tube[..., None] * .35) + tube[..., None] * .35        # white-hot core
        save(rgb, f'T1_neon_heart_{nm}_rgba.png', alpha=a)
    # danger plate: yellow triangle, black lightning (no text), 256 px
    M = 256
    im = Image.new('RGBA', (M, M), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(128, 14), (244, 230), (12, 230)], fill=(232, 190, 40, 255), outline=(25, 25, 25, 255))
    d.line([(128, 14), (244, 230), (12, 230), (128, 14)], fill=(25, 25, 25, 255), width=10)
    d.polygon([(140, 70), (100, 150), (128, 150), (110, 210), (160, 128), (132, 128), (150, 70)], fill=(25, 25, 25, 255))
    arr = np.asarray(im, np.float32) / 255
    save(arr[..., :3], 'T1_danger_plate_rgba.png', alpha=arr[..., 3])
    # hazard stripes (yellow / black 45 deg), red / white barrier stripes; 512 px, tile 1 m
    M = 512
    yy, xx = np.mgrid[0:M, 0:M].astype(np.float32)
    hz = (((xx + yy) % 128) < 64)
    save(np.where(hz[..., None], hexc('#E1B53A'), hexc('#262628')) * (.95 + .05 * noise((M, M), 3, 120))[..., None], 'T1_hazard_stripes_albedo.png')
    rw = ((xx % 256) < 128)
    save(np.where(rw[..., None], hexc('#C2332C'), hexc('#E9E6DF')), 'T1_stripes_rw_albedo.png')
    # window grille (Soviet shop): 1024 = 2 x 2 m; bars 16 mm every 12 cm + sunburst-free plain grid; RGBA
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    gb = (((xx % 61) < 4) | ((yy % 122) < 4)).astype(np.float32)
    save(np.full((N, N), .3, np.float32), 'T1_grille_rgba.png', alpha=blur(gb, .6))
    # flag fabric: neutral cloth with soft vertical folds (colour from the material), 512 px
    M = 512
    xx = np.mgrid[0:M, 0:M][1].astype(np.float32)
    fold = np.sin(xx / M * 2 * np.pi * 3 + noise((M, M), 40, 130) * .6) * .5 + .5
    save(.78 + .18 * fold, 'T1_flag_fabric_albedo.png')
    save(nrm_from_h(fold * 6, 1.0), 'T1_flag_fabric_normal.png')

print(len(made), 'textures ->', OUT)
for m in made: print('  ', m)
