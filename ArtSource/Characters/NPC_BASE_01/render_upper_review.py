"""Close review renders of the collar, sleeves, elbow and animated hands."""
import argparse,sys,math
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--revision',type=int,default=5)
p.add_argument('--hands-only',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(a.folder/f'NPC_BASE_01_v{a.revision:02d}.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['NPC_Rig_Mixamo65'];cam=scene.camera
out=a.folder/'Previews'/f'v{a.revision:02d}';out.mkdir(parents=True,exist_ok=True)
scene.render.resolution_x=800;scene.render.resolution_y=800;scene.cycles.samples=24
def render(name,target,offset,scale):
    cam.location=target+offset;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
for frame in ([] if a.hands_only else [1,11,20,40,60]):
    scene.frame_set(frame)
    render(f'Upper_{frame:03d}',Vector((0,0,1.18)),Vector((2,-5,1.7)),.91)
elbow_angles={}
for frame in range(1,69):
    scene.frame_set(frame);q=rig.pose.bones['mixamorig:LeftForeArm'].rotation_quaternion
    elbow_angles[frame]=min(q.angle,2*math.pi-q.angle)
frame=max(elbow_angles,key=elbow_angles.get);scene.frame_set(frame)
if not a.hands_only:render(f'Elbow_Max_{frame:03d}',rig.matrix_world@rig.pose.bones['mixamorig:LeftForeArm'].head,Vector((2,-5,3)),.52)
# Isolate the actually deformed wrist/hand for close inspection. Other limbs and
# shoes can occlude a palm-facing camera; the delivered blend remains untouched.
body=bpy.data.objects['Body_Base']
for obj in bpy.data.collections['NPC_BASE_01'].objects:
    if obj.type=='MESH':obj.hide_render=True
for side in ['Left','Right']:
    for frame in [1,20,40,60]:
        scene.frame_set(frame)
        sign=1 if side=='Left' else -1
        evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=bpy.data.meshes.new_from_object(evaluated)
        assert len(mesh.vertices)==len(body.data.vertices)
        bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
        remove=[bm.verts[v.index] for v in body.data.vertices if sign*v.co.x<.58]
        bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(mesh);bm.free()
        isolated=bpy.data.objects.new('AnimatedHandReview',mesh);scene.collection.objects.link(isolated)
        isolated.matrix_world=evaluated.matrix_world
        rest=rig.data.bones['mixamorig:'+side+'Hand'].matrix_local
        transform=rig.matrix_world@rig.pose.bones['mixamorig:'+side+'Hand'].matrix@rest.inverted()
        target=transform@Vector((sign*.735,-.02,1.168))
        offset=transform.to_3x3()@Vector((sign*.3,-.8,3)).normalized()*.55
        render(f'Hand_{side}_{frame:03d}',target,offset,.31)
        if frame in [20,60]:
            offset=transform.to_3x3()@Vector((sign*.1,-.8,-3)).normalized()*.55
            render(f'Palm_{side}_{frame:03d}',target,offset,.31)
        bpy.data.objects.remove(isolated,do_unlink=True);bpy.data.meshes.remove(mesh)
print('DETAIL_REVIEW_RENDERED',str(out))
