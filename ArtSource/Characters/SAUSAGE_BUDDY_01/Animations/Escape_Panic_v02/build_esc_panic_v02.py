"""Build driver for the Escape_Panic_v02 package (Blender 5.2, headless; one clip per process).

  blender -b --factory-startup --python build_esc_panic_v02.py -- --clip <Name> [--validate] [--final]
          [--stills <dir>] [--strip <dir>] [--res 300] [--strip_res 200] [--strip_step 3]
      author one clip; --final saves <stem>.blend / .fbx / _authoring.json here (never overwrites);
      --stills renders the key-pose stills (spec shots) for the contact sheet; --strip renders every
      strip_step-th frame of the clip (PNG frames, no video); --validate = v01 validation (120 Hz pad / floor /
      strap drift / self contact) + buckle contact errors + seam / chain checks (+ FBX reimport after --final)
  blender -b --factory-startup --python build_esc_panic_v02.py -- --keys
      writes esc_pose_keys_v02.json (the new keys BCRUN, RUN0_BC, RUN0_BC_L; all others = esc_pose_keys_v01.json)
  blender ... -- --list
Clip names: the short names of esc_panic_clips.make_specs (without the P2_ prefix) or the file stems.

Reuses ../Escape_v01/build_esc_v01.py (Session, smoothing, validation, FBX export, buckle empties) read-only.
"""
from pathlib import Path
import sys, json, math, argparse, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V01 = HERE.parent / 'Escape_v01'
for p in (str(V01), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)
_argv = sys.argv
sys.argv = [_argv[0]]
import build_esc_v01 as BE           # parses an empty argv at import
sys.argv = _argv
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
import esc_panic_clips as PC

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--clip', default='')
ap.add_argument('--final', action='store_true')
ap.add_argument('--validate', action='store_true')
ap.add_argument('--stills', default='')
ap.add_argument('--strip', default='')
ap.add_argument('--res', type=int, default=300)
ap.add_argument('--strip_res', type=int, default=200)
ap.add_argument('--strip_step', type=int, default=3)
ap.add_argument('--keys', action='store_true')
ap.add_argument('--list', action='store_true')
ap.add_argument('--times', default='', help='review renders at these clip times (comma list) into --stills dir')
ap.add_argument('--view', default='')
args = ap.parse_args(argv)
DEST = HERE
BE.DEST = HERE
KEYS_V01 = V01 / 'esc_pose_keys_v01.json'


# ---------------------------------------------------------------------------------------- session
def session():
    t0 = time.time()
    sess = BE.Session()
    PC.install(sess)
    specs = PC.make_specs(sess)
    sess.specs.update(specs)
    PC.add_keys(sess)
    sess.p2 = sorted(specs)
    print('PANIC SESSION ready %.1f s' % (time.time() - t0), flush=True)
    return sess


def resolve(sess, name):
    for k in sess.p2:
        if name in (k, k[3:], sess.specs[k]['stem']):
            return k
    raise SystemExit('unknown clip %s; known: %s' % (name, ', '.join(k[3:] for k in sess.p2)))


def pose_err(a, b):
    return max((a[n].translation - b[n].translation).length for n in a)


RUN_VIEW = None


def run_placement(sess):
    """Review placement of the cycle-space run loop: on the floor at the v01 RUN0 root (table space)."""
    EH.setup_run(sess, 'R')
    return E.W_PR @ EH.run_root(sess, EH.T_HOP, 'R')


# ---------------------------------------------------------------------------------------- authoring
def author(sess, key):
    B, ctx = sess.B, sess.ctx
    spec = sess.specs[key]
    T = spec['T']
    N = int(round(T * E.FPS))
    assert abs(N - T * E.FPS) < 1e-6, ('clip length must be a whole number of frames', key, T)
    t0 = time.time()
    ctx.stats = {'rail_slide_max': 0.0, 'rail_miss_max': 0.0, 'ik_over_max': {}, 'contact_lift_max': 0.0}
    frames = {}
    # instrument: when does each IK chain overreach the most
    over_t, cur = {}, [0.0]
    hik0 = type(ctx).hand_ik

    def hik(out, s, grip, f, n, pole, tag=''):
        o = hik0(ctx, out, s, grip, f, n, pole, tag)
        k = tag or s
        if o > over_t.get(k, (0.0, 0.0))[0]:
            over_t[k] = (o, round(cur[0], 3))
        return o
    ctx.hand_ik = hik
    if spec.get('cycle'):
        for i in range(2 * N + 1):
            frames[1 + i / 2] = PC.bc_cycle_pose(sess, i / (2 * E.FPS))
    else:
        curves, _ = E.build_curves(spec['keys'], ctx)
        for i in range(2 * N + 1):
            t = i / (2 * E.FPS)
            cur[0] = t
            out, inf = sess.eval_spec(spec, t, curves)
            frames[1 + i / 2] = out
    del ctx.hand_ik
    canonical = {1.0: sess.keys[spec['start']], float(N + 1): sess.keys[spec['end']]}
    seam_eval = {}
    for f, vals in canonical.items():
        seam_eval['t0' if f == 1.0 else 'tEnd'] = round(pose_err(frames[f], OC.pose_from_vals(B, vals)) * 1000, 3)
    keep = (1.0, float(N + 1))
    # buckle contact samples are never touched by the step limiter (exact contact on the v01 targets)
    kc = set(keep)
    for c in spec.get('contacts', []):
        x = 1 + c['t'] * E.FPS
        kc |= {math.floor(x * 2) / 2, math.ceil(x * 2) / 2}
    changed = AC.limit_rotation_steps(B, frames, max_deg=21.0, keep=tuple(sorted(kc)))
    smooth = lift = 0.0
    if not spec.get('cycle'):
        if spec.get('root_smooth', True):       # off for the sitting-hop clips: a rigid shift would push the strapped legs into the pad
            smooth = BE.smooth_root(sess, frames, keep=keep)
        lift = BE.fix_inbetween(sess, spec, frames, keep=keep)
    act, mismatch = B.key_action(spec['stem'], frames, canonical)
    assert not mismatch, ('canonical quaternion sign differs from the continuous chain', mismatch[:5])
    B.scene.frame_start, B.scene.frame_end = 1, N + 1
    B.scene.render.fps = E.FPS
    B.scene.frame_set(1)
    act['duration_seconds'] = T
    act['fps'] = E.FPS
    act['loop'] = spec['loop']
    act['authoring'] = 'Original local FK/IK acting (Escape_Panic_v02 package, panic variants of Escape_v01); no external motion reused'
    stats = {'rail_slide_max_m': round(ctx.stats['rail_slide_max'], 4), 'rail_miss_max_m': round(ctx.stats['rail_miss_max'], 5),
             'ik_overreach_max_m': {k: round(v, 4) for k, v in ctx.stats['ik_over_max'].items()},
             'hand_ik_overreach_at_s': {k: v[1] for k, v in over_t.items() if v[0] > 0.005},
             'contact_root_lift_max_m': round(ctx.stats['contact_lift_max'], 4),
             'free_leg_pad_lift_max_deg': round(ctx.stats.get('leg_lift_max_deg', 0.0), 2),
             'head_pillow_lift_max_deg': round(ctx.stats.get('head_lift_max_deg', 0.0), 2),
             'step_limiter_bones': changed, 'root_height_smoothing_max_m': round(smooth, 4), 'inbetween_lift_max_m': round(lift, 5),
             'seam_eval_vs_pose_key_mm': seam_eval}
    print('AUTHORED', key, spec['stem'], N, 'frames in %.1f s' % (time.time() - t0), json.dumps(stats), flush=True)
    return act, N, stats


# ---------------------------------------------------------------------------------------- validation
HANDS = {'Left': P + 'LeftHand', 'Right': P + 'RightHand'}
FEET = {'Left': P + 'LeftFoot', 'Right': P + 'RightFoot'}


def extra_checks(sess, key, act, N):
    """Buckle contacts, v01 key-file seams, end velocities of hands / feet (chain pops)."""
    B, ctx, S = sess.B, sess.ctx, sess.S
    spec = sess.specs[key]
    res = {}
    cts = []
    for c in spec.get('contacts', []):
        t = c['t']
        f = 1 + t * E.FPS
        pose = BE.sampled_pose(B, f)
        sk = spec['straps'].get(c['strap'])
        ang = max(0.0, EC.strap_curve(sk)(t)) if sk else 0.0
        p, n, u, w = S.buckle(c['strap'], ang)
        tgt = p + n * c['lift']
        g = ctx.grip_point(pose, EC.side_name(c['hand']))
        cts.append({'t': t, 'frame': round(f, 2), 'hand': EC.side_name(c['hand']), 'strap': c['strap'], 'strap_deg': round(ang, 1),
                    'grip_to_target_mm': round((g - tgt).length * 1000, 2)})
    if cts:
        res['buckle_contacts'] = cts
        res['buckle_contact_err_max_mm'] = max(x['grip_to_target_mm'] for x in cts)
    # seams vs the shipped v01 pose-key file (exact raw values)
    kj = json.loads(KEYS_V01.read_text(encoding='utf-8'))['keys']
    seam = {}
    for f, k in ((1.0, spec['start']), (float(N + 1), spec['end'])):
        if k not in kj:
            seam[k] = 'new key (esc_pose_keys_v02.json)'
            continue
        v = AC.read_values(act, f, B.order)
        e = 0.0
        for n in B.order:
            q1, q2 = Quaternion(v[n]['q']), Quaternion(kj[k][n]['q'])
            e = max(e, min(max(abs(a - b) for a, b in zip(q1, q2)), max(abs(a + b) for a, b in zip(q1, q2))))
            if v[n]['loc'] is not None:
                e = max(e, max(abs(a - b) for a, b in zip(v[n]['loc'], kj[k][n]['loc'])))
        seam[k] = round(e, 7)
    res['seam_vs_esc_pose_keys_v01_raw_max'] = seam
    # first / last half-frame step of hands, feet, head, hips (m per half frame): a pop shows as a big step
    def joints(f):
        pose = BE.sampled_pose(B, f)
        jn = [('hand_' + k, b) for k, b in HANDS.items()] + [('foot_' + k, b) for k, b in FEET.items()] + [('Head', P + 'Head'), ('Hips', P + 'Hips')]
        return {nm: pose[b].translation.copy() for nm, b in jn}
    a0, a1 = joints(1.0), joints(1.5)
    b0, b1 = joints(N + 0.5), joints(float(N + 1))
    res['seam_step_start_mm'] = {k: round((a1[k] - a0[k]).length * 1000, 1) for k in a0}
    res['seam_step_end_mm'] = {k: round((b1[k] - b0[k]).length * 1000, 1) for k in b0}
    # largest step anywhere (for reference)
    mx, mx_at = {}, {}
    prev = joints(1.0)
    for i in range(1, 2 * N + 1):
        cur = joints(1 + i / 2)
        for k in cur:
            d = (cur[k] - prev[k]).length
            if d > mx.get(k, 0.0):
                mx[k], mx_at[k] = d, round(i / (2 * E.FPS), 3)
        prev = cur
    res['max_step_mm'] = {k: round(v * 1000, 1) for k, v in mx.items()}
    # when does the closed-strap drift peak (BE.validate gives the size only)
    dr, dr_t = {}, {}
    for i in range(2 * N + 1):
        t = i / (2 * E.FPS)
        ang, closed = BE.strap_state(spec, t)
        if not any(closed.values()):
            continue
        sp = B.strap_points(BE.sampled_pose(B, 1 + i / 2))
        for k, on in closed.items():
            if on:
                kind, sd = k.split('_')
                kk = ('forearm_' if kind == 'arm' else 'shin_') + ('Left' if sd == 'L' else 'Right')
                d = (sp[kk] - B.strap0[kk]).length
                if d > dr.get(k, 0.0):
                    dr[k], dr_t[k] = d, round(t, 3)
    res['closed_strap_drift_at_s'] = dr_t
    res['max_step_at_s'] = mx_at
    return res


def validate_cycle(sess, key, act, N):
    """Run loop (cycle space): floor, self contact, key steps, loop seam."""
    B, ctx = sess.B, sess.ctx
    SC = E.SelfContact(ctx)
    res = {}
    zmin, zmin_t = 1.0, 0.0
    selfpen, selfpen_t = {}, {}
    for i in range(4 * N + 1):
        f = 1 + i / 4
        pose = BE.sampled_pose(B, f)
        pts = B.skin(pose, world=False)
        z = float(pts[:, 2].min())
        if z < zmin:
            zmin, zmin_t = z, round((f - 1) / E.FPS, 3)
        if i % 2 == 0:
            for pk in ('arm_Left', 'arm_Right'):
                for tg in ('trunk', 'head'):
                    k = '%s_in_%s' % (pk, tg)
                    d = SC.depth(pts, pk, tg)
                    if d > selfpen.get(k, 0.0):
                        selfpen[k], selfpen_t[k] = d, round((f - 1) / E.FPS, 3)
                    selfpen.setdefault(k, 0.0)
    res['floor_min_mm'] = round(zmin * 1000, 2)
    res['floor_min_at_s'] = zmin_t
    res['self_penetration_mm'] = {k: round(v * 1000, 1) for k, v in selfpen.items()}
    res['self_penetration_at_s'] = selfpen_t
    # plain Flee_Run floor for reference
    z0 = min(float(B.skin(OC.pose_from_vals(B, s), world=False)[:, 2].min()) for s in sess.flee['samples'][::2])
    res['flee_run_v01_floor_min_mm'] = round(z0 * 1000, 2)
    return res


def key_steps(sess, act, N):
    B = sess.B
    fcs = AC.fcurves_of(act)
    idx = {(fc.data_path, fc.array_index): fc for fc in fcs}
    step, worst = 0.0, ''
    for n in B.order:
        qp = 'pose.bones["%s"].rotation_quaternion' % n
        prev = None
        for i in range(2 * N + 1):
            q = Quaternion([idx[(qp, k)].evaluate(1 + i / 2) for k in range(4)])
            if prev is not None:
                a = math.degrees(2 * math.acos(min(1.0, abs(prev.dot(q)) / (prev.magnitude * q.magnitude))))
                if a > step:
                    step, worst = a, n
            prev = q
    return {'max_key_step_deg': round(step, 2), 'max_key_step_bone': worst}


# ---------------------------------------------------------------------------------------- renders
_CAM = {}


def cam(sess, res):
    if 'cam' not in _CAM:
        _CAM['cam'] = ER.setup(sess.B.scene, res=res, samples=10)
        # review view for the run loop: beside the runner placed at RUN0 (table space)
        M = run_placement(sess)
        p = M.translation
        fwd = (M.to_3x3() @ Vector((0, -1, 0))).normalized()
        side = Vector((0, 0, 1)).cross(fwd).normalized()
        loc = p + side * 2.6 - fwd * 0.35 + Vector((0, 0, 0.95))
        ER.VIEWS['run'] = (tuple(loc), tuple(p + Vector((0, 0, 0.62))), None, 35)
        lo, tg, o_, ln = ER.VIEWS['exit']           # mirror of the v01 exit view for the left-side exit clips
        ER.VIEWS['exit_L'] = ((-lo[0], lo[1], lo[2]), (-tg[0], tg[1], tg[2]), o_, ln)
    AC.use_eevee(sess.B.scene, (res, res), samples=10)
    return _CAM['cam']


def set_t(sess, spec, t):
    f = 1 + t * E.FPS
    sess.B.scene.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
    ang, _ = BE.strap_state(spec, t)
    sess.S.set_angles(ang)


def render_times(sess, key, outdir, times, view, res, label):
    spec = sess.specs[key]
    c = cam(sess, res)
    ER.aim(c, view)
    od = Path(outdir)
    out = (od if od.is_absolute() else HERE / od) / spec['stem']      # Blender resolves bare relative paths elsewhere
    for k, t in enumerate(times):
        set_t(sess, spec, t)
        ER.render_to(sess.B.scene, out / view / ('%s%03d_t%.3f.png' % (label, k, t)))
    print('RENDERED', label, spec['stem'], view, len(times), flush=True)


def prepare_review(sess, key):
    spec = sess.specs[key]
    if spec.get('cycle'):
        sess.B.rig.matrix_world = run_placement(sess)
        bpy.context.view_layer.update()


# ---------------------------------------------------------------------------------------- outputs
def authoring_json(sess, key, N, stats, val):
    spec = sess.specs[key]
    T = spec['T']
    ev = [dict(e, norm=round(e['t'] / T, 4), frame=round(1 + e['t'] * E.FPS, 2)) for e in spec['events']]
    straps = {}
    for n, ks in spec['straps'].items():
        straps[n] = {'angle_keys_deg': [[round(t, 4), a] for t, a in ks],
                     'angle_keys_norm': [[round(t / T, 4), a] for t, a in ks],
                     'note': 'rotation about the strap local +X (Unity same sign), 0 = closed, 120 = open; interpolate smoothly (monotone)'}
    v01 = spec.get('v01', '')
    v01_T = None
    pj = V01 / (v01 + '_authoring.json')
    if v01 and pj.exists():
        v01_T = json.loads(pj.read_text(encoding='utf-8'))['duration_s']
    rep = {
        'clip': spec['stem'], 'action': spec['stem'], 'take': 'Buddy_Rig_Mixamo65|' + spec['stem'],
        'variant_of': v01, 'v01_duration_s': v01_T,
        'duration_vs_v01_pct': round(100.0 * (T / v01_T - 1.0), 1) if v01_T else None,
        'frames': [1, N + 1], 'fps': E.FPS, 'duration_s': round(T, 6), 'loop': spec['loop'],
        'sampling': 'half-frame keys (60 Hz), linear interpolation',
        'start_pose_key': spec['start'], 'end_pose_key': spec['end'],
        'preconditions': spec['pre'], 'straps_after': spec.get('after', {}),
        'strap_animation': straps, 'events': ev, 'next': spec.get('next', []), 'beats': spec.get('beats', []),
        'root_motion': spec.get('root', 'none: rig object at PatientRest, the Hips curves place the body (Apply Root Motion off)'),
        'authoring_stats': stats, 'validation': val,
        'source_patient': str(E.O.PATIENT_BLEND.relative_to(E.ANIM.parents[3])).replace('\\', '/'),
        'pose_keys_file': 'esc_pose_keys_v01.json (Escape_v01)' + (' + esc_pose_keys_v02.json' if spec['end'] in ('RUN0_BC', 'RUN0_BC_L', 'BCRUN') or spec['start'] == 'BCRUN' else ''),
    }
    p = DEST / (spec['stem'] + '_authoring.json')
    assert not p.exists(), 'Refusing overwrite ' + p.name
    p.write_text(json.dumps(rep, indent=2), encoding='utf-8')
    print('JSON', p.name, flush=True)


def write_keys(sess):
    B = sess.B
    out = {'version': 'esc_pose_keys_v02', 'fps': E.FPS, 'rig': E.O.RIG_NAME, 'bones': B.order,
           'note': 'NEW keys of Escape_Panic_v02 only; every other key (LIE, SIT, EDGE_x, RUN0, LAND_x, DOWN_x, ...) is unchanged in Escape_v01/esc_pose_keys_v01.json. Raw pose-bone values (quaternion w,x,y,z; Hips location).',
           'key_notes': {'BCRUN': 'Esc_Run_BellyClutch_Loop_Panic_v02 frame 1, cycle space (in place, faces -Y, floor z = 0)',
                         'RUN0_BC': 'BCRUN at the v01 RUN0 root (PatientRest armature space): end of Esc_HopRun_R_BellyClutch_v02',
                         'RUN0_BC_L': 'BCRUN at the v01 RUN0_L root: end of Esc_HopRun_L_BellyClutch_v02'},
           'run0_root_patientrest_unity': EH.run0_root_unity(sess), 'run0_root_L_patientrest_unity': EH.run0_root_unity(sess, 'L'),
           'keys': {}}
    for k in ('BCRUN', 'RUN0_BC', 'RUN0_BC_L'):
        v = sess.keys[k]
        out['keys'][k] = {n: {'q': [round(x, 8) for x in v[n]['q']], 'loc': [round(x, 8) for x in v[n]['loc']] if v[n]['loc'] else None}
                          for n in B.order}
    p = DEST / 'esc_pose_keys_v02.json'
    assert not p.exists()
    p.write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('KEYS_WRITTEN', p, flush=True)


if __name__ == '__main__':
    sess = session()
    if args.list:
        for k in sess.p2:
            sp = sess.specs[k]
            print('CLIP', k[3:], sp['stem'], sp['T'], sp['start'], '->', sp['end'])
    if args.keys:
        write_keys(sess)
    if args.clip:
        key = resolve(sess, args.clip)
        spec = sess.specs[key]
        act, N, stats = author(sess, key)
        val = {}
        if args.validate:
            if spec.get('cycle'):
                val = validate_cycle(sess, key, act, N)
                val.update(key_steps(sess, act, N))
            else:
                val = BE.validate(sess, key, act, N)
            val.update(extra_checks(sess, key, act, N))
            print('VALIDATION', key, json.dumps(val), flush=True)
        prepare_review(sess, key)
        if args.stills and args.times:
            render_times(sess, key, args.stills, [float(x) for x in args.times.split(',')], args.view or spec['views'][0], args.res, 'x')
        elif args.stills:
            render_times(sess, key, args.stills, spec['shots'], spec['views'][0], args.res, 's')
        if args.strip:
            times = [min(spec['T'], i * args.strip_step / E.FPS) for i in range(int(round(spec['T'] * E.FPS)) // args.strip_step + 1)]
            if times[-1] < spec['T'] - 1e-6:
                times.append(spec['T'])
            render_times(sess, key, args.strip, times, spec['views'][0], args.strip_res, 'f')
        if args.final:
            BE.final(sess, key, act, N, stats)
            if args.validate:
                val.update(BE.fbx_check(sess, key, act, N, DEST / (spec['stem'] + '.fbx')))
                print('FBX', json.dumps({k: v for k, v in val.items() if k.startswith('fbx')}), flush=True)
            authoring_json(sess, key, N, stats, val)
