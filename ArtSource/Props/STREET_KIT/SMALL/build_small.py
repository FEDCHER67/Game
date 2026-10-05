"""STREET_KIT / SMALL - small map props still shown as placeholders by the map-look builder:
bus stop sign, "no swimming" beach sign, pipe supports (2 heights), advertising column, 5 rocks, CCTV cameras (wall, pole),
neutral default crate.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/SMALL/build_small.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/SMALL/build_small.py -- --revision 1
"""
import math, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import bpy, bmesh
from mathutils import Vector
import streetkit as sk
from streetkit import Mesh, T, R

fam = sk.Family('SK-SMALL', __file__)
BUDGET = (100, 800)
ROCK_BUDGET = (100, 600)


def disc(r, seg=24, dx=0.0, dz=0.0):
    return [(dx + r * math.cos(math.tau * k / seg), dz + r * math.sin(math.tau * k / seg)) for k in range(seg)]


def rect(x0, z0, x1, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def stroke(p0, p1, w):
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dz)
    nx, nz = -dz / L * w / 2, dx / L * w / 2
    return [(p0[0] + nx, p0[1] + nz), (p0[0] - nx, p0[1] - nz), (p1[0] - nx, p1[1] - nz), (p1[0] + nx, p1[1] + nz)]


LAYER = 0.005             # colour layers step toward the viewer like the TRAFFIC signs (no z-fighting)


def layers(m, front_y, zc, items, M=None):
    """items: [(k, poly XZ relative to the plate centre, colour)]; layer k front face at front_y - k*LAYER (toward -Y),
    embedded 3 mm into the layer behind. M places the result (e.g. a 180-degree turn for the back face)."""
    tmp = Mesh()
    for n, (k, poly, col) in enumerate(items):
        y1 = front_y - k * LAYER - 0.0004 * (n % 4)
        y0 = front_y - (k - 1) * LAYER + 0.003
        tmp.prism(poly, y0 - y1, col, T(0, (y0 + y1) / 2, zc))
    m.merge(tmp, M)


# ---------------------------------------------------------------- (1) bus stop sign
def bus_stop_sign():
    """Soviet stop sign: round two-faced plate with a black 'A' (avtobus) on yellow, white rim; route plate below."""
    m = Mesh()
    H, ZC, RP, TH = 2.40, 2.62, 0.27, 0.02
    m.cyl(0.04, H, 8, 'metal')                                                           # pipe pole
    m.cyl(0.12, 0.05, 8, 'concrete', r_top=0.09)                                         # collar
    m.box(0.09, 0.05, 0.1, 'metal_dark', at=(0, 0, H - 0.04))                            # clamp holding the plate edge
    m.prism(disc(RP + 0.01, 20), TH, 'metal', T(0, 0, ZC))                               # back plate (both faces get art)
    art = [(1, disc(RP, 20), 'white'), (2, disc(RP - 0.03, 20), 'yellow'),
           (3, stroke((-0.105, -0.13), (-0.018, 0.13), 0.05), 'black'),
           (3, stroke((0.105, -0.13), (0.018, 0.13), 0.05), 'black'),
           (3, rect(-0.062, -0.045, 0.062, -0.005), 'black')]
    layers(m, -TH / 2, ZC, art)
    layers(m, -TH / 2, ZC, art, R(180, 'Z'))                                             # back face, readable from +Y
    # route-number plate on the front of the pole: white board, three black "number" bars
    m.box(0.36, 0.02, 0.2, 'white', at=(0, -0.05, 1.95))
    m.box(0.07, 0.03, 0.04, 'metal_dark', at=(0, -0.03, 2.0))
    m.box(0.07, 0.03, 0.04, 'metal_dark', at=(0, -0.03, 1.9))
    for x in (-0.11, 0.0, 0.11):
        m.box(0.07, 0.006, 0.1, 'black', at=(x, -0.061, 1.95))
    return m


# ---------------------------------------------------------------- (2) "no swimming" beach sign with a text texture
FONT = {   # 5 x 7 pixel glyphs, rows top to bottom; Щ has an 8th descender row
    'К': ['X...X', 'X..X.', 'X.X..', 'XX...', 'X.X..', 'X..X.', 'X...X'],
    'У': ['X...X', 'X...X', 'X...X', '.XXXX', '....X', '....X', 'XXXX.'],
    'П': ['XXXXX', 'X...X', 'X...X', 'X...X', 'X...X', 'X...X', 'X...X'],
    'А': ['.XXX.', 'X...X', 'X...X', 'XXXXX', 'X...X', 'X...X', 'X...X'],
    'Т': ['XXXXX', '..X..', '..X..', '..X..', '..X..', '..X..', '..X..'],
    'Ь': ['X....', 'X....', 'X....', 'XXXX.', 'X...X', 'X...X', 'XXXX.'],
    'С': ['.XXX.', 'X...X', 'X....', 'X....', 'X....', 'X...X', '.XXX.'],
    'Я': ['.XXXX', 'X...X', 'X...X', '.XXXX', '..X.X', '.X..X', 'X...X'],
    'З': ['.XXX.', 'X...X', '....X', '..XX.', '....X', 'X...X', '.XXX.'],
    'Р': ['XXXX.', 'X...X', 'X...X', 'XXXX.', 'X....', 'X....', 'X....'],
    'Е': ['XXXXX', 'X....', 'X....', 'XXXX.', 'X....', 'X....', 'XXXXX'],
    'Щ': ['X.X.X', 'X.X.X', 'X.X.X', 'X.X.X', 'X.X.X', 'X.X.X', 'XXXXX', '....X'],
    'Н': ['X...X', 'X...X', 'X...X', 'XXXXX', 'X...X', 'X...X', 'X...X'],
    'О': ['.XXX.', 'X...X', 'X...X', 'X...X', 'X...X', 'X...X', '.XXX.'],
}
TEXT_LINES = ('КУПАТЬСЯ', 'ЗАПРЕЩЕНО')
TEXT_W, TEXT_H, TEXT_PX = 512, 256, 8          # texture size and pixels per font pixel
TEXT_NAME = 'SK_Text_NoSwimming'


def text_image():
    """512 x 256 sRGB board face: white field, red frame, red pixel-font text in two lines (generated, deterministic)."""
    img = bpy.data.images.get(TEXT_NAME)
    if img:
        return img
    red, white = [c / 255 for c in sk.PALETTE[sk.PAL['sign_red']][1]], [c / 255 for c in sk.PALETTE[sk.PAL['white']][1]]
    grid = [[False] * TEXT_W for _ in range(TEXT_H)]                  # True = red, row 0 = top
    for y in range(TEXT_H):
        for x in range(TEXT_W):
            grid[y][x] = min(x, y, TEXT_W - 1 - x, TEXT_H - 1 - y) < 14
    line_h = 7 * TEXT_PX
    gap = 3 * TEXT_PX
    top = (TEXT_H - 2 * line_h - gap) // 2
    for li, line in enumerate(TEXT_LINES):
        w = (len(line) * 6 - 1) * TEXT_PX
        x0 = (TEXT_W - w) // 2
        y0 = top + li * (line_h + gap)
        for ci, ch in enumerate(line):
            for r, row in enumerate(FONT[ch]):
                for c, bit in enumerate(row):
                    if bit == 'X':
                        for yy in range(TEXT_PX):
                            for xx in range(TEXT_PX):
                                grid[y0 + r * TEXT_PX + yy][x0 + (ci * 6 + c) * TEXT_PX + xx] = True
    img = bpy.data.images.new(TEXT_NAME, TEXT_W, TEXT_H, alpha=False)
    img.colorspace_settings.name = 'sRGB'
    px = []
    for y in range(TEXT_H):
        row = grid[TEXT_H - 1 - y]                                    # image rows go bottom-up
        for x in range(TEXT_W):
            px += [*(red if row[x] else white), 1.0]
    img.pixels = px
    return img


def text_material():
    m = sk._image_material(TEXT_NAME, text_image(), 0.7)
    m.node_tree.nodes['Image Texture'].interpolation = 'Linear'
    return m


def sign_no_swimming():
    """Beach sign: two pointed wooden posts dug into the sand, plank board 1.4 x 0.7 m whose front (-Y) face carries the text."""
    m = Mesh()
    BW, BH, BD, BZ = 1.4, 0.7, 0.04, 1.55
    for x in (-0.5, 0.5):
        m.box(0.09, 0.09, 1.9, 'wood_dark', at=(x, 0, 0), base=True)
        m.prism([(-0.045, 0), (0.045, 0), (0, 0.06)], 0.09, 'wood_dark', T(x, 0, 1.9))   # pointed top
    fs = list(m.box(BW, BD, BH, 'wood', at=(0, -0.045 - BD / 2, BZ)))
    m.fuv[fs[2]] = [(0, 0), (1, 0), (1, 1), (0, 1)]                  # -Y face: loop order BL, BR, TR, TL -> whole texture
    for z in (BZ - BH / 2 + 0.03, BZ + BH / 2 - 0.03):                # back battens
        m.box(BW - 0.1, 0.03, 0.08, 'wood_dark', at=(0, -0.03, z))
    y = -0.045 - BD - 0.008                                           # painted trim frame in front of the board edges
    for z in (-1, 1):
        m.box(BW + 0.04, 0.025, 0.04, 'wood_dark', at=(0, y, BZ + z * (BH / 2 + 0.0)))
    for x in (-1, 1):
        m.box(0.04, 0.025, BH - 0.04, 'wood_dark', at=(x * (BW / 2 + 0.0), y, BZ))
    m.beam((-0.5, 0.06, 0.25), (0.5, 0.06, 0.95), 0.07, 0.03, 'wood_dark', up=(0, 1, 0))   # cross brace behind
    for x in (-0.5, 0.5):                                             # sand heaped around the posts
        m.cyl(0.2, 0.08, 6, 'sand', r_top=0.06, at=(x, 0, 0))
    return m


# ---------------------------------------------------------------- (3) pipe support / saddle for a 0.8 m pipe
PIPE_R = 0.40


def pipe_support(gap):
    """Rusty welded steel saddle; the pipe (d 0.8 m, along X) rests with its underside `gap` m above the sand."""
    m = Mesh()
    zc = gap + PIPE_R                                                 # pipe axis height
    cradle_r = PIPE_R + 0.02
    m.box(0.36, 1.0, 0.03, 'rust', base=True)                         # base plate on the sand
    beam_top = gap - 0.03                                             # cross beam stays clear of the pipe underside
    a = [math.radians(-60 + 15 * k) for k in range(9)]                # saddle: 8 plates from -60 to +60 deg around the bottom
    pts = [(0, cradle_r * math.sin(t), zc - cradle_r * math.cos(t)) for t in a]
    leg_y = pts[-1][1] + 0.01
    for y in (-leg_y, leg_y):
        m.box(0.12, 0.10, pts[-1][2] - 0.03, 'metal_dark', at=(0, y, 0.03), base=True)  # leg (square tube) up to the saddle end
        m.box(0.2, 0.16, 0.02, 'rust', at=(0, y, 0.03), base=True)                     # foot gusset
    m.beam((0, -leg_y, 0.1), (0, leg_y, beam_top - 0.1), 0.06, 0.06, 'rust')          # diagonal brace
    m.box(0.12, 2 * leg_y, 0.08, 'metal_dark', at=(0, 0, beam_top - 0.08), base=True)  # cross beam
    for p0, p1 in zip(pts, pts[1:]):
        dy, dz = p1[1] - p0[1], p1[2] - p0[2]
        L = math.hypot(dy, dz)
        n = (0, dz / L * 0.012, -dy / L * 0.012)                       # push the 24 mm plate out of the pipe surface
        m.beam(tuple(p0[i] + n[i] for i in range(3)), tuple(p1[i] + n[i] for i in range(3)), 0.3, 0.024, 'rust',
               up=(0, dz, -dy))
    for y in (-0.27, -0.14, 0.14, 0.27):                              # short welded struts from the beam to the saddle
        top = zc - math.sqrt(cradle_r ** 2 - y * y) - 0.01
        m.box(0.03, 0.03, top - beam_top + 0.01, 'rust', at=(0, y, beam_top - 0.01), base=True)
    # strap over the top of the pipe, bolted to lugs at the saddle ends (+-120 degrees from the top)
    ring = [(0, (cradle_r + 0.014) * math.sin(t), zc + (cradle_r + 0.014) * math.cos(t))
            for t in [math.radians(-120 + 30 * k) for k in range(9)]]
    m.tube_path(ring, 0.014, 6, 'metal_dark')
    for p in (pts[0], pts[-1]):
        m.box(0.08, 0.07, 0.05, 'metal_dark', at=(0, p[1] * 1.08, p[2] - 0.01))
    return m, zc


# ---------------------------------------------------------------- (4) advertising column (Litfass)
def ad_column():
    m = Mesh()
    seg = 16
    m.lathe([(0.66, 0), (0.66, 0.18), (0.6, 0.24), (0.6, 2.42), (0.66, 2.48), (0.66, 2.56), (0.72, 2.6), (0.72, 2.66),
             (0.5, 2.86), (0.22, 2.96), (0.0, 3.0)], seg, 'cream',
            cols=['concrete_dark', 'concrete_dark', 'cream', 'green', 'green', 'green', 'green', 'green', 'green', 'green',
                  'green'])
    m.cyl(0.035, 0.18, 6, 'green', at=(0, 0, 2.96))                    # finial
    m.lathe([(0.06, 3.12), (0.0, 3.18)], 6, 'green', M=None)
    m.cyl(0.06, 0.02, 6, 'green', at=(0, 0, 3.1))
    # posters: flat panels on the column facets, 2 facets each, various colours, a few torn/shifted
    facet = math.tau / seg
    rp = 0.6 * math.cos(facet / 2) + 0.004                             # facet plane distance from axis
    w = 2 * 0.6 * math.sin(facet / 2) - 0.02
    posters = [(0, 0.9, 1.9, 'yellow'), (1, 0.95, 1.85, 'yellow'), (3, 1.2, 2.25, 'blue'), (4, 1.2, 2.25, 'blue'),
               (6, 0.5, 1.4, 'pink'), (7, 0.5, 1.4, 'pink'), (8, 1.5, 2.3, 'white'), (10, 0.7, 1.6, 'orange'),
               (11, 0.7, 1.6, 'orange'), (13, 1.1, 2.1, 'red'), (14, 1.1, 2.1, 'white'), (15, 0.4, 1.0, 'cream')]
    for k, z0, z1, col in posters:
        ang = facet * (k + 0.5) - math.pi / 2                          # facet 0 centred on -Y (front)
        M = R(math.degrees(ang) + 90, 'Z') @ T(0, -rp, 0)
        m.box(w, 0.006, z1 - z0, col, M, at=(0, 0, (z0 + z1) / 2))
    # a darker "text band" on the two big posters
    for k in (3, 4):
        ang = facet * (k + 0.5) - math.pi / 2
        m.box(w - 0.04, 0.006, 0.12, 'white', R(math.degrees(ang) + 90, 'Z') @ T(0, -rp - 0.005, 0), at=(0, 0, 1.95))
    return m


# ---------------------------------------------------------------- (5) rocks: faceted convex hulls
def rock(seed, size, squash, stretch, n, tilt=0.0):
    """Deterministic faceted boulder: convex hull of n points on a squashed, stretched ellipsoid; flat base on z = 0.
    size = longest horizontal dimension (approx.)."""
    rnd = random.Random(seed)
    pts = []
    rx, ry, rz = size / 2, size / 2 / stretch, size / 2 * squash
    for i in range(n):
        u = 1 - 2 * (i + 0.5) / n                                     # golden-spiral spread, jittered
        v = i * math.pi * (3 - math.sqrt(5)) + rnd.uniform(-0.25, 0.25)
        s = math.sqrt(1 - u * u)
        k = rnd.uniform(0.9, 1.0)
        x, y, z = s * math.cos(v) * rx * k, s * math.sin(v) * ry * k, u * rz * k
        x += z * tilt
        pts.append((x, y, max(z, -rz * 0.55)))
    bm = bmesh.new()
    for p in pts:
        bm.verts.new(p)
    bmesh.ops.convex_hull(bm, input=list(bm.verts))
    for v in [v for v in bm.verts if not v.link_faces]:
        bm.verts.remove(v)
    zmin = min(v.co.z for v in bm.verts)
    f = size / max(max(v.co.x for v in bm.verts) - min(v.co.x for v in bm.verts),
                   max(v.co.y for v in bm.verts) - min(v.co.y for v in bm.verts))
    for v in bm.verts:
        v.co.z -= zmin
        v.co *= f
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.verts.index_update()
    bm.normal_update()
    verts = [tuple(v.co) for v in bm.verts]
    faces, cols = [], []
    for f in bm.faces:
        faces.append(tuple(v.index for v in f.verts))
        nz = f.normal.z
        cols.append('concrete' if nz > 0.75 else ('ash' if nz > -0.2 and (f.index * 7 + seed) % 5 == 0 else 'concrete_dark'))
    bm.free()
    m = Mesh()
    m.shell(verts, faces, 'concrete_dark', cols=cols)
    return m


ROCKS = [  # name, seed, size m, squash, stretch, hull points, tilt, note
    ('SK_Rock_01', 11, 0.5, 0.8, 1.2, 64, 0.0, 'pebble-boulder 0.5 m'),
    ('SK_Rock_02', 23, 0.9, 1.25, 1.1, 80, 0.15, 'upright stone 0.9 m'),
    ('SK_Rock_03', 37, 1.4, 0.45, 1.4, 90, 0.0, 'flat slab 1.4 m for hillsides'),
    ('SK_Rock_04', 41, 2.2, 0.75, 1.3, 130, 0.1, 'boulder 2.2 m'),
    ('SK_Rock_05', 53, 3.0, 0.62, 1.6, 180, 0.2, 'large outcrop 3 m for beach ends'),
]


# ---------------------------------------------------------------- (6) CCTV cameras
CAM_TILT = -15.0


def cctv_head_mesh(joint):
    """Camera housing pointing along -Y, tilted down, built around the pan joint `joint` (world coords)."""
    m = Mesh()
    M = T(*joint) @ R(CAM_TILT, 'X')
    lens = Mesh()
    lens.bar((0, -0.29, -0.07), (0, -0.315, -0.07), 0.028, 'glass_dark', seg=8)
    h = Mesh()
    h.bevel_box(0.12, 0.30, 0.11, 0.015, 'white', at=(0, -0.13, -0.07))
    h.box(0.15, 0.34, 0.012, 'white', at=(0, -0.15, -0.006))
    h.box(0.09, 0.012, 0.075, 'black', at=(0, -0.282, -0.07))
    h.box(0.012, 0.006, 0.012, 'red', at=(0.035, -0.289, -0.03))
    h.merge(lens)
    m.merge(h, M)
    m.cyl(0.025, 0.07, 6, 'metal_dark', at=(joint[0], joint[1], joint[2] - 0.065))     # joint knuckle
    return m


def cctv_wall_bracket():
    """Wall plate on y = 0 and an arm reaching out toward -Y to the joint at (0, -0.22, 0.12)."""
    m = Mesh()
    m.box(0.12, 0.02, 0.2, 'white', at=(0, -0.01 + 0.004, 0.1))
    for x, z in ((-0.035, 0.04), (0.035, 0.04), (-0.035, 0.16), (0.035, 0.16)):
        m.cyl(0.01, 0.006, 6, 'metal_dark', R(90, 'X') @ T(x, z, 0.0))                   # screw heads (local XY = wall)
    m.beam((0, -0.01, 0.1), (0, -0.22, 0.17), 0.04, 0.04, 'white')
    m.cyl(0.03, 0.03, 8, 'white', at=(0, -0.22, 0.155))
    return m


def cctv_pole():
    """3 m pipe pole with base flange and a short arm toward -Y ending at the joint (0, -0.35, 2.95)."""
    m = Mesh()
    m.cyl(0.18, 0.02, 8, 'metal_dark')                                                   # flange
    for k in range(4):
        a = math.tau * (k + 0.5) / 4
        m.cyl(0.018, 0.04, 6, 'metal_dark', at=(0.13 * math.cos(a), 0.13 * math.sin(a), 0.02))   # anchor nuts
    m.cyl(0.055, 3.0, 8, 'metal', r_top=0.045)
    m.cyl(0.055, 0.03, 8, 'metal_dark', at=(0, 0, 3.0))                                  # cap
    m.beam((0, 0.0, 2.92), (0, -0.35, 2.98), 0.045, 0.045, 'metal')
    m.cyl(0.03, 0.04, 8, 'metal', at=(0, -0.35, 2.96))
    m.box(0.22, 0.12, 0.3, 'metal_dark', at=(0, -0.08, 2.1))                             # junction box
    m.box(0.18, 0.006, 0.12, 'yellow', at=(0, -0.143, 2.12))                             # warning plate
    return m


# ---------------------------------------------------------------- (7) default crate
def default_crate():
    """Neutral 0.6 m wooden crate: core box + framed boards with a diagonal brace on the four sides and the lid."""
    m = Mesh()
    S_, B, D = 0.6, 0.07, 0.02
    m.bevel_box(S_ - 2 * D, S_ - 2 * D, S_ - D, 0.01, 'wood', base=True)
    h = S_ / 2 - D / 2
    for ang in (0, 90, 180, 270):
        M = R(ang, 'Z') @ T(0, -h, S_ / 2 - D / 2)                                       # side frame plane, local XZ
        for z in (-1, 1):
            m.box(S_, D, B, 'wood_dark', M, at=(0, 0, z * (S_ / 2 - D / 2 - B / 2)))
        for x in (-1, 1):
            m.box(B, D, S_ - D - 2 * B, 'wood_dark', M, at=(x * (S_ / 2 - B / 2), 0, 0))
        L = S_ - 2 * B
        Hh = S_ - D - 2 * B
        ang_d = math.degrees(math.atan2(Hh, L))
        m.box(math.hypot(L, Hh) - B, D, B, 'wood_dark', M @ R(-ang_d, 'Y'))
    M = T(0, 0, S_ - D / 2)                                                              # lid frame, local XY
    for y in (-1, 1):
        m.box(S_ - 2 * D, B, D, 'wood_dark', M, at=(0, y * (S_ / 2 - D - B / 2), 0))
    for x in (-1, 1):
        m.box(B, S_ - 2 * D - 2 * B, D, 'wood_dark', M, at=(x * (S_ / 2 - D - B / 2), 0, 0))
    m.box(B, (S_ - 2 * D - 2 * B) * math.sqrt(2) - 0.06, D, 'wood_dark', M @ R(45, 'Z'))
    return m


# ---------------------------------------------------------------- assets
if fam.wants('SK_BusStopSign'):
    fam.asset('SK_BusStopSign', [('SK_BusStopSign_Mesh', bus_stop_sign(), None, None)], budget=BUDGET,
              notes='Soviet bus stop sign (map id bus_stop_sign): 2.4 m grey pipe, round two-faced plate r 0.27 m centred at 2.62 m '
                    '(white rim, yellow field, black "A"), white route plate on the -Y side at 1.95 m. Layered geometry, no textures.')

if fam.wants('SK_Sign_NoSwimming'):
    fam.asset('SK_Sign_NoSwimming', [('SK_Sign_NoSwimming_Mesh', sign_no_swimming(), None, None)], budget=BUDGET,
              notes='Beach sign (map id sign_no_swimming): two wooden posts 1.9 m, board 1.4 x 0.7 m at 1.55 m; its -Y face uses '
                    'material SK_Text_NoSwimming (512 x 256 generated texture SK_Text_NoSwimming.png, red "КУПАТЬСЯ ЗАПРЕЩЕНО" on white). '
                    'Posts can be sunk 0.2-0.3 m into the sand.')
    ob = fam.assets[-1]['objects'][0]
    ob.data.materials[1] = text_material()

for name, gap in (('SK_PipeSupport_040', 0.4), ('SK_PipeSupport_080', 0.8)):
    if fam.wants(name):
        mesh, zc = pipe_support(gap)
        fam.asset(name, [(name + '_Mesh', mesh, None, None)], budget=BUDGET, sockets=[('SOCKET_PipeAxis', (0, 0, zc))],
                  notes=f'Rusty steel saddle (map id pipe_support) for a d 0.8 m pipe running along X with its underside {gap} m above '
                        f'the sand; pipe axis at z = {zc:.2f} m (socket SOCKET_PipeAxis). Strap over the top shows the pipe position; '
                        'space supports every 4-6 m.')

if fam.wants('SK_AdColumn'):
    fam.asset('SK_AdColumn', [('SK_AdColumn_Mesh', ad_column(), None, None)], budget=BUDGET,
              notes='Round advertising column (Litfass style, map id ad_pole): d 1.2 m, 3.2 m with the green cap and finial, '
                    'plinth, coloured poster panels (geometry, no atlas).')

for name, seed, size, squash, stretch, n, tilt, note in ROCKS:
    if fam.wants(name):
        fam.asset(name, [(name + '_Mesh', rock(seed, size, squash, stretch, n, tilt), None, None)], budget=ROCK_BUDGET,
                  notes=f'Stylised faceted rock (map id rock), {note}: convex hull, flat base on z = 0; sink 5-15 % into the '
                        'terrain and rotate/scale freely (uniform 0.8-1.2).')

if fam.wants('SK_CCTV_Wall'):
    fam.asset('SK_CCTV_Wall', [('SK_CCTV_Wall_Mesh', cctv_wall_bracket(), None, None),
                               ('SK_CCTV_Wall_Head', cctv_head_mesh((0, -0.22, 0.155)), (0, -0.22, 0.155), None)],
              budget=BUDGET, ground=False, wall_mounted=True,
              notes='Security camera on a wall bracket (map id cctv_camera, elite hill). Wall = plane y = 0, pivot = bottom of the '
                    'wall plate; camera looks to -Y, tilted 15 deg down. The head is a child with its pivot on the pan joint '
                    '(0, -0.22, 0.155): rotate about local Z to pan.')

if fam.wants('SK_CCTV_Pole'):
    fam.asset('SK_CCTV_Pole', [('SK_CCTV_Pole_Mesh', cctv_pole(), None, None),
                               ('SK_CCTV_Pole_Head', cctv_head_mesh((0, -0.35, 3.0)), (0, -0.35, 3.0), None)], budget=BUDGET,
              notes='Security camera on a 3 m pipe pole with a flange, junction box and arm to -Y (map id cctv_camera, elite hill). '
                    'The head is a child with its pivot on the pan joint (0, -0.35, 3.0): rotate about local Z to pan.')

if fam.wants('SK_DefaultCrate'):
    fam.asset('SK_DefaultCrate', [('SK_DefaultCrate_Mesh', default_crate(), None, None)], budget=BUDGET,
              notes='Neutral 0.6 m wooden crate (map id default_crate), fallback for any missing prop: framed boards with diagonal '
                    'braces on the four sides and the lid. Collider: one box 0.6 m.')

if fam.wants('SK_Sign_NoSwimming'):                                   # texture next to the FBX, packed into the .blend
    img = text_image()
    img.filepath_raw = str(fam.dir / f'{TEXT_NAME}_{fam.rev}.png')
    img.file_format = 'PNG'
    img.save()
    img.pack()
fam.finish()
