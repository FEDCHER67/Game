"""Check skin weights, 65-bone hierarchy, animation and animated FBX round-trip."""
import bpy, argparse, json, math, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('--folder',type=Path,default=HERE)
p.add_argument('--revision',type=int,default=4)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
stem=f'NPC_BASE_01_v{a.revision:02d}';folder=a.folder
report_path=folder/f'validation_v{a.revision:02d}.json'
report=json.loads(report_path.read_text())
bpy.ops.wm.open_mainfile(filepath=str(folder/(stem+'.blend')))
scene=bpy.context.scene
assert scene['npc_asset_revision']==stem
rig=next(o for o in scene.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.data.collections['NPC_BASE_01'].objects if o.type=='MESH']
assert len(meshes)==6 and len(rig.data.bones)==65
assert len([ac for ac in bpy.data.actions if any(s.target_id_type=='OBJECT' for s in ac.slots)])==2
assert {b.name:b.parent.name if b.parent else None for b in rig.data.bones}==report['bone_parents']
assert not rig.constraints and not any(p.constraints for p in rig.pose.bones)
stats={};max_error=0;max_influences=0
for obj in meshes:
    assert len(obj.modifiers)==1 and obj.modifiers[0].object==rig
    assert obj.data.uv_layers
    for v in obj.data.vertices:
        weights=[g for g in v.groups if g.weight>0]
        assert weights and len(weights)<=4,(obj.name,v.index,len(weights))
        assert all(math.isfinite(g.weight) and 0<g.weight<=1 for g in weights)
        assert all(obj.vertex_groups[g.group].name in rig.data.bones for g in weights)
        assert all('Pinky' not in obj.vertex_groups[g.group].name for g in weights)
        error=abs(sum(g.weight for g in weights)-1);max_error=max(max_error,error)
        max_influences=max(max_influences,len(weights))
        assert error<1e-5
    obj.data.calc_loop_triangles()
    stats[obj.name]={'vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles)}
triangle_count=sum(d['triangles'] for d in stats.values())
assert triangle_count==report['total_triangles'] and triangle_count<17000
assert stats==report['meshes']
face=bpy.data.objects['Face_Expressions']
assert {'Blink','Happy','Worried','Surprised'}.issubset(face.data.shape_keys.key_blocks.keys())
assert all(k.value==0 for k in face.data.shape_keys.key_blocks)
def use(action):
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=next(s for s in action.slots if s.target_id_type=='OBJECT')
def points(obj):
    e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [e.matrix_world@v.co for v in e.data.vertices]
expected={};root_locations={};min_sole=999
for name in report['actions']:
    action=bpy.data.actions[name];use(action)
    assert tuple(round(v) for v in action.frame_range)==(1,68)
    expected[name]={};root_locations[name]=[]
    for frame in range(1,69):
        scene.frame_set(frame)
        root_locations[name].append((rig.matrix_world@rig.pose.bones['mixamorig:Hips'].matrix).translation.copy())
        for pb in rig.pose.bones:
            assert max(abs(v-1) for v in pb.matrix.to_scale())<1e-4,(frame,pb.name)
        for obj in meshes:
            ps=points(obj)
            assert all(math.isfinite(v) for point in ps for v in point)
            if name.endswith('InPlace'):
                assert all(-2<point.x<2 and -2<point.y<2 and -.01<point.z<2.5 for point in ps),(frame,obj.name)
                if obj.name=='Outfit_Shoes':min_sole=min(min_sole,min(point.z for point in ps))
            if frame in [1,20,40,68]:expected[name].setdefault(frame,{})[obj.name]=ps
    if name.endswith('InPlace'):
        assert all(abs(p.x)<1e-5 and abs(p.y)<1e-5 for p in root_locations[name])
    else:assert (root_locations[name][-1]-root_locations[name][0]).length>.5
report['skin_validation']={'status':'PASS','unweighted_vertices':0,'max_influences':max_influences,'max_weight_sum_error':max_error,'all_68_frames_finite':True,'in_place_min_shoe_z_m':min_sole}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(folder/(stem+'.fbx')),ignore_leaf_bones=False,automatic_bone_orientation=False)
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
meshes=[o for o in scene.objects if o.type=='MESH']
assert len(rig.data.bones)==65 and len(meshes)==6
assert len([ac for ac in bpy.data.actions if any(s.target_id_type=='OBJECT' for s in ac.slots)])==2
for obj in meshes:obj.data.calc_loop_triangles()
assert sum(len(o.data.loop_triangles) for o in meshes)==triangle_count
assert {m.name for o in meshes for m in o.data.materials}==set(report['materials'])
assert {b.name:b.parent.name if b.parent else None for b in rig.data.bones}==report['bone_parents']
assert sum(len(o.data.polygons) for o in meshes)>0
assert {'Blink','Happy','Worried','Surprised'}.issubset(bpy.data.objects['Face_Expressions'].data.shape_keys.key_blocks.keys())
max_distance=0
for name,frames in expected.items():
    action=next(ac for ac in bpy.data.actions if ac.name.endswith(name) and any(s.target_id_type=='OBJECT' for s in ac.slots))
    use(action)
    assert tuple(round(v) for v in action.frame_range)==(1,68)
    for frame,original in frames.items():
        scene.frame_set(frame)
        for obj in meshes:
            actual=points(obj);reference=original[obj.name]
            # FBX can split vertices at UV seams. Compare closest positions.
            from mathutils.kdtree import KDTree
            tree=KDTree(len(reference))
            for i,point in enumerate(reference):tree.insert(point,i)
            tree.balance()
            error=max(tree.find(point)[2] for point in actual)
            max_distance=max(max_distance,error)
            assert error<.001,(name,frame,obj.name,error)
report['animated_fbx_roundtrip']={'status':'PASS','bones':65,'meshes':6,'actions':list(expected),'sample_frames':[1,20,40,68],'max_vertex_error_m':max_distance}
report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RIG_VALIDATION_PASS '+json.dumps({k:report[k] for k in ['skin_validation','animated_fbx_roundtrip']}))
