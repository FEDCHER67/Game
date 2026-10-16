"""Operation_v01 clips: the patient on the operating table (TABLE-ASTRA-001 v02).

Authoring frame = armature space with the rig at PatientRest (see op_core): head toward +Y, face
+Z, patient's LEFT = +X, pad top at z ~ 0. Signs used by the channels below:
  pitch about X (+) lifts anything that points +Y (trunk, head) and lowers anything that points -Y
  head yaw (+) turns the face to the patient's LEFT (away from the table camera), (-) to his RIGHT
  (toward the table camera / the instrument tray)
Every on-table pose = FK deltas on TABLE_REST + arm / leg IK that keeps the strapped segments on
authored targets + skinned-mesh pad contact solves (chest, legs, arms, head, in that order).
"""
import math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import acting_core as AC
from acting_core import R, QI, Curve, P, clamp, smooth, smoother, pnoise
import op_core as O
from op_core import X, Y, Z, SIDES, bump, psin

D = {}   # default channel values (all zero)
CHANNELS = ('breath', 'arch', 'crunch', 'twist', 'pelvis_lift', 'pelvis_roll',
            'neck', 'head_yaw', 'head_nod', 'head_tilt', 'jaw', 'settle_head')
for _s in ('L', 'R'):
    CHANNELS += tuple(c + '_' + _s for c in ('shrug', 'elev', 'wx', 'wy', 'wz', 'elbow', 'hflap', 'hlift',
                                             'htwist', 'fist', 'thumb', 'knee', 'ankz', 'lrot', 'foot', 'toe',
                                             'drum'))


SETTLE_GAP = 0.002     # a limp head rests on the pillow with this clearance (m)


def ch0():
    return {c: 0.0 for c in CHANNELS}


class TableCtx:
    def __init__(self, B, straps_open=False):
        self.B = B
        self.S = O.Stage(straps_open=straps_open)
        self.L = O.LieRig(B, self.S)
        base = self.base = B.tablerest
        self.head_axis = (base[P + 'HeadTop_End'].translation - base[P + 'Head'].translation).normalized()
        self.leg_up = {s: (base[P + s + 'UpLeg'].translation - base[P + s + 'Foot'].translation).normalized() for s, _ in SIDES}
        self.arm_line = {s: (base[P + s + 'Hand'].translation - base[P + s + 'Arm'].translation).normalized() for s, _ in SIDES}
        self.l1 = {s: self.L.leg[s]['l1'] for s, _ in SIDES}
        self.l2 = {s: self.L.leg[s]['l2'] for s, _ in SIDES}
        g = self.L.gaps(base)
        self.tr_gap = {}
        for r, m in B.region_mask.items():
            gg = g[m]
            gg = gg[~np.isnan(gg)]
            self.tr_gap[r] = float(gg.min()) if len(gg) else 1.0
        self.margin = {r: min(0.0010, v - 0.00005) for r, v in self.tr_gap.items()}
        self.solve_stats = {'chest': 0.0, 'legs': 0.0, 'arms': 0.0, 'head': 0.0}

    # ------------------------------------------------------------------ the pose
    def pose(self, c, solve=True):
        B, L, base = self.B, self.L, self.base
        self.frame_fix = {}
        q = {}
        # trunk -------------------------------------------------------------------------------
        b = c['breath']
        a = c['arch']
        k = c['crunch']
        tw = c['twist']
        q['Spine'] = R(X, 0.30 * k + 0.25 * b)
        q['Spine1'] = R(X, 0.35 * k - 0.45 * a + 0.90 * b) @ R(Y, 0.5 * tw)
        q['Spine2'] = R(X, 0.35 * k - 0.40 * a + 0.70 * b) @ R(Y, 0.5 * tw)
        q['Neck'] = R(X, c['neck'] - 1.2 * b)
        q['Head'] = R(self.head_axis, c['head_yaw']) @ R(Z, c['head_tilt']) @ R(X, c['head_nod'])
        # a chest twist drops one shoulder toward the pad: the clavicle on that side rises to follow
        auto_elev = {'L': max(0.0, tw), 'R': max(0.0, -tw)}
        for s, sgn in SIDES:
            t = s[0]
            q[s + 'Shoulder'] = R(Z, sgn * (c['shrug_' + t] + 1.2 * b)) @ R(Y, -sgn * (c['elev_' + t] + auto_elev[t]))
        # pelvis: arch about the buttock contact, roll about the opposite buttock, lift
        root = Matrix.Translation((0, 0, c['pelvis_lift']))
        if a:
            root = root @ AC.rot_about(Vector((0, -0.055, 0.0)), R(X, a))
        pr = c['pelvis_roll']
        if pr:
            piv = Vector((-0.08 if pr > 0 else 0.08, -0.05, 0.0))
            root = root @ AC.rot_about(piv, R(Y, -pr))
        out, _ = B.fk(base, q, root=root)
        if solve:
            def ap_pel(o, x):
                M = Matrix.Translation((0, 0, 0.001 * x))
                return {kk: M @ v for kk, v in o.items()}
            out, x = L.lift(out, ('pelvis',), ap_pel, margin=self.margin['pelvis'], max_angle=8, tag='pelvis')
            self.frame_fix['pelvis'] = x
            regs = ('chest',)
            def ap_chest(o, x):
                n = {kk: v.copy() for kk, v in o.items()}
                B.rotate_subtree(n, 'Spine2', R(X, x))
                return n
            out, x = L.lift(out, regs, ap_chest, margin=self.margin['chest'], max_angle=12, tag='chest')
            self.solve_stats['chest'] = max(self.solve_stats['chest'], x)
            self.frame_fix['chest'] = x
        # legs --------------------------------------------------------------------------------
        for s, sgn in SIDES:
            t = s[0]
            self._leg(out, s, sgn, c, solve)
        # arms --------------------------------------------------------------------------------
        for s, sgn in SIDES:
            t = s[0]
            self._arm(out, s, sgn, c, solve)
        # the thigh twist can press the shorts into the pad: final pelvis safety (whole body, <2 mm)
        if solve:
            gp = L.min_gap(out, ('pelvis',))
            if gp < self.margin['pelvis']:
                M = Matrix.Translation((0, 0, self.margin['pelvis'] - gp))
                out = {kk: M @ v for kk, v in out.items()}
                self.frame_fix['pelvis2'] = self.margin['pelvis'] - gp
        # head --------------------------------------------------------------------------------
        if solve:
            def ap_head(o, x):
                n = {kk: v.copy() for kk, v in o.items()}
                B.rotate_subtree(n, 'Neck', R(X, x))
                return n
            base_out = out
            out, x = L.lift(out, ('head',), ap_head, margin=self.margin['head'], max_angle=25, tag='head')
            w = c['settle_head']
            if w > 0:
                # limp head: let it rest on the pillow (contact gap SETTLE_GAP) instead of floating
                lo, hi = -30.0, 30.0
                for _ in range(26):
                    mid = 0.5 * (lo + hi)
                    if L.min_gap(ap_head(base_out, mid), ('head',)) >= SETTLE_GAP:
                        hi = mid
                    else:
                        lo = mid
                xs = hi
                x = max(x, w * xs + (1 - w) * x)
                out = ap_head(base_out, x)
            self.solve_stats['head'] = max(self.solve_stats['head'], x)
            self.frame_fix['head'] = x
        return out

    # ---- strapped segments on rails ---------------------------------------------------------------
    # The closed straps hold the distal forearm and the shin with ~7 mm clearance. A strapped segment
    # keeps its TABLE_REST line: it may only slide along it (driven by the shoulder / hip moving),
    # twist about it, and tilt a few millimetres about its contact on the pad (elbow / knee lift).
    # The upper arm / thigh then follows from the shoulder / hip to the elbow / knee.
    def _rail(self, out, upper, lower, end_sub, lift, twist, solve_len=True):
        B, base = self.B, self.base
        nU, nL = P + upper, P + lower
        Hp = out[nU].translation.copy()
        U0, L0 = base[nU], base[nL]
        K0 = L0.translation.copy()
        A0 = base[P + end_sub].translation.copy()
        d0 = (A0 - K0).normalized()
        l1 = (K0 - U0.translation).length
        M = Matrix.Identity(4)
        if lift:
            piv = Vector((A0.x, A0.y, 0.0))
            axis = d0.cross(Vector((0, 0, 1))).normalized()
            r = (K0 - piv).length
            ang = math.degrees(math.asin(clamp(lift / r, -0.5, 0.5)))
            Ma = AC.rot_about(piv, R(axis, ang))
            if (Ma @ K0).z < K0.z:
                Ma = AC.rot_about(piv, R(axis, -ang))
            M = Ma @ M
        if twist:
            dd = (M.to_3x3() @ d0).normalized()
            M = AC.rot_about(M @ K0, R(dd, twist)) @ M
        K = M @ K0
        d = (M.to_3x3() @ d0)
        d = Vector((d.x, d.y, 0.0)).normalized()      # slide parallel to the pad (keeps the height)
        v = K - Hp
        b = d.dot(v)
        cc = v.dot(v) - l1 * l1
        disc = b * b - cc
        if disc >= 0:
            r1, r2 = -b + math.sqrt(disc), -b - math.sqrt(disc)
            sl = r1 if abs(r1) < abs(r2) else r2
        else:
            sl = -b
            self.rail_miss = max(getattr(self, 'rail_miss', 0.0), math.sqrt(-disc))
        sl = clamp(sl, -0.04, 0.06)
        M = Matrix.Translation(d * sl) @ M
        K = M @ K0
        q = (K0 - U0.translation).rotation_difference(K - Hp)
        Um = (q.to_matrix() @ U0.to_3x3()).to_4x4()
        Um.translation = Hp
        if twist:
            Um = AC.rot_about(Hp, R((K - Hp).normalized(), twist * 0.25)) @ Um
        out[nU] = Um
        for n in B.subtree(lower):
            out[n] = M @ base[n]
        return M, sl

    def _leg(self, out, s, sgn, c, solve):
        B, L = self.B, self.L
        t = s[0]
        h0 = clamp(c['knee_' + t], 0.0, 0.032)
        tw = clamp(sgn * c['lrot_' + t], -26, 26)

        def apply(o, x):
            n = {kk: v.copy() for kk, v in o.items()}
            M, sl = self._rail(n, s + 'UpLeg', s + 'Leg', s + 'Foot', h0 + 0.001 * x, tw)
            Xm = (M.to_3x3() @ Vector(X)).normalized()
            if c['foot_' + t]:
                B.rotate_subtree(n, s + 'Foot', R(Xm, c['foot_' + t]))
            if c['toe_' + t]:
                B.rotate_subtree(n, s + 'ToeBase', R(Xm, c['toe_' + t]))
            return n
        n = apply(out, 0.0)
        if solve:
            n, x = L.lift(n, ('leg_' + s,), lambda o, x: apply(out, x), margin=self.margin['leg_' + s], max_angle=12, tag='leg')
            self.solve_stats['legs'] = max(self.solve_stats['legs'], x)
            self.frame_fix['leg_' + s] = x
        out.update(n)

    def _arm(self, out, s, sgn, c, solve):
        B, L = self.B, self.L
        t = s[0]
        e0 = 0.0                                      # the strapped forearm cannot lift its elbow
        tw = clamp(sgn * c['htwist_' + t], -6, 6)

        def apply(o, x):
            n = {kk: v.copy() for kk, v in o.items()}
            M, sl = self._rail(n, s + 'Arm', s + 'ForeArm', s + 'Hand', 0.0, tw * max(0.0, 1.0 - 0.15 * x))
            d = (M.to_3x3() @ self.arm_line[s]).normalized()
            W = n[P + s + 'Hand'].translation
            hq = R(Z, sgn * c['hflap_' + t]) @ R(X, -c['hlift_' + t])
            if c['hflap_' + t] or c['hlift_' + t]:
                B.rotate_subtree(n, s + 'Hand', hq, pivot=W)
            self._fingers(n, s, sgn, c)
            return n
        n = apply(out, 0.0)
        if solve:
            n, x = L.lift(n, ('arm_' + s,), lambda o, x: apply(out, x), margin=self.margin['arm_' + s], max_angle=12, tag='arm')
            self.solve_stats['arms'] = max(self.solve_stats['arms'], x)
            self.frame_fix['arm_' + s] = x
        out.update(n)

    def _fingers(self, n, s, sgn, c):
        t = s[0]
        f = c['fist_' + t]
        dr = c['drum_' + t]
        per = None
        if dr:
            # drumming: index, middle, ring lift in a ripple (dr = phase in cycles)
            per = {}
            for i, fn in enumerate(('Index', 'Middle', 'Ring', 'Pinky')):
                ph = 2 * math.pi * (dr - 0.18 * i)
                per[fn] = f - 0.22 * max(0.0, math.sin(ph))
        if f or per:
            self.B.curl(n, s, f, thumb=c['thumb_' + t] if c['thumb_' + t] else f * 0.6, per=per)
        elif c['thumb_' + t]:
            self.B.curl(n, s, 0.0, thumb=c['thumb_' + t])


def table_canonical(ctx, N, pose0=None):
    vals = ctx.B.tablerest_values if pose0 is None else ctx.B.values_from_pose(pose0)
    return {1.0: vals, float(N + 1): vals}


# ======================================================================================== AWAKE
T_AWAKE = 4.0


def awake_channels():
    T = T_AWAKE
    cv = {}
    cv['head_yaw'] = Curve([(0, 0), (0.30, 0), (0.38, 4), (0.56, -40), (0.64, -36), (1.25, -33, 'flat'), (1.42, 2),
                            (1.52, -2), (1.62, 0, 'flat'), (1.86, 0), (2.0, 33), (2.08, 29), (2.45, 30, 'flat'),
                            (2.62, -4), (2.72, 0, 'flat'), (3.30, 0), (3.42, -12), (3.55, 8), (3.68, 0, 'flat'), (T, 0)], periodic=True)
    cv['neck'] = Curve([(0, 0), (2.70, 0, 'flat'), (2.86, 16), (2.95, 14), (3.30, 15, 'flat'), (3.50, 0), (3.58, 2.5),
                        (3.68, 0, 'flat'), (T, 0)], periodic=True)
    cv['head_nod'] = Curve([(0, 0), (1.62, 0, 'flat'), (1.70, 6), (1.78, 0, 'flat'), (2.86, 0), (2.98, 7), (3.25, 8, 'flat'),
                            (3.42, 0, 'flat'), (T, 0)], periodic=True)
    cv['head_tilt'] = Curve([(0, 0), (0.56, -5), (1.25, -6), (1.5, 0), (2.0, 5), (2.45, 4), (2.7, 0, 'flat'), (T, 0)], periodic=True)
    # nervous fists while staring at the doctor, finger drumming, thumbs
    cv['fist_R'] = Curve([(0, 0), (0.50, 0, 'flat'), (0.62, 0.45), (1.25, 0.40, 'flat'), (1.5, 0.12), (2.9, 0.12),
                          (3.05, 0.0, 'flat'), (T, 0)], periodic=True)
    cv['fist_L'] = Curve([(0, 0), (0.55, 0, 'flat'), (0.68, 0.35), (1.25, 0.3, 'flat'), (1.55, 0.0, 'flat'), (2.85, 0, 'flat'),
                          (2.97, 0.4), (3.3, 0.38, 'flat'), (3.5, 0.0, 'flat'), (T, 0)], periodic=True)
    cv['shrug'] = Curve([(0, 0), (0.45, 0, 'flat'), (0.6, 5), (1.2, 4.5, 'flat'), (1.5, 0, 'flat'), (2.85, 0, 'flat'),
                         (2.97, 4), (3.35, 3.5, 'flat'), (3.6, 0, 'flat'), (T, 0)], periodic=True)
    cv['feet'] = Curve([(0, 0), (1.55, 0, 'flat'), (1.8, 1), (2.6, 1, 'flat'), (2.8, 0, 'flat'), (T, 0)], periodic=True)
    cv['gulp'] = Curve([(0, 0), (1.60, 0, 'flat'), (1.68, 1), (1.80, 0, 'flat'), (T, 0)], periodic=True)
    return cv


class AwakeCtx(TableCtx):
    def __init__(self, B):
        super().__init__(B)
        self.cv = awake_channels()
        T = T_AWAKE
        self.n1 = pnoise(T, 11, cycles=(9, 13, 17))
        self.n2 = pnoise(T, 12, cycles=(10, 14, 19))


def awake_pose(ctx, t):
    T = T_AWAKE
    cv = ctx.cv
    c = ch0()
    c['breath'] = 0.5 * (1 - math.cos(2 * math.pi * 3 * t / T))
    c['head_yaw'] = cv['head_yaw'](t) + 1.2 * ctx.n1(t)
    c['neck'] = cv['neck'](t)
    c['head_nod'] = cv['head_nod'](t) + 3.0 * cv['gulp'](t)
    c['head_tilt'] = cv['head_tilt'](t)
    sh = cv['shrug'](t)
    c['shrug_L'] = c['shrug_R'] = sh
    c['elev_L'] = c['elev_R'] = 0.4 * sh
    c['fist_R'] = cv['fist_R'](t)
    c['fist_L'] = cv['fist_L'](t)
    # right hand drums its fingers 1.55-2.85 s (6 taps), left thumb twiddles 0.7-1.3 s
    w = bump(t, 1.50, 2.90, 0.1, 0.1)
    c['drum_R'] = 4.5 * (t - 1.5) / 1.0 * w if w else 0.0
    if w:
        c['fist_R'] = max(c['fist_R'], 0.25 * w)
    tw = bump(t, 0.65, 1.35, 0.15, 0.15)
    c['thumb_L'] = tw * (0.4 + 0.35 * math.sin(2 * math.pi * 3.0 * (t - 0.65)))
    # feet: wiggle (leg rotation) and point, out of phase; toes curl
    f = cv['feet'](t)
    c['lrot_L'] = f * 9 * math.sin(2 * math.pi * 2.5 * (t - 1.55))
    c['lrot_R'] = f * 9 * math.sin(2 * math.pi * 2.5 * (t - 1.55) + 2.0)
    c['foot_L'] = -f * 16 * (0.5 + 0.5 * math.sin(2 * math.pi * 2.5 * (t - 1.55) - 1.2))
    c['foot_R'] = -f * 16 * (0.5 + 0.5 * math.sin(2 * math.pi * 2.5 * (t - 1.55) + 0.8))
    c['toe_L'] = -f * 12 * (0.5 + 0.5 * math.sin(2 * math.pi * 2.5 * (t - 1.55) - 0.4))
    c['toe_R'] = -f * 12 * (0.5 + 0.5 * math.sin(2 * math.pi * 2.5 * (t - 1.55) + 1.6))
    # a small squirm of the shoulders while looking right (wriggle against the pad)
    c['twist'] = 2.0 * bump(t, 0.5, 1.4) * math.sin(2 * math.pi * 2.0 * (t - 0.5)) + 0.4 * ctx.n2(t)
    return ctx.pose(c), {'fix': dict(ctx.frame_fix)}


# ======================================================================================== ASLEEP
T_ASLEEP = 5.0


class AsleepCtx(TableCtx):
    def __init__(self, B):
        super().__init__(B)
        T = T_ASLEEP
        self.n1 = pnoise(T, 21, cycles=(1, 2, 3))
        self.twitch_foot = Curve([(0, 0), (3.30, 0, 'flat'), (3.36, 1), (3.44, 0.15), (3.50, 0.6), (3.62, 0, 'flat'), (T, 0)], periodic=True)
        self.twitch_hand = Curve([(0, 0), (1.20, 0, 'flat'), (1.26, 1), (1.40, 0, 'flat'), (T, 0)], periodic=True)


def asleep_base(c):
    """The lolled sleeping pose (relative to TABLE_REST): head rolled toward the table camera."""
    c['head_yaw'] = -30.0
    c['head_tilt'] = -9.0
    c['head_nod'] = 4.0
    c['elbow_L'] = c['elbow_R'] = 4.0          # slack elbows
    c['lrot_L'] = c['lrot_R'] = 11.0          # feet flop outward
    c['foot_L'] = c['foot_R'] = 1.5
    c['fist_L'] = c['fist_R'] = 0.18          # fingers relax into a loose curl
    c['settle_head'] = 1.0
    c['hflap_L'] = c['hflap_R'] = 0.0
    return c


def asleep_pose(ctx, t):
    T = T_ASLEEP
    c = asleep_base(ch0())
    # two deep breaths per loop: slow inhale, short pause, longer exhale
    ph = (t % (T / 2)) / (T / 2)
    br = smoother(ph / 0.42) if ph < 0.42 else (1.0 if ph < 0.50 else 1.0 - smoother((ph - 0.50) / 0.50))
    c['breath'] = 2.2 * br
    c['crunch'] = 0.6 * br
    c['head_nod'] += -2.0 * br                 # the head rocks back a little on each inhale
    c['head_yaw'] += 1.5 * ctx.n1(t)
    tf = ctx.twitch_foot(t)
    c['foot_R'] += -14 * tf
    c['toe_R'] = -12 * tf
    th = ctx.twitch_hand(t)
    c['fist_L'] += 0.25 * th
    return ctx.pose(c), {'fix': dict(ctx.frame_fix)}


# ======================================================================================== helpers
def pulse(t, t0, rise, hold, fall):
    """0 -> 1 -> 0 envelope: rise over `rise` s from t0, hold, fall (smoother ramps)."""
    if t < t0 or t > t0 + rise + hold + fall:
        return 0.0
    if t < t0 + rise:
        return smoother((t - t0) / rise)
    if t < t0 + rise + hold:
        return 1.0
    return 1.0 - smoother((t - t0 - rise - hold) / fall)


def kick(t, t0, rise=0.07, fall=0.16, over=0.18):
    """Snappy yank: fast rise to 1, fall slightly past 0 (small rebound), settle."""
    if t < t0:
        return 0.0
    u = t - t0
    if u < rise:
        return smoother(u / rise)
    u -= rise
    if u < fall:
        return 1.0 - (1.0 + over) * smoother(u / fall)
    u -= fall
    if u < 0.12:
        return -over * (1.0 - smoother(u / 0.12))
    return 0.0


# ======================================================================================== STRUGGLE
T_STRUGGLE = 2.5


class StruggleCtx(TableCtx):
    def __init__(self, B, T=T_STRUGGLE, panic=False):
        super().__init__(B)
        self.T = T
        self.panic = panic
        self.nz = {k: pnoise(T, 31 + i, cycles=(int(11 * T), int(13 * T), int(17 * T))) for i, k in
                   enumerate(('chest', 'head', 'armL', 'armR', 'legL', 'legR'))}


def struggle_pose(ctx, t):
    T = ctx.T
    c = ch0()
    # breathing: hard panting (5 per loop)
    c['breath'] = 1.4 * 0.5 * (1 - math.cos(2 * math.pi * 5 * t / T))
    # BUCK (0.20-0.70): arch against the torso strap, both arms yank, head strains up
    b1 = pulse(t, 0.20, 0.13, 0.17, 0.20)
    ant = pulse(t, 0.06, 0.08, 0.02, 0.10)          # anticipation: shoulders sink, chin tucks
    bo1 = pulse(t, 0.70, 0.05, 0.0, 0.12)           # landing bounce
    # TWIST HEAVE (1.26-2.0): crunch up, twist left then right
    h2 = pulse(t, 1.26, 0.14, 0.38, 0.22)
    twist = 8.0 * math.sin(2 * math.pi * (t - 1.36) / 0.5) * pulse(t, 1.34, 0.08, 0.34, 0.12)
    bo2 = pulse(t, 1.98, 0.05, 0.0, 0.12)
    c['arch'] = 7.0 * b1 + 1.0 * bo1
    c['pelvis_lift'] = 0.0
    c['crunch'] = 7.5 * h2 + 1.5 * bo2
    c['twist'] = twist
    c['neck'] = 17.0 * b1 + 20.0 * h2 + 3.0 * bo1
    c['head_nod'] = 6.0 * h2 + 4.0 * ant
    # head shakes "no-no-no" (0.72-1.26) and a look to the table camera "help!" (1.98-2.38)
    shake = pulse(t, 0.72, 0.06, 0.38, 0.10)
    c['head_yaw'] = (32.0 * shake * math.sin(2 * math.pi * 3.4 * (t - 0.72)) - 30.0 * pulse(t, 1.98, 0.08, 0.20, 0.12)
                     + 1.5 * twist + 2.0 * ctx.nz['head'](t))
    c['head_tilt'] = -8.0 * shake * math.sin(2 * math.pi * 3.4 * (t - 0.72) - 0.6)
    # arms: both yank in the buck, then alternate L / R / L, then with the twist
    yL = max(b1, kick(t, 0.76), kick(t, 1.08), 0.9 * pulse(t, 1.36, 0.08, 0.14, 0.10))
    yR = max(b1, kick(t, 0.92), 0.9 * pulse(t, 1.58, 0.08, 0.14, 0.12), 0.6 * kick(t, 2.08))
    # fists clench a little ahead of each yank and release slowly (finger key steps stay small)
    fz = {'L': max(pulse(t, 0.68, 0.14, 0.10, 0.18), pulse(t, 1.00, 0.14, 0.06, 0.18), 0.9 * pulse(t, 1.30, 0.12, 0.14, 0.14)),
          'R': max(pulse(t, 0.84, 0.14, 0.06, 0.18), 0.9 * pulse(t, 1.52, 0.12, 0.14, 0.14), 0.6 * pulse(t, 2.00, 0.14, 0.04, 0.16))}
    for s, y in (('L', yL), ('R', yR)):
        c['wy_' + s] = 0.016 * y
        c['wz_' + s] = 0.003 * max(0.0, y)
        c['shrug_' + s] = 6.0 * y
        c['elev_' + s] = 3.0 * y
        c['elbow_' + s] = 12.0 * y
        c['fist_' + s] = (0.25 + 0.75 * max(fz[s], 0.4 * b1, 0.6 * h2)) * pulse(t, 0.0, 0.16, T - 0.36, 0.20)
        c['hlift_' + s] = 8.0 * max(0.0, y)
        c['htwist_' + s] = 10.0 * y
    # legs: knees pump against the shin straps, feet kick and wiggle
    kL = max(0.7 * b1, kick(t, 0.80), kick(t, 1.12), 0.5 * kick(t, 2.02))
    kR = max(0.7 * b1, kick(t, 0.96), kick(t, 1.62), 0.5 * kick(t, 2.18))
    wig = pulse(t, 0.55, 0.15, 1.45, 0.30)
    for s, k_, ph in (('L', kL, 0.0), ('R', kR, 2.2)):
        k_ = max(0.0, k_)
        c['knee_' + s] = 0.022 * k_
        c['foot_' + s] = -24.0 * k_ - 8.0 * wig * (0.5 + 0.5 * math.sin(2 * math.pi * 3 * (t - 0.55) + ph))
        c['lrot_' + s] = 12.0 * wig * math.sin(2 * math.pi * 2.6 * (t - 0.55) + ph)
        c['toe_' + s] = -15.0 * k_
    # effort tremor while straining (buck and heave)
    tr = max(b1, h2)
    c['arch'] += 0.8 * tr * ctx.nz['chest'](t)
    c['neck'] += 2.5 * tr * ctx.nz['head'](t)
    for s, k in (('L', 'armL'), ('R', 'armR')):
        c['shrug_' + s] += 1.5 * tr * ctx.nz[k](t)
        c['fist_' + s] += 0.08 * tr * ctx.nz[k](t)
    return ctx.pose(c), {'fix': dict(ctx.frame_fix)}


# ======================================================================================== PANIC
T_PANIC = 2.0


def panic_pose(ctx, t):
    """Stronger, faster struggle: a horrified stare at his belly, whipping head, alternating yanks."""
    T = ctx.T
    c = ch0()
    c['breath'] = 1.8 * 0.5 * (1 - math.cos(2 * math.pi * 6 * t / T))
    on = pulse(t, 0.0, 0.12, T - 0.30, 0.18)       # ramps in and out at the seam
    b1 = pulse(t, 0.18, 0.09, 0.14, 0.14)
    b2 = pulse(t, 1.10, 0.09, 0.14, 0.14)
    look = pulse(t, 0.50, 0.10, 0.35, 0.12)        # lifts the head and stares at his belly
    look2 = pulse(t, 1.45, 0.10, 0.20, 0.15)
    bb = max(b1, b2)
    c['arch'] = 7.5 * bb + 1.5 * on * (0.5 + 0.5 * math.sin(2 * math.pi * 6 * t / T))
    c['pelvis_lift'] = 0.0
    c['crunch'] = 6.5 * look + 4.0 * look2
    c['twist'] = 7.0 * on * math.sin(2 * math.pi * 3 * t / T) * (1 - bb)
    c['neck'] = 22.0 * look + 16.0 * bb + 10.0 * look2
    c['head_nod'] = 10.0 * look + 4.0 * look2
    # head whips side to side (5 whips per loop), frozen while staring at the belly
    whip = on * (1 - look) * (1 - 0.6 * look2)
    c['head_yaw'] = 40.0 * whip * math.sin(2 * math.pi * 5 * t / T) + 3.0 * ctx.nz['head'](t)
    c['head_tilt'] = -10.0 * whip * math.sin(2 * math.pi * 5 * t / T - 0.5)
    # arms: 6 alternating yanks per loop (3 Hz), both together in the bucks
    ph = 2 * math.pi * 6 * t / T
    yL = on * max(0.0, math.sin(ph)) ** 0.7
    yR = on * max(0.0, -math.sin(ph)) ** 0.7
    for s, y in (('L', yL), ('R', yR)):
        y = max(y, bb)
        c['wy_' + s] = 0.022 * y
        c['wz_' + s] = 0.004 * y
        c['shrug_' + s] = 4.5 * y + 1.0 * on * ctx.nz['arm' + s](t)
        c['elev_' + s] = 3.5 * y
        c['elbow_' + s] = 15.0 * y
        c['fist_' + s] = 1.0 * on
        c['hlift_' + s] = 6.0 * y
        c['htwist_' + s] = 14.0 * y
    # legs: fast alternating pumps (4 per loop each) and flailing feet
    for s, phl in (('L', 0.0), ('R', math.pi)):
        k = on * max(0.0, math.sin(2 * math.pi * 4 * t / T + phl)) ** 0.8
        k = max(k, 0.8 * bb)
        c['knee_' + s] = 0.026 * k
        c['foot_' + s] = -28.0 * k - 6.0 * on
        c['lrot_' + s] = 16.0 * on * math.sin(2 * math.pi * 6 * t / T + phl + 0.8)
        c['toe_' + s] = -20.0 * k
    c['arch'] += 1.0 * on * ctx.nz['chest'](t)
    return ctx.pose(c), {'fix': dict(ctx.frame_fix)}


# ======================================================================================== DEAD / SHOCK
T_DEAD = 2.0
T_SHOCK = 2.0


def dead_base(c):
    """Limp pose on the table: head rolled toward the table camera, arms slack, feet flopped out."""
    c['head_yaw'] = -47.0
    c['head_tilt'] = -13.0
    c['head_nod'] = 7.0
    c['shrug_L'] = c['shrug_R'] = 0.0
    c['elev_L'] = c['elev_R'] = -1.0
    c['elbow_L'] = c['elbow_R'] = 6.0
    c['hflap_L'] = c['hflap_R'] = 4.0
    c['htwist_L'] = c['htwist_R'] = -6.0
    c['fist_L'] = c['fist_R'] = 0.12
    c['thumb_L'] = c['thumb_R'] = 0.05
    c['lrot_L'] = c['lrot_R'] = 25.0
    c['foot_L'] = c['foot_R'] = 3.0
    c['settle_head'] = 1.0
    return c


class DeadCtx(TableCtx):
    def __init__(self, B):
        super().__init__(B)
        self.dead = self.pose(dead_base(ch0()))


def dead_pose(ctx, t):
    return {k: v.copy() for k, v in ctx.dead.items()}, {}


class ShockCtx(TableCtx):
    def __init__(self, B):
        super().__init__(B)
        self.T = T_SHOCK
        self.dead_c = dead_base(ch0())
        self.dead = self.pose(dict(self.dead_c))
        self.nz = {k: pnoise(1.0, 51 + i, cycles=(14, 17, 23)) for i, k in
                   enumerate(('chest', 'head', 'yaw', 'armL', 'armR', 'legL', 'legR'))}


def shock_pose(ctx, t):
    if t >= 1.80 - 1e-9:
        return {k: v.copy() for k, v in ctx.dead.items()}, {'phase': 'dead'}
    c = ch0()
    jolt = pulse(t, 0.04, 0.07, 0.36, 0.13)         # rigid electrified arch, 0.04-0.60
    zap = pulse(t, 0.10, 0.03, 0.32, 0.06)          # 14-23 Hz tremor while rigid
    bounce = pulse(t, 0.58, 0.05, 0.0, 0.10)
    tw1 = pulse(t, 0.76, 0.04, 0.03, 0.10)          # twitch: right leg kick + shoulder
    tw2 = pulse(t, 1.00, 0.05, 0.02, 0.10)          # twitch: left fingers + head
    limp = smoother(clamp((t - 1.12) / 0.55))       # rolls into the dead pose 1.12-1.67
    c['arch'] = 8.0 * jolt + 1.2 * zap * ctx.nz['chest'](t)
    c['crunch'] = 4.0 * jolt
    c['pelvis_lift'] = 0.0
    c['neck'] = 24.0 * jolt + 4.0 * zap * ctx.nz['head'](t) + 3.0 * bounce
    c['head_nod'] = -12.0 * jolt
    c['head_yaw'] = 7.0 * zap * ctx.nz['yaw'](t) + 9.0 * tw2
    for s in ('L', 'R'):
        c['shrug_' + s] = 7.0 * jolt + 1.5 * zap * ctx.nz['arm' + s](t)
        c['elev_' + s] = 4.0 * jolt
        c['wy_' + s] = 0.012 * jolt
        c['wz_' + s] = 0.003 * jolt
        c['elbow_' + s] = 16.0 * jolt
        c['fist_' + s] = -0.40 * jolt                # fingers splayed
        c['thumb_' + s] = -0.3 * jolt
        c['hlift_' + s] = 6.0 * jolt
        c['foot_' + s] = -30.0 * jolt + 5.0 * zap * ctx.nz['leg' + s](t)
        c['toe_' + s] = -18.0 * jolt
        c['lrot_' + s] = -6.0 * jolt
    c['shrug_R'] += 7.0 * tw1
    c['knee_R'] = 0.022 * tw1
    c['foot_R'] += -24.0 * tw1
    c['fist_L'] += 0.35 * tw2 - 0.15 * pulse(t, 1.12, 0.06, 0.02, 0.10)
    c['head_nod'] += 4.0 * tw2
    # every channel rolls into the dead pose; the head overshoots the roll a little and settles
    d = ctx.dead_c
    for k in c:
        c[k] = c[k] * (1 - limp) + d.get(k, 0.0) * limp
    c['head_yaw'] += -6.0 * pulse(t, 1.40, 0.18, 0.0, 0.22)
    return ctx.pose(c), {'fix': dict(ctx.frame_fix)}


# ======================================================================================== ESCAPE / KO
# Unrestrained escape over the patient's LEFT pad edge (armature +X = table -X = Unity +X): the
# instrument stand stands on his right (TrayAnchor table (0.57, 0.29)) at only 6.5 cm from the pad,
# where hanging legs would pass through the tray. On the left the open straps stand up as hooks:
# torso hook at armature y -0.093..-0.017, leg hook at y -0.658..-0.582, so he first scoots toward
# the foot end and swings his legs off between them (hips at y ~ -0.34).
# Channels (degrees, metres; armature axes of the TABLE_REST base, carried by the parent):
#   root: px py pz (hips offset), yaw (about Z, + turns the legs toward +X), pitch (about X, + sits
#   up; 180 = prone, face down), roll (about Y)
#   trunk: crunch, twist, bend; neck, hnod (+ chin down), hyaw (about the head axis)
#   legs (L/R): fl hip flexion, ab abduction, lr external rotation, kn knee, fo foot (+ points)
#   arms (L/R): afl forward flexion, aab abduction, atw twist, sh shrug, el elbow, cu finger curl
T_ESCAPE = 3.0
T_KO = 4.0
FLOOR_Z = -O.PAD_Z            # floor in armature space (rig at PatientRest)
FLOOR_GAP = 0.001
EF_CH = ('px', 'py', 'pz', 'yaw', 'pitch', 'roll', 'crunch', 'twist', 'bend', 'neck', 'hnod', 'hyaw')
for _s in ('L', 'R'):
    EF_CH += tuple(c + '_' + _s for c in ('fl', 'ab', 'lr', 'kn', 'fo', 'afl', 'aab', 'atw', 'sh', 'el', 'cu'))


def efk(**kw):
    d = {}
    for k, v in kw.items():
        if k.endswith('_B'):
            d[k[:-2] + '_L'] = v
            d[k[:-2] + '_R'] = v
        else:
            d[k] = v
    return d


def ko_channels():
    """KO pose (prone splat on the floor, head toward +X, face turned toward -Y = the table's foot end)."""
    return efk(px=1.50, py=-0.36, pz=0.0, yaw=90, pitch=180, roll=-6, crunch=-4, twist=0, bend=4,
               neck=-32, hnod=-6, hyaw=-78,
               fl_L=9.5, ab_L=30, lr_L=85, kn_L=50, fo_L=33,
               fl_R=12, ab_R=9, lr_R=10, kn_R=6, fo_R=50,
               afl_L=177, aab_L=40, atw_L=0, sh_L=6, el_L=40, cu_L=0.25,
               afl_R=9, aab_R=16, atw_R=-30, sh_R=0, el_R=12, cu_R=0.2)


def escape_keys():
    """(time, channel overrides); every key inherits the previous one."""
    K = []
    K.append((0.00, {}))
    K.append((0.12, efk(neck=6, hyaw=10)))
    # realises the straps are open: head up, looks at his left arm
    K.append((0.30, efk(neck=24, hnod=4, hyaw=32, crunch=4, afl_L=8, el_L=10, cu_B=0.3)))
    # panic sit-up, knees tuck to the chest, arms flail forward
    K.append((0.52, efk(pitch=40, crunch=16, neck=14, hnod=0, hyaw=10, pz=0.02, py=-0.08,
                        fl_B=100, kn_B=120, fo_B=-10, afl_L=70, aab_L=30, el_L=40, afl_R=55, aab_R=40, el_R=50, cu_B=0.6)))
    # spins on the butt toward the left edge (knees still tucked high), scooting toward the foot end
    K.append((0.70, efk(pitch=66, crunch=12, yaw=34, px=0.06, py=-0.19, pz=0.05, roll=-3, neck=10, hyaw=-6,
                        fl_B=128, kn_B=135, ab_L=4, ab_R=0, afl_L=45, aab_L=50, el_L=60, afl_R=10, aab_R=25, el_R=40)))
    K.append((0.84, efk(pitch=76, crunch=8, yaw=72, px=0.15, py=-0.24, pz=0.05, roll=-1, neck=12, hyaw=-4,
                        fl_B=126, kn_B=128, afl_L=10, aab_L=0, el_L=30, afl_R=-10, aab_R=10, el_R=20)))
    # sits on the left edge, legs over it, hands on the pad behind (IK); looks down at the floor
    K.append((0.98, efk(pitch=80, crunch=6, yaw=90, px=0.21, py=-0.34, pz=-0.01, roll=0, neck=16, hnod=10, hyaw=0,
                        fl_B=82, kn_B=88, fo_B=-6, ab_L=8, ab_R=8, lr_B=4,
                        afl_L=-20, aab_L=12, el_L=8, afl_R=-20, aab_R=12, el_R=8, atw_B=0, cu_B=0.1)))
    K.append((1.14, efk(neck=22, hnod=14, hyaw=-6, crunch=8, sh_B=6)))     # gulp, peeks over the edge
    # pushes off: leans forward, arms push
    K.append((1.30, efk(pitch=104, crunch=10, px=0.32, pz=-0.04, neck=4, hnod=0, hyaw=0, sh_B=0,
                        fl_B=70, kn_B=70, fo_B=10, afl_L=10, aab_L=-4, el_L=20, afl_R=20, aab_R=-14, el_R=20)))
    # lands on the floor, knees bent, arms forward for balance
    K.append((1.48, efk(pitch=96, crunch=8, px=0.50, py=-0.36, pz=-0.20, neck=10,
                        fl_B=40, kn_B=62, fo_B=6, ab_L=10, ab_R=10, afl_L=75, aab_L=-2, el_L=30,
                        afl_R=70, aab_R=0, el_R=30, cu_B=0.0)))
    # wobbly anaesthesia legs: a stagger step away from the table, knees knock, windmill arms
    K.append((1.62, efk(pitch=104, crunch=12, px=0.64, pz=-0.30, roll=6, neck=-6, hyaw=18,
                        fl_B=55, kn_B=90, ab_L=-6, ab_R=-6, lr_L=-18, lr_R=-18,
                        afl_L=130, aab_L=0, el_L=40, afl_R=20, aab_R=60, el_R=50)))
    K.append((1.76, efk(pitch=118, roll=-8, px=0.76, pz=-0.34, neck=-12, hyaw=-14,
                        fl_B=55, kn_B=80, afl_L=30, aab_L=10, el_L=60, afl_R=125, aab_R=40, el_R=30)))
    # topples face first (feet stay planted, the body pivots over them)
    K.append((1.92, efk(pitch=150, roll=-4, px=1.10, pz=-0.42, crunch=4, neck=-20, hnod=-10, hyaw=-30,
                        fl_B=50, kn_B=30, lr_L=0, lr_R=0, ab_L=8, ab_R=8, fo_B=10,
                        afl_L=150, aab_L=40, el_L=20, afl_R=140, aab_R=45, el_R=20)))
    # SPLAT
    K.append((2.06, efk(pitch=182, roll=-6, px=1.46, py=-0.36, pz=-0.55, crunch=-6, neck=-18, hnod=-6, hyaw=-60,
                        fl_B=-6, kn_B=20, fo_B=20, ab_L=20, ab_R=10,
                        afl_L=165, aab_L=50, el_L=15, afl_R=60, aab_R=40, el_R=10, cu_B=0.0)))
    # bounce: feet flip up, head bounces
    K.append((2.18, efk(pitch=177, px=1.49, crunch=-2, neck=-8, hyaw=-70, fl_L=4, fl_R=-8, kn_L=48, kn_R=38,
                        afl_L=158, aab_L=46, afl_R=40, aab_R=25)))
    K.append((2.32, efk(pitch=181, crunch=-5, neck=-16, hyaw=-76, kn_L=30, kn_R=10, fl_R=-4)))
    ko = ko_channels()
    K.append((2.62, dict(ko)))
    K.append((3.00, dict(ko)))
    return K


class EscapeCtx(TableCtx):
    def __init__(self, B, ko=False):
        super().__init__(B, straps_open=True)
        base = self.base
        self.hip0 = base[P + 'Hips'].translation.copy()
        self.arm_axis = {s: (base[P + s + 'ForeArm'].translation - base[P + s + 'Arm'].translation).normalized() for s, _ in SIDES}
        self.leg_axis = {s: (base[P + s + 'Foot'].translation - base[P + s + 'UpLeg'].translation).normalized() for s, _ in SIDES}
        keys = escape_keys()
        cur = {c: 0.0 for c in EF_CH}
        seq = []
        for t, d in keys:
            cur = dict(cur)
            cur.update(d)
            seq.append((t, cur))
        self.seq = seq
        self.curves = {c: Curve([(t, v[c]) for t, v in seq]) for c in EF_CH}
        self.ko_mode = ko
        self.stats = {'floor_lift_max': 0.0, 'pad_lift_max': 0.0}
        if not ko:
            # pre-pass: fold the vertical contact solve into the hips-height keys, so the per-frame
            # solve only removes interpolation residue (no hips pops between keys)
            for _ in range(3):
                new = []
                for t, v in self.seq:
                    v = dict(v)
                    if t > 0.0 and t < T_ESCAPE:
                        _, dz = self.contact(self.fk(v, t), t)
                        v['pz'] += dz
                    new.append((t, v))
                self.seq = new
                self.curves = {c: Curve([(t, v[c]) for t, v in self.seq]) for c in EF_CH}
        self.ko_c = {c: 0.0 for c in EF_CH}
        self.ko_c.update(ko_channels())
        self.ko_mode = ko
        self.nz = pnoise(T_KO, 77, cycles=(1, 2, 3))
        self.stats = {'floor_lift_max': 0.0, 'pad_lift_max': 0.0}

    def channels(self, t):
        return {c: self.curves[c](t) for c in EF_CH}

    def hands_on_pad(self, out, w):
        """Seated on the edge: both palms planted on the pad behind and beside the hips (IK)."""
        B, L = self.B, self.L
        h = out[P + 'Hips'].translation
        for s, sgn in SIDES:
            other = {k: v.copy() for k, v in out.items()}
            # his left is +Y once he faces +X (yaw 90)
            tgt = Vector((h.x - 0.14, h.y + sgn * 0.15, 0.0))
            top = self.S.pad_top(np.array([[-tgt.x, -tgt.y, 0.0]]))[0] - O.PAD_Z
            tgt.z = (top if not math.isnan(top) else 0.0) + 0.055
            info = L.arm[s]
            em = other[P + s + 'Hand'].copy()
            pole = Vector((0.0, sgn * 0.6, -0.2)).normalized() + Vector((-0.8, 0, 0))
            B.solve_chain2(other, info, tgt, em, pole.normalized())
            B.blend_subtree(out, other, s + 'Arm', w)
        return out

    def fk(self, c, time_s=None):
        B, base = self.B, self.base
        q = {}
        k = c['crunch']
        q['Spine'] = R(X, 0.35 * k)
        q['Spine1'] = R(X, 0.35 * k) @ R(Y, 0.5 * c['twist']) @ R(Z, 0.5 * c['bend'])
        q['Spine2'] = R(X, 0.30 * k) @ R(Y, 0.5 * c['twist']) @ R(Z, 0.5 * c['bend'])
        q['Neck'] = R(X, c['neck'])
        q['Head'] = R(self.head_axis, c['hyaw']) @ R(X, c['hnod'])
        for s, sgn in SIDES:
            t = s[0]
            q[s + 'UpLeg'] = R(Z, sgn * c['ab_' + t]) @ R(X, -c['fl_' + t]) @ R(self.leg_axis[s], -sgn * c['lr_' + t])
            q[s + 'Leg'] = R(X, c['kn_' + t])
            q[s + 'Foot'] = R(X, c['fo_' + t])
            q[s + 'Shoulder'] = R(Z, sgn * c['sh_' + t])
            q[s + 'Arm'] = R(Z, sgn * c['aab_' + t]) @ R(X, -c['afl_' + t]) @ R(self.arm_axis[s], sgn * c['atw_' + t])
            q[s + 'ForeArm'] = R(X, -c['el_' + t])
        h = self.hip0
        root = (Matrix.Translation(h + Vector((c['px'], c['py'], c['pz']))) @
                (R(Z, c['yaw']) @ R(X, c['pitch']) @ R(Y, c['roll'])).to_matrix().to_4x4() @ Matrix.Translation(-h))
        out, _ = B.fk(base, q, root=root)
        if time_s is not None and not self.ko_mode and 0.80 < time_s < 1.36:
            w = smoother(clamp((time_s - 0.80) / 0.16)) * smoother(clamp((1.36 - time_s) / 0.10))
            if w > 0:
                out = self.hands_on_pad(out, w)
        for s, _ in SIDES:
            cu = c['cu_' + s[0]]
            if cu:
                B.curl(out, s, cu)
        return out

    def shift_z(self, out, dz):
        M = Matrix.Translation((0, 0, dz))
        return {k: M @ v for k, v in out.items()}

    def world_pts(self, out):
        W = np.array(O.W_PR)
        return self.B.skin(out, world=False) @ W[:3, :3].T + W[:3, 3]

    def contact(self, out, t):
        """Vertical contact solve (Hips height only). Floor phase: the lowest point rests on the floor.
        Seated on the edge: the butt rests on the pad. Always: no pad or floor penetration."""
        B = self.B
        pts = self.world_pts(out)
        zmin = float(pts[:, 2].min())          # table space
        top = self.S.pad_top(pts)
        g = pts[:, 2] - top
        near = ~np.isnan(g) & (g > -0.05)
        gpad = float(g[near].min()) if near.any() else 1.0
        dz = 0.0
        if not self.ko_mode and 0.84 <= t <= 1.24:
            w = smoother(clamp((t - 0.84) / 0.10)) * smoother(clamp((1.24 - t) / 0.08))
            m = near & (B.region_mask['pelvis'] | B.region_mask['leg_Left'] | B.region_mask['leg_Right'])
            if m.any():
                dz = w * (0.002 - float(g[m].min()))
        if self.ko_mode or t >= 1.44:
            dfl = FLOOR_GAP - zmin
            w2 = 1.0 if self.ko_mode else smoother(clamp((t - 1.44) / 0.08))
            dz = dfl if dfl > 0 else w2 * dfl
        if gpad + dz < 0.0025:
            dz = 0.0025 - gpad
        if zmin + dz < FLOOR_GAP:
            dz = FLOOR_GAP - zmin
        key = 'floor_lift_max' if (self.ko_mode or t >= 1.44) else 'pad_lift_max'
        self.stats[key] = max(self.stats[key], abs(dz))
        return self.shift_z(out, dz), dz


def escape_pose(ctx, t):
    c = ctx.channels(t)
    out = ctx.fk(c, t)
    out, dz = ctx.contact(out, t)
    return out, {'dz': dz}


def ko_offset(ctx):
    """Armature-space offset of the KO root relative to PatientRest: the floor point under the end hips."""
    end = ctx.contact(ctx.fk(ctx.ko_c), 3.0)[0]
    h = end[P + 'Hips'].translation
    return Vector((h.x, h.y, FLOOR_Z)), end


class KOCtx(EscapeCtx):
    def __init__(self, B):
        super().__init__(B, ko=True)
        self.off, self.end_pose = ko_offset(self)
        # the KO rig sits on the floor under the end hips (same yaw as PatientRest)
        self.W_ko = O.W_PR @ Matrix.Translation(self.off)
        self.Minv = Matrix.Translation(-self.off)
        B.place(self.W_ko)
        self.S.set_straps(False)
        self.twitch = Curve([(0, 0), (2.50, 0, 'flat'), (2.56, 1), (2.66, 0.2), (2.72, 0.7), (2.86, 0, 'flat'), (T_KO, 0)], periodic=True)


def ko_pose(ctx, t):
    T = T_KO
    c = dict(ctx.ko_c)
    # slow breathing (2 breaths per loop): the back rises, the head bobs a little
    br = 0.5 * (1 - math.cos(2 * math.pi * 2 * t / T))
    c['crunch'] += -1.6 * br
    c['neck'] += 1.0 * br
    c['hyaw'] += 1.0 * ctx.nz(t)
    tw = ctx.twitch(t)
    c['kn_R'] += 18 * tw
    c['fo_R'] += -16 * tw
    c['cu_L'] += 0.25 * tw
    out = ctx.fk(c)
    out, dz = ctx.contact(out, 3.0)
    return {k: ctx.Minv @ v for k, v in out.items()}, {'dz': dz}


def pose_from_vals(B, vals):
    out = {}
    for n in B.order:
        v = vals[n]
        basis = Quaternion(v['q']).normalized().to_matrix().to_4x4()
        if v['loc'] is not None:
            basis.translation = Vector(v['loc'])
        p = B.parent[n]
        out[n] = (B.rest[n] if p is None else out[p] @ (B.rest[p].inverted() @ B.rest[n])) @ basis
    return out


def lerp_vals(B, a, b, u):
    out = {}
    for n in B.order:
        qa, qb = Quaternion(a[n]['q']), Quaternion(b[n]['q'])
        if qa.dot(qb) < 0:
            qb.negate()
        q = Quaternion([x + (y - x) * u for x, y in zip(qa, qb)])
        loc = None
        if a[n]['loc'] is not None:
            loc = tuple(x + (y - x) * u for x, y in zip(a[n]['loc'], b[n]['loc']))
        out[n] = {'q': tuple(q), 'loc': loc}
    return out


def fix_inbetween(ctx, frames, keep=(), passes=4, floor_margin=0.0004, pad_margin=0.0006):
    """Safety net: Blender (and the 120 Hz validator) interpolate the raw keyed values linearly
    between the 60 Hz keys; fast swings sag between two clean keys. Lift both neighbouring keys by
    the measured deficit of the in-between sample (floor and pad top). Returns the max lift."""
    B = ctx.B
    keys = sorted(frames)
    worst = 0.0
    for _ in range(passes):
        vals = {f: B.values_from_pose(frames[f]) for f in keys}
        lift = {f: 0.0 for f in keys}
        for a, b in zip(keys[:-1], keys[1:]):
            for u in (0.5,):
                mid = pose_from_vals(B, lerp_vals(B, vals[a], vals[b], u))
                pts = ctx.world_pts(mid)
                d = floor_margin - float(pts[:, 2].min())
                g = pts[:, 2] - ctx.S.pad_top(pts)
                near = ~np.isnan(g) & (g > -0.05)
                if near.any():
                    d = max(d, pad_margin - float(g[near].min()))
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
    ctx.stats['inbetween_lift_max'] = worst
    return worst


def _escape_post(ctx, frames, canonical):
    keys = sorted(frames)
    fix_inbetween(ctx, frames, keep=(keys[0], keys[-1]))


def _ko_post(ctx, frames, canonical):
    # KO poses are stored relative to the KO root: evaluate them back in the PatientRest frame
    M = Matrix.Translation(ctx.off)
    tmp = {f: {k: M @ v for k, v in p.items()} for f, p in frames.items()}
    keys = sorted(tmp)
    fix_inbetween(ctx, tmp, keep=(keys[0], keys[-1]))
    for f in keys:
        frames[f] = {k: ctx.Minv @ v for k, v in tmp[f].items()}


def _escape_canon(ctx, N, frames):
    return {1.0: ctx.B.tablerest_values, float(N + 1): ctx.B.values_from_pose(frames[float(N + 1)])}


def _ko_canon(ctx, N, frames):
    v = ctx.B.values_from_pose(frames[1.0])
    return {1.0: v, float(N + 1): v}


# ======================================================================================== registry
def _canon_tablerest(ctx, N, frames):
    return table_canonical(ctx, N)


def _canon_first(ctx, N, frames):
    """Loop on its own first pose (exact raw values at both ends)."""
    return table_canonical(ctx, N, frames[1.0])


CLIPS = {
    'Awake': {'stem': 'Op_Lie_Awake_v01', 'T': T_AWAKE, 'loop': True, 'setup': AwakeCtx, 'pose': awake_pose,
              'canonical': _canon_tablerest},
    'Asleep': {'stem': 'Op_Lie_Asleep_v01', 'T': T_ASLEEP, 'loop': True, 'setup': AsleepCtx, 'pose': asleep_pose,
               'canonical': _canon_first},
    'Struggle': {'stem': 'Op_Struggle_v01', 'T': T_STRUGGLE, 'loop': True, 'setup': StruggleCtx, 'pose': struggle_pose,
                 'canonical': _canon_tablerest},
    'Panic': {'stem': 'Op_Panic_v01', 'T': T_PANIC, 'loop': True, 'setup': lambda B: StruggleCtx(B, T_PANIC, True),
              'pose': panic_pose, 'canonical': _canon_tablerest},
    'ShockDeath': {'stem': 'Op_ShockDeath_v01', 'T': T_SHOCK, 'loop': False, 'setup': ShockCtx, 'pose': shock_pose,
                   'canonical': lambda ctx, N, frames: {1.0: ctx.B.tablerest_values,
                                                        float(N + 1): ctx.B.values_from_pose(ctx.dead)}},
    'Dead': {'stem': 'Op_Dead_v01', 'T': T_DEAD, 'loop': True, 'setup': DeadCtx, 'pose': dead_pose,
             'canonical': _canon_first},
    'EscapeFall': {'stem': 'Op_EscapeFall_v01', 'T': T_ESCAPE, 'loop': False, 'setup': EscapeCtx, 'pose': escape_pose,
                   'canonical': _escape_canon, 'post': _escape_post},
    'KnockedOut': {'stem': 'Op_KnockedOut_v01', 'T': T_KO, 'loop': True, 'setup': KOCtx, 'pose': ko_pose,
                   'canonical': _ko_canon, 'post': _ko_post},
}
