import bpy,bmesh,json,hashlib,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).parent;GAME=ROOT.parents[3]
expected=json.loads((ROOT/'validation_v04_04.json').read_text());bindings=json.loads((ROOT/'wind_bindings_v04_04.json').read_text());result=[]
for spec in expected['variants']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path=ROOT/'Models'/(spec['id']+'_v04_04.fbx');bpy.ops.import_scene.fbx(filepath=str(path))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==3
    assert len(spec['colliders'])==2
    for cap in spec['colliders']:
        assert cap['height_m']>=2*cap['radius_m']>0 and abs(Vector(cap['axis_Blender']).length-1)<1e-5
    for ob in meshes:
        lod=int(ob.name.rsplit('LOD',1)[1]);wanted=next(r for r in expected['lods'] if r['id']==spec['id'] and r['lod']==lod)
        verts=[ob.matrix_world@v.co for v in ob.data.vertices];dims=[max(v[k] for v in verts)-min(v[k] for v in verts) for k in range(3)]
        tris=sum(len(p.vertices)-2 for p in ob.data.polygons);assert tris==wanted['triangles'] and tris<=8000
        assert max(abs(a-b) for a,b in zip(dims,wanted['dimensions']))<.001
        assert abs(min(v.z for v in verts))<.001 and ob.matrix_world.translation.length<.001
        assert all(abs(v-1)<.001 for v in ob.scale) and len(ob.data.uv_layers)==1
        assert all(m.name in bindings['material_remaps'][spec['family']] for m in ob.data.materials)
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);loose=sum(not v.link_edges for v in bm.verts);bm.free()
        assert bad==loose==0 and not any(p.area<1e-10 for p in ob.data.polygons)
        result.append(dict(model=ob.name,lod=lod,triangles=tris,dimensions=dims,pivot='PASS',unitScale='PASS',closedGeometry='PASS',UV='PASS',materialRemap='PASS'))
protected=json.loads((ROOT/'protected_before_v04_04.json').read_text());changed=[]
for name,digest in protected.items():
    with open(GAME/name,'rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
    if actual!=digest:changed.append(name)
assert not changed,changed
out=dict(status='PASS',models=3,lods=9,capsuleRecipes=6,protectedFiles=len(protected),changedProtectedFiles=changed,rows=result,
         unity='NOT RUN: Blender-only approval step; no Unity lock, import or scene changes',wind='Staged existing V19Wind generic material bindings; motion and per-instance stiffness verification await integration approval')
(ROOT/'fbx_roundtrip_v04_04.json').write_text(json.dumps(out,indent=2))
print('ROUNDTRIP_PASS',len(result),'meshes;',len(protected),'protected files unchanged',flush=True)




