"""v07 to v09: all v08 repairs (refine_npc_v08.py) with the softer cartoon hand of
TASK-000049, fingers kept together in the clips and a soft sausage head that
bends on the existing Neck/Head bones with a baked spring lag."""
import bpy,math,json,argparse,sys
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import refine_npc_v08 as v08
from refine_npc_joints import weights

KNUCKLE=.745;FINGER_Y={'Index':-.047,'Middle':0,'Ring':.047,'Pinky':.047}
FINGER_SCALE=.9;FINGER_SPACING=1.04;FINGER_WIDTH=1.25;FINGER_THICK=1.12
PALM_WIDEN=1.06;PALM_PUFF=.2;THUMB_THICK=1.12
THUMB_ROOT=Vector((.703,-.065,1.168));THUMB_DIR=Vector((.866,-.5,0)).normalized()
# Soft sausage: Spine2 -> Neck -> Head blend heights and the baked spring.
NECK_PIVOT=1.21;HEAD_PIVOT=1.45;BLEND_NECK=(1.245,1.40);BLEND_HEAD=(1.40,1.56)
SPRING_HZ=2.2;SPRING_DAMPING=.35;SPRING_TIP_Z=1.62;MAX_BEND_DEG=10

def smooth(lo,hi,x):
    t=max(0,min(1,(x-lo)/(hi-lo)));return t*t*(3-2*t)

def soft_hand(u,y,z,digit,main,thumb):
    """Left-hand coordinates (u=|x|) of v07: fuller wider palm, shorter thicker
    fingers closed up side by side, thicker thumb resting near the palm."""
    widen=1+(PALM_WIDEN-1)*smooth(.648,.70,u)
    puff=1+PALM_PUFF*math.sin(math.pi*max(0,min(1,(u-.648)/(KNUCKLE-.648))))
    nu=KNUCKLE+(u-KNUCKLE)*(1+(FINGER_SCALE-1)*main) if u>KNUCKLE else u
    yc=FINGER_Y.get(digit,0)
    ny=(1-main)*widen*y+main*(FINGER_SPACING*yc+FINGER_WIDTH*(y-yc))
    nz=1.168+(z-1.168)*((1-main)*puff+main*FINGER_THICK)
    p=Vector((nu,ny,nz))
    if thumb>0:
        d=Vector((u,y,z))-THUMB_ROOT;along=d.dot(THUMB_DIR)*THUMB_DIR;d=along+THUMB_THICK*(d-along)
        rot=Matrix.Rotation(math.radians(v08.THUMB_TOWARD_PALM),3,'X')@Matrix.Rotation(math.radians(v08.THUMB_TOWARD_FINGERS),3,'Z')
        root=Vector((THUMB_ROOT.x,THUMB_ROOT.y*(1+(PALM_WIDEN-1)*smooth(.648,.70,THUMB_ROOT.x)),THUMB_ROOT.z))
        p=p.lerp(root+rot@d,thumb)
    return p

def reshape_hands():
    body=bpy.data.objects['Body_Base'];rig=bpy.data.objects['NPC_Rig_Mixamo65'];me=body.data
    mask={d:me.attributes['npc_digit_'+d] for d in ['Thumb','Index','Middle','Ring']}
    for v in me.vertices:
        u=abs(v.co.x)
        if u<=.648 or abs(v.co.z-1.168)>.08:continue
        digit=max(['Index','Middle','Ring'],key=lambda d:mask[d].data[v.index].value)
        p=soft_hand(u,v.co.y,v.co.z,digit,mask[digit].data[v.index].value,mask['Thumb'].data[v.index].value)
        v.co=(math.copysign(p.x,v.co.x),p.y,p.z)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in rig.data.edit_bones:
        digit=next((d for d in ['Thumb','Index','Middle','Ring','Pinky'] if 'Hand'+d in bone.name),None)
        if not digit:continue
        for point in [bone.head,bone.tail]:
            p=soft_hand(abs(point.x),point.y,point.z,digit,0 if digit=='Thumb' else 1,1 if digit=='Thumb' else 0)
            point.x=math.copysign(p.x,point.x);point.y=p.y;point.z=p.z
    bpy.ops.object.mode_set(mode='OBJECT');me.update();bpy.context.view_layer.update()
    return {'main_finger_length_scale_from_v07':FINGER_SCALE,'finger_width_scale':FINGER_WIDTH,'finger_thickness_scale':FINGER_THICK,
            'finger_spacing_scale':FINGER_SPACING,'palm_width_scale':PALM_WIDEN,'palm_mid_thickness_scale':1+PALM_PUFF,
            'thumb_thickness_scale':THUMB_THICK,'thumb':'skinned to Hand, rests 25 deg toward the palm and 12 deg toward the fingers'}

def fingers_together():
    # Keep only the curl of the Mixamo finger keys; drop the human spread/twist.
    rig=bpy.data.objects['NPC_Rig_Mixamo65'];names=[b.name for b in rig.pose.bones if any('Hand'+d in b.name for d in ['Index','Middle','Ring','Pinky'])]
    removed=0
    for action in [bpy.data.actions['RunLookBack_InPlace'],bpy.data.actions['RunLookBack_RootMotion']]:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for name in names:
                        fc=[bag.fcurves.find('pose.bones["%s"].rotation_quaternion'%name,index=i) for i in range(4)]
                        if None in fc:continue
                        for k in range(len(fc[0].keyframe_points)):
                            w,x,y,z=(c.keyframe_points[k].co[1] for c in fc)
                            removed=max(removed,math.degrees(2*math.atan2(math.hypot(y,z),math.hypot(w,x))))
                            n=math.hypot(w,x) or 1
                            for c,val in zip(fc,(w/n,x/n,0,0)):c.keyframe_points[k].co[1]=val;c.keyframe_points[k].handle_left[1]=c.keyframe_points[k].handle_right[1]=val
                        for c in fc:c.update()
    return {'kept':'curl about each finger bone local X','max_removed_spread_twist_deg':round(removed,2)}

def soft_sausage():
    body=bpy.data.objects['Body_Base'];face=bpy.data.objects['Face_Expressions'];rig=bpy.data.objects['NPC_Rig_Mixamo65']
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT');eb=rig.data.edit_bones
    eb['mixamorig:Neck'].tail.z=HEAD_PIVOT;eb['mixamorig:Head'].head.z=HEAD_PIVOT
    assert abs(eb['mixamorig:Neck'].head.z-NECK_PIVOT)<1e-4
    bpy.ops.object.mode_set(mode='OBJECT')
    # The volume above the collar now bends on Neck and then Head; the part
    # inside the collar and the collar rim stay on Spine2.
    def w(z):
        n=smooth(*BLEND_NECK,z);h=smooth(*BLEND_HEAD,z)
        return {'mixamorig:Spine2':1-n,'mixamorig:Neck':n-h,'mixamorig:Head':h}
    for i in v08.head_parts(body.data):weights(body,i,w(body.data.vertices[i].co.z))
    for v in face.data.vertices:weights(face,v.index,w(v.co.z))
    body.data.update();face.data.update()
    rest={n:rig.data.bones['mixamorig:'+n].matrix_local.copy() for n in ['Spine2','Neck','Head']}
    tip0=rest['Spine2'].inverted()@Vector((0,0,SPRING_TIP_Z));base0=rest['Spine2'].inverted()@Vector((0,0,NECK_PIVOT))
    omega=2*math.pi*SPRING_HZ;stats={};keys={}
    # The lag is simulated on the in-place clip (same body motion; the steady
    # forward travel of the root-motion clip adds no inertia) and keyed on both.
    for action in [bpy.data.actions['RunLookBack_InPlace']]:
        rig.animation_data.action=action
        if action.slots:rig.animation_data.action_slot=next(s for s in action.slots if s.target_id_type=='OBJECT')
        frames=list(range(1,69));T={};B={};M={}
        for f in frames:
            bpy.context.scene.frame_set(f);m=rig.pose.bones['mixamorig:Spine2'].matrix.copy()
            M[f]=m;T[f]=m@tip0;B[f]=m@base0
        # The run is a loop: simulate three passes, keep the last.
        P=T[1].copy();V=Vector();sub=8;dt=1/30/sub;lag={}
        for loop in range(3):
            for f in frames:
                a,b=T[f],T[f%68+1]
                vel=(b-a)*30
                for s in range(sub):
                    target=a.lerp(b,s/sub);acc=omega*omega*(target-P)+2*SPRING_DAMPING*omega*(vel-V)
                    V+=acc*dt;P+=V*dt
                if loop==2:lag[f]=P.copy()
        angles=[]
        for f in frames:
            bpy.context.scene.frame_set(f)
            q=(T[f]-B[f]).rotation_difference(lag[f]-B[f])
            angle=min(q.angle,math.radians(MAX_BEND_DEG));q=Quaternion(q.axis,angle) if q.angle>1e-9 else Quaternion()
            angles.append(math.degrees(angle))
            half=Quaternion(q.axis,angle/2) if angle>0 else Quaternion()
            # Same half bend at both pivots: a soft curve, not a hinge at the collar.
            for name in ['Neck','Head']:
                pb=rig.pose.bones['mixamorig:'+name];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion()
                bpy.context.view_layer.update()
                frame=pb.matrix.to_quaternion()
                local=frame.inverted()@half@frame
                if f>1 and local.dot(prev[name])<0:local.negate()
                pb.rotation_quaternion=local;bpy.context.view_layer.update()
                pb.keyframe_insert('rotation_quaternion',frame=f,group=pb.name)
            prev={n:rig.pose.bones['mixamorig:'+n].rotation_quaternion.copy() for n in ['Neck','Head']}
            keys[f]=prev
        stats={'max_bend_deg':round(max(angles),2),'mean_bend_deg':round(sum(angles)/len(angles),2)}
    action=bpy.data.actions['RunLookBack_RootMotion'];rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=next(s for s in action.slots if s.target_id_type=='OBJECT')
    for f,q in keys.items():
        for name,value in q.items():
            pb=rig.pose.bones['mixamorig:'+name];pb.rotation_quaternion=value;pb.keyframe_insert('rotation_quaternion',frame=f,group=pb.name)
    rig.animation_data.action=bpy.data.actions['RunLookBack_InPlace']
    if rig.animation_data.action.slots:rig.animation_data.action_slot=next(s for s in rig.animation_data.action.slots if s.target_id_type=='OBJECT')
    rig['sausage_binding']='Collar rim and the head base inside it on Spine2; the visible sausage bends softly on Neck then Head. Human Neck/Head tracks are replaced by a baked spring lag.'
    return {'weights':{'spine2_to_neck_z_m':BLEND_NECK,'neck_to_head_z_m':BLEND_HEAD},'bones':{'Neck':[NECK_PIVOT,HEAD_PIVOT],'Head_pivot':HEAD_PIVOT},
            'spring':{'frequency_hz':SPRING_HZ,'damping_ratio':SPRING_DAMPING,'tip_z_m':SPRING_TIP_Z,'max_bend_deg':MAX_BEND_DEG},'clips':stats,
            'unity':'clips carry the baked lag; gameplay-driven lag (turns/stops in game) needs a small runtime spring on Neck/Head at integration'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True);p.add_argument('--revision',type=int,default=9)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);a.source=a.source.resolve();a.output_dir=a.output_dir.resolve();stem=f'NPC_BASE_01_v{a.revision:02d}'
    files=[a.output_dir/(stem+ext) for ext in ['.blend','.fbx']]+[a.output_dir/f'validation_v{a.revision:02d}.json']
    assert not any(f.exists() for f in files),'Choose an unused revision/output directory.'
    a.output_dir.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(a.source));bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;scene.name=stem;scene['npc_asset_revision']=stem;rig=bpy.data.objects['NPC_Rig_Mixamo65']
    report=json.loads(a.source.with_name('validation_'+a.source.stem.rsplit('_',1)[1]+'.json').read_text())
    for k in ['skin_validation','animated_fbx_roundtrip','joint_refinement_validation','hidden_fold_check']:report.pop(k,None)
    report.update(revision=stem,source_model=a.source.name)
    hands=reshape_hands();elbows=v08.compact_elbows();thumb=v08.rigid_thumb()
    report['v08_refinement']={'head':v08.shorten_head(),'shirt':v08.light_shirt(),'elbows':elbows,'thumb':thumb}
    report['v08_refinement']['hidden_body']=v08.hidden_body_follows_clothes()
    report['v09_refinement']={'hands':hands,'fingers_in_clips':fingers_together(),'soft_sausage':soft_sausage()}
    report['finger_mapping']=rig['finger_mapping']='Index, Middle, Ring; Thumb and Pinky retained without skin weights'
    meshes=[o for o in bpy.data.collections['NPC_BASE_01'].objects if o.type=='MESH'];report['meshes']={}
    for o in meshes:
        o.data.calc_loop_triangles();report['meshes'][o.name]={'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles)}
    report['total_triangles']=sum(v['triangles'] for v in report['meshes'].values())
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for o in meshes:o.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(files[1]),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=False)
    rig.animation_data.action=bpy.data.actions['RunLookBack_InPlace'];scene.frame_set(20)
    bpy.ops.wm.save_as_mainfile(filepath=str(files[0]));files[2].write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('V09_SAVED',stem,report['total_triangles'],json.dumps(report['v09_refinement']['soft_sausage']['clips']),json.dumps(report['v09_refinement']['fingers_in_clips']))
if __name__=='__main__':main()
