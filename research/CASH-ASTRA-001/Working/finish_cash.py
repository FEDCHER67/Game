"""Polish the approved Tripo cash bundle and produce the Blender handoff."""
import bpy
import math
from mathutils import Vector
from pathlib import Path

ROOT = Path(r"C:\Dev\Game-main\research\CASH-ASTRA-001")
SOURCE = ROOT / "Working" / "Tripo" / "cash_tripo_base.fbx"
PREVIEWS = ROOT / "Previews"
PREVIEWS.mkdir(exist_ok=True)

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for collection in list(bpy.data.collections):
    if collection.name != "Collection" and collection.users == 0:
        bpy.data.collections.remove(collection)

def collection(name):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col

geo_col = collection("COL_Cash_Geo")
preview_col = collection("COL_Cash_Preview")

def move_to(obj, col):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    col.objects.link(obj)

def material(name, rgba, roughness=0.82, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgba, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*rgba, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat

note = material("MAT_Cash_MutedTeal", (0.095, 0.225, 0.13), 0.86)
paper = material("MAT_Cash_WarmPaper", (0.49, 0.53, 0.40), 0.92)
band_mat = material("MAT_Cash_IvoryBand", (0.60, 0.53, 0.35), 0.88)
ink = material("MAT_Cash_FictionalInk", (0.018, 0.070, 0.040), 0.91)
soft_ink = material("MAT_Cash_PaleInk", (0.31, 0.46, 0.33), 0.91)

bpy.ops.import_scene.fbx(filepath=str(SOURCE))
source = next(obj for obj in bpy.context.selected_objects if obj.type == "MESH")
bpy.context.view_layer.objects.active = source
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.separate(type="LOOSE")
bpy.ops.object.mode_set(mode="OBJECT")
parts = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
mesh_parts = []
for obj in parts:
    if len(obj.data.polygons) < 4:
        bpy.data.objects.remove(obj, do_unlink=True)
        continue
    move_to(obj, geo_col)
    if obj.dimensions.x < 0.2:
        obj.name = "SM_Cash_Band"
        obj.data.materials.clear()
        obj.data.materials.append(band_mat)
    elif obj.dimensions.z > 0.12:
        obj.name = "SM_Cash_LayerStack"
    elif max((obj.matrix_world @ vert.co).z for vert in obj.data.vertices) > 0.20:
        obj.name = "SM_Cash_TopBill"
    else:
        obj.name = "SM_Cash_MidBill"
    mesh_parts.append(obj)

# The Tripo model arrives as disconnected paper, note and band islands. Keep
# that geometry; use face direction to distinguish painted faces from edges.
for obj in mesh_parts:
    if obj.name == "SM_Cash_Band":
        continue
    obj.data.materials.clear()
    obj.data.materials.append(note)
    obj.data.materials.append(paper)
    for face in obj.data.polygons:
        if face.normal.z > 0.58:
            face.material_index = 0
        elif face.normal.z < -0.58:
            face.material_index = 0
        else:
            face.material_index = 1

def top_height(x, y):
    best = -1.0
    for obj in mesh_parts:
        hit, point, _, _ = obj.ray_cast(Vector((x, y, 0.6)), Vector((0, 0, -1)))
        if hit:
            best = max(best, point.z)
    return (best if best >= 0 else 0.206) + 0.0013

def line(name, xy_points, mat=ink, radius=0.0017, closed=False):
    crv = bpy.data.curves.new(name, "CURVE")
    crv.dimensions = "3D"
    crv.resolution_u = 1
    crv.bevel_depth = radius
    crv.bevel_resolution = 2
    spline = crv.splines.new("POLY")
    spline.points.add(len(xy_points) - 1)
    for point, (x, y) in zip(spline.points, xy_points):
        point.co = (x, y, top_height(x, y), 1)
    spline.use_cyclic_u = closed
    obj = bpy.data.objects.new(name, crv)
    geo_col.objects.link(obj)
    obj.data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.convert(target="MESH")
    return bpy.context.object

def round_rect(cx, cy, w, h, r, steps=5):
    points = []
    for ox, oy, a0 in ((w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),
                       (-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)):
        for j in range(steps + 1):
            angle = math.radians(a0 + j * 90 / steps)
            points.append((cx + ox + r * math.cos(angle),
                           cy + oy + r * math.sin(angle)))
    return points

# Abstract printed motifs avoid real denominations, currency marks and seals.
for side, cx in (("Left", -0.286), ("Right", 0.286)):
    line("SM_Cash_" + side + "_PrintBorder",
         round_rect(cx, 0, 0.335, 0.315, 0.025), closed=True)
    line("SM_Cash_" + side + "_InnerFrame",
         round_rect(cx, 0, 0.255, 0.24, 0.043),
         mat=soft_ink, radius=0.0012, closed=True)
    # Layered lozenges read as a fictional printed emblem from a distance.
    for k, (w, h) in enumerate(((0.12, 0.09), (0.077, 0.058), (0.038, 0.029))):
        line("SM_Cash_" + side + "_Lozenge" + str(k),
             [(cx-w/2,0), (cx,-h/2), (cx+w/2,0), (cx,h/2)],
             mat=ink if k == 0 else soft_ink, radius=0.002, closed=True)
    for yy in (-0.101, 0.101):
        line("SM_Cash_" + side + "_Hatch" + str(yy),
             [(cx-0.07,yy), (cx+0.07,yy)], mat=ink, radius=0.0018)

line("SM_Cash_Band_Diamond",
     [(0,-0.075), (0.042,0), (0,0.075), (-0.042,0)],
     mat=ink, radius=0.003, closed=True)
line("SM_Cash_Band_Center",
     round_rect(0, 0, 0.032, 0.048, 0.014),
     mat=ink, radius=0.003, closed=True)

# Combine decorative strokes by ink to keep game draw calls low.
for mat, name in ((ink, "SM_Cash_PrintDark"),
                  (soft_ink, "SM_Cash_PrintPale")):
    decoration = [obj for obj in geo_col.objects if obj.type == "MESH"
                  and obj not in mesh_parts and obj.data.materials
                  and obj.data.materials[0] == mat]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in decoration:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = decoration[0]
    bpy.ops.object.join()
    decoration[0].name = name

# Put the model at the origin with the lowest paper edge on Z=0.
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 1.0

def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()

ground = material("MAT_Preview_Navy", (0.003, 0.007, 0.016), 0.94)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -0.013))
stage = bpy.context.object
stage.name = "PREVIEW_Ground"
stage.data.materials.append(ground)
move_to(stage, preview_col)

for name, location, energy, size, tint in (
    ("PREVIEW_Key", (-1.7,-1.6,2.6), 185, 3.0, (0.84,0.95,1.0)),
    ("PREVIEW_Fill", (1.4,-0.8,1.4), 85, 2.0, (1.0,0.88,0.72)),
    ("PREVIEW_Rim", (0.4,1.5,1.6), 145, 1.5, (0.65,0.82,1.0)),
):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.data.color = tint
    aim(light, (0,0,0.10))
    move_to(light, preview_col)

world = bpy.data.worlds.new("World_NavyStudio") if not scene.world else scene.world
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.035,0.052,0.074,1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.4

scene.render.engine = "CYCLES"
scene.cycles.samples = 28
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"

views = (
    ("01_front", (0,-2.0,0.66), 1.28),
    ("02_left", (-1.8,-0.15,0.60), 0.78),
    ("03_right", (1.8,-0.15,0.60), 0.78),
    ("04_back", (0,2.0,0.66), 1.28),
    ("05_three_quarter", (1.30,-1.55,0.93), 1.42),
    ("06_detail", (0.65,-0.9,0.62), 0.76),
)

for label, location, ortho in views:
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.object
    camera.name = "PREVIEW_Camera_" + label
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = ortho
    aim(camera, (0,0,0.105))
    move_to(camera, preview_col)
    scene.camera = camera
    scene.render.filepath = str(PREVIEWS / (label + ".png"))
    bpy.ops.render.render(write_still=True)

scene.camera = bpy.data.objects.get("PREVIEW_Camera_05_three_quarter")
scene.render.filepath = str(PREVIEWS / "05_three_quarter.png")

# Preview equipment lives in a separate collection and never enters game FBX.
bpy.ops.object.select_all(action="DESELECT")
for obj in geo_col.objects:
    if obj.type == "MESH":
        obj.select_set(True)
bpy.context.view_layer.objects.active = next(obj for obj in geo_col.objects if obj.type == "MESH")
bpy.ops.export_scene.fbx(filepath=str(ROOT / "CASH-ASTRA-001.fbx"),
                         use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, add_leaf_bones=False,
                         path_mode="COPY", bake_space_transform=False)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "CASH-ASTRA-001.blend"))

print("FINISHED", len([o for o in geo_col.objects if o.type == "MESH"]), "mesh objects")
