"""Police clips, v02 revisions (fixes round 2026-10-11): Cop_Run_Fat, Cop_Punch, Cop_ShakeFist.

Registered under the v01 names; build_ep_v02.py writes them as <Clip>_v02.*. Reuses ep_core and
clips_police (imported, unchanged). See ep_core.py for the conventions (30 fps, metres, +Z up,
the character faces -Y, his left is +X; R(X, +) leans an upward bone forward, R(Y, +) tips it toward
his left, R(Z, +) turns him to his left).

  Cop_Run_Fat : a heavy waddle RUN instead of a brisk walk. Near-flight, a deep landing squash every
                step, the chest/belly and the giant head keep dropping after the foot lands and bounce
                back (lagged periodic responses), the whole body rocks over the stance foot, arms out
                and pumping with lag, toe-out short strides on a wide track.
  Cop_Punch   : the same 0.45 s telegraph and Hit at 0.45 s, now with weight behind it: the right foot
                steps back in the wind-up (weight back, front toes lift), the strike drives off the
                back leg (heel peel, hips and chest rotate into it, weight onto the bent front knee),
                the follow-through overshoots and pulls him off balance so the back foot swings
                forward and catches him on its exact Idle spot, then he settles into Idle frame 1.
  Cop_ShakeFist: same acting as v01, but the right arm is an explicit IK path in the chest frame that
                keeps the fist out to the side and in front of the head (it went behind / into the
                head at ~0.77 s and ~1.57 s in v01).
"""
import math
from mathutils import Vector, Matrix, Quaternion
import ep_core as E
import clips_police as CP
from ep_core import (R, QI, Curve, P, X, Y, Z, SIDES, SGN, smooth, clamp, lerp, win, bump, K, Chan, arm, spine,
                     head, idle_canonical, step_arc)

CLIPS = {}


class Prm:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def pcurve(keys):
    """Periodic curve over a unit phase (first and last value equal)."""
    return Curve(list(keys), periodic=True)


# ============================================================================= Cop_Run_Fat v02
FAT = Prm(
    T=16 / 30, v=2.2,
    # feet: stance fraction per foot (0.40 -> 0.2 of each step airborne), heel ground point at touchdown
    c=0.40, y_td=-0.18, x_off=0.065, lift=0.09, lift_peak=0.38, td_pitch=-5.0, peel_from=0.50,
    peel_pitch=32.0, swing_peak=36.0, toe_yaw=17.0, land_flat=0.12, swing_out=0.035, splay=0.30,
    # hips height over one step (phase 0 = touchdown): still falling at touchdown, deep squash, push, float
    hz=[(0.0, 0.690), (0.10, 0.655), (0.30, 0.618), (0.50, 0.640), (0.70, 0.690), (0.84, 0.712), (1.0, 0.690)],
    surge=0.012,
    # side-to-side waddle: pelvis shift and whole-body rock over the stance foot (+ = over the left foot)
    sway=0.065, lag_sway=0.02, hip_roll=9.0, lag_rock=0.03, spine_roll=8.0, lag_spine=0.035,
    head_counter=12.0, lag_headroll=0.09,
    yaw=8.0, lag_yaw=0.0, chest_yaw=9.0,
    # posture: belly first (lower spine arched back), shoulders hunched, head pushed forward with the chin out
    hip_pitch=0.0, sp=(-8.0, 4.0, 10.0), neck=18.0, headp=-16.0,
    # landing responses (per step phase, delayed): belly bounce fold and head nod
    fold=14.0, lag_chest=0.025, nod_neck=8.0, lag_neck=0.05, nod_head=12.0, lag_head=0.085,
    # arms out and pumping with lag, flopping down on every landing
    arm_out=36.0, arm_bias=2.0, arm_swing=40.0, lag_arm=0.05, elbow=86.0, elbow_pump=26.0, flap=10.0,
    lag_flap=0.07, arm_drop=10.0, elbow_flop=14.0, sh_drop=7.0, lag_armresp=0.04, fist=0.7,
)

# belly bounce: 0 at touchdown (+lag), drops to 1, rebounds past 0 (up), settles
SQ_KEYS = [(0.0, 0.0), (0.15, 0.55), (0.32, 1.0), (0.55, 0.05), (0.70, -0.35), (0.86, -0.12), (1.0, 0.0)]
# head nod: bigger overshoot
NOD_KEYS = [(0.0, 0.0), (0.18, 0.6), (0.36, 1.0), (0.58, -0.1), (0.74, -0.55), (0.90, -0.2), (1.0, 0.0)]


class FatLeg(E.RunLeg):
    """RunLeg whose swing foot circles outward round the stance leg (waddle), sin^2 so the lift-off
    and touchdown velocities are untouched."""

    def __init__(self, body, side, p):
        E.RunLeg.__init__(self, body, side, p.T, p.v, p.c, p.y_td, x_off=SGN[side] * p.x_off, lift=p.lift,
                          lift_peak=p.lift_peak, td_pitch=p.td_pitch, peel_from=p.peel_from, peel_pitch=p.peel_pitch,
                          swing_pitch_peak=p.swing_peak, toe_yaw=SGN[side] * p.toe_yaw, land_flat=p.land_flat)
        self.out = p.swing_out

    def __call__(self, u):
        M, toe = E.RunLeg.__call__(self, u)
        u %= 1.0
        if u > self.c:
            s = (u - self.c) / (1 - self.c)
            M = Matrix.Translation((SGN[self.s] * self.out * math.sin(math.pi * s) ** 2, 0.0, 0.0)) @ M
        return M, toe


class FatCtx:
    def __init__(self, B, cache, p=FAT):
        self.B = B
        self.body = E.Body(B)
        self.p = p
        self.legs = {s: FatLeg(self.body, s, p) for s in SIDES}
        self.HZ = pcurve(p.hz)
        self.SQ = pcurve(SQ_KEYS)
        self.NOD = pcurve(NOD_KEYS)


def fat_pose(ctx, t):
    p, b = ctx.p, ctx.body
    T = p.T
    Ts = T / 2
    u = (t / T) % 1.0
    ph = (2 * u) % 1.0

    def sp(lag):            # step phase delayed by `lag` seconds
        return (ph - lag / Ts) % 1.0

    def cy(lag):            # cycle angle delayed by `lag` seconds (left touchdown at 0)
        return 2 * math.pi * (u - lag / T)

    hz = ctx.HZ(ph)
    sq_c = ctx.SQ(sp(p.lag_chest))
    sq_a = ctx.SQ(sp(p.lag_armresp))
    nod1 = ctx.NOD(sp(p.lag_neck))
    nod2 = ctx.NOD(sp(p.lag_head))
    rock = math.sin(cy(p.lag_rock))                      # +1: rocked over the left (stance) foot
    rock_s = math.sin(cy(p.lag_rock + p.lag_spine))
    rock_h = math.sin(cy(p.lag_rock + p.lag_headroll))
    rock_a = math.sin(cy(p.lag_rock + p.lag_flap))
    hx = p.sway * math.sin(cy(p.lag_sway))
    hy = p.surge * math.sin(2 * math.pi * (ph - 0.25))    # brakes on landing (+Y = back), surges on push-off
    yaw = -p.yaw * math.cos(cy(p.lag_yaw))               # left leg forward at u = 0 -> pelvis turned right
    chest = p.chest_yaw * math.cos(cy(p.lag_arm))        # chest counter-turns with the arms
    hrot = R(Z, yaw) @ R(Y, p.hip_roll * rock) @ R(X, p.hip_pitch)
    J = {}
    fold = p.fold * sq_c
    sr = p.spine_roll * rock_s
    J['Spine'] = R(Z, -0.35 * yaw + 0.25 * chest) @ R(X, p.sp[0] + 0.35 * fold) @ R(Y, 0.4 * sr)
    J['Spine1'] = R(Z, -0.35 * yaw + 0.35 * chest) @ R(X, p.sp[1] + 0.35 * fold) @ R(Y, 0.35 * sr)
    J['Spine2'] = R(Z, -0.3 * yaw + 0.4 * chest) @ R(X, p.sp[2] + 0.30 * fold) @ R(Y, 0.25 * sr)
    hc = -p.head_counter * rock_h
    J['Neck'] = R(Z, -0.45 * chest + 0.3 * yaw) @ R(X, p.neck + p.nod_neck * nod1) @ R(Y, 0.4 * hc)
    J['Head'] = R(Z, -0.35 * chest) @ R(X, p.headp + p.nod_head * nod2) @ R(Y, 0.6 * hc)
    ca = math.cos(cy(p.lag_arm))
    for s in SIDES:
        sg = SGN[s]
        fw = ca if s == 'Right' else -ca                # +1: this arm swung forward (opposite leg forward)
        flap = p.flap * (-sg) * rock_a                   # the arm on the high side flies up
        arm(J, s, fwd=p.arm_bias + p.arm_swing * fw, out=p.arm_out + 9.0 * fw + flap - p.arm_drop * sq_a,
            swing=6.0 * max(fw, 0.0), elbow=p.elbow + p.elbow_pump * fw - p.elbow_flop * sq_a,
            sh_up=3.0 - p.sh_drop * sq_a, sh_fwd=3.0 * fw, wrist=-8.0 * fw, twist=4.0)
    legs, toes = {}, {}
    for s in SIDES:
        M, toe = ctx.legs[s](u if s == 'Left' else u + 0.5)
        legs[s], toes[s] = M, toe
    curl = {s: (p.fist, 0.7) for s in SIDES}
    return b.pose(Vector((hx, hy, hz)), hrot, J, legs=legs, toes=toes, curl=curl, splay=p.splay)


CLIPS['Cop_Run_Fat'] = {
    'T': FAT.T, 'loop': True, 'stage': 'stand', 'setup': FatCtx, 'pose': fat_pose,
    'canonical': CP._loop_canonical, 'ground': lambda t, v=FAT.v: v * t,
    'ground_note': 'in place; ground +Y at %.2f m/s (play at speed / %.2f)' % (FAT.v, FAT.v),
    'start': 'own frame 1 (left heel touchdown)', 'end': 'frame 1 (exact seam)', 'events': {},
    'beats': [
        '0.000 left heel lands toe-out on a wide track while the body is still falling; hips sink 7.2 cm to 0.618 m by 0.080 s (deep knee bend)',
        '0.025-0.21 belly bounce: the chest folds 14 deg forward and down (max ~0.11 s) after the landing, then rebounds past upright (~0.21 s)',
        '0.05-0.28 the giant head nods down late (max ~0.18 s, 2-3 frames behind the chest) and whips back up through the next landing',
        'the whole body rocks over the stance foot (pelvis 9 deg + spine 8 deg, pelvis sway 6.5 cm); the head counter-tilts 0.09 s late',
        'arms out 36 deg (wider when forward), pumping +-40 deg with a 1.5-frame lag, flopping down on every landing',
        '0.213 left toe-off, 0.213-0.267 near-flight (both feet off the street, hips at their 0.712 m peak), 0.267 right heel lands (mirror)',
        '0.533 seam = frame 1 (16 frames)']}


# ============================================================================= Cop_Punch v02
PUNCH_T = 1.2
PUNCH_HIT = CP.PUNCH_HIT          # 0.45 s, frame 14.5 (unchanged)
# right-foot step times: lift, land back, peel start, toe-off, catch (lands on its exact Idle spot)
RB_LIFT, RB_LAND, RB_PEEL, RB_OFF, RB_CATCH = 0.07, 0.21, 0.33, 0.48, 0.66


def punch2_chan():
    return Chan(
        # hips (+y = back), extra knee bend
        hx=K((0, 0), (0.07, 0.012), (0.21, -0.022), (0.28, -0.034), (0.33, -0.036), (0.45, 0.028), (0.55, 0.042),
             (0.66, 0.026), (0.80, -0.008), (0.96, 0.003), (PUNCH_T, 0)),
        hy=K((0, 0), (0.07, -0.006), (0.21, 0.075), (0.28, 0.112), (0.33, 0.118), (0.45, -0.068, ('lin', 'auto')),
             (0.55, -0.105), (0.66, -0.085), (0.80, -0.012), (0.94, 0.008), (PUNCH_T, 0)),
        drop=K((0, 0), (0.07, 0.010), (0.21, 0.035), (0.28, 0.046), (0.33, 0.050), (0.45, 0.040), (0.55, 0.075),
               (0.66, 0.060), (0.78, 0.020), (0.88, 0.028), (1.05, 0.002), (PUNCH_T, 0)),
        hyaw=K((0, 0), (0.07, 3), (0.21, -12), (0.28, -16), (0.33, -17), (0.45, 12, ('lin', 'auto')), (0.55, 20),
               (0.66, 14), (0.85, -3), (1.0, 1), (PUNCH_T, 0)),
        syaw=K((0, 0), (0.07, 3), (0.21, -18), (0.28, -27), (0.33, -28), (0.45, 14, ('lin', 'auto')), (0.53, 24),
               (0.64, 18), (0.86, -4), (1.02, 1), (PUNCH_T, 0)),
        hpitch=K((0, 0), (0.07, 2), (0.28, -5), (0.33, -6), (0.45, 8), (0.55, 11), (0.66, 7), (0.85, -1), (PUNCH_T, 0)),
        spitch=K((0, 0), (0.07, 4), (0.21, -8), (0.28, -12), (0.33, -13), (0.45, 18, ('lin', 'auto')), (0.55, 24),
                 (0.66, 14), (0.80, -3), (0.92, 1), (1.00, -3), (1.10, 1), (PUNCH_T, 0)),
        hroll=K((0, 0), (0.07, 2), (0.28, -4), (0.33, -4), (0.45, 4), (0.55, 6), (0.68, 2), (0.85, -1), (PUNCH_T, 0)),
        # head: keeps the eyes on the target in the wind-up, then lags and whips forward (overlap)
        neck=K((0, 0), (0.07, 2), (0.28, 8), (0.33, 9), (0.45, 4), (0.52, 10), (0.60, 16), (0.70, 3), (0.82, 7),
               (0.95, -2), (1.04, 6), (1.13, -1), (PUNCH_T, 0)),
        nyaw=K((0, 0), (0.21, 20), (0.33, 32), (0.45, -18), (0.55, -34), (0.66, -24), (0.85, 3), (PUNCH_T, 0)),
        nroll=K((0, 0), (0.28, -6), (0.45, 3), (0.62, 6), (0.72, -4), (0.84, 2), (1.0, 0), (PUNCH_T, 0)),
        # right arm FK: haymaker cock (v01), then FK recovery after the IK follow-through
        r_fwd=K((0, 0), (0.10, 8), (0.28, -16), (0.32, -18), (0.45, -18), (0.62, 60), (0.82, 24), (1.0, 2), (PUNCH_T, 0)),
        r_out=K((0, 0), (0.10, 25), (0.28, 80), (0.32, 82), (0.45, 82), (0.62, 14), (0.80, 18), (1.0, 2), (PUNCH_T, 0)),
        r_tw=K((0, 0), (0.10, 20), (0.28, 70), (0.32, 72), (0.45, 72), (0.62, 0), (PUNCH_T, 0)),
        r_elb=K((0, 0), (0.10, 45), (0.28, 112), (0.32, 118), (0.45, 118), (0.62, 30), (0.82, 34), (1.0, 6), (PUNCH_T, 0)),
        r_sh=K((0, 0), (0.28, 18), (0.33, 20), (0.45, 2), (0.7, 2), (PUNCH_T, 0)),
        r_shf=K((0, 0), (0.28, -14), (0.45, 16), (0.58, 18), (0.9, 0), (PUNCH_T, 0)),
        ikw=K((0, 0), (0.32, 0, ('flat', 'lin')), (0.45, 1, ('lin', 'flat')), (0.62, 1), (0.88, 0), (PUNCH_T, 0)),
        # left arm: points at the target, chambers back on the strike, flies out for balance
        l_fwd=K((0, 0), (0.10, 30), (0.28, 80), (0.33, 82), (0.45, 22), (0.56, -18), (0.68, -10), (0.86, 4), (PUNCH_T, 0)),
        l_elb=K((0, 0), (0.10, 20), (0.28, 6), (0.33, 6), (0.45, 112), (0.56, 50), (0.70, 40), (0.90, 8), (PUNCH_T, 0)),
        l_out=K((0, 0), (0.28, 4), (0.45, 22), (0.58, 52), (0.70, 40), (0.90, 6), (PUNCH_T, 0)),
        l_sw=K((0, 0), (0.28, 26), (0.45, 4), (PUNCH_T, 0)),
        fist=K((0, 0), (0.10, 0.92), (0.80, 0.9), (1.0, 0.2), (PUNCH_T, 0)),
        lfist=K((0, 0), (0.10, 0.92), (0.50, 0.9), (0.60, 0.25), (0.90, 0.2), (PUNCH_T, 0)),
        point=K((0, 0), (0.10, 1), (0.33, 1), (0.42, 0), (PUNCH_T, 0)),
        tremble=K((0, 0), (0.20, 0), (0.27, 1), (0.33, 1), (0.36, 0), (PUNCH_T, 0)),
        # feet
        ltoe=K((0, 0), (0.08, 0), (0.24, -13), (0.33, -14), (0.37, 0, ('lin', 'flat')), (PUNCH_T, 0)),     # front toes up (weight back)
        lpeel=K((0, 0), (0.50, 0), (0.60, 13), (0.66, 11), (0.74, 0, ('lin', 'flat')), (PUNCH_T, 0)),      # topples onto the front ball
        rpeel=K((0, 0), (RB_PEEL, 0), (0.45, 38), (RB_OFF, 42), (PUNCH_T, 42)),                           # drives off the back toe
        rsup=K((0, 1), (RB_LIFT, 1), (0.11, 0), (0.17, 0), (RB_LAND, 1), (0.44, 1), (0.50, 0), (0.60, 0), (RB_CATCH, 1),
               (PUNCH_T, 1)),
    )


PUNCH2_PATH = E.Path3([          # strike / follow-through only (weight ikw); the wind-up and recovery are FK
    (0.33, (0.09, -0.42, 0.01), R(X, -88), ('h', 0.80, 0.15, 0.58)),
    (0.45, (0.09, -0.42, 0.01), R(X, -88), ('h', 0.80, 0.15, 0.58)),
    (0.52, (0.15, -0.41, -0.02), R(X, -90), ('h', 0.80, 0.18, 0.57)),
    (0.60, (0.20, -0.35, -0.08), R(Z, 15) @ R(X, -86), ('h', 0.78, 0.22, 0.58)),
    (0.70, (0.17, -0.27, -0.18), R(Z, 20) @ R(X, -75), ('h', 0.75, 0.25, 0.60)),
])


class PunchCtx:
    def __init__(self, B, cache):
        self.B = B
        self.body = b = E.Body(B)
        self.ch = punch2_chan()
        # back spot of the right foot: ball 0.22 m behind and 3 cm out, toe out 20 deg
        bp = b.pivot0['Right']['ball']
        self.RB = b.foot('Right', (bp.x - 0.03, bp.y + 0.22, 0.0), R(Z, -20), 'ball')


def stand_w(body, hx, hy, hrot, J, drop, feet, sup, arms=None, curl=None, toes=None, splay=0.12, post=None):
    """E.stand with per-leg support weights (0 = lifted foot): the pelvis height is the min over the
    legs of (height where this leg reaches full length) + (1 - w) * 0.25, continuous when a foot
    lifts off or lands (no pelvis pop)."""
    q = dict(J)
    q['Hips'] = hrot
    out, _ = body.B.fk(body.base, q, Matrix.Translation((hx, hy, 0.0)))
    dz = 1e9
    for s in SIDES:
        v = out[P + s + 'UpLeg'].translation - feet[s].translation
        r = body.Lleg
        dz = min(dz, math.sqrt(max(r * r - v.x * v.x - v.y * v.y, 0.0)) - v.z + (1 - sup[s]) * 0.25)
    hips = body.hips0 + Vector((hx, hy, dz - drop))
    out, info = body.pose(hips, hrot, J, legs=feet, arms=arms, curl=curl, toes=toes, splay=splay, post=post)
    info['dz'] = dz - drop
    return out, info


def punch2_feet(ctx, t, c):
    b = ctx.body
    F0L, F0R = b.F0['Left'], b.F0['Right']
    # left (front) foot: toes up about the heel, flat, then a brief roll onto the ball
    if c.lpeel > 1e-6:
        ML = E.rot_about(b.pivot0['Left']['mtp'], R(X, c.lpeel)) @ F0L
        tl = c.lpeel
    else:
        ML = E.rot_about(b.pivot0['Left']['heel'], R(X, c.ltoe)) @ F0L if abs(c.ltoe) > 1e-6 else F0L.copy()
        tl = 0.0
    # right (back) foot
    RB = ctx.RB
    mtp_b = RB @ (F0R.inverted() @ b.pivot0['Right']['mtp'])
    lat = RB.to_3x3() @ F0R.to_3x3().inverted() @ Vector(X)
    tr = 0.0
    if t <= RB_LIFT:
        MR = F0R.copy()
    elif t < RB_LAND:
        MR, _ = step_arc(F0R, RB, t, RB_LIFT, RB_LAND, lift=0.06)
    elif t <= RB_OFF:
        MR = E.rot_about(mtp_b, R(lat, c.rpeel)) @ RB
        tr = c.rpeel
    elif t < RB_CATCH:
        M0 = E.rot_about(mtp_b, R(lat, c.rpeel)) @ RB
        MR, _ = step_arc(M0, F0R, t, RB_OFF, RB_CATCH, lift=0.07)
        tr = c.rpeel * (1 - smooth((t - RB_OFF) / (0.4 * (RB_CATCH - RB_OFF))))
    else:
        MR = F0R.copy()
    return {'Left': ML, 'Right': MR}, {'Left': tl, 'Right': tr}


def punch2_pose(ctx, t):
    c = ctx.ch(t)
    b = ctx.body
    J = {}
    tr = c.tremble * 1.2 * math.sin(2 * math.pi * 14 * t)     # straining wind-up quiver
    hrot = R(Z, c.hyaw) @ R(Y, c.hroll) @ R(X, c.hpitch)
    spine(J, pitch=c.spitch, yaw=c.syaw + tr, roll=0.6 * c.hroll)
    head(J, pitch=c.neck, roll=c.nroll + tr, yaw=c.nyaw)
    arm(J, 'Right', fwd=c.r_fwd, out=c.r_out, twist=c.r_tw, elbow=c.r_elb, sh_up=c.r_sh, sh_fwd=c.r_shf)
    arm(J, 'Left', fwd=c.l_fwd, out=c.l_out, swing=c.l_sw, elbow=c.l_elb, twist=0.3 * c.l_elb)
    lcurl = (c.lfist, c.lfist * (1 - 0.8 * c.point), {'Index': c.lfist * (1 - c.point)})
    post = E.ik_arm_post(b, 'Right', PUNCH2_PATH, t, c.ikw)
    feet, toes = punch2_feet(ctx, t, c)
    sup = {'Left': 1.0, 'Right': c.rsup}
    return stand_w(b, c.hx, c.hy, hrot, J, c.drop, feet, sup, curl={'Left': lcurl, 'Right': (c.fist, c.fist)},
                   toes=toes, post=post)


CLIPS['Cop_Punch'] = {
    'T': PUNCH_T, 'loop': False, 'stage': 'stand', 'setup': PunchCtx, 'pose': punch2_pose, 'canonical': idle_canonical,
    'start': 'Idle frame 1 (exact)', 'end': 'Idle frame 1 (exact)', 'events': {'Hit': PUNCH_HIT},
    'beats': [
        '0.00-0.07 weight shifts onto the left foot, fists clench',
        '0.07-0.21 the right foot steps back 22 cm (toe out); the weight goes back onto it: hips back 12 cm, body twists 45 deg away and leans back, front toes lift',
        '0.10-0.28 haymaker cock: right fist up by the ear; the left index finger points at the target',
        '0.28-0.33 straining hold (quiver)',
        '0.33-0.45 the strike drives off the back leg: back heel peels about the toe, hips and chest rotate into it, weight onto the bent front knee, head forward',
        '0.45 HIT (full extension, frame 14.5)',
        '0.45-0.60 follow-through: torso keeps twisting (chest +44 deg), the fist carries past the target and across, he topples onto the front ball',
        '0.48-0.66 off balance: the back foot is pulled off the street and swings forward to catch him on its exact Idle spot',
        '0.66-0.90 teeter and rebalance (head wobble, arms out)', '0.90-1.20 settles into Idle frame 1'],
}


# ============================================================================= Cop_ShakeFist v02
SHAKE_T = CP.SHAKE_T           # 2.2 s


def shake2_chan():
    env = K((0, 0), (0.48, 0), (0.56, 1), (1.42, 1), (1.50, 0.4), (1.70, 0), (SHAKE_T, 0))
    return Chan(
        env=env,
        drop=K((0, 0), (0.25, 0.045), (0.42, 0.02), (0.9, 0.025), (1.0, 0.02), (1.16, 0.055), (1.26, 0.03), (1.62, 0.04),
               (1.9, 0.03), (2.06, 0.006), (SHAKE_T, 0)),
        pitch=K((0, 0), (0.25, -7), (0.45, 14), (0.9, 12), (1.16, 18), (1.3, 12), (1.55, 6), (1.66, 20), (1.85, 10), (2.05, 1), (SHAKE_T, 0)),
        yaw=K((0, 0), (0.25, 4), (0.45, -5), (1.4, -4), (1.66, -7), (1.9, -1), (SHAKE_T, 0)),
        r_sh=K((0, 0), (0.25, 4), (0.45, 16), (1.6, 16), (1.85, -6), (2.05, -2), (SHAKE_T, 0)),
        ikw=K((0, 0), (0.03, 0), (0.12, 1), (2.06, 1), (2.16, 0), (SHAKE_T, 0)),
        l_akimbo=K((0, 0), (0.22, 0), (0.48, 1), (1.62, 1), (1.92, 0), (SHAKE_T, 0)),
        neck=K((0, 0), (0.25, 10), (0.45, 22), (1.5, 20), (1.68, 28), (1.85, 4), (1.95, 12), (SHAKE_T, 0)),
        chin=K((0, 0), (0.25, 4), (0.45, -16), (1.5, -14), (1.68, -20), (1.85, 2), (SHAKE_T, 0)),
        no=K((0, 0), (1.80, 0), (1.86, 1), (2.05, 1), (2.14, 0), (SHAKE_T, 0)),
        fist=K((0, 0), (0.20, 0.95), (1.80, 0.95), (2.05, 0.3), (SHAKE_T, 0)),
        stomp=K((0, 0), (0.95, 0), (1.06, 1), (1.15, 0, ('lin', 'flat')), (SHAKE_T, 0)),
        jolt=K((0, 0), (1.14, 0), (1.17, 1), (1.32, 0), (SHAKE_T, 0)),
        wrist=K((0, 0), (0.25, 20), (0.40, -15), (0.50, -5), (1.45, -5), (1.56, 30), (1.68, -20), (1.80, -5),
                (2.0, 10), (SHAKE_T, 0)),
    )


class ShakeCtx:
    def __init__(self, B, cache):
        self.B = B
        self.body = b = E.Body(B)
        self.ch = shake2_chan()
        base = b.base
        s2 = base[P + 'Spine2'].translation
        w = base[P + 'RightHand'].translation
        el = base[P + 'RightForeArm'].translation
        sho = base[P + 'RightArm'].translation
        idle_off = tuple(w - s2)
        line = (w - sho).normalized()
        e0 = (el - sho) - line * (el - sho).dot(line)
        e0 = tuple(e0.normalized())
        # wrist offsets from the chest (Spine2 head, riding the chest rotation) and the elbow direction
        keys = [
            (0.00, idle_off, e0),
            (0.08, idle_off, e0),
            (0.25, (-0.24, -0.17, -0.10), (-0.55, 0.55, -0.62)),     # gathers: fist clenched in front of the chest
            (0.33, (-0.35, -0.27, 0.15), (-0.80, 0.25, -0.55)),      # (arcs outward, clear of the chin)
            (0.40, (-0.29, -0.25, 0.43), (-0.85, 0.15, -0.50)),      # thrust up, forward and out (overshoot)
            (0.50, (-0.31, -0.24, 0.38), (-0.85, 0.20, -0.50)),      # shake position: raised, out to the side and in front of the face
            (1.45, (-0.31, -0.24, 0.38), (-0.85, 0.20, -0.50)),
            (1.56, (-0.32, -0.24, 0.06), (-0.75, 0.45, -0.50)),      # last wind-up: pulled down in front of the shoulder
            (1.68, (-0.29, -0.25, 0.43), (-0.85, 0.15, -0.50)),      # last big thrust
            (1.80, (-0.31, -0.24, 0.38), (-0.85, 0.20, -0.50)),
            (1.90, (-0.38, -0.21, 0.20), (-0.85, 0.30, -0.45)),      # deflates: the arm drops out to the side
            (2.00, (-0.35, -0.13, -0.06), (-0.70, 0.55, -0.45)),
            (2.14, idle_off, e0),
            (SHAKE_T, idle_off, e0),
        ]
        self.off = [K(*[(k[0], k[1][i]) for k in keys]) for i in range(3)]
        self.elb = [K(*[(k[0], k[2][i]) for k in keys]) for i in range(3)]


def fist_post(ctx, t, c, sh):
    """Right arm IK: wrist at the keyed chest-frame offset (+ the shake), elbow toward the keyed direction,
    the hand follows the forearm (FK wrist on top). Blended over the FK arm by c.ikw."""
    b = ctx.body
    B = b.B

    def post(out):
        if c.ikw <= 1e-9:
            return
        Ra = (out[P + 'Spine2'].to_3x3() @ b.base[P + 'Spine2'].to_3x3().inverted())
        off = Vector([f(t) for f in ctx.off]) + Vector((0.0, -0.010 * sh, 0.045 * sh))
        e = Ra @ Vector([f(t) for f in ctx.elb])
        target = out[P + 'Spine2'].translation + Ra @ off
        H = out[P + 'RightArm'].translation
        line = (target - H).normalized()
        ep = e - line * e.dot(line)
        hinge = line.cross(ep.normalized())
        ik = dict(out)
        hm = out[P + 'RightHand'].copy()
        b.solve(ik, b.arm['Right'], target, hm, hinge)
        # the hand follows the forearm (as FK would), plus the wrist flexion
        fa = P + 'RightForeArm'
        hn = P + 'RightHand'
        Rfa = ik[fa].to_3x3() @ b.base[fa].to_3x3().inverted()
        rot = Rfa @ R(X, -(c.wrist - 16 * sh)).to_matrix() @ b.base[hn].to_3x3()
        m = rot.to_4x4()
        m.translation = ik[hn].translation
        delta = m @ ik[hn].inverted()
        for n in B.subtree('RightHand'):
            ik[n] = delta @ ik[n]
        E.blend_subtree(B, out, ik, 'RightArm', c.ikw)
    return post


def shake2_pose(ctx, t):
    c = ctx.ch(t)
    b = ctx.body
    w = 2 * math.pi * 4.6
    sh = c.env * math.sin(w * (t - 0.5))
    bob = c.env * abs(math.sin(w * (t - 0.5))) * 0.012
    J = {}
    hrot = R(Z, 0.3 * c.yaw) @ R(X, 0.25 * c.pitch) @ R(Y, -2.5 * c.jolt)
    spine(J, pitch=0.75 * c.pitch + 4 * c.jolt, yaw=0.7 * c.yaw - 3 * sh, roll=-2 * sh)
    noy = 14 * c.no * math.sin(2 * math.pi * 4.2 * (t - 1.86))
    head(J, pitch=c.neck + c.chin + 6 * sh, yaw=noy + 4 * sh, roll=5 * c.jolt * math.sin(2 * math.pi * 7 * t), neck=0.6)
    arm(J, 'Right', sh_up=c.r_sh + 3 * sh)
    a = c.l_akimbo
    arm(J, 'Left', fwd=-14 * a, out=48 * a, twist=-85 * a, elbow=118 * a, wrist=-20 * a, wdev=-15 * a, sh_up=4 * a)
    feet = {}
    if c.stomp > 1e-6:
        M = b.F0['Left'].copy()
        lift = 0.11 * c.stomp
        M = Matrix.Translation((0.01 * c.stomp, -0.03 * c.stomp, lift)) @ E.rot_about(b.pivot0['Left']['heel'], R(X, -12 * c.stomp)) @ M
        feet['Left'] = M
    return E.stand(b, -0.03 * c.stomp, 0.0, hrot, J, drop=c.drop + bob + 0.03 * c.jolt, feet=feet,
                   curl={'Left': (0.35 * a, 0.2 * a), 'Right': (c.fist, c.fist)}, post=fist_post(ctx, t, c, sh))


CLIPS['Cop_ShakeFist'] = {
    'T': SHAKE_T, 'loop': False, 'stage': 'stand', 'setup': ShakeCtx, 'pose': shake2_pose, 'canonical': idle_canonical,
    'start': 'Idle frame 1 (exact)', 'end': 'Idle frame 1 (exact)', 'events': {},
    'beats': [
        '0.00-0.25 gathers rage: crouch, lean back, right fist clenched in front of the chest',
        '0.25-0.45 the right fist thrusts up, forward and out beside the head; chest forward, chin out (yelling)',
        '0.50-1.45 the fist shakes at 4.6 Hz out to the side and in front of the head; body bounces, head jabs; left hand on hip',
        '0.95-1.15 left foot stamps (exact Idle spot), body jolts',
        '1.45-1.68 one last big wind-up (fist down and out to the side) and thrust',
        '1.80-2.10 deflates: arm drops, shoulders slump, "no-no" head shake', '2.10-2.20 settles into Idle frame 1'],
}
