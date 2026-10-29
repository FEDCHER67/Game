"""MECHANIC_W86 wrench v02: the rifle-sized double open-ended spanner (Fedya 2026-10-29: "much bigger, like an assault
rifle, ~0.80-0.90 m") and the model files that carry it. Blender 5.2, background.

  blender -b --factory-startup --python ArtSource/Characters/MECHANIC_W86/mechanic_w86_wrench_v02.py -- --build

--build writes here (never over existing files):
  MECHANIC_W86_v02.blend         = MECHANIC_W86_v01.blend with the v02 wrench (the animation source, LOD0 only)
  MECHANIC_W86_v02_opt_v02.blend = MECHANIC_W86_v01_opt_v02.blend with the v02 wrench in LOD0/1/2
  MECHANIC_W86_v02_opt_v02.fbx   = its game FBX (the opt_v02 export: rig + Body/Face/Outfit/Wrench_RightHand _LOD0/1/2,
                                   the Idle clip only, the same export options)
  wrench_MECHANIC_W86_v02.json   = layout, triangles, checks
Everything except the Wrench_RightHand meshes is the v01 data unchanged (same objects, weights, materials, shape keys).

The wrench (RightHand bone space, rigid on mixamorig:RightHand like v01; mesh name Wrench_RightHand, so NpcHeldProps
never drops it): 0.85 m long, one open jaw at each end in one plane (the v01 style, heavier), a beefy shank with a slimmer
grip section under the right fist and a support section just behind the front jaw for the left palm.
Why the grip is oblique: v01/v02 held the shank square to the hand (through the fist along the knuckle line). With this
rig's short arms (upper arm 0.23 m, forearm 0.21 m) a square grip cannot put the backward extension of a horizontal
wrench on the right upper arm unless the wrist bends ~60 deg (v02 measured 43 deg deviation + 63 deg flexion): the
forearm + hand stand 0.27-0.29 m off the axis and only 0.23 m of upper arm can bring them back to it. Turning the shank
45 deg in the palm (the pinky-side end toward the fingers, as a rifle's pistol grip sets the hand) lets the forearm come
up from the elbow at ~45 deg to the wrench with a straight wrist, like the reference photo. The front (long) part leaves
the fist on the pinky side, the rear jaw sits just past the thumb (toward the shoulder in the aim). The finger pose
that closes the mitten round the oblique grip is GRIP_V02 (Grip_R v02; mitten-vs-shank checked: no finger vertex
inside the grip section).
"""
import argparse, json, math, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import mech_rig as MR   # noqa: E402  (sets the SAUSAGE_BUDDY_01 path)

P = MR.P
WRENCH = 'Wrench_RightHand'
# ------------------------------------------------------------------ layout (RightHand bone space, metres)
DELTA = 45.0                                    # shank turned in the palm (deg), pinky-side end toward the fingers
CENTRE = Vector((0.0054, 0.1004, 0.0548))       # the grip centre in the closed GRIP_V02 fist
AXIS = Vector((-math.cos(math.radians(DELTA)), math.sin(math.radians(DELTA)), 0.0))   # rear -> front (front = pinky side)
NORMAL = Vector((0.0, 0.0, 1.0))                # the spanner plane = the palm plane (as v01)
FRONT_END, REAR_END = 0.604, -0.244             # along AXIS from CENTRE (jaw tips): 0.848 m overall
FRONT_JAW = dict(u=0.520, R=0.084, slot=0.032, half=0.0145, open_deg=15.0)
REAR_JAW = dict(u=-0.178, R=0.066, slot=0.025, half=0.0135, open_deg=15.0)
GRIP = (-0.068, 0.068)                          # the right fist's section (u)
SUPPORT_U = 0.335                               # the left palm centre (u); the slim support section 0.288..0.410
# shank sections (u, in-plane half width, half thickness)
SHANK = [(-0.140, 0.030, 0.0125), (-0.110, 0.022, 0.0120), (-0.088, 0.0165, 0.0112), (-0.068, 0.0135, 0.0110),
         (0.000, 0.0135, 0.0110), (0.068, 0.0135, 0.0110), (0.095, 0.0200, 0.0130), (0.150, 0.0245, 0.0142),
         (0.215, 0.0250, 0.0145), (0.262, 0.0230, 0.0135), (0.288, 0.0190, 0.0122), (0.345, 0.0185, 0.0120),
         (0.410, 0.0190, 0.0122), (0.436, 0.0250, 0.0135), (0.468, 0.0420, 0.0140)]
# Grip_R v02: finger curl per segment (deg) and thumb rotations, mech_rig.HAND_POSES format (found by a mitten-vs-shank
# search: no finger vertex inside the grip section, 27 vertices within 4 mm of it)
GRIP_V02 = dict(fingers=(0.0, 44.76, 29.96), thumb=(((1, 0, 0), 32.44), ((1, 0, 0), -8.20), ((1, 0, 0), 28.24)))
LOD_RES = {0: dict(seg=12, arc=22, slot=6), 1: dict(seg=8, arc=12, slot=3), 2: dict(seg=6, arc=7, slot=2)}


def frame():
    a = AXIS.normalized()
    n = (NORMAL - a * NORMAL.dot(a)).normalized()
    w = n.cross(a).normalized()
    return a, n, w


def point(u):
    """Bone-space point on the wrench axis."""
    return CENTRE + AXIS.normalized() * u


def section(u):
    """Shank cross-section at u: (in-plane half width, half thickness), linear between the SHANK rings."""
    if u <= SHANK[0][0]:
        return SHANK[0][1:]
    for (u0, w0, t0), (u1, w1, t1) in zip(SHANK, SHANK[1:]):
        if u <= u1:
            k = (u - u0) / (u1 - u0)
            return w0 + (w1 - w0) * k, t0 + (t1 - t0) * k
    return SHANK[-1][1:]


# ------------------------------------------------------------------ geometry (the v01 style: open jaws, slab heads)
def _jaw_outline(c, a, w, R, hw, open_deg, n_arc=22, n_slot=6):
    """Open spanner end (as mechanic_w86_type._jaw_outline): a disc of radius R round c with a parallel slot of half
    width hw opening along a turned by open_deg; points counter-clockwise in the a/w plane."""
    d = (a * math.cos(math.radians(open_deg)) + w * math.sin(math.radians(open_deg))).normalized()
    e = (w * math.cos(math.radians(open_deg)) - a * math.sin(math.radians(open_deg))).normalized()
    t = math.sqrt(R * R - hw * hw)
    ang = lambda p: math.atan2((p - c).dot(e), (p - c).dot(d))
    p1, p2 = c + d * t + e * hw, c + d * t - e * hw
    a1, a2 = ang(p1), ang(p2) + 2 * math.pi
    pts = [c + (d * math.cos(a1 + (a2 - a1) * k / n_arc) + e * math.sin(a1 + (a2 - a1) * k / n_arc)) * R for k in range(n_arc + 1)]
    bottom = c - d * 0.004
    pts.append(bottom - e * hw)
    for k in range(1, n_slot):
        th = -math.pi / 2 - math.pi * k / n_slot
        pts.append(bottom + (d * math.cos(th) * 0.9 + e * math.sin(th)) * hw)
    pts.append(bottom + e * hw)
    return pts


def _slab(bm, pts, nrm, half):
    top = [bm.verts.new(p + nrm * half) for p in pts]
    bot = [bm.verts.new(p - nrm * half) for p in pts]
    f1 = bm.faces.new(top)
    f2 = bm.faces.new(list(reversed(bot)))
    n = len(pts)
    side = [bm.faces.new((bot[k], bot[(k + 1) % n], top[(k + 1) % n], top[k])) for k in range(n)]
    return [f1, f2], side


def _loft(bm, sections, seg):
    rings = []
    for c, w, n, hw, ht in sections:
        rings.append([bm.verts.new(c + w * (hw * math.cos(2 * math.pi * j / seg)) + n * (ht * math.sin(2 * math.pi * j / seg)))
                      for j in range(seg)])
    faces = []
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(seg):
            faces.append(bm.faces.new((r0[j], r0[(j + 1) % seg], r1[(j + 1) % seg], r1[j])))
    caps = [bm.faces.new(list(reversed(rings[0]))), bm.faces.new(rings[-1])]
    return faces, caps


def wrench_bmesh(level=0):
    """The v02 wrench in RightHand bone space (one bmesh: shank + two jaw slabs, interpenetrating like v01's parts)."""
    res = LOD_RES[level]
    a, n, w = frame()
    bm = bmesh.new()
    shank = SHANK if level == 0 else [s for i, s in enumerate(SHANK) if i not in ((1, 4, 8, 11) if level == 1 else (1, 2, 4, 6, 8, 9, 11, 12))]
    faces, caps = _loft(bm, [(point(u), w, n, hw, ht) for u, hw, ht in shank], res['seg'])
    ngons = list(caps)
    for jaw, sgn in ((FRONT_JAW, 1), (REAR_JAW, -1)):
        pts = _jaw_outline(point(jaw['u']), a * sgn, w * sgn, jaw['R'], jaw['slot'], jaw['open_deg'], res['arc'], res['slot'])
        f, side = _slab(bm, pts, n, jaw['half'])
        ngons += f
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.triangulate(bm, faces=ngons, quad_method='BEAUTY', ngon_method='EAR_CLIP')
    return bm


def replace_wrench(obj_name, level, rest):
    """Swap the mesh of one Wrench_RightHand object for the v02 wrench (armature space at the rest pose), weight 1 on
    mixamorig:RightHand, the object's own material, flat shading (as v01). Returns triangles."""
    o = bpy.data.objects[obj_name]
    mat = o.data.materials[0]
    old = o.data
    bm = wrench_bmesh(level)
    Mr = rest[P + 'RightHand']
    for v in bm.verts:
        v.co = Mr @ v.co
    me = bpy.data.meshes.new(obj_name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    for poly in me.polygons:
        poly.use_smooth = False
        poly.material_index = 0
    o.data = me
    bpy.data.meshes.remove(old)
    me.name = obj_name
    o.vertex_groups.clear()
    vg = o.vertex_groups.new(name=P + 'RightHand')
    vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')
    if not any(m.type == 'ARMATURE' for m in o.modifiers):
        raise RuntimeError(f'{obj_name}: no armature modifier')
    return sum(len(p.vertices) - 2 for p in me.polygons)


def bone_space_extent(obj_name, rest):
    o = bpy.data.objects[obj_name]
    Mi = rest[P + 'RightHand'].inverted()
    a = AXIS.normalized()
    us = [(Mi @ (o.matrix_world @ v.co) - CENTRE).dot(a) for v in o.data.vertices]
    return round(min(us), 4), round(max(us), 4)


def check_hand(rest, rig):
    """The right mitten in the GRIP_V02 pose against the whole wrench (signed, BVH): grip contact, nothing through."""
    from mathutils.bvhtree import BVHTree
    from mathutils import Quaternion
    for pb in rig.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
    loc = MR.hand_locals(rest, 'Right', GRIP_V02)
    for b in MR.hand_children(rig, 'Right'):
        rig.pose.bones[b].rotation_quaternion = loc.get(b, Quaternion())
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    body = bpy.data.objects['Body']
    gi = {g.index: g.name for g in body.vertex_groups}
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    hand = [body.matrix_world @ me.vertices[v.index].co for v in body.data.vertices
            if sum(g.weight for g in v.groups if gi[g.group].startswith(P + 'RightHand')) > 0.5]
    ev.to_mesh_clear()
    wo = bpy.data.objects[WRENCH]
    wm = wo.evaluated_get(dg).to_mesh()
    tree = BVHTree.FromPolygons([wo.matrix_world @ v.co for v in wm.vertices], [tuple(p.vertices) for p in wm.polygons])
    wo.evaluated_get(dg).to_mesh_clear()
    inside, near, deep = 0, 0, 0.0
    for q in hand:
        hit, nor, idx, dist = tree.find_nearest(q)
        if hit is None:
            continue
        s = dist if (q - hit).dot(nor) >= 0 else -dist
        if s < 0 and dist < 0.03:
            inside += 1
            deep = max(deep, dist)
        elif s < 0.004:
            near += 1
    for pb in rig.pose.bones:
        pb.rotation_quaternion = Quaternion()
    return {'hand_verts': len(hand), 'inside': inside, 'deepest_mm': round(deep * 1000, 1), 'within_4mm': near}


def export_opt_fbx(rig, path):
    """build_types_opt_v02.export_fbx with the LOD0 names: rig + every skinned mesh, the Idle clip only."""
    objs = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent is rig]
    for o in objs:
        sk = o.data.shape_keys
        if sk is not None and sk.animation_data:
            sk.animation_data.action = None
    for a in list(bpy.data.actions):
        if a.name.endswith('_Face') or a.name == 'PoliceCall_Phone':
            bpy.data.actions.remove(a)
    for level in (1, 2):
        coll = bpy.data.collections.get(f'LOD{level}')
        if coll:
            coll.hide_viewport = False
            coll.hide_render = False
    for o in objs:
        if '_LOD' not in o.name:
            o.name = o.name + '_LOD0'
            o.data.name = o.name
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for o in [rig] + objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rig
    rig.data.pose_position = 'POSE'
    rig.animation_data.action = bpy.data.actions['Idle']
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 60
    scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'MESH', 'ARMATURE'}, add_leaf_bones=False,
                             use_armature_deform_only=False, bake_anim=True, bake_anim_use_all_actions=False,
                             bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0, axis_forward='-Z', axis_up='Y',
                             apply_unit_scale=True, use_mesh_modifiers=False)
    return sorted(o.name for o in objs)


def build(out=HERE):
    outs = {k: out / f'MECHANIC_W86_v02{k}' for k in ('.blend', '_opt_v02.blend', '_opt_v02.fbx')}
    note = out / 'wrench_MECHANIC_W86_v02.json'
    for p in list(outs.values()) + [note]:
        if p.exists():
            sys.exit(f'Refusing to overwrite {p}')
    rep = {'comment': __doc__.split('\n\n')[2].replace('\n', ' '), 'delta_deg': DELTA, 'centre_bone': list(CENTRE),
           'axis_bone_rear_to_front': [round(x, 5) for x in AXIS], 'front_end_u': FRONT_END, 'rear_end_u': REAR_END,
           'length_m': round(FRONT_END - REAR_END, 3), 'front_jaw': FRONT_JAW, 'rear_jaw': REAR_JAW, 'grip_u': GRIP,
           'support_u': SUPPORT_U, 'grip_pose': {'fingers': GRIP_V02['fingers'], 'thumb': [t[1] for t in GRIP_V02['thumb']]}}
    # 1. animation source
    rig, rest = MR.open_model(HERE / 'MECHANIC_W86_v01.blend')
    rep['tris'] = {'source': replace_wrench(WRENCH, 0, rest)}
    rep['extent_u_source'] = bone_space_extent(WRENCH, rest)
    rep['hand_check'] = check_hand(rest, rig)
    bpy.ops.wm.save_as_mainfile(filepath=str(outs['.blend']))
    # 2. game LODs
    rig, rest = MR.open_model(HERE / 'MECHANIC_W86_v01_opt_v02.blend')
    for level, name in ((0, WRENCH), (1, WRENCH + '_LOD1'), (2, WRENCH + '_LOD2')):
        rep['tris'][f'LOD{level}'] = replace_wrench(name, level, rest)
    bpy.ops.wm.save_as_mainfile(filepath=str(outs['_opt_v02.blend']))
    rep['fbx_objects'] = export_opt_fbx(rig, outs['_opt_v02.fbx'])
    rep['outputs'] = [p.name for p in outs.values()]
    note.write_text(json.dumps(rep, indent=1, default=str), encoding='utf-8')
    print('[WRENCH_V02]', json.dumps(rep, default=str))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--out', default=None)          # scratch output folder (tests); default: this folder
    args, _ = ap.parse_known_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    if args.build:
        build(Path(args.out) if args.out else HERE)
