"""Export the Buddy rig (and a skinned mesh proxy) to plain JSON so work can continue without Git LFS.

blender -b --factory-startup --python export_rig_json_v03.py
Reads ../../SAUSAGE_BUDDY_A_v04.blend (read-only). Writes, refusing to overwrite:
  rig_Buddy_Mixamo65.json      65 bones (order, parents, head/tail/roll/matrix_local, flags), armature object
                               transform, Idle frame-1 pose, rigid hand/shoe contact points, source hashes
  mesh_proxy_Buddy_A_v04.json  Body/Face/Outfit rest vertices, polygons, material slots (flat colours) and
                               vertex-group weights (no UVs, textures or shape keys) for floor checks/renders
Rebuild with rebuild_rig_from_json_v03.py.
"""
from pathlib import Path
import sys, json, hashlib
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bpy
import getup_lib_v03 as L

RIG_JSON = HERE / 'rig_Buddy_Mixamo65.json'
PROXY_JSON = HERE / 'mesh_proxy_Buddy_A_v04.json'
for p in (RIG_JSON, PROXY_JSON):
    assert not p.exists(), 'Refusing overwrite ' + p.name


def r(v, n=6):
    return [round(float(c), n) for c in v]


def m4(m, n=7):
    return [[round(float(m[i][j]), n) for j in range(4)] for i in range(4)]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


rig = L.Rig()  # opens A v04, records Idle frame 1, strips actions (in memory only)
ob = rig.rig
bpy.context.view_layer.objects.active = ob
bpy.ops.object.mode_set(mode='EDIT')
rolls = {eb.name: eb.roll for eb in ob.data.edit_bones}
bpy.ops.object.mode_set(mode='OBJECT')
bones = []
for b in ob.data.bones:
    bones.append({'name': b.name, 'parent': b.parent.name if b.parent else None,
                  'head': r(b.head_local), 'tail': r(b.tail_local), 'roll': round(rolls[b.name], 8),
                  'length': round(b.length, 7), 'matrix_local': m4(b.matrix_local),
                  'use_deform': b.use_deform, 'use_connect': b.use_connect,
                  'inherit_rotation': b.use_inherit_rotation, 'inherit_scale': b.inherit_scale,
                  'use_local_location': b.use_local_location})
# Idle frame 1 as pose-bone basis values (what an action keys) and armature-space matrices.
rig.install(rig.idle)
idle = {}
for pb in ob.pose.bones:
    q = pb.matrix_basis.to_quaternion()
    idle[pb.name] = {'rotation_quaternion': r(q, 8), 'location': r(pb.matrix_basis.translation, 8),
                     'matrix_armature': m4(rig.idle[pb.name])}
src = L.SRC
data = {
    'format': 'Buddy rig JSON v1 (GetUp v03 handoff)',
    'units': 'metres; Blender Z up; character faces -Y; +X = character left; 30 fps',
    'source_blend': 'ArtSource/Characters/SAUSAGE_BUDDY_01/SAUSAGE_BUDDY_A_v04.blend',
    'source_sha256': {n: sha(src / n) for n in ('SAUSAGE_BUDDY_A_v04.blend', 'SAUSAGE_BUDDY_B_v04.blend',
                                                'SAUSAGE_BUDDY_A_v04.fbx', 'SAUSAGE_BUDDY_B_v04.fbx')},
    'note': 'A and B v04 share an identical rest rig (verified by GetUp_Idle_v01/validation_v02.json).',
    'armature_object': {'name': ob.name, 'data_name': ob.data.name, 'matrix_world': m4(ob.matrix_world),
                        'location': r(ob.location), 'rotation_euler': r(ob.rotation_euler),
                        'scale': r(ob.scale), 'rotation_mode': ob.rotation_mode,
                        'pose_position': 'POSE', 'display_type': ob.data.display_type},
    'bone_count': len(bones),
    'bones': bones,
    'dfs_order': rig.order,
    'idle_frame1': {'action': 'Idle (SAUSAGE_BUDDY_A_v04.blend), frame 1',
                    'hips_world': r(rig.idle_hips), 'bones': idle},
    'contact_points_rest_relative': {
        'note': 'Rigid vertex sets used for exact floor contact: hand = Body/Outfit verts with >=95% hand-subtree '
                'weight, relative to the hand (wrist) head; shoe = Outfit verts with >50% Foot+ToeBase weight and '
                'rest z<0.19, relative to the foot (ankle) head.',
        'hand': {s: [r(p, 5) for p in rig.hand_pts[s]] for s in ('Left', 'Right')},
        'shoe': {s: [r(p, 5) for p in rig.shoe_pts[s]] for s in ('Left', 'Right')}},
}
RIG_JSON.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
print('WROTE', RIG_JSON, RIG_JSON.stat().st_size, flush=True)

# ------------------------------------------------------------------ mesh proxy (rest pose, no shape keys)
for pb in ob.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()
meshes = {}
for o in rig.meshes:
    me = o.data
    mats = []
    for mat in me.materials:
        col = list(mat.diffuse_color)
        if mat.node_tree:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf and not bsdf.inputs['Base Color'].is_linked:
                col = list(bsdf.inputs['Base Color'].default_value)
        mats.append({'name': mat.name, 'base_color': r(col, 4)})
    groups = [g.name for g in o.vertex_groups]
    meshes[o.name] = {
        'matrix_world': m4(o.matrix_world), 'parent': o.parent.name if o.parent else None,
        'vertex_groups': groups, 'materials': mats,
        'vertices': [r(v.co, 5) for v in me.vertices],
        'polygons': [list(p.vertices) for p in me.polygons],
        'material_index': [p.material_index for p in me.polygons],
        'smooth': [int(p.use_smooth) for p in me.polygons],
        'weights': [[[g.group, round(g.weight, 4)] for g in v.groups if g.weight > 1e-4] for v in me.vertices]}
proxy = {'format': 'Buddy mesh proxy v1 (GetUp v03 handoff)', 'source_blend': data['source_blend'],
         'note': 'Rest-pose geometry and skin weights of A v04 (Body, Face, Outfit). No UVs/textures/shape keys; '
                 'material colours are flat base colours. Enough for floor-contact checks and silhouette renders.',
         'meshes': meshes}
PROXY_JSON.write_text(json.dumps(proxy, separators=(',', ':')), encoding='utf-8')
print('WROTE', PROXY_JSON, PROXY_JSON.stat().st_size, flush=True)
