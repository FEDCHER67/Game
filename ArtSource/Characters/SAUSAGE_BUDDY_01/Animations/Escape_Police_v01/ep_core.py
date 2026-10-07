"""Shared authoring core for the Escape_Police_v01 package (Sausage Buddy, VOLUNTEERS ONLY).

Built on top of Idle_Knock_v03/acting_core.py (imported, not copied): rig loading from the A v04
.blend or, without Git LFS, from Idle_Knock_v03/rig_Buddy_Mixamo65_A_v04.json; FK deltas; roll-
preserving two-bone IK; finger curl; Hermite curves; exact-seam keying; FBX export settings.

This module adds a whole-body poser (`Body.pose`) that takes:
  hips  : world position of the Hips joint and a world rotation about it (relative to Idle frame 1)
  J     : FK deltas for any bone (short Mixamo name -> Quaternion; base world axes, carried by the
          parent, i.e. read "relative to the parent")
  legs  : per side a foot matrix (IK) or None (the leg then follows J, FK)
  arms  : per side (wrist target, hand rotation relative to the Idle hand, pole) or None (FK)
  toes, curl : toe bend and finger curl per side
plus foot/hand contact helpers and the moving ground frame used by the in-place locomotion clips.

Conventions (same as the rest of the Buddy pipeline): 30 fps, metres, +Z up, the character faces
-Y, his left is +X. Rotation helpers: R(X, +) leans an upward bone forward (and swings a hanging
arm backward); R(Y, +) tips an upward bone toward his left; R(Z, +) turns him to his left.
In-place locomotion: the ground slides toward +Y at the clip's ground speed; every planted contact
(sole pivot, knee, palm) moves with that ground exactly, so nothing slides relative to the floor.
"""
from pathlib import Path
import sys, math, json
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ANIM = HERE.parent
CORE_DIR = ANIM / 'Idle_Knock_v03'
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import acting_core as C
from acting_core import R, QI, Curve, P, clamp, smooth, smoother, rot_about, pnoise

X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
SIDES = ('Left', 'Right')
SGN = {'Left': 1.0, 'Right': -1.0}
FPS = C.FPS
VAN_FLOOR = 0.55          # van cargo floor above the street (m)
CARGO_LIMIT = 1.2         # mesh height limit above the van floor (m)

# Idle frame-1 sole pivots on the floor (measured on the A v04 Outfit sole; z = 0)
HEEL_Y, BALL_Y, TOE_Y = 0.105, -0.100, -0.205
DEFAULT_SPLAY = 0.12      # knee hinge splay (knees point slightly outward)
PALM_H = 0.032            # wrist height above the floor for a flat palm (GetUp_v03 measurement)


def lerp(a, b, u):
    return a + (b - a) * u


def vlerp(a, b, u):
    return Vector(a).lerp(Vector(b), u)


def ease_io(u):
    return smooth(u)


def win(t, a, b):
    """0 before a, 1 after b, smoothstep between."""
    return smooth((t - a) / (b - a)) if b > a else float(t >= a)


def bump(t, a, m, b):
    """0 outside [a, b], smooth rise to 1 at m and back to 0."""
    if t <= a or t >= b:
        return 0.0
    return smooth((t - a) / (m - a)) if t < m else smooth((b - t) / (b - m))


def eul(pitch=0.0, roll=0.0, yaw=0.0):
    """Character-frame rotation: yaw (Z) @ pitch (X) @ roll (Y), degrees."""
    return R(Z, yaw) @ R(X, pitch) @ R(Y, roll)


def hermite(p0, v0, p1, v1, T, u):
    """Cubic Hermite between p0 and p1 over a segment of length T (velocities per second)."""
    u2, u3 = u * u, u * u * u
    return ((2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * T * v0 +
            (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * T * v1)


class Ground:
    """Ground displacement G(t) toward +Y (integral of the ground speed curve)."""

    def __init__(self, speed, T, dt=1 / 600):
        self.speed = speed
        n = int(math.ceil(T / dt)) + 2
        self.ts = [i * dt for i in range(n)]
        g, acc = [0.0], 0.0
        for i in range(1, n):
            acc += 0.5 * (speed(self.ts[i - 1]) + speed(self.ts[i])) * dt
            g.append(acc)
        self.g = g

    def __call__(self, t):
        return float(np.interp(t, self.ts, self.g))


class Body:
    """Whole-body poser on the Idle frame-1 base pose."""

    def __init__(self, B):
        self.B = B
        self.base = base = B.idle
        self.leg = {s: self.chain_info(base, 'leg', s, (0, -1, 0)) for s in SIDES}
        self.arm = {s: self.chain_info(base, 'arm', s, (0, 1, 0)) for s in SIDES}
        self.hips0 = base[P + 'Hips'].translation.copy()
        self.F0 = {s: base[P + s + 'Foot'].copy() for s in SIDES}
        self.H0 = {s: base[P + s + 'Hand'].to_3x3() for s in SIDES}
        fx = {s: base[P + s + 'Foot'].translation.x for s in SIDES}
        self.pivot0 = {s: {'heel': Vector((fx[s], HEEL_Y, 0.0)),
                           'ball': Vector((base[P + s + 'ToeBase'].translation.x, BALL_Y, 0.0)),
                           'toe': Vector((base[P + s + 'ToeBase'].translation.x, TOE_Y, 0.0)),
                           'mtp': base[P + s + 'ToeBase'].translation.copy(),      # toe hinge (ball joint)
                           'ankle': base[P + s + 'Foot'].translation.copy()} for s in SIDES}
        self.mtp_h = base[P + 'LeftToeBase'].translation.z
        self.Lleg = self.leg['Left']['l1'] + self.leg['Left']['l2']
        self.Larm = self.arm['Left']['l1'] + self.arm['Left']['l2']

    # -- hinge IK ----------------------------------------------------------------------------
    @staticmethod
    def chain_info(base, kind, side, pole0):
        """Base data for hinge IK. The bend plane is described by its normal (the hinge axis), so
        the bone roll stays defined whatever the limb direction (a pole-projection frame flips
        when the shin points along the pole, e.g. a heel kicked up behind a running cop)."""
        names = [P + side + n for n in (('UpLeg', 'Leg', 'Foot') if kind == 'leg' else ('Arm', 'ForeArm', 'Hand'))]
        a, b, c = names
        H, K, E = base[a].translation, base[b].translation, base[c].translation
        line = (E - H).normalized()
        off = (K - H) - line * (K - H).dot(line)
        if off.length > 1e-4:          # bent base chain (the Idle arms): its own bend plane
            n0 = line.cross(off.normalized()).normalized()
        else:                          # straight base chain (the Idle legs): the default splayed knee hinge,
            h = Vector((-1.0, -SGN[side] * DEFAULT_SPLAY, 0.0))     # so Body.pose reproduces Idle exactly
            n0 = (h - line * h.dot(line)).normalized()
        return {'names': names, 'l1': (K - H).length, 'l2': (E - K).length, 'n0': n0,
                'F_up': C.frame_from(K - H, n0), 'F_lo': C.frame_from(E - K, n0),
                'R_up': base[a].to_3x3(), 'R_lo': base[b].to_3x3()}

    def solve(self, out, info, target, end_matrix, hinge):
        """Place the upper/lower bones in the plane normal to `hinge` (the joint bends toward
        hinge x line) and the end bone subtree at end_matrix's rotation. Returns the overreach."""
        a, b, c = info['names']
        H = out[a].translation.copy()
        T = Vector(target)
        l1, l2 = info['l1'], info['l2']
        d = T - H
        dist = d.length
        line = d / dist
        h = Vector(hinge)
        h = (h - line * h.dot(line))
        if h.length < 1e-6:
            raise ValueError('hinge parallel to the limb line')
        h.normalize()
        pp = h.cross(line)
        dc = min(l1 + l2, max(abs(l1 - l2) + 1e-6, dist))
        along = (l1 * l1 - l2 * l2 + dc * dc) / (2 * dc)
        bend = math.sqrt(max(0.0, l1 * l1 - along * along))
        K = H + line * along + pp * bend
        E_ = H + line * dc
        Fu = C.frame_from(K - H, h)
        Fl = C.frame_from(E_ - K, h)
        mu = (Fu @ info['F_up'].transposed() @ info['R_up']).to_4x4(); mu.translation = H
        ml = (Fl @ info['F_lo'].transposed() @ info['R_lo']).to_4x4(); ml.translation = K
        out[a], out[b] = mu, ml
        me = end_matrix.copy(); me.translation = E_
        delta = me @ out[c].inverted()
        for n in self.B.subtree(c[len(P):]):
            out[n] = delta @ out[n]
        return max(0.0, dist - (l1 + l2))

    @staticmethod
    def hinge_from_pole(H, T, pole):
        line = (Vector(T) - Vector(H)).normalized()
        pp = Vector(pole) - line * Vector(pole).dot(line)
        return line.cross(pp.normalized())

    def leg_hinge(self, hrot, side, splay=None):
        """Default knee hinge: the pelvis' right-to-left axis, splayed so the knees point a little out."""
        splay = DEFAULT_SPLAY if splay is None else splay
        return hrot @ Vector((-1.0, -SGN[side] * splay, 0.0)).normalized()

    # -- contacts --------------------------------------------------------------------------
    def foot(self, side, pos, rot=None, pivot='ball'):
        """Foot matrix with the Idle foot rotated by `rot` (world, about the pivot) and the
        pivot point (heel/ball/toe on the sole, or the ankle) moved to `pos`."""
        rot = rot or QI()
        p0 = self.pivot0[side][pivot]
        return Matrix.Translation(Vector(pos)) @ rot.to_matrix().to_4x4() @ Matrix.Translation(-p0) @ self.F0[side]

    def foot_flat(self, side, gx, gy, yaw=0.0, lift=0.0):
        """Flat foot whose ball sits at ground point (gx, gy) (+ lift), yawed (deg) about the ball."""
        return self.foot(side, (gx, gy, lift), R(Z, yaw), 'ball')

    def hand_rot(self, side, q):
        """Hand armature rotation = q applied to the Idle hand orientation."""
        return q.to_matrix() @ self.H0[side]

    # -- whole body ------------------------------------------------------------------------
    def pose(self, hips, hrot=None, J=None, legs=None, arms=None, toes=None, curl=None, splay=0.12, post=None):
        """legs[s]: foot matrix, or (foot matrix, hinge axis); arms[s]: (wrist target, hand rotation
        relative to Idle, pole) or (target, rotation, None, hinge). post(out) runs after the IK."""
        q = dict(J or {})
        q['Hips'] = hrot or QI()
        root = Matrix.Translation(Vector(hips) - self.hips0)
        out, D = self.B.fk(self.base, q, root)
        info = {'leg_over': 0.0, 'arm_over': 0.0}
        hr = q['Hips']
        for s, M in (legs or {}).items():
            if M is None:
                continue
            hinge = None
            if isinstance(M, tuple):
                M, hinge = M
            if hinge is None:
                hinge = self.leg_hinge(hr, s, splay)
            info['leg_over'] = max(info['leg_over'], self.solve(out, self.leg[s], M.translation, M, hinge))
        for s, a in (toes or {}).items():
            if abs(a) > 1e-9:
                ax = out[P + s + 'Foot'].to_3x3() @ self.F0[s].to_3x3().inverted() @ Vector(X)
                self.B.rotate_subtree(out, s + 'ToeBase', R(ax, -a))
        for s, a in (arms or {}).items():
            if a is None:
                continue
            target, hq, pole = a[:3]
            hinge = a[3] if len(a) > 3 else None
            if hinge is None:
                hinge = self.hinge_from_pole(out[P + s + 'Arm'].translation, target, pole)
            hm = self.hand_rot(s, hq).to_4x4()
            hm.translation = Vector(target)
            info['arm_over'] = max(info['arm_over'], self.solve(out, self.arm[s], target, hm, hinge))
        for s, c in (curl or {}).items():
            if c is None:
                continue
            amt, thumb, per = (tuple(c) + (None, None))[:3] if isinstance(c, (tuple, list)) else (c, None, None)
            self.B.curl(out, s, amt, thumb=thumb, per=per)
        if post:
            post(out)
        info['hips'] = tuple(out[P + 'Hips'].translation)
        return out, info

    # -- measurements ----------------------------------------------------------------------
    def bone(self, out, short):
        return out[P + short].translation.copy()

    def sole_low(self, out, side):
        return self.B.sole_low(out, side)


# ----------------------------------------------------------------------------- run gait
class RunLeg:
    """Foot path of one leg in an in-place run.

    Phase u in [0, 1): touchdown at u = 0, stance to u = c, swing to 1. During the stance the
    sole pivots ride the ground (+Y at speed v): a short heel-first landing (rotation about the
    heel), a flat foot, then a heel peel about the ball with the toes kept flat. The swing is a
    Hermite arc whose end velocities match the ground (no velocity pop at lift-off/touchdown)."""

    def __init__(self, body, side, T, v, c, y_td, x_off=0.0, lift=0.25, lift_peak=0.4, td_pitch=-10.0,
                 peel_from=0.45, peel_pitch=38.0, swing_pitch_peak=55.0, toe_yaw=0.0, land_flat=0.18):
        self.b, self.s = body, side
        self.T, self.v, self.c = T, v, c
        self.y_td, self.x_off = y_td, x_off
        self.lift, self.lift_peak = lift, lift_peak
        self.td_pitch, self.peel_from, self.peel_pitch = td_pitch, peel_from, peel_pitch
        self.swing_pitch_peak, self.yaw, self.land_flat = swing_pitch_peak, toe_yaw, land_flat
        self.heel_ball = HEEL_Y - body.pivot0[side]['mtp'].y

    def flat(self, gy):
        """Flat foot, yawed, with its heel point at ground y = gy."""
        h0 = self.b.pivot0[self.s]['heel']
        return Matrix.Translation((self.x_off, gy - h0.y, 0.0)) @ rot_about(h0, R(Z, self.yaw)) @ self.b.F0[self.s]

    def point(self, M, name):
        return M @ (self.b.F0[self.s].inverted() @ self.b.pivot0[self.s][name])

    def stance(self, u):
        """(foot matrix, toe bend) during stance, u in [0, c]."""
        s = u / self.c
        gy = self.y_td + self.v * self.T * u          # heel ground point, riding the ground
        M = self.flat(gy)
        lat = R(Z, self.yaw) @ Vector(X)
        if s < self.land_flat:                         # heel landing -> slap flat, rotation about the heel
            a = self.td_pitch * (1 - smooth(s / self.land_flat))
            return rot_about(self.point(M, 'heel'), R(lat, a)) @ M, 0.0
        if s < self.peel_from:
            return M, 0.0
        k = (s - self.peel_from) / (1 - self.peel_from)
        a = self.peel_pitch * (k * k * (3 - 2 * k) * 0.35 + k * 0.65)
        # heel peel about the toe hinge: the toes stay flat and fixed on the ground
        return rot_about(self.point(M, 'mtp'), R(lat, a)) @ M, a

    def __call__(self, u):
        u %= 1.0
        if u <= self.c:
            return self.stance(u)
        M0, toe0 = self.stance(self.c)
        M1, _ = self.stance(0.0)
        s = (u - self.c) / (1 - self.c)
        Ts = self.T * (1 - self.c)
        p0, p1 = M0.translation, M1.translation
        v0 = Vector((0, self.v, 0.9))
        v1 = Vector((0, self.v * 0.25, -1.1))
        p = Vector([hermite(p0[i], v0[i], p1[i], v1[i], Ts, s) for i in range(3)])
        # extra lift: heel kicks up behind, then the knee drives the foot forward
        lp = self.lift_peak
        lift = self.lift * (smooth(s / lp) if s < lp else (1 - smooth((s - lp) / (1 - lp))) ** 1.4)
        p.z += lift
        # foot pitch through the swing: toe-off pitch -> plantar flexed peak -> toes up for landing
        a0 = self.peel_pitch
        pk = self.swing_pitch_peak
        if s < 0.3:
            a = lerp(a0, pk, smooth(s / 0.3))
        elif s < 0.8:
            a = lerp(pk, self.td_pitch - 6, smooth((s - 0.3) / 0.5))
        else:
            a = lerp(self.td_pitch - 6, self.td_pitch, smooth((s - 0.8) / 0.2))
        toe = toe0 * (1 - smooth(s / 0.35))
        rot = R(Z, self.yaw) @ R(X, a)
        M = rot.to_matrix().to_4x4() @ self.b.F0[self.s].to_3x3().to_4x4()
        M.translation = p
        return M, toe


# ----------------------------------------------------------------------------- review stage
def treadmill(scene, col, spacing=0.25, width=4.0, length=14.0, z=0.0, name='Tread', colors=((200, 202, 207), (160, 163, 170))):
    """Striped floor (review only). Returns the object; move .location.y to show the ground motion."""
    mats = []
    for i, c in enumerate(colors):
        m = bpy.data.materials.new('%s_%d' % (name, i))
        m.diffuse_color = C.srgb(c)
        try:
            m.use_nodes = True
            b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
            b.inputs['Base Color'].default_value = C.srgb(c)
            b.inputs['Roughness'].default_value = 0.9
        except Exception:
            pass
        mats.append(m)
    verts, faces, mi = [], [], []
    n = int(length / spacing)
    for k in range(n):
        y0 = -length / 2 + k * spacing
        b = len(verts)
        verts += [(-width / 2, y0, z), (width / 2, y0, z), (width / 2, y0 + spacing, z), (-width / 2, y0 + spacing, z)]
        faces.append((b, b + 1, b + 2, b + 3))
        mi.append(k % 2)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for m in mats:
        me.materials.append(m)
    for p, i in zip(me.polygons, mi):
        p.material_index = i
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    return o


def box(col, name, lo, hi, rgb):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], f)
    m = bpy.data.materials.new(name)
    m.diffuse_color = C.srgb(rgb)
    me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    return o


def setup_engine(scene, res, engine='WORKBENCH'):
    if engine == 'WORKBENCH':
        scene.render.engine = 'BLENDER_WORKBENCH'
        sh = scene.display.shading
        sh.light = 'STUDIO'
        sh.color_type = 'MATERIAL'
        sh.show_shadows = True
        sh.show_cavity = False
        scene.display.shadow_focus = 0.4
        scene.render.resolution_x = scene.render.resolution_y = res
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = 'PNG'
        scene.view_settings.view_transform = 'Standard'
    else:
        C.use_eevee(scene, (res, res), samples=16)


# ----------------------------------------------------------------------------- standing helper
def K(*keys):
    """Non-periodic curve; keys (t, v) or (t, v, tangent). Ends are flat."""
    return Curve(list(keys))


class Chan:
    """A bag of named curves evaluated together: ch = Chan(a=K(...), b=K(...)); v = ch(t) -> dict."""

    def __init__(self, **curves):
        self.c = curves

    def __call__(self, t):
        return _Vals({k: f(t) for k, f in self.c.items()})


class _Vals(dict):
    def __getattr__(self, k):
        return self.get(k, 0.0)


def stand(body, hx, hy, hrot, J, drop=0.0, support=1.0, feet=None, free=(), arms=None, curl=None, toes=None,
          splay=0.12, post=None):
    """Standing pose with feet planted on matrices (default: the exact Idle frame-1 feet).
    The pelvis height is solved so the most extended supporting leg reaches support * leg length
    (1 = straight, as in Idle frame 1), then lowered by `drop`. Legs listed in `free` do not
    support (lifted feet)."""
    feet = dict(feet or {})
    for s in SIDES:
        feet.setdefault(s, body.F0[s])
    q = dict(J)
    q['Hips'] = hrot
    out, _ = body.B.fk(body.base, q, Matrix.Translation((hx, hy, 0.0)))
    dz = 1e9
    for s in SIDES:
        if s in free:
            continue
        v = out[P + s + 'UpLeg'].translation - feet[s].translation
        r = support * body.Lleg
        dz = min(dz, math.sqrt(max(r * r - v.x * v.x - v.y * v.y, 0.0)) - v.z)
    if dz > 1e8:
        dz = 0.0
    hips = body.hips0 + Vector((hx, hy, dz - drop))
    out, info = body.pose(hips, hrot, J, legs=feet, arms=arms, curl=curl, toes=toes, splay=splay, post=post)
    info['dz'] = dz - drop
    return out, info


def idle_canonical(ctx, frames, N):
    v = ctx.B.idle_values
    return {1.0: v, float(N + 1): v}


def contract_error(a, b):
    return max(abs(a[n][r][c] - b[n][r][c]) for n in a for r in range(4) for c in range(4))


def step_arc(p0, p1, t, t0, t1, lift=0.08, pitch=0.0):
    """Foot step from matrix p0 to p1 between t0 and t1 (ease in/out, lift arc, toe-down pitch mid-air)."""
    if t <= t0:
        return p0, False
    if t >= t1:
        return p1, False
    u = (t - t0) / (t1 - t0)
    e = smoother(u)
    pos = p0.translation.lerp(p1.translation, e)
    pos.z += lift * math.sin(math.pi * u) ** 1.2
    q0 = p0.to_quaternion()
    q1 = p1.to_quaternion()
    if q0.dot(q1) < 0:
        q1.negate()
    q = q0.slerp(q1, e)
    if pitch:
        q = R(X, pitch * math.sin(math.pi * u)) @ q
    M = q.to_matrix().to_4x4()
    M.translation = pos
    return M, True


def arm(J, s, fwd=0.0, out=0.0, swing=0.0, twist=0.0, elbow=0.0, wrist=0.0, wdev=0.0, sh_up=0.0, sh_fwd=0.0, fa_twist=0.0):
    """FK arm deltas (degrees). fwd: raise forward (negative = back); out: abduction; swing: across
    the body (horizontal plane, + = inward); twist: about the upper arm (+ = elbow out / internal-
    external mix, check renders); elbow: flexion; wrist: hand flexion (+ = palm side); sh_up / sh_fwd:
    clavicle shrug / protraction (the shrug is counter-rotated on the arm, as Idle_Knock gotcha 2)."""
    sg = SGN[s]
    J[s + 'Shoulder'] = R(Z, -sg * sh_fwd) @ R(Y, -sg * sh_up)
    J[s + 'Arm'] = R(Z, -sg * swing) @ R(X, -fwd) @ R(Y, -sg * (out - 0.8 * sh_up)) @ R(Z, sg * twist)
    J[s + 'ForeArm'] = R(X, -elbow) @ R(Z, sg * fa_twist)
    J[s + 'Hand'] = R(X, -wrist) @ R(Y, -sg * wdev)


def spine(J, pitch=0.0, roll=0.0, yaw=0.0, w=(0.3, 0.35, 0.35)):
    """Distribute a total upper-body bend over Spine/Spine1/Spine2 (pitch + forward, roll + to his left, yaw + left)."""
    for n, k in zip(('Spine', 'Spine1', 'Spine2'), w):
        J[n] = R(Z, yaw * k) @ R(X, pitch * k) @ R(Y, roll * k)


def head(J, pitch=0.0, roll=0.0, yaw=0.0, neck=0.4):
    J['Neck'] = R(Z, yaw * neck) @ R(X, pitch * neck) @ R(Y, roll * neck)
    J['Head'] = R(Z, yaw * (1 - neck)) @ R(X, pitch * (1 - neck)) @ R(Y, roll * (1 - neck))


def blend_subtree(B, out, other, short, w):
    """Blend the local (parent-relative) transforms of a subtree from `out` toward `other` by w,
    recomposing hierarchically so joints stay connected."""
    names = B.subtree(short)
    if w <= 0:
        return
    newm = {}
    for n in names:
        p = B.parent[n]
        Pa = out[p] if p not in newm else newm[p]
        la = out[p].inverted() @ out[n]
        lb = other[p].inverted() @ other[n]
        qa, qb = la.to_quaternion(), lb.to_quaternion()
        if qa.dot(qb) < 0:
            qb.negate()
        q = qa.slerp(qb, w)
        tvec = la.translation.lerp(lb.translation, w)
        m = q.to_matrix().to_4x4()
        m.translation = tvec
        newm[n] = Pa @ m
    out.update(newm)


class Path3:
    """Keyed IK path: keys (t, offset xyz, hand rotation Quaternion, pole xyz). Offsets and poles use
    monotone Hermite curves per component; rotations slerp between keys with smoothstep timing."""

    def __init__(self, keys):
        self.keys = keys
        self.ts = [k[0] for k in keys]
        self.off = [Curve([(k[0], k[1][i]) for k in keys]) for i in range(3)]
        # the bend plane is interpolated as a hinge axis (key offset x key pole), which stays smooth
        # when the wrist sweeps close to the shoulder (a pole there is nearly parallel to the limb)
        hs = []
        for k in keys:
            if k[3][0] == 'h':                 # ('h', x, y, z): the hinge axis given directly
                h = Vector(k[3][1:]).normalized()
            else:
                line = Vector(k[1]).normalized()
                pp = Vector(k[3]) - line * Vector(k[3]).dot(line)
                h = line.cross(pp.normalized())
            if hs and h.dot(hs[-1]) < 0:
                h = -h
            hs.append(h)
        self.hinge = [Curve([(k[0], h[i]) for k, h in zip(keys, hs)]) for i in range(3)]

    def __call__(self, t):
        off = Vector([c(t) for c in self.off])
        pole = Vector([c(t) for c in self.hinge]).normalized()
        ks = self.keys
        if t <= ks[0][0]:
            q = ks[0][2]
        elif t >= ks[-1][0]:
            q = ks[-1][2]
        else:
            i = max(j for j in range(len(ks)) if ks[j][0] <= t)
            u = smooth((t - ks[i][0]) / (ks[i + 1][0] - ks[i][0]))
            a, b = ks[i][2].copy(), ks[i + 1][2].copy()
            if a.dot(b) < 0:
                b.negate()
            q = a.slerp(b, u)
        return off, q, pole


def ik_arm_post(body, side, path, t, weight, anchor='Arm', frame=False):
    """Post hook: solve the arm to `anchor bone head + offset` and blend it in by `weight`.
    anchor 'Arm' means the side's upper arm; any other name is a full short bone name. With
    frame=True the offset and hand rotation ride the anchor bone's rotation (relative to Idle)."""
    def post(out):
        if weight <= 1e-9:
            return
        off, q, pole = path(t)
        an = P + side + anchor if anchor == 'Arm' else P + anchor
        if frame:
            Ra = (out[an].to_3x3() @ body.base[an].to_3x3().inverted()).to_quaternion()
            off, q, pole = Ra @ off, Ra @ q, Ra @ pole
        target = out[an].translation + off
        ik = dict(out)
        hm = body.hand_rot(side, q).to_4x4()
        hm.translation = target
        hinge = pole                       # Path3 returns the interpolated hinge axis
        body.solve(ik, body.arm[side], target, hm, hinge)
        blend_subtree(body.B, out, ik, side + 'Arm', weight)
    return post


def blend_pose(B, A, Bp, w):
    """Whole-pose blend: Hips world transform slerp/lerp, all other bones parent-relative."""
    out = {}
    for n in B.order:
        p = B.parent[n]
        la = A[n] if p is None else A[p].inverted() @ A[n]
        lb = Bp[n] if p is None else Bp[p].inverted() @ Bp[n]
        qa, qb = la.to_quaternion(), lb.to_quaternion()
        if qa.dot(qb) < 0:
            qb.negate()
        m = qa.slerp(qb, w).to_matrix().to_4x4()
        m.translation = la.translation.lerp(lb.translation, w)
        out[n] = m if p is None else out[p] @ m
    return out


def rigid_blend(body, A, Bp, k, kr, lift=0.0, limbs=True, kr_feet=None, k_root=None, k_feet=None, lift_feet=None,
                swing_feet=False, feet_local=False, floor_guard=None, kr_root=None, knee_path=None, kr_bones=None):
    """World-space blend of two poses that stays a valid rig pose (keys store rotations only, so a
    plain per-bone lerp would stretch bones). Hips: lerp/slerp; every other bone: the world
    rotation is slerped, its head is placed by its parent (rest offset). Then, optionally, each limb
    is re-solved by hinge IK so the hands and feet follow the world-blended end matrices (the bend
    plane from the world-blended elbow / knee). k: translation weight, kr: rotation weight."""
    Bk = body.B
    feet = set(Bk.subtree('LeftFoot')) | set(Bk.subtree('RightFoot')) if (kr_feet is not None or k_feet is not None) else set()
    kr_feet = kr if kr_feet is None else kr_feet
    blend = {}
    for n in Bk.order:
        a, b = A[n], Bp[n]
        qa, qb = a.to_quaternion(), b.to_quaternion()
        if qa.dot(qb) < 0:
            qb.negate()
        w = kr_feet if n in feet else (kr_root if (kr_root is not None and Bk.parent[n] is None) else kr)
        if kr_bones and n in kr_bones:
            w = kr_bones[n]
        m = qa.slerp(qb, w).to_matrix().to_4x4()
        kt = k_root if (k_root is not None and Bk.parent[n] is None) else (k_feet if (k_feet is not None and n in feet) else k)
        m.translation = a.translation.lerp(b.translation, kt) + Vector((0, 0, lift if (lift_feet is None or n not in feet) else lift_feet))
        blend[n] = m
    out = {}
    for n in Bk.order:
        p = Bk.parent[n]
        if p is None:
            out[n] = blend[n]
            continue
        off = (body.base[p].inverted() @ body.base[n]).translation
        m = blend[n].to_3x3().to_4x4()
        m.translation = out[p] @ off
        out[n] = m
    if limbs:
        def hinge_of(P, chain):
            r, mid, e = chain['names']
            H, Km, T = P[r].translation, P[mid].translation, P[e].translation
            line = (T - H).normalized()
            perp = (Km - H) - line * (Km - H).dot(line)
            return line.cross(perp.normalized()) if perp.length > 1e-6 else None
        for s in SIDES:
            for chain in ((body.leg[s], body.arm[s]) if limbs == 'all' else (body.leg[s],)):
                r, mid, e = chain['names']
                ha, hb = hinge_of(A, chain), hinge_of(Bp, chain)
                if ha is None or hb is None:
                    continue
                # (both hinges already point the bend side by construction: never flip one)
                h = ha.slerp(hb, kr) if hasattr(ha, 'slerp') else ha.lerp(hb, kr)          # the bend plane turns smoothly from one pose to the other
                if h.length < 1e-6:
                    continue
                tgt = blend[e].translation
                if knee_path is not None and chain is body.leg[s]:
                    # bend plane through an explicit knee path (world lerp of the two knees + a bump)
                    Kt = A[mid].translation.lerp(Bp[mid].translation, knee_path[0]) + Vector(knee_path[1])
                    Hc = out[r].translation
                    ln = (tgt - Hc).normalized()
                    pv = (Kt - Hc) - ln * (Kt - Hc).dot(ln)
                    if pv.length > 1e-4:
                        h = ln.cross(pv.normalized())
                if swing_feet and chain is body.leg[s]:
                    # knee direction interpolated as a rotation about the hip-ankle line, through the
                    # outside (the knee falls outward), never through a hinge parallel to the line
                    def kdir(P):
                        H_, K_, A_ = (P[x].translation for x in (r, mid, e))
                        ln = (A_ - H_).normalized()
                        v = (K_ - H_) - ln * (K_ - H_).dot(ln)
                        return v.normalized()
                    ln = (tgt - out[r].translation).normalized()
                    pa, pb = kdir(A), kdir(Bp)
                    pa = (pa - ln * pa.dot(ln)).normalized()
                    pb = (pb - ln * pb.dot(ln)).normalized()
                    outward = (out[P + 'Hips'].to_3x3() @ body.base[P + 'Hips'].to_3x3().inverted()) @ Vector((SGN[s], 0, 0))
                    ang = math.atan2(ln.dot(pa.cross(pb)), pa.dot(pb))
                    mid_dir = (Quaternion(ln, ang / 2) @ pa)
                    if mid_dir.dot(outward) < 0:          # take the other way round, through the outside
                        ang = ang - math.copysign(2 * math.pi, ang)
                    pp = Quaternion(ln, ang * kr) @ pa
                    h = ln.cross(pp)
                if swing_feet:   # the ankle swings round the hip (direction slerp, reach lerp, plus the lift)
                    kk = k_feet if k_feet is not None else k
                    da = A[e].translation - A[r].translation
                    db = Bp[e].translation - Bp[r].translation
                    d = QI().slerp(da.rotation_difference(db), kk) @ da.normalized() * lerp(da.length, db.length, kk)
                    tgt = out[r].translation + d + Vector((0, 0, lift_feet or 0.0))
                body.solve(out, chain, tgt, blend[e], h.normalized())
                if feet_local and chain is body.leg[s]:
                    # the foot turns relative to the shin (ankle flexion), not in world space
                    la = A[mid].inverted() @ A[e]
                    lb = Bp[mid].inverted() @ Bp[e]
                    qa, qb = la.to_quaternion(), lb.to_quaternion()
                    if qa.dot(qb) < 0:
                        qb.negate()
                    rot = out[mid].to_3x3() @ qa.slerp(qb, kr_feet).to_matrix()
                    m = rot.to_4x4()
                    m.translation = out[e].translation
                    delta = m @ out[e].inverted()
                    for n in Bk.subtree(e[len(P):]):
                        out[n] = delta @ out[n]
                if floor_guard is not None and chain is body.leg[s]:
                    # keep the shoe (rigid sole vertices) above the floor: raise the ankle target
                    for _ in range(3):
                        low = Bk.sole_low(out, s)
                        if low >= floor_guard:
                            break
                        tgt = tgt + Vector((0, 0, floor_guard - low))
                        body.solve(out, chain, tgt, out[e], h.normalized())
    return out
