"""InstrumentStand_v01: a simple wheeled Mayo-style instrument stand in the TABLE-ASTRA-001 style and palette.

blender -b --factory-startup --python build_instrument_stand_v01.py [-- --out <dir>]

Stand-local frame (Blender): origin on the floor under the tray centre, +Z up, tray long side along +-Y (parallel to
the table when placed at TrayAnchor with identity rotation), -X = the edge facing the table.
Tray floor top (slot height) z = 0.690 m: just above the gurney pad (0.646-0.664). Slots have the stand's axes
(Unity: +Y up; long items lie along the table, Unity local Z).
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

import bmesh
import bpy
from mathutils import Matrix, Vector

from v02_common import (V02, TABLE_V01_BLEND, clean_scene, ensure_collection, refuse_overwrite, log, argv_after_dashes,
                        tri_count, make_material)

ARGS = argv_after_dashes()
OUT_DIR = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else V02
OUT_BLEND = OUT_DIR / "InstrumentStand_v01.blend"
OUT_FBX = OUT_DIR / "InstrumentStand_v01.fbx"

TRAY_X, TRAY_Y = 0.42, 0.54          # outer depth (across the table) x length (along the table)
FLOOR_Z, RIM_Z, BOTTOM_Z = 0.690, 0.714, 0.680
CORNER_R = 0.03
SLOT_Z = FLOOR_Z + 0.002
SLOTS = {
    "SLOT_SYRINGE_ANESTHESIA": (-0.135, -0.165),
    "SLOT_SYRINGE_BLOOD": (-0.135, 0.0),
    "SLOT_SCALPEL": (-0.135, 0.165),
    "SLOT_BLOODBAG_1": (0.0, -0.165),
    "SLOT_BLOODBAG_2": (0.0, 0.0),
    "SLOT_BLOODBAG_3": (0.0, 0.165),
    "SLOT_ORGAN_1": (0.135, -0.165),
    "SLOT_ORGAN_2": (0.135, 0.0),
    "SLOT_ORGAN_3": (0.135, 0.165),
}


def table_materials():
    names = ["MAT_Frame_MatteGraphite", "MAT_Pad_MutedBlueGray", "MAT_Wheels_DarkRubber", "MAT_Straps_Charcoal"]
    with bpy.data.libraries.load(str(TABLE_V01_BLEND), link=False) as (src, dst):
        dst.materials = names
    mats = {m.name: m for m in dst.materials}
    mats["MAT_Astra_MatteSteel"] = make_material("MAT_Astra_MatteSteel", (0.56, 0.61, 0.65, 1.0), rough=0.78, metal=0.32)
    return mats


def rounded_rect(hx, hy, r, n=3):
    pts = []
    for cx, cy, a0 in ((hx - r, hy - r, 0), (-hx + r, hy - r, 90), (-hx + r, -hy + r, 180), (hx - r, -hy + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def tray(bm):
    """Rounded pan: chamfered bottom edge, vertical outer wall, flat rim, inner wall, blue-grey floor mat."""
    hx, hy = TRAY_X / 2, TRAY_Y / 2
    spec = [(0.006, BOTTOM_Z), (0.0, BOTTOM_Z + 0.006), (0.0, RIM_Z), (0.010, RIM_Z), (0.012, FLOOR_Z)]
    rings = []
    for inset, z in spec:
        rings.append([bm.verts.new((x, y, z)) for x, y in rounded_rect(hx - inset, hy - inset, CORNER_R - inset)])
    n = len(rings[0])
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            bm.faces.new((a[k], a[(k + 1) % n], b[(k + 1) % n], b[k]))
    bm.faces.new(list(reversed(rings[0])))              # bottom
    fl = bm.faces.new(rings[-1])                        # floor (blue-grey mat)
    fl.material_index = 1


def cylinder(bm, x, y, z0, z1, r, seg=8, mat=0):
    rings = [[bm.verts.new((x + r * math.cos(2 * math.pi * k / seg), y + r * math.sin(2 * math.pi * k / seg), z))
              for k in range(seg)] for z in (z0, z1)]
    for k in range(seg):
        f = bm.faces.new((rings[0][k], rings[0][(k + 1) % seg], rings[1][(k + 1) % seg], rings[1][k]))
        f.material_index = mat
    bm.faces.new(list(reversed(rings[0]))).material_index = mat
    bm.faces.new(rings[1]).material_index = mat


def box(bm, mn, mx, mat=0):
    v = [bm.verts.new((x, y, z)) for x in (mn[0], mx[0]) for y in (mn[1], mx[1]) for z in (mn[2], mx[2])]
    for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([v[i] for i in f]).material_index = mat


def wheel(bm, x, y, r=0.03, w=0.022, seg=10):
    """Caster wheel, axle along X, resting on the floor."""
    rings = []
    for dx in (-w / 2, w / 2):
        rings.append([bm.verts.new((x + dx, y + r * math.cos(2 * math.pi * k / seg - math.pi / 2), r + r * math.sin(2 * math.pi * k / seg - math.pi / 2)))
                      for k in range(seg)])
    for k in range(seg):
        bm.faces.new((rings[0][k], rings[1][k], rings[1][(k + 1) % seg], rings[0][(k + 1) % seg]))
    bm.faces.new(rings[0])
    bm.faces.new(list(reversed(rings[1])))


def to_obj(bm, name, mats, parent, coll):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.parent = parent
    return ob


def main():
    refuse_overwrite(OUT_BLEND, OUT_FBX)
    clean_scene()
    mats = table_materials()
    coll = ensure_collection("INSTRUMENT_STAND_v01")
    root = bpy.data.objects.new("STAND_Root", None)
    root.empty_display_type = "PLAIN_AXES"
    coll.objects.link(root)

    bm = bmesh.new()
    tray(bm)
    tray_ob = to_obj(bm, "GEO_Stand_Tray", [mats["MAT_Astra_MatteSteel"], mats["MAT_Pad_MutedBlueGray"]], root, coll)

    bm = bmesh.new()
    # base: two feet along Y, one cross bar, telescopic post, tray bracket
    for sx in (-1, 1):
        box(bm, (sx * 0.15 - 0.02, -0.25, 0.062), (sx * 0.15 + 0.02, 0.25, 0.088))
    box(bm, (-0.15, -0.02, 0.064), (0.15, 0.02, 0.086))
    cylinder(bm, 0, 0, 0.086, 0.42, 0.022)
    cylinder(bm, 0, 0, 0.40, 0.43, 0.029)               # clamp collar
    cylinder(bm, 0, 0, 0.43, BOTTOM_Z - 0.010, 0.016)
    box(bm, (-0.09, -0.16, BOTTOM_Z - 0.012), (0.09, 0.16, BOTTOM_Z))   # tray bracket plate
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(bm, (sx * 0.15 - 0.016, sy * 0.23 - 0.012, 0.030), (sx * 0.15 + 0.016, sy * 0.23 + 0.012, 0.062))  # fork
    frame_ob = to_obj(bm, "GEO_Stand_Frame", [mats["MAT_Frame_MatteGraphite"]], root, coll)

    bm = bmesh.new()
    for sx in (-1, 1):
        for sy in (-1, 1):
            wheel(bm, sx * 0.15, sy * 0.23 + 0.006)
    wheel_ob = to_obj(bm, "GEO_Stand_Wheels", [mats["MAT_Wheels_DarkRubber"]], root, coll)

    for name, (x, y) in SLOTS.items():
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = "ARROWS"
        e.empty_display_size = 0.04
        coll.objects.link(e)
        e.parent = root
        e.location = (x, y, SLOT_Z)

    tris = {o.name: tri_count(o) for o in (tray_ob, frame_ob, wheel_ob)}
    log("tris", tris, "total", sum(tris.values()))
    bpy.context.view_layer.update()
    min_z = min((o.matrix_world @ v.co).z for o in (tray_ob, frame_ob, wheel_ob) for v in o.data.vertices)
    log("min z", round(min_z, 5))
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
    bpy.ops.object.select_all(action="DESELECT")
    for ob in coll.objects:
        ob.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT_FBX), use_selection=True, object_types={"MESH", "EMPTY"},
                             use_mesh_modifiers=True, bake_anim=False, axis_forward="-Z", axis_up="Y",
                             apply_scale_options="FBX_SCALE_UNITS")
    log("exported", OUT_FBX, json.dumps({"slots": {k: [v[0], v[1], SLOT_Z] for k, v in SLOTS.items()}}))


main()
