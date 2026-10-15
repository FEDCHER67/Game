import bpy,json,collections,hashlib
from pathlib import Path
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pine_tall_v02'
expected=json.loads((ROOT/'validation_v03.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Cozy_PineTall_v03.blend'))
with bpy.data.libraries.load(str(OLD/'Cozy_PineTall_v02.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith(('SM_PineTall_','COL_PineTall_'))]
old_objects={o.name:o for o in dst.objects}
for ob in old_objects.values():bpy.context.scene.collection.objects.link(ob)
bpy.context.view_layer.update()
def wood_vertices(obj):
    ids={i for p in obj.data.polygons if obj.data.materials[p.material_index].name.startswith('MAT_Bark') for i in p.vertices}
    return {tuple(v.co) for v in obj.data.vertices if v.index in ids}
rows=[]
for spec in expected['variants']:
    assert 15<=spec['branchIncreasePercent']<=20 and spec['leafPlatesPerClump']==17
    for lod in range(3):
        ob=bpy.data.objects[f'SM_{spec["id"]}_v03_LOD{lod}'];old=old_objects[f'SM_{spec["id"]}_v02_LOD{lod}']
        assert wood_vertices(old)<=wood_vertices(ob)
        adjacency=collections.defaultdict(set)
        for p in ob.data.polygons:
            if ob.data.materials[p.material_index].name.startswith('MAT_Bark'):continue
            for i in p.vertices:adjacency[i].update(p.vertices)
        unseen=set(adjacency);components=0
        while unseen:
            stack=[unseen.pop()];components+=1
            while stack:
                v=stack.pop()
                for n in adjacency[v]:
                    if n in unseen:unseen.remove(n);stack.append(n)
        row=next(r for r in expected['lods'] if r['id']==spec['id'] and r['lod']==lod)
        assert components==row['leafPlates'],(components,row['leafPlates'])
        rows.append(dict(model=ob.name,leafComponents=components,expectedClumps=row['clusters'],platesPerClump=row['leafPlatesPerClump'],oldWoodyVerticesPreserved=True))
    for i in (1,2):
        current=bpy.data.objects[f'COL_{spec["id"]}_Trunk_{i}_v03'];previous=old_objects[f'COL_{spec["id"]}_Trunk_{i}_v02']
        assert max(abs(current.matrix_world[i][j]-previous.matrix_world[i][j]) for i in range(4) for j in range(4))<1e-6
        assert [tuple(v.co) for v in current.data.vertices]==[tuple(v.co) for v in previous.data.vertices]
assert json.loads((ROOT/'wind_bindings_v03.json').read_text())==json.loads((OLD/'wind_bindings_v02.json').read_text())
bindings=json.loads((ROOT/'wind_bindings_v03.json').read_text())
for value in bindings['material_remaps']['PineTall'].values():assert (ROOT/value).is_file(),value
(ROOT/'branch_validation_v03.json').write_text(json.dumps(dict(status='PASS',rows=rows,capsuleGeometryAndTransforms='unchanged',windBindings='unchanged',base='PineTall v02'),indent=2))
print('BRANCH_VALIDATION_PASS: all nine leaf counts; old wood, six capsules and wind bindings preserved',flush=True)
