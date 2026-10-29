"""MECHANIC_W86 animation set v02: the two-hand wrench aim (Fedya's reference, 2026-10-29) for Mech_Gag_WrenchGun and
Mech_Upgrade_Perform. Original procedural keyframe animation, Blender 5.2 background, same method and rig as v01
(mechanic_w86_anim.py, imported here; v01 files are read only).

  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/mechanic_w86_anim_v02.py -- --review <dir>
  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/mechanic_w86_anim_v02.py -- --final

--final writes Animations_v02/ (never over existing files): MECHANIC_W86_Anim_v02.blend (model + the two v02 actions +
*_Face shape-key tracks + Grip_R), Mech_Gag_WrenchGun_v02.fbx, Mech_Upgrade_Perform_v02.fbx (rig-only, one take each, the
v01 export options), clips_mechanic_v02.json (the full manifest: the seven unchanged v01 clips copied as they are + the
two v02 entries), contact/clearance measurements (aim_check_v02.json) and preview renders (Previews/).

The pose (why it looks like this): the wrench is skinned rigidly to mixamorig:RightHand with its shank through the fist
(bone X = shank axis, fist centre at bone (0.004, 0.099, 0.037)), so the right forearm can only stand roughly square to
the wrench. With this rig's short arms (upper arm 0.23 m, forearm 0.21 m) a search over fist positions, wrench rolls and
elbow angles (wrist deviation/flexion and forearm roll limits, wrench/arm/torso clearance, the backward axis meeting the
arm, the left arm clear of the chest) found solutions only with the SMALL jaw in front and the big (rear) jaw toward the
right shoulder: the right fist on the rear part next to the big jaw in front of the right chest, elbow down and out
(~16 cm below the shoulder), the wrist strongly bent (about 40 deg toward the thumb, 60 deg flexion: the cartoon stretch
this rig needs), the upper body turned ~16 deg to his right and the shoulders brought forward (a bladed rifle stance) so
the wrench points along the character's forward = at the van (the brain turns the root toward the van's aim point), the
head turned back to look along it. Measured conflict (see the report): the 2.8 cm of bare shank in front of the fist vs
an 11.5 cm wide mitten palm, so the left palm sits under the neck of the front jaw, right next to the fist.
The left palm is solved every frame from the wrench itself (two passes: right arm -> RightHand matrix -> the support point
under the shank/front jaw -> left arm IK), so it stays on the wrench through the hold and the transitions.
"""
import argparse, json, math, sys, subprocess
from pathlib import Path
import bpy
from mathutils import Vector, Matrix, Quaternion

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mechanic_w86_anim as M  # noqa: E402  (v01 helpers; sets the SAUSAGE_BUDDY_01 path)
import mech_rig as MR          # noqa: E402
import buddy_anim as A         # noqa: E402
import buddy_gags as GG        # noqa: E402
import buddy_rig as RG         # noqa: E402

P = MR.P
FPS = 30
OUT_DIR = HERE / 'Animations_v02'
V01_DIR = HERE / 'Animations_v01'
V, nrm, arm, Channel, mix_arm, mix_vec, mix_num = M.V, M.nrm, M.arm, M.Channel, M.mix_arm, M.mix_vec, M.mix_num

# ------------------------------------------------------------------ wrench geometry (RightHand bone space, measured)
AXIS_Y, AXIS_Z = 0.099, 0.037       # shank axis: (x, 0.099, 0.037) along bone +X (+X = thumb side = big jaw)
BIG_TIP, SMALL_TIP = 0.1776, -0.1427
SMALL_JAW = (-0.143, -0.086)        # small open jaw (front in the aim)
BIG_JAW = (0.109, 0.178)            # big open jaw (rear in the aim)
FIST_X = (-0.058, 0.081)            # the posed Grip_R fist along the shank (pinky edge .. thumb tip)
SUPPORT_X = -0.116                  # left palm centre along the shank (under the front jaw's neck; see the report)
# finger pose of the supporting left hand (palm up, fingers curled up the far side, thumb along the near side)
MR.HAND_POSES['support'] = dict(fingers=(30, 44, 30), thumb=(((1, 0, 0), 26), ((0, 0, 1), 10), ((1, 0, 0), 12)))

# ------------------------------------------------------------------ the aim stance
AIM = dict(spine=(4.4, -16.5, -0.6),           # pitch forward, yaw to his right (bladed stance), roll (+ left side down)
           head=(15.0, 9.0, -7.0),            # yaw back toward the van, pitch down to the tool, tilt toward it
           knees=4.0, shrug=(0.0, 3.0, 0.0),
           protract=(25.0, 20.0),             # shoulders (clavicles) forward, left / right, deg
           fist=(-0.148, -0.263, 1.138),       # right fist centre (character frame)
           psi=279.1,                          # roll of the right hand about the wrench axis (see aim_R)
           elbow=(-0.267, -0.055, 1.049),      # where the right elbow should go (pole)
           pitch=0.0, yaw=-1.0)                # wrench pitch (+ up) and yaw (+ toward his left) in the character frame
# found by a pose search on the posed meshes (skin/cloth clearance, wrist limits, the backward axis on the right arm,
# the left palm on the wrench): see the module docstring and Animations_v02/aim_check_v02.json
SUP = dict(lyaw=42.8, lshift=0.0, x=-0.125, pole=(0.776, 0.307, -0.981), twist_share=0.6, lift=-0.0055)


def stance_joints(C, spine, head, knees, shrug, protract):
    J = A.merge(dict(C.J0), M.body_joints(spine, head, knees, tuple(shrug)[:2]))
    lp, rp = protract
    if lp:
        J = A.merge(J, {'LeftShoulder': A.R((0, 0, 1), -lp)})
    if rp:
        J = A.merge(J, {'RightShoulder': A.R((0, 0, 1), rp)})
    return J


def wrench_dirs(pitch=0.0, yaw=0.0):
    p, y = math.radians(pitch), math.radians(yaw)
    fwd = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))).normalized()
    e1 = Vector((0, 0, 1))
    e1 = (e1 - fwd * e1.dot(fwd)).normalized()
    e2 = fwd.cross(e1)
    return fwd, e1, e2


def aim_R(C, spec=None, dfist=(0, 0, 0), dpsi=0.0):
    """Right-arm target of the aim: the fist centre, the hand frame from the wrench direction and roll psi (hd = hand
    direction; jd = thumb side = big jaw = backward), the pole toward the wanted elbow."""
    spec = spec or AIM
    fwd, e1, e2 = wrench_dirs(spec['pitch'], spec['yaw'])
    r = math.radians(spec['psi'] + dpsi)
    hd = (e1 * math.cos(r) + e2 * math.sin(r)).normalized()
    jd = -fwd
    pd = jd.cross(hd)
    F = Vector(spec['fist']) + Vector(dfist)
    J = stance_joints(C, spec['spine'], spec['head'], spec['knees'], spec['shrug'], spec['protract'])
    d0 = A.pose_from_joints(C.rig, C.rest, J)
    S = d0[P + 'RightArm'].translation
    W = F - jd * 0.004 - hd * 0.0988 - pd * 0.0369
    pole = (Vector(spec['elbow']) - (S + W) / 2).normalized()
    return arm(F, hd, pd, pole)


def share_twist(C, J, side, k):
    """Move a share k of the hand's twist about the forearm axis into the forearm bone (less candy-wrap at the wrist;
    the world pose of the hand is unchanged)."""
    if not k:
        return J
    d = A.pose_from_joints(C.rig, C.rest, J)
    f = (d[P + side + 'Hand'].translation - d[P + side + 'ForeArm'].translation).normalized()
    q = J[side + 'Hand']
    v = Vector((q.x, q.y, q.z))
    ang = 2 * math.atan2(v.dot(f), q.w)
    ang = (ang + math.pi) % (2 * math.pi) - math.pi
    Rk = Quaternion(f, k * ang)
    J = dict(J)
    J[side + 'ForeArm'] = Rk @ J[side + 'ForeArm']
    J[side + 'Hand'] = q @ Rk.inverted()
    return J


# ------------------------------------------------------------------ the left support, solved from the wrench
class Wrench:
    def __init__(self, rig, rest):
        o = bpy.data.objects['Wrench_RightHand']
        Mi = rest[P + 'RightHand'].inverted()
        self.v = [Mi @ (o.matrix_world @ v.co) for v in o.data.vertices]      # bone space

    def slice(self, x0, x1):
        return [v for v in self.v if x0 <= v.x <= x1]


def support_target(Mr, wr, lyaw=None, lshift=None, lift=None, x=None, approach=(0.0, 0.0, 0.0)):
    """Left palm target from the RightHand armature matrix Mr: the lowest point of the wrench under the shank axis at
    bone x (max over a 3 cm slice, continuous in the pose), palm facing up into it, fingers across the wrench toward his
    right (lyaw deg toward the front), shifted along the hand by lshift. approach = offset (m) in (across, along, down)
    for the placing / release motion."""
    lyaw = SUP['lyaw'] if lyaw is None else lyaw
    lshift = SUP['lshift'] if lshift is None else lshift
    lift = SUP.get('lift', 0.0) if lift is None else lift
    x = SUP['x'] if x is None else x
    R3 = Mr.to_3x3()
    ex, ey, ez = (R3.col[0]).normalized(), (R3.col[1]).normalized(), (R3.col[2]).normalized()
    fwd = -ex                                             # small jaw = front
    centre = Mr @ Vector((x, AXIS_Y, AXIS_Z))
    dn = Vector((0, 0, -1))
    dn = (dn - fwd * dn.dot(fwd)).normalized()
    h = max((Mr @ v - centre).dot(dn) for v in wr.slice(x - 0.015, x + 0.015))
    contact = centre + dn * (h + lift)
    pd = -dn
    across = fwd.cross(pd).normalized()                   # toward his right
    hd = (Quaternion(pd, math.radians(lyaw)) @ across).normalized()    # + lyaw: fingers toward the front
    a = Vector(approach)
    pt = contact + hd * lshift + across * a.x + fwd * a.y + dn * a.z
    return {'pt': pt, 'hd': hd, 'pd': pd, 'pole': nrm(*SUP['pole']), 'contact': contact, 'fwd': fwd}


# ------------------------------------------------------------------ a clip with the attached left hand
class Clip2(M.Clip):
    """v01 Clip + channels Lsup (0..1: the left target blends from L to the wrench support) and Lapp (approach offset
    across/along/down the wrench, m), solved in two passes so the left hand follows the wrench exactly."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.ch['Lsup'] = [(1, 0.0, 'smooth')]
        self.ch['Lapp'] = [(1, V(0, 0, 0), 'smooth')]
        self.ch['protract'] = [(1, V(0, 0, 0), 'smooth')]

    def k(self, ch, f, v, e='smooth'):
        if isinstance(v, (tuple, list)) and ch in ('Lapp', 'protract'):
            v = Vector(tuple(v) + (0.0,) * (3 - len(v)))
        return super().k(ch, f, v, e)

    def move(self, f0, f1, e='smooth', **chans):
        """v01 move(), but a key already at f0 keeps its own ease (v01 turned it into 'linear', so chained moves
        lost their ease-in and started with a jump)."""
        for ch, v in chans.items():
            if isinstance(v, (tuple, list)) and ch in ('spine', 'head', 'shrug', 'Rfine', 'Lfine', 'Lapp', 'protract'):
                v = Vector(tuple(v) + (0.0,) * (3 - len(v)))
            at0 = [k for k in self.ch[ch] if k[0] == f0]
            hold = self.last(ch, f0)
            e0 = at0[-1][2] if at0 else 'linear'
            self.ch[ch] = [k for k in self.ch[ch] if not (f0 <= k[0] <= f1)]
            self.ch[ch].append((f0, hold, e0))
            self.ch[ch].append((f1, v, e))
            self.ch[ch].sort(key=lambda k: k[0])
        return self

    def evaluate(self, C, f, info=None):
        sp = Channel(self.ch['spine']).at(f, mix_vec)
        hd = Channel(self.ch['head']).at(f, mix_vec)
        kn = Channel(self.ch['knees']).at(f, mix_num)
        sh = Channel(self.ch['shrug']).at(f, mix_vec)
        pr = Channel(self.ch['protract']).at(f, mix_vec)
        J = stance_joints(C, sp, hd, kn, (sh.x, sh.y), (pr.x, pr.y))
        env = math.sin(math.pi * (f - 1) / max(1, self.length - 1))
        br = math.sin(2 * math.pi * (f - 1) / 60.0) * 1.0 * env
        J = A.merge(J, {'Spine1': A.R((1, 0, 0), br * 0.4), 'Spine2': A.R((1, 0, 0), -br * 0.3)})

        def target(side):
            ch, fine, tw = ('R', 'Rfine', 'twist') if side == 'Right' else ('L', 'Lfine', 'ltwist')
            keys = [(fk, (C.stand[side] if v == 'STAND' else v), e) for fk, v, e in self.ch[ch]]
            return Channel(keys).at(f, mix_arm), Channel(self.ch[fine]).at(f, mix_vec), Channel(self.ch[tw]).at(f, mix_num)

        def solve(J, side, t, off, twist):
            pt = Vector(t['pt']) + off
            hdv, pdv = Vector(t['hd']).normalized(), Vector(t['pd'])
            if twist:
                pdv = Quaternion(hdv, math.radians(twist)) @ pdv
            wrist, hdv, pdv = C.wrist_of(side, {'pt': pt, 'hd': hdv, 'pd': pdv})
            return GG.solve_arm(C.rig, C.rest, J, side, wrist, t['pole'], hdv, pdv)

        tR, offR, twR = target('Right')
        J = solve(J, 'Right', tR, offR, twR)
        tL, offL, twL = target('Left')
        w = Channel(self.ch['Lsup']).at(f, mix_num)
        sup = None
        if w > 1e-4:
            d1 = A.pose_from_joints(C.rig, C.rest, J)
            app = Channel(self.ch['Lapp']).at(f, mix_vec)
            sup = support_target(d1[P + 'RightHand'], C.wrench, approach=tuple(app))
            tL = mix_arm(tL, sup, min(1.0, w))
            offL = offL * (1 - min(1.0, w))
        J = solve(J, 'Left', tL, offL, twL)
        J = share_twist(C, J, 'Left', SUP['twist_share'])
        desired = A.pose_from_joints(C.rig, C.rest, J)
        MR.set_hand(desired, C.rig, C.rest, 'Right', C.locals[('Right', 'grip')])
        hk = [(fk, (v if isinstance(v, tuple) else (v, v, 1.0)), e) for fk, v, e in self.ch['lhand']]
        hspec = Channel([(fk, v[1], e) for fk, v, e in hk]).at(f, lambda a, b, t: (a, b, t))
        if not isinstance(hspec, tuple):
            hspec = (hspec, hspec, 1.0)
        MR.set_hand(desired, C.rig, C.rest, 'Left', C.hand_local('Left', hspec))
        if info is not None:
            info['sup'] = sup
            info['w'] = w
        return desired

    def end_stand(self, f0, e='smooth'):
        super().end_stand(f0, e)
        for ch, v in (('Lsup', 0.0), ('Lapp', V(0, 0, 0)), ('protract', V(0, 0, 0))):
            last = max(k[0] for k in self.ch[ch])
            if last < f0:
                self.k(ch, f0, self.value(ch, f0), 'hold')
            self.k(ch, self.length, v, e)
        return self


def apply_params(p):
    """Set AIM / SUP from a flat parameter dict (the pose search's format)."""
    AIM.update(spine=(p['pitch'], p['yaw'], p['roll']), protract=(p['protL'], p['protR']), fist=(p['fx'], p['fy'], p['fz']),
               psi=p['psi'], elbow=(p['ex'], p['ey'], p['ez']), yaw=p['wyaw'])
    SUP.update(lyaw=p['lyaw'], x=p['supx'], pole=(p['lpx'], p['lpy'], p['lpz']))


def make_ctx(rig, rest):
    C = M.Ctx(rig, rest)
    C.locals.update({(s, 'support'): MR.hand_locals(rest, s, 'support') for s in ('Left', 'Right')})
    C.wrench = Wrench(rig, rest)
    return C


# ------------------------------------------------------------------ the shared raise / aim / release blocks
def ready_R(dz=-0.06):
    """The wrench coming up in front of the chest on the way to the aim (forearm forward, palm in, jaw up)."""
    return M.chest_R(dz=dz)


APPROACH = (-0.02, 0.06, 0.02)    # left hand off the wrench: 2 cm across, 6 cm forward, 2 cm below the contact (clean arm path)


def pre_support(C, app=APPROACH):
    """The left hand's free target just in front of / below its contact under the wrench in the aim pose (same palm
    frame and pole): the hand reaches in from the front and slides back under the front jaw (and out the same way)."""
    J = stance_joints(C, AIM['spine'], AIM['head'], AIM['knees'], AIM['shrug'], AIM['protract'])
    t = aim_R(C)
    wrist, hdv, pdv = C.wrist_of('Right', t)
    J = GG.solve_arm(C.rig, C.rest, J, 'Right', wrist, t['pole'], hdv, pdv)
    d = A.pose_from_joints(C.rig, C.rest, J)
    sup = support_target(d[P + 'RightHand'], C.wrench, approach=app)
    return arm(sup['pt'], sup['hd'], sup['pd'], sup['pole'])


def L_side():
    """Left hand passing beside the belly (on the way up to the wrench and back down)."""
    return arm(V(0.265, -0.25, 0.88), nrm(-0.25, -0.6, -0.75), (-0.9, 0.3, 0.1), (0.9, 0.35, -0.6))


def aim_block(c, C, f_ready, f_aim, f_side, f_wait, f_place, f_hold_end, f_cue, f_release, f_lowered, flick=(0.0, -0.013, -0.002)):
    """normal carry -> wrench up in front of the chest (f_ready) -> aim stance (f_aim); the left hand comes up past the
    belly (f_side) to just under its contact (f_wait), locks onto the wrench (support weight 0->1) and slides up to the
    contact (f_place); stable hold with a tiny breathing sway; a small recoil-free flick into the cue frame f_cue; the
    left palm drops off (f_release..+4) and goes home past the belly while the wrench is lowered to the chest."""
    R_aim = aim_R(C)
    L_pre = pre_support(C)
    c.move(2, f_ready, spine=(2, -5, 0), head=(3, 5, 0), R=ready_R(), knees=2)
    c.move(f_ready, f_aim, spine=AIM['spine'], head=AIM['head'], knees=AIM['knees'], shrug=AIM['shrug'],
           protract=AIM['protract'], R=R_aim)
    c.move(3, f_side, L=L_side(), lhand=('relaxed', 'cup', 1.0))
    c.move(f_side, f_wait, L=L_pre)
    c.k('Lapp', f_wait, V(*APPROACH), 'hold')
    c.k('Lsup', f_wait, 0.0, 'linear').k('Lsup', f_wait + 2, 1.0, 'smooth')
    c.move(f_wait + 2, f_place, 'smooth', Lapp=(0, 0, 0), lhand=('cup', 'support', 1.0))
    mid = (f_place + f_hold_end) // 2
    c.move(f_place, mid, Rfine=(0.0, -0.002, 0.003)).move(mid, f_hold_end, Rfine=(0.0, 0.001, -0.002))
    c.move(f_hold_end, f_cue, 'snap', Rfine=flick).move(f_cue, f_cue + 6, Rfine=(0.0, 0.0, 0.0))
    c.move(f_release, f_release + 4, Lapp=APPROACH, lhand=('support', 'cup', 1.0))
    c.k('L', f_release + 4, L_pre, 'hold')
    c.move(f_release + 4, f_release + 6, Lsup=0.0)
    c.move(f_release + 6, f_release + 15, L=L_side(), lhand=('cup', 'relaxed', 1.0))
    c.move(f_release + 15, f_lowered + 8, L='STAND')
    c.move(f_release + 4, f_lowered, R=ready_R(-0.03), spine=(1, -4, 0), head=(0, -3, 0), shrug=(0, 0, 0), protract=(0, 0),
           knees=0)
    return R_aim


# ------------------------------------------------------------------ the clips
def clip_gun_gag(C):
    c = Clip2('Mech_Gag_WrenchGun_v02', 126, role='MechGag', state='Mech_Gag_WrenchGun',
              note='v02 two-hand aim: brings the wrench up and shoulders it like a rifle (small jaw forward, big jaw toward '
                   'the right shoulder, upper body bladed ~16 deg right so the wrench points along his forward), left palm '
                   'under the front jaw, squints along it ~1 s with a mock-serious face, a silent "pew" with a tiny flick, '
                   'lets go with the left hand, lowers the wrench to the carry, smug nod, idle.')
    aim_block(c, C, f_ready=10, f_aim=19, f_side=8, f_wait=19, f_place=25, f_hold_end=47, f_cue=50, f_release=58, f_lowered=74,
              flick=(0.0, -0.016, -0.002))
    c.move(48, 50, 'snap', head=(25, 5, -6)).move(50, 57, head=AIM['head'])
    c.move(80, 86, head=(0, -6, 0)).move(86, 92, head=(0, 12, 0)).move(92, 98, head=(0, -2, 0))
    c.end_stand(98)
    c.face = [('Worried', 12, 0.0), ('Worried', 19, 0.45), ('Worried', 47, 0.45), ('Worried', 55, 0.15), ('Worried', 62, 0.0),
              ('Blink_L', 15, 0.0), ('Blink_L', 20, 1.0), ('Blink_L', 56, 1.0), ('Blink_L', 61, 0.0),
              ('Surprised', 48, 0.0), ('Surprised', 50, 0.45), ('Surprised', 56, 0.0),
              ('Happy', 76, 0.0), ('Happy', 84, 0.85), ('Happy', 108, 0.85), ('Happy', 120, 0.0)]
    c.events = {'Raise': 19, 'Aimed': 25, 'Pew': 50, 'Release': 58, 'Nod': 86}
    c.key_poses = [1, 10, 19, 25, 38, 50, 61, 68, 76, 92, 126]
    return c


def clip_upgrade(C):
    c = Clip2('Mech_Upgrade_Perform_v02', 138, role='MechUpgrade', state='Mech_Upgrade_Perform',
              note='v02 upgrade performance (the game turns him to face the van first): "watch this" nod, brings the wrench up '
                   'and shoulders it like a rifle (small jaw forward at the van, big jaw toward the right shoulder, upper body '
                   'bladed ~16 deg right), left palm under the front jaw, aims ~1 s (squint), a tiny recoil-free flick at Poof '
                   '(the van puff and the purchased change happen on that event, driven by the server, 1.70 s as v01), lets go '
                   'with the left hand, lowers the wrench to the carry, pleased grin, nod and a left thumbs-up; back to idle.')
    thumbs = arm(V(0.170, -0.300, 1.090), nrm(-0.2, -1, 0.3), (-1, 0, 0), (1, 0.2, -1))
    aim_block(c, C, f_ready=11, f_aim=20, f_side=9, f_wait=20, f_place=25, f_hold_end=49, f_cue=52, f_release=58, f_lowered=76)
    c.move(2, 6, head=(0, 9, 0)).move(6, 10, head=(3, 3, 0))      # "watch this" nod while the wrench comes up
    c.move(84, 92, R='STAND', L=thumbs, lhand='thumbs_up', head=(0, -4, 0), spine=(-3, 0, 0))
    c.move(92, 97, head=(0, 12, 0)).move(97, 102, head=(0, -2, 0)).move(102, 107, head=(0, 10, 0)).move(107, 112, head=(0, 0, 0))
    c.end_stand(114)
    c.face = [('Happy', 3, 0.0), ('Happy', 7, 0.4), ('Happy', 13, 0.0),
              ('Worried', 14, 0.0), ('Worried', 21, 0.4), ('Worried', 49, 0.4), ('Worried', 55, 0.0),
              ('Blink_L', 16, 0.0), ('Blink_L', 21, 1.0), ('Blink_L', 54, 1.0), ('Blink_L', 58, 0.0),
              ('Surprised', 50, 0.0), ('Surprised', 52, 0.4), ('Surprised', 60, 0.0),
              ('Happy', 78, 0.0), ('Happy', 90, 1.0), ('Happy', 118, 1.0), ('Happy', 132, 0.0)]
    c.events = {'AimStart': 25, 'Poof': 52, 'Release': 58, 'Pleased': 92, 'Done': 130}
    c.key_poses = [1, 11, 20, 25, 40, 52, 61, 68, 78, 97, 138]
    return c


def all_clips(C):
    return [clip_gun_gag(C), clip_upgrade(C)]


# ------------------------------------------------------------------ build
def build():
    rig, rest = MR.open_model(M.MODEL)
    scene = bpy.context.scene
    scene.render.fps = FPS
    for o in bpy.data.objects:
        if o.name == 'Prop_Phone':
            o.hide_render = True
            o.hide_viewport = True
    C = make_ctx(rig, rest)
    meshes = MR.meshes_lod0()
    face = bpy.data.objects['Face']
    grip = MR.grip_track(rig, rest)
    out = []
    for c in all_clips(C):
        frames = c.frames(C)
        act, ground = M.ground_and_key(C, c, frames, meshes, scene)
        fa = GG.face_action(face, c.name + '_Face', c.face) if c.face else None
        out.append((c, act, fa, ground))
        print(f'[ANIM] {c.name} frames {c.length} seam_dev_mm {c.seam_dev_mm} ground {ground}')
    return rig, rest, scene, grip, out, C


# ------------------------------------------------------------------ measurements on the posed meshes
def _weights(o):
    gi = {g.index: g.name for g in o.vertex_groups}
    return [{gi[g.group]: g.weight for g in v.groups} for v in o.data.vertices]


class Probe:
    """Posed-mesh checks of one frame: contacts, clearances, the backward wrench axis, wrist angles."""
    def __init__(self, rig, rest):
        self.rig, self.rest = rig, rest
        self.body, self.outfit = bpy.data.objects['Body'], bpy.data.objects['Outfit']
        self.face, self.wr = bpy.data.objects['Face'], bpy.data.objects['Wrench_RightHand']
        self.w = {o.name: _weights(o) for o in (self.body, self.outfit, self.face)}

        def group(o, test):
            return [i for i, ws in enumerate(self.w[o.name]) if test(ws)]

        def hand(side):
            return lambda ws: sum(v for k, v in ws.items() if k.startswith(P + side + 'Hand')) > 0.5

        def armw(ws):
            return sum(v for k, v in ws.items() if any(k == P + s + b for s in ('Left', 'Right') for b in ('Arm', 'ForeArm'))
                       or k.startswith(P + 'LeftHand') or k.startswith(P + 'RightHand'))
        self.lhand = group(self.body, hand('Left'))
        self.rhand = group(self.body, hand('Right'))
        self.torso = {o.name: group(o, lambda ws: armw(ws) < 0.2) for o in (self.body, self.outfit)}
        self.rarm = {o.name: group(o, lambda ws: sum(v for k, v in ws.items() if k in (P + 'RightArm', P + 'RightShoulder')) > 0.35)
                     for o in (self.body, self.outfit)}
        # the left forearm + hand (the part that crosses in front of the body; the upper-arm root always meets the torso)
        self.larm = {o.name: group(o, lambda ws: sum(v for k, v in ws.items() if k == P + 'LeftForeArm' or k.startswith(P + 'LeftHand')) > 0.5)
                     for o in (self.body, self.outfit)}
        self.rhand_set = set(self.rhand)
        self.lupper = group(self.body, lambda ws: ws.get(P + 'LeftArm', 0.0) > 0.6)
        wi = bpy.data.objects['Wrench_RightHand']
        Mi = rest[P + 'RightHand'].inverted()
        self.wr_free = [i for i, v in enumerate(wi.data.vertices) if not (FIST_X[0] - 0.008 <= (Mi @ (wi.matrix_world @ v.co)).x <= FIST_X[1] + 0.008)]
        self.head = list(range(len(self.face.data.vertices)))

    @staticmethod
    def mesh(o, dg):
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        co = [o.matrix_world @ v.co for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
        return co, polys

    @staticmethod
    def bvh(parts):
        from mathutils.bvhtree import BVHTree
        verts, polys = [], []
        for co, pl, keep in parts:
            keep = set(keep)
            remap = {}
            for i in sorted(keep):
                remap[i] = len(verts)
                verts.append(co[i])
            for p in pl:
                if all(i in keep for i in p):
                    polys.append([remap[i] for i in p])
        return BVHTree.FromPolygons(verts, polys) if polys else None

    @staticmethod
    def signed(tree, p, lim=0.03):
        """Distance to the surface, negative (inside) only near it: the parts are open pieces of closed meshes, so a
        far point's nearest-face normal says nothing."""
        loc, nor, idx, d = tree.find_nearest(p)
        if loc is None:
            return 9.0
        return -d if (d < lim and (p - loc).dot(nor) < 0) else d

    def capsule(self, tree, a, b, r0, r1, n=9):
        """Clearance of a limb segment a->b (radius r0..r1) from a surface: bone-axis samples, signed, minus the radius."""
        out = 9.0
        for i in range(n):
            t = i / (n - 1)
            q = a.lerp(b, t)
            loc, nor, idx, d = tree.find_nearest(q)
            if loc is None:
                continue
            sd = d if (q - loc).dot(nor) >= 0 else -d
            out = min(out, sd - (r0 + (r1 - r0) * t))
        return out

    def frame(self, scene, f):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        B, Bp = self.mesh(self.body, dg)
        O, Op = self.mesh(self.outfit, dg)
        Fc, Fp = self.mesh(self.face, dg)
        Wc, Wp = self.mesh(self.wr, dg)
        pb = self.rig.pose.bones
        mw = self.rig.matrix_world
        Mr = mw @ pb[P + 'RightHand'].matrix
        res = {'frame': f}
        # skin (Body, a closed mesh) is the reliable inside/outside test; clothes (open shells) by plain distance
        from mathutils.kdtree import KDTree

        def kdt(pts):
            kd = KDTree(len(pts))
            for i, q in enumerate(pts):
                kd.insert(q, i)
            kd.balance()
            return kd
        skin_torso = self.bvh([(B, Bp, self.torso['Body'])])
        skin_nohand = self.bvh([(B, Bp, [i for i in range(len(B)) if i not in self.rhand_set])])
        cloth = kdt(O)
        cloth_torso = kdt([O[i] for i in self.torso['Outfit']])
        wf = [Wc[i] for i in self.wr_free]
        res['wrench_vs_skin_mm'] = round(min(self.signed(skin_nohand, q) for q in wf) * 1000, 1)
        res['wrench_vs_cloth_mm'] = round(min(cloth.find(q)[2] for q in wf) * 1000, 1)
        headt = self.bvh([(Fc, Fp, self.head)])
        res['wrench_vs_face_mm'] = round(min(self.signed(headt, q) for q in Wc) * 1000, 1)
        lh = [B[i] for i in self.lhand]
        rh = [B[i] for i in self.rhand]
        wt = self.bvh([(Wc, Wp, range(len(Wc)))])
        dl = [self.signed(wt, q, 0.015) for q in lh]
        res['lefthand_to_wrench_min_mm'] = round(min(dl) * 1000, 1)
        res['lefthand_verts_within_4mm'] = sum(1 for d in dl if abs(d) <= 0.004)
        res['lefthand_into_wrench_max_mm'] = round(max(0.0, -min(dl)) * 1000, 1)
        kd = kdt(rh)
        res['lefthand_to_righthand_min_mm'] = round(min(kd.find(q)[2] for q in lh) * 1000, 1)
        lskin = [B[i] for i in self.larm['Body']]
        sh_l = mw @ pb[P + 'LeftArm'].head
        lup = [B[i] for i in self.lupper if (B[i] - sh_l).length > 0.09]
        res['leftupper_vs_skin_mm'] = round(min(self.signed(skin_torso, q, 0.06) for q in lup) * 1000, 1) if lup else None
        res['leftupper_vs_cloth_mm'] = round(min(cloth_torso.find(q)[2] for q in lup) * 1000, 1) if lup else None
        res['leftarm_vs_skin_mm'] = round(min(self.signed(skin_torso, q) for q in lskin[::2]) * 1000, 1)
        lsleeve = [O[i] for i in self.larm['Outfit']]
        res['leftarm_vs_cloth_mm'] = round(min(cloth_torso.find(q)[2] for q in (lskin + lsleeve)[::2]) * 1000, 1)
        # limb capsules (bone axes): left forearm + distal upper arm vs the torso skin; left vs right forearm/upper arm
        def seg(side, bone):
            b = pb[P + side + bone]
            return mw @ b.head, mw @ b.tail
        la_h, la_t = seg('Left', 'Arm')
        lf_h, lf_t = seg('Left', 'ForeArm')
        res['leftarm_capsule_vs_torso_mm'] = round(min(self.capsule(skin_torso, la_h.lerp(la_t, 0.45), la_t, 0.055, 0.05, 6),
                                                       self.capsule(skin_torso, lf_h, lf_t, 0.05, 0.042)) * 1000, 1)
        rf_h, rf_t = seg('Right', 'ForeArm')
        ra_h, ra_t = seg('Right', 'Arm')

        def segdist(a0, a1, b0, b1, n=12):
            return min((a0.lerp(a1, i / (n - 1)) - b0.lerp(b1, j / (n - 1))).length for i in range(n) for j in range(n))
        res['leftarm_vs_rightarm_mm'] = round((min(segdist(lf_h, lf_t, rf_h, rf_t), segdist(lf_h, lf_t, ra_h, ra_t)) - 0.10) * 1000, 1)
        # the left palm contact point (PALM_OFF from the posed LeftHand) vs the wrench surface
        Ml = mw @ pb[P + 'LeftHand'].matrix
        hdl = Ml.col[1].xyz.normalized()
        qh = Ml.to_quaternion() @ self.rest[P + 'LeftHand'].to_quaternion().inverted()
        pdl = (qh @ Vector((0, 0, -1))).normalized()
        palm = Ml.translation + hdl * M.PALM_OFF[0] + pdl * M.PALM_OFF[1]
        loc, nor, idx, d = wt.find_nearest(palm)
        res['palm_point_to_wrench_mm'] = round(d * 1000, 1)
        res['palm_point_along_shank_x'] = round((Mr.inverted() @ palm).x, 4)
        res['palm_up_dot'] = round(pdl.z, 3)
        # the backward wrench axis: from the rear (big) jaw tip along bone +X
        ex = (Mr.to_3x3().col[0]).normalized()
        tip = Mr @ Vector((BIG_TIP, AXIS_Y, AXIS_Z))
        rset = set(self.rhand)
        body_all = self.bvh([(B, Bp, [i for i in range(len(B)) if i not in rset]), (O, Op, range(len(O)))])
        hit = body_all.ray_cast(tip + ex * 0.0005, ex, 0.6)
        S = mw @ pb[P + 'RightArm'].head
        res['shoulder_joint'] = [round(x, 3) for x in S]
        if hit[0] is not None:
            hp = hit[0]
            near = min(range(len(B)), key=lambda i: (B[i] - hp).length)
            nearO = min(range(len(O)), key=lambda i: (O[i] - hp).length)
            src, i = ('Body', near) if (B[near] - hp).length <= (O[nearO] - hp).length else ('Outfit', nearO)
            ws = self.w[src][i]
            top = sorted(ws.items(), key=lambda kv: -kv[1])[:2]
            res['axis_hit'] = {'gap_from_rear_jaw_mm': round(hit[3] * 1000, 1), 'point': [round(x, 3) for x in hp],
                               'below_shoulder_joint_mm': round((S.z - hp.z) * 1000, 1),
                               'lateral_from_shoulder_joint_mm': round((S.x - hp.x) * 1000, 1),
                               'mesh': src, 'bones': [(k.replace(P, ''), round(v, 2)) for k, v in top]}
        else:
            res['axis_hit'] = None
        fwd = -ex
        res['wrench_fwd'] = [round(x, 3) for x in fwd]
        res['wrench_pitch_deg'] = round(math.degrees(math.asin(max(-1, min(1, fwd.z)))), 1)
        res['wrench_yaw_deg'] = round(math.degrees(math.atan2(fwd.x, -fwd.y)), 1)
        for side in ('Right', 'Left'):
            Mh = mw @ pb[P + side + 'Hand'].matrix
            Wp_ = Mh.translation
            E = mw @ pb[P + side + 'ForeArm'].head
            Sh = mw @ pb[P + side + 'Arm'].head
            f_ = (Wp_ - E).normalized()
            u = (E - Sh).normalized()
            hd = Mh.col[1].xyz.normalized()
            q = Mh.to_quaternion() @ self.rest[P + side + 'Hand'].to_quaternion().inverted()
            pd = (q @ Vector((0, 0, -1))).normalized()
            th = hd.cross(pd) if side == 'Right' else pd.cross(hd)
            dev = math.degrees(math.asin(max(-1, min(1, f_.dot(th)))))
            flex = math.degrees(math.atan2(f_.dot(pd), f_.dot(hd)))
            t0 = (-u + f_ * u.dot(f_)).normalized()
            tp = (th - f_ * th.dot(f_)).normalized()
            roll = math.degrees(math.atan2(f_.dot(t0.cross(tp)), t0.dot(tp)))
            pron = -roll if side == 'Right' else roll
            elbow = math.degrees(math.acos(max(-1, min(1, u.dot(f_)))))
            # skin twist of the wrist: hand local rotation about its own axis relative to the forearm bone
            lq = pb[P + side + 'Hand'].rotation_quaternion
            tw = 2 * math.degrees(math.atan2(lq.y, lq.w))
            tw = (tw + 180) % 360 - 180
            res[side] = {'ulnar_dev_deg': round(dev, 1), 'extension_deg': round(flex, 1), 'pronation_deg': round(pron, 1),
                         'wrist_skin_twist_deg': round(tw, 1), 'elbow_bend_deg': round(elbow, 1), 'elbow': [round(x, 3) for x in E],
                         'elbow_below_shoulder_mm': round((Sh.z - E.z) * 1000, 1)}
        return res


def _emissive(name, color, strength=3.0):
    mat = bpy.data.materials.new(name)
    try:
        mat.use_nodes = True
    except Exception:
        pass
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    for key in ('Emission Color', 'Emission'):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = (*color, 1)
            break
    if 'Emission Strength' in bsdf.inputs:
        bsdf.inputs['Emission Strength'].default_value = strength
    return mat


def axis_line(collection, Mr, back=0.42, name='AxisLine', color=(1.0, 0.05, 0.02), end=None, front_sign=-1):
    """Thin emissive rod along the wrench axis: from 3 cm past the front jaw tip, through the wrench, to `end` (the point
    where the backward extension meets the body) or `back` m past the rear jaw. front_sign -1: small jaw (bone -X) is
    the front (v02); +1: big jaw is the front (v01)."""
    import bmesh
    ex = Mr.to_3x3().col[0].normalized()
    front_tip, rear_tip = (SMALL_TIP, BIG_TIP) if front_sign < 0 else (BIG_TIP, SMALL_TIP)
    a = Mr @ Vector((front_tip + 0.03 * front_sign, AXIS_Y, AXIS_Z))
    b = Vector(end) if end is not None else Mr @ Vector((rear_tip, AXIS_Y, AXIS_Z)) - ex * front_sign * back
    d = b - a
    obj = bpy.data.objects.get(name)
    if obj is None:
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.0035, radius2=0.0035, depth=1.0)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(_emissive(name + '_Mat', color))
        obj = bpy.data.objects.new(name, me)
        collection.objects.link(obj)
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    obj.matrix_world = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((1, 1, d.length, 1))
    obj.hide_render = False
    return obj


def marker(collection, name, p, r=0.010, color=(0.05, 0.6, 1.0)):
    import bmesh
    obj = bpy.data.objects.get(name)
    if obj is None:
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(_emissive(name + '_Mat', color))
        obj = bpy.data.objects.new(name, me)
        collection.objects.link(obj)
    obj.location = p
    obj.hide_render = False
    return obj


VIEWS = {   # camera offset from the target (character frame): (offset, 'ortho' scale | 'persp' lens)
    'side': (Vector((-2.6, 0.0, 0.05)), 'ortho', 0.95),
    'front34R': (Vector((-1.35, -2.1, 0.25)), 'persp', 62),
    'front34L': (Vector((1.5, -2.05, 0.30)), 'persp', 62),
    'below34': (Vector((-1.0, -1.75, -0.70)), 'persp', 70),
    'top': (Vector((-0.35, -1.05, 1.75)), 'persp', 70),
    'rearR': (Vector((-1.55, 0.95, 0.75)), 'persp', 70),
    'front': (Vector((0.0, -2.6, 0.10)), 'ortho', 0.95),
    'full34': (Vector((-1.55, -2.55, 0.45)), 'persp', 50),
    'full34L': (Vector((1.7, -2.45, 0.40)), 'persp', 50),
    'side_full': (Vector((-3.2, 0.0, 0.0)), 'ortho', 1.95),
}


def shoot(scene, cam, path, view, tgt, res):
    import buddy_render as RD
    off, kind, val = VIEWS[view]
    if kind == 'ortho':
        RD.shot(scene, cam, path, tgt + off, tgt, res=res, ortho=val)
    else:
        RD.shot(scene, cam, path, tgt + off, tgt, lens=val, res=res)


def key_some(C, clip, fl, name):
    frames = {f: clip.evaluate(C, f) for f in fl}
    return RG.key_frames(C.rig, C.rest, frames, name)


def test(outdir, frames_by_clip, views=('side', 'front34R', 'front34L', 'below34'), res=(520, 640), samples=16):
    """Quick look: evaluate a few frames (no grounding), measure them, render with the axis line + contact markers."""
    import buddy_render as RD
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    rig, rest = MR.open_model(M.MODEL)
    scene = bpy.context.scene
    for o in bpy.data.objects:
        if o.name == 'Prop_Phone':
            o.hide_render = True
            o.hide_viewport = True
    C = make_ctx(rig, rest)
    probe = Probe(rig, rest)
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = samples
    report = {}
    for c in all_clips(C):
        fl = frames_by_clip.get(c.name.rsplit('_v', 1)[0], [])
        if not fl:
            continue
        act = key_some(C, c, fl, c.name + '_test')
        rig.animation_data.action = act
        for f in fl:
            info = {}
            c.evaluate(C, f, info)
            scene.frame_set(f)
            r = probe.frame(scene, f)
            report[f'{c.name}_f{f}'] = r
            Mr = rig.matrix_world @ rig.pose.bones[P + 'RightHand'].matrix
            axis_line(col, Mr)
            if info.get('sup'):
                marker(col, 'SupportMark', info['sup']['contact'])
            elif 'SupportMark' in bpy.data.objects:
                bpy.data.objects['SupportMark'].hide_render = True
            hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
            tgt = Vector((hips.x - 0.05, hips.y - 0.15, 1.12))
            for v in views:
                shoot(scene, cam, outdir / f'{c.name}_f{f:03d}_{v}.png', v, tgt if v not in ('full34',) else Vector((hips.x, hips.y, 0.95)), res)
            print('[TEST]', c.name, f, json.dumps(r))
    (outdir / 'test_report.json').write_text(json.dumps(report, indent=1), encoding='utf-8')
    return report


def check(rig, rest, scene, built, C, step=1):
    """Every frame of the built clips on the posed meshes: contacts, clearances, wrists, the axis, continuity."""
    probe = Probe(rig, rest)
    MR.clear_nla(rig)
    out = {}
    for c, act, fa, ground in built:
        rig.animation_data.action = act
        rows, prev = [], None
        for f in range(1, c.length + 1, step):
            r = probe.frame(scene, f)
            w = Channel(c.ch['Lsup']).at(f, mix_num)
            r['support_weight'] = round(w, 3)
            pb = rig.pose.bones
            cur = {s: (rig.matrix_world @ pb[P + s + 'ForeArm'].head, (rig.matrix_world @ pb[P + s + 'Hand'].matrix).to_quaternion())
                   for s in ('Right', 'Left')}
            if prev:
                for s in ('Right', 'Left'):
                    r[s]['elbow_step_mm'] = round((cur[s][0] - prev[s][0]).length * 1000, 1)
                    ang = math.degrees(cur[s][1].rotation_difference(prev[s][1]).angle)
                    r[s]['hand_rot_step_deg'] = round(min(ang, 360 - ang), 1)
            prev = cur
            rows.append(r)
        held = [r for r in rows if r['support_weight'] >= 0.999]
        aimed = [r for r in rows if r['support_weight'] >= 0.999 and abs(r['wrench_pitch_deg']) < 5]

        def worst(key, rs, fn=min):
            if not rs:
                return None
            r = fn(rs, key=lambda x: x[key])
            return {'value': r[key], 'frame': r['frame']}

        def worst_side(side, key, rs, fn=max):
            rs = [r for r in rs if key in r[side]]
            if not rs:
                return None
            r = fn(rs, key=lambda x: x[side][key])
            return {'value': r[side][key], 'frame': r['frame']}
        summary = {
            'frames_checked': len(rows), 'support_frames': [held[0]['frame'], held[-1]['frame']] if held else None,
            'min_wrench_vs_skin_mm': worst('wrench_vs_skin_mm', rows), 'min_wrench_vs_cloth_mm': worst('wrench_vs_cloth_mm', rows),
            'min_wrench_vs_face_mm': worst('wrench_vs_face_mm', rows),
            'min_leftarm_vs_skin_mm': worst('leftarm_vs_skin_mm', rows), 'min_leftarm_capsule_vs_torso_mm': worst('leftarm_capsule_vs_torso_mm', rows), 'min_leftupper_vs_skin_mm': worst('leftupper_vs_skin_mm', rows), 'min_leftupper_vs_cloth_mm': worst('leftupper_vs_cloth_mm', rows), 'min_leftarm_vs_cloth_mm': worst('leftarm_vs_cloth_mm', rows),
            'min_leftarm_vs_rightarm_mm': worst('leftarm_vs_rightarm_mm', rows),
            'min_lefthand_to_righthand_mm': worst('lefthand_to_righthand_min_mm', rows),
            'held_max_palm_point_to_wrench_mm': worst('palm_point_to_wrench_mm', held, max),
            'held_max_lefthand_into_wrench_mm': worst('lefthand_into_wrench_max_mm', held, max),
            'held_min_lefthand_verts_within_4mm': worst('lefthand_verts_within_4mm', held),
            'aim_wrench_pitch_deg': [min(r['wrench_pitch_deg'] for r in aimed), max(r['wrench_pitch_deg'] for r in aimed)] if aimed else None,
            'aim_wrench_yaw_deg': [min(r['wrench_yaw_deg'] for r in aimed), max(r['wrench_yaw_deg'] for r in aimed)] if aimed else None,
            'aim_axis_hits': sorted({(h['axis_hit']['bones'][0][0] if h['axis_hit'] else 'none') for h in aimed}),
            'aim_axis_below_shoulder_joint_mm': [min(h['axis_hit']['below_shoulder_joint_mm'] for h in aimed if h['axis_hit']),
                                                 max(h['axis_hit']['below_shoulder_joint_mm'] for h in aimed if h['axis_hit'])] if aimed else None,
            'aim_axis_gap_from_rear_jaw_mm': [min(h['axis_hit']['gap_from_rear_jaw_mm'] for h in aimed if h['axis_hit']),
                                              max(h['axis_hit']['gap_from_rear_jaw_mm'] for h in aimed if h['axis_hit'])] if aimed else None,
        }
        for s in ('Right', 'Left'):
            summary[s] = {k: {'max': worst_side(s, k, rows, max), 'min': worst_side(s, k, rows, min)}
                          for k in ('ulnar_dev_deg', 'extension_deg', 'pronation_deg', 'wrist_skin_twist_deg')}
            summary[s]['max_elbow_step_mm'] = worst_side(s, 'elbow_step_mm', rows, max)
            summary[s]['max_hand_rot_step_deg'] = worst_side(s, 'hand_rot_step_deg', rows, max)
            summary[s]['aim_elbow_below_shoulder_mm'] = [min(r[s]['elbow_below_shoulder_mm'] for r in aimed),
                                                         max(r[s]['elbow_below_shoulder_mm'] for r in aimed)] if aimed else None
        out[c.name] = {'summary': summary, 'frames': rows}
        print('[CHECK]', c.name, json.dumps(summary))
    return out


def _hide(*names):
    for n in names:
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_render = True


def _annotate(path, lines, out=None):
    """Write text lines on a render (ImageMagick), bottom-left, white box."""
    out = out or path
    cmd = ['magick', str(path), '-gravity', 'SouthWest', '-pointsize', '17', '-undercolor', '#000000B0', '-fill', 'white']
    for i, ln in enumerate(reversed(lines)):
        cmd += ['-annotate', f'+8+{8 + 22 * i}', ' ' + ln + ' ']
    cmd += [str(out)]
    subprocess.run(cmd, check=False)


def _draw_aim_marks(rig, col, probe, scene, f, info=None):
    """Axis line trimmed at the point where its backward extension meets the body + markers (hit yellow, left
    contact blue). Returns the probe result of the frame."""
    r = probe.frame(scene, f)
    Mr = rig.matrix_world @ rig.pose.bones[P + 'RightHand'].matrix
    h = r['axis_hit']
    axis_line(col, Mr, end=(Vector(h['point']) if h else None))
    if h:
        marker(col, 'HitMark', Vector(h['point']), r=0.011, color=(1.0, 0.85, 0.05))
    else:
        _hide('HitMark')
    if info and info.get('sup'):
        marker(col, 'SupportMark', info['sup']['contact'], r=0.008)
    else:
        _hide('SupportMark')
    return r


def strip_sheet(rig, scene, cam, col, built, folder, C):
    """Raise / hold / lower strip per clip (side and both 3/4), axis line + hit marker while the left hand supports."""
    folder = Path(folder)
    face = bpy.data.objects['Face']
    probe = Probe(rig, C.rest)
    sheets = []
    for c, act, fa, _ in built:
        rig.animation_data.action = act
        sk = face.data.shape_keys
        sk.animation_data_create()
        sk.animation_data.action = fa
        files, labels = [], []
        for f in c.key_poses:
            scene.frame_set(f)
            if Channel(c.ch['Lsup']).at(f, mix_num) >= 0.5:
                _draw_aim_marks(rig, col, probe, scene, f)
                _hide('SupportMark')
            else:
                _hide('AxisLine', 'HitMark', 'SupportMark')
            hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
            tgt = Vector((hips.x, hips.y, 0.98))
            for tag, view in (('s', 'side_full'), ('q', 'full34'), ('l', 'full34L')):
                p = folder / c.name / f'{c.name}_f{f:03d}_{tag}.png'
                shoot(scene, cam, p, view, tgt, (360, 520))
                files.append(p)
            ev = [k for k, v in c.events.items() if v == f]
            labels += [f'f{f} side' + (f' {ev[0]}' if ev else ''), f'f{f} 3/4 R', f'f{f} 3/4 L']
        sheet = folder / f'{c.name}_strip.png'
        cmd = ['magick', 'montage']
        for p, lab in zip(files, labels):
            cmd += ['-label', lab, str(p)]
        cmd += ['-tile', '6x', '-geometry', '240x347+2+2', '-pointsize', '13', '-depth', '8',
                '-title', c.name + '  raise / hold / lower (red: wrench axis to where it meets the body)', str(sheet)]
        subprocess.run(cmd, check=False)
        sheets.append(sheet)
        sk.animation_data.action = None
        _hide('AxisLine', 'HitMark', 'SupportMark')
    return sheets


def _overlay(path, scene, cam, pts):
    """Draw the wrench axis and its backward extension in 2D on top of a render (it is hidden behind the right forearm
    in a pure side view): solid red = the wrench, dashed red = the imaginary continuation to the hit, dots = contacts."""
    from bpy_extras.object_utils import world_to_camera_view
    W, H = scene.render.resolution_x, scene.render.resolution_y

    def px(p):
        v = world_to_camera_view(scene, cam, Vector(p))
        return round(v.x * W, 1), round((1 - v.y) * H, 1)
    f, r, hit = px(pts['front']), px(pts['rear']), (px(pts['hit']) if pts.get('hit') is not None else None)
    mvg = [f"stroke '#ff2a10' stroke-width 3 line {f[0]},{f[1]} {r[0]},{r[1]}"]
    if hit:
        mvg.append(f"push graphic-context stroke '#ff2a10' stroke-width 3 stroke-dasharray 9,6 line {r[0]},{r[1]} {hit[0]},{hit[1]} pop graphic-context")
        mvg.append(f"stroke '#000000' stroke-width 1 fill '#ffd60a' circle {hit[0]},{hit[1]} {hit[0] + 7},{hit[1]} fill none")
    for key, col in (('fist', '#28d228'), ('palm', '#1e9bff')):
        if pts.get(key) is not None:
            q = px(pts[key])
            mvg.append(f"stroke '#000000' stroke-width 1 fill '{col}' circle {q[0]},{q[1]} {q[0] + 6},{q[1]} fill none")
    subprocess.run(['magick', str(path), '-fill', 'none', '-draw', ' '.join(mvg), str(path)], check=False)


def pose_views(rig, scene, cam, col, built, folder, C):
    """Annotated aim views of the hold frame: side (axis + its extension to the arm), 3/4 front R/L, underside, top."""
    folder = Path(folder)
    face = bpy.data.objects['Face']
    probe = Probe(rig, C.rest)
    out = {}
    for c, act, fa, _ in built:
        f = c.key_poses[4]
        rig.animation_data.action = act
        sk = face.data.shape_keys
        sk.animation_data_create()
        sk.animation_data.action = fa
        scene.frame_set(f)
        info = {}
        c.evaluate(C, f, info)
        r = _draw_aim_marks(rig, col, probe, scene, f, info)
        h = r['axis_hit']
        hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
        tgt = Vector((hips.x - 0.06, hips.y - 0.17, 1.13))
        files = []
        notes = {
            'side': [f'{c.name} f{f}: side (from his right)',
                     f'wrench axis {r["wrench_pitch_deg"]:+.0f} deg pitch, {r["wrench_yaw_deg"]:+.0f} deg yaw (along his forward = at the van)',
                     (f'backward extension meets the right upper arm (yellow) {h["below_shoulder_joint_mm"] / 10:.1f} cm below') if h else 'axis: no hit',
                     (f'the shoulder joint, {h["gap_from_rear_jaw_mm"] / 10:.1f} cm behind the rear jaw tip') if h else ''],
            'front34R': [f'{c.name} f{f}: 3/4 front right',
                         'right fist (Grip_R) on the rear part next to the big jaw;', 'left palm under the small (front) jaw neck'],
            'front34L': [f'{c.name} f{f}: 3/4 front left',
                         f'left hand to wrench {r["lefthand_to_wrench_min_mm"]:.1f} mm (no penetration),', f'hands {r["lefthand_to_righthand_min_mm"] / 10:.1f} cm apart'],
            'below34': [f'{c.name} f{f}: from below right', 'supported underside: palm up, fingers curled up the far side'],
            'top': [f'{c.name} f{f}: from above, in front', 'one rigid wrench, two contacts'],
        }
        Mr = rig.matrix_world @ rig.pose.bones[P + 'RightHand'].matrix
        pts = {'front': Mr @ Vector((SMALL_TIP, AXIS_Y, AXIS_Z)), 'rear': Mr @ Vector((BIG_TIP, AXIS_Y, AXIS_Z)),
               'hit': Vector(h['point']) if h else None, 'fist': Mr @ Vector((0.004, 0.0988, 0.0369)),
               'palm': info['sup']['contact'] if info.get('sup') else None}
        notes['rearR'] = [f'{c.name} f{f}: from behind his right shoulder', 'rear (big) jaw and the gap to the arm']
        legend = 'red: axis, dashed: its extension, yellow: hit, green: fist, blue: palm'
        for view in ('side', 'front34R', 'front34L', 'below34', 'top', 'rearR'):
            p = folder / f'{c.name}_f{f:03d}_aim_{view}.png'
            shoot(scene, cam, p, view, tgt, (700, 860))
            if view in ('side', 'top', 'rearR', 'front34L'):
                _overlay(p, scene, cam, pts)
                notes[view] = notes[view] + [legend]
            _annotate(p, notes[view])
            files.append(p)
        out[c.name] = (f, files, r)
        _hide('AxisLine', 'HitMark', 'SupportMark')
        sk.animation_data.action = None
    return out


def before_after(prev, v02_views):
    """v01 vs v02 at the aim hold (f40 of both v01 clips), side and 3/4 front right, same cameras, axis drawn on both."""
    import buddy_render as RD
    bpy.ops.wm.open_mainfile(filepath=str(V01_DIR / 'MECHANIC_W86_Anim_v01.blend'))
    rig = bpy.data.objects[MR.RIG]
    MR.clear_nla(rig)
    scene = bpy.context.scene
    for o in bpy.data.objects:
        if o.name == 'Prop_Phone':
            o.hide_render = True
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = 24
    face = bpy.data.objects['Face']
    sheets = []
    for name, (f2, files2, r2) in v02_views.items():
        v1 = name.replace('_v02', '_v01')
        f1 = 40
        rig.animation_data.action = bpy.data.actions[v1]
        sk = face.data.shape_keys
        sk.animation_data_create()
        sk.animation_data.action = bpy.data.actions.get(v1 + '_Face')
        scene.frame_set(f1)
        Mr = rig.matrix_world @ rig.pose.bones[P + 'RightHand'].matrix
        axis_line(col, Mr, front_sign=+1)
        hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
        tgt = Vector((hips.x - 0.06, hips.y - 0.17, 1.13))
        v1files = []
        for view in ('side', 'front34R'):
            p = prev / 'v01_compare' / f'{v1}_f{f1:03d}_{view}.png'
            shoot(scene, cam, p, view, tgt, (700, 860))
            v1files.append(p)
        _annotate(v1files[0], [f'BEFORE {v1} f{f1}', 'wrench up beside the face like a pistol sight, left hand not on it'])
        _annotate(v1files[1], [f'BEFORE {v1} f{f1}'])
        sheet = prev / f'{name}_before_after_v01.png'
        subprocess.run(['magick', 'montage', str(v1files[0]), str(files2[0]), str(v1files[1]), str(files2[1]), '-tile', '2x',
                        '-geometry', '600x737+3+3', '-depth', '8', '-title', f'{v1} (left, before)  vs  {name} (right, after)',
                        '-pointsize', '14', str(sheet)], check=False)
        sheets.append(sheet)
        sk.animation_data.action = None
    return sheets


def export_v02(built, out_dir):
    blend = out_dir / 'MECHANIC_W86_Anim_v02.blend'
    for c, *_ in built:
        fbx = out_dir / (c.name + '.fbx')
        if fbx.exists():
            sys.exit(f'Refusing to overwrite {fbx}')
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        rig = bpy.data.objects[MR.RIG]
        MR.clear_nla(rig)
        act = bpy.data.actions[c.name]
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


def manifest_v02(built):
    v01 = json.loads((V01_DIR / 'clips_mechanic_v01.json').read_text(encoding='utf-8'))
    new = {}
    for c, act, fa, ground in built:
        new[c.state] = {
            'role': c.role, 'state': c.state, 'file': c.name + '.fbx', 'take': c.name,
            'source': f'ArtSource/Characters/MECHANIC_W86/Animations_v02/{c.name}.fbx',
            'loop': c.loop, 'frames': [1, c.length], 'fps': FPS, 'seconds': round((c.length - 1) / FPS, 4),
            'events': {k: {'frame': v, 'seconds': round((v - 1) / FPS, 4), 'fraction': round((v - 1) / (c.length - 1), 4)} for k, v in c.events.items()},
            'face_cues': [{'shape': s, 'frame': f, 'seconds': round((f - 1) / FPS, 4), 'value': v} for s, f, v in sorted(c.face, key=lambda k: (k[1], k[0]))],
            'face_track_blend': (c.name + '_Face') if c.face else None,
            'grounding_hips_shift_m': ground, 'seam_deviation_mm': c.seam_dev_mm, 'note': c.note, 'revision': 'v02'}
    clips = [new.get(e['state'], e) for e in v01['clips']]
    data = {'comment': 'MECHANIC_W86 clips v02 (Blender, Claude 2026-10-29): the full manifest in the clips_mechanic_v01.json format. '
                       'Mech_Gag_WrenchGun and Mech_Upgrade_Perform point at the new v02 FBX in Animations_v02 (same Animator state '
                       'names, same lengths 126 / 138 frames, Poof still frame 52 = 1.70 s, Pew frame 50); the seven other entries '
                       'are the v01 entries unchanged (their files stay in Animations_v01). Grip_R v01 unchanged.',
            'grip_clip': v01['grip_clip'], 'clips': clips}
    return data


def final():
    OUT_DIR.mkdir(exist_ok=True)
    blend = OUT_DIR / 'MECHANIC_W86_Anim_v02.blend'
    man = OUT_DIR / 'clips_mechanic_v02.json'
    chk = OUT_DIR / 'aim_check_v02.json'
    for p in (blend, man, chk):
        if p.exists():
            sys.exit(f'Refusing to overwrite {p}')
    rig, rest, scene, grip, built, C = build()
    report = check(rig, rest, scene, built, C)
    chk.write_text(json.dumps({'comment': 'Per-frame checks on the posed LOD0 meshes (mm, deg). skin = Body (closed mesh) signed '
                                          'distance, negative only within 3 cm of the surface; cloth = nearest Outfit vertex; '
                                          'leftupper / capsule values are relative measures (the idle pose itself gives about '
                                          '-15 / -23 mm where the arm meets the body); axis = ray from the rear (big) jaw tip '
                                          'back along the shank; wrist angles vs the forearm (ulnar +, extension +, pronation '
                                          'vs mid-prone, skin twist = the hand bone local twist).', 'aim': AIM, 'support': SUP,
                               'clips': report}, indent=1, default=str), encoding='utf-8')
    man.write_text(json.dumps(manifest_v02(built), indent=1, ensure_ascii=False), encoding='utf-8')
    MR.clear_nla(rig)
    rig.animation_data.action = bpy.data.actions['Idle'] if 'Idle' in bpy.data.actions else None
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))       # saved before the studio / markers are added
    import buddy_render as RD
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = 24
    prev = OUT_DIR / 'Previews'
    pv = pose_views(rig, scene, cam, col, built, prev, C)
    strips = strip_sheet(rig, scene, cam, col, built, prev, C)
    names = [c.name for c, *_ in built]
    export_v02(built, OUT_DIR)
    ba = before_after(prev, pv)
    print('[FINAL] done', [str(s) for s in strips + ba], names)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', default=None)
    ap.add_argument('--frames', default='')       # "Mech_Upgrade_Perform:23,40;Mech_Gag_WrenchGun:40"
    ap.add_argument('--views', default='side,front34R,front34L,below34')
    ap.add_argument('--check', default=None)
    ap.add_argument('--final', action='store_true')
    ap.add_argument('--params', default=None)
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if args.params:
        apply_params(json.loads(Path(args.params).read_text())['params'])
    if args.test:
        fb = {}
        for part in filter(None, args.frames.split(';')):
            k, v = part.split(':')
            fb[k] = [int(x) for x in v.split(',')]
        test(args.test, fb, views=tuple(args.views.split(',')))
        return
    if args.check:
        rig, rest, scene, grip, built, C = build()
        rep = check(rig, rest, scene, built, C, step=1)
        Path(args.check).write_text(json.dumps(rep, indent=1), encoding='utf-8')
        return
    if args.final:
        final()


if __name__ == '__main__':
    main()
