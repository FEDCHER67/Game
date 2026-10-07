"""Flee_Panic_Run: in-place panic run with both arms flailing above the head (Fedya: the running guys
shaking their hands above). Authored ground speed RUN_V (GreyboxNpc.FleeSpeed = 4.5 m/s): the ground moves
toward +Y under the character at RUN_V; Unity playback speed = ground speed / RUN_V.

Short cartoon legs churn fast (CYCLE frames per two steps, flight phase between steps), the stance foot lands
on the forefoot and its ball travels backward exactly at ground speed (no skid), the heel kicks up behind,
the knee drives high in front. Upper body: upright-to-slightly-back panic lean, head thrown back, arms up
over the head shaking one shake per step (alternating), floppy wrists and spread fingers, shoulders shrugged.
"""
import math
import crowd_core as K
from crowd_core import Curve

RUN_V = 4.5
CYCLE = 10                     # frames per cycle (two steps): 0.333 s, stride 1.5 m
T_RUN = CYCLE / K.FPS
STANCE = 0.34                  # stance fraction of the cycle per foot
BALL0_Y = -0.10                # Idle ball (toe joint) y
Y_TD = -0.30                   # ball touchdown y (world), in front of the hips
Y_TO = Y_TD + RUN_V * STANCE * T_RUN     # ball lift-off y, behind


def _swing_curves():
    """Swing path of the ball pivot (world y, z), heel roll and toe, phase u = 0..1 from lift-off to touchdown."""
    dur = (1 - STANCE) * T_RUN
    vy = RUN_V * dur            # dy/du of the stance (matching speed at both ends)
    y = Curve([(0.0, Y_TO, vy), (0.18, Y_TO + 0.07), (0.42, 0.18), (0.66, -0.12), (0.86, -0.36), (1.0, Y_TD, vy)])
    z = Curve([(0.0, 0.0, 0.9), (0.20, 0.17), (0.40, 0.27), (0.62, 0.26), (0.84, 0.11), (1.0, 0.0, -0.45)])
    roll = Curve([(0.0, 38.0, 60.0), (0.18, 68.0), (0.42, 62.0), (0.70, 18.0), (0.88, -4.0), (1.0, 8.0, 40.0)])
    tf = Curve([(0.0, 1.0, 'flat'), (0.25, 0.0, 'flat'), (0.75, 0.0, 'flat'), (1.0, 1.0, 'flat')])
    return y, z, roll, tf


SW = _swing_curves()


def foot(phase):
    """(y_ball_world, z, roll, toe_flatten) for one foot at cycle phase 0..1 (0 = touchdown)."""
    if phase < STANCE:
        u = phase / STANCE
        y = Y_TD + RUN_V * phase * T_RUN
        roll = 8.0 + 30.0 * u * u          # forefoot landing, heel rises toward the push-off
        return y, 0.0, roll, 1.0
    u = (phase - STANCE) / (1 - STANCE)
    y, z, roll, tf = (c(u) for c in SW)
    return y, max(z, 0.0), roll, tf


def params(t):
    ph = (t / T_RUN) % 1.0
    p = {'hip.free': 1.0}
    for side, off, sgn in (('L', 0.0, 1), ('R', 0.5, -1)):
        y, z, roll, tf = foot((ph + off) % 1.0)
        p['f%s.y' % side] = y - BALL0_Y
        p['f%s.z' % side] = z
        p['f%s.r' % side] = roll
        p['f%s.tf' % side] = tf
        p['f%s.x' % side] = -0.035          # narrow track (feet under the body)
        p['f%s.w' % side] = 6.0
        p['k' + side] = 8.0
    c2 = 2 * math.pi * 2 * ph               # step rate (two per cycle)
    c1 = 2 * math.pi * ph                   # cycle rate (left/right)
    # bounce: low just after each touchdown, high in the flight
    p['hip.z'] = -0.095 - 0.022 * math.cos(c2 - 2 * math.pi * 0.10)
    p['hip.w'] = -9.0 * math.cos(c1)        # pelvis turns with the forward leg
    p['hip.r'] = 4.0 * math.sin(c1)
    p['hip.p'] = 6.0 + 2.0 * math.cos(c2)
    p['s1.w'] = 4.0 * math.cos(c1)
    p['s2.w'] = 4.0 * math.cos(c1 - 0.4)
    p['s2.p'] = -7.0 - 2.0 * math.cos(c2 - 0.9)
    p['s3.p'] = -6.0
    p['nk.p'] = -4.0
    p['hd.p'] = -12.0 + 4.0 * math.cos(c2 - 1.8)          # head thrown back, bobbing with lag
    p['hd.r'] = 7.0 * math.sin(c1 - 1.0)                     # head wobbles side to side
    p['hd.w'] = 4.0 * math.sin(c1 + 0.6)
    # arms up over the head, shaking: one shake per step, left and right in opposition
    for side, sgn in (('L', 1.0), ('R', -1.0)):
        a = sgn * math.sin(c2)
        lag = sgn * math.sin(c2 - 1.1)
        lag2 = sgn * math.sin(c2 - 2.0)
        p['c%s.u' % side] = 14.0 + 5.0 * a
        p['a%s.f' % side] = 132.0 + 26.0 * a
        p['a%s.o' % side] = 34.0 + 8.0 * lag + 4.0 * math.sin(2 * c1 + sgn)
        p['a%s.t' % side] = 10.0
        p['e' + side] = 38.0 + 26.0 * lag
        p['e%s.t' % side] = 40.0
        p['w%s.f' % side] = 30.0 * lag2                       # floppy hands
        p['w%s.d' % side] = 10.0 * math.sin(c2 - 2.4)
        p['fi' + side] = -0.12 + 0.18 * max(0.0, lag2)
        p['th' + side] = -0.2
    return p


CONTRACTS = {'flee_run': {'params': lambda: params(0.0),
                          'doc': 'Flee_Panic_Run frame 1 (left forefoot touchdown); loop seam only, no transition contract'}}

CLIPS = {
    'Flee_Panic_Run': {'T': T_RUN, 'loop': True, 'start': 'flee_run', 'end': 'flee_run', 'params': params,
                       'activity': 'Flee', 'role': 'loop', 'run_speed': RUN_V,
                       'props': [('treadmill', {'speed': RUN_V})],
                       'events': {'FootL': 0.0, 'FootR': T_RUN / 2},
                       'unity': 'Loop Time on; authored at %.1f m/s, play at ground speed / %.1f' % (RUN_V, RUN_V),
                       'beats': ['frame 1 left forefoot touchdown, frame 6 right', 'flight between the steps',
                                 'heel kicks up behind, knee drives high', 'arms above the head, one shake per step, '
                                 'alternating, floppy wrists', 'head thrown back, wobbling']},
}
