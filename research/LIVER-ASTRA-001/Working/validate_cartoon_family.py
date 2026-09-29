"""Reopen the liver blend and reimport FBX after the material-only restyle."""
import bmesh
import bpy
import hashlib
import json
import math
import struct
from pathlib import Path
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / 'Working' / 'BeforeCartoonFamilyPass' / 'LIVER-ASTRA-001.blend'
FINAL = ROOT / 'LIVER-ASTRA-001.blend'
FBX = ROOT / 'LIVER-ASTRA-001.fbx'


def inspect():
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    assert len(meshes) == 1
    obj = meshes[0]
    mesh = obj.data
    digest = hashlib.sha256()
    for vertex in mesh.vertices:
        digest.update(struct.pack('<3f', *vertex.co))
    for poly in mesh.polygons:
        digest.update(struct.pack('<ii', len(poly.vertices), poly.material_index))
        for index in poly.vertices:
            digest.update(struct.pack('<i', index))
    for row in obj.matrix_world:
        digest.update(struct.pack('<4f', *row))
    for layer in mesh.uv_layers:
        digest.update(layer.name.encode('utf-8'))
        for uv in layer.data:
            digest.update(struct.pack('<2f', *uv.uv))
    bm = bmesh.new()
    bm.from_mesh(mesh)
    boundary = sum(e.is_boundary for e in bm.edges)
    nonmanifold = sum(not e.is_manifold for e in bm.edges)
    degenerate = sum(f.calc_area() < 1e-12 for f in bm.faces)
    bm.free()
    bounds = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    mats = []
    for mat in mesh.materials:
        shader = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        mats.append({
            'name': mat.name,
            'base_color': [round(float(x), 5) for x in mat.diffuse_color],
            'roughness': round(float(mat.roughness), 5),
            'shader_roughness': round(float(shader.inputs['Roughness'].default_value), 5) if shader else None,
            'specular_ior_level': round(float(shader.inputs['Specular IOR Level'].default_value), 5) if shader else None,
        })
    return {
        'mesh_count': len(meshes),
        'name': obj.name,
        'vertices': len(mesh.vertices),
        'polygons': len(mesh.polygons),
        'triangles': sum(len(p.vertices)-2 for p in mesh.polygons),
        'smooth_faces': sum(p.use_smooth for p in mesh.polygons),
        'uv_layers': [layer.name for layer in mesh.uv_layers],
        'boundary_edges': boundary,
        'nonmanifold_edges': nonmanifold,
        'degenerate_faces': degenerate,
        'finite_vertices': all(all(math.isfinite(c) for c in v.co) for v in mesh.vertices),
        'dimensions': [round(max(v[i] for v in bounds)-min(v[i] for v in bounds), 6) for i in range(3)],
        'geometry_uv_hash': digest.hexdigest(),
        'materials': mats,
    }


bpy.ops.wm.open_mainfile(filepath=str(BEFORE))
before = inspect()
bpy.ops.wm.open_mainfile(filepath=str(FINAL))
final = inspect()
assert final['geometry_uv_hash'] == before['geometry_uv_hash']
assert final['vertices'] == 7002 and final['triangles'] == 14000
assert len(final['materials']) == 1
assert final['materials'][0]['roughness'] == 0.87
assert final['materials'][0]['specular_ior_level'] == 0.0

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(FBX))
fbx = inspect()
for key in ('name', 'vertices', 'triangles', 'smooth_faces', 'uv_layers',
            'boundary_edges', 'nonmanifold_edges', 'degenerate_faces', 'dimensions'):
    assert fbx[key] == final[key], key
assert fbx['finite_vertices']
assert [(m['name'], m['base_color'], m['roughness'], m['specular_ior_level']) for m in fbx['materials']] == [
    (m['name'], m['base_color'], m['roughness'], m['specular_ior_level']) for m in final['materials']]

output = {'blender': bpy.app.version_string, 'before': before,
          'final_blend_reopen': final, 'fbx_reimport': fbx,
          'geometry_and_uv_unchanged': True}
(ROOT / 'Working' / 'cartoon_validation.json').write_text(
    json.dumps(output, indent=2), encoding='utf-8')
print('LIVER_VALIDATION', json.dumps({
    'geometry_and_uv_unchanged': True,
    'vertices': final['vertices'], 'triangles': final['triangles'],
    'materials': final['materials'], 'fbx_reimport': True,
}))
