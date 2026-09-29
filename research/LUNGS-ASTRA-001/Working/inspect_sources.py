import bpy
import json
import os
import sys
import tempfile
import zipfile
import io
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'Working', 'Tripo', 'lungs_tripo_base.fbx')
DONOR_ZIP = os.path.join(ROOT, 'Working', 'DonorAnimation', 'lungs_motion_donor.zip')
OUT = os.path.join(ROOT, 'Working', 'source_inspection.json')

with zipfile.ZipFile(DONOR_ZIP) as outer:
    with zipfile.ZipFile(io.BytesIO(outer.read(outer.namelist()[0]))) as inner:
        donor_data = inner.read(inner.namelist()[0])
donor_path = os.path.join(tempfile.gettempdir(), 'lungs_motion_donor_inspect.fbx')
with open(donor_path, 'wb') as stream:
    stream.write(donor_data)

def inspect(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    result = {'path': path, 'objects': [], 'materials': [], 'actions': [], 'scene_fps': bpy.context.scene.render.fps}
    for obj in bpy.data.objects:
        entry = {'name': obj.name, 'type': obj.type, 'parent': obj.parent.name if obj.parent else None,
                 'location': list(obj.location), 'rotation': list(obj.rotation_euler), 'scale': list(obj.scale)}
        if obj.type == 'MESH':
            mesh = obj.data
            world = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
            entry.update(vertices=len(mesh.vertices), polygons=len(mesh.polygons), triangles=sum(len(p.vertices)-2 for p in mesh.polygons),
                         materials=[m.name if m else None for m in mesh.materials],
                         bounds_min=[min(v[i] for v in world) for i in range(3)], bounds_max=[max(v[i] for v in world) for i in range(3)],
                         shape_keys=[{'name': k.name, 'value': k.value} for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
                         modifiers=[{'name': m.name, 'type': m.type} for m in obj.modifiers])
            if mesh.shape_keys and mesh.shape_keys.animation_data:
                entry['shape_animation'] = str(mesh.shape_keys.animation_data.action)
        if obj.type == 'ARMATURE':
            entry['bones'] = [bone.name for bone in obj.data.bones]
        if obj.animation_data:
            entry['animation'] = {'action': obj.animation_data.action.name if obj.animation_data.action else None,
                                  'nla': [{'name': t.name, 'strips': [{'name': s.name, 'action': s.action.name if s.action else None,
                                                                       'start': s.frame_start, 'end': s.frame_end} for s in t.strips]} for t in obj.animation_data.nla_tracks]}
        result['objects'].append(entry)
    for mat in bpy.data.materials:
        result['materials'].append({'name': mat.name, 'diffuse_color': list(mat.diffuse_color), 'roughness': mat.roughness,
                                    'nodes': [{'type': n.type, 'name': n.name} for n in mat.node_tree.nodes] if mat.use_nodes else []})
    for action in bpy.data.actions:
        item = {'name': action.name, 'frame_range': list(action.frame_range), 'fcurves': []}
        try:
            for fc in action.fcurves:
                item['fcurves'].append({'path': fc.data_path, 'index': fc.array_index,
                                        'keys': [[kp.co.x, kp.co.y] for kp in fc.keyframe_points[:12]]})
        except AttributeError:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for fc in bag.fcurves:
                            item['fcurves'].append({'path': fc.data_path, 'index': fc.array_index,
                                                    'keys': [[kp.co.x, kp.co.y] for kp in fc.keyframe_points[:12]]})
        result['actions'].append(item)
    return result

data = {'base': inspect(BASE), 'donor': inspect(donor_path)}
with open(OUT, 'w', encoding='utf-8') as stream:
    json.dump(data, stream, indent=2)
print('WROTE', OUT)
