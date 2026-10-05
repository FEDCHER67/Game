import bpy,bmesh,json,hashlib
from pathlib import Path
ROOT=Path(r'C:\Dev\Game\ArtSource\Props\EYE-ASTRA-001')
rows=[]
for key in ['BLUE','GREEN','BROWN','GRAY','AMBER']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(ROOT/'Variants'/'v04'/f'EYE_{key}_ASTRA_001_v04.fbx'))
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']; assert len(meshes)==1
 me=meshes[0].data; me.calc_loop_triangles(); bm=bmesh.new(); bm.from_mesh(me)
 row={'variant':key,'triangles':len(me.loop_triangles),'smooth_faces':sum(p.use_smooth for p in me.polygons),'faces':len(me.polygons),'nonmanifold_edges':sum(not e.is_manifold for e in bm.edges),'zero_area_faces':sum(f.calc_area()<1e-14 for f in bm.faces),'uv_layers':len(me.uv_layers),'texture_loaded':any(i.has_data and i.size[0]==1024 for i in bpy.data.images)}
 bm.free(); row['pass']=row['triangles']==550 and row['smooth_faces']==row['faces'] and row['nonmanifold_edges']==0 and row['zero_area_faces']==0 and row['uv_layers']==1 and row['texture_loaded']
 row['texture_sha256']=hashlib.sha256((ROOT/'Variants'/'v04'/f'EYE_{key}_basecolor_v04.png').read_bytes()).hexdigest()
 rows.append(row)
assert all(r['pass'] for r in rows),rows
assert len({r['texture_sha256'] for r in rows})==5
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'EYE_COLOR_SET_ASTRA_001_v04.blend'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
assert len(meshes)==6 and len({o.data.as_pointer() for o in meshes})==6
report={'variants':rows,'six_independent_meshes':True,'pass':True}
(ROOT/'Validation'/'variants_fbx_roundtrip_v04.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('VARIANTS_PASS',json.dumps(report))
