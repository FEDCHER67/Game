"""Standing clips with their own held base pose: SmokeCorner_*, PhoneTalk_*, BarDoor_* (Enter / Loop / Exit).

Each activity has a CONTRACT pose (frame 1 and last frame of the Loop, last frame of the Enter, first frame
of the Exit), keyed with identical raw values, so Enter -> Loop -> ... -> Loop -> Exit chains are exact.
Enter starts and Exit ends on Idle frame 1. No prop meshes are exported: the cigarette and the phone are
implied by the hands (Unity can parent a prop to mixamorig:RightHand if wanted, see README).
"""
import math
import crowd_core as K
from crowd_core import Track, add, window, smooth
from clips_stand import shift, _fill, keys, POINT_R

# ------------------------------------------------------------------------------------- SmokeCorner
MOUTH = (0.02, -0.165, 1.405)            # Idle-space mouth point (right-hand IK, x outward), carried by the Head
CIG_HOLD = {'aR.f': 25, 'aR.o': 5, 'eR': 122, 'eR.t': 60, 'wR.f': -25, 'fiR': 0.0, 'fiR.r': 0.8, 'fiR.k': 0.85,
            'fiR.i': 0.06, 'fiR.m': 0.12, 'thR': 0.3}
ARM_ACROSS_L = {'aL.f': 22, 'aL.o': -6, 'eL': 98, 'eL.t': 30, 'wL.f': 8, 'fiL': 0.5, 'thL': 0.3, 'ikL.w': 1.0,
                'ikL.rel': 'Spine1', 'ikL.pt': 'palm', 'ikL.x': -0.10, 'ikL.y': -0.20, 'ikL.z': 0.99}


def zero(p):
    """All numeric channels of p set to 0 (string channels such as ik targets' frames are kept out)."""
    return {k: 0.0 for k, v in p.items() if not isinstance(v, str)}


def smoke_base():
    return add(shift(0.45), CIG_HOLD, ARM_ACROSS_L, {'hd.p': 2, 'hd.r': -2, 's2.p': 1, 'ikR.w': 0.0, 'ikR.rel': 'Head',
                                                     'ikR.pt': 'pinch', 'ikR.x': MOUTH[0], 'ikR.y': MOUTH[1],
                                                     'ikR.z': MOUTH[2]})


def drag(extra=None):
    d = {'ikR.w': 1.0, 'aR.f': 55, 'aR.o': 10, 'eR': 135, 'eR.t': 70, 'wR.f': -20, 'hd.p': 5, 's3.p': 3}
    d.update(extra or {})
    return d


SM_T = 6.0


def _smoke_loop():
    T = SM_T
    base = smoke_base()
    k = keys(
        (0.0, base),
        (0.25, {'aR.f': 20, 'eR': 116, 'hd.p': 0}),                                     # little dip: anticipation
        (0.55, drag()),                                                                 # cig to the lips
        (0.75, {'s3.p': -3, 'cL.u': 5, 'cR.u': 4, 'hd.p': 2}),                         # draw in...
        (1.20, {'s3.p': -5, 'cL.u': 8, 'cR.u': 7, 'hd.p': 0}),
        (1.42, add(CIG_HOLD, {'ikR.w': 0.0, 'aR.o': 14, 'aR.f': 22, 'hd.p': -14, 'nk.p': -5, 's3.p': -6, 'cL.u': 9,
                              'cR.u': 8})),                                              # hand away, chin up, hold breath
        (1.65, {'hd.p': -16, 'hd.w': -14, 'hd.r': -4}),
        (2.35, {'hd.p': -10, 'hd.w': -24, 'nk.p': -3, 's3.p': 2, 's2.p': 3, 'cL.u': 0, 'cR.u': 0, 'hip.z': -0.008}),  # long exhale aside
        (2.60, {'hd.p': 8, 'hd.w': -8, 'hd.r': -3, 'nk.p': 4, 's2.p': 2, 's3.p': 1, 'aR.o': 10, 'aR.f': 28}),   # look at the ash
        (3.25, {'hd.p': 9, 'hd.w': -6}),
        (3.55, add(shift(-0.35), {'hd.p': 0, 'hd.w': 26, 'nk.w': 6, 's3.w': 6, 'hd.r': 2, 'nk.p': 0, 's2.p': 0, 's3.p': 0,
                                  'hip.z': 0.0, 'aR.o': 5, 'aR.f': 25})),                # weight over, look around
        (4.05, {'hd.w': 34}),
        (4.20, {'hd.p': -9, 'hd.w': 30}),                                               # "sup" chin-up to a passer-by
        (4.38, {'hd.p': 2}),
        (4.70, add(shift(0.45), {'hd.w': 0, 'nk.w': 0, 's3.w': 0, 'hd.p': 2, 'hd.r': -2})),
        (4.95, drag({'hd.p': 6})),                                                      # quick second puff
        (5.20, {'cL.u': 5, 'cR.u': 4, 's3.p': -3}),
        (5.42, add(CIG_HOLD, {'ikR.w': 0.0, 'hd.p': -6, 'cL.u': 2, 'cR.u': 2, 's3.p': -1})),
        (6.0, base),
    )
    tr = K.FitTrack(_fill(k), periodic=True)

    def params(t):
        p = tr(t)
        # ash taps: three thumb flicks with a wrist bob, 2.65-3.3 s
        w = window(t, 2.7, 3.25, 0.08)
        b = math.sin(2 * math.pi * 4.5 * (t - 2.7))
        p['wR.f'] = p.get('wR.f', 0) + 12 * w * b
        p['thR'] = p.get('thR', 0) + 0.45 * w * max(b, 0)
        return p
    return params


def _smoke_enter():
    """Idle -> cup the lighter at the lips, light up, first exhale -> smoke base."""
    base = smoke_base()
    cup_R = drag({'hd.p': 8, 's3.p': 4, 's2.p': 3})
    cup_L = {'ikL.w': 1.0, 'ikL.rel': 'Head', 'ikL.x': 0.06, 'ikL.y': -0.20, 'ikL.z': 1.37, 'ikL.pt': 'palm',
             'aL.f': 60, 'aL.o': 12, 'eL': 125, 'eL.t': 70, 'wL.f': -10, 'fiL': 0.45, 'thL': 0.6}
    k = keys(
        (0.0, {'ikR.rel': 'Head', 'ikR.pt': 'pinch'}),
        (0.20, {'hip.z': -0.006, 'hd.p': 3}),
        (0.50, add(shift(0.3), cup_R, cup_L, {'ikR.x': MOUTH[0], 'ikR.y': MOUTH[1], 'ikR.z': MOUTH[2], 'fiR': 0.0,
                                              'fiR.r': 0.8, 'fiR.k': 0.85, 'thR': 0.3})),   # hands cupped at the lips
        (0.70, {'thL': 0.9, 'hd.p': 10}),                                               # flick the lighter
        (0.82, {'thL': 0.5}),
        (0.95, {'thL': 0.95}),                                                          # second flick: lit
        (1.02, {'ikL.w': 0.0, 'aL.f': 40, 'eL': 110}),
        (1.08, {'ikL.rel': 'Spine1', 'ikL.pt': 'palm'}),
        (1.30, add(ARM_ACROSS_L, {'s3.p': -5, 'cL.u': 7, 'cR.u': 6, 'hd.p': 2})),   # drag, lighter hand away
        (1.50, add(base, {'hd.p': -12, 'hd.w': -16, 'cL.u': 3, 'cR.u': 3, 's3.p': -2})),       # first exhale aside
        (1.90, base),
    )
    return K.FitTrack(_fill(k, start={}, end=base))


def _smoke_exit():
    """Smoke base -> last look, flick the butt away, step on it and twist it out -> Idle."""
    base = smoke_base()
    k = keys(
        (0.0, base),
        (0.25, {'hd.p': 10, 'aR.f': 30, 'aR.o': 12, 'eR': 110}),                       # last look at it
        (0.42, {'aR.f': 42, 'aR.o': 18, 'eR': 128, 'wR.f': -40, 'hd.p': 4}),          # wind-up
        (0.55, {'aR.f': 18, 'aR.o': 24, 'eR': 40, 'eR.t': 20, 'wR.f': 30, 'fiR': 0.0, 'fiR.r': 0.0, 'fiR.k': 0.0,
                'fiR.i': -0.1, 'fiR.m': -0.1, 'thR': 0.0, 'hd.p': 12, 'hd.w': -10}),   # flick!
        (0.80, add(shift(0.9), {'aR.f': 0, 'aR.o': 6, 'eR': 10, 'eR.t': 0, 'wR.f': 0, 'fiR.i': 0, 'fiR.m': 0, 'aL.f': 6, 'ikL.w': 0.0,
                                'aL.o': 4, 'eL': 20, 'eL.t': 0, 'wL.f': 0, 'fiL': 0.1, 'thL': 0.1, 'hd.p': 16,
                                'hd.w': -6, 's2.p': 5, 'fR.z': 0.07, 'fR.y': -0.10, 'fR.x': 0.02, 'fR.r': -8})),  # step onto it
        (0.98, {'fR.z': 0.0, 'fR.r': 0.0, 'fR.y': -0.14, 'fR.x': 0.03}),
        (1.08, {'fR.r': 12, 'fR.wb': 0}),                                               # heel up, twist it out
        (1.24, {'fR.wb': 22}),
        (1.40, {'fR.wb': -16}),
        (1.56, {'fR.wb': 18}),
        (1.70, {'fR.wb': 0, 'fR.r': 0, 'hd.p': 10}),
        (1.92, {'fR.z': 0.06, 'fR.y': -0.06, 'fR.x': 0.01, 'fR.r': 6, 'hd.p': 4}),     # step back to its spot
        (2.10, add(shift(0.2), {'fR.z': 0.0, 'fR.y': 0.0, 'fR.x': 0.0, 'fR.r': 0.0, 'hd.p': 0, 'hd.w': 0, 's2.p': 0,
                                'aL.f': 0, 'aL.o': 0, 'eL': 0, 'fiL': 0, 'thL': 0, 'aR.o': 0, 'eR': 0, 'hd.r': 0})),
        (2.40, zero(base) | {'hip.z': 0.0}),
    )
    return K.FitTrack(_fill(k, start=base, end={}))


# ------------------------------------------------------------------------------------- PhoneTalk
EAR = {'ikR.w': 1.0, 'ikR.rel': 'Head', 'ikR.x': 0.165, 'ikR.y': -0.02, 'ikR.z': 1.46, 'ikR.pt': 'palm',
       'aR.f': 40, 'aR.o': 38, 'eR': 135, 'eR.t': 40, 'wR.f': -10, 'fiR': 0.55, 'thR': 0.7}


def phone_base():
    return add(shift(0.4), EAR, {'hd.r': -7, 'nk.r': -3, 'cR.u': 4, 'hd.p': 2})


PH_T = 7.0


def _phone_loop():
    T = PH_T
    base = phone_base()
    open_L = {'aL.f': 50, 'aL.o': 30, 'eL': 70, 'eL.t': 90, 'wL.f': -25, 'fiL': 0.1, 'thL': 0.05}
    chop_L = {'aL.f': 45, 'aL.o': 12, 'eL': 80, 'eL.t': 20, 'wL.f': 0, 'fiL': 0.05, 'thL': 0.1}
    hip_L = {'aL.o': 45, 'aL.f': -15, 'aL.t': 20, 'eL': 100, 'wL.f': -10, 'ikL.w': 1, 'ikL.rel': 'Hips', 'ikL.x': 0.215,
             'ikL.y': 0.01, 'ikL.z': 0.86, 'ikL.pt': 'fist', 'fiL': 0.7, 'thL': 0.6}
    rest_L = {'aL.f': 0, 'aL.o': 0, 'aL.t': 0, 'eL': 0, 'eL.t': 0, 'wL.f': 0, 'fiL': 0, 'thL': 0, 'ikL.w': 0}
    k = keys(
        (0.0, base),
        (0.25, {'hd.p': 8}), (0.42, {'hd.p': 1}), (0.60, {'hd.p': 8}), (0.78, {'hd.p': 2}),   # "da... da..."
        (0.95, {'hd.p': 3, 's3.p': 2}),
        (1.15, add(shift(0.1), open_L, {'s3.p': -8, 's2.p': -5, 'hd.p': -10, 'nk.p': -4, 'cL.u': 12, 'cR.u': 8,
                                        'hip.y': 0.012})),                                # "CHTO?!" recoil
        (1.45, {'hd.p': -12, 'cL.u': 14, 'aL.o': 34}),
        (1.75, add(chop_L, {'s3.p': 6, 's2.p': 5, 'hd.p': 8, 'nk.p': 4, 'cL.u': 2, 'cR.u': 4, 'hip.y': -0.01})),  # argue
        (1.95, {'aL.f': 30, 'eL': 95, 'hd.p': 12}),                                    # chop
        (2.15, {'aL.f': 48, 'eL': 78, 'hd.p': 6}),
        (2.35, {'aL.f': 28, 'eL': 96, 'hd.p': 12}),                                    # chop
        (2.55, {'aL.f': 50, 'eL': 76, 'hd.p': 5}),
        (2.75, {'aL.f': 26, 'eL': 98, 'hd.p': 13}),                                    # chop
        (3.10, add(shift(0.7), hip_L, {'hip.w': -6, 's2.w': -10, 's3.w': -6, 'hd.w': -8, 's3.p': 1, 's2.p': 1, 'hd.p': 2,
                                       'nk.p': 0, 'hip.y': 0.0})),                       # turn away, hand on hip
        (3.80, {'hd.p': -12, 'hd.r': -10, 'hd.w': -14}),                               # eye-roll at the sky
        (4.20, {'hd.p': -6, 'hd.r': -4, 'hd.w': 4}),
        (4.60, {'hd.p': 2, 'hd.w': 0}),
        (4.90, add(shift(0.3), rest_L, {'hip.w': 0, 's2.w': 0, 's3.w': 0, 's3.p': -6, 'hd.p': -12, 'cL.u': 8, 'cR.u': 6,
                                        'aL.f': 10, 'eL': 30})),                         # laugh
        (5.40, {'s3.p': 6, 's2.p': 6, 'hd.p': 6, 'cL.u': 0, 'cR.u': 4, 'aL.f': 30, 'aL.o': 4, 'eL': 70, 'eL.t': 10,
                'fiL': 0.2, 'hip.z': -0.01}),                                            # hand to the belly, laughing
        (5.90, {'s3.p': 2, 's2.p': 1, 'hd.p': 0, 'aL.f': 6, 'eL': 15, 'eL.t': 0, 'fiL': 0, 'hip.z': 0.0}),
        (6.25, {'hd.p': 7}), (6.45, {'hd.p': 0}),                                      # "ladno, davai"
        (7.0, base),
    )
    tr = K.FitTrack(_fill(k), periodic=True)

    def params(t):
        p = tr(t)
        w = window(t, 5.0, 5.9, 0.12)
        b = math.sin(2 * math.pi * 6.5 * (t - 5.0)) * w
        p['s3.p'] = p.get('s3.p', 0) + 3.0 * b
        p['cL.u'] = p.get('cL.u', 0) + 3.0 * b
        p['hd.p'] = p.get('hd.p', 0) - 2.0 * b
        return p
    return params


POCKET_R = {'ikR.w': 1.0, 'ikR.rel': 'Spine', 'ikR.x': 0.06, 'ikR.y': -0.205, 'ikR.z': 0.90, 'ikR.pt': 'fist',
            'aR.f': 25, 'aR.o': 2, 'eR': 85, 'eR.t': 10, 'wR.f': 5, 'fiR': 0.55, 'thR': 0.5}


def _phone_enter():
    base = phone_base()
    k = keys(
        (0.0, {'ikR.rel': 'Spine', 'ikR.pt': 'fist'}),
        (0.30, add(POCKET_R, {'hd.p': 8, 's2.p': 3, 'hip.z': -0.004})),                # hand into the pocket
        (0.45, {'ikR.z': 0.88}),
        (0.62, {'ikR.w': 0.0, 'aR.f': 60, 'aR.o': 20, 'eR': 110, 'eR.t': 60, 'wR.f': -20, 'fiR': 0.55, 'thR': 0.7,
                'hd.p': 12, 's2.p': 4}),                                                 # phone up, glance at the screen
        (0.70, {'ikR.rel': 'Head', 'ikR.pt': 'palm', 'ikR.x': EAR['ikR.x'], 'ikR.y': EAR['ikR.y'], 'ikR.z': EAR['ikR.z']}),
        (0.95, add(base, {'hd.r': -10, 'cR.u': 7, 'hd.p': 0, 's2.p': 0})),             # to the ear: "allo?"
        (1.30, base),
    )
    return K.FitTrack(_fill(k, start={}, end=base))


def _phone_exit():
    base = phone_base()
    k = keys(
        (0.0, base),
        (0.30, {'ikR.w': 0.0, 'aR.f': 60, 'aR.o': 20, 'eR': 110, 'eR.t': 60, 'wR.f': -20, 'hd.r': -2, 'nk.r': 0,
                'hd.p': 14, 's2.p': 4, 'cR.u': 0}),                                      # look at the screen: hung up?
        (0.50, {'hd.p': 16, 'hd.r': 3}),
        (0.58, {'ikR.rel': 'Spine', 'ikR.pt': 'fist', 'ikR.x': POCKET_R['ikR.x'], 'ikR.y': POCKET_R['ikR.y'],
                'ikR.z': POCKET_R['ikR.z']}),
        (0.80, add(POCKET_R, {'hd.p': 6, 's2.p': 2, 'hd.r': 0})),                       # into the pocket
        (1.10, add(shift(0.0), zero(base) | {'hd.p': -2})),
        (1.40, zero(base) | {'hd.p': 0.0, 's2.p': 0.0}),
    )
    return K.FitTrack(_fill(k, start=base, end={}))


# ------------------------------------------------------------------------------------- BarDoor (leaning on a wall)
WALL_Y = 0.36                 # wall plane behind the character (+Y), metres from the root
POCKET_BOTH = {'ikL.w': 1.0, 'ikL.rel': 'Spine', 'ikL.x': 0.075, 'ikL.y': -0.20, 'ikL.z': 0.90, 'ikL.pt': 'fist',
               'aL.f': 25, 'aL.o': 4, 'eL': 85, 'eL.t': 10, 'fiL': 0.55, 'thL': 0.5,
               'ikR.w': 1.0, 'ikR.rel': 'Spine', 'ikR.x': 0.075, 'ikR.y': -0.20, 'ikR.z': 0.90, 'ikR.pt': 'fist',
               'aR.f': 25, 'aR.o': 4, 'eR': 85, 'eR.t': 10, 'fiR': 0.55, 'thR': 0.5}
FOOT_WALL_R = {'fR.y': 0.445, 'fR.z': 0.26, 'fR.x': 0.03, 'fR.r': 84, 'fR.tf': 0.0, 'fR.t': 10, 'kR': 12}


def lean_base():
    return add(POCKET_BOTH, FOOT_WALL_R, {'hip.y': 0.12, 'hip.p': -9, 'hip.x': 0.035, 'hip.r': -3, 's1.p': -2,
                                          's2.p': 1, 's3.p': 3, 'nk.p': 4, 'hd.p': 5, 'hd.r': -3, 'hd.w': -6,
                                          'wall': 1.0, 'hip.z': -0.02})


def wall_setup(rig):
    rig.wall_y = WALL_Y


BD_T = 7.0


def _lean_loop():
    T = BD_T
    base = lean_base()
    k = keys(
        (0.0, base),
        (1.05, {'hd.w': -26, 'nk.w': -6, 'hd.p': 3}),                                  # watches a passer-by
        (1.30, {'hd.p': -6}),                                                           # "sup" chin-up
        (1.45, {'hd.p': 6}),
        (1.90, {'hd.w': -10, 'nk.w': 0}),
        (2.20, {'hip.z': -0.02, 's3.r': 0, 'cL.u': 0, 'cR.u': 0}),
        (3.60, {'hip.z': -0.02}),                                                       # back scratch on the wall (layer)
        (4.20, {'hd.w': 18, 'nk.w': 6, 'hd.p': 2, 'hd.r': 2}),                         # slow look the other way
        (5.00, {'hd.w': 24, 'hd.r': 4}),
        (5.70, {'hd.w': -4, 'nk.w': 0, 'hd.r': -3, 'hd.p': 5}),
        (7.0, base),
    )
    tr = K.FitTrack(_fill(k), periodic=True)

    def params(t):
        p = tr(t)
        # back scratch against the wall: up-down rub of the hips/back with a happy head roll
        w = window(t, 2.3, 3.5, 0.2)
        rub = math.sin(2 * math.pi * 2.5 * (t - 2.3)) * w
        p['hip.z'] = p.get('hip.z', 0) + 0.018 * rub
        p['s3.r'] = p.get('s3.r', 0) + 3.0 * rub
        p['s2.r'] = p.get('s2.r', 0) - 1.5 * rub
        p['hd.r'] = p.get('hd.r', 0) - 4.0 * rub
        p['hd.p'] = p.get('hd.p', 0) - 6.0 * w
        p['cL.u'] = p.get('cL.u', 0) + 4.0 * w
        p['cR.u'] = p.get('cR.u', 0) + 4.0 * w
        # foot on the wall taps along to some music 5.6-6.6 s (heel knocks the wall)
        w2 = window(t, 5.7, 6.5, 0.12)
        p['fR.y'] = p.get('fR.y', 0) - 0.025 * w2 * (0.5 - 0.5 * math.cos(2 * math.pi * 2.5 * (t - 5.7)))
        p['hd.p'] = p.get('hd.p', 0) + 3.0 * w2 * math.sin(2 * math.pi * 2.5 * (t - 5.7))
        return p
    return params


def _lean_enter():
    base = lean_base()
    k = keys(
        (0.0, {'ikL.rel': 'Spine', 'ikR.rel': 'Spine', 'ikL.pt': 'fist', 'ikR.pt': 'fist', 'fR.tf': 1.0}),
        (0.25, {'hd.w': 30, 'nk.w': 8, 's3.w': 6, 'hip.z': -0.008}),                   # glance back at the wall
        (0.45, {'hd.w': 0, 'nk.w': 0, 's3.w': 0}),
        (0.70, add({'hip.y': 0.10, 'hip.p': -6, 'wall': 1.0, 'hip.z': -0.022, 's3.p': 5, 'nk.p': 6, 'hd.p': 8,
                    'aL.o': 6, 'aR.o': 6})),                                              # flop back onto the wall
        (0.82, {'hd.p': 2, 's3.p': 2, 'hip.z': -0.018}),                                # head bounce
        (0.98, add(shift(0.8), {'hip.y': 0.10, 'fR.z': 0.12, 'fR.y': 0.12, 'fR.r': 30, 'kR': 6}, POCKET_BOTH,
                   {'aL.o': 4, 'aR.o': 4})),                                              # foot up, hands to the pocket
        (1.20, add(base, {'fR.tf': 0.0})),
        (1.50, base),
    )
    return K.FitTrack(_fill(k, start={}, end=base))


def _lean_exit():
    base = lean_base()
    k = keys(
        (0.0, base),
        (0.20, {'hip.z': -0.03, 's3.p': 0, 'hd.p': 2}),                                # gather
        (0.42, add(shift(0.7), {'fR.y': 0.05, 'fR.z': 0.06, 'fR.r': 10, 'fR.t': 0, 'kR': 2, 'hip.y': 0.06,
                                'hip.p': 0, 's3.p': 8, 'hd.p': 10, 'wall': 0.0})),       # push off with the shoulders
        (0.55, {'fR.tf': 1.0}),
        (0.70, add(shift(0.25), {'fR.y': 0.0, 'fR.z': 0.0, 'fR.r': 0.0, 'fR.x': 0.0, 'kR': 0, 'hip.y': -0.012,
                                 'hip.p': 3, 's1.p': 2, 's2.p': 5, 's3.p': 5, 'nk.p': 2, 'hd.p': 4, 'ikL.w': 0, 'ikR.w': 0,
                                 'aL.f': 12, 'aR.f': 12, 'eL': 20, 'eR': 20, 'fiL': 0.1, 'fiR': 0.1, 'thL': 0, 'thR': 0,
                                 'aL.o': 0, 'aR.o': 0, 'eL.t': 0, 'eR.t': 0, 'hd.w': 0, 'hd.r': 0})),   # forward overshoot
        (0.95, {'hip.y': 0.004, 'hip.p': -1, 's1.p': -1, 's2.p': -1, 's3.p': -1, 'hd.p': -2, 'nk.p': 0, 'aL.f': -4,
                'aR.f': -4, 'eL': 4, 'eR': 4, 'fiL': 0, 'fiR': 0}),
        (1.30, zero(base) | {'hip.y': 0.0, 'hip.p': 0.0, 's1.p': 0.0, 'fR.tf': 1.0}),
    )
    return K.FitTrack(_fill(k, start=base, end={}))


CONTRACTS = {
    'smoke': {'params': smoke_base, 'doc': 'SmokeCorner base: weight on the left leg, left forearm across the belly, '
                                           'right hand holds the cigarette at chest height (index+middle straight)'},
    'phone': {'params': phone_base, 'doc': 'PhoneTalk base: right hand (palm) at the right ear, head tilted into it'},
    'lean': {'params': lean_base, 'setup': [wall_setup],
             'doc': 'BarDoor base: back/hood against a wall plane %.2f m behind the root, right sole on the wall, '
                    'hands in the hoodie pocket' % WALL_Y},
}

_WALL_PROP = [('box', {'name': 'Wall_Review', 'lo': (-1.2, WALL_Y, 0.0), 'hi': (1.2, WALL_Y + 0.12, 2.2), 'rgb': (150, 120, 100)})]
CLIPS = {
    'SmokeCorner_Enter': {'T': 1.9, 'loop': False, 'start': 'idle', 'end': 'smoke', 'params': _smoke_enter(),
                          'activity': 'SmokeCorner', 'role': 'enter',
                          'beats': ['0.2-0.5 hands cupped at the lips', '0.7 / 0.95 two lighter flicks',
                                    '1.15 drag, lighter hand away', '1.4 first exhale aside', '1.85 smoke base']},
    'SmokeCorner_Loop': {'T': SM_T, 'loop': True, 'start': 'smoke', 'end': 'smoke', 'params': _smoke_loop(),
                         'activity': 'SmokeCorner', 'role': 'loop',
                         'beats': ['0.25-1.4 drag: dip, cig to the lips, chest fills', '1.4-2.4 chin up, long exhale aside',
                                   '2.6-3.3 look at the ash, three thumb taps', '3.5-4.4 weight over, look around, "sup" chin-up',
                                   '4.9-5.4 quick second puff', '5.4-6.0 back to base']},
    'SmokeCorner_Exit': {'T': 2.4, 'loop': False, 'start': 'smoke', 'end': 'idle', 'params': _smoke_exit(),
                         'activity': 'SmokeCorner', 'role': 'exit', 'events': {'Flick': 0.55, 'Step': 0.98},
                         'feet_free': {'Right': [(0.6, 2.15)]},
                         'beats': ['0.25 last look', '0.42-0.55 wind-up and flick (event Flick)',
                                   '0.6-1.0 step onto the butt (event Step)', '1.08-1.7 heel up, twist it out on the ball',
                                   '1.7-2.1 step back to the Idle spot', '2.4 Idle']},
    'PhoneTalk_Enter': {'T': 1.3, 'loop': False, 'start': 'idle', 'end': 'phone', 'params': _phone_enter(),
                        'activity': 'PhoneTalk', 'role': 'enter',
                        'beats': ['0.3 hand into the hoodie pocket', '0.6 phone up, glance at the screen',
                                  '0.95 to the ear "allo?"', '1.25 phone base']},
    'PhoneTalk_Loop': {'T': PH_T, 'loop': True, 'start': 'phone', 'end': 'phone', 'params': _phone_loop(),
                       'activity': 'PhoneTalk', 'role': 'loop',
                       'beats': ['0.2-0.8 "da... da..." nods', '1.1-1.5 "CHTO?!" recoil, free hand flies open',
                                 '1.7-2.8 argues with three chops', '3.1-4.6 turns away, hand on hip, eye-roll at the sky',
                                 '4.9-5.9 laughs, hand on the belly', '6.2-7.0 "ladno, davai" nod, back to base']},
    'PhoneTalk_Exit': {'T': 1.4, 'loop': False, 'start': 'phone', 'end': 'idle', 'params': _phone_exit(),
                       'activity': 'PhoneTalk', 'role': 'exit',
                       'beats': ['0.3-0.5 phone down, stares at the screen', '0.8 into the pocket', '1.35 Idle']},
    'BarDoor_Enter': {'T': 1.5, 'loop': False, 'start': 'idle', 'end': 'lean', 'params': _lean_enter(),
                      'setup': [wall_setup], 'props': _WALL_PROP, 'activity': 'BarDoor', 'role': 'enter',
                      'feet_free': {'Right': [(0.75, 1.45)]},
                      'beats': ['0.25 glance back at the wall', '0.5-0.7 flops back onto it (head bounce)',
                                '0.95-1.2 right foot up onto the wall, hands into the pocket', '1.45 lean base']},
    'BarDoor_Loop': {'T': BD_T, 'loop': True, 'start': 'lean', 'end': 'lean', 'params': _lean_loop(),
                     'setup': [wall_setup], 'props': _WALL_PROP, 'activity': 'BarDoor', 'role': 'loop',
                     'feet_free': {'Right': [(0.0, BD_T)]},
                     'beats': ['0.6-1.9 watches a passer-by, "sup" chin-up', '2.3-3.5 happy back scratch on the wall',
                               '4.2-5.7 slow look the other way', '5.7-6.5 heel taps the wall to music', '7.0 base']},
    'BarDoor_Exit': {'T': 1.3, 'loop': False, 'start': 'lean', 'end': 'idle', 'params': _lean_exit(),
                     'setup': [wall_setup], 'props': _WALL_PROP, 'activity': 'BarDoor', 'role': 'exit',
                     'feet_free': {'Right': [(0.0, 0.65)]},
                     'beats': ['0.2 gather', '0.42 push off the wall with the shoulders, foot comes down',
                               '0.62 forward overshoot, hands out of the pocket', '0.95-1.3 settle into Idle']},
}
