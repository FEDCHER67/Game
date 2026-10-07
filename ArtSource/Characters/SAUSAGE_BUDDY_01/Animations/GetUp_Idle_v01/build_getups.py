"""Original Buddy get-ups/idles. Read-only v04 inputs; no external motion/services.
Blender 5.2: -- --preview --review 1 or --final --revision 1.
Numbered deliverables and review renders are never overwritten.
"""
from pathlib import Path
import sys, math, json, argparse
sys.dont_write_bytecode=True
import bpy
from mathutils import Vector, Matrix, Quaternion
HERE=Path(__file__).resolve().parent
SRC=HERE.parent.parent
sys.path.insert(0,str(SRC))
import buddy_anim as A
import buddy_rig as RG
import buddy_render as RD
P=RG.P
ap=argparse.ArgumentParser()
ap.add_argument('--preview',action='store_true')
ap.add_argument('--final',action='store_true')
ap.add_argument('--check-only',action='store_true')
ap.add_argument('--revision',type=int,default=1)
ap.add_argument('--review',type=int,default=1)
ap.add_argument('--clip',default='all')
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
CLIPS={'GetUp_FromBack':78,'GetUp_FromBelly':75,'Idle_Variant_A':120,'Idle_Variant_B':120}
VERSION=f'v{args.revision:02}'

def open_source():
    bpy.ops.wm.open_mainfile(filepath=str(SRC/'SAUSAGE_BUDDY_A_v04.blend'))
    global scene,rig,meshes,rest,idle,base_hips,sole,footbase
    scene=bpy.context.scene;rig=bpy.data.objects['Buddy_Rig_Mixamo65']
    meshes=[bpy.data.objects[n] for n in ('Body','Face','Outfit')]
    rig.animation_data.action=bpy.data.actions['Idle'];scene.frame_set(1)
    idle={b.name:b.matrix.copy() for b in rig.pose.bones}
    base_hips=idle[P+'Hips'].translation.copy()
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    rig.animation_data_clear()
    for o in meshes:
        if o.data.shape_keys:
            o.data.shape_keys.animation_data_clear()
            for k in o.data.shape_keys.key_blocks:k.value=0
    for act in list(bpy.data.actions):bpy.data.actions.remove(act)
    for pb in rig.pose.bones:pb.matrix_basis.identity();pb.rotation_mode='QUATERNION'
    rig.data.pose_position='POSE';scene.render.fps=30
    sole={s:[v.co.copy() for v in meshes[2].data.vertices if v.co.z<.19 and v.co.x*sign>0
        and any(meshes[2].vertex_groups[g.group].name in (P+s+'Foot',P+s+'ToeBase') and g.weight>.5 for g in v.groups)]
        for s,sign in [('Left',1),('Right',-1)]}
    footbase={s:(idle[P+s+'Foot'].translation.copy(),
        idle[P+s+'Foot'].to_quaternion()@rest[P+s+'Foot'].to_quaternion().inverted()) for s in sole}

def install(desired):
    for n in RG.ordered(rig):
        pb=rig.pose.bones[n]
        kw={} if not pb.parent else {'parent_matrix':desired[pb.parent.name],'parent_matrix_local':rest[pb.parent.name]}
        pb.matrix_basis=pb.bone.convert_local_to_pose(desired[n],rest[n],invert=True,**kw)
    bpy.context.view_layer.update()

def mesh_low(desired):
    install(desired);dg=bpy.context.evaluated_depsgraph_get();low=10.
    for o in meshes:
        ev=o.evaluated_get(dg);me=ev.to_mesh()
        low=min(low,min((o.matrix_world@v.co).z for v in me.vertices));ev.to_mesh_clear()
    return low

def orient(n,head,tail,reference):
    # An explicit roll reference stays continuous when a bent elbow points
    # opposite its T-pose axis; shortest-arc rotation has a singularity there.
    y=(tail-head).normalized();x=reference-y*reference.dot(y)
    if x.length<1e-5:x=Vector((0,0,1))-y*y.z
    x.normalize();z=x.cross(y).normalized();x=y.cross(z).normalized()
    m=Matrix((x,y,z)).transposed().to_4x4();m.translation=head
    return m

def solve_chain(desired,side,kind,target,q,pole):
    names=[P+side+n for n in (('UpLeg','Leg','Foot') if kind=='leg' else ('Arm','ForeArm','Hand'))]
    upper,lower,end=names;h=desired[upper].translation.copy()
    l1=(rest[lower].translation-rest[upper].translation).length
    l2=(rest[end].translation-rest[lower].translation).length
    dvec=Vector(target)-h;d=dvec.length;direction=dvec.normalized()
    # No scaling/stretching; unreachable targets are projected to the reach sphere.
    d=min(l1+l2-1e-7,max(abs(l1-l2)+1e-7,d));target=h+direction*d
    along=(l1*l1-l2*l2+d*d)/(2*d)
    pole=Vector(pole);pole=(pole-direction*pole.dot(direction)).normalized()
    bend=math.sqrt(max(0,l1*l1-along*along));joint=h+direction*along+pole*bend
    # Both segments share the hinge plane. This avoids roll singularities when
    # the arm passes through vertical during a braced sit-to-crouch transition.
    reference=pole.cross(direction).normalized()*(-1 if kind=='leg' else 1)
    desired[upper]=orient(upper,h,joint,reference);desired[lower]=orient(lower,joint,target,reference)
    M=Matrix.Translation(target)@q.to_matrix().to_4x4()@Matrix.Translation(-rest[end].translation)
    for n in A.subtree(rig,side+('Foot' if kind=='leg' else 'Hand')):desired[n]=M@rest[n]

def blend_arm_local(out,reference,side,weight):
    names=A.subtree(rig,side+'Arm');bases={}
    for n in names:
        b=rig.data.bones[n];p=b.parent.name
        qa=b.convert_local_to_pose(out[n],rest[n],parent_matrix=out[p],parent_matrix_local=rest[p],invert=True).to_quaternion()
        qb=b.convert_local_to_pose(reference[n],rest[n],parent_matrix=reference[p],parent_matrix_local=rest[p],invert=True).to_quaternion()
        bases[n]=qb.slerp(qa,weight).to_matrix().to_4x4()
    for n in names:
        b=rig.data.bones[n];p=b.parent.name
        out[n]=b.convert_local_to_pose(bases[n],rest[n],parent_matrix=out[p],parent_matrix_local=rest[p])

def grounded_foot(side,x,y,pitch=0,clearance=0):
    q=A.R((1,0,0),pitch)@footbase[side][1]
    ankle_rest=rest[P+side+'Foot'].translation
    low=min((q@(v-ankle_rest)).z for v in sole[side])
    return Vector((x,y,-low+clearance)),q

def interp(keys,t):
    if t<=keys[0][0]:return dict(keys[0][1])
    for (ta,a),(tb,b) in zip(keys,keys[1:]):
        if t<=tb:
            u=A.smooth((t-ta)/(tb-ta));out={}
            for n in a:
                if isinstance(a[n],Quaternion):out[n]=a[n].slerp(b[n],u)
                elif isinstance(a[n],Vector):out[n]=a[n].lerp(b[n],u)
                else:out[n]=a[n]+(b[n]-a[n])*u
            return out
    return dict(keys[-1][1])

def initial_pose(belly):
    J=A.idle_joints(0,arm_down=62)
    J['LeftForeArm']=A.R((1,0,0),-5);J['RightForeArm']=A.R((1,0,0),-5)
    J['LeftUpLeg']=A.R((0,1,0),-1);J['RightUpLeg']=A.R((0,1,0),1)
    desired=A.pose_from_joints(rig,rest,J)
    pivot=rest[P+'Hips'].translation
    M=Matrix.Translation((0,0,.22))@A.R((1,0,0),90 if belly else -90).to_matrix().to_4x4()@Matrix.Translation(-pivot)
    desired=A.apply_all(desired,M)
    low=mesh_low(desired)
    return A.apply_all(desired,Matrix.Translation((0,0,-low+.0005)))

def getup_keys(belly,duration):
    initial=initial_pose(belly)
    def state(z,pitch,spine,neck,head,roll,ly,ry,lp=0,rp=0,lh=None,rh=None,clearL=0,clearR=0):
        d={'z':z,'pitch':pitch,'spine':spine,'neck':neck,'head':head,'roll':roll}
        for side,sgn,y,fp,hand,clear in [('Left',1,ly,lp,lh,clearL),('Right',-1,ry,rp,rh,clearR)]:
            ft,fq=grounded_foot(side,footbase[side][0].x,y,fp,clear)
            d[side+'Foot']=ft;d[side+'FootQ']=fq
            d[side+'Hand']=Vector(hand) if hand else idle[P+side+'Hand'].translation.copy()
            # The rest hand surface is in XY. Keep it horizontal, fingers forward.
            palm=A.R((0,0,1),-sgn*90)
            d[side+'HandQ']=palm
        return d
    start=state(initial[P+'Hips'].translation.z,90 if belly else -90,0,0,0,0,0,0)
    for s in sole:
        start[s+'Foot']=initial[P+s+'Foot'].translation.copy()
        start[s+'FootQ']=initial[P+s+'Foot'].to_quaternion()@rest[P+s+'Foot'].to_quaternion().inverted()
        start[s+'Hand']=initial[P+s+'Hand'].translation.copy()
        start[s+'HandQ']=initial[P+s+'Hand'].to_quaternion()@rest[P+s+'Hand'].to_quaternion().inverted()
    if belly:
        keys=[(0,start),(.14,start),
          (.38,state(.24,88,0,-12,0,0,.61,.61,75,75,(.32,-.36,.035),(-.32,-.36,.035))),
          (.70,state(.255,64,-8,-18,8,0,.61,.61,65,65,(.32,-.40,.035),(-.32,-.40,.035))),
          (1.04,state(.375,31,0,-8,-12,-3,-.20,.37,0,58,(.30,-.32,.30),(-.31,-.24,.25))),
          (1.30,state(.48,17,4,-8,4,0,-.20,.34,0,48,(.30,-.32,.50),(-.30,-.25,.43))),
          (1.62,state(.65,12,0,-6,0,3,-.10,.10,0,0,(.36,-.27,.68),(-.34,-.25,.68))),
          (1.90,state(.805,-5,0,3,12,5,0,0,0,0,(.38,-.08,.74),(-.38,-.08,.74))),
          (2.10,state(.805,3,0,-3,-13,-4,0,0,0,0,(.34,-.10,.73),(-.34,-.10,.73))),
          (2.28,state(.814,-1,0,1,5,1,0,0)),(duration,state(base_hips.z,0,0,0,0,0,0,0))]
    else:
        keys=[(0,start),(.16,start),
          (.46,state(.215,-64,0,12,0,0,-.61,-.61,-60,-60,(.34,.30,.115),(-.34,.30,.115))),
          (.80,state(.18,-32,-5,28,16,0,-.59,-.59,-8,-8,(.30,.22,.035),(-.30,.22,.035))),
          (1.00,state(.18,-30,-5,25,-18,4,-.54,-.56,0,0,(.30,.22,.035),(-.30,.22,.035))),
          (1.25,state(.265,65,-5,-35,8,0,-.23,-.30,0,0,(.33,-.32,.035),(-.33,-.32,.035))),
          (1.53,state(.43,28,-8,-8,0,-2,-.06,.04,0,0,(.34,-.31,.40),(-.32,-.30,.38))),
          (1.85,state(.685,10,0,-5,0,2,0,0,0,0,(.38,-.27,.67),(-.38,-.27,.67))),
          (2.05,state(.805,-5,0,4,-14,-5,0,0,0,0,(.38,-.08,.74),(-.38,-.08,.74))),
          (2.24,state(.807,3,0,-3,13,4,0,0,0,0,(.34,-.09,.73),(-.34,-.09,.73))),
          (2.42,state(.814,-1,0,1,-4,0,0,0)),(duration,state(base_hips.z,0,0,0,0,0,0,0,0))]
    for t,d in keys:
        if t>=(2.28 if belly else 2.42):
            for s in sole:
                d[s+'HandQ']=idle[P+s+'Hand'].to_quaternion()@rest[P+s+'Hand'].to_quaternion().inverted()
        elif t>=(1.04 if belly else 1.53):
            for s,sign in [('Left',1),('Right',-1)]:
                d[s+'HandQ']=A.R((0,1,0),sign*70)@A.R((1,0,0),-8)
    return initial,keys

def getup_pose(t,duration,initial,keys):
    if t<=.14:return {n:m.copy() for n,m in initial.items()}
    if t>=duration:return {n:m.copy() for n,m in idle.items()}
    d=interp(keys,t);J=A.idle_joints()
    J['Hips']=A.R((1,0,0),d['pitch'])@A.R((0,1,0),d['roll'])
    J['Spine']=A.R((1,0,0),d['spine'])
    J['Neck']=A.R((1,0,0),d['neck'])@A.R((0,0,1),d['head'])
    J['Head']=A.R((0,1,0),d['roll']*.6)
    out=A.pose_from_joints(rig,rest,J,Vector((0,0,d['z']-rest[P+'Hips'].translation.z)))
    for s,sign in [('Left',1),('Right',-1)]:
        # Raised knee while seated, gradually turn the knee pole forwards for standing.
        up=(3*A.smooth((1.25-t)/.6) if keys[0][1]['pitch']<0 else -3*(1-A.smooth((t-.38)/.66)))
        solve_chain(out,s,'leg',d[s+'Foot'],d[s+'FootQ'],(.05*sign,-1,up))
        solve_chain(out,s,'arm',d[s+'Hand'],d[s+'HandQ'],(sign,0,.15))
        if t<.38:blend_arm_local(out,initial,s,A.smooth((t-.14)/.24))
        if t>duration-.40:blend_arm_local(out,idle,s,1-A.smooth((t-(duration-.40))/.40))
    return out

def pulse(t,a,b):
    return math.sin(math.pi*(t-a)/(b-a))**2 if a<t<b else 0.

def idle_pose(t,variant,duration):
    if t<=0 or t>=duration:return {n:m.copy() for n,m in idle.items()}
    phase=t/duration;env=math.sin(math.pi*phase)**2
    J=A.idle_joints();weight=(math.sin(2*math.pi*phase)*.032*env if variant=='A' else .026*env)
    bob=(-.016*env if variant=='A' else -.012*env)
    J['Hips']=A.R((0,1,0),(-3 if variant=='A' else -2)*env)
    J['Spine']=A.R((0,1,0),(3 if variant=='A' else 2)*env)
    J['Spine1']=A.R((1,0,0),1.6*math.sin(2*math.pi*phase)*env)
    J['Neck']=A.R((0,0,1),26*pulse(t,.35,1.65)-32*pulse(t,1.8,3.25)) if variant=='A' else A.R((0,1,0),-6*pulse(t,1.3,3.3))
    J['Head']=A.R((1,0,0),(-4 if variant=='A' else 4)*env)
    if variant=='B':
        k=pulse(t,1.35,3.55)
        scratch=math.sin(2*math.pi*4*(t-2))*pulse(t,2.0,3.0)
        # An authored shoulder/elbow arc avoids crossing the IK elbow singularity
        # while the hand passes the shoulder. Fingers reach the right temple.
        J['RightArm']=A.R((1,0,0),-4+5*k)@A.R((0,1,0),-74+124*k)
        J['RightForeArm']=A.R((0,1,0),100*k+3*scratch)@A.R((1,0,0),-14*(1-k))
        J['RightHand']=A.R((0,1,0),-6-61*k-3*scratch)
    out=A.pose_from_joints(rig,rest,J,base_hips-rest[P+'Hips'].translation+Vector((weight,0,bob)))
    for s,sign in [('Left',1),('Right',-1)]:
        lift=0;pitch=0
        if variant=='B' and s=='Right':
            tap=sum(pulse(t,a,a+.35) for a in (.48,.97,1.46))
            lift=.022*tap;pitch=-14*tap
        ankle,q=grounded_foot(s,footbase[s][0].x,footbase[s][0].y,pitch,lift)
        solve_chain(out,s,'leg',ankle,q,(.05*sign,-1,0))
    return out

def make_clip(name,period):
    duration=period/30
    if name.startswith('GetUp'):
        initial,keys=getup_keys('Belly' in name,duration)
        fn=lambda t:getup_pose(t,duration,initial,keys)
    else:fn=lambda t:idle_pose(t,name[-1],duration)
    frames={};floor_corrections=[]
    for i in range(period*2+1):
        t=i/60;desired=fn(t)
        # Floor recovery stages use the actual skinned geometry, including palms,
        # hoodie and knees. This does not change any bone length or source data.
        if name.startswith('GetUp') and t<1.7:
            low=mesh_low(desired)
            correction=max(0,.0005-low)
            if correction:desired=A.apply_all(desired,Matrix.Translation((0,0,correction)))
            floor_corrections.append({'time_s':t,'lift_m':correction})
        frames[1+i/2]=desired
    if name.startswith('Idle'):frames[period+1]={n:m.copy() for n,m in frames[1].items()}
    else:frames[period+1]={n:m.copy() for n,m in idle.items()}
    action=RG.key_frames(rig,rest,frames,name+'_'+VERSION)
    action['authoring']='Original character-frame FK and analytical two-bone IK; no source motion reused'
    action['duration_seconds']=duration;action['fps']=30;action['loop']=name.startswith('Idle')
    action['idle_reference']='Original SAUSAGE_BUDDY_A_v04 Idle frame 1'
    scene.frame_start=1;scene.frame_end=period+1;scene.frame_set(1)
    return action,floor_corrections

def preflight(name,period):
    indices={s:[v.index for v in meshes[2].data.vertices if v.co.z<.19 and v.co.x*sgn>0
        and any(meshes[2].vertex_groups[g.group].name in (P+s+'Foot',P+s+'ToeBase') and g.weight>.5 for g in v.groups)]
        for s,sgn in [('Left',1),('Right',-1)]}
    penetration=0.;ground_error=0.;nan=0;reflections=0
    for i in range(period*2+1):
        f=1+i/2;t=i/60;scene.frame_set(int(f),subframe=f%1)
        for b in rig.pose.bones:
            nan+=sum(not math.isfinite(x) for row in b.matrix for x in row)
            reflections+=int(b.matrix.to_3x3().determinant()<=0)
        if name.startswith('GetUp') and t<1.7:continue
        ev=meshes[2].evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
        for s in indices:
            low=min((meshes[2].matrix_world@me.vertices[j].co).z for j in indices[s]);penetration=max(penetration,-low)
            tapping=name=='Idle_Variant_B' and s=='Right' and any(a<t<a+.35 for a in (.48,.97,1.46))
            if not tapping:ground_error=max(ground_error,abs(low))
        ev.to_mesh_clear()
    curves=RG.fcurves_of(rig.animation_data.action);maxstep=0.;step_at=None
    for n in rig.pose.bones.keys():
        channels=[next(fc for fc in curves if fc.data_path==f'pose.bones["{n}"].rotation_quaternion' and fc.array_index==c) for c in range(4)]
        for i in range(len(channels[0].keyframe_points)-1):
            a=Quaternion([fc.keyframe_points[i].co.y for fc in channels]).normalized()
            b=Quaternion([fc.keyframe_points[i+1].co.y for fc in channels]).normalized()
            step=math.degrees(2*math.acos(min(1.,abs(a.dot(b)))))
            if step>maxstep:maxstep=step;step_at=[n,channels[0].keyframe_points[i+1].co.x]
    result={'standing_sole_penetration_m':penetration,'standing_ground_error_m':ground_error,
        'nonfinite_components':nan,'reflected_samples':reflections,'max_half_frame_rotation_step_deg':maxstep,'max_step_at':step_at}
    print('PREFLIGHT',name,json.dumps(result),flush=True)
    assert nan==0 and reflections==0 and penetration<.001 and ground_error<.005 and maxstep<25,result
    scene.frame_set(1)
    return result

def export_clip(name,period,action):
    stem=name+'_'+VERSION
    for ext in ('.blend','.fbx'):assert not (HERE/(stem+ext)).exists(),'Refusing overwrite '+stem+ext
    # Pre-export gate: only unchanged, identity-scale rig is exported; 0 meshes.
    assert len(rig.data.bones)==65 and all(abs(s-1)<1e-6 for s in rig.scale)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(stem+'.blend')))
    rig.animation_data.action=None
    for pb in rig.pose.bones:pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(HERE/(stem+'.fbx')),use_selection=True,
        object_types={'ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,
        bake_anim_step=.5,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',
        apply_unit_scale=True,use_mesh_modifiers=False)
    rig.animation_data.action=action;scene.frame_set(1)
    print('EXPORTED',stem,flush=True)

def render_review(name,period):
    folder=HERE/'Previews'/((name+'_'+VERSION) if args.final else ('Review_%02d'%args.review))/name
    col,cam,floor=RD.studio(scene)
    # Small real-time previews for pose review; retain the original studio palette.
    scene.render.engine='CYCLES';scene.cycles.samples=12
    scene.cycles.use_denoising=True;scene.render.image_settings.file_format='PNG'
    scene.render.resolution_percentage=100
    times=([0,.38,.70,1.04,1.30,1.62,1.90,2.10,2.28,period/30] if 'Belly' in name else
        [0,.46,.80,1.0,1.25,1.53,1.85,2.05,2.24,period/30] if 'Back' in name else
        [0,.65,1.0,1.5,2.0,2.45,2.8,3.2,3.6,period/30])
    for label,loc in [('side',(5,0,1.65)),('three_quarter',(-3.7,-5,2.65))]:
        for idx,t in enumerate(times):
            path=folder/label/f'{name}_{VERSION}_{idx:02d}_{t:.2f}s.png'
            assert not path.exists(),'Refusing preview overwrite '+str(path)
            frame=1+t*30;scene.frame_set(int(frame),subframe=frame%1)
            RD.shot(scene,cam,path,loc,(0,0,.85),ortho=2.55,res=(480,480))
            print('RENDERED',name,label,idx,flush=True)

if __name__=='__main__':
    for name,period in CLIPS.items():
        if args.clip not in ('all',name):continue
        open_source();act,corrections=make_clip(name,period)
        if args.check_only:
            preflight(name,period)
            continue
        report=HERE/(name+'_'+VERSION+'_authoring.json' if args.final else f'Review_{args.review:02d}_{name}_authoring.json')
        assert not report.exists(),'Refusing report overwrite'
        check=preflight(name,period)
        report.write_text(json.dumps({'clip':name+'_'+VERSION,'duration_s':period/30,
            'floor_corrections':corrections,'preflight':check,'review_frames':'See labeled contact sheets'},indent=2),encoding='utf-8')
        if args.final:export_clip(name,period,act)
        if args.preview:render_review(name,period)
