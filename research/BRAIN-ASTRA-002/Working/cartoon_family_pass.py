"""Material-only cartoon organ-family pass on the approved BRAIN-ASTRA-002."""
import sys
import shutil
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT / 'Previews'
TRIAL = '--trial' in sys.argv
scene = bpy.context.scene
brain = next(obj for obj in scene.objects if obj.type == 'MESH')
mesh = brain.data
assert len([obj for obj in scene.objects if obj.type == 'MESH']) == 1
assert len(mesh.vertices) == 4138 and len(mesh.polygons) == 4870
assert len(mesh.materials) == 1


def set_matte(material, rgb, roughness):
    rgba = (*rgb, 1.0)
    material.use_nodes = True
    material.diffuse_color = rgba
    material.roughness = roughness
    material.metallic = 0.0
    shader = next(node for node in material.node_tree.nodes
                  if node.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = rgba
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Diffuse Roughness'].default_value = 0.68
    shader.inputs['Metallic'].default_value = 0.0
    shader.inputs['Specular IOR Level'].default_value = 0.0
    shader.inputs['Coat Weight'].default_value = 0.0
    shader.inputs['Sheen Weight'].default_value = 0.0


body = mesh.materials[0]
body.name = '01 | Cartoon warm peach-pink brain'
set_matte(body, (0.66, 0.19, 0.23), 0.86)
stem = bpy.data.materials.get('02 | Matte deeper coral-rose stem')
if stem is None:
    stem = bpy.data.materials.new('02 | Matte deeper coral-rose stem')
set_matte(stem, (0.54, 0.14, 0.165), 0.87)
mesh.materials.append(stem)

# The approved sculpt is a single mesh. Assign a second material to the
# existing lower central stem faces; do not move, delete or add any geometry.
stem_faces = 0
for polygon in mesh.polygons:
    center = polygon.center
    if center.z < -0.039 and abs(center.x) < 0.021 and center.y > 0.0:
        polygon.material_index = 1
        stem_faces += 1
assert 50 < stem_faces < 250, stem_faces
mesh.update()
print('STEM_FACES', stem_faces)

studio = bpy.data.collections['Preview Studio | Not Exported']
for name, color in {
    'Large softbox left': (1.0, 1.0, 1.0),
    'Broad fill right': (1.0, 0.96, 0.93),
    'Back edge softbox': (0.94, 0.96, 1.0),
}.items():
    light = studio.objects[name].data
    light.color = color
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


def render(name, location, target=(0, 0, 0), scale=0.205):
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale
    scene.render.filepath = str(name)
    bpy.ops.render.render(write_still=True)
    print('PREVIEW_DONE', name)


if TRIAL:
    render(ROOT / 'Working' / 'brain_cartoon_trial_front.png', (0, -0.32, 0.035))
    render(ROOT / 'Working' / 'brain_cartoon_trial_rear.png', (0, 0.32, 0.035))
else:
    PREVIEWS.mkdir(exist_ok=True)
    camera.location = (0, -0.32, 0.035)
    camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = 0.205
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'BRAIN-ASTRA-002.blend'))

    bpy.ops.object.select_all(action='DESELECT')
    brain.select_set(True)
    bpy.context.view_layer.objects.active = brain
    bpy.ops.export_scene.fbx(
        filepath=str(ROOT / 'BRAIN-ASTRA-002.fbx'), use_selection=True,
        object_types={'MESH'}, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
        mesh_smooth_type='FACE', use_mesh_modifiers=True,
        add_leaf_bones=False, bake_anim=False, path_mode='AUTO')

    views = [
        ('01_front_hero.png', (0, -0.32, 0.035), (0, 0, 0), 0.205),
        ('02_rear.png', (0, 0.32, 0.035), (0, 0, 0), 0.205),
        ('03_left_three_quarter.png', (-0.23, -0.27, 0.04), (0, 0, 0), 0.205),
        ('04_right_three_quarter.png', (0.23, -0.27, 0.04), (0, 0, 0), 0.205),
        ('05_side.png', (0.32, 0, 0.035), (0, 0, 0), 0.205),
        ('06_closeup.png', (-0.17, -0.22, 0.07), (-0.025, -0.025, 0.025), 0.12),
    ]
    for name, location, target, scale in views:
        render(PREVIEWS / name, location, target, scale)

    # Keep legacy preview filenames in sync for existing documentation links.
    for new, legacy in {
        '01_front_hero.png': '01_front.png',
        '02_rear.png': '05_rear.png',
        '03_left_three_quarter.png': '02_left_three_quarter.png',
        '04_right_three_quarter.png': '03_right_three_quarter.png',
        '05_side.png': '04_side.png',
        '06_closeup.png': '06_surface_closeup.png',
    }.items():
        shutil.copyfile(PREVIEWS / new, PREVIEWS / legacy)
    print('FINAL_DONE', ROOT)
