"""Render review frames of a walk blend (side, three-quarter, front) on a moving treadmill floor.

Blender 5.2 background:
  blender -b --factory-startup --python render_walk_v03.py -- [--blend Walk_v03.blend]
      [--out Previews/frames_v03] [--views side,threequarter,front] [--frames 1-20]
      [--samples 24] [--res 640 720]

The floor checker (0.25 m squares) moves toward +Y at the clip's nominal ground speed, so a
planted shoe must travel exactly with the checker; any slide is visible. Same studio as the
character's reference renders (buddy_render.studio). Nothing is saved back to the blend.
"""
from pathlib import Path
import sys
import argparse
sys.dont_write_bytecode = True
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
CHAR = HERE.parent.parent
sys.path.insert(0, str(CHAR))
import buddy_render as RD       # noqa: E402
import buddy_geo as G           # noqa: E402
import buddy_rig as RG          # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--blend', default=str(HERE / 'Walk_v03.blend'))
ap.add_argument('--out', default=str(HERE / 'Previews' / 'frames_v03'))
ap.add_argument('--views', default='side,threequarter')
ap.add_argument('--frames', default='')
ap.add_argument('--samples', type=int, default=24)
ap.add_argument('--res', type=int, nargs=2, default=(640, 720))
ap.add_argument('--speed', type=float, default=1.5)
args = ap.parse_args(argv)

VIEWS = {
    'side': dict(loc=(5.0, 0.0, 1.62), target=(0.0, 0.0, 0.84), ortho=2.15),
    'threequarter': dict(loc=(-2.8, -4.5, 1.65), target=(0.0, 0.0, 0.87), ortho=2.0),
    'front': dict(loc=(0.0, -5.0, 1.25), target=(0.0, 0.0, 0.86), ortho=2.0),
}

bpy.ops.wm.open_mainfile(filepath=args.blend)
scene = bpy.context.scene
rig = bpy.data.objects['Buddy_Rig_Mixamo65']
act = rig.animation_data.action
start = int(round(act.frame_range[0]))
end = int(round(act.frame_range[1]))           # duplicate seam frame; not rendered
cycle = end - start
fps = scene.render.fps
if args.frames:
    picked = []
    for part in args.frames.split(','):
        a, _, b = part.partition('-')
        picked += list(range(int(a), int(b or a) + 1))
else:
    picked = list(range(start, end))

_, cam, floor = RD.studio(scene)
scene.render.engine = 'CYCLES'
scene.cycles.samples = args.samples
scene.render.image_settings.file_format = 'PNG'
scene.render.resolution_x, scene.render.resolution_y = args.res
scene.render.resolution_percentage = 100

# Treadmill checker: shift = speed * time; one cycle moves an integer number of 0.5 m periods.
mat = floor.active_material
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
coord = nt.nodes.new('ShaderNodeTexCoord')
mapping = nt.nodes.new('ShaderNodeMapping')
checker = nt.nodes.new('ShaderNodeTexChecker')
checker.inputs['Scale'].default_value = 4.0                    # 0.25 m squares
checker.inputs['Color1'].default_value = G.srgb((198, 200, 206))
checker.inputs['Color2'].default_value = G.srgb((176, 179, 186))
nt.links.new(coord.outputs['Object'], mapping.inputs['Vector'])
nt.links.new(mapping.outputs['Vector'], checker.inputs['Vector'])
nt.links.new(checker.outputs['Color'], bsdf.inputs['Base Color'])
loc = mapping.inputs['Location']
for f in (start, end):
    loc.default_value[1] = -args.speed * (f - start) / fps      # pattern moves toward +Y
    loc.keyframe_insert('default_value', index=1, frame=f)
for fc in RG.fcurves_of(nt.animation_data.action):
    for k in fc.keyframe_points:
        k.interpolation = 'LINEAR'

out = Path(args.out)
for view in args.views.split(','):
    v = VIEWS[view]
    cam.location = v['loc']
    cam.rotation_euler = (Vector(v['target']) - Vector(v['loc'])).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = v['ortho']
    (out / view).mkdir(parents=True, exist_ok=True)
    for f in picked:
        scene.frame_set(f)
        scene.render.filepath = str(out / view / f'f{f:03}.png')
        bpy.ops.render.render(write_still=True)
print('RENDERS_READY', out, 'frames', picked[0], '..', picked[-1], 'cycle', cycle, flush=True)
