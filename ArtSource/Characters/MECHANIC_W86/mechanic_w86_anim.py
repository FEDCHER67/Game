"""MECHANIC_W86 animation set v01: the wrench gags, work actions with the free left hand, attention, and the upgrade
performance. Original procedural keyframe animation (no mocap, no downloads, no paid generation), Blender 5.2 background.

  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/mechanic_w86_anim.py -- --review <dir> [--clips A,B]
  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/mechanic_w86_anim.py -- --final

Input: MECHANIC_W86_v01.blend (rig, LOD0 meshes; read only). --final writes Animations_v01/ here (never over existing
files): MECHANIC_W86_Anim_v01.blend (the model + all new actions + *_Face shape-key tracks + Grip_R), one rig-only FBX per
clip (<clip>.fbx, a single take named like the action, the export options of the shared Sausage Buddy clips), the Grip_R
clip FBX, clips_mechanic_v01.json (the manifest in the clips.json format, with event frames, face cues and roles) and
key-pose previews. --review renders key poses only into <dir>.

Method (as buddy_gags / the panic clip): every frame is a joint dict in the character frame (faces -Y, left = +X) on the
standing base pose = SAUSAGE_BUDDY_A_v04 'Idle' frame 1 (= the first frame of the game's Idle role, Idle_Stand_v04, so the
Animator cross-fades meet the same pose); arms by two-bone IK (buddy_gags.solve_arm) from animated targets (the right
fist centre with the wrench, the left palm); fingers by local poses (mech_rig.HAND_POSES): the right hand holds Grip_R in
every frame, the left hand changes pose. Channels are keyed sparsely and eased per segment; first and last frames are the
exact base pose. Every frame is grounded (lowest mesh point on z = 0, as the pipeline grounds its clips), so knee bends
keep the boots on the floor. No root motion: the game turns the NPC toward the van / player itself.
"""
import argparse, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix, Quaternion

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mech_rig as MR          # noqa: E402  (sets the SAUSAGE_BUDDY_01 path)
import buddy_anim as A         # noqa: E402
import buddy_gags as GG        # noqa: E402
import buddy_rig as RG         # noqa: E402

P = MR.P
FPS = 30
MODEL = HERE / 'MECHANIC_W86_v01.blend'
OUT_DIR = HERE / 'Animations_v01'
ARM_DOWN = 74.0                # A_v04 Idle frame 1 = Idle_Stand_v04 frame 1
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))
# right hand: fist centre (the wrench grip) relative to the wrist in the hand frame (hand dir, palm dir, jaw dir)
FIST_OFF = (0.098, 0.039, 0.004)
# left hand: palm contact point relative to the wrist
PALM_OFF = (0.062, 0.030, 0.0)


def V(*a):
    return Vector(a)


def nrm(*a):
    return Vector(a).normalized()

# ------------------------------------------------------------------ easing and sparse channels
def ease(kind, t):
    t = max(0.0, min(1.0, t))
    if kind == 'linear':
        return t
    if kind == 'snap':                       # fast out of the old pose, soft landing
        return 1 - (1 - t) ** 3
    if kind == 'in':
        return t * t
    if kind == 'over':                       # back-out: ~7 % overshoot, settles
        s = 1.6
        u = t - 1
        return 1 + u * u * ((s + 1) * u + s)
    if kind == 'hold':
        return 0.0 if t < 1 else 1.0
    return t * t * (3 - 2 * t)              # 'smooth'


class Channel:
    """Sparse keys [(frame, value, ease into this key)]; value: float, Vector, or an arm target dict."""
    def __init__(self, keys):
        self.keys = sorted(keys, key=lambda k: k[0])

    def at(self, f, mix):
        ks = self.keys
        if f <= ks[0][0]:
            return ks[0][1]
        for (f0, v0, _), (f1, v1, e) in zip(ks, ks[1:]):
            if f <= f1:
                return mix(v0, v1, ease(e, (f - f0) / max(1e-6, f1 - f0)))
        return ks[-1][1]


def mix_num(a, b, t):
    return a + (b - a) * t


def mix_vec(a, b, t):
    return Vector(a).lerp(Vector(b), t)


def frame_q(hd, pd):
    """Orthonormal frame (hand dir, palm dir, jaw dir) as a quaternion."""
    h = Vector(hd).normalized()
    p = Vector(pd)
    p = (p - h * p.dot(h)).normalized()
    j = h.cross(p)
    return Matrix((h, p, j)).transposed().to_quaternion()


def mix_arm(a, b, t):
    qa, qb = frame_q(a['hd'], a['pd']), frame_q(b['hd'], b['pd'])
    if qa.dot(qb) < 0:
        qb = -qb
    m = qa.slerp(qb, max(0.0, min(1.0, t))).to_matrix()      # positions may overshoot ('over'), rotations do not
    return {'pt': Vector(a['pt']).lerp(Vector(b['pt']), t), 'hd': m.col[0].copy(), 'pd': m.col[1].copy(),
            'pole': Vector(a['pole']).lerp(Vector(b['pole']), t).normalized()}


def mix_hand(a, b, t):
    return (a, b, t)

# ------------------------------------------------------------------ the rig context
class Ctx:
    def __init__(self, rig, rest):
        self.rig, self.rest = rig, rest
        self.J0 = A.idle_joints(0.0, ARM_DOWN)
        self.base = A.pose_from_joints(rig, rest, self.J0)
        self.stand = {s: self.arm_target_from_pose(self.base, s) for s in ('Left', 'Right')}
        self.locals = {(s, n): MR.hand_locals(rest, s, n) for s in ('Left', 'Right') for n in MR.HAND_POSES}

    def arm_target_from_pose(self, pose, side):
        M = pose[P + side + 'Hand']
        wrist = M.translation.copy()
        hd = M.col[1].xyz.normalized()
        qh = M.to_quaternion() @ self.rest[P + side + 'Hand'].to_quaternion().inverted()
        pd = (qh @ Vector((0, 0, -1))).normalized()
        jd = hd.cross(pd)
        off = FIST_OFF if side == 'Right' else PALM_OFF
        pt = wrist + hd * off[0] + pd * off[1] + jd * off[2]
        sh = pose[P + side + 'Arm'].translation
        el = pose[P + side + 'ForeArm'].translation
        pole = (el - (sh + wrist) / 2).normalized()
        return {'pt': pt, 'hd': hd, 'pd': pd, 'pole': pole}

    def wrist_of(self, side, t):
        hd = Vector(t['hd']).normalized()
        pd = Vector(t['pd'])
        pd = (pd - hd * pd.dot(hd)).normalized()
        jd = hd.cross(pd)
        off = FIST_OFF if side == 'Right' else PALM_OFF
        return Vector(t['pt']) - hd * off[0] - pd * off[1] - jd * off[2], hd, pd

    def hand_local(self, side, spec):
        a, b, t = spec
        la = self.locals[(side, a)] if isinstance(a, str) else a
        lb = self.locals[(side, b)] if isinstance(b, str) else b
        return MR.blend_locals(la, lb, t)


def arm(pt, hd, pd, pole):
    return {'pt': Vector(pt), 'hd': Vector(hd).normalized(), 'pd': Vector(pd).normalized(), 'pole': Vector(pole).normalized()}


def body_joints(spine, head, knees, shoulders=(0.0, 0.0)):
    """spine = (pitch +forward, yaw +to his left, roll +his left side down) deg over Spine/Spine1/Spine2;
    head = (yaw, pitch +down, roll) over Neck/Head; knees = bend deg; shoulders = (left, right) shrug deg."""
    J = {}
    p, y, r = spine
    Q = A.R((1, 0, 0), p) @ A.R((0, 0, 1), y) @ A.R((0, 1, 0), r)
    for b, w in (('Spine', 0.25), ('Spine1', 0.35), ('Spine2', 0.40)):
        J[b] = Quaternion().slerp(Q, w)
    hy, hp, hr = head
    J['Neck'] = A.R((1, 0, 0), hp * 0.6) @ A.R((0, 0, 1), hy * 0.62) @ A.R((0, 1, 0), hr * 0.5)
    J['Head'] = A.R((1, 0, 0), hp * 0.4) @ A.R((0, 0, 1), hy * 0.38) @ A.R((0, 1, 0), hr * 0.5)
    if knees:
        J = A.merge(J, GG.knees(knees))
    ls, rs = shoulders
    if ls:
        J['LeftShoulder'] = A.R((0, 1, 0), -ls)
    if rs:
        J['RightShoulder'] = A.R((0, 1, 0), rs)
    return J

# ------------------------------------------------------------------ a clip
class Clip:
    """name, length (frames), channels: spine/head (Vector deg), knees (deg), R/L (arm targets or 'STAND'),
    lhand ((pose_a, pose_b, t) or pose name), face [(shape, frame, value)], events {name: frame}."""
    def __init__(self, name, length, loop=False, role='', state='', note=''):
        self.name, self.length, self.loop, self.role, self.state, self.note = name, length, loop, role, state, note
        self.ch = {'spine': [(1, V(0, 0, 0), 'smooth')], 'head': [(1, V(0, 0, 0), 'smooth')], 'knees': [(1, 0.0, 'smooth')],
                   'shrug': [(1, V(0, 0, 0), 'smooth')], 'R': [(1, 'STAND', 'smooth')], 'L': [(1, 'STAND', 'smooth')],
                   'lhand': [(1, 'relaxed', 'smooth')], 'Rfine': [(1, V(0, 0, 0), 'smooth')], 'Lfine': [(1, V(0, 0, 0), 'smooth')],
                   'twist': [(1, 0.0, 'smooth')], 'ltwist': [(1, 0.0, 'smooth')]}
        self.face, self.events, self.cues = [], {}, []
        self.key_poses = []
        self.start_base, self.end_base = True, True

    def k(self, ch, f, v, e='smooth'):
        if isinstance(v, (tuple, list)) and ch in ('spine', 'head', 'shrug', 'Rfine', 'Lfine'):
            v = Vector(v)
        self.ch[ch].append((f, v, e))
        return self

    def pose(self, f, e='smooth', **kw):
        for ch, v in kw.items():
            self.k(ch, f, v, e)
        return self

    def last(self, ch, f):
        prev = [k for k in self.ch[ch] if k[0] <= f]
        return (prev[-1] if prev else self.ch[ch][0])[1]

    def move(self, f0, f1, e='smooth', **chans):
        """Pose-to-pose: every named channel holds its last key value until f0, then eases to the new value at f1."""
        for ch, v in chans.items():
            if isinstance(v, (tuple, list)) and ch in ('spine', 'head', 'shrug', 'Rfine', 'Lfine'):
                v = Vector(v)
            hold = self.last(ch, f0)
            self.ch[ch] = [k for k in self.ch[ch] if not (f0 <= k[0] <= f1)]
            self.ch[ch].append((f0, hold, 'linear'))
            self.ch[ch].append((f1, v, e))
            self.ch[ch].sort(key=lambda k: k[0])
        return self

    def end_stand(self, f0, e='smooth'):
        """Everything back to the base pose between f0 and the last frame."""
        L = self.length
        for ch, v in (('spine', V(0, 0, 0)), ('head', V(0, 0, 0)), ('knees', 0.0), ('shrug', V(0, 0, 0)), ('R', 'STAND'),
                      ('L', 'STAND'), ('lhand', 'relaxed'), ('Rfine', V(0, 0, 0)), ('Lfine', V(0, 0, 0)), ('twist', 0.0),
                      ('ltwist', 0.0)):
            last = max(k[0] for k in self.ch[ch])
            if last < f0:
                self.k(ch, f0, self.value(ch, f0), 'hold')
            self.k(ch, L, v, e)
        return self

    def value(self, ch, f):
        keys = self.ch[ch]
        mixer = {'R': None, 'L': None, 'lhand': None}.get(ch, 0)
        if ch in ('R', 'L', 'lhand'):
            prev = [k for k in keys if k[0] <= f]
            return (prev[-1] if prev else keys[0])[1]
        return Channel(keys).at(f, mix_vec if isinstance(keys[0][1], Vector) else mix_num)

    def evaluate(self, C, f):
        sp = Channel(self.ch['spine']).at(f, mix_vec)
        hd = Channel(self.ch['head']).at(f, mix_vec)
        kn = Channel(self.ch['knees']).at(f, mix_num)
        sh = Channel(self.ch['shrug']).at(f, mix_vec)
        J = A.merge(dict(C.J0), body_joints(sp, hd, kn, (sh.x, sh.y)))
        # gentle breathing (zero at both ends)
        env = math.sin(math.pi * (f - 1) / max(1, self.length - 1)) if not self.loop else 1.0
        br = math.sin(2 * math.pi * (f - 1) / (60.0 if not self.loop else self.length / max(1, round(self.length / 60)))) * 1.0 * env
        J = A.merge(J, {'Spine1': A.R((1, 0, 0), br * 0.4), 'Spine2': A.R((1, 0, 0), -br * 0.3)})
        for side, fine, tw in (('Right', 'Rfine', 'twist'), ('Left', 'Lfine', 'ltwist')):
            ch = 'R' if side == 'Right' else 'L'
            keys = [(fk, (C.stand[side] if v == 'STAND' else v), e) for fk, v, e in self.ch[ch]]
            t = Channel(keys).at(f, mix_arm)
            off = Channel(self.ch[fine]).at(f, mix_vec)
            twist = Channel(self.ch[tw]).at(f, mix_num)
            pt = Vector(t['pt']) + off
            hdv, pdv = Vector(t['hd']).normalized(), Vector(t['pd'])
            if twist:
                pdv = Quaternion(hdv, math.radians(twist)) @ pdv
            wrist, hdv, pdv = C.wrist_of(side, {'pt': pt, 'hd': hdv, 'pd': pdv})
            J = GG.solve_arm(C.rig, C.rest, J, side, wrist, t['pole'], hdv, pdv)
        desired = A.pose_from_joints(C.rig, C.rest, J)
        MR.set_hand(desired, C.rig, C.rest, 'Right', C.locals[('Right', 'grip')])
        hk = [(fk, (v if isinstance(v, tuple) else (v, v, 1.0)), e) for fk, v, e in self.ch['lhand']]
        hspec = Channel([(fk, v[1], e) for fk, v, e in hk]).at(f, lambda a, b, t: (a, b, t))
        if not isinstance(hspec, tuple):
            hspec = (hspec, hspec, 1.0)
        MR.set_hand(desired, C.rig, C.rest, 'Left', C.hand_local('Left', hspec))
        return desired

    def frames(self, C):
        out = {}
        for f in range(1, self.length + 1):
            out[f] = self.evaluate(C, f)
        base = dict(C.base)
        MR.set_hand(base, C.rig, C.rest, 'Right', C.locals[('Right', 'grip')])
        MR.set_hand(base, C.rig, C.rest, 'Left', C.locals[('Left', 'relaxed')])
        dev = 0.0
        if self.start_base and not self.loop:
            dev = max((out[1][b].translation - base[b].translation).length for b in base)
            out[1] = base
        if self.loop:
            out[self.length] = out[1]
        elif self.end_base:
            dev = max(dev, max((out[self.length][b].translation - base[b].translation).length for b in base))
            out[self.length] = base
        self.seam_dev_mm = round(dev * 1000, 2)
        return out

# ------------------------------------------------------------------ poses used by several clips
JAW_REACH = 0.174              # fist centre -> far edge of the big jaw along the jaw direction


def jaw_dir(t):
    hd = Vector(t['hd']).normalized()
    pd = Vector(t['pd'])
    pd = (pd - hd * pd.dot(hd)).normalized()
    return hd.cross(pd)


def jaw_tip(t, extra=0.0):
    return Vector(t['pt']) + jaw_dir(t) * (JAW_REACH + extra)


def scope_R():
    """The wrench held up beside his right cheek like a pistol sight: forearm upright, palm out, big jaw pointing
    forward (a hand pointing up with the palm out puts the shank front-back through the fist)."""
    return arm((-0.172, -0.360, 1.495), nrm(0.05, -0.06, 1), (-1, 0, 0), (-0.6, -0.4, -1))


def chest_R(dx=0.0, dz=0.0):
    """Wrench upright in front of the chest (the reference's three-quarter pose): forearm forward, palm in."""
    return arm((-0.115 + dx, -0.330, 1.070 + dz), nrm(0.18, -1, 0.05), (1, 0, 0), (-0.6, 0.3, -1))


def mouth_R():
    """Big jaw tipped back in front of his mouth, to blow on it like a smoking barrel."""
    return arm((-0.050, -0.300, 1.250), nrm(0.25, -1, 0.3), (1, 0, 0), (-0.6, 0.2, -1))


def hip_L():
    """Left fist on the hip, elbow out (confident akimbo)."""
    return arm((0.262, -0.035, 0.935), nrm(0, -0.55, -0.85), (-1, 0.1, 0), (1, 0.5, 0.1))


def belt_L():
    """Left thumb hooked into the belt at the hip, fingers hanging."""
    return arm((0.226, -0.150, 0.858), nrm(0.05, -0.2, -1), (-0.75, 0.62, 0), (0.9, 0.3, 0))


def steady_L():
    """Left hand under the right wrist (a serious two-handed aim)."""
    s = scope_R()
    hd, pd = s['hd'], s['pd']
    wrist = s['pt'] - hd * FIST_OFF[0] - pd * FIST_OFF[1] - jaw_dir(s) * FIST_OFF[2]
    return arm(wrist + Vector((0.036, -0.004, -0.052)), nrm(-0.6, -0.2, 0.75), (-0.5, 0.1, 0.85), (0.8, 0.0, -1))


def shoulder_R():
    """Wrench resting on the right shoulder, fist in front of the shoulder."""
    return arm((-0.200, -0.165, 1.150), nrm(0, -0.6, 0.8), (1, 0, 0), (-0.4, -0.2, -1))


def stand_R_bench():
    """Right fist with the wrench resting on the bench edge while the left hand works."""
    return arm((-0.200, -0.420, 0.965), nrm(0, -0.7, -0.7), (1, 0, 0), (-0.8, 0.3, -0.4))

# ------------------------------------------------------------------ the clips
def clip_gun_gag():
    c = Clip('Mech_Gag_WrenchGun_v01', 126, role='MechGag', state='Mech_Gag_WrenchGun',
             note='Raises the wrench like a pistol sight beside his right cheek, left fist on the hip, squints along it with a '
                  'mock-serious face, a silent "pew" mouth, blows on the jaw like a smoking barrel, smug nod, back to idle.')
    c.move(2, 10, spine=(3, 0, 0), head=(-6, 10, 0), knees=6, R=chest_R(dz=-0.12))
    c.move(12, 20, 'over', spine=(4, 6, -2), head=(-12, 6, -10), knees=0, R=scope_R(), L=hip_L(), lhand='fist')
    c.move(20, 32, Rfine=(0, 0, 0.004)).move(32, 44, Rfine=(0, -0.004, -0.003)).move(44, 49, Rfine=(0, 0, 0))
    c.move(49, 51, 'snap', Rfine=(0, -0.010, 0.016), head=(-12, 3, -10)).move(51, 58, Rfine=(0, 0, 0), head=(-12, 6, -10))
    c.move(62, 74, R=mouth_R(), head=(-2, 7, 0), spine=(3, 3, 0)).move(80, 86, head=(-1, 10, 0))
    c.move(88, 94, R=chest_R(dz=-0.03), head=(0, -4, 0), spine=(0, 0, 0))
    c.move(94, 99, head=(0, 12, 0)).move(99, 104, head=(0, -2, 0))
    c.end_stand(104)
    c.face = [('Blink_L', 16, 0.0), ('Blink_L', 20, 1.0), ('Blink_L', 60, 1.0), ('Blink_L', 64, 0.0),
              ('Worried', 17, 0.0), ('Worried', 22, 0.45), ('Worried', 48, 0.45), ('Worried', 56, 0.2), ('Worried', 62, 0.0),
              ('Surprised', 49, 0.0), ('Surprised', 51, 0.4), ('Surprised', 56, 0.0),
              ('Surprised', 70, 0.0), ('Surprised', 74, 0.45), ('Surprised', 84, 0.45), ('Surprised', 88, 0.0),
              ('Blink', 70, 0.0), ('Blink', 74, 0.55), ('Blink', 86, 0.55), ('Blink', 90, 0.0),
              ('Happy', 86, 0.0), ('Happy', 92, 0.85), ('Happy', 108, 0.85), ('Happy', 120, 0.0)]
    c.events = {'Raise': 20, 'Pew': 51, 'Blow': 74, 'Nod': 99}
    c.key_poses = [1, 10, 22, 40, 51, 78, 99, 126]
    return c


def clip_cock_nod():
    c = Clip('Mech_Gag_CockNod_v01', 108, role='MechGag', state='Mech_Gag_CockNod',
             note='Brings the wrench up in front of his chest, turns it to inspect both jaws, "cocks" it with a slap of the '
                  'left palm on the big jaw (the wrench jolts), then a smug slow nod with half-closed eyes; back to idle.')
    hold = chest_R(dz=-0.065)
    tip = jaw_tip(hold)
    lhd, lpd, lpole = nrm(-0.5, -1, -0.1), (0, 0, -1), (1, 0.2, -0.3)
    c.move(2, 14, R=hold, head=(-12, 14, 0), spine=(2, 4, 0))
    c.move(16, 24, twist=38.0, head=(-14, 14, 6)).move(24, 34, twist=-34.0, head=(-10, 14, -6)).move(34, 42, twist=0.0, head=(-12, 12, 0))
    c.move(40, 46, L=arm(tip + Vector((0.0, 0.0, 0.075)), lhd, lpd, lpole), lhand='flat')
    c.move(46, 50, 'in', L=arm(tip + Vector((0.0, 0.0, 0.028)), lhd, lpd, lpole))
    c.move(50, 51, 'snap', Rfine=(0, 0, -0.022), head=(-12, 16, 0)).move(51, 56, Rfine=(0, 0, 0.003)).move(56, 60, Rfine=(0, 0, 0))
    c.move(51, 58, L=arm(tip + Vector((0.07, 0.0, 0.09)), nrm(-0.3, -1, 0.2), lpd, lpole), lhand='relaxed')
    c.move(58, 70, L='STAND')
    c.move(60, 68, head=(0, -6, 4), R=chest_R(dx=-0.02, dz=-0.08), spine=(-2, 0, 0))
    c.move(70, 77, head=(0, 13, 4)).move(77, 86, head=(0, -3, 3))
    c.end_stand(90)
    c.face = [('Blink', 18, 0.0), ('Blink', 22, 0.35), ('Blink', 40, 0.35), ('Blink', 44, 0.0),
              ('Surprised', 49, 0.0), ('Surprised', 51, 0.5), ('Surprised', 56, 0.0),
              ('Happy', 60, 0.0), ('Happy', 68, 0.9), ('Happy', 92, 0.9), ('Happy', 104, 0.0),
              ('Blink', 62, 0.0), ('Blink', 68, 0.45), ('Blink', 90, 0.45), ('Blink', 98, 0.0)]
    c.events = {'Cock': 51, 'Nod': 77}
    c.key_poses = [1, 14, 24, 34, 48, 51, 77, 108]
    return c


def clip_inspect_part():
    c = Clip('Mech_Work_InspectPart_v01', 168, role='MechWork/Bench', state='Mech_Work_InspectPart',
             note='At the workbench (bench top ~0.92 m, 0.45 m in front): picks up a small part with the left hand, holds it up '
                  'to his eyes and turns it, taps it twice with the wrench, a satisfied nod, puts it back. No part prop in the '
                  'model: the left hand mimes it (a small prop on mixamorig:LeftHand can be shown between PartUp and PartDown).')
    bench = V(0.110, -0.450, 0.935)
    reach = arm(bench + V(0, 0, 0.035), nrm(0.05, -0.55, -0.85), (0, 0, -1), (1, 0.2, -0.2))
    grab = arm(bench, nrm(0.05, -0.55, -0.85), (0, 0, -1), (1, 0.2, -0.2))
    held = arm(V(0.060, -0.355, 1.320), nrm(-0.35, -0.45, 0.82), (-0.85, 0.35, 0.2), (1, 0.3, -0.6))
    part = held['pt'] + held['hd'] * 0.05
    tap_o = arm(V(0, 0, 0), nrm(0.35, -1, 0.1), (1, 0, 0), (-0.6, 0.2, -1))
    tapR = arm(part - jaw_dir(tap_o) * (JAW_REACH + 0.022), tap_o['hd'], tap_o['pd'], tap_o['pole'])
    c.move(4, 16, spine=(17, 4, 0), knees=8, head=(4, 26, 0), L=reach, lhand='cup')
    c.move(16, 22, L=grab, lhand='pinch')
    c.move(24, 40, spine=(-1, 6, 0), knees=0, head=(10, 4, 3), L=held)
    c.move(40, 48, ltwist=35.0, head=(12, 6, 7)).move(48, 58, ltwist=-30.0, head=(9, 3, -5)).move(58, 66, ltwist=0.0, head=(10, 5, 2))
    c.move(64, 76, R=tapR)
    c.move(77, 80, 'in', Rfine=(0, 0, 0.018)).move(80, 84, Rfine=(0, 0, 0)).move(85, 88, 'in', Rfine=(0, 0, 0.018)).move(88, 92, Rfine=(0, 0, 0))
    c.move(94, 104, R='STAND', head=(6, -4, 0), shrug=(6, 6, 0)).move(104, 110, head=(6, 9, 0), shrug=(0, 0, 0)).move(110, 116, head=(4, 2, 0))
    c.move(118, 130, spine=(17, 4, 0), knees=8, head=(4, 26, 0), L=grab)
    c.move(130, 136, L=reach, lhand='cup')
    c.end_stand(140)
    c.face = [('Blink', 30, 0.0), ('Blink', 40, 0.35), ('Blink', 66, 0.35), ('Blink', 72, 0.0),
              ('Worried', 34, 0.0), ('Worried', 42, 0.3), ('Worried', 66, 0.3), ('Worried', 74, 0.0),
              ('Happy', 98, 0.0), ('Happy', 106, 0.6), ('Happy', 124, 0.6), ('Happy', 136, 0.0)]
    c.events = {'PartUp': 22, 'Tap': 80, 'Tap2': 88, 'PartDown': 130}
    c.key_poses = [1, 16, 22, 48, 58, 80, 106, 130, 168]
    return c


def clip_wipe():
    c = Clip('Mech_Work_WipeBench_v01', 186, role='MechWork/Shelf', state='Mech_Work_WipeBench',
             note='At a shelf / bench top (~0.92 m, 0.45 m in front): pats the rag in his back pocket, wipes the surface in three '
                  'circles with the flat left hand (right fist with the wrench resting on the bench edge), looks at his palm, '
                  'wipes the hand on his trouser leg twice; back to idle. The rag mesh stays on the pocket (no extra prop).')
    rag = arm(V(0.135, 0.150, 0.810), nrm(0.1, 0.3, -1), (0, -1, 0), (1, 0.6, 0))
    centre = V(0.090, -0.455, 0.940)
    flat = lambda p: arm(p, nrm(-0.05, -1, -0.25), (0, 0, -1), (1, 0.3, -0.3))
    look = arm(V(0.110, -0.320, 1.230), nrm(-0.2, -0.5, 0.85), (0, 0.85, 0.5), (1, 0.2, -0.6))
    thigh = lambda z: arm(V(0.150, -0.125, z), nrm(0, -0.15, -1), (0, 1, 0), (1, 0.4, 0))
    c.move(3, 14, L=rag, lhand='cup', spine=(0, 12, -2), head=(28, 6, 0))
    c.move(16, 19, 'snap', Lfine=(0, 0.012, 0)).move(19, 23, Lfine=(0, 0, 0))
    c.move(24, 34, spine=(15, 0, 0), knees=8, head=(2, 24, 0), L=flat(centre + V(0.06, 0, 0)), lhand='flat', R=stand_R_bench())
    c.k('Lfine', 36, V(0, 0, 0), 'linear')
    for loop in range(3):
        for q in range(1, 9):
            a = 2 * math.pi * q / 8
            c.k('Lfine', 36 + loop * 22 + round(q * 22 / 8), V(0.06 * math.cos(a) - 0.06, 0.045 * math.sin(a), 0.0), 'smooth' if q in (1, 8) else 'linear')
    c.move(106, 118, L=look, R='STAND', spine=(0, 2, 0), knees=0, head=(8, 14, 0))
    c.move(122, 132, L=thigh(0.700), head=(6, 20, 0), spine=(4, 0, 0)).move(132, 140, 'linear', L=thigh(0.560))
    c.move(140, 146, L=thigh(0.690)).move(146, 154, 'linear', L=thigh(0.560)).move(154, 160, head=(0, 4, 0))
    c.end_stand(160)
    c.face = [('Worried', 112, 0.0), ('Worried', 118, 0.5), ('Worried', 128, 0.5), ('Worried', 134, 0.0),
              ('Blink', 40, 0.0), ('Blink', 44, 0.25), ('Blink', 100, 0.25), ('Blink', 104, 0.0)]
    c.events = {'PatRag': 19, 'WipeStart': 36, 'WipeEnd': 102, 'HandWipe': 140}
    c.key_poses = [1, 14, 36, 47, 80, 118, 140, 186]
    return c


def clip_check_bay():
    c = Clip('Mech_Work_CheckBay_v01', 168, role='MechWork/BaySide', state='Mech_Work_CheckBay',
             note='At the side of the repair bay (outside the vehicle/lift footprint): bends down with the left hand on his '
                  'knee, knocks three times with the wrench at knee height in front of him (a wheel / a panel), listens with '
                  'his head tilted, a satisfied nod, straightens up and pats his thigh; back to idle.')
    low = arm(V(-0.215, -0.400, 0.600), nrm(0, -0.25, -1), (1, 0, 0), (-1, 0.6, 0))
    knee = arm(V(0.135, -0.200, 0.550), nrm(0, -1, -0.35), (0, 0, -1), (1, 0.4, 0.2))
    c.move(4, 22, spine=(24, 4, 0), knees=28, head=(0, 16, 0), R=low, L=knee, lhand='cup')
    for f in (44, 56, 68):
        c.move(f - 7, f - 3, Rfine=(0, 0.022, 0.012)).move(f - 3, f, 'in', Rfine=(0, -0.014, 0.0)).move(f, f + 5, Rfine=(0, 0, 0))
    c.move(74, 80, head=(-6, 18, 12)).move(98, 104, head=(0, 22, 0)).move(104, 110, head=(0, 10, 0))
    c.move(112, 128, spine=(0, 0, 0), knees=0, head=(0, 0, 0), R='STAND',
           L=arm(V(0.150, -0.120, 0.640), nrm(0, -0.15, -1), (0, 1, 0), (1, 0.4, 0)), lhand='flat')
    c.move(128, 133, Lfine=(0, -0.022, 0.03)).move(133, 135, 'in', Lfine=(0, 0, 0))
    c.end_stand(142)
    c.face = [('Worried', 70, 0.0), ('Worried', 78, 0.35), ('Worried', 98, 0.35), ('Worried', 104, 0.0),
              ('Blink_R', 78, 0.0), ('Blink_R', 82, 0.4), ('Blink_R', 98, 0.4), ('Blink_R', 102, 0.0),
              ('Happy', 102, 0.0), ('Happy', 110, 0.6), ('Happy', 130, 0.6), ('Happy', 142, 0.0)]
    c.events = {'Knock': 44, 'Knock2': 56, 'Knock3': 68, 'Nod': 104}
    c.key_poses = [1, 22, 41, 44, 84, 104, 135, 168]
    return c


ATTEND = dict(R=shoulder_R(), L=belt_L(), lhand='relaxed', head=V(0, -3, 0), spine=V(-2, 0, 0))


def clip_attend_enter():
    c = Clip('Mech_Attend_Enter_v01', 24, role='MechAttend/Enter', state='Mech_Attend_Enter',
             note='Notices the player (brows up), straightens, puts the wrench on his right shoulder and hooks his left thumb in '
                  'the belt. Ends on the first frame of Mech_Attend_Loop_v01.')
    c.move(2, 8, 'snap', head=(0, -6, 0), spine=(-3, 0, 0))
    c.move(6, 18, 'over', R=ATTEND['R'], L=ATTEND['L'])
    c.move(8, 18, head=ATTEND['head'], spine=ATTEND['spine'])
    c.face = [('Surprised', 2, 0.0), ('Surprised', 7, 0.35), ('Surprised', 16, 0.0)]
    c.key_poses = [1, 8, 14, 24]
    c.end_base = False
    return c


def clip_attend_loop():
    c = Clip('Mech_Attend_Loop_v01', 120, loop=True, role='MechAttend/Loop', state='Mech_Attend_Loop',
             note='Listening to the player: wrench on the shoulder, thumb in the belt, slow head tilts and blinks, at 2.2 s the '
                  'wrench lifts off the shoulder and taps it once; seamless loop (frame 120 = frame 1).')
    for ch, v in ATTEND.items():
        c.ch[ch] = [(1, v, 'smooth')]
    c.move(1, 30, head=(4, -2, 5)).move(30, 56, head=(-3, -4, -3)).move(76, 96, head=(2, -1, 3)).move(96, 120, head=ATTEND['head'])
    c.move(56, 63, Rfine=(0, -0.01, 0.035)).move(63, 68, 'in', Rfine=(0, 0, 0)).move(68, 72, Rfine=(0, 0, 0.004)).move(72, 76, Rfine=(0, 0, 0))
    c.move(1, 60, spine=(-1, 1, 0)).move(60, 120, spine=ATTEND['spine'])
    c.face = [('Blink', 38, 0.0), ('Blink', 40, 1.0), ('Blink', 43, 0.0), ('Blink', 98, 0.0), ('Blink', 100, 1.0), ('Blink', 103, 0.0)]
    c.events = {'ShoulderTap': 68}
    c.key_poses = [1, 30, 63, 68, 96]
    return c


def clip_attend_exit():
    c = Clip('Mech_Attend_Exit_v01', 21, role='MechAttend/Exit', state='Mech_Attend_Exit',
             note='From the attention pose (Mech_Attend_Loop_v01 frame 1) back to the standing idle.')
    for ch, v in ATTEND.items():
        c.ch[ch] = [(1, v, 'smooth')]
    c.end_stand(3)
    c.key_poses = [1, 10, 21]
    c.start_base = False
    return c


def clip_upgrade():
    c = Clip('Mech_Upgrade_Perform_v01', 138, role='MechUpgrade', state='Mech_Upgrade_Perform',
             note='Upgrade performance (the game turns him to face the van first): "watch this" nod, snaps the wrench up as a '
                  'sight with the left hand under his wrist, aims ~1 s (squint), a tiny recoil-free flick at Poof (the van '
                  'puff and the purchased change happen on that event, driven by the server), lowers it, blows on the jaw, '
                  'pleased grin, nod and a left thumbs-up; back to idle.')
    thumbs = arm(V(0.170, -0.300, 1.090), nrm(-0.2, -1, 0.3), (-1, 0, 0), (1, 0.2, -1))
    c.move(2, 8, head=(0, 8, 0), R=chest_R(dz=-0.06), spine=(-2, 0, 0)).move(8, 12, head=(0, -2, 0))
    c.move(13, 20, 'over', spine=(4, 6, -2), head=(-12, 6, -10), R=scope_R(), L=steady_L(), lhand='cup')
    c.move(20, 34, Rfine=(0, -0.003, 0.002)).move(34, 44, Rfine=(0, 0.002, -0.002)).move(44, 50, Rfine=(0, 0, 0))
    c.move(50, 52, 'snap', Rfine=(0, -0.008, 0.010), Lfine=(0, -0.006, 0.008)).move(52, 57, Rfine=(0, 0, 0), Lfine=(0, 0, 0))
    c.move(56, 64, L='STAND', lhand='relaxed')
    c.move(60, 70, R=mouth_R(), spine=(3, 3, 0), head=(-2, 7, 0)).move(78, 84, head=(-1, 10, 0))
    c.move(86, 92, R=chest_R(dz=-0.03), L=thumbs, lhand='thumbs_up', head=(0, -4, 0), spine=(-3, 0, 0))
    c.move(92, 97, head=(0, 12, 0)).move(97, 102, head=(0, -2, 0)).move(102, 107, head=(0, 10, 0)).move(107, 112, head=(0, 0, 0))
    c.end_stand(114)
    c.face = [('Happy', 4, 0.0), ('Happy', 9, 0.4), ('Happy', 16, 0.0),
              ('Blink_L', 16, 0.0), ('Blink_L', 21, 1.0), ('Blink_L', 54, 1.0), ('Blink_L', 58, 0.0),
              ('Worried', 18, 0.0), ('Worried', 23, 0.4), ('Worried', 50, 0.4), ('Worried', 55, 0.0),
              ('Surprised', 51, 0.0), ('Surprised', 53, 0.4), ('Surprised', 60, 0.0),
              ('Surprised', 68, 0.0), ('Surprised', 72, 0.45), ('Surprised', 82, 0.45), ('Surprised', 86, 0.0),
              ('Happy', 84, 0.0), ('Happy', 92, 1.0), ('Happy', 118, 1.0), ('Happy', 132, 0.0)]
    c.events = {'AimStart': 20, 'Poof': 52, 'Blow': 72, 'Pleased': 92, 'Done': 130}
    c.key_poses = [1, 8, 22, 40, 52, 74, 97, 138]
    return c


def all_clips():
    return [clip_gun_gag(), clip_cock_nod(), clip_inspect_part(), clip_wipe(), clip_check_bay(), clip_attend_enter(),
            clip_attend_loop(), clip_attend_exit(), clip_upgrade()]

# ------------------------------------------------------------------ build
def ground_and_key(C, clip, frames, meshes, scene):
    act = RG.key_frames(C.rig, C.rest, frames, clip.name)
    fs = sorted(frames)
    lows = dict(zip(fs, RG.ground_offset(scene, C.rig, act, meshes, fs)))
    bpy.data.actions.remove(act)
    if clip.loop:          # one offset for the whole loop (seamless)
        sh = {f: -min(lows.values()) for f in fs}
    else:
        sh = {f: -lows[f] for f in fs}
    act = RG.key_frames(C.rig, C.rest, {f: {b: Matrix.Translation((0, 0, sh[f])) @ m for b, m in frames[f].items()} for f in fs},
                        clip.name)
    return act, (round(min(sh.values()), 4), round(max(sh.values()), 4))


def build(names=None):
    rig, rest = MR.open_model(MODEL)
    scene = bpy.context.scene
    scene.render.fps = FPS
    for o in bpy.data.objects:
        if o.name == 'Prop_Phone':
            o.hide_render = True
            o.hide_viewport = True
    C = Ctx(rig, rest)
    meshes = MR.meshes_lod0()
    face = bpy.data.objects['Face']
    grip = MR.grip_track(rig, rest)
    out = []
    clips = [c for c in all_clips() if not names or c.name in names or c.name.rsplit('_v', 1)[0] in names]
    for c in clips:
        frames = c.frames(C)
        act, ground = ground_and_key(C, c, frames, meshes, scene)
        fa = GG.face_action(face, c.name + '_Face', c.face) if c.face else None
        out.append((c, act, fa, ground))
        print(f'[ANIM] {c.name} frames {c.length} seam_dev_mm {c.seam_dev_mm} ground {ground}')
    return rig, rest, scene, grip, out


def preview(rig, scene, built, folder, sheet_name=None):
    """Key-pose renders per clip (3/4 front and side) + one sheet per clip."""
    import subprocess
    import buddy_render as RD
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = 24
    face = bpy.data.objects['Face']
    MR.clear_nla(rig)
    sheets = []
    for c, act, fa, _ in built:
        rig.animation_data.action = act
        sk = face.data.shape_keys
        sk.animation_data_create()
        sk.animation_data.action = fa
        files = []
        for f in c.key_poses:
            scene.frame_set(f)
            hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
            tgt = Vector((hips.x, hips.y, 0.95))
            for tag, off in (('q', Vector((-1.55, -2.55, 0.45))), ('l', Vector((1.75, -2.45, 0.40))), ('s', Vector((-2.9, -0.35, 0.35)))):
                p = folder / c.name / f'{c.name}_f{f:03d}_{tag}.png'
                RD.shot(scene, cam, p, tgt + off, tgt, lens=50, res=(420, 560))
                files.append(p)
        sheet = folder / f'{c.name}_keyposes.png'
        labels = []
        for f in c.key_poses:
            ev = [k for k, v in c.events.items() if v == f]
            labels += [f'f{f} 3/4 R' + (f' {ev[0]}' if ev else ''), f'f{f} 3/4 L', f'f{f} side']
        cmd = ['magick', 'montage']
        for p, lab in zip(files, labels):
            cmd += ['-label', lab, str(p)]
        cmd += ['-tile', f'{min(9, len(files))}x', '-geometry', '210x280+2+2', '-pointsize', '13', '-title', c.name, str(sheet)]
        subprocess.run(cmd, check=False)
        sheets.append(sheet)
        sk.animation_data.action = None
    return sheets


def export_all(built, grip, out_dir):
    """One rig-only FBX per clip: reopen the saved .blend, keep only that action, export it as the single take."""
    blend = out_dir / 'MECHANIC_W86_Anim_v01.blend'
    names = [c.name for c, *_ in built] + ['Grip_R']
    for name in names:
        fbx = out_dir / (('MECHANIC_W86_' if name == 'Grip_R' else '') + name + ('_v01' if name == 'Grip_R' else '') + '.fbx')
        if fbx.exists():
            sys.exit(f'Refusing to overwrite {fbx}')
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        rig = bpy.data.objects[MR.RIG]
        MR.clear_nla(rig)
        act = bpy.data.actions[name]
        for a in list(bpy.data.actions):
            if a is not act:
                bpy.data.actions.remove(a)
        scene = bpy.context.scene
        rig.animation_data.action = act
        f0, f1 = (int(round(x)) for x in act.frame_range)
        scene.frame_start, scene.frame_end = f0, max(f1, f0 + 1)
        scene.frame_set(f0)
        bpy.ops.object.select_all(action='DESELECT')
        rig.select_set(True)
        bpy.context.view_layer.objects.active = rig
        bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'}, add_leaf_bones=False,
                                 use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_actions=True,
                                 bake_anim_use_nla_strips=False, bake_anim_step=.5, bake_anim_simplify_factor=0,
                                 axis_forward='-Z', axis_up='Y', apply_unit_scale=True, use_mesh_modifiers=False)
        print('[EXPORT]', fbx.name)


def manifest(built, out_dir):
    clips = []
    for c, act, fa, ground in built:
        clips.append({
            'role': c.role, 'state': c.state, 'file': c.name + '.fbx', 'take': c.name, 'source': f'ArtSource/Characters/MECHANIC_W86/Animations_v01/{c.name}.fbx',
            'loop': c.loop, 'frames': [1, c.length], 'fps': FPS, 'seconds': round((c.length - 1) / FPS, 4),
            'events': {k: {'frame': v, 'seconds': round((v - 1) / FPS, 4), 'fraction': round((v - 1) / (c.length - 1), 4)} for k, v in c.events.items()},
            'face_cues': [{'shape': s, 'frame': f, 'seconds': round((f - 1) / FPS, 4), 'value': v} for s, f, v in sorted(c.face, key=lambda k: (k[1], k[0]))],
            'face_track_blend': (c.name + '_Face') if c.face else None,
            'grounding_hips_shift_m': ground, 'seam_deviation_mm': c.seam_dev_mm, 'note': c.note})
    return clips


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--review', default=None)
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--clips', default='')
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    names = [n for n in args.clips.split(',') if n]
    if args.final:
        OUT_DIR.mkdir(exist_ok=True)
        blend = OUT_DIR / 'MECHANIC_W86_Anim_v01.blend'
        man = OUT_DIR / 'clips_mechanic_v01.json'
        for p in (blend, man):
            if p.exists():
                sys.exit(f'Refusing to overwrite {p}')
    rig, rest, scene, grip, built = build(names)
    if args.review:
        preview(rig, scene, built, args.review)
        return
    if args.final:
        data = {'comment': 'MECHANIC_W86 clips v01 (Blender, Claude 2026-10-29). Format follows Assets/OnlyVolunteers/Characters/'
                           'SausageBuddy/Animations/clips.json (role, state, file, take, loop, seconds, events) plus frames, face '
                           'cues (blend shapes of the Face mesh: Blink, Blink_L, Blink_R, Surprised, Worried, Happy; the game\'s '
                           'face script plays them, as for the other Sausage Buddy clips) and notes. 30 fps, no root motion, '
                           'generic rig Buddy_Rig_Mixamo65 (same bones and rest as every Sausage Buddy). Every clip starts and '
                           'ends on Idle_Stand_v04 frame 1 (except the attention loop and its enter/exit). The right hand holds '
                           'Grip_R in every frame; add the Grip_R layer for the shared clips (Walk_v04, Idle_Stand_v04, ...).',
                'grip_clip': {'file': 'MECHANIC_W86_Grip_R_v01.fbx', 'take': 'Grip_R', 'frames': [1, 2],
                              'keyed_bones': MR.hand_children(rig, 'Right')},
                'clips': manifest(built, OUT_DIR)}
        MR.clear_nla(rig)
        rig.animation_data.action = bpy.data.actions['Idle'] if 'Idle' in bpy.data.actions else None
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / 'MECHANIC_W86_Anim_v01.blend'))
        sheets = preview(rig, scene, built, OUT_DIR / 'Previews')
        (OUT_DIR / 'clips_mechanic_v01.json').write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding='utf-8')
        export_all(built, grip, OUT_DIR)


if __name__ == '__main__':
    main()
