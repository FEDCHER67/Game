"""Build the original BRAIN-ASTRA-001 game mesh and review studio in Blender 5.2."""

import math
import os
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT / "Previews"
PREVIEWS.mkdir(exist_ok=True)
DRAFT = True

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 24 if DRAFT else 96
scene.render.resolution_x = scene.render.resolution_y = 680 if DRAFT else 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.render.film_transparent = False
scene.unit_settings.system = "METRIC"

asset_col = bpy.data.collections.new("BRAIN-ASTRA-001 | Game Mesh")
scene.collection.children.link(asset_col)
studio_col = bpy.data.collections.new("Preview Studio | Not Exported")
scene.collection.children.link(studio_col)

mat = bpy.data.materials.new("01 | Warm dusty rose soft matte")
mat.use_nodes = True
mat.diffuse_color = (0.39, 0.155, 0.16, 1)
mat.roughness = 0.79
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = mat.diffuse_color
bsdf.inputs["Roughness"].default_value = 0.79
bsdf.inputs["Metallic"].default_value = 0
bsdf.inputs["Specular IOR Level"].default_value = 0.035
bsdf.inputs["Coat Weight"].default_value = 0
bsdf.inputs["Sheen Weight"].default_value = 0
bsdf.inputs["Subsurface Weight"].default_value = 0.015
bsdf.inputs["Diffuse Roughness"].default_value = 0.65


def catmull_rom(points, steps=12):
    """Smooth, hand-placed centerline through broad gyrus control points."""
    out = []
    for k in range(len(points) - 1):
        p0 = points[max(0, k - 1)]
        p1 = points[k]
        p2 = points[k + 1]
        p3 = points[min(len(points) - 1, k + 2)]
        for n in range(steps):
            t = n / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[i] + (-p0[i] + p2[i]) * t
                       + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2
                       + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t3)
                       for i in range(len(p1))))
    out.append(tuple(points[-1]))
    return out


def make_hemisphere(side):
    """Union rounded, flowing gyri with a closed stemless ovoid."""
    # Separate ovoids meet at a narrow fissure and retain a broad lower cap.
    center_x = side * 0.041
    rx, ry, rz = 0.039, 0.083, 0.044
    center_z = 0.004
    bpy.ops.mesh.primitive_uv_sphere_add(segments=72, ring_count=48,
                                         location=(center_x, 0, center_z))
    base = bpy.context.object
    base.name = "Base"
    base.scale = (rx, ry, rz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    def surface_point(kind, a, b):
        # Project hand-authored strokes onto the actual ovoid, then bury
        # their cores slightly into it for a smooth watertight voxel union.
        if kind == "side":
            y, z = a, b
            u, v = y / ry, (z - center_z) / rz
            edge = max(0.08, 1.0 - u * u - v * v)
            q = math.sqrt(edge)
            x = center_x + side * rx * q
            normal = Vector((side * q / rx, u / ry, v / rz)).normalized()
        else:
            local_x, y = a, b
            u, v = local_x / rx, y / ry
            edge = max(0.08, 1.0 - u * u - v * v)
            q = math.sqrt(edge)
            x = center_x + side * local_x
            z = center_z + rz * q
            normal = Vector((side * u / rx, v / ry, q / rz)).normalized()
        return Vector((x, y, z)) + normal * 0.0012

    # Side strokes curve and double back at different heights. Their
    # independent ends avoid the layered-cake silhouette of ring sulci.
    side_strokes = [
        [(-.068,.006),(-.061,.023),(-.044,.032),(-.024,.021),(-.013,.035)],
        [(-.055,.003),(-.039,.015),(-.019,.006),(.002,.020),(.020,.013)],
        [(-.061,-.011),(-.044,-.002),(-.026,-.015),(-.010,-.006)],
        [(-.024,.041),(-.005,.026),(.014,.034),(.027,.021),(.021,.007)],
        [(-.005,.044),(.014,.049),(.031,.035),(.048,.038)],
        [(.002,-.010),(.021,.001),(.038,-.008),(.052,.003)],
        [(.025,.019),(.042,.028),(.054,.017),(.067,.022)],
        [(.027,-.015),(.047,-.008),(.058,.007),(.069,.001)],
        [(-.064,.022),(-.072,.009),(-.065,-.006),(-.052,-.011)],
        [(.053,.028),(.069,.030),(.075,.017),(.066,.009)],
    ]
    crown_strokes = [
        [(-.019,-.051),(-.010,-.038),(-.019,-.023),(-.009,-.007),(-.016,.008)],
        [(.006,-.055),(.018,-.042),(.005,-.026),(.016,-.010),(.008,.004)],
        [(-.021,-.002),(-.008,.015),(-.020,.029),(-.010,.047)],
        [(.008,.004),(.023,.016),(.011,.033),(.023,.050)],
        [(-.027,-.027),(-.008,-.020),(.010,-.027),(.027,-.016)],
        [(-.026,.033),(-.007,.040),(.011,.029),(.029,.038)],
    ]
    tubes = []
    for k, (kind, strokes) in enumerate((("side", side_strokes),
                                          ("crown", crown_strokes))):
        for m, controls in enumerate(strokes):
            if side < 0:
                controls = [(a + (0.0025 if m % 2 else -0.002), b)
                            for a, b in controls]
            points = catmull_rom(controls)
            curve = bpy.data.curves.new("Rounded gyrus centerline", "CURVE")
            curve.dimensions = "3D"
            curve.resolution_u = 16
            curve.bevel_depth = 0.0078 if kind == "side" else 0.0084
            curve.bevel_resolution = 4
            curve.use_fill_caps = True
            spline = curve.splines.new("POLY")
            spline.points.add(len(points) - 1)
            for point, (a, b) in zip(spline.points, points):
                pos = surface_point(kind, a, b)
                point.co = (*pos, 1.0)
            obj = bpy.data.objects.new("Gyrus | %s %02d" % (kind, m + 1), curve)
            scene.collection.objects.link(obj)
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target="MESH")
            tubes.append(bpy.context.object)

    bpy.ops.object.select_all(action="DESELECT")
    for ob in [base] + tubes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.join()
    base.data.remesh_voxel_size = 0.0018
    bpy.ops.object.voxel_remesh()
    smooth = base.modifiers.new("Soft sculpt blend", "SMOOTH")
    smooth.factor = 1.5
    smooth.iterations = 6
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    decimate = base.modifiers.new("Game resolution", "DECIMATE")
    decimate.ratio = 0.42
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    base.name = "Left hemisphere" if side < 0 else "Right hemisphere"
    for col in tuple(base.users_collection):
        col.objects.unlink(base)
    asset_col.objects.link(base)
    base.data.materials.append(mat)
    for poly in base.data.polygons:
        poly.use_smooth = True
    bpy.ops.object.select_all(action="DESELECT")
    base.select_set(True)
    bpy.context.view_layer.objects.active = base
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.025)
    bpy.ops.object.mode_set(mode="OBJECT")
    base.data.uv_layers.active.name = "UV0"
    print("VOXEL_STATS", base.name, len(base.data.vertices), len(base.data.polygons))
    return base


left = make_hemisphere(-1)
right = make_hemisphere(1)

world = bpy.data.worlds.new("Organ family blue gray studio")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0165, 0.0235, 0.0365, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.48
scene.world = world


def light(name, loc, energy, size, color):
    data = bpy.data.lights.new(name, "AREA")
    data.shape = "DISK"
    data.energy = energy
    data.size = size
    data.color = color
    data.specular_factor = 0.0
    obj = bpy.data.objects.new(name, data)
    studio_col.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector((0, 0, 0)) - obj.location).to_track_quat("-Z", "Y").to_euler()


light("Large softbox left", (-0.15, -0.13, 0.20), 1.86, 0.201, (1.0, 0.987, 0.977))
light("Back edge softbox", (0.08, 0.16, 0.16), 1.31, 0.146, (0.735, 0.823, 1.0))
light("Broad fill right", (0.18, -0.07, 0.055), 0.775, 0.147, (1.0, 0.817, 0.703))
underside = bpy.data.lights.new("Underside review fill", "AREA")
underside.shape = "DISK"
underside.energy = 1.5
underside.size = 0.2
underside.color = (1, 0.91, 0.85)
underside.specular_factor = 0
underside_obj = bpy.data.objects.new("Underside review fill", underside)
studio_col.objects.link(underside_obj)
underside_obj.location = (0, -0.12, -0.18)
underside_obj.rotation_euler = (Vector((0, 0, 0)) - underside_obj.location).to_track_quat("-Z", "Y").to_euler()
underside_obj.hide_render = True
rear_fill = bpy.data.lights.new("Rear review fill", "AREA")
rear_fill.shape = "DISK"
rear_fill.energy = 0.9
rear_fill.size = 0.18
rear_fill.color = (1.0, 0.91, 0.86)
rear_fill.specular_factor = 0
rear_obj = bpy.data.objects.new("Rear review fill", rear_fill)
studio_col.objects.link(rear_obj)
rear_obj.location = (0.02, 0.22, 0.08)
rear_obj.rotation_euler = (Vector((0, 0, 0)) - rear_obj.location).to_track_quat("-Z", "Y").to_euler()
rear_obj.hide_render = True

cam_data = bpy.data.cameras.new("Review orthographic")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("Review orthographic", cam_data)
studio_col.objects.link(cam)
scene.camera = cam


def pose_camera(location, target=(0, 0, 0), scale=0.215):
    cam.location = location
    cam.rotation_euler = (Vector(target) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = scale


def render(filename, location, target=(0, 0, 0), scale=0.215):
    pose_camera(location, target, scale)
    scene.render.filepath = str(PREVIEWS / filename)
    bpy.ops.render.render(write_still=True)


if DRAFT:
    render("draft_front.png", (0.067, -0.3, 0.105))
    rear_obj.hide_render = False
    render("draft_rear.png", (-0.02, 0.3, 0.055))
    rear_obj.hide_render = True
    render("draft_side.png", (0.29, -0.01, 0.018))
    render("draft_top.png", (0.01, -0.03, 0.31))
    render("draft_closeup.png", (0.14, -0.20, 0.13), target=(0.045, -0.035, 0.016), scale=0.105)
    underside_obj.hide_render = False
    render("draft_underside.png", (0.022, -0.10, -0.3))
else:
    pose_camera((0.067, -0.3, 0.105))
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "BRAIN-ASTRA-001.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    for ob in (left, right):
        ob.select_set(True)
    bpy.context.view_layer.objects.active = left
    bpy.ops.export_scene.fbx(filepath=str(ROOT / "BRAIN-ASTRA-001.fbx"),
                             use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL",
                             axis_forward="-Z", axis_up="Y", mesh_smooth_type="FACE",
                             use_mesh_modifiers=True, bake_anim=False, path_mode="AUTO")
    render("01_front_hero.png", (0.067, -0.3, 0.105))
    rear_obj.hide_render = False
    render("02_rear.png", (-0.02, 0.3, 0.055))
    rear_obj.hide_render = True
    render("03_left_three_quarter.png", (-0.19, -0.24, 0.07))
    render("04_right_three_quarter.png", (0.19, -0.24, 0.07))
    render("05_side.png", (0.29, -0.01, 0.018))
    render("06_top.png", (0.01, -0.03, 0.31), scale=0.215)
    render("07_fold_closeup.png", (0.14, -0.20, 0.13), target=(0.045, -0.035, 0.016), scale=0.105)
    underside_obj.hide_render = False
    render("08_underside_cleanup.png", (0.022, -0.10, -0.3))
    underside_obj.hide_render = True
    neutral = bpy.data.materials.new("Preview only | neutral clay")
    neutral.use_nodes = True
    shader = neutral.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.39, 0.39, 0.39, 1)
    shader.inputs["Roughness"].default_value = 0.9
    shader.inputs["Specular IOR Level"].default_value = 0
    scene.view_layers[0].material_override = neutral
    render("09_neutral_sculpt.png", (0.025, -0.3, 0.065))
