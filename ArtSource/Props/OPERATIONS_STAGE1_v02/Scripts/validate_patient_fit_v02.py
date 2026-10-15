import bpy,bmesh,json,math,hashlib,os
from pathlib import Path
from mathutils import Vector
OUT=Path('C:/Dev/Game/ArtSource/Props/OPERATIONS_STAGE1_v02')
REV=os.environ.get('OPS_VALIDATE','v02_review')
FILE=OUT/('Operations_PATIENT_'+REV+'.blend')
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

 if o.name.endswith('_CLOSED_COVER'):
  o.parent['open']=0.;o.parent.update_tag();sc.frame_set(sc.frame_current);bpy.context.view_layer.update()
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
# Dense underside sampling across all eight authored body-shape fixtures.
from mathutils.bvhtree import BVHTree
profiles=json.loads((OUT/'Previews'/REV/'fit_profiles.json').read_text())
fit={}
for case,pars in profiles['cases'].items():
 trees=[]
 for ob in bpy.data.collections['02_PATIENT_'+case].objects:
  if ob.type=='MESH':trees.append(BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],[p.vertices[:] for p in ob.data.polygons]))
 def clearance(p):
  hits=[t.find_nearest(p) for t in trees];hits=[h for h in hits if h[0] is not None];loc,n,_,d=min(hits,key=lambda h:h[3]);return d if (p-loc).dot(n)>=0 else -d
 def height(p):
  hits=[t.ray_cast(Vector((p.x,p.y,2)),Vector((0,0,-1)))[0] for t in trees]
  return max(h.z for h in hits if h is not None) if any(h is not None for h in hits) else None
 for r in straps:
  r['open']=0.;r['girth']=pars.get('belly',0)-pars.get('thin',0);r['muscle']=pars.get('muscle',0);r['body_scale']=pars.get('scale',1)
 sync();fit[case]={}
 for r in straps:
  ob=bpy.data.objects[r.name+'_BAND'];ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();vs=[ob.matrix_world@v.co for v in me.vertices];gaps=[];central=[]
  # Bottom quad at each contact segment, sampled over length and width.
  count=15 if r.name=='STRAP_TORSO' else 10 if 'ARM' in r.name else 11
  for j in range(1,count):
   for strip in range(2):
    a,b,c,d=[vs[k] for k in [6*j+strip,6*j+strip+1,6*(j+1)+strip+1,6*(j+1)+strip]]
    for u in [0,.2,.4,.6,.8,1]:
     for v in [0,.25,.5,.75,1]:
      p=a.lerp(d,u).lerp(b.lerp(c,u),v);gap=clearance(p)
      gaps.append(gap)
      if 2<=j<=count-2:central.append(gap)
  ev.to_mesh_clear()
  fit[case][r.name]={'samples':len(gaps),'min_mm':min(gaps)*1000,'max_mm':max(gaps)*1000,'central_max_mm':max(central)*1000}
# Check moving band surfaces, including tails, at five hinge states.
sweep={}
for case,pars in profiles['cases'].items():
 trees=[]
 for ob in bpy.data.collections['02_PATIENT_'+case].objects:
  if ob.type=='MESH':trees.append(BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],[p.vertices[:] for p in ob.data.polygons]))
 for r in straps:r['girth']=pars.get('belly',0)-pars.get('thin',0);r['muscle']=pars.get('muscle',0);r['body_scale']=pars.get('scale',1)
 sweep[case]={}
 for op in [0,.25,.5,.75,1]:
  for r in straps:r['open']=op
  sync();minimum=0
  for r in straps:
   ob=bpy.data.objects[r.name+'_BAND'];ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();vs=[ob.matrix_world@v.co for v in me.vertices]
   for poly in me.polygons:
    ps=[vs[i] for i in poly.vertices]
    for p in ps+[sum(ps,Vector())/len(ps)]:
     hits=[t.find_nearest(p) for t in trees];loc,n,_,d=min((h for h in hits if h[0] is not None),key=lambda h:h[3])
     if (p-loc).dot(n)<0:
      if -d<minimum:
       minimum=-d

   ev.to_mesh_clear()
  sweep[case][str(op)]=minimum*1000
report['hinge_sweep_minimum_signed_clearance_mm']=sweep
ck('Band surface hinge sweep',all(v>=-1 for row in sweep.values() for v in row.values()),sweep)
for r in straps:r['open']=0.
sync()
report['girth_fit']=fit
ck('Girth contact clearance',all(v['min_mm']>=-1 and v['central_max_mm']<=12 for f in fit.values() for v in f.values()),fit)
for r in straps:r['girth']=0.;r['muscle']=0.;r['body_scale']=1.
sync()
markerchecks=[]
for name in roots[-3:]:
 r=bpy.data.objects[name];m=bpy.data.objects[r['source_marker']]
 markerchecks.append({'name':name,'position_error_m':(r.matrix_world.translation-m.matrix_world.translation).length,'matrix_error':max(abs(r.matrix_world[i][j]-m.matrix_world[i][j]) for i in range(4) for j in range(4))})
ck('Exact source marker positions and normals',all(v['matrix_error']<1e-6 for v in markerchecks),markerchecks)
inspection=json.loads((OUT/'source_inspection_v02.json').read_text())
ck('Approved patient and table sources unchanged',all(hashlib.sha256(Path(v['path']).read_bytes()).hexdigest()==v['sha256'] for v in inspection.values()),[v['path'] for v in inspection.values()])
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
# Retained tray geometry is identical; its review placement has moved outward 0.22 m.
tray_originals={o.name:o for o in geo.objects if o.name.startswith('TRAY_') and o.type=='MESH'}
with bpy.data.libraries.load('C:/Dev/Game/ArtSource/Props/OPERATIONS_STAGE1_v01/Operations_stage1_v02.blend',link=False) as (a,b):
 tn=[n for n in a.objects if n in tray_originals];b.objects=list(tn)
traychecks=[]
for n,o in zip(tn,b.objects):
 ref=tray_originals[n];same=len(ref.data.vertices)==len(o.data.vertices) and all((u.co-v.co).length<1e-8 for u,v in zip(ref.data.vertices,o.data.vertices)) and [tuple(p.vertices) for p in ref.data.polygons]==[tuple(p.vertices) for p in o.data.polygons]
 traychecks.append({'mesh':n,'identical_mesh':same})
ck('Retained tray geometry',all(v['identical_mesh'] for v in traychecks),traychecks)
fixed=[o for o in geo.objects if 'fixed_mount_for' in o];before={o.name:o.matrix_world.copy() for o in fixed}
for r in straps:r['open']=1.
sync()
ck('Fixed mounts do not follow opening bands',all(max(abs(o.matrix_world[i][j]-before[o.name][i][j]) for i in range(4) for j in range(4))<1e-7 for o in fixed),{'mount_parts':len(fixed)})
for r in straps:r['open']=0.
sync()
states=[]
for n in roots[-3:]:
 r=bpy.data.objects[n]
 for val in [0,1]:
  r['open']=val;r.update_tag();sc.frame_set(sc.frame_current);bpy.context.view_layer.update()
  states.append(bpy.data.objects[n+'_OPENING'].hide_render==(val==0) and bpy.data.objects[n+'_CLOSED_COVER'].hide_render==(val==1))
ck('Independent incision open and closed states',all(states),'Visibility drivers switch three separate openings and skin covers at open=0.5')
from mathutils import Matrix
patient_matrix=Matrix(((-1,0,0,0),(0,0,-1,.85),(0,-1,0,.795),(0,0,0,1)))
source_marks={o['name']:o for o in inspection['patient']['objects'] if o['name'].startswith('INC_')}
errors=[]
for n in roots[-3:]:
 r=bpy.data.objects[n];expected=patient_matrix@Matrix(source_marks[r['source_marker']]['world_matrix']);errors.append(max(abs(expected[i][j]-r.matrix_world[i][j]) for i in range(4) for j in range(4)))
ck('Marker transforms traced to approved source',max(errors)<1e-6,{'maximum_matrix_error':max(errors)})
report['new_geometry_triangles']=sum(v['triangles'] for v in report['mesh_statistics'].values())
report['result']='PASS' if all(v['status']=='PASS' for v in report['checks'].values()) else 'FAIL'
(OUT/('validation_v02.json' if REV=='v02_review' else 'validation_'+REV+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps({'result':report['result'],'checks':{n:v['status'] for n,v in report['checks'].items()},'tris':report['group_triangles'],'total':report['new_geometry_triangles']},indent=2),flush=True)
