import bpy
import json
import sys
from mathutils import Vector

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
source = sys.argv[sys.argv.index('--') + 1]
bpy.ops.import_scene.fbx(filepath=source)
report = []
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    points = [obj.matrix_world @ v.co for v in obj.data.vertices]
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    mats = {m.name: [] for m in obj.data.materials if m}
    for poly in obj.data.polygons:
        if poly.material_index < len(obj.data.materials):
            m = obj.data.materials[poly.material_index]
            if m:
                mats[m.name].extend(poly.vertices)
    material_bounds = {}
    for name, inds in mats.items():
        subset = [points[i] for i in set(inds)]
        if subset:
            material_bounds[name] = {
                'count': len(subset),
                'min': [min(p[i] for p in subset) for i in range(3)],
                'max': [max(p[i] for p in subset) for i in range(3)],
            }
    report.append({
        'name': obj.name, 'vertices': len(points), 'faces': len(obj.data.polygons),
        'triangles': sum(len(p.vertices)-2 for p in obj.data.polygons),
        'bounds': {'min': [min(xs), min(ys), min(zs)], 'max': [max(xs), max(ys), max(zs)]},
        'materials': material_bounds,
        'transform': {'location': list(obj.location), 'rotation': list(obj.rotation_euler), 'scale': list(obj.scale)},
    })
print('SOURCE_INSPECTION=' + json.dumps(report))
