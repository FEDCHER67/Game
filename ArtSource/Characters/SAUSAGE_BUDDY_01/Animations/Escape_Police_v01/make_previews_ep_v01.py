"""Preview MP4s + contact sheets from the SAVED Escape_Police_v01 .blend files (no re-authoring).

  python make_previews_ep_v01.py --dir <folder with <Clip>_v01.blend> --out <preview folder> [--clips a,b|all]
         [--res 420] [--engine WORKBENCH|EEVEE] [--loops 3]

Per clip: side + three-quarter PNG sequences (the review stage of build_ep_v01: moving striped floor
for in-place locomotion, the van floor slab for JumpOut), <Clip>_v01_<view>.mp4 (loops play
--loops times; ffmpeg must be on PATH) and <Clip>_v01_contact_sheet.png (10 labelled times, both
views). Needs Pillow. Refuses to overwrite existing MP4s / sheets.
"""
from pathlib import Path
import sys, argparse, subprocess, shutil
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ep_core as E
import bpy
import acting_core as C
import build_ep_v01 as BD
from PIL import Image, ImageDraw


def render_clip(name, blend, out, res, engine):
    spec = BD.REGISTRY[name]
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects[C.RIG_NAME]
    f0, f1 = (int(round(x)) for x in rig.animation_data.action.frame_range)
    col, cam = C.studio(scene)
    floor_obj = bpy.data.objects.get('Studio_Floor')
    stage = spec.get('stage_objects')
    movers = stage(col) if stage else []
    if spec.get('ground') and not stage:
        movers = [(E.treadmill(scene, col), 0.5)]
        floor_obj.hide_render = True
    if spec.get('floor_offset') is not None:
        floor_obj.location.z = spec['floor_offset']
    E.setup_engine(scene, res, engine)
    if engine == 'WORKBENCH':
        scene.world.color = (0.62, 0.64, 0.68)
    views = spec.get('views', BD.VIEWS_STAND)
    g = spec.get('ground')
    loop = spec['loop']
    last = f1 - 1 if loop else f1          # loops: drop the duplicated seam frame for the MP4
    paths = {}
    for v in ('side', 'three_quarter'):
        loc, tgt, ortho = views[v]
        C.aim(cam, loc, tgt, ortho)
        d = out / '_frames' / name / v
        d.mkdir(parents=True, exist_ok=True)
        for k, f in enumerate(range(f0, last + 1)):
            scene.frame_set(f)
            t = (f - f0) / C.FPS
            for o, period in movers:
                G = g(t) if g else 0.0
                o.location.y = (G % period) if period else G
            scene.render.filepath = str(d / ('s%04d.png' % k))
            bpy.ops.render.render(write_still=True)
        paths[v] = d
    return paths, f0, f1, last


def encode(frames_dir, mp4, loops):
    assert not mp4.exists(), 'Refusing overwrite ' + str(mp4)
    cmd = ['ffmpeg', '-loglevel', 'error', '-n']
    if loops > 1:
        cmd += ['-stream_loop', str(loops - 1)]
    cmd += ['-framerate', '30', '-i', str(frames_dir / 's%04d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-crf', '18', '-movflags', '+faststart', str(mp4)]
    subprocess.run(cmd, check=True)


def contact(paths, f0, last, out_png, title):
    assert not out_png.exists(), 'Refusing overwrite ' + str(out_png)
    n = last - f0 + 1
    idx = [round(i * (n - 1) / 9) for i in range(10)]
    s = 300
    sheet = Image.new('RGB', (5 * s, 40 + 4 * (s + 20)), (35, 39, 46))
    d = ImageDraw.Draw(sheet)
    d.text((10, 10), title + ' | 30 fps | side (rows 1-2), three-quarter (rows 3-4)', fill='white')
    for vi, v in enumerate(('side', 'three_quarter')):
        for i, k in enumerate(idx):
            x, y = (i % 5) * s, 40 + (vi * 2 + i // 5) * (s + 20)
            sheet.paste(Image.open(paths[v] / ('s%04d.png' % k)).convert('RGB').resize((s, s)), (x, y))
            d.text((x + 6, y + s + 3), '%.2f s (frame %d)' % (k / C.FPS, f0 + k), fill='white')
    sheet.save(out_png)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--clips', default='all')
    ap.add_argument('--res', type=int, default=420)
    ap.add_argument('--engine', default='WORKBENCH')
    ap.add_argument('--loops', type=int, default=3)
    ap.add_argument('--keep-frames', action='store_true')
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    names = list(BD.REGISTRY) if a.clips == 'all' else a.clips.split(',')
    for name in names:
        stem = '%s_%s' % (name, BD.REV)
        paths, f0, f1, last = render_clip(name, Path(a.dir) / (stem + '.blend'), out, a.res, a.engine)
        loops = a.loops if BD.REGISTRY[name]['loop'] else 1
        for v, d in paths.items():
            encode(d, out / ('%s_%s.mp4' % (stem, v)), loops)
        contact(paths, f0, last, out / (stem + '_contact_sheet.png'), stem)
        print('PREVIEW', stem, flush=True)
    if not a.keep_frames:
        shutil.rmtree(out / '_frames', ignore_errors=True)


if __name__ == '__main__':
    main()
