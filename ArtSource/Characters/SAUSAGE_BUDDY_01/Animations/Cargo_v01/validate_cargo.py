"""Independent 120 Hz saved-source validation and animation-only FBX reimport."""
from pathlib import Path
import sys,json,hashlib,math,argparse
sys.dont_write_bytecode=True
import bpy,numpy as np
from mathutils import Quaternion
HERE=Path(__file__).resolve().parent;SRC=HERE.parent.parent;P='mixamorig:'
sys.path.insert(0,str(SRC))
import buddy_rig as RG
ap=argparse.ArgumentParser();ap.add_argument('--revision',type=int,default=1)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
VERSION=f'v{args.revision:02}'
CLIPS={'SitUp_Cargo':63,'Cargo_Sit_Idle':120,'Cargo_Knock':84}
output=HERE/f'validation_{VERSION}.json';assert not output.exists(),'Refusing report overwrite'
def mat(m):return [list(r) for r in m]
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True).encode()).hexdigest()
def pose(rig):return {b.name:mat(rig.matrix_world@b.matrix) for b in rig.pose.bones}
def error(a,b):return max(abs(a[n][r][c]-b[n][r][c]) for n in a for r in range(4) for c in range(4))
def bone_signature(rig):
    return {b.name:{'parent':b.parent.name if b.parent else None,'rest':mat(b.matrix_local),'deform':b.use_deform} for b in rig.data.bones}
def signature():
    rig=bpy.data.objects['Buddy_Rig_Mixamo65']
    out={'bones':bone_signature(rig),'rig_transform':mat(rig.matrix_world),'meshes':{}}
    for n in ('Body','Face','Outfit'):
        o=bpy.data.objects[n]
        data={'vertices':[list(v.co) for v in o.data.vertices],
              'polygons':[list(p.vertices) for p in o.data.polygons],
              'weights':[[(o.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in o.data.vertices],
              'uvs':{l.name:[list(v.uv) for v in l.uv] for l in o.data.uv_layers},
              'materials':[m.name for m in o.data.materials],
              'shape_keys':{k.name:[list(v.co) for v in k.data] for k in o.data.shape_keys.key_blocks} if o.data.shape_keys else None}
        out['meshes'][n]={'sha256':digest(data),'scale':list(o.scale),'transform':mat(o.matrix_world),
                         'triangles':sum(len(p.vertices)-2 for p in o.data.polygons)}
    return out
def import_rig(path):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
    bpy.ops.import_scene.fbx(filepath=str(path),ignore_leaf_bones=False,automatic_bone_orientation=False)
    return next(o for o in bpy.data.objects if o.type=='ARMATURE')
def geometry_bounds():
    points=[];dg=bpy.context.evaluated_depsgraph_get()
    for name in ('Body','Face','Outfit'):
        o=bpy.data.objects[name];ev=o.evaluated_get(dg);me=ev.to_mesh()
        a=np.empty(len(me.vertices)*3,dtype=np.float32);me.vertices.foreach_get('co',a)
        m=np.array(o.matrix_world);points.append(a.reshape(-1,3)@m[:3,:3].T+m[:3,3]);ev.to_mesh_clear()
    a=np.concatenate(points);return a.min(0),a.max(0)
baseline=json.loads((HERE/'source_inspection_v01.json').read_text(encoding='utf-8'))['source_sha256']
hashes={n:hashlib.sha256((SRC/n).read_bytes()).hexdigest() for n in baseline}
bpy.ops.wm.open_mainfile(filepath=str(SRC/'SAUSAGE_BUDDY_A_v04.blend'));original=signature()
bpy.ops.wm.open_mainfile(filepath=str(SRC/'SAUSAGE_BUDDY_B_v04.blend'));originalB=signature()
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'GetUp_Idle_v01'/'GetUp_FromBack_v02.blend'))
bpy.context.scene.frame_set(1);supine=pose(bpy.data.objects['Buddy_Rig_Mixamo65'])
walk=import_rig(HERE.parent/'Locomotion_v01'/'Walk_v02.fbx');walkbones=bone_signature(walk)
report={'fps':30,'sample_rate_hz':120,'source_files_sha256_unchanged':hashes==baseline,
        'a_b_rig_rest_equal':original['bones']==originalB['bones'],
        'source_review_triangles':sum(x['triangles'] for x in original['meshes'].values()),
        'export_triangle_budget':0,'export_meshes':0,
        'thresholds':{'height_m':1.2,'sitting_penetration_m':.000001,'quaternion_half_frame_step_deg':25,
            'fbx_matrix_component_error':.00015,'reference_matrix_error':.00001},
        'scope':'Saved Blender sources, original A mesh, rig compatibility with A/B, FBX reimport. No Unity import or gameplay test.',
        'clips':{}}
sourceposes={};endpoints={}
for name,period in CLIPS.items():
    stem=name+'_'+VERSION;bpy.ops.wm.open_mainfile(filepath=str(HERE/(stem+'.blend')))
    scene=bpy.context.scene;rig=bpy.data.objects['Buddy_Rig_Mixamo65'];action=rig.animation_data.action
    r={'action':action.name,'duration_s':period/30,'frames':[1,period+1],'fps':scene.render.fps,
       'loop':name!='SitUp_Cargo','bone_count':len(rig.data.bones),'rig_mesh_uv_material_weights_shape_keys_unchanged':signature()==original,
       'bone_list_order_matches_a_v04':list(rig.data.bones.keys())==list(original['bones']),
       'nan_or_infinite_components':0,'reflected_bone_samples':0,'negative_adjacent_quaternion_key_dots':0,
       'max_half_frame_quaternion_rotation_deg':0.0,'max_120hz_local_rotation_deg':0.0}
    curves=RG.fcurves_of(action)
    for n in rig.pose.bones.keys():
        fc=[next(x for x in curves if x.data_path==f'pose.bones["{n}"].rotation_quaternion' and x.array_index==c) for c in range(4)]
        for i in range(len(fc[0].keyframe_points)-1):
            a=Quaternion([x.keyframe_points[i].co.y for x in fc]).normalized()
            b=Quaternion([x.keyframe_points[i+1].co.y for x in fc]).normalized()
            dot=a.dot(b)
            if dot<0:r['negative_adjacent_quaternion_key_dots']+=1
            step=math.degrees(2*math.acos(min(1,abs(dot))))
            if step>r['max_half_frame_quaternion_rotation_deg']:
                r['max_half_frame_quaternion_rotation_deg']=step;r['max_key_step_at']=[n,float(fc[0].keyframe_points[i+1].co.x)]
    lows=[];heights=[];seatedlows=[];hipheights=[];walllows=[];positions=[];poses={};prev={};min_det=1
    for i in range(period*4+1):
        f=1+i/4;t=(f-1)/30;scene.frame_set(int(f),subframe=f%1)
        lo,hi=geometry_bounds();lows.append(float(lo[2]));heights.append(float(hi[2]))
        hips=rig.matrix_world@rig.pose.bones[P+'Hips'].head;hipheights.append(hips.z);positions.append(list(hips))
        if name!='SitUp_Cargo' or t>=.97:seatedlows.append(float(lo[2]));walllows.append(float(lo[0]))
        for b in rig.pose.bones:
            m=b.matrix;det=m.to_3x3().determinant();min_det=min(min_det,det)
            r['nan_or_infinite_components']+=sum(not math.isfinite(x) for row in m for x in row)
            r['reflected_bone_samples']+=int(det<=0)
            q=b.matrix_basis.to_quaternion().normalized()
            if b.name in prev:
                step=math.degrees(2*math.acos(min(1,abs(q.dot(prev[b.name])))))
                r['max_120hz_local_rotation_deg']=max(r['max_120hz_local_rotation_deg'],step)
            prev[b.name]=q
        if i%2==0:poses[f]=pose(rig)
    endpoints[name]=(poses[1],poses[period+1]);sourceposes[name]=poses
    r.update({'max_height_above_floor_m':max(heights),'max_hips_height_m':max(hipheights),
              'sitting_sample_interval_s':[.97 if name=='SitUp_Cargo' else 0,period/30],
              'sitting_min_mesh_z_m':min(seatedlows),'sitting_max_floor_penetration_m':max(0,-min(seatedlows)),
              'all_frames_min_mesh_z_m':min(lows),'all_frames_max_floor_penetration_m':max(0,-min(lows)),
              'sitting_min_wall_clearance_m':min(walllows)-(-.65),
              'minimum_bone_determinant':min_det,
              'seam_max_matrix_component_error':error(poses[1],poses[period+1]) if r['loop'] else None,
              'supine_start_matrix_component_error':error(poses[1],supine) if name=='SitUp_Cargo' else None,
              'hips_horizontal_net_displacement_m':math.hypot(positions[-1][0]-positions[0][0],positions[-1][1]-positions[0][1])})
    report['clips'][stem]=r
reference=endpoints['Cargo_Sit_Idle'][0]
for name,period in CLIPS.items():
    stem=name+'_'+VERSION;r=report['clips'][stem]
    r['common_sit_end_matrix_error']=error(endpoints[name][1],reference)
    r['common_sit_start_matrix_error']=error(endpoints[name][0],reference) if r['loop'] else None
    rig=import_rig(HERE/(stem+'.fbx'));bones=bone_signature(rig)
    err=0;imported_endpoints={}
    for f,expected in sourceposes[name].items():
        bpy.context.scene.frame_set(int(f),subframe=f%1);actual=pose(rig);err=max(err,error(actual,expected))
        if f in (1,period+1):imported_endpoints[f]=actual
    binderr=max(abs(walkbones[n]['rest'][a][b]-bones[n]['rest'][a][b]) for n in walkbones for a in range(4) for b in range(4))
    hierarchy=lambda x:{n:v['parent'] for n,v in x.items()}
    r['fbx_reimport']={'bone_count':len(bones),'bone_list_order_matches_walk_v02':list(bones)==list(walkbones),
        'hierarchy_matches_walk_v02':hierarchy(bones)==hierarchy(walkbones),'max_bind_matrix_error_vs_walk_v02':binderr,
        'max_animated_world_matrix_component_error':err,
        'loop_seam_matrix_component_error':error(imported_endpoints[1],imported_endpoints[period+1]) if r['loop'] else None,
        'actions':{a.name:list(a.frame_range) for a in bpy.data.actions},
        'only_armature_objects':all(o.type=='ARMATURE' for o in bpy.data.objects),
        'constraints':sum(len(b.constraints) for b in rig.pose.bones)}
    r['pass']=all([r['fps']==30,r['bone_count']==65,r['rig_mesh_uv_material_weights_shape_keys_unchanged'],
        r['nan_or_infinite_components']==0,r['reflected_bone_samples']==0,r['negative_adjacent_quaternion_key_dots']==0,
        r['max_half_frame_quaternion_rotation_deg']<25,r['max_height_above_floor_m']<=1.2,
        r['sitting_max_floor_penetration_m']<=.000001,r['all_frames_max_floor_penetration_m']<=.000001,
        r['common_sit_end_matrix_error']<.00001,not r['loop'] or r['common_sit_start_matrix_error']<.00001,
        not r['loop'] or r['seam_max_matrix_component_error']==0,
        r['loop'] or r['supine_start_matrix_component_error']<.00001,
        r['fbx_reimport']['bone_list_order_matches_walk_v02'],r['fbx_reimport']['hierarchy_matches_walk_v02'],
        len(r['fbx_reimport']['actions'])==1,r['fbx_reimport']['only_armature_objects'],binderr<.0001,err<.00015,
        not r['loop'] or r['fbx_reimport']['loop_seam_matrix_component_error']==0])
report['pass']=report['source_files_sha256_unchanged'] and report['a_b_rig_rest_equal'] and all(r['pass'] for r in report['clips'].values())
output.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
if not report['pass']:raise RuntimeError('Cargo validation failed; see numbered JSON')
