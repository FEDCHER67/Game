import bpy
import json
from pathlib import Path
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
source = root / 'Working' / 'Tripo' / 'pink brain 3d model.fbx'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(source))

def describe(label):
    result = []
    for obj in bpy.data.objects:
        record = {'name': obj.name, 'type': obj.type, 'location': list(obj.location),
                  'rotation_euler': list(obj.rotation_euler), 'scale': list(obj.scale)}
        if obj.type == 'MESH':
            world = [obj.matrix_world @ Vector(v) for v in obj.bound_box]
            record.update(vertices=len(obj.data.vertices), polygons=len(obj.data.polygons),
                          triangles=sum(len(p.vertices)-2 for p in obj.data.polygons),
                          materials=[m.name if m else None for m in obj.data.materials],
                          bounds=[[min(v[i] for v in world), max(v[i] for v in world)] for i in range(3)],
                          smooth_faces=sum(p.use_smooth for p in obj.data.polygons))
        result.append(record)
    print(label + '=' + json.dumps(result))

describe('BRAIN_OBJECTS')
for mat in bpy.data.materials:
    print('BRAIN_MATERIAL=' + json.dumps({'name': mat.name, 'diffuse_color': list(mat.diffuse_color),
                                          'roughness': mat.roughness,
                                          'nodes': [(n.name, n.type, {i.name: (list(i.default_value) if hasattr(i.default_value, '__len__') else i.default_value) for i in n.inputs if i.name in ('Base Color','Roughness','Specular IOR Level','Metallic','Coat Weight','Diffuse Roughness')}) for n in mat.node_tree.nodes] if mat.use_nodes else []}))

bpy.ops.wm.open_mainfile(filepath=str(root.parent / 'KIDNEY-ASTRA-001' / 'KIDNEY-ASTRA-001.blend'))
describe('KIDNEY_OBJECTS')
for mat in bpy.data.materials:
    if mat.name.startswith(('Kidney','Tube')):
        print('KIDNEY_MATERIAL=' + json.dumps({'name': mat.name, 'diffuse_color': list(mat.diffuse_color), 'roughness': mat.roughness,
            'nodes': [(n.name, {i.name: (list(i.default_value) if hasattr(i.default_value, '__len__') else i.default_value) for i in n.inputs if i.name in ('Base Color','Roughness','Specular IOR Level','Metallic','Coat Weight','Diffuse Roughness')}) for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED']}))

bpy.ops.wm.open_mainfile(filepath=str(root.parent / 'HEART-ASTRA-007' / 'Working' / 'Heart_Astra_007_v6.blend'))
print('HEART_SCENE=' + json.dumps({'camera': bpy.context.scene.camera.name if bpy.context.scene.camera else None,
                                    'render_engine': bpy.context.scene.render.engine,
                                    'world_color': list(bpy.context.scene.world.color) if bpy.context.scene.world else None}))
for mat in bpy.data.materials:
    if mat.use_nodes:
        print('HEART_MATERIAL=' + json.dumps({'name': mat.name, 'roughness': mat.roughness,
            'nodes': [(n.name, {i.name: (list(i.default_value) if hasattr(i.default_value, '__len__') else i.default_value) for i in n.inputs if i.name in ('Base Color','Roughness','Specular IOR Level','Metallic','Coat Weight','Diffuse Roughness')}) for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED']}))
