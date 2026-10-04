"""MAP-BUSHES-001: stylised low-poly bushes for the VOLUNTEERS ONLY map (post-Soviet town yards, wastelands).

BU_Bush_Round  round shrub ~1.2 m            BU_Bush_Lilac  lilac ~2 m with blossom panicles
BU_Hedge_Box   trimmed hedge module 2.0 x 0.7 x 1.1 m, tileable along X (flat ends at x = +-1.0)
BU_Bush_Wild   scruffy wild bush ~1.5 m with dead twigs
One closed-shell multi-material object per asset, pivot at the centre of the base on the ground.

Run (repo root):  python3 ArtSource/Props/MAP_PROPS/BUSHES/build_bushes.py -- --revision 1
              or: blender -b --factory-startup --python ArtSource/Props/MAP_PROPS/BUSHES/build_bushes.py -- --revision 1
Flags: --force (overwrite the same revision), --no-render, --samples N, --out DIR
"""
import sys, math, random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import mapprops as mp  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

TAU = math.tau
fam = mp.Family('MAP-BUSHES-001', __file__, prefix='BU_', tri_budget_default=600,
                description='Stylised faceted low-poly bushes: round shrub, lilac with blossom, tileable box hedge module, scruffy wild bush. '
                            'One object per asset, flat matte MP_* colours, closed shells, pivot at the base centre.')


# ------------------------------------------------------------------ local helpers (the shared lib is not edited)
def clump(mesh, c, r, m, seed, squash=(1, 1, 1), jitter=0.16, subdiv=2, flat_bottom=None):
    """Foliage clump. bmesh icosphere: subdiv=1 is the bare icosahedron (20 tris), subdiv=2 = 80 tris."""
    mesh.blob(r, m, M=mp.T(*c), subdiv=subdiv, jitter=jitter, seed=seed, squash=squash, flat_bottom=flat_bottom)


def ground(mesh):
    """Drop the whole mesh so its lowest vertex sits exactly on z = 0 (bushes have no vertical trunk to anchor)."""
    mz = min(v[2] for v in mesh.verts)
    mesh.verts = [(x, y, z - mz) for x, y, z in mesh.verts]


def loft(mesh, rings, m, mfn=None):
    """Closed shell from a list of rings (same vertex count, consistent winding), capped at both ends.
    mfn(profile_edge_k) -> material name lets e.g. the top of a hedge use a lighter green."""
    n = len(rings[0])
    v, f, mats = [], [], []
    for ring in rings:
        for p in ring:
            v.append(tuple(p))
    for i in range(len(rings) - 1):
        for k in range(n):
            k1 = (k + 1) % n
            f.append((i * n + k, i * n + k1, (i + 1) * n + k1, (i + 1) * n + k))
            mats.append(mfn(k) if mfn else m)
    f.append(tuple(range(n))[::-1]); mats.append(m)
    f.append(tuple(range((len(rings) - 1) * n, len(rings) * n))); mats.append(m)
    mesh._shell(v, f, mats)


def stem(mesh, foot, top, r, m, seg=4):
    """Stem that leaves the ground vertically (flat base ring on z = 0) and then bends towards `top`."""
    fx, fy, _ = foot
    knee = Vector((fx, fy, 0.22))
    mesh.cyl_between((fx, fy, 0.0), knee, r, seg, m)
    mesh.cyl_between(knee, top, r * 0.95, seg, m, r1=r * 0.45)


# ------------------------------------------------------------------ assets
def bush_round(seed=101):
    rnd = random.Random(seed)
    m = mp.Mesh()
    n = 5
    for i in range(n):
        ang = TAU * i / n + rnd.uniform(-0.2, 0.2)
        d = 0.36 + rnd.uniform(-0.05, 0.08)
        r = 0.5 + rnd.uniform(-0.05, 0.08)
        clump(m, (math.cos(ang) * d, math.sin(ang) * d, r * 0.78), r, 'MP_Leaf' if i % 2 else 'MP_Leaf_Light', seed + i,
              squash=(1.0, 1.0, 0.9), jitter=0.15, flat_bottom=-0.55)
    clump(m, (0.02, -0.03, 0.72), 0.56, 'MP_Leaf_Light', seed + 9, squash=(1.0, 1.0, 0.85), jitter=0.15)
    ground(m)
    return m


def bush_lilac(seed=111):
    rnd = random.Random(seed)
    m = mp.Mesh()
    n = 3
    heads = []
    for i in range(n):
        ang = TAU * i / n + 0.5 + rnd.uniform(-0.25, 0.25)
        d = 0.46 + rnd.uniform(-0.05, 0.12)
        zc = 1.1 + rnd.uniform(-0.1, 0.2)
        c = Vector((math.cos(ang) * d, math.sin(ang) * d, zc))
        foot = (math.cos(ang) * 0.12, math.sin(ang) * 0.12, 0.0)
        stem(m, foot, c, 0.05, 'MP_Bark')
        heads.append((c, 0.5 + rnd.uniform(-0.04, 0.08)))
    c_top = Vector((-0.05, 0.08, 1.42))
    stem(m, (0.0, 0.0, 0.0), c_top, 0.06, 'MP_Bark')
    heads.append((c_top, 0.55))
    for i, (c, r) in enumerate(heads):
        clump(m, c, r, 'MP_Leaf_Dark' if i % 2 else 'MP_Leaf', seed + 20 + i, squash=(1.0, 1.0, 1.1), jitter=0.16)
    # blossom panicles: elongated faceted cones standing up out of the top of the leaf heads
    k = 0
    for i, (c, r) in enumerate(heads):
        for j in range(2 if i == len(heads) - 1 else 1):
            ang = TAU * rnd.random()
            off = Vector((math.cos(ang), math.sin(ang), 0)) * (r * rnd.uniform(0.3, 0.5) if j else 0.0)
            p = c + off + Vector((0, 0, r * (0.8 if j else 0.95)))
            m.blob(0.24 + rnd.uniform(0.0, 0.05), 'MP_Blossom', M=mp.T(*p), subdiv=1, jitter=0.08, seed=seed + 40 + k,
                   squash=(0.75, 0.75, 1.6))
            k += 1
    for i, (c, r) in enumerate(heads[:3]):  # a few side panicles leaning out
        ang = TAU * i / 3 + 0.3
        p = c + Vector((math.cos(ang) * r * 0.85, math.sin(ang) * r * 0.85, r * 0.35))
        m.blob(0.22, 'MP_Blossom', M=mp.T(*p) @ mp.R(-28, Vector((-math.sin(ang), math.cos(ang), 0))), subdiv=1, jitter=0.08,
               seed=seed + 60 + i, squash=(0.7, 0.7, 1.45))
    ground(m)
    return m


def hedge_box(seed=121, length=2.0, width=0.7, height=1.1):
    rnd = random.Random(seed)
    m = mp.Mesh()
    hw = width / 2
    # trimmed profile in (y, z): narrow foot, vertical sides, chamfered shoulders, flat top
    prof = [(-hw * 0.72, 0.0), (hw * 0.72, 0.0), (hw, height * 0.22), (hw, height * 0.8), (hw * 0.62, height),
            (-hw * 0.62, height), (-hw, height * 0.8), (-hw, height * 0.22)]
    xs = [-length / 2 + length * t / 8 for t in range(9)]
    rings = []
    for i, x in enumerate(xs):
        end = i in (0, len(xs) - 1)
        ring = []
        for (y, z) in prof:
            if end or z == 0.0:
                ring.append((x, y, z))                     # exact flat ends and exact ground line
            else:
                ring.append((x + rnd.uniform(-0.04, 0.04), y * rnd.uniform(0.9, 1.03), z * rnd.uniform(0.95, 1.03)))
        rings.append(ring)
    loft(m, rings, 'MP_Leaf_Dark', mfn=lambda k: 'MP_Leaf' if k in (3, 4, 5) else 'MP_Leaf_Dark')  # lighter top + shoulders
    # a few soft lumps on top / sides; they stay inside |x| < 1 so modules still butt together
    for i in range(4):
        x = -0.62 + i * 0.41 + rnd.uniform(-0.05, 0.05)
        y = rnd.uniform(-0.08, 0.08)
        clump(m, (x, y, height - 0.11), 0.3, 'MP_Leaf_Light' if i % 2 else 'MP_Leaf', seed + i,
              squash=(1.0, 0.9, 0.45), jitter=0.16, flat_bottom=-0.3)
    return m


def bush_wild(seed=131):
    rnd = random.Random(seed)
    m = mp.Mesh()
    n = 5
    tops = []
    for i in range(n):
        ang = TAU * i / n + rnd.uniform(-0.4, 0.4)
        d = 0.42 + rnd.uniform(-0.12, 0.18)
        r = 0.46 + rnd.uniform(-0.1, 0.14)
        zc = r * 0.9 + rnd.uniform(0.0, 0.35)
        c = (math.cos(ang) * d, math.sin(ang) * d, zc)
        clump(m, c, r, ['MP_Leaf_Dark', 'MP_Leaf', 'MP_Leaf_Autumn', 'MP_Leaf_Dark', 'MP_Leaf'][i], seed + i,
              squash=(rnd.uniform(0.85, 1.15), rnd.uniform(0.85, 1.15), rnd.uniform(0.8, 1.2)), jitter=0.26)
        tops.append((Vector(c), r))
    clump(m, (0.1, -0.05, 1.0), 0.5, 'MP_Leaf_Dark', seed + 9, squash=(0.9, 1.0, 1.05), jitter=0.25)
    tops.append((Vector((0.1, -0.05, 1.0)), 0.5))
    # dead twigs sticking out at odd angles
    for i in range(7):
        c, r = tops[i % len(tops)]
        ang = TAU * rnd.random()
        el = rnd.uniform(0.25, 1.2)
        d = Vector((math.cos(ang) * math.cos(el), math.sin(ang) * math.cos(el), math.sin(el)))
        p0 = c + d * (r * 0.3)
        p1 = c + d * (r + rnd.uniform(0.25, 0.55))
        m.cyl_between(p0, p1, 0.03, 4, 'MP_Wood_Grey', r1=0.012)
    ground(m)
    return m


SPECS = [
    ('BU_Bush_Round', bush_round, {}, 'Round trimmed-ish shrub ~1.2 m: 6 overlapping clumps, two greens. Yards, parks, sleeping district.'),
    ('BU_Bush_Lilac', bush_lilac, {}, 'Lilac ~2 m: 4 bent stems, 4 leaf heads, 8 pink MP_Blossom panicles. Soviet yards / old town.'),
    ('BU_Hedge_Box', hedge_box, {'tile_length_m': 2.0},
     'Trimmed box hedge module 2.0 x 0.7 x 1.1 m, tileable along X: ends are exactly flat at x = +-1.0, lumps stay inside. Elite hill, old town.'),
    ('BU_Bush_Wild', bush_wild, {}, 'Scruffy wild bush ~1.5 m: irregular dark/autumn clumps, 7 dead grey twigs. Wastelands, village edges.'),
]

for name, build, meta, notes in SPECS:
    mesh = build()
    ob = fam.make_object(name, mesh)
    fam.add_asset(name, [ob], budget=600, notes=notes, **meta)

fam.finish(lineup_gap=1.2, render=False)
if not fam.args.no_render:
    fam.render_previews(camera=[('01_lineup_front.png', 270, 8, (1800, 800), 50),
                                ('02_lineup_three_quarter.png', 240, 20, (1800, 900), 50)])
    # three hedge modules butted together at the 2.0 m pitch (showcase copies only, not exported) to check the tiling
    copies = [fam.place_copy('BU_Hedge_Box', x, 0.0) for x in (0.0, 2.0, 4.0)]
    objs = fam.showcase_only(True)
    fam.render_previews(camera=[('03_hedge_tiled.png', 205, 12, (1400, 800), 50)], frame_objects=objs, person_at=(6.8, 0, 0))
    fam.showcase_only(False)
    for c in copies:
        bpy.data.objects.remove(c)
