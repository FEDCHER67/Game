"""Authoring framework for the Sausage Buddy get-ups, revision v03.

Read-only inputs: ../../SAUSAGE_BUDDY_A_v04.blend and ../../buddy_rig.py (imported, never modified).
Nothing here writes outside this folder; Python byte-code writing is disabled.

Conventions (Blender, character rest frame): +X = character's left, +Y = back, +Z = up, metres, 30 fps.
Joint rotations are LOCAL rotations expressed in the rest-frame axes of the parent (so a "bend" means
the same thing whether the character stands or lies), applied on top of the Idle frame-1 pose. With every
offset at zero and the limb targets at their Idle values the builder reproduces Idle frame 1.
"""
from pathlib import Path
import sys, math
sys.dont_write_bytecode = True
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
import buddy_rig as RG  # noqa: E402  (read-only helper: ordered(), key_frames(), fcurves_of())

P = 'mixamorig:'
FPS = 30
SIDES = (('Left', 1.0), ('Right', -1.0))


# ----------------------------------------------------------------------------------------------- maths
def R(axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg))


def RX(d):
    return R((1, 0, 0), d)


def RY(d):
    return R((0, 1, 0), d)


def RZ(d):
    return R((0, 0, 1), d)


def eul(bend=0.0, side=0.0, twist=0.0):
    """bend +: forward flexion; side +: toward the character's left; twist +: turn to the character's left."""
    return RX(bend) @ RY(side) @ RZ(twist)


def smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def smoother(u):
    u = max(0.0, min(1.0, u))
    return u * u * u * (u * (6 * u - 15) + 10)


def window(f, f0, f1, attack=3.0, decay=4.0):
    """C1 envelope: 0 outside [f0, f1], smooth rise over `attack` frames and fall over `decay` frames."""
    if f <= f0 or f >= f1:
        return 0.0
    return min(smooth((f - f0) / max(attack, 1e-6)), smooth((f1 - f) / max(decay, 1e-6)))


def vec(v):
    return Vector((float(v[0]), float(v[1]), float(v[2])))


# ----------------------------------------------------------------------------------------------- curves
class Track:
    """Monotone cubic Hermite curve through keys (frame, value[, tension]).

    Values are floats or 3/4-tuples (interpolated per component). Interior tangents use the
    Fritsch-Butland harmonic mean, so the curve never overshoots its keys; local extrema and the
    first/last keys get zero tangents (eases). Tension 1 forces an ease at that key; 0 keeps the
    automatic tangent. Overshoot and anticipation are therefore always authored explicitly.
    """

    def __init__(self, keys):
        keys = sorted(keys, key=lambda k: k[0])
        xs = [float(k[0]) for k in keys]
        for a, b in zip(xs, xs[1:]):
            assert b > a, ('duplicate key frame', xs)
        self.x = np.array(xs)
        vals = [k[1] for k in keys]
        self.dim = len(vals[0]) if isinstance(vals[0], (tuple, list, Vector)) else 0
        self.y = np.array([[float(c) for c in v] if self.dim else [float(v)] for v in vals])
        ten = np.array([float(k[2]) if len(k) > 2 else 0.0 for k in keys])
        n = len(xs)
        m = np.zeros_like(self.y)
        if n > 1:
            h = np.diff(self.x)
            d = np.diff(self.y, axis=0) / h[:, None]
            for k in range(1, n - 1):
                d0, d1 = d[k - 1], d[k]
                w1 = 2 * h[k] + h[k - 1]
                w2 = h[k] + 2 * h[k - 1]
                same = (d0 * d1) > 0
                with np.errstate(divide='ignore', invalid='ignore'):
                    hm = (w1 + w2) / (w1 / d0 + w2 / d1)
                m[k] = np.where(same, hm, 0.0) * (1.0 - ten[k])
        self.m = m

    def __call__(self, f):
        x = self.x
        if f <= x[0]:
            v = self.y[0]
        elif f >= x[-1]:
            v = self.y[-1]
        else:
            k = int(np.searchsorted(x, f, side='right') - 1)
            h = x[k + 1] - x[k]
            u = (f - x[k]) / h
            h00 = 2 * u ** 3 - 3 * u ** 2 + 1
            h10 = u ** 3 - 2 * u ** 2 + u
            h01 = -2 * u ** 3 + 3 * u ** 2
            h11 = u ** 3 - u ** 2
            v = h00 * self.y[k] + h10 * h * self.m[k] + h01 * self.y[k + 1] + h11 * h * self.m[k + 1]
        return tuple(float(c) for c in v) if self.dim else float(v[0])


class QTrack:
    """Quaternion keys (frame, Quaternion[, tension]); timing from a monotone progress curve, slerp between."""

    def __init__(self, keys):
        keys = sorted(keys, key=lambda k: k[0])
        qs = []
        for k in keys:
            q = k[1].normalized()
            if qs and qs[-1].dot(q) < 0:
                q = -q
            qs.append(q)
        self.q = qs
        self.prog = Track([(k[0], float(i)) + ((k[2],) if len(k) > 2 else ()) for i, k in enumerate(keys)])

    def __call__(self, f):
        s = self.prog(f)
        i = max(0, min(len(self.q) - 2, int(math.floor(s)))) if len(self.q) > 1 else 0
        if len(self.q) == 1:
            return self.q[0].copy()
        return self.q[i].slerp(self.q[i + 1], max(0.0, min(1.0, s - i)))


class Step:
    """Piecewise-constant channel (e.g. which body region is grounded)."""

    def __init__(self, keys):
        self.keys = sorted(keys, key=lambda k: k[0])

    def __call__(self, f):
        v = self.keys[0][1]
        for k in self.keys:
            if f >= k[0]:
                v = k[1]
        return v


# ----------------------------------------------------------------------------------------------- rig context
REGION_OF = {}
for _n in ('Hips', 'Spine', 'Spine1', 'Spine2', 'Neck', 'Head', 'HeadTop_End', 'LeftShoulder', 'RightShoulder'):
    REGION_OF[P + _n] = 'torso'
for _s, _t in (('Left', 'L'), ('Right', 'R')):
    REGION_OF[P + _s + 'Arm'] = 'arm' + _t
    REGION_OF[P + _s + 'ForeArm'] = 'arm' + _t
    REGION_OF[P + _s + 'Hand'] = 'hand' + _t
    for _f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky'):
        for _i in range(1, 5):
            REGION_OF[P + _s + 'Hand' + _f + str(_i)] = 'hand' + _t
    REGION_OF[P + _s + 'UpLeg'] = 'leg' + _t
    REGION_OF[P + _s + 'Leg'] = 'leg' + _t
    REGION_OF[P + _s + 'Foot'] = 'foot' + _t
    REGION_OF[P + _s + 'ToeBase'] = 'foot' + _t
    REGION_OF[P + _s + 'Toe_End'] = 'foot' + _t
REGIONS = ('torso', 'armL', 'armR', 'handL', 'handR', 'legL', 'legR', 'footL', 'footR')


class Rig:
    """Opens the read-only A v04 source, records rest/Idle data, strips every action (one clip per file)."""

    def __init__(self):
        import os
        # Without Git LFS: rebuild_rig_from_json_v03.py --with-proxy --idle-action, then point this at it.
        source = os.environ.get('GETUP_SOURCE_BLEND') or str(SRC / 'SAUSAGE_BUDDY_A_v04.blend')
        self.source = source
        bpy.ops.wm.open_mainfile(filepath=source)
        self.scene = bpy.context.scene
        self.rig = rig = bpy.data.objects['Buddy_Rig_Mixamo65']
        self.meshes = [bpy.data.objects[n] for n in ('Body', 'Face', 'Outfit')]
        rig.animation_data.action = bpy.data.actions['Idle']
        self.scene.frame_set(1)
        self.idle = {b.name: b.matrix.copy() for b in rig.pose.bones}
        self.rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        self.order = RG.ordered(rig)
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
        self.children = {n: [c.name for c in rig.data.bones[n].children] for n in self.order}
        self.hr = {n: m.translation.copy() for n, m in self.rest.items()}
        # Build order: legs before the spine, so hands may be targeted at a solved knee.
        legs = [n for n in self.order if n.startswith((P + 'LeftUpLeg', P + 'LeftLeg', P + 'LeftFoot', P + 'LeftToe',
                                                         P + 'RightUpLeg', P + 'RightLeg', P + 'RightFoot', P + 'RightToe'))]
        self.build_order = [P + 'Hips'] + legs + [n for n in self.order if n != P + 'Hips' and n not in legs]
        assert len(self.build_order) == len(self.order) == 65
        rig.animation_data_clear()
        for o in self.meshes:
            if o.data.shape_keys:
                o.data.shape_keys.animation_data_clear()
                for k in o.data.shape_keys.key_blocks:
                    k.value = 0.0
        for act in list(bpy.data.actions):
            bpy.data.actions.remove(act)
        for pb in rig.pose.bones:
            pb.matrix_basis.identity()
            pb.rotation_mode = 'QUATERNION'
        rig.data.pose_position = 'POSE'
        self.scene.render.fps = FPS
        bpy.context.view_layer.update()
        # Idle frame 1 in the local rest-axis parameterisation.
        self.idle_T = {n: self.idle[n] @ self.rest[n].inverted() for n in self.order}
        self.idle_W = {n: self.idle_T[n].to_quaternion().normalized() for n in self.order}
        self.idle_local = {}
        for n in self.order:
            p = self.parent[n]
            q = self.idle_W[n] if p is None else self.idle_W[p].inverted() @ self.idle_W[n]
            self.idle_local[n] = q.normalized()
        self.idle_hips = self.idle_T[P + 'Hips'] @ self.hr[P + 'Hips']
        self._mesh_tables()

    # -------------------------------------------------------------------------------- mesh tables
    def _mesh_tables(self):
        """Per-vertex dominant region, rigid hand/shoe vertex sets for exact contact heights."""
        self.vregion = {}
        self.vbone = {}
        self.hand_pts = {'Left': [], 'Right': []}
        self.shoe_pts = {'Left': [], 'Right': []}
        for o in self.meshes:
            names = [g.name for g in o.vertex_groups]
            reg = np.empty(len(o.data.vertices), dtype=object)
            dom = np.empty(len(o.data.vertices), dtype=object)
            for v in o.data.vertices:
                best, bw = None, -1.0
                acc = {}
                for g in v.groups:
                    bn = names[g.group]
                    acc[bn] = acc.get(bn, 0.0) + g.weight
                    if g.weight > bw:
                        best, bw = bn, g.weight
                reg[v.index] = REGION_OF.get(best, 'torso')
                dom[v.index] = best
                co = o.matrix_world @ v.co
                for side in ('Left', 'Right'):
                    hand_w = sum(w for bn, w in acc.items() if bn.startswith(P + side + 'Hand'))
                    if hand_w >= 0.95:
                        self.hand_pts[side].append(co - self.hr[P + side + 'Hand'])
                    if o.name == 'Outfit':
                        foot_w = acc.get(P + side + 'Foot', 0.0) + acc.get(P + side + 'ToeBase', 0.0)
                        if foot_w > 0.5 and co.z < 0.19:
                            self.shoe_pts[side].append(co - self.hr[P + side + 'Foot'])
            self.vregion[o.name] = reg
            self.vbone[o.name] = dom
        self.region_idx = {o.name: {r: np.nonzero(self.vregion[o.name] == r)[0] for r in REGIONS} for o in self.meshes}
        # Diagnostic contact parts (dominant bone): which body parts actually touch the floor.
        parts = {'butt': ('Hips', 'Spine'), 'upper_back_hood': ('Spine1', 'Spine2', 'Neck', 'LeftShoulder', 'RightShoulder'),
                 'head': ('Head', 'HeadTop_End')}
        self.part_idx = {o.name: {k: np.nonzero(np.isin(self.vbone[o.name].astype(str), [P + b for b in bs]))[0]
                                  for k, bs in parts.items()} for o in self.meshes}
        self.hand_np = {s: np.array([tuple(p) for p in pts]) for s, pts in self.hand_pts.items()}
        self.shoe_np = {s: np.array([tuple(p) for p in pts]) for s, pts in self.shoe_pts.items()}
        assert all(len(v) > 50 for v in self.hand_np.values()) and all(len(v) > 50 for v in self.shoe_np.values())

    def low_of(self, pts, q):
        M = np.array(q.to_matrix())
        return float((pts @ M.T)[:, 2].min())

    def hand_contact_z(self, side, Wq, lift=0.0):
        return -self.low_of(self.hand_np[side], Wq) + lift

    def foot_contact_z(self, side, Wq, lift=0.0):
        return -self.low_of(self.shoe_np[side], Wq) + lift

    # -------------------------------------------------------------------------------- posing
    def T_of(self, T, n, local_q, hips_pos=None):
        p = self.parent[n]
        if p is None:
            return Matrix.Translation(hips_pos) @ local_q.to_matrix().to_4x4() @ Matrix.Translation(-self.hr[n])
        h = self.hr[n]
        return T[p] @ Matrix.Translation(h) @ local_q.to_matrix().to_4x4() @ Matrix.Translation(-h)

    def two_bone(self, T, upper, lower, end, hinge, sgn, p_rest, target, pole, W_end, soft=0.0):
        """Hinge-plane IK in rest-frame terms; keeps each bone's rest roll. Returns (locals, info).
        soft > 0 (v03, arms): beyond (1 - soft) of the full reach the effective distance approaches the full
        reach exponentially, so the elbow never snaps straight/bent at the reach limit."""
        Wp = T[self.parent[upper]].to_quaternion()
        head = T[self.parent[upper]] @ self.hr[upper]
        a = self.hr[lower] - self.hr[upper]
        b = self.hr[end] - self.hr[lower]
        h = Vector(hinge).normalized()
        b_par = h * b.dot(h)
        b_perp = b - b_par
        c = h.cross(b_perp)
        ap = a + b_par
        A = 2 * ap.dot(b_perp)
        B = 2 * ap.dot(c)
        C = ap.length_squared + b_perp.length_squared
        dvec = Vector(target) - head
        d = dvec.length
        rho = math.hypot(A, B)
        if soft > 0:
            dmax = math.sqrt(C + rho)
            ds = (1 - soft) * dmax
            if d > ds:
                d = ds + (dmax - ds) * (1 - math.exp(-(d - ds) / (dmax - ds)))
        alpha = math.atan2(B, A)
        arg = (d * d - C) / rho
        clamped = arg > 1 or arg < -1
        arg = max(-1.0, min(1.0, arg))
        phi = alpha + sgn * math.acos(arg)
        v = ap + b_perp * math.cos(phi) + c * math.sin(phi)
        e1 = v.normalized()
        e2 = (Vector(p_rest) - e1 * Vector(p_rest).dot(e1)).normalized()
        e3 = e1.cross(e2)
        f1 = dvec.normalized()
        pw = Vector(pole)
        f2 = pw - f1 * pw.dot(f1)
        if f2.length < 1e-6:
            f2 = Vector((0, 0, 1)) - f1 * f1.z
        f2.normalize()
        f3 = f1.cross(f2)
        F = Matrix((f1, f2, f3)).transposed()
        E = Matrix((e1, e2, e3))
        W_up = (F @ E).to_quaternion().normalized()
        q_up = (Wp.inverted() @ W_up).normalized()
        q_lo = Quaternion(h, phi)
        W_lo = W_up @ q_lo
        q_end = (W_lo.inverted() @ W_end).normalized()
        return (q_up, q_lo, q_end), {'reach_clamped': clamped, 'bend_deg': math.degrees(sgn * phi), 'dist': d}

    def build(self, prm):
        """prm: evaluated channel values (see choreography). Returns (desired, T, info)."""
        loc = dict(self.idle_local)
        info = {}
        hp = vec(prm['hips_pos'])
        q_h = RZ(prm['hips_yaw']) @ RX(prm['hips_pitch']) @ RY(prm['hips_lean']) @ RZ(prm['hips_twist'])
        loc[P + 'Hips'] = (q_h @ self.idle_local[P + 'Hips']).normalized()
        sb, ss, st = prm['spine']
        cb, cs, ct = prm['chest']
        for n, w in (('Spine', .30), ('Spine1', .34), ('Spine2', .36)):
            extra = eul(cb, cs, ct) if n == 'Spine2' else Quaternion()
            loc[P + n] = (extra @ eul(sb * w, ss * w, st * w) @ self.idle_local[P + n]).normalized()
        loc[P + 'Neck'] = (eul(*prm['neck']) @ self.idle_local[P + 'Neck']).normalized()
        loc[P + 'Head'] = (eul(*prm['head']) @ self.idle_local[P + 'Head']).normalized()
        for side, s in SIDES:
            t = side[0]
            shrug, cfwd = prm['clav' + t]
            loc[P + side + 'Shoulder'] = (RY(-s * shrug) @ RZ(-s * cfwd) @ self.idle_local[P + side + 'Shoulder']).normalized()
        T = {}
        for n in self.build_order:
            short = n[len(P):]
            if short in ('LeftUpLeg', 'RightUpLeg'):
                side = short[:-5]
                t = side[0]
                Wf = prm['footQ' + t]
                fx, fy, fh = prm['foot' + t]
                target = Vector((fx, fy, self.foot_contact_z(side, Wf, fh)))
                (qu, ql, qe), inf = self.two_bone(T, n, P + side + 'Leg', P + side + 'Foot', (1, 0, 0), 1.0,
                                                  (0, -1, 0), target, prm['knee' + t], Wf)
                loc[n], loc[P + side + 'Leg'], loc[P + side + 'Foot'] = qu, ql, qe
                info['leg' + t] = inf
            if short in ('LeftArm', 'RightArm'):
                side = short[:-3]
                t = side[0]
                s = 1.0 if side == 'Left' else -1.0
                # FK: absolute swing parameterisation re-based on Idle (exact at the Idle parameters).
                fwd, out, tw = prm['arm' + t]
                F = RX(-fwd) @ RY(s * (90 - out)) @ RX(s * tw)
                F0 = RX(-4) @ RY(s * 74)
                fk_up = (F @ F0.inverted() @ self.idle_local[n]).normalized()
                fk_lo = (RZ(-s * (prm['elbow' + t] - 14.0)) @ self.idle_local[P + side + 'ForeArm']).normalized()
                fk_end = (eul(*prm['wrist' + t]) @ self.idle_local[P + side + 'Hand']).normalized()
                w = max(0.0, min(1.0, prm['ik' + t]))
                if w > 1e-6:
                    Wh = prm['handQ' + t]
                    hx, hy, hh = prm['hand' + t]
                    target = Vector((hx, hy, self.hand_contact_z(side, Wh, hh)))
                    kw = prm.get('handOnKnee' + t, 0.0)
                    if kw > 1e-6:
                        knee_side = prm['handKneeSide' + t]
                        kp = T[P + knee_side + 'Leg'] @ self.hr[P + knee_side + 'Leg']
                        target = target.lerp(kp + vec(prm['handKneeOff' + t]), kw)
                    (qu, ql, qe), inf = self.two_bone(T, n, P + side + 'ForeArm', P + side + 'Hand', (0, 0, 1), -s,
                                                      (0, 1, 0), target, prm['pole' + t], Wh, soft=ARM_SOFT)
                    info['arm' + t] = inf
                    loc[n] = fk_up.slerp(qu, w)
                    loc[P + side + 'ForeArm'] = fk_lo.slerp(ql, w)
                    loc[P + side + 'Hand'] = fk_end.slerp(qe, w)
                else:
                    loc[n], loc[P + side + 'ForeArm'], loc[P + side + 'Hand'] = fk_up, fk_lo, fk_end
            T[n] = self.T_of(T, n, loc[n], hp)
        desired = {n: T[n] @ self.rest[n] for n in self.order}
        return desired, T, info

    def idle_params(self):
        """Channel values that rebuild Idle frame 1 (limb targets measured from the Idle matrices)."""
        prm = dict(DEFAULTS)
        prm['hips_pos'] = tuple(self.idle_hips)
        for side, s in SIDES:
            t = side[0]
            ank = self.idle_T[P + side + 'Foot'] @ self.hr[P + side + 'Foot']
            Wf = self.idle_W[P + side + 'Foot']
            prm['foot' + t] = (ank.x, ank.y, ank.z - self.foot_contact_z(side, Wf, 0.0))
            prm['footQ' + t] = Wf.copy()
            prm['knee' + t] = tuple(self.idle_W[P + side + 'UpLeg'] @ Vector((0, -1, 0)))
            prm['handQ' + t] = self.idle_W[P + side + 'Hand'].copy()
        return prm

    # -------------------------------------------------------------------------------- evaluation
    def install(self, desired):
        rig = self.rig
        for n in self.order:
            pb = rig.pose.bones[n]
            p = self.parent[n]
            kw = {} if p is None else {'parent_matrix': desired[p], 'parent_matrix_local': self.rest[p]}
            pb.matrix_basis = pb.bone.convert_local_to_pose(desired[n], self.rest[n], invert=True, **kw)
        bpy.context.view_layer.update()

    def region_lows(self, desired):
        self.install(desired)
        dg = bpy.context.evaluated_depsgraph_get()
        lows = {r: 10.0 for r in REGIONS}
        for o in self.meshes:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            co = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get('co', co)
            ev.to_mesh_clear()
            co = co.reshape(-1, 3)
            M = np.array(o.matrix_world)
            z = co @ M[2, :3] + M[2, 3]
            for r, idx in self.region_idx[o.name].items():
                if len(idx):
                    lows[r] = min(lows[r], float(z[idx].min()))
            for r, idx in self.part_idx[o.name].items():
                if len(idx):
                    lows[r] = min(lows.get(r, 10.0), float(z[idx].min()))
        return lows


# ----------------------------------------------------------------------------------------------- choreography runtime
DEFAULTS = {
    'hips_pos': None, 'hips_pitch': 0.0, 'hips_lean': 0.0, 'hips_twist': 0.0, 'hips_yaw': 0.0,
    'spine': (0, 0, 0), 'chest': (0, 0, 0), 'neck': (0, 0, 0), 'head': (0, 0, 0),
    'clavL': (0, 0), 'clavR': (0, 0),
    'armL': (4, 16, 0), 'armR': (4, 16, 0), 'elbowL': 14.0, 'elbowR': 14.0,
    'wristL': (0, 0, 0), 'wristR': (0, 0, 0), 'ikL': 0.0, 'ikR': 0.0,
    'handL': (0.3, 0, 0), 'handR': (-0.3, 0, 0), 'poleL': (1, 0.3, 0), 'poleR': (-1, 0.3, 0),
    'handOnKneeL': 0.0, 'handOnKneeR': 0.0, 'handKneeSideL': 'Left', 'handKneeSideR': 'Right',
    'handKneeOffL': (0, 0, 0), 'handKneeOffR': (0, 0, 0),
    'ground': 0.0, 'ground_set': ('torso',),
    'plantL': 0.0, 'plantR': 0.0,
}
ARM_SOFT = 0.08  # soft-IK zone of the arms (fraction of full reach)
HAND_CLEAR = 0.001  # planted palms: lowest deformed hand vertex this far above z=0 (mesh-measured, v03 fix)

ADDITIVE_TUPLE = ('spine', 'chest', 'neck', 'head', 'clavL', 'clavR', 'armL', 'armR', 'wristL', 'wristR',
                  'hips_pos', 'footL', 'footR', 'handL', 'handR')


class Clip:
    """A performance: channel tracks + procedural additive layers, evaluated per (sub)frame."""

    def __init__(self, rig, name, frames, tracks, layers=()):
        self.rig, self.name, self.N = rig, name, frames
        self.tracks = tracks
        self.layers = list(layers)

    def params(self, f):
        prm = dict(DEFAULTS)
        for k, tr in self.tracks.items():
            prm[k] = tr(f)
        for layer in self.layers:
            for k, dv in layer(f).items():
                base = prm[k]
                if isinstance(base, Quaternion):
                    prm[k] = (dv @ base).normalized()
                elif isinstance(base, tuple):
                    prm[k] = tuple(a + b for a, b in zip(base, dv))
                else:
                    prm[k] = base + dv
        return prm

    def _with_z(self, prm, z):
        q = dict(prm)
        x, y, _ = prm['hips_pos']
        q['hips_pos'] = (x, y, z)
        return q

    def _plant_hands(self, prm, z):
        """Planted-hand clearance (v03 fix): the rigid-point contact height misses mixed-weight wrist/cuff
        vertices (7 mm under in the supine start), so for planted hands (plantL/plantR weight) the hand target
        height is corrected until the lowest DEFORMED hand vertex sits HAND_CLEAR above the floor."""
        sides = [t for t in 'LR' if prm.get('plant' + t, 0.0) > 1e-4 and prm['ik' + t] > 1e-4]
        if not sides:
            return prm
        full = dict(prm)
        for _ in range(5):
            d, _, _ = self.rig.build(self._with_z(full, z))
            lows = self.rig.region_lows(d)
            done = True
            for t in sides:
                err = HAND_CLEAR - lows['hand' + t]
                if abs(err) > 2e-5:
                    done = False
                    x, y, h = full['hand' + t]
                    full['hand' + t] = (x, y, h + err)
            if done:
                break
        prm = dict(prm)
        for t in sides:  # partial plant weight blends the correction (hand arriving / leaving)
            w = min(1.0, prm['plant' + t])
            x, y, h = prm['hand' + t]
            prm['hand' + t] = (x, y, h + w * (full['hand' + t][2] - h))
        return prm

    def solve(self, step=0.5, lift_regions=('torso', 'armL', 'armR', 'legL', 'legR'), radius_frames=2.0, log=None):
        """Sample every `step` frames. Hips height = authored, blended toward 'grounded' (named regions touch
        z=0 exactly) by the 'ground' weight, then lifted where any non-planted region would penetrate.
        The lift is max-filtered and blurred over +-radius so it never undercuts the need and never pops."""
        rig = self.rig
        n = int(round(self.N / step))
        fs = [i * step for i in range(n + 1)]
        base_z, lift = [], []
        prms = []
        for f in fs:
            prm = self.params(f)
            z0 = prm['hips_pos'][2]
            w = max(0.0, min(1.0, prm['ground']))
            z = z0
            if w > 1e-4:
                zg = z0
                for _ in range(8):
                    d, _, _ = rig.build(self._with_z(prm, zg))
                    lows = rig.region_lows(d)
                    low = min(lows[r] for r in prm['ground_set'])
                    zg -= low
                    if abs(low) < 1e-5:
                        break
                z = (1 - w) * z0 + w * zg
            prm = self._plant_hands(prm, z)
            lf = 0.0
            for _ in range(6):
                d, _, _ = rig.build(self._with_z(prm, z + lf))
                lows = rig.region_lows(d)
                low = min(lows[r] for r in lift_regions)
                if low >= -2e-5:
                    break
                lf += -low + 2e-5
            base_z.append(z)
            lift.append(lf)
            prms.append(prm)
        r = max(1, int(round(radius_frames / step)))
        mx = [max(lift[max(0, i - r):i + r + 1]) for i in range(len(lift))]
        kern = [r + 1 - abs(j) for j in range(-r, r + 1)]
        sm = []
        for i in range(len(mx)):
            acc = wsum = 0.0
            for j, k in zip(range(-r, r + 1), kern):
                ii = min(len(mx) - 1, max(0, i + j))
                acc += k * mx[ii]
                wsum += k
            sm.append(acc / wsum)
        poses, infos, finals = {}, {}, {}
        for f, prm, z, s in zip(fs, prms, base_z, sm):
            q = self._with_z(prm, z + s)
            d, _, inf = rig.build(q)
            poses[f], infos[f], finals[f] = d, inf, q
        self.fs, self.poses, self.infos, self.final_prm = fs, poses, infos, finals
        self.base_z, self.lift_raw, self.lift = base_z, lift, sm
        if log:
            log({'clip': self.name, 'max_lift_m': max(sm), 'lift_frames': [f for f, v in zip(fs, lift) if v > 1e-4]})
        return poses

    def key(self, action_name, exact_idle_end=True):
        """Key every half frame (LINEAR, as the existing pipeline). Last frame = exact Idle frame 1 matrices."""
        rig = self.rig
        frames = {}
        for f, d in self.poses.items():
            frames[1 + f] = d
        if exact_idle_end:
            frames[1 + self.N] = {n: m.copy() for n, m in rig.idle.items()}
        act = RG.key_frames(rig.rig, rig.rest, frames, action_name)
        act['authoring'] = 'Original keyframed performance (local-rotation FK + hinge-plane IK); no external motion'
        act['duration_seconds'] = self.N / FPS
        act['fps'] = FPS
        act['loop'] = False
        act['idle_reference'] = 'Original SAUSAGE_BUDDY_A_v04 Idle frame 1'
        rig.scene.frame_start = 1
        rig.scene.frame_end = self.N + 1
        rig.scene.frame_set(1)
        return act


# ----------------------------------------------------------------------------------------------- review renders
def review_setup(rig, res=320, engine='BLENDER_EEVEE'):
    import buddy_render as RD  # read-only helper (studio lights/floor/camera)
    col, cam, floor = RD.studio(rig.scene)
    sc = rig.scene
    try:
        sc.render.engine = engine
    except TypeError:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    if hasattr(sc, 'eevee') and hasattr(sc.eevee, 'taa_render_samples'):
        sc.eevee.taa_render_samples = 16
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    return cam


VIEWS = {'side': ((5.0, 0.0, 1.65), (0.0, 0.0, 0.85)), 'three_quarter': ((-3.7, -5.0, 2.65), (0.0, 0.0, 0.85))}


def render_frames(rig, cam, out_dir, frames, views=('side', 'three_quarter'), ortho=2.6, prefix='f'):
    out_dir = Path(out_dir)
    sc = rig.scene
    paths = []
    for view in views:
        loc, tgt = VIEWS[view]
        cam.location = loc
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
        for fr in frames:
            sc.frame_set(int(math.floor(fr)), subframe=fr - math.floor(fr))
            p = out_dir / view / ('%s%06.2f.png' % (prefix, fr))
            p.parent.mkdir(parents=True, exist_ok=True)
            sc.render.filepath = str(p)
            bpy.ops.render.render(write_still=True)
            paths.append(p)
    return paths
