"""PortableFridge_W86 v01 - FBX round-trip + mesh health check (Blender 5.2, background).

blender -b --factory-startup --python validate_portable_fridge_w86_v01.py
env PF_DIR (folder with the FBX/JSON, default the asset folder), PF_VAL (output json)
"""
import bpy, bmesh, json, math, os
from mathutils import Vector

ROOT = r"C:\Dev\Game\ArtSource\Props\PortableFridge_W86"
DIR = os.environ.get("PF_DIR", ROOT)
VAL = os.environ.get("PF_VAL", os.path.join(ROOT, "Validation", "PortableFridge_W86_v01_validation.json"))
spec = json.load(open(os.path.join(DIR, "PortableFridge_W86_v01.json"), encoding="utf-8"))

EXPECT = {
    "PortableFridge_W86_v01.fbx": {
        "meshes": ["SM_PortableFridge_Body_LOD0", "SM_PortableFridge_Body_LOD1", "SM_PortableFridge_Lid_LOD0",
                   "SM_PortableFridge_Lid_LOD1", "UCX_SM_PortableFridge_Body_00", "UCX_SM_PortableFridge_Body_01",
                   "UCX_SM_PortableFridge_Body_02", "UCX_SM_PortableFridge_Lid_00"],
        "empties": ["PortableFridge_W86", "LID_PIVOT", "GRIP_L", "GRIP_R", "REF_LidFront_Open"] +
                   ["SLOT_%02d" % i for i in range(1, 9)],
        "decal_boundary": {"SM_PortableFridge_Body_LOD0": 4, "SM_PortableFridge_Body_LOD1": 4,
                           "SM_PortableFridge_Lid_LOD0": 4, "SM_PortableFridge_Lid_LOD1": 4},
    },
    "PortableFridge_W86_VanMount_v01.fbx": {
        "meshes": ["SM_PortableFridge_VanMount_LOD0", "SM_PortableFridge_VanMount_LOD1"] +
                  ["UCX_SM_PortableFridge_VanMount_%02d" % i for i in range(5)],
        "empties": ["PortableFridge_W86_VanMount", "COOLER_SOCKET", "REF_WallPlane"],
        "decal_boundary": {},
    },
}


def health(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    nonman = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-9)
    # signed volume per mesh (positive = outward normals overall)
    vol = 0.0
    for f in bm.faces:
        vs = [v.co for v in f.verts]
        for i in range(1, len(vs) - 1):
            vol += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    bm.free()
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for v in o.data.vertices:
        w = o.matrix_world @ v.co
        mn = Vector(map(min, mn, w))
        mx = Vector(map(max, mx, w))
    return {"triangles": tris, "boundary_edges": boundary, "nonmanifold_edges": nonman, "zero_area_faces": zero,
            "signed_volume_m3": round(vol, 6), "uv_layers": len(o.data.uv_layers),
            "materials": [m.name for m in o.data.materials if m],
            "world_min": [round(c, 4) for c in mn], "world_max": [round(c, 4) for c in mx]}


report = {"asset": "PortableFridge_W86", "revision": "v01", "files": {}, "pass": True, "checks": []}


def check(name, ok, detail=""):
    report["checks"].append({"check": name, "pass": bool(ok), "detail": detail})
    if not ok:
        report["pass"] = False


for fn, exp in EXPECT.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=os.path.join(DIR, fn))
    bpy.context.view_layer.update()
    O = bpy.data.objects
    names = sorted(o.name for o in O)
    meshes = {o.name: health(o) for o in O if o.type == "MESH"}
    empties = {o.name: [round(c, 4) for c in o.matrix_world.translation] for o in O if o.type == "EMPTY"}
    imgs = [{"name": i.name, "size": list(i.size), "packed": bool(i.packed_file)} for i in bpy.data.images]
    report["files"][fn] = {"objects": names, "meshes": meshes, "empties": empties, "images": imgs,
                           "bytes": os.path.getsize(os.path.join(DIR, fn))}
    for m in exp["meshes"]:
        check(fn + ": mesh " + m, m in meshes)
    for e in exp["empties"]:
        check(fn + ": empty " + e, e in empties)
    for m, h in meshes.items():
        if m.startswith("UCX_"):
            check(fn + ": " + m + " convex box", h["triangles"] == 12 and h["boundary_edges"] == 0)
            continue
        check(fn + ": " + m + " health",
              h["nonmanifold_edges"] == 0 and h["zero_area_faces"] == 0 and h["uv_layers"] == 1
              and h["boundary_edges"] == exp["decal_boundary"].get(m, 0) and h["signed_volume_m3"] > 0,
              json.dumps({k: h[k] for k in ("triangles", "boundary_edges", "nonmanifold_edges", "zero_area_faces",
                                            "signed_volume_m3")}))
    check(fn + ": atlas embedded", any(i["size"][0] == 1024 for i in imgs), json.dumps(imgs))

    if fn == "PortableFridge_W86_v01.fbx":
        lod0 = meshes["SM_PortableFridge_Body_LOD0"]["triangles"] + meshes["SM_PortableFridge_Lid_LOD0"]["triangles"]
        lod1 = meshes["SM_PortableFridge_Body_LOD1"]["triangles"] + meshes["SM_PortableFridge_Lid_LOD1"]["triangles"]
        check("LOD0 <= 2500 tris", lod0 <= 2500, "LOD0 %d, LOD1 %d" % (lod0, lod1))
        check("LOD1 < LOD0", lod1 < lod0 * 0.6, "LOD1/LOD0 = %.2f" % (lod1 / lod0))
        check("tris match build json", lod0 == spec["lods"]["LOD0_tris"] and lod1 == spec["lods"]["LOD1_tris"])
        for a in spec["slots"]["anchors"]:
            got = Vector(empties[a["name"]])
            check("slot " + a["name"] + " position", (got - Vector(a["blender"])).length < 1e-3, str(list(got)))
        for g in ("GRIP_L", "GRIP_R"):
            got = Vector(empties[g])
            check(g + " position", (got - Vector(spec["grips"][g]["blender"])).length < 1e-3, str(list(got)))
        piv = Vector(empties["LID_PIVOT"])
        check("LID_PIVOT position", (piv - Vector(spec["lid"]["pivot_blender"])).length < 1e-3, str(list(piv)))
        for n in ("SM_PortableFridge_Lid_LOD0", "SM_PortableFridge_Lid_LOD1", "UCX_SM_PortableFridge_Lid_00"):
            org = O[n].matrix_world.translation
            check(n + " origin on hinge", (org - piv).length < 1e-3, str([round(c, 4) for c in org]))
        lid = O["SM_PortableFridge_Lid_LOD0"]
        closed_top = max((lid.matrix_world @ v.co).z for v in lid.data.vertices)
        check("closed lid top = lid_top_height", abs(closed_top - spec["dimensions"]["lid_top_height"]) < 1e-3,
              "%.4f" % closed_top)
        # rotate the imported lid about its local X and compare the front edge with the REF empty
        lid.rotation_mode = "XYZ"
        lid.rotation_euler.x += math.radians(-spec["lid"]["open_angle_deg"])
        bpy.context.view_layer.update()
        ref = Vector(empties["REF_LidFront_Open"])
        ok, cp, _n, _i = lid.closest_point_on_mesh(lid.matrix_world.inverted() @ ref)
        best = ((lid.matrix_world @ cp) - ref).length if ok else 9.9
        zmax = max((lid.matrix_world @ v.co).z for v in lid.data.vertices)
        check("lid opens upward to REF_LidFront_Open", best < 0.02 and zmax > 0.75,
              "nearest lid surface %.4f m from ref, open lid top z %.3f" % (best, zmax))
        body = meshes["SM_PortableFridge_Body_LOD0"]
        check("feet on the floor (z min = 0)", abs(body["world_min"][2]) < 1e-4, str(body["world_min"]))
    else:
        sock = Vector(empties["COOLER_SOCKET"])
        check("COOLER_SOCKET at pad top", abs(sock.z - spec["van_mount"]["COOLER_SOCKET"]["blender"][2]) < 1e-4)
        m = meshes["SM_PortableFridge_VanMount_LOD0"]
        check("mount on the floor", abs(m["world_min"][2]) < 1e-4, str(m["world_min"]))
        check("mount rear = wall plane", abs(m["world_max"][1] - spec["van_mount"]["wall_plane"]["blender_y"]) < 1e-3,
              str(m["world_max"]))

os.makedirs(os.path.dirname(VAL), exist_ok=True)
if os.path.exists(VAL) and VAL.startswith(ROOT):
    raise SystemExit("refusing to overwrite " + VAL)
with open(VAL, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=1)
print("VALIDATION", "PASS" if report["pass"] else "FAIL", sum(c["pass"] for c in report["checks"]), "/", len(report["checks"]))
for c in report["checks"]:
    if not c["pass"]:
        print("FAILED", c["check"], c["detail"])
