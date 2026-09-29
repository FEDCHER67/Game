"""Independent source and FBX round-trip validation for BRAIN-ASTRA-001."""

import json
import math
from pathlib import Path

import bmesh
import bpy

root = Path(__file__).resolve().parents[1]
source = root / "BRAIN-ASTRA-001.blend"
fbx = root / "BRAIN-ASTRA-001.fbx"
assert source.is_file() and fbx.is_file()


def inspect_mesh(obj):
    assert obj.type == "MESH"
    assert len(obj.data.materials) == 1
    assert len(obj.data.uv_layers) >= 1
    assert all(math.isfinite(c) for v in obj.data.vertices for c in v.co)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()
    result = {
        "name": obj.name,
        "vertices": len(bm.verts),
        "faces": len(bm.faces),
        "triangles": sum(len(f.verts) - 2 for f in bm.faces),
        "uv_layers": [layer.name for layer in obj.data.uv_layers],
        "boundary_edges": sum(e.is_boundary for e in bm.edges),
        "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
        "degenerate_faces": sum(f.calc_area() < 1e-10 for f in bm.faces),
        "signed_volume": bm.calc_volume(signed=True),
        "z_min": min(v.co.z for v in bm.verts),
        "z_max": max(v.co.z for v in bm.verts),
    }
    bm.free()
    assert result["boundary_edges"] == 0, result
    assert result["nonmanifold_edges"] == 0, result
    assert result["degenerate_faces"] == 0, result
    assert result["signed_volume"] > 0, result
    return result


bpy.ops.wm.open_mainfile(filepath=str(source))
asset = bpy.data.collections["BRAIN-ASTRA-001 | Game Mesh"]
studio = bpy.data.collections["Preview Studio | Not Exported"]
assert len(asset.objects) == 2
assert sorted(o.name for o in asset.objects) == ["Left hemisphere", "Right hemisphere"]
assert all(o.type != "MESH" for o in studio.objects)
assert bpy.context.scene.view_layers[0].material_override is None
assert bpy.data.objects["Underside review fill"].hide_render
assert bpy.data.objects["Rear review fill"].hide_render
cam = bpy.context.scene.camera
assert cam is not None and cam.type == "CAMERA"
assert (cam.location - bpy.data.objects["Left hemisphere"].location).length > 0.2
assert 0.20 < cam.data.ortho_scale < 0.23
assert not any("stem" in o.name.lower() for o in bpy.data.objects)
source_data = [inspect_mesh(o) for o in asset.objects]
source_triangles = sum(r["triangles"] for r in source_data)
source_vertices = sum(r["vertices"] for r in source_data)
assert all(r["z_min"] > -0.06 for r in source_data)
mat = bpy.data.materials["01 | Warm dusty rose soft matte"]
bsdf = mat.node_tree.nodes.get("Principled BSDF")
assert abs(bsdf.inputs["Roughness"].default_value - 0.79) < 1e-5
assert bsdf.inputs["Coat Weight"].default_value == 0

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(fbx))
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
assert len(meshes) == 2, [o.name for o in meshes]
fbx_data = [inspect_mesh(o) for o in meshes]
assert sum(r["triangles"] for r in fbx_data) == source_triangles
assert sum(r["vertices"] for r in fbx_data) == source_vertices
assert all(o.type == "MESH" for o in bpy.context.scene.objects)

print("BRAIN_VALIDATION", json.dumps({
    "result": "PASS", "blender": bpy.app.version_string,
    "source": source_data, "fbx": fbx_data,
    "total_vertices": source_vertices, "total_triangles": source_triangles,
}, sort_keys=True))
