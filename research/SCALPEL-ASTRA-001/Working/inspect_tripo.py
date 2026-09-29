"""Inspect the first Tripo scalpel candidate without modifying source."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(r"C:\Dev\Game-main\research\SCALPEL-ASTRA-001")
SOURCE = ROOT / "Working" / "Tripo" / "SCALPEL-ASTRA-001_Tripo_Front.fbx"
OUT = ROOT / "Working" / "Tripo"

bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(SOURCE))
bpy.context.view_layer.update()
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
bounds = [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)]
report = {
    "source": str(SOURCE),
    "bounds": bounds,
    "meshes": [{"name": o.name, "vertices": len(o.data.vertices),
                "faces": len(o.data.polygons), "dimensions": list(o.dimensions),
                "materials": [m.name if m else None for m in o.data.materials]}
               for o in meshes],
}
report["x_bins"] = []
for low, high in [(-0.5,-0.3),(-0.3,-0.2),(-0.2,-0.1),(-0.1,0.1),(0.1,0.5)]:
    subset = [p for p in points if low <= p.x < high]
    report["x_bins"].append({"range":[low,high],"count":len(subset),
        "y":[min(p.y for p in subset),max(p.y for p in subset)] if subset else None,
        "z":[min(p.z for p in subset),max(p.z for p in subset)] if subset else None})
(OUT / "inspection.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))

center = Vector([(lo + hi) / 2 for lo, hi in bounds])
extent = max(hi - lo for lo, hi in bounds)
bpy.ops.object.camera_add(location=center + Vector((0.15, -1.6, 0.8)) * extent)
camera = bpy.context.object
camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.type = "ORTHO"
camera.data.ortho_scale = extent * 1.5
bpy.context.scene.camera = camera
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "SINGLE"
scene.display.shading.single_color = (0.65, 0.68, 0.72)
scene.display.shading.show_cavity = True
scene.render.resolution_x = 1200
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(OUT / "source_inspection.png")
bpy.ops.render.render(write_still=True)
