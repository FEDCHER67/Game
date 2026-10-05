"""VEHICLES_KIT / CARS - parked Soviet boxy sedan (4 paint colours), a wedge 3-door hatchback and a police sedan.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/VEHICLES_KIT/CARS/build_cars.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/VEHICLES_KIT/CARS/build_cars.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import vehiclekit as vk
from vehiclekit import sk, Mesh, T, R, plate, side_plate, end_plate, rect_yz, rect_xz, hexa
from mathutils import Vector

fam = sk.Family('VK-CARS', __file__)


def lerp(a, b, t):
    return a + (b - a) * t


class Greenhouse:
    """Tapered cabin between z0 and z1: windscreen base/top y (f0, f1), rear window base/top y (r0, r1), half widths."""

    def __init__(self, z0, z1, f0, f1, r0, r1, hw0, hw1):
        self.z0, self.z1, self.f0, self.f1, self.r0, self.r1, self.hw0, self.hw1 = z0, z1, f0, f1, r0, r1, hw0, hw1

    def t(self, z):
        return (z - self.z0) / (self.z1 - self.z0)

    def yf(self, z):
        return lerp(self.f0, self.f1, self.t(z))

    def yr(self, z):
        return lerp(self.r0, self.r1, self.t(z))

    def hw(self, z):
        return lerp(self.hw0, self.hw1, self.t(z))

    def side(self, s, y, z):
        return Vector((s * self.hw(z), y, z))

    def build(self, m, col):
        g = self
        bot = [Vector((-g.hw0, g.f0, g.z0)), Vector((g.hw0, g.f0, g.z0)), Vector((g.hw0, g.r0, g.z0)), Vector((-g.hw0, g.r0, g.z0))]
        top = [Vector((-g.hw1, g.f1, g.z1)), Vector((g.hw1, g.f1, g.z1)), Vector((g.hw1, g.r1, g.z1)), Vector((-g.hw1, g.r1, g.z1))]
        hexa(m, bot, top, col)

    def side_window(self, m, s, ya, yb, za, zb, col='glass_dark', front_slant=False, rear_slant=False):
        """Window on the tapered side; ya/yb are offsets from the pillars when the matching *_slant flag is set."""
        y0a = self.yf(za) + ya if front_slant else ya
        y0b = self.yf(zb) + ya if front_slant else ya
        y1a = self.yr(za) - yb if rear_slant else yb
        y1b = self.yr(zb) - yb if rear_slant else yb
        q = [self.side(s, y0a, za), self.side(s, y1a, za), self.side(s, y1b, zb), self.side(s, y0b, zb)]
        plate(m, q, (s, 0, 0), 0.010, col)

    def screens(self, m, za, zb, inset, col='glass_dark', rear=True):
        g = self
        plate(m, [Vector((-(g.hw(za) - inset), g.yf(za), za)), Vector((g.hw(za) - inset, g.yf(za), za)),
                  Vector((g.hw(zb) - inset, g.yf(zb), zb)), Vector((-(g.hw(zb) - inset), g.yf(zb), zb))],
              (0, -(g.z1 - g.z0), g.f1 - g.f0), 0.010, col)
        if rear:
            plate(m, [Vector((-(g.hw(za) - inset), g.yr(za), za)), Vector((g.hw(za) - inset, g.yr(za), za)),
                      Vector((g.hw(zb) - inset, g.yr(zb), zb)), Vector((-(g.hw(zb) - inset), g.yr(zb), zb))],
                  (0, g.z1 - g.z0, g.r0 - g.r1), 0.010, col)


# ---------------------------------------------------------------- boxy 1970s sedan ("classic" proportions, no logos)
S_HL, S_HW = 1.93, 0.80                 # half length / half width of the body tub (bumpers add ~0.12 at each end)
S_AX = (-1.21, 1.21)                    # front / rear axle y
S_R, S_TW = 0.30, 0.71                  # tyre radius, wheel centre x
S_BELT = 0.88


def sedan(paint, police=False):
    m = Mesh()
    hz = vk.wheels(m, (-S_TW, S_TW), S_AX, S_R, 0.17, 10, rim='chrome', rim_r=0.15)
    vk.tub_with_arches(m, S_HW, -S_HL, S_HL, 0.26, 0.56, S_BELT, S_AX, 0.39, hz, paint, bev=0.05, upper_bev=0.06,
                       lips=None if police else paint)
    g = Greenhouse(S_BELT, 1.42, -0.80, -0.26, 1.16, 0.90, 0.74, 0.62)
    g.build(m, paint)
    za, zb = 0.93, 1.37
    for s in (-1, 1):
        g.side_window(m, s, 0.09, 0.19, za, zb, front_slant=True)
        g.side_window(m, s, 0.29, 0.23, za, zb, rear_slant=True)
    g.screens(m, za, zb, 0.08)

    # doors: dark seams, chrome handles
    for s in (-1, 1):
        for y in (-0.77, 0.24, 0.98):
            m.box(0.010, 0.022, 0.50, 'black', at=(s * (S_HW + 0.003), y, 0.36), base=True)
        for y in (0.10, 0.86):
            m.box(0.03, 0.13, 0.026, 'chrome', at=(s * (S_HW + 0.012), y, 0.79))
    if police:                                                   # blue band along the flanks and across the bonnet
        for s in (-1, 1):
            side_plate(m, s, S_HW, rect_yz(-S_HL + 0.06, S_HL - 0.06, 0.64, 0.74), 'sign_blue', t=0.006)
        plate(m, [(-0.14, -S_HL + 0.06, S_BELT), (0.14, -S_HL + 0.06, S_BELT), (0.14, -0.86, S_BELT), (-0.14, -0.86, S_BELT)],
              (0, 0, 1), 0.006, 'sign_blue')
        vk.light_bar(m, 0.30, 1.42, 1.10, ['sign_red', 'white', 'sign_blue'])

    # nose: dark grille, four round headlights, indicators; tail: lamp clusters, plates
    m.box(1.42, 0.04, 0.20, 'black', at=(0, -S_HL - 0.01, 0.71))
    for x in (-0.58, -0.39, 0.39, 0.58):
        vk.lamp(m, x, -S_HL - 0.02, 0.71, 0.075, 'white', depth=0.03)
    for s in (-1, 1):
        m.box(0.20, 0.03, 0.06, 'orange', at=(s * 0.52, -S_HL - 0.01, 0.545))
        m.box(0.30, 0.04, 0.16, 'red', at=(s * 0.56, S_HL + 0.005, 0.72))
        m.box(0.10, 0.03, 0.16, 'orange', at=(s * 0.36, S_HL + 0.005, 0.72))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, -S_HL - 0.11, 0.44))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, S_HL + 0.012, 0.60))

    # chrome bumpers with overriders
    for s in (-1, 1):
        m.bevel_box(1.72, 0.10, 0.10, 0.03, 'chrome', at=(0, s * (S_HL + 0.04), 0.44))
        for x in (-0.32, 0.32):
            m.box(0.06, 0.07, 0.16, 'chrome', at=(x, s * (S_HL + 0.06), 0.46))

    # driver-side mirror, wipers
    m.box(0.03, 0.03, 0.08, 'chrome', at=(S_HW - 0.06, -0.70, S_BELT), base=True)
    m.bevel_box(0.12, 0.04, 0.08, 0.012, 'chrome', at=(S_HW - 0.02, -0.70, S_BELT + 0.10))
    for x in (-0.30, 0.22):
        m.beam((x, g.yf(0.95) - 0.02, 0.95), (x + 0.40, g.yf(0.95) - 0.02, 0.96), 0.02, 0.02, 'black')
    return m


# ---------------------------------------------------------------- 1980s wedge 3-door hatchback
H_HL, H_HW = 2.00, 0.81
H_AX = (-1.30, 1.16)


def hatchback(paint):
    m = Mesh()
    hz = vk.wheels(m, (-0.72, 0.72), H_AX, 0.29, 0.17, 10, rim='metal', rim_r=0.14)
    # wedge upper body: low nose rising to a high tail, lower blocks between the wheel openings
    vk.side_prism(m, [(-H_HL, 0.54), (H_HL, 0.54), (H_HL, 0.86), (-0.66, 0.88), (-H_HL + 0.06, 0.74), (-H_HL, 0.66)],
                  2 * H_HW, paint)
    cuts = (-H_HL, H_AX[0] - 0.38, H_AX[0] + 0.38, H_AX[1] - 0.38, H_AX[1] + 0.38, H_HL)
    for a, b in zip(cuts[::2], cuts[1::2]):
        m.bevel_box(2 * H_HW - 0.02, b - a, 0.32, 0.04, paint, at=(0, (a + b) / 2, 0.24), base=True)
    m.box(2 * H_HW - 0.24, 2 * H_HL - 0.2, 0.30, 'black', at=(0, 0, 0.24), base=True)
    for ay in H_AX:
        for s in (-1, 1):
            vk.well(m, s, H_HW - 0.004, ay, hz, 0.38)
    g = Greenhouse(0.87, 1.38, -0.66, -0.02, 1.98, 1.66, 0.76, 0.64)
    g.build(m, paint)
    za, zb = 0.92, 1.33
    for s in (-1, 1):
        g.side_window(m, s, 0.08, 0.66, za, zb, front_slant=True)            # long door window
        g.side_window(m, s, 0.76, 0.14, za, zb, rear_slant=True)             # rear quarter window
    g.screens(m, za, zb, 0.07)
    # black plastic: bumpers wrapping the corners, side rubbing strips, door seams
    for s in (-1, 1):
        m.bevel_box(1.66, 0.14, 0.20, 0.04, 'black', at=(0, s * (H_HL + 0.03), 0.42))
        side_plate(m, s, H_HW, rect_yz(-0.88, 0.74, 0.50, 0.56), 'black', t=0.012)
        for y in (-0.62, 0.70):
            m.box(0.010, 0.022, 0.50, 'black', at=(s * (H_HW + 0.003), y, 0.36), base=True)
        m.box(0.03, 0.12, 0.03, 'black', at=(s * (H_HW + 0.012), 0.58, 0.80))
    # nose: wide rectangular headlights with a slatted dark grille between; tail lamps across the back
    m.box(0.62, 0.03, 0.10, 'black', at=(0, -H_HL - 0.005, 0.62))
    for s in (-1, 1):
        m.box(0.40, 0.03, 0.12, 'white', at=(s * 0.53, -H_HL - 0.005, 0.62))
        m.box(0.10, 0.03, 0.12, 'orange', at=(s * 0.78, -H_HL + 0.02, 0.62))
        m.box(0.36, 0.03, 0.14, 'red', at=(s * 0.56, H_HL + 0.005, 0.74))
        m.box(0.12, 0.03, 0.14, 'orange', at=(s * 0.30, H_HL + 0.005, 0.74))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, -H_HL - 0.105, 0.40))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, H_HL + 0.012, 0.62))
    # roof spoiler lip over the hatch glass, driver mirror, single wiper
    m.bevel_box(1.20, 0.10, 0.04, 0.015, paint, at=(0, 1.62, 1.38))
    m.bevel_box(0.07, 0.12, 0.10, 0.015, 'black', at=(H_HW - 0.01, -0.58, 0.95))
    m.beam((-0.32, g.yf(0.93) - 0.02, 0.93), (0.30, g.yf(0.93) - 0.02, 0.94), 0.02, 0.02, 'black')
    return m


# ---------------------------------------------------------------- assets
COLOURS = (('Blue', 'car_blue', 'pale blue'), ('Red', 'red', 'cherry red'), ('Beige', 'cream', 'beige'),
           ('Green', 'green', 'green'))
SEDAN_NOTE = ('Parked boxy Soviet 1970s sedan, %s paint ("classic" proportions, no logos, no number on the plates): '
              'four round headlights in a dark grille, chrome bumpers with overriders, chrome hubcaps, four doors, '
              'no interior (dark glass). Faces -Y; driver side +X.')
for suffix, col, word in COLOURS:
    vk.asset(fam, f'VK_Car_Sedan_{suffix}', lambda c=col: sedan(c), SEDAN_NOTE % word)
vk.asset(fam, 'VK_Car_Hatchback', lambda: hatchback('purple'),
         'Parked 1980s wedge 3-door hatchback, "aubergine" paint: low nose, steep hatch with a roof lip, rectangular '
         'headlights, black plastic bumpers and rubbing strips, steel wheels. No interior. Faces -Y; driver side +X.')
vk.asset(fam, 'VK_Car_Police', lambda: sedan('white', police=True),
         'Police version of the sedan: white with a blue band along both flanks and across the bonnet, roof light bar '
         '(red / white / blue). No text, no interior. Faces -Y; driver side +X.')

fam.finish(gap=2.5)
