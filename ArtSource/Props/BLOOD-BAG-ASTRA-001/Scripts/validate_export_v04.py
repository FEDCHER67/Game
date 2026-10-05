import bpy,bmesh,json
from pathlib import Path
root=Path(r'C:\Dev\Game\ArtSource\Props\BLOOD-BAG-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root/'BLOOD_BAG_ASTRA_001_v04.fbx'))
rows=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH': continue
 me=ob.data; me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
 rows.append({'object':ob.name,'triangles':len(me.loop_triangles),'smooth_faces':sum(p.use_smooth for p in me.polygons),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'uv_layers':len(me.uv_layers)})
 bm.free()
images=[{'name':i.name,'width':i.size[0],'height':i.size[1],'has_data':i.has_data} for i in bpy.data.images]
report={'objects':rows,'total_triangles':sum(r['triangles'] for r in rows),'textures':images}
report['pass']=200<=report['total_triangles']<=600 and all(r['nonmanifold_edges']==0 and r['zero_area_faces']==0 and r['smooth_faces']==r['faces'] for r in rows) and any(i['has_data'] and i['width']==1024 for i in images)
(root/'Validation'/'fbx_roundtrip_v04.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report)); assert report['pass']