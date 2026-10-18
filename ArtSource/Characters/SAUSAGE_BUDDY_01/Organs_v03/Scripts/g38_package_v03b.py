"""Write the requested new G38 review revision; never overwrite v03 or v03b."""
import copy,difflib,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Matrix
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import g38_build_v03b as B
import g38_measure as M
OUT=HERE.parent;REVIEW=B.REVIEW;WORK=B.WORK
revision=sys.argv[sys.argv.index('--revision')+1] if '--revision' in sys.argv else 'v03b'
four=revision=='v03c';suffix='four_final' if four else 'final';pair_count=4 if four else 5
construction=json.loads((WORK/('construction_four.json' if four else 'construction_final.json')).read_text())
validation=json.loads((WORK/f'validation_{suffix}.json').read_text())
fit=json.loads((WORK/f'fit_{suffix}.json').read_text())
dest=OUT/f'Organs_{revision}.blend';body_fbx=OUT/f'Organs_InBody_{revision}.fbx';rib_fbx=OUT/f'FBX/RIBCAGE_{revision}.fbx'
layout_src=OUT.parent/'Patient_v03/ORGANS_LAYOUT_v03.json';layout_dst=layout_src.with_name(f'ORGANS_LAYOUT_{revision}.json')
manifest_path=OUT/f'G38_collisions_manifest_{revision}.json'
for p in (dest,body_fbx,rib_fbx,layout_dst,manifest_path):assert not p.exists(),str(p)
bpy.context.view_layer.update()
bones=sorted([o for o in bpy.context.scene.objects if o.name.startswith(('RIB_','STERNUM_'))],key=lambda o:o.name)
cols=sorted([o for o in bpy.context.scene.objects if o.name.startswith('UCX_')],key=lambda o:o.name)
assert len(bones)==pair_count*2+2 and len(cols)==len(validation['colliders'])
assert all(M.mesh_health(o)['nonmanifold_edges']==0 and M.mesh_health(o)['components']==1 for o in bones)
assert sum(B.L.tris(o) for o in bones)<=6000
assert all(M.mesh_health(o)['convex'] and len(o.data.vertices)<=64 for o in cols)
if '--draft-collisions' not in sys.argv:
    assert fit['summary']['outside_2mm_pass'] and fit['summary']['coverage_1mm_pass']
for name,row in construction['unchanged'].items():
    now=B.snapshot(bpy.data.objects[name]);assert row['before']==now,name
    row['after']=now;row['exact']=True
construction['candidate_saved_to']=str(dest)
(WORK/f'preservation_{revision}.json').write_text(json.dumps(construction,indent=2))
manifest={'schema':f'G38_collision_manifest_{revision}/1','status':'BLOCKED_REVIEW_CANDIDATE',
 'blockers':['Fixed patient body/neck surface intersections remain in rest, TABLE_REST and open35.','The tested neck-clearing horizontal sternum trim removes 84 mm (70%); it is not applied because it changes the approved overall look.'],
 'rib_pairs':pair_count,'collider_fit_results':fit['summary'],'collision_results':validation['summary'],
 'units':'metres; 1 Blender unit = 1 metre; export global_scale=1',
 'source_blend':str(dest),'inbody_fbx':str(body_fbx),'ribcage_fbx':str(rib_fbx),
 'coordinate_frames':{'rest_blender':'Z up, patient anterior -Y, patient left +X',
  'collider_vertices':'Target object local Blender coordinates; child local matrix is identity.',
  'ribcage_fbx':'SOCKET_THORAX at identity as in v03. In-body export retains original hierarchy.',
  'fbx_axes':'axis_forward=-Z, axis_up=Y; apply_unit_scale; FBX_SCALE_UNITS',
  'table_rest_transform':validation['table_transform_used']},
 'unity_handoff':{'automatic_ucx_conversion':False,'layer':'SurgicalBone',
   'rib_tag':'SurgicalRib','sternum_tag':'SurgicalSternum','numeric_layer_index':'Assign an available project layer; no index assumed.',
   'import':'Create one convex MeshCollider per listed UCX mesh, keep its local identity under the named target, disable its MeshRenderer, preserve BREAK empties. Do not add decorative cartilage or spine colliders.',
   'mallet_osteotome_query':'Use only SurgicalBone in every tool sweep/raycast/contact query. Organs, vessels, diaphragm, lung, heart and body must be excluded from this tool mask. Physical contact filtering needs the same exclusion.',
   'mass':'Approximate closed render-mesh volume x 1100 kg/m3, a gameplay hint in kilograms.',
   'ready_for_runtime':False,'unity_test':'NOT RUN; user prohibited Unity/Assets changes.'},
 'objects':{}}
if not fit['summary']['outside_2mm_pass'] or not fit['summary']['coverage_1mm_pass']:
    manifest['blockers'].append('Four-part convex decomposition fails the tight surface-fit limits on the smooth reference curves. More parts requested; no permission assumed.')
if validation['summary']['min_organ_clearance_closed_mm']<3 or validation['summary']['min_organ_clearance_open_mm']<3:
    manifest['blockers'].append('Current draft UCX geometry fails the organ-clearance requirement; do not enable it for gameplay.')
if not validation['summary']['all_rib_gaps_at_least_8mm']:
    manifest['blockers'].append('At least one neighbouring collider gap is below 8 mm.')
for ob in bones:
    own=[o for o in cols if o.parent==ob];br=bpy.data.objects['BREAK_'+ob.name]
    entry={'hinge_parent':ob.parent.name,'mass_kg':ob['mass_kg'],
      'object_local_transform':B.matrix(ob.matrix_basis),'object_rest_world_transform':B.matrix(ob.matrix_world),
      'break_empty':{'name':br.name,'parent':ob.name,'position_target_local_m':list(br.location),'position_rest_world_m':list(br.matrix_world.translation)},
      'ucx_parts':[]}
    for part in own:
        v=[list(p.co) for p in part.data.vertices]
        entry['ucx_parts'].append({'name':part.name,'vertex_count':len(v),'triangle_count':B.L.tris(part),
          'convex':True,'bounds_target_local_m':[[min(p[i] for p in v) for i in range(3)],[max(p[i] for p in v) for i in range(3)]],
          'bounds_rest_world_m':B.world_bounds([part]),'local_matrix':B.matrix(part.matrix_basis),
          'fit':fit['outside'][part.name],'clearance':validation['colliders'][part.name]['poses']})
    manifest['objects'][ob.name]=entry
manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
old=json.loads(layout_src.read_text(encoding='utf-8'));new=copy.deepcopy(old)
new['ribcage']={n:r for n,r in new['ribcage'].items() if not n.startswith('RIB_') or int(n[-2:])<=pair_count}
for ob in bones:
    if not ob.name.startswith('RIB_'):continue
    row=new['ribcage'][ob.name];mn,mx=B.L.local_bounds(ob)
    row.update(tris=B.L.tris(ob),local_bounds_min=B.L.rnd(mn,4),local_bounds_max=B.L.rnd(mx,4),
               size_m_xyz=B.L.rnd(mx-mn,4),largest_dimension_m=round(max(mx-mn),4))
assert {k:v for k,v in old.items() if k!='ribcage'}=={k:v for k,v in new.items() if k!='ribcage'}
assert all(new['ribcage'][n]==r for n,r in old['ribcage'].items() if not n.startswith('RIB_'))
layout_dst.write_text(json.dumps(new,indent=1),encoding='utf-8')
diff=''.join(difflib.unified_diff(json.dumps(old,indent=1).splitlines(True),json.dumps(new,indent=1).splitlines(True),fromfile='ORGANS_LAYOUT_v03.json',tofile=f'ORGANS_LAYOUT_{revision}.json'))
(REVIEW/f'G38_LAYOUT_DIFF_{revision}.patch').write_text(diff,encoding='utf-8')
bpy.context.scene['G38_status']='BLOCKED_REVIEW_CANDIDATE: see G38_REPORT.md before runtime integration'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(dest))
kw=dict(use_selection=True,object_types={'MESH','EMPTY'},axis_forward='-Z',axis_up='Y',global_scale=1,
 apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',use_mesh_modifiers=False,bake_anim=False,
 add_leaf_bones=False,use_custom_props=True,mesh_smooth_type='FACE')
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:o.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
root=bpy.data.objects['ORGANS_v03_ROOT'];allobs=[root]+list(root.children_recursive)
select(allobs);bpy.ops.export_scene.fbx(filepath=str(body_fbx),**kw)
expected={'inbody':{o.name:{'bounds':B.world_bounds([o]),'triangles':B.L.tris(o),'parent':o.parent.name if o.parent else None} for o in allobs if o.type=='MESH'}}
thorax=bpy.data.objects['SOCKET_THORAX'];saved=thorax.matrix_basis.copy();thorax.matrix_basis=Matrix.Identity(4)@root.matrix_world.inverted()
bpy.context.view_layer.update();rc=bpy.data.objects['RIBCAGE'];ribobs=[thorax,rc]+list(rc.children_recursive)
expected['ribcage']={o.name:{'bounds':B.world_bounds([o]),'triangles':B.L.tris(o),'parent':o.parent.name if o.parent else None} for o in ribobs if o.type=='MESH'}
select(ribobs);bpy.ops.export_scene.fbx(filepath=str(rib_fbx),**kw)
thorax.matrix_basis=saved;bpy.context.view_layer.update()
(WORK/f'fbx_expected_{revision}.json').write_text(json.dumps(expected,indent=2))
print('G38_PACKAGE_WRITTEN',str(dest),flush=True)
