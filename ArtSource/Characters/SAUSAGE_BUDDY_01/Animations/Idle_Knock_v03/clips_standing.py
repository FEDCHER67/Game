"""Standing clips: Idle_Stand_v03 (default idle) and Idle_Bored_v03 (fidget idle).

Both loop on the original SAUSAGE_BUDDY_A_v04 'Idle' frame-1 pose: frame 1 and the duplicated
last frame are keyed with the exact raw Idle values; every channel below is periodic and zero at
the seam, so the motion also flows through the loop point.
Feet stay planted on their exact Idle frame-1 matrices (zero sliding by construction); the
pelvis height is solved so the support leg never over-extends.
Character frame: faces -Y, left = +X. Rotation helpers: pitch = R(X) (+ leans/nods forward),
roll = R(Y) (+ tips the character's left side down), yaw = R(Z) (+ turns to his left).
"""
import math
from mathutils import Vector, Matrix, Quaternion
import acting_core as C
from acting_core import R, QI, Curve, P, smooth

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


class StandRig:
    """Shared standing machinery on top of the Idle frame-1 base pose."""

    def __init__(self, B):
        self.B = B
        self.base = B.idle
        self.leg = {s: B.chain_info(self.base, 'leg', s, (0, -1, 0)) for s in ('Left', 'Right')}
        self.arm = {s: B.chain_info(self.base, 'arm', s, (0, 1, 0)) for s in ('Left', 'Right')}
        self.L = self.leg['Left']['l1'] + self.leg['Left']['l2']
        self.ankle = {s: self.base[P + s + 'Foot'].translation.copy() for s in ('Left', 'Right')}

    def body(self, hip_xy, hips_q, joints, support=1.0, drop=0.0, knee_in=(0.0, 0.0)):
        """FK the whole body with planted feet.
        hip_xy: (x, y) pelvis offset; hips_q: pelvis rotation about the hips joint;
        joints: FK deltas for spine/neck/head/shoulders/arms/hands (short names);
        support: target hip-ankle distance ratio of the most extended leg (1 = straight);
        drop: extra pelvis drop (m, >= 0) on top of the support solve;
        knee_in: inward pole component for (Left, Right) knees."""
        B = self.B
        q = dict(joints)
        q['Hips'] = hips_q
        root = Matrix.Translation((hip_xy[0], hip_xy[1], 0.0))
        out, D = B.fk(self.base, q, root)
        # solve pelvis height: most extended leg reaches support * L
        dz = 1e9
        for s in ('Left', 'Right'):
            v = out[P + s + 'UpLeg'].translation - self.ankle[s]
            r = support * self.L
            h2 = r * r - v.x * v.x - v.y * v.y
            dz = min(dz, math.sqrt(max(h2, 0.0)) - v.z)
        dz -= drop
        out, D = B.fk(self.base, q, Matrix.Translation((hip_xy[0], hip_xy[1], dz)))
        over = 0.0
        hip_yaw = hips_q @ Vector((0, -1, 0))
        for i, (s, sgn) in enumerate((('Left', 1), ('Right', -1))):
            pole = Vector((hip_yaw.x * 0.35 - sgn * knee_in[i], -1.0, 0.0)).normalized()
            over = max(over, B.solve_chain(out, self.leg[s], self.ankle[s], self.base[P + s + 'Foot'], pole))
        return out, D, dz, over

    def arm_ik2(self, out, side, target, hand_q_world, pole, k=1.0):
        """Flip-free arm IK blended with the FK arm by k (no pop when the IK switches on/off)."""
        if not hasattr(self, 'arm2'):
            self.arm2 = {s: self.B.chain_info2(self.base, 'arm', s, (0, 1, 0)) for s in ('Left', 'Right')}
        ik = dict(out)
        self.B.solve_chain2(ik, self.arm2[side], target, self.B.hand_matrix(side, hand_q_world, target), pole)
        self.B.blend_subtree(out, ik, side + 'Arm', k)

    def arm_ik(self, out, side, target, hand_q_world, pole):
        return self.B.solve_chain(out, self.arm[side], target,
                                  self.B.hand_matrix(side, hand_q_world, target), pole)


# ----------------------------------------------------------------------------- Idle_Stand_v03
STAND_T = 4.0


def stand_channels():
    T = STAND_T
    ch = {}
    # two breaths, the second a touch deeper; holds at the bottom of each exhale
    ch['breath'] = Curve([(0, 0), (0.80, 1.0), (1.95, 0.02), (2.95, 1.18), (T, 0)], periodic=True)
    # weight onto the LEFT leg with an overshoot and settle, drifting hold, then home with a
    # small counter-swing to the other side before the seam
    ch['weight'] = Curve([(0, 0), (0.28, 0.05), (0.92, 1.07), (1.22, 0.96), (1.55, 1.0),
                          (2.30, 0.93), (3.12, 0.05), (3.45, -0.05), (T, 0)], periodic=True)
    # knees unlock a little before the shift (anticipation dip) and while shifted
    # knees stay locked (exactly straight, as in Idle frame 1) for 0.45 s around the seam
    ch['soft'] = Curve([(0, 0), (0.15, 0, 'flat'), (0.45, 0.55), (0.85, 0.85), (1.6, 0.75), (2.5, 0.8), (3.3, 0.3),
                        (3.7, 0, 'flat'), (T, 0)], periodic=True)
    # head gaze: drifts to his right and a little down (spacing out), blink-like dip + snap home
    ch['yaw'] = Curve([(0, 0), (0.45, 0.6), (1.35, -7.5), (2.18, -10.0), (2.40, -3.0), (2.75, 0.8),
                       (3.3, 0.0), (T, 0)], periodic=True)
    ch['nod'] = Curve([(0, 0), (0.5, -0.6), (1.4, 2.4), (2.18, 3.4), (2.26, 6.6), (2.40, -2.2),
                       (2.62, 0.9), (2.9, -0.3), (3.4, 0.2), (T, 0)], periodic=True)
    ch['tilt'] = Curve([(0, 0), (0.9, 2.2), (2.2, 3.0), (2.45, -0.8), (3.0, 0.4), (T, 0)], periodic=True)
    # relaxed fingers slowly curl a little and open again
    ch['fingers'] = Curve([(0, 0), (1.3, 0.16), (2.6, 0.10), (3.4, 0.03), (T, 0)], periodic=True)
    # overlap: chest and arms lag the weight transfer (periodic damped spring, zero at seam)
    # soft-zero transfer: the base legs are fully straight, so any leg shortening near the seam
    # bends the knee like sqrt(shortening). w^3/(w^2+e^2) vanishes to 6th order at the seam, so the
    # knees lock/unlock smoothly instead of popping through straight (review 1 defect).
    raw = ch['weight']
    ch['weight'] = w = lambda t, e=0.12: raw(t) ** 3 / (raw(t) ** 2 + e * e) * (1 + e * e)
    ch['chest_lag'] = C.spring_periodic(w, T, 1 / 240, 1.6, 0.45)
    ch['arm_lag'] = C.spring_periodic(w, T, 1 / 240, 1.3, 0.50)
    ch['hand_lag'] = C.spring_periodic(lambda t: w(t) + ch['arm_lag'](t), T, 1 / 240, 1.6, 0.50)
    return ch


def stand_pose(S, t, ch):
    b = ch['breath'](t)
    w = ch['weight'](t)
    soft = ch['soft'](t)
    cl = ch['chest_lag'](t)
    al = ch['arm_lag'](t)
    hl = ch['hand_lag'](t)
    yaw, nod, tilt = ch['yaw'](t), ch['nod'](t), ch['tilt'](t)
    J = {}
    # pelvis: shift left, right side sags (contrapposto), a hint of yaw toward the support leg
    hips_q = R(Y, -3.6 * w) @ R(Z, 2.0 * w)
    # lag < 0 while the pelvis accelerates left -> chest stays behind (tilts toward -X)
    J['Spine'] = R(Y, 1.8 * w + 2.5 * cl) @ R(X, -0.25 * b)
    J['Spine1'] = R(Y, 1.4 * w + 1.5 * cl) @ R(X, -1.5 * b) @ R(Z, -0.8 * w)
    J['Spine2'] = R(Y, 0.6 * w) @ R(X, -1.3 * b)
    J['Neck'] = R(X, 1.2 * b + 0.35 * nod) @ R(Z, 0.35 * yaw)
    J['Head'] = R(Z, 0.65 * yaw) @ R(X, 0.65 * nod) @ R(Y, -1.1 * w + 1.4 * cl + tilt)
    # breathing lifts the shoulders (clavicles) ~1.3 cm and opens the arms a touch
    J['LeftShoulder'] = R(Y, -5.5 * b)
    J['RightShoulder'] = R(Y, 5.5 * b)
    # pendulum arms: lag the sideways body motion, then catch up with a small overshoot
    swing = -5.5 * al
    # R(Y, +) swings a hanging arm's hand toward -X: abduction is - for Left, + for Right
    # the shrug rotates the clavicle about its inner end; counter-rotate so the arm is lifted,
    # not swung outward, then add the small breathing abduction
    J['LeftArm'] = R(Y, swing + 5.5 * b - 1.6 * b) @ R(X, 1.2 * w)
    J['RightArm'] = R(Y, swing - 5.5 * b + 1.6 * b) @ R(X, -1.0 * w)
    J['LeftForeArm'] = R(Y, -3.5 * hl)
    J['RightForeArm'] = R(Y, -3.5 * hl)
    J['LeftHand'] = R(Y, -4.5 * hl)
    J['RightHand'] = R(Y, -4.5 * hl)
    out, D, dz, over = S.body((0.041 * w, 0.0), hips_q, J,
                              support=1.0 - 0.0014 * soft * soft, drop=0.004 * soft * soft,
                              knee_in=(0.06 * max(0, -w), 0.18 * max(0, w)))
    f = ch['fingers'](t)
    S.B.curl(out, 'Left', f, thumb=0.5 * f)
    S.B.curl(out, 'Right', f * 0.8, thumb=0.4 * f)
    return out, {'dz': dz, 'over': over}


# ----------------------------------------------------------------------------- Idle_Bored_v03
BORED_T = 6.0


def _hand_q(side, point, palm):
    """World rotation applied to the rest hand: points it along `point`, palm facing `palm`
    (rest T-pose: Left hand points +X, Right -X, palms -Z)."""
    p0 = Vector((1, 0, 0)) if side == 'Left' else Vector((-1, 0, 0))
    n0 = Vector((0, 0, -1))
    p = Vector(point).normalized()
    n = Vector(palm)
    n = (n - p * n.dot(p)).normalized()
    A = Matrix((p0, n0, p0.cross(n0))).transposed()
    Bm = Matrix((p, n, p.cross(n))).transposed()
    return (Bm @ A.transposed()).to_quaternion()


def bored_channels():
    T = BORED_T
    ch = {}
    # "anybody coming?": look right (fast in, ease out), drift; sweep left dipping mid-arc; hold
    ch['yaw'] = Curve([(0, 0), (0.25, 0, 'flat'), (0.40, -36), (0.47, -42), (0.58, -40), (0.85, -35, 'flat'),
                       (1.02, -2), (1.14, 40), (1.20, 46), (1.28, 44, 'flat'), (1.45, 30), (1.60, 4), (1.75, 0),
                       (2.40, 0, 'flat'), (3.70, 0, 'flat'), (4.0, -4), (5.2, -6), (5.6, 0), (T, 0)], periodic=True)
    ch['dip'] = Curve([(0, 0), (0.85, 0, 'flat'), (0.98, 6.0), (1.10, 0.0, 'flat'), (T, 0)], periodic=True)
    # watch check (0..1): the left forearm SNAPS up, holds, drops into the sigh
    ch['watch'] = Curve([(0, 0), (1.30, 0, 'flat'), (1.45, 1.05), (1.51, 1.0, 'flat'), (2.38, 1.0, 'flat'),
                         (2.66, 0.0, 'flat'), (T, 0)], periodic=True)
    # head look at the watch: down, hold, double take (pull back, then lean in), shake, look away
    ch['look'] = Curve([(0, 0), (1.36, 0, 'flat'), (1.50, 24), (1.66, 22, 'flat'), (1.73, 12), (1.80, 30),
                        (2.12, 28, 'flat'), (2.42, 0), (T, 0)], periodic=True)
    ch['take'] = Curve([(0, 0), (1.66, 0, 'flat'), (1.73, -1.0), (1.80, 1.0), (1.95, 0.8), (2.12, 0.0), (T, 0)],
                       periodic=True)
    # two quick wrist shakes ("is it broken?")
    ch['shake'] = lambda t: (math.sin(2 * math.pi * 7.5 * (t - 1.95)) * smooth_bump(t, 1.95, 2.22))
    # the BIG SIGH: inhale (shrug + head back), hold, hard exhale (slump, knees unlock, hip pops right)
    ch['inhale'] = Curve([(0, 0), (2.40, 0, 'flat'), (2.92, 1.0), (3.12, 1.04, 'flat'), (3.28, -0.25),
                          (3.45, -0.32), (3.70, -0.2), (4.6, -0.12), (5.3, -0.05), (5.6, 0.0, 'flat'), (T, 0)],
                         periodic=True)
    ch['slump'] = Curve([(0, 0), (3.10, 0, 'flat'), (3.30, 1.0), (3.42, 0.88), (3.6, 0.95), (4.9, 0.75),
                         (5.45, 0.0, 'flat'), (T, 0)], periodic=True)
    # weight (+ = onto the left leg): hip pops to his RIGHT on the exhale, back home at the end
    ch['weight'] = Curve([(0, 0), (0.25, 0, 'flat'), (0.9, 0.12), (1.6, 0.0), (3.12, 0.0, 'flat'), (3.32, -1.08),
                          (3.48, -0.95), (4.8, -0.9), (5.35, -0.05), (5.6, 0, 'flat'), (T, 0)], periodic=True)
    ch['soft'] = Curve([(0, 0), (0.30, 0, 'flat'), (0.8, 0.3), (2.6, 0.3), (3.30, 1.0), (4.8, 0.85), (5.45, 0.1),
                        (5.65, 0, 'flat'), (T, 0)], periodic=True)
    # lazy scratch of the back of the head with the right hand (0..1)
    ch['scratch'] = Curve([(0, 0), (3.66, 0, 'flat'), (4.00, 1.0), (4.92, 1.0, 'flat'), (5.24, 0.0, 'flat'), (T, 0)],
                          periodic=True)
    raw = ch['weight']
    ch['weight'] = w = lambda t, e=0.12: raw(t) ** 3 / (raw(t) ** 2 + e * e) * (1 + e * e)
    drop = ch['inhale']
    ch['arm_lag'] = C.spring_periodic(lambda t: -drop(t) + 0.6 * w(t), T, 1 / 240, 1.5, 0.30)
    ch['head_lag'] = C.spring_periodic(lambda t: ch['slump'](t) - drop(t), T, 1 / 240, 2.2, 0.35)
    return ch


def smooth_bump(t, a, b):
    if t <= a or t >= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a)) ** 2


def bored_pose(S, t, ch):
    B = S.B
    yaw, dip, wat, look, take = ch['yaw'](t), ch['dip'](t), ch['watch'](t), ch['look'](t), ch['take'](t)
    shk, inh, sl = ch['shake'](t), ch['inhale'](t), ch['slump'](t)
    w, soft, scr = ch['weight'](t), ch['soft'](t), ch['scratch'](t)
    al, hl = ch['arm_lag'](t), ch['head_lag'](t)
    J = {}
    hips_q = R(Y, -4.8 * w) @ R(Z, 2.0 * w)
    J['Spine'] = R(Y, 2.4 * w) @ R(X, 2.5 * sl - 1.5 * inh) @ R(Z, 0.10 * yaw)
    J['Spine1'] = R(Y, 1.4 * w) @ R(X, 4.0 * sl - 4.0 * inh) @ R(Z, 0.15 * yaw)
    J['Spine2'] = R(Y, 0.6 * w) @ R(X, 4.5 * sl - 3.5 * inh) @ R(Z, 0.15 * yaw)
    J['Neck'] = R(Z, 0.25 * yaw) @ R(X, 0.35 * look + 0.4 * dip + 4.0 * sl - 5.0 * inh + 3.0 * hl)
    J['Head'] = (R(Z, 0.35 * yaw) @ R(X, 0.65 * look + 0.6 * dip + 4.0 * take + 4.0 * sl - 13.0 * inh + 5.0 * hl)
                 @ R(Y, -1.1 * w - 9.0 * scr + 0.06 * yaw * (1 if yaw < 0 else 0.5)))
    shr = 24.0 * max(inh, 0) + 8.0 * min(inh, 0)
    J['LeftShoulder'] = R(Y, -shr)
    J['RightShoulder'] = R(Y, shr)
    # counter-rotate the arms so the shrug lifts them instead of swinging them out (gotcha 2)
    swing = 5.0 * al
    J['LeftArm'] = R(Y, 0.9 * shr + swing) @ R(X, 3.0 * al)
    J['RightArm'] = R(Y, -0.9 * shr + swing) @ R(X, 3.0 * al)
    J['LeftForeArm'] = R(Y, -2.5 * al)
    J['RightForeArm'] = R(Y, -2.5 * al)
    out, D, dz, over = S.body((0.052 * w, 0.0), hips_q, J, support=1.0 - 0.0016 * soft * soft,
                              drop=0.030 * sl * sl + 0.004 * soft * soft,
                              knee_in=(0.06 * max(0, -w) + 0.10 * sl, 0.18 * max(0, w)))
    # ---- watch check: left wrist at (0.05, -0.25, 1.05), forearm horizontal, watch face up
    if wat > 1e-6:
        side = 'Left'
        tgt = Vector((0.05, -0.25, 1.05)) + Vector((0.012 * shk, -0.004 * shk, 0.018 * shk))
        k = smooth(min(wat, 1.0))
        tg = tgt + Vector((0, 0, 0.02 * max(0.0, wat - 1.0)))
        q1 = _hand_q(side, (-0.85, -0.45, 0.05), (0.15, 0.0, -1.0))
        S.arm_ik2(out, side, tg, q1, Vector((1.0, 0.25, -0.45)).normalized(), k)
    # ---- lazy scratch: right hand on the back of the head, 4 Hz scratching with the wrist
    if scr > 1e-6:
        side = 'Right'
        H = out[P + 'Head']
        M = H.to_3x3() @ B.rest[P + 'Head'].to_3x3().inverted()
        face, up, left = M @ Vector((0, -1, 0)), M @ Vector((0, 0, 1)), M @ Vector((1, 0, 0))
        ph = 2 * math.pi * 4.0 * (t - 3.98)
        amp = 0.016 * smooth_bump(t, 3.9, 5.1) ** 0.5
        tgt = (H.translation + up * 0.20 - face * 0.13 - left * 0.08 + up * (amp * math.sin(ph))
               + left * (0.5 * amp * math.cos(ph)))
        k = smooth(scr)
        q1 = _hand_q(side, up * 0.7 + left * 0.5 + face * 0.2, face * 0.6 + left * 0.4)
        S.arm_ik2(out, side, tgt, q1, Vector((-1.0, 0.1, 0.35)).normalized(), k)
    f = 0.1 + 0.25 * wat
    B.curl(out, 'Left', f, thumb=0.5 * f)
    B.curl(out, 'Right', 0.08 + 0.35 * scr * (0.6 + 0.4 * math.sin(2 * math.pi * 4.0 * (t - 3.98))),
           thumb=0.2 * scr)
    return out, {'dz': dz, 'over': over}


# ----------------------------------------------------------------------------- registry
class Ctx:
    def __init__(self, B, channels):
        self.S = StandRig(B)
        self.B = B
        self.ch = channels()


def _canonical(ctx, N):
    v = ctx.B.idle_values
    return {1.0: v, float(N + 1): v}


def _stand_stats(info):
    return {'min_pelvis_dz_m': min(i['dz'] for i in info), 'max_pelvis_dz_m': max(i['dz'] for i in info),
            'max_leg_overreach_m': max(i['over'] for i in info)}


CLIPS = {
    'Idle_Stand': {'T': STAND_T, 'loop': True, 'stage': 'stand',
                   'setup': lambda B: Ctx(B, stand_channels),
                   'pose': lambda ctx, t: stand_pose(ctx.S, t, ctx.ch),
                   'canonical': _canonical, 'stats': _stand_stats,
                   'beats': ['0.0-0.3 knees unlock, inhale starts', '0.3-1.55 weight onto the left leg with overshoot/settle, chest and arms lag',
                             '1.35-2.2 gaze drifts right and down (spacing out)', '2.2-2.6 blink-like head dip and snap back',
                             '2.4-3.45 second, deeper breath; weight returns home with a small counter-swing', '3.45-4.0 settle onto Idle frame 1']},
    'Idle_Bored': {'T': BORED_T, 'loop': True, 'stage': 'stand',
                   'setup': lambda B: Ctx(B, bored_channels),
                   'pose': lambda ctx, t: bored_pose(ctx.S, t, ctx.ch),
                   'canonical': _canonical, 'stats': _stand_stats,
                   'beats': ['0.0-0.25 neutral', '0.25-1.3 "anybody coming?": looks right, holds with a drift, sweeps left dipping mid-arc, holds',
                             '1.35-2.4 watch check: left forearm snaps up, head looks down, double take, two quick wrist shakes',
                             '2.4-3.7 BIG SIGH: huge inhale with a shoulder shrug and the head back, hold, hard exhale: slump, knees unlock, hip pops right, arms dangle',
                             '3.7-5.2 lazy scratch of the back of the head with the right hand, head tilts into it',
                             '5.2-6.0 straightens and settles onto Idle frame 1 (knees locked 0.35 s before the seam)']},
}
