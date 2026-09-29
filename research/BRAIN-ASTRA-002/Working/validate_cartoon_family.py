"""Reopen the brain source and reimport its FBX; verify geometry and materials."""
import bmesh
import bpy
import hashlib
import json
import math
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / 'Working' / 'BeforeCartoonFamilyPass' / 'BRAIN-ASTRA-002.blend'
FINAL = ROOT / 'BRAIN-ASTRA-002.blend'
FBX = ROOT / 'BRAIN-ASTRA-002.fbx'


def inspect():
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(meshes) == 1
    obj = meshes[0]
    mesh = obj.data
    digest = hashlib.sha256()
    for vertex in mesh.vertices:
        digest.update(struct.pack('<3f', *vertex.co))
    for poly in mesh.polygons:
        digest.update(struct.pack('<i', len(poly.vertices)))
        for index in poly.vertices:
            digest.update(struct.pack('<i', index))
    for row in obj.matrix_world:
        digest.update(struct.pack('<4f', *row))
    bm = bmesh.new()
    bm.from_mesh(mesh)
    boundary = sum(e.is_boundary for e in bm.edges)
    nonmanifold = sum(not e.is_manifold for e in bm.edges)
    degenerate = sum(f.calc_area() < 1e-12 for f in bm.faces)
    bm.free()
    mats = []
    for mat in mesh.materials:
        shader = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        mats.append({
            'name': mat.name,
            'base_color': [round(float(v), 5) for v in mat.diffuse_color],
            'roughness': round(float(mat.roughness), 5),
            'shader_roughness': round(float(shader.inputs['Roughness'].default_value), 5) if shader else None,
            'specular_ior_level': round(float(shader.inputs['Specular IOR Level'].default_value), 5) if shader else None,
        })
    bounds = [
        [round(min(v.co[i] for v in mesh.vertices), 6), round(max(v.co[i] for v in mesh.vertices), 6)]
        for i in range(3)
    ]
    return {
        'name': obj.name,
        'mesh_count': len(meshes),
        'vertices': len(mesh.vertices),
        'triangles': sum(len(p.vertices)-2 for p in mesh.polygons),
        'polygons': len(mesh.polygons),
        'smooth_faces': sum(p.use_smooth for p in mesh.polygons),
        'boundary_edges': boundary,
        'nonmanifold_edges': nonmanifold,
        'degenerate_faces': degenerate,
        'finite_vertices': all(all(math.isfinite(c) for c in v.co) for v in mesh.vertices),
        'bounds': bounds,
        'geometry_hash': digest.hexdigest(),
        'material_faces': [sum(p.material_index == i for p in mesh.polygons) for i in range(len(mats))],
        'materials': mats,
    }


bpy.ops.wm.open_mainfile(filepath=str(BEFORE))
before = inspect()
bpy.ops.wm.open_mainfile(filepath=str(FINAL))
final = inspect()
assert final['geometry_hash'] == before['geometry_hash']
for field in ('vertices', 'triangles', 'polygons', 'smooth_faces', 'boundary_edges', 'nonmanifold_edges', 'bounds'):
    assert final[field] == before[field], field
assert final['vertices'] == 4138 and final['triangles'] == 8296
assert final['material_faces'][1] > 100
assert all(m['roughness'] >= 0.86 and m['specular_ior_level'] == 0 for m in final['materials'])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(FBX))
fbx = inspect()
for field in ('vertices', 'triangles', 'boundary_edges', 'nonmanifold_edges', 'bounds', 'material_faces'):
    assert fbx[field] == final[field], field
assert [(m['name'], m['base_color'], m['roughness']) for m in fbx['materials']] == [
    (m['name'], m['base_color'], m['roughness']) for m in final['materials']]
assert fbx['finite_vertices'] and fbx['degenerate_faces'] == 0

output = {
    'blender': bpy.app.version_string,
    'before': before,
    'final_blend_reopen': final,
    'fbx_reimport': fbx,
    'geometry_unchanged': True,
}
out_path = ROOT / 'Working' / 'cartoon_validation.json'
out_path.write_text(json.dumps(output, indent=2), encoding='utf-8')
print('BRAIN_VALIDATION', json.dumps({
    'geometry_unchanged': True,
    'vertices': final['vertices'],
    'triangles': final['triangles'],
    'material_faces': final['material_faces'],
    'materials': final['materials'],
    'fbx_reimport': True,
}))
