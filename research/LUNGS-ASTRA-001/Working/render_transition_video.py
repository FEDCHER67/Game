"""Render frames for the Blender-only GOOD-to-BAD demonstration."""
import bpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LUNGS-ASTRA-001.blend'))
scene=bpy.context.scene
rig=bpy.data.objects['Lungs_Breath_Rig']
rig.animation_data.action=bpy.data.actions['Preview_GOOD_to_BAD_Transition']
scene.render.engine='CYCLES'
scene.cycles.samples=8
scene.cycles.use_denoising=True
scene.render.resolution_x=480
scene.render.resolution_y=480
scene.render.resolution_percentage=100
scene.render.fps=15
scene.render.fps_base=1.0
scene.frame_start=1
scene.frame_end=150
scene.frame_step=2
scene.render.image_settings.file_format='PNG'
frames=ROOT/'Working'/'TransitionFrames'
frames.mkdir(exist_ok=True)
scene.render.filepath=str(frames/'frame_')
scene.render.use_file_extension=True
bpy.ops.render.render(animation=True)
print('RENDERED_FRAMES',frames)
