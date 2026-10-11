from pathlib import Path
import bpy,sys
from mathutils import Vector
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE.parent.parent))
import buddy_render as RD
bpy.ops.wm.open_mainfile(filepath=str(HERE/'Walk_v01.blend'))
scene=bpy.context.scene
_,cam,_=RD.studio(scene)
scene.cycles.samples=12
scene.render.resolution_x=512
scene.render.resolution_y=576
scene.render.resolution_percentage=100
cam.data.type='ORTHO'; cam.data.ortho_scale=1.95
for view,loc in [('side',(5,0,1.0)),('three_quarter',(-2.8,-4.5,1.65))]:
    out=HERE/'Previews'/view; out.mkdir(exist_ok=True)
    cam.location=loc
    cam.rotation_euler=(Vector((0,0,.87))-cam.location).to_track_quat('-Z','Y').to_euler()
    for frame in range(1,21):
        scene.frame_set(frame)
        scene.render.filepath=str(out/f'f{frame:03}.png')
        bpy.ops.render.render(write_still=True)
print('LOOP_RENDERS_READY',flush=True)
