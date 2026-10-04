"""Pose authoring and the panic 'turn around and flee' animation for the Sausage Buddy rig.
Poses are written as joint rotations in the character frame (character faces -Y, left = +X)."""
import math
from mathutils import Vector, Matrix, Quaternion
from buddy_rig import P, ordered, retarget, key_frames


def R(axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg))


def pose_from_joints(rig, rest, J, root_offset=Vector(), yaw=0.0, pivot=None):
    """J: {bone_short_name: Quaternion} rotations about each joint, in the character frame.
    Root yaw is applied about `pivot` (default: the hips head). Returns {bone: armature-space matrix}."""
    Ry = R((0, 0, 1), yaw)
    desired, T = {}, {}
    for name in ordered(rig):
        b = rig.data.bones[name]
        h_rest = rest[name].translation
        if b.parent is None:
            pv = pivot if pivot is not None else h_rest
            Tp = Matrix.Translation(Vector(root_offset)) @ Matrix.Translation(pv) @ Ry.to_matrix().to_4x4() @ Matrix.Translation(-pv)
        else:
            Tp = T[b.parent.name]
        h = Tp @ h_rest
        q = J.get(name[len(P):])
        if q is not None:
            qw = Ry @ q @ Ry.inverted()
            Tb = Matrix.Translation(h) @ qw.to_matrix().to_4x4() @ Matrix.Translation(-h) @ Tp
        else:
            Tb = Tp
        T[name] = Tb
        desired[name] = Tb @ rest[name]
    return desired


def idle_joints(t=0.0, arm_down=74.0):
    """Relaxed stand like the reference sheet: arms hang beside the body, slight elbow bend."""
    breathe = math.sin(2 * math.pi * t) * 1.2
    return {
        'LeftArm': R((1, 0, 0), -4) @ R((0, 1, 0), arm_down), 'RightArm': R((1, 0, 0), -4) @ R((0, 1, 0), -arm_down),
        'LeftForeArm': R((1, 0, 0), -14), 'RightForeArm': R((1, 0, 0), -14),
        'LeftHand': R((0, 1, 0), 6), 'RightHand': R((0, 1, 0), -6),
        'Spine1': R((1, 0, 0), breathe * 0.4), 'Spine2': R((1, 0, 0), -breathe * 0.3),
        'LeftUpLeg': R((0, 1, 0), -2), 'RightUpLeg': R((0, 1, 0), 2),
    }


def blend(a, b, t):
    out = {}
    for k in a:
        qa, qb = a[k].to_quaternion(), b[k].to_quaternion()
        m = qa.slerp(qb, t).to_matrix().to_4x4()
        m.translation = a[k].translation.lerp(b[k].translation, t)
        out[k] = m
    return out


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def subtree(rig, root_short):
    names = []
    def walk(b):
        names.append(b.name)
        for c in b.children:
            walk(c)
    walk(rig.data.bones[P + root_short])
    return names


def rotate_subtree(desired, rig, root_short, q):
    """Rotate a bone chain about its posed joint (world axes)."""
    p = desired[P + root_short].translation.copy()
    M = Matrix.Translation(p) @ q.to_matrix().to_4x4() @ Matrix.Translation(-p)
    for n in subtree(rig, root_short):
        desired[n] = M @ desired[n]


def apply_all(desired, M):
    return {k: M @ v for k, v in desired.items()}


# ------------------------------------------------------------------ panic: startle, turn around, flee
def startle_joints(k):
    """k: 0..1 intensity. Hands fly up beside the head, torso recoils, head tilts back."""
    def lerpq(q):
        return Quaternion().slerp(q, k)
    return {
        'LeftArm': lerpq(R((1, 0, 0), -12) @ R((0, 1, 0), -38)), 'RightArm': lerpq(R((1, 0, 0), -12) @ R((0, 1, 0), 38)),
        'LeftForeArm': lerpq(R((0, 1, 0), -78)), 'RightForeArm': lerpq(R((0, 1, 0), 78)),
        'LeftHand': lerpq(R((0, 1, 0), -12)), 'RightHand': lerpq(R((0, 1, 0), 12)),
        'Spine1': lerpq(R((1, 0, 0), -8)), 'Spine2': lerpq(R((1, 0, 0), -5)), 'Neck': lerpq(R((1, 0, 0), -7)),
    }


def merge(a, b):
    """Combine two joint dicts (b applied after a for shared joints)."""
    out = dict(a)
    for k, q in b.items():
        out[k] = q @ out[k] if k in out else q
    return out


def scale_joints(J, k):
    return {n: Quaternion().slerp(q, k) for n, q in J.items()}


def step_joints(side, k):
    """Knee lift for a shuffle step during the turn (k: 0..1)."""
    return {side + 'UpLeg': Quaternion().slerp(R((1, 0, 0), -48), k), side + 'Leg': Quaternion().slerp(R((1, 0, 0), 78), k),
            side + 'Foot': Quaternion().slerp(R((1, 0, 0), -12), k)}


def bump(f, center, width):
    x = (f - center) / width
    return max(0.0, 1 - x * x) ** 2


def flail(desired, rig, phase, amount=1.0, raise_deg=118.0):
    """Panic arms: both arms raised high and waving out of phase (character frame, before the turn yaw)."""
    for side, s, ph in (('Left', 1, 0.0), ('Right', -1, math.pi)):
        theta = (raise_deg + 24 * math.sin(phase + ph)) * amount
        wave = 20 * math.sin(phase * 1.0 + ph + 1.1) * amount
        rotate_subtree(desired, rig, side + 'Arm', R((1, 0, 0), wave) @ R((0, 1, 0), -s * theta))
        rotate_subtree(desired, rig, side + 'ForeArm', R((0, 1, 0), -s * 28 * amount * (0.6 + 0.4 * math.sin(phase * 2 + ph))))


RUN_PERIOD = 18          # frames per running cycle (two steps) at 30 fps
RUN_SPEED = 3.2         # m/s


def run_joints(k, look=0.0):
    """Cartoon panic run in the character frame. k: frame index; look: -1..1 head turn back over a shoulder."""
    phi = 2 * math.pi * k / RUN_PERIOD
    J = {}
    for side, ph in (('Left', 0.0), ('Right', math.pi)):
        a = phi + ph
        hip = 38 * math.sin(a)                                   # thigh forward (+) / back (-)
        swing = max(0.0, math.cos(a))
        knee = 16 + 84 * swing ** 1.3
        foot = 22 * swing - 12 * max(0.0, -math.cos(a))
        J[side + 'UpLeg'] = R((1, 0, 0), -hip)
        J[side + 'Leg'] = R((1, 0, 0), knee)
        J[side + 'Foot'] = R((1, 0, 0), -foot)
    J['Hips'] = R((0, 0, 1), 7 * math.sin(phi))
    J['Spine'] = R((1, 0, 0), 13) @ R((0, 0, 1), -9 * math.sin(phi))
    J['Spine1'] = R((1, 0, 0), 4)
    J['Neck'] = R((1, 0, 0), -12) @ R((0, 0, 1), 70 * look)
    J['Head'] = R((0, 0, 1), 35 * look) @ R((1, 0, 0), -4 * abs(look))
    psi = 2 * math.pi * k / (RUN_PERIOD / 2)                    # two flails per cycle
    for side, s, ph in (('Left', 1, 0.0), ('Right', -1, math.pi)):
        theta = 48 + 22 * math.sin(psi + ph)                    # degrees above the T-pose horizontal: up and out
        wave = 22 * math.sin(psi + ph + 1.2)
        J[side + 'Arm'] = R((1, 0, 0), wave) @ R((0, 1, 0), -s * theta)
        J[side + 'ForeArm'] = R((0, 1, 0), -s * (20 + 16 * math.sin(psi * 1.0 + ph + 0.6)))
        J[side + 'Hand'] = R((0, 1, 0), -s * 10 * math.sin(psi + ph))
    bob = 0.028 * math.cos(2 * phi) - 0.012
    return J, bob


def build_panic(rig, rest, fps=30):
    """Returns {action_name: {frame: desired}}.
    Panic_TurnFlee: idle 1-10, startle 10-18, 180-degree turn 18-32, blend into the run 32-40, flee to 150
    (root motion, runs toward +Y, glances back twice). Panic_Run_Loop: the frightened run in place (18 frames, loops).
    Idle: 60-frame breathing loop."""
    out = {}
    out['Idle'] = {f: pose_from_joints(rig, rest, idle_joints((f - 1) / 60.0)) for f in range(1, 61)}
    loop = {}
    for f in range(1, RUN_PERIOD + 1):
        J, bob = run_joints(f - 1)
        loop[f] = pose_from_joints(rig, rest, J, root_offset=Vector((0, 0, bob)))
    out['Panic_Run_Loop'] = loop

    frames = {}
    for f in range(1, 33):
        J = idle_joints((f - 1) / 60.0)
        root = Vector()
        yaw = 0.0
        if f >= 10:
            crouch = bump(f, 12, 2.2) * 0.75
            jump = bump(f, 14.5, 2.5)
            land = bump(f, 17, 2.0)
            J = merge(J, startle_joints(min(1.0, (f - 10) / 4.0)))
            root = Vector((0, 0, 0.045 * jump - 0.028 * crouch - 0.022 * land))
            bend = max(crouch, land)
            J = merge(J, {'LeftUpLeg': R((1, 0, 0), -16 * bend), 'RightUpLeg': R((1, 0, 0), -16 * bend),
                          'LeftLeg': R((1, 0, 0), 30 * bend), 'RightLeg': R((1, 0, 0), 30 * bend),
                          'LeftFoot': R((1, 0, 0), -14 * bend), 'RightFoot': R((1, 0, 0), -14 * bend)})
        if f >= 18:
            t = smooth((f - 18) / 14.0)
            yaw = 180.0 * t
            J = merge(J, step_joints('Left', bump(f, 21.5, 3.0)))
            J = merge(J, step_joints('Right', bump(f, 27.5, 3.0)))
            J = merge(J, {'Spine': R((1, 0, 0), 12 * t)})
            for side, s, ph in (('Left', 1, 0.0), ('Right', -1, math.pi)):
                a = 30 * math.sin(2 * math.pi * (f - 18) / 9.0 + ph) * smooth((f - 18) / 6.0)
                J = merge(J, {side + 'Arm': R((0, 1, 0), -s * a)})
            root = root + Vector((0, 0, 0.018 * (bump(f, 21.5, 3.0) + bump(f, 27.5, 3.0))))
        frames[f] = pose_from_joints(rig, rest, J, root_offset=root, yaw=yaw)

    # Flee toward +Y (the way he now faces), accelerating over the first steps; two glances back.
    dist = 0.0
    for f in range(33, 151):
        k = f - 33
        speed = RUN_SPEED * smooth(k / 10.0) * 0.85 + RUN_SPEED * 0.15
        dist += speed / fps
        look = bump(f, 78, 9) * 1.0 - bump(f, 122, 9) * 1.0
        J, bob = run_joints(k, look)
        run = pose_from_joints(rig, rest, J, root_offset=Vector((0, dist, bob)), yaw=180.0)
        frames[f] = blend(frames[32], run, smooth((f - 32) / 8.0)) if f <= 40 else run
    out['Panic_TurnFlee'] = frames
    return out


def face_keys(face, action_name='Panic_TurnFlee_Face'):
    """Expression track for the panic clip (kept in the .blend; the game drives blend shapes itself)."""
    import bpy
    key = face.data.shape_keys
    key.animation_data_create()
    act = bpy.data.actions.new(action_name); act.use_fake_user = True
    key.animation_data.action = act
    kb = key.key_blocks
    def k(name, f, v):
        kb[name].value = v; kb[name].keyframe_insert('value', frame=f)
    for name in ('Blink', 'Surprised', 'Worried', 'Happy'):
        k(name, 1, 0.0)
    k('Surprised', 10, 0.0); k('Surprised', 13, 1.0); k('Surprised', 28, 1.0); k('Surprised', 38, 0.0)
    k('Worried', 28, 0.0); k('Worried', 38, 1.0); k('Worried', 150, 1.0)
    k('Surprised', 70, 0.0); k('Surprised', 76, 0.8); k('Surprised', 86, 0.0)
    k('Surprised', 114, 0.0); k('Surprised', 120, 0.8); k('Surprised', 130, 0.0)
    k('Blink', 9, 0.0); k('Blink', 11, 1.0); k('Blink', 13, 0.0)
    k('Blink', 88, 0.0); k('Blink', 90, 1.0); k('Blink', 92, 0.0)
    for name in ('Blink', 'Surprised', 'Worried', 'Happy'):
        kb[name].value = 0.0
    return act
