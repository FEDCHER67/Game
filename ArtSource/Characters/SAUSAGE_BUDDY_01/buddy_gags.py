"""Comedy clips for the Sausage Buddy (TASK-000243), procedural like the panic clip in buddy_anim.
Formula: stillness -> a 2-4 frame snap; the dumbest possible solution done at full energy; a rigid sausage
body with noodle limbs; a silhouette that reads from far away; chicken-like head snaps and blank stares.

Every clip returns {'frames': {frame: desired}, 'airborne': set(frames), 'face': [(shape, frame, value)],
'length': frames} (review GIFs: PREVIEWS). The build grounds each frame (lowest mesh point on z = 0) except the
airborne ones, keys the face track and, for PoliceCall, animates the phone prop from the 'phone' schedule.
Character frame: faces -Y, left = +X, 30 fps."""
import math
from mathutils import Vector, Matrix, Quaternion
from buddy_rig import P
from buddy_anim import (R, pose_from_joints, idle_joints, startle_joints, merge, step_joints, bump, smooth,
                        run_joints, apply_all, blend)

FPS = 30


def ramp(f, f0, f1):
    return smooth((f - f0) / max(1e-6, f1 - f0))


def look(deg, tilt=0.0):
    """Head turn split over neck and head (+ = toward his left); tilt > 0 nods forward."""
    return {'Neck': R((1, 0, 0), tilt * 0.6) @ R((0, 0, 1), deg * 0.62), 'Head': R((1, 0, 0), tilt * 0.4) @ R((0, 0, 1), deg * 0.38)}


def tip(desired, deg, pivot):
    """Whole-body pitch about the X axis through pivot: + falls forward (face down), - falls backward."""
    p = Vector(pivot)
    M = Matrix.Translation(p) @ Matrix.Rotation(math.radians(deg), 4, 'X') @ Matrix.Translation(-p)
    return apply_all(desired, M)


def tremble(f, amp=1.0):
    return {'Spine2': R((1, 0, 0), amp * 1.2 * math.sin(f * 2.3)), 'LeftArm': R((0, 1, 0), amp * 2.0 * math.sin(f * 2.9)),
            'RightArm': R((0, 1, 0), amp * 2.0 * math.sin(f * 3.3 + 1.0)), 'Head': R((0, 0, 1), amp * 1.5 * math.sin(f * 3.7))}


def knees(bend):
    """Soft crouch: both knees bend by `bend` degrees, hips/feet compensate (the build grounds the feet)."""
    return {'LeftUpLeg': R((1, 0, 0), -bend * 0.55), 'RightUpLeg': R((1, 0, 0), -bend * 0.55),
            'LeftLeg': R((1, 0, 0), bend), 'RightLeg': R((1, 0, 0), bend),
            'LeftFoot': R((1, 0, 0), -bend * 0.45), 'RightFoot': R((1, 0, 0), -bend * 0.45)}


def stiff(k):
    """Plank body: arms pressed straight to the sides, legs together (k: 0..1 from idle)."""
    J = idle_joints(0.0)
    target = {'LeftArm': R((0, 1, 0), 87), 'RightArm': R((0, 1, 0), -87), 'LeftForeArm': Quaternion(), 'RightForeArm': Quaternion(),
              'LeftHand': Quaternion(), 'RightHand': Quaternion(), 'Spine1': Quaternion(), 'Spine2': Quaternion(),
              'LeftUpLeg': R((0, 1, 0), 4), 'RightUpLeg': R((0, 1, 0), -4)}
    out = {}
    for name in set(J) | set(target):
        a, b = J.get(name, Quaternion()), target.get(name, Quaternion())
        out[name] = a.slerp(b, k)
    return out


def flail_arms(f, raise_deg=95.0, wave=1.0, speed=1.0, pitch=0.0):
    """Arms raised by raise_deg above the T-pose (95 = overhead; forward when lying face down), waving out of
    phase with amplitude `wave` (0 = still); pitch < 0 tilts them toward the back (off the floor when face down)."""
    ph = 2 * math.pi * f / (9.0 / speed)
    J = {}
    for side, s, o in (('Left', 1, 0.0), ('Right', -1, math.pi)):
        theta = raise_deg + 18 * wave * math.sin(ph + o)
        swing = 18 * wave * math.sin(ph + o + 1.1)
        J[side + 'Arm'] = R((1, 0, 0), swing + pitch) @ R((0, 1, 0), -s * theta)
        J[side + 'ForeArm'] = R((0, 1, 0), -s * 24 * wave * (0.6 + 0.4 * math.sin(2 * ph + o)))
    return J


def solve_arm(rig, rest, J, side, wrist, pole, hand_dir, palm_dir, curl=0.0):
    """Two-bone IK in the character frame: Arm/ForeArm/Hand rotations so the wrist reaches `wrist`, the hand points
    along hand_dir and the palm faces palm_dir; optional finger curl. Returns a new joint dict."""
    base = {k: v for k, v in J.items() if not (k.startswith(side + 'Hand') or k in (side + 'Arm', side + 'ForeArm'))}
    d0 = pose_from_joints(rig, rest, base)
    S = d0[P + side + 'Arm'].translation
    E0 = d0[P + side + 'ForeArm'].translation
    W0 = d0[P + side + 'Hand'].translation
    a, b = (E0 - S).length, (W0 - E0).length
    W = Vector(wrist)
    dvec = W - S
    d = max(abs(a - b) + 1e-4, min(a + b - 1e-4, dvec.length))
    dirv = dvec.normalized()
    cos_a = (a * a + d * d - b * b) / (2 * a * d)
    A = math.acos(max(-1.0, min(1.0, cos_a)))
    pole = Vector(pole)
    pp = pole - dirv * pole.dot(dirv)
    pp = pp.normalized() if pp.length > 1e-6 else dirv.orthogonal().normalized()
    E = S + dirv * (a * math.cos(A)) + pp * (a * math.sin(A))
    Wc = S + dirv * d
    q_arm = (E0 - S).normalized().rotation_difference((E - S).normalized())
    q_fore = (q_arm @ (W0 - E0).normalized()).rotation_difference((Wc - E).normalized())
    Mh = d0[P + side + 'Hand']
    qh0 = Mh.to_quaternion() @ rest[P + side + 'Hand'].to_quaternion().inverted()
    h1 = q_fore @ q_arm @ Mh.to_3x3().col[1].normalized()
    p1 = q_fore @ q_arm @ (qh0 @ Vector((0, 0, -1)))          # Mixamo T-pose: palms face down
    hd = Vector(hand_dir).normalized()
    q_h1 = h1.rotation_difference(hd)
    p2 = q_h1 @ p1
    pt = Vector(palm_dir)
    pt = (pt - hd * pt.dot(hd)).normalized()
    p2p = (p2 - hd * p2.dot(hd)).normalized()
    ang = math.atan2(hd.dot(p2p.cross(pt)), p2p.dot(pt))
    out = dict(base)
    out[side + 'Arm'] = q_arm
    out[side + 'ForeArm'] = q_fore
    out[side + 'Hand'] = Quaternion(hd, ang) @ q_h1
    if curl:
        axis = hd.cross(pt).normalized()
        for digit in ('Index', 'Middle', 'Ring'):
            for i in (1, 2, 3):
                out[f'{side}Hand{digit}{i}'] = Quaternion(axis, math.radians(curl))
        out[f'{side}HandThumb2'] = Quaternion(axis, math.radians(curl * 0.6))
    return out


def lerpv(a, b, t):
    return Vector(a).lerp(Vector(b), max(0.0, min(1.0, t)))


# ------------------------------------------------------------------ 1. double take, then flee
def double_take_flee(rig, rest):
    frames, air, face = {}, set(range(63, 66)), []
    dist = 0.0
    for f in range(1, 151):
        J = idle_joints((f - 1) / 60.0)
        root, yaw = Vector(), 0.0
        if f < 62:
            head = -80 * ramp(f, 18, 28) * (1 - ramp(f, 44, 52))
            J = merge(J, look(head))
        else:
            snap = min(1.0, (f - 62) / 3.0)
            k = 0.8 * snap
            J = merge(J, startle_joints(k))
            J = merge(J, {'Spine1': R((1, 0, 0), -6 * snap)})
            root = Vector((0, 0, 0.035 * bump(f, 64, 2.5)))
            if 65 <= f < 92:
                J = merge(J, tremble(f, 1.0))
                J = merge(J, knees(10))
            if f >= 78 and f < 81:
                J = merge(J, look(0, tilt=6 * bump(f, 79.5, 1.5)))       # gulp
            crouch = ramp(f, 86, 91) * (1 - ramp(f, 92, 97))
            J = merge(J, knees(34 * crouch))
            turn = ramp(f, 92, 104)
            head = -95 * min(1.0, (f - 62) / 2.0) * (1 - turn) if f < 104 else 0.0
            J = merge(J, look(head))
            yaw = 90.0 * turn
            if 92 <= f < 106:
                J = merge(J, step_joints('Right', bump(f, 95, 3.0)))
                J = merge(J, step_joints('Left', bump(f, 101, 3.0)))
        if f >= 104:
            k = f - 104
            speed = 3.0 * smooth(k / 10.0) * 0.85 + 0.45
            dist += speed / FPS
            back = bump(f, 126, 8) * 1.0
            Jr, bob = run_joints(k, back)           # run_joints already flails the arms overhead
            run = pose_from_joints(rig, rest, Jr, root_offset=Vector((dist, 0, bob)), yaw=90.0)
            if f < 110:
                frames[f] = blend(pose_from_joints(rig, rest, J, root_offset=root, yaw=yaw), run, smooth((f - 104) / 6.0))
            else:
                frames[f] = run
        else:
            frames[f] = pose_from_joints(rig, rest, J, root_offset=root, yaw=yaw)
    face += [('Happy', 1, 0.35), ('Happy', 61, 0.35), ('Happy', 64, 0.0)]
    face += [('Blink', 33, 0.0), ('Blink', 36, 1.0), ('Blink', 40, 0.0)]          # slow dumb blink at the van
    face += [('Surprised', 62, 0.0), ('Surprised', 64, 1.0), ('Surprised', 92, 1.0), ('Surprised', 102, 0.25),
             ('Surprised', 120, 0.25), ('Surprised', 126, 0.9), ('Surprised', 132, 0.25)]
    face += [('Blink', 73, 0.0), ('Blink', 74, 1.0), ('Blink', 75, 0.0)]
    face += [('Worried', 90, 0.0), ('Worried', 100, 1.0), ('Worried', 150, 1.0)]
    return {'frames': frames, 'airborne': air, 'face': face, 'length': 150}


# ------------------------------------------------------------------ 2. play dead: fall -> loop (~30 s in game) -> get up
HEEL = (0.0, 0.10, 0.0)


def play_dead_fall(rig, rest):
    """Startle, stiffen into a plank, fall backwards with a bounce; ends lying still = first frame of PlayDead_Loop."""
    frames, face = {}, []
    air = set(range(15, 18)) | set(range(45, 52))
    for f in range(1, 61):
        if f < 17:
            J = idle_joints((f - 1) / 60.0)
            J = merge(J, startle_joints(ramp(f, 14, 16) * 0.5))
            frames[f] = pose_from_joints(rig, rest, J, root_offset=Vector((0, 0, 0.02 * bump(f, 16, 1.5))))
            continue
        J = stiff(ramp(f, 17, 22))
        if f < 30:
            frames[f] = tip(pose_from_joints(rig, rest, J), 2.0 * bump(f, 26, 2.5), HEEL)
            continue
        t = min(1.0, (f - 30) / 14.0)
        angle, root = -90.0 * t * t, Vector()
        if 44 <= f <= 52:
            angle += 8.0 * bump(f, 47, 3.0) + 2.0 * bump(f, 51, 1.5)
            root = Vector((0, 0, 0.025 * bump(f, 47, 3.0)))
        frames[f] = tip(pose_from_joints(rig, rest, J, root_offset=root), angle, HEEL)
    face += [('Happy', 1, 0.2), ('Happy', 14, 0.0)]
    face += [('Surprised', 14, 0.0), ('Surprised', 16, 1.0), ('Surprised', 21, 1.0), ('Surprised', 24, 0.0)]
    face += [('Blink', 20, 0.0), ('Blink', 23, 1.0), ('Blink', 60, 1.0)]
    return {'frames': frames, 'airborne': air, 'face': face, 'length': 60}


def play_dead_loop(rig, rest):
    """Lying dead still, seamless 8 s loop. The game repeats it (~30 s) and then plays PlayDead_GetUp unless the
    player interacts. In the middle: one-eyed peek with chicken head snaps; later a toe twitch like an itch."""
    frames = {}
    for f in range(1, 241):
        J = stiff(1.0)
        lift = ramp(f, 70, 75) * (1 - ramp(f, 88, 90))
        snap = 0.0
        if 76 <= f < 88:
            snap = 18 if f < 80 else (-18 if f < 84 else 0)
        J = merge(J, look(snap, tilt=18 * lift))
        J = merge(J, {'LeftFoot': R((1, 0, 0), 28 * (bump(f, 160, 2.5) + bump(f, 166, 2.5)))})
        frames[f] = tip(pose_from_joints(rig, rest, J), -90.0, HEEL)
    face = [('Blink', 1, 1.0), ('Blink', 70, 1.0), ('Blink', 73, 0.0), ('Blink', 88, 0.0), ('Blink', 90, 1.0), ('Blink', 240, 1.0),
            ('Blink_L', 70, 0.0), ('Blink_L', 73, 1.0), ('Blink_L', 88, 1.0), ('Blink_L', 90, 0.0)]
    return {'frames': frames, 'airborne': set(), 'face': face, 'length': 240}


def play_dead_getup(rig, rest):
    """Eyes open, chicken look around, rises like a vampire (stiff plank about the heels), then 'nothing happened':
    hands behind the back, looks up, whistles innocently, rocks on his heels. Ends close to Idle."""
    frames = {}
    for f in range(1, 101):
        J = stiff(1.0 - ramp(f, 50, 60))
        lift = ramp(f, 12, 16) * (1 - ramp(f, 26, 30))
        snap = 20 if 16 <= f < 20 else (-20 if 20 <= f < 24 else 0)
        if 54 <= f < 58:
            snap = 26
        elif 58 <= f < 62:
            snap = -26
        J = merge(J, look(snap, tilt=16 * lift))
        if f < 28:
            angle = -90.0
        elif f < 46:
            angle = -90.0 * (1 - smooth((f - 28) / 18.0))
        else:
            angle = 5.0 * bump(f, 48, 2.5)
        behind = ramp(f, 62, 70)
        if behind > 0:                          # hands behind the back, looking up, rocking on the heels
            J['LeftArm'] = J['LeftArm'].slerp(R((1, 0, 0), 30) @ R((0, 1, 0), 78), behind)
            J['RightArm'] = J['RightArm'].slerp(R((1, 0, 0), 30) @ R((0, 1, 0), -78), behind)
            J['LeftForeArm'] = Quaternion().slerp(R((0, 1, 0), 62), behind)
            J['RightForeArm'] = Quaternion().slerp(R((0, 1, 0), -62), behind)
            rock = math.sin(2 * math.pi * (f - 62) / 30.0) * behind
            J = merge(J, look(0, tilt=-12 * behind))
            J = merge(J, {'Spine': R((0, 1, 0), 3 * rock), 'LeftFoot': R((1, 0, 0), -10 * max(0.0, rock)),
                          'RightFoot': R((1, 0, 0), -10 * max(0.0, rock))})
        frames[f] = tip(pose_from_joints(rig, rest, J), angle, HEEL)
    face = [('Blink', 1, 1.0), ('Blink', 10, 1.0), ('Blink', 13, 0.0), ('Blink', 64, 0.0), ('Blink', 68, 0.35), ('Blink', 100, 0.35),
            ('Surprised', 13, 0.0), ('Surprised', 15, 0.4), ('Surprised', 26, 0.4), ('Surprised', 34, 0.0),
            ('Worried', 26, 0.0), ('Worried', 32, 0.6), ('Worried', 50, 0.6), ('Worried', 56, 0.0),
            ('Surprised', 64, 0.0), ('Surprised', 68, 0.45), ('Surprised', 100, 0.45)]
    return {'frames': frames, 'airborne': set(), 'face': face, 'length': 100}


# ------------------------------------------------------------------ 3. trip on flat ground, belly slide, pop up, keep running
def trip_fall(rig, rest):
    frames, face = {}, []
    air = set(range(45, 52)) | set(range(53, 56)) | set(range(93, 100))
    dist, speed = 0.0, 3.0
    for f in range(1, 151):
        if f < 40:
            speed = 3.0
        elif f < 52:
            speed = 3.0 - 0.4 * (f - 40) / 12
        elif f < 78:
            speed = 2.6 * (1 - (f - 52) / 26) ** 2
        elif f < 92:
            speed = 0.0
        elif f < 100:
            speed = 1.5 * (f - 92) / 8
        else:
            speed = min(3.0, 1.5 + 1.5 * (f - 100) / 10)
        dist += speed / FPS
        root_y = -dist
        if f < 40 or f >= 100:
            k = f - 1 if f < 40 else f - 100
            back = -bump(f, 126, 8) if f >= 100 else 0.0
            J, bob = run_joints(k, back)            # run_joints already flails the arms overhead
            frames[f] = pose_from_joints(rig, rest, J, root_offset=Vector((0, root_y, bob)))
            if 100 <= f < 105:
                frames[f] = blend(frames[99], frames[f], smooth((f - 99) / 6.0))
            continue
        # 40-52 dive, 52-78 belly slide, 78-92 lying stare, 92-100 pop up like a plank spring
        if f < 52:
            t = (f - 40) / 12.0
            angle = 90.0 * t * t
        elif f < 92:
            angle = 90.0
        else:
            angle = 90.0 * (1 - smooth((f - 92) / 8.0))
        J = {}
        legs = ramp(f, 40, 50) * (1 - ramp(f, 92, 99))
        J['LeftUpLeg'] = R((1, 0, 0), 25 * legs)
        J['RightUpLeg'] = R((1, 0, 0), -15 * legs)
        J['LeftLeg'] = R((1, 0, 0), 100 * legs)
        J['RightLeg'] = R((1, 0, 0), 80 * legs)
        # dive: flailing; slide and stare: arms frozen forward and lifted off the floor; pop-up: flailing again
        wave = 1.0 if f < 50 else (1.0 - ramp(f, 50, 54) if f < 92 else ramp(f, 92, 96))
        pitch = -24 * ramp(f, 50, 55) * (1 - ramp(f, 92, 96))
        J = merge(J, flail_arms(f, 95, wave, 1.4 if f < 52 else 0.6, pitch))
        head_up = -42 * ramp(f, 44, 54) * (1 - ramp(f, 92, 98))
        tilt_snap = 12 if 84 <= f < 88 else 0
        J = merge(J, {'Neck': R((1, 0, 0), head_up * 0.6), 'Head': R((1, 0, 0), head_up * 0.4) @ R((0, 1, 0), tilt_snap)})
        bounce = Vector((0, 0, 0.03 * bump(f, 54, 2.0) + 0.09 * bump(f, 96, 3.0)))
        pivot = (0.0, root_y - 0.20, 0.0)
        frames[f] = tip(pose_from_joints(rig, rest, J, root_offset=Vector((0, root_y, 0)) + bounce), angle, pivot)
        if f < 45:
            frames[f] = blend(frames[39], frames[f], smooth((f - 39) / 6.0))
    face += [('Worried', 1, 1.0), ('Worried', 40, 1.0), ('Worried', 44, 0.0), ('Worried', 98, 0.0), ('Worried', 104, 1.0), ('Worried', 150, 1.0)]
    face += [('Surprised', 39, 0.0), ('Surprised', 41, 1.0), ('Surprised', 62, 1.0), ('Surprised', 72, 0.4), ('Surprised', 92, 0.4),
             ('Surprised', 96, 1.0), ('Surprised', 104, 0.2), ('Surprised', 122, 0.2), ('Surprised', 126, 0.9), ('Surprised', 132, 0.2)]
    face += [('Blink', 79, 0.0), ('Blink', 82, 1.0), ('Blink', 86, 0.0)]          # blank chicken blink lying there
    return {'frames': frames, 'airborne': air, 'face': face, 'length': 150}


# ------------------------------------------------------------------ 4. police call: pat pockets, juggle, drop, yell upside down
EAR_WRIST_R = Vector((-0.228, 0.004, 1.395))       # right wrist when the phone is on the right ear
FRONT_R, FRONT_L = Vector((-0.075, -0.205, 1.015)), Vector((0.075, -0.205, 1.015))
CATCH_L, CATCH_R = Vector((0.115, -0.235, 1.065)), Vector((-0.105, -0.235, 1.045))
FLOOR_PHONE = Vector((-0.05, -0.42, 0.0))


def police_call(rig, rest):
    frames, face = {}, []
    air = set(range(12, 15))
    up, fwd = Vector((0, 0, 1)), Vector((0, -1, 0))
    for f in range(1, 211):
        J = idle_joints((f - 1) / 60.0)
        root = Vector()
        if f >= 10:
            k = ramp(f, 10, 13) * (1 - ramp(f, 16, 20))
            J = merge(J, startle_joints(k))
            root = Vector((0, 0, 0.025 * bump(f, 13, 1.5)))
        targets = {}
        if 16 <= f < 40:          # frantic pocket patting, looking down
            ph = 2 * math.pi * (f - 16) / 6.0
            J = merge(J, look(0, tilt=22 * ramp(f, 16, 20)))
            J = merge(J, {'Spine1': R((0, 0, 1), 8 * math.sin(ph * 0.5))})
            pr = ramp(f, 16, 19)
            targets['Right'] = (lerpv((-0.40, 0, 1.0), (-0.205, -0.03, 0.865 + 0.035 * math.sin(ph)), pr), (-0.6, 0.6, 0.0), (0, 0, -1), (1, 0, 0), 15)
            targets['Left'] = (lerpv((0.40, 0, 1.0), (0.205, -0.03, 0.865 + 0.035 * math.sin(ph + math.pi)), pr), (0.6, 0.6, 0.0), (0, 0, -1), (-1, 0, 0), 15)
        elif 40 <= f < 52:        # found it: both hands bring it up in front, looking at it
            t = ramp(f, 40, 47)
            J = merge(J, look(0, tilt=22 - 6 * t))
            targets['Right'] = (lerpv((-0.205, -0.03, 0.88), FRONT_R, t), (-1, 0.3, -0.6), (0.3, -1, 0.25), (0, 0, 1), 35)
            targets['Left'] = (lerpv((0.205, -0.03, 0.88), FRONT_L, t), (1, 0.3, -0.6), (-0.3, -1, 0.25), (0, 0, 1), 20)
        elif 52 <= f < 92:        # juggle: R -> L (52-64), L -> R (68-76), R -> floor (80-92); hands always a bit late
            apex = 1.0 - abs((f - 58) / 6.0) if f < 64 else (1.0 - abs((f - 72) / 4.0) if f < 76 else 0.3)
            J = merge(J, look(0, tilt=-24 * max(0.0, apex) + (14 * ramp(f, 82, 90) if f >= 80 else 0.0)))
            if f < 64:
                rt = lerpv(FRONT_R + Vector((0, 0, 0.12)), CATCH_R + Vector((0, 0, 0.25)), ramp(f, 52, 58))
                lt = lerpv(FRONT_L, CATCH_L + Vector((0, 0, 0.30)), ramp(f, 52, 58)).lerp(CATCH_L, ramp(f, 58, 64))
            elif f < 68:
                rt, lt = lerpv(CATCH_R + Vector((0, 0, 0.25)), FRONT_R, ramp(f, 64, 68)), CATCH_L
            elif f < 76:
                rt = lerpv(FRONT_R, CATCH_R + Vector((0, 0, 0.18)), ramp(f, 68, 72)).lerp(CATCH_R, ramp(f, 72, 76))
                lt = lerpv(CATCH_L, CATCH_L + Vector((0.05, 0, 0.22)), ramp(f, 68, 74))
            elif f < 80:
                rt, lt = CATCH_R, lerpv(CATCH_L + Vector((0.05, 0, 0.22)), FRONT_L, ramp(f, 76, 80))
            else:                 # grabbing at the air while it falls
                g = ramp(f, 80, 90)
                rt = lerpv(CATCH_R, (-0.10, -0.36, 0.78), g) + Vector((0, 0, 0.05 * math.sin(f * 1.9)))
                lt = lerpv(FRONT_L, (0.10, -0.36, 0.80), g) + Vector((0, 0, 0.05 * math.sin(f * 2.3 + 1)))
                J = merge(J, {'Spine': R((1, 0, 0), 14 * g)})
            targets['Right'] = (rt, (-1, 0.3, -0.6), (0.2, -1, 0.4), (0, 0, 1), 25)
            targets['Left'] = (lt, (1, 0.3, -0.6), (-0.2, -1, 0.4), (0, 0, 1), 25)
        elif 92 <= f < 112:       # blank chicken stare at the phone on the floor
            J = merge(J, {'Spine': R((1, 0, 0), 14)})
            snap = 0.0
            if 104 <= f < 108:
                snap = 14
            elif 108 <= f < 111:
                snap = -10
            J = merge(J, look(0, tilt=30))
            J = merge(J, {'Head': R((0, 1, 0), snap)})
            targets['Right'] = ((-0.10, -0.36, 0.78), (-1, 0.3, -0.6), (0.2, -1, 0.4), (0, 0, 1), 10)
            targets['Left'] = ((0.10, -0.36, 0.80), (1, 0.3, -0.6), (-0.2, -1, 0.4), (0, 0, 1), 10)
        elif 112 <= f < 128:      # squat, snatch it (upside down), stand up with it at the ear
            s_ = ramp(f, 112, 117) * (1 - ramp(f, 120, 126))
            J = merge(J, knees(105 * s_))
            J = merge(J, {'Spine': R((1, 0, 0), 42 * s_), 'Spine1': R((1, 0, 0), 12 * s_)})
            J = merge(J, look(0, tilt=10 * s_))
            grab = FLOOR_PHONE + Vector((0, 0.10, 0.12))
            rt = lerpv((-0.10, -0.36, 0.78), grab, ramp(f, 112, 117)) if f < 120 else lerpv(grab, EAR_WRIST_R, ramp(f, 120, 127))
            hd = (0, -0.2, -1) if f < 120 else Vector((0, -0.2, -1)).lerp(up, ramp(f, 120, 127))
            pd = (0, 0, -1) if f < 120 else Vector((0, 0, -1)).lerp(Vector((1, 0, 0)), ramp(f, 120, 127))
            targets['Right'] = (rt, (-1, 0.4, -0.5), hd, pd, 30)
        elif f >= 128:            # yelling into the wrong end; 170-188 looks at it, then yells again
            look_at = ramp(f, 170, 175) * (1 - ramp(f, 182, 187))
            yell = 1.0 - look_at
            ph = 2 * math.pi * (f - 128) / 7.5
            peck = max(0.0, math.sin(ph))
            J = merge(J, {'Neck': R((1, 0, 0), 14 * peck * yell), 'Head': R((1, 0, 0), 6 * peck * yell),
                          'Spine': R((1, 0, 0), 5 * math.sin(ph) * yell)})
            J = merge(J, knees(10 + 8 * abs(math.sin(ph * 0.5)) * yell))
            if look_at > 0:
                tilt_snap = 14 if 177 <= f < 181 else 0
                J = merge(J, look(0, tilt=8 * look_at))
                J = merge(J, {'Head': R((0, 1, 0), tilt_snap)})
            wr = EAR_WRIST_R.lerp(Vector((-0.06, -0.27, 1.34)), look_at)
            targets['Right'] = (wr, (-1, 0.4, -0.5), up, Vector((1, 0, 0)).lerp(Vector((0, 1, 0)), look_at), 30)
            # free left arm: shaking and pointing at the danger
            pa = 2 * math.pi * (f - 128) / 10.0
            J['LeftArm'] = (R((1, 0, 0), (30 + 15 * math.sin(pa)) * yell) @ R((0, 1, 0), -(55 + 25 * math.sin(pa * 1.3)) * yell)).slerp(
                J['LeftArm'], look_at)
            J['LeftForeArm'] = R((0, 1, 0), -(15 + 15 * math.sin(pa * 2)) * yell)
        for side, (w, pole, hd, pd, curl) in targets.items():
            J = solve_arm(rig, rest, J, side, w, pole, hd, pd, curl)
        frames[f] = pose_from_joints(rig, rest, J, root_offset=root)
    face += [('Happy', 1, 0.25), ('Happy', 10, 0.0), ('Happy', 42, 0.0), ('Happy', 45, 0.8), ('Happy', 51, 0.8), ('Happy', 53, 0.0)]
    face += [('Surprised', 10, 0.0), ('Surprised', 12, 1.0), ('Surprised', 18, 0.2), ('Surprised', 40, 0.0),
             ('Surprised', 52, 0.0), ('Surprised', 54, 1.0), ('Surprised', 90, 1.0), ('Surprised', 94, 0.45), ('Surprised', 112, 0.45),
             ('Surprised', 116, 0.8), ('Surprised', 126, 0.6)]
    face += [('Worried', 14, 0.0), ('Worried', 20, 1.0), ('Worried', 40, 1.0), ('Worried', 44, 0.0), ('Worried', 52, 0.0),
             ('Worried', 60, 0.8), ('Worried', 92, 0.8), ('Worried', 96, 0.0), ('Worried', 124, 0.0), ('Worried', 130, 0.7), ('Worried', 210, 0.7)]
    face += [('Blink', 99, 0.0), ('Blink', 102, 1.0), ('Blink', 106, 0.0), ('Blink', 176, 0.0), ('Blink', 179, 1.0), ('Blink', 183, 0.0)]
    for f in range(128, 211, 2):            # yelling: the O mouth pumps with the head pecks
        if 172 <= f < 186:
            v = 0.15
        else:
            v = 0.55 + 0.45 * abs(math.sin(math.pi * (f - 128) / 7.5))
        face.append(('Surprised', f, round(v, 3)))
    phone = [('hidden', 1, 37), ('hand', 'Right', 37, 52, False), ('fly', 52, 64, 'Right', 'Left', 0.32, 2),
             ('hand', 'Left', 64, 68, False), ('fly', 68, 76, 'Left', 'Right', 0.20, 1), ('hand', 'Right', 76, 80, False),
             ('drop', 80, 92, 'Right', FLOOR_PHONE), ('floor', 92, 116), ('pick', 116, 119, 'Right'), ('hand', 'Right', 119, 211, True)]
    return {'frames': frames, 'airborne': air, 'face': face, 'length': 210, 'phone': phone}


# ------------------------------------------------------------------ 5. fake surrender, then bolt (TASK-000245)
def fake_surrender_flee(rig, rest):
    """Hands snap up ('ok ok, I give up'), nervous nods; slowly looks left, slowly right; one tiny careful step back;
    a beat - then whips around and runs flat out (faster cadence than the panic run)."""
    frames = {}
    air = set(range(12, 16))
    dist = 0.0
    up_pose = flail_arms(0, 92, 0.0)
    for f in range(1, 151):
        J = idle_joints((f - 1) / 60.0)
        root = Vector()
        if f >= 12:
            k = min(1.0, (f - 12) / 3.0)
            for side in ('Left', 'Right'):
                J[side + 'Arm'] = J[side + 'Arm'].slerp(up_pose[side + 'Arm'], k)
                J[side + 'ForeArm'] = J.get(side + 'ForeArm', Quaternion()).slerp(up_pose[side + 'ForeArm'], k)
            J = merge(J, tremble(f, 0.6 * ramp(f, 15, 20) * (1 - ramp(f, 92, 94))))
            root = Vector((0, 0, 0.02 * bump(f, 13.5, 1.5)))
            nod = 9 * (bump(f, 19, 1.5) + bump(f, 23, 1.5))
            head = 60 * ramp(f, 32, 46) * (1 - ramp(f, 52, 70)) - 60 * ramp(f, 52, 70) * (1 - ramp(f, 76, 82))
            J = merge(J, look(head, tilt=nod))
        back = 0.12 * ramp(f, 82, 92)
        if 82 <= f < 93:
            J = merge(J, step_joints('Right', 0.6 * bump(f, 87, 4.0)))
        stand = Vector((0, back, 0))
        if f < 95:
            frames[f] = pose_from_joints(rig, rest, J, root_offset=root + stand)
            continue
        turn = smooth((f - 95) / 4.0)
        speed = 4.4 * smooth((f - 95) / 6.0)
        dist += speed / FPS
        Jr, bob = run_joints((f - 95) * 1.3, -bump(f, 128, 7))
        run = pose_from_joints(rig, rest, Jr, root_offset=Vector((0, back + dist, bob)), yaw=180.0)
        if f < 100:
            frames[f] = blend(pose_from_joints(rig, rest, J, root_offset=stand, yaw=180.0 * turn), run, smooth((f - 95) / 5.0))
        else:
            frames[f] = run
    face = [('Happy', 1, 0.3), ('Happy', 11, 0.3), ('Happy', 13, 0.0),
            ('Surprised', 11, 0.0), ('Surprised', 13, 1.0), ('Surprised', 20, 0.25), ('Surprised', 92, 0.25), ('Surprised', 95, 1.0),
            ('Surprised', 104, 0.3), ('Surprised', 124, 0.3), ('Surprised', 128, 0.9), ('Surprised', 134, 0.3),
            ('Worried', 13, 0.0), ('Worried', 18, 1.0), ('Worried', 30, 0.6), ('Worried', 92, 0.6), ('Worried', 96, 1.0), ('Worried', 150, 1.0),
            ('Blink', 47, 0.0), ('Blink', 49, 1.0), ('Blink', 51, 0.0), ('Blink', 89, 0.0), ('Blink', 91, 1.0), ('Blink', 93, 0.0)]
    return {'frames': frames, 'airborne': air, 'face': face, 'length': 150}


# ------------------------------------------------------------------ 6. terrible hiding behind a pole far too thin (TASK-000245)
HIDE_POLE = (0.0, -0.33)       # lamp post right in front of him (preview prop); the threat / camera is at -Y


def tiptoes(k):
    return {'LeftFoot': R((1, 0, 0), 26 * k), 'RightFoot': R((1, 0, 0), 26 * k)}


def hide_enter(rig, rest):
    """Runs in, skids, turns to the threat and 'hides' behind the thin pole: stiff, on tiptoes, chin up, eyes shut
    (if I can't see you, you can't see me). Ends on the first frame of Hide_Loop."""
    frames = {}
    x = -2.64
    for f in range(1, 71):
        if f < 34:
            Jr, bob = run_joints(f - 1, 0.8 * bump(f, 18, 6))
            x += 2.4 / FPS
            frames[f] = pose_from_joints(rig, rest, Jr, root_offset=Vector((x, 0, bob)), yaw=90.0)
            continue
        if f < 40:                              # skid: lean back, feet forward
            sk = bump(f, 37, 3.0)
            x += (2.4 / FPS) * (1 - (f - 34) / 6.0)
            J = merge(flail_arms(f, 70, 0.8), {'Spine': R((1, 0, 0), -16 * sk), 'LeftUpLeg': R((1, 0, 0), -22 * sk),
                                                  'RightUpLeg': R((1, 0, 0), -22 * sk)})
            frames[f] = pose_from_joints(rig, rest, J, root_offset=Vector((x, 0, 0)), yaw=90.0)
            continue
        turn = smooth((f - 40) / 6.0)
        hide = ramp(f, 46, 52)
        J = stiff(hide)
        J = merge(J, step_joints('Left', bump(f, 42, 2.5) * 0.5))
        J = merge(J, step_joints('Right', bump(f, 46, 2.5) * 0.5))
        J = merge(J, look(0, tilt=-10 * hide))
        J = merge(J, tiptoes(hide))
        frames[f] = pose_from_joints(rig, rest, J, root_offset=Vector((x * (1 - turn), 0, 0)), yaw=90.0 * (1 - turn))
    face = [('Worried', 1, 1.0), ('Worried', 44, 1.0), ('Worried', 50, 0.3), ('Surprised', 30, 0.0), ('Surprised', 36, 0.8),
            ('Surprised', 46, 0.3), ('Surprised', 52, 0.0), ('Blink', 48, 0.0), ('Blink', 52, 1.0), ('Blink', 70, 1.0)]
    return {'frames': frames, 'airborne': set(), 'face': face, 'length': 70}


def hide_loop(rig, rest):
    """Seamless 6 s loop behind the pole: eyes shut; peeks out to his left with both eyes and chicken head snaps,
    later to his right with one eye; gulp. The game loops it until the player leaves (or reacts otherwise)."""
    frames = {}
    for f in range(1, 181):
        J = stiff(1.0)
        J = merge(J, tiptoes(1.0))
        lean = ramp(f, 30, 34) * (1 - ramp(f, 50, 53)) - ramp(f, 100, 104) * (1 - ramp(f, 120, 123))
        snap = 0.0
        if 38 <= f < 42 or 112 <= f < 116:
            snap = 16 if f < 100 else -16
        elif 42 <= f < 46 or 108 <= f < 112:
            snap = -10 if f < 100 else 10
        gulp = 6 * bump(f, 150, 2.0)
        J = merge(J, {'Spine': R((0, 1, 0), 10 * lean), 'Spine1': R((0, 1, 0), 8 * lean), 'Spine2': R((0, 1, 0), 6 * lean)})
        J = merge(J, look(snap, tilt=-10 + gulp))
        J = merge(J, {'Neck': R((0, 1, 0), 10 * lean)})
        frames[f] = pose_from_joints(rig, rest, J)
    face = [('Blink', 1, 1.0), ('Blink', 30, 1.0), ('Blink', 33, 0.0), ('Blink', 50, 0.0), ('Blink', 52, 1.0),
            ('Blink', 100, 1.0), ('Blink', 103, 0.0), ('Blink', 120, 0.0), ('Blink', 122, 1.0), ('Blink', 180, 1.0),
            ('Blink_L', 100, 0.0), ('Blink_L', 103, 1.0), ('Blink_L', 120, 1.0), ('Blink_L', 122, 0.0),
            ('Surprised', 30, 0.0), ('Surprised', 34, 0.45), ('Surprised', 50, 0.45), ('Surprised', 52, 0.0),
            ('Surprised', 100, 0.0), ('Surprised', 104, 0.45), ('Surprised', 120, 0.45), ('Surprised', 122, 0.0)]
    return {'frames': frames, 'airborne': set(), 'face': face, 'length': 180}


# ------------------------------------------------------------------ 7. runs looking back, BAM into a wall (TASK-000245)
BONK_WALL_X = 2.50             # wall face (preview prop) across his path


def lookback_bonk(rig, rest):
    """Runs away staring back over his shoulder; turns his head forward a split second too late - BAM into the wall;
    stuck for a moment, slides down it into a frog squat with the hands squeaking up the wall, sits dazed, gets up,
    shakes his head, turns left and runs on along the wall as if nothing happened (looking back again)."""
    frames = {}
    x0, speed, hit = -2.4, 3.6, 40
    x_hit = x0 + speed * (hit - 1) / FPS
    dist = 0.0
    for f in range(1, 151):
        if f < hit:
            back = ramp(f, 6, 12) * (1 - ramp(f, 36, 38))
            Jr, bob = run_joints(f - 1, back)
            frames[f] = pose_from_joints(rig, rest, Jr, root_offset=Vector((x0 + speed * (f - 1) / FPS, 0, bob)), yaw=90.0)
            continue
        if f < 98:
            slide = ramp(f, 48, 72) * (1 - ramp(f, 88, 98))
            J = {}
            for side, sg in (('Left', 1), ('Right', -1)):
                J[side + 'Arm'] = R((0, 0, 1), -sg * 22) @ R((0, 1, 0), -sg * (8 + 55 * slide))
                J[side + 'ForeArm'] = R((0, 1, 0), -sg * 10)
            J = merge(J, {'LeftUpLeg': R((0, 1, 0), -48 * slide) @ R((1, 0, 0), -20 * slide),
                          'RightUpLeg': R((0, 1, 0), 48 * slide) @ R((1, 0, 0), -20 * slide),
                          'LeftLeg': R((1, 0, 0), 95 * slide), 'RightLeg': R((1, 0, 0), 95 * slide)})
            wob = ramp(f, 72, 76) * (1 - ramp(f, 88, 92))
            J = merge(J, look(14 * math.sin((f - 72) * 0.5) * wob, tilt=10 * math.cos((f - 72) * 0.5) * wob))
            root = Vector((x_hit - 0.035 * bump(f, 41, 1.5), 0, 0))
            frames[f] = pose_from_joints(rig, rest, J, root_offset=root, yaw=90.0)
            if f < 43:
                frames[f] = blend(frames[hit - 1], frames[f], smooth((f - hit + 1) / 3.0))
            continue
        if f < 112:                             # shake it off, turn left
            J = idle_joints(0.0)
            shake = 18 * math.sin((f - 98) * 2.4) * ramp(f, 98, 100) * (1 - ramp(f, 104, 107))
            J = merge(J, look(shake))
            yaw = 90.0 + 90.0 * smooth((f - 106) / 6.0)
            frames[f] = pose_from_joints(rig, rest, J, root_offset=Vector((x_hit, 0, 0)), yaw=yaw)
            if f < 101:
                frames[f] = blend(frames[97], frames[f], smooth((f - 97) / 4.0))
            continue
        dist += 3.4 * smooth((f - 112) / 8.0) / FPS
        Jr, bob = run_joints(f - 112, ramp(f, 126, 132))
        run = pose_from_joints(rig, rest, Jr, root_offset=Vector((x_hit, dist, bob)), yaw=180.0)
        frames[f] = blend(frames[111], run, smooth((f - 111) / 5.0)) if f < 116 else run
    face = [('Worried', 1, 1.0), ('Worried', 36, 1.0), ('Worried', 38, 0.0), ('Worried', 76, 0.0), ('Worried', 80, 0.35),
            ('Worried', 98, 0.35), ('Worried', 100, 0.0), ('Worried', 112, 0.0), ('Worried', 118, 1.0), ('Worried', 150, 1.0),
            ('Surprised', 35, 0.0), ('Surprised', 37, 1.0), ('Surprised', 46, 1.0), ('Surprised', 52, 0.3), ('Surprised', 96, 0.3),
            ('Surprised', 100, 0.15), ('Surprised', 126, 0.15), ('Surprised', 132, 0.8), ('Surprised', 138, 0.2),
            ('Blink', 40, 0.0), ('Blink', 41, 1.0), ('Blink', 43, 0.0), ('Blink', 52, 0.0), ('Blink', 58, 0.55), ('Blink', 88, 0.55),
            ('Blink', 94, 0.0), ('Blink', 100, 0.0), ('Blink', 102, 1.0), ('Blink', 104, 0.0)]
    return {'frames': frames, 'airborne': set(), 'face': face, 'length': 150}


def build_gags(rig, rest):
    return {'DoubleTake_Flee': double_take_flee(rig, rest), 'PlayDead_Fall': play_dead_fall(rig, rest),
            'PlayDead_Loop': play_dead_loop(rig, rest), 'PlayDead_GetUp': play_dead_getup(rig, rest),
            'TripFall': trip_fall(rig, rest), 'PoliceCall': police_call(rig, rest),
            'FakeSurrender_Flee': fake_surrender_flee(rig, rest), 'Hide_Enter': hide_enter(rig, rest),
            'Hide_Loop': hide_loop(rig, rest), 'LookBack_Bonk': lookback_bonk(rig, rest)}


# Review GIFs: (gif name, [(clip, first, last), ...], follow offset or [(sequence frame, offset, look), ...]).
# PlayDead shows fall -> part of the loop (the peek) -> get up.
_WIDE, _CLOSE, _LOOK = Vector((-2.6, -2.9, 0.55)), Vector((-1.45, -0.55, 1.25)), Vector((0, 0.35, 0))
PREVIEWS = [
    ('DoubleTake_Flee', [('DoubleTake_Flee', 1, 150)], Vector((-2.4, -4.4, 0.45))),
    ('PlayDead', [('PlayDead_Fall', 1, 60), ('PlayDead_Loop', 1, 120), ('PlayDead_GetUp', 1, 100)],
     [(1, _WIDE, Vector()), (42, _WIDE, Vector()), (58, _CLOSE, _LOOK), (186, _CLOSE, _LOOK), (206, _WIDE, Vector())]),
    ('TripFall', [('TripFall', 1, 150)], Vector((-2.2, -3.8, 0.55))),
    ('PoliceCall', [('PoliceCall', 1, 210)], Vector((-1.7, -3.1, 0.35))),
    ('FakeSurrender_Flee', [('FakeSurrender_Flee', 1, 150)], Vector((-1.6, -3.6, 0.45))),
    ('TerribleHiding', [('Hide_Enter', 1, 70), ('Hide_Loop', 1, 180)], Vector((0.5, -4.2, 0.5))),
    ('LookBack_Bonk', [('LookBack_Bonk', 1, 150)], Vector((-1.4, -4.4, 0.5))),
]
# Preview-only set dressing (never in the model files): a lamp post too thin to hide behind, a wall to run into.
PREVIEW_PROPS = {
    'TerribleHiding': [('pole', (HIDE_POLE[0], HIDE_POLE[1], 0.0), (0.055, 0.055, 3.1))],
    'LookBack_Bonk': [('wall', (BONK_WALL_X + 0.125, 0.0, 1.4), (0.25, 7.0, 2.8))],
}


# ------------------------------------------------------------------ face track and the phone prop
def face_action(face, name, keys):
    import bpy
    key = face.data.shape_keys
    key.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    key.animation_data.action = act
    kb = key.key_blocks
    shapes = sorted({k[0] for k in keys} | {'Blink', 'Blink_L', 'Blink_R', 'Surprised', 'Worried', 'Happy'})
    for s in shapes:
        kb[s].value = 0.0
        kb[s].keyframe_insert('value', frame=1)
    for s, f, v in sorted(keys, key=lambda k: (k[0], k[1])):
        kb[s].value = v
        kb[s].keyframe_insert('value', frame=f)
    for s in shapes:
        kb[s].value = 0.0
    return act


def build_phone(collection):
    """Small silver phone like the in-game one: rounded body, glowing screen, island, camera bump (+Y = top)."""
    import bpy, bmesh
    import buddy_geo as G
    body_m = G.mat('Prop_Phone_Body', (196, 200, 206), 0.35)
    screen_m = G.mat('Prop_Phone_Screen', (120, 190, 255), 0.2)
    dark_m = G.mat('Prop_Phone_Dark', (18, 18, 22), 0.3)
    try:
        b = next(n for n in screen_m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs['Emission Color'].default_value = G.srgb((120, 190, 255))
        b.inputs['Emission Strength'].default_value = 1.2
    except Exception:
        pass
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.097, 0.202, 0.015), verts=bm.verts)          # 1.35x a real phone: reads from afar
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.006, segments=2, affect='EDGES', profile=0.5)
    me = bpy.data.meshes.new('Prop_Phone')
    bm.to_mesh(me); bm.free()
    me.materials.append(body_m); me.materials.append(screen_m); me.materials.append(dark_m)
    for p in me.polygons:
        if p.normal.z > 0.9 and abs(p.center.x) < 0.040 and abs(p.center.y) < 0.092:
            p.material_index = 1
    ob = bpy.data.objects.new('Prop_Phone', me)
    collection.objects.link(ob)
    island = G.ellipsoid('Prop_Phone_Island', (0, 0.086, 0.0078), (0.0135, 0.0047, 0.0016), dark_m, seg=12, rings=6)
    cam = G.ellipsoid('Prop_Phone_Camera', (-0.027, 0.073, -0.0084), (0.0135, 0.0135, 0.003), dark_m, seg=12, rings=6)
    G.join(ob, [island, cam])
    for p in ob.data.polygons:
        p.use_smooth = False
    ob.rotation_mode = 'QUATERNION'
    return ob


def phone_track(phone, rest, clip, shift, name='PoliceCall_Phone'):
    """Object keys for the phone from the clip's hand matrices (after grounding) and its schedule."""
    import bpy
    frames = clip['frames']

    def grip(f, side, flipped):
        M = frames[f][P + side + 'Hand']
        q = M.to_quaternion() @ rest[P + side + 'Hand'].to_quaternion().inverted()
        hd = M.to_3x3().col[1].normalized()
        palm = (q @ Vector((0, 0, -1))).normalized()
        pos = M.translation + hd * 0.080 + palm * 0.040 + Vector((0, 0, shift[f]))
        y = -hd if flipped else hd
        z = palm
        x = y.cross(z).normalized()
        z = x.cross(y).normalized()
        rot = Matrix((x, y, z)).transposed().to_quaternion()
        return pos, rot

    flat = Matrix(((1, 0, 0), (0, 1, 0), (0, 0, 1))).to_quaternion() @ Quaternion((0, 0, 1), math.radians(-20))
    track = {}
    last = max(frames)
    for seg in clip['phone']:
        kind = seg[0]
        if kind == 'hidden':
            _, f0, f1 = seg
            pos, rot = grip(f1, 'Right', False)
            for f in range(f0, f1):
                track[f] = (pos, rot, 0.0)
        elif kind == 'hand':
            _, side, f0, f1, flipped = seg
            for f in range(f0, min(f1, last + 1)):
                pos, rot = grip(f, side, flipped)
                track[f] = (pos, rot, 1.0)
        elif kind == 'fly':
            _, f0, f1, a, b, h, turns = seg
            p0, r0 = grip(f0, a, False)
            p1, r1 = grip(f1, b, False)
            for f in range(f0, f1):
                t = (f - f0) / (f1 - f0)
                pos = p0.lerp(p1, t) + Vector((0, 0, 4 * h * t * (1 - t)))
                rot = Quaternion((1, 0, 0), 2 * math.pi * turns * t) @ r0.slerp(r1, t)
                track[f] = (pos, rot, 1.0)
        elif kind == 'drop':
            _, f0, f1, a, floor = seg
            p0, r0 = grip(f0, a, False)
            land = Vector((floor.x, floor.y, 0.0075))
            for f in range(f0, f1):
                t = (f - f0) / (f1 - f0)
                pos = p0.lerp(land, t) + Vector((0, 0, 4 * 0.10 * t * (1 - t)))
                rot = Quaternion((1, 0, 0), 2 * math.pi * 1.0 * t) @ r0.slerp(flat, t)
                track[f] = (pos, rot, 1.0)
            track['land'] = land
        elif kind == 'floor':
            _, f0, f1 = seg
            land = track['land']
            for f in range(f0, f1):
                b = bump(f, f0 + 3, 3.0)
                track[f] = (land + Vector((0, 0, 0.035 * b)), Quaternion((0, 1, 0), math.radians(10 * b)) @ flat, 1.0)
        elif kind == 'pick':
            _, f0, f1, side = seg
            land = track['land']
            p1, r1 = grip(f1, side, True)
            for f in range(f0, f1):
                t = smooth((f - f0) / (f1 - f0))
                track[f] = (land.lerp(p1, t), flat.slerp(r1, t), 1.0)
    phone.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    phone.animation_data.action = act
    for f in sorted(k for k in track if isinstance(k, int)):
        pos, rot, sc = track[f]
        phone.location = pos
        phone.rotation_quaternion = rot
        phone.scale = (sc, sc, sc)
        phone.keyframe_insert('location', frame=f)
        phone.keyframe_insert('rotation_quaternion', frame=f)
        phone.keyframe_insert('scale', frame=f)
    return act
