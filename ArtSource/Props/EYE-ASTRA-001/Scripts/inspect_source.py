import bpy,json
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\eye_tripo_base.fbx')
for o in bpy.context.scene.objects:
 if o.type=='MESH':
  bpy.context.view_layer.objects.active=o; o.select_set(True)
  bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
  o.data.calc_loop_triangles()
  print('EYE_INSPECT',json.dumps({'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'triangles':len(o.data.loop_triangles),'bounds':[list(v) for v in o.bound_box],'materials':[m.name for m in o.data.materials]}))
  # Front/back polar ranges for local surface painting.
  for axis in range(3):
   lo=min(v.co[axis] for v in o.data.vertices); hi=max(v.co[axis] for v in o.data.vertices)
   print('AXIS',axis,lo,hi)
