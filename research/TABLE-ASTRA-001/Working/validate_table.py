"""Re-import the game FBX and check the functional mesh hierarchy."""
import bpy
import json
from pathlib import Path

ROOT = Path(r"C:\Dev\Game-main\research\TABLE-ASTRA-001")
FBX = ROOT / "TABLE-ASTRA-001.fbx"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=str(FBX))
objects = list(bpy.context.scene.objects)
names = {obj.name for obj in objects}
wheel_meshes = [obj for obj in objects if obj.type == "MESH" and obj.name.startswith("GEO_Wheel_")]
fork_meshes = [obj for obj in objects if obj.type == "MESH" and obj.name.startswith("GEO_Caster_Fork_")]
roll_pivots = [obj for obj in objects if obj.name.startswith("RIG_WheelRoll_")]
steer_pivots = [obj for obj in objects if obj.name.startswith("RIG_CasterSteer_")]
braces = [obj for obj in objects if obj.name.startswith("GEO_Lower_Longitudinal_Brace_")]
assert len(wheel_meshes) == len(fork_meshes) == len(roll_pivots) == len(steer_pivots) == 4
assert len(braces) == 2
assert "GEO_Push_Handle_Foot" in names
assert "GEO_Push_Handle_Head" not in names
assert all(obj.parent and obj.parent.name.startswith("RIG_WheelRoll_") for obj in wheel_meshes)
assert all(obj.parent and obj.parent.name.startswith("RIG_CasterSteer_") for obj in fork_meshes)
assert all(obj.parent and obj.parent.name.startswith("RIG_CasterSteer_") for obj in roll_pivots)
assert all(obj.data.materials for obj in objects if obj.type == "MESH")
mesh_faces = sum(len(obj.data.polygons) for obj in objects if obj.type == "MESH")
report = {"fbx": str(FBX), "reimport_ok": True, "mesh_faces": mesh_faces,
          "wheel_meshes": len(wheel_meshes), "caster_forks": len(fork_meshes),
          "roll_pivots": len(roll_pivots), "steering_pivots": len(steer_pivots),
          "lower_braces": len(braces), "one_foot_handle": True,
          "material_slots_present": True}
(ROOT / "Working" / "export_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
