"""MECHANIC_W86 shared rig helpers: the Grip_R finger pose, hand poses for the free left hand, loading the model and the
shared Sausage Buddy clips, finger overrides on armature-space poses, grounding, face tracks.

Conventions as the whole Sausage Buddy pipeline: Blender 5.2, Z up, the character faces -Y, left = +X, metres, 30 fps,
Mixamo 65-bone rig 'Buddy_Rig_Mixamo65'. A pose is {bone: armature-space 4x4 matrix} (buddy_anim.pose_from_joints).

Grip_R: local rotations of the right-hand finger bones only (Index/Middle/Ring/Pinky 1-3 curl 20/34/24 deg toward the
palm, Thumb 1-3 closing over the shank 35/15/15 deg). Local = relative to the parent bone, so the same values hold in any
arm pose; in Unity it is a 2-frame clip on a masked override layer (see the notes JSON)."""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix, Quaternion

HERE = Path(__file__).resolve().parent
BUDDY = HERE.parent / 'SAUSAGE_BUDDY_01'
for p in (str(BUDDY), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)
sys.dont_write_bytecode = True

P = 'mixamorig:'
RIG = 'Buddy_Rig_Mixamo65'
DIGITS = ('Index', 'Middle', 'Ring', 'Pinky')
SHARED_CLIPS = {      # the game's shared Sausage Buddy roles (Assets/.../SausageBuddy/Animations/clips.json), read only
    'Idle_Stand_v04': BUDDY / 'Animations' / 'Idle_Knock_v03' / 'Idle_Stand_v04.blend',
    'Walk': BUDDY / 'Animations' / 'Locomotion_v02' / 'Walk_v04.blend',
    'Idle_Bored_v03': BUDDY / 'Animations' / 'Idle_Knock_v03' / 'Idle_Bored_v03.blend',
}

# hand poses: per finger segment curl toward the palm (deg) + thumb rotations about character-frame axes (right hand;
# the left hand uses the mirrored axes). Pinky bones have no geometry (mitten hand) but are posed like the ring finger.
HAND_POSES = {
    'grip': dict(fingers=(20, 34, 24), thumb=(((1, 0, 0), 35), ((1, 0, 0), 15), ((1, 0, 0), 15))),     # Grip_R (wrench)
    'relaxed': dict(fingers=(10, 16, 12), thumb=(((1, 0, 0), 8), ((1, 0, 0), 6), ((1, 0, 0), 4))),
    'flat': dict(fingers=(2, 3, 2), thumb=(((0, 0, 1), 4), ((1, 0, 0), 0), ((1, 0, 0), 0))),
    'pinch': dict(fingers=(26, 40, 30), thumb=(((1, 0, 0), 30), ((0, 0, 1), 18), ((1, 0, 0), 12))),      # a small part
    'cup': dict(fingers=(18, 26, 18), thumb=(((1, 0, 0), 18), ((1, 0, 0), 10), ((1, 0, 0), 6))),
    'fist': dict(fingers=(70, 85, 60), thumb=(((1, 0, 0), 40), ((0, 0, 1), 20), ((1, 0, 0), 20))),
    'thumbs_up': dict(fingers=(70, 85, 60), thumb=(((1, 0, 0), -25), ((1, 0, 0), -5), ((1, 0, 0), 0))),
    'point': dict(fingers=(70, 85, 60), thumb=(((1, 0, 0), 30), ((0, 0, 1), 15), ((1, 0, 0), 15)), index=(0, 2, 0)),
}


def hand_locals(rest, side, pose, k=1.0):
    """{bone: local Quaternion} of one hand pose (scaled by k: 0 = straight T-pose fingers)."""
    spec = HAND_POSES[pose] if isinstance(pose, str) else pose
    s = 1 if side == 'Left' else -1
    curl_axis = Vector((0, s, 0))                 # Mixamo T-pose: palms down, fingers curl toward -Z
    out = {}
    for d in DIGITS:
        angles = spec['index'] if (d == 'Index' and 'index' in spec) else spec['fingers']
        for i, a in enumerate(angles):
            b = P + f'{side}Hand{d}{i + 1}'
            ax = (rest[b].to_3x3().inverted() @ curl_axis).normalized()
            out[b] = Quaternion(ax, math.radians(a * k))
    for i, (axis, a) in enumerate(spec['thumb']):
        b = P + f'{side}HandThumb{i + 1}'
        ax = Vector(axis)
        if s > 0:                                     # mirror the right-hand axis (pseudovector) for the left hand
            ax = Vector((ax.x, -ax.y, -ax.z))
        ax = (rest[b].to_3x3().inverted() @ ax).normalized()
        out[b] = Quaternion(ax, math.radians(a * k))
    return out


def blend_locals(a, b, t):
    keys = set(a) | set(b)
    t = max(0.0, min(1.0, t))
    return {k: a.get(k, Quaternion()).slerp(b.get(k, Quaternion()), t) for k in keys}


def hand_children(rig, side):
    out = []
    def walk(bone):
        for c in bone.children:
            out.append(c.name)
            walk(c)
    walk(rig.data.bones[P + side + 'Hand'])
    return out


def set_hand(desired, rig, rest, side, locals_):
    """Override the finger bones of one hand in an armature-space pose with local rotations (parent-relative)."""
    for name in hand_children(rig, side):
        parent = rig.data.bones[name].parent.name
        L = locals_.get(name, Quaternion()).to_matrix().to_4x4()
        desired[name] = desired[parent] @ (rest[parent].inverted() @ rest[name]) @ L
    return desired


def open_model(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects[RIG]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return rig, rest


def append_action(path, name):
    """Copy a shared clip (same rig, same rest) into this file; returns the action."""
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.actions = [name]
    act = dst.actions[0]
    act.use_fake_user = True
    return act


def grip_track(rig, rest, name='Grip_R', frames=(1, 2)):
    """Action keyed on the right-hand finger bones only (the Unity masked override layer clip)."""
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data_create()
    keep = rig.animation_data.action
    rig.animation_data.action = act
    loc = hand_locals(rest, 'Right', 'grip')
    for b in hand_children(rig, 'Right'):
        pb = rig.pose.bones[b]
        pb.rotation_quaternion = loc.get(b, Quaternion())
        for f in frames:
            pb.keyframe_insert('rotation_quaternion', frame=f, group=b)
    rig.animation_data.action = keep
    return act


def nla_grip(rig, base_action, grip_action):
    """Preview the Unity setup in Blender: the base clip on the lower NLA track, Grip_R on a REPLACE strip above it
    (only the right-hand finger bones are keyed in Grip_R, so everything else comes from the base clip)."""
    ad = rig.animation_data_create()
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    ad.action = None
    f0, f1 = base_action.frame_range
    t1 = ad.nla_tracks.new()
    t1.name = 'Base'
    s1 = t1.strips.new(base_action.name, int(f0), base_action)
    s1.extrapolation = 'HOLD'
    t2 = ad.nla_tracks.new()
    t2.name = 'Grip_R_layer'
    s2 = t2.strips.new('Grip_R', int(f0), grip_action)
    s2.blend_type = 'REPLACE'
    s2.extrapolation = 'HOLD'
    s2.scale = max(1.0, (f1 - f0) / 1.0)
    return t2


def clear_nla(rig):
    ad = rig.animation_data_create()
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)


def meshes_lod0():
    return [o for o in bpy.data.objects if o.type == 'MESH' and o.parent is not None and o.parent.name == RIG
            and '_LOD' not in o.name and o.name != 'Wrench_RightHand' and not o.name.startswith('Prop_')]
