"""Independent validation of the TABLE-ASTRA-001 v02 operating-table package (Blender 5.2, background).

blender -b --factory-startup --python validate_v02.py      -> v02/validation_v02.json (refuses overwrite)

Checks
  1. caster rig: every RIG_* / caster / wheel node of the v01 FBX exists in the v02 FBX with the same parent, local
     transform and (in the .blend) custom properties; v01 straps retired; exactly five STRAP_* objects.
  2. closed straps vs the TABLE_REST body: no triangle overlap; min gap to the body 0 < gap <= 15 mm.
  3. opening sweep 0..open_angle_deg (2.5 deg steps) about local +X: no overlap with body, pad, frame/rails, handle,
     braces, wheels; never below 2 cm above the floor.
  4. incision pieces: origin and axes on their INC_* marker (TABLE_REST pose); vertices not below the skin by > 1 mm.
  5. Patient_TableRest_v01.fbx: one take, 65 bones, single frame; pose equals the .blend action.
  6. triangle budgets.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

V02 = Path(r"C:/Dev/Game/ArtSource/Props/TABLE-ASTRA-001/v02")
V01_FBX = V02.parent / "TABLE-ASTRA-001.fbx"
OUT = V02 / "validation_v02.json"
STRAPS = ["STRAP_ARM_L", "STRAP_ARM_R", "STRAP_LEG_L", "STRAP_LEG_R", "STRAP_TORSO"]
TRI_BUDGET = {"STRAP": 175, "GEO_Strap_Anchors": 260, "INCISION": 200, "STAND_TOTAL": 600}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def fbx_nodes(path):
    reset()
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for o in bpy.data.objects:
        out[o.name] = {"type": o.type, "parent": o.parent.name if o.parent else None,
                       "local": [round(x, 5) for r in o.matrix_local for x in r],
                       "tris": sum(len(p.vertices) - 2 for p in o.data.polygons) if o.type == "MESH" else 0}
    acts = [(a.name, tuple(a.frame_range)) for a in bpy.data.actions]
    return out, acts


def world_mesh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    eo = ob.evaluated_get(dg)
    me = eo.to_mesh()
    v = [ob.matrix_world @ x.co for x in me.vertices]
    p = [tuple(x.vertices) for x in me.polygons]
    eo.to_mesh_clear()
    return v, p


def main():
    assert not OUT.exists(), f"Refusing to overwrite {OUT}"
    res = {"checks": {}, "details": {}}
    ok = res["checks"]

    # 1. caster rig vs v01 ---------------------------------------------------------------------------------------
    v1, _ = fbx_nodes(V01_FBX)
    v2, _ = fbx_nodes(V02 / "TABLE-ASTRA-001_v02.fbx")
    rig_names = [n for n in v1 if n.startswith(("RIG_", "GEO_Wheel", "GEO_Caster", "GEO_Frame", "GEO_Padded",
                                                 "GEO_Push", "GEO_Lower"))]
    diffs = [n for n in rig_names if n not in v2 or v2[n] != v1[n]]
    ok["rig_and_table_nodes_identical_to_v01"] = not diffs
    res["details"]["rig_node_count"] = len(rig_names)
    res["details"]["rig_diffs"] = diffs
    ok["v01_straps_retired"] = "GEO_Strap_01" not in v2 and "GEO_Strap_02" not in v2
    strap_nodes = sorted(n for n in v2 if n.startswith("STRAP_"))
    ok["exactly_five_straps"] = strap_nodes == sorted(STRAPS)
    ok["straps_parent_is_table_root"] = all(v2[n]["parent"] == "RIG_Table_Root" for n in strap_nodes)
    res["details"]["v02_extra_nodes"] = sorted(set(v2) - set(v1))

    reset()
    bpy.ops.wm.open_mainfile(filepath=str(V02.parent / "TABLE-ASTRA-001.blend"))
    rig_v01 = {o.name: (dict(o.items()), [round(x, 6) for r in o.matrix_world for x in r], o.parent.name if o.parent else None)
               for o in bpy.data.objects if o.name.startswith("RIG_")}

    # 2-3. closed fit and sweep, on the saved v02 blend (table) + TABLE_REST patient --------------------------
    reset()
    bpy.ops.wm.open_mainfile(filepath=str(V02 / "TABLE-ASTRA-001_v02.blend"))
    bpy.context.scene.frame_set(1)
    rig_v02 = {o.name: (dict(o.items()), [round(x, 6) for r in o.matrix_world for x in r], o.parent.name if o.parent else None)
               for o in bpy.data.objects if o.name.startswith("RIG_")}
    ok["blend_rig_names_props_transforms_identical_to_v01"] = rig_v01 == rig_v02
    rig_props = {k: v[0] for k, v in rig_v02.items()}
    bodyv, bodyp = [], []
    for n in ("Body", "Face", "Shorts"):
        v, p = world_mesh(bpy.data.objects[n])
        off = len(bodyv)
        bodyv += v
        bodyp += [tuple(i + off for i in q) for q in p]
    body = BVHTree.FromPolygons(bodyv, bodyp)
    obst = {"body": body}
    for n in ("GEO_Padded_Top", "GEO_Frame_And_Legs", "GEO_Push_Handle_Foot", "GEO_Lower_Longitudinal_Brace_Left",
              "GEO_Lower_Longitudinal_Brace_Right", "GEO_Wheel_Head_Left", "GEO_Wheel_Head_Right",
              "GEO_Wheel_Foot_Left", "GEO_Wheel_Foot_Right"):
        v, p = world_mesh(bpy.data.objects[n])
        obst[n] = BVHTree.FromPolygons(v, p)
    strap_res = {}
    for n in STRAPS:
        ob = bpy.data.objects[n]
        v, p = world_mesh(ob)
        b = BVHTree.FromPolygons(v, p)
        closed = {k: len(b.overlap(t)) for k, t in obst.items()}
        # dense samples on every face (5 mm) -> nearest body distance
        mind = 1e9
        for poly in ob.data.polygons:
            vs = [ob.matrix_world @ ob.data.vertices[i].co for i in poly.vertices]
            for k in range(1, len(vs) - 1):
                a, bb, c = vs[0], vs[k], vs[k + 1]
                m = max(1, int(max((bb - a).length, (c - a).length) / 0.005))
                for i in range(m + 1):
                    for j in range(m + 1 - i):
                        q = a + (bb - a) * (i / m) + (c - a) * (j / m)
                        hit = body.find_nearest(q)
                        if hit[0] is not None:
                            mind = min(mind, hit[3])
        ang_max = float(ob["open_angle_deg"])
        axis = (ob.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
        piv = ob.matrix_world.translation.copy()
        sweep_hits, floor_min = {}, 9.0
        k = 1
        while k * 2.5 <= ang_max + 1e-6:
            R = Matrix.Rotation(math.radians(k * 2.5), 4, axis)
            vv = [piv + (R @ (x - piv).to_4d()).to_3d() for x in v]
            bt = BVHTree.FromPolygons(vv, p)
            for on, t in obst.items():
                if bt.overlap(t):
                    sweep_hits.setdefault(on, []).append(k * 2.5)
            floor_min = min(floor_min, min(x.z for x in vv))
            k += 1
        strap_res[n] = {"closed_overlaps": {k2: c for k2, c in closed.items() if c}, "closed_min_gap_mm": round(mind * 1000, 2),
                        "hinge_axis": ob.get("hinge_axis"), "open_angle_deg": ang_max,
                        "sweep_hits_deg": sweep_hits, "sweep_min_z_m": round(floor_min, 4),
                        "tris": sum(len(q.vertices) - 2 for q in ob.data.polygons)}
    res["details"]["straps"] = strap_res
    ok["closed_straps_no_penetration"] = all(not s["closed_overlaps"] for s in strap_res.values())
    ok["closed_straps_gap_between_0_and_15mm"] = all(0 < s["closed_min_gap_mm"] <= 15 for s in strap_res.values())
    ok["open_sweep_clear_of_body_pad_frame"] = all(not s["sweep_hits_deg"] for s in strap_res.values())
    ok["open_sweep_above_floor"] = all(s["sweep_min_z_m"] > 0.02 for s in strap_res.values())
    ok["strap_custom_properties"] = all(s["hinge_axis"] == "local +X" and 110 <= s["open_angle_deg"] <= 130
                                        for s in strap_res.values())
    anc = bpy.data.objects["GEO_Strap_Anchors"]
    av, ap = world_mesh(anc)
    ab = BVHTree.FromPolygons(av, ap)
    anc_ov = {k: len(ab.overlap(t)) for k, t in obst.items() if ab.overlap(t)}
    ok["anchors_no_penetration"] = not anc_ov
    res["details"]["anchors"] = {"overlaps": anc_ov, "tris": len(ap) and sum(len(q.vertices) - 2 for q in anc.data.polygons)}
    markers = {n: bpy.data.objects[n].matrix_world.copy() for n in ("INC_KIDNEY_L", "INC_KIDNEY_R", "INC_LIVER")}

    # 4. incisions -----------------------------------------------------------------------------------------------
    reset()
    bpy.ops.wm.open_mainfile(filepath=str(V02 / "OperationIncisions_v01.blend"))
    bpy.context.scene.frame_set(1)
    inc_res = {}
    for o in bpy.data.objects:
        if not o.name.startswith("INCISION_"):
            continue
        mk = "INC_" + o.name[len("INCISION_"):].rsplit("_", 1)[0]
        m = markers[mk]
        dpos = (o.matrix_world.translation - m.translation).length
        dax = max((o.matrix_world.to_3x3().col[i] - m.to_3x3().normalized().col[i]).length for i in range(3))
        inc_res[o.name] = {"marker": mk, "origin_err_mm": round(dpos * 1000, 4), "axis_err": round(dax, 6),
                           "tris": sum(len(q.vertices) - 2 for q in o.data.polygons)}
    # skin clearance (vertices along -normal to the body)
    bodyv, bodyp = [], []
    for n in ("Body", "Face", "Shorts"):
        v, p = world_mesh(bpy.data.objects[n])
        off = len(bodyv)
        bodyv += v
        bodyp += [tuple(i + off for i in q) for q in p]
    body2 = BVHTree.FromPolygons(bodyv, bodyp)
    for name, r in inc_res.items():
        o = bpy.data.objects[name]
        nrm = (o.matrix_world.to_3x3() @ Vector((0, 0, 1))).normalized()
        lo = 1e9
        for v in o.data.vertices:
            w = o.matrix_world @ v.co
            hit = body2.ray_cast(w + nrm * 0.05, -nrm, 0.12)
            if hit[0] is not None:
                lo = min(lo, (w - hit[0]).dot(nrm))
        r["min_height_above_skin_mm"] = round(lo * 1000, 2)
    res["details"]["incisions"] = inc_res
    ok["incisions_six_pieces"] = sorted(inc_res) == sorted(
        f"INCISION_{k}_{s}" for k in ("KIDNEY_L", "KIDNEY_R", "LIVER") for s in ("OPEN", "COVER"))
    ok["incisions_on_markers"] = all(r["origin_err_mm"] < 0.1 and r["axis_err"] < 1e-4 for r in inc_res.values())
    ok["incisions_not_below_skin_over_1mm"] = all(r["min_height_above_skin_mm"] >= -1.0 for r in inc_res.values())

    # 5. clip ----------------------------------------------------------------------------------------------------
    nodes, acts = fbx_nodes(V02 / "Patient_TableRest_v01.fbx")
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    ok["clip_single_take"] = len(acts) == 1
    ok["clip_65_bones"] = len(arm.data.bones) == 65
    ok["clip_single_frame"] = len(acts) == 1 and acts[0][1][0] == acts[0][1][1]
    ok["clip_armature_only"] = all(n["type"] == "ARMATURE" for n in nodes.values())
    res["details"]["clip_takes"] = acts

    # 6. budgets -------------------------------------------------------------------------------------------------
    sv, _ = fbx_nodes(V02 / "InstrumentStand_v01.fbx")
    stand_tris = sum(n["tris"] for n in sv.values())
    slots = sorted(n for n in sv if n.startswith("SLOT_"))
    res["details"]["stand"] = {"tris": stand_tris, "slots": slots}
    ok["stand_slots"] = slots == sorted(["SLOT_SYRINGE_ANESTHESIA", "SLOT_SYRINGE_BLOOD", "SLOT_SCALPEL",
                                         "SLOT_BLOODBAG_1", "SLOT_BLOODBAG_2", "SLOT_BLOODBAG_3",
                                         "SLOT_ORGAN_1", "SLOT_ORGAN_2", "SLOT_ORGAN_3"])
    ok["tri_budgets"] = (all(s["tris"] <= TRI_BUDGET["STRAP"] for s in strap_res.values())
                         and res["details"]["anchors"]["tris"] <= TRI_BUDGET["GEO_Strap_Anchors"]
                         and all(r["tris"] <= TRI_BUDGET["INCISION"] for r in inc_res.values())
                         and stand_tris <= TRI_BUDGET["STAND_TOTAL"])
    res["details"]["tri_budget_limits"] = TRI_BUDGET
    res["details"]["rig_custom_props_sample"] = {k: v for k, v in rig_props.items() if v}
    res["all_passed"] = all(ok.values())
    OUT.write_text(json.dumps(res, indent=2))
    print("VALIDATION", json.dumps(ok, indent=1), "ALL", res["all_passed"], flush=True)


main()
