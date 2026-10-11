import bpy, bmesh, json
from pathlib import Path
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\TASER-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=r'C:\Dev\Game\Working\Tripo\taser_tripo_base.fbx')
rows=[]
for obj in bpy.context.scene.objects:
 if obj.type!='MESH': continue
 bpy.context.view_layer.objects.active=obj;obj.select_set(True)
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 me=obj.data; me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me)
 zmin=min(v.co.z for v in me.vertices);zmax=max(v.co.z for v in me.vertices)
 rings=[]
 for k in range(12):
  pts=[v.co for v in me.vertices if k/12 <= (v.co.z-zmin)/(zmax-zmin) <= (k+1)/12]
  rings.append({'k':k,'n':len(pts),'xmin':min((v.x for v in pts),default=0),'xmax':max((v.x for v in pts),default=0),'ymin':min((v.y for v in pts),default=0),'ymax':max((v.y for v in pts),default=0)})
 rows.append({'object':obj.name,'triangles':len(me.loop_triangles),'vertices':len(me.vertices),'faces':len(me.polygons),'bounds':[[min(v.co[i] for v in me.vertices),max(v.co[i] for v in me.vertices)] for i in range(3)],'dimensions':list(obj.dimensions),'nonmanifold':sum(not e.is_manifold for e in bm.edges),'zeroarea':sum(f.calc_area()<1e-13 for f in bm.faces),'materials':[m.name for m in me.materials],'uv':len(me.uv_layers),'rings':rings})
 bm.free()
(ROOT/'Validation/source_inspection.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
