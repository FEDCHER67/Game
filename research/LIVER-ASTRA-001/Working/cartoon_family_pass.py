"""Material-only cartoon organ-family pass on approved LIVER-ASTRA-001."""
import shutil
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT / 'Previews'
TRIAL = '--trial' in sys.argv
scene = bpy.context.scene
meshes = [obj for obj in scene.objects if obj.type == 'MESH']
assert len(meshes) == 1
body = meshes[0]
mesh = body.data
assert len(mesh.vertices) == 7002 and sum(len(p.vertices)-2 for p in mesh.polygons) == 14000
assert len(mesh.materials) == 1

material = mesh.materials[0]
material.name = '01 | Matte warm cartoon terracotta liver'
color = (0.275, 0.044, 0.033, 1.0)  # Blender linear RGB
material.diffuse_color = color
material.roughness = 0.87
material.metallic = 0.0
shader = next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
shader.inputs['Base Color'].default_value = color
shader.inputs['Roughness'].default_value = 0.87
shader.inputs['Diffuse Roughness'].default_value = 0.68
shader.inputs['Specular IOR Level'].default_value = 0.0
shader.inputs['Metallic'].default_value = 0.0
shader.inputs['Coat Weight'].default_value = 0.0
shader.inputs['Sheen Weight'].default_value = 0.0

# Use the same near-neutral broad lighting language as the current kidneys.
studio = bpy.data.collections['Preview Studio | Not Exported']
for name, rgb in {
    'Large softbox left': (1.0, 1.0, 1.0),
    'Broad fill right': (1.0, 0.96, 0.93),
    'Back edge softbox': (0.94, 0.96, 1.0),
}.items():
    light = studio.objects[name].data
    light.color = rgb
    light.specular_factor = 0.0
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.60
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32 if TRIAL else 80
scene.cycles.use_denoising = True
scene.render.resolution_x = 720 if TRIAL else 1000
scene.render.resolution_y = 720 if TRIAL else 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'
scene.view_settings.exposure = 0
scene.view_settings.gamma = 1
camera = scene.camera


def render(path, location, target=(0, 0, 0), scale=0.265):
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print('PREVIEW_DONE', path)


if TRIAL:
    render(ROOT / 'Working' / 'liver_cartoon_trial_front.png', (0, -0.32, 0.035))
    render(ROOT / 'Working' / 'liver_cartoon_trial_side.png', (0.33, -0.025, 0.02), scale=0.225)
else:
    PREVIEWS.mkdir(exist_ok=True)
    camera.location = (0, -0.32, 0.035)
    camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = 0.265
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'LIVER-ASTRA-001.blend'))

    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.export_scene.fbx(
        filepath=str(ROOT / 'LIVER-ASTRA-001.fbx'), use_selection=True,
        object_types={'MESH'}, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
        mesh_smooth_type='FACE', use_mesh_modifiers=True,
        add_leaf_bones=False, bake_anim=False, path_mode='AUTO')

    views = [
        ('01_front_hero.png', (0, -0.32, 0.035), (0, 0, 0), 0.265),
        ('02_rear.png', (0, 0.32, 0.035), (0, 0, 0), 0.265),
        ('03_left_three_quarter.png', (-0.22, -0.28, 0.045), (0, 0, 0), 0.265),
        ('04_right_three_quarter.png', (0.22, -0.28, 0.045), (0, 0, 0), 0.265),
        ('05_side.png', (0.33, -0.025, 0.02), (0, 0, 0), 0.225),
        ('06_closeup.png', (-0.15, -0.23, 0.07), (-0.035, 0, 0.02), 0.145),
    ]
    for name, location, target, scale in views:
        render(PREVIEWS / name, location, target, scale)
    shutil.copyfile(PREVIEWS / '06_closeup.png', PREVIEWS / '06_surface_closeup.png')

    # Preserve the two existing supplemental review views.
    underside_fill_data = bpy.data.lights.new('Temporary underside review fill', 'AREA')
    underside_fill_data.shape = 'DISK'
    underside_fill_data.energy = 1.3
    underside_fill_data.size = 0.25
    underside_fill_data.color = (1.0, 0.96, 0.93)
    underside_fill_data.specular_factor = 0.0
    underside_fill = bpy.data.objects.new('Temporary underside review fill', underside_fill_data)
    studio.objects.link(underside_fill)
    underside_fill.location = (0, -0.12, -0.25)
    underside_fill.rotation_euler = (-underside_fill.location).to_track_quat('-Z', 'Y').to_euler()
    render(PREVIEWS / '07_bottom_or_underside.png', (0.03, -0.15, -0.32))
    bpy.data.objects.remove(underside_fill, do_unlink=True)

    neutral = bpy.data.materials.new('Preview only | neutral clay')
    neutral.diffuse_color = (0.42, 0.42, 0.42, 1)
    neutral.use_nodes = True
    neutral_shader = neutral.node_tree.nodes['Principled BSDF']
    neutral_shader.inputs['Base Color'].default_value = (0.42, 0.42, 0.42, 1)
    neutral_shader.inputs['Roughness'].default_value = 0.87
    neutral_shader.inputs['Specular IOR Level'].default_value = 0.0
    scene.view_layers[0].material_override = neutral
    render(PREVIEWS / '08_neutral_sculpt.png', (0, -0.32, 0.035))
    scene.view_layers[0].material_override = None
    bpy.data.materials.remove(neutral)
    print('FINAL_DONE', ROOT)
