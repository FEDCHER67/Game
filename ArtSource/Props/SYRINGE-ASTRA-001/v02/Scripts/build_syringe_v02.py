"""SYRINGE-ASTRA-001 v02: the approved syringe (same meshes, size, materials) regrouped for a blood draw / transfer.

blender -b ArtSource/Props/SYRINGE-ASTRA-001/SYRINGE-ASTRA-001.blend --python v02/Scripts/build_syringe_v02.py [-- --out <dir>]
The v01 .blend is only read. Writes (refuses to overwrite) into SYRINGE-ASTRA-001/v02/:
  SYRINGE_ASTRA_001_v02.blend / .fbx, syringe_v02_validation.json, Previews/syringe_v02_fill_{000,050,100}.png

Hierarchy (Blender Z = barrel axis, needle tip at the root origin pointing -Z; Unity: +Y is the barrel axis):
  SYRINGE_ASTRA_001_v02 (root empty, origin = needle tip, same placement as v01)
    SYRINGE_BODY   opaque static parts: finger flange, collar, tapered hub, chamber lips, guards, graduations, needle seat
    NEEDLE         the fine needle
    NEEDLE_TIP     empty at the needle point; its +Z points out of the tip (along the needle)
    BARREL         translucent chamber shell (Unity: Transparent surface, see the material's custom props)
    BLOOD          blood volume; ORIGIN = FILL PLANE at the needle end of the chamber; mesh authored FULL;
                   scale its local Z (Unity local Y) = fill 0..1 (disable the renderer below ~0.01)
    PLUNGER        thumb pad + shaft + rubber stopper (one mesh); ORIGIN = centre of the stopper's lower face on the
                   barrel axis; slides along local/parent +Z (Unity +Y)
Fill rule (the blood surface always sits 0.4 mm under the stopper):
  BLOOD.scale.z  = fill
  PLUNGER.z      = PLUNGER_Z_EMPTY + fill * TRAVEL    (Blender; Unity localPosition.y, same numbers)
The FBX is exported FULL (fill = 1) plus a 61-frame DRAW_FILL take (frame 1 = empty, 61 = full) as an example.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else HERE.parent
STEM = "SYRINGE_ASTRA_001_v02"
OUT_BLEND, OUT_FBX, OUT_JSON = OUT / f"{STEM}.blend", OUT / f"{STEM}.fbx", OUT / "syringe_v02_validation.json"
PREV = OUT / "Previews"
assert Path(bpy.data.filepath).name == "SYRINGE-ASTRA-001.blend", "run on the v01 SYRINGE-ASTRA-001.blend"
for p in (OUT_BLEND, OUT_FBX, OUT_JSON):
    assert not p.exists(), f"refusing to overwrite {p}"
sc = bpy.context.scene

BODY = ["SM_FingerFlange", "SM_LowerBodyCollar", "SM_TaperedHub", "SM_LowerChamberLip", "SM_UpperChamberLip", "SM_ChamberGuard_L",
        "SM_ChamberGuard_R", "SM_Graduation_01", "SM_Graduation_02", "SM_Graduation_03", "SM_NeedleSeat"]
PLUNGER = ["SM_ThumbPad", "SM_PlungerShaft", "SM_PlungerCoreBridge", "SM_StopperCore", "SM_StopperLower", "SM_StopperUpper",
           "SM_StopperEdge"]

# v01 at FULL: frame 61 (CTRL_PlungerTravel_Z = 0, blood scale z = 0.04896)
sc.frame_set(61)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()


def world_mesh(names, name):
    bm = bmesh.new()
    mats = []
    for n in names:
        ob = bpy.data.objects[n]
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
        me.transform(ob.matrix_world)
        remap = []
        for m in me.materials:
            if m not in mats:
                mats.append(m)
            remap.append(mats.index(m))
        for p in me.polygons:
            p.material_index = remap[p.material_index] if remap else 0
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    return me


body_me = world_mesh(BODY, "SYRINGE_BODY")
needle_me = world_mesh(["SM_FineNeedle"], "NEEDLE")
barrel_me = world_mesh(["SM_ClearBarrel"], "BARREL")
plunger_me = world_mesh(PLUNGER, "PLUNGER")
blood_me = world_mesh(["SM_BloodVolume_FILL_Z"], "BLOOD")

zs = [v.co.z for v in blood_me.vertices]
BLOOD_BASE, BLOOD_TOP = min(zs), max(zs)
H = BLOOD_TOP - BLOOD_BASE
# the rubber stopper's lower face (the thin core bridge, r 4.3 mm, reaches ~1 mm lower inside the blood and is ignored)
stopper_bottom_full = min(v.co.z for v in plunger_me.vertices if 0.006 < math.hypot(v.co.x, v.co.y) < 0.016 and v.co.z < 0.14)
# v01 had the stopper face ~0.07 mm INSIDE the blood top (coplanar flicker). v02: a constant 0.5 mm gap; the blood column
# is rescaled so that its full height equals the plunger travel exactly.
GAP = 0.0005
PLUNGER_Z_EMPTY = BLOOD_BASE + GAP
TRAVEL = stopper_bottom_full - PLUNGER_Z_EMPTY
for v in blood_me.vertices:
    v.co.z = BLOOD_BASE + (v.co.z - BLOOD_BASE) * TRAVEL / H
H = TRAVEL
needle_tip_z = min(v.co.z for v in needle_me.vertices)

# remove the v01 objects and actions (the v01 file on disk is never written)
for o in list(bpy.data.objects):
    if o.type in ("MESH", "EMPTY"):
        bpy.data.objects.remove(o, do_unlink=True)
for a in list(bpy.data.actions):
    bpy.data.actions.remove(a)

coll = bpy.data.collections.new("SYRINGE_v02")
sc.collection.children.link(coll)
root = bpy.data.objects.new(STEM, None)
root.empty_display_type = "PLAIN_AXES"
root.empty_display_size = 0.05
coll.objects.link(root)


def add(me, name, origin):
    me.transform(Matrix.Translation(-Vector(origin)))
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.parent = root
    ob.location = origin
    for p in me.polygons:
        p.use_smooth = True
    return ob


body = add(body_me, "SYRINGE_BODY", (0, 0, 0))
needle = add(needle_me, "NEEDLE", (0, 0, 0))
barrel = add(barrel_me, "BARREL", (0, 0, 0))
blood = add(blood_me, "BLOOD", (0, 0, BLOOD_BASE))
plunger = add(plunger_me, "PLUNGER", (0, 0, PLUNGER_Z_EMPTY + TRAVEL))
tip = bpy.data.objects.new("NEEDLE_TIP", None)
tip.empty_display_type = "SINGLE_ARROW"
tip.empty_display_size = 0.02
coll.objects.link(tip)
tip.parent = root
tip.location = (0, 0, needle_tip_z)
tip.rotation_euler = (math.pi, 0, 0)          # +Z of the empty = along the needle, out of the tip (world -Z)
# flat-shade the graduations / lips stay as they were? smooth everything except the thin graduation plates
for p in body.data.polygons:
    p.use_smooth = True

# v02 colour tweaks: a more saturated cartoon blood (it reads through the chamber) and a clearer chamber
bm_ = blood_me.materials[0]
bbs = next(n for n in bm_.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bbs.inputs["Base Color"].default_value = (0.52, 0.012, 0.022, 1)
bbs.inputs["Roughness"].default_value = 0.45
# Unity material notes (sRGB) + the translucent chamber
for m in bpy.data.materials:
    bs = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None
    if bs is None:
        continue
    c = bs.inputs["Base Color"].default_value
    to_srgb = lambda x: 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    m["unity_base_color_srgb"] = [round(to_srgb(c[i]), 3) for i in range(3)]
    m["unity_smoothness"] = round(1 - bs.inputs["Roughness"].default_value, 2)
cm = barrel.data.materials[0]
cm["unity_surface"] = "Transparent"
cm["unity_alpha"] = 0.14
cbs = next(n for n in cm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
cbs.inputs["Alpha"].default_value = 0.14
cbs.inputs["Roughness"].default_value = 0.25
for attr, val in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
    try:
        setattr(cm, attr, val)
    except (AttributeError, TypeError):
        pass
cm.use_backface_culling = False


def set_fill(f):
    blood.scale = (1, 1, max(f, 1e-4))
    blood.hide_render = f < 0.01
    plunger.location = (0, 0, PLUNGER_Z_EMPTY + f * TRAVEL)


# example take: DRAW_FILL 1..61 (empty -> full), linear
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
sc.frame_start, sc.frame_end = 1, 61
for fr, f in ((1, 0.0), (61, 1.0)):
    sc.frame_set(fr)
    set_fill(f)
    blood.keyframe_insert("scale", index=2, frame=fr)
    plunger.keyframe_insert("location", index=2, frame=fr)
if blood.animation_data and blood.animation_data.action:
    blood.animation_data.action.name = "DRAW_FILL_BLOOD"
if plunger.animation_data and plunger.animation_data.action:
    plunger.animation_data.action.name = "DRAW_FILL_PLUNGER"
sc.frame_set(61)
set_fill(1.0)


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# validation: the stopper never enters the blood, never leaves the barrel, at fill 0 / 0.5 / 1
checks = {}
for fr, f in ((1, 0.0), (31, 0.5), (61, 1.0)):
    sc.frame_set(fr)
    bpy.context.view_layer.update()
    assert abs(blood.scale.z - max(f, 1e-4)) < 1e-3, (fr, blood.scale.z)
    top = BLOOD_BASE + f * H
    sb = min((plunger.matrix_world @ v.co).z for v in plunger.data.vertices if 0.006 < math.hypot(v.co.x, v.co.y) < 0.016 and v.co.z < 0.02)
    checks[f"fill_{f}"] = {"frame": fr, "blood_top_z": round(top, 5), "stopper_bottom_z": round(sb, 5), "gap_mm": round((sb - top) * 1000, 2)}
sc.frame_set(61)
report = {"source": bpy.data.filepath, "frame_read": 61,
          "axis": "Blender +Z = barrel axis (Unity +Y); needle tip at the root origin, pointing -Z",
          "blood": {"object": "BLOOD", "origin_z_fill_plane": round(BLOOD_BASE, 5), "full_height_m": round(H, 5),
                    "radius_m": round(max(v.co.x for v in blood.data.vertices), 5),
                    "rule": "BLOOD local scale Z (Unity local Y) = fill; hide the renderer below fill 0.01"},
          "plunger": {"object": "PLUNGER", "pivot": "centre of the stopper's lower face on the barrel axis",
                      "z_at_fill_0": round(PLUNGER_Z_EMPTY, 5), "z_at_fill_1": round(PLUNGER_Z_EMPTY + TRAVEL, 5),
                      "travel_m": round(TRAVEL, 5), "rule": "PLUNGER local position Z (Unity Y) = z_at_fill_0 + fill * travel_m",
                      "stopper_to_blood_gap_mm": round(GAP * 1000, 2)},
          "needle_tip": {"object": "NEEDLE_TIP", "position_z": round(needle_tip_z, 5), "plus_z_points": "out of the tip (world -Z)"},
          "fbx_default_state": "FULL (fill = 1)", "take": "DRAW_FILL frames 1..61 (30 fps): fill 0 -> 1, linear",
          "objects": {o.name: {"tris": tris(o), "materials": [m.name for m in o.data.materials]} for o in (body, needle, barrel, blood, plunger)},
          "total_tris": sum(tris(o) for o in (body, needle, barrel, blood, plunger)), "checks": checks,
          "translucent_barrel": {"material": cm.name, "alpha": 0.14, "unity": "URP Lit Transparent, render after BLOOD (queue +1) "
                                                                             "or keep BLOOD opaque so sorting cannot flip"}}

# previews: fill 0 / 50 / 100
PREV.mkdir(parents=True, exist_ok=True)
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        pass
sc.render.film_transparent = False            # keep the v01 file's colour management and studio lights
cam = bpy.data.objects.get("ReviewCamera")
if cam is None:
    cam = bpy.data.objects.new("ReviewCamera", bpy.data.cameras.new("ReviewCamera"))
    sc.collection.objects.link(cam)
sc.camera = cam
target = Vector((0, 0, 0.11))
loc = Vector((0.12, -0.36, 0.17))
fwd = (target - loc).normalized()
x = fwd.cross(Vector((0, 0, 1))).normalized()
cam.matrix_world = Matrix.Translation(loc) @ Matrix((x, x.cross(fwd), -fwd)).transposed().to_4x4()
cam.data.lens = 70
sc.render.resolution_x, sc.render.resolution_y = 700, 1000
for fr, f in ((1, 0.0), (31, 0.5), (61, 1.0)):     # the DRAW_FILL take drives both objects (linear)
    sc.frame_set(fr)
    blood.hide_render = f < 0.01
    sc.render.filepath = str(PREV / f"syringe_v02_fill_{int(f * 100):03d}.png")
    bpy.ops.render.render(write_still=True)
sc.frame_set(61)
blood.hide_render = False

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND), copy=True)
bpy.ops.object.select_all(action="DESELECT")
for o in (root, body, needle, barrel, blood, plunger, tip):
    o.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, object_types={"MESH", "EMPTY"}, axis_forward="-Z", axis_up="Y",
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", use_mesh_modifiers=False, bake_anim=True,
                         bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
                         add_leaf_bones=False, use_custom_props=True)
OUT_JSON.write_text(json.dumps(report, indent=1), encoding="utf-8")
print("[SYRINGE_v02]", json.dumps(report))
