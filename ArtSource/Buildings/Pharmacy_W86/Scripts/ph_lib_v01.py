"""Pharmacy_W86 v01 - shared geometry helpers (Blender 5.2, background bpy).
Copied from ArtSource/Buildings/Workshop_W86/Scripts/ws_lib_v01.py; additions: per-face atlas UVs in box(), z-face UV offset.

Conventions (same as FACADE_KIT_v01 / STREET_KIT):
  * Blender Z up, metres, front of the building = -Y.  FBX: axis_forward=-Z, axis_up=Y, bake_space_transform
    -> in Unity the front faces +Z, Blender +X becomes Unity -X  (unity = (-bx, bz, -by)).
  * UV0 in metres (1 UV = 1 m), box projection; Unity material tiling = 1 / tile_m.
    Vertical faces use v = z - 0.05 so brick courses line up with the 3a_brick_v07 texture at tile 2 m.
  * Meshes are built unwelded with explicit per-vertex normals (flat faces get their face normal,
    cylinders / lathes get smooth radial normals) -> exported as custom split normals.
"""
import math
import bmesh
import bpy
from mathutils import Vector, Matrix

ZV = Vector((0.0, 0.0, 1.0))
EPS = 1e-6


def V(*a):
    if len(a) == 1:
        return Vector(a[0])
    return Vector(a)


def newell(pts):
    n = Vector((0.0, 0.0, 0.0))
    m = len(pts)
    for i in range(m):
        a, b = pts[i], pts[(i + 1) % m]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    if n.length < 1e-12:
        return None
    return n.normalized()


def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def RZ(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Z')


def RX(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'X')


def RY(deg):
    return Matrix.Rotation(math.radians(deg), 4, 'Y')


class MB:
    """Accumulates faces; every face gets its own vertices (pos, uv, normal)."""

    def __init__(self, name):
        self.name = name
        self.P, self.UV, self.N = [], [], []
        self.F, self.M = [], []

    # ------------------------------------------------------------------ core
    def face(self, pts, mat, want=None, uvax=None, voff=-0.05, uoff=0.0, normals=None, uvs=None, zoff=(0.0, 0.0)):
        pts = [Vector(p) for p in pts]
        n = newell(pts)
        if n is None:
            return
        if want is not None and n.dot(Vector(want)) < 0:
            pts.reverse()
            n = -n
            if normals:
                normals = list(reversed(normals))
            if uvs:
                uvs = list(reversed(uvs))
        ax = uvax
        if ax is None:
            a = (abs(n.x), abs(n.y), abs(n.z))
            ax = 'z' if (a[2] >= a[0] - 1e-9 and a[2] >= a[1] - 1e-9) else ('x' if a[0] >= a[1] else 'y')
        base = len(self.P)
        for i, p in enumerate(pts):
            if uvs:
                uv = uvs[i]
            elif ax == 'z':
                uv = (p.x + zoff[0], (p.y if n.z >= 0 else -p.y) + zoff[1])
            elif ax == 'x':
                uv = ((p.y if n.x > 0 else -p.y) + uoff, p.z + voff)
            else:
                uv = ((-p.x if n.y > 0 else p.x) + uoff, p.z + voff)
            self.P.append(p)
            self.UV.append(uv)
            self.N.append(Vector(normals[i]).normalized() if normals else n.copy())
        self.F.append(tuple(range(base, base + len(pts))))
        self.M.append(mat)

    def tris(self):
        return sum(len(f) - 2 for f in self.F)

    # ------------------------------------------------------------------ solids
    _BOXF = {
        'x-': ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)),
        'x+': ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
        'y-': ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
        'y+': ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
        'z-': ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
        'z+': ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
    }
    _BOXN = {'x-': (-1, 0, 0), 'x+': (1, 0, 0), 'y-': (0, -1, 0), 'y+': (0, 1, 0), 'z-': (0, 0, -1), 'z+': (0, 0, 1)}

    # corner order of _BOXF faces -> (u, v) corner of an upright label seen from outside
    _BOXUV = {'y-': ((0, 0), (1, 0), (1, 1), (0, 1)), 'y+': ((1, 0), (1, 1), (0, 1), (0, 0)),
              'x+': ((0, 0), (1, 0), (1, 1), (0, 1)), 'x-': ((1, 0), (1, 1), (0, 1), (0, 0)),
              'z+': ((0, 0), (1, 0), (1, 1), (0, 1)), 'z-': ((0, 0), (0, 1), (1, 1), (1, 0))}

    def box(self, mn, mx, mat, M=None, skip=(), mats=None, uvax=None, voff=-0.05, rects=None, zoff=(0.0, 0.0)):
        """rects: {face_key: (u0, v0, u1, v1)} atlas rect for that face (upright label seen from outside)."""
        mn, mx = Vector(mn), Vector(mx)
        R = M.to_3x3() if M is not None else None
        for key, corners in self._BOXF.items():
            if key in skip:
                continue
            pts = []
            for c in corners:
                p = Vector((mx.x if c[0] else mn.x, mx.y if c[1] else mn.y, mx.z if c[2] else mn.z))
                pts.append(M @ p if M is not None else p)
            w = Vector(self._BOXN[key])
            if R is not None:
                w = R @ w
            uvs = None
            if rects and key in rects:
                r = rects[key]
                uvs = [(r[0] + (r[2] - r[0]) * a, r[1] + (r[3] - r[1]) * b) for a, b in self._BOXUV[key]]
            self.face(pts, (mats or {}).get(key, mat), want=w, uvax=uvax, voff=voff, uvs=uvs, zoff=zoff)

    def solid(self, faces_pts, mat, mats=None, skip=()):
        """Convex solid from a list of faces (point lists); orientation from the centroid."""
        allp = [Vector(p) for f in faces_pts for p in f]
        c = sum(allp, Vector()) / len(allp)
        for i, f in enumerate(faces_pts):
            if i in skip:
                continue
            fc = sum((Vector(p) for p in f), Vector()) / len(f)
            self.face(f, (mats or {}).get(i, mat), want=fc - c)

    def hexa(self, c, mat, skip=(), mats=None):
        """c: 8 corners indexed by bits x|y<<1|z<<2 (like a box)."""
        idx = lambda x, y, z: c[x | (y << 1) | (z << 2)]
        keys = list(self._BOXF.keys())
        faces = []
        for key in keys:
            faces.append([idx(*k) for k in self._BOXF[key]])
        sk = [keys.index(k) for k in skip]
        mm = {keys.index(k): v for k, v in (mats or {}).items()}
        self.solid(faces, mat, mats=mm, skip=sk)

    def prism(self, poly, w0, w1, mat, frame, caps=(True, True), cap_mat=None, side_mats=None, skip_sides=()):
        """poly: CCW list of (s, t); frame(s, t, w) -> Vector. Extruded from w0 to w1."""
        n = len(poly)
        area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
        sg = 1.0 if area > 0 else -1.0
        o = frame(0, 0, 0)
        es = frame(1, 0, 0) - o
        et = frame(0, 1, 0) - o
        ew = frame(0, 0, 1) - o
        for i in range(n):
            if i in skip_sides:
                continue
            a, b = poly[i], poly[(i + 1) % n]
            ds, dt = b[0] - a[0], b[1] - a[1]
            want = (es * dt - et * ds) * sg
            pts = [frame(a[0], a[1], w0), frame(b[0], b[1], w0), frame(b[0], b[1], w1), frame(a[0], a[1], w1)]
            self.face(pts, (side_mats or {}).get(i, mat), want=want)
        sgn = 1 if w1 > w0 else -1
        if caps[0]:
            self.face([frame(s, t, w0) for s, t in poly], cap_mat or mat, want=-ew * sgn)
        if caps[1]:
            self.face([frame(s, t, w1) for s, t in poly], cap_mat or mat, want=ew * sgn)

    def cyl(self, p0, p1, r, mat, n=8, r1=None, caps=(True, True), smooth=True, cap_mat=None, phase=0.0):
        p0, p1 = Vector(p0), Vector(p1)
        ax = p1 - p0
        L = ax.length
        if L < 1e-9:
            return
        ax.normalize()
        ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
        u = ax.cross(ref).normalized()
        v = ax.cross(u).normalized()
        r1 = r if r1 is None else r1
        ring0, ring1, nrm = [], [], []
        slope = (r - r1) / L
        for i in range(n):
            a = phase + 2 * math.pi * i / n
            d = u * math.cos(a) + v * math.sin(a)
            ring0.append(p0 + d * r)
            ring1.append(p1 + d * r1)
            nrm.append((d + ax * slope).normalized())
        for i in range(n):
            j = (i + 1) % n
            pts = [ring0[i], ring0[j], ring1[j], ring1[i]]
            mid = (nrm[i] + nrm[j]).normalized()
            if smooth:
                self.face(pts, mat, want=mid, normals=[nrm[i], nrm[j], nrm[j], nrm[i]])
            else:
                self.face(pts, mat, want=mid)
        if caps[0] and r > 1e-6:
            self.face(list(ring0), cap_mat or mat, want=-ax)
        if caps[1] and r1 > 1e-6:
            self.face(list(ring1), cap_mat or mat, want=ax)

    def lathe(self, prof, n, mat, M=None, smooth=True, mats=None, phase=0.0):
        """prof: list of (r, z), CCW in the (r, z) plane for closed shapes (outward normal = (dz, -dr))."""
        M = M or Matrix.Identity(4)
        R = M.to_3x3()
        for k in range(len(prof) - 1):
            (ra, za), (rb, zb) = prof[k], prof[k + 1]
            dr, dz = rb - ra, zb - za
            ln = math.hypot(dr, dz)
            if ln < 1e-9:
                continue
            nr, nz = dz / ln, -dr / ln
            for i in range(n):
                a0 = phase + 2 * math.pi * i / n
                a1 = phase + 2 * math.pi * (i + 1) / n
                c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
                pts = [Vector((ra * c0, ra * s0, za)), Vector((ra * c1, ra * s1, za)),
                       Vector((rb * c1, rb * s1, zb)), Vector((rb * c0, rb * s0, zb))]
                if ra < 1e-6:
                    pts = pts[1:]
                elif rb < 1e-6:
                    pts = pts[:3]
                pts = [M @ p for p in pts]
                n0 = R @ Vector((nr * c0, nr * s0, nz))
                n1 = R @ Vector((nr * c1, nr * s1, nz))
                nm = (n0 + n1).normalized()
                if smooth:
                    if len(pts) == 4:
                        nl = [n0, n1, n1, n0]
                    elif ra < 1e-6:
                        nl = [n1, n1, n0]
                    else:
                        nl = [n0, n1, n1]
                    self.face(pts, (mats or {}).get(k, mat), want=nm, normals=nl)
                else:
                    self.face(pts, (mats or {}).get(k, mat), want=nm)

    def disc(self, center, r, n, mat, normal=(0, 0, 1), phase=0.0):
        c = Vector(center)
        ax = Vector(normal).normalized()
        ref = Vector((0, 0, 1)) if abs(ax.z) < 0.9 else Vector((1, 0, 0))
        u = ax.cross(ref).normalized()
        v = ax.cross(u).normalized()
        pts = [c + (u * math.cos(phase + 2 * math.pi * i / n) + v * math.sin(phase + 2 * math.pi * i / n)) * r for i in range(n)]
        self.face(pts, mat, want=ax)

    def tube(self, pts, r, mat, n=8, caps=(True, True), joints=True):
        """Polyline pipe: one cylinder per segment plus small joint sleeves."""
        pts = [Vector(p) for p in pts]
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            d = (b - a).normalized()
            ext0 = r if (i > 0) else 0.0
            ext1 = r if (i < len(pts) - 2) else 0.0
            cap0 = caps[0] if i == 0 else False
            cap1 = caps[1] if i == len(pts) - 2 else False
            self.cyl(a - d * ext0, b + d * ext1, r, mat, n=n, caps=(cap0, cap1))

    def merge(self, other, M=None, keep_uv=False):
        M = M or Matrix.Identity(4)
        R = M.to_3x3()
        for f, m in zip(other.F, other.M):
            pts = [M @ other.P[i] for i in f]
            nl = [(R @ other.N[i]).normalized() for i in f]
            self.face(pts, m, normals=nl, uvs=[other.UV[i] for i in f] if keep_uv else None)

    # ------------------------------------------------------------------ to Blender
    def build(self, matlib, collection, name=None, location=None, rot_z_deg=0.0):
        name = name or self.name
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(p) for p in self.P], [], [list(f) for f in self.F])
        mats = []
        for m in self.M:
            if m not in mats:
                mats.append(m)
        for m in mats:
            me.materials.append(matlib[m])
        mi = [mats.index(m) for m in self.M]
        me.polygons.foreach_set('material_index', mi)
        uvl = me.uv_layers.new(name='UVMap')
        loop_uv = []
        for lp in me.loops:
            loop_uv.extend(self.UV[lp.vertex_index])
        uvl.data.foreach_set('uv', loop_uv)
        # triangulate n-gons (ear clipping handles concave caps); quads stay quads
        bm = bmesh.new()
        bm.from_mesh(me)
        ng = [f for f in bm.faces if len(f.verts) > 4]
        if ng:
            bmesh.ops.triangulate(bm, faces=ng, quad_method='BEAUTY', ngon_method='EAR_CLIP')
        bm.to_mesh(me)
        bm.free()
        me.shade_smooth()
        me.normals_split_custom_set_from_vertices([tuple(n) for n in self.N])
        me.validate(clean_customdata=False)
        ob = bpy.data.objects.new(name, me)
        collection.objects.link(ob)
        if location is not None:
            ob.location = location
        if rot_z_deg:
            ob.rotation_euler = (0, 0, math.radians(rot_z_deg))
        return ob


# ---------------------------------------------------------------------- wall frames
class Wall:
    """Plane frame: P(u, z, d) = O + T*u + Z*z + N*d, with T x Z = N (CCW quads in (u, z) face along N)."""

    def __init__(self, O, Tv, N):
        self.O, self.T, self.N = Vector(O), Vector(Tv), Vector(N)
        assert (self.T.cross(ZV) - self.N).length < 1e-6, 'frame must satisfy T x Z = N'

    def P(self, u, z, d=0.0):
        return self.O + self.T * u + ZV * z + self.N * d

    def u_of(self, p):
        return (Vector(p) - self.O).dot(self.T)

    def uax(self):
        return 'x' if abs(self.N.x) > 0.5 else 'y'


def pieces(u0, u1, z0, ztop, ops):
    """Rectangle [u0,u1] x [z0, ztop(u)] minus openings (ou0, ou1, oz0, oz1). -> [(a, b, za, zb)]; zb may be callable."""
    top_fn = ztop if callable(ztop) else None
    br = sorted(set([u0, u1] + [x for o in ops for x in (o[0], o[1]) if u0 + EPS < x < u1 - EPS]))
    out = []
    for a, b in zip(br, br[1:]):
        if b - a < EPS:
            continue
        m = 0.5 * (a + b)
        holes = sorted((o[2], o[3]) for o in ops if o[0] - EPS <= m <= o[1] + EPS)
        cur = z0
        for h0, h1 in holes:
            if h1 <= cur + EPS:
                continue
            if top_fn is None and h0 >= ztop - EPS:
                break
            if h0 > cur + EPS:
                out.append((a, b, cur, min(h0, ztop) if top_fn is None else h0))
            cur = max(cur, h1)
        if top_fn is None:
            if cur < ztop - EPS:
                out.append((a, b, cur, ztop))
        else:
            out.append((a, b, cur, top_fn))
    return out


def periodic_profile(a, b, period, bps):
    """bps: [(offset, depth), ...] for one period starting at offset 0 and ending at offset=period (same depth).
    Returns [(u, depth)] covering [a, b] with every breakpoint."""
    def depth(u):
        t = u - math.floor(u / period) * period
        for (o0, d0), (o1, d1) in zip(bps, bps[1:]):
            if o0 - 1e-9 <= t <= o1 + 1e-9:
                if o1 - o0 < 1e-9:
                    return d1
                return d0 + (d1 - d0) * (t - o0) / (o1 - o0)
        return bps[-1][1]
    k0 = math.floor(a / period) - 1
    k1 = math.ceil(b / period) + 1
    cand = {round(a, 6), round(b, 6)}
    for k in range(k0, k1 + 1):
        for o, _ in bps:
            u = k * period + o
            if a + 1e-5 < u < b - 1e-5:
                cand.add(round(u, 6))
    us = sorted(cand)
    return [(u, depth(u)) for u in us]


def corr_bps(pitch, d_valley, d_peak):
    wv = pitch * 0.40
    s = pitch * 0.12
    wp = pitch * 0.36
    return [(0.0, d_valley), (wv, d_valley), (wv + s, d_peak), (wv + s + wp, d_peak), (pitch, d_valley)]


def corrugate(mb, W, a, b, za, zb, mat, pitch, d_valley, d_peak, flat=False):
    """Vertical-rib corrugation on wall frame W over [a, b] x [za, zb(u)]."""
    topf = zb if callable(zb) else (lambda u: zb)
    if flat:
        d = 0.5 * (d_valley + d_peak)
        mb.face([W.P(a, za, d), W.P(b, za, d), W.P(b, topf(b), d), W.P(a, topf(a), d)], mat, want=W.N, uvax=W.uax())
        return
    prof = periodic_profile(a, b, pitch, corr_bps(pitch, d_valley, d_peak))
    # merge collinear flat runs is unnecessary: breakpoints only at shape changes
    for (u0, d0), (u1, d1) in zip(prof, prof[1:]):
        du, dd = u1 - u0, d1 - d0
        want = W.N * du - W.T * dd
        mb.face([W.P(u0, za, d0), W.P(u1, za, d1), W.P(u1, topf(u1), d1), W.P(u0, topf(u0), d0)], mat,
                want=want, uvax=W.uax())


BRICK_Z0 = 0.05
BRICK_COURSE = 0.125
BRICK_LEN = 0.25


def brick_profile(za, zb, groove=0.012, bevel=0.006):
    pts = []
    k0 = math.floor((za - BRICK_Z0) / BRICK_COURSE) - 1
    k1 = math.ceil((zb - BRICK_Z0) / BRICK_COURSE) + 1
    raw = []
    for k in range(k0, k1 + 1):
        z = BRICK_Z0 + k * BRICK_COURSE
        raw += [(z, -groove), (z + bevel, 0.0), (z + BRICK_COURSE - bevel, 0.0)]
    raw.append((BRICK_Z0 + (k1 + 1) * BRICK_COURSE, -groove))

    def dat(z):
        for (z0, d0), (z1, d1) in zip(raw, raw[1:]):
            if z0 - 1e-9 <= z <= z1 + 1e-9:
                return d0 + (d1 - d0) * (z - z0) / (z1 - z0) if z1 > z0 else d1
        return -groove
    zs = sorted({round(za, 6), round(zb, 6)} | {round(z, 6) for z, _ in raw if za + 1e-5 < z < zb - 1e-5})
    return [(z, dat(z)) for z in zs]


def brick_face(mb, W, a, b, za, zb, mat, flat=False):
    if flat:
        mb.face([W.P(a, za, 0), W.P(b, za, 0), W.P(b, zb, 0), W.P(a, zb, 0)], mat, want=W.N, uvax=W.uax())
        return
    prof = brick_profile(za, zb)
    for (z0, d0), (z1, d1) in zip(prof, prof[1:]):
        want = W.N * (z1 - z0) - ZV * (d1 - d0)
        mb.face([W.P(a, z0, d0), W.P(b, z0, d0), W.P(b, z1, d1), W.P(a, z1, d1)], mat, want=want, uvax=W.uax())


def brick_bump(mb, W, u0, u1, k, mat, proud=0.014):
    """One protruding brick of course k (aligned with the texture grid) between u0 and u1."""
    z0 = BRICK_Z0 + k * BRICK_COURSE + 0.010
    z1 = BRICK_Z0 + (k + 1) * BRICK_COURSE - 0.010
    corners = [None] * 8
    for di, d in enumerate((-0.004, proud)):
        for zi, z in enumerate((z0, z1)):
            for ui, u in enumerate((u0, u1)):
                corners[ui | (di << 1) | (zi << 2)] = W.P(u, z, d)
    mb.hexa(corners, mat, skip=('y-',))


def brick_joint_us(k):
    """u positions of vertical joints for course k (texture 3a_brick_v07 at tile 2 m)."""
    return 0.125 if (k % 2) else 0.0


def whexa(mb, W, u0, u1, d0, d1, z0, z1, mat, skip=(), mats=None):
    """Box in a wall frame: bits x->u, y->d, z->z. z0/z1 may be callables of u (sloped)."""
    f0 = z0 if callable(z0) else (lambda u: z0)
    f1 = z1 if callable(z1) else (lambda u: z1)
    c = [None] * 8
    for ui, u in enumerate((u0, u1)):
        for di, d in enumerate((d0, d1)):
            for zi, zf in enumerate((f0, f1)):
                c[ui | (di << 1) | (zi << 2)] = W.P(u, zf(u), d)
    mb.hexa(c, mat, skip=skip, mats=mats)


def hexa_xy(mb, x0, x1, y0, y1, zbot, ztop, mat, skip=(), mats=None):
    """World box whose bottom/top may be callables of (x, y) (sloped roof-following parts)."""
    fb = zbot if callable(zbot) else (lambda x, y: zbot)
    ft = ztop if callable(ztop) else (lambda x, y: ztop)
    c = [None] * 8
    for xi, x in enumerate((x0, x1)):
        for yi, y in enumerate((y0, y1)):
            for zi, f in enumerate((fb, ft)):
                c[xi | (yi << 1) | (zi << 2)] = Vector((x, y, f(x, y)))
    mb.hexa(c, mat, skip=skip, mats=mats)


def wrench_poly(L=1.0, hw=0.035, hr=0.085):
    """2D open-end wrench outline (concave), length L along x, centred."""
    s = L / 1.0
    cx = 0.40 * s
    pts = [(0.33 * s, -hw * s)]
    for a in (-140, -110, -80, -50, -25):
        r = math.radians(a)
        pts.append((cx + hr * s * math.cos(r), hr * s * math.sin(r)))
    pts += [(cx + 0.005 * s, -hw * 1.0 * s), (cx + 0.005 * s, hw * 1.0 * s)]
    for a in (25, 50, 80, 110, 140):
        r = math.radians(a)
        pts.append((cx + hr * s * math.cos(r), hr * s * math.sin(r)))
    pts.append((0.33 * s, hw * s))
    # left head (mirror, slightly smaller jaw)
    pts.append((-0.33 * s, hw * s))
    for a in (40, 70, 100, 130, 155):
        r = math.radians(a)
        pts.append((-cx + hr * s * math.cos(math.pi - r) * -1, hr * s * math.sin(math.pi - r)))
    pts += [(-cx - 0.005 * s, hw * 0.9 * s), (-cx - 0.005 * s, -hw * 0.9 * s)]
    for a in (155, 130, 100, 70, 40):
        r = math.radians(a)
        pts.append((-cx + hr * s * math.cos(math.pi - r) * -1, -hr * s * math.sin(math.pi - r)))
    pts.append((-0.33 * s, -hw * s))
    return pts
