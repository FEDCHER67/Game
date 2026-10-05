import bpy, json
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\blood_bag_tripo_base.fbx')
for o in bpy.context.scene.objects:
 if o.type=='MESH':
  o.data.calc_loop_triangles()
  print('BAG_INSPECT',json.dumps({'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'triangles':len(o.data.loop_triangles),'dimensions':list(o.dimensions),'bounds':[list(o.matrix_world@Vector(v)) for v in o.bound_box],'materials':[m.name for m in o.data.materials],'rotation':list(o.rotation_euler)}))