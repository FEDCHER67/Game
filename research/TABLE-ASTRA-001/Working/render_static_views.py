import bpy
from pathlib import Path
from mathutils import Vector
R=Path(r'C:\Dev\Game-main\research\TABLE-ASTRA-001')
bpy.ops.wm.open_mainfile(filepath=str(R/'TABLE-ASTRA-001.blend'))
scene=bpy.context.scene;camera=bpy.data.objects['PREVIEW_Camera'];scene.camera=camera
points=[o.matrix_world@v.co for o in bpy.data.collections['TABLE_ASTRA_Geometry'].objects for v in o.data.vertices]
center=Vector((0,0,.42))
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
scene.render.resolution_x=1280;scene.render.resolution_y=960;scene.render.resolution_percentage=100
views=(('01_front',(0,3,1.15)),('02_left',(3,0,1.05)),('03_right',(-3,0,1.05)),
       ('04_back',(0,-3,1.15)),('05_three_quarter',(2.5,2.8,1.9)),('06_high_three_quarter',(-2.3,-2.7,2.8)))
for name,offset in views:
    camera.location=center+Vector(offset)
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    bpy.context.view_layer.update()
    right=camera.matrix_world.to_quaternion()@Vector((1,0,0));up=camera.matrix_world.to_quaternion()@Vector((0,1,0))
    xx=[p.dot(right) for p in points];yy=[p.dot(up) for p in points]
    camera.data.ortho_scale=max((max(yy)-min(yy))*1.42,(max(xx)-min(xx))*1.42/(1280/960))
    scene.render.filepath=str(R/'Previews'/(name+'.png'))
    bpy.ops.render.render(write_still=True)
