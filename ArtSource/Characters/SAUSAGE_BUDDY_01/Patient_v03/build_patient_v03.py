"""Sausage Buddy PATIENT v03: the v02 patient with a closed back and the v03 organ sockets (chest + lowered liver/kidneys).

Fedya 2026-10-18: "when the patient is flipped onto his belly you see a through-hole and the organs from behind".
Cause (not a mesh hole - the v02 Body is closed, 0 boundary edges): in Unity every Body material whose name starts with
"Buddy_Skin" gets the stencil-tested skin shader, and ABDOMEN_MASK (Cull Off, ZWrite Off, drawn first at queue 1999)
writes the stencil wherever the opening projects on screen - also when it is seen from behind through the body. The
back skin inside that projection was then discarded.
Fix in the mesh: the Body gets a third material slot. Only the FRONT TORSO ZONE (belly + chest front, the only skin that
an opening can ever replace) keeps "Buddy_Skin"; every other face (back, flanks, arms, legs, head, neck) moves to the
new slot "Patient_Skin_Closed", which the Unity code never stencils. Vertices, weights, UVs, bones and the rig are
byte-identical to v02 (hash-checked); only polygon material indices and the material list change.
Recommended belt-and-braces shader fix (Unity, not done here): Cull Back on the ABDOMEN_MASK passes (its normals face out
of the belly), so the mask never writes the stencil when seen from inside / behind.

Run (v02 file is only read, never written):
  blender -b Patient_v02/SAUSAGE_BUDDY_PATIENT_v02.blend --python Patient_v03/build_patient_v03.py
Needs Organs_v03/organs_v03_build.json (run Organs_v03/Scripts/build_organs_v03.py first).
Writes next to this script (refuses to overwrite):
  SAUSAGE_BUDDY_PATIENT_v03.blend / .fbx, ORGANS_LAYOUT_v03.json, build_report_SAUSAGE_BUDDY_PATIENT_v03.json
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
ORG = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03"
sys.path.insert(0, str(ORG / "Scripts"))
import organs_layout_v03 as LAY  # noqa: E402
import organs_v03_lib as L       # noqa: E402

STEM = "SAUSAGE_BUDDY_PATIENT_v03"
TABLE_REST = REPO / "ArtSource/Props/TABLE-ASTRA-001/v02/Patient_TableRest_v01.blend"
P = "mixamorig:"
RIG = "Buddy_Rig_Mixamo65"
C_B2U = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))     # Unity prefab-local <- Blender table-local (points)
CLOSED = "Patient_Skin_Closed"
ZONE = {"z": (0.785, 1.180), "max_abs_x": 0.160, "max_normal_y": -0.12,
        "bones": {P + "Hips", P + "Spine", P + "Spine1", P + "Spine2"}}

scene = bpy.context.scene
rig = bpy.data.objects[RIG]
body = bpy.data.objects["Body"]
assert "v02" in Path(bpy.data.filepath).stem, "run on SAUSAGE_BUDDY_PATIENT_v02.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUTDIR = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else HERE          # --out <dir>: test build elsewhere
ORGJSON = Path(ARGS[ARGS.index("--organs-json") + 1]) if "--organs-json" in ARGS else ORG / "organs_v03_build.json"
out_blend, out_fbx = OUTDIR / f"{STEM}.blend", OUTDIR / f"{STEM}.fbx"
out_layout, out_report = OUTDIR / "ORGANS_LAYOUT_v03.json", OUTDIR / f"build_report_{STEM}.json"
for p in (out_blend, out_fbx, out_layout, out_report):
    assert not p.exists(), f"refusing to overwrite {p}"
ORGB = json.loads(ORGJSON.read_text(encoding="utf-8"))


def mesh_hash(ob):
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


before = {n: mesh_hash(bpy.data.objects[n]) for n in ("Body", "Face", "Shorts")}
before["bones"] = bone_hash(rig)
if rig.animation_data:
    rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()

# ------------------------------------------------------------------------------------------- 1. closed back (material split)
me = body.data
skin = me.materials[0]
assert skin.name == "Buddy_Skin", skin.name
closed = skin.copy()
closed.name = CLOSED
closed["note"] = "same look as Buddy_Skin; NEVER give this slot the stencil-tested skin shader"
me.materials.append(closed)
closed_idx = len(me.materials) - 1
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
# trunk island = the biggest connected piece (head, nose, ears, hands are separate islands)
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
trunk = max(islands, key=len)
gnames = {g.index: g.name for g in body.vertex_groups}


def dominant(vi):
    gs = sorted(me.vertices[vi].groups, key=lambda g: -g.weight)
    return gnames[gs[0].group] if gs else None


zone_faces = 0
for f in bm.faces:
    if f.material_index != 0:
        continue
    c = f.calc_center_median()
    in_zone = (all(v.index in trunk for v in f.verts) and ZONE["z"][0] <= c.z <= ZONE["z"][1] and abs(c.x) <= ZONE["max_abs_x"]
               and f.normal.y <= ZONE["max_normal_y"] and all(dominant(v.index) in ZONE["bones"] for v in f.verts))
    if in_zone:
        zone_faces += 1
    else:
        f.material_index = closed_idx
bm.to_mesh(me)
bm.free()
me.update()
mat_use = Counter(p.material_index for p in me.polygons)

# ------------------------------------------------------------------------------------------- 2. markers and sockets
for n in ("INC_KIDNEY_L", "INC_KIDNEY_R", "INC_LIVER", "INC_ABDOMEN", "GUIDE_BELLY_START", "GUIDE_BELLY_END"):
    bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
dg = bpy.context.evaluated_depsgraph_get()
bvh_all = BVHTree.FromObject(body, dg)
# trunk-only BVH: the chest skin lies under the head capsule's chin, which is a separate island
tv = [body.matrix_world @ me.vertices[i].co for i in sorted(trunk)]
tidx = {i: k for k, i in enumerate(sorted(trunk))}
tp = [[tidx[i] for i in p.vertices] for p in me.polygons if p.vertices[0] in trunk]
bvh_trunk = BVHTree.FromPolygons(tv, tp)
spine = rig.data.bones[P + "Spine"]


def skin_front(x, z, bvh=bvh_trunk):
    hit, normal, _, _ = bvh.ray_cast(Vector((x, -0.5, z)), Vector((0, 1, 0)))
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
# organ sockets (= the organ mesh frames of Organs_v03; organ pivot at the origin)
for sname, sd in ORGB["sockets"].items():
    mw = Matrix.Translation(sd["rest_position"]) @ Matrix((sd["rest_x_axis"], sd["rest_y_axis"], sd["rest_z_axis"])).transposed().to_4x4()
    markers[sname] = add_marker(sname, mw, 0.03, "ARROWS")
# INC_* pull frames at the organ centres (v02 convention: +Z skin normal / pull, +Y long axis, +X patient left)
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
# openings and guides on the skin
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
    ob = ORGB["objects"][kname]
    # hilum: the medial edge of the bean at mid height, slightly anterior (socket frame)
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
    rc = od["real_cm"]
    organs[oname] = {
        "socket": od["socket"], "incision_marker": inc, "pivot": "organ centre = socket origin (mesh authored in socket space)",
        "rest_socket": ORGB["sockets"][od["socket"]],
        "local_bounds_min_m": ob["local_bounds_min"], "local_bounds_max_m": ob["local_bounds_max"],
        "size_m_xyz_local": ob["size_m_xyz"], "largest_dimension_m": ob["largest_dimension_m"], "tris": ob["tris"],
        "real_size_cm_long_wide_thick": list(rc), "materials": ob["materials"], "source": od["source"],
        "fbx_alone": f"ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03/FBX/{oname}_v03.fbx",
        "pull": {"direction": f"{inc} +Z", "depth_below_skin_m": inc_info[inc]["depth_below_skin_m"],
                 "exit_distance_m": round(inc_info[inc]["depth_below_skin_m"] + 0.5 * ob["size_m_xyz"][2] + 0.03, 3)},
    }
    if oname in cords_out:
        organs[oname]["hilum_rest"] = cords_out[oname]["hilum_rest"]
        organs[oname]["cords"] = cords_out[oname]["cords"]
gs, ge = markers["GUIDE_BELLY_START"].matrix_world.translation, markers["GUIDE_BELLY_END"].matrix_world.translation
cs, ce = markers["GUIDE_CHEST_START"].matrix_world.translation, markers["GUIDE_CHEST_END"].matrix_world.translation
abd_inv = abd.inverted()
chest_mw = markers["INC_CHEST"].matrix_world
layout = {
    "version": "ORGANS_LAYOUT_v03", "date": "2026-10-18", "patient": f"{STEM}.fbx",
    "frames": {
        "rest": "patient model space, Blender metres, Z up, faces -Y, patient left = +X (all markers/sockets bone-parented "
                "to mixamorig:Spine; Hips/Spine/Spine1/Spine2 are rigid together in TABLE_REST)",
        "socket_local": "organ frame: +X patient left, +Y head / organ long axis, +Z anterior (organ front). Organ meshes "
                        "are authored in it: an organ placed at its socket with identity local transform sits in the body.",
        "incision_marker_local": "INC_*: +Z skin normal = pull direction, +Y long axis toward the head, +X patient left (v02 convention)",
        "unity_local": "after FBX import every marker/socket-local frame has X negated (Unity +X = patient RIGHT); *_unity "
                       "values already have x negated and rotations mirrored (xyzw)",
        "table_blender": "TABLE-ASTRA-001 v02 table-local Blender in the TABLE_REST pose (head end -Y, patient left -X)",
        "table_unity": "OperatingTableAstra_v02 prefab-local Unity = (-x, z, -y) of table_blender"},
    "size_rule": {"size_factor_vs_real": LAY.SIZE_FACTOR,
                  "note": "widths/depths x0.9 of a real adult; Buddy's trunk is short (x0.67 in height), so the lungs are "
                          "~15.5 cm tall instead of 25*0.9; every organ is 1:1 world scale, scale (1,1,1) - the same size in "
                          "the body, in the hand and on the tray"},
    "v02_to_v03_moves_rest_m": {"liver_centre": [[-0.030, -0.052, 1.032], ORGB["sockets"]["SOCKET_LIVER"]["rest_position"]],
                                "kidney_L_centre": [[0.080, 0.010, 0.975], ORGB["sockets"]["SOCKET_KIDNEY_L"]["rest_position"]],
                                "kidney_R_centre": [[-0.080, 0.010, 0.955], ORGB["sockets"]["SOCKET_KIDNEY_R"]["rest_position"]]},
    "organs": organs,
    "incision_markers": {n: dict(inc_info[n], rest_position=rnd(markers[n].matrix_world.translation),
                                 rest_z_axis=rnd(markers[n].matrix_world.col[2].xyz)) for n in INC},
    "ribcage": {k: v for k, v in ORGB["objects"].items() if k.startswith(("RIB", "STERNUM", "SPINE"))},
    "ribcage_notes": {
        "hierarchy": "SOCKET_THORAX > RIBCAGE > RIBCAGE_HALF_L|R (hinge pivot) > RIB_<L|R>_01..09, STERNUM_<L|R>; SPINE_THORACIC under RIBCAGE",
        "rib_pivot": "each rib's origin = its vertebral head (costovertebral joint); axes = SOCKET_THORAX axes",
        "sternotomy": "the sternum is split on the midline into STERNUM_L / STERNUM_R (mallet + osteotome cut line = GUIDE_CHEST_START "
                      "-> GUIDE_CHEST_END on the skin); the halves' midline faces use MAT_Bone_Cut_v03",
        "open": f"rotate RIBCAGE_HALF_L about its local +Y by +{LAY.RIBCAGE_HINGE['open_deg']} deg and RIBCAGE_HALF_R by "
                f"-{LAY.RIBCAGE_HINGE['open_deg']} deg (Blender); in Unity (mirrored X) the signs flip: L -angle, R +angle about local Y",
        "ribs_1_7": "true ribs (bone + costal cartilage to the sternum)", "ribs_8_9": "false ribs (cartilage joins the rib above = costal arch)"},
    "chest_vessels": {k: v for k, v in ORGB["objects"].items() if k.startswith(("VESSELS", "AIRWAY", "DIAPHRAGM"))},
    "connections": ORGB.get("connections", {}),
    "heart_vessel_stubs_note": "ORGAN_HEART carries short cut stubs (aorta, pulmonary trunk, SVC, IVC, 4 pulmonary veins) with a dark "
                               "lumen; each VESSELS_* tube starts 4 mm inside its stub. To 'cut' the heart free hide/shorten the "
                               "VESSELS_* near their snip points; the stubs stay on the removed heart.",
    "opening_abdomen": {"marker": "INC_ABDOMEN", "shape": "asymmetric lens: |x| = W (1 - |t|^p)^q, t = y / half_length (top or bottom)",
                        **{k: v for k, v in LAY.OPENING.items()}, "rest": {"centre_on_skin": rnd(abd.translation),
                                                                          "z_axis_skin_normal": rnd(abd.col[2].xyz)},
                        "mesh": "ArtSource/Props/TABLE-ASTRA-001/v03/OperationAbdomen_v03.fbx (origin and axes = INC_ABDOMEN)"},
    "guide_belly": {"start_marker": "GUIDE_BELLY_START", "end_marker": "GUIDE_BELLY_END", "rest_start": rnd(gs), "rest_end": rnd(ge),
                    "length_m": round((ge - gs).length, 4), "abdomen_local_start": rnd(abd_inv @ gs), "abdomen_local_end": rnd(abd_inv @ ge)},
    "chest": {"marker": "INC_CHEST", "rest_centre_on_skin": rnd(chest_mw.translation), "guide_start_marker": "GUIDE_CHEST_START",
              "guide_end_marker": "GUIDE_CHEST_END", "guide_rest_start": rnd(cs), "guide_rest_end": rnd(ce),
              "guide_length_m": round((ce - cs).length, 4),
              "note": "future sternotomy: no chest opening mesh yet. The head capsule's chin overlaps the upper chest skin; see "
                      "the TABLE_REST review render for how much of the chest the operation camera sees."},
    "great_vessels_abdominal_rest": {k: {"x": v["x"], "y": v["y"], "radius": v["r"], "z_head": v["z"][0], "z_pubic": v["z"][1]}
                                     for k, v in GV.items()},
    "stencil_zone": {"material_kept_for_stencil": "Buddy_Skin (front torso zone only)", "material_never_stencilled": CLOSED,
                     "zone_rule": {"rest_z": list(ZONE["z"]), "max_abs_x": ZONE["max_abs_x"], "face_normal_y_at_most": ZONE["max_normal_y"],
                                   "all_vertices_dominated_by": sorted(ZONE["bones"]), "island": "trunk only"},
                     "faces": {"zone_Buddy_Skin": mat_use[0], "Buddy_Skin_Nose": mat_use.get(1, 0), CLOSED: mat_use[closed_idx]}},
    "unity_integration": [
        "1. Patient: point the patient prefab at SAUSAGE_BUDDY_PATIENT_v03.fbx (same 65-bone rig, avatar and clips as v02). The Body "
        "has THREE material slots now: [0] Buddy_Skin (front torso zone only), [1] Buddy_Skin_Nose, [2] Patient_Skin_Closed. Give slot 2 "
        "a copy of the skin material whose asset name does NOT start with 'Buddy_Skin' (e.g. 'Patient_Skin_Closed'): "
        "OperationOpeningV02 stencils every slot whose material name starts with 'Buddy_Skin', so only the front zone is cut "
        "and the back, arms and head can never be culled.",
        "2. Recommended shader fix as well: OperationMaskStencil_v02 'Cull Off' -> 'Cull Back' in its passes (ABDOMEN_MASK normals "
        "face out of the belly, checked in OperationAbdomen_v03_validation.json), so the mask writes no stencil when the "
        "opening is seen from inside/behind (patient turned over, camera below the table).",
        "3. Anchors: INC_LIVER, INC_KIDNEY_L, INC_KIDNEY_R moved (organ centres, see organs.*.rest_socket); new INC_HEART, INC_LUNG_L, "
        "INC_LUNG_R, INC_CHEST, GUIDE_CHEST_START/END and SOCKET_* (organ frames). All bone-parented to mixamorig:Spine.",
        "4. Organs: every ORGAN_* mesh is authored in its SOCKET frame at 1:1 world scale. In the body: a child of SOCKET_<organ> "
        "with localPosition 0, localRotation identity, localScale 1, using the mesh (MeshFilter.sharedMesh) - the same "
        "recipe OperationOpeningV02 uses for ABDOMEN_* under INC_ABDOMEN. On the tray / in hand use the same mesh at scale 1 "
        "(FBX/ORGAN_*_v03.fbx): sizes in organs.*.size_m_xyz_local, largest_dimension_m. Do not rescale organs any more "
        "(drop worldModelSize / organItemScale fitting for these meshes, or set them to the largest dimension).",
        "5. Opening: OperationAbdomen_v03.fbx under INC_ABDOMEN (v03 marker moved to rest z 0.950). abdomenCutLength = guide_belly.length_m; "
        "abdomenHalfSize = (half_width, (half_length_top + half_length_bottom)/2) or use the asymmetric values; kidney cords from "
        "organs.ORGAN_KIDNEY_*.cords (same format as v02, marker-local Unity values).",
        "6. Chest (future): RIBCAGE_v03.fbx and CHEST_VESSELS_v03.fbx under SOCKET_THORAX (identity). The sternum splits into "
        "STERNUM_L/R along GUIDE_CHEST_START->END; open by rotating RIBCAGE_HALF_L/R about local Y (see ribcage_notes). The "
        "heart's VESSELS_* are separate meshes; hide them at their snip points to free the heart.",
    ],
    "table_rest_transform_rest_to_table_blender": [rnd(r, 6) for r in T],
    "table_rest": {},
}
for name, ob in markers.items():
    layout["table_rest"][name] = table_entry(ob.matrix_world)
for k, v in layout["great_vessels_abdominal_rest"].items():
    for key, zz in (("head", v["z_head"]), ("pubic", v["z_pubic"])):
        e = tpt((v["x"], v["y"], zz))
        v["table_blender_" + key] = e["table_blender"]
        v["table_unity_" + key] = e["table_unity"]

# ------------------------------------------------------------------------------------------- 6. checks and output
after = {n: mesh_hash(bpy.data.objects[n]) for n in ("Body", "Face", "Shorts")}
after["bones"] = bone_hash(rig)
assert after == before, f"geometry / weights / UVs / bones changed: {before} vs {after}"
bmc = bmesh.new()
bmc.from_mesh(me)
boundary = sum(1 for e in bmc.edges if e.is_boundary)
bmc.free()
report = {"source": bpy.data.filepath, "unchanged_hashes_verts_weights_uvs_bones": before, "body_boundary_edges": boundary,
          "body_materials": [m.name for m in me.materials], "material_face_counts": {me.materials[i].name: c for i, c in mat_use.items()},
          "markers": {n: {"rest_position": rnd(o.matrix_world.translation), "parent_bone": o.parent_bone} for n, o in markers.items()},
          "bones": len(rig.data.bones), "actions": len(bpy.data.actions)}
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out_blend), copy=False)
bpy.ops.object.select_all(action="DESELECT")
for ob in [rig, body, bpy.data.objects["Face"], bpy.data.objects["Shorts"]] + list(markers.values()):
    ob.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(out_fbx), use_selection=True, object_types={"MESH", "ARMATURE", "EMPTY"}, add_leaf_bones=False,
                         use_armature_deform_only=False, bake_anim=False, axis_forward="-Z", axis_up="Y",
                         apply_unit_scale=True, use_mesh_modifiers=False)
out_layout.write_text(json.dumps(layout, indent=1), encoding="utf-8")
out_report.write_text(json.dumps(report, indent=1), encoding="utf-8")
print("[PATIENT_v03]", json.dumps(report))
