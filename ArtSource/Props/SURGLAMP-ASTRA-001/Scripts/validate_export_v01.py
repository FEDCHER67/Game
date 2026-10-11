import bpy, bmesh, json, math
from pathlib import Path

ROOT = Path(r'C:\Dev\Game\ArtSource\Props\SURGLAMP-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(ROOT / 'SURGLAMP_ASTRA_001_v01.fbx'))
rows = []
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    me = obj.data
    me.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.transform(obj.matrix_world)
    remaining = set(bm.verts)
    islands = 0
    while remaining:
        islands += 1
        stack = [remaining.pop()]
        while stack:
            v = stack.pop()
            for edge in v.link_edges:
                other = edge.other_vert(v)
                if other in remaining:
                    remaining.remove(other)
                    stack.append(other)
    coords = [v.co for v in bm.verts]
    rows.append({
        'object': obj.name,
        'triangles': len(me.loop_triangles),
        'vertices': len(me.vertices),
        'mesh_islands': islands,
        'nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
        'zero_area_faces': sum(f.calc_area() < 1e-12 for f in bm.faces),
        'finite_vertices': all(math.isfinite(c) for v in coords for c in v),
        'uv_layers': len(me.uv_layers),
        'finite_uvs': all(math.isfinite(c) for layer in me.uv_layers for uv in layer.data for c in uv.uv),
        'dimensions_m': [max(v[i] for v in coords) - min(v[i] for v in coords) for i in range(3)],
    })
    bm.free()
images = [{'name': im.name, 'width': im.size[0], 'height': im.size[1], 'has_data': im.has_data} for im in bpy.data.images]
report = {'objects': rows, 'total_triangles': sum(r['triangles'] for r in rows), 'textures': images}
report['pass'] = (
    len(rows) == 1 and report['total_triangles'] == 1168
    and all(r['mesh_islands'] == 14 and r['nonmanifold_edges'] == 0 and r['zero_area_faces'] == 0
            and r['finite_vertices'] and r['uv_layers'] > 0 and r['finite_uvs']
            and abs(r['dimensions_m'][2] - 1.7) < 0.0002 for r in rows)
    and any(im['has_data'] and im['width'] == 1024 and im['height'] == 1024 for im in images)
)
(ROOT / 'Validation/fbx_roundtrip_v01.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
assert report['pass']

for folder, name in [
    ('BATON-ASTRA-001', 'BATON_ASTRA_001_v02.blend'),
    ('BAT-ASTRA-001', 'BAT_ASTRA_001_v01.blend'),
    ('PAN-ASTRA-001', 'PAN_ASTRA_001_v03.blend'),
    ('TASER-ASTRA-001', 'TASER_ASTRA_001_v02.blend'),
    ('PISTOL-ASTRA-001', 'PISTOL_ASTRA_001_v01.blend'),
    ('SURGLAMP-ASTRA-001', 'SURGLAMP_ASTRA_001_v01.blend'),
]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with bpy.data.libraries.load(str(ROOT.parent / folder / name), link=False) as (src, dst):
        dst.objects = src.objects
    inventory = []
    for obj in dst.objects:
        if obj is None:
            continue
        if obj.type == 'MESH':
            obj.data.calc_loop_triangles()
            inventory.append({'name': obj.name, 'triangles': len(obj.data.loop_triangles), 'hide_render': obj.hide_render, 'hide_viewport': obj.hide_viewport})
        elif obj.type == 'CAMERA':
            inventory.append({'camera': obj.name, 'rotation': list(obj.rotation_euler)})
    print('LIBRARY', folder, json.dumps(inventory))
