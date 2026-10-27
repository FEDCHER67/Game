import bpy,bmesh,json,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
root=R.ROOT;results=[]
for p in json.loads((root/'selected_models_v01.json').read_text()):
 rev=p['revision'];name=p['name'];folder=Path(p['folder']);R.clean();bpy.ops.import_scene.fbx(filepath=str(folder/(name+f'_v{rev:02}.fbx')))
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];lods=sorted(meshes,key=lambda o:o.name);lo,hi=R.bounds([next(o for o in lods if o.name.endswith('LOD0'))]);dims=list(hi-lo)
 tris=[R.tris([o]) for o in lods];err=max(abs(a-b) for a,b in zip(dims,p['dimensions_m']));pivot=max(abs(v) for o in lods for v in o.location)
 checks={'lod_count':len(lods)==3,'triangles_match':tris==p['lod_triangles'],'dimensions_match_0_1mm':err<.0001,'visual_origins_zero':pivot<.0001,'ground_contact':abs(lo.z)<.0001,'one_shared_material':all(len(o.data.materials)==1 for o in lods)}
 lod_dimensions=[list(R.bounds([o])[1]-R.bounds([o])[0]) for o in lods]
 checks['all_lod_dimensions_within_10_percent']=all(all(abs(v-dims[i])<max(.15,dims[i]*.1) for i,v in enumerate(d)) for d in lod_dimensions)
 R.clean();bpy.ops.import_scene.fbx(filepath=str(folder/(name+f'_collisions_v{rev:02}.fbx')))
 cs=[o for o in bpy.context.scene.objects if o.type=='MESH'];collider=[]
 for c in cs:
  bm=bmesh.new();bm.from_mesh(c.data);points=[v.co for v in bm.verts];volume=abs(bm.calc_volume());convex=all(all(f.normal.dot(v.co-f.verts[0].co)<=.00001 for v in bm.verts) for f in bm.faces);collider.append({'name':c.name,'closed':all(e.is_manifold for e in bm.edges),'convex':convex,'positive_volume':volume>0,'triangles':R.tris([c])});bm.free()
 checks['colliders_closed_convex']=all(c['closed'] and c['convex'] and c['positive_volume'] for c in collider);checks['collider_count']=len(cs)==p['ucx_count']
 results.append({'name':name,'revision':rev,'checks':checks,'max_dimension_error_m':err,'lod_dimensions_m':lod_dimensions,'roundtrip_triangles':tris,'colliders':collider,'PASS':all(checks.values())})
 print('ROUNDTRIP',name,all(checks.values()),checks,flush=True)
(root/'roundtrip_validation_v01.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
