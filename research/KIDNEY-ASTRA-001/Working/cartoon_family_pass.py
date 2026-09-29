"""Colour/material-only pass on the approved two-kidney Blender assembly."""
import bpy
import os
import shutil
import sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(r'C:\Dev\Game-main\research\KIDNEY-ASTRA-001')
PREVIEWS = ROOT / 'Previews'
TRIAL = '--trial' in sys.argv
scene = bpy.context.scene
asset = bpy.data.collections['KIDNEY-ASTRA-001 | Game Assembly']
studio = bpy.data.collections['Preview Studio | Not Exported']
meshes = sorted((o for o in asset.objects if o.type == 'MESH'), key=lambda o:o.name)
assert len(meshes) == 2
assert len(bpy.data.materials) == 2
assert sum(len(o.data.vertices) for o in meshes) == 18209

# Linear RGB: separate berry bodies and light coral-pink descending tubes.
palette = (
    ('01 | Matte warm brown red', '01 | Cartoon berry kidney', (0.300, 0.022, 0.050), 0.88),
    ('02 | Muted warm ureter', '02 | Soft coral-pink ureter', (0.650, 0.220, 0.230), 0.89),
)
for old_name, new_name, rgb, roughness in palette:
    mat = bpy.data.materials[old_name]
    mat.name = new_name
    mat.diffuse_color = (*rgb, 1.0)
    mat.metallic = 0.0
    mat.roughness = roughness
    shader = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    shader.inputs['Base Color'].default_value = (*rgb, 1.0)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = 0.0
    shader.inputs['Specular IOR Level'].default_value = 0.0
    shader.inputs['Coat Weight'].default_value = 0.0
    shader.inputs['Sheen Weight'].default_value = 0.0
    shader.inputs['Diffuse Roughness'].default_value = 0.68

# Neutral near-white broad lighting matches the current heart review studio.
lights = {
    'Large softbox left': (1.0, 1.0, 1.0),
    'Broad fill right': (1.0, 0.96, 0.93),
    'Back edge softbox': (0.94, 0.96, 1.0),
}
for name, rgb in lights.items():
    light = studio.objects[name].data
    light.color = rgb
    light.specular_factor = 0.0
world_bg = scene.world.node_tree.nodes['Background']
world_bg.inputs['Color'].default_value = (0.0165, 0.0235, 0.0365, 1.0)
world_bg.inputs['Strength'].default_value = 0.60

scene.render.engine = 'CYCLES'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.cycles.samples = 48 if TRIAL else 80
camera = scene.camera

def camera_view(loc, target, scale):
    camera.location = loc
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale = scale

def render(name, loc, target, scale):
    camera_view(loc,target,scale)
    scene.render.filepath = str(PREVIEWS/name)
    bpy.ops.render.render(write_still=True)
    print('PREVIEW_DONE',name)

hero = ((0.025,-0.32,0.028),(0.0,0.0,-0.025),0.245)
if TRIAL:
    camera_view(*hero)
    scene.render.filepath = str(ROOT/'Working'/'cartoon_trial.png')
    bpy.ops.render.render(write_still=True)
    print('TRIAL_DONE',scene.render.filepath)
else:
    PREVIEWS.mkdir(exist_ok=True)
    camera_view(*hero)
    scene.render.filepath = str(PREVIEWS/'01_front_hero.png')
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'KIDNEY-ASTRA-001.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    assert len(bpy.context.selected_objects)==2
    bpy.ops.export_scene.fbx(
        filepath=str(ROOT/'KIDNEY-ASTRA-001.fbx'), use_selection=True,
        object_types={'MESH'}, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
        mesh_smooth_type='FACE', use_mesh_modifiers=True,
        add_leaf_bones=False, bake_anim=False, path_mode='AUTO')
    render('01_front_hero.png',*hero)
    render('02_rear.png',(0.0,0.32,0.025),(0.0,0.0,-0.025),0.245)
    render('03_left_three_quarter.png',(-0.20,-0.29,0.042),(0.0,0.0,-0.025),0.245)
    render('04_right_three_quarter.png',(0.20,-0.29,0.042),(0.0,0.0,-0.025),0.245)
    render('05_side.png',(0.32,-0.025,0.02),(0.0,0.0,-0.025),0.22)
    scene.cycles.samples=96
    render('06_closeup.png',(-0.11,-0.23,0.030),(-0.066,0.0,0.005),0.135)
    shutil.copyfile(PREVIEWS/'06_closeup.png', PREVIEWS/'06_kidney_surface_closeup.png')
    render('07_hilum_connection_closeup.png',(0.02,-0.19,0.020),(0.053,0.0,-0.022),0.115)
    scene.cycles.samples=80
    render('08_full_pair_tubes.png',(0.0,-0.32,-0.025),(0.0,0.0,-0.025),0.245)
    neutral=bpy.data.materials.new('Preview only | neutral clay')
    neutral.diffuse_color=(0.42,0.42,0.42,1.0)
    neutral.use_nodes=True
    neutral.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.42,0.42,0.42,1.0)
    neutral.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=0.87
    scene.view_layers[0].material_override=neutral
    render('09_neutral_sculpt.png',(0.0,-0.32,0.025),(0.0,0.0,-0.025),0.245)
    scene.view_layers[0].material_override=None
    print('FINAL_DONE',str(ROOT/'KIDNEY-ASTRA-001.blend'),str(ROOT/'KIDNEY-ASTRA-001.fbx'))
