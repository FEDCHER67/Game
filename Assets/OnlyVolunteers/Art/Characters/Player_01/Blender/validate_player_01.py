"""Additional pose checks for PLAYER-CHAR-003; does not save the .blend."""

import json
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_player_01_previews import (  # noqa: E402
    apply_pose,
    evaluated_points,
    mesh_checks,
    reset_pose,
)

HERE = os.path.dirname(os.path.abspath(__file__))
BLEND = os.path.join(HERE, "Player_01.blend")
OUT = os.path.normpath(os.path.join(HERE, "..", "Preview", "technical_pose_validation.json"))

POSES = {
    "arms_raised": (
        {"bone": "UpperArm.L", "axis": "X", "degrees": -95.0},
        {"bone": "UpperArm.R", "axis": "X", "degrees": 95.0},
    ),
    "elbows_bent": (
        {"bone": "LowerArm.L", "axis": "X", "degrees": 105.0},
        {"bone": "LowerArm.R", "axis": "X", "degrees": -105.0},
    ),
    "knees_bent": (
        {"bone": "UpperLeg.L", "axis": "X", "degrees": -45.0},
        {"bone": "UpperLeg.R", "axis": "X", "degrees": -45.0},
        {"bone": "LowerLeg.L", "axis": "X", "degrees": 95.0},
        {"bone": "LowerLeg.R", "axis": "X", "degrees": 95.0},
    ),
    "ragdoll_extreme": (
        {"bone": "UpperArm.L", "axis": "X", "degrees": -125.0},
        {"bone": "UpperArm.R", "axis": "X", "degrees": 125.0},
        {"bone": "LowerArm.L", "axis": "X", "degrees": 130.0},
        {"bone": "LowerArm.R", "axis": "X", "degrees": -130.0},
        {"bone": "UpperLeg.L", "axis": "X", "degrees": -95.0},
        {"bone": "UpperLeg.R", "axis": "X", "degrees": -75.0},
        {"bone": "LowerLeg.L", "axis": "X", "degrees": 130.0},
        {"bone": "LowerLeg.R", "axis": "X", "degrees": 115.0},
    ),
}

bpy.ops.wm.open_mainfile(filepath=BLEND)
mesh = bpy.data.objects["Player_01"]
armature = bpy.data.objects["Armature"]
reset_pose(armature)
rest = evaluated_points(mesh)
results = {"neutral": mesh_checks(rest, rest), "poses": {}}
for name, angles in POSES.items():
    reset_pose(armature)
    apply_pose(armature, angles)
    results["poses"][name] = {
        "bone_angles": list(angles),
        "checks": mesh_checks(evaluated_points(mesh), rest),
    }
reset_pose(armature)
results["restored"] = max((a - b).length for a, b in zip(evaluated_points(mesh), rest)) < 1e-6
results["ok"] = (results["neutral"]["ok"] and results["restored"]
                 and all(p["checks"]["ok"] for p in results["poses"].values()))
with open(OUT, "w", encoding="utf-8") as handle:
    json.dump(results, handle, indent=2)
print("TECHNICAL_POSES=" + json.dumps({
    "ok": results["ok"],
    "poses": {name: value["checks"]["ok"] for name, value in results["poses"].items()},
    "restored": results["restored"],
}))
if not results["ok"]:
    raise SystemExit(1)
