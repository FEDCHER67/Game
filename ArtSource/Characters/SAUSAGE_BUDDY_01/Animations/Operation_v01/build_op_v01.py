"""Build driver for the Operation_v01 package (Blender 5.2, headless).

  blender -b --factory-startup --python build_op_v01.py -- --clip Awake --review 1 --out <dir> [--every 2 | --times a,b]
      author in memory and render review frames (nothing saved)
  blender -b --factory-startup --python build_op_v01.py -- --clip Awake --final
      author and save Op_<Clip>_v01.blend / .fbx / _authoring.json in this folder (never overwrites)
  blender -b --factory-startup --python build_op_v01.py -- --clip Awake --from-saved --out <dir> --seq
      render the SAVED .blend (no re-authoring) for the final previews

Half-frame keys (60 Hz), linear; loops key frame 1 and the duplicated last frame with identical raw values.
"""
from pathlib import Path
import sys, json, math, argparse, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
from mathutils import Vector, Matrix
import op_core as O
import op_clips as OC
import acting_core as AC

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--clip', required=True)
ap.add_argument('--review', type=int, default=0)
ap.add_argument('--out', default='')
ap.add_argument('--every', type=int, default=2)
ap.add_argument('--views', default='side,three_quarter')
ap.add_argument('--res', type=int, default=420)
ap.add_argument('--times', default='')
ap.add_argument('--final', action='store_true')
ap.add_argument('--seq', action='store_true')
ap.add_argument('--trace', default='')
ap.add_argument('--from-saved', action='store_true')
ap.add_argument('--dest', default='')
ap.add_argument('--samples', type=int, default=16)
args = ap.parse_args(argv)

REG = OC.CLIPS


def author(B, name):
    spec = REG[name]
    T = spec['T']
    N = int(round(T * O.FPS))
    t0 = time.time()
    ctx = spec['setup'](B)
    frames, info = {}, []
    for i in range(2 * N + 1):
        t = i / (2 * O.FPS)
        pose, extra = spec['pose'](ctx, t)
        frames[1 + i / 2] = pose
        extra = dict(extra or {})
        extra['t'] = t
        info.append(extra)
    canonical = spec['canonical'](ctx, N, frames)
    if 'post' in spec:
        spec['post'](ctx, frames, canonical)
    if args.trace:
        pts = ('HeadTop_End', 'Head', 'Neck', 'Spine2', 'Hips', 'LeftHand', 'RightHand', 'LeftForeArm', 'RightForeArm',
               'LeftLeg', 'RightLeg', 'LeftFoot', 'RightFoot')
        tr = {'T': T, 'fps': O.FPS, 'points': {p: [list(frames[1 + i / 2][O.P + p].translation) for i in range(2 * N + 1)]
                                                  for p in pts}}
        Path(args.trace).write_text(json.dumps(tr), encoding='utf-8')
    act, mismatch = B.key_action(spec['stem'], frames, canonical)
    assert not mismatch, ('canonical end quaternion sign differs from the continuous chain', mismatch[:5])
    B.scene.frame_start, B.scene.frame_end = 1, N + 1
    B.scene.frame_set(1)
    act['duration_seconds'] = T
    act['fps'] = O.FPS
    act['loop'] = spec['loop']
    act['authoring'] = 'Original local FK/IK acting (Operation_v01 package); no external motion reused'
    print('AUTHORED', name, N, 'frames in %.1f s' % (time.time() - t0), 'fixes', getattr(ctx, 'solve_stats', None), flush=True)
    return act, N, info, ctx


# ----------------------------------------------------------------------------------- review render
def studio(scene):
    col = bpy.data.collections.get('Studio_NOT_EXPORTED') or bpy.data.collections.new('Studio_NOT_EXPORTED')
    if col.name not in scene.collection.children:
        scene.collection.children.link(col)
    world = bpy.data.worlds.new('Studio')
    scene.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = AC.srgb((150, 158, 166))
    bg.inputs[1].default_value = 0.8

    def light(name, loc, power, size, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA'); d.energy = power; d.shape = 'DISK'; d.size = size; d.color = color
        o = bpy.data.objects.new(name, d); o.location = loc
        o.rotation_euler = (Vector((0, 0, 0.7)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        col.objects.link(o)
    light('Key', (2.2, 1.4, 3.4), 600, 3.0, (1.0, 0.97, 0.93))
    light('Fill', (-2.6, -1.6, 2.6), 380, 3.5, (0.93, 0.96, 1.0))
    light('Rim', (-0.6, -3.2, 2.6), 300, 2.5)
    me = bpy.data.meshes.new('Studio_Floor')
    me.from_pydata([(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [], [(0, 1, 2, 3)])
    m = bpy.data.materials.new('Studio_Floor')
    try:
        m.use_nodes = True
    except Exception:
        pass
    bs = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bs.inputs['Base Color'].default_value = AC.srgb((120, 126, 132))
    bs.inputs['Roughness'].default_value = 0.9
    me.materials.append(m)
    col.objects.link(bpy.data.objects.new('Studio_Floor', me))
    cd = bpy.data.cameras.new('Review_Cam')
    cam = bpy.data.objects.new('Review_Cam', cd)
    col.objects.link(cam)
    scene.camera = cam
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.exposure = -0.6
    return cam


# views in TABLE space: (location, target, ortho scale or None for perspective, lens)
VIEWS = {
    'side': ((3.2, -0.02, 0.95), (0.0, -0.02, 0.80), 2.05, None),
    'three_quarter': ((1.30, 1.50, 1.50), (0.0, -0.18, 0.74), None, 30),
    'tablecam': ((1.6, -0.02, 1.70), (0.05, -0.10, 0.78), None, 24),
    'left': ((-1.0, 3.8, 0.85), (-0.95, -0.05, 0.50), 3.3, None),
    'left_three_quarter': ((-3.3, 2.3, 2.3), (-1.0, -0.15, 0.35), None, 30),
    'floor_top': ((-1.0, -0.2, 4.0), (-1.0, -0.15, 0.0), 2.6, None),
}
CLIP_VIEWS = {'EscapeFall': ('left', 'left_three_quarter'), 'KnockedOut': ('left', 'left_three_quarter')}


def aim(cam, view):
    loc, tgt, ortho, lens = VIEWS[view]
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if ortho:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = 'PERSP'
        cam.data.lens = lens
        cam.data.sensor_width = 36


def review(scene, name, N, views):
    cam = studio(scene)
    AC.use_eevee(scene, (args.res, args.res), samples=args.samples)
    out = Path(args.out).resolve()
    if args.times:
        frames = [1 + float(x) * O.FPS for x in args.times.split(',')]
    else:
        frames = [float(f) for f in range(1, N + 2, args.every)]
        if frames[-1] != N + 1:
            frames.append(float(N + 1))
    for v in views:
        aim(cam, v)
        for k, f in enumerate(frames):
            scene.frame_set(int(f), subframe=f % 1)
            p = out / v / (f's{k:04d}.png' if args.seq else f'f{f:07.2f}.png')
            p.parent.mkdir(parents=True, exist_ok=True)
            scene.render.filepath = str(p)
            bpy.ops.render.render(write_still=True)
    print('REVIEW_DONE', name, len(frames), flush=True)


def final(B, name, act, N, info, ctx):
    spec = REG[name]
    stem = spec['stem']
    dest = Path(args.dest) if args.dest else HERE
    for ext in ('.blend', '.fbx', '_authoring.json'):
        assert not (dest / (stem + ext)).exists(), 'Refusing overwrite ' + stem + ext
    assert len(B.rig.data.bones) == 65 and all(abs(s - 1) < 1e-9 for s in B.rig.scale)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(dest / (stem + '.blend')))
    B.export_fbx(act, dest / (stem + '.fbx'))
    bpy.ops.wm.save_as_mainfile(filepath=str(dest / (stem + '.blend')))
    rep = {
        'clip': stem, 'action': act.name, 'take': 'Buddy_Rig_Mixamo65|' + act.name, 'frames': [1, N + 1], 'fps': O.FPS,
        'duration_s': spec['T'], 'loop': spec['loop'], 'sampling': 'half-frame keys (60 Hz), linear interpolation',
        'rig_object_in_blend': [list(r) for r in B.rig.matrix_world],
        'beats': spec.get('beats', []),
        'contact_solve_max': getattr(ctx, 'solve_stats', None),
        'authoring_stats': spec['stats'](ctx, info) if 'stats' in spec else None,
    }
    (dest / (stem + '_authoring.json')).write_text(json.dumps(rep, indent=2), encoding='utf-8')
    print('FINAL_SAVED', stem, flush=True)


if __name__ == '__main__':
    spec = REG[args.clip]
    views = args.views.split(',') if args.views != 'auto' else CLIP_VIEWS.get(args.clip, ('side', 'three_quarter'))
    if args.from_saved:
        bpy.ops.wm.open_mainfile(filepath=str(HERE / (spec['stem'] + '.blend')))
        act = bpy.data.objects[O.RIG_NAME].animation_data.action
        N = int(round(act.frame_range[1] - act.frame_range[0]))
        review(bpy.context.scene, args.clip, N, views)
    else:
        B = O.Patient()
        act, N, info, ctx = author(B, args.clip)
        if args.review:
            review(B.scene, args.clip, N, views)
        if args.final:
            final(B, args.clip, act, N, info, ctx)
