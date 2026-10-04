"""STREET_KIT / BENCHES - Soviet concrete-and-wood courtyard bench (intact and broken) and a cast-iron park bench.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/BENCHES/build_benches.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/BENCHES/build_benches.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import streetkit as sk
from streetkit import Mesh, T, R

fam = sk.Family('SK-BENCHES', __file__)
BACK_TILT = 14.0          # degrees the backrest leans back from vertical


def concrete_wood(broken=False):
    m = Mesh()
    L = 2.0
    for i, x in enumerate((-0.72, 0.72)):
        lean = None
        s = Mesh()
        s.bevel_box(0.18, 0.60, 0.10, 0.03, 'concrete', at=(0, 0.02, 0), base=True)              # foot
        s.bevel_box(0.15, 0.20, 0.34, 0.03, 'concrete', at=(0, 0.04, 0.08), base=True)           # column
        s.bevel_box(0.17, 0.52, 0.09, 0.03, 'concrete', at=(0, -0.01, 0.33), base=True)          # seat arm
        tilt = math.radians(BACK_TILT)
        p0 = (0, 0.20, 0.36)
        p1 = (0, 0.20 + 0.50 * math.sin(tilt), 0.36 + 0.50 * math.cos(tilt))
        s.beam(p0, p1, 0.15, 0.10, 'concrete', up=(0, 1, 0))                                       # backrest arm
        m.merge(s, T(x, 0, 0) @ (lean or T()))
    seat_y = (-0.21, -0.07, 0.07)
    for k, y in enumerate(seat_y):
        if broken and k == 1:
            continue                                                                              # missing slat
        if broken and k == 2:
            # cracked slat sagging in the middle: two halves meeting low
            m.beam((-L / 2, y, 0.445), (0.05, y, 0.40), 0.12, 0.045, 'wood_dark', up=(0, 0, 1))
            m.beam((0.05, y, 0.40), (L / 2, y, 0.445), 0.12, 0.045, 'wood_dark', up=(0, 0, 1))
            continue
        m.bevel_box(L, 0.12, 0.045, 0.012, 'wood_dark' if broken else 'wood', at=(0, y, 0.445))
    tilt = math.radians(BACK_TILT)
    for k, h in enumerate((0.30, 0.46)):
        if broken and k == 1:
            # top backrest slat hanging off one end
            c = (0.25 + 0.5 * math.sin(tilt) * 0, 0.27, 0.62)
            m.bevel_box(1.40, 0.11, 0.04, 0.012, 'wood_dark',
                        M=T(-0.2, 0.20 + (h - 0.05) * math.sin(tilt) + 0.07, 0.36 + (h - 0.05) * math.cos(tilt)) @ R(-BACK_TILT, 'X') @ R(-12, 'Y') @ R(90, 'X'))
            continue
        y = 0.20 + h * math.sin(tilt) - 0.07 * math.cos(tilt)
        z = 0.36 + h * math.cos(tilt) + 0.07 * math.sin(tilt) * 0
        m.bevel_box(L, 0.04, 0.12, 0.012, 'wood_dark' if broken else 'wood', M=T(0, y - 0.03, z) @ R(-BACK_TILT, 'X'))
    if broken:
        sk.jitter(m, 0.004, 7)
    return m


def park():
    m = Mesh()
    L = 1.8
    frame = 'metal_dark'
    for x in (-0.78, 0.78):
        # cast-iron side: front leg -> seat rail -> back leg, then a curved backrest arm with a scroll, and an armrest
        m.tube_path([(x, -0.27, 0.0), (x, -0.25, 0.20), (x, -0.22, 0.40), (x, 0.05, 0.42), (x, 0.20, 0.40), (x, 0.24, 0.20), (x, 0.27, 0.0)],
                    0.035, 6, frame)
        m.tube_path([(x, 0.16, 0.40), (x, 0.22, 0.58), (x, 0.28, 0.76), (x, 0.34, 0.90), (x, 0.30, 0.96), (x, 0.25, 0.92)], 0.03, 6, frame)
        m.tube_path([(x, -0.24, 0.42), (x, -0.25, 0.58), (x, -0.18, 0.64), (x, 0.05, 0.64), (x, 0.22, 0.60)], 0.026, 6, frame)
        m.bevel_box(0.10, 0.10, 0.03, 0.01, frame, at=(x, -0.27, 0), base=True)      # feet pads
        m.bevel_box(0.10, 0.10, 0.03, 0.01, frame, at=(x, 0.27, 0), base=True)
    # seat slats follow a slight dip, backrest slats follow the curved arm
    for y, z in ((-0.20, 0.455), (-0.10, 0.445), (0.0, 0.44), (0.10, 0.445), (0.19, 0.45)):
        m.bevel_box(L + 0.06, 0.085, 0.035, 0.01, 'green', at=(0, y, z))
    for t in (0.25, 0.48, 0.70):
        y = 0.18 + t * 0.20
        z = 0.48 + t * 0.48
        m.bevel_box(L + 0.06, 0.035, 0.09, 0.01, 'green', M=T(0, y - 0.035, z) @ R(-22, 'X'))
    return m


for name, fn, notes in (
        ('SK_Bench_ConcreteWood', lambda: concrete_wood(False), 'Courtyard bench: two concrete supports, three seat slats, two backrest slats; seat height 0.47 m.'),
        ('SK_Bench_ConcreteWood_Broken', lambda: concrete_wood(True), 'Bad-district variant: missing seat slat, cracked sagging slat, backrest slat hanging off, one support settled.'),
        ('SK_Bench_Park', park, 'Park bench: cast-iron tube sides with scrolls and armrests, green-painted slats; seat height 0.47 m.')):
    if fam.wants(name):
        fam.asset(name, [(name + '_Mesh', fn(), None, None)], notes=notes)

fam.finish()
