"""Rebuild the Sausage Buddy rig + skinned A-variant mesh proxy from rig_Buddy_Mixamo65_A_v04.json.

For cloud sessions without Git LFS (the .blend/.fbx sources are LFS pointers there).
  blender -b --factory-startup --python rebuild_rig_from_json.py -- [--json <file>] [--save <out.blend>]

Library use (acting_core.Buddy does this automatically when the source .blend is an LFS pointer):
  import rebuild_rig_from_json as RB; rig, meshes, data = RB.build_scene(json_path)
The rebuilt bones are verified against the stored matrix_local (bind pose) values.
"""
from pathlib import Path
import sys, json, argparse
sys.dont_write_bytecode = True
import bpy
from mathutils import Matrix

HERE = Path(__file__).resolve().parent
DEFAULT_JSON = HERE / 'rig_Buddy_Mixamo65_A_v04.json'


def build_scene(json_path=DEFAULT_JSON):
    data = json.loads(Path(json_path).read_text(encoding='utf-8'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    A = data['armature']
    arm = bpy.data.armatures.new(A['data'])
    rig = bpy.data.objects.new(A['object'], arm)
    scene.collection.objects.link(rig)
    rig.matrix_world = Matrix(A['matrix_world'])
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = {}
    for b in A['bones']:                       # stored in the original file order
        eb = arm.edit_bones.new(b['name'])
        eb.head, eb.tail, eb.roll = b['head'], b['tail'], b['roll']
        eb.use_deform = b['use_deform']
        eb.use_inherit_rotation = b['use_inherit_rotation']
        eb.inherit_scale = b['inherit_scale']
        eb.use_local_location = b['use_local_location']
        ebs[b['name']] = eb
    for b in A['bones']:
        if b['parent']:
            ebs[b['name']].parent = ebs[b['parent']]
            ebs[b['name']].use_connect = b['use_connect']
    bpy.ops.object.mode_set(mode='OBJECT')
    worst = 0.0
    for b in A['bones']:
        m = arm.bones[b['name']].matrix_local
        worst = max(worst, max(abs(m[r][c] - b['matrix_local'][r][c]) for r in range(4) for c in range(4)))
    assert [b.name for b in arm.bones] == [b['name'] for b in A['bones']], 'bone order differs'
    assert worst < 2e-6, 'rebuilt bind matrices differ by %g' % worst
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    meshes = []
    for M in data['meshes']:
        me = bpy.data.meshes.new(M['name'])
        me.from_pydata(M['vertices'], [], M['polygons'])
        me.update()
        for i, p in enumerate(me.polygons):
            p.use_smooth = M['smooth'][i]
            p.material_index = M['material_index'][i]
        for mi in M['materials']:
            mat = bpy.data.materials.new(mi['name'])
            try:
                mat.use_nodes = True
            except Exception:
                pass
            bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf:
                bsdf.inputs['Base Color'].default_value = mi['base_color']
                bsdf.inputs['Roughness'].default_value = mi['roughness']
            mat.diffuse_color = mi['base_color']
            me.materials.append(mat)
        o = bpy.data.objects.new(M['name'], me)
        scene.collection.objects.link(o)
        for g in M['vertex_groups']:
            o.vertex_groups.new(name=g)
        for vi, ws in enumerate(M['weights']):
            for gi, w in ws:
                o.vertex_groups[gi].add([vi], w, 'REPLACE')
        o.parent = rig
        o.matrix_parent_inverse = Matrix(M['matrix_parent_inverse'])
        mod = o.modifiers.new('Armature', 'ARMATURE')
        mod.object = rig
        meshes.append(o)
    bpy.context.view_layer.update()
    print('REBUILT', rig.name, len(arm.bones), 'bones; max bind-matrix error', worst,
          '; meshes', [(o.name, len(o.data.vertices)) for o in meshes], flush=True)
    return rig, meshes, data


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=str(DEFAULT_JSON))
    ap.add_argument('--save', default='')
    a = ap.parse_args(argv)
    build_scene(a.json)
    if a.save:
        assert not Path(a.save).exists(), 'Refusing overwrite ' + a.save
        bpy.ops.wm.save_as_mainfile(filepath=a.save)
        print('SAVED', a.save)
