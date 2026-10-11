import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001')
OUT=ROOT/'SURGLAMP_ASTRA_001_v01.blend';assert not OUT.exists(),'Preserve numbered deliverables'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\surglamp_tripo_base.fbx')
src=next(o for o in bpy.context.scene.objects if o.type=='MESH');bpy.context.view_layer.objects.active=src
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
src.data.calc_loop_triangles();source_tri=len(src.data.loop_triangles)
ref=bpy.data.collections.new('REFERENCE_Tripo_source_not_exported');bpy.context.scene.collection.children.link(ref)
for c in list(src.users_collection):c.objects.unlink(src)
ref.objects.link(src);src.name='Tripo_original_reference';ref.hide_viewport=True;ref.hide_render=True
bm=bmesh.new();bm.from_mesh(src.data);source_nonmanifold=sum(not e.is_manifold for e in bm.edges)
remaining=set(bm.verts);parts=[]
while remaining:
 vs={remaining.pop()};stack=list(vs)
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);vs.add(w);stack.append(w)
 parts.append(vs)
parts.sort(key=len,reverse=True);main_vs,head_vs=parts[:2]
shaft_fs={f for v in main_vs for f in v.link_faces if .2<f.calc_center_median().z<.75}
shaft_vs={v for f in shaft_fs for v in f.verts};lo=min(v.co.z for v in shaft_vs);hi=max(v.co.z for v in shaft_vs);mid=(lo+hi)/2
bottom=[v for v in shaft_vs if v.co.z<mid];top=[v for v in shaft_vs if v.co.z>=mid]
bottom_xy=Vector((sum(v.co.x for v in bottom)/len(bottom),sum(v.co.y for v in bottom)/len(bottom),0))
top_xy=Vector((sum(v.co.x for v in top)/len(top),sum(v.co.y for v in top)/len(top),0))
S=1.7/.99951171875
def corrected(co):
 t=max(0,min(1,(co.z-lo)/(hi-lo)));return (co-bottom_xy.lerp(top_xy,t))*S
def make(name,color,rough=.65,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
 p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;p.inputs['Specular IOR Level'].default_value=.25;return m
white=make('Lamp_clean_white',(.76,.79,.80));metal=make('Lamp_stem_metal',(.40,.46,.50),.35,.6);black=make('Lamp_black_casters',(.016,.019,.022),.77)
asset=bpy.data.collections.new('SURGLAMP_Final');bpy.context.scene.collection.children.link(asset);objects=[]
def part_obj(name,verts,faces,mat):
 me=bpy.data.meshes.new(name+'_mesh');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);asset.objects.link(o);me.materials.append(mat);objects.append(o);return o
def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def extracted(name,vs,target):
 vertices=list(vs);ids={v:i for i,v in enumerate(vertices)};fs={f for v in vs for f in v.link_faces}
 o=part_obj(name,[corrected(v.co) for v in vertices],[[ids[v] for v in f.verts] for f in fs],white)
 b=bmesh.new();b.from_mesh(o.data);bmesh.ops.remove_doubles(b,verts=list(b.verts),dist=1e-7)
 bmesh.ops.holes_fill(b,edges=[e for e in b.edges if e.is_boundary],sides=0);bmesh.ops.recalc_face_normals(b,faces=list(b.faces));b.to_mesh(o.data);b.free()
 activate(o);o.data.calc_loop_triangles();n=len(o.data.loop_triangles)
 d=o.modifiers.new('Local_polygon_reduction','DECIMATE');d.ratio=target/n;bpy.ops.object.modifier_apply(modifier=d.name);return o
main=extracted('Lamp_source_stand_and_gooseneck',main_vs,360)
head=extracted('Lamp_source_head',head_vs,280)
main.data.materials.append(metal)
for p in main.data.polygons:
 if (lo+.015)*S<p.center.z<(hi-.008)*S:p.material_index=1
bm.free()
# Use the measured front surface of the source head for a clean cream/blue lens atlas.
nb=Vector((0,-.867562,-.497329));nb.normalize();tv=Vector((0,nb.z,-nb.y));xv=Vector((1,0,0))
cap=[v.co.copy() for p in head.data.polygons if p.normal.dot(nb)>.90 for v in (head.data.vertices[i] for i in p.vertices)]
cx=(min(v.x for v in cap)+max(v.x for v in cap))/2
ct=(min(v.dot(tv) for v in cap)+max(v.dot(tv) for v in cap))/2
cp=sum(v.dot(nb) for v in cap)/len(cap);centre=xv*cx+tv*ct+nb*cp
rx=(max(v.x for v in cap)-min(v.x for v in cap))/2;rt=(max(v.dot(tv) for v in cap)-min(v.dot(tv) for v in cap))/2
lens=make('Lamp_front_diffuser_and_blue_ring',(.80,.75,.58),.68);nodes=lens.node_tree.nodes;links=lens.node_tree.links
geom=nodes.new('ShaderNodeNewGeometry');sub=nodes.new('ShaderNodeVectorMath');sub.operation='SUBTRACT';sub.inputs[1].default_value=centre;links.new(geom.outputs['Position'],sub.inputs[0])
def scalar_projection(axis,radius):
 dot=nodes.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';dot.inputs[1].default_value=axis;links.new(sub.outputs[0],dot.inputs[0])
 div=nodes.new('ShaderNodeMath');div.operation='DIVIDE';div.inputs[1].default_value=radius;links.new(dot.outputs['Value'],div.inputs[0])
 sq=nodes.new('ShaderNodeMath');sq.operation='MULTIPLY';links.new(div.outputs[0],sq.inputs[0]);links.new(div.outputs[0],sq.inputs[1]);return sq
sx=scalar_projection(xv,rx);st=scalar_projection(tv,rt);add=nodes.new('ShaderNodeMath');add.operation='ADD';links.new(sx.outputs[0],add.inputs[0]);links.new(st.outputs[0],add.inputs[1])
threshold=nodes.new('ShaderNodeMath');threshold.operation='GREATER_THAN';threshold.inputs[1].default_value=.84*.84;links.new(add.outputs[0],threshold.inputs[0])
mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[1].default_value=(.80,.75,.58,1);mix.inputs[2].default_value=(.26,.39,.60,1);links.new(threshold.outputs[0],mix.inputs[0]);links.new(mix.outputs[0],next(n for n in nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'])
head.data.materials.append(lens)
for p in head.data.polygons:
 if p.normal.dot(nb)>.70 and (p.center-centre).dot(nb)>-.025*S:p.material_index=1
# One measured foot/caster module, repeated on the four source-matching diagonal directions.
R_IN=.035;R_END=.246;R_WHEEL=.236;Z_LEG_MIN=.060;Z_LEG_MAX=.095;TIRE_R=.026;TIRE_W=.022;POST_MIN=.040;POST_MAX=.068
profile=[(-.022+.006,-.0175),(.022-.006,-.0175),(.022,-.0175+.006),(.022,.0175-.006),(.022-.006,.0175),(-.022+.006,.0175),(-.022,.0175-.006),(-.022,-.0175+.006)]
interfaces=[];legs=[];posts=[];tires=[]
for i,ang in enumerate([45,135,225,315]):
 u=Vector((math.cos(math.radians(ang)),math.sin(math.radians(ang)),0));v=Vector((-u.y,u.x,0));foot=u*R_WHEEL
 verts=[]
 for r,k in [(R_IN,.95),(R_END-.006,1),(R_END,.75)]:
  for q,z in profile:verts.append((u*r+v*(q*k)+Vector((0,0,(Z_LEG_MIN+Z_LEG_MAX)/2+z*k)))*S)
 faces=[]
 for j in range(2):
  for k in range(8):faces.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
 faces.extend([tuple(reversed(range(8))),tuple(range(16,24))]);leg=part_obj(f'Foot_{i+1}',verts,faces,white);legs.append(leg)
 verts=[]
 for offset,radius in [(-TIRE_W/2,TIRE_R*.82),(-TIRE_W/2+.004,TIRE_R),(TIRE_W/2-.004,TIRE_R),(TIRE_W/2,TIRE_R*.82)]:
  for k in range(8):
   a=k*math.tau/8;verts.append((foot+v*offset+u*(radius*math.cos(a))+Vector((0,0,TIRE_R+radius*math.sin(a))))*S)
 faces=[]
 for j in range(3):
  for k in range(8):faces.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
 faces.extend([tuple(reversed(range(8))),tuple(range(24,32))]);tire=part_obj(f'Caster_tire_{i+1}',verts,faces,black);tires.append(tire)
 verts=[]
 for z in [POST_MIN,POST_MAX]:
  for k in range(8):a=k*math.tau/8;verts.append((foot+Vector((math.cos(a)*.009,math.sin(a)*.009,z)))*S)
 faces=[(k,(k+1)%8,8+(k+1)%8,8+k) for k in range(8)]+[tuple(reversed(range(8))),tuple(range(8,16))]
 post=part_obj(f'Caster_mount_{i+1}',verts,faces,black);posts.append(post)
 interfaces.append({'foot':i+1,'direction_degrees':ang,'root_point_m':list((u*R_IN+Vector((0,0,(Z_LEG_MIN+Z_LEG_MAX)/2)))*S),'leg_mount_overlap_m':(POST_MAX-Z_LEG_MIN)*S,'mount_tire_overlap_m':(2*TIRE_R-POST_MIN)*S,'tire_ground_gap_m':0.0})
# Fix winding, smooth the curved pieces, and retain sharp surface transitions.
for o in objects:
 b=bmesh.new();b.from_mesh(o.data);bmesh.ops.recalc_face_normals(b,faces=list(b.faces))
 for f in b.faces:f.smooth=True
 for e in b.edges:
  if len(e.link_faces)==2:e.smooth=e.calc_face_angle()<math.radians(55)
 b.to_mesh(o.data);b.free();o.data.update()
def bvh_for(o):
 b=bmesh.new();b.from_mesh(o.data);return b,BVHTree.FromBMesh(b)
def inside(bvh,p):
 origin=p.copy();direction=Vector((.173,.397,.901)).normalized();hits=0
 for _ in range(60):
  hit=bvh.ray_cast(origin,direction,10)[0]
  if hit is None:break
  hits+=1;origin=hit+direction*1e-5
 return hits%2==1
mb,mv=bvh_for(main);hb,hv=bvh_for(head)
for row in interfaces:row['foot_root_inside_hub']=inside(mv,Vector(row['root_point_m']))
neck_points=[p.center.copy() for p in main.data.polygons if p.center.z>.84*S and p.center.y<-.12*S]
inside_count=sum(inside(hv,p) for p in neck_points);nearest=min(hv.find_nearest(p)[3] for p in neck_points)
report_interfaces={'caster_interfaces':interfaces,'head_neck_inside_samples':inside_count,'head_neck_surface_distance_m':nearest,'shaft_bottom_source_xy':list(bottom_xy),'shaft_top_source_xy':list(top_xy),'shaft_corrected_axis':'vertical Z','source_preserved':'head and continuous hub/stem/gooseneck; floating asymmetric feet/casters rebuilt from a seated module','pass':all(r['foot_root_inside_hub'] and r['leg_mount_overlap_m']>0 and r['mount_tire_overlap_m']>0 for r in interfaces) and inside_count>0}
mb.free();hb.free();(ROOT/'Validation/interfaces_v01.json').write_text(json.dumps(report_interfaces,indent=2),encoding='utf-8');print('INTERFACES',json.dumps(report_interfaces));assert report_interfaces['pass']
activate(main)
for o in objects:o.select_set(True)
bpy.ops.object.join();obj=bpy.context.object;obj.name='Prop_SurgicalLamp';me=obj.data
mod=obj.modifiers.new('Weighted_normals_for_curved_reference_surfaces','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=50;bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
atlas=bpy.data.images.new('SURGLAMP_basecolor_v01',width=1024,height=1024,alpha=False)
for m in me.materials:n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=atlas;m.node_tree.nodes.active=n
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=12
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'});atlas.filepath_raw=str(ROOT/'Textures/SURGLAMP_basecolor_v01.png');atlas.file_format='PNG';atlas.save();atlas.pack()
for m in me.materials:
 t=next(n for n in m.node_tree.nodes if n.type=='TEX_IMAGE');p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');m.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color'])
me.calc_loop_triangles();b=bmesh.new();b.from_mesh(me);remaining=set(b.verts);islands=0
while remaining:
 islands+=1;stack=[remaining.pop()]
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);stack.append(w)
coords=[v.co.copy() for v in me.vertices];dims=[max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3)]
report={'source_triangles':source_tri,'source_nonmanifold_edges':source_nonmanifold,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'mesh_islands':islands,'nonmanifold_edges':sum(not e.is_manifold for e in b.edges),'zero_area_faces':sum(f.calc_area()<1e-12 for f in b.faces),'signed_volume_m3':b.calc_volume(signed=True),'finite_vertices':all(math.isfinite(c) for v in coords for c in v),'uv_layers':len(me.uv_layers),'dimensions_m':dims,'budget':[600,1200],'caster_count':4,'texture':'1024px clean locally baked white/blue/cream/metal/black atlas, packed','origin':'ground at hub centre','front_axis':'-Y','source_parts_retained':'head and continuous stand/gooseneck/hub','local_repair':'straightened source stem, closed source boundaries, four identical feet and seated caster modules, source-fitted local reduction','interfaces_pass':report_interfaces['pass'],'paid_extras':False}
b.free();report['pass']=600<=report['final_triangles']<=1200 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0 and report['signed_volume_m3']>0 and report['finite_vertices'] and report['interfaces_pass'] and abs(dims[2]-1.7)<1e-4
(ROOT/'Validation/mesh_v01.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('SURGLAMP_MESH',json.dumps(report));assert report['pass']
bpy.ops.export_scene.fbx(filepath=str(ROOT/'SURGLAMP_ASTRA_001_v01.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
target=Vector((0,-.05,.85));scene.world=bpy.data.worlds.new('Preview_world');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.16,.18,.21,1);bg.inputs[1].default_value=.7
for name,loc,power,size in [('Key',(-2,-3,3),95,2),('Fill',(2,-1,2),40,2),('Rim',(1,3,2.8),70,1.8)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera');cam=bpy.data.objects.new('Preview_camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=2.02
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.cycles.samples=24;scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
views={'01_front':(0,-4,.85),'02_back':(0,4,.85),'03_left':(4,-.05,.85),'04_right':(-4,-.05,.85),'05_top':(0,-.05,4),'06_bottom':(0,-.05,-4),'07_hero':(2,-3,1.85)}
for name,loc in views.items():
 cam.location=loc;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Previews'/f'{name}_v01.png');bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=2.6;area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT));print('SURGLAMP_FINAL',json.dumps(report))
