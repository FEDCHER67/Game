import bpy,bmesh,json,hashlib,struct
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\EYE-ASTRA-001')
BASE=ROOT/'EYE_ASTRA_001_v03.blend'
OUT=ROOT/'Variants'/'v04'; OUT.mkdir(parents=True,exist_ok=True)
PALETTE={
 'BLUE':((.025,.19,.48),(.12,.38,.65),(.012,.07,.19)),
 'GREEN':((.025,.20,.06),(.15,.39,.10),(.012,.085,.025)),
 'BROWN':((.11,.035,.01),(.31,.15,.055),(.045,.014,.007)),
 'GRAY':((.18,.21,.23),(.39,.43,.45),(.065,.08,.09)),
 'AMBER':((.33,.11,.012),(.72,.42,.07),(.12,.04,.005)),
}
assert not (ROOT/'EYE_COLOR_SET_ASTRA_001_v04.blend').exists()
def geometry_hash(me):
 h=hashlib.sha256()
 for v in me.vertices: h.update(struct.pack('<3f',*v.co))
 for p in me.polygons:
  h.update(struct.pack('<I',len(p.vertices)))
  for i in p.vertices: h.update(struct.pack('<I',i))
 for uv in me.uv_layers.active.data: h.update(struct.pack('<2f',*uv.uv))
 return h.hexdigest()
def paint(obj,key,palette):
 mat=bpy.data.materials.new('Eye_'+key); mat.use_nodes=True
 nt=mat.node_tree; nodes=nt.nodes; links=nt.links
 bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED'); bs.inputs['Roughness'].default_value=.52
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
 stripe=op('ADD',op('MULTIPLY_ADD',op('SINE',op('MULTIPLY',angle,18)),.13),.5)
 color=mix(iris,(.78,.73,.62),mix(stripe,palette[0],palette[1]))
 color=mix(rim,color,palette[2]); color=mix(pupil,color,(.006,.008,.010))
 back=op('MULTIPLY',op('GREATER_THAN',y,.83),op('LESS_THAN',r,.17))
 color=mix(back,color,(.57,.23,.22)); links.new(color,bs.inputs['Base Color'])
 obj.data.materials.clear(); obj.data.materials.append(mat)
 im=bpy.data.images.new('EYE_'+key+'_basecolor_v04',width=1024,height=1024,alpha=False)
 tn=nodes.new('ShaderNodeTexImage'); tn.image=im; nodes.active=tn
 scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=1; scene.render.bake.margin=16
 bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'})
 im.filepath_raw=str(OUT/(im.name+'.png')); im.file_format='PNG'; im.save(); im.pack()
 for l in list(bs.inputs['Base Color'].links): links.remove(l)
 links.new(tn.outputs['Color'],bs.inputs['Base Color'])
 return im
rows=[]
for key,palette in PALETTE.items():
 bpy.ops.wm.open_mainfile(filepath=str(BASE))
 obj=bpy.data.objects['Item_Eye']; obj.name='Item_Eye_'+key
 obj.data=obj.data.copy(); before=geometry_hash(obj.data)
 bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active=obj
 paint(obj,key,palette)
 after=geometry_hash(obj.data); assert before==after
 obj.data.calc_loop_triangles(); assert len(obj.data.loop_triangles)==550
 stem='EYE_'+key+'_ASTRA_001_v04'
 assert not (OUT/(stem+'.blend')).exists()
 bpy.ops.export_scene.fbx(filepath=str(OUT/(stem+'.fbx')),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
 scene=bpy.context.scene; scene.cycles.samples=24; cam=scene.camera
 for view,loc in [('front',(0,-.2,.02)),('hero',(.10,-.20,.07))]:
  cam.location=loc; cam.rotation_euler=(Vector((0,-.002,.02))-cam.location).to_track_quat('-Z','Y').to_euler()
  scene.render.filepath=str(ROOT/'Previews'/f'{key.lower()}_{view}_v04.png'); bpy.ops.render.render(write_still=True)
 bpy.ops.object.select_all(action='DESELECT'); bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(stem+'.blend')))
 rows.append({'variant':key,'triangles':550,'mesh_and_uv_sha256':after,'geometry_and_uv_unchanged':True,'blend':str(OUT/(stem+'.blend')),'fbx':str(OUT/(stem+'.fbx'))})
 print('VARIANT_DONE',key,flush=True)
# Comparison scene: original turquoise and five new independent duplicates.
bpy.ops.wm.open_mainfile(filepath=str(BASE))
scene=bpy.context.scene; original=bpy.data.objects['Item_Eye']; original.name='Item_Eye_TURQUOISE'
objects=[original]
for key in PALETTE:
 ob=original.copy(); ob.data=original.data.copy(); ob.name='Item_Eye_'+key
 scene.collection.objects.link(ob)
 mat=bpy.data.materials.new('Eye_'+key); mat.use_nodes=True
 bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'); bs.inputs['Roughness'].default_value=.52
 tn=mat.node_tree.nodes.new('ShaderNodeTexImage'); tn.image=bpy.data.images.load(str(OUT/f'EYE_{key}_basecolor_v04.png')); tn.image.pack()
 mat.node_tree.links.new(tn.outputs['Color'],bs.inputs['Base Color'])
 ob.data.materials.clear(); ob.data.materials.append(mat); objects.append(ob)
labels=['TURQUOISE',*PALETTE.keys()]
for i,ob in enumerate(objects):
 ob.location=((i%3-1)*.075,0,.10 if i<3 else .022)
 font=bpy.data.curves.new('Label_'+labels[i],'FONT'); font.body=labels[i]; font.align_x='CENTER'; font.size=.005; font.extrude=0
 label=bpy.data.objects.new('Label_'+labels[i],font); scene.collection.objects.link(label)
 label.location=(ob.location.x,-.015,ob.location.z-.009); label.rotation_euler=(1.57079632679,0,0)
 lm=bpy.data.materials.get('Label_white')
 if lm is None:
  lm=bpy.data.materials.new('Label_white'); lm.use_nodes=True
  lbs=next(n for n in lm.node_tree.nodes if n.type=='BSDF_PRINCIPLED'); lbs.inputs['Base Color'].default_value=(.85,.85,.85,1)
 label.data.materials.append(lm)
assert len({ob.data.as_pointer() for ob in objects})==6
cam=scene.camera; target=Vector((0,-.002,.081)); cam.location=(0,-.5,.081); cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.ortho_scale=.235
scene.render.resolution_x=1200; scene.render.resolution_y=900; scene.cycles.samples=24
for ob in scene.objects:
 if ob.type=='LIGHT':
  ob.location.x*=3; ob.location.y*=3; ob.location.z=ob.location.z*3+.04
  ob.data.energy*=9; ob.data.size*=3; ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(ROOT/'Previews'/'color_set_front_v04.png'); bpy.ops.render.render(write_still=True)
bpy.ops.object.select_all(action='DESELECT')
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.region_3d.view_distance=.35; area.spaces.active.region_3d.view_location=target
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'EYE_COLOR_SET_ASTRA_001_v04.blend'))
(ROOT/'Validation'/'color_variants_v04.json').write_text(json.dumps({'variants':rows,'collection_triangles':3300,'single_user_meshes':True,'tripo_credits_spent':0},indent=2),encoding='utf-8')
print('COLOR_SET_DONE',flush=True)
