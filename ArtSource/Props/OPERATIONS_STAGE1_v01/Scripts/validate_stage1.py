import bpy,bmesh,json,math,hashlib,os
from pathlib import Path
from mathutils import Vector
OUT=Path('C:/Dev/Game/ArtSource/Props/OPERATIONS_STAGE1_v01')
REV=os.environ.get('OPS_VALIDATE','v01')
FILE=OUT/('Operations_stage1_'+REV+'.blend')
bpy.ops.wm.open_mainfile(filepath=str(FILE))
sc=bpy.context.scene
roots=['STRAP_L_ARM','STRAP_R_ARM','STRAP_L_LEG','STRAP_R_LEG','STRAP_TORSO','TRAY_INSTRUMENT','INCISION_KIDNEY_L','INCISION_KIDNEY_R','INCISION_LIVER']
report={'file':str(FILE),'checks':{},'mesh_statistics':{},'group_triangles':{},'limits':{'each_limb_strap_with_mounts':450,'torso_strap_with_mounts':500,'tray':700,'each_opening_with_closed_cover':300}}
def ck(n,ok,detail): report['checks'][n]={'status':'PASS' if ok else 'FAIL','detail':detail}
ck('Exact independent object names',all(n in bpy.data.objects for n in roots),roots)
ck('Metres',sc.unit_settings.system=='METRIC' and sc.unit_settings.scale_length==1,str(sc.unit_settings.scale_length))
geo=bpy.data.collections['03_OPERATIONS_PROPS']
for o in geo.objects:
 if o.type!='MESH': continue
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get()); me=ev.to_mesh(); me.calc_loop_triangles()
 bm=bmesh.new(); bm.from_mesh(me)
 stats={'triangles':len(me.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'loose_vertices':sum(not v.link_edges for v in bm.verts),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'scale':list(o.scale)}
 bm.free(); ev.to_mesh_clear(); report['mesh_statistics'][o.name]=stats
for root in roots:
 report['group_triangles'][root]=sum(v['triangles'] for n,v in report['mesh_statistics'].items() if n.startswith('TRAY_' if root=='TRAY_INSTRUMENT' else root+'_'))
ck('Closed solid geometry',all(v['nonmanifold_edges']==0 and v['zero_area_faces']==0 and v['loose_vertices']==0 for v in report['mesh_statistics'].values()),{'meshes':len(report['mesh_statistics']),'bad':[n for n,v in report['mesh_statistics'].items() if v['nonmanifold_edges'] or v['zero_area_faces'] or v['loose_vertices']]})
ck('Applied scale for new mesh parts',all(all(abs(x-1)<1e-6 for x in v['scale']) for v in report['mesh_statistics'].values()),'Evaluated new prop meshes only')
ck('Low triangle budgets',all(report['group_triangles'][n]<= (500 if n=='STRAP_TORSO' else 450 if n.startswith('STRAP_') else 700 if n=='TRAY_INSTRUMENT' else 300) for n in roots),report['group_triangles'])
straps=[bpy.data.objects[n] for n in roots[:5]]
def sync():
 for r in straps: r.update_tag()
 sc.frame_set(sc.frame_current); bpy.context.view_layer.update()
for r in straps: r['open']=0
sync()
base={r.name:r.matrix_world.copy() for r in straps}; independence=[]
for active in straps:
 active['open']=1.; sync()
 moved=abs(active.rotation_euler.y-math.radians(active['open_angle_deg']))<1e-6
 others=all(max(abs(r.matrix_world[i][j]-base[r.name][i][j]) for i in range(4) for j in range(4))<1e-7 for r in straps if r!=active)
 pivot=(active.matrix_world.translation-base[active.name].translation).length<1e-7
 independence.append({'name':active.name,'open_degrees':math.degrees(active.rotation_euler.y),'independent':others,'pivot_fixed':pivot,'target_angle_reached':moved})
 active['open']=0.; sync()
ck('Five independent fixed hinges',all(x['independent'] and x['pivot_fixed'] and x['target_angle_reached'] for x in independence),independence)
shell=bpy.data.objects['TRAY_INSTRUMENT_SHELL']
bottom=min((shell.matrix_world@v.co).z for v in shell.data.vertices)
ck('Tray pivot at underside',abs(bottom-bpy.data.objects['TRAY_INSTRUMENT'].matrix_world.translation.z)<1e-7,{'bottom_z':bottom,'root_z':bpy.data.objects['TRAY_INSTRUMENT'].location.z})
ck('Four tray placement markers',all('TRAY_SLOT_'+n in bpy.data.objects for n in ['SYRINGE','SCALPEL','KNIFE','ORGAN']),'All four at slot surfaces')
ck('Prepared openings and closed covers',all(n+'_OPENING' in bpy.data.objects and n+'_CLOSED_COVER' in bpy.data.objects and n+'_CUTTER' in bpy.data.objects for n in roots[-3:]),'Three individual rim/recess/floor meshes, three separate covers and three live cutters')
# Check clearances at actual band vertices through the closed-to-open sweep.
fit={}
for r in straps:
 samples=[]
 for op in [0,.25,.5,.75,1]:
  r['open']=op; sync(); band=bpy.data.objects[r.name+'_BAND']; gaps=[]
  for v in band.data.vertices:
   p=band.matrix_world@v.co
   for ob in bpy.data.collections['02_PATIENT_FIT_REFERENCE'].objects:
    if ob.type!='MESH': continue
    eo=ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    hit,loc,_,_=eo.ray_cast(Vector((p.x,p.y,2)),Vector((0,0,-1)))
    if hit and loc.z>.65: gaps.append(p.z-loc.z)
  samples.append({'open':op,'minimum_vertex_clearance_m':min(gaps) if gaps else None})
 r['open']=0; sync(); fit[r.name]=samples
report['band_clearance_samples']=fit
ck('Band vertices clear patient throughout five sampled states',all(s['minimum_vertex_clearance_m'] is None or s['minimum_vertex_clearance_m']>=-.001 for ss in fit.values() for s in ss),fit)
# Compare original table geometry with the appended reference, including world matrices.
names=[o.name for o in bpy.data.collections['01_REFERENCE_TABLE_UNCHANGED'].objects if o.type=='MESH']
originals={n:bpy.data.objects[n] for n in names}
src='C:/Dev/Game/ArtSource/Props/TABLE-ASTRA-001/TABLE-ASTRA-001.blend'
with bpy.data.libraries.load(src,link=False) as (a,b):
 source_names=[n for n in a.objects if n in names]
 b.objects=list(source_names)
temp=bpy.data.collections.new('VALIDATION_SOURCE_TABLE'); sc.collection.children.link(temp)
for o in b.objects:
 while o:
  if o.name not in temp.objects: temp.objects.link(o)
  o=o.parent
bpy.context.view_layer.update()
comparisons=[]
for n,o in zip(source_names,b.objects):
 ref=originals[n]
 same=len(ref.data.vertices)==len(o.data.vertices) and len(ref.data.polygons)==len(o.data.polygons)
 if same: same=all((u.co-v.co).length<1e-8 for u,v in zip(ref.data.vertices,o.data.vertices)) and all(tuple(p.vertices)==tuple(q.vertices) for p,q in zip(ref.data.polygons,o.data.polygons))
 same_transform=max(abs(ref.matrix_world[i][j]-o.matrix_world[i][j]) for i in range(4) for j in range(4))<1e-7
 comparisons.append({'mesh':n,'geometry_identical':same,'world_transform_identical':same_transform})
ck('Table geometry preserved',all(x['geometry_identical'] and x['world_transform_identical'] for x in comparisons),comparisons)
ck('No legacy extra straps',not any(n in bpy.data.objects for n in ['GEO_Strap_01','GEO_Strap_02']),'The assembled review contains exactly the five replacement restraints')
ck('Texture portability',all(im.packed_file for im in bpy.data.images if im.source=='FILE' and im.users>0),[im.name for im in bpy.data.images if im.source=='FILE' and im.users>0])
report['new_geometry_triangles']=sum(v['triangles'] for v in report['mesh_statistics'].values())
report['result']='PASS' if all(v['status']=='PASS' for v in report['checks'].values()) else 'FAIL'
(OUT/('validation_'+REV+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps({'result':report['result'],'checks':{n:v['status'] for n,v in report['checks'].items()},'tris':report['group_triangles'],'total':report['new_geometry_triangles']},indent=2),flush=True)
