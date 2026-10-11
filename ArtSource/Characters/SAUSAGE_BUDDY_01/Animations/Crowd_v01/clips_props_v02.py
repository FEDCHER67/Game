"""v02 revisions of three prop clips (Sausage Buddy crowd, VOLUNTEERS ONLY): BarDoor_Enter, SmokeCorner_Enter,
SmokeCorner_Loop. Original procedural keyframe animation; reuses crowd_core / clips_props / clips_stand unchanged.

Contracts are the v01 ones, untouched (clips_props.CONTRACTS): BarDoor_Enter_v02 ends on `lean`
(BarDoor_Loop_v01 / BarDoor_Exit_v01 chain on it), SmokeCorner_Enter_v02 ends on `smoke`, SmokeCorner_Loop_v02
starts and ends on `smoke` (SmokeCorner_Exit_v01 chains on it).

v02 additions (only used by the v02 clips; the contract poses never touch them, so they resolve exactly as in v01):
  * RigV02.pose: `wall.on` 0..1 blends the authored pelvis position with the wall-contact solution linearly (the v01
    `wall` weight is applied inside an iterative solve, so a ramp is not linear in time); `wall.gap` (m) keeps the
    back that far off the wall (rebound). Used for the BarDoor flop: a real fall with an ease-in and a hard stop.
  * reach point 'cig' (the cigarette's filter tip) for the right-hand IK, so the filter, not the fingers, lands on
    the lips. The cigarette itself is a preview-only prop (see CIGARETTE below and the README).
"""
import math
from mathutils import Vector, Matrix, Quaternion
import crowd_core as K
from crowd_core import add
import clips_props as CP
from clips_stand import shift, _fill, keys

REV = 'v02'
P = K.P

# ------------------------------------------------------------------------------------- preview-only props
# Hand-local frames are the pose-bone frames of the Blender rig: origin at the bone head (wrist joint), +Y along
# the bone toward the fingers. Right hand: +X = thumb/index side, +Z = palm normal (out of the palm).
# Left hand: +X = little-finger side, +Z = palm normal.
CIG_TILT = 0.0                                    # deg: + = the lit end leans toward the fingertips
_u = Vector((0.0, -math.sin(math.radians(CIG_TILT)), math.cos(math.radians(CIG_TILT))))   # grip -> filter (palm side)
CIGARETTE = {
    'bone': P + 'RightHand',
    'grip': (0.0175, 0.104, 0.0),                 # between index and middle finger, at their middle joints
    'axis_to_filter': tuple(_u),                  # unit vector, hand-local
    'filter_out': 0.030,                          # filter tip distance from the grip (palm side)
    'length': 0.08, 'radius': 0.004, 'ember': 0.010,
}
LIGHTER = {'bone': P + 'LeftHand', 'center': (-0.072, 0.070, 0.026), 'size': (0.026, 0.015, 0.055),   # x, y(thick), up
           'up': (-1.0, 0.0, 0.0)}                # hand-local direction of the lighter's top (thumb side, left hand)


def lighter_top_local():
    return Vector(LIGHTER['center']) + Vector(LIGHTER['up']) * (LIGHTER['size'][2] / 2)


def cig_matrix():
    """Hand-local 4x4 of the cigarette prop: origin at the grip, prop +Y axis toward the LIT end."""
    u = Vector(CIGARETTE['axis_to_filter'])
    q = Vector((0, 1, 0)).rotation_difference(-u)
    m = q.to_matrix().to_4x4()
    m.translation = Vector(CIGARETTE['grip'])
    return m


def cig_points_local():
    g, u = Vector(CIGARETTE['grip']), Vector(CIGARETTE['axis_to_filter'])
    filt = g + u * CIGARETTE['filter_out']
    lit = g - u * (CIGARETTE['length'] - CIGARETTE['filter_out'])
    return filt, lit


# ------------------------------------------------------------------------------------- v02 rig extension
class RigV02(K.Rig):
    def __init__(self, B):
        super().__init__(B)
        filt, _ = cig_points_local()
        self.hand_pts['Right']['cig'] = filt.copy()
        self.hand_pts['Left']['lighter'] = lighter_top_local()

    def _arm_ik(self, out, s, sgn, p, w):
        """v02: optional hand orientation before the v01 arm IK. ik<k>.ori (0..1) turns the hand about the wrist so
        its prop axis (right: the cigarette, filter -> lit end; left: the lighter's top) points along (ik<k>.cy outward yaw, ik<k>.cp downward pitch,
        degrees, in the Idle head frame carried by the ik<k>.rel bone) with the fingers rolled ik<k>.fr degrees from
        straight up (straight forward for a vertical axis) about that axis; the IK then puts the reach point on the target."""
        k = s[0]
        ori = p.get('ik%s.ori' % k, 0.0) * w
        if ori > 1e-6:
            cy, cp = math.radians(p.get('ik%s.cy' % k, 0.0)), math.radians(p.get('ik%s.cp' % k, 0.0))
            c = Vector((math.sin(cy) * math.cos(cp) * sgn, -math.cos(cy) * math.cos(cp), -math.sin(cp)))
            ref = Vector((0, -1, 0)) if abs(c.z) > 0.8 else Vector((0, 0, 1))
            f0 = Matrix.Rotation(math.radians(p.get('ik%s.fr' % k, 0.0)) * sgn, 3, c) @ ref
            rel = p.get('ik%s.rel' % k)
            if rel:
                Rr = (out[P + rel] @ self.base[P + rel].inverted()).to_3x3()
                c, f0 = Rr @ c, Rr @ f0
            # aligned hand-local axis: right hand = the cigarette (filter -> lit end), left hand = the lighter's top
            a1 = -Vector(CIGARETTE['axis_to_filter']) if sgn < 0 else Vector(LIGHTER['up'])
            a2 = (Vector((0, 1, 0)) - a1 * a1.y).normalized()
            b1 = c.normalized()
            b2 = (f0 - b1 * f0.dot(b1)).normalized()
            Ml = Matrix((a1, a2, a1.cross(a2))).transposed()
            Mw = Matrix((b1, b2, b1.cross(b2))).transposed()
            want = (Mw @ Ml.transposed()).to_quaternion()
            hm = out[P + s + 'Hand'].to_3x3().to_quaternion()
            q = hm.slerp(want, min(1.0, ori))
            M = K.rot_about(out[P + s + 'Hand'].translation, q @ hm.inverted())
            for n_ in self.B.subtree(s + 'Hand'):
                out[n_] = M @ out[n_]
        super()._arm_ik(out, s, sgn, p, w)

    def contact(self, out, p):
        g = p.get('wall.gap')
        if g is None or self.wall_y is None:
            return super().contact(out, p)
        wy = self.wall_y
        self.wall_y = wy - g
        try:
            return super().contact(out, p)
        finally:
            self.wall_y = wy

    def pose(self, p, contact=True):
        w = p.get('wall.on', 0.0)
        if not contact or w <= 0.0 or self.wall_y is None:
            return super().pose(p, contact)
        q = dict(p)
        q['wall'] = 1.0
        out_t, info_t = super().pose(q, contact)
        if w >= 1.0:
            return out_t, info_t
        hy_t = out_t[P + 'Hips'].translation.y - self.base[P + 'Hips'].translation.y
        hy_a = p.get('hip.y', 0.0)
        r = dict(p)
        r['hip.y'] = hy_a + w * (hy_t - hy_a)
        return super().pose(r, contact)


def impact(ks, i, factor=2.0, out='flat'):
    """Broken tangents at key i of a filled key list: every channel arrives with `factor` x its average slope over the
    previous segment (factor 2 after a flat key = a constant-acceleration fall) and leaves `out` (a hard stop)."""
    t0, a = ks[i - 1][0], ks[i - 1][1]
    t1, b = ks[i][0], ks[i][1]
    tan = {}
    for c, v in b.items():
        if isinstance(v, str):
            continue
        tan[c] = (factor * (v - a.get(c, 0.0)) / (t1 - t0), out)
    tan['*'] = 'auto'
    ks[i] = (t1, b, tan)
    return ks


def flat(ks, i):
    ks[i] = (ks[i][0], ks[i][1], 'flat')
    return ks


# ------------------------------------------------------------------------------------- BarDoor_Enter_v02
BD_ENTER_T = 1.7


NATURAL = -1.0                # wall.gap sentinel: "the gap this key pose has where it was authored" (resolved lazily)


class GapTrack(K.FitTrack):
    """FitTrack whose `wall.gap` = NATURAL keys are replaced on first use by the key pose's own distance to the wall
    (pelvis where authored, no contact), so switching `wall.on` on there moves nothing."""

    def __init__(self, keys, flats=(), impacts=()):
        super().__init__(keys)
        self.flats, self.impacts = flats, impacts

    def __call__(self, t):
        if self.tr is None:
            rig = K.RIG
            rig.vertex_dominant()
            for k in self.keys:
                if k[1].get('wall.gap') == NATURAL:
                    q = dict(k[1])
                    q['wall.on'], q['wall'] = 0.0, 0.0
                    out, _ = rig.pose(q, contact=False)
                    pts = rig.B.mesh_points(out)
                    k[1]['wall.gap'] = CP.WALL_Y - float(pts[~rig.is_foot, 1].max())
            for i in self.flats:
                flat(self.keys, i)
            for i in self.impacts:
                impact(self.keys, i)
        return super().__call__(t)


def _lean_enter_v02():
    base = CP.lean_base()
    k = keys(
        (0.0, {'ikL.rel': 'Spine', 'ikR.rel': 'Spine', 'ikL.pt': 'fist', 'ikR.pt': 'fist', 'fR.tf': 1.0}),
        (0.10, {'hd.w': -4, 'hip.z': -0.004}),                                             # tiny counter-turn
        (0.28, add(shift(0.3), {'hd.w': 52, 'nk.w': 18, 's3.w': 14, 's2.w': 8, 's1.w': 4, 'hd.r': 6, 'hd.p': 8,
                                'nk.p': 3, 'hip.z': -0.008})),                             # glance back at the wall
        (0.40, {'hd.w': 55, 'nk.w': 19, 'hd.p': 9}),                                        # (hold)
        (0.58, add(shift(0.0), {'hd.w': 0, 'nk.w': 0, 's3.w': 0, 's2.w': 0, 's1.w': 0, 'hd.r': 0, 'hip.p': 5, 's1.p': 3,
                                's2.p': 10, 's3.p': 8, 'nk.p': 4, 'hd.p': 12, 'hip.z': -0.04, 'hip.y': -0.025,
                                'cL.u': 9, 'cR.u': 9, 'aL.f': 12, 'aR.f': 12, 'eL': 18, 'eR': 18,
                                'wall.gap': NATURAL})),                                     # dip: gather
        (0.68, {'s2.p': 11, 's3.p': 9, 'hd.p': 14, 'cL.u': 11, 'cR.u': 11, 'hip.z': -0.042, 'wall.on': 1.0,
                'wall.gap': NATURAL}),                                                      # tip point
        (0.84, {'wall.gap': 0.0, 'hip.p': -13, 's1.p': -3, 's2.p': -2, 's3.p': 0,
                'nk.p': 8, 'hd.p': 18, 'hip.z': -0.055, 'cL.u': -3, 'cR.u': -3, 'aL.f': 26, 'aR.f': 24,
                'aL.o': 22, 'aR.o': 20, 'eL': 30, 'eR': 28}),                                # THUD: back hits the wall
        (0.89, {'nk.p': -2, 'hd.p': -8, 'aL.f': -6, 'aR.f': -8, 'aL.o': 34, 'aR.o': 32, 'eL': 14, 'eR': 14,
                'hip.z': -0.07, 'cL.u': -6, 'cR.u': -6}, {'wall.gap': ('flat', 1.5), '*': 'auto'}),  # head whips back (bonk)
        (0.94, {'wall.gap': 0.05, 'nk.p': 7, 'hd.p': 14, 'aL.f': 12, 'aR.f': 10, 'aL.o': 8, 'aR.o': 8, 'eL': 26,
                'eR': 24, 's3.p': 5, 'hip.z': -0.075, 'cL.u': -4, 'cR.u': -4}),            # rebound, head bounces
        (1.02, {'wall.gap': 0.0, 'nk.p': 1, 'hd.p': -5, 'aL.f': -4, 'aR.f': -4, 'aL.o': 10, 'aR.o': 10, 'eL': 6,
                'eR': 6, 's3.p': 1, 'hip.p': -11, 'hip.z': -0.06, 'cL.u': -2, 'cR.u': -2}),  # settles on the wall
        (1.10, {'nk.p': 2, 'hd.p': 2, 'aL.f': 3, 'aR.f': 3, 'aL.o': 5, 'aR.o': 5, 'eL': 12, 'eR': 12}),  # arms dangle
        (1.14, {'wall': 1.0}),
        (1.32, add(shift(0.8), {'hip.y': 0.10, 'fR.z': 0.12, 'fR.y': 0.12, 'fR.r': 30, 'kR': 6, 'hip.z': -0.03,
                                'hd.p': 4, 'nk.p': 3, 'hip.p': -9}, CP.POCKET_BOTH, {'aL.o': 4, 'aR.o': 4})),  # foot up
        (1.50, add(base, {'fR.tf': 0.0, 'wall.on': 1.0})),
        (BD_ENTER_T, base),
    )
    tr = GapTrack(_fill(k, start={}, end=base), flats=(5,), impacts=(6,))

    def params(t):
        p = tr(t)
        # "ow": a dazed little head wobble after the bonk (zero outside 0.92-1.33 s)
        w = K.window(t, 1.0, 1.25, 0.08) * math.sin(2 * math.pi * 3.0 * (t - 0.97))
        p['hd.r'] = p.get('hd.r', 0.0) + 6.0 * w
        p['nk.r'] = p.get('nk.r', 0.0) - 2.0 * w
        return p
    return params


# ------------------------------------------------------------------------------------- SmokeCorner v02
LIPS = (0.04, -0.131, 1.392)        # Idle-space point at the right corner of the mouth (x outward), carried by the Head
LIPS_DIR = (22.0, 10.0, 45.0)        # cigarette at the lips: yaw outward, pitch down, finger roll (deg, Idle head frame)
SMOKE_BASE = CP.smoke_base


def at_lips(extra=None):
    """Right hand IK: the cigarette's filter tip on the lips."""
    d = {'ikR.w': 1.0, 'ikR.rel': 'Head', 'ikR.pt': 'cig', 'ikR.x': LIPS[0], 'ikR.y': LIPS[1], 'ikR.z': LIPS[2],
         'ikR.ori': 1.0, 'ikR.cy': LIPS_DIR[0], 'ikR.cp': LIPS_DIR[1], 'ikR.fr': LIPS_DIR[2],
         'aR.f': 50, 'aR.o': 22, 'eR': 135, 'eR.t': 75, 'wR.f': -10, 'wR.d': 0,
         'fiR.r': 0.35, 'fiR.k': 0.4, 'thR': 0.15}                    # ring/pinky open a little: off the chin
    d.update(extra or {})
    return d


def lit_point(cy, cp, back=0.0, down=0.0):
    """Idle head-space point (x outward for the RIGHT side as ik<k>.x expects for the left hand: world x) of the lit end
    of the cigarette held at LIPS along (cy, cp), offset `down` below and `back` toward the face."""
    a, b = math.radians(cy), math.radians(cp)
    c = Vector((-math.sin(a) * math.cos(b), -math.cos(a) * math.cos(b), -math.sin(b)))
    lit = Vector((-LIPS[0], LIPS[1], LIPS[2])) + c * CIGARETTE['length']        # the filter tip is on the lips
    return lit + Vector((0, back, -down))


AWAY_R = {'ikR.w': 0.0, 'aR.f': 34, 'aR.o': 20, 'aR.t': 0, 'eR': 92, 'eR.t': 70, 'wR.f': -38, 'wR.d': 0}   # cig out front, up
REST_R = {'ikR.w': 0.0, 'aR.f': 16, 'aR.o': 26, 'aR.t': 0, 'eR': 55, 'eR.t': 55, 'wR.f': -25, 'wR.d': 0}   # out by the hip
LOOK_R = {'ikR.w': 0.0, 'aR.f': 28, 'aR.o': 10, 'aR.t': 0, 'eR': 96, 'eR.t': 45, 'wR.f': -12, 'wR.d': 0}   # looks at the ash
SM_T = 6.0


def _smoke_loop_v02():
    base = SMOKE_BASE()
    k = keys(
        (0.0, base),
        (0.16, {'aR.f': 18, 'aR.o': 4, 'eR': 112, 'wR.f': -14, 'hd.p': 3, 'ikR.cy': LIPS_DIR[0], 'ikR.cp': LIPS_DIR[1],
                'ikR.fr': LIPS_DIR[2]}),                                                    # little dip: anticipation
        (0.30, {'aR.f': 34, 'aR.o': 26, 'eR': 128, 'wR.f': -20, 'hd.p': 5}),                # elbow leads up and out
        (0.46, add(at_lips(), {'hd.p': 8, 's3.p': 2})),                                       # cig to the lips
        (0.56, {'hd.p': 6}),
        (1.08, {'s3.p': -6, 's2.p': -3, 'cL.u': 10, 'cR.u': 9, 'hd.p': -3, 'hd.r': -5, 'nk.p': -2}),  # puff: chest fills
        (1.22, {'hd.p': -5}),
        (1.42, add(AWAY_R, {'hd.p': -12, 'nk.p': -5, 'hd.r': -3, 's3.p': -7, 'cL.u': 11, 'cR.u': 10})),  # hand away, hold
        (1.58, {'hd.p': -13, 'aR.o': 21}),
        (2.30, {'hd.w': 24, 'nk.w': 6, 'hd.p': -8, 'hd.r': 3, 'nk.p': -2, 's3.p': 3, 's2.p': 3, 'cL.u': -2, 'cR.u': -2,
                'hip.z': -0.01, 'aR.f': 30, 'eR': 86}),                                       # long exhale aside
        (2.62, add(REST_R, {'hd.w': 6, 'nk.w': 0, 'hd.p': 2, 'hd.r': 0, 'nk.p': 0, 's3.p': 1, 's2.p': 1, 'cL.u': 0,
                            'cR.u': 0, 'hip.z': -0.004})),                                    # hand rests by the hip
        (2.84, add(LOOK_R, {'hd.w': -6, 'hd.p': 12, 'nk.p': 4, 's2.p': 2})),                 # looks at the ash
        (2.94, {'wR.f': -34, 'thR': 0.0, 'eR': 114, 'aR.f': 31}),                            # cock: forearm and wrist up
        (2.99, {'wR.f': 18, 'thR': 0.95, 'eR': 80, 'aR.f': 24}),                             # SNAP: forearm + wrist + thumb
        (3.07, {'wR.f': -16, 'thR': 0.2, 'eR': 104, 'aR.f': 29}),
        (3.15, {'wR.f': 12, 'thR': 0.85, 'eR': 84, 'aR.f': 25}),                             # second tap
        (3.28, {'wR.f': -12, 'thR': 0.3, 'eR': 96, 'aR.f': 28, 'hd.p': 9}),
        (3.60, add(shift(-0.35), REST_R, {'hd.p': 0, 'hd.w': -26, 'nk.w': -6, 's3.w': -6, 'hd.r': -2, 'nk.p': 0,
                                          's2.p': 0, 's3.p': 0, 'hip.z': 0.0})),             # weight over, look around
        (4.05, {'hd.w': -32}),
        (4.20, {'hd.p': -10, 'hd.w': -29}),                                                  # "sup" chin-up
        (4.36, {'hd.p': 2}),
        (4.62, add(shift(0.45), {'hd.w': 0, 'nk.w': 0, 's3.w': 0, 'hd.p': 4, 'hd.r': -2, 'aR.f': 22, 'aR.o': 26,
                                 'eR': 110, 'wR.f': -16})),                                  # elbow leads up again
        (4.78, add(at_lips(), {'hd.p': 8, 's3.p': 1})),                                       # quick second puff
        (5.08, {'s3.p': -4, 'cL.u': 6, 'cR.u': 5, 'hd.p': -2, 'hd.r': -3}),
        (5.24, add(AWAY_R, {'hd.p': -6, 'cL.u': 6, 'cR.u': 5, 's3.p': -4})),
        (5.62, {'hd.w': 16, 'hd.p': -6, 'hd.r': 2, 's3.p': 1, 'cL.u': 0, 'cR.u': 0, 'aR.f': 28}),  # exhale aside
        (SM_T, base),
    )
    ks = _fill(k)
    return _with_ash_twitch(K.FitTrack(ks, periodic=True))


def _with_ash_twitch(tr):
    def params(t):
        return tr(t)
    return params


def _smoke_enter_v02():
    base = SMOKE_BASE()
    pocket = add(CP.POCKET_BOTH, {'ikR.z': 0.905, 'ikL.z': 0.905})
    light_dir = (14.0, 14.0, 70.0)                                   # cig more forward while lighting
    flame = lit_point(light_dir[0], light_dir[1], back=0.006, down=0.016)
    cup_R = at_lips({'ikR.cy': light_dir[0], 'ikR.cp': light_dir[1], 'ikR.fr': light_dir[2]})
    cup_L = {'ikL.w': 1.0, 'ikL.rel': 'Head', 'ikL.pt': 'lighter', 'ikL.x': flame.x, 'ikL.y': flame.y, 'ikL.z': flame.z,
             'ikL.ori': 1.0, 'ikL.cy': 0.0, 'ikL.cp': -90.0, 'ikL.fr': -75.0,
             'aL.f': 62, 'aL.o': 8, 'eL': 128, 'eL.t': 75, 'wL.f': -10, 'wL.d': 0, 'fiL': 0.75, 'thL': 0.2}
    k = keys(
        (0.0, {'ikR.rel': 'Spine', 'ikR.pt': 'fist', 'ikL.rel': 'Spine', 'ikL.pt': 'fist'}),
        (0.20, add(pocket, {'hd.p': 12, 's2.p': 4, 's3.p': 2, 'hip.z': -0.006})),           # hands into the pocket
        (0.32, {'ikR.z': 0.89, 'ikL.z': 0.915, 'hd.p': 13}),                                 # rummage
        (0.46, {'ikR.w': 0.0, 'ikL.w': 0.0, 'aR.f': 36, 'aR.o': 22, 'eR': 118, 'eR.t': 60, 'wR.f': -18, 'fiR': 0.0,
                'fiR.r': 0.8, 'fiR.k': 0.85, 'fiR.i': 0.06, 'fiR.m': 0.12, 'thR': 0.3,
                'aL.f': 40, 'aL.o': 6, 'eL': 112, 'eL.t': 60, 'fiL': 0.75, 'thL': 0.2, 'hd.p': 6,
                'ikL.cy': 0.0, 'ikL.cp': -90.0, 'ikL.fr': -75.0, 'ikR.cy': light_dir[0], 'ikR.cp': light_dir[1],
                'ikR.fr': light_dir[2]}),                    # cig + lighter out (prop directions fixed from here on)
        (0.60, add(shift(0.3), cup_R, cup_L, {'hd.p': 12, 's3.p': 4, 's2.p': 3})),         # cupped at the lips
        (0.70, {'hd.p': 14}),
        (0.76, {'thL': 0.95, 'wL.f': -4}),                                                   # flick 1: nothing
        (0.83, {'thL': 0.25, 'hd.r': 4, 'wL.f': -12}),
        (0.94, {'thL': 1.0, 'hd.r': 0, 'wL.f': -4, 'hd.p': 15}),                             # flick 2: lit
        (1.06, {'s3.p': -4, 'cL.u': 7, 'cR.u': 6, 'hd.p': 6, 'thL': 0.6}),                  # first drag, chest fills
        (1.20, {'ikL.w': 0.0, 'ikL.ori': 0.0, 'aL.f': CP.ARM_ACROSS_L['aL.f'], 'aL.o': CP.ARM_ACROSS_L['aL.o'], 'aL.t': 0.0,
                'eL': CP.ARM_ACROSS_L['eL'], 'eL.t': 30, 'wL.f': 8, 'fiL': 0.5, 'thL': 0.3}),   # lighter hand drops to the belly
        (1.30, add(CP.ARM_ACROSS_L, {'ikR.w': 0.0, 'aR.f': 34, 'aR.o': 20, 'eR': 92, 'eR.t': 70, 'wR.f': -38,
                                     's3.p': -6, 'cL.u': 9, 'cR.u': 8, 'hd.p': -10, 'nk.p': -4})),   # cig away, hold
        (1.42, {'hd.p': -12}),
        (1.70, add(base, {'hd.w': 22, 'nk.w': 5, 'hd.p': -8, 'hd.r': 2, 'cL.u': -1, 'cR.u': -1, 's3.p': 2,
                          'aR.f': 28, 'aR.o': 10, 'eR': 110})),                              # exhale aside
        (1.90, base),
    )
    return K.FitTrack(_fill(k, start={}, end=base))


# ------------------------------------------------------------------------------------- registry
_WALL_PROP = CP._WALL_PROP
CONTRACTS = {c: CP.CONTRACTS[c] for c in ('smoke', 'lean')}


def _ember(segments, base=0.15):
    """Preview ember glow 0..1: base level plus bumps during drags [(t0, t_peak, t1), ...]."""
    def f(t):
        g = base
        for a, m, b in segments:
            if a < t < b:
                u = (t - a) / (m - a) if t <= m else 1.0 - (t - m) / (b - m)
                g = max(g, base + (1 - base) * K.smooth(max(0.0, min(1.0, u))))
        return g
    return f


CLIPS = {
    'BarDoor_Enter': {
        'T': BD_ENTER_T, 'loop': False, 'start': 'idle', 'end': 'lean', 'params': _lean_enter_v02(),
        'setup': [CP.wall_setup], 'props': _WALL_PROP, 'activity': 'BarDoor', 'role': 'enter',
        'feet_free': {'Right': [(1.10, 1.68)]}, 'events': {'Thud': 0.84, 'Bonk': 0.89},
        'beats': ['0.10-0.40 glance back over the left shoulder at the wall', '0.45-0.68 forward dip: gathers, shoulders up',
                  '0.68-0.84 lets himself fall back like a sack (accelerating)',
                  '0.84 THUD: hood and shoulders hit the wall (event Thud), knees buckle, arms flop',
                  '0.89 head whips back and bonks the wall (event Bonk)', '0.96 small rebound off the wall, head bounces',
                  '1.05 settles on the wall', '1.12-1.50 right foot up onto the wall, hands into the pocket',
                  '1.70 lean base']},
    'SmokeCorner_Enter': {
        'T': 1.9, 'loop': False, 'start': 'idle', 'end': 'smoke', 'params': _smoke_enter_v02(),
        'activity': 'SmokeCorner', 'role': 'enter',
        'events': {'CigOn': 0.40, 'LighterOn': 0.40, 'Light': 0.94, 'LighterOff': 1.20, 'Exhale': 1.46},
        'preview': {'cig': [(0.40, 9.9)], 'lighter': [(0.40, 1.20)], 'flame': [(0.94, 1.08)],
                    'ember': _ember([(0.94, 1.06, 1.40)], base=0.0), 'ember_from': 0.94},
        'beats': ['0.0-0.32 both hands into the hoodie pocket, looks down, rummages',
                  '0.46 out come the cigarette (right) and the lighter (left) (events CigOn / LighterOn 0.40)',
                  '0.60-0.70 cig to the lips, hands cupped, head dips into them',
                  '0.76 first flick: nothing; 0.83 head tilt "huh"', '0.94 second flick: lit (event Light)',
                  '1.06 first drag: chest fills', '1.06-1.20 lighter hand drops to the belly (event LighterOff 1.20)',
                  '1.30 cig pulled away from the lips, breath held, chin up',
                  '1.46-1.70 exhale aside (event Exhale)', '1.90 smoke base']},
    'SmokeCorner_Loop': {
        'T': SM_T, 'loop': True, 'start': 'smoke', 'end': 'smoke', 'params': _smoke_loop_v02(),
        'activity': 'SmokeCorner', 'role': 'loop',
        'events': {'Puff': 0.50, 'Exhale': 1.62, 'AshTap': 2.99, 'AshTap2': 3.15, 'Puff2': 4.80, 'Exhale2': 5.28},
        'preview': {'cig': [(0.0, 9.9)], 'ember': _ember([(0.46, 0.9, 1.6), (4.78, 5.0, 5.4)], base=0.15)},
        'beats': ['0.16 little dip (anticipation)', '0.30-0.46 elbow leads, cig to the lips in an arc',
                  '0.50-1.22 held puff: chest fills, head tilts (event Puff)', '1.42 hand pulled away out front, breath held',
                  '1.62-2.30 long exhale aside (event Exhale)', '2.62 hand rests by the hip, away from the body',
                  '2.84-3.28 looks at the ash: cocks the wrist, two sharp thumb taps (events AshTap 2.99 / 3.15)',
                  '3.60-4.36 weight over, looks around, "sup" chin-up', '4.62-4.78 elbow leads, quick second puff',
                  '5.24-5.62 hand away, exhale aside (event Exhale2)', '6.00 smoke base']},
}
for _c in CLIPS.values():
    _c['activity_doc'] = _c['activity']

PLACEMENT = {
    'BarDoor': 'wall plane %.2f m behind the root (the hood touches it, the right sole rests on it)' % CP.WALL_Y,
    'SmokeCorner': 'free standing, in place; cigarette = separate attachment on %s (README v02 section: hand-local '
                   'transform), enabled/disabled by the events' % CIGARETTE['bone'],
}

# v01 deliverables that claim the same contract poses (the v02 ends must equal them exactly)
CHAIN_V01 = {'lean': ['BarDoor_Enter', 'BarDoor_Loop', 'BarDoor_Exit'],
             'smoke': ['SmokeCorner_Enter', 'SmokeCorner_Loop', 'SmokeCorner_Exit']}
