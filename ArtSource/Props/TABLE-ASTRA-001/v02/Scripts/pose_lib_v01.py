"""TABLE_REST pose library: FK posing of Buddy_Rig_Mixamo65 by bone rotations only, plus contact metrics.

Rotations are given as deltas L_b in the armature's REST axes (standing T-pose: +Z up, -Y front, +X patient left),
relative to the parent. Pose basis = Rest_b^-1 * L_b * Rest_b, so rest pose / bone lengths are never touched.
The armature object sits at the PatientRest point on the pad (table-local location (0, Y, padTop), rotation Rz 180),
so in armature space the lying body has its head toward +Y and its face toward +Z (same as GetUp_FromBack_v03).
"""
import math

import bpy
from mathutils import Matrix, Quaternion, Vector

from v02_common import P, rx, ry, rz, q_axis

REGION_OF_BONE = {}
for side in ("Left", "Right"):
    REGION_OF_BONE.update({
        P + side + "Shoulder": "upper_back", P + side + "Arm": "upper_arm", P + side + "ForeArm": "forearm",
        P + side + "Hand": "hand", P + side + "UpLeg": "thigh", P + side + "Leg": "calf",
        P + side + "Foot": "foot", P + side + "ToeBase": "foot", P + side + "Toe_End": "foot"})
    for f in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
        for i in range(1, 5):
            REGION_OF_BONE[P + side + "Hand" + f + str(i)] = "hand"
REGION_OF_BONE.update({P + "Hips": "pelvis", P + "Spine": "mid_back", P + "Spine1": "mid_back",
                       P + "Spine2": "upper_back", P + "Neck": "head", P + "Head": "head",
                       P + "HeadTop_End": "head"})

DEFAULT = {
    # root placement on the table (table-local metres); rig yaw is fixed at 180 deg.
    "root_y": 0.0,
    "pad_z": 0.66,
    # hips
    "hips_tilt": 0.0,        # + = head end up (deg)
    "hips_y": 0.0,           # hips head offset along armature +Y (toward the head) from the root (m)
    "hips_h": 0.12,          # hips head height above the root (m)
    "spine": (0.0, 0.0, 0.0),   # Spine, Spine1, Spine2 flexion (+ = curl up off the pad)
    "neck": 0.0, "head": 0.0,  # flexion (+ = chin toward chest)
    "head_turn": 0.0,          # yaw of the head (deg, + = toward patient's left)
    "shoulder_down": 0.0,      # clavicle depression (deg)
    "arm_down": 84.0,          # adduction from T-pose (90 = vertical)
    "arm_back": 12.0,          # shoulder extension toward the pad (deg)
    "arm_twist": 0.0,          # + = pronation of the whole arm (deg)
    "elbow": 12.0,             # elbow flexion (deg)
    "wrist": 0.0,              # wrist flexion (deg)
    "wrist_dev": 0.0,          # wrist deviation (deg)
    "finger_curl": 14.0,
    "thumb_curl": 10.0,
    "leg_back": 0.0,           # hip extension toward the pad (deg)
    "leg_spread": 0.0,         # abduction per leg (deg)
    "leg_out": 0.0,            # external rotation per leg (deg)
    "knee": 2.0,
    "foot": 18.0,              # plantar flexion (deg)
    "toe": 0.0,
}


def rest_rot(rig, name):
    return rig.data.bones[name].matrix_local.to_3x3().to_quaternion()


def set_local(rig, name, L):
    """Set pose rotation so the bone's delta (relative to parent, in rest armature axes) equals quaternion L."""
    R = rest_rot(rig, name)
    pb = rig.pose.bones[name]
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = (R.inverted() @ L @ R).normalized()


def apply_pose(rig, prm):
    p = dict(DEFAULT)
    p.update(prm)
    for pb in rig.pose.bones:
        pb.matrix_basis.identity()
        pb.rotation_mode = "QUATERNION"
    # Hips: lay down (rest +Z -> armature +Y, rest -Y (front) -> +Z), then tilt the head end up.
    L_hips = rx(-90.0 + p["hips_tilt"])
    set_local(rig, P + "Hips", L_hips)
    hips = rig.pose.bones[P + "Hips"]
    bpy.context.view_layer.update()
    # location: put the hips head at (0, hips_y, hips_h) in armature space
    target = Vector((0.0, p["hips_y"], p["hips_h"]))
    rest_head = rig.data.bones[P + "Hips"].head_local
    R = rest_rot(rig, P + "Hips")
    hips.location = R.inverted() @ (target - rest_head)
    s1, s2, s3 = p["spine"]
    set_local(rig, P + "Spine", rx(s1))
    set_local(rig, P + "Spine1", rx(s2))
    set_local(rig, P + "Spine2", rx(s3))
    set_local(rig, P + "Neck", rx(p["neck"]))
    set_local(rig, P + "Head", rz(p["head_turn"]) @ rx(p["head"]))
    for side, sgn in (("Left", 1.0), ("Right", -1.0)):
        # clavicle depression: rotate the shoulder bone tip downward about the front-back axis
        set_local(rig, P + side + "Shoulder", ry(sgn * p["shoulder_down"]))
        # arm: adduct down (about rest Y), then swing back toward the pad (about rest X), twist about the bone
        twist = q_axis((sgn, 0, 0), p["arm_twist"])
        set_local(rig, P + side + "Arm", rx(p["arm_back"]) @ ry(sgn * p["arm_down"]) @ twist)
        # elbow flexion (forearm toward the rest front -Y)
        set_local(rig, P + side + "ForeArm", rz(-sgn * p["elbow"]))
        # wrist: flexion toward the palm (rest palm faces -Z), deviation toward the thumb side (-Y)
        set_local(rig, P + side + "Hand", rz(-sgn * p["wrist_dev"]) @ ry(sgn * p["wrist"]))
        for f in ("Index", "Middle", "Ring", "Pinky"):
            for i in (1, 2, 3):
                set_local(rig, P + side + "Hand" + f + str(i), ry(sgn * p["finger_curl"] * (1.0 + 0.25 * (i - 1))))
        for i in (1, 2, 3):
            set_local(rig, P + side + "HandThumb" + str(i), ry(sgn * p["thumb_curl"]) @ rz(sgn * p["thumb_curl"] * 0.5))
        # leg: extension toward the pad (+X rot moves the leg to rest +Y = back), spread, external rotation
        set_local(rig, P + side + "UpLeg", rz(sgn * p["leg_out"]) @ ry(-sgn * p["leg_spread"]) @ rx(p["leg_back"]))
        set_local(rig, P + side + "Leg", rx(p["knee"]))
        set_local(rig, P + side + "Foot", rx(p["foot"]))
        set_local(rig, P + side + "ToeBase", rx(p["toe"]))
    bpy.context.view_layer.update()
    return p


def place_rig(rig, p):
    rig.location = (0.0, p["root_y"], p["pad_z"])
    rig.rotation_mode = "XYZ"
    rig.rotation_euler = (0.0, 0.0, math.pi)
    rig.scale = (1, 1, 1)
    bpy.context.view_layer.update()


def vertex_regions(ob):
    """Region label per vertex by dominant deform weight (rest-pose head split into cap / back of head)."""
    names = {g.index: g.name for g in ob.vertex_groups}
    out = []
    for v in ob.data.vertices:
        best, bw = None, -1.0
        for g in v.groups:
            if g.weight > bw:
                best, bw = names.get(g.group), g.weight
        r = REGION_OF_BONE.get(best, "other")
        if ob.name == "Shorts":
            r = "shorts"
        elif ob.name == "Face":
            r = "face"
        elif r == "head":
            r = "head_cap" if v.co.z < 1.30 else "head_back"
        out.append(r)
    return out


def pad_height_fn(pad_bvh):
    def h(x, y):
        hit = pad_bvh.ray_cast(Vector((x, y, 3.0)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] is not None else None
    return h


def contact_metrics(objs, pad_bvh, regions):
    """Per-region minimum gap above the pad (m). Negative = penetration. 'off' counts vertices with no pad below."""
    dg = bpy.context.evaluated_depsgraph_get()
    h = pad_height_fn(pad_bvh)
    res = {}
    offpad = 0
    for name, ob in objs.items():
        eo = ob.evaluated_get(dg)
        me = eo.to_mesh()
        mw = ob.matrix_world
        reg = regions[name]
        for i, v in enumerate(me.vertices):
            w = mw @ v.co
            z = h(w.x, w.y)
            if z is None:
                offpad += 1
                continue
            g = w.z - z
            key = reg[i]
            r = res.setdefault(key, [1e9, None])
            if g < r[0]:
                r[0] = g
                r[1] = (round(w.x, 3), round(w.y, 3), round(w.z, 3))
        eo.to_mesh_clear()
    return {k: (round(v[0] * 1000, 1), v[1]) for k, v in sorted(res.items())}, offpad
