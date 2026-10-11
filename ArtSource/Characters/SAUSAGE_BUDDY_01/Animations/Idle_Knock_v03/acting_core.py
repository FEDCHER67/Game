"""Authoring core for the Idle_Knock_v03 package (Sausage Buddy, VOLUNTEERS ONLY).

Original local keyframe/procedural animation. Inputs are opened read-only:
  SAUSAGE_BUDDY_A_v04.blend (rig, meshes, Idle frame 1) and
  Animations/GetUp_Idle_v01/GetUp_FromBack_v02.blend (supine first-frame contract).
Nothing outside Animations/Idle_Knock_v03 is written.

Conventions: character faces -Y, left = +X, +Z up, metres, 30 fps.
Pose = {bone name: armature-space 4x4 matrix} (same as the GPT packages).
FK deltas are rotations about each bone's head in the BASE pose's world axes,
carried by the parent's delta (so a delta reads "relative to the parent").
"""
from pathlib import Path
import sys, math, json, hashlib, bisect
sys.dont_write_bytecode = True
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion

P = 'mixamorig:'
HERE = Path(__file__).resolve().parent
ANIM = HERE.parent
CHAR = ANIM.parent
SRC_A = CHAR / 'SAUSAGE_BUDDY_A_v04.blend'
SRC_B = CHAR / 'SAUSAGE_BUDDY_B_v04.blend'
GETUP_BACK = ANIM / 'GetUp_Idle_v01' / 'GetUp_FromBack_v02.blend'
FPS = 30
WALL_X = -0.65          # cargo side wall plane (review geometry, x = const)
HEIGHT_LIMIT = 1.2      # cargo bay limit above the floor
RIG_NAME = 'Buddy_Rig_Mixamo65'
MESH_NAMES = ('Body', 'Face', 'Outfit')
FINGERS = ('Index', 'Middle', 'Ring', 'Pinky')


# ----------------------------------------------------------------------------- math helpers
def R(axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg))


def QI():
    return Quaternion((1.0, 0.0, 0.0, 0.0))


def rot_about(p, q):
    return Matrix.Translation(p) @ q.to_matrix().to_4x4() @ Matrix.Translation(-Vector(p))


def qpow(q, k):
    """Scale a rotation angle by k (shortest arc)."""
    return QI().slerp(q, k) if k != 0 else QI()


def chain(*qs):
    out = QI()
    for q in qs:
        out = out @ q
    return out


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


def smoother(u):
    u = clamp(u)
    return u * u * u * (u * (6 * u - 15) + 10)


def frame_from(y, ref):
    """Orthonormal 3x3 frame with +Y along y and +X toward ref (projected)."""
    y = y.normalized()
    x = ref - y * ref.dot(y)
    if x.length < 1e-8:
        raise ValueError('degenerate frame reference')
    x.normalize()
    z = x.cross(y).normalized()
    x = y.cross(z).normalized()
    return Matrix((x, y, z)).transposed()


# ----------------------------------------------------------------------------- animation curves
class Curve:
    """Piecewise cubic Hermite curve through keys.

    keys: list of (t, v) or (t, v, tan). tan is 'auto' (Steffen monotone, never overshoots
    between keys), 'flat' (zero slope = hold/ease), a number (explicit slope per second), or a
    pair (in, out) of those for broken tangents (impacts). periodic=True wraps neighbours so the
    curve is C1 across the loop seam; the first and last key must then share the same value.
    """

    def __init__(self, keys, periodic=False):
        ks = []
        for k in keys:
            t, v = float(k[0]), float(k[1])
            tan = k[2] if len(k) > 2 else 'auto'
            ks.append((t, v, tan))
        ks.sort(key=lambda k: k[0])
        self.t = [k[0] for k in ks]
        self.v = [k[1] for k in ks]
        self.periodic = periodic
        n = len(ks)
        if periodic:
            assert n >= 2 and abs(self.v[0] - self.v[-1]) < 1e-12, 'periodic curve needs equal end values'
            self.T = self.t[-1] - self.t[0]
        self.min_in, self.mout = [0.0] * n, [0.0] * n
        auto = [self._steffen(i) for i in range(n)]
        for i, (_, _, tan) in enumerate(ks):
            tin, tout = (tan if isinstance(tan, tuple) else (tan, tan))
            self.min_in[i] = self._slope(tin, auto[i], i, 'in')
            self.mout[i] = self._slope(tout, auto[i], i, 'out')
        if periodic:   # identical slope on both sides of the seam
            a = self.mout[0] if ks[0][2] != 'auto' else auto[0]
            self.mout[0] = self.min_in[-1] = a
            self.min_in[0] = self.mout[-1] = a

    def _slope(self, mode, auto, i, side):
        if mode == 'auto':
            return auto
        if mode == 'flat':
            return 0.0
        if mode == 'lin':   # continue the straight line of the adjacent segment
            j = i - 1 if side == 'in' else i + 1
            if 0 <= j < len(self.t):
                return (self.v[i] - self.v[j]) / (self.t[i] - self.t[j])
            return 0.0
        return float(mode)

    def _nb(self, i, d):
        n = len(self.t)
        j = i + d
        if 0 <= j < n:
            return self.t[j], self.v[j]
        if not self.periodic:
            return None
        if j < 0:      # wrap: key n-2 shifted one period earlier
            return self.t[n - 2] - self.T, self.v[n - 2]
        return self.t[1] + self.T, self.v[1]

    def _steffen(self, i):
        a, b = self._nb(i, -1), self._nb(i, +1)
        ti, vi = self.t[i], self.v[i]
        if a is None and b is None:
            return 0.0
        if a is None or b is None:
            return 0.0       # clamped (flat) at non-periodic ends
        h0, h1 = ti - a[0], b[0] - ti
        d0, d1 = (vi - a[1]) / h0, (b[1] - vi) / h1
        if d0 * d1 <= 0:
            return 0.0
        p = (d0 * h1 + d1 * h0) / (h0 + h1)
        return (math.copysign(1, d0) + math.copysign(1, d1)) * min(abs(d0), abs(d1), 0.5 * abs(p))

    def __call__(self, t):
        if self.periodic:
            t = self.t[0] + (t - self.t[0]) % self.T if not (self.t[0] <= t <= self.t[-1]) else t
        if t <= self.t[0]:
            return self.v[0]
        if t >= self.t[-1]:
            return self.v[-1]
        i = bisect.bisect_right(self.t, t) - 1
        t0, t1 = self.t[i], self.t[i + 1]
        h = t1 - t0
        u = (t - t0) / h
        v0, v1 = self.v[i], self.v[i + 1]
        m0, m1 = self.mout[i], self.min_in[i + 1]
        u2, u3 = u * u, u * u * u
        return ((2 * u3 - 3 * u2 + 1) * v0 + (u3 - 2 * u2 + u) * h * m0 +
                (-2 * u3 + 3 * u2) * v1 + (u3 - u2) * h * m1)


def const(v):
    return lambda t: v


def pnoise(T, seed, cycles=(1, 2, 3), amps=None):
    """Smooth periodic noise, exactly zero at t = 0 and t = T (integer cycles per loop)."""
    rng = np.random.default_rng(seed)
    phases = rng.uniform(0, 2 * math.pi, len(cycles))
    amps = amps or [1.0 / (1 + i) for i in range(len(cycles))]
    norm = sum(abs(a) for a in amps)

    def f(t):
        return sum(a * (math.sin(2 * math.pi * c * t / T + ph) - math.sin(ph))
                   for c, a, ph in zip(cycles, amps, phases)) / norm
    return f


def spring_periodic(drive, T, dt, freq, zeta, loops=6):
    """Periodic steady-state response y of y'' = w^2 (x - y) - 2 z w y' to a periodic drive x(t).
    Returns a function lag(t) = y - x shifted to be exactly zero at t = 0 (periodic, smooth)."""
    w = 2 * math.pi * freq
    n = int(round(T / dt))
    xs = [drive(i * dt) for i in range(n)]
    y, v = xs[0], 0.0
    ys = [0.0] * n
    for _ in range(loops):
        for i in range(n):
            x = xs[i]
            # semi-implicit Euler with sub-steps
            for _ in range(4):
                a = w * w * (x - y) - 2 * zeta * w * v
                v += a * dt / 4
                y += v * dt / 4
            ys[i] = y
    lag = [ys[i] - xs[i] for i in range(n)]
    lag0 = lag[0]
    lag = [l - lag0 for l in lag] + [0.0]
    ts = [i * dt for i in range(n + 1)]
    return lambda t: float(np.interp(t % T if t != T else T, ts, lag))


# ----------------------------------------------------------------------------- rig utilities
def fcurves_of(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        pass
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for slot in act.slots:
                cb = strip.channelbag(slot)
                if cb:
                    out += list(cb.fcurves)
    return out


def ordered_bones(rig):
    out = []

    def walk(b):
        out.append(b.name)
        for c in b.children:
            walk(c)
    for b in rig.data.bones:
        if b.parent is None:
            walk(b)
    return out


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_values(act, frame, bone_names):
    """Raw keyed values {bone: {'q': (w,x,y,z), 'loc': (x,y,z) or None}} at a frame."""
    fcs = fcurves_of(act)
    idx = {(fc.data_path, fc.array_index): fc for fc in fcs}
    out = {}
    for n in bone_names:
        qp = f'pose.bones["{n}"].rotation_quaternion'
        lp = f'pose.bones["{n}"].location'
        q = tuple(idx[(qp, c)].evaluate(frame) for c in range(4))
        loc = tuple(idx[(lp, c)].evaluate(frame) for c in range(3)) if (lp, 0) in idx else None
        out[n] = {'q': q, 'loc': loc}
    return out


RIG_JSON = HERE / 'rig_Buddy_Mixamo65_A_v04.json'


def is_real_blend(path):
    """True for plain, zstd- or gzip-compressed .blend files; False for Git LFS pointers / missing."""
    try:
        with open(path, 'rb') as f:
            head = f.read(7)
    except OSError:
        return False
    return head.startswith(b'BLENDER') or head.startswith(b'\x28\xb5\x2f\xfd') or head.startswith(b'\x1f\x8b')


def use_json_rig():
    """Cloud sessions without Git LFS see pointer files instead of .blend sources."""
    import os
    return os.environ.get('BUDDY_RIG_JSON') == '1' or not (is_real_blend(SRC_A) and is_real_blend(GETUP_BACK))


class Buddy:
    """Opens the read-only A v04 source (or its JSON export) and prepares a clean scene for one new action."""

    def __init__(self, keep_open=False):
        self.from_json = use_json_rig()
        if self.from_json:
            import rebuild_rig_from_json as RB
            rig, meshes, data = RB.build_scene(RIG_JSON)
            conv = lambda vals: {n: {'q': tuple(v['q']), 'loc': tuple(v['loc']) if v['loc'] else None}
                                 for n, v in vals.items()}
            self.supine_values = conv(data['contracts']['supine_frame1']['values'])
            idle_values = conv(data['contracts']['idle_frame1']['values'])
            names = ordered_bones(rig)
        else:
            bpy.ops.wm.open_mainfile(filepath=str(GETUP_BACK))
            rig = bpy.data.objects[RIG_NAME]
            names = ordered_bones(rig)
            self.supine_values = read_values(rig.animation_data.action, 1.0, names)
            bpy.ops.wm.open_mainfile(filepath=str(SRC_A))
            idle_values = None
        self.scene = bpy.context.scene
        self.rig = rig = bpy.data.objects[RIG_NAME]
        self.meshes = [bpy.data.objects[n] for n in MESH_NAMES]
        self.order = ordered_bones(rig)
        assert self.order == names
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
        self.children = {b.name: [c.name for c in b.children] for b in rig.data.bones}
        self.rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        self.idle_values = idle_values or read_values(bpy.data.actions['Idle'], 1.0, self.order)
        # clean scene: no actions, no shape-key animation, quaternion pose bones
        rig.animation_data_clear()
        for o in self.meshes:
            if o.data.shape_keys:
                o.data.shape_keys.animation_data_clear()
                for k in o.data.shape_keys.key_blocks:
                    k.value = 0.0
        for act in list(bpy.data.actions):
            bpy.data.actions.remove(act)
        for pb in rig.pose.bones:
            pb.rotation_mode = 'QUATERNION'
            pb.matrix_basis.identity()
        rig.data.pose_position = 'POSE'
        self.scene.render.fps = FPS
        self.idle = self.pose_from_values(self.idle_values)
        self.supine = self.pose_from_values(self.supine_values)
        self.sole = self._sole_vertices()

    # -- value <-> matrix conversion -------------------------------------------------------
    def pose_from_values(self, values):
        for n in self.order:
            pb = self.rig.pose.bones[n]
            pb.rotation_quaternion = Quaternion(values[n]['q'])
            pb.location = Vector(values[n]['loc']) if values[n]['loc'] else Vector()
            pb.scale = (1, 1, 1)
        bpy.context.view_layer.update()
        out = {pb.name: pb.matrix.copy() for pb in self.rig.pose.bones}
        for pb in self.rig.pose.bones:
            pb.matrix_basis.identity()
        bpy.context.view_layer.update()
        return out

    def values_from_pose(self, desired):
        vals = {}
        for n in self.order:
            b = self.rig.data.bones[n]
            p = self.parent[n]
            kw = {} if p is None else {'parent_matrix': desired[p], 'parent_matrix_local': self.rest[p]}
            basis = b.convert_local_to_pose(desired[n], self.rest[n], invert=True, **kw)
            q = basis.to_quaternion()
            vals[n] = {'q': tuple(q), 'loc': tuple(basis.translation) if p is None else None}
        return vals

    def install(self, desired):
        for n in self.order:
            pb = self.rig.pose.bones[n]
            p = self.parent[n]
            kw = {} if p is None else {'parent_matrix': desired[p], 'parent_matrix_local': self.rest[p]}
            pb.matrix_basis = pb.bone.convert_local_to_pose(desired[n], self.rest[n], invert=True, **kw)
        bpy.context.view_layer.update()

    def mesh_points(self, desired=None, names=MESH_NAMES):
        if desired is not None:
            self.install(desired)
        dg = bpy.context.evaluated_depsgraph_get()
        pts = []
        for n in names:
            o = bpy.data.objects[n]
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            a = np.empty(len(me.vertices) * 3, dtype=np.float64)
            me.vertices.foreach_get('co', a)
            m = np.array(o.matrix_world)
            pts.append(a.reshape(-1, 3) @ m[:3, :3].T + m[:3, 3])
            ev.to_mesh_clear()
        return np.concatenate(pts)

    def _sole_vertices(self):
        """Outfit shoe-sole vertices (same selection rule as the GPT validators)."""
        out = self.meshes[2]
        res = {}
        for s, sgn in (('Left', 1), ('Right', -1)):
            res[s] = [v.index for v in out.data.vertices if v.co.z < .19 and v.co.x * sgn > 0 and any(
                out.vertex_groups[g.group].name in (P + s + 'Foot', P + s + 'ToeBase') and g.weight > .5
                for g in v.groups)]
        return res

    # -- FK ----------------------------------------------------------------------------------
    def fk(self, base, q=None, root=None, cf=None):
        """desired[n] = D[n] @ base[n], D[n] = D[parent] @ rot_about(base head, q_n).
        q: {short bone name: Quaternion} in the character frame cf (default world axes).
        root: 4x4 world transform pre-applied to the root (Hips) delta."""
        q = q or {}
        cfq = cf if cf is not None else None
        D, out = {}, {}
        for n in self.order:
            p = self.parent[n]
            Dp = D[p] if p else (root.copy() if root is not None else Matrix.Identity(4))
            qn = q.get(n[len(P):])
            if qn is not None:
                if cfq is not None:
                    qn = cfq @ qn @ cfq.inverted()
                Dn = Dp @ rot_about(base[n].translation, qn)
            else:
                Dn = Dp
            D[n] = Dn
            out[n] = Dn @ base[n]
        return out, D

    def subtree(self, short):
        names = []

        def walk(n):
            names.append(n)
            for c in self.children[n]:
                walk(c)
        walk(P + short)
        return names

    def rotate_subtree(self, out, short, q, pivot=None):
        p = out[P + short].translation.copy() if pivot is None else Vector(pivot)
        M = rot_about(p, q)
        for n in self.subtree(short):
            out[n] = M @ out[n]

    def transform_subtree(self, out, short, M):
        for n in self.subtree(short):
            out[n] = M @ out[n]

    # -- IK ----------------------------------------------------------------------------------
    @staticmethod
    def two_bone(H, T, l1, l2, pole):
        d = T - H
        dist = d.length
        dirv = d / dist
        over = dist - (l1 + l2)
        # No epsilon at full reach: a straight base limb is reproduced exactly (bend = 0).
        dc = min(l1 + l2, max(abs(l1 - l2) + 1e-6, dist))
        along = (l1 * l1 - l2 * l2 + dc * dc) / (2 * dc)
        bend = math.sqrt(max(0.0, l1 * l1 - along * along))
        pp = pole - dirv * pole.dot(dirv)
        pp.normalize()
        K = H + dirv * along + pp * bend
        E = H + dirv * dc
        return K, E, max(0.0, over)

    def chain_info(self, base, kind, side, pole0):
        """Reference data for roll-preserving IK relative to a base pose."""
        names = [P + side + n for n in (('UpLeg', 'Leg', 'Foot') if kind == 'leg' else ('Arm', 'ForeArm', 'Hand'))]
        a, b, c = names
        H, K, E = base[a].translation, base[b].translation, base[c].translation
        l1, l2 = (K - H).length, (E - K).length
        pole0 = Vector(pole0)
        line = (E - H).normalized()
        off = (K - H) - line * (K - H).dot(line)
        if off.length > 1e-4:   # bent base chain: its own bend plane defines the pole
            pole0 = off.normalized()
        info = {'names': names, 'l1': l1, 'l2': l2, 'pole0': pole0.copy(),
                'F_up': frame_from(K - H, pole0), 'F_lo': frame_from(E - K, pole0),
                'R_up': base[a].to_3x3(), 'R_lo': base[b].to_3x3(), 'base_end': base[c].copy()}
        return info

    def solve_chain(self, out, info, target, end_matrix, pole, end_subtree_from=None):
        """Place upper/lower bones (roll preserved from base frames) and the end bone subtree.
        end_matrix: desired armature matrix of the end bone (its translation is replaced by the
        reached end point). Subtree children follow rigidly relative to their current pose."""
        a, b, c = info['names']
        H = out[a].translation.copy()
        K, E, over = self.two_bone(H, Vector(target), info['l1'], info['l2'], Vector(pole))
        Fu = frame_from(K - H, Vector(pole))
        Fl = frame_from(E - K, Vector(pole))
        Ru = Fu @ info['F_up'].transposed() @ info['R_up']
        Rl = Fl @ info['F_lo'].transposed() @ info['R_lo']
        mu = Ru.to_4x4(); mu.translation = H
        ml = Rl.to_4x4(); ml.translation = K
        out[a], out[b] = mu, ml
        me = end_matrix.copy(); me.translation = E
        delta = me @ out[c].inverted()
        for n in self.subtree(c[len(P):]):
            out[n] = delta @ out[n]
        return over

    # -- hands -------------------------------------------------------------------------------
    def hand_q(self, out, side):
        return (out[P + side + 'Hand'].to_3x3() @ self.rest[P + side + 'Hand'].to_3x3().inverted()).to_quaternion()

    def hand_matrix(self, side, q_world, pos):
        m = (q_world.to_matrix() @ self.rest[P + side + 'Hand'].to_3x3()).to_4x4()
        m.translation = Vector(pos)
        return m

    def curl(self, out, side, amount, thumb=None, spread=0.0, per=None):
        """Fold the mitten fingers toward the palm about the posed palm axis (GPT-verified axis)."""
        hq = self.hand_q(out, side)
        sgn = 1 if side == 'Left' else -1
        flex = hq @ Vector((0, 1, 0))
        per = per or {}
        for f in FINGERS:
            a = per.get(f, amount)
            if abs(a) < 1e-9 and not spread:
                continue
            for i, ang in ((1, 68), (2, 88), (3, 65)):
                self.rotate_subtree(out, side + 'Hand' + f + str(i), R(flex, sgn * ang * a))
        t = amount if thumb is None else thumb
        if abs(t) > 1e-9:
            self.rotate_subtree(out, side + 'HandThumb1', R(hq @ Vector((0, 0, 1)), sgn * 28 * t))
            self.rotate_subtree(out, side + 'HandThumb2', R(flex, sgn * 30 * t))

    # -- floor helpers ------------------------------------------------------------------------
    def sole_low(self, out, side):
        """Lowest shoe-sole vertex z for a foot placed rigidly (rest-space sole points)."""
        ft = P + side + 'Foot'
        W = out[ft] @ self.rest[ft].inverted()
        o = self.meshes[2]
        return min((W @ o.data.vertices[i].co).z for i in self.sole[side])

    # -- keying --------------------------------------------------------------------------------
    def key_action(self, name, frames, canonical=None):
        """frames: {frame (float): desired pose}; canonical: {frame: raw values} keyed exactly.
        Quaternion signs follow the canonical start for continuity. Linear interpolation."""
        rig = self.rig
        act = bpy.data.actions.new(name)
        rig.animation_data_create()
        rig.animation_data.action = act
        prev = {}
        sign_mismatch = []
        for f in sorted(frames):
            vals = canonical[f] if canonical and f in canonical else self.values_from_pose(frames[f])
            for n in self.order:
                pb = rig.pose.bones[n]
                q = Quaternion(vals[n]['q'])
                if n in prev and prev[n].dot(q) < 0:
                    if canonical and f in canonical:
                        sign_mismatch.append((f, n))
                    else:
                        q.negate()
                prev[n] = q.copy()
                pb.rotation_quaternion = q
                pb.keyframe_insert('rotation_quaternion', frame=f, group=n)
                if self.parent[n] is None:
                    pb.location = Vector(vals[n]['loc'])
                    pb.keyframe_insert('location', frame=f, group=n)
        for fc in fcurves_of(act):
            for k in fc.keyframe_points:
                k.interpolation = 'LINEAR'
        act.use_fake_user = True
        return act, sign_mismatch

    def export_fbx(self, action, fbx_path):
        rig = self.rig
        rig.animation_data.action = None
        for pb in rig.pose.bones:
            pb.matrix_basis.identity()
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, object_types={'ARMATURE'},
                                 add_leaf_bones=False, use_armature_deform_only=False, bake_anim=True,
                                 bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                                 bake_anim_step=.5, bake_anim_simplify_factor=0,
                                 axis_forward='-Z', axis_up='Y', apply_unit_scale=True,
                                 use_mesh_modifiers=False)
        rig.animation_data.action = action
        self.scene.frame_set(1)


# ----------------------------------------------------------------------------- render helpers
def srgb(rgb):
    def c(x):
        x = x / 255.0
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return (c(rgb[0]), c(rgb[1]), c(rgb[2]), 1.0)


def studio(scene, wall=False, wall_x=WALL_X):
    """Review studio matching the GPT/owner previews (not exported)."""
    col = bpy.data.collections.new('Studio_NOT_EXPORTED')
    scene.collection.children.link(col)
    world = bpy.data.worlds.new('Studio')
    scene.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs[0].default_value = srgb((196, 198, 204))
    bg.inputs[1].default_value = 1.0

    def light(name, loc, power, size, color=(1, 1, 1)):
        d = bpy.data.lights.new(name, 'AREA'); d.energy = power; d.shape = 'DISK'; d.size = size; d.color = color
        o = bpy.data.objects.new(name, d); o.location = loc
        o.rotation_euler = (Vector((0, 0, 1.0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        col.objects.link(o)
    light('Key', (-2.6, -3.4, 3.6), 700, 3.0, (1.0, 0.97, 0.93))
    light('Fill', (3.2, -2.6, 2.2), 300, 3.5, (0.93, 0.96, 1.0))
    light('Rim', (0.8, 3.6, 3.0), 420, 2.5)

    def mat(name, rgb, rough):
        m = bpy.data.materials.new(name)
        try:
            m.use_nodes = True
        except Exception:
            pass
        b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Base Color'].default_value = rgb
        b.inputs['Roughness'].default_value = rough
        return m
    me = bpy.data.meshes.new('Studio_Floor')
    me.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [], [(0, 1, 2, 3)])
    me.materials.append(mat('Studio_Floor', srgb((196, 198, 204)), 0.9))
    col.objects.link(bpy.data.objects.new('Studio_Floor', me))
    if wall:
        me = bpy.data.meshes.new('Cargo_Wall_Review')
        me.from_pydata([(wall_x, -1.6, 0), (wall_x, 1.6, 0), (wall_x, 1.6, 1.3), (wall_x, -1.6, 1.3)], [], [(0, 1, 2, 3)])
        me.materials.append(mat('Cargo_Wall_Review', (.14, .20, .25, 1), 0.8))
        col.objects.link(bpy.data.objects.new('Cargo_Wall_Review', me))
        # thin height-limit marker line (1.2 m) drawn on the wall for review
        me = bpy.data.meshes.new('Height_1p2_Marker')
        z = HEIGHT_LIMIT
        me.from_pydata([(wall_x + .002, -1.6, z - .004), (wall_x + .002, 1.6, z - .004), (wall_x + .002, 1.6, z + .004),
                        (wall_x + .002, -1.6, z + .004)], [], [(0, 1, 2, 3)])
        me.materials.append(mat('Height_Marker', (.8, .25, .05, 1), 0.6))
        col.objects.link(bpy.data.objects.new('Height_1p2_Marker', me))
    cd = bpy.data.cameras.new('Review_Cam')
    cam = bpy.data.objects.new('Review_Cam', cd)
    col.objects.link(cam)
    scene.camera = cam
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.exposure = -0.85 if not wall else -1.0
    return col, cam


def aim(cam, loc, target, ortho):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ortho


def use_eevee(scene, res, samples=16):
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    if hasattr(scene, 'eevee') and hasattr(scene.eevee, 'taa_render_samples'):
        scene.eevee.taa_render_samples = samples
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
