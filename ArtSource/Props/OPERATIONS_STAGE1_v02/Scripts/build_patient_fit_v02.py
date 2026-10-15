import bpy,bmesh,math,json,sys,os,hashlib
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path('C:/Dev/Game'); OUT=ROOT/'ArtSource/Props/OPERATIONS_STAGE1_v02'; HERE=OUT/'Scripts'
REV=os.environ.get('OPS_PASS','v02_review'); REND=OUT/'Previews'/REV; REND.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v01/SAUSAGE_BUDDY_PATIENT_v01.blend'
KEEP=ROOT/'ArtSource/Props/OPERATIONS_STAGE1_v01/Operations_stage1_v02.blend'
sys.path.insert(0,str(SOURCE.parent.parent)); import buddy_wear
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene; sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=1
def coll(n):
 c=bpy.data.collections.new(n);sc.collection.children.link(c);return c
REF=coll('01_REFERENCE_TABLE_UNCHANGED');GEO=coll('03_OPERATIONS_PROPS');TOOLS=coll('04_EXISTING_TOOL_REFERENCES');STAGE=coll('90_REVIEW_STUDIO');HIDDEN=coll('99_PREPARED_CUTTERS');HIDDEN.hide_render=True
exec(compile((HERE/'geometry_v02.py').read_text(),str(HERE/'geometry_v02.py'),'exec'))
def append(path,col,predicate):
 with bpy.data.libraries.load(str(path),link=False) as (a,b): b.objects=[n for n in a.objects if predicate(n)]
 for o in b.objects: col.objects.link(o);o.hide_render=False;o.hide_viewport=False;o.hide_set(False)
 return b.objects
append(ROOT/'ArtSource/Props/TABLE-ASTRA-001/TABLE-ASTRA-001.blend',REF,lambda n:n.startswith(('GEO_','RIG_')) and not n.startswith('GEO_Strap'))
# Whitelist only approved reusable props; no patient objects are loaded from this asset bank.
append(KEEP,GEO,lambda n:n.startswith('TRAY_'))
append(KEEP,TOOLS,lambda n:n.startswith(('REF_SYRINGE','REF_SCALPEL','REF_KNIFE','REF_TRAY_ORGAN')))
append(KEEP,STAGE,lambda n:n.startswith(('REVIEW_','Key','Fill','Edge')))
# Assembly placement only: leave room for the outward arm-strap sweep.
bpy.data.objects['TRAY_INSTRUMENT'].location.x-=.22
for ob in TOOLS.objects:
 if ob.parent is None or ob.parent.name not in TOOLS.objects:ob.location.x-=.22
strapmat=bpy.data.materials['MAT_Straps_Charcoal'];steel=bpy.data.materials['MAT_Astra_MatteSteel'];oat=bpy.data.materials['Shirt_Oat'];frame=bpy.data.materials['MAT_Frame_MatteGraphite'];blue=bpy.data.materials['MAT_Pad_MutedBlueGray']
def mat(n,c):
 m=bpy.data.materials.new(n);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=.95;return m
cavity=mat('MAT_Patient_AbstractRecess',(.115,.068,.058))
CASES={'NORMAL':{},'THIN':{'thin':1},'FAT':{'belly':1},'MUSCLE':{'muscle':1.7},'SCALE105':{'scale':1.05},'THIN105':{'thin':1,'scale':1.05},'FAT105':{'belly':1,'scale':1.05},'MUSCLE105':{'muscle':1.7,'scale':1.05}}
CASES.update({'MID_THIN':{'thin':.5,'scale':1.025},'MID_FAT':{'belly':.5,'scale':1.025},'MID_MUSCLE':{'muscle':.85,'scale':1.025}})
fixtures={};source_marker_matrices={}
def pose_global(rig,bone,rot):
 pb=rig.pose.bones['mixamorig:'+bone];r=pb.bone.matrix_local.to_3x3();pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(r.inverted()@rot@r).to_quaternion()
def fixture(case,params):
 c=coll('02_PATIENT_'+case);obs=append(SOURCE,c,lambda n:n in ['Body','Face','Shorts','Buddy_Rig_Mixamo65','INC_KIDNEY_L','INC_KIDNEY_R','INC_LIVER'])
 r=next(o for o in obs if o.type=='ARMATURE');r.animation_data_clear()
 for p in r.pose.bones:p.matrix_basis=Matrix.Identity(4)
 for o in obs:
  o.animation_data_clear()
  if o.type=='MESH' and o.data.shape_keys:
   o.data.shape_keys.animation_data_clear()
   for k in o.data.shape_keys.key_blocks:k.value=0
 bpy.context.view_layer.update()
 if case=='NORMAL':
  for o in obs:
   if o.name.startswith('INC_'):source_marker_matrices[o.name]=[list(row) for row in o.matrix_world]
 meshes=[o for o in obs if o.type=='MESH']
 buddy_wear.reshape(meshes,**{k:v for k,v in params.items() if k!='scale'})
 for side,sign in [('Left',1),('Right',-1)]:
  pose_global(r,side+'Arm',Matrix.Rotation(math.radians(6),3,'X')@Matrix.Rotation(math.radians(65*sign),3,'Y'))
  pose_global(r,side+'UpLeg',Matrix.Rotation(math.radians(5),3,'X'))
 pose_global(r,'Neck',Matrix.Rotation(math.radians(15),3,'X'))
 s=params.get('scale',1);r.matrix_world=Matrix(((-s,0,0,0),(0,0,-s,.85),(0,-s,0,.795+(s-1)*.11),(0,0,0,1)))
 bpy.context.view_layer.update();marks={}
 for o in obs:
  if o.type=='EMPTY' and o.name.startswith('INC_'):
   mw=o.matrix_world.copy();o.parent=None;o.matrix_world=mw;key=o.name.split('.')[0];o.name=key if case=='NORMAL' else case+'_'+key;marks[key]=o
 for o in meshes:
  original=o.name.split('.')[0];ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get());mw=o.matrix_world.copy();o.modifiers.clear();o.data=me;o.parent=None;o.matrix_world=Matrix.Identity(4);me.transform(mw)
  o.name='REF_PATIENT_'+case+'_'+original;o['patient_source']=str(SOURCE);o['fit_case']=case
 r.name='REF_PATIENT_'+case+'_Rig';r.hide_render=True;r.hide_set(True)
 c.hide_render=case!='NORMAL';c.hide_viewport=case!='NORMAL'
 return {'collection':c,'meshes':meshes,'body':next(o for o in meshes if o.name.endswith('_Body')),'markers':marks,'parameters':params}
for case,params in CASES.items():fixtures[case]=fixture(case,params)
for f in fixtures.values():f['bvh']=[BVHTree.FromPolygons([v.co[:] for v in o.data.vertices],[p.vertices[:] for p in o.data.polygons]) for o in f['meshes']]
skin=fixtures['NORMAL']['body'].data.materials[0]
def ray(case,x,y,above=True):
 hits=[]
 for tree in fixtures[case]['bvh']:
  p,_,_,_=tree.ray_cast(Vector((x,y,2 if above else .4)),Vector((0,0,-1 if above else 1)))
  if p is not None:hits.append(p.z)
 return (max(hits) if above else min(hits)) if hits else None

# All band profiles share topology and fixed endpoints; only the body-contact arc changes.
SPECS=[('STRAP_L_ARM',-.52,-.27,-.06,.045),('STRAP_R_ARM',.52,.27,-.06,.045),('STRAP_L_LEG',-.200,-.005,.490,.058),('STRAP_R_LEG',.200,.005,.490,.058),('STRAP_TORSO',-.25,.25,-.009,.035)]
straps=[];profiles={};saddle_profiles={}
def driver(obj,path,root,expression,index=None):
 fc=obj.driver_add(path) if index is None else obj.driver_add(path,index);dr=fc.driver
 for var,prop in [('g','girth'),('m','muscle'),('s','body_scale')]:
  v=dr.variables.new();v.name=var;v.type='SINGLE_PROP';v.targets[0].id=root;v.targets[0].data_path='["'+prop+'"]'
 dr.expression=expression
def morphs(o,root,coords):
 o.shape_key_add(name='Normal');base=coords['NORMAL']
 for name in ['THIN','FAT','MUSCLE','SCALE105']:
  k=o.shape_key_add(name=name)
  for v,p in zip(k.data,coords[name]):v.co=p
  expression={'THIN':'max(-g,0)','FAT':'max(g,0)','MUSCLE':'m/1.7','SCALE105':'(s-1)/0.05'}[name];driver(k,'value',root,expression)
 for name,basecase in [('THIN105','THIN'),('FAT105','FAT'),('MUSCLE105','MUSCLE')]:
  k=o.shape_key_add(name=name+'_CORRECTION');k.slider_min=-1
  for i,v in enumerate(k.data):v.co=base[i]+coords[name][i]-coords[basecase][i]-coords['SCALE105'][i]+base[i]
  expression={'THIN':'max(-g,0)','FAT':'max(g,0)','MUSCLE':'m/1.7'}[basecase]+'*(s-1)/0.05';driver(k,'value',root,expression)
for name,x0,x1,y,width in SPECS:
 hinge_z=.79 if name=='STRAP_TORSO' else .83 if 'ARM' in name else .696
 root=empty(name,(x0,y,hinge_z));sign=1 if x1>x0 else -1;straps.append(root)
 for k,v in {'open':0.,'girth':0.,'muscle':0.,'body_scale':1.,'hinge_axis':'LOCAL_Y','closed_angle_deg':0.,'open_angle_deg':-115.*sign}.items():root[k]=v
 root.id_properties_ui('open').update(min=0,max=1);root.id_properties_ui('girth').update(min=-1,max=1,description='-1 thin; 0 normal; +1 fat. Each band adjusts independently.')
 root.id_properties_ui('muscle').update(min=0,max=1.7);root.id_properties_ui('body_scale').update(min=1,max=1.05)
 fc=root.driver_add('rotation_euler',1);v=fc.driver.variables.new();v.name='o';v.type='SINGLE_PROP';v.targets[0].id=root;v.targets[0].data_path='["open"]';fc.driver.expression=f'o*{math.radians(-115*sign)}'
 for label,x in [('HINGE',x0),('LATCH',x1)]:
  fixed=cube(name+'_MOUNT_'+label,(x,y,(.657+hinge_z)/2),(.037,width+.025,hinge_z-.657),frame,.005);fixed['fixed_mount_for']=name
  pin=cylinder(name+'_PIN_'+label,(x,y,hinge_z),.012,width+.032,steel);pin.rotation_euler.x=math.pi/2;pin['fixed_mount_for']=name
 if 'ARM' in name:
  rail=cube(name+'_MOUNT_OUTRIGGER',(math.copysign(.40,x0),y,.665),(.26,width+.035,.045),frame);rail['fixed_mount_for']=name
 coords={};contact={}
 for case in CASES:
  edgepts=[];count=15 if name=='STRAP_TORSO' else 10 if 'ARM' in name else 11
  for dy in [-width/2,0,width/2]:
   yy=y+dy;lo,hi=sorted((x0+.014*sign,x1-.014*sign));xs=[lo+(hi-lo)*j/800 for j in range(801)]
   valid=[x for x in xs if ray(case,x,yy) is not None]
   if name=='STRAP_TORSO':
    # Select the contiguous trunk interval around the centre, excluding the arms.
    center=min(range(len(xs)),key=lambda i:abs(xs[i]));l=center;r=center
    while l>0 and ray(case,xs[l-1],yy) is not None:l-=1
    while r<len(xs)-1 and ray(case,xs[r+1],yy) is not None:r+=1
    valid=xs[l:r+1]
   aa,bb=min(valid),max(valid);cx=(aa+bb)/2
   cz=(ray(case,cx,yy)+ray(case,cx,yy,False))/2
   row=[]
   for j in range(count):
    angle=math.pi*(1-j/(count-1)) if sign>0 else math.pi*j/(count-1)
    direction=Vector((math.cos(angle),0,math.sin(angle)));origin=Vector((cx,yy,cz))
    hits=[t.ray_cast(origin,direction) for t in fixtures[case]['bvh']];hits=[h for h in hits if h[0] is not None]
    hit,norm,_,_=(max if name=='STRAP_TORSO' else min)(hits,key=lambda h:h[3]);norm=norm.normalized()
    if norm.dot(direction)<0:norm=-norm
    clearance=.006 if 'ARM' in name and 'MUSCLE' in case else .004
    row.append((hit+norm*clearance,hit+norm*(clearance+.008)))
   edgepts.append(row)
  # Three rows across the width follow longitudinal curvature as well as girth.
  vs=[]
  def endpoint(x,z):
   return [Vector((x,y+dy,z+dz)) for dy,dz in [(-width/2,-.004),(0,-.004),(width/2,-.004),(width/2,.004),(0,.004),(-width/2,.004)]]
  vs.extend(endpoint(x0,hinge_z))
  for j in range(count):
   vs.extend([edgepts[k][j][0] for k in range(3)]+[edgepts[k][j][1] for k in [2,1,0]])
  vs.extend(endpoint(x1-sign*.012,hinge_z+.038));vs.extend(endpoint(x1,hinge_z+.012))
  # Relax only local collisions; preserve the rest of each snug surface profile.
  for iteration in range(5):
   for j in range(1,count):
    for strip in range(2):
     ids=[6*j+strip,6*j+strip+1,6*(j+1)+strip+1,6*(j+1)+strip]
     a,b,c,d=[vs[k] for k in ids];push=Vector((0,0,0))
     for u in [.2,.5,.8]:
      for v in [.2,.5,.8]:
       p=a.lerp(d,u).lerp(b.lerp(c,u),v)
       hits=[t.find_nearest(p) for t in fixtures[case]['bvh']];hits=[h for h in hits if h[0] is not None]
       loc,norm,_,dist=min(hits,key=lambda h:h[3]);gap=(p-loc).dot(norm)
       if gap<.001:
        delta=norm*(.001-gap)
        if delta.length>push.length:push=delta
     if push.length:
      for k in ids:vs[k]+=push;vs[k//6*6+5-k%6]+=push
  for iteration in range(3):
   for k in range(6,6*(count+1)):
    p=vs[k];hits=[t.find_nearest(p) for t in fixtures[case]['bvh']];loc,n,_,d=min((h for h in hits if h[0] is not None),key=lambda h:h[3])
    if (p-loc).dot(n)<0:vs[k]=loc+n*.001
  fs=[tuple(reversed(range(6)))]
  for j in range(count+2):
   for k in range(6):fs.append((j*6+k,j*6+(k+1)%6,(j+1)*6+(k+1)%6,(j+1)*6+k))
  fs.append(tuple((count+2)*6+k for k in range(6)))
  tmp=mesh_obj(name+'_PROFILE_'+case,vs,fs,material=strapmat)
  coords[case]=[v.co.copy()-root.location for v in tmp.data.vertices]
  for c in list(tmp.users_collection):c.objects.unlink(tmp)
  allp=[p for row in edgepts for pair in row for p in pair]
  contact[case]={'min_x':min(p.x for p in allp),'max_x':max(p.x for p in allp),'top':max(p.z for p in allp)}

 me=tmp.data.copy();me.name=name+'_BandMesh'
 for v,p in zip(me.vertices,coords['NORMAL']):v.co=p
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name+'_BAND',me);GEO.objects.link(ob);ob.parent=root;ob.location=(0,0,0);morphs(ob,root,coords)
 buckle(name,Vector((x1-sign*.022,y,hinge_z+.052)),width,root)
 if name!='STRAP_TORSO':
  saddle=cube(name+'_MOUNT_SADDLE',((x0+x1)/2,y,.70),(abs(x1-x0),width+.025,.02),blue,.003);saddle['fixed_mount_for']=name
  scoords={}
  for case in CASES:
   aa,bb=contact[case]['min_x'],contact[case]['max_x'];lower=[ray(case,aa+(bb-aa)*j/20,y+dy,False) for j in range(21) for dy in [-width/2,0,width/2]];lower=[v for v in lower if v is not None]
   ztop=min(lower)-.001
   scoords[case]=[Vector(((aa+bb)/2+(1 if v.co.x>0 else -1)*(bb-aa+.018)/2-saddle.location.x,v.co.y,(ztop if v.co.z>0 else .686)-saddle.location.z)) for v in saddle.data.vertices]
  for v,p in zip(saddle.data.vertices,scoords['NORMAL']):v.co=p
  morphs(saddle,root,scoords);saddle_profiles[name]={c: max(p.z+saddle.location.z for p in vs) for c,vs in scoords.items()}
 profiles[name]=contact

# Exact marker coordinate systems are the incision root coordinate systems.
patient=fixtures['NORMAL']['body'];incisions=[]
patient_tree=BVHTree.FromPolygons([v.co[:] for v in patient.data.vertices],[p.vertices[:] for p in patient.data.polygons])
# Restrict the live cuts to the continuous trunk island. Separate face/head islands
# must never be passed to a volumetric Boolean together with the trunk.
bm=bmesh.new();bm.from_mesh(patient.data);bm.verts.ensure_lookup_table()
seed=min(bm.verts,key=lambda v:(v.co-Vector((0,-.08,.905))).length);todo=[seed];component={seed}
while todo:
 v=todo.pop()
 for e in v.link_edges:
  w=e.other_vert(v)
  if w not in component:component.add(w);todo.append(w)
indices={v.index for v in component};bm2=bm.copy();bm2.verts.ensure_lookup_table()
bmesh.ops.delete(bm2,geom=[v for v in bm2.verts if v.index not in indices],context='VERTS');bmesh.ops.recalc_face_normals(bm2,faces=list(bm2.faces))
me=bpy.data.meshes.new('Patient_PreparedContinuousTrunk');bm2.to_mesh(me);bm2.free()
for m in patient.data.materials:me.materials.append(m)
patient.name='REF_PATIENT_NORMAL_HeadHands';core=bpy.data.objects.new('REF_PATIENT_NORMAL_Body',me);fixtures['NORMAL']['collection'].objects.link(core)
bmesh.ops.delete(bm,geom=list(component),context='VERTS');bm.to_mesh(patient.data);bm.free()
fixtures['NORMAL']['meshes'].append(core);fixtures['NORMAL']['body']=core;patient=core
def surface_local(M,x,y):
 start=M@Vector((x,y,.08));direction=-(M.to_3x3()@Vector((0,0,1)))
 p,_,_,_=patient_tree.ray_cast(start,direction)
 if p is None:raise RuntimeError('Incision projection missed patient')
 return M.inverted()@p
for suffix,rx,ry in [('KIDNEY_L',.032,.044),('KIDNEY_R',.032,.044),('LIVER',.051,.029)]:
 marker=fixtures['NORMAL']['markers']['INC_'+suffix];M=marker.matrix_world.copy();root=empty('INCISION_'+suffix,(0,0,0));root.matrix_world=M;root['source_marker']='INC_'+suffix;root['open']=1.;root['review_visible']=True;root.id_properties_ui('open').update(min=0,max=1)
 n=16;vs=[]
 for scale,zoff in [(1.19,-.0005),(1.08,.004),(1,.001),(.82,-.022),(1.19,-.030)]:
  for i in range(n):
   t=2*math.pi*i/n;p=surface_local(M,rx*scale*math.cos(t),ry*scale*math.sin(t));p.z+=zoff;vs.append(p)
 fs=[]
 for k in range(3):
  for i in range(n):fs.append((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i))
 fs.append(tuple(3*n+i for i in range(n)))
 for i in range(n):fs.append((i,4*n+i,4*n+(i+1)%n,(i+1)%n))
 fs.append(tuple(reversed(range(4*n,5*n))))
 o=mesh_obj(root.name+'_OPENING',vs,fs,material=skin);o.parent=root;o.data.materials.append(cavity)
 for p in o.data.polygons:
  if p.index>=2*n:p.material_index=1
 # The live cutter is local to the marker normal, not aligned to a world axis.
 cutvs=[(rx*math.cos(i*2*math.pi/n),ry*math.sin(i*2*math.pi/n),z) for z in [-.04,.08] for i in range(n)]
 cutfs=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
 cut=mesh_obj(root.name+'_CUTTER',cutvs,cutfs,col=HIDDEN);cut.parent=root;cut.hide_render=True;cut.hide_set(True)
 mod=patient.modifiers.new(root.name+'_CUT','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
 capvs=[surface_local(M,0,0)]+[surface_local(M,rx*math.cos(i*2*math.pi/n),ry*math.sin(i*2*math.pi/n)) for i in range(n)]
 for p in capvs:p.z+=.001
 cover=mesh_obj(root.name+'_CLOSED_COVER',capvs,[(0,i+1,(i+1)%n+1) for i in range(n)],material=skin);cover.parent=root;sol=cover.modifiers.new('Cover thickness','SOLIDIFY');sol.thickness=.003;cover.hide_render=True;cover.hide_set(True)
 # Closed guides use the opening's boundary and remain subtle on the patient surface.
 guide=line(root.name+'_CLOSED_GUIDE',[M@p for p in capvs[1:]]+[M@capvs[1]],.0008,cavity);parent(guide,root);guide.hide_render=True;guide.hide_set(True);guide['review_only']=True
 for part in [o,cover,guide]:
  part.hide_set(False)
  for prop in ['hide_render','hide_viewport']:
   fc=part.driver_add(prop);dr=fc.driver
   for vn,pn in [('a','open'),('v','review_visible')]:
    va=dr.variables.new();va.name=vn;va.type='SINGLE_PROP';va.targets[0].id=root;va.targets[0].data_path='["'+pn+'"]'
   dr.expression='not v or a<0.5' if part==o else 'not v or a>=0.5'
 incisions.append(root)

sc.world=bpy.data.worlds.new('Soft Studio');sc.world.use_nodes=True;bg=next(n for n in sc.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.55,.65,.75,1);bg.inputs['Strength'].default_value=.45
sc.render.engine='CYCLES';sc.cycles.samples=32;sc.cycles.use_denoising=True;sc.render.resolution_x=1200;sc.render.resolution_y=1000;sc.render.resolution_percentage=100;sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='AgX'
hero=camera('CAMERA_PATIENT',(-2.9,3.6,4.7),(-.17,-.02,.6),2.75)
top=camera('CAMERA_STRAPS',(0,.001,4),(0,0,.7),2.55)
close=camera('CAMERA_INCISIONS',(-.18,.18,1.75),(0,-.145,.88),.47)
# G25 tuning camera, mapped from Unity Y-up into this table's local Blender axes.
fixed=camera('CAMERA_G25_FIXED',(1.8,0,3.6),(0,0,1),2.6);fixed.data.type='PERSP';fixed.data.lens_unit='FOV';fixed.data.angle=math.radians(48)
sc['patient_source']=str(SOURCE);sc['fixture_contract']='Approved bare patient only. Static fit poses preserve rest proportions; no character source modified.'
sc['girth_contract']='girth -1..1 = thin1 / normal / belly1; muscle 0..1.7; body_scale 1..1.05. Independent controls per band; fixed saddles adapt without following hinge.'
sc['review_status']='Awaiting Fedya OK. No Unity import.'
def set_case(case,opened=0,incopen=1):
 for n,f in fixtures.items():f['collection'].hide_render=n!=case;f['collection'].hide_viewport=n!=case
 pars=CASES[case]
 for r in straps:r['open']=opened;r['girth']=pars.get('belly',0)-pars.get('thin',0);r['muscle']=pars.get('muscle',0);r['body_scale']=pars.get('scale',1);r.update_tag()
 for r in incisions:
  r['open']=incopen;r['review_visible']=case=='NORMAL';r.update_tag()
 sc.frame_set(sc.frame_current);bpy.context.view_layer.update()
def render(name,cam,case='NORMAL',opened=0,incopen=1):
 set_case(case,opened,incopen);sc.camera=cam;sc.render.filepath=str(REND/(name+'.png'));bpy.ops.render.render(write_still=True)
girthcam=camera('CAMERA_GIRTH',(-2.9,3.6,4.7),(0,.14,.8),1.85)
set_case('NORMAL');sc.camera=hero
for im in bpy.data.images:
 if im.source=='FILE' and not im.packed_file:
  try:im.pack()
  except:pass
dest=OUT/('Operations_PATIENT_'+REV+'.blend');assert not dest.exists();bpy.ops.wm.save_as_mainfile(filepath=str(dest))
(REND/'fit_profiles.json').write_text(json.dumps({'source_marker_matrices':source_marker_matrices,'cases':CASES,'profiles':profiles,'saddles':saddle_profiles},indent=2))
if '--build-only' in sys.argv:sys.exit()
if '--quick' in sys.argv:
 render('01_closed',hero);render('03_incisions_open',close);sys.exit()
render('01_closed',hero);render('02_open',hero,opened=1)
render('03_incisions_open',close);render('04_incisions_closed',close,incopen=0)
render('05_fixed',fixed)
for case in ['THIN','NORMAL','FAT','MUSCLE105']:render('06_girth_'+case,girthcam,case,incopen=0)
print('COMPLETE',dest)
