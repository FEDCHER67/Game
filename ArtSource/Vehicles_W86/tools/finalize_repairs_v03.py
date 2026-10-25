import bpy,bmesh,json,sys
from pathlib import Path
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
from topology_repair_v03 import repair
ROOT=R.ROOT
stats=json.loads((ROOT/'validation_v01.json').read_text());patch={x['name']:x for x in json.loads((ROOT/'validation_v02.json').read_text())}
final=[]
for p in stats:
 name=p['name'];folder=Path(p['folder']);p['revision']=1
 if name=='ASTRA_STATIC_VAN':p=patch[name];final.append(p);continue
 if name not in ['PANEL_VAN','CONTAINER_TRUCK']:final.append(p);continue
 bpy.ops.wm.open_mainfile(filepath=str(folder/(name+'_v01.blend')))
 lod0=next(o for o in bpy.context.scene.objects if o.name.endswith('LOD0'))
 for o in list(bpy.context.scene.objects):
  if o.name.endswith(('LOD1','LOD2')):bpy.data.objects.remove(o,do_unlink=True)
 if name=='CONTAINER_TRUCK':lod0.data=repair(lod0.data)
 else:
  bm=bmesh.new();bm.from_mesh(lod0.data);bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
  flap=[f for f in bm.faces if all(abs(v.co.z-.54)<1e-4 and abs(v.co.x)<.29 and -2.366<v.co.y<-2.319 for v in f.verts)]
  assert len(flap)==2;bmesh.ops.delete(bm,geom=flap,context='FACES_ONLY');loose=[e for e in bm.edges if not e.link_faces]
  if loose:bmesh.ops.delete(bm,geom=loose,context='EDGES')
  bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(lod0.data);bm.free()
 lods=[lod0]
 for level,ratio in [(1,.5),(2,.23)]:
  o=lod0.copy();o.data=lod0.data.copy();bpy.context.collection.objects.link(o);o.name='SM_'+name+'_LOD'+str(level);o.hide_set(False);bpy.context.view_layer.objects.active=o;mod=o.modifiers.new('LOD reduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True;bpy.ops.object.modifier_apply(modifier=mod.name);lods.append(o)
 p['geometry_audit']=[]
 for i,o in enumerate(lods):
  bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data)
  a={'name':o.name,'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'degenerate_faces':sum(f.calc_area()<1e-10 for f in bm.faces),'scale':list(o.scale),'location':list(o.location)};bm.free();assert a['boundary_edges']==a['nonmanifold_edges']==a['degenerate_faces']==0,a;p['geometry_audit'].append(a);o.hide_render=i!=0;o.hide_set(i!=0)
 p['lod_triangles']=[R.tris([o]) for o in lods];p['revision']=3
 cols=[o for o in bpy.context.scene.objects if o.name.startswith('UCX')]
 for c in cols:c.hide_set(True);c.hide_render=True
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/(name+'_v03.blend')))
 for group,suffix in [(lods,''),(cols,'_collisions')]:
  bpy.ops.object.select_all(action='DESELECT')
  for o in group:o.hide_set(False);o.select_set(True)
  bpy.context.view_layer.objects.active=group[0]
  bpy.ops.export_scene.fbx(filepath=str(folder/(name+suffix+'_v03.fbx')),use_selection=True,object_types={'MESH'},global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',axis_forward='-Z',axis_up='Y',bake_space_transform=True,mesh_smooth_type='FACE',bake_anim=False,path_mode='RELATIVE')
 (folder/(name+'_collisions_v03.json')).write_text((folder/(name+'_collisions_v01.json')).read_text(),encoding='utf-8')
 final.append(p)
(ROOT/'selected_models_v01.json').write_text(json.dumps(final,indent=2),encoding='utf-8')
