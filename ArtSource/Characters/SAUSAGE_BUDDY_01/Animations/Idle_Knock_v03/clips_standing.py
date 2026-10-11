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
from acting_core import R, QI, Curve, P

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
}
