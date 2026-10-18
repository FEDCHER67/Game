"""Esc_HopRun_R_v01: from EDGE_R (sitting on the patient's right pad edge) he slides off, lands,
wobbles, hop-turns 40 deg toward the foot end and accelerates into Escape_Police_v01 Flee_Run_v01.

The run-in (t >= RUN_T0) is the real Flee_Run cycle parameterised by DISTANCE (phase = distance /
3.2 m/s), so the stance foot never slides while the root accelerates; it ends exactly on Flee_Run
frame 1 at the RUN0 root with the authored 3.2 m/s ground speed (seamless hand-off to the in-place
loop on a root that moves at 3.2 m/s * playback speed)."""
import math
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import esc_core as E
from esc_core import ik_keys, look_keys, P, R, QI, X, Y, Z
import acting_core as AC
import op_clips as OC

T_HOP = 1.5
LAND_T = 0.52
RUN_T0 = 0.98            # run-in starts (blend into the cycle 0.98 -> 1.16)
RUN_BLEND = 0.18
RUN_SPEED = 3.2           # Flee_Run authored ground speed (m/s)
V0 = 0.8                  # speed at RUN_T0
YAW_RUN = -50.0           # final facing: (sin yaw, -cos yaw) = toward his right AND the table foot end
FLEE_ACTION = 'Flee_Run_v01'


def V(*a):
    return Vector(a)


def load_flee(B):
    """Append the Flee_Run_v01 action read-only, sample it every half frame, remove it again."""
    with bpy.data.libraries.load(str(E.FLEE_BLEND), link=False) as (src, dst):
        assert FLEE_ACTION in src.actions, src.actions
        dst.actions = [FLEE_ACTION]
    act = dst.actions[0]
    f0, f1 = act.frame_range
    samples = []
    f = f0
    while f <= f1 + 1e-9:
        samples.append(AC.read_values(act, f, B.order))
        f += 0.5
    bpy.data.actions.remove(act)
    Tc = (f1 - f0) / E.FPS
    return {'samples': samples, 'Tc': Tc, 'f0': f0, 'f1': f1}


def flee_vals(flee, phase):
    """Raw values of the cycle at cycle time `phase` (s), linear between half-frame samples."""
    Tc = flee['Tc']
    ph = phase % Tc
    x = ph * E.FPS * 2
    i = int(math.floor(x))
    u = x - i
    S = flee['samples']
    n = len(S) - 1          # last sample == first (loop)
    a, b = S[i % n], S[(i + 1) % n if (i + 1) < n else n]
    return a, b, u


def flee_pose(B, flee, phase):
    a, b, u = flee_vals(flee, phase)
    return OC.pose_from_vals(B, OC.lerp_vals(B, a, b, u))


def speed(t):
    if t <= RUN_T0:
        return V0
    u = min(1.0, (t - RUN_T0) / (T_HOP - RUN_T0))
    return V0 + (RUN_SPEED - V0) * (1 - (1 - u) ** 2)        # ease-out, reaches 3.2 at the end


def dist(t):
    """Distance covered since RUN_T0 (numeric integral of speed)."""
    if t <= RUN_T0:
        return 0.0
    n = 200
    h = (t - RUN_T0) / n
    return sum(0.5 * (speed(RUN_T0 + i * h) + speed(RUN_T0 + (i + 1) * h)) * h for i in range(n))


def run_dir():
    a = math.radians(YAW_RUN)
    return Vector((math.sin(a), -math.cos(a), 0.0))


def foot_bottom(ctx):
    """Bind-pose height of the ankle joint above the lowest sole vertex."""
    B = ctx.B
    reg = B.region
    vv = B.sk_v
    m = np.array([r == 'leg_Left' for r in reg])
    low = float(vv[m][:, 2].min())
    return B.rest[P + 'LeftFoot'].translation.z - low


def hop_keys(lib):
    ctx = lib.ctx
    EDGE = lib.EDGE()
    ah = foot_bottom(ctx) + 0.0015            # ankle height above the floor for a planted sole
    fz = E.FLOOR_Z + ah
    # landing spot (facing -X; his left is -Y)
    LX, LY = -0.62, -0.30

    def feet(yaw, cx, cy, spread=0.115, w=1.0):
        a = math.radians(yaw)
        fwd = Vector((math.sin(a), -math.cos(a), 0))
        left = Vector((0, 0, 1)).cross(fwd)
        d = {}
        for t, sg in (('L', 1), ('R', -1)):
            p = Vector((cx, cy, fz)) + left * sg * spread
            d.update({'fik_' + t: w, 'ax_' + t: p.x, 'ay_' + t: p.y, 'az_' + t: p.z,
                      'ox_' + t: fwd.x, 'oy_' + t: fwd.y, 'oz_' + t: 0.0})
        return d
    K = [(0.0, EDGE)]
    K.append((0.0, feet(-90, LX, LY, w=0.0)))
    K.append((0.10, {'neck': 14, 'hnod': 10, 'sh_L': 6, 'sh_R': 6, 'cu_L': -0.15, 'cu_R': -0.15}))
    K.append((0.20, {'neck': 18, 'hnod': 12, 'sh_L': 10, 'sh_R': 10, 'crunch': 9}))          # gulp
    K.append((0.30, {'pitch': 102, 'crunch': 12, 'neck': 6, 'hnod': 2, 'px': -0.22, 'pz': 0.0, 'sh_L': 0, 'sh_R': 0,
                     'fl_L': 70, 'fl_R': 70, 'kn_L': 70, 'kn_R': 72, 'fo_L': 14, 'fo_R': 14,
                     'afl_L': 60, 'afl_R': 60, 'aab_L': 35, 'aab_R': 35, 'el_L': 35, 'el_R': 35,
                     **lib.plant('L', -0.22, -0.30, -90, fwd=0.10), **lib.plant('R', -0.22, -0.30, -90, fwd=0.10)}))
    # slides off the edge: palms push (they stay planted), then the hands come off and swing forward
    K.append((0.34, {'ik_L': 1.0, 'ik_R': 1.0, 'seat': 1.0, 'px': -0.26, 'pz': -0.002, 'pitch': 101.5}))
    K.append((0.39, {'ik_L': 0.0, 'ik_R': 0.0, 'cu_L': 0.0, 'cu_R': 0.0, 'px': -0.36, 'pz': -0.008, 'seat': 0.3, 'pitch': 100.5}))
    K.append((0.41, {'pitch': 100, 'px': -0.40, 'pz': -0.01, 'seat': 0.0, 'fl_L': 40, 'fl_R': 42, 'kn_L': 40, 'kn_R': 44,
                     'fo_L': 20, 'fo_R': 20, 'afl_L': 55, 'afl_R': 55, 'aab_L': 35, 'aab_R': 35, 'el_L': 30, 'el_R': 30}))
    K.append((0.44, {'afl_L': 60, 'afl_R': 60, 'aab_L': 40, 'aab_R': 40, 'px': -0.465, 'pz': 0.012}))
    # the soles touch down: from here the lowest point rests on the floor (floor solve)
    K.append((0.47, {'pz': 0.03, 'px': -0.52, 'fl_L': 30, 'fl_R': 30, 'kn_L': 42, 'kn_R': 44, 'fo_L': 6, 'fo_R': 6,
                     'pitch': 98, 'floor': 1.0, **feet(-90, LX, LY, w=0.0)}))
    # LAND (both feet planted), squash, arms fly up
    K.append((LAND_T, {**feet(-90, LX, LY, w=1.0), 'px': LX + 0.01, 'py': LY, 'pz': -0.04, 'pitch': 104, 'crunch': 14,
                       'neck': -6, 'hnod': -4, 'afl_L': 80, 'afl_R': 88, 'aab_L': 55, 'aab_R': 50, 'el_L': 40, 'el_R': 35,
                       'cu_L': -0.3, 'cu_R': -0.3}))
    K.append((0.60, {'pz': -0.135, 'pitch': 110, 'crunch': 18, 'neck': -12, 'hnod': -8, 'afl_L': 95, 'afl_R': 90,
                     'aab_L': 70, 'aab_R': 75}))
    # dizzy wobble (anaesthesia legs): hips sway, head circles, windmill arms
    K.append((0.70, {'pz': -0.09, 'pitch': 99, 'roll': 7, 'py': LY + 0.03, 'crunch': 8, 'hyaw': 18, 'htilt': 8, 'neck': -4,
                     'afl_L': 60, 'afl_R': 100, 'aab_L': 80, 'aab_R': 60, 'el_L': 60, 'el_R': 20}))
    K.append((0.80, {'pz': -0.07, 'roll': -6, 'py': LY - 0.03, 'hyaw': -16, 'htilt': -8, 'afl_L': 100, 'afl_R': 55,
                     'aab_L': 60, 'aab_R': 80}))
    # hop-turn 40 deg toward the foot end (his left): crouch, take off, tuck, land into the run
    K.append((0.86, {'pz': -0.12, 'roll': 0, 'py': LY, 'pitch': 106, 'crunch': 12, 'hyaw': 0, 'htilt': 0, 'neck': -10,
                     'afl_L': 40, 'afl_R': 40, 'aab_L': 20, 'aab_R': 20, 'el_L': 50, 'el_R': 50, 'floor': 1.0}))
    K.append((0.88, {'fik_L': 1.0, 'fik_R': 1.0, 'floor': 1.0, 'pz': -0.08}))
    K.append((0.90, {'fik_L': 0.4, 'fik_R': 0.4, 'pz': 0.02, 'pitch': 100}))
    K.append((0.93, {'fik_L': 0.0, 'fik_R': 0.0, 'floor': 0.0, 'pz': 0.12, 'yaw': -72, 'px': LX - 0.04, 'py': LY - 0.02,
                      'pitch': 98, 'fl_L': 46, 'fl_R': 30, 'kn_L': 76, 'kn_R': 56, 'fo_L': 16, 'fo_R': 14,
                      'afl_L': 85, 'afl_R': 90, 'aab_L': 45, 'aab_R': 45, 'el_L': 30, 'el_R': 30, 'neck': -16, 'hnod': -10}))
    K.append((RUN_T0, {'yaw': YAW_RUN, 'pz': 0.03, 'pitch': 100, 'px': LX - 0.08, 'py': LY - 0.05, 'fl_L': 42, 'fl_R': 22,
                       'kn_L': 64, 'kn_R': 38, 'fo_L': 14, 'fo_R': 8, 'afl_L': 95, 'afl_R': 100, 'aab_L': 35, 'aab_R': 35,
                       'floor': 1.0}))
    K.append((T_HOP, {}))
    return K


def hop_run(lib):
    K = hop_keys(lib)
    return dict(stem='Esc_HopRun_R_v01', T=T_HOP, loop=False, start='EDGE_R', end='RUN0',
                pre={'closed': [], 'open': list(E.LIMB_STRAPS), 'any': []},
                closed0=[], straps={}, keys=K, pose_fn=hop_pose,
                events=[{'name': 'Land', 't': LAND_T}, {'name': 'RunStart', 't': RUN_T0},
                        {'name': 'HandOffToRun', 't': T_HOP, 'note': 'end pose = Flee_Run_v01 frame 1 at RUN0'}],
                after={}, next=['Flee_Run_v01 (loop) on the free NPC root placed at RUN0, moving 3.2 m/s along its facing'],
                views=('exit',), shots=(0.0, 0.30, 0.44, 0.60, 0.80, 0.93, 1.20, 1.5),
                root='hips leave the table (PatientRest-local); final hand-off root RUN0 (see esc_pose_keys_v01.json run0_root_patientrest_unity); speed at the end 3.2 m/s along the facing',
                beats=['0.00 EDGE_R', '0.10-0.20 looks down, gulp', '0.30-0.47 leans, palms push, slides off the edge',
                       '0.52 LAND (both feet), squash, arms fly up', '0.70-0.80 dizzy wobble (knees knock, head circles)',
                       '0.86-0.98 hop-turn 40 deg toward the foot end', '0.98-1.50 accelerates 0.8 -> 3.2 m/s into Flee_Run',
                       '1.50 = Flee_Run_v01 frame 1 at RUN0'])


def run_root(sess, t):
    """Cycle root (armature space) at time t during the run-in."""
    d = run_dir()
    P0 = sess.run_p0
    s = dist(t)
    pos = P0 + d * s
    return Matrix.Translation((pos.x, pos.y, E.FLOOR_Z)) @ Matrix.Rotation(math.radians(YAW_RUN), 4, 'Z')


def run_phase(t):
    return -(dist(T_HOP) - dist(t)) / RUN_SPEED


def setup_run(sess):
    if getattr(sess, 'run_p0', None) is not None:
        return
    spec = sess.specs['HopRun'] if hasattr(sess, 'specs') and 'HopRun' in sess.specs else None
    curves, _ = E.build_curves(hop_keys(sess.lib), sess.ctx)
    c = {k: cv(RUN_T0) for k, cv in curves.items()}
    hip = sess.ctx.h0 + Vector((c['px'], c['py'], c['pz']))
    # cycle hips at RUN_T0 phase, relative to the cycle root: put the cycle root so its hips sit over ours
    ph = run_phase(RUN_T0)
    fp = flee_pose(sess.B, sess.flee, ph)
    hl = fp[P + 'Hips'].translation
    Rz = Matrix.Rotation(math.radians(YAW_RUN), 3, 'Z')
    off = Rz @ Vector((hl.x, hl.y, 0.0))
    sess.run_p0 = Vector((hip.x - off.x, hip.y - off.y, 0.0))


def run0_pose(sess):
    setup_run(sess)
    Rr = run_root(sess, T_HOP)
    fp = OC.pose_from_vals(sess.B, sess.flee['samples'][0])
    return {k: Rr @ v for k, v in fp.items()}


def run0_root_unity(sess):
    setup_run(sess)
    Rr = run_root(sess, T_HOP)
    p = Rr.translation
    return {'position': [round(-p.x, 4), round(p.z, 4), round(-p.y, 4)],
            'yaw_deg_about_up': round(-YAW_RUN, 2),
            'facing_unity': [round(-run_dir().x, 4), 0.0, round(-run_dir().y, 4)],
            'note': 'PatientRest-local Unity transform of the floor root that Flee_Run_v01 frame 1 expects (position (-x, z, -y) of armature space; rotation = -yaw about Unity +Y, sign flips with the handedness). Equivalently table-local: PatientRest @ this.',
            'patientrest_armature': {'position': [round(p.x, 4), round(p.y, 4), round(p.z, 4)], 'yaw_deg_about_z': YAW_RUN},
            'speed_mps_at_end': RUN_SPEED}


def blend_full(B, a, b, w):
    """Blend two full poses: root bone translation lerp + rotation slerp, children by local slerp."""
    if w <= 0:
        return a
    if w >= 1:
        return {k: v.copy() for k, v in b.items()}
    out = {}
    for n in B.order:
        p = B.parent[n]
        if p is None:
            ta, tb = a[n].translation, b[n].translation
            qa, qb = a[n].to_quaternion(), b[n].to_quaternion()
            if qa.dot(qb) < 0:
                qb.negate()
            m = qa.slerp(qb, w).to_matrix().to_4x4()
            m.translation = ta.lerp(tb, w)
            out[n] = m
        else:
            la = a[p].inverted() @ a[n]
            lb = b[p].inverted() @ b[n]
            qa, qb = la.to_quaternion(), lb.to_quaternion()
            if qa.dot(qb) < 0:
                qb.negate()
            m = qa.slerp(qb, w).to_matrix().to_4x4()
            m.translation = la.translation.lerp(lb.translation, w)
            out[n] = out[p] @ m
    return out


def hop_pose(sess, spec, t, c, closed):
    setup_run(sess)
    ctx = sess.ctx
    if t < RUN_T0 + RUN_BLEND:
        out, cc, info = ctx.solve(c, closed)
    if t >= RUN_T0:
        Rr = run_root(sess, t)
        fp = flee_pose(sess.B, sess.flee, run_phase(t))
        cyc = {k: Rr @ v for k, v in fp.items()}
        u = min(1.0, (t - RUN_T0) / RUN_BLEND)
        w = u * u * (3 - 2 * u)
        if w >= 1.0:
            return cyc, {'run_w': 1.0, 'dist': dist(t)}
        out = blend_full(sess.B, out, cyc, w)
        zmin = float(ctx.world_pts(out)[:, 2].min())
        if zmin < 0.001:                       # the blend may dip a sole under the floor: lift rigidly
            M = Matrix.Translation((0, 0, 0.001 - zmin))
            out = {k: M @ v for k, v in out.items()}
        return out, {'run_w': w, 'dist': dist(t)}
    return out, info
