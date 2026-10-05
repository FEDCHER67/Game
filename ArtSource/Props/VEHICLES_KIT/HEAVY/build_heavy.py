"""VEHICLES_KIT / HEAVY - parked bonnet tow truck with a crane boom, a rounded city bus (bus-stop scale) and a small tractor.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/VEHICLES_KIT/HEAVY/build_heavy.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/VEHICLES_KIT/HEAVY/build_heavy.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import vehiclekit as vk
from vehiclekit import sk, Mesh, T, R, side_plate, end_plate, rect_yz, rect_xz, hexa
from mathutils import Vector

fam = sk.Family('VK-HEAVY', __file__)


def seam_v(m, s, x, y, z0, z1):
    m.box(0.010, 0.022, z1 - z0, 'black', at=(s * (x + 0.003), y, z0), base=True)


def fender(m, x, yc, zc, r, width, col, a0=180, a1=0, steps=6, thick=0.045):
    """Thin arched mudguard over a wheel: a square tube along the arc, stretched across to `width`."""
    t = Mesh()
    t.tube_path([(0, yc + r * math.cos(math.radians(lerp(a0, a1, k / steps))), zc + r * math.sin(math.radians(lerp(a0, a1, k / steps))))
                 for k in range(steps + 1)], thick / math.sqrt(2), 4, col)
    m.merge(t, T(x, 0, 0) @ sk.S(width / thick, 1, 1))


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- 1960s-style bonnet truck as a tow truck with a crane boom
def tow_truck():
    m = Mesh()
    P, Y = 'orange', 'yellow'
    FY, RY = -2.05, 1.75                                            # axles
    hz = vk.wheels(m, (-0.86, 0.86), (FY,), 0.47, 0.26, 10, rim='metal_dark', rim_r=0.24)
    vk.wheels(m, (-0.79, 0.79), (RY,), 0.47, 0.44, 10, rim='metal_dark', rim_r=0.24)     # twin rear tyres as one wide wheel
    for ay in (FY, RY):
        m.bar((-0.80, ay, hz), (0.80, ay, hz), 0.06, 'metal_dark', seg=6)
    for x in (-0.45, 0.45):                                         # frame rails
        m.box(0.12, 6.00, 0.20, 'black', at=(x, 0.10, 0.62), base=True)
    # bonnet, grille, lamp pods, front mudguards
    vk.side_prism(m, [(-3.05, 0.90), (-1.28, 0.90), (-1.28, 1.62), (-2.85, 1.56), (-3.05, 1.42)], 1.00, P)
    m.box(0.80, 0.04, 0.44, 'metal_dark', at=(0, -3.06, 1.14))
    for s in (-1, 1):
        fender(m, s * 0.86, FY, hz, 0.58, 0.40, P, a0=170, a1=8)
        m.bevel_box(0.18, 0.20, 0.18, 0.03, P, at=(s * 0.62, -2.80, 1.10))
        vk.lamp(m, s * 0.62, -2.89, 1.10, 0.075, 'white', depth=0.03)
        m.box(0.08, 0.03, 0.05, 'orange', at=(s * 0.62, -2.75, 1.25))
    m.bevel_box(2.10, 0.14, 0.18, 0.03, 'black', at=(0, -3.16, 0.80))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, -3.24, 0.80))
    # cab: windscreen in two panes, door windows, rear window; seams, handles, steps, mirrors, amber beacons
    m.bevel_box(2.00, 1.52, 1.26, 0.10, P, at=(0, -0.54, 1.00), base=True)
    for x0, x1 in ((-0.86, -0.04), (0.04, 0.86)):
        end_plate(m, -1, -1.30, rect_xz(x0, x1, 1.64, 2.12), 'glass_dark', t=0.010)
    end_plate(m, 1, 0.22, rect_xz(-0.50, 0.50, 1.70, 2.06), 'glass_dark', t=0.010)
    for s in (-1, 1):
        side_plate(m, s, 1.00, rect_yz(-1.14, -0.54, 1.62, 2.10), 'glass_dark', t=0.010)
        for y in (-1.22, -0.40):
            seam_v(m, s, 1.00, y, 1.08, 2.18)
        m.box(0.03, 0.12, 0.03, 'metal_dark', at=(s * 1.012, -0.55, 1.50))
        m.box(0.40, 0.40, 0.04, 'metal_dark', at=(s * 0.90, -0.80, 0.72))
        vk.mirror(m, s, 1.00, -1.18, 1.85, col='black', arm=0.18)
        m.cyl(0.08, 0.04, 8, 'black', at=(s * 0.55, -0.70, 2.26))
        m.cyl(0.07, 0.12, 8, 'orange', at=(s * 0.55, -0.70, 2.30))
    # deck, toolboxes, rear lamps and plate
    m.box(2.12, 2.72, 0.10, 'metal_dark', at=(0, 1.71, 1.00), base=True)
    for s in (-1, 1):
        m.box(2.72, 0.06, 0.10, P, M=T(s * 1.03, 1.71, 1.10) @ R(90, 'Z'), base=True)
        m.bevel_box(0.40, 0.70, 0.36, 0.03, P, at=(s * 0.82, 0.62, 0.64), base=True)
        m.box(0.14, 0.04, 0.10, 'red', at=(s * 0.92, 3.08, 0.92))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, 3.08, 0.80))
    m.box(2.06, 0.10, 0.16, 'black', at=(0, 3.03, 0.80))
    # crane: turret, A-frame, boom, pulley, cable and hook; underlift bar
    m.bevel_box(0.70, 0.70, 0.40, 0.04, P, at=(0, 2.00, 1.10), base=True)
    m.cyl(0.14, 0.60, 8, 'metal_dark', M=T(-0.30, 1.72, 1.36) @ R(90, 'Y'))                  # winch drum
    for s in (-1, 1):
        m.beam((s * 0.86, 0.90, 1.10), (s * 0.12, 2.86, 2.12), 0.12, 0.12, Y, up=(0, 0, 1))
    tip = Vector((0, 3.55, 2.85))
    m.beam((0, 2.00, 1.40), tuple(tip), 0.20, 0.20, Y, up=(0, 0, 1))
    m.bar((0, 1.80, 1.40), (0, 2.78, 2.15), 0.03, 'black', seg=4)                             # cable to the boom
    m.cyl(0.13, 0.14, 8, 'metal_dark', M=T(-0.07, tip.y + 0.05, tip.z) @ R(90, 'Y'))
    m.bar((0, tip.y + 0.17, tip.z), (0, tip.y + 0.17, 1.30), 0.012, 'black', seg=4)
    m.box(0.10, 0.10, 0.14, Y, at=(0, tip.y + 0.17, 1.24))
    m.tube_path([(0, tip.y + 0.17, 1.18), (0, tip.y + 0.17, 1.06), (0, tip.y + 0.22, 0.98), (0, tip.y + 0.31, 1.00),
                 (0, tip.y + 0.34, 1.08)], 0.022, 4, 'metal_dark')
    m.beam((0, 3.00, 0.66), (0, 3.55, 0.56), 0.16, 0.12, 'metal_dark')
    m.box(1.10, 0.14, 0.12, Y, at=(0, 3.58, 0.56))
    return m


# ---------------------------------------------------------------- rounded 1960s-70s city bus (fits the bus stop kerb)
B_HL, B_HW = 5.25, 1.25
B_AX = (-2.85, 2.30)


def bus():
    m = Mesh()
    P, ST = 'cream', 'red'
    hz = vk.wheels(m, (-1.05, 1.05), (B_AX[0],), 0.50, 0.28, 10, rim='metal', rim_r=0.24)
    vk.wheels(m, (-0.96, 0.96), (B_AX[1],), 0.50, 0.46, 10, rim='metal', rim_r=0.24)
    vk.tub_with_arches(m, B_HW, -B_HL, B_HL, 0.40, 0.95, 2.80, B_AX, 0.58, hz, P, bev=0.05, upper_bev=0.12)
    hexa(m, [Vector((-1.20, -5.10, 2.80)), Vector((1.20, -5.10, 2.80)), Vector((1.20, 5.10, 2.80)), Vector((-1.20, 5.10, 2.80))],
         [Vector((-0.98, -4.84, 3.02)), Vector((0.98, -4.84, 3.02)), Vector((0.98, 4.84, 3.02)), Vector((-0.98, 4.84, 3.02))], 'white')
    zw0, zw1 = 1.55, 2.45
    # kerb side (-X): three folding doors, windows between them, red band in segments
    doors = ((-4.98, -3.88), (-0.58, 0.52), (3.28, 4.38))
    for y0, y1 in doors:
        side_plate(m, -1, B_HW, rect_yz(y0, y1, 0.48, 2.50), 'glass_dark', t=0.010)
        seam_v(m, -1, B_HW + 0.01, (y0 + y1) / 2, 0.48, 2.50)
        m.box(0.012, y1 - y0, 0.10, P, at=(-(B_HW + 0.012), (y0 + y1) / 2, 1.20))
    for y0, y1 in ((-3.70, -2.22), (-2.10, -0.74), (0.68, 1.96), (2.08, 3.12), (4.54, 5.04)):
        side_plate(m, -1, B_HW, rect_yz(y0, y1, zw0, zw1), 'glass_dark', t=0.010)
    for y0, y1 in ((-5.14, -5.02), (-3.82, -0.64), (0.58, 3.22), (4.44, 5.14)):
        side_plate(m, -1, B_HW, rect_yz(y0, y1, 1.10, 1.30), ST, t=0.006)
    # driver side (+X): driver window, six panes, full red band
    for y0, y1 in ((-4.98, -3.98), (-3.86, -2.46), (-2.34, -0.94), (-0.82, 0.58), (0.70, 2.10), (2.22, 3.62), (3.74, 5.02)):
        side_plate(m, 1, B_HW, rect_yz(y0, y1, zw0, zw1), 'glass_dark', t=0.010)
    side_plate(m, 1, B_HW, rect_yz(-5.14, 5.14, 1.10, 1.30), ST, t=0.006)
    # front: split windscreen, route board, red band, round headlights, bumper, plate, bull-horn mirrors
    for x0, x1 in ((-1.08, -0.03), (0.03, 1.08)):
        end_plate(m, -1, -B_HL, rect_xz(x0, x1, 1.30, 2.48), 'glass_dark', t=0.010)
    end_plate(m, -1, -B_HL, rect_xz(-0.72, 0.72, 2.52, 2.66), 'white', t=0.012)
    end_plate(m, -1, -B_HL, rect_xz(-1.12, 1.12, 1.10, 1.30), ST, t=0.006)
    for s in (-1, 1):
        vk.lamp(m, s * 0.92, -B_HL - 0.02, 0.74, 0.11, 'white', depth=0.04)
        m.box(0.12, 0.03, 0.07, 'orange', at=(s * 0.92, -B_HL - 0.01, 0.92))
        vk.mirror(m, s, B_HW - 0.05, -5.10, 2.12, col='black', arm=0.22)
        m.box(0.14, 0.04, 0.34, 'red', at=(s * 1.02, B_HL + 0.01, 1.00))
    m.bevel_box(2.52, 0.14, 0.20, 0.04, 'metal_dark', at=(0, -B_HL - 0.05, 0.50))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, -B_HL - 0.125, 0.50))
    # rear: window, engine grille, red band, lamps, bumper, plate
    end_plate(m, 1, B_HL, rect_xz(-0.96, 0.96, 1.60, 2.45), 'glass_dark', t=0.010)
    end_plate(m, 1, B_HL, rect_xz(-0.80, 0.80, 0.62, 1.02), 'metal_dark', t=0.010)
    end_plate(m, 1, B_HL, rect_xz(-1.12, 1.12, 1.10, 1.30), ST, t=0.006)
    m.bevel_box(2.52, 0.14, 0.20, 0.04, 'metal_dark', at=(0, B_HL + 0.05, 0.50))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, B_HL + 0.125, 0.50))
    return m


# ---------------------------------------------------------------- small two-axle tractor with a glazed cab
def tractor():
    m = Mesh()
    P = 'red'
    RY, FY = 0.55, -1.25
    hr = vk.wheels(m, (-0.66, 0.66), (RY,), 0.62, 0.30, 12, rim=P, rim_r=0.36, rim_seg=8)
    hf = vk.wheels(m, (-0.58, 0.58), (FY,), 0.34, 0.15, 10, rim=P, rim_r=0.17)
    m.bar((-0.58, FY, hf), (0.58, FY, hf), 0.05, 'metal_dark', seg=6)
    m.bar((-0.66, RY, hr), (0.66, RY, hr), 0.08, 'metal_dark', seg=6)
    m.box(0.46, 1.95, 0.48, 'metal_dark', at=(0, -0.58, 0.30), base=True)                    # engine block / gearbox
    m.box(0.80, 0.22, 0.20, 'metal_dark', at=(0, -1.82, 0.44), base=True)                    # front weight
    # bonnet, grille, lamps, exhaust, air intake
    m.bevel_box(0.64, 1.46, 0.52, 0.06, P, at=(0, -1.04, 0.74), base=True)
    m.box(0.50, 0.03, 0.38, 'metal_dark', at=(0, -1.77, 0.98))
    for s in (-1, 1):
        vk.lamp(m, s * 0.20, -1.78, 1.12, 0.055, 'white', depth=0.03)
    m.bar((0.20, -1.30, 1.24), (0.20, -1.30, 2.02), 0.035, 'black', seg=6)
    m.cyl(0.05, 0.06, 6, 'black', at=(0.20, -1.30, 2.02))
    m.cyl(0.07, 0.28, 6, 'metal', at=(-0.18, -1.40, 1.24))
    # cab between the rear wheels: red lower shell, glass box, corner posts, white roof
    m.box(0.96, 1.22, 0.06, 'metal_dark', at=(0, 0.30, 1.00), base=True)
    m.bevel_box(0.94, 1.20, 0.46, 0.04, P, at=(0, 0.30, 1.04), base=True)
    m.box(0.90, 1.16, 0.78, 'glass_dark', at=(0, 0.30, 1.48), base=True)
    for x in (-0.46, 0.46):
        for y in (-0.29, 0.89):
            m.box(0.06, 0.06, 0.80, P, at=(x, y, 1.48), base=True)
    m.bevel_box(1.12, 1.38, 0.09, 0.03, 'white', at=(0, 0.30, 2.26), base=True)
    # rear mudguards, rear lamps, three-point hitch
    for s in (-1, 1):
        fender(m, s * 0.66, RY, hr, 0.70, 0.38, P, a0=176, a1=4, steps=6)
        m.box(0.06, 0.04, 0.06, 'red', at=(s * 0.66, RY + 0.71, hr + 0.10))
        m.beam((s * 0.24, 0.95, 0.52), (s * 0.34, 1.55, 0.42), 0.06, 0.06, 'metal_dark')
    m.beam((0, 0.95, 1.00), (0, 1.55, 0.78), 0.06, 0.06, 'metal_dark')
    m.box(0.30, 0.20, 0.30, 'metal_dark', at=(0, 0.88, 0.62), base=True)
    return m


vk.asset(fam, 'VK_Truck_Tow', tow_truck,
         'Parked 1960s-style bonnet truck converted into a tow truck: orange cab and bonnet, arched front mudguards, '
         'flat steel deck with toolboxes, yellow crane boom on an A-frame with pulley, cable and hook, rear underlift '
         'bar, two amber beacons. Twin rear tyres are one wide wheel. No interior. Faces -Y; driver side +X.')
vk.asset(fam, 'VK_Bus_City', bus,
         'Parked rounded city bus, about 10.5 m: cream body, white roof cap, red band, three folding doors on the kerb '
         'side (-X), split windscreen with a blank route board, round headlights, bull-horn mirrors, rear engine grille. '
         'Floor/door sill height matches the STREET_KIT bus stop. No interior. Faces -Y.')
vk.asset(fam, 'VK_Tractor_Small', tractor,
         'Parked small two-axle tractor: red bonnet and mudguards, big rear wheels, small front wheels, glazed cab with '
         'a white roof, vertical exhaust, front weight, three-point hitch. No interior. Faces -Y; driver side +X.')

fam.finish(gap=4.0)
