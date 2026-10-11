"""STYLE_KIT_v2 / BUSHES - round bush, flowering lilac, scrub, plus two cushion-hedge modules (style bible v2, 6.4).

  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python ArtSource/Props/STYLE_KIT_v2/BUSHES/build_bushes.py -- --revision 1

Bushes are 2-3 smooth lobes from a fixed template (icosphere subdiv 2, no jitter) pressed flat where they meet the
ground, leaf on top and leaf.dark below (gradient cell of the palette). The lilac carries soft teardrop panicles of
one colour; the scrub of the rough districts has two bare twigs. Hedges (v02b) are 2.0 m clipped modules: a
rounded-box section with a domed top and a templated lobe every 1 m, plus dome end pieces (top leaf.light).
"""
import math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import stylekit2 as sk                                   # noqa: E402
from mathutils import Vector                             # noqa: E402

fam = sk.Family('SK2-BUSHES-001', __file__, 'BU_', budget=(1, 300),
                description='Bushes v2: BU_Round, BU_Flower (lilac), BU_Scrub + BU_Hedge_Low / BU_Hedge_High modules (bible 6.4)')


def ground_lobe(m, x, y, r, sz, fb=-0.5, rot=0.0, crown=(0.0, 1.1), w=0.7, grad='grad.bush'):
    """Lobe whose flattened underside sits exactly on z = 0."""
    low = fb + (-1 - fb) * 0.25                 # lowest point of a flattened lobe, in units of r * sz
    z = -low * r * sz
    m.lobe(r, grad, at=(x, y, z), squash=(1, 1, sz), flat_bottom=fb, rot=rot,
           grad=(0.0, z + r * sz, (crown[0], crown[1], w)), name='lobe')
    return z + r * sz


def lobe(m, x, y, z, r, sz=1.0, rot=0.0, crown=(0.0, 1.1), w=0.7, grad='grad.bush'):
    m.lobe(r, grad, at=(x, y, z), squash=(1, 1, sz), rot=rot, grad=(z - r * sz, z + r * sz, (crown[0], crown[1], w)), name='lobe')
    return z + r * sz


def bloom(m, pos, axis, col):
    """Lilac blossom puff: a smooth icosphere (subdiv 1, 20 tris), r 0.16, pressed to 0.75 along `axis` and half sunk
    into the lobe, so the flowers read as soft patches of colour on the bush, not as spikes."""
    q = Vector((0, 0, 1)).rotation_difference(Vector(axis).normalized())
    M = sk.T(*pos) @ q.to_matrix().to_4x4()
    m.lobe(0.16, col, subdiv=1, squash=(1, 1, 0.75), M=M, grad=None, member=0.24, name='head')


def round_bush():
    """h 1.1 m, 1.6 m wide: two low lobes side by side, one on top, a little off-centre."""
    m = sk.Mesh()
    ground_lobe(m, -0.26, -0.12, 0.56, 0.82, rot=10)
    ground_lobe(m, 0.28, 0.14, 0.52, 0.82, rot=37)
    lobe(m, 0.04, 0.0, 0.66, 0.46, 0.95, rot=23)
    return m


def flower_bush():
    """Lilac, h ~1.75 m: a taller round bush + 9 lilac panicles pointing out and up from the upper half."""
    m = sk.Mesh()
    crown = (0.0, 1.62)
    lobes = [(-0.3, -0.1, None, 0.62, 0.9), (0.32, 0.15, None, 0.58, 0.9), (0.0, 0.02, 1.04, 0.56, 1.04)]
    centres = []
    for i, (x, y, z, r, sz) in enumerate(lobes):
        if z is None:
            top = ground_lobe(m, x, y, r, sz, rot=11 * i, crown=crown)
            z = top - r * sz
        else:
            lobe(m, x, y, z, r, sz, rot=29, crown=crown)
        centres.append((x, y, z, r, sz))
    # (lobe, azimuth deg, elevation deg): a hand-set ring of panicles, none on the shaded underside
    heads = [(2, 15, 62), (2, 135, 48), (2, 255, 40), (2, 320, 20), (0, 200, 38), (0, 260, 14), (1, 40, 32), (1, 95, 12), (1, 330, 44)]
    for li, az, el in heads:
        x, y, z, r, sz = centres[li]
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))
        p = Vector((x, y, z)) + Vector((d.x * r, d.y * r, d.z * r * sz)) * 0.97
        n = Vector((d.x, d.y, d.z / sz)).normalized() + Vector((0, 0, 0.3))
        bloom(m, tuple(p), tuple(n), 'lilac')
    return m


def scrub():
    """Rough-district scrub: three lobes of template sizes (big, medium, small-high) + two bare twigs (wood, 0.06 m)."""
    m = sk.Mesh()
    crown = (0.0, 1.28)
    ground_lobe(m, -0.2, 0.0, 0.6, 0.85, fb=-0.45, rot=5, crown=crown, w=0.5)
    ground_lobe(m, 0.45, 0.2, 0.42, 0.9, fb=-0.45, rot=40, crown=crown, w=0.5)
    lobe(m, -0.06, -0.15, 0.96, 0.32, 1.0, rot=17, crown=crown, w=0.5)
    m.tube([(-0.1, 0.0, 0.55), (0.12, -0.12, 1.12), (0.4, -0.3, 1.42)], [0.035, 0.032, 0.03], 5, 'wood', normals='soft',
           kind='organic', name='twig')
    m.tube([(0.25, 0.1, 0.45), (0.55, 0.2, 0.86), (0.82, 0.36, 1.02)], [0.034, 0.032, 0.03], 5, 'wood', normals='soft',
           kind='organic', name='twig')
    return m


def hedge_profile(h, d=0.9):
    """v02b clipped-hedge section (critique 4): a rounded box, not a log. Tucked foot, near-vertical sides, a 0.12 m
    bevel into a gently domed top (+0.045 m at the middle). [(y, z)] counter-clockwise seen from +X."""
    a = d / 2
    right = [(a - 0.03, 0.0), (a, 0.10), (a, h - 0.14), (a - 0.025, h - 0.045), (a - 0.09, h), (a - 0.25, h + 0.035)]
    return right + [(0.0, h + 0.045)] + [(-y, z) for y, z in reversed(right)]


def loft(m, sections, prof, grad_top, name):
    """Closed loft along +X: sections = [(x, width scale, height scale)], prof = [(y, z)]; caps at both ends (convex
    n-gons, ear-clipped later). The foot stays on z = 0; the section is scaled about its bottom centre."""
    n = len(prof)
    verts, faces = [], []
    for x, sw, sh in sections:
        verts += [(x, y * sw, z * sh) for y, z in prof]
    for k in range(len(sections) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    last = (len(sections) - 1) * n
    faces.append(tuple(range(n - 1, -1, -1)))
    faces.append(tuple(last + i for i in range(n)))
    vol = 0.0                                             # wind outward whatever the profile direction
    for f in faces:
        p = [Vector(verts[i]) for i in f]
        for q in range(1, len(p) - 1):
            vol += p[0].dot(p[q].cross(p[q + 1])) / 6.0
    if vol < 0:
        faces = [tuple(reversed(f)) for f in faces]
    m.shell(verts, faces, 'grad.hedge.v2', normals='soft', grad=(0.0, grad_top), kind='organic', facet=False,
            member=0.6, name=name)


def lobe_f(t):
    """Template lobe rhythm: one lobe per metre, creases at whole metres (module ends sit in a crease)."""
    return 0.5 - 0.5 * math.cos(sk.TAU * t)


def hedge(h, d=0.9, length=2.0, step=0.25):
    """v02b 2.0 m module (critique 4): the rounded-box section of hedge_profile lofted along X with a TEMPLATED lobe
    every 1 m (width x0.90-1.00, top x0.93-1.00), so a run reads as clipped shrubs, not a green log; both module ends
    sit in a crease and tile seamlessly. Free ends of a run take BU_Hedge_*_End."""
    m = sk.Mesh()
    k = int(round(length / step))
    sections = []
    for i in range(k + 1):
        t = i * step
        f = lobe_f(t)
        sections.append((t - length / 2, 0.90 + 0.10 * f, 0.93 + 0.07 * f))
    loft(m, sections, hedge_profile(h, d), h * 1.05, 'hedge')
    return m


def hedge_end(h, d=0.9, r=0.45):
    """Rounded lobed end of a hedge run: starts with the crease section at x = 0 and closes in a dome over r along +X
    (width follows a quarter circle, the top drops only ~45 %), so a run never ends in a flat cut."""
    m = sk.Mesh()
    sections = []
    for deg in (0.0, 22.5, 45.0, 62.0, 76.0, 84.0):
        th = math.radians(deg)
        c = math.cos(th)
        sections.append((r * math.sin(th), 0.90 * c, 0.93 * (1.0 - (1.0 - c) * 0.55)))
    loft(m, sections, hedge_profile(h, d), h * 1.05, 'hedge_end')
    return m


fam.add_asset('BU_Round', round_bush, budget=(1, 300), max_swatches=2, row=0, use='lawns, yards, beds; groups of 3 or 5')
fam.add_asset('BU_Flower', flower_bush, budget=(1, 450), max_swatches=2, row=0, flower='lilac', use='parks, the square, yards')
fam.add_asset('BU_Scrub', scrub, budget=(1, 350), max_swatches=2, row=0, use='arches, industrial zone, field edges')
fam.add_asset('BU_Hedge_Low', lambda: hedge(0.75), budget=(1, 260), max_swatches=1, row=1, module_m=2.0, use='the square, paths, flower beds')
fam.add_asset('BU_Hedge_High', lambda: hedge(1.1), budget=(1, 260), max_swatches=1, row=1, module_m=2.0, use='elite gardens, park edges')
fam.add_asset('BU_Hedge_Low_End', lambda: hedge_end(0.75), budget=(1, 160), max_swatches=1, row=1, module_m=0.45,
              use='free end of a low hedge run: origin at the joint, extends along +X (rotate 180 deg for the start)')
fam.add_asset('BU_Hedge_High_End', lambda: hedge_end(1.1), budget=(1, 160), max_swatches=1, row=1, module_m=0.45,
              use='free end of a high hedge run: origin at the joint, extends along +X')

report = fam.finish(lineup_gap=1.2, extra_notes=[
    'Hedge modules are 2.0 m long; v02b: rounded-box section (0.9 m deep, 0.12 m bevel, domed top, leaf.light top band) '
    'with a templated lobe every 1 m; modules tile end to end in a crease, BU_Hedge_*_End closes a run with a dome. '
    'Low hedge 0.75 m (v01: 0.6 m read as a log on the square).',
    'Uniform instance scale 0.92-1.08 (bible 6.4); bushes under ground-floor windows stay <= 1.0 m (BU_Round at 0.92).'])


# ---------------------------------------------------------------- previews
def slab(w, d, h, col):
    m = sk.Mesh()
    m.box(w, d, h, col, base=True)
    return m


if not fam.args.no_render:
    objs = []
    x = 0.0
    for n in ('BU_Round', 'BU_Flower', 'BU_Scrub', 'BU_Hedge_Low', 'BU_Hedge_High', 'BU_Hedge_High_End'):
        r = report['assets'][n]
        x += -r['bounds_min'][0]
        objs += fam.place(n, x, 0.0)
        x += r['bounds_max'][0] + 0.9
    fam.showcase(True)
    fam.shot('01_lineup.png', objs, az=25, el=14, res=(2000, 900), lens=55, ground='lawn', person=(-1.2, -0.8))
    fam.silhouette('03_silhouettes.png', objs, res=(2200, 700))
    fam.clear_showcase()
    # a bed on the square: low hedge along a paving path, round bushes in a group of 3, lilac at the corner, scrub apart
    objs = []
    for i in range(5):
        objs += fam.place('BU_Hedge_Low', i * 2.0, 0.0)
    objs += fam.place('BU_Hedge_Low_End', 9.0, 0.0)
    objs += fam.place('BU_Hedge_Low_End', -1.0, 0.0, rot=180)
    objs += fam.place('BU_Round', 1.0, 2.2, rot=0)
    objs += fam.place('BU_Round', 2.6, 2.6, rot=120, scale=0.92)
    objs += fam.place('BU_Round', 1.9, 3.7, rot=240, scale=1.06)
    objs += fam.place('BU_Flower', 6.6, 2.9, rot=30)
    objs += fam.place('BU_Scrub', 9.6, 4.2, rot=200)
    path = fam.proxy('Proxy_Paving', slab(14.0, 3.0, 0.02, 'paving'), 4.0, -2.2)
    curb = fam.proxy('Proxy_Curb', slab(14.0, 0.15, 0.12, 'chalk'), 4.0, -0.62)
    fam.showcase(True)
    fam.shot('02_bed_on_the_square.png', objs + [path, curb], az=-30, el=24, res=(1800, 1100), lens=45, ground='lawn',
             person=(-1.0, -1.6))
    fam.clear_showcase()
    fam.showcase(False)
print('done')
