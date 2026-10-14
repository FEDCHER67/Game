import bpy,json,math
from pathlib import Path
from mathutils import Vector
root=Path(__file__).parent
expected=json.loads((root/'validation_v04_03.json').read_text());bindings=json.loads((root/'wind_bindings_v04_03.json').read_text())
result=[]
for spec in expected['variants']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(root/'Models'/(spec['id']+'_v04_03.fbx')))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];assert len(meshes)==3
    for ob in meshes:
        lod=int(ob.name.rsplit('LOD',1)[1]);old=next(r for r in expected['lods'] if r['variant']==spec['id'] and r['lod']==lod)
        verts=[ob.matrix_world@v.co for v in ob.data.vertices]
        dims=[max(v[k] for v in verts)-min(v[k] for v in verts) for k in range(3)]
        count=sum(len(p.vertices)-2 for p in ob.data.polygons)
        assert count==old['triangles'],(ob.name,count,old['triangles'])
        assert max(abs(a-b) for a,b in zip(dims,old['dimensions_m']))<.001,(ob.name,dims)
        assert min(v.z for v in verts)>-.001 and min(v.z for v in verts)<.001,(ob.name,'pivot/base')
        assert ob.matrix_world.translation.length<.001,(ob.name,'origin')
        assert all(m.name in bindings['material_remaps'][spec['family']] for m in ob.data.materials),(ob.name,[m.name for m in ob.data.materials])
        import bmesh
        bm=bmesh.new();bm.from_mesh(ob.data);bad=sum(not e.is_manifold for e in bm.edges);bm.free();assert bad==0,(ob.name,bad)
        result.append(dict(model=ob.name,lod=lod,triangles=count,dimensions_m=dims,material_bindings='complete',base_pivot='pass',closed_geometry='pass'))
(root/'fbx_roundtrip_v04_03.json').write_text(json.dumps({'status':'PASS','meshes':len(result),'method':'Separate background Blender factory scenes; each FBX reimported and compared in world metres to native-source dimensions/topology, origin/base and material recipe coverage. Unity import deferred for approval.','rows':result},indent=2))
print('ROUNDTRIP_PASS',len(result),flush=True)
