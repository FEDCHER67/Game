"""Escape_v01 clip definitions (Sausage Buddy patient frees himself from TABLE-ASTRA-001 v02 straps).

Authoring frame = armature space with the rig at PatientRest (see esc_core): head +Y, face +Z,
patient's LEFT = +X, pad top z ~ 0, floor z = -0.66. Four limb straps only (no torso strap).

Pose keys (exact raw values at clip seams):
  LIE      = TABLE_REST (Patient_TableRest_v01, the contract of every Operation_v01 table clip)
  SIT      = sitting up on the table, legs straight in their TABLE_REST place (any leg strap may
             still be closed), both hands planted on the pad beside the hips
  EDGE_R   = sitting on the patient's RIGHT pad edge (table-camera side), legs hanging, all straps open
  RUN0     = Escape_Police_v01 Flee_Run_v01 frame 1 on the floor at the RUN0 root (PatientRest-local)
  REACH_L/REACH_R = grab pose of the wrist-unbuckle clips (start of the lying slump clips)
  LEGS_REACH      = grab pose of Esc_Sit_UnbuckleLegsBoth (start of the sitting slump clip)
Clip side naming: 'ArmR_ByL' = the free LEFT hand opens the RIGHT wrist strap.
"""
import math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import esc_core as E
from esc_core import ik_keys, look_keys, both, P, R, QI, X, Y, Z

FPS = 30


def V(*a):
    return Vector(a)


def other(t):
    return 'R' if t == 'L' else 'L'


def side_name(t):
    return 'Left' if t == 'L' else 'Right'


class Lib:
    """Shared targets, pose-key channel sets and helpers for one build session."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.S = ctx.S
        self.d0 = ctx.ch0()

    # -- rest / default channel subsets ----------------------------------------------------------
    def rest(self, names=None):
        if names is None:
            return dict(self.d0)
        return {k: self.d0[k] for k in names}

    def rest_hand(self, t, lift=V(0, 0, 0)):
        s = side_name(t)
        c = self.ctx
        return ik_keys(t, pos=c.rest_grip[s] + lift, f=c.rest_f[s], n=c.rest_n[s], pole=c.arm[s]['pole0'])

    def buckle(self, strap, deg=0.0):
        return self.S.buckle(strap, deg)

    def on_buckle(self, t, strap, deg=0.0, lift=0.004, off=V(0, 0, 0), f=None, pole=None, w=None):
        p, n, u, w_ = self.buckle(strap, deg)
        return ik_keys(t, pos=p + n * lift + off, n=-n, f=f, pole=pole, w=w)

    def look_strap(self, strap, w=1.0, off=V(0, 0, 0.16)):
        p, n, u, w_ = self.buckle(strap, 0.0)
        return look_keys(p + off, w)

    # -- SIT ------------------------------------------------------------------------------------------
    def pad_z(self, x, y):
        z = self.S.pad_top(np.array([[-x, -y, 0.0]]))[0]
        return -0.006 if math.isnan(z) else z - E.PAD_Z

    def plant(self, t, px, py, yaw, out=0.24, back=0.04, lift=0.0, fwd=0.0):
        """Palm planted on the pad beside the hips of a root (px, py, yaw): `out` to the side,
        `back` behind the hip joint; palm 11 mm over the local pad top (+lift)."""
        sg = 1 if t == 'L' else -1
        a = math.radians(yaw)
        fw = V(math.sin(a), -math.cos(a), 0.0)
        left = V(math.cos(a), math.sin(a), 0.0)
        h = self.ctx.h0 + V(px, py, 0.0)
        p = h + left * sg * out - fw * (back - fwd)
        z = self.pad_z(p.x, p.y) + 0.015 + lift
        f = (fw * 0.9 + left * sg * 0.35).normalized()
        pole = (left * sg * 0.7 - fw * 0.7).normalized()
        return ik_keys(t, pos=V(p.x, p.y, z), f=f, n=V(0, 0, -1), pole=pole, w=1.0)

    def sit_plant(self, t, lift=0.0, dy=0.0):
        return self.plant(t, 0.0, 0.0, 0.0, back=0.04 + dy, lift=lift)

    def SIT(self):
        d = dict(pitch=78, crunch=8, neck=-4, seat=1, arail_L=0, arail_R=0, lrail_L=1, lrail_R=1)
        d.update(self.sit_plant('L'))
        d.update(self.sit_plant('R'))
        d.update(look_w=0.0, hyaw=0.0, hnod=0.0, htilt=0.0, roll=0.0, twist=0.0, bend=0.0, yaw=0.0,
                 px=0.0, py=0.0, pz=0.0, cu_L=0.0, cu_R=0.0, th_L=0.0, th_R=0.0, floor=0.0)
        for k in ('pr', 'sh', 'afl', 'aab', 'atw', 'el', 'fl', 'ab', 'lr', 'kn', 'fo', 'toe', 'klift', 'ftw', 'att', 'fik'):
            d[k + '_L'] = d[k + '_R'] = 0.0
        return d

    # -- EDGE_R ------------------------------------------------------------------------------------------
    def edge_plant(self, t, lift=0.0):
        return self.plant(t, -0.17, -0.30, -90.0, lift=lift)

    def EDGE(self, side='R'):
        """EDGE_R; EDGE_L = exact channel mirror (his left pad edge, instrument-stand side)."""
        if side == 'L':
            return E.mirror_dict(self.EDGE('R'))
        d = dict(yaw=-90, pitch=84, px=-0.17, py=-0.30, pz=0.0, crunch=6, seat=1, neck=0, hnod=0, hyaw=0, htilt=0,
                 roll=0, twist=0, bend=0, look_w=0.0, floor=0.0,
                 lrail_L=0, lrail_R=0, fl_L=84, fl_R=84, kn_L=88, kn_R=88, ab_L=0, ab_R=0, lr_L=0, lr_R=0, fo_L=0, fo_R=0,
                 arail_L=0, arail_R=0, cu_L=0.0, cu_R=0.0, th_L=0.0, th_R=0.0)
        d.update(self.edge_plant('L'))
        d.update(self.edge_plant('R'))
        for k in ('pr', 'sh', 'afl', 'aab', 'atw', 'el', 'toe', 'klift', 'ftw', 'att', 'fik'):
            d[k + '_L'] = d[k + '_R'] = 0.0
        return d


def follow_keys(lib, t, strap, curve, t0, t1, lift=0.004, f=None, step=1.0 / 60):
    """Dense IK keys that keep the grip on the buckle while the strap angle follows `curve`."""
    keys = []
    n = max(1, int(round((t1 - t0) / step)))
    for i in range(n + 1):
        tt = t0 + (t1 - t0) * i / n
        a = curve(tt)
        keys.append((tt, lib.on_buckle(t, strap, a, lift=lift, f=f)))
    return keys


def strap_curve(keys):
    return E.Curve([(t, a) for t, a in keys])


# ===================================================================================== lying: wrists
T_UNBUCKLE_ARM = 2.6
ARM_GRAB1, ARM_GRAB2, ARM_OPEN = 0.80, 1.25, 1.40


def reach_body(A):
    sg = 1 if A == 'L' else -1
    return {'roll': -16 * sg, 'crunch': 24, 'twist': -22 * sg, 'bend': 4 * sg, 'pr_' + A: 22, 'neck': 2}


def unbuckle_arm(lib, A):
    """Free hand A opens the other wrist strap; LIE -> LIE."""
    ctx = lib.ctx
    Pp = other(A)
    sg = 1 if A == 'L' else -1
    sA, sP = side_name(A), side_name(Pp)
    strap = 'STRAP_ARM_' + Pp
    p0, n0, u0, w0 = lib.buckle(strap)
    f_reach = V(-0.8 * sg, -0.3, -0.5)
    pole = V(0.4 * sg, 0.3, 1.0)
    T = T_UNBUCKLE_ARM
    sk = [(0.0, 0.0), (ARM_OPEN, 0.0), (ARM_OPEN + 0.12, 30.0), (ARM_OPEN + 0.30, 120.0)]
    sc = strap_curve(sk)
    K = []
    K.append((0.0, lib.rest()))
    K.append((0.0, {'ik_' + A: 1.0, 'ik_' + Pp: 1.0}))
    # notice: head lifts and snaps to the strapped wrist
    K.append((0.10, {'neck': 6, 'arail_' + A: 1.0, 'look_w': 0.0, **lib.look_strap(strap, 0.0)}))
    K.append((0.24, {'neck': 10, 'crunch': 6, 'look_w': 0.75, 'arail_' + A: 0.0}))
    # free hand peels off the pad and swings over the belly
    K.append((0.36, {**lib.rest_hand(A, V(0.02 * sg, 0.05, 0.12)), 'crunch': 10, 'roll': -6 * sg, 'cu_' + A: -0.15}))
    K.append((0.50, {**ik_keys(A, pos=V(0.04 * sg, 0.14, 0.31), f=f_reach, n=V(0, 0, -1), pole=pole),
                     'crunch': 17, 'roll': -11 * sg, 'twist': -12 * sg, 'bend': 5 * sg, 'pr_' + A: 12}))
    # hover over the buckle, then grab #1
    K.append((0.66, {**lib.on_buckle(A, strap, lift=0.07, f=f_reach, pole=pole), **reach_body(A), 'cu_' + A: -0.25}))
    K.append((ARM_GRAB1, {**lib.on_buckle(A, strap, lift=0.004), 'cu_' + A: 0.0}))
    K.append((0.88, {'cu_' + A: 0.65, 'cu_' + Pp: 0.5}))
    # tug... the buckle holds, the fingers slip off
    K.append((0.98, {**lib.on_buckle(A, strap, lift=0.012), 'crunch': 26, 'cu_' + A: 0.7}))
    K.append((1.06, {**lib.on_buckle(A, strap, lift=0.07, off=V(0.02 * sg, 0.05, 0.0)), 'cu_' + A: -0.35,
                     'hyaw': 9 * sg, 'crunch': 20, 'ftw_' + Pp: 6}))
    K.append((1.15, {'hyaw': -9 * sg, 'ftw_' + Pp: -6, 'cu_' + Pp: 0.9, 'neck': 7}))
    # grab #2 and pop the buckle open (the hand follows the buckle to 30 deg, then lets go)
    K.append((ARM_GRAB2, {**lib.on_buckle(A, strap, lift=0.004), 'cu_' + A: 0.0, 'hyaw': 0.0, 'ftw_' + Pp: 0.0,
                          'neck': 4, 'crunch': 24}))
    K.append((1.33, {'cu_' + A: 0.7}))
    K += follow_keys(lib, A, strap, sc, ARM_OPEN, ARM_OPEN + 0.12)
    K.append((ARM_OPEN + 0.12, {'cu_' + A: 0.55}))
    p30, n30, _, _ = lib.buckle(strap, 30.0)
    K.append((1.62, {**ik_keys(A, pos=p30 + n30 * 0.09 + V(0.04 * sg, 0.02, 0.05)), 'cu_' + A: -0.3, 'look_w': 0.6}))
    # the freed arm yanks up out of the opened strap (after the band has flipped past vertical)
    K.append((1.62, {'arail_' + Pp: 1.0, 'cu_' + Pp: 0.9}))
    yank_pole = V(-0.8 * sg, 0.3, 0.6)
    K.append((1.62, ik_keys(Pp, pole=yank_pole)))
    K.append((1.72, {'arail_' + Pp: 0.0, **lib.rest_hand(Pp, V(0.0, 0.01, 0.04)), **ik_keys(Pp, pole=yank_pole)}))
    K.append((1.86, {**lib.rest_hand(Pp, V(0.0, 0.07, 0.19)), **ik_keys(Pp, pole=yank_pole), 'cu_' + Pp: 1.0,
                     **ik_keys(A, pos=V(0.10 * sg, 0.16, 0.30)), 'cu_' + A: 0.8,
                     'roll': -7 * sg, 'crunch': 16, 'twist': -6 * sg, 'bend': 3 * sg, 'pr_' + A: 8, 'look_w': 0.3, 'neck': 8}))
    # both arms come down to their sides, body unrolls
    K.append((2.12, {**lib.rest_hand(Pp, V(0.0, 0.0, 0.035)), **ik_keys(Pp, pole=yank_pole), **lib.rest_hand(A, V(0.0, 0.0, 0.05)),
                     'roll': 0.0, 'crunch': 5, 'twist': 0.0, 'bend': 0.0, 'pr_' + A: 0.0, 'cu_' + A: 0.2, 'cu_' + Pp: 0.3,
                     'look_w': 0.0, 'neck': 4}))
    K.append((2.34, {**lib.rest_hand(Pp), **lib.rest_hand(A), 'arail_' + A: 0.0, 'arail_' + Pp: 0.0, 'crunch': 1.0,
                     'cu_' + A: 0.0, 'cu_' + Pp: 0.0, 'neck': 1.5}))
    K.append((2.44, {'arail_' + A: 1.0, 'arail_' + Pp: 1.0}))
    K.append((T, lib.rest()))
    K.append((T, {'ik_' + A: 1.0, 'ik_' + Pp: 1.0}))
    events = [
        {'name': 'Grab', 'strap': strap, 'hand': sA, 't': ARM_GRAB1},
        {'name': 'Slip', 'strap': strap, 'hand': sA, 't': 1.06},
        {'name': 'Grab', 'strap': strap, 'hand': sA, 't': ARM_GRAB2},
        {'name': 'StrapOpen', 'strap': strap, 't': ARM_OPEN},
        {'name': 'Release', 'strap': strap, 'hand': sA, 't': ARM_OPEN + 0.12},
    ]
    return dict(stem='Esc_Lie_UnbuckleArm%s_By%s_v01' % (Pp, A), T=T, loop=False, start='LIE', end='LIE',
                pre={'closed': [strap], 'open': ['STRAP_ARM_' + A], 'any': ['STRAP_LEG_L', 'STRAP_LEG_R']},
                closed0=[strap, 'STRAP_LEG_L', 'STRAP_LEG_R'], straps={strap: sk}, keys=K, events=events,
                peak=('REACH_' + Pp, ARM_GRAB2),
                after={strap: 'open'},
                next=['Esc_SitUp_v01 (both arms now free)'],
                views=('wrist_' + Pp, 'side'),
                beats=['0.00 LIE', '0.10-0.24 notices the strapped %s wrist (head snaps to it)' % sP.lower(),
                       '0.24-0.66 %s hand peels off the pad, rolls onto his %s side, reaches across' % (sA.lower(), sP.lower()),
                       '0.80 grab #1, 0.98 tug, 1.06 fingers slip off (head shake)',
                       '1.25 grab #2, 1.40 STRAP OPEN (hand follows the buckle to 30 deg), 1.52 lets go',
                       '1.62-1.86 freed %s arm yanks up out of the open strap, fists up' % sP.lower(),
                       '1.86-2.60 arms drop to the sides, unrolls to LIE'])


# ===================================================================================== lying: tug loop
T_TUG_ARM = 2.0


def tug_arm(lib, Pp):
    """Strapped arm Pp yanks against its strap, the free hand hauls on the strap band; LIE loop."""
    ctx = lib.ctx
    A = other(Pp)
    sg = 1 if A == 'L' else -1
    sP = side_name(Pp)
    strap = 'STRAP_ARM_' + Pp
    p0, n0, u0, w0 = lib.buckle(strap)
    band = u0 * 0.03                                           # on the band, 3 cm inward of the buckle
    f_reach = V(-0.8 * sg, -0.3, -0.5)
    pole = V(0.4 * sg, 0.3, 1.0)
    T = T_TUG_ARM
    K = [(0.0, lib.rest()), (0.0, {'ik_' + A: 1.0})]
    K.append((0.12, {'arail_' + A: 1.0, 'neck': 6, 'look_w': 0.0, **lib.look_strap(strap, 0.0), 'cu_' + Pp: 0.4}))
    K.append((0.26, {'arail_' + A: 0.0, **lib.rest_hand(A, V(0.02 * sg, 0.05, 0.12)), 'look_w': 0.6, 'crunch': 12,
                     'roll': -8 * sg, 'neck': 10}))
    K.append((0.42, {**lib.on_buckle(A, strap, lift=0.06, off=band, f=f_reach, pole=pole), **reach_body(A), 'cu_' + A: -0.2}))
    K.append((0.52, {**lib.on_buckle(A, strap, lift=0.006, off=band), 'cu_' + A: 0.0}))
    # two pulls: the hand hauls up on the band, body heaves toward the head end, strapped shoulder shrugs,
    # forearm slides / twists in the strap, legs kick in their straps
    for i, t0 in enumerate((0.62, 1.12)):
        K.append((t0, {'cu_' + A: 0.75, 'crunch': 24, 'cu_' + Pp: 1.0, **lib.on_buckle(A, strap, lift=0.006, off=band)}))
        K.append((t0 + 0.12, {'sh_' + Pp: 14, 'sh_' + A: 8, 'crunch': 30, 'neck': 10, 'roll': -13 * sg,
                              'ftw_' + Pp: 7 * (1 if i == 0 else -1), 'hnod': -6, 'fo_L': -18, 'fo_R': -10, 'klift_L': 0.012,
                              **lib.on_buckle(A, strap, lift=0.016, off=band)}))
        K.append((t0 + 0.30, {'sh_' + Pp: 2, 'sh_' + A: 1, 'crunch': 24, 'neck': 4, 'roll': -16 * sg, 'ftw_' + Pp: 0.0,
                              'hnod': 2, 'fo_L': 0, 'fo_R': 0, 'klift_L': 0.0, 'klift_R': 0.008 if i == 0 else 0.0,
                              **lib.on_buckle(A, strap, lift=0.006, off=band)}))
    K.append((1.50, {'klift_R': 0.0, 'hyaw': 10 * sg}))
    K.append((1.62, {**lib.on_buckle(A, strap, lift=0.10, off=band + V(0.04 * sg, 0.04, 0.0)), 'cu_' + A: -0.3, 'hyaw': -10 * sg,
                     'neck': 8, 'crunch': 14}))
    K.append((1.78, {**lib.rest_hand(A, V(0.0, 0.0, 0.03)), 'roll': -2 * sg, 'crunch': 3, 'twist': -2 * sg, 'bend': 1 * sg,
                     'pr_' + A: 2, 'hyaw': 0, 'look_w': 0.0, 'neck': 3, 'cu_' + A: 0.1, 'cu_' + Pp: 0.2}))
    K.append((1.88, {**lib.rest_hand(A), 'arail_' + A: 0.0}))
    K.append((1.94, {'arail_' + A: 1.0}))
    K.append((T, lib.rest()))
    K.append((T, {'ik_' + A: 1.0}))
    return dict(stem='Esc_Lie_TugArm%s_Loop_v01' % Pp, T=T, loop=True, start='LIE', end='LIE',
                pre={'closed': [strap], 'open': ['STRAP_ARM_' + A], 'any': ['STRAP_LEG_L', 'STRAP_LEG_R']},
                closed0=[strap, 'STRAP_LEG_L', 'STRAP_LEG_R'], straps={}, keys=K, events=[],
                after={}, next=['loop', 'Esc_Lie_UnbuckleArm%s_By%s_v01' % (Pp, A)],
                views=('wrist_' + Pp, 'side'),
                beats=['0.12-0.42 looks at the strapped %s wrist, free hand reaches over' % sP.lower(),
                       '0.52 grabs the strap band next to the buckle', '0.62 / 1.12 two heaving pulls (forearm slides and twists in the strap, legs kick)',
                       '1.50-1.62 frustrated head shake, lets go', '1.62-2.00 back to LIE (loop seam)'])


# ===================================================================================== sit up
T_SITUP = 1.0


def sit_up(lib):
    SIT = lib.SIT()
    T = T_SITUP
    K = [(0.0, lib.rest()), (0.0, {'ik_L': 1.0, 'ik_R': 1.0})]
    K.append((0.10, {'neck': 10, 'hnod': 4, 'crunch': 6, 'cu_L': 0.3, 'cu_R': 0.3, 'arail_L': 1.0, 'arail_R': 1.0}))
    # jackknife: arms swing forward for momentum
    K.append((0.20, {'arail_L': 0.0, 'arail_R': 0.0, **lib.rest_hand('L', V(0.0, 0.02, 0.06)), **lib.rest_hand('R', V(0.0, 0.02, 0.06))}))
    K.append((0.34, {'pitch': 40, 'crunch': 26, 'neck': 14, 'hnod': 6, 'seat': 0.5,
                     **ik_keys('L', pos=V(0.20, -0.20, 0.38), f=V(0.0, -1, 0.1), n=V(-0.3, 0, -1), pole=V(1, 0.3, -0.4)),
                     **ik_keys('R', pos=V(-0.20, -0.20, 0.38), f=V(0.0, -1, 0.1), n=V(0.3, 0, -1), pole=V(-1, 0.3, -0.4)),
                     'cu_L': 0.1, 'cu_R': 0.1}))
    K.append((0.52, {'pitch': 92, 'crunch': 16, 'neck': 0, 'hnod': -2, 'seat': 1.0,
                     **ik_keys('L', pos=V(0.24, -0.22, 0.16), f=V(0.2, -1, -0.3), n=V(0, 0, -1), pole=V(1, 0.5, 0)),
                     **ik_keys('R', pos=V(-0.24, -0.22, 0.16), f=V(-0.2, -1, -0.3), n=V(0, 0, -1), pole=V(-1, 0.5, 0)),
                     'cu_L': 0.0, 'cu_R': 0.0}))
    # settles back, palms plant on the pad, quick look around (where's the door?)
    K.append((0.70, {'pitch': 76, 'crunch': 8, 'neck': -6, **lib.sit_plant('L', lift=0.02), **lib.sit_plant('R', lift=0.02),
                     'hyaw': 18}))
    K.append((0.84, {**lib.sit_plant('L'), **lib.sit_plant('R'), 'pitch': 79, 'hyaw': -10}))
    K.append((T, SIT))
    return dict(stem='Esc_SitUp_v01', T=T, loop=False, start='LIE', end='SIT',
                pre={'closed': [], 'open': ['STRAP_ARM_L', 'STRAP_ARM_R'], 'any': ['STRAP_LEG_L', 'STRAP_LEG_R']},
                closed0=['STRAP_LEG_L', 'STRAP_LEG_R'], straps={}, keys=K, events=[], after={},
                next=['Esc_Sit_UnbuckleLegsBoth_v01 / _LegL_ / _LegR_ (a leg strap closed)', 'Esc_SwingOff_R_v01 (all open)'],
                views=('side', 'feet'),
                beats=['0.10 chin tucks, fists', '0.20-0.52 jackknife sit-up, arms swing forward, overshoot',
                       '0.70-0.84 palms plant, quick look around', '1.00 SIT'])


# ===================================================================================== sitting: legs
T_LEG_ONE = 2.3
T_LEGS_BOTH = 2.6
LEGS_GRAB = 0.80


def leg_reach_body():
    return dict(pitch=116, crunch=24, neck=-16, hnod=-6, pr_L=14, pr_R=14, seat=1)


def leg_look():
    return look_keys(V(0.0, -0.80, 0.18), 0.45)


def unbuckle_legs(lib, sides):
    """Seated, one or both hands open the shin strap(s) on their own side; SIT -> SIT."""
    SIT = lib.SIT()
    one = len(sides) == 1
    T = T_LEG_ONE if one else T_LEGS_BOTH
    K = [(0.0, SIT)]
    straps, events = {}, []
    body = leg_reach_body()
    if one:
        a = sides[0]
        sg = 1 if a == 'L' else -1
        body = dict(body, bend=-5 * sg)
        body['pr_' + other(a)] = 4
    K.append((0.12, {**leg_look(), 'look_w': 0.0, 'neck': -8}))
    K.append((0.28, {'look_w': 0.45, 'pitch': 88, 'crunch': 12, 'neck': -10}))
    plan = []
    for k, a in enumerate(sides):
        sg = 1 if a == 'L' else -1
        strap = 'STRAP_LEG_' + a
        f = V(0.15 * sg, -1, -0.05)
        pole = V(0.7 * sg, 0.2, 0.6)
        lift_ = 0.0 if not one else 0.0
        K.append((0.30, {**lib.sit_plant(a, lift=0.03)}))
        K.append((0.52, {**ik_keys(a, pos=V(0.20 * sg, -0.40, 0.20), f=f, n=V(0, 0, -1), pole=pole), 'cu_' + a: -0.2}))
        K.append((0.66, {**lib.on_buckle(a, strap, lift=0.06, f=f, pole=pole)}))
        plan.append((a, strap, f, pole))
    K.append((0.66, body))
    if one:
        o = other(sides[0])
        sgo = 1 if o == 'L' else -1
        # the other hand slides forward on the pad / thigh for support
        K.append((0.66, lib.plant(o, 0.0, 0.0, 0.0, out=0.26, back=-0.16)))
    for a, strap, f, pole in plan:
        K.append((LEGS_GRAB, {**lib.on_buckle(a, strap, lift=0.012), 'cu_' + a: -0.3}))
        K.append((LEGS_GRAB + 0.08, {'cu_' + a: 0.2}))
    # fumble: the first side slips, the second opens; then the first opens
    a1 = plan[0][0]
    s1 = plan[0][1]
    t_slip = 1.00
    K.append((0.94, {**lib.on_buckle(a1, s1, lift=0.02), 'cu_' + a1: 0.25, 'crunch': body['crunch'] + 3}))
    K.append((t_slip, {**lib.on_buckle(a1, s1, lift=0.06, off=V(0.0, -0.03, 0.0)), 'cu_' + a1: -0.35, 'hyaw': 8}))
    K.append((1.10, {'hyaw': -8}))
    t_open = {}
    if one:
        t_open[a1] = 1.35
        K.append((1.20, {**lib.on_buckle(a1, s1, lift=0.012), 'cu_' + a1: -0.3, 'hyaw': 0, 'crunch': body['crunch']}))
        K.append((1.28, {'cu_' + a1: 0.2}))
    else:
        a2, s2 = plan[1][0], plan[1][1]
        t_open[a2] = 1.08
        t_open[a1] = 1.42
        K.append((1.28, {**lib.on_buckle(a1, s1, lift=0.012), 'cu_' + a1: -0.3, 'hyaw': 0, 'crunch': body['crunch']}))
        K.append((1.36, {'cu_' + a1: 0.2}))
    for a, strap, f, pole in plan:
        to = t_open[a]
        sk = [(0.0, 0.0), (to, 0.0), (to + 0.12, 40.0), (to + 0.30, 120.0)]
        straps[strap] = sk
        sc = strap_curve(sk)
        K += follow_keys(lib, a, strap, sc, to, to + 0.12, lift=0.012)
        K.append((to + 0.12, {'cu_' + a: 0.3}))
        p40, n40, _, _ = lib.buckle(strap, 40.0)
        sg = 1 if a == 'L' else -1
        K.append((to + 0.24, {**ik_keys(a, pos=p40 + n40 * 0.08 + V(0.02 * sg, 0.04, 0.08)), 'cu_' + a: -0.3}))
        events += [{'name': 'StrapOpen', 'strap': strap, 't': to}, {'name': 'Release', 'strap': strap, 'hand': side_name(a), 't': to + 0.12}]
        # freed foot wiggles
        K.append((to + 0.30, {'fo_' + a: -22}))
        K.append((to + 0.46, {'fo_' + a: 6}))
        K.append((to + 0.60, {'fo_' + a: 0}))
    events = [{'name': 'Grab', 'strap': s, 'hand': side_name(a), 't': LEGS_GRAB} for a, s, _, _ in plan] + \
        [{'name': 'Slip', 'strap': s1, 'hand': side_name(a1), 't': t_slip}] + \
        ([{'name': 'Grab', 'strap': s1, 'hand': side_name(a1), 't': 1.20 if one else 1.28}]) + events
    t_back = max(t_open.values()) + 0.30
    # sits back up, hands back to their pad plants
    K.append((t_back + 0.22, {'pitch': 86, 'crunch': 10, 'neck': -6, 'hnod': 0, 'twist': 0, 'bend': 0, 'pr_L': 0, 'pr_R': 0,
                              **lib.sit_plant('L', lift=0.05), **lib.sit_plant('R', lift=0.05), 'cu_L': 0.0, 'cu_R': 0.0,
                              'look_w': 0.2}))
    K.append((t_back + 0.42, {**lib.sit_plant('L'), **lib.sit_plant('R'), 'pitch': 77, 'look_w': 0.0, 'neck': -4}))
    K.append((T, SIT))
    if one:
        a = sides[0]
        stem = 'Esc_Sit_UnbuckleLeg%s_v01' % a
        pre = {'closed': ['STRAP_LEG_' + a], 'open': ['STRAP_ARM_L', 'STRAP_ARM_R'], 'any': ['STRAP_LEG_' + other(a)]}
        closed0 = ['STRAP_LEG_L', 'STRAP_LEG_R']
        views = ('feet', 'side')
    else:
        stem = 'Esc_Sit_UnbuckleLegsBoth_v01'
        pre = {'closed': ['STRAP_LEG_L', 'STRAP_LEG_R'], 'open': ['STRAP_ARM_L', 'STRAP_ARM_R'], 'any': []}
        closed0 = ['STRAP_LEG_L', 'STRAP_LEG_R']
        views = ('feet', 'side')
    beats = ['0.12-0.28 looks at his feet', '0.30-0.66 leans forward, hand(s) to the shin buckle(s)',
             '%.2f grab' % LEGS_GRAB, '%.2f slip (%s)' % (t_slip, side_name(a1).lower())]
    beats += ['%.2f STRAP OPEN %s' % (t, 'STRAP_LEG_' + a) for a, t in sorted(t_open.items(), key=lambda x: x[1])]
    beats += ['%.2f-%.2f sits back up to SIT' % (t_back, T)]
    return dict(stem=stem, T=T, loop=False, start='SIT', end='SIT', pre=pre, closed0=closed0, straps=straps, keys=K,
                events=sorted(events, key=lambda e: e['t']), after={s: 'open' for _, s, _, _ in plan},
                peak=('LEGS_REACH', LEGS_GRAB) if not one else None,
                next=['Esc_Sit_UnbuckleLeg<other>_v01 if the other leg is still strapped', 'Esc_SwingOff_R_v01'],
                views=views, beats=beats)


# ===================================================================================== sitting: tug loop
T_TUG_LEGS = 1.6


def tug_legs(lib):
    SIT = lib.SIT()
    T = T_TUG_LEGS
    K = [(0.0, SIT)]
    K.append((0.14, {'pitch': 82, 'crunch': 12, 'neck': -10, 'hnod': 4, **lib.sit_plant('L', dy=0.02), **lib.sit_plant('R', dy=0.02)}))
    for i, (t0, a) in enumerate(((0.24, 'L'), (0.62, 'R'), (1.00, 'L'))):
        o = other(a)
        K.append((t0, {'klift_' + a: 0.0, 'fo_' + a: 0}))
        K.append((t0 + 0.10, {'klift_' + a: 0.028, 'fo_' + a: -26, 'toe_' + a: -14, 'pitch': 70, 'crunch': 4, 'neck': -16,
                              'hnod': -6, 'hyaw': 10 * (1 if a == 'L' else -1), 'sh_L': 6, 'sh_R': 6,
                              **lib.sit_plant(a, dy=-0.02), **lib.sit_plant(o, dy=0.03)}))
        K.append((t0 + 0.26, {'klift_' + a: 0.0, 'fo_' + a: 4, 'toe_' + a: 0, 'pitch': 80, 'crunch': 11, 'neck': -8, 'hnod': 3,
                              'hyaw': 0, 'sh_L': 0, 'sh_R': 0}))
    K.append((1.36, {**lib.sit_plant('L'), **lib.sit_plant('R'), 'fo_L': 0, 'fo_R': 0, 'pitch': 79, 'crunch': 9, 'neck': -5, 'hnod': 0}))
    K.append((T, SIT))
    return dict(stem='Esc_Sit_TugLegs_Loop_v01', T=T, loop=True, start='SIT', end='SIT',
                pre={'closed': [], 'open': ['STRAP_ARM_L', 'STRAP_ARM_R'], 'any': ['STRAP_LEG_L', 'STRAP_LEG_R'],
                     'note': 'use while at least one leg strap is closed'},
                closed0=['STRAP_LEG_L', 'STRAP_LEG_R'], straps={}, keys=K, events=[], after={},
                next=['loop', 'Esc_Sit_UnbuckleLeg*_v01'], views=('feet', 'side'),
                beats=['three alternating knee yanks against the shin straps (0.24 L, 0.62 R, 1.00 L)',
                       'trunk heaves back with each yank, palms push on the pad', 'loop seam = SIT'])


# ===================================================================================== swing off
T_SWING = 1.2


def mirror_keys(K, first):
    """Left-side version of a right-side key list: every key channel-mirrored, the first key replaced
    by the exact (unmirrored) start pose so the seam stays exact."""
    return [(0.0, first)] + [(t, E.mirror_dict(d)) for t, d in K[1:]]


def swing_off(lib, side='R'):
    if side == 'L':
        sp = swing_off(lib, 'R')
        sp.update(stem='Esc_SwingOff_L_v01', end='EDGE_L', leg_clear=0.010, keys=mirror_keys(sp['keys'], lib.SIT()), next=['Esc_HopRun_L_v01'],
                  beats=[b.replace('right', 'left').replace('EDGE_R', 'EDGE_L') for b in sp['beats']])
        return sp
    SIT = lib.SIT()
    EDGE = lib.EDGE()
    T = T_SWING
    K = [(0.0, SIT)]
    K.append((0.0, {'fl_L': 78, 'fl_R': 78}))      # FK legs = the rail pose (pelvis pitched 78 deg)
    K.append((0.12, {'hyaw': -22, 'neck': -4}))
    # knees tuck up, hands push
    K.append((0.20, {'lrail_L': 1.0, 'lrail_R': 1.0}))
    K.append((0.40, {'lrail_L': 0.0, 'lrail_R': 0.0, 'fl_L': 126, 'fl_R': 126, 'kn_L': 128, 'kn_R': 128, 'fo_L': -10, 'fo_R': -10,
                     'pitch': 74, 'crunch': 12, 'hyaw': -30, 'px': -0.02,
                     **lib.plant('L', -0.02, 0.0, 0.0, back=0.08), **lib.plant('R', -0.02, 0.0, 0.0, back=0.08)}))
    # spin on the butt toward his right edge, scooting toward the foot end (palms re-plant with the turn)
    K.append((0.58, {'yaw': -40, 'px': -0.07, 'py': -0.12, 'fl_L': 130, 'fl_R': 128, 'kn_L': 132, 'kn_R': 130, 'pitch': 78,
                     'hyaw': -18, 'crunch': 10,
                     **lib.plant('L', -0.07, -0.12, -40, lift=0.05), **lib.plant('R', -0.07, -0.12, -40, lift=0.05)}))
    K.append((0.76, {'yaw': -80, 'px': -0.14, 'py': -0.26, 'fl_L': 110, 'fl_R': 110, 'kn_L': 120, 'kn_R': 118, 'pitch': 82,
                     'hyaw': -4, 'crunch': 8, **lib.plant('L', -0.14, -0.26, -80, lift=0.03), **lib.plant('R', -0.14, -0.26, -80, lift=0.03)}))
    # legs drop over the edge, palms plant
    K.append((0.92, {**EDGE, 'yaw': -92, 'kn_L': 96, 'kn_R': 94, 'fl_L': 80, 'fl_R': 82, 'fo_L': 8, 'fo_R': 8,
                     'neck': 8, 'hnod': 8, **lib.plant('L', -0.17, -0.30, -92, lift=0.01), **lib.plant('R', -0.17, -0.30, -92, lift=0.01)}))
    K.append((1.04, {'yaw': -89, 'kn_L': 86, 'kn_R': 87, 'fl_L': 85, 'fl_R': 84, 'fo_L': -3, 'fo_R': -2, 'neck': 4, 'hnod': 4,
                     **lib.plant('L', -0.17, -0.30, -89), **lib.plant('R', -0.17, -0.30, -89)}))
    K.append((T, EDGE))
    return dict(stem='Esc_SwingOff_R_v01', T=T, loop=False, start='SIT', end='EDGE_R',
                pre={'closed': [], 'open': list(E.LIMB_STRAPS), 'any': []},
                closed0=[], straps={}, keys=K, events=[], after={},
                next=['Esc_HopRun_R_v01'], views=('three_quarter', 'side'),
                beats=['0.12 looks at his right edge', '0.20-0.40 knees tuck to the chest (clear the open straps)',
                       '0.40-0.76 spins 90 deg on his butt toward his right, scoots toward the foot end',
                       '0.76-1.04 legs drop over the edge, palms plant', '1.20 EDGE_R'])


# ===================================================================================== slump on the edge
T_SLUMP_EDGE = 2.0


def slump_edge(lib, side='R'):
    """Interrupt while sitting on the pad edge (EDGE_x, or crossfaded from late SwingOff / early HopRun):
    jolt, sags limp, is swung back onto the pad (reverse SwingOff path) and tips over backward to LIE."""
    if side == 'L':
        sp = slump_edge(lib, 'R')
        sp.update(stem='Esc_Slump_Edge_L_v01', start='EDGE_L', leg_clear=0.010, keys=mirror_keys(sp['keys'], lib.EDGE('L')),
                  beats=[b.replace('EDGE_R', 'EDGE_L').replace('right', 'left') for b in sp['beats']])
        return sp
    pl = lambda px, py, yaw, **kw: {**lib.plant('L', px, py, yaw, **kw), **lib.plant('R', px, py, yaw, **kw)}
    T = T_SLUMP_EDGE
    K = [(0.0, lib.EDGE())]
    K.append((0.08, {'pitch': 90, 'crunch': 2, 'neck': 14, 'hnod': -10, 'cu_L': -0.4, 'cu_R': -0.4, 'kn_L': 80, 'kn_R': 78,
                     **pl(-0.17, -0.30, -90, lift=0.04)}))
    K.append((0.30, {'pitch': 82, 'crunch': 14, 'neck': 14, 'hnod': 16, 'cu_L': 0.0, 'cu_R': 0.0, 'kn_L': 90, 'kn_R': 92,
                     **pl(-0.17, -0.30, -90)}))
    # swung back onto the pad: the SwingOff path backward, head still lolling
    K.append((0.58, {'yaw': -80, 'px': -0.14, 'py': -0.26, 'fl_L': 110, 'fl_R': 110, 'kn_L': 120, 'kn_R': 118, 'pitch': 82,
                     'hyaw': -6, 'crunch': 12, 'neck': 12, 'hnod': 12, **pl(-0.14, -0.26, -80, lift=0.03)}))
    K.append((0.82, {'yaw': -40, 'px': -0.07, 'py': -0.12, 'fl_L': 128, 'fl_R': 130, 'kn_L': 130, 'kn_R': 132, 'pitch': 78,
                     'hyaw': 8, 'crunch': 10, 'neck': 8, 'hnod': 10, **pl(-0.07, -0.12, -40, lift=0.05)}))
    K.append((1.02, {'yaw': 0, 'px': -0.02, 'py': 0.0, 'lrail_L': 0.0, 'lrail_R': 0.0, 'fl_L': 120, 'fl_R': 122, 'kn_L': 120,
                     'kn_R': 122, 'fo_L': -10, 'fo_R': -10, 'pitch': 74, 'crunch': 10, 'hyaw': 12,
                     **pl(-0.02, 0.0, 0.0, back=0.08)}))
    K.append((1.16, {'px': 0.0, 'fl_L': 84, 'fl_R': 84, 'kn_L': 30, 'kn_R': 32, 'fo_L': 0, 'fo_R': 0, 'pitch': 76, 'hyaw': 16,
                     **lib.sit_plant('L', lift=0.02), **lib.sit_plant('R', lift=0.02)}))
    K.append((1.26, {'lrail_L': 1.0, 'lrail_R': 1.0, 'fl_L': 78, 'fl_R': 78, 'kn_L': 0, 'kn_R': 0, 'pitch': 74, 'crunch': 6,
                     'neck': 2, 'hnod': 4, 'hyaw': 18, **lib.sit_plant('L', lift=0.03), **lib.sit_plant('R', lift=0.03)}))
    # tips over backward, limp (tail of Esc_Slump_Sit)
    K.append((1.42, {'pitch': 40, 'crunch': 2, 'neck': 8, 'hnod': 2, 'hyaw': 20, 'seat': 0.6,
                     **lib.rest_hand('L', V(0.06, 0.06, 0.14)), **lib.rest_hand('R', V(-0.06, 0.06, 0.14))}))
    K.append((1.56, {'pitch': -1.5, 'crunch': -2, 'neck': -4, 'hnod': 0, 'hyaw': 26, 'seat': 0.0,
                     **lib.rest_hand('L', V(0.0, 0.0, 0.008)), **lib.rest_hand('R', V(0.0, 0.0, 0.008))}))
    K.append((1.68, {'pitch': 3, 'crunch': 2, 'neck': 2, 'hyaw': 24, **lib.rest_hand('L', V(0.0, 0.0, 0.02)),
                     **lib.rest_hand('R', V(0.0, 0.0, 0.015))}))
    K.append((1.80, {'pitch': 0, 'crunch': 0, 'neck': 0, 'hyaw': 16, **lib.rest_hand('L'), **lib.rest_hand('R'),
                     'arail_L': 0.0, 'arail_R': 0.0}))
    K.append((1.90, {'arail_L': 1.0, 'arail_R': 1.0}))
    K.append((T, lib.rest()))
    K.append((T, {'ik_L': 1.0, 'ik_R': 1.0}))
    return dict(stem='Esc_Slump_Edge_R_v01', T=T, loop=False, start='EDGE_R', end='LIE',
                pre={'closed': [], 'open': list(E.LIMB_STRAPS), 'any': []},
                closed0=[], straps={}, keys=K, events=[{'name': 'Limp', 't': 0.30}, {'name': 'BackHitsPad', 't': 1.56}],
                after={}, next=['Op_Lie_Asleep_v01 (re-injected) or Op_Lie_Awake / Op_Panic (hit); straps stay open'],
                views=('three_quarter', 'side'),
                beats=['0.00 = EDGE_R (crossfade in from late SwingOff_R or HopRun_R before 0.30)', '0.08 jolt, fingers splay',
                       '0.30 sags limp, head drops', '0.58-1.02 swung back onto the pad (SwingOff path backward)',
                       '1.02-1.26 legs straighten into their rest line', '1.26-1.56 tips over backward, limp',
                       '1.56 back hits the pad, bounce', '2.00 LIE'])


# ===================================================================================== slumps
T_SLUMP_LIE = 1.3
T_SLUMP_SIT = 1.4


def slump_lie(lib, A, reach_c):
    """Interrupt during a wrist reach by hand A: jolt, goes limp, flops back to LIE."""
    Pp = other(A)
    sg = 1 if A == 'L' else -1
    T = T_SLUMP_LIE
    K = [(0.0, reach_c)]
    hand0 = V(reach_c['tx_' + A], reach_c['ty_' + A], reach_c['tz_' + A])
    K.append((0.07, {'neck': 14, 'hnod': -10, 'crunch': 27, 'cu_' + A: -0.4, 'cu_' + Pp: -0.3,
                     **ik_keys(A, pos=hand0 + V(0.03 * sg, 0.03, 0.07))}))
    K.append((0.20, {'neck': 2, 'hnod': 6, 'look_w': 0.0, 'crunch': 18, 'roll': -14 * sg, 'hyaw': 10 * sg,
                     **ik_keys(A, pos=V(-0.02 * sg, 0.12, 0.32), pole=V(0.5 * sg, 0.3, 1.0))}))
    K.append((0.42, {'crunch': 6, 'roll': -5 * sg, 'twist': -6 * sg, 'bend': 3 * sg, 'pr_' + A: 6, 'neck': -2, 'hnod': 4,
                     'hyaw': 22 * sg, **lib.rest_hand(A, V(0.04 * sg, 0.03, 0.10)), 'cu_' + A: 0.0, 'cu_' + Pp: 0.1}))
    K.append((0.58, {'crunch': -1.5, 'roll': 0.5 * sg, 'twist': 0, 'bend': 0, 'pr_' + A: 0, 'neck': -3, 'hyaw': 26 * sg,
                     **lib.rest_hand(A, V(0.0, 0.0, 0.0)), 'cu_' + A: 0.05}))
    K.append((0.70, {'crunch': 1.0, 'roll': 0.0, 'neck': 1.5, 'hyaw': 20 * sg, **lib.rest_hand(A, V(0.0, 0.0, 0.012))}))
    K.append((0.82, {'crunch': 0.0, **lib.rest_hand(A), 'arail_' + A: 0.0, 'neck': 0.0}))
    K.append((0.95, {'arail_' + A: 1.0, 'hyaw': 10 * sg}))
    K.append((T, lib.rest()))
    K.append((T, {'ik_' + A: 1.0, 'ik_' + Pp: 1.0}))
    strap = 'STRAP_ARM_' + Pp
    return dict(stem='Esc_Slump_LieReach%s_v01' % Pp, T=T, loop=False, start='REACH_' + Pp, end='LIE',
                pre={'closed': [strap], 'open': ['STRAP_ARM_' + A], 'any': ['STRAP_LEG_L', 'STRAP_LEG_R']},
                closed0=[strap, 'STRAP_LEG_L', 'STRAP_LEG_R'], straps={}, keys=K, events=[{'name': 'Limp', 't': 0.20}], after={},
                next=['Op_Lie_Asleep_v01 (re-injected) or Op_Lie_Awake / Op_Panic (hit)'],
                views=('wrist_' + Pp, 'side'),
                beats=['0.00 = grab pose of Esc_Lie_UnbuckleArm%s_By%s (crossfade in from any time of that clip)' % (Pp, A),
                       '0.07 jolt (head snaps back, fingers splay)', '0.20-0.58 goes limp, unrolls, arm flops back to his side',
                       '0.58-0.82 small bounce, head lolls toward his %s' % ('left' if A == 'L' else 'right'), '1.30 LIE'])


def slump_sit(lib, reach_c):
    T = T_SLUMP_SIT
    K = [(0.0, reach_c)]
    hL = V(reach_c['tx_L'], reach_c['ty_L'], reach_c['tz_L'])
    hR = V(reach_c['tx_R'], reach_c['ty_R'], reach_c['tz_R'])
    K.append((0.08, {'pitch': 104, 'crunch': 18, 'neck': -24, 'hnod': -12, 'look_w': 0.0, 'cu_L': -0.4, 'cu_R': -0.4,
                     **ik_keys('L', pos=hL + V(0.03, 0.06, 0.10)), **ik_keys('R', pos=hR + V(-0.03, 0.06, 0.10))}))
    K.append((0.26, {'pitch': 92, 'crunch': 8, 'neck': -6, 'hnod': 4, 'hyaw': 14,
                     **ik_keys('L', pos=V(0.26, -0.30, 0.22), f=V(0.2, -1, -0.2), pole=V(1, 0.3, 0.3)),
                     **ik_keys('R', pos=V(-0.26, -0.30, 0.22), f=V(-0.2, -1, -0.2), pole=V(-1, 0.3, 0.3)), 'cu_L': 0.0, 'cu_R': 0.0}))
    # tips over backward, limp
    K.append((0.50, {'pitch': 40, 'crunch': 2, 'neck': 8, 'hnod': 2, 'hyaw': 20, 'seat': 0.6, 'pr_L': 0, 'pr_R': 0,
                     **lib.rest_hand('L', V(0.06, 0.06, 0.14)), **lib.rest_hand('R', V(-0.06, 0.06, 0.14))}))
    K.append((0.66, {'pitch': -1.5, 'crunch': -2, 'neck': -4, 'hnod': 0, 'hyaw': 26, 'seat': 0.0,
                     **lib.rest_hand('L', V(0.0, 0.0, 0.008)), **lib.rest_hand('R', V(0.0, 0.0, 0.008))}))
    K.append((0.78, {'pitch': 3, 'crunch': 2, 'neck': 2, 'hyaw': 24, **lib.rest_hand('L', V(0.0, 0.0, 0.02)), **lib.rest_hand('R', V(0.0, 0.0, 0.015))}))
    K.append((0.92, {'pitch': 0, 'crunch': 0, 'neck': 0, 'hyaw': 16, **lib.rest_hand('L'), **lib.rest_hand('R'),
                     'arail_L': 0.0, 'arail_R': 0.0}))
    K.append((1.04, {'arail_L': 1.0, 'arail_R': 1.0}))
    K.append((T, lib.rest()))
    K.append((T, {'ik_L': 1.0, 'ik_R': 1.0}))
    return dict(stem='Esc_Slump_Sit_v01', T=T, loop=False, start='LEGS_REACH', end='LIE',
                pre={'closed': [], 'open': ['STRAP_ARM_L', 'STRAP_ARM_R'], 'any': ['STRAP_LEG_L', 'STRAP_LEG_R']},
                closed0=['STRAP_LEG_L', 'STRAP_LEG_R'], straps={}, keys=K, events=[{'name': 'Limp', 't': 0.26},
                                                                                     {'name': 'BackHitsPad', 't': 0.66}],
                after={}, next=['Op_Lie_Asleep_v01 (re-injected) or Op_Lie_Awake / Op_Panic (hit)'],
                views=('side', 'feet'),
                beats=['0.00 = grab pose of Esc_Sit_UnbuckleLegsBoth (crossfade in from any sitting clip)',
                       '0.08 jolt upright, hands fly off', '0.26-0.66 tips over backward, limp', '0.66 back hits the pad, bounce',
                       '1.40 LIE'])
