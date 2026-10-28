"""Forest_v01 clips (Sausage Buddy rig Buddy_Rig_Mixamo65, 65 bones; previewed on FOREST_OD_JUNKIE, whose rig is
identical to A v04): Junkie_Walk, Inject, High_Lie_Loop. Original procedural keyframe animation.

Built on the Crowd_v01 posing core (crowd_core.Rig / Track / FitTrack, clips_stand._fill) and the shared
Idle_Knock_v03 library (acting_core), both imported read-only. Conventions are crowd_core's: the character faces -Y,
left = +X, +Z up, metres, 30 fps, one-sided parameters written for the LEFT side (x outward).

ForestRig (extends crowd_core.Rig; nothing in Crowd_v01 changes):
  ik<k>.ow 0..1      turn the hand before the arm IK so its hand-local +Y (fingers = the syringe needle) points along
                     ik<k>.dx/dy/dz and its palm normal (+Z) toward ik<k>.ux/uy/uz. Both are Idle-space vectors
                     (x outward) carried by the bone ik<k>.orel (else ik<k>.rel). The IK then puts the reach point on
                     the target, so the needle tip, not the knuckles, lands where it is aimed.
  reach points       right hand 'tip' (syringe needle tip), 'back' (back of the fingers); left hand 'index'
                     (index fingertip, finger straight)
  ikL.late 1         solve the left arm IK after the right one (targets riding mixamorig:RightHand)
  f<k>.sole 0..1     shift the foot vertically so its lowest shoe vertex (rigid foot) sits on the floor (lying/sitting)
"""
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CROWD = HERE.parent / 'Crowd_v01'
if str(CROWD) not in sys.path:
    sys.path.insert(0, str(CROWD))
import numpy as np
from mathutils import Vector, Matrix, Quaternion
import crowd_core as K
import acting_core as C
from crowd_core import add, window, bump, smooth
from clips_stand import _fill, keys
from clips_props import POCKET_R

REV = 'v01'
P = K.P
FPS = K.FPS

# ------------------------------------------------------------------------------------- the syringe (existing prop)
# SYRINGE-ASTRA-001.fbx: origin at the needle tip, long axis local +Z (needle tip z = 0 -> thumb pad z = 0.24 m with
# the plunger pulled out; CTRL_PlungerTravel_Z local z 0 = pulled out, -0.048 = pushed in). Held in a dart grip:
# barrel along the fingers on the palm side, needle beyond the fingertips, flange at the middle finger joints.
# Hand frame = Blender pose-bone frame of mixamorig:RightHand (origin at the wrist joint, +Y toward the fingers,
# +X thumb/index side, +Z palm normal).
SYRINGE = {
    'bone': P + 'RightHand',
    'fbx': r'C:\Users\chern_0eqkb03\Desktop\GAME\ArtSource\Props\SYRINGE-ASTRA-001\SYRINGE-ASTRA-001.fbx',
    'tip': (0.012, 0.215, 0.045),          # needle tip = prop origin, hand frame (m)
    'rot_wxyz': (0.7660444, 0.6427876, 0.0, 0.0),   # +80 deg about hand X: prop +Z (tip -> plunger) ~ hand -Y, tilted
                                                    # 10 deg so the plunger end clears the wrist on the palm side
    'plunger_out': 0.0, 'plunger_in': -0.048,
    'hide': ('SM_BloodVolume_FILL_Z',),     # cartoon, no blood: the fill mesh stays hidden
}
NEEDLE_AXIS = Vector((0.0, 0.9848078, -0.1736482))   # hand-local needle direction (tip side)
FINGER_AXIS = Vector((0.0, 1.0, 0.0))


def syringe_matrix():
    q = Quaternion(SYRINGE['rot_wxyz'])
    m = q.to_matrix().to_4x4()
    m.translation = Vector(SYRINGE['tip'])
    return m


# Idle frame-1 matrices used to express targets in Idle space (read from A v04 with probe output, 4 decimals)
R_HAND_IDLE = Matrix(((-0.0323, -0.1578, 0.9869, -0.3146),
                      (-0.9511, -0.2988, -0.0789, -0.0782),
                      (0.3073, -0.9412, -0.1405, 0.7516),
                      (0.0, 0.0, 0.0, 1.0)))
# The presented left forearm (ARM_OUT_L on the slouched stance, probe output): mixamorig:LeftForeArm world matrix
# times its Idle matrix inverse. Points/directions are designed in that presented pose and turned into Idle-space
# values carried by the forearm (ik rel/orel 'LeftForeArm'), so they stay on the arm through the sway.
R_PRES = Matrix(((0.056373, -0.945384, 0.321047, -0.103494),
                 (0.021419, 0.32263, 0.946283, -1.073262),
                 (-0.99818, -0.046468, 0.038437, 1.163091),
                 (0.0, 0.0, 0.0, 1.0)))
_RP_INV = R_PRES.inverted()


def pres_pt(v):
    return _RP_INV @ Vector(v)


def pres_dir(v):
    return (_RP_INV.to_3x3() @ Vector(v)).normalized()


def lx(v):
    """World (Idle) vector -> right-hand parameter triple (x outward = -world x)."""
    return (-v.x, v.y, v.z)


def hand_rot(d, u, axis=None):
    """Hand rotation (world 3x3) whose hand-local `axis` (default the syringe needle) points along d and whose palm
    normal (+Z) turns toward u."""
    a1 = Vector(axis or NEEDLE_AXIS).normalized()
    a2 = Vector((0.0, 0.0, 1.0))
    a2 = (a2 - a1 * a2.dot(a1)).normalized()
    b1 = d.normalized()
    b2 = (u - b1 * u.dot(b1)).normalized()
    Mw = Matrix((b1, b2, b1.cross(b2))).transposed()
    Ml = Matrix((a1, a2, a1.cross(a2))).transposed()
    return Mw @ Ml.transposed()


def tip_for_contact(contact, local_pt, d, u):
    """Idle-space needle-tip target that puts the hand-local point local_pt on `contact` with orientation (d, u)."""
    Rw = hand_rot(d, u)
    return contact + Rw @ (Vector(SYRINGE['tip']) - Vector(local_pt))


def r_ik(tgt, d, u, rel, extra=None):
    """Right-arm IK snippet: needle tip on tgt, needle along d, palm toward u (Idle-space values carried by `rel`)."""
    x, y, z = lx(tgt)
    dx, dy, dz = lx(d)
    ux, uy, uz = lx(u)
    s = {'ikR.w': 1.0, 'ikR.rel': rel, 'ikR.orel': rel, 'ikR.pt': 'tip', 'ikR.x': x, 'ikR.y': y, 'ikR.z': z, 'ikR.ow': 1.0,
         'ikR.dx': dx, 'ikR.dy': dy, 'ikR.dz': dz, 'ikR.ux': ux, 'ikR.uy': uy, 'ikR.uz': uz}
    s.update(extra or {})
    return s


# ------------------------------------------------------------------------------------- rig extension
class ForestRig(K.Rig):
    def __init__(self, B):
        super().__init__(B)
        self.hand_pts['Right']['tip'] = Vector(SYRINGE['tip'])
        hand = self.base[P + 'LeftHand']
        j3, j4 = (self.base[P + 'LeftHandIndex%d' % i].translation for i in (3, 4))
        self.hand_pts['Left']['index'] = hand.inverted() @ (j4 + (j4 - j3).normalized() * 0.012)
        o = B.meshes[2]
        self.sole_pts = {}
        for s, _, _ in K.SIDES:
            ft = P + s + 'Foot'
            W = self.base[ft] @ B.rest[ft].inverted()
            self.sole_pts[s] = np.array([tuple(W @ o.data.vertices[i].co) for i in B.sole[s]])

    def foot_matrix(self, s, sgn, p):
        M, lat = super().foot_matrix(s, sgn, p)
        w = p.get('f%s.sole' % s[0], 0.0)
        if w > 1e-6:
            R3 = np.array(M.to_3x3())
            z = self.sole_pts[s] @ R3[2, :] + M.translation.z
            M = Matrix.Translation((0.0, 0.0, -float(z.min()) * w)) @ M
        return M, lat

    def _arm_ik(self, out, s, sgn, p, w):
        k = s[0]
        ow = p.get('ik%s.ow' % k, 0.0) * w
        if ow > 1e-6:
            d = Vector((p.get('ik%s.dx' % k, 0.0) * sgn, p.get('ik%s.dy' % k, 0.0), p.get('ik%s.dz' % k, 1.0)))
            u = Vector((p.get('ik%s.ux' % k, 0.0) * sgn, p.get('ik%s.uy' % k, 0.0), p.get('ik%s.uz' % k, 0.0)))
            rel = p.get('ik%s.orel' % k) or p.get('ik%s.rel' % k)
            if rel:
                Rr = (out[P + rel] @ self.base[P + rel].inverted()).to_3x3()
                d, u = Rr @ d, Rr @ u
            want = hand_rot(d, u, NEEDLE_AXIS if s == 'Right' else FINGER_AXIS).to_quaternion()
            hm = out[P + s + 'Hand'].to_3x3().to_quaternion()
            if hm.dot(want) < 0:
                want.negate()
            q = hm.slerp(want, min(1.0, ow))
            M = K.rot_about(out[P + s + 'Hand'].translation, q @ hm.inverted())
            for n_ in self.B.subtree(s + 'Hand'):
                out[n_] = M @ out[n_]
        super()._arm_ik(out, s, sgn, p, w)

    def _body(self, p, q, feet, dz_extra):
        if p.get('ikL.late', 0.0) > 0.5 and p.get('ikL.w', 0.0) > 1e-6:
            p2 = dict(p)
            p2['ikL.w'] = 0.0
            out, hz, over = super()._body(p2, q, feet, dz_extra)
            self._arm_ik(out, 'Left', 1, p, p['ikL.w'])
            return out, hz, over
        return super()._body(p, q, feet, dz_extra)


def floor_setup(rig):
    rig.surfaces = [(0.0, lambda xs, ys: ys == ys)]


# ------------------------------------------------------------------------------------- periodic helpers
def pcurve(pairs, T):
    """Periodic Hermite curve through (t, v) pairs on [0, T] (the value at T is forced to the value at 0)."""
    ks = sorted(pairs)
    if ks[-1][0] < T - 1e-9:
        ks.append((T, ks[0][1]))
    ks[-1] = (T, ks[0][1])
    return C.Curve(ks, periodic=True)


def spring(drive, T, freq, zeta, n=960, loops=10):
    """Steady-state periodic response y(t) of y'' = w^2 (x - y) - 2 zeta w y' to the periodic drive x(t)."""
    w = 2 * math.pi * freq
    dt = T / n
    xs = [drive(i * dt) for i in range(n)]
    y, v = xs[0], 0.0
    ys = [0.0] * n
    for _ in range(loops):
        for i in range(n):
            for _ in range(4):
                a = w * w * (xs[i] - y) - 2 * zeta * w * v
                v += a * dt / 4
                y += v * dt / 4
            ys[i] = y
    ys.append(ys[0])
    ts = [i * dt for i in range(n + 1)]
    return lambda t: float(np.interp(t % T, ts, ys))


# ===================================================================================== Junkie_Walk
WALK_V = 0.80                  # authored ground speed (m/s): the floor moves +Y under him
WALK_T = 2.40                  # 4 steps: L, R, L crosses over (stumble), R catches wide
BALL0_Y = -0.10                # Idle toe-joint y

# per foot: stances (touchdown, lift-off, ball y at touchdown, outward offset, toe-out yaw, landing roll, heel-peel roll)
# and the swing that leads INTO each stance
STANCES = {
    'L': [dict(td=0.00, lo=0.68, y=-0.27, fx=0.00, yaw=17.0, land=-5.0, peel=26.0, swing=('normal', 0.032)),
          dict(td=1.20, lo=1.88, y=-0.28, fx=-0.20, yaw=-18.0, land=-3.0, peel=22.0, swing=('cross', 0.055))],
    'R': [dict(td=0.60, lo=1.26, y=-0.27, fx=0.00, yaw=17.0, land=-5.0, peel=24.0, swing=('normal', 0.032)),
          dict(td=1.62, lo=2.44, y=-0.40, fx=0.17, yaw=28.0, land=-12.0, peel=26.0, swing=('catch', 0.075))],
}
PEEL_T = 0.26                  # heel peel duration at the end of a stance
LAND_T = 0.10                  # foot flattens after touchdown


def _events(side):
    ev = []
    for sh in (-WALK_T, 0.0, WALK_T):
        for s in STANCES[side]:
            e = dict(s)
            e['td'] += sh
            e['lo'] += sh
            ev.append(e)
    return sorted(ev, key=lambda e: e['td'])


EVENTS = {s: _events(s) for s in 'LR'}
_SWING_CACHE = {}


def _peel(e, t):
    b = (e['lo'] - t) / PEEL_T
    return e['peel'] * (max(0.0, 1.0 - b) ** 1.7)


def _swing_curves(prev, nxt):
    dur = nxt['td'] - prev['lo']
    y0 = prev['y'] + WALK_V * (prev['lo'] - prev['td'])
    y1 = nxt['y']
    kind, peak = nxt['swing']
    m = WALK_V * dur                                # dy/du at both ends: the foot leaves and lands at ground speed
    mid = {'normal': 0.42, 'cross': 0.46, 'catch': 0.64}[kind]
    # the first and last 8 % follow the ground exactly (the toe pad / heel is still within 2 mm of the floor there)
    yc = C.Curve([(0.0, y0, m), (0.08, y0 + 0.08 * m, m), (0.5, y0 + (y1 - y0) * mid), (0.92, y1 - 0.08 * m, m),
                  (1.0, y1, m)])
    zc = C.Curve([(0.0, 0.0, 0.10), (0.06, 0.0045), (0.30, 0.007 if kind != 'catch' else 0.02), (0.62, peak),
                  (0.86, 0.35 * peak), (1.0, 0.0, -0.06)])
    roll_slope = prev['peel'] * 1.7 / PEEL_T * dur   # matches the heel-peel speed at lift-off
    rc = C.Curve([(0.0, prev['peel'], roll_slope), (0.16, prev['peel'] + 8.0), (0.48, 12.0), (0.82, nxt['land'] - 4.0),
                  (1.0, nxt['land'], 'flat')])
    return yc, zc, rc, dur


def walk_foot(side, t):
    """(ball y world, lift z, roll, outward x offset, yaw) of one foot at time t in [0, WALK_T]."""
    ev = EVENTS[side]
    for e in ev:
        if e['td'] - 1e-9 <= t <= e['lo'] + 1e-9:
            a = t - e['td']
            roll = e['land'] * (1.0 - smooth(a / LAND_T)) + _peel(e, t)
            return e['y'] + WALK_V * a, 0.0, roll, e['fx'], e['yaw']
    prev = max((e for e in ev if e['lo'] < t), key=lambda e: e['lo'])
    nxt = min((e for e in ev if e['td'] > t), key=lambda e: e['td'])
    ck = (side, round(prev['td'], 6))
    if ck not in _SWING_CACHE:
        _SWING_CACHE[ck] = _swing_curves(prev, nxt)
    yc, zc, rc, dur = _SWING_CACHE[ck]
    u = (t - prev['lo']) / dur
    kind = nxt['swing'][0]
    x0, x1 = prev['fx'], nxt['fx']
    if kind == 'cross':                 # passes the stance foot first, then hooks across in front of it
        fx = x0 + (x1 - x0) * smooth((u - 0.70) / 0.26)
        yaw = prev['yaw'] + (nxt['yaw'] - prev['yaw']) * smooth((u - 0.45) / 0.5)
    elif kind == 'catch':               # flung out wide early, a little overshoot
        fx = x0 + (x1 - x0) * smooth((u - 0.02) / 0.55) + 0.03 * bump(u, 0.45, 1.0)
        yaw = prev['yaw'] + (nxt['yaw'] - prev['yaw']) * smooth(u / 0.8)
    else:
        fx = x0 + (x1 - x0) * smooth(u)
        yaw = prev['yaw'] + (nxt['yaw'] - prev['yaw']) * smooth(u)
    return yc(u), max(0.0, zc(u)), rc(u), fx, yaw


def _walk():
    T = WALK_T
    hx = pcurve([(0.00, -0.085), (0.25, 0.050), (0.45, 0.065), (0.60, 0.010), (0.85, -0.070), (1.05, -0.050),
                 (1.20, -0.040), (1.40, -0.105), (1.62, -0.135), (1.80, -0.165), (2.00, -0.115), (2.20, -0.135)], T)
    hy = pcurve([(0.00, 0.000), (0.60, 0.012), (1.20, -0.015), (1.42, -0.085), (1.62, -0.105), (1.80, -0.055),
                 (2.05, 0.018)], T)
    hz = pcurve([(0.00, -0.085), (0.12, -0.102), (0.35, -0.070), (0.60, -0.085), (0.72, -0.102), (0.95, -0.070),
                 (1.20, -0.090), (1.36, -0.105), (1.55, -0.118), (1.62, -0.122), (1.74, -0.165), (1.92, -0.100),
                 (2.15, -0.075)], T)
    lurch = pcurve([(0.00, 0.0), (1.20, 0.0), (1.32, 7.0), (1.48, 22.0), (1.62, 17.0), (1.74, 24.0), (1.90, 4.0),
                    (2.05, -7.0), (2.25, 0.0)], T)
    lroll = pcurve([(0.00, 0.0), (1.20, 0.0), (1.45, -9.0), (1.62, -12.0), (1.80, -4.0), (2.00, 4.0), (2.20, 0.0)], T)
    # nodding off: the head sinks while he walks, eyes closing ... the stumble snaps him awake
    droop = pcurve([(0.00, 5.0), (0.50, 10.0), (1.02, 20.0), (1.20, 22.0), (1.31, 0.0), (2.22, 0.0)], T)
    whip = pcurve([(0.00, 0.0), (1.25, 0.0), (1.45, -28.0), (1.62, -20.0), (1.78, -8.0), (1.95, 14.0), (2.12, 22.0),
                   (2.30, 6.0)], T)
    look = pcurve([(0.00, 0.0), (1.90, 0.0), (2.10, -16.0), (2.30, -6.0)], T)
    # sway: the upper body lags the pelvis and overshoots (spring), the head lags the upper body
    sx = spring(hx, T, 1.25, 0.28)
    roll_t = lambda t: 330.0 * (sx(t) - hx(t)) + lroll(t)
    sr = spring(roll_t, T, 0.95, 0.22)
    sz = spring(hz, T, 1.6, 0.35)
    noise_r = K.pn(T, 11, cycles=(1, 2, 3))
    noise_w = K.pn(T, 12, cycles=(1, 2))
    # rope arms: pendulums hanging from the shoulders; the bob is pulled a little opposite to the legs
    leg = lambda t: (walk_foot('L', t)[0] - walk_foot('R', t)[0]) / 0.55
    pitch_t = lambda t: -4.0 + 6.0 + 10.0 + 6.0 + lurch(t) * 1.4
    sh = {}
    for side, sgn in (('L', 1), ('R', -1)):
        ys_ = (lambda sgn_: (lambda t: hy(t) - 0.36 * math.sin(math.radians(pitch_t(t)))))(sgn)
        drv = (lambda sgn_, f_: (lambda t: f_(t) - 0.075 * sgn_ * leg(t)))(sgn, ys_)
        xs_ = (lambda sgn_: (lambda t: sgn_ * 0.2 + hx(t) + 0.36 * math.sin(math.radians(roll_t(t)))))(sgn)
        by, bx = spring(drv, T, 0.85, 0.20), spring(xs_, T, 0.85, 0.22)
        sh[side] = (ys_, xs_, by, bx)
    ARM_L = 0.55

    def params(t):
        p = {'hip.soft': 0.04, 'kL': 10.0, 'kR': 10.0}
        fy = {}
        for side in 'LR':
            y, z, roll, fx, yaw = walk_foot(side, t)
            fy[side] = y
            p['f%s.y' % side] = y - BALL0_Y
            p['f%s.z' % side] = z
            p['f%s.r' % side] = roll
            p['f%s.x' % side] = fx
            p['f%s.w' % side] = yaw
        x = hx(t)
        p['hip.x'] = x
        p['hip.y'] = hy(t)
        p['hip.z'] = hz(t)
        hw = 8.0 * (fy['L'] - fy['R']) / 0.55
        p['hip.w'] = hw
        p['hip.r'] = -50.0 * x
        p['hip.p'] = -4.0
        lu = lurch(t)
        rt = roll_t(t)
        dr = droop(t)
        p['s1.p'] = 6.0 + 0.5 * lu
        p['s2.p'] = 10.0 + 0.6 * lu + 0.15 * dr
        p['s3.p'] = 6.0 + 0.3 * lu + 0.15 * dr
        p['s1.r'], p['s2.r'], p['s3.r'] = 0.25 * rt, 0.40 * rt, 0.35 * rt
        p['s2.w'], p['s3.w'] = -0.9 * hw, -0.4 * hw
        # head: hangs forward and sinks (nodding off), lolls with lag, nods with the bob, whips up in the stumble
        hr = 0.5 * rt + 1.6 * (sr(t) - rt) + 8.0 * noise_r(t)
        p['nk.p'] = 6.0 - 0.2 * whip(t) + 0.3 * dr
        p['hd.p'] = 2.0 + 0.8 * whip(t) + 0.7 * dr + 260.0 * (sz(t) - hz(t))
        p['nk.r'], p['hd.r'] = 0.3 * hr, 0.75 * hr
        p['hd.w'] = 8.0 * noise_w(t) + look(t) - 0.3 * hw
        p['cL.f'] = p['cR.f'] = 8.0
        # arms: rope pendulums + a little backward windmill while he catches his balance
        wm = window(t, 1.40, 1.84, 0.20)
        ph = 2 * math.pi * 2.2 * (t - 1.364)            # both arms start low when the windmill fades in
        pitch = p['hip.p'] + p['s1.p'] + p['s2.p'] + p['s3.p']
        for side, sgn, off in (('L', 1, 0.0), ('R', -1, 0.25 * math.pi)):
            ys_, xs_, by, bx = sh[side]
            ff = math.degrees((ys_(t) - by(t)) / ARM_L) * 1.5
            fo = math.degrees(sgn * (bx(t) - xs_(t)) / ARM_L) * 1.5
            af = ff - 0.85 * pitch + 4.0
            ao = 6.0 + fo + sgn * 0.85 * (rt + p['hip.r'])
            ee = 14.0 + 0.35 * max(0.0, ff) + 4.0 * math.sin(2 * math.pi * t / T * 2 + off)
            wf = 18.0 + 0.8 * ff
            a_f = 65.0 + 60.0 * math.sin(ph + off)
            a_o = 45.0 + 28.0 * math.cos(ph + off)
            e_w = 35.0 + 18.0 * math.sin(ph + off + 1.0)
            w_w = 22.0 * math.sin(ph + off - 1.2)
            p['a%s.f' % side] = af + wm * (a_f - af)
            p['a%s.o' % side] = ao + wm * (a_o - ao)
            p['e' + side] = ee + wm * (e_w - ee)
            p['w%s.f' % side] = wf + wm * (w_w - wf)
            p['c%s.u' % side] = -4.0 + 16.0 * wm
            p['fi' + side] = 0.35 - 0.3 * wm
            p['th' + side] = 0.25
        return p
    params.droop = droop
    return params


walk_params = _walk()

# ===================================================================================== high_lie (contract) + floor
LIE_HAND = (0.62, 0.80, 0.030)          # palm point on the floor (x outward), palm up
LIE_ARMS = {'aL.f': 0.0, 'aR.f': 0.0, 'aL.o': 80.0, 'aR.o': 80.0, 'aL.t': 0.0, 'aR.t': 0.0, 'eL': 20.0, 'eR': 20.0,
            'eL.t': 60.0, 'eR.t': 60.0, 'wL.f': 0.0, 'wR.f': 0.0, 'fiL': 0.35, 'fiR': 0.35, 'thL': 0.2, 'thR': 0.2}
for _k in 'LR':
    LIE_ARMS.update({'ik%s.w' % _k: 1.0, 'ik%s.rel' % _k: '', 'ik%s.orel' % _k: '', 'ik%s.pt' % _k: 'palm',
                     'ik%s.floor' % _k: 1.0,
                     'ik%s.x' % _k: LIE_HAND[0], 'ik%s.y' % _k: LIE_HAND[1], 'ik%s.z' % _k: LIE_HAND[2],
                     'ik%s.ow' % _k: 1.0, 'ik%s.dx' % _k: 1.0, 'ik%s.dy' % _k: 0.25, 'ik%s.dz' % _k: 0.0,
                     'ik%s.ux' % _k: 0.0, 'ik%s.uy' % _k: 0.0, 'ik%s.uz' % _k: 1.0})
LIE_LEGS = {'fL.x': 0.20, 'fR.x': 0.20, 'fL.y': -0.36, 'fR.y': -0.36, 'fL.z': 0.0, 'fR.z': 0.0, 'fL.r': -72.0,
            'fR.r': -72.0, 'fL.w': 42.0, 'fR.w': 42.0, 'fL.sole': 1.0, 'fR.sole': 1.0, 'kL': 30.0, 'kR': 30.0}


def lie_base():
    return add(LIE_ARMS, LIE_LEGS, {'hip.free': 1.0, 'lift': 1.0, 'gnd': 1.0, 'hip.y': 0.40, 'hip.z': -0.70,
                                    'hip.p': -84.0, 's1.p': -2.0, 's2.p': -2.0, 's3.p': -2.0, 'nk.p': -2.0, 'hd.p': 0.0,
                                    'hd.w': 16.0, 'hd.r': 4.0})


LIE_VIEWS = {'side': ((5.6, 0.40, 0.9), (0.0, 0.40, 0.55), 2.7),
             'three_quarter': ((3.9, -3.5, 2.5), (0.0, 0.35, 0.50), 2.7),
             'front': ((0.0, -5.2, 1.5), (0.0, 0.4, 0.5), 2.7),
             'top': ((0.0, 0.40, 6.0), (0.0, 0.40, 0.0), 2.6)}

# ===================================================================================== Inject (idle -> high_lie)
INJ_T = 8.0
# held up in front of the eyes, needle up, palm toward his face
HOLD_TIP = Vector((-0.03, -0.285, 1.51))             # Idle space, carried by Spine2
HOLD_D = Vector((0.0, 0.10, 1.0))
HOLD_U = Vector((0.55, 0.85, -0.1))
# left index flick point on the barrel (hand frame of the right hand -> Idle space)
_HOLD_R = hand_rot(HOLD_D, HOLD_U)
_LEFTWARD = _HOLD_R.transposed() @ Vector((1.0, 0.0, 0.0))     # hand-local direction of world +X while held up
_BARREL = Vector(SYRINGE['tip']) - NEEDLE_AXIS * 0.095            # lower barrel, past the fingertips
FLICK_HIT = R_HAND_IDLE @ (_BARREL + _LEFTWARD * 0.026)
FLICK_OFF = R_HAND_IDLE @ (_BARREL + _LEFTWARD * 0.070)
# designed in the presented pose (world): the inner forearm faces up (palm up); the needle comes from his right, across
# the arm and 30 deg into it, palm toward the arm; the chop-slap lands with the pinky edge, palm toward his belly
ARM_N = Vector((0.0, -0.28, 0.96)).normalized()
VEIN = Vector((0.229, -0.250, 0.975))            # top of the forearm sleeve ~30 % from the elbow
SLAP_PT = Vector((0.229, -0.275, 0.968))
NEEDLE_W = (Vector((1.0, 0.0, 0.0)) * math.cos(math.radians(30)) - ARM_N * math.sin(math.radians(30))).normalized()
SLAP_DW = Vector((1.0, -0.15, -0.25)).normalized()
SLAP_UW = Vector((0.0, 0.0, 1.0)).cross(SLAP_DW).normalized()
PINKY_EDGE = Vector((-0.050, 0.115, 0.004))      # hand-local, outside of the little finger
NEEDLE_D, NEEDLE_U = pres_dir(NEEDLE_W), pres_dir(-ARM_N)
SLAP_D, SLAP_U = pres_dir(SLAP_DW), pres_dir(SLAP_UW)
TIP_HOVER = pres_pt(VEIN + ARM_N * 0.05 - NEEDLE_W * 0.03)
TIP_TOUCH = pres_pt(VEIN + ARM_N * 0.004)
TIP_IN = pres_pt(VEIN + ARM_N * 0.004 + NEEDLE_W * 0.016)
SLAP_HIT = pres_pt(tip_for_contact(SLAP_PT + ARM_N * 0.006, PINKY_EDGE, SLAP_DW, SLAP_UW))
SLAP_UP = pres_pt(tip_for_contact(SLAP_PT + ARM_N * 0.12 + Vector((-0.03, 0.03, 0.0)), PINKY_EDGE, SLAP_DW, SLAP_UW))

ARM_OUT_L = {'aL.f': 50.0, 'aL.o': -8.0, 'aL.t': -10.0, 'eL': 25.0, 'eL.t': 95.0, 'wL.f': -15.0, 'fiL': 0.65,
             'thL': 0.5, 'fiL.i': 0.0}
FLICK_L = {'ikL.w': 1.0, 'ikL.rel': 'RightHand', 'ikL.pt': 'index', 'aL.f': 45.0, 'aL.o': 10.0,
           'eL': 110.0, 'eL.t': 40.0, 'wL.f': 10.0, 'fiL': 0.85, 'fiL.i': -0.85, 'thL': 0.7}
HANG_R = {'ikR.w': 0.0, 'aR.f': 8.0, 'aR.o': 8.0, 'aR.t': 0.0, 'eR': 22.0, 'eR.t': 10.0, 'wR.f': 10.0, 'fiR': 0.45,
          'thR': 0.5}
HANG_L = {'ikL.w': 0.0, 'aL.f': 6.0, 'aL.o': 8.0, 'aL.t': 0.0, 'eL': 16.0, 'eL.t': 0.0, 'wL.f': 15.0, 'fiL': 0.35,
          'fiL.i': 0.0, 'thL': 0.3}
GRIP_R = {'fiR': 0.42, 'thR': 0.55}


def sit_base():
    return {'hip.free': 1.0, 'lift': 1.0, 'gnd': 1.0, 'hip.y': 0.24, 'hip.z': -0.64, 'hip.p': -14.0, 's1.p': 18.0,
            's2.p': 12.0, 's3.p': 8.0, 'nk.p': 6.0, 'hd.p': 4.0,
            'fL.x': 0.10, 'fR.x': 0.10, 'fL.y': -0.40, 'fR.y': -0.40, 'fL.z': 0.0, 'fR.z': 0.0, 'fL.r': -45.0,
            'fR.r': -45.0, 'fL.w': 28.0, 'fR.w': 28.0, 'fL.sole': 1.0, 'fR.sole': 1.0, 'kL': 26.0, 'kR': 26.0}


def _inject():
    base = lie_base()
    sb = sit_base()
    lap = {'aL.f': 34.0, 'aR.f': 30.0, 'aL.o': 12.0, 'aR.o': 14.0, 'eL': 48.0, 'eR': 52.0, 'eL.t': 60.0, 'eR.t': 80.0,
           'wL.f': -8.0, 'wR.f': -12.0}
    k = keys(
        (0.00, {'ikR.rel': 'Spine', 'ikR.orel': 'Spine', 'ikR.pt': 'fist', 'ikL.rel': 'RightHand', 'ikL.pt': 'index'}),
        (0.40, {'ikL.late': 1.0, 'hip.z': -0.035, 's2.p': 10.0, 's3.p': 6.0, 'nk.p': 4.0, 'hd.p': 8.0, 'cL.f': 6.0, 'cR.f': 6.0,
                'aL.f': 4.0, 'aR.f': 4.0, 'eL': 12.0, 'eR': 12.0, 'fiL': 0.3, 'fiR': 0.3}),            # slouch, sway
        (0.72, add(POCKET_R, {'hd.p': 18.0, 'nk.p': 6.0, 's2.p': 12.0, 'hd.w': -6.0})),                  # hand into the pocket
        (0.86, {'ikR.z': 0.88, 'hd.r': -6.0}),                                                           # rummage...
        (0.98, {'ikR.z': 0.91, 'hd.r': 4.0}),
        (1.08, {'ikR.z': 0.89, 'hd.p': 12.0}),
        (1.20, add(GRIP_R, {'ikR.w': 0.0, 'ikR.orel': 'Spine2', 'aR.f': 50.0, 'aR.o': 18.0, 'eR': 115.0,
                            'eR.t': 60.0, 'wR.f': 0.0, 'hd.p': 0.0, 'hd.r': 0.0, 'hd.w': 0.0})),       # out it comes
        (1.48, r_ik(HOLD_TIP, HOLD_D, HOLD_U, 'Spine2', {'aR.f': 45.0, 'aR.o': 10.0, 'eR': 130.0, 'eR.t': 70.0,
                                                       'hd.p': 8.0, 'nk.p': -4.0, 's2.p': 8.0, 's3.p': 2.0})),  # holds it up
        (1.64, {'hd.p': 12.0, 'nk.p': -8.0, 'hd.r': 6.0, 'aL.f': 30.0, 'aL.t': -20.0, 'eL': 60.0, 'eL.t': 20.0}),  # squints; left hand comes up
        (1.80, add(FLICK_L, {'ikL.x': FLICK_OFF.x, 'ikL.y': FLICK_OFF.y, 'ikL.z': FLICK_OFF.z})),       # finger ready
        (1.92, {'ikL.x': FLICK_HIT.x, 'ikL.y': FLICK_HIT.y, 'ikL.z': FLICK_HIT.z, 'wL.f': -10.0}),      # tap
        (2.02, {'ikL.x': FLICK_OFF.x, 'ikL.y': FLICK_OFF.y, 'ikL.z': FLICK_OFF.z, 'wL.f': 15.0, 'hd.r': 9.0}),
        (2.12, {'ikL.x': FLICK_HIT.x, 'ikL.y': FLICK_HIT.y, 'ikL.z': FLICK_HIT.z, 'wL.f': -10.0}),      # tap
        (2.24, {'ikL.x': FLICK_OFF.x, 'ikL.y': FLICK_OFF.y, 'ikL.z': FLICK_OFF.z, 'wL.f': 10.0, 'hd.p': 14.0,
                'hd.r': 3.0}),
        (2.40, add(ARM_OUT_L, {'ikL.w': 0.0, 'hd.p': 20.0, 'nk.p': 6.0, 'hd.w': 14.0,
                               's2.p': 12.0})),                                                         # arm out, palm up
        (2.52, {'ikR.w': 0.0, 'ikR.orel': 'LeftForeArm', 'aR.f': 40.0, 'aR.o': 20.0, 'eR': 100.0, 'eR.t': 20.0}),
        (2.68, add(r_ik(SLAP_UP, SLAP_D, SLAP_U, 'LeftForeArm'), {'aR.f': 40.0, 'aR.o': 20.0, 'eR': 100.0,
                                                                  'eR.t': 20.0})),                 # wind up
        (2.78, {'ikR.x': lx(SLAP_HIT)[0], 'ikR.y': SLAP_HIT.y, 'ikR.z': SLAP_HIT.z}),                   # slap
        (2.90, {'ikR.x': lx(SLAP_UP)[0], 'ikR.y': SLAP_UP.y, 'ikR.z': SLAP_UP.z}),
        (3.00, {'ikR.x': lx(SLAP_HIT)[0], 'ikR.y': SLAP_HIT.y, 'ikR.z': SLAP_HIT.z}),                   # slap
        (3.16, r_ik(TIP_HOVER, NEEDLE_D, NEEDLE_U, 'LeftForeArm')),                                     # aim
        (3.36, {'ikR.x': lx(TIP_TOUCH)[0], 'ikR.y': TIP_TOUCH.y, 'ikR.z': TIP_TOUCH.z, 'hd.p': 24.0}),
        (3.48, {'ikR.x': lx(TIP_IN)[0], 'ikR.y': TIP_IN.y, 'ikR.z': TIP_IN.z, 'thR': 0.8}),             # in, push
        (3.90, {'hd.p': 23.0}),                                                                         # freeze
        (4.06, {'ikR.x': lx(TIP_HOVER)[0], 'ikR.y': TIP_HOVER.y, 'ikR.z': TIP_HOVER.z, 'thR': 0.55}),  # out
        (4.30, add(HANG_R, HANG_L, GRIP_R, {'hd.p': 0.0, 'nk.p': 0.0, 'hd.w': 0.0, 's2.p': 6.0, 's3.p': 2.0,
                                            'ikR.ow': 0.0, 'ikR.orel': '', 'ikL.orel': ''})),          # arms drop
        (4.75, {'hd.p': -30.0, 'nk.p': -10.0, 's3.p': -6.0, 's2.p': 0.0, 'hip.z': -0.05, 'cL.u': -6.0,
                'cR.u': -6.0}),                                                                         # head tips back, bliss
        (5.02, {'hd.p': -34.0}),
        (5.12, {'hip.z': -0.15, 's1.p': 10.0, 's2.p': 8.0, 'hd.p': -18.0, 'kL': 26.0, 'kR': 26.0}),     # buckle 1
        (5.36, {'hip.z': -0.13, 's1.p': 6.0, 'hd.p': -26.0}),                                           # wobbly catch
        (5.58, {'hip.free': 1.0, 'lift': 1.0, 'hip.z': -0.46, 'hip.y': 0.10, 'hip.p': 22.0, 's1.p': 10.0,
                's2.p': 6.0, 'hd.p': -10.0, 'aL.o': 30.0, 'aR.o': 30.0, 'aL.f': 30.0, 'aR.f': 30.0, 'kL': 30.0,
                'kR': 30.0, 'gnd': 0.0}),                                                               # buckle 2: drops
        (5.66, {'hip.z': -0.74, 'hip.y': 0.17, 'hip.p': 2.0, 's1.p': 8.0, 's2.p': 6.0, 'hd.p': -16.0,
                'fL.y': -0.05, 'fR.y': -0.05, 'fL.r': -6.0, 'fR.r': -6.0, 'kL': 28.0, 'kR': 28.0}),           # butt hits the floor (lift stop)
        (5.80, add(sb, {'gnd': 1.0, 'hip.y': 0.21, 'hip.p': -22.0, 's1.p': 4.0, 's2.p': 2.0, 'hd.p': -22.0,
                        'fL.z': 0.11, 'fR.z': 0.09, 'fL.r': -30.0, 'fR.r': -30.0, 'fL.sole': 0.0, 'fR.sole': 0.0,
                        'aL.o': 42.0, 'aR.o': 42.0, 'aL.f': 40.0, 'aR.f': 40.0})),                       # plop: legs fly up
        (5.94, add(sb, lap, {'s1.p': 24.0, 's2.p': 16.0, 'hd.p': 14.0})),                              # legs slap down, bounce
        (6.10, {'s1.p': 14.0, 's2.p': 10.0, 'hd.p': -6.0}),
        (6.30, {'hd.p': -10.0}),                                                                        # seated sway (layer)
        (6.55, {'hd.p': -16.0, 's1.p': 10.0}),
        (6.90, {'hip.p': -26.0, 'hip.y': 0.27, 's1.p': 4.0, 's2.p': 4.0, 's3.p': 2.0, 'hd.p': 4.0,
                'aL.f': 40.0, 'aR.f': 36.0, 'aL.o': 30.0, 'aR.o': 30.0}),                               # starts tipping back
        (7.08, {'hip.p': -50.0, 'hip.y': 0.34, 's1.p': -2.0, 's2.p': 0.0, 's3.p': 0.0, 'hd.p': 14.0, 'aL.f': 30.0,
                'aR.f': 34.0, 'aL.o': 62.0, 'aR.o': 66.0, 'eL': 30.0, 'eR': 26.0}),                    # falling, arms fly out
        (7.18, {'fiR': 0.0, 'thR': -0.1, 'hip.p': -66.0, 'aR.o': 74.0}),                                # hand opens: the syringe flies
        (7.30, add(base, {'hd.p': 16.0, 'hd.w': 6.0, 'fiR': 0.0, 'thR': 0.0})),                        # thud on the back
        (7.38, {'hd.p': -4.0}),                                                                         # head bonk
        (7.48, {'hd.p': 8.0}),                                                                          # bounce
        (7.66, {'hd.p': base['hd.p'] - 2.0, 'fiR': base['fiR'], 'thR': base['thR'], 'hd.w': base['hd.w']}),
        (8.00, base),
    )
    tr = K.FitTrack(_fill(k, start={}, end=base))
    sway = lambda t: window(t, 0.35, 4.6, 0.3)          # exactly 0 at t = 0 (Idle frame 1)
    seat = lambda t: window(t, 6.05, 6.9, 0.25)

    def params(t):
        p = tr(t)
        w = sway(t)
        c = 2 * math.pi * t / 1.7
        p['hip.x'] = p.get('hip.x', 0.0) + 0.022 * w * math.sin(c)
        p['hip.y'] = p.get('hip.y', 0.0) + 0.012 * w * math.cos(c)
        p['s1.r'] = p.get('s1.r', 0.0) - 3.0 * w * math.sin(c - 0.6)
        p['s2.r'] = p.get('s2.r', 0.0) - 2.5 * w * math.sin(c - 0.9)
        p['hd.r'] = p.get('hd.r', 0.0) + 6.0 * w * math.sin(c - 1.5)
        # big blissful wobble after the shot
        wb = window(t, 4.4, 5.1, 0.2)
        c2 = 2 * math.pi * (t - 4.4) / 0.9
        p['hip.x'] += 0.04 * wb * math.sin(c2)
        p['hip.y'] += 0.03 * wb * math.cos(c2)
        p['s1.r'] -= 7.0 * wb * math.sin(c2 - 0.7)
        p['s1.p'] = p.get('s1.p', 0.0) + 5.0 * wb * math.cos(c2 - 0.7)
        p['hd.r'] += 12.0 * wb * math.sin(c2 - 1.6)
        # seated circling
        ws = seat(t)
        c3 = 2 * math.pi * (t - 6.05) / 1.0
        p['s1.r'] += 6.0 * ws * math.sin(c3)
        p['s1.p'] += 4.0 * ws * math.cos(c3)
        p['hd.r'] += 10.0 * ws * math.sin(c3 - 1.2)
        # rummage jiggle in the pocket
        wr = window(t, 0.80, 1.10, 0.06)
        p['ikR.x'] = p.get('ikR.x', 0.0) + 0.012 * wr * math.sin(2 * math.pi * 9.0 * t)
        # plunger push happens with the thumb (preview prop); a tiny freeze tremble
        wt = window(t, 3.55, 3.95, 0.05)
        p['hd.r'] += 1.5 * wt * math.sin(2 * math.pi * 11.0 * t)
        return p
    return params


inject_params = _inject()

# ===================================================================================== High_Lie_Loop
LIE_T = 8.0


def _lie_loop():
    T = LIE_T
    base = lie_base()
    paddle = {'ikL.w': 0.0, 'ikR.w': 0.0, 'aL.f': 85.0, 'aR.f': 85.0, 'aL.o': 30.0, 'aR.o': 30.0, 'eL': 40.0,
              'eR': 40.0, 'eL.t': 40.0, 'eR.t': 40.0, 'wL.f': 20.0, 'wR.f': 20.0, 'fiL': 0.15, 'fiR': 0.15}
    wave_R = {'ikR.w': 0.0, 'aR.f': 95.0, 'aR.o': 25.0, 'eR': 35.0, 'eR.t': 60.0, 'wR.f': -10.0, 'fiR': 0.05,
              'thR': 0.05}
    k = keys(
        (0.00, base),
        (1.20, {'hd.w': -18.0}),                                                        # head rolls the other way
        (2.10, add(paddle, {'hd.w': -4.0, 'hd.p': 0.0})),                                # arms up: swim in the air
        (4.05, {'hd.w': 14.0}),
        (4.50, add({k_: base[k_] for k_ in paddle}, {'hd.p': base['hd.p'] + 4.0})),    # arms flop back down
        (4.80, {'hd.w': 20.0}),
        (5.10, add(wave_R, {'hd.w': -10.0, 'hd.p': -6.0})),                             # slow wave at the sky
        (6.05, {'hd.w': -6.0}),
        (6.45, add({k_: base[k_] for k_ in wave_R}, {'hd.w': 6.0, 'hd.p': base['hd.p']})),
        (6.80, {'ikL.w': 0.0, 'aL.f': 70.0, 'aL.o': 30.0, 'eL': 95.0, 'eL.t': 30.0, 'wL.f': 15.0, 'fiL': 0.1,
                'hd.w': 10.0}),                                                          # lazy swat...
        (7.00, {'aL.f': 40.0, 'aL.o': 4.0, 'eL': 70.0, 'wL.f': -25.0, 'hd.w': 24.0, 'hd.p': base['hd.p'] + 6.0}),  # ...misses
        (7.40, add({k_: base[k_] for k_ in ('ikL.w', 'aL.f', 'aL.o', 'eL', 'eL.t', 'wL.f', 'fiL')}, {'hd.w': 18.0})),
        (8.00, base),
    )
    tr = K.FitTrack(_fill(k), periodic=True)

    def params(t):
        p = tr(t)
        # breathing belly (4 slow breaths)
        p['s2.p'] = p.get('s2.p', 0.0) - 2.2 * math.sin(2 * math.pi * 4 * t / T) ** 2
        p['s1.p'] = p.get('s1.p', 0.0) - 1.0 * math.sin(2 * math.pi * 4 * t / T) ** 2
        # head rolls slowly side to side (on top of the keyed turns)
        p['hd.w'] = p.get('hd.w', 0.0) + 8.0 * math.sin(2 * math.pi * 2 * t / T)
        # right leg: two quick dreaming-dog kicks 1.38-1.92, the whole body jolts with them
        k1, k2 = bump(t, 1.38, 1.62), bump(t, 1.62, 1.92)
        kk = k1 + k2
        p['fR.y'] = p.get('fR.y', 0.0) + 0.15 * k1 + 0.19 * k2
        p['fR.z'] = p.get('fR.z', 0.0) + 0.16 * k1 ** 0.7 + 0.21 * k2 ** 0.7
        p['fR.r'] = p.get('fR.r', 0.0) + 22.0 * kk
        p['fR.sole'] = 1.0 - min(1.0, 1.6 * kk)
        p['hip.r'] = p.get('hip.r', 0.0) + 3.5 * kk
        p['s1.p'] += 2.5 * kk
        p['hd.p'] = p.get('hd.p', 0.0) - 5.0 * kk
        # left foot twitches (5.2-5.6): toes flap, the knee jerks
        wt = window(t, 5.22, 5.58, 0.05)
        ph = 2 * math.pi * 6.0 * (t - 5.22)
        p['fL.r'] = p.get('fL.r', 0.0) + 20.0 * wt * math.sin(ph)
        p['fL.w'] = p.get('fL.w', 0.0) + 10.0 * wt * math.sin(ph + 1.0)
        p['fL.y'] = p.get('fL.y', 0.0) + 0.035 * wt * max(0.0, math.sin(ph - 0.6))
        # paddling: slow breaststroke circles 2.3-4.0
        wp = window(t, 2.3, 4.0, 0.25)
        c = 2 * math.pi * (t - 2.3) / 0.85
        for side, off in (('L', 0.0), ('R', 0.35)):
            p['a%s.o' % side] += 22.0 * wp * math.sin(c + off)
            p['a%s.f' % side] += 14.0 * wp * math.cos(c + off)
            p['e' + side] += 18.0 * wp * math.sin(c + off + 1.2)
            p['w%s.f' % side] += 20.0 * wp * math.sin(c + off - 1.0)
        # slow wave 5.25-6.05 (upper-arm twist swings the forearm, floppy wrist)
        ww = window(t, 5.25, 6.05, 0.15)
        p['aR.t'] = p.get('aR.t', 0.0) + 28.0 * ww * math.sin(2 * math.pi * 1.4 * (t - 5.25))
        p['wR.d'] = p.get('wR.d', 0.0) + 22.0 * ww * math.sin(2 * math.pi * 1.4 * (t - 5.25) - 0.8)
        # giggle after the miss
        wg = window(t, 7.25, 7.7, 0.08)
        p['s2.p'] += 2.0 * wg * math.sin(2 * math.pi * 7.0 * t)
        return p
    return params


lie_loop_params = _lie_loop()

# ===================================================================================== registry
CONTRACTS = {
    'junkie_walk': {'params': lambda: walk_params(0.0),
                    'doc': 'Junkie_Walk frame 1 (left foot touchdown; right foot still out wide behind from the catch); '
                           'loop seam only'},
    'high_lie': {'params': lie_base, 'setup': [floor_setup],
                 'doc': 'High_Lie base: flat on the back on the floor behind the root (head toward +Y, hips ~0.4 m '
                        'behind the root), starfish: arms out on the floor palms up, legs spread, feet flopped out'},
}


def _face_walk(t):
    st = window(t, 1.30, 1.75, 0.05)
    huh = window(t, 1.95, 2.3, 0.08)
    sleepy = min(1.0, max(0.0, walk_params.droop(t) / 22.0))
    return {'Blink': (0.55 + 0.45 * sleepy) * (1 - st), 'Worried': 0.25 + 0.5 * huh, 'Surprised': 0.95 * st,
            'Happy': 0.0}


def _face_inject(t):
    squint = window(t, 1.5, 2.35, 0.1)
    shot = window(t, 3.42, 3.9, 0.04)
    bliss = smooth((t - 4.1) / 0.6)
    plop = bump(t, 5.62, 5.92)
    return {'Blink': 0.6 * (1 - bliss) * (1 - shot) + 0.25 * squint + 0.5 * bliss * (1 - plop),
            'Worried': 0.3 * (1 - bliss) * (1 - squint), 'Surprised': 0.8 * shot + 0.4 * plop,
            'Happy': 0.35 * squint + 1.0 * bliss}


def _face_lie(t):
    blink = bump(t, 2.6, 2.95) + bump(t, 6.1, 6.4)
    fly = window(t, 6.7, 7.1, 0.08)
    return {'Blink': 0.5 + 0.5 * blink - 0.3 * fly, 'Happy': 1.0 - 0.4 * fly, 'Surprised': 0.35 * fly,
            'Worried': 0.0}


CLIPS = {
    'Junkie_Walk': {'T': WALK_T, 'loop': True, 'start': 'junkie_walk', 'end': 'junkie_walk', 'params': walk_params,
                    'activity': 'JunkieWalk', 'role': 'loop', 'run_speed': WALK_V,
                    'props': [('treadmill', {'speed': WALK_V})], 'face': _face_walk,
                    'events': {'FootL': 0.0, 'FootR': 0.60, 'Stumble': 1.20, 'Catch': 1.62},
                    'unity': 'Loop Time on; authored at %.1f m/s, play at ground speed / %.1f' % (WALK_V, WALK_V),
                    'beats': ['0.00 left foot down, 0.60 right: soft-kneed shuffle, toes out, feet skimming the floor',
                              '0.0-1.2 nodding off while walking: the head sinks, eyes close (face hint)',
                              'torso hunched forward, swaying side to side behind the pelvis (spring lag, overshoot)',
                              'head hangs and lolls with lag; arms hang like ropes (pendulums) with follow-through',
                              '1.20 the left foot hooks across in front of the right (event Stumble)',
                              '1.30-1.62 lurch forward-right, head whips up, little backward arm windmill',
                              '1.62 the right foot flings out wide and catches him (event Catch), knees buckle',
                              '1.9-2.3 wobble back, "huh?" look down at the feet, shuffles on']},
    'Inject': {'T': INJ_T, 'loop': False, 'start': 'idle', 'end': 'high_lie', 'params': inject_params,
               'setup': [floor_setup], 'views': LIE_VIEWS, 'activity': 'Inject', 'role': 'oneshot', 'face': _face_inject,
               'syringe': {'show': 1.16, 'push': (3.48, 3.86), 'drop': 7.18},
               'events': {'SyringeShow': 1.16, 'Inject': 3.48, 'Sit': 5.66, 'SyringeDrop': 7.18},
               'feet_free': {'Left': [(5.50, INJ_T)], 'Right': [(5.50, INJ_T)]},
               'beats': ['0.0-0.7 sways standing, slouched', '0.7-1.1 hand into the hoodie pocket, rummages',
                         '1.16 out comes the syringe (event SyringeShow)', '1.5 holds it up in front of his eyes',
                         '1.6-2.3 squints cross-eyed, two finger flicks on the barrel (tap tap)',
                         '2.4 left arm out, palm up; 2.78 / 3.00 two chop-slaps on the inner forearm',
                         '3.16-3.48 aims, needle in (event Inject), thumb pushes; 3.5-3.9 freezes',
                         '4.06 pulls it out, arms drop; 4.3-5.0 head tips back slowly, blissful, big wobble',
                         '5.12 knees buckle (1), 5.36 catches himself, 5.58 buckle (2)',
                         '5.66 plops onto his butt (event Sit), 5.80 legs fly up, 5.94 legs slap down, bounce',
                         '5.9-6.6 sways seated', '6.6-7.3 tips slowly back (accelerating), arms fly out',
                         '7.18 the right hand opens mid-fling, the syringe drops (event SyringeDrop)',
                         '7.30 thud on the back, 7.38 head bonk and bounce, hands land palm-up', '8.0 high_lie']},
    'High_Lie_Loop': {'T': LIE_T, 'loop': True, 'start': 'high_lie', 'end': 'high_lie', 'params': lie_loop_params,
                      'setup': [floor_setup], 'views': LIE_VIEWS, 'activity': 'HighLie', 'role': 'loop',
                      'face': _face_lie, 'syringe': {'floor': True},
                      'feet_free': {'Right': [(1.30, 2.00)], 'Left': [(5.15, 5.65)]},
                      'beats': ['breathing belly throughout; head rolls slowly side to side',
                                '1.38-1.92 the right leg kicks twice like a dreaming dog, the body jolts',
                                '2.1-4.4 both arms up, slow breaststroke paddling in the air, flop back down',
                                '5.1-6.45 slow goofy wave at the sky (right hand)', '5.22-5.58 left foot twitches',
                                '6.8-7.4 a lazy swat at a fly, misses, the hand flops down; giggle', '8.0 base']},
}

PLACEMENT = {
    'Junkie_Walk': 'in place on a treadmill; authored ground speed %.1f m/s (playback speed = ground speed / %.1f)'
                   % (WALK_V, WALK_V),
    'Inject': 'free standing; ends lying behind the root (see High_Lie). Needs a free ~1.6 x 2.4 m patch from 0.75 m in '
              'front of the root to 1.6 m behind it. The syringe is a separate prop on mixamorig:RightHand '
              '(SyringeShow .. SyringeDrop), then a world prop on the floor',
    'High_Lie_Loop': 'on the floor behind the root: hips ~0.4 m, head top ~1.3 m behind; feet ~0.6 m in front, hands '
                     '~0.9 m to each side',
}
