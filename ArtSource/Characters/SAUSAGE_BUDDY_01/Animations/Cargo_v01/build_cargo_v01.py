"""Original cargo performances; read-only A v04 and GetUp_FromBack v02 inputs.
Blender --factory-startup --background --python build_cargo_v01.py -- --review 1
Use --final --revision N only after visual review. Never overwrites deliverables.
"""
from pathlib import Path
import sys, math, json, argparse, importlib.util
sys.dont_write_bytecode = True
import bpy
import numpy as np
from mathutils import Vector, Matrix, Quaternion
HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent
sys.path.insert(0, str(SRC))
import buddy_anim as A
import buddy_rig as RG
import buddy_render as RD
argv = sys.argv[:]
sys.argv = [argv[0]]
spec = importlib.util.spec_from_file_location('getup_helpers', HERE.parent/'GetUp_Idle_v01'/'build_getups.py')
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
sys.argv = argv
ap = argparse.ArgumentParser()
ap.add_argument('--final', action='store_true')
ap.add_argument('--preview', action='store_true')
ap.add_argument('--check-only', action='store_true')
ap.add_argument('--revision', type=int, default=1)
ap.add_argument('--review', type=int, default=1)
ap.add_argument('--clip', default='all')
args = ap.parse_args(argv[argv.index('--')+1:] if '--' in argv else [])
VERSION = f'v{args.revision:02}'
P = RG.P
CLIPS = {'SitUp_Cargo': 63, 'Cargo_Sit_Idle': 120, 'Cargo_Knock': 84}
WALL_X = -.55

def open_source():
    global scene, rig, rest, initial, sit, meshes
    bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'GetUp_Idle_v01'/'GetUp_FromBack_v02.blend'))
    bpy.context.scene.frame_set(1)
    initial = {b.name:b.matrix.copy() for b in bpy.data.objects['Buddy_Rig_Mixamo65'].pose.bones}
    G.open_source()
    scene, rig, rest, meshes = G.scene, G.rig, G.rest, G.meshes
    sit = floor_safe(seated_pose(0, 'idle', 4))[0]

def bounds(desired=None):
    if desired is not None: G.install(desired)
    points = []
    dg = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        v = np.empty(len(me.vertices)*3, dtype=np.float32); me.vertices.foreach_get('co', v)
        m = np.array(o.matrix_world)
        points.append(v.reshape((-1,3)) @ m[:3,:3].T + m[:3,3])
        ev.to_mesh_clear()
    v = np.concatenate(points)
    return v.min(axis=0), v.max(axis=0)

def floor_safe(out):
    lo, hi = bounds(out)
    lift = max(0, .0015-float(lo[2]))
    return A.apply_all(out, Matrix.Translation((0,0,lift))) if lift else out, lift

def curve(keys,t):
    if t<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*A.smooth((t-a)/(b-a))
    return keys[-1][1]

def curl(out,side,amount):
    # Three visible mitten finger chains, with preserved original joints.
    for finger in ('Index','Middle','Ring','Pinky'):
        for i,angle in ((1,68),(2,88),(3,65)):
            name=side+'Hand'+finger+str(i)
            A.rotate_subtree(out,rig,name,A.R((0,0,1),(-1 if side=='Left' else 1)*angle*amount))
    A.rotate_subtree(out,rig,side+'HandThumb1',A.R((0,0,1),(1 if side=='Left' else -1)*28*amount))

def seated_pose(t,kind,duration):
    env=math.sin(math.pi*t/duration)**2 if 0<t<duration else 0
    shake=math.sin(2*math.pi*6*t)*env
    yaw=0; tilt=0; twist=0; recoil=0
    if kind=='idle':
        yaw=curve([(0,0),(.45,0),(.8,38),(1.3,38),(1.7,0),(2.15,-46),(2.7,-46),(3.25,0),(duration,0)],t)
        tilt=3*math.sin(2*math.pi*t/duration)*env
    else:
        twist=curve([(0,0),(.32,0),(.65,-64),(2.10,-64),(2.48,0),(duration,0)],t)
        yaw=twist*.65
        # Fast impact, held contact and a slower withdrawal, three distinct knocks.
        impact=curve([(0,0),(.66,0),(.84,1),(.91,1),(1.08,0),(1.22,1),(1.29,1),(1.48,0),(1.63,1),(1.70,1),(1.95,0),(duration,0)],t)
        recoil=impact
    J=A.idle_joints()
    J['Hips']=A.R((1,0,0),-11)
    J['Spine']=A.R((1,0,0),10+env*1.2) @ A.R((0,0,1),twist*.35)
    J['Spine1']=A.R((1,0,0),-4+shake*.3) @ A.R((0,0,1),twist*.65)
    J['Spine2']=A.R((1,0,0),-3-recoil*3)
    J['Neck']=A.R((0,0,1),yaw) @ A.R((1,0,0),10+tilt+shake*.65)
    J['Head']=A.R((0,1,0),tilt+shake*.35) @ A.R((1,0,0),3)
    out=A.pose_from_joints(rig,rest,J,Vector((0,0,.19))-rest[P+'Hips'].translation)
    for side,sgn in [('Left',1),('Right',-1)]:
        foot,fq=G.grounded_foot(side,.17*sgn,-.49,-2,.002)
        G.solve_chain(out,side,'leg',foot,fq,(.12*sgn,-.45,1))
        hand=Vector((sgn*.165,-.36,.46+shake*.0015))
        hq=A.R((0,1,0),sgn*76) @ A.R((0,0,1),-sgn*20)
        if kind=='knock' and side=='Right':
            reach=curve([(0,0),(.28,0),(.65,1),(2.08,1),(2.55,0),(duration,0)],t)
            target=Vector((-.35,.15+.092*recoil,.64+.015*recoil))
            hand=hand.lerp(target,reach)
            hq=hq.slerp(A.R((0,0,1),90)@A.R((0,1,0),-12),reach)
        G.solve_chain(out,side,'arm',hand,hq,(sgn,-.1,-.25))
        curl(out,side,.18 if kind=='idle' or side=='Left' else reach)
    # The original supine start lies along Y, then turns to sit against the X wall.
    return A.apply_all(out,Matrix.Translation((-.24,0,0)) @ A.R((0,0,1),90).to_matrix().to_4x4())

def blend_local(a,b,u):
    out={}
    for n in RG.ordered(rig):
        bone=rig.data.bones[n];p=bone.parent.name if bone.parent else None
        ka={} if p is None else {'parent_matrix':a[p],'parent_matrix_local':rest[p]}
        kb={} if p is None else {'parent_matrix':b[p],'parent_matrix_local':rest[p]}
        aa=bone.convert_local_to_pose(a[n],rest[n],invert=True,**ka)
        bb=bone.convert_local_to_pose(b[n],rest[n],invert=True,**kb)
        basis=aa.to_quaternion().slerp(bb.to_quaternion(),u).to_matrix().to_4x4()
        if p is None:basis.translation=aa.translation.lerp(bb.translation,u)
        kw={} if p is None else {'parent_matrix':out[p],'parent_matrix_local':rest[p]}
        out[n]=bone.convert_local_to_pose(basis,rest[n],**kw)
    return out

def situp_pose(t,duration):
    if t<=.12:return {n:m.copy() for n,m in initial.items()}
    if t>=duration:return {n:m.copy() for n,m in sit.items()}
    u=A.smooth((t-.12)/.85)
    out=blend_local(initial,sit,u)
    # Dazed wobble and a right-temple rub after the pelvis settles.
    rub=curve([(0,0),(.85,0),(1.14,1),(1.53,1),(1.9,0),(duration,0)],t)
    if rub:
        A.rotate_subtree(out,rig,'Neck',A.R((1,0,0),7*math.sin(2*math.pi*(t-.85)/.6)*rub))
        side='Right';shoulder=out[P+side+'Arm'].translation
        target=out[P+'Head'].translation+Vector((.07,-.15,.07))
        target.z+=.012*math.sin(2*math.pi*4*t)*rub
        current=out[P+side+'Hand'].translation.copy()
        q=out[P+side+'Hand'].to_quaternion()@rest[P+side+'Hand'].to_quaternion().inverted()
        reference={n:m.copy() for n,m in out.items()}
        G.solve_chain(out,side,'arm',current.lerp(target,rub),q,(.2,-1,.05))
        # Fade the local elbow roll with the gesture, avoiding an abrupt IK entrance.
        G.blend_arm_local(out,reference,side,rub)
    return out

def author(name,period):
    frames={};lifts=[]
    for i in range(period*2+1):
        t=i/60
        if name=='SitUp_Cargo':out=situp_pose(t,period/30)
        else:out=seated_pose(t,'idle' if name=='Cargo_Sit_Idle' else 'knock',period/30)
        if name=='SitUp_Cargo' and t<=.12:lift=0
        else:out,lift=floor_safe(out)
        frames[1+i/2]=out;lifts.append(lift)
    if name!='SitUp_Cargo':frames[period+1]={n:m.copy() for n,m in frames[1].items()}
    else:frames[period+1]={n:m.copy() for n,m in sit.items()}
    action=RG.key_frames(rig,rest,frames,name+'_'+VERSION)
    action['duration_seconds']=period/30;action['fps']=30;action['loop']=name!='SitUp_Cargo'
    action['authoring']='Original FK / analytical IK cargo performance; supine pose from GetUp_FromBack_v02'
    scene.frame_start=1;scene.frame_end=period+1;scene.frame_set(1)
    return action,lifts

def preflight(name,period):
    low=10;high=-10;hiphi=0;step=0;bad=0
    for i in range(period*2+1):
        f=1+i/2;scene.frame_set(int(f),subframe=f%1)
        lo,hi=bounds();low=min(low,float(lo[2]));high=max(high,float(hi[2]))
        hiphi=max(hiphi,rig.pose.bones[P+'Hips'].head.z)
        for b in rig.pose.bones:bad+=sum(not math.isfinite(x) for row in b.matrix for x in row)
    curves=RG.fcurves_of(rig.animation_data.action)
    for n in rig.pose.bones.keys():
        fc=[next(x for x in curves if x.data_path==f'pose.bones["{n}"].rotation_quaternion' and x.array_index==c) for c in range(4)]
        for i in range(len(fc[0].keyframe_points)-1):
            a=Quaternion([x.keyframe_points[i].co.y for x in fc]).normalized()
            b=Quaternion([x.keyframe_points[i+1].co.y for x in fc]).normalized()
            step=max(step,math.degrees(2*math.acos(min(1,abs(a.dot(b))))))
    result={'min_mesh_z_m':low,'max_mesh_z_m':high,'max_hips_z_m':hiphi,'max_half_frame_rotation_deg':step,'nonfinite':bad}
    print('PREFLIGHT',name,json.dumps(result),flush=True)
    assert high<=1.2 and low>=-.001 and bad==0 and step<25,result
    scene.frame_set(1)
    return result

def export(name,action):
    stem=name+'_'+VERSION
    for ext in ('.blend','.fbx'):assert not (HERE/(stem+ext)).exists(),'Refusing overwrite '+stem+ext
    assert len(rig.data.bones)==65 and all(abs(x-1)<1e-6 for x in rig.scale)
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(stem+'.blend')))
    rig.animation_data.action=None
    for pb in rig.pose.bones:pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(HERE/(stem+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=True,
        bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0,
        axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=False)
    rig.animation_data.action=action;scene.frame_set(1)

def preview(name,period):
    folder=HERE/'Previews'/((name+'_'+VERSION) if args.final else f'Review_{args.review:02}')/name
    col,cam,floor=RD.studio(scene)
    scene.cycles.samples=12;scene.cycles.use_denoising=True
    scene.render.image_settings.file_format='PNG';scene.render.resolution_percentage=100
    # Wall is review geometry only, positioned at the cargo bay's side.
    mat=bpy.data.materials.new('Cargo_Wall_Review');mat.diffuse_color=(.2,.27,.32,1)
    me=bpy.data.meshes.new('Cargo_Wall_Review')
    me.from_pydata([(WALL_X,-1.2,0),(WALL_X,1.4,0),(WALL_X,1.4,1.3),(WALL_X,-1.2,1.3)],[],[(0,1,2,3)])
    me.materials.append(mat);wall=bpy.data.objects.new('Cargo_Wall_Review',me);col.objects.link(wall)
    times=([0,.2,.45,.7,.95,1.15,1.4,1.6,1.9,period/30] if name=='SitUp_Cargo' else
        [0,.48,.84,1.08,1.22,1.48,1.63,1.95,2.48,period/30] if name=='Cargo_Knock' else
        [0,.5,.8,1.3,1.7,2.15,2.7,3.25,3.65,period/30])
    for label,loc in [('side',(0,-5,1.7)),('three_quarter',(4,-4,2.5))]:
        for i,t in enumerate(times):
            path=folder/label/f'{name}_{VERSION}_{i:02}_{t:.2f}s.png'
            assert not path.exists(),'Refusing preview overwrite'
            f=1+t*30;scene.frame_set(int(f),subframe=f%1)
            RD.shot(scene,cam,path,loc,(0,0,.53),ortho=2.0,res=(480,480))
            print('RENDERED',name,label,i,flush=True)

if __name__=='__main__':
    for name,period in CLIPS.items():
        if args.clip not in ('all',name):continue
        open_source();action,lifts=author(name,period);check=preflight(name,period)
        if args.check_only:continue
        path=HERE/(name+'_'+VERSION+'_authoring.json' if args.final else f'Review_{args.review:02}_{name}_authoring.json')
        assert not path.exists(),'Refusing report overwrite'
        path.write_text(json.dumps({'clip':name+'_'+VERSION,'preflight':check,'max_floor_correction_m':max(lifts)},indent=2),encoding='utf-8')
        if args.final:export(name,action)
        if args.preview:preview(name,period)
