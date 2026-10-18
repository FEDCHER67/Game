"""Export the collider-only v03d after measured Blender gates pass."""
import json,sys,hashlib
from pathlib import Path
import bpy
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
import g38_measure as M
O=B.OUT;W=B.WORK;R=B.REVIEW
V=json.loads((W/'validation_v03d_01.json').read_text());F=json.loads((W/'fit_v03d_final.json').read_text())
C=json.loads((W/'colliders_v03d_01.json').read_text());source=json.loads((W/'preservation_delivered_v03c.json').read_text())
assert Path(bpy.data.filepath).name=='colliders_v03d_01.blend'
dest=O/'Organs_v03d.blend';full=O/'Organs_InBody_v03d.fbx';rib=O/'FBX/RIBCAGE_v03d.fbx'
manifest_path=O/'G38_collisions_manifest_v03d.json';layout=O.parent/'Patient_v03/ORGANS_LAYOUT_v03d.json'
for path in (dest,full,rib,manifest_path,layout):assert not path.exists(),str(path)
assert F['summary']['outside_2mm_pass'] and F['summary']['coverage_1mm_pass']
assert all(V['summary'][key] for key in ('all_convex','all_at_most_64_vertices','all_closed_triangulated','all_rib_gaps_at_least_8mm','filtered_probes_pass'))
assert V['summary']['min_organ_clearance_closed_mm']>=3 and V['summary']['min_organ_clearance_open_mm']>=3
assert not any(row['poses'][pose]['anatomical_containment'] for row in V['colliders'].values() for pose in ('closed','open35'))
bpy.context.view_layer.update()
fixed={o.name:B.snapshot(o) for o in bpy.context.scene.objects if not o.name.startswith('UCX_')}
assert fixed=={n:r for n,r in source['objects'].items() if not n.startswith('UCX_')}
bones=sorted((o for o in bpy.context.scene.objects if o.name.startswith(('RIB_','STERNUM_'))),key=lambda o:o.name)
cols=sorted((o for o in bpy.context.scene.objects if o.name.startswith('UCX_')),key=lambda o:o.name)
assert len(cols)==96 and sum(B.L.tris(o) for o in bones)==5840
manifest={'schema':'G38_collision_manifest_v03d/1','revision':'v03d','status':'BLENDER_COLLIDER_VALIDATION_PASS',
 'visual_source_revision':'v03c','visual_acceptance':'Accepted by user; no render mesh changes permitted or made.',
 'blockers':[],'rib_pairs':4,'collider_count':len(cols),'parts_per_rib':10,
 'acceptance_policy':{'rib_parts':'6-10 short convex pieces; 10 used per rib. Supersedes earlier four-piece limit.',
  'outside_max_mm':2,'uncovered_surface_max_mm':1,'organ_clearance_min_mm':3,'poses':['closed','open35'],
  'body_neck_intersection':'Accepted by user; information only, excluded from pass criteria.',
  'sternum_neck_overlap':'Accepted as is; original sternum render geometry preserved.',
  'render_mesh_changes_allowed':False},
 'source_blend':str(dest),'accepted_visual_source_blend':str(O/'Organs_v03c.blend'),
 'inbody_fbx':str(full),'ribcage_fbx':str(rib),'units':'metres; 1 Blender unit = 1 metre; export global_scale=1',
 'collider_fit_results':F['summary'],'collision_results':V['summary'],
 'coordinate_frames':{'rest_blender':'Z up, patient anterior -Y, patient left +X',
  'collider_vertices':'Target local coordinates; local matrix identity under rib/sternum.',
  'ribcage_fbx':'SOCKET_THORAX at identity as in v03/v03c; in-body export retains original hierarchy.',
  'fbx_axes':'axis_forward=-Z, axis_up=Y; apply_unit_scale; FBX_SCALE_UNITS',
  'table_rest_transform':V['table_transform_used']},
 'unity_handoff':{'automatic_ucx_conversion':False,'layer':'SurgicalBone','rib_tag':'SurgicalRib','sternum_tag':'SurgicalSternum',
  'numeric_layer_index':'Assign an available project layer; no index assumed.',
  'import':'Create one convex MeshCollider per UCX mesh under its target with local identity. Disable UCX MeshRenderer. Preserve BREAK empties and mass_kg.',
  'mallet_osteotome_query':'All mallet/osteotome queries and physical contacts must include only SurgicalBone; exclude organ/vessel/diaphragm/lung/heart/body layers.',
  'ready_for_unity_integration':True,'ready_for_runtime':False,
  'runtime_status':'Unity import, PhysX cooking and gameplay verification remain NOT RUN; user prohibited Unity/Assets work.'},
 'validation_files':{'clearance':str(W/'validation_v03d_01.json'),'fit':str(W/'fit_v03d_final.json')},'objects':{}}
for ob in bones:
    own=[o for o in cols if o.parent==ob];br=bpy.data.objects['BREAK_'+ob.name]
    assert len(own)==(10 if ob.name.startswith('RIB_') else 8)
    entry={'hinge_parent':ob.parent.name,'mass_kg':ob['mass_kg'],
     'object_local_transform':B.matrix(ob.matrix_basis),'object_rest_world_transform':B.matrix(ob.matrix_world),
     'break_empty':{'name':br.name,'parent':ob.name,'position_target_local_m':list(br.location),'position_rest_world_m':list(br.matrix_world.translation)},'ucx_parts':[]}
    for part in own:
        v=[list(p.co) for p in part.data.vertices]
        assert B.matrix(part.matrix_basis)==B.matrix(Matrix.Identity(4)) and B.matrix(part.matrix_parent_inverse)==B.matrix(Matrix.Identity(4))
        entry['ucx_parts'].append({'name':part.name,'vertex_count':len(v),'triangle_count':B.L.tris(part),'convex':True,
         'bounds_target_local_m':[[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]],
         'bounds_rest_world_m':B.world_bounds([part]),'local_matrix':B.matrix(part.matrix_basis),
         'fit':F['outside'][part.name],'clearance':V['colliders'][part.name]['poses']})
    manifest['objects'][ob.name]=entry
manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
# The accepted layout is copied byte for byte; no new transform values.
layout.write_bytes((O.parent/'Patient_v03/ORGANS_LAYOUT_v03c.json').read_bytes())
bpy.context.scene['G38_status']='v03d: Blender collider validation PASS; body/neck overlap accepted; Unity NOT RUN'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
kw=dict(use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',global_scale=1,
 apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',use_mesh_modifiers=False,bake_anim=False,
 add_leaf_bones=False,use_custom_props=True,mesh_smooth_type='FACE')
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
root=bpy.data.objects['ORGANS_v03_ROOT'];obs=[root]+list(root.children_recursive)
select(obs);bpy.ops.export_scene.fbx(filepath=str(full),**kw)
def expected(obs):return {o.name:{'bounds':B.world_bounds([o]),'triangles':B.L.tris(o),'parent':o.parent.name if o.parent else None} for o in obs if o.type=='MESH'}
exp={'inbody':expected(obs)}
thorax=bpy.data.objects['SOCKET_THORAX'];saved=thorax.matrix_basis.copy();thorax.matrix_basis=Matrix.Identity(4)@root.matrix_world.inverted()
bpy.context.view_layer.update();rc=bpy.data.objects['RIBCAGE'];obs=[thorax,rc]+list(rc.children_recursive)
exp['ribcage']=expected(obs);select(obs);bpy.ops.export_scene.fbx(filepath=str(rib),**kw)
thorax.matrix_basis=saved;bpy.context.view_layer.update()
(W/'fbx_expected_v03d.json').write_text(json.dumps(exp,indent=2))
print('V03D_EXPORTED',len(cols),'colliders; render meshes preserved',flush=True)
