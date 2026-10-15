import bpy, bmesh, math, json, os, sys
from mathutils import Vector, Matrix
from pathlib import Path
ROOT=Path('C:/Dev/Game')
OUT=ROOT/'ArtSource/Props/OPERATIONS_STAGE1_v01'
BUILD=os.environ.get('OPS_BUILD','wip01')
assert not (OUT/('Operations_stage1_'+BUILD+'.blend')).exists(), 'Refusing to overwrite an existing numbered scene.'
REND=OUT/'Previews'/BUILD
REND.mkdir(parents=True,exist_ok=True)
sources=json.loads((OUT/'source_inspection_v01.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
sc.unit_settings.system='METRIC'; sc.unit_settings.scale_length=1
def coll(n):
 c=bpy.data.collections.new(n); sc.collection.children.link(c); return c
REF=coll('01_REFERENCE_TABLE_UNCHANGED'); PAT=coll('02_PATIENT_FIT_REFERENCE'); GEO=coll('03_OPERATIONS_PROPS'); TOOLS=coll('04_EXISTING_TOOL_REFERENCES'); STAGE=coll('90_REVIEW_STUDIO'); HIDDEN=coll('99_PREPARED_CUTTERS')
HIDDEN.hide_render=True
def append(key,col,flt):
 path=sources[key]['path']
 with bpy.data.libraries.load(path,link=False) as (src,dst): dst.objects=[n for n in src.objects if flt(n)]
 objects=[o for o in dst.objects if o]
 for o in objects:
  col.objects.link(o)
  o.hide_render=False; o.hide_viewport=False; o.hide_set(False)
  o['source_file']=path
 # Appended images with local paths must be resolved before a new blend is saved.
 for o in objects:
  if o.type=='MESH':
   for m in o.data.materials:
    if m and m.use_nodes:
     for n in m.node_tree.nodes:
      if n.type=='TEX_IMAGE' and n.image and not n.image.packed_file:
       p=n.image.filepath
       if p.startswith('//'): n.image.filepath=str(Path(path).parent/p[2:].replace('\\','/'))
 return objects
table=append('table',REF,lambda n:n.startswith(('GEO_','RIG_')) and not n.startswith('GEO_Strap'))
patient=append('npc',PAT,lambda n:n in ['Body_Base','Face_Expressions','Outfit_Shorts','Outfit_Socks','Outfit_Shoes','Outfit_TShirt','NPC_Rig_Mixamo65'])
rig=next(o for o in patient if o.type=='ARMATURE')
rig.animation_data_clear()
for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
for side,sign in [('Left',1),('Right',-1)]:
 pb=rig.pose.bones['mixamorig:'+side+'Arm']; rest=pb.bone.matrix_local.to_3x3()
 pb.rotation_mode='QUATERNION'; pb.rotation_quaternion=(rest.inverted()@Matrix.Rotation(math.radians(82*sign),3,'Y')@rest).to_quaternion()
bpy.context.view_layer.update()
# The fit fixture uses the existing skin, face, clothes and proportions, in a static pose.
# Lift the shirt hem on the local copy to expose the abdomen; the source NPC is untouched.
shirt=bpy.data.objects['Outfit_TShirt']
for v in shirt.data.vertices:
 if v.co.z<1.105 and abs(v.co.x)<.21: v.co.z=1.06+(v.co.z-.75)*.127
if shirt.data.shape_keys:
 for kb in shirt.data.shape_keys.key_blocks:
  for v in kb.data:
   if v.co.z<1.105 and abs(v.co.x)<.21: v.co.z=1.06+(v.co.z-.75)*.127
rig.matrix_world=Matrix(((-1,0,0,0),(0,0,-1,.82),(0,-1,0,.825),(0,0,0,1)))
bpy.context.view_layer.update()
# Freeze only the review copy so local prepared openings remain editable and predictable.
for o in list(patient):
 if o.type!='MESH': continue
 ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get())
 mesh=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get())
 mw=o.matrix_world.copy(); o.modifiers.clear(); o.data=mesh; o.parent=None; o.matrix_world=mw
 o.data.transform(o.matrix_world); o.matrix_world=Matrix.Identity(4)
 for v in o.data.vertices:
  t=max(0,min(1,(-v.co.y-.30)/.25)); t=t*t*(3-2*t)
  v.co.z-=.075*(1-t)
 o.name='REF_PATIENT_'+o.name; o['reference_only']=True
rig.hide_render=True; rig.hide_set(True)
body=bpy.data.objects['REF_PATIENT_Body_Base']
# The source body is a collection of overlapping closed islands. Isolate the abdomen
# island before Boolean preparation, preserving the head/limbs exactly on the fixture.
bm=bmesh.new(); bm.from_mesh(body.data); bm.verts.ensure_lookup_table()
seed=min(bm.verts,key=lambda v:(v.co-Vector((0,-.10,.826))).length)
todo=[seed]; component={seed}
while todo:
 v=todo.pop()
 for e in v.link_edges:
  w=e.other_vert(v)
  if w not in component: component.add(w); todo.append(w)
idx={v.index for v in component}
bm2=bm.copy(); bm2.verts.ensure_lookup_table()
bmesh.ops.delete(bm2,geom=[v for v in bm2.verts if v.index not in idx],context='VERTS')
bmesh.ops.recalc_face_normals(bm2,faces=list(bm2.faces))
me=bpy.data.meshes.new('PatientPreparedAbdomen'); bm2.to_mesh(me); bm2.free()
abd=bpy.data.objects.new('REF_PATIENT_ABDOMEN_SURFACE',me); PAT.objects.link(abd); me.materials.append(bpy.data.materials['Skin_Warm']); abd['reference_only']=True
bmesh.ops.delete(bm,geom=list(component),context='VERTS'); bm.to_mesh(body.data); bm.free()
body=abd
def mat(n,c,rough=.85,metal=0):
 m=bpy.data.materials.new(n); m.use_nodes=True
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 p.inputs['Base Color'].default_value=(*c,1); p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal
 m.diffuse_color=(*c,1); return m
with bpy.data.libraries.load(sources['table']['path'],link=False) as (src,dst): dst.materials=['MAT_Straps_Charcoal']
strapmat=bpy.data.materials['MAT_Straps_Charcoal']; frame=bpy.data.materials['MAT_Frame_MatteGraphite']; blue=bpy.data.materials['MAT_Pad_MutedBlueGray']; skin=bpy.data.materials['Skin_Warm']
steel=mat('MAT_Astra_MatteSteel',(.56,.61,.65),.78,.32)
oat=bpy.data.materials['Shirt_Oat']
cavity=mat('MAT_Astra_AbstractRecess',(.115,.068,.058),.96)
def mesh_obj(n,vs,fs,col=GEO,material=None):
 me=bpy.data.meshes.new(n+'_Mesh'); me.from_pydata(vs,[],fs); me.update(); o=bpy.data.objects.new(n,me); col.objects.link(o)
 if material: me.materials.append(material)
 bm=bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
 return o
def empty(n,p,col=GEO):
 o=bpy.data.objects.new(n,None); col.objects.link(o); o.location=p; o.empty_display_size=.035; return o
def parent(o,p):
 mw=o.matrix_world.copy(); o.parent=p; o.matrix_world=mw
def move_to(o,col):
 for c in list(o.users_collection): c.objects.unlink(o)
 col.objects.link(o)
def cube(n,p,size,material,bevel=0,col=GEO):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p); o=bpy.context.object; o.name=n; move_to(o,col); o.scale=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 o.data.materials.append(material)
 if bevel:
  mod=o.modifiers.new('Soft manufactured edge','BEVEL'); mod.width=bevel; mod.segments=1
  o.modifiers.new('Corner normals','WEIGHTED_NORMAL')
 return o
def cylinder(n,p,rad,depth,material,col=GEO):
 bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=rad,depth=depth,location=p)
 o=bpy.context.object; o.name=n; move_to(o,col); o.data.materials.append(material); return o
def line(n,pts,rad,material,col=GEO):
 cu=bpy.data.curves.new(n+'_Curve','CURVE'); cu.dimensions='3D'; cu.resolution_u=1; cu.bevel_depth=rad; cu.bevel_resolution=0; cu.resolution_u=1
 sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
 for q,p in zip(sp.points,pts): q.co=(*p,1)
 o=bpy.data.objects.new(n,cu); col.objects.link(o); cu.materials.append(material); return o
def camera(n,p,target,ortho):
 d=bpy.data.cameras.new(n); d.type='ORTHO'; d.ortho_scale=ortho; o=bpy.data.objects.new(n,d); STAGE.objects.link(o); o.location=p; o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler(); return o
def light(n,p,power,size):
 d=bpy.data.lights.new(n,'AREA'); d.energy=power; d.shape='DISK'; d.size=size; o=bpy.data.objects.new(n,d); STAGE.objects.link(o); o.location=p; o.rotation_euler=(Vector((0,0,.7))-o.location).to_track_quat('-Z','Y').to_euler()
floor=mat('MAT_Review_Background',(.17,.21,.23),1)
cube('REVIEW_Floor',(0,0,-.035),(200,200,.05),floor,col=STAGE)
sc.world=bpy.data.worlds.new('Soft Studio'); sc.world.use_nodes=True
next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Color'].default_value=(.55,.65,.75,1)
next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND').inputs['Strength'].default_value=.45
light('Key',(-3,-4,7),650,5); light('Fill',(4,1,4),400,4); light('Edge',(-1,4,5),500,3)
try: sc.render.engine='CYCLES'
except TypeError: pass
sc.cycles.samples=32; sc.cycles.use_denoising=True
sc.render.resolution_x=1200; sc.render.resolution_y=1000; sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
sc.view_settings.view_transform='AgX'
cam=camera('CAMERA_FIT_CHECK',(-2.6,3.5,4.2),(0,-.03,.58),2.6); sc.camera=cam
sc.render.filepath=str(REND/'fit_check.png')
if '--fit-only' in sys.argv: bpy.ops.render.render(write_still=True)
samples={}
for x in [-.3,-.25,-.2,-.15,-.1,-.05,0,.05,.1,.15,.2,.25,.3]:
 for y in [-.38,-.3,-.23,-.17,-.1,-.03,.03,.12,.3,.45,.5]:
  hit,loc,n,idx=body.ray_cast(Vector((x,y,2)),Vector((0,0,-1)))
  if hit: samples[f'{x},{y}']=list(loc)
(REND/'fit_samples.json').write_text(json.dumps(samples,indent=2))
print('FIT_READY',str(REND/'fit_check.png'),flush=True)
if '--fit-only' in sys.argv:
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('Operations_fit_'+BUILD+'.blend')))
 sys.exit()

# Five individually addressable hinges. Closed is local Y=0, open is the stored angle.
straps=[]
def band(n,pts,width,thick,material):
 vs=[]
 for i,p in enumerate(pts):
  tangent=Vector(pts[min(i+1,len(pts)-1)])-Vector(pts[max(0,i-1)])
  norm=Vector((-tangent.z,0,tangent.x)).normalized()
  if norm.z<0: norm=-norm
  for sy,sn in [(-1,-1),(1,-1),(1,1),(-1,1)]: vs.append(Vector(p)+Vector((0,sy*width/2,0))+sn*thick/2*norm)
 fs=[(3,2,1,0)]
 for i in range(len(pts)-1):
  for j in range(4): fs.append((i*4+j,i*4+(j+1)%4,(i+1)*4+(j+1)%4,(i+1)*4+j))
 fs.append(tuple((len(pts)-1)*4+j for j in range(4)))
 return mesh_obj(n,vs,fs,material=material)
def buckle(n,p,width,root):
 # Open rectangular steel frame, dark latch tongue and a pale release tab.
 x,y,z=p; length=.048; bw=width+.014; rod=.009
 bv=[]
 for zz in [z-.006,z+.006]:
  for sx,sy in [(length/2+rod/2,bw/2+rod/2),(length/2-rod/2,bw/2-rod/2)]:
   bv.extend([(x-sx,y-sy,zz),(x+sx,y-sy,zz),(x+sx,y+sy,zz),(x-sx,y+sy,zz)])
 bf=[]
 for j in range(4):
  k=(j+1)%4
  bf.extend([(j,k,8+k,8+j),(4+j,12+j,12+k,4+k),(j,4+j,4+k,k),(8+j,8+k,12+k,12+j)])
 o=mesh_obj(n+'_BUCKLE_FRAME',bv,bf,material=steel); parent(o,root)
 o=cube(n+'_BUCKLE_TONGUE',(x,y,z+.004),(length*.62,.012,.010),frame,0); parent(o,root)
 o=cube(n+'_RELEASE_TAB',(x+length*.24,y,z+.015),(.022,width*.62,.01),oat,.003); parent(o,root)
def restraint(name,x0,x1,y,top,width):
 z=.696; sign=1 if x1>x0 else -1
 root=empty(name,(x0,y,z)); root['hinge_axis']='LOCAL_Y'; root['closed_angle_deg']=0.; root['open_angle_deg']=-115.*sign; root['open']=0.; root['role']='INDIVIDUAL_TABLE_RESTRAINT'
 for label,x in [('HINGE',x0),('LATCH',x1)]:
  o=cube(name+'_MOUNT_'+label,(x,y,.678),(.037,width+.025,.042),frame,.005)
  o['fixed_mount_for']=name
  o=cylinder(name+'_PIN_'+label,(x,y,.702),.012,width+.032,steel); o.rotation_euler.x=math.pi/2
  o['fixed_mount_for']=name
 # Low flat saddle supports each limb above the existing pad; no table deformation.
 if name!='STRAP_TORSO':
  cube(name+'_MOUNT_SADDLE',((x0+x1)/2,y,.701),(abs(x1-x0)+.02,width+.025,.022),blue,.005)
 pts=[(x0,y,z),(x0+sign*.012,y,z+.045),(x0+(x1-x0)*.24,y,top-.008),(x0+(x1-x0)*.45,y,top),(x0+(x1-x0)*.65,y,top-.002),(x1-sign*.026,y,z+.065),(x1,y,z+.012)]
 if name=='STRAP_TORSO':
  pts=[(x0,y,z)]
  for k in range(1,12):
   x=x0+(x1-x0)*k/12; heights=[]
   for dy in [-width/2,0,width/2]:
    for ob in PAT.objects:
     if ob.type!='MESH': continue
     hit,loc,_,_=ob.ray_cast(Vector((x,y+dy,1.4)),Vector((0,0,-1)))
     if hit: heights.append(loc.z)
   zz=max(heights)+.010 if heights else z+.055
   pts.append((x,y,zz))
  pts.append((x1,y,z+.012))
 o=band(name+'_BAND',pts,width,.008,strapmat); parent(o,root)
 # Buckle sits over the outer rising section, visible from the fixed overview.
 bp=Vector(pts[-2]); bp.z+=.01; buckle(name,bp,width,root)
 fc=root.driver_add('rotation_euler',1); dr=fc.driver; v=dr.variables.new(); v.name='open'; v.type='SINGLE_PROP'; v.targets[0].id=root; v.targets[0].data_path='["open"]'; dr.expression=f'open*{math.radians(root["open_angle_deg"])}'
 root.id_properties_ui('open').update(min=0,max=1,description='0 closed / 1 open. Independent hinge; local Y axis.')
 straps.append(root); return root
restraint('STRAP_L_ARM',-.326,-.166,-.018,.814,.052)
restraint('STRAP_R_ARM', .326, .166,-.018,.814,.052)
restraint('STRAP_L_LEG',-.190,-.010, .475,.799,.058)
restraint('STRAP_R_LEG', .190, .010, .475,.799,.058)
restraint('STRAP_TORSO',-.319, .319,-.315,.852,.075)

# The tray is a continuous shallow shell with a recessed floor, two grip ends and four bays.
tray=empty('TRAY_INSTRUMENT',(-.68,-.02,.775)); tray['pivot']='Bottom centre of tray'; tray['dimensions_m']=[.48,.38,.055]
outline=[(-.20,-.19),(.20,-.19),(.24,-.15),(.24,.13),(.21,.18),(.09,.19),(-.09,.19),(-.21,.18),(-.24,.13),(-.24,-.15)]
vs=[]
for scale,z in [(1,0),(1,.045),(.93,.052),(.875,.036),(.875,.018)]:
 for x,y in outline: vs.append((x*scale,y*scale,z))
N=len(outline); fs=[]
for k in range(4):
 for i in range(N): fs.append((k*N+i,k*N+(i+1)%N,(k+1)*N+(i+1)%N,(k+1)*N+i))
fs.extend([tuple(reversed(range(N))),tuple(4*N+i for i in range(N))])
o=mesh_obj('TRAY_INSTRUMENT_SHELL',vs,fs,material=steel); o.parent=tray; o.location=(0,0,0); o.data.materials.append(blue)
for p in o.data.polygons:
 if p.index>=30: p.material_index=1
def traycube(n,p,sz,material,bevel=.003):
 o=cube(n,Vector(tray.location)+Vector(p),sz,material,bevel); parent(o,tray); return o
for i,x in enumerate([-.075,.004,.077]): traycube('TRAY_DIVIDER_'+str(i),(x,-.005,.029),(.009,.30,.018),steel)
for i,x in enumerate([-.135,-.035,.04]):
 for j,y in enumerate([-.10,.09]): traycube('TRAY_TOOL_REST_'+str(i)+'_'+str(j),(x,y,.025),(.047,.011,.009),strapmat)
for label,y in [('HEAD',.176),('FOOT',-.177)]: traycube('TRAY_GRIP_'+label,(0,y,.048),(.13,.024,.014),strapmat)
# One large clear organ bay at patient-side edge; three smaller instrument lanes.
for i,(x,y) in enumerate([(-.137,-.14),(-.036,-.14),(.038,-.14),(.146,-.14)]):
 traycube('TRAY_BAY_MARK_'+str(i+1),(x,y,.020),(.022,.018,.002),oat,0)
tray['slots']='SYRINGE | SCALPEL | KNIFE | ORGAN'
for label,x in [('SYRINGE',-.139),('SCALPEL',-.035),('KNIFE',.038),('ORGAN',.151)]:
 slot=empty('TRAY_SLOT_'+label,(x,0,.025)); slot.parent=tray; slot['role']='PLACEMENT_MARKER'

# Existing instruments are displayed at original metre scale, not remodeled substitutes.
def tool_reference(key,name,rot,target,flt):
 obs=append(key,TOOLS,flt)
 for o in obs: o.animation_data_clear()
 bpy.context.view_layer.update()
 meshes=[o for o in obs if o.type=='MESH']
 worlds={o:o.matrix_world.copy() for o in meshes}
 for o in meshes: o.parent=None; o.matrix_world=worlds[o]; o.data=o.data.copy(); o.data.transform(o.matrix_world); o.matrix_world=Matrix.Identity(4); o.data.transform(rot)
 coords=[v.co for o in meshes for v in o.data.vertices]
 lo=Vector([min(v[i] for v in coords) for i in range(3)]); hi=Vector([max(v[i] for v in coords) for i in range(3)])
 off=Vector(target)-Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
 for i,o in enumerate(meshes): o.location=off; o.name=name+'_'+str(i).zfill(2); o['reference_only']=True
 for o in obs:
  if o.type!='MESH': o.hide_render=True; o.hide_set(True)
 return meshes
tx,ty,tz=tray.location
tool_reference('syringe','REF_SYRINGE',Matrix.Rotation(math.pi/2,4,'X'),(tx-.139,ty,.809),lambda n:n.startswith(('SM_','CTRL_','SYRINGE_')))
tool_reference('scalpel','REF_SCALPEL',Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Rotation(math.pi/2,4,'X'),(tx-.035,ty,.806),lambda n:n.startswith('Scalpel_'))
tool_reference('knife','REF_KNIFE',Matrix.Rotation(math.pi/2,4,'Z')@Matrix.Rotation(math.pi/2,4,'X'),(tx+.038,ty,.806),lambda n:n=='Knife0_Mesh')
tool_reference('kidney','REF_TRAY_ORGAN',Matrix.Rotation(math.pi/2,4,'X'),(tx+.151,ty,.799),lambda n:n.startswith('L_Kidney'))
# A quiet studio plinth supports the tray in the review; it is not a deliverable cart.
cube('REVIEW_TraySupport_Top',(tx,ty,.757),(.40,.31,.03),frame,.01,col=STAGE)
cube('REVIEW_TraySupport_Post',(tx,ty,.39),(.045,.045,.71),frame,.007,col=STAGE)
cube('REVIEW_TraySupport_Base',(tx,ty,.045),(.35,.29,.05),frame,.008,col=STAGE)

# Authored access pieces: skin-matching bevel, recessed inner wall and a solid shadow floor.
# Each uses a live cutter on this posed reference body, avoiding a painted-on decal.
incisions=[]
def surface(x,y):
 hit,loc,_,_=body.ray_cast(Vector((x,y,1.02)),Vector((0,0,-1)))
 return loc.z if hit else .815
def incision(name,cx,cy,rx,ry):
 root=empty(name,(cx,cy,surface(cx,cy))); root['zone']='ABDOMEN'; root['state']='PREPARED_OPEN'; root['patient_side']='LEFT' if name.endswith('_L') else 'RIGHT' if name.endswith('_R') else 'LIVER'; root['geometry']='Authored rim, recess, floor, removable closed cover; live cut in reference patient'
 n=16; pts=[(cx+rx*math.cos(t*2*math.pi/n),cy+ry*math.sin(t*2*math.pi/n)) for t in range(n)]
 vs=[]
 for fac,zoff in [(1.19,-.001),(1.08,.006),(1,.002),(.82,-.025),(1.19,-.035)]:
  for x,y in pts:
   xx=cx+(x-cx)*fac; yy=cy+(y-cy)*fac; vs.append((xx,yy,surface(xx,yy)+zoff))
 fs=[]
 for k in range(3):
  for i in range(n): fs.append((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i))
 fs.append(tuple(3*n+i for i in range(n)))
 for i in range(n): fs.append((i,4*n+i,4*n+(i+1)%n,(i+1)%n))
 fs.append(tuple(reversed([4*n+i for i in range(n)])))
 rim=mesh_obj(name+'_OPENING',vs,fs,material=skin); rim.data.materials.append(cavity)
 for p in rim.data.polygons:
  if p.index>=2*n: p.material_index=1
 parent(rim,root)
 cutter_vs=[(x,y,z) for z in [.74,1.03] for x,y in pts]
 cutter_fs=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
 cut=mesh_obj(name+'_CUTTER',cutter_vs,cutter_fs,col=HIDDEN); cut.hide_render=True; cut.hide_set(True); cut.display_type='WIRE'; parent(cut,root)
 mod=body.modifiers.new(name+'_PREPARED_CUT','BOOLEAN'); mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cut
 # Separate neutral skin cover for closed state. Hidden in open-state review renders.
 capvs=[(cx,cy,surface(cx,cy)+.001)]+[(x,y,surface(x,y)+.001) for x,y in pts]
 capfs=[(0,1+i,1+(i+1)%n) for i in range(n)]
 cap=mesh_obj(name+'_CLOSED_COVER',capvs,capfs,material=skin); parent(cap,root); cap.hide_render=True; cap.hide_set(True); cap['state']='CLOSED_ONLY'
 sol=cap.modifiers.new('Cover thickness','SOLIDIFY'); sol.thickness=.003
 incisions.append(root)
 return root
incision('INCISION_KIDNEY_L',-.055,-.075,.031,.040)
incision('INCISION_KIDNEY_R', .055,-.075,.031,.040)
incision('INCISION_LIVER',0,-.176,.064,.032)

# Make the neutral closed covers and open pieces accessible from the Outliner.
sc['review_status']='PREVIEW ONLY — awaiting Fedya OK. No Unity import.'
sc['coordinate_contract']='Metres; table +Z up, head -Y. Patient left is -X. Strap pivots local Y. Tray pivot bottom.'
sc['reference_table']='TABLE-ASTRA-001, geometry/transforms unchanged; legacy two straps omitted from assembled review.'
sc.frame_start=1; sc.frame_end=2
sc.timeline_markers.new('CLOSED_REFERENCE',frame=1); sc.timeline_markers.new('OPEN_REFERENCE',frame=2)
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:
  try: im.pack()
  except Exception as e: print('PACK_WARNING',im.name,str(e))
def set_open(v):
 for r in straps: r['open']=v
 sc.frame_set(sc.frame_current); bpy.context.view_layer.update()
def render(name,cam,patient_on=True,open_amount=0):
 set_open(open_amount); PAT.hide_render=not patient_on
 for r in incisions:
  for o in r.children:
   if o.type=='MESH' and o.name.endswith('_OPENING'): o.hide_render=not patient_on
 sc.camera=cam; sc.render.filepath=str(REND/(name+'.png')); bpy.ops.render.render(write_still=True)
hero=camera('CAMERA_01_PATIENT',(-2.9,3.6,4.7),(-.19,-.02,.58),2.75)
overview=camera('CAMERA_02_FIXED_TABLE',(-.9,1.2,4.4),(-.20,-.04,.74),2.6)
topcam=camera('CAMERA_03_RESTRAINTS',(0,0,4),(0,-.03,.68),2.5)
traycam=camera('CAMERA_04_TRAY',(tx-.5,ty-.7,1.9),(tx,ty,.805),.64)
bellycam=camera('CAMERA_05_ABDOMEN',(-.10,.22,1.7),(0,-.11,.80),.42)
sc.camera=hero; set_open(0)
for screen in bpy.data.screens:
 for ar in screen.areas:
  if ar.type=='VIEW_3D':
   ar.spaces.active.region_3d.view_perspective='CAMERA'; ar.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('Operations_stage1_'+BUILD+'.blend')))
render('01_patient_closed',hero)
render('02_table_open',topcam,False,1)
render('03_table_closed',topcam,False,0)
render('04_tray',traycam)
render('05_incisions',bellycam)
render('06_fixed_camera',overview)
from bpy_extras.object_utils import world_to_camera_view
labels={}
for camera_name,objects in [('05_incisions',incisions),('03_table_closed',straps),('02_table_open',straps)]:
 cc=bellycam if camera_name=='05_incisions' else topcam
 labels[camera_name]={o.name:list(world_to_camera_view(sc,cc,o.matrix_world.translation))[:2] for o in objects}
(REND/'label_positions.json').write_text(json.dumps(labels,indent=2))
print('STAGE_RENDERED',BUILD,flush=True)
