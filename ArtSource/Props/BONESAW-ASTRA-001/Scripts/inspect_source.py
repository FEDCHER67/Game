import bpy,bmesh,json
from pathlib import Path
root=Path(r'C:\Dev\Game\ArtSource\Props\BONESAW-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\bonesaw_tripo_base.fbx')
rows=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH': continue
 bpy.context.view_layer.objects.active=o; o.select_set(True)
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 o.data.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(o.data)
 rows.append({'name':o.name,'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'triangles':len(o.data.loop_triangles),'bounds':[list(v) for v in o.bound_box],'nonmanifold':sum(not e.is_manifold for e in bm.edges),'materials':[m.name for m in o.data.materials],'coords':[list(v.co) for v in o.data.vertices]})
 bm.free()
root.joinpath('Validation').mkdir(exist_ok=True)
root.joinpath('Validation/source_inspection.json').write_text(json.dumps(rows,indent=2))
print('SAW_INSPECT',json.dumps([{k:v for k,v in r.items() if k!='coords'} for r in rows]))
