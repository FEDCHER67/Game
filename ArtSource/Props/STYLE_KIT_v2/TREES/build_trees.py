"""STYLE_KIT_v2 / TREES - five species x two variants, built from templates (style bible v2, section 5).

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python ArtSource/Props/STYLE_KIT_v2/TREES/build_trees.py -- --revision 1

Every crown is a hand-set template of 3-5 smooth lobes (icosphere subdiv 2, no jitter), a single lathed column
(poplar) or 3-4 eight-sided cones (spruce). Light top / dark bottom comes from the gradient cells of the palette atlas
(crown-level gradient blended with a per-lobe one so each bump keeps a lit cap). Trunks are thick, flared at the ground
(x1.3 over 0-0.4 m, the lowest 0.4 m in wood.dark), and 2-3 branches run from a fork into the lower lobes.
A and B differ in proportion and lobe layout, not in scale (bible 4.7). One intentional asymmetry per template:
the crown is shifted 5-8 % to one side, the birch and the poplar lean, the pine trunk has one kink.
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit2 as sk                                   # noqa: E402
from mathutils import Vector                             # noqa: E402

SPECIES = {s['name']: s for s in sk.BIBLE_DATA['species']}
fam = sk.Family('SK2-TREES-001', __file__, 'TR_', budget=(1, 800),
                description='Trees v2: linden (round), birch, poplar, spruce, pine - A and B each (bible 5.1-5.2)')


# ---------------------------------------------------------------- shared parts
def trunk(m, pts, radii, col='wood', base='wood.dark', seg=8, base_h=0.4, marks=None):
    """Trunk as a tube; bands below base_h take the contact-shadow colour. marks: {(band, k): colour} (birch)."""
    zs = [p[2] for p in pts]

    def cf(band, k):
        if marks and (band, k) in marks:
            return marks[(band, k)]
        return base if zs[band + 1] <= base_h + 1e-6 else None
    m.tube(pts, radii, seg, col, cols_fn=cf, normals='soft', kind='organic', member=2 * min(radii), name='trunk')


def branch(m, p0, p1, r0, r1, col='wood', seg=6):
    m.tube([p0, p1], [r0, r1], seg, col, normals='soft', kind='organic', member=2 * min(r0, r1), name='branch')


def lobes(m, spec, grad, crown_w=0.65, ox=0.0, oy=0.0):
    """spec: [(x, y, z, r, (sx, sy, sz), flat_bottom, rot[, tilt])]. The gradient blends the crown range (weight crown_w)
    with each lobe's own range so the crown reads as one mass lit from above and every bump keeps a lit cap.
    tilt (deg, about Y) swings a hanging tassel outward."""
    spec = [tuple(l) + (0.0,) * (8 - len(l)) for l in spec]
    zlo = min(z - r * sq[2] for x, y, z, r, sq, fb, rot, tl in spec)
    zhi = max(z + r * sq[2] for x, y, z, r, sq, fb, rot, tl in spec)
    for x, y, z, r, sq, fb, rot, tl in spec:
        lo = z - r * sq[2] if fb is None else z + r * sq[2] * (fb + (-1 - fb) * 0.25)
        M = sk.T(x + ox, y + oy, z) @ sk.R(tl, 'Y') if tl else None
        m.lobe(r, grad, at=(0, 0, 0) if M else (x + ox, y + oy, z), squash=sq, flat_bottom=fb, rot=rot, M=M,
               grad=(lo, z + r * sq[2], (zlo, zhi, crown_w)), name='lobe')
    return zlo, zhi


def flare_radii(r, n_above):
    """Ground flare x1.3 at z = 0 easing to r at 0.4 m."""
    return [r * 1.3, r] + n_above


# ---------------------------------------------------------------- species templates
def linden(v):
    """'Lollipop' (v02): ONE smooth crown surface - the smooth union of a round mass, two low shoulders, a back bump
    and an off-centre dome - so the contour is one soft cloud with 3-5 bumps and no creases between tiers. Crown
    width : height ~ 1.15 : 1, dome top (no peak), underside pressed flat with a rounded rim. 500 / 320 even
    triangles (geodesic frequency 5 / 4) with smooth normals; crown shifted 5-6 % to one side (the asymmetry)."""
    m = sk.Mesh()
    if v == 'A':      # h 8.0, crown 6.0 wide x 5.2 tall, bottom 2.8, trunk 0.55; crown shifted +x 5 %
        r = 0.275
        trunk(m, [(0, 0, 0), (0, 0, 0.4), (0.02, 0, 1.6), (0.06, 0, 2.8), (0.12, 0, 4.4)],
              flare_radii(r, [0.245, 0.205, 0.13]))
        ox, H0, H1, W = 0.3, 2.8, 8.0, 6.0
        prims = [('ell', (0.0, 0.0, 5.2), (2.6, 2.5, 2.1)),          # the round mass
                 ('ell', (-1.75, -0.75, 4.35), (1.45, 1.45, 1.25)),  # left shoulder, a little forward
                 ('ell', (1.8, 0.55, 4.45), (1.45, 1.45, 1.25)),     # right shoulder, a little back
                 ('ell', (0.55, 1.6, 5.9), (1.3, 1.3, 1.15)),        # back bump
                 ('ell', (-0.45, -0.35, 6.75), (1.55, 1.5, 1.2))]    # dome top, off-centre
        m.blob(prims, 'grad.leaf', centre=(0.0, 0.0, 5.2), freq=5, k=0.55, zcut=3.35, kcut=0.9,
               fit=(-W / 2 + ox, W / 2 + ox, -W / 2 * 0.96, W / 2 * 0.96, H0, H1), grad=(H0, H1))
        branch(m, (0.04, 0, 2.2), (-1.3 + ox, -0.5, 3.6), 0.1, 0.065)
        branch(m, (0.06, 0, 2.45), (1.25 + ox, 0.55, 3.7), 0.095, 0.06)
        branch(m, (0.05, 0, 2.6), (-0.2 + ox, 0.95, 3.9), 0.085, 0.056)
    else:             # h 6.0, crown 4.2 wide x 3.6 tall, bottom 2.4, trunk 0.42; crown shifted -x 6 %
        r = 0.21
        trunk(m, [(0, 0, 0), (0, 0, 0.4), (-0.02, 0, 1.4), (-0.06, 0, 2.4), (-0.1, 0, 3.4)],
              flare_radii(r, [0.19, 0.16, 0.1]))
        ox, H0, H1, W = -0.25, 2.4, 6.0, 4.2
        prims = [('ell', (0.0, 0.0, 3.9), (1.85, 1.8, 1.5)),
                 ('ell', (-1.2, 0.45, 3.35), (1.05, 1.05, 0.95)),
                 ('ell', (1.2, -0.5, 3.4), (1.05, 1.05, 0.95)),
                 ('ell', (0.3, 0.2, 4.75), (1.2, 1.15, 0.95))]
        m.blob(prims, 'grad.leaf', centre=(0.0, 0.0, 3.9), freq=4, k=0.45, zcut=2.75, kcut=0.7,
               fit=(-W / 2 + ox, W / 2 + ox, -W / 2 * 0.96, W / 2 * 0.96, H0, H1), grad=(H0, H1))
        branch(m, (-0.04, 0, 1.9), (-0.85 + ox, 0.35, 3.0), 0.085, 0.055)
        branch(m, (-0.05, 0, 2.05), (0.8 + ox, -0.4, 3.05), 0.08, 0.055)
    return m


def birch(v):
    """Light droplet-torch: three elongated lobes merged into one tapering mass, slim tassels hanging at the lower
    edge; white trunk with ink dashes on the lower two thirds and a dark foot."""
    m = sk.Mesh()
    if v == 'A':      # h 10, crown 4.5, bottom 3.5, trunk 0.36, leans 2.6 deg
        r = 0.18
        pts = [(0, 0, 0), (0, 0, 0.3), (0.0, 0, 0.62), (0.02, 0, 0.75), (0.04, 0, 1.05), (0.05, 0, 1.18),
               (0.07, 0, 1.5), (0.08, 0, 1.6), (0.1, 0, 1.95), (0.11, 0, 2.06), (0.17, 0, 3.4), (0.3, 0, 6.0), (0.38, 0, 8.3)]
        radii = [r * 1.3, r * 1.08, r, r * 0.99, r * 0.97, r * 0.96, r * 0.94, r * 0.93, r * 0.9, r * 0.9, r * 0.82, r * 0.6, r * 0.38]
        # thin bands 2, 4, 6, 8 carry the dashes; facet k faces (k + 1) * 45 deg (k = 5 is the front, -Y)
        marks = {(2, 5): 'ink', (2, 6): 'ink', (4, 2): 'ink', (6, 7): 'ink', (6, 0): 'ink', (8, 4): 'ink', (8, 1): 'ink'}
        trunk(m, pts, radii, col='chalk', base='ink', seg=8, base_h=0.3, marks=marks)
        spec = [(0.08, 0.0, 5.98, 1.74, (1, 1, 1.36), None, 5),           # widest part of the drop
                (0.26, -0.06, 7.15, 1.42, (1, 1, 1.38), None, 23),       # each lobe up: smaller, tucked in
                (0.44, 0.04, 8.3, 1.02, (1, 1, 1.42), None, 13),
                (0.6, -0.02, 9.32, 0.56, (1, 1, 1.2), None, 40),         # tip, leaning with the trunk
                (-1.45, -0.32, 4.6, 0.46, (1, 1, 2.3), None, 31, -14),   # tassel hanging below the left edge
                (1.66, 0.36, 4.75, 0.44, (1, 1, 2.3), None, 2, 14)]      # tassel hanging below the right edge
        lobes(m, spec, 'grad.birch', crown_w=0.85)
        branch(m, (0.15, 0, 3.15), (-1.22, -0.28, 5.05), 0.065, 0.052, col='chalk')
        branch(m, (0.18, 0, 3.55), (1.44, 0.33, 5.2), 0.065, 0.052, col='chalk')
    else:             # h 8, crown 3.6, bottom 3.0, trunk 0.30, leans the other way 3 deg; one tassel
        r = 0.15
        pts = [(0, 0, 0), (0, 0, 0.3), (0, 0, 0.7), (-0.02, 0, 0.82), (-0.04, 0, 1.25), (-0.05, 0, 1.36),
               (-0.07, 0, 1.75), (-0.08, 0, 1.85), (-0.17, 0, 3.2), (-0.3, 0, 5.2), (-0.38, 0, 6.7)]
        radii = [r * 1.3, r * 1.08, r, r * 0.99, r * 0.96, r * 0.95, r * 0.93, r * 0.92, r * 0.82, r * 0.6, r * 0.4]
        marks = {(2, 6): 'ink', (2, 7): 'ink', (4, 3): 'ink', (6, 5): 'ink', (6, 1): 'ink'}
        trunk(m, pts, radii, col='chalk', base='ink', seg=8, base_h=0.3, marks=marks)
        spec = [(-0.1, 0.05, 4.95, 1.45, (1, 1, 1.34), None, 17),
                (-0.28, -0.08, 5.95, 1.18, (1, 1, 1.38), None, 3),
                (-0.45, 0.04, 6.95, 0.8, (1, 1, 1.4), None, 29),
                (1.12, 0.25, 4.05, 0.42, (1, 1, 2.3), None, 11, 15)]
        lobes(m, spec, 'grad.birch', crown_w=0.85)
        branch(m, (-0.12, 0, 2.7), (0.95, 0.22, 4.4), 0.062, 0.052, col='chalk')
    return m


def column(m, z0, height, radius, knots, lean, seg=12, flat_y=0.9):
    """Poplar crown: ONE lathed column (knots = [(s, r/R)], s = fraction of the crown height), leaning lean * s^2
    along +X like a flame, cross-section slightly flattened in Y. Closed at both ends by poles."""
    verts, faces, rings = [], [], []
    off = math.pi / seg
    for s, k in knots:
        z = z0 + s * height
        dx = lean * s * s
        if k <= 1e-9:
            rings.append([len(verts)])
            verts.append((dx, 0.0, z))
        else:
            rings.append(list(range(len(verts), len(verts) + seg)))
            verts += [(dx + radius * k * math.cos(off + sk.TAU * j / seg), radius * k * flat_y * math.sin(off + sk.TAU * j / seg), z)
                      for j in range(seg)]
    for a, c in zip(rings, rings[1:]):
        for j in range(seg):
            j1 = (j + 1) % seg
            if len(a) == 1:
                faces.append((a[0], c[j1], c[j]))
            elif len(c) == 1:
                faces.append((a[j], a[j1], c[0]))
            else:
                faces.append((a[j], a[j1], c[j1], c[j]))
    m.shell(verts, faces, 'grad.leaf', normals='smooth', grad=(z0, z0 + height), kind='organic', name='column')


def poplar(v):
    """Column-flame: one lathed body with two soft bulges and a waist, a rounded tip. v02: upright (tilt 0, bible
    5.5 - streets and yards), the trunk keeps its full 0.42 / 0.38 m diameter up to the crown (1.6 / 1.4 m)."""
    m = sk.Mesh()
    if v == 'A':      # h 12, crown 3.1, bottom 1.6, trunk 0.42 visible ~1.4 m; big bulge low, second bulge high
        r = 0.21
        trunk(m, [(0, 0, 0), (0, 0, 0.4), (0.0, 0, 1.6), (0.0, 0, 3.6)], flare_radii(r, [0.21, 0.17]))
        knots = [(0.0, 0.0), (0.04, 0.5), (0.1, 0.78), (0.18, 0.93), (0.27, 1.0), (0.37, 0.97), (0.47, 0.85),
                 (0.57, 0.89), (0.67, 0.83), (0.76, 0.67), (0.84, 0.5), (0.92, 0.31), (1.0, 0.0)]
        column(m, 1.6, 10.4, 1.58, knots, lean=0.0)
    else:             # h 9.5, crown 2.5, bottom 1.4, trunk 0.36; one broad bulge, slimmer tip, leans the other way
        r = 0.19
        trunk(m, [(0, 0, 0), (0, 0, 0.4), (0.0, 0, 1.4), (0.0, 0, 3.0)], flare_radii(r, [0.19, 0.15]))
        knots = [(0.0, 0.0), (0.045, 0.52), (0.11, 0.8), (0.21, 0.95), (0.33, 1.0), (0.45, 0.96), (0.56, 0.87),
                 (0.66, 0.79), (0.76, 0.65), (0.85, 0.47), (0.925, 0.29), (1.0, 0.0)]
        column(m, 1.4, 8.1, 1.25, knots, lean=0.0)
    return m


def spruce(v):
    """3-4 eight-sided tiers, flat shading; each tier 0.75 the width of the one below, overlapping 30 %. Every tier
    has a concave flank (steep top, flaring skirt), a short drooping lip and a concave underside; tiers turn by
    22.5 deg so the facets alternate like painted needles."""
    m = sk.Mesh()
    h, W, n, r = (11.0, 5.5, 4, 0.175) if v == 'A' else (8.0, 4.0, 3, 0.16)
    bottom = 0.6
    trunk(m, [(0, 0, 0), (0, 0, 0.4), (0, 0, bottom + 1.2)], flare_radii(r, [r * 0.85]), seg=6)
    radii = [W / 2 * 0.75 ** i for i in range(n)]
    span = sum(0.7 * ri for ri in radii[:-1]) + radii[-1]
    k = (h - bottom - 0.12) / span
    z = bottom + 0.12
    tiers = []
    for ri in radii:
        tiers.append((z, ri, k * ri))
        z += 0.7 * k * ri
    seg = 8
    for i, (zr, ri, hi) in enumerate(tiers):
        off = math.pi / seg + (math.pi / 8 if i % 2 else 0.0)

        def ring(rad, zz, off=off):
            return [(rad * math.cos(off + sk.TAU * j / seg), rad * math.sin(off + sk.TAU * j / seg), zz) for j in range(seg)]
        mid = ring(0.4 * ri, zr + 0.45 * hi)          # concave flank: 0.40 r at 55 % down from the apex (linear: 0.55 r)
        rim = ring(ri, zr)
        lip = ring(0.9 * ri, zr - 0.12)
        verts = mid + rim + lip + [(0.0, 0.0, zr + hi), (0.0, 0.0, zr + 0.22 * hi)]
        M0, R0, L0, A, U = 0, seg, 2 * seg, 3 * seg, 3 * seg + 1
        faces = []
        for j in range(seg):
            j1 = (j + 1) % seg
            faces.append((M0 + j, M0 + j1, A))                         # tip
            faces.append((R0 + j, R0 + j1, M0 + j1, M0 + j))           # flaring flank
            faces.append((L0 + j, L0 + j1, R0 + j1, R0 + j))           # drooping lip
            faces.append((L0 + j1, L0 + j, U))                         # concave underside
        m.shell(verts, faces, 'grad.conifer', normals='flat', grad=(zr - 0.12, zr + hi, (bottom, h, 0.3)),
                kind='organic', name=f'tier{i}')
    return m


def pine(v):
    """v02: a long, stout bare trunk (0.45 m at the ground, one kink; wood below, the orange wood.light only in the
    upper third) and ONE clustered crown at the top: 2-3 flattened cushions merged by a smooth union, so the crown is a
    lumpy cloud, not a stack of discs (bible 5.1, 5.6 - no pagoda, no bonsai)."""
    m = sk.Mesh()

    def bark(pts, radii, split):
        zs = [p[2] for p in pts]

        def cf(band, k):
            return 'wood.dark' if zs[band + 1] <= 0.4 + 1e-6 else ('wood' if zs[band + 1] <= split + 1e-6 else None)
        m.tube(pts, radii, 8, 'wood.light', cols_fn=cf, normals='soft', kind='organic', member=2 * min(radii), name='trunk')
    if v == 'A':      # h 13, crown 5.85 wide from 7.0 m (bible 5.1: 0.45 h, trunk visible on 55 %), trunk 0.45
        r = 0.225
        bark([(0, 0, 0), (0, 0, 0.4), (0.1, 0, 3.4), (0.36, 0.04, 6.2), (0.3, 0.06, 8.6), (0.15, 0.0, 11.0)],
             [r * 1.3, r, 0.205, 0.185, 0.16, 0.12], split=5.4)
        prims = [('ell', (-1.1, -0.3, 8.4), (1.8, 1.6, 0.9)),          # low cushion, left-front
                 ('ell', (1.25, 0.35, 9.6), (1.7, 1.55, 0.95)),        # middle cushion, right-back
                 ('ell', (-0.5, 0.45, 10.9), (1.5, 1.4, 0.9)),         # upper cushion, left-back
                 ('ell', (0.3, -0.1, 12.0), (1.5, 1.4, 1.0))]          # top dome
        m.blob(prims, 'grad.conifer', centre=(0.0, 0.0, 10.0), freq=5, k=0.4,
               fit=(-2.75, 3.1, -2.4, 2.5, 7.0, 13.0), grad=(7.0, 13.0))
        branch(m, (0.36, 0.04, 6.1), (-1.0, -0.3, 7.8), 0.12, 0.08, col='wood')
        branch(m, (0.31, 0.06, 7.4), (1.1, 0.35, 8.9), 0.11, 0.075, col='wood.light')
    else:             # h 10, crown 4.5 wide from 5.5 m, trunk 0.38; the kink goes the other way; 2 cushions + dome
        r = 0.19
        bark([(0, 0, 0), (0, 0, 0.4), (-0.1, 0, 2.6), (-0.3, -0.04, 4.8), (-0.2, -0.06, 6.6), (-0.05, 0.08, 8.4)],
             [r * 1.3, r, 0.175, 0.155, 0.135, 0.1], split=4.2)
        prims = [('ell', (0.85, 0.25, 6.6), (1.4, 1.3, 0.8)),
                 ('ell', (-0.9, -0.3, 7.6), (1.35, 1.25, 0.8)),
                 ('ell', (0.05, 0.1, 8.9), (1.35, 1.3, 0.95))]
        m.blob(prims, 'grad.conifer', centre=(0.0, 0.0, 7.6), freq=4, k=0.35,
               fit=(-2.15, 2.35, -1.95, 1.95, 5.5, 10.0), grad=(5.5, 10.0))
        branch(m, (-0.3, -0.04, 4.7), (0.65, 0.2, 6.1), 0.1, 0.07, col='wood')
        branch(m, (-0.25, -0.05, 5.5), (-0.75, -0.3, 6.9), 0.1, 0.07, col='wood.light')
    return m


# ---------------------------------------------------------------- assets + bible checks
TABLE = {   # bible 5.1: height, crown bottom, trunk diameter at the ground (above the flare), crown width factor
    ('round', 'A'): (8.0, 2.8, 0.55), ('round', 'B'): (6.0, 2.4, 0.42),
    ('birch', 'A'): (10.0, 3.5, 0.36), ('birch', 'B'): (8.0, 3.0, 0.30),
    ('poplar', 'A'): (12.0, 1.6, 0.42), ('poplar', 'B'): (9.5, 1.4, 0.36),
    ('spruce', 'A'): (11.0, 0.6, 0.35), ('spruce', 'B'): (8.0, 0.6, 0.32),
    ('pine', 'A'): (13.0, 7.0, 0.45), ('pine', 'B'): (10.0, 5.5, 0.38),
}
BUILD = {'round': linden, 'birch': birch, 'poplar': poplar, 'spruce': spruce, 'pine': pine}
MODEL = {'round': 'Round', 'birch': 'Birch', 'poplar': 'Poplar', 'spruce': 'Spruce', 'pine': 'Pine'}
BUDGET_B = {'round': 550}                                 # bible 4: linden B <= 550, everything else as A


def crown_stats(mesh):
    pts = [Vector(mesh.verts[i]) for sid, sh in enumerate(mesh.shells) if sh['name'] in ('lobe', 'column', 'crown') or sh['name'].startswith('tier')
           for i in range(sh['v0'], sh['v1'])]
    w = max(max(p.x for p in pts) - min(p.x for p in pts), max(p.y for p in pts) - min(p.y for p in pts))
    return w, min(p.z for p in pts), max(p.z for p in pts)


row = 0
for sp in ('round', 'birch', 'poplar', 'spruce', 'pine'):
    for v in ('A', 'B'):
        h, bottom, trunk_d = TABLE[(sp, v)]
        js = SPECIES[sp]
        mesh = BUILD[sp](v)
        w, cb, top = crown_stats(mesh)
        wk = js['crown_width_k']
        branch_d = [sh['member'] for sh in mesh.shells if sh['name'] == 'branch']
        checks = {
            'branches_ge_0.10_m': all(d >= 0.1 - 1e-6 for d in branch_d),
            'height_matches_bible_5_1': abs(top - h) <= 0.03 * h,
            'height_in_species_range': js['h_min'] - 1e-6 <= top <= js['h_max'] + 1e-6,
            'crown_width_within_15pct_of_k_h': abs(w - wk * h) <= 0.15 * wk * h,
            'crown_bottom_ge_bible_min': cb >= js['crown_base_min'] - 0.05,
            'crown_bottom_matches_table_0_15m': abs(cb - bottom) <= 0.15,
        }
        crowns = [sh for sh in mesh.shells if sh['name'] == 'crown']
        if crowns:                       # v02 smooth-crown rule: one closed surface, even triangles, 300-550 of them
            ct = sum(1 for s_ in mesh.fshell if mesh.shells[s_]['name'] == 'crown')
            checks['smooth_crown_one_surface'] = len(crowns) == 1
            checks['smooth_crown_tris_300_550'] = 300 <= ct <= 550
        tmax = BUDGET_B.get(sp, js['tris_max']) if v == 'B' else js['tris_max']
        fam.add_asset(f'TR_{MODEL[sp]}_{v}', (lambda sp=sp, v=v: BUILD[sp](v)), budget=(1, tmax), row=row,
                      max_swatches=3, species=sp, variant=v, plan_species=js['plan_sp'],
                      bible_table={'height_m': h, 'crown_bottom_m': bottom, 'trunk_d_m': trunk_d, 'crown_width_m': round(wk * h, 2)},
                      measured={'height_m': round(top, 3), 'crown_width_m': round(w, 3), 'crown_bottom_m': round(cb, 3)},
                      extra_checks=checks)

# extra bible checks are merged into each asset's checks after validation
_orig = fam._validate_asset


def _validate(a):
    r = _orig(a)
    r['checks'].update(a['meta'].get('extra_checks', {}))
    r['all_checks_passed'] = all(r['checks'].values())
    return r


fam._validate_asset = _validate
for a in fam.assets:
    a['meta']['extra_checks'] = {k: bool(v) for k, v in a['meta']['extra_checks'].items()}
report = fam.finish(lineup_gap=2.5, extra_notes=[
    'Heights are the A/B values of bible 5.1; in Unity TerrainBaker scales each tree to its plan height (5.3), so the model '
    'height only fixes proportions.',
    'Gradients: grad.leaf (linden, poplar), grad.birch (one step lighter), grad.conifer (spruce, pine).',
    'LOD1 (bible 5.2.7) is not part of v01/v02.',
    'v02: linden and pine crowns are ONE smooth surface (smooth union of template ellipsoids projected onto a geodesic '
    'sphere, 500 / 320 even triangles, smooth normals) instead of intersecting lobes; poplars stand upright; the pine '
    'trunk is stout and its crown clusters at the top.',
    'v02b (2026-10-07, critique of the trial frame): geodesic vertices keyed by exact barycentric weights (the freq-5 '
    'crowns of v02 test builds had 32 open edges); pine crown bottom back to bible 5.1 (7.0 / 5.5 m, trunk visible on '
    '55 %) with 3 cushions + a dome clustered in the top 45 %.'])


# ---------------------------------------------------------------- previews
def facade_proxy(x, y, w=12.0, d=8.0, floors=3):
    """A 3-storey old-town block for scale only (not exported): eaves at 0.5 + 3 x 3.2 = 10.1 m."""
    m = sk.Mesh()
    eave = 0.5 + floors * 3.2
    m.box(w, d, eave, 'cream', base=True, cols=[None, 'grey', None, None, None, None])
    m.prism([(-d / 2 - 0.5, eave), (0, eave + d / 2 * math.tan(math.radians(32))), (d / 2 + 0.5, eave)], w + 1.0, 'terracotta',
            cap='cream', side=['terracotta', 'terracotta', 'chalk'], M=sk.R(90, 'Z'))
    return fam.proxy('Proxy_Facade_NotExported', m, x, y)


names = [f'TR_{MODEL[sp]}_{v}' for sp in ('round', 'birch', 'poplar', 'spruce', 'pine') for v in ('A', 'B')]
if not fam.args.no_render:
    # 01: the species ruler next to a 1.75 m person and a 3-storey facade (bible 5.7)
    x = 0.0
    lineup = []
    for n in names:
        r = report['assets'][n]
        x += -r['bounds_min'][0]
        lineup += fam.place(n, x, 0.0)
        x += r['bounds_max'][0] + 1.2
    proxy = facade_proxy(x + 7.0, 2.0)
    fam.showcase(True)
    fam.shot('01_species_ruler.png', lineup + [proxy], az=12, el=10, res=(2400, 1000), lens=60, ground='meadow', person=(-1.5, -2.5))
    fam.shot('02_species_ruler_high.png', lineup + [proxy], az=28, el=24, res=(2400, 1100), lens=55, ground='meadow', person=(-1.5, -2.5))
    fam.silhouette('03_silhouettes.png', lineup, res=(2600, 800))
    fam.clear_showcase()
    # 04: pairs, closer
    for sp in ('round', 'birch', 'poplar', 'spruce', 'pine'):
        a = fam.place(f'TR_{MODEL[sp]}_A', -3.6 if sp != 'spruce' else -3.4, 0.0)
        b = fam.place(f'TR_{MODEL[sp]}_B', 3.6 if sp != 'spruce' else 3.4, 0.0, rot=30)
        fam.showcase(True)
        fam.shot(f'04_{sp}_AB.png', a + b, az=30, el=14, res=(1600, 1200), lens=50, ground='meadow', person=(0.0, -2.0))
        fam.clear_showcase()
    # 05: a street row: one species, one variant, equal spacing, along a paving strip in front of a facade (bible 5.5)
    row_objs = []
    for i in range(6):
        row_objs += fam.place('TR_Round_A', i * 9.0, 0.0, rot=(i * 47) % 360)
    proxy = facade_proxy(22.5, 11.0, w=52.0, d=10.0)
    fam.showcase(True)
    fam.shot('05_street_row_lindens.png', row_objs + [proxy], az=-28, el=12, res=(2000, 1100), lens=40, ground='lawn', person=(18.0, -3.0))
    fam.clear_showcase()
    # 06: forest edge (spruce dominant, pine every third, birch at the edge - bible 5.4)
    layout = [('TR_Spruce_A', 0, 0, 0), ('TR_Spruce_B', 5.5, -2.0, 20), ('TR_Spruce_A', 10.5, 1.5, 45), ('TR_Pine_A', 15.5, -1.0, 10),
              ('TR_Spruce_B', 20.0, 2.0, 70), ('TR_Spruce_A', 24.5, -1.5, 15), ('TR_Pine_B', 29.0, 1.0, 50),
              ('TR_Spruce_A', 3.0, 7.0, 33), ('TR_Spruce_B', 13.0, 7.5, 5), ('TR_Spruce_A', 22.0, 8.0, 60),
              ('TR_Birch_A', -5.0, -5.0, 0), ('TR_Birch_B', 33.5, -4.5, 25)]
    fobjs = []
    for n, fx, fy, rot in layout:
        fobjs += fam.place(n, fx, fy, rot=rot)
    fam.showcase(True)
    fam.shot('06_forest_edge.png', fobjs, az=20, el=16, res=(2000, 1100), lens=40, ground='lawn', person=(-2.0, -7.0))
    fam.clear_showcase()
    fam.showcase(False)
print('done')
