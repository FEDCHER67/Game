"""Idle_Stand_v04 (fixes round 2026-10-11): the default standing idle, made alive.

Loops on the exact SAUSAGE_BUDDY_A_v04 'Idle' frame-1 pose (frame 1 and the duplicated last frame are
keyed with the raw Idle values, like Idle_Stand_v03). Every channel is periodic and zero at the seam.
Reuses clips_standing.StandRig (planted feet on their exact Idle frame-1 matrices, pelvis height
solved from the support leg) and the flip-free arm IK blend; clips_standing.py is not changed.

Beats (5.0 s): two visible breaths (clavicle shrug with arm counter-rotation, chest lift, head
rise); a weight shift onto his RIGHT leg (hips sway 6.5 cm, pelvis tips, the LEFT knee unlocks and
bends forward-in, seen from both review cameras), chest/arms overlap; a look around (to his left,
toward the side camera, then a sweep to his right dipping mid-arc, lag and settle); a small fidget:
the left hand comes up and scratches the left cheek with the fingertips (stopped on the head
surface by a contact solve), the head tilts into it, then a sniff and the arm drops with
pendulum follow-through. Knees locked (exactly straight, as in Idle frame 1) 0.40 s before and
0.25 s after the seam (HANDOFF 8.1).
Character frame: faces -Y, left = +X. pitch = R(X) (+ forward), roll = R(Y) (+ tips his left side
down), yaw = R(Z) (+ turns to his left).
"""
import math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import acting_core as C
from acting_core import R, QI, Curve, P, smooth, clamp
from clips_standing import StandRig, smooth_bump, _hand_q

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
T4 = 5.0


def soft0(raw, e=0.12):
    """w^3/(w^2+e^2): vanishes to high order at 0 so the straight base knees unlock smoothly (8.1)."""
    return lambda t: raw(t) ** 3 / (raw(t) ** 2 + e * e) * (1 + e * e)


def bump(t, a, b):
    return smooth_bump(t, a, b)


def channels():
    T = T4
    ch = {}
    # two breaths: quicker inhale, top hold, slower exhale; the second one deeper (a content sigh)
    ch['breath'] = Curve([(0, 0), (0.20, 0, 'flat'), (0.92, 0.93), (1.10, 1.0, 'flat'), (2.02, 0.05), (2.22, 0.0, 'flat'),
                          (2.98, 1.10), (3.16, 1.16, 'flat'), (4.30, 0.04), (4.55, 0.0, 'flat'), (T, 0)], periodic=True)
    # weight (+ = onto his left leg, - = onto his right leg). Anticipation push to the left, the sway
    # onto the right leg with overshoot and settle, drifting hold, back through the middle with a small
    # counter-sway onto the left leg (during the scratch), home and locked before the seam.
    raw = Curve([(0, 0), (0.25, 0, 'flat'), (0.45, 0.10), (0.64, -0.50), (0.86, -1.10), (1.06, -0.95), (1.30, -1.0),
                 (2.10, -0.92), (2.72, -1.0, 'flat'), (3.10, -0.25), (3.36, 0.30), (3.58, 0.38, 'flat'),
                 (4.05, 0.32), (4.42, 0.02), (4.60, 0, 'flat'), (T, 0)], periodic=True)
    ch['weight_raw'] = raw
    ch['weight'] = w = soft0(raw)
    # both knees soften while the weight is off-centre (the support knee unlocks a little too)
    ch['soft'] = Curve([(0, 0), (0.42, 0, 'flat'), (0.70, 0.55), (0.95, 1.0), (2.75, 0.9), (3.25, 0.45), (3.65, 0.6),
                        (4.30, 0.12), (4.60, 0, 'flat'), (T, 0)], periodic=True)
    # look around: anticipation dip to the right, SNAP to his left (toward the side camera) with
    # overshoot, drifting hold, sweep to his right dipping mid-arc, hold, back with overshoot; then a
    # small turn into the scratching hand
    ch['yaw'] = Curve([(0, 0), (1.00, 0, 'flat'), (1.10, -4.0), (1.27, 41.0), (1.36, 43.0), (1.50, 38.5), (1.88, 35.0, 'flat'),
                       (2.10, 3.0), (2.30, -33.0), (2.38, -35.5), (2.52, -32.0), (2.76, -30.0, 'flat'), (3.00, 2.0),
                       (3.10, 4.0), (3.40, 7.0), (3.85, 8.0, 'flat'), (4.25, 0.5), (4.45, 0.0, 'flat'), (T, 0)],
                      periodic=True)
    # head pitch (+ = down): curious lift on the left look, dip in the middle of the sweep, the scratch
    # tips the head down into the hand, the sniff lifts it, settle
    ch['nod'] = Curve([(0, 0), (1.00, 0, 'flat'), (1.10, 2.0), (1.30, -4.0), (1.85, -2.5), (2.10, 7.5), (2.30, 0.5),
                       (2.55, -1.0), (2.95, 0.0), (3.40, 4.0), (3.82, 5.0), (3.96, 4.0), (4.06, -5.0), (4.18, -3.5),
                       (4.38, 1.5), (4.58, 0.0, 'flat'), (T, 0)], periodic=True)
    # head roll (+ = his left side down): a curious cock on the left look, the other way on the right
    # look, tilts into the scratching hand
    ch['tilt'] = Curve([(0, 0), (1.10, 0, 'flat'), (1.40, 4.0), (1.88, 3.0), (2.30, -3.5), (2.76, -2.5), (3.05, 0.0),
                        (3.40, 9.0), (3.80, 10.0), (4.02, 2.0), (4.32, -1.0), (4.58, 0, 'flat'), (T, 0)], periodic=True)
    # the scratch: left-hand IK blend (0..1); a separate shoulder-dip anticipation; scratch strokes
    # (the IK weight stays 1 while the release below carries the hand down; it fades out once the IK
    #  hand has reached the hanging FK hand, so the two solutions never have to be blended far apart)
    ch['scr'] = Curve([(0, 0), (3.10, 0, 'flat'), (3.38, 1.0, 'flat'), (4.04, 1.0, 'flat'), (4.20, 0.0, 'flat'), (T, 0)],
                      periodic=True)
    # the elbow leads: an FK fold of the forearm (hand travels up close to the body, not out in front)
    ch['elbow'] = Curve([(0, 0), (3.00, 0, 'flat'), (3.24, 1.0), (3.84, 1.0, 'flat'), (4.10, 0.0, 'flat'),
                         (T, 0)], periodic=True)
    ch['antic'] = Curve([(0, 0), (2.98, 0, 'flat'), (3.10, 1.0), (3.24, 0.0), (T, 0)], periodic=True)
    ch['strokes'] = lambda t: math.sin(2 * math.pi * 6.0 * (t - 3.40)) * bump(t, 3.36, 3.86) ** 0.5
    ch['sniff'] = Curve([(0, 0), (3.96, 0, 'flat'), (4.06, 1.0), (4.18, 0.2), (4.28, 0.0, 'flat'), (T, 0)], periodic=True)
    ch['fingers'] = Curve([(0, 0), (0.6, 0.10), (1.6, 0.22), (2.6, 0.12), (4.5, 0.05), (T, 0)], periodic=True)
    # overlap: chest follows the look with a lag (spring), arms and hands lag the sway and the chest
    yaw = ch['yaw']
    ch['yaw_lag'] = C.spring_periodic(yaw, T, 1 / 240, 1.8, 0.55)
    ch['chest_lag'] = C.spring_periodic(w, T, 1 / 240, 1.5, 0.42)
    ch['arm_lag'] = C.spring_periodic(lambda t: w(t) + 0.02 * yaw(t), T, 1 / 240, 1.25, 0.38)
    ch['hand_lag'] = C.spring_periodic(lambda t: w(t) + ch['arm_lag'](t), T, 1 / 240, 1.7, 0.45)
    # the scratch arm drops on a pendulum: the FK arm under the IK blend swings forward and back
    # release (0..1, 3.84-4.08): the IK target travels from the cheek down beside the body to the
    # hanging FK hand (only used while the IK weight is > 0)
    ch['rel'] = lambda t: smooth((t - 3.84) / 0.24) if 3.84 < t < 4.30 else 0.0
    # pendulum after the drop, driven by the hand height proxy (1 at the face, 0 hanging)
    ch['drop_lag'] = C.spring_periodic(lambda t: ch['scr'](t) * (1 - ch['rel'](t)), T, 1 / 240, 1.4, 0.32)
    ch['breath_lag'] = C.spring_periodic(ch['breath'], T, 1 / 240, 2.0, 0.6)
    return ch


class HeadContact:
    """Radial profile of the (rigid) head in the Idle base pose, for fingertips-on-the-head contact.
    Head axis = world Z through (0, 0) in the base pose. table[phi, z] = outer radius."""

    def __init__(self, B):
        self.B = B
        base = B.idle
        pts, names = [], []
        for o in B.meshes:
            vg = [g.name for g in o.vertex_groups]
            for v in o.data.vertices:
                g = max(v.groups, key=lambda g: g.weight, default=None)
                names.append(g is not None and vg[g.group] in (P + 'Head', P + 'HeadTop_End', P + 'Neck'))
        names = np.array(names)
        allp = B.mesh_points(base)
        hp = allp[names]
        self.z0, self.dz, self.nz = 1.24, 0.01, 52
        self.nphi = 72
        tab = np.zeros((self.nphi, self.nz))
        phi = np.arctan2(hp[:, 1], hp[:, 0])
        r = np.hypot(hp[:, 0], hp[:, 1])
        ip = ((phi + math.pi) / (2 * math.pi) * self.nphi).astype(int) % self.nphi
        iz = np.clip(((hp[:, 2] - self.z0) / self.dz).astype(int), 0, self.nz - 1)
        np.maximum.at(tab, (ip, iz), r)
        # fill holes from neighbours (max over a 3x3 window)
        for _ in range(2):
            pad = np.pad(tab, ((1, 1), (0, 0)), mode='wrap')
            pad = np.pad(pad, ((0, 0), (1, 1)), mode='edge')
            win = np.max([pad[i:i + self.nphi, j:j + self.nz] for i in range(3) for j in range(3)], axis=0)
            tab = np.where(tab > 0, tab, win)
        self.tab = tab
        self.Hb = base[P + 'Head'].copy()
        self.hand_idx = {}
        off = 0
        idx = {'Left': [], 'Right': []}
        for o in B.meshes:
            vg = [g.name for g in o.vertex_groups]
            for v in o.data.vertices:
                for s in idx:
                    if any(vg[g.group].startswith(P + s + 'Hand') and g.weight > 0.3 for g in v.groups):
                        idx[s].append(off + v.index)
            off += len(o.data.vertices)
        self.hand_idx = {s: np.array(i) for s, i in idx.items()}

    def clearance(self, out, side):
        """Smallest (vertex radius - head radius) over the hand vertices that lie in the head's height
        band, in the base-pose head frame; and the outward world normal at that vertex."""
        pts = self.B.mesh_points(out)[self.hand_idx[side]]
        Mh = out[P + 'Head'] @ self.Hb.inverted()
        Mi = np.array(Mh.inverted())
        q = pts @ Mi[:3, :3].T + Mi[:3, 3]
        inb = (q[:, 2] > self.z0 + 0.03) & (q[:, 2] < self.z0 + self.dz * self.nz - 0.01)
        if not inb.any():
            return 1.0, Vector((1, 0, 0))
        q = q[inb]
        phi = np.arctan2(q[:, 1], q[:, 0])
        r = np.hypot(q[:, 0], q[:, 1])
        ip = ((phi + math.pi) / (2 * math.pi) * self.nphi).astype(int) % self.nphi
        iz = np.clip(((q[:, 2] - self.z0) / self.dz).astype(int), 0, self.nz - 1)
        gap = r - self.tab[ip, iz]
        k = int(np.argmin(gap))
        nrm = Vector((math.cos(phi[k]), math.sin(phi[k]), 0.0))
        return float(gap[k]), (Mh.to_3x3() @ nrm).normalized()


def head_axes(B, out):
    M = out[P + 'Head'].to_3x3() @ B.rest[P + 'Head'].to_3x3().inverted()
    return M @ Vector((0, -1, 0)), M @ Vector((0, 0, 1)), M @ Vector((1, 0, 0))   # face, up, his left


def pose(ctx, t):
    S, ch, B = ctx.S, ctx.ch, ctx.B
    b = ch['breath'](t)
    bl = ch['breath_lag'](t)
    w = ch['weight'](t)
    soft = ch['soft'](t)
    cl, al, hl = ch['chest_lag'](t), ch['arm_lag'](t), ch['hand_lag'](t)
    yaw, nod, tilt = ch['yaw'](t), ch['nod'](t), ch['tilt'](t)
    ylag = ch['yaw_lag'](t)
    scr, antic, strokes, sniff = ch['scr'](t), ch['antic'](t), ch['strokes'](t), ch['sniff'](t)
    drop = ch['drop_lag'](t)
    J = {}
    # pelvis: sway over the support foot, the free side drops (contrapposto), the free hip turns forward
    hips_q = R(Y, -7.0 * w) @ R(Z, 3.0 * w)
    # chest turns ~30 % with the look (lagging spring); shoulders counter-tilt the pelvis
    chest = 0.30 * (yaw + ylag)
    J['Spine'] = R(Z, 0.30 * chest) @ R(Y, 3.4 * w + 2.6 * cl) @ R(X, -0.6 * b)
    J['Spine1'] = R(Z, 0.35 * chest) @ R(Y, 3.0 * w + 1.8 * cl) @ R(X, -2.8 * b - 0.8 * bl)
    J['Spine2'] = R(Z, 0.35 * chest) @ R(Y, 1.8 * w) @ R(X, -2.6 * b)
    hy = yaw - chest
    J['Neck'] = R(Z, 0.35 * hy) @ R(X, 1.8 * b + 0.35 * nod)
    J['Head'] = (R(Z, 0.65 * hy) @ R(X, 0.65 * nod - 1.2 * b + 2.0 * bl - 6.0 * sniff)
                 @ R(Y, tilt - 1.6 * w + 1.4 * cl))
    # breathing lifts the shoulders (clavicles, ~2.5 cm at the top of the second breath); the arm
    # counter-rotation keeps the hands hanging (gotcha 2). The scratch hunches the left shoulder.
    rel = ch['rel'](t)
    shl = 11.0 * b + 7.0 * scr * (1 - rel) - 3.0 * antic
    shr = 11.0 * b
    J['LeftShoulder'] = R(Y, -shl)
    J['RightShoulder'] = R(Y, shr)
    swing = -7.0 * al
    el = ch['elbow'](t)
    J['LeftArm'] = R(Y, swing + 0.85 * shl - 1.5 * b - 14.0 * el) @ R(X, 1.5 * w + 6.0 * drop - 14.0 * el)
    J['RightArm'] = R(Y, swing - 0.85 * shr + 1.5 * b) @ R(X, -1.2 * w - 2.0 * cl)
    # the forearm folds up and INWARD (toward the face), not straight out in front
    J['LeftForeArm'] = R(Y, -4.0 * hl) @ R(X, 4.0 * drop) @ R((-0.60, 0.80, 0.0), 118.0 * el)
    J['RightForeArm'] = R(Y, -4.0 * hl)
    J['LeftHand'] = R(Y, -5.0 * hl)
    J['RightHand'] = R(Y, -5.0 * hl)
    out, D, dz, over = S.body((0.065 * w, 0.0), hips_q, J,
                              support=1.0 - 0.0025 * soft * soft, drop=0.005 * soft * soft,
                              knee_in=(0.30 * max(0.0, -w) + 0.05 * max(0.0, w), 0.30 * max(0.0, w)))
    # ---- the fidget: the left fingertips scratch the left cheek (target in the head frame)
    gap = None
    f = ch['fingers'](t)
    fl = f + scr * (1 - rel) * (0.30 + 0.18 * strokes)
    B.curl(out, 'Right', f * 0.8, thumb=0.4 * f)
    if scr > 1e-6:
        face, up, left = head_axes(B, out)
        H = out[P + 'Head'].translation
        radial = (left * 0.88 + face * 0.48).normalized()
        cheek = H + up * 0.195 + radial * 0.142
        point = (up * 0.92 - face * 0.10 + left * 0.10).normalized()
        palm = -radial
        q1 = _hand_q('Left', point, palm)
        # wrist below the fingertips, a hand-thickness off the cheek; scratch strokes along `up`
        tgt = cheek - point * 0.105 + radial * 0.030 + up * (0.012 * strokes)
        pole = (left * 0.75 - up * 0.55 + face * 0.45).normalized()
        k = smooth(scr)
        fk = dict(out)

        def solve(tg, q, pl, curl):
            o = dict(fk)
            ctx.S.arm_ik2(o, 'Left', tg, q, pl, k)
            B.curl(o, 'Left', curl, thumb=0.5 * f)
            return o
        # contact at the cheek (scratch state): fingertips on the cheek, never inside; pulled onto it
        # only once the hand is close (k > 0.6)
        fl0 = f + scr * (0.30 + 0.18 * strokes)
        out = solve(tgt, q1, pole, fl0)
        pull = clamp((k - 0.6) / 0.4)
        for _ in range(5):
            gap, nrm = ctx.head.clearance(out, 'Left')
            err_ = gap - 0.0015
            if (err_ < 0 and -err_ < 2e-4) or (err_ >= 0 and err_ * pull < 2e-4):
                break
            tgt = tgt - nrm * (err_ if err_ < 0 else err_ * pull)
            out = solve(tgt, q1, pole, fl0)
        gap, _ = ctx.head.clearance(out, 'Left')
        if rel > 0:
            # the release: from the contact-corrected cheek target down beside the body (bulging out
            # to his left and forward) to the hanging FK hand; IK weight still 1, so no far blend
            hand = fk[P + 'LeftHand'].translation
            sh = fk[P + 'LeftArm'].translation
            elb = fk[P + 'LeftForeArm'].translation
            u = rel
            tg = tgt.lerp(hand, u) + left * (0.07 * math.sin(math.pi * u)) + face * (0.03 * math.sin(math.pi * u))
            q2 = q1.slerp(B.hand_q(fk, 'Left'), u)
            line = (hand - sh).normalized()
            off = (elb - sh) - line * (elb - sh).dot(line)
            pole_fk = off.normalized() if off.length > 1e-4 else Vector((1, 0, 0))
            out = solve(tg, q2, pole.lerp(pole_fk, u).normalized(), fl)
        gap, _ = ctx.head.clearance(out, 'Left')
    else:
        B.curl(out, 'Left', fl, thumb=0.5 * f)
    return out, {'dz': dz, 'over': over, 'w': w, 'gap': gap}


class Ctx:
    def __init__(self, B):
        self.B = B
        self.S = StandRig(B)
        self.ch = channels()
        self.head = HeadContact(B)


def _canonical(ctx, N):
    v = ctx.B.idle_values
    return {1.0: v, float(N + 1): v}


def _stats(info):
    gaps = [i['gap'] for i in info if i.get('gap') is not None and i['gap'] < 0.5]   # 1.0 = hand below the head
    return {'min_pelvis_dz_m': min(i['dz'] for i in info), 'max_pelvis_dz_m': max(i['dz'] for i in info),
            'max_leg_overreach_m': max(i['over'] for i in info),
            'cheek_contact_gap_m_min_max': [min(gaps), max(gaps)] if gaps else None}


BEATS = ['0.00-0.25 locked knees at the seam (exact Idle frame 1), exhale bottom',
         '0.20-1.10 first breath in (shoulders up, chest lifts); 0.25-0.46 anticipation push onto the left leg',
         '0.46-1.30 weight sways onto his RIGHT leg with overshoot and settle: hips 6.5 cm over, pelvis tips, LEFT knee unlocks and bends forward-in; chest and arms lag',
         '1.00-1.88 look to his LEFT: tiny dip the other way, snap 41 deg with overshoot, curious head cock, drifting hold; chest follows ~30 % on a lagging spring',
         '1.88-2.76 sweep to his RIGHT dipping mid-arc (blink-like), -35 deg overshoot, hold; second, deeper breath starts at 2.2',
         '2.72-3.36 weight comes back through the middle onto the left leg a little; head back to centre',
         '2.98-3.36 fidget anticipation (left shoulder dips), left hand comes up to the cheek',
         '3.36-3.86 scratches the left cheek with the fingertips (6 Hz strokes), head tilts and dips into the hand, shoulder hunched',
         '3.84-4.28 the hand drops on a pendulum, then a sniff (head lifts, 3.96-4.28); long exhale',
         '4.30-5.00 settles; knees locked from 4.60 s into the seam']

CLIPS = {
    'Idle_Stand_v04': {'T': T4, 'loop': True, 'stage': 'stand',
                       'setup': Ctx, 'pose': pose, 'canonical': _canonical, 'stats': _stats,
                       'beats': BEATS},
}
