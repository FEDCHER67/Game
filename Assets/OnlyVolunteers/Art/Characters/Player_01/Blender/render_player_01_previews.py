"""PLAYER-CHAR-003 - honest neutral and posed approval previews for Player_01.

Run headless:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --python render_player_01_previews.py

Reads (never modified):
    Player_01.blend                  existing rigged low-poly character

Writes (exact owned outputs, nothing else):
    ../Preview/Player_01_Front.png
    ../Preview/Player_01_Side.png
    ../Preview/Player_01_ThreeQuarter.png
    ../Preview/Player_01_Back.png
    ../Preview/Player_01_Wireframe.png
    ../Preview/Player_01_Rig.png
    ../Preview/Player_01_BentArmLeg.png
    ../Preview/Player_01_Crouch.png
    ../Preview/pose_validation.json

Prints one line:  PREVIEW_REPORT=<json>

Design notes:
  * Workbench engine, orthographic camera, light neutral background, flat
    material colours: honest previews without perspective tricks, shared
    framing so every image shows the model at a comparable scale.
  * Wireframe preview renders the solid mesh plus a black wireframe shell
    (Wireframe modifier, replaced faces, slightly offset outward) so mesh
    edges stay readable without hiding the solid silhouette.
  * Rig preview renders the solid mesh plus octahedral bone markers and an
    origin axis triad, pushed in front of the model along the camera axis so
    the skeleton stays legible over the solid body. This is a legibility
    overlay, not a depth-correct x-ray render.
  * Poses use bone-local Euler rotations (all bones were authored with roll 0),
    the rest pose is restored and re-checked before every pose, and every pose
    is evaluated through the depsgraph for finite-coordinate, bounds and
    extent-explosion checks.
  * The .blend and the FBX are never saved.
"""

import json
import math
import os

import bpy
from mathutils import Vector

TASK_ID = "PLAYER-CHAR-003"
HERE = os.path.dirname(os.path.abspath(__file__))
PLAYER_DIR = os.path.normpath(os.path.join(HERE, ".."))
PREVIEW_DIR = os.path.join(PLAYER_DIR, "Preview")
BLEND_IN = os.path.join(HERE, "Player_01.blend")

MESH_OBJECT_NAME = "Player_01"
ARMATURE_OBJECT_NAME = "Armature"
RESOLUTION = 1024
BACKGROUND_COLOR = (0.86, 0.86, 0.86)
MAX_EXTENT_RATIO = 1.6          # no catastrophic extent explosion
MIN_POSE_DISPLACEMENT = 0.03    # a pose must actually deform the mesh (m)
REST_EPSILON = 1e-5             # rest pose restoration tolerance (m)
MAX_ABS_COORDINATE = 5.0        # sanity ceiling for any evaluated coordinate (m)

AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}

VIEWS = {
    "front": Vector((0.0, -1.0, 0.0)),          # camera on -Y, character faces -Y
    "side": Vector((1.0, 0.0, 0.0)),            # camera on +X (character left)
    "three_quarter": Vector((0.65, -0.8, 0.0)),  # front / +X
    "back": Vector((0.0, 1.0, 0.0)),            # camera on +Y
}

NEUTRAL_VIEW_IMAGES = (
    ("Player_01_Front.png", "front"),
    ("Player_01_Side.png", "side"),
    ("Player_01_ThreeQuarter.png", "three_quarter"),
    ("Player_01_Back.png", "back"),
)

POSE_TESTS = (
    {
        "name": "BentArmLeg",
        "image": "Player_01_BentArmLeg.png",
        "view": "three_quarter",
        # Left arm: shoulder lowered, elbow flexed up; left leg: hip and knee flexed.
        "bones": (
            {"bone": "UpperArm.L", "axis": "X", "degrees": -40.0},
            {"bone": "LowerArm.L", "axis": "X", "degrees": 75.0},
            {"bone": "UpperLeg.L", "axis": "X", "degrees": -45.0},
            {"bone": "LowerLeg.L", "axis": "X", "degrees": 80.0},
            {"bone": "Foot.L", "axis": "X", "degrees": -25.0},
        ),
    },
    {
        "name": "Crouch",
        "image": "Player_01_Crouch.png",
        "view": "side",
        # Hips dropped 0.25 m; hips, knees and ankles bent into a squat with the
        # feet kept close to the original ground plane.
        "bones": (
            {"bone": "Root", "axis": "Y", "degrees": 0.0, "location": (0.0, -0.25, 0.0)},
            {"bone": "UpperLeg.L", "axis": "X", "degrees": -55.0},
            {"bone": "UpperLeg.R", "axis": "X", "degrees": -55.0},
            {"bone": "LowerLeg.L", "axis": "X", "degrees": 95.0},
            {"bone": "LowerLeg.R", "axis": "X", "degrees": 95.0},
            {"bone": "Foot.L", "axis": "X", "degrees": -40.0},
            {"bone": "Foot.R", "axis": "X", "degrees": -40.0},
        ),
    },
)

JOINT_REPORT = ("Hips", "Head", "Hand.L", "Hand.R", "Foot.L", "Foot.R")


def log(message):
    print(message, flush=True)


def round_vec(vector, digits=5):
    return [round(float(value), digits) for value in vector]


def points_bounds(points):
    finite = [p for p in points if all(math.isfinite(c) for c in p)]
    if not finite:
        return None
    low = [min(p[i] for p in finite) for i in range(3)]
    high = [max(p[i] for p in finite) for i in range(3)]
    return {"min": round_vec(low), "max": round_vec(high),
            "size": round_vec([high[i] - low[i] for i in range(3)])}


def evaluated_points(mesh_obj):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = mesh_obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    matrix = eval_obj.matrix_world
    points = [matrix @ vertex.co for vertex in mesh.vertices]
    eval_obj.to_mesh_clear()
    return points


def mesh_checks(points, rest_points):
    non_finite_values = sum(1 for p in points for c in p if not math.isfinite(c))
    bounds = points_bounds(points)
    displacements = [0.0]
    if len(points) == len(rest_points):
        displacements = [(p - r).length for p, r in zip(points, rest_points)
                         if all(math.isfinite(c) for c in p)]
    max_displacement = max(displacements) if displacements else float("inf")
    rest_size = points_bounds(rest_points)
    extent_ratio = None
    if bounds is not None and rest_size is not None:
        rest_max = max(rest_size["size"])
        if rest_max > 1e-9:
            extent_ratio = round(max(bounds["size"]) / rest_max, 5)
    max_abs = max((abs(c) for p in points for c in p if math.isfinite(c)), default=0.0)
    reasons = []
    if non_finite_values:
        reasons.append("non-finite evaluated vertex coordinates: {}".format(non_finite_values))
    if bounds is None:
        reasons.append("no finite evaluable vertex coordinates")
    if extent_ratio is not None and extent_ratio > MAX_EXTENT_RATIO:
        reasons.append("extent ratio {:.3f} exceeds {:.2f}".format(extent_ratio, MAX_EXTENT_RATIO))
    if max_abs > MAX_ABS_COORDINATE:
        reasons.append("coordinate magnitude {:.3f} exceeds {:.2f}".format(max_abs, MAX_ABS_COORDINATE))
    return {
        "vertices_checked": len(points),
        "non_finite_values": non_finite_values,
        "finite_coordinates_ok": non_finite_values == 0,
        "bounds_m": bounds,
        "max_abs_coordinate_m": round(max_abs, 5),
        "max_vertex_displacement_m": round(max_displacement, 5),
        "extent_ratio_vs_rest": extent_ratio,
        "ok": not reasons,
        "reasons": reasons,
    }


def reset_pose(arm_obj):
    for pose_bone in arm_obj.pose.bones:
        pose_bone.location = (0.0, 0.0, 0.0)
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler = (0.0, 0.0, 0.0)
        pose_bone.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pose_bone.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


def apply_pose(arm_obj, bone_entries):
    reset_pose(arm_obj)
    for entry in bone_entries:
        pose_bone = arm_obj.pose.bones[entry["bone"]]
        if "location" in entry:
            pose_bone.location = entry["location"]
        pose_bone.rotation_mode = "XYZ"
        pose_bone.rotation_euler[AXIS_INDEX[entry["axis"]]] += math.radians(entry["degrees"])
    bpy.context.view_layer.update()


def joint_positions(arm_obj):
    return {name: round_vec(arm_obj.matrix_world @ arm_obj.pose.bones[name].tail)
            for name in JOINT_REPORT}


def configure_scene(scene):
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = RESOLUTION
    scene.render.resolution_y = RESOLUTION
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 15
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.use_nodes = False

    scene.display.render_aa = "16"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = False
    shading.show_cavity = False
    shading.show_object_outline = False
    shading.show_specular_highlight = False
    shading.show_backface_culling = False
    shading.background_type = "VIEWPORT"
    shading.background_color = BACKGROUND_COLOR

    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def make_camera(scene, center, size):
    camera_data = bpy.data.cameras.new("Player_01 preview camera")
    camera_data.type = "ORTHO"
    span = max(size.x, size.y, size.z, 0.1)
    camera_data.ortho_scale = max(size.z * 1.30, size.x * 1.35, size.y * 1.35, 0.5)
    camera_obj = bpy.data.objects.new("Player_01 preview camera", camera_data)
    scene.collection.objects.link(camera_obj)
    scene.camera = camera_obj
    return camera_obj, span * 3.0


def aim_camera(camera_obj, center, distance, direction):
    direction = direction.normalized()
    camera_obj.location = center + direction * distance
    camera_obj.rotation_euler = (center - camera_obj.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return direction


def render_to(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    log("RENDERED " + path)
    return os.path.isfile(path)


def new_material(name, rgba):
    material = bpy.data.materials.new(name)
    material.diffuse_color = rgba
    return material


def build_polygon_mesh(name, vertices, faces, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in vertices], [], faces)
    mesh.validate()
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    mesh.materials.append(material)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def octahedron(head, tail, radius_scale=0.15):
    direction = tail - head
    length = direction.length
    if length < 1e-6:
        return [], []
    direction.normalize()
    reference = Vector((0.0, 0.0, 1.0)) if abs(direction.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    side_u = direction.cross(reference).normalized()
    side_v = direction.cross(side_u).normalized()
    radius = min(max(length * radius_scale, 0.012), 0.055)
    ring = head + direction * (length * 0.15)
    vertices = [head, tail,
                ring + side_u * radius, ring + side_v * radius,
                ring - side_u * radius, ring - side_v * radius]
    faces = [(0, 2, 3), (0, 3, 4), (0, 4, 5), (0, 5, 2),
             (1, 3, 2), (1, 4, 3), (1, 5, 4), (1, 2, 5)]
    return vertices, faces


def box(center, size):
    cx, cy, cz = center
    hx, hy, hz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    vertices = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
                (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz),
                (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
                (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
             (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return vertices, faces


def build_wireframe_overlay(scene, mesh_obj):
    """Black wireframe shell over the solid mesh (solid silhouette kept)."""
    wire_obj = mesh_obj.copy()
    wire_obj.data = mesh_obj.data.copy()
    wire_obj.name = "Player_01__wire_overlay"
    wire_obj.data.name = "Player_01__wire_overlay_mesh"
    scene.collection.objects.link(wire_obj)
    modifier = wire_obj.modifiers.new("Wireframe overlay", "WIREFRAME")
    modifier.thickness = 0.007
    modifier.offset = 1.0
    modifier.use_replace = True
    modifier.use_even_offset = True
    black = new_material("Player_01__wire_black", (0.02, 0.02, 0.02, 1.0))
    wire_obj.data.materials.clear()
    wire_obj.data.materials.append(black)
    for polygon in wire_obj.data.polygons:
        polygon.material_index = 0
    wire_obj.hide_render = False
    wire_obj.hide_viewport = False
    return [wire_obj]


def build_rig_overlay(scene, arm_obj, direction, push):
    """Octahedral bone markers + origin axis triad, pushed toward the camera."""
    offset = direction.normalized() * push
    bone_material = new_material("Player_01__rig_bone", (1.0, 0.35, 0.05, 1.0))
    bone_vertices = []
    bone_faces = []
    for bone in arm_obj.data.bones:
        head = (arm_obj.matrix_world @ bone.head_local) + offset
        tail = (arm_obj.matrix_world @ bone.tail_local) + offset
        vertices, faces = octahedron(head, tail)
        base = len(bone_vertices)
        bone_vertices.extend(vertices)
        bone_faces.extend([tuple(index + base for index in face) for face in faces])
    objects = [build_polygon_mesh("Player_01__rig_bones", bone_vertices, bone_faces, bone_material)]

    axis_specs = (
        ("x", (1.0, 0.1, 0.1, 1.0), Vector((1.0, 0.0, 0.0))),
        ("y", (0.1, 0.65, 0.15, 1.0), Vector((0.0, 1.0, 0.0))),
        ("z", (0.15, 0.35, 0.95, 1.0), Vector((0.0, 0.0, 1.0))),
    )
    for name, color, axis in axis_specs:
        start = Vector((0.0, 0.0, 0.0)) + offset
        end = Vector((0.0, 0.0, 0.0)) + axis * 0.28 + offset
        center = (start + end) * 0.5
        size = [0.022, 0.022, 0.022]
        size[AXIS_INDEX[name.upper()]] = 0.20
        vertices, faces = box(center, size)
        objects.append(build_polygon_mesh("Player_01__axis_" + name, vertices, faces,
                                          new_material("Player_01__axis_" + name + "_mat", color)))
    return objects


def remove_objects(objects):
    for obj in objects:
        mesh = obj.data
        for material in list(mesh.materials):
            bpy.data.materials.remove(material)
        bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.meshes.remove(mesh)


def main():
    report = {
        "task_id": TASK_ID,
        "blender": bpy.app.version_string,
        "blend": BLEND_IN,
        "images": [],
        "poses": [],
        "caveats": [],
        "ok": False,
    }
    if not os.path.isfile(BLEND_IN):
        raise RuntimeError("blend not found: {}".format(BLEND_IN))
    bpy.ops.wm.open_mainfile(filepath=BLEND_IN)
    scene = bpy.context.scene
    mesh_obj = bpy.data.objects.get(MESH_OBJECT_NAME)
    arm_obj = bpy.data.objects.get(ARMATURE_OBJECT_NAME)
    if mesh_obj is None or mesh_obj.type != "MESH":
        raise RuntimeError("mesh object not found: {}".format(MESH_OBJECT_NAME))
    if arm_obj is None or arm_obj.type != "ARMATURE":
        raise RuntimeError("armature object not found: {}".format(ARMATURE_OBJECT_NAME))

    os.makedirs(PREVIEW_DIR, exist_ok=True)
    configure_scene(scene)

    pose_was_identity = all(
        pose_bone.location.length < 1e-9
        and abs(pose_bone.rotation_euler.x) < 1e-9
        and abs(pose_bone.rotation_euler.y) < 1e-9
        and abs(pose_bone.rotation_euler.z) < 1e-9
        and abs(pose_bone.scale.x - 1.0) < 1e-9
        for pose_bone in arm_obj.pose.bones)
    reset_pose(arm_obj)

    base_mesh = mesh_obj.data
    report.update({
        "mesh_object": mesh_obj.name,
        "armature_object": arm_obj.name,
        "armature_data": arm_obj.data.name,
        "pose_position": arm_obj.data.pose_position,
        "pose_transforms_initially_identity": pose_was_identity,
        "vertices": len(base_mesh.vertices),
        "triangles": sum(len(polygon.vertices) - 2 for polygon in base_mesh.polygons),
        "materials": [material.name if material else None for material in base_mesh.materials],
        "bones": [bone.name for bone in arm_obj.data.bones],
        "deform_bones": [bone.name for bone in arm_obj.data.bones if bone.use_deform],
    })

    rest_points = evaluated_points(mesh_obj)
    rest_bounds = points_bounds(rest_points)
    report["vertex_groups"] = len(mesh_obj.vertex_groups)
    report["rest"] = {
        "bounds_m": rest_bounds,
        "checks": mesh_checks(rest_points, rest_points),
        "joints_m": joint_positions(arm_obj),
    }
    rest_size = Vector(rest_bounds["size"])
    center = Vector(((rest_bounds["min"][0] + rest_bounds["max"][0]) * 0.5,
                     (rest_bounds["min"][1] + rest_bounds["max"][1]) * 0.5,
                     (rest_bounds["min"][2] + rest_bounds["max"][2]) * 0.5))
    camera_obj, camera_distance = make_camera(scene, center, rest_size)
    report["camera"] = {
        "type": camera_obj.data.type,
        "ortho_scale_m": round(camera_obj.data.ortho_scale, 5),
        "distance_m": round(camera_distance, 5),
    }

    neutral_written = []
    for image_name, view_name in NEUTRAL_VIEW_IMAGES:
        direction = aim_camera(camera_obj, center, camera_distance, VIEWS[view_name])
        path = os.path.join(PREVIEW_DIR, image_name)
        render_to(scene, path)
        neutral_written.append(os.path.isfile(path))
        report["images"].append({"file": image_name, "view": view_name,
                                 "camera_direction": round_vec(direction)})

    # Wireframe over solid (rest pose, three-quarter view).
    direction = aim_camera(camera_obj, center, camera_distance, VIEWS["three_quarter"])
    overlay = build_wireframe_overlay(scene, mesh_obj)
    wire_path = os.path.join(PREVIEW_DIR, "Player_01_Wireframe.png")
    render_to(scene, wire_path)
    remove_objects(overlay)
    neutral_written.append(os.path.isfile(wire_path))
    report["images"].append({"file": "Player_01_Wireframe.png", "view": "three_quarter",
                             "camera_direction": round_vec(direction),
                             "overlay": "solid mesh + black Wireframe modifier shell (offset outward)"})

    # Skeleton over solid (rest pose, front view).
    direction = aim_camera(camera_obj, center, camera_distance, VIEWS["front"])
    push = max((point - center).dot(direction) for point in rest_points) + 0.25
    overlay = build_rig_overlay(scene, arm_obj, direction, push)
    rig_path = os.path.join(PREVIEW_DIR, "Player_01_Rig.png")
    render_to(scene, rig_path)
    remove_objects(overlay)
    neutral_written.append(os.path.isfile(rig_path))
    report["images"].append({"file": "Player_01_Rig.png", "view": "front",
                             "camera_direction": round_vec(direction),
                             "overlay": "octahedral bone markers for all 20 bones + origin RGB axis triad, "
                                        "pushed {:.3f} m toward the camera for legibility".format(push)})
    report["caveats"].append("rig preview bones are pushed toward the camera so they stay visible "
                             "over the solid body; the image is a legibility overlay, not x-ray depth")

    pose_failures = []
    for pose in POSE_TESTS:
        # Restore the rest pose first, then prove it was restored.
        reset_pose(arm_obj)
        restored_points = evaluated_points(mesh_obj)
        restored_delta = max(((a - b).length for a, b in zip(restored_points, rest_points)), default=0.0)
        rest_restored = restored_delta < REST_EPSILON

        apply_pose(arm_obj, pose["bones"])
        posed_points = evaluated_points(mesh_obj)
        checks = mesh_checks(posed_points, rest_points)
        checks["rest_restored_before_pose"] = rest_restored
        checks["rest_restore_delta_m"] = round(restored_delta, 8)
        if not rest_restored:
            checks["reasons"].append("rest pose was not restored before pose")
        if checks["max_vertex_displacement_m"] < MIN_POSE_DISPLACEMENT:
            checks["reasons"].append(
                "pose displacement {:.5f} m below {:.3f} m - pose did not deform the mesh".format(
                    checks["max_vertex_displacement_m"], MIN_POSE_DISPLACEMENT))
        checks["ok"] = not checks["reasons"]

        direction = aim_camera(camera_obj, center, camera_distance, VIEWS[pose["view"]])
        path = os.path.join(PREVIEW_DIR, pose["image"])
        render_to(scene, path)
        pose_entry = {
            "name": pose["name"],
            "image": pose["image"],
            "view": pose["view"],
            "camera_direction": round_vec(direction),
            "bone_angles": [
                {key: (list(entry[key]) if isinstance(entry.get(key), tuple) else entry.get(key))
                 for key in ("bone", "axis", "degrees", "location") if key in entry}
                for entry in pose["bones"]
            ],
            "bones_posed": [entry["bone"] for entry in pose["bones"]],
            "joints_m": joint_positions(arm_obj),
            "mesh_bounds_m": checks["bounds_m"],
            "checks": checks,
        }
        report["poses"].append(pose_entry)
        report["images"].append({"file": pose["image"], "view": pose["view"],
                                 "camera_direction": round_vec(direction)})
        if not checks["ok"] or not os.path.isfile(path):
            pose_failures.append(pose["name"])

    # Restore the rest pose at the end and confirm it.
    reset_pose(arm_obj)
    final_points = evaluated_points(mesh_obj)
    final_delta = max(((a - b).length for a, b in zip(final_points, rest_points)), default=0.0)
    report["rest_restored_at_end"] = final_delta < REST_EPSILON
    report["rest_restore_delta_at_end_m"] = round(final_delta, 8)
    report["blend_saved"] = False

    written = [os.path.join(PREVIEW_DIR, name) for name, _ in NEUTRAL_VIEW_IMAGES] + [
        os.path.join(PREVIEW_DIR, "Player_01_Wireframe.png"),
        os.path.join(PREVIEW_DIR, "Player_01_Rig.png")] + [
        os.path.join(PREVIEW_DIR, pose["image"]) for pose in POSE_TESTS]
    missing = [path for path in written if not os.path.isfile(path)]
    if missing:
        report["caveats"].append("missing outputs: {}".format(missing))

    report["ok"] = (not missing
                    and not pose_failures
                    and report["rest"]["checks"]["ok"]
                    and report["rest_restored_at_end"])
    json_path = os.path.join(PREVIEW_DIR, "pose_validation.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    log("VALIDATION " + json_path)
    log("PREVIEW_REPORT=" + json.dumps({
        "ok": report["ok"],
        "images": len(written),
        "missing": missing,
        "poses": [{"name": pose["name"], "ok": pose["checks"]["ok"],
                   "max_displacement_m": pose["checks"]["max_vertex_displacement_m"],
                   "extent_ratio": pose["checks"]["extent_ratio_vs_rest"]}
                  for pose in report["poses"]],
        "rest_restored_at_end": report["rest_restored_at_end"],
    }))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
