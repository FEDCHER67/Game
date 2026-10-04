"""Mixamo 65-bone skeleton fitted to the Sausage Buddy, plus motion retargeting helpers.
The source skeleton and clip are read from the original Mixamo FBX; names, parents and bone rolls are kept,
so any Mixamo animation exported 'without skin' plays on this rig."""
import bpy
from mathutils import Vector, Matrix, Quaternion

P = 'mixamorig:'


def import_source(fbx_path):
    existing = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx_path), ignore_leaf_bones=False, automatic_bone_orientation=False)
    imported = [o for o in bpy.data.objects if o not in existing]
    src = next(o for o in imported if o.type == 'ARMATURE')
    return src, imported


def sample_motion(scene, src):
    act = src.animation_data.action
    start, end = (int(round(x)) for x in act.frame_range)
    rest = {b.name: src.matrix_world @ b.matrix_local for b in src.data.bones}
    motion = {}
    for f in range(start, end + 1):
        scene.frame_set(f)
        motion[f] = {pb.name: src.matrix_world @ pb.matrix for pb in src.pose.bones}
    return rest, motion, (start, end)


def fit_rig(collection, src, src_rest, joints, name='Buddy_Rig_Mixamo65'):
    data = src.data.copy(); data.name = name
    rig = bpy.data.objects.new(name, data)
    collection.objects.link(rig)
    data.display_type = 'STICK'; rig.show_in_front = True
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    names = {eb.name for eb in data.edit_bones}
    assert names == set(joints), (names ^ set(joints))
    for eb in data.edit_bones:
        eb.use_connect = False
        eb.head, eb.tail = joints[eb.name]
        eb.align_roll(src_rest[eb.name].to_3x3().col[2].normalized())
        eb.use_deform = not (eb.name.endswith(('4', '_End')) or 'Pinky' in eb.name)
    bpy.ops.object.mode_set(mode='OBJECT')
    rest = {b.name: b.matrix_local.copy() for b in data.bones}
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return rig, rest


def ordered(rig):
    out = []
    def walk(b):
        out.append(b.name)
        for c in b.children:
            walk(c)
    for b in rig.data.bones:
        if b.parent is None:
            walk(b)
    return out


def retarget(motion, src_rest, rest, rig, stride_scale, inplace, finger_scale=0.0):
    """World-space delta transfer: target = source_pose * source_rest^-1 * target_rest (rotations);
    hips translation scaled by the leg-length ratio. Returns {frame: {bone: armature-space matrix}}."""
    root = P + 'Hips'
    order = ordered(rig)
    first = min(motion)
    first_root = motion[first][root].translation.copy()
    out = {}
    for f, mats in motion.items():
        desired = {}
        for name in order:
            rot = (mats[name].to_quaternion() @ src_rest[name].to_quaternion().inverted() @ rest[name].to_quaternion()).normalized()
            if finger_scale < 1.0 and any(d in name for d in ('HandIndex', 'HandMiddle', 'HandRing', 'HandPinky')):
                parent = rig.data.bones[name].parent.name
                # keep a fraction of the source finger curl relative to the parent (cartoon mitten fingers)
                prot = desired[parent].to_quaternion()
                rel_target = rest[parent].to_quaternion().inverted() @ rest[name].to_quaternion()
                straight = (prot @ rel_target).normalized()
                rot = straight.slerp(rot, finger_scale)
            if name == root:
                delta = (mats[name].translation - src_rest[name].translation) * stride_scale
                if inplace:
                    delta.x = 0.0; delta.y = 0.0
                else:
                    delta.x -= (first_root.x - src_rest[name].translation.x) * stride_scale
                    delta.y -= (first_root.y - src_rest[name].translation.y) * stride_scale
                pos = rest[name].translation + delta
            else:
                parent = rig.data.bones[name].parent.name
                pos = (desired[parent] @ (rest[parent].inverted() @ rest[name])).translation
            m = rot.to_matrix().to_4x4(); m.translation = pos
            desired[name] = m
        out[f] = desired
    return out


def key_frames(rig, rest, frames, action_name, linear=True):
    """frames: {frame: {bone: armature-space matrix}} -> new action with quaternion keys (+ hips location)."""
    act = bpy.data.actions.new(action_name)
    rig.animation_data_create()
    rig.animation_data.action = act
    order = ordered(rig)
    prev = {}
    for f in sorted(frames):
        desired = frames[f]
        for name in order:
            pb = rig.pose.bones[name]
            kw = {} if not pb.parent else {'parent_matrix': desired[pb.parent.name], 'parent_matrix_local': rest[pb.parent.name]}
            basis = pb.bone.convert_local_to_pose(desired[name], rest[name], invert=True, **kw)
            q = basis.to_quaternion()
            if name in prev and prev[name].dot(q) < 0:
                q.negate()
            prev[name] = q.copy()
            pb.rotation_quaternion = q
            pb.keyframe_insert('rotation_quaternion', frame=f, group=name)
            if not pb.parent:
                pb.location = basis.translation
                pb.keyframe_insert('location', frame=f, group=name)
    if linear:
        for fc in fcurves_of(act):
            for k in fc.keyframe_points:
                k.interpolation = 'LINEAR'
    act.use_fake_user = True
    return act


def fcurves_of(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        pass
    out = []
    for layer in act.layers:
        for strip in layer.strips:
            for slot in act.slots:
                cb = strip.channelbag(slot)
                if cb:
                    out += list(cb.fcurves)
    return out


def ground_offset(scene, rig, act, meshes, frames):
    """Lowest mesh point over the clip -> offset so the shoes touch z=0."""
    rig.animation_data.action = act
    dg = bpy.context.evaluated_depsgraph_get()
    lows = []
    for f in frames:
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        low = 1e9
        for o in meshes:
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            for v in me.vertices:
                z = (o.matrix_world @ v.co).z
                if z < low:
                    low = z
            ev.to_mesh_clear()
        lows.append(low)
    return lows
