"""Build the stylized lungs and three exportable skeletal breathing states."""
import bpy
import json
import math
import os
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
PREVIEWS = ROOT / 'Previews'
PREVIEWS.mkdir(exist_ok=True)
DRAFT = os.environ.get('LUNGS_DRAFT') == '1'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 28 if DRAFT else 72
scene.cycles.use_denoising = True
scene.render.resolution_x = 650 if DRAFT else 1000
scene.render.resolution_y = 650 if DRAFT else 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 51
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'None'

asset_col = bpy.data.collections.new('LUNGS-ASTRA-001 | Game Assembly')
scene.collection.children.link(asset_col)
studio_col = bpy.data.collections.new('Preview Studio | Not Exported')
scene.collection.children.link(studio_col)

bpy.ops.import_scene.fbx(filepath=str(ROOT / 'Working' / 'Tripo' / 'lungs_tripo_base.fbx'))
source = next(o for o in bpy.data.objects if o.type == 'MESH')
bpy.ops.object.select_all(action='DESELECT')
source.select_set(True)
bpy.context.view_layer.objects.active = source
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
# The source uses an approximately metre-tall authoring scale. Match the
# approved small game-prop organ family and place the pivot at the pair centre.
for v in source.data.vertices:
    v.co = v.co * 0.22 - Vector((0, 0, 0.1008))
source.data.update()
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.separate(type='LOOSE')
bpy.ops.object.mode_set(mode='OBJECT')
parts = [o for o in bpy.context.selected_objects if o.type == 'MESH']

def material(name, color, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = (*color, 1)
    mat.roughness = roughness
    mat.metallic = 0
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Specular IOR Level'].default_value = 0
    bsdf.inputs['Diffuse Roughness'].default_value = 0.68
    bsdf.inputs['Metallic'].default_value = 0
    bsdf.inputs['Coat Weight'].default_value = 0
    bsdf.inputs['Sheen Weight'].default_value = 0
    return mat

LOBE = material('01 | Dry muted coral lung', (0.29, 0.082, 0.075), 0.84)
TRACHEA = material('02 | Soft dusty rose airway', (0.23, 0.082, 0.070), 0.84)
DETAIL = material('03 | Quiet warm branch relief', (0.245, 0.074, 0.068), 0.86)

named = {}
for obj in parts:
    verts = [v.co for v in obj.data.vertices]
    center = sum(verts, Vector()) / len(verts)
    side = 'L' if center.x < 0 else 'R'
    if abs(center.x) < 0.025:
        role = 'Trachea'; mat = TRACHEA
    elif len(verts) > 900:
        role = 'Lobe'; mat = LOBE
    else:
        role = 'BranchRear' if center.y > 0 else 'BranchFront'
        mat = DETAIL
        # Small placement pass: lift and gather the embossed branch forms so
        # their endpoints sit more deliberately within each lobe's mass.
        scale_x = 0.965 if role == 'BranchFront' else 0.975
        scale_z = 0.975 if role == 'BranchFront' else 0.98
        for v in obj.data.vertices:
            p = v.co.copy()
            p.x = center.x + (p.x - center.x) * scale_x + (-0.0009 if side == 'R' else 0.0009)
            p.z = center.z + (p.z - center.z) * scale_z + 0.0015
            v.co = p
        obj.data.update()
    obj.name = f'Lungs_{role}_{side}' if role != 'Trachea' else 'Lungs_Trachea_Bronchi'
    obj.data.name = obj.name + '_Mesh'
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    for col in tuple(obj.users_collection):
        col.objects.unlink(obj)
    asset_col.objects.link(obj)
    named[obj.name] = obj

arm_data = bpy.data.armatures.new('Lungs_Breath_Rig_Data')
rig = bpy.data.objects.new('Lungs_Breath_Rig', arm_data)
asset_col.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
root = arm_data.edit_bones.new('Root_Static_Airway')
root.head = (0, 0, -0.09); root.tail = (0, 0, -0.015)
for side, x in [('L', -0.056), ('R', 0.056)]:
    bone = arm_data.edit_bones.new('Lobe_' + side)
    bone.head = (x, 0, -0.022)
    bone.tail = (x, 0, 0.034)
    bone.parent = root
    bone.use_connect = False
bpy.ops.object.mode_set(mode='OBJECT')
rig.show_in_front = True

for obj in parts:
    groups = {name: obj.vertex_groups.new(name=name) for name in ('Root_Static_Airway', 'Lobe_L', 'Lobe_R')}
    if 'Trachea' in obj.name:
        for vert in obj.data.vertices:
            p = vert.co
            side = 'Lobe_L' if p.x < 0 else 'Lobe_R'
            lateral = max(0.0, min(1.0, (abs(p.x) - 0.009) / 0.020))
            lower = max(0.0, min(1.0, (0.058 - p.z) / 0.050))
            follower = 0.78 * lateral * lower
            groups['Root_Static_Airway'].add([vert.index], 1.0-follower, 'REPLACE')
            if follower > 0:
                groups[side].add([vert.index], follower, 'REPLACE')
    else:
        group = groups['Lobe_L' if obj.name.endswith('_L') else 'Lobe_R']
        group.add(list(range(len(obj.data.vertices))), 1.0, 'REPLACE')
    obj.parent = rig
    mod = obj.modifiers.new('Breathing skin', 'ARMATURE')
    mod.object = rig
    mod.use_deform_preserve_volume = True

def add_action(name, last, peak, amount):
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    if not rig.animation_data:
        rig.animation_data_create()
    rig.animation_data.action = action
    for frame, factor in [(1, 0), (peak, 1), (last, 0)]:
        for side, asym in [('L', 1.0), ('R', 0.96)]:
            bone = rig.pose.bones['Lobe_' + side]
            bone.scale = (1 + amount[0]*factor*asym,
                          1 + amount[1]*factor*asym,
                          1 + amount[2]*factor*asym)
            bone.keyframe_insert(data_path='scale', frame=frame, group=bone.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:
                        key.interpolation = 'BEZIER'
                        key.handle_left_type = 'AUTO_CLAMPED'
                        key.handle_right_type = 'AUTO_CLAMPED'
    return action

STATIC = add_action('STATIC_Rest', 2, 1.5, (0, 0, 0))
GOOD = add_action('GOOD_Breathe_50f', 51, 20, (0.105, 0.050, 0.055))
BAD = add_action('BAD_Distress_24f', 25, 9, (0.135, 0.070, 0.070))
rig.animation_data.action = STATIC
scene.frame_set(1)

world = bpy.data.worlds.new('Organ Family Studio World')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0165, 0.0235, 0.0365, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.48
scene.world = world

def light(name, loc, power, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.shape = 'DISK'; data.size = size; data.energy = power
    data.color = color; data.specular_factor = 0
    obj = bpy.data.objects.new(name, data)
    studio_col.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (-obj.location).to_track_quat('-Z', 'Y').to_euler()

light('Large softbox left', (-0.24,-0.24,0.28), 1.86,0.201,(1.0,0.987,0.977))
light('Broad fill right', (0.24,-0.16,0.11),0.775,0.147,(1.0,0.817,0.703))
light('Back edge softbox', (0.02,0.24,0.18),1.31,0.146,(0.735,0.823,1.0))
camera_data = bpy.data.cameras.new('Review Camera')
camera = bpy.data.objects.new('Review Camera',camera_data)
studio_col.objects.link(camera)
camera_data.type = 'ORTHO'
scene.camera = camera

def render(name, loc, target=(0,0,0), scale=0.255, action=STATIC, frame=1):
    rig.animation_data.action = action
    scene.frame_set(frame)
    camera.location = loc
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera_data.ortho_scale = scale
    scene.render.filepath = str(PREVIEWS / name) if not DRAFT else str(ROOT / 'Working' / ('draft_'+name))
    bpy.ops.render.render(write_still=True)

if DRAFT:
    render('01_front_hero.png',(0,-0.36,0.006))
    render('08_good_expanded.png',(0,-0.36,0.006),action=GOOD,frame=20)
    render('09_bad_expanded.png',(0,-0.36,0.006),action=BAD,frame=9)
else:
    render('01_front_hero.png',(0,-0.36,0.006))
    render('02_rear.png',(0,0.36,0.006))
    render('03_left_three_quarter.png',(-0.26,-0.32,0.026))
    render('04_right_three_quarter.png',(0.26,-0.32,0.026))
    render('05_side.png',(0.39,-0.03,0.016))
    render('06_closeup.png',(-0.09,-0.26,-0.004),target=(-0.055,0,-0.012),scale=0.145)
    render('07_static_rest.png',(0,-0.36,0.006),action=STATIC)
    render('08_good_expanded.png',(0,-0.36,0.006),action=GOOD,frame=20)
    render('09_bad_expanded.png',(0,-0.36,0.006),action=BAD,frame=9)
    rig.animation_data.action = STATIC
    scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / 'LUNGS-ASTRA-001.blend'))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in asset_col.objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(ROOT / 'LUNGS-ASTRA-001.fbx'),use_selection=True,
        object_types={'MESH','ARMATURE'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE',use_mesh_modifiers=True,
        add_leaf_bones=False,use_armature_deform_only=True,bake_anim=True,bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,bake_anim_use_all_actions=True,bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,path_mode='STRIP')
    metrics = {'parts': {o.name: {'vertices':len(o.data.vertices),'triangles':sum(len(p.vertices)-2 for p in o.data.polygons)} for o in parts},
               'actions':{a.name:list(a.frame_range) for a in (STATIC,GOOD,BAD)},
               'materials':{m.name:{'color':list(m.diffuse_color),'roughness':m.roughness} for m in (LOBE,TRACHEA,DETAIL)}}
    with open(ROOT/'Working'/'build_metrics.json','w') as f: json.dump(metrics,f,indent=2)
    print('BUILD_METRICS',json.dumps(metrics))
