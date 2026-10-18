"""Sausage Buddy PATIENT v04: Patient_v03 (closed back, same rig/weights) with the v04 sockets/markers (the organ block moved
down 4.5 cm and forward 3 mm) and the stencil zone grown to cover the bigger chest+belly opening.

blender -b Patient_v03/SAUSAGE_BUDDY_PATIENT_v03.blend --python Patient_v04/build_patient_v04.py [-- --out <dir> --organs-json <f>]
The v03 file is only read. Needs Organs_v04/organs_v04_build.json. Writes next to this script (refuses to overwrite):
  SAUSAGE_BUDDY_PATIENT_v04.blend / .fbx, ORGANS_LAYOUT_v04.json, build_report_SAUSAGE_BUDDY_PATIENT_v04.json

Body material slots stay as in v03: [0] Buddy_Skin = the only stencil-tested skin (front torso zone), [1] Buddy_Skin_Nose,
[2] Patient_Skin_Closed (never stencil-tested). v04 adds to the zone every trunk face that lies under the v04 opening
(mask outline + 2.5 cm margin, front-facing), so the larger opening is never covered by its own skin.
"""
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
REPO = Path(r"C:/Dev/Game")
ORG4 = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04"
sys.path.insert(0, str(ORG4 / "Scripts"))
import organs_layout_v04 as LAY  # noqa: E402

STEM = "SAUSAGE_BUDDY_PATIENT_v04"
TABLE_REST = REPO / "ArtSource/Props/TABLE-ASTRA-001/v02/Patient_TableRest_v01.blend"
LAYOUT_V03D = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v03/ORGANS_LAYOUT_v03d.json"
P = "mixamorig:"
RIG = "Buddy_Rig_Mixamo65"
C_B2U = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))
ZONE_MARGIN = 0.025

scene = bpy.context.scene
rig = bpy.data.objects[RIG]
body = bpy.data.objects["Body"]
assert Path(bpy.data.filepath).stem == "SAUSAGE_BUDDY_PATIENT_v03", "run on SAUSAGE_BUDDY_PATIENT_v03.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUTDIR = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else HERE
ORGJSON = Path(ARGS[ARGS.index("--organs-json") + 1]) if "--organs-json" in ARGS else ORG4 / "organs_v04_build.json"
out_blend, out_fbx = OUTDIR / f"{STEM}.blend", OUTDIR / f"{STEM}.fbx"
out_layout, out_report = OUTDIR / "ORGANS_LAYOUT_v04.json", OUTDIR / f"build_report_{STEM}.json"
for p in (out_blend, out_fbx, out_layout, out_report):
    assert not p.exists(), f"refusing to overwrite {p}"
ORGB = json.loads(ORGJSON.read_text(encoding="utf-8"))
L3D = json.loads(LAYOUT_V03D.read_text(encoding="utf-8"))


def geo_hash(ob):
    h = hashlib.sha1()
    for v in ob.data.vertices:
        h.update(("%.6f %.6f %.6f" % tuple(v.co)).encode())
        for g in v.groups:
            h.update(("%d:%.5f" % (g.group, g.weight)).encode())
    for uvl in ob.data.uv_layers:
        for d in uvl.data:
            h.update(("%.5f %.5f" % tuple(d.uv)).encode())
    return h.hexdigest()


def bone_hash(r):
    h = hashlib.sha1()
    for b in r.data.bones:
        h.update(b.name.encode())
        for row in b.matrix_local:
            h.update(("%.6f %.6f %.6f %.6f" % tuple(row)).encode())
    return h.hexdigest()


def rnd(v, n=4):
    return [round(float(c), n) for c in v]


before = {n: geo_hash(bpy.data.objects[n]) for n in ("Body", "Face", "Shorts")}
before["bones"] = bone_hash(rig)
if rig.animation_data:
    rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()
me = body.data
assert [m.name for m in me.materials] == ["Buddy_Skin", "Buddy_Skin_Nose", "Patient_Skin_Closed"]
mat_before = Counter(p.material_index for p in me.polygons)

# ------------------------------------------------------------------------------------------- 1. markers and sockets
for o in [o for o in bpy.data.objects if o.type == "EMPTY" and o.name.startswith(("INC_", "SOCKET_", "GUIDE_"))]:
    bpy.data.objects.remove(o, do_unlink=True)
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
seen, islands = set(), []
for v in bm.verts:
    if v.index in seen:
        continue
    stack, comp = [v], set()
    seen.add(v.index)
    while stack:
        x = stack.pop()
        comp.add(x.index)
        for e in x.link_edges:
            o = e.other_vert(x)
            if o.index not in seen:
                seen.add(o.index)
                stack.append(o)
    islands.append(comp)
bm.free()
trunk = max(islands, key=len)
tv = [body.matrix_world @ me.vertices[i].co for i in sorted(trunk)]
tidx = {i: k for k, i in enumerate(sorted(trunk))}
bvh_trunk = BVHTree.FromPolygons(tv, [[tidx[i] for i in p.vertices] for p in me.polygons if p.vertices[0] in trunk])
spine = rig.data.bones[P + "Spine"]


def skin_front(x, z):
    hit, normal, _, _ = bvh_trunk.ray_cast(Vector((x, -0.5, z)), Vector((0, 1, 0)))
    assert hit is not None, (x, z)
    if normal.y > 0:
        normal = -normal
    return hit, normal.normalized()


def frame(z_axis, primary, primary_is="Y"):
    z = z_axis.normalized()
    if primary_is == "Y":
        y = (primary - z * primary.dot(z)).normalized()
        x = y.cross(z)
    else:
        x = (primary - z * primary.dot(z)).normalized()
        y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def add_marker(name, matrix, size=0.05, kind="SINGLE_ARROW"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = kind
    e.empty_display_size = size
    scene.collection.objects.link(e)
    e.matrix_world = matrix
    bpy.context.view_layer.update()
    mw = e.matrix_world.copy()
    e.parent = rig
    e.parent_type = "BONE"
    e.parent_bone = spine.name
    e.matrix_world = mw
    return e


markers = {}
for sname, sd in ORGB["sockets"].items():
    mw = Matrix.Translation(sd["rest_position"]) @ Matrix((sd["rest_x_axis"], sd["rest_y_axis"], sd["rest_z_axis"])).transposed().to_4x4()
    markers[sname] = add_marker(sname, mw, 0.03, "ARROWS")
INC = {"INC_LIVER": ("SOCKET_LIVER", "X"), "INC_KIDNEY_L": ("SOCKET_KIDNEY_L", "Y"), "INC_KIDNEY_R": ("SOCKET_KIDNEY_R", "Y"),
       "INC_HEART": ("SOCKET_HEART", "Y"), "INC_LUNG_L": ("SOCKET_LUNG_L", "Y"), "INC_LUNG_R": ("SOCKET_LUNG_R", "Y")}
inc_info = {}
for name, (sname, prim) in INC.items():
    smw = markers[sname].matrix_world
    c = smw.translation
    sk, n = skin_front(c.x, c.z)
    axis = smw.col[0].xyz if prim == "X" else smw.col[1].xyz
    rot = frame(n, axis, prim)
    markers[name] = add_marker(name, Matrix.Translation(c) @ rot.to_4x4())
    hit = bvh_trunk.ray_cast(c, rot.col[2])
    inc_info[name] = {"socket": sname, "depth_below_skin_m": round(hit[3], 4), "skin_point_along_z": rnd(hit[0])}
op = LAY.OPENING
sk, n = skin_front(0.0, op["centre_z"])
abd = Matrix.Translation(sk) @ frame(n, Vector((0, 0, 1))).to_4x4()
markers["INC_ABDOMEN"] = add_marker("INC_ABDOMEN", abd, 0.08)
for gname, gz in (("GUIDE_BELLY_START", LAY.GUIDE["start_z"]), ("GUIDE_BELLY_END", LAY.GUIDE["end_z"]),
                  ("GUIDE_CHEST_START", LAY.CHEST["guide_start_z"]), ("GUIDE_CHEST_END", LAY.CHEST["guide_end_z"])):
    s, gn = skin_front(0.0, gz)
    markers[gname] = add_marker(gname, Matrix.Translation(s) @ frame(gn, Vector((0, 0, 1))).to_4x4(), 0.03, "SPHERE")
sk, n = skin_front(0.0, LAY.CHEST["centre_z"])
markers["INC_CHEST"] = add_marker("INC_CHEST", Matrix.Translation(sk) @ frame(n, Vector((0, 0, 1))).to_4x4(), 0.08)
bpy.context.view_layer.update()

# ------------------------------------------------------------------------------------------- 2. stencil zone for the v04 opening
outline = LAY.outline_xy(op, 128)


def in_poly(x, y, poly):
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def dist_poly(x, y, poly):
    best = 9.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / max(1e-12, dx * dx + dy * dy)))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


abd_inv = abd.inverted()
az = abd.col[2].xyz
added = candidates = 0
for p in me.polygons:
    if p.material_index == 1 or p.vertices[0] not in trunk:
        continue
    c = body.matrix_world @ p.center
    lc = abd_inv @ c
    if lc.z < -0.04 or p.normal.dot(az) < 0.2:
        continue
    if in_poly(lc.x, lc.y, outline) or dist_poly(lc.x, lc.y, outline) <= ZONE_MARGIN:
        candidates += 1
        if p.material_index != 0:
            p.material_index = 0
            added += 1
me.update()
mat_after = Counter(p.material_index for p in me.polygons)

# ------------------------------------------------------------------------------------------- 3. TABLE_REST frame
with bpy.data.libraries.load(str(TABLE_REST), link=False) as (src, dst):
    dst.objects = [RIG]
trig = dst.objects[0]
scene.collection.objects.link(trig)
scene.frame_set(1)
bpy.context.view_layer.update()
pb = trig.pose.bones[P + "Spine"]
T = trig.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
bpy.data.objects.remove(trig, do_unlink=True)
for arm in [a for a in bpy.data.armatures if a.users == 0]:
    bpy.data.armatures.remove(arm)
for act in [a for a in bpy.data.actions if a.users == 0]:
    bpy.data.actions.remove(act)


def table_entry(m):
    t = T @ m
    r = t.to_3x3().normalized()
    ru = C_B2U @ r @ C_B2U.transposed()
    q = ru.to_quaternion()
    p = t.translation
    return {"table_blender": {"position": rnd(p), "x_axis": rnd(r.col[0]), "y_axis": rnd(r.col[1]), "z_axis": rnd(r.col[2])},
            "table_unity": {"position": rnd(C_B2U @ p), "z_axis_out": rnd(C_B2U @ r.col[2]), "y_axis": rnd(C_B2U @ r.col[1]),
                            "rotation_quat_xyzw": rnd([q.x, q.y, q.z, q.w], 5)}}


def tpt(p):
    p = T @ Vector(p)
    return {"table_blender": rnd(p), "table_unity": rnd(C_B2U @ p)}


# ------------------------------------------------------------------------------------------- 4. kidney cords (v02 recipe)
GV = LAY.GREAT_VESSELS
CORDS = {"A_renal_artery": {"along": +0.008, "end_dz": +0.016, "radius": 0.0050, "colour": "artery red"},
         "B_renal_vein": {"along": -0.008, "end_dz": -0.012, "radius": 0.0060, "colour": "vein purple"}}
cords_out = {}
for kname, inc in (("ORGAN_KIDNEY_L", "INC_KIDNEY_L"), ("ORGAN_KIDNEY_R", "INC_KIDNEY_R")):
    smw = markers[LAY.ORGANS[kname]["socket"]].matrix_world
    mmw = markers[inc].matrix_world
    side = 1 if smw.translation.x > 0 else -1
    hilum = smw @ Vector((-side * 0.0255, -0.004, 0.004))
    gv = GV["aorta" if side > 0 else "vena_cava"]
    rot = smw.to_3x3()
    cords = {}
    for cname, spec in CORDS.items():
        start = hilum + rot @ Vector((side * 0.002, spec["along"], 0))
        end = Vector((gv["x"] + side * 0.6 * gv["r"], gv["y"], hilum.z + spec["end_dz"]))
        inv = mmw.inverted()
        ls, le = inv @ start, inv @ end
        cords[cname] = {"rest_start": rnd(start), "rest_end": rnd(end), "rest_snip_point": rnd(start.lerp(end, 0.5)),
                        "marker_local_blender_start": rnd(ls), "marker_local_blender_end": rnd(le),
                        "marker_local_unity_start": rnd((-ls.x, ls.y, ls.z)), "marker_local_unity_end": rnd((-le.x, le.y, le.z)),
                        "length_m": round((end - start).length, 4), "radius_m": spec["radius"], "colour": spec["colour"],
                        "ends_on": "aorta" if side > 0 else "vena_cava", "direction_rest": rnd((end - start).normalized()),
                        "table_start": tpt(start), "table_end": tpt(end)}
    cords_out[kname] = {"marker": inc, "hilum_rest": rnd(hilum), "cords": cords}

# ------------------------------------------------------------------------------------------- 5. layout JSON
organs = {}
for oname, od in LAY.ORGANS.items():
    ob = ORGB["objects"][oname]
    inc = next(k for k, v in INC.items() if v[0] == od["socket"])
    organs[oname] = dict(L3D["organs"][oname])
    organs[oname].update({
        "socket": od["socket"], "incision_marker": inc, "rest_socket": ORGB["sockets"][od["socket"]],
        "local_bounds_min_m": ob["local_bounds_min"], "local_bounds_max_m": ob["local_bounds_max"],
        "size_m_xyz_local": ob["size_m_xyz"], "largest_dimension_m": ob["largest_dimension_m"], "tris": ob["tris"],
        "fbx_alone": f"ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/FBX/{oname}_v04.fbx",
        "pull": {"direction": f"{inc} +Z", "depth_below_skin_m": inc_info[inc]["depth_below_skin_m"],
                 "exit_distance_m": round(inc_info[inc]["depth_below_skin_m"] + 0.5 * ob["size_m_xyz"][2] + 0.03, 3)}})
    if oname in cords_out:
        organs[oname]["hilum_rest"] = cords_out[oname]["hilum_rest"]
        organs[oname]["cords"] = cords_out[oname]["cords"]
gs, ge = markers["GUIDE_BELLY_START"].matrix_world.translation, markers["GUIDE_BELLY_END"].matrix_world.translation
cs, ce = markers["GUIDE_CHEST_START"].matrix_world.translation, markers["GUIDE_CHEST_END"].matrix_world.translation
chest_mw = markers["INC_CHEST"].matrix_world
layout = dict(L3D)
layout.update({
    "version": "ORGANS_LAYOUT_v04", "date": "2026-10-18", "patient": f"{STEM}.fbx",
    "v03d_to_v04": {"rigid_shift_rest_m": list(LAY.SHIFT),
                    "what_moved": "every organ socket and everything below it: organs, ribs, sternum halves, spine, RIBCAGE_HALF_L/R "
                                  "hinges, BREAK_* empties, 96 UCX colliders, vessels, airway, diaphragm; no relative change",
                    "why": "the lying patient's chin hid the chest from the top table camera (chin line rest z 1.120 at the midline)",
                    "organs_build": "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/organs_v04_build.json",
                    "collisions_manifest": "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/G38_collisions_manifest_v04.json",
                    "rigid_shift_check": ORGB.get("rigid_shift_check")},
    "organs": organs,
    "incision_markers": {n: dict(inc_info[n], rest_position=rnd(markers[n].matrix_world.translation),
                                 rest_z_axis=rnd(markers[n].matrix_world.col[2].xyz)) for n in INC},
    "ribcage": {k: v for k, v in ORGB["objects"].items() if k.startswith(("RIB", "STERNUM", "SPINE", "BREAK_"))},
    "ribcage_colliders": {"count": sum(1 for k in ORGB["objects"] if k.startswith("UCX_")),
                          "manifest": "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/G38_collisions_manifest_v04.json",
                          "contract": "one convex MeshCollider per UCX_* under its rib/sternum (local identity), layer SurgicalBone, "
                                      "tags SurgicalRib / SurgicalSternum (G38 v03d contract, unchanged)"},
    "ribcage_notes": dict(L3D["ribcage_notes"], hierarchy="SOCKET_THORAX > RIBCAGE > RIBCAGE_HALF_L|R (hinge pivot) > RIB_<L|R>_01..04 "
                                                         "(+ UCX_* parts, BREAK_*), STERNUM_<L|R> (+ UCX_*, BREAK_*); SPINE_THORACIC under RIBCAGE",
                          ribs="4 thick pairs (G38 v03c), colliders G38 v03d"),
    "chest_vessels": {k: v for k, v in ORGB["objects"].items() if k.startswith(("VESSELS", "AIRWAY", "DIAPHRAGM"))},
    "connections": ORGB.get("connections", {}),
    "opening_abdomen": {"marker": "INC_ABDOMEN", "shape": "asymmetric lens: |x| = W (1 - |t|^p)^q, t = y / half_length (top or bottom); "
                        "frames chest + belly; rim/flap/cut-face profiles identical to v03",
                        **{k: v for k, v in op.items()}, "rest": {"centre_on_skin": rnd(abd.translation), "z_axis_skin_normal": rnd(abd.col[2].xyz)},
                        "mesh": "ArtSource/Props/TABLE-ASTRA-001/v04/OperationAbdomen_v04.fbx (origin and axes = INC_ABDOMEN)"},
    "guide_belly": {"start_marker": "GUIDE_BELLY_START", "end_marker": "GUIDE_BELLY_END", "rest_start": rnd(gs), "rest_end": rnd(ge),
                    "length_m": round((ge - gs).length, 4), "abdomen_local_start": rnd(abd_inv @ gs), "abdomen_local_end": rnd(abd_inv @ ge)},
    "chest": {"marker": "INC_CHEST", "rest_centre_on_skin": rnd(chest_mw.translation), "guide_start_marker": "GUIDE_CHEST_START",
              "guide_end_marker": "GUIDE_CHEST_END", "guide_rest_start": rnd(cs), "guide_rest_end": rnd(ce),
              "guide_length_m": round((ce - cs).length, 4),
              "note": "v04: the sternum lies inside the OperationAbdomen_v04 opening; the chin line of the lying patient is rest z ~1.12"},
    "great_vessels_abdominal_rest": {k: {"x": v["x"], "y": v["y"], "radius": v["r"], "z_head": v["z"][0], "z_pubic": v["z"][1]}
                                     for k, v in GV.items()},
    "stencil_zone": dict(L3D["stencil_zone"], v04_rule=f"v03 zone + every front-facing trunk face within {ZONE_MARGIN} m of the v04 opening "
                                                       "outline (INC_ABDOMEN frame)",
                         faces={"zone_Buddy_Skin": mat_after[0], "Buddy_Skin_Nose": mat_after.get(1, 0), "Patient_Skin_Closed": mat_after[2],
                                "added_in_v04": added, "faces_under_v04_opening_plus_margin": candidates}),
    "table_rest_transform_rest_to_table_blender": [rnd(r, 6) for r in T],
    "table_rest": {},
})
layout.pop("v02_to_v03_moves_rest_m", None)
layout["unity_integration"] = [s.replace("v03", "v04") for s in L3D["unity_integration"]] + [
    "7. v04: patient prefab -> SAUSAGE_BUDDY_PATIENT_v04.fbx (same rig/avatar/clips; markers moved); opening -> OperationAbdomen_v04.fbx; "
    "organs/ribcage -> Organs_v04 FBX set; colliders per G38_collisions_manifest_v04.json."]
for name, ob in markers.items():
    layout["table_rest"][name] = table_entry(ob.matrix_world)
for k, v in layout["great_vessels_abdominal_rest"].items():
    for key, zz in (("head", v["z_head"]), ("pubic", v["z_pubic"])):
        e = tpt((v["x"], v["y"], zz))
        v["table_blender_" + key] = e["table_blender"]
        v["table_unity_" + key] = e["table_unity"]

# ------------------------------------------------------------------------------------------- 6. checks and output
after = {n: geo_hash(bpy.data.objects[n]) for n in ("Body", "Face", "Shorts")}
after["bones"] = bone_hash(rig)
assert after == before, "geometry / weights / UVs / bones changed"
report = {"source": bpy.data.filepath, "unchanged_hashes_verts_weights_uvs_bones": before,
          "body_material_faces_v03": {me.materials[i].name: c for i, c in mat_before.items()},
          "body_material_faces_v04": {me.materials[i].name: c for i, c in mat_after.items()}, "zone_faces_added": added, "zone_faces_under_v04_opening_plus_margin": candidates,
          "markers": {n: {"rest_position": rnd(o.matrix_world.translation), "parent_bone": o.parent_bone} for n, o in markers.items()},
          "bones": len(rig.data.bones)}
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out_blend), copy=True)
bpy.ops.object.select_all(action="DESELECT")
for ob in [rig, body, bpy.data.objects["Face"], bpy.data.objects["Shorts"]] + list(markers.values()):
    ob.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(out_fbx), use_selection=True, object_types={"MESH", "ARMATURE", "EMPTY"}, add_leaf_bones=False,
                         use_armature_deform_only=False, bake_anim=False, axis_forward="-Z", axis_up="Y",
                         apply_unit_scale=True, use_mesh_modifiers=False)
out_layout.write_text(json.dumps(layout, indent=1), encoding="utf-8")
out_report.write_text(json.dumps(report, indent=1), encoding="utf-8")
print("[PATIENT_v04]", json.dumps({k: v for k, v in report.items() if k != "markers"}))
