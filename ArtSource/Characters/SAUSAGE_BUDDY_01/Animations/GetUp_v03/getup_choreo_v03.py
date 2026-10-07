"""Choreography for GetUp_FromBack_v03 / GetUp_FromBelly_v03 (Sausage Buddy).

STATUS (handoff 2026-10-07): only the two lying START POSES are authored and verified (they define the
ragdoll-blend contract: head direction, hipsStart). The full performances are PLANNED below as beat
sheets (BEATS_*); make_back()/make_belly() currently return a short hold of the start pose so the whole
pipeline (floor solver, keying, review renders) can be exercised. READY stays False until the beats are
authored and reviewed; build_getups_v03.py refuses --final while READY is False.

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
from mathutils import Vector
import getup_lib_v03 as L
from getup_lib_v03 import Track, QTrack, Step, RX, RY, RZ, P

READY = False  # flip to True only after the full performances are authored and reviewed

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
        'ikL': 1.0, 'ikR': 1.0,
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
        'neck': (10.0, -6.0, 30.0), 'head': (6.0, -8.0, 48.0),
        'clavL': (6.0, 0.0), 'clavR': (6.0, 0.0),
        'ikL': 1.0, 'ikR': 1.0,
        'handL': (0.30, -0.17, 0.008), 'handR': (-0.30, -0.17, 0.008),
        'handQL': RZ(-90 + 15), 'handQR': RZ(90 - 15),
        'poleL': (0.8, 0.5, 0.7), 'poleR': (-0.8, 0.5, 0.7),
        'footL': (0.13, 0.675, 0.0), 'footR': (-0.12, 0.68, 0.0),
        'footQL': _lying_foot(90, -12, 62), 'footQR': _lying_foot(90, 10, 58),
        'kneeL': (0.25, 0.0, -1.0), 'kneeR': (-0.25, 0.0, -1.0),
        'ground': 1.0, 'ground_set': ('torso',),
    }


def _hold_tracks(pose, f0=0, f1=6):
    tracks = {}
    for k, v in pose.items():
        if k == 'ground_set':
            tracks[k] = Step([(f0, v)])
        elif hasattr(v, 'slerp'):
            tracks[k] = QTrack([(f0, v), (f1, v)])
        else:
            tracks[k] = Track([(f0, v), (f1, v)])
    return tracks


def make_back(rig):
    """STUB: hold of the supine start pose (6 frames). Replace with the BEATS_BACK performance."""
    return L.Clip(rig, 'GetUp_FromBack', 6, _hold_tracks(start_back()))


def make_belly(rig):
    """STUB: hold of the prone start pose (6 frames). Replace with the BEATS_BELLY performance."""
    return L.Clip(rig, 'GetUp_FromBelly', 6, _hold_tracks(start_belly()))
