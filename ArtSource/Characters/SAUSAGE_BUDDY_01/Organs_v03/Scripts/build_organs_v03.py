"""ORGANS v03 for SAUSAGE_BUDDY_PATIENT_v03: heart, lungs, liver, kidneys, ribcage, great vessels, airway, diaphragm.

blender -b --factory-startup --python build_organs_v03.py [-- --dry]

Every organ is one object with a clean pivot (organ centre) at 1:1 world scale, scale (1,1,1), mesh authored in its
SOCKET frame (organs_v03_lib.py: +X patient left, +Y head / long axis, +Z anterior). In Organs_v03.blend each object sits
at its socket in the patient REST frame. Writes (refuses to overwrite) next to Scripts/:
  Organs_v03.blend                 everything placed in the body (plus a hidden reference patient body)
  Organs_InBody_v03.fbx            everything placed in the body (rest frame) - overlay / reference for Unity
  FBX/<ORGAN>_v03.fbx              each organ alone at the origin (identity), 1:1 - same mesh as in the body
  FBX/RIBCAGE_v03.fbx              SOCKET_THORAX hierarchy: ribcage halves with hinge pivots, ribs, sternum halves, spine
  FBX/CHEST_VESSELS_v03.fbx        SOCKET_THORAX frame: VESSELS_*, AIRWAY_TRACHEA, DIAPHRAGM
  organs_v03_build.json            per object: socket, pivot, local bounds, size, tris, materials; fit/validation results
--dry builds and validates without writing (for iteration).
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import heart_v03 as H          # noqa: E402
import organs_layout_v03 as LAY  # noqa: E402
import organs_v03_lib as L     # noqa: E402

REPO = Path(r"C:/Dev/Game")
OUT = HERE.parent
PATIENT_V02 = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v02/SAUSAGE_BUDDY_PATIENT_v02.blend"
LUNGS = REPO / "ArtSource/Props/LUNGS-ASTRA-001/LUNGS-ASTRA-001_recolour_v01.blend"
TABLE_REST = REPO / "ArtSource/Props/TABLE-ASTRA-001/v02/Patient_TableRest_v01.blend"
LIVER = REPO / "ArtSource/Props/LIVER-ASTRA-001/LIVER-ASTRA-001_recolour_v01.blend"
KIDNEY = REPO / "ArtSource/Props/KIDNEY-ASTRA-001/KIDNEY-ASTRA-001_recolour_v01.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DRY = "--dry" in ARGS
OUT_BLEND = OUT / "Organs_v03.blend"
OUT_FBX = OUT / "Organs_InBody_v03.fbx"
OUT_JSON = OUT / "organs_v03_build.json"
FBX_DIR = OUT / "FBX"

sc = bpy.context.scene
TRUNK = None          # BVH of the reference body's trunk island (set in main)
LIVER_BVH = None      # BVH of the placed liver (diaphragm follows its dome)
REPORT = {"version": "ORGANS_v03", "date": "2026-10-18", "objects": {}, "fit": {}, "validation": {}}


def log(*a):
    print("[ORGANS_v03]", *a, flush=True)


# ================================================================================================ materials
def make_materials():
    M = {}
    M["heart"] = L.material("MAT_Organ_Heart_v03", (0.74, 0.16, 0.19), 0.33, coat=0.3)
    M["fat"] = L.material("MAT_Organ_Fat_v03", (0.94, 0.80, 0.52), 0.40)
    M["artery"] = L.material("MAT_Vessel_Artery_v03", (0.80, 0.16, 0.20), 0.32, coat=0.3)
    M["vein"] = L.material("MAT_Vessel_Vein_v03", (0.52, 0.36, 0.66), 0.32, coat=0.3)
    M["lumen"] = L.material("MAT_Vessel_Lumen_v03", (0.30, 0.05, 0.08), 0.60)
    M["lung"] = L.material("MAT_Organ_Lung_v03", (0.90, 0.52, 0.56), 0.42, coat=0.2)
    M["lung_vein"] = L.material("MAT_Organ_LungVein_v03", (0.64, 0.22, 0.31), 0.45)
    M["liver"] = L.material("MAT_Organ_Liver_v03", (0.62, 0.22, 0.20), 0.32, coat=0.3)
    M["kidney"] = L.material("MAT_Organ_Kidney_v03", (0.72, 0.31, 0.39), 0.35, coat=0.3)
    M["kidney_tube"] = L.material("MAT_Organ_KidneyTube_v03", (0.88, 0.60, 0.58), 0.40)
    M["bone"] = L.material("MAT_Bone_v03", (0.93, 0.88, 0.76), 0.55)
    M["cartilage"] = L.material("MAT_Cartilage_v03", (0.80, 0.87, 0.90), 0.35, coat=0.2)
    M["marrow"] = L.material("MAT_Bone_Cut_v03", (0.86, 0.45, 0.42), 0.6)
    M["airway"] = L.material("MAT_Airway_v03", (0.93, 0.74, 0.74), 0.40)
    M["diaphragm"] = L.material("MAT_Diaphragm_v03", (0.60, 0.16, 0.18), 0.40, coat=0.2)
    return M


# ================================================================================================ helpers
def collection(name):
    c = bpy.data.collections.new(name)
    sc.collection.children.link(c)
    return c


def socket_mw(name):
    s = LAY.SOCKETS[name]
    m = L.socket_matrix(s["pos"], s["y"], s["z"])
    return m


def empty(name, mw, coll, size=0.03, kind="ARROWS", parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    coll.objects.link(e)
    if parent is not None:
        bpy.context.view_layer.update()
        e.parent = parent
        e.matrix_parent_inverse.identity()
        e.matrix_basis = parent.matrix_world.inverted() @ mw
    else:
        e.matrix_world = mw
    return e


def attach(ob, parent):
    bpy.context.view_layer.update()
    mw = ob.matrix_world.copy()
    ob.parent = parent
    ob.matrix_parent_inverse.identity()
    ob.matrix_basis = parent.matrix_world.inverted() @ mw


def append_objects(path, names=None):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if names is None or n in names]
    return [o for o in dst.objects if o is not None]


def mesh_from_source(ob, dg):
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    me.transform(ob.matrix_world)
    return me


def load_reference_body(coll):
    obs = append_objects(PATIENT_V02, ["Body", "Buddy_Rig_Mixamo65"])
    for o in obs:
        coll.objects.link(o)
    rig = next(o for o in obs if o.type == "ARMATURE")
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    body = next(o for o in obs if o.name.startswith("Body"))
    dg = bpy.context.evaluated_depsgraph_get()
    me = mesh_from_source(body, dg)
    ref = bpy.data.objects.new("REF_PatientBody_v02_rest", me)
    coll.objects.link(ref)
    for o in obs:
        bpy.data.objects.remove(o, do_unlink=True)
    ref.hide_render = True
    return ref


def load_table_rest_body(coll):
    """The TABLE_REST posed body (arms down, head on the pillow), mapped back into the REST frame through the Spine
    bone (the trunk is rigid with Spine in that pose), so organ sockets can be checked against the lying patient too."""
    obs = append_objects(TABLE_REST, ["Body", "Buddy_Rig_Mixamo65"])
    for o in obs:
        coll.objects.link(o)
    rig = next(o for o in obs if o.type == "ARMATURE")
    sc.frame_set(1)
    bpy.context.view_layer.update()
    pb = rig.pose.bones["mixamorig:Spine"]
    T = rig.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    body = next(o for o in obs if o.name.startswith("Body"))
    dg = bpy.context.evaluated_depsgraph_get()
    me = mesh_from_source(body, dg)
    me.transform(T.inverted())
    ref = bpy.data.objects.new("REF_PatientBody_TableRest_in_rest_frame", me)
    coll.objects.link(ref)
    for o in obs:
        bpy.data.objects.remove(o, do_unlink=True)
    for a in [a for a in bpy.data.actions if a.users == 0]:
        bpy.data.actions.remove(a)
    ref.hide_render = True
    ref.hide_viewport = True
    REPORT["table_rest_spine_matrix"] = [L.rnd(r, 5) for r in T]
    return ref, T


# ================================================================================================ organs
def build_heart(M, coll):
    bm = H.build(None)
    ob = L.new_object("ORGAN_HEART", bm, [M["heart"], M["fat"], M["artery"], M["vein"], M["lumen"]], coll, socket_mw("SOCKET_HEART"))
    return ob


def to_local(me, centre, scale):
    """Source model space (Z up, front -Y) -> organ local (+Y up, +Z front): centre, scale per model axis, Rx(-90)."""
    c = Vector(centre)
    for v in me.vertices:
        p = v.co - c
        p = Vector((p.x * scale[0], p.y * scale[1], p.z * scale[2]))
        v.co = Vector((p.x, p.z, -p.y))
    me.update()


def remap_materials(me, mapping, M):
    names = [m.name if m else "" for m in me.materials]
    new = []
    for n in names:
        key = next((v for k, v in mapping.items() if k in n), None)
        new.append(M[key] if key else None)
    for i, m in enumerate(new):           # slot assignment keeps the polygon material indices (clear() would reset them)
        me.materials[i] = m


def build_source_organs(M, coll):
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    # ---- liver
    src = append_objects(LIVER, ["LIVER-ASTRA-001 | clean organ body"])
    me = mesh_from_source(src[0], dg)
    for o in src:
        bpy.data.objects.remove(o, do_unlink=True)
    fit = LAY.SOURCE_FIT["ORGAN_LIVER"]
    to_local(me, fit["centre"], fit["scale"])
    remap_materials(me, {"liver": "liver"}, M)
    ob = bpy.data.objects.new("ORGAN_LIVER", me)
    coll.objects.link(ob)
    ob.matrix_world = socket_mw("SOCKET_LIVER")
    out["ORGAN_LIVER"] = ob
    # ---- kidneys (R_ mesh = patient-left kidney)
    src = append_objects(KIDNEY, ["R_Kidney and descending tube | integrated sculpt", "L_Kidney and descending tube | integrated sculpt"])
    for o in src:
        name = "ORGAN_KIDNEY_L" if o.name.startswith("R_Kidney") else "ORGAN_KIDNEY_R"
        me = mesh_from_source(o, dg)
        fit = LAY.SOURCE_FIT[name]
        to_local(me, fit["centre"], fit["scale"])
        remap_materials(me, {"deep_rose": "kidney", "warm_rose": "kidney_tube"}, M)
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        ob.matrix_world = socket_mw(LAY.ORGANS[name]["socket"])
        out[name] = ob
    for o in src:
        bpy.data.objects.remove(o, do_unlink=True)
    # ---- lungs (rest pose of the breathing rig; +X lobe = patient-left lung)
    src = append_objects(LUNGS)
    for o in src:
        if o.type in ("MESH", "ARMATURE"):
            sc.collection.objects.link(o)
    rig = next(o for o in src if o.type == "ARMATURE")
    rig.data.pose_position = "REST"
    if rig.animation_data:
        rig.animation_data.action = None
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    parts = {"ORGAN_LUNG_L": ["Lungs_Lobe_R", "Lungs_BranchFront_R", "Lungs_BranchRear_R"],
             "ORGAN_LUNG_R": ["Lungs_Lobe_L", "Lungs_BranchFront_L"]}
    for name, pnames in parts.items():
        bm = bmesh.new()
        lobe_bm = None
        for pn in pnames:
            so = next(o for o in src if o.name == pn)
            me = mesh_from_source(so, dg)
            remap_materials(me, {"lung_pink": "lung", "deep_rose": "lung_vein"}, M)
            if pn.startswith("Lungs_Lobe"):
                # one simple subdivision so the cardiac impression / diaphragm fit can bend the surface smoothly
                tb = bmesh.new()
                tb.from_mesh(me)
                bmesh.ops.subdivide_edges(tb, edges=tb.edges[:], cuts=1, use_grid_fill=True)
                bmesh.ops.triangulate(tb, faces=[f for f in tb.faces if len(f.verts) > 4])
                L.relax(tb, 1, 0.15)
                tb.to_mesh(me)
                tb.free()
            # material indices: lobe 0 = lung, 1 = lung_vein; decals = lung_vein
            if not pn.startswith("Lungs_Lobe"):
                for p in me.polygons:
                    p.material_index = 1
            bm.from_mesh(me)
            bpy.data.meshes.remove(me)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        co = [v.co for v in me.vertices]
        c = Vector(((min(v.x for v in co) + max(v.x for v in co)) / 2, (min(v.y for v in co) + max(v.y for v in co)) / 2,
                    (min(v.z for v in co) + max(v.z for v in co)) / 2))
        to_local(me, c, LAY.SOURCE_FIT[name]["scale"])
        me.materials.append(M["lung"])         # the joined mesh has no slots yet; indices 0 lobe / 1 vein decals
        me.materials.append(M["lung_vein"])
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        ob.matrix_world = socket_mw(LAY.ORGANS[name]["socket"])
        out[name] = ob
        REPORT["fit"][name + "_source_centre_model"] = L.rnd(c)
    for o in src:
        if o.name in bpy.data.objects:
            bpy.data.objects.remove(o, do_unlink=True)
    for p in out.values():
        for poly in p.data.polygons:
            poly.use_smooth = True
    return out


# ================================================================================================ fits
def heart_sdf_world(heart):
    inv = heart.matrix_world.inverted()

    def f(pw):
        pl = np.array([tuple(inv @ Vector(p)) for p in pw])
        return H.heart_sdf(pl)
    return f


def push_out_of_heart(ob, heart, gap=0.0065):
    """Cardiac impression: lung vertices inside the heart (+gap) move out along the SDF gradient."""
    hinv = heart.matrix_world.inverted()
    mw = ob.matrix_world
    moved = 0
    pts = np.array([tuple(hinv @ (mw @ v.co)) for v in ob.data.vertices])
    for _ in range(6):
        d = H.heart_sdf(pts) - gap
        idx = np.where(d < 0)[0]
        if not len(idx):
            break
        e = 1e-4
        g = np.zeros((len(idx), 3))
        for k in range(3):
            off = np.zeros(3)
            off[k] = e
            g[:, k] = (H.heart_sdf(pts[idx] + off) - H.heart_sdf(pts[idx] - off)) / (2 * e)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
        pts[idx] -= g * d[idx, None]
        moved = max(moved, len(idx))
    hm = heart.matrix_world
    inv = mw.inverted()
    for v, p in zip(ob.data.vertices, pts):
        v.co = inv @ (hm @ Vector(tuple(p)))
    ob.data.update()
    return moved


LIVER_TOP = None      # (xs, ys, heights) blurred liver-dome height map, set in main


def make_liver_top(liver_bvh):
    xs = np.arange(-0.16, 0.1601, 0.005)
    ys = np.arange(-0.10, 0.0901, 0.005)
    hgt = np.full((len(xs), len(ys)), -1.0)
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            hit = liver_bvh.ray_cast(Vector((x, y, 1.40)), Vector((0, 0, -1)), 1.0)
            if hit[0] is not None:
                hgt[i, j] = hit[0].z
    # dilate 1.5 cm (so thin lobe edges cannot slip between samples), then blur ~1 cm
    from itertools import product
    dil = hgt.copy()
    for di, dj in product(range(-3, 4), range(-3, 4)):
        dil = np.maximum(dil, np.roll(np.roll(hgt, di, 0), dj, 1))
    k = np.array([1, 4, 6, 4, 1], float)
    k /= k.sum()
    b = dil.copy()
    for _ in range(2):
        b = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 0, b)
        b = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, b)
    b = np.maximum(b, dil - 0.003)
    return xs, ys, b


def liver_top(x, y):
    if LIVER_TOP is None:
        return -1.0
    xs, ys, b = LIVER_TOP
    fi = (x - xs[0]) / (xs[1] - xs[0])
    fj = (y - ys[0]) / (ys[1] - ys[0])
    i0, j0 = int(math.floor(fi)), int(math.floor(fj))
    if i0 < 0 or j0 < 0 or i0 >= len(xs) - 1 or j0 >= len(ys) - 1:
        return -1.0
    u, v = fi - i0, fj - j0
    return (b[i0, j0] * (1 - u) * (1 - v) + b[i0 + 1, j0] * u * (1 - v) + b[i0, j0 + 1] * (1 - u) * v + b[i0 + 1, j0 + 1] * u * v)


def front_clamp(x, y):
    """The diaphragm stays above the abdominal opening's cavity (OperationAbdomen_v03), with 7 mm to spare."""
    return LAY.cavity_top(x, y) + 0.007


def diaphragm_z(x, y):
    return max(diaphragm_base(x, y), liver_top(x, y) + 0.008, front_clamp(x, y))


def diaphragm_base(x, y):
    """Diaphragm height (rest frame): right dome over the liver, left dome lower, central tendon under the heart,
    sloping down to the back; the front edge rises toward the xiphoid."""
    z = 1.004
    z += 0.044 * math.exp(-(((x + 0.062) / 0.066) ** 2 + ((y + 0.004) / 0.072) ** 2))     # right dome (over the liver)
    z += 0.026 * math.exp(-(((x - 0.068) / 0.055) ** 2 + ((y + 0.004) / 0.065) ** 2))     # left dome
    z += 0.024 * math.exp(-((x / 0.040) ** 2 + ((y + 0.030) / 0.045) ** 2))               # central tendon under the heart
    z -= 0.022 * max(0.0, (y - 0.02) / 0.08)                                                # lower at the back
    return z


def push_above_diaphragm(ob, gap=0.004):
    mw = ob.matrix_world
    inv = mw.inverted()
    n = 0
    for v in ob.data.vertices:
        p = mw @ v.co
        zmin = diaphragm_z(p.x, p.y) + gap
        if p.z < zmin:
            p.z = zmin
            v.co = inv @ p
            n += 1
    ob.data.update()
    return n


def relax_moved(ob, iters=2):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    L.relax(bm, iters, 0.2)
    bm.to_mesh(ob.data)
    bm.free()


# ================================================================================================ ribcage
def skin_dist(c, d):
    hit = TRUNK.ray_cast(c, d, 1.2)
    return hit[3] if hit[0] is not None else 1.0


def conform(path, inset, keep_first=0):
    """Keep a centreline at least `inset` under the trunk skin (radial from the cage axis), then smooth the clamps."""
    def clamp(pts):
        out = []
        for k, p in enumerate(pts):
            c = Vector((0.0, -0.003, p.z))
            v = Vector((p.x - c.x, p.y - c.y, 0.0))
            if k < keep_first or v.length < 1e-6:
                out.append(p.copy())
                continue
            d = v.normalized()
            lim = skin_dist(c, d) - inset
            out.append(c + d * min(v.length, lim) + Vector((0, 0, 0)) if v.length > lim else p.copy())
            out[-1].z = p.z
        return out
    pts = clamp(path)
    for _ in range(3):
        pts = [pts[0]] + [(pts[k - 1] + pts[k] * 2 + pts[k + 1]) / 4 for k in range(1, len(pts) - 1)] + [pts[-1]]
        pts = clamp(pts)
    return pts


def skin_front_y(x, z):
    hit = TRUNK.ray_cast(Vector((x, 0.0, z)), Vector((0, -1, 0)), 0.5)
    return hit[0].y
def rib_centreline(i, side):
    """Rest-frame centreline of rib i (bone part, head -> costochondral junction) and of its cartilage."""
    r = LAY.RIBS[i]
    s, zp = r["s"], r["zp"]
    jx, jy, jz = r["junction"]
    # posterior and lateral control points (left side), scaled toward the trunk axis for the small upper ribs
    ctrl = [(0.020, 0.048, zp), (0.040, 0.066, zp + 0.002), (0.072, 0.082, zp - 0.002), (0.118, 0.068, zp - 0.008),
            (0.146, 0.018, zp - 0.018), (0.140, -0.040, zp - 0.030)]
    pts = []
    for k, (x, y, z) in enumerate(ctrl):
        f = s if k >= 2 else 1.0
        pts.append(Vector((x * f, y * (f if k >= 3 else 1.0), z)))
    j = Vector((jx, jy, jz))
    # anterior arc: from the last lateral point sweep smoothly forward and medially into the junction
    p5 = pts[-1]
    p6 = Vector((p5.x * 0.55 + j.x * 0.45 + 0.010 * s, p5.y * 0.35 + j.y * 0.65, p5.z * 0.45 + j.z * 0.55))
    pts += [p6, j]
    if i == 1:
        pts = [pts[0], pts[1], pts[2], Vector((0.088, 0.040, zp - 0.008)), Vector((0.096, -0.020, zp - 0.016)), j]
    bone = L.resample(L.catmull(pts, 8), 0.008)
    for p in bone:
        p.x *= side
    return bone


def cartilage_path(i, side, carts):
    r = LAY.RIBS[i]
    jx, jy, jz = r["junction"]
    j = Vector((jx, jy, jz))
    to = r["to"]
    if to[0] == "sternum":
        ex = LAY.STERNUM["half_width_body"] * 0.8 if i > 1 else LAY.STERNUM["half_width_top"] * 0.85
        end = Vector((ex, skin_front_y(ex, to[1]) + 0.0068 + LAY.STERNUM["thick"] / 2, to[1]))
        mid = Vector(((j.x + end.x) / 2, min(j.y, end.y) - 0.003, j.z + (end.z - j.z) * (0.35 if i >= 5 else 0.5)))
        if i >= 6:
            mid = Vector((j.x * 0.55 + end.x * 0.45, (j.y + end.y) / 2 - 0.004, j.z + (end.z - j.z) * 0.30))
        pts = [j, mid, end]
    else:
        k, t = to[1], to[2]
        target_path = carts[k]
        idx = int(t * (len(target_path) - 1))
        end = Vector(target_path[idx])
        end = Vector((abs(end.x), end.y, end.z))
        mid = Vector((j.x * 0.62 + end.x * 0.38, (j.y + end.y) / 2 - 0.006, j.z + (end.z - j.z) * 0.30 - 0.004))
        pts = [j, mid, end]
    path = L.resample(L.catmull(pts, 8), 0.007)
    for p in path:
        p.x *= side
    return path


def rib_sweep(bm, path, h, th, mat, cap0="round", cap1="round", h_fn=None):
    """Flat rib cross-section: wide (h) along the cage surface, thin (th) along the outward normal."""
    n = len(path)
    rings = []
    segs = 8
    for i, p in enumerate(path):
        t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
        out = Vector((p.x, p.y + 0.003, 0.0)).normalized()
        w = t.cross(out).normalized()
        nn = w.cross(t).normalized()
        f = h_fn(i, n) if h_fn else 1.0
        if cap0 == "round" and i == 0:
            f *= 0.6
        if cap1 == "round" and i == n - 1:
            f *= 0.7
        rings.append([bm.verts.new(p + w * math.cos(2 * math.pi * j / segs) * h * 0.5 * f + nn * math.sin(2 * math.pi * j / segs) * th * 0.5 * f)
                      for j in range(segs)])
    for i in range(n - 1):
        for j in range(segs):
            j2 = (j + 1) % segs
            bm.faces.new((rings[i][j], rings[i][j2], rings[i + 1][j2], rings[i + 1][j])).material_index = mat
    for ring, end in ((rings[0], False), (rings[-1], True)):
        c = bm.verts.new(sum((v.co for v in ring), Vector()) / segs)
        for j in range(segs):
            j2 = (j + 1) % segs
            bm.faces.new((ring[j], ring[j2], c) if end else (ring[j2], ring[j], c)).material_index = mat


def sternum_half(side, M):
    """One half of the sternum (split on the midline): front/back plates, outer edge and the midline cut face."""
    S = LAY.STERNUM
    rows = 18
    cols = 4
    zt, zx = S["top"], S["xiphoid"]

    def hw(z):
        t = (zt - z) / (zt - zx)            # 0 top .. 1 xiphoid tip
        if t < 0.28:                          # manubrium: wide, narrowing at the manubriosternal joint
            return S["half_width_top"] * (1 - 0.35 * (t / 0.28) ** 2) * (0.75 + 0.25 * math.sin(min(1, t / 0.08) * math.pi / 2))
        if t < 0.86:
            return S["half_width_body"] * (1.0 + 0.12 * math.sin((t - 0.28) / 0.58 * math.pi))
        return S["half_width_body"] * 0.55 * (1 - (t - 0.86) / 0.14) + 0.002

    bm = bmesh.new()
    front, back = [], []
    for r in range(rows + 1):
        z = zt - (zt - zx) * r / rows
        w = hw(z)
        fr, bk = [], []
        for c in range(cols + 1):
            x = side * w * c / cols
            bulge = 0.0012 * (1 - (c / cols) ** 2)
            yf = skin_front_y(x, z) + 0.0068 - bulge
            yb = yf + S["thick"] * (1 - 0.25 * (c / cols) ** 2)
            fr.append(bm.verts.new((x, yf, z)))
            bk.append(bm.verts.new((x, yb, z)))
        front.append(fr)
        back.append(bk)
    flip = side < 0

    def face(vs, mat):
        f = bm.faces.new(list(reversed(vs)) if flip else vs)
        f.material_index = mat

    for r in range(rows):
        for c in range(cols):
            face([front[r][c], front[r + 1][c], front[r + 1][c + 1], front[r][c + 1]], 0)
            face([back[r][c], back[r][c + 1], back[r + 1][c + 1], back[r + 1][c]], 0)
        face([front[r][cols], front[r + 1][cols], back[r + 1][cols], back[r][cols]], 0)      # outer edge
        face([front[r][0], back[r][0], back[r + 1][0], front[r + 1][0]], 1)                  # midline cut face
    for c in range(cols):
        face([front[0][c], front[0][c + 1], back[0][c + 1], back[0][c]], 0)                   # top (jugular notch)
        face([front[rows][c], back[rows][c], back[rows][c + 1], front[rows][c + 1]], 0)       # xiphoid tip
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def build_ribcage(M, coll, thorax):
    tmw = thorax.matrix_world
    tinv = tmw.inverted()
    root = empty("RIBCAGE", tmw, coll, 0.05, parent=thorax)
    objs = {"RIBCAGE": root}
    hinge = Vector(LAY.RIBCAGE_HINGE["pos_left"])
    centrelines = {}
    for side, tag in ((1, "L"), (-1, "R")):
        hp = Vector((hinge.x * side, hinge.y, hinge.z))
        half = empty(f"RIBCAGE_HALF_{tag}", Matrix.Translation(hp) @ tmw.to_3x3().to_4x4(), coll, 0.04, "SINGLE_ARROW", parent=root)
        objs[half.name] = half
        carts = {}
        for i in sorted(LAY.RIBS):
            bone = conform(rib_centreline(i, side), 0.0125, keep_first=3)
            cart = cartilage_path(i, 1, carts)
            cart = conform([Vector((p.x * side, p.y, p.z)) for p in cart], 0.0110)
            carts[i] = [Vector((abs(p.x), p.y, p.z)) for p in cart]
            # the cartilage starts where the (conformed) bone ends
            off = bone[-1] - cart[0]
            n = len(cart)
            cart = [p + off * (1 - k / max(1, n - 1)) ** 2 for k, p in enumerate(cart)]
            centrelines[(tag, i)] = (bone, cart)
            pivot = bone[0]
            bm = bmesh.new()
            h_bone = 0.0095 if i > 1 else 0.0085
            rib_sweep(bm, bone, h_bone, 0.0052, 0, cap0="round", cap1="flat",
                      h_fn=lambda k, n: 0.75 + 0.25 * min(1.0, k / 6.0) if k < 6 else 1.0)
            rib_sweep(bm, [bone[-1] + (bone[-1] - bone[-2]).normalized() * -0.002] + cart[1:], 0.0080, 0.0052, 1, cap0="flat",
                      cap1="flat" if LAY.RIBS[i]["to"][0] == "sternum" else "round")
            # into rib-local space (origin = rib head, axes = thorax socket axes)
            mw = Matrix.Translation(pivot) @ tmw.to_3x3().to_4x4()
            inv = mw.inverted()
            for v in bm.verts:
                v.co = inv @ v.co
            ob = L.new_object(f"RIB_{tag}_{i:02d}", bm, [M["bone"], M["cartilage"]], coll, mw)
            attach(ob, half)
            objs[ob.name] = ob
        # sternum half
        bm = sternum_half(side, M)
        top = Vector((0.0, skin_front_y(0.0, LAY.STERNUM["top"]) + 0.0068 + LAY.STERNUM["thick"] / 2, LAY.STERNUM["top"]))
        mw = Matrix.Translation(top) @ tmw.to_3x3().to_4x4()
        inv = mw.inverted()
        for v in bm.verts:
            v.co = inv @ v.co
        ob = L.new_object(f"STERNUM_{tag}", bm, [M["bone"], M["marrow"]], coll, mw, smooth=True)
        attach(ob, half)
        objs[ob.name] = ob
    # thoracic spine (static)
    bm = bmesh.new()
    Sp = LAY.SPINE
    for k in range(Sp["levels"]):
        z = Sp["z_bottom"] + (Sp["z_top"] - Sp["z_bottom"]) * (k + 0.5) / Sp["levels"]
        h = (Sp["z_top"] - Sp["z_bottom"]) / Sp["levels"]
        rad = 0.0128 + 0.0025 * (1 - k / Sp["levels"])
        body = L.resample([Vector((0, Sp["y"], z - h * 0.36)), Vector((0, Sp["y"], z + h * 0.36))], h * 0.24)
        L.tube(bm, body, rad, segs=10, cap0="flat", cap1="flat", mat=0)
        disc = L.resample([Vector((0, Sp["y"], z + h * 0.36)), Vector((0, Sp["y"], z + h * 0.64))], h * 0.14)
        L.tube(bm, disc, rad * 0.93, segs=10, cap0=None, cap1=None, mat=1)
        sp = L.resample(L.catmull([Vector((0, Sp["y"] + rad * 0.8, z)), Vector((0, Sp["y"] + 0.026, z - 0.004)),
                                   Vector((0, Sp["y"] + 0.040, z - 0.012))], 4), 0.004)
        L.tube(bm, sp, 0.0042, segs=6, flat=0.6, mat=0)
        for sd in (1, -1):
            tp = L.resample([Vector((sd * rad * 0.6, Sp["y"] + rad * 0.7, z + 0.002)), Vector((sd * 0.030, Sp["y"] + 0.016, z + 0.001))], 0.004)
            L.tube(bm, tp, 0.0036, segs=6, mat=0)
    mw = tmw.copy()
    inv = mw.inverted()
    for v in bm.verts:
        v.co = inv @ v.co
    ob = L.new_object("SPINE_THORACIC", bm, [M["bone"], M["cartilage"]], coll, mw)
    attach(ob, root)
    objs[ob.name] = ob
    return objs, centrelines


# ================================================================================================ vessels, airway, diaphragm
def lung_hilum(lung, side, dz, dy):
    """Point on the medial lung surface at (socket z + dz, socket y + dy), found by a ray from the midline."""
    bvh, _, _ = L.bvh_of([lung])
    c = lung.matrix_world.translation
    o = Vector((0.0, c.y + dy, c.z + dz))
    d = Vector((side, 0, 0))
    hit = bvh.ray_cast(o, d, 0.3)
    assert hit[0] is not None, (lung.name, dz, dy)
    return hit[0]


def heart_stub(heart, name):
    p, d, r, kind = H.stub_end(name)
    mw = heart.matrix_world
    return mw @ p, (mw.to_3x3() @ d).normalized(), r, kind


def build_vessels(M, coll, thorax, heart, lungs):
    tmw = thorax.matrix_world
    tinv = tmw.inverted()
    out = {}
    conn = {}

    def obj(name, parts, mats):
        bm = bmesh.new()
        for path, r, mat, caps, kw in parts:
            L.tube(bm, [tinv @ p for p in path], r, segs=kw.get("segs", 12), cap0=caps[0], cap1=caps[1], mat=mat,
                   radius_fn=kw.get("rf"))
        ob = L.new_object(name, bm, mats, coll, tmw.copy())
        attach(ob, thorax)
        out[name] = ob
        return ob

    def from_stub(name, inset=0.004):
        p, d, r, kind = heart_stub(heart, name)
        return p - d * inset, p, d, r

    # ---- aorta: root stub -> arch -> descending beside the spine -> joins the abdominal aorta behind the diaphragm
    s0, s1, d, r = from_stub("AORTA")
    ga = LAY.GREAT_VESSELS["aorta"]
    z0 = s1.z
    arch = [s0, s1 + d * 0.008, Vector((s1.x + 0.002, -0.036, z0 + 0.015)), Vector((s1.x + 0.007, -0.022, z0 + 0.025)),
            Vector((0.021, 0.000, z0 + 0.022)), Vector((0.026, 0.019, z0 + 0.006)), Vector((0.025, 0.025, 1.120)),
            Vector((0.021, 0.020, 1.075)),
            Vector((ga["x"], ga["y"] + 0.006, 1.040)), Vector((ga["x"], ga["y"], ga["z"][0] - 0.012))]
    path = L.resample(L.catmull(arch, 8), 0.006)
    taper = lambda i, n: 1.0 - 0.13 * i / max(1, n - 1)        # 9.8 mm at the root -> 8.5 mm at the abdominal join
    branches = []
    # three arch branches (brachiocephalic, left carotid, left subclavian) up into the neck, ending inside the body
    arch_pts = [p for p in path if p.z > z0 + 0.012]
    for k, dx in enumerate((-0.012, 0.004, 0.018)):
        a = min(arch_pts, key=lambda p: abs(p.x - (dx * 0.6 + 0.006)))
        b = Vector((dx * 1.6 - 0.002, a.y + 0.004, z0 + 0.054 - 0.002 * k))
        branches.append((L.resample(L.catmull([a - Vector((0, 0, 0.004)), a.lerp(b, 0.5) + Vector((dx * 0.3, 0, 0)), b], 6), 0.004),
                         0.0042 if k else 0.0050, 0, ("flat", "round"), {"segs": 8}))
    obj("VESSELS_AORTA", [(path, r, 0, ("flat", "round"), {"rf": taper})] + branches, [M["artery"]])
    conn["VESSELS_AORTA"] = {"heart_stub": "AORTA", "start_rest": L.rnd(s1), "abdominal_join_rest": L.rnd(path[-1]),
                             "radius_m": round(r, 4), "snip_point_rest": L.rnd(path[min(len(path) - 1, 5)])}

    # ---- vena cava: SVC up from the right atrium into the neck; IVC down through the diaphragm to the abdominal IVC
    s0, s1, d, r = from_stub("SVC")
    svc = L.resample(L.catmull([s0, s1 + d * 0.012, Vector((s1.x - 0.002, s1.y + 0.006, 1.195)), Vector((s1.x - 0.004, s1.y + 0.010, 1.216))], 8), 0.006)
    i0, i1, di, ri = from_stub("IVC")
    gv = LAY.GREAT_VESSELS["vena_cava"]
    ivc = L.resample(L.catmull([i0, i1 + di * 0.006, Vector((gv["x"], gv["y"] - 0.010, 1.055)),
                                Vector((gv["x"], gv["y"], gv["z"][0] - 0.012))], 8), 0.004)
    obj("VESSELS_VENA_CAVA", [(svc, r, 0, ("flat", "round"), {}), (ivc, ri, 0, ("flat", "round"),
                                                                          {"rf": lambda i, n: 1.0 + 0.11 * i / max(1, n - 1)})], [M["vein"]])
    conn["VESSELS_VENA_CAVA"] = {"heart_stubs": ["SVC", "IVC"], "svc_start_rest": L.rnd(s1), "ivc_start_rest": L.rnd(i1),
                                 "abdominal_join_rest": L.rnd(ivc[-1]), "snip_point_svc_rest": L.rnd(svc[4]),
                                 "snip_point_ivc_rest": L.rnd(ivc[min(4, len(ivc) - 1)])}

    # ---- pulmonary arteries: trunk stub -> bifurcation under the arch -> each lung hilum (into the lung by 8 mm)
    s0, s1, d, r = from_stub("PULMONARY_TRUNK")
    bif = Vector((s1.x - 0.006, -0.014, s1.z + 0.010))
    hl = lung_hilum(lungs["ORGAN_LUNG_L"], 1, 0.016, -0.004)
    hr = lung_hilum(lungs["ORGAN_LUNG_R"], -1, 0.014, -0.002)
    trunk = L.resample(L.catmull([s0, s1 + d * 0.008, bif], 8), 0.006)
    left = L.resample(L.catmull([bif, Vector((0.032, -0.004, bif.z - 0.004)), hl, hl + Vector((0.010, 0.002, -0.002))], 8), 0.006)
    right = L.resample(L.catmull([bif, Vector((-0.010, 0.002, bif.z - 0.006)), Vector((-0.030, 0.004, hr.z + 0.004)), hr,
                                  hr + Vector((-0.010, 0.002, -0.002))], 8), 0.004)
    obj("VESSELS_PULMONARY_ARTERY", [(trunk, r, 0, ("flat", "round"), {}), (left, 0.0070, 0, ("round", "round"), {}),
                                     (right, 0.0070, 0, ("round", "round"), {})], [M["vein"]])
    conn["VESSELS_PULMONARY_ARTERY"] = {"heart_stub": "PULMONARY_TRUNK", "start_rest": L.rnd(s1), "lung_L_hilum_rest": L.rnd(hl),
                                        "lung_R_hilum_rest": L.rnd(hr)}

    # ---- pulmonary veins: four short veins, left atrium stubs -> straight on into the lung (ending 9 mm inside it)
    parts = []
    pv = {}
    for name, lung in (("PV_L_SUP", "ORGAN_LUNG_L"), ("PV_L_INF", "ORGAN_LUNG_L"), ("PV_R_SUP", "ORGAN_LUNG_R"), ("PV_R_INF", "ORGAN_LUNG_R")):
        s0, s1, d, r = from_stub(name)
        lb = L.bvh_of([lungs[lung]])[0]
        hit = lb.ray_cast(s1, d, 0.2)
        if hit[0] is None or hit[1].dot(d) > 0 or (hit[0] - s1).length < 0.004:
            h = s1 + d * 0.004                  # the stub end is already inside the lung (or touching it)
        else:
            h = hit[0]                          # the medial lung surface
        path = L.resample([s0, h + d * 0.009], 0.006)
        parts.append((path, r, 0, ("flat", "round"), {"segs": 8}))
        pv[name] = {"start_rest": L.rnd(s1), "lung_surface_rest": L.rnd(h), "end_inside_lung_rest": L.rnd(path[-1])}
    obj("VESSELS_PULMONARY_VEINS", parts, [M["artery"]])
    conn["VESSELS_PULMONARY_VEINS"] = pv

    # ---- airway: trachea (ringed) + main bronchi into the lung hila
    bl = lung_hilum(lungs["ORGAN_LUNG_L"], 1, 0.006, 0.012)
    br = lung_hilum(lungs["ORGAN_LUNG_R"], -1, 0.006, 0.012)
    car = Vector((-0.006, 0.004, 1.150))
    trachea = L.resample([Vector((-0.006, -0.004, 1.222)), Vector((-0.006, -0.001, 1.190)), car], 0.004)
    ring = lambda i, n: 1.0 + 0.08 * (1 if (i % 3) == 0 else 0)
    bL = L.resample(L.catmull([car, Vector((0.020, 0.010, 1.140)), bl, bl + Vector((0.010, 0, -0.002))], 8), 0.004)
    bR = L.resample(L.catmull([car, Vector((-0.026, 0.010, 1.140)), br, br + Vector((-0.010, 0, -0.002))], 8), 0.004)
    obj("AIRWAY_TRACHEA", [(trachea, 0.0072, 0, ("round", "round"), {"rf": ring}), (bL, 0.0052, 0, ("round", "round"), {"rf": ring}),
                           (bR, 0.0056, 0, ("round", "round"), {"rf": ring})], [M["airway"]])
    conn["AIRWAY_TRACHEA"] = {"carina_rest": L.rnd(car), "bronchus_L_hilum_rest": L.rnd(bl), "bronchus_R_hilum_rest": L.rnd(br)}
    REPORT["connections"] = conn
    return out


def build_diaphragm(M, coll, thorax, ref_bvh):
    """Thin domed sheet under the lungs and heart, spanning the trunk inside the ribs (muscle rim, pale central tendon)."""
    tmw = thorax.matrix_world
    tinv = tmw.inverted()
    bm = bmesh.new()
    R, A = 14, 48
    grid = []
    for i in range(R + 1):
        row = []
        for a in range(A):
            th = 2 * math.pi * a / A
            u = i / R
            # outline: the cage interior at diaphragm level (half width 0.138, front -0.078, back +0.070)
            ex, ey = 0.138 * math.cos(th), (0.070 if math.sin(th) > 0 else 0.078) * math.sin(th)
            x, y = ex * u, ey * u - 0.004 * (1 - u)
            z = diaphragm_base(x, y)
            if u > 0.70 and math.sin(th) > -0.3:   # the rim curves down along the back and side walls
                z -= 0.026 * ((u - 0.70) / 0.30) ** 2 * min(1.0, (math.sin(th) + 0.3) / 0.6)
            z = max(z, liver_top(x, y) + 0.008, front_clamp(x, y))
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    c = bm.verts.new((0, -0.004, diaphragm_z(0, -0.004)))
    for a in range(A):
        f = bm.faces.new((c, grid[0][a], grid[0][(a + 1) % A]))
    for i in range(R):
        for a in range(A):
            a2 = (a + 1) % A
            bm.faces.new((grid[i][a], grid[i + 1][a], grid[i + 1][a2], grid[i][a2]))
    for f in bm.faces:
        f.material_index = 0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # normals up (toward the chest); thicken a little so it is visible from both sides
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
    bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.002)
    for v in bm.verts:
        v.co = tinv @ v.co
    ob = L.new_object("DIAPHRAGM", bm, [M["diaphragm"]], coll, tmw.copy())
    attach(ob, thorax)
    return ob


# ================================================================================================ validation
def body_islands(ref, with_size=False):
    """BVH per big closed island of the reference body (trunk, head): inside = inside any of them."""
    bm = bmesh.new()
    bm.from_mesh(ref.data)
    bm.verts.ensure_lookup_table()
    seen, out = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], set()
        seen.add(v.index)
        while stack:
            x = stack.pop()
            comp.add(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        if len(comp) < 400:
            continue
        faces = {f for x in comp for f in x.link_faces}
        idx = {x.index: k for k, x in enumerate(comp)}
        vs = [ref.matrix_world @ x.co for x in comp]
        ps = [[idx[x.index] for x in f.verts] for f in faces]
        out.append((BVHTree.FromPolygons(vs, ps), len(comp)) if with_size else BVHTree.FromPolygons(vs, ps))
    bm.free()
    return out


def surface_points(ob, step=1):
    mw = ob.matrix_world
    return [mw @ v.co for v in ob.data.vertices[::step]]


def validate(objs, ref, groups, ref_pose=None):
    bpy.context.view_layer.update()
    res = {}
    if ref_pose is not None:
        isl2 = body_islands(ref_pose)
        pose = {}
        for name, ob in objs.items():
            if ob.type != "MESH":
                continue
            out = [p for p in surface_points(ob) if not any(L.inside_count(i, [p]) == 1 for i in isl2)]
            pose[name] = len(out)
        res["table_rest_verts_outside_body"] = pose
    dg = bpy.context.evaluated_depsgraph_get()
    islands = body_islands(ref)
    clear = {}
    for name, ob in objs.items():
        if ob.type != "MESH":
            continue
        pts = surface_points(ob)
        outside, dmin, worst, closest = 0, 9.0, None, None
        for p in pts:
            ins = [isl for isl in islands if L.inside_count(isl, [p]) == 1]
            if not ins:
                outside += 1
                worst = p
                continue
            d = max(isl.find_nearest(p)[3] for isl in ins)
            if d < dmin:
                dmin, closest = d, p
        clear[name] = {"verts_outside_body": outside, "min_skin_distance_mm": round(dmin * 1000, 1),
                       "closest_vert_rest": L.rnd(closest) if closest is not None else None}
        if worst is not None:
            clear[name]["an_outside_vert_rest"] = L.rnd(worst)
    res["inside_body"] = clear
    # 2. surface intersections between groups (BVH triangle overlap), by object pair
    bvhs = {n: L.bvh_of([o])[0] for n, o in objs.items() if o.type == "MESH"}
    hits = {}
    names = [n for n in bvhs]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if groups.get(a) == groups.get(b) and groups.get(a) is not None:
                continue
            ov = bvhs[a].overlap(bvhs[b])
            if ov:
                hits[f"{a} x {b}"] = len(ov)
    res["intersections_tri_pairs"] = hits
    return res


# ================================================================================================ main
def main():
    if not DRY:
        for p in (OUT_BLEND, OUT_FBX, OUT_JSON):
            assert not p.exists(), f"refusing to overwrite {p}"
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    M = make_materials()
    ref_coll = collection("REFERENCE_PATIENT_v02_REST")
    ref = load_reference_body(ref_coll)
    ref_pose, T_TABLE = load_table_rest_body(ref_coll)
    coll = collection("ORGANS_v03")
    root = empty("ORGANS_v03_ROOT", Matrix.Identity(4), coll, 0.1, "PLAIN_AXES")
    sockets = {n: empty(n, socket_mw(n), coll, 0.025, "ARROWS", parent=root) for n in LAY.SOCKETS}

    global TRUNK, LIVER_BVH, LIVER_TOP
    isl = body_islands(ref, with_size=True)
    TRUNK = max(isl, key=lambda t: t[1])[0]
    heart = build_heart(M, coll)
    organs = {"ORGAN_HEART": heart}
    organs.update(build_source_organs(M, coll))
    bpy.context.view_layer.update()
    LIVER_BVH = L.bvh_of([organs["ORGAN_LIVER"]])[0]
    LIVER_TOP = make_liver_top(LIVER_BVH)

    # fits: lungs make room for the heart and sit on the diaphragm
    fit = {}
    for n in ("ORGAN_LUNG_L", "ORGAN_LUNG_R"):
        fit[n] = {"verts_moved_by_heart": push_out_of_heart(organs[n], heart),
                  "verts_raised_to_diaphragm": push_above_diaphragm(organs[n])}
        relax_moved(organs[n], 1)
    REPORT["fit"].update(fit)

    thorax = sockets["SOCKET_THORAX"]
    rib_objs, centrelines = build_ribcage(M, coll, thorax)
    vessels = build_vessels(M, coll, thorax, heart, organs)
    dia = build_diaphragm(M, coll, thorax, None)
    for name, ob in organs.items():
        attach(ob, sockets[LAY.ORGANS[name]["socket"]])

    allobj = dict(organs)
    allobj.update({k: v for k, v in rib_objs.items() if v.type == "MESH"})
    allobj.update(vessels)
    allobj["DIAPHRAGM"] = dia
    groups = {n: "ribcage" for n in rib_objs}
    groups.update({n: "vessels" for n in vessels})
    REPORT["validation"] = validate(allobj, ref, groups, ref_pose)
    log("TABLE_REST outside:", {k: v for k, v in REPORT["validation"]["table_rest_verts_outside_body"].items() if v})
    for n, v in REPORT["validation"]["inside_body"].items():
        log("INSIDE", n, v)
    for n, v in REPORT["validation"]["intersections_tri_pairs"].items():
        log("HIT", n, v)
    log(json.dumps(REPORT["fit"]))
    for n, o in allobj.items():
        mn, mx = L.local_bounds(o)
        log(n, "tris", L.tris(o), "size_cm", L.rnd((mx - mn) * 100, 1))
    describe(allobj, sockets, rib_objs)
    if DRY:
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(ARGS[ARGS.index("--dry") + 1]) if len(ARGS) > ARGS.index("--dry") + 1 else
                                                  Path(bpy.app.tempdir) / "organs_dry.blend"))
        Path(ARGS[ARGS.index("--dry") + 1]).with_suffix(".json").write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
        return
    export(organs, sockets, rib_objs, vessels, dia, ref_pose)


# ================================================================================================ description / export
def mat_info(m):
    return {"name": m.name, "base_color_srgb": list(m.get("unity_base_color_srgb", [])), "smoothness": m.get("unity_smoothness")}


def describe(allobj, sockets, rib_objs):
    bpy.context.view_layer.update()
    REPORT["sockets"] = {}
    for n, e in sockets.items():
        mw = e.matrix_world
        REPORT["sockets"][n] = {"rest_position": L.rnd(mw.translation, 5), "rest_rotation_wxyz": L.rnd(mw.to_quaternion(), 5),
                                "rest_x_axis": L.rnd(mw.col[0][:3], 4), "rest_y_axis": L.rnd(mw.col[1][:3], 4),
                                "rest_z_axis": L.rnd(mw.col[2][:3], 4)}
    objs = {}
    extra = {k: v for k, v in rib_objs.items() if v.type == "EMPTY"}
    for name, ob in list(allobj.items()) + list(extra.items()):
        sock = ob
        while sock.parent is not None and not sock.parent.name.startswith("SOCKET_"):
            sock = sock.parent
        socket = sock.parent
        rel = socket.matrix_world.inverted() @ ob.matrix_world
        d = {"socket": socket.name, "parent": ob.parent.name if ob.parent else None,
             "socket_local_blender": {"position": L.rnd(rel.translation, 5), "rotation_wxyz": L.rnd(rel.to_quaternion(), 5)},
             "socket_local_unity": {"position": L.unity_local_pos(rel.translation), "rotation_xyzw": L.unity_local_quat(rel.to_quaternion())},
             "rest_position": L.rnd(ob.matrix_world.translation, 5), "scale": L.rnd(ob.matrix_world.to_scale(), 4)}
        if ob.type == "MESH":
            mn, mx = L.local_bounds(ob)
            d.update({"tris": L.tris(ob), "local_bounds_min": L.rnd(mn, 4), "local_bounds_max": L.rnd(mx, 4),
                      "size_m_xyz": L.rnd(mx - mn, 4), "largest_dimension_m": round(max(mx - mn), 4),
                      "materials": [mat_info(m) for m in ob.data.materials]})
        objs[name] = d
    REPORT["objects"] = objs


def export(organs, sockets, rib_objs, vessels, dia, ref_pose):
    FBX_DIR.mkdir(exist_ok=True)
    for p in [OUT_FBX] + [FBX_DIR / f"{n}_v03.fbx" for n in organs] + [FBX_DIR / "RIBCAGE_v03.fbx", FBX_DIR / "CHEST_VESSELS_v03.fbx"]:
        assert not p.exists(), f"refusing to overwrite {p}"
    bpy.data.objects.remove(ref_pose, do_unlink=True)
    kw = dict(use_selection=True, object_types={"MESH", "EMPTY"}, axis_forward="-Z", axis_up="Y", apply_unit_scale=True,
              apply_scale_options="FBX_SCALE_UNITS", use_mesh_modifiers=False, bake_anim=False, add_leaf_bones=False,
              use_custom_props=True, mesh_smooth_type="FACE")

    def select(objs):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]

    root = bpy.data.objects["ORGANS_v03_ROOT"]
    everything = [root] + [o for o in root.children_recursive]
    select(everything)
    bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), **kw)
    # each organ alone at the origin (identity), the same mesh as in the body
    for n, ob in organs.items():
        par, mb = ob.parent, ob.matrix_basis.copy()
        ob.parent = None
        ob.matrix_world = Matrix.Identity(4)
        select([ob])
        bpy.ops.export_scene.fbx(filepath=str(FBX_DIR / f"{n}_v03.fbx"), **kw)
        ob.parent = par
        ob.matrix_parent_inverse.identity()
        ob.matrix_basis = mb
    # chest hierarchies with SOCKET_THORAX at the origin
    th = sockets["SOCKET_THORAX"]
    mb = th.matrix_basis.copy()
    th.matrix_basis = Matrix.Identity(4) @ root.matrix_world.inverted()
    bpy.context.view_layer.update()
    rc = rib_objs["RIBCAGE"]
    select([th, rc] + list(rc.children_recursive))
    bpy.ops.export_scene.fbx(filepath=str(FBX_DIR / "RIBCAGE_v03.fbx"), **kw)
    select([th] + list(vessels.values()) + [dia])
    bpy.ops.export_scene.fbx(filepath=str(FBX_DIR / "CHEST_VESSELS_v03.fbx"), **kw)
    th.matrix_basis = mb
    bpy.context.view_layer.update()
    REPORT["outputs"] = [str(p.relative_to(REPO)).replace("\\", "/") for p in
                         [OUT_BLEND, OUT_FBX] + sorted(FBX_DIR.glob("*_v03.fbx")) + [OUT_JSON]]
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    OUT_JSON.write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
    log("written", REPORT["outputs"])


main()
