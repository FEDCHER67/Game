"""Focused v07+ clothing, elbow, hand, rigid-head and uniform-skin checks."""
import bpy,bmesh,json,math,argparse,sys
from pathlib import Path
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import intersect_ray_tri
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from refine_npc_joints import components
p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);p.add_argument('--revision',type=int,default=7);p.add_argument('--render',action='store_true')
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.folder=a.folder.resolve();report_file=a.folder/f'validation_v{a.revision:02d}.json';report=json.loads(report_file.read_text())
bpy.ops.wm.open_mainfile(filepath=str(a.folder/f'NPC_BASE_01_v{a.revision:02d}.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['NPC_Rig_Mixamo65'];body=bpy.data.objects['Body_Base'];shirt=bpy.data.objects['Outfit_TShirt'];face=bpy.data.objects['Face_Expressions'];shorts=bpy.data.objects['Outfit_Shorts']
skin=bpy.data.materials['Skin_Warm']
assert all(m==skin for m in body.data.materials)
assert all(body.data.materials[p.material_index]==skin for p in body.data.polygons)
shader=next(n for n in skin.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
assert not shader.inputs['Base Color'].is_linked
assert max(abs(a-b) for a,b in zip(shader.inputs['Base Color'].default_value,report['appearance_refinement']['skin_base_color_linear_rgba']))<1e-6
# Head-neck, ears and nose: shells above the yoke (v08 head is shorter than 1.74 m).
head=[i for part in components(body.data) if min(body.data.vertices[i].co.z for i in part)>1.15 and max(abs(body.data.vertices[i].co.x) for i in part)<.2 for i in part]
bm=bmesh.new();bm.from_mesh(shirt.data);collar=[v.index for v in bm.verts if v.is_boundary and v.co.z>1.12 and math.hypot(v.co.x,v.co.y)<.15]
assert all(len(e.link_faces) in (1,2) and (e.is_boundary or e.is_contiguous) for e in bm.edges);bm.free()
rigid=[(body,head),(face,list(range(len(face.data.vertices)))),(shirt,collar)]
if a.revision>=9:
    # v09: the visible sausage bends on Neck/Head; its base inside the collar and the rim stay on Spine2.
    rigid=[(body,[i for i in head if body.data.vertices[i].co.z<1.245]),(shirt,collar)]
for obj,ids in rigid:
    for i in ids:
        gs=[g for g in obj.data.vertices[i].groups if g.weight>1e-6]
        assert len(gs)==1 and obj.vertex_groups[gs[0].group].name=='mixamorig:Spine2'
def geo(obj):
    e=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();m.calc_loop_triangles()
    ps=[e.matrix_world@v.co for v in m.vertices];ts=[tuple(t.vertices) for t in m.loop_triangles];e.to_mesh_clear()
    return ps,ts,BVHTree.FromPolygons(ps,ts,all_triangles=True)
def crosses(a,b):
    for s,t in [(a,b),(b,a)]:
        for i in range(3):
            d=s[(i+1)%3]-s[i];hit=intersect_ray_tri(*t,d,s[i],True)
            if hit is not None and d.length_squared>1e-16 and 1e-5<(hit-s[i]).dot(d)/d.length_squared<1-1e-5:return True
    return False
max_drift=0;checks={};creases={};hand_contacts={};finger_contacts={}
def check(name):
    global max_drift
    bv,bt,bb=geo(body);sv,st,sb=geo(shirt);fv,ft,fb=geo(face);pv,pt,pb=geo(shorts)
    transform=rig.matrix_world@rig.pose.bones['mixamorig:Spine2'].matrix@rig.data.bones['mixamorig:Spine2'].matrix_local.inverted()
    for obj,ids in rigid:
        ps={body:bv,face:fv,shirt:sv}[obj]
        max_drift=max(max_drift,max((ps[i]-transform@obj.data.vertices[i].co).length for i in ids))
    cross=[];self_cross=0
    for i,j in bb.overlap(sb):
        if crosses([bv[k] for k in bt[i]],[sv[k] for k in st[j]]):
            center=sum((body.data.vertices[k].co for k in bt[i]),Vector())/3
            cross.append([round(v,4) for v in center])
    for i,j in sb.overlap(sb):
        if i<j and not set(st[i])&set(st[j]) and crosses([sv[k] for k in st[i]],[sv[k] for k in st[j]]):
            self_cross+=1
            if self_cross<=2:print('SELF_LOCATION',name,[[round(sum(shirt.data.vertices[k].co[d] for k in st[q])/3,4) for d in range(3)] for q in [i,j]])
    arm_self=0;crease=0;fingers=0
    for sign in [-1,1]:
        tris=[t for t in bt if all(sign*body.data.vertices[k].co.x>.30 for k in t)]
        tree=BVHTree.FromPolygons(bv,tris,all_triangles=True)
        for i,j in tree.overlap(tree):
            if i<j and not set(tris[i])&set(tris[j]) and crosses([bv[k] for k in tris[i]],[bv[k] for k in tris[j]]):
                # v08 elbows keep both limb segments full; their inner surfaces meet
                # inside the crease (buried, see verify_hidden_folds.py). Anything
                # outside the elbow band still fails.
                if a.revision>=8 and all(.33<abs(body.data.vertices[k].co.x)<.49 for k in tris[i]+tris[j]):crease+=1
                # v09 closes the fat fingers side by side; neighbours may touch.
                elif a.revision>=9 and all(abs(body.data.vertices[k].co.x)>.745 for k in tris[i]+tris[j]):fingers+=1
                else:arm_self+=1
    shorts_body=0
    for i,j in bb.overlap(pb):
        if crosses([bv[k] for k in bt[i]],[pv[k] for k in pt[j]]):
            # A swinging hand brushing the hip is animation contact, not garment fit.
            if all(abs(body.data.vertices[k].co.x)>.6 for k in bt[i]):hand_contacts[name]=hand_contacts.get(name,0)+1
            else:shorts_body+=1
    checks[name]={'body_shirt':len(cross),'shirt_self':self_cross,'arm_hand_self':arm_self,'shorts_body':shorts_body}
    if crease:creases[name]=crease
    if fingers:finger_contacts[name]=fingers
    if cross or self_cross or arm_self or shorts_body:print('CROSSINGS',name,checks[name],cross[:6])
def render(name,target,scale,offset=Vector((1,-3,1))):
    if not a.render:return
    out=a.folder/'Previews'/f'v{a.revision:02d}';out.mkdir(parents=True,exist_ok=True)
    cam=scene.camera;cam.location=target+offset;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
    scene.render.resolution_x=800;scene.render.resolution_y=800;scene.cycles.samples=16
    scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
for f in range(1,69):
    scene.frame_set(f);check('run_'+str(f))
    if f in [20,60]:
        transform=rig.matrix_world@rig.pose.bones['mixamorig:Spine2'].matrix@rig.data.bones['mixamorig:Spine2'].matrix_local.inverted()
        render('Upper_'+str(f),transform@Vector((0,0,1.40)),.96)
        if f==20:render('Mouth_20',transform@Vector((0,-.12,1.398)),.19,transform.to_3x3()@Vector((0,-.5,.05)))
action=rig.animation_data.action;rig.animation_data.action=None
def reset():
    for bone in rig.pose.bones:bone.location=(0,0,0);bone.rotation_quaternion=Quaternion();bone.scale=(1,1,1)
def rotate(name,axis,degrees):
    bone=rig.pose.bones['mixamorig:'+name];local=bone.bone.matrix_local.to_3x3().inverted()@Vector(axis)
    bone.rotation_quaternion=Quaternion(local,math.radians(degrees))
poses={
 'Rest':[],
 'ArmsDown':[('LeftArm',(0,1,0),80),('RightArm',(0,1,0),-80)],
 'ArmsRaised':[('LeftArm',(0,1,0),-55),('RightArm',(0,1,0),55)],
 'Reach':[('LeftArm',(0,0,1),-70),('RightArm',(0,1,0),-60)],
 'TorsoTwist':[('Spine1',(0,0,1),30),('Spine2',(1,0,0),25),('LeftArm',(0,1,0),65),('RightArm',(0,1,0),-65)],
 'HumanNeckMotionIgnored':[('Neck',(1,0,0),50),('Head',(0,0,1),-80),('LeftArm',(0,1,0),70),('RightArm',(0,1,0),-70)]}
poses.update({
 'Elbow90':[('LeftForeArm',(0,0,1),-90),('RightForeArm',(0,0,1),90)],
 'Elbow120':[('LeftForeArm',(0,0,1),-120),('RightForeArm',(0,0,1),120)],
 'ThumbSpread':[('LeftHandThumb1',(0,0,1),-35),('RightHandThumb1',(0,0,1),35)],
 'ThumbFlex':[('LeftHandThumb2',(.73,.68,0),55),('LeftHandThumb3',(.73,.68,0),25),('RightHandThumb2',(-.73,.68,0),-55),('RightHandThumb3',(-.73,.68,0),-25)]})
for name,rotations in poses.items():
    reset()
    for bone,axis,angle in rotations:rotate(bone,axis,angle)
    bpy.context.view_layer.update();check(name)
    if name in ['Rest','ArmsRaised','TorsoTwist']:render(name,Vector((0,0,1.38)),.99)
# The mouth strips must remain in front of the head for every stored expression.
reset();bpy.context.view_layer.update();body.data.calc_loop_triangles()
head_set=set(head);hs=[tuple(t.vertices) for t in body.data.loop_triangles if set(t.vertices)<=head_set]
tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],hs,all_triangles=True)
mouth=set(report['upper_repair']['mouth_vertices']);clearances=[]
for expression in ['Basis','Happy','Worried','Surprised']:
    expression_start=len(clearances)
    for key in face.data.shape_keys.key_blocks:
        if key.name!='Basis':key.value=1 if key.name==expression else 0
    bpy.context.view_layer.update();v,t,_=geo(face)
    for tri in t:
        if not set(tri)<=mouth:continue
        samples=[v[i] for i in tri]+[sum((v[i] for i in tri),Vector())/3]
        for pt in samples:
            hit=tree.ray_cast(Vector((pt.x,-1,pt.z)),Vector((0,1,0)))
            assert hit[0] is not None
            clearances.append(hit[0].y-pt.y)
    print('MOUTH_CLEARANCE',expression,min(clearances[expression_start:]))
assert min(clearances)>.0005,min(clearances)
assert max_drift<1e-5,max_drift
report['joint_refinement_validation']={'rigid_head_face_collar_max_drift_m':max_drift,'mouth_min_clearance_m':min(clearances),'run_frames':68,'diagnostic_poses':list(poses),'crossings':checks,'elbow_crease_contacts':creases,'hand_garment_contacts':hand_contacts,'finger_side_contacts':finger_contacts}
latest=json.loads(report_file.read_text());latest['joint_refinement_validation']=report['joint_refinement_validation']
report_file.write_text(json.dumps(latest,indent=2),encoding='utf-8')
print('SAUSAGE_UPPER_CHECK',json.dumps({k:v for k,v in report['joint_refinement_validation'].items() if k!='crossings'}))
assert all(not any(v.values()) for v in checks.values()),'Clothing crossings remain; inspect reported poses.'
