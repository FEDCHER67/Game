"""Export the Sausage Buddy rig, contract poses and a skinned mesh proxy to JSON (no Git LFS needed).

  blender -b --factory-startup --python export_rig_json.py -- [--out rig_Buddy_Mixamo65_A_v04.json]

Reads (read-only): SAUSAGE_BUDDY_A_v04.blend, SAUSAGE_BUDDY_B_v04.blend (rig equality check),
Animations/GetUp_Idle_v01/GetUp_FromBack_v02.blend (supine first-frame contract).
The JSON holds: bones (head/tail/roll/flags/matrix_local, file order), Idle frame-1 raw values,
GetUp_FromBack_v02 frame-1 raw values, A v04 Body/Face/Outfit vertices, faces, material slots
(flat base colours) and vertex-group weights. rebuild_rig_from_json.py turns it back into a scene.
Refuses to overwrite an existing output.
"""
from pathlib import Path
import sys, json, argparse, hashlib
sys.dont_write_bytecode = True
import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import acting_core as C

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument('--out', default=str(HERE / 'rig_Buddy_Mixamo65_A_v04.json'))
args = ap.parse_args(argv)
out = Path(args.out)
assert not out.exists(), 'Refusing overwrite ' + str(out)


def r6(v):
    return [round(float(x), 7) for x in v]


def mat(m):
    return [r6(row) for row in m]


def full(v):
    return [float(x) for x in v]


def fmat(m):
    return [full(row) for row in m]


def bone_table(rig):
    bpy.context.view_layer.objects.active = rig
    for o in bpy.context.selected_objects:
        o.select_set(False)
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = {b.name: (full(b.head), full(b.tail), float(b.roll), b.use_connect) for b in rig.data.edit_bones}
    bpy.ops.object.mode_set(mode='OBJECT')
    table = []
    for b in rig.data.bones:
        h, t, roll, conn = eb[b.name]
        table.append({'name': b.name, 'parent': b.parent.name if b.parent else None, 'head': h, 'tail': t,
                      'roll': roll, 'use_connect': conn, 'use_deform': b.use_deform,
                      'use_inherit_rotation': b.use_inherit_rotation, 'inherit_scale': b.inherit_scale,
                      'use_local_location': b.use_local_location, 'matrix_local': fmat(b.matrix_local)})
    return table


def material_info(m):
    info = {'name': m.name, 'base_color': list(m.diffuse_color), 'roughness': 0.6, 'linked_base_color': False}
    if m.node_tree:
        bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf:
            bc = bsdf.inputs['Base Color']
            info['base_color'] = list(bc.default_value)
            info['linked_base_color'] = bc.is_linked
            info['roughness'] = float(bsdf.inputs['Roughness'].default_value)
            if bc.is_linked:   # follow one RGB / colour-ramp node for a representative flat colour
                src = bc.links[0].from_node
                if src.type == 'RGB':
                    info['base_color'] = list(src.outputs[0].default_value)
                elif src.type == 'VALTORGB':
                    info['base_color'] = list(src.color_ramp.elements[0].color)
    return info


def mesh_table(o):
    me = o.data
    groups = [g.name for g in o.vertex_groups]
    return {
        'name': o.name, 'parent': o.parent.name if o.parent else None, 'parent_type': o.parent_type,
        'matrix_world': mat(o.matrix_world), 'matrix_parent_inverse': mat(o.matrix_parent_inverse),
        'modifiers': [{'type': m.type, 'name': m.name, 'object': getattr(m, 'object', None).name
                       if getattr(m, 'object', None) else None} for m in o.modifiers],
        'vertices': [r6(v.co) for v in me.vertices],
        'polygons': [list(p.vertices) for p in me.polygons],
        'smooth': [bool(p.use_smooth) for p in me.polygons],
        'material_index': [p.material_index for p in me.polygons],
        'materials': [material_info(m) for m in me.materials],
        'vertex_groups': groups,
        'weights': [[[g.group, round(float(g.weight), 6)] for g in v.groups] for v in me.vertices],
        'shape_keys': [k.name for k in me.shape_keys.key_blocks] if me.shape_keys else [],
    }


B = C.Buddy()          # opens GetUp_FromBack_v02 (supine values) then A v04, read-only
bpy.ops.wm.open_mainfile(filepath=str(C.SRC_B))
rigB = bpy.data.objects[C.RIG_NAME]
bonesB = {b.name: [list(r) for r in b.matrix_local] for b in rigB.data.bones}
bpy.ops.wm.open_mainfile(filepath=str(C.SRC_A))
rig = bpy.data.objects[C.RIG_NAME]
bones = bone_table(rig)
ab_equal = all(max(abs(a - b) for ra, rb in zip(bt['matrix_local'], bonesB[bt['name']]) for a, b in zip(ra, rb)) < 1e-6
               for bt in bones)
data = {
    'format': 'Buddy rig + contract poses + skinned mesh proxy, v1 (Idle_Knock_v03 package)',
    'conventions': 'Blender units = metres, +Z up, character faces -Y, left = +X, 30 fps. '
                   'Quaternions are (w, x, y, z) pose-bone rotation_quaternion values (matrix_basis); '
                   'only mixamorig:Hips has a location channel.',
    'sources': {str(p.relative_to(C.CHAR)).replace('\\', '/'): C.sha256(p) for p in (C.SRC_A, C.SRC_B, C.GETUP_BACK)},
    'blender': bpy.app.version_string,
    'a_b_rest_rig_equal': ab_equal,
    'armature': {'object': rig.name, 'data': rig.data.name, 'matrix_world': mat(rig.matrix_world),
                 'bone_order_depth_first': C.ordered_bones(rig), 'bones': bones},
    'contracts': {
        'idle_frame1': {'source': 'SAUSAGE_BUDDY_A_v04.blend action Idle, frame 1',
                        'values': {n: v for n, v in B.idle_values.items()}},
        'supine_frame1': {'source': 'Animations/GetUp_Idle_v01/GetUp_FromBack_v02.blend frame 1 '
                                    '(neutral supine, head toward +Y, hips 0.3070 m)',
                          'values': {n: v for n, v in B.supine_values.items()}},
    },
    'meshes': [mesh_table(bpy.data.objects[n]) for n in C.MESH_NAMES],
    'sole_vertex_rule': 'Outfit vertices with rest z < 0.19, on the side (x*sign > 0), weight > 0.5 in '
                        '<Side>Foot or <Side>ToeBase (same rule as the GPT validators)',
}
out.write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
print('RIG_JSON', out, out.stat().st_size, 'bytes', 'A/B rest equal:', ab_equal, flush=True)
