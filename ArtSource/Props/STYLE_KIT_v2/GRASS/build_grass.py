"""STYLE_KIT_v2 / GRASS - three grass tufts and two flower patches (style bible v2, 6.5).

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python ArtSource/Props/STYLE_KIT_v2/GRASS/build_grass.py -- --revision 1

A tuft is 5-7 wedge blades (closed tetrahedra, 4 tris) fanned out from one root by a fixed template; the zone swatch at
the base turns to its .light step at the tips. Every normal points straight up, so a tuft is lit exactly like the
ground it stands on and never shimmers. Flower patches are a tuft plus 6 soft heads of ONE colour on short stalks.
No grass carpets: the zone reads by the ground colour; tufts are sparse accents along edges (bible 6.5, 10.5).
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit2 as sk                                   # noqa: E402

fam = sk.Family('SK2-GRASS-001', __file__, 'GR_', budget=(1, 40),
                description='Grass v2: GR_Tuft_A/B (lawn), GR_Tuft_C (meadow), GR_Flowers_Chalk, GR_Flowers_Red (bible 6.5)')

# blade template: (azimuth deg, tip radius m, height fraction)
TUFTS = {
    'A': ('grad.lawn', 0.30, [(8, 0.10, 1.0), (80, 0.13, 0.80), (152, 0.11, 0.92), (226, 0.14, 0.74), (298, 0.12, 0.86)]),
    'B': ('grad.lawn', 0.38, [(20, 0.12, 0.88), (75, 0.15, 1.0), (140, 0.13, 0.78), (195, 0.16, 0.9), (262, 0.12, 0.7),
                              (320, 0.15, 0.84)]),
    'C': ('grad.meadow', 0.45, [(0, 0.13, 0.82), (52, 0.17, 1.0), (104, 0.12, 0.7), (157, 0.16, 0.9), (209, 0.14, 0.76),
                                (262, 0.17, 0.95), (314, 0.12, 0.66)]),
}


def tuft(m, grad, H, blades, root=0.03, w=0.07):
    for az, rho, k in blades:
        a = math.radians(az)
        foot = (root * math.cos(a), root * math.sin(a), 0.0)
        tip = (rho * math.cos(a), rho * math.sin(a), H * k)
        m.blade(foot, tip, w, 0.035, grad, grad=(0.0, H), name='blade')


def grass(key):
    grad, H, blades = TUFTS[key]
    m = sk.Mesh()
    tuft(m, grad, H, blades)
    return m


# flower heads: (azimuth deg, radius m, height m)
HEADS = [(15, 0.07, 0.31), (85, 0.15, 0.25), (150, 0.09, 0.35), (205, 0.17, 0.22), (265, 0.11, 0.29), (330, 0.16, 0.33)]


def flowers(col):
    m = sk.Mesh()
    tuft(m, 'grad.lawn', 0.26, [(40, 0.12, 0.9), (112, 0.1, 1.0), (178, 0.13, 0.78), (250, 0.11, 0.95), (318, 0.12, 0.84)])
    for az, rho, h in HEADS:
        a = math.radians(az)
        head = (rho * math.cos(a), rho * math.sin(a), h)
        foot = (0.02 * math.cos(a), 0.02 * math.sin(a), 0.0)
        m.blade(foot, (head[0], head[1], h - 0.01), 0.06, 0.03, 'grad.lawn', grad=(0.0, 0.3), name='stalk')
        m.bipyramid(0.06, 0.075, 6, col, at=head, rot=az, normals='smooth', name='head')
    return m


for i, k in enumerate(('A', 'B', 'C')):
    fam.add_asset(f'GR_Tuft_{k}', (lambda k=k: grass(k)), budget=(1, 40), max_swatches=1, row=0,
                  height_m=TUFTS[k][1], blades=len(TUFTS[k][2]), zone='lawn' if TUFTS[k][0] == 'grad.lawn' else 'meadow')
for col in ('chalk', 'red'):
    fam.add_asset(f'GR_Flowers_{col.capitalize()}', (lambda col=col: flowers(col)), budget=(1, 120), max_swatches=2, row=1,
                  flower=col, heads=len(HEADS))

report = fam.finish(lineup_gap=0.25, extra_notes=[
    'All grass normals point up (+Z): lit like the ground, no shimmer (bible 6.5). Cut off beyond 60 m, GPU instancing.',
    'GR_Tuft_A/B carry the lawn ramp (old town, parks, yards), GR_Tuft_C the meadow ramp (hamlet, roadsides, field edges).'])


# ---------------------------------------------------------------- previews
def box(w, d, h, col, at=(0, 0, 0)):
    m = sk.Mesh()
    m.box(w, d, h, col, base=True, at=at)
    return m


if not fam.args.no_render:
    objs = []
    x = 0.0
    for n in ('GR_Tuft_A', 'GR_Tuft_B', 'GR_Tuft_C', 'GR_Flowers_Chalk', 'GR_Flowers_Red'):
        objs += fam.place(n, x, 0.0)
        x += 0.55
    fam.showcase(True)
    fam.shot('01_lineup.png', objs, az=20, el=16, res=(1800, 800), lens=60, ground='lawn')
    fam.clear_showcase()
    # lawn edge in the old town: a 0.4 m strip along the plinth, tufts every 1.5-3 m; a round flower bed with a chalk rim
    objs = []
    for i, (xx, k) in enumerate([(0.3, 'A'), (2.1, 'B'), (3.0, 'A'), (5.4, 'B'), (7.2, 'A'), (8.0, 'B'), (10.3, 'A')]):
        objs += fam.place(f'GR_Tuft_{k}', xx, 0.25, rot=i * 67)
    wall = sk.Mesh()
    wall.box(12.0, 0.6, 3.2, 'cream', base=True, at=(5.2, 0.0, 0.5))
    wall.box(12.1, 0.7, 0.5, 'asphalt', base=True, at=(5.2, 0.0, 0.0))
    objs.append(fam.proxy('Proxy_Wall', wall, 0.0, 0.85))
    rim = sk.Mesh()
    rim.lathe_loop([(1.6, 0.0), (1.75, 0.0), (1.75, 0.15), (1.6, 0.15)], 24, 'chalk', normals='soft')
    rim.lathe([(0.0, 0.0), (1.62, 0.0), (1.62, 0.03), (0.0, 0.03)], 24, 'wood.dark', normals='flat')
    objs.append(fam.proxy('Proxy_Bed', rim, 5.2, -3.0))
    for i in range(14):
        a = math.radians(i * 137.5)
        rr = 1.25 * math.sqrt((i + 0.5) / 14)
        objs += fam.place('GR_Flowers_Red', 5.2 + rr * math.cos(a), -3.0 + rr * math.sin(a), rot=i * 53)
    fam.showcase(True)
    fam.shot('02_lawn_edge_and_bed.png', objs, az=-25, el=28, res=(1800, 1100), lens=40, ground='lawn')
    fam.clear_showcase()
    # meadow: clusters of 3-7 tufts and one patch of white flowers (bible 6.5 table)
    objs = []
    clusters = [(0.0, 0.0, 5), (3.6, 1.2, 3), (1.8, 3.4, 7), (5.5, 4.2, 4)]
    for ci, (cx, cy, n) in enumerate(clusters):
        for j in range(n):
            a = math.radians(j * 360 / n + ci * 29)
            rr = 0.28 + 0.12 * (j % 2)
            objs += fam.place('GR_Tuft_C', cx + rr * math.cos(a), cy + rr * math.sin(a), rot=j * 71 + ci * 13)
    for j in range(5):
        a = math.radians(j * 72 + 10)
        objs += fam.place('GR_Flowers_Chalk', 3.3 + 0.35 * math.cos(a), 2.9 + 0.35 * math.sin(a), rot=j * 41)
    fam.showcase(True)
    fam.shot('03_meadow_clusters.png', objs, az=15, el=22, res=(1800, 1000), lens=45, ground='meadow')
    fam.clear_showcase()
    fam.showcase(False)
print('done')
