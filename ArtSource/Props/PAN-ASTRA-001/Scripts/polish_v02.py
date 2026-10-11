import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\PAN-ASTRA-001');OUT=ROOT/'PAN_ASTRA_001_v02.blend'
assert not OUT.exists(), 'Preserve numbered revisions'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\pan_tripo_base.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');obj.name='Item_Pan'
bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
me=obj.data;me.calc_loop_triangles();source_tri=len(me.loop_triangles)
raw=obj.copy();raw.data=me.copy();raw.name='Tripo_original_reference';reference=bpy.data.collections.new('REFERENCE_Tripo_source_not_exported');bpy.context.scene.collection.children.link(reference);reference.objects.link(raw);reference.hide_render=True;reference.hide_viewport=True
# Anatomy measured from source and approved Rev02: bowl/height=.631,
# grip/height=.37; one continuous casting with one through hole at grip end.
# Tripo flattened both floor surfaces into radial fans. Replace those fans
# with continuous local rings centred on the approved front-left dent.
bm=bmesh.new();bm.from_mesh(me)
poles=sorted([v for v in bm.verts if abs(v.co.x)<.01 and .27<v.co.z<.33 and len(v.link_edges)>12],key=lambda v:v.co.y)
assert len(poles)==2, [(list(v.co),len(v.link_edges)) for v in poles]
dent_source=(-.08,.235);created=[];floor_reports=[]
for pole in poles:
 neighbors=[e.other_vert(pole) for e in pole.link_edges];cx,cz=dent_source
 neighbors.sort(key=lambda v:math.atan2(v.co.z-cz,v.co.x-cx));n=len(neighbors)
 coords=np.array([[v.co.x,v.co.z,1.] for v in neighbors]);ys=np.array([v.co.y for v in neighbors]);a,b,c=np.linalg.lstsq(coords,ys,rcond=None)[0]
 floor_reports.append({'old_pole':list(pole.co),'perimeter_vertices':n,'baseline_plane_y_ax_bz_c':[float(a),float(b),float(c)]})
 bmesh.ops.delete(bm,geom=list(pole.link_faces),context='FACES_ONLY');bmesh.ops.delete(bm,geom=[pole],context='VERTS')
 prev=neighbors
 start=math.atan2(neighbors[0].co.z-cz,neighbors[0].co.x-cx)
 prev_angles=[math.atan2(v.co.z-cz,v.co.x-cx)-start for v in neighbors]
 for radius,depth in [(.085,0),(.045,.014)]:
  loop=[];angles=[k*2*math.pi/16 for k in range(16)]
  for ang in angles:
   x=cx+radius*math.cos(ang+start);z=cz+radius*math.sin(ang+start)
   nv=bm.verts.new((x,a*x+b*z+c+depth,z));loop.append(nv);created.append(nv)
  i=j=0
  while i<len(prev) or j<len(loop):
   next_i=prev_angles[i+1] if i+1<len(prev) else 2*math.pi
   next_j=angles[j+1] if j+1<len(loop) else 2*math.pi
   if i<len(prev) and (j==len(loop) or next_i<=next_j):
    bm.faces.new((prev[i%len(prev)],prev[(i+1)%len(prev)],loop[j%len(loop)]));i+=1
   else:
    bm.faces.new((prev[i%len(prev)],loop[(j+1)%len(loop)],loop[j%len(loop)]));j+=1
  prev=loop;prev_angles=angles
 centre=bm.verts.new((cx,a*cx+b*cz+c+.027,cz));created.append(centre)
 for k in range(len(prev)):bm.faces.new((prev[k],prev[(k+1)%len(prev)],centre))
bm.verts.index_update();dent_indices=[v.index for v in created]
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
me.calc_loop_triangles();restored_tri=len(me.loop_triangles)
protect=obj.vertex_groups.new(name='Decimate_outside_local_dent');protect.add(list(range(len(me.vertices))),1,'REPLACE');protect.add(dent_indices,0,'REPLACE')
mod=obj.modifiers.new('Local_triangle_budget','DECIMATE');mod.vertex_group=protect.name;mod.vertex_group_factor=1
low=0.;high=1.
for trial in range(18):
 mod.ratio=(low+high)/2;bpy.context.view_layer.update();ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());em=ev.to_mesh();em.calc_loop_triangles();count=len(em.loop_triangles);ev.to_mesh_clear()
 if count>590:high=mod.ratio
 else:low=mod.ratio
mod.ratio=low;bpy.ops.object.modifier_apply(modifier=mod.name);me=obj.data
# Normalize to 46cm overall. Flatten only excess source depth, not the dent.
lo=min(v.co.z for v in me.vertices);hi=max(v.co.z for v in me.vertices);scale=.46/(hi-lo)
for v in me.vertices:v.co=Vector((v.co.x*scale,v.co.y*scale*.8,(v.co.z-lo)*scale))
for v in raw.data.vertices:v.co=Vector((v.co.x*scale,v.co.y*scale*.8,(v.co.z-lo)*scale))
me.update();bpy.context.view_layer.update()
for p in me.polygons:p.use_smooth=True
mat=bpy.data.materials.new('Pan_clean_charcoal_cast_iron');mat.use_nodes=True;me.materials.clear();me.materials.append(mat)
bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.028,.031,.036,1);bs.inputs['Roughness'].default_value=.74;bs.inputs['Specular IOR Level'].default_value=.24;bs.inputs['Metallic'].default_value=.15
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
atlas=bpy.data.images.new('PAN_basecolor_v02',width=512,height=512,alpha=False);tn=mat.node_tree.nodes.new('ShaderNodeTexImage');tn.image=atlas;mat.node_tree.nodes.active=tn
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=12
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'});atlas.filepath_raw=str(ROOT/'Textures/PAN_basecolor_v02.png');atlas.file_format='PNG';atlas.save();atlas.pack();mat.node_tree.links.new(tn.outputs['Color'],bs.inputs['Base Color'])
me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me);remaining=set(bm.verts);islands=0
while remaining:
 islands+=1;stack=[remaining.pop()]
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);stack.append(w)
coords=[v.co.copy() for v in me.vertices];dims=[max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3)]
report={'source_triangles':source_tri,'dent_restored_before_reduction_triangles':restored_tri,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'mesh_islands':islands,'signed_volume_m3':bm.calc_volume(signed=True),'finite_vertices':all(math.isfinite(c) for v in coords for c in v),'uv_layers':len(me.uv_layers),'dimensions_m':dims,'budget':[300,600],'origin':'bottom centre of upright bowl','front_axis':'-Y','texture':'512px locally baked clean charcoal atlas, packed','shading':'smooth','local_polish':'source mesh; floor fan replacement by connected local rings, front-left dent and corresponding exterior bulge restored; local decimation outside protected dent loops; depth compressed20percent','dent_centre_m':[dent_source[0]*scale,dent_source[1]*scale],'dent_depth_m':.027*scale*.8,'floor_repairs':floor_reports,'paid_extras':False}
bm.free();report['pass']=300<=report['final_triangles']<=600 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0 and islands==1 and report['signed_volume_m3']>0 and report['finite_vertices'] and abs(dims[2]-.46)<1e-5
(ROOT/'Validation/mesh_v02.json').write_text(json.dumps(report,indent=2));print('PAN_MESH',json.dumps(report));assert report['pass'],report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'PAN_ASTRA_001_v02.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
target=Vector((0,0,.23));scene.world=bpy.data.worlds.new('Preview_world');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.16,.18,.21,1);bg.inputs[1].default_value=.7
for name,loc,power,size in [('Key',(-.65,-1,1.0),45,.8),('Fill',(.8,-.3,.6),16,.6),('Rim',(.2,1,.85),40,.7)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=size;o=bpy.data.objects.new(name,ld);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera');cam=bpy.data.objects.new('Preview_camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=.55
scene.cycles.samples=24;scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
views={'01_front':(0,-4,.23),'02_back':(0,4,.23),'03_left':(-4,0,.23),'04_right':(4,0,.23),'05_top':(0,0,4),'06_bottom':(0,0,-4),'07_hero':(.8,-2,.65)}
for name,loc in views.items():
 cam.location=loc;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Previews'/f'{name}_v02.png');bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=.9;area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT));print('PAN_FINAL',json.dumps(report))
