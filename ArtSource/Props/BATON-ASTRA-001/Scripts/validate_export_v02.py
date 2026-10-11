import bpy,bmesh,json,math
from pathlib import Path
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\BATON-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'BATON_ASTRA_001_v02.fbx'))
rows=[]
for obj in bpy.context.scene.objects:
 if obj.type!='MESH':continue
 me=obj.data;me.calc_loop_triangles();bm=bmesh.new();bm.from_mesh(me)
 coords=[obj.matrix_world@v.co for v in me.vertices];dims=[max(v[i] for v in coords)-min(v[i] for v in coords) for i in range(3)]
 remaining=set(bm.verts);islands=0
 while remaining:
  islands+=1;stack=[remaining.pop()]
  while stack:
   v=stack.pop()
   for e in v.link_edges:
    w=e.other_vert(v)
    if w in remaining:remaining.remove(w);stack.append(w)
 rows.append({'object':obj.name,'triangles':len(me.loop_triangles),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-12 for f in bm.faces),'mesh_islands':islands,'uv_layers':len(me.uv_layers),'finite_uvs':all(math.isfinite(c) for layer in me.uv_layers for uv in layer.data for c in uv.uv),'dimensions_m':dims,'smooth_faces':sum(p.use_smooth for p in me.polygons),'faces':len(me.polygons)})
 bm.free()
images=[{'name':im.name,'width':im.size[0],'height':im.size[1],'has_data':im.has_data} for im in bpy.data.images]
report={'objects':rows,'total_triangles':sum(r['triangles'] for r in rows),'textures':images,'pass':False}
report['pass']=len(rows)==1 and 200<=report['total_triangles']<=500 and all(r['nonmanifold_edges']==0 and r['zero_area_faces']==0 and r['mesh_islands']==1 and r['uv_layers']>0 and r['finite_uvs'] and abs(r['dimensions_m'][2]-.55)<1e-5 and r['smooth_faces']==r['faces'] for r in rows) and any(im['has_data'] and im['width']==512 for im in images)
(ROOT/'Validation/fbx_roundtrip_v02.json').write_text(json.dumps(report,indent=2));print(json.dumps(report));assert report['pass']
