import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\PISTOL-ASTRA-001');OUT=ROOT/'PISTOL_ASTRA_001_v01.blend'
assert not OUT.exists(),'Keep numbered revisions'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\pistol_tripo_base.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');obj.name='Item_Pistol';bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
me=obj.data;me.calc_loop_triangles();source_tri=len(me.loop_triangles)
raw=obj.copy();raw.data=me.copy();raw.name='Tripo_original_reference';ref=bpy.data.collections.new('REFERENCE_Tripo_source_not_exported');bpy.context.scene.collection.children.link(ref);ref.objects.link(raw);ref.hide_render=True;ref.hide_viewport=True
bm=bmesh.new();bm.from_mesh(me);before=sum(not e.is_manifold for e in bm.edges)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
boundary=[e for e in bm.edges if e.is_boundary];bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.calc_loop_triangles()
closed_tri=len(me.loop_triangles);mod=obj.modifiers.new('Local_lowpoly_budget','DECIMATE');mod.ratio=760/closed_tri;bpy.ops.object.modifier_apply(modifier=mod.name);me=obj.data
lo=min(v.co.z for v in me.vertices);hi=max(v.co.z for v in me.vertices);scale=.19/(max(v.co.x for v in me.vertices)-min(v.co.x for v in me.vertices))
for v in me.vertices:v.co=Vector((v.co.x*scale,v.co.y*scale,(v.co.z-lo)*scale))
for v in raw.data.vertices:v.co=Vector((v.co.x*scale,v.co.y*scale,(v.co.z-lo)*scale))
def make(name,color,rough,metal):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;return m
mats=[make('Pistol_charcoal_metal',(.018,.020,.023),.65,.30),make('Pistol_brown_grip',(.29,.145,.075),.72,0),make('Pistol_dark_muzzle',(.002,.002,.002),.88,0)];me.materials.clear()
for m in mats:
 me.materials.append(m);next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Specular IOR Level'].default_value=.15
bm=bmesh.new();bm.from_mesh(me);remaining=set(bm.verts)
while remaining:
 part={remaining.pop()};stack=list(part)
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);part.add(w);stack.append(w)
 fs={f for v in part for f in v.link_faces};maxz=max(v.co.z for v in part)/scale;miny=min(v.co.y for v in part)/scale;maxy=max(v.co.y for v in part)/scale
 idx=1 if maxz<.53 and (miny>.080 or maxy<-.080) else 0
 for f in fs:
  f.material_index=2 if idx==0 and f.calc_center_median().x/scale<-.493 else idx;f.smooth=True
for e in bm.edges:
 if len(e.link_faces)==2:e.smooth=e.calc_face_angle()<math.radians(55)
bm.to_mesh(me);bm.free();mod=obj.modifiers.new('Soft_edges_and_stable_panel_normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=50;bpy.ops.object.modifier_apply(modifier=mod.name)
me.update();bpy.context.view_layer.update()
# Bake clean material colours into one atlas; no source grain is retained.
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
atlas=bpy.data.images.new('PISTOL_basecolor_v01',width=1024,height=1024,alpha=False)
for m in mats:
 n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=atlas;m.node_tree.nodes.active=n
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=12
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'});atlas.filepath_raw=str(ROOT/'Textures/PISTOL_basecolor_v01.png');atlas.file_format='PNG';atlas.save();atlas.pack()
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
report={'source_triangles':source_tri,'source_nonmanifold_edges':before,'source_closed_triangles':closed_tri,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'mesh_islands':islands,'signed_volume_m3':bm.calc_volume(signed=True),'finite_vertices':all(math.isfinite(c) for v in coords for c in v),'uv_layers':len(me.uv_layers),'dimensions_m':dims,'budget':[400,800],'origin':'bottom centre of whole pistol','front_axis':'-Y','texture':'1024px locally baked charcoal/brown atlas, packed','shading':'smooth with sharp transitions and weighted normals','local_polish':'cap source open part ends, local reduction, clean grip/metal colours and UV; original shell and through-open trigger guard retained','paid_extras':False}
# Check the empty space inside the guard from the two wide sides.
from mathutils.bvhtree import BVHTree
bvh=BVHTree.FromBMesh(bm);rays=[]
for x in (-.17,-.15,-.13):
 for z in (.38,.41,.44):
  hit=bvh.ray_cast(Vector((x*scale,-1,z*scale)),Vector((0,1,0)),2)[0];rays.append({'source_x':x,'source_z':z,'clear':hit is None})
report['trigger_guard_clear_rays']=rays;report['trigger_guard_open']=all(r['clear'] for r in rays)
remaining=set(bm.verts);eulers=[]
while remaining:
 part={remaining.pop()};stack=list(part)
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);part.add(w);stack.append(w)
 es={e for v in part for e in v.link_edges};fs={f for v in part for f in v.link_faces};eulers.append(len(part)-len(es)+len(fs))
report['component_euler_characteristics']=eulers
bm.free();report['pass']=400<=report['final_triangles']<=800 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0 and report['signed_volume_m3']>0 and report['finite_vertices'] and abs(dims[0]-.19)<1e-5 and report['trigger_guard_open'] and 0 in eulers
(ROOT/'Validation/mesh_v01.json').write_text(json.dumps(report,indent=2));print('PISTOL_MESH',json.dumps(report));assert report['pass'],report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'PISTOL_ASTRA_001_v01.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
target=Vector((0,0,(hi-lo)*scale/2));scene.world=bpy.data.worlds.new('Preview_world');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.16,.18,.21,1);bg.inputs[1].default_value=.7
for name,loc,power,size in [('Key',(-.22,-.34,.35),1.25,.24),('Fill',(.28,-.10,.20),.45,.20),('Rim',(.07,.35,.3),1.125,.23)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=size;o=bpy.data.objects.new(name,ld);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera');cam=bpy.data.objects.new('Preview_camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=.225
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.cycles.samples=24;scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
views={'01_front':(0,-4,target.z),'02_back':(0,4,target.z),'03_left':(-4,0,target.z),'04_right':(4,0,target.z),'05_top':(0,0,4),'06_bottom':(0,0,-4),'07_hero':(-.8,-2,.65)}
for name,loc in views.items():
 cam.location=loc;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Previews'/f'{name}_v01.png');bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=.3;area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT));print('PISTOL_FINAL',json.dumps(report))
