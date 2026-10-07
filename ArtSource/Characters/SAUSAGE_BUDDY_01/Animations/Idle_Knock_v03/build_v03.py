"""Build driver for the Idle_Knock_v03 package (Blender 5.2, headless).

  blender -b --factory-startup --python build_v03.py -- --clip Idle_Stand --review 1 --out <dir>
      author in memory and render review frames (no source/export written)
  blender -b --factory-startup --python build_v03.py -- --clip Idle_Stand --final
      author and save <stem>.blend, <stem>.fbx, <stem>_authoring.json (never overwrites)

Every clip is sampled at half-frame steps (60 Hz) and keyed linearly, matching the GPT packages.
Loop clips key frame 1 and the duplicated last frame with exact canonical raw values.
"""
from pathlib import Path
import sys, json, math, argparse
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
from mathutils import Vector
import acting_core as C
import clips_standing as CS
try:
    import clips_cargo as CC
except ImportError:
    CC = None

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--clip', required=True)
ap.add_argument('--review', type=int, default=0)
ap.add_argument('--out', default='')
ap.add_argument('--every', type=int, default=2)
ap.add_argument('--views', default='side,three_quarter,front')
ap.add_argument('--res', type=int, default=320)
ap.add_argument('--times', default='')
ap.add_argument('--final', action='store_true')
ap.add_argument('--trace', default='')
ap.add_argument('--seq', action='store_true', help='name review frames s0000.png.. (ffmpeg-friendly)')
ap.add_argument('--dest', default='', help='write --final outputs here instead of this folder (dry runs)')
ap.add_argument('--from-saved', action='store_true', help='render the saved <stem>.blend instead of re-authoring')
ap.add_argument('--saved-dir', default='', help='folder of the saved <stem>.blend for --from-saved (default: this folder)')
args = ap.parse_args(argv)

REGISTRY = dict(CS.CLIPS)
if CC is not None:
    REGISTRY.update(CC.CLIPS)
STEMS = {'Idle_Stand': 'Idle_Stand_v03', 'Idle_Bored': 'Idle_Bored_v03',
         'Cargo_Sit_Idle': 'Cargo_Sit_Idle_v04', 'Cargo_Knock': 'Cargo_Knock_v03b',
         'SitUp_Cargo': 'SitUp_Cargo_v04'}


def author(B, name):
    spec = REGISTRY[name]
    T = spec['T']
    N = int(round(T * C.FPS))
    ctx = spec['setup'](B)
    frames, info = {}, []
    for i in range(2 * N + 1):
        t = i / (2 * C.FPS)
        pose, extra = spec['pose'](ctx, t)
        frames[1 + i / 2] = pose
        extra = dict(extra or {})
        extra['t'] = t
        info.append(extra)
    canonical = spec['canonical'](ctx, N)
    if 'post' in spec:                       # clip-level safety nets on the sampled poses
        spec['post'](ctx, frames, canonical)
    if args.trace:
        pts = ('HeadTop_End', 'Head', 'Neck', 'Spine2', 'Hips', 'LeftArm', 'RightArm', 'LeftHand', 'RightHand',
               'LeftLeg', 'RightLeg', 'LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase')
        tr = {'T': T, 'fps': C.FPS, 'points': {p: [list(frames[1 + i / 2][C.P + p].translation) for i in range(2 * N + 1)]
                                                  for p in pts}}
        Path(args.trace).write_text(json.dumps(tr), encoding='utf-8')
    act, mismatch = B.key_action(STEMS[name], frames, canonical)
    assert not mismatch, ('canonical end quaternion sign differs from the continuous chain', mismatch[:5])
    B.scene.frame_start, B.scene.frame_end = 1, N + 1
    B.scene.frame_set(1)
    act['duration_seconds'] = T
    act['fps'] = C.FPS
    act['loop'] = spec['loop']
    act['authoring'] = 'Original local FK/IK acting (Idle_Knock_v03 package); no external motion reused'
    return act, N, info, ctx


VIEWS_STAND = {
    'side': ((5.0, 0.0, 1.05), (0.0, 0.0, 0.92), 2.15),
    'three_quarter': ((3.4, -4.4, 1.85), (0.0, 0.0, 0.90), 2.15),
    'front': ((0.0, -5.0, 1.05), (0.0, 0.0, 0.92), 2.15),
}
VIEWS_CARGO = {
    'side': ((0.0, -5.0, 0.80), (-0.20, 0.0, 0.52), 1.85),
    'three_quarter': ((3.3, -3.6, 1.75), (-0.22, 0.0, 0.48), 1.85),
    'front': ((4.6, 0.0, 0.85), (-0.25, 0.0, 0.50), 1.85),
}


# the knock turns to his right (toward -Y): its three-quarter camera sits on the -Y side (HANDOFF 7)
VIEWS_KNOCK = dict(VIEWS_CARGO, three_quarter=((2.0, -4.0, 1.6), (-0.32, 0.0, 0.55), 1.85))


def review(B, name, N):
    spec = REGISTRY[name]
    cargo = spec.get('stage') == 'cargo'
    col, cam = C.studio(B.scene, wall=cargo)
    C.use_eevee(B.scene, (args.res, args.res), samples=12)
    views = (VIEWS_KNOCK if name == 'Cargo_Knock' else VIEWS_CARGO) if cargo else VIEWS_STAND
    out = Path(args.out)
    if args.times:
        frames = [1 + float(x) * C.FPS for x in args.times.split(',')]
    else:
        frames = [float(f) for f in range(1, N + 2, args.every)]
        if frames[-1] != N + 1:
            frames.append(float(N + 1))
    for v in args.views.split(','):
        loc, tgt, ortho = views[v]
        C.aim(cam, loc, tgt, ortho)
        for k, f in enumerate(frames):
            B.scene.frame_set(int(f), subframe=f % 1)
            p = out / v / (f's{k:04d}.png' if args.seq else f'f{f:07.2f}.png')
            p.parent.mkdir(parents=True, exist_ok=True)
            B.scene.render.filepath = str(p)
            bpy.ops.render.render(write_still=True)
    print('REVIEW_DONE', name, len(frames), flush=True)


def final(B, name, act, N, info, ctx):
    stem = STEMS[name]
    dest = Path(args.dest) if args.dest else HERE
    for ext in ('.blend', '.fbx'):
        assert not (dest / (stem + ext)).exists(), 'Refusing overwrite ' + stem + ext
    rep = dest / (stem + '_authoring.json')
    assert not rep.exists(), 'Refusing overwrite ' + rep.name
    assert len(B.rig.data.bones) == 65 and all(abs(s - 1) < 1e-9 for s in B.rig.scale)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(dest / (stem + '.blend')))
    B.export_fbx(act, dest / (stem + '.fbx'))
    spec = REGISTRY[name]
    rep.write_text(json.dumps({
        'clip': stem, 'action': act.name, 'frames': [1, N + 1], 'fps': C.FPS, 'duration_s': spec['T'],
        'loop': spec['loop'], 'sampling': 'half-frame keys (60 Hz), linear interpolation',
        'beats': spec.get('beats', []),
        'authoring_stats': spec['stats'](info) if 'stats' in spec else None,
    }, indent=2), encoding='utf-8')
    print('FINAL_SAVED', stem, flush=True)


class _Saved:
    """Minimal stand-in for Buddy when rendering a saved deliverable without re-authoring."""
    def __init__(self, stem):
        bpy.ops.wm.open_mainfile(filepath=str((Path(args.saved_dir) if args.saved_dir else HERE) / (stem + '.blend')))
        self.scene = bpy.context.scene
        act = bpy.data.objects[C.RIG_NAME].animation_data.action
        self.N = int(round(act.frame_range[1] - act.frame_range[0]))


if __name__ == '__main__' and args.from_saved:
    S = _Saved(STEMS[args.clip])
    review(S, args.clip, S.N)
elif __name__ == '__main__':
    B = C.Buddy()
    act, N, info, ctx = author(B, args.clip)
    if args.review:
        review(B, args.clip, N)
    if args.final:
        final(B, args.clip, act, N, info, ctx)
