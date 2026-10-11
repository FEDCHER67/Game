"""SK1-BUSHES-001: style-bible bushes (section 6.1) - three lobes each, flat bottoms, gradient colour, no jitter.

BU_Bush_Round  1.1 m hemisphere: two lower lobes side by side + one on top, light top / bush-green underside
BU_Bush_Wild   1.4 m loose, deliberately asymmetric: three dark lobes of different size, one dry (field_dry) lobe,
               two thick dead twigs (0.08 m)
BU_Bush_Lilac  2.0 m: three heads on three thick stems (0.08 m) + six blossom panicles

Run (repo root):
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python ArtSource/Props/STYLE_KIT_v1/BUSHES/build_bushes.py -- --revision 1
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit as sk                      # noqa: E402
from stylekit import Mesh                  # noqa: E402
from mathutils import Vector               # noqa: E402

fam = sk.Family('SK1-BUSHES-001', __file__, prefix='BU_', budget=(100, 400),
                description='Style-bible bushes: round, wild, lilac. Three smooth lobes per bush, flat bottoms, vertical palette '
                            'gradient, one deliberate asymmetry each, no random jitter.')


def ground(m):
    mz = min(v[2] for v in m.verts)
    m.verts = [(x, y, z - mz) for x, y, z in m.verts]
    m.fgrad = [None if g is None else (g[0] - mz, g[1] - mz) for g in m.fgrad]


def lobe(m, c, r, grad, rng, squash=(1, 1, 1), flat_bottom=-0.55):
    m.blob(r, grad, at=c, squash=squash, flat_bottom=flat_bottom, grad=rng)


def bush_round():
    m = Mesh()
    rng = (0.0, 1.12)
    lobe(m, (-0.4, 0.0, 0.5), 0.6, 'grad_bush', rng, squash=(1, 1, 0.85))
    lobe(m, (0.42, -0.05, 0.5), 0.6, 'grad_bush', rng, squash=(1, 1, 0.85))
    lobe(m, (0.03, 0.1, 0.72), 0.5, 'grad_bush', rng, squash=(1, 1, 0.8))
    ground(m)
    return m, {'height_m': 1.12}


def bush_wild():
    m = Mesh()
    rng = (0.0, 1.4)
    lobe(m, (-0.45, 0.1, 0.42), 0.5, 'grad_bush_dark', rng, squash=(1, 1, 0.9))
    lobe(m, (0.2, -0.1, 0.62), 0.7, 'grad_bush_dark', rng, squash=(1, 0.95, 0.95))
    lobe(m, (0.55, 0.45, 0.38), 0.45, 'grad_bush_dark', rng, squash=(1, 1, 0.9))
    lobe(m, (-0.15, -0.55, 0.36), 0.38, 'field_dry', rng, squash=(1, 1, 0.85))           # the one dry lobe (asymmetry)
    # two thick dead twigs
    m.bar((0.1, -0.05, 0.9), (0.75, -0.35, 1.72), 0.045, 'trunk', seg=5, r1=0.04)
    m.bar((-0.3, 0.2, 0.75), (-0.95, 0.55, 1.35), 0.045, 'trunk', seg=5, r1=0.04)
    ground(m)
    return m, {'height_m': 1.72}


def bush_lilac():
    m = Mesh()
    heads = [((-0.5, 0.1, 1.25), 0.55), ((0.45, -0.2, 1.35), 0.55), ((0.05, 0.45, 1.6), 0.5)]
    rng = (0.6, 2.05)
    for (c, r) in heads:
        cx, cy, cz = c
        m.bar((cx * 0.2, cy * 0.2, 0.0), (cx, cy, cz - r * 0.2), 0.045, 'trunk', seg=5, r1=0.04)
        m.blob(r, 'grad_crown_dark', at=c, squash=(1, 1, 0.95), grad=rng)
    # six blossom panicles: tall ovals standing out of the tops of the heads
    for i, (dx, dy, hi) in enumerate(((0.0, 0.0, 0), (0.3, 0.15, 0), (0.0, 0.0, 1), (-0.3, 0.1, 1), (0.0, 0.0, 2), (0.25, -0.2, 2))):
        c, r = heads[hi]
        p = (c[0] + dx, c[1] + dy, c[2] + r * 0.8 + 0.05)
        m.blob(0.18, 'blossom', at=p, subdiv=1, squash=(0.8, 0.8, 1.6))
    return m, {'height_m': 2.05}


SPECS = [
    ('BU_Bush_Round', bush_round, (100, 400), 3, 'Round bush 1.1 m: two lobes side by side + one on top, light top / bush-green underside, flat bottom. Yards, parks.'),
    ('BU_Bush_Wild', bush_wild, (100, 400), 4, 'Wild bush 1.4 m: three dark lobes of different sizes, one dry field_dry lobe, two thick dead twigs. Wastelands, village edges.'),
    ('BU_Bush_Lilac', bush_lilac, (100, 450), 3, 'Lilac 2.0 m: three heads on three 0.08 m stems, six blossom panicles. Soviet yards, old town.'),
]

for name, build, budget, maxc, notes in SPECS:
    mesh, meta = build()
    ob = fam.make_object(name, mesh)
    fam.add_asset(name, [ob], budget=budget, notes=notes, max_colours=maxc,
                  checks={'height_le_2.1_m': meta['height_m'] <= 2.1}, min_member_m=round(mesh.min_member, 3) if mesh.min_member else None, **meta)

fam.finish(lineup_gap=1.2)

if not fam.args.no_render:
    allobjs = fam.objs_of([s[0] for s in SPECS])
    fam.shot('01_lineup_three_quarter.png', allobjs, az=35, el=14, res=(1800, 900), lens=50, person=(-1.3, 0.3))
    fam.shot('02_lineup_front.png', allobjs, az=0, el=3, res=(1800, 800), lens=50, ortho=True, person=(-1.3, 0.3))
    fam.silhouette('03_silhouettes.png', allobjs, az=0, res=(1800, 800))
    fam.shot('04_street_view.png', allobjs, az=-20, el=3, res=(1800, 900), lens=35, person=(-1.3, -1.5), eye=1.5)
