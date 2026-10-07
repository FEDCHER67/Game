"""Escape-set clips: Hit_React_Front/Back/Head, Stagger, Struggle_Carried, Escape_Scramble_Start,
Escape_Scramble (loop), JumpOut. See ep_core.py for the conventions."""
import math
from mathutils import Vector, Matrix, Quaternion
import ep_core as E
from ep_core import (R, QI, Curve, P, X, Y, Z, SIDES, SGN, smooth, smoother, clamp, lerp, win, bump, K, Chan, stand,
                     arm, spine, head, idle_canonical, step_arc, pnoise)

CLIPS = {}


class StandCtx:
    def __init__(self, B, chan_fn):
        self.B = B
        self.body = E.Body(B)
        self.ch = chan_fn()


def _spec(T, chan_fn, pose_fn, beats, events=None, **kw):
    d = {'T': T, 'loop': False, 'stage': 'stand', 'setup': lambda B, cache: StandCtx(B, chan_fn),
         'pose': pose_fn, 'canonical': idle_canonical, 'beats': beats, 'events': events or {},
         'start': 'Idle frame 1 (exact)', 'end': 'Idle frame 1 (exact)'}
    d.update(kw)
    return d


def wob(t, t0, f, decay, amp=1.0):
    """Decaying wobble starting at t0 (zero before)."""
    if t <= t0:
        return 0.0
    u = t - t0
    return amp * math.sin(2 * math.pi * f * u) * math.exp(-decay * u)


# ============================================================================= Hit_React_Front (belly punch: "OOF")
HF_T = 0.8


def hf_chan():
    return Chan(
        pitch=K((0, 0), (0.06, 24, ('lin', 'auto')), (0.14, 36), (0.30, 30), (0.45, 8), (0.56, -5), (0.68, 1), (HF_T, 0)),
        hy=K((0, 0), (0.06, 0.05, ('lin', 'auto')), (0.14, 0.065), (0.34, 0.045), (0.55, -0.01), (0.7, 0.002), (HF_T, 0)),
        drop=K((0, 0), (0.06, 0.035), (0.16, 0.085), (0.34, 0.065), (0.55, 0.0), (0.66, 0.008), (HF_T, 0)),
        neck=K((0, 0), (0.04, -10), (0.11, 20), (0.22, 10), (0.45, -8), (0.6, 3), (HF_T, 0)),
        fwd=K((0, 0), (0.06, 50), (0.16, 34), (0.36, 30), (0.58, 4), (HF_T, 0)),
        elb=K((0, 0), (0.06, 18), (0.17, 100), (0.38, 96), (0.60, 12), (HF_T, 0)),
        sw=K((0, 0), (0.06, 5), (0.17, 34), (0.38, 32), (0.6, 4), (HF_T, 0)),
        curl=K((0, 0), (0.06, -0.1), (0.17, 0.6), (0.4, 0.6), (0.65, 0.05), (HF_T, 0)),
        sh=K((0, 0), (0.08, 12), (0.3, 8), (0.55, -3), (HF_T, 0)),
    )


def hf_pose(ctx, t):
    c = ctx.ch(t)
    J = {}
    w = wob(t, 0.12, 3.0, 5.0, 4.0) * (1 - win(t, 0.6, HF_T))
    spine(J, pitch=c.pitch, roll=w, w=(0.25, 0.4, 0.35))
    head(J, pitch=c.neck - 0.3 * c.pitch, roll=-1.5 * w, neck=0.5)
    for s in SIDES:
        arm(J, s, fwd=c.fwd, swing=c.sw, elbow=c.elb, sh_up=c.sh, out=-6 * win(t, 0.1, 0.2) * (1 - win(t, 0.4, 0.6)),
            twist=-20 * c.elb / 100, wrist=15 * c.curl)
    hrot = R(X, -0.35 * c.pitch) @ R(Y, 0.5 * w)
    cur = (c.curl, 0.5 * c.curl)
    return stand(ctx.body, 0.0, c.hy, hrot, J, drop=c.drop, curl={'Left': cur, 'Right': cur})


# ============================================================================= Hit_React_Back (kicked in the butt)
HB_T = 23 / 30


def hb_chan():
    return Chan(
        pitch=K((0, 0), (0.05, -20, ('lin', 'auto')), (0.12, -27), (0.26, -10), (0.40, 7), (0.54, -2), (0.64, 0.5), (HB_T, 0)),
        hy=K((0, 0), (0.05, -0.06, ('lin', 'auto')), (0.12, -0.08), (0.30, -0.035), (0.48, 0.006), (HB_T, 0)),
        drop=K((0, 0), (0.05, 0.0), (0.13, 0.03), (0.30, 0.05), (0.50, 0.008), (HB_T, 0)),
        neck=K((0, 0), (0.04, 12), (0.10, -24), (0.20, -10), (0.33, 12), (0.46, -3), (0.6, 1), (HB_T, 0)),
        fwd=K((0, 0), (0.05, -30), (0.12, -48), (0.24, -26), (0.40, -38), (0.55, -14), (HB_T, 0)),
        out=K((0, 0), (0.06, 28), (0.14, 34), (0.30, 16), (0.5, 8), (HB_T, 0)),
        elb=K((0, 0), (0.06, 10), (0.15, 25), (0.32, 70), (0.46, 64), (0.62, 8), (HB_T, 0)),
        tw=K((0, 0), (0.15, 0), (0.32, -40), (0.46, -40), (0.62, 0), (HB_T, 0)),
        spread=K((0, 0), (0.06, -0.25), (0.25, -0.2), (0.4, 0.2), (0.6, 0), (HB_T, 0)),
        rub=K((0, 0), (0.30, 0), (0.36, 1), (0.48, 1), (0.56, 0), (HB_T, 0)),
    )


def hb_pose(ctx, t):
    c = ctx.ch(t)
    J = {}
    rubw = c.rub * math.sin(2 * math.pi * 7 * (t - 0.3))
    spine(J, pitch=c.pitch, roll=3 * rubw * c.rub, w=(0.3, 0.35, 0.35))
    head(J, pitch=c.neck - 0.4 * c.pitch, yaw=-12 * c.rub, neck=0.5)
    for s in SIDES:
        arm(J, s, fwd=c.fwd, out=c.out, elbow=c.elb, twist=c.tw, wrist=-10 * c.rub + 8 * rubw * SGN[s], sh_up=-0.2 * c.pitch)
    hrot = R(X, 0.45 * c.pitch) @ R(Z, 4 * rubw)
    cur = (c.spread, 0.6 * abs(c.spread))
    return stand(ctx.body, 0.0, c.hy, hrot, J, drop=c.drop, curl={'Left': cur, 'Right': cur})


# ============================================================================= Hit_React_Head (bonk on the top)
HH_T = 0.9


def hh_chan():
    return Chan(
        neck=K((0, 0), (0.04, 22, ('lin', 'auto')), (0.10, 26), (0.22, 4), (0.30, 10), (0.7, 6), (0.8, 0), (HH_T, 0)),
        sh=K((0, 0), (0.05, 24, ('lin', 'auto')), (0.12, 26), (0.26, 10), (0.65, 8), (0.82, 0), (HH_T, 0)),
        drop=K((0, 0), (0.06, 0.045), (0.12, 0.09), (0.23, 0.03), (0.36, 0.05), (0.6, 0.035), (0.8, 0.0), (HH_T, 0)),
        pitch=K((0, 0), (0.08, 12), (0.24, 2), (0.6, 4), (HH_T, 0)),
        # arms: jerk out (jazz hands), then both hands clutch the top of the head, then down
        out=K((0, 0), (0.06, 40), (0.14, 46), (0.26, 30), (0.62, 30), (0.80, 4), (HH_T, 0)),
        fwd=K((0, 0), (0.06, 10), (0.14, 30), (0.28, 70), (0.62, 70), (0.80, 10), (HH_T, 0)),
        elb=K((0, 0), (0.06, 10), (0.14, 40), (0.28, 130), (0.62, 130), (0.80, 10), (HH_T, 0)),
        tw=K((0, 0), (0.14, 0), (0.28, 30), (0.62, 30), (0.80, 0), (HH_T, 0)),
        spread=K((0, 0), (0.06, -0.3), (0.16, -0.25), (0.28, 0.25), (0.62, 0.25), (0.8, 0), (HH_T, 0)),
        dizzy=K((0, 0), (0.24, 0), (0.32, 1), (0.6, 1), (0.78, 0), (HH_T, 0)),
        hold=K((0, 0), (0.11, 0), (0.30, 1), (0.62, 1), (0.80, 0), (HH_T, 0)),
    )


def hh_pose(ctx, t):
    c = ctx.ch(t)
    J = {}
    ph = 2 * math.pi * 3.2 * (t - 0.24)
    dz = c.dizzy
    spine(J, pitch=c.pitch, roll=4 * dz * math.sin(ph), yaw=3 * dz * math.cos(ph))
    head(J, pitch=c.neck + 6 * dz * math.cos(ph), roll=10 * dz * math.sin(ph), yaw=5 * dz * math.sin(2 * ph), neck=0.5)
    for s in SIDES:
        arm(J, s, fwd=c.fwd, out=c.out, elbow=c.elb, twist=c.tw, sh_up=c.sh, wrist=-25 * win(t, 0.18, 0.3) * (1 - win(t, 0.6, 0.78)))
    hrot = R(Y, 3 * dz * math.sin(ph))
    cur = (c.spread, 0.6 * abs(c.spread))
    b = ctx.body
    posts = [E.ik_arm_post(b, s, HH_HANDS[s], t, c.hold, anchor='Head', frame=True) for s in SIDES]
    return stand(b, 0.01 * dz * math.sin(ph), 0.0, hrot, J, drop=c.drop, curl={'Left': cur, 'Right': cur},
                 post=lambda out: [p(out) for p in posts])


# hands clutch the sides of the big head (offsets from the Head joint, in the head's frame)
HH_HANDS = {s: E.Path3([(0.0, (SGN[s] * 0.15, -0.06, 0.13), R(Y, -SGN[s] * 15) @ R(X, -165), ('h', 0.0, 1.0, 0.0)),
                        (1.0, (SGN[s] * 0.15, -0.06, 0.13), R(Y, -SGN[s] * 15) @ R(X, -165), ('h', 0.0, 1.0, 0.0))])
            for s in SIDES}


# ============================================================================= Stagger (dazed, 1.4 s)
ST_T = 1.4


def st_chan():
    return Chan(
        # pelvis wanders over the stepping feet and comes home
        hx=K((0, 0), (0.18, -0.05), (0.38, -0.085), (0.58, 0.05), (0.80, 0.03), (1.0, -0.02), (1.18, 0.008), (ST_T, 0)),
        hy=K((0, 0), (0.18, -0.02), (0.40, -0.06), (0.62, -0.13), (0.80, -0.10), (1.0, -0.03), (1.2, 0.005), (ST_T, 0)),
        drop=K((0, 0), (0.12, 0.03), (0.32, 0.06), (0.50, 0.035), (0.66, 0.08), (0.84, 0.05), (1.06, 0.03), (1.25, 0.004), (ST_T, 0)),
        lean_r=K((0, 0), (0.16, -8), (0.38, -12), (0.56, 9), (0.74, 6), (0.95, -4), (1.15, 1), (ST_T, 0)),
        lean_f=K((0, 0), (0.2, 4), (0.42, 2), (0.64, 16), (0.78, 10), (0.98, -4), (1.18, 1), (ST_T, 0)),
        dizzy=K((0, 0), (0.1, 1), (1.1, 1), (1.32, 0), (ST_T, 0)),
        arms=K((0, 0), (0.2, 0.4), (0.55, 1), (0.85, 1), (1.15, 0.2), (ST_T, 0)),
        mill=K((0, 0), (0.52, 0), (0.62, 1), (0.82, 1), (0.95, 0), (ST_T, 0)),
        soft=K((0, 0), (0.12, 1), (1.24, 1), (ST_T, 0)),      # knees never snap through straight mid-clip
    )


def st_feet(body, t):
    """Steps: right foot out to his right, left crosses over, right lurches forward, then both come home."""
    F0 = body.F0
    def at(s, dx, dy, yaw=0.0):
        return Matrix.Translation((dx, dy, 0.0)) @ E.rot_about(body.pivot0[s]['ankle'], R(Z, yaw)) @ F0[s]
    R1 = at('Right', -0.13, -0.06, -14)
    L1 = at('Left', -0.07, -0.16, 10)
    R2 = at('Right', -0.02, -0.30, -6)
    L2 = at('Left', 0.02, -0.08, 4)
    steps = {'Right': [(0.14, 0.32, F0['Right'], R1, 0.07), (0.54, 0.70, R1, R2, 0.09), (0.94, 1.12, R2, F0['Right'], 0.07)],
             'Left': [(0.34, 0.52, F0['Left'], L1, 0.08), (0.74, 0.90, L1, L2, 0.06), (1.10, 1.26, L2, F0['Left'], 0.06)]}
    feet, free = {}, []
    for s in SIDES:
        M = F0[s]
        for t0, t1, a, b, lift in steps[s]:
            if t >= t0:
                M, moving = step_arc(a, b, t, t0, t1, lift=lift, pitch=8)
                if moving:
                    free.append(s)
        feet[s] = M
    return feet, tuple(free)


def st_pose(ctx, t):
    c = ctx.ch(t)
    J = {}
    dz = c.dizzy
    ph = 2 * math.pi * 1.6 * t
    spine(J, pitch=c.lean_f + 3 * dz * math.sin(ph), roll=c.lean_r + 5 * dz * math.cos(ph))
    head(J, pitch=6 * dz * math.sin(ph + 0.8) - 0.3 * c.lean_f, roll=-0.6 * c.lean_r + 12 * dz * math.cos(ph + 0.8),
         yaw=8 * dz * math.sin(2 * ph), neck=0.5)
    m = c.mill
    for s in SIDES:
        sg = SGN[s]
        # loose dangling arms that drift out for balance; a short windmill on the forward lurch
        out = c.arms * (22 + 10 * sg * math.sin(math.radians(c.lean_r) * 6)) + 8 * dz * math.sin(ph + sg)
        fwd = 15 * c.arms * math.sin(ph * 0.5 + sg) + m * 70 * math.sin(2 * math.pi * 3.0 * (t - 0.52) + (0 if s == 'Left' else math.pi))
        arm(J, s, fwd=fwd, out=out, elbow=20 * c.arms + 25 * m, wrist=10 * dz * math.sin(ph * 1.5 + sg))
    feet, free = st_feet(ctx.body, t)
    hrot = R(Y, -0.4 * c.lean_r) @ R(X, 0.25 * c.lean_f) @ R(Z, 6 * dz * math.sin(ph * 0.7))
    return stand(ctx.body, c.hx, c.hy, hrot, J, drop=c.drop, feet=feet, free=(), support=1 - 0.02 * c.soft ** 2,
                 curl={'Left': (0.15 * c.arms, 0.1 * c.arms), 'Right': (0.15 * c.arms, 0.1 * c.arms)})


CLIPS['Hit_React_Front'] = _spec(HF_T, hf_chan, hf_pose, [
    '0.00-0.06 belly hit: snaps into a fold ("OOF"), butt shoots back 5 cm, arms fly forward', '0.06-0.16 head whips down after the chest (lag), knees buckle 8.5 cm',
    '0.16-0.40 hugs the belly, wobbling', '0.40-0.68 straightens with a small overshoot backward', '0.68-0.80 settles into Idle frame 1'])
CLIPS['Hit_React_Back'] = _spec(HB_T, hb_chan, hb_pose, [
    '0.00-0.05 kicked from behind: hips shoot forward 6-8 cm, back arches, arms fly back with spread fingers', '0.04-0.20 head lags then whips back',
    '0.30-0.50 hands rub the sore butt / lower back, small wiggle', '0.50-0.75 straightens into Idle frame 1'])
CLIPS['Hit_React_Head'] = _spec(HH_T, hh_chan, hh_pose, [
    '0.00-0.05 bonk: head jams down, shoulders shrug up (turtle), knees buckle 9.5 cm', '0.05-0.14 hands jerk out (jazz hands)',
    '0.14-0.30 both hands clutch the top of the head', '0.30-0.62 dizzy head wobble with the hands on the head', '0.62-0.90 hands down, settles into Idle frame 1'])
CLIPS['Stagger'] = _spec(ST_T, st_chan, st_pose, [
    '0.00-0.14 dizzy sway starts, arms drift out', '0.14-0.32 right foot stumbles out to his right', '0.34-0.52 left foot crosses over in front',
    '0.54-0.70 lurches forward onto the right foot, arms windmill', '0.74-0.90 left foot catches up', '0.94-1.26 both feet shuffle back onto their exact Idle spots',
    '1.26-1.40 settles into Idle frame 1'])


# ============================================================================= Struggle_Carried (additive-friendly loop)
SC_T = 1.6


def sin_t(k, t, ph=0.0):
    """sin with k whole cycles per loop, shifted so it is exactly 0 at t = 0 and t = T."""
    return math.sin(2 * math.pi * k * t / SC_T + ph) - math.sin(ph)


def notch(t, w=0.25):
    """1 away from the seam, smoothly 0 at t = 0 / T (C1)."""
    d = min(t, SC_T - t)
    return smooth(d / w)


def sq_t(k, t, ph=0.0):
    """Non-negative bump train (k cycles per loop), exactly 0 at the seam: (1 - cos) / 2 shape.
    Phase-shifted trains are faded by a short notch at the seam instead of being offset (an offset
    would turn part of the bump negative: a knee bending backward, a leg kicking the wrong way)."""
    x = 2 * math.pi * k * t / SC_T + ph
    v = 0.5 * (1 - math.cos(x))
    return v if abs(math.sin(ph / 2)) < 1e-9 else v * notch(t)


def sc_pose(ctx, t):
    """Kicking and wriggling while held up by the torso. Frame 1 = Idle frame 1 exactly (the additive
    reference pose); every channel is a sum of whole-cycle sines that are 0 at the seam, so the pose
    only sweeps through Idle there, it never stops on it. Hips do not translate (additive-safe)."""
    b = ctx.body
    J = {}
    # torso: wriggle (yaw), squirm (roll), curl / arch (pitch)
    yaw = 20 * sin_t(2, t) + 6 * sin_t(5, t, 0.7)
    roll = 9 * sin_t(3, t, 0.3)
    pitch = 8 * sin_t(1, t) + 6 * sin_t(4, t, 1.1)
    spine(J, pitch=pitch, roll=roll, yaw=yaw)
    head(J, pitch=-0.5 * pitch + 8 * sin_t(3, t, 2.0), roll=-0.7 * roll + 6 * sin_t(5, t, 0.4),
         yaw=-0.6 * yaw + 18 * sin_t(3, t, 1.4), neck=0.5)
    hrot = R(Z, -0.4 * yaw) @ R(Y, -0.3 * roll) @ R(X, -0.25 * pitch)
    # legs: alternating bicycle kicks (4 per loop, left and right in antiphase) + one big double kick
    for s, ph in (('Left', 0.0), ('Right', math.pi)):
        sg = SGN[s]
        # tuck-and-piston: the knee folds while the thigh comes up, then the shin shoots out (kick)
        kick = 62 * sq_t(4, t, ph) + 8 * sin_t(8, t, ph + 0.5) - 10 * sq_t(2, t, ph + 2.0)
        bend = 105 * sq_t(4, t, ph + 1.4) + 10 * sq_t(8, t, ph)
        J[s + 'UpLeg'] = R(X, -kick) @ R(Y, -sg * (10 * sq_t(2, t, ph + 0.4) + 5 * sin_t(3, t)))
        J[s + 'Leg'] = R(X, bend)
        J[s + 'Foot'] = R(X, 25 * sin_t(4, t, ph + 2.2))
    # arms: flailing / pushing at the holder, out of phase with the kicks
    for s, ph in (('Left', 0.6), ('Right', 0.6 + math.pi)):
        sg = SGN[s]
        arm(J, s, fwd=85 * sq_t(4, t, ph) + 25 * sin_t(2, t, ph), out=35 * sq_t(3, t, ph + 1.0) + 10 * sin_t(5, t, ph),
            elbow=95 * sq_t(4, t, ph + 1.8), twist=15 * sin_t(2, t, ph), sh_up=10 * sq_t(4, t, ph), wrist=20 * sin_t(4, t, ph + 0.9))
    fist = 0.8 * sq_t(2, t, 0.0)
    out, info = b.pose(b.hips0, hrot, J, legs={}, curl={'Left': (fist, fist), 'Right': (fist, fist)})
    return out, info


CLIPS['Struggle_Carried'] = {
    'T': SC_T, 'loop': True, 'stage': 'air', 'setup': lambda B, cache: StandCtx(B, lambda: None), 'pose': sc_pose,
    'canonical': idle_canonical, 'floor_offset': -0.8, 'floor': lambda x, y, t: -10.0,   # held in the air: no floor
    'start': 'Idle frame 1 (exact; additive reference pose)', 'end': 'frame 1 (exact seam)',
    'beats': ['bicycle kicks, 4 per leg per loop (2.5 Hz), legs in antiphase, knees snap', 'torso wriggles (yaw 2 cycles), squirms (roll 3), curls/arches (pitch 1+4)',
              'arms flail and shove at the holder out of phase with the legs; fists clench twice per loop', 'head thrashes against the body motion',
              'hips never translate; frame 1 = Idle frame 1 = additive reference'], 'events': {}}


# ============================================================================= Escape_Scramble (crawl loop, van bay)
class CrawlP:
    T = 0.5            # one full crawl cycle (both diagonals)
    v = 1.2            # ground (van floor) speed under the in-place crawl, m/s
    knee_r = 0.04     # knee joint centre above the floor when the knee rests on it (thin legs: measured on the mesh)
    duty_k = 0.42
    duty_h = 0.46
    # touchdown phases: left hand, right knee, right hand, left knee (lateral-diagonal sequence)
    td = {'LH': 0.0, 'RK': 0.08, 'RH': 0.5, 'LK': 0.58}
    knee_x = 0.13
    knee_y_mid = 0.15   # knee ground point under / slightly behind the hip joints at mid stance
    hand_x = 0.19
    hand_y_mid = -0.37
    pitch = 74.0       # pelvis pitch forward
    spine_pitch = 20.0
    shin_up = 22.0     # shin angle above the floor in stance
    knee_lift = 0.05
    hand_lift = 0.07
    palm_h = 0.039     # wrist height for a flat palm (+7 mm: the wrist skin follows the forearm angle)


def phase_of(u, td, duty):
    """(in_stance, s) with s = stance progress or swing progress, for limb touchdown phase td."""
    p = (u - td) % 1.0
    if p < duty:
        return True, p / duty
    return False, (p - duty) / (1 - duty)


class CrawlCtx:
    def __init__(self, B, cache):
        self.B = B
        self.body = E.Body(B)
        self.p = CrawlP


def crawl_pose(ctx, t, G=None, extra=None):
    """In-place hands-and-knees scramble toward -Y. The van floor rides +Y at p.v; planted palms and
    knees ride with it. Pelvis height and roll are solved so every planted knee touches the floor."""
    b, p = ctx.body, ctx.p
    u = (t / p.T) % 1.0
    tw = 2 * math.pi * u
    trav_k = p.v * p.T * p.duty_k
    trav_h = p.v * p.T * p.duty_h
    # --- torso: pitched forward almost horizontal; lizard wriggle (side bend) with the diagonals
    wr = math.sin(tw - 0.6)
    yaw = 6 * math.sin(tw - 0.3)
    hrot = R(Z, yaw) @ R(X, p.pitch) @ R(Y, 0.0)
    J = {}
    spine(J, pitch=p.spine_pitch + 3 * math.sin(2 * tw - 1.0), roll=9 * wr, yaw=-0.5 * yaw)
    # periscope head: neck and head bent back so the face looks at the door; panicky bobs and glances
    glance = 10 * math.sin(tw + 0.4) + 6 * math.sin(2 * tw + 1.3)
    head(J, pitch=-(p.pitch + p.spine_pitch) + 14 + 4 * math.sin(2 * tw + 0.5), roll=-5 * wr, yaw=glance, neck=0.5)
    # --- knee targets (ground points), weights
    knees = {}
    for s, key in (('Left', 'LK'), ('Right', 'RK')):
        st, k = phase_of(u, p.td[key], p.duty_k)
        x = SGN[s] * p.knee_x
        if st:
            y = p.knee_y_mid - trav_k / 2 + trav_k * k
            knees[s] = (Vector((x, y, p.knee_r)), True, k)
        else:
            y0 = p.knee_y_mid + trav_k / 2
            y1 = p.knee_y_mid - trav_k / 2
            Ts = p.T * (1 - p.duty_k)
            y = E.hermite(y0, p.v, y1, p.v * 0.3, Ts, k)
            lift = p.knee_lift * math.sin(math.pi * k) ** 1.5
            knees[s] = (Vector((x, y, p.knee_r + lift)), False, k)
    # --- pelvis height (and roll, when both knees are down): every planted knee touches the floor
    hips = Vector((0.012 * math.sin(tw - 0.9), 0.0, 0.45))
    l1 = b.leg['Left']['l1']

    # contact points used by the solve: planted knees, and for a swinging knee its lift-off point
    # (early swing) or its landing point (late swing), both riding the floor. The pelvis roll blends
    # in before a touchdown so both knees already agree when the new one lands (no pop), and fades
    # after a lift-off. The height follows the planted knees only.
    cp, wr = {}, {}
    for s in SIDES:
        K, planted, k = knees[s]
        if planted:
            cp[s], wr[s] = K, 1.0
        else:
            Ts = p.T * (1 - p.duty_k)
            if k < 0.5:
                cp[s] = Vector((K.x, p.knee_y_mid + trav_k / 2 + p.v * Ts * k, p.knee_r))
                wr[s] = 1 - smooth(k / 0.3)
            else:
                cp[s] = Vector((K.x, p.knee_y_mid - trav_k / 2 - p.v * Ts * (1 - k), p.knee_r))
                wr[s] = smooth((k - 0.55) / 0.45)

    def needs(hr):
        o, _ = b.B.fk(b.base, dict(J, Hips=hr), Matrix.Translation(hips - b.hips0))
        res = {}
        for s in SIDES:
            K = cp[s]
            Hj = o[P + s + 'UpLeg'].translation
            d2 = (Hj.x - K.x) ** 2 + (Hj.y - K.y) ** 2
            res[s] = K.z + math.sqrt(max(l1 * l1 - d2, 0.0)) - Hj.z
        return res
    wb = min(wr['Left'], wr['Right'])
    full = 0.0                                   # roll that equalises both knees, then blended by wb
    if wb > 0:
        req = needs(hrot)
        for _ in range(4):
            full += -math.degrees(math.atan((req['Left'] - req['Right']) / (2 * 0.1)))
            full = clamp(full, -12.0, 12.0)
            req = needs(R(Y, full) @ hrot)       # world forward axis (the pelvis is pitched ~75 deg)
    roll = wb * full
    hrot = R(Y, roll) @ hrot
    req = needs(hrot)
    planted = [req[s] for s in SIDES if knees[s][1]]
    if planted:
        dz = max(planted)
    else:   # airborne-knees gap: blend from the knee that just lifted to the one about to land, by time
        Ts = p.T * (1 - p.duty_k)
        lift_s = min(SIDES, key=lambda s: knees[s][2])
        land_s = max(SIDES, key=lambda s: knees[s][2])
        a = knees[lift_s][2] * Ts
        bb = (1 - knees[land_s][2]) * Ts
        g = smooth(a / (a + bb))
        dz = (1 - g) * req[lift_s] + g * req[land_s]
    hips.z += dz
    legs = {}
    out1, _ = b.B.fk(b.base, dict(J, Hips=hrot), Matrix.Translation(hips - b.hips0))
    for s in SIDES:
        K, planted, k = knees[s]
        H = out1[P + s + 'UpLeg'].translation
        Kp = H + (K - H).normalized() * l1            # thigh points at the knee target (exact when planted)
        zc = p.knee_r + 0.008
        if not planted and Kp.z < zc and H.z - zc < l1:
            # a swinging knee that would dip into the floor stays just above it: same horizontal
            # direction, reachable distance (continuous with the plain aim at the switch)
            r = math.sqrt(l1 * l1 - (H.z - zc) ** 2)
            dxy = Vector((Kp.x - H.x, Kp.y - H.y, 0.0))
            Kp = Vector((H.x, H.y, zc)) + dxy.normalized() * r
        phi = p.shin_up + (0 if planted else 30 * math.sin(math.pi * k))
        shin = Vector((0.0, math.cos(math.radians(phi)), math.sin(math.radians(phi))))
        A = Kp + shin * b.leg[s]['l2']
        line = (A - H).normalized()
        perp = (Kp - H) - line * (Kp - H).dot(line)
        hinge = line.cross(perp.normalized())
        frot = R(X, 150 + phi + (0 if planted else 15 * math.sin(math.pi * k)))
        M = frot.to_matrix().to_4x4() @ b.F0[s].to_3x3().to_4x4()
        M.translation = A
        legs[s] = (M, hinge)
    # --- hands
    arms = {}
    for s, key in (('Left', 'LH'), ('Right', 'RH')):
        sg = SGN[s]
        st, k = phase_of(u, p.td[key], p.duty_h)
        x = sg * p.hand_x
        if st:
            y = p.hand_y_mid - trav_h / 2 + trav_h * k
            pos = Vector((x, y, p.palm_h))
            q = R(Z, -sg * 12) @ R(Y, -sg * 90) @ R(X, -90)
        else:
            y0 = p.hand_y_mid + trav_h / 2
            y1 = p.hand_y_mid - trav_h / 2
            Ts = p.T * (1 - p.duty_h)
            y = E.hermite(y0, p.v, y1, p.v * 0.3, Ts, k)
            pos = Vector((x, y, p.palm_h + p.hand_lift * math.sin(math.pi * k) ** 1.3))
            q = R(Z, -sg * 12) @ R(Y, -sg * 90) @ R(X, -90 - 25 * math.sin(math.pi * k))
        arms[s] = (pos, q, Vector((sg * 0.6, 1.0, 0.3)))
    out, info = b.pose(hips, hrot, J, legs=legs, arms=arms, curl={'Left': (0.1, 0.0), 'Right': (0.1, 0.0)})
    info['pelvis_roll'] = roll
    return out, info


def _crawl_canonical(ctx, frames, N):
    v = ctx.B.values_from_pose(frames[1.0])
    return {1.0: v, float(N + 1): v}


def crawl_extra(ctx, frames, info):
    return {'hips_z_range': [min(i['hips'][2] for i in info), max(i['hips'][2] for i in info)]}


CLIPS['Escape_Scramble'] = {
    'T': CrawlP.T, 'loop': True, 'stage': 'cargo', 'setup': CrawlCtx, 'pose': crawl_pose, 'canonical': _crawl_canonical,
    'ground': lambda t: CrawlP.v * t, 'ground_note': 'in place on the van floor; floor rides +Y at %.2f m/s' % CrawlP.v,
    'height_ref': lambda t: 0.0, 'extra_metrics': crawl_extra,
    'start': 'own frame 1 (left palm touchdown)', 'end': 'frame 1 (exact seam)',
    'beats': ['panicky hands-and-knees scramble toward the open door (-Y), 0.5 s cycle, lateral-diagonal sequence',
              'palms and knees ride the van floor (no sliding); pelvis height solved from the planted knees',
              'body almost horizontal, lizard wriggle with the diagonals; head bent back like a periscope, glancing',
              'feet flick up behind on every knee swing'], 'events': {}}


# ============================================================================= JumpOut (van door -> street -> Flee_Run)
import clips_police as CPOL

JO_T = 34 / 30         # = 2 Flee_Run cycles: lands on the left foot at 17/30 s = a Flee_Run left touchdown
JO_CROUCH = 0.27       # frog-hop from the crawl into a crouch on the sill
JO_TAKEOFF = 0.35
JO_LAND = 17 / 30
JO_VZ = 0.0            # take-off vertical speed (m/s); flight is ballistic (g = 9.81)
VF = E.VAN_FLOOR


def jo_speed(t):
    """Ground speed under the in-place clip: crawl speed on the van floor, ramps in the air to the run speed."""
    return CrawlP.v + (CPOL.FLEE.v - CrawlP.v) * smooth((t - JO_TAKEOFF) / 0.10)


JO_GROUND = E.Ground(jo_speed, JO_T + 0.1)
JO_HEEL_Y = -0.10      # crouch heel position on the sill at the crouch time (toes just behind the edge)
JO_EDGE0 = JO_HEEL_Y - 0.33 - JO_GROUND(JO_TAKEOFF) + JO_GROUND(JO_CROUCH)   # sill edge at t = 0 (rides the ground)


def jo_floor(x, yg, t):
    """Floor height at ground-frame y (yg = clip y - G(t)): van floor behind the sill, street in front."""
    return VF if yg > JO_EDGE0 else 0.0


class JumpCtx:
    def __init__(self, B, cache):
        self.B = B
        self.body = E.Body(B)
        self.crawl = CrawlCtx(B, cache)
        self.run = CPOL.RunCtx(B, CPOL.FLEE)
        out0, _ = crawl_pose(self.crawl, 0.0)
        lift = Matrix.Translation((0, 0, VF))
        self.P0 = {n: lift @ m for n, m in out0.items()}
        # the Flee_Run parts at its frame 1 (the landing target and the end contract)
        cap = {}
        CPOL.run_pose(self.run, 0.0, mod=lambda t, d: cap.update({k: (v.copy() if hasattr(v, 'copy') else v) for k, v in d.items()}))
        self.run0 = cap
        self.ch = Chan(
            hy=K((JO_CROUCH, 0.03), (JO_TAKEOFF, -0.06), (0.42, -0.02), (JO_LAND, 0.0)),
            pitch=K((JO_CROUCH, 38), (0.31, 44), (JO_TAKEOFF, 22), (0.40, 8), (0.50, 14), (JO_LAND, 10)),
            arms_f=K((JO_CROUCH, -40), (0.31, -45), (JO_TAKEOFF, -20), (0.47, 85), (0.51, 95), (0.545, 75), (JO_LAND, 50)),
            arms_o=K((JO_CROUCH, 20), (JO_TAKEOFF, 30), (0.40, 55), (JO_LAND, 40)),
            elb=K((JO_CROUCH, 30), (JO_TAKEOFF, 10), (0.40, 30), (JO_LAND, 35)),
            look=K((JO_CROUCH, 25), (0.31, 35), (JO_TAKEOFF, -10), (0.40, -25), (JO_LAND, -15)),
            spine_p=K((JO_CROUCH, 15), (0.31, 20), (JO_TAKEOFF, -8), (0.40, -12), (JO_LAND, -4)),
            blend=K((0.38, 0), (JO_LAND, 1)),
        )
        self.feet_crouch = {s: self._crouch_foot(s, JO_CROUCH) for s in SIDES}

    def _crouch_foot(self, s, t):
        """Planted crouch foot on the van floor (rides the ground at the crawl speed)."""
        y = JO_HEEL_Y + (JO_GROUND(t) - JO_GROUND(JO_CROUCH))
        return self.body.foot(s, (SGN[s] * 0.13, y, VF), R(Z, SGN[s] * 8), 'heel')


def jo_air_pose(ctx, t):
    """Crouch on the sill (planted feet), take-off, flight; blends into the Flee_Run parts by the landing."""
    b = ctx.body
    c = ctx.ch(t)
    if t <= JO_TAKEOFF:
        hz = VF + 0.40 + 0.10 * smooth((t - JO_CROUCH) / (JO_TAKEOFF - JO_CROUCH)) ** 2 - 0.04 * bump(t, JO_CROUCH, 0.30, JO_TAKEOFF)
    else:
        tau = t - JO_TAKEOFF
        hz = VF + 0.50 + JO_VZ * tau - 0.5 * 9.81 * tau * tau
    hips = Vector((0.0, c.hy, hz))
    hrot = R(X, c.pitch)
    J = {}
    spine(J, pitch=c.spine_p)
    head(J, pitch=c.look - c.pitch * 0.6, yaw=8 * math.sin(2 * math.pi * 6 * t), neck=0.5)
    for s in SIDES:
        sg = SGN[s]
        flail = 16 * math.sin(2 * math.pi * 4.5 * t + (0 if s == 'Left' else 2.2)) * smooth((t - JO_TAKEOFF) / 0.12)
        arm(J, s, fwd=c.arms_f + flail, out=c.arms_o, elbow=c.elb, wrist=-15)
    # legs
    legs, toes = {}, {}
    run_legs = ctx.run.legs
    for s in SIDES:
        if t <= JO_TAKEOFF:
            M = ctx._crouch_foot(s, t)
            peel = 50 * smooth((t - 0.30) / (JO_TAKEOFF - 0.30))     # push off through the toes
            if peel > 0:
                L = run_legs[s]
                lat = R(Z, SGN[s] * 8) @ Vector(X)
                mtp = M @ (b.F0[s].inverted() @ b.pivot0[s]['mtp'])
                M = E.rot_about(mtp, R(lat, peel)) @ M
            legs[s], toes[s] = M, peel
        else:
            # flight: from the take-off foot to the Flee_Run foot at landing time, with a comic air-run tuck
            M0 = ctx._crouch_foot(s, JO_TAKEOFF)
            mtp = M0 @ (b.F0[s].inverted() @ b.pivot0[s]['mtp'])
            M0 = E.rot_about(mtp, R(R(Z, SGN[s] * 8) @ Vector(X), 50)) @ M0
            u_land = 0.0 if s == 'Left' else 0.5
            M1, toe1 = run_legs[s](u_land)
            k = (t - JO_TAKEOFF) / (JO_LAND - JO_TAKEOFF)
            Ts = JO_LAND - JO_TAKEOFF
            p0, p1 = M0.translation, M1.translation
            v0 = Vector((0, jo_speed(JO_TAKEOFF), 1.0))
            v1 = Vector((0, 0.95 * CPOL.FLEE.v, -1.2)) if s == 'Left' else Vector((0, -2.0, 0.0))
            pos = Vector([E.hermite(p0[i], v0[i], p1[i], v1[i], Ts, k) for i in range(3)])
            if s == 'Right':   # the trailing foot stays forward under him until the sill is well behind
                ky = k ** 3
                pos.y = E.hermite(p0.y, 0.0, p1.y, -1.0, Ts, ky) - 0.05 * math.sin(math.pi * ky)
            # cannonball tuck: both feet stay above the van floor until the sill has passed behind him
            pos.z += 0.34 * bump(k, 0.0, 0.40, 0.92) * (1.0 if s == 'Left' else 0.4)
            pos.y += (-0.12 if s == 'Left' else 0.10) * math.sin(math.pi * k)   # bicycle in the air
            q0, q1 = M0.to_quaternion(), M1.to_quaternion()
            if q0.dot(q1) < 0:
                q1.negate()
            q = q0.slerp(q1, smooth(k))
            M = q.to_matrix().to_4x4()
            M.translation = pos
            legs[s], toes[s] = M, 50 * (1 - smooth(k / 0.4)) + toe1 * smooth(k)
    # converge onto the Flee_Run frame-1 parts for a seamless landing
    w = c.blend
    if w > 0:
        r = ctx.run0
        hips = hips.lerp(r['hips'], w)
        hrot = hrot.slerp(r['hrot'], w)
        for n in set(J) | set(r['J']):
            a = J.get(n, QI())
            bq = r['J'].get(n, QI())
            if a.dot(bq) < 0:
                bq = -bq
            J[n] = a.slerp(bq, w)
    curl = {s: (0.1 * (1 - w) + w * CPOL.FLEE.fist, 0.8 * w) for s in SIDES}
    return b.pose(hips, hrot, J, legs=legs, toes=toes, curl=curl)


def jo_pose(ctx, t):
    b = ctx.body
    if t >= JO_LAND:
        # landing squash and stumble on top of the exact Flee_Run (decays to zero by the end)
        sq = bump(t, JO_LAND, 0.65, 0.96)
        lean = bump(t, JO_LAND, 0.71, 1.04)

        def mod(tt, d):
            d['hips'] = d['hips'] + Vector((0, -0.03 * lean, -0.09 * sq))
            d['hrot'] = R(X, 14 * lean) @ d['hrot']
            J = d['J']
            J['Spine1'] = R(X, 10 * sq) @ J.get('Spine1', QI())
            J['Neck'] = R(X, 14 * sq) @ J.get('Neck', QI())
            for s in SIDES:
                J[s + 'Arm'] = R(Y, -SGN[s] * 30 * lean) @ J.get(s + 'Arm', QI())
        return CPOL.run_pose(ctx.run, t - JO_T, mod=mod)
    if t >= JO_CROUCH:
        return jo_air_pose(ctx, t)
    # frog hop: whole-skeleton blend from the crawl frame 1 (on the van floor) to the crouch
    # both ends ride the van floor: the crawl contacts are carried back with it, the crouch feet are
    # the planted feet at time t (so nothing skids at lift-off or at the landing on the sill)
    P1, _ = jo_air_pose(ctx, JO_CROUCH)
    shift = JO_GROUND(t) - JO_GROUND(JO_CROUCH)
    P1 = {n: Matrix.Translation((0, shift, 0)) @ m for n, m in P1.items()}
    k = smoother(t / JO_CROUCH)
    kr = smooth(t / JO_CROUCH)            # rotations ease out too: the feet must arrive still (they turn ~170 deg)
    P0 = {n: Matrix.Translation((0, JO_GROUND(t), 0)) @ m for n, m in ctx.P0.items()}
    u = t / JO_CROUCH
    # the feet unroll (~170 deg) early, while they are still high, and arrive flat and still
    out = E.rigid_blend(b, P0, P1, k, kr, lift=0.13 * math.sin(math.pi * k) ** 0.7, kr_feet=smooth(u / 0.9),
                        feet_local=True, floor_guard=VF + 0.010)
    return out, {'leg_over': 0.0, 'arm_over': 0.0, 'hips': tuple(out[P + 'Hips'].translation)}


def jo_canonical(ctx, frames, N):
    crawl1 = ctx.B.values_from_pose(ctx.P0)
    end = ctx.B.values_from_pose(CPOL.run_pose(ctx.run, 0.0)[0])
    return {1.0: crawl1, float(N + 1): end}


def jo_stage(col):
    """Review stage: street (striped) + a van floor slab behind the sill that rides with the ground."""
    tread = E.treadmill(bpy.context.scene, col)
    van = E.box(col, 'Van_Floor_Review', (-0.7, JO_EDGE0, 0.0), (0.7, JO_EDGE0 + 3.0, VF), (90, 96, 104))
    bpy.data.objects['Studio_Floor'].hide_render = True
    return [(tread, 0.5), (van, None)]


import bpy
CLIPS['JumpOut'] = {
    'T': JO_T, 'loop': False, 'stage': 'jump', 'setup': JumpCtx, 'pose': jo_pose, 'canonical': jo_canonical,
    'ground': JO_GROUND, 'floor': jo_floor, 'stage_objects': jo_stage,
    'ground_note': 'in place; ground +Y: %.1f m/s on the van floor until take-off (0.35 s), ramps in the air to %.1f m/s within 0.1 s, then Flee_Run speed. Root = street level below the door; the van floor is +%.2f m' % (CrawlP.v, CPOL.FLEE.v, VF),
    'start': 'Escape_Scramble frame 1 raised by the van floor height (+0.55 m), exact', 'end': 'Flee_Run frame 1 (exact)',
    'events': {'Land': JO_LAND},
    'beats': ['0.00-0.27 frog hop: from the crawl, hands shove off and both feet snap under him onto the sill',
              '0.27-0.35 crouched on the edge, arms swing back, peeks down (gulp), pushes off through the toes',
              '0.35-0.567 steps off and falls: arms fly up and flail, cannonball tuck until the van is behind him, ballistic drop of 0.55 m',
              '0.567 LAND on the left foot (= a Flee_Run touchdown): squash 9 cm, chest and head fold, arms splay',
              '0.567-1.02 stumbling forward lean while the legs already run', '1.133 = Flee_Run frame 1'],
}


# ============================================================================= Escape_Scramble_Start (cargo sit -> crawl)
SIT_HIPS = Vector((-0.30, 0.0, 0.117))   # planned Cargo_Sit_Idle_v04 layout (Idle_Knock_v03 HANDOFF 5), +9 mm: butt on the floor


def sit_pose(b, look=0.0, shrug=0.0, hug=1.0, lean=0.0, t=0.0):
    """Seated on the van floor, back to the side wall (x = -0.65), facing +X, knees up, arms round the
    shins. Provisional stand-in for the Cargo_Sit_Idle_v04 frame-1 contract (not authored yet)."""
    hrot = R(Z, 90) @ R(X, -18 + lean)
    J = {}
    spine(J, pitch=36 + 0.5 * lean, yaw=0.25 * look)
    head(J, pitch=4, yaw=0.7 * look, neck=0.45)
    fwd = Vector((1, 0, 0))
    left = Vector((0, 1, 0))
    legs = {}
    for s in SIDES:
        sg = SGN[s]
        A = SIT_HIPS + fwd * 0.40 + left * (sg * 0.12)
        A.z = b.pivot0[s]['ankle'].z
        legs[s] = (b.foot(s, A, R(Z, 90 + sg * 6), 'ankle'), (R(Z, 90) @ Vector((-1.0, -sg * 0.12, 0.0))).normalized())
    arms = {}
    for s in SIDES:
        sg = SGN[s]
        tgt = SIT_HIPS + fwd * 0.30 + left * (-sg * 0.035) + Vector((0, 0, 0.30 + 0.03 * sg))
        tgt = SIT_HIPS + R(Z, 0.25 * look) @ (tgt - SIT_HIPS) + Vector((-0.004 * max(0.0, -lean), 0, 0.02 * shrug / 16))
        q = R(Z, 90) @ R(X, -75) @ R(Y, sg * 40)
        arms[s] = (tgt, q, (R(Z, 90) @ Vector((sg * 0.9, 0.0, -0.3))))
    for s in SIDES:
        arm(J, s, sh_up=shrug)
    hips = SIT_HIPS + Vector((0, 0, 0.0014 * max(0.0, -lean)))     # leaning back rolls the pelvis onto the butt
    return b.pose(hips, hrot, J, legs=legs, arms=arms, curl={'Left': (0.5, 0.4), 'Right': (0.5, 0.4)})


class StartCtx:
    def __init__(self, B, cache):
        self.B = B
        self.body = E.Body(B)
        self.crawl = CrawlCtx(B, cache)
        self.S0, _ = sit_pose(self.body)
        self.C1, _ = crawl_pose(self.crawl, 0.0)


SS_T = 0.8
SS_LUNGE = 0.32


def ss_chan():
    return Chan(
        look=K((0, 0), (0.10, 0), (0.17, -58, ('lin', 'auto')), (0.22, -62), (SS_LUNGE, -55)),
        shrug=K((0, 0), (0.10, 0), (0.16, 16), (0.24, 12), (SS_LUNGE, 14)),
        lean=K((0, 0), (0.10, 0), (0.18, -4), (SS_LUNGE, -3)),
        trem=K((0, 0), (0.16, 0), (0.20, 1), (SS_LUNGE, 1)),
    )


def ss_pose(ctx, t):
    """0-0.10 sit (contract), 0.10-0.32 SNAP stare at the door and freeze, 0.32-0.80 lunge-turn onto
    all fours, landing on Escape_Scramble frame 1."""
    b = ctx.body
    c = ctx.ch(min(t, SS_LUNGE))
    tr = c.trem * 2.0 * math.sin(2 * math.pi * 9 * t)
    S, info = sit_pose(b, look=c.look + tr, shrug=c.shrug, lean=c.lean)
    if t <= SS_LUNGE:
        return S, info
    u = (t - SS_LUNGE) / (SS_T - SS_LUNGE)
    k = smoother(u)
    kr = smooth(u)
    # the feet leave the floor before they turn (no skid), the lift follows the raw progress
    # the hips rise first (onto the knees), then the feet swing back under and behind him
    # the hips rise first (onto the knees), then the feet swing back under and behind him; the feet
    # turn relative to the shins; the head stays tucked until the body has pitched forward (1.2 m roof)
    out = E.rigid_blend(b, S, ctx.C1, k, kr, lift=0.10 * math.sin(math.pi * min(1.0, u / 0.9)) ** 0.5,
                        kr_feet=smooth((u - 0.05) / 0.55), k_root=smooth(min(1.0, u / 0.45)),
                        kr_root=smooth(min(1.0, u / 0.45)), k_feet=smooth((u - 0.2) / 0.8),
                        lift_feet=0.10 * math.sin(math.pi * u) ** 0.6, feet_local=True, floor_guard=0.008,
                        kr_bones=dict({P + 'Neck': smooth((u - 0.35) / 0.65), P + 'Head': smooth((u - 0.35) / 0.65)},
                                      **{P + n: smooth(min(1.0, u / 0.5)) for n in ('Spine', 'Spine1', 'Spine2')}))
    return out, {'leg_over': 0.0, 'arm_over': 0.0, 'hips': tuple(out[P + 'Hips'].translation)}


class SSCtx(StartCtx):
    def __init__(self, B, cache):
        StartCtx.__init__(self, B, cache)
        self.ch = ss_chan()



def ss_canonical(ctx, frames, N):
    return {1.0: ctx.B.values_from_pose(ctx.S0), float(N + 1): ctx.B.values_from_pose(ctx.C1)}


CARGO_VIEWS = {'side': ((0.0, -5.0, 0.8), (-0.2, 0.0, 0.5), 1.9), 'three_quarter': ((3.3, -3.6, 1.75), (-0.22, 0.0, 0.48), 1.9),
               'front': ((4.6, 0.0, 0.85), (-0.25, 0.0, 0.5), 1.9), 'door': ((1.2, -4.6, 1.4), (-0.1, 0.0, 0.45), 1.9)}
CLIPS['Escape_Scramble_Start'] = {
    'T': SS_T, 'loop': False, 'stage': 'cargo', 'setup': SSCtx, 'pose': ss_pose, 'canonical': ss_canonical,
    'views': CARGO_VIEWS, 'height_ref': lambda t: 0.0,
    'start': 'provisional cargo sit pose (hips (-0.30, 0, 0.117), facing +X, back to the wall x = -0.65); swap in Cargo_Sit_Idle_v04 frame 1 when it exists',
    'end': 'Escape_Scramble frame 1 (exact)',
    'beats': ['0.00-0.10 the knee hug (sit contract)', '0.10-0.17 SNAP: head whips 58 deg to his right, toward the open doors (-Y); shoulders jolt up',
              '0.17-0.32 frozen stare, trembling, presses back against the wall', '0.32-0.80 lunges round 90 deg to his right onto hands and knees, body lifts and drops into the crawl',
              '0.80 = Escape_Scramble frame 1 (the capsule starts moving)']}
