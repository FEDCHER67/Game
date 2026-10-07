"""Sitting and lying clips: BenchSit_Enter/Loop/Exit and BeachLie_Enter/Loop/Exit.

The pelvis height is solved against the support surfaces on the skinned mesh (crowd_core.Rig.contact): the
butt sits exactly on the bench top, the body lies exactly on the towel, never through it. Feet are IK-placed;
planted feet keep their Idle spot unless a beat steps them (crossing the legs on the towel).
Placement contract (character root = feet origin, facing -Y): see BENCH / TOWEL below and the README.
"""
import math
import crowd_core as K
from crowd_core import Track, add, window, smooth
from clips_stand import shift, _fill, keys
from clips_props import zero

# ------------------------------------------------------------------------------------- BenchSit
BENCH = {'seat_top': 0.45, 'front_y': 0.10, 'back_y': 0.52, 'half_width': 0.9, 'backrest_y': 0.54}


def bench_setup(rig):
    b = BENCH
    rig.surfaces = [(b['seat_top'], lambda xs, ys: (ys > b['front_y']) & (ys < b['back_y']) & (abs(xs) < b['half_width'])),
                    (0.0, lambda xs, ys: ys == ys)]


BENCH_PROPS = [('box', {'name': 'Bench_Seat_Review', 'lo': (-0.9, BENCH['front_y'], 0.39), 'hi': (0.9, BENCH['back_y'], 0.45),
                        'rgb': (140, 95, 60)}),
               ('box', {'name': 'Bench_Back_Review', 'lo': (-0.9, BENCH['backrest_y'], 0.62), 'hi': (0.9, BENCH['backrest_y'] + 0.05, 0.95),
                        'rgb': (140, 95, 60)}),
               ('box', {'name': 'Bench_Leg_L', 'lo': (0.7, 0.15, 0.0), 'hi': (0.78, 0.47, 0.39), 'rgb': (60, 60, 64)}),
               ('box', {'name': 'Bench_Leg_R', 'lo': (-0.78, 0.15, 0.0), 'hi': (-0.7, 0.47, 0.39), 'rgb': (60, 60, 64)})]

HANDS_THIGHS = {'ikL.w': 1.0, 'ikL.pt': 'palm', 'ikL.rel': 'Hips', 'ikL.x': 0.135, 'ikL.y': -0.20, 'ikL.z': 0.81,
                'ikR.w': 1.0, 'ikR.pt': 'palm', 'ikR.rel': 'Hips', 'ikR.x': 0.135, 'ikR.y': -0.20, 'ikR.z': 0.81,
                'aL.f': 40, 'aL.o': 4, 'eL': 40, 'eL.t': -10, 'wL.f': -18, 'fiL': 0.3, 'thL': 0.2,
                'aR.f': 40, 'aR.o': 4, 'eR': 40, 'eR.t': -10, 'wR.f': -18, 'fiR': 0.3, 'thR': 0.2}


def sit_base():
    return add(HANDS_THIGHS, {'hip.free': 1.0, 'lift': 1.0, 'gnd': 1.0, 'hip.y': 0.30, 'hip.z': -0.30, 'hip.p': -8,
                              's1.p': 6, 's2.p': 6, 's3.p': 3, 'nk.p': 2, 'hd.p': -2, 'kL': 6, 'kR': 6,
                              'fL.x': 0.02, 'fR.x': 0.02})


SIT_T = 7.0


def _sit_loop():
    T = SIT_T
    base = sit_base()
    stretch = {'ikL.w': 0.0, 'ikR.w': 0.0, 'aL.f': 150, 'aR.f': 150, 'aL.o': 30, 'aR.o': 30, 'eL': 35, 'eR': 35,
               'eL.t': 0, 'eR.t': 0, 'wL.f': 20, 'wR.f': 20, 'fiL': 0.6, 'fiR': 0.6, 'thL': 0.5, 'thR': 0.5,
               's1.p': -4, 's2.p': -10, 's3.p': -10, 'nk.p': -4, 'hd.p': -16, 'cL.u': 14, 'cR.u': 14, 'hip.p': -14}
    scratch = {'ikR.w': 1.0, 'ikR.rel': 'Spine1', 'ikR.pt': 'fist', 'ikR.x': 0.02, 'ikR.y': -0.215, 'ikR.z': 0.93,
               'aR.f': 30, 'aR.o': 6, 'eR': 80, 'eR.t': 0, 'wR.f': 20, 'fiR': 0.55, 'thR': 0.3}
    k = keys(
        (0.0, base),
        (0.55, {'hd.w': 36, 'nk.w': 8, 's3.w': 6, 'hd.p': -4}),                         # look around: left...
        (1.05, {'hd.w': 32, 'hd.r': 4}),
        (1.35, {'hd.w': -30, 'nk.w': -6, 's3.w': -5, 'hd.r': -2}),                      # ...right
        (1.65, {'hd.w': -26}),
        (1.74, {'ikL.w': 0.0, 'ikR.w': 0.0}),                                           # hands leave the thighs
        (2.00, add(stretch, {'hd.w': 0, 'nk.w': 0, 's3.w': 0, 'hd.r': 0})),            # big yawn stretch
        (2.45, {'aL.f': 160, 'aR.f': 158, 'hd.p': -20, 's3.p': -12, 'cL.u': 16, 'cR.u': 16}),
        (2.85, add(HANDS_THIGHS, {'s1.p': 12, 's2.p': 12, 's3.p': 8, 'nk.p': 4, 'hd.p': 6, 'cL.u': -3, 'cR.u': -3,
                                  'hip.p': -6})),                                         # arms flop onto the thighs
        (3.10, {'s1.p': 7, 's2.p': 7, 's3.p': 4, 'hd.p': 0, 'cL.u': 0, 'cR.u': 0, 'hip.p': -8}),
        (4.35, {'hd.p': 3, 'hd.w': -6}),                                                # nervous knee jiggle (layer)
        (4.70, add(scratch, {'hd.p': 14, 'nk.p': 6, 'hd.w': 0})),                       # scratch the belly
        (5.45, {'hd.p': 4, 'nk.p': 2}),
        (5.75, add(HANDS_THIGHS, {'hd.p': -6, 's3.p': -2, 's2.p': 3})),                 # "nu, ladno": knee slap
        (5.95, {'aL.f': 50, 'aR.f': 50, 'ikL.z': 0.86, 'ikR.z': 0.86, 'hd.p': 2}),     # hands up...
        (6.10, {'aL.f': 40, 'aR.f': 40, 'ikL.z': 0.81, 'ikR.z': 0.81, 'hd.p': 6, 's3.p': 5}),   # slap!
        (7.0, base),
    )
    tr = K.FitTrack(_fill(k), periodic=True)

    def params(t):
        p = tr(t)
        # nervous knee jiggle: right heel bounces on the ball (6 Hz), left fingers drum the thigh
        w = window(t, 3.15, 4.2, 0.12)
        p['fR.r'] = p.get('fR.r', 0) + 9.0 * w * (0.5 - 0.5 * math.cos(2 * math.pi * 6.0 * (t - 3.15)))
        for i, f in enumerate(('fiL.i', 'fiL.m', 'fiL.r', 'fiL.k')):
            p[f] = p.get(f, 0) + 0.35 * w * max(0.0, math.sin(2 * math.pi * 4.0 * (t - 3.15) - i * 0.9))
        # belly scratch circles
        w2 = window(t, 4.75, 5.4, 0.1)
        p['ikR.x'] = p.get('ikR.x', 0) + 0.025 * w2 * math.sin(2 * math.pi * 4.5 * (t - 4.75))
        p['ikR.z'] = p.get('ikR.z', 0) + 0.02 * w2 * math.cos(2 * math.pi * 4.5 * (t - 4.75))
        return p
    return params


def _sit_enter():
    base = sit_base()
    reach = {'ikL.w': 1.0, 'ikR.w': 1.0, 'ikL.rel': '', 'ikR.rel': '', 'ikL.pt': 'palm', 'ikR.pt': 'palm',
             'ikL.x': 0.26, 'ikR.x': 0.26, 'ikL.y': 0.24, 'ikR.y': 0.24, 'ikL.z': 0.47, 'ikR.z': 0.47,
             'aL.f': -30, 'aR.f': -30, 'aL.o': 20, 'aR.o': 20, 'eL': 20, 'eR': 20, 'wL.f': -50, 'wR.f': -50,
             'fiL': 0.1, 'fiR': 0.1, 'ikL.floor': 1.0, 'ikR.floor': 1.0}
    k = keys(
        (0.0, {'hip.free': 1.0, 'lift': 1.0, 'ikL.rel': '', 'ikR.rel': '', 'ikL.pt': 'palm', 'ikR.pt': 'palm'}),
        (0.30, {'hd.w': -62, 'nk.w': -14, 's3.w': -16, 's2.w': -9, 'hip.w': -4, 'hd.p': 8, 'hip.z': -0.012}),   # glance back at the bench
        (0.50, {'hd.w': -20, 'nk.w': -4, 's3.w': -4, 's2.w': 0, 'hip.w': 0, 'aL.f': -10, 'aR.f': -10, 'aL.o': 10, 'aR.o': 10}),
        (0.80, add(reach, {'ikL.w': 0.4, 'ikR.w': 0.4, 'hd.w': 0, 'nk.w': 0, 's3.w': 0, 'hip.y': 0.17, 'hip.z': -0.20,
                           'hip.p': 18, 's1.p': 10, 's2.p': 8, 's3.p': 4, 'hd.p': -6, 'kL': 8, 'kR': 8})),  # bend, reach back
        (1.00, {'ikL.w': 1.0, 'ikR.w': 1.0, 'hip.y': 0.27, 'hip.z': -0.27, 'hip.p': 12, 's1.p': 10, 's2.p': 10,
                'gnd': 0.0}),                                                            # hands on the seat, lowering
        (1.12, {'gnd': 1.0, 'hip.y': 0.30, 'hip.z': -0.32, 'hip.p': 0, 's1.p': -2, 's2.p': -4, 's3.p': -4, 'hd.p': -10,
                'cL.u': 6, 'cR.u': 6}),                                                  # plop! head lags back
        (1.26, {'s1.p': 10, 's2.p': 10, 's3.p': 8, 'hd.p': 10, 'cL.u': -3, 'cR.u': -3, 'hip.p': -10}),   # bounce forward
        (1.40, {'ikL.w': 0.0, 'ikR.w': 0.0}),
        (1.47, {'ikL.rel': 'Hips', 'ikR.rel': 'Hips', 'ikL.floor': 0.0, 'ikR.floor': 0.0}),
        (1.78, add(base, {'s1.p': 5, 's2.p': 5, 's3.p': 2, 'hd.p': -4, 'cL.u': 0, 'cR.u': 0, 'kL': 6, 'kR': 6})),
        (2.0, base),
    )
    return K.FitTrack(_fill(k, start={}, end=base))


def _sit_exit():
    base = sit_base()
    knees = {'ikL.x': 0.11, 'ikR.x': 0.11, 'ikL.y': -0.40, 'ikR.y': -0.40, 'ikL.z': 0.72, 'ikR.z': 0.72}
    k = keys(
        (0.0, base),
        (0.25, add(knees, {'s1.p': 22, 's2.p': 16, 's3.p': 8, 'hip.p': 6, 'hd.p': -12, 'nk.p': -4})),  # hands to the knees, lean
        (0.45, {'s1.p': 30, 's2.p': 20, 'hip.p': 14, 'hip.y': 0.26, 'gnd': 0.0, 'hd.p': -16}),          # nose over the toes
        (0.68, {'hip.y': 0.12, 'hip.z': -0.18, 'hip.p': 18, 's1.p': 20, 's2.p': 13, 's3.p': 6, 'hd.p': -10, 'ikL.w': 0.6,
                'ikR.w': 0.6}),                                                          # push up off the knees
        (0.86, {'hip.y': 0.04, 'hip.z': -0.09, 'hip.p': 12, 's1.p': 10, 's2.p': 7, 's3.p': 3, 'hd.p': -4,
                'ikL.w': 0.0, 'ikR.w': 0.0, 'aL.f': 10, 'aR.f': 10, 'eL': 20, 'eR': 20}),   # rising
        (1.12, add(zero(base), {'hip.free': 1.0, 'lift': 1.0, 'hip.y': -0.005, 'hip.z': -0.03, 'hip.p': -6, 's1.p': -4,
                                's2.p': -8, 's3.p': -6, 'hd.p': -8, 'nk.p': -2, 'cL.u': 8, 'cR.u': 8, 'aL.f': -25,
                                'aR.f': -25, 'aL.o': 14, 'aR.o': 14, 'eL': 70, 'eR': 70, 'wL.f': -30, 'wR.f': -30})),  # back stretch
        (1.42, {'hip.z': -0.012, 'hip.p': -3, 's2.p': -4, 's3.p': -3, 'hd.p': -3}),
        (1.70, {'hip.y': 0.0, 'hip.z': 0.0, 'hip.p': 0, 's1.p': 0, 's2.p': 0, 's3.p': 0, 'hd.p': 0, 'nk.p': 0,
                'cL.u': 0, 'cR.u': 0, 'aL.f': 0, 'aR.f': 0, 'aL.o': 0, 'aR.o': 0, 'eL': 0, 'eR': 0, 'wL.f': 0,
                'wR.f': 0}),
    )
    return K.FitTrack(_fill(k, start=base, end={}))


# ------------------------------------------------------------------------------------- BeachLie
TOWEL = {'top': 0.004, 'x': 0.45, 'y0': -0.45, 'y1': 1.75}


def towel_setup(rig):
    rig.surfaces = [(TOWEL['top'], lambda xs, ys: ys == ys)]


BEACH_VIEWS = {'side': ((5.6, 0.55, 0.8), (0.0, 0.55, 0.6), 2.6),
               'three_quarter': ((3.8, -3.4, 2.4), (0.0, 0.45, 0.45), 2.6),
               'front': ((0.0, -5.2, 1.4), (0.0, 0.5, 0.5), 2.6)}
TOWEL_PROPS = [('box', {'name': 'Towel_Review', 'lo': (-TOWEL['x'], TOWEL['y0'], 0.0), 'hi': (TOWEL['x'], TOWEL['y1'], TOWEL['top']),
                        'rgb': (60, 150, 190)})]

HEAD_HANDS = {'ikL.w': 1.0, 'ikR.w': 1.0, 'ikL.rel': 'Head', 'ikR.rel': 'Head', 'ikL.pt': 'palm', 'ikR.pt': 'palm',
              'ikL.x': 0.10, 'ikR.x': 0.10, 'ikL.y': 0.10, 'ikR.y': 0.10, 'ikL.z': 1.47, 'ikR.z': 1.47,
              'aL.f': 150, 'aR.f': 150, 'aL.o': 55, 'aR.o': 55, 'eL': 135, 'eR': 135, 'eL.t': 0, 'eR.t': 0,
              'wL.f': 10, 'wR.f': 10, 'fiL': 0.3, 'fiR': 0.3}
CROSS_R = {'fR.x': -0.265, 'fR.y': 0.066, 'fR.z': 0.349, 'fR.r': -40, 'fR.w': 30, 'kR': 40}   # ankle over the left knee


def lie_base():
    return add(HEAD_HANDS, CROSS_R, {'hip.free': 1.0, 'lift': 1.0, 'gnd': 1.0, 'shin.free': 0.0,
                                     'hip.y': 0.42, 'hip.z': -0.70, 'hip.p': -64, 's1.p': -5, 's2.p': -1, 's3.p': 0,
                                     'nk.p': 8, 'hd.p': 6, 'fL.y': 0.06, 'fL.x': 0.03, 'kL': 6})


LIE_T = 7.0


def _lie_loop():
    T = LIE_T
    base = lie_base()
    swat_R = {'ikR.w': 0.0, 'aR.f': 120, 'aR.o': 30, 'eR': 60, 'eR.t': 60, 'wR.f': 20, 'fiR': 0.1}
    k = keys(
        (0.0, base),
        (1.10, {'hd.w': 26, 'nk.w': 6}),                                                # turns his face to the sun
        (2.20, {'hd.w': 22}),
        (2.55, {'hd.w': -6, 'nk.w': 0}),
        (2.62, {'ikR.w': 0.0}),
        (2.85, add(swat_R, {'hd.w': -14, 'hd.p': 2})),                                 # a fly! swat
        (2.98, {'aR.f': 95, 'eR': 25, 'wR.f': -20, 'hd.w': -18}),                      # swat!
        (3.10, {'aR.f': 112, 'eR': 55, 'wR.f': 10}),
        (3.22, {'aR.f': 90, 'eR': 22, 'wR.f': -25}),                                   # swat again!
        (3.45, add({k_: base[k_] for k_ in ('ikR.w', 'aR.f', 'aR.o', 'eR', 'eR.t', 'wR.f', 'fiR')}, {'hd.w': -4, 'hd.p': 6})),
        (3.75, {'hd.w': 0}),
        (5.30, {'hip.z': -0.70}),                                                       # wiggle settle (layer)
        (6.20, {'hd.w': 8}),
        (7.0, base),
    )
    tr = K.FitTrack(_fill(k), periodic=True)

    def params(t):
        p = tr(t)
        # breathing belly + crossed foot bobbing to music, then a happy wiggle settle
        p['s2.p'] = p.get('s2.p', 0) - 1.6 * math.sin(2 * math.pi * 4 * t / T) ** 2
        w = window(t, 0.4, 2.4, 0.3) + window(t, 3.9, 4.9, 0.3)
        p['fR.r'] = p.get('fR.r', 0) + 12.0 * w * math.sin(2 * math.pi * 2.0 * t)
        p['fR.w'] = p.get('fR.w', 0) + 6.0 * w * math.sin(2 * math.pi * 1.0 * t)
        w2 = window(t, 5.0, 5.9, 0.2)
        p['hip.r'] = p.get('hip.r', 0) + 4.0 * w2 * math.sin(2 * math.pi * 3.0 * (t - 5.0))
        p['s3.r'] = p.get('s3.r', 0) - 3.0 * w2 * math.sin(2 * math.pi * 3.0 * (t - 5.0))
        return p
    return params


def _lie_enter():
    base = lie_base()
    floor_hands = {'ikL.w': 1.0, 'ikR.w': 1.0, 'ikL.rel': '', 'ikR.rel': '', 'ikL.pt': 'palm', 'ikR.pt': 'palm',
                   'ikL.floor': 1.0, 'ikR.floor': 1.0, 'ikL.x': 0.27, 'ikR.x': 0.27, 'ikL.y': 0.62, 'ikR.y': 0.62,
                   'ikL.z': 0.03, 'ikR.z': 0.03, 'aL.f': -40, 'aR.f': -40, 'aL.o': 20, 'aR.o': 20, 'eL': 20, 'eR': 20,
                   'wL.f': -60, 'wR.f': -60, 'fiL': 0.1, 'fiR': 0.1}
    k = keys(
        (0.0, {'hip.free': 1.0, 'lift': 1.0, 'ikL.rel': '', 'ikR.rel': '', 'ikL.pt': 'palm', 'ikR.pt': 'palm'}),
        (0.30, {'hd.p': 16, 'nk.p': 6, 's3.p': 4, 'hip.z': -0.01}),                     # look down at the towel
        (0.75, {'hip.y': 0.10, 'hip.z': -0.40, 'hip.p': 30, 's1.p': 16, 's2.p': 12, 's3.p': 6, 'hd.p': -6, 'nk.p': 0,
                'aL.f': 40, 'aR.f': 40, 'eL': 30, 'eR': 30, 'kL': 14, 'kR': 14, 'fL.r': 8, 'fR.r': 8}),  # squat down
        (1.05, add(floor_hands, {'ikL.w': 0.6, 'ikR.w': 0.6, 'hip.y': 0.30, 'hip.z': -0.62, 'hip.p': -10, 's1.p': 10,
                                 's2.p': 8, 's3.p': 4, 'hd.p': 0, 'fL.r': 0, 'fR.r': 0, 'gnd': 0.0})),   # sit down, hands back
        (1.25, {'ikL.w': 1.0, 'ikR.w': 1.0, 'gnd': 1.0, 'hip.y': 0.36, 'hip.p': -22, 's1.p': 4, 's2.p': 2,
                'hd.p': 4}),                                                               # on the butt: plop
        (1.55, {'hip.p': -34, 's1.p': -2, 's2.p': -2, 'hd.p': 8, 'hd.w': 10}),           # sigh, look at the sky
        (1.66, {'ikL.w': 0.0, 'ikR.w': 0.0}),                                            # hands leave the towel
        (1.85, add(base, {'ikL.w': 0.0, 'ikR.w': 0.0, 'aL.f': 90, 'aR.f': 90, 'aL.o': 40, 'aR.o': 40, 'eL': 90, 'eR': 90,
                          'fR.x': 0.0, 'fR.y': 0.0, 'fR.z': 0.0, 'fR.r': 0, 'fR.w': 0, 'kR': 6, 'hip.p': -60,
                          'hd.w': 0, 'ikL.floor': 0.0, 'ikR.floor': 0.0})),                 # lie back, arms swing up
        (1.95, {'ikL.rel': 'Head', 'ikR.rel': 'Head'}),
        (2.25, add(HEAD_HANDS, {'hip.p': base['hip.p'], 'fR.z': 0.25, 'fR.y': 0.08, 'fR.x': 0.06, 'fR.r': -30}),),  # hands behind the head
        (2.55, add(CROSS_R, {'hd.p': base['hd.p'] + 4})),                                # cross the leg
        (2.90, base),
    )
    return K.FitTrack(_fill(k, start={}, end=base))


def _lie_exit():
    base = lie_base()
    k = keys(
        (0.0, base),
        (0.30, {'fR.x': 0.0, 'fR.y': 0.0, 'fR.z': 0.06, 'fR.r': 0, 'fR.w': 0, 'kR': 6, 'hd.p': 12}),   # uncross
        (0.42, {'fR.z': 0.0, 'ikL.w': 0.0, 'ikR.w': 0.0}),
        (0.62, {'aL.f': 100, 'aR.f': 100, 'aL.o': 20, 'aR.o': 20, 'eL': 60, 'eR': 60,
                'hip.p': -66, 's1.p': -4}),                                              # hands out from behind the head
        (0.85, {'hip.p': -20, 's1.p': 14, 's2.p': 14, 's3.p': 10, 'nk.p': 10, 'hd.p': 10, 'aL.f': 75, 'aR.f': 75,
                'aL.o': 6, 'aR.o': 6, 'eL': 15, 'eR': 15, 'hip.y': 0.34}),                # crunch up, arms forward
        (1.05, {'hip.p': -5, 's1.p': 20, 's2.p': 16, 'hd.p': 2, 'nk.p': 2}),              # rock...
        (1.35, {'gnd': 0.0, 'hip.y': 0.08, 'hip.z': -0.40, 'hip.p': 34, 's1.p': 18, 's2.p': 12, 's3.p': 6,
                'aL.f': 70, 'aR.f': 70, 'kL': 12, 'kR': 12, 'fL.y': 0.0, 'fL.x': 0.0}),  # ...forward into a squat
        (1.85, {'hip.y': 0.0, 'hip.z': -0.06, 'hip.p': 8, 's1.p': 4, 's2.p': 3, 's3.p': 0, 'hd.p': -4, 'aL.f': 10,
                'aR.f': 10, 'aL.o': 4, 'aR.o': 4, 'eL': 20, 'eR': 20, 'kL': 2, 'kR': 2}),   # stand up
        (2.05, {'ikL.rel': 'Hips', 'ikR.rel': 'Hips', 'ikL.pt': 'palm', 'ikR.pt': 'palm', 'ikL.floor': 0.0,
                'ikR.floor': 0.0, 'ikL.x': 0.13, 'ikR.x': 0.13, 'ikL.y': 0.17, 'ikR.y': 0.17, 'ikL.z': 0.72,
                'ikR.z': 0.72, 'hip.z': -0.01, 'hip.p': 0, 'hd.p': 6, 'hd.w': 14}),
        (2.20, {'ikL.w': 1.0, 'ikR.w': 1.0, 'aL.f': -30, 'aR.f': -30, 'eL': 40, 'eR': 40, 'ikL.y': 0.21,
                'ikR.y': 0.21, 'wL.f': -20, 'wR.f': -20}),                               # brush the sand off the butt
        (2.32, {'ikL.y': 0.17, 'ikR.y': 0.17}),
        (2.44, {'ikL.y': 0.22, 'ikR.y': 0.22}),
        (2.58, {'ikL.w': 0.0, 'ikR.w': 0.0, 'hd.w': 0, 'hd.p': -2}),
        (3.00, add(zero(base), {'hip.free': 1.0, 'lift': 1.0, 'ikL.floor': 0.0, 'ikR.floor': 0.0})),
    )
    return K.FitTrack(_fill(k, start=base, end={}))


CONTRACTS = {
    'bench_sit': {'params': sit_base, 'setup': [bench_setup],
                  'doc': 'BenchSit base: sitting on a seat %.2f m high, seat front edge %.2f m behind the root, hands on '
                         'the thighs, feet on their Idle spots' % (BENCH['seat_top'], BENCH['front_y'])},
    'beach_lie': {'params': lie_base, 'setup': [towel_setup],
                  'doc': 'BeachLie base: on the back on a towel behind the root (head toward +Y, hips ~0.4 m behind the '
                         'root), hands behind the head, left knee up, right ankle crossed over the left knee'},
}

CLIPS = {
    'BenchSit_Enter': {'T': 2.0, 'loop': False, 'start': 'idle', 'end': 'bench_sit', 'params': _sit_enter(),
                       'setup': [bench_setup], 'props': BENCH_PROPS, 'activity': 'BenchSit', 'role': 'enter',
                       'events': {'Sit': 1.12},
                       'beats': ['0.3 glance back at the bench', '0.5-1.0 bend, hands reach back onto the seat',
                                 '1.12 plop onto the seat (event Sit), head lags back', '1.26 bounce forward',
                                 '1.4-2.0 hands onto the thighs, settle']},
    'BenchSit_Loop': {'T': SIT_T, 'loop': True, 'start': 'bench_sit', 'end': 'bench_sit', 'params': _sit_loop(),
                      'setup': [bench_setup], 'props': BENCH_PROPS, 'activity': 'BenchSit', 'role': 'loop',
                      'feet_free': {'Right': [(3.0, 4.35)]},
                      'beats': ['0.5-1.7 look around left and right', '1.9-2.6 big yawn stretch, arms overhead',
                                '2.75 arms flop onto the thighs', '3.15-4.2 nervous knee jiggle, fingers drum the thigh',
                                '4.7-5.4 belly scratch', '5.75-6.1 "nu, ladno" knee slap', '7.0 base']},
    'BenchSit_Exit': {'T': 1.7, 'loop': False, 'start': 'bench_sit', 'end': 'idle', 'params': _sit_exit(),
                      'setup': [bench_setup], 'props': BENCH_PROPS, 'activity': 'BenchSit', 'role': 'exit',
                      'beats': ['0.25 hands to the knees, lean', '0.45 nose over the toes', '0.75 push up off the knees',
                                '1.05 back stretch, hands on the lower back', '1.65 Idle']},
    'BeachLie_Enter': {'T': 2.9, 'loop': False, 'start': 'idle', 'end': 'beach_lie', 'params': _lie_enter(),
                       'setup': [towel_setup], 'props': TOWEL_PROPS, 'views': BEACH_VIEWS, 'activity': 'BeachLie', 'role': 'enter',
                       'feet_free': {'Left': [(0.5, 1.1)], 'Right': [(0.5, 2.9)]},
                       'beats': ['0.3 look down at the towel', '0.75 squat', '1.05-1.25 sit down, hands back (plop)',
                                 '1.55 sigh at the sky', '1.85 lie back, arms swing up', '2.25 hands behind the head',
                                 '2.55 cross the leg', '2.9 base']},
    'BeachLie_Loop': {'T': LIE_T, 'loop': True, 'start': 'beach_lie', 'end': 'beach_lie', 'params': _lie_loop(),
                      'setup': [towel_setup], 'props': TOWEL_PROPS, 'views': BEACH_VIEWS, 'activity': 'BeachLie', 'role': 'loop',
                      'feet_free': {'Right': [(0.0, LIE_T)]},
                      'beats': ['breathing belly throughout', '0.4-2.4 crossed foot bobs to music, face turns to the sun',
                                '2.8-3.4 a fly: two swats', '3.9-4.9 foot bobbing again', '5.0-5.9 happy wiggle settle',
                                '7.0 base']},
    'BeachLie_Exit': {'T': 3.0, 'loop': False, 'start': 'beach_lie', 'end': 'idle', 'params': _lie_exit(),
                      'setup': [towel_setup], 'props': TOWEL_PROPS, 'views': BEACH_VIEWS, 'activity': 'BeachLie', 'role': 'exit',
                      'feet_free': {'Right': [(0.0, 0.45)], 'Left': [(1.0, 1.9)]},
                      'beats': ['0.3 uncross the leg', '0.55 hands out from behind the head', '0.85 crunch up',
                                '1.05-1.35 rock forward into a squat', '1.85 stand up',
                                '2.05-2.5 brush the sand off the butt (two pats)', '2.95 Idle']},
}
