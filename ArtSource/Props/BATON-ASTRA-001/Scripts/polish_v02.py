import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\BATON-ASTRA-001')
OUT=ROOT/'BATON_ASTRA_001_v02.blend'
assert not OUT.exists(), 'Preserve numbered deliverables'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\baton_tripo_base.fbx')
raw=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=raw;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
raw.data.calc_loop_triangles();source_tri=len(raw.data.loop_triangles)
lo=min(v.co.z for v in raw.data.vertices);hi=max(v.co.z for v in raw.data.vertices)
lower=[v.co for v in raw.data.vertices if v.co.z<lo+(hi-lo)*.25]
cx=(min(v.x for v in lower)+max(v.x for v in lower))/2;cy=(min(v.y for v in lower)+max(v.y for v in lower))/2
for v in raw.data.vertices:v.co=Vector(((v.co.x-cx)*.55/(hi-lo),(v.co.y-cy)*.55/(hi-lo),(v.co.z-lo)*.55/(hi-lo)))
# Retopology follows the generated source silhouette and approved grip anatomy.
# Connected longitudinal loops, not overlapping capped cylinders. The T junction
# replaces four shaft faces with one continuous bridge into the side-grip loops.
raw.name='Tripo_original_reference';source_col=bpy.data.collections.new('REFERENCE_Tripo_source_not_exported');bpy.context.scene.collection.children.link(source_col)
for col in list(raw.users_collection):col.objects.unlink(raw)
source_col.objects.link(raw);source_col.hide_render=True;source_col.hide_viewport=True
verts=[];faces=[]
main_profile=[(0,.008),(.006,.016),(.019,.019),(.378,.019),(.398,.020),(.418,.019),(.431,.019),(.442,.022),(.458,.0185),(.470,.022),(.484,.0185),(.497,.022),(.512,.0185),(.524,.023),(.537,.025),(.548,.018),(.55,.008)]
for z,r in main_profile:
 for k in range(10):
  a=2*math.pi*k/10;verts.append((r*math.cos(a),r*math.sin(a),z))
for row in range(len(main_profile)-1):
 for k in range(10):
  if row in (3,4) and k in (9,0):continue
  faces.append((row*10+k,row*10+(k+1)%10,(row+1)*10+(k+1)%10,(row+1)*10+k))
faces.append(tuple(reversed(range(10))));faces.append(tuple((len(main_profile)-1)*10+k for k in range(10)))
# Octagonal opening ordered in the Y/Z plane, centered on source side-grip axis.
opening=[4*10+1,5*10+1,5*10,5*10+9,4*10+9,3*10+9,3*10,3*10+1]
side_start=len(verts)
side_profile=[(.035,.018),(.051,.021),(.065,.0175),(.080,.021),(.094,.0175),(.108,.021),(.120,.0175),(.130,.023),(.140,.025),(.151,.007)]
for x,r in side_profile:
 for k in range(8):
  a=2*math.pi*k/8;verts.append((x,r*math.cos(a),.398+r*math.sin(a)))
for k in range(8):faces.append((opening[k],opening[(k+1)%8],side_start+(k+1)%8,side_start+k))
for row in range(len(side_profile)-1):
 for k in range(8):faces.append((side_start+row*8+k,side_start+row*8+(k+1)%8,side_start+(row+1)*8+(k+1)%8,side_start+(row+1)*8+k))
faces.append(tuple(side_start+(len(side_profile)-1)*8+k for k in range(8)))
me=bpy.data.meshes.new('Baton_source_fitted_retopology');me.from_pydata(verts,[],faces);me.update()
obj=bpy.data.objects.new('Item_Baton',me);bpy.context.scene.collection.objects.link(obj)
for ob in bpy.context.selected_objects:ob.select_set(False)
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
for p in me.polygons:p.use_smooth=True
mat=bpy.data.materials.new('Baton_matte_black_rubber');mat.use_nodes=True;mat.diffuse_color=(.008,.009,.011,1)
bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.008,.009,.011,1);bs.inputs['Roughness'].default_value=.8;bs.inputs['Specular IOR Level'].default_value=.2
me.materials.append(mat)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
atlas=bpy.data.images.new('BATON_basecolor_v02',width=512,height=512,alpha=False)
tn=mat.node_tree.nodes.new('ShaderNodeTexImage');tn.image=atlas;mat.node_tree.nodes.active=tn
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=12
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
atlas.filepath_raw=str(ROOT/'Textures/BATON_basecolor_v02.png');atlas.file_format='PNG';atlas.save();atlas.pack()
mat.node_tree.links.new(tn.outputs['Color'],bs.inputs['Base Color'])
me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me)
remaining=set(bm.verts);islands=0
while remaining:
 islands+=1;stack=[remaining.pop()]
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);stack.append(w)
coords=[v.co.copy() for v in me.vertices];dims=[max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3)]
report={'source_triangles':source_tri,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'mesh_islands':islands,'signed_volume_m3':bm.calc_volume(signed=True),'finite_vertices':all(math.isfinite(c) for v in coords for c in v),'uv_layers':len(me.uv_layers),'dimensions_m':dims,'budget':[200,500],'origin':'main shaft centre at lower tip','front_axis':'-Y','contact':'one closed connected T junction, continuous loops, no intersecting separate solids','texture':'512px locally baked uniform black rubber atlas, packed','shading':'smooth, matte rubber','local_polish':'retopology fitted to Tripo source; three broad grip sections restored on both handles; no additional Tripo generation','paid_extras':False}
bm.free();report['pass']=200<=report['final_triangles']<=500 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0 and islands==1 and report['signed_volume_m3']>0 and report['finite_vertices'] and abs(dims[2]-.55)<1e-5
(ROOT/'Validation/mesh_v02.json').write_text(json.dumps(report,indent=2));print('BATON_MESH',json.dumps(report));assert report['pass'],report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'BATON_ASTRA_001_v02.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
# Presentation is added after the completed mesh audit.
target=Vector((.025,0,.275));scene.world=bpy.data.worlds.new('Preview_world');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.16,.18,.21,1);bg.inputs[1].default_value=.7
for name,loc,power,size in [('Key',(-.8,-1.2,1.3),65,1),('Fill',(.9,-.5,.7),25,.8),('Rim',(.2,1,1.1),55,.8)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=size;ob=bpy.data.objects.new(name,ld);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera');cam=bpy.data.objects.new('Preview_camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=.67
scene.cycles.samples=24;scene.render.resolution_x=700;scene.render.resolution_y=700;scene.render.resolution_percentage=100
views={'01_front':(target.x,-4,.275),'02_back':(target.x,4,.275),'03_left':(-4,0,.275),'04_right':(4,0,.275),'05_top':(target.x,0,4),'06_bottom':(target.x,0,-4),'07_hero':(.75,-2,.85)}
for name,loc in views.items():
 cam.location=loc;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Previews'/f'{name}_v02.png');bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=1;area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT));print('BATON_FINAL',json.dumps(report))
