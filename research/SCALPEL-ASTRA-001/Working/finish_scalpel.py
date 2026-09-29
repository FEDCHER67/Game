"""Turn the approved Tripo candidate into a small, matte game prop."""
import bpy
import bmesh
import json
import math
from mathutils import Vector
from pathlib import Path

ROOT = Path(r"C:\Dev\Game-main\research\SCALPEL-ASTRA-001")
SOURCE = ROOT / "Working" / "Tripo" / "SCALPEL-ASTRA-001_Tripo_Front.fbx"
EXPORT = ROOT / "SCALPEL-ASTRA-001.fbx"
BLEND = ROOT / "SCALPEL-ASTRA-001.blend"
PREVIEWS = ROOT / "Previews"
PREVIEWS.mkdir(parents=True, exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(SOURCE))
bpy.context.view_layer.update()
source = next(o for o in bpy.context.scene.objects if o.type == "MESH")
source_matrix = source.matrix_world.copy()
raw = source.data

# Keep the approved X-Z silhouette.  The source handle is almost square in
# cross-section, so the thin blade reads as if it were rolled relative to the
# grip when seen from above.  Flatten both around the same Y=0 center plane.
scale = 0.17
blade_cut = -0.165
handle_front = -0.150
handle_y_scale = 0.50
handle_z_scale = 0.85
# Source grip's broad surfaces drift in Y with Z.  Remove the source roll
# before reducing thickness, while retaining its approved X-Z outline.
handle_source_points = [source_matrix @ v.co for v in raw.vertices
                        if 0.0 <= (source_matrix @ v.co).x <= 0.30]
handle_mean_y = sum(p.y for p in handle_source_points) / len(handle_source_points)
handle_mean_z = sum(p.z for p in handle_source_points) / len(handle_source_points)
handle_yz_slope = (sum((p.y-handle_mean_y)*(p.z-handle_mean_z) for p in handle_source_points) /
                   sum((p.z-handle_mean_z)**2 for p in handle_source_points))
parts = {"Blade": [], "Handle": []}
for poly in raw.polygons:
    cx = sum((source_matrix @ raw.vertices[i].co).x for i in poly.vertices) / len(poly.vertices)
    parts["Blade" if cx < blade_cut else "Handle"].append(poly)

def material(name, color, roughness, metal=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metal
    return m

mat_blade = material("Scalpel_Blade_MatteSteel", (0.56, 0.61, 0.65), 0.66, 0.42)
mat_handle = material("Scalpel_Handle_Charcoal", (0.075, 0.088, 0.10), 0.88)
objects = []
for part_name, faces in parts.items():
    if part_name == "Blade":
        # Straight constant-section blade.  The only profile change is a
        # short planar point cut at the far end; the broad faces are parallel.
        zc = handle_mean_z * scale
        profile = [(-0.069,-0.0032), (-0.061,0.0032),
                   (-0.01836,0.0032), (-0.01836,-0.0032)]
        half_y = 0.0005
        coords = [(x,y,zc+z) for y in (-half_y,half_y) for x,z in profile]
        polygons = [(3,2,1,0), (4,5,6,7)]
        for j in range(4):
            nxt = (j+1) % 4
            polygons.append((j,nxt,4+nxt,4+j))
    else:
        original_ids = sorted({i for face in faces for i in face.vertices})
        mapping = {old: new for new, old in enumerate(original_ids)}
        coords = []
        for old in original_ids:
            p = source_matrix @ raw.vertices[old].co
            p.y = (p.y - handle_yz_slope * (p.z - handle_mean_z)) * handle_y_scale
            # Faces selected at the seam can carry a long, dark source
            # triangle into the exposed tang.  Seat their X coordinates at
            # the front grip plane instead of leaving a floating prong.
            p.x = max(p.x, handle_front)
            nose_blend = max(0.0, min(1.0, (p.x - handle_front) / 0.065))
            nose_profile = 0.62 + 0.38 * nose_blend
            p.z = handle_mean_z + (p.z - handle_mean_z) * handle_z_scale * nose_profile
            p.y *= 0.72 + 0.28 * nose_blend
            coords.append((p.x * scale, p.y * scale, p.z * scale))
        polygons = [tuple(mapping[i] for i in face.vertices) for face in faces]
    new_mesh = bpy.data.meshes.new("Scalpel_" + part_name + "Mesh")
    new_mesh.from_pydata(coords, [], polygons)
    new_mesh.update()
    if part_name == "Blade":
        bm = bmesh.new()
        bm.from_mesh(new_mesh)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(new_mesh)
        bm.free()
    obj = bpy.data.objects.new("Scalpel_" + part_name, new_mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat_blade if part_name == "Blade" else mat_handle)
    for face in new_mesh.polygons:
        face.use_smooth = False
    # The source's 5k faces are excessive for a hand-sized pickup.
    target = 200 if part_name == "Blade" else 800
    if len(new_mesh.polygons) > target:
        mod = obj.modifiers.new("GamePolyBudget", "DECIMATE")
        mod.ratio = target / len(new_mesh.polygons)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    objects.append(obj)

bpy.data.objects.remove(source, do_unlink=True)
bpy.context.view_layer.update()
all_points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
min_z = min(p.z for p in all_points)
for obj in objects:
    for v in obj.data.vertices:
        v.co.z -= min_z
bpy.context.view_layer.update()
all_points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
bounds = [[min(p[i] for p in all_points), max(p[i] for p in all_points)] for i in range(3)]
blade_right = max((o.matrix_world @ v.co).x for o in objects if o.name == "Scalpel_Blade" for v in o.data.vertices)
blade_left = min((o.matrix_world @ v.co).x for o in objects if o.name == "Scalpel_Blade" for v in o.data.vertices)
handle_left = min((o.matrix_world @ v.co).x for o in objects if o.name == "Scalpel_Handle" for v in o.data.vertices)
handle_right = max((o.matrix_world @ v.co).x for o in objects if o.name == "Scalpel_Handle" for v in o.data.vertices)
def section_measure(obj, lo, hi):
    # Cross-section samples well away from the tip and handle cap.  A broad
    # plane parallel to X-Z has small Y extent and principal roll near zero.
    points = [obj.matrix_world @ v.co for v in obj.data.vertices if lo <= (obj.matrix_world @ v.co).x <= hi]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    my = sum(ys) / len(ys)
    mz = sum(zs) / len(zs)
    yy = sum((y-my)**2 for y in ys) / len(ys)
    zz = sum((z-mz)**2 for z in zs) / len(zs)
    yz = sum((y-my)*(z-mz) for y,z in zip(ys,zs)) / len(ys)
    return {"sample_vertices": len(points), "y_center_m": my,
            "y_span_m": max(ys)-min(ys), "z_span_m": max(zs)-min(zs),
            "broad_face_roll_deg": math.degrees(0.5*math.atan2(2*yz, zz-yy))}

blade_section = section_measure(objects[0], -0.07, -0.04)
handle_section = section_measure(objects[1], 0.0, 0.05)
def blade_cross_section(obj, x):
    points = []
    for edge in obj.data.edges:
        p = obj.matrix_world @ obj.data.vertices[edge.vertices[0]].co
        q = obj.matrix_world @ obj.data.vertices[edge.vertices[1]].co
        if (p.x-x)*(q.x-x) <= 0 and abs(q.x-p.x) > 1e-9:
            t = (x-p.x)/(q.x-p.x)
            points.append(p.lerp(q,t))
    assert len(points) >= 4, (x, points)
    return {"x_m": x, "y_thickness_m": max(p.y for p in points)-min(p.y for p in points),
            "z_width_m": max(p.z for p in points)-min(p.z for p in points)}

blade_straight_sections = [blade_cross_section(objects[0], x) for x in (-0.055,-0.040,-0.030)]
report = {
    "source": str(SOURCE), "bounds_m": bounds,
    "contact_gap_m": handle_left - blade_right,
    "blade_section": blade_section,
    "handle_section": handle_section,
    "section_center_offset_m": handle_section["y_center_m"] - blade_section["y_center_m"],
    "section_roll_difference_deg": handle_section["broad_face_roll_deg"] - blade_section["broad_face_roll_deg"],
    "blade_straight_sections": blade_straight_sections,
    "visible_blade_length_m": handle_left - blade_left,
    "handle_length_m": handle_right - handle_left,
    "blade_to_handle_z_width_ratio": blade_straight_sections[0]["z_width_m"] / handle_section["z_span_m"],
    "parts": [{"name": o.name, "vertices": len(o.data.vertices), "faces": len(o.data.polygons)} for o in objects],
}
(ROOT / "Working" / "export_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
assert -0.009 < report["contact_gap_m"] < -0.006
assert sum(x["faces"] for x in report["parts"]) < 1600
assert 0.15 < bounds[0][1] - bounds[0][0] < 0.18
assert abs(report["section_center_offset_m"]) < 0.001
assert abs(report["section_roll_difference_deg"]) < 8
assert 0.0042 < handle_section["y_span_m"] < 0.0052
assert 0.0135 < handle_section["z_span_m"] < 0.0148
assert blade_section["y_span_m"] < 0.002
assert all(abs(s["y_thickness_m"]-0.001) < 0.00001 and
           abs(s["z_width_m"]-0.0064) < 0.00001 for s in blade_straight_sections)
assert 0.4 < report["blade_to_handle_z_width_ratio"] < 0.6
assert 0.040 < report["visible_blade_length_m"] < 0.048

bpy.ops.object.select_all(action="DESELECT")
for obj in objects:
    obj.select_set(True)
bpy.context.view_layer.objects.active = objects[0]
bpy.ops.export_scene.fbx(filepath=str(EXPORT), use_selection=True,
                         object_types={"MESH"}, apply_unit_scale=True,
                         bake_space_transform=False, add_leaf_bones=False)
bpy.ops.object.select_all(action="DESELECT")

# Preview collection is excluded from FBX. Keep it in the editable .blend.
center = Vector([(lo + hi) / 2 for lo, hi in bounds])
center.z = 0.008
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = "PREVIEW_Camera"
camera.data.type = "ORTHO"
camera.data.ortho_scale = 0.215
bpy.context.scene.camera = camera
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world.color = (0.24, 0.27, 0.31)
scene.world.use_nodes = True
world_bg = scene.world.node_tree.nodes.get("Background")
world_bg.inputs["Color"].default_value = (0.32, 0.35, 0.38, 1)
world_bg.inputs["Strength"].default_value = 0.55
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"

for name, loc, energy, size in [
    ("PREVIEW_Key", (0.0, -0.23, 0.26), 0.9, 0.25),
    ("PREVIEW_Fill", (0.0, 0.20, 0.14), 0.4, 0.20),
]:
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.shape = "DISK"
    light.size = size
    obj = bpy.data.objects.new(name, light)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (center - obj.location).to_track_quat("-Z", "Y").to_euler()

views = [
    ("01_front", (0.0, -0.26, 0.05)),
    ("02_back", (0.0, 0.26, 0.05)),
    ("03_top", (0.0, -0.04, 0.27)),
    ("04_bottom", (0.0, 0.04, -0.25)),
    ("05_three_quarter", (-0.13, -0.22, 0.16)),
    ("06_blade_close", (-0.10, -0.17, 0.10)),
]
for name, offset in views:
    focus = center.copy()
    if name == "06_blade_close":
        focus.x = -0.045
        camera.data.ortho_scale = 0.105
    else:
        camera.data.ortho_scale = 0.215
    camera.location = focus + Vector(offset)
    camera.rotation_euler = (focus - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(PREVIEWS / (name + ".png"))
    bpy.ops.render.render(write_still=True)

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
