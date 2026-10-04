"""STREET_KIT / BUS_STOP - Soviet courtyard-road bus stop shelter (intact and vandalised) with a stop sign post.

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/BUS_STOP/build_bus_stop.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/BUS_STOP/build_bus_stop.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import streetkit as sk
from streetkit import Mesh, T, R

fam = sk.Family('SK-BUS_STOP', __file__)
W, D, H = 4.0, 1.6, 2.45          # inner width, depth, wall height; open side faces -Y
YB = D / 2                        # back wall line


def shelter(vandal):
    m = Mesh()
    m.bevel_box(W + 0.5, D + 0.4, 0.12, 0.03, 'concrete_dark', at=(0, 0, 0), base=True)             # floor slab
    # back wall: steel frame, lower sheet panels, glazing above
    xs = [-W / 2, -W / 6, W / 6, W / 2]
    for x in xs:
        m.box(0.08, 0.08, H, 'metal_dark', at=(x, YB, 0.12), base=True)
    m.box(W, 0.06, 0.06, 'metal_dark', at=(0, YB, 0.12 + 0.62))
    m.box(W, 0.06, 0.06, 'metal_dark', at=(0, YB, 0.12 + H - 0.03))
    for i, (a, b) in enumerate(zip(xs, xs[1:])):
        cx, w = (a + b) / 2, b - a - 0.08
        m.box(w, 0.04, 0.58, 'blue', at=(cx, YB, 0.12 + 0.02), base=True)                               # sheet panel
        if vandal and i == 1:
            # smashed pane: a few shards left in the frame
            for tri in (((-0.6, 0.80), (-0.1, 0.80), (-0.55, 1.45)), ((0.6, 2.53), (0.05, 2.53), (0.55, 1.95)),
                        ((0.6, 0.80), (0.35, 0.80), (0.6, 1.10))):
                m.prism([(cx + u, z) for u, z in tri], 0.02, 'glass', M=T(0, YB, 0))
        else:
            m.box(w, 0.03, H - 0.72, 'glass', at=(cx, YB, 0.12 + 0.66), base=True)
    # side walls: concrete slabs with a cheerful Soviet mosaic band on the outer face
    for s in (-1, 1):
        x = s * (W / 2 + 0.06)
        m.bevel_box(0.12, D, H, 0.02, 'concrete', at=(x, 0.0, 0.12), base=True)
        for k, (col, z) in enumerate((('orange', 1.75), ('yellow', 1.50), ('sign_blue', 1.25), ('teal', 1.00))):
            dy = 0.25 * ((k % 2) - 0.5)
            m.box(0.02, D - 0.5 - 0.15 * k, 0.20, col, at=(x + s * 0.07, dy, z))
        if vandal:
            m.box(0.02, 0.55, 0.32, 'pink', M=T(x + s * 0.07, -0.25, 0.70) @ R(8, 'X'))                  # graffiti tag
            m.box(0.02, 0.35, 0.10, 'black', M=T(x + s * 0.075, 0.15, 0.62) @ R(-12, 'X'))
    # roof: thick slab sloping slightly to the back, coloured fascia
    roof = T(0, 0.05, 0.12 + H + 0.10) @ R(-2.5, 'X')
    m.bevel_box(W + 0.7, D + 0.7, 0.16, 0.04, 'metal', M=roof)
    m.box(W + 0.72, 0.04, 0.22, 'orange', M=roof @ T(0, -(D + 0.7) / 2 - 0.0, -0.02))
    # bench along the back wall
    for x in (-1.2, 1.2):
        m.box(0.06, 0.36, 0.42, 'metal_dark', at=(x, YB - 0.24, 0.12), base=True)
    for k, y in enumerate((-0.32, -0.20, -0.08)):
        if vandal and k == 0:
            continue
        m.bevel_box(2.8, 0.11, 0.04, 0.01, 'wood', at=(0, YB - 0.24 + y + 0.20, 0.12 + 0.44))
    # timetable board on the inside of the back wall (signage atlas, square slot)
    m.sign_face_box(0.62, 0.62, 0.04, 'metal_dark', 'square_1x1', 0, M=T(1.25, YB - 0.05, 1.55))
    if vandal:
        # litter on the floor and a broken bottle
        m.bevel_box(0.25, 0.18, 0.12, 0.02, 'cream', M=T(-1.1, -0.2, 0.18) @ R(20, 'Z'))
        m.bar((0.6, -0.3, 0.14), (0.85, -0.25, 0.14), 0.035, 'green', seg=6)
        sk.jitter(m, 0.006, 3)
    return m


def stop_sign():
    """Post with the Russian 5.16 'bus stop' plate: blue square, white bus pictogram."""
    m = Mesh()
    x0, y0 = W / 2 + 0.9, -D / 2 - 0.45
    m.cyl(0.04, 2.75, 8, 'metal', at=(x0, y0, 0))
    m.bevel_box(0.62, 0.03, 0.62, 0.02, 'metal', at=(x0, y0 - 0.055, 2.40))                       # plate back, in front of the post
    m.box(0.58, 0.02, 0.58, 'sign_blue', at=(x0, y0 - 0.075, 2.40))
    m.bevel_box(0.44, 0.02, 0.24, 0.02, 'white', at=(x0, y0 - 0.09, 2.43))                       # bus body
    m.box(0.30, 0.02, 0.07, 'sign_blue', at=(x0 - 0.04, y0 - 0.10, 2.48))                          # window band
    m.box(0.02, 0.02, 0.07, 'white', at=(x0 - 0.04, y0 - 0.11, 2.48))                              # window post
    m.box(0.06, 0.02, 0.10, 'sign_blue', at=(x0 + 0.16, y0 - 0.10, 2.46))                          # windscreen
    for dx in (-0.12, 0.12):
        m.cyl(0.05, 0.02, 8, 'sign_blue', M=T(x0 + dx, y0 - 0.09, 2.31) @ R(90, 'X'))              # wheels (cut-outs)
        m.cyl(0.03, 0.02, 8, 'white', M=T(x0 + dx, y0 - 0.10, 2.31) @ R(90, 'X'))
    return m


for name, vandal, notes in (('SK_BusStop_Shelter', False, 'Shelter 4.0 x 1.6 m inside, open to -Y; glazing in the back wall, mosaic bands on the side walls, bench, timetable board (signage square_1x1 slot 0), stop sign post at +X front.'),
                            ('SK_BusStop_Shelter_Vandalised', True, 'Bad-district variant: smashed back pane (shards), missing bench slat, graffiti, litter.')):
    if fam.wants(name):
        m = shelter(vandal)
        m.merge(stop_sign())
        fam.asset(name, [(name + '_Mesh', m, None, None)], notes=notes)

fam.finish()
