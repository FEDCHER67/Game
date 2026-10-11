from pathlib import Path
import sys, subprocess, json
sys.dont_write_bytecode = True
import bpy
from mathutils import Vector
ROOT = Path(r'C:\Dev\Game\ArtSource\Characters\SAUSAGE_BUDDY_01\Animations\GetUp_Idle_v01')
sys.path.insert(0, str(ROOT.parent.parent))
import buddy_render as RD
clips = {'GetUp_FromBack':78, 'GetUp_FromBelly':75, 'Idle_Variant_A':120, 'Idle_Variant_B':120}
for name, period in clips.items():
    stem = name + '_v02'
    folder = ROOT / 'Previews' / stem / name
    movie = folder / (stem + '.mp4')
    assert not movie.exists(), 'Refusing overwrite: ' + str(movie)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / (stem + '.blend')))
    scene = bpy.context.scene
    col, cam, floor = RD.studio(scene)
    scene.render.engine = 'BLENDER_EEVEE'
    if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = 16
    scene.render.resolution_x = scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.fps = 30
    cam.location = (-3.7,-5,2.65)
    cam.rotation_euler = (Vector((0,0,.85)) - cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = 2.55
    frames = folder / 'motion_frames'
    frames.mkdir(parents=True, exist_ok=True)
    for i in range(period):
        path = frames / ('f%04d.png' % i)
        assert not path.exists(), 'Refusing overwrite: ' + str(path)
        scene.frame_set(1+i)
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        print('MOVIE_FRAME', stem, i, flush=True)
    cmd = ['ffmpeg','-v','error','-n']
    if name.startswith('Idle_'): cmd += ['-stream_loop','1']
    cmd += ['-framerate','30','-start_number','0','-i',str(frames / 'f%04d.png'),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(movie)]
    subprocess.run(cmd, check=True)
    print('MOVIE_COMPLETE', str(movie), flush=True)
