"""MAP_W86_v01 vehicles - shared Blender helpers (Blender 5.2, background mode: blender -b --factory-startup -P build_x.py -- ...).

Geometry conventions (same as STREET_KIT / VEHICLES_KIT, whose Mesh accumulator this module re-implements so that
nothing in those kits is touched):
  * Blender Z up, metres. Vehicles: nose to -Y (Blender) = Unity +Z after FBX export (axis_forward=-Z, axis_up=Y,
    apply transform). Driver / port side = +X Blender = Unity -X.
  * Pivot: ground models - centre of the footprint (XY bounding box) on the ground (min z = 0);
    water models - centre of the footprint on the WATERLINE (z = 0, hull goes below).
  * Faces carry a palette cell name ('ink', 'mil_base', ...) -> one UV point in that cell, or a pattern token:
      '@pattern' = projected through the whole object (camo, teak deck - continuous over faces),
      '#pattern' = fitted to the face (hazard panels, wagon boards).
  * Flat shading, every part a closed shell; meshes are triangulated before export; LOD0 + LOD1 in one FBX
    (<Name>_LOD0 / <Name>_LOD1 -> Unity builds the LODGroup on import).
"""
import json, math, sys
from pathlib import Path

import bpy, bmesh
from mathutils import Vector, Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mw86_palette as PAL  # noqa: E402

TAU = math.tau
LIB = Path(__file__).resolve().parent


def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def R(deg, axis):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def S(x, y=None, z=None):
    return Matrix.Diagonal((x, x if y is None else y, x if z is None else z, 1.0))


def _ccw_xy(poly):
    return sum((poly[(i + 1) % len(poly)][0] - poly[i][0]) * (poly[(i + 1) % len(poly)][1] + poly[i][1]) for i in range(len(poly))) < 0


class Mesh:
    """Closed shells as plain lists; fcol = palette cell name or pattern token per face. lod: 0 full, 1 reduced."""

    def __init__(self, lod=0):
        self.lod = lod
        self.verts, self.faces, self.fcol = [], [], []

    # ------------------------------------------------------------------ core
    def shell(self, verts, faces, col, M=None, cols=None):
        M = M or Matrix.Identity(4)
        b = len(self.verts)
        self.verts += [tuple(M @ Vector(v)) for v in verts]
        for i, f in enumerate(faces):
            self.faces.append(tuple(b + k for k in f))
            self.fcol.append(cols[i] if cols and cols[i] else col)
        return range(len(self.faces) - len(faces), len(self.faces))

    def merge(self, other, M=None):
        self.shell(other.verts, [tuple(f) for f in other.faces], None, M, cols=other.fcol)

    def tris(self):
        return sum(len(f) - 2 for f in self.faces)

    def seg(self, n0, n1=None):
        """Segment count per LOD (LOD1 default: ~60 %, min 4)."""
        return n0 if self.lod == 0 else (n1 if n1 is not None else max(4, int(round(n0 * 0.6))))

    def bevelled(self, verts, faces, col, bev, M=None, seg=1, cols=None):
        """Any closed shell with every edge chamfered (bmesh bevel, clamped). LOD1 or bev <= 0: no bevel."""
        if self.lod > 0 or bev <= 0:
            return self.shell(verts, faces, col, M, cols=cols)
        bm = bmesh.new()
        vs = [bm.verts.new(v) for v in verts]
        for f in faces:
            bm.faces.new([vs[i] for i in f])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bev, segments=seg, affect='EDGES', profile=0.5, clamp_overlap=True)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
        bm.verts.index_update()
        v = [tuple(x.co) for x in bm.verts]
        f = [tuple(x.index for x in fa.verts) for fa in bm.faces]
        bm.free()
        return self.shell(v, f, col, M)

    # ------------------------------------------------------------------ primitives (all closed)
    def box(self, sx, sy, sz, col, M=None, at=(0, 0, 0), base=False, cols=None):
        """cols (optional, 6): bottom, top, -Y, +X, +Y, -X."""
        x, y = sx / 2, sy / 2
        z0, z1 = (0, sz) if base else (-sz / 2, sz / 2)
        v = [(-x, -y, z0), (x, -y, z0), (x, y, z0), (-x, y, z0), (-x, -y, z1), (x, -y, z1), (x, y, z1), (-x, y, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        return self.shell(v, f, col, (M or Matrix.Identity(4)) @ T(*at), cols=cols)

    def bb(self, sx, sy, sz, bev, col, M=None, at=(0, 0, 0), base=False):
        """Bevelled box (one 45-degree chamfer on every edge); plain box in LOD1."""
        if self.lod > 0 or bev <= 0:
            return self.box(sx, sy, sz, col, M, at, base)
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(bev, sx / 2.01, sy / 2.01, sz / 2.01), segments=1,
                        affect='EDGES', profile=0.5)
        if base:
            bmesh.ops.translate(bm, vec=(0, 0, sz / 2), verts=bm.verts)
        bm.verts.index_update()
        v = [tuple(x.co) for x in bm.verts]
        f = [tuple(x.index for x in fa.verts) for fa in bm.faces]
        bm.free()
        return self.shell(v, f, col, (M or Matrix.Identity(4)) @ T(*at))

    def hexa(self, bot, top, col, bev=0.0, M=None):
        """Closed 8-vertex solid from a bottom and a top quad (both CCW seen from above)."""
        v = [tuple(p) for p in bot] + [tuple(p) for p in top]
        f = [(3, 2, 1, 0), (4, 5, 6, 7)] + [(i, (i + 1) % 4, (i + 1) % 4 + 4, i + 4) for i in range(4)]
        return self.bevelled(v, f, col, bev, M)

    def prism_xy(self, poly, z0, z1, col, M=None, bev=0.0, top=None):
        """Polygon in the XY plane extruded from z0 to z1."""
        poly = list(poly)
        if not _ccw_xy(poly):
            poly = poly[::-1]
        n = len(poly)
        v = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly]
        f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        if bev > 0 and self.lod == 0:
            return self.bevelled(v, f, col, bev, M)
        cols = [None, top] + [None] * n
        return self.shell(v, f, col, M, cols=cols)

    def side(self, poly_yz, x0, x1, col, bev=0.0, M=None):
        """Side silhouette polygon (y, z) extruded across the vehicle from x0 to x1 (bevelled in LOD0 if bev)."""
        poly = list(poly_yz)
        if not _ccw_xy(poly):
            poly = poly[::-1]
        n = len(poly)
        v = [(x0, y, z) for y, z in poly] + [(x1, y, z) for y, z in poly]
        f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
        return self.bevelled(v, f, col, bev, M)

    def end(self, poly_xz, y0, y1, col, bev=0.0, M=None):
        """Cross-section polygon (x, z) extruded along Y from y0 to y1."""
        poly = list(poly_xz)
        if not _ccw_xy(poly):
            poly = poly[::-1]
        n = len(poly)
        v = [(x, y0, z) for x, z in poly] + [(x, y1, z) for x, z in poly]
        f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        return self.bevelled(v, f, col, bev, M)

    def ring(self, r_in, r_out, z0, z1, seg, col, M=None, top=None, offset=None, topfn=None):
        """Thick annulus (tube section) from z0 to z1; topfn(k) -> colour of top face segment k."""
        off = math.pi / seg if offset is None else offset
        pr = [(r_in, z0), (r_out, z0), (r_out, z1), (r_in, z1)]
        v, f, fc = [], [], []
        for r, z in pr:
            v += [(r * math.cos(off + TAU * k / seg), r * math.sin(off + TAU * k / seg), z) for k in range(seg)]
        for b in range(4):
            a0, c0 = b * seg, ((b + 1) % 4) * seg
            for k in range(seg):
                k1 = (k + 1) % seg
                f.append((a0 + k, a0 + k1, c0 + k1, c0 + k))
                fc.append((topfn(k) if topfn else top) if b == 2 else None)
        return self.shell(v, f, col, M, cols=fc)

    def frustum(self, bot_xy, z0, top_xy, z1, col, bev=0.0, M=None):
        """Solid between a bottom polygon at z0 and a top polygon at z1 (same count, CCW from above)."""
        n = len(bot_xy)
        v = [(x, y, z0) for x, y in bot_xy] + [(x, y, z1) for x, y in top_xy]
        f = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        return self.bevelled(v, f, col, bev, M)

    def lathe(self, profile, seg, col, M=None, offset=None, cols=None):
        """profile [(r, z)] bottom to top; r == 0 -> pole. cols: optional colour per band (len(profile) - 1)."""
        off = math.pi / seg if offset is None else offset
        v, f, fc = [], [], []
        rings = []
        for r, z in profile:
            if r <= 1e-9:
                rings.append([len(v)]); v.append((0, 0, z))
            else:
                rings.append(list(range(len(v), len(v) + seg)))
                v += [(r * math.cos(off + TAU * k / seg), r * math.sin(off + TAU * k / seg), z) for k in range(seg)]
        for b, (a, c) in enumerate(zip(rings, rings[1:])):
            bc = cols[b] if cols else None
            for k in range(seg):
                k1 = (k + 1) % seg
                if len(a) == 1:
                    f.append((a[0], c[k1], c[k]))
                elif len(c) == 1:
                    f.append((a[k], a[k1], c[0]))
                else:
                    f.append((a[k], a[k1], c[k1], c[k]))
                fc.append(bc)
        if len(rings[0]) > 1:
            f.append(tuple(reversed(rings[0]))); fc.append(cols[0] if cols else None)
        if len(rings[-1]) > 1:
            f.append(tuple(rings[-1])); fc.append(cols[-1] if cols else None)
        return self.shell(v, f, col, M, cols=fc)

    def cyl(self, r, h, seg, col, M=None, r_top=None, at=(0, 0, 0), offset=None):
        """Upright cylinder / frustum standing on `at`."""
        return self.lathe([(r, 0), (r if r_top is None else r_top, h)], seg, col, (M or Matrix.Identity(4)) @ T(*at), offset)

    def cyl_x(self, r, w, seg, col, at=(0, 0, 0), r2=None):
        """Cylinder with its axis along X, centred on `at` (wheels, drums, rollers)."""
        return self.cyl(r, w, seg, col, T(at[0] - w / 2, at[1], at[2]) @ R(90, 'Y'), r_top=r2)

    def cyl_y(self, r, l, seg, col, at=(0, 0, 0), r2=None):
        """Cylinder with its axis along Y from at.y - l/2 to at.y + l/2 (r at -Y end, r2 at +Y end)."""
        return self.cyl(r, l, seg, col, T(at[0], at[1] - l / 2, at[2]) @ R(-90, 'X'), r_top=r2)

    def bar(self, p0, p1, r, col, seg=6, r1=None):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        q = d.to_track_quat('Z', 'Y' if abs(d.normalized().z) < 0.99 else 'X')
        M = T(*p0) @ q.to_matrix().to_4x4()
        return self.cyl(r, d.length, seg, col, M, r_top=r1)

    def beam(self, p0, p1, w, h, col, up=(0, 0, 1)):
        """Box from p0 to p1 with cross-section w (sideways) x h (along `up`)."""
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        x = d.normalized()
        z = Vector(up)
        z = (z - x * z.dot(x)).normalized()
        y = z.cross(x)
        M = Matrix((x, y, z)).transposed().to_4x4()
        M.translation = (p0 + p1) / 2
        return self.box(d.length, w, h, col, M)

    def tube_path(self, pts, r, seg, col, closed=False):
        pts = [Vector(p) for p in pts]
        n = len(pts)
        rings = []
        a = None
        for i, p in enumerate(pts):
            if closed:
                t = (pts[(i + 1) % n] - pts[i - 1]).normalized()
            elif i == 0:
                t = (pts[1] - pts[0]).normalized()
            elif i == n - 1:
                t = (pts[-1] - pts[-2]).normalized()
            else:
                t = ((pts[i + 1] - p).normalized() + (p - pts[i - 1]).normalized()).normalized()
            if a is None:
                ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
                a = t.cross(ref).normalized()
            else:
                a = (a - t * a.dot(t)).normalized()
            b = t.cross(a)
            scale = 1.0
            if 0 < i < n - 1 or closed:
                d0 = (p - pts[i - 1]).normalized()
                scale = 1 / max(0.5, d0.dot(t))
            rings.append([p + (a * math.cos(TAU * k / seg + math.pi / seg) + b * math.sin(TAU * k / seg + math.pi / seg)) * r * scale
                          for k in range(seg)])
        v = [tuple(x) for ring in rings for x in ring]
        f = []
        m = n if closed else n - 1
        for i in range(m):
            a0, b0 = i * seg, ((i + 1) % n) * seg
            for k in range(seg):
                k1 = (k + 1) % seg
                f.append((a0 + k, a0 + k1, b0 + k1, b0 + k))
        if not closed:
            f.append(tuple(range(seg - 1, -1, -1)))
            f.append(tuple(range((n - 1) * seg, n * seg)))
        return self.shell(v, f, col)

    def plate(self, pts, out, t, col, inset=0.004):
        """Planar convex polygon thickened along its normal (t outwards, inset inwards) - glass, stripes, panels."""
        pts = [Vector(p) for p in pts]
        k = len(pts)
        n = Vector()
        for i in range(k):
            a, b = pts[i], pts[(i + 1) % k]
            n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
        n.normalize()
        if n.dot(Vector(out)) < 0:
            pts.reverse()
            n = -n
        v = [tuple(p - n * inset) for p in pts] + [tuple(p + n * t) for p in pts]
        f = [tuple(range(k - 1, -1, -1)), tuple(range(k, 2 * k))]
        for i in range(k):
            j = (i + 1) % k
            f.append((i, j, k + j, k + i))
        return self.shell(v, f, col)

    def xplate(self, s, x, poly_yz, col, t=0.01, inset=0.005):
        """Plate on the side plane x = s*x (s=+1 / -1)."""
        return self.plate([(s * x, y, z) for y, z in poly_yz], (s, 0, 0), t, col, inset)

    def yplate(self, s, y, poly_xz, col, t=0.01, inset=0.005):
        """Plate on the end plane y (s=-1 front face, +1 rear face)."""
        return self.plate([(x, y, z) for x, z in poly_xz], (0, s, 0), t, col, inset)

    def zplate(self, z, poly_xy, col, t=0.01, inset=0.005):
        return self.plate([(x, y, z) for x, y in poly_xy], (0, 0, 1), t, col, inset)

    def loft(self, rings, col, cols=None, cap0=True, cap1=True, cap_cols=(None, None), colfn=None):
        """Rings = lists of 3D points (same count, same winding); quads between consecutive rings; ngon caps.
        cols: optional colour per ring edge index (edge k = ring[k] -> ring[k+1]); colfn(i_segment, k_edge) overrides."""
        n = len(rings[0])
        v = [tuple(p) for ring in rings for p in ring]
        f, fc = [], []
        for i in range(len(rings) - 1):
            a0, b0 = i * n, (i + 1) * n
            for k in range(n):
                k1 = (k + 1) % n
                f.append((a0 + k, a0 + k1, b0 + k1, b0 + k))
                c = colfn(i, k) if colfn else None
                fc.append(c or (cols[k] if cols else None))
        # caps: triangle fan from the ring centroid (no slivers on very thin bow / nose rings)
        for cap, ring_i, cc in ((cap0, 0, cap_cols[0]), (cap1, len(rings) - 1, cap_cols[1])):
            if not cap:
                continue
            ring = rings[ring_i]
            c = tuple(sum(p[k] for p in ring) / n for k in range(3))
            ci = len(v)
            v.append(c)
            base = ring_i * n
            for k in range(n):
                k1 = (k + 1) % n
                f.append((base + k1, base + k, ci) if ring_i == 0 else (base + k, base + k1, ci))
                fc.append(cc)
        return self.shell(v, f, col, cols=fc)

    # ------------------------------------------------------------------ vehicle parts
    def wheel(self, x, y, r, w, tyre='tyre', rim='grey', seg=12, rim_r=None, hz=None):
        """Wheel with its axle along X centred at (x, y, hz); tyre flat rests on z = 0 by default."""
        sg = self.seg(seg, max(6, seg // 2 + 1) if r >= 0.45 else 6)
        hz = hz if hz is not None else r * math.cos(math.pi / sg)
        self.cyl_x(r, w, sg, tyre, at=(x, y, hz))
        if rim and (self.lod == 0 or r >= 0.45):
            rr = rim_r or r * 0.55
            sx = 1 if x >= 0 else -1
            self.cyl_x(rr, 0.05, max(6, sg // 2), rim, at=(x + sx * (w / 2 + 0.01), y, hz))
        return hz


def octa(a, z0, z1, c, y):
    """Octagonal section ring at y: half-width a, from z0 to z1, corner chamfer c (CCW seen from -Y)."""
    return [(-a + c, y, z0), (a - c, y, z0), (a, y, z0 + c), (a, y, z1 - c), (a - c, y, z1), (-a + c, y, z1), (-a, y, z1 - c), (-a, y, z0 + c)]


def hull_rings(L, B, fb, draft, ts=None, bow_rise=0.45, transom=0.82, chine=0.8, deadrise=0.22, bow_w=0.03,
               keel_bow=None, flare=0.0):
    """Planing / displacement hull sections from bow (y = -L/2) to transom (y = +L/2), waterline z = 0.
    Ring (9 pts, closed): L sheer, L stripe top, L waterline, L chine, keel, R chine, R waterline, R stripe top, R sheer;
    edge k: 0 L topside, 1 L stripe, 2-5 bottom, 6 R stripe, 7 R topside, 8 deck."""
    ts = ts or [0.0, 0.035, 0.1, 0.22, 0.4, 0.6, 0.8, 1.0]
    kb = fb * 0.55 if keel_bow is None else keel_bow
    rings = []
    for t in ts:
        y = -L / 2 + L * t
        if t <= 0.55:
            w = B / 2 * max(bow_w * 2 / B, math.sin(math.pi / 2 * min(1.0, t / 0.55)) ** 0.75)
        else:
            w = B / 2 * (1 - (1 - transom) * ((t - 0.55) / 0.45) ** 2)
        zs = fb + bow_rise * (1 - t) ** 2.2
        s = min(1.0, t / 0.32) ** 0.6
        zk = -draft * s + (1 - s) * kb
        zc = zk + (zs - zk) * deadrise * (0.6 + 0.4 * s)
        zw = min(max(0.06, zc + 0.04 * (zs - zk)), zs - 0.3 * (zs - zk))
        zt = zw + min(0.3, 0.32 * (zs - zw))
        wc = chine * w

        def xat(z):
            return wc + (w - wc) * (z - zc) / max(1e-6, zs - zc) + flare * (z - zc) / max(1e-6, zs - zc) * 0.0
        ring = [(-w, y, zs), (-xat(zt), y, zt), (-xat(zw), y, zw), (-wc, y, zc), (0.0, y, zk),
                (wc, y, zc), (xat(zw), y, zw), (xat(zt), y, zt), (w, y, zs)]
        rings.append(ring)
    return rings


def hull(m, L, B, fb, draft, top, stripe, bottom, deck, transom_col=None, **kw):
    rings = hull_rings(L, B, fb, draft, **kw)
    m.loft(rings, top, cols=[top, stripe, bottom, bottom, bottom, bottom, stripe, top, deck],
           cap_cols=(top, transom_col or top))
    return rings


def sheer_line(rings, side):
    """Sheer points (x, y, z) along the hull on side +1 / -1 (bow -> stern)."""
    return [r[8] if side > 0 else r[0] for r in rings]


def hull_x(rings, y, z, side=1):
    """Half-breadth of a hull_rings() hull at (y, z) on side +1/-1 (linear in y between stations, in z along the side)."""
    def at_ring(r):
        pts = [r[5], r[6], r[7], r[8]]                        # chine, waterline, stripe top, sheer (z ascending)
        if z <= pts[0][2]:
            return abs(pts[0][0])
        for a, b in zip(pts, pts[1:]):
            if a[2] <= z <= b[2]:
                t = (z - a[2]) / max(1e-6, b[2] - a[2])
                return abs(a[0]) + (abs(b[0]) - abs(a[0])) * t
        return abs(pts[-1][0])
    ys = [r[0][1] for r in rings]
    if y <= ys[0]:
        return side * at_ring(rings[0])
    for i in range(len(rings) - 1):
        if ys[i] <= y <= ys[i + 1]:
            t = (y - ys[i]) / max(1e-6, ys[i + 1] - ys[i])
            return side * (at_ring(rings[i]) * (1 - t) + at_ring(rings[i + 1]) * t)
    return side * at_ring(rings[-1])


def deck_z(rings, y):
    """Sheer height at y."""
    ys = [r[0][1] for r in rings]
    for i in range(len(rings) - 1):
        if ys[i] <= y <= ys[i + 1]:
            t = (y - ys[i]) / max(1e-6, ys[i + 1] - ys[i])
            return rings[i][0][2] * (1 - t) + rings[i + 1][0][2] * t
    return rings[0][0][2] if y < ys[0] else rings[-1][0][2]


def hull_plate(m, rings, side, y0, y1, z0, z1, col, t=0.015, inset=0.02):
    """Window / stripe band lying on the hull side between y0..y1, z0..z1, sampled at every station so it follows
    the hull curvature (closed thin shell: outer face t proud of the hull, inner face `inset` inside)."""
    ys = [y0] + [r[0][1] for r in rings if y0 < r[0][1] < y1] + [y1]
    secs = []
    for y in ys:
        xb, xt = abs(hull_x(rings, y, z0, side)), abs(hull_x(rings, y, z1, side))
        secs.append([(side * (xb - inset), y, z0), (side * (xb + t), y, z0), (side * (xt + t), y, z1), (side * (xt - inset), y, z1)])
    return m.loft(secs, col)


# ---------------------------------------------------------------------- material / object / export
def atlas_path(family, variant='A'):
    return LIB / 'atlases' / f'MW86_{family}_{variant}.png'


def family_material(family):
    name = f'MW86_{family}'
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tex = nt.nodes.new('ShaderNodeTexImage')
    img = bpy.data.images.load(str(atlas_path(family, 'A')), check_existing=True)
    img.colorspace_settings.name = 'sRGB'
    tex.image = img
    tex.interpolation = 'Linear'
    tex.extension = 'EXTEND'
    nt.links.new(tex.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.8
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = 0.25
    m.diffuse_color = (0.7, 0.7, 0.7, 1.0)
    return m


def _face_uvs(family, verts, face, token, obox):
    """UVs for one face: palette cell point, '@' object projection or '#' face fit into a pattern region."""
    if not token or token[0] not in '@#':
        u, v = PAL.cell_uv(family, token or 'grey')
        return [(u, v)] * len(face)
    mode, pname = token[0], token[1:]
    u0, v0, u1, v1 = PAL.region_uv(family, pname)
    pts = [Vector(verts[i]) for i in face]
    n = Vector()
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n += Vector(((a.y - b.y) * (a.z + b.z), (a.z - b.z) * (a.x + b.x), (a.x - b.x) * (a.y + b.y)))
    ax = max(range(3), key=lambda k: abs(n[k]))
    ia, ib = {0: (1, 2), 1: (0, 2), 2: (0, 1)}[ax]
    if mode == '@':
        lo, hi = obox
    else:
        lo = [min(p[k] for p in pts) for k in range(3)]
        hi = [max(p[k] for p in pts) for k in range(3)]
    out = []
    for p in pts:
        a = (p[ia] - lo[ia]) / max(1e-6, hi[ia] - lo[ia])
        b = (p[ib] - lo[ib]) / max(1e-6, hi[ib] - lo[ib])
        a, b = min(1, max(0, a)), min(1, max(0, b))
        out.append((u0 + a * (u1 - u0), v0 + b * (v1 - v0)))
    return out


def make_object(name, mesh, family, coll, obox=None, offset=(0, 0, 0)):
    off = Vector(offset)
    verts = [tuple(Vector(v) + off) for v in mesh.verts]
    if obox is None:
        lo = [min(v[k] for v in verts) for k in range(3)]
        hi = [max(v[k] for v in verts) for k in range(3)]
        obox = (lo, hi)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [list(f) for f in mesh.faces])
    me.materials.append(family_material(family))
    uv = me.uv_layers.new(name='UVMap')
    loops = []
    for p, f, tok in zip(me.polygons, mesh.faces, mesh.fcol):
        loops += _face_uvs(family, verts, f, tok, obox)
    flat = [c for uvp in loops for c in uvp]
    uv.data.foreach_set('uv', flat)
    me.polygons.foreach_set('use_smooth', [False] * len(me.polygons))
    me.update()
    # consistent outward normals per closed shell, then triangulate (exact tri count, concave caps safe in Unity)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='EAR_CLIP')
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def analyse(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    tris = len(bm.faces)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    bm.free()
    co = [v.co for v in ob.data.vertices]
    lo = [min(c[k] for c in co) for k in range(3)]
    hi = [max(c[k] for c in co) for k in range(3)]
    return {'triangles': tris, 'vertices': len(co), 'non_manifold_edges': nonman, 'zero_area_faces': zero,
            'bounds_min': [round(x, 3) for x in lo], 'bounds_max': [round(x, 3) for x in hi],
            'size_xyz_m': [round(hi[k] - lo[k], 3) for k in range(3)]}


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    return sc


def export_asset(spec, build, out_root, fbx_dir, force=False):
    """spec: dict(name, family, kind 'ground'|'water', budget (lod0 max), folder, notes, target (x, y, z) or None).
    build(lod) -> Mesh. Writes <folder>/<name>_v01.blend, validation json, and <fbx_dir>/<name>_v01.fbx."""
    name, fam = spec['name'], spec['family']
    rev = spec.get('rev', 'v01')
    folder = Path(out_root) / spec['folder']
    folder.mkdir(parents=True, exist_ok=True)
    Path(fbx_dir).mkdir(parents=True, exist_ok=True)
    blend = folder / f'{name}_{rev}.blend'
    fbx = Path(fbx_dir) / f'{name}_{rev}.fbx'
    if not force:
        for p in (blend, fbx):
            if p.exists():
                raise SystemExit(f'refusing to overwrite {p}')
    sc = reset_scene()
    m0, m1 = build(0), build(1)
    # footprint centre -> origin; ground models stand on z = 0, water models keep their waterline z = 0
    lo = [min(v[k] for v in m0.verts) for k in range(3)]
    hi = [max(v[k] for v in m0.verts) for k in range(3)]
    off = (-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2] if spec['kind'] == 'ground' else 0.0)
    obox = ([lo[k] + off[k] for k in range(3)], [hi[k] + off[k] for k in range(3)])
    coll = bpy.data.collections.new(name)
    sc.collection.children.link(coll)
    o0 = make_object(f'{name}_LOD0', m0, fam, coll, obox, off)
    o1 = make_object(f'{name}_LOD1', m1, fam, coll, obox, off)
    a0, a1 = analyse(o0), analyse(o1)
    budget = spec['budget']
    checks = {
        'lod0_within_budget': a0['triangles'] <= budget,
        'lod1_ratio_25_55pct': 0.25 <= a1['triangles'] / a0['triangles'] <= 0.55,
        'pivot_footprint_centred': abs(a0['bounds_min'][0] + a0['bounds_max'][0]) < 0.02 and abs(a0['bounds_min'][1] + a0['bounds_max'][1]) < 0.02,
        'no_zero_area_faces': a0['zero_area_faces'] == 0 and a1['zero_area_faces'] == 0,
    }
    if spec['kind'] == 'ground':
        checks['base_on_ground_z0'] = abs(a0['bounds_min'][2]) < 0.005 and a1['bounds_min'][2] > -0.005
    tgt = spec.get('target')
    if tgt:
        tol = spec.get('tol_m', 0.05)
        checks['footprint_within_data_box_+5pct'] = all(a0['size_xyz_m'][k] <= tgt[k] * 1.05 + tol for k in range(2))
    # save .blend (LOD1 hidden, moved aside only visually via hide)
    o1.hide_render = True
    o1.hide_set(True)
    img = family_material(fam).node_tree.nodes['Image Texture'].image if 'Image Texture' in family_material(fam).node_tree.nodes else None
    if img:
        img.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    o1.hide_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    o0.select_set(True); o1.select_set(True)
    bpy.context.view_layer.objects.active = o0
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                             axis_forward='-Z', axis_up='Y', apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
                             bake_space_transform=True, use_mesh_modifiers=False, mesh_smooth_type='FACE',
                             add_leaf_bones=False, bake_anim=False, colors_type='NONE', path_mode='STRIP',
                             embed_textures=False, use_custom_props=False)
    rep = {
        'asset': name, 'family': fam, 'revision': rev, 'blender': bpy.app.version_string,
        'kind': spec['kind'],
        'pivot': 'footprint centre on the ground (z=0)' if spec['kind'] == 'ground' else 'footprint centre on the WATERLINE (z=0); hull below',
        'axes': 'Blender Z up, nose -Y; FBX axis_forward=-Z, axis_up=Y, FBX_SCALE_ALL, apply transform -> Unity: nose +Z, Y up, 1 unit = 1 m',
        'offset_applied_to_builder_coords': [round(x, 4) for x in off],
        'lod0': a0, 'lod1': a1, 'lod1_ratio': round(a1['triangles'] / a0['triangles'], 3),
        'triangle_budget_lod0': budget, 'data_box_target_xyz': tgt,
        'material': f'MW86_{fam}', 'textures': [f'MW86_{fam}_{v}.png' for v in PAL.VARIANTS],
        'files': {'fbx': str(fbx), 'blend': str(blend)}, 'notes': spec.get('notes', ''),
        'checks': checks, 'all_checks_passed': all(checks.values()),
    }
    (folder / f'validation_{name}_{rev}.json').write_text(json.dumps(rep, indent=2, ensure_ascii=False), encoding='utf-8')
    flag = 'OK ' if rep['all_checks_passed'] else 'FAIL'
    print(f'[MW86] {flag} {name:28s} LOD0 {a0["triangles"]:5d} LOD1 {a1["triangles"]:5d} ({rep["lod1_ratio"]:.2f}) size {a0["size_xyz_m"]} '
          + ' '.join(k for k, v in checks.items() if not v), flush=True)
    return rep


def run_family(specs, builders):
    """CLI: blender -b --factory-startup -P build_x.py -- --out-root DIR --fbx-dir DIR [--only a,b] [--force]"""
    import argparse
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-root', required=True)
    ap.add_argument('--fbx-dir', required=True)
    ap.add_argument('--only', default='')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args(argv)
    only = {s for s in a.only.split(',') if s}
    reps = []
    for spec in specs:
        if only and spec['name'] not in only:
            continue
        reps.append(export_asset(spec, builders[spec['name']], a.out_root, a.fbx_dir, a.force))
    bad = [r['asset'] for r in reps if not r['all_checks_passed']]
    print(f'[MW86] done {len(reps)} assets, failed: {bad or "none"}', flush=True)
