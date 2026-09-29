"""One-time update of the saved review camera after adding builder framing."""

from pathlib import Path

import bpy
from mathutils import Vector

root = Path(__file__).resolve().parents[1]
source = root / "BRAIN-ASTRA-001.blend"
bpy.ops.wm.open_mainfile(filepath=str(source))
cam = bpy.context.scene.camera
assert cam and cam.type == "CAMERA"
cam.location = (0.067, -0.3, 0.105)
cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.ortho_scale = 0.215
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_perspective = "CAMERA"
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(source))
print("CAMERA_FRAMED", tuple(cam.location), cam.data.ortho_scale)
