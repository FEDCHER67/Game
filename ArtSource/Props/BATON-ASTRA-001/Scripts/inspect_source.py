import bpy, bmesh, json
from pathlib import Path
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\BATON-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\baton_tripo_base.fbx')
rows=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH': continue
    bpy.context.view_layer.objects.active=ob
    bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
    me=ob.data; me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
    rows.append({'name':ob.name,'vertices':len(me.vertices),'faces':len(me.polygons),'triangles':len(me.loop_triangles),'bounds':[[min(v.co[i] for v in me.vertices),max(v.co[i] for v in me.vertices)] for i in range(3)],'nonmanifold':sum(not e.is_manifold for e in bm.edges),'boundary':sum(e.is_boundary for e in bm.edges),'materials':[m.name for m in me.materials],'uv_layers':len(me.uv_layers)})
    bm.free()
(ROOT/'Validation/source_inspection.json').write_text(json.dumps(rows,indent=2))
print('BATON_SOURCE',json.dumps(rows))
