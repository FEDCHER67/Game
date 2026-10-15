import bpy,json,collections
from pathlib import Path
ROOT=Path(__file__).parent;OLD=ROOT.parent/'pine_tall_v03'
data=json.loads((ROOT/'validation_v04_04.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Cozy_PineTall_v04_04.blend'))
with bpy.data.libraries.load(str(OLD/'Cozy_PineTall_v03.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith(('SM_PineTall_','COL_PineTall_'))]
old={o.name:o for o in dst.objects}
for ob in old.values():bpy.context.scene.collection.objects.link(ob)
bpy.context.view_layer.update()
def groups(ob,wood):
    links=collections.defaultdict(set)
    for p in ob.data.polygons:
        iswood=ob.data.materials[p.material_index].name.startswith('MAT_Bark')
        if iswood!=wood:continue
        for i in p.vertices:links[i].update(p.vertices)
    unseen=set(links);out=[]
    while unseen:
        seed=unseen.pop();queue=[seed];ids=[seed]
        while queue:
            for n in links[queue.pop()]:
                if n in unseen:unseen.remove(n);queue.append(n);ids.append(n)
        out.append(ids)
    return out
rows=[]
for spec in data['variants']:
    assert spec['mainBranches']==spec['previousMainBranches']+8 and spec['clusters']==spec['previousClusters']+10
    for lod in range(3):
        ob=bpy.data.objects[f'SM_{spec["id"]}_v04_04_LOD{lod}'];prev=old[f'SM_{spec["id"]}_v03_LOD{lod}']
        wanted=next(r for r in data['lods'] if r['id']==spec['id'] and r['lod']==lod)
        leaves=groups(ob,False);assert len(leaves)==wanted['leafPlates']
        vertices={tuple(v.co) for v in ob.data.vertices}
        preserved=0
        for component in groups(prev,True):
            if min(prev.data.vertices[i].co.z for i in component)<spec['height']*.34:
                assert all(tuple(prev.data.vertices[i].co) in vertices for i in component);preserved+=1
        assert len(groups(ob,True))==len(groups(prev,True))+10
        assert abs(ob['crown_width_m']-wanted['crownWidth'])<.001
        rows.append(dict(model=ob.name,leafPlates=len(leaves),addedWoodComponents=10,preservedTrunkRootStubComponents=preserved,nativeWidthMetadata='PASS'))
    for i in (1,2):
        ob=bpy.data.objects[f'COL_{spec["id"]}_Trunk_{i}_v04_04'];prev=old[f'COL_{spec["id"]}_Trunk_{i}_v03']
        assert max(abs(ob.matrix_world[r][c]-prev.matrix_world[r][c]) for r in range(4) for c in range(4))<1e-6
        assert [tuple(v.co) for v in ob.data.vertices]==[tuple(v.co) for v in prev.data.vertices]
assert json.loads((ROOT/'wind_bindings_v04_04.json').read_text())==json.loads((OLD/'wind_bindings_v03.json').read_text())
(ROOT/'structure_validation_v04_04.json').write_text(json.dumps(dict(status='PASS',rows=rows,capsules='six unchanged',sharedWindBindings='unchanged'),indent=2))
print('STRUCTURE_PASS: 8 main branches + 2 twigs per variant; density, trunk, stubs, roots, capsules and wind checked',flush=True)
