"""SK1-TREES-001: style-bible trees (section 5) - six species x two size variants, hand-placed lobes, no jitter.

Linden (round deciduous, covers oak), Birch, Poplar, Pine, Spruce, Apple. A = large, B = small (different proportions,
not a scaled copy). One closed multi-shell mesh per tree: flared trunk (lathe), 2-4 branches that cross the crown
contour from below, 3-4 smooth icosphere lobes (subdiv 2, jitter 0) coloured by a vertical gradient of the palette
(light top / dark underside), conifers as flat pads / cones. Heights follow section 5.4 (street trees <= 8 m).

Run (repo root):
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python ArtSource/Props/STYLE_KIT_v1/TREES/build_trees.py -- --revision 1
Flags: --force, --no-render, --samples N, --cpu, --out DIR
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit as sk                      # noqa: E402
from stylekit import Mesh, T, shear_z      # noqa: E402
from mathutils import Vector               # noqa: E402

TAU = math.tau
fam = sk.Family('SK1-TREES-001', __file__, prefix='TR_', budget=(100, 1200),
                description='Style-bible trees: linden, birch, poplar, pine, spruce, apple; A = large, B = small. Smooth gradient '
                            'lobes without jitter, thick visible trunks, branches entering the crown from below, flat faceted trunks.')


# ------------------------------------------------------------------ helpers
def axis(lean):
    return lambda z: Vector((lean[0] * z, lean[1] * z, z))


def trunk(m, h, r_base, r_top, lean=(0.0, 0.0), col='trunk', flare=1.35, seg=8, colfn=None, profile=None):
    """Flared, tapering trunk; the shear keeps the base ring flat on the ground. Returns the top point."""
    prof = profile or [(r_base * flare, 0.0), (r_base * 1.1, 0.25), (r_base, 0.6), (r_base * 0.82, h * 0.5), (r_top, h)]
    m.lathe(prof, seg, col, M=shear_z(*lean), offset=math.pi / seg, colfn=colfn, member=2 * r_top)
    return axis(lean)(h)


def lobe(m, c, r, grad, squash=(1, 1, 1), flat_bottom=None, rng=None):
    c = Vector(c)
    z0, z1 = c.z - r * squash[2], c.z + r * squash[2]
    m.blob(r, grad, at=tuple(c), squash=squash, flat_bottom=flat_bottom, grad=rng or (z0, z1))
    return c


def branch(m, p0, p1, r0, r1=0.06, col='trunk'):
    m.bar(p0, p1, r0, col, seg=6, r1=max(r1, 0.06))


def ao_trunk(x, y, z):
    """Contact darkening of the lowest 0.3 m (vertex colour only), section 3.1."""
    return 0.9 + 0.1 * min(z / 0.3, 1.0)


# ------------------------------------------------------------------ species
def linden(h, r_base, crown_from, R, lean, top_side, sq=0.8):
    """Lollipop: wide main lobe, smaller top lobe pushed to one side, dark underside lobe, 3 branches from below."""
    m = Mesh()
    ax = axis(lean)
    zc = crown_from + R * sq * 0.72
    c_main = ax(zc)
    R2, R3 = R * 0.66, R * 0.62
    c_top = Vector((c_main.x + top_side[0] * R, c_main.y + top_side[1] * R, zc + R * sq * 0.66))
    c_bot = Vector((c_main.x - top_side[0] * R * 0.8, c_main.y - top_side[1] * R * 0.6, zc - R * sq * 0.46))
    rng = (c_bot.z - R3 * 0.72, c_top.z + R2 * 0.9)                        # one gradient range for the whole crown
    trunk(m, zc, r_base, r_base * 0.55, lean)
    lobe(m, c_main, R, 'grad_crown', squash=(1, 1, sq), rng=rng)
    lobe(m, c_top, R2, 'grad_crown', squash=(1, 1, 0.9), rng=rng)
    lobe(m, c_bot, R3, 'grad_crown', squash=(1, 1, 0.72), rng=rng)
    fork = ax(crown_from - 0.35)
    for i, a in enumerate((0.3, 2.4, 4.4)):
        tgt = Vector((c_main.x + math.cos(a) * R * 0.55, c_main.y + math.sin(a) * R * 0.55, zc - R * sq * 0.1 + i * 0.15))
        branch(m, fork, tgt, r_base * 0.36, 0.07)
    return m, {'height_m': round(rng[1], 2), 'crown_from_m': crown_from, 'crown_width_m': round(2 * R, 2),
               'trunk_diameter_m': round(2 * r_base, 2)}


def birch(h, r_base, crown_from, lean, marks, top_z=None):
    """Slim white trunk with deliberate dark dashes, two tall lobes + a small top, airy light gradient."""
    m = Mesh()
    ax = axis(lean)
    ht = top_z or h * 0.9
    stations = [0.0, 0.28]                                   # dark base band 0.28 m
    kinds = ['base']
    for z in marks:
        stations += [z, z + 0.12]
        kinds += ['white', 'mark']
    stations.append(ht)
    kinds.append('white')
    r_of = lambda z: r_base * 1.3 if z <= 0 else max(r_base * (1 - z / ht) ** 0.75 + 0.05, 0.07)
    prof = [(r_of(z), z) for z in stations]
    mark_k = {i: (i * 3) % 8 for i in range(len(stations))}

    def colfn(b, k):
        kind = kinds[min(b, len(kinds) - 1)]
        if kind == 'base':
            return 'trunk_mark'
        if kind == 'mark' and (k == mark_k[b] or k == (mark_k[b] + 1) % 8):
            return 'trunk_mark'
        return 'trunk_birch'

    trunk(m, ht, r_base, 0.07, lean, col='trunk_birch', colfn=colfn, profile=prof)
    R1 = (ht - crown_from) * 0.32
    c1 = ax(crown_from + R1 * 1.25) + Vector((0.25 * R1, 0.0, 0))
    c2 = ax(crown_from + R1 * 2.75) + Vector((-0.35 * R1, 0.3 * R1, 0))
    c3 = ax(ht - R1 * 0.2) + Vector((0.1 * R1, -0.1 * R1, 0))
    rng = (c1.z - R1 * 1.35, c3.z + R1 * 0.72)
    lobe(m, c1, R1, 'grad_crown_light', squash=(0.9, 0.9, 1.4), rng=rng)
    lobe(m, c2, R1 * 0.92, 'grad_crown_light', squash=(0.85, 0.85, 1.4), rng=rng)
    lobe(m, c3, R1 * 0.62, 'grad_crown_light', squash=(0.9, 0.9, 1.2), rng=rng)
    for src, dst in ((ax(crown_from + 0.2), c1 + Vector((0, 0, -R1 * 0.3))), (ax(crown_from + R1 * 1.9), c2 + Vector((0, 0, -R1 * 0.4)))):
        branch(m, src, dst, r_base * 0.45, 0.06, col='trunk_birch')
    return m, {'height_m': round(rng[1], 2), 'crown_from_m': crown_from, 'crown_width_m': round(2 * R1 * 0.9 + 0.6 * R1, 2),
               'trunk_diameter_m': round(2 * r_base, 2)}


def poplar(h, r_base, R, lean):
    """Column with a pointed top: three stacked tall lobes (r 1.0 / 0.9 / 0.6), trunk visible ~10 %."""
    m = Mesh()
    ax = axis(lean)
    z0 = h * 0.1
    trunk(m, h * 0.92, r_base, r_base * 0.35, lean)
    sq = 1.6
    c1 = ax(z0 + R * sq * 0.78)
    c2 = ax(c1.z + R * sq * 1.35)
    c3 = ax(c2.z + R * sq * 1.15)
    rng = (z0, c3.z + R * 0.6 * 2.0)
    lobe(m, c1, R, 'grad_crown', squash=(1, 1, sq), rng=rng)
    lobe(m, c2, R * 0.9, 'grad_crown', squash=(1, 1, sq), rng=rng)
    lobe(m, c3, R * 0.6, 'grad_crown', squash=(1, 1, 2.0), rng=rng)
    return m, {'height_m': round(rng[1], 2), 'crown_from_m': z0, 'crown_width_m': round(2 * R, 2), 'trunk_diameter_m': round(2 * r_base, 2)}


def pine(h, r_base, crown_from, pads, dome_r, lean):
    """Bare trunk (45 %), 2-3 flat pads on upward branches, dome; every pad has its own light-top / dark-under gradient."""
    m = Mesh()
    ax = axis(lean)
    top = trunk(m, h * 0.93, r_base, r_base * 0.3, lean)
    for i, (z, r, dx, dy) in enumerate(pads):
        c = ax(z) + Vector((dx, dy, 0))
        lobe(m, c, r, 'grad_pine', squash=(1, 0.92, 0.5), flat_bottom=-0.35)
        branch(m, ax(z - r * 0.55), c + Vector((0, 0, -r * 0.1)), r_base * 0.42, 0.07)
    c_dome = ax(h * 0.93) + Vector((0.0, 0.0, dome_r * 0.1))
    lobe(m, c_dome, dome_r, 'grad_pine', squash=(1, 1, 0.75), flat_bottom=-0.3)
    return m, {'height_m': round(c_dome.z + dome_r * 0.75, 2), 'crown_from_m': crown_from, 'crown_width_m': round(2 * max(p[1] for p in pads), 2),
               'trunk_diameter_m': round(2 * r_base, 2)}


def spruce(h, r_base, cones, lean):
    """Three faceted cones stacked with 30 % overlap, spire top; gradient dark bottom -> light top over the whole tree."""
    m = Mesh()
    ax = axis(lean)
    z_first = cones[0][0]
    trunk(m, z_first + 0.6, r_base, r_base * 0.7, lean)
    top = cones[-1][0] + cones[-1][2]
    rng = (z_first, top)
    for z, r, ch in cones:
        c = ax(z)
        m.cone(r, ch, 8, 'grad_pine', at=tuple(c), offset=math.pi / 8, smooth=False, grad=rng)
    return m, {'height_m': round(top, 2), 'crown_from_m': z_first, 'crown_width_m': round(2 * cones[0][1], 2), 'trunk_diameter_m': round(2 * r_base, 2)}


def apple(h, r_base, trunk_h, R, limbs, n_fruit, bend):
    """Low and wide: crooked trunk (3-point tube), 3 limbs, two lobes side by side + one on top, red fruit on the surface."""
    m = Mesh()
    pts = [(0, 0, 0), (0, 0, trunk_h * 0.45), (bend[0], bend[1], trunk_h)]
    m.tube(pts, [r_base * 1.3, r_base, r_base * 0.8], 8, 'trunk')
    top = Vector(pts[-1])
    centres = [Vector((top.x + dx, top.y + dy, z)) for dx, dy, z in limbs]
    rng = (min(c.z for c in centres) - R * 0.9, max(c.z for c in centres) + R * 0.88)
    for i, c in enumerate(centres):
        r = R * (1.0, 0.92, 0.86)[i % 3]
        lobe(m, c, r, 'grad_crown_dark', squash=(1, 1, 0.86), rng=rng)
        branch(m, top - Vector((0, 0, trunk_h * 0.25)), c - Vector((0, 0, r * 0.25)), r_base * 0.6, 0.07)
    # fruit: deterministic spiral over the outer-lower surface of the lobes, so they read from street level
    for i in range(n_fruit):
        c = centres[i % len(centres)]
        r = R * (1.0, 0.92, 0.86)[i % 3]
        a = 0.9 + i * 2.2
        el = (-0.45, -0.15, 0.1, -0.3)[i % 4]
        d = Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el) * 0.86))
        p = c + d * r * 0.98
        m.blob(0.17, 'fruit_red', at=tuple(p), subdiv=1, smooth=True)
    return m, {'height_m': round(rng[1], 2), 'crown_from_m': trunk_h, 'crown_width_m': round(2 * R + 2 * max(abs(l[0]) for l in limbs), 2),
               'trunk_diameter_m': round(2 * r_base, 2)}


# ------------------------------------------------------------------ specs (section 5.1: heights A / B)
SPECS = [
    ('TR_Linden_A', 8.0, lambda: linden(7.0, 0.32, 2.3, 2.75, (0.02, 0.0), (0.18, 0.06)),
     'Linden A ~7 m: lollipop crown 5.5 m wide, trunk visible 2.3 m (33 %), top lobe pushed right, dark underside. Old-town square rows.'),
    ('TR_Linden_B', 8.0, lambda: linden(5.0, 0.24, 1.6, 2.0, (-0.03, 0.01), (-0.16, 0.1), sq=0.88),
     'Linden B ~5 m: rounder and squatter, top lobe to the left. Yards, old-town side streets.'),
    ('TR_Birch_A', 13.0, lambda: birch(9.0, 0.21, 3.0, (0.045, 0.01), (0.9, 1.7, 2.5, 3.6, 4.6, 5.7, 6.9)),
     'Birch A ~9 m: white trunk with 7 two-face dashes and a dark foot, two tall airy lobes + a small top, 2 white branches.'),
    ('TR_Birch_B', 8.0, lambda: birch(6.5, 0.18, 2.2, (-0.06, 0.02), (0.8, 1.5, 2.3, 3.2, 4.2)),
     'Birch B ~6.5 m: young, leaning the other way, 5 dashes.'),
    ('TR_Poplar_A', 13.0, lambda: poplar(11.0, 0.2, 1.4, (0.0, 0.0)),
     'Poplar A ~11 m: column of three tall lobes, pointed top, trunk visible 1.1 m. Avenue rows, industrial zone.'),
    ('TR_Poplar_B', 13.0, lambda: poplar(8.0, 0.17, 1.15, (0.01, 0.0)),
     'Poplar B ~8 m: plumper column.'),
    ('TR_Pine_A', 13.0, lambda: pine(12.0, 0.26, 5.4, [(6.2, 3.0, 0.7, 0.2), (8.4, 2.4, -0.9, -0.3), (10.2, 1.8, 0.5, 0.4)], 1.35, (0.02, 0.01)),
     'Scots pine A ~12 m: bare trunk 5.4 m, three flat pads stepping up on alternate sides, dome. Forest dominant.'),
    ('TR_Pine_B', 13.0, lambda: pine(9.0, 0.22, 4.0, [(4.7, 2.5, 0.6, 0.0), (6.9, 1.9, -0.7, 0.3)], 1.25, (0.04, 0.0)),
     'Scots pine B ~9 m: two pads + dome, bigger dome relative to height.'),
    ('TR_Spruce_A', 13.0, lambda: spruce(10.0, 0.2, [(0.8, 2.0, 3.6), (3.3, 1.6, 3.8), (6.1, 1.15, 3.9)], (0.0, 0.0)),
     'Spruce A ~10 m: three faceted cones, 30 % overlap, spire. Forest by the swamp, 2-3 at the church.'),
    ('TR_Spruce_B', 13.0, lambda: spruce(7.0, 0.16, [(0.6, 1.5, 2.6), (2.4, 1.2, 2.7), (4.3, 0.85, 2.7)], (0.0, 0.0)),
     'Spruce B ~7 m.'),
    ('TR_Apple_A', 8.0, lambda: apple(4.5, 0.15, 1.35, 1.35, [(-1.05, 0.15, 2.65), (1.1, -0.2, 2.55), (0.15, 0.3, 3.35)], 10, (0.22, 0.1)),
     'Apple A ~4.5 m: crooked trunk, 3 limbs, two lobes side by side + one on top, 10 red apples on the outer surface. Hamlet yards.'),
    ('TR_Apple_B', 8.0, lambda: apple(3.2, 0.15, 1.0, 1.0, [(-0.8, 0.1, 1.95), (0.85, -0.15, 1.85), (0.05, 0.25, 2.5)], 8, (-0.15, 0.12)),
     'Apple B ~3.2 m: 8 apples.'),
]

for name, h_limit, build, notes in SPECS:
    mesh, meta = build()
    ob = fam.make_object(name, mesh, ao=ao_trunk)
    cf = 0.5 if 'Pine' in name else 0.35                       # pines: bare trunk 45 % by section 5.1
    checks = {f'height_le_{h_limit:g}_m': meta['height_m'] <= h_limit + 1e-6,
              f'crown_from_le_{cf}_h': meta['crown_from_m'] <= cf * meta['height_m'] + 1e-6,
              'trunk_diameter_ge_0.3_m': meta['trunk_diameter_m'] >= 0.3 - 1e-6}
    fam.add_asset(name, [ob], notes=notes, checks=checks, row=0 if name.endswith('_B') else 1, species=name.split('_')[1],
                  min_member_m=round(mesh.min_member, 3), **meta)

fam.finish(lineup_gap=2.5, row_gap=5.0)

if not fam.args.no_render:
    allobjs = fam.objs_of([s[0] for s in SPECS])
    fam.shot('01_lineup_three_quarter.png', allobjs, az=30, el=16, res=(2200, 1000), lens=50, person=(-2.5, 0.0))
    fam.shot('02_lineup_front.png', allobjs, az=0, el=5, res=(2200, 900), lens=50, ortho=True, person=(-2.5, 0.0))
    fam.silhouette('03_silhouettes.png', allobjs, az=0, res=(2200, 900))
    for sp in ('Linden', 'Birch', 'Poplar', 'Pine', 'Spruce', 'Apple'):
        pair = fam.objs_of([f'TR_{sp}_A', f'TR_{sp}_B'])
        xa = pair[0].location.x
        fam.shot(f'04_{sp.lower()}_AB.png', pair, az=35, el=14, res=(1400, 1100), lens=50, person=(xa - 4.5, -2.0))
    street = [s[0] for s in SPECS if s[0].endswith('_A') and 'Pine' not in s[0]]
    objs = fam.objs_of(street)
    fam.shot('05_street_view.png', objs, az=-10, el=4, res=(2200, 900), lens=35, person=(objs[0].location.x - 3.0, -4.0), eye=1.6)
