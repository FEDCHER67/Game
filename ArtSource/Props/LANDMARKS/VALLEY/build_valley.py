"""LANDMARKS / VALLEY - landmarks of the small valley: casino crown sign 'КАЗИНО' with bulb dots,
nightclub neon shapes (bars, star, cocktail glass), giant bowling pin and ball for the bowling hall roof, two billboards, a roadside gas pump.

Emissive parts (bulbs, neon tubes) are the child mesh <Asset>_Emissive. Run from the repository root
(bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/LANDMARKS/VALLEY/build_valley.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/LANDMARKS/VALLEY/build_valley.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import landmarks as lm
from landmarks import Mesh, T, R

fam = lm.Family('LM-VALLEY', __file__)


# ---------------------------------------------------------------- casino crown sign (stands on a flat roof)
def casino_sign():
    """Board 7.0 x 1.6 m with gold letters КАЗИНО, a five-point crown on top, a bulb chase border, roof trestles behind.
    Returns (body, emissive)."""
    m, e = Mesh(), Mesh()
    W, H, D = 7.0, 1.6, 0.30
    zb = 0.9                                                                                     # board bottom above roof
    # roof trestles: two A-frames and a cross brace behind the board
    for x in (-2.4, 2.4):
        m.box(0.30, 1.40, 0.10, 'metal_dark', at=(x, 0.45, 0), base=True)                        # foot rail
        m.beam((x, -0.05, 0.05), (x, -0.05, zb + H * 0.9), 0.14, 0.14, 'metal_dark', up=(0, 1, 0))             # front post
        m.beam((x, 1.05, 0.05), (x, 0.05, zb + H * 0.8), 0.10, 0.10, 'metal_dark', up=(1, 0, 0))  # rear strut
    m.beam((-2.4, 0.12, zb * 0.6), (2.4, 0.12, zb * 0.6), 0.08, 0.08, 'metal_dark')
    # board: dark red box with a gold rim
    m.bevel_box(W, D, H, 0.05, 'sign_red', at=(0, 0, zb + H / 2))
    m.box(W + 0.16, D - 0.10, 0.10, 'yellow', at=(0, 0, zb - 0.02))
    m.box(W + 0.16, D - 0.10, 0.10, 'yellow', at=(0, 0, zb + H + 0.02))
    for x in (-W / 2 - 0.03, W / 2 + 0.03):
        m.box(0.10, D - 0.12, H + 0.12, 'yellow', at=(x, 0, zb + H / 2))
    # letters (gold, proud of the front face)
    lm.word(m, 'КАЗИНО', 1.05, 'yellow', y=-D / 2 - 0.05, z0=zb + 0.27, stroke_w=0.17, depth=0.10, gap=0.14)
    # crown: purple band with five points, a ball on each point, a red gem in the middle
    zc = zb + H + 0.07
    cw = 3.0
    tips = []
    for i in range(5):
        x = -cw / 2 + cw * i / 4
        h = (1.25, 0.95, 1.55, 0.95, 1.25)[i]
        tips.append((x * 0.96, zc + h))
    # crown as a band plus one convex prism per point
    base_h = 0.42
    m.prism([(-cw / 2, zc), (cw / 2, zc), (cw / 2, zc + base_h), (-cw / 2, zc + base_h)], 0.20, 'purple', M=T(0, 0, 0))
    for i, (x, zt) in enumerate(tips):
        hw = 0.36 if i != 2 else 0.42
        m.prism([(x - hw, zc + base_h - 0.01), (x + hw, zc + base_h - 0.01), (x, zt)], 0.18, 'purple')
        lm.ball(m, 0.13, 'yellow', at=(x, 0, zt + 0.08), seg=6, rings=3)
    m.box(cw + 0.10, 0.26, 0.10, 'yellow', at=(0, 0, zc + 0.04))                                  # crown rim
    lm.ball(m, 0.16, 'sign_red', at=(0, -0.12, zc + 0.22), seg=6, rings=3)                        # gem
    for x in (-0.9, 0.9):
        lm.ball(m, 0.10, 'sign_blue', at=(x, -0.11, zc + 0.22), seg=6, rings=3)
    # bulb dots: chase border around the board front and along the crown band
    y = -D / 2 - 0.01
    nx, nz = 18, 4
    for i in range(nx + 1):
        x = -W / 2 + 0.12 + (W - 0.24) * i / nx
        lm.bulb(e, 0.045, 'glow', (x, y + 0.01, zb + 0.10))
        lm.bulb(e, 0.045, 'glow', (x, y + 0.01, zb + H - 0.10))
    for k in range(1, nz):
        z = zb + 0.10 + (H - 0.20) * k / nz
        lm.bulb(e, 0.045, 'glow', (-W / 2 + 0.12, y + 0.01, z))
        lm.bulb(e, 0.045, 'glow', (W / 2 - 0.12, y + 0.01, z))
    for i in range(9):
        lm.bulb(e, 0.045, 'glow', (-cw / 2 + 0.2 + (cw - 0.4) * i / 8, -0.11, zc + 0.30))
    return m, e


# ---------------------------------------------------------------- nightclub neon (wall mounted, wall plane y = 0)
def neon_mount(m, pts_xz, standoff):
    """Clear acrylic-ish rail behind the tubes plus little stand-off clips; tubes sit at y = -standoff."""
    xs = [p[0] for p in pts_xz]
    zs = [p[1] for p in pts_xz]
    for z in (min(zs) + 0.05, max(zs) - 0.05):
        m.box(max(xs) - min(xs) + 0.2, 0.03, 0.05, 'metal_dark', at=((max(xs) + min(xs)) / 2, -0.015, z))
    for x, z in pts_xz:
        m.box(0.04, standoff, 0.04, 'metal', at=(x, -standoff / 2, z))


def neon_bars():
    """Three stacked neon bars: a zig-zag, a straight double bar and a wave, 3.0 m wide - the club facade 'lines'."""
    m, e = Mesh(), Mesh()
    so, r = 0.10, 0.028
    W = 3.0
    zig = [(-W / 2 + W * i / 12, 1.05 + (0.12 if i % 2 else -0.12)) for i in range(13)]
    lm.path_xz(e, zig, r, 'pink', M=T(0, -so, 0))
    for z in (0.62, 0.50):
        lm.path_xz(e, [(-W / 2, z), (W / 2, z)], r, 'teal', M=T(0, -so, 0))
    wave = [(-W / 2 + W * i / 16, 0.15 + 0.10 * math.sin(i * math.pi / 4)) for i in range(17)]
    lm.path_xz(e, wave, r, 'purple', M=T(0, -so, 0))
    for cap in (zig[0], zig[-1], wave[0], wave[-1], (-W / 2, 0.56), (W / 2, 0.56)):               # electrode caps
        m.cyl(0.045, 0.08, 6, 'black', M=T(cap[0], -so, cap[1]) @ R(90, 'Y'), at=(0, 0, -0.04))
    neon_mount(m, [(-1.3, 1.05), (0.0, 0.93), (1.3, 1.05), (-1.3, 0.56), (1.3, 0.56), (-1.0, 0.15), (1.0, 0.15)], so)
    m.box(0.30, 0.10, 0.18, 'metal_dark', at=(W / 2 + 0.25, -0.05, 0.0), base=True)               # transformer box
    return m, e


def neon_star():
    """Five-point star outline 1.6 m tall, doubled (yellow outer, pink inner)."""
    m, e = Mesh(), Mesh()
    so = 0.10
    def star(R_, r_, cz):
        return [((R_ if i % 2 == 0 else r_) * math.cos(math.pi / 2 + math.pi * i / 5),
                 cz + (R_ if i % 2 == 0 else r_) * math.sin(math.pi / 2 + math.pi * i / 5)) for i in range(10)]
    lm.ring_xz(e, star(0.80, 0.36, 0.82), 0.03, 'yellow', M=T(0, -so, 0))
    lm.ring_xz(e, star(0.52, 0.23, 0.82), 0.025, 'pink', M=T(0, -so - 0.02, 0))
    neon_mount(m, [(p[0] * 0.95, p[1]) for p in star(0.80, 0.36, 0.82)[1::2]], so)
    m.box(0.24, 0.10, 0.16, 'metal_dark', at=(0.0, -0.05, 0.0), base=True)
    return m, e


def neon_cocktail():
    """Martini glass outline 1.8 m tall with an olive on a pick and a straw, plus three rising bubbles."""
    m, e = Mesh(), Mesh()
    so = 0.10
    glass = [(-0.70, 1.60), (0.70, 1.60), (0.05, 0.85), (0.05, 0.22), (0.42, 0.10), (-0.42, 0.10), (-0.05, 0.22),
             (-0.05, 0.85)]
    lm.ring_xz(e, glass, 0.03, 'teal', M=T(0, -so, 0))
    lm.path_xz(e, [(-0.50, 1.40), (0.50, 1.40)], 0.026, 'teal', M=T(0, -so, 0))                     # liquid line
    lm.path_xz(e, [(0.20, 1.12), (0.62, 1.84)], 0.022, 'yellow', M=T(0, -so - 0.03, 0))              # pick
    lm.ring_xz(e, lm.circle_pts(0.12, 0.12, 8, 0.33, 1.26), 0.026, 'green', M=T(0, -so - 0.03, 0))  # olive
    lm.path_xz(e, [(-0.30, 1.30), (-0.52, 1.95), (-0.70, 1.95)], 0.022, 'pink', M=T(0, -so - 0.03, 0))  # straw
    for i, (x, z) in enumerate(((0.80, 1.90), (0.95, 2.15), (0.78, 2.35))):
        lm.ring_xz(e, lm.circle_pts(0.06 + 0.01 * i, 0.06 + 0.01 * i, 6, x, z), 0.018, 'pink', M=T(0, -so, 0))
    neon_mount(m, [(-0.55, 1.60), (0.55, 1.60), (0.0, 0.60), (-0.35, 0.10), (0.35, 0.10)], so)
    m.box(0.24, 0.10, 0.16, 'metal_dark', at=(0.6, -0.05, 0.0), base=True)
    return m, e


# ---------------------------------------------------------------- bowling hall roof
PIN_PROFILE = [  # (radius, height) of a standard pin scaled to 4.2 m, roughly the real silhouette
    (0.0, 0.0), (0.42, 0.0), (0.55, 0.30), (0.77, 0.95), (0.80, 1.30), (0.74, 1.75), (0.56, 2.25), (0.36, 2.70),
    (0.32, 2.95), (0.38, 3.30), (0.44, 3.60), (0.40, 3.90), (0.26, 4.12), (0.0, 4.20)]


def bowling_pin():
    """Giant white pin 4.2 m with two red neck stripes, bolted to a roof plinth with three guy brackets."""
    m = Mesh()
    zb = 0.30
    m.cyl(0.95, 0.30, 8, 'concrete_dark')                                                         # roof plinth
    prof = list(PIN_PROFILE)
    prof.insert(8, (0.34, 2.80)); prof.insert(9, (0.33, 2.86))                                    # thin white gap
    cols = ['white'] * (len(prof) - 1)
    cols[7], cols[9] = 'sign_red', 'sign_red'
    m.lathe(prof, 12, 'white', T(0, 0, zb), cols=cols)
    for k in range(3):
        a = math.tau * k / 3
        c, s = math.cos(a), math.sin(a)
        m.beam((0.5 * c, 0.5 * s, 0.30), (0.78 * c, 0.78 * s, 1.0), 0.06, 0.06, 'metal_dark', up=(0, 0, 1))
        m.box(0.16, 0.16, 0.05, 'metal', at=(0.5 * c, 0.5 * s, 0.30), base=True)
    return m



def bowling_ball():
    """Giant ball 2.4 m in a cradle: blue ball with three dark finger holes and a swirl band, steel cradle ring."""
    m = Mesh()
    r = 1.2
    zc = 0.25 + 0.30 + r * 0.75
    m.cyl(1.05, 0.25, 8, 'concrete_dark')                                                         # roof plinth
    m.cyl(0.55, zc - 0.6 * r - 0.25, 8, 'metal_dark', r_top=0.40, at=(0, 0, 0.25))                # cradle stem
    for k in range(4):                                                                            # cradle arms
        a = math.tau * (k + 0.5) / 4
        m.beam((0.35 * math.cos(a), 0.35 * math.sin(a), zc - 0.6 * r - 0.05),
               (0.95 * math.cos(a), 0.95 * math.sin(a), zc - 0.6 * r), 0.08, 0.08, 'metal_dark')
    lm.ring_xz(m, lm.circle_pts(0.96, 0.96, 8), 0.06, 'metal', M=T(0, 0, zc - 0.6 * r) @ R(90, 'X'))  # cradle ring
    # the ball: tilted so the finger holes face front-up; a swirl band of a second blue
    rings = 8
    prof = [(r * math.sin(math.pi * i / rings), -r * math.cos(math.pi * i / rings)) for i in range(rings + 1)]
    prof[0], prof[-1] = (0.0, -r), (0.0, r)
    cols = ['blue'] * rings
    cols[4] = 'sign_blue'
    Mb = T(0, 0, zc) @ R(-35, 'X') @ R(20, 'Y')
    m.lathe(prof, 12, 'blue', Mb, cols=cols)
    for ang, rot in ((0, -16), (-14, 12), (14, 12)):                                              # finger holes
        Mh = Mb @ R(rot + 20, 'X') @ R(ang, 'Y') @ T(0, 0, r - 0.08)
        m.cyl(0.13, 0.14, 8, 'black', Mh)
        m.cyl(0.16, 0.04, 8, 'metal_dark', Mh, at=(0, 0, 0.10))
    return m


# ---------------------------------------------------------------- billboards (poster face: material LM_Poster, UV 0..1)
def billboard_large():
    """6.0 x 3.0 m poster on a single steel mast 5 m high: frame, catwalk with railing, three flood lamps, ladder."""
    m, p = Mesh(), Mesh()
    W, H, zb = 6.0, 3.0, 5.0
    m.cyl(0.45, 0.30, 8, 'concrete')                                                              # footing
    m.cyl(0.24, zb + 0.4, 8, 'metal', r_top=0.20, at=(0, 0.25, 0.3))                               # mast
    m.box(1.2, 0.5, 0.25, 'metal_dark', at=(0, 0.25, zb - 0.25), base=True)                        # head
    for x in (-2.0, 2.0):
        m.beam((0, 0.25, zb - 0.8), (x, 0.25, zb), 0.12, 0.12, 'metal_dark', up=(0, 1, 0))         # outriggers
    m.bevel_box(W + 0.3, 0.30, H + 0.3, 0.04, 'metal_dark', at=(0, 0.15, zb + H / 2))              # frame / back
    lm.poster_face_box(p, W, H, 0.04, 'white', M=T(0, -0.02, zb + H / 2))
    m.box(W + 0.3, 0.80, 0.06, 'metal', at=(0, -0.35, zb - 0.10), base=True)                       # catwalk
    m.bar((-W / 2 - 0.15, -0.72, zb + 0.75), (W / 2 + 0.15, -0.72, zb + 0.75), 0.025, 'metal', seg=4)
    for x in (-W / 2 - 0.1, -1.0, 1.0, W / 2 + 0.1):
        m.bar((x, -0.72, zb - 0.04), (x, -0.72, zb + 0.76), 0.022, 'metal', seg=4)
    for x in (-2.0, 0.0, 2.0):                                                                     # flood lamps
        m.bar((x, -0.70, zb + 0.75), (x, -1.15, zb + 1.05), 0.03, 'metal_dark', seg=4)
        m.lathe([(0.0, 0.0), (0.16, 0.0), (0.10, 0.22), (0.0, 0.22)], 6, 'metal_dark',
                T(x, -1.15, zb + 1.05) @ R(-120, 'X'))
    for x in (-0.20, 0.20):                                                                        # ladder rails
        m.bar((x, 0.62, 0.3), (x, 0.62, zb - 0.05), 0.025, 'metal', seg=4)
    for i in range(9):
        m.bar((-0.20, 0.62, 0.8 + i * 0.5), (0.20, 0.62, 0.8 + i * 0.5), 0.018, 'metal', seg=4)
    return m, p


def billboard_small():
    """3.0 x 1.5 m poster on two square legs (town street size), with a little cornice and one lamp."""
    m, p = Mesh(), Mesh()
    W, H, zb = 3.0, 1.5, 1.6
    for x in (-1.0, 1.0):
        m.box(0.40, 0.40, 0.12, 'concrete', at=(x, 0.0, 0), base=True)
        m.box(0.12, 0.12, zb + H, 'metal_dark', at=(x, 0.02, 0.12), base=True)
        m.beam((x, 0.02, 0.6), (x, 0.40, 0.12), 0.06, 0.06, 'metal_dark', up=(1, 0, 0))            # back brace
    m.bevel_box(W + 0.20, 0.16, H + 0.20, 0.03, 'green', at=(0, 0.0, zb + H / 2))
    lm.poster_face_box(p, W, H, 0.03, 'white', M=T(0, -0.09, zb + H / 2))
    m.prism([(-W / 2 - 0.20, zb + H + 0.10), (W / 2 + 0.20, zb + H + 0.10), (W / 2 + 0.10, zb + H + 0.24),
             (-W / 2 - 0.10, zb + H + 0.24)], 0.30, 'green', M=T(0, -0.02, 0))                      # cornice
    for x in (-0.8, 0.8):                                                                          # two lamps
        m.bar((x, -0.08, zb + H + 0.16), (x, -0.50, zb + H + 0.30), 0.025, 'metal_dark', seg=4)
        m.lathe([(0.0, 0.0), (0.12, 0.0), (0.08, 0.16), (0.0, 0.16)], 6, 'metal_dark',
                T(x, -0.50, zb + H + 0.30) @ R(-125, 'X'))
    for x in (-W / 2 - 0.05, W / 2 + 0.05):                                                        # side pilasters
        m.bevel_box(0.14, 0.24, H + 0.36, 0.03, 'green', at=(x, 0.0, zb + H / 2 + 0.02))
    m.box(W + 0.30, 0.22, 0.08, 'green', at=(0, 0.0, zb - 0.08))                                    # bottom sill
    return m, p


# ---------------------------------------------------------------- roadside gas pump
def gas_pump():
    """90s roadside pump on a concrete island: white body, red hood, lit price box, two counter windows, hose to a
    nozzle in the holster on +X, yellow-black bollards. Returns (body, emissive, nozzle)."""
    m, e, n = Mesh(), Mesh(), Mesh()
    m.bevel_box(1.9, 0.9, 0.15, 0.04, 'concrete', base=True)                                       # island
    m.box(1.9, 0.9, 0.02, 'yellow', at=(0, 0, 0.15), base=True)                                     # painted kerb top
    for x in (-0.80, 0.80):                                                                         # bollards
        m.cyl(0.08, 0.80, 6, 'yellow', at=(x, 0, 0.17))
        m.cyl(0.085, 0.14, 6, 'black', at=(x, 0, 0.45))
        m.cyl(0.085, 0.12, 6, 'black', at=(x, 0, 0.75))
    W, D, zb = 0.70, 0.45, 0.17
    m.bevel_box(W + 0.06, D + 0.06, 0.20, 0.02, 'metal_dark', at=(0, 0, zb), base=True)              # plinth
    m.bevel_box(W, D, 1.05, 0.03, 'white', at=(0, 0, zb + 0.20), base=True)                          # lower body
    m.bevel_box(W + 0.04, D + 0.04, 0.40, 0.04, 'red', at=(0, 0, zb + 1.25), base=True)              # hood
    m.box(W + 0.05, D + 0.05, 0.05, 'metal', at=(0, 0, zb + 1.22), base=True)                        # chrome belt
    for y in (-1, 1):                                                                                # counter windows
        m.box(0.46, 0.02, 0.26, 'metal_dark', at=(0, y * (D / 2 + 0.005), zb + 0.98))
        e.box(0.40, 0.02, 0.20, 'glow', at=(0, y * (D / 2 + 0.012), zb + 0.98))
        for k in range(3):
            m.box(0.10, 0.012, 0.04, 'black', at=(-0.12 + k * 0.12, y * (D / 2 + 0.024), zb + 0.94))  # digit wheels
        m.box(0.50, 0.03, 0.30, 'red', at=(0, y * (D / 2 + 0.01), zb + 0.50))                        # fuel grade panel
        m.box(0.30, 0.035, 0.10, 'white', at=(0, y * (D / 2 + 0.012), zb + 0.55))
    # price lightbox on a short stem
    m.box(0.10, 0.10, 0.20, 'metal_dark', at=(0, 0, zb + 1.65), base=True)
    m.bevel_box(0.80, 0.22, 0.40, 0.03, 'red', at=(0, 0, zb + 1.85), base=True)
    for y in (-1, 1):
        e.box(0.70, 0.02, 0.30, 'white', at=(0, y * 0.115, zb + 2.05))
    # holster on +X, hose from the body to the nozzle
    m.box(0.10, 0.18, 0.22, 'metal_dark', at=(W / 2 + 0.05, -0.08, zb + 0.95), base=True)
    m.cyl(0.06, 0.06, 6, 'black', M=T(W / 2, 0.12, zb + 0.70) @ R(90, 'Y'))                          # hose outlet
    m.tube_path([(W / 2 + 0.05, 0.12, zb + 0.70), (W / 2 + 0.30, 0.14, zb + 0.45), (W / 2 + 0.36, 0.05, zb + 0.30),
                 (W / 2 + 0.30, -0.10, zb + 0.55), (W / 2 + 0.16, -0.10, zb + 0.95)], 0.03, 6, 'rubber')
    # nozzle: separate object, pivot at the holster mouth so it can be lifted out
    p = (W / 2 + 0.12, -0.08, zb + 1.05)
    n.box(0.06, 0.06, 0.20, 'black', at=(p[0], p[1], p[2] - 0.10), base=True)                       # grip
    n.beam((p[0], p[1], p[2] + 0.06), (p[0] - 0.04, p[1], p[2] - 0.12), 0.03, 0.03, 'metal', up=(1, 0, 0))  # spout
    n.box(0.05, 0.10, 0.03, 'metal_dark', at=(p[0] + 0.02, p[1], p[2] - 0.04))                      # lever guard
    return m, e, n, p


# ---------------------------------------------------------------- assets
def two(name, fn, **kw):
    if not fam.wants(name):
        return None
    body, emis = fn()
    return fam.asset(name, [(name + '_Mesh', body, None, None), (name + '_Emissive', emis, None, None)], **kw)


two('LM_CasinoCrownSign', casino_sign,
    notes='Roof sign 7.0 x 1.6 m, letters КАЗИНО, crown with five points, bulb dots in LM_CasinoCrownSign_Emissive. '
          'Stands on a flat roof: pivot = centre of the trestle feet, front -Y.')
for name, fn, txt in (('LM_Neon_Bars', neon_bars, 'Three neon bars 3.0 m wide (zig-zag pink, double teal, wave purple).'),
                      ('LM_Neon_Star', neon_star, 'Five-point star 1.6 m, yellow outer and pink inner tube.'),
                      ('LM_Neon_Cocktail', neon_cocktail, 'Martini glass 1.8 m with olive, straw and bubbles.')):
    two(name, fn, wall_mounted=True,
        notes=txt + f' Wall-mounted: wall plane y = 0, tubes 0.10 m in front, pivot on the wall at the bottom of the '
                    f'transformer box. Tubes = {name}_Emissive.')
if fam.wants('LM_BowlingPin_Giant'):
    fam.asset('LM_BowlingPin_Giant', [('LM_BowlingPin_Giant_Mesh', bowling_pin(), None, None)],
              notes='Roof pin 4.5 m on a 1.9 m plinth; pivot = plinth centre on the roof.')
if fam.wants('LM_BowlingBall_Giant'):
    fam.asset('LM_BowlingBall_Giant', [('LM_BowlingBall_Giant_Mesh', bowling_ball(), None, None)],
              notes='Roof ball 2.4 m in a steel cradle, three finger holes to the front-top; pivot = plinth centre.')
for name, fn, txt in (('LM_Billboard_Large', billboard_large, 'Poster 6.0 x 3.0 m on a 5 m mast with catwalk and lamps.'),
                      ('LM_Billboard_Small', billboard_small, 'Poster 3.0 x 1.5 m on two legs, street size.')):
    if fam.wants(name):
        body, poster = fn()
        fam.asset(name, [(name + '_Mesh', body, None, None), (name + '_Poster', poster, None, None)],
                  notes=txt + ' Poster face (-Y) = material LM_Poster, UV 0..1 over the poster, aspect 2:1.')
        lm.use_poster(fam.assets[-1]['objects'][1])
if fam.wants('LM_GasPump'):
    body, emis, nozzle, piv = gas_pump()
    fam.asset('LM_GasPump', [('LM_GasPump_Mesh', body, None, None), ('LM_GasPump_Emissive', emis, None, None),
                             ('LM_GasPump_Nozzle', nozzle, piv, None)],
              sockets=[('SOCKET_Interact', (0.0, -0.75, 1.0)), ('SOCKET_Refuel', (0.9, -0.6, 0.6))],
              notes='Roadside pump on a 1.9 x 0.9 m island; counter windows on -Y and +Y, price box on top '
                    '(LM_GasPump_Emissive). LM_GasPump_Nozzle has its pivot at the holster mouth (can be lifted out). '
                    'SOCKET_Interact = where the player stands, SOCKET_Refuel = where a car filler should be.')

fam.finish()
