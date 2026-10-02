"""Render the saved fitted rig; frames can be assembled into a GIF/video."""
import argparse,sys
from pathlib import Path
import bpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--revision',type=int,default=4)
p.add_argument('--frames-dir',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
bpy.ops.wm.open_mainfile(filepath=str(HERE/f'NPC_BASE_01_v{a.revision:02d}.blend'))
scene=bpy.context.scene
a.frames_dir.mkdir(parents=True,exist_ok=True)
scene.render.resolution_x=480;scene.render.resolution_y=544
scene.cycles.samples=12
for frame in range(scene.frame_start,scene.frame_end+1):
    scene.frame_set(frame)
    scene.render.filepath=str(a.frames_dir/f'{frame:04d}.png')
    bpy.ops.render.render(write_still=True)
# Rest pose with actual bones for inspection; only this read-only render changes pose_position.
rig=bpy.data.objects['NPC_Rig_Mixamo65'];rig.data.pose_position='REST'
scene.camera.location=(0,-6,.95)
scene.camera.rotation_euler=(Vector((0,0,.9))-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera.data.ortho_scale=2.12
scene.render.resolution_x=900;scene.render.resolution_y=1000
scene.cycles.samples=24
scene.render.filepath=str(HERE/'Previews'/f'v{a.revision:02d}'/'Rest_TPose.png')
bpy.ops.render.render(write_still=True)
