"""Re-import the game FBX and check its parts, size and polygon budget."""
import bpy
import json
from pathlib import Path

root = Path(r"C:\Dev\Game-main\research\SCALPEL-ASTRA-001")
target = root / "SCALPEL-ASTRA-001.fbx"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(target))
bpy.context.view_layer.update()
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
report = {
    "fbx": str(target),
    "parts": [{"name": o.name, "faces": len(o.data.polygons),
               "materials": [m.name for m in o.data.materials]} for o in meshes],
    "bounds_m": [[min(p[i] for p in points), max(p[i] for p in points)] for i in range(3)],
}
report["total_faces"] = sum(o["faces"] for o in report["parts"])
assert len(meshes) == 2, report
assert report["total_faces"] < 1300, report
assert 0.15 < report["bounds_m"][0][1] - report["bounds_m"][0][0] < 0.16, report
assert 0.0042 < report["bounds_m"][1][1] - report["bounds_m"][1][0] < 0.0052, report
assert 0.0135 < report["bounds_m"][2][1] - report["bounds_m"][2][0] < 0.0148, report
assert all(o["materials"] for o in report["parts"]), report
(root / "Working" / "reimport_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
