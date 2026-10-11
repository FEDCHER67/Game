from pathlib import Path
import bpy,json,hashlib,math,sys
HERE=Path(__file__).resolve().parent
SRC=HERE.parent.parent
P='mixamorig:'
REV='v02' if '--v02' in sys.argv else 'v01'
def matrix(m):return [[float(x) for x in row] for row in m]
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
def signature():
    rig=bpy.data.objects['Buddy_Rig_Mixamo65']
    bones={b.name:{'parent':b.parent.name if b.parent else None,'rest':matrix(b.matrix_local),'deform':b.use_deform} for b in rig.data.bones}
    meshes={}
    for name in ('Body','Face','Outfit'):
        o=bpy.data.objects.get(name)
        if not o:continue
        meshes[name]=digest({'vertices':[list(v.co) for v in o.data.vertices],
            'polygons':[list(p.vertices) for p in o.data.polygons],
            'weights':[[(o.vertex_groups[g.group].name,g.weight) for g in v.groups] for v in o.data.vertices]})
    return {'bones':bones,'meshes':meshes,'rig_transform':matrix(rig.matrix_world)}

bpy.ops.wm.open_mainfile(filepath=str(SRC/'SAUSAGE_BUDDY_A_v04.blend'))
original=signature()
bpy.ops.wm.open_mainfile(filepath=str(HERE/f'Walk_{REV}.blend'))
saved=signature()
scene=bpy.context.scene; rig=bpy.data.objects['Buddy_Rig_Mixamo65']; outfit=bpy.data.objects['Outfit']
indices={s:[v.index for v in outfit.data.vertices if v.co.z<.026 and v.co.x*sgn>0] for s,sgn in [('Left',1),('Right',-1)]}
samples=[]; sourceposes={}
for i in range(81):
    f=1+i/4;scene.frame_set(int(f),subframe=f%1)
    dg=bpy.context.evaluated_depsgraph_get();ev=outfit.evaluated_get(dg); me=ev.to_mesh()
    feet={}
    for side,offset in [('Left',0),('Right',.5)]:
        q=((f-1)/20+offset)%1
        feet[side]={'stance':q<=.55+1e-8,'phase':q,
          'sole_min_z':min((outfit.matrix_world@me.vertices[v].co).z for v in indices[side]),
          'ankle':list(rig.matrix_world@rig.pose.bones[P+side+'Foot'].head)}
    ev.to_mesh_clear()
    samples.append({'frame':f,'hips':list(rig.matrix_world@rig.pose.bones[P+'Hips'].head),'feet':feet})
    if i%4==0:sourceposes[f]={b.name:matrix(rig.matrix_world@b.matrix) for b in rig.pose.bones}
seam=max(abs(sourceposes[1][n][r][c]-sourceposes[21][n][r][c]) for n in sourceposes[1] for r in range(4) for c in range(4))
stance_ground=[abs(s['feet'][side]['sole_min_z']) for s in samples for side in ('Left','Right') if s['feet'][side]['stance']]
speed_errors=[]
for a,b in zip(samples,samples[1:]):
    for side in ('Left','Right'):
        fa,fb=a['feet'][side],b['feet'][side]
        if fa['stance'] and fb['stance'] and fb['phase']>fa['phase']:
            speed=(fb['ankle'][1]-fa['ankle'][1])/(.25/30)
            speed_errors.append(abs(speed-1.5))
baseline=json.loads((HERE/'source_inspection.json').read_text())
hashes={n:hashlib.sha256((SRC/n).read_bytes()).hexdigest() for n in baseline['source_sha256']}
report={'action':'Walk','fps':30,'frame_start':1,'duplicate_end_frame':21,'loop_seconds':20/30,
    'nominal_speed_m_s':1.5,'step_length_m':.5,'stride_m':1.,'stance_fraction_per_leg':.55,'double_support_fraction':.10,
    'source_files_sha256_unchanged':hashes==baseline['source_sha256'],
    'rig_mesh_topology_weights_rest_unchanged':original==saved,
    'a_b_rest_equal':baseline['A']['bones']==baseline['B']['bones'],
    'seam_max_matrix_component_error':seam,
    'stance_max_ground_error_m':max(stance_ground),
    'stance_max_speed_error_m_s':max(speed_errors),
    'lowest_sole_m':min(s['feet'][side]['sole_min_z'] for s in samples for side in ('Left','Right')),
    'highest_swing_sole_m':max(s['feet'][side]['sole_min_z'] for s in samples for side in ('Left','Right')),
    'hips_horizontal_range_m':[max(s['hips'][i] for s in samples)-min(s['hips'][i] for s in samples) for i in (0,1)],
    'hips_vertical_range_m':max(s['hips'][2] for s in samples)-min(s['hips'][2] for s in samples),
    'sample_rate_hz':120}

# Compare imported hierarchy and bind matrices to the actual full-character FBX.
def import_rig(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps=30
    bpy.ops.import_scene.fbx(filepath=str(path),ignore_leaf_bones=False,automatic_bone_orientation=False)
    return next(o for o in bpy.data.objects if o.type=='ARMATURE')
reference=import_rig(SRC/'SAUSAGE_BUDDY_A_v04.fbx')
refbones={b.name:(b.parent.name if b.parent else None,matrix(b.matrix_local)) for b in reference.data.bones}
imported=import_rig(HERE/f'Walk_{REV}.fbx')
newbones={b.name:(b.parent.name if b.parent else None,matrix(b.matrix_local)) for b in imported.data.bones}
act=imported.animation_data.action
report['fbx_reimport']={'armature':imported.name,'bones':len(imported.data.bones),'root_bones':[b.name for b in imported.data.bones if not b.parent],
    'actions':{a.name:list(a.frame_range) for a in bpy.data.actions},
    'only_armature_objects':all(o.type=='ARMATURE' for o in bpy.data.objects),
    'hierarchy_matches_original_fbx':{n:v[0] for n,v in refbones.items()}=={n:v[0] for n,v in newbones.items()},
    'max_bind_matrix_error_vs_original_fbx':max(abs(refbones[n][1][r][c]-newbones[n][1][r][c]) for n in refbones for r in range(4) for c in range(4))}
reimport_error=0
for frame,ref in sourceposes.items():
    bpy.context.scene.frame_set(int(frame))
    for b in imported.pose.bones:
        m=imported.matrix_world@b.matrix
        reimport_error=max(reimport_error,max(abs(m[r][c]-ref[b.name][r][c]) for r in range(4) for c in range(4)))
report['fbx_reimport']['max_world_pose_matrix_error']=reimport_error
(HERE/f'validation_{REV}.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
