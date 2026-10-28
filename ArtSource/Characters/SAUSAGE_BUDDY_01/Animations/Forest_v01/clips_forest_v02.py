"""Forest v02 (owner review of v01: "too complex, too Disney"): the same three clips redone in the style of the best
existing clips (Flee_Run, JumpOut, Cop_Trip): a few big key poses, snappy 2-4 frame transitions, clear holds, one arm
action at a time, and SUDDEN FACE SNAPS (Blink / Surprised / Worried / Happy, keyed 0 -> 1 in 1-2 frames).

  Junkie_Walk  1.2 s loop (2 steps): bent knees, big dumb side-to-side bob, arms hanging, head lolling; gag: the eyes
               droop shut and the head sinks ... SNAP wide awake with a jolt.
  Inject       3.5 s: syringe out (Happy) -> left arm out -> JAB (Surprised snap, whole body jolts) -> blissful hold
               (Happy + half Blink) -> falls straight back stiff as a plank -> thud -> high_lie_v02.
  High_Lie_Loop 3.5 s loop: lies still, dumb half-asleep face dozing off, one leg twitch (eyes snap open), one arm flop.

Reuses clips_forest (v01, unchanged): ForestRig, the syringe grip, the presented-forearm needle targets, floor_setup.
The face track is data here (FACE_*): build_forest_v02 keys it on the Face shape keys of the saved .blend and writes it
to the manifest for Unity (GreyboxFace); the FBX stays armature-only.
"""
import math
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
if str(HERE.parent / 'Crowd_v01') not in sys.path:
    sys.path.insert(0, str(HERE.parent / 'Crowd_v01'))
import numpy as np
import crowd_core as K
import acting_core as C
from crowd_core import add
from clips_stand import _fill, keys
import clips_forest as F

REV = 'v02'
FPS = 30
fr = lambda n: n / FPS                    # frames -> seconds
SHAPES = ('Blink', 'Surprised', 'Worried', 'Happy')


class Face:
    """Face track: list of (t, {shape: weight}); shapes not named hold their value; linear between keys.
    A snap = two keys 1-2 frames apart."""

    def __init__(self, ks, T, loop):
        cur = {s: 0.0 for s in SHAPES}
        self.keys = []
        for t, d in ks:
            cur = dict(cur)
            cur.update(d)
            self.keys.append((t, cur))
        if loop:
            self.keys.append((T, dict(self.keys[0][1])))
        self.T = T

    def __call__(self, t):
        ts = [k[0] for k in self.keys]
        return {s: float(np.interp(t, ts, [k[1][s] for k in self.keys])) for s in SHAPES}

    def listing(self):
        """[(t, shape, weight)] at every key where a shape changes (for Unity)."""
        out, prev = [], None
        for t, d in self.keys:
            for s in SHAPES:
                if prev is None or abs(prev[s] - d[s]) > 1e-9:
                    out.append((round(t, 4), s, round(d[s], 3)))
            prev = d
        return out


# ===================================================================================== Junkie_Walk (1.2 s, 2 steps)
W_T, W_V = 1.2, 0.6           # cycle, ground speed (m/s): 0.36 m steps, a slow bow-legged shuffle
STANCE = 0.62
Y_TD = -0.22                  # ball y at touchdown (world)
BALL0_Y = -0.10


def _swing_curves():
    dur = (1 - STANCE) * W_T
    m = W_V * dur
    y0, y1 = Y_TD + W_V * STANCE * W_T, Y_TD
    yc = C.Curve([(0.0, y0, m), (0.08, y0 + 0.08 * m, m), (0.5, y0 + (y1 - y0) * 0.45), (0.92, y1 - 0.08 * m, m),
                  (1.0, y1, m)])
    zc = C.Curve([(0.0, 0.0, 0.12), (0.10, 0.012), (0.55, 0.055), (0.85, 0.02), (1.0, 0.0, -0.08)])
    rc = C.Curve([(0.0, 18.0), (0.2, 22.0), (0.55, 6.0), (0.85, -6.0), (1.0, -4.0, 'flat')])
    return yc, zc, rc


_SW = _swing_curves()


def wfoot(ph):
    """(ball y, z, roll) at phase 0..1 (0 = touchdown)."""
    if ph < STANCE:
        a = ph * W_T
        b = (STANCE - ph) * W_T
        roll = -4.0 * (1 - K.smooth(a / 0.08)) + 18.0 * max(0.0, 1 - b / 0.22) ** 1.7
        return Y_TD + W_V * a, 0.0, roll
    u = (ph - STANCE) / (1 - STANCE)
    yc, zc, rc = _SW
    return yc(u), max(0.0, zc(u)), rc(u)


# the gag, one per cycle: head sinks with the eyes closing ... SNAP awake with a jolt (frames)
_GAG = K.Track([(0.0, {'hd': 4.0, 'nk': 0.0, 'cu': 0.0, 'hz': 0.0}),
                (fr(20), {'hd': 20.0, 'nk': 7.0, 'cu': -2.0, 'hz': -0.008}),
                (fr(23), {'hd': 22.0, 'nk': 8.0, 'cu': -2.0, 'hz': -0.010}),
                (fr(25), {'hd': -16.0, 'nk': -5.0, 'cu': 18.0, 'hz': 0.020}),        # SNAP (2 frames)
                (fr(26), {'hd': -18.0, 'nk': -6.0, 'cu': 19.0, 'hz': 0.022}),
                (fr(31), {'hd': -14.0, 'nk': -4.0, 'cu': 15.0, 'hz': 0.016}),        # hold, wide-eyed
                (W_T, {'hd': 4.0, 'nk': 0.0, 'cu': 0.0, 'hz': 0.0})], periodic=True)
FACE_WALK = Face([(0.0, {'Blink': 0.45, 'Worried': 0.2}), (fr(23), {'Blink': 1.0}),
                  (fr(24), {'Blink': 1.0, 'Surprised': 0.0}), (fr(25), {'Blink': 0.0, 'Surprised': 1.0}),
                  (fr(31), {'Surprised': 1.0}), (fr(34), {'Surprised': 0.0, 'Blink': 0.45})], W_T, loop=True)


def walk_params(t):
    p = {'hip.soft': 0.04, 'kL': 16.0, 'kR': 16.0}
    for side, off in (('L', 0.0), ('R', 0.5)):
        y, z, roll = wfoot((t / W_T + off) % 1.0)
        p['f%s.y' % side] = y - BALL0_Y
        p['f%s.z' % side] = z
        p['f%s.r' % side] = roll
        p['f%s.x' % side] = 0.03
        p['f%s.w' % side] = 16.0
    c = 2 * math.pi * t / W_T
    g = _GAG(t)
    sway = math.sin(c)                                   # +1 over the left foot (t = T/4), -1 over the right
    p['hip.x'] = 0.065 * sway
    p['hip.z'] = -0.10 - 0.022 * math.cos(2 * c) + g['hz']
    p['hip.r'] = -6.0 * sway
    p['hip.w'] = -6.0 * math.cos(c)
    p['hip.p'] = -2.0
    p['s1.r'], p['s2.r'] = 5.0 * sway, 6.0 * sway       # the whole body rocks onto the standing leg
    p['s1.p'], p['s2.p'], p['s3.p'] = 4.0, 10.0, 6.0
    p['nk.p'] = 6.0 + g['nk']
    p['hd.p'] = g['hd']
    p['hd.r'] = 16.0 * math.sin(c - 1.0)                # dumb head loll, a beat behind the body
    p['cL.u'] = p['cR.u'] = -4.0 + g['cu']
    pitch = p['hip.p'] + p['s1.p'] + p['s2.p'] + p['s3.p']
    for side, sgn in (('L', 1), ('R', -1)):              # arms just hang (they swing out with the rock)
        p['a%s.f' % side] = -0.8 * pitch + 3.0
        p['a%s.o' % side] = 9.0 + sgn * 11.0 * sway * 0.6 + 0.35 * g['cu']
        p['e' + side] = 14.0
        p['w%s.f' % side] = 16.0
        p['fi' + side] = 0.3
    return p


# ===================================================================================== high_lie_v02 (plank landing)
# lying flat on the back where the plank fall lands: hips ~0.84 m behind the root, head top ~1.8 m behind, arms on
# the floor out at shoulder level (palms up), feet at the root flopped out
LIE2_HAND = (0.60, 1.22, 0.030)        # palm up on the floor, out at shoulder level


def lie2_base():
    p = {'hip.free': 1.0, 'lift': 1.0, 'gnd': 1.0, 'hip.y': 0.84, 'hip.z': -0.70, 'hip.p': -86.0, 's1.p': -1.0,
         's2.p': -1.0, 's3.p': -1.0, 'nk.p': -2.0, 'hd.p': 0.0, 'hd.w': 12.0,
         'fL.x': 0.05, 'fR.x': 0.05, 'fL.y': 0.05, 'fR.y': 0.05, 'fL.r': -78.0, 'fR.r': -78.0, 'fL.w': 32.0,
         'fR.w': 32.0, 'fL.sole': 1.0, 'fR.sole': 1.0, 'kL': 20.0, 'kR': 20.0,
         'aL.f': 0.0, 'aR.f': 0.0, 'aL.o': 75.0, 'aR.o': 75.0, 'eL': 20.0, 'eR': 20.0, 'eL.t': 60.0, 'eR.t': 60.0,
         'fiL': 0.35, 'fiR': 0.35, 'thL': 0.2, 'thR': 0.2}
    for k in 'LR':
        p.update({'ik%s.w' % k: 1.0, 'ik%s.rel' % k: '', 'ik%s.orel' % k: '', 'ik%s.pt' % k: 'palm',
                  'ik%s.floor' % k: 1.0, 'ik%s.x' % k: LIE2_HAND[0], 'ik%s.y' % k: LIE2_HAND[1],
                  'ik%s.z' % k: LIE2_HAND[2], 'ik%s.ow' % k: 1.0, 'ik%s.dx' % k: 1.0, 'ik%s.dy' % k: 0.25,
                  'ik%s.dz' % k: 0.0, 'ik%s.ux' % k: 0.0, 'ik%s.uy' % k: 0.0, 'ik%s.uz' % k: 1.0})
    return p


def plank(theta):
    """Stiff fall backwards about the heels: pelvis and feet rotate together by theta (deg), spine straight."""
    th = math.radians(theta)
    y = 0.095 - 0.095 * math.cos(th) + 0.821 * math.sin(th)
    z = 0.095 * math.sin(th) + 0.821 * math.cos(th)
    return {'hip.free': 1.0, 'hip.y': y, 'hip.z': z - 0.821, 'hip.p': -theta, 'fL.r': -theta, 'fR.r': -theta,
            'fL.sole': 1.0, 'fR.sole': 1.0,
            's1.p': 0.0, 's2.p': 0.0, 's3.p': 0.0, 'nk.p': 0.0, 'hd.p': 0.0, 'hd.w': 0.0, 'hip.x': 0.0}


LIE2_VIEWS = {'side': ((5.6, 0.85, 0.8), (0.0, 0.85, 0.35), 2.4),
              'three_quarter': ((3.4, -2.6, 2.3), (0.0, 0.80, 0.25), 2.2),
              'front': ((0.0, -4.6, 1.6), (0.0, 0.8, 0.3), 2.4)}
INJ_VIEWS = {'side': ((5.6, 0.6, 1.0), (0.0, 0.6, 0.7), 2.6),
             'three_quarter': ((3.6, -3.4, 2.3), (0.0, 0.45, 0.70), 2.5),
             'front': ((0.0, -5.0, 1.4), (0.0, 0.6, 0.7), 2.6)}
WALK_VIEWS = {'side': ((5.2, 0.0, 1.0), (0.0, 0.0, 0.9), 2.0),
              'three_quarter': ((3.6, -4.6, 1.9), (0.0, 0.0, 0.92), 1.95),
              'front': ((0.0, -5.2, 1.0), (0.0, 0.0, 0.9), 2.0)}

# ===================================================================================== Inject (3.5 s)
INJ_T = 3.5
SOFT = {'hip.z': -0.04, 's2.p': 6.0, 'nk.p': 4.0, 'hd.p': 4.0}
ADMIRE_R = {'ikR.w': 0.0, 'aR.f': 55.0, 'aR.o': 14.0, 'aR.t': 0.0, 'eR': 128.0, 'eR.t': 70.0, 'wR.f': -6.0,
            'fiR': 0.42, 'thR': 0.55}
HANG_R = {'ikR.w': 0.0, 'ikR.ow': 0.0, 'aR.f': 6.0, 'aR.o': 10.0, 'aR.t': 0.0, 'eR': 18.0, 'eR.t': 10.0,
          'wR.f': 8.0}
HANG_L = {'aL.f': 4.0, 'aL.o': 10.0, 'aL.t': 0.0, 'eL': 14.0, 'eL.t': 0.0, 'wL.f': 10.0, 'fiL': 0.3, 'thL': 0.3}
STIFF = {'aL.f': 0.0, 'aR.f': 0.0, 'aL.o': 6.0, 'aR.o': 6.0, 'eL': 4.0, 'eR': 4.0, 'eL.t': 0.0, 'eR.t': 0.0,
         'wL.f': 0.0, 'wR.f': 0.0, 'kL': 0.0, 'kR': 0.0, 'cL.u': 0.0, 'cR.u': 0.0}
JAB = F.r_ik(F.TIP_IN, F.NEEDLE_D, F.NEEDLE_U, 'LeftForeArm')
EV_INJ = {'SyringeShow': fr(4), 'Inject': fr(40), 'Bliss': fr(55), 'Fall': fr(74), 'Thud': fr(88),
          'SyringeDrop': fr(88)}


def _inject():
    base = lie2_base()
    k = keys(
        (0.0, {'ikR.rel': 'LeftForeArm', 'ikR.orel': 'LeftForeArm', 'ikR.pt': 'tip'}),
        (fr(4), {}),
        (fr(9), add(SOFT, ADMIRE_R, {'hd.p': 12.0, 'hd.w': -14.0, 'hd.r': -8.0})),        # SNAP: syringe out, admire
        (fr(27), {'hd.p': 13.0}),                                                          # hold
        (fr(31), add(F.ARM_OUT_L, {'hd.p': 20.0, 'hd.w': 14.0, 'hd.r': 0.0, 'aR.f': 62.0, 'eR': 118.0})),  # arm out
        (fr(37), {'hd.p': 21.0}),                                                          # hold (aim)
        (fr(40), add(JAB, {'cL.u': 20.0, 'cR.u': 20.0, 'hd.p': -16.0, 'nk.p': -4.0, 'hip.z': -0.005,
                           's2.p': -4.0})),                                                # JAB! jolt
        (fr(42), {'cL.u': 22.0, 'cR.u': 22.0, 'hd.p': -19.0}),
        (fr(52), {'cL.u': 18.0, 'cR.u': 18.0, 'hd.p': -15.0, 'hip.z': -0.012}),           # frozen, eyes popping
        (fr(55), add(HANG_R, HANG_L, {'cL.u': -4.0, 'cR.u': -4.0, 'hd.p': -26.0, 'nk.p': -8.0, 's3.p': -6.0,
                                      's2.p': 0.0, 'hip.z': -0.045, 'ikR.orel': ''})),   # BLISS (snap)
        (fr(72), {'hd.p': -27.0}),                                                         # hold
        (fr(74), add(STIFF, plank(0.0), {'gnd': 0.0, 'lift': 1.0})),                       # goes stiff
        (fr(80), plank(14.0)),
        (fr(84), plank(38.0)),                                                             # falls like a plank
        (fr(87), plank(66.0)),
        (fr(88), add(plank(76.0), {'fiR': 0.0, 'thR': 0.0})),                              # THUD, hand opens
        (fr(91), add(base, {'hd.p': 10.0, 'aL.o': 30.0, 'aR.o': 30.0, 'fL.w': 10.0, 'fR.w': 10.0,
                            'ikL.w': 0.0, 'ikR.w': 0.0})),                                 # bounce
        (fr(96), {'hd.p': -2.0, 'ikL.w': 1.0, 'ikR.w': 1.0, 'aL.o': 75.0, 'aR.o': 75.0, 'fL.w': 32.0,
                  'fR.w': 32.0}),                                                          # flop out
        (INJ_T, base),
    )
    return K.FitTrack(_fill(k, start={}, end=base))


inject_params = _inject()
FACE_INJ = Face([(0.0, {}), (fr(4), {}), (fr(6), {'Happy': 1.0}),                          # syringe out: grin
                 (fr(39), {'Happy': 1.0}), (fr(40), {'Happy': 0.0, 'Surprised': 1.0}),     # JAB: snap
                 (fr(54), {'Surprised': 1.0}), (fr(55), {'Surprised': 0.0, 'Happy': 1.0, 'Blink': 0.5}),  # bliss
                 (fr(87), {'Blink': 0.5}), (fr(88), {'Blink': 1.0}),                       # thud: eyes squeezed
                 (fr(93), {'Blink': 1.0}), (fr(95), {'Blink': 0.6, 'Happy': 0.7})], INJ_T, loop=False)

# ===================================================================================== High_Lie_Loop (3.5 s)
LIE_T = 3.5


def _lie_loop():
    base = lie2_base()
    k = keys(
        (0.0, base),
        (fr(40), {}),
        (fr(43), {'fR.y': 0.16, 'fR.z': 0.10, 'fR.r': -40.0, 'fR.sole': 0.0}),          # TWITCH (body jolt: layer)
        (fr(48), {'fR.y': 0.17, 'fR.z': 0.11}),                                            # hold
        (fr(51), {'fR.y': base['fR.y'], 'fR.z': 0.0, 'fR.r': base['fR.r'], 'fR.sole': 1.0}),  # drop
        (fr(72), {}),
        (fr(80), {'ikL.w': 0.0, 'aL.f': 55.0, 'aL.o': 45.0, 'eL': 25.0, 'fiL': 0.2}),      # left arm floats up...
        (fr(86), {'aL.f': 60.0}),                                                          # hold
        (fr(89), {'ikL.w': 1.0, 'aL.f': 0.0, 'aL.o': 75.0, 'eL': 20.0, 'fiL': 0.35, 'hd.p': 3.0}),  # FLOP
        (fr(92), {'hd.p': 0.0}),
        (LIE_T, base),
    )
    tr = K.FitTrack(_fill(k), periodic=True)

    def params(t):
        p = tr(t)
        p['s2.p'] = p.get('s2.p', 0.0) - 1.6 * math.sin(2 * math.pi * 2 * t / LIE_T) ** 2   # two slow breaths
        j = K.window(t, fr(43), fr(48), fr(3))           # body jolts with the twitch (kept out of the keys so the
        p['hip.r'] = p.get('hip.r', 0.0) + 3.0 * j      # arm IK fit is identical on every key)
        p['hd.p'] = p.get('hd.p', 0.0) - 6.0 * j
        return p
    return params


lie_loop_params = _lie_loop()
FACE_LIE = Face([(0.0, {'Happy': 0.7, 'Blink': 0.6}), (fr(38), {'Blink': 1.0}),           # dozes off
                 (fr(42), {'Blink': 1.0, 'Surprised': 0.0}), (fr(43), {'Blink': 0.1, 'Surprised': 0.6}),  # twitch: snap
                 (fr(52), {'Blink': 0.1, 'Surprised': 0.6}), (fr(55), {'Blink': 0.6, 'Surprised': 0.0}),
                 (fr(88), {}), (fr(89), {'Blink': 1.0}), (fr(92), {'Blink': 0.6})], LIE_T, loop=True)

# ===================================================================================== registry
CONTRACTS = {
    'junkie_walk_v02': {'params': lambda: walk_params(0.0), 'doc': 'Junkie_Walk_v02 frame 1 (left heel down); loop only'},
    'high_lie_v02': {'params': lie2_base, 'setup': [F.floor_setup],
                     'doc': 'flat on the back where the plank fall lands: hips ~0.84 m behind the root, head toward +Y '
                            '(top ~1.8 m behind), feet at the root flopped out, hands palm-up on the floor out at shoulder level'},
}

CLIPS = {
    'Junkie_Walk': {'T': W_T, 'loop': True, 'start': 'junkie_walk_v02', 'end': 'junkie_walk_v02', 'params': walk_params,
                    'activity': 'JunkieWalk', 'role': 'loop', 'run_speed': W_V, 'views': WALK_VIEWS,
                    'props': [('treadmill', {'speed': W_V})], 'face': FACE_WALK,
                    'events': {'FootL': 0.0, 'FootR': W_T / 2, 'SnapAwake': fr(25)},
                    'unity': 'Loop Time on; authored at %.1f m/s, play at ground speed / %.1f' % (W_V, W_V),
                    'beats': ['2 steps, bent knees, toes out, big side-to-side rock onto the standing leg',
                              'arms hang, head lolls a beat behind', '0-0.77 eyes droop shut, head sinks',
                              '0.83 SNAP awake: eyes wide (Surprised), head jerks up, shoulders jolt; hold 6 frames',
                              '1.13 back to droopy']},
    'Inject': {'T': INJ_T, 'loop': False, 'start': 'idle', 'end': 'high_lie_v02', 'params': inject_params,
               'setup': [F.floor_setup], 'views': INJ_VIEWS, 'activity': 'Inject', 'role': 'oneshot', 'face': FACE_INJ,
               'syringe': {'show': EV_INJ['SyringeShow'], 'push': (fr(40), fr(46)), 'drop': EV_INJ['SyringeDrop']},
               'events': EV_INJ, 'feet_free': {'Left': [(fr(86), INJ_T)], 'Right': [(fr(86), INJ_T)]},
               'beats': ['0.13-0.30 SNAP: syringe out, held up, Happy grin; hold', '1.03 left arm out, palm up; hold',
                         '1.33 JAB (event Inject): Surprised snap, shoulders and head jolt; frozen hold',
                         '1.83 BLISS snap: Happy + half Blink, arms drop, head back; hold',
                         '2.47 goes stiff, falls straight back like a plank (accelerating)',
                         '2.93 THUD (events Thud, SyringeDrop): eyes squeezed, bounce, arms and feet flop out',
                         '3.5 high_lie_v02']},
    'High_Lie_Loop': {'T': LIE_T, 'loop': True, 'start': 'high_lie_v02', 'end': 'high_lie_v02', 'params': lie_loop_params,
                      'setup': [F.floor_setup], 'views': LIE2_VIEWS, 'activity': 'HighLie', 'role': 'loop',
                      'face': FACE_LIE, 'syringe': {'floor': True}, 'feet_free': {'Right': [(fr(38), fr(54))]},
                      'beats': ['lies still, dumb half-asleep grin, two slow breaths', '0-1.27 dozes off (eyes close)',
                                '1.43 right leg TWITCH, eyes snap half open; 1.70 drops', '2.4-2.87 left arm floats up',
                                '2.97 FLOP down']},
}

PLACEMENT = {
    'Junkie_Walk': 'in place on a treadmill; authored ground speed %.1f m/s' % W_V,
    'Inject': 'free standing; falls straight back: ends lying behind the root (hips ~0.84 m, head top ~1.8 m behind). '
              'Needs a free 1.0 x 2.2 m strip behind the root. Syringe = separate prop on mixamorig:RightHand '
              '(SyringeShow .. SyringeDrop), then a world prop on the floor',
    'High_Lie_Loop': 'on the floor behind the root (as Inject ends)',
}
