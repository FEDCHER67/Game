"""Cargo clips, fixes round 2026-10-11: Cargo_Sit_Idle_v05 and SitUp_Cargo_v05.

Same stage, authoring frame and machinery as clips_cargo.py (SitRig, SitParams, neutral, the wall /
floor contact solves), which is imported and NOT changed. Both clips key the frozen cargo sit
contract (Cargo_Sit_Contract_v04.json, raw values) exactly: frame 1 and the duplicated last frame of
Cargo_Sit_Idle_v05, the last frame of SitUp_Cargo_v05. SitUp_Cargo_v05 frame 1 is the raw
GetUp_FromBack_v02 frame-1 (supine) values.

Local frame (see clips_cargo): he sits at the origin facing -Y, left = +X; the wall is the plane
y = +y_wall behind him, the doors are toward local -X (his right). pitch = R(X) (+ forward),
roll = R(Y) (+ tips his left side down), yaw = R(Z) (+ turns to his left).
"""
import math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import acting_core as C
from acting_core import R, QI, Curve, P, clamp, smooth, smoother
import clips_cargo as CC
from clips_cargo import (SitRig, SitParams, neutral, SitCtx, hand_q, lerp, vlerp, sit_contract_values,
                         SIDES, FLOOR_GAP, WALL_GAP)

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def bump(t, a, b):
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a)) ** 2


# ----------------------------------------------------------------------------- Cargo_Sit_Idle_v05
SIT5_T = 4.5


def sit5_channels():
    T = SIT5_T
    ch = {}
    # head yaw (deg, - = to his right, toward the doors): anticipation the other way, SNAP glance
    # with overshoot, held stare with drift, reluctant turn back; double-take (32, hold, 64) and back
    ch['yaw'] = Curve([(0, 0), (0.36, 0, 'flat'), (0.47, 6.0, 'flat'), (0.57, -63), (0.64, -54), (0.76, -58),
                       (1.10, -55), (1.40, -52, 'flat'), (1.62, -14), (1.74, 3.0), (1.88, 0), (2.95, 0, 'flat'),
                       (3.02, -33), (3.08, -30, 'flat'), (3.13, -65), (3.19, -57), (3.36, -59, 'flat'), (3.60, -6),
                       (3.72, 1.5), (3.92, 0), (T, 0)], periodic=True)
    # shoulder jolt on the snap (0..1)
    ch['jolt'] = Curve([(0, 0), (0.50, 0, 'flat'), (0.58, 1.0), (0.70, 0.45), (0.95, 0.3), (1.45, 0.3), (1.7, 0.1),
                        (1.92, 0.15), (2.00, 0.9), (2.10, -0.2), (2.25, 0.0), (3.02, 0.3), (3.13, 1.0), (3.25, 0.5),
                        (3.6, 0.3), (4.05, 0.0), (T, 0)], periodic=True)
    # SHRINK back into the wall (0..1): shoulders up to the ears, head pulled down, pelvis rolls under
    # so the back presses into the wall, knees squeezed together, feet drawn in
    ch['shrink'] = Curve([(0, 0), (0.60, 0, 'flat'), (0.70, 0.70), (0.80, 1.05), (0.90, 0.98), (1.40, 1.0, 'flat'),
                          (1.80, 0.35), (2.15, 0.12), (2.95, 0.12), (3.15, 0.75), (3.40, 0.85), (3.75, 0.3),
                          (4.15, 0.0, 'flat'), (T, 0)], periodic=True)
    # feet drawn in (0..1): a quick drag in on the shrink, slow slide back out while he settles
    ch['tuck'] = Curve([(0, 0), (0.62, 0, 'flat'), (0.78, 1.0, 'flat'), (3.70, 0.92), (4.30, 0.0, 'flat'), (T, 0)],
                       periodic=True)
    # gulp (0..1): chin tuck + head dip; arms squeeze the knees
    ch['gulp'] = Curve([(0, 0), (1.80, 0, 'flat'), (1.90, 0.3), (2.00, 1.0), (2.08, 0.9), (2.20, 0.0), (T, 0)],
                       periodic=True)
    ch['squeeze'] = Curve([(0, 0), (0.62, 0, 'flat'), (0.78, 0.8), (1.45, 0.8), (1.9, 0.6), (2.0, 1.0), (2.25, 0.7),
                           (2.9, 0.5), (3.10, 0.9), (3.6, 1.0), (4.1, 0.2), (T, 0)], periodic=True)
    # three anxious rocks on the butt (deg, + forward); the wall stops the back swings
    ch['rock'] = Curve([(0, 0), (2.10, 0, 'flat'), (2.19, -1.5), (2.37, 12.0), (2.53, -1.5), (2.71, 11.0),
                        (2.86, -1.0), (2.98, 0.0, 'flat'), (T, 0)], periodic=True)
    # sink lower behind the knees (0..1)
    ch['sink'] = Curve([(0, 0), (3.20, 0, 'flat'), (3.55, 1.0), (3.85, 0.85), (4.25, 0.15), (T, 0)], periodic=True)
    # panicky shallow breathing, 9 cycles per loop (2 Hz)
    amp = Curve([(0, 0.6), (0.6, 0.8), (1.4, 1.0), (2.2, 0.6), (3.1, 0.9), (4.0, 0.7), (T, 0.6)], periodic=True)
    ch['breath'] = lambda t: amp(t) * math.sin(2 * math.pi * 9 * t / T)
    # trembling: integer cycles per loop (6.9 to 9.1 Hz), zero at the seam; stronger while staring
    env = Curve([(0, 0.55), (0.5, 0.6), (0.62, 1.0), (1.45, 1.0), (1.8, 0.65), (2.9, 0.65), (3.1, 1.0), (3.6, 0.9),
                 (4.2, 0.55), (T, 0.55)], periodic=True)
    ch['env'] = env
    nz = [C.pnoise(T, 11 + i, cycles=(31, 37, 41)) for i in range(9)]
    ch['trem'] = lambda t, i: env(t) * nz[i](t)
    # overlap: chest follows the head yaw with a lag; the giant head lags the rocks and nods after them
    ch['yaw_lag'] = C.spring_periodic(ch['yaw'], T, 1 / 240, 2.2, 0.55)
    ch['rock_lag'] = C.spring_periodic(ch['rock'], T, 1 / 240, 2.6, 0.35)
    ch['shrink_lag'] = C.spring_periodic(ch['shrink'], T, 1 / 240, 2.4, 0.40)
    return ch


class Sit5Ctx:
    def __init__(self, B):
        self.B = B
        self.S = SitRig(B)
        self.ch = sit5_channels()


TREM = {'spine_roll': 1.3, 'spine_pitch': 1.1, 'neck': 1.4, 'head_pitch': 1.9, 'head_roll': 1.6,
        'shoulder': 2.6, 'hand': 0.0055}


def sit5_pose(ctx, t):
    S, ch = ctx.S, ctx.ch
    yaw, lag = ch['yaw'](t), ch['yaw_lag'](t)
    jolt, shrink, gulp = ch['jolt'](t), ch['shrink'](t), ch['gulp'](t)
    sq, rock, sink, b = ch['squeeze'](t), ch['rock'](t), ch['sink'](t), ch['breath'](t)
    tuck, rl, sl = ch['tuck'](t), ch['rock_lag'](t), ch['shrink_lag'](t)
    tr = [ch['trem'](t, i) for i in range(9)]
    p = neutral(S)
    chest = 0.28 * (yaw + lag)
    p.rock = R(X, rock)
    # pelvis rolls under on the shrink (the lower back presses into the wall)
    p.hips_q = p.hips_q @ R(X, 0.6 * b - 4.0 * shrink)
    J = p.J
    J['Spine'] = (J['Spine'] @ R(X, -1.0 * shrink + 2.0 * sink) @ R(Z, 0.3 * chest)
                  @ R(Y, TREM['spine_roll'] * tr[0] + 3.5 * shrink))
    J['Spine1'] = J['Spine1'] @ R(X, 3.0 * shrink + 3.0 * sink - 0.9 * b + 0.25 * rl) @ R(Z, 0.35 * chest)
    J['Spine2'] = (J['Spine2'] @ R(X, 3.5 * shrink + 2.5 * sink - 1.2 * b + TREM['spine_pitch'] * tr[1] + 0.15 * rl)
                   @ R(Z, 0.35 * chest))
    # shoulders: base shrug + snap jolt + SHRINK (up to the ears) + breath + shiver
    shr = 8.0 * jolt + 24.0 * shrink + 2.5 * b + 4.0 * gulp
    J['LeftShoulder'] = J['LeftShoulder'] @ R(Y, -(shr + TREM['shoulder'] * tr[6]))
    J['RightShoulder'] = J['RightShoulder'] @ R(Y, shr + TREM['shoulder'] * tr[7])
    hy = yaw - chest
    # head pulled down between the shoulders (neck forward, head pitched back to keep watching),
    # the giant head lags the rocks (nods after each one)
    J['Neck'] = (J['Neck'] @ R(X, 13.0 * shrink + 3.0 * sl + 7.0 * gulp + 6.0 * sink + TREM['neck'] * tr[2]
                               + 0.40 * rl) @ R(Z, 0.35 * hy))
    J['Head'] = (J['Head'] @ R(Z, 0.65 * hy)
                 @ R(X, -8.0 * shrink + 9.0 * gulp - 1.0 * sink + TREM['head_pitch'] * tr[3] + 0.50 * rl)
                 @ R(Y, -0.08 * hy - 0.05 * lag + TREM['head_roll'] * tr[4]))
    # knees squeezed together, feet drawn in (a quick drag with a small lift)
    lift = 0.012 * bump(t, 0.60, 0.80)
    for s, sgn in SIDES:
        a0, fq, pole = p.feet[s]
        a1 = (a0[0] - sgn * 0.035 * tuck, a0[1] + 0.065 * tuck, a0[2] + lift)
        pl = (pole[0] * (1 - 0.75 * max(shrink, 0.0)), pole[1], pole[2])
        p.feet[s] = (a1, fq, pl)
    for s, sgn in SIDES:
        h = p.hands[s]
        base = S.shin_grip(s, inward=0.035 + 0.03 * sq)
        k = TREM['hand'] * tr[5 if s == 'Left' else 8] * sgn
        h['pos'] = (lambda f, k=k: (lambda out: f(out) + Vector((k, 0.3 * k, 0.7 * k))))(base)
        h['curl'] = 0.5 + 0.3 * sq
    out = S.pose(p)
    return out, {'wall_lean_deg': S.last_fix[0], 'seat_lift_m': S.last_fix[1]}


def _sit_canonical(ctx, N):
    v = sit_contract_values(ctx)
    return {1.0: v, float(N + 1): v}


def _sit_stats(info):
    return {'max_wall_lean_deg': max(i['wall_lean_deg'] for i in info),
            'max_seat_lift_m': max(i['seat_lift_m'] for i in info)}


SIT5_BEATS = ['0.00-0.47 panicky breathing (9 per loop) and a visible shiver (1.1-2.6 deg spine/neck/head/shoulders, hand jitter 5.5 mm, zero at the seam); 0.36-0.47 anticipation: head 6 deg the other way',
              '0.47-0.64 SNAP glance at the doors (his right, 63 deg with overshoot), shoulders jolt, chest follows on a lagging spring',
              '0.60-0.90 SHRINK: shoulders up to the ears, head pulled down, pelvis rolls under and the back presses into the wall (wall contact solve), knees squeezed together, feet dragged in 6.5 cm',
              '0.90-1.40 frozen stare, shivering hardest', '1.40-1.88 slow reluctant turn back with a small overshoot, shoulders come down',
              '1.80-2.20 GULP: chin tuck, head dip, shoulders up and down, arms squeeze',
              '2.10-2.98 two big anxious rocks on the butt (12 and 11 deg forward; the wall stops the back swings), the giant head lags and nods after each',
              '2.95-3.36 double-take at the doors: 33 deg, a 2-frame hold, SNAP 65 deg with overshoot, hold, shrinks again',
              '3.36-3.72 turns back and sinks lower behind the knees', '3.70-4.50 settles; the feet slide back out into the exact sit contract']


# ----------------------------------------------------------------------------- SitUp_Cargo_v05
SITUP5_T = 3.0
HOLD5 = 0.15                   # exact supine hold for the ragdoll blend (frames 1..5.5)
PUSHES = ((2.17, 2.28), (2.37, 2.49), (2.58, 2.69))   # three heel + palm pushes of the scramble (start, end)


def situp5_channels():
    T = SITUP5_T
    H = HOLD5
    ch = {}
    # body blend lying -> sitting (0..1)
    ch['body'] = Curve([(0, 0), (H, 0, 'flat'), (0.42, 0.10), (0.52, 0.24), (0.70, 0.80), (0.84, 1.0, 'flat'),
                        (T, 1.0, 'flat')])
    # head pitch relative to the blended pose (deg, + = forward): the giant head LAGS back while the
    # torso comes up (chin to the ceiling), then FLOPS forward past the pose (chin on the chest),
    # bounces back up, a smaller second flop, settles
    ch['hp'] = Curve([(0, 0), (0.45, 0, 'flat'), (0.60, -28), (0.74, -52), (0.81, -54, 'flat'), (0.87, 4),
                      (0.91, 38), (0.94, 42, 'flat'), (1.02, -13), (1.09, 20), (1.17, -6), (1.26, 7), (1.37, 0),
                      (T, 0, 'flat')])
    # dazed wobble (circular head roll) after the flop, then a quick "brrr" shake to snap out of it
    ch['daze'] = Curve([(0, 0), (1.06, 0, 'flat'), (1.18, 1.0), (1.34, 0.7), (1.48, 0.0, 'flat'), (T, 0, 'flat')])
    ch['shake_env'] = Curve([(0, 0), (1.40, 0, 'flat'), (1.45, 1.0), (1.70, 0.0, 'flat'), (T, 0, 'flat')])
    # legs: drop and bend right after the hold, feet slide up to the butt
    ch['knees'] = Curve([(0, 0), (H, 0, 'flat'), (0.27, 0.45), (0.42, 0.9), (0.52, 1.0, 'flat'), (T, 1.0, 'flat')])
    # groggy stir: head roll, hand twitch
    ch['stir'] = Curve([(0, 0), (H, 0, 'flat'), (0.26, 1.0), (0.35, 0.55), (0.44, 0.0), (T, 0, 'flat')])
    # hands push on the floor during the sit-up
    ch['push'] = Curve([(0, 0), (0.16, 0, 'flat'), (0.50, 1.0), (0.68, 1.0), (0.98, 0.0, 'flat'), (T, 0, 'flat')])
    # rub the bump (right hand on the right side of the head, small circles), wince
    ch['rub'] = Curve([(0, 0), (1.44, 0, 'flat'), (1.74, 1.0), (1.94, 1.0), (1.99, 0.97, 'flat'), (2.24, 0.0, 'flat'),
                       (T, 0, 'flat')])
    ch['wince'] = Curve([(0, 0), (1.64, 0, 'flat'), (1.74, 1.0), (1.93, 0.8), (2.00, 0.0), (T, 0, 'flat')])
    # realisation: the hand freezes, slow look up, SNAP panic glance at the doors (in front of him)
    ch['look'] = Curve([(0, 0), (1.96, 0, 'flat'), (2.06, 0.55), (2.11, 1.25), (2.19, 1.0), (2.32, 0.55), (2.58, 0.0),
                        (T, 0, 'flat')])
    # scramble: turn 90 deg to his left and scoot to the wall in three heel pushes (fast, then a
    # near-hold while the feet re-plant)
    a0 = PUSHES[0][0] - 0.03
    tk, sk = [(0, 0), (a0, 0, 'flat')], [(0, 0), (a0, 0, 'flat')]
    for i, (a, b) in enumerate(PUSHES):
        last = i == len(PUSHES) - 1
        v1 = (i + 1) / len(PUSHES)
        tk += [(b, 0.985 if last else v1 - 0.035), (b + 0.07, 1.0 if last else v1, 'flat' if last else 'auto')]
        sk += [(b + 0.015, 0.985 if last else v1 - 0.03), (b + 0.08, 1.0 if last else v1, 'flat' if last else 'auto')]
    ch['turn'] = Curve(tk + [(T, 1.0, 'flat')])
    ch['scoot'] = Curve(sk + [(T, 1.0, 'flat')])

    # palms on the floor for the scramble (0..1): slam down with the panic, lift into the hug
    ch['hands'] = Curve([(0, 0), (1.92, 0, 'flat'), (2.22, 1.0, 'flat'), (2.66, 1.0, 'flat'), (2.92, 0.0, 'flat'),
                         (T, 0, 'flat')])
    # curl into the knee hug (0..1) with a squash when the hood bumps the wall
    ch['hug'] = Curve([(0, 0), (2.56, 0, 'flat'), (2.80, 0.75), (2.94, 1.0, 'flat'), (T, 1.0, 'flat')])
    ch['bump'] = Curve([(0, 0), (2.66, 0, 'flat'), (2.72, 1.0), (2.82, -0.35), (2.90, 0.1), (2.97, 0.0, 'flat'),
                        (T, 0, 'flat')])
    return ch


def _body_frame(S, tu, sc):
    """Placement of the sit track: the 90 deg turn to his left and the scoot toward the wall."""
    return Matrix.Translation((S.wx * sc, 0, 0)) @ R(Z, 90 * tu).to_matrix().to_4x4()


EXT = 0.07          # extra leg extension at the end of a heel push (m, along his facing)
STEP_LIFT = 0.025   # foot lift while stepping to the next plant


def _heel_target(S, ch, t, rest, w_rest):
    """World ankle target for the scramble. rest(tt): local rest ankle at time tt; w_rest: world rest
    ankle now. Plant i (held from a_i to b_i) = where the rest foot will be at the end of push i,
    pushed out by EXT along his facing; between plants the foot steps (smooth, lifted)."""
    def plant(i):
        a, b = PUSHES[i]
        Mb = _body_frame(S, ch['turn'](b), ch['scoot'](b))
        return Mb @ (rest(b) + Vector((0, -EXT, 0))) + Vector((0, 0, 0.001))
    pre = 0.12
    a0 = PUSHES[0][0]
    if t < a0 - pre:
        return w_rest
    if t < a0:
        u = smooth((t - (a0 - pre)) / pre)
        return w_rest.lerp(plant(0), u) + Vector((0, 0, STEP_LIFT * bump(t, a0 - pre, a0)))
    for i, (a, b) in enumerate(PUSHES):
        if a <= t <= b:
            return plant(i)
        if i + 1 < len(PUSHES) and b < t < PUSHES[i + 1][0]:
            a2 = PUSHES[i + 1][0]
            u = smooth((t - b) / (a2 - b))
            return plant(i).lerp(plant(i + 1), u) + Vector((0, 0, STEP_LIFT * bump(t, b, a2)))
    b = PUSHES[-1][1]
    post = 0.20
    if t < b + post:
        u = smooth((t - b) / post)
        return plant(len(PUSHES) - 1).lerp(w_rest, u) + Vector((0, 0, 0.6 * STEP_LIFT * bump(t, b, b + post)))
    return w_rest


PALM = (0.27, 0.04)    # palm plant beside the hips in the sit track (|x|, y), local frame


def _palm_target(S, ch, t, sgn):
    """World palm target and finger direction for the scramble: each palm is planted for the whole
    push at the spot beside the hip where the hip is half-way through the push (the right palm
    pushes from his side to behind him, the left one pulls him round); it hops to the next plant."""
    def plant(i):
        a, b = PUSHES[i]
        m = 0.5 * (a + b)
        Mb = _body_frame(S, ch['turn'](m), ch['scoot'](m))
        p = Mb @ Vector((sgn * PALM[0], PALM[1], 0.0))
        p.z = 0.050
        return p, (Mb.to_3x3() @ Vector((0, -1, 0))).normalized()
    n = len(PUSHES)
    if t <= PUSHES[0][1]:
        return plant(0)
    for i in range(n - 1):
        b, a2 = PUSHES[i][1], PUSHES[i + 1][0]
        if t <= b:
            return plant(i)
        if t < a2:
            u = smooth((t - b) / (a2 - b))
            (p0, f0), (p1, f1) = plant(i), plant(i + 1)
            return p0.lerp(p1, u) + Vector((0, 0, 0.05 * bump(t, b, a2))), f0.lerp(f1, u).normalized()
    return plant(n - 1)


class SitUp5Ctx(CC.SitUpCtx):
    def __init__(self, B):
        super().__init__(B)
        self.ch = situp5_channels()


def situp5_pose(ctx, t):
    B, S, ch = ctx.B, ctx.S, ctx.ch
    T = SITUP5_T
    if t <= HOLD5 + 1e-9:
        return {n: m.copy() for n, m in B.supine.items()}, {'phase': 'hold'}
    if t >= T - 1e-9:
        return {n: m.copy() for n, m in ctx.contract.items()}, {'phase': 'contract'}
    wb, hpitch = ch['body'](t), ch['hp'](t)
    kn, stir, push = ch['knees'](t), ch['stir'](t), ch['push'](t)
    daze, se, rub, wince, look = ch['daze'](t), ch['shake_env'](t), ch['rub'](t), ch['wince'](t), ch['look'](t)
    tu, sc, hug, bmp = ch['turn'](t), ch['scoot'](t), ch['hug'](t), ch['bump'](t)
    # ---- sit track in the local frame (at the origin, facing -Y), then placed by M(t)
    p = neutral(S)
    loose = 1 - hug
    p.hips_q = p.hips_q @ R(X, -6 * loose)
    J = p.J
    J['Spine'] = J['Spine'] @ R(X, 6 * loose - 4 * bmp)
    J['Spine1'] = J['Spine1'] @ R(X, 4 * loose - 3 * bmp)
    J['Spine2'] = J['Spine2'] @ R(X, 2 * loose)
    J['LeftShoulder'] = J['LeftShoulder'] @ R(Y, 10 * loose - 6 * bmp)
    J['RightShoulder'] = J['RightShoulder'] @ R(Y, -10 * loose + 6 * bmp)
    J['Neck'] = J['Neck'] @ R(X, -10 * look + 8 * bmp)
    J['Head'] = J['Head'] @ R(X, -8 * look - 5 * bmp)
    th = 90 * tu
    sx = S.wx * sc
    M = _body_frame(S, tu, sc)
    for s, sgn in SIDES:
        a0, fq, pole = p.feet[s]
        rest = lambda tt, a0=a0, sgn=sgn: vlerp((sgn * 0.17, -0.60, a0[2]), a0, ch['hug'](tt))
        # heel pushes: each foot is planted on the floor (world) for the whole push while the butt
        # slides away from it (the legs extend), then steps (lifted) to the next plant
        a = M.inverted() @ _heel_target(S, ch, t, rest, M @ rest(t))
        p.feet[s] = (tuple(a), fq, pole)
    for s, sgn in SIDES:
        h = p.hands[s]
        knee = (lambda side: (lambda out: out[P + side + 'Leg'].translation + Vector((0, -0.04, 0.05))))(s)
        grip = h['pos']
        h['pos'] = (lambda g, k, w: (lambda out: k(out).lerp(g(out), w)))(grip, knee, hug)
        h['curl'] = lerp(0.15, 0.5, hug)
    sit = S._pose(p)
    sit = {n: M @ m for n, m in sit.items()}
    # ---- blend supine -> sit track in basis (local rotation) space (the head too: its lag and
    #      flop are the explicit layer below)
    sv = B.values_from_pose(sit)
    vals = {}
    for n in B.order:
        qa = Quaternion(ctx.sup_vals[n]['q'])
        qb = Quaternion(sv[n]['q'])
        if qa.dot(qb) < 0:
            qb.negate()
        q = qa.slerp(qb, wb)
        loc = None
        if ctx.sup_vals[n]['loc'] is not None:
            loc = tuple(vlerp(ctx.sup_vals[n]['loc'], sv[n]['loc'], wb))
        vals[n] = {'q': tuple(q), 'loc': loc}
    out = B.pose_from_values(vals)
    # ---- procedural head layers (world axes of the posed head)
    face, up, left = CC._head_axes(B, out)
    nk = out[P + 'Neck'].translation.copy()
    # lag back / FLOP forward: 40 % about the neck base, 60 % about the head joint (an arc, not a hinge)
    B.rotate_subtree(out, 'Neck', R(left, 0.4 * hpitch), nk)
    hp = out[P + 'Head'].translation.copy()
    face, up, left = CC._head_axes(B, out)
    B.rotate_subtree(out, 'Head', R(left, 0.6 * hpitch), hp)
    # stir: groggy head roll on the floor
    face, up, left = CC._head_axes(B, out)
    B.rotate_subtree(out, 'Head', R(face, 14 * stir), hp)
    # dazed wobble: the head circles (roll + pitch in quadrature), decaying
    if daze > 0:
        ph = 2 * math.pi * 2.6 * (t - 1.06)
        face, up, left = CC._head_axes(B, out)
        B.rotate_subtree(out, 'Head', R(face, 11 * daze * math.sin(ph)) @ R(left, 7 * daze * math.cos(ph)), hp)
    # "brrr": 2.5 quick decaying shakes (yaw + roll), within the per-key rotation limit
    if se > 0:
        ph = 2 * math.pi * 2.5 * (t - 1.40) / 0.30
        face, up, left = CC._head_axes(B, out)
        B.rotate_subtree(out, 'Head', R(up, 20 * se * math.sin(ph)) @ R(face, 8 * se * math.sin(ph + 0.6)), hp)
    if wince > 0:
        face, up, left = CC._head_axes(B, out)
        B.rotate_subtree(out, 'Head', R(face, -10 * wince) @ R(left, -6 * wince), hp)
    # ---- legs: drop and bend right after the hold; feet slide up to the butt on the floor
    for s, sgn in SIDES:
        tgt_sit = sit[P + s + 'Foot']
        if kn < 1:
            lie = ctx.sup_foot[s].copy()
            k = smooth(kn)
            pos = ctx.sup_ankle[s].lerp(tgt_sit.translation, k)
            pos.z = max(pos.z, tgt_sit.translation.z)
            q = lie.to_quaternion().slerp(tgt_sit.to_quaternion(), k)
            fm = q.to_matrix().to_4x4()
            fm.translation = pos
        else:
            fm = tgt_sit.copy()
        pole_lie = Vector((sgn * 0.1, 0.0, 1.0))
        pole_sit = M.to_3x3() @ Vector(p.feet[s][2])
        pole = pole_lie.lerp(pole_sit, wb).normalized()
        info = S.leg[s] if wb > 0.5 else ctx.leg_sup[s]
        B.solve_chain2(out, info, fm.translation, fm, pole)
    # ---- arms: IK layers blended in rotation space, in order (sit-up palms, bump rub, scramble palms)
    face, up, left = CC._head_axes(B, out)
    hands = ch['hands'](t)
    for s, sgn in SIDES:
        layers = []
        hip = out[P + 'Hips'].translation
        if push > 0:
            fwd = Vector((face.x, face.y, 0)).normalized() if face.xy.length > 1e-3 else Vector((0, -1, 0))
            side = Vector((-fwd.y, fwd.x, 0)) * (-1)
            tp = hip + side * (sgn * 0.27) - fwd * 0.10
            tp.z = 0.045
            layers.append((tp, hand_q(s, fwd, (0, 0, -1)),
                           (side * sgn + Vector((0, 0, -0.3)) - fwd * 0.6).normalized(), smooth(push)))
        if s == 'Right' and rub > 0:
            hpos = out[P + 'Head'].translation
            ang = 2 * math.pi * 4.0 * (t - 1.76)
            right = -left
            tr_ = (hpos + up * 0.24 - face * 0.03 + right * 0.15 +
                   (up * math.cos(ang) + face * math.sin(ang)) * 0.025 * min(1, 2 * rub))
            layers.append((tr_, hand_q(s, up * 0.85 - face * 0.3, -right),
                           (right * 1.0 - up * 0.3 - face * 0.2).normalized(), smooth(rub)))
        if hands > 0:
            # scramble: palms slam down on the floor beside/behind the hips and push with every heel
            # push (planted in the van while the body slides), then hop to the next plant
            tp, fw = _palm_target(S, ch, t, sgn)
            tp = S.soft_reach(out, s, tp)          # never a locked elbow (it would snap open)
            sideW = (M.to_3x3() @ Vector((sgn, 0, 0))).normalized()
            layers.append((tp, hand_q(s, fw, (0, 0, -1)),
                           (sideW + Vector((0, 0, 0.35)) + fw * 0.3).normalized(), smooth(hands)))
        for tgt, q_full, pole, kik in layers:
            ik = dict(out)
            B.solve_chain2(ik, S.arm[s], tgt, B.hand_matrix(s, q_full, tgt), pole)
            B.blend_subtree(out, ik, s + 'Arm', kik)
    # ---- floor fit: the seat rests on the floor (never below), feet re-planted
    pts = B.mesh_points(out)
    dz = 0.0
    low = float(pts[:, 2].min())
    seat = S._butt_low(pts)
    # a hair more clearance while he scrambles (the 120 Hz samples between the 60 Hz keys)
    env = smooth((t - 1.88) / 0.14) * (1.0 - smooth((t - 2.80) / 0.12))
    if wb > 0:
        dz = (FLOOR_GAP + 0.0012 * env - seat) * smooth(min(1, wb * 3))
    dz = max(dz, -low + 0.0002 + 0.0012 * env)
    if abs(dz) > 1e-7:
        Mz = Matrix.Translation((0, 0, dz))
        feet = {s: out[P + s + 'Foot'].copy() for s, _ in SIDES}
        for n in out:
            out[n] = Mz @ out[n]
        if wb > 0.3:
            for s, sgn in SIDES:
                B.solve_chain2(out, S.leg[s], feet[s].translation, feet[s],
                               (M.to_3x3() @ Vector(p.feet[s][2])).normalized())
    # ---- the wall stops the scoot (hood contact)
    pts = B.mesh_points(out)
    exw = (C.WALL_X + 0.0015) - float(pts[:, 0].min())
    if exw > 0:
        Mx = Matrix.Translation((exw, 0, 0))
        for n in out:
            out[n] = Mx @ out[n]
    # fade the residual difference to the contract during the last frames (exact landing)
    wend = smoother((t - 2.86) / 0.14)
    if wend > 0:
        for n in out:
            a, b = out[n], ctx.contract[n]
            qa, qb = a.to_quaternion(), b.to_quaternion()
            m = qa.slerp(qb, wend).to_matrix().to_4x4()
            m.translation = a.translation.lerp(b.translation, wend)
            out[n] = m
    return out, {'dz': dz, 'wall_push': max(0.0, exw), 'min_z': low}


def _situp5_canonical(ctx, N):
    v = sit_contract_values(ctx)
    return {1.0: ctx.B.supine_values, float(N + 1): v}


def _situp5_stats(info):
    return {'max_wall_push_m': max(i.get('wall_push', 0.0) for i in info),
            'min_mesh_z_before_fit_m': min(i.get('min_z', 1.0) for i in info),
            'events': SITUP5_EVENTS}


SITUP5_EVENTS = {'SatUp': {'frame': 27, 'time_s': 0.867, 'fraction': round(0.867 / SITUP5_T, 3)},
                 'Seated_Stable': {'frame': 88, 'time_s': 2.9, 'fraction': round(2.9 / SITUP5_T, 3)}}
SITUP5_BEATS = ['0.00-0.15 exact supine hold (GetUp_FromBack_v02 frame 1, hipsStart 0.307 m), frames 1-5.5, for the ragdoll blend',
                '0.15-0.44 groggy stir: head rolls, the legs drop and bend, feet slide to the butt',
                '0.42-0.84 heavy sit-up pushing on the floor with both palms; the giant head LAGS back (54 deg, chin to the ceiling)',
                '0.81-1.37 the head FLOPS forward past the pose (42 deg, chin on the chest), bounces back up (-13), flops again (20), settles',
                '1.06-1.48 dazed wobble: the head circles, decaying', '1.40-1.70 quick brrr head shake (2.5 shakes) to snap out of it',
                '1.44-1.99 rubs the bump on the right side of his head, wincing',
                '2.00-2.32 the hand freezes, slow look up, SNAP panic glance at the doors',
                '1.92-2.76 scramble: the palms slam down with the panic; he turns 90 deg to his left and scoots 0.36 m to the wall in three heel + palm pushes (2.17, 2.37, 2.58 s), feet and palms planted during each push',
                '2.66-2.90 the hood bumps the wall: squash and rebound',
                '2.56-3.00 curls into the knee hug, landing exactly on the cargo sit contract',
                'events: SatUp frame 27 (0.867 s); Seated/Stable from frame 88 (2.90 s)']


# ----------------------------------------------------------------------------- registry
CLIPS = {
    'Cargo_Sit_Idle_v05': {'T': SIT5_T, 'loop': True, 'stage': 'cargo',
                           'setup': Sit5Ctx, 'pose': sit5_pose, 'canonical': _sit_canonical, 'stats': _sit_stats,
                           'beats': SIT5_BEATS},
    'SitUp_Cargo_v05': {'T': SITUP5_T, 'loop': False, 'stage': 'cargo',
                        'setup': SitUp5Ctx, 'pose': situp5_pose, 'canonical': _situp5_canonical,
                        'stats': _situp5_stats, 'beats': SITUP5_BEATS},
}
