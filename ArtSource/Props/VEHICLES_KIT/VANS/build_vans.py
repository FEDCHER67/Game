"""VEHICLES_KIT / VANS - parked "loaf" 4x4 minibus (UAZ-like silhouette) and a short-bonnet ambulance van.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/VEHICLES_KIT/VANS/build_vans.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/VEHICLES_KIT/VANS/build_vans.py -- --revision 1
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import vehiclekit as vk
from vehiclekit import sk, Mesh, side_plate, end_plate, rect_yz, rect_xz, plate

fam = sk.Family('VK-VANS', __file__)


def seam_v(m, s, x, y, z0, z1):
    """Vertical dark door seam on the side plane x."""
    m.box(0.010, 0.022, z1 - z0, 'black', at=(s * (x + 0.003), y, z0), base=True)


# ---------------------------------------------------------------- rounded "loaf" minibus, high-riding 4x4
M_HL, M_HW = 2.18, 0.97
M_AX = (-1.16, 1.14)


def minibus(paint='green'):
    m = Mesh()
    hz = vk.wheels(m, (-0.85, 0.85), M_AX, 0.40, 0.22, 10, rim=paint, rim_r=0.20)
    for ay in M_AX:                                                 # visible axles under the high body
        m.bar((-0.85, ay, hz), (0.85, ay, hz), 0.05, 'metal_dark', seg=6)
    vk.tub_with_arches(m, M_HW, -M_HL, M_HL, 0.55, 0.80, 2.05, M_AX, 0.46, hz, paint, bev=0.04, upper_bev=0.17)
    fw = M_HW - 0.17                                                # flat part of the front / rear faces
    # glass: split windscreen, side windows, rear door windows
    for x0, x1 in ((-fw + 0.04, -0.04), (0.04, fw - 0.04)):
        end_plate(m, -1, -M_HL, rect_xz(x0, x1, 1.32, 1.84), 'glass_dark', t=0.010)
        end_plate(m, 1, M_HL, rect_xz(x0 + 0.06, x1 - 0.06, 1.38, 1.78), 'glass_dark', t=0.010)
    for s in (-1, 1):
        for y0, y1 in ((-1.92, -1.34), (-0.98, -0.30), (-0.10, 0.62), (0.82, 1.54)):
            side_plate(m, s, M_HW, rect_yz(y0, y1, 1.34, 1.80), 'glass_dark', t=0.010)
        for y in (-1.98, -1.26):                                    # cab doors
            seam_v(m, s, M_HW, y, 0.86, 1.90)
        m.box(0.03, 0.12, 0.03, 'metal_dark', at=(s * (M_HW + 0.012), -1.42, 1.22))
        vk.mirror(m, s, M_HW, -1.90, 1.38)
    for y in (-1.06, -0.22):                                        # kerb-side passenger door
        seam_v(m, -1, M_HW, y, 0.86, 1.90)
    m.box(0.03, 0.12, 0.03, 'metal_dark', at=(-(M_HW + 0.012), -0.36, 1.22))
    m.box(0.022, 0.010, 1.00, 'black', at=(0, M_HL + 0.003, 0.88), base=True)          # rear doors seam
    # face: round headlights, sidelights above, slotted grille; bumpers, lamps, plates
    for s in (-1, 1):
        vk.lamp(m, s * 0.64, -M_HL - 0.02, 1.04, 0.10, 'white', depth=0.04)
        m.box(0.10, 0.03, 0.06, 'orange', at=(s * 0.64, -M_HL - 0.01, 1.22))
        m.box(0.10, 0.03, 0.20, 'red', at=(s * 0.70, M_HL + 0.01, 1.00))
    m.box(0.56, 0.03, 0.34, 'metal_dark', at=(0, -M_HL - 0.01, 1.04))
    for x in (-0.18, -0.06, 0.06, 0.18):
        m.box(0.04, 0.03, 0.30, paint, at=(x, -M_HL - 0.025, 1.04))
    for s in (-1, 1):
        m.bevel_box(2.00, 0.12, 0.14, 0.03, 'metal_dark', at=(0, s * (M_HL + 0.06), 0.64))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, -M_HL - 0.13, 0.78))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, M_HL + 0.012, 0.90))
    return m


# ---------------------------------------------------------------- short-bonnet ambulance van with a high box
A_HL, A_HW = 2.75, 1.02
A_AX = (-1.45, 1.45)
A_WS = (-1.85, 1.12, -1.25, 2.12)          # windscreen line: base (y, z) -> top (y, z)


def yws(z):
    y0, z0, y1, z1 = A_WS
    return y0 + (z - z0) * (y1 - y0) / (z1 - z0)


def ambulance():
    m = Mesh()
    W, RED, BLUE = 'white', 'sign_red', 'sign_blue'
    hz = vk.wheels(m, (-0.84, 0.84), A_AX, 0.36, 0.20, 10, rim='metal', rim_r=0.17)
    # bonnet and cab+box silhouettes (upper body), lower blocks between the wheel openings, underbody
    vk.side_prism(m, [(-A_HL + 0.03, 0.80), (-1.80, 0.80), (-1.80, 1.15), (-2.62, 1.04), (-A_HL + 0.03, 0.95)], 2 * A_HW - 0.04, W)
    vk.side_prism(m, [(-1.85, 0.80), (A_HL, 0.80), (A_HL, 2.50), (-0.95, 2.50), (A_WS[2], A_WS[3]), (A_WS[0], A_WS[1])],
                  2 * A_HW, W)
    cuts = (-A_HL + 0.03, A_AX[0] - 0.42, A_AX[0] + 0.42, A_AX[1] - 0.42, A_AX[1] + 0.42, A_HL)
    for a, b in zip(cuts[::2], cuts[1::2]):
        m.bevel_box(2 * A_HW - 0.04, b - a, 0.37, 0.04, W, at=(0, (a + b) / 2, 0.45), base=True)
    m.box(2 * A_HW - 0.24, 2 * A_HL - 0.3, 0.36, 'black', at=(0, 0, 0.45), base=True)
    for ay in A_AX:
        for s in (-1, 1):
            vk.well(m, s, A_HW - 0.004, ay, hz, 0.42)
    # glass
    za, zb = 1.20, 2.04
    plate(m, [(-0.92, yws(za), za), (0.92, yws(za), za), (0.92, yws(zb), zb), (-0.92, yws(zb), zb)],
          (0, -(A_WS[3] - A_WS[1]), A_WS[2] - A_WS[0]), 0.010, 'glass_dark')
    for s in (-1, 1):
        side_plate(m, s, A_HW, [(yws(1.25) + 0.10, 1.25), (-1.06, 1.25), (-1.06, 1.95), (yws(1.95) + 0.10, 1.95)], 'glass_dark', t=0.010)
        side_plate(m, s, A_HW, rect_yz(0.15, 0.95, 1.55, 2.00), 'glass', t=0.010)                 # frosted box window
        # red band along bonnet and body, red cross on the box
        side_plate(m, s, A_HW - 0.02, [(-2.70, 0.86), (-1.81, 0.86), (-1.81, 1.00), (-2.66, 1.00)], RED, t=0.006)
        side_plate(m, s, A_HW, rect_yz(-1.84, A_HL - 0.04, 0.86, 1.00), RED, t=0.006)
        vk.cross(m, s, A_HW, 1.95, 1.72, 0.56, RED)
        seam_v(m, s, A_HW, -0.98, 0.86, 2.02)
        m.box(0.03, 0.12, 0.03, 'black', at=(s * (A_HW + 0.012), -1.14, 1.16))
        vk.mirror(m, s, A_HW, -1.62, 1.50, col='black', arm=0.14)
    for y in (-0.82, 0.08):                                         # kerb-side sliding door
        seam_v(m, -1, A_HW, y, 0.86, 2.30)
    for x0, x1 in ((-0.86, -0.12), (0.12, 0.86)):                   # rear doors: frosted windows
        end_plate(m, 1, A_HL, rect_xz(x0, x1, 1.75, 2.28), 'glass', t=0.010)
    m.box(0.022, 0.010, 1.56, 'black', at=(0, A_HL + 0.003, 0.84), base=True)
    vk.end_cross(m, 1, A_HL, 0, 1.36, 0.44, RED)
    end_plate(m, 1, A_HL, rect_xz(-A_HW + 0.04, A_HW - 0.04, 0.86, 1.00), RED, t=0.006)
    # roof beacons over the cab, blue beacon at the rear corner
    vk.light_bar(m, -0.62, 2.50, 1.30, [BLUE, W, BLUE])
    m.cyl(0.08, 0.14, 8, BLUE, at=(0.80, A_HL - 0.18, 2.50))
    # nose: grille, rectangular headlights, black bumper; rear lamps, bumper with step, plates
    m.box(0.80, 0.03, 0.12, 'metal_dark', at=(0, -A_HL + 0.015, 0.88))
    for s in (-1, 1):
        m.box(0.34, 0.03, 0.12, W, at=(s * 0.68, -A_HL + 0.015, 0.88))
        m.box(0.12, 0.03, 0.40, 'red', at=(s * 0.92, A_HL + 0.01, 1.20))
    m.bevel_box(2.08, 0.16, 0.22, 0.04, 'black', at=(0, -A_HL - 0.04, 0.60))
    m.bevel_box(2.04, 0.14, 0.16, 0.04, 'black', at=(0, A_HL + 0.05, 0.55))
    m.box(0.90, 0.30, 0.04, 'metal_dark', at=(0, A_HL + 0.12, 0.42))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, -A_HL - 0.13, 0.60))
    m.box(0.52, 0.02, 0.11, 'white', at=(0, A_HL + 0.13, 0.55))
    return m


vk.asset(fam, 'VK_Van_Minibus', minibus,
         'Parked rounded "loaf" 4x4 minibus (UAZ-like silhouette, no logos), army green: high ground clearance with '
         'visible axles, split windscreen, round headlights and slotted grille, four side windows, kerb-side passenger '
         'door, twin rear doors. No interior. Faces -Y; driver side +X.')
vk.asset(fam, 'VK_Van_Ambulance', ambulance,
         'Parked short-bonnet ambulance van with a high box body: white, red band and red crosses (sides and rear), '
         'blue roof light bar and rear beacon, frosted box windows, kerb-side sliding door, twin rear doors. '
         'No text, no interior. Faces -Y; driver side +X.')

fam.finish(gap=3.0)
