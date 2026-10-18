"""OperationSutured_v05: the closed, stitched incision that replaces OperationAbdomen_v05 at the end of every operation
(Blender 5.2, background).

blender -b --factory-startup --python build_sutured_v05.py [-- --layout <ORGANS_LAYOUT_v05.json> --out <dir>
                                                              --patient <SAUSAGE_BUDDY_PATIENT_v05.blend>]

Same frame as the opening (origin and axes = INC_ABDOMEN, TABLE_REST skin) and the SAME outline (organs_layout_v05.outline_xy,
128 points, the v02 wobble), so Unity can swap open -> sutured in place:
  SUTURE_SKIN        skin patch over the whole opening: outline + 9 mm (the stencil mask is outline + 3 mm, so it overlaps
                     the uncut skin by 6 mm, its outer ring tucked 0.4 mm under the skin, body normals so it melts in);
                     a slightly puffy seam (two swollen lips, a thin crusted cut line) runs tip to tip along the midline.
                     Materials: [0] Buddy_Skin (= the patient's own, unstencilled skin, as on the opening flap),
                     [1] MAT_Suture_Seam_v05 (swollen pink strip), [2] MAT_Suture_Cut_v05 (crusted cut line).
  SUTURE_STITCH_01..N  one cartoon cross-stitch each (two thread arms crossing over the seam, a knot with two short tails,
                     four dark entry dots), ordered from the head end (01) to the pubic end (N). Custom properties:
                     order, progress_start, progress_end (0..1), centre_local. Show the first round(N * p) for progress p.
  SUTURE_THREAD_ALL  the same N stitches merged into one mesh; UV channel 2 ("Progress", Unity UV1): u = position along the
                     seam in stitch order (0 = head end, 1 = pubic end; inside a stitch: arm A, arm B, knot), v = 0.
                     A shader can clip u > _Progress to animate stitching with a single renderer.
  SUTURE_BLOOD       a little dried blood along the seam (flat blobs 0.25 mm above the skin), UV2 u = seam progress too.
Writes (refuses to overwrite) into TABLE-ASTRA-001/v05/:
  OperationSutured_v05.blend / .fbx, OperationSutured_v05.json
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
_src = (HERE / "build_abdomen_v05.py").read_text(encoding="utf-8")
assert _src.rstrip().endswith("main()")
ABD = {"__name__": "abd_v05", "__file__": str(HERE / "build_abdomen_v05.py")}
exec(compile(_src.rstrip()[:-len("main()")], str(HERE / "build_abdomen_v05.py"), "exec"), ABD)
LAY = ABD["LAY"]

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUTDIR = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else ABD["REPO"] / "ArtSource/Props/TABLE-ASTRA-001/v05"
OUT_BLEND, OUT_FBX, OUT_JSON = OUTDIR / "OperationSutured_v05.blend", OUTDIR / "OperationSutured_v05.fbx", OUTDIR / "OperationSutured_v05.json"
SEG = ABD["SEG"]
PATCH_OUT = 0.009          # patch boundary: outline + 9 mm (mask = outline + 3 mm)
COLS = [0.0, 0.0035, 0.009, 0.017, 0.028, 0.042, 0.060, 0.083, 0.11, 0.145, 0.19, 0.245, 0.31, 0.385, 0.47, 0.56, 0.65,
        0.74, 0.82, 0.885, 0.935, 0.97, 0.99, 1.0]           # column fractions of the row half width (dense at the seam)
ROW_STEP = 0.004
STITCH_PITCH = 0.0155      # one cross-stitch every 15.5 mm along the seam
THREAD_R = 0.0011          # cartoon-thick thread (2.2 mm), readable from the table camera
ARM_W, ARM_S = 0.0085, 0.0042


def log(*a):
    print("[SUTURE_v05]", *a, flush=True)


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def poly_offset(pts, nrm, d):
    return [Vector((p.x - n.x * d, p.y - n.y * d)) for p, n in zip(pts, nrm)]


def row_interval(poly, y):
    xs = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a.y > y) != (b.y > y):
            xs.append(a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y))
    return (min(xs), max(xs)) if len(xs) >= 2 else None


def dist_poly(x, y, poly):
    best = 9.0
    for a, b in zip(poly, poly[1:] + poly[:1]):
        dx, dy = b.x - a.x, b.y - a.y
        t = max(0.0, min(1.0, ((x - a.x) * dx + (y - a.y) * dy) / max(1e-12, dx * dx + dy * dy)))
        best = min(best, math.hypot(x - (a.x + t * dx), y - (a.y + t * dy)))
    return best


def in_poly(x, y, poly):
    c = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a.y > y) != (b.y > y) and x < (b.x - a.x) * (y - a.y) / (b.y - a.y) + a.x:
            c = not c
    return c


class Surface:
    """Skin height (marker-local z) of the posed body + the seam relief, shared by the patch, the stitches and the blood."""

    def __init__(self, skin_h, skin_n, y_top, y_bot, outer):
        self.skin_h, self.skin_n, self.y_top, self.y_bot, self.outer = skin_h, skin_n, y_top, y_bot, outer
        self.cache = {}

    def taper(self, y):
        return smoothstep(self.y_bot, self.y_bot + 0.022, y) * smoothstep(self.y_top, self.y_top - 0.022, y)

    def ridge(self, x, y):
        t = self.taper(y)
        if t <= 0:
            return 0.0
        ax = abs(x)
        lips = 0.0017 * math.exp(-((ax - 0.0032) / 0.0030) ** 2)          # two swollen lips
        swell = 0.0009 * math.exp(-(ax / 0.012) ** 2)                       # the puffy seam
        groove = -0.0006 * math.exp(-(ax / 0.0010) ** 2)                    # the closed cut line between the lips
        return t * (lips + swell + groove)

    def lift(self, x, y):
        """Patch height above the skin: tucked 0.4 mm under it at the outer edge, +0.4 mm over the masked hole."""
        d = dist_poly(x, y, self.outer)
        return -0.0004 + 0.0008 * smoothstep(0.0003, 0.0020, d)

    def base(self, x, y):
        k = (round(x, 5), round(y, 5))
        if k not in self.cache:
            self.cache[k] = self.skin_h(x, y)
        return self.cache[k]

    def z(self, x, y):
        return self.base(x, y) + self.lift(x, y) + self.ridge(x, y)


def build_patch(surf, outer, y_seam):
    ys = [p.y for p in outer]
    y0, y1 = min(ys), max(ys)
    nrow = max(8, int(round((y1 - y0) / ROW_STEP)))
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    uvp = bm.loops.layers.uv.new("Progress")
    rows = []
    for j in range(1, nrow):
        y = y0 + (y1 - y0) * j / nrow
        iv = row_interval(outer, y)
        if iv is None or iv[1] - iv[0] < 1e-4:
            continue
        xl, xr = iv
        xs = [xl * f for f in reversed(COLS[1:])] + [0.0] + [xr * f for f in COLS[1:]]
        rows.append([bm.verts.new((x, y, surf.z(x, y))) for x in xs])
    tip_b = bm.verts.new((0.0, y0, surf.z(0.0, y0 + 1e-4)))
    tip_t = bm.verts.new((0.0, y1, surf.z(0.0, y1 - 1e-4)))
    faces = []
    for a, b in zip(rows, rows[1:]):
        for k in range(len(a) - 1):
            faces.append(bm.faces.new((a[k], a[k + 1], b[k + 1], b[k])))
    for k in range(len(rows[0]) - 1):
        faces.append(bm.faces.new((rows[0][k + 1], rows[0][k], tip_b)))
    for k in range(len(rows[-1]) - 1):
        faces.append(bm.faces.new((rows[-1][k], rows[-1][k + 1], tip_t)))
    seam_top, seam_bot = y_seam
    for f in faces:
        c = f.calc_center_median()
        t = surf.taper(c.y)
        ax = abs(c.x)
        if t > 0.05 and ax < 0.0011 and seam_bot < c.y < seam_top:
            f.material_index = 2                       # crusted cut line
        elif t > 0.05 and ax < 0.0062 * (0.55 + 0.45 * t):
            f.material_index = 1                       # swollen pink strip
        else:
            f.material_index = 0
        for loop in f.loops:
            co = loop.vert.co
            loop[uv].uv = (0.5 + co.x * 2.0, 0.5 + co.y * 2.0)           # planar, like the opening flap
            loop[uvp].uv = (max(0.0, min(1.0, (seam_top - co.y) / (seam_top - seam_bot))), 0.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    if sum(f.normal.z for f in bm.faces) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.normal_update()
    return bm


def tube_path(bm, path, radius, segs, ring_scale=None):
    """Swept tube with closed ends; returns the created verts in path order (rings)."""
    rings = []
    n = len(path)
    for i, p in enumerate(path):
        t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized()
        b = t.cross(a)
        r = radius * (ring_scale[i] if ring_scale else 1.0)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * j / segs) + b * math.sin(2 * math.pi * j / segs)) * r)
                      for j in range(segs)])
    for i in range(n - 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    return rings


def blob(bm, surf, cx, cy, r, seed, lift=0.00025, n=10, sx=1.0, sy=1.0):
    """Flat irregular decal blob (outer ring, half-size inner ring, centre) that follows the seam relief."""
    rnd = random.Random(seed)
    outer, inner = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r * (0.70 + 0.45 * rnd.random())
        dx, dy = sx * rr * math.cos(a), sy * rr * math.sin(a) * (0.8 + 0.4 * rnd.random())
        for ring, f in ((outer, 1.0), (inner, 0.5)):
            x, y = cx + dx * f, cy + dy * f
            ring.append(bm.verts.new((x, y, surf.z(x, y) + lift)))
    c = bm.verts.new((cx, cy, surf.z(cx, cy) + lift + 0.00005))
    faces = [bm.faces.new((outer[k], outer[(k + 1) % n], inner[(k + 1) % n], inner[k])) for k in range(n)]
    faces += [bm.faces.new((inner[k], inner[(k + 1) % n], c)) for k in range(n)]
    return faces


def build_stitch(surf, cy, order, count):
    """One cross-stitch centred on the seam at y = cy: arm A (patient right-head -> left-pubic... i.e. a diagonal), arm B over
    it, a knot with two tails at the patient-left end of arm B, four entry dots. Returns (bmesh, per-vertex progress)."""
    bm = bmesh.new()
    prog = {}
    p0, p1 = (order - 1) / count, order / count

    def arm(xa, ya, xb, yb, over, part):
        pts = []
        m = 12
        for i in range(m + 1):
            t = i / m
            x, y = xa + (xb - xa) * t, ya + (yb - ya) * t
            arch = 0.0011 * math.sin(math.pi * t) + over * math.sin(math.pi * t) ** 1.5
            dip = -0.0006 * (1 - smoothstep(0.0, 0.12, t)) - 0.0006 * smoothstep(0.88, 1.0, t)
            pts.append(Vector((x, y, surf.z(x, y) + THREAD_R * 0.9 + arch + dip)))
        scale = [0.75 if i in (0, m) else 1.0 for i in range(m + 1)]
        rings = tube_path(bm, pts, THREAD_R, 8, scale)
        for i, ring in enumerate(rings):
            for v in ring:
                prog[v] = p0 + (p1 - p0) * (part + i / m) / 3.0
    arm(-ARM_W, cy + ARM_S, ARM_W, cy - ARM_S, 0.0, 0)
    arm(-ARM_W, cy - ARM_S, ARM_W, cy + ARM_S, 2.3 * THREAD_R, 1)
    # knot + tails at the +X end of arm B
    kx, ky = ARM_W + 0.0012, cy + ARM_S + 0.0006
    kz = surf.z(kx, ky) + 0.0011
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.0017)
    for v in res["verts"]:
        v.co = Vector((kx + v.co.x, ky + v.co.y * 0.85, kz + v.co.z * 0.7))
        prog[v] = p0 + (p1 - p0) * (2.0 + 0.5) / 3.0
    for k, ang in enumerate((0.55, -0.35)):
        d = Vector((math.cos(ang), math.sin(ang), 0.0))
        pts = [Vector((kx, ky, kz)) + d * (0.0012 + 0.0016 * i) + Vector((0, 0, 0.0009 * i * (1 - i / 3.0))) for i in range(4)]
        rings = tube_path(bm, pts, 0.00062, 6, [1.0, 1.0, 0.9, 0.6])
        for i, ring in enumerate(rings):
            for v in ring:
                prog[v] = p0 + (p1 - p0) * (2.5 + 0.5 * i / 3) / 3.0
    thread_faces = set(bm.faces)
    for j, (ex, ey) in enumerate(((-ARM_W, cy + ARM_S), (ARM_W, cy - ARM_S), (-ARM_W, cy - ARM_S), (ARM_W, cy + ARM_S))):
        for f in blob(bm, surf, ex, ey, 0.0011, order * 10 + j, lift=0.0003, n=8):
            f.material_index = 1
            for v in f.verts:
                prog[v] = p0 + (p1 - p0) * (0.0 if j < 2 else 1.0 / 3.0)
    for f in thread_faces:
        f.material_index = 0
    return bm, prog


def trunk_bvh(body):
    """Posed trunk island of the Body only (the head capsule overlaps the top of the chest: a ray down from above the
    patch's top tip would land on the chin instead of the chest skin), triangulated, with the body's own smooth corner
    normals so the patch can copy the exact shading normal of the skin it covers."""
    from mathutils.bvhtree import BVHTree
    me0 = body.data
    parent = list(range(len(me0.vertices)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for e in me0.edges:
        a, b = find(e.vertices[0]), find(e.vertices[1])
        if a != b:
            parent[a] = b
    roots = [find(i) for i in range(len(me0.vertices))]
    big = max(set(roots), key=roots.count)
    dg = bpy.context.evaluated_depsgraph_get()
    eo = body.evaluated_get(dg)
    me = eo.to_mesh()
    me.calc_loop_triangles()
    m3 = body.matrix_world.to_3x3().inverted().transposed()
    vs = [body.matrix_world @ v.co for v in me.vertices]
    cn = [(m3 @ c.vector).normalized() for c in me.corner_normals]
    tris = [(tuple(lt.vertices), tuple(lt.loops)) for lt in me.loop_triangles if roots[lt.vertices[0]] == big]
    eo.to_mesh_clear()
    bvh = BVHTree.FromPolygons(vs, [t[0] for t in tris])

    def smooth_normal(hit, index):
        (a, b, c), (la, lb, lc) = tris[index]
        pa, pb, pc = vs[a], vs[b], vs[c]
        v0, v1, v2 = pb - pa, pc - pa, hit - pa
        d00, d01, d11, d20, d21 = v0.dot(v0), v0.dot(v1), v1.dot(v1), v2.dot(v0), v2.dot(v1)
        den = max(1e-20, d00 * d11 - d01 * d01)
        wb = (d11 * d20 - d01 * d21) / den
        wc = (d00 * d21 - d01 * d20) / den
        wa = 1.0 - wb - wc
        return (cn[la] * wa + cn[lb] * wb + cn[lc] * wc).normalized()
    return bvh, smooth_normal


def finish(bm, name, mats, mw, coll, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.matrix_world = mw
    return ob


def progress_uv(ob, prog_by_index, name="Progress"):
    me = ob.data
    if "UVMap" not in me.uv_layers:
        me.uv_layers.new(name="UVMap")
    lay = me.uv_layers.new(name=name)
    for loop in me.loops:
        lay.data[loop.index].uv = (prog_by_index[loop.vertex_index], 0.0)


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    for p in (OUT_BLEND, OUT_FBX, OUT_JSON):
        assert not p.exists(), f"refusing to overwrite {p}"
    ABD["clean"]()
    layout = json.loads(ABD["LAYOUT"].read_text(encoding="utf-8"))
    op = layout["opening_abdomen"]
    pt, refcoll = ABD["load_rest"]()
    bvh, smooth_normal = trunk_bvh(pt["Body"])
    mw = ABD["marker_matrix"](layout["table_rest"]["INC_ABDOMEN"])
    mwi = mw.inverted()
    skin = pt["Body"].data.materials[0]
    assert skin.name.startswith("Buddy_Skin"), skin.name

    def skin_h(x, y):
        o = mw @ Vector((x, y, 0.08))
        d = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
        hit = bvh.ray_cast(o, d, 0.3)
        assert hit[0] is not None, f"no skin under ({x:.3f}, {y:.3f})"
        return (mwi @ hit[0]).z

    def skin_n(x, y):
        o = mw @ Vector((x, y, 0.08))
        d = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
        hit = bvh.ray_cast(o, d, 0.3)
        n = (mwi.to_3x3() @ smooth_normal(hit[0], hit[2])).normalized()     # the skin's own interpolated shading normal
        return n if n.z > 0 else -n

    pts, nrm = ABD["outline"](op)
    outer = poly_offset(pts, nrm, PATCH_OUT)
    mask_ring = poly_offset(pts, nrm, 0.003)
    y_top_tip, y_bot_tip = pts[SEG // 4].y, pts[3 * SEG // 4].y
    seam_top, seam_bot = y_top_tip - 0.004, y_bot_tip + 0.004
    surf = Surface(skin_h, skin_n, seam_top, seam_bot, outer)

    mf = ABD["material_flat"]
    seam_m = mf("MAT_Suture_Seam_v05", (0.90, 0.52, 0.47), 0.55)
    cut_m = mf("MAT_Suture_Cut_v05", (0.50, 0.12, 0.12), 0.45, 0.2)
    thread_m = mf("MAT_Suture_Thread_v05", (0.12, 0.15, 0.34), 0.35, 0.3)
    blood_m = mf("MAT_Suture_DriedBlood_v05", (0.40, 0.07, 0.07), 0.70)
    coll = bpy.data.collections.new("OPERATION_SUTURED_v05")
    bpy.context.scene.collection.children.link(coll)

    # ---- skin patch
    pbm = build_patch(surf, outer, (seam_top, seam_bot))
    patch = finish(pbm, "SUTURE_SKIN", [skin, seam_m, cut_m], mw, coll)
    me = patch.data
    cn = []
    for v in me.vertices:
        x, y = v.co.x, v.co.y
        w_geo = surf.taper(y) * (1 - smoothstep(0.010, 0.016, abs(x)))
        bn = skin_n(x, y)
        cn.append(tuple((v.normal * w_geo + bn * (1 - w_geo)).normalized()))
    me.normals_split_custom_set_from_vertices(cn)

    # ---- stitches (ordered head end -> pubic end)
    L = seam_top - seam_bot
    count = max(6, int(round(L / STITCH_PITCH)))
    stitches, all_bm, all_prog = [], bmesh.new(), []
    for i in range(count):
        order = i + 1
        cy = seam_top - L * (i + 0.5) / count
        sbm, prog = build_stitch(surf, cy, order, count)
        sbm.verts.index_update()
        pv = [0.0] * len(sbm.verts)
        for v, u in prog.items():
            pv[v.index] = u
        tmp = bpy.data.meshes.new("tmp")
        sbm.to_mesh(tmp)
        all_bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
        all_prog += pv
        ob = finish(sbm, f"SUTURE_STITCH_{order:02d}", [thread_m, blood_m], mw, coll)
        progress_uv(ob, pv)
        ob["order"] = order
        ob["progress_start"] = round((order - 1) / count, 5)
        ob["progress_end"] = round(order / count, 5)
        ob["centre_local"] = [0.0, round(cy, 5), round(surf.z(0.0, cy), 5)]
        stitches.append(ob)
    allob = finish(all_bm, "SUTURE_THREAD_ALL", [thread_m, blood_m], mw, coll)
    progress_uv(allob, all_prog)
    allob["stitch_count"] = count

    # ---- a little dried blood along the seam
    rnd = random.Random(505)
    bbm = bmesh.new()
    spots = []
    for k in range(16):
        y = seam_bot + 0.012 + (L - 0.024) * (k + rnd.random() * 0.8) / 16
        x = rnd.uniform(-0.003, 0.003)
        r = rnd.uniform(0.0010, 0.0022)
        spots.append((x, y, r))
    spots = [(x, y, r, 1.0, 1.0) for x, y, r in spots]
    for k in range(4):                                  # a few dried smears running off the seam to the side
        y = seam_bot + L * (0.2 + 0.2 * k) + rnd.uniform(-0.01, 0.01)
        side = 1 if k % 2 else -1
        spots.append((side * 0.0100, y, 0.0011, 3.0, 1.0))
    for k, (x, y, r, sx, sy) in enumerate(spots):
        blob(bbm, surf, x, y, r, 900 + k, lift=0.00025, n=14 if sx > 1 else 10, sx=sx, sy=sy)
    bbm.verts.index_update()
    bprog = [max(0.0, min(1.0, (seam_top - v.co.y) / L)) for v in bbm.verts]
    blood = finish(bbm, "SUTURE_BLOOD", [blood_m], mw, coll, smooth=False)
    progress_uv(blood, bprog)

    for ob in coll.objects:
        ob["marker"] = "INC_ABDOMEN"

    # ---- validation
    def tris(ob):
        return sum(len(p.vertices) - 2 for p in ob.data.polygons)

    lifts = []
    for v in me.vertices:
        lifts.append(v.co.z - surf.base(v.co.x, v.co.y))
    mask_cover = min(-dist_poly(p.x, p.y, outer) if not in_poly(p.x, p.y, outer) else dist_poly(p.x, p.y, outer) for p in mask_ring)
    under = 0
    for ob in stitches:
        for v in ob.data.vertices:
            if v.co.z < surf.base(v.co.x, v.co.y) - 0.0012:
                under += 1
    res = {"marker": "INC_ABDOMEN", "origin_table_blender": [round(c, 4) for c in mw.translation],
           "outline": "organs_layout_v05.outline_xy(OPENING, 128) - identical to OperationAbdomen_v05 / the stencil zone",
           "patch_boundary": f"outline + {PATCH_OUT * 1000:.0f} mm outward; ABDOMEN_MASK = outline + 3 mm",
           "mask_ring_inside_patch_min_mm": round(mask_cover * 1000, 2),
           "patch_height_above_skin_mm": [round(min(lifts) * 1000, 2), round(max(lifts) * 1000, 2)],
           "seam_local_y": [round(seam_bot, 4), round(seam_top, 4)], "seam_length_m": round(L, 4),
           "stitches": count, "stitch_pitch_m": round(L / count, 4), "thread_radius_m": THREAD_R,
           "stitch_vertices_deeper_than_1_2mm_under_skin": under,
           "objects": {ob.name: {"tris": tris(ob), "materials": [m.name for m in ob.data.materials],
                                 "uv": [u.name for u in ob.data.uv_layers],
                                 **({"order": ob["order"], "progress": [ob["progress_start"], ob["progress_end"]]} if "order" in ob else {})}
                       for ob in coll.objects},
           "materials_srgb": {m.name: list(m.get("unity_base_color_srgb", [])) for m in (seam_m, cut_m, thread_m, blood_m)},
           "unity": ["Put OperationSutured_v05.fbx under INC_ABDOMEN (identity), exactly where OperationAbdomen_v05 was.",
                     "Closing: hide ABDOMEN_OPENING, ABDOMEN_INTESTINES, ABDOMEN_VESSELS, CORD_* and the organs; keep ABDOMEN_MASK + the "
                     "Buddy_Skin stencil on (SUTURE_SKIN fills exactly the masked hole and overlaps the intact skin by 6 mm).",
                     "SUTURE_SKIN slot 0 'Buddy_Skin': give it the patient's ORIGINAL skin material (as OperationOpeningV02 does for the "
                     "opening flap), never the stencil copy.",
                     "Stitching animation: either enable SUTURE_STITCH_01..N in 'order' (stitch k done at progress k/N), or render "
                     "SUTURE_THREAD_ALL with a shader that clips UV1.x > _Progress (0 -> 1). SUTURE_BLOOD UV1.x = the same seam "
                     "progress (optional reveal). Import with 'Generate Lightmap UVs' OFF so UV1 is kept."]}
    log(json.dumps(res))
    refcoll.hide_render = False
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    bpy.ops.object.select_all(action="DESELECT")
    for ob in coll.objects:
        ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, object_types={"MESH"},
                             use_mesh_modifiers=True, bake_anim=False, axis_forward="-Z", axis_up="Y",
                             apply_scale_options="FBX_SCALE_UNITS", use_custom_props=True, path_mode="RELATIVE")
    OUT_JSON.write_text(json.dumps(res, indent=2), encoding="utf-8")
    log("exported", OUT_FBX)


main()
