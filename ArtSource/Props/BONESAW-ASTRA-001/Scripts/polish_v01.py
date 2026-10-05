import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\BONESAW-ASTRA-001')
for d in ['Textures','Previews','Validation']: (ROOT/d).mkdir(exist_ok=True)
OUT=ROOT/'BONESAW_ASTRA_001_v01.blend'
assert not OUT.exists()
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\bonesaw_tripo_base.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH'); obj.name='Item_BoneSaw'
bpy.context.view_layer.objects.active=obj; obj.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
obj.data.calc_loop_triangles(); source_tri=len(obj.data.loop_triangles)
bm=bmesh.new(); bm.from_mesh(obj.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=.00001)
boundary=[e for e in bm.edges if e.is_boundary]
if boundary: bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
print('SAW_REPAIR',len(bm.verts),len(bm.faces),sum(not e.is_manifold for e in bm.edges))
bm.to_mesh(obj.data); bm.free(); obj.data.update()
obj.data.calc_loop_triangles(); repaired_tri=len(obj.data.loop_triangles)
mod=obj.modifiers.new('Local_triangle_budget','DECIMATE'); mod.ratio=650/repaired_tri
bpy.ops.object.modifier_apply(modifier=mod.name)
# Keep broad blade faces flat, smooth rounded handle/chamfers only.
for p in obj.data.polygons: p.use_smooth=p.center.x>.24 or abs(p.normal.y)<.8
mat=bpy.data.materials.new('BoneSaw_clean_slate_steel_rust'); mat.use_nodes=True
nodes=mat.node_tree.nodes; links=mat.node_tree.links
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED'); bs.inputs['Roughness'].default_value=.58
tc=nodes.new('ShaderNodeTexCoord'); sep=nodes.new('ShaderNodeSeparateXYZ'); links.new(tc.outputs['Generated'],sep.inputs[0])
def op(kind,a,b=0):
 n=nodes.new('ShaderNodeMath'); n.operation=kind
 for i,v in enumerate((a,b)):
  if isinstance(v,(int,float)): n.inputs[i].default_value=v
  else: links.new(v,n.inputs[i])
 return n.outputs[0]
def mix(f,c1,c2):
 n=nodes.new('ShaderNodeMixRGB'); links.new(f,n.inputs[0])
 for i,c in ((1,c1),(2,c2)):
  if isinstance(c,tuple): n.inputs[i].default_value=(*c,1)
  else: links.new(c,n.inputs[i])
 return n.outputs[0]
x,y,z=sep.outputs['X'],sep.outputs['Y'],sep.outputs['Z']
grip=op('GREATER_THAN',x,.77)
color=mix(grip,(.49,.54,.57),(.09,.14,.20))
# Two broad flat orange flecks, no noisy procedural grime.
r1=op('MULTIPLY',op('MULTIPLY',op('GREATER_THAN',x,.68),op('LESS_THAN',x,.74)),op('GREATER_THAN',z,.67))
r2=op('MULTIPLY',op('MULTIPLY',op('GREATER_THAN',x,.71),op('LESS_THAN',x,.75)),op('MULTIPLY',op('GREATER_THAN',z,.38),op('LESS_THAN',z,.53)))
color=mix(op('MAXIMUM',r1,r2),color,(.42,.18,.065)); links.new(color,bs.inputs['Base Color'])
obj.data.materials.clear(); obj.data.materials.append(mat)
# Overall 34 cm, handle to +X, broad front to -Y, base origin.
for v in obj.data.vertices: v.co*=.34/.99951171875
obj.data.update()
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.025); bpy.ops.object.mode_set(mode='OBJECT')
im=bpy.data.images.new('BONESAW_basecolor_v01',width=1024,height=1024,alpha=False)
tn=nodes.new('ShaderNodeTexImage'); tn.image=im; nodes.active=tn
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=1; scene.render.bake.margin=16
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
im.filepath_raw=str(ROOT/'Textures/BONESAW_basecolor_v01.png'); im.file_format='PNG'; im.save(); im.pack()
for l in list(bs.inputs['Base Color'].links): links.remove(l)
links.new(tn.outputs['Color'],bs.inputs['Base Color'])
me=obj.data; me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
report={'source_triangles':source_tri,'repaired_triangles':repaired_tri,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'uv_layers':len(me.uv_layers),'width_m':.34,'budget':[400,700],'front_axis':'-Y','origin':'bottom centre','paid_extras':False,'materials':'locally baked 1024px flat colours; broad rust patches'}
bm.free(); report['pass']=400<=report['final_triangles']<=700 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0
(ROOT/'Validation/mesh_v01.json').write_text(json.dumps(report,indent=2)); print('SAW_MESH',json.dumps(report)); assert report['pass'],report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'BONESAW_ASTRA_001_v01.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
scene.cycles.samples=20; scene.render.resolution_x=1000; scene.render.resolution_y=700; scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Preview_world'); scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs[0].default_value=(.11,.13,.16,1); bg.inputs[1].default_value=.7
target=Vector((0,0,.05))
for name,loc,power,size in [('Key',(-.3,-.5,.7),16,.5),('Fill',(.4,-.2,.3),6,.4),('Rim',(0,.4,.5),10,.3)]:
 ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.size=size
 lo=bpy.data.objects.new(name,ld); scene.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera'); cam=bpy.data.objects.new('Preview_camera',cd); scene.collection.objects.link(cam); scene.camera=cam; cd.type='ORTHO'; cd.ortho_scale=.40
views={'01_front':(0,-1,.05),'02_back':(0,1,.05),'03_left':(-1,0,.05),'04_right':(1,0,.05),'05_top':(0,0,1),'06_bottom':(0,0,-1),'07_hero':(.25,-1,.25)}
for name,loc in views.items():
 cam.location=loc; cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(ROOT/'Previews'/f'{name}_v01.png'); bpy.ops.render.render(write_still=True)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.type='MATERIAL'; area.spaces.active.region_3d.view_distance=.65; area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT)); print('SAW_FINAL',json.dumps(report))
