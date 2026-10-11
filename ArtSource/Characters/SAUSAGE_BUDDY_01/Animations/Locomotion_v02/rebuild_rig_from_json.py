"""Rebuild Buddy_Rig_Mixamo65 in bpy from rig_Buddy_Mixamo65.json (no .blend/.fbx needed).

As a module:   import rebuild_rig_from_json as RR; rig = RR.build(json_path)
Standalone check (Blender 5.2 background):
  blender -b --factory-startup --python rebuild_rig_from_json.py -- [--json rig_Buddy_Mixamo65.json]
      [--fbx OUT.fbx]
The check rebuilds the armature in an empty scene, compares every rest matrix with the JSON and
prints the largest difference; --fbx also writes a bind-pose-only FBX with the walk export settings.
"""
from pathlib import Path
import sys
import json
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent


def build(json_path=HERE / 'rig_Buddy_Mixamo65.json', collection=None):
    doc = json.loads(Path(json_path).read_text())
    o = doc['armature_object']
    data = bpy.data.armatures.new(o['data_name'])
    rig = bpy.data.objects.new(o['name'], data)
    (collection or bpy.context.scene.collection).objects.link(rig)
    rig.rotation_mode = o['rotation_mode']
    rig.location = o['location']
    rig.rotation_euler = o['rotation_euler']
    rig.rotation_quaternion = o['rotation_quaternion']
    rig.scale = o['scale']
    bpy.context.view_layer.objects.active = rig
    for ob in bpy.context.view_layer.objects:
        ob.select_set(ob == rig)
    bpy.ops.object.mode_set(mode='EDIT')
    for b in doc['bones']:                                  # parents come first in the file
        eb = data.edit_bones.new(b['name'])
        eb.head = Vector(b['head'])
        eb.tail = Vector(b['tail'])
        eb.roll = b['roll']
        if b['parent']:
            eb.parent = data.edit_bones[b['parent']]
        eb.use_connect = b['use_connect']
        eb.use_deform = b['use_deform']
        eb.use_inherit_rotation = b['use_inherit_rotation']
        eb.inherit_scale = b['inherit_scale']
        eb.use_local_location = b['use_local_location']
        eb.use_relative_parent = b['use_relative_parent']
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return rig


def rest_error(rig, json_path=HERE / 'rig_Buddy_Mixamo65.json'):
    doc = json.loads(Path(json_path).read_text())
    err = 0.0
    for b in doc['bones']:
        m = rig.data.bones[b['name']].matrix_local
        err = max(err, max(abs(m[r][c] - b['matrix_local'][r][c]) for r in range(4) for c in range(4)))
    parents = all((rig.data.bones[b['name']].parent.name if rig.data.bones[b['name']].parent else None) == b['parent']
                  for b in doc['bones'])
    return err, parents, len(rig.data.bones) == doc['bone_count']


if __name__ == '__main__':
    import argparse
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=str(HERE / 'rig_Buddy_Mixamo65.json'))
    ap.add_argument('--fbx', default='')
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rig = build(a.json)
    err, parents_ok, count_ok = rest_error(rig, a.json)
    print('REBUILT', rig.name, len(rig.data.bones), 'bones; max rest matrix error', err,
          'parents ok', parents_ok, 'count ok', count_ok, flush=True)
    if a.fbx:
        out = Path(a.fbx)
        assert not out.exists(), f'Refusing to overwrite {out}'
        bpy.ops.export_scene.fbx(filepath=str(out), use_selection=True, object_types={'ARMATURE'},
                                 add_leaf_bones=False, use_armature_deform_only=False, bake_anim=False,
                                 axis_forward='-Z', axis_up='Y', apply_unit_scale=True)
        print('FBX', out, flush=True)
