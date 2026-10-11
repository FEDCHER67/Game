"""STYLE_KIT_v2 house library (v02b): the facade grammar of STYLE_BIBLE_v2 section 7 as reusable bpy-free geometry.

Used by HOUSES/build_houses.py (hand-set reference buildings) and HOUSES_PLAN/build_plan_houses.py (one model per
plan building of the trial region - a preview of the ProceduralBuilding roll-out). Everything is built from closed,
outward-wound shells in a stylekit2.Mesh; colours are bible swatches or bible-3.3 pattern maps ('PT_Brick_v2|brick').

Conventions: house frame = Blender metres, Z up, front facade at -Y, pivot = centre of the footprint on the ground.
Body sides: 0 front (-Y), 1 right (+X), 2 back (+Y), 3 left (-X); u runs left -> right seen from outside, v = z.

v02b additions (critique of the 2026-10-07 trial frame):
  * doors: two recessed panels (leaf.dark) framed by stiles and rails, a handle, chalk casing; canopy or fanlight;
  * one accent per house: flower boxes or shutters (recipe accent), never both;
  * cross gables / dormers are closed volumes with side cheeks and a back wall (no floating ridge bar, no white wedge);
  * a cornice is a ring around the walls, never a slab through the roof deck (mid-rise z-fight);
  * terracotta slopes, brick and plank walls and panel seams use the bible-3.3 pattern maps (mip-mapped in Unity)
    instead of thin geometry strips;
  * panel blocks: open balconies with panel parapets, a third glazed, ink doors under concrete canopies, a dark
    asphalt plinth, blank end walls; towers: cream podium + glazed shaft with a chalk grid (bible 2.7).
"""
import math
import zlib

import stylekit2 as sk
from mathutils import Vector, Matrix

ROOF_TILE = 'PT_RoofTile_v2'
BRICK = 'PT_Brick_v2'
PLANKS = 'PT_Planks_v2'
SEAMS = 'PT_PanelSeams_v2'


def h32(*parts):
    """Stable 32-bit hash (crc32) of the joined parts - the only 'random' source: a template choice per building id."""
    return zlib.crc32('|'.join(str(p) for p in parts).encode('utf-8'))


def lstar(name):
    r, g, b = sk.srgb_to_linear(sk.SWATCH[name])
    Y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    f = Y ** (1 / 3) if Y > 216 / 24389 else (24389 / 27 * Y + 16) / 116
    return 116 * f - 16


def dark(col):
    """The .dark ramp step of a swatch when the bible has one (accents and core), else the swatch itself."""
    base = sk.pattern_parts(col)[1] if sk.is_pattern(col) else col
    base = base.split('.')[0]
    return base + '.dark' if base + '.dark' in sk.SWATCH else base


def light(col):
    base = (sk.pattern_parts(col)[1] if sk.is_pattern(col) else col).split('.')[0]
    return base + '.light' if base + '.light' in sk.SWATCH else base


def wall_paint(sw):
    """Wall colour -> face colour: brick and wood walls carry their bible-3.3 pattern map."""
    if sw == 'brick':
        return f'{BRICK}|brick'
    if sw == 'wood':
        return f'{PLANKS}|wood'
    return sw


def roof_paint(sw):
    return f'{ROOF_TILE}|terracotta' if sw == 'terracotta' else sw


def bays(L, pitch, w, margin=0.9, odd=False):
    """Window centres along a wall of length L (centred coordinates): as many as fit with `margin` to the corners."""
    n = max(1, int(math.floor((L - 2 * margin - w) / pitch + 1e-9)) + 1)
    if odd and n % 2 == 0:
        n -= 1
    return [(k - (n - 1) / 2) * pitch for k in range(n)]


# ---------------------------------------------------------------- the facade grid body
class Body:
    """Closed box (-W/2..W/2, -D/2..D/2, z0..z1) whose walls are cut into a grid. Openings are rectangles in (u, v)
    pushed in by `depth` (inner face + four reveals); paint rectangles recolour flush wall areas. Cells of one colour
    merge into maximal rectangles, T-junctions are removed and n-gons ear-clipped: one closed shell."""

    def __init__(self, W, D, z0, z1, wall, top='grey', bottom='asphalt', reveal='chalk', pat_origin=None):
        self.W, self.D, self.z0, self.z1 = W, D, z0, z1
        self.wall, self.top, self.bottom, self.reveal = wall, top, bottom, reveal
        self.pat_origin = pat_origin
        self.open = {0: [], 1: [], 2: [], 3: []}
        self.paint = {0: [], 1: [], 2: [], 3: []}
        self.vcuts = {0: set(), 1: set(), 2: set(), 3: set()}
        self.ucuts = {0: set(), 1: set(), 2: set(), 3: set()}

    def L(self, side):
        return self.W if side in (0, 2) else self.D

    def frame(self, side):
        W, D = self.W, self.D
        return {0: (Vector((-W / 2, -D / 2, 0)), Vector((1, 0, 0)), Vector((0, -1, 0))),
                1: (Vector((W / 2, -D / 2, 0)), Vector((0, 1, 0)), Vector((1, 0, 0))),
                2: (Vector((W / 2, D / 2, 0)), Vector((-1, 0, 0)), Vector((0, 1, 0))),
                3: (Vector((-W / 2, D / 2, 0)), Vector((0, -1, 0)), Vector((-1, 0, 0)))}[side]

    def P(self, side, u, v, n=0.0):
        o, ud, nd = self.frame(side)
        return o + ud * u + Vector((0, 0, v)) + nd * n

    def matrix(self, side):
        """Local frame of a side: X = u, Y = inward, Z = up, origin at u = 0 on the wall plane."""
        o, ud, nd = self.frame(side)
        M = Matrix((ud, -nd, Vector((0, 0, 1)))).transposed().to_4x4()
        M.translation = o
        return M

    def u_of(self, side, c):
        return self.L(side) / 2 + c

    def opening(self, side, c, w, v0, v1, fill, depth=0.15):
        """fill: swatch, or [(v_from, swatch), ...] bottom-up (door + transom)."""
        u0, u1 = self.u_of(side, c) - w / 2, self.u_of(side, c) + w / 2
        self.open[side].append((u0, u1, v0, v1, fill, depth))
        self.ucuts[side] |= {u0, u1}
        self.vcuts[side] |= {v0, v1}
        return u0, u1

    def paint_rect(self, side, c, w, v0, v1, col):
        u0, u1 = self.u_of(side, c) - w / 2, self.u_of(side, c) + w / 2
        self.paint[side].append((u0, u1, v0, v1, col))
        self.ucuts[side] |= {u0, u1}
        self.vcuts[side] |= {v0, v1}

    @staticmethod
    def _clean(vals, lo, hi):
        out = []
        for v in sorted(v for v in vals if lo - 1e-9 <= v <= hi + 1e-9):
            if not out or v - out[-1] > 1e-4:
                out.append(v)
        return out

    def _faces(self):
        polys = []
        for side in range(4):
            L = self.L(side)
            us = self._clean({0.0, L} | self.ucuts[side], 0.0, L)
            zs = self._clean({self.z0, self.z1} | self.vcuts[side], self.z0, self.z1)
            ops = self.open[side]
            nu, nv = len(us) - 1, len(zs) - 1
            label = [[None] * nv for _ in range(nu)]
            for i in range(nu):
                for j in range(nv):
                    uc, vc = (us[i] + us[i + 1]) / 2, (zs[j] + zs[j + 1]) / 2
                    if any(o[0] <= uc <= o[1] and o[2] <= vc <= o[3] for o in ops):
                        continue
                    col = self.wall
                    for pu0, pu1, pv0, pv1, pc in self.paint[side]:
                        if pu0 <= uc <= pu1 and pv0 <= vc <= pv1:
                            col = pc
                    label[i][j] = col
            used = [[False] * nv for _ in range(nu)]
            for j in range(nv):
                for i in range(nu):
                    c = label[i][j]
                    if c is None or used[i][j]:
                        continue
                    i1 = i
                    while i1 + 1 < nu and not used[i1 + 1][j] and label[i1 + 1][j] == c:
                        i1 += 1
                    j1 = j
                    while j1 + 1 < nv and all(not used[k][j1 + 1] and label[k][j1 + 1] == c for k in range(i, i1 + 1)):
                        j1 += 1
                    for k in range(i, i1 + 1):
                        for l in range(j, j1 + 1):
                            used[k][l] = True
                    a, b, v0, v1 = us[i], us[i1 + 1], zs[j], zs[j1 + 1]
                    polys.append(([self.P(side, a, v0), self.P(side, b, v0), self.P(side, b, v1), self.P(side, a, v1)], c))
            for (u0, u1, v0, v1, fill, dep) in ops:
                parts = [(v0, fill)] if not isinstance(fill, list) else fill
                bands = [(max(vf, v0), parts[k + 1][0] if k + 1 < len(parts) else v1, col) for k, (vf, col) in enumerate(parts)]
                for a, b, col in bands:
                    polys.append(([self.P(side, u0, a, -dep), self.P(side, u1, a, -dep), self.P(side, u1, b, -dep),
                                   self.P(side, u0, b, -dep)], col))
                r = self.reveal
                polys.append(([self.P(side, u0, v0), self.P(side, u1, v0), self.P(side, u1, v0, -dep), self.P(side, u0, v0, -dep)], r))
                polys.append(([self.P(side, u0, v1), self.P(side, u0, v1, -dep), self.P(side, u1, v1, -dep), self.P(side, u1, v1)], r))
                polys.append(([self.P(side, u0, v0), self.P(side, u0, v0, -dep), self.P(side, u0, v1, -dep), self.P(side, u0, v1)], r))
                polys.append(([self.P(side, u1, v0), self.P(side, u1, v1), self.P(side, u1, v1, -dep), self.P(side, u1, v0, -dep)], r))
        W, D, z0, z1 = self.W, self.D, self.z0, self.z1
        polys.append(([Vector((-W / 2, -D / 2, z1)), Vector((W / 2, -D / 2, z1)), Vector((W / 2, D / 2, z1)), Vector((-W / 2, D / 2, z1))], self.top))
        polys.append(([Vector((-W / 2, -D / 2, z0)), Vector((-W / 2, D / 2, z0)), Vector((W / 2, D / 2, z0)), Vector((W / 2, -D / 2, z0))], self.bottom))
        return polys

    def build(self, m, M=None, name='body'):
        polys = self._faces()
        verts, index = [], {}

        def key(p):
            return (int(round(p.x * 1e4)), int(round(p.y * 1e4)), int(round(p.z * 1e4)))

        def vid(p):
            k = key(p)
            if k not in index:
                index[k] = len(verts)
                verts.append(Vector(p))
            return index[k]
        faces = [[vid(p) for p in poly] for poly, _ in polys]
        cols = [c for _, c in polys]
        keys = [key(v) for v in verts]
        lines = ({}, {}, {})
        for i, k in enumerate(keys):
            for ax in range(3):
                rest = tuple(k[a] for a in range(3) if a != ax)
                lines[ax].setdefault(rest, []).append((k[ax], i))
        for d in lines:
            for lst in d.values():
                lst.sort()
        out_faces = []
        for f in faces:
            ring = []
            for k in range(len(f)):
                a, b = f[k], f[(k + 1) % len(f)]
                ring.append(a)
                ka, kb = keys[a], keys[b]
                diff = [ax for ax in range(3) if ka[ax] != kb[ax]]
                if len(diff) != 1:
                    continue
                ax = diff[0]
                rest = tuple(ka[q] for q in range(3) if q != ax)
                lo, hi = sorted((ka[ax], kb[ax]))
                mids = [(c, i) for c, i in lines[ax].get(rest, []) if lo < c < hi]
                if ka[ax] > kb[ax]:
                    mids = mids[::-1]
                ring += [i for _, i in mids]
            out_faces.append(ring)
        tri_faces, tri_cols = [], []
        for f, c in zip(out_faces, cols):
            if len(f) <= 4:
                tri_faces.append(tuple(f))
                tri_cols.append(c)
                continue
            for t in sk.ear_clip([verts[i] for i in f]):
                tri_faces.append(tuple(f[i] for i in t))
                tri_cols.append(c)
        m.shell([tuple(v) for v in verts], tri_faces, self.wall, M, cols=tri_cols, normals='flat', kind='hard',
                member=min(self.W, self.D), name=name, pat_origin=self.pat_origin)


# ---------------------------------------------------------------- the house kit (trims, windows, doors, roofs)
class House:
    def __init__(self, W, D, z1, rc, plinth=0.5, floor=3.2, ground_floor=None, pat_origin=None):
        """rc: recipe dict (wall, roof, trim, plinth, door, accent, deck, frame ...)."""
        self.m = sk.Mesh()
        self.W, self.D, self.z1, self.rc = W, D, z1, rc
        self.plinth, self.floor = plinth, floor
        self.gf = ground_floor or floor
        self.wallc = wall_paint(rc['wall'])
        self.body = Body(W, D, 0.0, z1, self.wallc, top=rc.get('deck', 'grey'), bottom=rc['plinth'], pat_origin=pat_origin)
        self.later = []
        self.frame = rc.get('frame') or rc['trim']

    def floor_z(self, f):
        return self.plinth + (0 if f == 0 else self.gf + (f - 1) * self.floor)

    def sbox(self, side, u0, u1, v0, v1, n0, n1, col, **kw):
        M = self.body.matrix(side) @ sk.T((u0 + u1) / 2, -(n0 + n1) / 2, (v0 + v1) / 2)
        kw.setdefault('kind', 'relief' if n1 <= 0.32 else 'hard')
        kw.setdefault('member', max(min(u1 - u0, v1 - v0), 0.0) if kw['kind'] == 'relief' else min(u1 - u0, v1 - v0, n1 - n0))
        return self.m.box(u1 - u0, n1 - n0, v1 - v0, col, M=M, **kw)

    # -- openings
    def window(self, side, c, f, w=1.2, h=1.8, sill_h=0.9, glass='glass', cross=True, lintel=False, sill=True,
               casing=True):
        z = self.floor_z(f) + sill_h
        u0, u1 = self.body.opening(side, c, w, z, z + h, glass, depth=0.15)
        trim = self.frame
        fw = 0.12

        def deco():
            if casing:
                self.sbox(side, u0 - fw, u1 + fw, z + h, z + h + fw, -0.01, 0.03, trim)
                self.sbox(side, u0 - fw, u0, z, z + h, -0.01, 0.03, trim)
                self.sbox(side, u1, u1 + fw, z, z + h, -0.01, 0.03, trim)
            if sill:
                self.sbox(side, u0 - fw - 0.08, u1 + fw + 0.08, z - 0.10, z, -0.02, 0.12, trim, kind='hard', member=0.10)
            if lintel:
                self.sbox(side, u0 - fw - 0.10, u1 + fw + 0.10, z + h + fw, z + h + fw + 0.15, -0.02, 0.10, trim,
                          kind='hard', member=0.10)
            self.sbox(side, (u0 + u1) / 2 - 0.04, (u0 + u1) / 2 + 0.04, z, z + h, -0.16, -0.10, trim, kind='relief', member=0.08)
            if cross:
                self.sbox(side, u0, u1, z + h * 2 / 3 - 0.04, z + h * 2 / 3 + 0.04, -0.16, -0.10, trim, kind='relief', member=0.08)
        self.later.append(deco)
        return u0, u1, z

    def door(self, side, c, w=1.2, h=2.6, transom=2.1, leaf=None, steps=2, canopy=None, arch=False, columns=False,
             z=None):
        """v02b: a real door - two recessed panels (leaf.dark) framed by stiles and rails in the leaf colour, a brass
        handle (mustard), chalk casing, paving steps; optional canopy (roof-colour slab on brackets, or a civic slab on
        two chalk columns) or a chalk fanlight arch."""
        z = self.floor_z(0) if z is None else z
        leaf = leaf or self.rc['door']
        low = 'ink' if leaf == 'ink' else dark(leaf)
        hi = 'ink.light' if leaf == 'ink' else leaf
        top = z + (transom if transom else h)
        fill = [(z, low), (top, 'glass.light')] if transom else low
        u0, u1 = self.body.opening(side, c, w, z, z + h, fill, depth=0.12)
        trim = self.rc['trim']

        def deco():
            fw = 0.12
            self.sbox(side, u0 - fw, u1 + fw, z + h, z + h + fw, -0.01, 0.04, trim)
            self.sbox(side, u0 - fw, u0, z - 0.02, z + h, -0.01, 0.04, trim)
            self.sbox(side, u1, u1 + fw, z - 0.02, z + h, -0.01, 0.04, trim)
            if transom:
                self.sbox(side, u0, u1, top - 0.04, top + 0.04, -0.13, -0.07, trim, kind='relief', member=0.08)
            # leaf: stiles and rails 0.04 proud of the recessed panels
            n0, n1 = -0.12, -0.08
            st = 0.12
            self.sbox(side, u0, u0 + st, z, top, n0, n1, hi, kind='relief', member=0.08)
            self.sbox(side, u1 - st, u1, z, top, n0, n1, hi, kind='relief', member=0.08)
            self.sbox(side, u0 + st, u1 - st, z, z + 0.20, n0, n1, hi, kind='relief', member=0.08)
            zm = z + (top - z) * 0.46
            self.sbox(side, u0 + st, u1 - st, zm - 0.07, zm + 0.07, n0, n1, hi, kind='relief', member=0.08)
            self.sbox(side, u0 + st, u1 - st, top - 0.13, top, n0, n1, hi, kind='relief', member=0.08)
            if w >= 1.35:                                    # double door: centre stile, handles in the middle
                um = (u0 + u1) / 2
                self.sbox(side, um - 0.05, um + 0.05, z, top, n0, n1, hi, kind='relief', member=0.08)
                for hu in (um - 0.16, um + 0.10):
                    self.sbox(side, hu, hu + 0.06, z + 1.0, z + 1.18, n1, n1 + 0.05, 'mustard', kind='relief', member=0.06)
            else:
                self.sbox(side, u1 - st - 0.12, u1 - st - 0.06, z + 1.0, z + 1.18, n1, n1 + 0.05, 'mustard', kind='relief',
                          member=0.06)
            for s in range(steps):
                tz = z - 0.15 * s
                if tz <= 0.02:
                    break
                self.sbox(side, u0 - 0.35 - 0.1 * s, u1 + 0.35 + 0.1 * s, 0.0, tz, -0.02, 0.32 + 0.3 * s, 'paving', kind='hard')
            if canopy:
                cw, cd = canopy
                zc = z + h + fw + 0.25
                uc = (u0 + u1) / 2
                if columns:                                 # civic: slab on two chalk columns (bible 7.1)
                    self.sbox(side, uc - cw / 2, uc + cw / 2, zc, zc + 0.18, -0.02, cd, 'grey', kind='hard', member=0.18)
                    self.sbox(side, uc - cw / 2 - 0.03, uc + cw / 2 + 0.03, zc + 0.18, zc + 0.24, -0.02, cd + 0.03, trim,
                              kind='hard', member=0.06)
                    for cu in (uc - cw / 2 + 0.25, uc + cw / 2 - 0.25):
                        M = self.body.matrix(side) @ sk.T(cu, -(cd - 0.25), 0.0)
                        self.m.cyl(0.125, zc, 10, trim, M=M, normals='soft', kind='hard', member=0.25)
                else:
                    self.sbox(side, uc - cw / 2, uc + cw / 2, zc, zc + 0.12, -0.02, cd, self.rc.get('canopy', self.rc['roof_c']),
                              kind='hard', member=0.12)
                    for bu in (uc - cw / 2 + 0.15, uc + cw / 2 - 0.27):
                        self.bracket(side, bu, bu + 0.12, zc, cd * 0.8)
            if arch:
                self.half_ring(side, (u0 + u1) / 2, z + h + fw, w / 2 + fw, w / 2, trim)
        self.later.append(deco)
        return u0, u1

    def shopfront(self, side, c, w, h=2.45, sill=0.55, mullions=2):
        z0 = self.floor_z(0)
        u0, u1 = self.body.opening(side, c, w, z0 + sill, z0 + h, 'glass', depth=0.15)
        t = self.frame

        def deco():
            self.sbox(side, u0 - 0.10, u1 + 0.10, z0 + h, z0 + h + 0.10, -0.01, 0.04, t)
            self.sbox(side, u0 - 0.10, u0, z0 + sill - 0.10, z0 + h, -0.01, 0.04, t)
            self.sbox(side, u1, u1 + 0.10, z0 + sill - 0.10, z0 + h, -0.01, 0.04, t)
            self.sbox(side, u0 - 0.10, u1 + 0.10, z0 + sill - 0.20, z0 + sill, -0.02, 0.08, t, kind='hard', member=0.2)
            for k in range(1, mullions + 1):
                um = u0 + (u1 - u0) * k / (mullions + 1)
                self.sbox(side, um - 0.04, um + 0.04, z0 + sill, z0 + h, -0.16, -0.10, t, kind='relief', member=0.08)
        self.later.append(deco)
        return u0, u1

    # -- accents (one per house)
    def shutters(self, side, u0, u1, z, h, col):
        """A pair of louvred shutters beside a window: 0.45 m x window height, 0.04 m proud, two dark rails."""
        for a, b in ((u0 - 0.12 - 0.47, u0 - 0.12 - 0.02), (u1 + 0.12 + 0.02, u1 + 0.12 + 0.47)):
            self.sbox(side, a, b, z, z + h, -0.01, 0.05, col, kind='relief', member=0.45)
            for f in (0.33, 0.66):
                self.sbox(side, a + 0.05, b - 0.05, z + h * f - 0.03, z + h * f + 0.03, 0.05, 0.07, dark(col),
                          kind='relief', member=0.06)

    def flower_box(self, side, u0, u1, z, col, bloom):
        """Window box on the sill: accent box, a band of leaves, four flower heads of one colour."""
        a, b = u0 - 0.10, u1 + 0.10
        self.sbox(side, a, b, z - 0.06, z + 0.18, 0.12, 0.36, col, kind='hard', member=0.22)
        self.sbox(side, a + 0.04, b - 0.04, z + 0.18, z + 0.30, 0.15, 0.33, 'leaf', kind='hard', member=0.12)
        M0 = self.body.matrix(side)
        for k in range(4):
            uu = a + (b - a) * (k + 0.5) / 4
            self.m.bipyramid(0.075, 0.13, 6, bloom, at=tuple(M0 @ Vector((uu, -0.24, z + 0.33))), member=0.13)

    # -- small parts
    def bracket(self, side, u0, u1, ztop, depth):
        poly = [(0.0, ztop), (0.0, ztop - depth), (depth, ztop)]
        M = self.body.matrix(side) @ sk.T((u0 + u1) / 2, 0, 0) @ sk.R(-90, 'Z')
        self.m.prism([(n, z) for n, z in poly], u1 - u0, self.rc['trim'], M=M, kind='hard', member=0.12)

    def half_ring(self, side, uc, zb, r_out, r_in, col, seg=8):
        disc = [(0.0, 0.0)] + [(r_in * math.cos(math.pi * k / seg), r_in * math.sin(math.pi * k / seg)) for k in range(seg + 1)]
        for k in range(seg):
            a0, a1 = math.pi * k / seg, math.pi * (k + 1) / seg
            q = [(r_in * math.cos(a0), r_in * math.sin(a0)), (r_out * math.cos(a0), r_out * math.sin(a0)),
                 (r_out * math.cos(a1), r_out * math.sin(a1)), (r_in * math.cos(a1), r_in * math.sin(a1))]
            self.wall_poly(side, uc, zb, q, -0.01, 0.04, col)
        self.wall_poly(side, uc, zb, disc[1:] + [disc[0]], -0.01, 0.02, 'glass.light')

    def wall_poly(self, side, uc, zb, poly, n0, n1, col, kind='relief'):
        o, ud, nd = self.body.frame(side)
        base = o + ud * uc
        verts = [tuple(base + ud * du + Vector((0, 0, zb + dz)) + nd * n0) for du, dz in poly] + \
                [tuple(base + ud * du + Vector((0, 0, zb + dz)) + nd * n1) for du, dz in poly]
        n = len(poly)
        area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
        idx = list(range(n)) if area > 0 else list(range(n))[::-1]
        faces = [tuple(n + i for i in idx), tuple(idx[::-1])]
        for a, b in zip(idx, idx[1:] + idx[:1]):
            faces.append((a, b, n + b, n + a))
        self.m.shell(verts, faces, col, normals='flat', kind=kind, member=0.12)

    def oculus(self, side, uc, zc, r=0.42, col=None):
        col = col or self.rc['trim']
        seg = 12
        for k in range(seg):
            a0, a1 = sk.TAU * k / seg, sk.TAU * (k + 1) / seg
            q = [((r - 0.12) * math.cos(a0), (r - 0.12) * math.sin(a0)), (r * math.cos(a0), r * math.sin(a0)),
                 (r * math.cos(a1), r * math.sin(a1)), ((r - 0.12) * math.cos(a1), (r - 0.12) * math.sin(a1))]
            self.wall_poly(side, uc, zc, q, -0.01, 0.05, col)
        disc = [((r - 0.1) * math.cos(sk.TAU * k / seg), (r - 0.1) * math.sin(sk.TAU * k / seg)) for k in range(seg)]
        self.wall_poly(side, uc, zc, disc, -0.01, 0.02, 'glass')

    # -- whole-building trims
    def plinth_box(self):
        p, W, D = self.plinth, self.W, self.D
        self.m.box(W + 0.1, D + 0.1, p, self.rc['plinth'], base=True, member=p)
        self.m.box(W + 0.14, D + 0.14, 0.06, self.rc['plinth'], at=(0, 0, p - 0.03), member=0.06)

    def pilasters(self, z_top, w=0.40, proud=0.04):
        W, D = self.W, self.D
        for sx in (-1, 1):
            for sy in (-1, 1):
                x0, x1 = sorted((sx * (W / 2 - w), sx * (W / 2 + proud)))
                y0, y1 = sorted((sy * (D / 2 - w), sy * (D / 2 + proud)))
                self.m.box_between((x0, y0, self.plinth), (x1, y1, z_top), self.rc['trim'], kind='relief', member=w)

    def band(self, z, h=0.22, proud=0.08, col=None):
        self.m.box(self.W + 2 * proud, self.D + 2 * proud, h, col or self.rc['trim'], at=(0, 0, z), kind='relief', member=h)

    def cornice(self, z_top, h=0.35, out=0.25, col=None):
        """v02b: the cornice is a ring around the walls (top at z_top - 0.02), never a slab through the roof deck."""
        ring_xy(self.m, -self.W / 2, -self.D / 2, self.W / 2, self.D / 2, out, z_top - h - 0.02, z_top - 0.02,
                col or self.rc['trim'], out=out, kind='relief', name='cornice')

    def parapet(self, z_top, ph=0.8, cap=True):
        ring_xy(self.m, -self.W / 2, -self.D / 2, self.W / 2, self.D / 2, 0.3, z_top, z_top + ph, self.wallc, kind='hard',
                name='parapet')
        if cap:
            ring_xy(self.m, -self.W / 2, -self.D / 2, self.W / 2, self.D / 2, 0.4, z_top + ph, z_top + ph + 0.15, 'chalk',
                    out=0.1, kind='relief', name='cap')

    def _frame_matrix(self, axis):
        """Roofs are built with the ridge along local X; axis 'y' turns that frame 90 deg (ridge along the depth)."""
        return Matrix.Identity(4) if axis == 'x' else sk.R(90, 'Z')

    def gable_roof(self, pitch, ov=0.5, t=0.18, axis=None, oculus=True):
        """Ridge along X (axis 'x', eaves front and back) or along Y (axis 'y', gables front and back - the gable-front
        town house). Slab = chevron prism: slopes in the roof colour (terracotta carries PT_RoofTile_v2), fascia, soffit
        and bargeboard ends chalk; ridge cap roof.dark; gable walls in the wall colour reach 0.05 into the slab."""
        if axis is None:
            axis = 'x' if self.W >= self.D else 'y'
        L, S = (self.W, self.D) if axis == 'x' else (self.D, self.W)
        z1 = self.z1
        ta = math.tan(math.radians(pitch))
        Y0 = S / 2 + ov
        zE = z1 - ov * ta
        zR = zE + Y0 * ta
        roof = self.rc['roof']
        rp = roof_paint(roof)
        trim = self.rc['trim']
        F = self._frame_matrix(axis)
        sec = [(-Y0, zE), (0.0, zR), (Y0, zE), (Y0, zE + t), (0.0, zR + t), (-Y0, zE + t)]
        sides = [trim, trim, trim, rp, rp, trim]
        self.m.prism(sec, L + 2 * ov, roof, M=F @ sk.R(90, 'Z'), cap=trim, side=sides, kind='hard', member=t, name='roof')
        self.m.box(L + 2 * ov + 0.02, 0.14, 0.14, dark(roof), M=F @ sk.T(0, 0, zR + t) @ sk.R(45, 'X'), kind='hard', member=0.14)
        tri = [(-S / 2, z1), (S / 2, z1), (0.0, zR + 0.05)]
        self.m.prism(tri, L, self.wallc, M=F @ sk.R(90, 'Z'), kind='hard', member=L, name='gable')
        if oculus and zR - z1 > 1.6:
            zc = z1 + (zR - z1) * 0.36
            for side in ((1, 3) if axis == 'x' else (0, 2)):
                self.oculus(side, self.body.L(side) / 2, zc, r=0.42 if zR - z1 > 2.4 else 0.32)
        return zE, zR + t

    def hip_roof(self, pitch, ov=0.5, t=0.18):
        """Solid hipped roof: flat chalk soffit, 0.18 chalk fascia all round, four slopes, ridge along the long side."""
        axis = 'x' if self.W >= self.D else 'y'
        L, S = (self.W, self.D) if axis == 'x' else (self.D, self.W)
        F = self._frame_matrix(axis)
        z1 = self.z1
        ta = math.tan(math.radians(pitch))
        X0, Y0 = L / 2 + ov, S / 2 + ov
        zb, zf = z1 - 0.02, z1 - 0.02 + t
        rise = Y0 * ta
        rx = max(X0 - Y0, 0.0)
        roof, trim = self.rc['roof'], self.rc['trim']
        rp = roof_paint(roof)
        v = [(-X0, -Y0, zb), (X0, -Y0, zb), (X0, Y0, zb), (-X0, Y0, zb),
             (-X0, -Y0, zf), (X0, -Y0, zf), (X0, Y0, zf), (-X0, Y0, zf),
             (-rx, 0.0, zf + rise), (rx, 0.0, zf + rise)]
        f = [(0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
             (4, 5, 9, 8), (6, 7, 8, 9), (5, 6, 9), (7, 4, 8)]
        cols = [trim, trim, trim, trim, trim, rp, rp, rp, rp]
        self.m.shell(v, f, roof, F, cols=cols, normals='flat', kind='hard', member=t, name='roof')
        self.m.box(2 * rx + 0.3, 0.14, 0.14, dark(roof), M=F @ sk.T(0, 0, zf + rise) @ sk.R(45, 'X'), kind='hard', member=0.14)
        return zf, zf + rise

    def roof_surface_z(self, x, y, pitch, ov=0.5, t=0.18, kind='hip'):
        """Height of the top of a hip roof (axis x) over (x, y) - used to bury dormer backs safely."""
        ta = math.tan(math.radians(pitch))
        X0, Y0 = self.W / 2 + ov, self.D / 2 + ov
        zf = self.z1 - 0.02 + t
        return zf + min(Y0 - abs(y), X0 - abs(x)) * ta

    def cross_gable(self, side, c, w, pitch, depth_in, ov=0.35, t=0.16, main_pitch=30):
        """v02b dormer / pediment over a front bay as a CLOSED volume: a house-shaped prism (wall colour) from the
        facade plane back to `depth_in` - its sides are the cheeks, its back wall is buried in the main roof - with a
        small gable roof on top (front bargeboard chalk, back end in the roof colour, never a white wedge)."""
        z1 = self.z1
        ta = math.tan(math.radians(pitch))
        a = w / 2 + 0.2
        X0 = a + 0.05
        zR = z1 + a * ta
        # bury the back: the main hip surface above the dormer ridge at the back end (+0.25 m margin)
        while depth_in < self.D / 2 and self.roof_surface_z(0.0, -self.D / 2 + depth_in, main_pitch) < zR + t + 0.35:
            depth_in += 0.2
        roof, trim = self.rc['roof'], self.rc['trim']
        rp = roof_paint(roof)
        Mside = self.body.matrix(side) @ sk.T(self.body.u_of(side, c), 0, 0)
        house = [(-a, z1 - 0.3), (a, z1 - 0.3), (a, z1), (0.0, zR), (-a, z1)]
        self.m.prism(house, depth_in, self.wallc, M=Mside @ sk.T(0, depth_in / 2, 0), kind='hard', member=w, name='dormer')
        sec = [(-X0, z1 - 0.02), (0.0, zR - 0.02), (X0, z1 - 0.02), (X0, z1 - 0.02 + t), (0.0, zR - 0.02 + t), (-X0, z1 - 0.02 + t)]
        L = depth_in + ov
        n = len(sec)
        # prism along the inward axis; front cap (outside) chalk bargeboard, back cap roof colour
        v = [(x, -ov, z) for x, z in sec] + [(x, depth_in, z) for x, z in sec]
        f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
        cols = [trim, roof]
        side_cols = [trim, trim, trim, rp, rp, trim]
        for i in range(n):
            j = (i + 1) % n
            f.append((i, j, n + j, n + i))
            cols.append(side_cols[i])
        vol = 0.0
        for fa in f:
            p = [Vector(v[i]) for i in fa]
            for q in range(1, len(p) - 1):
                vol += p[0].dot(p[q].cross(p[q + 1])) / 6.0
        if vol < 0:
            f = [tuple(reversed(fa)) for fa in f]
        self.m.shell(v, f, roof, Mside, cols=cols, normals='flat', kind='hard', member=t, name='roof')
        self.m.box(0.14, L + 0.02, 0.14, dark(roof), M=Mside @ sk.T(0, (depth_in - ov) / 2, zR - 0.02 + t) @ sk.R(45, 'Y'),
                   kind='hard', member=0.14)
        return zR

    def shed_roof(self, ov=0.4, t=0.18, rise=None, high='back'):
        """Mono-pitch: a wall-colour wedge on top of the walls and a slab on it (fascia trim), falling to the front."""
        W, D, z1 = self.W, self.D, self.z1
        rise = rise if rise is not None else max(0.6, D * 0.12)
        s = 1 if high == 'back' else -1
        wedge = [(-D / 2, z1), (D / 2, z1), (s * D / 2, z1 + rise)] if s > 0 else [(-D / 2, z1), (D / 2, z1), (-D / 2, z1 + rise)]
        self.m.prism([(y, z) for y, z in wedge], W, self.wallc, M=sk.R(90, 'Z'), kind='hard', member=W, name='wedge')
        ta = rise / D
        y0, y1 = -D / 2 - ov, D / 2 + ov
        z_at = (lambda y: z1 + (y + D / 2) * ta) if s > 0 else (lambda y: z1 + (D / 2 - y) * ta)
        sec = [(y0, z_at(y0)), (y1, z_at(y1)), (y1, z_at(y1) + t), (y0, z_at(y0) + t)]
        roof, trim = self.rc['roof'], self.rc['trim']
        self.m.prism(sec, W + 2 * ov, roof, M=sk.R(90, 'Z'), cap=trim, side=[trim, trim, roof_paint(roof), trim], kind='hard',
                     member=t, name='roof')
        return z1 + rise + t

    def chimney(self, x, y, z_top, z_bottom):
        self.m.box_between((x - 0.3, y - 0.3, z_bottom), (x + 0.3, y + 0.3, z_top), wall_paint('brick'), kind='hard', member=0.6)
        self.m.box_between((x - 0.38, y - 0.38, z_top), (x + 0.38, y + 0.38, z_top + 0.12), 'grey', kind='hard', member=0.12)

    def finish(self):
        self.body.build(self.m)
        for fn in self.later:
            fn()
        return self.m


def ring_xy(m, x0, y0, x1, y1, w, z0, z1, col, out=0.0, **kw):
    """Closed rectangular ring (parapets, caps, cornices): outer edge `out` beyond the rect, `w` wide inward."""
    ox0, oy0, ox1, oy1 = x0 - out, y0 - out, x1 + out, y1 + out
    ix0, iy0, ix1, iy1 = ox0 + w, oy0 + w, ox1 - w, oy1 - w
    O = [(ox0, oy0), (ox1, oy0), (ox1, oy1), (ox0, oy1)]
    I = [(ix0, iy0), (ix1, iy0), (ix1, iy1), (ix0, iy1)]
    v = [(x, y, z0) for x, y in O] + [(x, y, z0) for x, y in I] + [(x, y, z1) for x, y in O] + [(x, y, z1) for x, y in I]
    f = []
    for k in range(4):
        k1 = (k + 1) % 4
        f.append((k, k1, 8 + k1, 8 + k))
        f.append((4 + k1, 4 + k, 12 + k, 12 + k1))
        f.append((8 + k, 8 + k1, 12 + k1, 12 + k))
        f.append((k1, k, 4 + k, 4 + k1))
    kw.setdefault('member', w)
    m.shell(v, f, col, normals='flat', **kw)


def striped_sweep(m, M, sec, us, cols, **kw):
    """Convex section [(n, z)] swept along u through the cuts `us`; segment k takes cols[k]: one closed shell."""
    ns = len(sec)
    verts = []
    for u in us:
        verts += [tuple(M @ Vector((u, -nn, z))) for nn, z in sec]
    cz = sum(z for _, z in sec) / ns
    cn = sum(nn for nn, _ in sec) / ns
    faces, fcols = [], []

    def orient(f, out):
        pts = [Vector(verts[i]) for i in f]
        nrm = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        return f if nrm.dot(out) > 0 else f[::-1]
    for k in range(len(us) - 1):
        for i in range(ns):
            j = (i + 1) % ns
            f = (k * ns + i, k * ns + j, (k + 1) * ns + j, (k + 1) * ns + i)
            mid_n, mid_z = (sec[i][0] + sec[j][0]) / 2 - cn, (sec[i][1] + sec[j][1]) / 2 - cz
            out = M.to_3x3() @ Vector((0, -mid_n, mid_z))
            faces.append(orient(f, out))
            fcols.append(cols[k])
    ax = M.to_3x3() @ Vector((1, 0, 0))
    faces.append(orient(tuple(range(ns)), -ax))
    fcols.append(cols[0])
    last = (len(us) - 1) * ns
    faces.append(orient(tuple(last + i for i in range(ns)), ax))
    fcols.append(cols[-1])
    m.shell(verts, faces, cols[0], cols=fcols, normals='flat', **kw)


def awning(m, B, side, c, w, z, depth, drop, stripes, colours):
    M = B.matrix(side)
    u_mid = B.u_of(side, c)
    us = [u_mid - w / 2 + i * w / stripes for i in range(stripes + 1)]
    sec = [(-0.02, z), (depth, z - drop), (depth, z - drop - 0.22), (depth - 0.06, z - drop - 0.22), (-0.02, z - 0.12)]
    striped_sweep(m, M, sec, us, [colours[i % len(colours)] for i in range(stripes)], kind='relief', member=0.1)


# ---------------------------------------------------------------- archetypes
def glass_for(seed, *k):
    """15-20 % of panes catch the sky (glass.light), by template hash - never random noise."""
    return 'glass.light' if h32(seed, *k) % 100 < 18 else 'glass'


def masonry(sp):
    """oldtown / civic / villa-classic house (bible 7.3): plinth, corner pilasters, floor bands, windows with casings,
    sills, crosses, lintels on the 2nd floor (half the houses), a panelled door with canopy, arch or civic columns,
    ONE accent (flower boxes or shutters), gable (eaves- or gable-front), hip or flat roof with cornice, chimneys.
    sp: W (frontage), D (depth), floors, roof ('gable'|'hip'|'flat'), rc, id, style, shop (ground-floor shopfront),
    accent_kind ('flower'|'shutters'|None)."""
    W, D, floors, rc, sid = sp['W'], sp['D'], sp['floors'], sp['rc'], sp['id']
    style = sp.get('style', 'oldtown')
    civic = style == 'civic'
    villa = style == 'villa'
    rural = style == 'rural'
    pl = {'civic': 0.6, 'villa': 0.4, 'rural': 0.6}.get(style, 0.5)
    fl = sp.get('floor_h', 3.2)
    z1 = pl + floors * fl + 0.25
    h = House(W, D, z1, rc, plinth=pl, floor=fl)
    pitch = 3.0 if civic else (3.2 if rural else 2.8)
    wh = 2.1 if villa else (1.3 if rural else 1.8)
    ww = 1.0 if rural else 1.2
    front = bays(W, pitch, ww, odd=civic or villa or bool(sp.get('central_door')))
    side_b = bays(D, pitch, ww)
    nf = len(front)
    if nf % 2 == 1 and (civic or villa or sp.get('central_door') or nf >= 5):
        door_i = nf // 2
    else:
        door_i = [i for i in range(nf)][(h32(sid, 'door') % max(1, nf - 2)) + (1 if nf > 2 else 0)] if nf > 2 else h32(sid, 'door') % nf
    lintels = civic or (h32(sid, 'lintel') % 2 == 0)
    shop = sp.get('shop', False)
    acc = sp.get('accent_kind')
    accent = rc.get('accent') or 'red'
    win = {}
    for f in range(floors):
        for i, c in enumerate(front):
            if f == 0 and i == door_i:
                continue
            if f == 0 and shop:
                h.shopfront(0, c, min(pitch - 0.5, 2.3))
                continue
            win[(0, f, i)] = h.window(0, c, f, w=ww, h=wh, glass=glass_for(sid, 0, f, i), lintel=(f == 1 and lintels))
        for i, c in enumerate(bays(W, pitch, ww)):
            h.window(2, c, f, w=ww, h=wh, glass=glass_for(sid, 2, f, i), lintel=(f == 1 and lintels))
        if D >= 5.0:
            for i, c in enumerate(side_b):
                h.window(1, c, f, w=ww, h=wh, glass=glass_for(sid, 1, f, i), lintel=(f == 1 and lintels))
                h.window(3, c, f, w=ww, h=wh, glass=glass_for(sid, 3, f, i), lintel=(f == 1 and lintels))
    dc = front[door_i]
    if civic or villa:
        h.door(0, dc, w=1.6, h=2.8, transom=2.25, steps=3, canopy=(3.2, 1.6), columns=True)
    elif h32(sid, 'canopy') % 2 == 0 or nf < 3:
        h.door(0, dc, w=1.2, h=2.6, transom=2.1, steps=3, canopy=(1.6, 0.8))
    else:
        h.door(0, dc, w=1.3, h=2.5, transom=2.05, steps=3, arch=True)
    # the accent: flower boxes on the 2nd-floor front windows, or shutters on the ground and 2nd floor
    if acc == 'flower' and floors >= 2:
        bloom = 'chalk' if accent == 'red' else 'red'
        for (sd, f, i), (u0, u1, z) in win.items():
            if f == 1:
                h.later.append(lambda u0=u0, u1=u1, z=z: h.flower_box(0, u0, u1, z, accent, bloom))
    elif acc == 'shutters':
        for (sd, f, i), (u0, u1, z) in win.items():
            if f <= 1:
                h.later.append(lambda u0=u0, u1=u1, z=z: h.shutters(0, u0, u1, z, wh, accent))
    h.plinth_box()
    roof = sp.get('roof', 'gable')
    if not (sp.get('no_pilasters') or rural):
        h.pilasters(z1 if roof != 'flat' else z1)
    if not rural:
        for f in range(1, floors):
            h.band(h.floor_z(f) - 0.05)
    m = h.m
    ztop = z1
    if roof == 'gable':
        axis = sp.get('axis') or ('x' if W >= D else 'y')
        zE, ztop = h.gable_roof(sp.get('pitch', 35), axis=axis)
    elif roof == 'hip':
        zf, ztop = h.hip_roof(sp.get('pitch', 30))
        if sp.get('dormer') and nf >= 3 and W >= D:
            h.cross_gable(0, dc, 3.0, 38, 3.2, main_pitch=sp.get('pitch', 30))
            h.oculus(0, h.body.u_of(0, dc), z1 + 0.86, r=0.34)
    else:
        h.cornice(z1)
        h.parapet(z1, ph=0.8)
        ztop = z1 + 0.95
        if W * D > 150:
            m.box(3.2, 2.4, 2.0, h.wallc, base=True, at=(W * 0.18, D * 0.12, z1), kind='hard', member=2.0)
            m.box(3.4, 2.6, 0.15, 'chalk', base=True, at=(W * 0.18, D * 0.12, z1 + 2.0), kind='hard', member=0.15)
    if roof in ('gable', 'hip'):
        nch = 1 + (h32(sid, 'chim') % 2 if W > 10 else 0)
        sx = 1 if h32(sid, 'chs') % 2 else -1
        for k in range(nch):
            cx = sx * (W / 2 - 1.1) if k == 0 else -sx * (W / 2 - 1.6)
            h.chimney(cx, D * 0.18, ztop + 0.5, z1)
    hm = h.finish()
    if shop:
        for i, c in enumerate(front):
            if i != door_i:
                awning(hm, h.body, 0, c, min(pitch - 0.3, 2.6), h.floor_z(0) + 2.95, 1.0, 0.5, 6, [accent, 'chalk'])
    if sp.get('flag'):
        # civic: flagpole over the entrance (ink pole, cobalt flag)
        M = h.body.matrix(0) @ sk.T(h.body.u_of(0, dc), -0.3, h.floor_z(1) + 0.4) @ sk.R(-35, 'X')
        hm.cyl(0.04, 2.2, 6, 'ink', M=M, member=0.08, kind='detail')
        hm.box(0.9, 0.06, 0.55, sp['flag'], M=M @ sk.T(0.47, 0, 1.85), kind='detail', member=0.06)
    return hm


def slab(sp):
    """Panel block (bible 7.1, 7.4): sections of five 3.6 m bays (window, balcony, stair, balcony, window), a stair
    strip and a concrete canopy with an ink door per section, open balconies with panel parapets and a third of them
    glazed (lower panel in the house accent), blank end walls, panel seams as PT_PanelSeams_v2, a dark asphalt plinth,
    flat roof with parapet, chalk cap and stair heads."""
    W, D, floors, rc, sid = sp['W'], sp['D'], sp['floors'], sp['rc'], sp['id']
    fl, pl = 2.8, 0.6
    z_top = pl + floors * fl
    nsec = max(1, int(round(W / 18.0)))
    Ws = W / nsec
    pitch = Ws / 5
    rc = dict(rc)
    rc['plinth'] = 'asphalt.dark'
    h = House(W, D, z_top, rc, plinth=pl, floor=fl, pat_origin=(-W / 2, pl))
    h.wallc = 'panel'                       # parapets, stair heads: plain panel
    h.body.wall = f'{SEAMS}|panel'
    B = h.body
    acc = rc.get('accent') or 'mustard'
    balconies = []
    for s in range(nsec):
        cs = -W / 2 + Ws * (s + 0.5)
        us = [cs + (k - 2) * pitch for k in range(5)]
        for f in range(floors):
            for k in (0, 4):
                h.window(0, us[k], f, w=1.5, h=1.5, glass=glass_for(sid, 'f', s, f, k), cross=False)
            for k in (1, 3):
                if f == 0:
                    h.window(0, us[k], f, w=1.5, h=1.5, glass=glass_for(sid, 'g', s, k), cross=False)
                else:
                    z = h.floor_z(f) + 0.15
                    B.opening(0, us[k], 1.6, z, z + 2.25, glass_for(sid, 'bd', s, f, k), depth=0.15)
                    balconies.append((us[k], f, (s + f + k) % 3 == 0))
            for k in range(5):
                if k == 2:
                    if 1 <= f < floors:
                        zl = h.floor_z(f) + 0.95                  # landing half a floor up
                        B.opening(2, -us[k], 0.9, zl, zl + 0.9, glass_for(sid, 'l2', s, f), depth=0.12)
                    continue
                h.window(2, -us[k], f, w=1.5, h=1.5, glass=glass_for(sid, 'b', s, f, k), cross=False)
        # stair bay: landing windows half a floor up, a light stair strip, the entrance under a concrete canopy
        B.paint_rect(0, us[2], 1.6, pl + 2.8, z_top, 'panel.light')
        for f in range(1, floors):
            zl = h.floor_z(f) + 0.95
            B.opening(0, us[2], 0.9, zl, zl + 0.9, glass_for(sid, 'l', s, f), depth=0.12)
        h.door(0, us[2], w=1.3, h=2.2, transom=None, leaf='ink', steps=3)
        u = B.u_of(0, us[2])
        zc = pl + 2.2 + 0.2

        def canopy(u=u, zc=zc):
            h.sbox(0, u - 1.2, u + 1.2, zc, zc + 0.18, -0.02, 1.5, 'grey', kind='hard', member=0.18)
            h.sbox(0, u - 1.23, u + 1.23, zc + 0.18, zc + 0.24, -0.02, 1.53, 'chalk', kind='hard', member=0.06)
        h.later.append(canopy)
    h.plinth_box()
    m = h.finish()
    for c, f, glazed in balconies:
        u = B.u_of(0, c)
        z = h.floor_z(f)
        h.sbox(0, u - 1.5, u + 1.5, z - 0.15, z, -0.02, 1.2, 'grey', kind='hard', member=0.15)
        if glazed:
            h.sbox(0, u - 1.5, u + 1.5, z, z + 1.0, 1.12, 1.2, acc, kind='hard', member=0.08)
            h.sbox(0, u - 1.46, u + 1.46, z + 1.0, z + 2.45, 1.14, 1.18, 'glass.light', kind='relief', member=0.08)
            for uu in (u - 1.5, u - 0.04, u + 1.42):
                h.sbox(0, uu, uu + 0.08, z + 1.0, z + 2.45, 1.1, 1.2, 'chalk', kind='hard', member=0.08)
            h.sbox(0, u - 1.5, u + 1.5, z + 2.45, z + 2.53, 0.0, 1.2, 'chalk', kind='hard', member=0.08)
        else:
            h.sbox(0, u - 1.5, u + 1.5, z, z + 1.0, 1.12, 1.2, 'panel', kind='hard', member=0.08)
            h.sbox(0, u - 1.5, u + 1.5, z + 1.0, z + 1.06, 1.1, 1.22, 'grey', kind='hard', member=0.06)
        h.sbox(0, u - 1.5, u - 1.42, z, z + 1.0, 0.0, 1.2, 'panel', kind='hard', member=0.08)
        h.sbox(0, u + 1.42, u + 1.5, z, z + 1.0, 0.0, 1.2, 'panel', kind='hard', member=0.08)
    ring_xy(m, -W / 2, -D / 2, W / 2, D / 2, 0.3, z_top, z_top + 1.0, 'panel', kind='hard', name='parapet')
    ring_xy(m, -W / 2, -D / 2, W / 2, D / 2, 0.4, z_top + 1.0, z_top + 1.15, 'chalk', out=0.1, kind='relief', name='cap')
    for s in range(nsec):
        cs = -W / 2 + Ws * (s + 0.5)
        m.box(2.8, 5.0, 2.2, 'panel', base=True, at=(cs, -D / 2 + 3.2, z_top), kind='hard', member=2.2)
        m.box(3.0, 5.2, 0.15, 'chalk', base=True, at=(cs, -D / 2 + 3.2, z_top + 2.2), kind='hard', member=0.15)
    return m


def tower(sp):
    """Old-town tower (bible 2.7): a cream podium of two floors with shop windows and a civic entrance, a glazed shaft
    with a chalk grid (posts 0.25 m every 2.4 m, a 0.3 m band on every floor), flat roof, chalk cap, machine room."""
    W, D, floors, rc, sid = sp['W'], sp['D'], sp['floors'], sp['rc'], sp['id']
    fl, pl = 2.8, 0.6
    zp = pl + 2 * fl + 0.6                                   # podium top (with a cornice zone)
    z_top = pl + floors * fl + 0.6
    prc = dict(rc, wall='cream', trim='chalk', plinth='asphalt', roof_c='grey')
    h = House(W, D, zp, prc, plinth=pl, floor=fl)
    front = bays(W, 3.6, 2.4)
    for side in range(4):
        L = h.body.L(side)
        bs = bays(L, 3.6, 2.4)
        for i, c in enumerate(bs):
            if side == 0 and i == len(bs) // 2:
                continue
            h.shopfront(side, c, 2.4, h=2.6)
            h.window(side, c, 1, w=1.4, h=1.6, glass=glass_for(sid, 'p', side, i), cross=False)
    h.door(0, front[len(front) // 2], w=1.8, h=2.6, transom=2.1, steps=2, canopy=(4.0, 1.8), columns=True)
    h.plinth_box()
    h.pilasters(zp)
    h.band(h.floor_z(1) - 0.05)
    m = h.finish()
    h.cornice(zp + 0.36, h=0.36, out=0.3)
    # shaft: glass body inset 0.4 m, painted light panes on a template, chalk grid
    ins = 0.4
    Ws, Ds = W - 2 * ins, D - 2 * ins
    sb = Body(Ws, Ds, zp, z_top, 'glass', top='grey', bottom='grey', reveal='chalk')
    for side in range(4):
        L = sb.L(side)
        n = max(1, int(round(L / 2.4)))
        step = L / n
        for f in range(floors - 2):
            z0 = zp + f * fl
            for k in range(n):
                if h32(sid, side, f, k) % 100 < 16:
                    sb.paint_rect(side, -L / 2 + (k + 0.5) * step, step, z0, z0 + fl, 'glass.light')
    sb.build(m, name='shaft')
    for side in range(4):
        L = sb.L(side)
        n = max(1, int(round(L / 2.4)))
        step = L / n
        M0 = sb.matrix(side)
        for k in range(n + 1):
            u = k * step
            m.box(0.25, 0.08, z_top - zp, 'chalk', M=M0 @ sk.T(min(max(u, 0.125), L - 0.125), -0.04, (zp + z_top) / 2),
                  kind='relief', member=0.25)
        for f in range(floors - 2 + 1):
            z = zp + f * fl
            m.box(L + 0.1, 0.1, 0.3, 'chalk', M=M0 @ sk.T(L / 2, -0.05, min(z, z_top - 0.15) + (0.15 if f == 0 else 0.0)),
                  kind='relief', member=0.3)
    ring_xy(m, -Ws / 2, -Ds / 2, Ws / 2, Ds / 2, 0.3, z_top, z_top + 1.0, 'cream', kind='hard', name='parapet')
    ring_xy(m, -Ws / 2, -Ds / 2, Ws / 2, Ds / 2, 0.4, z_top + 1.0, z_top + 1.15, 'chalk', out=0.1, kind='relief', name='cap')
    m.box(5.0, 4.0, 2.6, 'cream', base=True, at=(1.5, 1.0, z_top), kind='hard', member=2.6)
    m.box(5.2, 4.2, 0.15, 'chalk', base=True, at=(1.5, 1.0, z_top + 2.6), kind='hard', member=0.15)
    return m


def commercial(sp):
    """Shop / supermarket / pavilion (bible 7.3 commercial): plinth 0.3, display windows with chalk frames, a sign
    band (accent) over them, an awning on small shops, small high windows on the other sides, flat roof with a chalk
    cornice and a low parapet."""
    W, D, rc, sid = sp['W'], sp['D'], sp['rc'], sp['id']
    hgt = max(3.2, sp.get('h', 4.0))
    z1 = hgt
    h = House(W, D, z1, rc, plinth=0.3, floor=hgt - 0.3)
    front = bays(W, 3.6, 2.8, margin=0.6)
    door_i = len(front) // 2
    for i, c in enumerate(front):
        if i == door_i:
            continue
        h.shopfront(0, c, min(3.0, 3.6 - 0.5), h=min(2.6, hgt - 1.2))
    h.door(0, front[door_i], w=1.6 if W > 10 else 1.2, h=2.3, transom=None, steps=1)
    for side in (1, 2, 3):
        L = h.body.L(side)
        for i, c in enumerate(bays(L, 4.0, 0.9, margin=1.2)):
            if h32(sid, side, i) % 3 == 0:
                continue
            h.window(side, c, 0, w=0.9, h=0.7, sill_h=1.7, cross=False, casing=False)
    h.plinth_box()
    m = h.finish()
    sign = sp.get('sign') or rc.get('accent') or 'red'
    zs = 0.3 + min(2.6, hgt - 1.2) + 0.15
    ztop_sign = min(zs + 0.7, z1 - 0.45)
    if ztop_sign - zs >= 0.35:
        h.sbox(0, 0.4, W - 0.4, zs, ztop_sign, -0.02, 0.12, sign, kind='hard', member=0.12)
    if sp.get('awning') and W < 26:
        for i, c in enumerate(front):
            if i != door_i:
                awning(m, h.body, 0, c, 3.0, zs - 0.08, 1.0, 0.45, 6, [sign, 'chalk'])
    h.cornice(z1, h=0.3, out=0.2)
    h.parapet(z1, ph=0.5)
    return m


def garages(sp):
    """Garage row (garage base): brick/grey walls, a run of up-and-over doors in teal / cobalt / mustard / grey by
    template, flat concrete roof slab with a 0.3 m overhang - the post-Soviet 'ракушки' by form, not by grime."""
    W, D, rc, sid = sp['W'], sp['D'], sp['rc'], sp['id']
    hgt = max(2.8, sp.get('h', 3.2))
    h = House(W, D, hgt, rc, plinth=0.15, floor=hgt)
    n = max(1, int(W // 3.4))
    cols = ['teal', 'cobalt', 'mustard', 'grey']
    for k in range(n):
        c = (k - (n - 1) / 2) * 3.4
        h.body.opening(0, c, 2.8, 0.0, 2.3, cols[h32(sid, k) % 4], depth=0.10)
    h.plinth_box()
    m = h.finish()
    m.box(W + 0.6, D + 0.6, 0.22, 'grey', base=True, at=(0, 0, hgt), kind='hard', member=0.22)
    return m


def industrial(sp):
    """Industrial shed / workshop / depot (bible 7.3 industrial, shed): brick (PT_Brick_v2), grey or panel walls,
    big gates with mustard/ink hazard posts, a door, ribbon windows under the eaves, shed, gable or flat roof."""
    W, D, rc, sid = sp['W'], sp['D'], sp['rc'], sp['id']
    hgt = max(3.0, sp.get('h', 5.0))
    roof = sp.get('roof', 'shed')
    pl = 0.5 if hgt > 4 else 0.3
    h = House(W, D, hgt, rc, plinth=pl, floor=hgt - pl)
    gate_c = rc.get('gate') or ['teal', 'cobalt', 'grey'][h32(sid, 'gate') % 3]
    ng = 1 if W < 16 else 2
    gw, gh = min(4.2, W * 0.3), min(4.2, hgt - 0.9)
    gates = [((k - (ng - 1) / 2) * (W / ng)) for k in range(ng)]
    for c in gates:
        h.body.opening(0, c, gw, pl, pl + gh, gate_c, depth=0.18)
    dc = gates[-1] + gw / 2 + 1.6 if gates[-1] + gw / 2 + 2.4 < W / 2 else None
    if dc is not None:
        h.door(0, dc, w=1.0, h=2.1, transom=None, steps=1)
    if hgt >= 4.0:
        for side in (1, 3, 2):
            L = h.body.L(side)
            for i, c in enumerate(bays(L, 3.6, 2.4, margin=1.2)):
                h.window(side, c, 0, w=2.4, h=0.8, sill_h=hgt - pl - 1.5, cross=False, casing=False)
    h.plinth_box()
    m = h.finish()
    for c in gates:                                         # hazard posts beside each gate: mustard / ink bands
        u0 = h.body.u_of(0, c) - gw / 2
        for uu in (u0 - 0.30, u0 + gw + 0.06):
            for k in range(6):
                z0 = pl + k * 0.3
                h.sbox(0, uu, uu + 0.24, z0, z0 + 0.3, -0.01, 0.10, 'mustard' if k % 2 == 0 else 'ink', kind='hard', member=0.10)
        h.sbox(0, u0 - 0.1, u0 + gw + 0.1, pl + gh, pl + gh + 0.25, -0.02, 0.12, rc['trim'], kind='hard', member=0.12)
    if roof == 'gable':
        h.gable_roof(sp.get('pitch', 22), ov=0.4, axis='x' if W >= D else 'y', oculus=False)
    elif roof == 'flat':
        h.parapet(hgt, ph=0.6)
    else:
        h.shed_roof(ov=0.4)
    return m


def kiosk(sp):
    """Kiosk (bible 2.5 style table): accent walls, chalk trim, a big serving window with a counter and a sign band,
    shed roof in the district roof colour."""
    W, D, rc, sid = sp['W'], sp['D'], sp['rc'], sp['id']
    hgt = max(2.6, sp.get('h', 2.8))
    h = House(W, D, hgt, rc, plinth=0.2, floor=hgt)
    u0, u1 = h.body.opening(0, 0.0, W * 0.55, 0.95, 2.2, 'glass', depth=0.15)
    h.door(1, 0.0, w=0.9, h=2.05, transom=None, steps=0)
    h.plinth_box()
    m = h.finish()
    h.sbox(0, u0 - 0.1, u1 + 0.1, 0.85, 0.95, -0.02, 0.35, 'chalk', kind='hard', member=0.1)
    h.sbox(0, 0.1, W - 0.1, 2.3, 2.62, -0.02, 0.1, 'chalk', kind='hard', member=0.1)
    h.shed_roof(ov=0.35, rise=0.35)
    return m


def chimney_tower(sp):
    """Industrial chimney (bible 2.7): a tapered 12-sided brick shaft (PT_Brick_v2), chalk and red bands under the
    top, a dark lip; plinth block at the foot."""
    d, hgt = sp.get('d', 7.7), sp.get('h', 85.0)
    m = sk.Mesh()
    m.box(d + 1.2, d + 1.2, 1.2, 'grey', base=True, member=1.2)
    r0, r1 = d / 2, d / 2 * 0.62
    rz = lambda z: r0 + (r1 - r0) * (z / hgt)                          # noqa: E731
    bands = [(hgt - 9.0, 'chalk'), (hgt - 7.0, 'red'), (hgt - 5.0, 'chalk'), (hgt - 3.0, 'red')]
    prof = [(rz(0.0), 1.2), (rz(hgt - 9.0), hgt - 9.0)]
    cols = [f'{BRICK}|brick']
    for k, (zb, col) in enumerate(bands):
        prof.append((rz(zb + 2.0), zb + 2.0))
        cols.append(col)
    prof.append((rz(hgt) * 1.08, hgt))
    cols.append('brick.dark')
    prof.append((rz(hgt) * 0.85, hgt))
    cols.append('ink')
    m.lathe(prof, 12, wall_paint('brick'), cols=cols, normals='flat', kind='hard', member=r1, name='shaft')
    return m


def villa_modern(sp):
    """Modern villa (bible 7.3): chalk walls, ink window frames, ribbon windows, flat roof under a chalk slab with a
    0.8 m overhang, plinth 0.4 grey."""
    W, D, floors, rc, sid = sp['W'], sp['D'], sp['floors'], sp['rc'], sp['id']
    rc = dict(rc, wall='chalk', frame='ink', plinth='grey')
    fl = 3.2
    z1 = 0.4 + floors * fl
    h = House(W, D, z1, rc, plinth=0.4, floor=fl)
    for f in range(floors):
        for side in range(4):
            L = h.body.L(side)
            if L < 8:
                continue
            h.window(side, 0.0 if side else -L * 0.12, f, w=min(L - 3.0, 6.0), h=1.7, sill_h=0.7, cross=False,
                     glass=glass_for(sid, side, f), sill=False)
    h.door(0, W / 2 - 1.8, w=1.2, h=2.5, transom=None, leaf='wood', steps=2)
    h.plinth_box()
    m = h.finish()
    m.box(W + 1.6, D + 1.6, 0.3, 'chalk', base=True, at=(0, 0, z1), kind='hard', member=0.3)
    return m


def water_tower(sp):
    """Water tower (bible 2.7): an 8-sided brick shaft (PT_Brick_v2), a teal tank with a grey cap, an ink ring
    gallery under the tank."""
    hgt = sp.get('h', 18.0)
    d = sp.get('d', 7.7)
    m = sk.Mesh()
    zt = hgt * 0.62
    m.box(d * 0.7 + 0.8, d * 0.7 + 0.8, 0.6, 'grey', base=True, member=0.6)
    m.lathe([(d * 0.33, 0.6), (d * 0.28, zt)], 8, wall_paint('brick'), normals='flat', kind='hard', member=d * 0.5, name='shaft')
    m.lathe([(d * 0.52, zt), (d * 0.52, zt + 0.25)], 12, 'ink', normals='flat', kind='hard', member=0.25)
    m.lathe([(d * 0.48, zt + 0.25), (d * 0.48, hgt - 1.6), (d * 0.3, hgt - 0.4), (0.0, hgt)], 12, 'teal',
            cols=['teal', 'grey', 'grey'], normals='soft', kind='hard', member=d * 0.6, name='tank')
    return m
