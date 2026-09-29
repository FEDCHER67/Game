"""Finish the approved low-poly Tripo table as a Blender game prop."""
import bpy
import json
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path(r"C:\Dev\Game-main\research\TABLE-ASTRA-001")
SOURCE = ROOT / "Working" / "Tripo" / "TABLE-ASTRA-001_Tripo_Rev03.fbx"
PREVIEWS = ROOT / "Previews"
PREVIEWS.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col

geo_col = collection("TABLE_ASTRA_Geometry")
rig_col = collection("TABLE_ASTRA_Rig")
preview_col = collection("TABLE_ASTRA_Preview")

def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)

def material(name, color, roughness, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat

frame_mat = material("MAT_Frame_MatteGraphite", (0.155, 0.171, 0.184), 0.88, 0.24)
pad_mat = material("MAT_Pad_MutedBlueGray", (0.125, 0.190, 0.280), 0.91)
strap_mat = material("MAT_Straps_Charcoal", (0.040, 0.046, 0.054), 0.96)
rubber_mat = material("MAT_Wheels_DarkRubber", (0.066, 0.071, 0.078), 0.98)

bpy.ops.import_scene.fbx(filepath=str(SOURCE))
source = next(obj for obj in bpy.context.selected_objects if obj.type == "MESH")
bpy.context.view_layer.objects.active = source
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
# Source proportions: width 0.455 : length 1.0 : height 0.330.
# Target game scale: width 0.75 m : length 2.0 m : height 0.79 m.
source.scale = (1.65, 2.0, 2.4)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")
parts = [o for o in bpy.context.selected_objects if o.type == "MESH"]

def bounds(obj):
    ps = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return [[min(p[i] for p in ps), max(p[i] for p in ps)] for i in range(3)]

def center_of(box):
    return Vector([(lo + hi) / 2 for lo, hi in box])

def label(box):
    return ("Foot" if center_of(box).y > 0 else "Head") + ("_Right" if center_of(box).x > 0 else "_Left")

def empty(name, position, parent=None):
    obj = bpy.data.objects.new(name, None)
    rig_col.objects.link(obj)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.08
    if parent:
        obj.parent = parent
    obj.matrix_world = Matrix.Translation(position)
    bpy.context.view_layer.update()
    return obj

def parent_keep_world(child, parent):
    keep = child.matrix_world.copy()
    child.parent = parent
    child.matrix_world = keep

root = empty("RIG_Table_Root", (0, 0, 0))
frame = pad = foot_handle = None
straps = []
forks = {}
wheels = {}
removed_handle = False
for obj in parts:
    count = len(obj.data.vertices)
    box = bounds(obj)
    move_to(obj, geo_col)
    obj.data.materials.clear()
    if count > 1000:
        obj.name = "GEO_Frame_And_Legs"
        obj.data.materials.append(frame_mat)
        frame = obj
    elif count > 800:
        obj.name = "GEO_Padded_Top"
        obj.data.materials.append(pad_mat)
        pad = obj
    elif count > 500:
        obj.name = f"GEO_Strap_{len(straps)+1:02d}"
        obj.data.materials.append(strap_mat)
        straps.append(obj)
    elif count > 400:
        if center_of(box).y < 0:
            # Tripo hallucinated a second handle at the head end.
            bpy.data.objects.remove(obj, do_unlink=True)
            removed_handle = True
            continue
        obj.name = "GEO_Push_Handle_Foot"
        obj.data.materials.append(frame_mat)
        foot_handle = obj
    elif count > 150:
        obj.name = "GEO_Caster_Fork_" + label(box)
        obj.data.materials.append(frame_mat)
        forks[label(box)] = obj
    elif count > 50:
        obj.name = "GEO_Wheel_" + label(box)
        obj.data.materials.append(rubber_mat)
        wheels[label(box)] = obj
    else:
        raise RuntimeError(f"Unclassified Tripo island: {count} vertices, {box}")
    for face in obj.data.polygons:
        face.use_smooth = obj == pad or obj in wheels.values()

assert frame and pad and foot_handle and removed_handle
assert len(straps) == 2 and len(forks) == 4 and len(wheels) == 4
assert set(forks) == set(wheels)

for obj in (frame, pad, foot_handle, *straps):
    parent_keep_world(obj, root)

# The reconstruction omitted the low longitudinal rail visible in both side
# references. One simple beam per side makes that same rail readable from
# either long profile; their ends seat slightly inside the corner legs.
lower_braces = []
for side, x in (("Left", -0.319), ("Right", 0.319)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, 0, 0.315))
    brace = bpy.context.object
    brace.name = "GEO_Lower_Longitudinal_Brace_" + side
    brace.dimensions = (0.030, 1.790, 0.034)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    brace.data.materials.append(frame_mat)
    move_to(brace, geo_col)
    parent_keep_world(brace, root)
    lower_braces.append(brace)

rig_data = []
for key in sorted(wheels):
    fork = forks[key]
    wheel = wheels[key]
    fb, wb = bounds(fork), bounds(wheel)
    caster_origin = Vector((center_of(fb).x, center_of(fb).y, fb[2][1]))
    wheel_origin = center_of(wb)
    caster = empty("RIG_CasterSteer_" + key, caster_origin, root)
    parent_keep_world(fork, caster)
    roll = empty("RIG_WheelRoll_" + key, wheel_origin, caster)
    parent_keep_world(wheel, roll)
    radius = (wb[2][1] - wb[2][0]) / 2
    roll["roll_axis"] = "local X"
    roll["radius_m"] = round(radius, 5)
    caster["steering_axis"] = "local Z"
    rig_data.append({"position": key, "caster": caster.name, "wheel": wheel.name,
                     "roll_pivot": roll.name, "radius_m": radius,
                     "wheel_bounds": wb, "fork_bounds": fb})

import sys
sys.path.insert(0, str(ROOT / "Working"))
from caster_geometry import rebuild_casters
forks, wheels, rig_data = rebuild_casters(root, geo_col, rig_col, frame_mat, rubber_mat)
(ROOT / "Working" / "caster_geometry_validation.json").write_text(json.dumps(rig_data, indent=2), encoding="utf-8")

asset_objects = [o for o in geo_col.objects] + [o for o in rig_col.objects]
all_points = [o.matrix_world @ v.co for o in geo_col.objects for v in o.data.vertices]
global_bounds = [[min(p[i] for p in all_points), max(p[i] for p in all_points)] for i in range(3)]

def overlap(a, b):
    return [min(a[i][1], b[i][1]) - max(a[i][0], b[i][0]) for i in range(3)]

contact = {"pad_frame_overlap_m": overlap(bounds(pad), bounds(frame)),
           "foot_handle_frame_overlap_m": overlap(bounds(foot_handle), bounds(frame))}
for brace in lower_braces:
    contact["brace_frame_overlap_m_" + brace.name] = overlap(bounds(brace), bounds(frame))
for key in forks:
    socket = bpy.data.objects['GEO_Caster_Socket_' + key]
    contact['socket_frame_overlap_m_' + key] = overlap(bounds(socket), bounds(frame))
    contact['fork_socket_vertical_overlap_m_' + key] = bounds(forks[key])[2][1] - bounds(socket)[2][0]

report = {"source": str(SOURCE), "source_quad_faces": 5190,
          "extra_head_handle_removed": removed_handle,
          "global_bounds_m": global_bounds,
          "rig": rig_data, "contact_aabb_overlap_m": contact,
          "geometry_objects": len(geo_col.objects), "lower_longitudinal_braces": len(lower_braces)}
(ROOT / "Working" / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"bounds_m": global_bounds, "geometry_objects": len(geo_col.objects),
                  "caster_count": len(forks), "wheel_count": len(wheels),
                  "removed_head_handle": removed_handle}, indent=2))

# Keep source meshes and the pivot hierarchy together in the exported FBX.
bpy.ops.object.select_all(action="DESELECT")
for obj in asset_objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = root
bpy.ops.export_scene.fbx(filepath=str(ROOT / "TABLE-ASTRA-001.fbx"),
                         use_selection=True, object_types={"MESH", "EMPTY"},
                         add_leaf_bones=False, bake_anim=False,
                         apply_scale_options="FBX_SCALE_UNITS")

# Presentation scene only. None of these objects are included in the FBX.
floor_mat = material("MAT_Preview_Floor", (0.075, 0.091, 0.109), 0.94)
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.018))
floor = bpy.context.object
floor.name = "PREVIEW_Floor"
floor.data.materials.append(floor_mat)
move_to(floor, preview_col)

world = bpy.context.scene.world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.14, 0.18, 0.23, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25

def aim(obj, at):
    obj.rotation_euler = (Vector(at) - obj.location).to_track_quat("-Z", "Y").to_euler()

for name, loc, energy, size in (
    ("Key", (1.7, 0.6, 3.3), 80, 3.0),
    ("Fill", (-1.8, -0.4, 2.0), 50, 2.5),
    ("Rim", (0.0, -1.8, 2.7), 60, 2.0),
):
    bpy.ops.object.light_add(type="AREA", location=loc)
    lamp = bpy.context.object
    lamp.name = "PREVIEW_" + name
    lamp.data.energy = energy
    lamp.data.shape = "DISK"
    lamp.data.size = size
    aim(lamp, (0, 0, 0.45))
    move_to(lamp, preview_col)

bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = "PREVIEW_Camera"
camera.data.type = "ORTHO"
move_to(camera, preview_col)
bpy.context.scene.camera = camera

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 1280
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.frame_set(1)

bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "TABLE-ASTRA-001.blend"))

center = Vector([(lo + hi) / 2 for lo, hi in global_bounds])
center.z = 0.42
views = (
    ("01_front", (0.0, 3.0, 1.15)),
    ("02_left", (3.0, 0.0, 1.05)),
    ("03_right", (-3.0, 0.0, 1.05)),
    ("04_back", (0.0, -3.0, 1.15)),
    ("05_three_quarter", (2.5, 2.8, 1.9)),
    ("06_high_three_quarter", (-2.3, -2.7, 2.8)),
)
for name, direction in views:
    camera.location = center + Vector(direction)
    aim(camera, center)
    bpy.context.view_layer.update()
    right = camera.matrix_world.to_quaternion() @ Vector((1, 0, 0))
    up = camera.matrix_world.to_quaternion() @ Vector((0, 1, 0))
    xs = [p.dot(right) for p in all_points]
    ys = [p.dot(up) for p in all_points]
    projected_width = max(xs) - min(xs)
    projected_height = max(ys) - min(ys)
    camera.data.ortho_scale = max(projected_height * 1.42, projected_width * 1.42 / (1280/960))
    scene.render.filepath = str(PREVIEWS / (name + ".png"))
    bpy.ops.render.render(write_still=True)
    print("Rendered", scene.render.filepath)

# Save the scene with the main three-quarter preview framed in Blender.
camera.location = center + Vector((2.5, 2.8, 1.9))
aim(camera, center)
camera.data.ortho_scale = 2.2
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "TABLE-ASTRA-001.blend"))
