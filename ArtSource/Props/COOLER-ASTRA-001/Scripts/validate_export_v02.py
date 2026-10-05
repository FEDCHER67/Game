import bpy, bmesh, json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(r'C:\Dev\Game\ArtSource\Props\COOLER-ASTRA-001')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root / 'COOLER_ASTRA_001_v02.fbx'))
rows, contacts = [], []
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH':
        continue
    me = ob.data
    me.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(me)
    pending = set(bm.verts)
    parts = []
    while pending:
        seed = pending.pop()
        part, stack = [seed], [seed]
        while stack:
            v = stack.pop()
            for e in v.link_edges:
                other = e.other_vert(v)
                if other in pending:
                    pending.remove(other)
                    part.append(other)
                    stack.append(other)
        parts.append(part)
    body = max(parts, key=len)
    body_index = {v: i for i, v in enumerate(body)}
    body_faces = {f for v in body for f in v.link_faces}
    body_bvh = BVHTree.FromPolygons(
        [ob.matrix_world @ v.co for v in body],
        [[body_index[v] for v in f.verts] for f in body_faces])
    for part in parts:
        coords = [ob.matrix_world @ v.co for v in part]
        zmax = max(v.z for v in coords)
        if zmax < .02:
            cx = sum(v.x for v in coords) / len(coords)
            cy = sum(v.y for v in coords) / len(coords)
            hit, normal, index, distance = body_bvh.ray_cast(
                Vector((cx, cy, -1)), Vector((0, 0, 1)))
            contacts.append({'centre_m': [cx, cy],
                             'foot_top_m': zmax,
                             'body_bottom_m': hit.z if hit else None,
                             'overlap_m': zmax - hit.z if hit else None})
    coords = [ob.matrix_world @ v.co for v in me.vertices]
    dims = [max(v[i] for v in coords) - min(v[i] for v in coords)
            for i in range(3)]
    rows.append({'object': ob.name, 'triangles': len(me.loop_triangles),
                 'faces': len(me.polygons),
                 'nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
                 'boundary_edges': sum(e.is_boundary for e in bm.edges),
                 'zero_area_faces': sum(f.calc_area() < 1e-12 for f in bm.faces),
                 'uv_layers': len(me.uv_layers), 'mesh_islands': len(parts),
                 'dimensions_m': dims})
    bm.free()
images = [{'name': i.name, 'width': i.size[0], 'height': i.size[1],
           'has_data': i.has_data} for i in bpy.data.images]
report = {'objects': rows, 'total_triangles': sum(r['triangles'] for r in rows),
          'textures': images, 'foot_contacts_after_export': contacts}
report['pass'] = (
    len(rows) == 1 and 500 <= report['total_triangles'] <= 900
    and all(r['nonmanifold_edges'] == 0 and r['zero_area_faces'] == 0
            and r['uv_layers'] > 0 for r in rows)
    and any(i['has_data'] and i['width'] == 2048 and i['height'] == 2048
            for i in images)
    and len(contacts) == 4
    and all(c['overlap_m'] is not None and c['overlap_m'] > 0
            for c in contacts))
(root / 'Validation/fbx_roundtrip_v02.json').write_text(json.dumps(report, indent=2))
mesh_report = json.loads((root / 'Validation/mesh_v02.json').read_text())
mesh_report['dimensions_m'] = rows[0]['dimensions_m']
mesh_report['foot_contacts_after_export'] = contacts
(root / 'Validation/mesh_v02.json').write_text(json.dumps(mesh_report, indent=2))
print(json.dumps(report))
assert report['pass'], report
