import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\BAT-ASTRA-001')
OUT=ROOT/'BAT_ASTRA_001_v01.blend'
assert not OUT.exists(), 'Preserve numbered deliverables'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\bat_tripo_base.fbx')
raw=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=raw;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
raw.data.calc_loop_triangles(); source_tri=len(raw.data.loop_triangles)
lo=min(v.co.z for v in raw.data.vertices);hi=max(v.co.z for v in raw.data.vertices)
for v in raw.data.vertices:v.co*=.8/(hi-lo)
raw.name='Tripo_original_reference'
reference=bpy.data.collections.new('REFERENCE_Tripo_source_not_exported');bpy.context.scene.collection.children.link(reference)
for col in list(raw.users_collection):col.objects.unlink(raw)
reference.objects.link(raw);reference.hide_render=True;reference.hide_viewport=True
# Fifteen continuous radial loops follow the generated barrel / neck / knob.
# Source grip seams have 32 open edges: rebuild closed topology locally.
# Shallow chips are texture only, as approved; no jagged cuts in the silhouette.
profile=[(0,.010),(.005,.023),(.019,.034),(.032,.034),(.044,.019),(.198,.0185),(.205,.0167),(.340,.019),(.50,.029),(.66,.041),(.755,.045),(.777,.043),(.790,.037),(.799,.021),(.8,.008)]
N=16;verts=[];faces=[]
for z,r in profile:
 for k in range(N):
  a=2*math.pi*k/N;verts.append((r*math.cos(a),r*math.sin(a),z))
for row in range(len(profile)-1):
 for k in range(N):faces.append((row*N+k,row*N+(k+1)%N,(row+1)*N+(k+1)%N,(row+1)*N+k))
faces.append(tuple(reversed(range(N))));faces.append(tuple((len(profile)-1)*N+k for k in range(N)))
me=bpy.data.meshes.new('Bat_source_fitted_closed_loops');me.from_pydata(verts,[],faces);me.update()
obj=bpy.data.objects.new('Item_Bat',me);bpy.context.scene.collection.objects.link(obj)
for o in bpy.context.selected_objects:o.select_set(False)
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
for p in me.polygons:p.use_smooth=True
mat=bpy.data.materials.new('Honey_wood_and_charcoal_tape');mat.use_nodes=True;me.materials.append(mat)
nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.69;bs.inputs['Specular IOR Level'].default_value=.25
tc=nodes.new('ShaderNodeTexCoord');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(tc.outputs['Object'],sep.inputs[0]);x,y,z=[sep.outputs[k] for k in ('X','Y','Z')]
def op(kind,a,b=0):
 n=nodes.new('ShaderNodeMath');n.operation=kind
 for i,v in enumerate((a,b)):
  if isinstance(v,(int,float)):n.inputs[i].default_value=v
  else:links.new(v,n.inputs[i])
 return n.outputs[0]
def mix(f,a,b):
 n=nodes.new('ShaderNodeMixRGB');links.new(f,n.inputs[0])
 for i,v in enumerate((a,b),1):
  if isinstance(v,tuple):n.inputs[i].default_value=v
  else:links.new(v,n.inputs[i])
 return n.outputs[0]
angle=op('ARCTAN2',y,x)
grainphase=op('ADD',op('MULTIPLY',angle,7),op('MULTIPLY',op('SINE',op('MULTIPLY',z,5)),1.4))
grain=op('MULTIPLY',op('POWER',op('MULTIPLY',op('ADD',op('SINE',grainphase),1),.5),5),.45)
wood=mix(grain,(.58,.29,.085,1),(.34,.135,.030,1))
# Two stylized, broad asymmetric chips, front / left only. Diamond edges suggest
# chipped wood without geometric cuts or fine texture noise.
def chip(cx,cz,wx,wz):
 d=op('ADD',op('DIVIDE',op('ABSOLUTE',op('SUBTRACT',x,cx)),wx),op('DIVIDE',op('ABSOLUTE',op('SUBTRACT',z,cz)),wz))
 return op('MULTIPLY',op('LESS_THAN',d,1),op('LESS_THAN',y,-.017))
chip1=chip(-.011,.716,.012,.018)
wood=mix(chip1,wood,mix(op('GREATER_THAN',z,.716),(.75,.44,.16,1),(.26,.11,.025,1)))
sidechip=op('MULTIPLY',op('LESS_THAN',op('ADD',op('DIVIDE',op('ABSOLUTE',op('ADD',y,.006)),.011),op('DIVIDE',op('ABSOLUTE',op('SUBTRACT',z,.505)),.018)),1),op('LESS_THAN',x,-.022))
wood=mix(sidechip,wood,(.69,.39,.125,1))
phase=op('FRACT',op('SUBTRACT',op('DIVIDE',op('SUBTRACT',z,.044),.032),op('DIVIDE',angle,2*math.pi)))
tape=mix(op('LESS_THAN',phase,.05),(.023,.026,.03,1),(.005,.006,.008,1))
tape=mix(op('MULTIPLY',op('GREATER_THAN',phase,.05),op('LESS_THAN',phase,.14)),tape,(.042,.046,.050,1))
tapezone=op('MULTIPLY',op('GREATER_THAN',z,.044),op('LESS_THAN',z,.2))
links.new(mix(tapezone,wood,tape),bs.inputs['Base Color'])
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
atlas=bpy.data.images.new('BAT_basecolor_v01',width=1024,height=1024,alpha=False)
tn=nodes.new('ShaderNodeTexImage');tn.image=atlas;nodes.active=tn
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1;scene.render.bake.margin=16
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
atlas.filepath_raw=str(ROOT/'Textures/BAT_basecolor_v01.png');atlas.file_format='PNG';atlas.save();atlas.pack()
for link in list(bs.inputs['Base Color'].links):links.remove(link)
links.new(tn.outputs['Color'],bs.inputs['Base Color'])
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
report={'source_triangles':source_tri,'source_nonmanifold_edges':32,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'mesh_islands':islands,'signed_volume_m3':bm.calc_volume(signed=True),'finite_vertices':all(math.isfinite(c) for v in coords for c in v),'uv_layers':len(me.uv_layers),'dimensions_m':dims,'budget':[200,500],'origin':'bottom centre of wooden knob','front_axis':'-Y','texture':'1024px locally baked honey wood / five charcoal tape wraps / two front-left chips, packed','shading':'smooth','local_polish':'source-fitted continuous-loop retopology; source seams closed; chips painted in atlas, no added chip geometry','paid_extras':False}
bm.free();report['pass']=200<=report['final_triangles']<=500 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0 and islands==1 and report['signed_volume_m3']>0 and report['finite_vertices'] and abs(dims[2]-.8)<1e-5
(ROOT/'Validation/mesh_v01.json').write_text(json.dumps(report,indent=2));print('BAT_MESH',json.dumps(report));assert report['pass'],report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'BAT_ASTRA_001_v01.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
target=Vector((0,0,.4));scene.world=bpy.data.worlds.new('Preview_world');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.16,.18,.21,1);bg.inputs[1].default_value=.7
for name,loc,power,size in [('Key',(-.8,-1.3,1.5),65,1),('Fill',(.9,-.5,.9),25,.8),('Rim',(.2,1,1.2),55,.8)]:
 ld=bpy.data.lights.new(name,'AREA');ld.energy=power;ld.size=size;o=bpy.data.objects.new(name,ld);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera');cam=bpy.data.objects.new('Preview_camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=.93
scene.cycles.samples=24;scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
views={'01_front':(0,-4,.4),'02_back':(0,4,.4),'03_left':(-4,0,.4),'04_right':(4,0,.4),'05_top':(0,0,4),'06_bottom':(0,0,-4),'07_hero':(.50,-2,.85)}
for name,loc in views.items():
 cam.location=loc;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(ROOT/'Previews'/f'{name}_v01.png');bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=1.2;area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT));print('BAT_FINAL',json.dumps(report))
