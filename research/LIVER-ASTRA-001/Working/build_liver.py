"""Build a clean stylized liver from Faqihcuk's exterior mass.

The donor archive is intentionally read only. ElliotSS's source is used solely
as a color reference; no donor texture is loaded into the finished scene.
"""
import os
import tempfile
import zipfile
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
FAQIHCuk_ZIP = REPO / '_reference' / 'liver_sources' / 'ElliotSS_HumanLiver' / 'liver-organ.zip'
PREVIEWS = ROOT / 'Previews'
PREVIEWS.mkdir(exist_ok=True)
DRAFT = os.environ.get('LIVER_DRAFT') == '1'

bpy.ops.wm.read_factory_settings(use_empty=True)
with tempfile.TemporaryDirectory(prefix='liver_astra_') as temp_dir:
    glb_path = Path(temp_dir) / 'LIVER.glb'
    with zipfile.ZipFile(FAQIHCuk_ZIP) as archive:
        glb_path.write_bytes(archive.read('source/LIVER.glb'))
    bpy.ops.import_scene.gltf(filepath=str(glb_path))

# The supplied GLB contains four meshes. Only mesh_id36 is the external liver
# body; the three remaining medical elements are removed from the final file.
donor = bpy.data.objects['mesh_id36']
world_vertices = [donor.matrix_world @ v.co for v in donor.data.vertices]
faces = [tuple(p.vertices) for p in donor.data.polygons]
center = Vector(tuple((min(v[i] for v in world_vertices) + max(v[i] for v in world_vertices)) / 2 for i in range(3)))
width = max(v.x for v in world_vertices) - min(v.x for v in world_vertices)
uniform_scale = 0.205 / width
vertices = []
for v in world_vertices:
    p = (v-center) * uniform_scale
    p.y *= 1.16  # Give the broad prop modest depth without changing its front silhouette.
    vertices.append(p)
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for imported_mesh in list(bpy.data.meshes):
    if imported_mesh.users == 0:
        bpy.data.meshes.remove(imported_mesh)
for imported_material in list(bpy.data.materials):
    if imported_material.users == 0:
        bpy.data.materials.remove(imported_material)
for imported_image in list(bpy.data.images):
    if imported_image.users == 0:
        bpy.data.images.remove(imported_image)

mesh = bpy.data.meshes.new('Liver | rebuilt exterior surface')
mesh.from_pydata(vertices, [], faces)
mesh.update()
body = bpy.data.objects.new('LIVER-ASTRA-001 | clean organ body', mesh)
bpy.context.scene.collection.objects.link(body)
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bpy.context.view_layer.objects.active = body

# The donor exterior is open and has small lower-surface irregularities.
# Voxel remeshing closes the body and discards fine medical scan detail.
mesh.remesh_voxel_size = 0.0024
mesh.use_remesh_preserve_volume = True
bpy.ops.object.voxel_remesh()
smooth = body.modifiers.new('Broad form relaxation', 'SMOOTH')
smooth.factor = 1.2
smooth.iterations = 5
bpy.ops.object.modifier_apply(modifier=smooth.name)
current_triangles = sum(len(p.vertices)-2 for p in body.data.polygons)
if current_triangles > 14000:
    reduce = body.modifiers.new('Game mesh reduction', 'DECIMATE')
    reduce.ratio = 14000/current_triangles
    bpy.ops.object.modifier_apply(modifier=reduce.name)
smooth_final = body.modifiers.new('Final large form polish', 'SMOOTH')
smooth_final.factor = 0.55
smooth_final.iterations = 2
bpy.ops.object.modifier_apply(modifier=smooth_final.name)
for poly in body.data.polygons:
    poly.use_smooth = True
body.data.update()
print('BUILD_MESH', len(body.data.vertices),
      sum(len(poly.vertices)-2 for poly in body.data.polygons))

# UV0 is kept for future engine integration; the final material is solid color.
if not body.data.uv_layers:
    body.data.uv_layers.new(name='UV0')
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(island_margin=0.015)
bpy.ops.object.mode_set(mode='OBJECT')
body.data.uv_layers.active.name = 'UV0'

material = bpy.data.materials.new('01 | Matte warm liver burgundy')
material.use_nodes = True
base = (0.19, 0.054, 0.040, 1.0)
material.diffuse_color = base
material.metallic = 0.0
material.roughness = 0.82
shader = material.node_tree.nodes.get('Principled BSDF')
shader.inputs['Base Color'].default_value = base
shader.inputs['Metallic'].default_value = 0
shader.inputs['Roughness'].default_value = 0.82
shader.inputs['Diffuse Roughness'].default_value = 0.68
shader.inputs['Specular IOR Level'].default_value = 0
shader.inputs['Coat Weight'].default_value = 0
shader.inputs['Sheen Weight'].default_value = 0
body.data.materials.clear()
body.data.materials.append(material)

scene = bpy.context.scene
asset_col = bpy.data.collections.new('LIVER-ASTRA-001 | Game Mesh')
scene.collection.children.link(asset_col)
for collection in tuple(body.users_collection):
    collection.objects.unlink(body)
asset_col.objects.link(body)
studio = bpy.data.collections.new('Preview Studio | Not Exported')
scene.collection.children.link(studio)
world = bpy.data.worlds.new('Organ-family dark blue-gray')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0165,0.0235,0.0365,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.48
scene.world = world

def area(name, position, energy, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.shape = 'DISK'
    data.energy = energy
    data.size = size
    data.color = color
    data.specular_factor = 0
    obj = bpy.data.objects.new(name, data)
    studio.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj

area('Large softbox left', (-0.27,-0.25,0.20), 3.5, 0.28, (1.0,0.987,0.977))
area('Broad fill right', (0.27,-0.17,0.10), 1.45, 0.22, (1.0,0.817,0.703))
area('Back edge softbox', (0.02,0.25,0.17), 2.45, 0.22, (0.735,0.823,1.0))
cam_data = bpy.data.cameras.new('Review Camera')
cam_data.type = 'ORTHO'
cam = bpy.data.objects.new('Review Camera', cam_data)
studio.objects.link(cam)
scene.camera = cam
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if DRAFT else 96
scene.cycles.use_denoising = True
scene.render.resolution_x = 650 if DRAFT else 1000
scene.render.resolution_y = 650 if DRAFT else 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'
scene.unit_settings.system = 'METRIC'

def render(name, location, target=(0,0,0), scale=0.265):
    cam.location = location
    cam.rotation_euler = (Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam_data.ortho_scale = scale
    scene.render.filepath = str(PREVIEWS / name)
    bpy.ops.render.render(write_still=True)

if DRAFT:
    render('draft_front.png', (0,-0.32,0.035))
    render('draft_rear.png', (0,0.32,0.035))
    underside_fill = area('Temporary underside review fill', (0,-0.12,-0.25), 1.3, 0.25, (1.0,0.90,0.84))
    render('draft_underside.png', (0.03,-0.15,-0.32))
    bpy.data.objects.remove(underside_fill, do_unlink=True)
else:
    bpy.ops.object.select_all(action='DESELECT')
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'LIVER-ASTRA-001.fbx'),
        use_selection=True, object_types={'MESH'}, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL', axis_forward='-Z', axis_up='Y',
        mesh_smooth_type='FACE', use_mesh_modifiers=True, add_leaf_bones=False,
        bake_anim=False, path_mode='AUTO')
    render('01_front_hero.png', (0,-0.32,0.035))
    render('02_rear.png', (0,0.32,0.035))
    render('03_left_three_quarter.png', (-0.22,-0.28,0.045))
    render('04_right_three_quarter.png', (0.22,-0.28,0.045))
    render('05_side.png', (0.33,-0.025,0.02), scale=0.225)
    render('06_surface_closeup.png', (-0.15,-0.23,0.07), (-0.035,0,0.02), 0.145)
    underside_fill = area('Temporary underside review fill', (0,-0.12,-0.25), 1.3, 0.25, (1.0,0.90,0.84))
    render('07_bottom_or_underside.png', (0.03,-0.15,-0.32))
    bpy.data.objects.remove(underside_fill, do_unlink=True)
    neutral = bpy.data.materials.new('Preview only | neutral clay')
    neutral.use_nodes = True
    neutral.diffuse_color = (0.42,0.42,0.42,1)
    node = neutral.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (0.42,0.42,0.42,1)
    node.inputs['Roughness'].default_value = 0.87
    node.inputs['Specular IOR Level'].default_value = 0
    scene.view_layers[0].material_override = neutral
    render('08_neutral_sculpt.png', (0,-0.32,0.035))
    scene.view_layers[0].material_override = None
    bpy.data.materials.remove(neutral)
    cam.location = (0,-0.32,0.035)
    cam.rotation_euler = (-cam.location).to_track_quat('-Z','Y').to_euler()
    cam_data.ortho_scale = 0.265
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.shading.color_type = 'MATERIAL'
                area.spaces.active.region_3d.view_location = (0,0,0)
                area.spaces.active.region_3d.view_distance = 0.40
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'LIVER-ASTRA-001.blend'))
