"""PLAYER-CHAR-003 - build a conservative rigged Blender prototype for Player_01.

Run headless:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python build_player_01.py

Reads (never modified):
    ../Source/human dude.fbx          preserved CC0 source character

Writes:
    Player_01.blend                   exact owned output
    ../Export/Player_01.fbx           exact owned output

Prints one line:  BUILD_REPORT=<json>

Design notes:
  * The source is a 14.3-unit-tall low-poly T-pose character facing -Y.
  * Normalisation bakes the FBX import transform into the mesh, scales the
    character to exactly 1.8 m and puts the origin at the feet.
  * Only torso top vertices receive a very slight radial expansion +
    rounding; head, hands, limbs and footwear keep their exact coordinates.
  * Automatic (bone heat) weights are attempted first; if they fail a
    coverage / cross-side sanity gate, a deterministic bounded-region
    weighting fallback is applied. All weights are normalised to sum 1.
  * No animation, no Unity integration.
"""

import json
import math
import os

import bpy
from mathutils import Matrix, Vector

TASK_ID = "PLAYER-CHAR-003"

HERE = os.path.dirname(os.path.abspath(__file__))
PLAYER_DIR = os.path.normpath(os.path.join(HERE, ".."))
SOURCE_FBX = os.path.join(PLAYER_DIR, "Source", "human dude.fbx")
BLEND_OUT = os.path.join(HERE, "Player_01.blend")
FBX_OUT = os.path.join(PLAYER_DIR, "Export", "Player_01.fbx")

MESH_OBJECT_NAME = "Player_01"
ARMATURE_OBJECT_NAME = "Armature"
TARGET_HEIGHT = 1.8  # metres

# --------------------------------------------------------------------------
# Torso expansion (subtle, keeps topology)
# --------------------------------------------------------------------------
TORSO_Z_LO = 0.86
TORSO_Z_HI = 1.135
TORSO_MAX_AX = 0.19
TORSO_MAX_R = 0.20
TORSO_RAMP_IN = (0.87, 0.92)
TORSO_RAMP_OUT = (1.11, 1.16)
TORSO_ROUND = 0.35   # blend cross-section radius toward the mean (0 = keep shape)
TORSO_EXPAND = 0.09  # radial expansion at the bump peak

# --------------------------------------------------------------------------
# Skeleton landmarks (metres, origin at feet, +X = character left, -Y = front)
# Values measured from the normalised source mesh.
# --------------------------------------------------------------------------
CENTER_BONES = [
    # name,     head,               tail,               parent,  connect, deform
    ("Root",   (0.0, 0.0, 0.00),   (0.0, 0.0, 0.12),   None,    False, False),
    ("Hips",   (0.0, 0.0, 0.895),  (0.0, 0.0, 1.00),   "Root",  False, True),
    ("Spine",  (0.0, 0.0, 1.00),   (0.0, 0.0, 1.13),   "Hips",  True,  True),
    ("Chest",  (0.0, 0.0, 1.13),   (0.0, 0.0, 1.30),   "Spine", True,  True),
    ("Neck",   (0.0, 0.0, 1.30),   (0.0, 0.0, 1.42),   "Chest", True,  True),
    ("Head",   (0.0, 0.0, 1.42),   (0.0, 0.0, 1.72),   "Neck",  True,  True),
]

LEFT_BONES = [
    # name,         head,                    tail,                     parent,       connect
    ("Shoulder.L", (0.035, 0.0, 1.265),     (0.145, 0.0, 1.25),       "Chest",      False),
    ("UpperArm.L", (0.145, 0.0, 1.25),      (0.475, 0.005, 1.35),     "Shoulder.L", True),
    ("LowerArm.L", (0.475, 0.005, 1.35),    (0.815, -0.085, 1.42),    "UpperArm.L", True),
    ("Hand.L",     (0.815, -0.085, 1.42),   (0.925, -0.13, 1.43),     "LowerArm.L", True),
    ("UpperLeg.L", (0.0992, 0.001, 0.88),   (0.0992, 0.0, 0.49),      "Hips",       False),
    ("LowerLeg.L", (0.0992, 0.0, 0.49),     (0.0992, 0.0, 0.19),      "UpperLeg.L", True),
    ("Foot.L",     (0.0992, 0.0, 0.19),     (0.0992, -0.14, 0.045),   "LowerLeg.L", True),
]

# Weighting chains (bone order bottom/root -> top/tip, boundaries increasing)
BODY_Z_CHAIN = ["Foot", "LowerLeg", "UpperLeg", "Hips", "Spine", "Chest", "Neck", "Head"]
BODY_Z_BOUNDS = [
    (0.19, 0.045),  # ankle
    (0.49, 0.055),  # knee
    (0.88, 0.05),   # hip
    (0.99, 0.05),   # hips / spine
    (1.12, 0.05),   # spine / chest
    (1.30, 0.045),  # chest / neck
    (1.34, 0.04),   # neck / head
]
ARM_CHAIN = ["Shoulder", "UpperArm", "LowerArm", "Hand"]
ARM_X_BOUNDS = [
    (0.185, 0.05),  # shoulder ring / upper arm
    (0.475, 0.055),  # elbow
    (0.82, 0.05),  # wrist
]
ARM_Z_MIN = 1.14   # arm geometry starts above this height
ARM_AX_MIN = 0.13  # torso half-width is below this


def log(message):
    print(message, flush=True)


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def chain_weights(value, bones, bounds):
    """Linear/smooth blend along an ordered bone chain of len(bounds)+1 bones."""
    for i, (pos, half) in enumerate(bounds):
        lo, hi = pos - half, pos + half
        if value < lo:
            return {bones[i]: 1.0}
        if value <= hi:
            t = smoothstep((value - lo) / (hi - lo))
            return {bones[i]: 1.0 - t, bones[i + 1]: t}
    return {bones[-1]: 1.0}


def region_weight(x, y, z):
    """Deterministic bounded-region weights for one vertex (normalised)."""
    ax = abs(x)
    if z >= ARM_Z_MIN and ax > ARM_AX_MIN:
        side = "L" if x >= 0.0 else "R"
        names = ["{}.{}".format(b, side) for b in ARM_CHAIN]
        return chain_weights(ax, names, ARM_X_BOUNDS)
    if z < 0.88 and ax < 1e-6:
        return {"Hips": 0.5, "UpperLeg.L": 0.25, "UpperLeg.R": 0.25}
    side = "L" if x >= 0.0 else "R"
    names = [BodyName(fmt, side) for fmt in BODY_Z_CHAIN]
    return chain_weights(z, names, BODY_Z_BOUNDS)


def BodyName(fmt, side):
    return fmt if fmt in ("Hips", "Spine", "Chest", "Neck", "Head") else "{}.{}".format(fmt, side)


def bone_table():
    table = list(CENTER_BONES)
    for name, head, tail, parent, connect in LEFT_BONES:
        table.append((name, head, tail, parent, bool(connect), True))
        right_parent = parent[:-2] + ".R" if parent.endswith(".L") else parent
        table.append((name[:-2] + ".R", (-head[0], head[1], head[2]),
                      (-tail[0], tail[1], tail[2]), right_parent, bool(connect), True))
    return table


def bounds_of(points):
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    return [round(min(xs), 5), round(min(ys), 5), round(min(zs), 5),
            round(max(xs), 5), round(max(ys), 5), round(max(zs), 5)]


def classify_material(mat):
    name = mat.name.lower()
    if name.startswith("top"):
        return "SHIRT"
    if name.startswith("shoe"):
        return "SHOE"
    if name.startswith("pants"):
        color = mat.diffuse_color
        if color[0] > color[1] > color[2] and color[0] > 0.4:
            return "SKIN"  # tan material used by head + hands
        return "PANTS"
    return "OTHER"


def import_source():
    if not os.path.isfile(SOURCE_FBX):
        raise RuntimeError("source FBX not found: {}".format(SOURCE_FBX))
    bpy.ops.import_scene.fbx(filepath=SOURCE_FBX)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("no mesh imported from {}".format(SOURCE_FBX))
    mesh_obj = max(meshes, key=lambda o: len(o.data.vertices))
    for extra in [o for o in bpy.data.objects if o.type == "MESH" and o is not mesh_obj]:
        bpy.data.objects.remove(extra, do_unlink=True)
    mesh_obj.name = MESH_OBJECT_NAME
    mesh_obj.data.name = MESH_OBJECT_NAME + "_Mesh"
    return mesh_obj


def bake_and_normalise(mesh_obj):
    me = mesh_obj.data
    me.transform(mesh_obj.matrix_world)
    mesh_obj.matrix_world = Matrix.Identity(4)
    points = [v.co.copy() for v in me.vertices]
    bb = bounds_of(points)
    raw_height = bb[5] - bb[2]
    if raw_height <= 1e-6:
        raise RuntimeError("degenerate source mesh height")
    scale = TARGET_HEIGHT / raw_height
    centre = Vector(((bb[0] + bb[3]) * 0.5, (bb[1] + bb[4]) * 0.5, bb[2]))
    me.transform(Matrix.Diagonal((scale, scale, scale, 1.0)) @ Matrix.Translation(-centre))
    me.update()
    return {
        "raw_height": round(raw_height, 5),
        "scale_factor": round(scale, 6),
        "bounds_before": bb,
        "bounds_after": bounds_of([v.co for v in me.vertices]),
    }


def expand_torso(mesh_obj, role_sets):
    """Slightly expand + round only the shirt torso vertices (topology kept)."""
    me = mesh_obj.data
    coords = [v.co.copy() for v in me.vertices]
    torso = []
    for i, p in enumerate(coords):
        r = math.hypot(p.x, p.y)
        if ("SHIRT" in role_sets[i] and TORSO_Z_LO <= p.z <= TORSO_Z_HI
                and abs(p.x) < TORSO_MAX_AX and r < TORSO_MAX_R):
            torso.append(i)

    radii = {}
    for i in torso:
        z = coords[i].z
        near = [math.hypot(coords[j].x, coords[j].y) for j in torso
                if abs(coords[j].z - z) <= 0.03]
        radii[i] = sum(near) / len(near) if near else 0.15

    moved = 0
    max_shift = 0.0
    for i in torso:
        p = coords[i]
        r = math.hypot(p.x, p.y)
        if r < 1e-6:
            continue
        w = (smoothstep((p.z - TORSO_RAMP_IN[0]) / (TORSO_RAMP_IN[1] - TORSO_RAMP_IN[0]))
             * (1.0 - smoothstep((p.z - TORSO_RAMP_OUT[0]) / (TORSO_RAMP_OUT[1] - TORSO_RAMP_OUT[0]))))
        if w <= 1e-6:
            continue
        r_ref = radii[i]
        k = TORSO_ROUND * w
        a = TORSO_EXPAND * w
        if r > 0.4 * r_ref:
            r_new = (r * (1.0 - k) + r_ref * k) * (1.0 + a)
        else:
            r_new = r * (1.0 + a)
        factor = r_new / r
        new = Vector((p.x * factor, p.y * factor, p.z))
        max_shift = max(max_shift, (new - p).length)
        me.vertices[i].co = new
        moved += 1
    me.update()
    return {"vertices_moved": moved, "torso_vertices": len(torso),
            "max_displacement": round(max_shift, 5)}


def build_armature():
    arm_data = bpy.data.armatures.new("Player_01_Armature")
    arm_obj = bpy.data.objects.new(ARMATURE_OBJECT_NAME, arm_data)
    bpy.context.scene.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = {}
    for name, head, tail, parent, connect, deform in bone_table():
        bone = arm_data.edit_bones.new(name)
        bone.head = Vector(head)
        bone.tail = Vector(tail)
        bone.roll = 0.0
        if parent is not None:
            bone.parent = edit_bones[parent]
            bone.use_connect = connect
        bone.use_deform = deform
        edit_bones[name] = bone
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def deform_bone_names(arm_obj):
    return [b.name for b in arm_obj.data.bones if b.use_deform]


def assess_weights(mesh_obj, arm_obj):
    deform = set(deform_bone_names(arm_obj))
    group_names = {g.index: g.name for g in mesh_obj.vertex_groups if g.name in deform}
    unweighted = 0
    cross_side = 0
    side_checked = 0
    max_influences = 0
    sums = []
    for vert in mesh_obj.data.vertices:
        total = 0.0
        best_name = None
        best_weight = -1.0
        influences = 0
        for entry in vert.groups:
            name = group_names.get(entry.group)
            if name is None:
                continue
            influences += 1
            total += entry.weight
            if entry.weight > best_weight:
                best_weight, best_name = entry.weight, name
        max_influences = max(max_influences, influences)
        sums.append(total)
        if total <= 1e-6:
            unweighted += 1
        if best_name is not None and abs(vert.co.x) > 0.25 and best_name[-2:] in (".L", ".R"):
            side_checked += 1
            wanted = ".L" if vert.co.x > 0.0 else ".R"
            if not best_name.endswith(wanted):
                cross_side += 1
    ok = unweighted == 0 and (side_checked == 0 or cross_side / side_checked <= 0.02)
    return {
        "ok": ok,
        "unweighted": unweighted,
        "cross_side": cross_side,
        "side_checked": side_checked,
        "max_influences": max_influences,
        "min_weight_sum": round(min(sums), 6),
        "max_weight_sum": round(max(sums), 6),
    }


def try_automatic_weights(mesh_obj, arm_obj):
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    try:
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
    except Exception as exc:  # bone heat can fail on disconnected low-poly parts
        return {"ok": False, "error": repr(exc)}
    return assess_weights(mesh_obj, arm_obj)


def ensure_armature_modifier(mesh_obj, arm_obj):
    modifier = next((m for m in mesh_obj.modifiers if m.type == "ARMATURE"), None)
    if modifier is None:
        modifier = mesh_obj.modifiers.new("Armature", "ARMATURE")
    modifier.object = arm_obj
    if mesh_obj.parent is None:
        mesh_obj.parent = arm_obj
        mesh_obj.matrix_parent_inverse = Matrix.Identity(4)


def apply_region_weights(mesh_obj, arm_obj):
    for group in list(mesh_obj.vertex_groups):
        mesh_obj.vertex_groups.remove(group)
    groups = {name: mesh_obj.vertex_groups.new(name=name)
              for name in deform_bone_names(arm_obj)}
    used = set()
    for vert in mesh_obj.data.vertices:
        for name, weight in region_weight(vert.co.x, vert.co.y, vert.co.z).items():
            if weight > 1e-4 and name in groups:
                groups[name].add([vert.index], weight, "REPLACE")
                used.add(name)
    return {"groups_used": len(used), "groups_total": len(groups)}


def normalise_weights(mesh_obj, arm_obj):
    deform = set(deform_bone_names(arm_obj))
    group_names = {g.index: g.name for g in mesh_obj.vertex_groups if g.name in deform}
    fixed = 0
    for vert in mesh_obj.data.vertices:
        entries = [(entry.group, entry.weight) for entry in vert.groups
                   if entry.group in group_names]
        total = sum(weight for _, weight in entries)
        if total <= 1e-8:
            for name, weight in region_weight(vert.co.x, vert.co.y, vert.co.z).items():
                group = mesh_obj.vertex_groups.get(name)
                if group is not None and weight > 1e-4:
                    group.add([vert.index], weight, "REPLACE")
            fixed += 1
            continue
        if abs(total - 1.0) > 1e-9:
            for group_index, weight in entries:
                mesh_obj.vertex_groups[group_index].add(
                    [vert.index], weight / total, "REPLACE")
    return {"renormalised": True, "rescued_vertices": fixed}


def export_fbx(mesh_obj, arm_obj):
    os.makedirs(os.path.dirname(FBX_OUT), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    mesh_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    kwargs = dict(
        filepath=FBX_OUT,
        use_selection=True,
        object_types={"ARMATURE", "MESH"},
        axis_forward="-Z",
        axis_up="Y",
        apply_scale_options="FBX_SCALE_NONE",
        add_leaf_bones=False,
        bake_anim=False,
        mesh_smooth_type="FACE",
    )
    try:
        bpy.ops.export_scene.fbx(**kwargs)
    except TypeError:
        bpy.ops.export_scene.fbx(filepath=FBX_OUT, use_selection=True,
                                 add_leaf_bones=False, bake_anim=False)


def preservation_checks(coords_before, role_sets):
    """Confirm head/hands/legs/feet coordinates are untouched by the expansion."""
    regions = {"head": [], "hands": [], "legs_feet": []}
    for i, p in enumerate(coords_before):
        if abs(p.x) > 0.70:
            regions["hands"].append(i)
        elif p.z > 1.30 and abs(p.x) < 0.30:
            regions["head"].append(i)
        elif p.z < 0.86:
            regions["legs_feet"].append(i)
    return regions


def main():
    report = {"task_id": TASK_ID, "ok": False, "blender": bpy.app.version_string,
              "source": SOURCE_FBX, "blend_out": BLEND_OUT, "fbx_out": FBX_OUT,
              "caveats": []}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0  # no .blend1 backups

    mesh_obj = import_source()
    me = mesh_obj.data
    report["source_mesh"] = {
        "object": mesh_obj.name,
        "vertices": len(me.vertices),
        "polygons": len(me.polygons),
        "triangles": sum(len(p.vertices) - 2 for p in me.polygons),
        "materials": [m.name if m else None for m in me.materials],
    }

    report["normalisation"] = bake_and_normalise(mesh_obj)

    # role set per vertex (from face materials)
    roles = [classify_material(m) for m in me.materials]
    role_sets = [set() for _ in me.vertices]
    for poly in me.polygons:
        if poly.material_index < len(roles):
            role = roles[poly.material_index]
            for vi in poly.vertices:
                role_sets[vi].add(role)
    report["material_roles"] = {m.name: r for m, r in zip(me.materials, roles)}

    coords_before = [v.co.copy() for v in me.vertices]
    regions = preservation_checks(coords_before, role_sets)
    bounds_before = {name: bounds_of([coords_before[i] for i in ids])
                     for name, ids in regions.items()}

    report["torso_expansion"] = expand_torso(mesh_obj, role_sets)
    for poly in me.polygons:
        poly.use_smooth = False
    me.update()

    coords_after = [v.co for v in me.vertices]
    report["preservation"] = {
        "head_bounds_before": bounds_before["head"],
        "head_bounds_after": bounds_of([coords_after[i] for i in regions["head"]]),
        "hands_bounds_before": bounds_before["hands"],
        "hands_bounds_after": bounds_of([coords_after[i] for i in regions["hands"]]),
        "legs_feet_bounds_before": bounds_before["legs_feet"],
        "legs_feet_bounds_after": bounds_of([coords_after[i] for i in regions["legs_feet"]]),
        "max_abs_z_change": round(max(abs(coords_after[i].z - coords_before[i].z)
                                      for i in range(len(coords_before))), 8),
    }

    arm_obj = build_armature()
    report["rig"] = {
        "object": arm_obj.name,
        "bones": [b.name for b in arm_obj.data.bones],
        "bone_count": len(arm_obj.data.bones),
        "deform_bones": deform_bone_names(arm_obj),
    }

    auto = try_automatic_weights(mesh_obj, arm_obj)
    if auto.get("ok"):
        method = "automatic"
        ensure_armature_modifier(mesh_obj, arm_obj)
    else:
        method = "bounded_region"
        ensure_armature_modifier(mesh_obj, arm_obj)
        auto["fallback"] = apply_region_weights(mesh_obj, arm_obj)
    report["skinning"] = {
        "method": method,
        "automatic_assessment": auto,
        "normalisation": normalise_weights(mesh_obj, arm_obj),
        "final_assessment": assess_weights(mesh_obj, arm_obj),
        "vertex_groups": len(mesh_obj.vertex_groups),
    }

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = mesh_obj
    mesh_obj.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_OUT, check_existing=False, compress=False)
    export_fbx(mesh_obj, arm_obj)

    report["outputs"] = {
        "blend_bytes": os.path.getsize(BLEND_OUT) if os.path.isfile(BLEND_OUT) else 0,
        "fbx_bytes": os.path.getsize(FBX_OUT) if os.path.isfile(FBX_OUT) else 0,
        "mesh_dimensions": {
            "x": round(max(v.co.x for v in me.vertices) - min(v.co.x for v in me.vertices), 5),
            "y": round(max(v.co.y for v in me.vertices) - min(v.co.y for v in me.vertices), 5),
            "z": round(max(v.co.z for v in me.vertices) - min(v.co.z for v in me.vertices), 5),
        },
        "mesh_bounds_final": bounds_of([v.co for v in me.vertices]),
    }

    hard_fail = False
    if len(regions["head"]) and report["preservation"]["head_bounds_before"] != report["preservation"]["head_bounds_after"]:
        hard_fail = True
    if (report["preservation"]["legs_feet_bounds_before"]
            != report["preservation"]["legs_feet_bounds_after"]):
        hard_fail = True
    if not report["skinning"]["final_assessment"]["ok"]:
        hard_fail = True
    if not os.path.isfile(BLEND_OUT) or not os.path.isfile(FBX_OUT):
        hard_fail = True

    report["ok"] = not hard_fail
    if hard_fail:
        report["caveats"].append("hard acceptance check failed")
    log("BUILD_REPORT=" + json.dumps(report))
    if hard_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
