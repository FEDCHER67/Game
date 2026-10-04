"""STREET_KIT / PLAYGROUND - Soviet courtyard playground set: A-frame swings, slide, hand-pushed carousel,
sandbox with the "mushroom" shade, triple horizontal bar (turnik) and a carpet-beating rack.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/PLAYGROUND/build_playground.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/PLAYGROUND/build_playground.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import streetkit as sk
from streetkit import Mesh, T, R

fam = sk.Family('SK-PLAYGROUND', __file__)
PIPE = 0.045              # main frame pipe radius
ROD = 0.014               # thin rods (hangers, rungs, bars)


def rust_band(m, p0, p1, t0, t1, r):
    """Short rust collar around a straight pipe between fractions t0..t1 of p0->p1."""
    a = [p0[i] + (p1[i] - p0[i]) * t0 for i in range(3)]
    b = [p0[i] + (p1[i] - p0[i]) * t1 for i in range(3)]
    m.bar(a, b, r + 0.005, 'rust', seg=6)


def foot(m, x, y, col='concrete_dark'):
    m.bevel_box(0.16, 0.16, 0.05, 0.015, col, at=(x, y, 0), base=True)


# ---------------------------------------------------------------- 1. swings
SW_TOP = 2.25
SW_SEATS = (-0.65, 0.65)


def swings_frame():
    m = Mesh()
    for x in (-1.5, 1.5):
        for y in (-0.8, 0.8):
            foot(m, x, y)
            m.bar((x, y, 0.04), (x, 0, SW_TOP + 0.02), PIPE, 'red', seg=8)          # A leg
        m.bar((x, -0.52, 0.75), (x, 0.52, 0.75), 0.03, 'red', seg=6)                  # A cross brace
        rust_band(m, (x, -0.8, 0.04), (x, 0, SW_TOP), 0.04, 0.16, PIPE)
    m.bar((-1.62, 0, SW_TOP), (1.62, 0, SW_TOP), 0.05, 'yellow', seg=8)              # top bar along X
    m.cyl(0.055, 0.04, 8, 'yellow', M=T(-1.66, 0, SW_TOP) @ R(90, 'Y'), at=(0, 0, 0))  # end plugs
    m.cyl(0.055, 0.04, 8, 'yellow', M=T(1.62, 0, SW_TOP) @ R(90, 'Y'), at=(0, 0, 0))
    rust_band(m, (-1.62, 0, SW_TOP), (1.62, 0, SW_TOP), 0.28, 0.33, 0.05)
    return m


def swing_seat(x, seat_col):
    m = Mesh()
    zs = 0.45
    for dx in (-0.22, 0.22):
        m.cyl(0.065, 0.05, 8, 'metal_dark', M=T(x + dx - 0.025, 0, SW_TOP) @ R(90, 'Y'))   # bearing collar on the bar
        m.bar((x + dx, 0, SW_TOP - 0.05), (x + dx, 0, zs + 0.02), ROD, 'metal', seg=6)     # rigid hanger rod
    m.bevel_box(0.56, 0.26, 0.045, 0.012, seat_col, at=(x, 0, zs))                          # seat board
    m.bevel_box(0.50, 0.04, 0.05, 0.01, 'metal_dark', at=(x, 0, zs - 0.045))                # seat bracket
    return m


# ---------------------------------------------------------------- 2. slide
PL_Z = 1.45               # platform top
PL_X0, PL_X1 = -1.0, -0.4 # platform extent in X
CH_W = 0.50               # chute width


def slide():
    m = Mesh()
    # ladder: two rails leaning from the ground up to the platform, continuing up as hand grips
    lx0, lx1 = -1.75, -1.02
    for y in (-0.27, 0.27):
        foot(m, lx0, y)
        m.tube_path([(lx0, y, 0.04), (lx1, y, PL_Z), (lx1 + 0.04, y, PL_Z + 0.75), (PL_X0 + 0.25, y, PL_Z + 0.85)],
                    PIPE * 0.8, 6, 'blue')
    for k in range(1, 6):
        t = k / 6
        x = lx0 + (lx1 - lx0) * t
        z = 0.04 + (PL_Z - 0.04) * t
        m.bar((x, -0.27, z), (x, 0.27, z), 0.02, 'yellow', seg=6)                           # rungs
    # platform with two back posts
    m.bevel_box(PL_X1 - PL_X0 + 0.04, 0.62, 0.06, 0.015, 'wood_dark', at=((PL_X0 + PL_X1) / 2, 0, PL_Z - 0.03))
    for y in (-0.27, 0.27):
        foot(m, PL_X1 - 0.04, y)
        m.bar((PL_X1 - 0.04, y, 0.04), (PL_X1 - 0.04, y, PL_Z - 0.04), PIPE * 0.8, 'blue', seg=6)
        # handrail: from the ladder grip over the platform down to the chute start
        m.tube_path([(PL_X0 + 0.25, y, PL_Z + 0.85), (PL_X1 - 0.05, y, PL_Z + 0.85), (PL_X1 + 0.12, y, PL_Z + 0.03)],
                    0.03, 6, 'red')
        rust_band(m, (PL_X1 - 0.04, y, 0.04), (PL_X1 - 0.04, y, PL_Z), 0.02, 0.10, PIPE * 0.8)
    m.bar((PL_X1 - 0.04, -0.27, 0.6), (PL_X1 - 0.04, 0.27, 0.6), 0.02, 'blue', seg=6)      # back brace
    # chute: sloped bed from the platform edge down to a flat run-out, with side lips
    s0 = (PL_X1 - 0.02, PL_Z - 0.02)
    s1 = (1.55, 0.38)
    s2 = (2.15, 0.38)
    def strip(y, d, lo, hi, col):
        # sloped piece and flat run-out as two convex prisms meeting on a vertical cut at s1 (no overlap seams)
        m.prism([(s0[0], s0[1] + lo), (s1[0], s1[1] + lo), (s1[0], s1[1] + hi), (s0[0], s0[1] + hi)], d, col, M=T(0, y, 0))
        m.prism([(s1[0], s1[1] + lo), (s2[0], s2[1] + lo), (s2[0], s2[1] + hi), (s1[0], s1[1] + hi)], d, col, M=T(0, y, 0))
    strip(0, CH_W, -0.02, 0.02, 'chrome')                                                    # chute bed
    for y in (-CH_W / 2 - 0.02, CH_W / 2 + 0.02):
        strip(y, 0.05, -0.03, 0.14, 'yellow')                                                # side lips
    # supports under the slope and the run-out
    slope = (s0[1] - s1[1]) / (s1[0] - s0[0])
    xm = 0.55
    zm = s0[1] - (xm - s0[0]) * slope - 0.03
    for y in (-0.2, 0.2):
        foot(m, xm, y)
        m.bar((xm, y, 0.04), (xm, y, zm), 0.03, 'blue', seg=6)
        foot(m, 2.0, y)
        m.bar((2.0, y, 0.04), (2.0, y, s2[1] - 0.03), 0.03, 'blue', seg=6)
    return m


# ---------------------------------------------------------------- 3. carousel
CR_R = 1.0
CR_Z0, CR_Z1 = 0.30, 0.38     # disc underside / top


def carousel_base():
    m = Mesh()
    m.cyl(0.40, 0.10, 10, 'concrete', at=(0, 0, 0))
    m.cyl(0.16, 0.10, 8, 'metal_dark', r_top=0.10, at=(0, 0, 0.10))
    m.cyl(0.05, CR_Z0 - 0.18 + 0.02, 8, 'metal', at=(0, 0, 0.18))        # axle stub up into the hub
    return m


def carousel_rotor():
    m = Mesh()
    seg = 12
    m.lathe([(0.12, CR_Z0 - 0.04), (CR_R - 0.05, CR_Z0), (CR_R, CR_Z0 + 0.02), (CR_R, CR_Z1), (0.0, CR_Z1)], seg, 'wood',
            cols=['metal_dark', 'red', 'red', 'wood'], offset=0)
    m.cyl(0.09, 0.62, 8, 'red', at=(0, 0, CR_Z1 - 0.02))                    # central post
    m.cyl(0.11, 0.05, 8, 'yellow', at=(0, 0, CR_Z1 + 0.58))                 # post cap
    cols = ('blue', 'yellow', 'green', 'blue', 'yellow', 'green')
    for k in range(6):
        a = TAU6 * k + TAU6 / 2
        c, s = math.cos(a), math.sin(a)
        r1 = CR_R - 0.12
        pts = [(0.06 * c, 0.06 * s, CR_Z1 + 0.52), (0.55 * c, 0.55 * s, CR_Z1 + 0.50),
               (r1 * c, r1 * s, CR_Z1 + 0.42), (r1 * c, r1 * s, CR_Z1 - 0.01)]
        m.tube_path(pts, 0.028, 6, cols[k])                                 # radial handrail spoke with upright
    # ring rail joining the spokes
    ring = [(0.55 * math.cos(math.tau * k / 12), 0.55 * math.sin(math.tau * k / 12), CR_Z1 + 0.50) for k in range(12)]
    m.tube_path(ring, 0.02, 6, 'metal', closed=True)
    return m


TAU6 = math.tau / 6


# ---------------------------------------------------------------- 4. sandbox with mushroom
SB = 2.0                  # outer size
SB_H = 0.28               # plank height


def sandbox():
    m = Mesh()
    t = 0.06
    h = SB / 2
    for i, (sx, sy, at) in enumerate(((SB, t, (0, -h + t / 2, 0)), (SB, t, (0, h - t / 2, 0)),
                                      (t, SB - 2 * t, (-h + t / 2, 0, 0)), (t, SB - 2 * t, (h - t / 2, 0, 0)))):
        m.bevel_box(sx, sy, SB_H, 0.012, 'wood' if i % 2 == 0 else 'wood_dark', at=at, base=True)
    m.box(SB - 2 * t, SB - 2 * t, 0.16, 'sand', at=(0, 0, 0), base=True)              # sand fill
    m.lathe([(0.35, 0.16), (0.18, 0.20), (0.0, 0.21)], 8, 'sand', M=T(0.45, -0.4, 0), offset=0.3)   # sand heap
    # triangular corner seats
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = (sx * (h - 0.01), sy * (h - 0.01))
            tri = [c, (c[0] - sx * 0.40, c[1]), (c[0], c[1] - sy * 0.40)]
            m.prism_xy(tri, SB_H, SB_H + 0.04, 'wood_dark')
    # mushroom: post + red cone roof with white spots
    m.cyl(0.07, 0.10, 8, 'concrete', at=(0, 0, 0.12))
    m.cyl(0.055, 1.80, 8, 'green', at=(0, 0, 0.16))
    rr, z0, z1 = 0.95, 1.78, 2.30
    m.lathe([(0.10, z0 + 0.02), (rr - 0.03, z0), (rr, z0 + 0.05), (0.0, z1)], 12, 'red', cols=['red', 'red', 'red'])
    rise = math.degrees(math.atan2(z1 - z0 - 0.05, rr))
    for k, (rs, ang) in enumerate(((0.62, 15), (0.66, 105), (0.58, 200), (0.64, 290), (0.30, 60), (0.28, 240))):
        z = z0 + 0.05 + (rr - rs) * (z1 - z0 - 0.05) / rr
        a = math.radians(ang)
        m.cyl(0.075 if rs > 0.4 else 0.055, 0.03, 8, 'white',
              M=T(rs * math.cos(a), rs * math.sin(a), z) @ R(ang, 'Z') @ R(rise, 'Y') @ T(0, 0, -0.015))
    return m


# ---------------------------------------------------------------- 5. triple horizontal bar
def horizontal_bar():
    m = Mesh()
    xs = (-1.65, -0.55, 0.55, 1.65)
    bars = (1.30, 1.80, 2.30)
    tops = (1.40, 1.90, 2.40, 2.40)
    for x, ztop in zip(xs, tops):
        m.cyl(0.12, 0.06, 8, 'concrete', at=(x, 0, 0))                  # concrete footing
        m.cyl(PIPE, ztop - 0.06, 8, 'blue', at=(x, 0, 0.06))
        m.cyl(PIPE + 0.012, 0.03, 8, 'blue', at=(x, 0, ztop))            # cap
        rust_band(m, (x, 0, 0.06), (x, 0, ztop), 0.0, 0.07, PIPE)
    for i, z in enumerate(bars):
        m.bar((xs[i] - 0.06, 0, z), (xs[i + 1] + 0.06, 0, z), 0.018, 'chrome', seg=6)
        for x in (xs[i], xs[i + 1]):
            m.cyl(PIPE + 0.012, 0.07, 8, 'yellow', at=(x, 0, z - 0.035))   # clamp collars
    return m


# ---------------------------------------------------------------- 6. carpet-beating rack
def carpet_rack():
    m = Mesh()
    W, H = 2.5, 2.0
    x0, x1 = -W / 2, W / 2
    for x in (x0, x1):
        m.cyl(0.13, 0.06, 8, 'concrete', at=(x, 0, 0))
        m.tube_path([(x, 0, 0.06), (x + (0.03 if x < 0 else -0.02), 0.01, 1.0), (x, 0, H)], PIPE, 8, 'green')   # slightly bent post
        m.bar((x, 0, 1.0), (x, 0.55, 0.04), 0.03, 'green', seg=6)                     # rear strut
        foot(m, x, 0.58)
        rust_band(m, (x, 0, 0.06), (x, 0, H), 0.0, 0.10, PIPE)
    m.tube_path([(x0 - 0.10, 0, H - 0.04), (-0.4, 0, H - 0.07), (0.4, 0, H - 0.08), (x1 + 0.10, 0, H - 0.04)], 0.035, 6, 'green')
    for z, sag in ((1.45, 0.04), (0.95, 0.02)):
        m.tube_path([(x0, 0, z), (0, 0, z - sag), (x1, 0, z)], 0.022, 6, 'metal')
    rust_band(m, (x0, 0, 1.45), (x1, 0, 1.45), 0.55, 0.75, 0.022)
    m.bar((-0.25, 0, H - 0.08), (0.10, 0, H - 0.085), 0.04, 'rust', seg=6)
    sk.jitter(m, 0.003, 11)
    return m


ASSETS = (
    ('SK_Play_Swings', lambda: [('SK_Play_Swings_Frame', swings_frame(), None, None),
                                ('SK_Play_Swings_SeatA', swing_seat(SW_SEATS[0], 'red'), (SW_SEATS[0], 0, SW_TOP), None),
                                ('SK_Play_Swings_SeatB', swing_seat(SW_SEATS[1], 'blue'), (SW_SEATS[1], 0, SW_TOP), None)],
     'A-frame pipe swing set, top bar 2.25 m along X; two seats on rigid rods, seat height 0.45 m. '
     'SeatA/SeatB pivots on the top-bar axis: rotate around local X to swing.'),
    ('SK_Play_Slide', lambda: [('SK_Play_Slide_Mesh', slide(), None, None)],
     'Ladder (5 rungs) from -X up to a 1.45 m platform with handrails, steel chute down to a flat run-out at +X (0.38 m).'),
    ('SK_Play_Carousel', lambda: [('SK_Play_Carousel_Base', carousel_base(), None, None),
                                  ('SK_Play_Carousel_Rotor', carousel_rotor(), (0, 0, 0), None)],
     'Hand-pushed round carousel, disc 2.0 m, top 0.38 m. Rotor pivot on the vertical axis (0,0,0): rotate around Z.'),
    ('SK_Play_Sandbox', lambda: [('SK_Play_Sandbox_Mesh', sandbox(), None, None)],
     'Square 2.0 m plank sandbox with triangular corner seats, sand fill and the central "mushroom" shade (red cone, white spots).'),
    ('SK_Play_HorizontalBar', lambda: [('SK_Play_HorizontalBar_Mesh', horizontal_bar(), None, None)],
     'Triple turnik: four posts, bars at 1.30 / 1.80 / 2.30 m.'),
    ('SK_Play_CarpetRack', lambda: [('SK_Play_CarpetRack_Mesh', carpet_rack(), None, None)],
     'Carpet-beating rack: two bent posts with rear struts, sagging top bar at ~1.95 m, two crossbars, rust patches.'),
)

for name, parts, notes in ASSETS:
    if fam.wants(name):
        fam.asset(name, parts(), notes=notes)

fam.finish()
