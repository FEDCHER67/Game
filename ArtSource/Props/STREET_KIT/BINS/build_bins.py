"""STREET_KIT / BINS - Soviet concrete litter urn, tipping litter bin on posts, 0.75 m3 garbage container (closed / open).

Run from the repository root (bpy 5.0.1 from PyPI, Python 3.11, or Blender 5.x):
    python3 ArtSource/Props/STREET_KIT/BINS/build_bins.py -- --revision 1
    blender -b --factory-startup --python ArtSource/Props/STREET_KIT/BINS/build_bins.py -- --revision 1
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import streetkit as sk
from streetkit import Mesh, T, R, S

fam = sk.Family('SK-BINS', __file__)
SQ2 = math.sqrt(2)


def concrete_urn():
    m = Mesh()
    # vase-shaped hollow urn on a short foot; inside is a cup so it reads as a bin from above
    prof = [(0.17, 0.0), (0.17, 0.07), (0.13, 0.11), (0.15, 0.20), (0.23, 0.56), (0.27, 0.62), (0.27, 0.69),
            (0.22, 0.69), (0.20, 0.42), (0.0, 0.42)]
    cols = ['concrete_dark', 'concrete_dark', 'concrete', 'concrete', 'concrete', 'concrete', 'concrete', 'concrete_dark', 'black']
    m.lathe(prof, 10, 'concrete', cols=cols)
    # litter inside: crumpled paper and a bottle neck
    m.lathe([(0.0, 0.42), (0.10, 0.47), (0.08, 0.52), (0.0, 0.53)], 6, 'white', M=T(0.05, 0.03, 0) @ R(15, 'X'))
    m.bar((-0.06, -0.05, 0.43), (-0.02, -0.09, 0.66), 0.03, 'green', seg=6, r1=0.012)
    return m


def tipping_bin():
    """Two pipe posts, a bucket hanging on a cross axle between them (bucket is its own part, pivot on the axle)."""
    frame = Mesh()
    for x in (-0.30, 0.30):
        frame.cyl(0.03, 0.95, 8, 'metal_dark', at=(x, 0, 0))
        frame.cyl(0.045, 0.04, 8, 'metal_dark', at=(x, 0, 0.95))           # post cap
        frame.bevel_box(0.12, 0.12, 0.05, 0.015, 'concrete', at=(x, 0, 0), base=True)    # concreted foot
    frame.bar((-0.30, 0, 0.78), (0.30, 0, 0.78), 0.016, 'metal', seg=6)    # axle
    bucket = Mesh()
    z0 = 0.30
    prof = [(0.19, z0), (0.23, z0 + 0.50), (0.25, z0 + 0.52), (0.25, z0 + 0.56), (0.21, z0 + 0.56), (0.17, z0 + 0.06), (0.0, z0 + 0.06)]
    cols = ['blue', 'blue', 'blue', 'blue', 'blue', 'blue', 'rust']
    bucket.lathe(prof, 10, 'blue', cols=cols, offset=math.pi / 10)
    bucket.box(0.06, 0.06, 0.05, 'metal', at=(-0.255, 0, 0.78))           # axle hubs
    bucket.box(0.06, 0.06, 0.05, 'metal', at=(0.255, 0, 0.78))
    bucket.box(0.04, 0.12, 0.10, 'rust', at=(0, -0.23, z0 + 0.20))       # rust patch / dent on the front
    bucket.box(0.08, 0.05, 0.03, 'metal_dark', at=(0, -0.26, z0 + 0.50))   # tipping handle
    return frame, bucket


def container_body(open_top):
    m = Mesh()
    XS = 1.75                                         # x stretch of the square lathe
    hb, ht, z0, z1 = 0.33, 0.40, 0.14, 1.06          # half depth bottom/top (y), base and rim heights
    rim = 0.025
    prof = [(hb * SQ2, z0), (ht * SQ2, z1), ((ht + rim) * SQ2, z1), ((ht + rim) * SQ2, z1 + 0.05),
            ((ht - 0.03) * SQ2, z1 + 0.05), ((hb - 0.03) * SQ2, z0 + 0.06), (0.0, z0 + 0.06)]
    cols = ['green', 'green', 'green', 'green', 'green', 'green', 'rust']
    m.lathe(prof, 4, 'green', M=S(XS, 1, 1), offset=math.pi / 4, cols=cols)
    # vertical stiffening ribs on front and back, horizontal belt, rust on the lower edge
    for side in (-1, 1):
        for x in (-0.36, 0.0, 0.36):
            yb, yt = side * (hb + 0.01), side * (ht + 0.01)
            m.beam((x * (hb / ht) * 1.0, yb, z0 + 0.02), (x, yt, z1 - 0.02), 0.06, 0.03, 'green', up=(0, side, 0))
        m.beam((-0.62, side * (hb + 0.012), z0 + 0.08), (0.62, side * (hb + 0.012), z0 + 0.08), 0.06, 0.03, 'rust', up=(0, side, 0))
    # lifting trunnions on the short sides
    for x in (-1, 1):
        xx = x * (ht * XS + 0.0)
        m.bar((x * 0.62, 0, 0.86), (x * 0.78, 0, 0.86), 0.045, 'metal_dark', seg=8)
        m.cyl(0.075, 0.03, 8, 'metal_dark', M=T(x * 0.78, 0, 0.86) @ R(90 * x, 'Y'))
    # castors: fork blocks + wheels
    for x in (-0.46, 0.46):
        for y in (-0.22, 0.22):
            m.box(0.07, 0.10, 0.06, 'metal_dark', at=(x, y, z0 - 0.03))
            m.bar((x - 0.035, y, 0.06), (x + 0.035, y, 0.06), 0.06, 'rubber', seg=8)
    # graffiti-ish paint stripe and a number plate patch on the front
    m.box(0.40, 0.012, 0.16, 'white', M=T(-0.25, -(hb + ht) / 2 - 0.016, 0.62) @ R(-3.7, 'X'))
    m.box(0.30, 0.012, 0.08, 'yellow', M=T(0.30, -(hb + ht) / 2 - 0.016, 0.40) @ R(-3.7, 'X'))
    return m


def container_lid():
    """Lid closed: lies on the rim, hinge along the back top edge (y = +0.43, z = 1.11)."""
    m = Mesh()
    w, d = 1.48, 0.88
    m.bevel_box(w, d, 0.05, 0.02, 'green', at=(0, 0.43 - d / 2, 1.11 + 0.025))
    m.bevel_box(w - 0.3, d - 0.3, 0.03, 0.01, 'green', at=(0, 0.43 - d / 2, 1.16))    # pressed panel
    m.box(0.20, 0.06, 0.04, 'metal_dark', at=(0, 0.43 - d - 0.02, 1.13))                  # front handle
    for x in (-0.5, 0.5):
        m.bar((x - 0.08, 0.43, 1.12), (x + 0.08, 0.43, 1.12), 0.025, 'metal_dark', seg=6)  # hinge knuckles
    return m


def garbage_heap(seed):
    import random
    rnd = random.Random(seed)
    m = Mesh()
    spots = [(-0.40, -0.05, 1.02), (0.05, 0.10, 1.07), (0.42, -0.08, 1.00), (-0.10, -0.15, 1.12), (0.30, 0.15, 1.13)]
    for i, (x, y, z) in enumerate(spots):
        r = rnd.uniform(0.20, 0.26)
        col = 'bag' if i % 2 == 0 else 'black'
        start = len(m.verts)
        m.lathe([(0, -r * 0.8), (r, -r * 0.2), (r * 0.9, r * 0.5), (0, r * 0.8)], 6, col, M=T(x, y, z) @ R(rnd.uniform(-30, 30), 'X'))
        sk.jitter(m, 0.03, seed + i, start, keep_ground=False)
        m.bar((x, y, z + r * 0.7), (x + 0.02, y, z + r * 0.7 + 0.08), 0.03, col, seg=4)  # tied knot
    m.bevel_box(0.35, 0.25, 0.22, 0.02, 'cream', M=T(-0.2, 0.12, 1.15) @ R(25, 'Y') @ R(10, 'Z'))    # cardboard box
    # one bag on the ground in front
    start = len(m.verts)
    m.lathe([(0, 0.0), (0.24, 0.08), (0.20, 0.30), (0, 0.38)], 6, 'bag', M=T(0.55, -0.62, 0))
    sk.jitter(m, 0.025, seed + 99, start)
    return m


if fam.wants('SK_TrashBin_Concrete'):
    fam.asset('SK_TrashBin_Concrete', [('SK_TrashBin_Concrete_Mesh', concrete_urn(), None, None)],
              notes='Soviet concrete vase urn, hollow top with litter; 0.54 m wide, 0.69 m tall.')
if fam.wants('SK_TrashBin_Tipping'):
    frame, bucket = tipping_bin()
    fam.asset('SK_TrashBin_Tipping', [('SK_TrashBin_Tipping_Frame', frame, None, None),
                                      ('SK_TrashBin_Tipping_Bucket', bucket, (0, 0, 0.78), None)],
              notes='Tipping litter bin between two posts; the bucket pivots on the axle (local X) at z = 0.78 m.')
if fam.wants('SK_GarbageContainer_Closed'):
    fam.asset('SK_GarbageContainer_Closed', [('SK_GarbageContainer_Closed_Body', container_body(False), None, None),
                                             ('SK_GarbageContainer_Closed_Lid', container_lid(), (0, 0.43, 1.11), None)],
              notes='0.75 m3 street container with lid closed; lid pivot on the back hinge, rotate about local X (negative = open).')
if fam.wants('SK_GarbageContainer_Open'):
    body = container_body(True)
    body.merge(garbage_heap(5))
    fam.asset('SK_GarbageContainer_Open', [('SK_GarbageContainer_Open_Body', body, None, None),
                                           ('SK_GarbageContainer_Open_Lid', container_lid(), (0, 0.43, 1.11), (-112, 0, 0))],
              notes='Same container, lid thrown open (-112 deg about the hinge), overfilled with bags and a box, one bag on the ground.')

fam.finish()
