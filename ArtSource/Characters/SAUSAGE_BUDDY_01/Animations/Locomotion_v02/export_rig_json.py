"""Export the Buddy_Rig_Mixamo65 skeleton and the shoe-sole skin data to plain JSON, so animation
can be authored and exported to FBX without the Git LFS .blend/.fbx files.

Blender 5.2 background (reads SAUSAGE_BUDDY_A_v04.blend and _B_v04.blend; never writes them):
  blender -b --factory-startup --python export_rig_json.py

Writes next to this script (refuses to overwrite):
  rig_Buddy_Mixamo65.json   65 bones in hierarchy order: name, parent, head/tail/roll (edit space),
                            flags, rest matrix (armature space), armature object transform.
  shoe_soles_v04.json       Outfit vertices of both shoes (z < 0.10 m) with Leg/Foot/ToeBase skin
                            weights, for variants A and B (rest space); used for contact maths.
Rebuild the armature with rebuild_rig_from_json.py.
"""
from pathlib import Path
import sys
import json
import hashlib
sys.dont_write_bytecode = True
import bpy

HERE = Path(__file__).resolve().parent
CHAR = HERE.parent.parent
RIG_JSON = HERE / 'rig_Buddy_Mixamo65.json'
SOLES_JSON = HERE / 'shoe_soles_v04.json'
for p in (RIG_JSON, SOLES_JSON):
    assert not p.exists(), f'Refusing to overwrite {p}'
P = 'mixamorig:'


def mat(m):
    return [[float(x) for x in row] for row in m]


def vec(v):
    return [float(x) for x in v]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_variant(variant):
    bpy.ops.wm.open_mainfile(filepath=str(CHAR / f'SAUSAGE_BUDDY_{variant}_v04.blend'))
    rig = bpy.data.objects['Buddy_Rig_Mixamo65']
    bpy.context.view_layer.objects.active = rig
    for o in bpy.context.view_layer.objects:
        o.select_set(o == rig)
    bpy.ops.object.mode_set(mode='EDIT')
    edit = {eb.name: {'head': vec(eb.head), 'tail': vec(eb.tail), 'roll': float(eb.roll),
                      'use_connect': eb.use_connect} for eb in rig.data.edit_bones}
    bpy.ops.object.mode_set(mode='OBJECT')
    order = []

    def walk(b):
        order.append(b)
        for c in b.children:
            walk(c)
    for b in rig.data.bones:
        if b.parent is None:
            walk(b)
    bones = []
    for b in order:
        e = edit[b.name]
        bones.append({
            'name': b.name, 'parent': b.parent.name if b.parent else None,
            'head': e['head'], 'tail': e['tail'], 'roll': e['roll'],
            'use_connect': e['use_connect'], 'use_deform': b.use_deform,
            'use_inherit_rotation': b.use_inherit_rotation, 'inherit_scale': b.inherit_scale,
            'use_local_location': b.use_local_location, 'use_relative_parent': b.use_relative_parent,
            'matrix_local': mat(b.matrix_local),
        })
    obj = {'name': rig.name, 'data_name': rig.data.name, 'matrix_world': mat(rig.matrix_world),
           'location': vec(rig.location), 'rotation_mode': rig.rotation_mode,
           'rotation_euler': vec(rig.rotation_euler), 'rotation_quaternion': vec(rig.rotation_quaternion),
           'scale': vec(rig.scale), 'parent': rig.parent.name if rig.parent else None}
    outfit = bpy.data.objects['Outfit']
    names = {g.index: g.name for g in outfit.vertex_groups}
    soles = {}
    for side in ('Left', 'Right'):
        keep = {P + side + n for n in ('Leg', 'Foot', 'ToeBase')}
        verts = []
        for v in outfit.data.vertices:
            co = outfit.matrix_world @ v.co
            if co.z >= 0.10:
                continue
            w = {names[g.group]: float(g.weight) for g in v.groups if g.weight > 0.0}
            if not any(n in keep for n in w):
                continue
            verts.append({'i': v.index, 'co': vec(co), 'w': w})
        soles[side] = verts
    meta = {'outfit_matrix_world': mat(outfit.matrix_world), 'outfit_vertices': len(outfit.data.vertices)}
    return bones, obj, soles, meta


bones_a, obj_a, soles_a, meta_a = read_variant('A')
bones_b, obj_b, soles_b, meta_b = read_variant('B')
same = bones_a == bones_b and obj_a == obj_b
assert same, 'A and B skeletons differ; this export assumes one shared rig'
sources = {n: sha(CHAR / n) for n in ('SAUSAGE_BUDDY_A_v04.blend', 'SAUSAGE_BUDDY_B_v04.blend',
                                      'SAUSAGE_BUDDY_A_v04.fbx', 'SAUSAGE_BUDDY_B_v04.fbx')}
rig_doc = {
    'format': 'Buddy rig JSON v1',
    'note': ('Skeleton of SAUSAGE_BUDDY_A_v04 and _B_v04 (identical). Units metres, Blender armature space: '
             'character faces -Y, left = +X, Z up. head/tail/roll are edit-bone values; matrix_local is the rest '
             'matrix in armature space (bone Y axis along the bone). Bones are listed parents first.'),
    'source_sha256': sources,
    'a_b_identical': same,
    'armature_object': obj_a,
    'bone_count': len(bones_a),
    'root': [b['name'] for b in bones_a if b['parent'] is None],
    'bones': bones_a,
    'fbx_export': {'note': 'Settings used for the Walk FBX revisions (animation-only, Unity Generic import)',
                   'use_selection': True, 'object_types': ['ARMATURE'], 'add_leaf_bones': False,
                   'use_armature_deform_only': False, 'bake_anim': True, 'bake_anim_use_all_actions': True,
                   'bake_anim_use_nla_strips': False, 'bake_anim_step': 0.5, 'bake_anim_simplify_factor': 0.0,
                   'axis_forward': '-Z', 'axis_up': 'Y', 'apply_unit_scale': True, 'use_mesh_modifiers': False,
                   'pose_before_export': 'rest (all pose bones identity, no action) so the bind pose is the rest pose'},
}
soles_doc = {
    'format': 'Buddy shoe soles JSON v1',
    'note': ('Outfit vertices of both shoes below z = 0.10 m with skin weights (bone name -> weight), rest space. '
             'Vertices weighted only to Foot form the rigid heel part, only to ToeBase the rigid toe part; '
             'mixed ones bend at the ball. Rest sole bottom is z = -0.001.'),
    'source_sha256': sources,
    'A': {'meta': meta_a, 'soles': soles_a},
    'B': {'meta': meta_b, 'soles': soles_b},
}
RIG_JSON.write_text(json.dumps(rig_doc, indent=1))
SOLES_JSON.write_text(json.dumps(soles_doc))
print('RIG_JSON', RIG_JSON, len(bones_a), 'bones; SOLES_JSON', SOLES_JSON,
      {v: {s: len(d[s]) for s in d} for v, d in (('A', soles_a), ('B', soles_b))}, flush=True)
