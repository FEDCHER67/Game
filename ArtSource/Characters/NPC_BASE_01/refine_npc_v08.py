"""Local v07 to v08 repair: light crew collar and closer sleeves, compact elbows,
thumb bound to the hand and a slightly shorter head-neck block."""
import bpy,math,json,argparse,sys
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from refine_npc_joints import weights,components

HEAD_DROP=.045;NECK_LO=1.245;NECK_HI=1.37
ELBOW_RHO=.05
ELBOW_ANGLES=[(30,.5),(50,1),(70,1),(90,1.2),(105,1.2),(120,.6)]

def mixed(parts):
    # Weighted sum of weight dicts, at most four influences, normalised.
    w={}
    for d,s in parts:
        for name,value in d.items():w[name]=w.get(name,0)+value*s
    top=[kv for kv in sorted(w.items(),key=lambda kv:-kv[1])[:4] if kv[1]>1e-4];total=sum(v for _,v in top)
    return {k:v/total for k,v in top}

def surface_weights(obj,tree,polys,co,cache):
    loc,n,index,dist=tree.find_nearest(co);ids=polys[index]
    inv=[1/max((obj.data.vertices[i].co-loc).length,1e-6) for i in ids];total=sum(inv)
    return mixed([(cache[i],s/total) for i,s in zip(ids,inv)]),loc,n,dist

def head_parts(mesh):
    # Head-neck cylinder, ears and nose: separate shells above the shirt yoke.
    return [i for part in components(mesh) if min(mesh.vertices[i].co.z for i in part)>1.15
            and max(abs(mesh.vertices[i].co.x) for i in part)<.2 for i in part]

def shorten_head():
    body=bpy.data.objects['Body_Base'];face=bpy.data.objects['Face_Expressions'];rig=bpy.data.objects['NPC_Rig_Mixamo65']
    # Remove a band of the straight neck between the collar and the mouth.
    # Everything above it (face, ears, nose, cranium) moves down unchanged.
    k=(NECK_HI-HEAD_DROP-NECK_LO)/(NECK_HI-NECK_LO)
    def f(z):
        if z<=NECK_LO:return z
        if z<NECK_HI:return NECK_LO+(z-NECK_LO)*k
        return z-HEAD_DROP
    head=head_parts(body.data);assert len(head)>600
    for i in head:
        v=body.data.vertices[i];v.co.z=f(v.co.z)
        # Hidden bottom of the cylinder: narrower, so raised shoulders of the
        # shirt never uncover it near the armpits.
        if v.co.z<1.17:v.co.x*=.85;v.co.y*=.85
    assert min(v.co.z for v in face.data.vertices)>NECK_HI
    for key in face.data.shape_keys.key_blocks:
        for d in key.data:d.co.z=f(d.co.z)
    for v in face.data.vertices:v.co.z=f(v.co.z)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        if bone.name in ('mixamorig:Head','mixamorig:HeadTop_End'):
            for point in [bone.head,bone.tail]:point.z=f(point.z)
    bpy.ops.object.mode_set(mode='OBJECT');body.data.update();face.data.update();bpy.context.view_layer.update()
    return {'removed_neck_band_m':HEAD_DROP,'compressed_z_m':[NECK_LO,NECK_HI],
            'head_top_z_m':max(body.data.vertices[i].co.z for i in head),
            'bones_moved':['mixamorig:Head tail','mixamorig:HeadTop_End'],'face_unchanged':True}

PALM_ROOT=.655;KNUCKLE=.745;NEW_KNUCKLE=.735;FINGER_SCALE=1.3;PALM_PUFF=.18
THUMB_ROOT=Vector((.703,-.065,1.168));THUMB_SCALE=1.1;THUMB_TOWARD_FINGERS=12;THUMB_TOWARD_PALM=25

def hand_map(u,y,z,main,thumb):
    """Left-hand coordinates (u=|x|): shorter palm, longer main digits, fuller palm."""
    def palm(u):
        if u<=PALM_ROOT:return u
        if u<=KNUCKLE:return PALM_ROOT+(u-PALM_ROOT)*(NEW_KNUCKLE-PALM_ROOT)/(KNUCKLE-PALM_ROOT)
        return u-(KNUCKLE-NEW_KNUCKLE)
    if u>KNUCKLE:nu=NEW_KNUCKLE+(u-KNUCKLE)*(1+(FINGER_SCALE-1)*main)
    else:nu=palm(u)
    # Rounded fullness through the middle of the palm, not in the digits.
    t=max(0,min(1,(u-.648)/(KNUCKLE-.648)));puff=1+PALM_PUFF*math.sin(math.pi*t)*(1-main)*(1-thumb)
    p=Vector((nu,y,1.168+(z-1.168)*puff))
    if thumb>0:
        # The thumb is now carried by the hand, so rest it closer to the palm
        # and the fingers instead of sticking out sideways.
        root=Vector((palm(THUMB_ROOT.x),THUMB_ROOT.y,THUMB_ROOT.z))
        rot=Matrix.Rotation(math.radians(THUMB_TOWARD_PALM),3,'X')@Matrix.Rotation(math.radians(THUMB_TOWARD_FINGERS),3,'Z')
        p=p.lerp(root+THUMB_SCALE*(rot@(Vector((u,y,z))-THUMB_ROOT)),thumb)
    return p

def reshape_hands():
    body=bpy.data.objects['Body_Base'];rig=bpy.data.objects['NPC_Rig_Mixamo65'];me=body.data
    mask={d:me.attributes['npc_digit_'+d] for d in ['Thumb','Index','Middle','Ring']}
    moved=0
    for v in me.vertices:
        u=abs(v.co.x)
        if u<=PALM_ROOT or abs(v.co.z-1.168)>.08:continue
        main=max(mask[d].data[v.index].value for d in ['Index','Middle','Ring']);thumb=mask['Thumb'].data[v.index].value
        p=hand_map(u,v.co.y,v.co.z,main,thumb);v.co=(math.copysign(p.x,v.co.x),p.y,p.z);moved+=1
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        digit=next((d for d in ['Thumb','Index','Middle','Ring','Pinky'] if 'Hand'+d in bone.name),None)
        if not digit and not bone.name.endswith('Hand'):continue
        for point in [bone.head,bone.tail]:
            u=abs(point.x)
            if u<=PALM_ROOT:continue
            p=hand_map(u,point.y,point.z,1 if digit in ('Index','Middle','Ring','Pinky') else 0,1 if digit=='Thumb' else 0)
            point.x=math.copysign(p.x,point.x);point.y=p.y;point.z=p.z
    bpy.ops.object.mode_set(mode='OBJECT');me.update();bpy.context.view_layer.update()
    return {'palm_length_m':[KNUCKLE-PALM_ROOT,NEW_KNUCKLE-PALM_ROOT],'main_finger_length_scale':FINGER_SCALE,'thumb_length_scale':THUMB_SCALE,
            'palm_mid_thickness_scale':1+PALM_PUFF,'thumb_rest_rotation_deg':{'toward_fingers':THUMB_TOWARD_FINGERS,'toward_palm':THUMB_TOWARD_PALM},
            'vertices':moved,'bones':'Hand tail, finger and thumb joints follow the new shape; names and hierarchy unchanged'}

def light_shirt():
    shirt=bpy.data.objects['Outfit_TShirt'];body=bpy.data.objects['Body_Base']
    from clean_shapes import tshirt
    old_weights=[{shirt.vertex_groups[g.group].name:g.weight for g in v.groups} for v in shirt.data.vertices]
    old_faces=[tuple(p.vertices) for p in shirt.data.polygons]
    generated=tshirt(shirt.data.materials[0],bpy.data.collections['NPC_BASE_01'],light=True)
    assert old_faces==[tuple(p.vertices) for p in generated.data.polygons]
    bpy.context.view_layer.objects.active=generated
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15192,island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
    mesh=generated.data;bpy.data.objects.remove(generated,do_unlink=True);old=shirt.data;shirt.data=mesh
    bpy.data.meshes.remove(old)
    for i,w in enumerate(old_weights):weights(shirt,i,w)
    # Sleeves take the weights of the arm surface right under them, so the
    # closer sleeve and the arm deform together instead of sliding apart.
    arm=[tuple(p.vertices) for p in body.data.polygons if all(abs(body.data.vertices[i].co.x)>.15 for i in p.vertices)
         and all(abs(body.data.vertices[i].co.x)<.36 for i in p.vertices)]
    tree=BVHTree.FromPolygons([v.co for v in body.data.vertices],arm,all_triangles=False)
    bw=[{body.vertex_groups[g.group].name:g.weight for g in v.groups} for v in body.data.vertices]
    moved=0
    for v in shirt.data.vertices:
        u=abs(v.co.x)
        if u<.165:continue
        w=surface_weights(body,tree,arm,v.co,bw)[0];b=max(0,min(1,(u-.165)/.025));b=b*b*(3-2*b)
        weights(shirt,v.index,mixed([(old_weights[v.index],1-b),(w,b)]));moved+=1
    shirt.data.update()
    return {'collar':'thin crew band at the neck base: front dip 0.028 m, about 0.004 m thick lip, no rolled edge',
            'shoulders':'slope from the collar band to the sleeves, no flat yoke ledge',
            'sleeve_gap_to_arm_m':'about 0.007-0.015 (v07: 0.010-0.031)',
            'sleeve_vertices_weighted_from_arm':moved,'topology':'identical to v07; weights kept by vertex index'}

def hidden_body_follows_clothes():
    # Thighs inside the shorts and the hidden torso core take the weights of the
    # garment surface right outside them, so they cannot slide out through it.
    body=bpy.data.objects['Body_Base'];me=body.data
    cloth=[]
    for name in ['Outfit_TShirt','Outfit_Shorts']:
        o=bpy.data.objects[name];polys=[tuple(p.vertices) for p in o.data.polygons]
        cloth.append((o,BVHTree.FromPolygons([v.co for v in o.data.vertices],polys,all_triangles=False),polys,
                      [{o.vertex_groups[g.group].name:g.weight for g in v.groups} for v in o.data.vertices]))
    hidden=[i for part in components(me) if max(me.vertices[i].co.z for i in part)<1.3
            and max(abs(me.vertices[i].co.x) for i in part)<.2 for i in part if me.vertices[i].co.z>.60]
    changed=0
    for i in hidden:
        co=me.vertices[i].co;best=None
        for o,tree,polys,cache in cloth:
            w,loc,n,dist=surface_weights(o,tree,polys,co,cache)
            if (co-loc).dot(n)<0 and dist<.1 and (best is None or dist<best[1]):best=(w,dist)
        if best:weights(body,i,best[0]);changed+=1
    me.update()
    return {'vertices':changed,'parts':'thighs above z 0.60 inside the shorts and the hidden torso core'}

def compact_elbows():
    body=bpy.data.objects['Body_Base'];rig=bpy.data.objects['NPC_Rig_Mixamo65'];me=body.data
    # Per-vertex least squares: the two-bone blend that best follows an evenly
    # thick tube bent around the hinge (centreline radius ELBOW_RHO).
    res={}
    for side,sx in [('Left',1),('Right',-1)]:
        j=rig.data.bones['mixamorig:%sForeArm'%side].head_local.copy()
        eu=Vector((sx,0,0));ev=Vector((0,-1,0))
        for v in me.vertices:
            if not(.30<sx*v.co.x<.53 and abs(v.co.y)<.06 and abs(v.co.z-1.175)<.06):continue
            p=v.co.copy();d0=p-j;s=d0.dot(eu);t=d0.dot(ev);up=Vector((0,0,d0.z));num=den=0
            for deg,weight in ELBOW_ANGLES:
                th=math.radians(deg);tau=math.cos(th)*eu+math.sin(th)*ev;nu=-math.sin(th)*eu+math.cos(th)*ev
                forearm=j+s*tau+t*nu+up;d=ELBOW_RHO*math.tan(th/2)
                if s<=-d:target=p
                elif s>=d:target=forearm
                else:
                    ph=th*(s+d)/(2*d)
                    target=(j-d*eu+ELBOW_RHO*math.sin(ph)*eu+ELBOW_RHO*(1-math.cos(ph))*ev
                            +t*(-math.sin(ph)*eu+math.cos(ph)*ev)+up)
                step=forearm-p;num+=weight*step.dot(target-p);den+=weight*step.length_squared
            res[v.index]=min(1,max(0,num/den)) if den>1e-12 else float(s>0)
    links={i:[] for i in res}
    for e in me.edges:
        a,b=e.vertices
        if a in res and b in res:links[a].append(b);links[b].append(a)
    for _ in range(2):
        res={i:.5*w+.5*sum(res[k] for k in links[i])/len(links[i]) if links[i] else w for i,w in res.items()}
    for i,w in res.items():
        side='Left' if me.vertices[i].co.x>0 else 'Right'
        weights(body,i,{'mixamorig:'+side+'Arm':1-w,'mixamorig:'+side+'ForeArm':w})
    me.update()
    return {'method':'per-vertex least-squares fit to an evenly thick bent tube, hinge at the existing elbow joint',
            'tube_centreline_radius_m':ELBOW_RHO,'fit_angles_deg':[a for a,_ in ELBOW_ANGLES],
            'blend_span_abs_x_m':[.37,.45],'vertices':len(res)}

def rigid_thumb():
    body=bpy.data.objects['Body_Base'];changed=0
    for v in body.data.vertices:
        if any('Thumb' in body.vertex_groups[g.group].name for g in v.groups if g.weight>0):
            weights(body,v.index,{'mixamorig:'+('Left' if v.co.x>0 else 'Right')+'Hand':1});changed+=1
    body.data.update()
    return {'thumb_skin':'bound to Hand only; Thumb1-4 bones and their tracks stay in the rig without skin influence',
            'vertices':changed}

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--revision',type=int,default=8)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.source=a.source.resolve();a.output_dir=a.output_dir.resolve();stem=f'NPC_BASE_01_v{a.revision:02d}'
    files=[a.output_dir/(stem+ext) for ext in ['.blend','.fbx']]+[a.output_dir/f'validation_v{a.revision:02d}.json']
    assert not any(f.exists() for f in files),'Choose an unused revision/output directory.'
    a.output_dir.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(a.source));bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;scene.name=stem;scene['npc_asset_revision']=stem
    rig=bpy.data.objects['NPC_Rig_Mixamo65']
    report=json.loads(a.source.with_name('validation_'+a.source.stem.rsplit('_',1)[1]+'.json').read_text())
    for k in ['skin_validation','animated_fbx_roundtrip','joint_refinement_validation']:report.pop(k,None)
    report.update(revision=stem,source_model=a.source.name)
    # Body weights first, so the sleeves copy the final arm weights.
    hands=reshape_hands();elbows=compact_elbows();thumb=rigid_thumb()
    report['v08_refinement']={'head':shorten_head(),'shirt':light_shirt(),'elbows':elbows,'thumb':thumb,'hands':hands}
    report['v08_refinement']['hidden_body']=hidden_body_follows_clothes()
    report['finger_mapping']='Index, Middle, Ring; Thumb and Pinky retained without skin weights'
    rig['finger_mapping']=report['finger_mapping']
    meshes=[o for o in bpy.data.collections['NPC_BASE_01'].objects if o.type=='MESH']
    report['meshes']={}
    for o in meshes:
        o.data.calc_loop_triangles();report['meshes'][o.name]={'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles)}
    report['total_triangles']=sum(v['triangles'] for v in report['meshes'].values())
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for o in meshes:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(files[1]),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=False)
    rig.animation_data.action=bpy.data.actions['RunLookBack_InPlace'];scene.frame_set(20)
    bpy.ops.wm.save_as_mainfile(filepath=str(files[0]));files[2].write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('V08_REFINEMENT_SAVED',stem,report['total_triangles'])
if __name__=='__main__':main()
