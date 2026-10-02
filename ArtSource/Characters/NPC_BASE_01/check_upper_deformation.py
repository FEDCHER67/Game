"""Check clothing crossings, collar fit and animated palm/wrist deformation."""
import bpy,bmesh,json,sys,argparse,math
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--revision',type=int,default=5)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
report_path=a.folder/f'validation_v{a.revision:02d}.json'
report=json.loads(report_path.read_text())
bpy.ops.wm.open_mainfile(filepath=str(a.folder/f'NPC_BASE_01_v{a.revision:02d}.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['NPC_Rig_Mixamo65']
shirt=bpy.data.objects['Outfit_TShirt'];body=bpy.data.objects['Body_Base']
bm=bmesh.new();bm.from_mesh(shirt.data)
assert all(len(e.link_faces) in (1,2) for e in bm.edges)
assert all(e.is_contiguous for e in bm.edges if len(e.link_faces)==2)
boundary={v for e in bm.edges if e.is_boundary for v in e.verts};loops=[]
while boundary:
    todo=[boundary.pop()];ids=[]
    while todo:
        v=todo.pop();ids.append(v.index)
        edges=[e for e in v.link_edges if e.is_boundary];assert len(edges)==2
        for e in edges:
            o=e.other_vert(v)
            if o in boundary:boundary.remove(o);todo.append(o)
    loops.append(ids)
assert len(loops)==4,len(loops)
collar=max(loops,key=lambda loop:sum(shirt.data.vertices[i].co.z for i in loop)/len(loop))
for i in collar:
    groups=[g for g in shirt.data.vertices[i].groups if g.weight>1e-6]
    assert len(groups)==1 and shirt.vertex_groups[groups[0].group].name=='mixamorig:Neck'
bm.free()
bm=bmesh.new();bm.from_mesh(body.data)
assert all(len(e.link_faces)==2 and e.is_contiguous for e in bm.edges)
bm.free()
palm_ids={}
for side,sign in [('Left',1),('Right',-1)]:
    ids=[v.index for v in body.data.vertices if .68<sign*v.co.x<.727 and abs(v.co.y)<.036
         and all(body.data.attributes['npc_digit_'+d].data[v.index].value<1e-7 for d in ['Thumb','Index','Middle','Ring'])]
    assert len(ids)>=10,(side,len(ids))
    for i in ids:
        groups=[g for g in body.data.vertices[i].groups if g.weight>1e-6]
        assert len(groups)==1 and body.vertex_groups[groups[0].group].name=='mixamorig:'+side+'Hand'
    palm_ids[side]=ids
body.data.calc_loop_triangles()
hand_tris={side:[tuple(t.vertices) for t in body.data.loop_triangles
                if all(sign*body.data.vertices[k].co.x>.595 for k in t.vertices)]
           for side,sign in [('Left',1),('Right',-1)]}
def geometry(obj):
    e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles()
    v=[e.matrix_world@p.co for p in m.vertices];t=[tuple(p.vertices) for p in m.loop_triangles]
    e.to_mesh_clear();return v,t,BVHTree.FromPolygons(v,t,all_triangles=True)
def crosses(a,b):
    for s,t in [(a,b),(b,a)]:
        for i in range(3):
            delta=s[(i+1)%3]-s[i];hit=intersect_ray_tri(*t,delta,s[i],True)
            if hit is not None and delta.length_squared>1e-16:
                f=(hit-s[i]).dot(delta)/delta.length_squared
                if 1e-5<f<1-1e-5:return hit
    return None
frames={};ring_drift=0;palm_drift=0;max_hand_crossings=0
for frame in range(1,69):
    scene.frame_set(frame)
    av,at,ab=geometry(body);bv,bt,bb=geometry(shirt)
    hits=[]
    for i,j in ab.overlap(bb):
        hit=crosses([av[k] for k in at[i]],[bv[k] for k in bt[j]])
        if hit is not None:
            rest=sum((body.data.vertices[k].co for k in at[i]),start=body.data.vertices[at[i][0]].co*0)/3
            hits.append({'body_rest':[round(v,4) for v in rest],'shirt_triangle':j})
    self_hits=0;self_examples=[]
    for i,j in bb.overlap(bb):
        if i>=j or set(bt[i])&set(bt[j]):continue
        if crosses([bv[k] for k in bt[i]],[bv[k] for k in bt[j]]) is not None:
            self_hits+=1
            if len(self_examples)<4:
                self_examples.append([[round(sum(shirt.data.vertices[k].co[d] for k in bt[t])/3,4) for d in range(3)] for t in [i,j]])
    transform=rig.matrix_world@rig.pose.bones['mixamorig:Neck'].matrix@rig.data.bones['mixamorig:Neck'].matrix_local.inverted()
    for i in collar:ring_drift=max(ring_drift,(bv[i]-transform@shirt.data.vertices[i].co).length)
    hand_crossings={}
    for side,ids in palm_ids.items():
        name='mixamorig:'+side+'Hand'
        transform=rig.matrix_world@rig.pose.bones[name].matrix@rig.data.bones[name].matrix_local.inverted()
        for i in ids:palm_drift=max(palm_drift,(av[i]-transform@body.data.vertices[i].co).length)
        tris=hand_tris[side];tree=BVHTree.FromPolygons(av,tris,all_triangles=True);count=0
        for i,j in tree.overlap(tree):
            if i>=j or set(tris[i])&set(tris[j]):continue
            if crosses([av[k] for k in tris[i]],[av[k] for k in tris[j]]) is not None:count+=1
        hand_crossings[side]=count;max_hand_crossings=max(max_hand_crossings,count)
    frames[str(frame)]={'body_shirt_crossings':len(hits),'shirt_self_crossings':self_hits,
                        'hand_self_crossings':hand_crossings,'examples':hits[:6],'self_examples':self_examples}
assert ring_drift<1e-5,ring_drift
assert palm_drift<1e-5,palm_drift
result={'shirt_boundary_loops':4,'collar_vertices_follow_neck_exactly':True,'collar_max_drift_m':ring_drift,
        'max_body_shirt_crossings':max(v['body_shirt_crossings'] for v in frames.values()),
        'max_shirt_self_crossings':max(v['shirt_self_crossings'] for v in frames.values()),
        'palm_core_vertices':{k:len(v) for k,v in palm_ids.items()},'palm_core_max_drift_m':palm_drift,
        'max_hand_self_crossings':max_hand_crossings,'frames':frames}
report['upper_deformation']=result
report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('UPPER_DEFORMATION_RESULT',json.dumps({k:v for k,v in result.items() if k!='frames'}))
for f,v in frames.items():
    if v['body_shirt_crossings'] or v['shirt_self_crossings'] or any(v['hand_self_crossings'].values()):print('CROSSING_FRAME',f,json.dumps(v))
assert result['max_body_shirt_crossings']==result['max_shirt_self_crossings']==max_hand_crossings==0,result
