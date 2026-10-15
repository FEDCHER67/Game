"""Validate only three new poplar FBXs and retained v04_03 deliverables."""
import bpy
import bmesh
import hashlib
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).parent
expected = json.loads((ROOT / 'validation_v04_04.json').read_text())
baseline = json.loads((ROOT / 'validation_v04_03.json').read_text())
bindings = json.loads((ROOT / 'wind_bindings_v04_03.json').read_text())
result = []
for spec in expected['variants']:
    old_spec = next(s for s in baseline['variants'] if s['id'] == spec['variant'])
    assert old_spec['collider'] == spec['collider'], 'Collider recipe changed'
    bpy.ops.wm.read_factory_settings(use_empty=True)
    path = ROOT / 'Models' / (spec['variant'] + '_v04_04.fbx')
    bpy.ops.import_scene.fbx(filepath=str(path))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(meshes) == 3
    for ob in meshes:
        lod = int(ob.name.rsplit('LOD', 1)[1])
        wanted = next(r for r in expected['lods'] if r['variant'] == spec['variant'] and r['lod'] == lod)
        verts = [ob.matrix_world @ v.co for v in ob.data.vertices]
        dims = [max(v[k] for v in verts) - min(v[k] for v in verts) for k in range(3)]
        count = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        assert count == wanted['triangles'], (ob.name, count)
        assert max(abs(a-b) for a,b in zip(dims, wanted['dimensions_m'])) < .001
        assert abs(min(v.z for v in verts)) < .001
        assert ob.matrix_world.translation.length < .001
        assert all(abs(v - 1) < .001 for v in ob.scale)
        assert all(m.name in bindings['material_remaps']['Poplar'] for m in ob.data.materials)
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bad = sum(not e.is_manifold for e in bm.edges)
        loose = sum(not v.link_edges for v in bm.verts)
        bm.free()
        assert not bad and not loose
        assert not any(p.area < 1e-10 for p in ob.data.polygons)
        assert len(ob.data.uv_layers) == 1
        result.append(dict(model=ob.name, lod=lod, triangles=count, dimensions_m=dims,
                           base_pivot='PASS', unit_scale='PASS', closed_geometry='PASS',
                           original_material_remap='PASS', uv='PASS'))

for path, digest in expected['protected_files'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path
old_sheet = ROOT.parents[3] / 'Working/Reviews/Trees/leafy_trees_v04.png'
assert hashlib.sha256(old_sheet.read_bytes()).hexdigest() == expected['approved_sheet_sha256']

# Native-file comparison verifies original model/collider meshes survive the
# save/load cycle unchanged, in addition to the file hashes above.
def signature(ob):
    content = {'vertices': [list(v.co) for v in ob.data.vertices],
               'polygons': [(list(p.vertices), p.material_index) for p in ob.data.polygons],
               'uv': [[list(v.uv) for v in layer.data] for layer in ob.data.uv_layers],
               'materials': [m.name for m in ob.data.materials],
               'transform': [list(v) for v in ob.matrix_world],
               'properties': {k:str(ob[k]) for k in ob.keys()}}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Leafy_Trees_v04_03.blend'))
original = {o.name: signature(o) for o in bpy.data.objects
            if o.type == 'MESH' and (o.name.startswith('SM_') or o.name.startswith('COL_'))}
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Leafy_Trees_v04_04.blend'))
assert all(signature(bpy.data.objects[n]) == digest for n,digest in original.items())
profiles = []
for letter in 'ABC':
    old = bpy.data.objects[f'SM_Poplar_{letter}_v04_03_LOD0']
    new = bpy.data.objects[f'SM_Poplar_{letter}_v04_04_LOD0']
    def foliage(ob):
        indices = {i for p in ob.data.polygons if p.material_index > 0 for i in p.vertices}
        return [ob.data.vertices[i].co for i in indices]
    a,b = foliage(old), foliage(new)
    low,high = min(v.z for v in a), max(v.z for v in a)
    thirds = []
    for third in range(3):
        z0,z1 = low+(high-low)*third/3, low+(high-low)*(third+1)/3
        def width(vs):
            section = [v for v in vs if z0-1e-5 <= v.z <= z1+1e-5]
            return max(max(v[k] for v in section)-min(v[k] for v in section) for k in (0,1))
        before,after = width(a), width(b)
        thirds.append(dict(third=('lower','middle','upper')[third], before_m=before,
                           after_m=after, increase_percent=(after/before-1)*100))
    profiles.append(dict(variant=letter, thirds=thirds, visible_trunk_to_first_leaf_m=low))

report = dict(status='PASS', meshes=len(result), rows=result, width_profiles=profiles,
              old_files_unchanged=len(expected['protected_files']), old_native_models_colliders_unchanged=len(original),
              approved_apple_palm_bush='PASS - original source geometry and all exports unchanged; no rebuild/re-export',
              collider_recipe='PASS - exact v04_03 capsule values retained', shared_wind='PASS - original material slots/remap retained',
              unity='NOT RUN - excluded by user; no lock or scene operations')
(ROOT / 'fbx_roundtrip_v04_04.json').write_text(json.dumps(report, indent=2))
print('ROUNDTRIP_PASS', len(result), 'PROTECTED_FILES', len(expected['protected_files']), flush=True)
print('WIDTH_PROFILES', json.dumps(profiles), flush=True)
