"""MECHANIC_W86 animation set v03: every mechanic clip on the rifle-sized v02 wrench (mechanic_w86_wrench_v02.py),
the two-hand aim re-authored on it, his own carry copies of the shared Idle / Walk. Original procedural keyframe
animation, Blender 5.2 background, the v01/v02 method and rig (mechanic_w86_anim.py and _v02.py are imported and
configured here; their files are read only).

  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/mechanic_w86_anim_v03.py -- --test <dir> [--clips A,B]
  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/mechanic_w86_anim_v03.py -- --final

Input: MECHANIC_W86_v02.blend (v01 + the v02 wrench). --final writes Animations_v03/ (never over existing files):
MECHANIC_W86_Anim_v03.blend, one rig-only FBX per clip (the v01 export options, one take named like the action),
MECHANIC_W86_Grip_R_v02.fbx (the finger pose round the oblique grip), clips_mechanic_v03.json (the full manifest, the
v01 format + 'carry_clips'), check_v03.json (per-frame clearances, contacts, wrists, the aim axis) and Previews/.

What changed and why (numbers in check_v03.json):
- The wrench is 0.84 m and sits 45 deg oblique in the fist (see the wrench module): the front (long) part leaves the
  fist on the pinky side, the rear jaw just past the thumb. Every v01 clip was re-checked on it; the ones where it went
  into the body (both attention clips and the exit, CockNod, InspectPart) are re-authored, the others (CheckBay,
  WipeBench) are the v01 definitions re-evaluated on the new wrench and carry base.
- Carry: the shared Idle_Stand_v04 / Walk_v04 hang the right hand so the long part points back-down; in the walk's arm
  swing its jaw reached the floor and brushed the right leg. Fix = a small arm offset baked into his own copies of the
  two clips (Mech_Idle_v03, Mech_Walk_v03): the right hand turned CARRY_DEV deg in the palm plane (the wrench rises
  toward the horizontal, clear of the leg, pouch and floor). Every v03 clip starts and ends on that carry pose.
- Aim (Mech_Gag_WrenchGun_v03, Mech_Upgrade_Perform_v03): a bladed rifle stance (upper body ~33 deg to his right, left
  shoulder forward), the wrench horizontal along his forward (= at the van; the game turns the root), right fist on the
  rear part next to the rear jaw, elbow down and out, left palm up under the shank just behind the front jaw (~22 cm of
  bare shank between the hands), the backward extension of the axis on the right upper arm ~2.5 cm below the shoulder
  joint, the rear jaw ~1.5 cm in front of the arm. Same lengths and event frames as v02 (Poof frame 52 = 1.70 s).
"""
import argparse, json, math, sys, subprocess
from pathlib import Path
import bpy
from mathutils import Vector, Matrix, Quaternion

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mechanic_w86_anim as M          # noqa: E402
import mechanic_w86_anim_v02 as V2     # noqa: E402
import mechanic_w86_wrench_v02 as WV   # noqa: E402
import mech_rig as MR                  # noqa: E402
import buddy_anim as A                 # noqa: E402
import buddy_gags as GG                # noqa: E402
import buddy_rig as RG                 # noqa: E402

P = MR.P
FPS = 30
OUT_DIR = HERE / 'Animations_v03'
V01_DIR, V02_DIR = HERE / 'Animations_v01', HERE / 'Animations_v02'
MODEL = HERE / 'MECHANIC_W86_v02.blend'
V, nrm, arm, Channel, mix_arm, mix_vec, mix_num = M.V, M.nrm, M.arm, M.Channel, M.mix_arm, M.mix_vec, M.mix_num

# ------------------------------------------------------------------ the v02 wrench in the v01 / v02 machinery
M.FIST_OFF = (WV.CENTRE.y, WV.CENTRE.z, WV.CENTRE.x)      # grip centre in the hand frame (hand dir, palm dir, thumb dir)
MR.HAND_POSES['grip'] = WV.GRIP_V02
AX = WV.AXIS.normalized()
CARRY_DEV = 20.0             # carry: right hand turned in the palm plane (deg, + = the long part up toward the horizontal)
REAR_U, FRONT_U = WV.REAR_END, WV.FRONT_END


def hand_frame(s, rho=0.0, e_hint=None):
    """Hand frame for a wrench whose front points along s: bone AXIS (pinky side, 45 deg toward the fingers) = s.
    e = the hand direction's part square to the wrench: e_hint (default up) made square to s, rolled by rho about s."""
    s = Vector(s).normalized()
    e = Vector(e_hint) if e_hint is not None else Vector((0, 0, 1))
    e = (e - s * e.dot(s))
    if e.length < 1e-6:
        e = s.orthogonal()
    e = Quaternion(s, math.radians(-rho)) @ e.normalized() if rho else e.normalized()
    d = math.radians(WV.DELTA)
    hd = s * math.sin(d) + e * math.cos(d)
    jd = -s * math.cos(d) + e * math.sin(d)
    return hd.normalized(), jd.cross(hd).normalized()


def hold(F, s, pole, rho=0.0, e_hint=None):
    """Right-arm target: the grip centre at F, the wrench front along s."""
    hd, pd = hand_frame(s, rho, e_hint)
    return arm(F, hd, pd, pole)


def front_tip_of(t):
    """World point of the front jaw tip for a right target (hold())."""
    hd, pd = Vector(t['hd']).normalized(), Vector(t['pd']).normalized()
    jd = hd.cross(pd)
    d = math.radians(WV.DELTA)
    s = -jd * math.cos(d) + hd * math.sin(d)
    return Vector(t['pt']) + s * FRONT_U, s


class Wrench3:
    """The wrench vertices in RightHand bone space with their position u along the axis."""
    def __init__(self, rig, rest):
        o = bpy.data.objects['Wrench_RightHand']
        Mi = rest[P + 'RightHand'].inverted()
        self.v = [Mi @ (o.matrix_world @ v.co) for v in o.data.vertices]
        self.u = [(v - WV.CENTRE).dot(AX) for v in self.v]

    def slice(self, u0, u1):
        return [v for v, u in zip(self.v, self.u) if u0 <= u <= u1]


SIDE = {'mode': 'under'}


def support_target3(Mr, wr, lyaw=None, lshift=None, lift=None, x=None, approach=(0.0, 0.0, 0.0)):
    """V2.support_target for the oblique wrench: the left palm under the shank at u = x (default SUP['x']), palm up,
    fingers across toward his right turned lyaw toward the front. SIDE['mode'] 'top': palm down on top of it."""
    S = V2.SUP
    lyaw = S['lyaw'] if lyaw is None else lyaw
    lshift = S['lshift'] if lshift is None else lshift
    lift = S.get('lift', 0.0) if lift is None else lift
    x = S['x'] if x is None else x
    fwd = (Mr.to_3x3() @ AX).normalized()
    centre = Mr @ WV.point(x)
    up = Vector((0, 0, 1)) if SIDE['mode'] == 'top' else Vector((0, 0, -1))
    dn = (up - fwd * up.dot(fwd)).normalized()
    a, n, w = WV.frame()
    R3 = Mr.to_3x3()
    hw, ht = WV.section(x)
    h = math.sqrt((hw * dn.dot((R3 @ w).normalized())) ** 2 + (ht * dn.dot((R3 @ n).normalized())) ** 2)
    contact = centre + dn * (h + lift)
    pd = -dn
    across = fwd.cross(pd).normalized()
    hd = (Quaternion(pd, math.radians(lyaw)) @ across).normalized()
    a = Vector(approach)
    pt = contact + hd * lshift + across * a.x + fwd * a.y + dn * a.z
    return {'pt': pt, 'hd': hd, 'pd': pd, 'pole': nrm(*S['pole']), 'contact': contact, 'fwd': fwd}


V2.support_target = support_target3

# ------------------------------------------------------------------ the aim (pose search on the rig, see the docstring)
AIM3 = dict(spine=(-2.0, -31.95, -8.0), head=(28.0, 12.0, -8.0), knees=2.0, shrug=(0.0, 9.60, 0.0), protract=(37.42, -9.87),
            fist=(-0.2234, -0.168, 1.131), rho=5.0, pole=(-0.2603, 0.122, -0.506), pitch=0.0, yaw=0.0)
SUP3 = dict(lyaw=20.0, lshift=0.0, x=0.3062, pole=(1.0, -0.0692, 0.0), twist_share=0.6, lift=0.0004)
# the supporting left hand round the v02 support section (palm up, fingers curled up the far side)
MR.HAND_POSES['support'] = dict(fingers=(30.0, 50.0, 35.0), thumb=(((1, 0, 0), 26), ((0, 0, 1), 10), ((1, 0, 0), 12)))
V2.AIM.clear()
V2.AIM.update(AIM3)
V2.SUP.clear()
V2.SUP.update(SUP3)


def aim_R3(C, spec=None, dfist=(0, 0, 0), dpsi=0.0):
    spec = spec or V2.AIM
    fwd, e1, e2 = V2.wrench_dirs(spec['pitch'], spec['yaw'])
    return hold(Vector(spec['fist']) + Vector(dfist), fwd, nrm(*spec['pole']), spec['rho'] + dpsi)


def sdir(el, az):
    """Unit direction from elevation (deg up) and azimuth (deg; 0 = his forward -Y, + toward his left +X)."""
    e, a = math.radians(el), math.radians(az)
    return Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))


# right-hand holds found by a search on the rig (wrist <= ~15 deg, arm and wrench clear of the torso, see the docstring)
HOLDS = {
    'ready': dict(F=(-0.2446, -0.2605, 1.0624), s=(-20.0, 15.0), rho=-11.09, pole=(-0.5733, 0.9924, -0.9239)),
    'shoulder': dict(F=(-0.2663, -0.1715, 1.4157), s=(46.55, 156.53), rho=-14.29, pole=(-0.1172, -0.078, -0.9622)),
    'lift': dict(F=(-0.2842, -0.3351, 1.0726), s=(-13.4, 169.79), rho=90.0, pole=(0.2957, 0.9874, 0.1046)),
    'port': dict(F=(-0.2291, -0.2564, 1.1346), s=(33.15, 75.0), rho=-90.0, pole=(-0.5384, -0.3857, -0.8463)),
    'tap': dict(s=(10.0, -79.6), rho=36.75, pole=(0.6069, -0.0677, -0.4665)),
}


def held_R(name, dF=(0, 0, 0)):
    h = HOLDS[name]
    return hold(Vector(h['F']) + Vector(dF), sdir(*h['s']), nrm(*h['pole']), h['rho'])


def ready_R3(dz=-0.06):
    """On the way up to the aim: low ready, the wrench in front of the belly pointing forward, a little down."""
    return held_R('ready', (0, 0, dz + 0.06))


APPROACH3 = (-0.02, 0.06, 0.04)      # left palm arriving: 2 cm across, 6 cm forward, 4 cm below its contact
RELEASE3 = (-0.10, 0.0, 0.06)        # left palm leaving: down off the shank first, then 10 cm to his left


def aim_block3(c, C, f_ready, f_aim, f_side, f_wait, f_place, f_hold_end, f_cue, f_release, f_lowered, flick=(0.0, -0.013, -0.002)):
    """V2.aim_block on the big wrench: carry -> low ready -> aim; the left palm comes up past the belly, locks onto the
    wrench and slides into its contact; hold with a small sway; a recoil-free flick into the cue frame; on release the
    palm slides off to his left with the wrench (still attached), drops to beside the belly, then the wrench is lowered
    (it starts 6 frames after the release so the front part never passes the leaving hand)."""
    R_aim = V2.aim_R(C)
    L_pre = V2.pre_support(C, app=APPROACH3)
    c.move(2, f_ready, spine=(2, -5, 0), head=(3, 5, 0), R=V2.ready_R(), knees=2)
    c.move(f_ready, f_aim, spine=V2.AIM['spine'], head=V2.AIM['head'], knees=V2.AIM['knees'], shrug=V2.AIM['shrug'],
           protract=V2.AIM['protract'], R=R_aim)
    c.move(3, f_side, L=V2.L_side(), lhand=('relaxed', 'cup', 1.0))
    c.move(f_side, f_wait, L=L_pre)
    c.k('Lapp', f_wait, V(*APPROACH3), 'hold')
    c.k('Lsup', f_wait, 0.0, 'linear').k('Lsup', f_wait + 2, 1.0, 'smooth')
    c.move(f_wait + 2, f_place, 'smooth', Lapp=(0, 0, 0), lhand=('cup', 'support', 1.0))
    mid = (f_place + f_hold_end) // 2
    c.move(f_place, mid, Rfine=(0.0, -0.002, 0.003)).move(mid, f_hold_end, Rfine=(0.0, 0.001, -0.002))
    c.move(f_hold_end, f_cue, 'snap', Rfine=Vector(flick) * 0.5).move(f_cue, f_cue + 6, Rfine=(0.0, 0.0, 0.0))
    c.move(f_release, f_release + 2, Lapp=(0.0, 0.0, RELEASE3[2]), lhand=('support', 'cup', 1.0))
    c.move(f_release + 2, f_release + 4, Lapp=RELEASE3)
    c.k('L', f_release + 4, V2.L_side(), 'hold')
    c.move(f_release + 4, f_release + 9, Lsup=0.0)
    c.move(f_release + 9, f_lowered + 8, L='STAND', lhand=('cup', 'relaxed', 1.0))
    c.move(f_release + 6, f_lowered, R=V2.ready_R(-0.03), spine=(1, -4, 0), head=(0, -3, 0), shrug=(0, 0, 0), protract=(0, 0),
           knees=0)
    return R_aim


V2.aim_R = aim_R3
V2.ready_R = ready_R3
V2.aim_block = aim_block3


class Ctx3(M.Ctx):
    """v01 context on the v02 wrench: the carry base pose (Idle_Stand_v04 frame 1 + CARRY_DEV), the support hand
    pose, the wrench."""
    def __init__(self, rig, rest):
        super().__init__(rig, rest)
        pdw = self.base[P + 'RightHand'].col[2].xyz.normalized()
        self.carry_q = Quaternion(pdw, math.radians(CARRY_DEV))
        self.J0 = dict(self.J0)
        self.J0['RightHand'] = self.carry_q @ self.J0['RightHand']
        self.base = A.pose_from_joints(rig, rest, self.J0)
        self.stand = {s: self.arm_target_from_pose(self.base, s) for s in ('Left', 'Right')}
        self.locals.update({(s, 'support'): MR.hand_locals(rest, s, 'support') for s in ('Left', 'Right')})
        self.wrench = Wrench3(rig, rest)


def make_ctx(rig, rest):
    return Ctx3(rig, rest)


# ------------------------------------------------------------------ carry copies of the shared clips
def carry_pose(desired, rig, rest, C):
    """Turn the right hand (and its fingers) CARRY_DEV deg about its palm normal at the wrist; grip fingers."""
    Mh = desired[P + 'RightHand']
    W = Mh.translation.copy()
    pd = Mh.col[2].xyz.normalized()
    R = Matrix.Translation(W) @ Quaternion(pd, math.radians(CARRY_DEV)).to_matrix().to_4x4() @ Matrix.Translation(-W)
    for n in A.subtree(rig, 'RightHand'):
        desired[n] = R @ desired[n]
    MR.set_hand(desired, rig, rest, 'Right', C.locals[('Right', 'grip')])
    return desired


def bake_carry(C, src_action, name, scene):
    rig = C.rig
    rig.animation_data_create()
    MR.clear_nla(rig)
    rig.animation_data.action = src_action
    f0, f1 = (int(round(x)) for x in src_action.frame_range)
    frames = {}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        desired = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
        frames[f] = carry_pose(desired, rig, C.rest, C)
    act = RG.key_frames(rig, C.rest, frames, name)
    act.use_fake_user = True
    return act, (f0, f1)


SHARED = {'Mech_Idle_v03': ('Idle_Stand_v04', 'Idle', True), 'Mech_Walk_v03': ('Walk', 'Walk', True)}


def shared_actions():
    out = {}
    for key in ('Idle_Stand_v04', 'Walk'):
        with bpy.data.libraries.load(str(MR.SHARED_CLIPS[key]), link=False) as (a, b):
            b.actions = [n for n in a.actions if not n.endswith('_Face')][:1]
        out[key] = b.actions[0]
    return out


# ------------------------------------------------------------------ re-authored clips
class Clip3(V2.Clip2):
    """Clip2 + which side of the shank the left palm meets (under / top)."""
    side = 'under'

    def evaluate(self, C, f, info=None):
        SIDE['mode'] = self.side
        try:
            return super().evaluate(C, f, info)
        finally:
            SIDE['mode'] = 'under'


class Clip3T(Clip3):
    side = 'top'


def rename(c, old, new, note=None):
    c.name = c.name.replace(old, new)
    if note:
        c.note = note
    return c


def clip_gun_gag3(C):
    c = V2.clip_gun_gag(C)
    c.__class__ = Clip3
    return rename(c, '_v02', '_v03',
                  'v03 two-hand aim on the 0.84 m wrench: brings it up across the belly and shoulders it like a rifle (bladed '
                  'stance, upper body ~33 deg to his right, the wrench horizontal along his forward = at the van), right fist on '
                  'the rear part next to the rear jaw, elbow down and out, left palm up under the shank just behind the front jaw, '
                  'squints along it ~1 s with a mock-serious face, a silent "pew" with a tiny flick, lets go with the left hand, '
                  'lowers it to the carry, smug nod, idle.')


def clip_upgrade3(C):
    c = V2.clip_upgrade(C)
    c.__class__ = Clip3
    return rename(c, '_v02', '_v03',
                  'v03 upgrade performance on the 0.84 m wrench (the game turns him to face the van first): "watch this" nod, '
                  'shoulders the wrench like a rifle (bladed stance, the wrench horizontal at the van, right fist next to the rear '
                  'jaw, left palm under the shank behind the front jaw), aims ~1 s, a tiny recoil-free flick at Poof (the van puff '
                  'and the purchased change happen on that event, driven by the server, 1.70 s as v01/v02), lets go with the left '
                  'hand, lowers it to the carry, pleased grin, nod and a left thumbs-up; back to idle.')


def flex_R(C, elbow=45.0, arm_fwd=0.0, out=0.0):
    """The carry arm with the elbow bent forward-up by `elbow` deg (and the upper arm forward / out): the long part of
    the wrench swings from back-down through back-horizontal to up-back at his right side, clear of the body."""
    J = dict(C.J0)
    J['RightForeArm'] = A.R((1, 0, 0), -elbow) @ J['RightForeArm']
    if arm_fwd or out:
        J['RightArm'] = A.R((0, 1, 0), -out) @ A.R((1, 0, 0), -arm_fwd) @ J['RightArm']
    d = A.pose_from_joints(C.rig, C.rest, J)
    return C.arm_target_from_pose(d, 'Right')


def frame_se(t):
    """(fist, wrench front direction s, hand direction's square part e, pole) of a right target."""
    hd, pd = Vector(t['hd']).normalized(), Vector(t['pd']).normalized()
    jd = hd.cross(pd)
    d = math.radians(WV.DELTA)
    s = (-jd * math.cos(d) + hd * math.sin(d)).normalized()
    e = (hd - s * math.sin(d)) / math.cos(d)
    return Vector(t['pt']), s, (e - s * e.dot(s)).normalized(), Vector(t['pole']).normalized()


def path_R(a, b, k, via_s=None, dF=(0, 0, 0)):
    """A right target part way (k) from target a to b with the wrench direction through via_s (if given: a -> via ->
    b, piecewise slerp) and the hand direction blended in between, so the long part follows a chosen sweep."""
    Fa, sa, ea, pa = frame_se(a)
    Fb, sb, eb, pb = frame_se(b)
    if via_s is not None:
        v = Vector(via_s).normalized()
        sk = sa.slerp(v, k * 2) if k < 0.5 else v.slerp(sb, k * 2 - 1)
    else:
        sk = sa.slerp(sb, k)
    ek = ea.slerp(eb, k)
    F = Fa.lerp(Fb, k) + Vector(dF)
    return hold(F, sk, pa.slerp(pb, k), 0.0, e_hint=ek)


def shoulder_lo_R3():
    """On the way up to / down from the shoulder: the same wrench direction, lowered 15 cm and out to his right."""
    return held_R('shoulder', (-0.05, -0.06, -0.16))


def shoulder_R3():
    """Wrench on the right shoulder: the shank on the shoulder just behind the left-palm section, front jaw up behind
    him, fist in front at head height, forearm upright."""
    return held_R('shoulder')


def belt_L3():
    return M.belt_L()


def attend_R3(C):
    """Attention hold: the carry arm with the elbow bent ~50 deg, the wrench held angled at his right side (long part back,
    near horizontal, front jaw behind his hip, rear jaw forward). The v01 shoulder rest needs the fist at head height
    with this wrench (shoulder_R3) and its swing up there passed through the head; kept out."""
    return flex_R(C, 50.0, 12.0, 6.0)


def clip_attend_enter3(C):
    att = dict(R=attend_R3(C), L=belt_L3(), head=V(0, -3, 0), spine=V(-2, 0, 0))
    c = Clip3('Mech_Attend_Enter_v03', 24, role='MechAttend/Enter', state='Mech_Attend_Enter',
              note='Notices the player (brows up), straightens, lifts the big wrench to hold it angled at his right side (long '
                   'part back, near horizontal) and hooks his left thumb in the belt. Ends on the first frame of Mech_Attend_Loop_v03.')
    c.move(2, 8, 'snap', head=(0, -6, 0), spine=(-3, 0, 0))
    c.move(4, 16, 'over', R=att['R'])
    c.move(6, 18, L=att['L'])
    c.move(8, 18, head=att['head'], spine=att['spine'])
    c.face = [('Surprised', 2, 0.0), ('Surprised', 7, 0.35), ('Surprised', 16, 0.0)]
    c.key_poses = [1, 6, 11, 16, 24]
    c.end_base = False
    return c, att


def clip_attend_loop3(C, att):
    c = Clip3('Mech_Attend_Loop_v03', 120, loop=True, role='MechAttend/Loop', state='Mech_Attend_Loop',
              note='Listening to the player: the big wrench held angled at his right side, thumb in the belt, slow head tilts and '
                   'blinks, at 2.2 s a little impatient bounce of the wrench (event name kept: ShoulderTap); seamless loop.')
    for ch, v in att.items():
        c.ch[ch] = [(1, v, 'smooth')]
    c.move(1, 30, head=(4, -2, 5)).move(30, 56, head=(-3, -4, -3)).move(76, 96, head=(2, -1, 3)).move(96, 120, head=att['head'])
    c.move(56, 63, Rfine=(0, -0.01, 0.035)).move(63, 68, 'in', Rfine=(0, 0, 0)).move(68, 72, Rfine=(0, 0, 0.006)).move(72, 76, Rfine=(0, 0, 0))
    c.move(1, 60, spine=(-1, 1, 0)).move(60, 120, spine=att['spine'])
    c.face = [('Blink', 38, 0.0), ('Blink', 40, 1.0), ('Blink', 43, 0.0), ('Blink', 98, 0.0), ('Blink', 100, 1.0), ('Blink', 103, 0.0)]
    c.events = {'ShoulderTap': 68}
    c.key_poses = [1, 30, 63, 68, 96]
    return c


def clip_attend_exit3(C, att):
    c = Clip3('Mech_Attend_Exit_v03', 21, role='MechAttend/Exit', state='Mech_Attend_Exit',
              note='From the attention pose (Mech_Attend_Loop_v03 frame 1) back to the standing carry.')
    for ch, v in att.items():
        c.ch[ch] = [(1, v, 'smooth')]
    c.end_stand(3)
    c.key_poses = [1, 6, 11, 16, 21]
    c.start_base = False
    return c


def port_R(dz=0.0):
    """Port arms: fist at the right chest, the wrench up across the chest toward his left shoulder."""
    return held_R('port', (0, 0, dz))


def clip_cock_nod3(C):
    c = Clip3('Mech_Gag_CockNod_v03', 108, role='MechGag', state='Mech_Gag_CockNod',
              note='v03 on the big wrench: brings it up across his chest like a rifle at port arms, turns it to look at the '
                   'front jaw (left fist on the hip), "cocks" it with a sharp flick of the wrist (the wrench jolts), then a smug '
                   'slow nod with half-closed eyes; back to the carry.')
    hold0 = port_R()
    c.move(2, 8, R=V2.ready_R(), head=(-6, 10, 0), spine=(2, 2, 0))
    c.move(8, 14, R=hold0, head=(-14, 14, 0), spine=(2, 4, 0))
    c.move(4, 14, L=M.hip_L(), lhand='fist')
    c.move(16, 24, twist=22.0, head=(-18, 10, 6)).move(24, 34, twist=-18.0, head=(-12, 12, -6)).move(34, 40, twist=0.0, head=(-12, 12, 0))
    c.move(44, 49, 'in', twist=-14.0, head=(-12, 15, 0)).move(49, 51, 'snap', twist=10.0, Rfine=(0, 0, -0.022))
    c.move(51, 56, twist=0.0, Rfine=(0, 0, 0.003)).move(56, 60, Rfine=(0, 0, 0))
    c.move(60, 72, L='STAND', lhand='relaxed')
    c.move(60, 68, head=(0, -6, 4), R=port_R(dz=-0.03), spine=(-2, 0, 0))
    c.move(70, 77, head=(0, 13, 4)).move(77, 86, head=(0, -3, 3))
    c.move(86, 94, R=V2.ready_R())
    c.end_stand(94)
    c.face = [('Blink', 18, 0.0), ('Blink', 22, 0.35), ('Blink', 40, 0.35), ('Blink', 44, 0.0),
              ('Surprised', 49, 0.0), ('Surprised', 51, 0.5), ('Surprised', 56, 0.0),
              ('Happy', 60, 0.0), ('Happy', 68, 0.9), ('Happy', 92, 0.9), ('Happy', 104, 0.0),
              ('Blink', 62, 0.0), ('Blink', 68, 0.45), ('Blink', 90, 0.45), ('Blink', 98, 0.0)]
    c.events = {'Cock': 51, 'Nod': 77}
    c.key_poses = [1, 8, 14, 24, 34, 49, 51, 77, 108]
    return c


def clip_inspect_part3(C):
    """v01 InspectPart, the taps with the rear jaw (the short end, next to the fist) instead of v01's head."""
    c = M.clip_inspect_part()
    c.__class__ = Clip3
    for k in ('Lsup', 'Lapp', 'protract'):
        c.ch[k] = [(1, (0.0 if k == 'Lsup' else V(0, 0, 0)), 'smooth')]
    held = M.arm(V(0.060, -0.355, 1.320), M.nrm(-0.35, -0.45, 0.82), (-0.85, 0.35, 0.2), (1, 0.3, -0.6))
    part = held['pt'] + held['hd'] * 0.10      # just past the fingertips (the jaw head is big)
    h = HOLDS['tap']
    s = sdir(*h['s'])                       # the long part up and out to his right, the rear jaw toward the part
    F = part + s * (-REAR_U + 0.012)        # the rear jaw tip 1.2 cm short of the part
    tap = hold(F, s, nrm(*h['pole']), h['rho'])
    c.ch['R'] = [k for k in c.ch['R'] if k[0] < 64] + [(64, c.last('R', 64), 'linear'), (70, V2.ready_R(), 'smooth'), (76, tap, 'smooth')]
    c.ch['R'] = [k for k in c.ch['R']] + [(94, tap, 'linear'), (99, V2.ready_R(), 'smooth'), (104, 'STAND', 'smooth')]
    c.ch['R'].sort(key=lambda k: k[0])
    knock = -s * 0.016                       # toward the part
    c.ch['Rfine'] = [(1, V(0, 0, 0), 'smooth'), (77, V(0, 0, 0), 'linear'), (80, knock, 'in'), (84, V(0, 0, 0), 'smooth'),
                     (85, V(0, 0, 0), 'linear'), (88, knock, 'in'), (92, V(0, 0, 0), 'smooth')]
    return rename(c, '_v01', '_v03',
                  'At the workbench (bench top ~0.92 m, 0.45 m in front): picks up a small part with the left hand, holds it up '
                  'to his eyes and turns it, taps it twice with the rear jaw of the big wrench (the long part pointing down and '
                  'away to his right), a satisfied nod, puts it back. No part prop in the model: the left hand mimes it (a small '
                  'prop on mixamorig:LeftHand can be shown between PartUp and PartDown).')


def clip_wipe3(C):
    c = M.clip_wipe()
    c.__class__ = Clip3
    for k in ('Lsup', 'Lapp', 'protract'):
        c.ch[k] = [(1, (0.0 if k == 'Lsup' else V(0, 0, 0)), 'smooth')]
    return rename(c, '_v01', '_v03')


def clip_check_bay3(C):
    c = M.clip_check_bay()
    c.__class__ = Clip3
    for k in ('Lsup', 'Lapp', 'protract'):
        c.ch[k] = [(1, (0.0 if k == 'Lsup' else V(0, 0, 0)), 'smooth')]
    return rename(c, '_v01', '_v03')


def all_clips(C, names=None):
    enter, att = clip_attend_enter3(C)
    clips = [clip_gun_gag3(C), clip_cock_nod3(C), clip_inspect_part3(C), clip_wipe3(C), clip_check_bay3(C), enter,
             clip_attend_loop3(C, att), clip_attend_exit3(C, att), clip_upgrade3(C)]
    if names:
        clips = [c for c in clips if c.name in names or c.name.rsplit('_v', 1)[0] in names]
    return clips


# ------------------------------------------------------------------ build
def build(model=MODEL, names=None, carry=True):
    rig, rest = MR.open_model(model)
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
    for c in all_clips(C, names):
        frames = c.frames(C)
        act, ground = M.ground_and_key(C, c, frames, meshes, scene)
        fa = GG.face_action(face, c.name + '_Face', c.face) if c.face else None
        out.append((c, act, fa, ground))
        print(f'[ANIM] {c.name} frames {c.length} seam_dev_mm {c.seam_dev_mm} ground {ground}')
    carried = []
    if carry:
        src = shared_actions()
        for name, (key, state, loop) in SHARED.items():
            act, fr = bake_carry(C, src[key], name, scene)
            carried.append((name, key, state, loop, act, fr))
            print(f'[CARRY] {name} from {key} frames {fr}')
    return rig, rest, scene, grip, out, carried, C


# ------------------------------------------------------------------ measurements on the posed meshes
def _weights(o):
    gi = {g.index: g.name for g in o.vertex_groups}
    return [{gi[g.group]: g.weight for g in v.groups} for v in o.data.vertices]


class Probe3:
    """Per frame: wrench vs skin / cloth / face / floor, the left palm on the wrench, hands apart, the left arm vs
    the torso, the backward aim axis, wrist angles."""
    def __init__(self, rig, rest):
        self.rig, self.rest = rig, rest
        self.body, self.outfit = bpy.data.objects['Body'], bpy.data.objects['Outfit']
        self.face, self.wr = bpy.data.objects['Face'], bpy.data.objects['Wrench_RightHand']
        self.w = {o.name: _weights(o) for o in (self.body, self.outfit)}

        def rarm(ws):
            return sum(v for k, v in ws.items() if k.startswith(P + 'RightHand') or k == P + 'RightForeArm') > 0.3

        def armw(ws):
            return sum(v for k, v in ws.items() if any(k == P + s + b for s in ('Left', 'Right') for b in ('Arm', 'ForeArm'))
                       or k.startswith(P + 'LeftHand') or k.startswith(P + 'RightHand'))
        self.keep_b = [i for i, ws in enumerate(self.w['Body']) if not rarm(ws)]
        self.keep_o = [i for i, ws in enumerate(self.w['Outfit']) if not rarm(ws)]
        self.lhand = [i for i, ws in enumerate(self.w['Body']) if sum(v for k, v in ws.items() if k.startswith(P + 'LeftHand')) > 0.5]
        self.rhand = [i for i, ws in enumerate(self.w['Body']) if sum(v for k, v in ws.items() if k.startswith(P + 'RightHand')) > 0.5]
        self.torso = [i for i, ws in enumerate(self.w['Body']) if armw(ws) < 0.2]
        self.larm = [i for i, ws in enumerate(self.w['Body'])
                     if sum(v for k, v in ws.items() if k == P + 'LeftForeArm' or k.startswith(P + 'LeftHand')) > 0.5]
        Mi = rest[P + 'RightHand'].inverted()
        us = [(Mi @ (self.wr.matrix_world @ v.co) - WV.CENTRE).dot(AX) for v in self.wr.data.vertices]
        self.wr_free = [i for i, u in enumerate(us) if not (WV.GRIP[0] - 0.012 <= u <= WV.GRIP[1] + 0.012)]
        mats = self.outfit.data.materials
        self.vmat = {}
        for p in self.outfit.data.polygons:
            for i in p.vertices:
                self.vmat[i] = mats[p.material_index].name

    mesh = staticmethod(V2.Probe.mesh)
    bvh = staticmethod(V2.Probe.bvh)
    signed = staticmethod(V2.Probe.signed)

    def frame(self, scene, f, aim=False):
        from mathutils.kdtree import KDTree
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
        skin = self.bvh([(B, Bp, self.keep_b)])
        kd = KDTree(len(self.keep_o))
        for j, i in enumerate(self.keep_o):
            kd.insert(O[i], j)
        kd.balance()
        wf = [Wc[i] for i in self.wr_free]
        res['wrench_vs_skin_mm'] = round(min(self.signed(skin, q) for q in wf) * 1000, 1)
        cl = min((kd.find(q)[2], self.keep_o[kd.find(q)[1]]) for q in wf)
        res['wrench_vs_cloth_mm'] = round(cl[0] * 1000, 1)
        res['wrench_vs_cloth_part'] = self.vmat.get(cl[1], '?')
        headt = self.bvh([(Fc, Fp, range(len(Fc)))])
        res['wrench_vs_face_mm'] = round(min(self.signed(headt, q) for q in Wc) * 1000, 1)
        res['wrench_floor_mm'] = round((min(q.z for q in Wc) - min(q.z for q in O)) * 1000, 1)
        wt = self.bvh([(Wc, Wp, range(len(Wc)))])
        lh = [B[i] for i in self.lhand]
        dl = [self.signed(wt, q, 0.015) for q in lh]
        res['lefthand_to_wrench_min_mm'] = round(min(dl) * 1000, 1)
        res['lefthand_verts_within_4mm'] = sum(1 for d in dl if abs(d) <= 0.004)
        res['lefthand_into_wrench_max_mm'] = round(max(0.0, -min(dl)) * 1000, 1)
        kr = KDTree(len(self.rhand))
        for j, i in enumerate(self.rhand):
            kr.insert(B[i], j)
        kr.balance()
        res['lefthand_to_righthand_min_mm'] = round(min(kr.find(q)[2] for q in lh) * 1000, 1)
        torso = self.bvh([(B, Bp, self.torso)])
        res['leftarm_vs_skin_mm'] = round(min(self.signed(torso, B[i]) for i in self.larm[::2]) * 1000, 1)
        if aim:
            rear = Mr @ WV.point(REAR_U)
            back = -(Mr.to_3x3() @ AX).normalized()
            rset = set(self.rhand)
            body_all = self.bvh([(B, Bp, [i for i in range(len(B)) if i not in rset]), (O, Op, range(len(O)))])
            hit = body_all.ray_cast(rear + back * 0.0005, back, 0.6)
            S = mw @ pb[P + 'RightArm'].head
            if hit[0] is not None:
                hp = hit[0]
                near = min(range(len(B)), key=lambda i: (B[i] - hp).length)
                nearO = min(range(len(O)), key=lambda i: (O[i] - hp).length)
                src, i = ('Body', near) if (B[near] - hp).length <= (O[nearO] - hp).length else ('Outfit', nearO)
                top = sorted(self.w[src][i].items(), key=lambda kv: -kv[1])[:2]
                res['axis_hit'] = {'gap_from_rear_jaw_mm': round(hit[3] * 1000, 1), 'point': [round(x, 3) for x in hp],
                                   'below_shoulder_joint_mm': round((S.z - hp.z) * 1000, 1), 'mesh': src,
                                   'bones': [(k.replace(P, ''), round(v, 2)) for k, v in top]}
            else:
                res['axis_hit'] = None
            fwd = -back
            res['wrench_pitch_deg'] = round(math.degrees(math.asin(max(-1, min(1, fwd.z)))), 1)
            res['wrench_yaw_deg'] = round(math.degrees(math.atan2(fwd.x, -fwd.y)), 1)
        for side in ('Right', 'Left'):
            Mh = mw @ pb[P + side + 'Hand'].matrix
            E = mw @ pb[P + side + 'ForeArm'].head
            Sh = mw @ pb[P + side + 'Arm'].head
            f_ = (Mh.translation - E).normalized()
            hd = Mh.col[1].xyz.normalized()
            q = Mh.to_quaternion() @ self.rest[P + side + 'Hand'].to_quaternion().inverted()
            pd = (q @ Vector((0, 0, -1))).normalized()
            th = hd.cross(pd) if side == 'Right' else pd.cross(hd)
            res[side] = {'ulnar_dev_deg': round(math.degrees(math.asin(max(-1, min(1, f_.dot(th))))), 1),
                         'extension_deg': round(math.degrees(math.atan2(f_.dot(pd), f_.dot(hd))), 1),
                         'wrist_total_deg': round(math.degrees(math.acos(max(-1, min(1, f_.dot(hd))))), 1),
                         'elbow_below_shoulder_mm': round((Sh.z - E.z) * 1000, 1)}
        return res


def check(rig, rest, scene, built, carried, C, step=1):
    probe = Probe3(rig, rest)
    MR.clear_nla(rig)
    out = {}
    items = [(c.name, act, c, c.length) for c, act, fa, g in built] + [(n, act, None, fr[1]) for n, k, s, l, act, fr in carried]
    for name, act, c, length in items:
        rig.animation_data.action = act
        rows = []
        f0 = int(act.frame_range[0])
        for f in range(f0, length + 1, step):
            aim = c is not None and Channel(c.ch['Lsup']).at(f, mix_num) >= 0.999 and 'Wrench' in c.name or (c is not None and 'Upgrade' in c.name and Channel(c.ch['Lsup']).at(f, mix_num) >= 0.999)
            r = probe.frame(scene, f, aim=aim)
            r['support_weight'] = round(Channel(c.ch['Lsup']).at(f, mix_num), 3) if c is not None else 0.0
            rows.append(r)

        def worst(key, rs, fn=min):
            rs = [r for r in rs if r.get(key) is not None]
            if not rs:
                return None
            r = fn(rs, key=lambda x: x[key])
            return {'value': r[key], 'frame': r['frame']}
        held = [r for r in rows if r['support_weight'] >= 0.999]
        aimed = [r for r in held if 'wrench_pitch_deg' in r]
        s = {'frames_checked': len(rows),
             'min_wrench_vs_skin_mm': worst('wrench_vs_skin_mm', rows), 'min_wrench_vs_cloth_mm': worst('wrench_vs_cloth_mm', rows),
             'min_wrench_vs_face_mm': worst('wrench_vs_face_mm', rows), 'min_wrench_floor_mm': worst('wrench_floor_mm', rows),
             'min_leftarm_vs_skin_mm': worst('leftarm_vs_skin_mm', rows),
             'min_lefthand_to_wrench_mm': worst('lefthand_to_wrench_min_mm', rows),
             'max_lefthand_into_wrench_mm': worst('lefthand_into_wrench_max_mm', rows, max),
             'min_lefthand_to_righthand_mm': worst('lefthand_to_righthand_min_mm', rows)}
        s['cloth_part_at_min'] = next((r['wrench_vs_cloth_part'] for r in rows if s['min_wrench_vs_cloth_mm'] and r['frame'] == s['min_wrench_vs_cloth_mm']['frame']), None)
        for side in ('Right', 'Left'):
            rs = [r for r in rows if side in r]
            s[side + '_max_wrist_total_deg'] = worst('x', [{'x': r[side]['wrist_total_deg'], 'frame': r['frame']} for r in rs], max)
            s[side + '_max_abs_ulnar_dev_deg'] = worst('x', [{'x': abs(r[side]['ulnar_dev_deg']), 'frame': r['frame']} for r in rs], max)
            s[side + '_held_max_wrist_total_deg'] = worst('x', [{'x': r[side]['wrist_total_deg'], 'frame': r['frame']} for r in held], max)
        if held:
            s['support_frames'] = [held[0]['frame'], held[-1]['frame']]
            s['held_max_lefthand_into_wrench_mm'] = worst('lefthand_into_wrench_max_mm', held, max)
            s['held_min_lefthand_verts_within_4mm'] = worst('lefthand_verts_within_4mm', held)
            s['held_max_lefthand_to_wrench_mm'] = worst('lefthand_to_wrench_min_mm', held, max)
            s['held_min_hands_apart_mm'] = worst('lefthand_to_righthand_min_mm', held)
        if aimed:
            hits = [r['axis_hit'] for r in aimed if r['axis_hit']]
            s['aim_frames'] = len(aimed)
            s['aim_pitch_deg'] = [min(r['wrench_pitch_deg'] for r in aimed), max(r['wrench_pitch_deg'] for r in aimed)]
            s['aim_yaw_deg'] = [min(r['wrench_yaw_deg'] for r in aimed), max(r['wrench_yaw_deg'] for r in aimed)]
            s['aim_axis_hits'] = sorted({h['bones'][0][0] for h in hits}) + (['none'] if len(hits) < len(aimed) else [])
            if hits:
                s['aim_axis_below_shoulder_mm'] = [min(h['below_shoulder_joint_mm'] for h in hits), max(h['below_shoulder_joint_mm'] for h in hits)]
                s['aim_axis_gap_from_rear_jaw_mm'] = [min(h['gap_from_rear_jaw_mm'] for h in hits), max(h['gap_from_rear_jaw_mm'] for h in hits)]
        out[name] = {'summary': s, 'frames': rows}
        print('[CHECK]', name, json.dumps(s))
    return out


# ------------------------------------------------------------------ previews
def keyframe_sheet(rig, scene, cam, col, name, act, fa, poses, events, folder, C, axis=None):
    """Key-pose strip (side, 3/4 R, 3/4 L) of one action; axis(f) -> True draws the wrench axis to the body hit."""
    folder = Path(folder)
    face = bpy.data.objects['Face']
    probe = Probe3(rig, C.rest)
    rig.animation_data.action = act
    sk = face.data.shape_keys
    sk.animation_data_create()
    sk.animation_data.action = fa
    files, labels = [], []
    for f in poses:
        scene.frame_set(f)
        if axis and axis(f):
            r = probe.frame(scene, f, aim=True)
            Mr = rig.matrix_world @ rig.pose.bones[P + 'RightHand'].matrix
            draw_axis(col, Mr, r.get('axis_hit'))
        else:
            V2._hide('AxisLine', 'HitMark', 'SupportMark')
        hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
        tgt = Vector((hips.x, hips.y, 0.95))
        for tag, view in (('s', 'side_full'), ('q', 'full34'), ('l', 'full34L')):
            p = folder / name / f'{name}_f{f:03d}_{tag}.png'
            V2.shoot(scene, cam, p, view, tgt, (360, 520))
            files.append(p)
        ev = [k for k, v in events.items() if v == f]
        labels += [f'f{f} side' + (f' {ev[0]}' if ev else ''), f'f{f} 3/4 R', f'f{f} 3/4 L']
    sheet = folder / f'{name}_strip.png'
    cmd = ['magick', 'montage']
    for p, lab in zip(files, labels):
        cmd += ['-label', lab, str(p)]
    cmd += ['-tile', '6x', '-geometry', '240x347+2+2', '-pointsize', '13', '-depth', '8', '-title', name, str(sheet)]
    subprocess.run(cmd, check=False)
    sk.animation_data.action = None
    V2._hide('AxisLine', 'HitMark', 'SupportMark')
    return sheet


def draw_axis(col, Mr, hit):
    """Red rod along the wrench axis from 3 cm past the front jaw to the body hit (or 0.4 m past the rear jaw)."""
    import bmesh
    fwd = (Mr.to_3x3() @ AX).normalized()
    a = Mr @ WV.point(FRONT_U + 0.03)
    b = Vector(hit['point']) if hit else Mr @ WV.point(REAR_U) - fwd * 0.4
    obj = bpy.data.objects.get('AxisLine')
    if obj is None:
        me = bpy.data.meshes.new('AxisLine')
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.0035, radius2=0.0035, depth=1.0)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(V2._emissive('AxisLine_Mat', (1.0, 0.05, 0.02)))
        obj = bpy.data.objects.new('AxisLine', me)
        col.objects.link(obj)
    d = b - a
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    obj.matrix_world = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((1, 1, d.length, 1))
    obj.hide_render = False
    if hit:
        V2.marker(col, 'HitMark', Vector(hit['point']), r=0.011, color=(1.0, 0.85, 0.05))
    else:
        V2._hide('HitMark')


def aim_views(rig, scene, cam, col, c, act, fa, f, folder, C, tag='v03'):
    """Annotated aim views of one frame: side (axis + its extension, 2D overlay), 3/4 front R / L, from below."""
    folder = Path(folder)
    face = bpy.data.objects['Face']
    probe = Probe3(rig, C.rest)
    rig.animation_data.action = act
    sk = face.data.shape_keys
    sk.animation_data_create()
    sk.animation_data.action = fa
    scene.frame_set(f)
    info = {}
    c.evaluate(C, f, info)
    r = probe.frame(scene, f, aim=True)
    Mr = rig.matrix_world @ rig.pose.bones[P + 'RightHand'].matrix
    h = r.get('axis_hit')
    draw_axis(col, Mr, h)
    if info.get('sup'):
        V2.marker(col, 'SupportMark', info['sup']['contact'], r=0.008)
    hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
    tgt = Vector((hips.x - 0.05, hips.y - 0.22, 1.10))
    pts = {'front': Mr @ WV.point(FRONT_U), 'rear': Mr @ WV.point(REAR_U), 'hit': Vector(h['point']) if h else None,
           'fist': Mr @ WV.CENTRE, 'palm': info['sup']['contact'] if info.get('sup') else None}
    legend = 'red: axis, dashed: its extension, yellow: hit, green: fist, blue: palm'
    notes = {
        'side': [f'{c.name} f{f}: side (from his right)',
                 f'wrench {r["wrench_pitch_deg"]:+.0f} deg pitch, {r["wrench_yaw_deg"]:+.0f} deg yaw (along his forward = at the van)',
                 (f'backward extension meets the right upper arm {h["below_shoulder_joint_mm"] / 10:.1f} cm below the shoulder joint,') if h else 'axis: no hit',
                 (f'{h["gap_from_rear_jaw_mm"] / 10:.1f} cm behind the rear jaw tip') if h else '', legend],
        'front34R': [f'{c.name} f{f}: 3/4 front right', f'right wrist {r["Right"]["wrist_total_deg"]:.0f} deg, left wrist {r["Left"]["wrist_total_deg"]:.0f} deg',
                     f'hands {r["lefthand_to_righthand_min_mm"] / 10:.1f} cm apart'],
        'front34L': [f'{c.name} f{f}: 3/4 front left', f'left palm to wrench {r["lefthand_to_wrench_min_mm"]:.1f} mm, {r["lefthand_verts_within_4mm"]} verts within 4 mm', legend],
        'below34': [f'{c.name} f{f}: from below right', 'left palm up under the shank, right fist round the grip'],
    }
    files = []
    V2.VIEWS['side_aim'] = (Vector((-2.6, 0.0, 0.05)), 'ortho', 1.35)
    for view in ('side', 'front34R', 'front34L', 'below34'):
        p = folder / f'{c.name}_f{f:03d}_aim_{view}.png'
        if view == 'side':
            V2.shoot(scene, cam, p, 'side_aim', tgt + Vector((0, -0.22, 0)), (860, 860))
        else:
            V2.shoot(scene, cam, p, view, tgt, (700, 860))
        if view in ('side', 'front34L'):
            V2._overlay(p, scene, cam, pts)
        V2._annotate(p, notes[view])
        files.append(p)
    sk.animation_data.action = None
    V2._hide('AxisLine', 'HitMark', 'SupportMark')
    return files, r


# ------------------------------------------------------------------ export, manifest
def export_actions(blend, names, out_dir):
    for name, fbx_name in names:
        fbx = out_dir / fbx_name
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


def manifest_v03(built, carried, rig):
    v01 = json.loads((V01_DIR / 'clips_mechanic_v01.json').read_text(encoding='utf-8'))
    new = {}
    for c, act, fa, ground in built:
        new[c.state] = {
            'role': c.role, 'state': c.state, 'file': c.name + '.fbx', 'take': c.name,
            'source': f'ArtSource/Characters/MECHANIC_W86/Animations_v03/{c.name}.fbx',
            'loop': c.loop, 'frames': [1, c.length], 'fps': FPS, 'seconds': round((c.length - 1) / FPS, 4),
            'events': {k: {'frame': v, 'seconds': round((v - 1) / FPS, 4), 'fraction': round((v - 1) / (c.length - 1), 4)} for k, v in c.events.items()},
            'face_cues': [{'shape': s, 'frame': f, 'seconds': round((f - 1) / FPS, 4), 'value': v} for s, f, v in sorted(c.face, key=lambda k: (k[1], k[0]))],
            'face_track_blend': (c.name + '_Face') if c.face else None,
            'grounding_hips_shift_m': ground, 'seam_deviation_mm': c.seam_dev_mm, 'note': c.note, 'revision': 'v03'}
    clips = [new.get(e['state'], e) for e in v01['clips']]
    carry = [{'role': 'Mech' + state, 'state': state, 'file': name + '.fbx', 'take': name,
              'source': f'ArtSource/Characters/MECHANIC_W86/Animations_v03/{name}.fbx', 'loop': loop, 'frames': list(fr),
              'fps': FPS, 'seconds': round((fr[1] - fr[0]) / FPS, 4), 'from_shared': key,
              'note': f'{key} with the right hand turned {CARRY_DEV:.0f} deg in the palm plane (the big wrench clear of the leg, '
                      f'pouch and floor); replaces the shared clip in his controller state "{state}".'}
             for name, key, state, loop, act, fr in carried]
    return {'comment': 'MECHANIC_W86 clips v03 (Blender, Claude 2026-10-29): the full manifest in the clips_mechanic_v01.json '
                       'format for the 0.84 m wrench v02 (MECHANIC_W86_v02_opt_v02.fbx). Every clip entry points at a v03 FBX '
                       'in Animations_v03 (same Animator state names, lengths and event frames as v02: WrenchGun 126 frames, Pew '
                       '50; Upgrade 138 frames, Poof 52 = 1.70 s). carry_clips: his own copies of the shared Idle_Stand_v04 / '
                       'Walk_v04 for the states Idle and Walk. grip_clip: Grip_R v02 (the oblique grip), same bones.',
            'grip_clip': {'file': 'MECHANIC_W86_Grip_R_v02.fbx', 'take': 'Grip_R', 'frames': [1, 2],
                          'keyed_bones': MR.hand_children(rig, 'Right'),
                          'source': 'ArtSource/Characters/MECHANIC_W86/Animations_v03/MECHANIC_W86_Grip_R_v02.fbx'},
            'carry_clips': carry, 'clips': clips}


def before_after(prev, v03_views):
    """v02 (left, the 0.27 m wrench) vs v03 (right) at the aim hold, side and 3/4 front right, the same cameras."""
    import buddy_render as RD
    bpy.ops.wm.open_mainfile(filepath=str(V02_DIR / 'MECHANIC_W86_Anim_v02.blend'))
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
    for name, (f3, files3) in v03_views.items():
        v2 = name.replace('_v03', '_v02')
        f2 = 38 if 'Wrench' in name else 40
        rig.animation_data.action = bpy.data.actions[v2]
        sk = face.data.shape_keys
        sk.animation_data_create()
        sk.animation_data.action = bpy.data.actions.get(v2 + '_Face')
        scene.frame_set(f2)
        Mr = rig.matrix_world @ rig.pose.bones[P + 'RightHand'].matrix
        V2.axis_line(col, Mr, front_sign=-1)
        hips = rig.matrix_world @ rig.pose.bones[P + 'Hips'].head
        tgt = Vector((hips.x - 0.05, hips.y - 0.22, 1.10))
        files2 = []
        V2.VIEWS['side_aim'] = (Vector((-2.6, 0.0, 0.05)), 'ortho', 1.35)
        for view in ('side', 'front34R'):
            p = prev / 'v02_compare' / f'{v2}_f{f2:03d}_{view}.png'
            if view == 'side':
                V2.shoot(scene, cam, p, 'side_aim', tgt + Vector((0, -0.22, 0)), (860, 860))
            else:
                V2.shoot(scene, cam, p, view, tgt, (700, 860))
            files2.append(p)
        V2._annotate(files2[0], [f'BEFORE {v2} f{f2}: wrench 0.27 m, square grip', 'wrist 43 deg deviation + 63 deg flexion, 2.8 cm of shank between the hands'])
        V2._annotate(files2[1], [f'BEFORE {v2} f{f2}'])
        sheet = prev / f'{name}_before_after_v02.png'
        subprocess.run(['magick', 'montage', str(files2[0]), str(files3[0]), str(files2[1]), str(files3[1]), '-tile', '2x',
                        '-geometry', '640x640>+3+3', '-depth', '8', '-title', f'{v2} (left, before)  vs  {name} (right, after)',
                        '-pointsize', '14', str(sheet)], check=False)
        sheets.append(sheet)
        sk.animation_data.action = None
    return sheets


def final(model=MODEL):
    OUT_DIR.mkdir(exist_ok=True)
    blend = OUT_DIR / 'MECHANIC_W86_Anim_v03.blend'
    man = OUT_DIR / 'clips_mechanic_v03.json'
    chk = OUT_DIR / 'check_v03.json'
    for p in (blend, man, chk):
        if p.exists():
            sys.exit(f'Refusing to overwrite {p}')
    rig, rest, scene, grip, built, carried, C = build(model)
    report = check(rig, rest, scene, built, carried, C, step=1)
    chk.write_text(json.dumps({'comment': 'Per-frame checks on the posed LOD0 meshes (mm, deg), MECHANIC_W86 v03 clips on the '
                                          'v02 wrench. skin = Body (closed mesh, without the right forearm and hand) signed '
                                          'distance to the wrench outside the grip; cloth = nearest Outfit vertex (unsigned); '
                                          'face = Face mesh signed; floor = lowest wrench point above the boot soles; lefthand = '
                                          'left mitten vs the wrench (into = deepest overlap, within 4 mm = contact); axis = ray '
                                          'from the rear jaw tip backward along the shank (aim frames with the left hand on); '
                                          'wrists: forearm vs hand total bend.', 'aim': V2.AIM, 'support': V2.SUP,
                               'carry_dev_deg': CARRY_DEV, 'holds': HOLDS, 'wrench': {'delta_deg': WV.DELTA, 'length_m': round(FRONT_U - REAR_U, 3)},
                               'clips': report}, indent=1, default=str), encoding='utf-8')
    man.write_text(json.dumps(manifest_v03(built, carried, rig), indent=1, ensure_ascii=False), encoding='utf-8')
    MR.clear_nla(rig)
    rig.animation_data.action = bpy.data.actions['Idle'] if 'Idle' in bpy.data.actions else None
    for a in bpy.data.actions:
        a.use_fake_user = True
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    import buddy_render as RD
    col, cam, floor = RD.studio(scene)
    scene.cycles.samples = 24
    prev = OUT_DIR / 'Previews'
    views = {}
    for c, act, fa, g in built:
        aim = 'Wrench' in c.name or 'Upgrade' in c.name
        keyframe_sheet(rig, scene, cam, col, c.name, act, fa, c.key_poses, c.events, prev, C,
                       axis=(lambda f, c=c: Channel(c.ch['Lsup']).at(f, mix_num) >= 0.999) if aim else None)
        if aim:
            files, r = aim_views(rig, scene, cam, col, c, act, fa, c.key_poses[4], prev, C)
            views[c.name] = (c.key_poses[4], files)
    for n, k, st, l, act, fr in carried:
        fl = sorted(set(list(range(fr[0], fr[1] + 1, max(1, (fr[1] - fr[0]) // 5))) + [fr[1]]))
        keyframe_sheet(rig, scene, cam, col, n, act, None, fl, {}, prev, C)
    names = [(c.name, c.name + '.fbx') for c, *_ in built] + [(n, n + '.fbx') for n, *_ in carried] + [('Grip_R', 'MECHANIC_W86_Grip_R_v02.fbx')]
    export_actions(blend, names, OUT_DIR)
    ba = before_after(prev, views)
    print('[FINAL] done', [str(x) for x in ba])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', default=None)
    ap.add_argument('--model', default=None)
    ap.add_argument('--clips', default='')
    ap.add_argument('--nocarry', action='store_true')
    ap.add_argument('--step', type=int, default=2)
    ap.add_argument('--render', action='store_true')
    ap.add_argument('--final', action='store_true')
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    model = Path(args.model) if args.model else MODEL
    names = [n for n in args.clips.split(',') if n]
    if args.test:
        out = Path(args.test)
        out.mkdir(parents=True, exist_ok=True)
        rig, rest, scene, grip, built, carried, C = build(model, names, carry=not args.nocarry)
        rep = check(rig, rest, scene, built, carried, C, step=args.step)
        (out / 'check.json').write_text(json.dumps({k: v['summary'] for k, v in rep.items()}, indent=1, default=str), encoding='utf-8')
        if args.render:
            import buddy_render as RD
            col, cam, floor = RD.studio(scene)
            scene.cycles.samples = 12
            for c, act, fa, g in built:
                aimf = (lambda f, c=c: 'Wrench' in c.name or 'Upgrade' in c.name) if c.ch['Lsup'] else None
                keyframe_sheet(rig, scene, cam, col, c.name, act, fa, c.key_poses, c.events, out, C,
                               axis=(lambda f, c=c: Channel(c.ch['Lsup']).at(f, mix_num) >= 0.999 and ('Wrench' in c.name or 'Upgrade' in c.name)))
                if 'Wrench' in c.name or 'Upgrade' in c.name:
                    aim_views(rig, scene, cam, col, c, act, fa, c.key_poses[4], out, C)
            for n, k, s, l, act, fr in carried:
                fl = list(range(fr[0], fr[1] + 1, max(1, (fr[1] - fr[0]) // 5)))
                keyframe_sheet(rig, scene, cam, col, n, act, None, fl, {}, out, C)
        return
    if args.final:
        final(model)


if __name__ == '__main__':
    main()
