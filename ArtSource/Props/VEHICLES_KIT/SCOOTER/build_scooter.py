"""VEHICLES_KIT / SCOOTER - parked 1960s-style Soviet motor scooter on its centre stand.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/VEHICLES_KIT/SCOOTER/build_scooter.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/VEHICLES_KIT/SCOOTER/build_scooter.py -- --revision 1
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import vehiclekit as vk
from vehiclekit import sk, Mesh, side_plate, rect_yz

fam = sk.Family('VK-SCOOTER', __file__)


def scooter(paint='teal'):
    m = Mesh()
    FY, RY = -0.64, 0.60
    hz = vk.wheels(m, (0.0,), (FY, RY), 0.22, 0.10, 12, rim='chrome', rim_r=0.10)
    # rounded rear cowl over the engine and rear wheel, chrome side trims, seat, rack, tail lamp, plate
    m.bevel_box(0.50, 0.82, 0.40, 0.12, paint, at=(0, 0.52, 0.30), base=True)
    for s in (-1, 1):
        side_plate(m, s, 0.25, rect_yz(0.26, 0.78, 0.48, 0.51), 'chrome', t=0.006)
    m.bevel_box(0.30, 0.60, 0.10, 0.03, 'black', at=(0, 0.40, 0.70), base=True)
    m.tube_path([(-0.12, 0.72, 0.76), (0.12, 0.72, 0.76), (0.12, 0.98, 0.76), (-0.12, 0.98, 0.76)], 0.012, 4, 'chrome', closed=True)
    m.box(0.12, 0.04, 0.06, 'red', at=(0, 0.94, 0.58))
    m.box(0.20, 0.02, 0.12, 'white', at=(0, 0.95, 0.42))
    # floorboard and frame, leg shield, front mudguard, fork, steering column, headset with lamp, handlebar, mirror
    m.box(0.34, 0.62, 0.05, 'black', at=(0, -0.24, 0.24), base=True)
    m.box(0.30, 0.60, 0.10, paint, at=(0, -0.24, 0.14), base=True)
    m.beam((0, -0.52, 0.20), (0, -0.60, 0.98), 0.48, 0.05, paint, up=(0, 1, 0))
    m.bevel_box(0.16, 0.42, 0.10, 0.04, paint, at=(0, FY, 0.48))
    for x in (-0.07, 0.07):
        m.bar((x, FY, hz), (x * 0.85, -0.60, 0.62), 0.02, 'metal_dark', seg=4)
    m.bar((0, -0.60, 0.55), (0, -0.58, 1.02), 0.04, paint, seg=6)
    m.bevel_box(0.24, 0.20, 0.14, 0.04, paint, at=(0, -0.58, 1.06))
    vk.lamp(m, 0, -0.67, 1.06, 0.06, 'white', depth=0.03)
    m.bar((-0.34, -0.56, 1.10), (0.34, -0.56, 1.10), 0.015, 'chrome', seg=6)
    for s in (-1, 1):
        m.bar((s * 0.25, -0.56, 1.10), (s * 0.37, -0.56, 1.10), 0.024, 'black', seg=6)
    m.bar((0.22, -0.56, 1.10), (0.26, -0.58, 1.30), 0.008, 'chrome', seg=4)
    m.bevel_box(0.10, 0.03, 0.07, 0.01, 'chrome', at=(0.26, -0.58, 1.33))
    # silencer on the kerb side (-X), centre stand
    m.bar((-0.24, 0.30, 0.20), (-0.24, 0.86, 0.25), 0.04, 'chrome', seg=6)
    for x in (-0.13, 0.13):
        m.box(0.04, 0.06, 0.16, 'metal_dark', at=(x, 0.10, 0.0), base=True)
    return m


vk.asset(fam, 'VK_Scooter', scooter,
         'Parked 1960s-style Soviet motor scooter on its centre stand, mint/teal: rounded rear cowl with chrome trims, '
         'small wheels, leg shield, front mudguard, headset lamp, black bench seat with a chrome rack, silencer on '
         'the right. Faces -Y.')

fam.finish(gap=1.0)
