import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\EYE-ASTRA-001')
OUT=ROOT/'EYE_ASTRA_001_v01.blend'
assert not OUT.exists(), 'Preserve numbered revisions'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\eye_tripo_base.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH'); obj.name='Item_Eye'
bpy.context.view_layer.objects.active=obj; obj.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
obj.data.calc_loop_triangles(); source_tri=len(obj.data.loop_triangles)
mod=obj.modifiers.new('Local_budget_reduction','DECIMATE'); mod.ratio=.5
bpy.ops.object.modifier_apply(modifier=mod.name)
for p in obj.data.polygons: p.use_smooth=True
mat=bpy.data.materials.new('Eye_ivory_teal'); mat.use_nodes=True
nt=mat.node_tree; nodes=nt.nodes; links=nt.links
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
bs.inputs['Roughness'].default_value=.52
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
dx=op('SUBTRACT',x,.5); dz=op('SUBTRACT',z,.5)
r=op('SQRT',op('ADD',op('MULTIPLY',dx,dx),op('MULTIPLY',dz,dz)))
front=op('LESS_THAN',y,.32)
iris=op('MULTIPLY',front,op('LESS_THAN',r,.278))
pupil=op('MULTIPLY',front,op('LESS_THAN',r,.132))
rim=op('MULTIPLY',front,op('MULTIPLY',op('GREATER_THAN',r,.255),op('LESS_THAN',r,.278)))
angle=op('ARCTAN2',dz,dx)
stripe=op('MULTIPLY_ADD',op('SINE',op('MULTIPLY',angle,18)),.13)
# Soft radial variation, intentionally stylized rather than photorealistic.
stripe=op('ADD',stripe,.5)
iriscolor=mix(stripe,(.025,.26,.30),(.08,.42,.32))
color=mix(iris,(.78,.73,.62),iriscolor)
color=mix(rim,color,(.018,.14,.18)); color=mix(pupil,color,(.006,.008,.010))
back=op('MULTIPLY',op('GREATER_THAN',y,.83),op('LESS_THAN',r,.17))
color=mix(back,color,(.57,.23,.22))
links.new(color,bs.inputs['Base Color'])
obj.data.materials.clear(); obj.data.materials.append(mat)
# Scale body diameter to 40 mm, with base origin; front faces -Y.
scale=.04/.83544921875
for v in obj.data.vertices: v.co*=scale
obj.data.update()
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(island_margin=.025); bpy.ops.object.mode_set(mode='OBJECT')
im=bpy.data.images.new('EYE_basecolor_v01',width=1024,height=1024,alpha=False)
tn=nodes.new('ShaderNodeTexImage'); tn.image=im; nodes.active=tn
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=1; scene.render.bake.margin=16
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
im.filepath_raw=str(ROOT/'Textures'/'EYE_basecolor_v01.png'); im.file_format='PNG'; im.save(); im.pack()
for l in list(bs.inputs['Base Color'].links): links.remove(l)
links.new(tn.outputs['Color'],bs.inputs['Base Color'])
me=obj.data; me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
report={'source_triangles':source_tri,'local_decimate_ratio':.5,'final_triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'smooth_faces':sum(p.use_smooth for p in me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'boundary_edges':sum(e.is_boundary for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'uv_layers':len(me.uv_layers),'body_diameter_m':.04,'budget':[200,600],'front_axis':'-Y','origin':'bottom centre','paid_extras':False}
bm.free(); report['pass']=200<=report['final_triangles']<=600 and report['nonmanifold_edges']==0 and report['zero_area_faces']==0
(ROOT/'Validation'/'mesh_v01.json').write_text(json.dumps(report,indent=2),encoding='utf-8'); assert report['pass'],report
bpy.ops.export_scene.fbx(filepath=str(ROOT/'EYE_ASTRA_001_v01.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
scene.cycles.samples=24; scene.render.resolution_x=800; scene.render.resolution_y=800; scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Preview_world'); scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs[0].default_value=(.14,.17,.20,1); bg.inputs[1].default_value=.5
target=Vector((0,-.002,.02))
for name,loc,power,size in [('Key',(-.08,-.10,.12),.16,.09),('Fill',(.09,-.04,.075),.065,.07),('Rim',(0,.09,.09),.13,.06)]:
 ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.shape='DISK'; ld.size=size
 lo=bpy.data.objects.new(name,ld); scene.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(target-lo.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Preview_camera'); cam=bpy.data.objects.new('Preview_camera',cd); scene.collection.objects.link(cam); scene.camera=cam; cd.type='ORTHO'; cd.ortho_scale=.06
views={'01_front':(0,-.2,.02),'02_back':(0,.2,.02),'03_left':(-.2,0,.02),'04_right':(.2,0,.02),'05_top':(0,0,.22),'06_bottom':(0,0,-.18),'07_hero':(.10,-.20,.07)}
for name,loc in views.items():
 cam.location=loc; cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(ROOT/'Previews'/f'{name}_v01.png'); bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='DESELECT')
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.type='MATERIAL'; area.spaces.active.region_3d.view_distance=.095; area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(OUT)); print('EYE_FINAL',json.dumps(report))
