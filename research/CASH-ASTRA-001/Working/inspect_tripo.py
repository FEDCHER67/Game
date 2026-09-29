import bpy
import json
import math
from mathutils import Vector

ROOT = r"C:\Dev\Game-main\research\CASH-ASTRA-001"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=ROOT + r"\Working\Tripo\cash_tripo_base.fbx")
bpy.context.view_layer.update()
report = []
for obj in bpy.context.scene.objects:
    item = {"name": obj.name, "type": obj.type,
            "location": list(obj.location), "rotation": list(obj.rotation_euler),
            "scale": list(obj.scale), "dimensions": list(obj.dimensions)}
    if obj.type == "MESH":
        mesh = obj.data
        item.update(vertices=len(mesh.vertices), faces=len(mesh.polygons),
                    materials=[m.name if m else None for m in mesh.materials],
                    uv_layers=[uv.name for uv in mesh.uv_layers],
                    bounds_world=[[min((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box),
                                   max((obj.matrix_world @ Vector(c))[i] for c in obj.bound_box)] for i in range(3)])
        bins = {"x": {}, "y": {}, "z": {}}
        for axis, axis_i in (("x", 0), ("y", 1), ("z", 2)):
            lo, hi = item["bounds_world"][axis_i]
            for face in mesh.polygons:
                p = obj.matrix_world @ face.center
                k = round((p[axis_i] - lo) / (hi - lo + 1e-9) * 10)
                bins[axis][k] = bins[axis].get(k, 0) + 1
        item["face_position_bins"] = bins
        parent = list(range(len(mesh.vertices)))
        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for edge in mesh.edges:
            a, b = edge.vertices
            parent[find(a)] = find(b)
        islands = {}
        for vert in mesh.vertices:
            root = find(vert.index)
            islands.setdefault(root, []).append(obj.matrix_world @ vert.co)
        item['islands'] = sorted([{'verts': len(points),
                                   'bounds': [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]}
                                  for points in islands.values()], key=lambda x: -x['verts'])[:20]
    report.append(item)
with open(ROOT + r"\Working\Tripo\inspection.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print(json.dumps(report, indent=2))

world = bpy.context.scene.world
world.color = (0.15, 0.15, 0.15)
def aim(obj, at):
    obj.rotation_euler = (Vector(at) - obj.location).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.camera_add(location=(1.25, -1.35, 0.88))
cam = bpy.context.object
aim(cam, (0, 0, 0.10))
cam.data.type = 'ORTHO'
cam.data.ortho_scale = 1.55
bpy.context.scene.camera = cam
for loc, energy, size in [((-1.0, -1.0, 1.6), 350, 2.0), ((0.3, 1.2, 1.1), 200, 1.5)]:
    bpy.ops.object.light_add(type='AREA', location=loc)
    lamp = bpy.context.object
    lamp.data.energy = energy
    lamp.data.shape = 'DISK'
    lamp.data.size = size
    aim(lamp, (0, 0, 0.10))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 20
scene.render.resolution_x = 900
scene.render.resolution_y = 700
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = ROOT + r'\Working\Tripo\source_inspection.png'
bpy.ops.render.render(write_still=True)
