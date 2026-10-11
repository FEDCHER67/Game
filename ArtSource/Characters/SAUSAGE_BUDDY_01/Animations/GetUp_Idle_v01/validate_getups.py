"""Validate saved sources at 120 Hz, then independently reimport every FBX."""
from pathlib import Path
import sys,json,hashlib,math,argparse
sys.dont_write_bytecode=True
import bpy
from mathutils import Vector
HERE=Path(__file__).resolve().parent;SRC=HERE.parent.parent;P='mixamorig:'
sys.path.insert(0,str(SRC))
import buddy_rig as RG
ap=argparse.ArgumentParser();ap.add_argument('--revision',type=int,default=1);ap.add_argument('--clip',default='all')
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
VERSION=f'v{args.revision:02}'
CLIPS={'GetUp_FromBack':78,'GetUp_FromBelly':75,'Idle_Variant_A':120,'Idle_Variant_B':120}
if args.clip!='all':CLIPS={n:p for n,p in CLIPS.items() if n==args.clip}
def mat(m):return [list(r) for r in m]
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def signature():
    rig=bpy.data.objects['Buddy_Rig_Mixamo65']
    return {'bones':{b.name:{'parent':b.parent.name if b.parent else None,'rest':mat(b.matrix_local),'deform':b.use_deform} for b in rig.data.bones},
        'rig_transform':mat(rig.matrix_world),
        'meshes':{n:digest({'vertices':[list(v.co) for v in bpy.data.objects[n].data.vertices],
            'polygons':[list(p.vertices) for p in bpy.data.objects[n].data.polygons],
            'weights':[[(bpy.data.objects[n].vertex_groups[g.group].name,g.weight) for g in v.groups] for v in bpy.data.objects[n].data.vertices]}) for n in ('Body','Face','Outfit')}}
def max_error(a,b):return max(abs(a[n][r][c]-b[n][r][c]) for n in a for r in range(4) for c in range(4))
def import_rig(path):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
    bpy.ops.import_scene.fbx(filepath=str(path),ignore_leaf_bones=False,automatic_bone_orientation=False)
    return next(o for o in bpy.data.objects if o.type=='ARMATURE')
def bone_signature(rig):return {b.name:(b.parent.name if b.parent else None,mat(b.matrix_local)) for b in rig.data.bones}

output=HERE/(f'validation_{VERSION}.json' if args.clip=='all' else f'validation_{args.clip}_{VERSION}.json');assert not output.exists(),'Refusing numbered report overwrite'
baseline=json.loads((HERE/'source_inspection_v01.json').read_text(encoding='utf-8'))
hashes={n:hashlib.sha256(((HERE.parent/'Locomotion_v01'/n) if n.startswith('Walk') else (SRC/n)).read_bytes()).hexdigest() for n in baseline['source_sha256']}
bpy.ops.wm.open_mainfile(filepath=str(SRC/'SAUSAGE_BUDDY_A_v04.blend'));original=signature()
rig=bpy.data.objects['Buddy_Rig_Mixamo65'];rig.animation_data.action=bpy.data.actions['Idle'];bpy.context.scene.frame_set(1)
idle={b.name:mat(rig.matrix_world@b.matrix) for b in rig.pose.bones}
bpy.ops.wm.open_mainfile(filepath=str(SRC/'SAUSAGE_BUDDY_B_v04.blend'));originalB=signature()
walk=import_rig(HERE.parent/'Locomotion_v01'/'Walk_v02.fbx');walkbones=bone_signature(walk)
report={'fps':30,'sample_rate_hz':120,'source_files_sha256_unchanged':hashes==baseline['source_sha256'],
    'a_b_rig_rest_equal':original['bones']==originalB['bones'],'clips':{},
    'validation_scope':'Blender source, deformed soles and FBX reimport; no Unity import/playtest in this source-only brief'}
sourceposes={}
for name,period in CLIPS.items():
    stem=name+'_'+VERSION;bpy.ops.wm.open_mainfile(filepath=str(HERE/(stem+'.blend')))
    scene=bpy.context.scene;rig=bpy.data.objects['Buddy_Rig_Mixamo65'];outfit=bpy.data.objects['Outfit']
    r={'action':rig.animation_data.action.name,'frames':[1,period+1],'duration_s':period/30,
       'loop':name.startswith('Idle'),'rig_mesh_topology_weights_rest_unchanged':signature()==original,
       'bone_count':len(rig.data.bones),'nan_or_infinite_components':0,'reflected_bone_samples':0,
       'max_quaternion_key_step_deg':0.,'negative_adjacent_quaternion_key_dots':0}
    curves=RG.fcurves_of(rig.animation_data.action)
    for n in rig.pose.bones.keys():
        channel=[next(fc for fc in curves if fc.data_path==f'pose.bones["{n}"].rotation_quaternion' and fc.array_index==c) for c in range(4)]
        for i in range(len(channel[0].keyframe_points)-1):
            a=[fc.keyframe_points[i].co.y for fc in channel];b=[fc.keyframe_points[i+1].co.y for fc in channel]
            dot=sum(x*y for x,y in zip(a,b))/(math.sqrt(sum(x*x for x in a))*math.sqrt(sum(x*x for x in b)))
            if dot<0:r['negative_adjacent_quaternion_key_dots']+=1
            angle=math.degrees(2*math.acos(min(1.,abs(dot))))
            r['max_quaternion_key_step_deg']=max(r['max_quaternion_key_step_deg'],angle)
    indices={s:[v.index for v in outfit.data.vertices if v.co.z<.19 and v.co.x*sgn>0 and any(
        outfit.vertex_groups[g.group].name in (P+s+'Foot',P+s+'ToeBase') and g.weight>.5 for g in v.groups)]
        for s,sgn in [('Left',1),('Right',-1)]}
    positions=[];ground_errors=[];standing_penetrations=[];all_penetrations=[];floor_penetrations=[]
    poses={};min_det=1.
    for i in range(period*4+1):
        f=1+i/4;t=(f-1)/30;scene.frame_set(int(f),subframe=f%1)
        positions.append(list(rig.matrix_world@rig.pose.bones[P+'Hips'].head))
        for b in rig.pose.bones:
            m=b.matrix;det=m.to_3x3().determinant();min_det=min(min_det,det)
            if det<=0:r['reflected_bone_samples']+=1
            r['nan_or_infinite_components']+=sum(not math.isfinite(x) for row in m for x in row)
        dg=bpy.context.evaluated_depsgraph_get();ev=outfit.evaluated_get(dg);me=ev.to_mesh()
        for s in indices:
            low=min((outfit.matrix_world@me.vertices[idx].co).z for idx in indices[s])
            all_penetrations.append(max(0,-low))
            standing=name.startswith('Idle') or t>=1.7
            if standing:
                standing_penetrations.append(max(0,-low))
                tapping=name=='Idle_Variant_B' and s=='Right' and any(a<t<a+.35 for a in (.48,.97,1.46))
                if not tapping:ground_errors.append(abs(low))
        ev.to_mesh_clear()
        if name.startswith('GetUp'):
            lows=[]
            for o in (bpy.data.objects[n] for n in ('Body','Face','Outfit')):
                ev=o.evaluated_get(dg);me=ev.to_mesh();lows.append(min((o.matrix_world@v.co).z for v in me.vertices));ev.to_mesh_clear()
            floor_penetrations.append(max(0,-min(lows)))
        if i%4==0:poses[f]={b.name:mat(rig.matrix_world@b.matrix) for b in rig.pose.bones}
    r.update({'idle_end_matrix_error':max_error(poses[period+1],idle),
       'idle_start_matrix_error':max_error(poses[1],idle) if name.startswith('Idle') else None,
       'seam_max_matrix_component_error':max_error(poses[1],poses[period+1]) if name.startswith('Idle') else None,
       'standing_max_sole_penetration_m':max(standing_penetrations),
       'standing_support_max_ground_error_m':max(ground_errors),
       'all_frames_max_sole_penetration_m':max(all_penetrations),
       'all_mesh_max_floor_penetration_m':max(floor_penetrations) if floor_penetrations else None,
       'minimum_bone_determinant':min_det,
       'hips_horizontal_range_m':[max(p[c] for p in positions)-min(p[c] for p in positions) for c in (0,1)],
       'hips_horizontal_net_displacement_m':math.hypot(positions[-1][0]-positions[0][0],positions[-1][1]-positions[0][1]),
       'first_hips_height_m':positions[0][2],
       'standing_sample_interval_s':[0 if name.startswith('Idle') else 1.7,period/30]})
    sourceposes[name]=poses;report['clips'][stem]=r
for name,period in CLIPS.items():
    stem=name+'_'+VERSION;r=report['clips'][stem];rig=import_rig(HERE/(stem+'.fbx'));bones=bone_signature(rig)
    err=0;imported_endpoints={}
    for f,pose in sourceposes[name].items():
        bpy.context.scene.frame_set(int(f));actual={b.name:mat(rig.matrix_world@b.matrix) for b in rig.pose.bones};err=max(err,max_error(actual,pose))
        if f in (1,period+1):imported_endpoints[f]=actual
    binderr=max(abs(walkbones[n][1][a][b]-bones[n][1][a][b]) for n in walkbones for a in range(4) for b in range(4))
    r['fbx_reimport']={'bone_count':len(bones),'bone_list_order_matches_walk_v02':list(bones)==list(walkbones),
        'hierarchy_matches_walk_v02':{n:v[0] for n,v in bones.items()}=={n:v[0] for n,v in walkbones.items()},
        'max_bind_matrix_error_vs_walk_v02':binderr,'max_animated_world_matrix_error':err,
        'loop_seam_max_matrix_component_error':max_error(imported_endpoints[1],imported_endpoints[period+1]) if r['loop'] else None,
        'actions':{a.name:list(a.frame_range) for a in bpy.data.actions},
        'only_armature_objects':all(o.type=='ARMATURE' for o in bpy.data.objects)}
    r['pass']=all([r['rig_mesh_topology_weights_rest_unchanged'],r['idle_end_matrix_error']<1e-5,
        r['nan_or_infinite_components']==0,r['reflected_bone_samples']==0,r['negative_adjacent_quaternion_key_dots']==0,
        r['max_quaternion_key_step_deg']<25,
        r['standing_max_sole_penetration_m']<.001,r['standing_support_max_ground_error_m']<.005,
        not r['loop'] or r['seam_max_matrix_component_error']==0,
        r['fbx_reimport']['bone_list_order_matches_walk_v02'],r['fbx_reimport']['hierarchy_matches_walk_v02'],
        len(r['fbx_reimport']['actions'])==1,r['fbx_reimport']['only_armature_objects'],binderr<.0001,err<.00015])
report['pass']=report['source_files_sha256_unchanged'] and report['a_b_rig_rest_equal'] and all(r['pass'] for r in report['clips'].values())
output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)
