"""Fit the supplied Mixamo skeleton to the saved NPC and bake its animation.
Run in Blender background. Keeps every source bone name and parent, including tips.
New numbered deliverables only; use --output-dir for disposable development previews.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix, Quaternion

HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE))
parser=argparse.ArgumentParser()
parser.add_argument('--model',type=Path,default=HERE/'NPC_BASE_01_v03.blend')
parser.add_argument('--motion',type=Path,default=HERE/'Sources'/'Run Look Back.fbx')
parser.add_argument('--output-dir',type=Path,default=HERE)
parser.add_argument('--revision',type=int,default=4)
parser.add_argument('--stills',action='store_true')
parser.add_argument('--rebuild-upper',action='store_true',help='Rebuild elbows, shoulders, circular collar and deformation-ready hands for v05+.')
parser.add_argument('--rigid-sausage',action='store_true',help='Bind the whole sausage head, face and collar to Spine2; repair mouth and shoulder weights.')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
OUT=args.output_dir;stem=f'NPC_BASE_01_v{args.revision:02d}'
outputs=[OUT/(stem+'.blend'),OUT/(stem+'.fbx'),OUT/f'validation_v{args.revision:02d}.json']
if any(p.exists() for p in outputs):parser.error('Revision already exists. Choose a new number or an empty output directory.')
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(args.model))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene
scene.name=stem;scene['npc_asset_revision']=stem
collection=bpy.data.collections['NPC_BASE_01']
topology_update=None
if args.rebuild_upper:
    from rebuild_upper import rebuild
    topology_update=rebuild(collection)
meshes=[o for o in collection.objects if o.type=='MESH']
assert len(meshes)==6 and not any(o.type=='ARMATURE' for o in collection.objects)
existing=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(args.motion),ignore_leaf_bones=False,automatic_bone_orientation=False)
imported=set(bpy.data.objects)-existing
source=next(o for o in imported if o.type=='ARMATURE')
assert len(source.data.bones)==65
source_names=set(source.data.bones.keys())
parents={b.name:b.parent.name if b.parent else None for b in source.data.bones}
src_action=source.animation_data.action
start,end=map(lambda x:int(round(x)),src_action.frame_range)
fps=scene.render.fps;fps_base=scene.render.fps_base
prefix='mixamorig:'
src_rest={b.name:source.matrix_world@b.matrix_local for b in source.data.bones}
motion={}
for frame in range(start,end+1):
    scene.frame_set(frame)
    motion[frame]={p.name:source.matrix_world@p.matrix for p in source.pose.bones}

# Duplicate the actual source bone data, then fit it to the NPC's rest geometry.
data=source.data.copy();data.name=stem+'_Mixamo65'
rig=bpy.data.objects.new('NPC_Rig_Mixamo65',data);collection.objects.link(rig)
rig.show_in_front=True;data.display_type='STICK'
rig['source_animation']='Run Look Back / Mixamo'
rig['finger_mapping']='Thumb, Index, Middle, Ring; Pinky retained without skin weights'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
points={}
def bone(name,head,tail):points[prefix+name]=(Vector(head),Vector(tail))
bone('Hips',(0,0,.77),(0,0,.86))
bone('Spine',(0,0,.86),(0,0,.98))
bone('Spine1',(0,0,.98),(0,0,1.09))
bone('Spine2',(0,0,1.09),(0,0,1.21))
bone('Neck',(0,0,1.21),(0,0,1.244))
bone('Head',(0,0,1.244),(0,0,1.74))
bone('HeadTop_End',(0,0,1.74),(0,0,1.77))
for side,sign in [('Left',1),('Right',-1)]:
    def b(n,h,t):bone(side+n,(sign*h[0],h[1],h[2]),(sign*t[0],t[1],t[2]))
    b('Shoulder',(.06,0,1.18),(.19,0,1.18))
    b('Arm',(.19,0,1.18),(.41,0,1.175))
    b('ForeArm',(.41,0,1.175),(.64,0,1.168))
    b('Hand',(.64,0,1.168),(.745,0,1.168))
    thumb=[(.701,-.055,1.168),(.728,-.097,1.168),(.754,-.121,1.168),(.772,-.131,1.168),(.778,-.137,1.168)]
    for i in range(4):b('HandThumb'+str(i+1),thumb[i],thumb[i+1])
    for digit,y,xs in [('Index',-.047,[.744,.778,.803,.821,.829]),('Middle',0,[.744,.781,.807,.827,.835]),('Ring',.047,[.744,.775,.797,.815,.823]),('Pinky',.047,[.744,.775,.797,.815,.823])]:
        for i in range(4):b('Hand'+digit+str(i+1),(xs[i],y,1.168),(xs[i+1],y,1.168))
    b('UpLeg',(.089,0,.76),(.089,0,.413))
    b('Leg',(.089,0,.413),(.089,0,.13))
    b('Foot',(.089,0,.13),(.089,-.105,.052))
    b('ToeBase',(.089,-.105,.052),(.089,-.155,.035))
    b('Toe_End',(.089,-.155,.035),(.089,-.17,.03))
assert set(points)==source_names
for eb in data.edit_bones:
    eb.use_connect=False
    eb.head,eb.tail=points[eb.name]
    eb.align_roll(src_rest[eb.name].to_3x3().col[2].normalized())
    eb.use_deform=not (eb.name.endswith(('4','_End')) or 'Pinky' in eb.name)
bpy.ops.object.mode_set(mode='OBJECT')
assert parents=={b.name:b.parent.name if b.parent else None for b in data.bones}
rest={b.name:b.matrix_local.copy() for b in data.bones}

# Region-aware weights: the face stays rigid; garment and skin joints use the
# same functions. No heat weighting across separated eyes, clothes or fingers.
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def mix(a,b,t):
    out={k:v*(1-t) for k,v in a.items()}
    for k,v in b.items():out[k]=out.get(k,0)+t*v
    return out
def chain(value,anchors):
    if value<=anchors[0][0]:return {anchors[0][1]:1}
    for (lo,a),(hi,b) in zip(anchors,anchors[1:]):
        if value<=hi:return mix({a:1},{b:1},smooth(lo,hi,value))
    return {anchors[-1][1]:1}
def torso(p):
    return chain(p.z,[(.83,'Hips'),(.92,'Spine'),(1.04,'Spine1'),(1.17,'Spine2')])
def leg(p,side):
    if p.z>.69:return hip(p)
    # Keep the visible sock and the skin inside it on the same shin transform.
    # Ankle blending is inside the shoe; it must not buckle the sock cylinder.
    return chain(p.z,[(.375,side+'Leg'),(.451,side+'UpLeg')])
def hip(p):
    sided=mix({'RightUpLeg':1},{'LeftUpLeg':1},smooth(-.05,.05,p.x))
    return mix(sided,{'Hips':1},smooth(.69,.815,p.z))
def arm(p,side):
    x=abs(p.x)
    w=chain(x,[(.095,'Spine2'),(.300,side+'Arm'),(.345,side+'Arm'),(.475,side+'ForeArm'),(.618,side+'ForeArm'),(.677,side+'Hand')])
    if x<.68:return w
    # Four separate digit zones; preserve soft webbing at each palm junction.
    thumb_amount=smooth(.065,.091,-p.y)*smooth(.686,.725,x)
    digit=min([('Index',-.047),('Middle',0),('Ring',.047)],key=lambda d:abs(p.y-d[1]))[0]
    finger=chain(x,[(.746,side+'Hand'),(.763,side+'Hand'+digit+'1'),(.785,side+'Hand'+digit+'1'),(.795,side+'Hand'+digit+'2'),(.811,side+'Hand'+digit+'3')])
    along=(Vector((x,p.y,1.168))-Vector((.701,-.055,1.168))).dot(Vector((.071,-.076,0)).normalized())
    thumb=chain(along,[(.005,side+'Hand'),(.027,side+'HandThumb1'),(.045,side+'HandThumb1'),(.064,side+'HandThumb2'),(.087,side+'HandThumb3')])
    return mix(finger,thumb,thumb_amount)
def upper(p):
    # The sleeve joins shoulder weights gently; arms inside the sleeves match.
    side='Left' if p.x>=0 else 'Right'
    w=mix(torso(p),arm(p,side),smooth(.98,1.125,p.z)) if args.rebuild_upper else mix(torso(p),arm(p,side),smooth(.135,.205,abs(p.x))*smooth(1.08,1.15,p.z))
    collar=smooth(1.215,1.241,p.z)*(1-smooth(.128,.158,math.hypot(p.x,p.y)))
    return mix(w,{'Neck':1},collar) if args.rebuild_upper else mix(w,{'Head':1},collar)
def fitted_hand(p,side,index,obj):
    x=abs(p.x)
    # The wrist bends before the fleshy palm. Digit masks are authored with the
    # topology, not guessed by proximity to neighbouring fingers.
    if x<.667:return mix({side+'ForeArm':1},{side+'Hand':1},smooth(.595,.655,x))
    fields={digit:max(0,min(1,obj.data.attributes['npc_digit_'+digit].data[index].value))
            for digit in ['Thumb','Index','Middle','Ring']}
    total=sum(fields.values())
    if total>1:fields={k:v/total for k,v in fields.items()};total=1
    w={side+'Hand':1-total}
    for digit,amount in fields.items():
        if amount<1e-6:continue
        if digit=='Thumb':
            along=(Vector((x,p.y,1.168))-Vector((.701,-.055,1.168))).dot(Vector((.071,-.076,0)).normalized())
            dw=chain(along,[(.042,side+'HandThumb1'),(.066,side+'HandThumb2'),(.092,side+'HandThumb3')])
        else:
            # Broad phalanx blends avoid folding the inner surface of the thick,
            # short cartoon fingers into itself at a narrow joint boundary.
            dw=chain(x,[(.755,side+'Hand'+digit+'1'),(.810,side+'Hand'+digit+'2'),(.835,side+'Hand'+digit+'3')])
        for name,weight in dw.items():w[name]=w.get(name,0)+amount*weight
    return w
def components(mesh):
    adjacent=[[] for _ in mesh.vertices]
    for e in mesh.edges:
        a,b=e.vertices;adjacent[a].append(b);adjacent[b].append(a)
    remaining=set(range(len(adjacent)))
    while remaining:
        todo=[remaining.pop()];ids=[]
        while todo:
            i=todo.pop();ids.append(i)
            for j in adjacent[i]:
                if j in remaining:remaining.remove(j);todo.append(j)
        yield ids
body_regions={}
body=bpy.data.objects['Body_Base']
for ids in components(body.data):
    ps=[body.data.vertices[i].co for i in ids]
    region='head' if min(p.z for p in ps)>1.23 else 'leg' if max(p.z for p in ps)<.8 else 'arm' if max(abs(p.x) for p in ps)>.6 else 'torso'
    for i in ids:body_regions[i]=region
for obj in meshes:
    obj.vertex_groups.clear()
    groups={b.name[len(prefix):]:obj.vertex_groups.new(name=b.name) for b in data.bones if b.use_deform}
    for v in obj.data.vertices:
        p=obj.matrix_world@v.co;side='Left' if p.x>=0 else 'Right'
        if obj.name=='Face_Expressions':w={'Head':1}
        elif obj.name=='Body_Base':
            region=body_regions[v.index]
            if region=='head':
                w=mix({'Neck':1},{'Head':1},smooth(1.26,1.36,p.z)) if args.rebuild_upper else {'Head':1}
            elif args.rebuild_upper and region=='arm' and abs(p.x)>.59:
                w=fitted_hand(p,side,v.index,obj)
            else:w=leg(p,side) if region=='leg' else upper(p)
        elif obj.name=='Outfit_TShirt':
            if args.rebuild_upper:
                base=mix(torso(p),arm(p,side),smooth(.98,1.125,p.z))
                w=mix(base,{'Neck':1},obj.data.attributes['npc_collar'].data[v.index].value)
            else:w=upper(p)
        elif obj.name=='Outfit_Shorts':w=hip(p)
        elif obj.name=='Outfit_Socks':w=leg(p,side)
        else:
            w=mix({side+'Foot':1},{side+'ToeBase':1},smooth(.09,.145,-p.y))
            w=mix(w,leg(p,side),smooth(.10,.145,p.z))
        w=dict(sorted(((n,weight) for n,weight in w.items() if weight>1e-5),key=lambda x:-x[1])[:4])
        total=sum(w.values());assert total>0
        for n,weight in w.items():groups[n].add([v.index],weight/total,'REPLACE')
    obj.parent=rig;obj.matrix_parent_inverse=Matrix.Identity(4)
    mod=obj.modifiers.new('Mixamo65_Skin','ARMATURE');mod.object=rig
    mod.use_deform_preserve_volume=False

upper_repair=None
if args.rigid_sausage:
    from repair_sausage_upper import apply_repair
    upper_repair=apply_repair()

# World-space rest corrections account for altered proportions and bone axes.
# Translation is rebuilt along the target hierarchy so limb lengths never stretch.
root=prefix+'Hips'
stride_scale=(.76-.13)/((src_rest[prefix+'LeftUpLeg'].translation-src_rest[prefix+'LeftFoot'].translation).length)
first_root=motion[start][root].translation.copy()
previous={}
actions={}
for in_place in [False,True]:
    action=bpy.data.actions.new('RunLookBack_InPlace' if in_place else 'RunLookBack_RootMotion')
    rig.animation_data_create();rig.animation_data.action=action
    action.use_fake_user=True
    previous.clear()
    for frame in range(start,end+1):
        desired={}
        for pb in rig.pose.bones:
            name=pb.name
            rot=(motion[frame][name].to_quaternion()@src_rest[name].to_quaternion().inverted()@rest[name].to_quaternion()).normalized()
            if pb.parent:
                pos=desired[pb.parent.name]@rest[pb.parent.name].inverted()@rest[name].translation
            else:
                delta=(motion[frame][name].translation-src_rest[name].translation)*stride_scale
                delta.x-=(first_root.x-src_rest[name].translation.x)*stride_scale
                delta.y-=(first_root.y-src_rest[name].translation.y)*stride_scale
                if in_place:delta.x=delta.y=0
                pos=rest[name].translation+delta
            matrix=rot.to_matrix().to_4x4();matrix.translation=pos;desired[name]=matrix
            kw={} if not pb.parent else {'parent_matrix':desired[pb.parent.name],'parent_matrix_local':rest[pb.parent.name]}
            basis=pb.bone.convert_local_to_pose(matrix,rest[name],invert=True,**kw)
            pb.rotation_mode='QUATERNION';q=basis.to_quaternion()
            if args.rebuild_upper and any('Hand'+digit in name for digit in ['Index','Middle','Ring']):
                # This Mixamo take closes long human fingers into a tight fist.
                # Adapt local curl to the short, thick NPC fingers; preserve all
                # arm/wrist motion. Keep desired source matrices above unchanged
                # when deriving the remaining ORIGINAL local joint rotations.
                q=Quaternion().slerp(q,.55)
            if name in previous and previous[name].dot(q)<0:q.negate()
            previous[name]=q.copy();pb.rotation_quaternion=q;pb.location=basis.translation;pb.scale=(1,1,1)
            pb.keyframe_insert('rotation_quaternion',frame=frame,group=name)
            if not pb.parent:pb.keyframe_insert('location',frame=frame,group=name)
        bpy.context.view_layer.update()
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
    actions[action.name]=action
for obj in imported:bpy.data.objects.remove(obj,do_unlink=True)
# FBX importer marks its action with a fake user. Do not export the unfitted
# source take alongside the two retargeted takes.
bpy.data.actions.remove(src_action)
rig.animation_data.action=actions['RunLookBack_InPlace']
scene.frame_start=start;scene.frame_end=end
scene.render.fps=fps;scene.render.fps_base=fps_base
scene.frame_set(start)

# Ground the preview using the evaluated soles across the whole clip.
mins=[]
shoes=bpy.data.objects['Outfit_Shoes']
for frame in range(start,end+1):
    scene.frame_set(frame)
    evaluated=shoes.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mins.append(min((evaluated.matrix_world@v.co).z for v in evaluated.data.vertices))
ground_offset=-min(mins)+.008
for action in actions.values():
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    if fc.data_path==f'pose.bones["{root}"].location':
                        # Bone-local root translation, not world Z. Convert the offset.
                        amount=(rest[root].to_3x3().inverted()@Vector((0,0,ground_offset)))[fc.array_index]
                        for key in fc.keyframe_points:key.co.y+=amount
scene.frame_set(start)

stats={'revision':stem,'source_model':args.model.name,'source_motion':args.motion.name,
       'topology_update':topology_update,'upper_repair':upper_repair,
       'source_motion_sha256':hashlib.sha256(args.motion.read_bytes()).hexdigest(),
       'bones':len(data.bones),'bone_parents':parents,'fps':fps,'frames':[start,end],
       'actions':list(actions),'stride_scale':stride_scale,'ground_offset_m':ground_offset,
       'finger_mapping':rig['finger_mapping'],'meshes':{},'materials':sorted({m.name for o in meshes for m in o.data.materials})}
for obj in meshes:
    obj.data.calc_loop_triangles()
    stats['meshes'][obj.name]={'vertices':len(obj.data.vertices),'triangles':len(obj.data.loop_triangles)}
stats['total_triangles']=sum(m['triangles'] for m in stats['meshes'].values())
if args.rebuild_upper:
    stats['finger_pose_adaptation']={'main_digit_local_rotation_scale':.55,
        'thumb_and_wrist_motion':'unchanged','reason':'short thick cartoon fingers cannot accommodate the source human closed-fist curl'}
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
for obj in meshes:obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(outputs[1]),use_selection=True,object_types={'MESH','ARMATURE'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=True,
    bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,axis_forward='-Z',axis_up='Y',
    apply_unit_scale=True,use_mesh_modifiers=False)
rig.animation_data.action=actions['RunLookBack_InPlace'];scene.frame_set(start)
scene['preview_help']='Space: play RunLookBack_InPlace, 1-68 at 30 fps. RootMotion action also included. Rest pose: Armature data > Rest Position.'
camera=scene.camera
camera.location=(3,-6,2.7)
camera.rotation_euler=(Vector((0,0,.92))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.ortho_scale=2.15
scene.render.resolution_x=600;scene.render.resolution_y=680
scene.render.resolution_percentage=100
scene.cycles.samples=16
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=3
            area.spaces.active.region_3d.view_location=(0,0,.9)
            area.spaces.active.shading.type='MATERIAL'
            area.spaces.active.overlay.show_overlays=False
scene.frame_set(20)
bpy.ops.wm.save_as_mainfile(filepath=str(outputs[0]))
outputs[2].write_text(json.dumps(stats,indent=2),encoding='utf-8')
if args.stills:
    preview=OUT/'Previews'/f'v{args.revision:02d}';preview.mkdir(parents=True,exist_ok=True)
    for frame in [1,10,20,30,40,50,60,68]:
        scene.frame_set(frame);scene.render.filepath=str(preview/f'Run_{frame:03d}.png')
        bpy.ops.render.render(write_still=True)
print('RIG_BUILD_PASS '+json.dumps(stats),flush=True)
