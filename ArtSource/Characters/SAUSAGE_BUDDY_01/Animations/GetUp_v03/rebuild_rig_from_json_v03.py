"""Rebuild Buddy_Rig_Mixamo65 (and optionally the skinned mesh proxy) from the v03 JSON files, no Git LFS needed.

blender -b --factory-startup --python rebuild_rig_from_json_v03.py -- --out <new.blend> [--with-proxy] [--idle-action]
--with-proxy   also builds Body/Face/Outfit from mesh_proxy_Buddy_A_v04.json (flat colours, armature modifier)
--idle-action  adds a one-key action named 'Idle' (Idle frame 1), so getup_lib_v03 can use the rebuilt file:
               set the environment variable GETUP_SOURCE_BLEND=<new.blend> before running build_getups_v03.py.
Refuses to overwrite --out.
"""
from pathlib import Path
import sys, json, argparse
import bpy
from mathutils import Matrix, Vector, Quaternion

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--rig-json', default=str(HERE / 'rig_Buddy_Mixamo65.json'))
ap.add_argument('--proxy-json', default=str(HERE / 'mesh_proxy_Buddy_A_v04.json'))
ap.add_argument('--with-proxy', action='store_true')
ap.add_argument('--idle-action', action='store_true')
args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
out = Path(args.out)
assert not out.exists(), 'Refusing overwrite ' + str(out)
data = json.loads(Path(args.rig_json).read_text(encoding='utf-8'))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
A = data['armature_object']
arm = bpy.data.armatures.new(A['data_name'])
rig = bpy.data.objects.new(A['name'], arm)
scene.collection.objects.link(rig)
rig.matrix_world = Matrix(A['matrix_world'])
arm.display_type = A.get('display_type', 'STICK')
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for b in data['bones']:
    eb = arm.edit_bones.new(b['name'])
    eb.head, eb.tail, eb.roll = Vector(b['head']), Vector(b['tail']), b['roll']
for b in data['bones']:
    eb = arm.edit_bones[b['name']]
    if b['parent']:
        eb.parent = arm.edit_bones[b['parent']]
    eb.use_connect = b['use_connect']
    eb.use_deform = b['use_deform']
    eb.use_inherit_rotation = b['inherit_rotation']
    eb.inherit_scale = b['inherit_scale']
    eb.use_local_location = b['use_local_location']
bpy.ops.object.mode_set(mode='OBJECT')
for pb in rig.pose.bones:
    pb.rotation_mode = 'QUATERNION'
err = max(abs(rig.data.bones[b['name']].matrix_local[i][j] - b['matrix_local'][i][j])
          for b in data['bones'] for i in range(4) for j in range(4))
print('REBUILD_REST_MAX_ERR', err, flush=True)

if args.with_proxy:
    proxy = json.loads(Path(args.proxy_json).read_text(encoding='utf-8'))
    for name, m in proxy['meshes'].items():
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in m['vertices']], [], [tuple(p) for p in m['polygons']])
        for md in m['materials']:
            mat = bpy.data.materials.new(md['name'])
            mat.diffuse_color = md['base_color']
            try:
                mat.use_nodes = True
            except Exception:
                pass
            bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf:
                bsdf.inputs['Base Color'].default_value = md['base_color']
            me.materials.append(mat)
        me.polygons.foreach_set('material_index', m['material_index'])
        me.polygons.foreach_set('use_smooth', [bool(s) for s in m['smooth']])
        me.update()
        ob = bpy.data.objects.new(name, me)
        scene.collection.objects.link(ob)
        ob.matrix_world = Matrix(m['matrix_world'])
        groups = [ob.vertex_groups.new(name=g) for g in m['vertex_groups']]
        for vi, ws in enumerate(m['weights']):
            for gi, w in ws:
                groups[gi].add([vi], w, 'REPLACE')
        ob.parent = rig
        mod = ob.modifiers.new('Armature', 'ARMATURE')
        mod.object = rig
    print('REBUILD_PROXY', list(proxy['meshes']), flush=True)

if args.idle_action:
    act = bpy.data.actions.new('Idle')
    rig.animation_data_create()
    rig.animation_data.action = act
    for name, v in data['idle_frame1']['bones'].items():
        pb = rig.pose.bones[name]
        pb.rotation_quaternion = Quaternion(v['rotation_quaternion'])
        pb.keyframe_insert('rotation_quaternion', frame=1, group=name)
        if pb.parent is None:
            pb.location = Vector(v['location'])
            pb.keyframe_insert('location', frame=1, group=name)
    act.use_fake_user = True
    scene.frame_set(1)
    e2 = max(abs(rig.pose.bones[n].matrix[i][j] - v['matrix_armature'][i][j])
             for n, v in data['idle_frame1']['bones'].items() for i in range(4) for j in range(4))
    print('REBUILD_IDLE_MAX_ERR', e2, flush=True)

bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(out))
print('REBUILT', out, flush=True)
