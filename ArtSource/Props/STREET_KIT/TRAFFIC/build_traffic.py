"""STREET_KIT / TRAFFIC - parking boom barrier, Russian (GOST) road signs on pipe posts, manhole cover, fire hydrant.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/TRAFFIC/build_traffic.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/TRAFFIC/build_traffic.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import streetkit as sk
from streetkit import Mesh, T, R

fam = sk.Family('SK-TRAFFIC', __file__)

# ---------------------------------------------------------------- road sign helpers
POST_R = 0.038            # steel pipe post radius
POST_H = 2.50             # post height
PLATE_Z = 2.20            # plate centre height
PLATE_BACK = -0.050       # y of the back face of the grey back plate (post surface is at -0.038)
PLATE_T = 0.025           # grey back plate thickness
LAYER = 0.005             # each colour layer sits this much further toward -Y than the previous one


def rpoly(n, R_, rot=90.0, cut=0.0, dx=0.0, dz=0.0):
    """Regular n-gon (circumradius R_, first corner at angle `rot` deg) in the XZ plane, corners cut back by `cut`."""
    c = [(R_ * math.cos(math.radians(rot) + math.tau * k / n), R_ * math.sin(math.radians(rot) + math.tau * k / n)) for k in range(n)]
    if cut <= 0:
        return [(x + dx, z + dz) for x, z in c]
    out = []
    for k in range(n):
        p, a, b = c[k], c[k - 1], c[(k + 1) % n]
        for q in (a, b):
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            out.append((p[0] + (q[0] - p[0]) * cut / L + dx, p[1] + (q[1] - p[1]) * cut / L + dz))
    return out


def tri_R(inradius):
    return inradius * 2.0


def disc(r, seg=24, dx=0.0, dz=0.0):
    return [(dx + r * math.cos(math.tau * k / seg), dz + r * math.sin(math.tau * k / seg)) for k in range(seg)]


class Plate:
    """Sign plate: grey back plate, then colour layers stacked toward -Y (layer k front face at back plate front - k*LAYER)."""

    def __init__(self, m, back_poly):
        self.m = m
        y0 = PLATE_BACK - PLATE_T
        self.front = y0
        self.n = 0
        m.prism(back_poly, PLATE_T, 'metal', T(0, y0 + PLATE_T / 2, PLATE_Z))

    def layer(self, k, poly, col):
        """Convex polygon (XZ, relative to the plate centre) on layer k >= 1; embedded 3 mm into the layer behind."""
        self.n += 1
        y1 = self.front - k * LAYER - 0.0004 * (self.n % 4)          # shapes sharing a layer never share a front plane
        y0 = self.front - (k - 1) * LAYER + 0.003
        self.m.prism(poly, y0 - y1, col, T(0, (y0 + y1) / 2, PLATE_Z))

    def rect(self, k, x0, z0, x1, z1, col):
        self.layer(k, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], col)

    def stroke(self, k, p0, p1, w, col):
        """Flat bar of width w from p0 to p1 (XZ, relative to the plate centre)."""
        dx, dz = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dz)
        nx, nz = -dz / L * w / 2, dx / L * w / 2
        self.layer(k, [(p0[0] + nx, p0[1] + nz), (p0[0] - nx, p0[1] - nz), (p1[0] - nx, p1[1] - nz), (p1[0] + nx, p1[1] + nz)], col)


def sign_post(m, plate_half_h, h=POST_H):
    """Grey steel pipe with a cap, two clamps to the plate and a small concrete collar on the ground."""
    m.cyl(POST_R, h, 8, 'metal')
    m.cyl(POST_R + 0.006, 0.03, 8, 'metal_dark', r_top=POST_R - 0.01, at=(0, 0, h))                      # cap
    m.cyl(0.11, 0.05, 8, 'concrete', r_top=0.085)                                                        # collar
    for dz in (-plate_half_h * 0.6, plate_half_h * 0.6):
        m.box(0.07, 0.05, 0.045, 'metal_dark', at=(0, -0.026, PLATE_Z + dz))                             # clamp
        m.box(0.09, 0.018, 0.06, 'metal_dark', at=(0, PLATE_BACK + 0.009 + 0.001, PLATE_Z + dz))         # bracket strap


# blocky letters on a 3 x 5 cell grid: rectangles (x0, z0, x1, z1) in cells
FONT = {
    'S': [(0, 4, 3, 5), (0, 3, 1, 4), (0, 2, 3, 3), (2, 0, 3, 2), (0, 0, 2, 1)],
    'T': [(0, 4, 3, 5), (1, 0, 2, 4)],
    'O': [(0, 0, 1, 5), (2, 0, 3, 5), (1, 4, 2, 5), (1, 0, 2, 1)],
    'P': [(0, 0, 1, 5), (1, 4, 3, 5), (2, 2, 3, 4), (1, 2, 2, 3)],
}


def text(p, k, s, cw, ch, gap, col, zc=0.0):
    w = len(s) * 3 * cw + (len(s) - 1) * gap
    x = -w / 2
    for c in s:
        for x0, z0, x1, z1 in FONT[c]:
            p.rect(k, x + x0 * cw, zc - 2.5 * ch + z0 * ch, x + x1 * cw, zc - 2.5 * ch + z1 * ch, col)
        x += 3 * cw + gap


def sign_stop():
    m = Mesh()
    F = 0.76                                                     # flat-to-flat of the white octagon
    Rf = lambda f: f / 2 / math.cos(math.pi / 8)
    p = Plate(m, rpoly(8, Rf(F + 0.02), 22.5))
    sign_post(m, F / 2)
    p.layer(1, rpoly(8, Rf(F), 22.5), 'white')
    p.layer(2, rpoly(8, Rf(F - 0.07), 22.5), 'sign_red')
    text(p, 3, 'STOP', 0.042, 0.042, 0.03, 'white')
    return m


def sign_give_way():
    m = Mesh()
    side = 0.90
    Rt = side / math.sqrt(3)
    dz = Rt / 4                                                  # centre the bounding box (not the centroid) on the plate
    p = Plate(m, rpoly(3, Rt + 0.025, -90, 0.04, dz=dz))
    sign_post(m, Rt * 0.75)
    p.layer(1, rpoly(3, Rt, -90, 0.035, dz=dz), 'sign_red')
    p.layer(2, rpoly(3, Rt - tri_R(0.075), -90, 0.02, dz=dz), 'white')
    return m


def sign_no_entry():
    m = Mesh()
    r = 0.36
    p = Plate(m, disc(r + 0.012))
    sign_post(m, r)
    p.layer(1, disc(r), 'white')
    p.layer(2, disc(r - 0.02), 'sign_red')
    p.rect(3, -0.24, -0.055, 0.24, 0.055, 'white')
    return m


def warning_triangle(m, side=0.90):
    Rt = side / math.sqrt(3)
    dz = -Rt / 4
    p = Plate(m, rpoly(3, Rt + 0.025, 90, 0.04, dz=dz))
    sign_post(m, Rt * 0.75, h=2.40)                              # lower top: the apex is too narrow to hide the cap
    p.layer(1, rpoly(3, Rt, 90, 0.035, dz=dz), 'sign_red')
    p.layer(2, rpoly(3, Rt - tri_R(0.075), 90, 0.02, dz=dz), 'white')
    return p


def sign_speed_bump():
    m = Mesh()
    p = warning_triangle(m)
    zb = -0.12                                                   # road line
    p.rect(3, -0.20, zb - 0.035, 0.20, zb, 'black')
    hump = [(0.10 * math.cos(math.pi * k / 10), zb - 0.01 + 0.085 * math.sin(math.pi * k / 10)) for k in range(11)]
    p.layer(3, hump, 'black')
    return m


def sign_ped_crossing():
    m = Mesh()
    s = 0.70
    sq = lambda a, c: rpoly(4, a / math.sqrt(2), 45, c)
    p = Plate(m, sq(s + 0.02, 0.03))
    sign_post(m, s / 2)
    p.layer(1, sq(s, 0.03), 'white')
    p.layer(2, sq(s - 0.04, 0.02), 'sign_blue')
    side = 0.60
    Rt = side / math.sqrt(3)
    dz = -Rt / 4
    p.layer(3, rpoly(3, Rt, 90, 0.02, dz=dz), 'white')
    # zebra at the feet: five slanted bars
    for i in range(5):
        x = -0.15 + i * 0.075
        p.layer(4, [(x - 0.02, -0.225), (x + 0.02, -0.225), (x + 0.035, -0.17), (x - 0.005, -0.17)], 'black')
    # walking figure (to the right)
    k = 4
    hip, sh = (-0.005, -0.04), (0.012, 0.075)
    p.stroke(k, hip, sh, 0.05, 'black')                                     # torso
    p.layer(k, disc(0.032, 10, 0.025, 0.125), 'black')                      # head
    p.stroke(k, (hip[0], hip[1] + 0.01), (0.075, -0.155), 0.034, 'black')   # front leg
    p.stroke(k, (hip[0], hip[1] + 0.01), (-0.07, -0.155), 0.034, 'black')   # back leg
    p.stroke(k, (0.09, -0.152), (0.065, -0.158), 0.03, 'black')             # front foot
    p.stroke(k, (sh[0], sh[1] - 0.005), (0.07, 0.0), 0.026, 'black')        # front arm
    p.stroke(k, (sh[0], sh[1] - 0.005), (-0.06, 0.01), 0.026, 'black')      # back arm
    return m


# ---------------------------------------------------------------- parking barrier
HINGE = (0.0, -0.235, 0.86)      # boom axle (axis along Y)
BOOM_LEN = 4.0
BOOM_H, BOOM_D = 0.10, 0.065


def barrier_body():
    m = Mesh()
    m.bevel_box(0.46, 0.46, 0.06, 0.015, 'concrete', base=True)                          # plinth
    m.bevel_box(0.35, 0.35, 0.90, 0.025, 'white', at=(0, 0, 0.05), base=True)             # cabinet
    m.bevel_box(0.40, 0.40, 0.07, 0.02, 'metal_dark', at=(0, 0, 0.94), base=True)         # lid
    m.box(0.37, 0.37, 0.07, 'sign_red', at=(0, 0, 0.62), base=True)                       # red band
    m.box(0.18, 0.02, 0.36, 'metal', at=(0, 0.177, 0.14), base=True)                      # service door (+Y)
    m.box(0.03, 0.02, 0.06, 'black', at=(0.06, 0.19, 0.30), base=True)                    # lock
    m.cyl(0.05, 0.07, 8, 'orange', at=(0, 0, 1.01), r_top=0.035)                          # signal lamp
    m.cyl(0.055, 0.015, 8, 'metal_dark', at=(0, 0, 1.01))
    # fork support at the far end (the boom tip rests in it)
    x, y = BOOM_LEN - 0.20, HINGE[1]
    z_rest = HINGE[2] - BOOM_H / 2
    m.bevel_box(0.24, 0.24, 0.03, 0.01, 'metal_dark', at=(x, y, 0), base=True)
    m.cyl(0.04, z_rest - 0.05, 8, 'metal', at=(x, y, 0.03))
    m.box(0.07, 0.17, 0.035, 'metal_dark', at=(x, y, z_rest - 0.035), base=True)          # fork base / rubber pad
    m.box(0.065, 0.075, 0.03, 'rubber', at=(x, y, z_rest - 0.012), base=True)
    for s in (-1, 1):
        m.box(0.06, 0.022, 0.13, 'yellow', at=(x, y + s * (BOOM_D / 2 + 0.024), z_rest - 0.01), base=True)  # prongs
    return m


def barrier_boom():
    m = Mesh()
    hx, hy, hz = HINGE
    # axle hub coming out of the cabinet front, counterweight tail behind the hinge
    m.bar((hx, -0.175, hz), (hx, hy - BOOM_D / 2 - 0.02, hz), 0.075, 'metal_dark', seg=10)
    m.bevel_box(0.40, BOOM_D + 0.03, 0.15, 0.02, 'metal_dark', at=(hx - 0.30, hy, hz))
    seg = 8
    L = BOOM_LEN / seg
    for i in range(seg):
        col = 'sign_red' if i % 2 else 'white'
        m.box(L, BOOM_D, BOOM_H, col, at=(hx + 0.05 + L * (i + 0.5), hy, hz))
    m.box(0.03, BOOM_D + 0.01, BOOM_H + 0.01, 'rubber', at=(hx + 0.05 + BOOM_LEN + 0.015, hy, hz))   # tip cap
    return m


# ---------------------------------------------------------------- manhole cover
def ring(m, r0, r1, z0, z1, seg, col, offset=0.0):
    """Closed annulus (flat ring) from radius r0 to r1."""
    v, f = [], []
    for r, z in ((r0, z0), (r1, z0), (r1, z1), (r0, z1)):
        v += [(r * math.cos(offset + math.tau * k / seg), r * math.sin(offset + math.tau * k / seg), z) for k in range(seg)]
    for a in range(4):
        b = (a + 1) % 4
        for k in range(seg):
            k1 = (k + 1) % seg
            f.append((a * seg + k, a * seg + k1, b * seg + k1, b * seg + k))
    return m.shell(v, f, col)


def manhole():
    m = Mesh()
    seg = 24
    # frame + cover as one lathe: bevelled outer frame, slightly sunk cover plate
    m.lathe([(0.40, 0.0), (0.40, 0.006), (0.385, 0.018), (0.345, 0.018), (0.335, 0.012), (0.0, 0.012)], seg, 'metal_dark',
            cols=['metal_dark', 'metal_dark', 'metal', 'metal_dark', 'metal_dark', 'metal_dark'])
    ring(m, 0.20, 0.235, 0.008, 0.019, seg, 'metal', math.pi / seg)                       # concentric relief ring
    m.cyl(0.06, 0.011, 8, 'metal', at=(0, 0, 0.008))                                      # centre boss
    for k in range(8):                                                                    # ribs
        a = math.tau * k / 8 + math.pi / 8
        c, s = math.cos(a), math.sin(a)
        m.beam((0.05 * c, 0.05 * s, 0.0135), (0.205 * c, 0.205 * s, 0.0135), 0.022, 0.011, 'metal')
        b = a + math.pi / 8
        cb, sb = math.cos(b), math.sin(b)
        m.beam((0.23 * cb, 0.23 * sb, 0.0135), (0.33 * cb, 0.33 * sb, 0.0135), 0.022, 0.011, 'metal')
    for a in (0.0, math.pi):                                                              # lifting slots
        m.box(0.05, 0.016, 0.004, 'black', at=(0.29 * math.cos(a), 0.0, 0.0115))
    return m


# ---------------------------------------------------------------- fire hydrant
def hydrant():
    m = Mesh()
    seg = 12
    m.lathe([(0.17, 0.0), (0.17, 0.05), (0.125, 0.07), (0.125, 0.56), (0.15, 0.58), (0.15, 0.64), (0.0, 0.64)], seg, 'red')
    m.lathe([(0.155, 0.635), (0.155, 0.67), (0.13, 0.74), (0.07, 0.79), (0.0, 0.80)], seg, 'brick')          # dome cap
    m.cyl(0.04, 0.06, 5, 'metal_dark', at=(0, 0, 0.785))                                                     # operating nut
    for a in range(0, 360, 60):                                                                             # bonnet bolts
        x, y = 0.145 * math.cos(math.radians(a + 15)), 0.145 * math.sin(math.radians(a + 15))
        m.box(0.03, 0.03, 0.025, 'metal_dark', at=(x, y, 0.64), base=True)
    for a in range(0, 360, 90):                                                                             # base bolts
        x, y = 0.15 * math.cos(math.radians(a + 45)), 0.15 * math.sin(math.radians(a + 45))
        m.box(0.035, 0.035, 0.03, 'metal_dark', at=(x, y, 0.05), base=True)
    m.lathe([(0.135, 0.20), (0.135, 0.26), (0.0, 0.26)], seg, 'brick')                                      # lower band
    # side hose outlets (+-X) and the big pumper outlet (-Y front)
    for s in (-1, 1):
        m.bar((s * 0.10, 0, 0.44), (s * 0.20, 0, 0.44), 0.055, 'red', seg=8)
        m.bar((s * 0.20, 0, 0.44), (s * 0.245, 0, 0.44), 0.065, 'brick', seg=8)
        m.bar((s * 0.24, 0, 0.44), (s * 0.27, 0, 0.44), 0.025, 'metal_dark', seg=5)
    m.bar((0, -0.10, 0.36), (0, -0.20, 0.36), 0.075, 'red', seg=10)
    m.bar((0, -0.20, 0.36), (0, -0.25, 0.36), 0.088, 'brick', seg=10)
    m.bar((0, -0.245, 0.36), (0, -0.28, 0.36), 0.032, 'metal_dark', seg=5)
    return m


# ---------------------------------------------------------------- assets
SIGN_NOTE = ('Russian road sign {code} on a 2.5 m grey steel pipe (r 0.038) with a concrete collar; plate centre at 2.2 m, '
             'front faces -Y, plate front ~0.08 m in front of the post axis. Sign art is layered geometry (5 mm steps), no textures.')

if fam.wants('SK_ParkingBarrier'):
    fam.asset('SK_ParkingBarrier', [('SK_ParkingBarrier_Mesh', barrier_body(), None, None),
                                    ('SK_ParkingBarrier_Boom', barrier_boom(), HINGE, None)],
              notes='Boom barrier: white cabinet 0.35 x 0.35 x 1.0 m with lid and signal lamp, red/white 4 m boom along +X on the '
                    'cabinet front (-Y), fork rest at x = 3.8 m. Boom is a child with its pivot on the axle (0, -0.235, 0.86); '
                    'axle axis = Blender Y, rotating -90 deg about Blender Y raises the boom.')

for name, fn, code in (('SK_Sign_Stop', sign_stop, '2.5 STOP (octagon)'),
                       ('SK_Sign_GiveWay', sign_give_way, '2.4 Give way'),
                       ('SK_Sign_NoEntry', sign_no_entry, '3.1 No entry'),
                       ('SK_Sign_SpeedBump', sign_speed_bump, '1.17 Speed bump'),
                       ('SK_Sign_PedestrianCrossing', sign_ped_crossing, '5.19.1 Pedestrian crossing')):
    if fam.wants(name):
        fam.asset(name, [(name + '_Mesh', fn(), None, None)], notes=SIGN_NOTE.format(code=code))

if fam.wants('SK_ManholeCover'):
    fam.asset('SK_ManholeCover', [('SK_ManholeCover_Mesh', manhole(), None, None)],
              notes='Cast-iron manhole cover d 0.8 m (frame) / 0.67 m (lid), 2 cm high: relief ring, centre boss, 16 ribs, lifting slots. '
                    'Sits on the ground (base at z = 0); can be sunk 1-2 cm into the road in Unity.')

if fam.wants('SK_FireHydrant'):
    fam.asset('SK_FireHydrant', [('SK_FireHydrant_Mesh', hydrant(), None, None)],
              notes='Above-ground column hydrant 0.84 m: red barrel, dark dome cap and operating nut, two side outlets (+-X) and a '
                    'pumper outlet to the front (-Y), all capped.')

fam.finish()
