"""ORGANS v04: the accepted v03d organ block (G38: 4 rib pairs v03c + 96 UCX colliders v03d) moved down rigidly.

blender -b ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03/Organs_v03d.blend --python build_organs_v04.py [-- --dry <dir>]
The v03d file is only read. Every SOCKET_* under the root is translated by organs_layout_v04.SHIFT; everything else
(organs, ribs, sternum halves, spine, RIBCAGE_HALF_L/R hinges, BREAK_* empties, UCX_* colliders, vessels, airway,
diaphragm) is parented below the sockets and follows, so no relative transform, mesh, material or custom property
changes. Checks: world matrices == SHIFT @ v03d (max error), organ<->UCX minimum distance before == after (closed and
opened 35 deg), everything inside the patient body in rest and TABLE_REST (UCX body contacts reported as info, as in v03d).
Writes (refuses to overwrite) into Organs_v04/:
  Organs_v04.blend, Organs_InBody_v04.fbx, FBX/ORGAN_*_v04.fbx, FBX/RIBCAGE_v04.fbx (with UCX + BREAK),
  FBX/CHEST_VESSELS_v04.fbx, organs_v04_build.json, G38_collisions_manifest_v04.json
"""
import copy
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import organs_layout_v04 as LAY  # noqa: E402

REPO = Path(r"C:/Dev/Game")
V03 = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DRY = Path(ARGS[ARGS.index("--dry") + 1]) if "--dry" in ARGS else None
OUT = DRY or HERE.parent
FBX_DIR = OUT / "FBX"
OUT_BLEND, OUT_INBODY, OUT_JSON = OUT / "Organs_v04.blend", OUT / "Organs_InBody_v04.fbx", OUT / "organs_v04_build.json"
OUT_MANIFEST = OUT / "G38_collisions_manifest_v04.json"
MANIFEST_V03D = V03 / "G38_collisions_manifest_v03d.json"
BUILD_V03 = V03 / "organs_v03_build.json"
PATIENT_V03 = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v03/SAUSAGE_BUDDY_PATIENT_v03.blend"
TABLE_REST = REPO / "ArtSource/Props/TABLE-ASTRA-001/v02/Patient_TableRest_v01.blend"
SHIFT = Matrix.Translation(LAY.SHIFT)
sc = bpy.context.scene
assert Path(bpy.data.filepath).name == "Organs_v03d.blend", "run on Organs_v03d.blend"
REPORT = {"version": "ORGANS_v04", "date": "2026-10-18", "source": bpy.data.filepath, "shift_rest_m": list(LAY.SHIFT)}


def log(*a):
    print("[ORGANS_v04]", *a, flush=True)


def rnd(v, n=5):
    return [round(float(c), n) for c in v]


# ------------------------------------------------------------------------------------------------ helpers
def world_bvh(ob):
    me = ob.data
    mw = ob.matrix_world
    return BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [p.vertices for p in me.polygons]), [mw @ v.co for v in me.vertices]


ORGANISH = ("ORGAN_", "VESSELS_", "AIRWAY_", "DIAPHRAGM")


def organ_ucx_distance():
    """Minimum distance between any UCX collider and any organ / vessel / airway / diaphragm surface (vertex-to-surface
    both ways + surface overlap). Returns (min_mm, ucx, organ)."""
    bpy.context.view_layer.update()
    ucx = [o for o in bpy.data.objects if o.name.startswith("UCX_")]
    org = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(ORGANISH)]
    ob_data = {o.name: world_bvh(o) for o in ucx + org}
    best = (1e9, None, None)
    for u in ucx:
        bu, vu = ob_data[u.name]
        for g in org:
            bg, vg = ob_data[g.name]
            if bu.overlap(bg):
                return (0.0, u.name, g.name)
            d = min(min(bg.find_nearest(p)[3] for p in vu), min(bu.find_nearest(p)[3] for p in vg[::3]))
            if d < best[0]:
                best = (d, u.name, g.name)
    return (round(best[0] * 1000, 4), best[1], best[2])


def set_open(deg):
    for name, s in (("RIBCAGE_HALF_L", 1), ("RIBCAGE_HALF_R", -1)):
        h = bpy.data.objects[name]
        if "_mb0" not in h:
            h["_mb0"] = [list(r) for r in h.matrix_basis]
        h.matrix_basis = Matrix(h["_mb0"]) @ Matrix.Rotation(math.radians(s * deg), 4, "Y")
    bpy.context.view_layer.update()


def clear_open():
    for name in ("RIBCAGE_HALF_L", "RIBCAGE_HALF_R"):
        h = bpy.data.objects[name]
        h.matrix_basis = Matrix(h["_mb0"])
        del h["_mb0"]
    bpy.context.view_layer.update()


def load_bodies():
    """Patient v03 body in rest, and the TABLE_REST body mapped back to rest through the Spine transform."""
    out = {}
    with bpy.data.libraries.load(str(PATIENT_V03), link=False) as (src, dst):
        dst.objects = ["Body", "Buddy_Rig_Mixamo65"]
    coll = bpy.data.collections.new("_bodies")
    sc.collection.children.link(coll)
    for o in dst.objects:
        coll.objects.link(o)
    rig = next(o for o in dst.objects if o.type == "ARMATURE")
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    body = next(o for o in dst.objects if o.type == "MESH")
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    me.transform(body.matrix_world)
    out["rest"] = me
    for o in dst.objects:
        bpy.data.objects.remove(o, do_unlink=True)
    with bpy.data.libraries.load(str(TABLE_REST), link=False) as (src, dst):
        dst.objects = ["Body", "Buddy_Rig_Mixamo65"]
    for o in dst.objects:
        coll.objects.link(o)
    rig = next(o for o in dst.objects if o.type == "ARMATURE")
    sc.frame_set(1)
    bpy.context.view_layer.update()
    pb = rig.pose.bones["mixamorig:Spine"]
    T = rig.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    body = next(o for o in dst.objects if o.type == "MESH")
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    me.transform(T.inverted() @ body.matrix_world)
    out["table_rest"] = me
    for o in dst.objects:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(coll)
    for a in [a for a in bpy.data.actions if a.users == 0 and a.name.startswith("Patient_TableRest")]:
        bpy.data.actions.remove(a)
    REPORT["table_rest_spine_matrix"] = [rnd(r, 6) for r in T]
    return out


def islands(me, min_verts=400):
    bm = bmesh.new()
    bm.from_mesh(me)
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
        if len(comp) < min_verts:
            continue
        faces = {f for x in comp for f in x.link_faces}
        idx = {x.index: k for k, x in enumerate(comp)}
        out.append(BVHTree.FromPolygons([x.co.copy() for x in comp], [[idx[x.index] for x in f.verts] for f in faces]))
    bm.free()
    return out


def inside(bvh, p, ray=Vector((0.0123, 0.0071, 1.0)).normalized()):
    hits, o = 0, Vector(p)
    for _ in range(64):
        h = bvh.ray_cast(o + ray * 1e-5, ray)
        if h[0] is None:
            break
        hits += 1
        o = h[0]
    return hits % 2 == 1


def body_check(objs, bodies):
    res = {}
    for pose, me in bodies.items():
        isl = islands(me)
        whole = BVHTree.FromPolygons([v.co for v in me.vertices], [p.vertices for p in me.polygons])
        per = {}
        for ob in objs:
            mw = ob.matrix_world
            pts = [mw @ v.co for v in ob.data.vertices]
            out = sum(1 for p in pts if not any(inside(i, p) for i in isl))
            dmin = min(whole.find_nearest(p)[3] for p in pts)
            per[ob.name] = {"verts_outside_body": out, "min_vertex_to_skin_mm": round(dmin * 1000, 2)}
        res[pose] = per
    return res


# ------------------------------------------------------------------------------------------------ main
def main():
    if DRY is None:
        for p in (OUT_BLEND, OUT_INBODY, OUT_JSON, OUT_MANIFEST):
            assert not p.exists(), f"refusing to overwrite {p}"
    else:
        DRY.mkdir(parents=True, exist_ok=True)
    root = bpy.data.objects["ORGANS_v03_ROOT"]
    assert root.matrix_world == Matrix.Identity(4)
    movers = [o for o in bpy.data.objects if o.name != "REF_PatientBody_v02_rest" and o.type in ("MESH", "EMPTY")]
    before = {o.name: o.matrix_world.copy() for o in movers}
    # 1. organ <-> collider distance before
    d_closed_0 = organ_ucx_distance()
    set_open(35)
    d_open_0 = organ_ucx_distance()
    clear_open()
    log("v03d organ-UCX min mm closed", d_closed_0, "open35", d_open_0)
    # 2. rigid shift: only the sockets (the root's children) move
    sockets = [o for o in root.children]
    assert all(o.name.startswith("SOCKET_") for o in sockets) and len(sockets) == 7, [o.name for o in sockets]
    for s in sockets:
        s.matrix_basis = SHIFT @ s.matrix_basis
    root.name = "ORGANS_v04_ROOT"
    for c in bpy.data.collections:
        if c.name == "ORGANS_v03":
            c.name = "ORGANS_v04"
        elif c.name == "COL_Collision_v03d":
            c.name = "COL_Collision_v04"
    bpy.context.view_layer.update()
    err = max(max(abs(a - b) for ra, rb in zip(o.matrix_world, SHIFT @ before[n]) for a, b in zip(ra, rb))
              for n, o in ((n, bpy.data.objects[n if n != "ORGANS_v03_ROOT" else "ORGANS_v04_ROOT"]) for n in before)
              if o.name != "ORGANS_v04_ROOT")
    log("max |world - SHIFT @ v03d| =", err)
    assert err < 1e-6
    # 3. organ <-> collider distance after (must be identical)
    d_closed_1 = organ_ucx_distance()
    set_open(35)
    d_open_1 = organ_ucx_distance()
    clear_open()
    log("v04 organ-UCX min mm closed", d_closed_1, "open35", d_open_1)
    REPORT["rigid_shift_check"] = {"max_world_matrix_error": err, "objects_moved": len(movers) - 1,
                                   "organ_ucx_min_mm_v03d": {"closed": d_closed_0, "open35": d_open_0},
                                   "organ_ucx_min_mm_v04": {"closed": d_closed_1, "open35": d_open_1},
                                   "identical": abs(d_closed_0[0] - d_closed_1[0]) < 1e-3 and abs(d_open_0[0] - d_open_1[0]) < 1e-3,
                                   "g38_reported_v03d_mm": {"closed": 4.899128, "open35": 3.149244},
                                   "method": "vertex-to-surface both ways + triangle overlap (G38 used exact triangle distance; "
                                             "its values are the reference, this measure must not change under the shift)"}
    # 4. inside the patient body (rest + TABLE_REST); UCX body/neck contacts are information (accepted in v03d)
    bodies = load_bodies()
    render = [o for o in bpy.data.objects if o.type == "MESH" and o.name.split("_")[0] in ("ORGAN", "RIB", "STERNUM", "SPINE", "VESSELS",
                                                                                          "AIRWAY", "DIAPHRAGM")]
    ucx = [o for o in bpy.data.objects if o.name.startswith("UCX_")]
    bc = body_check(render, bodies)
    REPORT["inside_body_render_meshes"] = bc
    log("render meshes outside body:", {p: {k: v["verts_outside_body"] for k, v in d.items() if v["verts_outside_body"]} for p, d in bc.items()})
    bu = body_check(ucx, bodies)
    REPORT["ucx_body_info"] = {p: {"colliders_with_vertices_outside_body": sum(1 for v in d.values() if v["verts_outside_body"]),
                                   "per_collider": d} for p, d in bu.items()}
    for me in bodies.values():
        bpy.data.meshes.remove(me)
    # key heights
    def zr(name, mats=None):
        o = bpy.data.objects[name]
        vs = [o.matrix_world @ o.data.vertices[i].co for p in o.data.polygons if mats is None or p.material_index in mats for i in p.vertices]
        return round(min(v.z for v in vs), 4), round(max(v.z for v in vs), 4)
    REPORT["rest_z_ranges_v04"] = {n: zr(n) for n in ("ORGAN_HEART", "ORGAN_LUNG_L", "ORGAN_LUNG_R", "ORGAN_LIVER", "ORGAN_KIDNEY_L",
                                                     "ORGAN_KIDNEY_R", "STERNUM_L", "RIB_L_01", "RIB_L_04", "DIAPHRAGM", "VESSELS_AORTA")}
    REPORT["rest_z_ranges_v04"]["ORGAN_HEART_body_only"] = zr("ORGAN_HEART", {0})
    REPORT["rest_z_ranges_v04"]["ORGAN_KIDNEY_L_bean"] = zr("ORGAN_KIDNEY_L", {0})
    REPORT["rest_z_ranges_v04"]["ORGAN_KIDNEY_R_bean"] = zr("ORGAN_KIDNEY_R", {0})
    log("z ranges", REPORT["rest_z_ranges_v04"])
    describe(root)
    manifest(ucx, bu)
    if DRY is not None:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND), copy=True)
        OUT_JSON.write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
        return
    export(root)


def describe(root):
    bpy.context.view_layer.update()
    v3 = json.loads(BUILD_V03.read_text(encoding="utf-8"))
    REPORT["sockets"] = {}
    for s in root.children:
        mw = s.matrix_world
        REPORT["sockets"][s.name] = {"rest_position": rnd(mw.translation), "rest_rotation_wxyz": rnd(mw.to_quaternion()),
                                     "rest_x_axis": rnd(mw.col[0][:3], 4), "rest_y_axis": rnd(mw.col[1][:3], 4),
                                     "rest_z_axis": rnd(mw.col[2][:3], 4)}
    objs = {}
    for ob in bpy.data.objects:
        if ob.name.startswith(("REF_", "ORGANS_v04_ROOT", "SOCKET_")) or ob.type not in ("MESH", "EMPTY"):
            continue
        sock = ob
        while sock.parent is not None and not sock.parent.name.startswith("SOCKET_"):
            sock = sock.parent
        socket = sock.parent
        rel = socket.matrix_world.inverted() @ ob.matrix_world
        q = rel.to_quaternion()
        d = {"socket": socket.name, "parent": ob.parent.name if ob.parent else None,
             "socket_local_blender": {"position": rnd(rel.translation), "rotation_wxyz": rnd(q)},
             "socket_local_unity": {"position": [round(-rel.translation.x, 5), round(rel.translation.y, 5), round(rel.translation.z, 5)],
                                    "rotation_xyzw": [round(q.x, 5), round(-q.y, 5), round(-q.z, 5), round(q.w, 5)]},
             "rest_position": rnd(ob.matrix_world.translation), "scale": rnd(ob.matrix_world.to_scale(), 4)}
        if ob.type == "MESH" and not ob.name.startswith("UCX_"):
            co = [v.co for v in ob.data.vertices]
            mn = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
            mx = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
            d.update({"tris": sum(len(p.vertices) - 2 for p in ob.data.polygons), "local_bounds_min": rnd(mn, 4),
                      "local_bounds_max": rnd(mx, 4), "size_m_xyz": rnd(mx - mn, 4), "largest_dimension_m": round(max(mx - mn), 4),
                      "materials": [{"name": m.name, "base_color_srgb": list(m.get("unity_base_color_srgb", [])),
                                     "smoothness": m.get("unity_smoothness")} for m in ob.data.materials]})
            for k in ("mass_kg", "mass_hint"):
                if k in ob:
                    d[k] = ob[k]
        if ob.name.startswith("UCX_"):
            d = {"target": ob.parent.name, "vertices": len(ob.data.vertices), "tris": sum(len(p.vertices) - 2 for p in ob.data.polygons)}
        objs[ob.name] = d
    REPORT["objects"] = objs
    # connections (vessel ends, hila) from the v03 build, moved by the same shift
    def shift_tree(x):
        if isinstance(x, dict):
            return {k: shift_tree(v) for k, v in x.items()}
        if isinstance(x, list) and len(x) == 3 and all(isinstance(c, (int, float)) for c in x):
            return [round(a + b, 5) for a, b in zip(x, LAY.SHIFT)]
        return x
    REPORT["connections"] = shift_tree(v3.get("connections", {}))


def manifest(ucx, body_info):
    m = json.loads(MANIFEST_V03D.read_text(encoding="utf-8"))
    m4 = copy.deepcopy(m)
    m4["schema"] = "G38_collision_manifest_v04/1 (v03d moved rigidly by Claude)"
    m4["revision"] = "v04"
    m4["derived_from"] = {"manifest": str(MANIFEST_V03D), "rigid_shift_rest_m": list(LAY.SHIFT),
                          "note": "every *_rest_world* value moved by the shift; target-local data, fits and organ clearances are "
                                  "unchanged by a rigid move (re-measured: see rigid_shift_check); body/head contacts re-measured "
                                  "against the unmoved patient body (body_v04)"}
    m4["status"] = "BLENDER_RIGID_SHIFT_PASS"
    m4["source_blend"] = str(OUT_BLEND)
    m4["inbody_fbx"] = str(OUT_INBODY)
    m4["ribcage_fbx"] = str(FBX_DIR / "RIBCAGE_v04.fbx")
    m4["rigid_shift_check"] = REPORT["rigid_shift_check"]

    def sz(v):
        return [v[0] + LAY.SHIFT[0], v[1] + LAY.SHIFT[1], v[2] + LAY.SHIFT[2]]
    for tname, t in m4["objects"].items():
        for i in range(3):
            t["object_rest_world_transform"][i][3] += LAY.SHIFT[i]
        if t.get("break_empty"):
            t["break_empty"]["position_rest_world_m"] = sz(t["break_empty"]["position_rest_world_m"])
        for part in t["ucx_parts"]:
            part["bounds_rest_world_m"] = [sz(b) for b in part["bounds_rest_world_m"]]
            if "fit" in part and "worst_sample_rest_m" in part["fit"]:
                part["fit"]["worst_sample_rest_m"] = sz(part["fit"]["worst_sample_rest_m"])
            for pose in part.get("clearance", {}).values():
                for k in [k for k in pose if k.startswith(("body_", "head_", "other_", "nearest_other", "surface_intersections"))]:
                    pose.pop(k)
            part["body_v04"] = {p: body_info[p][part["name"]] for p in body_info}
    OUT_MANIFEST.write_text(json.dumps(m4, indent=1), encoding="utf-8")


def export(root):
    FBX_DIR.mkdir(exist_ok=True)
    organs = [o for o in bpy.data.objects if o.name.startswith("ORGAN_") and o.type == "MESH"]
    targets = [FBX_DIR / f"{o.name}_v04.fbx" for o in organs] + [FBX_DIR / "RIBCAGE_v04.fbx", FBX_DIR / "CHEST_VESSELS_v04.fbx"]
    for p in targets:
        assert not p.exists(), f"refusing to overwrite {p}"
    kw = dict(use_selection=True, object_types={"MESH", "EMPTY"}, axis_forward="-Z", axis_up="Y", apply_unit_scale=True,
              apply_scale_options="FBX_SCALE_UNITS", use_mesh_modifiers=False, bake_anim=False, add_leaf_bones=False,
              use_custom_props=True, mesh_smooth_type="FACE")

    def select(objs):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.hide_set(False)
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]

    for c in bpy.data.collections:          # make sure nothing selected is excluded from the view layer
        c.hide_viewport = False
    select([root] + list(root.children_recursive))
    bpy.ops.export_scene.fbx(filepath=str(OUT_INBODY), **kw)
    for ob in organs:
        par, mb = ob.parent, ob.matrix_basis.copy()
        ob.parent = None
        ob.matrix_world = Matrix.Identity(4)
        select([ob])
        bpy.ops.export_scene.fbx(filepath=str(FBX_DIR / f"{ob.name}_v04.fbx"), **kw)
        ob.parent = par
        ob.matrix_parent_inverse.identity()
        ob.matrix_basis = mb
    th = bpy.data.objects["SOCKET_THORAX"]
    mb = th.matrix_basis.copy()
    th.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    rc = bpy.data.objects["RIBCAGE"]
    select([th, rc] + list(rc.children_recursive))
    bpy.ops.export_scene.fbx(filepath=str(FBX_DIR / "RIBCAGE_v04.fbx"), **kw)
    chest = [o for o in th.children if o.name.startswith(("VESSELS_", "AIRWAY_", "DIAPHRAGM"))]
    select([th] + chest)
    bpy.ops.export_scene.fbx(filepath=str(FBX_DIR / "CHEST_VESSELS_v04.fbx"), **kw)
    th.matrix_basis = mb
    bpy.context.view_layer.update()
    REPORT["outputs"] = [str(p.relative_to(REPO)).replace("\\", "/") for p in [OUT_BLEND, OUT_INBODY] + targets + [OUT_JSON, OUT_MANIFEST]]
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND), copy=True)
    OUT_JSON.write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
    log("written", REPORT["outputs"])


main()
