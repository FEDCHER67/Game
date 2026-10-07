"""Police clips: Cop_Run, Cop_Run_Fat, Cop_Punch, Cop_Aim_Raise, Cop_Aim, Cop_Trip, Cop_ShakeFist.

Same Buddy rig (the police are sausage people too). See ep_core.py for the conventions.
"""
import math
from mathutils import Vector, Matrix, Quaternion
import ep_core as E
from ep_core import R, QI, Curve, P, X, Y, Z, SIDES, SGN, smooth, clamp, lerp, win, bump, eul, pnoise


# ============================================================================= Cop_Run
class RunParams:
    def __init__(self, **kw):
        self.__dict__.update(kw)


RUN = RunParams(
    T=0.6, v=3.0, c=0.32, y_td=-0.15, x_off=0.0, lift=0.24, lift_peak=0.42, td_pitch=-12.0,
    peel_from=0.42, peel_pitch=40.0, swing_peak=62.0, toe_yaw=4.0,
    # hips height over one step (phase 0 = touchdown): land, compress, push, float
    bob=[(0.0, 0.712), (0.14, 0.668), (0.30, 0.660), (0.56, 0.728), (0.80, 0.752), (1.0, 0.712)],
    sway=0.018, yaw=10.0, roll=4.5, lean=14.0, spine_lean=(6.0, 6.0, 2.0),
    chest_yaw=13.0, arm_swing=42.0, arm_bias=-8.0, arm_out=10.0, elbow=95.0, elbow_pump=16.0,
    fist=0.92, neck=(9.0, 3.0), land_nod=7.0, land_squash=7.0, head_roll=3.0,
    arm_lag=0.05, head_lag=0.06, hunch=8.0,
)

FAT = RunParams(
    T=17 / 30, v=1.8, c=0.50, y_td=-0.17, x_off=0.05, lift=0.10, lift_peak=0.40, td_pitch=-6.0,
    peel_from=0.52, peel_pitch=24.0, swing_peak=28.0, toe_yaw=16.0,
    bob=[(0.0, 0.715), (0.15, 0.690), (0.32, 0.688), (0.60, 0.720), (0.80, 0.732), (1.0, 0.715)],
    sway=0.050, yaw=5.0, roll=6.0, lean=-5.0, spine_lean=(-4.0, -3.0, 3.0),
    chest_yaw=4.0, arm_swing=14.0, arm_bias=-6.0, arm_out=30.0, elbow=60.0, elbow_pump=8.0,
    fist=0.5, neck=(7.0, -3.0), land_nod=9.0, land_squash=6.0, head_roll=4.0,
    arm_lag=0.08, head_lag=0.09, waddle_twist=0.0, waddle_roll=10.0, arm_flap=14.0,
)

# civilian panic run (JumpOut lands into it): upright, arms flapping up, open hands, head thrown back
FLEE = RunParams(
    T=17 / 30, v=3.2, c=0.30, y_td=-0.16, x_off=0.0, lift=0.26, lift_peak=0.40, td_pitch=-12.0,
    peel_from=0.42, peel_pitch=40.0, swing_peak=60.0, toe_yaw=3.0,
    bob=[(0.0, 0.725), (0.14, 0.685), (0.30, 0.680), (0.56, 0.740), (0.80, 0.765), (1.0, 0.725)],
    sway=0.02, yaw=8.0, roll=4.0, lean=3.0, spine_lean=(0.0, -2.0, -3.0),
    chest_yaw=10.0, arm_swing=50.0, arm_bias=-55.0, arm_out=38.0, elbow=35.0, elbow_pump=20.0,
    fist=0.0, neck=(-6.0, -10.0), land_nod=6.0, land_squash=4.0, head_roll=6.0,
    arm_lag=0.04, head_lag=0.07, hunch=4.0,
)


class RunCtx:
    def __init__(self, B, prm):
        self.B = B
        self.body = E.Body(B)
        self.p = prm
        self.legs = {s: E.RunLeg(self.body, s, prm.T, prm.v, prm.c, prm.y_td, x_off=SGN[s] * prm.x_off, lift=prm.lift,
                                 lift_peak=prm.lift_peak, td_pitch=prm.td_pitch, peel_from=prm.peel_from,
                                 peel_pitch=prm.peel_pitch, swing_pitch_peak=prm.swing_peak,
                                 toe_yaw=SGN[s] * prm.toe_yaw) for s in SIDES}
        self.bob = Curve(prm.bob, periodic=True)
        self.ground = lambda t: prm.v * t


def run_pose(ctx, t, mod=None):
    """In-place run. Left touchdown at t = 0, right at T/2. mod(t, d) may edit the parts dict
    d = {hips, hrot, J, legs, toes, curl} before the solve (used by Cop_Trip)."""
    p, b = ctx.p, ctx.body
    u = (t / p.T) % 1.0
    ph = (2 * u) % 1.0                      # step phase
    tw = 2 * math.pi * u
    # stance side: Left for u in [0, 0.5)
    side_sign = 1.0 if u < 0.5 else -1.0
    wrap = lambda x: (x + 0.5) % 1.0 - 0.5                  # periodic phase distance (seamless pulses)
    land = math.exp(-(wrap(ph - 0.12) / 0.11) ** 2)          # landing impact pulse each step
    land_l = math.exp(-(wrap((2 * ((u - p.head_lag / p.T) % 1.0)) % 1.0 - 0.14) / 0.12) ** 2)
    hz = ctx.bob(ph)
    hx = p.sway * math.sin(tw - 0.6)
    yaw = -p.yaw * math.cos(tw - 0.35)
    roll = -p.roll * math.sin(tw - 0.4)
    hrot = R(Z, yaw) @ R(Y, roll) @ R(X, p.lean * 0.4)
    J = {}
    sl = p.spine_lean
    tw_extra = getattr(p, 'waddle_twist', 0.0)
    wr = getattr(p, 'waddle_roll', 0.0)
    tilt = wr * math.sin(tw - 0.25)               # penguin tilt over the stance foot (left stance -> +)
    tilt_l = wr * math.sin(tw - 0.25 - 2 * math.pi * p.head_lag / p.T)
    J['Spine'] = R(X, sl[0] + p.lean * 0.2 + p.land_squash * 0.5 * land) @ R(Z, -yaw * 0.35) @ R(Y, -roll * 0.5 + 0.55 * tilt)
    J['Spine1'] = R(Y, 0.45 * tilt) @ R(X, sl[1] + p.lean * 0.2 + p.land_squash * land) @ R(Z, -yaw * 0.45 + p.chest_yaw * 0.4 * math.cos(tw - 0.6))
    J['Spine2'] = R(X, sl[2] + p.land_squash * 0.5 * land) @ R(Z, p.chest_yaw * 0.6 * math.cos(tw - 0.6)) @ R(Y, -roll * 0.4 - tw_extra * 0.3 * math.sin(tw - 0.9))
    J['Neck'] = R(X, p.neck[0] - p.land_nod * 0.3 * land_l) @ R(Z, -p.chest_yaw * 0.5 * math.cos(tw - 0.6))
    J['Head'] = R(X, p.neck[1] + p.land_nod * land_l) @ R(Y, p.head_roll * math.sin(tw - 1.2) - 0.9 * tilt_l + 0.5 * tilt) @ R(Z, -p.chest_yaw * 0.3 * math.cos(tw - 0.9))
    # arms: opposite to the legs (left leg forward at u = 0 -> left arm back), pumping elbows
    for s in SIDES:
        sg = SGN[s]
        ua = u - p.arm_lag / p.T
        sw = p.arm_swing * math.cos(2 * math.pi * ua) * sg          # + = arm back (R(X,+) swings a hanging arm back)
        if s == 'Right':
            sw = -p.arm_swing * math.cos(2 * math.pi * ua)
        else:
            sw = p.arm_swing * math.cos(2 * math.pi * ua)
        fwdness = -sw / p.arm_swing                                   # +1 arm fully forward
        hunch = getattr(p, 'hunch', 0.0)
        J[s + 'Shoulder'] = R(X, -4 * fwdness) @ R(Y, -sg * (3.0 * (0.5 + 0.5 * fwdness) + hunch))
        flap = getattr(p, 'arm_flap', 0.0) * (-sg) * math.sin(tw - 0.25 - 0.5)   # arm on the high side lifts
        J[s + 'Arm'] = R(Y, -sg * (p.arm_out - hunch * 0.8 + flap)) @ R(X, sw + p.arm_bias) @ R(Z, sg * 6 * fwdness)
        J[s + 'ForeArm'] = R(X, -(p.elbow + p.elbow_pump * fwdness)) @ R(Z, sg * 10)
        J[s + 'Hand'] = R(Y, sg * 8) @ R(X, -10 * fwdness)
    legs, toes = {}, {}
    for s in SIDES:
        us = u if s == 'Left' else u + 0.5
        M, toe = ctx.legs[s](us)
        legs[s] = M
        toes[s] = toe
    hips = Vector((hx, 0.0, hz))
    d = {'hips': hips, 'hrot': hrot, 'J': J, 'legs': legs, 'toes': toes,
         'curl': {'Left': (p.fist, 0.8), 'Right': (p.fist, 0.8)}}
    if mod:
        mod(t, d)
    out, info = b.pose(d['hips'], d['hrot'], d['J'], legs=d['legs'], toes=d['toes'], curl=d['curl'])
    return out, info


def _loop_canonical(ctx, frames, N):
    v = ctx.B.values_from_pose(frames[1.0])
    return {1.0: v, float(N + 1): v}


def _run_spec(prm, beats, note):
    return {'T': prm.T, 'loop': True, 'stage': 'stand',
            'setup': lambda B, cache, prm=prm: RunCtx(B, prm),
            'pose': lambda ctx, t: run_pose(ctx, t),
            'canonical': _loop_canonical,
            'ground': lambda t, v=prm.v: v * t,
            'ground_note': 'in place; ground +Y at %.2f m/s (play at speed / %.2f)' % (prm.v, prm.v),
            'start': 'own frame 1 (left heel touchdown)', 'end': 'frame 1 (exact seam)',
            'beats': beats}


CLIPS = {
    'Flee_Run': _run_spec(FLEE, [
        'bonus civilian panic run (JumpOut ends on its frame 1): upright, arms flapping up in front with open hands',
        'head thrown back (screaming), quick 0.567 s (17-frame) cycle at 3.2 m/s', '0.283 right heel lands (mirror)', '0.567 seam = frame 1'], 'flee'),
    'Cop_Run': _run_spec(RUN, [
        '0.00 left heel lands; body sinks 3.7 cm into the landing, chest folds, head nods (lags 2 frames)',
        '0.10 left heel peels, push-off; fists pump to chin height, elbows ~92-106 deg',
        '0.19-0.30 flight; right knee drives forward, left heel kicks up behind',
        '0.30 right heel lands (mirror)', '0.60 seam = frame 1'],
        'run'),
    'Cop_Run_Fat': _run_spec(FAT, [
        '0.00 left foot lands toe-out on a wide track; hips lurch 5.5 cm onto it and roll 7.5 deg',
        '0.00-0.36 belly-first posture (leans back), arms held out round the belly, short paddling swing',
        'head bobbles sideways with a 3-frame lag; landing nods are big',
        '0.283 right foot lands (mirror)', '0.567 seam = frame 1 (17 frames)'],
        'waddle'),
}


# ============================================================================= standing police clips
from ep_core import K, Chan, stand, arm, spine, head, idle_canonical, step_arc


class StandCtx:
    def __init__(self, B, chan_fn):
        self.B = B
        self.body = E.Body(B)
        self.ch = chan_fn()


def _stand_spec(T, chan_fn, pose_fn, beats, events=None, loop=False, canonical=idle_canonical,
                start='Idle frame 1 (exact)', end='Idle frame 1 (exact)'):
    return {'T': T, 'loop': loop, 'stage': 'stand', 'setup': lambda B, cache: StandCtx(B, chan_fn),
            'pose': pose_fn, 'canonical': canonical, 'beats': beats, 'events': events or {},
            'start': start, 'end': end}


# ---- Cop_Punch: 0.45 s telegraph, Hit at 0.45 s
PUNCH_HIT = 0.45


def punch_chan():
    # wind-up peak 0.30-0.33 (straining hold), strike 0.33 -> 0.45 at constant speed, Hit at 0.45
    return Chan(
        yaw=K((0, 0), (0.08, 5), (0.28, -38), (0.33, -42), (0.45, 24, ('lin', 'auto')), (0.52, 30), (0.64, 26), (0.86, -3), (1.0, 0)),
        pitch=K((0, 0), (0.08, 6), (0.28, -13), (0.33, -15), (0.45, 15, ('lin', 'auto')), (0.53, 21), (0.66, 16), (0.88, -2), (1.0, 0)),
        hx=K((0, 0), (0.30, -0.03), (0.45, 0.012), (0.7, 0.008), (1.0, 0)),
        hy=K((0, 0), (0.08, -0.012), (0.30, 0.05), (0.45, -0.055), (0.55, -0.07), (0.68, -0.06), (0.92, 0.004), (1.0, 0)),
        drop=K((0, 0), (0.08, 0.03), (0.30, 0.035), (0.45, 0.06), (0.55, 0.075), (0.72, 0.05), (0.92, 0.004), (1.0, 0)),
        # right arm FK: haymaker cock (upper arm out to the side, fist up by the ear), FK again on recovery
        # (during the strike ikw carries the arm; the FK holds the cock until the IK fully owns it)
        r_fwd=K((0, 0), (0.10, 8), (0.28, -16), (0.32, -18), (0.45, -18), (0.62, 82), (0.86, 6), (1.0, 0)),
        r_out=K((0, 0), (0.10, 25), (0.28, 80), (0.32, 82), (0.45, 82), (0.62, 8), (0.86, 2), (1.0, 0)),
        r_tw=K((0, 0), (0.10, 20), (0.28, 70), (0.32, 72), (0.45, 72), (0.62, 0), (1.0, 0)),
        r_elb=K((0, 0), (0.10, 45), (0.28, 112), (0.32, 118), (0.45, 118), (0.62, 12), (0.80, 40), (1.0, 0)),
        r_sh=K((0, 0), (0.28, 18), (0.33, 20), (0.45, 2), (0.7, 2), (1.0, 0)),
        r_shf=K((0, 0), (0.28, -14), (0.45, 16), (0.62, 14), (0.9, 0), (1.0, 0)),
        ikw=K((0, 0), (0.32, 0, ('flat', 'lin')), (0.45, 1, ('lin', 'flat')), (0.64, 1), (0.86, 0), (1.0, 0)),
        l_fwd=K((0, 0), (0.10, 30), (0.28, 80), (0.33, 82), (0.45, 22), (0.56, 12), (0.82, 4), (1.0, 0)),
        l_elb=K((0, 0), (0.10, 20), (0.28, 6), (0.33, 6), (0.45, 112), (0.62, 104), (0.86, 8), (1.0, 0)),
        l_out=K((0, 0), (0.28, 4), (0.45, 22), (0.8, 4), (1.0, 0)),
        l_sw=K((0, 0), (0.28, 26), (0.45, 4), (1.0, 0)),
        neck=K((0, 0), (0.28, -10), (0.33, -11), (0.45, 4), (0.56, 12), (0.80, 0), (1.0, 0)),
        hroll=K((0, 0), (0.28, -8), (0.45, 3), (0.6, 5), (0.9, 0), (1.0, 0)),
        fist=K((0, 0), (0.10, 0.92), (0.84, 0.9), (1.0, 0)),
        point=K((0, 0), (0.10, 1), (0.33, 1), (0.42, 0), (1.0, 0)),
        tremble=K((0, 0), (0.20, 0), (0.27, 1), (0.33, 1), (0.36, 0), (1.0, 0)),
    )


IDLE_RW = Vector((-0.1146, -0.0782, -0.4145))     # Idle right wrist relative to the right shoulder joint
PUNCH_PATH = E.Path3([          # strike / hold only (weight ikw); the wind-up and recovery are FK
    (0.33, (0.09, -0.42, 0.01), R(X, -88), ('h', 0.80, 0.15, 0.58)),
    (0.45, (0.09, -0.42, 0.01), R(X, -88), ('h', 0.80, 0.15, 0.58)),
    (0.52, (0.10, -0.425, -0.01), R(X, -90), ('h', 0.80, 0.15, 0.58)),
    (0.64, (0.08, -0.40, -0.04), R(X, -85), ('h', 0.80, 0.20, 0.56)),
])


def punch_pose(ctx, t):
    c = ctx.ch(t)
    J = {}
    tr = c.tremble * 1.2 * math.sin(2 * math.pi * 14 * t)     # straining wind-up quiver
    hrot = R(Z, 0.35 * c.yaw) @ R(X, 0.3 * c.pitch)
    spine(J, pitch=0.7 * c.pitch, yaw=0.65 * c.yaw + tr, roll=0.2 * c.hroll)
    head(J, pitch=c.neck - 0.25 * c.pitch, roll=c.hroll + tr, yaw=-0.45 * c.yaw)
    arm(J, 'Right', fwd=c.r_fwd, out=c.r_out, twist=c.r_tw, elbow=c.r_elb, sh_up=c.r_sh, sh_fwd=c.r_shf)
    arm(J, 'Left', fwd=c.l_fwd, out=c.l_out, swing=c.l_sw, elbow=c.l_elb, twist=0.3 * c.l_elb)
    # the left hand points at the target during the wind-up (index finger out), then fists
    lcurl = (c.fist, c.fist * (1 - 0.8 * c.point), {'Index': c.fist * (1 - c.point)})
    post = E.ik_arm_post(ctx.body, 'Right', PUNCH_PATH, t, c.ikw)
    return stand(ctx.body, c.hx, c.hy, hrot, J, drop=c.drop, curl={'Left': lcurl, 'Right': (c.fist, c.fist)}, post=post)


# ---- Cop_ShakeFist: angry fist shake at the escaping van (one-shot from/to Idle)
SHAKE_T = 2.2


def shake_chan():
    env = K((0, 0), (0.48, 0), (0.56, 1), (1.42, 1), (1.50, 0.4), (1.70, 0), (SHAKE_T, 0))
    return Chan(
        env=env,
        drop=K((0, 0), (0.25, 0.045), (0.42, 0.02), (0.9, 0.025), (1.0, 0.02), (1.16, 0.055), (1.26, 0.03), (1.62, 0.04),
               (1.9, 0.03), (2.06, 0.006), (SHAKE_T, 0)),
        pitch=K((0, 0), (0.25, -7), (0.45, 14), (0.9, 12), (1.16, 18), (1.3, 12), (1.55, 6), (1.66, 20), (1.85, 10), (2.05, 1), (SHAKE_T, 0)),
        yaw=K((0, 0), (0.25, 6), (0.45, -10), (1.4, -8), (1.66, -14), (1.9, -2), (SHAKE_T, 0)),
        r_fwd=K((0, 0), (0.25, 20), (0.42, 138), (0.50, 132), (1.45, 136), (1.56, 108), (1.68, 150), (1.78, 136), (2.02, 6), (SHAKE_T, 0)),
        r_out=K((0, 0), (0.25, 14), (0.45, 58), (1.6, 55), (1.9, 8), (SHAKE_T, 0)),
        r_elb=K((0, 0), (0.25, 110), (0.42, 30), (0.50, 40), (1.45, 40), (1.56, 95), (1.68, 20), (1.80, 35), (2.0, 15), (SHAKE_T, 0)),
        r_sh=K((0, 0), (0.25, 4), (0.45, 16), (1.6, 16), (1.85, -6), (2.05, -2), (SHAKE_T, 0)),
        l_akimbo=K((0, 0), (0.22, 0), (0.48, 1), (1.62, 1), (1.92, 0), (SHAKE_T, 0)),
        neck=K((0, 0), (0.25, 10), (0.45, 22), (1.5, 20), (1.68, 28), (1.85, 4), (1.95, 12), (SHAKE_T, 0)),
        chin=K((0, 0), (0.25, 4), (0.45, -16), (1.5, -14), (1.68, -20), (1.85, 2), (SHAKE_T, 0)),
        no=K((0, 0), (1.80, 0), (1.86, 1), (2.05, 1), (2.14, 0), (SHAKE_T, 0)),
        fist=K((0, 0), (0.20, 0.95), (1.80, 0.95), (2.05, 0.3), (SHAKE_T, 0)),
        stomp=K((0, 0), (0.95, 0), (1.06, 1), (1.15, 0, ('lin', 'flat')), (SHAKE_T, 0)),
        jolt=K((0, 0), (1.14, 0), (1.17, 1), (1.32, 0), (SHAKE_T, 0)),
    )


def shake_pose(ctx, t):
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
    arm(J, 'Right', fwd=c.r_fwd + 7 * sh, out=c.r_out, elbow=c.r_elb + 26 * sh, sh_up=c.r_sh + 3 * sh,
        wrist=-12 * sh, twist=-10 * clamp(c.r_fwd / 150, 0.0, 1.0))
    a = c.l_akimbo
    arm(J, 'Left', fwd=-14 * a, out=48 * a, twist=-85 * a, elbow=118 * a, wrist=-20 * a, wdev=-15 * a, sh_up=4 * a)
    # left foot stomp: lift, then slam down onto its exact Idle spot
    feet, free = {}, ()
    if c.stomp > 1e-6:
        M = b.F0['Left'].copy()
        lift = 0.11 * c.stomp
        M = Matrix.Translation((0.01 * c.stomp, -0.03 * c.stomp, lift)) @ E.rot_about(b.pivot0['Left']['heel'], R(X, -12 * c.stomp)) @ M
        feet['Left'] = M   # the lifted foot still enters the pelvis solve: no height pop at lift-off
    return stand(b, -0.03 * c.stomp, 0.0, hrot, J, drop=c.drop + bob + 0.03 * c.jolt, feet=feet, free=free,
                 curl={'Left': (0.35 * a, 0.2 * a), 'Right': (c.fist, c.fist)})


# ---- Cop_Aim_Raise / Cop_Aim: two-handed pistol pose (no prop), upper-body friendly
AIM_T = 2.0
RAISE_T = 0.5


def aim_targets(body, t, ch):
    """Wrist targets for the hold pose with a slow aim drift and the re-grip beat."""
    drift = Vector((0.012 * ch.ax, 0.0, 0.010 * ch.az))
    rg = ch.regrip
    rw = Vector((-0.05, -0.398, 1.21)) + drift + Vector((0, 0.03 * rg, -0.02 * rg))
    lw = Vector((0.02, -0.355, 1.17)) + drift + Vector((0.03 * rg, 0.06 * rg, -0.05 * rg))
    return rw, lw


def aim_arms(body, t, ch, w=1.0):
    rw, lw = aim_targets(body, t, ch)
    rq = R(Z, -8) @ R(X, -82) @ R(Y, 6)
    lq = R(Z, 22) @ R(X, -70) @ R(Y, -20)
    return {'Right': (rw, rq, Vector((-0.6, 0.3, -1.0))), 'Left': (lw, lq, Vector((0.7, 0.2, -1.0)))}


def aim_hold_chan():
    T = AIM_T
    per = lambda *k: E.Curve(list(k), periodic=True)
    return Chan(
        breath=per((0, 0), (0.6, 1), (1.4, 0.1), (T, 0)),
        ax=per((0, 0), (0.5, 0.8), (0.9, 0.3), (1.25, -0.9), (1.6, -0.2), (T, 0)),
        az=per((0, 0), (0.45, -0.6), (1.0, 0.5), (1.35, -0.4), (T, 0)),
        regrip=per((0, 0), (1.0, 0), (1.08, 1), (1.2, 1), (1.32, 0), (T, 0)),
        squint=per((0, 0), (0.95, 0), (1.15, -1), (1.45, 0), (T, 0)),
        sway=per((0, 0), (0.8, 1), (1.6, -0.6), (T, 0)),
    )


def aim_body(ctx, t, ch, w=1.0, raise_ch=None):
    """w blends Idle -> aim stance (1 = hold)."""
    J = {}
    lean = 5 * w
    spine(J, pitch=lean - 1.0 * ch.breath, roll=1.5 * ch.sway * w, yaw=-4 * w)
    head(J, pitch=9 * w + 2 * ch.squint, roll=-7 * w + 3 * ch.squint, yaw=3 * w, neck=0.35)
    arm(J, 'Left', sh_up=3 * ch.breath)
    arm(J, 'Right', sh_up=3 * ch.breath)
    hrot = R(Z, -3 * w) @ R(X, 2 * w)
    return J, hrot


def aim_pose(ctx, t):
    ch = ctx.ch(t)
    b = ctx.body
    J, hrot = aim_body(ctx, t, ch)
    arms = aim_arms(b, t, ch)
    pn = 0.0
    return stand(b, 0.006 * ch.sway, 0.01, hrot, J, drop=0.035 + 0.004 * ch.breath, arms=arms,
                 curl={'Right': (0.8, 0.55, {'Index': 0.12}), 'Left': (0.62, 0.5)}, splay=0.25)


def raise_chan():
    return Chan(w=K((0, 0), (0.06, 0.05), (0.30, 0.95), (0.38, 1.04), (RAISE_T, 1.0)),
                hy=K((0, 0), (RAISE_T, 0.01)), drop=K((0, 0), (0.25, 0.045), (RAISE_T, 0.035)))


class AimCtx:
    def __init__(self, B, cache):
        self.B = B
        self.body = E.Body(B)
        self.ch = aim_hold_chan()
        self.rch = raise_chan()
        if 'aim_frame1' not in cache:
            out, _ = aim_pose(self, 0.0)
            cache['aim_frame1'] = B.values_from_pose(out)
        self.aim_values = cache['aim_frame1']


def raise_pose(ctx, t):
    """Idle -> aim hold frame 1. The arms are blended bone by bone from Idle FK to the hold IK."""
    b = ctx.body
    r = ctx.rch(t)
    w = clamp(r.w, 0.0, 1.2)
    ch = ctx.ch(0.0)
    J, hrot = aim_body(ctx, 0.0, ch, w=min(w, 1.0))
    hold, _ = aim_pose(ctx, 0.0)
    out, info = stand(b, 0.006 * ch.sway * w, r.hy, hrot, J, drop=r.drop, splay=0.12 + 0.13 * min(w, 1))
    # arms: hierarchical blend of the local bone transforms Idle -> hold, with a swing arc
    ws = smooth(min(w, 1.0))
    over = max(0.0, w - 1.0)
    for s in SIDES:
        E.blend_subtree(ctx.B, out, hold, s + 'Shoulder', ws)
        if over:
            E.blend_subtree(ctx.B, out, hold, s + 'Arm', 1.0)
            ctx.B.rotate_subtree(out, s + 'Arm', R(X, 25 * over))
    return out, info


def aim_canonical(ctx, frames, N):
    v = ctx.aim_values
    return {1.0: v, float(N + 1): v}


def raise_canonical(ctx, frames, N):
    return {1.0: ctx.B.idle_values, float(N + 1): ctx.aim_values}


CLIPS['Cop_Punch'] = _stand_spec(1.0, punch_chan, punch_pose, [
    '0.00-0.08 small dip, fists clench', '0.08-0.30 big telegraphed wind-up: body twists 30 deg to his right and leans back, right fist cocked by the ear, left arm points at the target',
    '0.30-0.345 straining hold (quiver)', '0.345-0.45 the punch snaps out at constant speed, body unwinds, hips lunge forward 5.5 cm',
    '0.45 HIT (full extension, frame 14.5)', '0.45-0.64 follow-through overshoot and hold', '0.64-1.00 recover into Idle frame 1'],
    events={'Hit': PUNCH_HIT})
CLIPS['Cop_ShakeFist'] = _stand_spec(SHAKE_T, shake_chan, shake_pose, [
    '0.00-0.25 gathers rage: crouch, lean back, fists clench', '0.25-0.45 right fist thrusts up overhead, chest forward, chin out (yelling)',
    '0.50-1.45 fist shakes at 4.6 Hz, body bounces, head jabs with every shake; left hand on hip', '0.95-1.15 left foot stamps (exact Idle spot), body jolts',
    '1.55-1.70 one last big wind-up and thrust', '1.80-2.10 deflates: arm drops, shoulders slump, "no-no" head shake', '2.10-2.20 settles into Idle frame 1'])
CLIPS['Cop_Aim'] = {'T': AIM_T, 'loop': True, 'stage': 'stand', 'setup': AimCtx, 'pose': aim_pose,
                    'canonical': aim_canonical, 'start': 'aim hold pose (= Cop_Aim_Raise last frame)', 'end': 'frame 1 (exact seam)',
                    'beats': ['two-handed pistol pose (no prop), elbows soft, knees bent, head tilted to sight with one eye',
                              'breathing, a slow aim drift (wrists move together)', '1.0-1.3 nervous re-grip: support hand slides off and back, squint',
                              '2.0 seam = frame 1'], 'events': {}}
CLIPS['Cop_Aim_Raise'] = {'T': RAISE_T, 'loop': False, 'stage': 'stand', 'setup': AimCtx, 'pose': raise_pose,
                          'canonical': raise_canonical, 'start': 'Idle frame 1 (exact)', 'end': 'Cop_Aim frame 1 (exact)',
                          'beats': ['0.00-0.06 settle', '0.06-0.30 arms swing up into the grip, knees bend, head drops to the sights',
                                    '0.30-0.38 small overshoot (arms 4% past)', '0.38-0.50 settles exactly on Cop_Aim frame 1'], 'events': {}}


# ============================================================================= Cop_Trip
TRIP_T = 22 / 30
TRIP_SNAG = 0.14          # right toe catches under the body
TRIP_RELEASE = 0.24       # toe drags back with the ground, then the leg flies up behind
TRIP_LAND = 0.40          # desperate stumble step with the left foot
TRIP_PUSH = 0.62          # ...which pushes off into the dive


def trip_chan():
    return Chan(
        w=K((0, 0), (0.06, 0), (0.30, 1), (TRIP_T, 1)),
        hy=K((0, 0), (0.14, 0.0), (0.40, -0.12), (0.60, -0.26), (TRIP_T, -0.36, ('auto', 'lin'))),
        hz=K((0, 0.70), (0.14, 0.69), (0.30, 0.66), (0.42, 0.60), (0.56, 0.55), (TRIP_T, 0.44, ('auto', 'lin'))),
        pitch=K((0, 0), (0.14, 2), (0.30, 18), (0.45, 40), (0.60, 60), (TRIP_T, 76, ('auto', 'lin'))),
        arch=K((0, 0), (0.18, -6), (0.40, -14), (0.60, -6), (TRIP_T, 4)),
        look=K((0, 0), (0.16, -10), (0.35, -40), (0.55, -55), (TRIP_T, -62)),
        mill=K((0, 0), (0.14, 0), (0.30, 1), (0.48, 1), (0.58, 0), (TRIP_T, 0)),
        brace=K((0, 0), (0.44, 0), (0.62, 1), (TRIP_T, 1)),
        roll=K((0, 0), (0.25, -4), (0.5, 6), (TRIP_T, 3)),
    )


class TripCtx(RunCtx):
    def __init__(self, B, cache):
        RunCtx.__init__(self, B, RUN)
        self.ch = trip_chan()
        p = RUN
        # the right foot in the plain run at the snag time: its toe tip, lowered to the floor, is the snag point
        M, _ = self.legs['Right']((TRIP_SNAG / p.T + 0.5) % 1.0)
        toe = self.legs['Right'].point(M, 'toe')
        self.snag = Vector((toe.x, toe.y, 0.0))
        self.snag_M = M
        self.snag_drop = toe.z
        # left stumble-step touchdown (heel), far forward
        self.left_td_y = -0.30


def trip_mod_factory(ctx):
    b = ctx.body
    p = RUN
    v = p.v

    def right_leg(t):
        L = ctx.legs['Right']
        if t <= TRIP_SNAG:
            M, toe = L((t / p.T + 0.5) % 1.0)
            k = smooth((t - 0.06) / (TRIP_SNAG - 0.06))     # dip the swinging foot so the toe scuffs the floor
            return Matrix.Translation((0, 0, -ctx.snag_drop * k)) @ M, toe
        M0 = Matrix.Translation((0, 0, -ctx.snag_drop)) @ ctx.snag_M
        piv0 = L.point(M0, 'toe')
        if t <= TRIP_RELEASE:   # caught: the toe tip rides the ground while the foot tips up (heel rises)
            k = (t - TRIP_SNAG) / (TRIP_RELEASE - TRIP_SNAG)
            piv = piv0 + Vector((0, v * (t - TRIP_SNAG), 0))
            lat = M0.to_3x3() @ b.F0['Right'].to_3x3().inverted() @ Vector(X)
            # (+11 mm: the rounded toe cap in front of the pivot would otherwise dip into the street)
            return Matrix.Translation(piv - piv0 + Vector((0, 0, 0.011 * smooth(k)))) @ E.rot_about(piv0, R(lat, 35 * smooth(k))) @ M0, 0.0
        # released: the trailing leg flies up behind as the body pitches forward
        Mr, _ = right_leg(TRIP_RELEASE)
        u = (t - TRIP_RELEASE) / (TRIP_T - TRIP_RELEASE)
        k = smooth(u)
        # keeps riding back with the ground for a moment while the toe pops up, then swings up behind
        pos = Mr.translation + Vector((0, v * (t - TRIP_RELEASE) * (1 - k) + 0.10 * k, 0.40 * (0.5 * u + 0.5 * k)))
        hip = d_now['hips'] + d_now['hrot'] @ Vector((-0.1, 0.0, -0.02))
        dv = pos - hip
        if dv.length > 0.97 * b.Lleg:            # airborne: never ask for more than the leg can reach
            pos = hip + dv.normalized() * 0.97 * b.Lleg
        rot = R(X, 50 * k).to_matrix() @ Mr.to_3x3()
        M = rot.to_4x4()
        M.translation = pos
        return M, 0.0

    def left_leg(t):
        L = ctx.legs['Left']
        t_off = p.c * p.T                       # normal run lift-off of the left foot
        if t <= t_off:
            return L(t / p.T)
        M0, toe0 = L.stance(p.c)
        # stance of the stumble step
        def stance(tt):
            gy = ctx.left_td_y + v * (tt - TRIP_LAND)
            M = L.flat(gy)
            lat = R(Z, L.yaw) @ Vector(X)
            if tt < TRIP_LAND + 0.035:
                a = -10 * (1 - smooth((tt - TRIP_LAND) / 0.035))
                return E.rot_about(L.point(M, 'heel'), R(lat, a)) @ M, 0.0
            if tt < 0.52:
                return M, 0.0
            a = 45 * smooth((tt - 0.52) / (TRIP_PUSH - 0.52))
            return E.rot_about(L.point(M, 'mtp'), R(lat, a)) @ M, a
        if t >= TRIP_PUSH:     # pushes off into the dive: the foot leaves the street and trails behind
            Mp, ap = stance(TRIP_PUSH)
            u = (t - TRIP_PUSH) / (TRIP_T - TRIP_PUSH)
            pos = Mp.translation + Vector((0, v * (t - TRIP_PUSH) * (1 - 0.5 * u), 0.22 * u))
            hip = d_now['hips'] + d_now['hrot'] @ Vector((0.1, 0.0, -0.02))
            dv = pos - hip
            if dv.length > 0.97 * b.Lleg:
                pos = hip + dv.normalized() * 0.97 * b.Lleg
            M = (R(X, 25 * u).to_matrix() @ Mp.to_3x3()).to_4x4()
            M.translation = pos
            return M, ap * (1 - u)
        if t >= TRIP_LAND:
            return stance(t)
        M1, _ = stance(TRIP_LAND)
        s = (t - t_off) / (TRIP_LAND - t_off)
        Ts = TRIP_LAND - t_off
        p0, p1 = M0.translation, M1.translation
        v0, v1 = Vector((0, v, 0.9)), Vector((0, v * 0.3, -1.4))
        pos = Vector([E.hermite(p0[i], v0[i], p1[i], v1[i], Ts, s) for i in range(3)])
        pos.z += 0.16 * math.sin(math.pi * s) ** 1.3
        q0, q1 = M0.to_quaternion(), M1.to_quaternion()
        if q0.dot(q1) < 0:
            q1.negate()
        q = q0.slerp(q1, smooth(s))
        M = q.to_matrix().to_4x4()
        M.translation = pos
        return M, toe0 * (1 - smooth(s / 0.4))

    d_now = {}

    def mod(t, d):
        d_now.update(d)
        c = ctx.ch(t)
        w = c.w
        d['hips'] = d['hips'].lerp(Vector((d['hips'].x * (1 - w), c.hy, c.hz)), w) if t > 0.08 else d['hips']
        trip_rot = R(Y, c.roll) @ R(X, c.pitch)
        q0 = d['hrot']
        d['hrot'] = q0.slerp(trip_rot, w) if w > 0 else q0
        J = d['J']
        T = {}
        spine(T, pitch=c.arch, roll=0.5 * c.roll)
        head(T, pitch=c.look - 0.35 * c.pitch, neck=0.45)
        m = c.mill
        for s, ph in (('Left', 0.0), ('Right', math.pi)):
            sg = SGN[s]
            ang = 360 * 2.0 * (t - 0.12) + math.degrees(ph)       # windmill (+ = forward over the top)
            fwd = (1 - c.brace) * (m * (60 + 70 * math.sin(math.radians(ang))) + (1 - m) * 30) + c.brace * (95 - 0.4 * c.pitch)
            arm(T, s, fwd=fwd, out=25 + 25 * m, elbow=(1 - c.brace) * 25 + c.brace * 15, wrist=-20 * c.brace, sh_up=10 * m)
        for n in set(J) | set(T):
            a = J.get(n, QI())
            bq = T.get(n, QI())
            if a.dot(bq) < 0:
                bq = -bq
            J[n] = a.slerp(bq, w)
        d_now.update(d)
        lm, lt = left_leg(t)
        rm, rt = right_leg(t)
        d['legs'] = {'Left': lm, 'Right': rm}
        d['toes'] = {'Left': lt, 'Right': rt}
        op = 1 - c.brace
        d['curl'] = {sd: (p.fist * (1 - w) + w * (0.2 * op - 0.2 * c.brace), 0.8 * (1 - w)) for sd in SIDES}
    return mod


def trip_pose(ctx, t):
    if not hasattr(ctx, 'mod'):
        ctx.mod = trip_mod_factory(ctx)
    return run_pose(ctx, t, mod=ctx.mod)


def trip_canonical(ctx, frames, N):
    """Frame 1 = Cop_Run frame 1 exactly (same authoring function at t = 0)."""
    return {1.0: ctx.B.values_from_pose(run_pose(ctx, 0.0)[0])}


CLIPS['Cop_Trip'] = {
    'T': TRIP_T, 'loop': False, 'stage': 'stand', 'setup': TripCtx, 'pose': trip_pose, 'canonical': trip_canonical,
    'ground': lambda t: RUN.v * t, 'ground_note': 'in place; ground +Y at %.2f m/s (same as Cop_Run); hips advance 0.36 m in the dive' % RUN.v,
    'start': 'Cop_Run frame 1 (exact)', 'end': 'ragdoll hand-off pose (diving, airborne except the left toe)',
    'events': {'Ragdoll': TRIP_T},
    'beats': ['0.00-0.14 normal heavy run (identical to Cop_Run)', '0.14 the right toe catches the street under the body',
              '0.14-0.24 the toe is dragged back with the ground, heel tips up; the body starts to pitch forward',
              '0.12-0.48 arms windmill, head snaps up looking ahead (uh-oh), back arches',
              '0.19-0.40 desperate long stumble step with the left foot', '0.40-0.72 diving: body pitches to 76 deg, arms reach forward to brace',
              '0.733 hand off to the ragdoll (hips 0.44 m, still moving forward/down)']}
