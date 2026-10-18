"""Core for the Escape_v01 package: the patient (SAUSAGE_BUDDY_PATIENT_v05, mixamorig 65-bone rig,
skeleton unchanged) frees himself from the operating table TABLE-ASTRA-001 v02 and runs.
Blender 5.2, headless. Original FK/IK keyframe acting; no external motion, no paid generation.

Reuses (imported read-only, never modified):
  ../Operation_v01/op_core.py      Patient (TABLE_REST contract, numpy skinning, FBX export), Stage
  ../Idle_Knock_v03/acting_core.py Curve, FK deltas, flip-free two-bone IK, keying, step limiter

Frames (same as Operation_v01)
  * armature space = all authoring: the rig object sits at PatientRest = T(0,0,0.66) @ Rz(180) in
    table space; lying body: head toward +Y, face +Z, patient's LEFT = +X, pad top at z ~ 0,
    floor at z = -0.66.
  * table space (Blender, RIG_Table_Root at the origin): head end -Y, patient's left = -X.
  * Unity prefab-local = (-x, z, -y) of table space; a point given in armature space maps to
    PatientRest-local Unity (-x, z, -y) as well.
Only four limb straps exist for gameplay (Fedya 2026-10-18: torso strap removed); STRAP_TORSO is
hidden in every review render and never constrains anything.
"""
from pathlib import Path
import sys, math, json, hashlib
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ANIM = HERE.parent
OPDIR = ANIM / 'Operation_v01'
if str(OPDIR) not in sys.path:
    sys.path.insert(0, str(OPDIR))
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
import op_core as O
import acting_core as AC
from acting_core import R, QI, Curve, P, clamp, smooth, smoother

CHAR = ANIM.parent
O.PATIENT_BLEND = CHAR / 'Patient_v05' / 'SAUSAGE_BUDDY_PATIENT_v05.blend'     # current patient
FLEE_BLEND = ANIM / 'Escape_Police_v01' / 'Flee_Run_v01.blend'
FPS = 30
PAD_Z = O.PAD_Z
W_PR = O.W_PR
FLOOR_Z = -PAD_Z
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
SIDES = (('Left', 1), ('Right', -1))
LIMB_STRAPS = ('STRAP_ARM_L', 'STRAP_ARM_R', 'STRAP_LEG_L', 'STRAP_LEG_R')
STRAP_OF = {('arm', 'L'): 'STRAP_ARM_L', ('arm', 'R'): 'STRAP_ARM_R', ('leg', 'L'): 'STRAP_LEG_L', ('leg', 'R'): 'STRAP_LEG_R'}
STAND_AT_LEFT = (-0.57, 0.29, 0.0)   # review only: instrument stand on the patient's LEFT (as in Unity v03+)
OPEN_DEG = 120.0
FACE_BIND = Vector((0, -1, 0))       # the character faces -Y in the bind pose

# channel set ---------------------------------------------------------------------------------------
CH = ['px', 'py', 'pz', 'yaw', 'pitch', 'roll', 'crunch', 'twist', 'bend', 'neck', 'hnod', 'hyaw', 'htilt',
      'look_w', 'lk_x', 'lk_y', 'lk_z', 'seat', 'floor']
for _t in ('L', 'R'):
    CH += [c + '_' + _t for c in (
        # FK arm / leg (relative to the parent, base = TABLE_REST, degrees)
        'sh', 'pr', 'afl', 'aab', 'atw', 'el', 'hfl', 'cu', 'th',
        'fl', 'ab', 'lr', 'kn', 'fo', 'toe',
        # rails (1 = strapped segment on its TABLE_REST strap line), knee lift (m), forearm twist
        'arail', 'lrail', 'klift', 'ftw',
        # hand IK: weight, grip-point target, finger direction, palm normal, elbow pole
        'ik', 'tx', 'ty', 'tz', 'fx', 'fy', 'fz', 'nx', 'ny', 'nz', 'qx', 'qy', 'qz',
        # foot IK (ankle target, toe direction), weight
        'fik', 'ax', 'ay', 'az', 'ox', 'oy', 'oz')]
CH = tuple(CH)
MIRROR_NEG = {'px', 'yaw', 'roll', 'twist', 'bend', 'hyaw', 'htilt', 'lk_x'}
for _t in ('L', 'R'):
    MIRROR_NEG |= {c + '_' + _t for c in ('tx', 'fx', 'nx', 'qx', 'ax', 'ox')}


def mirror_name(k):
    if k.endswith('_L'):
        return k[:-2] + '_R'
    if k.endswith('_R'):
        return k[:-2] + '_L'
    return k


def mirror_dict(d):
    out = {}
    for k, v in d.items():
        m = mirror_name(k)
        out[m] = -v if k in MIRROR_NEG else v
    return out


def mirror_strap(n):
    return n[:-1] + ('R' if n.endswith('L') else 'L')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def V(*a):
    return Vector(a[0] if len(a) == 1 else a)


def tbl_to_arm(p):
    return (W_PR.inverted() @ Vector(p).to_4d()).to_3d()


def arm_to_tbl(p):
    return (W_PR @ Vector(p).to_4d()).to_3d()


# ----------------------------------------------------------------------------------------- stage
class Stage(O.Stage):
    """Table v02 (review/validation only, never exported). Per-strap angles; torso strap hidden."""

    def __init__(self):
        super().__init__(straps_open=False, stand=True, coll_name='REVIEW_TABLE_v02_NOT_EXPORTED')
        self.objs['STAND_Root'].location = STAND_AT_LEFT
        t = self.objs['STRAP_TORSO']
        t.hide_render = True
        t.hide_viewport = True
        self.angles = {n: 0.0 for n in LIMB_STRAPS}
        bpy.context.view_layer.update()
        self.buckles = self._buckle_geometry()

    def set_angles(self, angles):
        for n in LIMB_STRAPS:
            a = float(angles.get(n, 0.0))
            self.angles[n] = a
            self.objs[n].matrix_basis = self.strap_rest[n] @ Matrix.Rotation(math.radians(a), 4, 'X')
        bpy.context.view_layer.update()

    def _buckle_geometry(self):
        """Buckle block of every limb strap (the mesh's small separate component): top-face centre
        and outward normal in strap-local coordinates (exact table v02 geometry)."""
        out = {}
        for n in LIMB_STRAPS + ('STRAP_TORSO',):
            o = self.objs[n]
            me = o.data
            # connected components by edges
            adj = {i: [] for i in range(len(me.vertices))}
            for e in me.edges:
                a, b = e.vertices
                adj[a].append(b)
                adj[b].append(a)
            seen, comps = set(), []
            for i in range(len(me.vertices)):
                if i in seen:
                    continue
                st, comp = [i], []
                seen.add(i)
                while st:
                    x = st.pop()
                    comp.append(x)
                    for y in adj[x]:
                        if y not in seen:
                            seen.add(y)
                            st.append(y)
                comps.append(sorted(comp))
            comps.sort(key=len)
            bk = comps[0]
            top = [vi for k, vi in enumerate(bk) if k % 4 in (2, 3)]
            topset = set(top)
            c = sum((me.vertices[i].co for i in top), Vector()) / len(top)
            nrm = Vector()
            for p in me.polygons:
                if all(v in topset for v in p.vertices):
                    nrm += p.normal * p.area
            nrm.normalize()
            allc = sum((me.vertices[i].co for i in bk), Vector()) / len(bk)
            out[n] = {'top_local': c.copy(), 'normal_local': nrm.copy(), 'centroid_local': allc.copy()}
        return out

    def strap_matrix(self, name, deg):
        """World (= table) matrix of a strap at a given opening angle."""
        o = self.objs[name]
        par = o.parent.matrix_world if o.parent else Matrix.Identity(4)
        return par @ self.strap_rest[name] @ Matrix.Rotation(math.radians(deg), 4, 'X')

    def buckle(self, name, deg=0.0, space='arm'):
        """(top centre, outward normal, along-band direction, across-band direction) of a buckle."""
        M = self.strap_matrix(name, deg)
        b = self.buckles[name]
        p = M @ b['top_local']
        n = (M.to_3x3() @ b['normal_local']).normalized()
        u = (M.to_3x3() @ Vector((0, 1, 0))).normalized()     # strap local +Y = inward along the band
        w = (M.to_3x3() @ Vector((1, 0, 0))).normalized()     # hinge axis = across the band
        if space == 'arm':
            Wi = W_PR.inverted()
            p = (Wi @ p.to_4d()).to_3d()
            n, u, w = [(Wi.to_3x3() @ x).normalized() for x in (n, u, w)]
        return p, n, u, w


# ----------------------------------------------------------------------------------------- context
class EscCtx:
    """Pose builder: channel dict -> armature-space pose (bone -> 4x4) with strap rails, hand/foot
    IK, look-at and pad / floor contact. The rig object stays at PatientRest for every clip."""

    def __init__(self, B, stage):
        self.B = B
        self.S = stage
        B.place(W_PR)
        B.init_strap_points()
        base = self.base = B.tablerest
        self.rest = B.rest
        self.h0 = base[P + 'Hips'].translation.copy()
        self.head_axis = (base[P + 'HeadTop_End'].translation - base[P + 'Head'].translation).normalized()
        self.arm_axis = {s: (base[P + s + 'ForeArm'].translation - base[P + s + 'Arm'].translation).normalized() for s, _ in SIDES}
        self.leg_axis = {s: (base[P + s + 'Foot'].translation - base[P + s + 'UpLeg'].translation).normalized() for s, _ in SIDES}
        self.arm = {s: B.chain_info2(base, 'arm', s, (0, 0, 1)) for s, _ in SIDES}
        self.leg = {s: B.chain_info2(base, 'leg', s, (0, 0, 1)) for s, _ in SIDES}
        self._hand_geometry()
        self._face_geometry()
        self.stats = {'rail_slide_max': 0.0, 'rail_miss_max': 0.0, 'ik_over_max': {}, 'contact_lift_max': 0.0}
        self.rail_log = []

    # -- hand / face reference points -----------------------------------------------------------
    def _hand_geometry(self):
        """Palm grip point (bind pose, armature) per hand: the palm-side surface under the middle of
        the palm. Bind pose: palms face -Z, the left fingers point +X, the right fingers -X."""
        B = self.B
        body = B.meshes[0]
        names = [g.name for g in body.vertex_groups]
        Mb = B.rig.matrix_world.inverted() @ body.matrix_world      # armature space (bind pose)
        self.grip_rest, self.f_bind, self.n_bind = {}, {}, {}
        for s, sgn in SIDES:
            hb = P + s + 'Hand'
            w0 = self.rest[hb].translation
            pts = []
            for v in body.data.vertices:
                best, bw = None, 0.0
                for g in v.groups:
                    if g.weight > bw:
                        best, bw = names[g.group], g.weight
                if best and best.startswith(P + s + 'Hand'):
                    pts.append(Mb @ v.co)
            pts = np.array(pts)
            along = (pts[:, 0] - w0.x) * sgn
            m = (along > 0.035) & (along < 0.075) & (np.abs(pts[:, 1] - w0.y) < 0.025)
            sel = pts[m]
            k = int(np.argmin(sel[:, 2]))
            palm = Vector(sel[k])
            palm.y = w0.y
            self.grip_rest[s] = palm
            self.f_bind[s] = Vector((sgn, 0, 0))
            self.n_bind[s] = Vector((0, 0, -1))
            self.hand_len = float(np.max(along))
        # rest (TABLE_REST) hand frames for "rest" IK targets
        base = self.base
        self.rest_grip, self.rest_f, self.rest_n = {}, {}, {}
        for s, _ in SIDES:
            hb = P + s + 'Hand'
            Q = base[hb].to_3x3() @ self.rest[hb].to_3x3().inverted()
            self.rest_grip[s] = (base[hb] @ self.rest[hb].inverted() @ self.grip_rest[s].to_4d()).to_3d()
            self.rest_f[s] = (Q @ self.f_bind[s]).normalized()
            self.rest_n[s] = (Q @ self.n_bind[s]).normalized()
            self.rest_pole = None

    def _face_geometry(self):
        face = self.B.meshes[1]
        Mf = self.B.rig.matrix_world.inverted() @ face.matrix_world
        pts = np.array([list(Mf @ v.co) for v in face.data.vertices])
        self.face_rest = Vector(pts.mean(axis=0))       # bind-pose face centre (eyes/nose area)

    def grip_point(self, pose, s):
        hb = P + s + 'Hand'
        return (pose[hb] @ self.rest[hb].inverted() @ self.grip_rest[s].to_4d()).to_3d()

    def face_point(self, pose):
        hb = P + 'Head'
        return (pose[hb] @ self.rest[hb].inverted() @ self.face_rest.to_4d()).to_3d()

    def hand_frame(self, pose, s):
        hb = P + s + 'Hand'
        Q = pose[hb].to_3x3() @ self.rest[hb].to_3x3().inverted()
        return (Q @ self.f_bind[s]).normalized(), (Q @ self.n_bind[s]).normalized()

    # -- channel defaults --------------------------------------------------------------------------
    def ch0(self):
        c = {k: 0.0 for k in CH}
        for t in ('L', 'R'):
            c['arail_' + t] = 1.0
            c['lrail_' + t] = 1.0
            s = 'Left' if t == 'L' else 'Right'
            g, f, n = self.rest_grip[s], self.rest_f[s], self.rest_n[s]
            for k, v in zip(('tx', 'ty', 'tz', 'fx', 'fy', 'fz', 'nx', 'ny', 'nz'), list(g) + list(f) + list(n)):
                c[k + '_' + t] = v
            pole = self.arm[s]['pole0']
            c['qx_' + t], c['qy_' + t], c['qz_' + t] = pole
            a = self.base[P + s + 'Foot'].translation
            c['ax_' + t], c['ay_' + t], c['az_' + t] = a
            c['ox_' + t], c['oy_' + t], c['oz_' + t] = 0.0, -1.0, 0.0
        c['lk_x'], c['lk_y'], c['lk_z'] = 0.0, 0.2, 1.0
        return c

    # -- rails -------------------------------------------------------------------------------------
    def rail(self, out, upper, lower, end_sub, lift, twist, slide_lim=(-0.05, 0.07), tag=''):
        """Strapped segment on its TABLE_REST line (after Operation_v01 TableCtx._rail): the lower
        segment may only slide along its own line (parallel to the pad), twist about it and tilt a
        few mm about the pad point under its end joint; the upper segment joins the moved joint."""
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
        d = Vector((d.x, d.y, 0.0)).normalized()
        v = K - Hp
        b = d.dot(v)
        cc = v.dot(v) - l1 * l1
        disc = b * b - cc
        miss = 0.0
        if disc >= 0:
            r1, r2 = -b + math.sqrt(disc), -b - math.sqrt(disc)
            sl = r1 if abs(r1) < abs(r2) else r2
        else:
            sl = -b
            miss = math.sqrt(-disc)
        sl0 = sl
        sl = clamp(sl, slide_lim[0], slide_lim[1])
        M = Matrix.Translation(d * sl) @ M
        K = M @ K0
        if sl != sl0:
            miss = max(miss, abs((K - Hp).length - l1))
        q = (K0 - U0.translation).rotation_difference(K - Hp)
        Um = (q.to_matrix() @ U0.to_3x3()).to_4x4()
        Um.translation = Hp
        out[nU] = Um
        for n in B.subtree(lower):
            out[n] = M @ base[n]
        self.stats['rail_slide_max'] = max(self.stats['rail_slide_max'], abs(sl))
        self.stats['rail_miss_max'] = max(self.stats['rail_miss_max'], miss)
        self._last_rail = (tag, sl, miss)
        return sl, miss

    # -- hand IK -----------------------------------------------------------------------------------
    def hand_ik(self, out, s, grip, f, n, pole, tag=''):
        B = self.B
        hb = P + s + 'Hand'
        f = Vector(f).normalized()
        n = Vector(n)
        n = (n - f * n.dot(f)).normalized()
        Fb = Matrix((self.f_bind[s], self.n_bind[s], self.f_bind[s].cross(self.n_bind[s]))).transposed()
        Fd = Matrix((f, n, f.cross(n))).transposed()
        Q = Fd @ Fb.transposed()
        Rh = Q @ self.rest[hb].to_3x3()
        wrist = Vector(grip) - Q @ (self.grip_rest[s] - self.rest[hb].translation)
        em = Rh.to_4x4()
        em.translation = wrist
        over = B.solve_chain2(out, self.arm[s], wrist, em, Vector(pole).normalized())
        if over > 0:
            k = tag or s
            self.stats['ik_over_max'][k] = max(self.stats['ik_over_max'].get(k, 0.0), over)
        return over

    def foot_ik(self, out, s, ankle, toe_dir, pole=None):
        """Ankle target with the foot turned so its toe points along toe_dir (horizontal), sole flat."""
        B = self.B
        fb = P + s + 'Foot'
        # bind foot: toe direction in the bind pose = toe base - foot head (projected horizontal)
        tb = self.rest[P + s + 'ToeBase'].translation - self.rest[fb].translation
        tb = Vector((tb.x, tb.y, 0)).normalized()
        td = Vector(toe_dir)
        td = Vector((td.x, td.y, 0)).normalized()
        Q = tb.rotation_difference(td) if tb.dot(td) > -0.999 else R(Z, 180)
        Rf = Q.to_matrix() @ self.rest[fb].to_3x3()
        em = Rf.to_4x4()
        em.translation = Vector(ankle)
        if pole is None:
            pole = (td + Vector((0, 0, 0.2))).normalized()
        over = B.solve_chain2(out, self.leg[s], Vector(ankle), em, Vector(pole))
        if over > 0:
            self.stats['ik_over_max']['foot_' + s] = max(self.stats['ik_over_max'].get('foot_' + s, 0.0), over)
        return over

    # -- look at -----------------------------------------------------------------------------------
    def look_at(self, out, target, w, neck_share=0.4, max_deg=80.0):
        if w <= 1e-6:
            return
        B = self.B
        hb = P + 'Head'
        Dh = out[hb].to_3x3() @ self.rest[hb].to_3x3().inverted()
        face = (Dh @ FACE_BIND).normalized()
        fp = self.face_point(out)
        d = Vector(target) - fp
        if d.length < 1e-4:
            return
        d.normalize()
        rot = face.rotation_difference(d)
        ang = math.degrees(rot.angle)
        k = w * (min(1.0, max_deg / ang) if ang > 1e-6 else 1.0)
        rw = QI().slerp(rot, k)
        qn = QI().slerp(rw, neck_share)
        B.rotate_subtree(out, 'Neck', qn)
        B.rotate_subtree(out, 'Head', rw @ qn.inverted())

    # -- the pose ------------------------------------------------------------------------------------
    def pose(self, c, closed):
        """closed: {'arm_L': bool, 'arm_R': bool, 'leg_L': bool, 'leg_R': bool} - closed straps force
        their limb onto the rail (weight 1)."""
        B, base = self.B, self.base
        q = {}
        k = c['crunch']
        q['Spine'] = R(X, 0.34 * k) @ R(Z, 0.3 * c['bend'])
        q['Spine1'] = R(X, 0.34 * k) @ R(Y, 0.5 * c['twist']) @ R(Z, 0.35 * c['bend'])
        q['Spine2'] = R(X, 0.32 * k) @ R(Y, 0.5 * c['twist']) @ R(Z, 0.35 * c['bend'])
        q['Neck'] = R(X, c['neck'])
        q['Head'] = R(self.head_axis, c['hyaw']) @ R(Z, c['htilt']) @ R(X, c['hnod'])
        for s, sgn in SIDES:
            t = s[0]
            q[s + 'UpLeg'] = R(Z, sgn * c['ab_' + t]) @ R(X, -c['fl_' + t]) @ R(self.leg_axis[s], -sgn * c['lr_' + t])
            q[s + 'Leg'] = R(X, c['kn_' + t])
            q[s + 'Foot'] = R(X, c['fo_' + t])
            if c['toe_' + t]:
                q[s + 'ToeBase'] = R(X, c['toe_' + t])
            q[s + 'Shoulder'] = R(Z, sgn * c['sh_' + t]) @ R(Y, -sgn * c['pr_' + t])
            q[s + 'Arm'] = R(Z, sgn * c['aab_' + t]) @ R(X, -c['afl_' + t]) @ R(self.arm_axis[s], sgn * c['atw_' + t])
            q[s + 'ForeArm'] = R(X, -c['el_' + t])
            if c['hfl_' + t]:
                q[s + 'Hand'] = R(X, -c['hfl_' + t])
        h = self.h0
        root = (Matrix.Translation(h + Vector((c['px'], c['py'], c['pz']))) @
                (R(Z, c['yaw']) @ R(X, c['pitch']) @ R(Y, c['roll'])).to_matrix().to_4x4() @ Matrix.Translation(-h))
        out, _ = B.fk(base, q, root=root)
        # legs: foot IK, then rails --------------------------------------------------------------
        for s, sgn in SIDES:
            t = s[0]
            w = c['fik_' + t]
            if w > 1e-6:
                other = {kk: v.copy() for kk, v in out.items()}
                self.foot_ik(other, s, Vector((c['ax_' + t], c['ay_' + t], c['az_' + t])),
                             Vector((c['ox_' + t], c['oy_' + t], c['oz_' + t])))
                B.blend_subtree(out, other, s + 'UpLeg', min(1.0, w))
            w = 1.0 if closed.get('leg_' + t) else c['lrail_' + t]
            if w > 1e-6:
                other = {kk: v.copy() for kk, v in out.items()}
                self.rail(other, s + 'UpLeg', s + 'Leg', s + 'Foot', c['klift_' + t], 0.0, tag='leg_' + t)
                if c['fo_' + t]:
                    B.rotate_subtree(other, s + 'Foot', R(X, c['fo_' + t]))
                if c['toe_' + t]:
                    B.rotate_subtree(other, s + 'ToeBase', R(X, c['toe_' + t]))
                B.blend_subtree(out, other, s + 'UpLeg', min(1.0, w))
        # arms: hand IK, then rails ---------------------------------------------------------------
        for s, sgn in SIDES:
            t = s[0]
            w = c['ik_' + t]
            if w > 1e-6 and not closed.get('arm_' + t):
                other = {kk: v.copy() for kk, v in out.items()}
                self.hand_ik(other, s, Vector((c['tx_' + t], c['ty_' + t], c['tz_' + t])),
                             Vector((c['fx_' + t], c['fy_' + t], c['fz_' + t])),
                             Vector((c['nx_' + t], c['ny_' + t], c['nz_' + t])),
                             Vector((c['qx_' + t], c['qy_' + t], c['qz_' + t])), tag='hand_' + t)
                B.blend_subtree(out, other, s + 'Arm', min(1.0, w))
            w = 1.0 if closed.get('arm_' + t) else c['arail_' + t]
            if w > 1e-6:
                other = {kk: v.copy() for kk, v in out.items()}
                self.rail(other, s + 'Arm', s + 'ForeArm', s + 'Hand', 0.0, sgn * c['ftw_' + t], tag='arm_' + t)
                B.blend_subtree(out, other, s + 'Arm', min(1.0, w))
            if c['cu_' + t] or c['th_' + t]:
                B.curl(out, s, c['cu_' + t], thumb=c['th_' + t] if c['th_' + t] else c['cu_' + t] * 0.6)
        # head ------------------------------------------------------------------------------------
        self.look_at(out, Vector((c['lk_x'], c['lk_y'], c['lk_z'])), c['look_w'])
        return out

    # -- contact ---------------------------------------------------------------------------------------
    def world_pts(self, out):
        W = np.array(W_PR)
        return self.B.skin(out, world=False) @ W[:3, :3].T + W[:3, 3]

    def pad_gap(self, out, regions=('pelvis', 'chest')):
        pts = self.world_pts(out)
        g = pts[:, 2] - self.S.pad_top(pts)
        m = np.zeros(len(g), dtype=bool)
        for r in regions:
            m |= self.B.region_mask[r]
        gg = g[m & ~np.isnan(g)]
        return (float(gg.min()) if len(gg) else 1.0), pts

    def solve(self, c, closed, seat_target=0.002, margin=0.0006):
        """Vertical root solve. seat (0..1): the pelvis rests on the pad (gap = seat_target);
        floor (0..1): the lowest vertex rests on the floor; always: chest/pelvis never under the
        pad top and nothing under the floor. Iterates on the root height (rails re-solve)."""
        c = dict(c)
        pz0 = c['pz']

        def eval_(dz):
            cc = dict(c)
            cc['pz'] = pz0 + dz
            out = self.pose(cc, closed)
            g, pts = self.pad_gap(out)
            return out, g, float(pts[:, 2].min()), cc

        out, g, zmin, cc = eval_(0.0)
        dz = 0.0
        if c['seat'] > 1e-6 or c['floor'] > 1e-6:
            tgt_d = 0.0
            if c['seat'] > 1e-6:
                tgt_d += c['seat'] * (seat_target - g)
            if c['floor'] > 1e-6:
                tgt_d += c['floor'] * (0.001 - zmin)
            dz = tgt_d
            for _ in range(4):
                out, g, zmin, cc = eval_(dz)
                err = 0.0
                if c['seat'] > 1e-6:
                    err += c['seat'] * (seat_target - g)
                if c['floor'] > 1e-6:
                    err += c['floor'] * (0.001 - zmin)
                if abs(err) < 2e-4:
                    break
                dz += err
        for _ in range(4):
            need = max(margin - g if g < margin else 0.0, 0.001 - zmin if zmin < 0.0005 else 0.0)
            if need <= 0:
                break
            dz += need + 1e-4
            out, g, zmin, cc = eval_(dz)
        self.stats['contact_lift_max'] = max(self.stats['contact_lift_max'], abs(dz))
        return out, cc, {'dz': dz, 'pad_gap': g, 'zmin': zmin}


# ----------------------------------------------------------------------------------------- keys
def build_curves(keys, ctx):
    """keys: [(t, {channel: value})], each key inherits the previous one; returns {channel: Curve}."""
    cur = ctx.ch0()
    seq = []
    for t, d in keys:
        cur = dict(cur)
        for k, v in d.items():
            assert k in cur, ('unknown channel', k)
            cur[k] = float(v)
        seq.append((float(t), cur))
    seq.sort(key=lambda x: x[0])
    curves = {}
    for ch in CH:
        vals = [(t, v[ch]) for t, v in seq]
        if all(abs(v - vals[0][1]) < 1e-12 for _, v in vals):
            const = vals[0][1]
            curves[ch] = (lambda cv: (lambda tt: cv))(const)
        else:
            curves[ch] = Curve(vals)
    return curves, seq


def ik_keys(t, pos=None, f=None, n=None, pole=None, w=None):
    d = {}
    if w is not None:
        d['ik_' + t] = w
    for nm, v in (('t', pos), ('f', f), ('n', n), ('q', pole)):
        if v is not None:
            d[nm + 'x_' + t], d[nm + 'y_' + t], d[nm + 'z_' + t] = v
    return d


def look_keys(target, w=1.0):
    return {'look_w': w, 'lk_x': target[0], 'lk_y': target[1], 'lk_z': target[2]}


def both(**kw):
    d = {}
    for k, v in kw.items():
        if k.endswith('_B'):
            d[k[:-2] + '_L'] = v
            d[k[:-2] + '_R'] = v
        else:
            d[k] = v
    return d


# ----------------------------------------------------------------------------------------- run cycle
def flee_run_frame1_values():
    """Raw values (bone -> q / loc) of Escape_Police_v01 Flee_Run_v01 frame 1 and the cycle action
    sampled every half frame (read-only open of the saved .blend). Faces -Y, in place."""
    bpy.ops.wm.open_mainfile(filepath=str(FLEE_BLEND))
    rig = bpy.data.objects[O.RIG_NAME]
    act = rig.animation_data.action
    names = AC.ordered_bones(rig)
    f0, f1 = act.frame_range
    samples = {}
    f = f0
    while f <= f1 + 1e-9:
        samples[round(f, 3)] = AC.read_values(act, f, names)
        f += 0.5
    return {'frame_range': (f0, f1), 'samples': samples, 'action': act.name}


# ----------------------------------------------------------------------------------------- self contact
class SelfContact:
    """Rough self-penetration probe on the skinned mesh: forearm / hand / shin / foot vertices of one
    limb tested against the trunk (chest + pelvis + shorts) and the head surfaces (nearest-face sign)."""

    def __init__(self, ctx):
        B = ctx.B
        self.ctx = ctx
        body = B.meshes[0]
        nb = len(body.data.vertices)
        reg = B.region
        trunk_regions = {'chest', 'pelvis'}
        mid = B.mesh_id
        offs = [0]
        for o in B.meshes:
            offs.append(offs[-1] + len(o.data.vertices))
        self.trunk_faces, self.head_faces = [], []
        for mi, o in enumerate(B.meshes):
            off = offs[mi]
            for p in o.data.polygons:
                vs = [off + v for v in p.vertices]
                rs = {reg[v] for v in vs}
                if rs <= trunk_regions:
                    self.trunk_faces.append(vs)
                elif rs == {'head'} and mi == 0:
                    self.head_faces.append(vs)
        # probe vertices: forearm + hand (+fingers) and shin + foot of each side (Body mesh only)
        self.probe = {}
        rest = B.rest
        for s, _ in SIDES:
            w_arm = [v for v in range(nb) if reg[v] == 'arm_' + s]
            # keep the distal part only (beyond the elbow in the bind pose: |x| > 0.47)
            vv = B.sk_v
            self.probe['arm_' + s] = np.array([v for v in w_arm if abs(vv[v][0]) > 0.47])
            w_leg = [v for v in range(nb) if reg[v] == 'leg_' + s]
            self.probe['leg_' + s] = np.array([v for v in w_leg if vv[v][2] < 0.45])

    def depth(self, pts, probe_key, target='trunk'):
        faces = self.trunk_faces if target == 'trunk' else self.head_faces
        verts = [Vector(p) for p in pts]
        bvh = BVHTree.FromPolygons(verts, faces, all_triangles=False, epsilon=0.0)
        worst = 0.0
        for vi in self.probe[probe_key]:
            v = verts[vi]
            loc, nrm, idx, dist = bvh.find_nearest(v, 0.12)
            if loc is None:
                continue
            if (v - loc).dot(nrm) < 0:
                worst = max(worst, dist)
        return worst
