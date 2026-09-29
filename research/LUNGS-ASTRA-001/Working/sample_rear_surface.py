import bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
scene=bpy.context.scene
rig=bpy.data.objects['Lungs_Breath_Rig'];rig.animation_data.action=bpy.data.actions['STATIC'];scene.frame_set(1)
cam=scene.camera;cam.location=(0,0.36,0.006);cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=0.255
deps=bpy.context.evaluated_depsgraph_get()
for px,py in [(385,325),(397,313),(405,300),(410,365),(420,382),(431,397),(440,412),(450,420),(490,430),(460,470)]:
    sx=(px/650-0.5)*cam.data.ortho_scale;sy=(0.5-py/650)*cam.data.ortho_scale
    origin=cam.matrix_world @ Vector((sx,sy,0))
    direction=cam.matrix_world.to_quaternion() @ Vector((0,0,-1))
    hit,loc,norm,face,obj,_=scene.ray_cast(deps,origin,direction)
    print(px,py,hit,obj.name if obj else None,tuple(round(v,5) for v in loc),tuple(round(v,3) for v in norm),face)
