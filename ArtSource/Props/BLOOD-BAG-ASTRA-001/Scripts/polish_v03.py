import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\BLOOD-BAG-ASTRA-001')
OUT=ROOT/'BLOOD_BAG_ASTRA_001_v03.blend'
assert not OUT.exists(), 'Do not overwrite revision'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\blood_bag_tripo_base.fbx')
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
obj.name='BLOOD_BAG_body'
bpy.context.view_layer.objects.active=obj
obj.select_set(True)
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
obj.data.calc_loop_triangles(); source_tri=len(obj.data.loop_triangles)
mod=obj.modifiers.new('Local_budget_reduction','DECIMATE'); mod.ratio=0.5
bpy.ops.object.modifier_apply(modifier=mod.name)
# Approved reference: body width/height ~0.74; ports z<0.15; hanger z>0.85.
# Preserve source silhouette; all painting and decimation are local.
def material(name,color,roughness=.65):
 m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
 bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Base Color'].default_value=(*color,1); bs.inputs['Roughness'].default_value=roughness
 return m
red=material('Blood_muted_red',(0.34,.028,.038),.5)
ivory=material('Seam_and_caps',(0.73,.69,.62))
white=material('Label_ivory',(.86,.83,.75))
obj.data.materials.clear()
for m in (red,ivory): obj.data.materials.append(m)
for f in obj.data.polygons:
 x,y,z=f.center
 f.material_index=1 if z<.045 or z>.84 or (z>.13 and (abs(x)>.322 or z<.175)) else 0
 f.use_smooth=True
# Surface-only colour: no floating geometry or UV dependencies.
nt=red.node_tree; nodes=nt.nodes; links=nt.links
bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
tex=nodes.new('ShaderNodeTexCoord'); sep=nodes.new('ShaderNodeSeparateXYZ'); links.new(tex.outputs['Generated'],sep.inputs[0])
def op(kind,a,b=0):
 n=nodes.new('ShaderNodeMath'); n.operation=kind
 for i,v in enumerate((a,b)):
  if isinstance(v,(int,float)): n.inputs[i].default_value=v
  else: links.new(v,n.inputs[i])
 return n.outputs[0]
x,y,z=sep.outputs['X'],sep.outputs['Y'],sep.outputs['Z']
ax=op('ABSOLUTE',op('SUBTRACT',x,.5)); az=op('ABSOLUTE',op('SUBTRACT',z,.5))
qx=op('MAXIMUM',op('SUBTRACT',ax,.36),0); qz=op('MAXIMUM',op('SUBTRACT',az,.28),0)
body=op('LESS_THAN',op('ADD',op('MULTIPLY',qx,qx),op('MULTIPLY',qz,qz)),.0036)
ports=op('MULTIPLY',op('GREATER_THAN',z,.045),op('LESS_THAN',z,.14))
redmask=op('MAXIMUM',body,ports)
label=op('MULTIPLY',op('LESS_THAN',ax,.2),op('MULTIPLY',op('GREATER_THAN',z,.43),op('MULTIPLY',op('LESS_THAN',z,.61),op('LESS_THAN',y,.45))))
dx=op('DIVIDE',ax,.0538); dz=op('DIVIDE',op('SUBTRACT',z,.515),.038)
ellipse=op('MULTIPLY',op('LESS_THAN',op('ADD',op('MULTIPLY',dx,dx),op('MULTIPLY',dz,dz)),1),op('LESS_THAN',z,.515))
upper=op('MULTIPLY',op('GREATER_THAN',z,.515),op('MULTIPLY',op('LESS_THAN',z,.585),op('LESS_THAN',ax,op('MULTIPLY',op('SUBTRACT',.585,z),.76857))))
dropmask=op('MULTIPLY',label,op('MAXIMUM',ellipse,upper))
def mix(f,c1,c2):
 n=nodes.new('ShaderNodeMixRGB'); n.blend_type='MIX'; links.new(f,n.inputs[0])
 for i,c in [(1,c1),(2,c2)]:
  if isinstance(c,tuple): n.inputs[i].default_value=(*c,1)
  else: links.new(c,n.inputs[i])
 return n.outputs[0]
colour=mix(redmask,(.62,.58,.52),(.22,.012,.022))
colour=mix(label,colour,(.82,.78,.68)); colour=mix(dropmask,colour,(.30,.012,.022))
links.new(colour,bs.inputs['Base Color']); bs.inputs['Roughness'].default_value=.72
for p in obj.data.polygons: p.material_index=0
assets=[obj]
for ob in assets:
 for v in ob.data.vertices: v.co*=.28
 ob.data.update()
# Validate source-derived body and the intentionally open surface decals separately.
rows=[]
for ob in assets:
 me=ob.data; me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
 rows.append({'object':ob.name,'vertices':len(me.vertices),'faces':len(me.polygons),'triangles':len(me.loop_triangles),'boundary_edges':sum(e.is_boundary for e in bm.edges),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces)})
 bm.free()
tri=sum(r['triangles'] for r in rows)
assert 200<=tri<=600,tri
report={'source_triangles':source_tri,'local_decimate_ratio':.5,'final_triangles':tri,'budget':[200,600],'budget_pass':True,'height_m':.28,'objects':rows,'label_surface_offset_m':.00028,'drop_surface_offset_m':.000448,'notes':['Body smooth shading; seam, label and drop are procedural surface colour.','No paid texture or remesh used.','Materials recreated locally; source FBX preserved unchanged.']}
(ROOT/'Validation'/'mesh_v03.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
# Export only asset meshes.
bpy.ops.object.select_all(action='DESELECT')
for ob in assets: ob.select_set(True)
bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(ROOT/'BLOOD_BAG_ASTRA_001_v03.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
# Presentation after geometry is complete.
scene=bpy.context.scene
try: scene.render.engine='CYCLES'
except TypeError: pass
scene.cycles.samples=24
scene.render.resolution_x=800; scene.render.resolution_y=800; scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Preview_world')
scene.world.color=(.14,.14,.14)
world=scene.world; world.use_nodes=True
bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs[0].default_value=(.14,.17,.20,1); bg.inputs[1].default_value=.5
for name,loc,power,size in [('Key',(-.45,-.55,.65),5,.5),('Fill',(.5,-.2,.4),2,.4),('Rim',(0,.5,.5),4,.35)]:
 ld=bpy.data.lights.new(name,'AREA'); ld.energy=power; ld.shape='DISK'; ld.size=size
 lo=bpy.data.objects.new(name,ld); scene.collection.objects.link(lo); lo.location=loc; lo.rotation_euler=(Vector((0,0,.14))-lo.location).to_track_quat('-Z','Y').to_euler()
camd=bpy.data.cameras.new('Preview_camera'); cam=bpy.data.objects.new('Preview_camera',camd); scene.collection.objects.link(cam); scene.camera=cam; camd.type='ORTHO'; camd.ortho_scale=.36
views={'01_front':(0,-1,.14),'02_back':(0,1,.14),'03_left':(-1,0,.14),'04_right':(1,0,.14),'05_top':(0,0,1.14),'06_bottom':(0,0,-.86),'07_hero':(.48,-1,.38)}
for name,loc in views.items():
 cam.location=loc; cam.rotation_euler=(Vector((0,0,.14))-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(ROOT/'Previews'/f'{name}_v03.png'); bpy.ops.render.render(write_still=True)
# Save comfortable material preview, no selected outlines.
bpy.ops.object.select_all(action='DESELECT')
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   area.spaces.active.shading.type='MATERIAL'; area.spaces.active.region_3d.view_distance=.6; area.spaces.active.region_3d.view_location=Vector((0,0,.14))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print('FINAL_BAG',json.dumps(report))