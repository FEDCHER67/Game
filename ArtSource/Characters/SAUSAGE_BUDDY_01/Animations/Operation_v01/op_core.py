"""Core for the Operation_v01 package: SAUSAGE_BUDDY_PATIENT_v01 animations on the operating table
TABLE-ASTRA-001 v02 (VOLUNTEERS ONLY). Blender 5.2, headless.

Reuses the authoring machinery of ../Idle_Knock_v03/acting_core.py (imported read-only: Curve,
pnoise, FK deltas, flip-free two-bone IK, finger curl, exact-seam keying, rotation-step limiter).

Frames
  * armature space (all authoring): the rig object sits at PatientRest = T(0, 0, 0.66) @ Rz(180)
    in table space, so the lying body has its head toward armature +Y, face toward +Z,
    patient's LEFT = armature +X. The pad top is at armature z ~ 0 (table z 0.646..0.664).
  * table space (Blender, RIG_Table_Root at the origin): head end -Y, patient's left = -X,
    floor z = 0. Unity prefab-local = (-x, z, -y) of table space; Unity root-local of a point given
    in armature space = (-x, z, -y) as well (PatientRest has Unity Euler (0, 180, 0)).
Nothing outside Animations/Operation_v01 is written.
"""
from pathlib import Path
import sys, math, json, hashlib
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ANIM = HERE.parent
ACTING = ANIM / 'Idle_Knock_v03'
if str(ACTING) not in sys.path:
    sys.path.insert(0, str(ACTING))
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
import acting_core as AC
from acting_core import R, QI, Curve, P, clamp, smooth, smoother, pnoise, fcurves_of, ordered_bones, read_values

REPO = ANIM.parents[3]
CHAR = ANIM.parent
PATIENT_BLEND = CHAR / 'Patient_v01' / 'SAUSAGE_BUDDY_PATIENT_v01.blend'
TABLE_DIR = REPO / 'ArtSource' / 'Props' / 'TABLE-ASTRA-001' / 'v02'
TABLE_BLEND = TABLE_DIR / 'TABLE-ASTRA-001_v02.blend'
TABLEREST_BLEND = TABLE_DIR / 'Patient_TableRest_v01.blend'
STAND_BLEND = TABLE_DIR / 'InstrumentStand_v01.blend'
STAND_AT = (0.57, 0.29, 0.0)      # TrayAnchor, table space (Unity (-0.57, 0, -0.29))
FPS = 30
RIG_NAME = 'Buddy_Rig_Mixamo65'
MESH_NAMES = ('Body', 'Face', 'Shorts')
PAD_Z = 0.66                      # PatientRest height (table space)
W_PR = Matrix.Translation((0, 0, PAD_Z)) @ Matrix.Rotation(math.pi, 4, 'Z')
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)
SIDES = (('Left', 1), ('Right', -1))
STRAP_NAMES = ('STRAP_ARM_L', 'STRAP_ARM_R', 'STRAP_LEG_L', 'STRAP_LEG_R', 'STRAP_TORSO')
STRAP_OPEN_DEG = 120.0
# closed strap centre lines (table y) -> armature y = -table y
STRAP_Y = {'arm': -0.045, 'leg': 0.62, 'torso': 0.055}

REGION_BONES = {
    'head': ('Neck', 'Head', 'HeadTop_End'),
    'chest': ('Spine1', 'Spine2', 'LeftShoulder', 'RightShoulder'),
    'pelvis': ('Hips', 'Spine'),
}
for _s, _ in SIDES:
    REGION_BONES['arm_' + _s] = tuple(_s + n for n in ('Arm', 'ForeArm', 'Hand')) + tuple(
        _s + 'Hand' + f + str(i) for f in ('Thumb', 'Index', 'Middle', 'Ring', 'Pinky') for i in range(1, 5))
    REGION_BONES['leg_' + _s] = tuple(_s + n for n in ('UpLeg', 'Leg', 'Foot', 'ToeBase', 'Toe_End'))
BONE_REGION = {P + b: r for r, bs in REGION_BONES.items() for b in bs}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def lerp(a, b, u):
    return a + (b - a) * u


def vlerp(a, b, u):
    return Vector(a).lerp(Vector(b), u)


def bump(t, t0, t1, ease_in=0.25, ease_out=0.35):
    """0 outside [t0, t1], 1 in the middle, smooth ramps (fractions of the window)."""
    if t <= t0 or t >= t1:
        return 0.0
    w = t1 - t0
    a, b = t0 + ease_in * w, t1 - ease_out * w
    if t < a:
        return smoother((t - t0) / max(1e-9, a - t0))
    if t > b:
        return smoother((t1 - t) / max(1e-9, t1 - b))
    return 1.0


def wrap(t, T):
    return t % T


def psin(t, T, cycles, phase=0.0):
    """Periodic sine with an integer number of cycles per loop T, zero at t=0 when phase=0."""
    return math.sin(2 * math.pi * cycles * t / T + phase) - math.sin(phase)


# ----------------------------------------------------------------------------- table stage
class Stage:
    """Table v02 geometry (review/validation only, never exported) and fast contact queries."""

    def __init__(self, straps_open=False, stand=True, coll_name='REVIEW_TABLE_v02_NOT_EXPORTED'):
        col = bpy.data.collections.new(coll_name)
        bpy.context.scene.collection.children.link(col)
        with bpy.data.libraries.load(str(TABLE_BLEND), link=False) as (src, dst):
            dst.collections = [c for c in src.collections if c in ('TABLE_ASTRA_Geometry', 'TABLE_ASTRA_Rig')]
        self.objs = {}
        for c in dst.collections:
            col.children.link(c)
            for o in c.all_objects:
                self.objs[o.name] = o
        if stand:
            with bpy.data.libraries.load(str(STAND_BLEND), link=False) as (src, dst):
                dst.collections = [c for c in src.collections if c.startswith('INSTRUMENT_STAND')]
            for c in dst.collections:
                col.children.link(c)
                for o in c.all_objects:
                    self.objs[o.name] = o
            root = self.objs['STAND_Root']
            root.location = STAND_AT
        self.collection = col
        self.strap_rest = {n: self.objs[n].matrix_basis.copy() for n in STRAP_NAMES}
        self.set_straps(straps_open)
        bpy.context.view_layer.update()
        self._height_field()

    def set_straps(self, open_):
        self.straps_open = open_
        for n in STRAP_NAMES:
            o = self.objs[n]
            o.matrix_basis = self.strap_rest[n] @ (Matrix.Rotation(math.radians(STRAP_OPEN_DEG), 4, 'X') if open_ else Matrix.Identity(4))
        bpy.context.view_layer.update()

    def bvh(self, name):
        o = self.objs[name]
        dg = bpy.context.evaluated_depsgraph_get()
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
        return BVHTree.FromPolygons(verts, polys, epsilon=0.0)

    def _height_field(self, step=0.002):
        pad = self.bvh('GEO_Padded_Top')
        self.pad_bvh = pad
        xs = np.arange(-0.300, 0.300 + 1e-9, step)
        ys = np.arange(-0.950, 0.900 + 1e-9, step)
        H = np.full((len(xs), len(ys)), np.nan)
        for i, x in enumerate(xs):
            for j, y in enumerate(ys):
                hit = pad.ray_cast(Vector((x, y, 2.0)), Vector((0, 0, -1)))
                if hit[0] is not None:
                    H[i, j] = hit[0].z
        self.hx, self.hy, self.H, self.hstep = xs, ys, H, step

    def pad_top(self, pts):
        """Bilinear pad-top height under table-space points; NaN where there is no pad below."""
        fx = (pts[:, 0] - self.hx[0]) / self.hstep
        fy = (pts[:, 1] - self.hy[0]) / self.hstep
        ok = (fx >= 0) & (fy >= 0) & (fx < len(self.hx) - 1) & (fy < len(self.hy) - 1)
        out = np.full(len(pts), np.nan)
        i = np.floor(fx[ok]).astype(int)
        j = np.floor(fy[ok]).astype(int)
        u, v = fx[ok] - i, fy[ok] - j
        H = self.H
        h = (H[i, j] * (1 - u) * (1 - v) + H[i + 1, j] * u * (1 - v) + H[i, j + 1] * (1 - u) * v + H[i + 1, j + 1] * u * v)
        out[ok] = h
        return out

    def pad_gaps(self, pts):
        """Gap above the pad top for every point over the pad (NaN elsewhere)."""
        return pts[:, 2] - self.pad_top(pts)

    def exact_pad_gap(self, p):
        hit = self.pad_bvh.ray_cast(Vector((p[0], p[1], 2.0)), Vector((0, 0, -1)))
        return None if hit[0] is None else p[2] - hit[0].z


# ----------------------------------------------------------------------------- patient rig
class Patient(AC.Buddy):
    """Opens the read-only PATIENT source and the TABLE_REST contract; prepares a clean scene."""

    def __init__(self):
        # TABLE_REST raw values (one-frame action, the contract every table clip starts from)
        bpy.ops.wm.open_mainfile(filepath=str(TABLEREST_BLEND))
        rig = bpy.data.objects[RIG_NAME]
        names = ordered_bones(rig)
        vals = read_values(rig.animation_data.action, 1.0, names)
        tr_rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        for n, v in vals.items():
            if v['loc'] is not None and rig.data.bones[n].parent is not None:
                assert max(abs(x) for x in v['loc']) < 1e-9, ('non-root location in TABLE_REST', n)
                v['loc'] = None
        self.tablerest_values = vals
        bpy.ops.wm.open_mainfile(filepath=str(PATIENT_BLEND))
        self.from_json = False
        self.scene = bpy.context.scene
        self.rig = rig = bpy.data.objects[RIG_NAME]
        self.meshes = [bpy.data.objects[n] for n in MESH_NAMES]
        self.order = ordered_bones(rig)
        assert self.order == names and len(self.order) == 65
        assert list(rig.data.bones.keys()) == self.order
        self.parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
        self.children = {b.name: [c.name for c in b.children] for b in rig.data.bones}
        self.rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        for n in self.order:
            d = max(abs(self.rest[n][i][j] - tr_rest[n][i][j]) for i in range(4) for j in range(4))
            assert d < 1e-6, ('rest differs from TABLE_REST file', n, d)
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
        self.tablerest = self.pose_from_values(self.tablerest_values)
        self._skin_setup()

    # -- placement ------------------------------------------------------------------------------
    def place(self, M):
        self.rig.matrix_world = M
        bpy.context.view_layer.update()
        self.W = np.array(M)

    # -- numpy linear-blend skinning (matches the Armature modifier; verified in self_test) ----------
    def _skin_setup(self):
        rig = self.rig
        deform = [b.name for b in rig.data.bones if b.use_deform]
        self.deform = deform
        di = {n: i for i, n in enumerate(deform)}
        vs, idx, wts, region, mesh_id = [], [], [], [], []
        for mi, o in enumerate(self.meshes):
            M = np.array(rig.matrix_world.inverted() @ o.matrix_world)
            names = [g.name for g in o.vertex_groups]
            for v in o.data.vertices:
                co = M[:3, :3] @ np.array(v.co) + M[:3, 3]
                gs = [(di[names[g.group]], g.weight) for g in v.groups if names[g.group] in di and g.weight > 0]
                gs.sort(key=lambda x: -x[1])
                tot = sum(w for _, w in gs)
                gs = gs[:8]
                ii = [g[0] for g in gs] + [0] * (8 - len(gs))
                ww = [g[1] / tot for g in gs] + [0.0] * (8 - len(gs))
                vs.append(co)
                idx.append(ii)
                wts.append(ww)
                dom = deform[gs[0][0]] if gs else None
                r = BONE_REGION.get(dom, 'pelvis')
                if o.name == 'Face':
                    r = 'head'
                elif o.name == 'Shorts':
                    r = 'pelvis'
                region.append(r)
                mesh_id.append(mi)
        self.sk_v = np.array(vs)
        self.sk_i = np.array(idx)
        self.sk_w = np.array(wts)
        self.region = np.array(region)
        self.mesh_id = np.array(mesh_id)
        self.rest_inv = np.array([np.array(self.rest[n].inverted()) for n in deform])
        self.region_mask = {r: self.region == r for r in REGION_BONES}

    def skin(self, pose, world=True):
        S = np.array([np.array(pose[n]) for n in self.deform]) @ self.rest_inv     # (K,4,4)
        A = S[self.sk_i]                                                            # (V,8,4,4)
        p = np.einsum('vkij,vj->vki', A[:, :, :3, :3], self.sk_v) + A[:, :, :3, 3]
        out = np.einsum('vk,vki->vi', self.sk_w, p)
        if world:
            out = out @ self.W[:3, :3].T + self.W[:3, 3]
        return out

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

    # -- helpers -------------------------------------------------------------------------------
    def bone_point(self, pose, bone, local):
        """Armature-space position of a point fixed in a bone's rest-relative frame."""
        return (pose[P + bone] @ self.rest[P + bone].inverted() @ Vector(local).to_4d()).to_3d() \
            if len(local) == 3 else None

    def strap_points(self, pose):
        """Armature-space points carried by the strapped segments (fixed in the bones' frames)."""
        out = {}
        for s, _ in SIDES:
            out['forearm_' + s] = self.carried(pose, s + 'ForeArm', self._strap_local['forearm_' + s])
            out['shin_' + s] = self.carried(pose, s + 'Leg', self._strap_local['shin_' + s])
            out['wrist_' + s] = pose[P + s + 'Hand'].translation.copy()
        out['pelvis'] = self.carried(pose, 'Hips', self._strap_local['pelvis'])
        return out

    def carried(self, pose, bone, rest_pt):
        b = P + bone
        return (pose[b] @ self.rest[b].inverted() @ rest_pt.to_4d()).to_3d()

    def init_strap_points(self):
        base = self.tablerest
        self._strap_local = {}
        for s, _ in SIDES:
            e, w = base[P + s + 'ForeArm'].translation, base[P + s + 'Hand'].translation
            f = (e.y - (-STRAP_Y['arm'])) / (e.y - w.y)
            pt = e.lerp(w, f)
            self._strap_local['forearm_' + s] = (self.rest[P + s + 'ForeArm'] @ base[P + s + 'ForeArm'].inverted() @ pt.to_4d()).to_3d()
            k, a = base[P + s + 'Leg'].translation, base[P + s + 'Foot'].translation
            f = (k.y - (-STRAP_Y['leg'])) / (k.y - a.y)
            pt = k.lerp(a, f)
            self._strap_local['shin_' + s] = (self.rest[P + s + 'Leg'] @ base[P + s + 'Leg'].inverted() @ pt.to_4d()).to_3d()
        h = base[P + 'Hips'].translation.copy()
        pt = Vector((0.0, -STRAP_Y['torso'], h.z))
        self._strap_local['pelvis'] = (self.rest[P + 'Hips'] @ base[P + 'Hips'].inverted() @ pt.to_4d()).to_3d()
        self.strap0 = self.strap_points(base)

    def export_fbx(self, action, fbx_path):
        """Armature only, rig object at identity (PatientRest / the floor root supplies placement)."""
        rig = self.rig
        keep = rig.matrix_world.copy()
        rig.matrix_world = Matrix.Identity(4)
        rig.animation_data.action = None
        for pb in rig.pose.bones:
            pb.matrix_basis.identity()
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        assert [a.name for a in bpy.data.actions] == [action.name], [a.name for a in bpy.data.actions]
        bpy.ops.export_scene.fbx(filepath=str(fbx_path), use_selection=True, object_types={'ARMATURE'},
                                 add_leaf_bones=False, use_armature_deform_only=False, bake_anim=True,
                                 bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                                 bake_anim_step=.5, bake_anim_simplify_factor=0,
                                 axis_forward='-Z', axis_up='Y', apply_unit_scale=True,
                                 use_mesh_modifiers=False)
        rig.matrix_world = keep
        rig.animation_data.action = action
        self.scene.frame_set(1)


# ----------------------------------------------------------------------------- lying machinery
class LieRig:
    """FK + IK on top of the TABLE_REST pose. Arms and legs are re-solved by IK so the strapped
    segments follow authored targets (pinned unless the clip moves them)."""

    def __init__(self, B, stage):
        self.B = B
        self.S = stage
        self.base = B.tablerest
        B.place(W_PR)
        B.init_strap_points()
        self.arm = {s: B.chain_info2(self.base, 'arm', s, (0, 0, 1)) for s, _ in SIDES}
        # straight TABLE_REST legs: the knees bend up (+Z)
        self.leg = {s: B.chain_info2(self.base, 'leg', s, (0, 0, 1)) for s, _ in SIDES}
        self.wrist0 = {s: self.base[P + s + 'Hand'].translation.copy() for s, _ in SIDES}
        self.ankle0 = {s: self.base[P + s + 'Foot'].translation.copy() for s, _ in SIDES}
        self.elbow0 = {s: self.base[P + s + 'ForeArm'].translation.copy() for s, _ in SIDES}
        self.knee0 = {s: self.base[P + s + 'Leg'].translation.copy() for s, _ in SIDES}
        self.fix_log = []

    def pole_arm(self, out, s, swing=0.0, lift=0.0):
        """Elbow pole: base elbow offset from the shoulder-wrist line, rotated about that line."""
        info = self.arm[s]
        return info['pole0']

    def solve_arm(self, out, s, target, hand_q=None, pole=None):
        """IK the arm to a wrist target. hand_q: armature-space rotation applied to the base hand."""
        info = self.arm[s]
        hb = self.base[P + s + 'Hand']
        q = hand_q if hand_q is not None else QI()
        em = q.to_matrix().to_4x4() @ Matrix.Translation(-hb.translation) @ hb
        # hand orientation follows the chest delta carried in out (keep base orientation in arm space)
        return self.B.solve_chain2(out, info, target, em, pole if pole is not None else info['pole0'])

    def solve_leg(self, out, s, target, foot_q=None, pole=None):
        info = self.leg[s]
        fb = self.base[P + s + 'Foot']
        q = foot_q if foot_q is not None else QI()
        em = q.to_matrix().to_4x4() @ Matrix.Translation(-fb.translation) @ fb
        return self.B.solve_chain2(out, info, target, em, pole if pole is not None else info['pole0'])

    # -- contact: lift a region off the pad by rotating a bone subtree ---------------------------
    def gaps(self, out, region=None):
        pts = self.B.skin(out)
        g = self.S.pad_gaps(pts)
        if region is not None:
            g = np.where(self.B.region_mask[region], g, np.nan)
        return g

    def min_gap(self, out, regions):
        pts = self.B.skin(out)
        g = self.S.pad_gaps(pts)
        m = np.zeros(len(g), dtype=bool)
        for r in regions:
            m |= self.B.region_mask[r]
        g = g[m]
        g = g[~np.isnan(g)]
        return float(g.min()) if len(g) else 1.0

    def lift(self, out, regions, apply, margin=0.0012, max_angle=20.0, tag=''):
        """Find the smallest parameter a >= 0 with min gap(regions) >= margin, where apply(out, a)
        returns a new pose. Secant / bisection on the skinned mesh. Returns (pose, a)."""
        g0 = self.min_gap(out, regions)
        if g0 >= margin:
            return out, 0.0
        lo, hi = 0.0, None
        a = 1.0
        for _ in range(12):
            p = apply(out, a)
            g = self.min_gap(p, regions)
            if g >= margin:
                hi = a
                break
            lo = a
            a = min(max_angle, a * 2.0)
            if lo >= max_angle:
                break
        if hi is None:
            self.fix_log.append((tag, 'unsolved', g))
            return apply(out, max_angle), max_angle
        for _ in range(14):
            mid = 0.5 * (lo + hi)
            p = apply(out, mid)
            if self.min_gap(p, regions) >= margin:
                hi = mid
            else:
                lo = mid
            if hi - lo < 0.01:
                break
        self.fix_log.append((tag, hi))
        return apply(out, hi), hi


def rotate_about_subtree(B, out, short, axis, deg, pivot=None):
    new = {k: v.copy() for k, v in out.items()}
    B.rotate_subtree(new, short, R(axis, deg), pivot=pivot)
    return new


def quat_close(a, b):
    return abs(a.dot(b))
