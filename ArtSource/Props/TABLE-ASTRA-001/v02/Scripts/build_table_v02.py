"""TABLE-ASTRA-001 v02: the v01 gurney (caster rig untouched) with five hinged restraint straps in the original
charcoal flat-band style, fitted to the TABLE_REST patient pose. Blender 5.2, background:

blender -b --factory-startup --python build_table_v02.py [-- --out <dir>] [--rest <Patient_TableRest_v01.blend>]

Writes (refuses to overwrite): TABLE-ASTRA-001_v02.blend, TABLE-ASTRA-001_v02.fbx, table_rest_contract_v01.json.

Strap convention (every strap): object origin = hinge point on the pad's outer top edge, local +X = hinge axis
(along the table edge), local +Y = inward across the pad, local +Z = up. A positive rotation about local +X opens the
strap (inner end lifts, flips up and outward). Same sign in Unity (rotation about the strap's local X).
"""
import bisect
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

from v02_common import (P, RIG_NAME, PATIENT_MESHES, INC_NAMES, V02, TABLE_V01_BLEND, clean_scene, ensure_collection,
                        load_table, bvh_world, refuse_overwrite, rnd, log, unity_pos, unity_quat, unity_euler,
                        argv_after_dashes, tri_count, C_B2U)
from pose_lib_v01 import vertex_regions

ARGS = argv_after_dashes()
OUT_DIR = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else V02
REST_BLEND = Path(ARGS[ARGS.index("--rest") + 1]) if "--rest" in ARGS else V02 / "Patient_TableRest_v01.blend"
OUT_BLEND = OUT_DIR / "TABLE-ASTRA-001_v02.blend"
OUT_FBX = OUT_DIR / "TABLE-ASTRA-001_v02.fbx"
OUT_CONTRACT = OUT_DIR / "table_rest_contract_v01.json"

W = 0.076          # band width (original 7.4-7.6 cm)
T = 0.010          # band thickness (original ~1 cm)
C_BODY = 0.0072    # closed clearance band underside -> body
C_PAD = 0.0015     # band underside -> pad where it lies on the pad
R_CLOSE = 0.012    # bridging radius (band cannot follow concavities tighter than this)
OPEN_DEG = 120.0
DU = 0.002
BUCKLE_LEN, BUCKLE_H, BUCKLE_CH = 0.056, 0.013, 0.004

ARM_REGIONS = {"upper_arm", "forearm", "hand"}
LEG_REGIONS = {"thigh", "calf", "foot"}

# name, hinge side (table X sign), centre Y (table-local, head end = -Y), kind
STRAPS = [
    ("STRAP_ARM_L", -1, -0.045, "arm"),     # distal forearm
    ("STRAP_ARM_R", +1, -0.045, "arm"),
    ("STRAP_LEG_L", -1, 0.620, "leg"),      # shin above the ankle
    ("STRAP_LEG_R", +1, 0.620, "leg"),
    ("STRAP_TORSO", -1, 0.055, "torso"),    # pelvis / shorts, also over both wrists; below the kidney openings
]
STRAP_ORDER = ["STRAP_ARM_L", "STRAP_ARM_R", "STRAP_LEG_L", "STRAP_LEG_R", "STRAP_TORSO"]


# ----------------------------------------------------------------------------------------------- scene loading
def load_rest_patient():
    coll = ensure_collection("REFERENCE_PATIENT_TABLE_REST")
    names = [RIG_NAME, *PATIENT_MESHES, *INC_NAMES]
    with bpy.data.libraries.load(str(REST_BLEND), link=False) as (src, dst):
        dst.objects = names
    objs = {}
    for ob in dst.objects:
        coll.objects.link(ob)
        objs[ob.name] = ob
    rig = objs[RIG_NAME]
    assert rig.animation_data and rig.animation_data.action and rig.animation_data.action.name == "Patient_TableRest"
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return objs


def evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    eo = ob.evaluated_get(dg)
    me = eo.to_mesh()
    mw = ob.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    eo.to_mesh_clear()
    return verts, polys


def build_body_bvhs(pt):
    """Whole-body BVH plus per-limb BVHs (faces whose vertices all belong to the limb on one side)."""
    allv, allp = [], []
    limb = {("arm", -1): ([], []), ("arm", 1): ([], []), ("leg", -1): ([], []), ("leg", 1): ([], [])}
    for n in PATIENT_MESHES:
        verts, polys = evaluated(pt[n])
        reg = vertex_regions(pt[n])
        off = len(allv)
        allv += verts
        allp += [tuple(i + off for i in p) for p in polys]
        if n != "Body":
            continue
        for kind, regs in (("arm", ARM_REGIONS), ("leg", LEG_REGIONS)):
            for p in polys:
                if all(reg[i] in regs for i in p):
                    sx = 1 if sum(verts[i].x for i in p) > 0 else -1
                    lv, lp = limb[(kind, sx)]
                    base = len(lv)
                    lv += [verts[i] for i in p]
                    lp.append(tuple(range(base, base + len(p))))
    out = {"body": BVHTree.FromPolygons(allv, allp)}
    geo = {"body": (allv, allp)}
    for k, (lv, lp) in limb.items():
        out[k] = BVHTree.FromPolygons(lv, lp)
        geo[k] = (lv, lp)
    return out, geo


def ray_down(bvh, x, y, z0=2.5):
    hit = bvh.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)))
    return hit[0].z if hit[0] is not None else None


def side_face_x(pad, y, sign, z=None):
    """Outermost |x| of the pad side face over the band width (y +- W/2) and the side-face height range."""
    best = 0.0
    for yy in (y - W / 2 - 0.003, y - W / 4, y, y + W / 4, y + W / 2 + 0.003):
        for zz in ((z,) if z else (0.55, 0.57, 0.59, 0.61, 0.63, 0.645)):
            hit = pad.ray_cast(Vector((sign * 1.0, yy, zz)), Vector((-sign, 0, 0)))
            if hit[0] is not None:
                best = max(best, abs(hit[0].x))
    return best


# ----------------------------------------------------------------------------------------------- profile fitting
def dilate(vals, r):
    n = len(vals)
    k = int(round(r / DU))
    out = [-1e9] * n
    for i in range(n):
        best = -1e9
        for d in range(-k, k + 1):
            j = i + d
            if 0 <= j < n and vals[j] > -1e8:
                best = max(best, vals[j] + math.sqrt(max(r * r - (d * DU) ** 2, 0.0)))
        out[i] = best
    return out


def erode(vals, r):
    n = len(vals)
    k = int(round(r / DU))
    out = [0.0] * n
    for i in range(n):
        best = 1e9
        for d in range(-k, k + 1):
            j = i + d
            if 0 <= j < n:
                best = min(best, vals[j] - math.sqrt(max(r * r - (d * DU) ** 2, 0.0)))
        out[i] = best
    return out


def closing(vals, r):
    return [max(a, b) for a, b in zip(erode(dilate(vals, r), r), vals)]


def douglas_peucker(pts, tol):
    if len(pts) < 3:
        return pts
    a, b = Vector(pts[0]), Vector(pts[-1])
    ab = b - a
    best, idx = -1.0, 0
    for i in range(1, len(pts) - 1):
        p = Vector(pts[i])
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
        d = (p - (a + ab * t)).length
        if d > best:
            best, idx = d, i
    if best <= tol:
        return [pts[0], pts[-1]]
    return douglas_peucker(pts[:idx + 1], tol)[:-1] + douglas_peucker(pts[idx:], tol)


def interp(poly, u):
    for (u0, z0), (u1, z1) in zip(poly, poly[1:]):
        if u0 <= u <= u1:
            return z0 if u1 == u0 else z0 + (z1 - z0) * (u - u0) / (u1 - u0)
    return poly[0][1] if u < poly[0][0] else poly[-1][1]


def surface_samples(verts, polys, y0, y1, step=0.004):
    """Dense points on the triangles that reach into the slab y0..y1."""
    out = []
    for p in polys:
        vs = [verts[i] for i in p]
        if max(v.y for v in vs) < y0 or min(v.y for v in vs) > y1:
            continue
        for k in range(1, len(vs) - 1):
            a, b, c = vs[0], vs[k], vs[k + 1]
            n = max(1, int(max((b - a).length, (c - a).length, (c - b).length) / step))
            for i in range(n + 1):
                for j in range(n + 1 - i):
                    q = a + (b - a) * (i / n) + (c - a) * (j / n)
                    if y0 <= q.y <= y1:
                        out.append(q)
    return out


def upper_hull(pts):
    """Upper convex chain of (u, h) points (Andrew's monotone chain), left to right."""
    hull = []
    for p in sorted(pts):
        while len(hull) >= 2:
            (x1, y1), (x2, y2) = hull[-2], hull[-1]
            if (x2 - x1) * (p[1] - y1) - (y2 - y1) * (p[0] - x1) >= 0:
                hull.pop()
            else:
                break
        hull.append(p)
    return hull


def one_sided_simplify(pts, tol):
    """Douglas-Peucker, then push the simplified polyline outward (along its normals) so no sample lies above it."""
    simp = douglas_peucker(pts, tol)
    worst = 0.0
    for u, z in pts:
        p = Vector((u, z))
        best = None
        for (u0, z0), (u1, z1) in zip(simp, simp[1:]):
            a, b = Vector((u0, z0)), Vector((u1, z1))
            ab = b - a
            t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
            q = a + ab * t
            d = (p - q).length
            if best is None or d < best[0]:
                nrm = Vector((-ab.y, ab.x)).normalized()
                best = (d, (p - q).dot(nrm))
        if best and best[1] > worst:
            worst = best[1]
    return (offset_polyline(simp, worst) if worst > 1e-6 else simp), worst


def fit_profile(name, sign, yc, kind, pad, geo):
    """Hinge-polar fit. Returns (hinge_world, underside polyline [(u, z)], meta); u = inward distance from the hinge.

    The underside is built as a function of the radius r from the hinge axis: at each r it sits at the smallest
    polar angle that keeps C_BODY clearance from every body sample (and C_PAD above the pad). Because the angle is a
    function of r, rotating the strap about the hinge (increasing angle) can never sweep through the body.
    """
    face = side_face_x(pad, yc, sign)
    x_h = sign * (face + 0.0065)
    ys = [yc - W / 2 - 0.004 + i * (W + 0.008) / 10 for i in range(11)]
    x_of = lambda u: x_h - sign * u
    padz_of = lambda u: max([z for z in (ray_down(pad, x_of(u), y) for y in ys) if z is not None] or [None])         if any(ray_down(pad, x_of(u), y) is not None for y in ys) else None
    z_flat = padz_of(0.032)
    z_axis = z_flat + C_PAD + T / 2
    far = side_face_x(pad, yc, -sign)
    u_wall = face + 0.0065 + far + 0.0015

    def pad_at(u):
        if u < 0.032:
            return z_flat
        if kind == "torso" and u > u_wall - 0.034:
            return padz_of(u_wall - 0.034)
        z = padz_of(u)
        return z if z is not None else z_flat

    verts, polys = geo["body"] if kind == "torso" else geo[(kind, sign)]
    samples = surface_samples(verts, polys, yc - W / 2 - C_BODY, yc + W / 2 + C_BODY)
    pol = []
    for q in samples:
        u, h = -sign * (q.x - x_h), q.z - z_axis
        pol.append((math.hypot(u, h), math.atan2(h, u)))
    pol.sort()
    rho_list = [r for r, _ in pol]
    r_lim = max(rho_list) if kind != "torso" else None
    r0 = 0.03
    if kind == "torso":
        r_end = u_wall
    else:
        r_end = r_lim + C_BODY + 0.001 + 0.010          # 1 cm tip resting on the pad beyond the limb
    rs = [r0 + i * DU for i in range(int((r_end - r0) / DU) + 1)]
    phis = []
    for r in rs:
        ph = -math.pi / 2
        # pad: underside at least C_PAD above the pad top (two fixed-point iterations on the circle)
        zz = pad_at(r) + C_PAD - z_axis
        for _ in range(2):
            ang = math.asin(max(-1.0, min(1.0, zz / r)))
            zz = pad_at(r * math.cos(ang)) + C_PAD - z_axis
        ph = max(ph, math.asin(max(-1.0, min(1.0, zz / r))))
        for rho, al in pol[bisect.bisect_left(rho_list, r - C_BODY):bisect.bisect_right(rho_list, r + C_BODY)]:
            if True:
                cosv = (r * r + rho * rho - C_BODY * C_BODY) / (2 * r * rho)
                ph = max(ph, al + math.acos(max(-1.0, min(1.0, cosv))))
        phis.append(ph)
    # polyline in (u, h); fill angular jumps with constant-radius arcs on the free side
    pts = [(0.0, -T / 2)]
    step = math.radians(5.0)
    for i, (r, ph) in enumerate(zip(rs, phis)):
        if i:
            pr, pp = rs[i - 1], phis[i - 1]
            if ph > pp + step:          # rising: climb at the previous (smaller) radius
                a = pp + step
                while a < ph:
                    pts.append((pr * math.cos(a), pr * math.sin(a)))
                    a += step
            elif ph < pp - step:        # dropping: descend at the current (larger) radius
                a = pp
                while a > ph:
                    pts.append((r * math.cos(a), r * math.sin(a)))
                    a -= step
        pts.append((r * math.cos(ph), r * math.sin(ph)))
    if kind == "torso":
        pts = upper_hull(pts)      # a taut belt: convex from the hinge, so still sweep-safe and never below the fit
    simp, shift = one_sided_simplify(pts, 0.0015)
    under = [(u, h + z_axis) for u, h in simp]
    meta = {"pad_face_abs_x": round(face, 4), "z_axis": round(z_axis, 4), "samples": len(samples),
            "outward_shift_mm": round(shift * 1000, 2), "profile_points": len(under)}
    if kind != "torso":
        meta["limb_max_radius"] = round(r_lim, 4)
        apex = max(range(len(under)), key=lambda i: under[i][1])
        meta["limb_apex_u"] = round(under[apex][0], 4)
    else:
        last_z = under[-1][1]
        under = [p for p in under if p[0] < u_wall - 0.004] + [(u_wall, last_z), (u_wall + 1e-4, 0.600)]
    return Vector((x_h, yc, 0.0)), under, meta


# ----------------------------------------------------------------------------------------------- mesh building
def offset_polyline(poly, t):
    """Offset an (u, z) polyline by t along its left normal (up for increasing u), mitred."""
    out = []
    n = len(poly)
    segs = []
    for i in range(n - 1):
        d = Vector((poly[i + 1][0] - poly[i][0], poly[i + 1][1] - poly[i][1])).normalized()
        segs.append(Vector((-d.y, d.x)))
    for i in range(n):
        if i == 0:
            nv = segs[0]
        elif i == n - 1:
            nv = segs[-1]
        else:
            m = (segs[i - 1] + segs[i]).normalized()
            nv = m / max(m.dot(segs[i]), 0.35)
        out.append((poly[i][0] + nv.x * t, poly[i][1] + nv.y * t))
    return out


def band_mesh(under, top, z_axis):
    """Rectangular-section band, flat shaded. Local: x across width (hinge axis), y = u, z = height - z_axis."""
    bm = bmesh.new()
    rows = []
    for (u0, z0), (u1, z1) in zip(under, top):
        rows.append([bm.verts.new((-W / 2, u0, z0 - z_axis)), bm.verts.new((W / 2, u0, z0 - z_axis)),
                     bm.verts.new((W / 2, u1, z1 - z_axis)), bm.verts.new((-W / 2, u1, z1 - z_axis))])
    for a, b in zip(rows, rows[1:]):
        bm.faces.new((a[0], b[0], b[1], a[1]))   # underside
        bm.faces.new((a[3], a[2], b[2], b[3]))   # top
        bm.faces.new((a[1], b[1], b[2], a[2]))   # +x side
        bm.faces.new((a[0], a[3], b[3], b[0]))   # -x side
    bm.faces.new((rows[0][0], rows[0][1], rows[0][2], rows[0][3]))
    bm.faces.new((rows[-1][3], rows[-1][2], rows[-1][1], rows[-1][0]))
    return bm


def add_buckle(bm, top, z_axis, u_c):
    """Raised chamfered buckle block hugging the band top around u_c (conforms to the band's curve)."""
    u0, u1 = u_c - BUCKLE_LEN / 2, u_c + BUCKLE_LEN / 2
    us = [u0] + [u for u, _ in top if u0 < u < u1] + [u1]
    us = sorted(set(round(u, 5) for u in us))
    if len(us) < 4:
        us = [u0, u0 + BUCKLE_LEN / 3, u0 + 2 * BUCKLE_LEN / 3, u1]
    sec = []
    for k, u in enumerate(us):
        z = interp(top, u)
        du = 0.002
        tz = Vector((2 * du, interp(top, u + du) - interp(top, u - du))).normalized()
        nv = Vector((-tz.y, tz.x))
        base = Vector((u, z)) - nv * 0.001
        hi = Vector((u, z)) + nv * BUCKLE_H
        if k == 0:
            hi += tz * BUCKLE_CH
        if k == len(us) - 1:
            hi -= tz * BUCKLE_CH
        w0, w1 = W / 2 - 0.002, W / 2 - 0.002 - BUCKLE_CH
        sec.append([bm.verts.new((-w0, base.x, base.y - z_axis)), bm.verts.new((w0, base.x, base.y - z_axis)),
                    bm.verts.new((w1, hi.x, hi.y - z_axis)), bm.verts.new((-w1, hi.x, hi.y - z_axis))])
    for a, b in zip(sec, sec[1:]):
        bm.faces.new((a[3], a[2], b[2], b[3]))
        bm.faces.new((a[1], b[1], b[2], a[2]))
        bm.faces.new((a[0], a[3], b[3], b[0]))
    bm.faces.new((sec[0][0], sec[0][1], sec[0][2], sec[0][3]))
    bm.faces.new((sec[-1][3], sec[-1][2], sec[-1][1], sec[-1][0]))


def strap_basis(sign):
    """Columns = local X (hinge axis), Y (inward), Z (up) in table-local Blender axes."""
    y_l = Vector((-sign, 0, 0))
    z_l = Vector((0, 0, 1))
    x_l = y_l.cross(z_l)
    return Matrix((x_l, y_l, z_l)).transposed()


def box(bm, mn, mx):
    v = [bm.verts.new((x, y, z)) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([v[i] for i in f])


def barrel(bm, centre, length, radius, seg=8):
    """Cylinder along table Y."""
    rings = []
    for yy in (-length / 2, length / 2):
        rings.append([bm.verts.new((centre.x + radius * math.cos(2 * math.pi * k / seg), centre.y + yy,
                                    centre.z + radius * math.sin(2 * math.pi * k / seg))) for k in range(seg)])
    for k in range(seg):
        a, b = rings[0], rings[1]
        bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[1])


# ----------------------------------------------------------------------------------------------- validation helpers
def world_bvh_of(ob):
    v, p = evaluated(ob)
    return BVHTree.FromPolygons(v, p), v, p


def underside_samples(ob, step=0.004):
    """Dense samples on downward-ish facing faces (world space)."""
    mw = ob.matrix_world
    me = ob.data
    out = []
    for poly in me.polygons:
        nrm = (mw.to_3x3() @ poly.normal).normalized()
        vs = [mw @ me.vertices[i].co for i in poly.vertices]
        if len(vs) != 4:
            continue
        a, b, c, d = vs
        nu = max(2, int((b - a).length / step) + 1)
        nv = max(2, int((d - a).length / step) + 1)
        for i in range(nu):
            for j in range(nv):
                s, t = i / (nu - 1), j / (nv - 1)
                out.append(((a.lerp(b, s)).lerp(d.lerp(c, s), t), nrm))
    return out


def sweep_check(ob, axis_world, pivot_world, deg_max, obstacles, step=5.0):
    """Rotate the strap about its hinge from 0 to deg_max and test triangle overlap with each obstacle BVH."""
    v0, polys = evaluated(ob)
    worst = {}
    for k in range(1, int(deg_max / step) + 1):
        ang = math.radians(k * step)
        R = Matrix.Rotation(ang, 4, axis_world)
        vv = [pivot_world + (R @ (v - pivot_world).to_4d()).to_3d() for v in v0]
        b = BVHTree.FromPolygons(vv, polys)
        for oname, ob_bvh in obstacles.items():
            n = len(b.overlap(ob_bvh))
            if n:
                worst.setdefault(oname, []).append(k * step)
        floor_min = min(v.z for v in vv)
        if floor_min < 0.02:
            worst.setdefault("floor", []).append(k * step)
    return worst


# ----------------------------------------------------------------------------------------------- main
def main():
    refuse_overwrite(OUT_BLEND, OUT_FBX, OUT_CONTRACT, OUT_DIR / "table_v02_build_validation.json")
    clean_scene()
    t = load_table(TABLE_V01_BLEND, "TABLE_ASTRA_v02")
    root = t["RIG_Table_Root"]
    geo_coll = bpy.data.collections["TABLE_ASTRA_Geometry"]
    mat = bpy.data.materials["MAT_Straps_Charcoal"]
    # retire the two v01 reference straps
    for n in ("GEO_Strap_01", "GEO_Strap_02"):
        me = t[n].data
        bpy.data.objects.remove(t[n], do_unlink=True)
        bpy.data.meshes.remove(me)
        t.pop(n)
    rig_snapshot = {n: [rnd(r, 6) for r in o.matrix_world] for n, o in t.items() if n.startswith("RIG_")}

    pt = load_rest_patient()
    pad, _, _ = bvh_world(t["GEO_Padded_Top"])
    frame, _, _ = bvh_world(t["GEO_Frame_And_Legs"])
    bvhs, geo = build_body_bvhs(pt)

    anchors = bmesh.new()
    report = {}
    strap_objs = {}
    for name, sign, yc, kind in STRAPS:
        hinge, under, meta = fit_profile(name, sign, yc, kind, pad, geo)
        z_axis = meta["z_axis"]
        top = offset_polyline(under, T)
        bm = band_mesh(under, top, z_axis)
        if kind == "arm":
            u_b = meta["limb_apex_u"]
        elif kind == "leg":
            u_b = 0.085
        else:
            u_b = abs(hinge.x)          # table centre line
        add_buckle(bm, top, z_axis, u_b)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = False
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        geo_coll.objects.link(ob)
        ob.parent = root
        basis = strap_basis(sign)
        pivot = Vector((hinge.x, yc, z_axis))
        ob.matrix_world = Matrix.Translation(pivot) @ basis.to_4x4()
        ob["hinge_axis"] = "local +X"
        ob["hinge_axis_local"] = [1.0, 0.0, 0.0]
        ob["open_angle_deg"] = OPEN_DEG
        ob["open_sign"] = "+ (positive rotation about local +X opens; same sign in Unity)"
        strap_objs[name] = ob
        # static anchor: side tab down the pad side face to just above the rail, plus the hinge barrel
        face = meta["pad_face_abs_x"]
        rail = ray_down(frame, sign * (face + 0.006), yc) or 0.54
        x0, x1 = sorted((sign * (face + 0.0015), sign * (face + 0.0015 + T)))
        box(anchors, (x0, yc - W / 2, rail + 0.003), (x1, yc + W / 2, z_axis - 0.004))
        barrel(anchors, pivot, W + 0.006, 0.0075)
        if kind == "torso":
            far = side_face_x(pad, yc, -sign)
            fx0, fx1 = sorted((-sign * (far + 0.0015), -sign * (far + 0.0015 + T)))
            rail_f = ray_down(frame, -sign * (far + 0.006), yc) or 0.54
            box(anchors, (fx0, yc - W / 2, rail_f + 0.003), (fx1, yc + W / 2, 0.5985))
        report[name] = {"kind": kind, "hinge_side_table_x_sign": sign, "centre_y": yc, "z_axis": round(z_axis, 4),
                        **meta, "tris": tri_count(ob)}
        log(name, report[name])

    bmesh.ops.recalc_face_normals(anchors, faces=anchors.faces)
    me = bpy.data.meshes.new("GEO_Strap_Anchors")
    anchors.to_mesh(me)
    anchors.free()
    for p in me.polygons:
        p.use_smooth = False
    me.materials.append(mat)
    anc = bpy.data.objects.new("GEO_Strap_Anchors", me)
    geo_coll.objects.link(anc)
    anc.parent = root
    bpy.context.view_layer.update()

    # ------------------------------------------------------------------ validation
    anc_bvh, _, _ = world_bvh_of(anc)
    others = {"pad": pad, "frame": frame}
    for n in ("GEO_Push_Handle_Foot", "GEO_Lower_Longitudinal_Brace_Left", "GEO_Lower_Longitudinal_Brace_Right"):
        others[n] = bvh_world(t[n])[0]
    val = {}
    for name, ob in strap_objs.items():
        sb, sv, sp = world_bvh_of(ob)
        overl = {"body": len(sb.overlap(bvhs["body"]))}
        for k, b in others.items():
            overl[k] = len(sb.overlap(b))
        overl["anchors"] = len(sb.overlap(anc_bvh))
        # clearance: underside samples -> nearest body surface
        mind, minpt = 1e9, None
        for p, nrm in underside_samples(ob):
            if nrm.z > 0.2:
                continue
            loc, _, _, d = bvhs["body"].find_nearest(p)
            if loc is not None and d < mind:
                mind, minpt = d, p
        # apex gap along the strap centre line: vertical distance band underside -> body top
        axis_w = (ob.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
        pivot = ob.matrix_world.translation.copy()
        obst = {"body": bvhs["body"], "pad": pad, **{k: v for k, v in others.items() if k != "pad"}}
        sweep = sweep_check(ob, axis_w, pivot, OPEN_DEG, obst)
        # tip position at the open angle (world)
        R = Matrix.Rotation(math.radians(OPEN_DEG), 4, axis_w)
        open_v = [pivot + (R @ (v - pivot).to_4d()).to_3d() for v in sv]
        val[name] = {"closed_overlaps": overl, "closed_min_gap_to_body_mm": round(mind * 1000, 2),
                     "closed_min_gap_point": rnd(minpt, 3) if minpt else None,
                     "sweep_collisions_deg": sweep,
                     "open_bounds_min": rnd([min(v[i] for v in open_v) for i in range(3)], 3),
                     "open_bounds_max": rnd([max(v[i] for v in open_v) for i in range(3)], 3),
                     "tris": tri_count(ob)}
        log("VAL", name, val[name])
    val["GEO_Strap_Anchors"] = {"tris": tri_count(anc), "overlap_body": len(anc_bvh.overlap(bvhs["body"])),
                                "overlap_frame": len(anc_bvh.overlap(frame)), "overlap_pad": len(anc_bvh.overlap(pad))}
    log("VAL anchors", val["GEO_Strap_Anchors"])
    rig_after = {n: [rnd(r, 6) for r in bpy.data.objects[n].matrix_world] for n in rig_snapshot}
    val["caster_rig_unchanged"] = rig_after == rig_snapshot

    # ------------------------------------------------------------------ save + export
    pt_coll = bpy.data.collections["REFERENCE_PATIENT_TABLE_REST"]
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    log("saved", OUT_BLEND)
    bpy.ops.object.select_all(action="DESELECT")
    tbl_coll = bpy.data.collections["TABLE_ASTRA_v02"]
    for ob in tbl_coll.all_objects:
        if ob.type in {"MESH", "EMPTY"}:
            ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, object_types={"MESH", "EMPTY"},
                             use_mesh_modifiers=True, bake_anim=False, axis_forward="-Z", axis_up="Y",
                             apply_scale_options="FBX_SCALE_UNITS", use_custom_props=True)
    log("exported", OUT_FBX)

    # ------------------------------------------------------------------ contract
    rest_metrics = json.loads((REST_BLEND.parent / "table_rest_metrics_v01.json").read_text())
    rig = pt[RIG_NAME]
    root_m = rig.matrix_world.to_3x3().normalized()
    straps_c = {}
    for name in STRAP_ORDER:
        ob = strap_objs[name]
        m3 = ob.matrix_world.to_3x3().normalized()
        axis_b = m3.col[0]
        uq = unity_quat(m3)
        straps_c[name] = {
            "hinge_axis": "local +X",
            "open_angle_deg": OPEN_DEG,
            "open_direction": "positive rotation about local +X lifts the inner end up and flips it outward",
            "blender_table_local": {"pivot": rnd(ob.matrix_world.translation, 4), "hinge_axis_dir": rnd(axis_b, 4),
                                    "rotation_euler_deg": rnd([math.degrees(a) for a in ob.matrix_world.to_euler()], 3)},
            "unity_prefab_local": {"pivot": rnd(unity_pos(ob.matrix_world.translation), 4),
                                   "local_rotation_quat_xyzw": rnd(uq, 5),
                                   "hinge_axis_dir": rnd(C_B2U @ axis_b * -1.0, 4),
                                   "note": "Unity local +X of the imported strap = -(C*X_blender); rotation about local "
                                           "+X keeps the Blender angle sign"},
        }
    contract = {
        "version": "table_rest_contract_v01",
        "date": "2026-10-16",
        "frames": {
            "blender_table_local": "RIG_Table_Root at the origin, +Z up, head end (pillow) -Y, foot end/push handle +Y, "
                                   "patient's left = -X",
            "unity_prefab_local": "OperatingTableAstra_v02 root (same frame as NetworkTableAstra root): position = "
                                  "(-x, z, -y) of Blender table-local; head end +Z, patient's left = +X",
        },
        "patient_root": {
            "object": "PatientRest (parent of the SAUSAGE_BUDDY_PATIENT_v01 model instance at identity)",
            "blender_table_local": {"location": rnd(rig.matrix_world.translation, 4), "rotation_euler_deg": [0, 0, 180]},
            "unity_prefab_local": {"localPosition": rnd(unity_pos(rig.matrix_world.translation), 4),
                                   "localEulerAngles": unity_euler(root_m), "localRotation_xyzw": rnd(unity_quat(root_m), 5)},
            "clip": "Patient_TableRest_v01.fbx take 'Buddy_Rig_Mixamo65|Patient_TableRest' (1 frame, all 65 bones; "
                    "Hips carry the lying pose relative to the rig root; do not add root motion)",
            "hips_world_blender_table_local": rest_metrics["joints_blender_table_local"]["Hips"],
        },
        "pad_surface": {
            "lying_surface_z_blender": [0.646, 0.664],
            "centre_line_z": round(ray_down(pad, 0.0, 0.0), 4),
            "edge_flat_z_at_abs_x_0_27": round(ray_down(pad, 0.27, 0.0), 4),
            "pillow_wedge": "rises from y=-0.62 (z 0.663) to y=-0.93 (z 0.789), ~24 deg; head end only",
            "unity_y": round(ray_down(pad, 0.0, 0.0), 4),
        },
        "inc_markers_in_table_rest": rest_metrics["inc_markers"],
        "straps": straps_c,
        "strap_order_for_OperatingTableStraps": STRAP_ORDER,
        "pose_contact_gaps_mm": rest_metrics["region_min_gap_above_pad_mm"],
    }
    OUT_CONTRACT.write_text(json.dumps(contract, indent=2))
    (OUT_DIR / "table_v02_build_validation.json").write_text(json.dumps({"straps": report, "validation": val}, indent=2))
    log("wrote", OUT_CONTRACT)


main()
