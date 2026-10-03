"""Small targeted review of neckline, elbow and thumb on the actual saved mesh."""
import bpy,bmesh,argparse,sys,math
from pathlib import Path
from mathutils import Vector,Quaternion
p=argparse.ArgumentParser();p.add_argument('--blend',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.blend=a.blend.resolve();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(a.blend));scene=bpy.context.scene;rig=bpy.data.objects['NPC_Rig_Mixamo65'];body=bpy.data.objects['Body_Base'];cam=scene.camera
scene.render.resolution_x=700;scene.render.resolution_y=700;scene.cycles.samples=16
def draw(name,target,offset,scale):
    cam.location=target+offset;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath=str(a.out/(name+'.png'));bpy.ops.render.render(write_still=True)
rig.data.pose_position='REST'
draw('Neckline_Rest',Vector((0,-.01,1.21)),Vector((.5,-3,1.3)),.67)
rig.data.pose_position='POSE';scene.frame_set(60)
draw('Upper_Run60',Vector((0,0,1.27)),Vector((1,-3,1)),.97)
scene.frame_set(63)
draw('Elbow_Run63',rig.matrix_world@rig.pose.bones['mixamorig:LeftForeArm'].head,Vector((2,-5,3)),.50)
for obj in bpy.data.collections['NPC_BASE_01'].objects:
    if obj.type=='MESH':obj.hide_render=True
def hand(name):
    bpy.context.view_layer.update();e=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=bpy.data.meshes.new_from_object(e)
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.verts[v.index] for v in body.data.vertices if v.co.x<.60],context='VERTS');bm.to_mesh(mesh);bm.free()
    obj=bpy.data.objects.new('ReviewOnly',mesh);scene.collection.objects.link(obj);obj.matrix_world=e.matrix_world
    bone=rig.pose.bones['mixamorig:LeftHand'];transform=rig.matrix_world@bone.matrix@bone.bone.matrix_local.inverted()
    draw(name,transform@Vector((.733,-.037,1.168)),transform.to_3x3()@Vector((.2,-.8,3)).normalized()*.55,.265)
    bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
scene.frame_set(20);hand('Thumb_Run20')
scene.frame_set(60);hand('Thumb_Run60')
rig.animation_data.action=None
def reset():
    for bone in rig.pose.bones:bone.location=(0,0,0);bone.rotation_quaternion=Quaternion();bone.scale=(1,1,1)
def rotate(name,axis,angle):
    b=rig.pose.bones['mixamorig:'+name];b.rotation_quaternion=Quaternion(b.bone.matrix_local.to_3x3().inverted()@Vector(axis),math.radians(angle))
reset();hand('Hand_Rest')
rotate('LeftHandThumb1',(0,0,1),-35);hand('Thumb_Spread')
reset();rotate('LeftHandThumb2',(.73,.68,0),55);rotate('LeftHandThumb3',(.73,.68,0),25);hand('Thumb_Flex')
