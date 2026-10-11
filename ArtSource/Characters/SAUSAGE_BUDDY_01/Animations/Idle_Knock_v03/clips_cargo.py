"""Cargo-bay clips: Cargo_Sit_Idle_v04 (scared sitting loop), Cargo_Knock_v03b (two-fist banging on
the side wall) and SitUp_Cargo_v04 (wakes up lying in the van and scrambles into the sit).

Layout (GPT's accepted stage): floor z = 0, side wall plane x = WALL_X = -0.65, height limit 1.2 m.
He sits with his back (the big hood) to the wall, facing +X, hips at about (-0.30, 0, 0.11); the van's
rear doors are toward -Y, which is his RIGHT while seated.

Authoring frame ("local"): every seated pose is built as if he sat at the origin facing -Y
(left = +X, the A v04 convention, so the sign rules of clips_standing apply unchanged) and is then
placed in the van by SitRig.W = Translation(wx, 0, 0) @ Rz(90). In the local frame the wall is the
plane y = +y_wall behind him and the doors are toward local -X.
Rotation helpers (local frame): pitch = R(X) (+ leans/nods forward), roll = R(Y) (+ tips his left
side down), yaw = R(Z) (+ turns to his left).

The cargo sit contract (Cargo_Sit_Idle_v04 frame 1) is computed once here (`sit_contract`) and
keyed with identical raw values at both ends of the sit idle and the knock and at the end of the
sit-up. SitUp_Cargo_v04 frame 1 is the raw GetUp_FromBack_v02 frame-1 (supine) values.
"""
import math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import acting_core as C
from acting_core import R, QI, Curve, P, clamp, smooth, smoother

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
SIDES = (('Left', 1), ('Right', -1))
WALL_GAP = 0.003          # hood-to-wall clearance at the contract pose (m)
FLOOR_GAP = 0.0005        # butt / sole clearance above the floor at the contract pose (m)


def hand_q(side, point, palm):
    """World rotation (applied to the rest hand) that points the hand along `point` with the palm
    facing `palm`. Rest: Left hand points +X, Right hand -X, palms face -Z (T-pose)."""
    p0 = Vector((1, 0, 0)) if side == 'Left' else Vector((-1, 0, 0))
    n0 = Vector((0, 0, -1))
    p = Vector(point).normalized()
    n = Vector(palm)
    n = (n - p * n.dot(p)).normalized()
    A = Matrix((p0, n0, p0.cross(n0))).transposed()
    Bm = Matrix((p, n, p.cross(n))).transposed()
    return (Bm @ A.transposed()).to_quaternion()


def hand_q_thumb(side, point, thumb):
    """Like hand_q, but specified by the thumb direction (a vertical fist: thumb up)."""
    p = Vector(point).normalized()
    t = Vector(thumb)
    t = (t - p * t.dot(p)).normalized()
    n = p.cross(t) if side == 'Left' else t.cross(p)
    return hand_q(side, p, n)


def lerp(a, b, u):
    return a + (b - a) * u


def vlerp(a, b, u):
    return Vector(a).lerp(Vector(b), u)


def qlerp(a, b, u):
    return a.slerp(b, u)


class SitRig:
    """Seated machinery on top of the Idle frame-1 base pose (authored in the local frame)."""

    def __init__(self, B):
        self.B = B
        self.base = B.idle
        self.leg = {s: B.chain_info2(self.base, 'leg', s, (0, -1, 0)) for s, _ in SIDES}
        self.arm = {s: B.chain_info2(self.base, 'arm', s, (0, 1, 0)) for s, _ in SIDES}
        self.hip0 = self.base[P + 'Hips'].translation.copy()
        self.ankle0 = {s: self.base[P + s + 'Foot'].translation.copy() for s, _ in SIDES}
        self.hand_verts = self._hand_vertices()
        self.seat_mask = self._seat_vertices()
        self.seat_z = 0.0      # solved below: pelvis height that rests the butt on the floor
        self.W = Matrix.Identity(4)
        self.y_wall = 1.0
        self.last_fix = (0.0, 0.0)
        self.last_swing = {'Left': 0.0, 'Right': 0.0}
        self.swing_override = None
        # seat height and wall placement from the neutral seated pose
        p0 = self.pose(neutral(self), world=False, safe=False)
        pts = B.mesh_points(p0)
        body_low = self._butt_low(pts)
        self.seat_z = FLOOR_GAP - body_low
        p0 = self.pose(neutral(self), world=False, safe=False)
        pts = B.mesh_points(p0)
        maxy = float(pts[:, 1].max())
        wx = C.WALL_X + WALL_GAP + maxy
        self.W = Matrix.Translation((wx, 0, 0)) @ R(Z, 90).to_matrix().to_4x4()
        self.y_wall = wx - C.WALL_X          # local y of the wall plane
        self.wx = wx

    def _hand_vertices(self):
        import numpy as np
        res = {}
        for s, _ in SIDES:
            # contact set for a wall hand: hand, fingers and forearm (skin and sleeve)
            pres = (P + s + 'Hand',)
            idx, off = [], 0
            for o in self.B.meshes:
                names = [g.name for g in o.vertex_groups]
                idx += [off + v.index for v in o.data.vertices
                        if any(names[g.group].startswith(pres) and g.weight > 0.3 for g in v.groups)]
                off += len(o.data.vertices)
            res[s] = np.array(idx)
        # whole-arm vertex sets (checked by _arm_off_wall); forearm + hand sets are excluded from
        # the body lean solve (a hand pinned to a target cannot be moved by leaning the spine)
        # while an arm is driven by its own wall contact (leaning the spine cannot move a hand
        # pinned to a target, so the arm must not steer the lean)
        self.arm_verts = {}
        for s, _ in SIDES:
            pres = (P + s + 'Arm', P + s + 'ForeArm', P + s + 'Hand')
            idx, off = [], 0
            for o in self.B.meshes:
                names = [g.name for g in o.vertex_groups]
                idx += [off + v.index for v in o.data.vertices
                        if any(names[g.group].startswith(pres) and g.weight > 0.3 for g in v.groups)]
                off += len(o.data.vertices)
            self.arm_verts[s] = np.array(idx)
        return res

    def _seat_vertices(self):
        """Mask of the vertices that sit on the floor: dominant weight on the pelvis, spine or
        thigh (the shins and feet are placed by the leg IK and checked separately)."""
        import numpy as np
        keep = ('Hips', 'Spine', 'Spine1', 'Spine2', 'LeftUpLeg', 'RightUpLeg')
        mask = []
        for o in self.B.meshes:
            names = [g.name for g in o.vertex_groups]
            for v in o.data.vertices:
                g = max(v.groups, key=lambda g: g.weight, default=None)
                mask.append(g is not None and names[g.group][len(P):] in keep)
        return np.array(mask)

    def _butt_low(self, pts):
        return float(pts[self.seat_mask, 2].min())

    def pose(self, p, world=True, safe=True):
        """Build a seated pose from SitParams p. Returns {bone: matrix} (world if world=True).
        safe: contact solve, measured on the skinned mesh.
        - Floor: if the seat (pelvis/thigh vertices) would dip below the floor, the pelvis is
          lifted by the exact excess (the feet stay planted through the leg IK).
        - Wall: the wall stops the lean. If anything but a wall-contact hand would cross the
          wall plane, the upper body is tipped away from the wall (about the local X axis, from
          Spine) by the smallest angle that leaves it touching (regula falsi on the measured
          excess). The result is continuous in time, so contact reads as a press, not a pop."""
        import numpy as np
        out = self._pose(p, swing=not safe)
        if safe and self.y_wall < 1.0:
            lim = self.y_wall - WALL_GAP + 0.0015
            skip = ([self.hand_verts[s] for s, _ in SIDES if p.hands[s].get('wall')] +
                    [self.arm_verts[s] for s, _ in SIDES if p.hands[s].get('alt') and p.hands[s].get('k', 0) > 0])
            m = np.ones(len(self.seat_mask), bool)
            for idx in skip:
                m[idx] = False
            ax = (p.rock @ p.hips_q).inverted() @ Vector(X)

            def build(lean, lift):
                q = SitParams.copy(p)
                q.J = dict(p.J)
                if lean:
                    q.J['Spine'] = R(ax, lean) @ q.J.get('Spine', QI())
                q.root = (p.root[0], p.root[1], p.root[2] + lift)
                o = self._pose(q, swing=False)
                pts = self.B.mesh_points(o)
                return o, float(pts[m, 1].max()) - lim, self._butt_low(pts) - FLOOR_GAP * 0.4

            lean, lift = 0.0, 0.0
            pts = self.B.mesh_points(out)
            ex, lo = float(pts[m, 1].max()) - lim, self._butt_low(pts) - FLOOR_GAP * 0.4
            for _ in range(3):
                if lo >= -1e-6:
                    break
                lift += -lo
                out, ex, lo = build(lean, lift)
            if ex > 0:
                a, fa = 0.0, ex
                b = max(1.0, math.degrees(ex / 0.6))
                out_b, fb, _ = build(b, lift)
                while fb > 0:
                    a, fa = b, fb
                    b *= 2
                    out_b, fb, _ = build(b, lift)
                side = 0
                for _ in range(12):
                    c = b - fb * (b - a) / (fb - fa)
                    out_c, fc, _ = build(c, lift)
                    if fc > 0:
                        a, fa = c, fc
                        if side == -1:
                            fb *= 0.5
                        side = -1
                    else:
                        b, fb, out_b = c, fc, out_c
                        if side == 1:
                            fa *= 0.5
                        side = 1
                    if -1e-4 <= fb <= 0:
                        break
                lean, out = b, out_b
            self.last_fix = (lean, lift)
            # final build with the per-arm wall swing (after the body has found its contact)
            q = SitParams.copy(p)
            q.J = dict(p.J)
            if lean:
                q.J['Spine'] = R(ax, lean) @ q.J.get('Spine', QI())
            q.root = (p.root[0], p.root[1], p.root[2] + lift)
            out = self._pose(q, swing=True)
        if world:
            out = {n: self.W @ m_ for n, m_ in out.items()}
        return out

    def soft_reach(self, out, s, tgt, a=0.80, b=0.975):
        """Pull an arm target in smoothly so the elbow never locks straight: distances beyond
        a*L are compressed exponentially toward b*L (L = arm length). A locked elbow would snap
        open like sqrt(shortening) as soon as the target comes back into reach."""
        info = self.arm[s]
        L = info['l1'] + info['l2']
        sh = out[info['names'][0]].translation
        d = Vector(tgt) - sh
        r = d.length
        if r <= a * L:
            return Vector(tgt)
        span = (b - a) * L
        r2 = b * L - span * math.exp(-(r - a * L) / span)
        return sh + d * (r2 / r)

    def _solve_arm(self, base, s, spec):
        """One arm solution on a copy of `base`: soft-reach IK, optional forearm-aligned fist,
        finger curl, then the hand contact with the wall. Returns the new pose dict."""
        B = self.B
        pre = dict(base)
        t2 = self.soft_reach(pre, s, spec['pos'](pre) if callable(spec['pos']) else spec['pos'])
        pole2 = spec['pole'](pre, t2) if callable(spec['pole']) else Vector(spec['pole'])
        q2 = spec['q']
        B.solve_chain2(pre, self.arm[s], t2, B.hand_matrix(s, q2, t2), pole2.normalized())
        if spec.get('wrist'):
            # fist = straight extension of the forearm; blended toward the explicit orientation
            # (palm on the wall) by (1 - wrist). No 180 deg wrist twist.
            fa, hd = P + s + 'ForeArm', P + s + 'Hand'
            Rn = pre[fa].to_3x3() @ B.rest[fa].to_3x3().inverted()
            qn = Rn.to_quaternion()
            q2 = q2.slerp(qn, spec['wrist']) if spec['wrist'] < 1 else qn
            m = B.hand_matrix(s, q2, pre[hd].translation)
            delta = m @ pre[hd].inverted()
            for n in B.subtree(s + 'Hand'):
                pre[n] = delta @ pre[n]
        B.curl(pre, s, spec.get('curl', 0.0), thumb=spec.get('thumb'))
        if spec.get('wall') and self.y_wall < 1.0:
            self._hand_on_wall(pre, s, t2, q2, pole2, spec['wall'])
        return pre

    def _arm_off_wall(self, out, s, margin=0.0):
        """If any vertex of the (blended) arm would cross the wall, swing the whole arm about its
        shoulder joint away from the wall by the smallest angle that clears it (bisection; the
        swing is monotone, so the result is continuous in time)."""
        B = self.B
        lim = self.y_wall - 0.0015 - margin
        idx = self.arm_verts[s]
        fixed = self.swing_override.get(s) if self.swing_override is not None else None
        if fixed is None:
            ex0 = float(B.mesh_points(out)[idx, 1].max()) - lim
            if ex0 <= 0:
                return 0.0
        elif fixed <= 0:
            return 0.0
        a = P + s + 'Arm'
        sh = out[a].translation.copy()
        hand = out[P + s + 'Hand'].translation - sh
        ax = hand.cross(Vector((0, 1, 0)))
        if ax.length < 1e-6:
            ax = Vector((1, 0, 0))
        ax.normalize()
        base = {n: out[n].copy() for n in B.subtree(s + 'Arm')}
        # hand side of the arm moves off the wall (toward -Y) for +angle about ax
        if (ax.cross(hand)).y > 0:
            ax.negate()

        def apply(ang):
            M = C.rot_about(sh, R(ax, ang))
            for n, m in base.items():
                out[n] = M @ m
            return float(B.mesh_points(out)[idx, 1].max()) - lim if fixed is None else 0.0
        if fixed is not None:
            apply(fixed)
            return fixed
        lo, hi = 0.0, 4.0
        while apply(hi) > 0 and hi < 60:
            lo, hi = hi, hi * 2
        for _ in range(14):
            mid = 0.5 * (lo + hi)
            if apply(mid) > 0:
                lo = mid
            else:
                hi = mid
        apply(hi)
        return hi

    def _hand_on_wall(self, out, s, tgt, q, pole, mode, margin=0.0):
        """Stop a hand on the wall: measured on the skinned mesh, the IK target is shifted back by
        the exact excess (mode True: never past the wall; 'touch': exactly on it). Fingers keep
        their curl because the hand subtree moves rigidly."""
        B = self.B
        lim = self.y_wall - 0.0025 - margin
        for _ in range(8):
            pts = B.mesh_points(out)
            ex = float(pts[self.hand_verts[s], 1].max()) - lim
            if not (ex > 2e-6 or (mode == 'touch' and ex < -1e-4)):
                break
            tgt = tgt - Vector((0, ex, 0))
            B.solve_chain2(out, self.arm[s], tgt, B.hand_matrix(s, q, tgt), Vector(pole).normalized())
        return tgt

    def _pose(self, p, swing=True):
        B = self.B
        self.last_swing = {'Left': 0.0, 'Right': 0.0}
        J = dict(p.J)
        J['Hips'] = p.hips_q
        # root: rotate the pelvis about the butt contact (rocking on the sit bones), then offset
        piv = Vector((0, 0.02, 0.0))
        root = (Matrix.Translation(Vector(p.root) + Vector((0, 0, self.seat_z - self.hip0.z))))
        root = Matrix.Translation(piv) @ p.rock.to_matrix().to_4x4() @ Matrix.Translation(-piv) @ root
        out, D = B.fk(self.base, J, root)
        for s, sgn in SIDES:
            ank, fq, pole = p.feet[s]
            fm = (fq.to_matrix() @ self.base[P + s + 'Foot'].to_3x3()).to_4x4()
            fm.translation = Vector(ank)
            B.solve_chain2(out, self.leg[s], Vector(ank), fm, Vector(pole).normalized())
        for s, sgn in SIDES:
            h = p.hands[s]
            alt, k = h.get('alt'), h.get('k', 0.0)
            pre = dict(out) if alt and k > 0 else None
            tgt = h['pos'](out) if callable(h['pos']) else Vector(h['pos'])
            q = h['q'](out) if callable(h['q']) else h['q']
            B.solve_chain2(out, self.arm[s], tgt, B.hand_matrix(s, q, tgt), Vector(h['pole']).normalized())
            B.curl(out, s, h.get('curl', 0.0), thumb=h.get('thumb'))
            h['_t'], h['_q'] = tgt, q
            if pre is not None:
                # a second arm solution (e.g. fists on the wall), blended in rotation space so the
                # arm travels in a natural arc instead of dragging the hand through the body.
                # alt may itself carry a 'guard' solution blended in by (1 - alt['k2']).
                sol = self._solve_arm(pre, s, alt)
                rf = h.get('refs') or {}
                if alt.get('guard') is not None and alt.get('k2', 1.0) < 1.0:
                    g = self._solve_arm(pre, s, alt['guard'])
                    B.blend_subtree(g, sol, s + 'Arm', alt['k2'], rf.get('inner'), tag=(s, 'inner'))
                    sol = g
                B.blend_subtree(out, sol, s + 'Arm', k, rf.get('outer'), tag=(s, 'outer'))
                if swing and alt.get('wall') and self.y_wall < 1.0:
                    self.last_swing[s] = self._arm_off_wall(out, s)

        # wall contact for hands: a hand that would cross the wall stops on it (measured on the
        # skinned mesh, the IK target is shifted back by the exact excess; fingers keep their curl)
        wall_hands = [s for s, _ in SIDES if p.hands[s].get('wall')]
        if wall_hands and self.y_wall < 1.0:
            lim = self.y_wall - 0.0025
            for _ in range(8):
                pts = B.mesh_points(out)
                done = True
                for s in wall_hands:
                    h = p.hands[s]
                    ex = float(pts[self.hand_verts[s], 1].max()) - lim
                    if ex > 2e-6 or (h.get('wall') == 'touch' and ex < -1e-4):
                        done = False
                        tgt = h['_t'] - Vector((0, ex, 0))
                        h['_t'] = tgt
                        B.solve_chain2(out, self.arm[s], tgt, B.hand_matrix(s, h['_q'], tgt),
                                      Vector(h['pole']).normalized())
                if done:
                    break
        return out

    # -- shin-relative hand targets (the hug follows the knees) ---------------------------------
    def shin_grip(self, side, down=0.11, front=0.075, inward=0.035):
        sgn = 1 if side == 'Left' else -1

        def f(out):
            K = out[P + side + 'Leg'].translation
            E = out[P + side + 'Foot'].translation
            d = (E - K).normalized()
            fr = Vector((0, -1, 0.35))
            fr = (fr - d * fr.dot(d)).normalized()
            return K + d * down + fr * front + Vector((-sgn * inward, 0, 0))
        return f

    def shin_grip_q(self, side, twist=0.0):
        sgn = 1 if side == 'Left' else -1

        def f(out):
            K = out[P + side + 'Leg'].translation
            E = out[P + side + 'Foot'].translation
            d = (E - K).normalized()
            fr = Vector((0, -1, 0.35))
            fr = (fr - d * fr.dot(d)).normalized()
            # fingers wrap inward around the shin front, palm on the shin
            point = Vector((-sgn, 0, 0))
            point = (point - fr * point.dot(fr))
            q = hand_q(side, point, -fr)
            return R(fr, sgn * twist) @ q if twist else q
        return f


class SitParams:
    """Neutral seated parameters (the knee hug), in the local frame."""

    def __init__(self):
        self.root = (0.0, 0.0, 0.0)
        self.rock = QI()
        self.hips_q = R(X, -16)
        self.J = {
            'Spine': R(X, 11), 'Spine1': R(X, 11), 'Spine2': R(X, 9),
            'Neck': R(X, 14), 'Head': R(X, -12),
            'LeftShoulder': R(Y, -12), 'RightShoulder': R(Y, 12),
        }
        self.feet = {s: ((sgn * 0.15, -0.47, 0.1165 + FLOOR_GAP - 0.0005), QI(), (sgn * 0.25, -0.55, 0.8))
                     for s, sgn in SIDES}
        self.hands = {}

    @staticmethod
    def copy(p):
        q = SitParams.__new__(SitParams)
        q.__dict__.update(p.__dict__)
        return q


def neutral(S):
    p = SitParams()
    for s, sgn in SIDES:
        p.hands[s] = {'pos': S.shin_grip(s), 'q': S.shin_grip_q(s), 'pole': (sgn * 1.0, 0.5, -0.3),
                      'curl': 0.5, 'thumb': 0.4}
    return p


# ----------------------------------------------------------------------------- Cargo_Sit_Idle_v04
SIT_T = 4.5


def sit_channels():
    T = SIT_T
    ch = {}
    # head yaw (deg, - = to his right, toward the doors): snap glance with overshoot, held stare
    # with drift, reluctant turn back; double-take (30 then 55) with a short hold; turn back
    ch['yaw'] = Curve([(0, 0), (0.42, 0, 'flat'), (0.56, 4.0, 'flat'), (0.66, -57), (0.74, -49), (1.05, -51), (1.45, -47, 'flat'),
                       (1.62, -12), (1.72, 2.5), (1.85, 0), (2.85, 0, 'flat'), (2.93, -31), (2.99, -28, 'flat'),
                       (3.03, -60), (3.09, -54), (3.22, -55, 'flat'), (3.48, -6), (3.6, 1.0), (3.8, 0), (T, 0)],
                      periodic=True)
    # shoulder jolt / shrug on top of the base shrug (0..1)
    ch['jolt'] = Curve([(0, 0), (0.58, 0, 'flat'), (0.66, 1.0), (0.80, 0.55), (1.45, 0.65), (1.7, 0.2),
                        (1.80, 0.25), (1.95, 0.85), (2.08, -0.15), (2.25, 0.1), (2.92, 0.2), (3.03, 1.0),
                        (3.15, 0.6), (3.6, 0.45), (4.05, 0.0), (T, 0)], periodic=True)
    # shrink back against the wall (0..1): spine straightens toward the wall, head sinks
    ch['shrink'] = Curve([(0, 0), (0.62, 0, 'flat'), (0.85, 0.85), (1.45, 1.0), (1.75, 0.2), (2.2, 0.0),
                          (2.9, 0), (3.1, 0.6), (3.6, 0.2), (T, 0)], periodic=True)
    # gulp (0..1): chin tuck + head dip; arms squeeze the knees
    ch['gulp'] = Curve([(0, 0), (1.72, 0, 'flat'), (1.86, 0.25), (1.98, 1.0), (2.06, 0.9), (2.2, 0.0), (T, 0)],
                       periodic=True)
    ch['squeeze'] = Curve([(0, 0), (1.75, 0, 'flat'), (1.95, 1.0), (2.25, 0.7), (2.9, 0.4), (3.05, 0.8),
                           (3.6, 1.0), (4.1, 0.2), (T, 0)], periodic=True)
    # anxious rocks on the butt (deg, + forward); the wall stops the back swing
    ch['rock'] = Curve([(0, 0), (2.2, 0, 'flat'), (2.38, 6.5), (2.52, 0.8), (2.70, 5.5), (2.88, 0.2), (2.95, 0),
                        (T, 0)], periodic=True)
    # sink lower behind the knees (0..1)
    ch['sink'] = Curve([(0, 0), (3.2, 0, 'flat'), (3.55, 1.0), (3.85, 0.85), (4.25, 0.15), (T, 0)], periodic=True)
    # panicky shallow breathing, 9 cycles per loop (2 Hz), deeper while staring
    amp = Curve([(0, 0.55), (0.6, 0.8), (1.4, 1.0), (2.2, 0.5), (3.1, 0.9), (4.0, 0.6), (T, 0.55)], periodic=True)
    ch['breath'] = lambda t: amp(t) * math.sin(2 * math.pi * 9 * t / T)
    # trembling: integer cycles per loop (6.9 to 9.1 Hz), zero at the seam; stronger while staring
    env = Curve([(0, 0.45), (0.5, 0.5), (0.75, 1.0), (1.45, 1.0), (1.8, 0.5), (2.9, 0.6), (3.1, 1.0), (3.6, 0.8),
                 (4.2, 0.45), (T, 0.45)], periodic=True)
    nz = [C.pnoise(T, 11 + i, cycles=(31, 37, 41)) for i in range(6)]
    ch['trem'] = lambda t, i: env(t) * nz[i](t)
    # overlap: chest follows 25 % of the head yaw with a lag, head roll follows the snap
    yaw = ch['yaw']
    ch['yaw_lag'] = C.spring_periodic(yaw, T, 1 / 240, 2.2, 0.55)
    return ch


class SitCtx:
    def __init__(self, B):
        self.B = B
        self.S = SitRig(B)
        self.ch = sit_channels()


def sit_idle_pose(ctx, t):
    S, ch = ctx.S, ctx.ch
    yaw, lag = ch['yaw'](t), ch['yaw_lag'](t)
    jolt, shrink, gulp = ch['jolt'](t), ch['shrink'](t), ch['gulp'](t)
    sq, rock, sink, b = ch['squeeze'](t), ch['rock'](t), ch['sink'](t), ch['breath'](t)
    tr = [ch['trem'](t, i) for i in range(6)]
    p = neutral(S)
    chest = 0.25 * (yaw + lag)
    p.rock = R(X, rock)
    p.hips_q = p.hips_q @ R(X, 0.6 * b)
    J = p.J
    # leans away from the doors (his left side down) while he stares at them
    J['Spine'] = J['Spine'] @ R(X, -3.0 * shrink + 2.0 * sink) @ R(Z, 0.3 * chest) @ R(Y, 0.4 * tr[0] + 3.5 * shrink)
    J['Spine1'] = J['Spine1'] @ R(X, -2.5 * shrink + 3.0 * sink - 0.8 * b) @ R(Z, 0.35 * chest)
    J['Spine2'] = J['Spine2'] @ R(X, -1.5 * shrink + 2.5 * sink - 1.0 * b + 0.5 * tr[1]) @ R(Z, 0.35 * chest)
    shr = 7.0 * jolt + 4.0 * shrink + 2.0 * b
    J['LeftShoulder'] = J['LeftShoulder'] @ R(Y, -shr)
    J['RightShoulder'] = J['RightShoulder'] @ R(Y, shr)
    hy = yaw - chest
    J['Neck'] = J['Neck'] @ R(X, -4.0 * shrink + 7.0 * gulp + 6.0 * sink + 0.6 * tr[2]) @ R(Z, 0.35 * hy)
    J['Head'] = (J['Head'] @ R(Z, 0.65 * hy) @ R(X, 3.0 * shrink + 9.0 * gulp - 1.0 * sink + 0.7 * tr[3])
                 @ R(Y, -0.07 * hy - 0.05 * lag + 0.6 * tr[4]))
    for s, sgn in SIDES:
        h = p.hands[s]
        base = S.shin_grip(s, inward=0.035 + 0.025 * sq)
        k = 0.0016 * tr[5] * sgn
        h['pos'] = (lambda f, k=k: (lambda out: f(out) + Vector((k, 0, 0.6 * k))))(base)
        h['curl'] = 0.5 + 0.25 * sq
    out = S.pose(p)
    return out, {'wall_lean_deg': S.last_fix[0], 'seat_lift_m': S.last_fix[1]}


CONTRACT_JSON = C.HERE / 'Cargo_Sit_Contract_v04.json'


def sit_contract_values(ctx):
    """Raw values of the cargo sit contract (Cargo_Sit_Idle_v04 frame 1). Frozen once in
    Cargo_Sit_Contract_v04.json so the sit idle, the knock and the sit-up key bit-identical
    values; computed (and the file written, never overwritten) when it does not exist yet."""
    import json
    if CONTRACT_JSON.exists():
        d = json.loads(CONTRACT_JSON.read_text(encoding='utf-8'))
        return {n: {'q': tuple(v['q']), 'loc': tuple(v['loc']) if v['loc'] else None} for n, v in d['values'].items()}
    sit = ctx if isinstance(ctx, SitCtx) else ctx.sit
    pose = sit_idle_pose(sit, 0.0)[0]
    v = ctx.B.values_from_pose(pose)
    CONTRACT_JSON.write_text(json.dumps({
        'contract': 'Cargo sit contract = Cargo_Sit_Idle_v04 frame 1 = Cargo_Knock_v03b first/last frame = '
                    'SitUp_Cargo_v04 last frame', 'rig': C.RIG_NAME, 'bone_order': ctx.B.order,
        'layout': {'wall_x_m': C.WALL_X, 'floor_z_m': 0.0, 'facing': '+X (back to the wall)',
                   'doors': '-Y (his right)', 'hips_world_m': list(pose[P + 'Hips'].translation)},
        'values': {n: {'q': list(x['q']), 'loc': list(x['loc']) if x['loc'] else None} for n, x in v.items()}},
        indent=1), encoding='utf-8')
    return v


def _sit_canonical(ctx, N):
    v = sit_contract_values(ctx)
    return {1.0: v, float(N + 1): v}


# ----------------------------------------------------------------------------- Cargo_Knock_v03b
KNOCK_T = 3.3
L_HITS = (0.62, 0.94)          # alternating hammer-fists (L R L R, 6.25 Hz alternation)
R_HITS = (0.78, 1.10)
SLAM = 1.40 
CHEST_TWIST = 92            # chest twist on top of the 80 deg swivel: faces the wall ~8 deg off-square
                   # double-fist slam


def _pulse(t, t0, w=0.05):
    """Hit response: 0 before t0, quick rise, decaying (peak 1 at t0 + w)."""
    if t <= t0:
        return 0.0
    x = (t - t0) / w
    return x * math.exp(1 - x)


def knock_channels():
    T = KNOCK_T
    ch = {}
    # swivel on the butt (0..1): small counter-move in the anticipation, overshoot, settle
    ch['turn'] = Curve([(0, 0), (0.06, 0, 'flat'), (0.17, -0.05), (0.40, 0.92), (0.48, 1.04), (0.60, 1.0),
                        (2.38, 1.0, 'flat'), (2.62, 0.52), (2.84, 0.04), (2.95, -0.02), (3.08, 0.0), (T, 0)])
    ch['chest'] = Curve([(0, 0), (0.12, 0, 'flat'), (0.22, -0.04), (0.47, 0.95), (0.56, 1.06), (0.68, 1.0),
                         (2.40, 1.0, 'flat'), (2.70, 0.5), (2.92, 0.0), (T, 0)])
    # anticipation squash (0..1)
    ch['squash'] = Curve([(0, 0), (0.04, 0, 'flat'), (0.16, 1.0), (0.26, 0.2), (0.34, -0.2), (0.45, 0.0), (T, 0)])
    # head yaw relative to the chest (deg): snaps toward the wall over his right shoulder first
    ch['head'] = Curve([(0, 0), (0.04, 0, 'flat'), (0.13, -48), (0.22, -44), (0.48, 30), (0.58, 40),
                        (0.9, 34), (1.2, 42), (1.45, 38), (1.62, 52), (1.72, 58), (2.24, 56, 'flat'), (2.55, 25), (2.85, 0),
                        (T, 0)])
    # release the knees (0 = hug, 1 = free hands)
    ch['free'] = Curve([(0, 0), (0.14, 0, 'flat'), (0.52, 1.0, 'flat'), (2.40, 1.0, 'flat'), (2.94, 0.0, 'flat'),
                        (T, 0)])
    # listening (0..1): palms flat on the wall, cheek pressed to it
    ch['listen'] = Curve([(0, 0), (1.47, 0, 'flat'), (1.62, 0.85), (1.75, 1.0), (2.22, 1.0, 'flat'), (2.42, 0.0),
                          (T, 0)])
    # fists reach for the wall (0 = guard in front of the chest)
    ch['reach'] = Curve([(0, 0), (0.34, 0, 'flat'), (0.58, 1.0, 'flat'), (2.36, 1.0, 'flat'), (2.78, 0.0, 'flat'), (T, 0)])
    # leaning in toward the wall while pounding (0..1)
    ch['pound'] = Curve([(0, 0), (0.30, 0, 'flat'), (0.55, 1.0), (1.45, 1.0, 'flat'), (1.75, 0.0, 'flat'), (T, 0)])
    # double-fist raise (0..1) and slam
    ch['raise'] = Curve([(0, 0), (1.12, 0, 'flat'), (1.23, 1.0), (1.26, 1.02, 'flat'), (1.40, 0.0, ('lin', 'flat')),
                         (T, 0)])
    # slump: deflate after listening (0..1)
    ch['slump'] = Curve([(0, 0), (2.22, 0, 'flat'), (2.45, 1.0), (2.75, 0.8), (3.0, 0.15), (3.3, 0.0, 'flat')])
    # sad sigh: shoulders rise and drop
    ch['sigh'] = Curve([(0, 0), (2.85, 0, 'flat'), (3.02, 1.0), (3.12, 0.95), (3.24, -0.15), (3.3, 0.0, 'flat')])
    env = Curve([(0, 0), (1.55, 0, 'flat'), (1.7, 1.0), (2.2, 1.0), (2.4, 0.0, 'flat'), (T, 0)])
    nz = [C.pnoise(T, 31 + i, cycles=(27, 31, 37)) for i in range(4)]
    ch['trem'] = lambda t, i: env(t) * nz[i](t)
    return ch


def _strike(t, hits, slam):
    """Per-hand fist travel: 1 = into the wall (stopped by the contact), 0 = wound up."""
    v = 0.0
    for th in hits + (slam,):
        d = t - th
        if -0.13 <= d <= 0.0:          # accelerating strike (ease-in)
            u = 1 + d / 0.13
            v = max(v, u ** 1.6)
        elif 0.0 < d <= 0.035:         # stuck on the wall for a frame
            v = max(v, 1.0)
        elif 0.035 < d <= 0.17:        # recoil (ease-out)
            u = (d - 0.035) / 0.135
            v = max(v, 1 - smooth(u))
    return v


class KnockCtx:
    def __init__(self, B):
        self.B = B
        self.S = SitRig(B)
        self.ch = knock_channels()
        self.sit = SitCtx.__new__(SitCtx)
        self.sit.B, self.sit.S, self.sit.ch = B, self.S, sit_channels()
        self.swing = None
        self.refs = None
        self.refs = self._blend_refs()
        self.swing = self._swing_table()

    def _blend_refs(self, dt=1 / 240):
        """Pre-pass for the arm blends: record both endpoint rotations of every arm blend on a
        fine time grid, make each sequence sign-continuous, and use them as hemisphere references
        (deterministic: the final pass at any time t aligns to the table, not to call order)."""
        import numpy as np
        n = int(round(KNOCK_T / dt))
        tabs = {}
        self.B.blend_log = {}
        for i in range(n + 1):
            t = i * dt
            self.B.blend_log.clear()
            knock_pose(self, t)
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
        """Pass 1: the wall swing each arm needs (measured), then max-filter (+-rmax) and blur
        (sigma, support 3 sigma < rmax) so the applied swing is smooth and never smaller than
        needed at the sampled times."""
        import numpy as np
        n = int(round(KNOCK_T / dt))
        ts = np.arange(n + 1) * dt
        need = {s: np.zeros(n + 1) for s, _ in SIDES}
        for i, t in enumerate(ts):
            knock_pose(self, float(t))
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
        import numpy as np
        ts, tab = self.swing
        return {s: float(np.interp(t, ts, tab[s])) for s, _ in SIDES}


def knock_pose(ctx, t):
    S, ch = ctx.S, ctx.ch
    T = KNOCK_T
    yw = S.y_wall
    u, cu, sq = ch['turn'](t), ch['chest'](t), ch['squash'](t)
    hy, free, lis = ch['head'](t), ch['free'](t), ch['listen'](t)
    rai, slump, sigh = ch['raise'](t), ch['slump'](t), ch['sigh'](t)
    tr = [ch['trem'](t, i) for i in range(4)]
    pound = ch['pound'](t)
    bounce = sum(_pulse(t, th) for th in L_HITS + R_HITS) + 1.6 * _pulse(t, SLAM, 0.07)
    shake = sum(_pulse(t, th, 0.04) * (1 if th in L_HITS else -1) for th in L_HITS + R_HITS)
    p = neutral(S)
    # leans in toward the wall to listen (the wall contact solve stops the cheek on it)
    # mid-swivel the butt lurches ~15 cm off the wall so the swinging right shoulder clears it
    p.root = (0.0, -0.12 * math.sin(math.pi * clamp(u)) ** 1.5 - 0.09 * smooth(clamp(u)) * (1 - slump), 0.0)
    p.rock = R(Z, -80 * u) @ R(X, 3.0 * sq - 4.0 * slump)
    J = p.J
    tw = -CHEST_TWIST * cu
    J['Spine'] = J['Spine'] @ R(Z, 0.36 * tw) @ R(X, 4 * sq + 3 * slump - 2.0 * bounce)
    # leans in toward the wall to listen (the wall contact solve stops the cheek on it)
    ax = (p.rock @ p.hips_q).inverted() @ Vector(X)
    J['Spine'] = R(ax, -30 * lis - 20 * pound - 3.0 * bounce) @ J['Spine']
    J['Spine1'] = J['Spine1'] @ R(Z, 0.36 * tw) @ R(X, 3 * sq + 4 * slump - 1.5 * bounce - 2.0 * sigh + 2.0 * lis)
    J['Spine2'] = J['Spine2'] @ R(Z, 0.28 * tw) @ R(X, 2 * sq + 3 * slump - 1.0 * bounce - 2.0 * sigh)
    shr = 8 * sq + 6 * rai + 9 * sigh - 6 * slump + 3 * lis
    J['LeftShoulder'] = J['LeftShoulder'] @ R(Y, -shr)
    J['RightShoulder'] = J['RightShoulder'] @ R(Y, shr)
    J['Neck'] = J['Neck'] @ R(Z, 0.4 * hy) @ R(X, -6 * sq + 8 * slump - 4 * rai + 0.6 * tr[0])
    J['Head'] = (J['Head'] @ R(Z, 0.6 * hy) @ R(X, -4 * sq + 6 * slump - 3 * sigh + 3.0 * bounce + 0.6 * tr[1])
                 @ R(Y, 7 * shake - 22 * lis + 0.6 * tr[2]))
    # legs: knees fall to his left into a side-sit, feet pivot roughly in place
    for s, sgn in SIDES:
        a0, fq0, pole0 = p.feet[s]
        a1 = (0.11, -0.50, a0[2]) if s == 'Left' else (-0.20, -0.42, a0[2])
        # knees point to his new front (perpendicular to the hip-ankle line, so no flip)
        pole1 = (-0.90, -0.12, 0.40)
        k = smoother(u)
        an = vlerp(a0, a1, k)
        an.z += 0.008 * math.sin(math.pi * clamp(u)) ** 2      # feet skid round a hair off the floor
        p.feet[s] = (tuple(an), R(Z, -38 * k), tuple(vlerp(pole0, pole1, k)))
    # hands: shin hug <-> fists / palms on the wall (targets in the local frame, wall at y = yw)
    rch = smooth(ch['reach'](t))
    piv = Vector((0, 0.02, 0))
    sl = _strike(t, L_HITS, SLAM)
    sr = _strike(t, R_HITS, SLAM)
    for s, sgn in SIDES:
        h = p.hands[s]
        st = sl if s == 'Left' else sr
        c = Vector((-0.27, yw + 0.03, 0.68)) if s == 'Left' else Vector((0.12, yw + 0.03, 0.78))
        wind = c + Vector((0.02 * sgn, -0.11, 0.09))
        high = Vector((c.x + 0.03 * sgn, yw - 0.14, 0.98))
        fist = wind.lerp(c, st)
        fist = fist.lerp(high, rai)
        palm = Vector((c.x - 0.04 * sgn, yw + 0.01, 0.80 + 0.03 * (s == 'Right')))
        tgt = fist.lerp(palm, lis)
        fq = hand_q_thumb(s, (0, 0.85, -0.35 + 0.9 * rai), (0, -0.2, 1))   # vertical fist, thumb up
        pq = hand_q(s, (sgn * 0.25, 0.0, 1.0), (0, 1, 0))                   # palm flat on the wall
        q_wall = fq.slerp(pq, lis)
        # until the swivel is complete the wall targets ride with the chest (rotated back by the
        # yaw still missing), so the arms keep their shape relative to the body during the turn
        off = R(Z, -80 * (u - 1) - CHEST_TWIST * (cu - 1))
        tgt = piv + off @ (tgt - piv) + Vector(p.root)
        q_wall = off @ q_wall

        def guard_tgt(out, side=s, sgn=sgn, u=u):
            # guard between the knee hug and the wall, measured from his own shoulder (never folded
            # tight: a target too close to the shoulder makes the elbow swing wildly): fists up by
            # the face when facing the wall, lowered to the chest while swivelled away
            ch_m = out[P + 'Spine2']
            Mq = ch_m.to_3x3() @ S.B.rest[P + 'Spine2'].to_3x3().inverted()
            sh = out[P + side + 'Arm'].translation
            high = sh + Mq @ Vector((sgn * 0.03, 0.01, 0.0)) + Vector((0, 0, 0.25))
            low = sh + Mq @ Vector((-sgn * 0.04, -0.21, 0.0))
            return high.lerp(low, smooth(1 - u))

        # elbow pole: his side axis made perpendicular to the shoulder->fist line (never parallel
        # to the reach, so the elbow cannot flip while the chest swings round), down, and away
        # from the wall (van -Y) so the elbows are never pressed into it
        side_ax = R(Z, -80 * u - CHEST_TWIST * cu) @ Vector((sgn, 0, 0))

        def elbow(out, tg, side=s, side_ax=side_ax, lis=lis):
            d = (tg - out[P + side + 'Arm'].translation).normalized()
            perp = (side_ax - d * side_ax.dot(d)).normalized()
            return (perp * 0.7 + Vector((0, 0, -0.6)) + Vector((0, -1, 0)) * (0.55 + 0.3 * lis)).normalized()
        h['alt'] = {'pos': tgt, 'q': q_wall, 'pole': elbow, 'wrist': 1 - smooth(lis), 'flex': 0.0,
                    'curl': lerp(1.0, 0.12, lis),
                    'thumb': lerp(0.9, 0.1, lis)}
        h['alt']['wall'] = True        # targets sit past the wall; the contact solve stops them on it
        h['alt']['guard'] = dict(h['alt'], pos=guard_tgt, wall=False, wrist=1.0)
        # out and back the arms pass through the guard (same path both ways: no net 360 deg twist)
        h['alt']['k2'] = rch
        h['k'] = smooth(free)
        h['refs'] = ctx.refs_at(s, t) if getattr(ctx, 'refs', None) else None
        h['curl'] = 0.5 + 0.15 * sigh
    S.swing_override = ctx.swing_at(t) if getattr(ctx, 'swing', None) is not None else None
    out = S.pose(p)
    S.swing_override = None
    return out, {'wall_lean_deg': S.last_fix[0], 'seat_lift_m': S.last_fix[1],
                 'arm_swing_L_deg': S.last_swing['Left'], 'arm_swing_R_deg': S.last_swing['Right']}


def _knock_post(ctx, frames, canonical):
    """Safety nets on the sampled knock poses (contract end frames are never touched):
    1. rotation-rate limit for the swivel transitions (acting_core.limit_rotation_steps, < 25 deg
       per half frame);
    2. the arms are swung about the shoulder off the wall where the smoothed frames would graze it;
       the swing is measured per frame, max-filtered (+-3 samples) and blurred so it stays smooth."""
    S = ctx.S
    keep = set(canonical.keys())
    ctx.post_changed, ctx.post_swing = {}, {'Left': 0.0, 'Right': 0.0}
    for rnd in range(4):         # alternate until both hold (usually 2 rounds)
        ch = C.limit_rotation_steps(ctx.B, frames, max_deg=23.0, keep=keep)
        for b_, n_ in ch.items():
            ctx.post_changed[b_] = max(n_, ctx.post_changed.get(b_, 0))
        sw = _knock_wall_swing(ctx, frames, keep)
        for s_ in sw:
            ctx.post_swing[s_] = max(ctx.post_swing[s_], sw[s_])
        if not ch and max(sw.values()) <= 0:
            break


def _knock_wall_swing(ctx, frames, keep):
    S = ctx.S
    keys = sorted(frames)
    Winv = S.W.inverted()
    need = {s: np.zeros(len(keys)) for s, _ in SIDES}
    for i, f in enumerate(keys):
        if f in keep:
            continue
        loc = {n: Winv @ m for n, m in frames[f].items()}
        S.swing_override = None
        for s, _ in SIDES:
            need[s][i] = S._arm_off_wall(dict(loc), s, margin=0.004)
    k = np.array([0.25, 0.5, 1.0, 0.5, 0.25])
    k /= k.sum()
    applied = {}
    for s, _ in SIDES:
        a = need[s]
        m = np.array([a[max(0, i - 3):i + 4].max() for i in range(len(a))])
        mp = np.concatenate([m[:1], m[:1], m, m[-1:], m[-1:]])
        applied[s] = np.maximum(np.convolve(mp, k, mode='valid'), a)
    for i, f in enumerate(keys):
        if f in keep or (applied['Left'][i] <= 0 and applied['Right'][i] <= 0):
            continue
        loc = {n: Winv @ m for n, m in frames[f].items()}
        S.swing_override = {s: float(applied[s][i]) for s, _ in SIDES}
        for s, _ in SIDES:
            S._arm_off_wall(loc, s, margin=0.004)
        S.swing_override = None
        frames[f] = {n: S.W @ m for n, m in loc.items()}
    return {s: float(applied[s].max()) for s, _ in SIDES}


def _knock_canonical(ctx, N):
    v = sit_contract_values(ctx)
    return {1.0: v, float(N + 1): v}


# ----------------------------------------------------------------------------- SitUp_Cargo_v04
SITUP_T = 2.4
HOLD = 0.13                    # exact supine hold for the ragdoll blend (frames 1..4.9)


def situp_channels():
    T = SITUP_T
    ch = {}
    # body blend lying -> sitting (0..1); the giant head LAGS (stays back), then FLOPS forward
    ch['body'] = Curve([(0, 0), (HOLD, 0, 'flat'), (0.40, 0.10), (0.50, 0.22), (0.66, 0.78), (0.80, 1.0, 'flat'),
                        (T, 1.0, 'flat')])
    ch['head'] = Curve([(0, 0), (HOLD, 0, 'flat'), (0.40, 0.03), (0.58, 0.07), (0.70, 0.55), (0.77, 1.0, 'flat'),
                        (T, 1.0, 'flat')])
    ch['flop'] = Curve([(0, 0), (0.68, 0, 'flat'), (0.77, 1.0), (0.84, 0.70), (0.91, 0.82), (1.0, 0.25), (1.10, 0.0),
                        (T, 0, 'flat')])
    # legs: drop and bend right after the hold, feet slide up to the butt
    ch['knees'] = Curve([(0, 0), (HOLD, 0, 'flat'), (0.25, 0.45), (0.40, 0.9), (0.50, 1.0, 'flat'), (T, 1.0, 'flat')])
    # groggy stir: head roll, hand twitch
    ch['stir'] = Curve([(0, 0), (HOLD, 0, 'flat'), (0.24, 1.0), (0.33, 0.55), (0.42, 0.0), (T, 0, 'flat')])
    # hands push on the floor during the sit-up
    ch['push'] = Curve([(0, 0), (0.14, 0, 'flat'), (0.48, 1.0), (0.64, 1.0), (0.96, 0.0, 'flat'), (T, 0, 'flat')])
    # dazed "brrr" head shake: 3 decaying shakes
    ch['shake_env'] = Curve([(0, 0), (0.80, 0, 'flat'), (0.86, 1.0), (1.15, 0.0, 'flat'), (T, 0, 'flat')])
    # rub the bump (right hand on the back-top of the head, small circles)
    ch['rub'] = Curve([(0, 0), (0.94, 0, 'flat'), (1.22, 1.0), (1.50, 1.0), (1.54, 0.97, 'flat'), (1.80, 0.0, 'flat'),
                       (T, 0, 'flat')])
    ch['wince'] = Curve([(0, 0), (1.12, 0, 'flat'), (1.24, 1.0), (1.46, 0.8), (1.52, 0.0), (T, 0, 'flat')])
    # realisation: slow look up (0..1) then SNAP panic glance at the doors (in front of him)
    ch['look'] = Curve([(0, 0), (1.48, 0, 'flat'), (1.60, 0.6), (1.64, 1.25), (1.70, 1.0), (1.80, 0.55), (2.05, 0.0),
                        (T, 0, 'flat')])
    # scramble: turn 90 deg to his left and scoot toward the wall in two heel pushes
    ch['turn'] = Curve([(0, 0), (1.68, 0, 'flat'), (1.80, 0.45), (1.86, 0.52), (1.96, 0.94), (2.03, 1.0, 'flat'),
                        (T, 1.0, 'flat')])
    ch['scoot'] = Curve([(0, 0), (1.70, 0, 'flat'), (1.82, 0.40), (1.88, 0.44), (1.99, 0.97), (2.06, 1.0, 'flat'),
                         (T, 1.0, 'flat')])
    # curl into the knee hug (0..1) with a small squash when the hood bumps the wall
    ch['hug'] = Curve([(0, 0), (1.86, 0, 'flat'), (2.10, 0.75), (2.30, 1.0, 'flat'), (T, 1.0, 'flat')])
    ch['bump'] = Curve([(0, 0), (2.02, 0, 'flat'), (2.08, 1.0), (2.18, -0.35), (2.28, 0.1), (2.36, 0.0, 'flat'),
                        (T, 0, 'flat')])
    return ch


class SitUpCtx:
    def __init__(self, B):
        self.B = B
        self.S = SitRig(B)
        self.ch = situp_channels()
        self.sit = SitCtx.__new__(SitCtx)
        self.sit.B, self.sit.S, self.sit.ch = B, self.S, sit_channels()
        self.contract = sit_idle_pose(self.sit, 0.0)[0]
        self.sup_vals = B.supine_values
        sup = B.supine
        self.sup_ankle = {s: sup[P + s + 'Foot'].translation.copy() for s, _ in SIDES}
        self.sup_foot = {s: sup[P + s + 'Foot'].copy() for s, _ in SIDES}
        # supine leg chains (straight, knee caps up)
        self.leg_sup = {s: B.chain_info2(sup, 'leg', s, (0, 0, 1)) for s, _ in SIDES}


def _head_axes(B, out):
    M = out[P + 'Head'].to_3x3() @ B.rest[P + 'Head'].to_3x3().inverted()
    return M @ Vector((0, -1, 0)), M @ Vector((0, 0, 1)), M @ Vector((1, 0, 0))   # face, up, his left


def situp_pose(ctx, t):
    B, S, ch = ctx.B, ctx.S, ctx.ch
    T = SITUP_T
    if t <= HOLD + 1e-9:
        return {n: m.copy() for n, m in B.supine.items()}, {'phase': 'hold'}
    if t >= T - 1e-9:
        return {n: m.copy() for n, m in ctx.contract.items()}, {'phase': 'contract'}
    wb, wh, fl = ch['body'](t), ch['head'](t), ch['flop'](t)
    kn, stir, push = ch['knees'](t), ch['stir'](t), ch['push'](t)
    se, rub, wince, look = ch['shake_env'](t), ch['rub'](t), ch['wince'](t), ch['look'](t)
    tu, sc, hug, bump = ch['turn'](t), ch['scoot'](t), ch['hug'](t), ch['bump'](t)
    # ---- sit track in the local frame (at the origin, facing -Y), then placed by M(t)
    p = neutral(S)
    loose = 1 - hug
    p.hips_q = p.hips_q @ R(X, -6 * loose)
    J = p.J
    J['Spine'] = J['Spine'] @ R(X, 6 * loose - 3 * bump)
    J['Spine1'] = J['Spine1'] @ R(X, 4 * loose - 2 * bump)
    J['Spine2'] = J['Spine2'] @ R(X, 2 * loose)
    J['LeftShoulder'] = J['LeftShoulder'] @ R(Y, 10 * loose)
    J['RightShoulder'] = J['RightShoulder'] @ R(Y, -10 * loose)
    J['Neck'] = J['Neck'] @ R(X, -10 * look + 6 * bump)
    J['Head'] = J['Head'] @ R(X, -8 * look - 4 * bump)
    for s, sgn in SIDES:
        a0, fq, pole = p.feet[s]
        a1 = (sgn * 0.17, -0.60, a0[2])
        p.feet[s] = (tuple(vlerp(a1, a0, hug)), fq, pole)
    th = 90 * tu
    sx = S.wx * sc
    M = Matrix.Translation((sx, 0, 0)) @ R(Z, th).to_matrix().to_4x4()
    for s, sgn in SIDES:
        h = p.hands[s]
        # hands rest loosely on the knees while dazed, hug at the end
        knee = (lambda side: (lambda out: out[P + side + 'Leg'].translation + Vector((0, -0.04, 0.05))))(s)
        grip = h['pos']
        h['pos'] = (lambda g, k, w: (lambda out: k(out).lerp(g(out), w)))(grip, knee, hug)
        h['curl'] = lerp(0.15, 0.5, hug)
    sit = S._pose(p)
    sit = {n: M @ m for n, m in sit.items()}
    # ---- blend supine -> sit track in basis (local rotation) space
    sv = B.values_from_pose(sit)
    vals = {}
    head_bones = (P + 'Neck', P + 'Head', P + 'HeadTop_End')
    for n in B.order:
        w = wh if n in head_bones else wb
        qa = Quaternion(ctx.sup_vals[n]['q'])
        qb = Quaternion(sv[n]['q'])
        if qa.dot(qb) < 0:
            qb.negate()
        q = qa.slerp(qb, w)
        loc = None
        if ctx.sup_vals[n]['loc'] is not None:
            loc = tuple(vlerp(ctx.sup_vals[n]['loc'], sv[n]['loc'], wb))
        vals[n] = {'q': tuple(q), 'loc': loc}
    out = B.pose_from_values(vals)
    # ---- procedural head layers (world axes of the posed head)
    face, up, left = _head_axes(B, out)
    hp = out[P + 'Head'].translation.copy()
    nk = out[P + 'Neck'].translation.copy()
    # flop: the head falls forward past the sit pose and bounces
    B.rotate_subtree(out, 'Neck', R(left, -42 * fl), nk)
    # stir: groggy head roll on the floor
    B.rotate_subtree(out, 'Head', R(face, 14 * stir), hp)
    # dazed shake: 3 decaying shakes (yaw + roll), within the 25 deg per half-frame limit
    if se > 0:
        ph = 2 * math.pi * 3 * (t - 0.80) / 0.35
        face, up, left = _head_axes(B, out)
        B.rotate_subtree(out, 'Head', R(up, 22 * se * math.sin(ph)) @ R(face, 9 * se * math.sin(ph + 0.6)), hp)
    # wince: head tilts into the rubbing hand (his right), shoulders hunch handled below
    if wince > 0:
        face, up, left = _head_axes(B, out)
        B.rotate_subtree(out, 'Head', R(face, -10 * wince) @ R(left, -6 * wince), hp)
    # ---- legs: drop and bend right after the hold; feet slide up to the butt on the floor
    for s, sgn in SIDES:
        tgt_sit = sit[P + s + 'Foot']
        if kn < 1:
            lie = ctx.sup_foot[s].copy()
            flat = tgt_sit.copy()
            k = smooth(kn)
            pos = ctx.sup_ankle[s].lerp(tgt_sit.translation, k)
            pos.z = max(pos.z, tgt_sit.translation.z)
            q = lie.to_quaternion().slerp(flat.to_quaternion(), k)
            fm = q.to_matrix().to_4x4()
            fm.translation = pos
        else:
            fm = tgt_sit.copy()
        pole_lie = Vector((sgn * 0.1, 0.0, 1.0))
        pole_sit = M.to_3x3() @ Vector(p.feet[s][2])
        pole = pole_lie.lerp(pole_sit, wb).normalized()
        info = S.leg[s] if wb > 0.5 else ctx.leg_sup[s]
        B.solve_chain2(out, info, fm.translation, fm, pole)
    # ---- arms
    face, up, left = _head_axes(B, out)
    for s, sgn in SIDES:
        tgt, q, pole = None, None, None
        hip = out[P + 'Hips'].translation
        if push > 0:
            # palms flat on the floor beside/behind the hips, fingers forward
            fwd = Vector((face.x, face.y, 0)).normalized() if face.xy.length > 1e-3 else Vector((0, -1, 0))
            side = Vector((-fwd.y, fwd.x, 0)) * (-1)     # his left in the floor plane
            tp = hip + side * (sgn * 0.27) - fwd * 0.10
            tp.z = 0.045
            qp = hand_q(s, fwd, (0, 0, -1))
            tgt, tgt_full, q_full, kik = tp, tp, qp, smooth(push)
            pole = (side * sgn + Vector((0, 0, -0.3)) - fwd * 0.6).normalized()
        if s == 'Right' and rub > 0:
            ang = 2 * math.pi * 4.0 * (t - 1.2)
            right = -left
            tr_ = (hp + up * 0.24 - face * 0.03 + right * 0.15 +
                   (up * math.cos(ang) + face * math.sin(ang)) * 0.025 * min(1, 2 * rub))
            qr = hand_q(s, up * 0.85 - face * 0.3, -right)
            tgt, tgt_full, q_full, kik = tr_, tr_, qr, smooth(rub)
            pole = (right * 1.0 - up * 0.3 - face * 0.2).normalized()
        if tgt is not None:
            ik = dict(out)
            B.solve_chain2(ik, S.arm[s], tgt_full, B.hand_matrix(s, q_full, tgt_full), pole)
            B.blend_subtree(out, ik, s + 'Arm', kik)
    # ---- floor fit: the seat rests on the floor (never below), feet re-planted
    pts = B.mesh_points(out)
    dz = 0.0
    low = float(pts[:, 2].min())
    seat = S._butt_low(pts)
    target = FLOOR_GAP
    if wb > 0:
        dz = (target - seat) * smooth(min(1, wb * 3))
    dz = max(dz, -low + 0.0002)
    if abs(dz) > 1e-7:
        Mz = Matrix.Translation((0, 0, dz))
        feet = {s: out[P + s + 'Foot'].copy() for s, _ in SIDES}
        for n in out:
            out[n] = Mz @ out[n]
        if wb > 0.3:
            for s, sgn in SIDES:
                info = S.leg[s]
                B.solve_chain2(out, info, feet[s].translation, feet[s],
                              (M.to_3x3() @ Vector(p.feet[s][2])).normalized())
    # ---- the wall stops the scoot (hood contact)
    pts = B.mesh_points(out)
    exw = (C.WALL_X + 0.0015) - float(pts[:, 0].min())
    if exw > 0:
        Mx = Matrix.Translation((exw, 0, 0))
        for n in out:
            out[n] = Mx @ out[n]
    # fade the residual difference to the contract during the last frames (exact landing)
    wend = smoother((t - 2.25) / 0.15)
    if wend > 0:
        for n in out:
            a, b = out[n], ctx.contract[n]
            qa, qb = a.to_quaternion(), b.to_quaternion()
            m = qa.slerp(qb, wend).to_matrix().to_4x4()
            m.translation = a.translation.lerp(b.translation, wend)
            out[n] = m
    return out, {'dz': dz, 'wall_push': max(0.0, exw), 'min_z': low}


def _situp_canonical(ctx, N):
    v = sit_contract_values(ctx)
    return {1.0: ctx.B.supine_values, float(N + 1): v}


CLIPS = {
    'Cargo_Sit_Idle': {'T': SIT_T, 'loop': True, 'stage': 'cargo',
                       'setup': SitCtx, 'pose': sit_idle_pose, 'canonical': _sit_canonical,
                       'beats': ['0.0-0.6 shallow fast breathing and trembling',
                                 '0.6-0.75 SNAP glance at the doors (his right), shoulders jolt up',
                                 '0.75-1.45 holds the stare, trembles more, shrinks back against the wall',
                                 '1.45-1.7 slow reluctant turn back', '1.7-2.2 GULP: chin tuck, head dip, shoulders up/down, arms squeeze',
                                 '2.2-2.9 two small anxious rocks on the butt', '2.9-3.1 double-take at the doors (30 then 55 deg) with a hold',
                                 '3.1-3.6 turns back and sinks lower behind the knees', '3.6-4.5 settles into frame 1']},
    'Cargo_Knock': {'T': KNOCK_T, 'loop': True, 'stage': 'cargo',
                    'setup': KnockCtx, 'pose': knock_pose, 'canonical': _knock_canonical,
                    'post': _knock_post,
                    'beats': ['0.0-0.2 anticipation: squashes down, head snaps toward the wall over his right shoulder',
                              '0.2-0.53 releases the knees and swivels ~80 deg right on the butt; knees fall into a side-sit; chest twists to ~150 deg',
                              '0.53-1.15 alternating hammer-fists L R L R with body bounce and head shake',
                              '1.15-1.53 both fists rise (anticipation) and SLAM together, short hold on the wall',
                              '1.53-2.27 palms flat on the wall, cheek pressed to it, listening, frozen with a tiny tremble',
                              '2.27-2.87 deflates and swivels back, legs come back up', '2.87-3.3 sad sigh into the exact knee hug']},
    'SitUp_Cargo': {'T': SITUP_T, 'loop': False, 'stage': 'cargo',
                    'setup': SitUpCtx, 'pose': situp_pose, 'canonical': _situp_canonical,
                    'beats': ['0.0-0.13 exact supine hold (GetUp_FromBack_v02 frame 1) for the ragdoll blend',
                              '0.13-0.40 groggy stir: head rolls, the legs drop and bend, feet slide to the butt',
                              '0.40-0.80 heavy sit-up pushing on the floor; the giant head lags, then flops forward',
                              '0.80-1.15 dazed brrr head shake (3 decaying shakes)',
                              '1.15-1.50 rubs the bump on the back of the head, wincing, head tilts into the hand',
                              '1.50-1.70 hand freezes, slow look up, SNAP panic glance at the doors',
                              '1.70-2.10 scramble: turns 90 deg left and scoots 0.3 m to the wall in two heel pushes; hood bumps the wall',
                              '2.10-2.40 curls into the knee hug, landing exactly on the cargo sit contract']},
}
