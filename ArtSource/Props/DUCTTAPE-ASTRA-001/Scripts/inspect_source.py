import bpy, bmesh, json
from pathlib import Path
from mathutils import Vector
root=Path(r'C:\Dev\Game\ArtSource\Props\DUCTTAPE-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\ducttape_tripo_base.fbx')
rows=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH': continue
 bpy.context.view_layer.objects.active=ob; ob.select_set(True)
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 me=ob.data; me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
 rows.append({'name':ob.name,'triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'bounds':[list(v) for v in ob.bound_box],'nonmanifold':sum(not e.is_manifold for e in bm.edges),'materials':[m.name for m in me.materials],'coords':[list(v.co) for v in me.vertices],'faces_data':[list(p.vertices) for p in me.polygons]})
 bm.free()
root.joinpath('Validation/source_inspection.json').write_text(json.dumps(rows,indent=2))
print('TAPE_SOURCE',json.dumps([{k:v for k,v in r.items() if k not in ['coords','faces_data']} for r in rows]))
