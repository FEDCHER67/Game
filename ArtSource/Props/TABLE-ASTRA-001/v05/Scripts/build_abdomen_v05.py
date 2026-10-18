"""OperationAbdomen_v05: the bigger, lower chest + belly opening for SAUSAGE_BUDDY_PATIENT_v05 (Blender 5.2, background).

blender -b --factory-startup --python build_abdomen_v05.py [-- --layout <ORGANS_LAYOUT_v05.json> --out <dir> --organs <blend>
                                                             --patient <SAUSAGE_BUDDY_PATIENT_v05.blend>]

v04 -> v05 (Fedya's playtest, 2026-10-18): the chest + liver block moved down another 2 cm (Organs_v05) and the trunks are
low-rise (waistband rest z 0.771), so the opening runs from just under the chin (rest z 1.112) right down to the bottom of
the belly (0.787) and is wider and fuller at the chest (half width 0.134, top lens p 2.4 / q 0.32) so heart, lungs and the
ribs lie well inside it. The rim is EXACTLY the v03 rim (same flap, cut face and wall profiles, wobble and jag); only the
outline, the flap squeeze limits and the cavity floor ends change. The intestine coil is back at its v03 size (4 rows,
tube radius 10.8 mm) in the lower belly, in front of / below the kidneys.
Reads  Patient_v05/ORGANS_LAYOUT_v05.json, Patient_TableRest_v01.blend (posed body, skin sampling only) with its trunks
replaced by the v05 low-rise Shorts (posed by the same rig).
Writes (refuses to overwrite) into TABLE-ASTRA-001/v05/:
  OperationAbdomen_v05.blend / .fbx, OperationAbdomen_v05_Gradient.png, OperationAbdomen_v05_validation.json
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
sys.path.insert(0, r"C:/Dev/Game/ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v05/Scripts")
import organs_layout_v05 as LAY  # noqa: E402
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

REPO = Path(r"C:/Dev/Game")
V02 = REPO / "ArtSource/Props/TABLE-ASTRA-001/v02"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
V03 = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else REPO / "ArtSource/Props/TABLE-ASTRA-001/v05"
LAYOUT = (Path(ARGS[ARGS.index("--layout") + 1]) if "--layout" in ARGS else
          REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v05/ORGANS_LAYOUT_v05.json")
PATIENT_BLEND = (Path(ARGS[ARGS.index("--patient") + 1]) if "--patient" in ARGS else
                 REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v05/SAUSAGE_BUDDY_PATIENT_v05.blend")
REST_BLEND = V02 / "Patient_TableRest_v01.blend"
ORGANS_BLEND = (Path(ARGS[ARGS.index("--organs") + 1]) if "--organs" in ARGS else
                REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v05/Organs_v05.blend")
OUT_BLEND = V03 / "OperationAbdomen_v05.blend"
OUT_FBX = V03 / "OperationAbdomen_v05.fbx"
OUT_PNG = V03 / "OperationAbdomen_v05_Gradient.png"
OUT_JSON = V03 / "OperationAbdomen_v05_validation.json"
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
FLOOR_LAMBDA = [0.05, 0.11, 0.19, 0.28, 0.38, 0.49, 0.60, 0.71, 0.81, 0.89, 0.95]
DEPTH_V = (-0.02, 0.64, -0.155, 0.02)   # wall/floor v: local z -0.02 -> v 0.64, z -0.155 -> v 0.02 (linear)


def log(*a):
    print("[ABD_v05]", *a, flush=True)


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
    swap_shorts({o.name: o for o in dst.objects}, coll)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return {o.name: o for o in coll.objects}, coll


def swap_shorts(pt, coll):
    """v05: the table-rest file still carries the v01 trunks (waistband rest z 0.80); replace them by the v05 low-rise
    Shorts mesh (same vertex groups -> same deformation by the table-rest rig)."""
    old = pt["Shorts"]
    trig = old.parent
    before = set(bpy.data.objects)
    with bpy.data.libraries.load(str(PATIENT_BLEND), link=False) as (src, dst):
        dst.objects = ["Shorts"]
    new = dst.objects[0]
    extra = [o for o in bpy.data.objects if o not in before and o is not new]     # the patient rig dragged in by parent/modifier
    coll.objects.link(new)
    new.parent = trig
    new.parent_type = old.parent_type
    new.matrix_parent_inverse = old.matrix_parent_inverse.copy()
    new.matrix_basis = old.matrix_basis.copy()
    for m in new.modifiers:
        if m.type == "ARMATURE":
            m.object = next(mm.object for mm in old.modifiers if mm.type == "ARMATURE")
    bpy.data.objects.remove(old, do_unlink=True)
    for o in extra:
        bpy.data.objects.remove(o, do_unlink=True)
    new.name = "Shorts"


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
    """Asymmetric lens outline in marker-local XY, counter-clockwise seen from +Z, with a natural +-2 mm wobble.
    Head half (y > 0): half_length_top, exponent q_top (pointed, ends below the xiphoid); pubic half: half_length_bottom."""
    pts = [Vector(p) for p in LAY.outline_xy(op, SEG)]      # v05: shared with Patient_v05 (stencil zone) and the sutured mesh
    normals = []
    for k in range(SEG):
        tng = (pts[(k + 1) % SEG] - pts[k - 1]).normalized()
        normals.append(Vector((-tng.y, tng.x)))       # inward for a CCW loop
    return pts, normals


def floor_z(x, y):
    """Back wall of the cavity (marker-local z): kidney gutters ~15 cm deep, a soft spine ridge on the midline,
    rising to the side walls and to both ends (diaphragm at the head end, pelvis at the foot end)."""
    z = -0.155                                               # gutters / back wall
    z += 0.035 * math.exp(-(x / 0.027) ** 2)                 # vertebral column / psoas ridge
    z += 0.055 * smoothstep(0.105, 0.155, abs(x))            # side walls
    # v03: the kidneys sit lower (local y -0.10 .. +0.02), so the gutters run further toward the pelvis; the head end
    # rises earlier to the diaphragm under the liver
    # v04: the cavity stays deep under the chest (heart, lungs) and only rises right at the head and pubic ends
    # v05: the opening is longer (half lengths 0.1625): the end ramps move out with it
    z += 0.050 * smoothstep(0.130, 0.176, y) if y > 0 else 0.070 * smoothstep(0.132, 0.178, -y)
    return z


def v_of_depth(z):
    z0, v0, z1, v1 = DEPTH_V
    return max(0.0, min(v0, v0 + (z - z0) * (v1 - v0) / (z1 - z0)))


def gradient_image():
    h, w = 256, 4
    img = bpy.data.images.new("OperationAbdomen_v05_Gradient", w, h, alpha=False)
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
    m = bpy.data.materials.new("MAT_Abdomen_Interior_v05")
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
    # The flaps may not run round the flank (|x| > 0.150), onto the trunks' waistband (v05 low-rise: rest z 0.774) or
    # under the lying patient's chin (rest z chin_z(x) - 4 mm): compress there. Marker-local y ~ rest z - centre_z.
    squeeze = []
    cz = op["centre_z"]
    for k in range(SEG):
        out = -nrm[k]
        rx = (0.150 - abs(pts[k].x)) / max(abs(out.x), 1e-3) if out.x * pts[k].x > 0 else 1.0
        if out.y < 0:
            ry = (pts[k].y - (op["flap_limit_bottom_rest_z"] - cz)) / max(-out.y, 1e-3)
        else:
            ry = ((LAY.chin_z(pts[k].x) - 0.004 - cz) - pts[k].y) / max(out.y, 1e-3)
        squeeze.append(max(0.08, min(1.0, rx / -FLAP[0][0], ry / -FLAP[0][0])))
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
        blend = smoothstep(0.0, 0.32, lam)            # v03: reaches the floor sooner (steeper side walls)
        for k in range(SEG):
            p0, z0 = last_wall[k]
            # v03: the deep floor reaches further toward the pelvis (kidneys sit lower): foot half converges less
            # v03: a wider, longer deep floor so the lowered kidneys lie fully in their gutters
            p = Vector((p0.x * (1 - lam ** 1.6), p0.y * (1 - (0.72 if p0.y > 0 else 0.42) * lam)))
            z = z0 + (floor_z(p.x, p.y) - z0) * blend
            ring.append(bm.verts.new((p.x, p.y, z)))
            vs.append(v_of_depth(z))
        rings.append((ring, vs, 1))
    cy = sum(last_wall[k][0].y * (1 - (0.72 if last_wall[k][0].y > 0 else 0.42)) for k in range(SEG)) / SEG
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
    """One meandering small-bowel tube in the lower belly (rows across, rounded turns): v05 = the v03 coil again (4 rows,
    tube radius 10.8 mm, same wobble), moved to the bottom of the longer opening."""
    bm = bmesh.new()
    path = []
    for i, (y, xl, xr) in enumerate(LAY.INTESTINE_ROWS):
        xs = [-xl + (xl + xr) * j / 6 for j in range(7)]
        if i % 2:
            xs.reverse()
        for j, x in enumerate(xs):
            bulge = 0.006 * math.sin(j * 1.7 + i * 1.3)
            yy = y + 0.006 * math.sin(j * 2.3 + i * 0.8)
            path.append((x, yy, LAY.INTESTINE_DEPTH + bulge - 0.012 * (abs(x) / 0.08) ** 2))
    tube(bm, catmull(path, 6), LAY.INTESTINE_RADIUS, 14)
    return bm


def build_vessels(layout, mwi):
    """Aorta and vena cava lying on the spine ridge (from the layout's great vessels)."""
    out = {}
    for name, v in layout["great_vessels_abdominal_rest"].items():
        a, b = mwi @ Vector(v["table_blender_head"]), mwi @ Vector(v["table_blender_pubic"])
        pts = [a.lerp(b, t / 8) for t in range(9)]
        for k, p in enumerate(pts):
            p.x += 0.0025 * math.sin(k * 1.1 + (0 if name == "aorta" else 2))
        bm = bmesh.new()
        tube(bm, catmull(pts, 4), v["radius"], 14)
        out[name] = bm
    return out


def cavity_volume(opening):
    """Closed volume of the cavity (cut face + wall + floor, capped by a lid 3 cm above the skin), as a BVH in the
    opening's local frame, for inside tests."""
    bm = bmesh.new()
    bm.from_mesh(opening.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == 0], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    ext = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary])
    for v in [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]:
        v.co.z += 0.03
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bvh = BVHTree.FromBMesh(bm)
    bm.free()
    return bvh


def inside(bvh, p, ray=Vector((0.0123, 0.0071, 1.0)).normalized()):
    hits, o = 0, Vector(p)
    for _ in range(64):
        h = bvh.ray_cast(o + ray * 1e-5, ray)
        if h[0] is None:
            break
        hits += 1
        o = h[0]
    return hits % 2 == 1


def organs_vs_cavity(layout, opening, mw):
    """How much of each Organs_v05 piece lies inside the cavity volume (v04: chest and belly organs and the front of the
    ribcage are meant to be inside; the rest of a piece runs on under the rim / into the body wall)."""
    if not ORGANS_BLEND.exists():
        return {"skipped": f"{ORGANS_BLEND} not found"}
    T = Matrix(layout["table_rest_transform_rest_to_table_blender"])
    with bpy.data.libraries.load(str(ORGANS_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith(("ORGAN_", "RIB_", "STERNUM_", "DIAPHRAGM", "VESSELS_", "SPINE_"))]
    tmp = bpy.data.collections.new("_organs_check")
    bpy.context.scene.collection.children.link(tmp)
    linked = set()
    for ob in dst.objects:
        o = ob
        while o is not None and o.name not in linked:
            tmp.objects.link(o)
            linked.add(o.name)
            o = o.parent
    bpy.context.view_layer.update()
    vol = cavity_volume(opening)
    to_local = mw.inverted() @ T
    res = {}
    for ob in dst.objects:
        pts = [to_local @ (ob.matrix_world @ v.co) for v in ob.data.vertices]
        n_in = sum(1 for p in pts if inside(vol, p))
        res[ob.name] = {"verts": len(pts), "inside_cavity": n_in}
    for name in linked:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.data.collections.remove(tmp)
    return res


OPENING_OB, BODY_BVH = [None], [None]


def bowel_checks(layout, bowels, mw):
    """v05: where the v03-size bowel coil sits relative to the kidneys and their cords (marker frame): minimum gap, and how
    much of each kidney the coil hides from straight above (rays along marker +Z from the kidney's vertices)."""
    if not ORGANS_BLEND.exists():
        return {"skipped": f"{ORGANS_BLEND} not found"}
    T = Matrix(layout["table_rest_transform_rest_to_table_blender"])
    with bpy.data.libraries.load(str(ORGANS_BLEND), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.startswith(("ORGAN_KIDNEY", "ORGAN_LIVER"))]
    tmp = bpy.data.collections.new("_kidney_check")
    bpy.context.scene.collection.children.link(tmp)
    linked = set()
    for ob in dst.objects:
        o = ob
        while o is not None and o.name not in linked:
            tmp.objects.link(o)
            linked.add(o.name)
            o = o.parent
    bpy.context.view_layer.update()
    to_local = mw.inverted() @ T
    bv = [v.co.copy() for v in bowels.data.vertices]
    bowel_bvh = BVHTree.FromPolygons(bv, [p.vertices for p in bowels.data.polygons])
    res = {"bowel_local_y_range": [round(min(v.y for v in bv), 4), round(max(v.y for v in bv), 4)],
           "bowel_local_z_range": [round(min(v.z for v in bv), 4), round(max(v.z for v in bv), 4)]}
    for ob in dst.objects:
        pts = [to_local @ (ob.matrix_world @ v.co) for v in ob.data.vertices]
        gap = min(bowel_bvh.find_nearest(p)[3] for p in pts)
        hidden = sum(1 for p in pts if bowel_bvh.ray_cast(p + Vector((0, 0, 1e-4)), Vector((0, 0, 1)))[0] is not None)
        top = [p for p in pts]
        res[ob.name] = {"min_gap_to_bowel_mm": round(gap * 1000, 1), "verts_hidden_from_above_by_bowel_pct": round(100 * hidden / len(pts), 1),
                        "local_y_range": [round(min(p.y for p in top), 4), round(max(p.y for p in top), 4)],
                        "local_z_range": [round(min(p.z for p in top), 4), round(max(p.z for p in top), 4)]}
    # bowel vertices outside the cavity must stay under the skin (not poke out below/beside the opening)
    skin_gap, out_cnt = 9.0, 0
    cav = cavity_volume(OPENING_OB[0])
    for v in bv:
        if inside(cav, v):
            continue
        h = BODY_BVH[0].ray_cast(mw @ v, (mw.to_3x3() @ Vector((0, 0, 1))).normalized(), 0.5)
        if h[0] is None:
            out_cnt += 1
        else:
            skin_gap = min(skin_gap, h[3])
    res["bowel_outside_cavity_min_depth_under_skin_mm"] = round(skin_gap * 1000, 1)
    res["bowel_outside_cavity_verts_without_skin_above"] = out_cnt
    for kid in ("ORGAN_KIDNEY_L", "ORGAN_KIDNEY_R"):
        for cname, cd in layout["organs"][kid]["cords"].items():
            a = mw.inverted() @ Vector(cd["table_start"]["table_blender"])
            b = mw.inverted() @ Vector(cd["table_end"]["table_blender"])
            q = [a.lerp(b, t / 10) for t in range(11)]
            res[f"cord_{kid[-1]}_{cname[0]}"] = {
                "min_gap_to_bowel_mm": round(min(bowel_bvh.find_nearest(x)[3] for x in q) * 1000 - cd["radius_m"] * 1000, 1),
                "points_hidden_from_above_pct": round(100 * sum(1 for x in q if bowel_bvh.ray_cast(x, Vector((0, 0, 1)))[0] is not None) / 11, 1)}
    for name in linked:
        bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    bpy.data.collections.remove(tmp)
    return res


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
    V03.mkdir(parents=True, exist_ok=True)
    refuse_overwrite(OUT_BLEND, OUT_FBX, OUT_PNG, OUT_JSON)
    clean()
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    pt, refcoll = load_rest()
    bvh = body_bvh(pt)
    mw = marker_matrix(layout["table_rest"]["INC_ABDOMEN"])
    layout["opening"] = layout["opening_abdomen"]
    mwi = mw.inverted()
    skin = pt["Body"].data.materials[0]
    assert skin.name.startswith("Buddy_Skin"), skin.name
    img = gradient_image()
    interior = material_interior(img)
    bowel = material_flat("MAT_Abdomen_Bowel_v05", (0.90, 0.56, 0.52), 0.30, 0.35)
    artery = material_flat("MAT_Vessel_Artery_v05", (0.80, 0.16, 0.20), 0.32, 0.3)
    vein = material_flat("MAT_Vessel_Vein_v05", (0.52, 0.36, 0.66), 0.32, 0.3)
    maskm = material_flat("MAT_Abdomen_StencilMask_v05", (0.0, 1.0, 1.0), 1.0)
    coll = bpy.data.collections.new("OPERATION_ABDOMEN_v05")
    bpy.context.scene.collection.children.link(coll)

    BODY_BVH[0] = bvh
    bm, pts, nrm, skin_h, body_normals = build_opening(bvh, mw, mwi, layout["opening"])
    bm.verts.index_update()
    blend_n = {v.index: bn for v, bn in body_normals.items()}
    opening = finish(bm, "ABDOMEN_OPENING", [skin, interior], mw, coll)
    OPENING_OB[0] = opening
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
    for kid, side in (("ORGAN_KIDNEY_L", "L"), ("ORGAN_KIDNEY_R", "R")):
        for cname, cd in layout["organs"][kid]["cords"].items():
            a = mwi @ Vector(cd["table_start"]["table_blender"])
            b = mwi @ Vector(cd["table_end"]["table_blender"])
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
    for n, v in layout["great_vessels_abdominal_rest"].items():
        gaps = []
        for key in ("table_blender_head", "table_blender_pubic"):
            a, b = mwi @ Vector(v[key]), None
            for t in (0.25, 0.5, 0.75):
                q = (mwi @ Vector(v["table_blender_head"])).lerp(mwi @ Vector(v["table_blender_pubic"]), t)
                gaps.append(q.z - v["radius"] - floor_z(q.x, q.y))
        vessel_gaps[n] = [round(min(gaps) * 1000, 1), round(max(gaps) * 1000, 1)]
    mask_up = all(p.normal.z > 0 for p in mask.data.polygons)
    cav = cavity_volume(opening)
    res = {"marker": "INC_ABDOMEN", "origin_table_blender": [round(c, 4) for c in mw.translation],
           "mask_normals": "+Z (out of the belly): a Cull Back stencil-mask shader never writes from inside/behind" if mask_up else "MIXED",
           "organs_vs_cavity_verts_inside": organs_vs_cavity(layout, opening, mw),
           "objects": {ob.name: {"tris": tris(ob), "materials": [m.name for m in ob.data.materials]} for ob in coll.objects},
           "flap_height_above_skin_mm": [round(min(flap_heights) * 1000, 2), round(max(flap_heights) * 1000, 2)],
           "deepest_floor_marker_local_m": round(min(zs), 4),
           "min_body_left_behind_floor_m": round(min(g for g in back_gap if g >= 0), 4) if back_gap else None,
           "floor_points_without_body_behind": sum(1 for g in back_gap if g < 0),
           "gradient_png": OUT_PNG.name,
           "vessel_bottom_minus_floor_mm": vessel_gaps,
           "bowel_vs_kidneys": bowel_checks(layout, bowels, mw),
           "bowel_verts_inside_cavity_pct": round(100 * sum(1 for v in bowels.data.vertices if inside(cav, v.co))
                                                  / len(bowels.data.vertices), 1),
           "outline": {"half_width": layout["opening"]["half_width"], "half_length_top": layout["opening"]["half_length_top"],
                       "half_length_bottom": layout["opening"]["half_length_bottom"], "source": "organs_layout_v05.outline_xy (128 pts)"}}
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
