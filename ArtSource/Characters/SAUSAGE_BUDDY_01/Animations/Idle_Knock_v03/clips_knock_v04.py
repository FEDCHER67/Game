"""Cargo_Knock_v04: desperate banging on the cargo side wall, 3.5 s loop on the cargo sit contract.

REDO of Cargo_Knock_v03b (fixes round 2026-10-11). Review verdict on v03b: the pounding did not read.
He swivelled ~80 deg and twisted the chest a further ~92 deg to face the wall, so from both doors-side
review cameras the fists were hidden behind his giant head and hood; it looked like he pressed his face
to the wall.

New staging: after a startled inhale and a squash he spins ~88 deg to his RIGHT on the butt and scoots
24 cm off the wall, so he FACES THE DOORS (-Y, i.e. the review cameras) with the wall at his right side
and the legs folded to his left. The near (right) arm bangs SIDEWAYS on the wall: the elbow stays out
at shoulder height, the forearm tips in over the head (the wind-up, body leaning away, head pulled back)
and swings out upright like a wiper, so the pinky side of the fist meets the wall. That arc lies in the
side camera's image plane; the face stays toward the cameras. Beats: BANG ... BANG-BANG, a listen
(head tipped onto the wall, right palm flat on it, left index raised: "wait..."), a frustrated two-fisted
mega wind-up, the SLAM (right fist on the wall, left fist on his own knee), a deflate (the fist slides
down the wall, the arm drops, the head droops) and the spin back into the exact knee hug.

Everything seated is authored in the clips_cargo local frame (he sits at the origin facing -Y, the wall is
the plane y = +S.y_wall, the doors are toward -X) and placed in the van by SitRig.W. Once he has turned,
his front is local -X, his right (the wall) local +Y.

The clips_cargo machinery is imported, never edited: SitRig (seated FK, flip-free leg/arm IK, rotation-
space arm blends with hemisphere references, the body-lean wall contact and the floor solve on the
skinned mesh, the arm-off-wall swing) and the frozen sit contract (keyed exactly at both ends through
`canonical`). Local additions: SitRig4 (a fist contact that includes the sleeve cuff, solved by a
bracketed regula falsi with the fist re-aligned to the forearm), contact points frozen per hit, and a
post-pass that emulates the validator's 120 Hz sampling between keys.
"""
import math
import numpy as np
from mathutils import Vector, Quaternion
import acting_core as C
from acting_core import R, Curve, P, clamp, smooth, smoother
import clips_cargo as CC
from clips_cargo import SitRig, neutral, hand_q, lerp, vlerp, SIDES, X, Y, Z

KNOCK_T = 3.5
TURN = 88.0          # swivel to his right on the butt (deg): faces the doors, the wall at his right side
SHIFT = 0.24         # scoot off the wall during the swivel (m): room for the banging arm
HITS = (24 / 30, 35 / 30, 40 / 30)  # right hammer-fist hits (0.80, 1.167, 1.333 s = frames 25, 36, 41): BANG ... BANG-BANG
SLAM = 75 / 30                     # frustrated last slam (2.50 s = frame 76): right fist on the wall, left fist on his knee
# per hit: (contact, swing time, ease-in exponent, stuck on the wall, recoil time, recoil depth, hold the
# recoil level until). Exponents < 1.5 keep the last half-frame of a swing under ~20 deg of forearm turn.
STRIKES = ((HITS[0], 0.14, 1.3, 0.05, 0.15, 1.0, None),
           (HITS[1], 0.12, 1.3, 0.035, 0.08, 0.45, HITS[2]),     # BANG-BANG: a short bounce off the wall
           (HITS[2], 0.075, 1.25, 0.06, 0.0, 0.0, None),         # stays on the wall (opens into the palm)
           (SLAM, 0.14, 1.3, 0.06, 0.0, 0.0, None))              # held on the wall after the slam

def _vslerp(a, b, u):
    a, b = a.normalized(), b.normalized()
    d = max(-1.0, min(1.0, a.dot(b)))
    th = math.acos(d)
    if th < 1e-6:
        return a.lerp(b, u).normalized()
    s = math.sin(th)
    return (a * math.sin((1 - u) * th) + b * math.sin(u * th)) / s


def arc(c, a, b, u):
    """Point on the arc from a to b around the centre c (direction slerp, radius lerp)."""
    da, db = a - c, b - c
    return c + _vslerp(da, db, u) * lerp(da.length, db.length, u)


def _ramp(t, a, b):
    return smooth((t - a) / (b - a))


def strike(t):
    """Right fist travel along its arc: 0 = cocked, 1 = on the wall (stopped there by the contact solve).
    Accelerating swing, stuck on the wall, ease-out recoil (full, or a short bounce before the next hit)."""
    v = 0.0
    for th, pre, ex, stick, rec, depth, until in STRIKES:
        d = t - th
        if -pre <= d <= 0.0:
            v = max(v, (1 + d / pre) ** ex)
        elif 0.0 < d <= stick:
            v = max(v, 1.0)
        elif stick < d <= stick + rec:
            v = max(v, 1 - depth * smooth((d - stick) / rec))
        elif d > stick + rec and until is not None and t < until:
            v = max(v, 1 - depth)
    # stays on the wall after BANG 3 (it opens into the listening palm) and after the slam (held beat,
    # then it slides down the wall while he deflates)
    hold = max(_ramp(t, HITS[2] - 0.005, HITS[2]) * (1 - _ramp(t, 2.04, 2.18)),
               _ramp(t, SLAM - 0.005, SLAM) * (1 - _ramp(t, 3.03, 3.10)))
    return max(v, hold)


def _impulse(t, t0, w=0.05):
    """Hit response: 0 before t0, smooth onset (no velocity kink), peak 1 at t0 + w, decaying."""
    if t <= t0:
        return 0.0
    x = (t - t0) / w
    return x * x * math.exp(2 * (1 - x))


def _wobble(t, t0, f=4.2, tau=0.16):
    """Damped overshoot after a hit (starts at 0 with a smooth onset, first lobe positive)."""
    if t <= t0:
        return 0.0
    d = t - t0
    return math.exp(-d / tau) * math.sin(2 * math.pi * f * d) * smooth(d / 0.05)


def channels():
    T = KNOCK_T
    ch = {}
    # swivel on the butt (0..1): a small counter-move in the anticipation, overshoot, settle; back at the end
    ch['turn'] = Curve([(0, 0), (0.10, 0, 'flat'), (0.17, -0.045), (0.38, 0.88), (0.46, 1.04), (0.55, 0.985),
                        (0.62, 1.0), (2.86, 1.0, 'flat'), (3.10, 0.46), (3.27, 0.03), (3.35, -0.012),
                        (3.42, 0.0, 'flat'), (T, 0)])
    # scoot off the wall (0..1), leads the swivel so the hood clears the wall
    ch['scoot'] = Curve([(0, 0), (0.13, 0, 'flat'), (0.40, 1.0, 'flat'), (2.90, 1.0, 'flat'), (3.28, 0.0, 'flat'),
                         (T, 0)])
    # anticipation: a startled inhale (shoulders and head up), then a squash before the spin
    ch['inhale'] = Curve([(0, 0), (0.02, 0, 'flat'), (0.09, 1.0), (0.16, 0.9), (0.30, 0.0, 'flat'), (T, 0)])
    ch['squash'] = Curve([(0, 0), (0.10, 0, 'flat'), (0.19, 1.0), (0.26, 0.4), (0.34, -0.3), (0.44, 0.0), (T, 0)])
    # head yaw relative to the chest (deg, - = his right): scared look toward the wall over the right
    # shoulder, leads the swivel, then faces the doors (the cameras); leads the turn back at the end
    ch['look'] = Curve([(0, 0), (0.03, 0, 'flat'), (0.11, -40), (0.18, -36), (0.32, -22), (0.43, 5), (0.52, 0),
                        (2.86, 0, 'flat'), (3.00, 14), (3.22, 4), (3.38, 0.0, 'flat'), (T, 0)])
    # release the knees (0 = hug, 1 = free hands)
    ch['free'] = Curve([(0, 0), (0.10, 0, 'flat'), (0.40, 1.0, 'flat'), (2.90, 1.0, 'flat'), (3.32, 0.0, 'flat'),
                        (T, 0)])
    # arms from the guard (0) to their acting targets (1)
    # (stays 1 on the way back: the deflated arm goes from hanging straight into the hug; it only resets
    # while the hands are in the hug, where it has no effect)
    ch['ready'] = Curve([(0, 0), (0.22, 0, 'flat'), (0.50, 1.0, 'flat'), (3.32, 1.0, 'flat'), (3.45, 0.0, 'flat'),
                         (T, 0)])
    # sits up straight for the banging (0..1)
    ch['up'] = Curve([(0, 0), (0.14, 0, 'flat'), (0.48, 1.0, 'flat'), (2.72, 1.0, 'flat'), (3.12, 0.0, 'flat'),
                      (T, 0)])
    # right fist wind level: 0 = guard by the shoulder, 1 = cocked high beside the head (>1: mega)
    ch['rw'] = Curve([(0, 0), (0.30, 0.0, 'flat'), (0.56, 0.85), (0.66, 1.06), (0.71, 1.0, 'flat'),
                      (0.84, 1.0, 'flat'), (0.95, 0.55), (1.06, 0.84), (1.085, 0.82, 'flat'),
                      (1.40, 0.82, 'flat'), (2.10, 0.6), (2.30, 1.18), (2.40, 1.2, 'flat'), (2.62, 1.2, 'flat'),
                      (2.95, 0.4), (3.2, 0.0, 'flat'), (T, 0)])
    # body lean (deg about his forward axis once turned = the local X axis; + = away from the wall).
    # Wind-ups lean away, hits whip toward the wall, the listen leans in until the head meets the wall
    ch['lean'] = Curve([(0, 0), (0.30, 0, 'flat'), (0.50, 8), (0.64, 22), (0.71, 24, 'flat'),
                        # fastest at the contact, then the body follows through toward the wall and rebounds
                        (24 / 30, -6, -300), (0.865, -11.5, 'flat'), (0.98, 4), (1.07, 15), (1.085, 15.5, 'flat'),
                        (35 / 30, -5, -260), (1.215, -9.5, 'flat'), (1.265, 3.5), (1.28, 4, 'flat'),
                        (40 / 30, -6, -260), (1.40, -12), (1.60, -26), (2.04, -27, 'flat'), (2.18, 6), (2.30, 31),
                        (2.40, 34, 'flat'), (75 / 30, -9, -300), (2.58, -12.5, 'flat'), (2.72, -9, 'flat'), (2.95, -4),
                        (3.15, 0.0, 'flat'), (T, 0)])
    # chest yaw (deg, + = his left): coils away from the wall in the wind-ups, toward it on the hits
    ch['twist'] = Curve([(0, 0), (0.40, 0, 'flat'), (0.66, 9), (0.71, 10, 'flat'), (0.80, -6), (0.95, 1),
                         (1.07, 6), (35 / 30, -5), (1.26, 2), (40 / 30, -5), (1.55, -3), (2.04, -3, 'flat'),
                         (2.30, 17), (2.40, 18, 'flat'), (2.50, -9), (2.70, -7, 'flat'), (3.0, 0), (T, 0)])
    # listening (0..1): right palm flat on the wall, head tipped over so the ear goes onto the wall,
    # left index raised ("wait..."), frozen with a tiny tremble
    ch['lis'] = Curve([(0, 0), (1.36, 0, 'flat'), (1.58, 0.92), (1.66, 1.0), (2.04, 1.0, 'flat'), (2.27, 0.0, 'flat'),
                       (T, 0)])
    # left arm: pump in front of the belly (0..1 up), last slam (0..1: raised high -> 1, on the knee -> 2)
    ch['lpump'] = Curve([(0, 0), (0.40, 0, 'flat'), (0.62, 1.0), (0.71, 1.1, 'flat'), (0.80, -0.9), (0.86, -1.0),
                         (0.97, 0.2), (1.07, 0.9), (35 / 30, -0.9), (1.24, 0.5), (40 / 30, -0.9), (1.45, 0.0), (T, 0)])
    ch['lfin'] = Curve([(0, 0), (2.08, 0, 'flat'), (2.30, 1.0), (2.36, 1.04, 'flat'), (T, 1.04, 'flat')])
    # deflate after the slam (0..1) and a sad sigh into the hug
    ch['slump'] = Curve([(0, 0), (2.60, 0, 'flat'), (2.84, 1.0), (3.10, 0.75), (3.42, 0.0, 'flat'), (T, 0)])
    # the right fist slides down the wall, then the arm drops off it and hangs
    ch['slide'] = Curve([(0, 0), (2.55, 0, 'flat'), (2.83, 1.0, 'flat'), (T, 1.0, 'flat')])
    ch['drop'] = Curve([(0, 0), (2.79, 0, 'flat'), (3.03, 1.0, 'flat'), (T, 1.0, 'flat')])
    ch['sigh'] = Curve([(0, 0), (3.10, 0, 'flat'), (3.24, 1.0), (3.33, 0.9), (3.44, 0.0, 'flat'), (T, 0)])
    env = Curve([(0, 0), (1.58, 0, 'flat'), (1.68, 1.0), (2.00, 1.0), (2.08, 0.0, 'flat'), (T, 0)])
    nz = [C.pnoise(T, 41 + i, cycles=(27, 31, 37)) for i in range(4)]
    ch['trem'] = lambda t, i: env(t) * nz[i](t)
    # the giant head lags the body lean and overshoots (spring follow-through, zero at the seam)
    lean = ch['lean']
    ch['lean_lag'] = C.spring_periodic(lean, T, 1 / 240, 3.4, 0.38)
    return ch


def chest_axes(B, out):
    """His right, up and forward in the current pose (from the Spine2 rotation)."""
    M = out[P + 'Spine2'].to_3x3() @ B.rest[P + 'Spine2'].to_3x3().inverted()
    return M @ Vector((-1, 0, 0)), M @ Vector((0, 0, 1)), M @ Vector((0, -1, 0))


class SitRig4(SitRig):
    """SitRig whose wall-contact set for a hand also holds the distal forearm (skin and sleeve cuff):
    in a sideways hammer-fist the forearm is nearly parallel to the wall and the cuff can meet it first."""

    def _hand_vertices(self):
        res = super()._hand_vertices()          # also builds self.arm_verts
        for s, _ in SIDES:
            h0 = self.B.rest[P + s + 'Hand'].translation
            extra, off = [], 0
            for o in self.B.meshes:
                names = [g.name for g in o.vertex_groups]
                mw = o.matrix_world
                for v in o.data.vertices:
                    if (any(names[g.group] == P + s + 'ForeArm' and g.weight > 0.3 for g in v.groups)
                            and (mw @ v.co - h0).length < 0.11):
                        extra.append(off + v.index)
                off += len(o.data.vertices)
            res[s] = np.unique(np.concatenate([res[s], np.array(extra, dtype=int)]))
        return res

    def _solve_arm(self, base, s, spec):
        """clips_cargo.SitRig._solve_arm with (a) an optional per-finger curl ('per') and (b) the wall
        contact solved here: after every re-solve of the shifted IK target the fist is re-aligned with
        the forearm, so it does not twist against the forearm on the contact frame."""
        B = self.B
        pre = dict(base)
        t2 = self.soft_reach(pre, s, spec['pos'](pre) if callable(spec['pos']) else spec['pos'])
        pole2 = spec['pole'](pre, t2) if callable(spec['pole']) else Vector(spec['pole'])
        pole2 = pole2.normalized()
        wrist = spec.get('wrist')
        fa, hd = P + s + 'ForeArm', P + s + 'Hand'

        def place(tgt):
            q2 = spec['q']
            B.solve_chain2(pre, self.arm[s], tgt, B.hand_matrix(s, q2, tgt), pole2)
            if wrist:
                qn = (pre[fa].to_3x3() @ B.rest[fa].to_3x3().inverted()).to_quaternion()
                q2 = q2.slerp(qn, wrist) if wrist < 1 else qn
                delta = B.hand_matrix(s, q2, pre[hd].translation) @ pre[hd].inverted()
                for n in B.subtree(s + 'Hand'):
                    pre[n] = delta @ pre[n]
        place(t2)
        B.curl(pre, s, spec.get('curl', 0.0), thumb=spec.get('thumb'), per=spec.get('per'))
        mode = spec.get('wall')
        if mode and self.y_wall < 1.0:
            # the hand (fist, fingers and the distal forearm) stops 2.5 mm before the wall: regula falsi
            # (Illinois) on the shift of the IK target away from the wall, bracketed so the final
            # placement never crosses (the fist re-aligns with the forearm, so the response is not 1:1)
            lim = self.y_wall - 0.0025
            idx = self.hand_verts[s]

            def excess(d):
                place(t2 - Vector((0, d, 0)))
                return float(B.mesh_points(pre)[idx, 1].max()) - lim
            fa_ = excess(0.0)
            if fa_ > 2e-6:
                a = 0.0
                b = fa_
                fb = excess(b)
                while fb > 0 and b < 0.6:
                    a, fa_ = b, fb
                    b = 2 * b + 0.005
                    fb = excess(b)
                side = 0
                for _ in range(16):
                    if fb > -1e-4:
                        break
                    c = b - fb * (b - a) / (fb - fa_)
                    fc = excess(c)
                    if fc > 0:
                        a, fa_ = c, fc
                        if side == -1:
                            fb *= 0.5
                        side = -1
                    else:
                        b, fb = c, fc
                        if side == 1:
                            fa_ *= 0.5
                        side = 1
                excess(b)           # final placement on the non-crossing side
        return pre


class Knock4Ctx:
    """Context + pre-passes (copied from clips_cargo.KnockCtx; they call this module's pose)."""

    def __init__(self, B, fast=None):
        import os
        self.B = B
        self.S = SitRig4(B)
        self.ch = channels()
        self.refs = None
        self.swing = None
        self.want_gaps = False
        self.hit_pts = None
        self.hit_pts = self._hit_points()
        if fast is None:
            fast = os.environ.get('KNOCK4_FAST') == '1'
        if not fast:
            self.refs = self._blend_refs()
            self.swing = self._swing_table()
        self.want_gaps = True           # the final sampling records the right hand's wall gap (stats)

    def _hit_points(self):
        """Contact wrist targets frozen in the van (local) frame: the chest-relative R_POUND point at each
        contact time, so the fist does not slide along the wall while it is stuck on it. BANG 3 lands on
        the spot of BANG 2 (it bounces and hits again)."""
        S, B = self.S, self.B
        Winv = S.W.inverted()
        pts = []
        for th in HITS + (SLAM,):
            out = {n: Winv @ m for n, m in knock4_pose(self, th)[0].items()}
            sh = out[P + 'RightArm'].translation
            pw = _rel(sh, chest_axes(B, out), R_POUND[0])
            pw.y = S.y_wall - POUND_IN
            pts.append(pw)
        pts[2] = pts[1].copy()
        return pts

    def hit_at(self, t):
        """Frozen contact point of the current (or next) strike."""
        if self.hit_pts is None:
            return None
        i = 0
        for k, st in enumerate(STRIKES):
            if t >= st[0] - st[1]:
                i = k
        return self.hit_pts[i]

    def _blend_refs(self, dt=1 / 240):
        n = int(round(KNOCK_T / dt))
        tabs = {}
        self.B.blend_log = {}
        for i in range(n + 1):
            t = i * dt
            self.B.blend_log.clear()
            knock4_pose(self, t)
            for tag, log in self.B.blend_log.items():
                tb = tabs.setdefault(tag, {})
                for bone, (qa, qb) in log.items():
                    sa, sb = tb.setdefault(bone, ([], []))
                    for seq, q in ((sa, qa), (sb, qb)):
                        q = q.copy()
                        last = next((x for _, x in reversed(seq)), None)
                        if last is not None and last.dot(q) < 0:
                            q.negate()
                        seq.append((t, q))
        self.B.blend_log = None
        self._ref_tabs = tabs
        return True

    def refs_at(self, s, t):
        out = {}
        for which in ('inner', 'outer'):
            tb = self._ref_tabs.get((s, which))
            if not tb:
                continue
            ra, rb = {}, {}
            for bone, (sa, sb) in tb.items():
                for seq, dst in ((sa, ra), (sb, rb)):
                    ts = np.array([x[0] for x in seq])
                    dst[bone] = seq[int(np.abs(ts - t).argmin())][1]
            out[which] = (ra, rb)
        return out

    def _swing_table(self, dt=1 / 120, rmax=0.06, sigma=0.02):
        n = int(round(KNOCK_T / dt))
        ts = np.arange(n + 1) * dt
        need = {s: np.zeros(n + 1) for s, _ in SIDES}
        for i, t in enumerate(ts):
            knock4_pose(self, float(t))
            for s, _ in SIDES:
                need[s][i] = self.S.last_swing[s]
        r = int(round(rmax / dt))
        k = np.exp(-0.5 * (np.arange(-3 * int(sigma / dt), 3 * int(sigma / dt) + 1) * dt / sigma) ** 2)
        k /= k.sum()
        out = {}
        for s, _ in SIDES:
            a = need[s]
            m = np.array([a[max(0, i - r):i + r + 1].max() for i in range(n + 1)])
            pad = len(k) // 2
            mp = np.concatenate([np.full(pad, m[0]), m, np.full(pad, m[-1])])
            out[s] = np.convolve(mp, k, mode='valid')
        self.swing_need = need
        return ts, out

    def swing_at(self, t):
        ts, tab = self.swing
        return {s: float(np.interp(t, ts, tab[s])) for s, _ in SIDES}


# right arm keys relative to the right shoulder, in his chest axes (right = toward the wall, up, forward):
# (wrist, elbow hint). The bang is a forearm swing about the elbow: the elbow stays out at shoulder
# height, the forearm tips in over the head (cocked) and swings out upright so the pinky side of the
# fist meets the wall. The R_POUND wrist sits POUND_IN inside the wall plane (frozen per hit in the van
# frame); the fist's side reaches past it and the contact solve stops the fist 2.5 mm before the wall.
R_GUARD = ((0.14, 0.12, 0.14), (0.19, -0.09, 0.03))
R_COCK = ((0.06, 0.31, 0.08), (0.18, 0.10, 0.08))
R_MEGA = ((0.03, 0.38, 0.05), (0.15, 0.21, 0.05))
R_POUND = ((0.34, 0.22, 0.07), (0.10, -0.03, 0.15))
R_HANG = ((0.10, -0.24, 0.14), (0.05, -0.10, -0.15))  # deflated: the hand hangs beside his thigh, elbow back
R_SLIDE_E = (0.06, -0.11, -0.13)                        # elbow hint while the fist slides down the wall (turns back)
POUND_IN = 0.035      # the pound wrist target sits this far inside the wall plane (the fist's side reaches past it)
# left fist: pump in front of the belly, raised "wait" hand, raised fist (his left = -right)
L_PUMP = (0.07, -0.11, 0.22)
L_WAIT = (-0.07, 0.30, 0.13)
L_HIGH = (-0.12, 0.31, 0.08)
L_SLAM_T = 0.22       # left fist slam onto his knee: swing time before SLAM


def _rel(sh, ax, v):
    rt, up, fw = ax
    return sh + rt * v[0] + up * v[1] + fw * v[2]


def _wiper(sh, ax, A, Bk, u):
    """Forearm swing about the elbow between two arm keys: the elbow hint moves on a straight line,
    the wrist circles it (direction slerp, radius lerp). Returns (wrist, elbow hint)."""
    ea, eb = _rel(sh, ax, A[1]), _rel(sh, ax, Bk[1])
    wa, wb = _rel(sh, ax, A[0]), _rel(sh, ax, Bk[0])
    e = ea.lerp(eb, u)
    return e + _vslerp(wa - ea, wb - eb, u) * lerp((wa - ea).length, (wb - eb).length, u), e


def r_arm(B, out, yw, rw, rs, lis, slide, drop, hit_pt=None):
    """Right wrist target and elbow hint for the current pose."""
    sh = out[P + 'RightArm'].translation
    ax = chest_axes(B, out)
    if rw <= 1:
        key = (_rel(sh, ax, R_GUARD[0]), _rel(sh, ax, R_GUARD[1]))
        key2 = (_rel(sh, ax, R_COCK[0]), _rel(sh, ax, R_COCK[1]))
        u = clamp(rw)
    else:
        key = (_rel(sh, ax, R_COCK[0]), _rel(sh, ax, R_COCK[1]))
        key2 = (_rel(sh, ax, R_MEGA[0]), _rel(sh, ax, R_MEGA[1]))
        u = clamp((rw - 1) / 0.2)
    e = key[1].lerp(key2[1], u)
    w = e + _vslerp(key[0] - key[1], key2[0] - key2[1], u) * lerp((key[0] - key[1]).length, (key2[0] - key2[1]).length, u)
    pw, pe = _rel(sh, ax, R_POUND[0]), _rel(sh, ax, R_POUND[1])
    pw.y = yw - POUND_IN
    if hit_pt is not None:
        pw = hit_pt.copy()
    e2 = e.lerp(pe, rs)
    w = e2 + _vslerp(w - e, pw - pe, rs) * lerp((w - e).length, (pw - pe).length, rs)
    e = e2
    # listening: palm flat on the wall in front of his face, elbow down
    palm_w = Vector((-0.27, yw + 0.02, 0.53))
    palm_e = _rel(sh, ax, (0.08, -0.16, 0.12))
    w, e = w.lerp(palm_w, lis), e.lerp(palm_e, lis)
    # deflating: the fist slides down the wall, then the arm drops off it and hangs
    if slide > 0:
        k = smooth(slide)
        w, e = w.lerp(Vector((w.x - 0.03, yw + 0.02, 0.48)), k), e.lerp(_rel(sh, ax, R_SLIDE_E), k)
    if drop > 0:
        k = smooth(drop)
        w, e = w.lerp(_rel(sh, ax, R_HANG[0]), k), e.lerp(_rel(sh, ax, R_HANG[1]), k)
    return w, e


def knock4_pose(ctx, t):
    S, ch, B = ctx.S, ctx.ch, ctx.B
    yw = S.y_wall
    u, sc, sq, ih = ch['turn'](t), ch['scoot'](t), ch['squash'](t), ch['inhale'](t)
    look, free, ready, up = ch['look'](t), ch['free'](t), ch['ready'](t), ch['up'](t)
    rw, lean, twist, lis = ch['rw'](t), ch['lean'](t), ch['twist'](t), ch['lis'](t)
    lpump, lfin, slump, sigh = ch['lpump'](t), ch['lfin'](t), ch['slump'](t), ch['sigh'](t)
    lag = ch['lean_lag'](t)
    tr = [ch['trem'](t, i) for i in range(4)]
    rs = strike(t)
    bounce = sum(_impulse(t, th) for th in HITS) + 1.5 * _impulse(t, SLAM, 0.07)
    wob = sum(_wobble(t, th) for th in HITS) + 1.4 * _wobble(t, SLAM, 3.6, 0.2)
    p = neutral(S)
    # ---- swivel on the butt + scoot off the wall (displacement applied after the rotation)
    rock = R(Z, -TURN * u) @ R(X, 3.0 * sq - 3.0 * slump)
    d = Vector((0.0, -SHIFT * sc, 0.0))
    p.rock = rock
    p.root = tuple(rock.inverted() @ d)
    p.hips_q = p.hips_q @ R(X, 5.0 * up)
    J = p.J
    # lean about the local X axis (his forward axis once turned): + away from the wall
    ax = (p.rock @ p.hips_q).inverted() @ Vector(X)
    J['Spine'] = R(ax, 0.55 * lean) @ J['Spine'] @ R(X, -5 * up + 6 * sq + 7 * slump + 4.0 * bounce) @ R(Z, 0.35 * twist)
    J['Spine1'] = (J['Spine1'] @ R(X, -6 * up - 3 * ih + 5 * sq + 8 * slump + 2.0 * bounce - 2.0 * sigh)
                   @ R(Y, 0.25 * lean) @ R(Z, 0.35 * twist))
    J['Spine2'] = (J['Spine2'] @ R(X, -4 * up - 3 * ih + 4 * sq + 5 * slump + 1.5 * bounce - 2.0 * sigh)
                   @ R(Y, 0.20 * lean) @ R(Z, 0.30 * twist))
    cock = clamp(rw) * ready * (1 - lis)
    mega = clamp((rw - 1) / 0.2) * (1 - clamp((t - SLAM + 0.06) / 0.06))
    shr = 12 * ih + 6 * sq + 9 * sigh - 12 * slump + 3 * lis
    rsh = shr + 10 * clamp(rw) * ready * (1 - lis) + 6 * mega - 4 * bounce
    J['LeftShoulder'] = J['LeftShoulder'] @ R(Y, -shr - 6 * clamp(lfin, 0, 1) * (1 - slump))
    J['RightShoulder'] = J['RightShoulder'] @ R(Y, rsh)
    # head: faces the cameras; pulled back in the wind-ups, jolts on the hits, lags the lean (overlap),
    # tips over to his right (ear toward the wall) while listening
    hy = look - 0.9 * twist
    roll = 0.7 * lag + 6.0 * cock + 4.0 * mega - 22 * lis - 4.0 * wob
    pitch = -9 * up - 9 * cock - 7 * mega + 9 * bounce + 5 * wob + 28 * slump - 4 * sigh - 7 * ih + 6 * sq
    J['Neck'] = J['Neck'] @ R(Z, 0.4 * hy) @ R(X, 0.45 * pitch + 0.6 * tr[0]) @ R(Y, 0.4 * roll)
    J['Head'] = (J['Head'] @ R(Z, 0.6 * hy) @ R(X, 0.55 * pitch + 0.6 * tr[1])
                 @ R(Y, 0.6 * roll + 0.6 * tr[2]))
    # ---- legs: knees fall to his left into a side-sit, feet pivot roughly in place
    for s, sgn in SIDES:
        a0, fq0, pole0 = p.feet[s]
        a1 = (0.12, -0.65, a0[2]) if s == 'Left' else (-0.22, -0.58, a0[2])
        pole1 = (-0.90, -0.12, 0.40)
        k = smoother(u)
        an = vlerp(a0, a1, k)
        # the feet skid round a hair off the floor during both swivels (time windows, so the pelvis
        # counter-turn of the anticipation is covered too; keys between planted poses cannot dip)
        an.z += 0.007 * (math.sin(math.pi * clamp((t - 0.10) / 0.54)) ** 2 + math.sin(math.pi * clamp((t - 2.80) / 0.64)) ** 2)
        p.feet[s] = (tuple(an), R(Z, -38 * k), tuple(vlerp(pole0, pole1, k)))
    # ---- arms (rotation-space blends: knee hug -> guard -> acting targets)
    fwd_l = R(Z, -TURN * u) @ Vector((0, -1, 0))        # his front in the local frame
    for s, sgn in SIDES:
        h = p.hands[s]
        if s == 'Right':
            st = (rw, rs, lis, ch['slide'](t), ch['drop'](t), ctx.hit_at(t))

            def tgt(out, st=st):
                return r_arm(B, out, yw, *st)[0]

            def pole(out, tg, st=st):
                return r_arm(B, out, yw, *st)[1] - out[P + 'RightArm'].translation
            q_palm = hand_q('Right', fwd_l * 0.55 + Vector((0, 0, 1)), (0, 1, 0))
            h['alt'] = {'pos': tgt, 'q': q_palm, 'pole': pole, 'wrist': 1 - lis,
                        'curl': lerp(lerp(1.0, 0.1, lis), 0.45, smooth(ch['drop'](t))),
                        'thumb': lerp(0.9, 0.1, lis), 'wall': True}

            def guard(out):
                sh = out[P + 'RightArm'].translation
                return _rel(sh, chest_axes(B, out), R_GUARD[0])

            def gpole(out, tg):
                return _rel(Vector(), chest_axes(B, out), R_GUARD[1])
            h['alt']['guard'] = dict(h['alt'], pos=guard, pole=gpole, wall=False, wrist=1.0, curl=1.0, thumb=0.9)
        else:
            def tgt(out, lpump=lpump, lis=lis, lfin=lfin, t=t):
                sh = out[P + 'LeftArm'].translation
                ax_ = chest_axes(B, out)
                pump = _rel(sh, ax_, (L_PUMP[0] - 0.02 * lpump, L_PUMP[1] + 0.09 * lpump, L_PUMP[2] - 0.03 * lpump))
                f = arc(sh, pump, _rel(sh, ax_, L_WAIT), lis)
                if lfin > 0:
                    hi = _rel(sh, ax_, L_HIGH)
                    f = arc(sh, f, hi, clamp(lfin))
                    sl = clamp((t - SLAM + L_SLAM_T) / L_SLAM_T) ** 1.2
                    if sl > 0:
                        knee = out[P + 'LeftLeg'].translation + Vector((0, 0, 0.10))
                        f = arc(sh, f, knee, sl)
                return f

            def pole(out, tg):
                rt, up_, fw = chest_axes(B, out)
                return (-rt * 1.0 - up_ * 0.3 - fw * 0.3).normalized()
            q_wait = hand_q('Left', Vector((0, 0, 1)) + fwd_l * 0.15, fwd_l)
            lcurl = lerp(1.0, 0.45, smooth(slump))
            h['alt'] = {'pos': tgt, 'q': q_wait, 'pole': pole, 'wrist': 1 - lis, 'curl': lcurl,
                        'per': {'Index': lerp(lcurl, 0.0, lis)}, 'thumb': 0.9, 'wall': True}

            def guard(out):
                sh = out[P + 'LeftArm'].translation
                return _rel(sh, chest_axes(B, out), L_PUMP)
            h['alt']['guard'] = dict(h['alt'], pos=guard, wall=False, wrist=1.0, curl=1.0, thumb=0.9, per=None)
        h['alt']['k2'] = smooth(ready)
        h['k'] = smooth(free)
        h['refs'] = ctx.refs_at(s, t) if ctx.refs else None
        h['curl'] = 0.5 + 0.15 * sigh
    S.swing_override = ctx.swing_at(t) if ctx.swing is not None else None
    out = S.pose(p)
    S.swing_override = None
    extra = {'wall_lean_deg': S.last_fix[0], 'seat_lift_m': S.last_fix[1],
             'arm_swing_L_deg': S.last_swing['Left'], 'arm_swing_R_deg': S.last_swing['Right']}
    if getattr(ctx, 'want_gaps', False):
        pts = B.mesh_points(out)
        extra['r_hand_wall_gap_m'] = float(pts[S.hand_verts['Right'], 0].min()) - C.WALL_X
    return out, extra


def _mid_values(va, vb):
    """Raw values half-way between two keys, as Blender evaluates linear quaternion/location keys."""
    out = {}
    for n, x in va.items():
        qa, qb = Quaternion(x['q']), Quaternion(vb[n]['q'])
        q = Quaternion([0.5 * (i + j) for i, j in zip(qa, qb)]).normalized()
        loc = None if x['loc'] is None else tuple(0.5 * (i + j) for i, j in zip(x['loc'], vb[n]['loc']))
        out[n] = {'q': tuple(q), 'loc': loc}
    return out


def _post(ctx, frames, canonical):
    """Safety nets on the sampled poses (the contract end frames are never touched):
    1. rotation-rate limit (acting_core.limit_rotation_steps, < 23 deg per half frame), as in v03b;
    2. validator emulation: every 120 Hz sample between two half-frame keys (linear interpolation of
       the keyed raw values, exactly as Blender evaluates them) is checked on the skinned mesh against
       the wall, the floor and the 1.2 m limit. An arm that would graze the wall between two clean keys
       is swung about its shoulder at both keys by the smallest angle that clears it. Unlike the v03b
       net (a 4 mm margin on every arm vertex) this leaves the fist contacts at 2.5 mm."""
    B, S = ctx.B, ctx.S
    keep = set(canonical.keys())
    ctx.post_changed = C.limit_rotation_steps(B, frames, max_deg=23.0, keep=keep)
    keys = sorted(frames)
    Winv = S.W.inverted()
    ctx.post_swing = []
    ctx.post_report = []
    for rnd in range(6):
        vals = []
        prev = {}
        for f in keys:
            v = canonical[f] if f in canonical else B.values_from_pose(frames[f])
            v = {n: dict(x) for n, x in v.items()}
            for n, x in v.items():
                q = Quaternion(x['q'])
                if n in prev and prev[n].dot(q) < 0:
                    q.negate()
                prev[n] = q
                x['q'] = tuple(q)
            vals.append(v)
        bad = []
        if rnd == 0:
            for i, f in enumerate(keys):          # the keys themselves (report only; clean by construction)
                pts = B.mesh_points(B.pose_from_values(vals[i]))
                if (float(pts[:, 0].min()) < C.WALL_X or float(pts[:, 2].min()) < 0
                        or float(pts[:, 2].max()) > C.HEIGHT_LIMIT):
                    ctx.post_report.append(('key', f, float(pts[:, 0].min()), float(pts[:, 2].min()),
                                            float(pts[:, 2].max())))
        for i in range(len(keys) - 1):
            pts = B.mesh_points(B.pose_from_values(_mid_values(vals[i], vals[i + 1])))
            minx, minz, maxz = float(pts[:, 0].min()), float(pts[:, 2].min()), float(pts[:, 2].max())
            if minz < 1e-5 or maxz > C.HEIGHT_LIMIT - 1e-3:
                ctx.post_report.append(('floor/height', keys[i], minz, maxz))
            if minx < C.WALL_X + 2e-4:
                over = np.where(pts[:, 0] < C.WALL_X + 2e-4)[0]
                sides = [s for s, _ in SIDES if np.isin(over, S.arm_verts[s]).any()]
                body = not all(np.isin(over, np.concatenate([S.arm_verts[s] for s, _ in SIDES])))
                bad.append((i, sides, body, C.WALL_X - minx))
        if not bad:
            break
        for i, sides, body, ex in bad:
            if body:
                ctx.post_report.append(('body-wall', keys[i], ex))
            for s in sides:
                ang = 0.5 * 2 ** rnd
                for f in (keys[i], keys[i + 1]):
                    if f in keep:
                        continue
                    loc = {n: Winv @ m for n, m in frames[f].items()}
                    S.swing_override = {s_: (ang if s_ == s else 0.0) for s_, _ in SIDES}
                    S._arm_off_wall(loc, s)
                    S.swing_override = None
                    frames[f] = {n: S.W @ m for n, m in loc.items()}
                ctx.post_swing.append((keys[i], s, ang))
    print('POST rotation-limited bones:', ctx.post_changed, 'swings:', ctx.post_swing, 'report:', ctx.post_report,
          flush=True)


def _stats(info):
    gaps = [(i['t'], i.get('r_hand_wall_gap_m')) for i in info]
    touch, prev = [], False
    for t, g in gaps:                     # first sample of every run with the right hand on the wall
        on = g is not None and g <= 0.003
        if on and not prev:
            touch.append(round(t, 4))
        prev = on
    return {'max_wall_contact_lean_deg': max(i['wall_lean_deg'] for i in info),
            'max_seat_lift_m': max(i['seat_lift_m'] for i in info),
            'max_arm_swing_deg': {'Left': max(i['arm_swing_L_deg'] for i in info),
                                  'Right': max(i['arm_swing_R_deg'] for i in info)},
            'min_right_hand_wall_gap_m': min(g for _, g in gaps if g is not None),
            'right_hand_reaches_wall_s': touch,
            'nominal_hits_s': {'bang_1': round(HITS[0], 4), 'bang_2': round(HITS[1], 4), 'bang_3': round(HITS[2], 4),
                               'slam_right_fist_wall_left_fist_knee': round(SLAM, 4)}}


CLIPS = {
    'Cargo_Knock_v04': {
        'T': KNOCK_T, 'loop': True, 'stage': 'cargo',
        'setup': Knock4Ctx, 'pose': knock4_pose, 'canonical': CC._knock_canonical, 'post': _post,
        'stats': _stats,
        'beats': ['0.00-0.30 anticipation: startled inhale (shoulders and head up, head turns over his right shoulder), then a squash',
                  '0.17-0.62 spins ~88 deg right on the butt and scoots 24 cm off the wall: faces the doors (the cameras), legs fold to his left; the arms let go of the knees',
                  '0.40-0.71 wind-up 1 (big): right forearm tipped in over the head, body leaning 24 deg away, head pulled back; left fist pumping in front',
                  '0.80 BANG 1: the forearm swings out, pinky side of the fist on the wall (2.5 mm), the body whips in and follows through, the head jolts and wobbles',
                  '0.85-1.09 recoil and wind-up 2',
                  '1.167 BANG 2, a short bounce off the wall, 1.333 BANG 3 (BANG-BANG)',
                  '1.36-1.66 the fist opens into a palm flat on the wall, he leans in until his head is on the wall, left index raised ("wait...")',
                  '1.66-2.04 listening hold with a tiny tremble (hopeful silence)',
                  '2.04-2.40 frustrated mega wind-up: both fists up, body coiled 34 deg away, head thrown back, hold',
                  '2.50 SLAM: right fist on the wall, left fist on his own knee; head jolt, held beat',
                  '2.55-3.03 deflate: the fist slides down the wall, the arm drops off it and hangs, the head droops, the shoulders sag',
                  '2.86-3.50 spins back with the head leading, sad sigh, lands in the exact knee hug (cargo sit contract)'],
    },
}
