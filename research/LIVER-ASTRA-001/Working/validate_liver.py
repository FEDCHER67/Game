"""Read-back inspection of the finished liver Blender source and FBX."""
import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

root = Path(__file__).resolve().parents[1]

def inspect(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = {
        'name': obj.name,
        'vertices': len(obj.data.vertices),
        'triangles': sum(len(p.vertices)-2 for p in obj.data.polygons),
        'materials': [m.name for m in obj.data.materials],
        'uv_layers': [uv.name for uv in obj.data.uv_layers],
        'smooth_faces': sum(p.use_smooth for p in obj.data.polygons),
        'boundary_edges': sum(e.is_boundary for e in bm.edges),
        'nonmanifold_edges': sum(not e.is_manifold for e in bm.edges),
        'degenerate_faces': sum(f.calc_area() < 1e-12 for f in bm.faces),
        'finite_vertices': all(all(math.isfinite(x) for x in v.co) for v in obj.data.vertices),
        'location': list(obj.location), 'rotation': list(obj.rotation_euler), 'scale': list(obj.scale),
    }
    corners = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
    result['dimensions'] = [round(max(v[i] for v in corners)-min(v[i] for v in corners), 6) for i in range(3)]
    bm.free()
    return result

bpy.ops.wm.open_mainfile(filepath=str(root / 'LIVER-ASTRA-001.blend'))
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == 'MESH']
print('BLEND=' + json.dumps([inspect(o) for o in meshes]))
material = meshes[0].active_material
node = material.node_tree.nodes['Principled BSDF']
print('MATERIAL=' + json.dumps({'name': material.name, 'base_color': list(node.inputs['Base Color'].default_value),
    'roughness': node.inputs['Roughness'].default_value,
    'specular': node.inputs['Specular IOR Level'].default_value,
    'diffuse_roughness': node.inputs['Diffuse Roughness'].default_value,
    'metallic': node.inputs['Metallic'].default_value,
    'coat': node.inputs['Coat Weight'].default_value,
    'image_textures': sum(n.type == 'TEX_IMAGE' for n in material.node_tree.nodes),
    'lights': len([o for o in scene.objects if o.type == 'LIGHT']),
    'camera': scene.camera.name if scene.camera else None}))
print('DATABLOCKS=' + json.dumps({'materials': [m.name for m in bpy.data.materials],
    'images': [i.name for i in bpy.data.images],
    'mesh_datablocks': [m.name for m in bpy.data.meshes]}))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root / 'LIVER-ASTRA-001.fbx'))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
print('FBX=' + json.dumps([inspect(o) for o in meshes]))
print('FBX_MATERIAL=' + json.dumps([{'name': m.name, 'base_color': list(m.diffuse_color),
    'roughness': m.roughness} for m in bpy.data.materials]))
