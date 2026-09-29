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
DRAFT = os.environ.get("BRAIN_DRAFT") == "1"

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


def make_hemisphere(side):
    """An asymmetrical closed ovoid, with broad sculpted sulci in its surface."""
    seg, rings = 136, 76
    center_x = side * 0.027
    verts, faces = [], []
    ridge_paths, ridge_weights = [], []

    def add_ridge(x, y, z, t):
        ridge_paths.append(Vector((x, y, z)))
        taper = max(0.0, min(1.0, min(t, 1.0 - t) / 0.23))
        ridge_weights.append(taper * taper * (3.0 - 2.0 * taper))

    # Independent serpentine gyri run in several directions across the crown
    # and lateral wall. Negative space between these raised, rounded forms
    # becomes the sulcus network; no continuous horizontal bands are carved.
    guides = [
        (0.43, -2.05, 0.83, -0.42, 0.11, 0.08, 0.3),
        (0.48, 0.24, 0.78, 2.07, -0.13, 0.10, 1.4),
        (0.78, -1.75, 1.12, 0.46, 0.16, -0.10, 2.5),
        (0.88, 0.78, 1.16, 2.27, -0.12, 0.09, 0.8),
        (0.68, -1.32, 1.43, -0.12, 0.15, 0.18, 1.9),
        (0.74, 1.38, 1.39, 0.16, -0.14, -0.17, 3.2),
        (1.15, -1.42, 1.74, 0.37, 0.17, -0.13, 0.9),
        (1.70, -0.40, 1.31, 1.30, -0.13, 0.19, 2.7),
        (1.94, -1.28, 1.60, 0.02, 0.14, 0.14, 1.1),
        (1.51, 0.60, 2.03, 1.60, -0.12, -0.16, 2.0),
        (1.16, -2.12, 1.86, -1.12, 0.11, 0.16, 3.0),
        (1.10, 1.44, 1.78, 2.13, -0.12, 0.12, 0.5),
    ]
    for k, (th0, ph0, th1, ph1, th_bend, ph_bend, phase) in enumerate(guides):
        if side < 0:
            th0 += 0.04 * math.sin(k * 1.8)
            th1 += 0.05 * math.cos(k * 1.3)
            phase += 0.6
        for n in range(81):
            t = n / 80
            theta = th0 + (th1 - th0) * t
            theta += th_bend * math.sin(math.pi * t) * math.sin(2.2 * math.pi * t + phase)
            phi_local = ph0 + (ph1 - ph0) * t
            phi_local += ph_bend * math.sin(math.pi * t) * math.sin(2.0 * math.pi * t + phase)
            phi = phi_local if side > 0 else math.pi - phi_local
            nz = math.cos(theta)
            x = center_x + 0.054 * math.sin(theta) * math.cos(phi)
            y = 0.083 * math.sin(theta) * math.sin(phi)
            y *= 1.0 + 0.025 * math.sin(3 * phi + side)
            z = 0.052 * nz + 0.007 * (1 - nz * nz) + 0.013 * max(0, -nz) ** 3 - 0.0015
            add_ridge(x, y, z, t)

    # Crown ridges fill the center of each dorsal plate. Projected S curves
    # avoid a smooth oval at the top while keeping broad, readable forms.
    for k, (x_center, y_start, y_end, phase) in enumerate((
        (-0.013, -0.047, 0.043, 0.2),
        (0.008, -0.053, 0.048, 1.6),
        (0.029, -0.045, 0.039, 2.9),
    )):
        for n in range(81):
            t = n / 80
            local_x = x_center + 0.008 * math.sin(2.3 * math.pi * t + phase) * math.sin(math.pi * t)
            y = y_start + (y_end - y_start) * t
            q = min(0.96, (local_x / 0.054) ** 2 + (y / 0.083) ** 2)
            nz = math.sqrt(1 - q)
            add_ridge(center_x + side * local_x, y,
                      0.052 * nz + 0.007 * q - 0.0015, t)

    ridge_tree = KDTree(len(ridge_paths))
    for idx, p in enumerate(ridge_paths):
        ridge_tree.insert(p, idx)
    ridge_tree.balance()
    for j in range(rings + 1):
        theta = math.pi * (j + 0.5) / (rings + 1)
        st, ct = math.sin(theta), math.cos(theta)
        for i in range(seg):
            phi = 2 * math.pi * i / seg
            nx, ny, nz = st * math.cos(phi), st * math.sin(phi), ct
            # Broad lobes keep the silhouette organic without adding lower anatomy.
            x = center_x + 0.054 * nx
            y = 0.083 * ny * (1.0 + 0.025 * math.sin(3 * phi + side))
            z = 0.052 * nz + 0.007 * (1 - nz * nz) + 0.013 * max(0, -nz) ** 3 - 0.0015
            # The inner walls meet across a narrow sagittal fissure and remain closed.
            fissure = 0.0007 if nz > -0.2 else -0.0003
            if side * x < fissure:
                x = side * fissure
            # Broad positive gyri blend into the original closed ovoid. The
            # base surface between them supplies soft valleys without sharp
            # subtraction artifacts or exposed path endpoints.
            ridge_field = max(ridge_weights[index] * math.exp(-0.5 * (distance / 0.0083) ** 2)
                              for _, index, distance in ridge_tree.find_n(Vector((x, y, z)), 8))
            fold_fade = max(0.0, min(1.0, (nz + 0.52) / 0.43))
            fold_fade = fold_fade * fold_fade * (3 - 2 * fold_fade)
            swell = 0.0008 * (math.sin(3.7 * phi + 2.4 * theta + side)
                              + 0.5 * math.cos(5.1 * phi - 1.7 * theta))
            radial = (0.0105 * ridge_field + swell) * fold_fade
            x += radial * nx
            y += radial * ny
            z += radial * nz
            verts.append((x, y, z))
    for j in range(rings):
        for i in range(seg):
            n = j * seg + i
            ni = j * seg + (i + 1) % seg
            faces.append((n, n + seg, ni + seg, ni))
    # Close poles with a modest cap rather than leaving pinholes.
    top = len(verts)
    verts.append((center_x, 0, 0.0505))
    bottom = len(verts)
    verts.append((center_x, 0, -0.0405))
    for i in range(seg):
        faces.append((top, i, (i + 1) % seg))
        a = rings * seg + i
        b = rings * seg + (i + 1) % seg
        faces.append((bottom, b, a))
    # The lower center of a UV ovoid otherwise makes a narrow V in side view.
    # Lift it into a broad, softly rounded closure; there is no lower stalk.
    for index, (x, y, z) in enumerate(verts):
        if z < -0.028:
            t = min(1.0, (-z - 0.028) / 0.013)
            z += 0.008 * t * t * math.exp(-0.5 * (y / 0.025) ** 2)
            verts[index] = (x, y, z)
    mesh = bpy.data.meshes.new("Cerebral hemisphere surface")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Left hemisphere" if side < 0 else "Right hemisphere", mesh)
    asset_col.objects.link(obj)
    obj.data.materials.append(mat)
    for p in mesh.polygons:
        p.use_smooth = True
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.025)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.data.uv_layers.active.name = "UV0"
    return obj


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
