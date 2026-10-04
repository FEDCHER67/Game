"""MAP-TREES-001: stylised low-poly trees for the VOLUNTEERS ONLY map (post-Soviet town).

Six species, two size variants each (A large, B smaller with different proportions/seed):
birch, pine (Scots pine: tall trunk, cloud pads), oak, Lombardy poplar, apple tree (with fruit), palm (beach / elite hill).
Each tree is ONE multi-material object: trunk + branches + crown clumps, all closed faceted shells,
root pivot at the centre of the trunk base on the ground.

Run (repo root):  python3 ArtSource/Props/MAP_PROPS/TREES/build_trees.py -- --revision 1
              or: blender -b --factory-startup --python ArtSource/Props/MAP_PROPS/TREES/build_trees.py -- --revision 1
Flags: --force (overwrite the same revision), --no-render, --samples N, --out DIR
"""
import sys, math, random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '_lib'))
import mapprops as mp  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

TAU = math.tau
fam = mp.Family('MAP-TREES-001', __file__, prefix='TR_', tri_budget_default=1500,
                description='Stylised faceted low-poly trees: birch, pine, oak, poplar, apple, palm; A = large, B = smaller variant. '
                            'One object per tree (trunk + crown, multi-material), flat matte MP_* colours, closed shells.')


# ------------------------------------------------------------------ local helpers (the shared lib is not edited)
def tube(mesh, pts, radii, seg, m, mfn=None):
    """Closed generalised cylinder along a polyline. mfn(band, k) -> material name for per-face colouring (birch marks).
    Make pts[1] vertically above pts[0] so the base ring lies flat on the ground."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    tang = []
    for i in range(n):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, n - 1)]
        tang.append((b - a).normalized())
    ref = Vector((1, 0, 0)) if abs(tang[0].x) < 0.9 else Vector((0, 1, 0))
    u = (ref - tang[0] * ref.dot(tang[0])).normalized()
    v, f, mats, rings = [], [], [], []
    for i in range(n):
        if i:
            u = (u - tang[i] * u.dot(tang[i])).normalized()
        w = tang[i].cross(u)
        idx = []
        for k in range(seg):
            a = TAU * k / seg
            idx.append(len(v)); v.append(tuple(pts[i] + radii[i] * (math.cos(a) * u + math.sin(a) * w)))
        rings.append(idx)
    for i in range(n - 1):
        lo, hi = rings[i], rings[i + 1]
        for k in range(seg):
            k1 = (k + 1) % seg
            f.append((lo[k], lo[k1], hi[k1], hi[k]))
            mats.append(mfn(i, k) if mfn else m)
    f.append(tuple(rings[0][::-1])); mats.append(m)
    f.append(tuple(rings[-1])); mats.append(m)
    mesh._shell(v, f, mats)


def ribbon(mesh, spine, widths, m, fold=0.45, thick=0.03):
    """Closed drooping leaf blade (palm frond): diamond cross-section (top spine, folded-down edges, thin bottom)
    swept along `spine`, pole-capped at both ends. widths = half-width per spine point (>0)."""
    spine = [Vector(p) for p in spine]
    n = len(spine)
    v, f = [], []
    d0 = (spine[1] - spine[0]).normalized()
    base = spine[0] - d0 * 0.08
    tip = spine[-1] + (spine[-1] - spine[-2]).normalized() * 0.12
    v.append(tuple(base))
    rings = []
    for i in range(n):
        a = spine[max(i - 1, 0)]; b = spine[min(i + 1, n - 1)]
        t = (b - a).normalized()
        right = t.cross(Vector((0, 0, 1)))
        if right.length < 1e-4:
            right = Vector((0, 1, 0))
        right.normalize()
        up = right.cross(t).normalized()
        c = spine[i]; w = widths[i]
        pts = [c + up * thick, c + right * w - up * (w * fold), c - up * thick, c - right * w - up * (w * fold)]
        idx = []
        for p in pts:
            idx.append(len(v)); v.append(tuple(p))
        rings.append(idx)
    v.append(tuple(tip)); tip_i = len(v) - 1
    r0 = rings[0]
    for k in range(4):
        f.append((0, r0[(k + 1) % 4], r0[k]))
    for i in range(n - 1):
        lo, hi = rings[i], rings[i + 1]
        for k in range(4):
            k1 = (k + 1) % 4
            f.append((lo[k], lo[k1], hi[k1], hi[k]))
    rl = rings[-1]
    for k in range(4):
        f.append((rl[k], rl[(k + 1) % 4], tip_i))
    mesh._shell(v, f, m)


def clump(mesh, c, r, m, seed, squash=(1, 1, 1), jitter=0.16, subdiv=2, flat_bottom=None):
    """Foliage clump. bmesh icosphere: subdiv=1 is the bare icosahedron (20 tris), subdiv=2 = 80 tris."""
    mesh.blob(r, m, M=mp.T(*c), subdiv=subdiv, jitter=jitter, seed=seed, squash=squash, flat_bottom=flat_bottom)


def branch(mesh, p0, p1, r0, r1, m, seg=5):
    mesh.cyl_between(p0, p1, r0, seg, m, r1=r1)


def axis_at(pts, z):
    """Point on a trunk polyline at height z (linear interpolation)."""
    for a, b in zip(pts, pts[1:]):
        if a[2] <= z <= b[2]:
            t = (z - a[2]) / max(b[2] - a[2], 1e-6)
            return Vector(a).lerp(Vector(b), t)
    return Vector(pts[-1])


def curved_trunk(h, lean, wiggle, rnd, n_steps=7, phase=0.0):
    """Trunk polyline from the ground to height h, vertical first step, gentle lean + sine wiggle."""
    pts = [(0.0, 0.0, 0.0)]
    for i in range(1, n_steps + 1):
        t = i / n_steps
        if i == 1:
            pts.append((0.0, 0.0, h * t))
        else:
            x = lean * h * t * t + wiggle * h * math.sin(t * 4.2 + phase) * t
            y = wiggle * 0.6 * h * math.cos(t * 3.1 + phase) * t
            pts.append((x, y, h * t))
    return pts


def pick(rnd, seq, weights):
    return rnd.choices(seq, weights=weights, k=1)[0]


# ------------------------------------------------------------------ species
def birch(h, seed, n_clumps, crown_from, lean, r_base, clump_r):
    rnd = random.Random(seed)
    m = mp.Mesh()
    # trunk stations: alternate long / short bands; short bands carry the black marks (= horizontal dashes)
    zs = [0.0, 0.5 * h / 12]
    z, short = zs[-1], True
    top = h * 0.94
    while z < top - 0.3:
        step = (0.22 if short else rnd.uniform(0.75, 1.15)) * (h / 12)
        z = min(z + step, top); zs.append(z); short = not short
    nz = len(zs)
    pts, radii = [], []
    for i, z in enumerate(zs):
        t = z / h
        if i <= 1:
            x = y = 0.0
        else:
            x = lean * h * t * t + 0.03 * h * math.sin(t * 5.0 + seed) * t
            y = 0.02 * h * math.cos(t * 3.7 + seed) * t
        pts.append((x, y, z))
        radii.append(r_base * (1 - t) ** 0.9 + 0.035)
    grid = [[rnd.random() for _ in range(7)] for _ in range(nz)]
    short_band = [(zs[b + 1] - zs[b]) < 0.3 * h / 12 for b in range(nz - 1)]

    def mfn(b, k):
        zb = zs[b]
        p = 0.5 if short_band[b] and zb < crown_from * 1.15 else (0.14 if short_band[b] else 0.025)
        return 'MP_Bark_Mark' if grid[b][k] < p else 'MP_Bark_Birch'

    tube(m, pts, radii, 7, 'MP_Bark_Birch', mfn)
    # crown: top clump + elongated clumps hugging the upper trunk on thin white branches, two small hanging ones below
    tipz = zs[-1]
    tipx, tipy = pts[-1][0], pts[-1][1]
    clump(m, (tipx, tipy, tipz - clump_r * 0.3), clump_r * 1.1, 'MP_Leaf_Light', seed + 100,
          squash=(0.9, 0.9, 1.3), jitter=0.17)
    span = tipz - clump_r * 0.6 - crown_from
    for i in range(n_clumps):
        ang = TAU * (i * 0.618 + 0.25) + rnd.uniform(-0.25, 0.25)
        t = (i + 0.5) / n_clumps
        zc = crown_from + span * (0.25 + 0.75 * t) + rnd.uniform(-0.25, 0.25)
        r = clump_r * rnd.uniform(0.8, 1.0) * (0.85 + 0.3 * t)
        dist = r * rnd.uniform(0.55, 0.95)
        a = axis_at(pts, zc)
        c = (a.x + math.cos(ang) * dist, a.y + math.sin(ang) * dist, zc)
        branch(m, axis_at(pts, zc - r * 0.5), (c[0], c[1], c[2] + r * 0.2), r_base * 0.2, 0.03, 'MP_Bark_Birch')
        clump(m, c, r, pick(rnd, ['MP_Leaf_Light', 'MP_Leaf'], [0.65, 0.35]), seed + 10 + i,
              squash=(0.85, 0.85, rnd.uniform(1.25, 1.5)), jitter=0.18)
    for i in range(2):  # hanging twig clumps at the bottom of the crown
        ang = TAU * (i / 2 + 0.15) + rnd.uniform(-0.3, 0.3)
        r = clump_r * 0.55
        a = axis_at(pts, crown_from + r)
        c = (a.x + math.cos(ang) * r * 1.3, a.y + math.sin(ang) * r * 1.3, crown_from - r * 0.2)
        branch(m, a, (c[0], c[1], c[2] + r * 0.5), r_base * 0.16, 0.025, 'MP_Bark_Birch')
        clump(m, c, r, 'MP_Leaf', seed + 80 + i, squash=(0.8, 0.8, 1.6), jitter=0.18)
    return m


def pine(h, seed, n_pads, lean, r_base, pad_r, crown_from):
    rnd = random.Random(seed)
    m = mp.Mesh()
    pts = curved_trunk(h * 0.92, lean, 0.012, rnd, n_steps=7, phase=seed)
    radii = [r_base * (1 - i / 7) ** 0.85 + 0.06 for i in range(8)]
    tube(m, pts, radii, 7, 'MP_Bark')
    tip = Vector(pts[-1])
    # top dome pad
    clump(m, (tip.x, tip.y, tip.z + pad_r * 0.1), pad_r * 1.25, 'MP_Leaf_Pine', seed + 50,
          squash=(1.0, 1.0, 0.62), jitter=0.16, flat_bottom=-0.35)
    clump(m, (tip.x + pad_r * 0.1, tip.y, tip.z + pad_r * 0.55), pad_r * 0.7, 'MP_Leaf_Dark', seed + 51,
          squash=(1.0, 1.0, 0.8), jitter=0.16)
    # side pads on upward branches, alternating sides
    for i in range(n_pads):
        t = (i + 0.5) / n_pads
        zb = crown_from + (h * 0.88 - crown_from) * t
        ang = TAU * (i * 0.618 + 0.1) + rnd.uniform(-0.25, 0.25)
        r = pad_r * rnd.uniform(0.7, 1.0) * (1.0 - 0.25 * t)
        dist = pad_r * rnd.uniform(1.0, 1.6) * (1.0 - 0.3 * t)
        a = axis_at(pts, zb)
        c = Vector((a.x + math.cos(ang) * dist, a.y + math.sin(ang) * dist, zb + dist * 0.45))
        branch(m, a, c + Vector((0, 0, -r * 0.1)), r_base * 0.28, 0.05, 'MP_Bark')
        clump(m, c, r, pick(rnd, ['MP_Leaf_Pine', 'MP_Leaf_Dark'], [0.7, 0.3]), seed + 10 + i,
              squash=(1.0, rnd.uniform(0.85, 1.0), 0.5), jitter=0.17, flat_bottom=-0.3)
    return m


def oak(h, seed, r_base, crown_r, n_ring, crown_z, spread):
    rnd = random.Random(seed)
    m = mp.Mesh()
    trunk_h = h * 0.36
    prof = [(r_base * 1.25, 0.0), (r_base, trunk_h * 0.18), (r_base * 0.88, trunk_h * 0.6), (r_base * 0.8, trunk_h)]
    m.lathe(prof, 8, 'MP_Bark', offset=0.2)
    mp.jitter_mesh(m, r_base * 0.07, seed)
    for i in range(8):  # keep the base ring flat on the ground after the jitter
        x, y, _ = m.verts[i]; m.verts[i] = (x, y, 0.0)
    top = Vector((0, 0, trunk_h))
    centres = []
    for i in range(n_ring):
        ang = TAU * i / n_ring + rnd.uniform(-0.2, 0.2)
        d = spread * rnd.uniform(0.85, 1.1)
        c = Vector((math.cos(ang) * d, math.sin(ang) * d, crown_z + rnd.uniform(-0.08, 0.08) * h))
        centres.append((c, crown_r * rnd.uniform(0.85, 1.05)))
        branch(m, top - Vector((0, 0, trunk_h * 0.25)), c, r_base * 0.42, r_base * 0.12, 'MP_Bark', seg=6)
    centres.append((Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), crown_z + crown_r * 1.15)), crown_r * 1.15))
    centres.append((Vector((0, 0, crown_z + crown_r * 0.2)), crown_r * 1.05))
    for i, (c, r) in enumerate(centres):
        mat = 'MP_Leaf_Dark' if (i < n_ring and i % 2 == 1) else 'MP_Leaf'
        clump(m, c, r, mat, seed + 20 + i, squash=(1.0, 1.0, rnd.uniform(0.8, 0.95)), jitter=0.15)
    return m


def poplar(h, seed, r_base, r_max, n_clumps, fat):
    rnd = random.Random(seed)
    m = mp.Mesh()
    m.lathe([(r_base * 1.15, 0.0), (r_base, 0.4), (r_base * 0.55, h * 0.55), (r_base * 0.3, h * 0.9)], 7, 'MP_Bark', offset=0.3)
    z0, z1 = h * 0.1, h * 0.985
    for i in range(n_clumps):
        t = i / (n_clumps - 1)
        zc = z0 + (z1 - z0) * t
        r = max(r_max * math.sin(math.pi * t ** 0.75) ** fat, r_max * 0.22)
        if i == n_clumps - 1:
            r = r_max * 0.28
        cx = rnd.uniform(-0.12, 0.12) * r_max; cy = rnd.uniform(-0.12, 0.12) * r_max
        mat = ['MP_Leaf_Light', 'MP_Leaf', 'MP_Leaf_Light', 'MP_Leaf_Dark'][i % 4]
        sz = 1.55 if i == n_clumps - 1 else rnd.uniform(1.25, 1.5)
        clump(m, (cx, cy, zc), r, mat, seed + 30 + i, squash=(0.95, 0.95, sz), jitter=0.15)
    return m


def apple(h, seed, r_base, crown_r, n_limbs, spread, fruit_r, n_fruit):
    rnd = random.Random(seed)
    m = mp.Mesh()
    trunk_h = h * 0.28
    pts = [(0, 0, 0), (0, 0, trunk_h * 0.5), (0.05 * h, 0.02 * h, trunk_h)]
    tube(m, pts, [r_base * 1.2, r_base, r_base * 0.85], 7, 'MP_Bark')
    top = Vector(pts[-1])
    centres = []
    for i in range(n_limbs):
        ang = TAU * i / n_limbs + rnd.uniform(-0.3, 0.3)
        d = spread * rnd.uniform(0.8, 1.15)
        c = Vector((top.x + math.cos(ang) * d, top.y + math.sin(ang) * d, h * 0.56 + rnd.uniform(-0.05, 0.05) * h))
        branch(m, top - Vector((0, 0, trunk_h * 0.2)), c, r_base * 0.55, r_base * 0.15, 'MP_Bark', seg=5)
        centres.append((c, crown_r * rnd.uniform(0.85, 1.05)))
    centres.append((top + Vector((0, 0, h * 0.42)), crown_r * 1.1))
    for i, (c, r) in enumerate(centres):
        clump(m, c, r, pick(rnd, ['MP_Leaf', 'MP_Leaf_Dark'], [0.75, 0.25]), seed + 40 + i,
              squash=(1.0, 1.0, 0.85), jitter=0.14)
    # fruit: sitting on the clump surfaces, biased outward / down so they read from street level
    for i in range(n_fruit):
        c, r = centres[i % len(centres)]
        ang = TAU * rnd.random()
        el = rnd.uniform(-0.6, 0.35)
        d = Vector((math.cos(ang) * math.cos(el), math.sin(ang) * math.cos(el), math.sin(el)))
        p = c + d * (r * 0.92)
        m.blob(fruit_r, 'MP_Fruit_Red', M=mp.T(*p), subdiv=1, jitter=0.05, seed=seed + 70 + i)
    return m


def palm(h, seed, lean, r_trunk, n_seg, n_fronds, frond_len, frond_w, n_nuts):
    rnd = random.Random(seed)
    m = mp.Mesh()
    pts = [Vector((0, 0, 0)), Vector((0, 0, h * 0.09))]
    for i in range(2, n_seg + 1):
        t = i / n_seg
        pts.append(Vector((lean * h * t ** 1.9, 0.015 * h * math.sin(t * 3 + seed) * t, h * 0.88 * t)))
    # segmented trunk: each segment is a closed truncated cone slightly wider at its top
    for i in range(n_seg):
        t = i / n_seg
        r = r_trunk * (1 - 0.35 * t)
        ov = (pts[i + 1] - pts[i]).normalized() * r * 0.3
        m.cyl_between(pts[i] if i == 0 else pts[i] - ov, pts[i + 1], r * 0.82, 7, 'MP_Bark_Palm', r1=r * 1.08)
    top = pts[-1]
    tdir = (pts[-1] - pts[-2]).normalized()
    crown = top + tdir * r_trunk * 0.3
    m.blob(r_trunk * 1.35, 'MP_Bark_Palm', M=mp.T(*crown), subdiv=2, jitter=0.1, seed=seed + 1)
    # fronds: a radial drooping ring + a few shorter upright ones in the middle
    def frond(ang, pitch0, L, W, droop, seed_i):
        rs = random.Random(seed_i)
        n = 7
        spine, widths = [], []
        dx, dy = math.cos(ang), math.sin(ang)
        for j in range(n):
            s = j / (n - 1)
            horiz = L * s
            z = L * (math.tan(pitch0) * s - droop * s * s)
            spine.append(crown + Vector((dx * horiz, dy * horiz, z)))
            widths.append(max(W * math.sin(math.pi * s ** 0.8) ** 0.9, 0.04) + 0.015)
        ribbon(m, spine, widths, 'MP_Leaf_Palm', fold=0.6, thick=0.035)

    for i in range(n_fronds):
        ang = TAU * i / n_fronds + rnd.uniform(-0.15, 0.15)
        frond(ang, math.radians(rnd.uniform(22, 40)), frond_len * rnd.uniform(0.9, 1.05), frond_w, rnd.uniform(1.25, 1.55), seed + 200 + i)
    for i in range(3):
        ang = TAU * i / 3 + 0.4 + rnd.uniform(-0.2, 0.2)
        frond(ang, math.radians(rnd.uniform(48, 58)), frond_len * 0.55, frond_w * 0.8, rnd.uniform(1.3, 1.5), seed + 300 + i)
    for i in range(n_nuts):
        ang = TAU * i / n_nuts + 0.9
        p = crown + Vector((math.cos(ang) * r_trunk * 1.1, math.sin(ang) * r_trunk * 1.1, -r_trunk * 0.9))
        m.blob(r_trunk * 0.5, 'MP_Wood_Dark', M=mp.T(*p), subdiv=1, jitter=0.05, seed=seed + 400 + i)
    return m


# ------------------------------------------------------------------ assets
SPECS = [
    ('TR_Birch_A', lambda: birch(12.0, 11, n_clumps=8, crown_from=5.0, lean=0.05, r_base=0.34, clump_r=1.2),
     'Birch, large (~12 m). White trunk with black per-face marks, slim, airy crown of elongated clumps. Forest staple.'),
    ('TR_Birch_B', lambda: birch(8.0, 12, n_clumps=6, crown_from=3.0, lean=0.09, r_base=0.24, clump_r=0.95),
     'Birch, small (~8 m), young and more leaning, fewer and relatively bigger clumps.'),
    ('TR_Pine_A', lambda: pine(14.0, 21, n_pads=5, lean=0.03, r_base=0.42, pad_r=2.1, crown_from=7.5),
     'Scots pine, large (~14 m): tall bare trunk, flat cloud-like needle pads on upward branches, dome top. Forest staple.'),
    ('TR_Pine_B', lambda: pine(9.0, 22, n_pads=3, lean=0.06, r_base=0.3, pad_r=1.7, crown_from=4.2),
     'Scots pine, small (~9 m): shorter trunk, bigger top dome relative to height, 3 side pads.'),
    ('TR_Oak_A', lambda: oak(11.0, 31, r_base=0.55, crown_r=2.3, n_ring=5, crown_z=6.6, spread=2.6),
     'Oak, large (~11 m): thick flared trunk, 5 limbs, wide heavy round crown.'),
    ('TR_Oak_B', lambda: oak(7.0, 32, r_base=0.42, crown_r=1.75, n_ring=4, crown_z=4.0, spread=1.9),
     'Oak, small (~7 m): squatter, 4 limbs, crown relatively wider.'),
    ('TR_Poplar_A', lambda: poplar(16.0, 41, r_base=0.3, r_max=1.75, n_clumps=9, fat=0.55),
     'Lombardy poplar, large (~16 m): columnar spire of stacked elongated clumps.'),
    ('TR_Poplar_B', lambda: poplar(11.0, 42, r_base=0.22, r_max=1.45, n_clumps=7, fat=0.45),
     'Lombardy poplar, small (~11 m): a bit plumper in proportion.'),
    ('TR_AppleTree_A', lambda: apple(5.0, 51, r_base=0.24, crown_r=1.25, n_limbs=4, spread=1.3, fruit_r=0.21, n_fruit=12),
     'Apple tree, large (~5 m): short bent trunk, 4 limbs, low wide crown with red fruit blobs on the surface.'),
    ('TR_AppleTree_B', lambda: apple(3.5, 52, r_base=0.19, crown_r=0.95, n_limbs=3, spread=0.95, fruit_r=0.17, n_fruit=9),
     'Apple tree, small (~3.5 m): 3 limbs, fewer fruit.'),
    ('TR_Palm_A', lambda: palm(9.0, 61, lean=0.22, r_trunk=0.32, n_seg=8, n_fronds=9, frond_len=3.6, frond_w=0.6, n_nuts=3),
     'Palm, large (~9 m): curved segmented trunk, 9 drooping fronds + 3 upright, 3 coconuts. Beach / elite hill.'),
    ('TR_Palm_B', lambda: palm(6.0, 62, lean=0.12, r_trunk=0.28, n_seg=6, n_fronds=8, frond_len=2.9, frond_w=0.52, n_nuts=2),
     'Palm, small (~6 m): straighter and stubbier, 8 fronds, 2 coconuts.'),
]

for name, build, notes in SPECS:
    mesh = build()
    ob = fam.make_object(name, mesh)
    fam.add_asset(name, [ob], budget=1500, notes=notes, row=0 if name.endswith('_B') else 1)  # small variants in front

report = fam.finish(lineup_gap=2.5, row_gap=4.0, render=False)


# ------------------------------------------------------------------ previews (lineup + close-up groups; studio only, nothing exported)
def objs_of(names):
    return [o for a in fam.assets if a['name'] in names for o in a['objects']]


def showcase(fname, names, direction, elev, res=(1400, 1000), lens=50, gap=1.5):
    """Render a few assets as isolated linked copies (Showcase_NotExported) so neighbouring rows do not clutter the shot."""
    copies, x = [], 0.0
    for n in names:
        r = fam.report['assets'][n]
        x += -r['bounds_min'][0]
        copies.append(fam.place_copy(n, x, 0.0))
        x += r['bounds_max'][0] + gap
    objs = fam.showcase_only(True)
    fam.render_previews(camera=[(fname, direction, elev, res, lens)], frame_objects=objs, person_at=(-2.0, 0, 0))
    fam.showcase_only(False)
    for c in copies:
        bpy.data.objects.remove(c)


if not fam.args.no_render:
    fam.render_previews(camera=[('01_lineup_front.png', 270, 6, (2200, 900), 50),
                                ('02_lineup_three_quarter.png', 245, 16, (2200, 1000), 50)])
    showcase('03_birch_pine.png', ['TR_Birch_A', 'TR_Birch_B', 'TR_Pine_A', 'TR_Pine_B'], 255, 9)
    showcase('04_oak_poplar.png', ['TR_Oak_A', 'TR_Oak_B', 'TR_Poplar_A', 'TR_Poplar_B'], 255, 9)
    showcase('05_apple_palm.png', ['TR_AppleTree_A', 'TR_AppleTree_B', 'TR_Palm_A', 'TR_Palm_B'], 255, 9)
    showcase('06_street_view.png', ['TR_Birch_B', 'TR_Oak_B', 'TR_AppleTree_B', 'TR_Pine_B'], 262, 2, (1600, 900), 35, gap=3.0)
