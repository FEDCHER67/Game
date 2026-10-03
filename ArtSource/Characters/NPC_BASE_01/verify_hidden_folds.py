"""Render check for v08+ elbows: no inside-out skin may be visible from outside.
Back faces of Skin_Warm are drawn pure red; a sleeve cut view must detect them
(positive control), every elbow view must stay free of red pixels."""
import bpy,json,math,argparse,sys
from pathlib import Path
from mathutils import Vector,Quaternion
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);p.add_argument('--revision',type=int,default=8)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.folder=a.folder.resolve()
report_file=a.folder/f'validation_v{a.revision:02d}.json'
bpy.ops.wm.open_mainfile(filepath=str(a.folder/f'NPC_BASE_01_v{a.revision:02d}.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['NPC_Rig_Mixamo65'];cam=scene.camera
scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=scene.render.resolution_y=240
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
bpy.data.objects['Preview_Floor'].hide_render=True
skin=bpy.data.materials['Skin_Warm'];nt=skin.node_tree;out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
geo=nt.nodes.new('ShaderNodeNewGeometry');red=nt.nodes.new('ShaderNodeEmission');red.inputs['Color'].default_value=(1,0,0,1)
mix=nt.nodes.new('ShaderNodeMixShader');nt.links.new(out.inputs['Surface'].links[0].from_socket,mix.inputs[1])
nt.links.new(red.outputs[0],mix.inputs[2]);nt.links.new(geo.outputs['Backfacing'],mix.inputs['Fac']);nt.links.new(mix.outputs[0],out.inputs['Surface'])
skin.use_backface_culling=False
tmp=Path(bpy.app.tempdir)/'hidden_fold.png'
def shot(target,direction,scale,clip=.1):
    d=Vector(direction).normalized()*4;cam.location=target+d;cam.data.ortho_scale=scale;cam.data.clip_start=clip
    cam.rotation_euler=(-d).to_track_quat('-Z','Y' if abs(d.normalized().z)<.99 else 'X').to_euler()
    scene.render.filepath=str(tmp);bpy.ops.render.render(write_still=True)
    img=bpy.data.images.load(str(tmp));px=np.array(img.pixels[:]).reshape(-1,4);bpy.data.images.remove(img)
    return int(((px[:,0]>.8)&(px[:,1]<.25)&(px[:,2]<.25)).sum())
views=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1),(1,1,1),(-1,-1,1),(1,-1,-1),(-1,1,-1)]
action=rig.animation_data.action
rig.data.pose_position='REST'
control=shot(Vector((.27,0,1.177)),(1,0,0),.2,clip=3.99)   # looks into the cut arm inside the sleeve
assert control>1000,control
rig.data.pose_position='POSE';rig.animation_data.action=None;results={}
for deg in [60,80,100,120,135]:
    for b in rig.pose.bones:b.rotation_quaternion=Quaternion();b.location=(0,0,0)
    for side,sign in [('Left',-1),('Right',1)]:
        b=rig.pose.bones['mixamorig:%sForeArm'%side];b.rotation_quaternion=Quaternion(b.bone.matrix_local.to_3x3().inverted()@Vector((0,0,1)),math.radians(sign*deg))
    bpy.context.view_layer.update()
    for side in ['Left','Right']:
        j=rig.matrix_world@rig.pose.bones['mixamorig:%sForeArm'%side].head
        results['Elbow%d_%s'%(deg,side)]=sum(shot(j,d,.35) for d in views)
rig.animation_data.action=action
for f in range(1,69,3):
    scene.frame_set(f)
    for side in ['Left','Right']:
        j=rig.matrix_world@rig.pose.bones['mixamorig:%sForeArm'%side].head
        results['run%d_%s'%(f,side)]=sum(shot(j,d,.35) for d in views)
bad={k:v for k,v in results.items() if v}
latest=json.loads(report_file.read_text())
latest['hidden_fold_check']={'status':'PASS' if not bad else 'FAIL','positive_control_red_pixels':control,'views_per_case':len(views),'cases':len(results),'visible_backface_pixels':bad}
report_file.write_text(json.dumps(latest,indent=2),encoding='utf-8')
print('HIDDEN_FOLDS',json.dumps(latest['hidden_fold_check']))
assert not bad,'Inside-out elbow skin is visible; inspect the listed cases.'
