"""Build driver for the Escape_Police_v01 package (Blender 5.2 or `pip install bpy`, headless).

Run from the repository root (PKG = ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Escape_Police_v01):

  python $PKG/build_ep_v01.py --clip Cop_Run --metrics
      author in memory, print contact / floor / reach metrics (fast; nothing written)
  python $PKG/build_ep_v01.py --clip Cop_Run --review <dir> [--every 2] [--views side,three_quarter] [--res 300]
      author in memory and render review frames (Workbench) + one labelled grid per view
  python $PKG/build_ep_v01.py --clip Cop_Run --trace <file.json>
      joint traces (plot with Idle_Knock_v03/plot_trace.py)
  python $PKG/build_ep_v01.py --clip all --final --dest <dir>
      author and save <stem>.blend, <stem>.fbx, <stem>_authoring.json into <dir> (never overwrites)
  (with Blender instead of the bpy module: blender -b --factory-startup --python build_ep_v01.py -- <args>)

Every clip is sampled at half-frame steps (60 Hz) and keyed linearly, like the rest of the Buddy
pipeline. Loops key frame 1 and the duplicated last frame with identical canonical raw values;
clips that start or end on a contract pose (Idle frame 1, another clip's frame) key those exactly.
"""
from pathlib import Path
import sys, json, math, argparse, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ep_core as E            # sets up the Idle_Knock_v03 path for acting_core
import bpy
import numpy as np
from mathutils import Vector
import acting_core as C
import clips_police as CP
import clips_escape as CE

REGISTRY = {}
REGISTRY.update(CE.CLIPS)
REGISTRY.update(CP.CLIPS)
REV = 'v01'


def stem(name):
    return '%s_%s' % (name, REV)


def parse():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--clip', required=True, help="clip name, comma list, or 'all'")
    ap.add_argument('--review', default='')
    ap.add_argument('--every', type=int, default=2)
    ap.add_argument('--times', default='')
    ap.add_argument('--views', default='side,three_quarter')
    ap.add_argument('--res', type=int, default=300)
    ap.add_argument('--engine', default='WORKBENCH')
    ap.add_argument('--seq', action='store_true', help='frame names s0000.png.. for ffmpeg')
    ap.add_argument('--cols', type=int, default=10)
    ap.add_argument('--metrics', action='store_true')
    ap.add_argument('--trace', default='')
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--dest', default='')
    return ap.parse_args(argv)


def author(B, name, ctx_cache):
    spec = REGISTRY[name]
    T = spec['T']
    N = int(round(T * C.FPS))
    assert abs(T * C.FPS - N) < 1e-9, '%s: length %.4f s is not a whole number of frames' % (name, T)
    ctx = spec['setup'](B, ctx_cache)
    frames, info = {}, []
    for i in range(2 * N + 1):
        t = i / (2 * C.FPS)
        pose, extra = spec['pose'](ctx, t)
        frames[1 + i / 2] = pose
        extra = dict(extra or {})
        extra['t'] = t
        info.append(extra)
    canonical = spec['canonical'](ctx, frames, N) if spec.get('canonical') else {}
    return frames, info, canonical, N, ctx


def key(B, name, frames, canonical, N):
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    spec = REGISTRY[name]
    act, mismatch = B.key_action(stem(name), frames, canonical)
    flipped = []
    if mismatch:
        # q and -q are the same rotation. For a one-shot the continuous key chain may legitimately
        # arrive at the end contract with the opposite sign (e.g. a foot unrolling ~170 deg); key the
        # end contract with the matching sign (the pose stays exact). For a loop it would mean a net
        # 360 deg turn across the seam, which is a real defect: refuse.
        assert not spec['loop'], ('loop seam: quaternion sign flip (net 360 deg turn)', mismatch[:5])
        for f, n in mismatch:
            v = dict(canonical[f][n])
            v['q'] = tuple(-x for x in v['q'])
            canonical[f] = dict(canonical[f])
            canonical[f][n] = v
            flipped.append([f, n])
        bpy.data.actions.remove(act)
        act, mismatch = B.key_action(stem(name), frames, canonical)
        assert not mismatch, mismatch
        print('END_SIGN_MATCHED', name, flipped, flush=True)
    act['end_sign_matched'] = json.dumps(flipped)
    B.scene.frame_start, B.scene.frame_end = 1, N + 1
    B.scene.frame_set(1)
    act['duration_seconds'] = spec['T']
    act['fps'] = C.FPS
    act['loop'] = spec['loop']
    act['authoring'] = 'Original local FK/IK acting (Escape_Police_v01 package); no external motion reused'
    return act


# ----------------------------------------------------------------------------- metrics
def contact_metrics(B, name, frames, N, step=1):
    """Skinned-mesh floor penetration / touching-vertex slide (ground frame) / height, every half frame."""
    spec = REGISTRY[name]
    g = spec.get('ground')
    floor = spec.get('floor', lambda x, y, t: 0.0)
    keys = sorted(frames)[::step]
    prev = None
    pen, slide, hmax, zmin = 0.0, 0.0, 0.0, 9.0
    worst = None
    for f in keys:
        t = (f - 1) / C.FPS
        pts = B.mesh_points(frames[f])
        G = g(t) if g else 0.0
        fl = np.array([floor(x, y - G, t) for x, y in pts[:, :2]]) if spec.get('floor') else np.zeros(len(pts))
        h = pts[:, 2] - fl
        pen = max(pen, float(-h.min()))
        zmin = min(zmin, float(h.min()))
        top = spec.get('height_ref', lambda t: 0.0)(t)
        hmax = max(hmax, float(pts[:, 2].max() - top))
        touch = h < 0.002
        if prev is not None:
            pp, ptouch, pG = prev
            both = touch & ptouch
            if both.any():
                d = pts[both, :2] - pp[both, :2]
                d[:, 1] -= (G - pG)
                s = float(np.sqrt((d * d).sum(1)).max())
                if s > slide:
                    slide, worst = s, f
        prev = (pts, touch, G)
    return {'floor_penetration_mm': pen * 1000, 'contact_slide_mm_per_half_frame': slide * 1000,
            'worst_slide_frame': worst, 'max_height_above_ref_m': hmax, 'min_floor_clearance_m': zmin}


def key_steps(frames, B):
    worst = (0.0, None, None)
    ks = sorted(frames)
    vals = [B.values_from_pose(frames[f]) for f in ks]
    for i in range(len(ks) - 1):
        for n in B.order:
            a = vals[i][n]['q']
            b = vals[i + 1][n]['q']
            d = abs(sum(x * y for x, y in zip(a, b)))
            ang = math.degrees(2 * math.acos(min(1.0, d)))
            if ang > worst[0]:
                worst = (ang, ks[i], n)
    return worst


# ----------------------------------------------------------------------------- review
def review(B, name, N, args, out_dir):
    spec = REGISTRY[name]
    scene = B.scene
    col, cam = C.studio(scene)
    floor_obj = bpy.data.objects.get('Studio_Floor')
    stage = spec.get('stage_objects')
    movers = stage(col) if stage else []
    if spec.get('ground') and not stage:
        tread = E.treadmill(scene, col)
        floor_obj.hide_render = True
        movers = [(tread, 0.5)]
    if spec.get('floor_offset') is not None:
        floor_obj.location.z = spec['floor_offset']
        floor_obj.hide_render = False
    E.setup_engine(scene, args.res, args.engine)
    if args.engine == 'WORKBENCH':
        scene.world.color = (0.62, 0.64, 0.68)
    views = spec.get('views', VIEWS_STAND)
    out = Path(out_dir)
    if args.times:
        fr = [1 + float(x) * C.FPS for x in args.times.split(',')]
    else:
        fr = [float(f) for f in range(1, N + 2, args.every)]
        if fr[-1] != N + 1:
            fr.append(float(N + 1))
    g = spec.get('ground')
    for v in args.views.split(','):
        loc, tgt, ortho = views[v]
        C.aim(cam, loc, tgt, ortho)
        for k, f in enumerate(fr):
            scene.frame_set(int(f), subframe=f % 1)
            t = (f - 1) / C.FPS
            for o, period in movers:
                G = g(t) if g else 0.0
                o.location.y = (G % period) if period else G
            p = out / v / (('s%04d.png' % k) if args.seq else ('f%07.2f.png' % f))
            p.parent.mkdir(parents=True, exist_ok=True)
            scene.render.filepath = str(p)
            bpy.ops.render.render(write_still=True)
    if not args.seq:
        grid(out, name, args)
    print('REVIEW_DONE', name, len(fr), flush=True)


def grid(out, name, args):
    from PIL import Image, ImageDraw
    for v in args.views.split(','):
        files = sorted((out / v).glob('f*.png'))
        if not files:
            continue
        s = 260
        cols = args.cols
        rows = (len(files) + cols - 1) // cols
        img = Image.new('RGB', (cols * s, 20 + rows * (s + 14)), (35, 39, 46))
        d = ImageDraw.Draw(img)
        d.text((4, 3), '%s | %s' % (name, v), fill='white')
        for i, f in enumerate(files):
            x, y = (i % cols) * s, 20 + (i // cols) * (s + 14)
            img.paste(Image.open(f).convert('RGB').resize((s, s)), (x, y))
            fr = float(f.stem[1:])
            d.text((x + 3, y + s), 'f%g %.2fs' % (fr, (fr - 1) / C.FPS), fill='white')
        img.save(out / ('grid_%s_%s.png' % (name, v)))


VIEWS_STAND = {
    'side': ((5.0, 0.0, 1.6), (0.0, 0.0, 0.85), 2.3),
    'three_quarter': ((3.4, -4.4, 1.85), (0.0, 0.0, 0.86), 2.3),
    'front': ((0.0, -5.0, 1.0), (0.0, 0.0, 0.88), 2.3),
    'three_quarter_r': ((-3.4, -4.4, 1.85), (0.0, 0.0, 0.86), 2.3),
    'back34': ((-3.4, 4.4, 1.85), (0.0, 0.0, 0.86), 2.3),
}


# ----------------------------------------------------------------------------- final
def final(B, name, act, N, info, frames, args):
    st = stem(name)
    dest = Path(args.dest) if args.dest else HERE
    dest.mkdir(parents=True, exist_ok=True)
    for ext in ('.blend', '.fbx', '_authoring.json'):
        assert not (dest / (st + ext)).exists(), 'Refusing overwrite ' + st + ext
    assert len(B.rig.data.bones) == 65 and all(abs(s - 1) < 1e-9 for s in B.rig.scale)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(dest / (st + '.blend')))
    B.export_fbx(act, dest / (st + '.fbx'))
    spec = REGISTRY[name]
    rep = {'clip': st, 'action': act.name, 'frames': [1, N + 1], 'fps': C.FPS, 'duration_s': spec['T'],
           'loop': spec['loop'], 'sampling': 'half-frame keys (60 Hz), linear interpolation',
           'start_contract': spec.get('start', ''), 'end_contract': spec.get('end', ''),
           'events': spec.get('events', {}), 'ground_speed': spec.get('ground_note', 'none (in place, static floor)'),
           'beats': spec.get('beats', []),
           'max_leg_ik_overreach_m': max(i.get('leg_over', 0.0) for i in info),
           'max_arm_ik_overreach_m': max(i.get('arm_over', 0.0) for i in info),
           'hips_first': list(frames[1.0][C.P + 'Hips'].translation),
           'hips_last': list(frames[float(N + 1)][C.P + 'Hips'].translation)}
    (dest / (st + '_authoring.json')).write_text(json.dumps(rep, indent=2), encoding='utf-8')
    print('FINAL_SAVED', st, flush=True)


ARGS = None


def main():
    global ARGS
    args = ARGS = parse()
    names = list(REGISTRY) if args.clip == 'all' else args.clip.split(',')
    B = C.Buddy()
    cache = {}
    for name in names:
        t0 = time.time()
        frames, info, canonical, N, ctx = author(B, name, cache)
        if args.trace:
            pts = ('HeadTop_End', 'Head', 'Neck', 'Spine2', 'Hips', 'LeftArm', 'RightArm', 'LeftHand', 'RightHand',
                   'LeftLeg', 'RightLeg', 'LeftFoot', 'RightFoot', 'LeftToeBase', 'RightToeBase')
            tr = {'T': REGISTRY[name]['T'], 'fps': C.FPS,
                  'points': {p: [list(frames[1 + i / 2][C.P + p].translation) for i in range(2 * N + 1)] for p in pts}}
            Path(args.trace).write_text(json.dumps(tr), encoding='utf-8')
        if args.metrics:
            m = {'leg_over_max_m': max(i.get('leg_over', 0) for i in info),
                 'arm_over_max_m': max(i.get('arm_over', 0) for i in info)}
            m.update(contact_metrics(B, name, frames, N))
            for fk, vals in canonical.items():      # authored pose vs the exactly keyed contract pose
                m['contract_err_f%g' % fk] = E.contract_error(frames[fk], B.pose_from_values(vals))
            ang, f, n = key_steps(frames, B)
            m['max_half_frame_rot_deg'] = ang
            m['max_rot_at'] = [f, n]
            for k, v in REGISTRY[name].get('extra_metrics', lambda ctx, fr, inf: {})(ctx, frames, info).items():
                m[k] = v
            print('METRICS', name, json.dumps(m), flush=True)
        act = key(B, name, frames, canonical, N)
        if args.review:
            review(B, name, N, args, Path(args.review) / name)
        if args.final:
            final(B, name, act, N, info, frames, args)
        print('DONE', name, '%.1fs' % (time.time() - t0), flush=True)
        if args.review or args.final:   # the studio / saved file pollute the scene: reload for the next clip
            if name != names[-1]:
                B = C.Buddy()


if __name__ == '__main__':
    main()
