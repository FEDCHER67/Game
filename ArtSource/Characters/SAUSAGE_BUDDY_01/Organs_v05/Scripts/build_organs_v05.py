"""ORGANS v05 from the trimmed Organs_v04 (Blender 5.2, background).

blender -b ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/Organs_v04.blend --python build_organs_v05.py [-- --dry <dir>]
The v04 file is only read.
  1. chest + liver block (every socket except the kidneys) moves by organs_layout_v05.SHIFT_CHEST, kidneys by SHIFT_KIDNEY;
  2. ureter stubs: the kidney tube below the bean is compressed to URETER_KEEP of its length;
  3. ribs 3-4 are bent again where the lower position brings their posterior tips closer than 2 mm to the back skin
     (same solver as trim_back_ribs_v04.py: ring translations only, skin + organ constraints), and only the UCX pieces over
     moved rings are rebuilt with G38's recipe; the G38 contract is re-checked for them, and the organ clearance of all
     96 pieces is re-measured against the moved kidneys;
  4. inside-body check (rest + TABLE_REST) of every render mesh, organ-organ surface intersections.
Writes into Organs_v05/: Organs_v05.blend, Organs_InBody_v05.fbx, FBX/ORGAN_*_v05.fbx, FBX/RIBCAGE_v05.fbx (UCX + BREAK),
FBX/CHEST_VESSELS_v05.fbx, organs_v05_build.json, G38_collisions_manifest_v05.json (refuses to overwrite).
"""
import copy
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
REPO = Path(r"C:/Dev/Game")
V04DIR = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04"
sys.path.insert(0, str(HERE))
import organs_layout_v05 as LAY  # noqa: E402

# reuse the v04 rib-trim machinery (skin/organ solver, G38 helpers B/M, partition, shave, contract measures)
_TRIM = V04DIR / "Scripts/trim_back_ribs_v04.py"
_src = _TRIM.read_text(encoding="utf-8")
T4 = {"__file__": str(_TRIM), "__name__": "trim_v04_lib"}
exec(compile(_src[:_src.rfind("\nmain()")], str(_TRIM), "exec"), T4)
B, M = T4["B"], T4["M"]

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DRY = Path(ARGS[ARGS.index("--dry") + 1]) if "--dry" in ARGS else None
OUT = DRY or HERE.parent
FBX_DIR = OUT / "FBX"
OUT_BLEND, OUT_INBODY, OUT_JSON = OUT / "Organs_v05.blend", OUT / "Organs_InBody_v05.fbx", OUT / "organs_v05_build.json"
OUT_MANIFEST = OUT / "G38_collisions_manifest_v05.json"
MAN4 = json.loads((V04DIR / "G38_collisions_manifest_v04.json").read_text(encoding="utf-8"))
BUILD4 = json.loads((V04DIR / "organs_v04_build.json").read_text(encoding="utf-8"))
RIBS = ("RIB_L_03", "RIB_R_03", "RIB_L_04", "RIB_R_04")
sc = bpy.context.scene
REPORT = {"version": "ORGANS_v05", "date": "2026-10-18", "source": bpy.data.filepath, "shift_chest_rest_m": list(LAY.SHIFT_CHEST),
          "shift_kidney_rest_m": list(LAY.SHIFT_KIDNEY), "ureter_keep": LAY.URETER_KEEP}


def log(*a):
    print("[ORGANS_v05]", *a, flush=True)


def rnd(v, n=5):
    return [round(float(c), n) for c in v]


def current_ranges(rib):
    """UCX ring ranges of a rib as they are in v04 (rebuilt pieces carry their rings; the others = v03d range minus the
    rings cut from the tip)."""
    removed = 1 if rib.endswith("_04") else 0
    out = []
    for part in MAN4["objects"][rib]["ucx_parts"]:
        if "rebuilt_v04_rib_trim" in part:
            a, z = part["rebuilt_v04_rib_trim"]["rings"]
        else:
            v3 = next(p for p in T4["RING_RANGES_V03D"][rib]["parts"] if p["name"] == part["name"])
            a, z = v3["first_ring"] - removed, v3["last_ring"] - removed
        out.append({"name": part["name"], "first_ring": a, "last_ring": z})
    return out


def shorten_ureter(ob, keep):
    """Compress the kidney tube (material 1) below the bean toward the bean's lower edge (organ-local Y is the long axis)."""
    me = ob.data
    bean = {i for p in me.polygons if p.material_index == 0 for i in p.vertices}
    tube = {i for p in me.polygons if p.material_index == 1 for i in p.vertices} - bean
    y0 = min(me.vertices[i].co.y for i in bean)
    n = 0
    for i in tube:
        v = me.vertices[i]
        if v.co.y < y0:
            v.co.y = y0 + (v.co.y - y0) * keep
            n += 1
    me.update()
    return {"tube_vertices_moved": n, "bean_bottom_local_y": round(y0, 4),
            "tube_tip_local_y": round(min(me.vertices[i].co.y for i in tube), 4)}


def main():
    if DRY is None:
        for p in (OUT_BLEND, OUT_INBODY, OUT_JSON, OUT_MANIFEST):
            assert not p.exists(), f"refusing to overwrite {p}"
    else:
        DRY.mkdir(parents=True, exist_ok=True)
    root = bpy.data.objects["ORGANS_v04_ROOT"]
    before = {o.name: o.matrix_world.copy() for o in bpy.data.objects if o.type in ("MESH", "EMPTY") and not o.name.startswith("REF_")}
    # 1. move the sockets
    Sc, Sk = Matrix.Translation(LAY.SHIFT_CHEST), Matrix.Translation(LAY.SHIFT_KIDNEY)
    for s in root.children:
        s.matrix_basis = (Sk if s.name in LAY.KIDNEY_SOCKETS else Sc) @ s.matrix_basis
    root.name = "ORGANS_v05_ROOT"
    for c in bpy.data.collections:
        if c.name == "ORGANS_v04":
            c.name = "ORGANS_v05"
        elif c.name == "COL_Collision_v04":
            c.name = "COL_Collision_v05"
    bpy.context.view_layer.update()
    kid_objs = {o.name for s in root.children if s.name in LAY.KIDNEY_SOCKETS for o in [s] + list(s.children_recursive)}
    err = 0.0
    for n, mw0 in before.items():
        o = bpy.data.objects.get(n) or bpy.data.objects.get("ORGANS_v05_ROOT")
        if o.name == "ORGANS_v05_ROOT":
            continue
        S = Sk if n in kid_objs else Sc
        err = max(err, max(abs(a - b) for ra, rb in zip(o.matrix_world, S @ mw0) for a, b in zip(ra, rb)))
    REPORT["move_check_max_matrix_error"] = err
    log("moved; max matrix error", err)
    assert err < 1e-6
    # 2. ureters
    REPORT["ureters"] = {n: shorten_ureter(bpy.data.objects[n], LAY.URETER_KEEP) for n in ("ORGAN_KIDNEY_L", "ORGAN_KIDNEY_R")}
    log("ureters", REPORT["ureters"])
    # 3. ribs 3-4 back tips
    skins = [T4["trunk_mesh"](T4["PATIENT"], False), T4["trunk_mesh"](T4["TABLE_REST"], True)]
    anatomy = {o.name: M.Mesh(o) for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("ORGAN_", "VESSELS_", "DIAPHRAGM", "AIRWAY_"))}
    organs = [m.bvh for m in anatomy.values()]
    rebuilt, bend = {}, {}
    for name in RIBS:
        ob = bpy.data.objects[name]
        tag = name.split("_")[1]
        opened_T = B.opened(tag)
        disp, skin_after, org_after, iters = T4["solve_bend"](ob, skins, organs, opened_T)
        moved = [k for k in range(len(disp)) if disp[k].length > 5e-5]
        inv3 = ob.matrix_world.inverted().to_3x3()
        for k in range(len(disp)):
            dl = inv3 @ disp[k]
            for v in ob.data.vertices[k * 10:(k + 1) * 10]:
                v.co += dl
        ob.data.update()
        bend[name] = {"rings_moved": moved, "max_translation_mm": round(max(d.length for d in disp) * 1000, 2),
                      "worst_skin_mm_after": min(skin_after), "worst_organ_mm_after_closed_open35": min(org_after)}
        log(name, "extra bend", bend[name])
        assert min(skin_after) >= 2.0
        if not moved:
            continue
        bpy.context.view_layer.update()
        rw = T4["rings_world"](ob)
        inv = ob.matrix_world.inverted()
        parts = current_ranges(name)
        aff = [p for p in parts if any(p["first_ring"] <= k <= p["last_ring"] for k in moved)]
        assert aff[0]["first_ring"] == 0
        E, K = aff[-1]["last_ring"], len(aff)
        bone = M.Mesh(ob)
        costs = {}
        for a in range(E):
            for z in range(a + 1, min(a + 5, E) + 1):
                bm = B.make_hull([p for k in range(a, z + 1) for p in rw[k]])
                costs[a, z] = T4["estimate_outside"](bm, bone)
                bm.free()
        score, total, ranges = T4["partition"](costs, K, E)
        tmp = bpy.data.collections.new("_tmp_ucx")
        sc.collection.children.link(tmp)
        for part, (a, z) in zip(aff, ranges):
            bm = B.make_hull([p for k in range(a, z + 1) for p in rw[k]])
            shaved = T4["shave_to_bone"](bm, bone, [p for k in range(a, z + 1) for p in rw[k]])
            cuts, unresolved = B.trim_to_obstacles(bm, tag, {n: m.bvh for n, m in anatomy.items()}, margin=.00315)
            old = bpy.data.objects[part["name"]]
            new = B.create_collision(part["name"] + "_new", ob, bm, inv, tmp, 0 if a < 24 else 1)
            old_me = old.data
            old.data = new.data
            old.data.name = old.name
            old["part_material_index"] = 0 if a < 24 else 1
            bpy.data.objects.remove(new, do_unlink=True)
            bpy.data.meshes.remove(old_me)
            rebuilt[old.name] = {"rib": name, "rings": [a, z], "rings_v04": [part["first_ring"], part["last_ring"]],
                                 "bulge_shave_cuts": shaved, "organ_cuts": cuts, "unresolved_cuts": unresolved}
        bpy.data.collections.remove(tmp)
    REPORT["rib_bend_v05"] = bend
    bpy.context.view_layer.update()
    # contract checks on rebuilt pieces
    checks = {}
    for pname, info in rebuilt.items():
        part = bpy.data.objects[pname]
        rib = bpy.data.objects[info["rib"]]
        health = M.mesh_health(part)
        out_mm, samples = T4["outside_bone_mm"](part, M.Mesh(rib))
        tag = info["rib"].split("_")[1]
        dmin = {}
        for pose, T in (("closed", Matrix.Identity(4)), ("open35", B.opened(tag))):
            pm = M.Mesh(part, T)
            best = (9e9, None)
            for an, am in anatomy.items():
                d, hit = M.distance(pm, am, upper=best[0])
                if d < best[0]:
                    best = (d, an)
            dmin[pose] = {"organ_min_mm": round(best[0] * 1000, 3), "nearest_organ": best[1]}
        checks[pname] = dict(info, vertices=health["vertices"], triangles=health["triangles"], convex=health["convex"],
                             closed=health["nonmanifold_edges"] == 0 and health["components"] == 1,
                             outside_sample_max_mm=round(out_mm, 3), outside_certified_mm=round(out_mm + 0.25, 3), samples=samples, clearance=dmin)
    cover = {}
    for name in RIBS:
        rib = bpy.data.objects[name]
        unc, n_unc, n = T4["uncovered_mm"](rib, [o for o in rib.children if o.name.startswith("UCX_")])
        cover[name] = {"uncovered_sample_max_mm": round(unc, 3), "uncovered_certified_mm": round(unc + 0.25, 3)}
    gaps = {}
    for tag in ("L", "R"):
        for a, b in (("02", "03"), ("03", "04")):
            pa = [M.Mesh(o) for o in bpy.data.objects[f"RIB_{tag}_{a}"].children if o.name.startswith("UCX_")]
            pb_ = [M.Mesh(o) for o in bpy.data.objects[f"RIB_{tag}_{b}"].children if o.name.startswith("UCX_")]
            best = 9e9
            for x in pa:
                for y in pb_:
                    best = min(best, M.distance(x, y, upper=best)[0])
            gaps[f"RIB_{tag}_{a} / RIB_{tag}_{b}"] = round(best * 1000, 3)
    # every UCX piece against the moved kidneys (the only organs that moved relative to the ribcage)
    kid = {n: anatomy[n] for n in ("ORGAN_KIDNEY_L", "ORGAN_KIDNEY_R")}
    kmin = {"closed": 9e9, "open35": 9e9}
    for u in [o for o in bpy.data.objects if o.name.startswith("UCX_")]:
        tag = "L" if "_L_" in u.name else "R"
        for pose, T in (("closed", Matrix.Identity(4)), ("open35", B.opened(tag))):
            um = M.Mesh(u, T)
            for km in kid.values():
                kmin[pose] = min(kmin[pose], M.distance(um, km, upper=kmin[pose])[0])
    kmin = {k: round(v * 1000, 2) for k, v in kmin.items()}
    ok = (all(c["convex"] and c["closed"] and c["vertices"] <= 64 and c["outside_certified_mm"] <= 2.0
              and c["clearance"]["closed"]["organ_min_mm"] >= 3.0 and c["clearance"]["open35"]["organ_min_mm"] >= 3.0
              and not c["unresolved_cuts"] for c in checks.values())
          and all(c["uncovered_certified_mm"] <= 1.0 for c in cover.values()) and all(g >= 8.0 for g in gaps.values())
          and min(kmin.values()) >= 3.0)
    REPORT.update({"ucx_rebuilt_v05": checks, "coverage": cover, "rib_gaps_mm": gaps, "ucx_to_kidneys_min_mm": kmin, "contract_pass": ok})
    log("rebuilt", len(checks), "UCX; worst outside", max([c["outside_certified_mm"] for c in checks.values()] or [0]),
        "coverage", cover, "gaps", gaps, "UCX-kidney", kmin, "PASS" if ok else "FAIL")
    assert ok
    # 4. inside body + organ-organ hits
    render = [o for o in bpy.data.objects if o.type == "MESH" and o.name.split("_")[0] in ("ORGAN", "RIB", "STERNUM", "SPINE", "VESSELS", "AIRWAY", "DIAPHRAGM")]
    inside = {}
    for o in render:
        w = 9.0
        for v in o.data.vertices[::1]:
            p = o.matrix_world @ v.co
            for b in skins:
                w = min(w, T4["signed"](b, p)[0])
        inside[o.name] = round(w * 1000, 2)
    REPORT["min_skin_depth_mm"] = inside
    log("min skin depth mm (<3):", {k: v for k, v in inside.items() if v < 3})
    hits = {}
    organ_meshes = [o for o in render if o.name.startswith("ORGAN_")]
    for i, a in enumerate(organ_meshes):
        for b in organ_meshes[i + 1:]:
            ov = anatomy[a.name].bvh.overlap(anatomy[b.name].bvh)
            if ov:
                hits[f"{a.name} x {b.name}"] = len(ov)
    REPORT["organ_organ_tri_pairs"] = hits
    log("organ-organ hits", hits)
    z = {}
    for n in ("ORGAN_HEART", "ORGAN_LUNG_L", "ORGAN_LIVER", "ORGAN_KIDNEY_L", "ORGAN_KIDNEY_R", "STERNUM_L", "RIB_L_01", "DIAPHRAGM"):
        o = bpy.data.objects[n]
        zs = [(o.matrix_world @ v.co).z for v in o.data.vertices]
        z[n] = [round(min(zs), 4), round(max(zs), 4)]
    REPORT["rest_z_ranges_v05"] = z
    log("z", z)
    describe(root)
    manifest(checks, cover, gaps, kmin, kid_objs)
    if DRY is not None:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND), copy=True)
        OUT_JSON.write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
        return
    export(root)


def describe(root):
    bpy.context.view_layer.update()
    REPORT["sockets"] = {}
    for s in root.children:
        mw = s.matrix_world
        REPORT["sockets"][s.name] = {"rest_position": rnd(mw.translation), "rest_rotation_wxyz": rnd(mw.to_quaternion()),
                                     "rest_x_axis": rnd(mw.col[0][:3], 4), "rest_y_axis": rnd(mw.col[1][:3], 4),
                                     "rest_z_axis": rnd(mw.col[2][:3], 4)}
    objs = {}
    for ob in bpy.data.objects:
        if ob.name.startswith(("REF_", "ORGANS_v05_ROOT", "SOCKET_")) or ob.type not in ("MESH", "EMPTY"):
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

    def shift_tree(x):
        if isinstance(x, dict):
            return {k: shift_tree(v) for k, v in x.items()}
        if isinstance(x, list) and len(x) == 3 and all(isinstance(c, (int, float)) for c in x):
            return [round(a + b, 5) for a, b in zip(x, LAY.SHIFT_CHEST)]
        return x
    REPORT["connections"] = shift_tree(BUILD4.get("connections", {}))


def manifest(checks, cover, gaps, kmin, kid_objs):
    m = copy.deepcopy(MAN4)
    m["schema"] = "G38_collision_manifest_v05/1 (v04 moved + re-trimmed by Claude)"
    m["revision"] = "v05"
    m["derived_from_v04"] = {"shift_chest_rest_m": list(LAY.SHIFT_CHEST), "note": "ribcage moves with the chest block (rigid); "
                             "only the kidneys moved relative to it (re-measured: ucx_to_kidneys_min_mm)"}
    m["source_blend"], m["inbody_fbx"], m["ribcage_fbx"] = str(OUT_BLEND), str(OUT_INBODY), str(FBX_DIR / "RIBCAGE_v05.fbx")

    def sz(v):
        return [v[i] + LAY.SHIFT_CHEST[i] for i in range(3)]
    for tname, t in m["objects"].items():
        for i in range(3):
            t["object_rest_world_transform"][i][3] += LAY.SHIFT_CHEST[i]
        if t.get("break_empty"):
            t["break_empty"]["position_rest_world_m"] = sz(t["break_empty"]["position_rest_world_m"])
        for part in t["ucx_parts"]:
            part["bounds_rest_world_m"] = [sz(b) for b in part["bounds_rest_world_m"]]
            if "worst_sample_rest_m" in part.get("fit", {}):
                part["fit"]["worst_sample_rest_m"] = sz(part["fit"]["worst_sample_rest_m"])
            part.pop("body_v04", None)
            if part["name"] in checks:
                c = checks[part["name"]]
                ob = bpy.data.objects[part["name"]]
                co = [v.co for v in ob.data.vertices]
                wc = [ob.matrix_world @ v for v in co]
                part.update({"vertex_count": c["vertices"], "triangle_count": c["triangles"],
                             "bounds_target_local_m": [[min(v[i] for v in co) for i in range(3)], [max(v[i] for v in co) for i in range(3)]],
                             "bounds_rest_world_m": [[min(v[i] for v in wc) for i in range(3)], [max(v[i] for v in wc) for i in range(3)]],
                             "fit": {"sample_max_outside_mm": c["outside_sample_max_mm"], "certified_upper_outside_mm": c["outside_certified_mm"],
                                     "grid_cover_radius_mm": 0.25, "samples": c["samples"], "pass_2mm": c["outside_certified_mm"] <= 2.0},
                             "clearance": c["clearance"], "rebuilt_v05": {"rings": c["rings"], "organ_cuts": c["organ_cuts"]}})
    m["v05_checks"] = {"rib_bend_v05": REPORT["rib_bend_v05"], "coverage": cover, "rib_gaps_mm": gaps, "ucx_to_kidneys_min_mm": kmin,
                       "contract_pass": REPORT["contract_pass"]}
    allparts = [p for t in m["objects"].values() for p in t["ucx_parts"]]
    m["collision_results"]["min_organ_clearance_closed_mm"] = min(min(p["clearance"]["closed"]["organ_min_mm"] for p in allparts), kmin["closed"])
    m["collision_results"]["min_organ_clearance_open_mm"] = min(min(p["clearance"]["open35"]["organ_min_mm"] for p in allparts), kmin["open35"])
    m["collider_fit_results"]["maximum_outside_bound_mm"] = max(p["fit"]["certified_upper_outside_mm"] for p in allparts)
    m["status"] = "BLENDER_V05_PASS" if REPORT["contract_pass"] else "FAIL"
    (DRY or OUT).joinpath("G38_collisions_manifest_v05.json").write_text(json.dumps(m, indent=1), encoding="utf-8")


def export(root):
    FBX_DIR.mkdir(exist_ok=True)
    organs = [o for o in bpy.data.objects if o.name.startswith("ORGAN_") and o.type == "MESH"]
    targets = [FBX_DIR / f"{o.name}_v05.fbx" for o in organs] + [FBX_DIR / "RIBCAGE_v05.fbx", FBX_DIR / "CHEST_VESSELS_v05.fbx"]
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

    select([root] + list(root.children_recursive))
    bpy.ops.export_scene.fbx(filepath=str(OUT_INBODY), **kw)
    for ob in organs:
        par, mb = ob.parent, ob.matrix_basis.copy()
        ob.parent = None
        ob.matrix_world = Matrix.Identity(4)
        select([ob])
        bpy.ops.export_scene.fbx(filepath=str(FBX_DIR / f"{ob.name}_v05.fbx"), **kw)
        ob.parent = par
        ob.matrix_parent_inverse.identity()
        ob.matrix_basis = mb
    th = bpy.data.objects["SOCKET_THORAX"]
    mb = th.matrix_basis.copy()
    th.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    rc = bpy.data.objects["RIBCAGE"]
    select([th, rc] + list(rc.children_recursive))
    bpy.ops.export_scene.fbx(filepath=str(FBX_DIR / "RIBCAGE_v05.fbx"), **kw)
    select([th] + [o for o in th.children if o.name.startswith(("VESSELS_", "AIRWAY_", "DIAPHRAGM"))])
    bpy.ops.export_scene.fbx(filepath=str(FBX_DIR / "CHEST_VESSELS_v05.fbx"), **kw)
    th.matrix_basis = mb
    bpy.context.view_layer.update()
    REPORT["outputs"] = [str(p.relative_to(REPO)).replace("\\", "/") for p in [OUT_BLEND, OUT_INBODY] + targets + [OUT_JSON, OUT_MANIFEST]]
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND), copy=True)
    OUT_JSON.write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
    log("written", len(REPORT["outputs"]), "files")


main()
