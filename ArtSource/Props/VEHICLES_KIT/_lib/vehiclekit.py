"""Shared helpers for the VEHICLES_KIT family builders (bpy 5.0.1 from PyPI or Blender 5.x, background mode).

Built on STREET_KIT/_lib/streetkit.py: same axes, pivots, FBX export, validation, previews and the same shared palette
material SK_Palette (SK_Palette.png is regenerated next to streetkit.py, byte-identical colours). Vehicle conventions:
  * Nose to -Y, so the driver's (left) side is +X and the kerb (right) side is -X - passenger doors face -X.
  * Pivot = centre of the base on the ground (root empty VK_<Asset> at the origin); the tyre flats rest on z = 0.
  * Static props: one mesh object per asset, no interiors, no moving parts, no sockets.
"""
import math, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'STREET_KIT' / '_lib'))
import streetkit as sk                                       # noqa: E402  (re-exported for the family scripts)
from streetkit import Mesh, T, R                             # noqa: E402
from mathutils import Vector                                 # noqa: E402


def plate(m, pts, out, t, col, inset=0.004):
    """Planar convex polygon thickened along its normal (t outwards, `inset` inwards) - glass, stripes, panels."""
    pts = [Vector(p) for p in pts]
    k = len(pts)
    n = Vector()
    for i in range(k):                                      # Newell normal
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


def side_plate(m, s, x, poly_yz, col, t=0.008, inset=0.004):
    """Plate on the side plane x = s * x (s = +1 left / driver side, -1 right / kerb side)."""
    return plate(m, [(s * x, y, z) for y, z in poly_yz], (s, 0, 0), t, col, inset)


def end_plate(m, s, y, poly_xz, col, t=0.008, inset=0.004):
    """Plate on the end plane y (s = -1 front face, +1 rear face)."""
    return plate(m, [(x, y, z) for x, z in poly_xz], (0, s, 0), t, col, inset)


def rect_yz(y0, y1, z0, z1):
    return [(y0, z0), (y1, z0), (y1, z1), (y0, z1)]


def rect_xz(x0, x1, z0, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def hexa(m, bot, top, col, cols=None):
    """Closed 8-vertex solid from a bottom and a top quad, both counter-clockwise seen from above."""
    v = [tuple(p) for p in bot] + [tuple(p) for p in top]
    f = [(3, 2, 1, 0), (4, 5, 6, 7)] + [(i, (i + 1) % 4, (i + 1) % 4 + 4, i + 4) for i in range(4)]
    return m.shell(v, f, col, cols=cols)


def side_prism(m, poly_yz, width, col, x=0.0, cap=None):
    """Convex side silhouette (y, z) extruded across the car (X) by `width`, centred on x."""
    return m.prism(poly_yz, width, col, M=T(x, 0, 0) @ R(90, 'Z'), cap=cap)


def wheel(r, w, seg=10, tyre='rubber', rim='chrome', rim_r=None, rim_seg=6):
    """Wheel centred on the origin, axle along X: tyre cylinder plus a slightly wider rim/hub cylinder."""
    t = Mesh()
    t.cyl(r, w, seg, tyre, M=T(-w / 2, 0, 0) @ R(90, 'Y'))
    if rim:
        rr = rim_r or r * 0.5
        t.cyl(rr, w + 0.03, rim_seg, rim, M=T(-(w + 0.03) / 2, 0, 0) @ R(90, 'Y'))
    return t


def hub_z(r, seg=10):
    """Hub height that puts the flat bottom of a `seg`-sided tyre on the ground."""
    return r * math.cos(math.pi / seg)


def wheels(m, xs, ys, r, w, seg=10, **kw):
    """Stand a wheel at every (x, y) combination; returns the hub height."""
    hz = hub_z(r, seg)
    wm = wheel(r, w, seg, **kw)
    for y in ys:
        for x in xs:
            m.merge(wm, T(x, y, hz))
    return hz


def well(m, s, x, y, z, r, col='black'):
    """Dark half-disc wheel well on the body side behind the upper half of a wheel."""
    disc = [(r * math.cos(math.radians(d)), r * math.sin(math.radians(d))) for d in (0, 45, 90, 135, 180)]
    m.prism(disc, 0.012, col, M=T(s * x, y, z) @ R(90, 'Z'))


def tub_with_arches(m, hw, y0, y1, z_sill, z_split, z_top, axles, arch_r, hz, col, lower_col=None, bev=0.05,
                    upper_bev=None, lips=None, lip_r=0.04):
    """Body block: an upper bevelled box from z_split to z_top over the whole length, lower bevelled blocks from the
    sill up to z_split between the wheel openings, dark half-disc wells, a black underbody, optional arch lips."""
    m.bevel_box(2 * hw, y1 - y0, z_top - z_split, upper_bev or bev, col, at=(0, (y0 + y1) / 2, z_split), base=True)
    cuts = [y0] + [c for ay in axles for c in (ay - arch_r, ay + arch_r)] + [y1]
    for a, b in zip(cuts[::2], cuts[1::2]):
        if b - a > 0.05:
            m.bevel_box(2 * hw - 0.02, b - a, z_split - z_sill + 0.02, bev, lower_col or col,
                        at=(0, (a + b) / 2, z_sill), base=True)
    m.box(2 * hw - 0.24, y1 - y0 - 0.2, z_split - z_sill, 'black', at=(0, (y0 + y1) / 2, z_sill), base=True)
    for ay in axles:
        for s in (-1, 1):
            well(m, s, hw - 0.004, ay, hz, arch_r)
            if lips:
                lr = arch_r + lip_r * 0.6
                m.tube_path([(s * (hw - 0.005), ay + lr * math.cos(math.radians(d)), hz + lr * math.sin(math.radians(d)))
                             for d in (0, 45, 90, 135, 180)], lip_r, 4, lips)


def lamp(m, x, y, z, r, col, seg=8, depth=0.04, face=-1):
    """Round lamp lens on an end face (face -1 = front, +1 = rear)."""
    m.cyl(r, depth, seg, col, M=T(x, y, z) @ R(-90 * face, 'X'))


def mirror(m, s, x, y, z, col='black', arm=0.10, arm_col='metal_dark'):
    """Wing mirror on a short arm sticking out sideways from the body side at x."""
    m.beam((s * (x - 0.01), y, z), (s * (x + arm), y, z + 0.04), 0.03, 0.03, arm_col)
    m.bevel_box(0.05, 0.05, 0.16, 0.012, col, at=(s * (x + arm + 0.02), y, z + 0.10))


def light_bar(m, y, z, length, colours, depth=0.26, base='black'):
    """Roof light bar: a dark base and a row of lens blocks (colours from the driver side +X to the kerb side -X)."""
    m.bevel_box(length, depth, 0.05, 0.015, base, at=(0, y, z), base=True)
    n = len(colours)
    seg = (length - 0.06) / n
    for i, c in enumerate(colours):
        x = (length - 0.06) / 2 - seg * (i + 0.5)
        m.bevel_box(seg - 0.02, depth - 0.06, 0.10, 0.02, c, at=(x, y, z + 0.05), base=True)


def cross(m, s, x, y, z, size, col, t=0.006):
    """Medical cross on the side plane x (two bars; the vertical one slightly prouder so they never z-fight)."""
    a, b = size / 2, size / 6
    side_plate(m, s, x, rect_yz(y - a, y + a, z - b, z + b), col, t=t)
    side_plate(m, s, x, rect_yz(y - b, y + b, z - a, z + a), col, t=t + 0.003)


def end_cross(m, s, y, x, z, size, col, t=0.006):
    a, b = size / 2, size / 6
    end_plate(m, s, y, rect_xz(x - a, x + a, z - b, z + b), col, t=t)
    end_plate(m, s, y, rect_xz(x - b, x + b, z - a, z + a), col, t=t + 0.003)


def asset(fam, name, build, notes, budget=(600, 1500)):
    if fam.wants(name):
        fam.asset(name, [(name + '_Mesh', build(), None, None)], budget=budget, notes=notes)
