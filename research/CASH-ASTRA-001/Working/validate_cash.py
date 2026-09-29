import bpy
import bmesh
import json
from pathlib import Path
from mathutils import Vector

root = Path(r"C:\Dev\Game-main\research\CASH-ASTRA-001")

def summarize():
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"
              and not obj.name.startswith("PREVIEW_")]
    counts = {"objects": len(meshes), "vertices": 0, "polygons": 0,
              "triangles": 0, "materials": set(), "unassigned_faces": 0,
              "core_open_edges": {}, "core_nonmanifold_edges": {},
              "world_bounds": [[float("inf"), -float("inf")] for _ in range(3)],
              "names": sorted(obj.name for obj in meshes)}
    for obj in meshes:
        mesh = obj.data
        counts["vertices"] += len(mesh.vertices)
        counts["polygons"] += len(mesh.polygons)
        mesh.calc_loop_triangles()
        counts["triangles"] += len(mesh.loop_triangles)
        counts["materials"].update(m.name for m in mesh.materials if m)
        counts["unassigned_faces"] += sum(1 for face in mesh.polygons
                                          if face.material_index >= len(mesh.materials))
        if obj.name in {"SM_Cash_Band", "SM_Cash_LayerStack", "SM_Cash_MidBill", "SM_Cash_TopBill"}:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            counts["core_open_edges"][obj.name] = sum(1 for edge in bm.edges if edge.is_boundary)
            counts["core_nonmanifold_edges"][obj.name] = sum(1 for edge in bm.edges if not edge.is_manifold)
            bm.free()
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for i in range(3):
                counts["world_bounds"][i][0] = min(counts["world_bounds"][i][0], world[i])
                counts["world_bounds"][i][1] = max(counts["world_bounds"][i][1], world[i])
    counts["materials"] = sorted(counts["materials"])
    return counts

bpy.ops.wm.open_mainfile(filepath=str(root / "CASH-ASTRA-001.blend"))
blend = summarize()
preview_objects = sorted(o.name for o in bpy.context.scene.objects if o.name.startswith("PREVIEW_"))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(root / "CASH-ASTRA-001.fbx"))
export = summarize()
result = {"blend": blend, "fbx_reimport": export,
          "preview_objects_in_blend": preview_objects,
          "fbx_preview_objects": [n for n in export["names"] if n.startswith("PREVIEW_")]}
with open(root / "Working" / "validation.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
print(json.dumps(result, indent=2))
