import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\TASER-ASTRA-001');OUT=ROOT/'TASER_ASTRA_001_v01.blend'
assert not OUT.exists(),'Keep numbered revisions'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\taser_tripo_base.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');obj.name='Item_Taser';bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
me=obj.data;me.calc_loop_triangles();source_tri=len(me.loop_triangles)
raw=obj.copy();raw.data=me.copy();raw.name='Tripo_original_reference';ref=bpy.data.collections.new('REFERENCE_Tripo_source_not_exported');bpy.context.scene.collection.children.link(ref);ref.objects.link(raw);ref.hide_render=True;ref.hide_viewport=True
bm=bmesh.new();bm.from_mesh(me);before=sum(not e.is_manifold for e in bm.edges)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
boundary=[e for e in bm.edges if e.is_boundary];bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.calc_loop_triangles()
closed_tri=len(me.loop_triangles);mod=obj.modifiers.new('Local_lowpoly_budget','DECIMATE');mod.ratio=560/closed_tri;bpy.ops.object.modifier_apply(modifier=mod.name);me=obj.data
lo=min(v.co.z for v in me.vertices);hi=max(v.co.z for v in me.vertices);scale=.15/(hi-lo)
for v in me.vertices:v.co=Vector((v.co.x*scale,v.co.y*scale,(v.co.z-lo)*scale))
for v in raw.data.vertices:v.co=Vector((v.co.x*scale,v.co.y*scale,(v.co.z-lo)*scale))
def make(name,color,rough,metal):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;return m
mats=[make('Taser_black_rubber',(.022,.024,.027),.65,0),make('Taser_yellow_rubber',(.96,.69,.003),.55,0),make('Taser_contact_silver',(.38,.42,.49),.34,.65)];me.materials.clear()
for m in mats:me.materials.append(m)
for p in me.polygons:
 c=p.center/scale;x,y,z=c.x,c.y,c.z
 if z>.934:p.material_index=2
 elif y<-.098 and abs(x)<.095 and .63<z<.85:p.material_index=1
 else:
  qx=abs(x)-.164;qz=abs(z-.465)-.382;dist=math.hypot(max(qx,0),max(qz,0))+min(max(qx,qz),0)-.039
  p.material_index=1 if (y<-.063 or y>.090) and dist>-.004 else 0
 p.use_smooth=True
me.update();bpy.context.view_layer.update()
# Bake clean material colours into one atlas; no source grain is retained.
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
atlas=bpy.data.images.new('TASER_basecolor_v01',width=1024,height=1024,alpha=False)
for m in mats:
 n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=atlas;m.node_tree.nodes.active=n
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=12
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'});atlas.filepath_raw=str(ROOT/'Textures/TASER_basecolor_v01.png');atlas.file_format='PNG';atlas.save();atlas.pack()
for m in mats:
 t=next(n for n in m.node_tree.nodes if n.type=='TEX_IMAGE');b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');m.node_tree.links.new(t.outputs['Color'],b.inputs['Base Color'])
me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me);remaining=set(bm.verts);islands=0
while remaining:
 islands+=1;stack=[remaining.pop()]
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);stack.append(w)
coords=[v.co.copy() for v in me.vertices];dims=[max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3)]
report={'source_triangles':source_tri,'source_nonmanifold_edges':before,'source_closed_triangles':closed_tri,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'mesh_islands':islands,'signed_volume_m3':bm.calc_volume(signed=True),'finite_vertices':all(math.isfinite(c) for v in coords for c in v),'uv_layers':len(me.uv_layers),'dimensions_m':dims,'budget':[300,600],'origin':'bottom centre of upright body','front_axis':'-Y','texture':'1024px locally baked clean yellow/black/silver atlas, packed','shading':'smooth','local_polish':'close source boundary loops, local reduction, clean colours and UV; source rectangular shell retained','paid_extras':False}
bm.free();report['pass']=300<=report['final_triangles']<=600 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0 and report['signed_volume_m3']>0 and report['finite_vertices'] and abs(dims[2]-.15)<1e-5
(ROOT/'Validation/mesh_v01.json').write_text(json.dumps(report,indent=2));print('TASER_MESH',json.dumps(report));assert report['pass'],report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'TASER_ASTRA_001_v01.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
target=Vector((0,0,.075));scene.world=bpy.data.worlds.new('Preview_world');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.16,.18,.21,1);bg.inputs[1].default_value=.7
for name,loc,power,size in [('Key',(-.22,-.34,.35),5,.24),('Fill',(.28,-.10,.20),1.8,.20),('Rim',(.07,.35,.3),4.5,.23)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=size;o=bpy.data.objects.new(name,ld);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera');cam=bpy.data.objects.new('Preview_camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=.18
scene.cycles.samples=24;scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
views={'01_front':(0,-4,.075),'02_back':(0,4,.075),'03_left':(-4,0,.075),'04_right':(4,0,.075),'05_top':(0,0,4),'06_bottom':(0,0,-4),'07_hero':(.8,-2,.50)}
for name,loc in views.items():
 cam.location=loc;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Previews'/f'{name}_v01.png');bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=.3;area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT));print('TASER_FINAL',json.dumps(report))
