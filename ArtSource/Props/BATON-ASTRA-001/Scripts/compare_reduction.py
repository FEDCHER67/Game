import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\BATON-ASTRA-001')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'BATON_ASTRA_001_v01.blend'))
old=bpy.data.objects['Item_Baton']; bpy.data.objects.remove(old,do_unlink=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\baton_tripo_base.fbx')
obj=next(o for o in bpy.context.selected_objects if o.type=='MESH')
bpy.context.view_layer.objects.active=obj
bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
me=obj.data
lo=min(v.co.z for v in me.vertices); hi=max(v.co.z for v in me.vertices)
lower=[v.co for v in me.vertices if v.co.z<lo+(hi-lo)*.25]
cx=(min(v.x for v in lower)+max(v.x for v in lower))/2
cy=(min(v.y for v in lower)+max(v.y for v in lower))/2
for v in me.vertices:v.co=Vector(((v.co.x-cx)*.55/(hi-lo),(v.co.y-cy)*.55/(hi-lo),(v.co.z-lo)*.55/(hi-lo)))
for v in me.vertices:
 if v.co.z<.36 and v.co.z>.025:
  rad=math.hypot(v.co.x,v.co.y)
  if rad>0: v.co.x*=.019/rad; v.co.y*=.019/rad
 if .429<v.co.z<.519:
  rad=math.hypot(v.co.x,v.co.y)
  target=.018+sum(.003*math.exp(-((v.co.z-c)/.007)**2) for c in (.446,.473,.500))
  if rad>0:v.co.x*=target/rad;v.co.y*=target/rad
 if .038<v.co.x<.123:
  rad=math.hypot(v.co.y,v.co.z-.397)
  target=.018+sum(.003*math.exp(-((v.co.x-c)/.007)**2) for c in (.052,.080,.108))
  if rad>0:v.co.y*=target/rad;v.co.z=.397+(v.co.z-.397)*target/rad
original=me.copy()
mat=bpy.data.materials.new('Clean_black'); mat.use_nodes=True
bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(.008,.009,.011,1); bs.inputs['Roughness'].default_value=.8; bs.inputs['Specular IOR Level'].default_value=.2
for candidate in ['w1','w3','w6']:
 obj.data=original.copy(); me=obj.data
 me.materials.clear();me.materials.append(mat)
 if candidate.startswith('w'):
  group=obj.vertex_groups.new(name='Preserve_grips')
  for v in me.vertices:
   w=.90 if (v.co.z>.427 or v.co.x>.044 or v.co.z<.027) else .60
   group.add([v.index],w,'REPLACE')
  mod=obj.modifiers.new('Weighted','DECIMATE');mod.ratio=498/1062;mod.vertex_group=group.name;mod.vertex_group_factor=int(candidate[1:])/100;mod.invert_vertex_group=True
  bpy.ops.object.modifier_apply(modifier=mod.name)
 elif candidate=='planar':
  bm=bmesh.new();bm.from_mesh(me)
  candidates=[e for e in bm.edges if all(v.co.z<.37 for v in e.verts)]
  bmesh.ops.dissolve_limit(bm,angle_limit=.15,use_dissolve_boundaries=False,verts=[],edges=candidates,delimit={'NORMAL'})
  bm.to_mesh(me);bm.free();me.calc_loop_triangles(); print('PLANAR_COUNT',len(me.loop_triangles))
  mod=obj.modifiers.new('Budget','DECIMATE');mod.ratio=min(1,498/len(me.loop_triangles))
  bpy.ops.object.modifier_apply(modifier=mod.name)
 for p in obj.data.polygons:p.use_smooth=True;p.material_index=0
 obj.data.calc_loop_triangles();print(candidate,len(obj.data.loop_triangles))
 bpy.context.scene.render.filepath=str(ROOT/'Validation'/f'reduction_{candidate}.png');bpy.ops.render.render(write_still=True)
