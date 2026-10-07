"""Crowd_v01 posing core (Sausage Buddy, VOLUNTEERS ONLY). Original keyframe/procedural animation.

Builds on the shared Idle_Knock_v03 library (acting_core: rig/JSON loading, FK, two-bone IK, curves,
finger curl, keying, FBX export). Nothing outside Animations/Crowd_v01 is written.

A pose is described by a flat dict of scalar PARAMETERS (all 0 = the exact A v04 Idle frame-1 pose).
Clips are Python functions t -> params, so enter/loop/exit transitions interpolate parameters and land
exactly on each other's contract poses. One-sided parameters are written for the LEFT side and mirrored
for the right (same value = mirror-image pose), so a whole clip mirrors by swapping L/R parameters and
negating the centre-line roll/yaw/x (mirror_params).

Character frame: faces -Y, left = +X, +Z up, metres, 30 fps.
Rotation parameters are degrees, applied as deltas about each joint in the base pose's world axes,
carried by the parent (so they read "relative to the parent"):
  .p pitch  + = bends/leans forward          (R about +X)
  .r roll   + = tips toward the character's left  (R about +Y)
  .w yaw    + = turns to the character's left     (R about +Z)

Parameters (missing = 0):
  hip.x hip.y hip.z      pelvis offset (m); hip.z is clamped to leg reach unless hip.free = 1
  hip.p hip.r hip.w      pelvis rotation about the hips joint (yaw is also the knee-pole yaw)
  s1.* s2.* s3.*         Spine, Spine1, Spine2 (p, r, w);  nk.* Neck;  hd.* Head
  cL.u cL.f              clavicle lift (+ = shrug up) and forward (+ = shoulder rolls forward)
  aL.f aL.o aL.t         upper arm: forward raise, outward raise (abduction), twist (+ = external)
  eL eL.t                elbow flex (+ = more bent), forearm twist (+ = supinate, palm turns up/forward)
  wL.f wL.d wL.t         wrist flex (+ = palm side), deviation (+ = toward the thumb side), twist
  ikL.w                  0..1 blend from FK to IK for the arm; target ikL.x ikL.y ikL.z (world m,
                         x is OUTWARD: + = away from the centre line). The IK reaches with the hand
                         point ikL.pt ('wrist' | 'fist' | 'pinch' | 'palm') and keeps the FK hand rotation.
                         ikL.rel = 'Head' | 'Spine2' | 'Hips' ...: the target is given in Idle world space
                         and carried by that bone's motion (phone at the ear, hands in the pocket).
                         ikL.flat 0..1 turns the palm flat onto a support (palm down, fingers level).
  fiL thL                finger curl 0..1, thumb curl; fiL.i fiL.m fiL.r fiL.k: per-finger extra
                         (index, middle, ring, pinky)
  fL.x fL.y fL.z         foot pivot offset (m; x outward)
  fL.w                   foot yaw (+ = toe out)
  fL.r                   foot roll: + = heel up about the ball, - = toe up about the heel
  fL.wb                  foot yaw about the ball (twist on the ball of the foot, + = heel in)
  fL.t fL.tf             toe bend (+ = toes up) and toe-flatten weight (1 = toes stay flat while the
                         heel is up; default 1)
  kL                     knee pole out (deg, + = knee points outward)
  gnd                    0..1 ground/seat contact: pulls the body down onto the clip's support surfaces
  wall                   0..1 wall contact: pushes the body back onto the clip's wall plane
"""
from pathlib import Path
import sys, math
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CORE = HERE.parent / 'Idle_Knock_v03'
if str(CORE) not in sys.path:
    sys.path.insert(0, str(CORE))
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import acting_core as C
from acting_core import R, QI, P, Curve, clamp, smooth, smoother, rot_about

X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
S = Matrix.Diagonal((-1.0, 1.0, 1.0))           # mirror across the centre plane x = 0
SIDES = (('Left', 'L', 1), ('Right', 'R', -1))
FPS = C.FPS
def ball_sink(roll):
    """Skinned crease sink under the ball with the heel up and the toes flat (fit to the A v04 shoe, m)."""
    return 0.00002 * roll + 0.0000058 * roll * roll




def pry(p=0.0, r=0.0, w=0.0):
    return R(Z, w) @ R(X, p) @ R(Y, r)


def mrot(axis, deg, sgn):
    """Rotation about a LEFT-side axis, mirrored for the right side (sgn = -1)."""
    a = Vector(axis)
    if sgn < 0:
        a = S @ a
        deg = -deg
    return R(a, deg)


def mvec(v, sgn):
    v = Vector(v)
    return v if sgn > 0 else S @ v


def slerp_m(a, b, w):
    """Blend two armature matrices (rotation slerp, translation lerp)."""
    qa, qb = a.to_quaternion(), b.to_quaternion()
    m = qa.slerp(qb, w).to_matrix().to_4x4()
    m.translation = a.translation.lerp(b.translation, w)
    return m


class Rig:
    """Parametric pose builder on the Idle frame-1 base pose."""

    def __init__(self, B):
        self.B = B
        self.base = base = B.idle
        self.leg = {s: B.chain_info(base, 'leg', s, (0, -1, 0)) for s, _, _ in SIDES}
        self.arm = {s: B.chain_info(base, 'arm', s, (0, 0.3, 0)) for s, _, _ in SIDES}
        self.L = self.leg['Left']['l1'] + self.leg['Left']['l2']
        # left-side reference axes (base pose, world); the right side uses their mirror
        a, f, h = (base[P + 'Left' + n] for n in ('Arm', 'ForeArm', 'Hand'))
        up_dir = (f.translation - a.translation).normalized()
        lo_dir = (h.translation - f.translation).normalized()
        self.arm_dir = up_dir
        self.lo_dir = lo_dir
        self.hinge = up_dir.cross(lo_dir).normalized()
        hm = h.to_3x3()
        self.hand_ax = (hm.col[0].normalized(), hm.col[2].normalized(), hm.col[1].normalized())   # flex, dev, twist
        # foot pivots (base world): ball = toe joint on the floor, heel = back of the sole on the floor
        o = B.meshes[2]
        self.ball, self.heel, self.ankle_g = {}, {}, {}
        for s, _, _ in SIDES:
            ft = P + s + 'Foot'
            W = base[ft] @ B.rest[ft].inverted()
            pts = [W @ o.data.vertices[i].co for i in B.sole[s]]
            low = [p for p in pts if p.z < 0.012]
            tj = base[P + s + 'ToeBase'].translation
            an = base[ft].translation
            self.ball[s] = Vector((tj.x, tj.y, 0.0))
            self.heel[s] = Vector((an.x, max(p.y for p in low) - 0.012, 0.0))
            self.ankle_g[s] = Vector((an.x, an.y, 0.0))
        # hand reach points in the Hand bone's rest-relative frame (offset from the wrist, base pose)
        self.hand_pts = {}
        for s, _, _ in SIDES:
            hand = base[P + s + 'Hand']
            idx2 = base[P + s + 'HandIndex2'].translation
            mid2 = base[P + s + 'HandMiddle2'].translation
            mid1 = base[P + s + 'HandMiddle1'].translation
            inv = hand.inverted()
            self.hand_pts[s] = {'wrist': Vector(), 'fist': inv @ mid1, 'palm': inv @ (hand.translation.lerp(mid1, 0.6)),
                                'pinch': inv @ ((idx2 + mid2) / 2)}
        self.surfaces = []          # [(kind, fn)] support surfaces for gnd (see contact())
        self.wall_y = None          # wall plane y (behind the character) for wall contact
        self._vdom = None

    # ------------------------------------------------------------------------------------ FK part
    def _fk_q(self, p):
        g = lambda k: p.get(k, 0.0)
        q = {'Hips': pry(g('hip.p'), g('hip.r'), g('hip.w'))}
        for key, bone in (('s1', 'Spine'), ('s2', 'Spine1'), ('s3', 'Spine2'), ('nk', 'Neck'), ('hd', 'Head')):
            q[bone] = pry(g(key + '.p'), g(key + '.r'), g(key + '.w'))
        for s, k, sgn in SIDES:
            # clavicle: lift about the forward axis, forward roll about the vertical axis
            q[s + 'Shoulder'] = mrot(-Y, g('c%s.u' % k), sgn) @ mrot(Z, g('c%s.f' % k), sgn)
            # upper arm: abduct (outward) then raise forward, then twist about the new arm axis
            # a clavicle shrug swings the hanging arm outward about the clavicle's inner end; counter-rotate
            # the arm so a shrug lifts it instead (Idle_Knock_v03 gotcha 2)
            swing = mrot(-X, g('a%s.f' % k), sgn) @ mrot(-Y, g('a%s.o' % k) - 0.9 * g('c%s.u' % k), sgn)
            d = swing @ mvec(self.arm_dir, sgn)
            tw = g('a%s.t' % k)
            q[s + 'Arm'] = (R(d, -tw * sgn) if tw else QI()) @ swing
            q[s + 'ForeArm'] = mrot(self.hinge, g('e' + k), sgn) @ mrot(self.lo_dir, -g('e%s.t' % k), sgn)
            fx, dv, tw = self.hand_ax
            q[s + 'Hand'] = mrot(fx, g('w%s.f' % k), sgn) @ mrot(dv, g('w%s.d' % k), sgn) @ mrot(tw, g('w%s.t' % k), sgn)
        return q

    # ------------------------------------------------------------------------------------ feet
    def foot_matrix(self, s, sgn, p):
        g = lambda k, d=0.0: p.get(k, d)
        k = s[0]
        roll = g('f%s.r' % k)
        # with the heel up and the toes flat the skinned crease under the ball sinks (quadratically with the
        # heel angle): lift the pivot by that much so the sole never goes into the floor
        off = Vector((g('f%s.x' % k) * sgn, g('f%s.y' % k), g('f%s.z' % k) + ball_sink(max(roll, 0.0)) * g('f%s.tf' % k, 1.0)))
        yaw = g('f%s.w' % k) * sgn
        Yw = rot_about(self.ankle_g[s], R(Z, yaw))
        piv = Yw @ (self.ball[s] if roll >= 0 else self.heel[s])
        lat = R(Z, yaw) @ X
        M = Matrix.Translation(off) @ rot_about(piv, R(lat, roll)) @ Yw
        wb = g('f%s.wb' % k) * sgn
        if wb:                         # twist on the ball (the ball point stays put)
            M = rot_about(M @ self.ball[s], R(Z, wb)) @ M
            lat = R(Z, wb) @ lat
        return M, lat

    # ------------------------------------------------------------------------------------ pose
    def pose(self, p, contact=True):
        """params -> (armature-space pose dict, info)."""
        B = self.B
        g = lambda k, d=0.0: p.get(k, d)
        q = self._fk_q(p)
        feet = {s: self.foot_matrix(s, sgn, p) for s, _, sgn in SIDES}
        dz_extra = 0.0
        info = {}
        for it in range(4):
            out, dz, over = self._body(p, q, feet, dz_extra)
            if not contact or (g('gnd') <= 0 and g('wall') <= 0 and not g('lift')):
                break
            shift = self.contact(out, p)
            if shift is None:
                break
            ddz, dwy = shift
            if abs(ddz) < 2e-4 and abs(dwy) < 2e-4:
                break
            dz_extra += ddz
            if dwy:
                p = dict(p)
                p['hip.y'] = p.get('hip.y', 0.0) + dwy
        info.update(dz=dz, over=over, dz_contact=dz_extra)
        return out, info

    def _body(self, p, q, feet, dz_extra):
        B = self.B
        g = lambda k, d=0.0: p.get(k, d)
        hx, hy, hz = g('hip.x'), g('hip.y'), g('hip.z') + dz_extra
        out, _ = B.fk(self.base, q, Matrix.Translation((hx, hy, hz)))
        if not g('hip.free'):
            sup = 1.0 - g('hip.soft')
            lim = 1e9
            for s, _, _ in SIDES:
                M, _ = feet[s]
                ank = (M @ self.base[P + s + 'Foot']).translation
                v = out[P + s + 'UpLeg'].translation - ank
                r = sup * self.L
                h2 = r * r - v.x * v.x - v.y * v.y
                lim = min(lim, math.sqrt(max(h2, 0.0)) - v.z)
            if lim < 0:
                hz += lim
                out, _ = B.fk(self.base, q, Matrix.Translation((hx, hy, hz)))
        over = 0.0
        hq = out[P + 'Hips'].to_quaternion() @ self.base[P + 'Hips'].to_quaternion().inverted()
        for s, k, sgn in SIDES:
            M, lat = feet[s]
            fm = M @ self.base[P + s + 'Foot']
            # knee hinge axis: between the pelvis' and the foot's lateral axes, turned out by kL about the pelvis'
            # up axis; the pole is perpendicular to the hip-ankle line, so the knee plane can never flip
            hinge = (hq @ X + lat).normalized()
            hinge = R(hq @ Z, sgn * g('k' + k)) @ hinge
            pole = (fm.translation - out[P + s + 'UpLeg'].translation).cross(hinge)
            over = max(over, self._leg_ik(out, s, fm, pole))
            roll = g('f%s.r' % k)
            tang = -(max(roll, 0.0) * g('f%s.tf' % k, 1.0) + g('f%s.t' % k))
            if abs(tang) > 1e-9:
                B.rotate_subtree(out, s + 'ToeBase', R(lat, tang))
        # arms: optional IK on top of FK (keeps the FK hand orientation and elbow plane)
        for s, k, sgn in SIDES:
            w = g('ik%s.w' % k)
            if w > 1e-6:
                self._arm_ik(out, s, sgn, p, w)
        for s, k, sgn in SIDES:
            per = {'Index': g('fi%s' % k) + g('fi%s.i' % k), 'Middle': g('fi%s' % k) + g('fi%s.m' % k),
                   'Ring': g('fi%s' % k) + g('fi%s.r' % k), 'Pinky': g('fi%s' % k) + g('fi%s.k' % k)}
            if any(abs(v) > 1e-9 for v in per.values()) or abs(g('th' + k)) > 1e-9:
                B.curl(out, s, 0.0, thumb=g('th' + k), per=per)
        return out, hz, over

    def _leg_ik(self, out, s, fm, pole):
        """Two-bone leg IK framed by the knee hinge axis (normal of the hip-knee-ankle plane), so the thigh
        can point anywhere (sitting, squatting, crossed legs) without the bone roll flipping. A straight base
        leg is reproduced exactly. The foot subtree follows fm rigidly."""
        B = self.B
        info = self.leg[s]
        a, b, c = info['names']
        if 'n0' not in info:
            H0, K0, E0 = (self.base[n].translation for n in (a, b, c))
            info['n0'] = (E0 - H0).cross(Vector((0, -1, 0))).normalized()
            info['Fu0'] = C.frame_from(K0 - H0, info['n0']).transposed()
            info['Fl0'] = C.frame_from(E0 - K0, info['n0']).transposed()
        H = out[a].translation.copy()
        K1, E1, over = B.two_bone(H, fm.translation, info['l1'], info['l2'], Vector(pole))
        n = (E1 - H).cross(Vector(pole))
        Ru = C.frame_from(K1 - H, n) @ info['Fu0'] @ info['R_up']
        Rl = C.frame_from(E1 - K1, n) @ info['Fl0'] @ info['R_lo']
        mu = Ru.to_4x4(); mu.translation = H
        ml = Rl.to_4x4(); ml.translation = K1
        out[a], out[b] = mu, ml
        me = fm.copy(); me.translation = E1
        delta = me @ out[c].inverted()
        for n_ in B.subtree(c[len(P):]):
            out[n_] = delta @ out[n_]
        return over

    def hand_point(self, out, s, name):
        return out[P + s + 'Hand'] @ self.hand_pts[s][name]

    def _arm_ik(self, out, s, sgn, p, w):
        """Arm IK on top of the FK arm. The target blends from the FK hand point to the IK target by w, the
        elbow stays in the FK elbow plane, and each bone turns by the minimal rotation from its FK direction,
        so the FK twist (aL.t, eL.t) is kept and w = 0 reproduces the FK arm exactly (no roll flips)."""
        B = self.B
        k = s[0]
        tgt = Vector((p.get('ik%s.x' % k, 0.0) * sgn, p.get('ik%s.y' % k, 0.0), p.get('ik%s.z' % k, 0.0)))
        rel = p.get('ik%s.rel' % k)
        if rel:                        # target given in Idle world space, carried by that bone's motion
            tgt = (out[P + rel] @ self.base[P + rel].inverted()) @ tgt
        pt = p.get('ik%s.pt' % k, 'wrist')
        a, b, c = (P + s + n for n in ('Arm', 'ForeArm', 'Hand'))
        flat = p.get('ik%s.flat' % k, 0.0)
        if flat > 0:                   # palm flat on the support: palm normal (hand +Z) down, fingers level
            hm = out[c].to_3x3()
            fy = hm.col[1].copy()
            fy.z = 0.0
            if fy.length > 1e-6:
                fy.normalize()
                fz = Vector((0, 0, -1))
                fx = fy.cross(fz)
                want = Matrix((fx, fy, fz)).transposed().to_quaternion()
                q = hm.to_quaternion().slerp(want, min(1.0, flat * w))      # fades with the IK weight
                M = rot_about(out[c].translation, q @ hm.to_quaternion().inverted())
                for n_ in B.subtree(s + 'Hand'):
                    out[n_] = M @ out[n_]
        hand = out[c].copy()
        off = (hand @ self.hand_pts[s][pt]) - hand.translation
        H, K0, E0 = out[a].translation.copy(), out[b].translation.copy(), out[c].translation.copy()
        goal = E0.lerp(tgt - off, w)
        line = (E0 - H).normalized()
        e_off = (K0 - H) - line * (K0 - H).dot(line)
        pole = e_off + 0.03 * mvec(Vector((0.6, 0.6, -0.5)).normalized(), sgn)
        K1, E1, over = B.two_bone(H, goal, self.arm[s]['l1'], self.arm[s]['l2'], pole)
        # align each bone by its (direction, elbow-pole) frame relative to the FK bone: a rotation that stays
        # in the elbow plane, so it can never flip the bone roll
        frame_from = C.frame_from
        n0 = (E0 - H).cross(pole)          # elbow hinge axis (normal of the elbow plane), FK and IK
        n1 = (E1 - H).cross(pole)
        Ru = frame_from(K1 - H, n1) @ frame_from(K0 - H, n0).transposed()
        Rl = frame_from(E1 - K1, n1) @ frame_from(E0 - K0, n0).transposed()
        up_m = (Ru @ out[a].to_3x3()).to_4x4()
        up_m.translation = H
        lo_m = (Rl @ out[b].to_3x3()).to_4x4()
        lo_m.translation = K1
        he = hand.copy()
        he.translation = E1
        delta = he @ out[c].inverted()
        out[a], out[b] = up_m, lo_m
        for n in B.subtree(s + 'Hand'):
            out[n] = delta @ out[n]

    # ------------------------------------------------------------------------------------ contacts
    def vertex_dominant(self):
        """Dominant deform bone per mesh vertex (Body, Face, Outfit concatenated)."""
        if self._vdom is None:
            dom = []
            for o in self.B.meshes:
                names = [vg.name for vg in o.vertex_groups]
                for v in o.data.vertices:
                    best = max(v.groups, key=lambda g: g.weight, default=None)
                    dom.append(names[best.group] if best else '')
            self._vdom = np.array(dom)
            short = np.array([d[len(P):] if d.startswith(P) else d for d in dom])
            self.is_foot = np.array([('Foot' in d or 'Toe' in d) for d in short])
            self.is_hand = np.array([('Hand' in d) for d in short])
            self.is_shin = np.array([d.endswith('Leg') and 'Up' not in d for d in short])
        return self._vdom

    def contact(self, out, p):
        """Support/wall contact: returns (dz, dy) hips shift, or None when nothing to do.
        Surfaces: self.surfaces = [(z_top, fn_inside(xs, ys) -> bool mask)]; feet and IK-placed hands are
        excluded (they are placed exactly by their targets). gnd pulls down to touch (weight), never through;
        lift-only behaviour for gnd = 0 when p['lift'] is set."""
        self.vertex_dominant()
        pts = self.B.mesh_points(out)
        excl = self.is_foot.copy()
        for s, k, _ in SIDES:
            if p.get('ik%s.floor' % k, 0.0) > 0.0:      # hands planted on the support by IK
                excl |= self.is_hand
        if p.get('shin.free'):
            excl |= self.is_shin
        use = ~excl
        xs, ys, zs = pts[use, 0], pts[use, 1], pts[use, 2]
        dz = 0.0
        if self.surfaces:
            gaps = []
            for ztop, inside in self.surfaces:
                m = inside(xs, ys) & (zs > ztop - 0.25)
                if m.any():
                    gaps.append(float(zs[m].min()) - ztop)
            if gaps:
                gap = min(gaps)                       # > 0: floating, < 0: penetrating
                gw = p.get('gnd', 0.0)
                want = -gap * gw if gap > 0 else -gap
                dz = want
        dy = 0.0
        if self.wall_y is not None and p.get('wall', 0.0) > 0:
            gap = self.wall_y - float(ys.max())
            dy = gap * p['wall'] if gap > 0 else gap
        return dz, dy


# ---------------------------------------------------------------------------------- parameter tools
def mirror_params(p):
    """Mirror image of a parameter set: swap L/R, negate centre-line roll/yaw and hip.x."""
    out = {}
    for k, v in p.items():
        if isinstance(v, str):
            nk = k
        else:
            nk = k
        if k.startswith(('s1.', 's2.', 's3.', 'nk.', 'hd.', 'hip.')) and (k.endswith('.r') or k.endswith('.w') or k == 'hip.x'):
            v = -v
        # swap side letters in the channel key
        head, _, tail = k.partition('.')
        if head and head[-1] in 'LR' and head[:-1] in ('c', 'a', 'e', 'w', 'ik', 'fi', 'th', 'f', 'k'):
            nk = head[:-1] + ('R' if head[-1] == 'L' else 'L') + ('.' + tail if tail else '')
        out[nk] = v
    return out


def mix(a, b, w):
    """Blend two parameter dicts (numbers lerp; strings switch at w >= 0.5)."""
    keys = set(a) | set(b)
    out = {}
    for k in keys:
        va, vb = a.get(k, 0.0), b.get(k, 0.0)
        if isinstance(va, str) or isinstance(vb, str):
            out[k] = vb if w >= 0.5 else va
        else:
            out[k] = va + (vb - va) * w
    return out


def add(*ps):
    """Merge parameter dicts left to right: later values override earlier ones (pose snippets + overrides)."""
    out = {}
    for p in ps:
        out.update(p)
    return out


def layer(*ps):
    """Sum parameter dicts (numbers add; strings: the last one wins). For additive layers."""
    out = {}
    for p in ps:
        for k, v in p.items():
            out[k] = v if isinstance(v, str) else out.get(k, 0.0) + v
    return out


class Track:
    """Pose-to-pose keys: list of (t, params[, tangent mode]) -> params(t), each channel a Curve.
    A channel absent from a key holds the previous key's value at that time (so every key is a full
    pose implicitly). String channels (ik point names) step at keys. periodic=True closes a loop:
    the first and last key must be the same pose."""

    def __init__(self, keys, periodic=False, default_tan='auto'):
        keys = sorted(keys, key=lambda k: k[0])
        chans = sorted({c for k in keys for c in k[1] if not isinstance(k[1][c], str)})
        self.str_keys = [(k[0], {c: v for c, v in k[1].items() if isinstance(v, str)}) for k in keys]
        self.curves = {}
        for c in chans:
            ks, last = [], 0.0
            for k in keys:
                tan = k[2] if len(k) > 2 else default_tan
                if isinstance(tan, dict):
                    tan = tan.get(c, tan.get('*', default_tan))
                v = k[1].get(c, None)
                if v is None:
                    v = last
                last = v
                ks.append((k[0], v, tan))
            if periodic:
                ks[-1] = (ks[-1][0], ks[0][1], ks[-1][2])
            self.curves[c] = Curve(ks, periodic=periodic)
        self.t0, self.t1 = keys[0][0], keys[-1][0]

    def __call__(self, t):
        out = {c: f(t) for c, f in self.curves.items()}
        cur = {}
        for kt, sv in self.str_keys:
            if kt <= t + 1e-9:
                cur.update(sv)
        out.update(cur)
        return out


# ---------------------------------------------------------------------------------- procedural helpers
def pn(T, seed, cycles=(3, 5, 7), amps=None):
    """Periodic smooth noise in [-1, 1]-ish, zero at 0 and T."""
    return C.pnoise(T, seed, cycles, amps)


def bump(t, a, b, ease=smooth):
    """0 before a, rises to 1 at the centre, back to 0 at b (smooth window)."""
    if t <= a or t >= b:
        return 0.0
    u = (t - a) / (b - a)
    return ease(1 - abs(2 * u - 1))


def window(t, a, b, ramp):
    """1 inside [a, b] with smooth ramps of length ramp outside."""
    return smooth((t - (a - ramp)) / ramp) * (1 - smooth((t - b) / ramp))


def osc(t, freq, phase=0.0):
    return math.sin(2 * math.pi * (freq * t + phase))


# ---------------------------------------------------------------------------------- FK fitting for IK key poses
RIG = None            # the active Rig (set by build_crowd.Author); fitting needs it
_FIT_CACHE = {}


def _fit_err(rig, p, k, sgn, keys, x, x0):
    q = dict(p)
    q.update(dict(zip(keys, x)))
    q['ik%s.w' % k] = 0.0
    out, _ = rig.pose(q, contact=False)
    tgt = Vector((p['ik%s.x' % k] * sgn, p['ik%s.y' % k], p['ik%s.z' % k]))
    rel = p.get('ik%s.rel' % k)
    if rel:
        tgt = (out[P + rel] @ rig.base[P + rel].inverted()) @ tgt
    side = 'Left' if k == 'L' else 'Right'
    e = (rig.hand_point(out, side, p.get('ik%s.pt' % k, 'wrist')) - tgt).length
    return e + 0.0006 * float(np.abs(np.array(x) - np.array(x0)).sum())


def fit_params(p):
    """Move the FK arm angles (a.f, a.o, a.t, e) of every arm with IK weight > 0 so the FK hand lands near its
    IK target, staying close to the authored values (regularised). The IK then only corrects a residual, so
    IK blends never whip the forearm. Deterministic and cached."""
    if RIG is None:
        return p
    key = tuple(sorted((k, v) for k, v in p.items()))
    if key in _FIT_CACHE:
        return _FIT_CACHE[key]
    q = dict(p)
    for k, sgn in (('L', 1), ('R', -1)):
        if q.get('ik%s.w' % k, 0.0) <= 1e-6:
            continue
        keys = ['a%s.f' % k, 'a%s.o' % k, 'a%s.t' % k, 'e' + k]
        lo, hi = (-60, -12, -95, 0), (175, 170, 95, 150)
        x0 = [q.get(c, 0.0) for c in keys]
        x = list(x0)
        best = _fit_err(RIG, q, k, sgn, keys, x, x0)
        step = 16.0
        while step > 0.5:
            imp = False
            for i in range(4):
                for d in (step, -step):
                    y = list(x)
                    y[i] = min(hi[i], max(lo[i], y[i] + d))
                    e = _fit_err(RIG, q, k, sgn, keys, y, x0)
                    if e < best - 1e-6:
                        best, x, imp = e, y, True
            if not imp:
                step /= 2
        q.update(dict(zip(keys, x)))
    _FIT_CACHE[key] = q
    return q


def inherit_fit(raw, ks):
    """An IK-off key next to an IK-on key with the same authored arm FK takes the fitted FK of that key, so
    releasing (or grabbing) a contact starts from where the hand really is."""
    for k in ('L', 'R'):
        fk = ['a%s.f' % k, 'a%s.o' % k, 'a%s.t' % k, 'e' + k]
        on = lambda i: raw[i][1].get('ik%s.w' % k, 0.0) > 1e-6
        for i in range(len(raw)):
            if on(i):
                continue
            for j in (i - 1, i + 1):
                if 0 <= j < len(raw) and on(j) and all(raw[i][1].get(c, 0.0) == raw[j][1].get(c, 0.0) for c in fk):
                    for c in fk:
                        ks[i][1][c] = ks[j][1].get(c, 0.0)
                    break


def hold_ik_targets(ks):
    """Keys where an arm's IK is off take the IK target (and its frame/point) of a key where it is on, so the
    target never sweeps in from the origin while the weight ramps: the previous on-key when the weight is
    falling into this key, else the next on-key. A single off-key between two on-keys with a different IK
    frame gets a zero-weight twin 1 ms later that switches to the next target, so frames switch at w = 0."""
    names = lambda k: ['ik%s.%s' % (k, c) for c in ('x', 'y', 'z', 'rel', 'pt')]
    for k in ('L', 'R'):
        on = lambda i: ks[i][1].get('ik%s.w' % k, 0.0) > 1e-6
        if not any(on(i) for i in range(len(ks))):
            continue
        extra = []
        for i, key in enumerate(ks):
            if on(i):
                continue
            prev = next((j for j in range(i - 1, -1, -1) if on(j)), None)
            nxt = next((j for j in range(i + 1, len(ks)) if on(j)), None)
            src = prev if (prev is not None and (prev == i - 1 or nxt is None)) else nxt
            copy = lambda j, dst: [dst.__setitem__(n, ks[j][1][n]) if n in ks[j][1] else dst.pop(n, None)
                                   for n in names(k)]
            copy(src, key[1])
            if src == prev and nxt == i + 1 and any(ks[prev][1].get(n) != ks[nxt][1].get(n) for n in names(k)[3:]):
                twin = dict(key[1])
                copy(nxt, twin)
                extra.append((key[0] + 1e-3, twin) + tuple(key[2:]))
        ks.extend(extra)
        ks.sort(key=lambda kk: kk[0])


class FitTrack:
    """Track whose key poses are FK-fitted to their IK targets on first use (needs crowd_core.RIG)."""

    def __init__(self, keys, periodic=False):
        self.keys, self.periodic, self.tr = keys, periodic, None

    def __call__(self, t):
        if self.tr is None:
            ks = [(k[0], fit_params(k[1])) + tuple(k[2:]) for k in self.keys]
            inherit_fit(self.keys, ks)
            chans = {c for k in ks for c, v in k[1].items() if not isinstance(v, str)}
            for k in ks:                 # channels the fit introduced (arm twist) are 0 in the other keys
                for c in chans:
                    k[1].setdefault(c, 0.0)
            hold_ik_targets(ks)
            self.tr = Track(ks, periodic=self.periodic)
        return self.tr(t)
