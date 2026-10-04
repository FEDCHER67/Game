"""STREET_KIT / WRECKS - generic boxy Soviet 1970s sedan as an abandoned wreck (faded, rusty, on bricks) and a burnt-out shell.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/WRECKS/build_wrecks.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/WRECKS/build_wrecks.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import streetkit as sk
from streetkit import Mesh, T, R
from mathutils import Vector

fam = sk.Family('SK-WRECKS', __file__)

# ---------------------------------------------------------------- body dimensions (car space: ground z=0, hubs at HUB, -Y = nose)
HL = 1.95                       # half length of the body tub (bumpers add 0.10 at each end -> ~4.1 m overall)
HUB = 0.30                      # hub height on inflated tyres
AXLES = (-1.22, 1.16)           # front / rear axle y
ARCH_R = 0.40                   # wheel opening radius
WX = 0.73                       # wheel centre x
SILL = 0.28                     # underside of the body
BELT = 0.88                     # beltline = bonnet / trunk deck height
GZ0, GZ1 = 0.88, 1.38           # greenhouse bottom / roof
GF0, GF1 = -0.78, -0.24         # windscreen base / top y
GR0, GR1 = 1.18, 0.92           # rear window base / top y
HW0, HW1 = 0.73, 0.61           # greenhouse half width at bottom / roof (tumblehome)


def lerp(a, b, t):
    return a + (b - a) * t


def _t(z):
    return (z - GZ0) / (GZ1 - GZ0)


def yf(z):
    return lerp(GF0, GF1, _t(z))


def yr(z):
    return lerp(GR0, GR1, _t(z))


def hw(z):
    return lerp(HW0, HW1, _t(z))


def gside(s, y, z):
    """Point on the greenhouse side plane (s = -1 left, +1 right)."""
    return Vector((s * hw(z), y, z))


# ---------------------------------------------------------------- extra closed primitives
def plate(m, pts, out, t, col, inset=0.004):
    """Planar convex polygon thickened along its normal (t outwards, `inset` inwards) - panels, glass, rust patches."""
    pts = [Vector(p) for p in pts]
    k = len(pts)
    n = Vector()
    for i in range(k):                                  # Newell normal
        a, b = pts[i], pts[(i + 1) % k]
        n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    n.normalize()
    if n.dot(Vector(out)) < 0:
        pts.reverse()
        n = -n
    v = [tuple(p - n * inset) for p in pts] + [tuple(p + n * t) for p in pts]
    f = [tuple(range(k - 1, -1, -1)), tuple(range(k, 2 * k))]
    for i in range(k):
        j = (i + 1) % k
        f.append((i, j, k + j, k + i))
    return m.shell(v, f, col)


def side_plate(m, s, x, poly_yz, t, col, inset=0.004):
    return plate(m, [(s * x, y, z) for y, z in poly_yz], (s, 0, 0), t, col, inset)


def dent(part, amount, seed):
    """Dent a plate()/beam built alone in `part`: outer and inner vertex rings move together, so thin panels never invert."""
    import random
    rnd = random.Random(seed)
    k = len(part.verts) // 2
    for i in range(k):
        d = Vector((rnd.uniform(-amount, amount) for _ in range(3)))
        for j in (i, i + k):
            part.verts[j] = tuple(Vector(part.verts[j]) + d)


def hexa(m, bot, top, col, cols=None):
    """Closed 8-vertex solid from a bottom and a top quad, both counter-clockwise seen from above."""
    v = [tuple(p) for p in bot] + [tuple(p) for p in top]
    f = [(3, 2, 1, 0), (4, 5, 6, 7)] + [(i, (i + 1) % 4, (i + 1) % 4 + 4, i + 4) for i in range(4)]
    return m.shell(v, f, col, cols=cols)


def hinged(m, part, hinge, axis, deg):
    """Merge `part` rotated about a hinge line through `hinge` along axis 'X'/'Y'/'Z'."""
    m.merge(part, T(*hinge) @ R(deg, axis) @ T(*(-c for c in hinge)))


# ---------------------------------------------------------------- shared body
def sedan(o):
    """Body shell in car space (no wheels). o: dict of variant options."""
    m = Mesh()
    C, LOW, LIP = o['paint'], o['lower'], o['lips']

    # -- tub (beltline block) and lower body between the wheel openings
    m.bevel_box(1.60, 2 * HL, BELT - 0.58, 0.06, C, at=(0, 0, 0.58), base=True)
    lower = Mesh()
    fa, ra = AXLES
    for y0, y1 in ((-HL, fa - ARCH_R), (fa + ARCH_R, ra - ARCH_R), (ra + ARCH_R, HL)):
        lower.bevel_box(1.58, y1 - y0, 0.60 - SILL, 0.05, LOW, at=(0, (y0 + y1) / 2, SILL), base=True)
    if o.get('dent_lower'):
        sk.jitter(lower, o['dent_lower'], 11)
    m.merge(lower)

    # -- wheel openings: dark half-disc wells + chunky arch lips
    disc = [(ARCH_R * math.cos(a), ARCH_R * math.sin(a)) for a in [math.radians(d) for d in (0, 45, 90, 135, 180)]]
    for ai, ay in enumerate(AXLES):
        for s in (-1, 1):
            m.prism(disc, 0.012, 'black', M=T(s * 0.809, ay, SILL) @ R(90, 'Z'))
            lr = ARCH_R + 0.03
            m.tube_path([(s * 0.815, ay + lr * math.cos(math.radians(d)), SILL + lr * math.sin(math.radians(d)))
                         for d in (0, 45, 90, 135, 180)], 0.045, 4, LIP(s, ai))

    # -- doors (proud panels) with dark seams and chrome handles
    for s in (-1, 1):
        for dk, poly in enumerate(([(-0.76, 0.36), (0.24, 0.36), (0.24, 0.865), (-0.76, 0.865)],
                                   [(0.27, 0.36), (0.74, 0.36), (0.98, 0.70), (0.98, 0.865), (0.27, 0.865)])):
            d = Mesh()
            side_plate(d, s, 0.80, poly, 0.012, o['door_col'](s, dk))
            if o.get('dent_doors'):
                dent(d, o['dent_doors'], 31 + dk + 2 * (s > 0))
            ajar = o.get('door_ajar')
            if ajar and ajar[0] == s and ajar[1] == dk:
                hinged(m, d, (s * 0.80, poly[0][0], 0), 'Z', -s * ajar[2])
            else:
                m.merge(d)
        for y in (-0.775, 0.255):
            m.box(0.010, 0.026, 0.50, 'black', at=(s * 0.803, y, 0.36), base=True)
        if o.get('handles'):
            for y in (0.10, 0.86):
                m.box(0.03, 0.13, 0.026, 'chrome', at=(s * 0.818, y, 0.79))

    # -- greenhouse
    if o['glass']:
        bot = [Vector((-HW0, GF0, GZ0)), Vector((HW0, GF0, GZ0)), Vector((HW0, GR0, GZ0)), Vector((-HW0, GR0, GZ0))]
        top = [Vector((-HW1, GF1, GZ1)), Vector((HW1, GF1, GZ1)), Vector((HW1, GR1, GZ1)), Vector((-HW1, GR1, GZ1))]
        hexa(m, bot, top, C)
        za, zb = 0.93, 1.33
        for s in (-1, 1):
            front = [gside(s, yf(za) + 0.09, za), gside(s, 0.20, za), gside(s, 0.20, zb), gside(s, yf(zb) + 0.09, zb)]
            rear = [gside(s, 0.31, za), gside(s, yr(za) - 0.24, za), gside(s, yr(zb) - 0.24, zb), gside(s, 0.31, zb)]
            for wk, q in enumerate((front, rear)):
                col = o['glass'](s, wk)
                plate(m, q, (s, 0, 0), 0.004 if col == 'black' else 0.012, col)
                if col == 'black':          # a shard left in the broken frame
                    a, b = q[0], q[1]
                    plate(m, [a, a.lerp(b, 0.35), a.lerp(q[3], 0.45)], (s, 0, 0), 0.012, 'glass')
        plate(m, [Vector((-(hw(za) - 0.08), yf(za), za)), Vector((hw(za) - 0.08, yf(za), za)),
                  Vector((hw(zb) - 0.08, yf(zb), zb)), Vector((-(hw(zb) - 0.08), yf(zb), zb))], (0, -1, 1), 0.012, 'glass_dark')
        plate(m, [Vector((-(hw(za) - 0.10), yr(za), za)), Vector((hw(za) - 0.10, yr(za), za)),
                  Vector((hw(zb) - 0.10, yr(zb), zb)), Vector((-(hw(zb) - 0.10), yr(zb), zb))], (0, 1, 1), 0.012, 'glass_dark')
    else:
        # burnt shell: open frame of pillars, headers and a sagging roof; sooty floor with scorched seat frames
        P, RF = o['pillar'], o['roof']
        m.box(1.44, GR0 - GF0 - 0.06, 0.008, 'soot', at=(0, (GF0 + GR0) / 2, BELT), base=True)
        for s in (-1, 1):
            m.beam((s * (HW0 - 0.03), GF0 + 0.03, GZ0), (s * (HW1 - 0.03), GF1 + 0.03, GZ1 - 0.01), 0.08, 0.06, P, up=(s, 0, 0.3))
            m.beam(gside(s, 0.255, GZ0) - Vector((s * 0.02, 0, 0)), gside(s, 0.255, GZ1 - 0.01) - Vector((s * 0.02, 0, 0)), 0.08, 0.06, P, up=(s, 0, 0))
            plate(m, [gside(s, yr(GZ0) - 0.26, GZ0), gside(s, yr(GZ0), GZ0), gside(s, yr(GZ1), GZ1), gside(s, yr(GZ1) - 0.20, GZ1)],
                  (s, 0, 0), 0.02, P, inset=0.03)
        m.beam((-HW1, GF1 + 0.03, GZ1 - 0.02), (HW1, GF1 + 0.03, GZ1 - 0.02), 0.08, 0.05, P)
        m.beam((-HW1, GR1 - 0.03, GZ1 - 0.02), (HW1, GR1 - 0.03, GZ1 - 0.02), 0.08, 0.05, P)
        sag = (0, 0.36, GZ1 - 0.07)
        m.beam((0, GF1 - 0.01, GZ1 + 0.005), sag, 2 * HW1 + 0.04, 0.04, RF)
        m.beam(sag, (0, GR1 + 0.01, GZ1 + 0.005), 2 * HW1 + 0.04, 0.04, RF)
        for sx in (-0.36, 0.36):                                     # front seat frames
            m.tube_path([(sx - 0.20, 0.16, BELT), (sx - 0.21, 0.24, 1.20), (sx + 0.21, 0.24, 1.20), (sx + 0.20, 0.16, BELT)], 0.018, 4, 'ash')
            m.tube_path([(sx - 0.20, -0.32, 0.95), (sx + 0.20, -0.32, 0.95), (sx + 0.20, 0.14, 0.97), (sx - 0.20, 0.14, 0.97)],
                        0.016, 4, 'rust', closed=True)
        m.tube_path([(-0.62, 0.92, BELT), (-0.60, 0.98, 1.14), (0.60, 0.98, 1.14), (0.62, 0.92, BELT)], 0.018, 4, 'ash')
        ring = [(-0.36 + 0.17 * math.cos(TAU6 * k), -0.50 + 0.17 * math.sin(TAU6 * k) * 0.42, 1.10 + 0.17 * math.sin(TAU6 * k) * 0.91)
                for k in range(6)]
        m.tube_path(ring, 0.016, 3, 'soot', closed=True)              # steering wheel rim
        m.bar((-0.36, -0.50, 1.10), (-0.36, -0.78, BELT - 0.02), 0.022, 'soot', seg=4)

    # -- bonnet, engine bay, trunk lid
    m.box(1.38, 1.06, 0.006, 'black', at=(0, -1.37, BELT), base=True)
    bon = Mesh()
    if o.get('bonnet_buckle'):
        pk = (0, -1.42, BELT + o['bonnet_buckle'])
        bon.beam((0, -HL + 0.04, BELT + 0.02), pk, 1.46, 0.025, o['bonnet_col'])
        bon.beam(pk, (0, GF0 - 0.05, BELT + 0.016), 1.46, 0.025, o['bonnet_col'])
    else:
        plate(bon, [(-0.73, -HL + 0.04, BELT), (0.73, -HL + 0.04, BELT), (0.73, GF0 - 0.05, BELT), (-0.73, GF0 - 0.05, BELT)],
              (0, 0, 1), 0.022, o['bonnet_col'])
    if o.get('dent_bonnet'):
        if o.get('bonnet_buckle'):
            sk.jitter(bon, o['dent_bonnet'], 23)
        else:
            dent(bon, o['dent_bonnet'], 23)
    hinged(m, bon, (0, GF0 - 0.05, BELT), 'X', o.get('bonnet_open', 0.0))
    trunk = Mesh()
    plate(trunk, [(-0.72, GR0 + 0.05, BELT), (0.72, GR0 + 0.05, BELT), (0.72, HL - 0.04, BELT), (-0.72, HL - 0.04, BELT)],
          (0, 0, 1), 0.022, o['trunk_col'])
    if o.get('dent_trunk'):
        dent(trunk, o['dent_trunk'], 29)
    hinged(m, trunk, (0, GR0 + 0.05, BELT), 'X', o.get('trunk_open', 0.0))

    # -- nose: dark grille with four round headlights, indicators
    m.box(1.42, 0.04, 0.22, 'black', at=(0, -HL - 0.01, 0.715))
    for k, x in enumerate((-0.58, -0.39, 0.39, 0.58)):
        lens, push, tilt = o['lens'](k)
        if lens:
            m.cyl(0.08, 0.03 - push, 8, lens, M=T(x, -HL - 0.025, 0.715) @ R(tilt, 'Y') @ R(90, 'X'))
    for s in (-1, 1):
        m.box(0.20, 0.03, 0.06, o['indicator'], at=(s * 0.52, -HL - 0.01, 0.545))
        m.box(0.34, 0.04, 0.16, o['tail'], at=(s * 0.55, HL + 0.005, 0.72))
        m.box(0.12, 0.03, 0.06, o['indicator'], at=(s * 0.27, HL + 0.005, 0.72))

    # -- bumpers (front with overriders)
    fb = Mesh()
    fb.bevel_box(1.72, 0.10, 0.11, 0.03, o['bumper'], at=(0, 0, 0))
    for x in (-0.32, 0.32):
        fb.box(0.06, 0.07, 0.17, o['bumper'], at=(x, -0.02, 0.02))
    fdrop = o.get('front_bumper_drop', 0.0)
    m.merge(fb, T(0.86, -HL - 0.05, 0.44) @ R(fdrop, 'Y') @ T(-0.86, 0, 0))
    rb = Mesh()
    rb.bevel_box(1.72, 0.10, 0.11, 0.03, o['bumper'], at=(0, 0, 0))
    m.merge(rb, T(0.86, HL + 0.05, 0.46) @ R(o.get('rear_bumper_drop', 0.0), 'Y') @ T(-0.86, 0, 0))

    # -- mirror (right side only), antenna
    if o.get('mirror'):
        m.box(0.03, 0.03, 0.08, 'chrome', at=(0.82, GF0 + 0.12, BELT), base=True)
        m.bevel_box(0.12, 0.04, 0.08, 0.012, 'chrome', at=(0.86, GF0 + 0.12, BELT + 0.10))
    if o.get('antenna'):
        m.tube_path([(-0.70, -1.55, BELT), (-0.70, -1.60, 1.20), (-0.66, -1.48, 1.42)], 0.008, 3, 'chrome')

    for fn in o.get('extra', ()):                                    # variant decals (rust, soot, ash) in car space
        fn(m)
    return m


TAU6 = math.tau / 6


def tyre(r, w, seg, col, sag=0.0, hub_col=None, hub_r=0.15):
    """Wheel centred on the origin, axis X. sag > 0 squashes the bottom (flat tyre) and bulges it sideways."""
    t = Mesh()
    t.cyl(r, w, seg, col, M=T(-w / 2, 0, 0) @ R(90, 'Y'))
    if sag:
        floor = -(r * math.cos(math.pi / seg) - sag)
        t.verts = [(x * (1.25 if z < floor + 1e-6 else 1.0), y, max(z, floor)) for x, y, z in t.verts]
    if hub_col:
        t.cyl(hub_r, w + 0.03, 6, hub_col, M=T(-(w + 0.03) / 2, 0, 0) @ R(90, 'Y'))
    return t


def place(m, body, M, wheels, bricks=None):
    """Merge the posed body and stand the wheels (list of (car-space hub point, Mesh, ground hub height)) on the ground."""
    m.merge(body, M)
    for p, w, hz in wheels:
        q = M @ Vector(p)
        m.merge(w, T(q.x, q.y, hz))
    if bricks:
        bricks(m, M)
    mz = min(v[2] for v in m.verts)
    m.verts = [(x, y, z - mz) for x, y, z in m.verts]
    return m


# ---------------------------------------------------------------- variants
def wrecked():
    C = 'car_blue'

    def rust(m):
        for s in (-1, 1):                                            # rotten sills
            side_plate(m, s, 0.79, [(-0.80, 0.29), (0.70, 0.29), (0.66, 0.40), (0.20, 0.43), (-0.40, 0.41), (-0.78, 0.37)],
                       0.035, 'rust')
        side_plate(m, -1, 0.80, [(-1.62, 0.56), (-1.46, 0.72), (-1.20, 0.78), (-0.96, 0.70), (-0.86, 0.58)], 0.025, 'rust')
        side_plate(m, 1, 0.80, [(1.52, 0.56), (1.40, 0.74), (1.16, 0.80), (0.92, 0.72), (0.80, 0.60)], 0.025, 'rust')
        side_plate(m, -1, 0.80, [(0.30, 0.40), (0.62, 0.40), (0.58, 0.52), (0.36, 0.55)], 0.03, 'rust')
        side_plate(m, -1, 0.80, [(-1.94, 0.62), (-1.70, 0.62), (-1.66, 0.74), (-1.90, 0.80)], 0.025, 'rust')
        plate(m, [(0.30, 1.70, BELT), (0.66, 1.62, BELT), (0.70, 1.90, BELT), (0.40, 1.91, BELT)], (0, 0, 1), 0.032, 'rust')
        plate(m, [(-0.30, 0.10, GZ1), (0.05, 0.02, GZ1), (0.12, 0.36, GZ1), (-0.22, 0.42, GZ1)], (0, 0, 1), 0.01, 'rust')

    o = dict(paint=C, lower=C, door_col=lambda s, k: C,
             lips=lambda s, a: 'rust' if (s, a) in ((-1, 0), (-1, 1), (1, 1)) else C,
             dent_lower=0.010, dent_doors=0.016, dent_bonnet=0.012, dent_trunk=0.008,
             handles=True, glass=lambda s, k: 'black' if (s, k) == (-1, 1) else 'glass_dark',
             bonnet_col=C, bonnet_open=-3.0, trunk_col=C,
             lens=lambda k: ('glass_dark', 0.012, 9) if k == 0 else ('white', 0, 0),
             indicator='orange', tail='red', bumper='chrome', rear_bumper_drop=-5.0,
             mirror=True, antenna=True, extra=(rust,))
    body = sedan(o)
    # the rear-left corner sits on bricks, the rest on flat tyres: drop, roll to the left, nose up a touch
    M = T(0, 0, -0.04) @ R(-0.8, 'X') @ R(-1.8, 'Y')
    seg = 10
    wheels = []
    for (s, ai), hz in (((-1, 0), 0.215), ((1, 0), 0.25), ((1, 1), 0.24)):
        r = 0.30
        sag = r * math.cos(math.pi / seg) - hz
        wheels.append(((s * WX, AXLES[ai], HUB), tyre(r, 0.18, seg, 'rubber', sag, 'chrome'), hz))
    # bare brake drum in the empty rear-left opening
    drum = Mesh()
    drum.cyl(0.10, 0.10, 6, 'metal_dark', M=T(-0.05, 0, 0) @ R(90, 'Y'))

    def bricks(m, M):
        d = M @ Vector((-0.66, AXLES[1], HUB))               # bare drum, propped on a crosswise stack of bricks
        m.merge(drum, T(d.x, d.y, d.z))
        top = d.z - 0.10 * math.cos(math.pi / 6)
        n = max(2, round(top / 0.065))
        h = top / n
        for i in range(n):
            m.box(0.25 if i % 2 == 0 else 0.12, 0.12 if i % 2 == 0 else 0.25, h - 0.002, 'brick',
                  M=T(d.x + 0.02, d.y, i * h) @ R((-1) ** i * 6 + 3, 'Z'), base=True)
        m.box(0.22, 0.11, 0.065, 'brick', M=T(-0.95, 1.95, 0) @ R(28, 'Z'), base=True)  # a loose brick on the ground

    return place(Mesh(), body, M, wheels, bricks)


def burnt():
    def soot(m):
        plate(m, [(-0.70, -1.90, BELT), (-0.20, -1.92, BELT), (-0.10, -1.65, BELT), (-0.60, -1.55, BELT)], (0, 0, 1), 0.01, 'soot')

    o = dict(paint='rust', lower='soot', door_col=lambda s, k: 'ash' if (s, k) in ((1, 0), (-1, 1)) else 'rust',
             lips=lambda s, a: 'rust', dent_lower=0.014, dent_doors=0.026, dent_trunk=0.02,
             door_ajar=(-1, 0, 9.0), handles=False, glass=None, pillar='soot', roof='ash',
             bonnet_col='ash', bonnet_buckle=0.09, trunk_col='rust', trunk_open=6.0,
             lens=lambda k: ('soot', 0.015, 0), indicator='soot', tail='soot', bumper='rust',
             front_bumper_drop=-9.0, extra=(soot,))
    body = sedan(o)
    seg = 8
    r = 0.19
    hz = r * math.cos(math.pi / seg)
    M = T(0, 0, -(HUB - hz) - 0.02) @ R(-1.6, 'X') @ R(1.5, 'Y')
    wheels = [((s * WX, ay, HUB), tyre(r, 0.13, seg, 'rust', 0, 'soot', 0.08), hz) for ay in AXLES for s in (-1, 1)]

    def debris(m, M):                                                # ash heap under the open driver door
        m.prism_xy([(-1.05, -0.55), (-0.90, -0.75), (-0.80, -0.30), (-0.95, -0.10), (-1.10, -0.25)], 0, 0.03, 'ash')

    return place(Mesh(), body, M, wheels, debris)


for name, fn, notes in (
        ('SK_Car_Wrecked', wrecked, 'Abandoned 1970s sedan: faded blue paint, rotten sills and arches, dented panels, flat tyres, '
                                    'rear-left wheel missing (corner on bricks, bare drum), broken rear-left window, cracked headlight, '
                                    'bonnet ajar, sagging rear bumper, slight roll to the left. Faces -Y.'),
        ('SK_Car_Burnt', burnt, 'Burnt-out shell of the same sedan: rust/soot/ash only, no glass and no tyres (sits low on bare rims), '
                                'open pillar frame with sagged roof, scorched seat frames and steering wheel inside, warped doors '
                                '(front-left ajar), buckled bonnet, popped trunk lid, front bumper hanging. Faces -Y.')):
    if fam.wants(name):
        fam.asset(name, [(name + '_Mesh', fn(), None, None)], notes=notes)

fam.finish()
