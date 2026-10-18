"""Build driver for the Escape_v01 package (Blender 5.2, headless; one clip per process).

  blender -b --factory-startup --python build_esc_v01.py -- --clip <Name> [--final] [--stills <dir>] [--validate]
      author one clip in memory; --final saves <stem>.blend / .fbx / _authoring.json here (never
      overwrites); --stills renders the review stills of its shot times; --validate samples the keyed
      action at 120 Hz (+ FBX reimport after --final) and writes the result into _authoring.json
  blender -b --factory-startup --python build_esc_v01.py -- --keys
      writes esc_pose_keys_v01.json and Esc_BuckleTargets_v01.json/.fbx (never overwrites)
Clip names: see CLIP_NAMES. Half-frame keys (60 Hz), linear; start/end frames keyed with the exact
raw values of their pose keys.
"""
from pathlib import Path
import sys, json, math, argparse, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import esc_core as E
import esc_clips as EC
import esc_hop as EH
import esc_render as ER
import acting_core as AC
import op_clips as OC
from acting_core import P

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--clip', default='')
ap.add_argument('--final', action='store_true')
ap.add_argument('--validate', action='store_true')
ap.add_argument('--stills', default='')
ap.add_argument('--res', type=int, default=300)
ap.add_argument('--views', default='')
ap.add_argument('--keys', action='store_true')
ap.add_argument('--dest', default='')
args = ap.parse_args(argv)
DEST = Path(args.dest) if args.dest else HERE

CLIP_NAMES = ['UnbuckleArmR_ByL', 'UnbuckleArmL_ByR', 'TugArmR', 'TugArmL', 'SitUp', 'UnbuckleLegL', 'UnbuckleLegR',
              'UnbuckleLegsBoth', 'TugLegs', 'SwingOff', 'HopRun', 'SlumpLieReachR', 'SlumpLieReachL', 'SlumpSit']
SHOTS = {
    'UnbuckleArmR_ByL': (0.0, 0.66, 0.80, 1.06, 1.46, 1.86, 2.6),
    'UnbuckleArmL_ByR': (0.0, 0.66, 0.80, 1.06, 1.46, 1.86, 2.6),
    'TugArmR': (0.0, 0.42, 0.74, 1.24, 1.62, 2.0),
    'TugArmL': (0.0, 0.42, 0.74, 1.24, 1.62, 2.0),
    'SitUp': (0.0, 0.20, 0.34, 0.52, 0.70, 1.0),
    'UnbuckleLegL': (0.0, 0.52, 0.80, 1.00, 1.40, 1.90, 2.3),
    'UnbuckleLegR': (0.0, 0.52, 0.80, 1.00, 1.40, 1.90, 2.3),
    'UnbuckleLegsBoth': (0.0, 0.52, 0.80, 1.00, 1.14, 1.48, 2.6),
    'TugLegs': (0.0, 0.34, 0.72, 1.10, 1.6),
    'SwingOff': (0.0, 0.40, 0.58, 0.76, 0.92, 1.2),
    'HopRun': None,
    'SlumpLieReachR': (0.0, 0.07, 0.20, 0.42, 0.70, 1.3),
    'SlumpLieReachL': (0.0, 0.07, 0.20, 0.42, 0.70, 1.3),
    'SlumpSit': (0.0, 0.08, 0.26, 0.50, 0.66, 1.4),
}


# ---------------------------------------------------------------------------------------- registry
def make_specs(lib):
    sp = {}
    sp['UnbuckleArmR_ByL'] = EC.unbuckle_arm(lib, 'L')
    sp['UnbuckleArmL_ByR'] = EC.unbuckle_arm(lib, 'R')
    sp['TugArmR'] = EC.tug_arm(lib, 'R')
    sp['TugArmL'] = EC.tug_arm(lib, 'L')
    sp['SitUp'] = EC.sit_up(lib)
    sp['UnbuckleLegL'] = EC.unbuckle_legs(lib, ['L'])
    sp['UnbuckleLegR'] = EC.unbuckle_legs(lib, ['R'])
    sp['UnbuckleLegsBoth'] = EC.unbuckle_legs(lib, ['L', 'R'])
    sp['TugLegs'] = EC.tug_legs(lib)
    sp['SwingOff'] = EC.swing_off(lib)
    sp['HopRun'] = EH.hop_run(lib)
    # slumps start on the grab pose of their reach clip: copy that clip's channels at the grab time
    for nm, src, A in (('SlumpLieReachR', 'UnbuckleArmR_ByL', 'L'), ('SlumpLieReachL', 'UnbuckleArmL_ByR', 'R')):
        curves, _ = E.build_curves(sp[src]['keys'], lib.ctx)
        tp = sp[src]['peak'][1]
        rc = {k: cv(tp) for k, cv in curves.items()}
        sp[nm] = EC.slump_lie(lib, A, rc)
    curves, _ = E.build_curves(sp['UnbuckleLegsBoth']['keys'], lib.ctx)
    tp = sp['UnbuckleLegsBoth']['peak'][1]
    sp['SlumpSit'] = EC.slump_sit(lib, {k: cv(tp) for k, cv in curves.items()})
    return sp


def strap_state(spec, t):
    """angle (deg) per limb strap at time t, and the closed flags for the limb constraints."""
    ang, closed = {}, {}
    for n in E.LIMB_STRAPS:
        if n in spec['straps']:
            a = max(0.0, EC.strap_curve(spec['straps'][n])(t))
        else:
            a = 0.0 if n in spec['closed0'] else E.OPEN_DEG
        ang[n] = a
        kind = 'arm' if 'ARM' in n else 'leg'
        closed[kind + '_' + n[-1]] = (n in spec['closed0']) and a < 0.25
    return ang, closed


class Session:
    def __init__(self):
        t0 = time.time()
        self.B = E.O.Patient()
        self.flee = EH.load_flee(self.B)          # Flee_Run_v01 samples (appended action removed again)
        self.S = E.Stage()
        self.ctx = E.EscCtx(self.B, self.S)
        self.ctx.flee = self.flee
        self.lib = EC.Lib(self.ctx)
        self.specs = make_specs(self.lib)
        self.keys = self.pose_keys()
        print('SESSION ready %.1f s' % (time.time() - t0), flush=True)

    def eval_spec(self, spec, t, curves=None):
        if curves is None:
            curves, _ = E.build_curves(spec['keys'], self.ctx)
        c = {k: cv(t) for k, cv in curves.items()}
        ang, closed = strap_state(spec, t)
        if 'pose_fn' in spec:
            return spec['pose_fn'](self, spec, t, c, closed)
        out, cc, info = self.ctx.solve(c, closed)
        return out, info

    def pose_keys(self):
        B, ctx, lib = self.B, self.ctx, self.lib
        keys = {'LIE': B.tablerest_values}
        sit, _, _ = ctx.solve({**ctx.ch0(), **lib.SIT()}, {'leg_L': True, 'leg_R': True})
        keys['SIT'] = B.values_from_pose(sit)
        edge, _, _ = ctx.solve({**ctx.ch0(), **lib.EDGE()}, {})
        keys['EDGE_R'] = B.values_from_pose(edge)
        for nm in ('UnbuckleArmR_ByL', 'UnbuckleArmL_ByR', 'UnbuckleLegsBoth'):
            sp = self.specs[nm]
            k, tp = sp['peak']
            out, _ = self.eval_spec(sp, tp)
            keys[k] = B.values_from_pose(out)
        keys['RUN0'] = B.values_from_pose(EH.run0_pose(self))
        return keys


# ---------------------------------------------------------------------------------------- authoring
def author(sess, name):
    B, ctx = sess.B, sess.ctx
    spec = sess.specs[name]
    T = spec['T']
    N = int(round(T * E.FPS))
    assert abs(N - T * E.FPS) < 1e-6, ('clip length must be a whole number of frames', name, T)
    t0 = time.time()
    ctx.stats = {'rail_slide_max': 0.0, 'rail_miss_max': 0.0, 'ik_over_max': {}, 'contact_lift_max': 0.0}
    curves, _ = E.build_curves(spec['keys'], ctx)
    frames, info = {}, []
    for i in range(2 * N + 1):
        t = i / (2 * E.FPS)
        out, inf = sess.eval_spec(spec, t, curves)
        frames[1 + i / 2] = out
        inf = dict(inf)
        inf['t'] = t
        info.append(inf)
    canonical = {1.0: sess.keys[spec['start']], float(N + 1): sess.keys[spec['end']]}
    # post: rotation-step safety net (never touching the seam frames), in-between pad/floor lift
    changed = AC.limit_rotation_steps(B, frames, max_deg=21.0, keep=(1.0, float(N + 1)))
    smooth = smooth_root(sess, frames, keep=(1.0, float(N + 1)))
    lift = fix_inbetween(sess, spec, frames, keep=(1.0, float(N + 1)))
    act, mismatch = B.key_action(spec['stem'], frames, canonical)
    assert not mismatch, ('canonical quaternion sign differs from the continuous chain', mismatch[:5])
    B.scene.frame_start, B.scene.frame_end = 1, N + 1
    B.scene.render.fps = E.FPS
    B.scene.frame_set(1)
    act['duration_seconds'] = T
    act['fps'] = E.FPS
    act['loop'] = spec['loop']
    act['authoring'] = 'Original local FK/IK acting (Escape_v01 package); no external motion reused'
    stats = {'rail_slide_max_m': round(ctx.stats['rail_slide_max'], 4), 'rail_miss_max_m': round(ctx.stats['rail_miss_max'], 5),
             'ik_overreach_max_m': {k: round(v, 4) for k, v in ctx.stats['ik_over_max'].items()},
             'contact_root_lift_max_m': round(ctx.stats['contact_lift_max'], 4),
             'free_leg_pad_lift_max_deg': round(ctx.stats.get('leg_lift_max_deg', 0.0), 2),
             'head_pillow_lift_max_deg': round(ctx.stats.get('head_lift_max_deg', 0.0), 2),
             'step_limiter_bones': changed, 'root_height_smoothing_max_m': round(smooth, 4), 'inbetween_lift_max_m': round(lift, 5)}
    print('AUTHORED', name, spec['stem'], N, 'frames in %.1f s' % (time.time() - t0), json.dumps(stats), flush=True)
    return act, N, stats


def smooth_root(sess, frames, keep=(), acc_lim=0.006, pad_margin=0.0, floor_margin=0.0005):
    """The per-sample vertical contact solves (seat -> floor hand-over, hop take-off) can make the
    hips height jitter. Where the hips' vertical acceleration exceeds acc_lim (m per half-frame^2),
    smooth the height (rigid vertical shift of the whole pose), then add back a smoothed upper
    envelope of any lift still needed against the pad and the floor. Seam frames never move."""
    B, ctx = sess.B, sess.ctx
    keys = sorted(frames)
    n = len(keys)
    h = np.array([frames[f][P + 'Hips'].translation.z for f in keys])
    acc = np.zeros(n)
    acc[1:-1] = np.abs(h[:-2] + h[2:] - 2 * h[1:-1])
    bad = np.where(acc > acc_lim)[0]
    if not len(bad):
        return 0.0
    mask = np.zeros(n, dtype=bool)
    for i in bad:
        mask[max(1, i - 4):min(n - 1, i + 5)] = True
    for i, f in enumerate(keys):
        if f in keep:
            mask[i] = False
    hs = h.copy()
    for _ in range(12):
        nh = hs.copy()
        for i in np.where(mask)[0]:
            nh[i] = 0.25 * hs[i - 1] + 0.5 * hs[i] + 0.25 * hs[i + 1]
        hs = nh

    def shift(i, d):
        M = Matrix.Translation((0, 0, float(d)))
        frames[keys[i]] = {k: M @ v for k, v in frames[keys[i]].items()}
    for i in np.where(mask)[0]:
        shift(i, hs[i] - h[i])
    req = np.zeros(n)
    for i in np.where(mask)[0]:
        g, pts = ctx.pad_gap(frames[keys[i]])
        req[i] = max(0.0, pad_margin - g, floor_margin - float(pts[:, 2].min()))
    env = req.copy()
    for i in range(n):
        env[i] = req[max(0, i - 2):i + 3].max()
    for _ in range(3):
        e2 = env.copy()
        e2[1:-1] = 0.25 * env[:-2] + 0.5 * env[1:-1] + 0.25 * env[2:]
        env = np.maximum(e2, req)
    for i in np.where(mask)[0]:
        if env[i] > 0:
            shift(i, env[i])
    return float(np.max(np.abs(hs - h)))


def fix_inbetween(sess, spec, frames, keep=(), passes=3, pad_margin=0.0, floor_margin=0.0003):
    """Linear interpolation of raw values between two clean 60 Hz keys can sag a fast-moving body into
    the pad or floor: lift both neighbouring keys by the measured deficit of the mid sample."""
    B, ctx = sess.B, sess.ctx
    keys = sorted(frames)
    worst = 0.0
    for _ in range(passes):
        vals = {f: B.values_from_pose(frames[f]) for f in keys}
        lift = {f: 0.0 for f in keys}
        for f in keys:                        # the keys themselves (the step limiter can move limbs)
            if f in keep:
                continue
            g, pts = ctx.pad_gap(frames[f])
            d = max(pad_margin - g, floor_margin - float(pts[:, 2].min()))
            if d > 0:
                lift[f] = max(lift[f], d)
        for a, b in zip(keys[:-1], keys[1:]):
            mid = OC.pose_from_vals(B, OC.lerp_vals(B, vals[a], vals[b], 0.5))
            g, pts = ctx.pad_gap(mid)
            d = max(pad_margin - g, floor_margin - (float(pts[:, 2].min())))
            if d > 0:
                for f in (a, b):
                    if f not in keep:
                        lift[f] = max(lift[f], d)
        if max(lift.values()) <= 0:
            break
        for f, d in lift.items():
            if d > 0:
                M = Matrix.Translation((0, 0, d))
                frames[f] = {k: M @ v for k, v in frames[f].items()}
                worst = max(worst, d)
    return worst


# ---------------------------------------------------------------------------------------- validation
def sampled_pose(B, f):
    B.scene.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
    return {pb.name: pb.matrix.copy() for pb in B.rig.pose.bones}


def validate(sess, name, act, N):
    B, ctx = sess.B, sess.ctx
    spec = sess.specs[name]
    SC = E.SelfContact(ctx)
    res = {}
    # seams: raw keyed values at both ends vs the pose keys
    names = B.order

    def seam_err(f, key):
        v = AC.read_values(act, f, names)
        ref = sess.keys[key]
        e = 0.0
        for n in names:
            q1, q2 = Quaternion(v[n]['q']), Quaternion(ref[n]['q'])
            e = max(e, min(max(abs(a - b) for a, b in zip(q1, q2)), max(abs(a + b) for a, b in zip(q1, q2))))
            if v[n]['loc'] is not None:
                e = max(e, max(abs(a - b) for a, b in zip(v[n]['loc'], ref[n]['loc'])))
        return e
    res['seam_start_err'] = seam_err(1.0, spec['start'])
    res['seam_end_err'] = seam_err(float(N + 1), spec['end'])
    # key steps
    fcs = AC.fcurves_of(act)
    idx = {(fc.data_path, fc.array_index): fc for fc in fcs}
    step = 0.0
    worst_b = ''
    for n in names:
        qp = 'pose.bones["%s"].rotation_quaternion' % n
        prev = None
        for i in range(2 * N + 1):
            f = 1 + i / 2
            q = Quaternion([idx[(qp, k)].evaluate(f) for k in range(4)])
            if prev is not None:
                a = math.degrees(2 * math.acos(min(1.0, abs(prev.dot(q)) / (prev.magnitude * q.magnitude))))
                if a > step:
                    step, worst_b = a, n
            prev = q
    res['max_key_step_deg'] = round(step, 2)
    res['max_key_step_bone'] = worst_b
    # 120 Hz sampling: pad gaps per region, floor, closed-strap drift, self contact (30 Hz)
    gaps = {r: 1.0 for r in B.region_mask}
    gap_t = {}
    zmin, zmin_t = 1.0, 0.0
    drift = {}
    selfpen, selfpen_t = {}, {}
    for i in range(4 * N + 1):
        f = 1 + i / 4
        t = (f - 1) / E.FPS
        pose = sampled_pose(B, f)
        pts = ctx.world_pts(pose)
        top = sess.S.pad_top(pts)
        g = pts[:, 2] - top
        # inside the pad slab only: over the pad footprint (|x| <= 0.285) and less than 10 cm under its top
        inside = ~np.isnan(g) & (np.abs(pts[:, 0]) <= 0.285) & (g > -0.10)
        for r, m in B.region_mask.items():
            gg = g[m & inside]
            if len(gg) and float(gg.min()) < gaps[r]:
                gaps[r] = float(gg.min())
                gap_t[r] = round(t, 3)
        if float(pts[:, 2].min()) < zmin:
            zmin, zmin_t = float(pts[:, 2].min()), round(t, 3)
        ang, closed = strap_state(spec, t)
        sp = B.strap_points(pose)
        for k, on in closed.items():
            if on:
                kind, s = k.split('_')
                side = 'Left' if s == 'L' else 'Right'
                key = ('forearm_' if kind == 'arm' else 'shin_') + side
                d = (sp[key] - B.strap0[key]).length
                drift[k] = max(drift.get(k, 0.0), d)
        if i % 4 == 0:
            ap = B.skin(pose, world=False)
            for pk, tg in (('arm_Left', 'trunk'), ('arm_Left', 'head'), ('arm_Right', 'trunk'), ('arm_Right', 'head'),
                           ('leg_Left', 'head'), ('leg_Right', 'head')):
                k = '%s_in_%s' % (pk, tg)
                d = SC.depth(ap, pk, tg)
                if d > selfpen.get(k, 0.0):
                    selfpen[k], selfpen_t[k] = d, round(t, 3)
                selfpen.setdefault(k, 0.0)
    res['pad_gap_min_mm'] = {r: round(v * 1000, 2) for r, v in gaps.items() if v < 0.999}
    res['pad_gap_min_at_s'] = gap_t
    res['floor_min_mm'] = round(zmin * 1000, 2)
    res['floor_min_at_s'] = zmin_t
    res['closed_strap_drift_mm'] = {k: round(v * 1000, 1) for k, v in drift.items()}
    res['self_penetration_mm'] = {k: round(v * 1000, 1) for k, v in selfpen.items()}
    res['self_penetration_at_s'] = selfpen_t
    return res


def fbx_check(sess, name, act, N, fbx_path):
    """Reimport the FBX into the scene and compare armature-space bone matrices at 5 frames."""
    B = sess.B
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx_path), automatic_bone_orientation=False, ignore_leaf_bones=False)
    new = [o for o in bpy.data.objects if o not in before and o.type == 'ARMATURE']
    assert len(new) == 1, new
    imp = new[0]
    ia = imp.animation_data.action if imp.animation_data else None
    err_pos = 0.0
    bind = 0.0
    for b in imp.data.bones:
        m1, m2 = b.matrix_local, B.rig.data.bones[b.name].matrix_local
        bind = max(bind, max(abs(m1[i][j] - m2[i][j]) for i in range(4) for j in range(4)))
    for f in (1.0, 1 + N * 0.25, 1 + N * 0.5, 1 + N * 0.75, float(N + 1)):
        B.scene.frame_set(int(f), subframe=f % 1)
        for pb in B.rig.pose.bones:
            p1 = (B.rig.matrix_world @ pb.matrix).translation
            p2 = (imp.matrix_world @ imp.pose.bones[pb.name].matrix).translation
            # the reimported armature sits at the identity; compare in armature space
            p1 = pb.matrix.translation
            p2 = imp.pose.bones[pb.name].matrix.translation
            err_pos = max(err_pos, (p1 - p2).length)
    out = {'fbx_bind_err': bind, 'fbx_bone_pos_err_m': round(err_pos, 6), 'fbx_take_imported': ia.name if ia else None,
           'fbx_bones': len(imp.data.bones)}
    return out


# ---------------------------------------------------------------------------------------- stills
def render_stills(sess, name, outdir):
    B, S = sess.B, sess.S
    spec = sess.specs[name]
    shots = SHOTS.get(name) or spec.get('shots')
    cam = ER.setup(B.scene, res=args.res, samples=10)
    out = Path(outdir)
    views = args.views.split(',') if args.views else spec['views'][:1]
    for view in views:
        ER.aim(cam, view)
        for k, t in enumerate(shots):
            f = 1 + t * E.FPS
            B.scene.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
            ang, _ = strap_state(spec, t)
            S.set_angles(ang)
            ER.render_to(B.scene, out / name / view / ('s%02d_t%.2f.png' % (k, t)))
    print('STILLS_DONE', name, len(shots), flush=True)


# ---------------------------------------------------------------------------------------- final save
def strap_actions(sess, spec, N):
    """Review only (added AFTER the FBX export): strap objects keyed to the clip's strap timeline."""
    S = sess.S
    for n in E.LIMB_STRAPS:
        o = S.objs[n]
        o.rotation_mode = 'XYZ'
        if n not in spec['straps']:
            ang, _ = strap_state(spec, 0.0)
            S.set_angles(ang)
            continue
        for i in range(N + 1):
            t = i / E.FPS
            ang, _ = strap_state(spec, t)
            S.set_angles(ang)
            o.keyframe_insert('rotation_euler', frame=1 + i)


def final(sess, name, act, N, stats):
    B = sess.B
    spec = sess.specs[name]
    stem = spec['stem']
    for ext in ('.blend', '.fbx', '_authoring.json'):
        assert not (DEST / (stem + ext)).exists(), 'Refusing overwrite ' + stem + ext
    assert len(B.rig.data.bones) == 65 and all(abs(s - 1) < 1e-9 for s in B.rig.scale)
    B.export_fbx(act, DEST / (stem + '.fbx'))
    strap_actions(sess, spec, N)
    add_buckle_empties(sess)
    B.scene.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(DEST / (stem + '.blend')))
    print('FINAL_SAVED', stem, flush=True)


def add_buckle_empties(sess):
    """BUCKLE_* empties (closed strap, top-face centre, Z = outward normal) under the review table."""
    S = sess.S
    col = S.collection
    root = S.objs.get('RIG_Table_Root')
    for n in E.LIMB_STRAPS:
        nm = 'BUCKLE_' + n[len('STRAP_'):]
        if nm in bpy.data.objects:
            continue
        p, nrm, u, w = S.buckle(n, 0.0, space='table')
        e = bpy.data.objects.new(nm, None)
        e.empty_display_type = 'ARROWS'
        e.empty_display_size = 0.05
        zx = nrm
        xx = (w - zx * w.dot(zx)).normalized()
        yy = zx.cross(xx)
        M = Matrix((xx, yy, zx)).transposed().to_4x4()
        M.translation = p
        e.matrix_world = M
        col.objects.link(e)


def authoring_json(sess, name, N, stats, val):
    spec = sess.specs[name]
    T = spec['T']
    ev = [dict(e, norm=round(e['t'] / T, 4)) for e in spec['events']]
    straps = {}
    for n, ks in spec['straps'].items():
        straps[n] = {'angle_keys_deg': [[round(t, 4), a] for t, a in ks],
                     'angle_keys_norm': [[round(t / T, 4), a] for t, a in ks],
                     'note': 'rotation about the strap local +X (Unity same sign), 0 = closed, 120 = open; interpolate smoothly (monotone)'}
    rep = {
        'clip': spec['stem'], 'action': spec['stem'], 'take': 'Buddy_Rig_Mixamo65|' + spec['stem'],
        'frames': [1, N + 1], 'fps': E.FPS, 'duration_s': T, 'loop': spec['loop'],
        'sampling': 'half-frame keys (60 Hz), linear interpolation',
        'start_pose_key': spec['start'], 'end_pose_key': spec['end'],
        'preconditions': spec['pre'], 'straps_after': spec.get('after', {}),
        'strap_animation': straps, 'events': ev, 'next': spec.get('next', []), 'beats': spec.get('beats', []),
        'root_motion': spec.get('root', 'none: rig object at PatientRest, the Hips curves place the body (Apply Root Motion off)'),
        'authoring_stats': stats, 'validation': val,
        'source_patient': str(E.O.PATIENT_BLEND.relative_to(E.ANIM.parents[3])).replace('\\', '/'),
    }
    p = DEST / (spec['stem'] + '_authoring.json')
    assert not p.exists(), 'Refusing overwrite ' + p.name
    p.write_text(json.dumps(rep, indent=2), encoding='utf-8')


# ---------------------------------------------------------------------------------------- keys + targets
def write_keys(sess):
    B, S, ctx = sess.B, sess.S, sess.ctx
    out = {'version': 'esc_pose_keys_v01', 'fps': E.FPS, 'rig': E.O.RIG_NAME, 'bones': B.order,
           'note': 'raw pose-bone values (quaternion w,x,y,z; Hips location) keyed at clip seams; rig object at PatientRest',
           'run0_root_patientrest_unity': EH.run0_root_unity(sess), 'keys': {}}
    for k, v in sess.keys.items():
        out['keys'][k] = {n: {'q': [round(x, 8) for x in v[n]['q']], 'loc': [round(x, 8) for x in v[n]['loc']] if v[n]['loc'] else None}
                          for n in B.order}
    p = DEST / 'esc_pose_keys_v01.json'
    assert not p.exists()
    p.write_text(json.dumps(out, indent=1), encoding='utf-8')
    # buckle targets: closed position, hinge, and the path while opening
    tg = {'version': 'Esc_BuckleTargets_v01', 'source': 'ArtSource/Props/TABLE-ASTRA-001/v02/TABLE-ASTRA-001_v02.blend (strap meshes, buckle block = small mesh component, top-face centre)',
          'frames': 'table_blender = RIG_Table_Root space (head end -Y, patient left -X); unity_prefab = (-x, z, -y); patientrest_armature = authoring space (head +Y, patient left +X, pad ~0)',
          'grip_rule': 'hand palm-surface point (centre of the palm, 4.5-7.5 cm from the wrist) placed 4 mm along the buckle normal above the top-face centre; palm normal = -buckle normal',
          'targets': {}}
    for n in E.LIMB_STRAPS:
        p, nrm, u, w = S.buckle(n, 0.0, space='table')
        pa, na, ua, wa = S.buckle(n, 0.0, space='arm')
        st = S.objs[n]
        piv = S.strap_matrix(n, 0.0).translation
        path = []
        for a in (0, 10, 20, 30, 40, 60, 90, 120):
            q, qn, _, _ = S.buckle(n, a, space='table')
            path.append({'deg': a, 'table_blender': [round(x, 4) for x in q], 'unity_prefab': [round(-q.x, 4), round(q.z, 4), round(-q.y, 4)]})
        tg['targets']['BUCKLE_' + n[len('STRAP_'):]] = {
            'strap': n,
            'table_blender': {'pos': [round(x, 4) for x in p], 'normal': [round(x, 4) for x in nrm]},
            'unity_prefab': {'pos': [round(-p.x, 4), round(p.z, 4), round(-p.y, 4)], 'normal': [round(-nrm.x, 4), round(nrm.z, 4), round(-nrm.y, 4)]},
            'patientrest_armature': {'pos': [round(x, 4) for x in pa], 'normal': [round(x, 4) for x in na]},
            'hinge_pivot_table_blender': [round(x, 4) for x in piv],
            'opening_path': path,
        }
    p2 = DEST / 'Esc_BuckleTargets_v01.json'
    assert not p2.exists()
    p2.write_text(json.dumps(tg, indent=1), encoding='utf-8')
    # FBX with the four empties under a table-root empty (Unity: drop under the table prefab root)
    for o in list(bpy.data.objects):
        o.select_set(False)
    root = bpy.data.objects.new('TABLE_ROOT_REF', None)
    bpy.context.scene.collection.objects.link(root)
    add_buckle_empties(sess)
    for n in E.LIMB_STRAPS:
        e = bpy.data.objects['BUCKLE_' + n[len('STRAP_'):]]
        mw = e.matrix_world.copy()
        e.parent = root
        e.matrix_world = mw
        e.select_set(True)
    root.select_set(True)
    p3 = DEST / 'Esc_BuckleTargets_v01.fbx'
    assert not p3.exists()
    bpy.ops.export_scene.fbx(filepath=str(p3), use_selection=True, object_types={'EMPTY'}, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, bake_anim=False, add_leaf_bones=False)
    print('KEYS_WRITTEN', flush=True)


if __name__ == '__main__':
    sess = Session()
    if args.keys:
        write_keys(sess)
    if args.clip:
        assert args.clip in CLIP_NAMES, args.clip
        act, N, stats = author(sess, args.clip)
        val = {}
        if args.validate:
            val = validate(sess, args.clip, act, N)
            print('VALIDATION', args.clip, json.dumps(val), flush=True)
        if args.stills:
            render_stills(sess, args.clip, args.stills)
        if args.final:
            final(sess, args.clip, act, N, stats)
            if args.validate:
                val.update(fbx_check(sess, args.clip, act, N, DEST / (sess.specs[args.clip]['stem'] + '.fbx')))
                print('FBX', json.dumps({k: v for k, v in val.items() if k.startswith('fbx')}), flush=True)
            authoring_json(sess, args.clip, N, stats, val)
