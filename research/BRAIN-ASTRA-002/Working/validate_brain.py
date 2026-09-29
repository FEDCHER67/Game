"""Read-back validation for the finished source and export."""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parents[1]

def inspect(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bad_faces = sum(face.calc_area() < 1e-12 for face in bm.faces)
    boundaries = sum(edge.is_boundary for edge in bm.edges)
    nonmanifold = sum(not edge.is_manifold for edge in bm.edges)
    bm.free()
    bounds = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    return {
        'name': obj.name, 'vertices': len(obj.data.vertices),
        'triangles': sum(len(poly.vertices)-2 for poly in obj.data.polygons),
        'smooth_faces': sum(poly.use_smooth for poly in obj.data.polygons),
        'boundary_edges': boundaries, 'nonmanifold_edges': nonmanifold,
        'degenerate_faces': bad_faces,
        'finite_vertices': all(all(math.isfinite(x) for x in v.co) for v in obj.data.vertices),
        'dimensions': [round(max(v[i] for v in bounds)-min(v[i] for v in bounds), 6) for i in range(3)],
        'location': list(obj.location), 'rotation': list(obj.rotation_euler), 'scale': list(obj.scale),
        'materials': [mat.name for mat in obj.data.materials],
    }

bpy.ops.wm.open_mainfile(filepath=str(root / 'BRAIN-ASTRA-002.blend'))
asset = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
print('BLEND=' + json.dumps([inspect(obj) for obj in asset]))
print('SCENE=' + json.dumps({'camera': bpy.context.scene.camera.name if bpy.context.scene.camera else None,
                             'lights': len([obj for obj in bpy.context.scene.objects if obj.type == 'LIGHT']),
                             'material': {
                                 'roughness': asset[0].active_material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value,
                                 'specular': asset[0].active_material.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value,
                                 'diffuse_roughness': asset[0].active_material.node_tree.nodes['Principled BSDF'].inputs['Diffuse Roughness'].default_value,
                                 'base_color': list(asset[0].active_material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value),
                             }}))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root / 'BRAIN-ASTRA-002.fbx'))
print('FBX=' + json.dumps([inspect(obj) for obj in bpy.context.scene.objects if obj.type == 'MESH']))
print('FBX_MATERIAL=' + json.dumps([{'name': mat.name, 'roughness': mat.roughness,
    'base_color': list(mat.diffuse_color)} for mat in bpy.data.materials]))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root / 'Working' / 'Tripo' / 'pink brain 3d model.fbx'))
print('SOURCE=' + json.dumps([inspect(obj) for obj in bpy.context.scene.objects if obj.type == 'MESH']))
