"""Colour the rear relief fused into the existing left lobe; keep geometry intact."""
import bpy
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
scene=bpy.context.scene
obj=bpy.data.objects['Lungs_Lobe_L']
rig=bpy.data.objects['Lungs_Breath_Rig']
demo=bpy.data.actions['Preview_GOOD_to_BAD_Transition']
static=bpy.data.actions['STATIC']
rig.animation_data.action=static
scene.frame_set(1)
camera=scene.camera
camera.location=(0,0.36,0.006)
camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=0.255
scene.render.resolution_x=650
scene.render.resolution_y=650
bpy.context.view_layer.update()

paths=[[(380,326),(397,342),(417,380),(447,443)],
       [(380,325),(405,286),(425,242),(430,222)],
       [(425,242),(413,202)],[(425,242),(451,224)],
       [(400,285),(439,263),(480,273),(515,300)],
       [(480,273),(500,255)],
       [(447,443),(500,442),(559,449)],
       [(460,442),(501,459),(553,486)],
       [(459,442),(486,476),(515,519)],
       [(447,443),(445,475),(437,511)]]
def distance_to_paths(point):
    x,y=point
    best=1e9
    for path in paths:
        for (ax,ay),(bx,by) in zip(path,path[1:]):
            dx=bx-ax;dy=by-ay
            t=max(0,min(1,((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
            best=min(best,((x-(ax+t*dx))**2+(y-(ay+t*dy))**2)**0.5)
    return best

vessels=bpy.data.materials['03 | Berry burgundy vessels']
if vessels.name not in [m.name for m in obj.data.materials]:
    obj.data.materials.append(vessels)
index=[m.name for m in obj.data.materials].index(vessels.name)
selected=0
for polygon in obj.data.polygons:
    centre=sum((obj.data.vertices[i].co for i in polygon.vertices),Vector())/len(polygon.vertices)
    image=world_to_camera_view(scene,camera,obj.matrix_world @ centre)
    pixel=(image.x*650,(1-image.y)*650)
    small_rear_face=(centre.y>0.012 and centre.x< -0.022 and -0.080<centre.z<0.057
        and polygon.area<0.00003 and distance_to_paths(pixel)<15)
    seam_bridge=polygon.index in {1193,1296,1295,1097,1114,1117,1170,1166}
    if small_rear_face or seam_bridge:
        polygon.material_index=index
        selected+=1
print('REAR_VESSEL_FACES',selected)

scene.render.resolution_x=1000
scene.render.resolution_y=1000
scene.cycles.samples=72
scene.render.image_settings.file_format='PNG'
def render(name,loc,target=(0,0,0),scale=0.255):
    camera.location=loc
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=scale
    scene.render.filepath=str(ROOT/'Previews'/name)
    bpy.ops.render.render(write_still=True)

render('02_rear.png',(0,0.36,0.006))
render('03_left_three_quarter.png',(-0.26,-0.32,0.026))
render('04_right_three_quarter.png',(0.26,-0.32,0.026))
render('05_side.png',(0.39,-0.03,0.016))

rig.animation_data.action=demo
scene.frame_set(1)
camera.location=(0,-0.36,0.006)
camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=0.255
scene.frame_start=1;scene.frame_end=150
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))

# Keep only the three gameplay actions during this export. The saved blend
# already contains the Blender-only transition demo.
rig.animation_data.action=static
bpy.data.actions.remove(demo)
asset=bpy.data.collections['LUNGS-ASTRA-001 | Game Assembly']
bpy.ops.object.select_all(action='DESELECT')
for item in asset.objects:item.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'LUNGS-ASTRA-001.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',
    axis_forward='-Z',axis_up='Y',mesh_smooth_type='FACE',use_mesh_modifiers=True,
    add_leaf_bones=False,use_armature_deform_only=True,bake_anim=True,bake_anim_use_all_bones=True,
    bake_anim_use_nla_strips=False,bake_anim_use_all_actions=True,bake_anim_step=1.0,
    bake_anim_simplify_factor=0.0,path_mode='STRIP')
