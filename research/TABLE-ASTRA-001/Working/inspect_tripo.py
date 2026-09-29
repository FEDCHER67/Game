"""Inspect the approved Tripo FBX without modifying its geometry."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(r"C:\Dev\Game-main\research\TABLE-ASTRA-001")
SOURCE = ROOT / "Working" / "Tripo" / "TABLE-ASTRA-001_Tripo_Rev03.fbx"
OUT = ROOT / "Working" / "Tripo"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(SOURCE))
bpy.context.view_layer.update()

items = []
all_points = []
for obj in bpy.context.scene.objects:
    info = {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
    }
    if obj.type == "MESH":
        mesh = obj.data
        points = [obj.matrix_world @ v.co for v in mesh.vertices]
        all_points.extend(points)
        info.update(
            vertices=len(mesh.vertices),
            faces=len(mesh.polygons),
            materials=[m.name if m else None for m in mesh.materials],
            bounds=[[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)],
        )
        parent = list(range(len(mesh.vertices)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for edge in mesh.edges:
            a, b = edge.vertices
            parent[find(a)] = find(b)
        islands = {}
        for vert in mesh.vertices:
            islands.setdefault(find(vert.index), []).append(obj.matrix_world @ vert.co)
        info["islands"] = sorted(
            (
                {
                    "vertices": len(ps),
                    "bounds": [[min(p[i] for p in ps), max(p[i] for p in ps)] for i in range(3)],
                }
                for ps in islands.values()
            ),
            key=lambda island: -island["vertices"],
        )
    items.append(info)

global_bounds = [[min(p[i] for p in all_points), max(p[i] for p in all_points)] for i in range(3)]
report = {"source": str(SOURCE), "bounds": global_bounds, "objects": items}
(OUT / "inspection.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"bounds": global_bounds, "meshes": [{"name": o["name"], "faces": o.get("faces"), "islands": len(o.get("islands", []))} for o in items]}, indent=2))

center = Vector([(lo + hi) / 2 for lo, hi in global_bounds])
extent = max(hi - lo for lo, hi in global_bounds)
bpy.ops.object.camera_add(location=center + Vector((1.4, -1.3, 0.9)) * extent)
camera = bpy.context.object
camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = extent * 1.7
bpy.context.scene.camera = camera

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.64, 0.67, 0.71)
scene.display.shading.show_cavity = True
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "source_inspection.png")
bpy.ops.render.render(write_still=True)
