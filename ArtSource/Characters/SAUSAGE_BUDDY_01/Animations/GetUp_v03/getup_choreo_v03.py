"""Choreography for GetUp_FromBack_v03 / GetUp_FromBelly_v03 (Sausage Buddy).

STATUS (cloud pass 2026-10-07): both performances are authored in make_back()/make_belly() following the
beat sheets below (the measured Stable is back f67.25 = 0.80, belly f61 = 0.73; see README.md), reviewed in
three render passes and validated (validation_v03.json). READY = True. The beat sheets keep the planning text;
the keyed timings are in make_back()/make_belly().

Channel reference (all angles in degrees, positions in metres, frames are 0-based clip frames, 30 fps):
  hips_pos (x,y,z) | hips_pitch (+ = forward; -90 supine, +90 prone) | hips_lean (+ = toward char. left)
  hips_twist (+ = turn/roll toward char. left, about the body's long axis) | hips_yaw (world, about +Z)
  spine / chest / neck / head: (bend + forward, side + left, twist + left); spine is spread 30/34/36 %
  clavL / clavR: (shrug + up, forward + forward)
  armL / armR FK: (fwd = shoulder flexion from hanging, out = abduction from hanging, twist); Idle = (4,16,0)
  elbowL / elbowR FK flexion (Idle 14) | wristL / wristR (bend, side, twist)
  ikL / ikR: 0 = FK arm, 1 = IK hand; handL/handR (x, y, h) with h = height of the hand's lowest point
  above z=0 for the orientation handQL/handQR (world delta from rest; RZ(-90)/RZ(+90) = palm down,
  fingers toward -Y); poleL/poleR = where the elbow points (world)
  footL / footR (x, y, h): h = height of the shoe's lowest point above z=0 for orientation footQL/footQR
  kneeL / kneeR: where the knee points (world)
  handOnKneeL/R weight + handKneeSideL/R ('Left'/'Right') + handKneeOffL/R: hand target follows a knee
  ground (0..1) + ground_set (regions): hips height solved so those regions touch z=0
"""
import sys
sys.dont_write_bytecode = True
from mathutils import Vector, Euler
import getup_lib_v03 as L
import math
from getup_lib_v03 import Track, QTrack, Step, RX, RY, RZ, P, window

READY = True  # performances authored and reviewed (cloud v03 pass, 2026-10-07)

# ------------------------------------------------------------------------------------------- beat sheets
# Planned by the v03 animator (not yet keyed). Frames are 0-based; the clip's last frame is Idle frame 1.
BEATS_BACK = {  # N = 84 frames -> 2.8 s; Blender frames 1..85
    'N': 84,
    'beats': [
        (0, 5, 'HOLD supine start (ragdoll blend target). Head tipped back on the hood, turned left; '
               'palms down beside the hips; legs relaxed, toes up and out.'),
        (5, 14, 'GROGGY HEAD LIFT: neck flexes, head peels off the floor and looks at the feet ("huh?"), '
                'slow with a small lateral bobble; left knee twitches up a little.'),
        (14, 17, 'ANTICIPATION: head drops back a touch, hands leave the floor (IK->FK), shoulders load.'),
        (17, 24, 'SIT-UP SNAP: pelvis -90 -> -8, spine curls to 45 (overshoot over the legs), arms thrown '
                 'forward toward the feet; heels pop up 5-6 cm (counterweight) and slap down at f22; '
                 'head lags then whips forward.'),
        (24, 30, 'SETTLE to a slumped sit; hands land on the thighs (IK on the thigh tops).'),
        (30, 46, 'DIZZY CIRCLE: neck/head/upper spine trace one slow circle (~2 Hz, 14 deg neck, 6 deg spine '
                 'with phase lag); arms ride limp on the thighs.'),
        (42, 51, 'BRR SHAKE: head twist +-30 deg at 5 Hz decaying, neck side +-8, spine twist counter-shakes '
                 'with lag, shoulders shrug up during the shake ("shaking off the stars").'),
        (48, 56, 'GATHER: feet slide to y=-0.27 (soles flatten, knees up), hands plant behind the hips '
                 '(fingers out/back), torso leans back onto the arms (pelvis -32).'),
        (56, 64, 'ROCK-UP: push off the hands, rock forward over the feet into a deep squat (hips to '
                 'y=-0.17, z=0.33, pelvis +38), arms swing forward for momentum, head lags.'),
        (63, 71, 'RISE to standing too fast (hips to y=-0.22, z=0.80); head comes up last.'),
        (70, 77, 'HEAD-RUSH STAGGER BACK: body keeps tipping back (spine -10, head thrown back), arms '
                 'windmill (one circle per ~9 frames, keep < 25 deg per half frame), RIGHT foot steps back '
                 'to its Idle spot (y 0), hips drop to absorb.'),
        (76, 84, 'RECOVER: LEFT foot steps back to Idle, hips return to (0,0), small head wobble, arms drop, '
                 'settle exactly into Idle frame 1. Stable ~f71 (0.85) or earlier once upright.'),
    ],
}
BEATS_BELLY = {  # N = 84 frames -> 2.8 s
    'N': 84,
    'beats': [
        (0, 6, 'HOLD prone start: head turned left, right cheek on the floor; hands beside the chest '
               '(push-up hands), elbows up/back; legs straight, shoe tops on the floor.'),
        (6, 16, 'PUSH 1 (noodle arms): chest rises, arms tremble (8-10 Hz torso bob +-1 cm drives the IK '
                'elbows), head hangs, face still near the floor.'),
        (16, 19, 'ARMS BUCKLE: chest flops back down halfway (3 frames), head nearly bonks.'),
        (19, 30, 'PUSH 2 + PUSH BACK: determined push, hips shift back over the knees (hips 0 -> y +0.30), '
                 'knees slide under -> all fours (knees ~y +0.30, hands stay at y -0.15).'),
        (30, 46, 'ALL-FOURS DIZZY: head hangs low, one slow circle, then a whole-body WET-DOG SHAKE '
                 '(head leads, spine side/twist follows with lag, ~5 Hz, 2.5 cycles).'),
        (46, 57, 'KNEEL UP + HALF-KNEEL: hands push off, torso swings up to kneeling; RIGHT foot swings '
                 'forward to its Idle spot (y ~0); both hands go onto the right knee (handOnKnee).'),
        (57, 67, 'STAND: push on the knee, hips forward/up to (0,0,~0.8); LEFT foot swings forward from '
                 'behind to its Idle spot; head comes up last.'),
        (66, 78, 'FORWARD TEETER (in place, no steps): head rush tips him forward onto the toes '
                 '(heels up ~4 cm), arms windmill, then he rocks back onto the heels (toes up slightly).'),
        (78, 84, 'SETTLE into Idle frame 1. Stable ~f63 (0.75).'),
    ],
}


# ------------------------------------------------------------------------------------------- start poses
def _lying_foot(pitch_body, toe_out, plantar):
    """World foot orientation for a lying body: lay down (pitch_body), toe-out about the leg axis, plantarflex."""
    return RX(pitch_body) @ RZ(toe_out) @ RX(plantar)


def start_back():
    """Supine, head toward +Y, feet toward -Y. The hood (0.17 m bulge behind Spine2) works as a pillow:
    the pelvis is tilted (pitch -67) so butt AND hood touch the floor; the head rests back on the hood.
    (Pitch -90 floats the butt 9-15 cm, which is why GPT's v02 hipsStart was 0.307 m.)"""
    return {
        'hips_pos': (0.0, 0.0, 0.15), 'hips_pitch': -67.0, 'hips_lean': 0.0, 'hips_twist': 4.0, 'hips_yaw': 0.0,
        'spine': (0.0, 0.0, 0.0), 'chest': (0.0, 0.0, 0.0),
        'neck': (-28.0, 0.0, 0.0), 'head': (-14.0, 4.0, 22.0),
        'clavL': (0.0, 0.0), 'clavR': (0.0, 0.0),
        'ikL': 1.0, 'ikR': 1.0, 'plantL': 1.0, 'plantR': 1.0,
        # h = 8 mm: rigid palm points sit 8 mm up so the mixed-weight wrist/cuff vertices clear the floor.
        'handL': (0.31, 0.04, 0.008), 'handR': (-0.31, 0.06, 0.008),
        'handQL': RZ(-90) @ RY(0), 'handQR': RZ(90) @ RY(0),
        'poleL': (1.0, 0.2, 0.6), 'poleR': (-1.0, 0.2, 0.6),
        'footL': (0.16, -0.66, 0.0), 'footR': (-0.15, -0.67, 0.0),
        'footQL': _lying_foot(-90, 28, 30), 'footQR': _lying_foot(-90, -22, 28),
        'kneeL': (0.35, 0.0, 1.0), 'kneeR': (-0.30, 0.0, 1.0),
        'ground': 1.0, 'ground_set': ('torso',),
    }


def start_belly():
    """Prone, head toward -Y, feet toward +Y. Right cheek on the floor, push-up hands beside the chest."""
    return {
        'hips_pos': (0.0, 0.0, 0.17), 'hips_pitch': 90.0, 'hips_lean': 0.0, 'hips_twist': -3.0, 'hips_yaw': 0.0,
        'spine': (-9.0, 0.0, 0.0), 'chest': (0.0, 0.0, 0.0),
        # neck bend 10 -> 14 (v03 fix): the cheek now rests on the floor (was floating 2.8 cm).
        'neck': (14.0, -6.0, 30.0), 'head': (6.0, -8.0, 48.0),
        'clavL': (6.0, 0.0), 'clavR': (6.0, 0.0),
        'ikL': 1.0, 'ikR': 1.0, 'plantL': 1.0, 'plantR': 1.0,
        'handL': (0.30, -0.17, 0.008), 'handR': (-0.30, -0.17, 0.008),
        'handQL': RZ(-90 + 15), 'handQR': RZ(90 - 15),
        'poleL': (0.8, 0.5, 0.7), 'poleR': (-0.8, 0.5, 0.7),
        'footL': (0.13, 0.675, 0.0), 'footR': (-0.12, 0.68, 0.0),
        'footQL': _lying_foot(90, -12, 62), 'footQR': _lying_foot(90, 10, 58),
        'kneeL': (0.25, 0.0, -1.0), 'kneeR': (-0.25, 0.0, -1.0),
        'ground': 1.0, 'ground_set': ('torso',),
    }


# ------------------------------------------------------------------------------------------- authoring helpers
class E:
    """Key value with tension (1 = forced ease at this key: a hold/settle; 0 = automatic monotone tangent)."""

    def __init__(self, v, t=1.0):
        self.v, self.t = v, t


class Keys:
    """Pose-to-pose keys per channel. at(frame, **channels) adds keys only for the channels given, so
    overlap/lag is authored by keying related channels on different frames."""

    def __init__(self):
        self.k = {}

    def at(self, f, **chans):
        for c, v in chans.items():
            self.k.setdefault(c, []).append((float(f), v))
        return self

    def pose(self, f, pose, only=None, skip=()):
        for c, v in pose.items():
            if (only is None or c in only) and c not in skip:
                self.k.setdefault(c, []).append((float(f), v))
        return self

    def tracks(self):
        out = {}
        for c, keys in self.k.items():
            byf = {}
            for f, v in keys:  # a later key on the same frame replaces the earlier one
                byf[f] = v
            keys = sorted(byf.items(), key=lambda kv: kv[0])
            ks = []
            for f, v in keys:
                t = 0.0
                if isinstance(v, E):
                    v, t = v.v, v.t
                ks.append((f, v, t))
            if c == 'ground_set' or isinstance(ks[0][1], str):
                out[c] = Step([(f, v) for f, v, _ in ks])
            elif hasattr(ks[0][1], 'slerp'):
                out[c] = QTrack(ks)
            else:
                out[c] = Track(ks)
        return out


def osc(f, f0, f1, period, attack=3.0, decay=4.0, phase=0.0):
    """Windowed sine (cycles from f0), C1 at the window edges."""
    return window(f, f0, f1, attack, decay) * math.sin(2 * math.pi * ((f - f0) / period + phase))


def _eq(x, y, z):
    """World hand orientation (delta from rest) from XYZ Euler degrees; used to match an FK hand to an IK contact."""
    return Euler((math.radians(x), math.radians(y), math.radians(z)), 'XYZ').to_quaternion()


def _hold_tracks(pose, f0=0, f1=6):
    k = Keys()
    k.pose(f0, pose).pose(f1, pose)
    return k.tracks()


# ------------------------------------------------------------------------------------------- FromBack
def thigh_hand(side, k_side, off):
    """IK hand resting on a thigh just above the knee (handOnKnee)."""
    return {'handOnKnee' + side: 1.0, 'handKneeSide' + side: k_side, 'handKneeOff' + side: off}


def make_back(rig):
    N = BEATS_BACK['N']
    s0 = start_back()
    idle = rig.idle_params()
    k = Keys()
    k.pose(0, s0).pose(5, s0)
    k.pose(N, idle, skip=('ground_set',))
    k.at(N, plantL=0.0, plantR=0.0, handOnKneeL=0.0, handOnKneeR=0.0)
    standQL, standQR = idle['footQL'], idle['footQR']

    # --- hips / ground ------------------------------------------------------------------------------
    k.at(12, hips_pitch=-66.0, hips_twist=2.0)
    k.at(16, hips_pitch=E(-68.0))
    k.at(19, hips_pitch=-52.0)
    k.at(22, hips_pitch=-12.0)
    k.at(24, hips_pitch=-3.0, hips_twist=0.0)
    k.at(28, hips_pitch=-10.0)
    k.at(46, hips_pitch=-9.0, hips_lean=0.0)
    k.at(51, hips_pitch=-18.0)
    k.at(55, hips_pitch=E(-30.0), hips_lean=-3.0)
    k.at(58, hips_pitch=-18.0)
    k.at(62, hips_pitch=30.0, hips_lean=2.0)
    k.at(64.5, hips_pitch=E(38.0))
    k.at(69, hips_pitch=8.0)
    k.at(72, hips_pitch=-9.0, hips_lean=-2.0, hips_yaw=-4.0)
    k.at(76, hips_pitch=-3.0, hips_lean=1.5, hips_yaw=3.0)
    k.at(80, hips_pitch=2.0, hips_lean=0.0, hips_yaw=0.0)
    k.at(57, ground=1.0)
    k.at(61, ground=0.0)
    k.at(0, ground_set=('torso',))
    k.at(5, hips_pos=(0.0, 0.0, 0.15))
    k.at(57, hips_pos=(0.0, 0.0, 0.12))
    k.at(60, hips_pos=(0.0, -0.10, 0.22))
    k.at(64.5, hips_pos=E((0.0, -0.17, 0.33)))
    k.at(69, hips_pos=(0.0, -0.24, 0.79))
    k.at(72, hips_pos=(0.0, -0.15, 0.755))
    k.at(76, hips_pos=(0.0, -0.07, 0.77))
    k.at(80, hips_pos=(0.0, -0.01, 0.805))

    # --- spine / neck / head ------------------------------------------------------------------------
    k.at(12, spine=(4.0, 0.0, 0.0))
    k.at(16, spine=(1.0, 0.0, 0.0))
    k.at(19, spine=(18.0, 0.0, 0.0))
    k.at(22.5, spine=(44.0, 0.0, 0.0))
    k.at(25, spine=(40.0, 3.0, 0.0))
    k.at(29, spine=(30.0, 4.0, -3.0))
    k.at(47, spine=(30.0, 2.0, 0.0))
    k.at(52, spine=(18.0, 0.0, 0.0))
    k.at(55, spine=(6.0, 0.0, 0.0))
    k.at(59, spine=(24.0, 0.0, 0.0))
    k.at(64, spine=(34.0, 0.0, 0.0))
    k.at(68, spine=(18.0, 0.0, 0.0))
    k.at(70.5, spine=(4.0, 0.0, 2.0))
    k.at(73.5, spine=(-12.0, -2.0, 4.0))
    k.at(77, spine=(-3.0, 1.0, -2.0))
    k.at(80.5, spine=(3.0, 0.0, 0.0))

    k.at(13, neck=(34.0, 3.0, -4.0), head=(14.0, -8.0, 0.0))
    k.at(16, neck=(20.0, 0.0, 0.0), head=(8.0, -2.0, 0.0))
    k.at(19.5, neck=(-14.0, 0.0, 0.0), head=(-10.0, 0.0, 0.0))
    k.at(23.5, neck=(38.0, 0.0, 0.0), head=(22.0, 0.0, 0.0))
    k.at(27, neck=(12.0, 0.0, 0.0), head=(6.0, 4.0, 0.0))
    k.at(47, neck=(10.0, 0.0, 0.0), head=(4.0, 0.0, 0.0))
    k.at(55, neck=(16.0, 0.0, 0.0), head=(8.0, 0.0, 0.0))
    k.at(60, neck=(-6.0, 0.0, 0.0), head=(-8.0, 0.0, 0.0))
    k.at(64.5, neck=(-30.0, 0.0, 0.0), head=(-18.0, 0.0, 0.0))
    k.at(69, neck=(18.0, 0.0, 0.0), head=(12.0, 0.0, 0.0))
    k.at(71, neck=(8.0, 0.0, 0.0), head=(2.0, 0.0, 0.0))
    k.at(74, neck=(-18.0, -4.0, 0.0), head=(-14.0, 0.0, 4.0))
    k.at(77.5, neck=(10.0, 3.0, 0.0), head=(6.0, 2.0, -3.0))
    k.at(80.5, neck=(-4.0, 0.0, 0.0), head=(-2.0, 0.0, 0.0))

    # --- arms -----------------------------------------------------------------------------------------
    k.at(11, ikL=1.0, ikR=1.0, plantL=1.0, plantR=1.0, handL=(0.28, 0.10, 0.008), handR=(-0.28, 0.11, 0.008))
    k.at(14, plantL=0.0, plantR=0.0)
    k.at(17.5, ikL=0.0, ikR=0.0)
    for t in 'LR':
        k.at(5, **{'arm' + t: (8.0, 20.0, 0.0), 'elbow' + t: 12.0})
        k.at(16, **{'arm' + t: (24.0, 22.0, 0.0), 'elbow' + t: 34.0, 'clav' + t: (8.0, -4.0)})
        k.at(20, **{'arm' + t: (100.0, 18.0, 0.0), 'elbow' + t: 20.0})
        k.at(23, **{'arm' + t: (124.0, 12.0, 0.0), 'elbow' + t: 8.0, 'clav' + t: (4.0, 10.0)})
        k.at(26, **{'arm' + t: (70.0, 14.0, 0.0), 'elbow' + t: 30.0})
    # hands land on the thighs, then slide behind the hips for the push
    k.at(25, ikL=0.0, ikR=0.0)
    k.at(28.5, ikL=E(1.0), ikR=E(1.0))
    k.at(0, handOnKneeL=0.0, handOnKneeR=0.0)
    k.at(23, handOnKneeL=0.0, handOnKneeR=0.0)
    k.at(26, handOnKneeL=1.0, handOnKneeR=1.0)
    k.at(16, handKneeSideL='Left', handKneeSideR='Right')
    k.at(16, handKneeOffL=(0.02, 0.10, 0.05), handKneeOffR=(-0.02, 0.10, 0.05))
    k.at(16, handQL=RZ(-90), handQR=RZ(90))
    k.at(16, poleL=(1.0, 0.4, 0.2), poleR=(-1.0, 0.4, 0.2))
    k.at(29, clavL=(0.0, 0.0), clavR=(0.0, 0.0))
    k.at(46.5, handOnKneeL=1.0, handOnKneeR=1.0, handQL=RZ(-90), handQR=RZ(90))
    k.at(48, handL=(0.30, 0.04, 0.10), handR=(-0.30, 0.06, 0.10))
    k.at(51, handOnKneeL=0.0, handOnKneeR=0.0, handL=(0.24, 0.16, 0.06), handR=(-0.24, 0.17, 0.06))
    k.at(52.5, handQL=RZ(45), handQR=RZ(-45), poleL=(0.3, 1.0, 0.3), poleR=(-0.3, 1.0, 0.3))
    k.at(53, handL=(0.22, 0.22, 0.008), handR=(-0.22, 0.23, 0.008), plantL=0.0, plantR=0.0)
    k.at(54, plantL=1.0, plantR=1.0)
    k.at(57.5, plantL=1.0, plantR=1.0, ikL=1.0, ikR=1.0, handL=(0.22, 0.22, 0.008), handR=(-0.22, 0.23, 0.008))
    k.at(59, plantL=0.0, plantR=0.0, handL=(0.22, 0.20, 0.07), handR=(-0.22, 0.21, 0.07))
    k.at(60.5, ikL=0.0, ikR=0.0)
    for t in 'LR':
        k.at(58, **{'arm' + t: (-30.0, 20.0, 0.0), 'elbow' + t: 10.0})
        k.at(60.5, **{'arm' + t: (-8.0, 34.0, 0.0), 'elbow' + t: 24.0})
        k.at(62.5, **{'arm' + t: (70.0, 36.0, 0.0), 'elbow' + t: 30.0})
        k.at(64.5, **{'arm' + t: (112.0, 14.0, 0.0), 'elbow' + t: 26.0})
        k.at(69, **{'arm' + t: (30.0, 18.0, 0.0), 'elbow' + t: 24.0})
        k.at(78, **{'arm' + t: (20.0, 26.0, 0.0), 'elbow' + t: 24.0})
        k.at(81, **{'arm' + t: (2.0, 15.0, 0.0), 'elbow' + t: 12.0})

    # --- legs -----------------------------------------------------------------------------------------
    k.at(9, footL=(0.16, -0.66, 0.0), kneeL=(0.35, 0.0, 1.0))
    k.at(11.5, footL=(0.17, -0.57, 0.0), kneeL=(0.45, -0.1, 1.0))
    k.at(15, footL=(0.16, -0.64, 0.0), footR=(-0.15, -0.67, 0.0))
    k.at(18, footL=(0.16, -0.63, 0.0), footR=(-0.15, -0.64, 0.0))
    k.at(20, footL=(0.16, -0.61, 0.055), footR=(-0.15, -0.62, 0.05))
    k.at(22, footL=E((0.16, -0.60, 0.0)), footR=E((-0.15, -0.60, 0.0)))
    k.at(22, kneeL=(0.3, -0.1, 1.0), kneeR=(-0.3, -0.1, 1.0))
    k.at(47, footL=(0.16, -0.60, 0.0), footR=(-0.15, -0.60, 0.0),
         footQL=_lying_foot(-90, 28, 30), footQR=_lying_foot(-90, -22, 28))
    k.at(54, footL=E((0.14, -0.27, 0.0)), footR=E((-0.14, -0.28, 0.0)), footQL=standQL, footQR=standQR,
         kneeL=(0.35, -0.6, 1.0), kneeR=(-0.35, -0.6, 1.0))
    k.at(64.5, kneeL=(0.3, -1.0, 0.4), kneeR=(-0.3, -1.0, 0.4))
    # 2 mm contact margin during the snap rise: the half-frame LINEAR keys otherwise dip the soles 1.9 mm
    # between keys (measured at 120 Hz) while the legs straighten this fast
    k.at(65.5, footL=(0.14, -0.27, 0.0), footR=(-0.14, -0.28, 0.0))
    k.at(66.5, footL=E((0.14, -0.27, 0.002)), footR=E((-0.14, -0.28, 0.002)))
    k.at(68.5, footL=E((0.14, -0.27, 0.002)), footR=E((-0.14, -0.28, 0.002)))
    k.at(70, footL=(0.14, -0.27, 0.0), footR=(-0.14, -0.28, 0.0), kneeL=(0.1, -1.0, 0.0), kneeR=(-0.1, -1.0, 0.0))
    k.at(72.5, footR=(-0.13, -0.15, 0.06))
    k.at(75, footR=E((-0.124, 0.0, 0.0)))
    k.at(76, footL=(0.14, -0.27, 0.0))
    k.at(78, footL=(0.13, -0.13, 0.05))
    k.at(80.5, footL=E((0.124, 0.0, 0.0)))

    def layers(f):
        d = {}
        # dizzy circle: neck/head trace a circle, upper spine follows with lag
        c = window(f, 29, 48, 4, 5)
        ph = 2 * math.pi * (f - 29) / 15.0
        d['neck'] = (9 * c * math.cos(ph), 16 * c * math.sin(ph), 0.0)
        d['head'] = (5 * c * math.cos(ph - 0.7), 6 * c * math.sin(ph - 0.7), 0.0)
        d['spine'] = (4 * c * math.cos(ph - 1.4), 6 * c * math.sin(ph - 1.4), 0.0)
        # brr shake: head twist +-30 at 5 Hz, decaying; neck side and counter spine twist with lag
        b = window(f, 42, 52, 1.5, 4) * max(0.0, 1.0 - (f - 42) / 13.0)
        sh = math.sin(2 * math.pi * (f - 42) / 6.0)
        d['head'] = (d['head'][0], d['head'][1] + 4 * b * sh, d['head'][2] + 36 * b * sh)
        d['neck'] = (d['neck'][0], d['neck'][1] + 8 * b * math.sin(2 * math.pi * (f - 43) / 6.0), d['neck'][2] + 10 * b * sh)
        d['spine'] = (d['spine'][0], d['spine'][1], d['spine'][2] - 8 * b * math.sin(2 * math.pi * (f - 44) / 6.0))
        sw = window(f, 41, 53, 2, 4)
        d['clavL'] = (12 * sw, 0.0)
        d['clavR'] = (12 * sw, 0.0)
        # windmill: both arms circle (left leads), elbows loose
        w = window(f, 69, 79, 2, 3)
        for t, ph0 in (('L', 0.0), ('R', 0.6)):
            a = 2 * math.pi * ((f - 69) / 11.0 + ph0)
            d['arm' + t] = (55 * w * math.sin(a), 28 * w * (1 - math.cos(a)) / 2, 0.0)
        return d

    return L.Clip(rig, 'GetUp_FromBack', N, k.tracks(), layers=[layers])


def make_belly(rig):
    N = BEATS_BELLY['N']
    s0 = start_belly()
    idle = rig.idle_params()
    k = Keys()
    k.pose(0, s0).pose(6, s0, skip=('ground_set',))
    k.pose(N, idle, skip=('ground_set',))
    k.at(N, plantL=0.0, plantR=0.0, handOnKneeL=0.0, handOnKneeR=0.0)
    standQL, standQR = idle['footQL'], idle['footQR']
    kneelQL, kneelQR = _lying_foot(90, -8, 70), _lying_foot(90, 8, 70)

    # --- hips / ground: torso grounded -> free -> knees grounded -> free (standing) -----------------
    k.at(0, ground_set=('torso', 'legL', 'legR'))  # lying: belly or thighs carry the weight
    k.at(14, hips_pitch=64.0, hips_twist=-1.0)
    k.at(17, hips_pitch=E(84.0))
    k.at(19, hips_pitch=83.0, ground=1.0)
    k.at(19, hips_pos=(0.0, 0.0, 0.20))
    k.at(23.5, ground=0.0, hips_pos=(0.0, 0.10, 0.30), hips_pitch=80.0)
    k.at(24, ground_set=('legL', 'legR'))
    k.at(28.5, ground=1.0, hips_pos=(0.0, 0.29, 0.46), hips_pitch=92.0, hips_twist=0.0)
    k.at(46, ground=1.0, hips_pos=(0.0, 0.30, 0.46), hips_pitch=92.0)
    k.at(49.5, hips_pitch=72.0)
    k.at(50.5, ground_set=('legL',))
    k.at(53, hips_pitch=38.0, hips_pos=(0.0, 0.26, 0.55), hips_lean=-4.0)
    k.at(56, hips_pitch=40.0, ground=1.0, hips_pos=(0.0, 0.22, 0.46))
    k.at(58, hips_pos=(0.0, 0.17, 0.52))
    k.at(59.5, ground=0.0)
    k.at(60.5, hips_pos=(0.0, 0.09, 0.64), hips_pitch=28.0, hips_lean=2.0)
    k.at(65, hips_pos=(0.0, 0.0, 0.785), hips_pitch=6.0, hips_lean=0.0)
    k.at(69.5, hips_pos=(0.0, -0.09, 0.795), hips_pitch=10.0)
    k.at(73.5, hips_pos=(0.0, 0.035, 0.80), hips_pitch=-5.0)
    k.at(78, hips_pos=(0.0, -0.01, 0.815), hips_pitch=1.5)

    # --- spine / neck / head --------------------------------------------------------------------------
    k.at(6, spine=(-9.0, 0.0, 0.0))
    k.at(14, spine=(-26.0, 0.0, 0.0))
    k.at(17, spine=(-8.0, 0.0, 0.0))
    k.at(21, spine=(-22.0, 0.0, 0.0))
    k.at(28.5, spine=(4.0, 0.0, 0.0))
    k.at(46, spine=(4.0, 0.0, 0.0))
    k.at(50, spine=(6.0, 0.0, 0.0))
    k.at(54, spine=(18.0, -3.0, 0.0))
    k.at(60, spine=(28.0, 0.0, 0.0))
    k.at(64.5, spine=(14.0, 0.0, 0.0))
    k.at(69.5, spine=(24.0, 0.0, 0.0))
    k.at(73.5, spine=(-8.0, 0.0, 0.0))
    k.at(78, spine=(2.0, 0.0, 0.0))
    k.at(11, neck=(30.0, -4.0, 22.0), head=(10.0, -4.0, 26.0))
    k.at(15, neck=(34.0, -2.0, 6.0), head=(14.0, -2.0, 6.0))
    k.at(18, neck=(16.0, 0.0, 0.0), head=(4.0, 0.0, 0.0))
    k.at(21, neck=(-8.0, 0.0, 0.0), head=(-8.0, 0.0, 0.0))
    k.at(28.5, neck=(-6.0, 0.0, 0.0), head=(-6.0, 0.0, 0.0))
    k.at(46, neck=(-4.0, 0.0, 0.0), head=(-4.0, 0.0, 0.0))
    k.at(50.5, neck=(-10.0, 0.0, 0.0), head=(-6.0, 0.0, 0.0))
    k.at(55, neck=(8.0, 0.0, 0.0), head=(2.0, 0.0, 0.0))
    k.at(60, neck=(22.0, 0.0, 0.0), head=(10.0, 0.0, 0.0))
    k.at(66, neck=(-4.0, 0.0, 0.0), head=(-6.0, 0.0, 0.0))
    k.at(70, neck=(14.0, 0.0, 0.0), head=(8.0, 0.0, 0.0))
    k.at(74.5, neck=(-14.0, 0.0, 0.0), head=(-8.0, 0.0, 0.0))
    k.at(79, neck=(3.0, 0.0, 0.0), head=(2.0, 0.0, 0.0))

    # --- arms -----------------------------------------------------------------------------------------
    k.at(6, ikL=1.0, ikR=1.0, plantL=1.0, plantR=1.0)
    k.at(19, handL=(0.30, -0.17, 0.008), handR=(-0.30, -0.17, 0.008))
    k.at(28.5, handL=(0.24, -0.13, 0.008), handR=(-0.24, -0.13, 0.008), handQL=RZ(-90 + 5), handQR=RZ(90 - 5),
         poleL=(0.6, 0.6, 0.3), poleR=(-0.6, 0.6, 0.3))
    k.at(46, handL=(0.24, -0.13, 0.008), handR=(-0.24, -0.13, 0.008), ikL=1.0, ikR=1.0, plantL=1.0, plantR=1.0)
    k.at(47, plantL=1.0, plantR=1.0)
    k.at(48.5, plantL=0.0, plantR=0.0, handL=(0.25, -0.08, 0.11), handR=(-0.25, -0.08, 0.11))
    k.at(47, ikL=1.0, ikR=1.0)
    k.at(51, ikL=0.0, ikR=0.0)
    for t in 'LR':
        k.at(46, **{'arm' + t: (55.0, 20.0, 0.0), 'elbow' + t: 26.0})
        k.at(50, **{'arm' + t: (40.0, 22.0, 0.0), 'elbow' + t: 30.0})
        k.at(53, **{'arm' + t: (62.0, 18.0, 0.0), 'elbow' + t: 70.0})
    # both hands onto the right knee (half kneel), push, release
    k.at(0, handOnKneeL=0.0, handOnKneeR=0.0)
    k.at(51, handOnKneeL=0.0, handOnKneeR=0.0, ikL=0.0, ikR=0.0)
    k.at(55.5, handOnKneeL=1.0, handOnKneeR=1.0, ikL=1.0, ikR=1.0)
    k.at(50, handKneeSideL='Right', handKneeSideR='Right')
    k.at(50, handKneeOffL=(0.03, -0.02, 0.07), handKneeOffR=(-0.06, 0.10, 0.07),
         handQL=_eq(-72.5, 20.4, -94.2), handQR=_eq(-82.2, -20.2, 87.9), poleL=(0.6, 0.3, 0.2), poleR=(-1.0, 0.3, 0.2))
    k.at(58, handOnKneeL=1.0, handOnKneeR=1.0, ikL=1.0, ikR=1.0)
    k.at(61.5, ikL=0.0, ikR=0.0)
    for t in 'LR':
        k.at(59, **{'arm' + t: (55.0, 20.0, 0.0), 'elbow' + t: 80.0})
        k.at(63, **{'arm' + t: (20.0, 22.0, 0.0), 'elbow' + t: 20.0})
        k.at(67, **{'arm' + t: (40.0, 30.0, 0.0), 'elbow' + t: 26.0})
        k.at(78, **{'arm' + t: (14.0, 22.0, 0.0), 'elbow' + t: 20.0})
        k.at(80.5, **{'arm' + t: (3.0, 15.0, 0.0), 'elbow' + t: 13.0})

    # --- legs -----------------------------------------------------------------------------------------
    k.at(19, footL=(0.13, 0.675, 0.0), footR=(-0.12, 0.68, 0.0), footQL=s0['footQL'], footQR=s0['footQR'], kneeL=(0.25, 0.0, -1.0), kneeR=(-0.25, 0.0, -1.0))
    k.at(28.5, footL=E((0.13, 0.66, 0.0)), footR=E((-0.12, 0.66, 0.0)), footQL=kneelQL, footQR=kneelQR,
         kneeL=(0.2, -0.6, -1.0), kneeR=(-0.2, -0.6, -1.0))
    k.at(48, footR=(-0.12, 0.66, 0.0), footQR=kneelQR, kneeR=(-0.2, -0.6, -1.0))
    k.at(51, footR=(-0.13, 0.30, 0.10), kneeR=(-0.2, -1.0, 0.4))
    k.at(54, footR=E((-0.124, 0.0, 0.0)), footQR=standQR, kneeR=(-0.15, -1.0, 0.3))
    k.at(56, footL=(0.13, 0.66, 0.0), footQL=kneelQL, kneeL=(0.2, -0.6, -1.0))
    k.at(60, footL=(0.13, 0.30, 0.12), kneeL=(0.15, -1.0, 0.0))
    k.at(62.5, footL=(0.126, 0.06, 0.07), footQL=RX(-12) @ standQL)
    k.at(64, footQL=standQL)
    k.at(65, footL=E((0.124, 0.0, 0.0)), kneeL=(0.0, -1.0, 0.0), kneeR=(0.0, -1.0, 0.0))
    # teeter: up on the toes, then back onto the heels
    tipL, tipR = RX(-18) @ standQL, RX(-18) @ standQR
    backL, backR = RX(7) @ standQL, RX(7) @ standQR
    k.at(66, footQL=standQL, footQR=standQR)
    k.at(69.5, footQL=tipL, footQR=tipR)
    k.at(74, footQL=backL, footQR=backR)
    k.at(78, footQL=standQL, footQR=standQR)

    def layers(f):
        d = {}
        # noodle-arm tremor during both pushes (pitch bob drives the IK elbows)
        tr = window(f, 7, 16, 2, 2) + window(f, 20, 27, 2, 3)
        d['hips_pitch'] = 1.6 * tr * math.sin(2 * math.pi * (f - 7) / 3.4)
        d['spine'] = (1.5 * tr * math.sin(2 * math.pi * (f - 7.8) / 3.4), 0.0, 0.0)
        # all fours: one slow head circle, then the wet-dog shake (head leads, spine follows with lag)
        c = window(f, 29, 39, 3, 3)
        ph = 2 * math.pi * (f - 29) / 10.0
        d['neck'] = (10 * c * math.cos(ph), 16 * c * math.sin(ph), 0.0)
        d['head'] = (4 * c * math.cos(ph - 0.7), 6 * c * math.sin(ph - 0.7), 0.0)
        w = window(f, 37, 47, 1.5, 3)
        d['head'] = (d['head'][0], d['head'][1] + 10 * w * math.sin(2 * math.pi * (f - 37) / 6.0),
                     d['head'][2] + 34 * w * math.sin(2 * math.pi * (f - 37) / 6.0))
        d['neck'] = (d['neck'][0], d['neck'][1] + 8 * w * math.sin(2 * math.pi * (f - 38) / 6.0),
                     d['neck'][2] + 12 * w * math.sin(2 * math.pi * (f - 38) / 6.0))
        d['spine'] = (d['spine'][0], 8 * w * math.sin(2 * math.pi * (f - 39) / 6.0),
                      10 * w * math.sin(2 * math.pi * (f - 39.5) / 6.0))
        d['hips_twist'] = 7 * w * math.sin(2 * math.pi * (f - 40) / 6.0)
        d['hips_lean'] = 3 * w * math.sin(2 * math.pi * (f - 40.5) / 6.0)
        # teeter windmill: arms circle backward (fwd decreasing) to fight the forward tip
        wm = window(f, 65, 77, 2, 3)
        for t, ph0 in (('L', 0.0), ('R', 0.5)):
            a = -2 * math.pi * ((f - 65) / 13.0 + ph0)
            d['arm' + t] = (60 * wm * math.sin(a), 30 * wm * (1 - math.cos(a)) / 2, 0.0)
        return d

    return L.Clip(rig, 'GetUp_FromBelly', N, k.tracks(), layers=[layers])
