"""Read-only mesh and FBX validation for KIDNEY-ASTRA-001."""

import bpy
import bmesh
import json
import math
import os
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(os.environ.get('ASTRA_OUTPUT_ROOT',
    r'C:\Dev\Game\_worktrees\fedya-player-v2\research\KIDNEY-ASTRA-001'))
bpy.ops.wm.open_mainfile(filepath=str(root / 'KIDNEY-ASTRA-001.blend'))
collection = bpy.data.collections['KIDNEY-ASTRA-001 | Game Assembly']
objects = sorted((o for o in collection.objects if o.type == 'MESH'), key=lambda o: o.name)
summary = {'objects': [], 'materials': sorted({m.name for o in objects for m in o.data.materials if m})}
all_bounds = []
for o in objects:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    nonmanifold = sum(1 for e in bm.edges if not e.is_manifold)
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-12)
    signed_volume = bm.calc_volume(signed=True)
    bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm)
    self_intersections = 0
    for a, b in tree.overlap(tree):
        if a >= b:
            continue
        if not set(bm.faces[a].verts).intersection(bm.faces[b].verts):
            self_intersections += 1
    bm.free()
    bounds = [o.matrix_world @ Vector(corner) for corner in o.bound_box]
    all_bounds.extend(bounds)
    summary['objects'].append({
        'name': o.name,
        'vertices': len(o.data.vertices),
        'triangles': sum(len(p.vertices)-2 for p in o.data.polygons),
        'boundary_edges': boundary,
        'nonmanifold_edges': nonmanifold,
        'degenerate_faces': degenerate,
        'self_intersection_pairs': self_intersections,
        'signed_volume': round(signed_volume, 9),
        'uv_layers': [x.name for x in o.data.uv_layers],
        'material_slots': [m.name if m else None for m in o.data.materials],
        'identity_transform': tuple(round(x, 8) for row in o.matrix_world for x in row) == (1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0),
    })
summary['total_vertices'] = sum(r['vertices'] for r in summary['objects'])
summary['total_triangles'] = sum(r['triangles'] for r in summary['objects'])
summary['bounds_min'] = [round(min(v[i] for v in all_bounds), 5) for i in range(3)]
summary['bounds_max'] = [round(max(v[i] for v in all_bounds), 5) for i in range(3)]
summary['render_camera'] = bpy.context.scene.camera.name if bpy.context.scene.camera else None
print('ASTRA_BLEND_QA', json.dumps(summary, sort_keys=True))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root / 'KIDNEY-ASTRA-001.fbx'))
fbx_meshes = [o for o in bpy.data.objects if o.type == 'MESH']
fbx = {
    'objects': sorted(o.name for o in fbx_meshes),
    'vertices': sum(len(o.data.vertices) for o in fbx_meshes),
    'triangles': sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in fbx_meshes),
    'materials': sorted({m.name for o in fbx_meshes for m in o.data.materials if m}),
    'uv_missing': [o.name for o in fbx_meshes if not o.data.uv_layers],
}
print('ASTRA_FBX_QA', json.dumps(fbx, sort_keys=True))
