"""Finish the supplied Tripo brain as a restrained VOLUNTEERS ONLY organ prop."""
import os
from pathlib import Path

import bpy
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Working' / 'Tripo' / 'pink brain 3d model.fbx'
PREVIEWS = ROOT / 'Previews'
PREVIEWS.mkdir(exist_ok=True)
DRAFT = os.environ.get('BRAIN_DRAFT') == '1'

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(SOURCE))
scene = bpy.context.scene
brain = next(obj for obj in scene.objects if obj.type == 'MESH')
brain.name = 'BRAIN-ASTRA-002 | Original Tripo sculpt'
brain.data.name = 'Brain | source topology preserved'

# FBX presents the sculpt with a 90-degree X rotation and one-unit dimensions.
# Bake its existing orientation and uniformly scale it to a game-prop size.
# Translate only the pivot to its bounds center; vertex relationships stay intact.
brain.data.transform(brain.matrix_world)
brain.matrix_world = Matrix.Identity(4)
coords = [v.co.copy() for v in brain.data.vertices]
center = Vector(tuple((min(v[i] for v in coords) + max(v[i] for v in coords)) / 2 for i in range(3)))
for vertex in brain.data.vertices:
    vertex.co = (vertex.co - center) * 0.16
brain.data.update()
for poly in brain.data.polygons:
    poly.use_smooth = True

material = bpy.data.materials.new('01 | Soft matte warm brain pink')
material.use_nodes = True
base = (0.43, 0.185, 0.175, 1.0)  # linear RGB: muted peach-pink
material.diffuse_color = base
material.metallic = 0.0
material.roughness = 0.82
bsdf = material.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = base
bsdf.inputs['Metallic'].default_value = 0.0
bsdf.inputs['Roughness'].default_value = 0.82
bsdf.inputs['Diffuse Roughness'].default_value = 0.68
bsdf.inputs['Specular IOR Level'].default_value = 0.0
bsdf.inputs['Coat Weight'].default_value = 0.0
bsdf.inputs['Sheen Weight'].default_value = 0.0
brain.data.materials.clear()
brain.data.materials.append(material)

asset_col = bpy.data.collections.new('BRAIN-ASTRA-002 | Game Mesh')
scene.collection.children.link(asset_col)
for collection in tuple(brain.users_collection):
    collection.objects.unlink(brain)
asset_col.objects.link(brain)
studio = bpy.data.collections.new('Preview Studio | Not Exported')
scene.collection.children.link(studio)

world = bpy.data.worlds.new('Dark blue-gray organ-family studio')
scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get('Background')
background.inputs['Color'].default_value = (0.0165, 0.0235, 0.0365, 1.0)
background.inputs['Strength'].default_value = 0.48

def area(name, location, energy, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.shape = 'DISK'
    data.energy = energy
    data.size = size
    data.color = color
    data.specular_factor = 0.0
    obj = bpy.data.objects.new(name, data)
    studio.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (-obj.location).to_track_quat('-Z', 'Y').to_euler()

area('Large softbox left', (-0.27, -0.28, 0.22), 4.2, 0.30, (1.0, 0.987, 0.977))
area('Broad fill right', (0.30, -0.19, 0.09), 1.75, 0.22, (1.0, 0.817, 0.703))
area('Back edge softbox', (0.03, 0.27, 0.19), 2.95, 0.22, (0.735, 0.823, 1.0))

camera_data = bpy.data.cameras.new('Review Camera')
camera_data.type = 'ORTHO'
camera = bpy.data.objects.new('Review Camera', camera_data)
studio.objects.link(camera)
scene.camera = camera

scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if DRAFT else 96
scene.cycles.use_denoising = True
scene.render.resolution_x = 640 if DRAFT else 1000
scene.render.resolution_y = 640 if DRAFT else 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
scene.render.film_transparent = False
scene.unit_settings.system = 'METRIC'

def render(name, location, target=(0, 0, 0), scale=0.205):
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = scale
    scene.render.filepath = str(PREVIEWS / name)
    bpy.ops.render.render(write_still=True)

if DRAFT:
    render('draft_front.png', (0, -0.32, 0.035))
    render('draft_rear.png', (0, 0.32, 0.035))
    render('draft_side.png', (0.32, 0, 0.035))
else:
    bpy.ops.object.select_all(action='DESELECT')
    brain.select_set(True)
    bpy.context.view_layer.objects.active = brain
    bpy.ops.export_scene.fbx(filepath=str(ROOT / 'BRAIN-ASTRA-002.fbx'),
        use_selection=True, object_types={'MESH'}, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
        mesh_smooth_type='FACE', use_mesh_modifiers=True, add_leaf_bones=False,
        bake_anim=False, path_mode='AUTO')
    render('01_front.png', (0, -0.32, 0.035))
    render('02_left_three_quarter.png', (-0.23, -0.27, 0.04))
    render('03_right_three_quarter.png', (0.23, -0.27, 0.04))
    render('04_side.png', (0.32, 0, 0.035))
    render('05_rear.png', (0, 0.32, 0.035))
    render('06_surface_closeup.png', (-0.17, -0.22, 0.07), (-0.025, -0.025, 0.025), 0.12)
    camera.location = (0, -0.32, 0.035)
    camera.rotation_euler = (Vector((0, 0, 0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.ortho_scale = 0.205
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.shading.color_type = 'MATERIAL'
                area.spaces.active.region_3d.view_location = (0, 0, 0)
                area.spaces.active.region_3d.view_distance = 0.36
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'BRAIN-ASTRA-002.blend'))
