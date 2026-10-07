"""Original procedural walk on the unchanged Buddy v04 rig. No external motion.
Run in Blender 5.2 background; --preview skips deliverables, --final exports once.
The original A/B blend and FBX files are read-only inputs.
"""
from pathlib import Path
import sys, math, argparse
import bpy
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
SRC = HERE.parent.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(SRC))
import buddy_anim as A
import buddy_rig as RG
import buddy_render as RD
P = RG.P
FPS, PERIOD, SPEED, STANCE = 30, 20, 1.5, 0.55
DURATION = PERIOD/FPS
FINAL = '--final' in sys.argv
ap=argparse.ArgumentParser()
ap.add_argument('--revision',type=int,default=3)
args,_=ap.parse_known_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
STEM=f'Walk_v{args.revision:02}'
if FINAL:
    for name in (STEM+'.blend',STEM+'.fbx'):
        assert not (HERE/name).exists(), f'Refusing to overwrite {name}'

bpy.ops.wm.open_mainfile(filepath=str(SRC/'SAUSAGE_BUDDY_A_v04.blend'))
scene = bpy.context.scene
rig = bpy.data.objects['Buddy_Rig_Mixamo65']
meshes = [bpy.data.objects[n] for n in ('Body','Face','Outfit')]
rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
rig.animation_data_clear()
for o in meshes:
    if o.data.shape_keys:
        o.data.shape_keys.animation_data_clear()
        for k in o.data.shape_keys.key_blocks: k.value = 0
for act in list(bpy.data.actions): bpy.data.actions.remove(act)
for pb in rig.pose.bones:
    pb.matrix_basis.identity()
    pb.rotation_mode='QUATERNION'
rig.data.pose_position='POSE'
scene.render.fps=FPS
scene.frame_start,scene.frame_end=1,PERIOD+1

# The lowest sole vertices have only Foot/ToeBase influence. Both bones receive
# the same rigid foot transform. These measured rest points set the true floor.
sole = {}
for side,sgn in (('Left',1),('Right',-1)):
    sole[side] = [v.co.copy() for v in meshes[2].data.vertices if v.co.z < .026 and v.co.x*sgn > 0]

def foot_target(phase,side):
    q=phase%1.0
    span=SPEED*DURATION*STANCE
    clearance=0.
    pitch=0.
    if q <= STANCE:
        y=-span/2+SPEED*DURATION*q
    else:
        u=(q-STANCE)/(1-STANCE)
        # Cubic Hermite closes position and velocity onto the planted track.
        tangent=SPEED*DURATION*(1-STANCE)
        h00=2*u**3-3*u*u+1; h10=u**3-2*u*u+u
        h01=-2*u**3+3*u*u; h11=u**3-u*u
        y=h00*span/2+h10*tangent-h01*span/2+h11*tangent
        clearance=.060*math.sin(math.pi*u)**2
        pitch=-6*math.sin(math.pi*u)**2
    rotation=A.R((1,0,0),pitch)
    ankle_rest=rest[P+side+'Foot'].translation
    low=min((rotation @ (v-ankle_rest)).z for v in sole[side])
    ankle=Vector((ankle_rest.x,y,-low+clearance))
    return ankle, rotation, q <= STANCE, clearance

def bone_matrix(name,head,tail):
    b=rig.data.bones[name]
    turn=(b.tail_local-b.head_local).rotation_difference(tail-head)
    m=(turn @ rest[name].to_quaternion()).to_matrix().to_4x4()
    m.translation=head
    return m

reach_margin=[]
def pose(phase):
    phi=2*math.pi*phase
    J=A.idle_joints()
    J['Hips']=A.R((0,0,1),-3*math.cos(phi)) @ A.R((0,1,0),-1.1*math.sin(phi))
    J['Spine']=A.R((1,0,0),3) @ A.R((0,0,1),4.5*math.cos(phi))
    J['Spine1']=A.R((1,0,0),-.6*math.cos(2*phi))
    J['Spine2']=A.R((0,1,0),.7*math.sin(phi))
    J['Neck']=A.R((1,0,0),-2.5) @ A.R((0,0,1),-1.5*math.cos(phi))
    J['Head']=A.R((0,1,0),-.4*math.sin(phi))
    for side,sgn in (('Left',1),('Right',-1)):
        J[side+'Arm']=A.R((1,0,0),sgn*18*math.cos(phi)-3) @ A.R((0,1,0),sgn*76)
        J[side+'ForeArm']=A.R((1,0,0),-13-sgn*3*math.sin(phi))
    desired=A.pose_from_joints(rig,rest,J,root_offset=Vector((0,0,-.052-.025*math.cos(2*phi))))
    for side,sgn,offset in (('Left',1,0),('Right',-1,.5)):
        upper,lower,foot=(P+side+n for n in ('UpLeg','Leg','Foot'))
        hip=desired[upper].translation.copy()
        ankle,rotation,_,_=foot_target(phase+offset,side)
        l1=(rest[lower].translation-rest[upper].translation).length
        l2=(rest[foot].translation-rest[lower].translation).length
        direction=ankle-hip; d=direction.length; direction.normalize()
        reach_margin.append(l1+l2-d)
        assert d < l1+l2, (phase,side,d,l1+l2)
        along=(l1*l1-l2*l2+d*d)/(2*d)
        bend=math.sqrt(max(0,l1*l1-along*along))
        pole=Vector((.06*sgn,-1,0))
        pole=(pole-direction*pole.dot(direction)).normalized()
        knee=hip+direction*along+pole*bend
        desired[upper]=bone_matrix(upper,hip,knee)
        desired[lower]=bone_matrix(lower,knee,ankle)
        transform=Matrix.Translation(ankle) @ rotation.to_matrix().to_4x4() @ Matrix.Translation(-rest[foot].translation)
        for n in A.subtree(rig,side+'Foot'): desired[n]=transform @ rest[n]
    return desired

# Dense half-frame keys keep the IK support point accurate between 30fps samples.
frames={1+i/2:pose(i/(2*PERIOD)) for i in range(2*PERIOD)}
frames[PERIOD+1]={n:m.copy() for n,m in frames[1].items()}
action=RG.key_frames(rig,rest,frames,'Walk')
action['nominal_ground_speed_m_s']=SPEED
action['loop_duration_s']=DURATION
action['stance_fraction']=STANCE
action['authoring']='Original analytical 2-bone IK walk; fitted Buddy v04 skeleton; no source motion reused'
rig.animation_data.action=action
scene.frame_set(1)

if FINAL:
    # The saved file retains original A meshes for editing and visual review.
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/(STEM+'.blend')))
    # Unskinned FBX nodes inherit the current pose as their default transform.
    # Reset pose before exporting; all-actions baking still samples only Walk.
    rig.animation_data.action=None
    for pb in rig.pose.bones: pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(HERE/(STEM+'.fbx')),use_selection=True,
        object_types={'ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_actions=True,bake_anim_use_nla_strips=False,
        bake_anim_step=.5,bake_anim_simplify_factor=0,
        axis_forward='-Z',axis_up='Y',apply_unit_scale=True,use_mesh_modifiers=False)
    print('EXPORT_READY',HERE/(STEM+'.fbx'),'action Walk frame 1..21 duration',DURATION,flush=True)
    rig.animation_data.action=action
    scene.frame_set(1)

col,cam,floor=RD.studio(scene)
scene.render.engine='CYCLES'
scene.cycles.samples=16
scene.render.image_settings.file_format='PNG'
scene.render.resolution_percentage=100
preview=HERE/'Previews'/STEM
preview.mkdir(parents=True,exist_ok=True)
for label,loc,fr in [('01_contact_34',(-2.8,-4.5,1.65),1),('02_passing_side',(5,0,1.0),6),('03_contact_side',(5,0,1.0),1),('04_passing_front',(0,-5,1.0),6)]:
    RD.shot(scene,cam,preview/(label+'.png'),loc,(0,0,.87),ortho=1.95,res=(640,720),frame=fr)
print('PREVIEWS_READY',flush=True)
