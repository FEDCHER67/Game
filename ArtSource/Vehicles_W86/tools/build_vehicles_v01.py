import sys,json,math,struct,re,bmesh
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools')
import blender_runner_v01 as R
ROOT=R.ROOT
PALETTE=[('paint_blue','5A7FA6',.22,.30),('paint_red','A8504A',.22,.31),('paint_cream','C9B79A',.18,.35),('paint_green','6F8F6A',.22,.34),('white','E9ECEB',.12,.35),('rubber','24262A',0,.85),('trim','36383E',.05,.65),('glass','2C3A46',.25,.14),('chrome','84888E',.85,.26),('lamp','E8DCBB',.05,.20),('tail','A8322F',.15,.23),('amber','D9A34C',.05,.25),('orange','C78D49',.18,.38),('sand','B9A684',0,.92),('container','985D50',.18,.4),('darkpaint','744D42',.18,.45),('interior','6F6A60',0,.8),('black','1C1D20',0,.8)]
IDX={v[0]:i for i,v in enumerate(PALETTE)}

def shared_material():
 m=bpy.data.materials.new('MAT_W86_VehiclePalette_v01');m.use_nodes=True;nt=m.node_tree;n=nt.nodes.get('Principled BSDF')
 for prop,file in [('Base Color','W86_VehiclePalette_v01.png'),(None,'W86_VehicleSurface_v01.png')]:
  im=bpy.data.images.load(str(ROOT/'shared'/file),check_existing=True);tex=nt.nodes.new('ShaderNodeTexImage');tex.image=im;tex.interpolation='Closest';tex.extension='EXTEND'
  if prop:nt.links.new(tex.outputs['Color'],n.inputs[prop])
  else:
   im.colorspace_settings.name='Non-Color';sp=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(tex.outputs['Color'],sp.inputs['Color']);nt.links.new(sp.outputs['Red'],n.inputs['Metallic']);nt.links.new(sp.outputs['Green'],n.inputs['Roughness'])
 return m

def uvset(o,keys,mat):
 o.data.materials.clear();o.data.materials.append(mat)
 uv=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
 for f,key in zip(o.data.polygons,keys):
  f.material_index=0;i=IDX[key];pos=((i%8+.5)/8,1-(i//8+.5)/4)
  for l in f.loop_indices:uv.data[l].uv=pos

def sample(o,f):
 if not o.data.materials:return (.5,.5,.5)
 mat=o.data.materials[min(f.material_index,len(o.data.materials)-1)]
 if mat and mat.use_nodes:
  imgs=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
  if imgs and o.data.uv_layers.active:
   im=imgs[0]
   if im.size[0] and len(im.pixels):
    uv=o.data.uv_layers.active.data[f.loop_start].uv;w,h=im.size;x=min(w-1,max(0,int(uv.x*w)));y=min(h-1,max(0,int(uv.y*h)));i=4*(y*w+x)
    return tuple(im.pixels[i:i+3])
 return tuple(mat.diffuse_color[:3]) if mat else (.5,.5,.5)

def remap(obs,p,mat,kind='normal'):
 body={'SEDAN':'paint_blue','COMPACT':'paint_red','DISPLAY_COUPE':'paint_cream','DISPLAY_GT':'paint_green','PANEL_VAN':'paint_cream','ASTRA_STATIC_VAN':'paint_cream','FLATBED':'orange','BOX_TRUCK':'white'}[p['name']]
 for o in obs:
  keys=[]
  for f in o.data.polygons:
   mn=o.data.materials[f.material_index].name.lower() if o.data.materials else ''
   if 'quaternius' in p['author'].lower():
    key='glass' if 'window' in mn else 'rubber' if 'black' in mn else 'chrome' if 'grey' in mn else 'lamp' if 'headlight' in mn else 'tail' if 'taillight' in mn else 'trim' if 'darkorange' in mn else body
   elif p['name']=='ASTRA_STATIC_VAN':
    key='glass' if 'glass' in mn else 'rubber' if 'tire' in mn else 'trim' if 'trim' in mn or 'grille' in mn else 'chrome' if 'hub' in mn else 'lamp' if 'white' in mn else 'amber' if 'indicator' in mn else 'tail' if 'tail' in mn else 'interior' if 'seat' in mn or 'interior' in mn else body
   else:
    c=sample(o,f);v=max(c);a=sum(c)/3
    # Texture pixel samples are linear. Preserve meaningful palette roles, remove pastel tyres/glazing.
    if kind=='wheel':key='rubber' if v<.32 else 'chrome'
    elif v<.09:key='rubber'
    elif c[2]>c[0]*1.15 and c[2]>c[1]*1.03:
     key='glass' if p['name']!='PANEL_VAN' or a>.65 else body
    elif c[0]>.5 and c[1]<.18 and c[2]<.18:key='tail'
    elif c[0]>.5 and c[1]>.25 and c[2]<.1:key='amber'
    elif v>.85:key='glass' if p['name']=='PANEL_VAN' else body
    elif a<.25 and max(c)-min(c)<.06:key='trim'
    elif max(c)-min(c)<.04:key='chrome'
    elif c[0]>c[2]*1.5 and c[1]>.3:key='sand' if p['name']=='FLATBED' and f.center.z>1.3 else body
    else:key=body
   keys.append(key)
  uvset(o,keys,mat)

def bake(obs):
 for o in obs:
  mx=o.matrix_world.copy();o.parent=None;o.data=o.data.copy();o.data.transform(mx);o.matrix_world=Matrix.Identity(4);o.animation_data_clear()
 return obs

def join(obs,name):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();o=bpy.context.object;o.name=name;o.data.name=name+'_Mesh'
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
 # Palette UVs define all shading; discard source vertex colour data.
 for a in list(o.data.color_attributes):o.data.color_attributes.remove(a)
 return o

def box(name,center,size,mat=None,key='trim'):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if mat:uvset(o,[key]*len(o.data.polygons),mat)
 return o

def donor_wheel(path,p):
 R.clean();bpy.ops.wm.obj_import(filepath=path,forward_axis='NEGATIVE_Z',up_axis='Y',use_split_groups=True)
 o=next(o for o in bpy.context.scene.objects if o.name=='wheel-front-right');bake([o]);lo,hi=R.bounds([o]);mid=(lo+hi)/2
 o.data.transform(Matrix.Translation(-mid))
 # Store source mesh in memory across scene resets via Python data lists.
 data={'verts':[list(v.co) for v in o.data.vertices],'faces':[list(f.vertices) for f in o.data.polygons],'keys':['rubber' if max(sample(o,f))<.32 else 'chrome' for f in o.data.polygons],'dimensions':list(hi-lo)}
 return data

def refine_truck(obs,p,mat,donor):
 o=obs[0];bm=bmesh.new();bm.from_mesh(o.data)
 # Components from source construction preserve wheel/axle anchors. Remove tyres and hubs only.
 unseen=set(bm.verts);removed=[];centers=[]
 while unseen:
  start=unseen.pop();stack=[start];comp={start}
  while stack:
   v=stack.pop()
   for e in v.link_edges:
    n=e.other_vert(v)
    if n in unseen:unseen.remove(n);comp.add(n);stack.append(n)
  lo=Vector([min(v.co[i] for v in comp) for i in range(3)]);hi=Vector([max(v.co[i] for v in comp) for i in range(3)]);d=hi-lo;c=(hi+lo)/2
  if .7<abs(c.x)<1.4 and hi.z<1.08 and .3<d.y<1.15 and .3<d.z<1.15 and d.x<.8 and abs(d.y-d.z)<.1:
   removed+=list(comp)
   if d.y>.8:centers.append((list(c),list(d)))
 bmesh.ops.delete(bm,geom=removed,context='VERTS');bm.to_mesh(o.data);bm.free()
 assert len(centers)==(6 if p['name']=='FLATBED' else 12),('wheel identification',p['name'],len(centers))
 new=[o]
 for i,(c,d) in enumerate(centers):
  me=bpy.data.meshes.new('DonorWheel');me.from_pydata(donor['verts'],[],donor['faces']);me.update();w=bpy.data.objects.new('DonorWheel',me);bpy.context.collection.objects.link(w)
  size=Vector(d);src=Vector(donor['dimensions']);scale=Vector([size[j]/src[j] for j in range(3)])
  for v in me.vertices:
   v.co=Vector([v.co[j]*scale[j] for j in range(3)])+Vector(c)
  uvset(w,donor['keys'],mat);new.append(w)
 p['wheel_contact_audit']={'wheels':len(centers),'axle_centers_and_original_bounds':centers,'replacement':'source wheel bounds exactly matched; original hubs/tyres removed'}
 return new

def colliders(name,lo,hi):
 w,L,h=hi-lo;out=[]
 if name=='CONTAINER_TRUCK':
  boxes=[((0,-7.1,2.0),(2.45,2.8,4.0)),((0,1.5,2.69),(2.44,12.19,2.62)),((0,-.1,.65),(2.4,15.8,1.3))]
 elif name=='DUMP_TRUCK':boxes=[((0,-3.1,1.6),(2.5,2.3,3.1)),((0,1.1,1.9),(2.72,5.7,2.1)),((0,0,.6),(2.5,8.1,1.2))]
 else:boxes=[((0,0,h*.26),(w*.92,L*.96,h*.52)),((0,-L*.03,h*.7),(w*.83,L*(.62 if 'VAN' in name else .52),h*.6))]
 for i,(c,d) in enumerate(boxes):
  o=box('UCX_'+name+'_'+str(i).zfill(2),c,d);out.append(o)
 return out

if __name__=='__main__':
 picks=json.loads((ROOT/'picks_v01.json').read_text());stats=[]
 for p in picks:
  name=p['deliverable'];folder=ROOT/p['name'];donor=donor_wheel(p['source'],p) if 'reuse_source' in p else None
  R.clean()
  if p['name']=='PANEL_VAN':
   bpy.ops.wm.obj_import(filepath=p['source'],forward_axis='NEGATIVE_Z',up_axis='Y',use_split_groups=True);obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
  else:obs=R.load(p.get('reuse_source',p['source']),True)
  bake(obs);source_tri=R.tris(obs)
  for extra in list(bpy.context.scene.objects):
   if extra.type!='MESH':bpy.data.objects.remove(extra,do_unlink=True)
  mat=shared_material();remap(obs,p,mat)
  if donor:obs=refine_truck(obs,p,mat,donor)
  else:
   lo,hi=R.bounds(obs);size=hi-lo
   desired={'SEDAN':(None,4.35,1.45),'COMPACT':(None,3.85,1.47),'DISPLAY_COUPE':(None,4.35,1.32),'DISPLAY_GT':(None,4.45,1.34),'PANEL_VAN':(2.05,5.0,2.35)}.get(p['name'])
   if desired:
    if p['author']=='Quaternius':
     # Extend cabins above the beltline; retain round wheels and stretch their axle spacing only.
     factor=(desired[2]-.55)/(size.z-.55);ys=desired[1]/size.y
     for o in obs:
      if 'wheel' in o.name.lower():
       a,b=R.bounds([o]);cy=(a.y+b.y)/2
       for v in o.data.vertices:v.co.y+=cy*(ys-1)
      else:
       for v in o.data.vertices:
        v.co.y*=ys
        if v.co.z>.55:v.co.z=.55+(v.co.z-.55)*factor
    elif p['name']=='PANEL_VAN':
     # Preserve circular wheel geometry: increase the wheelbase between axles, then extend upper cargo body.
     uniform=1.35;extra=5-size.y*uniform
     for o in obs:
      wheel='wheel' in o.name.lower();a,b=R.bounds([o]);cy=(a.y+b.y)/2
      for v in o.data.vertices:
       oldy=v.co.y;v.co*=uniform
       if wheel:v.co.y+=math.copysign(extra/2,cy)
       else:
        v.co.y+=max(-1,min(1,oldy/.4))*extra/2
        if v.co.z>.81:v.co.z=.81+(v.co.z-.81)*(2.35-.81)/(size.z*uniform-.81)
   R.center(obs);bake(obs)
  lod0=join(obs,'SM_'+name+'_LOD0');lo,hi=R.bounds([lod0])
  # Apply a single base-centre translation to all models, including truck donor assemblies.
  shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));lod0.data.transform(Matrix.Translation(-shift));lo,hi=R.bounds([lod0])
  lods=[lod0]
  for level,ratio in [(1,.5),(2,.23)]:
   lod=lod0.copy();lod.data=lod0.data.copy();bpy.context.collection.objects.link(lod);lod.name='SM_'+name+'_LOD'+str(level)
   bpy.context.view_layer.objects.active=lod;mod=lod.modifiers.new('LOD reduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name);lods.append(lod)
  for lod in lods:
   bm=bmesh.new();bm.from_mesh(lod.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(lod.data);bm.free()
   for f in lod.data.polygons:f.use_smooth=False
  cols=colliders(name,lo,hi)
  # Truck collision coordinates were authored in original source space.
  if donor:
   for c in cols:c.location-=shift
  manifest={'schema':'W86.static-collision.v01','asset':name,'units':'metres','blender_axes':'Z up, -Y front','fbx_axes':'Y up; -Z export forward setting; verify +Z front on roundtrip','pivot':'base centre; visual meshes and root identity','unity_instruction':'UCX names alone do not create colliders. Add BoxColliders from unity_local_center/size, disable UCX renderers; or convex MeshColliders from separate collision FBX. Do not render UCX.','colliders':[]}
  for c in cols:
   cc=c.location;dd=c.dimensions
   manifest['colliders'].append({'name':c.name,'shape':'convex_box','convex':True,'triangles':12,'blender_center':list(cc),'blender_size':list(dd),'unity_local_center':[cc.x,cc.z,-cc.y],'unity_local_size':[dd.x,dd.z,dd.y]})
  (folder/(name+'_collisions_v01.json')).write_text(json.dumps(manifest,indent=2),encoding='utf-8')
  for level,lod in enumerate(lods):lod.hide_render=level!=0;lod.hide_set(level!=0)
  for c in cols:c.hide_render=True;c.hide_set(True)
  audits=[]
  for o in lods:
   bm=bmesh.new();bm.from_mesh(o.data);audits.append({'name':o.name,'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces),'scale':list(o.scale),'location':list(o.location)});bm.free()
  p['geometry_audit']=audits
  stats.append({'name':name,'folder':str(folder),'source_triangles':source_tri,'lod_triangles':[R.tris([o]) for o in lods],'dimensions_m':list(hi-lo),'bounds_min':list(lo),'bounds_max':list(hi),'licence':p['licence'],'author':p['author'],'materials':1,'ucx_count':len(cols),'geometry_audit':p['geometry_audit'],'wheel_contact_audit':p.get('wheel_contact_audit'),'source':p['source'],'reuse_source':p.get('reuse_source')})
  assert R.tris([lod0])<=8000
  # Save source revision once. Future visual changes must use v02.
  dst=folder/(name+'_v01.blend');assert not dst.exists();bpy.ops.wm.save_as_mainfile(filepath=str(dst))
  for group,suffix in [(lods,''),(cols,'_collisions')]:
   bpy.ops.object.select_all(action='DESELECT')
   for o in group:o.hide_set(False);o.select_set(True)
   bpy.context.view_layer.objects.active=group[0]
   bpy.ops.export_scene.fbx(filepath=str(folder/(name+suffix+'_v01.fbx')),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Z',axis_up='Y',bake_space_transform=True,use_mesh_modifiers=True,mesh_smooth_type='FACE',bake_anim=False,path_mode='RELATIVE')
   for o in group:o.hide_set(o!=lod0)
  print('ASSET_DONE',name,stats[-1]['lod_triangles'],flush=True)
 (ROOT/'validation_v01.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
