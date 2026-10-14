import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path(r'C:\Dev\Game\ArtSource\Dev\Trees_staging\v03')
report=json.loads((root/'forest_validation_v03_04.json').read_text())
checks=[]
for path in sorted((root/'Models').glob('*_v03_04.fbx')):
    test=bpy.data.scenes.new('Roundtrip_'+path.stem);bpy.context.window.scene=test
    bpy.ops.import_scene.fbx(filepath=str(path))
    models=[o for o in test.objects if o.type=='MESH']
    assert len(models)==3,(path,len(models))
    for ob in models:
        variant=next(s['id'] for s in report['variants'] if 'Forest_'+s['id']+'_' in ob.name)
        lod=int(ob.name[-1]);expected=next(r for r in report['lods'] if r['variant']==variant and r['lod']==lod)
        coords=[ob.matrix_world@v.co for v in ob.data.vertices]
        low=min(v.z for v in coords);height=max(v.z for v in coords)-low
        width=max(max(v.x for v in coords)-min(v.x for v in coords),max(v.y for v in coords)-min(v.y for v in coords))
        triangles=sum(len(p.vertices)-2 for p in ob.data.polygons)
        assert abs(low)<1e-5 and abs(height-expected['height_m'])<1e-4,(ob.name,low,height)
        assert abs(width-expected['height_m']*expected['crown_ratio'])<1e-4,(ob.name,width)
        assert triangles==expected['triangles'],(ob.name,triangles)
        assert ob.data.uv_layers and min(v.uv.x for v in ob.data.uv_layers[0].data)>=-1e-5
        assert max(v.uv.x for v in ob.data.uv_layers[0].data)<=1.00001
        assert all(p.area>1e-10 for p in ob.data.polygons)
        checks.append(dict(model=ob.name,triangles=triangles,height_m=height,width_m=width,base_m=low,status='PASS',tip_uv='0..1'))
out=root/'fbx_roundtrip_v03_04.json'
if out.exists():raise RuntimeError('Never overwrite validation evidence')
out.write_text(json.dumps(checks,indent=2))
print('PASS: all 12 LOD meshes, dimensions, base pivots, triangles and frond UV masks preserved.')
