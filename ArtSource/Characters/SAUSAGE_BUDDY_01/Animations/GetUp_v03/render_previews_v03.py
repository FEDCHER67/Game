"""Previews for the Sausage Buddy get-ups v03: MP4 (side + three-quarter), contact sheets, onion-skin strips.

  blender -b --factory-startup --python render_previews_v03.py -- --clip all --out Previews --engine eevee
  (cloud / no GPU: --engine workbench renders ~0.1 s per frame on software GL; EEVEE needs ~6 s)

By default the clip is rebuilt in-process with build_getups_v03.build() (deterministic, identical to the
.blend), so previews can be made without the binary deliverables (no Git LFS). --from-blend opens the saved
GetUp_*_v03.blend instead. Renders go to <out>/<clip>_v03/; never overwrites an existing file.
Also used by build_getups_v03.py --review (contact sheets only).
"""
from pathlib import Path
import sys, math, argparse, subprocess, shutil
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent))
import bpy
from mathutils import Vector

# camera: (location, target). Side looks from the character's left (+X); the body lies along Y.
VIEWS = {'side': ((6.0, -0.12, 1.55), (0.0, -0.12, 0.72)),
         'three_quarter': ((-3.9, -5.2, 2.75), (0.0, -0.10, 0.70))}
ORTHO = 2.45


def _mat(name, rgba):
    m = bpy.data.materials.new(name)
    m.diffuse_color = rgba
    try:
        m.use_nodes = True
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = rgba
        b.inputs['Roughness'].default_value = 0.9
    except Exception:
        pass
    return m


def _floor(scene, tile=0.25, half=12):
    """Checker floor (0.25 m tiles) so sliding contacts are visible in the previews."""
    col = bpy.data.collections.new('Preview_NOT_EXPORTED')
    scene.collection.children.link(col)
    verts, faces, mi = [], [], []
    for i in range(-half, half):
        for j in range(-half, half):
            k = len(verts)
            x0, y0 = i * tile, j * tile
            verts += [(x0, y0, 0), (x0 + tile, y0, 0), (x0 + tile, y0 + tile, 0), (x0, y0 + tile, 0)]
            faces.append((k, k + 1, k + 2, k + 3))
            mi.append((i + j) % 2)
    me = bpy.data.meshes.new('Preview_Floor')
    me.from_pydata(verts, [], faces)
    me.materials.append(_mat('Preview_FloorA', (0.62, 0.63, 0.66, 1)))
    me.materials.append(_mat('Preview_FloorB', (0.52, 0.53, 0.56, 1)))
    me.polygons.foreach_set('material_index', mi)
    me.update()
    fl = bpy.data.objects.new('Preview_Floor', me)
    col.objects.link(fl)
    return col


def setup(scene, engine='workbench', res=320):
    col = _floor(scene)
    cd = bpy.data.cameras.new('Preview_Cam')
    cam = bpy.data.objects.new('Preview_Cam', cd)
    col.objects.link(cam)
    scene.camera = cam
    cd.type = 'ORTHO'
    cd.ortho_scale = ORTHO
    if engine == 'eevee':
        import buddy_render as RD  # read-only studio lights (also sets a world)
        RD.studio(scene)
        scene.camera = cam
        for o in list(bpy.data.objects):
            if o.name.startswith('Studio_Floor'):
                o.hide_render = True
        try:
            scene.render.engine = 'BLENDER_EEVEE'
        except TypeError:
            scene.render.engine = 'BLENDER_EEVEE_NEXT'
        if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
            scene.eevee.taa_render_samples = 16
    else:
        scene.render.engine = 'BLENDER_WORKBENCH'
        world = bpy.data.worlds.new('Preview_World')
        world.color = (0.78, 0.79, 0.82)
        scene.world = world
        sh0 = scene.display.shading
        sh0.background_type = 'WORLD'
        sh = scene.display.shading
        sh.light = 'STUDIO'
        sh.color_type = 'MATERIAL'
        sh.show_shadows = True
        sh.shadow_intensity = 0.55
        sh.show_cavity = True
        scene.display.light_direction = (0.45, -0.35, 0.82)
        scene.view_settings.view_transform = 'Standard'
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.fps = 30
    return cam


def aim(scene, view):
    cam = scene.camera
    loc, tgt = VIEWS[view]
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def render(scene, frame, path):
    path = Path(path)
    assert not path.exists(), 'Refusing overwrite ' + str(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    scene.frame_set(int(math.floor(frame)), subframe=frame - math.floor(frame))
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def contact_sheets(scene, out, name, frames, views=('side', 'three_quarter'), cols=12):
    """One labelled sheet per view (every listed frame) + one onion-skin overlay per view."""
    from PIL import Image, ImageDraw, ImageChops
    out = Path(out)
    sheets = []
    for view in views:
        aim(scene, view)
        paths = [render(scene, f, out / view / ('f%06.2f.png' % f)) for f in frames]
        ims = [Image.open(p).convert('RGB') for p in paths]
        w, h = ims[0].size
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * w, rows * h), (255, 255, 255))
        for i, (im, f) in enumerate(zip(ims, frames)):
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 58, 16), fill=(255, 255, 255))
            d.text((3, 2), 'f%g' % (f - 1), fill=(0, 0, 0))
            sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        sp = out / ('%s_%s_sheet.png' % (name, view))
        assert not sp.exists(), 'Refusing overwrite ' + str(sp)
        sheet.save(sp)
        onion = ims[0]
        for im in ims[1::2]:
            onion = ImageChops.darker(onion, im)
        op = out / ('%s_%s_onion.png' % (name, view))
        assert not op.exists(), 'Refusing overwrite ' + str(op)
        onion.save(op)
        sheets += [sp, op]
    return sheets


def movie(scene, out, stem, n_frames, view):
    folder = Path(out) / ('frames_' + view)
    for i in range(n_frames + 1):
        render(scene, 1 + i, folder / ('f%04d.png' % i))
    mp4 = Path(out) / ('%s_%s.mp4' % (stem, view))
    assert not mp4.exists(), 'Refusing overwrite ' + str(mp4)
    ff = shutil.which('ffmpeg')
    assert ff, 'ffmpeg not found on PATH'
    subprocess.run([ff, '-v', 'error', '-n', '-framerate', '30', '-start_number', '0', '-i', str(folder / 'f%04d.png'),
                    '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(mp4)],
                   check=True)
    return mp4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--clip', default='all', choices=('all', 'back', 'belly'))
    ap.add_argument('--out', default=str(HERE / 'Previews'))
    ap.add_argument('--engine', default='eevee', choices=('workbench', 'eevee'))
    ap.add_argument('--res', type=int, default=480)
    ap.add_argument('--sheet-every', type=int, default=3)
    ap.add_argument('--revision', type=int, default=3)
    ap.add_argument('--from-blend', action='store_true')
    ap.add_argument('--no-movie', action='store_true')
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    import build_getups_v03 as B
    B.VERSION = 'v%02d' % args.revision
    for key, (name, _) in B.CLIPS.items():
        if args.clip not in ('all', key):
            continue
        stem = name + '_' + B.VERSION
        if args.from_blend:
            bpy.ops.wm.open_mainfile(filepath=str(HERE / (stem + '.blend')))
            scene = bpy.context.scene
            n = scene.frame_end - scene.frame_start
        else:
            rig, clip, act, m = B.build(key)
            scene, n = rig.scene, clip.N
        out = Path(args.out) / stem
        setup(scene, args.engine, args.res)
        frames = [1 + f for f in range(0, n + 1, args.sheet_every)]
        if frames[-1] != 1 + n:
            frames.append(1 + n)
        for p in contact_sheets(scene, out / 'sheets', stem, frames):
            print('SHEET', p, flush=True)
        if not args.no_movie:
            for view in VIEWS:
                aim(scene, view)
                print('MOVIE', movie(scene, out, stem, n, view), flush=True)


if __name__ == '__main__':
    main()
