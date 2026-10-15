"""Operation incision pieces for SAUSAGE_BUDDY_PATIENT_v01 in the TABLE_REST pose (Blender 5.2, background).

blender -b --factory-startup --python build_incisions_v01.py [-- --out <dir>] [--rest <Patient_TableRest_v01.blend>]

For each marker INC_KIDNEY_L / INC_KIDNEY_R / INC_LIVER:
  INCISION_<X>_OPEN   oval skin rim (Buddy_Skin) + rose inner wall + dark shallow floor; cartoon, no gore
  INCISION_<X>_COVER  thin skin-coloured cover hugging the belly with a subtle dotted guide line
Object origin and axes = the marker (local +Z = skin normal, local Y = along the body toward the head).
The objects are placed at the marker's TABLE_REST pose in table-local space (drop the FBX at the table root to line
up with the patient; or parent a piece to its marker with zero local position/rotation).
The body is not cut: the floor sits ~1 mm above the skin and the raised rim makes it read as a shallow opening.
"""
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

from v02_common import (RIG_NAME, PATIENT_MESHES, INC_NAMES, V02, clean_scene, ensure_collection, refuse_overwrite,
                        rnd, log, argv_after_dashes, tri_count, make_material)

ARGS = argv_after_dashes()
OUT_DIR = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else V02
REST_BLEND = Path(ARGS[ARGS.index("--rest") + 1]) if "--rest" in ARGS else V02 / "Patient_TableRest_v01.blend"
OUT_BLEND = OUT_DIR / "OperationIncisions_v01.blend"
OUT_FBX = OUT_DIR / "OperationIncisions_v01.fbx"
OUT_JSON = OUT_DIR / "OperationIncisions_v01_validation.json"

# outer size (length along the body x width), metres
SIZES = {"INC_KIDNEY_L": (0.092, 0.054), "INC_KIDNEY_R": (0.092, 0.054), "INC_LIVER": (0.092, 0.058)}
SEG = 18
# (ellipse scale, height above skin along the marker normal, material slot) rings from the outside in
RIM = [(1.00, -0.0008, 0), (0.94, 0.0042, 0), (0.85, 0.0060, 0), (0.77, 0.0044, 1), (0.70, 0.0016, 2)]
FLOOR_H = 0.0010
COVER_RINGS = [(1.00, -0.0008), (0.95, 0.0011), (0.80, 0.0016), (0.45, 0.0018)]
DASHES = 7


def load_rest():
    coll = ensure_collection("REFERENCE_PATIENT_TABLE_REST")
    with bpy.data.libraries.load(str(REST_BLEND), link=False) as (src, dst):
        dst.objects = [RIG_NAME, *PATIENT_MESHES, *INC_NAMES]
    objs = {}
    for ob in dst.objects:
        coll.objects.link(ob)
        objs[ob.name] = ob
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    return objs


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


def skin_point(bvh, mw, mwi, x, y):
    """Marker-local skin height at (x, y): cast along the marker -Z from 6 cm above."""
    o = mw @ Vector((x, y, 0.06))
    d = (mw.to_3x3() @ Vector((0, 0, -1))).normalized()
    hit = bvh.ray_cast(o, d, 0.15)
    assert hit[0] is not None, f"no skin under ({x:.3f}, {y:.3f})"
    return (mwi @ hit[0]).z


def ellipse(a, b, s, k):
    t = 2 * math.pi * k / SEG
    # local Y = along the body (length a), local X = across (width b)
    return b / 2 * s * math.cos(t), a / 2 * s * math.sin(t)


def build_open(bvh, mw, mwi, a, b):
    bm = bmesh.new()
    rings = []
    for s, h, _ in RIM:
        ring = []
        for k in range(SEG):
            x, y = ellipse(a, b, s, k)
            ring.append(bm.verts.new((x, y, skin_point(bvh, mw, mwi, x, y) + h)))
        rings.append(ring)
    for ri in range(len(rings) - 1):
        for k in range(SEG):
            f = bm.faces.new((rings[ri][k], rings[ri][(k + 1) % SEG], rings[ri + 1][(k + 1) % SEG], rings[ri + 1][k]))
            f.material_index = 1 if ri >= 2 else 0
    c = bm.verts.new((0, 0, skin_point(bvh, mw, mwi, 0, 0) + FLOOR_H))
    for k in range(SEG):
        f = bm.faces.new((rings[-1][k], rings[-1][(k + 1) % SEG], c))
        f.material_index = 2
    return bm


def build_cover(bvh, mw, mwi, a, b):
    bm = bmesh.new()
    rings = []
    for s, h in COVER_RINGS:
        ring = []
        for k in range(SEG):
            x, y = ellipse(a, b, s, k)
            ring.append(bm.verts.new((x, y, skin_point(bvh, mw, mwi, x, y) + h)))
        rings.append(ring)
    for ri in range(len(rings) - 1):
        for k in range(SEG):
            bm.faces.new((rings[ri][k], rings[ri][(k + 1) % SEG], rings[ri + 1][(k + 1) % SEG], rings[ri + 1][k]))
    c = bm.verts.new((0, 0, skin_point(bvh, mw, mwi, 0, 0) + COVER_RINGS[-1][1]))
    for k in range(SEG):
        bm.faces.new((rings[-1][k], rings[-1][(k + 1) % SEG], c))
    # dotted guide line along the body axis: short flat dashes 0.6 mm above the cover
    span = a * 0.72
    for i in range(DASHES):
        yc = -span / 2 + span * i / (DASHES - 1)
        ql = []
        for dx, dy in ((-0.0013, -0.0035), (0.0013, -0.0035), (0.0013, 0.0035), (-0.0013, 0.0035)):
            x, y = dx, yc + dy
            ql.append(bm.verts.new((x, y, skin_point(bvh, mw, mwi, x, y) + COVER_RINGS[-1][1] + 0.0006)))
        f = bm.faces.new(ql)
        f.material_index = 1
    return bm


def finish(bm, name, mats, mw, coll):
    # faces are wound counter-clockwise seen from the marker's +Z (normals point away from the skin)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.matrix_world = mw
    return ob


def main():
    refuse_overwrite(OUT_BLEND, OUT_FBX, OUT_JSON)
    clean_scene()
    pt = load_rest()
    bvh = body_bvh(pt)
    skin_src = pt["Body"].data.materials[0]
    assert skin_src.name.startswith("Buddy_Skin"), skin_src.name
    skin = skin_src              # the patient's own Buddy_Skin (Unity remaps it to the patient's material)
    wall = make_material("MAT_Incision_Wall", (0.42, 0.11, 0.10, 1.0), rough=0.75)
    floor = make_material("MAT_Incision_Cavity", (0.13, 0.035, 0.035, 1.0), rough=0.9)
    guide = make_material("MAT_Incision_Guide", (0.52, 0.17, 0.08, 1.0), rough=0.6)
    coll = ensure_collection("OPERATION_INCISIONS_v01")
    out = {}
    for n in INC_NAMES:
        mw = pt[n].matrix_world.copy()
        mwi = mw.inverted()
        a, b = SIZES[n]
        base = "INCISION_" + n[len("INC_"):]
        op = finish(build_open(bvh, mw, mwi, a, b), base + "_OPEN", [skin, wall, floor], mw, coll)
        cv = finish(build_cover(bvh, mw, mwi, a, b), base + "_COVER", [skin, guide], mw, coll)
        op["marker"] = n
        cv["marker"] = n
        bpy.context.view_layer.update()
        # validation: every vertex above the skin except the embedded outer ring; piece origin == marker
        res = {}
        for ob in (op, cv):
            below = 0
            lo = 1e9
            for v in ob.data.vertices:
                sz = skin_point(bvh, mw, mwi, v.co.x, v.co.y)
                d = v.co.z - sz
                lo = min(lo, d)
            res[ob.name] = {"tris": tri_count(ob), "min_height_above_skin_mm": round(lo * 1000, 2),
                            "origin_offset_from_marker_mm": round((ob.matrix_world.translation - mw.translation).length * 1000, 4),
                            "axes_match_marker": all((ob.matrix_world.to_3x3().col[i] - mw.to_3x3().col[i]).length < 1e-6 for i in range(3)),
                            "size_m": [a, b]}
        out[n] = res
        log(n, res)
    for ob in list(pt.values()):
        if ob.name != RIG_NAME and ob.type == "MESH":
            ob.hide_render = False
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    bpy.ops.object.select_all(action="DESELECT")
    for ob in coll.objects:
        ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, object_types={"MESH"},
                             use_mesh_modifiers=True, bake_anim=False, axis_forward="-Z", axis_up="Y",
                             apply_scale_options="FBX_SCALE_UNITS", use_custom_props=True)
    OUT_JSON.write_text(json.dumps(out, indent=2))
    log("exported", OUT_FBX)


main()
