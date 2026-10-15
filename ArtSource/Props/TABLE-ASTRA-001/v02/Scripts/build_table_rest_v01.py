"""Build the TABLE_REST pose of SAUSAGE_BUDDY_PATIENT_v01 on TABLE-ASTRA-001 (Blender 5.2, background).

blender -b --factory-startup --python build_table_rest_v01.py

Writes (refuses to overwrite):
  v02/Patient_TableRest_v01.blend   patient posed on the v01 table (table = reference only), action Patient_TableRest
  v02/Patient_TableRest_v01.fbx     armature only, one 1-frame take (Buddy animation export settings)
  v02/table_rest_metrics_v01.json   contact gaps, penetration checks, joint and marker positions
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from v02_common import (P, RIG_NAME, PATIENT_MESHES, INC_NAMES, V02, clean_scene, load_table, load_patient, bvh_world,
                        refuse_overwrite, rnd, log, unity_pos, unity_euler, unity_quat, argv_after_dashes)
from pose_lib_v01 import DEFAULT, apply_pose, place_rig, set_local, contact_metrics, vertex_regions, rz

_args = argv_after_dashes()
OUT_DIR = Path(_args[_args.index("--out") + 1]) if "--out" in _args else V02   # --out <dir> for dry runs
OUT_BLEND = OUT_DIR / "Patient_TableRest_v01.blend"
OUT_FBX = OUT_DIR / "Patient_TableRest_v01.fbx"
OUT_METRICS = OUT_DIR / "table_rest_metrics_v01.json"
ACTION = "Patient_TableRest"

# Final TABLE_REST parameters (tuned 2026-10-16; gaps measured by contact_metrics, see metrics json).
POSE = {
    "root_y": 0.0, "pad_z": 0.66, "hips_h": 0.1112,
    "neck": 37.0, "head": -25.5,                 # neck S-curve: back of head on the pillow wedge, neck cap clear
    "leg_back": 3.2, "knee": 0.0,                # heels on the pad
    "arm_down": 84.0, "arm_back": 20.0, "elbow": 26.0, "wrist_dev": -7.0,   # forearm + hand on the pad
    "finger_curl": 8.0, "thumb_curl": 0.0,
}
THUMB1_Z = 40.0   # thumb laid along the index finger (rest axes, mirrored per side)


def pose_patient(rig):
    p = dict(DEFAULT)
    p.update(POSE)
    place_rig(rig, p)
    apply_pose(rig, p)
    for side, sgn in (("Left", 1.0), ("Right", -1.0)):
        set_local(rig, P + side + "HandThumb1", rz(sgn * THUMB1_Z))
        for i in (2, 3):
            set_local(rig, P + side + "HandThumb" + str(i), rz(0.0))
    bpy.context.view_layer.update()
    return p


def mesh_bvh(ob, face_filter=None):
    dg = bpy.context.evaluated_depsgraph_get()
    eo = ob.evaluated_get(dg)
    me = eo.to_mesh()
    mw = ob.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(pl.vertices) for pl in me.polygons if face_filter is None or face_filter(pl)]
    eo.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0), verts


def penetration_checks(pt, table_objs):
    """Triangle-overlap tests of every patient mesh against every table mesh, plus arm-into-torso test."""
    res = {}
    tbl = {n: bvh_world(o)[0] for n, o in table_objs.items() if o.type == "MESH"}
    for pn in PATIENT_MESHES:
        pb, _ = mesh_bvh(pt[pn])
        hits = {tn: len(pb.overlap(tb)) for tn, tb in tbl.items()}
        res[pn] = {k: v for k, v in hits.items() if v}
    # forearm / hand vertices vs the trunk + thigh + shorts surface (signed by face normal)
    body = pt["Body"]
    regions = vertex_regions(body)
    dg = bpy.context.evaluated_depsgraph_get()
    eo = body.evaluated_get(dg)
    me = eo.to_mesh()
    mw = body.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    trunk = {"pelvis", "mid_back", "upper_back", "thigh"}
    polys = [tuple(pl.vertices) for pl in me.polygons
             if all(regions[i] in trunk for i in pl.vertices)]
    eo.to_mesh_clear()
    tb = BVHTree.FromPolygons(verts, polys)
    sb, _ = mesh_bvh(pt["Shorts"])
    worst = 1e9
    for i, r in enumerate(regions):
        if r not in ("forearm", "hand"):
            continue
        for bvh in (tb, sb):
            loc, nrm, _, dist = bvh.find_nearest(verts[i])
            if loc is None:
                continue
            signed = dist if (verts[i] - loc).dot(nrm) >= 0 else -dist
            worst = min(worst, signed)
    res["arm_vs_trunk_min_signed_mm"] = round(worst * 1000, 1)
    return res


def key_action(rig):
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.keyframe_insert("location", frame=1)
        pb.keyframe_insert("rotation_quaternion", frame=1)
        pb.keyframe_insert("scale", frame=1)
    act = rig.animation_data.action
    act.name = ACTION
    return act


def main():
    refuse_overwrite(OUT_BLEND, OUT_FBX, OUT_METRICS)
    clean_scene()
    table = load_table(collection_name="REFERENCE_TABLE_v01")
    pt = load_patient(collection_name="PATIENT")
    rig = pt[RIG_NAME]
    assert len(rig.data.bones) == 65
    p = pose_patient(rig)

    pad_bvh, _, _ = bvh_world(table["GEO_Padded_Top"])
    regions = {n: vertex_regions(pt[n]) for n in PATIENT_MESHES}
    gaps, offpad = contact_metrics({n: pt[n] for n in PATIENT_MESHES}, pad_bvh, regions)
    pen = penetration_checks(pt, table)
    log("GAPS", gaps, "offpad", offpad)
    log("PEN", pen)

    joints = {b: rnd(rig.matrix_world @ rig.pose.bones[P + b].head, 4)
              for b in ("Hips", "Spine", "Spine2", "Neck", "Head", "HeadTop_End", "LeftHand", "RightHand",
                        "LeftForeArm", "RightForeArm", "LeftFoot", "RightFoot", "LeftLeg", "RightLeg")}
    markers = {}
    for n in INC_NAMES:
        m = pt[n].matrix_world
        r3 = m.to_3x3().normalized()
        markers[n] = {"blender_table_local": {"position": rnd(m.translation, 4),
                                              "x_axis": rnd(r3.col[0], 4), "y_axis": rnd(r3.col[1], 4),
                                              "z_axis_normal": rnd(r3.col[2], 4)},
                      "unity_prefab_local": {"position": rnd(unity_pos(m.translation), 4),
                                             "rotation_quat_xyzw": rnd(unity_quat(r3), 5),
                                             "euler_deg": unity_euler(r3)}}

    act = key_action(rig)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 1
    scene.render.fps = 30
    scene.frame_set(1)
    # The only action in the file.
    for a in list(bpy.data.actions):
        if a != act:
            bpy.data.actions.remove(a)
    assert [a.name for a in bpy.data.actions] == [ACTION]

    rig_world = rig.matrix_world.copy()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    log("saved", OUT_BLEND)

    # FBX: rig object at identity (PatientRest supplies the placement), Buddy clip settings.
    rig.location = (0, 0, 0)
    rig.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, object_types={"ARMATURE"},
                             add_leaf_bones=False, use_armature_deform_only=False, bake_anim=True,
                             bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False, bake_anim_step=0.5,
                             bake_anim_simplify_factor=0, axis_forward="-Z", axis_up="Y", apply_unit_scale=True,
                             use_mesh_modifiers=False)
    log("exported", OUT_FBX)

    metrics = {
        "pose_params": {k: p[k] for k in sorted(p)} | {"thumb1_z_deg": THUMB1_Z},
        "patient_root_blender_table_local": {"location": [0.0, p["root_y"], p["pad_z"]], "rotation_euler_deg": [0, 0, 180]},
        "region_min_gap_above_pad_mm": {k: v[0] for k, v in gaps.items()},
        "region_min_gap_points": {k: v[1] for k, v in gaps.items()},
        "vertices_without_pad_below": offpad,
        "triangle_overlaps_patient_vs_table": {k: v for k, v in pen.items() if k in PATIENT_MESHES},
        "arm_vs_trunk_min_signed_mm": pen["arm_vs_trunk_min_signed_mm"],
        "joints_blender_table_local": joints,
        "inc_markers": markers,
        "rig_matrix_world_on_table": [rnd(r, 6) for r in rig_world],
    }
    OUT_METRICS.write_text(json.dumps(metrics, indent=2))
    log("wrote", OUT_METRICS)


main()
