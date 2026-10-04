"""Close-up face comparison of two Sausage Buddy revisions (review only, nothing exported).
Each expression shape key at full strength, rest pose, same studio and cameras for both files; ImageMagick tiles the
renders into one sheet: rows = expressions, columns = old front | new front | old 3/4 | new 3/4.

  blender -b --factory-startup --python ArtSource/Characters/SAUSAGE_BUDDY_01/buddy_face_compare.py -- \
      --old SAUSAGE_BUDDY_A_v04.blend --new SAUSAGE_BUDDY_A_v05.blend --out Previews/A_v05/06_face_v04_vs_v05.png
Paths are relative to this folder. Refuses to overwrite --out.
"""
import argparse, shutil, subprocess, sys, tempfile
from pathlib import Path
import bpy

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
import buddy_render as RD      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--old', required=True)
ap.add_argument('--new', required=True)
ap.add_argument('--out', required=True)
args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
OUT = HERE / args.out
if OUT.exists():
    sys.exit(f'Refusing to overwrite {OUT.name}')
EXPRESSIONS = ('Basis', 'Blink', 'Surprised', 'Worried', 'Happy')
VIEWS = (('front', (0, -1.25, 1.50), (0, 0, 1.50)), ('34', (-0.75, -1.05, 1.56), (0, 0, 1.50)))
tmp = Path(tempfile.mkdtemp(prefix='buddy_face_'))


def render_file(blend, tag):
    bpy.ops.wm.open_mainfile(filepath=str(HERE / blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['Buddy_Rig_Mixamo65']
    rig.data.pose_position = 'REST'
    key = bpy.data.objects['Face'].data.shape_keys
    if key.animation_data:
        key.animation_data.action = None
    tris = sum(len(p.vertices) - 2 for o in bpy.data.objects if o.type == 'MESH' and o.name in ('Body', 'Outfit', 'Face')
               for p in o.data.polygons)
    col, cam, floor = RD.studio(scene)
    for expr in EXPRESSIONS:
        for kb in key.key_blocks[1:]:
            kb.value = 1.0 if kb.name == expr else 0.0
        for view, loc, tgt in VIEWS:
            RD.shot(scene, cam, tmp / f'{tag}_{expr}_{view}.png', loc, tgt, lens=55, res=(600, 700))
    return tris


labels = {}
for tag, blend in (('old', args.old), ('new', args.new)):
    labels[tag] = f'{Path(blend).stem.split("_")[-1]}  {render_file(blend, tag)} tris'

tool = ['magick'] if shutil.which('magick') else ['convert']
rows = []
for expr in EXPRESSIONS:
    cells = []
    for view, _, _ in VIEWS:
        for tag in ('old', 'new'):
            cell = tmp / f'{tag}_{expr}_{view}_l.png'
            subprocess.run(tool + [str(tmp / f'{tag}_{expr}_{view}.png'), '-resize', 'x420', '-gravity', 'north', '-pointsize', '22',
                                   '-fill', 'black', '-annotate', '+0+8', f'{labels[tag]} - {expr}', str(cell)], check=True)
            cells.append(str(cell))
    row = tmp / f'row_{expr}.png'
    subprocess.run(tool + cells + ['+append', str(row)], check=True)
    rows.append(str(row))
OUT.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(tool + rows + ['-append', str(OUT)], check=True)
shutil.rmtree(tmp)
print('[BUDDY] face comparison', OUT)
