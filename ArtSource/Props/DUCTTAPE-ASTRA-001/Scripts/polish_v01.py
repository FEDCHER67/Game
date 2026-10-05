import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\DUCTTAPE-ASTRA-001')
OUT=ROOT/'DUCTTAPE_ASTRA_001_v01.blend'
assert not OUT.exists(), 'Preserve previous revisions'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\ducttape_tripo_base.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH'); obj.name='Item_DuctTape'
bpy.context.view_layer.objects.active=obj; obj.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
me=obj.data; me.calc_loop_triangles(); source_tri=len(me.loop_triangles)
bm=bmesh.new(); bm.from_mesh(me)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.000001)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces)); bm.to_mesh(me); bm.free()
me.calc_loop_triangles(); repaired_tri=len(me.loop_triangles)
# Anatomy measured from source: upright ring, through core and one integral curved tongue.
# Ring diameter is the height; its leftmost point defines centre, tongue extends +X.
zmin=min(v.co.z for v in me.vertices); zmax=max(v.co.z for v in me.vertices)
radius=(zmax-zmin)/2; cx=min(v.co.x for v in me.vertices)+radius; cz=(zmax+zmin)/2
mod=obj.modifiers.new('Local_triangle_budget','DECIMATE'); mod.ratio=380/repaired_tri
bpy.ops.object.modifier_apply(modifier=mod.name); me=obj.data
mat=bpy.data.materials.new('DuctTape_grey_cardboard'); mat.use_nodes=True
nodes=mat.node_tree.nodes; links=mat.node_tree.links; bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
bs.inputs['Roughness'].default_value=.74
tc=nodes.new('ShaderNodeTexCoord'); sep=nodes.new('ShaderNodeSeparateXYZ'); links.new(tc.outputs['Geometry'] if 'Geometry' in tc.outputs else tc.outputs['Object'],sep.inputs[0])
def op(kind,a,b=0):
 n=nodes.new('ShaderNodeMath'); n.operation=kind
 for i,v in enumerate((a,b)):
  if isinstance(v,(float,int)): n.inputs[i].default_value=v
  else: links.new(v,n.inputs[i])
 return n.outputs[0]
x=op('SUBTRACT',sep.outputs['X'],cx); z=op('SUBTRACT',sep.outputs['Z'],cz)
rr=op('ADD',op('MULTIPLY',x,x),op('MULTIPLY',z,z))
core=op('LESS_THAN',rr,(radius*.56)**2)
mix=nodes.new('ShaderNodeMixRGB'); links.new(core,mix.inputs[0]); mix.inputs[1].default_value=(.30,.33,.37,1); mix.inputs[2].default_value=(.55,.33,.15,1)
links.new(mix.outputs[0],bs.inputs['Base Color']); me.materials.clear(); me.materials.append(mat)
for p in me.polygons: p.use_smooth=True
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.025); bpy.ops.object.mode_set(mode='OBJECT')
im=bpy.data.images.new('DUCTTAPE_basecolor_v01',width=1024,height=1024,alpha=False)
tn=nodes.new('ShaderNodeTexImage'); tn.image=im; nodes.active=tn
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=1; scene.render.bake.margin=16
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
im.filepath_raw=str(ROOT/'Textures/DUCTTAPE_basecolor_v01.png'); im.file_format='PNG'; im.save(); im.pack()
for l in list(bs.inputs['Base Color'].links): links.remove(l)
links.new(tn.outputs['Color'],bs.inputs['Base Color'])
# Normalize to a 12cm roll diameter; keep integral tongue connected and origin on floor.
scale=.12/(zmax-zmin)
for v in me.vertices: v.co=Vector(((v.co.x-cx)*scale,v.co.y*scale,(v.co.z-zmin)*scale))
me.update(); bpy.context.view_layer.update(); me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
verts=set(bm.verts); islands=0
while verts:
 islands+=1; stack=[verts.pop()]
 while stack:
  v=stack.pop()
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in verts: verts.remove(w); stack.append(w)
report={'source_triangles':source_tri,'repaired_triangles':repaired_tri,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'mesh_islands':islands,'uv_layers':len(me.uv_layers),'dimensions_m':list(obj.dimensions),'roll_diameter_m':.12,'front_axis':'-Y','origin':'roll centre at floor','budget':[200,400],'paid_extras':False,'contact':'tongue and roll are one connected source mesh, no separate floating pieces','materials':'local flat grey and beige 1024px baked atlas'}
bm.free(); report['pass']=200<=report['final_triangles']<=400 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0 and islands==1
(ROOT/'Validation/mesh_v01.json').write_text(json.dumps(report,indent=2)); print('TAPE_MESH',json.dumps(report)); assert report['pass'], report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'DUCTTAPE_ASTRA_001_v01.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
scene.cycles.samples=20; scene.render.resolution_x=800; scene.render.resolution_y=800; scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Preview_world'); scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs[0].default_value=(.12,.14,.17,1); bg.inputs[1].default_value=.65
target=Vector((.012,0,.06))
for name,loc,power,size in [('Key',(-.15,-.25,.35),4,.25),('Fill',(.2,-.1,.2),1.5,.2),('Rim',(0,.25,.3),3,.2)]:
 ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.size=size; lo=bpy.data.objects.new(name,ld); scene.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera'); cam=bpy.data.objects.new('Preview_camera',cd); scene.collection.objects.link(cam); scene.camera=cam; cd.type='ORTHO'; cd.ortho_scale=.175
views={'01_front':(.012,-1,.06),'02_back':(.012,1,.06),'03_left':(-1,0,.06),'04_right':(1,0,.06),'05_top':(.012,0,1),'06_bottom':(.012,0,-1),'07_hero':(.24,-.6,.32)}
for name,loc in views.items():
 cam.location=loc; cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); scene.render.filepath=str(ROOT/'Previews'/f'{name}_v01.png'); bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.type='MATERIAL'; area.spaces.active.region_3d.view_distance=.35; area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT)); print('TAPE_FINAL',json.dumps(report))
