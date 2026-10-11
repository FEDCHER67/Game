"""SK1-GRASS-001: style-bible grass (section 6.2) - tufts and flower patches as closed pyramids.

GR_Tuft_A/B/C     four blades (pyramids 0.08 x 0.03 base, 0.3-0.4 m) on a fixed fan, 24 triangles each; A upright,
                  B blown to one side, C low and wide. Colour = grass gradient (leaf_mid tips, grass_shade feet).
GR_Flowers_Yellow / GR_Flowers_White   three stalks with octahedron heads of ONE colour + three leaf blades, 60 tris.

Run (repo root):
  "/c/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python ArtSource/Props/STYLE_KIT_v1/GRASS/build_grass.py -- --revision 1
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit as sk                      # noqa: E402
from stylekit import Mesh                  # noqa: E402

TAU = math.tau
fam = sk.Family('SK1-GRASS-001', __file__, prefix='GR_', budget=(12, 60),
                description='Style-bible grass tufts (24 tris) and flower patches (60 tris): closed pyramids, one colour per patch, '
                            'placed by PropScatterer in clusters of 5-9 inside a 2 m circle.')


def tuft(blades, rng_top):
    """blades: (foot x, foot y, tip x, tip y, height, width)."""
    m = Mesh()
    for fx, fy, tx, ty, h, w in blades:
        m.blade((fx, fy, 0.0), (tx, ty, h), w, 0.03, 'grad_grass', grad=(0.0, rng_top))
    return m


def flowers(col):
    m = Mesh()
    stalks = ((-0.12, 0.05, -0.2, 0.1, 0.30), (0.1, -0.08, 0.15, -0.16, 0.34), (0.03, 0.14, 0.0, 0.26, 0.27))
    for fx, fy, tx, ty, h in stalks:
        m.blade((fx, fy, 0.0), (tx, ty, h), 0.045, 0.035, 'grad_grass', grad=(0.0, 0.36))
        m.octa(0.075, col, at=(tx, ty, h + 0.02), squash=(1, 1, 0.75))
    for fx, fy, tx, ty, h, w in ((0.16, 0.1, 0.3, 0.2, 0.2, 0.08), (-0.14, -0.12, -0.3, -0.2, 0.18, 0.08), (0.0, -0.18, -0.02, -0.34, 0.16, 0.07)):
        m.blade((fx, fy, 0.0), (tx, ty, h), w, 0.03, 'grad_grass', grad=(0.0, 0.36))
    return m


SPECS = [
    ('GR_Tuft_A', lambda: tuft(((0.0, 0.0, 0.05, 0.04, 0.40, 0.08), (-0.08, 0.03, -0.22, 0.1, 0.30, 0.08),
                                (0.07, -0.05, 0.2, -0.17, 0.33, 0.08), (0.0, 0.08, -0.05, 0.25, 0.28, 0.08)), 0.40), (12, 24), 1,
     'Tuft A 0.4 m: upright fan of four blades.'),
    ('GR_Tuft_B', lambda: tuft(((0.0, 0.0, 0.22, 0.05, 0.34, 0.08), (-0.08, 0.04, 0.12, 0.14, 0.28, 0.08),
                                (0.05, -0.06, 0.3, -0.1, 0.30, 0.08), (-0.04, -0.04, 0.16, -0.22, 0.22, 0.08)), 0.34), (12, 24), 1,
     'Tuft B 0.34 m: all blades blown to +X (wind), use rotated.'),
    ('GR_Tuft_C', lambda: tuft(((0.0, 0.0, -0.26, 0.05, 0.22, 0.09), (0.02, 0.02, 0.24, 0.12, 0.24, 0.09),
                                (-0.02, -0.03, 0.05, -0.3, 0.2, 0.09), (0.03, 0.04, 0.0, 0.28, 0.21, 0.09)), 0.24), (12, 24), 1,
     'Tuft C 0.24 m: low, wide, flat star.'),
    ('GR_Flowers_Yellow', lambda: flowers('flower_yellow'), (30, 60), 2, 'Flower patch: three yellow heads + three leaf blades. Meadow, hamlet, fields.'),
    ('GR_Flowers_White', lambda: flowers('flower_white'), (30, 60), 2, 'Flower patch: three white heads + three leaf blades.'),
]

for name, build, budget, maxc, notes in SPECS:
    mesh = build()
    ob = fam.make_object(name, mesh)
    fam.add_asset(name, [ob], budget=budget, notes=notes, max_colours=maxc)

fam.finish(lineup_gap=0.5)

if not fam.args.no_render:
    allobjs = fam.objs_of([s[0] for s in SPECS])
    fam.shot('01_lineup_three_quarter.png', allobjs, az=30, el=22, res=(1800, 700), lens=50, pad=1.15)
    # a 2 m cluster as PropScatterer would place it (showcase copies only)
    for i, (n, x, y, rot) in enumerate((('GR_Tuft_A', 0.0, 0.0, 0), ('GR_Tuft_B', 0.7, 0.3, 40), ('GR_Tuft_C', -0.6, 0.5, 120),
                                        ('GR_Tuft_A', 0.3, -0.7, 200), ('GR_Tuft_B', -0.5, -0.5, 300), ('GR_Tuft_C', 0.9, -0.3, 80),
                                        ('GR_Tuft_A', -0.9, -0.1, 250), ('GR_Flowers_Yellow', 0.1, 0.8, 0), ('GR_Flowers_White', -1.2, 0.9, 60))):
        fam.place_copy(n, 4.0 + x, 3.0 + y, rot)
    objs = fam.showcase_only(True)
    fam.shot('02_cluster_eye_level.png', objs, az=-15, el=10, res=(1600, 900), lens=35, person=(2.2, 2.0), eye=1.2, pad=1.2)
    fam.showcase_only(False)
    fam.clear_showcase()
