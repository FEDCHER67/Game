"""Standing crowd clips: ShopQueue_Loop, BusWait_Loop, Chat_Loop (+ Chat_Loop_Mirror), KioskBuy,
SmokeCorner_Enter/Loop/Exit, PhoneTalk_Enter/Loop/Exit.

Feet stay planted on their Idle frame-1 matrices unless a beat lifts a heel or a toe about a fixed
pivot (taps, tiptoes), so nothing slides. Idle-based loops are periodic in every parameter and key
the exact Idle raw values at frame 1 and the last frame.
Parameter conventions: crowd_core docstring (L-side values, mirrored for R).
"""
import math
import crowd_core as K
from crowd_core import Track, add, mix, bump, window, osc, smooth

# ------------------------------------------------------------------------------------- pose snippets


def shift(w, knee=0.0):
    """Weight shift: w > 0 onto the LEFT leg (contrapposto), w < 0 onto the right."""
    return {'hip.x': 0.042 * w, 'hip.r': -3.6 * w, 'hip.w': 2.0 * w, 's1.r': 1.9 * w, 's2.r': 1.5 * w,
            's3.r': 0.6 * w, 'hd.r': -1.2 * w, 'hip.z': -0.004 * abs(w) - knee}


ZERO_ARM = {k: 0.0 for side in 'LR' for k in ('a%s.f' % side, 'a%s.o' % side, 'a%s.t' % side, 'e' + side, 'e%s.t' % side,
                                              'w%s.f' % side, 'w%s.d' % side, 'w%s.t' % side, 'ik%s.w' % side,
                                              'fi' + side, 'th' + side, 'fi%s.i' % side, 'fi%s.m' % side,
                                              'fi%s.r' % side, 'fi%s.k' % side, 'c%s.u' % side, 'c%s.f' % side)}

HAND_HIP_L = {'aL.o': 45, 'aL.f': -15, 'aL.t': 20, 'eL': 100, 'wL.f': -10, 'ikL.w': 1, 'ikL.x': 0.215, 'ikL.y': 0.01,
              'ikL.z': 0.86, 'fiL': 0.7, 'thL': 0.6}
WATCH_L = {'aL.f': 62, 'aL.o': 10, 'eL': 118, 'eL.t': -70, 'wL.f': 5, 'fiL': 0.35, 'thL': 0.2}
POINT_R = {'aR.f': 85, 'aR.o': 10, 'eR': 10, 'fiR': 0.9, 'fiR.i': -0.9, 'thR': 0.8}
SHADE_R = {'aR.f': 85, 'aR.o': 40, 'eR': 120, 'eR.t': 70, 'wR.f': 10, 'wR.d': -10, 'ikR.w': 1, 'ikR.rel': 'Head',
           'ikR.pt': 'palm', 'ikR.x': 0.03, 'ikR.y': -0.24, 'ikR.z': 1.645, 'fiR': 0.1, 'thR': 0.1}   # palm over the brow
SHADE_L = K.mirror_params(SHADE_R)


def side_key(d, side):
    """Rename an L-side snippet to the other side."""
    if side == 'L':
        return dict(d)
    out = {}
    for k, v in d.items():
        h, dot, tail = k.partition('.')
        if h and h[-1] == 'L' and h[:-1] in ('c', 'a', 'e', 'w', 'ik', 'fi', 'th', 'f', 'k'):
            h = h[:-1] + 'R'
        out[h + dot + tail] = v
    return out


def keys(*ks):
    """Cumulative key list: each key is (t, changes[, tan]); channels persist until changed."""
    return list(ks)


# ------------------------------------------------------------------------------------- ShopQueue_Loop
SQ_T = 6.0


def _shopqueue():
    T = SQ_T
    peek = add(shift(-1.0), {'s1.r': -9, 's2.r': -14, 's3.r': -12, 'nk.r': 6, 'hd.r': 14, 'hd.w': -8, 's3.p': 6, 'nk.p': 8,
                             'hd.p': -8, 'fL.r': 16, 'aL.o': 8, 'aL.f': 6, 'eL': 12, 'aR.f': 6, 'eR': 10})
    k = keys(
        (0.0, {}),
        (0.30, {'hip.z': -0.008, 'hd.p': 3, 's3.p': 2}),                                 # tiny dip: here we go
        (0.62, peek),                                                                   # lean out to his right
        (0.80, {'hd.r': 11, 'nk.p': 9, 'hd.p': -10}),
        (1.25, {'hd.w': -14, 'hd.p': -7}),                                              # crane, scan the queue
        (1.40, {'hd.w': -6}),
        (1.62, add(shift(0.35), {'hd.p': 6, 'hd.w': 6, 'hd.r': -4, 'nk.p': 2, 's3.p': 0, 'aL.o': 0, 'aL.f': 0, 'eL': 0, 'nk.r': 0, 'aR.f': 0, 'eR': 0, 'fL.r': 0})),
        (1.80, add(shift(0.15), {'hd.p': -2, 'hd.w': 0, 'hd.r': -1})),
        (2.30, {'cL.u': 13, 'cR.u': 13, 's3.p': -7, 's2.p': -3, 'hd.p': -14, 'nk.p': -4, 'aL.o': 4, 'aR.o': 4}),  # inhale
        (2.48, {'cL.u': 14, 'cR.u': 14, 'hd.p': -16}),
        (2.78, add(shift(0.55), {'cL.u': -6, 'cR.u': -6, 's3.p': 9, 's2.p': 10, 'hd.p': 16, 'nk.p': 7, 'aL.o': 0, 'aR.o': 0,
                                 'aL.f': 6, 'aR.f': 6, 'hip.z': -0.018})),                # big sigh: slump
        (3.10, add(shift(0.75), HAND_HIP_L, {'cL.u': 2, 'cR.u': 0, 's3.p': 1, 's2.p': 2, 'hd.p': 2, 'nk.p': 1, 'aR.f': 0,
                                             'hd.w': 6, 'hd.r': 4})),                     # hand to hip, foot starts
        (4.20, {'hd.w': 3, 'hd.r': -3}),
        (4.45, add(shift(0.6), {'hd.w': 40, 's3.w': 10, 's2.w': 6, 'nk.w': 8, 'hd.p': -3})),  # glare back down the queue
        (4.78, {'hd.w': 46, 'hd.r': 5}),
        (5.05, add(shift(0.25), {'hd.w': 0, 's3.w': 0, 's2.w': 0, 'nk.w': 0, 'hd.p': 3, 'hd.r': -2, 'ikL.w': 0.0,
                                 'aL.o': 12, 'aL.f': 0, 'aL.t': 0, 'eL': 30, 'wL.f': 0, 'fiL': 0.2, 'thL': 0.2, 'cL.u': 0})),
        (5.45, add(shift(-0.08), {'hd.p': -1, 'hd.r': 0, 'aL.o': -2, 'eL': -4, 'fiL': 0, 'thL': 0})),
        (6.0, {}),
    )
    tr = K.FitTrack(_fill(k), periodic=True)
    tap = lambda t: window(t, 3.25, 4.15, 0.12) * (0.5 - 0.5 * math.cos(2 * math.pi * 3.0 * (t - 3.25)))

    def params(t):
        p = tr(t)
        p['fR.r'] = -15.0 * tap(t)                                   # toe taps on the heel (3 Hz)
        p['hd.p'] = p.get('hd.p', 0) + 2.0 * tap(t)                 # head nods with the taps
        p['hd.r'] = p.get('hd.r', 0) + 1.5 * math.sin(2 * math.pi * 1.5 * (t - 3.25)) * window(t, 3.25, 4.15, 0.12)
        return p
    return params


def _fill(ks, start=None, end=None):
    """Turn cumulative changes into full key poses (every key carries every channel seen so far).
    start / end: contract params the first / last key are pinned to exactly (channels not in them = 0)."""
    cur, out = {}, []
    allk = set()
    for k in ks:
        allk |= {c for c, v in k[1].items() if not isinstance(v, str)}
    for k in ks:
        cur.update(k[1])
        full = {c: cur.get(c, 0.0) for c in allk}
        full.update({c: v for c, v in cur.items() if isinstance(v, str)})   # IK frame/point carry over
        out.append((k[0], full) + tuple(k[2:]))
    for idx, pin in ((0, start), (-1, end)):
        if pin is not None:
            allk |= {c for c, v in pin.items() if not isinstance(v, str)}
            full = {c: pin.get(c, 0.0) for c in allk}
            full.update({c: v for c, v in pin.items() if isinstance(v, str)})
            for c, v in out[idx][1].items():       # keep string channels (ik frames) unless the pin sets them
                if isinstance(v, str) and c not in full:
                    full[c] = v
            out[idx] = (out[idx][0], full) + tuple(out[idx][2:])
    if start is not None or end is not None:     # every key must carry every channel
        for i, k in enumerate(out):
            for c in allk:
                k[1].setdefault(c, 0.0)
    return out


# ------------------------------------------------------------------------------------- BusWait_Loop
BW_T = 6.5


def _buswait():
    T = BW_T
    look = {'hd.w': 40, 'nk.w': 12, 's3.w': 14, 's2.w': 10, 's1.w': 5, 'hip.w': 6, 's2.p': 8, 's3.p': 5, 'nk.p': 6, 'hd.p': -6}
    k = keys(
        (0.0, {}),
        (0.30, {'hd.w': -4, 'hip.z': -0.006}),                                           # anticipation: little glance away
        (0.62, add(shift(0.5), look, SHADE_L, {'cL.u': 0})),                             # snap: look up the road, hand to brow
        (0.80, {'hd.w': 44, 'hd.p': -8}),
        (1.00, {'fL.r': 22, 'fR.r': 22, 'hip.z': 0.0, 'hip.x': 0.0, 'hip.r': 0, 'hip.w': 4, 's1.r': 0, 's2.r': 0,
                's3.r': 0, 'hd.r': -3, 'hd.p': -10, 's2.p': 10}),                       # up on tiptoes, peering
        (1.55, {'hd.w': 34, 'hd.r': 2, 'fL.r': 25, 'fR.r': 25}),
        (1.80, {'hd.w': 46, 'hd.r': -4}),                                                # scan... nothing
        (1.94, {'ikL.w': 0.0}),                                                         # hand leaves the brow
        (2.16, {'fL.r': 0, 'fR.r': 0, 'hip.z': -0.022, 's2.p': 12, 's3.p': 10, 'hd.p': 10, 'cL.u': -5, 'cR.u': -5,
                'hd.w': 30, 'aL.f': 20, 'aL.o': 10, 'eL': 40, 'eL.t': 0, 'wL.f': 0, 'fiL': 0.1}),  # drop: huff
        (2.30, add(shift(-0.3), {'hip.z': -0.012, 'hd.w': 6, 'nk.w': 2, 's3.w': 2, 's2.w': 0, 's1.w': 0, 'hip.w': -0.6,
                                 's2.p': 3, 's3.p': 2, 'nk.p': 1, 'hd.p': 3, 'cL.u': 0, 'cR.u': 0, 'aL.f': 0, 'aL.o': 0,
                                 'eL': 0, 'fiL': 0, 'thL': 0})),
        (2.80, {'fL.r': -12, 'fR.r': -12, 'hip.y': 0.02, 's2.p': -2, 'hd.p': -3}),       # rock back on the heels
        (3.20, {'fL.r': 14, 'fR.r': 14, 'hip.y': -0.02, 's2.p': 4, 'hd.p': 3}),          # forward on the toes
        (3.60, {'fL.r': -10, 'fR.r': -10, 'hip.y': 0.015, 's2.p': -2, 'hd.p': -3}),
        (4.00, {'fL.r': 0, 'fR.r': 0, 'hip.y': 0.0, 's2.p': 1, 'hd.p': 1}),
        (4.30, add(shift(-0.5), {'hd.w': -48, 'nk.w': -8, 's3.w': -10, 's2.w': -4, 'hd.p': -4})),   # maybe from there?
        (4.70, {'hd.w': -44, 'hd.r': 4}),
        (5.00, {'hd.w': 10, 'nk.w': 0, 's3.w': 0, 's2.w': 0, 'hd.r': -2}),             # back the other way, sigh
        (5.40, add(shift(0.25), {'hd.w': 2, 'hd.r': 0, 'cL.u': 6, 'cR.u': 6, 'hd.p': -4})),
        (5.80, add(shift(0.0), {'cL.u': 0, 'cR.u': 0, 'hd.p': 2})),
        (6.5, {}),
    )
    tr = K.FitTrack(_fill(k), periodic=True)
    return tr


# ------------------------------------------------------------------------------------- Chat_Loop (+ mirror)
CH_T = 8.0


def _chat():
    """4 s talking (gesturing), then 4 s listening (nods, a laugh with a thigh slap).
    The partner plays Chat_Loop_Mirror offset by half a loop, so one talks while the other listens."""
    T = CH_T
    expl_R = {'aR.f': 50, 'aR.o': 18, 'eR': 75, 'eR.t': 70, 'wR.f': -12, 'fiR': 0.15, 'thR': 0.1}
    expl_L = {'aL.f': 45, 'aL.o': 22, 'eL': 70, 'eL.t': 75, 'wL.f': -10, 'fiL': 0.15, 'thL': 0.1}
    both_open = add(expl_R, expl_L, {'aR.o': 34, 'aL.o': 36, 'eR.t': 95, 'eL.t': 95, 'wR.f': -25, 'wL.f': -25})
    rest_arms = {k: 0.0 for k in set(expl_R) | set(expl_L)}
    k = keys(
        (0.0, {}),
        (0.25, {'s2.p': -3, 'hd.p': -5, 'cL.u': 4, 'cR.u': 4}),                         # inhale to speak
        (0.55, add(shift(-0.4), expl_R, {'s2.p': 6, 's3.p': 4, 'hd.p': 4, 'cL.u': 0, 'cR.u': 0, 'aR.f': 58})),  # "so listen..."
        (0.80, {'aR.f': 40, 'eR': 85, 'wR.f': -2, 'hd.p': 8}),                           # beat
        (1.05, {'aR.f': 56, 'eR': 70, 'wR.f': -16, 'hd.p': 2}),                          # beat
        (1.30, {'aR.f': 42, 'eR': 86, 'wR.f': -2, 'hd.p': 7}),                           # beat
        (1.75, add(shift(0.4), both_open, {'s2.p': -4, 's3.p': -3, 'hd.p': -8, 'hd.r': 8, 'cL.u': 10, 'cR.u': 10})),  # "and THEN!"
        (2.10, {'hd.r': 10, 'cL.u': 12, 'cR.u': 12}),
        (2.40, add(shift(0.2), rest_arms, {'aL.f': 30, 'eL': 60, 'eL.t': 60, 'aR.f': 25, 'eR': 50, 'eR.t': 40,
                                           'hd.r': 0, 'hd.p': 4, 's2.p': 5, 's3.p': 3, 'cL.u': 0, 'cR.u': 0})),
        (2.75, add(POINT_R, {'aR.f': 62, 'eR': 35, 's2.p': 9, 's3.p': 6, 'hd.p': 2, 'hd.w': -4, 'hip.y': -0.015})),  # "you know?"
        (3.10, {'aR.f': 56, 'eR': 42, 'hd.p': 6}),
        (3.35, {'aR.f': 64, 'eR': 32, 'hd.p': 0}),
        (3.80, add(shift(-0.2), rest_arms, {'fiR.i': 0, 'fiR': 0, 'thR': 0, 's2.p': 0, 's3.p': 0, 'hd.p': 0, 'hd.w': 0,
                                            'hip.y': 0, 'aL.f': 0, 'eL': 0, 'eL.t': 0})),
        # listening: hand to chin, nods, then a laugh
        (4.30, add(shift(-0.6), {'aL.f': 55, 'aL.o': 8, 'eL': 128, 'eL.t': 60, 'wL.f': -20, 'fiL': 0.55, 'thL': 0.3,
                                 'ikL.w': 1, 'ikL.x': 0.04, 'ikL.y': -0.17, 'ikL.z': 1.33, 'ikL.pt': 'fist',
                                 'aR.f': 25, 'aR.o': 6, 'eR': 85, 'eR.t': 20, 'fiR': 0.3, 'hd.r': 6, 'hd.p': 4, 'nk.p': 3})),
        (4.65, {'hd.p': 12, 'nk.p': 6}),                                                # mm-hm
        (4.90, {'hd.p': 2, 'nk.p': 2}),
        (5.15, {'hd.p': 13, 'nk.p': 6}),                                                # mm-hm
        (5.45, {'hd.p': 0, 'nk.p': 0, 'hd.r': 4}),
        (5.70, add(shift(0.3), {'ikL.w': 0, 'aL.f': 10, 'aL.o': 10, 'eL': 40, 'eL.t': 0, 'wL.f': 0, 'fiL': 0.2, 'thL': 0.1,
                                's3.p': -10, 's2.p': -8, 'hd.p': -16, 'nk.p': -4, 'cL.u': 8, 'cR.u': 8, 'hd.r': -3,
                                'aR.f': 10, 'aR.o': 10, 'eR': 30, 'eR.t': 0, 'fiR': 0.2})),     # laugh: head thrown back
        (6.15, add(shift(0.5), {'s3.p': 14, 's2.p': 16, 's1.p': 6, 'hd.p': 10, 'nk.p': 6, 'cL.u': -2, 'cR.u': -2,
                                'aR.f': -12, 'aR.o': 14, 'eR': 18, 'hip.z': -0.03, 'hd.r': 3})),  # double over, slap thigh
        (6.55, {'s3.p': 8, 's2.p': 9, 's1.p': 3, 'hd.p': 4, 'aR.f': 0, 'eR': 10}),
        (7.05, add(shift(0.1), {'s3.p': 1, 's2.p': 1, 's1.p': 0, 'hd.p': -2, 'nk.p': 0, 'cL.u': 0, 'cR.u': 0, 'aL.f': 0,
                                'aL.o': 0, 'eL': 0, 'fiL': 0, 'thL': 0, 'aR.f': 0, 'aR.o': 0, 'eR': 0, 'fiR': 0, 'hip.z': -0.006,
                                'hd.r': 0})),
        (7.45, {'hd.p': 1}),
        (8.0, {}),
    )
    tr = K.FitTrack(_fill(k), periodic=True)

    def params(t):
        p = tr(t)
        # laughter: quick chest/shoulder bounces 5.7-6.9 s (zero outside the window)
        w = window(t, 5.8, 6.8, 0.15)
        b = math.sin(2 * math.pi * 7.0 * (t - 5.8)) * w
        p['s3.p'] = p.get('s3.p', 0) + 3.0 * b
        p['cL.u'] = p.get('cL.u', 0) + 3.5 * b
        p['cR.u'] = p.get('cR.u', 0) + 3.5 * b
        p['hd.p'] = p.get('hd.p', 0) - 2.5 * b
        return p
    return params


# ------------------------------------------------------------------------------------- KioskBuy (one-shot)
KB_T = 4.6


def _kiosk():
    """Idle -> lean in, point at the goods, dig in the hoodie pocket, pay, take, tuck, nod, glance away -> Idle.
    The kiosk window is in front (-Y); the counter top is at 1.0 m, its front edge at y = -0.42."""
    pocket_L = {'aL.f': 28, 'aL.o': -2, 'eL': 70, 'eL.t': 10, 'wL.f': 10, 'ikL.w': 1, 'ikL.x': 0.05, 'ikL.y': -0.20,
                'ikL.z': 0.90, 'fiL': 0.5, 'thL': 0.4}
    pay_L = {'ikL.w': 0, 'aL.f': 72, 'aL.o': 6, 'eL': 30, 'eL.t': 60, 'wL.f': -10, 'fiL': 0.55, 'thL': 0.75}
    take_R = {'aR.f': 70, 'aR.o': 8, 'eR': 35, 'eR.t': 70, 'wR.f': -5, 'fiR': 0.15, 'thR': 0.1}
    tuck_R = {'aR.f': 25, 'aR.o': 2, 'eR': 85, 'eR.t': 10, 'wR.f': 5, 'ikR.w': 1, 'ikR.x': 0.05, 'ikR.y': -0.21,
              'ikR.z': 0.92, 'fiR': 0.6, 'thR': 0.5}
    k = keys(
        (0.0, {}),
        (0.30, {'hip.z': -0.01, 'hd.p': 4}),
        (0.70, add(shift(-0.3), {'s1.p': 4, 's2.p': 10, 's3.p': 8, 'nk.p': 5, 'hd.p': -8, 'hip.y': -0.02,
                                 'fL.r': 10})),                                          # lean in, peer at the goods
        (1.05, add(POINT_R, {'aR.f': 80, 'eR': 20, 'hd.p': -4, 'hd.w': -4})),           # "that one"
        (1.25, {'aR.f': 74, 'eR': 26}),                                                 # jab
        (1.40, {'aR.f': 82, 'eR': 18}),                                                 # jab
        (1.75, add(shift(0.4), pocket_L, {'aR.f': 0, 'eR': 0, 'fiR': 0, 'fiR.i': 0, 'thR': 0, 's2.p': 12, 's3.p': 10,
                                          'hd.p': 14, 'hd.w': 6, 'fL.r': 0, 'hip.y': 0, 's1.p': 2})),   # dig in the pocket
        (2.05, {'ikL.z': 0.88, 'ikL.x': 0.07, 'hd.p': 16}),                             # rummage
        (2.25, {'ikL.z': 0.91, 'ikL.x': 0.04}),
        (2.65, add(shift(-0.2), pay_L, {'s2.p': 8, 's3.p': 6, 'hd.p': -2, 'hd.w': 0, 'hip.y': -0.02})),   # pay
        (2.85, {'aL.f': 74}),
        (3.15, add(take_R, {'aL.f': 10, 'aL.o': 4, 'eL': 20, 'eL.t': 0, 'wL.f': 0, 'fiL': 0.1, 'thL': 0.1})),  # take it
        (3.35, {'fiR': 0.6, 'thR': 0.6}),                                               # grab
        (3.75, add(shift(0.3), tuck_R, {'s2.p': 2, 's3.p': 0, 'hd.p': 6, 'hd.r': 5, 'hip.y': 0, 'aL.f': 0, 'aL.o': 0,
                                        'eL': 0, 'fiL': 0, 'thL': 0})),                  # tuck into the pocket, happy
        (3.88, {'hd.p': -8, 'hip.z': 0.0, 'hd.r': 4, 'fL.r': 14, 'fR.r': 14, 'cL.u': 6, 'cR.u': 6}),  # happy hop onto the toes
        (4.02, {'fL.r': 0, 'fR.r': 0, 'hip.z': -0.012, 'hd.p': 4, 'cL.u': 0, 'cR.u': 0}),
        (4.12, {'fL.r': 9, 'fR.r': 9, 'hip.z': 0.0, 'hd.p': -3}),                      # second little bounce
        (4.30, add(shift(0.0), {'fL.r': 0, 'fR.r': 0, 'ikR.w': 0, 'aR.f': 0, 'aR.o': 0, 'eR': 0, 'eR.t': 0, 'wR.f': 0, 'fiR': 0, 'thR': 0,
                                's2.p': 0, 'hd.p': 0, 'hd.r': 0, 'hd.w': -12, 'nk.w': -4})),     # glance where he goes
        (4.6, {'hd.w': 0, 'nk.w': 0}),
    )
    return K.FitTrack(_fill(k, start={}, end={}))


CLIPS = {
    'ShopQueue_Loop': {'T': SQ_T, 'loop': True, 'start': 'idle', 'end': 'idle', 'params': _shopqueue(),
                       'activity': 'ShopQueue', 'role': 'loop',
                       'events': {'Tap': [3.25 + i / 3.0 for i in range(3)]},
                       'beats': ['0.3-0.8 lean out to his right to peek past the queue', '0.8-1.5 crane and scan',
                                 '1.5-1.8 snap back', '1.8-2.8 big impatient sigh (shrug up, head back, slump)',
                                 '2.9-4.2 hand on hip, right toe taps x3 with head nods', '4.3-5.0 glare back down the queue',
                                 '5.0-6.0 hand drops, settle into Idle']},
    'BusWait_Loop': {'T': BW_T, 'loop': True, 'start': 'idle', 'end': 'idle', 'params': _buswait(),
                     'activity': 'BusWait', 'role': 'loop',
                     'feet_heel_toe': True,
                     'beats': ['0.3-0.8 snap look up the road (his left), left hand shading the eyes',
                               '0.8-1.8 up on tiptoes, peering, scanning', '1.8-2.3 drops down with a huff',
                               '2.6-4.0 bored heel-toe rocking', '4.2-4.9 maybe it comes from the right?',
                               '4.9-6.5 back, shrug-sigh, settle into Idle']},
    'Chat_Loop': {'T': CH_T, 'loop': True, 'start': 'idle', 'end': 'idle', 'params': _chat(),
                  'activity': 'Chat', 'role': 'loop', 'partner': ('Chat_Loop_Mirror', CH_T / 2, ((0.0, -1.15, 0.0), 180.0)),
                  'views': {'side': ((5.6, -0.575, 1.0), (0.0, -0.575, 0.9), 2.9),
                            'three_quarter': ((5.0, -2.6, 1.9), (0.0, -0.575, 0.88), 2.9),
                            'front': ((-5.0, -2.6, 1.9), (0.0, -0.575, 0.88), 2.9)},
                  'beats': ['0.0-0.5 inhale to speak', '0.5-1.4 explaining with right-hand beats',
                            '1.6-2.3 both hands open "and THEN!"', '2.6-3.5 point "you know?"', '3.8-4.2 drop arms',
                            '4.2-5.5 listen: hand to chin, two nods', '5.6-6.9 laugh: head back, double over, thigh slap',
                            '7.0-8.0 settle into Idle']},
    'KioskBuy': {'T': KB_T, 'loop': False, 'start': 'idle', 'end': 'idle', 'params': _kiosk(),
                 'activity': 'Kiosk', 'role': 'oneshot',
                 'events': {'Pay': 2.70, 'Take': 3.30},
                 'props': [('box', {'name': 'Kiosk_Counter_Review', 'lo': (-0.8, -0.85, 0.94), 'hi': (0.8, -0.42, 1.0),
                                    'rgb': (90, 120, 150)})],
                 'beats': ['0.3-0.7 lean in and peer at the goods', '0.9-1.4 point "that one" with two jabs',
                           '1.6-2.4 dig in the hoodie pocket (rummage)', '2.5-2.9 hand the money over (event Pay)',
                           '3.0-3.4 take the item (event Take)', '3.5-4.2 tuck it in the pocket, happy double bounce on the toes',
                           '4.0-4.6 glance where he goes next, end in Idle']},
}
CLIPS['Chat_Loop_Mirror'] = dict(CLIPS['Chat_Loop'], params=(lambda f: (lambda t: K.mirror_params(f(t))))(CLIPS['Chat_Loop']['params']),
                                 role='loop_mirror', partner=('Chat_Loop', CH_T / 2, ((0.0, -1.15, 0.0), 180.0)))
