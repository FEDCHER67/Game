"""OperationAbdomen_v02: the one big belly opening for SAUSAGE_BUDDY_PATIENT_v02 (Blender 5.2, background).

blender -b --factory-startup --python build_abdomen_v02.py

Reads  Patient_v02/ORGANS_LAYOUT_v02.json (opening shape, INC_ABDOMEN frame, cords) and Patient_TableRest_v01.blend
       (posed body, only to sample the skin; the v02 mesh is byte-identical to v01).
Writes (refuses to overwrite) into TABLE-ASTRA-001/v02/:
  OperationAbdomen_v02.blend / .fbx, OperationAbdomen_v02_Gradient.png, OperationAbdomen_v02_validation.json

Objects (origin and axes = the INC_ABDOMEN marker: +Z skin normal / out of the body, +Y toward the head,
+X patient's left in Blender; parent each to INC_ABDOMEN with zero local position/rotation/scale 1):
  ABDOMEN_OPENING     retracted skin flaps (Buddy_Skin) + the cut face (dermis / fat / fascia / muscle bands) + the
                      peritoneal wall and the cavity floor (one gradient-textured moist material); spine ridge on the
                      floor with a kidney gutter either side
  ABDOMEN_MASK        flat lid exactly over the hole, for a stencil mask that hides the patient's belly skin inside
                      the opening (the body mesh is not cut)
  ABDOMEN_INTESTINES  a coil of soft small-bowel loops tucked under the lower rim (decor, no interaction)
  ABDOMEN_VESSELS     aorta (red, patient's left of the midline) and vena cava (purple, right) on the spine ridge
  CORD_KIDNEY_<L|R>_<A|B>  optional reference cords, hilum -> great vessel (A renal artery, B renal vein)
Placed in the file at the marker's TABLE_REST pose in table-local space, like OperationIncisions_v01.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

REPO = Path(r"C:/Dev/Game")
V02 = REPO / "ArtSource/Props/TABLE-ASTRA-001/v02"
LAYOUT = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v02/ORGANS_LAYOUT_v02.json"
REST_BLEND = V02 / "Patient_TableRest_v01.blend"
OUT_BLEND = V02 / "OperationAbdomen_v02.blend"
OUT_FBX = V02 / "OperationAbdomen_v02.fbx"
OUT_PNG = V02 / "OperationAbdomen_v02_Gradient.png"
OUT_JSON = V02 / "OperationAbdomen_v02_validation.json"
RIG_NAME = "Buddy_Rig_Mixamo65"
PATIENT_MESHES = ("Body", "Face", "Shorts")

SEG = 128
# Gradient texture rows, top (v=1) to bottom (v=0): the cut layers then the peritoneal wall getting darker with depth.
GRADIENT = [  # (v, linear-ish sRGB colour)
    (1.00, (0.86, 0.56, 0.46)),   # dermis right under the skin
    (0.955, (0.74, 0.33, 0.32)),  # dermis, darker pink line
    (0.93, (0.96, 0.86, 0.58)),   # subcutaneous fat (cream yellow)
    (0.80, (0.93, 0.79, 0.50)),
    (0.775, (0.94, 0.90, 0.84)),  # fascia, thin pale line
    (0.755, (0.62, 0.14, 0.14)),  # muscle, dark red
    (0.665, (0.52, 0.10, 0.11)),
    (0.64, (0.90, 0.52, 0.52)),   # peritoneum: glossy pink
    (0.45, (0.80, 0.36, 0.38)),
    (0.25, (0.58, 0.18, 0.22)),
    (0.08, (0.38, 0.09, 0.13)),   # deep back wall
    (0.00, (0.30, 0.06, 0.10)),
]
# Profile across the edge: (inset metres along the inward normal, height above the skin, v, part)
FLAP = [(-0.042, -0.0007), (-0.030, 0.0011), (-0.019, 0.0031), (-0.010, 0.0046), (-0.004, 0.0054), (-0.0012, 0.0052),
        (0.0, 0.0042)]
CUT = [(0.0, 0.0042, 1.0), (0.0010, 0.0024, 0.965), (0.0022, 0.0004, 0.94), (0.0042, -0.0040, 0.87), (0.0060, -0.0085, 0.80),
       (0.0068, -0.0100, 0.775), (0.0076, -0.0122, 0.75), (0.0086, -0.0162, 0.67), (0.0092, -0.0184, 0.64)]
WALL = [(0.0080, -0.028), (0.0035, -0.042), (-0.0035, -0.058), (-0.0060, -0.076)]
FLOOR_LAMBDA = [0.05, 0.11, 0.19, 0.28, 0.38, 0.49, 0.60, 0.71, 0.81, 0.89]
DEPTH_V = (-0.02, 0.64, -0.155, 0.02)   # wall/floor v: local z -0.02 -> v 0.64, z -0.155 -> v 0.02 (linear)


def log(*a):
    print("[ABD_v02]", *a, flush=True)


def refuse_overwrite(*paths):
    for p in paths:
        assert not Path(p).exists(), f"refusing to overwrite {p}"


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def clean():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def load_rest():
    with bpy.data.libraries.load(str(REST_BLEND), link=False) as (src, dst):
        dst.objects = [RIG_NAME, *PATIENT_MESHES]
    coll = bpy.data.collections.new("REFERENCE_PATIENT_TABLE_REST")
    bpy.context.scene.collection.children.link(coll)
    for ob in dst.objects:
        coll.objects.link(ob)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return {o.name: o for o in dst.objects}, coll


def body_bvh(pt):
    dg = bpy.context.evaluated_depsgraph_get()
    allv, allp = [], []
    for n in PATIENT_MESHES:
        ob = pt[n]
        eo = ob.evaluated_get(dg)
        me = eo.to_mesh()
        off = len(allv)
        allv += [ob.matrix_world @ v.co for v in me.vertices]
        allp += [tuple(i + off for i in p.vertices) for p in me.polygons]
        eo.to_mesh_clear()
    return BVHTree.FromPolygons(allv, allp)


def marker_matrix(entry):
    tb = entry["table_blender"]
    r = Matrix((tb["x_axis"], tb["y_axis"], tb["z_axis"])).transposed()
    return Matrix.Translation(tb["position"]) @ r.to_4x4()


def outline(op):
    """Lens outline in marker-local XY, counter-clockwise seen from +Z, with a natural +-2 mm wobble."""
    W, H, p, q = op["half_width_m"], op["half_length_m"], op["p"], op["q"]
    pts = []
    for k in range(SEG):
        th = 2 * math.pi * k / SEG
        t = math.sin(th)
        w = W * (1 - abs(t) ** p) ** q
        x = math.copysign(w, math.cos(th)) if abs(math.cos(th)) > 1e-9 else 0.0
        y = H * t
        wob = 0.018 * math.sin(3 * th + 0.7) + 0.014 * math.sin(7 * th + 2.1) + 0.008 * math.sin(13 * th + 0.4)
        pts.append(Vector((x * (1 + wob), y * (1 + 0.35 * wob))))
    normals = []
    for k in range(SEG):
        tng = (pts[(k + 1) % SEG] - pts[k - 1]).normalized()
        normals.append(Vector((-tng.y, tng.x)))       # inward for a CCW loop
    return pts, normals


def floor_z(x, y):
    """Back wall of the cavity (marker-local z): kidney gutters ~15 cm deep, a soft spine ridge on the midline,
    rising to the side walls and to both ends (diaphragm at the head end, pelvis at the foot end)."""
    z = -0.152
    z += 0.035 * math.exp(-(x / 0.027) ** 2)                 # vertebral column / psoas ridge
    z += 0.055 * smoothstep(0.095, 0.15, abs(x))             # side walls
    z += (0.060 if y > 0 else 0.075) * smoothstep(0.05, 0.135, abs(y))
    return z


def v_of_depth(z):
    z0, v0, z1, v1 = DEPTH_V
    return max(0.0, min(v0, v0 + (z - z0) * (v1 - v0) / (z1 - z0)))


def gradient_image():
    h, w = 256, 4
    img = bpy.data.images.new("OperationAbdomen_v02_Gradient", w, h, alpha=False)
    px = []
    for j in range(h):
        v = (j + 0.5) / h
        for a, b in zip(GRADIENT[1:], GRADIENT[:-1]):     # descending v pairs (b above a)
            if a[0] <= v <= b[0]:
                f = (v - a[0]) / max(1e-6, b[0] - a[0])
                c = [a[1][i] + (b[1][i] - a[1][i]) * f for i in range(3)]
                break
        else:
            c = GRADIENT[0][1] if v > 0.5 else GRADIENT[-1][1]
        for _ in range(w):
            px += [c[0], c[1], c[2], 1.0]
    img.pixels[:] = px
    img.filepath_raw = str(OUT_PNG)
    img.file_format = "PNG"
    img.save()
    return img


def material_interior(img):
    m = bpy.data.materials.new("MAT_Abdomen_Interior_v02")
    m["unity_base_map"] = OUT_PNG.name
    m["unity_smoothness"] = 0.7
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    tex.extension = "EXTEND"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.30          # moist; Unity URP Lit smoothness ~0.7
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.55
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.25
        bsdf.inputs["Coat Roughness"].default_value = 0.15
    return m


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def material_flat(name, srgb, rough, coat=0.0):
    """Colours are given in sRGB (as typed into a Unity material); Blender wants linear."""
    rgb = tuple(srgb_to_linear(c) for c in srgb)
    m = bpy.data.materials.new(name)
    m["unity_base_color_srgb"] = list(srgb)
    m["unity_smoothness"] = round(1.0 - rough, 2)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    if coat and "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.2
    m.diffuse_color = (*rgb, 1)
    return m


def build_opening(bvh, mw, mwi, op):
    pts, nrm = outline(op)

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
        n = (mwi.to_3x3() @ hit[1]).normalized()
        return n if n.z > 0 else -n

    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rings = []          # list of (verts, v, material)
    # The flaps may not run round the flank (|x| > 0.150) or onto the trunks' waistband (y < -0.150): compress there.
    squeeze = []
    for k in range(SEG):
        out = -nrm[k]
        rx = (0.150 - abs(pts[k].x)) / max(abs(out.x), 1e-3) if out.x * pts[k].x > 0 else 1.0
        ry = (pts[k].y + 0.150) / max(-out.y, 1e-3) if out.y < 0 else 1.0
        squeeze.append(max(0.25, min(1.0, rx / -FLAP[0][0], ry / -FLAP[0][0])))
    body_normals = {}                                     # flap vertex -> (body normal, weight of the body normal)
    for ri, (d, h) in enumerate(FLAP):
        ring = []
        for k in range(SEG):
            p = pts[k] + nrm[k] * d * squeeze[k]
            lift = 1.0 + 0.45 * abs(nrm[k].x) if ri >= 2 else 1.0     # retraction rolls the side flaps up a little more
            v = bm.verts.new((p.x, p.y, skin_h(p.x, p.y) + h * lift))
            ring.append(v)
            w = (1.0, 0.85, 0.45)[ri] if ri < 3 else 0.0
            if w > 0:
                body_normals[v] = (skin_n(p.x, p.y), w)
        rings.append((ring, None, 0))
    flap_count = len(rings)
    for ci, (d, h, v) in enumerate(CUT):
        ring = []
        for k in range(SEG):
            th = 2 * math.pi * k / SEG
            jag = 0.0009 * math.sin(23 * th + 1.3) + 0.0006 * math.sin(37 * th + 0.2)   # slightly irregular cut line
            p = pts[k] + nrm[k] * (d + jag)
            ring.append(bm.verts.new((p.x, p.y, skin_h(p.x, p.y) + h)))
        rings.append((ring, [v] * SEG, 1))
    last_wall = None
    for d, h in WALL:
        ring, vs = [], []
        for k in range(SEG):
            # retraction pulls the sides open more than the ends: the wall dips under the rim mostly at the sides
            side = abs(nrm[k].x)
            p = pts[k] + nrm[k] * (d * (0.4 + 0.6 * side) if d < 0 else d)
            z = skin_h(pts[k].x, pts[k].y) + h
            ring.append(bm.verts.new((p.x, p.y, z)))
            vs.append(v_of_depth(z))
        rings.append((ring, vs, 1))
        last_wall = [(Vector((pts[k] + nrm[k] * (d * (0.4 + 0.6 * abs(nrm[k].x)) if d < 0 else d))), ring[k].co.z) for k in range(SEG)]
    for lam in FLOOR_LAMBDA:
        ring, vs = [], []
        blend = smoothstep(0.0, 0.42, lam)
        for k in range(SEG):
            p0, z0 = last_wall[k]
            p = Vector((p0.x * (1 - lam), p0.y * (1 - 0.72 * lam)))
            z = z0 + (floor_z(p.x, p.y) - z0) * blend
            ring.append(bm.verts.new((p.x, p.y, z)))
            vs.append(v_of_depth(z))
        rings.append((ring, vs, 1))
    cy = sum(last_wall[k][0].y for k in range(SEG)) / SEG * (1 - 0.72)
    centre = bm.verts.new((0.0, cy, floor_z(0.0, cy)))
    # faces
    for ri in range(len(rings) - 1):
        (ra, va, ma), (rb, vb, mb) = rings[ri], rings[ri + 1]
        if ri == flap_count - 1:
            continue                                          # sharp cut edge: flap and cut face are separate sheets
        for k in range(SEG):
            k2 = (k + 1) % SEG
            f = bm.faces.new((ra[k], ra[k2], rb[k2], rb[k]))
            f.material_index = mb if ri >= flap_count else 0
            for loop in f.loops:
                if f.material_index == 0:
                    co = loop.vert.co
                    loop[uv].uv = (0.5 + co.x * 2.0, 0.5 + co.y * 2.0)   # planar, for a tiling skin texture
                else:
                    idx = ra.index(loop.vert) if loop.vert in ra else rb.index(loop.vert)
                    vv = (va if loop.vert in ra else vb)[idx]
                    loop[uv].uv = ((idx + 0.5) / SEG, vv)
    rl, vl, _ = rings[-1]
    for k in range(SEG):
        k2 = (k + 1) % SEG
        f = bm.faces.new((rl[k], rl[k2], centre))
        f.material_index = 1
        for loop in f.loops:
            vv = v_of_depth(loop.vert.co.z)
            loop[uv].uv = (0.5, vv)
    return bm, pts, nrm, skin_h, body_normals


def build_mask(pts, nrm, skin_h):
    bm = bmesh.new()
    ring = []
    for k in range(SEG):
        p = pts[k] - nrm[k] * 0.003               # 3 mm under the flap, so no skin sliver survives at the edge
        ring.append(bm.verts.new((p.x, p.y, skin_h(p.x, p.y) + 0.0015)))
    bm.faces.new(ring)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    return bm


def tube(bm, path, radius, segs=10):
    """Simple swept tube with rounded (hemisphere-ish) end caps along a list of points."""
    rings = []
    n = len(path)
    for i, p in enumerate(path):
        t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        a = t.orthogonal().normalized()
        b = t.cross(a)
        r = radius * (0.35 + 0.65 * math.sin(math.pi * min(1.0, min(i, n - 1 - i) / 2.0) / 2)) if i in (0, n - 1, 1, n - 2) else radius
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * j / segs) + b * math.sin(2 * math.pi * j / segs)) * r) for j in range(segs)])
    for i in range(n - 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


def catmull(points, per=8):
    pts = [Vector(p) for p in points]
    out = []
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(per):
            t = s / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def build_intestines():
    """One meandering small-bowel tube in the lower belly (rows across, rounded turns), mostly under the pubic rim."""
    bm = bmesh.new()
    rows = [(-0.078, 0.104, 0.104), (-0.098, 0.090, 0.092), (-0.117, 0.080, 0.084), (-0.138, 0.064, 0.060)]
    path = []
    for i, (y, xl, xr) in enumerate(rows):
        xs = [-xl + (xl + xr) * j / 6 for j in range(7)]
        if i % 2:
            xs.reverse()
        for j, x in enumerate(xs):
            bulge = 0.006 * math.sin(j * 1.7 + i * 1.3)
            yy = y + 0.006 * math.sin(j * 2.3 + i * 0.8)
            path.append((x, yy, -0.058 + bulge - 0.012 * (abs(x) / 0.08) ** 2))
    tube(bm, catmull(path, 6), 0.0108, 14)
    return bm


def build_vessels(layout, mwi):
    """Aorta and vena cava lying on the spine ridge (from the layout's great vessels)."""
    out = {}
    for name, v in layout["great_vessels_rest"].items():
        a, b = mwi @ Vector(v["table_blender_head"]), mwi @ Vector(v["table_blender_pubic"])
        pts = [a.lerp(b, t / 8) for t in range(9)]
        for k, p in enumerate(pts):
            p.x += 0.0025 * math.sin(k * 1.1 + (0 if name == "aorta" else 2))
        bm = bmesh.new()
        tube(bm, catmull(pts, 4), v["radius"], 14)
        out[name] = bm
    return out


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


def main():
    refuse_overwrite(OUT_BLEND, OUT_FBX, OUT_PNG, OUT_JSON)
    clean()
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    pt, refcoll = load_rest()
    bvh = body_bvh(pt)
    mw = marker_matrix(layout["table_rest"]["INC_ABDOMEN"])
    mwi = mw.inverted()
    skin = pt["Body"].data.materials[0]
    assert skin.name.startswith("Buddy_Skin"), skin.name
    img = gradient_image()
    interior = material_interior(img)
    bowel = material_flat("MAT_Abdomen_Bowel_v02", (0.90, 0.56, 0.52), 0.30, 0.35)
    artery = material_flat("MAT_Vessel_Artery_v02", (0.80, 0.16, 0.20), 0.32, 0.3)
    vein = material_flat("MAT_Vessel_Vein_v02", (0.52, 0.36, 0.66), 0.32, 0.3)
    maskm = material_flat("MAT_Abdomen_StencilMask_v02", (0.0, 1.0, 1.0), 1.0)
    coll = bpy.data.collections.new("OPERATION_ABDOMEN_v02")
    bpy.context.scene.collection.children.link(coll)

    bm, pts, nrm, skin_h, body_normals = build_opening(bvh, mw, mwi, layout["opening"])
    bm.verts.index_update()
    blend_n = {v.index: bn for v, bn in body_normals.items()}
    opening = finish(bm, "ABDOMEN_OPENING", [skin, interior], mw, coll)
    # Custom normals: the outer flap rings take the body's own normal so the flap melts into the skin (no shading seam).
    me = opening.data
    cn = []
    for v in me.vertices:
        if v.index in blend_n:
            n, w = blend_n[v.index]
            cn.append(tuple((v.normal * (1 - w) + n * w).normalized()))
        else:
            cn.append(tuple(v.normal))
    me.normals_split_custom_set_from_vertices(cn)
    mask = finish(build_mask(pts, nrm, skin_h), "ABDOMEN_MASK", [maskm], mw, coll, smooth=False)
    mask.hide_render = True
    bowels = finish(build_intestines(), "ABDOMEN_INTESTINES", [bowel], mw, coll)
    vb = build_vessels(layout, mwi)
    bmv = bmesh.new()
    me_tmp = []
    for name, bm in vb.items():
        me = bpy.data.meshes.new("tmp_" + name)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.material_index = 0 if name == "aorta" else 1
        me_tmp.append(me)
    for me in me_tmp:
        bmv.from_mesh(me)
        bpy.data.meshes.remove(me)
    vessels = finish(bmv, "ABDOMEN_VESSELS", [artery, vein], mw, coll)

    # optional reference cords, from the layout (table frame -> marker-local)
    cords = []
    for kid, side in (("INC_KIDNEY_L", "L"), ("INC_KIDNEY_R", "R")):
        for cname, cd in layout["organs"][kid]["cords"].items():
            a = mwi @ Vector(cd["table_blender_start"])
            b = mwi @ Vector(cd["table_blender_end"])
            mid = a.lerp(b, 0.5) + Vector((0, 0, -0.003))
            bm = bmesh.new()
            tube(bm, catmull([a, mid, b], 8), cd["radius_m"], 10)
            cords.append(finish(bm, f"CORD_KIDNEY_{side}_{cname[0]}", [artery if cname[0] == "A" else vein], mw, coll))

    for ob in coll.objects:
        ob["marker"] = "INC_ABDOMEN"

    # ---- validation
    def tris(ob):
        return sum(len(p.vertices) - 2 for p in ob.data.polygons)

    # flap height above the skin (should be >= -0.7 mm, the tucked outer ring)
    flap_heights = []
    for p in opening.data.polygons:
        if p.material_index == 0:
            for i in p.vertices:
                co = opening.data.vertices[i].co
                flap_heights.append(co.z - skin_h(co.x, co.y))
    zs = [v.co.z for v in opening.data.vertices]
    # body thickness behind the floor: cast from the deepest floor points toward the back
    back_gap = []
    for v in opening.data.vertices:
        if v.co.z < -0.12:
            o = mw @ v.co
            d = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
            hit = bvh.ray_cast(o, d, 0.5)
            back_gap.append(hit[3] if hit[0] is not None else -1)
    vessel_gaps = {}
    for n, v in layout["great_vessels_rest"].items():
        gaps = []
        for key in ("table_blender_head", "table_blender_pubic"):
            a, b = mwi @ Vector(v[key]), None
            for t in (0.25, 0.5, 0.75):
                q = (mwi @ Vector(v["table_blender_head"])).lerp(mwi @ Vector(v["table_blender_pubic"]), t)
                gaps.append(q.z - v["radius"] - floor_z(q.x, q.y))
        vessel_gaps[n] = [round(min(gaps) * 1000, 1), round(max(gaps) * 1000, 1)]
    res = {"marker": "INC_ABDOMEN", "origin_table_blender": [round(c, 4) for c in mw.translation],
           "objects": {ob.name: {"tris": tris(ob), "materials": [m.name for m in ob.data.materials]} for ob in coll.objects},
           "flap_height_above_skin_mm": [round(min(flap_heights) * 1000, 2), round(max(flap_heights) * 1000, 2)],
           "deepest_floor_marker_local_m": round(min(zs), 4),
           "min_body_left_behind_floor_m": round(min(g for g in back_gap if g >= 0), 4) if back_gap else None,
           "floor_points_without_body_behind": sum(1 for g in back_gap if g < 0),
           "gradient_png": OUT_PNG.name,
           "vessel_bottom_minus_floor_mm": vessel_gaps}
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
    OUT_JSON.write_text(json.dumps(res, indent=2))
    log("exported", OUT_FBX)


main()
